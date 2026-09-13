# -*- coding: utf-8 -*-
"""V292 FLIGHT READ -- (a) the RING-DOWN, and (c) the r24 comparators b5/b6 matched.

THE RING-DOWN.  The pre-registered read is "18-22 Hz envelope half-peak decay 545 -> 183 ms on hands-off
creep".  Two things have to be said about that number before it is scored:
  * 545 and 183 ms are MODEL numbers -- DESIGN-V291-FBLP's "ring FULL / SUB 582 / 545 ms" and
    ADV-V291-B's "180 / 183 ms".  They are not an on-car measurement of V282.
  * V292-REPLAY-PREDICTION section 4.2 showed, BEFORE the drive, that the DRIVEN envelope half-life is
    CONFOUNDED: V282 driven 344 ms, V292 driven 441 ms, and the disturbance's own envelope 276 ms.  A
    driven envelope's decay measures peak-to-background contrast, not ring-down, and it is not a matched
    comparison when the two arms' rings differ in size.
So the driven decay is reported HERE AS A NUMBER and explicitly not used as the test.  The instrument the
replay itself nominated -- the ring AMPLITUDE -- is in v292_flight_creep.py and v292_flight_norm.

Method, the record's: GI.envelope at the window's own f0 (bandwidth +-2 Hz) on the DRIVER-TORQUE bar,
GI.growth_fit's log-envelope decay slope, half-life = ln2 / -slope.  Episodes are contiguous engaged runs
whose 2 s-window 18-22 Hz bar amplitude and prominence pass the record's presence predicate
(prom >= 8 AND amp >= 40, grind1_census_v282.py), on a 0.5 s grid -- the same predicate, evaluated on a
coarser window grid than the full census so it completes on this corpus.

b5/b6 -- the r24 comparators.  V292 cuts the r24 engaged arm 0xC6446 5244 -> 4725 (-9.9 %, read from the
images).  The pre-registered control is "b5/b6 duties ~-10 %".  Reported MATCHED, per speed/demand cell,
because the raw engaged duties are regime-dependent.

ANALYSIS ONLY.  Run: python rlog-tools/studies/grind/v292_flight_decay.py
"""
import io
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import v280_map_profiles as V                 # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import grind1_census_v282 as CEN              # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
CPD = V.CPD
V292_IMG = (LG.FW + "_v292_V292-V282BASE-EFCAVE.C4C00.6D74-FBPOLE.10HZ.962.958-R24.4725-B3.FBSTATE-"
            "KP.FLAT.Y0-CAVE.R24CMP.B5.B6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
V292_ROUTES = ("r6d_v292", "r6e_v292", "r6f_v292")
ALL = V292_ROUTES + ("r6c", "r39", "r35")
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def main():
    CEN.IMG["V292"] = V292_IMG
    for t in V292_ROUTES:
        CEN.CELL_OF[t] = "V292"
    CEN.CELL_OF["r6c"] = "V282"
    cb = {k: GI.read_cells(p) for k, p in CEN.IMG.items() if k in ("V282", "V292", "V281r3")}
    rng = np.random.default_rng(20260913)
    G = {}
    for t in ALL:
        g = C20.load(t)
        g["idx"], _ = GI.demand_live(np.round(g["cmd"]), g["bar"], cb[CEN.CELL_OF[t]])
        B = dict(np.load(os.path.join(C20.CACHE, t + "_b4.npz")))
        k14, P14, tn14, _ = C20.dejitter(B["t14b"].astype(float), 0.01, 100)
        b4 = B["b4"].astype(int)
        for n in (3, 5, 6, 7):
            g["bit%d" % n] = np.round(np.interp(g["t"], tn14, ((b4 >> n) & 1).astype(float)))
        G[t] = g

    # ---------------------------------------------------------------- episodes + decay
    pr("=" * 150)
    pr("(a) THE 18-22 Hz EPISODES AND THEIR DRIVEN HALF-PEAK DECAY.")
    pr("    Presence predicate: grind1_census_v282's, unchanged -- 2 s windows on a 0.5 s grid,")
    pr("    18-22 Hz prominence >= 8 on the driver-torque bar AND 18-22 Hz bar amplitude >= 40.")
    pr("🛑 The pre-registered 545 -> 183 ms are MODEL numbers, and the replay showed BEFORE the drive that")
    pr("   the DRIVEN half-peak decay is confounded (V282 driven 344 ms vs V292 driven 441 ms, disturbance")
    pr("   envelope 276 ms).  This table is reported, not used as the test.")
    pr("=" * 150)
    W, STEP = 200, 50
    pr("  %-10s %-7s %8s %8s %7s | %8s %8s %8s | %9s %9s | %8s" %
       ("route", "build", "n_win", "n_pres", "pres %", "n_ep", "dur p50", "f0 p50", "decay p50", "decay p90",
        "env p50"))
    RES = {}
    for t in ALL:
        g = G[t]
        m = g["eng"]
        wt, wp = [], []
        for a, b in C20.runs(m, W):
            for s in range(a, b - W + 1, STEP):
                e = s + W
                f0, prom = CEN.line_of(g["bar"][s:e], FS)
                amp = CEN.band(g["bar"][s:e], 18, 22)
                wt.append(s + W // 2)
                wp.append(bool(prom >= 8 and amp >= 40))
        wt = np.asarray(wt, int); wp = np.asarray(wp, bool)
        n, npres = len(wt), int(wp.sum())
        # episodes = contiguous frames whose nearest window is present
        hot = np.zeros(len(g["t"]), bool)
        for c, p_ in zip(wt, wp):
            if p_:
                hot[max(0, c - STEP // 2):c + STEP // 2] = True
        hot &= g["eng"]
        eps = []
        for a, b in C20.runs(hot, int(0.5 * FS)):
            f0, prom = CEN.line_of(g["bar"][a:b], FS)
            if not np.isfinite(f0):
                continue
            lo_, hi_ = max(0, a - 100), min(len(g["t"]), b + 100)
            env = CEN.envelope(g["bar"][lo_:hi_], f0, FS)
            tl = g["t"][lo_:hi_] - g["t"][lo_]
            gu, gd = CEN.growth_fit(tl, env)
            eps.append(dict(a=a, b=b, dur=(b - a) / FS, f0=f0, gd=gd, gu=gu,
                            env=float(np.nanmax(env)),
                            ramp=CEN.band(g["wire"][a:b], 18, 22) / CPD,
                            v=float(g["vego"][a:b].mean()),
                            hands=float(np.median(np.abs(g["bar"][a:b])))))
        RES[t] = eps
        gd = np.array([e["gd"] for e in eps], float)
        dec = np.where(gd < -1e-9, np.log(2.0) / (-gd) * 1e3, np.nan)
        pr("  %-10s %-7s %8d %8d %6.1f%% | %8d %8.2f %8.2f | %9.0f %9.0f | %8.1f" % (
            t, CEN.CELL_OF.get(t, "?"), n, npres, 100.0 * npres / max(n, 1), len(eps),
            np.median([e["dur"] for e in eps]) if eps else np.nan,
            np.median([e["f0"] for e in eps]) if eps else np.nan,
            np.nanmedian(dec) if len(dec) else np.nan, np.nanpercentile(dec, 90) if len(dec) else np.nan,
            np.median([e["env"] for e in eps]) if eps else np.nan))
    pr("")
    pr("  episode rate per engaged hour, and the decay CI:")
    pr("  %-10s %-7s %10s %10s | %-24s" % ("route", "build", "eng h", "ep / h", "decay p50 ms [95% CI]"))
    for t in ALL:
        g = G[t]
        eps = RES[t]
        gd = np.array([e["gd"] for e in eps], float)
        dec = np.where(gd < -1e-9, np.log(2.0) / (-gd) * 1e3, np.nan)
        dec = dec[np.isfinite(dec)]
        engh = g["eng"].sum() / FS / 3600.0
        if len(dec) < 4:
            pr("  %-10s %-7s %10.3f %10.1f | too few decaying episodes (%d)" %
               (t, CEN.CELL_OF.get(t, "?"), engh, len(eps) / engh, len(dec)))
            continue
        bb = np.array([np.median(dec[rng.integers(0, len(dec), len(dec))]) for _ in range(4000)])
        pr("  %-10s %-7s %10.3f %10.1f | %8.0f [%.0f, %.0f]  n=%d" % (
            t, CEN.CELL_OF.get(t, "?"), engh, len(eps) / engh, np.median(dec),
            np.percentile(bb, 2.5), np.percentile(bb, 97.5), len(dec)))
    pr("")
    pr("  hands-off episodes only (median |bar| < 400 over the episode):")
    for t in ALL:
        eps = [e for e in RES[t] if e["hands"] < 400]
        gd = np.array([e["gd"] for e in eps], float)
        dec = np.where(gd < -1e-9, np.log(2.0) / (-gd) * 1e3, np.nan)
        dec = dec[np.isfinite(dec)]
        pr("  %-10s %-7s n_ep %3d  f0 p50 %5.2f Hz  rate18-22 p50 %5.2f deg/s  decay p50 %s" % (
            t, CEN.CELL_OF.get(t, "?"), len(eps),
            np.median([e["f0"] for e in eps]) if eps else np.nan,
            np.median([e["ramp"] for e in eps]) if eps else np.nan,
            ("%.0f ms (n=%d)" % (np.median(dec), len(dec))) if len(dec) >= 4 else "too few"))

    # ---------------------------------------------------------------- b5/b6 matched
    pr("")
    pr("=" * 150)
    pr("b5 / b6 -- THE r24 COMPARATORS, MATCHED.  V292 cuts the r24 engaged arm 0xC6446 5244 -> 4725")
    pr("(-9.9 %%, read from the images).  Pre-registered control: duties about -10 %%.  Raw engaged duty is")
    pr("regime-dependent, so this is reported per speed x demand-index cell and then re-weighted onto")
    pr("r6c's own cell mix so the arms are compared on the same mixture.")
    pr("=" * 150)
    VB = [(0, 3), (3, 8), (8, 15), (15, 25), (25, 40)]
    IB = [(0, 20), (20, 60), (60, 120), (120, 241)]
    cellsw = {}
    for t in ALL:
        g = G[t]
        cw = {}
        for vlo, vhi in VB:
            for ilo, ihi in IB:
                m = g["eng"] & (g["vego"] >= vlo) & (g["vego"] < vhi) & (g["idx"] >= ilo) & (g["idx"] < ihi)
                if m.sum() >= 200:
                    cw[(vlo, ilo)] = (float(g["bit5"][m].mean()), float(g["bit6"][m].mean()), int(m.sum()))
        cellsw[t] = cw
    base = cellsw["r6c"]
    pr("  %-10s %-7s | %-26s | %-26s | %s" % ("route", "build", "b5 raw / reweighted", "b6 raw / reweighted",
                                              "cells shared with r6c"))
    for t in ALL:
        g = G[t]
        cw = cellsw[t]
        m = g["eng"]
        raw5, raw6 = float(g["bit5"][m].mean()), float(g["bit6"][m].mean())
        shared = [k for k in cw if k in base]
        wt = np.array([base[k][2] for k in shared], float)
        if len(shared) >= 3:
            rw5 = float(np.average([cw[k][0] for k in shared], weights=wt))
            rw6 = float(np.average([cw[k][1] for k in shared], weights=wt))
        else:
            rw5 = rw6 = np.nan
        pr("  %-10s %-7s | %10.3f / %10.3f     | %10.3f / %10.3f     | %d of %d" %
           (t, CEN.CELL_OF.get(t, "?"), raw5, rw5, raw6, rw6, len(shared), len(base)))
    pr("")
    pr("  reweighted ratio to r6c (predicted about 0.90):")
    rw = {}
    for t in ALL:
        cw = cellsw[t]
        shared = [k for k in cw if k in base]
        if len(shared) < 3:
            continue
        wt = np.array([base[k][2] for k in shared], float)
        rw[t] = (float(np.average([cw[k][0] for k in shared], weights=wt)),
                 float(np.average([cw[k][1] for k in shared], weights=wt)))
    b5b = rw.get("r6c")
    for t in ALL:
        if t == "r6c" or t not in rw or b5b is None:
            continue
        pr("    %-10s b5 x%.3f   b6 x%.3f" % (t, rw[t][0] / b5b[0], rw[t][1] / b5b[1]))
    pr("")
    pr("  per-cell detail (speed x idx; b5 / b6 / n):")
    keys = sorted(set(k for t in ALL for k in cellsw[t]))
    pr("  %-14s %s" % ("cell v,idx", " ".join("%-20s" % t for t in ALL)))
    for k in keys:
        row = []
        for t in ALL:
            c = cellsw[t].get(k)
            row.append("%.3f/%.3f n%-5d" % c if c else "      --            ")
        pr("  %-14s %s" % ("%d-,%d-" % k, " ".join("%-20s" % x for x in row)))

    io.open(os.path.join(SCR, "v292_flight_decay.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("\nwrote v292_flight_decay.txt")


if __name__ == "__main__":
    main()
