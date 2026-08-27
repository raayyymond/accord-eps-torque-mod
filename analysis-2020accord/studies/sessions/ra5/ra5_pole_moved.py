r"""V105 / route `a5` -- THE MECHANISM, AND THE NULL THAT LICENSES IT.

`studies/sessions/ra5/ra5_adjudicate.py` found, from ABSOLUTE spectra (not ratios), that the 21-28 Hz mode's PEAK
FREQUENCY is different on V105 in BOTH windows:

    engaged < 16 km/h    V104 peak 22.73 Hz  PSD 51.4   ->  V105 peak 20.48 Hz  PSD 17.5
    engaged 40-95 km/h   V104 peak 26.47 Hz  PSD 49.0   ->  V105 peak 26.97 Hz  PSD 79.1

and that inside the notch's own coverage the PSD fell on both, while just outside it rose.  That
is the signature of a notch DISPLACING a closed-loop pole rather than damping it.

This file tries to break that claim four ways before it is reported:

N1  PEAK-FREQUENCY CI -- episode bootstrap of the argmax.  A 0.25 Hz bin shift is not a finding;
    a shift whose bootstrap CI excludes the other build's peak is.
N2  RATE-MATCHED RE-RUN -- redo the absolute spectra INSIDE the matched 15-40 deg/s stratum, so
    the low-speed peak move cannot be a rate-mix artifact.
N3  WITHIN-DRIVE RANDOM-SPLIT NULL -- the honest noise floor for the headline ratio.  Many random
    halves of the SAME drive, same statistic, same episode unit.  If |log r| of the cross-build
    ratio is inside that null, the ratio is NOT quotable.  [`feedback-episodes-not-windows`]
N4  SPEED-MATCHED HIGHWAY ABSOLUTE SPECTRA (55-70 km/h) -- the ratio there is contaminated by a
    moving peak; only the absolute spectra say which build is louder where.
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
import json

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
FS = L.FS
CARRIER = (21.0, 28.0)
PLACEBO = (32.0, 45.0)
THR_FRAC = 0.70
MIN_BURST_S, MERGE_GAP_S = 0.25, 0.15
TAGS = ('r97', 'r96', 'r9e', 'ra4', 'ra5')
NAMES = {'r97': 'STOCK 1x', 'r96': 'V102 6x', 'r9e': 'V103 6x', 'ra4': 'V104 6x',
         'ra5': 'V105 NOTCH'}
NPER = int(round(4 * FS))
FB = np.fft.rfftfreq(NPER, 1 / FS)
WIN = np.hanning(NPER + 1)[:NPER]
UU = (WIN ** 2).sum()
DF = FB[1] - FB[0]
OUT = {}


def bp_analytic(x, lo, hi):
    n = len(x)
    X = np.fft.rfft(x - x.mean())
    fr = np.fft.rfftfreq(n, 1 / FS)
    Y = np.zeros_like(X)
    keep = (fr >= lo) & (fr < hi)
    Y[keep] = X[keep]
    Z = np.zeros(n, complex)
    Z[:len(Y)] = 2.0 * Y
    Z[0] /= 2
    return np.abs(np.fft.ifft(Z))


def bursts(env, thr_on, thr_off):
    on = np.zeros(len(env), bool)
    st = False
    for i, x in enumerate(env):
        st = (x >= thr_on) if not st else (x >= thr_off)
        on[i] = st
    idx = np.flatnonzero(np.diff(on.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(on)]))
    segs = [(int(b[i]), int(b[i + 1])) for i in range(len(b) - 1) if on[b[i]]]
    mg = []
    for s, e in segs:
        if mg and (s - mg[-1][1]) <= int(MERGE_GAP_S * FS):
            mg[-1] = (mg[-1][0], e)
        else:
            mg.append((s, e))
    return [(s, e) for s, e in mg if (e - s) >= int(MIN_BURST_S * FS)]


def run_slices(tag, vlo, vhi, minlen_s=2.0):
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    m = e & (v >= vlo) & (v < vhi)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    ml = int(minlen_s * FS)
    return d, [(int(a), int(c)) for a, c in zip(b[:-1], b[1:]) if m[a] and (c - a) >= ml]


def welch_per_ep(tag, vlo, vhi, ratelo=None, ratehi=None):
    d, rs = run_slices(tag, vlo, vhi, 4.2)
    x = d['rate_f'].astype(float)
    rc = np.abs(d['rate_c'].astype(float))
    per = []
    for a, b in rs:
        seg, rseg = x[a:b], rc[a:b]
        acc, nw = None, 0
        for s in range(0, len(seg) - NPER + 1, NPER // 2):
            if ratelo is not None and not (ratelo <= np.median(rseg[s:s + NPER]) < ratehi):
                continue
            xs = seg[s:s + NPER] - seg[s:s + NPER].mean()
            X = np.fft.rfft(xs * WIN)
            p = (X.conj() * X).real / (FS * UU)
            acc = p if acc is None else acc + p
            nw += 1
        if nw:
            per.append((acc, nw))
    return per


def pool(per):
    return None if not per else sum(p[0] for p in per) / sum(p[1] for p in per)


def peak_ci(per, lo, hi, nb=4000, seed=53):
    """Episode bootstrap of the argmax frequency in [lo, hi]."""
    k = (FB >= lo) & (FB <= hi)
    ff = FB[k]
    rg = np.random.default_rng(seed)
    pk = []
    for _ in range(nb):
        pick = rg.integers(0, len(per), len(per))
        S = sum(per[j][0] for j in pick) / sum(per[j][1] for j in pick)
        pk.append(ff[int(np.argmax(S[k]))])
    S0 = pool(per)
    return float(ff[int(np.argmax(S0[k]))]), float(np.percentile(pk, 2.5)), \
        float(np.percentile(pk, 97.5)), float(S0[k].max())


# ================================================================= N1 + N2
print("=" * 118)
print("N1/N2.  PEAK FREQUENCY WITH AN EPISODE-BOOTSTRAP CI -- pooled, then RATE-MATCHED.")
print("        A 0.25 Hz bin shift is noise.  A shift whose CI excludes the other build's")
print("        peak is a moved pole.")
print("=" * 118)
for lbl, vlo, vhi, rlo, rhi in (
        ('engaged < 16 km/h, ALL rates', 0.0, 16.0, None, None),
        ('engaged < 16 km/h, RATE-MATCHED 15-40 deg/s', 0.0, 16.0, 15.0, 40.0),
        ('engaged 40-95 km/h', 40.0, 95.0, None, None),
        ('engaged 55-70 km/h (SPEED-MATCHED)', 55.0, 70.0, None, None)):
    print("\n  %s" % lbl)
    print("%12s %6s %10s %22s %12s" % ('build', 'eps', 'peak Hz', '95 % CI (episode boot)',
                                       'peak PSD'))
    for t in TAGS:
        per = welch_per_ep(t, vlo, vhi, rlo, rhi)
        if len(per) < 3:
            print("%12s %6d   -- fewer than 3 episodes, no CI --" % (NAMES[t], len(per)))
            continue
        p, lo2, hi2, pv = peak_ci(per, 18.0, 33.0)
        print("%12s %6d %10.2f %22s %12.4f" % (NAMES[t], len(per), p,
                                               "[%.2f, %.2f]" % (lo2, hi2), pv))
        OUT.setdefault('peaks', {}).setdefault(lbl, {})[NAMES[t]] = dict(
            peak=p, ci=[lo2, hi2], psd=pv, eps=len(per))

# ================================================================= N3 within-drive null
print()
print("=" * 118)
print("N3.  🛑 THE WITHIN-DRIVE RANDOM-SPLIT NULL for the headline statistic")
print("     (21-28 Hz in-burst median envelope, engaged < 16 km/h, 15-40 deg/s).")
print("     2000 random splits of each drive's OWN episodes into two halves.  The cross-build")
print("     ratio must sit OUTSIDE this null to be quotable.")
print("=" * 118)
d97, rs97 = run_slices('r97', 0.0, 16.0)
env97 = np.concatenate([bp_analytic(d97['rate_f'].astype(float)[a:b], *CARRIER) for a, b in rs97])
THR_ON = float(np.percentile(env97, 95))
p97 = np.concatenate([bp_analytic(d97['rate_f'].astype(float)[a:b], *PLACEBO) for a, b in rs97])
THR_P = float(np.percentile(p97, 95))


def stratum_amps(tag, band, thr, lo=15.0, hi=40.0):
    d, rs = run_slices(tag, 0.0, 16.0)
    rate_f = d['rate_f'].astype(float)
    rc = np.abs(d['rate_c'].astype(float))
    per = []
    for a, b in rs:
        env = bp_analytic(rate_f[a:b], *band)
        on = np.zeros(len(env), bool)
        for s, e in bursts(env, thr, THR_FRAC * thr):
            on[s:e] = True
        sel = (rc[a:b] >= lo) & (rc[a:b] < hi)
        if sel.sum() < int(0.25 * FS):
            continue
        per.append(env[on & sel])
    return per


def med(pp):
    aa = [p for p in pp if len(p)]
    return float(np.median(np.concatenate(aa))) if aa else np.nan


AM = {t: stratum_amps(t, CARRIER, THR_ON) for t in TAGS}
AP = {t: stratum_amps(t, PLACEBO, THR_P) for t in TAGS}
print("%12s %6s %30s %26s"
      % ('build', 'eps', 'random-split ratio 95 % null', 'null half-width (log2)'))
NULL = {}
rg = np.random.default_rng(67)
for t in TAGS:
    per = AM[t]
    if len(per) < 6:
        print("%12s %6d   -- fewer than 6 episodes, no null --" % (NAMES[t], len(per)))
        continue
    rs2 = []
    for _ in range(2000):
        idx = rg.permutation(len(per))
        h = len(per) // 2
        a, b = med([per[j] for j in idx[:h]]), med([per[j] for j in idx[h:]])
        if np.isfinite(a) and np.isfinite(b) and b > 0:
            rs2.append(a / b)
    q = np.percentile(rs2, [2.5, 97.5])
    NULL[t] = [float(q[0]), float(q[1])]
    print("%12s %6d %30s %26.3f"
          % (NAMES[t], len(per), "[%.3f, %.3f]" % (q[0], q[1]),
             0.5 * np.log2(q[1] / q[0])))
OUT['random_split_null'] = NULL

r54 = med(AM['ra5']) / med(AM['ra4'])
p54 = med(AP['ra5']) / med(AP['ra4'])
print()
print("  MEASURED CROSS-BUILD RATIO V105/V104 in this cell:  21-28 Hz **%.3f**   32-45 Hz %.3f"
      % (r54, p54))
print("                                        placebo-corrected **%.3f**" % (r54 / p54))
worst = max((abs(np.log(NULL[t][0])) if NULL[t][0] < 1 else 0) for t in NULL)
print("  Widest within-drive null bound below 1.00 across all builds: %.3f" % np.exp(-worst))
for t in NULL:
    inside = NULL[t][0] <= r54 <= NULL[t][1]
    print("     vs %-11s null [%.3f, %.3f]  =>  measured 0.343 is %s"
          % (NAMES[t], NULL[t][0], NULL[t][1], "INSIDE (not quotable)" if inside
             else "OUTSIDE"))
OUT['measured'] = dict(raw=float(r54), placebo=float(p54), corrected=float(r54 / p54))

# ================================================================= N4 highway absolute
print()
print("=" * 118)
print("N4.  SPEED-MATCHED HIGHWAY (55-70 km/h) -- ABSOLUTE spectra, 22-30 Hz.")
print("     The ratio there is contaminated by a moving peak; only absolutes say who is louder.")
print("=" * 118)
SP = {}
for t in TAGS:
    per = welch_per_ep(t, 55.0, 70.0)
    if len(per) < 2:
        continue
    SP[t] = (pool(per), per)
k = (FB >= 22.0) & (FB <= 30.0)
print("%7s" % 'Hz' + "".join("%12s" % NAMES[t] for t in TAGS if t in SP))
for i, f in enumerate(FB[k]):
    print("%7.2f" % f + "".join("%12.4f" % SP[t][0][k][i] for t in TAGS if t in SP))
print()
for t in TAGS:
    if t not in SP:
        continue
    S = SP[t][0]
    print("  %-11s 21-28 RMS %8.4f   24.5-26.5 RMS %8.4f   26.5-28 RMS %8.4f   eps %d"
          % (NAMES[t], np.sqrt((S[(FB >= 21) & (FB < 28)].sum()) * DF),
             np.sqrt((S[(FB >= 24.5) & (FB < 26.5)].sum()) * DF),
             np.sqrt((S[(FB >= 26.5) & (FB < 28)].sum()) * DF), len(SP[t][1])))
    OUT.setdefault('hwy_matched_abs', {})[NAMES[t]] = dict(
        rms_21_28=float(np.sqrt((S[(FB >= 21) & (FB < 28)].sum()) * DF)),
        rms_notch=float(np.sqrt((S[(FB >= 24.5) & (FB < 26.5)].sum()) * DF)),
        rms_above=float(np.sqrt((S[(FB >= 26.5) & (FB < 28)].sum()) * DF)),
        eps=len(SP[t][1]))

# episode-bootstrap CI on the two highway sub-band ratios that matter
if 'ra5' in SP and 'ra4' in SP:
    rg2 = np.random.default_rng(71)
    res = {}
    for nm, lo2, hi2 in (('24.5-26.5 (INSIDE the notch)', 24.5, 26.5),
                         ('26.5-28.0 (JUST ABOVE it)', 26.5, 28.0),
                         ('21.0-24.5 (BELOW it)', 21.0, 24.5)):
        vals = []
        kk = (FB >= lo2) & (FB < hi2)
        for _ in range(4000):
            o = []
            for P in (SP['ra5'][1], SP['ra4'][1]):
                pick = rg2.integers(0, len(P), len(P))
                S = sum(P[j][0] for j in pick) / sum(P[j][1] for j in pick)
                o.append(np.sqrt(S[kk].sum() * DF))
            vals.append(o[0] / o[1])
        q = np.percentile(vals, [2.5, 97.5])
        res[nm] = [float(np.median(vals)), float(q[0]), float(q[1])]
        print("  V105/V104 RMS  %-30s  %.3f  [%.3f, %.3f]" % (nm, np.median(vals), q[0], q[1]))
    OUT['hwy_matched_subband'] = res
    print("  ⚠ 4 episodes per arm.  These CIs are WIDE by construction; read the DIRECTION.")

json.dump(OUT, open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                                 '_scratch/out/_ra5_pole.json'), 'w'), indent=1, default=float)
print("\nwrote _scratch/out/_ra5_pole.json")
