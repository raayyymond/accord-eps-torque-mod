# -*- coding: utf-8 -*-
"""studies/grind/basepick_delivered_dose.py -- IS THE Kd-SCHEDULE CLASS CAPPED?  Agent `basepick`, 2026-09-09.
Analysis only: builds nothing, flashes nothing, sends nothing.

`powerS` weighted the delivered Kd by grinding-episode SECONDS and found the car sees a mean delivered Kd of
112.8 on the V289 pool (x0.882 of base), not the nominal 96 (x0.75), because roughly half of grinding time
sits above idx 32 where row S's cells are byte-identical to base.  `paramod` then showed the brief's
"put the cut wholly below the band the rings visit" cannot be built, because the rings live on BOTH sides
of the ramp.  This file answers the question those two leave open:

    IS THERE ANY (Y, X) THAT REACHES A WORTHWHILE DELIVERED DOSE WHILE KEEPING THE AUTHORITY PROTECTION,
    OR IS THE SCHEDULE CLASS CAPPED AT ROUGHLY x0.88?

Method.  For each candidate record it computes, off the wire, the DELIVERED mean Kd in each regime
(grinding episodes / capped step / full-lock turn / cruise), then reads zeta, the ring time, the 7 Hz gate
and the capped-step pkR off `basepick_effective_kd.py`'s fine Kd curve AT THAT DELIVERED Kd.  Nothing is
scored at a nominal Y[0] anywhere in this file.

The protection is by construction only while X[3] stays at 32: above the top knot the cells are
byte-identical to base, so gate73 and pkR read at base.  MOVING X IS THE ONLY WAY TO REACH FURTHER, AND IT
SPENDS EXACTLY THAT PROTECTION -- that trade is what the X rows below price.

Run:  python basepick_delivered_dose.py   -> _scratch/basepick_delivered_dose.txt (+ .json)
"""
import json
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import kpkd_axis_r62_r63 as AX     # noqa: E402  (reqaxis's byte-exact demand mirror)
import creep20_loop_id as C20      # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


# ---- the candidate records ------------------------------------------------------------------------------
#  (label, X, Y, payload bytes, "protection by construction?" )
CANDS = [
    ("base            Y=(128,128,128,128) X=(0,11,22,32)", (0, 11, 22, 32), (128, 128, 128, 128), 0, True),
    ("S'  Y0=112      Y=(112,112,112,128) X=(0,11,22,32)", (0, 11, 22, 32), (112, 112, 112, 128), 6, True),
    ("S   Y0=96       Y=( 96, 96, 96,128) X=(0,11,22,32)", (0, 11, 22, 32), (96, 96, 96, 128), 6, True),
    ("M1  paramod     Y=( 96, 96,112,128) X=(0,11,22,32)", (0, 11, 22, 32), (96, 96, 112, 128), 6, True),
    ("M2  paramod     Y=( 96,104,116,128) X=(0,11,22,32)", (0, 11, 22, 32), (96, 104, 116, 128), 6, True),
    ("S80 deeper      Y=( 80, 80, 80,128) X=(0,11,22,32)", (0, 11, 22, 32), (80, 80, 80, 128), 6, True),
    ("S64 deepest     Y=( 64, 64, 64,128) X=(0,11,22,32)", (0, 11, 22, 32), (64, 64, 64, 128), 6, True),
    ("S0  Kd->0       Y=(  0,  0,  0,128) X=(0,11,22,32)", (0, 11, 22, 32), (0, 0, 0, 128), 6, True),
    ("X48 knot out    Y=( 96, 96, 96,128) X=(0,11,22,48)", (0, 11, 22, 48), (96, 96, 96, 128), 8, False),
    ("X64 knot out    Y=( 96, 96, 96,128) X=(0,11,22,64)", (0, 11, 22, 64), (96, 96, 96, 128), 8, False),
    ("X96 knot out    Y=( 96, 96, 96,128) X=(0,11,22,96)", (0, 11, 22, 96), (96, 96, 96, 128), 8, False),
    ("X240 knot out   Y=( 96, 96, 96,128) X=(0,11,22,240)", (0, 11, 22, 240), (96, 96, 96, 128), 8, False),
    ("X64+deep        Y=( 64, 64, 64,128) X=(0,11,22,64)", (0, 11, 22, 64), (64, 64, 64, 128), 8, False),
]


def kd_of(idx, X, Y):
    """the firmware LERP with the X[n-1] high clamp (0x29EA0)."""
    return np.interp(np.clip(idx, X[0], X[-1]), np.asarray(X, float), np.asarray(Y, float))


def ring(zeta, f):
    if not np.isfinite(zeta) or zeta <= 0:
        return np.nan, np.nan
    c = np.log(10) / (2 * np.pi * zeta)
    return c, 1e3 * c / f


def main():
    curves = json.load(open(os.path.join(SCR, "basepick_effective_kd.json")))
    key282 = [k for k in curves if k.startswith("A ")][0]
    keyC = [k for k in curves if k.startswith("D ")][0]

    def rd(key, col, kd):
        rows = curves[key]
        x = np.array([r["kd"] for r in rows], float)[::-1]
        y = np.array([r[col] for r in rows], float)[::-1]
        return float(np.interp(kd, x, y))

    # ---- the wire ---------------------------------------------------------------------------------------
    C = {n: AX.cells(n) for n in AX.IMGS}
    P = pickle.load(open(AX.CENSUS_PKL, "rb"))
    ep = {}
    for e in P["episodes"]:
        ep.setdefault(e["tag"], []).append(e)
    dt = 1.0 / FS
    W = {}
    for tag in ("r62_v289", "r63_v289", "r5e_v288"):
        g = C20.load(tag)
        idx, _, _ = AX.demand(np.round(g["cmd"]), g["bar"], C[AX.TAG_IMG[tag]])
        eng = g["eng"]; v = g["vego"]; ang = np.abs(g["ang"])
        dcmd = np.abs(np.r_[0.0, np.diff(np.round(g["cmd"]))])
        m = np.zeros(len(g["t"]), bool)
        for e in ep.get(tag, []):
            m[int(e["a"]):int(e["b"])] = True
        W[tag] = dict(idx=idx, grind=eng & m, step=eng & (dcmd >= 122),
                      lock=eng & (v >= 2) & (v <= 5) & (ang >= 70) & (ang <= 140),
                      cruise=eng & (v >= 22) & (ang < 5), eng=eng)
    # V289 POOL, episode-seconds weighted (powerS's statistic): r62 + r63 grinding samples concatenated
    pool289 = np.concatenate([W[t]["idx"][W[t]["grind"]] for t in ("r62_v289", "r63_v289")])

    pr("basepick_delivered_dose -- EVERY column read at the DELIVERED Kd, never at a nominal Y[0].")
    pr("  grinding-episode idx pooled over r62+r63 (the V289 pool, episode-seconds weighted): n = %d samples = %.1f s"
       % (len(pool289), len(pool289) * dt))
    pr("  Protection column: 'byte-id' = cells byte-identical to base above idx 32, so gate73/pkR are base by")
    pr("  CONSTRUCTION.  'SPENT' = X moved, so the full-lock and capped-step regimes see a reduced Kd.")
    pr("")
    H = ("  %-52s %3s %-8s | %6s %6s | %7s %7s %7s | %7s | %7s %7s | %6s")
    pr(H % ("record", "B", "protect", "dlv289", "dlvGrn", "z_w", "z_med", "ring ms", "cyc", "gate73", "pkR_m", "x base"))
    pr("  " + "-" * 152)
    res = []
    for lab, X, Y, nb, prot in CANDS:
        kd289 = float(kd_of(pool289.astype(float), X, Y).mean())
        grn = [float(kd_of(W[t]["idx"][W[t]["grind"]].astype(float), X, Y).mean()) for t in W]
        lock = [float(kd_of(W[t]["idx"][W[t]["lock"]].astype(float), X, Y).mean()) for t in W]
        step = [float(kd_of(W[t]["idx"][W[t]["step"]].astype(float), X, Y).mean()) for t in W]
        crz = [float(kd_of(W[t]["idx"][W[t]["cruise"]].astype(float), X, Y).mean()) for t in W]
        zw = rd(key282, "z_w", kd289); zm = rd(key282, "z_med", kd289); fm = rd(key282, "f_med", kd289)
        cyc, ms = ring(zm, fm)
        gate = max(rd(key282, "gate", k) for k in lock)          # worst of the three routes
        pk = min(rd(key282, "pkR_med", k) for k in step)
        res.append(dict(lab=lab, X=X, Y=Y, bytes=nb, prot=prot, kd289=kd289, grn=grn, lock=lock, step=step,
                        cruise=crz, z_w=zw, z_med=zm, ring_ms=ms, ring_cyc=cyc, gate=gate, pkR=pk))
        pr(H % (lab, nb, "byte-id" if prot else "SPENT", "%.1f" % kd289, "%.0f/%.0f/%.0f" % tuple(grn),
                "%+.4f" % zw, "%+.4f" % zm, "%.0f" % ms, "%.1f" % cyc,
                "%.4f" % gate, "%.3f" % pk, "%.3f" % (kd289 / 128.0)))

    # ---- what the NOMINAL reading would have said, for contrast ----------------------------------------
    pr("")
    pr("  For contrast -- the NOMINAL reading the earlier tables used (score at Y[0], authority at Y[3]):")
    for lab, X, Y, nb, prot in CANDS[1:4] + [CANDS[6]]:
        zm = rd(key282, "z_med", Y[0]); fm = rd(key282, "f_med", Y[0])
        cyc, ms = ring(zm, fm)
        pr("    %-52s nominal Kd %3d -> z_med %+.4f, ring %.0f ms (%.1f cyc), gate73 %.4f (WRONG on both sides)"
           % (lab, Y[0], zm, ms, cyc, rd(key282, "gate", Y[0])))

    # ---- the same rows on the C base (option D) ---------------------------------------------------------
    pr("")
    pr("  THE SAME RECORDS ON THE C BASE (option D = feedback-operand notch 21.5 Q1.5 + fb 40 + the schedule):")
    pr("  The notch acts on EVERY episode regardless of demand; only the Kd part is demand-gated.")
    pr(H % ("record on the C base", "B", "protect", "dlv289", "dlvGrn", "z_w", "z_med", "ring ms", "cyc", "gate73", "pkR_m", "x base"))
    for r in res:
        if r["bytes"] == 0 or not r["prot"]:
            continue
        zw = rd(keyC, "z_w", r["kd289"]); zm = rd(keyC, "z_med", r["kd289"]); fm = rd(keyC, "f_med", r["kd289"])
        cyc, ms = ring(zm, fm)
        gate = max(rd(keyC, "gate", k) for k in r["lock"])
        pk = min(rd(keyC, "pkR_med", k) for k in r["step"])
        pr(H % (r["lab"], r["bytes"], "byte-id", "%.1f" % r["kd289"], "%.0f/%.0f/%.0f" % tuple(r["grn"]),
                "%+.4f" % zw, "%+.4f" % zm, "%.0f" % ms, "%.1f" % cyc, "%.4f" % gate, "%.3f" % pk,
                "%.3f" % (r["kd289"] / 128.0)))
    zC = rd(keyC, "z_med", 128.0); fC = rd(keyC, "f_med", 128.0)
    cC, mC = ring(zC, fC)
    pr("    C ALONE (no schedule, Kd 128 everywhere): z_w %+.4f  z_med %+.4f  ring %.0f ms (%.1f cyc)  gate %.4f  pkR_m %.3f"
       % (rd(keyC, "z_w", 128.0), zC, mC, cC, rd(keyC, "gate", 128.0), rd(keyC, "pkR_med", 128.0)))

    json.dump(res, open(os.path.join(SCR, "basepick_delivered_dose.json"), "w"), indent=0, default=float)
    open(os.path.join(SCR, "basepick_delivered_dose.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/basepick_delivered_dose.txt")


if __name__ == "__main__":
    main()
