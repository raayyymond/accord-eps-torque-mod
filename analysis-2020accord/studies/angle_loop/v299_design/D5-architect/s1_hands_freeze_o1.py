# -*- coding: utf-8 -*-
r"""s1_hands_freeze_o1.py -- D5-architect (V299 design round).  Route-79 COUNTERFACTUALS for the hand-detection layer:
  A. the hands-off torque-word (reaction twist) distribution by speed and |alpha|  -> where a threshold must sit;
  B. the FIRMWARE integrator-freeze rule: V298 (hard 512 | opposing 300) vs candidate rules -> freeze duty, discarded
     integration, toggle rate, threshold-crossing rate per minute of hands-off turning (the ratchet's measured trigger);
  C. the FORK O1 override rule: V298 (on > 600 raw, off <= 500) vs debounced / Honda-threshold rules -> how many of the
     70 hand episodes (steeringPressed) are still caught and how late, how many of the 345 twist episodes still fire;
  D. the fork setpoint limiter on hard windows only (recursive, <= ~25k frames): cap binding share under the V298 O1 +
     120 deg/s cap vs the candidate O1 + cap 250 deg/s, and the demand beyond the error clip.
ANALYSIS ONLY (caches; nothing sent / flashed / edited).  Vectorised except D's limiter recursion, which runs only over
hard-manoeuvre windows (a few thousand frames).  Wall time printed.  python = bin_decompile env.
Sign conventions (m3_lane / M3 / refute_synth_data, re-used): bar = 0x18F x 1.024 (signed); gp-0x4f60 = -bar;
err = theta_sp - theta (deg, + = setpoint left of the wheel); E' has the sign of err (G > 0).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import signal

T0 = time.time()
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
sys.path.insert(0, str(AL / "v298_flight"))
import m3_lane as M  # noqa: E402

KIT = M.KIT
OUT = KIT / "_scratch" / "out" / "v299_D5"
OUT.mkdir(parents=True, exist_ok=True)
LINES = []


def pr(s=""):
    print(s)
    LINES.append(s)


def runs(mask):
    m = np.asarray(mask, bool).astype(np.int8)
    d = np.diff(np.r_[0, m, 0])
    return np.flatnonzero(d == 1), np.flatnonzero(d == -1)


def dilate(mask, k):
    if k <= 0:
        return mask.copy()
    c = np.convolve(mask.astype(float), np.ones(2 * k + 1), "same")
    return c > 0.5


# ---------------------------------------------------------------------------------------------------------------------
W = M.load_wire()
t, v, eng = W["t"], W["vego"], W["eng"]
bar = np.nan_to_num(W["bar"])
abar = np.abs(bar)
gp60 = -bar
err = np.nan_to_num(W["err"])
press = W["pressed"]
theta = np.nan_to_num(W["ang"])
w18 = np.nan_to_num(W["w18"])
b8, a8 = signal.butter(2, 8.0 / 50.0)
alpha = np.gradient(signal.filtfilt(b8, a8, w18)) * 100.0       # deg/s^2 (M3 method 1)
handsoff = eng & ~dilate(press, 50)                               # 0.5 s guard around steeringPressed
hard = eng & ((np.abs(theta) > 30) | (np.abs(w18) > 60))
w05 = np.convolve(w18, np.ones(50) / 50, "same")
turning = eng & (np.abs(w05) >= 10)
tse = W["tse"]
settled = eng & (tse >= 1.2)
VB = (("0-5", 0, 5), ("5-8", 5, 8), ("8-12.5", 8, 12.5), ("12.5-22", 12.5, 22), (">22", 22, 99))
pr("s1 -- route 79 (V298), hands / freeze / O1 counterfactuals.  engaged %.1f s, hands-off %.1f s, hard %.1f s "
   "(hands-off hard %.1f s), hands-off turning %.1f s" % (eng.sum() / 100, handsoff.sum() / 100, hard.sum() / 100,
                                                          (hard & handsoff).sum() / 100, (turning & handsoff).sum() / 100))

# =====================================================================================================================
# A. the hands-off torque word distribution (EVIDENCE: wire)
# =====================================================================================================================
pr("\nA. HANDS-OFF |gp-0x4f60| (= |bar|, gp units = 0x18F raw x 1.024) percentiles; 1229 gp = 1200 raw (Honda STEER_THRESHOLD)")
pr("  %-9s %7s %6s %6s %6s %7s %7s %6s | %s" % ("band", "s", "p50", "p90", "p99", "p99.9", "max", ">1229%",
                                                "hands-off HARD: p90 p99 max >1229%"))
A = {}
for nm, lo, hi in VB:
    m = handsoff & settled & (v >= lo) & (v < hi)
    mh = m & hard
    if m.sum() < 50:
        continue
    q = np.percentile(abar[m], [50, 90, 99, 99.9])
    qh = np.percentile(abar[mh], [90, 99]) if mh.sum() > 20 else [np.nan, np.nan]
    A[nm] = dict(s=m.sum() / 100, p=q.tolist(), max=float(abar[m].max()), f1229=float((abar[m] > 1229).mean()),
                 hard_p90=float(qh[0]), hard_p99=float(qh[1]), hard_max=float(abar[mh].max()) if mh.any() else None,
                 hard_f1229=float((abar[mh] > 1229).mean()) if mh.any() else None)
    pr("  %-9s %7.1f %6.0f %6.0f %6.0f %7.0f %7.0f %5.2f%% | %5.0f %5.0f %5.0f %5.2f%%" % (
        nm, m.sum() / 100, q[0], q[1], q[2], q[3], abar[m].max(), 100 * (abar[m] > 1229).mean(), qh[0], qh[1],
        abar[mh].max() if mh.any() else np.nan, 100 * (abar[mh] > 1229).mean() if mh.any() else np.nan))
pr("  by |alpha| (hands-off settled, all speeds): " + "  ".join(
    "%s: p90 %.0f p99 %.0f" % (lab, np.percentile(abar[handsoff & settled & (np.abs(alpha) >= lo) & (np.abs(alpha) < hi)], 90),
                               np.percentile(abar[handsoff & settled & (np.abs(alpha) >= lo) & (np.abs(alpha) < hi)], 99))
    for lab, lo, hi in (("<100", 0, 100), ("100-400", 100, 400), ("400-1000", 400, 1000), (">1000", 1000, 1e9))
    if (handsoff & settled & (np.abs(alpha) >= lo) & (np.abs(alpha) < hi)).sum() > 50))
pm = eng & press
pr("  PRESSED (steeringPressed, hand) |bar|: p10 %.0f p50 %.0f p90 %.0f (n %.1f s)" % (
    *np.percentile(abar[pm], [10, 50, 90]), pm.sum() / 100))

# =====================================================================================================================
# B. the firmware freeze rule
# =====================================================================================================================
G = M.glut(M.image_cells()["rows"])
vws = np.clip(np.round(v * 230.4), 0, 12000).astype(int)
wgt = np.abs(err) * G[vws]                                       # |E G| weighting (refute_synth_data form, no A3)
opp = np.sign(gp60) * np.sign(err) < 0


def frz_rule(th_hard, th_opp):
    f = abar > th_hard
    if th_opp is not None:
        f |= (abar > th_opp) & opp
    return f


RULES = (("V298 512|opp300", 512, 300), ("hard 512 only", 512, None), ("hard 900 only", 900, None),
         ("hard 1229 | opp 900", 1229, 900), ("hard 1229 only [V299]", 1229, None), ("no freeze", 1e9, None))
pr("\nB. INTEGRATOR FREEZE RULE on r79's wire (hands-off settled frames; the I-rate effect, not a closed-loop replay)")
pr("  %-24s %8s %8s %9s %9s %10s %10s %12s" % ("rule", "duty", "dutyHARD", "discard", "disc<8", "toggles/s", "tog/s HARD",
                                               "x-ings/min turn"))
B = {}
ho = handsoff & settled
for nm, th1, th2 in RULES:
    f = frz_rule(th1, th2)
    tog = np.abs(np.diff(f.astype(int))) > 0
    tog = np.r_[False, tog]
    lo8 = ho & (v < 8)
    # crossings of the rule's thresholds by |bar| (either threshold), per minute of hands-off turning
    xs = np.zeros(len(t), bool)
    for th in (th1, th2):
        if th is None or th > 1e8:
            continue
        a = abar > th
        xs |= np.r_[False, a[1:] != a[:-1]]
    tm = turning & handsoff
    r = dict(duty=float(f[ho].mean()), duty_hard=float(f[ho & hard].mean()),
             discard=float((wgt * f)[ho].sum() / wgt[ho].sum()), discard_lt8=float((wgt * f)[lo8].sum() / wgt[lo8].sum()),
             tog=float(tog[ho].sum() / (ho.sum() / 100)), tog_hard=float(tog[ho & hard].sum() / max((ho & hard).sum() / 100, 1e-9)),
             xing=float(xs[tm].sum() / (tm.sum() / 6000)))
    for b_, lo, hi in (("0-5", 0, 5), ("5-10", 5, 10)):
        mm = tm & (v >= lo) & (v < hi)
        r["xing_" + b_] = float(xs[mm].sum() / max(mm.sum() / 6000, 1e-9))
    B[nm] = r
    pr("  %-24s %7.2f%% %7.2f%% %8.1f%% %8.1f%% %10.2f %10.2f %7.1f (0-5 %.1f, 5-10 %.1f)" % (
        nm, 100 * r["duty"], 100 * r["duty_hard"], 100 * r["discard"], 100 * r["discard_lt8"], r["tog"], r["tog_hard"],
        r["xing"], r["xing_0-5"], r["xing_5-10"]))
# freeze while the wheel accelerates toward the setpoint (the loop's own reaction): share of frozen hands-off frames
acc_tow = np.sign(alpha) == np.sign(err)
for nm, th1, th2 in RULES[:1] + RULES[4:5]:
    f = frz_rule(th1, th2) & ho & (np.abs(alpha) > 100)
    pr("  %-24s frozen hands-off frames with |alpha|>100 and the wheel accelerating TOWARD the setpoint: %.1f%% (n %.1f s)"
       % (nm, 100 * (f & acc_tow).sum() / max(f.sum(), 1), f.sum() / 100))

# =====================================================================================================================
# C. the fork's O1 override rule, on the fork's own frame axis (carState i-1 pairing, latActive)
# =====================================================================================================================
F = np.load(M.CACHE / "r79_fork.npz")
tco = F["t_co"]
jc = np.clip(np.searchsorted(F["t_cc"], tco, side="right") - 2, 0, len(F["t_cc"]) - 1)
lat = F["cc_latActive"][jc].astype(bool)
sh = lambda x: np.r_[x[:1], x[:-1]]  # noqa: E731
tq = np.abs(sh(F["cs_tq"].astype(float)))
prs = sh(F["cs_press"].astype(bool))
vv = sh(F["cs_vegoraw"].astype(float))


def hyst(on, off, lat):
    ev = np.full(len(on), -1, np.int8)
    ev[on] = 1
    ev[off] = 0
    ev[~lat] = 0
    idx = np.where(ev >= 0, np.arange(len(on)), -1)
    last = np.maximum.accumulate(idx)
    return np.where(last >= 0, ev[np.maximum(last, 0)], 0).astype(bool) & lat


def runlen_pos(mask):
    """position inside the current True-run (1-based), 0 where False -- vectorised."""
    m = np.asarray(mask, bool)
    k = np.arange(len(m))
    start = np.maximum.accumulate(np.where(m & ~np.r_[False, m[:-1]], k, 0))
    return np.where(m, k - start + 1, 0)


def o1_rule(kind, nd=6):
    if kind == "V298":
        return hyst(tq > 600, tq <= 500, lat)
    if kind == "steeringPressed":
        return hyst(tq > 1200, tq <= 1200, lat)
    if kind.startswith("deb"):
        pos = runlen_pos(tq > 600)
        on = (tq > 1200) | (pos >= nd)
        return hyst(on, tq <= 500, lat)
    raise KeyError(kind)


o1v = o1_rule("V298")
s_, e_ = runs(o1v)
epi_pressed = np.array([prs[a:b].any() for a, b in zip(s_, e_)])
pr("\nC. FORK O1 RULE (fork frame axis, carState i-1, latActive).  V298 reconstructed: %d episodes, %.1f s; pressed "
   "(hand) episodes %d (%.1f s), never-pressed (twist) %d (%.1f s)" % (
       len(s_), o1v.sum() / 100, epi_pressed.sum(), sum(b - a for a, b, p in zip(s_, e_, epi_pressed) if p) / 100,
       (~epi_pressed).sum(), sum(b - a for a, b, p in zip(s_, e_, epi_pressed) if not p) / 100))
C = {}
pr("  %-22s %6s %7s %14s %16s %18s %14s" % ("rule", "epis", "time s", "hand epis hit", "twist epis fire",
                                            "onset delay p50/p90", "O1 on hard %"))
hardF = lat & ((np.abs(sh(F["cs_ang"])) > 30) | (np.abs(sh(F["cs_rate"])) > 60))
for kind, nd in (("V298", 0), ("deb40", 4), ("deb60", 6), ("deb80", 8), ("deb100", 10), ("steeringPressed", 0)):
    o = o1_rule(kind, nd) if kind.startswith("deb") else o1_rule(kind)
    s2, e2 = runs(o)
    hit, fire, dly = 0, 0, []
    for a, b, p in zip(s_, e_, epi_pressed):
        seg = o[a:min(b + 15, len(o))]
        if p:
            if seg.any():
                hit += 1
                dly.append(int(np.argmax(seg)))
        else:
            if o[a:b].any():
                fire += 1
    dly = np.array(dly) * 10.0
    C[kind] = dict(epis=len(s2), time=o.sum() / 100, hand_hit=hit, twist_fire=fire,
                   delay_ms=[float(np.median(dly)) if len(dly) else None, float(np.percentile(dly, 90)) if len(dly) else None],
                   hard_share=float(o[hardF].mean()))
    pr("  %-22s %6d %7.1f %10d/%d %12d/%d %12.0f/%.0f ms %13.1f" % (
        kind, len(s2), o.sum() / 100, hit, epi_pressed.sum(), fire, (~epi_pressed).sum(),
        np.median(dly) if len(dly) else -1, np.percentile(dly, 90) if len(dly) else -1, 100 * o[hardF].mean()))

# =====================================================================================================================
# D. the limiter on HARD windows (recursive; only over windows) -- cap binding and clip excess, V298 vs V299 fork
# =====================================================================================================================
with __import__("contextlib").redirect_stdout(__import__("io").StringIO()):
    import m4_common as MC
cpj = json.loads(str(F["carparams_json"]))
steer_from_curv, vm = MC.vm_from_cp(cpj)
des = F["cc_ang"][jc].astype(float)
th_ = sh(F["cs_ang"].astype(float))
rate_ = sh(F["cs_rate"].astype(float))
v_ = np.maximum(vv, 1.0)
dmax_j = np.degrees(steer_from_curv(MC.MAX_LAT_JERK / v_ ** 2, v_)) * 0.01
amax = np.degrees(steer_from_curv(MC.MAX_LAT_ACCEL / v_ ** 2, v_))
EBP = np.array([3.1, 8.0, 10.0, 11.75, 17.5, 26.9])
EV298 = np.array([17.0, 15.5, 19.5, 17.0, 8.5, 4.5])
EV299 = np.array([35.0, 32.0, 19.5, 17.0, 8.5, 4.5])
win = dilate(hardF, 100) & lat
ws, we = runs(win)


def limiter(o1, cap, ebp_v):
    """returns (apply, stage flags: cap-bound, clip-bound, demand-beyond-clip) on the window frames."""
    capb = np.zeros(len(tco), bool)
    clipb = np.zeros(len(tco), bool)
    beyond = np.zeros(len(tco), bool)
    emax = np.interp(vv, EBP, ebp_v)
    dmax = np.minimum(dmax_j, cap)
    rel = np.r_[False, o1[:-1] & ~o1[1:]]
    for a, b in zip(ws, we):                         # windows only (hard +- 1 s), a few thousand frames in total
        last = th_[a]
        for i in range(a, b):
            if rel[i]:
                last = th_[i]
            r1 = min(max(des[i], last - dmax[i]), last + dmax[i])
            capb[i] = (abs(r1 - des[i]) > 1e-3) and not o1[i]   # the cap shapes the OUTPUT only when O1 is off
            r2 = min(max(r1, -amax[i]), amax[i])
            r3 = th_[i] + rate_[i] * 0.06 if o1[i] else r2
            beyond[i] = abs(des[i] - th_[i]) > emax[i]
            r4 = min(max(r3, th_[i] - emax[i]), th_[i] + emax[i])
            clipb[i] = (abs(r4 - r3) > 1e-3) and not o1[i]
            last = r4
    return capb, clipb, beyond


D = {}
hoF = hardF & ~dilate(prs, 50)
pr("\nD. FORK LIMITER on hard windows (%.1f s of window frames, recursive): share of HARD frames (and hands-off hard)"
   % (win.sum() / 100))
pr("  (cap/clip counted only on frames where O1 is OFF, i.e. where they shape the output)")
pr("  %-34s %10s %12s %10s %12s %12s %10s" % ("config", "cap bound", "cap (h-off)", "clip bound", "clip (h-off)",
                                          "<8 m/s cap h-off", "O1 on hard"))
for nm, o1k, cap, ev_ in (("V298: O1 600/500, cap 1.2, clip V298", "V298", 1.2, EV298),
                          ("O1 deb60, cap 1.2, clip V298", "deb60", 1.2, EV298),
                          ("V299: O1 deb60, cap 2.5, clip V299", "deb60", 2.5, EV299)):
    o = o1_rule(o1k, 6) if o1k.startswith("deb") else o1_rule(o1k)
    cb, kb, by = limiter(o, cap, ev_)
    lo8 = hoF & (vv < 8)
    D[nm] = dict(cap_hard=float(cb[hardF].mean()), cap_ho=float(cb[hoF].mean()), clip_hard=float(kb[hardF].mean()),
                 clip_ho=float(kb[hoF].mean()), cap_ho_lt8=float(cb[lo8].mean()))
    D[nm]["o1_hard"] = float(o[hardF].mean())
    pr("  %-34s %9.1f%% %11.1f%% %9.1f%% %11.1f%% %11.1f%% %9.1f%%" % (nm, 100 * cb[hardF].mean(), 100 * cb[hoF].mean(),
                                                          100 * kb[hardF].mean(), 100 * kb[hoF].mean(),
                                                          100 * cb[lo8].mean(), 100 * o[hardF].mean()))
wall = time.time() - T0
pr("\nwall %.1f s" % wall)
(OUT / "s1_hands_freeze_o1.txt").write_text("\n".join(LINES) + "\n", encoding="utf-8")
(OUT / "s1_hands_freeze_o1.json").write_text(json.dumps(dict(A=A, B=B, C=C, D=D, wall_s=wall), indent=1), encoding="utf-8")
