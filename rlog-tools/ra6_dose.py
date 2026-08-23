r"""ROUTE `a6` == V106 -- Q1 (DID THE DOSE ARRIVE, AND HOW BIG WAS IT) AND Q2' (THE CLAMP).

=================================================================================================
🛑 THE INSTRUMENT, AND WHAT IT CAN AND CANNOT SEE
=================================================================================================
`gp-0x6b26` is **NOT on the 427 wire on route a6.**  V104/V105/V106 all point the 427 tap at
`gp-0x6b86` (the biquad lane).  The cell was on the wire only on **r77 (V90, x1.00 stock)**,
**r78 (V91, x1.50)** and **r7d (V94, x0.25)**.
⇒ **NO DIRECT MEASUREMENT OF |gp-0x6b26| EXISTS ON a6.  Any clamp duty for a6 is a
   RECONSTRUCTION and is labelled as one.**

What a6 DOES carry is the cave rung
        `b5` = ( |gp-0x6ae2|  >=  |gp-0x6b26| )        FRICTION  vs  INERTIA
whose **operand B is the exact cell V106 triples** and whose operand A is untouched by V106.

=================================================================================================
⭐ WHY A POOLED `b5` DUTY IS THE WRONG ESTIMATOR, AND WHAT REPLACES IT
=================================================================================================
`eps_chain_lanes.py` states the trap explicitly:
    "gp-0x6b26 = K*alpha where alpha is what K damps, so IN A STABLE CLOSED LOOP THE PRODUCT IS
     INVARIANT TO K (V91/V92's x1.5 measured 0.99).  Measure the INPUT or a symptom -- never the
     product."
A pooled `b5` duty reads exactly that product, so a NULL on it is **ambiguous** -- it is equally
consistent with "the dose never arrived" and with "the dose arrived and killed the acceleration
that produced it."  **That ambiguity is the whole reason this file conditions on measured alpha.**

⭐ **CONDITION ON THE MEASURED ACCELERATION.**  At a FIXED alpha the comparator's operand B is
`K(v) * k * c2c(alpha)`, which IS proportional to k.  So the **duty-vs-alpha curve shifts
horizontally by exactly the delivered multiplier**, and the shift is immune to the closed-loop
invariance.  The estimator is `alpha_p` = the alpha at which `b5` duty crosses a fixed level p:
        delivered multiplier  =  alpha_p(a5) / alpha_p(a6)          (expected 2.0 if x1.5 -> x3.0)
Both curves are measured INSIDE their own drive, on their own alpha axis.

🛑 CONTROL BEFORE MEASUREMENT: the alpha proxy is validated on **r77**, where BOTH the proxy and
the true |gp-0x6b26| are on the wire, before it is used anywhere.

=================================================================================================
Q2' -- THE CLAMP, AND THE V80 RELAY LESSON
=================================================================================================
`FUN_00036c12` clamps `gp-0x6b26` to +-511 (`0xC407E`).  V80's postmortem
(`accord-v80-damper-relay-and-grind1-inert`): **"does not clip" and "is not a relay" are different
statements** -- V80's supremum equalled the ceiling exactly and clipped 0.00 %.
So this file runs TWO tests, not one:
  (A) RECONSTRUCTED clamp duty on a6 (r77-calibrated), by rate bin and speed regime;
  (B) ⭐ a **DIRECT, ASSUMPTION-FREE RELAY TEST from `b5` itself**: if `|gp-0x6b26|` were railing,
      then above the railing alpha `b5` would become `( |gp-0x6ae2| >= 511 )` -- a quantity with NO
      alpha dependence -- so the duty-vs-alpha curve would go FLAT.  A curve still falling at the
      top of the observed alpha range is evidence the term is NOT saturating there, and it needs no
      cross-route transfer at all.

Usage:  python ra6_dose.py
"""
import os
import sys
import json

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "analysis-2020accord"))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
FS = L.FS
CLAMP = 511.0
B5KEY = {'ra4': 'v104_b5', 'ra5': 'v105_b5', 'ra6': 'v106_b5'}
NAMES = {'ra4': 'V104 (x1.5)', 'ra5': 'V105 (x1.5)', 'ra6': 'V106 (x3.0)'}
WIRE_SCALE_B26 = {'r77': 8.0 / 5.0, 'r78': 8.0 / 5.0}
DOSE_VS_STOCK = {'r77': 1.00, 'r78': 1.50}
OUT = {}


def base(tag):
    d = L.load(tag)
    e = np.asarray(d['cc_lat'], float) > 0.5
    v = (np.asarray(d['v_rear'], float) if 'v_rear' in d.files
         else 0.5 * (np.asarray(d['ws_rl'], float) + np.asarray(d['ws_rr'], float))) * KPH
    rc = np.abs(np.asarray(d['rate_c'], float))
    tq = np.abs(np.asarray(d['tq'], float))
    return d, e, v, rc, tq


def alpha_proxy(d):
    """Two candidate proxies for |gp-0x6c2c| (the FILTERED MOTOR-RATE FIRST DIFFERENCE).

    p1 = |d(rate_f)/dt|, boxcar-smoothed 50 ms  -- the literal first difference, aliased.
    p2 = local RMS of a 15-35 Hz band-passed rate_f, times 2*pi*f_c -- band-limited acceleration,
         which is what an oscillation at the mode's own frequency actually delivers.
    🛑 Which one is used is decided by the r77 CONTROL below, not by preference."""
    rf = np.asarray(d['rate_f'], float)
    p1 = np.abs(np.gradient(rf) * FS)
    k = int(round(0.05 * FS)) | 1
    p1 = np.convolve(p1, np.ones(k) / k, mode='same')
    n = len(rf)
    X = np.fft.rfft(rf - rf.mean())
    f = np.fft.rfftfreq(n, 1 / FS)
    X[(f < 15.0) | (f > 35.0)] = 0
    bp = np.fft.irfft(X, n=n)
    env = np.convolve(np.abs(bp), np.ones(k) / k, mode='same') * np.sqrt(np.pi / 2)
    p2 = env * 2 * np.pi * 22.0
    return p1, p2


def b26_wire(tag):
    d = L.load(tag)
    mt = np.asarray(d['ab_mt'], float)
    abt = np.asarray(d['ab_t1ab'], float)
    t = np.asarray(d['t'], float)
    j = np.clip(np.searchsorted(abt, t, side='right') - 1, 0, len(mt) - 1)
    return mt[j] * WIRE_SCALE_B26[tag]


# ================================================================ 0. THE CONTROL
print("=" * 124)
print("0.  🛑 CONTROL FIRST -- VALIDATE THE ALPHA PROXY ON r77, WHERE |gp-0x6b26| IS ON THE WIRE.")
print("    An alpha proxy that does not predict the real cell is not allowed to calibrate a dose.")
print("=" * 124)
print("%8s %8s %10s %28s %28s"
      % ('route', 'dose', 'engaged s', 'corr(log|b26|, log p1)', 'corr(log|b26|, log p2)'))
CTRL = {}
for tag in ('r77', 'r78'):
    d, e, v, rc, tq = base(tag)
    b26 = b26_wire(tag)
    p1, p2 = alpha_proxy(d)
    m = e & (b26 > 0) & (p1 > 0) & (p2 > 0)
    lb = np.log(b26[m])
    c1 = float(np.corrcoef(lb, np.log(p1[m]))[0, 1])
    c2 = float(np.corrcoef(lb, np.log(p2[m]))[0, 1])
    CTRL[tag] = dict(corr_p1=c1, corr_p2=c2, n=int(m.sum()), sec=float(e.sum() / FS))
    print("%8s %8.2f %10.1f %28.4f %28.4f"
          % (tag, DOSE_VS_STOCK[tag], e.sum() / FS, c1, c2))
USE_P2 = np.mean([CTRL[t]['corr_p2'] for t in CTRL]) >= np.mean([CTRL[t]['corr_p1'] for t in CTRL])
print("  ⇒ using proxy **p%d** (the one that predicts the real cell better on BOTH control routes)"
      % (2 if USE_P2 else 1))
OUT['alpha_control'] = dict(CTRL, chosen='p2' if USE_P2 else 'p1')

# the alpha -> b26 calibration on r77 (dose x1.00 stock), used ONLY for the reconstruction in 2A
d77, e77, v77, rc77, _ = base('r77')
b77 = b26_wire('r77')
p1_77, p2_77 = alpha_proxy(d77)
a77 = p2_77 if USE_P2 else p1_77
m77 = e77 & (b77 > 0) & (a77 > 0)
sl, ic = np.polyfit(np.log(a77[m77]), np.log(b77[m77]), 1)
resid = np.log(b77[m77]) - (sl * np.log(a77[m77]) + ic)
print("  r77 calibration  log|b26| = %.4f * log(alpha) + %.4f   resid sd %.3f (log units, = x%.2f)"
      % (sl, ic, resid.std(), np.exp(resid.std())))
OUT['calib_r77'] = dict(slope=float(sl), intercept=float(ic), resid_sd=float(resid.std()))


def pick(tag):
    d, e, v, rc, tq = base(tag)
    p1, p2 = alpha_proxy(d)
    return d, e, v, rc, tq, (p2 if USE_P2 else p1)


# ================================================================ 1. Q1 -- b5 DUTY
print()
print("=" * 124)
print("1.  Q1 -- `b5` DUTY.  ⭐ THE WITHIN-DRIVE CONTRAST IS ENGAGED vs MANUAL: V106 dosed ONLY")
print("    the ENGAGED records (26/27); mode 24 (MANUAL) is Honda-stock on every build.")
print("    A widening of the engaged-minus-manual gap from a5 to a6 IS the dose arriving.")
print("=" * 124)
print("%16s %10s %10s %10s %12s %12s %12s"
      % ('build', 'eng s', 'man s', 'b5 pooled', 'b5 ENGAGED', 'b5 MANUAL', 'eng - man'))
DUTY = {}
for tag in ('ra4', 'ra5', 'ra6'):
    d, e, v, rc, tq, al = pick(tag)
    b5 = np.asarray(d[B5KEY[tag]], float) > 0.5
    DUTY[tag] = dict(pooled=float(b5.mean()), eng=float(b5[e].mean()), man=float(b5[~e].mean()),
                     eng_s=float(e.sum() / FS), man_s=float((~e).sum() / FS))
    r = DUTY[tag]
    print("%16s %10.1f %10.1f %10.4f %12.4f %12.4f %12.4f"
          % (NAMES[tag], r['eng_s'], r['man_s'], r['pooled'], r['eng'], r['man'],
             r['eng'] - r['man']))
OUT['b5_duty'] = DUTY

print()
print("  SPEED-MATCHED engaged-vs-manual (duty inside each speed bin; the pooled numbers above")
print("  are confounded because manual and engaged driving occupy different speeds):")
VE = [0, 5, 10, 16, 25, 40, 60, 80, 1e9]
VL = ['0-5', '5-10', '10-16', '16-25', '25-40', '40-60', '60-80', '80+']
print("%16s %8s" % ('build', 'arm') + "".join("%10s" % s for s in VL))
for tag in ('ra4', 'ra5', 'ra6'):
    d, e, v, rc, tq, al = pick(tag)
    b5 = np.asarray(d[B5KEY[tag]], float) > 0.5
    for arm, mm in (('engaged', e), ('manual', ~e)):
        row, cells = [], {}
        for i, s in enumerate(VL):
            m = mm & (v >= VE[i]) & (v < VE[i + 1])
            val = float(b5[m].mean()) if m.sum() >= 200 else np.nan
            row.append(val)
            cells[s] = dict(duty=val, n=int(m.sum()))
        print("%16s %8s" % (NAMES[tag], arm)
              + "".join("     --   " if not np.isfinite(x) else "%10.4f" % x for x in row))
        OUT.setdefault('b5_by_speed', {}).setdefault(NAMES[tag], {})[arm] = cells

# ================================================================ 2. THE DOSE CALIBRATION
print()
print("=" * 124)
print("2.  ⭐⭐ THE DOSE CALIBRATION -- `b5` DUTY vs MEASURED ALPHA, ENGAGED.")
print("    At fixed alpha the comparator's operand B is proportional to k, so the curve shifts")
print("    HORIZONTALLY by the delivered multiplier.  This is immune to the closed-loop")
print("    K*alpha invariance that makes a pooled duty uninterpretable.")
print("=" * 124)
AE = np.array([0, 30, 60, 120, 250, 500, 1000, 2000, 4000, 1e9], float)
AL = ['<30', '30-60', '60-120', '120-250', '250-500', '500-1k', '1k-2k', '2k-4k', '4k+']
print("%16s %8s" % ('build', 'n eng') + "".join("%10s" % s for s in AL))
CURVES = {}
for tag in ('ra4', 'ra5', 'ra6'):
    d, e, v, rc, tq, al = pick(tag)
    b5 = np.asarray(d[B5KEY[tag]], float) > 0.5
    row, cells = [], {}
    for i, s in enumerate(AL):
        m = e & (al >= AE[i]) & (al < AE[i + 1])
        val = float(b5[m].mean()) if m.sum() >= 200 else np.nan
        row.append(val)
        cells[s] = dict(duty=val, n=int(m.sum()),
                        alpha_med=float(np.median(al[m])) if m.sum() else np.nan)
    CURVES[tag] = (al, e, b5)
    print("%16s %8d" % (NAMES[tag], int(e.sum()))
          + "".join("     --   " if not np.isfinite(x) else "%10.4f" % x for x in row))
    OUT.setdefault('b5_vs_alpha', {})[NAMES[tag]] = cells
print("  (alpha in deg/s^2, proxy p%d, ENGAGED frames only)" % (2 if USE_P2 else 1))


def alpha_at(alv, b5v, p, lo=1.0, hi=1e5):
    """The alpha at which the duty falls through level p, by log-linear interpolation on a fine
    quantile grid.  Returns nan if the curve never crosses p inside the observed range."""
    q = np.exp(np.linspace(np.log(max(lo, np.percentile(alv, 1))),
                           np.log(min(hi, np.percentile(alv, 99.5))), 40))
    du = []
    for j in range(len(q) - 1):
        m = (alv >= q[j]) & (alv < q[j + 1])
        du.append(b5v[m].mean() if m.sum() >= 100 else np.nan)
    du = np.array(du)
    ctr = np.sqrt(q[:-1] * q[1:])
    ok = np.isfinite(du)
    if ok.sum() < 4:
        return np.nan
    c, dd = ctr[ok], du[ok]
    for j in range(len(dd) - 1):
        if (dd[j] - p) * (dd[j + 1] - p) <= 0 and dd[j] != dd[j + 1]:
            w = (p - dd[j]) / (dd[j + 1] - dd[j])
            return float(np.exp(np.log(c[j]) + w * (np.log(c[j + 1]) - np.log(c[j]))))
    return np.nan


print()
print("  ⭐ THE DELIVERED MULTIPLIER, read off the horizontal shift (episode bootstrap):")
print("%10s" % 'level p' + "".join("%16s" % NAMES[t] for t in ('ra4', 'ra5', 'ra6'))
      + "%22s %22s" % ('a6/a5 shift', 'a6/a4 shift'))


def eps_of(tag):
    d, e, _, _, _, _ = pick(tag)
    idx = np.flatnonzero(np.diff(e.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(e)]))
    return [(int(a), int(c)) for a, c in zip(b[:-1], b[1:])
            if e[a] and (c - a) >= int(2.5 * FS)]


BOOT = {}
for tag in ('ra4', 'ra5', 'ra6'):
    al, e, b5 = CURVES[tag]
    BOOT[tag] = (al, b5, eps_of(tag))
for p in (0.10, 0.15, 0.20, 0.25):
    pts, arrs = {}, {}
    for tag in ('ra4', 'ra5', 'ra6'):
        al, b5, eps = BOOT[tag]
        cat = np.concatenate([np.arange(a, b) for a, b in eps])
        pts[tag] = alpha_at(al[cat], b5[cat].astype(float), p)
        rg = np.random.default_rng(41)
        vv = []
        for _ in range(400):
            pick_e = rg.integers(0, len(eps), len(eps))
            c2 = np.concatenate([np.arange(*eps[j]) for j in pick_e])
            vv.append(alpha_at(al[c2], b5[c2].astype(float), p))
        arrs[tag] = np.array(vv, float)
    r65 = arrs['ra5'] / arrs['ra6']
    r64 = arrs['ra4'] / arrs['ra6']
    q65 = np.nanpercentile(r65, [2.5, 97.5]) if np.isfinite(r65).sum() > 20 else [np.nan] * 2
    q64 = np.nanpercentile(r64, [2.5, 97.5]) if np.isfinite(r64).sum() > 20 else [np.nan] * 2
    print("%10.2f" % p + "".join("%16.1f" % pts[t] for t in ('ra4', 'ra5', 'ra6'))
          + "%22s %22s"
          % ("%.2f [%.2f, %.2f]" % (pts['ra5'] / pts['ra6'], q65[0], q65[1]),
             "%.2f [%.2f, %.2f]" % (pts['ra4'] / pts['ra6'], q64[0], q64[1])))
    OUT.setdefault('delivered_multiplier', {})["p=%.2f" % p] = dict(
        alpha_p={NAMES[t]: float(pts[t]) for t in pts},
        a6_over_a5=float(pts['ra5'] / pts['ra6']), ci_a5=[float(q65[0]), float(q65[1])],
        a6_over_a4=float(pts['ra4'] / pts['ra6']), ci_a4=[float(q64[0]), float(q64[1])])
print("  🛑 EXPECTED 2.00 if V105 really ran x1.5 and V106 really runs x3.0.")
print("     A value near 3.00 instead would mean the x1.5 was NEVER IN FORCE (open item #6 / Q7).")

# ================================================================ 3. Q2' THE CLAMP
print()
print("=" * 124)
print("3.  Q2' -- THE CLAMP.  (A) the RECONSTRUCTION, (B) the assumption-free RELAY TEST.")
print("=" * 124)
print("\n  (A) RECONSTRUCTED |gp-0x6b26| on a6 = r77's alpha->b26 law x 3.0 (r77 ran x1.00 stock).")
print("      🛑 THIS IS A RECONSTRUCTION, NOT A MEASUREMENT -- resid sd x%.2f on its own"
      % np.exp(resid.std()))
print("      calibration route.  Read the DUTIES as an order of magnitude, not to 3 decimals.")
RE = [0, 5, 15, 40, 100, 200, 400, 1e9]
RL = ['0-5', '5-15', '15-40', '40-100', '100-200', '200-400', '400+']
d6, e6, v6, rc6, tq6, al6 = pick('ra6')
b26_hat = np.exp(sl * np.log(np.clip(al6, 1e-6, None)) + ic) * 3.0
b26_hat = np.clip(b26_hat, 0, None)
print("%12s %10s %10s %10s %10s %12s %12s"
      % ('|rate| bin', 'n eng', 'p50', 'p90', 'p99', 'duty>=511', 'duty>=256'))
for i, lbl in enumerate(RL):
    m = e6 & (rc6 >= RE[i]) & (rc6 < RE[i + 1])
    if m.sum() < 100:
        print("%12s %10d   -- too few frames --" % (lbl, m.sum()))
        continue
    x = np.minimum(b26_hat[m], CLAMP)
    xr = b26_hat[m]
    print("%12s %10d %10.1f %10.1f %10.1f %12.5f %12.5f"
          % (lbl, m.sum(), np.percentile(x, 50), np.percentile(x, 90), np.percentile(x, 99),
             np.mean(xr >= CLAMP), np.mean(xr >= 256)))
    OUT.setdefault('clamp_recon_by_rate', {})[lbl] = dict(
        n=int(m.sum()), duty511=float(np.mean(xr >= CLAMP)), duty256=float(np.mean(xr >= 256)))
print("%12s %10s %10s %10s %10s %12s %12s"
      % ('speed regime', 'n eng', 'p50', 'p90', 'p99', 'duty>=511', 'duty>=256'))
for lbl, lo, hi in (('<8 km/h (S1)', 0, 8), ('<16 km/h', 0, 16), ('16-40', 16, 40),
                    ('40-95 (S3)', 40, 95), ('hard turn S2c', -1, -1)):
    if lo < 0:
        m = e6 & (v6 < 20) & (tq6 >= 500) & (rc6 >= 15) & (rc6 < 40)
    else:
        m = e6 & (v6 >= lo) & (v6 < hi)
    if m.sum() < 100:
        print("%12s %10d   -- too few frames --" % (lbl, m.sum()))
        continue
    xr = b26_hat[m]
    x = np.minimum(xr, CLAMP)
    print("%12s %10d %10.1f %10.1f %10.1f %12.5f %12.5f"
          % (lbl, m.sum(), np.percentile(x, 50), np.percentile(x, 90), np.percentile(x, 99),
             np.mean(xr >= CLAMP), np.mean(xr >= 256)))
    OUT.setdefault('clamp_recon_by_speed', {})[lbl] = dict(
        n=int(m.sum()), duty511=float(np.mean(xr >= CLAMP)), duty256=float(np.mean(xr >= 256)))

print()
print("  (B) ⭐ THE ASSUMPTION-FREE RELAY TEST.  If |gp-0x6b26| were railing at 511 above some")
print("      alpha, `b5` would collapse to ( |gp-0x6ae2| >= 511 ) -- NO alpha dependence -- and the")
print("      duty-vs-alpha curve would go FLAT.  A curve still MOVING at the top of the observed")
print("      alpha range is direct evidence the term is not saturating there.  No transfer needed.")
print("%16s %12s" % ('build', 'top decile') + "".join("%12s" % s for s in
                                                      ('d(duty)/d(log a) mid', 'top', 'flat?')))
for tag in ('ra5', 'ra6'):
    al, b5, eps = BOOT[tag]
    cat = np.concatenate([np.arange(a, b) for a, b in eps])
    a_, b_ = al[cat], b5[cat].astype(float)
    q = np.percentile(a_, [50, 70, 85, 93, 97, 99.3, 99.9])
    du, ct = [], []
    edges = np.concatenate(([np.percentile(a_, 20)], q))
    for j in range(len(edges) - 1):
        m = (a_ >= edges[j]) & (a_ < edges[j + 1])
        if m.sum() >= 200:
            du.append(b_[m].mean())
            ct.append(np.sqrt(edges[j] * edges[j + 1]))
    du, ct = np.array(du), np.array(ct)
    if len(du) >= 4:
        smid = float(np.polyfit(np.log(ct[:len(ct) // 2 + 1]), du[:len(ct) // 2 + 1], 1)[0])
        stop = float(np.polyfit(np.log(ct[-3:]), du[-3:], 1)[0])
        print("%16s %12.1f %24.4f %12.4f %12s"
              % (NAMES[tag], ct[-1], smid, stop, "FLAT" if abs(stop) < 0.02 else "still moving"))
        OUT.setdefault('relay_test', {})[NAMES[tag]] = dict(
            slope_mid=smid, slope_top=stop, alpha_top=float(ct[-1]),
            duty_curve=[[float(a), float(b)] for a, b in zip(ct, du)])
        print("        duty by alpha decile: "
              + "  ".join("%.0f:%.3f" % (a, b) for a, b in zip(ct, du)))

json.dump(OUT, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 'analysis-2020accord', '_ra6_dose.json'), 'w'),
          indent=1, default=float)
print("\nwrote analysis-2020accord/_ra6_dose.json")
