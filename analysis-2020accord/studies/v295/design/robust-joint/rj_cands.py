# -*- coding: utf-8 -*-
"""rj_cands.py -- lens robust-joint: the candidate generator (the joint knob space) and the per-candidate summary.

Parametrisation (all relative to V294, every cell read from the V294 IMAGE by the harness):
  g      feed-forward (sub-rail) gain multiplier  -> Kp = 960*g (flat) ; the P-clamp rail is unchanged (15360)
  t      HF trim multiplier = Kp*b / (960*567)    -> b = 567*t/g  (the trim's damping above its pole scales with t)
  f_fb   fb-lag pole, Hz                          -> a = round(1024 exp(-2 pi f / 1 kHz))
  f_lag  output-lag corner, Hz, DC held <= V294's -> (lag_a, lag_b)
  kd     Kd bank level (flat 4 knots) with D clamp 4096 and the SUM clamp cut 15360 -> 15240 so the rail cannot rise
  sched  Kp idx schedule shape: flat | lowboost (x s at idx <= 12, -> 1 by 40) | turnboost (x s at idx >= 56)
  e_shift is DERIVED: 2 (as built) unless b would exceed 0.95 b_max(a); then 1 (Kp x2, b /2), then 0  -> "opcode"
  C      fb clamp: 1024 unless given
ANALYSIS ONLY."""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rj_lin as RL  # noqa: E402
from rj_lin import H  # noqa: E402

BASE = None


def base():
    global BASE
    if BASE is None:
        BASE = H.Cells.v294()
    return BASE


def make(g=1.0, t=1.0, f_fb=None, f_lag=None, kd=0, sched="flat", s=1.25, C=1024, name=None, allow_opcode=True):
    b0 = base()
    a = b0.fb_a if f_fb is None else RL.fb_a_for(f_fb)
    kp = 960.0 * g
    bb = 567.0 * t / g
    e = 2
    bmax = (2 ** 31) * (1024 - a) / (12000.0 * a)
    while bb > 0.95 * bmax and e > 0 and allow_opcode:
        e -= 1
        kp *= 2
        bb /= 2
    if bb > 0.95 * bmax:
        return None
    kp = int(round(kp))
    bb = int(round(bb))
    if kp > 65535:
        return None
    if sched == "flat":
        kx, ky = b0.kp_x, (kp,) * 5
    elif sched == "lowboost":
        kx, ky = (0, 12, 40, 136, 208), (int(round(kp * s)), int(round(kp * s)), kp, kp, kp)
    elif sched == "turnboost":
        kx, ky = (0, 24, 56, 136, 208), (kp, kp, int(round(kp * s)), int(round(kp * s)), int(round(kp * s)))
    else:
        raise ValueError(sched)
    kw = dict(fb_a=a, fb_b=bb, fb_clamp=int(C), e_shift=e, kp_x=tuple(kx), kp_y=tuple(ky))
    if f_lag is not None:
        la, lb = RL.lag_pair(f_lag)
        kw.update(lag_a=la, lag_b=lb)
    if kd:
        kw.update(kd_y=(int(kd),) * 4, d_clamp=4096, sum_clamp=15240)
    nm = name or ("g%.2f_t%.2f_fb%s_lag%s_kd%d_%s%s_C%d" % (g, t, "%.2f" % f_fb if f_fb else "2.03",
                                                          "%.2f" % f_lag if f_lag else "5.05", kd, sched,
                                                          "%.2f" % s if sched != "flat" else "", C))
    return b0.replace(name=nm, **kw)


def summarise(ev, ev0):
    """condense a linear evaluation against V294's (same ctx).  Worst case over members unless named."""
    o, o0 = ev["outer"], ev0["outer"]
    gm_rel, ms_bad, gm_min, gm_lb_hwy = np.inf, 0.0, np.inf, np.inf
    for k, x in o.items():
        x0 = o0[k]
        lim = min(x0["GM"], 2.0)
        gm_rel = min(gm_rel, x["GM"] / lim)
        ms_bad = max(ms_bad, x["Ms"] / max(1.1 * x0["Ms"], 1.5))
        gm_min = min(gm_min, x["GM"])
        if k[0] == "light_b" and k[1] >= 17:
            gm_lb_hwy = min(gm_lb_hwy, x["GM"])
    jerk = {}
    for nm in RL.M_OUTER:
        r = [o[(nm, v, 40, True)]["jerk"] / o0[(nm, v, 40, True)]["jerk"] for v in (8.0, 12.0, 17.0)]
        jerk[nm] = float(np.exp(np.mean(np.log(r))))
    lo = {}
    hw = {}
    for nm in RL.M_OUTER:
        lo[nm] = float(np.mean([abs(1 - o[(nm, v, 10, True)]["track"]) - abs(1 - o0[(nm, v, 10, True)]["track"])
                                for v in (3.1, 5.0, 8.0)]))
        hw[nm] = float(np.mean([abs(1 - o[(nm, v, i, True)]["track"]) - abs(1 - o0[(nm, v, i, True)]["track"])
                                for v in (17.0, 26.9) for i in (10, 40)]))
    tr = {}
    for k, x in ev["track_cf"].items():
        tr[k] = x["R2"] - ev0["track_cf"][k]["R2"]
    S = dict(HF_P=ev["HF_P_ratio"], HF_T=ev["HF_T_ratio"], P20=ev["P20"], stress_rel=ev["stress_zeta_rel"],
             stress_min=ev["stress_zeta_min"], in_Ms=ev["in_Ms"], in_GM=ev["in_GM"], in_L13=ev["in_L13"],
             out_gm_rel=gm_rel, out_ms_bad=ms_bad, out_gm_min=gm_min, out_gm_lb_hwy=gm_lb_hwy,
             jerk_worst=max(jerk.values()), jerk_best=min(jerk.values()), jerk_nom=jerk["nominal"], jerk_lb=jerk["light_b"],
             loose_lo_worst=max(lo.values()), loose_lo_nom=lo["nominal"], loose_lo_lb=lo["light_b"],
             loose_hw_worst=max(hw.values()), loose_hw_nom=hw["nominal"], loose_hw_lb=hw["light_b"],
             track_worst=min(tr.values()), track_nom=float(np.mean([tr[("nominal", v)] for v in (8.0, 12.0, 17.0)])),
             track_R2_nom12=ev["track_cf"][("nominal", 12.0)]["R2"], track_slope_nom12=ev["track_cf"][("nominal", 12.0)]["slope"],
             ffdel_nom8=o[("nominal", 8.0, 10, True)]["ffdel"], track_nom8=o[("nominal", 8.0, 10, True)]["track"],
             track_nom17=o[("nominal", 17.0, 10, True)]["track"], track_lb27=o[("light_b", 26.9, 10, True)]["track"])
    feas = dict(
        H_HF1=S["HF_P"] <= 3.0 and S["HF_T"] <= 3.0,
        H_HF2=S["stress_rel"] >= 0.8,
        H_LOOP1=S["in_Ms"] <= 1.5 and S["in_GM"] > 1.0,
        H_LOOP2=S["out_gm_rel"] >= 0.95 and S["out_ms_bad"] <= 1.0)
    S["feasible"] = all(feas.values())
    S["fails"] = [k for k, v in feas.items() if not v]
    return S


def objective(S):
    """scalar, lower = better; each term ~0 at V294.  jerk: log ratio (worst member); loose: change of |1 - act/plan|
    at 0.1-0.3 Hz (worst member), low and highway; tracking: change of the 1-8 Hz complex-gain R^2 of alpha/cmd (worst)."""
    return (math.log(S["jerk_worst"]) + S["loose_lo_worst"] + S["loose_hw_worst"] - S["track_worst"])   # weights 1/1/1/1 as pre-registered
