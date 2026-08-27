r"""V105 / route `a5` -- ADJUDICATION.  The controls that decide whether studies/sessions/ra5/ra5_prereg_primary.py's
numbers are quotable, plus the absolute spectra behind the ratios.

Six questions, each of which can kill a headline:

A  ABSOLUTE SPECTRA, not ratios.  `studies/sessions/ra5/ra5_prereg_primary.py` found a fine-grain V105/V104 trough at
   ~23 Hz (0.044) and a RISE at the notch centre 25.5 Hz (2.23) in the < 16 km/h window.  A ratio
   cannot tell a "V105 removed something at 23 Hz" from a "V104 had a peak at 23 Hz that V105's
   mode sits beside".  Only the absolute spectra can.  Peak locations are reported per build.

B  SPLIT-HALF NULL **INSIDE THE HEADLINE STRATUM** (15-40 deg/s).  The pooled split-half null was
   1.654 (a5) / 0.478 (a4) -- both far from 1.00 -- but the pooled statistic mixes rate strata,
   so it is the wrong null for a stratified claim.  [`feedback-episodes-not-windows`]

C  WITHIN-STRATUM EXPOSURE MATCH.  A "15-40 deg/s" cell whose a5 half sits at 16 deg/s and whose
   a4 half sits at 38 deg/s is not a matched comparison.
   [`accord-averaged-spectrum-needs-matched-speed-distributions`]

D  PLACEBO-CORRECTED RATIO WITH A **JOINT** EPISODE BOOTSTRAP -- resampling both bands from the
   same resampled episodes, so the correction carries its own uncertainty instead of being a
   point estimate divided by a point estimate.

E  🛑 WHEEL ORDER AT THE HIGHWAY.  At 40-95 km/h (11.1-26.4 m/s) tyre order 2 (0.962*v) spans
   10.7-25.4 Hz and order 3 (1.442*v) spans 16.0-38.1 Hz -- **both sweep through 21-28 Hz**.
   The highway core:shoulder result is therefore exposed to a speed-mix artifact in a way the
   < 16 km/h result is not (there, order 3 tops out at 6.4 Hz).  A per-episode speed census and
   an order-frequency overlay are mandatory before that number is quoted.

F  THE CORPUS ORDERING -- where V105's headline cell sits against STOCK / V102 / V103 / V104,
   so the reader can see whether this is a build effect or a drive.
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
TAGS = ('r97', 'r96', 'r9e', 'ra4', 'ra5')
NAMES = {'r97': 'STOCK 1x', 'r96': 'V102 6x', 'r9e': 'V103 6x', 'ra4': 'V104 6x',
         'ra5': 'V105 NOTCH'}
NPER = int(round(4 * FS))
FB = np.fft.rfftfreq(NPER, 1 / FS)
WIN = np.hanning(NPER + 1)[:NPER]
UU = (WIN ** 2).sum()
DF = FB[1] - FB[0]
CORE = (24.5, 26.5)
SHOULDER = [(20.0, 23.0), (29.0, 33.0)]
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


def run_slices(tag, vlo, vhi, minlen_s=2.0, engaged=True):
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    m = (e if engaged else ~e) & (v >= vlo) & (v < vhi)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    ml = int(minlen_s * FS)
    return d, [(int(a), int(c)) for a, c in zip(b[:-1], b[1:])
               if m[a] and (c - a) >= ml]


def welch_per_ep(tag, vlo, vhi, chan='rate_f', ratelo=None, ratehi=None):
    """Per-EPISODE (Sxx, nwin), optionally restricted to a TRUE-deg/s rate stratum."""
    d, rs = run_slices(tag, vlo, vhi, minlen_s=4.2)
    x = d[chan].astype(float)
    rc = np.abs(d['rate_c'].astype(float))
    per = []
    for a, b in rs:
        seg, rseg = x[a:b], rc[a:b]
        acc, nw = None, 0
        for s in range(0, len(seg) - NPER + 1, NPER // 2):
            if ratelo is not None:
                r = rseg[s:s + NPER]
                if not (ratelo <= np.median(r) < ratehi):
                    continue
            xs = seg[s:s + NPER]
            xs = xs - xs.mean()
            X = np.fft.rfft(xs * WIN)
            acc = (X.conj() * X).real / (FS * UU) if acc is None \
                else acc + (X.conj() * X).real / (FS * UU)
            nw += 1
        if nw:
            per.append((acc, nw))
    return per


def pool(per):
    return None if not per else sum(p[0] for p in per) / sum(p[1] for p in per)


def bandP(S, lo, hi):
    k = (FB >= lo) & (FB < hi)
    return float(S[k].sum() * DF)


# ============================================================== A. ABSOLUTE SPECTRA
print("=" * 118)
print("A.  ABSOLUTE SPECTRA, NOT RATIOS -- 18-33 Hz, 0.25 Hz bins, engaged, per window.")
print("    A ratio of 0.04 at 23 Hz can mean 'V105 removed it' or 'V104 had a peak there'.")
print("=" * 118)
SPEC = {}
for scope, vlo, vhi in (('engaged < 16 km/h', 0.0, 16.0), ('engaged 40-95 km/h', 40.0, 95.0)):
    print("\n  %s" % scope)
    for t in TAGS:
        per = welch_per_ep(t, vlo, vhi)
        S = pool(per)
        if S is None:
            continue
        SPEC[(scope, t)] = (S, per)
    k = (FB >= 18.0) & (FB <= 33.0)
    ff = FB[k]
    hdr = "%7s" % 'Hz' + "".join("%11s" % NAMES[t] for t in TAGS if (scope, t) in SPEC)
    print("  " + hdr)
    for i in range(len(ff)):
        row = "%7.2f" % ff[i]
        for t in TAGS:
            if (scope, t) in SPEC:
                row += "%11.4f" % (SPEC[(scope, t)][0][k][i])
        print("  " + row)
    print("  PSD of `rate_f`, (deg/s)^2/Hz.  PEAK of each build in 18-33 Hz:")
    for t in TAGS:
        if (scope, t) not in SPEC:
            continue
        S = SPEC[(scope, t)][0][k]
        j = int(np.argmax(S))
        print("     %-11s peak %6.2f Hz  PSD %10.4f   band RMS 21-28 %8.4f  24.5-26.5 %8.4f"
              % (NAMES[t], ff[j], S[j], np.sqrt(bandP(SPEC[(scope, t)][0], 21, 28)),
                 np.sqrt(bandP(SPEC[(scope, t)][0], *CORE))))
    OUT.setdefault('peaks', {})[scope] = {
        NAMES[t]: dict(peak_hz=float(FB[k][int(np.argmax(SPEC[(scope, t)][0][k]))]),
                       rms_21_28=float(np.sqrt(bandP(SPEC[(scope, t)][0], 21, 28))),
                       rms_core=float(np.sqrt(bandP(SPEC[(scope, t)][0], *CORE))))
        for t in TAGS if (scope, t) in SPEC}

# ============================================================== B/C. stratum null + match
print()
print("=" * 118)
print("B/C.  THE HEADLINE STRATUM (15-40 deg/s, engaged < 16 km/h): WITHIN-STRATUM SPLIT-HALF")
print("      NULL and EXPOSURE MATCH.  Both must pass before 'V105/V104 = 0.343' is quotable.")
print("=" * 118)
d97, rs97 = run_slices('r97', 0.0, 16.0)
env97 = np.concatenate([bp_analytic(d97['rate_f'].astype(float)[a:b], *CARRIER) for a, b in rs97])
THR_ON = float(np.percentile(env97, 95))
p97 = np.concatenate([bp_analytic(d97['rate_f'].astype(float)[a:b], *PLACEBO) for a, b in rs97])
THR_P = float(np.percentile(p97, 95))


def stratum_runs(tag, band, thr, lo=15.0, hi=40.0, vlo=0.0, vhi=16.0):
    d, rs = run_slices(tag, vlo, vhi)
    rate_f = d['rate_f'].astype(float)
    rc = np.abs(d['rate_c'].astype(float))
    v = d['v_rear'].astype(float) * KPH
    per = []
    for a, b in rs:
        env = bp_analytic(rate_f[a:b], *band)
        on = np.zeros(len(env), bool)
        for s, e2 in bursts(env, thr, THR_FRAC * thr):
            on[s:e2] = True
        sel = (rc[a:b] >= lo) & (rc[a:b] < hi)
        if sel.sum() < int(0.25 * FS):
            continue
        per.append(dict(on_n=float((on & sel).sum()), sel_n=float(sel.sum()),
                        amps=env[on & sel], rc=rc[a:b][sel], v=v[a:b][sel]))
    return per


print("%12s %6s %8s | %8s %8s %8s | %8s %8s %8s"
      % ('build', 'runs', 'sec', 'rate p10', 'rate p50', 'rate p90', 'v p10', 'v p50', 'v p90'))
STR = {}
for t in TAGS:
    per = stratum_runs(t, CARRIER, THR_ON)
    if not per:
        continue
    rc = np.concatenate([p['rc'] for p in per])
    v = np.concatenate([p['v'] for p in per])
    STR[t] = per
    print("%12s %6d %8.1f | %8.1f %8.1f %8.1f | %8.2f %8.2f %8.2f"
          % (NAMES[t], len(per), len(rc) / FS,
             np.percentile(rc, 10), np.percentile(rc, 50), np.percentile(rc, 90),
             np.percentile(v, 10), np.percentile(v, 50), np.percentile(v, 90)))
    OUT.setdefault('stratum_census', {})[NAMES[t]] = dict(
        runs=len(per), sec=len(rc) / FS,
        rate=[float(np.percentile(rc, q)) for q in (10, 50, 90)],
        v=[float(np.percentile(v, q)) for q in (10, 50, 90)])

print()
print("  SPLIT-HALF NULL inside the stratum (runs ordered in time, ODD vs EVEN):")
print("%12s %10s %10s %14s" % ('build', 'half A', 'half B', 'A/B'))
for t in TAGS:
    if t not in STR:
        continue
    per = STR[t]
    if len(per) < 4:
        print("%12s %10s" % (NAMES[t], '< 4 runs -- no null available'))
        continue
    A = [p for i, p in enumerate(per) if i % 2 == 0]
    B = [p for i, p in enumerate(per) if i % 2 == 1]

    def med(pp):
        aa = [p['amps'] for p in pp if len(p['amps'])]
        return float(np.median(np.concatenate(aa))) if aa else np.nan
    a, b = med(A), med(B)
    print("%12s %10.3f %10.3f %14.3f" % (NAMES[t], a, b, a / b if b else np.nan))
    OUT.setdefault('stratum_splithalf', {})[NAMES[t]] = float(a / b) if b else None

# ============================================================== D. joint placebo bootstrap
print()
print("=" * 118)
print("D.  PLACEBO-CORRECTED PRIMARY, JOINT EPISODE BOOTSTRAP (both bands from the SAME")
print("    resampled episodes, so the correction carries its own uncertainty).")
print("=" * 118)
PSTR = {t: stratum_runs(t, PLACEBO, THR_P) for t in TAGS}


def joint_boot(tagA, tagB, nb=4000, seed=31):
    rg = np.random.default_rng(seed)
    # align episode lists by index -- stratum_runs uses the same run order for both bands
    A1, A2 = STR[tagA], PSTR[tagA]
    B1, B2 = STR[tagB], PSTR[tagB]
    if not (len(A1) == len(A2) and len(B1) == len(B2)):
        return None
    raw, cor, pla = [], [], []
    for _ in range(nb):
        pa = rg.integers(0, len(A1), len(A1))
        pb = rg.integers(0, len(B1), len(B1))

        def med(per, pick):
            aa = [per[j]['amps'] for j in pick if len(per[j]['amps'])]
            return np.median(np.concatenate(aa)) if aa else np.nan
        r1 = med(A1, pa) / med(B1, pb)
        r2 = med(A2, pa) / med(B2, pb)
        if np.isfinite(r1) and np.isfinite(r2) and r2 > 0:
            raw.append(r1)
            pla.append(r2)
            cor.append(r1 / r2)
    q = lambda z: (float(np.percentile(z, 2.5)), float(np.percentile(z, 97.5)))  # noqa: E731
    return dict(raw=q(raw), pla=q(pla), cor=q(cor),
                raw_pt=float(np.median(raw)), pla_pt=float(np.median(pla)),
                cor_pt=float(np.median(cor)))


J = joint_boot('ra5', 'ra4')
if J:
    print("  15-40 deg/s, engaged < 16 km/h, V105 / V104:")
    print("     21-28 Hz RAW        %.3f  [%.3f, %.3f]" % (J['raw_pt'], *J['raw']))
    print("     32-45 Hz PLACEBO    %.3f  [%.3f, %.3f]" % (J['pla_pt'], *J['pla']))
    print("     ⇒ CORRECTED         %.3f  [%.3f, %.3f]" % (J['cor_pt'], *J['cor']))
    print("     (bootstrap medians; the point estimates from the direct computation are")
    print("      0.343 raw / 0.734 placebo / 0.468 corrected)")
    OUT['joint_boot'] = J

# ============================================================== E. wheel order at highway
print()
print("=" * 118)
print("E.  🛑 WHEEL ORDER AT THE HIGHWAY -- the confound the < 16 km/h window does not have.")
print("=" * 118)
print("  order 2 = 0.962 * v(m/s) Hz,  order 3 = 1.442 * v(m/s) Hz  [`accord-v57-confirms-...`]")
print("%12s %8s | %8s %8s %8s | %14s %14s"
      % ('build', 'sec', 'v p10', 'v p50', 'v p90', 'ord2 p10-p90', 'ord3 p10-p90'))
for t in TAGS:
    d, rs = run_slices(t, 40.0, 95.0, minlen_s=4.2)
    if not rs:
        continue
    v = np.concatenate([(d['v_rear'].astype(float))[a:b] for a, b in rs])
    q = [np.percentile(v, x) for x in (10, 50, 90)]
    print("%12s %8.1f | %8.2f %8.2f %8.2f | %14s %14s"
          % (NAMES[t], len(v) / FS, q[0] * KPH, q[1] * KPH, q[2] * KPH,
             "%.1f-%.1f" % (0.962 * q[0], 0.962 * q[2]),
             "%.1f-%.1f" % (1.442 * q[0], 1.442 * q[2])))
    OUT.setdefault('hwy_census', {})[NAMES[t]] = dict(
        sec=len(v) / FS, v_kph=[float(x * KPH) for x in q],
        ord2=[float(0.962 * q[0]), float(0.962 * q[2])],
        ord3=[float(1.442 * q[0]), float(1.442 * q[2])])
print("  🛑 If ord2 or ord3 lands inside 24.5-26.5 Hz for one build and inside 20-23 / 29-33 for")
print("     another, the highway CORE:SHOULDER contrast is a SPEED artifact, not a notch.")

# ============================================================== E2. speed-matched highway
print()
print("  E2. SPEED-MATCHED HIGHWAY RE-RUN -- 55-70 km/h only, where a4 and a5 both have")
print("      exposure.  Orders 2/3 then span a NARROW, common range on both builds.")
print("%12s %8s %10s %12s %12s %12s"
      % ('build', 'episodes', 'sec', 'CORE P', 'SHOULDER P', 'core/shldr'))
HM = {}
for t in TAGS:
    per = welch_per_ep(t, 55.0, 70.0)
    S = pool(per)
    if S is None or len(per) < 2:
        print("%12s %8d %10s" % (NAMES[t], len(per), ' -- too few windows --'))
        continue
    d, rs = run_slices(t, 55.0, 70.0, minlen_s=4.2)
    sec = sum(b - a for a, b in rs) / FS
    c = bandP(S, *CORE)
    sh = sum(bandP(S, lo, hi) for lo, hi in SHOULDER)
    cw = CORE[1] - CORE[0]
    sw = sum(hi - lo for lo, hi in SHOULDER)
    HM[t] = dict(per=per, S=S, cs=(c / cw) / (sh / sw))
    print("%12s %8d %10.1f %12.4f %12.4f %12.4f" % (NAMES[t], len(per), sec, c, sh, HM[t]['cs']))
if 'ra5' in HM and 'ra4' in HM:
    def cs_of(S):
        c = bandP(S, *CORE)
        sh = sum(bandP(S, lo, hi) for lo, hi in SHOULDER)
        return (c / (CORE[1] - CORE[0])) / (sh / sum(hi - lo for lo, hi in SHOULDER))
    rg = np.random.default_rng(41)
    vals = []
    for _ in range(4000):
        o = []
        for P in (HM['ra5']['per'], HM['ra4']['per']):
            pick = rg.integers(0, len(P), len(P))
            o.append(cs_of(sum(P[j][0] for j in pick) / sum(P[j][1] for j in pick)))
        vals.append(o[0] / o[1])
    lo3, hi3 = np.percentile(vals, [2.5, 97.5])
    print("    ⇒ SPEED-MATCHED (55-70 km/h) V105/V104 CORE:SHOULDER = %.3f  [%.3f, %.3f]"
          % (HM['ra5']['cs'] / HM['ra4']['cs'], lo3, hi3))
    OUT['hwy_matched_core_shoulder'] = dict(
        point=float(HM['ra5']['cs'] / HM['ra4']['cs']), ci=[float(lo3), float(hi3)])
    k = (FB >= 18.0) & (FB <= 33.0)
    print("\n    fine-grain V105/V104 ratio, 55-70 km/h, 18-33 Hz:")
    ff, r = FB[k], HM['ra5']['S'][k] / HM['ra4']['S'][k]
    ln = ["%5.2f:%6.3f" % (ff[i], r[i]) for i in range(len(ff))]
    for i in range(0, len(ln), 6):
        print("      " + "  ".join(ln[i:i + 6]))
    OUT['hwy_matched_fine'] = {'f': [float(x) for x in ff], 'r': [float(x) for x in r]}

# ============================================================== F. corpus ordering
print()
print("=" * 118)
print("F.  THE CORPUS ORDERING -- headline cell (15-40 deg/s, engaged < 16 km/h), all builds.")
print("=" * 118)
print("%12s %10s %12s %12s %12s"
      % ('build', 'sec', '21-28 in-b', '32-45 in-b', 'ratio to STOCK'))
base = None
for t in TAGS:
    if t not in STR or t not in PSTR:
        continue

    def med(per):
        aa = [p['amps'] for p in per if len(p['amps'])]
        return float(np.median(np.concatenate(aa))) if aa else np.nan
    a, b = med(STR[t]), med(PSTR[t])
    sec = sum(p['sel_n'] for p in STR[t]) / FS
    if t == 'r97':
        base = a
    print("%12s %10.1f %12.3f %12.3f %12s"
          % (NAMES[t], sec, a, b, '-' if base is None else "%.1fx" % (a / base)))
    OUT.setdefault('corpus', {})[NAMES[t]] = dict(sec=sec, carrier=a, placebo=b)

json.dump(OUT, open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                                 '_scratch/out/_ra5_adjudicate.json'), 'w'), indent=1, default=float)
print("\nwrote _scratch/out/_ra5_adjudicate.json")
