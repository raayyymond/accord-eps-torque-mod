r"""🛑 THE BRANCH TEST -- IS `FUN_00036c12` IN THE MODE-RECORD LERP, OR IN A FIXED FALLBACK?

=================================================================================================
THE QUESTION (orchestrator's decompile of `FUN_00036c12`, program `code.bin`)
=================================================================================================
    if (gp-0x671a < 0xff) and (gp-0x67f4 == 1):
        if gp-0x671a < cal(0xC64FD)=5:  Y_eff = LERP(mode record)   <- what V107 would edit
        else:                           Y_eff = cal(0xC640A) = -8192  FIXED, records bypassed
    else:                               Y_eff = cal(0xC640C) = -3277  FIXED, records bypassed
If the car sits in a fallback at road speed, a schedule reshape buys NOTHING there.

=================================================================================================
⭐ THE KIT HAS ALREADY ANSWERED THIS ON THE WIRE, THREE TIMES, AND NOBODY CONNECTED IT
=================================================================================================
`gp-0x671a` is the **oscillation detector's output** (sole writer `0x42A12`), and it has been a
cave rung on three builds:
  * V64, route `35`: `0x14A` byte4 = **constant 0x87** over 14,980 frames -- bit7 liveness SET
    (so the cave WAS executing) while `gp-0x671a >= 5` and `gp-0x671a != 0` both read **0**.
  * V67: the same `>= 5` rung over **186,321 frames**.
  * V68, routes `4c`/`4e`: `gp-0x671a >= 1` fired **0 times in 53,991 frames**, including straight
    through the 1,468-count 28 Hz lane-change burst.
⇒ **~255,000 frames, four routes, three independent cave cuts: `gp-0x671a` has NEVER been observed
  non-zero.**  `0 < 5` and `0 < 0xff` ⇒ **the LERP branch is taken.**
⚠ THE CAVEAT IS IN THAT MEMORY'S OWN TITLE -- *"no positive control"*: the cell has never been
  non-zero, so "the detector never fires" cannot be separated from "the probe was blind".  V64's
  liveness bit argues against blindness but does not prove the rung's operand was right.
⚠ AND THE COVERAGE GAP THAT MATTERS HERE: route `35` was **all creep**.  Whether those routes
  covered ROAD SPEED is not recorded -- and road speed is exactly where V107 acts.
⇒ **This file is the independent test, and it is powered at road speed** (r77: 275 s at 40-70 and
  145 s at 70-90; r78: 100 s at >=90).

=================================================================================================
THE TESTS, WEAKEST IDENTIFICATION LAST
=================================================================================================
T1 ⭐ **THE DOSE RATIO -- the only test with clean identification.**  r77 (V90, x1.0) and r78 (V91,
   x1.5) differ ONLY in the mode-record Y.  Both fallbacks are stock-virgin on those builds.  So at
   MATCHED speed and MATCHED alpha:
        |b26|_r78 / |b26|_r77  =  [(1-f)*1.5*Y0(v) + f*F] / [(1-f)*1.0*Y0(v) + f*F]
   **1.50 if the LERP branch is live; 1.00 if the fallback is.**  It is evaluated INSIDE a speed
   band, so it cannot be confounded by anything that varies with speed -- including the fidelity of
   my alpha proxy, which cancels in the ratio.
T2  **THE SHAPE TEST.**  `|b26| / (alpha * Y_LERP(v))` is CONSTANT across speed under pure LERP and
   rises ~5x from 0 to 90 km/h under pure fallback.  ⚠ Confounded by any speed-dependence of the
   alpha proxy; descriptive only, and T1 is the control for it.
T3  **THE BIMODALITY TEST as commissioned.**  Run INSIDE `>=90 km/h` on r78, where `Y_LERP` is
   FLAT (2949) so a second cluster cannot be a speed effect.  Expected gap 8192/2949 = 2.78x.
   With a split-half-by-block null on the mixture fraction, per
   `feedback-run-the-control-before-the-measurement`.
C1 🛑 **SYNTHETIC CALIBRATION, RUN FIRST.**  Build |b26| from the MEASURED alpha at known fallback
   fractions f = 0, 0.10, 0.25, 0.50, 1.00 with the MEASURED residual spread, and push it through
   T1/T2/T3.  **If T3 cannot see a 25 % fallback, a null from T3 means nothing.**

Usage:  python studies/ra6/ra6_branch_test.py
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
CNT_PER_KPH = 64.0
Y_STOCK = np.array([-9830.0, -5734.0, -1966.0])
X_CNT = np.array([0.0, 1280.0, 5760.0])
FB2 = 8192.0                                   # cal 0xC640A -- the gp-0x671a >= 5 fallback
FB1 = 3277.0                                   # cal 0xC640C -- the outer fallback
DOSE = {'r77': 1.0, 'r78': 1.5}
WIRE = {'r77': 8.0 / 5.0, 'r78': 8.0 / 5.0}
VE = [0, 8, 16, 30, 50, 70, 90, 1e9]
VL = ['<8', '8-16', '16-30', '30-50', '50-70', '70-90', '>=90']
OUT = {}


def yl(v_kph, dose=1.0):
    return np.abs(np.interp(np.asarray(v_kph, float) * CNT_PER_KPH, X_CNT, Y_STOCK * dose))


def load(tag):
    d = L.load(tag)
    mt = np.asarray(d['ab_mt'], float)
    abt = np.asarray(d['ab_t1ab'], float)
    t = np.asarray(d['t'], float)
    j = np.clip(np.searchsorted(abt, t, side='right') - 1, 0, len(mt) - 1)
    b26 = mt[j] * WIRE[tag]
    e = np.asarray(d['cc_lat'], float) > 0.5
    v = (np.asarray(d['v_rear'], float) if 'v_rear' in d.files
         else 0.5 * (np.asarray(d['ws_rl'], float) + np.asarray(d['ws_rr'], float))) * KPH
    rf = np.asarray(d['rate_f'], float)
    k = int(round(0.05 * FS)) | 1
    a = np.convolve(np.abs(np.gradient(rf) * FS), np.ones(k) / k, mode='same')
    blk = (np.arange(len(t)) // int(30 * FS)).astype(int)
    return dict(b26=b26, e=e, v=v, a=a, blk=blk, tag=tag)


R = {t: load(t) for t in ('r77', 'r78')}
print("EXPECTED FALLBACK/LERP RATIO OF |Y_eff| BY SPEED (stock dose), i.e. the gap T3 must resolve:")
for i, s in enumerate(VL):
    vm = 0.5 * (VE[i] + min(VE[i + 1], 110))
    print("   %-7s v~%5.1f km/h   |Y_LERP| %7.0f   FB2/LERP %5.2fx   FB1/LERP %5.2fx"
          % (s, vm, yl(vm), FB2 / yl(vm), FB1 / yl(vm)))
    OUT.setdefault('expected_gap', {})[s] = dict(v_mid=float(vm), y_lerp=float(yl(vm)),
                                                 fb2_ratio=float(FB2 / yl(vm)),
                                                 fb1_ratio=float(FB1 / yl(vm)))

# =============================================================== C1 SYNTHETIC CALIBRATION
print()
print("=" * 124)
print("C1.  🛑 SYNTHETIC CALIBRATION, FIRST.  |b26| built from the MEASURED alpha with a KNOWN")
print("     fallback fraction and the MEASURED residual spread.  If a test cannot see f = 0.25,")
print("     a null from that test is worthless.")
print("=" * 124)
# fit the alpha -> c2c-proxy law on r77's LERP model, to get the residual spread
d7 = R['r77']
m7 = d7['e'] & (d7['b26'] > 0) & (d7['a'] > 0)
Y7 = yl(d7['v'], DOSE['r77'])
# under pure LERP, |b26| = C * Y * c2c(alpha); fit log|b26| - log Y = s*log a + c
lhs = np.log(d7['b26'][m7]) - np.log(Y7[m7])
sl, ic = np.polyfit(np.log(d7['a'][m7]), lhs, 1)
res = lhs - (sl * np.log(d7['a'][m7]) + ic)
print("  fitted on r77 under the PURE-LERP model:  log(|b26|/Y) = %.4f*log(alpha) %+.4f"
      "   residual sd %.3f (x%.2f)" % (sl, ic, res.std(), np.exp(res.std())))
OUT['lerp_fit'] = dict(slope=float(sl), intercept=float(ic), resid_sd=float(res.std()))
rgc = np.random.default_rng(2024)


def synth(tag, f):
    D = R[tag]
    Y = yl(D['v'], DOSE[tag])
    fb = rgc.random(len(Y)) < f
    Yeff = np.where(fb, FB2, Y)
    lg = sl * np.log(np.clip(D['a'], 1e-6, None)) + ic + rgc.choice(res, len(Y))
    return np.exp(lg) * Yeff, fb


def t1_ratio(b77, b78, band):
    """r78/r77 |b26| at matched (speed band, alpha decile).  Weighted geometric mean."""
    i = VL.index(band)
    out, wts = [], []
    A = R['r77']
    B = R['r78']
    ma = A['e'] & (A['v'] >= VE[i]) & (A['v'] < VE[i + 1]) & (b77 > 0)
    mb = B['e'] & (B['v'] >= VE[i]) & (B['v'] < VE[i + 1]) & (b78 > 0)
    if ma.sum() < 100 or mb.sum() < 100:
        return np.nan, 0
    q = np.quantile(np.concatenate([A['a'][ma], B['a'][mb]]), np.linspace(0.05, 0.95, 7))
    for j in range(len(q) - 1):
        sa = ma & (A['a'] >= q[j]) & (A['a'] < q[j + 1])
        sb = mb & (B['a'] >= q[j]) & (B['a'] < q[j + 1])
        if sa.sum() >= 30 and sb.sum() >= 30:
            out.append(np.log(np.median(b78[sb]) / np.median(b77[sa])))
            wts.append(min(sa.sum(), sb.sum()))
    if not out:
        return np.nan, 0
    return float(np.exp(np.average(out, weights=wts))), len(out)


print("\n  T1 (dose ratio, expected 1.50 at f=0 and 1.00 at f=1) on SYNTHETIC data:")
print("%10s" % 'f' + "".join("%12s" % s for s in VL))
for f in (0.0, 0.10, 0.25, 0.50, 1.00):
    b7s, _ = synth('r77', f)
    b8s, _ = synth('r78', f)
    row = [t1_ratio(b7s, b8s, s)[0] for s in VL]
    print("%10.2f" % f + "".join("     --     " if not np.isfinite(x) else "%12.3f" % x
                                 for x in row))
    OUT.setdefault('C1_T1', {})["f=%.2f" % f] = [float(x) for x in row]

print("\n  T3 (bimodality of log(|b26|/alpha) at >=90 km/h on r78) on SYNTHETIC data:")
print("%10s %10s %14s %14s" % ('f', 'n', 'dip (bimod?)', 'sd of log ratio'))
B = R['r78']
i90 = VL.index('>=90')
m90 = B['e'] & (B['v'] >= VE[i90]) & (B['a'] > 0)
for f in (0.0, 0.25, 0.50, 1.00):
    b8s, fb = synth('r78', f)
    x = np.log(b8s[m90 & (b8s > 0)] / B['a'][m90 & (b8s > 0)])
    h, _ = np.histogram(x, bins=40)
    # crude bimodality: is there a valley >= 20 % below both flanking maxima?
    pk = np.argmax(h)
    right = h[pk:]
    dip = 0.0
    if len(right) > 6:
        for j in range(2, len(right) - 2):
            if right[j] < 0.8 * right[:j].max() and right[j:].max() > 1.25 * right[j]:
                dip = max(dip, (right[:j].max() - right[j]) / max(right[:j].max(), 1))
    print("%10.2f %10d %14.3f %14.3f" % (f, int(m90.sum()), dip, x.std()))
    OUT.setdefault('C1_T3', {})["f=%.2f" % f] = dict(dip=float(dip), sd=float(x.std()))
print("  🛑 READ THIS BEFORE READING T3's REAL RESULT.")

# =============================================================== T1 REAL
print()
print("=" * 124)
print("T1.  ⭐⭐ THE DOSE RATIO ON REAL DATA -- r78/r77 |b26| at matched speed AND matched alpha.")
print("     **1.50 => the mode-record LERP is LIVE.  1.00 => the fallback is.**")
print("=" * 124)
print("%12s %10s %10s %12s %26s" % ('speed band', 'n r77', 'n r78', 'ratio', 'implied f [95 % CI]'))
b77r, b78r = R['r77']['b26'], R['r78']['b26']


def implied_f(ratio, v_mid, dose_lo=1.0, dose_hi=1.5):
    """Solve [(1-f)*dh*Y + f*F] / [(1-f)*dl*Y + f*F] = ratio for f."""
    Y = yl(v_mid)
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        r = ((1 - mid) * dose_hi * Y + mid * FB2) / ((1 - mid) * dose_lo * Y + mid * FB2)
        if r > ratio:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


for i, s in enumerate(VL):
    r, nc = t1_ratio(b77r, b78r, s)
    if not np.isfinite(r):
        continue
    ma = R['r77']['e'] & (R['r77']['v'] >= VE[i]) & (R['r77']['v'] < VE[i + 1])
    mb = R['r78']['e'] & (R['r78']['v'] >= VE[i]) & (R['r78']['v'] < VE[i + 1])
    vmid = 0.5 * (VE[i] + min(VE[i + 1], 110))
    rg = np.random.default_rng(600 + i)
    bs = []
    for _ in range(400):
        ba = R['r77']['blk']
        bb = R['r78']['blk']
        ua, ub = np.unique(ba[ma]), np.unique(bb[mb])
        ka = np.isin(ba, rg.choice(ua, len(ua)))
        kb = np.isin(bb, rg.choice(ub, len(ub)))
        bt = np.where(ka, b77r, 0.0)
        bt2 = np.where(kb, b78r, 0.0)
        rr, _ = t1_ratio(bt, bt2, s)
        if np.isfinite(rr):
            bs.append(implied_f(rr, vmid))
    q = np.percentile(bs, [2.5, 97.5]) if len(bs) > 40 else [np.nan] * 2
    print("%12s %10d %10d %12.3f %26s"
          % (s, int(ma.sum()), int(mb.sum()), r,
             "%.3f [%.3f, %.3f]" % (implied_f(r, vmid), q[0], q[1])))
    OUT.setdefault('T1_real', {})[s] = dict(n77=int(ma.sum()), n78=int(mb.sum()),
                                            ratio=float(r), cells=int(nc),
                                            f=float(implied_f(r, vmid)),
                                            f_ci=[float(q[0]), float(q[1])])

# =============================================================== T2
print()
print("=" * 124)
print("T2.  THE SHAPE TEST -- median |b26| / (alpha * Y_LERP(v)), normalised to the <8 km/h cell.")
print("     Pure LERP => FLAT across speed.  Pure fallback => rises ~5x by 90 km/h.")
print("     ⚠ Descriptive: confounded by any speed-dependence of the alpha proxy.  T1 is the control.")
print("=" * 124)
print("%6s" % 'route' + "".join("%12s" % s for s in VL) + "%16s" % 'pure-FB2 shape')
for tag in ('r77', 'r78'):
    D = R[tag]
    Y = yl(D['v'], DOSE[tag])
    val = []
    for i, s in enumerate(VL):
        m = D['e'] & (D['v'] >= VE[i]) & (D['v'] < VE[i + 1]) & (D['b26'] > 0) & (D['a'] > 0)
        val.append(float(np.median(D['b26'][m] / (D['a'][m] * Y[m]))) if m.sum() >= 100 else np.nan)
    v0 = val[0] if np.isfinite(val[0]) else np.nanmax(val)
    print("%6s" % tag + "".join("     --     " if not np.isfinite(x) else "%12.3f" % (x / v0)
                                for x in val)
          + "%16s" % ("%.2f at >=90" % (yl(5) / yl(100))))
    OUT.setdefault('T2_shape', {})[tag] = [float(x / v0) if np.isfinite(x) else None for x in val]
print("  (a pure-fallback world would show this row rising to %.2f by >=90 km/h)"
      % (yl(4.0) / yl(100.0)))

# =============================================================== T3
print()
print("=" * 124)
print("T3.  THE BIMODALITY TEST AS COMMISSIONED -- inside >=90 km/h on r78, where Y_LERP is FLAT")
print("     (2949), so a second cluster cannot be a speed effect.  Expected gap %.2fx."
      % (FB2 / yl(100.0, 1.5)))
print("=" * 124)
x = np.log(B['b26'][m90 & (B['b26'] > 0)] / B['a'][m90 & (B['b26'] > 0)])
print("  n = %d frames;  log-ratio sd %.3f;  expected cluster separation %.3f log units"
      % (len(x), x.std(), np.log(FB2 / yl(100.0, 1.5))))
qs = np.percentile(x, [5, 25, 50, 75, 95])
print("  percentiles of log(|b26|/alpha): " + "  ".join("%.2f" % q for q in qs))
h, edges = np.histogram(x, bins=30)
print("  histogram (30 bins over %.2f..%.2f):" % (edges[0], edges[-1]))
print("    " + " ".join("%d" % c for c in h))
OUT['T3'] = dict(n=int(len(x)), sd=float(x.std()),
                 expected_sep=float(np.log(FB2 / yl(100.0, 1.5))),
                 pct=[float(q) for q in qs], hist=[int(c) for c in h],
                 edges=[float(e) for e in edges])

# =============================================================== T4
print()
print("=" * 124)
print("T4.  CROSS-VALIDATION AGAINST THE MEASURED 1.68x DELIVERED MULTIPLIER (a6 vs a5).")
print("     A fallback fraction f dilutes an intended x2.0 step to:")
print("       [(1-f)*3.0*Y0 + f*8192] / [(1-f)*1.5*Y0 + f*8192]")
print("=" * 124)
print("%8s" % 'f' + "".join("%12s" % ("%s km/h" % s) for s in ('5', '20', '50', '90')))
for f in (0.0, 0.05, 0.10, 0.15, 0.25, 0.40):
    row = []
    for vv in (5, 20, 50, 90):
        Y0 = yl(vv)
        row.append(((1 - f) * 3.0 * Y0 + f * FB2) / ((1 - f) * 1.5 * Y0 + f * FB2))
    print("%8.2f" % f + "".join("%12.3f" % r for r in row))
    OUT.setdefault('T4_dilution', {})["f=%.2f" % f] = [float(r) for r in row]
print("  measured delivered multiplier a6 vs a5 = 1.68 [1.16, 1.88]")
print("  ⇒ read off which f reproduces it AT THE SPEEDS a6 ACTUALLY DROVE (top-heavy: 809 s of")
print("    1224 s engaged above 70 km/h).")

json.dump(OUT, open(os.path.join(ROOT, 'analysis-2020accord', '_scratch/out/_ra6_branch_test.json'), 'w'),
          indent=1, default=float)
print("\nwrote analysis-2020accord/_scratch/out/_ra6_branch_test.json")
