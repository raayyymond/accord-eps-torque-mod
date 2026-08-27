"""IS THE MEASURED V103/V102 DIFFERENCE RESOLVABLE AT ALL?  The control before the claim.

studies/sessions/v104/v104_perceptual_null.py sec 4 measures V103/V102 = 1.916x at 6-9 Hz (band RMS of rate_f,
matched 18-90 km/h window).  The operator says he could not tell the two apart.
Before either is believed, the between-drive floor has to be measured:

  C1  EPISODE BOOTSTRAP of the ratio -- does its CI exclude 1.0?
  C2  SPLIT-HALF NULL inside each route -- interleaved episodes, same statistic.  If half-A/half-B
      inside ONE route spans 1.9x, the between-route 1.9x is exposure, not build.
  C3  A PLACEBO BAND the c4 arming provably cannot reach (26-40 Hz: |H| there is inside the
      biquad's own stopband and the lever's predicted |A| ratio is ~1.00).  If the placebo band
      moves as much as 6-9 Hz, the whole comparison is drive-to-drive.
  C4  THE SAME CONTRAST ON THE STOCK ROUTE r97 vs V102 r96 -- two builds that differ by the
      6x gain itself, i.e. a contrast the operator DID score.  Scale reference.

🛑 feedback-run-the-control-before-the-measurement / feedback-episodes-not-windows.
🛑 x6b94 not read anywhere in this file.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
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

NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
KPH = 3.6
FB = [(2, 4), (4, 6), (6, 9), (9, 13), (18, 22), (22, 26), (26, 40)]


def ep_specs(tag):
    """Per-episode summed auto-spectra of rate_f over the matched 18-90 km/h engaged window."""
    d = L.load(tag)
    eng = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    ra = np.abs(d['rate_f'].astype(float))
    keep = (v >= 18.0) & (v <= 90.0) & (ra <= 60.0)
    rate = d['rate_f'].astype(float)
    idx = np.flatnonzero(np.diff(eng.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(eng)]))
    w = np.hanning(NPER + 1)[:NPER]
    U = (w ** 2).sum()
    tt = np.arange(NPER)
    A = np.vstack([tt, np.ones(NPER)]).T
    out = []
    for i in range(len(b) - 1):
        a0, b0 = b[i], b[i + 1]
        if not eng[a0] or (b0 - a0) < NPER:
            continue
        S = None
        nw = 0
        for s in range(a0, b0 - NPER + 1, NPER // 2):
            if not keep[s:s + NPER].all():
                continue
            xs = rate[s:s + NPER]
            if not np.all(np.isfinite(xs)):
                continue
            xs = xs - A @ np.linalg.lstsq(A, xs, rcond=None)[0]
            X = np.fft.rfft(xs * w)
            sxx = (X.conj() * X).real / (L.FS * U)
            S = sxx if S is None else S + sxx
            nw += 1
        if nw:
            out.append((S, nw))
    return out


def rms(sp, lo, hi):
    if not sp:
        return np.nan
    sel = (f >= lo) & (f < hi)
    return float(np.sqrt(sum(s[0] for s in sp)[sel].sum() / sum(s[1] for s in sp)
                         * (f[1] - f[0])))


SP = {t: ep_specs(t) for t in ('r96', 'r97', 'r9e')}
for t in SP:
    print("  %s: %d episodes with matched windows, %d windows (%.0f s equivalent)"
          % (t, len(SP[t]), sum(s[1] for s in SP[t]),
             sum(s[1] for s in SP[t]) * NPER / 2 / L.FS))

print()
print("=" * 108)
print("C1 -- EPISODE BOOTSTRAP of the V103/V102 band-RMS ratio.  Does the CI exclude 1.0?")
print("=" * 108)
rng = np.random.default_rng(11)
NB = 4000
print("%12s %12s %12s %12s %22s %10s" %
      ('band (Hz)', 'V102 r96', 'V103 r9e', 'ratio', 'ratio 95 % CI', 'P(>1)'))
for lo, hi in FB:
    a, b = SP['r96'], SP['r9e']
    r = rms(b, lo, hi) / rms(a, lo, hi)
    dr = np.array([rms([b[j] for j in rng.integers(0, len(b), len(b))], lo, hi)
                   / rms([a[j] for j in rng.integers(0, len(a), len(a))], lo, hi)
                   for _ in range(NB)])
    print("%6.0f-%-5.0f %12.4f %12.4f %12.3f   [%8.3f, %8.3f] %10.3f"
          % (lo, hi, rms(a, lo, hi), rms(b, lo, hi), r,
             np.percentile(dr, 2.5), np.percentile(dr, 97.5), (dr > 1).mean()))

print()
print("=" * 108)
print("C2 -- SPLIT-HALF NULL INSIDE each route (interleaved episodes).  THE FLOOR.")
print("=" * 108)
print("%12s %18s %18s %18s" % ('band (Hz)', 'r96 halfA/halfB', 'r9e halfA/halfB',
                               'r97 halfA/halfB'))
for lo, hi in FB:
    row = []
    for t in ('r96', 'r9e', 'r97'):
        sp = SP[t]
        row.append(rms(sp[0::2], lo, hi) / rms(sp[1::2], lo, hi))
    print("%6.0f-%-5.0f %18.3f %18.3f %18.3f" % (lo, hi, *row))
print()
print("  ⇒ compare each C2 entry with the SAME band's C1 ratio.  A between-route ratio that is")
print("    not larger than the within-route split-half spread is EXPOSURE, not build.")

print()
print("=" * 108)
print("C3/C4 -- PLACEBO BAND and a SCALE REFERENCE the operator actually scored")
print("=" * 108)
print("  C3 placebo: 26-40 Hz.  The c4 lever's own model gives |A| ratio ~1.00 there")
print("     (studies/sessions/v104/v104_recommend_k.py sec 5: 26-31 Hz = 0.987 at k=1.85), so any movement is drive.")
print("  C4 scale:   r97 (STOCK 1x) vs r96 (V102 6x) -- a contrast the operator DID score")
print("     ('no vibration or grinding' vs 'vibration and grinding ... ratcheting was bad').")
print()
print("%12s %14s %14s %14s %14s" %
      ('band (Hz)', 'V103/V102', 'V102/STOCK', 'V103/STOCK', 'ratio of ratios'))
for lo, hi in FB:
    r32 = rms(SP['r9e'], lo, hi) / rms(SP['r96'], lo, hi)
    r27 = rms(SP['r96'], lo, hi) / rms(SP['r97'], lo, hi)
    r37 = rms(SP['r9e'], lo, hi) / rms(SP['r97'], lo, hi)
    print("%6.0f-%-5.0f %14.3f %14.3f %14.3f %14.3f" % (lo, hi, r32, r27, r37, r32 / r27))
print()
print("  ⇒ if V103/V102 at 6-9 Hz is the SAME SIZE as the placebo band's V103/V102, the")
print("    operator's null and the instrument AGREE and nothing needs explaining.")


# ==================================================================================================
# C5 -- THE ONE THAT MATTERS: does 6-9 Hz track the 0xC6CD0 GAIN, the thing he DID score?
#       Bootstrap CIs on STOCK -> 6x, per band, and split by speed.
# ==================================================================================================
def ep_specs_v(tag, vlo, vhi):
    d = L.load(tag)
    eng = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    ra = np.abs(d['rate_f'].astype(float))
    keep = (v >= vlo) & (v < vhi) & (ra <= 60.0)
    rate = d['rate_f'].astype(float)
    idx = np.flatnonzero(np.diff(eng.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(eng)]))
    w = np.hanning(NPER + 1)[:NPER]
    U = (w ** 2).sum()
    tt = np.arange(NPER)
    A = np.vstack([tt, np.ones(NPER)]).T
    out = []
    for i in range(len(b) - 1):
        a0, b0 = b[i], b[i + 1]
        if not eng[a0] or (b0 - a0) < NPER:
            continue
        S, nw = None, 0
        for s in range(a0, b0 - NPER + 1, NPER // 2):
            if not keep[s:s + NPER].all():
                continue
            xs = rate[s:s + NPER]
            if not np.all(np.isfinite(xs)):
                continue
            xs = xs - A @ np.linalg.lstsq(A, xs, rcond=None)[0]
            X = np.fft.rfft(xs * w)
            S = ((X.conj() * X).real / (L.FS * U)) if S is None \
                else S + (X.conj() * X).real / (L.FS * U)
            nw += 1
        if nw:
            out.append((S, nw))
    return out


print()
print("=" * 108)
print("C5 -- STOCK (1x, r97) -> V102 (6x, r96): the contrast the OPERATOR SCORED, with CIs")
print("=" * 108)
print("  Operator on STOCK: 'No vibration or grinding.  Maybe ever so slightly, barely")
print("  perceptible ratcheting.'   On V102 (6x): 'Vibration and grinding somewhere between 4x")
print("  and 8x.  Ratcheting was bad.'   ⇒ this contrast IS above his threshold, by his own words.")
print()
rng2 = np.random.default_rng(23)
for vlo, vhi, nm in ((18.0, 90.0, 'matched 18-90 km/h'), (0.0, 40.0, 'LOW  0-40 km/h'),
                     (60.0, 130.0, 'HIGH 60-130 km/h')):
    A_ = ep_specs_v('r97', vlo, vhi)
    B_ = ep_specs_v('r96', vlo, vhi)
    if len(A_) < 2 or len(B_) < 2:
        print("  %-20s (too few episodes: %d / %d)" % (nm, len(A_), len(B_)))
        continue
    print("  %-20s  stock %d episodes / %d windows   6x %d episodes / %d windows"
          % (nm, len(A_), sum(s[1] for s in A_), len(B_), sum(s[1] for s in B_)))
    print("%14s %12s %12s %12s %24s %10s" %
          ('band (Hz)', 'STOCK', '6x (V102)', '6x/STOCK', '95 % CI', 'P(>1)'))
    for lo, hi in FB:
        r = rms(B_, lo, hi) / rms(A_, lo, hi)
        dr = np.array([rms([B_[j] for j in rng2.integers(0, len(B_), len(B_))], lo, hi)
                       / rms([A_[j] for j in rng2.integers(0, len(A_), len(A_))], lo, hi)
                       for _ in range(3000)])
        flag = "  <-- CLEARS 1.0" if np.percentile(dr, 2.5) > 1.0 else ""
        print("%8.0f-%-5.0f %12.4f %12.4f %12.3f   [%9.3f, %9.3f] %10.3f%s"
              % (lo, hi, rms(A_, lo, hi), rms(B_, lo, hi), r,
                 np.percentile(dr, 2.5), np.percentile(dr, 97.5), (dr > 1).mean(), flag))
    print()
print("  ⇒ THE BAND(S) WHOSE CI CLEARS 1.0 ARE THE ONES THAT ACTUALLY TRACK THE GAIN HE SCORED.")
print("    A lever aimed at a band that does NOT clear here is aimed at a band whose entire")
print("    stock-to-6x excursion is inside the drive-to-drive floor.")
