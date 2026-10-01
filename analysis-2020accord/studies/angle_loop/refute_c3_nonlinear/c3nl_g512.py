# -*- coding: utf-8 -*-
r"""c3nl_g512.py -- attribution of the 11.4-12.2 m/s small-signal collapse to the integer I quantum: with G < 512,
e5 = ((E*G) >> 8) >> 5 is 0 for a +1-count (0.1 deg) error but -1 for a -1-count error (sar floors).  Control columns:
C3-P with its G floored at 512 ('C3-P/G>=512'), C3-P with G raised by +0 elsewhere (unchanged), and P2 with its G
lowered to C3-P's 463 at the dip ('P2/G463').  ANALYSIS ONLY.  usage: python c3nl_g512.py"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c3nl_sim as S  # noqa: E402
import c3nl_lens as L  # noqa: E402

# derived implementations (only the G LUT differs)
S.IMPL["C3-P/G>=512"] = dict(S.IMPL["C3-P"], glut=np.maximum(S.IMPL["C3-P"]["glut"], 512))
S.IMPL["P2/G463"] = dict(S.IMPL["P2"], glut=np.where((np.arange(65536) >= 2620) & (np.arange(65536) <= 2814),
                                                      np.minimum(S.IMPL["P2"]["glut"], 463), S.IMPL["P2"]["glut"]))
IM = ("C3-P", "C3-P/G>=512", "P2", "P2/G463")
SP = (11.0, 11.5, 11.75, 12.0, 12.5)


def main():
    # arithmetic: e5 for +-1 and +-2 counts at the dip G
    for G in (463, 511, 512, 537):
        e = {k: ((k * 16 * G) >> 8) >> 5 for k in (-2, -1, 1, 2)}
        print(f"G {G}: e5 for error -2/-1/+1/+2 counts = {e[-2]}/{e[-1]}/{e[1]}/{e[2]}")
    for scn in ("small_0.3_0.1", "small_0.5_0.2", "small_1_0.3"):
        for mb in ("F_hi", "bc"):
            cols = [dict(impl=i, member=mb, v=v) for v in SP for i in IM]
            s, meta = L.build(scn, cols)
            r = S.run(cols, s)
            m = L.metrics(scn, meta, r, cols)
            print(f"== {scn} {mb}: in-phase gain / dwell events")
            for v in SP:
                row = []
                for i in IM:
                    j = [k for k, c in enumerate(cols) if c["impl"] == i and c["v"] == v][0]
                    row.append(f"{i:12s} {m['gain'][j]:6.2f} dj {m['dj'][j]:3.0f}")
                print(f"  v {v:5.2f}: " + " | ".join(row))


if __name__ == "__main__":
    main()
