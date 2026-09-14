# -*- coding: utf-8 -*-
"""v293_ident_surface.py -- tabulate the V293 delivered-torque surface T(idx) from the GOLDEN MODEL's
byte-exact march, so the plant identification has a predicted `u` to compare the 427 tap against.

ANALYSIS ONLY.  Reads the model, writes a json table into _scratch.  Subagent v293plant, 2026-09-13.

The V293 cal set is the one `_self_check_v293()` in eps_chain_control.py builds and asserts:
    replace(Calibration(), fb_clamp=0, kd_y=(0,0,0,0), pid_d_clamp=0, kp_y=(120,)*5)
with `Calibration()`'s defaults BEING V282 read from its image.  `Calibration.for_build` only knows
V9..V57, so it cannot be used here.

Output: _scratch/v293_surface.json  with T(idx) at fade 254 (the at-rest / hands-off taper) for
idx 0..320, plus the V282 surface on the same axis for contrast.
"""
import json
import os
import sys

from dataclasses import replace

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "model"))
OUT = os.path.join(HERE, "_scratch")

import eps_lkas_chain_model as M  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

V282 = M.Calibration()
V293 = replace(M.Calibration(), fb_clamp=0, kd_y=(0, 0, 0, 0), pid_d_clamp=0, kp_y=(120,) * 5)

IDX = list(range(0, 321))
tab = {"idx": IDX}
for name, cal in (("V293", V293), ("V282", V282)):
    T, sp = [], []
    for i in IDX:
        s = M.lkas_rate_pid_surface(i, cal, fb=0, pol=1, taper=254)
        T.append(int(s["T"])); sp.append(int(s["sp"]))
    tab[name + "_T"] = T
    tab[name + "_sp"] = sp

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "v293_surface.json"), "w") as fh:
    json.dump(tab, fh)

print("idx    sp   V293_T   V282_T     dT/didx(V293)")
prev = None
for i in IDX:
    if i % 16 == 0 or i in (1, 2, 3, 4, 8, 239, 240, 241):
        sl = "" if prev is None else "  %.3f" % ((tab["V293_T"][i] - prev[1]) / float(i - prev[0]))
        print("%4d %5d %8d %8d %s" % (i, tab["V293_sp"][i], tab["V293_T"][i], tab["V282_T"][i], sl))
        prev = (i, tab["V293_T"][i])
print("\nV293 rail %d at idx %d ; V282 rail %d at idx %d"
      % (max(tab["V293_T"]), tab["V293_T"].index(max(tab["V293_T"])),
         max(tab["V282_T"]), tab["V282_T"].index(max(tab["V282_T"]))))
# slope in the linear region, least squares over idx 10..200
import numpy as np  # noqa: E402
x = np.array(IDX[10:201], float); y = np.array(tab["V293_T"][10:201], float)
A = np.vstack([x, np.ones_like(x)]).T
m, b = np.linalg.lstsq(A, y, rcond=None)[0]
print("V293 linear region (idx 10..200): T = %.4f*idx %+.2f   (record quotes 10.34/idx)" % (m, b))
y2 = np.array(tab["V282_T"][10:201], float)
m2, b2 = np.linalg.lstsq(A, y2, rcond=None)[0]
print("V282 same region:                 T = %.4f*idx %+.2f" % (m2, b2))
