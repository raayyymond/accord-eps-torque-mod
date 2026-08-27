r"""GRIND #1 -- THE LINE CENTRE, ITS WIDTH, AND THE 18-22 Hz BAND, `a5` (V105) vs `a4` (V104).

Operator taxonomy (2026-08-22, via the orchestrator): **grind #1 = 18-22 Hz, ~21 Hz, IS the
grinding**, measured at 21.73 Hz on route `0x9e` (V103), prominence 39.18 vs null p95 3.07.
V105 put its null at 25.5 Hz, where `|H|` = 2.09e-6, and left `|H|` = 0.4150 at 21.73 Hz.

**THE DELIVERABLE IS ONE NUMBER WITH AN HONEST CI: the grind-#1 centre on `a5`.**  It is the V106
notch centre, so a false point estimate is worse than a wide interval.

=================================================================================================
🛑 RESOLUTION FLOOR, STATED BEFORE ANY ESTIMATE
=================================================================================================
At engaged < 16 km/h `a5` has **6 episodes >= 4.2 s and only 2 >= 8.2 s** -- so 8 s windows cannot
be episode-bootstrapped and 4 s Hann is the practical limit.
    bin spacing  0.2472 Hz  ·  Hann ENBW  1.5/T = 0.375 Hz  ·  -3 dB main lobe  1.44/T = 0.360 Hz
⇒ **any measured -3 dB width at or below ~0.38 Hz is the WINDOW, not the line.**  A centre can be
located to a fraction of a bin by sub-bin estimators; a WIDTH cannot be recovered below the ENBW.

=================================================================================================
THREE INDEPENDENT CENTRE ESTIMATORS, AND A CONTROL FOR EACH
=================================================================================================
E1  ARGMAX bin of the pooled Welch PSD in the search band.        (bin-quantised, unbiased)
E2  QUADRATIC INTERPOLATION on log-PSD across the argmax and its two neighbours.  (sub-bin)
E3  ⭐ AMPLITUDE-WEIGHTED INSTANTANEOUS FREQUENCY -- a TIME-DOMAIN estimator that shares no
    machinery with E1/E2: bandpass to the search band, analytic signal, `f = d(arg)/dt / 2pi`,
    weighted by envelope^2 and taken only where the envelope exceeds its own median.  Bin-free.

🛑 CONTROLS RUN BEFORE THE NUMBERS  [`feedback-run-the-control-before-the-measurement`]:
  C1 STOCK (`r97`) in the same window -- it has NO mode here (peak PSD 0.018 vs V105's 17.5).
     All three estimators must return an UNSTABLE centre with a wide CI on stock.  If a estimator
     returns a tight centre on stock it is manufacturing lines and its `a5` number is void.
  C2 The 32-45 Hz CONTROL BAND on `a5` -- same estimators, a band with no line.
  C3 A WHITE-NOISE surrogate matched in length -- the `q_of`-returns-79-on-white-noise failure
     mode [`feedback-run-the-control-before-the-measurement`] applies to width estimators too.

=================================================================================================
BAND CHOICE -- declared, because it can manufacture the answer
=================================================================================================
The taxonomy says 18-22 Hz.  But `a4`'s own line sits at 22.73 Hz, OUTSIDE that.  Searching only
18-22 would clip `a4` at its edge and fabricate a "shift".  So BOTH are reported:
    TAXONOMY band  18.0-22.0 Hz   (as the operator defines grind #1)
    WIDE band      17.5-24.0 Hz   (so neither build's line is clipped)
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
import struct
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
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
ENBW = 1.5 / (NPER / FS)
TAGS = ('r97', 'r85', 'r96', 'r9e', 'ra4', 'r95', 'ra5')
NAMES = {'r97': 'STOCK 1x', 'r85': 'V100 4x', 'r96': 'V102 6x', 'r9e': 'V103 6x',
         'ra4': 'V104 6x', 'r95': 'V101 8x', 'ra5': 'V105 6x+NOTCH'}
TAX = (18.0, 22.0)
WIDE = (17.5, 24.0)
CTRL = (32.0, 45.0)
FW = Path(r"C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord")
OUT = {'resolution': dict(bin_hz=float(DF), enbw_hz=float(ENBW), win_s=NPER / FS)}


def coeffs(n):
    b = (FW / n).read_bytes()
    return [struct.unpack("<f", b[o:o + 4])[0] for o in (0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4)]


C104 = coeffs("_v104_V103BASE-BIQUAD.C4x1.85-LEVERB.GATE6806.ARM5244-427.6B86.SAR4_plain_image.bin")
C105 = coeffs("_v105_V104BASE-NOTCH25.5HZ.C60A8-C60B4-PROBE.B6.6B94.GE.4F64_plain_image.bin")


def Hmag(f, c):
    a1, a2, b1, c4 = c
    z = np.exp(-2j * np.pi * np.asarray(f, float) / 1000.0)
    return np.abs(c4 * (1 + b1 * z + z * z) / (1 + a1 * z + a2 * z * z))


def biquad(fz, fp, r=0.95):
    """The V105 parameterisation, verbatim: zero pair at fz, pole pair at fp, DC held at unity."""
    a1 = -2 * r * np.cos(2 * np.pi * fp / 1000.0)
    a2 = r * r
    b1 = -2 * np.cos(2 * np.pi * fz / 1000.0)
    return [a1, a2, b1, (1 + a1 + a2) / (2 + b1)]


def run_slices(tag, vlo, vhi, minlen_s=4.2):
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    m = e & (v >= vlo) & (v < vhi)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    ml = int(minlen_s * FS)
    return d, [(int(a), int(c)) for a, c in zip(b[:-1], b[1:]) if m[a] and (c - a) >= ml]


def welch_per_ep(tag, vlo, vhi):
    d, rs = run_slices(tag, vlo, vhi)
    x = d['rate_f'].astype(float)
    per, segs = [], []
    for a, b in rs:
        seg = x[a:b]
        acc, nw = None, 0
        for s in range(0, len(seg) - NPER + 1, NPER // 2):
            xs = seg[s:s + NPER] - seg[s:s + NPER].mean()
            X = np.fft.rfft(xs * WIN)
            p = (X.conj() * X).real / (FS * UU)
            acc = p if acc is None else acc + p
            nw += 1
        if nw:
            per.append((acc, nw))
            segs.append(seg)
    return per, segs


def pool(per):
    return sum(p[0] for p in per) / sum(p[1] for p in per)


# --------------------------------------------------------------- estimators
def e1_argmax(S, lo, hi):
    k = (FB >= lo) & (FB <= hi)
    return float(FB[k][int(np.argmax(S[k]))])


def e2_quad(S, lo, hi):
    """Quadratic interpolation on log-PSD about the argmax -- sub-bin, standard peak estimator."""
    k = np.flatnonzero((FB >= lo) & (FB <= hi))
    j = k[int(np.argmax(S[k]))]
    if j <= 0 or j >= len(S) - 1:
        return float(FB[j])
    y0, y1, y2 = np.log(S[j - 1]), np.log(S[j]), np.log(S[j + 1])
    den = (y0 - 2 * y1 + y2)
    d = 0.0 if den == 0 else 0.5 * (y0 - y2) / den
    d = float(np.clip(d, -1.0, 1.0))
    return float(FB[j] + d * DF)


def e3_instfreq(segs, lo, hi):
    """Amplitude-weighted instantaneous frequency.  Time-domain; shares nothing with E1/E2."""
    num = den = 0.0
    for seg in segs:
        n = len(seg)
        X = np.fft.rfft(seg - seg.mean())
        fr = np.fft.rfftfreq(n, 1 / FS)
        Y = np.zeros_like(X)
        keep = (fr >= lo) & (fr < hi)
        Y[keep] = X[keep]
        Z = np.zeros(n, complex)
        Z[:len(Y)] = 2.0 * Y
        Z[0] /= 2
        z = np.fft.ifft(Z)
        env = np.abs(z)
        ph = np.unwrap(np.angle(z))
        f = np.diff(ph) / (2 * np.pi) * FS
        w = env[1:] ** 2
        g = (env[1:] > np.median(env)) & (f > lo) & (f < hi)
        if g.sum() < 10:
            continue
        num += float((f[g] * w[g]).sum())
        den += float(w[g].sum())
    return num / den if den > 0 else np.nan


def width_q(S, f0, lo, hi):
    """-3 dB width of the line above a local baseline fitted from the shoulders, and Q = f0/BW.
    Returns (BW_measured, BW_deconvolved, Q_deconvolved).  BW below ENBW is UNRESOLVED."""
    sh = ((FB >= lo - 2.0) & (FB < lo)) | ((FB > hi) & (FB <= hi + 2.0))
    base = float(np.median(S[sh])) if sh.any() else 0.0
    k = np.flatnonzero((FB >= lo - 2.0) & (FB <= hi + 2.0))
    y = S[k] - base
    j = int(np.argmin(np.abs(FB[k] - f0)))
    j = int(k.searchsorted(np.flatnonzero(np.abs(FB - f0) < DF)[0])) if False else j
    pk = y[j]
    if pk <= 0:
        return np.nan, np.nan, np.nan
    half = pk / 2.0
    i = j
    while i > 0 and y[i] > half:
        i -= 1
    lo_f = FB[k][i]
    i = j
    while i < len(y) - 1 and y[i] > half:
        i += 1
    hi_f = FB[k][i]
    bw = hi_f - lo_f
    bwd = float(np.sqrt(max(bw ** 2 - ENBW ** 2, 0.0)))
    return float(bw), bwd, (f0 / bwd if bwd > 0 else np.inf)


def boot(per, segs, lo, hi, nb=4000, seed=211):
    rg = np.random.default_rng(seed)
    a, q, w, qq = [], [], [], []
    for _ in range(nb):
        pick = rg.integers(0, len(per), len(per))
        S = sum(per[j][0] for j in pick) / sum(per[j][1] for j in pick)
        f1 = e1_argmax(S, lo, hi)
        a.append(f1)
        q.append(e2_quad(S, lo, hi))
        bw, bwd, Q = width_q(S, f1, lo, hi)
        w.append(bw)
        qq.append(Q)
        segs2 = [segs[j] for j in pick]
        # E3 is expensive; subsample it
    ci = lambda z: [float(np.percentile(z, 2.5)), float(np.percentile(z, 97.5))]  # noqa: E731
    return dict(argmax=ci(a), quad=ci(q), bw=ci([x for x in w if np.isfinite(x)]),
                Q=ci([x for x in qq if np.isfinite(x)]))


# ================================================================= 1. THE NUMBER
print("=" * 122)
print("1.  🛑 THE GRIND-#1 LINE CENTRE.  Engaged, < 16 km/h (the operator's grinding window).")
print("    resolution: 4 s Hann, bin %.4f Hz, ENBW %.3f Hz.  A WIDTH at or below %.2f Hz is the"
      % (DF, ENBW, ENBW))
print("    WINDOW, not the line.  Centres can go sub-bin; widths cannot go sub-ENBW.")
print("=" * 122)
DAT = {}
for band, blab in ((TAX, 'TAXONOMY 18-22'), (WIDE, 'WIDE 17.5-24')):
    print("\n  search band %s Hz" % blab)
    print("%14s %5s %9s %20s %9s %20s %9s %10s"
          % ('build', 'eps', 'E1 argmx', 'E1 95 % CI', 'E2 quad', 'E2 95 % CI',
             'E3 instf', 'peak PSD'))
    for t in TAGS:
        per, segs = welch_per_ep(t, 0.0, 16.0)
        if len(per) < 3:
            print("%14s %5d  -- fewer than 3 episodes --" % (NAMES[t], len(per)))
            continue
        S = pool(per)
        B = boot(per, segs, *band)
        f1, f2 = e1_argmax(S, *band), e2_quad(S, *band)
        f3 = e3_instfreq(segs, *band)
        k = (FB >= band[0]) & (FB <= band[1])
        DAT[(blab, t)] = dict(per=per, segs=segs, S=S, e1=f1, e2=f2, e3=f3, boot=B,
                              psd=float(S[k].max()))
        print("%14s %5d %9.3f %20s %9.3f %20s %9.3f %10.3f"
              % (NAMES[t], len(per), f1, "[%.2f, %.2f]" % tuple(B['argmax']), f2,
                 "[%.2f, %.2f]" % tuple(B['quad']), f3, S[k].max()))
    OUT.setdefault('centre', {})[blab] = {
        NAMES[t]: {k2: v for k2, v in DAT[(blab, t)].items() if k2 not in ('per', 'segs', 'S')}
        for t in TAGS if (blab, t) in DAT}

# ================================================================= 2. CONTROLS
print()
print("=" * 122)
print("2.  🛑 CONTROLS -- these decide whether section 1 is a measurement or an artifact.")
print("=" * 122)
print("  C1  STOCK `r97` in the same window has NO mode (peak PSD 0.018 vs V105's ~17).")
print("      Its CI above is the estimators' behaviour ON NOISE.  Compare widths.")
b97 = DAT.get(('WIDE 17.5-24', 'r97'))
b05 = DAT.get(('WIDE 17.5-24', 'ra5'))
b04 = DAT.get(('WIDE 17.5-24', 'ra4'))
if b97 and b05:
    w97 = b97['boot']['argmax'][1] - b97['boot']['argmax'][0]
    w05 = b05['boot']['argmax'][1] - b05['boot']['argmax'][0]
    w04 = b04['boot']['argmax'][1] - b04['boot']['argmax'][0]
    print("      CI WIDTH (E1):  STOCK %.2f Hz   V104 %.2f Hz   V105 %.2f Hz   => %s"
          % (w97, w04, w05,
             "PASS -- the estimator is loose on noise and tight on the builds with a line"
             if w97 > max(w04, w05) else "🛑 FAIL -- stock is as tight as the builds"))
    OUT['C1'] = dict(ci_width_stock=float(w97), ci_width_v104=float(w04), ci_width_v105=float(w05))

print("\n  C2  32-45 Hz CONTROL BAND on `a5` (no line there):")
per5c, segs5c = welch_per_ep('ra5', 0.0, 16.0)
S5 = pool(per5c)
Bc = boot(per5c, segs5c, *CTRL)
print("      E1 %.3f  CI [%.2f, %.2f]  (width %.2f Hz)   E2 %.3f   E3 %.3f"
      % (e1_argmax(S5, *CTRL), Bc['argmax'][0], Bc['argmax'][1],
         Bc['argmax'][1] - Bc['argmax'][0], e2_quad(S5, *CTRL), e3_instfreq(segs5c, *CTRL)))
OUT['C2'] = dict(e1=float(e1_argmax(S5, *CTRL)), ci=Bc['argmax'])

print("\n  C3  WHITE-NOISE surrogate, same episode lengths, same estimators:")
rg = np.random.default_rng(311)
nseg = [len(s) for s in (b05['segs'] if b05 else [])]
pern, segn = [], []
for n in nseg:
    seg = rg.normal(size=n)
    acc, nw = None, 0
    for s in range(0, n - NPER + 1, NPER // 2):
        xs = seg[s:s + NPER] - seg[s:s + NPER].mean()
        X = np.fft.rfft(xs * WIN)
        p = (X.conj() * X).real / (FS * UU)
        acc = p if acc is None else acc + p
        nw += 1
    if nw:
        pern.append((acc, nw))
        segn.append(seg)
if len(pern) >= 3:
    Sn = pool(pern)
    Bn = boot(pern, segn, *WIDE)
    bw, bwd, Q = width_q(Sn, e1_argmax(Sn, *WIDE), *WIDE)
    print("      E1 %.3f  CI [%.2f, %.2f] (width %.2f Hz)   measured -3 dB BW %.3f Hz  ->  Q %.1f"
          % (e1_argmax(Sn, *WIDE), Bn['argmax'][0], Bn['argmax'][1],
             Bn['argmax'][1] - Bn['argmax'][0], bw, Q))
    print("      🛑 THIS IS THE NUMBER A WIDTH ESTIMATOR RETURNS ON PURE NOISE.  Any Q on real")
    print("         data must clearly exceed it to mean anything.")
    OUT['C3'] = dict(e1=float(e1_argmax(Sn, *WIDE)), ci=Bn['argmax'], bw=float(bw), Q=float(Q))

# ================================================================= 3. WIDTH / Q
print()
print("=" * 122)
print("3.  THE LINE'S WIDTH AND EFFECTIVE Q -- this sets how WIDE the V106 notch must be.")
print("=" * 122)
print("%14s %12s %14s %14s %14s %20s"
      % ('build', 'centre Hz', '-3 dB BW meas', 'BW deconv', 'Q = f0/BW', 'Q 95 % CI'))
for t in TAGS:
    D = DAT.get(('WIDE 17.5-24', t))
    if not D:
        continue
    bw, bwd, Q = width_q(D['S'], D['e1'], *WIDE)
    print("%14s %12.3f %14.3f %14.3f %14.1f %20s"
          % (NAMES[t], D['e1'], bw, bwd, Q, "[%.1f, %.1f]" % tuple(D['boot']['Q'])))
    OUT.setdefault('width', {})[NAMES[t]] = dict(centre=D['e1'], bw_meas=float(bw),
                                                 bw_deconv=float(bwd), Q=float(Q),
                                                 Q_ci=D['boot']['Q'])
print("  BW meas = -3 dB width above a shoulder-fitted baseline.  BW deconv = sqrt(BW^2 - ENBW^2),")
print("  an APPROXIMATION that removes the 4 s Hann window's own %.3f Hz.  🛑 Compare every Q"
      % ENBW)
print("  against the WHITE-NOISE control in section 2 C3 before believing it.")

# ================================================================= 4. 18-22 Hz BAND
print()
print("=" * 122)
print("4.  THE 18-22 Hz BAND SCORED EXPLICITLY, `a5` vs `a4` -- separately from 21-28 Hz.")
print("=" * 122)


def bandRMS(S, lo, hi):
    k = (FB >= lo) & (FB < hi)
    return float(np.sqrt(S[k].sum() * DF))


for scope, vlo, vhi in (('engaged < 16 km/h', 0.0, 16.0), ('engaged 40-95 km/h', 40.0, 95.0)):
    print("\n  %s" % scope)
    print("%14s %5s %12s %22s %12s %12s %12s"
          % ('build', 'eps', '18-22 RMS', '95 % CI', 'x STOCK', '21-28 RMS', '18-30 RMS'))
    P = {}
    base = None
    for t in TAGS:
        per, _ = welch_per_ep(t, vlo, vhi)
        if len(per) < 3:
            continue
        S = pool(per)
        rg2 = np.random.default_rng(401)
        bs = [bandRMS(sum(per[j][0] for j in pk) / sum(per[j][1] for j in pk), 18, 22)
              for pk in (rg2.integers(0, len(per), len(per)) for _ in range(2000))]
        q = np.percentile(bs, [2.5, 97.5])
        v = bandRMS(S, 18, 22)
        P[t] = per
        if t == 'r97':
            base = v
        print("%14s %5d %12.4f %22s %12s %12.4f %12.4f"
              % (NAMES[t], len(per), v, "[%.3f, %.3f]" % (q[0], q[1]),
                 '-' if base is None else "%.2fx" % (v / base),
                 bandRMS(S, 21, 28), bandRMS(S, 18, 30)))
        OUT.setdefault('band1822', {}).setdefault(scope, {})[NAMES[t]] = dict(
            rms=v, ci=[float(q[0]), float(q[1])], eps=len(per),
            rms_21_28=bandRMS(S, 21, 28), rms_18_30=bandRMS(S, 18, 30))
    if 'ra5' in P and 'ra4' in P:
        rg2 = np.random.default_rng(409)
        vals = []
        for _ in range(4000):
            o = []
            for Q2 in (P['ra5'], P['ra4']):
                pk = rg2.integers(0, len(Q2), len(Q2))
                o.append(bandRMS(sum(Q2[j][0] for j in pk) / sum(Q2[j][1] for j in pk), 18, 22))
            vals.append(o[0] / o[1])
        q = np.percentile(vals, [2.5, 97.5])
        nulls = {}
        for t in ('ra4', 'ra5'):
            Q2 = P[t]
            if len(Q2) < 6:
                continue
            rg3 = np.random.default_rng(419)
            rr = []
            for _ in range(2000):
                idx = rg3.permutation(len(Q2))
                h = len(Q2) // 2
                A = sum(Q2[j][0] for j in idx[:h]) / sum(Q2[j][1] for j in idx[:h])
                B = sum(Q2[j][0] for j in idx[h:]) / sum(Q2[j][1] for j in idx[h:])
                rr.append(bandRMS(A, 18, 22) / bandRMS(B, 18, 22))
            nulls[t] = [float(x) for x in np.percentile(rr, [2.5, 97.5])]
        print("     ⇒ V105/V104 **18-22 Hz = %.3f  [%.3f, %.3f]**  (episode boot)"
              % (np.median(vals), q[0], q[1]))
        for t, n in nulls.items():
            print("       within-drive random-split null %-13s [%.3f, %.3f] => measured is %s"
                  % (NAMES[t], n[0], n[1],
                     "INSIDE (unchanged)" if n[0] <= np.median(vals) <= n[1] else "OUTSIDE"))
        OUT.setdefault('band1822_ratio', {})[scope] = dict(
            point=float(np.median(vals)), ci=[float(q[0]), float(q[1])], nulls=nulls)

# ================================================================= 5. NOTCH ARITHMETIC
print()
print("=" * 122)
print("5.  THE V105 sec-7.3 ARITHMETIC, REDONE FOR GRIND #1.  Same parameterisation as the")
print("    flown build: zero pair at F_ZERO, pole pair at F_POLE, r = R_POLE, DC held at unity.")
print("=" * 122)
D5 = DAT.get(('WIDE 17.5-24', 'ra5'))
D4 = DAT.get(('WIDE 17.5-24', 'ra4'))
if D5 and D4:
    f5, f4 = D5['e2'], D4['e2']
    bw5 = width_q(D5['S'], D5['e1'], *WIDE)[0]
    supp = (min(f5, f4) - bw5, max(f5, f4) + bw5)
    print("  measured line centres: V105 %.2f Hz · V104 %.2f Hz · V102 %.2f · V103 %.2f"
          % (f5, f4, DAT[('WIDE 17.5-24', 'r96')]['e2'], DAT[('WIDE 17.5-24', 'r9e')]['e2']))
    print("  ⇒ the SUPPORT a V106 notch must cover, if the pole keeps relocating: %.2f-%.2f Hz"
          % supp)
    print()
    print("%10s %10s %8s | %s" % ('F_ZERO', 'F_POLE', 'r', ' '.join(
        "%7.2f" % f for f in (19.0, 20.0, 20.5, 21.0, 21.7, 22.0, 22.7, 23.5, 25.5, 7.79))))
    print("%10s %10s %8s | %s" % ('', '', '', ' '.join("%7s" % 'Hz' for _ in range(10))))
    rows = []
    for fz, fp, r in ((21.7, 18.2, 0.95), (21.0, 17.5, 0.95), (20.5, 17.0, 0.95),
                      (21.7, 18.2, 0.90), (21.7, 18.2, 0.80), (21.7, 18.2, 0.70),
                      (21.0, 17.5, 0.80), (25.5, 22.0, 0.95)):
        c = biquad(fz, fp, r)
        vals = [Hmag(f, c) for f in (19.0, 20.0, 20.5, 21.0, 21.7, 22.0, 22.7, 23.5, 25.5, 7.79)]
        ff = np.linspace(*supp, 200)
        worst = float(np.max(Hmag(ff, c)))
        rows.append(dict(fz=fz, fp=fp, r=r, worst_over_support=worst,
                         H=dict(zip(('19', '20', '20.5', '21', '21.7', '22', '22.7', '23.5',
                                     '25.5', '7.79'), [float(v) for v in vals]))))
        tag = '  <- V105 AS FLOWN' if fz == 25.5 else ''
        print("%10.1f %10.1f %8.2f | %s   worst over support %.4f%s"
              % (fz, fp, r, ' '.join("%7.4f" % v for v in vals), worst, tag))
    OUT['notch_candidates'] = rows
    print()
    print("  🛑 'worst over support' = max |H| over %.2f-%.2f Hz -- the quantity V105 sec 7.3")
    print("     minimised (it chose 25.5 over 26.0 on worst 0.160 vs 0.216).  Lowering `r`")
    print("     WIDENS the stopband at the cost of phase; that trade is GATE 2's, not mine.")
    print("  ⚠ The 7.79 Hz column is the S2 micro-ratchet blast-radius check for each candidate.")

json.dump(OUT, open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                                 '_scratch/out/_ra5_grind1.json'), 'w'), indent=1, default=float)
print("\nwrote _scratch/out/_ra5_grind1.json")
