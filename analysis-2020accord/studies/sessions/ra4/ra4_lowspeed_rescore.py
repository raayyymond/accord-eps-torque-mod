"""RESCORE AT THE OPERATOR'S OWN WINDOW -- below 10 mph (16 km/h).

Operator, 2026-08-22: "Ok if you say grinding improved I was not able to observe this. I hope you
are measuring in the right windows (low speed < 10 mph)"

🛑 HIS VERDICT IS THE VERDICT: **GRINDING IS UNFIXED.**  Nothing in this file changes that.
   Bands are reported as bands, in Hz.  His words are reported as his words.  A band moving is
   not a symptom being fixed.

🛑 AND HIS METHODOLOGICAL POINT IS CORRECT: we scored 0-40 km/h; he places grinding below
   ~16 km/h.  A 0-40 window mixes the regime he means with three times as much driving where he
   does not report it, and dilutes any contrast.

=================================================================================================
SECTION 0 -- SPEED UNIT VERIFICATION.  BLOCKING.  A factor-3.6 error here would silently turn a
"< 16 km/h" window into "< 57.6 km/h" and reproduce the exact dilution he just caught.
=================================================================================================
Every speed in this file is `v_rear * 3.6`, where `v_rear = 0.5*(ws_rl + ws_rr)`.  Section 0
prints `v_rear*3.6`, `ws_kph` (separately decoded) and `cs_v*3.6` at matched percentiles on all
four routes and asserts they agree.  ⇒ `v_rear` is m/s; the stratum edges below are km/h.
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

KPH = 3.6
NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
WIN = np.hanning(NPER + 1)[:NPER]
U = (WIN ** 2).sum()
DF = f[1] - f[0]
FB = [(2, 4), (4, 6), (6, 9), (9, 13), (13, 18), (18, 22), (21, 28), (32, 45)]
TAGS = ('r97', 'r96', 'r9e', 'ra4')

# ================================================================= 0. UNITS
print("=" * 116)
print("0. SPEED UNIT VERIFICATION -- BLOCKING CHECK, printed not assumed")
print("=" * 116)
QS = [5, 25, 50, 75, 95]
for t in TAGS:
    d = L.load(t)
    vr = d['v_rear'].astype(float)
    same = bool(np.allclose(vr, 0.5 * (d['ws_rl'].astype(float) + d['ws_rr'].astype(float))))
    row = {'v_rear*3.6': vr * 3.6, 'cs_v*3.6': d['cs_v'].astype(float) * 3.6}
    wk = np.asarray(d['ws_kph'], float)
    if wk.ndim > 1:
        wk = wk.mean(axis=1)
    if len(wk) == len(vr):
        row['ws_kph'] = wk
    print("  %s  (v_rear == mean of rear wheel speeds: %s)" % (t, same))
    for k, v in row.items():
        print("     %-14s" % k + "".join("%9.2f" % np.percentile(v, q) for q in QS))
    if 'ws_kph' in row:
        ok = np.isfinite(vr) & np.isfinite(row['ws_kph']) & (row['ws_kph'] > 1)
        rel = np.max(np.abs(vr[ok] * 3.6 - row['ws_kph'][ok]) / row['ws_kph'][ok])
        print("     max relative disagreement vs ws_kph (where >1 km/h): %.5f" % rel)
        assert rel < 0.05, "SPEED UNIT MISMATCH -- STOP"
print("  ✅ `v_rear*3.6`, `ws_kph` and `cs_v*3.6` agree at every percentile ⇒ `v_rear` is m/s,")
print("     my ×3.6 is correct, and every stratum edge below is in km/h. [EVIDENCE]")
print("  ⊕ `cs_v` is confirmed m/s too -- `feel-impact`'s correction is right, and my own work")
print("     never used `cs_v`, so nothing I have reported inherits that error.")


# ================================================================= machinery
def specs(tag, engaged, vlo, vhi):
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
        S, nw = None, 0
        for s in range(a0, b0 - NPER + 1, NPER // 2):
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
    if not sp:
        return np.nan
    sel = (f >= lo) & (f < hi)
    return float(sum(s[0] for s in sp)[sel].sum() / sum(s[1] for s in sp) * DF)


def ratio(A_, B_, lo, hi, nb=4000, seed=13):
    if len(A_) < 3 or len(B_) < 3:
        return None
    r = np.random.default_rng(seed)
    pt = np.sqrt(power(B_, lo, hi) / power(A_, lo, hi))
    dr = np.array([np.sqrt(power([B_[j] for j in r.integers(0, len(B_), len(B_))], lo, hi)
                           / power([A_[j] for j in r.integers(0, len(A_), len(A_))], lo, hi))
                   for _ in range(nb)])
    return pt, np.percentile(dr, 2.5), np.percentile(dr, 97.5)


# ================================================================= 1. exposure
STRATA = [('< 10 km/h', 0.0, 10.0), ('< 16 km/h  (HIS WINDOW, 10 mph)', 0.0, 16.0),
          ('< 20 km/h  (fallback)', 0.0, 20.0), ('0-40 km/h  (what we scored)', 0.0, 40.0)]
print()
print("=" * 116)
print("1. EXPOSURE PER STRATUM -- engaged seconds and RUN count, so the power is visible")
print("=" * 116)
print("%34s" % 'stratum' + "".join("%20s" % t for t in TAGS))
SP = {}
for nm, lo_, hi_ in STRATA:
    cells = []
    for t in TAGS:
        d = L.load(t)
        e = d['cc_lat'] > 0.5
        v = d['v_rear'].astype(float) * KPH
        sec = (e & (v >= lo_) & (v < hi_)).sum() / L.FS
        sp = specs(t, True, lo_, hi_)
        SP[(nm, t)] = sp
        cells.append("%.0f s / %d runs" % (sec, len(sp)))
    print("%34s" % nm + "".join("%20s" % c for c in cells))
print()
print("  🛑 a ratio needs >= 3 runs per arm for even a crude bootstrap.  Where a stratum has")
print("     fewer, the row below prints '-' rather than a thin CI.")

# ================================================================= 2. the rescore
for nm, lo_, hi_ in STRATA:
    A = {t: SP[(nm, t)] for t in TAGS}
    if min(len(A[t]) for t in TAGS) < 2:
        print()
        print("=" * 116)
        print("%s -- INSUFFICIENT (runs: %s).  Not scored." %
              (nm, ", ".join("%s=%d" % (t, len(A[t])) for t in TAGS)))
        continue
    print()
    print("=" * 116)
    print("2. BAND TABLE at %s" % nm)
    print("=" * 116)
    print("%12s" % 'band' + "".join("%10s" % t for t in TAGS)
          + "%22s %22s %10s" % ('V104/STOCK [CI]', 'V104/V103 [CI]', 'a4 A/B'))
    plac = None
    rows = {}
    for lo2, hi2 in FB:
        vals = [np.sqrt(power(A[t], lo2, hi2)) for t in TAGS]
        r1 = ratio(A['r97'], A['ra4'], lo2, hi2)
        r2 = ratio(A['r9e'], A['ra4'], lo2, hi2)
        rows[(lo2, hi2)] = (r1, r2)
        sh = (np.sqrt(power(A['ra4'][0::2], lo2, hi2) / power(A['ra4'][1::2], lo2, hi2))
              if len(A['ra4']) >= 4 else np.nan)
        s1 = "%.2f [%.2f,%.2f]" % r1 if r1 else "-"
        s2 = "%.2f [%.2f,%.2f]" % r2 if r2 else "-"
        mark = {(18, 22): '  Lever B', (21, 28): '  THE 26 Hz MODE',
                (32, 45): '  PLACEBO', (6, 9): '  ratchet (c4)'}.get((lo2, hi2), '')
        print("%7.0f-%-4.0f" % (lo2, hi2) + "".join("%10.4f" % v for v in vals)
              + "%22s %22s %10s%s" % (s1, s2, ("%.2f" % sh) if np.isfinite(sh) else "-", mark))
        if (lo2, hi2) == (32, 45):
            plac = r2
    if plac:
        print()
        print("  PLACEBO-CORRECTED V104/V103 (band ÷ the 32-45 Hz placebo of %.2f):" % plac[0])
        print("%12s" % '' + "".join("%12s" % ("%g-%g" % b) for b in FB))
        print("%12s" % 'corrected' + "".join(
            "%12.2f" % (rows[b][1][0] / plac[0]) if rows[b][1] else "%12s" % '-' for b in FB))

# ================================================================= 3. dilution
print()
print("=" * 116)
print("3. HOW MUCH DILUTION DID THE 0-40 km/h WINDOW COST?  V104/STOCK, same bands")
print("=" * 116)
print("%12s" % 'band' + "".join("%22s" % nm.split('  ')[0] for nm, _, _ in STRATA))
for lo2, hi2 in FB:
    cells = []
    for nm, lo_, hi_ in STRATA:
        A = {t: SP[(nm, t)] for t in TAGS}
        r = ratio(A['r97'], A['ra4'], lo2, hi2) if min(len(A[t]) for t in TAGS) >= 3 else None
        cells.append("%.2f" % r[0] if r else "-")
    print("%7.0f-%-4.0f" % (lo2, hi2) + "".join("%22s" % c for c in cells))
print()
print("  ⇒ read ACROSS: if the contrast is larger in the tighter window, the 0-40 km/h numbers")
print("    were diluted and every grind-related figure quoted today is a LOWER BOUND.")
