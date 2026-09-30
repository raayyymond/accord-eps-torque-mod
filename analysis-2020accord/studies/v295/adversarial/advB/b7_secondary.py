"""b7_secondary.py -- ADV-B step 7 (I7): what ONE drive can and cannot decide on the SECONDARY outcomes, from r71b
(V294) block bootstraps.  No change is simulated: every interval below is the scatter of the metric under NO change,
i.e. the width a V295 effect must exceed to be seen.

Metrics (hands-off laterally-engaged frames; hands-off = not steeringPressed dilated +-0.5 s; the harness's forms):
  HARD16  1.6-3 Hz band-passed wheel rate (x/8, deg/s) rms on HARD frames (|plan| >= 1.5 m/s^2 or |angle| > 60 deg),
          5-10, 10-15 and 5-15 m/s  (plan = controlsState.desiredCurvature * v^2)
  ERR0510 0.5-1 Hz band-passed lateral-accel error rms, 0-5 / 5-10 / 0-10 m/s, two forms: plan - actualLateralAccel
          (harness) and torqueState desired - actual
  RMID    1-3 Hz wheel-rate rms at 15-22 m/s
  TRACK   tracking gain (slope of actual on plan, |plan| > 0.3) and TURN-HOLD (median act/plan at |plan| 0.8-1.5,
          |d plan/dt| < 0.5) by speed band
Band-passes: 2nd-order Butterworth, zero-phase, applied per engaged run (>= 4 s), 1 s trimmed at each end.
Bootstrap unit: 5 s blocks of eligible frames (hard-turn EPISODES for HARD16).  For exposure E: a pseudo-drive =
blocks drawn with replacement until >= E s; ratio to an independent pseudo-drive of the FULL r71b exposure (the baseline
also has sampling error).  2000 draws; 90 % interval.  Within-route bootstrap = a LOWER bound on drive-to-drive scatter.
Run: python b7_secondary.py > b7_secondary_out.txt
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/lib")
import r71b_cache as R  # noqa: E402

rng = np.random.default_rng(71)
G = R.grid100()
n = len(G["t"])
eng = np.asarray(G["eng"], bool)
pressed = np.nan_to_num(G["cs_pressed"]) > 0.5
pr = np.convolve(pressed.astype(int), np.ones(101, int), "same") > 0
ho = eng & ~pr
v = np.nan_to_num(G["cs_vego"])
rate = np.asarray(G["x_fw"], float) / 8.0
ang = np.nan_to_num(G["cs_angle"])
plan = np.nan_to_num(G["ctl_des_curv"]) * v ** 2
act = np.nan_to_num(G["ctl_la_act"])
des = np.nan_to_num(G["ctl_la_des"])
dplan = np.gradient(plan) * 100.0


def runs(mask, min_len=1):
    d = np.diff(np.r_[0, np.asarray(mask, int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= min_len]


def bp_runs(x, lo, hi):
    out = np.full(n, np.nan)
    bb, aa = signal.butter(2, [lo / 50.0, hi / 50.0], btype="band")
    for a, b in runs(eng, 400):
        y = signal.filtfilt(bb, aa, x[a:b])
        y[:100] = np.nan; y[-100:] = np.nan
        out[a:b] = y
    return out


r16 = bp_runs(rate, 1.6, 3.0)
r13 = bp_runs(rate, 1.0, 3.0)
e_plan = bp_runs(plan - act, 0.5, 1.0)
e_des = bp_runs(des - act, 0.5, 1.0)
hard = (np.abs(plan) >= 1.5) | (np.abs(ang) > 60)


def blocks_of(mask, L=500, episodes=False):
    B = []
    for a, b in runs(mask):
        if episodes:
            B.append(np.arange(a, b))
        else:
            for s in range(a, b, L):
                e = min(b, s + L)
                if e - s >= 100:
                    B.append(np.arange(s, e))
    return B


def rms_metric(sig):
    return lambda ii: float(np.sqrt(np.nanmean(sig[ii] ** 2)))


def track_metric(ii):
    sel = np.abs(plan[ii]) > 0.3
    return float(np.polyfit(plan[ii][sel], act[ii][sel], 1)[0]) if sel.sum() > 100 else np.nan


def hold_metric(ii):
    hm = (np.abs(plan[ii]) >= 0.8) & (np.abs(plan[ii]) < 1.5) & (np.abs(dplan[ii]) < 0.5)
    return float(np.median(act[ii][hm] / plan[ii][hm])) if hm.sum() > 50 else np.nan


def pseudo(B, E_s):
    tot, pick = 0, []
    while tot < E_s * 100:
        k = rng.integers(0, len(B))
        pick.append(B[k]); tot += len(B[k])
    return np.concatenate(pick)


def boot(B, f, exposures, ndraw=2000, ratio=True):
    full_s = sum(len(b) for b in B) / 100.0
    base = f(np.concatenate(B))
    out = dict(full_s=full_s, value=base)
    for E in exposures:
        if E > full_s * 1.5:
            continue
        rr, dd = [], []
        for _ in range(ndraw):
            a = f(pseudo(B, E)); bfull = f(pseudo(B, full_s)); c = f(pseudo(B, E))
            if ratio:
                rr.append(a / bfull); dd.append(a / c)
            else:
                rr.append(a - bfull); dd.append(a - c)
        rr = np.array(rr); dd = np.array(dd)
        rr = rr[np.isfinite(rr)]; dd = dd[np.isfinite(dd)]
        out[E] = dict(vs_r71b=(float(np.percentile(rr, 5)), float(np.percentile(rr, 50)), float(np.percentile(rr, 95))),
                      drive_vs_drive=(float(np.percentile(dd, 5)), float(np.percentile(dd, 95))))
    return out


res = {}


def show(name, B, f, exposures, ratio=True, pred=None):
    if not B:
        print("   %-40s no eligible frames" % name)
        return
    o = boot(B, f, exposures, ratio=ratio)
    res[name] = o
    s = "   %-40s r71b %.4g over %5.1f s | " % (name, o["value"], o["full_s"])
    for E in exposures:
        if E in o:
            a = o[E]["vs_r71b"]; d = o[E]["drive_vs_drive"]
            s += "%3ds: %s [%.3f, %.3f] d-v-d [%.3f, %.3f] | " % (E, "x" if ratio else "+", a[0], a[2], d[0], d[1])
    if pred:
        s += " PRED %s" % pred
    print(s)


print("hands-off laterally engaged: %.0f s ; hard frames among them: %.1f s" % (ho.sum() / 100, (ho & hard).sum() / 100))
print("\n[a] HARD16 -- 1.6-3 Hz wheel-rate rms in hard turns (the band behind 'jerky on hard turns at medium speed')")
for lo, hi in ((5, 10), (10, 15), (5, 15)):
    m = ho & hard & (v >= lo) & (v < hi) & np.isfinite(r16)
    show("HARD16 %d-%d m/s (episodes)" % (lo, hi), blocks_of(m, episodes=True), rms_metric(r16), (15, 30, 60),
         pred="down: x0.68-0.93 family, x0.83 nominal (b 1106; b 1050 slightly less) [design, NOT FIT]")
# per-episode scatter (event to event)
m = ho & hard & (v >= 5) & (v < 15) & np.isfinite(r16)
ep = [np.sqrt(np.mean(r16[b] ** 2)) for b in blocks_of(m, episodes=True) if len(b) >= 100]
if len(ep) >= 3:
    ep = np.array(ep)
    ratios = np.array([a / b for i, a in enumerate(ep) for j, b in enumerate(ep) if i != j])
    print("   per-episode (>= 1 s) 5-15 m/s: %d episodes, rms %.1f..%.1f deg/s ; one episode vs another (no change) 90 %% "
          "[x%.2f, x%.2f]" % (len(ep), ep.min(), ep.max(), np.percentile(ratios, 5), np.percentile(ratios, 95)))

print("\n[b] ERR -- 0.5-1 Hz lateral-accel error rms (m/s^2) at low speed (the band behind 'loose at low speed' per ADV-stability)")
for form, sig in (("plan-act", e_plan), ("des-act", e_des)):
    for lo, hi in ((0, 5), (5, 10), (0, 10)):
        m = ho & (v >= lo) & (v < hi) & np.isfinite(sig)
        show("ERR %s %d-%d m/s" % (form, lo, hi), blocks_of(m), rms_metric(sig), (30, 60, 120, 300),
             pred="UP x1.04-1.40 (b 1106, family; direction only) [ADV-stability]")

print("\n[c] RMID -- 1-3 Hz wheel-rate rms at 15-22 m/s")
m = ho & (v >= 15) & (v < 22) & np.isfinite(r13)
show("RMID 15-22 m/s", blocks_of(m), rms_metric(r13), (30, 60, 120), pred="down x0.75-0.99 (b 1106) [design]")

print("\n[d] TRACK / HOLD by speed band (differences, not ratios)")
for lo, hi in ((0, 5), (5, 10), (10, 15), (15, 22), (22, 99)):
    m = ho & (v >= lo) & (v < hi)
    show("TRACK gain %d-%d m/s" % (lo, hi), blocks_of(m), track_metric, (60, 120, 300), ratio=False,
         pred="+-0.004 (no change predicted)")
    show("TURN-HOLD %d-%d m/s" % (lo, hi), blocks_of(m), hold_metric, (60, 120, 300), ratio=False,
         pred="-0.009..+0.014 (no change predicted)")

json.dump(res, open(os.path.join(HERE, "b7_secondary_out.json"), "w"), indent=1, default=str)
