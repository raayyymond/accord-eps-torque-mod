# -*- coding: utf-8 -*-
"""ab4_observe.py -- ADV instrument: can ONE short drive separate candidate A (b 1106) from V294 on the EXISTING wire?

Instrument (the design's, re-implemented on MY lane): per window, OLS  T_tap = c0 + c1*FF + c2*TRIM  on 427-tap frames,
FF = my V294 march with r26 forced 0 (feed-forward only), TRIM = my V294 live march - FF, both on the drive's own
recorded 0xE4-derived demand and 0x18F rate (plib cache inputs; my march == plib T1k_live bit-for-bit, ab2 [7]).
  NULL      : the REAL r71b tap (V294 on the car).
  POSITIVE  : synthetic A tap = quant(my A march) + the REAL r71b residual (tap - quant(V294 march)).
  STRESS    : POSITIVE + 0.95 x (a proxy of the part of the residual that SCALES WITH b: TRIM computed from a ZOH /
              linear 100 Hz x minus TRIM from the resample_poly x) -- the residual under A carries 1.95x the
              reconstruction error that V294's residual carries.
Windows: (W1) hands-off engaged tap frames in consecutive chunks of 5/10/15/20/30 s ; (W2) contiguous 15 s / 30 s
wall-clock windows, ALL engaged frames (hands-on included, taper in the march) ; (W3) SYMPTOMATIC windows: +-10 s
around each medium-speed hard turn (my own event finder), all engaged frames and hands-off only.
Then the SYMPTOM band's one-episode noise floor (1.6-3 Hz wheel-rate rms per hard-turn event; raw and normalised).
ANALYSIS ONLY."""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ab2_lane as AL  # noqa: E402

KIT = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
d = np.load(KIT + "/analysis-2020accord/studies/v295/plant/_scratch/cache/plant_r71b_v294.npz")
sg = int(d["sg"])
c294 = AL.cells()
cA = AL.cells(b_override=1106)
cB = AL.cells(b_override=850)
n1k = len(d["x1k"])
idx100, sgn100, m100 = d["idx"], d["sgn"], d["m"]


def march(c, x1k=None):
    if x1k is None:
        r26 = np.zeros(n1k, dtype=np.int64)
    else:
        r26 = np.array(AL.r26_series(np.clip(np.round(x1k), -12000, 12000).astype(np.int64).tolist(), c)[0], dtype=np.int64)
    sp1k = np.repeat(sgn100 * np.array(c["SP"])[idx100], 10)[:n1k]
    m1k = np.repeat(m100, 10)[:n1k]
    P = np.clip(((sp1k << c["shl"]) - r26) * c["Kp"] >> 8, -c["Pcl"], c["Pcl"])
    S = np.clip((P * m1k) >> 8, -c["Scl"], c["Scl"])
    return sg * np.array(AL.lag_series(S.tolist(), c), dtype=np.float64)


def quant(T):
    return np.sign(T) * (np.abs(T).astype(np.int64) >> 3) * 8.0


x_rp = d["x1k"]
wire = np.nan_to_num(d["wire"])
x_zoh = np.repeat(wire, 10)[:n1k]
x_lin = np.interp(np.arange(n1k) / 10.0, np.arange(len(wire)), wire)
T0 = march(c294)                       # FF only (r26 = 0)
T294 = march(c294, x_rp)
TA = march(cA, x_rp)
TB = march(cB, x_rp)
T294_zoh = march(c294, x_zoh)
T294_lin = march(c294, x_lin)
assert np.array_equal(T294, d["T1k_live"]), "my V294 march != plib"
assert np.array_equal(T0, d["T1k_null"]), "my FF march != plib null"
print("my FF and live marches == plib T1k_null / T1k_live bit-for-bit (1,020,390 ticks)")

tt = d["tick_tap"]
Ttap = d["T_tap"]
j = d["j100"]
FF = T0[tt]
TR = T294[tt] - T0[tt]
resid = Ttap - quant(T294[tt])
err_zoh = (T294_zoh[tt] - T0[tt]) - TR
err_lin = (T294_lin[tt] - T0[tt]) - TR
eng = d["eng"][j]
pressed = d["cs_pressed"][j] > 0.5
ho = eng & ~pressed & (np.abs(d["bar"][j]) < 400)
print("tap frames %d, engaged %d (%.0f s), hands-off engaged %d (%.0f s) ; tap residual vs V294 march (hands-off) %.2f counts rms"
      % (len(tt), eng.sum(), eng.sum() / 50.0, ho.sum(), ho.sum() / 50.0, np.sqrt(np.mean(resid[ho] ** 2))))
print("trim-reconstruction error proxies on hands-off engaged frames: ZOH-x %.2f, linear-x %.2f counts rms (TRIM itself %.2f)"
      % (np.sqrt(np.mean(err_zoh[ho] ** 2)), np.sqrt(np.mean(err_lin[ho] ** 2)), np.sqrt(np.mean(TR[ho] ** 2))))

Y = {"V294 real": Ttap,
     "A synth": quant(TA[tt]) + resid,
     "A stress(zoh)": quant(TA[tt]) + resid + 0.95 * err_zoh,
     "B b850 synth": quant(TB[tt]) + resid}


def ols(y, X):
    X1 = np.column_stack([np.ones(len(y))] + list(X))
    co, *_ = np.linalg.lstsq(X1, y, rcond=None)
    return co


def report(name, wins, min_frames=100):
    wins = [w for w in wins if len(w) >= min_frames]
    print("\n%s: %d windows (frames per window median %d)" % (name, len(wins), int(np.median([len(w) for w in wins])) if wins else 0))
    if not wins:
        return None
    out = {}
    for k, y in Y.items():
        C = np.array([ols(y[w], (FF[w], TR[w])) for w in wins])
        out[k] = C
        print("   %-14s c1 median %.3f [p5 %.3f p95 %.3f] | c2 median %.3f [p5 %.3f p95 %.3f] min %.3f max %.3f"
              % (k, np.median(C[:, 1]), *np.percentile(C[:, 1], [5, 95]), np.median(C[:, 2]),
                 *np.percentile(C[:, 2], [5, 95]), C[:, 2].min(), C[:, 2].max()))
    thr = 1.45
    fa = np.mean(out["V294 real"][:, 2] > thr)
    miss = np.mean(out["A synth"][:, 2] <= thr)
    miss_s = np.mean(out["A stress(zoh)"][:, 2] <= thr)
    trim_rms = [np.std(TR[w]) for w in wins]
    print("   rule c2 > %.2f => 'A live': false-alarm on V294 %d/%d, miss on A %d/%d, miss on A-stress %d/%d ;"
          " TRIM rms per window median %.1f (min %.1f) counts"
          % (thr, int(fa * len(wins)), len(wins), int(miss * len(wins)), len(wins), int(miss_s * len(wins)), len(wins),
             np.median(trim_rms), np.min(trim_rms)))
    return out


# W1: hands-off frames, consecutive chunks
iho = np.flatnonzero(ho)
for sec in (5, 10, 15, 20, 30):
    n = sec * 50
    report("W1 hands-off engaged, %d s of tap frames" % sec, [iho[i:i + n] for i in range(0, len(iho) - n + 1, n)])

# W2: contiguous wall-clock windows, all engaged frames
t_tap = d["t_tap"]
for sec in (15, 30):
    edges = np.arange(t_tap[0], t_tap[-1], sec)
    wins = []
    for a in edges:
        w = np.flatnonzero((t_tap >= a) & (t_tap < a + sec) & eng)
        if len(w) >= 0.8 * sec * 50:
            wins.append(w)
    report("W2 contiguous %d s windows, ALL engaged frames (>= 80 %% engaged)" % sec, wins)
    wins_ho = []
    for a in edges:
        w = np.flatnonzero((t_tap >= a) & (t_tap < a + sec) & ho)
        if len(w) >= 0.5 * sec * 50:
            wins_ho.append(w)
    report("W2 contiguous %d s windows, hands-off frames only (>= 50 %% hands-off)" % sec, wins_ho)

# W3: symptomatic windows around medium-speed hard turns (v 5-22 m/s, |desired lat accel| >= 1.0 for >= 1 s)
v = d["v"]
lad = np.abs(d["ctl_la_des"])
e100 = d["eng"]
hard = (v >= 5) & (v < 22) & (lad >= 1.0) & e100
dd = np.diff(np.r_[0, hard.astype(int), 0])
ev = [(a, b) for a, b in zip(np.flatnonzero(dd == 1), np.flatnonzero(dd == -1)) if b - a >= 100]
# merge events closer than 5 s
mer = []
for a, b in ev:
    if mer and a - mer[-1][1] < 500:
        mer[-1] = (mer[-1][0], b)
    else:
        mer.append((a, b))
print("\nmedium-speed hard-turn events (v 5-22, |la_des| >= 1.0 m/s^2 for >= 1 s, merged within 5 s): %d" % len(mer))
t100 = d["t"]
w3_all, w3_ho, evinfo = [], [], []
for a, b in mer:
    tc0, tc1 = t100[a] - 10.0, t100[b - 1] + 10.0
    w = np.flatnonzero((t_tap >= tc0) & (t_tap < tc1) & eng)
    wh = np.flatnonzero((t_tap >= tc0) & (t_tap < tc1) & ho)
    w3_all.append(w)
    w3_ho.append(wh)
    evinfo.append((d["tr"][a], (b - a) / 100.0, float(np.median(v[a:b])), len(w) / 50.0, len(wh) / 50.0))
for e in evinfo:
    print("   event at route %.0f s: hard for %.1f s, v %.1f m/s ; window engaged %.1f s, hands-off %.1f s" % e)
o3 = report("W3 SYMPTOMATIC windows (event +-10 s), ALL engaged frames", w3_all, min_frames=50)
o3h = report("W3 SYMPTOMATIC windows (event +-10 s), hands-off frames only", w3_ho, min_frames=50)
if o3 is not None:
    print("   per-event c2 (all engaged): V294 %s" % np.round(o3["V294 real"][:, 2], 2).tolist())
    print("                               A    %s" % np.round(o3["A synth"][:, 2], 2).tolist())
    print("                               Astr %s" % np.round(o3["A stress(zoh)"][:, 2], 2).tolist())

# ---------------------------------------------------------------- the SYMPTOM band's single-episode noise floor
om = d["om"]                                   # wheel rate deg/s (0x18F / 8), 100 Hz
cmd = d["cmd"]
sos = signal.butter(4, [1.6, 3.0], btype="band", fs=100.0, output="sos")
om_b = signal.sosfiltfilt(sos, np.nan_to_num(om))
cmd_b = signal.sosfiltfilt(sos, np.nan_to_num(cmd))
tap100 = np.interp(t100, t_tap, Ttap)
tap_b = signal.sosfiltfilt(sos, tap100)
st = []
for a, b in mer:
    lo, hi = max(0, a - 100), min(len(om), b + 100)
    r = np.sqrt(np.mean(om_b[lo:hi] ** 2))
    rc = np.sqrt(np.mean(cmd_b[lo:hi] ** 2))
    rt = np.sqrt(np.mean(tap_b[lo:hi] ** 2))
    st.append((r, r / max(rc, 1e-9), r / max(rt, 1e-9)))
st = np.array(st)
print("\nSYMPTOM band, per hard-turn event (event +-1 s): 1.6-3 Hz wheel-rate rms deg/s: %s"
      % np.round(st[:, 0], 1).tolist())
for k, nm in enumerate(("raw rate rms", "rate / command (1.6-3 Hz)", "rate / tap (1.6-3 Hz)")):
    lg = np.log(st[:, k])
    sd = np.std(lg, ddof=1)
    mde1 = np.exp(-1.645 * np.sqrt(2) * sd)
    mde3 = np.exp(-1.645 * np.sqrt(2.0 / 3.0) * sd)
    print("   %-27s ln-sd across events %.2f -> one-event-vs-one-event ratio 90 %% band x%.2f..x%.2f ;"
          " smallest detectable drop (one-sided 95 %%): 1 event x%.2f, mean of 3 events x%.2f"
          % (nm, sd, np.exp(-1.645 * np.sqrt(2) * sd), np.exp(1.645 * np.sqrt(2) * sd), mde1, mde3))
