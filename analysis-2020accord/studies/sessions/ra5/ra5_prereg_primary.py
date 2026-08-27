r"""V105 (route `a5`) -- THE PRE-REGISTERED PRIMARY, RATE-STRATIFIED, PLUS THE NOTCH-SHAPE TEST.

`studies/sessions/ra5/ra5_burst_conditional.py` (a 2-line delta on `studies/sessions/ra4/ra4_burst_conditional.py`: `TAGS`/`NAMES` only) runs
the pre-registered BURST detector verbatim.  This file supplies the three things the drive card
(`docs/HANDOFF-2026-08-22-...notch.md` sec 12) asks for that the burst script does not:

  (1) the PRIMARY **stratified by steering rate, 15-40 deg/s as the headline cell**;
  (2) the CONTROLS the operator's own doctrine requires FIRST -- split-half null, matched speed
      AND rate census, 32-45 Hz placebo band;
  (3) the NOTCH-SHAPE test: did 25.5 Hz move MORE than its own neighbours?

=================================================================================================
🛑 CONTROLS RUN BEFORE ANY RATIO IS QUOTED  [`feedback-run-the-control-before-the-measurement`]
=================================================================================================
C1  MATCHED-EXPOSURE CENSUS -- speed AND steering rate, per route, inside the scoring window.
    `accord-ratchet-axis-is-wheel-rate` + drive-card sec 5.3: the 21-28 Hz mode is RATE-driven
    (~90x stock at 15-40 deg/s, COLLAPSING to stock above 100 deg/s).  An unmatched rate
    distribution manufactures or destroys a build effect on its own.
C2  SPLIT-HALF NULL, within each drive, on the headline statistic, bootstrapped over EPISODES
    (`feedback-episodes-not-windows`).  Quote no cross-build ratio the within-drive null spans.
C3  32-45 Hz PLACEBO BAND -- drive-card sec 4.4 made placebo correction MANDATORY for any
    cross-drive ratio in this corpus.

=================================================================================================
UNITS -- both scale traps handled explicitly
=================================================================================================
* `rate_f` is the 0x18F wheel-rate channel and is **0.7996x true deg/s**
  [`accord-rate-f-is-0p7996-of-true-degs`].  ALL band statistics here are on `rate_f`, exactly as
  every prior score in this corpus, so RATIOS are exact; absolute deg/s are 1.2506x low.
* the STRATIFYING axis is `rate_c` (TRUE deg/s), so the stratum edges 5/15/40/100 deg/s mean what
  the drive card says they mean.  Cross-checked against `rate_f / 0.7996` in C1.
* speeds are `v_rear * 3.6` km/h (`v_rear` is m/s -- verified against `cs_v` and `ws_kph`).

=================================================================================================
THE NOTCH-SHAPE TEST -- pre-declared bands, before any spectrum was plotted
=================================================================================================
V105's biquad |H|:  20.0 Hz 0.589 · 21.73 0.415 · 24.0 0.160 · 24.9 0.062 · **25.5 2.09e-6** ·
26.8 0.123 · 42.3 0.680.  V104's biquad is ~1.85 and FLAT across all of these (its notch sat at
55 Hz).  So if the notch is in force AND the lane reaches the wheel:
    CORE      24.5-26.5 Hz   must fall MUCH more than
    SHOULDERS 20.0-23.0 and 29.0-33.0 Hz
A whole-band change with NO core-vs-shoulder dent is a DIFFERENT (and more interesting) result
than a notch working, and is reported as such.

⚠ The wheel is the CLOSED LOOP, not the lane.  A notch inside a feedback path does not put its own
|H| on the output; this test asks only whether the dent is LOCALISED at the notch centre.
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
MIN_BURST_S = 0.25
MERGE_GAP_S = 0.15
VLO, VHI = 0.0, 16.0
TAGS = ('r97', 'r96', 'r9e', 'ra4', 'ra5')
NAMES = {'r97': 'STOCK 1x', 'r96': 'V102 6x', 'r9e': 'V103 6x', 'ra4': 'V104 6x',
         'ra5': 'V105 NOTCH'}
RATE_EDGES = [0.0, 5.0, 15.0, 40.0, 100.0, 1e9]
RATE_LBL = ['0-5', '5-15', '15-40', '40-100', '100+']
NPER = int(round(4 * FS))
FB = np.fft.rfftfreq(NPER, 1 / FS)
WIN = np.hanning(NPER + 1)[:NPER]
UU = (WIN ** 2).sum()
DF = FB[1] - FB[0]
CORE = (24.5, 26.5)
SHOULDER = [(20.0, 23.0), (29.0, 33.0)]
OUT = {}


# ------------------------------------------------------------------ primitives (verbatim)
def bp_analytic(x, lo, hi):
    """TRUE analytic envelope of x band-limited to [lo,hi).  Identical to the pre-registered one."""
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
    state = False
    for i, x in enumerate(env):
        state = (x >= thr_on) if not state else (x >= thr_off)
        on[i] = state
    idx = np.flatnonzero(np.diff(on.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(on)]))
    segs = [(int(b[i]), int(b[i + 1])) for i in range(len(b) - 1) if on[b[i]]]
    merged = []
    for s, e2 in segs:
        if merged and (s - merged[-1][1]) <= int(MERGE_GAP_S * FS):
            merged[-1] = (merged[-1][0], e2)
        else:
            merged.append((s, e2))
    return [(s, e2) for s, e2 in merged if (e2 - s) >= int(MIN_BURST_S * FS)]


def run_slices(tag, engaged=True, vlo=VLO, vhi=VHI, minlen_s=2.0):
    """Contiguous (engaged AND speed-window) segments >= minlen_s.  The EPISODE unit."""
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    m = (e if engaged else ~e) & (v >= vlo) & (v < vhi)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    ml = int(minlen_s * FS)
    return d, [(int(b[i]), int(b[i + 1])) for i in range(len(b) - 1)
               if m[b[i]] and (b[i + 1] - b[i]) >= ml]


# ================================================================= C1 census
print("=" * 118)
print("C1.  MATCHED-EXPOSURE CENSUS -- engaged, < 16 km/h.  SPEED **AND** STEERING RATE.")
print("     The mode is RATE-driven (drive card 5.3), so an unmatched rate mix is a confound")
print("     that can manufacture or destroy a build effect on its own.")
print("=" * 118)
print("%12s %5s %7s | %6s %6s %6s | %7s %7s %7s | %s"
      % ('build', 'runs', 'sec', 'v p10', 'v p50', 'v p90', '|r| p50', '|r| p90', '|r| p99',
         '  '.join("%6s" % s for s in RATE_LBL)))
CENSUS = {}
for t in TAGS:
    d, rs = run_slices(t)
    if not rs:
        continue
    v = np.concatenate([(d['v_rear'].astype(float) * KPH)[a:b] for a, b in rs])
    rc = np.concatenate([np.abs(d['rate_c'].astype(float))[a:b] for a, b in rs])
    rf = np.concatenate([np.abs(d['rate_f'].astype(float))[a:b] for a, b in rs])
    frac = [float(np.mean((rc >= RATE_EDGES[i]) & (rc < RATE_EDGES[i + 1])))
            for i in range(len(RATE_LBL))]
    CENSUS[t] = dict(runs=len(rs), sec=len(v) / FS,
                     v=[float(np.percentile(v, q)) for q in (10, 50, 90)],
                     r=[float(np.percentile(rc, q)) for q in (50, 90, 99)],
                     rate_frac=frac, rf_over_rc=float(np.median(rf) / max(np.median(rc), 1e-9)))
    C = CENSUS[t]
    print("%12s %5d %7.1f | %6.2f %6.2f %6.2f | %7.1f %7.1f %7.1f | %s"
          % (NAMES[t], C['runs'], C['sec'], C['v'][0], C['v'][1], C['v'][2],
             C['r'][0], C['r'][1], C['r'][2], '  '.join("%6.3f" % f for f in frac)))
print("  last five columns = fraction of the window's frames in each TRUE-deg/s rate stratum.")
print("  🛑 READ THIS BEFORE ANY BUILD COMPARISON: if two builds' rate mixes differ, the pooled")
print("     21-28 Hz number is comparing different physics, not different firmware.")
OUT['census'] = CENSUS

# ================================================================= threshold (pre-registered)
d97, rs97 = run_slices('r97')
env97 = np.concatenate([bp_analytic(d97['rate_f'].astype(float)[a:b], *CARRIER) for a, b in rs97])
THR_ON = float(np.percentile(env97, 95))
THR_OFF = THR_FRAC * THR_ON
p97 = np.concatenate([bp_analytic(d97['rate_f'].astype(float)[a:b], *PLACEBO) for a, b in rs97])
THR_P = float(np.percentile(p97, 95))
print("\n  PRE-REGISTERED THRESHOLD (STOCK p95, unchanged): THR_ON = %.4f  THR_OFF = %.4f"
      % (THR_ON, THR_OFF))
print("  PLACEBO-BAND THRESHOLD (32-45 Hz, STOCK p95):    THR_P  = %.4f" % THR_P)


# ================================================================= helper: per-run stats
def per_run(tag, band, thr_on, thr_off, engaged=True, vlo=VLO, vhi=VHI):
    """Per-run (episode) burst arrays + the rate axis, so every statistic can be stratified
    and every CI can be bootstrapped over EPISODES."""
    d, rs = run_slices(tag, engaged, vlo, vhi)
    rate_f = d['rate_f'].astype(float)
    rate_c = np.abs(d['rate_c'].astype(float))
    out = []
    for a, b in rs:
        env = bp_analytic(rate_f[a:b], *band)
        bs = bursts(env, thr_on, thr_off)
        onmask = np.zeros(len(env), bool)
        for s, e2 in bs:
            onmask[s:e2] = True
        out.append(dict(env=env, on=onmask, rc=rate_c[a:b], n=len(env),
                        longest=max([(e2 - s) / FS for s, e2 in bs], default=0.0)))
    return out


def strat_stats(runs, lo, hi):
    """Pooled in-burst envelope median and burst duty inside a rate stratum, plus the per-run
    pieces needed for an EPISODE bootstrap."""
    per = []
    for R in runs:
        sel = (R['rc'] >= lo) & (R['rc'] < hi)
        if sel.sum() < int(0.25 * FS):
            continue
        on = R['on'] & sel
        per.append((float(on.sum()), float(sel.sum()), R['env'][on], R['env'][sel]))
    if not per:
        return None
    allon = np.concatenate([p[2] for p in per]) if any(len(p[2]) for p in per) else np.array([])
    allsel = np.concatenate([p[3] for p in per])
    return dict(per=per, duty=sum(p[0] for p in per) / sum(p[1] for p in per),
                inburst=float(np.median(allon)) if len(allon) else np.nan,
                allband=float(np.median(allsel)), sec=sum(p[1] for p in per) / FS,
                nrun=len(per))


def boot_ratio(perA, perB, stat='inburst', nb=4000, seed=17):
    """Episode bootstrap of a cross-build ratio.  Resamples RUNS independently in each arm."""
    rg = np.random.default_rng(seed)
    outv = []
    for _ in range(nb):
        vals = []
        for per in (perA, perB):
            pick = rg.integers(0, len(per), len(per))
            if stat == 'inburst':
                aa = [per[j][2] for j in pick if len(per[j][2])]
                vals.append(np.median(np.concatenate(aa)) if aa else np.nan)
            elif stat == 'allband':
                aa = [per[j][3] for j in pick if len(per[j][3])]
                vals.append(np.median(np.concatenate(aa)) if aa else np.nan)
            else:
                on = sum(per[j][0] for j in pick)
                tot = sum(per[j][1] for j in pick)
                vals.append(on / tot if tot else np.nan)
        if np.isfinite(vals[0]) and np.isfinite(vals[1]) and vals[1] > 0:
            outv.append(vals[0] / vals[1])
    if len(outv) < 100:
        return None
    return float(np.percentile(outv, 2.5)), float(np.percentile(outv, 97.5))


# ================================================================= C2 split-half null
print()
print("=" * 118)
print("C2.  SPLIT-HALF NULL, WITHIN EACH DRIVE -- run BEFORE any cross-build ratio is quoted.")
print("     Runs are ordered in time and split ODD / EVEN, so the two halves share the drive,")
print("     the build and the road, and differ only by sampling.  A cross-build ratio the null")
print("     spans is NOT QUOTABLE.")
print("=" * 118)
print("%12s %28s %28s" % ('build', 'split-half in-burst A ratio', 'split-half burst-duty ratio'))
RUNS = {t: per_run(t, CARRIER, THR_ON, THR_OFF) for t in TAGS}
SPLIT = {}
for t in TAGS:
    rr = RUNS[t]
    A = [R for i, R in enumerate(rr) if i % 2 == 0]
    B = [R for i, R in enumerate(rr) if i % 2 == 1]
    if len(A) < 2 or len(B) < 2:
        continue

    def _med(rs_):
        parts = [R['env'][R['on']] for R in rs_ if R['on'].any()]
        if not parts:
            return np.nan
        e = np.concatenate(parts)
        return float(np.median(e)) if len(e) else np.nan

    def _duty(rs_):
        return sum(R['on'].sum() for R in rs_) / sum(R['n'] for R in rs_)
    SPLIT[t] = dict(inburst=_med(A) / _med(B), duty=_duty(A) / _duty(B),
                    nA=len(A), nB=len(B))
    print("%12s %28.3f %28.3f" % (NAMES[t], SPLIT[t]['inburst'], SPLIT[t]['duty']))
print("  🛑 a 1.00 here is a perfect null; the distance from 1.00 is the noise floor of any")
print("     cross-build ratio computed the same way on the same amount of data.")
OUT['split_half'] = SPLIT

# ================================================================= 1. THE PRIMARY
print()
print("=" * 118)
print("1.  🛑 THE PRE-REGISTERED PRIMARY, AS WRITTEN: 21-28 Hz **IN-BURST LEVEL**, ENGAGED,")
print("    < 16 km/h, STRATIFIED BY STEERING RATE.  HEADLINE CELL = 15-40 deg/s.")
print("    Drive card: 'Predicted: substantially reduced.  The notch is -24.1 dB at 24.9 Hz.'")
print("=" * 118)
print("%12s | %s" % ('build', ' | '.join("%20s" % ("%s deg/s" % s) for s in RATE_LBL)))
PRIM = {}
for t in TAGS:
    row, cells = [], {}
    for i, lbl in enumerate(RATE_LBL):
        st = strat_stats(RUNS[t], RATE_EDGES[i], RATE_EDGES[i + 1])
        if st is None or not np.isfinite(st['inburst']):
            row.append("%20s" % '-')
            cells[lbl] = None
            continue
        row.append("%20s" % ("%.3f  (%.1fs,%dr)" % (st['inburst'], st['sec'], st['nrun'])))
        cells[lbl] = st
    PRIM[t] = cells
    print("%12s | %s" % (NAMES[t], ' | '.join(row)))
print("  cell = median 21-28 Hz analytic envelope INSIDE bursts (deg/s on `rate_f`), with")
print("  (exposure seconds, contributing runs).  Threshold is STOCK's, identical in every cell.")

print()
print("  V105 / V104 in each stratum, with a 4000x EPISODE bootstrap CI:")
print("%14s %14s %26s %14s" % ('rate stratum', 'V105 / V104', '95 % CI (episode boot)', 'verdict'))
RAT = {}
for i, lbl in enumerate(RATE_LBL):
    a, b = PRIM['ra5'].get(lbl), PRIM['ra4'].get(lbl)
    if a is None or b is None or not (np.isfinite(a['inburst']) and np.isfinite(b['inburst'])):
        print("%14s %14s %26s %14s" % (lbl, '-', 'insufficient exposure', '-'))
        continue
    r = a['inburst'] / b['inburst']
    ci = boot_ratio(a['per'], b['per'], 'inburst')
    sh = SPLIT.get('ra5', {}).get('inburst', np.nan)
    verdict = ('NULL' if (ci is None or (ci[0] <= 1.0 <= ci[1])) else
               ('REDUCED' if ci[1] < 1.0 else 'INCREASED'))
    RAT[lbl] = dict(ratio=float(r), ci=ci)
    print("%14s %14.3f %26s %14s"
          % (lbl, r, ("[%.3f, %.3f]" % ci) if ci else 'n/a', verdict))
OUT['primary'] = {t: {k: (None if v is None else
                          dict(inburst=v['inburst'], duty=v['duty'], sec=v['sec'],
                               nrun=v['nrun'], allband=v['allband']))
                      for k, v in PRIM[t].items()} for t in PRIM}
OUT['primary_ratio'] = RAT

# ================================================================= 2. rate-stratified POOLED
print()
print("=" * 118)
print("2.  DRIVE-CARD sec 5.3 REPLICATED AND EXTENDED -- POOLED (not burst-conditioned) median")
print("    21-28 Hz envelope, engaged < 16 km/h, by TRUE steering rate.")
print("=" * 118)
print("%12s | %s" % ('build', ' | '.join("%12s" % s for s in RATE_LBL)))
for t in TAGS:
    row = []
    for lbl in RATE_LBL:
        st = PRIM[t].get(lbl)
        row.append("%12s" % ('-' if st is None else "%.3f" % st['allband']))
    print("%12s | %s" % (NAMES[t], ' | '.join(row)))
print("  ⚠ sec 5.3's own table was band RMS on a 1/0.7996-corrected axis; this is the median")
print("     analytic envelope on `rate_f`.  The SHAPE across strata is the comparable part.")

# ================================================================= 3. C3 placebo
print()
print("=" * 118)
print("3.  C3 PLACEBO BAND 32-45 Hz, same detector, same strata -- drive card 4.4 makes this")
print("    correction MANDATORY on any cross-drive ratio in this corpus.")
print("    ⊕ It is ALSO a directed prediction: V105 costs 42 Hz a factor 1.75 (0.385 -> 0.680).")
print("=" * 118)
PRUNS = {t: per_run(t, PLACEBO, THR_P, THR_FRAC * THR_P) for t in TAGS}
print("%12s | %s" % ('build', ' | '.join("%12s" % s for s in RATE_LBL)))
PPRIM = {}
for t in TAGS:
    row, cells = [], {}
    for i, lbl in enumerate(RATE_LBL):
        st = strat_stats(PRUNS[t], RATE_EDGES[i], RATE_EDGES[i + 1])
        cells[lbl] = st
        row.append("%12s" % ('-' if st is None or not np.isfinite(st['inburst'])
                             else "%.3f" % st['inburst']))
    PPRIM[t] = cells
    print("%12s | %s" % (NAMES[t], ' | '.join(row)))
print()
print("%14s %14s %26s" % ('rate stratum', 'V105 / V104', '95 % CI (episode boot)'))
PLA = {}
for lbl in RATE_LBL:
    a, b = PPRIM['ra5'].get(lbl), PPRIM['ra4'].get(lbl)
    if a is None or b is None or not (np.isfinite(a['inburst']) and np.isfinite(b['inburst'])):
        print("%14s %14s %26s" % (lbl, '-', '-'))
        continue
    r = a['inburst'] / b['inburst']
    ci = boot_ratio(a['per'], b['per'], 'inburst')
    PLA[lbl] = dict(ratio=float(r), ci=ci)
    print("%14s %14.3f %26s" % (lbl, r, ("[%.3f, %.3f]" % ci) if ci else 'n/a'))
print()
print("  PLACEBO-CORRECTED PRIMARY = (21-28 ratio) / (32-45 ratio):")
for lbl in RATE_LBL:
    if lbl in RAT and lbl in PLA and PLA[lbl]['ratio'] > 0:
        print("     %-8s  %.3f / %.3f = **%.3f**" % (lbl, RAT[lbl]['ratio'], PLA[lbl]['ratio'],
                                                    RAT[lbl]['ratio'] / PLA[lbl]['ratio']))
OUT['placebo'] = PLA


# ================================================================= 4. NOTCH SHAPE
def spec_in(tag, engaged=True, vlo=VLO, vhi=VHI, chan='rate_f'):
    """Per-EPISODE summed Welch auto-spectra (4 s Hann, 50 % overlap, detrended)."""
    d, rs = run_slices(tag, engaged, vlo, vhi, minlen_s=4.2)
    x = d[chan].astype(float)
    per = []
    for a, b in rs:
        seg = x[a:b]
        acc, nw = None, 0
        for s in range(0, len(seg) - NPER + 1, NPER // 2):
            xs = seg[s:s + NPER]
            xs = xs - xs.mean()
            X = np.fft.rfft(xs * WIN)
            p = (X.conj() * X).real / (FS * UU)
            acc = p if acc is None else acc + p
            nw += 1
        if nw:
            per.append((acc, nw))
    return per


def pool(per):
    if not per:
        return None
    return sum(p[0] for p in per) / sum(p[1] for p in per)


def bandP(S, lo, hi):
    k = (FB >= lo) & (FB < hi)
    return float(S[k].sum() * DF)


def core_shoulder(S):
    c = bandP(S, *CORE)
    sh = sum(bandP(S, lo, hi) for lo, hi in SHOULDER)
    cw = CORE[1] - CORE[0]
    sw = sum(hi - lo for lo, hi in SHOULDER)
    return (c / cw) / (sh / sw)


print()
print("=" * 118)
print("4.  🛑 THE NOTCH-SHAPE TEST -- did 25.5 Hz move MORE than its own neighbours?")
print("    CORE %.1f-%.1f Hz  vs  SHOULDERS %s.  A working notch dents its own centre." %
      (CORE[0], CORE[1], ' + '.join("%.0f-%.0f" % s for s in SHOULDER)))
print("=" * 118)
SP = {}
for scope, vlo2, vhi2 in (('engaged <16 km/h', 0.0, 16.0), ('engaged 40-95 km/h', 40.0, 95.0)):
    print("\n  %s" % scope)
    print("%12s %8s %12s %12s %12s %16s"
          % ('build', 'episodes', 'CORE P', 'SHOULDER P', 'core/shldr', 'vs V104'))
    base = None
    for t in TAGS:
        per = spec_in(t, True, vlo2, vhi2)
        S = pool(per)
        if S is None or len(per) < 2:
            print("%12s %8d %12s" % (NAMES[t], len(per), '  -- too few 4 s windows --'))
            continue
        c = bandP(S, *CORE)
        sh = sum(bandP(S, lo, hi) for lo, hi in SHOULDER)
        cs = core_shoulder(S)
        SP[(scope, t)] = dict(per=per, S=S, core=c, sh=sh, cs=cs, nep=len(per))
        if t == 'ra4':
            base = cs
        print("%12s %8d %12.5f %12.5f %12.4f %16s"
              % (NAMES[t], len(per), c, sh, cs,
                 '-' if base is None or t == 'ra4' else "%.3f" % (cs / base)))
    # episode bootstrap on the a5/a4 core:shoulder contrast
    A, B = SP.get((scope, 'ra5')), SP.get((scope, 'ra4'))
    if A and B:
        rg = np.random.default_rng(23)
        vals = []
        for _ in range(4000):
            out2 = []
            for P in (A['per'], B['per']):
                pick = rg.integers(0, len(P), len(P))
                Sx = sum(P[j][0] for j in pick) / sum(P[j][1] for j in pick)
                out2.append(core_shoulder(Sx))
            vals.append(out2[0] / out2[1])
        lo3, hi3 = np.percentile(vals, [2.5, 97.5])
        pt = A['cs'] / B['cs']
        print("    ⇒ V105/V104 CORE:SHOULDER contrast = %.3f  [%.3f, %.3f]  (episode boot)"
              % (pt, lo3, hi3))
        print("      < 1 means 25.5 Hz fell MORE than its neighbours (a notch-shaped dent).")
        print("      ~ 1 means the band moved as a WHOLE, with no dent at the notch centre.")
        OUT.setdefault('notch_shape', {})[scope] = dict(point=float(pt), ci=[float(lo3),
                                                                            float(hi3)])

# fine-grain ratio curve
print()
print("  FINE-GRAIN V105/V104 POWER RATIO, engaged < 16 km/h, 0.25 Hz bins, 15-45 Hz:")
A, B = SP.get(('engaged <16 km/h', 'ra5')), SP.get(('engaged <16 km/h', 'ra4'))
if A and B:
    k = (FB >= 15.0) & (FB <= 45.0)
    r = A['S'][k] / B['S'][k]
    ff = FB[k]
    line = []
    for i in range(0, len(ff)):
        line.append("%5.2f:%6.3f" % (ff[i], r[i]))
    for i in range(0, len(line), 6):
        print("    " + "  ".join(line[i:i + 6]))
    OUT['fine_ratio'] = {'f': [float(x) for x in ff], 'r': [float(x) for x in r]}
    print("  🛑 V105's biquad |H| for reference: 20.0 0.589 · 21.7 0.415 · 24.0 0.160 ·")
    print("     24.9 0.062 · 25.5 2e-6 · 26.8 0.123 · 42.3 0.680, against V104's ~1.85 FLAT.")

# ================================================================= 5. the 427 lane itself
print()
print("=" * 118)
print("5.  THE NOTCH IN ITS OWN LANE -- CAN 427 carries |gp-0x6b86|, the biquad OUTPUT, on BOTH")
print("    routes with the SAME packer (`sar 4`, 3.2 counts/LSB).  This is the only channel that")
print("    sees the filter directly rather than through the closed loop.")
print("=" * 118)
print("  ⚠ TWO HARD LIMITS, stated before the numbers:")
print("     * the 0x1AB frame rate is ~50 Hz  =>  NYQUIST ~25 Hz.  **25.5 Hz IS ABOVE NYQUIST**")
print("       and cannot be observed directly; it aliases onto ~24.5 Hz.  Only the notch's")
print("       SKIRT (20-24 Hz, |H| 0.59 -> 0.16) is inside the observable band.")
print("     * the channel is RECTIFIED (|.|), a nonlinearity, so a true null gets partly filled.")
print("     ⇒ this leg can CONFIRM the filter is in force; it cannot refute it.")
LN = {}
for t in ('ra4', 'ra5'):
    d, rs = run_slices(t, True, 0.0, 95.0, minlen_s=4.2)
    x = d['x6b86_mag'].astype(float)
    acc, nw = None, 0
    for a, b in rs:
        seg = x[a:b]
        for s in range(0, len(seg) - NPER + 1, NPER // 2):
            xs = seg[s:s + NPER]
            xs = xs - xs.mean()
            X = np.fft.rfft(xs * WIN)
            p = (X.conj() * X).real / (FS * UU)
            acc = p if acc is None else acc + p
            nw += 1
    LN[t] = dict(S=acc / nw, nw=nw, med=float(np.median(x)),
                 p99=float(np.percentile(x, 99)), mx=float(x.max()))
BND = [(3, 8), (8, 13), (13, 18), (18, 21), (21, 24), (24, 24.9)]
print("\n%14s %14s %14s %14s %18s"
      % ('band Hz', 'V104 RMS', 'V105 RMS', 'V105/V104', 'predicted |H| ratio'))
PRED = {(3, 8): 0.9863 / 1.85, (8, 13): 0.90 / 1.85, (13, 18): 0.78 / 1.85,
        (18, 21): 0.589 / 1.85, (21, 24): 0.30 / 1.85, (24, 24.9): 0.11 / 1.85}
for lo2, hi2 in BND:
    a = np.sqrt(bandP(LN['ra5']['S'], lo2, hi2))
    b = np.sqrt(bandP(LN['ra4']['S'], lo2, hi2))
    print("%14s %14.4f %14.4f %14.4f %18.4f"
          % ("%g-%g" % (lo2, hi2), b, a, a / b, PRED[(lo2, hi2)]))
print("\n  |gp-0x6b86| counts:  V104 p50 %.1f p99 %.1f max %.1f   V105 p50 %.1f p99 %.1f max %.1f"
      % (LN['ra4']['med'], LN['ra4']['p99'], LN['ra4']['mx'],
         LN['ra5']['med'], LN['ra5']['p99'], LN['ra5']['mx']))
print("  windows: V104 %d   V105 %d" % (LN['ra4']['nw'], LN['ra5']['nw']))
OUT['lane427'] = {t: dict(med=LN[t]['med'], p99=LN[t]['p99'], mx=LN[t]['mx'], nw=LN[t]['nw'])
                  for t in LN}
OUT['lane427_bands'] = {("%g-%g" % b): dict(
    v104=float(np.sqrt(bandP(LN['ra4']['S'], *b))),
    v105=float(np.sqrt(bandP(LN['ra5']['S'], *b))),
    ratio=float(np.sqrt(bandP(LN['ra5']['S'], *b)) / np.sqrt(bandP(LN['ra4']['S'], *b))),
    predicted=PRED[b]) for b in BND}

# ================================================================= 6. the cave
print()
print("=" * 118)
print("6.  THE CAVE / PROBE TELEMETRY V105 CARRIED -- what the bits actually said.")
print("=" * 118)
print("  V105 budgeted ONE new rung: b6 = |gp-0x6b94| >= |gp-0x4f64|  (aggregator sum vs the")
print("  GOVERNOR BOUND).  Drive card: 'a live duty readout of the governor clamp, on the wire")
print("  for the first time'.  Secondary endpoint.  b7/b5/b4/b3 are V104's, carried.")
BITS = [('b7', 'sign gp-0x6b4c (LKAS cmd) -- NOT the 427 cell'),
        ('b6', '🆕 |gp-0x6b94| >= |gp-0x4f64|  GOVERNOR CLIP'),
        ('b5', '|gp-0x6ae2| >= |gp-0x6b26|  friction vs inertia'),
        ('b4', 'sign r24 (gp-0x6ada)'),
        ('b3', 'sign D_state (gp-0x3680)')]
CAVE = {}
for t, pfx in (('ra4', 'v104'), ('ra5', 'v105')):
    d = L.load(t)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    # drive card: DISCARD THE FIRST ~1 s OF EACH ENGAGED EPISODE when scoring b6
    idx = np.flatnonzero(np.diff(e.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(e)]))
    warm = np.zeros(len(e), bool)
    for i in range(len(b) - 1):
        if e[b[i]]:
            warm[b[i] + int(1.0 * FS):b[i + 1]] = True
    CAVE[t] = {}
    print("\n  %s" % NAMES[t])
    for nm, desc in BITS:
        x = d['%s_%s' % (pfx, nm)].astype(float) > 0.5
        CAVE[t][nm] = dict(all=float(x.mean()), eng=float(x[e].mean()),
                           man=float(x[~e].mean()),
                           eng_warm=float(x[e & warm].mean()),
                           eng_low=float(x[e & (v < 16)].mean()),
                           eng_hwy=float(x[e & (v >= 40)].mean()))
        C = CAVE[t][nm]
        flag = '  🛑 NEVER FIRED' if C['all'] == 0.0 else ('  🛑 RAILED ON' if C['all'] == 1.0
                                                          else '')
        print("    %-3s all %.4f  eng %.4f  manual %.4f  eng>1s %.4f  eng<16 %.4f  eng>=40 %.4f%s"
              % (nm, C['all'], C['eng'], C['man'], C['eng_warm'], C['eng_low'], C['eng_hwy'],
                 flag))
        print("        %s" % desc)
OUT['cave'] = CAVE

print()
print("=" * 118)
json.dump(OUT, open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                                 '_scratch/out/_ra5_prereg.json'), 'w'), indent=1, default=float)
print("wrote _scratch/out/_ra5_prereg.json")
