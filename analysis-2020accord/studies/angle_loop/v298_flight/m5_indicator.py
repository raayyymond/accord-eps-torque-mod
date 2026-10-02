# -*- coding: utf-8 -*-
"""m5_indicator.py -- M5: the on-screen torque/demand bar vs what the EPS did, route 79 (V298, first angle-loop flight).

ANALYSIS ONLY.  Reads the two route-79 caches (no rlog); writes JSON + a text dump under _scratch/out/r79/m5/.
Vectorised numpy; target < 30 s (measured wall time printed at the end).

The bar (fork Dom 2712e1336, selfdrive/ui/onroad/starpilot/torque_bar.py, TorqueBar._update_state, angle branch):
    a_act  = controlsState.curvature        * vEgo^2
    a_des  = controlsState.desiredCurvature * vEgo^2
    rollc  = liveParameters.roll * 9.81 * interp(vEgo, [5,15], [0,1])
    x      = clip(((a_act - rollc) + (a_des - a_act)) / CP.maxLateralAccel, -1, 1)   if carControl.latActive else 0
    bar    = FirstOrderFilter(rc 0.1 s, dt 1/fps) of x       (fps 60 non-tizi, 20 tizi; both ~0.1 s time constant)
  NOTE the a_act terms cancel: x = (a_des - rollc)/maxLatAccel.  Checked numerically below.

Units/signs (EVIDENCE from the drive-read docstring and the fork cache README):
  tap  0x1AB field (b0&3)<<8|b1, sign bit 9, |T|>>3 -> reported in field LSB = T/8 (rail 2461 T = 307.6 LSB)
  e    theta_sp - theta, theta_sp = -cmd/10 (0xE4 bus 129), theta = 0x14A ang (deg, + left)
  bt   0x18F STEER_TORQUE_SENSOR * 1.024 (kit wire bar torque); cs_tq = the unscaled field (fork override uses it)
  clip |co_ang - cs_ang| == ANGLE_ERROR_MAX(vEgoRaw) on latActive, not-override frames (carOutput row i pairs carState row i)
"""
import json
import os
import time

import numpy as np

T0 = time.perf_counter()
CACHE = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v280"
OUT = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/_scratch/out/r79/m5"
os.makedirs(OUT, exist_ok=True)

F = np.load(os.path.join(CACHE, "r79_fork.npz"))
W = np.load(os.path.join(CACHE, "r79_a1f5d2_al.npz"))
R = {}
G = 9.81  # opendbc ACCELERATION_DUE_TO_GRAVITY = 9.81


def zoh(ts, x, tg):
    """latest sample at or before tg (nan before the first)."""
    i = np.searchsorted(ts, tg, side="right") - 1
    y = np.asarray(x, float)[np.clip(i, 0, None)]
    return np.where(i >= 0, y, np.nan)


def winmean(ts, x, tg, w):
    """mean of samples in (tg - w, tg]; nan if empty -- cumsum, vectorised."""
    x = np.asarray(x, float)
    fin = np.isfinite(x)
    c = np.concatenate([[0.0], np.cumsum(np.where(fin, x, 0.0))])
    cn = np.concatenate([[0], np.cumsum(fin)])
    hi = np.searchsorted(ts, tg, side="right")
    lo = np.searchsorted(ts, tg - w, side="right")
    n = cn[hi] - cn[lo]
    return np.where(n > 0, (c[hi] - c[lo]) / np.maximum(n, 1), np.nan)


def winmaxabs(ts, x, tg, w):
    """max |x| in (tg - w, tg] for a strided grid: build per-sample index arrays (small windows)."""
    hi = np.searchsorted(ts, tg, side="right")
    lo = np.searchsorted(ts, tg - w, side="right")
    k = int(np.max(hi - lo)) if len(tg) else 0
    ax = np.nan_to_num(np.abs(np.asarray(x, float)), nan=-np.inf)
    idx = lo[:, None] + np.arange(max(k, 1))[None, :]
    ok = idx < hi[:, None]
    v = np.where(ok, ax[np.clip(idx, 0, len(ax) - 1)], -np.inf)
    m = v.max(axis=1)
    return np.where(np.isfinite(m), m, np.nan)


cp = json.loads(str(F["carparams_json"]))
MAXLA = float(cp["maxLateralAccel"])
R["carparams"] = dict(maxLateralAccel=MAXLA, steerControlType=cp.get("steerControlType"), brand=cp.get("brand"),
                      fingerprint=cp.get("carFingerprint"))
R["ctl_lat_is_angle_frac"] = float(np.mean(F["ctl_lat_is_angle"]))

# ---------------------------------------------------------------- 100 Hz bar on the controlsState rows (exact form)
tc = F["t_ctl"]
v_c = zoh(F["t_cs"], F["cs_vego"], tc)
roll_c = zoh(F["t_lp"], F["lp_roll"], tc)
a_act = F["ctl_curv"] * v_c ** 2
a_des = F["ctl_dcurv"] * v_c ** 2
rollc = roll_c * G * np.interp(v_c, [5, 15], [0.0, 1.0])
lat = F["cc_latActive"].astype(bool)  # carControl pairs controlsState row for row (README)
x_full = np.clip(((a_act - rollc) + (a_des - a_act)) / MAXLA, -1, 1)
x_red = np.clip((a_des - rollc) / MAXLA, -1, 1)
ok = np.isfinite(x_full)
R["cancel_check_max_abs_diff"] = float(np.nanmax(np.abs(x_full - x_red)))
x100 = np.where(lat, np.nan_to_num(x_full), 0.0)

# ---------------------------------------------------------------- 20 Hz analysis grid
tg = np.arange(np.ceil(tc[0] * 20) / 20, tc[-1], 0.05)
xg = zoh(tc, x100, tg)                    # what the UI sampled (latest message)
# UI filter rc 0.1 s; 60 fps -> continuous tau 0.1 s.  On the 20 Hz grid use the exact discrete equivalent of tau 0.1.
from scipy.signal import lfilter  # noqa: E402
a = 1 - np.exp(-0.05 / 0.1)
bar = lfilter([a], [1, -(1 - a)], np.nan_to_num(xg))
latg = zoh(F["t_cc"], lat.astype(float), tg) > 0.5
vg = zoh(F["t_cs"], F["cs_vego"], tg)
ades_g = zoh(tc, a_des, tg)
rollc_g = zoh(tc, rollc, tg)

# tap, 50 Hz native -> mean over the last 50 ms (signed) and max|.| over the last 50 ms
fld = ((W["b0"].astype(int) & 3) << 8) | W["b1"].astype(int)
tap = np.where(fld >= 512, -1.0, 1.0) * (fld & 511)   # LSB = T/8
t1ab = W["t1ab"]
tapg = winmean(t1ab, tap, tg, 0.05)
tapg_abs = winmaxabs(t1ab, tap, tg, 0.05)
# setpoint error at 100 Hz on the 0x14A instants, theta_sp held
th = W["ang"]
thsp = -zoh(W["te4"], W["cmd"], W["t14"]) / 10.0
req14 = zoh(W["te4"], W["req"], W["t14"]) > 0.5
e14 = thsp - th
eg = winmean(W["t14"], e14, tg, 0.05)
reqg = zoh(W["te4"], W["req"], tg) > 0.5
scag = zoh(W["t18"], W["sca"], tg) > 0.5
btg = winmean(W["t18"], W["tq"] * 1.024, tg, 0.05)

# error clip: carOutput row i vs carState row i
co, csa = F["co_ang"], F["cs_ang"]
n = min(len(co), len(csa))
co, csa = co[:n], csa[:n]
vraw = F["cs_vegoraw"][:n]
emax = np.interp(vraw, [3.1, 8.0, 10.0, 11.75, 17.5, 26.9], [17.0, 15.5, 19.5, 17.0, 8.5, 4.5])
lat_co = zoh(F["t_cc"], lat.astype(float), F["t_co"][:n]) > 0.5
# fork override O1 hysteresis on |cs_tq| (600 on / 500 off) -- vectorised forward fill of the last decisive event
aq = np.abs(F["cs_tq"][:n])
ev = np.where(aq > 600, 1, np.where(aq <= 500, 0, -1))
ev = np.where(lat_co, ev, 0)
last = np.maximum.accumulate(np.where(ev >= 0, np.arange(n), -1))
ovr = np.where(last >= 0, ev[np.clip(last, 0, None)], 0) == 1
dev = np.abs(co - csa)
ratio = dev / emax
clip = lat_co & ~ovr & (np.abs(dev - emax) < 1e-3)
R["clip_pairing_check"] = dict(
    lat_frames=int(lat_co.sum()), override_frames=int((lat_co & ovr).sum()),
    frac_lat_noovr_at_ratio_1=float(np.mean(clip[lat_co & ~ovr])),
    frac_lat_noovr_ratio_gt_1p001=float(np.mean(ratio[lat_co & ~ovr] > 1.001)),
    ratio_pcts_lat_noovr=[float(q) for q in np.percentile(ratio[lat_co & ~ovr], [50, 90, 95, 99])])
# second method for the clip: the controller's own command (cc_ang, pre-limiter) vs the measured angle, and the wire
cc_n = F["cc_ang"][:min(n, len(F["cc_ang"]))]
ccr = np.abs(zoh(F["t_cc"], F["cc_ang"], F["t_co"][:n]) - csa) / emax
w_e = np.abs(e14) / np.interp(zoh(F["t_cs"], F["cs_vegoraw"], W["t14"]), [3.1, 8, 10, 11.75, 17.5, 26.9],
                               [17, 15.5, 19.5, 17, 8.5, 4.5])
R["clip_second_method"] = dict(
    cc_minus_meas_over_emax_gt1_lat_noovr=float(np.mean(ccr[lat_co & ~ovr] > 1.0)),
    cc_minus_meas_over_emax_pcts=[float(q) for q in np.nanpercentile(ccr[lat_co & ~ovr], [50, 95, 99, 99.9])],
    co_ratio_max_lat_noovr=float(np.max(ratio[lat_co & ~ovr])),
    wire_err_over_emax_req_pcts=[float(q) for q in np.nanpercentile(w_e[req14], [50, 95, 99, 99.9, 100])],
    wire_err_over_emax_req_gt_0p95=float(np.mean(w_e[req14] > 0.95)))
clipg = winmaxabs(F["t_co"][:n], clip.astype(float), tg, 0.05) > 0.5
ratiog = winmaxabs(F["t_co"][:n], np.where(lat_co, ratio, 0.0), tg, 0.05)
ovrg = winmaxabs(F["t_co"][:n], ovr.astype(float), tg, 0.05) > 0.5

# ---------------------------------------------------------------- populations
A = latg & np.isfinite(tapg) & np.isfinite(eg) & np.isfinite(btg) & (vg > 3)
E = A & reqg & scag                       # EPS executing the angle loop (request 1, STEER_CONTROL_ACTIVE)
H = E & (np.abs(btg) < 500) & ~ovrg       # hands-off
R["pop_s"] = dict(latActive_v3=float(A.sum() / 20), eps_engaged=float(E.sum() / 20), hands_off=float(H.sum() / 20))
bands = [(3, 8), (8, 12.5), (12.5, 17.5), (17.5, 22), (22, 40)]


def frac(m, pop):
    return float(np.sum(m & pop) / max(np.sum(pop), 1))


def pears(x, y, m):
    x, y = x[m], y[m]
    if len(x) < 20:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def lagcorr(x, y, m, maxlag=20):
    """corr(x[t], y[t+L]) for L in [-maxlag, maxlag] samples (positive L: y lags x).  Returns (best L s, r, r@0)."""
    best = (0, 0.0)
    r0 = pears(x, y, m)
    rs = {}
    for L in range(-maxlag, maxlag + 1):
        if L >= 0:
            xx, yy, mm = x[:len(x) - L], y[L:], m[:len(m) - L] & m[L:]
        else:
            xx, yy, mm = x[-L:], y[:len(y) + L], m[-L:] & m[:len(m) + L]
        r = pears(xx, yy, mm)
        rs[L] = r
        if np.isfinite(r) and abs(r) > abs(best[1]):
            best = (L, r)
    return dict(best_lag_s=best[0] * 0.05, r_best=best[1], r0=r0)


# A. what the bar looked like
pin = np.abs(xg) >= 0.999
R["bar_shape"] = {}
for nm, pop in (("latActive", A), ("eps_engaged", E), ("hands_off", H)):
    d = dict(pinned_raw=frac(pin, pop), disp_ge_0p75_orange=frac(np.abs(bar) >= 0.75, pop),
             disp_lt_0p3=frac(np.abs(bar) < 0.3, pop))
    for lo, hi in bands:
        pb = pop & (vg >= lo) & (vg < hi)
        d["pinned_%g-%g" % (lo, hi)] = frac(pin, pb)
    R["bar_shape"][nm] = d
# the lateral accel at which the bar saturates, and roll's share
straight = E & (np.abs(ades_g) < 0.1)
R["roll"] = dict(straight_s=float(straight.sum() / 20),
                 straight_frac_bar_gt_0p3=frac(np.abs(bar) >= 0.3, straight),
                 straight_frac_bar_pinned=frac(pin, straight),
                 rollc_abs_pcts_engaged=[float(q) for q in np.nanpercentile(np.abs(rollc_g[E]), [50, 90, 99])],
                 ades_abs_pcts_engaged=[float(q) for q in np.nanpercentile(np.abs(ades_g[E]), [50, 75, 90, 99])],
                 roll_deg_pcts=[float(q) for q in np.degrees(np.nanpercentile(np.abs(F["lp_roll"]), [50, 90, 99]))])

# B. correlations (signed + magnitude), lag search +-1 s
R["corr"] = {}
for nm, pop in (("eps_engaged", E), ("hands_off", H)):
    R["corr"][nm] = dict(
        bar_vs_tap=lagcorr(bar, tapg, pop), absbar_vs_abstap=lagcorr(np.abs(bar), tapg_abs, pop),
        bar_vs_err=lagcorr(bar, eg, pop), absbar_vs_abserr=lagcorr(np.abs(bar), np.abs(eg), pop),
        absbar_vs_cliprat=lagcorr(np.abs(bar), ratiog, pop),
        bar_vs_bartq=lagcorr(bar, btg, pop), absbar_vs_absbartq=lagcorr(np.abs(bar), np.abs(btg), pop),
        # control: what the EPS-side signals say about each other
        tap_vs_err=lagcorr(tapg, eg, pop), abstap_vs_abserr=lagcorr(tapg_abs, np.abs(eg), pop),
        # what a sp-error/clip indicator would track vs the tap
        cliprat_vs_abstap=lagcorr(ratiog, tapg_abs, pop))
    # rank (Spearman) for magnitude, no lag
    from scipy.stats import spearmanr  # noqa: E402
    R["corr"][nm]["spearman_absbar_abstap"] = float(spearmanr(np.abs(bar[pop]), tapg_abs[pop]).statistic)
    R["corr"][nm]["spearman_abserr_abstap"] = float(spearmanr(np.abs(eg[pop]), tapg_abs[pop]).statistic)

# C. the mismatch, quantified
BIG = tapg_abs > 150
R["mismatch"] = {}
for nm, pop in (("eps_engaged", E), ("hands_off", H)):
    lo_bar = np.abs(bar) < 0.3
    hi_bar = np.abs(bar) >= 0.9
    work = BIG | clipg
    idle = (tapg_abs < 50) & ~clipg
    d = dict(
        P_tap_gt150=frac(BIG, pop), P_clip=frac(clipg, pop), P_work=frac(work, pop),
        bar_lt_0p3_and_work=frac(lo_bar & work, pop),
        P_bar_lt_0p3_given_work=float(np.sum(lo_bar & work & pop) / max(np.sum(work & pop), 1)),
        P_bar_lt_0p3_given_tap_gt150=float(np.sum(lo_bar & BIG & pop) / max(np.sum(BIG & pop), 1)),
        P_bar_lt_0p3_given_clip=float(np.sum(lo_bar & clipg & pop) / max(np.sum(clipg & pop), 1)),
        bar_ge_0p9_and_idle=frac(hi_bar & idle, pop),
        P_idle_given_bar_ge_0p9=float(np.sum(hi_bar & idle & pop) / max(np.sum(hi_bar & pop), 1)),
        P_bar_ge_0p9=frac(hi_bar, pop),
        # sign: when both are large, do they point the same way?
        sign_agree_tap_bar=float(np.mean(np.sign(bar[pop & BIG & (np.abs(bar) > 0.3)]) ==
                                         np.sign(tapg[pop & BIG & (np.abs(bar) > 0.3)]))) if np.any(pop & BIG & (np.abs(bar) > 0.3)) else None,
        n_both_big=int(np.sum(pop & BIG & (np.abs(bar) > 0.3))))
    for lo, hi in bands:
        pb = pop & (vg >= lo) & (vg < hi)
        d["band_%g-%g" % (lo, hi)] = dict(s=float(pb.sum() / 20), P_work=frac(work, pb),
                                          P_bar_lt_0p3_given_work=float(np.sum(lo_bar & work & pb) / max(np.sum(work & pb), 1)),
                                          P_idle_given_bar_ge_0p9=float(np.sum(hi_bar & idle & pb) / max(np.sum(hi_bar & pb), 1)),
                                          P_bar_pinned=frac(pin, pb))
    R["mismatch"][nm] = d

# C2. sensitivity at a quarter rail (the half-rail population is nearly empty on this route)
R["mismatch_quarter_rail"] = {}
for nm, pop in (("eps_engaged", E), ("hands_off", H)):
    Q = tapg_abs > 75
    R["mismatch_quarter_rail"][nm] = dict(
        P_tap_gt75=frac(Q, pop), s_tap_gt75=float(np.sum(Q & pop) / 20),
        P_bar_lt_0p3_given_tap_gt75=float(np.sum((np.abs(bar) < 0.3) & Q & pop) / max(np.sum(Q & pop), 1)),
        P_bar_ge_0p9_given_tap_gt75=float(np.sum((np.abs(bar) >= 0.9) & Q & pop) / max(np.sum(Q & pop), 1)),
        P_bar_ge_0p9_given_tap_lt25=float(np.sum((np.abs(bar) >= 0.9) & (tapg_abs < 25) & pop) /
                                          max(np.sum((tapg_abs < 25) & pop), 1)),
        bar_abs_pcts_given_tap_gt75=[float(q) for q in np.percentile(np.abs(bar[Q & pop]), [10, 50, 90])] if np.any(Q & pop) else None,
        bar_abs_pcts_given_tap_lt25=[float(q) for q in np.percentile(np.abs(bar[(tapg_abs < 25) & pop]), [10, 50, 90])])

# D. reference: in TORQUE mode the bar showed -actuatorsOutput.torque, which is the 0xE4 command (raw).  V294 (r71b)
#    wire cache: corr(|cmd|, |tap|) = what the old bar's magnitude tracked.  Single method; same 20 Hz construction.
try:
    V = np.load(os.path.join(CACHE, "r71b_v294.npz"))
    tgv = np.arange(np.ceil(V["te4"][0] * 20) / 20, V["te4"][-1], 0.05)
    fv = ((V["b0"].astype(int) & 3) << 8) | V["b1"].astype(int)
    tv = np.where(fv >= 512, -1.0, 1.0) * (fv & 511)
    tapv = winmean(V["t1ab"], tv, tgv, 0.05)
    cmdv = winmean(V["te4"], V["cmd"], tgv, 0.05)
    reqv = zoh(V["te4"], V["req"], tgv) > 0.5
    scav = zoh(V["t18"], V["sca"], tgv) > 0.5
    btv = winmean(V["t18"], V["tq"] * 1.024, tgv, 0.05)
    vv = zoh(V["tcs"], V["vego"], tgv)
    Ev = reqv & scav & np.isfinite(tapv) & np.isfinite(cmdv) & (vv > 3)
    Hv = Ev & (np.abs(btv) < 500)
    R["ref_v294_torque_mode"] = dict(
        engaged_s=float(Ev.sum() / 20),
        cmd_vs_tap=lagcorr(cmdv, tapv, Ev), abscmd_vs_abstap=lagcorr(np.abs(cmdv), np.abs(tapv), Ev),
        hands_off_cmd_vs_tap=lagcorr(cmdv, tapv, Hv))
except Exception as ex:  # noqa: BLE001
    R["ref_v294_torque_mode"] = dict(error=str(ex))

# E. candidate truthful indicators, scored on route 79 against the tap (the EPS's delivered lane torque)
#    (i) the tap itself / rail  (ii) error / clip  (iii) bar torque  -- each's corr with |tap| is the figure of merit
R["candidates"] = {}
for nm, pop in (("eps_engaged", E), ("hands_off", H)):
    R["candidates"][nm] = dict(
        err_over_clip_vs_abstap=lagcorr(np.abs(eg) / np.interp(vg, [3.1, 8, 10, 11.75, 17.5, 26.9],
                                                                [17, 15.5, 19.5, 17, 8.5, 4.5]), tapg_abs, pop),
        abserr_vs_abstap=lagcorr(np.abs(eg), tapg_abs, pop),
        absbartq_vs_abstap=lagcorr(np.abs(btg), tapg_abs, pop),
        abs_ades_vs_abstap=lagcorr(np.abs(ades_g), tapg_abs, pop))

# F. the same bar formula at other normalisations / without roll: is the SHAPE wrong or only the SCALE?
R["rescaled_bar"] = {}
for nm, pop in (("eps_engaged", E), ("hands_off", H)):
    d = {}
    for la in (MAXLA, 1.0, 2.0, 3.0, 3.589):
        for withroll in (True, False):
            xx = np.clip((ades_g - (rollc_g if withroll else 0.0)) / la, -1, 1)
            xx = lfilter([a], [1, -(1 - a)], np.nan_to_num(np.where(latg, xx, 0.0)))
            d["la%.3g_%s" % (la, "roll" if withroll else "noroll")] = dict(
                signed=pears(xx, tapg, pop), mag=pears(np.abs(xx), tapg_abs, pop),
                pinned=frac(np.abs(xx) >= 0.999, pop))
    R["rescaled_bar"][nm] = d
    # scale: least-squares |tap| (LSB) per |a_des| (m/s^2), through the origin, and its residual corr
    m = pop & np.isfinite(ades_g)
    k = float(np.sum(np.abs(ades_g[m]) * tapg_abs[m]) / np.sum(ades_g[m] ** 2))
    R["rescaled_bar"][nm]["tap_LSB_per_mps2"] = k
    R["rescaled_bar"][nm]["ades_at_tap150_mps2"] = 150.0 / k
    R["rescaled_bar"][nm]["ades_at_rail307_mps2"] = 307.6 / k

R["tap_pcts_engaged"] = [float(q) for q in np.percentile(tapg_abs[E], [50, 90, 99, 100])]
R["wall_s"] = time.perf_counter() - T0
json.dump(R, open(os.path.join(OUT, "m5.json"), "w"), indent=1, default=float)


def pp(d, ind=0):
    for k, v in d.items():
        if isinstance(v, dict):
            print(" " * ind + k)
            pp(v, ind + 2)
        else:
            print(" " * ind + "%s: %s" % (k, (("%.3f" % v) if isinstance(v, float) else v)))


pp(R)
print("WALL %.2f s" % R["wall_s"])
