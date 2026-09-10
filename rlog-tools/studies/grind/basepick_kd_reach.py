# -*- coding: utf-8 -*-
"""studies/grind/basepick_kd_reach.py -- HOW MUCH OF THE MEASURED GRINDING POPULATION DOES A SCHEDULED Kd
ACTUALLY REACH?  Agent `basepick`, 2026-09-09.  Analysis only: builds nothing, flashes nothing, sends nothing.

The Kd record 0xE511C is X = (0, 11, 22, 32), and `0x29EA0` clamps the lookup at X[3] = 32, so a Y-only edit
(row S: Y[0..2] = 96, Y[3] = 128) delivers its full cut only below idx 22 and NOTHING above idx 32.  The
measured demand-index populations say cruise lives at idx p50 3 but GRINDING EPISODES sit at p50 8-46 with
56-67 % of their time above idx 32.  This script computes the DELIVERED Kd(t) distribution per regime, for
row S and for X-extended variants, straight off the wire, using `reqaxis`'s byte-exact demand() mirror.

Run:  python basepick_kd_reach.py     -> _scratch/basepick_kd_reach.txt
"""
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import kpkd_axis_r62_r63 as AX                # noqa: E402  (reqaxis's byte-exact demand mirror)
import creep20_loop_id as C20                 # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def kd_of(idx, X, Y):
    """the firmware LERP with the X[n-1] high clamp (0x29EA0), evaluated on a float idx array."""
    return np.interp(np.clip(idx, X[0], X[-1]), X, Y)


VARIANTS = [
    ("V282/V289 stock       Y=(128,128,128,128) X=(0,11,22,32)", (0, 11, 22, 32), (128, 128, 128, 128)),
    ("row S  (A / B / D)    Y=(96,96,96,128)    X=(0,11,22,32)", (0, 11, 22, 32), (96, 96, 96, 128)),
    ("row S' (A'/ B'/ D')   Y=(112,112,112,128) X=(0,11,22,32)", (0, 11, 22, 32), (112, 112, 112, 128)),
    ("paramod M1            Y=(96,96,112,128)   X=(0,11,22,32)", (0, 11, 22, 32), (96, 96, 112, 128)),
    ("X-EXTENDED  X[3]=64   Y=(96,96,96,128)    X=(0,11,22,64)", (0, 11, 22, 64), (96, 96, 96, 128)),
    ("X-EXTENDED  X[3]=96   Y=(96,96,96,128)    X=(0,11,22,96)", (0, 11, 22, 96), (96, 96, 96, 128)),
    ("X-EXTENDED  X[3]=128  Y=(96,96,96,128)    X=(0,11,22,128)", (0, 11, 22, 128), (96, 96, 96, 128)),
    ("X-EXTENDED  X[3]=240  Y=(96,96,96,128)    X=(0,11,22,240)", (0, 11, 22, 240), (96, 96, 96, 128)),
]


def main():
    C = {n: AX.cells(n) for n in AX.IMGS}
    tags = ["r62_v289", "r63_v289", "r5e_v288"]
    P = pickle.load(open(AX.CENSUS_PKL, "rb")) if os.path.exists(AX.CENSUS_PKL) else {"episodes": []}
    ep = {}
    for e in P["episodes"]:
        ep.setdefault(e["tag"], []).append(e)

    pr("basepick_kd_reach -- DELIVERED Kd per regime, straight off the wire (reqaxis's byte-exact demand mirror).")
    pr("  The 7 Hz gate and the capped-step pkR are read at the DELIVERED Kd of their own regime, not at Kd = Y[0].")
    pr("")
    rows = {}
    for tag in tags:
        g = C20.load(tag)
        c = C[AX.TAG_IMG[tag]]
        idx, _, _ = AX.demand(np.round(g["cmd"]), g["bar"], c)
        eng = g["eng"]; v = g["vego"]; ang = np.abs(g["ang"])
        dcmd = np.abs(np.r_[0.0, np.diff(np.round(g["cmd"]))])
        reg = {
            "ALL engaged": eng,
            "cruise v>=22, |ang|<5": eng & (v >= 22) & (ang < 5),
            "capped step |dcmd|>=122": eng & (dcmd >= 122),
            "full-lock turn 2-5 m/s": eng & (v >= 2) & (v <= 5) & (ang >= 70) & (ang <= 140),
        }
        if tag in ep:
            m = np.zeros(len(g["t"]), bool)
            for e in ep[tag]:
                m[int(e["a"]):int(e["b"])] = True
            reg["GRINDING episodes"] = eng & m
        pr("=" * 150)
        pr("%s" % tag)
        pr("  %-58s | %s" % ("variant", "  ".join("%-24s" % k for k in reg)))
        pr("  %-58s | %s" % ("", "  ".join("%-24s" % "mean Kd | frac at Y[0]" for k in reg)))
        for lab, X, Y in VARIANTS:
            cells = []
            for k, m in reg.items():
                if m.sum() < 50:
                    cells.append("%-24s" % "   (too little)"); continue
                kd = kd_of(idx[m].astype(float), np.array(X, float), np.array(Y, float))
                cells.append("%9.1f | %12.3f" % (kd.mean(), float(np.mean(kd <= Y[0] + 0.01))))
                rows.setdefault((tag, lab, k), (float(kd.mean()), float(np.mean(kd <= Y[0] + 0.01))))
            pr("  %-58s | %s" % (lab, "  ".join(cells)))
        pr("")
    p = os.path.join(HERE, "_scratch", "basepick_kd_reach.txt")
    open(p, "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    print("\nwritten: %s" % p)


if __name__ == "__main__":
    main()
