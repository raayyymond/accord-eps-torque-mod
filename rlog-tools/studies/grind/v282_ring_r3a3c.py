# -*- coding: utf-8 -*-
"""studies/grind/v282_ring_r3a3c.py -- DID THE LAF CUT REDUCE THE 7 Hz RING'S DRIVE?

STATE.md's prediction for the SteerLatAccel 2.11 -> 4.0 move: "the LAF cut reduces the ring's DRIVE
independently of any firmware change", sized from r39's own 6-10 Hz bar in the loaded-turn stratum
(p50 178 raw vs r35's 42, 19 vs 12 windows -- thin; the DIRECTION was the finding, not the size).

Firmware is V282 on r39 / r3c / r3a alike -- the cave, the Kp table and the map are byte-identical, so
any change here is the OUTER loop's drive, not the inner loop's dynamics.

The stratum, the band estimator, the window length and the step are v282_read_r39.py's section 2f,
verbatim (2 s windows, 0.5 s step, engaged & |ang| >= 30 & idx >= 68).  Run it on r39 first: it must
reproduce 178 / 42 before r3a and r3c are read.

Run: python rlog-tools/studies/grind/v282_ring_r3a3c.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import v280_map_profiles as V                 # noqa: E402
import grind_incident_r35 as GI               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
W, STEP = 200, 50
ALL = ("r3a", "r3c", "r39", "r35", "r34")
TUNE = {"r3a": "V282  LAF 4.00", "r3c": "V282  LAF 3.60", "r39": "V282  LAF 2.11",
        "r35": "V281r3 LAF 2.11 SR12.5", "r34": "V280r2 LAF 2.11"}
IMG = {"V282": LG.FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
       "V281r3": LG.FW + "_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
       "V280r2": LG.FW + LG.IMAGES["V280r2"]}
CELL_OF = {"r3a": "V282", "r3c": "V282", "r39": "V282", "r35": "V281r3", "r34": "V280r2"}
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def band(x, lo, hi):
    return C20.bamp(x, lo, hi, FS)


def main():
    cells = {k: GI.read_cells(p) for k, p in IMG.items()}
    G = {}
    for tag in ALL:
        print("loading %s ..." % tag, flush=True)
        g = C20.load(tag)
        g["idx"], g["sgn"] = GI.demand_live(np.round(g["cmd"]), g["bar"], cells[CELL_OF[tag]])
        G[tag] = g

    pr("=" * 168)
    pr("THE 7 Hz RING'S DRIVE ACROSS THE LAF DOSE.  Firmware V282 unchanged on r39/r3c/r3a; only SteerLatAccel moved.")
    pr("  Stratum and estimator are v282_read_r39.py section 2f, VERBATIM: engaged & |ang| >= 30 & idx >= 68,")
    pr("  2 s windows, 0.5 s step, 4th-order zero-phase Butterworth band amplitude (sqrt(2) * sd).")
    pr("  REPRODUCTION GATE: r39 must read p50 178 and r35 p50 42 before r3a/r3c are believed.")
    pr("=" * 168)
    pr("  %-5s %-24s %9s %8s | %-30s | %-30s | %s" % (
        "route", "build / tune", "stratum s", "windows", "bar 6-10 p50/p90/max", "bar 18-22 p50/p90/max", "rate 6-10 p50 deg/s"))
    hold = {}
    for tag in ALL:
        gg = G[tag]
        m = gg["eng"] & (np.abs(gg["ang"]) >= 30) & (gg["idx"] >= 68)
        a6, a20, r6 = [], [], []
        for aa, bb in C20.runs(m, W):
            for s in range(aa, bb - W + 1, STEP):
                e = s + W
                a6.append(band(gg["bar"][s:e], 6, 10))
                a20.append(band(gg["bar"][s:e], 18, 22))
                r6.append(band(gg["wire"][s:e], 6, 10) / V.CPD)
        hold[tag] = np.array(a6, float)
        if len(a6) < 5:
            pr("  %-5s %-24s %9.1f %8d | (too thin to quote)" % (tag, TUNE[tag], m.sum() / FS, len(a6)))
            continue
        pr("  %-5s %-24s %9.1f %8d | %9.0f %9.0f %9.0f | %9.0f %9.0f %9.0f | %8.2f" % (
            tag, TUNE[tag], m.sum() / FS, len(a6), *np.percentile(a6, (50, 90)), max(a6),
            *np.percentile(a20, (50, 90)), max(a20), np.median(r6)))

    pr()
    pr("  BOOTSTRAP on the loaded-turn 6-10 Hz p50 (windows overlap 4:1, so resample 2 s NON-OVERLAPPING blocks):")
    rng = np.random.default_rng(5)
    for tag in ALL:
        a = hold[tag]
        if len(a) < 8:
            pr("    %-5s n %d -- too thin" % (tag, len(a)))
            continue
        b = a[::4]                                   # every 4th window = non-overlapping
        s = np.median(b[rng.integers(0, len(b), (4000, len(b)))], axis=1)
        pr("    %-5s p50 %6.0f  95%% CI [%5.0f, %5.0f]  (n %d overlapping windows, %d independent)" % (
            tag, np.median(b), np.percentile(s, 2.5), np.percentile(s, 97.5), len(a), len(b)))

    pr()
    pr("  IDX-MATCHED: the loaded-turn stratum is re-weighted onto r39's OWN demand-index distribution, so the")
    pr("  comparison is not confounded by r3a/r3c simply asking for less.  Bins of 20 in idx, r39 the reference.")
    ref = G["r39"]
    mref = ref["eng"] & (np.abs(ref["ang"]) >= 30) & (ref["idx"] >= 68)
    edges = np.arange(60, 261, 20)
    wref, _ = np.histogram(ref["idx"][mref], bins=edges)
    wref = wref / max(wref.sum(), 1)
    pr("    r39 idx weights " + " ".join("%3.0f-%3.0f:%.2f" % (edges[i], edges[i + 1], wref[i]) for i in range(len(wref))))
    pr("    %-5s %14s %14s %10s" % ("route", "raw p50 6-10", "idx-matched p50", "bins used"))
    for tag in ALL:
        gg = G[tag]
        m = gg["eng"] & (np.abs(gg["ang"]) >= 30) & (gg["idx"] >= 68)
        vals, idxs = [], []
        for aa, bb in C20.runs(m, W):
            for s in range(aa, bb - W + 1, STEP):
                vals.append(band(gg["bar"][s:s + W], 6, 10))
                idxs.append(np.median(gg["idx"][s:s + W]))
        vals, idxs = np.array(vals, float), np.array(idxs, float)
        if len(vals) < 5:
            pr("    %-5s %14s %14s %10s" % (tag, "--", "--", "0"))
            continue
        per, used = [], 0
        for i in range(len(wref)):
            s = (idxs >= edges[i]) & (idxs < edges[i + 1])
            if s.sum() >= 2 and wref[i] > 0:
                per.append((wref[i], np.median(vals[s])))
                used += 1
        mm = (sum(w * v for w, v in per) / sum(w for w, v in per)) if per else np.nan
        pr("    %-5s %14.0f %14.0f %10d" % (tag, np.median(vals), mm, used))

    pr()
    pr("  CONTEXT: the DEMAND the outer loop is making in that stratum (the ring's drive is proportional to it).")
    pr("    %-5s %10s %10s %10s %10s %10s %10s" % ("route", "idx p50", "idx p90", "|cmd| p50", "|cmd| p90", "|ang| p50", "v p50"))
    for tag in ALL:
        gg = G[tag]
        m = gg["eng"] & (np.abs(gg["ang"]) >= 30) & (gg["idx"] >= 68)
        if m.sum() < 200:
            pr("    %-5s (too thin)" % tag)
            continue
        pr("    %-5s %10.0f %10.0f %10.0f %10.0f %10.0f %10.1f" % (
            tag, np.percentile(gg["idx"][m], 50), np.percentile(gg["idx"][m], 90),
            np.percentile(np.abs(gg["cmd"][m]), 50), np.percentile(np.abs(gg["cmd"][m]), 90),
            np.percentile(np.abs(gg["ang"][m]), 50), np.percentile(gg["vego"][m], 50)))

    pr()
    pr("  ROUTE-WIDE ENGAGED CONTEXT (not the loaded stratum) -- exposure, for the record:")
    pr("    %-5s %12s %12s %12s %12s" % ("route", "engaged s", "eng v<6 s", "loaded s", "bar 6-10 p50 all-eng"))
    for tag in ALL:
        gg = G[tag]
        e = gg["eng"]
        m = e & (np.abs(gg["ang"]) >= 30) & (gg["idx"] >= 68)
        a = []
        for aa, bb in C20.runs(e, W):
            for s in range(aa, bb - W + 1, 200):
                a.append(band(gg["bar"][s:s + W], 6, 10))
        pr("    %-5s %12.1f %12.1f %12.1f %12.0f" % (
            tag, e.sum() / FS, (e & (gg["vego"] < 6)).sum() / FS, m.sum() / FS,
            np.median(a) if a else np.nan))

    pr()
    pr("=" * 168)
    pr("  THE HIGH-POWER READ.  The loaded-turn stratum gives r3a FIVE windows -- it cannot settle anything.")
    pr("  Here EVERY engaged 2 s window enters (0.5 s step), then the comparison is made INSIDE matched cells of")
    pr("  (speed x demand index), so r3a/r3c are never credited for simply driving a different road.")
    pr("=" * 168)
    WIN = {}
    for tag in ALL:
        gg = G[tag]
        e = gg["eng"]
        rows = []
        for aa, bb in C20.runs(e, W):
            for s in range(aa, bb - W + 1, STEP):
                rows.append((band(gg["bar"][s:s + W], 6, 10),
                             np.median(gg["vego"][s:s + W]), np.median(gg["idx"][s:s + W]),
                             np.median(np.abs(gg["ang"][s:s + W]))))
        WIN[tag] = np.array(rows, float) if rows else np.zeros((0, 4))
    VB = ((0, 4), (4, 9), (9, 16), (16, 40))
    IB = ((0, 40), (40, 100), (100, 180), (180, 260))
    pr("  bar 6-10 p50 by (speed x idx) cell, n windows in brackets:")
    pr("    %-10s" % "v \\ idx" + "".join("%38s" % ("idx %d-%d" % b) for b in IB))
    for vlo, vhi in VB:
        for tag in ALL:
            cells = []
            Wt = WIN[tag]
            for ilo, ihi in IB:
                s = (Wt[:, 1] >= vlo) & (Wt[:, 1] < vhi) & (Wt[:, 2] >= ilo) & (Wt[:, 2] < ihi)
                cells.append("%38s" % ("--" if s.sum() < 6 else "%6.0f  (n%4d)" % (np.median(Wt[s, 0]), s.sum())))
            pr("    %-10s %-5s" % ("%g-%g m/s" % (vlo, vhi) if tag == ALL[0] else "", tag) + "".join(cells))
        pr()
    pr("  AND THE SINGLE POOLED NUMBER: every engaged window re-weighted onto r39's own (speed x idx) cell mass.")
    ref = WIN["r39"]
    wt = {}
    for vlo, vhi in VB:
        for ilo, ihi in IB:
            s = (ref[:, 1] >= vlo) & (ref[:, 1] < vhi) & (ref[:, 2] >= ilo) & (ref[:, 2] < ihi)
            wt[(vlo, ilo)] = s.sum()
    tot = sum(wt.values())
    pr("    %-5s %-24s %14s %18s %12s" % ("route", "tune", "raw p50", "r39-matched p50", "cells used"))
    for tag in ALL:
        Wt = WIN[tag]
        num = den = 0.0
        used = 0
        for vlo, vhi in VB:
            for ilo, ihi in IB:
                w = wt[(vlo, ilo)] / tot
                if w <= 0:
                    continue
                s = (Wt[:, 1] >= vlo) & (Wt[:, 1] < vhi) & (Wt[:, 2] >= ilo) & (Wt[:, 2] < ihi)
                if s.sum() < 6:
                    continue
                num += w * np.median(Wt[s, 0])
                den += w
                used += 1
        pr("    %-5s %-24s %14.0f %18.0f %12d" % (
            tag, TUNE[tag], np.median(Wt[:, 0]) if len(Wt) else np.nan,
            num / den if den else np.nan, used))

    out = os.path.join(HERE, "_scratch", "v282_ring_r3a3c.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(OUT))
    pr("\nwrote %s" % out)


if __name__ == "__main__":
    main()
