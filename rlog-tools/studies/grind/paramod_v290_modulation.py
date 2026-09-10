# -*- coding: utf-8 -*-
r"""paramod 2026-09-09 -- ITEM 1: IS THE SCHEDULED-Kd ROW S A PARAMETRIC MODULATION ON THE WIRE?

DESIGN STUDY.  Builds nothing, flashes nothing, sends nothing.

Row S (agent `reconcile`, docs/review/V290-DECISION-TABLE-2026-09-09.md) sets the slot-7 Kd LERP record
0xE511C to Y = [96, 96, 96, 128] on the shipped knots X = [0, 11, 22, 32].  The lookup high-clamps above
X[3] = 32 (0x29EA0/0x29EB0), so the delivered Kd surface is

      Kd(idx) = 96                            idx <= 22       <- knot 11 is a NO-OP under row S
              = 96 + 32*(idx-22)/(32-22)      22 < idx < 32   <- the RAMP, dKd/didx = +3.2
              = 128                           idx >= 32       <- byte-identical to V282

The hazard: `idx` is the rectified openpilot 0xE4 demand (reqaxis, TRACE-2026-09-09-kp-kd-schedule-axis.md,
1 idx LSB = 16.1257 wire counts), and openpilot's command carries an ECHO of the wheel ring through its own
unfiltered 100 Hz angle measurement.  So Kd(t) is modulated BY THE RING ITSELF.  A loop gain that oscillates
at ~2x a mode's frequency is the textbook parametric pump (memory accord-parametric-pump-intervention-never-run,
where V59 MEASURED a 42.19 Hz pump into a 21.09 Hz mode, prominence 11.10x, and the intervention was never run).

This script measures the modulation FROM THE WIRE, not from a model:
  * knot-crossing rates for 11 / 22 / 32, all engaged and inside grinding episodes and 7 Hz strong-turn windows;
  * the duty of time inside the RAMP band (22, 32) and within +-delta of each knot;
  * the spectrum of the delivered Kd(t) trace, and the fraction of its variance at f_ring, 2*f_ring, 7 and 14 Hz;
  * the modulation depth epsilon = (Kdmax - Kdmin)/(Kdmax + Kdmin) per episode, the same statistic V59 reported.

Run:  python rlog-tools/studies/grind/paramod_v290_modulation.py
Out:  rlog-tools/studies/grind/_scratch/paramod_v290_modulation.txt (+ .json)
"""
import json
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
import creep20_loop_id as C20                 # noqa: E402
import kpkd_axis_r62_r63 as AX                # noqa: E402  (reqaxis's byte-exact demand() and cells())

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
DT = 1.0 / FS
CENSUS_PKL = os.path.join(HERE, "_scratch", "grind1_census_v289_r62_r63_cache.pkl")
OUT = []
J = {}

# row S and the alternatives sized in item 3
KDX = np.array([0.0, 11.0, 22.0, 32.0])
ROWS = {
    "V282 (flat 128)":       np.array([128.0, 128.0, 128.0, 128.0]),
    "S  Y=[96,96,96,128]":   np.array([96.0, 96.0, 96.0, 128.0]),
    "S' Y=[112,112,112,128]": np.array([112.0, 112.0, 112.0, 128.0]),
    "flat 96 (unschedulable)": np.array([96.0, 96.0, 96.0, 96.0]),
}
ROUTES = ["r62_v289", "r63_v289", "r5e_v288", "r39"]
IMG_OF = {"r62_v289": "V289", "r63_v289": "V289", "r5e_v288": "V288", "r39": "V288"}
# r39 flew V282; its Kd/taper/LIM cells are identical to V288's (Kd never edited on a flown build, LIM 16384
# from V280r2 on) -- asserted below by comparing the cells that enter demand().


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def kd_of(idx, Y):
    """The firmware LERP with its high-clamp branch (0x29EA0/0x29EB0): np.interp already clamps at both ends."""
    return np.interp(idx, KDX, Y)


def crossings(sig, level):
    """Number of times sig crosses `level` (either direction), counting a run of equal samples once."""
    s = np.sign(sig - level)
    s[s == 0] = 1.0            # a sample sitting exactly on the knot is not itself a crossing
    return int(np.sum(np.abs(np.diff(s)) > 0))


def pspec(x, fs):
    """Hann-windowed POWER SPECTRUM of the mean-removed x, normalised so sum(P[1:]) == var(x).
    Returns (f, P) with the DC bin already zeroed -- every band statistic below is AC-only."""
    x = np.asarray(x, float)
    x = x - x.mean()
    n = len(x)
    if n < 16 or not np.any(x):
        return np.zeros(1), np.zeros(1)
    w = np.hanning(n)
    X = np.abs(np.fft.rfft(x * w)) ** 2
    f = np.fft.rfftfreq(n, 1.0 / fs)
    X[0] = 0.0                                   # the window leaks the (already removed) mean into bin 0
    s = X.sum()
    if s <= 0:
        return f, X
    return f, X * (float(np.var(x)) / s)         # sum(P) == var(x) exactly


def band_frac(x, fs, f_lo, f_hi):
    """fraction of the AC variance of x in [f_lo, f_hi]."""
    f, P = pspec(x, fs)
    t = P.sum()
    if t <= 0:
        return 0.0
    return float(P[(f >= f_lo) & (f <= f_hi)].sum() / t)


def band_rms(x, fs, f_lo, f_hi):
    """rms of the component of x in [f_lo, f_hi], in the same units as x."""
    f, P = pspec(x, fs)
    return float(np.sqrt(max(P[(f >= f_lo) & (f <= f_hi)].sum(), 0.0)))


def main():
    pr("=" * 118)
    pr("ITEM 1 -- THE MODULATION, MEASURED FROM THE WIRE (agent paramod, 2026-09-09)")
    pr("=" * 118)
    pr()
    pr("Row S delivered Kd surface (LERP 0xE511C slot 7, X = 0/11/22/32, high-clamp above 32):")
    for name, Y in ROWS.items():
        s = "  %-26s Kd(0)=%3.0f  Kd(11)=%3.0f  Kd(22)=%3.0f  Kd(27)=%5.1f  Kd(32)=%3.0f  Kd(>=32)=%3.0f" % (
            name, kd_of(0, Y), kd_of(11, Y), kd_of(22, Y), kd_of(27, Y), kd_of(32, Y), kd_of(240, Y))
        pr(s)
    pr()
    pr("  ==> under row S knot 11 is a NO-OP (Y[0]==Y[1]==Y[2]).  The ONLY varying region is the RAMP 22 < idx < 32,")
    pr("      slope dKd/didx = +3.2 per idx count = +0.1984 Kd per wire count of 0xE4.  Kd is CONTINUOUS in idx")
    pr("      (piecewise linear), so there is no discontinuous switch anywhere -- the hazard, if any, is a")
    pr("      CONTINUOUS parametric modulation whose depth is set by how much of the ramp the demand traverses.")
    pr()

    # ---------------------------------------------------------------- cells / images
    C = {n: AX.cells(n) for n in ("V289", "V288")}
    for n, c in C.items():
        pr("  %-5s Kd X=%s Y=%s   LIM=%d  idxclamp +%d/-%d" % (
            n, c["kd"]["X"].astype(int).tolist(), c["kd"]["Y"].astype(int).tolist(),
            c["lim"]["Y"][0], c["clamp_pos"], c["clamp_neg"]))
    same = all(np.array_equal(C["V289"][k]["Y"], C["V288"][k]["Y"]) and
               np.array_equal(C["V289"][k]["X"], C["V288"][k]["X"])
               for k in ("kd", "lim", "taperS", "taperO"))
    pr("  demand()-relevant cells identical between V288 and V289 images: %s  (so r39/V282 uses the same axis)" % same)
    pr()

    # ---------------------------------------------------------------- episodes
    ep = {}
    if os.path.exists(CENSUS_PKL):
        P = pickle.load(open(CENSUS_PKL, "rb"))
        for e in P["episodes"]:
            ep.setdefault(e["tag"], []).append(e)
    pr("census grinding episodes available: %s" % {k: len(v) for k, v in sorted(ep.items())})
    pr()

    G = {}
    for tag in ROUTES:
        g = C20.load(tag)
        c = C[IMG_OF[tag]]
        g["dem"], g["dsgn"], g["Gg"] = AX.demand(np.round(g["cmd"]), g["bar"], c)
        G[tag] = g

    # ================================================================ 1A. knot crossings and duties
    pr("=" * 118)
    pr("1A.  KNOT CROSSINGS AND DUTY -- how often does the demand index visit / cross the row-S knots?")
    pr("=" * 118)
    pr()
    pr("  Regimes:  ENG = laterally engaged;  GRIND = census grinding episodes;  TURN7 = 2-5 m/s and |ang| 70-140 deg")
    pr("            (the operator's full-lock strong-turn regime, where the 7.5 Hz ring lives);  CRUISE = v>=22, |ang|<5.")
    pr()
    hdr = ("  %-11s %-8s %7s | %8s %8s %8s | %8s | %7s %7s %7s | %7s" %
           ("route", "regime", "sec", "x@11/s", "x@22/s", "x@32/s", "in-ramp", "<=22", "22-32", ">=32", "eps_Kd"))
    pr(hdr)
    pr("  " + "-" * (len(hdr) - 2))
    J["duty"] = {}
    for tag in ROUTES:
        g = G[tag]
        eng = g["eng"]
        dem = g["dem"]
        v = g["vego"]
        ang = np.abs(g["ang"])
        regimes = {"ENG": eng,
                   "TURN7": eng & (v >= 2) & (v <= 5) & (ang >= 70) & (ang <= 140),
                   "CRUISE": eng & (v >= 22) & (ang < 5)}
        if tag in ep:
            m = np.zeros(len(g["t"]), bool)
            for e in ep[tag]:
                m[int(e["a"]):int(e["b"])] = True
            regimes["GRIND"] = eng & m
        for lbl in ("ENG", "GRIND", "TURN7", "CRUISE"):
            if lbl not in regimes:
                continue
            m = regimes[lbl]
            sec = m.sum() * DT
            if sec < 0.5:
                pr("  %-11s %-8s %7.1f | (too little)" % (tag, lbl, sec))
                continue
            d = dem[m]
            kd = kd_of(d, ROWS["S  Y=[96,96,96,128]"])
            eps = (kd.max() - kd.min()) / (kd.max() + kd.min()) if kd.max() + kd.min() else 0.0
            # crossings counted on the CONTIGUOUS engaged stream restricted to the mask, per second of that mask
            row = (tag, lbl, sec,
                   crossings(d, 11.0) / sec, crossings(d, 22.0) / sec, crossings(d, 32.0) / sec,
                   float(np.mean((d > 22) & (d < 32))) * 100.0,
                   float(np.mean(d <= 22)) * 100.0, float(np.mean((d > 22) & (d < 32))) * 100.0,
                   float(np.mean(d >= 32)) * 100.0, eps)
            pr("  %-11s %-8s %7.1f | %8.2f %8.2f %8.2f | %7.2f%% | %6.1f%% %6.1f%% %6.1f%% | %7.3f" % row)
            J["duty"]["%s/%s" % (tag, lbl)] = dict(sec=sec, x11=row[3], x22=row[4], x32=row[5],
                                                   in_ramp_pct=row[6], le22=row[7], ramp=row[8], ge32=row[9], eps=eps)
    pr()
    pr("  x@K/s = knot crossings per second of that regime.  in-ramp = share of time strictly inside 22 < idx < 32,")
    pr("  the ONLY band where row S's Kd actually varies.  eps_Kd = (max-min)/(max+min) of the delivered Kd over the")
    pr("  regime -- V59's own modulation-depth statistic, for comparison with its measured 0.333 p95.")
    pr()

    # ================================================================ 1B. per-episode spectrum of Kd(t)
    pr("=" * 118)
    pr("1B.  THE SPECTRUM OF THE DELIVERED Kd(t), INSIDE EACH GRINDING EPISODE")
    pr("=" * 118)
    pr()
    pr("  For each census episode: its measured line frequency f0, then the fraction of the AC variance of the")
    pr("  ROW-S Kd(t) trace that falls in +-1.5 Hz of f0, of 2*f0 (the parametric-resonance band), of 7.3 Hz and")
    pr("  of 14.6 Hz.  eps = modulation depth of Kd over the episode; sdKd = std(Kd); ramp% = time in 22<idx<32.")
    pr("  NOTE the wire is 100 Hz: 2*f0 is 31-40 Hz, comfortably below the 50 Hz Nyquist, so the 2f band is REAL,")
    pr("  not an alias.")
    pr()
    hdr = ("  %-11s %5s %6s %6s %6s | %6s %6s %6s %6s | %7s %7s %7s" %
           ("route", "n", "dur_s", "f0", "2f0", "@f0", "@2f0", "@7.3", "@14.6", "eps", "sd(Kd)", "ramp%"))
    pr(hdr)
    pr("  " + "-" * (len(hdr) - 2))
    J["episodes"] = []
    agg = {}
    for tag in ROUTES:
        if tag not in ep:
            continue
        g = G[tag]
        dem = g["dem"]
        rows = []
        for e in ep[tag]:
            a, b = int(e["a"]), int(e["b"])
            if b - a < 32:
                continue
            d = dem[a:b]
            kd = kd_of(d, ROWS["S  Y=[96,96,96,128]"])
            f0 = float(e["f0"])
            r = dict(tag=tag, dur=(b - a) * DT, f0=f0,
                     at_f0=band_frac(kd, FS, f0 - 1.5, f0 + 1.5),
                     at_2f0=band_frac(kd, FS, 2 * f0 - 1.5, 2 * f0 + 1.5),
                     at_73=band_frac(kd, FS, 5.8, 8.8),
                     at_146=band_frac(kd, FS, 13.1, 16.1),
                     eps=float((kd.max() - kd.min()) / (kd.max() + kd.min())),
                     sd=float(kd.std()),
                     ramp=float(np.mean((d > 22) & (d < 32)) * 100.0))
            rows.append(r)
            J["episodes"].append(r)
        if not rows:
            continue
        agg[tag] = rows
        q = lambda k: np.percentile([r[k] for r in rows], [50])[0]  # noqa: E731
        pr("  %-11s %5d %6.2f %6.1f %6.1f | %6.3f %6.3f %6.3f %6.3f | %7.4f %7.3f %7.2f   <-- MEDIAN" % (
            tag, len(rows), q("dur"), q("f0"), 2 * q("f0"), q("at_f0"), q("at_2f0"), q("at_73"), q("at_146"),
            q("eps"), q("sd"), q("ramp")))
        mx = max(rows, key=lambda r: r["at_2f0"])
        pr("  %-11s %5s %6.2f %6.1f %6.1f | %6.3f %6.3f %6.3f %6.3f | %7.4f %7.3f %7.2f   <-- WORST @2f0" % (
            "", "", mx["dur"], mx["f0"], 2 * mx["f0"], mx["at_f0"], mx["at_2f0"], mx["at_73"], mx["at_146"],
            mx["eps"], mx["sd"], mx["ramp"]))
        n_any = sum(1 for r in rows if r["sd"] > 0)
        n_ramp = sum(1 for r in rows if r["ramp"] > 0)
        pr("  %-11s episodes with ANY Kd variation: %d/%d;  episodes that enter the ramp at all: %d/%d"
           % ("", n_any, len(rows), n_ramp, len(rows)))
    pr()

    # ================================================================ 1C. the WHOLE engaged Kd(t) spectrum
    pr("=" * 118)
    pr("1C.  THE WHOLE-ROUTE Kd(t) MODULATION SPECTRUM (engaged frames, contiguous runs >= 2 s)")
    pr("=" * 118)
    pr()
    pr("  %-11s %8s %9s %9s | %s" % ("route", "sec", "sd(Kd)", "rms/128", "share of Kd AC variance by band"))
    bands = [(0.0, 2.0), (2.0, 5.0), (5.0, 8.8), (8.8, 13.1), (13.1, 18.0), (18.0, 23.0), (23.0, 30.0),
             (30.0, 36.0), (36.0, 44.0), (44.0, 50.0)]
    pr("  %-11s %8s %9s %9s | %s" % ("", "", "", "", "  ".join("%.0f-%.0f" % b for b in bands)))
    J["spectra"] = {}
    for tag in ROUTES:
        g = G[tag]
        eng = g["eng"]
        dem = g["dem"]
        kd = kd_of(dem, ROWS["S  Y=[96,96,96,128]"])
        # contiguous engaged runs
        idxs = np.where(eng)[0]
        if len(idxs) == 0:
            continue
        splits = np.where(np.diff(idxs) > 1)[0]
        runs = np.split(idxs, splits + 1)
        runs = [r for r in runs if len(r) >= 200]
        acc = np.zeros(len(bands))
        tot_var = 0.0
        sec = 0.0
        nsamp = 0
        for r in runs:
            x = kd[r]
            sec += len(r) * DT
            f, P = pspec(x, FS)
            if P.sum() <= 0:
                nsamp += len(r)
                continue
            # weight each run by its sample count so the pooled shares are a duration-weighted mean
            tot_var += P.sum() * len(r)
            for i, (lo, hi) in enumerate(bands):
                acc[i] += P[(f >= lo) & (f < hi)].sum() * len(r)
            nsamp += len(r)
        sh = acc / tot_var if tot_var > 0 else acc
        sdv = float(np.sqrt(tot_var / max(nsamp, 1)))
        pr("  %-11s %8.1f %9.3f %9.5f | %s" % (tag, sec, sdv, sdv / 128.0,
                                               "  ".join("%5.3f" % v for v in sh)))
        J["spectra"][tag] = dict(sec=sec, sd=sdv, bands=[list(b) for b in bands], share=sh.tolist())
    pr()

    # ================================================================ 1D. how far is the modulation from V59's pump?
    pr("=" * 118)
    pr("1D.  SCALE CHECK AGAINST THE KIT'S ONE MEASURED PARAMETRIC PUMP (V59, memory")
    pr("     accord-parametric-pump-intervention-never-run: eps p50 0.333 into a 21.09 Hz mode at 42.19 Hz)")
    pr("=" * 118)
    pr()
    pr("  Computed PER EPISODE (never on a concatenation of disjoint windows) and pooled by episode duration.")
    pr("  eps_kf = (rms of the Kd component in +-2 Hz of k*f0) / (mean Kd over the episode) -- the depth of the")
    pr("  parametric drive at 1f and at 2f.  For a sinusoidal pump, V59's eps is the half-swing / mean, so a")
    pr("  sinusoid of rms r has eps_V59 = r*sqrt(2)/mean; the sqrt(2) column makes the comparison like-for-like.")
    pr()
    pr("  %-11s %5s %8s %9s %11s %11s | %11s %11s" %
       ("route", "n", "meanKd", "f0(Hz)", "eps_1f", "eps_2f", "eps_1f*rt2", "eps_2f*rt2"))
    for tag in ROUTES:
        if tag not in ep:
            continue
        g = G[tag]
        rows = []
        for e in ep[tag]:
            a, b = int(e["a"]), int(e["b"])
            if b - a < 32:
                continue
            d = g["dem"][a:b]
            kd = kd_of(d, ROWS["S  Y=[96,96,96,128]"])
            f0 = float(e["f0"])
            mk = float(kd.mean())
            rows.append((b - a, mk, f0,
                         band_rms(kd, FS, f0 - 2, f0 + 2) / mk,
                         band_rms(kd, FS, 2 * f0 - 2, 2 * f0 + 2) / mk))
        if not rows:
            continue
        w = np.array([r[0] for r in rows], float)
        mk = float(np.average([r[1] for r in rows], weights=w))
        f0 = float(np.average([r[2] for r in rows], weights=w))
        e1 = float(np.average([r[3] for r in rows], weights=w))
        e2 = float(np.average([r[4] for r in rows], weights=w))
        e1x = float(np.max([r[3] for r in rows]))
        e2x = float(np.max([r[4] for r in rows]))
        pr("  %-11s %5d %8.2f %9.1f %11.5f %11.5f | %11.5f %11.5f   <-- duration-weighted mean"
           % (tag, len(rows), mk, f0, e1, e2, e1 * np.sqrt(2), e2 * np.sqrt(2)))
        pr("  %-11s %5s %8s %9s %11.5f %11.5f | %11.5f %11.5f   <-- WORST single episode"
           % ("", "", "", "", e1x, e2x, e1x * np.sqrt(2), e2x * np.sqrt(2)))
        J.setdefault("v59", {})[tag] = dict(meanKd=mk, f0=f0, eps1f=e1, eps2f=e2, eps1f_max=e1x, eps2f_max=e2x)
    pr()
    pr("  V59's MEASURED pump, for scale: eps p50 0.333 (p95), at 42.19 Hz = 2 x a 21.09 Hz mode, prominence 11.10x.")
    pr()


    # ================================================================ 1E / ITEM 3: the mitigation variants
    pr("=" * 118)
    pr("ITEM 3.  THE MITIGATION VARIANTS, SCORED ON THE SAME MEASURED WIRE")
    pr("=" * 118)
    pr()
    pr("  Every variant below keeps Y[3] = 128 and therefore is BYTE-IDENTICAL TO V282 above idx 32, where the")
    pr("  Kd lookup takes its high-clamp branch (0x29EA0 sld.hu 0x6,ep,r10 / 0x29EB0 ld.hu 0x6,r8,r7).  So the")
    pr("  7 Hz strong-turn gate and the capped-step authority are x1.000 BY CONSTRUCTION on all of them.")
    pr()
    pr("  🛑 THE LERP GATE ON ANY X EDIT: the lookup divides by X[i] - X[i-1] (`divq`), so X must stay STRICTLY")
    pr("  increasing -- X = [0, 11, 11, 32] would divide by zero.  X bytes are also a different, riskier byte class")
    pr("  than Y bytes: they move the axis every consumer of this record shares.")
    pr()
    VAR = [
        ("V282 (no edit)",            [0, 11, 22, 32], [128, 128, 128, 128], 0,  "-",     "revert"),
        ("S   Y=[96,96,96,128]",      [0, 11, 22, 32], [96, 96, 96, 128],    6,  "Y only", "the candidate"),
        ("S'  Y=[112,112,112,128]",   [0, 11, 22, 32], [112, 112, 112, 128], 6,  "Y only", "shallower cut"),
        ("M1  Y=[96,96,112,128]",     [0, 11, 22, 32], [96, 96, 112, 128],   6,  "Y only", "ramp 11->32, SAME cost"),
        ("M2  Y=[96,104,116,128]",    [0, 11, 22, 32], [96, 104, 116, 128],  6,  "Y only", "ramp 0->32, SAME cost"),
        ("M3  X=[0,8,11,32] Y=[96,96,96,128]", [0, 8, 11, 32], [96, 96, 96, 128], 10, "X+Y", "ramp 11->32 via X"),
    ]
    pr("  %-38s %-8s %-8s %-11s %-9s %s" % ("variant", "bytes", "class", "ramp (idx)", "dKd/didx", "note"))
    for nm, X, Y, nb, cls, note in VAR:
        X = np.array(X, float); Y = np.array(Y, float)
        seg = [(X[i - 1], X[i], (Y[i] - Y[i - 1]) / (X[i] - X[i - 1])) for i in range(1, len(X)) if Y[i] != Y[i - 1]]
        if seg:
            rmp = "%.0f-%.0f" % (seg[0][0], seg[-1][1])
            slp = "%.2f" % max(abs(s3) for _, _, s3 in seg)
        else:
            rmp, slp = "none", "0.00"
        pr("  %-38s %-8s %-8s %-11s %-9s %s" % (nm, nb if nb else "0", cls, rmp, slp, note))
    pr()
    pr("  Now the SAME variants against the measured demand.  Kd_eff = duration-weighted mean delivered Kd (LOWER =")
    pr("  more of the damping benefit kept).  sd = std of Kd(t).  eps2f = the parametric drive depth at 2x the")
    pr("  route's ring, duration-weighted over census grinding episodes -- the number the hazard is actually about.")
    pr()
    hdr2 = "  %-38s | %s" % ("variant", "  ".join("%-22s" % t for t in ROUTES))
    pr(hdr2)
    pr("  %-38s | %s" % ("", "  ".join("%-22s" % "Kd_eff  sd   eps2f" for t in ROUTES)))
    J["item3"] = {}
    for nm, X, Y, nb, cls, note in VAR:
        X = np.array(X, float); Y = np.array(Y, float)
        cellsr = []
        for tag in ROUTES:
            g = G[tag]
            if tag in ep:
                rows = []
                for e in ep[tag]:
                    a, b = int(e["a"]), int(e["b"])
                    if b - a < 32:
                        continue
                    kk = np.interp(g["dem"][a:b], X, Y)
                    mk = float(kk.mean())
                    rows.append((b - a, mk, float(kk.std()),
                                 band_rms(kk, FS, 2 * e["f0"] - 2, 2 * e["f0"] + 2) / mk if mk else 0.0))
                w = np.array([r[0] for r in rows], float)
                ke = float(np.average([r[1] for r in rows], weights=w))
                sd = float(np.average([r[2] for r in rows], weights=w))
                e2 = float(np.average([r[3] for r in rows], weights=w)) * np.sqrt(2)
            else:
                ke = sd = e2 = float("nan")
            kd_eng = np.interp(g["dem"][g["eng"]], X, Y)
            cellsr.append("%6.1f %5.2f %6.4f" % (float(kd_eng.mean()), sd, e2))
            J["item3"]["%s/%s" % (nm, tag)] = dict(kd_eng=float(kd_eng.mean()), kd_grind=ke, sd=sd, eps2f=e2)
        pr("  %-38s | %s" % (nm, "  ".join("%-22s" % c for c in cellsr)))
    pr()
    pr("  Kd_eff here is over ALL ENGAGED time (the authority-neutral statistic); sd and eps2f are over the census")
    pr("  grinding episodes.  Compare eps2f against the instability threshold measured in item 2: eps ~= 1.035.")
    pr()
    pr("  (b) 'MOVE THE CUT WHOLLY BELOW THE BAND THE INDEX VISITS DURING RINGS' -- NOT AVAILABLE.  Item 1 measured")
    pr("  the grinding episodes' idx p50 at 8 (r62) / 46 (r63) / 37 (r5e) / 20 (r39) with 24-66 % of their time at")
    pr("  idx >= 32.  The rings live on BOTH sides of the ramp, so there is no placement that is simultaneously")
    pr("  below the ring band and above nothing.  This mitigation cannot be built as stated.")
    pr()

    p = os.path.join(HERE, "_scratch", "paramod_v290_modulation.txt")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    json.dump(J, open(p.replace(".txt", ".json"), "w"), indent=1, default=float)
    pr("written: %s" % p)


if __name__ == "__main__":
    main()
