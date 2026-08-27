"""(A) THE OPERATOR'S FLOOR CHALLENGE TO THE HARMONIC "KILLER", AND (B) THE HIGHWAY CO-PRIMARY.

=================================================================================================
(A) THE CHALLENGE, and it is a fair one
=================================================================================================
Operator, 2026-08-22: "a harmonic can scale differently than its fundamental if there is a filter
which attenuates the harmonic more than the fundamental."

MY POSITION, stated before testing:
  * A FIXED LINEAR FILTER between the harmonic's generation point and the measurement applies
    IDENTICALLY to the stock and 6x arms, so it CANCELS EXACTLY in a cross-arm RATIO.  My test
    was a ratio across arms, not an absolute magnitude.  A static roll-off -- the 54.8 Hz EMA,
    the 0x18F ZOH, |Z|'s un-modelled roll-off above ~13 Hz -- cannot by itself produce
    13.55x vs 1.93x.  [This is the defence I failed to state and the orchestrator is right that
    it is the strongest one.]
  * 🛑 A NOISE FLOOR IS NOT A FILTER AND DOES NOT CANCEL IN A RATIO.  If most of stock's
    40-50 Hz (0.2763 deg/s) is a build-independent broadband floor, the harmonic component is
    ~0 at stock and ~0.26 at 6x, and the true harmonic ratio is UNBOUNDED.  ⇒ the operator's
    objection lands here, and only here.  THIS FILE TESTS IT.
  * ⚠ A GAIN-DEPENDENT or SATURATING element does NOT cancel either.  Named in the output.

FLOOR ESTIMATOR: the MANUAL (LKAS-off) arm, SPEED-MATCHED.  Manual has no engaged loop, so
whatever sits at 40-50 Hz there is floor + road + tyre + sensor.  Subtract in POWER, not
amplitude.  🛑 LIMIT, measured not assumed: manual exposure is ~100 % below 40 km/h on r97,
r96, ra4, r85, r95 (only r9e has 25 s above 80).  ⇒ THE FLOOR CORRECTION IS ONLY AVAILABLE AT
0-40 km/h.  Everything in (A) is therefore a LOW-SPEED test.

=================================================================================================
(B) HIGHWAY CO-PRIMARY -- declared by the orchestrator BEFORE any outcome was seen
=================================================================================================
6-9 Hz `rate_f`, ENGAGED, >= 80 km/h, a4 vs r97 (STOCK), speed-matched.
🛑 POWER WARNING STATED UP FRONT: route a4 has 138.6 s above 80 km/h in only **2 contiguous
runs**, so a true EPISODE bootstrap is impossible.  A 20 s BLOCK bootstrap is reported instead
and labelled as such -- blocks inside one continuous run are NOT independent, so its interval is
optimistic.  The point estimate is the quotable part; the interval is indicative.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
WIN = np.hanning(NPER + 1)[:NPER]
U = (WIN ** 2).sum()
DF = f[1] - f[0]
FUND = (20, 25)
HARM = (40, 50)


def specs(tag, engaged, vlo, vhi, block_s=None):
    """Per-run summed auto-spectra of rate_f.  block_s splits long runs into fixed blocks."""
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    m = (e if engaged else ~e) & (v >= vlo) & (v < vhi)
    rate = d['rate_f'].astype(float)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    tt = np.arange(NPER)
    M = np.vstack([tt, np.ones(NPER)]).T
    out = []
    for i in range(len(b) - 1):
        a0, b0 = b[i], b[i + 1]
        if (b0 - a0) < NPER or not m[a0]:
            continue
        cuts = ([(a0, b0)] if block_s is None else
                [(s, min(s + int(block_s * L.FS), b0))
                 for s in range(a0, b0, int(block_s * L.FS))])
        for c0, c1 in cuts:
            if (c1 - c0) < NPER:
                continue
            S, nw = None, 0
            for s in range(c0, c1 - NPER + 1, NPER // 2):
                if not m[s:s + NPER].all():
                    continue
                xs = rate[s:s + NPER]
                if not np.all(np.isfinite(xs)):
                    continue
                xs = xs - M @ np.linalg.lstsq(M, xs, rcond=None)[0]
                X = np.fft.rfft(xs * WIN)
                p = (X.conj() * X).real / (L.FS * U)
                S = p if S is None else S + p
                nw += 1
            if nw:
                out.append((S, nw))
    return out


def power(sp, lo, hi):
    """Band POWER (deg^2/s^2), the quantity that subtracts linearly."""
    if not sp:
        return np.nan
    sel = (f >= lo) & (f < hi)
    return float(sum(s[0] for s in sp)[sel].sum() / sum(s[1] for s in sp) * DF)


# =================================================================== (A)
print("=" * 112)
print("(A) THE FLOOR-CORRECTED HARMONIC SCALING -- 0-40 km/h, the only speed-matched arm")
print("=" * 112)
print("  Manual exposure above 40 km/h: r97 1.7 s · r96 0.0 s · ra4 0.0 s · r85/r95 0.0 s.")
print("  ⇒ a speed-matched floor exists ONLY at 0-40 km/h.  [EVIDENCE, measured from the caches]")
print()
ROWS = [('r97  STOCK 1x', 'r97'), ('r85  V100 4x', 'r85'), ('r96  V102 6x', 'r96'),
        ('r9e  V103 6x', 'r9e'), ('ra4  V104 6x', 'ra4'), ('r95  V101 8x  (CONFOUNDED)', 'r95')]
print("%28s %7s %7s %11s %11s %11s %11s %11s" %
      ('build', 'eng s', 'man s', 'F eng', 'H eng', 'H manual', 'H corrected', 'H/F corr'))
DAT = {}
for nm, tag in ROWS:
    e = specs(tag, True, 0, 40)
    m = specs(tag, False, 0, 40)
    if not e or not m:
        print("%28s  (insufficient exposure)" % nm)
        continue
    Fe = power(e, *FUND)
    He = power(e, *HARM)
    Hm = power(m, *HARM)
    Fm = power(m, *FUND)
    Hc = max(He - Hm, 0.0)
    Fc = max(Fe - Fm, 0.0)
    DAT[tag] = dict(Fe=Fe, He=He, Hm=Hm, Fm=Fm, Hc=Hc, Fc=Fc)
    d = L.load(tag)
    ee = d['cc_lat'] > 0.5
    vv = d['v_rear'].astype(float) * KPH
    print("%28s %7.1f %7.1f %11.4f %11.4f %11.4f %11.4f %11.4f"
          % (nm, (ee & (vv < 40)).sum() / L.FS, ((~ee) & (vv < 40)).sum() / L.FS,
             np.sqrt(Fe), np.sqrt(He), np.sqrt(Hm), np.sqrt(Hc),
             np.sqrt(Hc) / np.sqrt(Fc) if Fc > 0 else np.nan))
print("  (amplitudes shown; the SUBTRACTION is done in power.  H corrected = sqrt(He - Hm).)")

print()
print("  THE TEST -- does the refutation survive the floor correction?")
print("%36s %14s %14s %14s %14s" %
      ('contrast', 'F raw', 'H raw', 'F corrected', 'H corrected'))
base = DAT.get('r97')
for nm, tag in ROWS[1:]:
    if tag not in DAT or base is None:
        continue
    D = DAT[tag]
    print("%36s %14.2f %14.2f %14.2f %14.2f"
          % (nm + " / STOCK",
             np.sqrt(D['Fe'] / base['Fe']), np.sqrt(D['He'] / base['He']),
             np.sqrt(D['Fc'] / base['Fc']) if base['Fc'] > 0 else np.nan,
             np.sqrt(D['Hc'] / base['Hc']) if base['Hc'] > 0 else np.nan))
print()
print("  🛑 THE VERDICT RULE, stated before the numbers were read: a SECOND HARMONIC must grow")
print("     AT LEAST as fast as its fundamental.  If H_corrected/STOCK >= F_corrected/STOCK the")
print("     amplitude-scaling leg is DEAD and I owe a retraction.  If it stays far below, the")
print("     leg survives the operator's objection.")

print()
print("  SENSITIVITY -- how much floor would it take to overturn the leg?")
if base and 'r96' in DAT:
    F6, H6 = DAT['r96']['Fe'], DAT['r96']['He']
    Fs, Hs = base['Fe'], base['He']
    fr = np.linspace(0.0, 0.999, 1000)
    surv = []
    for x in fr:
        hs, h6 = Hs * (1 - x), max(H6 - Hs * x, 1e-12)
        surv.append(np.sqrt(h6 / hs) if hs > 0 else np.inf)
    fsc = np.sqrt(F6 / Fs)
    hit = np.flatnonzero(np.array(surv) >= fsc)
    print("     fundamental ratio to beat = %.2f" % fsc)
    print("     harmonic ratio at floor fraction 0.00 / 0.50 / 0.90 / 0.99 = %.2f / %.2f / %.2f / %.2f"
          % (surv[0], surv[500], surv[900], surv[990]))
    if len(hit):
        print("     ⇒ the leg only overturns if the floor is >= %.1f %% of STOCK's 40-50 Hz power."
              % (100 * fr[hit[0]]))
    print("     MEASURED floor fraction (manual/engaged power at 40-50 Hz, STOCK) = %.3f"
          % (base['Hm'] / base['He']))

# =================================================================== (B)
print()
print("=" * 112)
print("(B) HIGHWAY CO-PRIMARY -- 6-9 Hz, ENGAGED, >= 80 km/h.  Declared before any outcome.")
print("=" * 112)
for tag in ('ra4', 'r9e', 'r96', 'r97'):
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    runs = specs(tag, True, 80, 130)
    blk = specs(tag, True, 80, 130, block_s=20)
    print("  %s: %.1f s engaged >=80 km/h  |  %d contiguous runs  |  %d x 20 s blocks"
          % (tag, (e & (v >= 80)).sum() / L.FS, len(runs), len(blk)))
print("  🛑 route a4 has TWO contiguous runs => an EPISODE bootstrap is impossible. The 20 s")
print("     BLOCK bootstrap below is labelled and its interval is OPTIMISTIC (blocks inside one")
print("     run are not independent).  The point estimates are the quotable part.")
print()
BB = [(2, 4), (4, 6), (6, 9), (9, 13), (13, 18), (18, 22), (21, 28), (32, 45)]
S = {t: specs(t, True, 80, 130, block_s=20) for t in ('ra4', 'r9e', 'r96', 'r97')}
print("%12s" % 'band' + "".join("%11s" % t for t in ('r97', 'r96', 'r9e', 'ra4'))
      + "%24s %24s" % ('a4/STOCK [block CI]', 'a4/V103 [block CI]'))
rng = np.random.default_rng(31)


def bratio(A_, B_, lo, hi, nb=4000):
    if len(A_) < 3 or len(B_) < 3:
        return None
    pt = np.sqrt(power(B_, lo, hi) / power(A_, lo, hi))
    dr = np.array([np.sqrt(power([B_[j] for j in rng.integers(0, len(B_), len(B_))], lo, hi)
                           / power([A_[j] for j in rng.integers(0, len(A_), len(A_))], lo, hi))
                   for _ in range(nb)])
    return pt, np.percentile(dr, 2.5), np.percentile(dr, 97.5)


for lo, hi in BB:
    vals = [np.sqrt(power(S[t], lo, hi)) for t in ('r97', 'r96', 'r9e', 'ra4')]
    r1 = bratio(S['r97'], S['ra4'], lo, hi)
    r2 = bratio(S['r9e'], S['ra4'], lo, hi)
    s1 = "%.2f [%.2f,%.2f]" % r1 if r1 else "-"
    s2 = "%.2f [%.2f,%.2f]" % r2 if r2 else "-"
    star = "  <- CO-PRIMARY" if (lo, hi) == (6, 9) else ""
    print("%7.0f-%-4.0f" % (lo, hi) + "".join("%11.4f" % v for v in vals)
          + "%24s %24s%s" % (s1, s2, star))
print()
print("  SPLIT-HALF FLOOR on a4's own 20 s highway blocks (interleaved):")
sp = S['ra4']
print("%12s" % 'band' + "".join("%11s" % ("%g-%g" % b) for b in BB))
print("%12s" % 'a4 A/B' + "".join(
    "%11.2f" % np.sqrt(power(sp[0::2], a_, b_) / power(sp[1::2], a_, b_)) for a_, b_ in BB))


# =================================================================== (B2) speed-matched highway
print()
print("=" * 112)
print("(B2) 🛑 THE >=80 km/h ARM IS SPEED-MISMATCHED.  Re-run on the MATCHED 80-95 km/h window.")
print("=" * 112)
print("  Inside '>=80 km/h': r9e tops out at 92.0 km/h (p50 90.1, ZERO seconds above 95) while")
print("  a4 runs to 113.4 (p50 96.6, 83.3 s above 95).  Road and tyre noise scale with speed, so")
print("  the >=80 comparison above is confounded.  80-95 km/h is the overlap:")
print("     r97 73.7 s · r96 32.2 s · r9e 54.5 s · ra4 55.3 s   [EVIDENCE, from the caches]")
print()
S2 = {t: specs(t, True, 80, 95, block_s=20) for t in ('ra4', 'r9e', 'r96', 'r97')}
for t in ('r97', 'r96', 'r9e', 'ra4'):
    print("  %s: %d contiguous runs, %d x 20 s blocks" %
          (t, len(specs(t, True, 80, 95)), len(S2[t])))
print()
print("%12s" % 'band' + "".join("%11s" % t for t in ('r97', 'r96', 'r9e', 'ra4'))
      + "%24s %24s %12s" % ('a4/STOCK [block CI]', 'a4/V103 [block CI]', 'a4/V103 ÷plac'))
rowsv = {}
for lo, hi in BB:
    vals = [np.sqrt(power(S2[t], lo, hi)) for t in ('r97', 'r96', 'r9e', 'ra4')]
    r1 = bratio(S2['r97'], S2['ra4'], lo, hi)
    r2 = bratio(S2['r9e'], S2['ra4'], lo, hi)
    rowsv[(lo, hi)] = (r1, r2)
    s1 = "%.2f [%.2f,%.2f]" % r1 if r1 else "-"
    s2 = "%.2f [%.2f,%.2f]" % r2 if r2 else "-"
    print("%7.0f-%-4.0f" % (lo, hi) + "".join("%11.4f" % v for v in vals)
          + "%24s %24s" % (s1, s2), end="")
    plac = rowsv.get((32, 45), (None, None))[1]
    if r2 and plac:
        print("%12.2f" % (r2[0] / plac[0]), end="")
    print("  <- CO-PRIMARY" if (lo, hi) == (6, 9) else "")
print()
print("  ⚠ the LAST column divides by the 32-45 Hz placebo, which is only meaningful once the")
print("    placebo row itself has been printed -- read it bottom-up.  A uniform ratio across")
print("    EVERY band including the placebo is a DRIVE offset, not a lever.")
print()
print("  SPLIT-HALF FLOOR, a4's own 80-95 km/h 20 s blocks (interleaved):")
print("%12s" % 'band' + "".join("%11s" % ("%g-%g" % b) for b in BB))
sp2 = S2['ra4']
if len(sp2) >= 4:
    print("%12s" % 'a4 A/B' + "".join(
        "%11.2f" % np.sqrt(power(sp2[0::2], a_, b_) / power(sp2[1::2], a_, b_)) for a_, b_ in BB))
