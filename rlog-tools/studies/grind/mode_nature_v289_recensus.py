# -*- coding: utf-8 -*-
"""studies/grind/mode_nature_v289_recensus.py -- MODE-NATURE RE-CENSUS WITH THE V289 ROUTES.   Subagent modenat, 2026-09-09.
Analysis only: builds nothing, flashes nothing, sends nothing.

Why: loopshape20_mode_nature.py (2026-09-08) concluded "a PLANT MODE the loop de-damps, f pinned 20.03-20.08 Hz across Kp 248-696".
V289 rev 1 (V282 + a notch on the clamped rate-loop output S, 20.04 Hz Q3, + fb pole 16.5 -> 25 Hz; Kp/Kd/clamps/gain unchanged)
flew on r62/r63 and the grinding line MOVED 20.0 -> 15-17 Hz.  A pinned plant mode does not move 3.5 Hz on a phase-only change.

Parts
  1  the 2026-09-08 census tables (f0, zeta per build / Kp bin, presence) with r62_v289 + r63_v289 added; the band widened to
     12-26 Hz and the amplitude gate PEAK-TRACKED (bar amplitude at f0 +- 2 Hz >= 40 raw) so a 16 Hz line is counted.  The old
     fixed-band gate (bar 18-22 >= 40) is reported alongside so the yardstick's blindness is visible.  Free-decay zeta per episode.
     Closed-loop transfer cmd -> rate/bar (12-26 Hz) and the plant tap rate/T at native instants for the V289 routes.
  2  for each plant hypothesis the 2026-09-08 study carried (smooth, resonant, smooth+mode, weak-mode; _scratch/loopshape20_plants.json)
     the CLOSED-LOOP POLES under V282, V288 (= V282 electronics: the pre-filter is outside the loop) and V289's byte-exact electronics
     (notch b=[16048,-31842,16048]/a=[16384,-31842,15712] Q14 on S; fb pole 875/2301), from the roots of the discrete characteristic
     polynomial 1 + L(z) = 0 (ZOH plant at 1 kHz, integer-tick delay) -- not the |S|-peak proxy the earlier study used.  Predicted
     (f, zeta) vs measured per build, chi-square and relative likelihood.  Then each family RE-FITTED jointly to V282 + V289.
  3  the physical reading (in the report).
  4  V289 AS AN EXPERIMENT: with the notch's exact phase and the fb pole's phase, back out the plant's phase AND magnitude at the two
     measured line frequencies from the -180 deg / |L| = 1 condition, with error bars from the measured zeta (|1+L| <= ~2 zeta at
     a lightly damped crossover pole) and the f0 spread.  Compared with the tap-measured plant (offset-corrected) and every fit.
Run: python mode_nature_v289_recensus.py [--nocensus]   (writes _scratch/mode_nature_v289_recensus.txt and *_windows.npz beside it)
"""
import json
import os
import sys

import numpy as np
from scipy import signal, stats

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import v280_map_profiles as V                 # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import _grind2_lib as G2                      # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FST, FS1K, TS = 100.0, 50.0, 1000.0, 1e-3
W, STEP = 200, 50
CPD = 8.0
TAU_STREAM = 0.0039
LINE_LO, LINE_HI = 12.0, 26.0          # widened census band (was 15-26)
DEMAND_MIN = 20.0                      # LKAS demand index above which the rate loop is actually commanding (see 1e)
IMG = {
    "V282": LG.FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "V288": LG.FW + "_v288r2_V288R2-V282BASE-SPFILT.K4.EINIT-KP.FLAT.Y0-CAVE.R24CMP.B6-SPSIGN.B5-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "V289": LG.FW + "_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "V281r3": LG.FW + "_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "V280r2": LG.FW + LG.IMAGES["V280r2"],
    "V278r3": LG.FW + LG.IMAGES["V278r3"],
}
ROUTES = ("r39", "r3a", "r3c", "r5e_v288", "r62_v289", "r63_v289", "r35", "r32", "r33", "r34", "r31")
BUILD = {"r39": "V282", "r3a": "V282", "r3c": "V282", "r5e_v288": "V288", "r62_v289": "V289", "r63_v289": "V289",
         "r35": "V281r3", "r32": "V280r2", "r33": "V280r2", "r34": "V280r2", "r31": "V278r3"}
GROUP = {"V282": "flat-Kp", "V288": "flat-Kp", "V281r3": "flat-Kp", "V289": "flat-Kp-V289", "V280r2": "Kp-LERP", "V278r3": "Kp-LERP"}
BUILDS = ("V278r3", "V280r2", "V281r3", "V282", "V288", "V289")
# V289 notch as built (Q14, cave 0xC4C00; DC gain (16048-31842+16048)/(16384-31842+15712) = 254/254 = 1)
NOTCH_B = np.array([16048.0, -31842.0, 16048.0]) / 16384.0
NOTCH_A = np.array([16384.0, -31842.0, 15712.0]) / 16384.0
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def med_iqr(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return "%.2f [%.2f-%.2f] n=%d" % (np.median(x), np.percentile(x, 25), np.percentile(x, 75), len(x)) if len(x) >= 5 else "(n=%d)" % len(x)


# =====================================================================================================================
# PART 1 -- the census, widened and peak-tracked
# =====================================================================================================================
def kp_of(c, idx):
    return np.interp(idx, c["kp_X"], c["kp_Y"])


def load_route(tag, cells):
    g = C20.load(tag)
    g["tr"] = g["t"] - g["t"][0]
    c = cells[BUILD[tag]]
    g["idx"], _ = GI.demand_live(np.round(g["cmd"]), g["bar"], c)
    g["kp"] = kp_of(c, g["idx"])
    g["rate"] = np.abs(g["wire"]) / V.CPD
    return g


_BANDMASK = {}


def _prom_band(f, P, lo, hi, halfwin=6.0, exclude=1.5):
    """G2.prom_spectrum restricted to the rows in [lo, hi] -- BIT-IDENTICAL there, NaN outside.

    Why: G2.prom_spectrum builds a full (nfft/2+1)^2 mask and a same-shape float array, i.e. 32 MiB
    per call at GI.line_of's nfft=4096.  The census makes ~30 000 calls; the 2026-09-09 run died with
    _ArrayMemoryError inside it.  locate() only ever reads R inside [lo, hi], and every row there has
    its full +-halfwin column support inside [lo-halfwin, hi+halfwin], so the row-sum >= 5 cull and the
    median are unchanged.  Verified equal to GI.line_of on real windows (see verify_line_of()).
    """
    key = (len(f), float(f[1]), lo, hi, halfwin, exclude)
    got = _BANDMASK.get(key)
    if got is None:
        rows = np.flatnonzero((f >= lo - 1e-9) & (f <= hi + 1e-9))
        # f is an exact multiple of df = fs/nfft (a power of two here), so |f_i - f_j| = |k| df exactly:
        # the mask is the SAME offset annulus for every row in the band, and no row loses a column to the
        # array edge (row 12 Hz - 6 Hz > 0, row 26 Hz + 6 Hz < f_nyq) or to the f > 0.3 rule.
        df = float(f[1]); kmax = int(np.floor(halfwin / df + 1e-9))
        offs = np.array([k for k in range(-kmax, kmax + 1) if exclude < abs(k) * df <= halfwin + 1e-12], int)
        assert rows[0] + offs.min() >= 0 and rows[-1] + offs.max() < len(f) and len(offs) >= 5
        got = (rows, rows[:, None] + offs[None, :])
        _BANDMASK[key] = got
    rows, idx = got
    with np.errstate(all="ignore"):
        fl = np.median(P[idx], axis=1)
        r = np.where(fl > 0, P[rows] / np.where(fl > 0, fl, 1.0), np.nan)
    R = np.full(len(f), np.nan)
    R[rows] = r
    return R


def line_of(x, fs, lo=LINE_LO, hi=LINE_HI):
    """GI.line_of with the banded prominence floor (same f0/prominence, ~30x less memory and time)."""
    x = np.asarray(x, float)
    if len(x) < 32:
        return np.nan, np.nan, None, None
    f, P = signal.periodogram(x - x.mean(), fs=fs, window="hann", nfft=4096)
    R = _prom_band(f, P, lo, hi)
    f0, prom = G2.locate(f, P, lo, hi, R=R)
    return f0, prom, f, P


def verify_line_of(G, tags, n=12):
    """EVIDENCE that the banded prominence is not a shortcut: identical (f0, prom) to GI.line_of."""
    marker = os.path.join(SCR, "mode_nature_v289_lineof_check.txt")
    if os.path.exists(marker):
        pr("  " + open(marker).read().strip() + "  [cached from an earlier run]")
        return True
    rng = np.random.default_rng(7)
    bad = 0; k = 0
    for tag in tags:
        g = G[tag]
        idx = np.flatnonzero(g["eng"])[: -W - 1] if g["eng"].any() else np.array([], int)
        if len(idx) < 10:
            continue
        for s in rng.choice(idx, min(n, len(idx)), replace=False):
            for sig in ("bar", "wire"):
                a = line_of(g[sig][s:s + W], FS)
                b = GI.line_of(g[sig][s:s + W], FS, lo=LINE_LO, hi=LINE_HI)
                k += 1
                if not (np.allclose(a[0], b[0], equal_nan=True, rtol=0, atol=1e-9) and np.allclose(a[1], b[1], equal_nan=True, rtol=0, atol=1e-9)):
                    bad += 1
    msg = "line_of banded-prominence check: %d windows, %d disagreements with GI.line_of  (%s)" % (k, bad, "PASS" if bad == 0 else "FAIL")
    pr("  " + msg)
    if bad == 0:
        open(marker, "w").write(msg)
    return bad == 0


def band_at(x, f0, fs=FS, half=2.0):
    return GI.band(x, max(f0 - half, 1.0), f0 + half, fs)


def inst_freq(x, f0, fs, bw=3.0):
    y = C20.bandpass(x, max(f0 - bw, 1.0), f0 + bw, fs)
    ph = np.unwrap(np.angle(signal.hilbert(y)))
    return np.gradient(ph) * fs / (2 * np.pi)


def census(G, tags):
    cache = os.path.join(SCR, "mode_nature_v289_windows.npz")
    rows = []
    for tag in tags:
        per = os.path.join(SCR, "mode_nature_v289_win_%s.npz" % tag)   # per-route cache: a killed run resumes here
        if os.path.exists(per):
            d = np.load(per, allow_pickle=True)
            rows += [{k: d[k][i] for k in d.files} for i in range(len(d["f0"]))]
            print("  census: reused cache for %s (%d windows)" % (tag, len(d["f0"])), flush=True)
            continue
        n0 = len(rows)
        g = G[tag]
        for aa, bb in C20.runs(g["eng"], W):
            for s in range(aa, bb - W + 1, STEP):
                e = s + W
                f0w, promw, _, _ = line_of(g["bar"][s:e], FS)
                if not np.isfinite(f0w):
                    continue
                fr, pr_, _, _ = line_of(g["wire"][s:e], FS)
                rows.append(dict(
                    tag=tag, build=BUILD[tag], grp=GROUP[BUILD[tag]], t=g["tr"][s], f0=f0w, prom=promw, fr=fr, promr=pr_,
                    amp=band_at(g["bar"][s:e], f0w), amp1822=GI.band(g["bar"][s:e], 18, 22),
                    ramp=band_at(g["wire"][s:e], f0w) / V.CPD, camp=band_at(g["cmd"][s:e], f0w),
                    tq=float(np.median(np.abs(g["bar"][s:e]))), idx=float(np.median(g["idx"][s:e])),
                    kp=float(np.median(g["kp"][s:e])), v=float(g["vego"][s:e].mean()),
                    rate=float(np.mean(g["rate"][s:e])), ang=float(np.median(np.abs(g["ang"][s:e]))),
                    T=float(np.median(np.abs(g["T100"][s:e])))))
        sub = rows[n0:]
        np.savez(per, **{k: np.array([r[k] for r in sub]) for k in sub[0]})
        print("  census: %s done (%d windows)" % (tag, len(sub)), flush=True)
    R = {k: np.array([r[k] for r in rows]) for k in rows[0]}
    np.savez(cache, **R)
    return R


def part1(G, tags, R=None):
    pr("\n" + "=" * 150)
    pr("1. CENSUS, 12-26 Hz PEAK-TRACKED (2 s windows, 0.5 s step, engaged lateral; present = 12-26 Hz prominence >= 8 AND bar amplitude at f0 +- 2 Hz >= 40 raw)")
    pr("   OLD gate for comparison: prominence >= 8 AND bar 18-22 >= 40 raw (the 2026-09-08 yardstick)")
    pr("=" * 150)
    if R is None:
        verify_line_of(G, tags)
        R = census(G, tags)
    pres = (R["prom"] >= 8) & (R["amp"] >= 40)
    pres_old = (R["prom"] >= 8) & (R["amp1822"] >= 40)
    pr("  windows %d, present (new gate) %d, present (old gate) %d" % (len(R["f0"]), pres.sum(), pres_old.sum()))

    pr("\n1a. f0 (bar line) by build -- new gate | old gate; share of present windows at 13-18 Hz vs 18-22.5 Hz:")
    pr("  %-7s %-28s %-28s %6s %6s | %-28s %6s" % ("build", "f0 new gate", "rate-line f new gate", "pres%", "13-18%", "f0 old gate", "pres%"))
    for b in BUILDS:
        mb = R["build"] == b
        m = pres & mb; mo = pres_old & mb
        if m.any():
            lo = np.mean((R["f0"][m] >= 13) & (R["f0"][m] < 18)) * 100
            pr("  %-7s %-28s %-28s %5.1f%% %5.0f%% | %-28s %5.1f%%" % (
                b, med_iqr(R["f0"][m]), med_iqr(R["fr"][m]), 100 * m.sum() / max(1, mb.sum()), lo, med_iqr(R["f0"][mo]), 100 * mo.sum() / max(1, mb.sum())))
    pr("\n1a'. per route (new gate):")
    for tag in tags:
        m = pres & (R["tag"] == tag)
        if m.any():
            pr("  %-9s %-7s f0 %-28s amp p50 %5.0f raw  presence %.1f %%  13-18 share %.0f %%" % (
                tag, BUILD[tag], med_iqr(R["f0"][m]), np.median(R["amp"][m]), 100 * m.sum() / max(1, (R["tag"] == tag).sum()),
                100 * np.mean((R["f0"][m] >= 13) & (R["f0"][m] < 18))))
    pr("\n1a''. f0 histogram of present windows, 1 Hz bins 12-26, per build (counts):")
    edges = np.arange(12, 27, 1.0)
    pr("  %-7s " % "build" + " ".join("%4d" % e for e in edges[:-1]))
    for b in BUILDS:
        m = pres & (R["build"] == b)
        h, _ = np.histogram(R["f0"][m], edges)
        pr("  %-7s " % b + " ".join("%4d" % v for v in h))

    pr("\n1b. f0 by HANDS (|bar| median raw), pooled per group (new gate):")
    for grp in ("flat-Kp", "flat-Kp-V289", "Kp-LERP"):
        for lab, lo, hi in (("hands-off <400", 0, 400), ("mid 400-700", 400, 700), ("hands-on >700", 700, 1e9), ("hard >1500", 1500, 1e9)):
            m = pres & (R["grp"] == grp) & (R["tq"] >= lo) & (R["tq"] < hi)
            pr("  %-13s %-16s f0 %s" % (grp, lab, med_iqr(R["f0"][m])))

    pr("\n1c. f0 vs state, Spearman rho (p) and OLS slope over p10-p90, present windows (new gate):")
    for grp in ("flat-Kp", "flat-Kp-V289", "Kp-LERP"):
        m = pres & (R["grp"] == grp)
        pr("  group %s (n=%d):" % (grp, m.sum()))
        for key, lab in (("tq", "|bar| raw"), ("idx", "idx"), ("kp", "Kp(idx)"), ("v", "v m/s"), ("rate", "|rate| deg/s"),
                         ("ang", "|angle|"), ("T", "|T| tap"), ("camp", "cmd amp at f0")):
            x, y = R[key][m], R["f0"][m]
            ok = np.isfinite(x) & np.isfinite(y)
            if ok.sum() < 10 or np.std(x[ok]) == 0:
                pr("    %-22s (flat or n<10)" % lab); continue
            rho, p = stats.spearmanr(x[ok], y[ok])
            sl, ic, r, pp, se = stats.linregress(x[ok], y[ok])
            p10, p90 = np.percentile(x[ok], (10, 90))
            pr("    %-22s rho %+.2f (p %.3f)  slope %+.4f +- %.4f Hz/unit  -> %+.2f Hz over p10-p90 [%.1f, %.1f]" % (lab, rho, p, sl, se, sl * (p90 - p10), p10, p90))

    pr("\n1d. THE Kp DISCRIMINATOR (unchanged data, new gate) -- f0 by Kp(idx) bins on r31-r34; idx bins on flat-Kp and on V289:")
    m0 = pres & (R["grp"] == "Kp-LERP")
    for lo, hi in ((240, 300), (300, 400), (400, 500), (500, 600), (600, 700)):
        m = m0 & (R["kp"] >= lo) & (R["kp"] < hi)
        pr("  Kp-LERP       Kp %3d-%3d : f0 %s   amp p50 %.0f" % (lo, hi, med_iqr(R["f0"][m]), np.median(R["amp"][m]) if m.any() else np.nan))
    for grp in ("flat-Kp", "flat-Kp-V289"):
        m0 = pres & (R["grp"] == grp)
        for lo, hi in ((0, 20), (20, 60), (60, 120), (120, 250)):
            m = m0 & (R["idx"] >= lo) & (R["idx"] < hi)
            pr("  %-13s idx %3d-%3d : f0 %s   amp p50 %.0f" % (grp, lo, hi, med_iqr(R["f0"][m]), np.median(R["amp"][m]) if m.any() else np.nan))
    pr("\n1f. speed bins, V282+V288 pooled vs V289:")
    for grp in ("flat-Kp", "flat-Kp-V289"):
        m0 = pres & (R["grp"] == grp)
        for lo, hi in ((0, 2), (2, 3), (3, 6), (6, 12), (12, 40)):
            m = m0 & (R["v"] >= lo) & (R["v"] < hi)
            pr("  %-13s v %2d-%2d m/s : f0 %s" % (grp, lo, hi, med_iqr(R["f0"][m])))

    # -------------------------------------------------------------------- 1e: the widened band holds TWO populations
    pr("\n" + "-" * 150)
    pr("1e. 🛑 THE WIDENED BAND CONTAINS TWO DIFFERENT LINES.  f0 median / n, by LKAS demand index (rows) x speed (cols), present windows.")
    pr("    idx is the live assist-map demand index: idx < 5 means openpilot is asking for essentially nothing, idx >= 20 means the rate loop is working.")
    pr("-" * 150)
    for grp, bl in (("V282+V288", ["V282", "V288"]), ("V281r3", ["V281r3"]), ("V289", ["V289"]), ("Kp-LERP", ["V280r2", "V278r3"])):
        m = pres & np.isin(R["build"], bl)
        pr("  === %s ===" % grp)
        pr("    %-10s" % "idx \\ v" + "".join("%13s" % ("%d-%d m/s" % (a, b)) for a, b in ((0, 6), (6, 12), (12, 20), (20, 40))))
        for ilo, ihi in ((0, 5), (5, 20), (20, 60), (60, 300)):
            cells = []
            for vlo, vhi in ((0, 6), (6, 12), (12, 20), (20, 40)):
                mm = m & (R["idx"] >= ilo) & (R["idx"] < ihi) & (R["v"] >= vlo) & (R["v"] < vhi)
                cells.append("%7.2f/%-5d" % (np.median(R["f0"][mm]), mm.sum()) if mm.sum() >= 15 else "%13s" % ("n=%d" % mm.sum()))
            pr("    %-10s" % ("%d-%d" % (ilo, ihi)) + "".join(cells))
        pr("    cmd amplitude at f0 (raw) by idx bin: " + "  ".join("idx %d-%d: %.1f" % (a, b, np.median(R["camp"][m & (R["idx"] >= a) & (R["idx"] < b)])) for a, b in ((0, 5), (5, 20), (20, 60), (60, 300))))
    pr("  READING (EVIDENCE, from the table above): the LOW-DEMAND line (idx < 5) sits at 12.4-13.8 Hz, falls with speed, carries ~4 raw of command")
    pr("  amplitude at its own frequency, and is at the SAME frequency on V282, V288, V289 and the Kp-LERP builds -- it does not care what the loop is.")
    pr("  The HIGH-DEMAND line (idx >= 20) sits at 20.0 Hz on V278r3/V280r2/V281r3/V282/V288 and at 16.2-16.7 Hz on V289, at EVERY speed bin, and")
    pr("  carries 15-40 raw of command amplitude.  The 2026-09-08 band (15-26 Hz) excluded most of the low-demand line by accident; widening the band")
    pr("  WITHOUT a demand gate mixes the two and drags every pooled median to ~14-15 Hz.  Everything downstream uses the DEMAND-GATED population.")
    pres_loop = pres & (R["idx"] >= DEMAND_MIN)
    pr("\n1e'. the demand-gated loop population (present AND idx >= %g): n=%d of %d present" % (DEMAND_MIN, pres_loop.sum(), pres.sum()))
    pr("  %-8s %-28s %6s | low-demand (idx<5) %-24s" % ("build", "f0 demand-gated", "n", "f0"))
    for b in BUILDS:
        m = pres_loop & (R["build"] == b); ml = pres & (R["build"] == b) & (R["idx"] < 5)
        pr("  %-8s %-28s %6d | %-24s" % (b, med_iqr(R["f0"][m]), m.sum(), med_iqr(R["f0"][ml])))
    pr("\n1e''. THE Kp DISCRIMINATOR, DEMAND-GATED (this is the row the 2026-09-08 'f pinned across Kp' verdict rests on):")
    m0 = pres_loop & (R["grp"] == "Kp-LERP")
    for lo, hi in ((240, 300), (300, 400), (400, 500), (500, 600), (600, 700)):
        m = m0 & (R["kp"] >= lo) & (R["kp"] < hi)
        pr("  Kp-LERP  Kp %3d-%3d : f0 %-28s amp p50 %5.0f  |bar| p50 %5.0f  |T| p50 %5.0f" % (
            lo, hi, med_iqr(R["f0"][m]), *(np.median(R[k][m]) if m.sum() else np.nan for k in ("amp", "tq", "T"))))
    for grp in ("flat-Kp", "flat-Kp-V289"):
        m = pres_loop & (R["grp"] == grp)
        pr("  %-13s (Kp 248 flat)  : f0 %-28s amp p50 %5.0f" % (grp, med_iqr(R["f0"][m]), np.median(R["amp"][m]) if m.sum() else np.nan))
    return R, pres, pres_loop


def part1_decays(G, tags, R, pres, lbl="DEMAND-GATED (idx >= %g)" % DEMAND_MIN, npz="mode_nature_v289_episodes.npz"):
    pr("\n" + "=" * 150)
    pr("2. FREE-DECAY FITS per episode, %s (>= 0.5 s present run): zeta = -gd/(2 pi f0); envelope at f0 +- 2 Hz; f_inst during the decay" % lbl)
    pr("=" * 150)
    eps = []
    for tag in tags:
        g = G[tag]
        sel = np.flatnonzero(R["tag"] == tag)
        wt, wp = R["t"][sel], pres[sel]
        if len(wt) == 0:
            continue
        j = np.clip(np.searchsorted(wt, g["tr"] - 1.0), 0, len(wt) - 1)
        near = np.abs(wt[j] + 1.0 - g["tr"]) < 1.5
        hot = g["eng"] & near & wp[j]
        for a, b in C20.runs(hot, int(0.5 * FS)):
            f0, prom, _, _ = line_of(g["bar"][a:b], FS)
            if not np.isfinite(f0):
                continue
            lo, hi = max(0, a - 100), min(len(g["tr"]), b + 100)
            env = GI.envelope(g["bar"][lo:hi], f0, FS)
            envr = GI.envelope(g["wire"][lo:hi], f0, FS)
            tloc = g["tr"][lo:hi]
            gu, _, gd, dur_d = GI.growth_fit(tloc, env)
            gur, _, gdr, _ = GI.growth_fit(tloc, envr)
            k = int(np.argmax(env))
            k2 = k + (np.flatnonzero(env[k:] <= 0.1 * env[k])[0] if (env[k:] <= 0.1 * env[k]).any() else len(env) - k - 1)
            fi = inst_freq(g["bar"][lo:hi], f0, FS)
            fdec = float(np.median(fi[k:k2])) if k2 - k >= 5 else np.nan
            eps.append(dict(tag=tag, build=BUILD[tag], t0=g["tr"][a], dur=(b - a) / FS, f0=f0, env=float(env[k]), gu=gu, gd=gd, gdr=gdr,
                            zeta=(-gd / (2 * np.pi * f0)) if np.isfinite(gd) else np.nan, zetar=(-gdr / (2 * np.pi * f0)) if np.isfinite(gdr) else np.nan,
                            fdec=fdec, tq=float(np.median(np.abs(g["bar"][a:b]))), v=float(g["vego"][a:b].mean()), kp=float(np.median(g["kp"][a:b]))))
    E = {k: np.array([e[k] for e in eps]) for k in eps[0]}
    np.savez(os.path.join(SCR, npz), **E)
    pr("  episodes: %d  (%s)" % (len(eps), ", ".join("%s=%d" % (t, (E["tag"] == t).sum()) for t in tags)))
    okd = np.isfinite(E["gd"]) & (E["gd"] < 0)
    pr("\n2a. decay-rate distribution (bar envelope), episodes with a measurable decay (gd < 0): n=%d of %d" % (okd.sum(), len(eps)))
    meas = {}
    for b in BUILDS:
        m = okd & (E["build"] == b)
        if m.sum() >= 3:
            z = E["zeta"][m]
            # bootstrap CI on the median zeta and on the median f0
            rng = np.random.default_rng(1)
            bz = [np.median(rng.choice(z, len(z))) for _ in range(400)]
            bf = [np.median(rng.choice(E["f0"][m], m.sum())) for _ in range(400)]
            meas[b] = dict(f=float(np.median(E["f0"][m])), f_lo=float(np.percentile(bf, 2.5)), f_hi=float(np.percentile(bf, 97.5)),
                           f_iqr=(float(np.percentile(E["f0"][m], 25)), float(np.percentile(E["f0"][m], 75))),
                           z=float(np.median(z)), z_lo=float(np.percentile(bz, 2.5)), z_hi=float(np.percentile(bz, 97.5)),
                           z_iqr=(float(np.percentile(z, 25)), float(np.percentile(z, 75))), n=int(m.sum()), env=float(np.median(E["env"][m])))
            pr("  %-7s n=%3d gd /s p10/p50/p90 %6.2f/%6.2f/%6.2f -> zeta p10/p50/p90 %.3f/%.3f/%.3f  (median CI95 %.3f-%.3f; rate-env zeta p50 %.3f)  f_dec p50 %.2f  f0 p50 %.2f (CI95 %.2f-%.2f)  env pk p50 %.0f" % (
                b, m.sum(), *np.percentile(E["gd"][m], (10, 50, 90)), *np.percentile(z, (10, 50, 90)), meas[b]["z_lo"], meas[b]["z_hi"],
                np.nanmedian(E["zetar"][m]), np.nanmedian(E["fdec"][m]), meas[b]["f"], meas[b]["f_lo"], meas[b]["f_hi"], meas[b]["env"]))
    pr("\n2b. V289 episodes split by line frequency (is the 16 Hz line a different animal from the residual ~20 Hz windows?):")
    m = okd & (E["build"] == "V289")
    for lab, mm in (("f0 13-18 Hz", m & (E["f0"] >= 13) & (E["f0"] < 18)), ("f0 18-22.5 Hz", m & (E["f0"] >= 18) & (E["f0"] < 22.5)), ("f0 22.5-26", m & (E["f0"] >= 22.5))):
        if mm.sum() >= 2:
            pr("  %-14s n=%2d  zeta p25/p50/p75 %.3f/%.3f/%.3f  env pk p50 %.0f  f0 p50 %.2f  dur p50 %.2f s" % (
                lab, mm.sum(), *np.percentile(E["zeta"][mm], (25, 50, 75)), np.median(E["env"][mm]), np.median(E["f0"][mm]), np.median(E["dur"][mm])))
        else:
            pr("  %-14s n=%d" % (lab, mm.sum()))
    pr("\n2c. zeta vs Kp on the Kp-LERP routes (unchanged data, new gate):")
    m = okd & np.isin(E["build"], ["V280r2", "V278r3"])
    for lo, hi in ((240, 320), (320, 450), (450, 700)):
        mm = m & (E["kp"] >= lo) & (E["kp"] < hi)
        if mm.sum() >= 3:
            pr("  Kp %3d-%3d n=%3d  zeta p25/p50/p75 %.3f/%.3f/%.3f  env pk p50 %.0f  f0 p50 %.2f" % (lo, hi, mm.sum(), *np.percentile(E["zeta"][mm], (25, 50, 75)), np.median(E["env"][mm]), np.median(E["f0"][mm])))
    pr("\n2d. zeta by hands, V282+V288+V281r3 pooled vs V289:")
    for lab_b, bl in (("flat-Kp V281-288", ["V282", "V288", "V281r3"]), ("V289", ["V289"])):
        m = okd & np.isin(E["build"], bl)
        for lab, lo, hi in (("hands-off <400", 0, 400), ("on >700", 700, 1e9)):
            mm = m & (E["tq"] >= lo) & (E["tq"] < hi)
            if mm.sum() >= 3:
                pr("  %-17s %-15s n=%3d  zeta p25/p50/p75 %.3f/%.3f/%.3f  f0 p50 %.2f" % (lab_b, lab, mm.sum(), *np.percentile(E["zeta"][mm], (25, 50, 75)), np.median(E["f0"][mm])))
    return E, meas


def part1_transfers(G, cells):
    pr("\n" + "=" * 150)
    pr("3. CLOSED-LOOP TRANSFER cmd -> wheel rate / bar, 100 Hz frame axis, Welch nperseg 256, 12-26 Hz; engaged, v < 8, |bar| < 400; resonance fit 13-25 Hz")
    pr("=" * 150)

    def resonance_fit(f, H, flo=12.0, fhi=26.0):
        m = (f >= flo) & (f <= fhi) & np.isfinite(H)
        ff, hh = f[m], np.abs(H[m])
        best = (np.nan, np.nan, np.inf)
        for fn in np.arange(13.0, 25.01, 0.1):
            for ze in np.r_[0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05, 0.07, 0.10, 0.15, 0.2, 0.3, 0.5]:
                r = 1.0 / np.abs(1 - (ff / fn) ** 2 + 2j * ze * ff / fn)
                A = np.exp(np.mean(np.log(hh) - np.log(r)))
                res = np.sqrt(np.mean((np.log(hh) - np.log(A * r)) ** 2))
                if res < best[2]:
                    best = (fn, ze, res)
        return best
    for grp, tl in (("V282 (r39+r3a+r3c)", ["r39", "r3a", "r3c"]), ("V288 (r5e)", ["r5e_v288"]), ("V289 (r62+r63)", ["r62_v289", "r63_v289"])):
        P = C20.Pool(FS, 256); secs = 0.0
        for tag in tl:
            if tag not in G:
                continue
            g = G[tag]
            msk = g["eng"] & (g["vego"] < 8.0) & (np.abs(g["bar"]) < 400)
            for a, b in C20.runs(msk, 256):
                P.add({"c": g["cmd"][a:b] - g["cmd"][a:b].mean(), "r": g["rate_x"][a:b] - g["rate_x"][a:b].mean(), "q": g["bar"][a:b] - g["bar"][a:b].mean()})
                secs += (b - a) / FS
        if P.n == 0:
            pr("  %s: no data" % grp); continue
        f = P.f
        Hcr, Hcq = P.tf("c", "r"), P.tf("c", "q"); ccr, ccq = P.coh("c", "r"), P.coh("c", "q")
        pr("\n  %s: %.0f s, %d windows" % (grp, secs, P.n))
        pr("   f Hz   |H c->r| ang coh   |   |H c->q| ang coh   |  S_qq/S_cc   S_rr/S_cc")
        for f0 in (10, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 26):
            i = np.argmin(np.abs(f - f0))
            pr("   %4.1f   %7.4f %+5.0f %.2f   |   %7.3f %+5.0f %.2f   |  %8.3g   %8.3g" % (
                f[i], abs(Hcr[i]), np.degrees(np.angle(Hcr[i])), ccr[i], abs(Hcq[i]), np.degrees(np.angle(Hcq[i])), ccq[i],
                np.real(P.s("q", "q")[i]) / max(np.real(P.s("c", "c")[i]), 1e-12), np.real(P.s("r", "r")[i]) / max(np.real(P.s("c", "c")[i]), 1e-12)))
        for nm, H in (("cmd->rate", Hcr), ("cmd->bar", Hcq)):
            fn, ze, res = resonance_fit(f, H)
            pr("   resonance fit %-9s : fn %.1f Hz  zeta %.3f  (rms log resid %.2f)" % (nm, fn, ze, res))
        # pooled auto-spectrum peak of the wheel rate 12-26 Hz (the line itself, no input needed)
        Srr = np.real(P.s("r", "r")); m = (f >= 12) & (f <= 26)
        k = np.argmax(Srr[m]); pr("   pooled rate PSD peak in 12-26 Hz: %.2f Hz, x%.1f the band median" % (f[m][k], Srr[m][k] / np.median(Srr[m])))

    pr("\n" + "=" * 150)
    pr("4. PLANT rate/T from the 427 tap at its own instants (50 Hz), engaged v<8 hands-off, nperseg 64 (0.78 Hz); angle RAW and with the 3.9 ms stream offset removed")
    pr("   (the plant does not know which build is flying: V289's rows must agree with V282's if the tap and the timing model are right)")
    pr("=" * 150)
    tapG = {}
    for grp, tl in (("V282 (r39+r3a+r3c)", ["r39", "r3a", "r3c"]), ("V288 (r5e)", ["r5e_v288"]), ("V289 (r62+r63)", ["r62_v289", "r63_v289"]), ("V280r2+V278r3", ["r31", "r32", "r33", "r34"])):
        P = C20.Pool(FST, 64); secs = 0.0
        for tag in tl:
            if tag not in G:
                continue
            g = G[tag]
            msk = g["eng"] & (g["vego"] < 8.0) & (np.abs(g["bar"]) < 400)
            for a, b in C20.runs(msk, 128):
                seg = C20.native_tap_segment(g, a, b)
                if seg is None or len(seg["T"]) < 64:
                    continue
                P.add({k: v - v.mean() for k, v in seg.items()}); secs += (b - a) / FS
        if P.n == 0:
            pr("  %s: no data" % grp); continue
        f = P.f
        Gd = -P.tf("T", "r"); Gc = -P.tf("T", "r", ref="c"); coh_Tr, coh_cr = P.coh("T", "r"), P.coh("c", "r")
        tapG[grp] = (f, Gd, coh_Tr)
        pr("\n  %s: %.0f s, %d windows" % (grp, secs, P.n))
        pr("   f Hz   |G|e-3 angG_raw angG_corr coh_Tr | cmdIV |G| ang_corr coh_cr")
        for f0 in (10, 12, 14, 15.6, 16.4, 17.2, 18, 18.8, 19.5, 20.3, 21.1, 21.9, 22.7, 24.2):
            i = np.argmin(np.abs(f - f0))
            corr = np.exp(-2j * np.pi * f[i] * TAU_STREAM)
            pr("   %4.1f  %6.1f  %+6.0f   %+6.0f    %.2f  | %6.1f  %+6.0f  %.2f" % (
                f[i], 1e3 * abs(Gd[i]), np.degrees(np.angle(Gd[i])), np.degrees(np.angle(Gd[i] * corr)), coh_Tr[i], 1e3 * abs(Gc[i]), np.degrees(np.angle(Gc[i] * corr)), coh_cr[i]))
        i1 = (f >= 18) & (f <= 21); i0 = (f >= 10) & (f <= 15); i2 = (f >= 15) & (f <= 17.5)
        pr("   |G| 18-21 / 10-15 = %.2f ; |G| 15-17.5 / 10-15 = %.2f ; coherence p50 10-15 %.2f, 15-17.5 %.2f, 18-21 %.2f" % (
            np.median(abs(Gd[i1])) / np.median(abs(Gd[i0])), np.median(abs(Gd[i2])) / np.median(abs(Gd[i0])), np.median(coh_Tr[i0]), np.median(coh_Tr[i2]), np.median(coh_Tr[i1])))
    return tapG


# =====================================================================================================================
# PART 2 -- exact closed-loop poles under each build's electronics for each plant hypothesis
# =====================================================================================================================
class ZT:
    """rational function in z, coefficients highest power first."""
    def __init__(self, num, den):
        self.num, self.den = np.atleast_1d(np.asarray(num, float)), np.atleast_1d(np.asarray(den, float))

    def __mul__(self, o):
        if isinstance(o, ZT):
            return ZT(np.polymul(self.num, o.num), np.polymul(self.den, o.den))
        return ZT(self.num * float(o), self.den)

    def __call__(self, f):
        z = np.exp(2j * np.pi * np.asarray(f, float) * TS)
        return np.polyval(self.num, z) / np.polyval(self.den, z)


def elec(c, notch=False, kp=None, kd=None):
    """the return ratio R(z) in T counts per raw rate count: F * C * fade * [N] * Hlag * K6/32768 * z^-1  (no plant, no CPD)."""
    kp = float(c["kp_Y"][0]) if kp is None else float(kp)
    kd = float(c["kd_Y"][0]) if kd is None else float(kd)
    F = ZT([c["fb_b"] / 1024.0, c["fb_b"] / 1024.0], [1.0, -c["fb_a"] / 1024.0])
    C = ZT([kp / 256.0 + kd / 8.0, -kd / 8.0], [1.0, 0.0])
    H = ZT([c["lag_b"] / 1024.0 / 32.0, c["lag_b"] / 1024.0 / 32.0], [1.0, -c["lag_a"] / 1024.0])
    R = F * C * H * ZT([1.0], [1.0, 0.0]) * (254.0 / 256.0 * c["gain"] / 32768.0)
    if notch:
        R = R * ZT(NOTCH_B, NOTCH_A)
    return R


def elec_parts(c, notch, f):
    """phase/magnitude of each element at f (deg), incl. the ZOH half-tick that belongs to the electronics side."""
    z = np.exp(2j * np.pi * f * TS)
    items = [("fb one-pole", 1 / (1 - (c["fb_a"] / 1024.0) / z)), ("fb (1+z^-1)", 1 + 1 / z),
             ("PID C", c["kp_Y"][0] / 256.0 + c["kd_Y"][0] / 8.0 * (1 - 1 / z)), ("output-lag one-pole", 1 / (1 - (c["lag_a"] / 1024.0) / z)),
             ("output lag (1+z^-1)", 1 + 1 / z), ("compute latency z^-1", 1 / z), ("ZOH half-tick", (1 - np.exp(-2j * np.pi * f * TS)) / (2j * np.pi * f * TS))]
    if notch:
        items.append(("notch (as built, Q14)", np.polyval(NOTCH_B, z) / np.polyval(NOTCH_A, z)))
    return items


class PlantH:
    """G(s) = g0 e^{-s tau}/(1+s/w1) [* M or * (1 + kappa (M-1))], tau an integer number of ms; ZOH discretisation at 1 kHz."""
    def __init__(self, g0, tau, f1, fp=None, zp=None, kappa=None, label=""):
        self.g0, self.tau, self.f1, self.fp, self.zp, self.kappa, self.label = g0, tau, f1, fp, zp, kappa, label
        w1 = 2 * np.pi * f1
        num, den = np.array([g0 * w1]), np.array([1.0, w1])
        if fp:
            wp = 2 * np.pi * fp
            md = np.array([1.0, 2 * zp * wp, wp ** 2])
            mn = np.array([wp ** 2]) if kappa is None else np.polyadd((1 - kappa) * md, np.array([kappa * wp ** 2]))
            num, den = np.polymul(num, mn), np.polymul(den, md)
        self.num_s, self.den_s = num, den
        d = int(round(tau / TS))
        self.d = d
        nz, dz, _ = signal.cont2discrete((num, den), TS, method="zoh")
        nz = np.atleast_1d(np.squeeze(nz))
        self.G = ZT(nz, np.polymul(dz, np.r_[1.0, np.zeros(d)]))

    def Gs(self, f):
        s = 2j * np.pi * np.asarray(f, float)
        return np.polyval(self.num_s, s) / np.polyval(self.den_s, s) * np.exp(-s * self.tau)

    def as_dict(self):
        return dict(g0=self.g0, tau=self.tau, f1=self.f1, fp=self.fp, zp=self.zp, kappa=self.kappa, label=self.label)


def loop(R, pl):
    return R * pl.G * CPD


_POLE_CACHE = {}


def cl_poles(L):
    """closed-loop poles (negative feedback): roots of den + num, mapped to s = ln z / T. returns array of (f_damped Hz, zeta, |z|)."""
    key = (L.num.tobytes(), L.den.tobytes())
    hit = _POLE_CACHE.get(key)
    if hit is not None:
        return hit
    n, d = L.num, L.den
    if len(n) > len(d):
        d = np.r_[np.zeros(len(n) - len(d)), d]
    else:
        n = np.r_[np.zeros(len(d) - len(n)), n]
    ch = d + n
    z = np.roots(ch)
    z = z[np.imag(z) > 1e-9]
    s = np.log(z) / TS
    f = np.imag(s) / (2 * np.pi); ze = -np.real(s) / np.abs(s)
    res = np.c_[f, ze, np.abs(z)]
    if len(_POLE_CACHE) > 300000:
        _POLE_CACHE.clear()
    _POLE_CACHE[key] = res
    return res


def dominant(L, lo=10.0, hi=30.0):
    """the least-damped closed-loop pole with damped frequency in [lo, hi]; also the sensitivity peak in the band."""
    P = cl_poles(L)
    m = (P[:, 0] >= lo) & (P[:, 0] <= hi)
    if not m.any():
        return np.nan, np.nan, P
    k = np.argmin(P[m, 1])
    return float(P[m][k, 0]), float(P[m][k, 1]), P


def unstable_any(L):
    P = cl_poles(L)
    return bool((P[:, 2] > 1.0 + 1e-9).any())


def sens(L, f):
    return 1.0 / np.abs(1 + L(f))


SIG_F, SIG_LZ = 0.35, 0.5     # measurement sigmas for the chi-square: line frequency (Hz), ln(zeta)


def chi2(pred_f, pred_z, meas_f, meas_z, unstable=False):
    if not np.isfinite(pred_f):
        return 25.0
    zp = max(pred_z, 1e-3) if not unstable else 1e-3
    return ((pred_f - meas_f) / SIG_F) ** 2 + ((np.log(zp) - np.log(meas_z)) / SIG_LZ) ** 2


def part2(cells, meas, tapG):
    pr("\n" + "=" * 150)
    pr("5. CLOSED-LOOP POLES per plant hypothesis under each build's byte-exact electronics (roots of 1 + L(z) = 0; ZOH plant, integer-ms delay)")
    pr("   V282 and V288 share the loop (the V288 pre-filter is outside it); V289 = notch as built (Q14) on S + fb pole 875/2301")
    pr("=" * 150)
    c282, c289 = cells["V282"], cells["V289"]
    nb = NOTCH_B * 16384
    f_notch = np.arccos(-nb[1] / (2 * nb[0])) * FS1K / (2 * np.pi)      # the numerator's zero: cos(w0) = 31842 / (2 * 16048)
    zN = lambda f: np.polyval(NOTCH_B, np.exp(2j * np.pi * f * TS)) / np.polyval(NOTCH_A, np.exp(2j * np.pi * f * TS))  # noqa: E731
    pr("  notch as built: zero at %.3f Hz; |N| 20.0 Hz %.4f (%.1f dB), 16.5 Hz %.3f / %+.1f deg, 17.0 Hz %.3f / %+.1f deg, 15.0 Hz %.3f / %+.1f deg; DC %.4f" % (
        f_notch, abs(zN(20.0)), 20 * np.log10(abs(zN(20.0))), abs(zN(16.5)), np.degrees(np.angle(zN(16.5))), abs(zN(17.0)), np.degrees(np.angle(zN(17.0))),
        abs(zN(15.0)), np.degrees(np.angle(zN(15.0))), abs(zN(1e-6))))
    R282, R289 = elec(c282), elec(c289, notch=True)
    pr("  electronics (return ratio incl. z^-1, excl. ZOH) V282: 16.5 Hz |R| %.3f ang %+.1f ; 20.0 Hz |R| %.3f ang %+.1f" % (
        abs(R282(16.5)), np.degrees(np.angle(R282(16.5))), abs(R282(20.0)), np.degrees(np.angle(R282(20.0)))))
    pr("  electronics V289:                                16.5 Hz |R| %.3f ang %+.1f ; 20.0 Hz |R| %.3f ang %+.1f" % (
        abs(R289(16.5)), np.degrees(np.angle(R289(16.5))), abs(R289(20.0)), np.degrees(np.angle(R289(20.0)))))
    pr("  V289 - V282 electronics at 16.5 Hz: gain x%.3f, phase %+.1f deg  (fb pole alone x%.3f %+.1f deg; notch alone x%.3f %+.1f deg)" % (
        abs(R289(16.5) / R282(16.5)), np.degrees(np.angle(R289(16.5) / R282(16.5))),
        abs(elec(c289)(16.5) / R282(16.5)), np.degrees(np.angle(elec(c289)(16.5) / R282(16.5))), abs(zN(16.5)), np.degrees(np.angle(zN(16.5)))))

    # measured targets
    M = {b: meas[b] for b in ("V282", "V288", "V289") if b in meas}
    pr("\n  MEASURED targets (free-decay episodes, new gate): " + " ; ".join("%s f %.2f [IQR %.2f-%.2f] zeta %.3f [IQR %.3f-%.3f] n %d" % (
        b, M[b]["f"], *M[b]["f_iqr"], M[b]["z"], *M[b]["z_iqr"], M[b]["n"]) for b in M))
    plants_json = json.load(open(os.path.join(SCR, "loopshape20_plants.json")))
    fams = {}
    for fam, d in plants_json.items():
        fams[fam] = PlantH(d["g0"], d["tau"], d["f1"], d.get("fp"), d.get("zp"), d.get("kappa"), label="%s (2026-09-08 fit)" % fam)

    def eval_family(pl, tagl):
        rows = {}
        for b, R in (("V282", R282), ("V288", R282), ("V289", R289)):
            L = loop(R, pl)
            f, z, P = dominant(L)
            uns = unstable_any(L)
            fg = np.arange(10, 30, 0.02); S = sens(L, fg); k = np.argmax(S)
            rows[b] = dict(f=f, z=z, uns=uns, Ms=float(S[k]), fMs=float(fg[k]), L20=L(20.0), L165=L(16.5), poles=P)
        return rows

    pr("\n5a. THE 2026-09-08 FITS, as they stand, under the three loops.  Pole = least-damped closed-loop pole in 10-30 Hz (f_damped Hz / zeta); Ms and its f; chi2 vs measured; UNS = an unstable closed-loop pole exists")
    pr("  %-32s | %-26s | %-26s | %-26s | %6s %6s" % ("plant", "V282  f / zeta  Ms@f  UNS", "V288  f / zeta  Ms@f  UNS", "V289  f / zeta  Ms@f  UNS", "chi2", "rel.L"))
    table = []
    for fam, pl in fams.items():
        rows = eval_family(pl, None)
        x2 = sum(chi2(rows[b]["f"], rows[b]["z"], M[b]["f"], M[b]["z"], rows[b]["uns"]) for b in M)
        table.append((fam, pl, rows, x2))
    lik = np.exp(-0.5 * np.array([t[3] for t in table])); lik = lik / lik.sum()
    for (fam, pl, rows, x2), lk in zip(table, lik):
        pr("  %-32s | %s | %s | %s | %6.1f %6.3f" % (fam, *["%5.2f / %6.3f %5.1f@%4.1f %s" % (rows[b]["f"], rows[b]["z"], rows[b]["Ms"], rows[b]["fMs"], "UNS" if rows[b]["uns"] else "   ") for b in ("V282", "V288", "V289")], x2, lk))
    pr("  measured                         | %s" % " | ".join("%5.2f / %6.3f" % (M[b]["f"], M[b]["z"]) + " " * 15 for b in ("V282", "V288", "V289")))
    pr("  (chi2 uses sigma_f %.2f Hz, sigma_ln(zeta) %.2f; an unstable pole is scored as zeta 0.001; rel.L = exp(-chi2/2) normalised over the four rows)" % (SIG_F, SIG_LZ))
    for fam, pl, rows, x2 in table:
        pr("    %-12s all closed-loop poles 8-40 Hz:  " % fam + " ; ".join("%s: %s" % (b, ", ".join("%.1f/%.3f" % (p[0], p[1]) for p in rows[b]["poles"] if 8 <= p[0] <= 40)) for b in ("V282", "V289")))
        pr("    %-12s L at the lines: V282 L(20.0) %.2f ang %+.0f | V289 L(16.5) %.2f ang %+.0f, L(20.0) %.2f ang %+.0f" % (
            fam, abs(rows["V282"]["L20"]), np.degrees(np.angle(rows["V282"]["L20"])), abs(rows["V289"]["L165"]), np.degrees(np.angle(rows["V289"]["L165"])),
            abs(rows["V289"]["L20"]), np.degrees(np.angle(rows["V289"]["L20"]))))

    # ---------------------------------------------------------------- joint refit of each family to V282 + V289 (+ off-line |G| 10/15 Hz)
    pr("\n5b. JOINT RE-FIT of each family to BOTH builds (V282 pole + V289 pole + the off-line tap |G|/angle at 10 and 15 Hz, offset-corrected, weight 0.3)")
    pr("    Each family's best joint fit, its per-build prediction, chi2 (poles only) and the relative likelihood across families.  Grid search; tau in whole ms.")
    G_OFF = {10: (42.9, -35.0), 15: (41.4, -42.0)}
    f_meas = {b: M[b]["f"] for b in M}; z_meas = {b: M[b]["z"] for b in M}

    def joint_err(pl, use289=True):
        e = 0.0; det = {}
        for b, R in (("V282", R282), ("V289", R289)):
            if b == "V289" and not use289:
                continue
            L = loop(R, pl); f, z, _ = dominant(L); uns = unstable_any(L)
            e += chi2(f, z, f_meas[b], z_meas[b], uns); det[b] = (f, z, uns)
        for f0, (mag, phr) in G_OFF.items():
            g = pl.Gs(f0) * 1e3; phc = phr - 360 * f0 * TAU_STREAM
            e += 0.3 * ((np.log(abs(g)) - np.log(mag)) / 0.4) ** 2 + 0.3 * ((np.degrees(np.angle(g)) - phc) / 20.0) ** 2
        return e, det

    def search(fam):
        best = (1e18, None)
        if fam == "smooth":
            for tau in range(1, 16):
                for f1 in (1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 30.0):
                    for g0 in np.exp(np.linspace(np.log(0.005), np.log(0.4), 36)):
                        pl = PlantH(g0, tau * TS, f1, label="smooth")
                        e, _ = joint_err(pl)
                        if e < best[0]:
                            best = (e, pl)
        elif fam == "resonant":
            for fp in np.arange(14.0, 24.01, 0.5):
                for zp in (0.01, 0.02, 0.03, 0.05, 0.08, 0.12):
                    for tau in (1, 2, 4, 6, 8):
                        for f1 in (2.0, 5.0, 12.0):
                            for g0 in np.exp(np.linspace(np.log(0.003), np.log(0.3), 14)):
                                pl = PlantH(g0, tau * TS, f1, fp, zp, label="resonant fp %.1f zp %.3f" % (fp, zp))
                                e, _ = joint_err(pl)
                                if e < best[0]:
                                    best = (e, pl)
        elif fam == "smooth+mode":
            for fp in np.arange(14.0, 25.01, 0.5):
                for zp in (0.05, 0.08, 0.12, 0.18, 0.25, 0.35, 0.5):
                    for tau in (2, 4, 6, 8, 10, 13):
                        for f1 in (3.0, 8.0, 20.0):
                            for g0 in np.exp(np.linspace(np.log(0.01), np.log(0.3), 12)):
                                pl = PlantH(g0, tau * TS, f1, fp, zp, label="smooth+mode fp %.1f zp %.2f" % (fp, zp))
                                e, _ = joint_err(pl)
                                if e < best[0]:
                                    best = (e, pl)
        elif fam == "weak-mode":
            for fp in np.arange(14.0, 23.01, 0.5):
                for zp in (0.02, 0.03, 0.05, 0.07, 0.10):
                    for kappa in (0.3, 0.5, 0.8, 1.2):
                        for tau in (4, 7, 10, 13):
                            for f1 in (5.0, 12.0, 30.0):
                                for g0 in np.exp(np.linspace(np.log(0.02), np.log(0.12), 8)):
                                    pl = PlantH(g0, tau * TS, f1, fp, zp, kappa, label="weak-mode fp %.1f zp %.3f kappa %.1f" % (fp, zp, kappa))
                                    e, _ = joint_err(pl)
                                    if e < best[0]:
                                        best = (e, pl)
        return best

    refits = {}
    jt = []
    for fam in ("smooth", "resonant", "smooth+mode", "weak-mode"):
        e, pl = search(fam)
        refits[fam] = pl
        _, det = joint_err(pl)
        x2 = sum(chi2(det[b][0], det[b][1], f_meas[b], z_meas[b], det[b][2]) for b in det)
        jt.append((fam, pl, det, x2, e))
    lik = np.exp(-0.5 * np.array([t[3] for t in jt])); lik = lik / lik.sum()
    pr("  %-52s | %-22s | %-22s | %6s %6s %6s" % ("best joint fit", "V282 f / zeta  UNS", "V289 f / zeta  UNS", "chi2p", "total", "rel.L"))
    for (fam, pl, det, x2, e), lk in zip(jt, lik):
        pr("  %-52s | %5.2f / %6.3f %s | %5.2f / %6.3f %s | %6.1f %6.1f %6.3f" % (
            "%s: g0 %.4f tau %.0f ms f1 %g%s" % (fam, pl.g0, 1e3 * pl.tau, pl.f1, (" fp %.1f zp %.3f%s" % (pl.fp, pl.zp, (" k %.1f" % pl.kappa) if pl.kappa else "")) if pl.fp else ""),
            det["V282"][0], det["V282"][1], "UNS" if det["V282"][2] else "   ", det["V289"][0], det["V289"][1], "UNS" if det["V289"][2] else "   ", x2, e, lk))
    pr("  measured %s" % " ; ".join("%s %.2f / %.3f" % (b, f_meas[b], z_meas[b]) for b in ("V282", "V289")))
    json.dump({fam: pl.as_dict() for fam, pl in refits.items()}, open(os.path.join(SCR, "mode_nature_v289_refits.json"), "w"), indent=1)
    # the refits against the tap plant and the Kp rows
    pr("\n5c. each joint refit vs the tap-measured plant (offset-corrected) and the Kp discriminator (LINEAR poles; the P/D/sum clamps are not in this model)")
    for fam, pl in refits.items():
        pr("  %s:" % pl.label)
        pr("    |G|e-3 / angle:  " + "  ".join("%g Hz %.1f/%+.0f" % (f0, 1e3 * abs(pl.Gs(f0)), np.degrees(np.angle(pl.Gs(f0)))) for f0 in (10, 15, 16.5, 18, 20, 22, 24)))
        line = []
        for kp in (248, 350, 470, 560, 696):
            L = loop(elec(c282, kp=kp), pl); f, z, _ = dominant(L)
            line.append("Kp %d: %.2f/%.3f%s" % (kp, f, z, " UNS" if unstable_any(L) else ""))
        pr("    V282-type loop vs Kp: " + " ; ".join(line) + "   (measured r31-r34: f 20.01 -> 20.57 by Kp bin, zeta 0.036 -> 0.019, never unstable)")
        # phase crossover of the OPEN loop vs Kp (what a saturation-limited cycle would sit at)
        fg = np.arange(8, 40, 0.01)
        line = []
        for kp in (248, 350, 470, 696):
            L = loop(elec(c282, kp=kp), pl); ph = np.degrees(np.unwrap(np.angle(L(fg))))
            i = np.flatnonzero(np.diff(np.sign(ph + 180)) != 0)
            line.append("Kp %d: f180 %s |L| %s" % (kp, ", ".join("%.1f" % fg[j] for j in i[:2]), ", ".join("%.2f" % abs(L(fg[j])) for j in i[:2])))
        pr("    open-loop -180 deg crossings: " + " ; ".join(line))
    return fams, refits, M, R282, R289


# =====================================================================================================================
# PART 4 -- V289 as an experiment: back out the plant at the two line frequencies
# =====================================================================================================================
def part4(cells, M, R282, R289, fams, refits, tapG):
    pr("\n" + "=" * 150)
    pr("6. V289 AS AN EXPERIMENT -- the plant's phase and magnitude at the two measured line frequencies, backed out from the electronics")
    pr("=" * 150)
    pr("  CONDITION USED: at a lightly damped CLOSED-LOOP pole that is the loop's own (its residue in S is order 1), L(j w0) sits within |1+L| ~ 2 zeta of -1,")
    pr("  so angle(L(w0)) = -180 deg +- 2 zeta rad and |L(w0)| = 1 +- 2 zeta.  This is the peak-of-|S| condition made quantitative, and it is the")
    pr("  -180 deg condition with an error bar.  It does NOT hold for a weakly coupled plant mode the loop merely de-damps (small residue in S:")
    pr("  the weak-mode fit has zeta 0.019 with |1+L|min 0.27) -- but that reading predicts NO frequency shift under V289 (5a), and V289 shifted 3.5 Hz.")
    pr("  Electronics phase includes the ZOH half-tick; the plant point is therefore 'motor-current command at the hold -> wheel rate on the 0x18F wire'.")
    c282, c289 = cells["V282"], cells["V289"]
    res = {}
    for b, R, c, notch in (("V282", R282, c282, False), ("V289", R289, c289, True)):
        f0 = M[b]["f"]; ze = M[b]["z"]
        flo, fhi = M[b]["f_iqr"]
        zlo, zhi = M[b]["z_iqr"]
        z = np.exp(2j * np.pi * f0 * TS)
        zoh = (1 - np.exp(-2j * np.pi * f0 * TS)) / (2j * np.pi * f0 * TS)
        Re = R(f0) * zoh * CPD                       # T counts per (deg/s) incl. hold
        phe = np.degrees(np.angle(Re)); mage = abs(Re)
        # error bars: (i) the condition, +- 2 zeta rad (use the IQR-high zeta as the conservative bound); (ii) f0 spread through the electronics slope
        dphe_df = np.degrees(np.angle(R(f0 + 0.1) * (1 - np.exp(-2j * np.pi * (f0 + 0.1) * TS)) / (2j * np.pi * (f0 + 0.1) * TS) / Re)) / 0.1
        e_cond = np.degrees(2 * zhi)
        e_f = abs(dphe_df) * (fhi - flo) / 2
        php = -180.0 - phe
        magp = 1.0 / mage
        res[b] = dict(f=f0, php=php, e_cond=e_cond, e_f=e_f, e_tot=np.hypot(e_cond, e_f), magp=magp, mag_lo=magp / (1 + 2 * zhi), mag_hi=magp / max(1 - 2 * zhi, 0.5), phe=phe, mage=mage, zeta=ze)
        pr("\n  %s: line f0 %.2f Hz [IQR %.2f-%.2f], zeta %.3f [IQR %.3f-%.3f]" % (b, f0, flo, fhi, ze, zlo, zhi))
        for nm, v in elec_parts(c, notch, f0):
            pr("    %-26s |.| %8.4f  phase %+7.1f deg" % (nm, abs(v), np.degrees(np.angle(v))))
        pr("    => electronics at f0 (x CPD 8): |Re| %.3f T counts per deg/s, phase %+.1f deg (slope %+.1f deg/Hz)" % (mage, phe, dphe_df))
        pr("    => PLANT at %.2f Hz: phase %+.1f deg +- %.1f (condition +-%.1f, f-spread +-%.1f);  |G| %.1f e-3 deg/s per T count [%.1f - %.1f]" % (
            f0, php, res[b]["e_tot"], e_cond, e_f, 1e3 * magp, 1e3 * res[b]["mag_lo"], 1e3 * res[b]["mag_hi"]))
    a, b = res["V282"], res["V289"]
    slope = (a["php"] - b["php"]) / (a["f"] - b["f"])
    eslope = np.hypot(a["e_tot"], b["e_tot"]) / abs(a["f"] - b["f"])
    pr("\n  TWO-POINT PLANT: phase %+.1f deg @ %.2f Hz and %+.1f deg @ %.2f Hz -> slope %+.1f +- %.1f deg/Hz = an equivalent delay of %.1f +- %.1f ms if all of it were delay" % (
        b["php"], b["f"], a["php"], a["f"], slope, eslope, -slope / 360 * 1e3, eslope / 360 * 1e3))
    pr("  |G| ratio 20/16.5: %.2f (a bump toward 20 Hz if > 1; the tap read x%.2f at 18-21 over 10-15 on V282)" % (a["magp"] / b["magp"], 1.68))
    pr("\n  cross-check against the tap-measured plant (offset-corrected, engaged v<8 hands-off) at the nearest bins:")
    for grp, (f, Gd, coh) in tapG.items():
        s = []
        for f0 in (b["f"], a["f"]):
            i = np.argmin(np.abs(f - f0)); corr = np.exp(-2j * np.pi * f[i] * TAU_STREAM)
            s.append("%.1f Hz |G| %.1f e-3 ang %+.0f (raw %+.0f) coh %.2f" % (f[i], 1e3 * abs(Gd[i]), np.degrees(np.angle(Gd[i] * corr)), np.degrees(np.angle(Gd[i])), coh[i]))
        pr("    %-24s " % grp + " | ".join(s))
    pr("\n  the fits at the two backed-out points (phase / |G| e-3):")
    for nm, D in (("2026-09-08 fits", fams), ("joint refits", refits)):
        for fam, pl in D.items():
            pr("    %-16s %-14s 16.5 Hz %+6.0f / %5.1f   20.0 Hz %+6.0f / %5.1f" % (nm, fam, np.degrees(np.angle(pl.Gs(b["f"]))), 1e3 * abs(pl.Gs(b["f"])), np.degrees(np.angle(pl.Gs(a["f"]))), 1e3 * abs(pl.Gs(a["f"]))))
    pr("    %-16s %-14s 16.5 Hz %+6.0f / %5.1f   20.0 Hz %+6.0f / %5.1f   (+- %.0f / %.0f deg)" % ("BACKED OUT", "measured", b["php"], 1e3 * b["magp"], a["php"], 1e3 * a["magp"], b["e_tot"], a["e_tot"]))
    # what the V289 loop looks like at 20 Hz given the backed-out plant at 20 Hz (interpolating nothing): the notch's residual
    z20 = R289(20.0) * (1 - np.exp(-2j * np.pi * 20.0 * TS)) / (2j * np.pi * 20.0 * TS) * CPD * a["magp"] * np.exp(1j * np.radians(a["php"]))
    z165 = R282(b["f"]) * (1 - np.exp(-2j * np.pi * b["f"] * TS)) / (2j * np.pi * b["f"] * TS) * CPD * b["magp"] * np.exp(1j * np.radians(b["php"]))
    pr("\n  consistency: with the backed-out plant, V289's loop at 20.0 Hz is |L| %.3f ang %+.0f (the notch took it out), and V282's loop at %.1f Hz was |L| %.2f ang %+.0f" % (
        abs(z20), np.degrees(np.angle(z20)), b["f"], abs(z165), np.degrees(np.angle(z165))))
    pr("  -> under V282 the loop at 16.5 Hz had %.0f deg of phase margin to -180 and %.2f of gain; V289's fb pole (+%.1f deg) and the notch skirt (%+.1f deg, x%.2f) closed that." % (
        180 + np.degrees(np.angle(z165)), abs(z165), np.degrees(np.angle(elec(c289)(b["f"]) / R282(b["f"]))),
        np.degrees(np.angle(np.polyval(NOTCH_B, np.exp(2j * np.pi * b["f"] * TS)) / np.polyval(NOTCH_A, np.exp(2j * np.pi * b["f"] * TS)))),
        abs(np.polyval(NOTCH_B, np.exp(2j * np.pi * b["f"] * TS)) / np.polyval(NOTCH_A, np.exp(2j * np.pi * b["f"] * TS)))))
    return res


def main():
    nocensus = "--nocensus" in sys.argv
    stage1_pkl = os.path.join(SCR, "mode_nature_v289_stage1.pkl")
    if "--stage2" in sys.argv and os.path.exists(stage1_pkl):
        # RESUME: parts 1-4 already computed and on disk; recompute only the model parts (5, 6).
        import pickle
        with open(stage1_pkl, "rb") as fh:
            st = pickle.load(fh)
        OUT.extend(st["out"])
        cells = {k: GI.read_cells(p) for k, p in IMG.items()}
        fams, refits, M, R282, R289 = part2(cells, st["meas"], st["tapG"])
        part4(cells, M, R282, R289, fams, refits, st["tapG"])
        with open(os.path.join(SCR, "mode_nature_v289_recensus.txt"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(OUT) + "\n")
        pr("\nwrote _scratch/mode_nature_v289_recensus.txt")
        return
    cells = {k: GI.read_cells(p) for k, p in IMG.items()}
    pr("cells per build (Kp knots / Kd / lag / fb / gain / Dclamp):")
    for k, c in cells.items():
        pr("  %-7s Kp %s  Kd %s  lag %d/%d  fb %d/%d  gain %d  Dclamp %d" % (
            k, c["kp_Y"].astype(int).tolist(), c["kd_Y"].astype(int).tolist(), c["lag_a"], c["lag_b"], c["fb_a"], c["fb_b"], c["gain"], c["d_clamp"]))
    assert (cells["V289"]["fb_a"], cells["V289"]["fb_b"]) == (875, 2301), "V289 image fb pole is not 875/2301"
    assert (cells["V282"]["fb_a"], cells["V282"]["fb_b"]) == (923, 1560)
    G = {}
    for tag in ROUTES:
        try:
            G[tag] = load_route(tag, cells)
            pr("loaded %-9s %-7s %.0f s, %.0f s engaged" % (tag, BUILD[tag], G[tag]["tr"][-1], G[tag]["eng"].sum() / FS))
        except Exception as e:  # noqa: BLE001
            pr("FAILED %s: %r" % (tag, e))
    tags = [t for t in ROUTES if t in G]
    R = None
    cache = os.path.join(SCR, "mode_nature_v289_windows.npz")
    if nocensus and os.path.exists(cache):
        R = dict(np.load(cache, allow_pickle=True))
    R, pres, pres_loop = part1(G, tags, R)
    E, meas = part1_decays(G, tags, R, pres_loop)
    part1_decays(G, tags, R, pres & (R["idx"] < 5), lbl="LOW-DEMAND CONTROL (idx < 5, the other line -- for the record; NOT used downstream)",
                 npz="mode_nature_v289_episodes_lowdemand.npz")
    tapG = part1_transfers(G, cells)
    import pickle
    with open(stage1_pkl, "wb") as fh:                 # so a killed run resumes at part 5 (--stage2)
        pickle.dump(dict(out=list(OUT), meas=meas, tapG=tapG), fh)
    pr("  [stage-1 cache written: mode_nature_v289_stage1.pkl -- rerun with --stage2 to skip parts 1-4]")
    fams, refits, M, R282, R289 = part2(cells, meas, tapG)
    part4(cells, M, R282, R289, fams, refits, tapG)
    with open(os.path.join(SCR, "mode_nature_v289_recensus.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    pr("\nwrote _scratch/mode_nature_v289_recensus.txt")


if __name__ == "__main__":
    main()
