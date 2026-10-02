# -*- coding: utf-8 -*-
r"""d4_gate2.py -- DESIGNER D4: GATE 2 (PM, GM-up, Ms = max|S|) per operating point, on the INDEPENDENT C3-r1 stability
model (refute_stability/c3r1/c3r1_model.py: exact sampled-data plant channels, the 100 Hz hold, the EMA, the output lag,
the fade) -- for V298's loop (= D4 (a) and (b): their edits are hand-rule nonlinearities and leave both linear states,
PID and I-frozen PD, byte-identical) and for the REJECTED-OR-OPTIONAL stiffness variant GB-S13 (the 10 / 11.75 / 17.5
m/s knots x1.3).  Also the curve-hold OPERATING-POINT form (rb_opbreak: the plant spring softened by the tyre
saturation at lateral acceleration a = 1.5 / 2.5 m/s^2).  Analysis only.  Writes _scratch/v299_D4/gate2.{json,txt}.
usage: python d4_gate2.py [procs]      (wall time printed; target < 30 s)
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
KIT = AL.parents[2]
OUT = KIT / "_scratch" / "v299_D4"
sys.path.insert(0, str(AL / "refute_stability" / "c3r1"))
sys.path.insert(0, str(AL / "c3" / "rev2B"))
import c3r1_model as M  # noqa: E402
import rb_table as TB  # noqa: E402

GBP = tuple(TB.GB_P)


def scaled(rows, idx, fac):
    """multiply the G of knot rows idx by fac and recompute every Q12 slope S(i) = (G(i+1) - G(i)) 4096 / (X(i+1) - X(i))
    (rounded to nearest: reproduces GB-P exactly, the control below)."""
    X = [r[0] for r in rows]
    G = [int(round(r[1] * (fac if i in idx else 1.0))) for i, r in enumerate(rows)]
    out = []
    for i in range(len(rows)):
        if i + 1 < len(rows) and X[i + 1] != 0xFFFF:
            S = int(round((G[i + 1] - G[i]) * 4096 / (X[i + 1] - X[i])))
        else:
            S = 0
        out.append((X[i], G[i], S))
    return tuple(out)


# control: the scaled() slope rule reproduces GB-P itself
_ctl = scaled(GBP, (), 1.0)
DES = {"V298": M.Design("V298", "fresh", kd=48, ki=40, rows=GBP),
       "GB-S13": M.Design("GB-S13", "fresh", kd=48, ki=40, rows=scaled(GBP, (2, 3, 4), 1.3))}
MEMS = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6", "b_lo*J_hi", "b_lo*tau6", "J1.0", "b_q", "b_q*J_hi",
        "ms_free")
SINGLE = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6", "ms_free")
FR = (("nom", 1.0, 1.0), ("FA.83", 0.83, 1.0), ("FA1.155", 1.155, 1.0))
SP = (3.1, 5.0, 8.0, 10.0, 11.75, 13.0, 15.0, 17.5, 20.0, 22.0, 26.9)
F = np.unique(np.concatenate([np.logspace(-2.0, math.log10(400.0), 500), [5, 7, 10, 13, 16, 20, 25]]))
SR, LWB = 16.0, 2.83


def work(args):
    mem, v = args
    res = []
    for a in (0.0, 1.5, 2.5):
        s2 = 1.0 if a == 0 else 1 - math.tanh(SR * LWB * a / (v * v) * 180 / math.pi /
                                              (19.3 + 546 * math.exp(-v / 3.01))) ** 2
        pl = M.member(mem, v)
        pl.k *= s2
        for fn, kap, jb in FR:
            Pt, Pw = M.plant_channels(pl, F, jb, 0.0)
            for dn, des in DES.items():
                for e in (0, 10):
                    for noI in (False, True):
                        Cth, Cw, Cref = M.controller(des, v, F, e, kap, noI)
                        K = M.Kout(F)
                        L = -K * (Cth * Pt + Cw * Pw)
                        PM, FC, GMu = M.pm_gm(L, F)
                        Ms = float(np.abs(1 / (1 + L)).max())
                        res.append(dict(d=dn, m=mem, v=v, a=a, fr=fn, e=e, loop="PD" if noI else "PID", PM=PM, fc=FC,
                                        GMu=GMu, Ms=Ms))
    return res


def bar(mem, e):
    return (45.0 if e == 0 else 30.0) if mem in SINGLE and mem != "ms_free" else 30.0


def main():
    t0 = time.time()
    procs = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    print("control: scaled(GB-P, none) == GB-P:", _ctl == GBP, "| GB-S13 rows:", DES["GB-S13"].rows)
    with Pool(procs) as pool:
        R = [r for rr in pool.map(work, [(m, v) for m in MEMS for v in SP], chunksize=1) for r in rr]
    lines = []

    def P(s=""):
        print(s)
        lines.append(s)
    P("GATE 2 per operating point (independent c3r1 model). cell = min PM deg / min GM-up dB / max Ms over members x frames"
      " (nom, FA.83, FA1.155) x ages (0, 10); bar 45 deg single members age 0, 30 otherwise; ms_free reported apart")
    for loop in ("PID", "PD"):
        for a in (0.0, 1.5, 2.5):
            P("\n-- loop %s, curve-hold a = %.1f m/s^2 (a = 0: straight) --" % (loop, a))
            P("   speed | " + " | ".join("%-28s" % dn for dn in DES) + " | binding member (V298)")
            for v in SP:
                cells = []
                bind = ""
                for dn in DES:
                    X = [r for r in R if r["d"] == dn and r["v"] == v and r["a"] == a and r["loop"] == loop
                         and r["m"] != "ms_free"]
                    pm = min(r["PM"] for r in X)
                    gm = min(r["GMu"] for r in X)
                    ms = max(r["Ms"] for r in X)
                    nf = sum(r["PM"] < bar(r["m"], r["e"]) for r in X)
                    cells.append("%5.1f / %5.1f / %4.2f fails %2d" % (pm, gm, ms, nf))
                    if dn == "V298":
                        w = min(X, key=lambda r: r["PM"] - bar(r["m"], r["e"]))
                        bind = "%s %s e%d (PM %.1f)" % (w["m"], w["fr"], w["e"], w["PM"])
                P("   %5.2f | " % v + " | ".join(cells) + " | " + bind)
    P("\nms_free (BELIEF-disfavoured family, report only): min PM over speeds, PID a=0 / a=2.5")
    for dn in DES:
        for a in (0.0, 2.5):
            X = [r for r in R if r["d"] == dn and r["a"] == a and r["loop"] == "PID" and r["m"] == "ms_free"]
            w = min(X, key=lambda r: r["PM"])
            P("   %-7s a=%.1f: %5.1f at %.2f m/s %s e%d" % (dn, a, w["PM"], w["v"], w["fr"], w["e"]))
    P("\nWALL %.1f s" % (time.time() - t0))
    (OUT / "gate2.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    json.dump(R, open(OUT / "gate2.json", "w"))


if __name__ == "__main__":
    main()
