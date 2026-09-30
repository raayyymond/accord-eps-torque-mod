# -*- coding: utf-8 -*-
"""adv4_observe.py -- ADV bytes+instrument, D1/D2/D3: can ONE short drive separate b 964 from V294 on the EXISTING wire?

Independent of the designer's s4_attrib.py: the lane march is the adversary's own mirror (adv2: bit-exact to plib on all
1.02 M r71b ticks), the E3 reader is re-implemented from r71b_attribution.instrument / the design's wire-read table.

Construction (the designer's, made explicit so it can be attacked): FAKE b964 TAP = real r71b tap - quant(V294 march)
+ quant(b964 march) at the tap's own ticks.  This assumes the real residual (tap - march) is NOT trim-proportional; the
stress rows inflate the residual x1.5 and x2 (i.e. up to 100 % of it scaling with the edit) to bound that assumption.

E3 (the flown regressor): y = tap - quant(null march) ~ [1, Rm, pred, dFF/dt],
   Rm = lp1(-d/dt lp1(wire/8, 2.03 Hz), 5.05 Hz) at 100 Hz sampled at the tap frame; pred = quant(null) ; dFF/dt from the
   100 Hz block-mean null.  beta = the Rm coefficient.
Windows (the operator gives ~15-30 s symptomatic + ordinary driving):
   W20ho  the designer's: contiguous hands-off runs cut into 20 s (hands-off = engaged & |bar| < 400 & ~pressed)
   S15/S20/S30ho  sliding 15/20/30 s windows over the whole route (step 2.5 s), hands-off frames only, >= 50 % hands-off
   S15/S20all     sliding windows, ALL engaged frames (hands-on included), plain regressor AND taper-scaled Rm*(m/254)
   HARD15         15 s windows centred on every medium-speed hard turn (5-15 m/s, |angle| >= 45 deg or |cmd rate| peak),
                  all engaged frames, taper-scaled regressor -- the symptomatic episode the operator will actually drive
   DRIVE2/5min    contiguous 2 and 5 minute chunks, pooled over their hands-off frames
Decision thresholds are the design's pre-registered sentences: live-at-x1.7 >= +0.28 (window) ; "V294 gain" +0.15..+0.25 ;
no trim |beta| < 0.04 ; inverted < -0.10.
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "plant"))
import plib as P  # noqa: E402
sys.path.insert(0, HERE)
import adv_mirror as AM  # noqa: E402

d = P.load()
M = np.load(os.path.join(HERE, "_adv_march_r71b.npz"))
sg = int(M["sg"])
T567, T964 = sg * M["T567"], sg * M["T964"]
# null march with the adversary mirror (C = 0 -> r26 == 0)
cN = dict(AM.load_cells(), C=0)
LN = AM.Lane(cN)
x1k = np.clip(np.round(d["x1k"]), -12000, 12000).astype(int).tolist()
sgn, idx, m = d["sgn"].astype(int).tolist(), d["idx"].astype(int).tolist(), d["m"].astype(int).tolist()
Tn = np.zeros(len(x1k), np.int64)
for i in range(len(x1k)):
    k = i // 10
    Tn[i] = LN.tick(x1k[i], sgn[k] * LN.map[idx[k]], idx[k], m[k])
Tn = sg * Tn
print("null march == plib T1k_null: %s" % np.array_equal(Tn, d["T1k_null"].astype(np.int64)))

q = P.quant
ticks = d["tick_tap"]
j = d["j100"]
tap = d["T_tap"].astype(float)
q567, q964, qn = q(T567[ticks]), q(T964[ticks]), q(Tn[ticks])
resid = tap - q567
eng = d["eng"][j]
ho = eng & (np.abs(d["bar"][j]) < 400) & ~d["pressed"][j]
print("tap frames %d ; engaged %d (%.0f s) ; hands-off %d (%.0f s) ; residual rms hands-off %.2f, all engaged %.2f counts"
      % (len(tap), eng.sum(), eng.sum() / 50, ho.sum(), ho.sum() / 50, np.sqrt(np.mean(resid[ho] ** 2)),
         np.sqrt(np.mean(resid[eng] ** 2))))


def lp1(xs, fc, fs=100.0):
    a = math.exp(-2 * math.pi * fc / fs)
    y = np.empty_like(xs)
    s = xs[0]
    for i, v in enumerate(xs):
        s = a * s + (1 - a) * v
        y[i] = s
    return y


wire = np.nan_to_num(d["wire"]) / 8.0
fp = -math.log(1011 / 1024) / (2 * math.pi * 1e-3)
Rm100 = lp1(-np.gradient(lp1(wire, fp)) * 100.0, 5.05)
Rm = Rm100[j]
taper = d["m"][j] / 254.0
RmT = Rm * taper
dff = (np.gradient(P.block_mean_1k(Tn.astype(float), len(d["t"]), d["dms"])) * 100.0)[j]
tt = d["t"][j] - d["t"][0]
v = d["v"][j]
print("E3 regressor pole %.3f Hz (from a = 1011)" % fp)


def beta(y, R, mk):
    X = np.column_stack([np.ones(mk.sum()), R[mk], qn[mk], dff[mk]])
    return np.linalg.lstsq(X, y[mk], rcond=None)[0][1]


def taps(k=1.0):
    """V294 real tap and the b964 fake tap with the residual scaled by k (k = 1: the designer's construction)"""
    return q567 + k * resid, q964 + k * resid


def windows_sliding(L_s, step_s=2.5, base=eng, need=ho, min_frac=0.5):
    out = []
    n = len(tt)
    s = 0.0
    T_end = tt[-1]
    while s + L_s <= T_end:
        a = np.searchsorted(tt, s)
        b = np.searchsorted(tt, s + L_s)
        mk = np.zeros(n, bool)
        mk[a:b] = True
        sel = mk & need
        if sel.sum() >= min_frac * L_s * 50 and (mk & base).sum() >= 0.8 * L_s * 50:
            out.append(sel)
        s += step_s
    return out


def windows_designer():
    out = []
    for a, b in P.runs(ho, 1000):
        for s0 in range(a, b - 1000 + 1, 1000):
            mk = np.zeros(len(tt), bool)
            mk[s0 + 50:s0 + 1000] = True
            out.append(mk & ho)
    return out


def hard_turn_windows(L_s=15.0):
    """medium-speed hard turns: engaged, 5-15 m/s, |angle| >= 45 deg; one window per event (events >= 5 s apart)"""
    th = np.abs(d["th"][j])
    cand = np.flatnonzero(eng & (v >= 5) & (v < 15) & (th >= 45))
    ev = []
    last = -1e9
    for i in cand:
        if tt[i] - last > 5.0:
            ev.append(i)
            last = tt[i]
    out = []
    for i in ev:
        mk = (tt >= tt[i] - L_s / 2) & (tt < tt[i] + L_s / 2) & eng
        if mk.sum() >= 0.8 * L_s * 50:
            out.append(mk)
    return out


def summarize(name, wins, R=Rm, ks=(1.0, 1.5, 2.0)):
    if not wins:
        print("  %-26s NO WINDOWS" % name)
        return
    for k in ks:
        t294, t964 = taps(k)
        y294, y964 = t294 - qn, t964 - qn
        b294 = np.array([beta(y294, R, w) for w in wins])
        b964 = np.array([beta(y964, R, w) for w in wins])
        p = lambda a, pc: np.percentile(a, pc)  # noqa: E731
        miss = np.mean(b964 < 0.28)
        misread = np.mean((b964 >= 0.15) & (b964 <= 0.25))
        gap964 = np.mean((b964 > 0.25) & (b964 < 0.28))
        false_live = np.mean(b294 >= 0.28)
        v294ok = np.mean((b294 >= 0.15) & (b294 <= 0.25))
        sep = (np.median(b964) - np.median(b294)) / (0.5 * (p(b964, 84) - p(b964, 16) + p(b294, 84) - p(b294, 16)) / 2)
        # the best single threshold a reader could use, and its error rate
        ths = np.linspace(0.1, 0.5, 401)
        err = [0.5 * (np.mean(b964 < t) + np.mean(b294 >= t)) for t in ths]
        tb = ths[int(np.argmin(err))]
        print("  %-26s n %4d  k %.1f | V294 med %+.3f [5-95 %+.3f,%+.3f] | b964 med %+.3f [%+.3f,%+.3f] | d' %.1f |"
              " b964<0.28 %.3f  b964 in V294-band %.3f  b964 in gap %.3f | V294>=0.28 %.3f  V294 in band %.3f |"
              " best thr %.3f err %.3f" % (name, len(wins), k, np.median(b294), p(b294, 5), p(b294, 95), np.median(b964),
                                          p(b964, 5), p(b964, 95), sep, miss, misread, gap964, false_live, v294ok, tb,
                                          min(err)))


print("\n=== E3 per window, V294 (real tap) vs b964 (fake tap); k = residual scale ===")
summarize("W20ho designer", windows_designer())
for L in (15.0, 20.0, 30.0):
    summarize("S%dho sliding (>=50%% ho)" % L, windows_sliding(L))
for L in (15.0, 20.0):
    wa = windows_sliding(L, need=eng, min_frac=0.8)
    summarize("S%dall plain Rm" % L, wa, R=Rm, ks=(1.0,))
    summarize("S%dall taper Rm" % L, wa, R=RmT, ks=(1.0, 2.0))
hw = hard_turn_windows()
print("  hard-turn events (5-15 m/s, |angle| >= 45 deg): %d windows; hands-off fraction in them median %.2f"
      % (len(hw), np.median([np.mean(ho[w]) for w in hw]) if hw else float("nan")))
summarize("HARD15 all, plain Rm", hw, R=Rm, ks=(1.0,))
summarize("HARD15 all, taper Rm", hw, R=RmT, ks=(1.0, 2.0))
hwo = [w & ho for w in hw if (w & ho).sum() >= 250]
summarize("HARD15 ho-only (>=5 s ho)", hwo, ks=(1.0,))

print("\n=== pooled over contiguous drive chunks (hands-off frames) ===")
for mins in (2.0, 5.0):
    wins = []
    L = mins * 60
    s = 0.0
    while s + L <= tt[-1]:
        mk = (tt >= s) & (tt < s + L) & ho
        if mk.sum() >= 30 * 50:
            wins.append(mk)
        s += L / 2
    summarize("DRIVE%.0fmin pooled ho" % mins, wins, ks=(1.0, 2.0))

# the pooled whole-route numbers (the designer's headline) for reference
t294, t964 = taps(1.0)
print("\npooled whole route hands-off: V294 %+.3f  b964 %+.3f (designer +0.213 / +0.361)"
      % (beta(t294 - qn, Rm, ho), beta(t964 - qn, Rm, ho)))
# SEL circularity demonstration: rms(fake964 - q964) == rms(real - q567) identically
print("SEL circularity: rms(fake964 - q964) = %.4f ; rms(real tap - q567) = %.4f (identical by construction)"
      % (np.sqrt(np.mean((t964 - q964)[ho] ** 2)), np.sqrt(np.mean((t294 - q567)[ho] ** 2))))
# how trim-proportional is the real residual?  regress resid^2 on the modelled trim^2 on hands-off frames
trim = q567 - qn
X = np.column_stack([np.ones(ho.sum()), trim[ho] ** 2])
cf = np.linalg.lstsq(X, resid[ho] ** 2, rcond=None)[0]
print("residual^2 = %.2f + %.5f * trim^2 (hands-off): trim-proportional share of residual variance %.1f %% ; "
      "binned rms by |trim| quartile %s" % (cf[0], cf[1], 100 * cf[1] * np.mean(trim[ho] ** 2) / np.mean(resid[ho] ** 2),
                                            [round(float(np.sqrt(np.mean(resid[ho][(np.abs(trim[ho]) >= lo) & (np.abs(trim[ho]) < hi)] ** 2))), 2)
                                             for lo, hi in ((0, 4), (4, 12), (12, 30), (30, 1e9))]))
