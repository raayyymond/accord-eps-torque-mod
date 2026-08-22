"""REFINED BANDS -- the 26-40 Hz 'placebo' CONTAINED the mode, so it was never a placebo.

ra4_2640_wheelorder.py locates the peak at 26.0-26.8 Hz at EVERY speed (regression slope
-0.027 on a4, +0.055 on r97, R2 = 0.04, vs a wheel-order prediction of 0.962/1.442) => a FIXED
MODE, not a tyre order.  But it sits on the 26 Hz band EDGE, so the old 22-26 / 26-40 split cuts
straight through it and neither band is clean.

New split:  MODE 21-28 Hz (contains it)   ·   TRUE PLACEBO 32-45 Hz (above it, and below the
50.4 Hz Nyquist of the 0x18F channel).  c4's model is ~0.99 in both, so 32-45 is the honest
placebo for a same-gain V104 vs V103 comparison.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _gate2_boost_lib as L

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
WIN = np.hanning(NPER + 1)[:NPER]
U = (WIN ** 2).sum()
FB = [(6, 9), (13, 18), (18, 22), (21, 28), (32, 45)]
NAMES = {(6, 9): 'RATCHET (c4)', (13, 18): '', (18, 22): 'Lever B',
         (21, 28): 'THE MODE', (32, 45): 'TRUE PLACEBO'}


def ep(tag, engaged, vlo, vhi):
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    m = (e if engaged else ~e) & (v >= vlo) & (v < vhi)
    rate = d['rate_f'].astype(float)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    tt = np.arange(NPER); M = np.vstack([tt, np.ones(NPER)]).T
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


def rms(sp, lo, hi):
    if not sp:
        return np.nan
    sel = (f >= lo) & (f < hi)
    return float(np.sqrt(sum(s[0] for s in sp)[sel].sum() / sum(s[1] for s in sp) * (f[1] - f[0])))


def ratio(A_, B_, lo, hi, nb=4000, seed=13):
    if len(A_) < 2 or len(B_) < 2:
        return None
    r = np.random.default_rng(seed)
    pt = rms(B_, lo, hi) / rms(A_, lo, hi)
    d = np.array([rms([B_[j] for j in r.integers(0, len(B_), len(B_))], lo, hi)
                  / rms([A_[j] for j in r.integers(0, len(A_), len(A_))], lo, hi) for _ in range(nb)])
    return pt, np.percentile(d, 2.5), np.percentile(d, 97.5), len(B_), len(A_)


for nm, vlo, vhi in (('LOW 0-40 km/h', 0, 40), ('MID 40-80 km/h', 40, 80),
                     ('HIGH 80-130 km/h', 80, 130)):
    print("=" * 108)
    print("%s" % nm)
    print("=" * 108)
    SP = {t: ep(t, True, vlo, vhi) for t in ('ra4', 'r9e', 'r96', 'r97')}
    print("%14s %8s" % ('band', 'runs') + "".join("%11s" % t for t in ('r97', 'r96', 'r9e', 'ra4'))
          + "%22s %22s %10s" % ('V104/V103 [CI]', 'V104/STOCK [CI]', 'a4 split-half'))
    for lo, hi in FB:
        vals = [rms(SP[t], lo, hi) for t in ('r97', 'r96', 'r9e', 'ra4')]
        r1 = ratio(SP['r9e'], SP['ra4'], lo, hi)
        r2 = ratio(SP['r97'], SP['ra4'], lo, hi)
        sh = (rms(SP['ra4'][0::2], lo, hi) / rms(SP['ra4'][1::2], lo, hi)
              if len(SP['ra4']) >= 4 else np.nan)
        s1 = "%.3f [%.2f,%.2f]" % (r1[0], r1[1], r1[2]) if r1 else "-"
        s2 = "%.3f [%.2f,%.2f]" % (r2[0], r2[1], r2[2]) if r2 else "-"
        print("%8.0f-%-5.0f %8d" % (lo, hi, len(SP['ra4']))
              + "".join("%11.4f" % v for v in vals)
              + "%22s %22s %10.2f  %s" % (s1, s2, sh, NAMES[(lo, hi)]))
    print()
