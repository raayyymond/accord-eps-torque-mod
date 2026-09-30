# -*- coding: utf-8 -*-
"""h3_fork_replay.py -- HARD GATE H3a: the REAL fork LatControlTorque (Dom 20d24ab79) replayed on r71b's LOGGED inputs
must reproduce the logged torqueState p/i/f/output, carOutput torque and the 0xE4 count (CRITERIA-HARNESS.md H3a).

Inputs per controlsState frame k (previous-value sample at ctl_t[k], i.e. the newest message controlsd could hold):
  carState  vEgo, steeringAngleDeg, steeringRateDeg, steeringPressed
  liveParameters angleOffsetDeg, roll, stiffnessFactor, steerRatio
  liveTorqueParameters latAccelOffsetFiltered (KeepLearnedLatAccelOffset 1, useParams 1)
  liveDelay lateralDelay (+ LAT_SMOOTH_SECONDS 0.1)
  controlsState.desiredCurvature (= the clipped curvature controlsd passed to LaC.update)
  carControl.latActive
  steer_limited_by_safety: controlsd.publish's own rule, from the logged carControl/carOutput torque, updated only while
  selfdriveState.active (it is used on the NEXT frame)
Outputs saved to _scratch/h3_replay.npz for the port check (H3b).
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "lib"))
sys.path.insert(0, HERE)
import r71b_cache as RC  # noqa: E402
import fork_real as FK  # noqa: E402


def prev_idx(t_src, t_dst):
    return np.clip(np.searchsorted(t_src, t_dst, side="right") - 1, 0, len(t_src) - 1)


def r2(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return 1.0 - np.sum((a - b) ** 2) / max(np.sum((b - b.mean()) ** 2), 1e-30)


def matched_cs_index(D):
    """POST-HOC alignment (declared in V295-HARNESS.md): per controlsState frame, the carState sample among
    {prev-1, prev, prev+1} whose measurement -VM.calc_curvature(angle - offset)*v^2 (the port's curvature, which is
    bit-identical to the real VM -- h3b) equals the LOGGED actualLateralAccel after float32 rounding.  Frames where no
    candidate matches (inactive frames: la_act is not logged) keep the previous-value sample."""
    import v295_harness as H
    t = D["ctl_t"]
    ic0 = prev_idx(D["cs_t"], t)
    il = prev_idx(D["lpar_t"], t)
    port = H.ForkPort(1, D["meta"]["starpilot_toggles"]["first"]["toggles"])
    best, bestl = ic0.copy(), il.copy()
    found = np.zeros(len(t), bool)
    target = D["ctl_la_act"].astype(np.float32)
    for sh, shl in ((0, 0), (0, -1), (-1, 0), (1, 0), (-1, -1), (1, -1), (0, 1)):
        ic = np.clip(ic0 + sh, 0, len(D["cs_t"]) - 1)
        ill = np.clip(il + shl, 0, len(D["lpar_t"]) - 1)
        v = D["cs_vego"][ic]
        meas = port.curvature(D["cs_angle"][ic] - D["lpar_off"][ill], v, D["lpar_roll"][ill]) * v ** 2
        hit = (meas.astype(np.float32) == target) & ~found & (D["ctl_active"] > 0.5)
        best[hit] = ic[hit]
        bestl[hit] = ill[hit]
        found |= hit
    return (best, bestl), found


def inputs(D, cs_shift=0, ic_override=None):
    t = D["ctl_t"]
    ic = np.clip(prev_idx(D["cs_t"], t) + cs_shift, 0, len(D["cs_t"]) - 1) if ic_override is None else ic_override[0]
    il = prev_idx(D["lpar_t"], t) if ic_override is None else ic_override[1]
    it = prev_idx(D["ltp_t"], t)
    idl = prev_idx(D["ldel_t"], t)
    isd = prev_idx(D["sd_t"], t)
    ico = prev_idx(D["co_t"], t)
    return dict(t=t, v=D["cs_vego"][ic], ang=D["cs_angle"][ic], rate=D["cs_rate"][ic], pressed=D["cs_pressed"][ic] > 0.5,
                off=D["lpar_off"][il], roll=D["lpar_roll"][il], stiff=D["lpar_stiff"][il], sr=D["lpar_sr"][il],
                laf_off=D["ltp_off"][it], delay=D["ldel_delay"][idl] + 0.1, des_curv=D["ctl_des_curv"],
                active=D["cc_lat_active"] > 0.5, sd_active=D["sd_active"][isd] > 0.5, cc_torque=D["cc_torque"],
                co_torque_latest=D["co_torque"][ico])


def run(D, cs_shift=0, n=None, toggles=None, ic_override=None):
    I = inputs(D, cs_shift, ic_override)
    tg = toggles or D["meta"]["starpilot_toggles"]["first"]["toggles"]
    ctl = FK.RealController(tg)
    N = len(I["t"]) if n is None else n
    out = {k: np.zeros(N) for k in ("torque", "p", "i", "f", "output", "la_des", "la_act", "jerk", "error")}
    act = np.zeros(N, bool)
    lim = False
    for k in range(N):
        r = ctl.step(I["active"][k], I["v"][k], I["ang"][k], I["rate"][k], I["pressed"][k], I["off"][k], I["roll"][k],
                     I["des_curv"][k], I["delay"][k], I["laf_off"][k], lim, stiffness=I["stiff"][k], lp_sr=I["sr"][k])
        for kk in out:
            out[kk][k] = r[kk]
        act[k] = r["active"]
        if I["sd_active"][k]:                         # controlsd.publish: uses the logged CC/CO of this frame
            lim = abs(I["cc_torque"][k] - I["co_torque_latest"][k]) > 1e-2
    out["active"] = act
    return out, I


def main():
    D = RC.load(with_raw=False)
    t0 = time.time()
    # alignment probe: which carState sample did controlsd use?  la_act must be EXACT (it is a pure function of the
    # angle, offset, roll, speed and the SR map)
    best = None
    for sh in (-1, 0, 1):
        o, I = run(D, cs_shift=sh, n=6000)
        m = o["active"] & (D["ctl_active"][:6000] > 0.5)
        e = np.max(np.abs(o["la_act"][m] - D["ctl_la_act"][:6000][m])) if m.any() else np.inf
        print("  alignment probe cs_shift %+d: max|la_act sim - log| over %d active frames = %.3g" % (sh, m.sum(), e))
        if best is None or e < best[0]:
            best = (e, sh)
    sh = best[1]
    o, I = run(D, cs_shift=sh)
    dt_run = time.time() - t0
    print("REPLAY r71b, real LatControlTorque @%s -- (1) PRE-REGISTERED input alignment: previous-value carState, "
          "cs_shift %+d, %.1f s" % (FK.FORK_COMMIT, sh, dt_run))
    res = score(D, o)
    res["cs_shift"] = sh
    res["runtime_s"] = dt_run
    os.makedirs(os.path.join(HERE, "_scratch"), exist_ok=True)
    np.savez_compressed(os.path.join(HERE, "_scratch", "h3_replay.npz"), **{k: v for k, v in o.items()},
                        **{"in_" + k: np.asarray(v) for k, v in I.items()})
    # (2) POST-HOC: the carState sample identified per frame from the logged actualLateralAccel
    icm, found = matched_cs_index(D)
    act = D["ctl_active"] > 0.5
    ic0 = prev_idx(D["cs_t"], D["ctl_t"])
    il0 = prev_idx(D["lpar_t"], D["ctl_t"])
    print("\n(2) POST-HOC alignment: the (carState, liveParameters) samples identified from the logged "
          "actualLateralAccel on %.4f of active frames; carState differs from previous-value on %.4f, liveParameters "
          "(one message older) on %.4f of active frames"
          % (np.mean(found[act]), np.mean((icm[0] != ic0)[act]), np.mean((icm[1] != il0)[act])))
    o2, _ = run(D, ic_override=icm)
    res2 = score(D, o2)
    json.dump(dict(preregistered=res, posthoc_aligned=res2), open(os.path.join(HERE, "_scratch", "h3_replay.json"), "w"),
              indent=1, default=float)
    return res


def score(D, o):
    L = {k: D["ctl_" + k] for k in ("p", "i", "f", "output", "la_des", "la_act", "error")}
    L["jerk"] = D["ctl_jerk_des"]
    m = (D["ctl_active"] > 0.5) & o["active"]
    print("   %d frames, %d active in both" % (len(m), m.sum()))
    res = {}
    for k in ("output", "p", "i", "f", "la_des", "la_act", "jerk", "error"):
        a, b = o[k][m], L[k][m]
        res[k] = dict(r2=r2(a, b), rms=float(np.sqrt(np.mean((a - b) ** 2))), maxabs=float(np.max(np.abs(a - b))),
                      exact_frac=float(np.mean(np.abs(a - b) <= 1e-6 * np.maximum(1, np.abs(b)))))
        print("   %-7s R2 %.7f  rms %.3g  max|d| %.3g  exact(1e-6) %.4f" % (k, res[k]["r2"], res[k]["rms"], res[k]["maxabs"],
                                                                         res[k]["exact_frac"]))
    act_mis = int(np.sum((D["ctl_active"] > 0.5) != o["active"]))
    print("   active flag mismatches: %d" % act_mis)
    # carOutput: card applies the carControl of the PREVIOUS controlsd frame (measured: pairing each carOutput with
    # the carControl one frame before the newest one reproduces carOutput exactly on 99.94 % of frames; pairing with
    # the newest reproduces 0.4 %).  The SIM actuators.torque goes through that pairing and the Honda limiter.
    co_t = D["co_t"]
    j = np.searchsorted(D["cc_t"], co_t, side="right") - 2
    ok = j >= 0
    jj = np.clip(j, 0, None)
    lim_sim = np.zeros(len(co_t))
    can_sim = np.zeros(len(co_t), int)
    last = 0.0
    for k in range(len(co_t)):
        tq = o["torque"][jj[k]] if (ok[k] and D["cc_lat_active"][jj[k]] > 0.5) else 0.0
        last, can_sim[k] = FK.honda_rate_limit_and_can(tq, last)
        lim_sim[k] = last
    co_log, can_log = D["co_torque"], D["co_torque_can"]
    ma = ok & (D["cc_lat_active"][jj] > 0.5)
    res["co_torque"] = dict(r2=r2(lim_sim[ma], co_log[ma]), rms=float(np.sqrt(np.mean((lim_sim[ma] - co_log[ma]) ** 2))))
    dcan = np.abs(can_sim[ma] - can_log[ma])
    res["can"] = dict(within1=float(np.mean(dcan <= 1)), exact=float(np.mean(dcan == 0)), max=int(dcan.max()))
    # the controller's actuators.torque vs the logged carControl torque
    mc = D["cc_lat_active"] > 0.5
    res["cc_torque"] = dict(r2=r2(o["torque"][mc], D["cc_torque"][mc]),
                            rms=float(np.sqrt(np.mean((o["torque"][mc] - D["cc_torque"][mc]) ** 2))))
    print("   actuators.torque vs carControl: R2 %.7f rms %.3g" % (res["cc_torque"]["r2"], res["cc_torque"]["rms"]))
    print("   carOutput torque (rate-limited): R2 %.7f rms %.3g" % (res["co_torque"]["r2"], res["co_torque"]["rms"]))
    print("   0xE4 counts: exact %.4f, within +-1 %.4f, max |d| %d" % (res["can"]["exact"], res["can"]["within1"],
                                                                     res["can"]["max"]))
    gate = (res["output"]["r2"] >= 0.999 and res["output"]["rms"] <= 0.003 and
            all(res[k]["r2"] >= 0.995 for k in ("p", "i", "f")) and res["co_torque"]["r2"] >= 0.999 and
            res["can"]["within1"] >= 0.99)
    print("   H3a clauses: output R2>=0.999 %s, rms<=0.003 %s, p/i/f R2>=0.995 %s, carOutput R2>=0.999 %s, 0xE4 +-1 >= 99%% %s"
          % tuple("yes" if c else "NO" for c in (res["output"]["r2"] >= 0.999, res["output"]["rms"] <= 0.003,
                                                  all(res[k]["r2"] >= 0.995 for k in ("p", "i", "f")),
                                                  res["co_torque"]["r2"] >= 0.999, res["can"]["within1"] >= 0.99)))
    print("H3a", "PASS" if gate else "FAIL")
    res["gate"] = bool(gate)
    return res


if __name__ == "__main__":
    main()
