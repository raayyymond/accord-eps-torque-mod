# -*- coding: utf-8 -*-
r"""op_signed_arb.py -- JUDGE OPERABILITY (panel 2, 2026-10-01): does a SIGNED angle-referenced I bound fix the
cross-centre override that the unsigned ARB (E2-A2/A3) leaves open, and what does it cost on a straight with a constant
road torque (crown / crosswind)?  The two cases are the same geometry from the bound's point of view (an external
torque holds the wheel on the far side of centre from where the I pushes); this run measures both.

ANALYSIS ONLY.  Monkeypatches ONE line of panel2/score_time.CandLane.cave_stage for columns whose id ends in 's':
    unsigned (E2's bytes):  bound = (|theta| << sh) + B
    signed  (hypothetical): bound = (max(0, sgn(E') * theta) << sh) + B
Everything else is the scorer's lane unchanged.  Positive control: the unsigned columns must reproduce op_probe.py.
The signed variant has NO bytes (BELIEF: about the same size as E2's |theta| block).

usage: python op_signed_arb.py -> prints the table (copied into JUDGE-operability §5)
"""
from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import op_probe as OP  # noqa: E402  (loads panel2/score_time.py as p2_score_time)

ST = OP.ST
_orig_init = ST.CandLane.__init__
_orig_stage = ST.CandLane.cave_stage


def _init(self, cands, vw):
    _orig_init(self, cands, vw)
    self._signed = np.array([c.id.endswith("s") and c.arb is not None for c in cands])


def _stage(self, sp, r26, ramp, a6a00, abe, tq, I8, Eprev, bxC, bxW):
    if not self._signed.any():
        return _orig_stage(self, sp, r26, ramp, a6a00, abe, tq, I8, Eprev, bxC, bxW)
    E = ST.s32((sp << 2) - r26)
    Ep = ST.s32(E * self.G) >> 8
    th6 = ST.s16(a6a00)
    th_signed = np.maximum(np.where(Ep >= 0, th6, -th6), 0)
    a_eff = np.where(self._signed, np.where(th_signed >= 0, th_signed, 0), np.abs(th6))
    # feed the stage a substitute angle whose |.| equals the signed quantity on signed columns (the angle is read by
    # the stage ONLY for the bound and for box10, which no ARB column uses)
    a_sub = np.where(self._signed, a_eff, th6)
    return _orig_stage(self, sp, r26, ramp, a_sub, abe, tq, I8, Eprev, bxC, bxW)


ST.CandLane.__init__ = _init
ST.CandLane.cave_stage = _stage

for base in ("E2-A3", "E2-A2"):
    ST.CBYID[base + "s"] = replace(ST.CBYID[base], id=base + "s", hexsrc=None, note="signed ARB (hypothetical)")
CANDS = ["P2", "E2-A3", "E2-A3s", "E2-A2", "E2-A2s", "E1-cal"]
OP.CANDS = CANDS

if __name__ == "__main__":
    res = OP.main(["ctl_lt400", "xc_lt400", "xc_fm2400", "crown_300", "crown_450"], tag="op_signed_arb")
    for scn, key in (("ctl_lt400", "lurch"), ("xc_lt400", "lurch"), ("xc_fm2400", "lurch"), ("crown_300", "err"),
                     ("crown_450", "err")):
        print(f"\n## {scn}.{key}: worst over nominal / b_lo*J_hi; bands <8 | 8-12.5 | 12.5-22 | >22")
        for c in CANDS:
            cells = []
            for lo, hi in ((0, 7.99), (8, 12.5), (12.51, 22), (22.01, 99)):
                v = [r[key] for r in res[scn] if r["cid"] == c and lo <= r["v"] <= hi]
                cells.append(f"{max(v):.2f}" if v else "-")
            print(f"| {c} | " + " | ".join(cells) + " |")
