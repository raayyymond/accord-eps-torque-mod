r"""NEW-Q1 -- DOES PITCH TRACK AMPLITUDE *WITHIN* ROUTE a6?

=================================================================================================
🛑 FIRST, A DISTINCTION THAT DECIDES WHAT IS BEING TESTED
=================================================================================================
`memory/accord-f0-crossover-is-the-endpoint` states the -1.93 Hz-per-e-fold law about **`f0`, the
`Re(Z)` ZERO CROSSING, versus COMMAND amplitude (median |0x0E4|)**.  It is NOT a law about the
spectral PEAK versus MODE amplitude -- and `accord-v105-relocated-the-mode-not-damped` says so in
as many words: *"`f0` = 24.90 Hz is a `Re(Z)` zero-crossing, which was never the spectral peak."*
⇒ Two different regressions, and this file runs BOTH rather than conflating them:
      (I)  peak frequency  vs  log(MODE amplitude, 18-30 Hz band RMS)   <- what was asked for
      (II) peak frequency  vs  log(COMMAND amplitude, |e4tq|)           <- the law's own variable

=================================================================================================
🛑🛑 THE ESTIMATOR ARTEFACT THAT WOULD MANUFACTURE THIS RESULT, AND THE CONTROL FOR IT
=================================================================================================
A per-window argmax inside a fixed search band is **biased toward the band centre when there is
no line**: a low-amplitude window is noise, so its argmax scatters uniformly and averages to the
band centre; a high-amplitude window locks onto the true mode.  **If the true mode sits below the
band centre, that alone produces a negative slope, and if above, a positive one -- with no physics
whatsoever.**  Route a6's low-speed windows are largely lineless (prominence 1.5 vs stock's 1.46),
so this is not a hypothetical.

CONTROLS, ALL RUN BEFORE THE MEASUREMENT:
  C1  **SYNTHETIC CALIBRATION.**  A STATIONARY 22.0 Hz mode injected at a ladder of amplitudes into
      route a6's own MANUAL-driving noise, pushed through the identical binning + argmax pipeline.
      The true slope is EXACTLY ZERO by construction.  **Whatever slope comes back is the
      artefact floor, and no measured slope smaller than it may be reported as real.**
  C2  **BAND-CENTRE SWEEP.**  If the slope tracks (band centre - mode frequency), it is C1's
      artefact and not physics.
  C3  **PROMINENCE GATING.**  Repeat using only windows that actually contain a line (prom >= 3).
  C4  **SPEED STRATIFICATION.**  f0 rises with speed, and amplitude falls with speed, so a pooled
      fit is a Simpson's-paradox trap -- the exact error that withdrew "f0 shifted 8.18 -> 7.71 Hz"
      in `feedback-episodes-not-windows`.

Bootstrap is over contiguous **30 s BLOCKS** (route a6 has only 7 engaged episodes), disclosed.

Usage:  python studies/ra6/ra6_pitch_amp.py
"""
import os
import sys
import json

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "analysis-2020accord"))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
FS = L.FS
NPER = int(round(4 * FS))
FB = np.fft.rfftfreq(NPER, 1 / FS)
WIN = np.hanning(NPER + 1)[:NPER]
UU = (WIN ** 2).sum()
DF = FB[1] - FB[0]
BAND = (18.0, 30.0)
TAGS = ('ra4', 'ra5', 'ra6')
NAMES = {'ra4': 'V104 6x', 'ra5': 'V105 NOTCH', 'ra6': 'V106 6b26x3'}
OUT = {}


def windows(tag, engaged=True):
    d = L.load(tag)
    e = np.asarray(d['cc_lat'], float) > 0.5
    if not engaged:
        e = ~e
    v = np.asarray(d['v_rear'], float) * KPH
    x = np.asarray(d['rate_f'], float)
    dem = np.abs(np.asarray(d['e4tq'], float))
    idx = np.flatnonzero(np.diff(e.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(e)]))
    P, V, D, B, RAW = [], [], [], [], []
    for a, c in zip(b[:-1], b[1:]):
        if not (e[a] and (c - a) >= NPER):
            continue
        for s in range(a, c - NPER + 1, NPER // 2):
            xs = x[s:s + NPER] - x[s:s + NPER].mean()
            X = np.fft.rfft(xs * WIN)
            P.append((X.conj() * X).real / (FS * UU))
            V.append(float(np.mean(v[s:s + NPER])))
            D.append(float(np.median(dem[s:s + NPER])))
            B.append(int(s // int(30 * FS)))
            RAW.append(xs)
    return (np.array(P), np.array(V), np.array(D), np.array(B), np.array(RAW))


W = {t: windows(t) for t in TAGS}


def pk(S, lo=BAND[0], hi=BAND[1]):
    k = (FB >= lo) & (FB <= hi)
    return float(FB[k][int(np.argmax(S[k]))])


def rms(S, lo=BAND[0], hi=BAND[1]):
    k = (FB >= lo) & (FB < hi)
    return float(np.sqrt(S[k].sum() * DF))


def binned_slope(P, amp, nbin=6, lo=BAND[0], hi=BAND[1], minn=10):
    """Bin windows by log(amp) into nbin equal-count bins, take the POOLED spectrum's argmax in
    each bin (far more stable than a per-window argmax), and regress peak Hz on log(median amp).
    Returns (slope Hz per e-fold, list of (median amp, peak Hz, n))."""
    ok = np.isfinite(amp) & (amp > 0)
    if ok.sum() < nbin * minn:
        return np.nan, []
    q = np.quantile(amp[ok], np.linspace(0, 1, nbin + 1))
    pts = []
    for j in range(nbin):
        m = ok & (amp >= q[j]) & (amp <= q[j + 1] if j == nbin - 1 else amp < q[j + 1])
        if m.sum() < minn:
            continue
        pts.append((float(np.median(amp[m])), pk(P[m].mean(0), lo, hi), int(m.sum())))
    if len(pts) < 4:
        return np.nan, pts
    xs = np.log([p[0] for p in pts])
    ys = np.array([p[1] for p in pts])
    return float(np.polyfit(xs, ys, 1)[0]), pts


# =============================================================== C1  SYNTHETIC CALIBRATION
print("=" * 124)
print("C1.  🛑 THE ESTIMATOR CONTROL, RUN FIRST.  A **STATIONARY 22.0 Hz** mode injected at a")
print("     ladder of amplitudes into route a6's own MANUAL-driving noise, through the IDENTICAL")
print("     binning + argmax pipeline.  TRUE SLOPE = 0 BY CONSTRUCTION.")
print("=" * 124)
Pm, Vm, Dm, Bm, RAWm = windows('ra6', engaged=False)
print("  noise pool: %d manual windows from route a6" % len(RAWm))
rg = np.random.default_rng(4242)
tt = np.arange(NPER) / FS
for f_inj in (22.0, 20.0, 26.0):
    Ps, As = [], []
    for i in range(len(RAWm)):
        a = float(np.exp(rg.uniform(np.log(0.02), np.log(6.0))))
        sig = RAWm[i] + a * np.sin(2 * np.pi * f_inj * tt + rg.uniform(0, 2 * np.pi))
        X = np.fft.rfft((sig - sig.mean()) * WIN)
        S = (X.conj() * X).real / (FS * UU)
        Ps.append(S)
        As.append(a)
    Ps, As = np.array(Ps), np.array(As)
    sl, pts = binned_slope(Ps, np.array([rms(S) for S in Ps]))
    sl2, _ = binned_slope(Ps, As)
    print("  injected %4.1f Hz (stationary)  ->  slope vs log(BAND RMS) %+7.3f Hz/e-fold   "
          "vs log(TRUE amp) %+7.3f" % (f_inj, sl, sl2))
    print("       recovered peaks by amplitude bin: "
          + "  ".join("%.2f(n=%d)" % (p[1], p[2]) for p in pts))
    OUT.setdefault('C1_synthetic', {})["%.1f Hz" % f_inj] = dict(
        slope_vs_bandrms=float(sl), slope_vs_trueamp=float(sl2),
        pts=[[float(a), float(b), int(c)] for a, b, c in pts])
print("  🛑 ARTEFACT FLOOR = the largest |slope| above.  A measured slope inside it is NOT a")
print("     result.  Note the SIGN tracks (band centre 24 Hz - injected f), exactly as predicted.")

# =============================================================== 1  the measurement
print()
print("=" * 124)
print("1.  (I) PEAK FREQUENCY vs log(MODE AMPLITUDE) -- WITHIN each drive, SPEED-STRATIFIED.")
print("=" * 124)
VB = [('<16 km/h', 0, 16), ('16-40 km/h', 16, 40), ('40-95 km/h', 40, 95), ('>=70 km/h', 70, 1e9)]
print("%14s %14s %8s %26s   %s"
      % ('build', 'speed', 'n win', 'slope Hz/e-fold [95 % CI]', 'peak by amplitude sextile'))
for t in TAGS:
    P, V, D, B, RAW = W[t]
    for lbl, lo, hi in VB:
        m = (V >= lo) & (V < hi)
        if m.sum() < 60:
            continue
        Pm_, Bm_ = P[m], B[m]
        amp = np.array([rms(S) for S in Pm_])
        sl, pts = binned_slope(Pm_, amp)
        ub = np.unique(Bm_)
        rg2 = np.random.default_rng(99)
        bs = []
        for _ in range(600):
            sel = np.concatenate([np.flatnonzero(Bm_ == j) for j in rg2.choice(ub, len(ub))])
            s2, _ = binned_slope(Pm_[sel], amp[sel])
            if np.isfinite(s2):
                bs.append(s2)
        q = np.percentile(bs, [2.5, 97.5]) if len(bs) > 50 else [np.nan] * 2
        print("%14s %14s %8d %26s   %s"
              % (NAMES[t], lbl, int(m.sum()),
                 "%+.3f [%+.3f, %+.3f]" % (sl, q[0], q[1]),
                 " ".join("%.1f" % p[1] for p in pts)))
        OUT.setdefault('I_mode_amplitude', {}).setdefault(NAMES[t], {})[lbl] = dict(
            nwin=int(m.sum()), slope=float(sl), ci=[float(q[0]), float(q[1])],
            pts=[[float(a), float(b), int(c)] for a, b, c in pts])

print()
print("=" * 124)
print("2.  (II) PEAK FREQUENCY vs log(COMMAND AMPLITUDE |e4tq|) -- the -1.93 Hz/e-fold law's OWN")
print("    independent variable.  🛑 MANDATORY per `accord-f0-crossover-is-the-endpoint`: the")
print("    median |0x0E4| is reported beside every row.")
print("=" * 124)
print("%14s %14s %8s %10s %26s   %s"
      % ('build', 'speed', 'n win', 'med |0E4|', 'slope Hz/e-fold [95 % CI]', 'peak by sextile'))
for t in TAGS:
    P, V, D, B, RAW = W[t]
    for lbl, lo, hi in VB:
        m = (V >= lo) & (V < hi)
        if m.sum() < 60:
            continue
        Pm_, Bm_, Dm_ = P[m], B[m], D[m]
        sl, pts = binned_slope(Pm_, Dm_)
        ub = np.unique(Bm_)
        rg2 = np.random.default_rng(98)
        bs = []
        for _ in range(600):
            sel = np.concatenate([np.flatnonzero(Bm_ == j) for j in rg2.choice(ub, len(ub))])
            s2, _ = binned_slope(Pm_[sel], Dm_[sel])
            if np.isfinite(s2):
                bs.append(s2)
        q = np.percentile(bs, [2.5, 97.5]) if len(bs) > 50 else [np.nan] * 2
        print("%14s %14s %8d %10.0f %26s   %s"
              % (NAMES[t], lbl, int(m.sum()), np.median(Dm_),
                 "%+.3f [%+.3f, %+.3f]" % (sl, q[0], q[1]),
                 " ".join("%.1f" % p[1] for p in pts)))
        OUT.setdefault('II_command_amplitude', {}).setdefault(NAMES[t], {})[lbl] = dict(
            nwin=int(m.sum()), med_e4tq=float(np.median(Dm_)), slope=float(sl),
            ci=[float(q[0]), float(q[1])],
            pts=[[float(a), float(b), int(c)] for a, b, c in pts])

# =============================================================== C2  band sweep
print()
print("=" * 124)
print("C2.  BAND-CENTRE SWEEP on the real data.  If the slope tracks the band centre, it is C1.")
print("=" * 124)
SB = [(18, 30), (16, 28), (20, 32), (15, 35), (19, 26)]
print("%14s %14s" % ('build', 'speed') + "".join("%14s" % ("%g-%g" % b) for b in SB))
for t in TAGS:
    P, V, D, B, RAW = W[t]
    for lbl, lo, hi in (('<16 km/h', 0, 16), ('40-95 km/h', 40, 95)):
        m = (V >= lo) & (V < hi)
        if m.sum() < 60:
            continue
        row = []
        for blo, bhi in SB:
            amp = np.array([rms(S, blo, bhi) for S in P[m]])
            s2, _ = binned_slope(P[m], amp, lo=blo, hi=bhi)
            row.append(s2)
        print("%14s %14s" % (NAMES[t], lbl) + "".join("%14.3f" % x for x in row))
        OUT.setdefault('C2_bandsweep', {}).setdefault(NAMES[t], {})[lbl] = [float(x) for x in row]

# =============================================================== C3  prominence gate
print()
print("=" * 124)
print("C3.  PROMINENCE-GATED -- only windows that actually contain a line (prom >= 3 against a")
print("     +-3 Hz median background).  Removes the lineless windows whose argmax is noise.")
print("=" * 124)


def wprom(S):
    k = (FB >= 15) & (FB <= 35)
    j = int(np.argmax(S[k]))
    f0 = FB[k][j]
    bg = np.median(S[(FB >= f0 - 3) & (FB <= f0 + 3)])
    return (S[k][j] / bg) if bg > 0 else 0.0


print("%14s %14s %10s %10s %26s"
      % ('build', 'speed', 'n win', 'n gated', 'slope Hz/e-fold [95 % CI]'))
for t in TAGS:
    P, V, D, B, RAW = W[t]
    pr = np.array([wprom(S) for S in P])
    for lbl, lo, hi in (('<16 km/h', 0, 16), ('40-95 km/h', 40, 95)):
        m = (V >= lo) & (V < hi) & (pr >= 3.0)
        n0 = ((V >= lo) & (V < hi)).sum()
        if m.sum() < 40:
            print("%14s %14s %10d %10d   -- too few gated windows --"
                  % (NAMES[t], lbl, n0, m.sum()))
            continue
        amp = np.array([rms(S) for S in P[m]])
        sl, pts = binned_slope(P[m], amp, nbin=5)
        ub = np.unique(B[m])
        rg2 = np.random.default_rng(97)
        bs = []
        for _ in range(600):
            sel = np.concatenate([np.flatnonzero(B[m] == j) for j in rg2.choice(ub, len(ub))])
            s2, _ = binned_slope(P[m][sel], amp[sel], nbin=5)
            if np.isfinite(s2):
                bs.append(s2)
        q = np.percentile(bs, [2.5, 97.5]) if len(bs) > 50 else [np.nan] * 2
        print("%14s %14s %10d %10d %26s"
              % (NAMES[t], lbl, n0, int(m.sum()), "%+.3f [%+.3f, %+.3f]" % (sl, q[0], q[1])))
        OUT.setdefault('C3_prom_gated', {}).setdefault(NAMES[t], {})[lbl] = dict(
            nwin=int(n0), ngated=int(m.sum()), slope=float(sl), ci=[float(q[0]), float(q[1])])

# =============================================================== 3  the cross-drive check
print()
print("=" * 124)
print("3.  ⭐ THE CHECK THE MEMORY MAKES MANDATORY: does the a6-vs-a5 shift sit ON the amplitude")
print("    law's own slope?  If it does, it is NOT evidence a lever touched the loop.")
print("=" * 124)
for t in TAGS:
    P, V, D, B, RAW = W[t]
    print("  %-14s engaged median |0x0E4| = %6.0f   (all engaged windows)"
          % (NAMES[t], np.median(D)))
d5 = np.median(W['ra5'][2])
d6 = np.median(W['ra6'][2])
print("  a6 / a5 command ratio %.3f  =>  %.3f e-folds LOWER command on a6" % (d6 / d5,
                                                                              np.log(d5 / d6)))
for nm, slope in (("the memory's f0 law (-1.93 Hz/e-fold)", -1.93),
                  ("the memory's within-V102 f0 law (-0.99)", -0.99)):
    print("     under %-42s a6 should read %+0.2f Hz vs a5 from COMMAND ALONE"
          % (nm, -slope * np.log(d5 / d6)))
OUT['command_medians'] = {NAMES[t]: float(np.median(W[t][2])) for t in TAGS}
OUT['a6_a5_command_efolds'] = float(np.log(d5 / d6))

json.dump(OUT, open(os.path.join(ROOT, 'analysis-2020accord', '_scratch/out/_ra6_pitch_amp.json'), 'w'),
          indent=1, default=float)
print("\nwrote analysis-2020accord/_scratch/out/_ra6_pitch_amp.json")
