# -*- coding: utf-8 -*-
"""studies/grind/grind1_dclamp_resize_allstrata.py -- RE-SIZING the D clamp after adversary B's FAIL.
Subagent `shape`, 2026-09-06.  ANALYSIS ONLY.  Builds nothing, sends nothing, flashes nothing.

Adversary B (docs/review/ADV-V287-B-UNITS-STRATA-2026-09-06.md) FAILED 2560 on F2 (three unsampled
strata, 20-28 % of engaged time, where the clamp becomes a local Kd cut) and F4 (endpoint thresholds
swallowed by their own spread).  Its machinery reproduces my Appendix B numbers to 3 digits on my
windows, so the divergence is stratum coverage and not method.  I adopt its stratification verbatim.

LADDER: 10240 (today) / 7680 / 6144 / 5120 / 3840 / 2560.
PART 1  admissibility per stratum per dose: D_sp-dominance % of binding ticks, p99|D_fb|/clamp, bind %
PART 2  the measured in-band effective-Kd multiplier at 6-9 Hz and 18-22 Hz, per stratum per dose
PART 3  the onset/steady 18-22 Hz envelope of T, ROUTE-WIDE on top-1 % command-step onsets (so it
        always exists), with the onset statistic's own WITHIN-ROUTE spread
PART 4  the 7.3 Hz ring cost: Re@7 in the loaded stratum with the servo arm's Kd scaled by the measured
        multiplier, and the implied |L_tot| against the gate 0.983 (the CI upper bound)
PART 5  the pick

Run: python grind1_dclamp_resize_allstrata.py   (writes _scratch/grind1_dclamp_resize_allstrata.txt)
"""
import os
import sys
import math
import cmath
import struct

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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


ROOT = os.environ["ACCORD_FIRMWARE_ROOT"] + "/analysis-2020accord/"
IMG = ROOT + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
B = open(IMG, "rb").read()
u16 = lambda a: struct.unpack_from("<H", B, a)[0]
D_TODAY = u16(0xC61B6)          # 0xC61B6, NOT 0xC61BA -- the decompose script's line 47 bug is fixed there too
LAG_A, LAG_B, FB_A, FB_B = u16(0xC63EC), u16(0xC63EE), u16(0xC63E8), u16(0xC63EA)
FS, FS1K, KD, KP0 = 100.0, 1000.0, 128.0, 248.0
LADDER = [D_TODAY, 7680, 6144, 5120, 3840, 2560]

cells = GI.read_cells(IMG)
G = {}
for tag in ("r39", "r3a", "r3c"):
    try:
        C20.BUILD[tag] = "V282"
    except Exception:
        pass
    G[tag] = C20.load(tag)
    G[tag]["tr"] = G[tag]["t"] - G[tag]["t"][0]

STRATA = [
    ("CREEP hands-off (the design's stratum)", lambda g: g["eng"] & (g["vego"] >= 1) & (g["vego"] < 3) & (np.abs(g["bar"]) < 400)),
    ("LOW-MID hands-off 3-8 m/s", lambda g: g["eng"] & (g["vego"] >= 3) & (g["vego"] < 8) & (np.abs(g["bar"]) < 400)),
    ("SUBURBAN hands-off 8-15 m/s", lambda g: g["eng"] & (g["vego"] >= 8) & (g["vego"] < 15) & (np.abs(g["bar"]) < 400)),
    ("HIGHWAY hands-off >15 m/s", lambda g: g["eng"] & (g["vego"] >= 15) & (np.abs(g["bar"]) < 400)),
    ("HANDS-ON |bar|>700", lambda g: g["eng"] & (np.abs(g["bar"]) > 700)),
    ("HANDS-ON HARD |bar|>1500", lambda g: g["eng"] & (np.abs(g["bar"]) > 1500)),
    ("LOADED HIGH-ANGLE |ang|>60", lambda g: g["eng"] & (np.abs(g["ang"]) > 60)),
    ("FAST WHEEL >25 deg/s", lambda g: g["eng"] & (np.abs(g["rate_x"]) > 25)),
]


def runs_of(m, minlen):
    d = np.diff(np.r_[0, m.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


pr("=" * 152)
pr("RE-SIZING THE D CLAMP OVER ADVERSARY B's FULL STRATIFICATION -- ladder %s" % " / ".join(str(x) for x in LADDER))
pr("=" * 152)
pr("  cell 0xC61B6 = %d today.  Adversary B's strata adopted verbatim; its p99|D_fb|/clamp and D_sp-dominance" % D_TODAY)
pr("  definitions adopted verbatim.  One simulate per segment, all six doses evaluated post-hoc from the same")
pr("  D_raw, so the ladder is internally paired and costs no extra mirror runs.")

# ---------------------------------------------------------------- collect D_raw per stratum
SEG = {}
for name, sel in STRATA:
    pool = []
    for tag in ("r39", "r3a", "r3c"):
        g = G[tag]
        m = sel(g) & g["eng"]
        md = (np.convolve(m.astype(int), np.ones(31, int), "same") > 0) & g["eng"]
        for a_, b_ in runs_of(md, 150)[:30]:
            b_ = min(b_, a_ + 4000)
            try:
                s0 = GI.simulate(g, a_, b_, cells)
            except Exception:
                continue
            live = np.repeat(g["eng"][s0["seg"]], 10)
            if live.sum() < 400:
                continue
            dsp = np.r_[0.0, np.diff(32.0 * s0["sp"])]
            dfb = np.r_[0.0, np.diff(s0["fb"])]
            pool.append((np.floor(dsp * KD / 8.0)[live], np.floor(-dfb * KD / 8.0)[live],
                         np.floor((dsp - dfb) * KD / 8.0)[live]))
    if pool:
        SEG[name] = pool
    pr("  collected %-42s %5d segments, %8.1f s" % (name, len(pool), sum(len(p[2]) for p in pool) / FS1K))

pr("")
pr("=" * 152)
pr("PART 1 -- ADMISSIBILITY PER STRATUM PER DOSE.  ADMISSIBLE = D_sp-dominance >= 80 % AND p99|D_fb|/clamp < 1.0")
pr("=" * 152)
pr("  %-42s %8s | %s" % ("stratum", "s", "".join("%-24s" % ("clamp %d" % d) for d in LADDER)))
pr("  %-42s %8s | %s" % ("", "", "".join("%-24s" % "dom%  p99r  bind%   " for d in LADDER)))
ADM = {}
for name, pool in SEG.items():
    Dsp = np.concatenate([p[0] for p in pool])
    Dfb = np.concatenate([p[1] for p in pool])
    Draw = np.concatenate([p[2] for p in pool])
    cells_out = []
    for d in LADDER:
        bm = np.abs(Draw) > d
        dom = 100.0 * (np.abs(Dsp[bm]) > np.abs(Dfb[bm])).mean() if bm.any() else 100.0
        p99r = np.percentile(np.abs(Dfb), 99) / d
        bind = 100.0 * bm.mean()
        ADM[(name, d)] = (dom, p99r, bind)
        flag = "*" if (dom >= 80.0 and p99r < 1.0) else " "
        cells_out.append("%s%5.1f %6.2f %6.2f  " % (flag, dom, p99r, bind))
    pr("  %-42s %8.1f | %s" % (name, len(Draw) / FS1K, "".join("%-24s" % c for c in cells_out)))
pr("  ('*' = admissible in that stratum at that dose.)")
pr("")
pr("  ADMISSIBLE IN **EVERY** STRATUM?")
for d in LADDER:
    bad = [n for n in SEG if not (ADM[(n, d)][0] >= 80.0 and ADM[(n, d)][1] < 1.0)]
    pr("    clamp %5d : %s%s" % (d, "YES" if not bad else "NO",
                                 "" if not bad else "  -- fails in: " + "; ".join(b[:34] for b in bad)))

# ---------------------------------------------------------------- PART 2
pr("")
pr("=" * 152)
pr("PART 2 -- THE MEASURED IN-BAND EFFECTIVE-Kd MULTIPLIER (adversary B's PART 5 method, full ladder)")
pr("=" * 152)
pr("  ratio = band-amplitude of clip(D_raw, +-L) / band-amplitude of D_raw.  A ratio < 1 IS a local Kd cut.")
pr("  %-42s | %s" % ("stratum", "".join("%-17s" % ("clamp %d" % d) for d in LADDER)))
pr("  %-42s | %s" % ("", "".join("%-17s" % "6-9Hz  18-22Hz " for d in LADDER)))
MULT = {}
for name, pool in SEG.items():
    cells_out = []
    for d in LADDER:
        row = []
        for lo, hi in ((6.0, 9.0), (18.0, 22.0)):
            num = den = 0.0
            for _, _, Draw in pool:
                if len(Draw) < 512:
                    continue
                num += C20.bamp(np.clip(Draw, -d, d), lo, hi, FS1K) ** 2 * len(Draw)
                den += C20.bamp(Draw, lo, hi, FS1K) ** 2 * len(Draw)
            row.append(math.sqrt(num / den) if den > 0 else float("nan"))
        MULT[(name, d)] = row
        cells_out.append("%6.3f %8.3f  " % (row[0], row[1]))
    pr("  %-42s | %s" % (name, "".join("%-17s" % c for c in cells_out)))

# ---------------------------------------------------------------- PART 3
pr("")
pr("=" * 152)
pr("PART 3 -- THE ONSET STATISTIC, ROUTE-WIDE (not only bookmarked episodes), and its WITHIN-ROUTE SPREAD")
pr("=" * 152)
pr("  Onset = the 0.5 s after a command step in the top 1 % of non-zero |d(sp)| over the WHOLE engaged route.")
pr("  Steady = engaged ticks with no step above the median step size within 0.3 s.  Both always exist.")
ONS = {}
for tag in ("r39", "r3c"):
    g = G[tag]
    ev_per_dose = {d: [] for d in LADDER}
    st_per_dose = {d: [] for d in LADDER}
    for a_, b_ in runs_of(g["eng"], 1500)[:6]:
        b_ = min(b_, a_ + 20000)
        base = None
        for d in LADDER:
            old = V.D_CLAMP
            V.D_CLAMP = d
            try:
                sN = GI.simulate(g, a_, b_, cells)
            finally:
                V.D_CLAMP = old
            dsp = np.abs(np.r_[0.0, np.diff(32.0 * sN["sp"])])
            nz = dsp[dsp > 0]
            if len(nz) < 100:
                continue
            thr = np.percentile(nz, 99)
            med = np.percentile(nz, 50)
            starts = np.flatnonzero(dsp >= thr)
            for i in starts[:400]:
                if i + 500 <= len(sN["T"]):
                    ev_per_dose[d].append(C20.bamp(sN["T"][i:i + 500], 18.0, 22.0, FS1K))
            recent = np.convolve((dsp > med).astype(float), np.ones(300), mode="same") > 0
            stm = ~recent
            sr = runs_of(stm, 500)
            for a2, b2 in sr[:200]:
                st_per_dose[d].append(C20.bamp(sN["T"][a2:b2], 18.0, 22.0, FS1K))
    ONS[tag] = (ev_per_dose, st_per_dose)
    pr("")
    pr("  ROUTE %s -- %d onset events, %d steady runs" % (tag, len(ev_per_dose[LADDER[0]]), len(st_per_dose[LADDER[0]])))
    pr("  %-8s %10s %10s %10s | %10s %10s | %s" % (
        "clamp", "onset p50", "onset p25", "onset p75", "steady p50", "x base", "onset x base"))
    b_on = np.median(ev_per_dose[LADDER[0]]) if ev_per_dose[LADDER[0]] else float("nan")
    b_st = np.median(st_per_dose[LADDER[0]]) if st_per_dose[LADDER[0]] else float("nan")
    for d in LADDER:
        e = np.array(ev_per_dose[d])
        s_ = np.array(st_per_dose[d])
        if len(e) == 0:
            continue
        pr("  %-8d %10.2f %10.2f %10.2f | %10.2f %10.3f | %12.3f" % (
            d, np.median(e), np.percentile(e, 25), np.percentile(e, 75),
            np.median(s_) if len(s_) else float("nan"),
            (np.median(s_) / b_st) if len(s_) and b_st else float("nan"),
            np.median(e) / b_on if b_on else float("nan")))
    e0 = np.array(ev_per_dose[LADDER[0]])
    if len(e0) > 4:
        iqr = np.percentile(e0, 75) - np.percentile(e0, 25)
        se = 1.253 * (iqr / 1.349) / math.sqrt(len(e0))
        pr("    WITHIN-ROUTE SPREAD of the onset statistic on the UNCHANGED build: p25-p75 = %.2f-%.2f (IQR %.2f)," % (
            np.percentile(e0, 25), np.percentile(e0, 75), iqr))
        pr("    n = %d events, so the MEDIAN's standard error is %.3f = %.1f %% of the median." % (
            len(e0), se, 100.0 * se / np.median(e0)))
        pr("    => a shift is resolvable at 2 SE if it exceeds x%.3f." % (1.0 - 2 * se / np.median(e0)))

# ---------------------------------------------------------------- PART 4
pr("")
pr("=" * 152)
pr("PART 4 -- THE 7.3 Hz RING COST, with the servo arm's Kd scaled by the MEASURED in-band multiplier")
pr("=" * 152)
z = lambda f: cmath.exp(2j * math.pi * f * 1e-3)
Cc = lambda f, kp=KP0, kd=KD: kp / 256.0 + (kd / 8.0) * (1 - 1 / z(f))
Ls_, Lr_ = 0.55 * cmath.exp(1j * math.radians(96)), 1.19 * cmath.exp(1j * math.radians(-27))
BASE = abs(Ls_ + Lr_)
LOADED = "LOADED HIGH-ANGLE |ang|>60"
pr("  The clamp's in-band multiplier m at 6-9 Hz in the LOADED stratum is an effective Kd of m*128 THERE.")
pr("  Ls scales by C(7.3, Kp, m*128) / C(7.3, Kp, 128).  Lr (the r24 arm) is untouched.  Registered")
pr("  |L_tot| = 0.980 [0.971-0.983]; the GATE is the CI UPPER BOUND, 0.983.")
pr("")
pr("  %-8s %12s %12s %14s %14s %10s %s" % (
    "clamp", "m @6-9Hz", "Kd_eff", "|L_tot| pred", "vs gate 0.983", "Re@7", "verdict"))
LANE7 = dict(As=2.50, ps=-63.2, Ar=3.37, pr_=+166.0)
S_R24 = 0.43
for d in LADDER:
    m = MULT.get((LOADED, d), [float("nan"), float("nan")])[0]
    if m != m:
        continue
    kdeff = m * KD
    Rs = Cc(7.3, KP0, kdeff) / Cc(7.3, KP0, KD)
    ring = 0.980 * abs(Ls_ * Rs + Lr_) / BASE
    R7 = Cc(7.0, KP0, kdeff) / Cc(7.0, KP0, KD)
    Ps = LANE7["As"] * cmath.exp(1j * math.radians(LANE7["ps"])) * R7
    Pr_ = LANE7["Ar"] * cmath.exp(1j * math.radians(LANE7["pr_"])) * S_R24
    pr("  %-8d %12.3f %12.1f %14.3f %14s %10.2f %s" % (
        d, m, kdeff, ring, "PASS" if ring <= 0.983 else "**FAIL**", (Ps + Pr_).real,
        "" if ring <= 0.983 else "  ring re-armed"))

# ---------------------------------------------------------------- PART 5
pr("")
pr("=" * 152)
pr("PART 5 -- THE PICK")
pr("=" * 152)
ok_adm = [d for d in LADDER if all(ADM[(n, d)][0] >= 80.0 and ADM[(n, d)][1] < 1.0 for n in SEG)]
ok_ring = []
for d in LADDER:
    m = MULT.get((LOADED, d), [float("nan")])[0]
    if m != m:
        continue
    Rs = Cc(7.3, KP0, m * KD) / Cc(7.3, KP0, KD)
    if 0.980 * abs(Ls_ * Rs + Lr_) / BASE <= 0.983:
        ok_ring.append(d)
pr("  admissible in EVERY stratum : %s" % (", ".join(str(x) for x in ok_adm) if ok_adm else "NONE"))
pr("  ring gate 0.983 passes at   : %s" % (", ".join(str(x) for x in ok_ring) if ok_ring else "NONE"))
both = [d for d in LADDER if d in ok_adm and d in ok_ring and d != D_TODAY]
pr("  BOTH, and an actual dose    : %s" % (", ".join(str(x) for x in both) if both else "NONE"))

with open(os.path.join(SCR, "grind1_dclamp_resize_allstrata.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT) + "\n")
pr("")
pr("[written to _scratch/grind1_dclamp_resize_allstrata.txt]")
