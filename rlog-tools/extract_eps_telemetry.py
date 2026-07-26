#!/usr/bin/env python3
"""extract_eps_telemetry.py -- pull EPS gentle-EME gate-firing telemetry (+ steering context)
from a StarPilot rlog into a CSV for finding which gate fires at each ~90 ms cut.

The StarPilot fork logs the `epsTelemetry` service (cereal/custom.capnp EpsTelemetry) at the
CAN-330 rate (~100 Hz). Each sample is decoded from CAN 330 (0x14A) spare bits that the V31P-V2
EPS firmware (39990-TVA-A160) piggybacks -- NOT UDS (V31P-V2 needs no CAN TX / UDS / OBD mux):

    byte4 bit3 engageSmCut     decider FUN_00040d58 voterMax >= 320 (cal 0xC6312)
    byte4 bit4 voterAvg        deliver-commit voterAvg >= 320 (cal 0xC62FE)
    byte4 bit5 gate5Torque     deliver-commit |colTorque| >= 4096 (cal 0xC61EA)
    byte4 bit6 angleDb         FUN_0003c7fc angle deadband > 4825 (cal 0xC6354)
    byte4 bit7 rateGate        decider rate >= 1600 (cal 0xC6310)
    byte7 bit6 angleConsensus  decider r12==4 angle-consensus gate (V34 target)   [V31P-V2]
    byte7 bit7 hardCut         gp-0x676e==4 all-3-phase motor disable = HARD cut  [V31P-V2]

This emits long-form rows (one per event, native rate) time-indexed by logMonoTime, so the
gate flags line up with the comma-visible steering signals in the same rlog. NOTE: anchor the
gentle-EME cut on raw CAN 399 STEER_STATUS=no_torque_alert_2 (the fork's cs.steeringTorqueEps /
raw 427 MOTOR_TORQUE are ~0 on Honda and do NOT track the cut).

    src=eps : engage_sm_cut, voter_avg, gate5_torque, angle_db, rate_gate,
              angle_consensus, hard_cut, byte4, byte7
    src=cs  : steering angle, driver torque, EPS torque(=0), steer faults, v_ego
    src=cc  : latActive / longActive / enabled

Usage:
    python extract_eps_telemetry.py RLOG [RLOG ...] -o out.csv
    python extract_eps_telemetry.py "<route>--*/rlog.zst" -o eme.csv
    python extract_eps_telemetry.py --eps-only rlog.zst -o eps.csv

Requires only the local rlog_parse.py (cereal schema + pycapnp + zstandard).
"""
import argparse
import csv
import glob
import sys
from pathlib import Path

import capnp  # noqa: F401  (imported so we can catch capnp.KjException on truncated logs)

from rlog_parse import read_messages

COLUMNS = [
    "t_ns", "t_s", "src", "file",
    # eps (V31P-V2 gate-firing flags decoded from CAN 330 spare bits)
    "engage_sm_cut", "voter_avg", "gate5_torque", "angle_db", "rate_gate",
    "angle_consensus", "hard_cut", "byte4", "byte7",
    # cs
    "str_angle_meas", "str_torque_driver", "str_torque_eps", "str_pressed",
    "steer_fault_temp", "steer_fault_perm", "v_ego",
    # cc
    "lat_active", "long_active", "enabled",
]


def iter_rows(rlog_path: Path, eps_only: bool):
    """Yield row dicts for one rlog file. Tolerates a truncated final segment."""
    it = read_messages(rlog_path)
    while True:
        try:
            evt = next(it)
        except StopIteration:
            break
        except capnp.KjException:
            # final segment of a route can be truncated mid-write
            break

        w = evt.which()
        t = evt.logMonoTime

        if w == "epsTelemetry":
            e = evt.epsTelemetry
            yield {
                "t_ns": t, "src": "eps",
                "engage_sm_cut": int(e.engageSmCut), "voter_avg": int(e.voterAvg),
                "gate5_torque": int(e.gate5Torque), "angle_db": int(e.angleDb),
                "rate_gate": int(e.rateGate),
                "angle_consensus": int(e.angleConsensus), "hard_cut": int(e.hardCut),
                "byte4": f"0x{e.byte4:02X}", "byte7": f"0x{e.byte7:02X}",
            }
        elif not eps_only and w == "carState":
            cs = evt.carState
            yield {
                "t_ns": t, "src": "cs",
                "str_angle_meas": cs.steeringAngleDeg,
                "str_torque_driver": cs.steeringTorque,
                "str_torque_eps": cs.steeringTorqueEps,
                "str_pressed": bool(cs.steeringPressed),
                "steer_fault_temp": bool(cs.steerFaultTemporary),
                "steer_fault_perm": bool(cs.steerFaultPermanent),
                "v_ego": cs.vEgo,
            }
        elif not eps_only and w == "carControl":
            cc = evt.carControl
            yield {
                "t_ns": t, "src": "cc",
                "lat_active": bool(cc.latActive),
                "long_active": bool(cc.longActive),
                "enabled": bool(cc.enabled),
            }


def main():
    ap = argparse.ArgumentParser(description="Extract EPS gentle-EME UDS telemetry from rlogs to CSV.")
    ap.add_argument("rlogs", nargs="+", help="rlog(.zst) files or globs (e.g. 'route--*/rlog.zst')")
    ap.add_argument("-o", "--out", default="eps_telemetry.csv", help="output CSV path")
    ap.add_argument("--eps-only", action="store_true", help="only emit epsTelemetry rows (skip cs/cc)")
    args = ap.parse_args()

    # expand globs (and accept already-expanded shell args)
    paths: list[Path] = []
    for pat in args.rlogs:
        hits = [Path(p) for p in glob.glob(pat)]
        paths.extend(hits if hits else ([Path(pat)] if Path(pat).exists() else []))
    if not paths:
        print("[error] no rlog files matched", file=sys.stderr)
        return 2
    paths.sort()

    rows = []
    t0 = None
    counts = {"eps": 0, "cs": 0, "cc": 0}
    gate_keys = ("engage_sm_cut", "voter_avg", "gate5_torque", "angle_db",
                 "rate_gate", "angle_consensus", "hard_cut")
    gate_counts = {k: 0 for k in gate_keys}
    for p in paths:
        n_before = len(rows)
        try:
            for row in iter_rows(p, args.eps_only):
                if t0 is None:
                    t0 = row["t_ns"]
                row["t_s"] = (row["t_ns"] - t0) / 1e9
                row["file"] = p.name
                counts[row["src"]] = counts.get(row["src"], 0) + 1
                if row["src"] == "eps":
                    for k in gate_keys:
                        if row.get(k):
                            gate_counts[k] += 1
                rows.append(row)
        except Exception as e:  # keep whatever parsed before a hard failure
            print(f"[warn] {p.name}: stopped early ({type(e).__name__}: {e})", file=sys.stderr)
        print(f"[read] {p.name}: {len(rows) - n_before} rows")

    rows.sort(key=lambda r: r["t_ns"])
    out = Path(args.out)
    with out.open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        wr.writeheader()
        wr.writerows(rows)

    print(f"[done] wrote {out}  ({len(rows):,} rows)")
    print(f"       eps={counts['eps']}  cs={counts['cs']}  cc={counts['cc']}")
    if counts["eps"]:
        print("       gate-flag set-counts: " +
              ", ".join(f"{k}={v}" for k, v in gate_counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
