# -*- coding: utf-8 -*-
"""c1_handsoff_torque.py -- where does the C1 freeze threshold (|gp-0x4f68| > 512 internal = ~500 on the 0x18F wire)
sit against the driver-torque word the car actually produces while lateral is engaged?  Reads carState.steeringTorque
(the 0x18F STEER_TORQUE_SENSOR wire value, = -1.024 x gp-0x4f60 / ... the kit's wire = raw x 1.024 memory),
carState.steeringPressed / steeringRateDeg / vEgo and carControl.latActive from local rlogs.  EVIDENCE for the
distribution on the routes read; BELIEF that it transfers to the angle build (the wheel's own inertia reaction is the
build-dependent part, so it is reported against |steering rate|).
usage: python c1_handsoff_torque.py <route-prefix> [n_segments]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[3]
sys.path.insert(0, str(KIT / "rlog-tools" / "lib"))
import rlog_parse as RP  # noqa: E402

RL = KIT / "analysis-2020accord" / "rlogs"


def main():
    pref = sys.argv[1]
    nseg = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    segs = sorted(RL.glob(pref + "--*--rlog.zst"), key=lambda p: int(p.name.split("--")[2]))[:nseg]
    rows = []
    for sp in segs:
        lat = False
        for e in RP.read_messages(sp):
            try:
                w = e.which()
            except Exception:
                continue
            if w == "carControl":
                lat = bool(e.carControl.latActive)
            elif w == "carState":
                cs = e.carState
                rows.append((lat, float(cs.steeringTorque), bool(cs.steeringPressed), float(cs.steeringRateDeg),
                             float(cs.vEgo)))
    a = np.array(rows, float)
    eng = a[:, 0] > 0
    tq = np.abs(a[:, 1]); pr = a[:, 2] > 0; rate = np.abs(a[:, 3]); v = a[:, 4]
    out = {"route": pref, "segments": [s.name for s in segs], "frames": int(len(a)), "engaged": int(eng.sum())}
    lines = [f"route {pref}, {len(segs)} segments, {len(a)} carState frames, {int(eng.sum())} with latActive"]
    m = eng & ~pr
    for lab, sel in (("engaged, not steeringPressed", m), ("engaged, all", eng)):
        q = np.percentile(tq[sel], [50, 90, 95, 99, 99.9]) if sel.any() else [np.nan] * 5
        frac = {thr: float(np.mean(tq[sel] > thr)) for thr in (250, 500, 700, 1000, 1200)}
        lines.append(f"  {lab:30s} n {int(sel.sum()):7d}  |wire| p50 {q[0]:.0f} p90 {q[1]:.0f} p95 {q[2]:.0f} p99 {q[3]:.0f} "
                     f"p99.9 {q[4]:.0f} | frac > 250/500/700/1000/1200: " + " ".join(f"{frac[t]:.4f}" for t in frac))
        out[lab] = dict(p=list(map(float, q)), frac=frac)
    for lo, hi in ((0, 10), (10, 30), (30, 60), (60, 1000)):
        sel = m & (rate >= lo) & (rate < hi)
        if sel.sum() > 50:
            q = np.percentile(tq[sel], [50, 95, 99])
            lines.append(f"  engaged & not pressed, |rate| {lo:3d}-{hi:4d} deg/s: n {int(sel.sum()):6d} |wire| p50 {q[0]:.0f} "
                         f"p95 {q[1]:.0f} p99 {q[2]:.0f} ; frac > 500 {np.mean(tq[sel] > 500):.4f}")
    for lo, hi in ((0, 5), (5, 10), (10, 20), (20, 40)):
        sel = m & (v >= lo) & (v < hi)
        if sel.sum() > 50:
            q = np.percentile(tq[sel], [50, 95, 99])
            lines.append(f"  engaged & not pressed, v {lo:2d}-{hi:2d} m/s: n {int(sel.sum()):6d} |wire| p50 {q[0]:.0f} p95 "
                         f"{q[1]:.0f} p99 {q[2]:.0f} ; frac > 500 {np.mean(tq[sel] > 500):.4f}")
    txt = "\n".join(lines)
    print(txt)
    (HERE / f"handsoff_torque_{pref.split('_')[1].split('--')[0][-2:]}.txt").write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    main()
