# -*- coding: utf-8 -*-
"""hardturn_matched.py -- criterion P1 at MATCHED speed x demand, in HARD turns, against every V293 flight with an
ident cache (r70 rev1, r71-old rev2, r72/r73 rev3, r75 rev4, r76 rev5).  Subagent "bands", 2026-09-30.

Masks and filters are the record's (v293_ident_lib): the lateral-engaged mask g["eng"] & torqueState.active,
hands-off = not steeringPressed with a +-0.5 s buffer (v293r3_read / v293r5_read), 4th-order zero-phase band-passes,
planner demand D = desiredCurvature * v^2.  Cells are speed band x |D| bin; stretches >= 2 s; a cell needs >= 8 s.
Per cell:
  r16   1.6-3 Hz wheel-rate rms, deg/s (0x18F / 8)            -- P1's quantity
  shr   its share of the 0.3-8 Hz wheel-rate energy, %        -- O4's normalisation
  c16   1.6-3 Hz 0xE4 command rms, counts                     -- does the COMMAND carry it?
  coh   magnitude-squared coherence command -> rate, mean over 1.6-3 Hz (Welch 256 on the concatenated stretches)
  tap16 1.6-3 Hz tap rms, counts (the EPS delivered torque, 50 Hz native via ZOH on the 100 Hz grid)
A 2 Hz wheel-rate oscillation the command does not carry (coh low, c16 small) is the EPS/plant side; one it does
carry is the outer loop.  EVIDENCE for the numbers.  What the operator felt is his.
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, *[".."] * 5))
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "grind"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import v293_ident_lib as L   # noqa: E402
import v293r3_read as R3     # noqa: E402

FS = 100.0
TAGS = ["r71b_v294", "r70_v293", "r71_v293r2", "r72_v293r3", "r73_v293r3", "r75_v293r4", "r76_v293r5"]
SPEED = [("5-10", 5, 10), ("10-15", 10, 15), ("15-22", 15, 22), ("22+", 22, 99)]
DEM = [("1.0-1.5", 1.0, 1.5), (">=1.5", 1.5, 99.0)]
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def cell_stats(g, m, rate, tap):
    st = L.stretches(m, int(2 * FS))
    s = sum(b - a for a, b in st) / FS
    if s < 8:
        return dict(s=s)
    r16 = np.concatenate([L.bandpass(rate[a:b], 1.6, 3.0) for a, b in st])
    r03 = np.concatenate([L.bandpass(rate[a:b], 0.3, 8.0) for a, b in st])
    c16 = np.concatenate([L.bandpass(g["cmd"][a:b], 1.6, 3.0) for a, b in st])
    t16 = np.concatenate([L.bandpass(tap[a:b], 1.6, 3.0) for a, b in st])
    X = np.concatenate([signal.detrend(g["cmd"][a:b]) for a, b in st])
    Y = np.concatenate([signal.detrend(rate[a:b]) for a, b in st])
    f, C = signal.coherence(X, Y, fs=FS, nperseg=256)
    sel = (f >= 1.6) & (f <= 3.0)
    return dict(s=s, n=len(st), r16=float(np.sqrt(np.mean(r16 ** 2))), shr=float(100 * np.mean(r16 ** 2) / np.mean(r03 ** 2)),
                c16=float(np.sqrt(np.mean(c16 ** 2))), coh=float(np.mean(C[sel])), tap16=float(np.sqrt(np.mean(t16 ** 2))))


def main():
    res = {}
    for t in TAGS:
        g = R3.load_plus(t)
        v = g["v"]
        rate = np.nan_to_num(g["rate_dps"])
        tap = np.nan_to_num(g["T"])
        eng = g["eng"] & (g["cs_active"] > 0.5) & np.isfinite(v)
        w = int(0.5 * FS)
        pb = np.convolve((g["press"] > 0.5).astype(float), np.ones(2 * w + 1), mode="same") > 0
        D = np.abs(np.nan_to_num(g["des_curv"] * v ** 2))
        res[t] = {}
        for strat, base in (("hands-off", eng & ~pb), ("engaged", eng)):
            for sn, lo, hi in SPEED:
                for dn, dlo, dhi in DEM:
                    m = base & (v >= lo) & (v < hi) & (D >= dlo) & (D < dhi)
                    res[t]["%s|%s|%s" % (strat, sn, dn)] = cell_stats(g, m, rate, tap)
            m = base & (v < 10) & (np.abs(g["ang"]) > 60)
            res[t]["%s|v<10|ang>60" % strat] = cell_stats(g, m, rate, tap)
        print("   done", t, flush=True)
    keys = list(res[TAGS[0]].keys())
    for strat in ("hands-off", "engaged"):
        pr("\n%s -- r16 deg/s [shr %%] c16 cnt coh tap16 cnt (s)" % strat.upper())
        pr("  %-18s " % "cell" + " ".join("%-34s" % t for t in TAGS))
        for k in keys:
            if not k.startswith(strat + "|"):
                continue
            row = "  %-18s " % k.split("|", 1)[1]
            for t in TAGS:
                c = res[t][k]
                if "r16" not in c:
                    row += "%-34s " % ("  (%.0f s)" % c["s"])
                else:
                    row += "%-34s " % ("%5.2f [%2.0f%%] %5.1f %.2f %5.1f (%3.0f s)" % (c["r16"], c["shr"], c["c16"], c["coh"], c["tap16"], c["s"]))
            pr(row)
    # P1 matched verdict against r75 / r76 (and the V293 family max)
    pr("\nP1 MATCHED (hands-off and engaged): V294 r16 vs r75 / r76 in every cell where both have >= 8 s")
    for k in keys:
        a = res["r71b_v294"][k]
        if "r16" not in a:
            continue
        row = "  %-28s V294 %5.2f" % (k, a["r16"])
        for ref in ("r75_v293r4", "r76_v293r5"):
            b = res[ref][k]
            row += "   %s %s" % (ref[:3], ("%5.2f -> x%.2f" % (b["r16"], a["r16"] / b["r16"])) if "r16" in b else "   - (%.0f s)" % b["s"])
        fam = [res[t][k]["r16"] for t in TAGS[1:] if "r16" in res[t][k]]
        row += "   V293 family range %s" % (("%.2f-%.2f (n %d)" % (min(fam), max(fam), len(fam))) if fam else "-")
        pr(row)
    json.dump(res, open(os.path.join(HERE, "hardturn_matched_out.json"), "w"), indent=1)
    open(os.path.join(HERE, "hardturn_matched_out.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
