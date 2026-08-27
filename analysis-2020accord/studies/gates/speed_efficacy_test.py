#!/usr/bin/env python3
r"""Follow-up to studies/gates/speed_status_engagement.py (team-lead request): does the EPS actually
REFUSE to steer at low speed, or does it merely LABEL the status while still complying?

Uses two EPS-transmitted signals on CAN 399 (0x18F) that studies/gates/speed_status_engagement.py did not
decode, per the DBC ground-truth in opendbc_repo/opendbc/dbc/generator/honda/_bosch_2018.dbc
(the fragment actually imported by honda_civic_hatchback_ex_2017_can.dbc, the Accord's DBC --
confirmed via generator.py's plain-text IMPORT resolution, not the _steering_control_a/b/c.dbc
fragment used by Clarity/Odyssey/RDX/ILX/Civic-Touring):

  BO_ 399 STEER_STATUS: 7 EPS
   SG_ STEER_TORQUE_SENSOR  : 7|16@0-  (-1,0)              bytes[0:2] BE, negated
   SG_ STEER_ANGLE_RATE     : 23|16@0- (-0.1,0) "deg/s"     bytes[2:4] BE, x -0.1
   SG_ STEER_STATUS         : 39|4@0+                       byte[4] high nibble
   SG_ STEER_CONTROL_ACTIVE : 35|1@0+                       byte[4] bit 3 (mask 0x08)
   SG_ CHECKSUM             : 51|4@0+                       byte[6] low nibble
   SG_ COUNTER              : 53|2@0+                       byte[6] bits[5:4]

Also decodes the TX'd STEERING_CONTROL message (228 / 0xE4) for the actual commanded torque
openpilot put on the bus (not the normalized carControl.actuators.torque):
  BO_ 228 STEERING_CONTROL: 5 EON
   SG_ STEER_TORQUE         : 7|16@0-   bytes[0:2] BE        the commanded torque, EPS units
   SG_ STEER_TORQUE_REQUEST : 23|1@0+   byte[2] bit 7
   SG_ CHECKSUM             : 35|4@0+   byte[4] high nibble (see honda_checksum below)

Restricts everything to carControl.latActive==True (openpilot IS actively commanding), since
the whole question is whether the EPS complies when asked, not what it does when left alone.
"""
import sys, glob, collections
from pathlib import Path
import numpy as np

KIT = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod")
sys.path.insert(0, str(KIT / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

MPH = 2.23694


def honda_checksum(address, d):
    s = 0; a = address
    while a:
        s += a & 0xF; a >>= 4
    for i, b in enumerate(d):
        if i == len(d) - 1:
            b >>= 4
        s += (b & 0xF) + (b >> 4)
    return (8 - s) & 0xF


def s16be(b0, b1):
    v = (b0 << 8) | b1
    return v - 0x10000 if v & 0x8000 else v


EDGES = [0, 1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 45, 100]
def bucket(mph):
    for i in range(len(EDGES) - 1):
        if EDGES[i] <= mph < EDGES[i + 1]:
            return f"{EDGES[i]:>3d}-{EDGES[i+1]:<3d}"
    return "100+"
ORDER = [f"{EDGES[i]:>3d}-{EDGES[i+1]:<3d}" for i in range(len(EDGES) - 1)]


def find_all_rlogs():
    flat = sorted((KIT / "analysis-2020accord" / "rlogs").glob("*.zst"))
    nested = sorted((KIT / "analysis-2020accord" / "rlogs").glob("*/*/*/rlog.zst"))
    return flat, nested


def route_groups():
    flat, nested = find_all_rlogs()
    def route_key(p):
        parts = p.stem.split("--")
        return "--".join(parts[:-2]) if len(parts) >= 3 else p.stem
    groups = collections.defaultdict(list)
    for p in flat:
        groups[route_key(p)].append(p)
    for p in nested:
        route_id = p.parent.parent.name
        groups[f"manual/{route_id}"].append(p)
    return groups


def process_route(paths):
    lat = False
    vego = None
    cmd_torque = 0
    cmd_req = 0
    n228 = 0
    n399 = 0
    chk_bad_399 = 0
    chk_bad_228 = 0

    # rows, only kept when latActive==True at time of a 399 frame
    rows = []  # (bucket, status, control_active, angle_rate_dps, torque_sensor, cmd_torque, cmd_req)

    for p in paths:
        try:
            for evt in read_messages(p):
                try:
                    w = evt.which()
                except Exception:
                    continue
                if w == "carControl":
                    lat = bool(evt.carControl.latActive)
                elif w == "carState":
                    vego = float(evt.carState.vEgo) * MPH
                elif w == "can":
                    for fr in evt.can:
                        if fr.address == 228 and len(fr.dat) == 5:
                            d = bytes(fr.dat)
                            if honda_checksum(228, d) != (d[4] & 0xF):
                                chk_bad_228 += 1
                                continue
                            n228 += 1
                            cmd_torque = s16be(d[0], d[1])
                            cmd_req = (d[2] >> 7) & 1
                        elif fr.address == 399 and fr.src == 1 and len(fr.dat) == 7:
                            if vego is None:
                                continue
                            d = bytes(fr.dat)
                            if honda_checksum(399, d) != (d[6] & 0xF):
                                chk_bad_399 += 1
                                continue
                            n399 += 1
                            status = (d[4] >> 4) & 0xF
                            control_active = (d[4] >> 3) & 1
                            angle_rate = -0.1 * s16be(d[2], d[3])
                            torque_sensor = -s16be(d[0], d[1])
                            if lat:
                                rows.append((bucket(vego), status, control_active, angle_rate,
                                             torque_sensor, cmd_torque, cmd_req))
        except Exception as e:
            print(f"    [warn] {p.name}: {e}", file=sys.stderr)
    return rows, n399, n228, chk_bad_399, chk_bad_228


def pctl(a, q):
    return float(np.percentile(a, q)) if len(a) else float("nan")


def main():
    groups = route_groups()
    all_rows = []
    total_n399 = total_n228 = total_bad399 = total_bad228 = 0

    for key in sorted(groups):
        paths = sorted(groups[key])
        rows, n399, n228, bad399, bad228 = process_route(paths)
        total_n399 += n399; total_n228 += n228; total_bad399 += bad399; total_bad228 += bad228
        all_rows.extend(rows)
        if rows:
            print(f"[{key}] n399={n399} n228={n228} latActive=True rows kept={len(rows)}")

    print(f"\nTOTAL: n399={total_n399} (bad={total_bad399})  n228={total_n228} (bad={total_bad228})")
    print(f"latActive==True rows retained for analysis: {len(all_rows)}")

    # ---- A) HEADLINE: co-occurrence of STEER_CONTROL_ACTIVE and STEER_STATUS==LOW_SPEED_LOCKOUT(3),
    #        restricted to latActive==True, at 0-3 mph ----
    print("\n" + "=" * 100)
    print("HEADLINE: STEER_CONTROL_ACTIVE vs STEER_STATUS, latActive=True, 0-3 mph band")
    low_rows = [r for r in all_rows if r[0] in ("  0-1  ", "  1-2  ", "  2-3  ")]
    cross = collections.Counter()
    for (_, status, ca, *_rest) in low_rows:
        cross[(status, ca)] += 1
    tot_low = sum(cross.values())
    print(f"  n={tot_low} frames (latActive=True, 0-3mph)")
    for (status, ca), n in sorted(cross.items()):
        print(f"  STEER_STATUS={status:<2} STEER_CONTROL_ACTIVE={ca}  n={n:>7}  ({100*n/max(tot_low,1):5.1f}%)")
    lockout_and_active = cross.get((3, 1), 0)
    lockout_total = sum(v for (s, ca), v in cross.items() if s == 3)
    print(f"\n  Co-occurrence check: STEER_STATUS==3(LOW_SPEED_LOCKOUT) AND STEER_CONTROL_ACTIVE==1: "
          f"{lockout_and_active} / {lockout_total} lockout frames "
          f"({100*lockout_and_active/max(lockout_total,1):.2f}%)")

    # ---- B) STEER_CONTROL_ACTIVE by speed bucket, latActive==True ----
    print("\n" + "=" * 100)
    print("B) STEER_CONTROL_ACTIVE by speed bucket (latActive=True)")
    buckets = collections.defaultdict(collections.Counter)
    for (b, status, ca, *_rest) in all_rows:
        buckets[b][ca] += 1
    print(f"  {'speed(mph)':>12} {'n':>7}   {'CA=0':>7} {'CA=1':>7}")
    for b in ORDER:
        c = buckets.get(b)
        if not c:
            continue
        tot = sum(c.values())
        print(f"  {b:>12} {tot:>7}   {100*c.get(0,0)/tot:6.1f}% {100*c.get(1,0)/tot:6.1f}%")

    # ---- C) |STEER_ANGLE_RATE| and |commanded torque| by speed bucket, latActive==True ----
    print("\n" + "=" * 100)
    print("C) |STEER_ANGLE_RATE| (deg/s) and |commanded STEER_TORQUE| by speed bucket (latActive=True)")
    by_bucket = collections.defaultdict(list)
    for (b, status, ca, rate, tsens, cmdt, cmdreq) in all_rows:
        by_bucket[b].append((rate, cmdt, cmdreq, ca))
    print(f"  {'speed(mph)':>12} {'n':>7}   {'|rate| mean':>12} {'p50':>8} {'p90':>8}   "
          f"{'|cmdT| mean':>12}   {'rate/|cmdT|':>12}   {'%CA=1':>7}")
    for b in ORDER:
        recs = by_bucket.get(b)
        if not recs:
            continue
        rates = np.abs(np.array([r[0] for r in recs]))
        cmdts = np.abs(np.array([r[1] for r in recs]))
        cas = np.array([r[3] for r in recs])
        mean_rate = rates.mean(); mean_cmdt = cmdts.mean()
        ratio = mean_rate / mean_cmdt if mean_cmdt > 1e-6 else float("nan")
        print(f"  {b:>12} {len(recs):>7}   {mean_rate:12.2f} {pctl(rates,50):8.2f} {pctl(rates,90):8.2f}   "
              f"{mean_cmdt:12.1f}   {ratio:12.5f}   {100*cas.mean():6.1f}%")

    # split further by CA state for the low-speed bands specifically
    print("\n  Low-speed detail, split by STEER_CONTROL_ACTIVE (0 vs 1):")
    for b in ("  0-1  ", "  1-2  ", "  2-3  ", "  3-4  ", "  4-5  ", "  5-6  ", "  6-8  ", " 10-15 "):
        recs = by_bucket.get(b)
        if not recs:
            continue
        for ca_val in (0, 1):
            sub = [r for r in recs if r[3] == ca_val]
            if not sub:
                continue
            rates = np.abs(np.array([r[0] for r in sub]))
            cmdts = np.abs(np.array([r[1] for r in sub]))
            mean_rate = rates.mean(); mean_cmdt = cmdts.mean()
            ratio = mean_rate / mean_cmdt if mean_cmdt > 1e-6 else float("nan")
            print(f"    {b} CA={ca_val}  n={len(sub):>6}  |rate| mean={mean_rate:8.2f} p90={pctl(rates,90):8.2f}  "
                  f"|cmdT| mean={mean_cmdt:8.1f}  ratio={ratio:.5f}")


if __name__ == "__main__":
    main()
