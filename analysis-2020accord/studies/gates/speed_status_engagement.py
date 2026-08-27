#!/usr/bin/env python3
r"""Decisive test for the low-speed-steer handoff (Task 2, team-lead brief):
does raw CAN 399 STEER_STATUS = LOW_SPEED_LOCKOUT (3) appear as a function of
SPEED even when openpilot is NOT engaged/commanding (carControl.latActive==False)?

If status=3 shows up at low speed regardless of latActive -> could be a genuine
firmware speed compare (or at minimum, an engagement-substate fallback that
correlates with speed for reasons independent of what OP is doing this instant).
If status=3 ONLY shows while latActive==True is irrelevant framing -- the real
per-firmware-trace claim (reference_accord_no_vehicle_speed_in_arbitration_steerstatus3)
is the opposite: status should FALL to 3 whenever latActive is NOT active/engaged
(because the assist substate gp-0x67fe never reaches "engaged"=2), independent of
whether that's because of low speed or plain disengagement. So the real
discriminator is: does status=3 ALSO appear at HIGH speed whenever OP is NOT
commanding steering (latActive False for reasons other than low speed, e.g. not
engaged at all)? If yes at both high and low speed -> confirms "engagement
fallback", not a firmware speed comparison. If status=3 is confined to low speed
even while latActive=True (OP IS commanding) -> that WOULD indicate a genuine
EPS-side speed lockout that not even LKAS-active can override.

Outputs, for the grand total and per-route:
  - status distribution x (latActive bucket) x (speed bucket)
  - lowest speed bucket where status==NORMAL(0) is observed
  - lowest speed bucket where status==LOW_SPEED_LOCKOUT(3) is observed while latActive==True
  - highest speed bucket where status==3 is observed while latActive==False

DBC ground truth for the byte-level decode below (confirmed 2026-07-24 against the real pinned
repo, not the vendored analysis-2020accord/reference/opendbc/ copy):
opendbc_repo/opendbc/dbc/generator/honda/_bosch_2018.dbc, BO_ 399 STEER_STATUS: 7 EPS. This is
the fragment actually pulled into the Accord's compiled DBC -- honda_civic_hatchback_ex_2017_can.dbc
(values.py Bus.pt for CAR.HONDA_ACCORD) imports "_bosch_2018.dbc" via a plain-text
CM_ "IMPORT ..." directive that generator.py resolves by literal concatenation (no override
semantics) -- confirmed by reading generator.py's _create_dbc_content(). Three OTHER near-identical
BO_ 399 fragments exist in the same directory (_steering_control_a/b/c.dbc, enum "1=driver_steering"
+ explicit "7=permanent_fault", 6-7 byte length) but those are imported only by
acura_ilx_2016_can.dbc / acura_rdx_2018_can.dbc / honda_civic_touring_2016_can.dbc (NIDEC, not this
car) / honda_clarity_hybrid_2018_can.dbc / honda_crv_touring_2016_can.dbc / honda_odyssey_*.dbc --
none of which is HONDA_ACCORD's dbc. Do not cite the driver_steering/permanent_fault enum for this
car; VAL_ 399 STEER_STATUS 6 "tmp_fault" 5 "fault_1" 4 "no_torque_alert_2" 3 "low_speed_lockout"
2 "no_torque_alert_1" 1 "tja_low_speed_lockout" 0 "normal" is the applicable enum (values 0/3/4 used
below are identical across both enum variants, so this correction does not change any numeric
result already reported from this script).
"""
import sys, glob, io, collections
from pathlib import Path
import numpy as np

KIT = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod")
sys.path.insert(0, str(KIT / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

MPH = 2.23694
STATUS_NAMES = {0: "NORMAL", 1: "TJA_LOW_SPEED_LOCKOUT", 2: "NO_TORQUE_ALERT_1",
                3: "LOW_SPEED_LOCKOUT", 4: "NO_TORQUE_ALERT_2", 5: "FAULT_1", 6: "TMP_FAULT",
                7: "UNKNOWN(unmapped->steerFaultPermanent)"}

EDGES = [0, 1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 45, 100]
def bucket(mph):
    for i in range(len(EDGES) - 1):
        if EDGES[i] <= mph < EDGES[i + 1]:
            return f"{EDGES[i]:>3d}-{EDGES[i+1]:<3d}"
    return "100+"
ORDER = [f"{EDGES[i]:>3d}-{EDGES[i+1]:<3d}" for i in range(len(EDGES) - 1)]


def honda_checksum(address, d):
    s = 0; a = address
    while a:
        s += a & 0xF; a >>= 4
    for i, b in enumerate(d):
        if i == len(d) - 1:
            b >>= 4
        s += (b & 0xF) + (b >> 4)
    return (8 - s) & 0xF


def find_all_rlogs():
    flat = sorted((KIT / "analysis-2020accord" / "rlogs").glob("*.zst"))
    nested = sorted((KIT / "analysis-2020accord" / "rlogs").glob("*/*/*/rlog.zst"))
    nested += sorted((KIT / "analysis-2020accord" / "rlogs").glob("*/*/rlog.zst"))
    return flat, nested


def process_route(paths, label):
    """paths: list of rlog.zst segment paths belonging to one logical route, in order."""
    # (latActive_bucket, speed_bucket) -> Counter(status)
    grid = collections.defaultdict(collections.Counter)
    lat = False
    vego = None
    n399 = 0
    chk_bad = 0
    lat_seen = False
    for p in paths:
        try:
            for evt in read_messages(p):
                try:
                    w = evt.which()
                except Exception:
                    continue
                if w == "carControl":
                    lat = bool(evt.carControl.latActive)
                    lat_seen = True
                elif w == "carState":
                    vego = float(evt.carState.vEgo) * MPH
                elif w == "can":
                    if vego is None:
                        continue
                    for fr in evt.can:
                        if fr.address == 399 and fr.src == 1 and len(fr.dat) == 7:
                            d = bytes(fr.dat)
                            if honda_checksum(399, d) != (d[6] & 0xF):
                                chk_bad += 1
                                continue
                            status = (d[4] >> 4) & 0xF
                            n399 += 1
                            grid[(lat, bucket(vego))][status] += 1
        except Exception as e:
            print(f"    [warn] {p.name}: {e}", file=sys.stderr)
    return grid, n399, chk_bad, lat_seen


def print_grid(grid, title):
    print(f"\n--- {title} ---")
    for latflag in (True, False):
        rows = {b: grid[(latflag, b)] for b in ORDER if grid.get((latflag, b))}
        if not rows:
            continue
        print(f"  latActive={latflag}:")
        print(f"    {'speed(mph)':>12} {'n':>7}   " + "  ".join(f"ST={k}" for k in sorted(STATUS_NAMES)))
        for b in ORDER:
            c = rows.get(b)
            if not c:
                continue
            tot = sum(c.values())
            cells = "  ".join(f"{100*c.get(k,0)/tot:5.1f}%" for k in sorted(STATUS_NAMES))
            print(f"    {b:>12} {tot:>7}   {cells}")


def main():
    flat, nested = find_all_rlogs()
    print(f"flat routes (analysis-2020accord/rlogs/*.zst): {len(flat)} files")
    print(f"nested routes (manual/…/rlog.zst etc.): {len(nested)} files")

    # group flat files by route prefix (everything before the last "--N--rlog.zst" segment index)
    def route_key(p):
        name = p.stem  # strip .zst -> ...--rlog
        parts = name.split("--")
        # typical: <dongle>_<routeid>--<segstr>--<segidx>--rlog  (variable format; just drop last 2 tokens if numeric-ish)
        return "--".join(parts[:-2]) if len(parts) >= 3 else name

    groups = collections.defaultdict(list)
    for p in flat:
        groups[route_key(p)].append(p)
    for p in nested:
        # .../manual/<dongle>/<routeid>--<hash>--<seg>/rlog.zst
        route_id = p.parent.parent.name
        groups[f"manual/{route_id}"].append(p)

    grand = collections.defaultdict(collections.Counter)
    grand_n399 = 0
    grand_bad = 0
    any_lat_true = False

    for key in sorted(groups):
        paths = sorted(groups[key])
        grid, n399, chk_bad, lat_seen = process_route(paths, key)
        if n399 == 0:
            print(f"\n[{key}] {len(paths)} segs -- no CAN-399 EPS frames (src=1) found, skipping")
            continue
        print(f"\n[{key}] {len(paths)} segs, n399={n399} (chk_bad={chk_bad}), latActive seen={lat_seen}")
        print_grid(grid, key)
        for k, v in grid.items():
            grand[k].update(v)
            any_lat_true = any_lat_true or (k[0] is True and sum(v.values()) > 0)
        grand_n399 += n399
        grand_bad += chk_bad

    print("\n" + "=" * 100)
    print(f"GRAND TOTAL n399={grand_n399} (chk_bad={grand_bad})")
    print_grid(grand, "GRAND TOTAL (all routes combined)")

    # Decisive-test summary
    print("\n" + "=" * 100)
    print("DECISIVE-TEST SUMMARY")
    lowest_normal = None
    lowest_lockout_engaged = None
    highest_lockout_disengaged = None
    for b in ORDER:
        for latflag in (True, False):
            c = grand.get((latflag, b))
            if not c:
                continue
            if c.get(0, 0) > 0 and lowest_normal is None:
                lowest_normal = (b, latflag)
            if latflag is True and c.get(3, 0) > 0 and lowest_lockout_engaged is None:
                lowest_lockout_engaged = b
            if latflag is False and c.get(3, 0) > 0:
                highest_lockout_disengaged = b  # keep overwriting -> ends at highest bucket seen
    print(f"Lowest speed bucket where STEER_STATUS==NORMAL(0) observed: {lowest_normal}")
    print(f"Lowest speed bucket where STEER_STATUS==LOW_SPEED_LOCKOUT(3) while latActive=True: {lowest_lockout_engaged}")
    print(f"Highest speed bucket where STEER_STATUS==LOW_SPEED_LOCKOUT(3) while latActive=False: {highest_lockout_disengaged}")
    print(f"Any latActive=True samples seen at all: {any_lat_true}")


if __name__ == "__main__":
    main()
