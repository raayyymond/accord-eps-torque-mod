r"""GRIND #1 -- ~21.0-22.5 Hz, ENGAGED, < 16 km/h.  BOTH READINGS.

READING 1  DIRECT ACOUSTIC CONTENT at 21.0-22.5 Hz, now at 0.9766 Hz resolution.
           ⚠ This is a NARROWER test than the one already run.  `decode/extract_audio_env.py` measured a
           21-28 Hz band-pass of the raw PCM (correct method, immune to the bin defect) and found
           no stock-vs-6x separation -- but a 7 Hz band dilutes a ~1 Hz line 4-7x.  21.0-22.5 Hz
           is a genuinely different measurement.

READING 2  AMPLITUDE MODULATION at 21.0-22.5 Hz of broadband audible carriers.  ⭐ PRIMARY.
           21 Hz is a 16 m wavelength and a steering rack is a hopeless radiator there, so the
           direct null is close to PREDICTED physics rather than evidence of absence.  A rough,
           sticking mechanism makes itself heard by MODULATING broadband noise at the mode rate.
           Envelopes at 500 Hz behind a 200 Hz low-pass => modulation Nyquist 250 Hz, >5x headroom
           over 47 Hz and no filter shaping anywhere in the band of interest.

CONTROLS, in force before any number is quoted:
   PRIMARY   ENGAGED vs ROLLING MANUAL (v >= 2 km/h) **within route**.  Road noise, wind, engine
             order and HVAC do not know whether LKAS is engaged.  Manual <16 km/h is 73-83 %
             PARKED on every route, so the rolling filter is mandatory, not optional.
   NULL      split-half within a route, same estimator, BEFORE any between-route ratio.
   SURROGATE phase-shuffled, for every modulation claim.
   SPEED     re-weighted to a common mixture in 2 km/h bins.
   🛑 STOCK IS ONE ROUTE.  Between-route level comparisons cannot separate build from drive; they
      are reported but they are NOT the headline.  The within-route engaged/manual contrast is.

THE BAR, from the wheel-rate result on this same mode: burst duty 0.056 stock vs 0.93-0.95 at 6x,
longest burst 0.69 s vs 7-14 s, DISJOINT intervals.  A 2-3x ratio is not that and will not be
presented as if it were.
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
import json
import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import acoustic_lib as A                                            # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TAGS = ['r97', 'r85', 'r96', 'r9e', 'ra4', 'r95']
G1 = (21.0, 22.5)
VLO, VHI = 0.0, 16.0
FSE = 500.0

D = {}
for t in TAGS:
    g = np.load(os.path.join(A.HERE, '_cache_%s' % t, '%s_grind.npz' % t))
    c = np.load(os.path.join(A.HERE, '_cache_%s' % t, '%s.npz' % t), allow_pickle=True)
    ct = c['t'].astype(float)
    eng_c = (c['cc_lat'].astype(float) > 0.5).astype(float)
    v_c = c['v_rear'].astype(float) * 3.6
    ts, te = g['t_sp'].astype(float), g['t_env'].astype(float)
    D[t] = dict(
        t_sp=ts, sp=g['sp'].astype(float), sp_f=g['sp_f'].astype(float),
        t_env=te, env=g['env'].astype(float), env_f=g['env_f'], splice=g['splice'].astype(bool),
        eng_sp=np.interp(ts, ct, eng_c) > 0.5, v_sp=np.interp(ts, ct, v_c),
        eng_env=np.interp(te, ct, eng_c) > 0.5, v_env=np.interp(te, ct, v_c))
F = D['r97']['sp_f']
BINS = np.flatnonzero((F >= G1[0]) & (F <= G1[1]))
print("  PASS A resolution %.4f Hz; grind #1 %.1f-%.1f Hz spans %d bins: %s"
      % (F[1] - F[0], G1[0], G1[1], len(BINS), np.round(F[BINS], 2)))
print("  PASS B envelopes @ %.0f Hz, modulation Nyquist %.0f Hz" % (FSE, FSE / 2))


def msk(t, arr, engaged=True, rolling=True):
    d = D[t]
    e = d['eng_sp'] if arr == 'sp' else d['eng_env']
    v = d['v_sp'] if arr == 'sp' else d['v_env']
    m = (e if engaged else ~e) & (v >= VLO) & (v < VHI)
    if arr == 'env':
        m = m & ~d['splice']
    if not engaged and rolling:
        m = m & (v >= A.V_ROLL)
    return m


def runs(m, fs, min_s):
    m = np.asarray(m, bool)
    i = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], i, [len(m)]))
    return [(int(b[k]), int(b[k + 1])) for k in range(len(b) - 1)
            if m[b[k]] and (b[k + 1] - b[k]) / fs >= min_s]


def speed_w_ratio(t, col_a, col_b, nboot=1500, seed=5):
    """engaged/manual amplitude ratio at a common speed mixture, block bootstrap over 5 s blocks."""
    d = D[t]
    ed = np.arange(VLO, VHI + 2, 2.0)
    out = {}
    for nm, (m, x) in (('e', (msk(t, 'sp', True), col_a)), ('m', (msk(t, 'sp', False), col_b))):
        rr = runs(m, 3.906, 2.0)
        blocks = []
        nb = max(int(5.0 * 3.906), 4)
        for a, b in rr:
            for s in range(a, b - nb // 2, nb):
                blocks.append((x[s:min(s + nb, b)], d['v_sp'][s:min(s + nb, b)]))
        out[nm] = blocks
    if len(out['e']) < 3 or len(out['m']) < 3:
        return None

    def wm(bl, w):
        s = np.zeros(len(ed) - 1)
        c = np.zeros(len(ed) - 1)
        for p, v in bl:
            j = np.clip(np.digitize(v, ed) - 1, 0, len(ed) - 2)
            np.add.at(s, j, p)
            np.add.at(c, j, 1)
        return s, c
    se, ce = wm(out['e'], None)
    sm, cm = wm(out['m'], None)
    ok = (ce >= 8) & (cm >= 8)
    if not ok.any():
        return None
    w = np.minimum(ce, cm) * ok
    w = w / w.sum()
    f = lambda s, c: float(np.sum(w * np.where(c > 0, s / np.maximum(c, 1), 0.0)))
    pt = np.sqrt(f(se, ce) / max(f(sm, cm), 1e-300))
    rg = np.random.default_rng(seed)
    bo = np.empty(nboot)
    for i in range(nboot):
        a1, c1 = wm([out['e'][j] for j in rg.integers(0, len(out['e']), len(out['e']))], None)
        a2, c2 = wm([out['m'][j] for j in rg.integers(0, len(out['m']), len(out['m']))], None)
        bo[i] = np.sqrt(f(a1, c1) / max(f(a2, c2), 1e-300))
    lo, hi = np.percentile(bo[np.isfinite(bo)], [2.5, 97.5])
    return dict(r=pt, lo=float(lo), hi=float(hi), ne=len(out['e']), nm=len(out['m']))


print()
print("=" * 122)
print("READING 1 -- DIRECT ACOUSTIC CONTENT at %.1f-%.1f Hz, engaged <16 km/h" % G1)
print("=" * 122)
print("%-6s %-9s %8s %10s %10s %24s %10s" %
      ('route', 'build', 'gain', 'eng s', 'man s', 'ENG/MAN [95% CI]', 'prom'))
R1 = {}
for t in TAGS:
    d = D[t]
    p = d['sp'][:, BINS].sum(1)
    r = speed_w_ratio(t, p, p)
    # spectral prominence of the line against 12-35 Hz neighbours, engaged only
    me = msk(t, 'sp', True)
    nb = (F >= 12) & (F <= 35)
    nb[BINS] = False
    prom = d['sp'][me][:, BINS].mean() / np.median(d['sp'][me][:, nb].mean(0))
    R1[t] = dict(ratio=None if r is None else r['r'], prom=float(prom))
    print("%-6s %-9s %8.0fx %10.1f %10.1f %24s %10.2f"
          % (t, A.NAMES[t], A.GAIN[t], msk(t, 'sp', True).sum() / 3.906,
             msk(t, 'sp', False).sum() / 3.906,
             ("%.2f [%.2f, %.2f]" % (r['r'], r['lo'], r['hi'])) if r else '-', prom))
print("  ENG/MAN is the amplitude ratio at a common speed mixture, within route.")
print("  'prom' is the %.1f-%.1f Hz band mean divided by the median of its 12-35 Hz neighbours," % G1)
print("  engaged: > 1 means a LINE sits there rather than smooth background.")

print()
print("=" * 122)
print("READING 2 (PRIMARY) -- AMPLITUDE MODULATION at %.1f-%.1f Hz of the audible carriers" % G1)
print("=" * 122)


def am_excess(x, fs=FSE, lo=G1[0], hi=G1[1], nper=1024):
    """Excess of the envelope PSD in [lo,hi] over a log-log background fitted on 8-18 and 26-45 Hz."""
    if len(x) < nper:
        return None
    f, p = signal.welch(x - x.mean(), fs=fs, nperseg=nper, noverlap=nper // 2, detrend='linear')
    tgt = (f >= lo) & (f <= hi)
    bg = ((f >= 8) & (f < 18)) | ((f > 26) & (f <= 45))
    if tgt.sum() < 2 or bg.sum() < 8:
        return None
    cf = np.polyfit(np.log(f[bg]), np.log(p[bg]), 1)
    return float(np.mean(p[tgt] / np.exp(np.polyval(cf, np.log(f[tgt])))))


def surro(x, rng):
    X = np.fft.rfft(x - x.mean())
    ph = rng.uniform(0, 2 * np.pi, len(X))
    ph[0] = 0
    return np.fft.irfft(np.abs(X) * np.exp(1j * ph), n=len(x))


rng = np.random.default_rng(31)
BF = D['r97']['env_f']
R2 = {}
for j in range(len(BF)):
    print("\n  ---- carrier %g-%g Hz ----" % tuple(BF[j]))
    print("%-6s %-9s %8s %12s %12s %10s %24s %9s" %
          ('route', 'build', 'gain', 'ENG excess', 'MAN excess', 'eng/man',
           'surrogate [2.5,97.5]', 'verdict'))
    for t in TAGS:
        d = D[t]
        row = {}
        for nm, eng in (('eng', True), ('man', False)):
            rr = runs(msk(t, 'env', eng), FSE, 3.0)
            v = [am_excess(d['env'][a:b, j]) for a, b in rr]
            v = [x for x in v if x is not None]
            row[nm] = float(np.mean(v)) if v else None
        rr = runs(msk(t, 'env', True), FSE, 3.0)
        sur = []
        for a, b in rr[:6]:
            for _ in range(20):
                s = am_excess(surro(d['env'][a:b, j], rng))
                if s is not None:
                    sur.append(s)
        sl, sh = (np.percentile(sur, [2.5, 97.5]) if sur else (np.nan, np.nan))
        hit = row['eng'] is not None and np.isfinite(sh) and row['eng'] > sh
        R2.setdefault("%g-%g" % tuple(BF[j]), {})[t] = dict(
            eng=row['eng'], man=row['man'], sur_lo=float(sl), sur_hi=float(sh))
        print("%-6s %-9s %8.0fx %12s %12s %10s %24s %9s"
              % (t, A.NAMES[t], A.GAIN[t],
                 ("%.3f" % row['eng']) if row['eng'] else '-',
                 ("%.3f" % row['man']) if row['man'] else '-',
                 ("%.2f" % (row['eng'] / row['man'])) if (row['eng'] and row['man']) else '-',
                 "[%.3f, %.3f]" % (sl, sh) if np.isfinite(sl) else '-',
                 'EXCESS' if hit else 'null'))

json.dump({'reading1': R1, 'reading2': R2},
          open(os.path.join(A.HERE, '_scratch/out/_acoustic_grind1.json'), 'w'), indent=1, default=float)
print("\n  wrote _scratch/out/_acoustic_grind1.json")
