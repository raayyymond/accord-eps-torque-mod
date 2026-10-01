# -*- coding: utf-8 -*-
r"""e2_arb_slope.py -- the slope the angle-referenced I bound must have so a normal turn never binds it: for every
member the scorer gates (nominal / bc / F_hi / b_lo*J_hi), every speed, every wheel angle 0.5-90 deg, the I must carry
the spring k*sat*tanh(th/sat) plus static friction Fs, less what P carries at a 5 % error (Kp_eff = 112 G/256 at
0.1002 T per Kp_eff per deg, P2's table).  needed slope = max over th of (load - B)/th, B = 200 T.  Also the fade-arm
values the page quotes.  ANALYSIS ONLY."""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from e2_common import ST, R  # noqa: E402
import c1_lib as C  # noqa: E402
import harness_time as HT  # noqa: E402
from harness_time import vlerp  # noqa: E402

tbl = [tuple(r) for r in R.tables()["P2"]]
th = np.linspace(0.5, 90, 400)
L = ["v m/s | Kp_T T/deg | needed slope T/deg (nominal bc F_hi b_lo*J_hi) | A2 slope"]
for v in (3.1, 5, 6, 7, 8, 9, 10, 11, 11.75, 12.5, 13, 14, 15, 17, 19, 22, 26.9, 30):
    G = C.cave_G(C.spd_counts(v), tbl)
    KpT = 0.1002 * 112 * G / 256
    out = []
    for mem in ("nominal", "bc", "F_hi", "b_lo*J_hi"):
        p = ST.member(mem).at(v)
        req = p.k * p.sat * np.tanh(th / p.sat) + p.Fs - KpT * 0.05 * th
        out.append(max(0.0, ((req - 200.0) / th).max()))
    a2 = 0.160 * 10 * (16 if C.spd_counts(v) <= 2880 else 64)
    L.append(f"{v:5.2f} | {KpT:5.1f} | " + " ".join(f"{x:6.1f}" for x in out) + f" | {a2:.0f}")
cal = HT.base_cal()
for x in (16, 48, 64, 75, 80, 96, 112):
    f1 = int(vlerp(*cal["fadeB"], np.array([x]))[0])
    f2 = int(vlerp(*cal["fadeB2"], np.array([x]))[0])
    L.append(f"fade at |tq|>>5 = {x:3d} (raw {x * 32}): stock 0xCBBC4 {f1}/255 = {f1 / 255:.2f}; 6803==2 0xCBAE4 {f2}/255 = "
             f"{f2 / 255:.2f}; ratio {f2 / max(f1, 1):.2f}")
txt = "\n".join(L)
print(txt)
(HERE / "e2_arb_slope_out.txt").write_text(txt + "\n", encoding="utf-8")
