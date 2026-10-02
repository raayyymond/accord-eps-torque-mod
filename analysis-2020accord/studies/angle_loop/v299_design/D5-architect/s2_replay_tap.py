# -*- coding: utf-8 -*-
r"""s2_replay_tap.py -- D5-architect (V299 design round).  OPEN-LOOP lane replays on route 79's RECORDED wheel
(theta, rate, torque word): the lane torque each candidate rule set WOULD HAVE commanded on the recorded errors.

ENGINE: v298_flight/m3_lane.py (M3's integer-exact memoryless terms + event-driven integer I recursion + float output
lag; validated by M3 against the 0x1AB tap, R^2 0.928 at +10 ticks with the direction-2 ramp).  Variants:
  R0  V298 as built (control: must reproduce M3's R^2 against the measured tap)
  R1  V299 firmware rules (b): hard freeze 1229, opposing freeze removed, A3 low-speed 4096 cap removed (vcap 0)
  R2  R1 + the (b) FORK setpoint on hard windows: O1 debounce 60 ms, cap 2.5 deg/frame, clip V299, + LEAD
      tau_L(v) * w_f (w_f = 5-frame boxcar slope of the applied setpoint + 30 ms pole; tau_L = 0.7 * 89.5 / G(v) s)
  A1  (a) FIRMWARE: R1 + washout D (D on abe - abe_lp, abe_lp 1 kHz EMA tau 256 ms) + friction comp
      clamp((E' Kf) >> 8, +-Lf) with Kf 112 (= Kp, small-signal P x2), Lf 400 S (~64 T); fork = V299 O1/cap/clip, NO lead
ALL OPEN LOOP: the wheel is the one V298 produced.  A faster setpoint against that wheel inflates the error, so R2/A1
taps are an UPPER-BOUND-LIKE counterfactual for slews (BELIEF on what the closed loop would do; s4 runs closed loop).
ANALYSIS ONLY.  Vectorised (the I recursion is event-driven; the fork limiter runs only over hard windows).
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.signal import lfilter

T0 = time.time()
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
sys.path.insert(0, str(AL / "v298_flight"))
import m3_lane as M  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    import m4_common as MC  # noqa: E402
OUT = M.KIT / "_scratch" / "out" / "v299_D5"
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
    c = np.convolve(mask.astype(float), np.ones(2 * k + 1), "same")
    return c > 0.5


C = M.image_cells()
GL = M.glut(C["rows"])
W = M.load_wire()
th, cmd, tq, x, abe, vws = M.wire_inputs(W)
n = len(th)
eng = W["eng"]
t, v = W["t"], W["vego"]
r0_2, R_2 = M.ramp_ticks(eng, C["ramp_in2"], C["ramp_out2"])
QS = 10
TT, Ttap = W["T_t"], W["T"]

# ---------------------------------------------------------------------------------------------------------------------
# the fork side on its own axis: V299 setpoint on hard windows (O1 deb60, cap 2.5, clip V299) and the lead
# ---------------------------------------------------------------------------------------------------------------------
F = np.load(M.CACHE / "r79_fork.npz")
tco = F["t_co"]
jc = np.clip(np.searchsorted(F["t_cc"], tco, side="right") - 2, 0, len(F["t_cc"]) - 1)
lat = F["cc_latActive"][jc].astype(bool)
sh = lambda a: np.r_[a[:1], a[:-1]]  # noqa: E731
tqF = np.abs(sh(F["cs_tq"].astype(float)))
vv = sh(F["cs_vegoraw"].astype(float))
des = F["cc_ang"][jc].astype(float)
thF = sh(F["cs_ang"].astype(float))
rtF = sh(F["cs_rate"].astype(float))
co = F["co_ang"].astype(float)
import json as _j  # noqa: E402
steer_from_curv, vm = MC.vm_from_cp(_j.loads(str(F["carparams_json"])))
v_ = np.maximum(vv, 1.0)
dmax_j = np.degrees(steer_from_curv(MC.MAX_LAT_JERK / v_ ** 2, v_)) * 0.01
amax = np.degrees(steer_from_curv(MC.MAX_LAT_ACCEL / v_ ** 2, v_))
EBP = np.array([3.1, 8.0, 10.0, 11.75, 17.5, 26.9])
EV299 = np.array([35.0, 32.0, 19.5, 17.0, 8.5, 4.5])
GKN = np.array([1178.0, 1465.0, 760.0, 560.0, 1068.0, 2188.0])     # the GB-P table's G at the knots (image rows)
TAU_L = 0.7 * 89.5 / GKN                                             # s; D(S per wheel deg/s) / P(S per deg) x 0.7


def hyst(on, off, lat):
    ev = np.full(len(on), -1, np.int8)
    ev[on] = 1
    ev[off] = 0
    ev[~lat] = 0
    idx = np.where(ev >= 0, np.arange(len(on)), -1)
    last = np.maximum.accumulate(idx)
    return np.where(last >= 0, ev[np.maximum(last, 0)], 0).astype(bool) & lat


k = np.arange(len(tqF))
m6 = tqF > 600
start = np.maximum.accumulate(np.where(m6 & ~np.r_[False, m6[:-1]], k, 0))
pos = np.where(m6, k - start + 1, 0)
o1n = hyst((tqF > 1200) | (pos >= 6), tqF <= 500, lat)
hardF = lat & ((np.abs(thF) > 30) | (np.abs(rtF) > 60))
win = dilate(hardF, 100) & lat
ws, we = runs(win)
newsp = co.copy()
emax = np.interp(vv, EBP, EV299)
dmax = np.minimum(dmax_j, 2.5)
rel = np.r_[False, o1n[:-1] & ~o1n[1:]]
for a, b in zip(ws, we):                       # hard windows only (~16k frames)
    last = co[a - 1] if a > 0 else thF[a]
    for i in range(a, b):
        if rel[i]:
            last = thF[i]
        r1 = min(max(des[i], last - dmax[i]), last + dmax[i])
        r2 = min(max(r1, -amax[i]), amax[i])
        r3 = thF[i] + rtF[i] * 0.06 if o1n[i] else r2
        r4 = min(max(r3, thF[i] - emax[i]), thF[i] + emax[i])
        newsp[i] = r4
        last = r4
# the lead on the applied setpoint (fork axis), 5-frame boxcar slope (nulls the 20 Hz model staircase) + 30 ms pole
slope = np.r_[np.zeros(5), (newsp[5:] - newsp[:-5]) / 0.05]
slope = lfilter([1 - np.exp(-0.01 / 0.03)], [1, -np.exp(-0.01 / 0.03)], slope)
tauL = np.interp(vv, EBP, TAU_L)
o1v298 = hyst(tqF > 600, tqF <= 500, lat)
lead = np.where(lat & ~o1n, tauL * slope, 0.0)
sp_b = np.where(win, newsp, co) + lead
sp_b = np.where(lat, np.clip(sp_b, thF - np.interp(vv, EBP, EV299), thF + np.interp(vv, EBP, EV299)), co)
sp_a = np.where(win, newsp, co)                # (a): same fork limiter, no lead


def to_wire(sp_fork):
    """map a fork-axis setpoint change onto the wire grid (the 0xE4 the fork sends after carOutput i) -> cmd."""
    dlt = sp_fork - co
    j = np.clip(np.searchsorted(tco, t, side="right") - 1, 0, len(tco) - 1)
    thsp = np.nan_to_num(W["theta_sp"]) + np.where(eng, dlt[j], 0.0)
    raw = np.floor(-10.0 * thsp + 0.5)
    return np.clip(-4 * raw.astype(np.int64), -0x4000, 0x4000), thsp


cmd_b, thsp_b = to_wire(sp_b)
cmd_a, thsp_a = to_wire(sp_a)

# ---------------------------------------------------------------------------------------------------------------------
# lane variants
# ---------------------------------------------------------------------------------------------------------------------
def terms(cm):
    return M.lane_terms(C, th, cm, tq, x, abe, vws, eng, R_2, r0_2, GL, q_shift=QS)


def vw_ticks(L):
    return np.repeat(np.clip(vws[L["F"]], 0, 12000), 10)


def v299_freeze_bound(L):
    fr = (L["atq"] > 1229) | L["c4"]
    vw = vw_ticks(L) & 0xFFFF
    sh_ = np.where(vw <= 2880, 4, 6)
    bound = M.FL.s32((np.abs(L["th6"]) << sh_) + 1250)
    bound = np.where((vw <= 0) & (bound > 4096), 4096, bound)       # vcap 1382 -> 0: the cap only at standstill
    return fr, bound


def run_variant(L, fr, bound=None, D=None, Padd=None):
    L2 = dict(L)
    if bound is not None:
        L2["bound"] = bound
    if D is not None:
        L2["D"] = D
    if Padd is not None:
        L2["P"] = L["P"] + Padd
    Ia, a3s, clp, nev = M.i_recursion(L2, fr, a3=True, icl_s=C["icl"])
    T = M.output_T(C, L2, Ia, n)
    return T, Ia, a3s, L2


L0 = terms(cmd)
T_R0, I_R0, a3_R0, _ = run_variant(L0, L0["c1"] | L0["c2"] | L0["c4"])
fr1, bd1 = v299_freeze_bound(L0)
T_R1, I_R1, a3_R1, _ = run_variant(L0, fr1, bd1)
Lb = terms(cmd_b)
frb, bdb = v299_freeze_bound(Lb)
T_R2, I_R2, a3_R2, _ = run_variant(Lb, frb, bdb)
La = terms(cmd_a)
fra, bda = v299_freeze_bound(La)
# (a) washout D: abe_lp = 1 kHz EMA of abe (tau 256 ms = 2^8 ticks), D = clamp(6 (abe - abe_lp)); per marched tick
ab = La["D"] * 0                                                      # placeholder shape
abt = np.empty((La["m"], 10), np.int64)
kn = np.minimum(La["F"] + 1, n - 1)
abt[:, :9] = abe[La["F"]][:, None]
abt[:, 9] = abe[kn]
abt = abt.ravel().astype(float)
lp = np.zeros_like(abt)
for a_, b_ in zip(*runs(La["run"])):
    lp[a_:b_] = lfilter([1 / 256.0], [1, -(1 - 1 / 256.0)], abt[a_:b_], zi=[abt[a_] * (1 - 1 / 256.0)])[0]
Dw = np.clip(np.round(6.0 * (abt - lp)), -10240, 10240).astype(np.int64)
Pf = np.clip((La["Ep"] * 112) >> 8, -400, 400)                        # friction comp: Kf 112, Lf 400 S
T_A1, I_A1, a3_A1, _ = run_variant(La, fra, bda, D=Dw, Padd=Pf)


# ---------------------------------------------------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------------------------------------------------
def r2(y, yh):
    ss = np.sum((y - y.mean()) ** 2)
    return float(1 - np.sum((y - yh) ** 2) / ss) if ss > 0 else float("nan")


jj = np.clip(np.searchsorted(t, TT, side="right") - 1, 0, n - 1)
mt = eng[jj] & np.isfinite(Ttap) & (np.abs(W["bar"][jj]) < 500) & (W["tse"][jj] >= 1.2)
best = None
for lag in range(-2, 9):
    j2 = np.clip(np.searchsorted(t, TT - lag * 0.01, side="right") - 1, 0, n - 1)
    rr = r2(Ttap[mt] / 8, T_R0[j2[mt]] / 8)
    if best is None or rr > best[1]:
        best = (lag, rr)
LAG = best[0]
j2 = np.clip(np.searchsorted(t, TT - LAG * 0.01, side="right") - 1, 0, n - 1)
pr("s2 -- open-loop lane replays on route 79.  Control R0 (V298 rules) vs the 0x1AB tap: R^2 %.3f at lag %+d frames "
   "(hands-off |bar|<500, settled; M3's 0.928)" % (best[1], LAG))
sgn_dir = np.sign(np.corrcoef(T_R0[eng], np.nan_to_num(W["err"])[eng])[0, 1])
pr("  replayed T sign vs err (theta_sp - theta, + = left): corr sign %+d  -> T_left = %+d * T" % (sgn_dir, sgn_dir))
w18 = np.nan_to_num(W["w18"])
theta = np.nan_to_num(W["ang"])
hard = eng & ((np.abs(theta) > 30) | (np.abs(w18) > 60))
press = W["pressed"]
ho = eng & ~dilate(press, 50) & (np.abs(W["bar"]) < 600)
fast_ret = ho & (np.abs(w18) > 60) & (np.abs(theta) > 5) & (np.sign(w18) == -np.sign(theta))
fast_wind = ho & (np.abs(w18) > 60) & (np.abs(theta) > 5) & (np.sign(w18) == np.sign(theta))
lo8 = v < 8
RES = {}
pr("\n  %-44s %6s %6s %8s %10s %12s %14s %14s" % ("variant", "peak", "p99", "p99 hard", "p99 h-off", "I>4096S <6m/s",
                                                 "ret drive p50", "wind drive p50"))
meas_peak = np.nanmax(np.abs(Ttap[eng[jj]])) / 8
meas_p99 = np.nanpercentile(np.abs(Ttap[eng[jj]]), 99) / 8
meas_ph = np.nanpercentile(np.abs(Ttap[hard[jj]]), 99) / 8
pr("  %-44s %6.0f %6.0f %8.0f %10s %12s %14s %14s" % ("MEASURED tap (0x1AB, 50 Hz)", meas_peak, meas_p99, meas_ph,
                                                     "-", "-", "-", "-"))
for nm, T_, Ia in (("R0 V298 rules (control)", T_R0, I_R0), ("R1 V299 fw rules, recorded setpoint", T_R1, I_R1),
                   ("R2 (b): R1 + fork O1deb/cap2.5/clip/LEAD", T_R2, I_R2),
                   ("A1 (a): R1 + washout D + friction comp", T_A1, I_A1)):
    tl = T_ / 8.0
    Is = M.slot4(L0 if T_ is T_R0 or T_ is T_R1 else (Lb if T_ is T_R2 else La), Ia >> 7, n)
    big = (np.abs(Is) > 4096) & (v < 6) & eng
    drive = sgn_dir * tl * np.sign(w18)                  # + = the lane pushes along the wheel's motion
    RES[nm] = dict(peak=float(np.abs(tl[eng]).max()), p99=float(np.percentile(np.abs(tl[eng]), 99)),
                   p99_hard=float(np.percentile(np.abs(tl[hard]), 99)),
                   p99_hoh=float(np.percentile(np.abs(tl[hard & ho]), 99)) if (hard & ho).any() else None,
                   I_gt4096_lt6_s=float(big.sum() / 100),
                   ret_drive_p50=float(np.median(drive[fast_ret])) if fast_ret.any() else None,
                   ret_share_driving=float((drive[fast_ret] > 0).mean()) if fast_ret.any() else None,
                   wind_drive_p50=float(np.median(drive[fast_wind])) if fast_wind.any() else None,
                   ret_drive_p50_lt8=float(np.median(drive[fast_ret & lo8])) if (fast_ret & lo8).any() else None)
    r = RES[nm]
    pr("  %-44s %6.0f %6.0f %8.0f %10.0f %12.1f %8.0f (%.2f) %14.0f" % (
        nm, r["peak"], r["p99"], r["p99_hard"], r["p99_hoh"] or -1, r["I_gt4096_lt6_s"], r["ret_drive_p50"],
        r["ret_share_driving"], r["wind_drive_p50"]))
r2_R1 = r2(Ttap[mt] / 8, T_R1[j2[mt]] / 8)
pr("\n  instrument separation (the next drive's attribution test): R^2 vs the r79 tap  R0 %.3f  R1 %.3f  (R1's rules on "
   "V298's wire must score LOWER; on a V299 wire the order must invert)" % (best[1], r2_R1))
m_mid = mt & (np.abs(W["bar"][jj]) > 300)
pr("  ... restricted to 300 < |bar| < 500 hands-off frames (where the rule sets differ): R0 %.3f  R1 %.3f  (n %d)" % (
    r2(Ttap[m_mid & mt] / 8, T_R0[j2[m_mid & mt]] / 8) if (m_mid & mt).sum() > 50 else float("nan"),
    r2(Ttap[m_mid & mt] / 8, T_R1[j2[m_mid & mt]] / 8) if (m_mid & mt).sum() > 50 else float("nan"), int((m_mid & mt).sum())))
pr("  fast hands-off returns: %.1f s (%.1f s below 8 m/s); wind-ups %.1f s" % (fast_ret.sum() / 100,
                                                                             (fast_ret & lo8).sum() / 100,
                                                                             fast_wind.sum() / 100))
wall = time.time() - T0
pr("\nwall %.1f s" % wall)
(OUT / "s2_replay_tap.txt").write_text("\n".join(LINES) + "\n", encoding="utf-8")
(OUT / "s2_replay_tap.json").write_text(json.dumps(dict(res=RES, r2_R0=best[1], r2_R1=r2_R1, lag=LAG, wall_s=wall),
                                                   indent=1), encoding="utf-8")
