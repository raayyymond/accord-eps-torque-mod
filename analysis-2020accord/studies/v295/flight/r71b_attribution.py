# -*- coding: utf-8 -*-
"""r71b_attribution.py -- WIRE ATTRIBUTION of route 75604b0a432fdc89_00000071--a7b8ba5d9d (tag r71b_v294).

    python analysis-2020accord/studies/v295/flight/r71b_attribution.py          (~2-4 min; writes r71b_attribution_out.txt)

Sections (the brief's a-d):
  A  exposure: wall clock, duration, LATERAL engaged seconds by speed band, steeringPressed share, hands-off seconds
  B  fork: initData git + every Accord*/Steer*/lateral param, vs toggle-config_V294_accel-trim_r1.decoded.json; the runtime
     toggles (starpilotPlan.starpilotToggles); which controller ran; the 100 Hz Kp read (p/error); Ki (di / (error*dt));
     LAF used ((p+i+d+f)/-output); friction used (f minus its lateral-accel part); steer ratio used (angle-bin shape test);
     liveDelay; liveTorqueParameters
  C  firmware: (C1) the V293/V294 FF identity -- |427 tap| vs the IMAGE's surface(idx) x taper, all engaged and
     low-acceleration frames, two implementations (v293_lib.surface on V293 cells; the GOLDEN MODEL's
     lkas_rate_pid_surface on a Calibration built from V294 image cells); V282 cells as the negative control.
     (C2) THE PRE-REGISTERED TRIM-LIVE INSTRUMENT (HANDOFF-2026-09-23 item 2): byte-exact 1 kHz predictor on the route's
     own command, regressor Rm = output-lag replica of -d/dt LPF_2.03(rate) in deg/s^2, nuisance FF + dFF/dt (E3), 20 s
     hands-off windows; beta > +0.10 T counts per deg/s^2 = LIVE (expected +0.21), |beta| < 0.04 = NOT LIVE.  Plus: the
     port reproduced on the V293 null routes r75/r70 (null and synthetic-live), block-bootstrap CI, speed bands, and a
     model-selection read (tap vs the null and the live 1 kHz march).
  D  events: STEER_STATUS, carState faults, onroadEvents, 0x1AB OUTPUT_DISABLED, max |cmd|, share at the 0xE4 limit,
     slew-capped share, max wheel rate, max |tap|

FAIL / SURPRISE CRITERIA -- written BEFORE any number below was computed (2026-09-30):
  F1  attribution FAILS if the FF identity R^2 (V293 cells, best lag, engaged) < 0.90 or sign(tap) != +sign(cmd) on
      < 99 % -> "the wire says this is not a V293-FF image"; R^2 >= 0.95 with V282 cells -> a V282-class image.
  F2  the trim is NOT LIVE if E3 median |beta| < 0.04; LIVE if > +0.10; INVERTED if < -0.10 (-> the revert sentence);
      between = inconclusive.  The port must reproduce rp7b on r75_v293r4 (null |E3| < 0.04, synthetic live > +0.15)
      or its read on r71b is void.
  F3  fork mismatch: any r1-config key whose flown value differs from the file is LISTED; Kp read != SteerKP by > 1 %,
      or LAF read != SteerLatAccel by > 2 %, is a SURPRISE (a param back-fill or a code path the config did not ask for).
  F4  any STEER_STATUS != 0, any steerFault flag, any steerUnavailable/steerTempUnavailable event, or OUTPUT_DISABLED set
      while engaged = a FAULT to report loudly.
Everything is EVIDENCE (measured on this route's wire / read from the image) unless marked BELIEF.
ANALYSIS ONLY. Reads the cache, the rlog-derived kit caches and the images; sends nothing, flashes nothing.
"""
import contextlib
import io
import json
import math
import os
import sys
from dataclasses import replace

import numpy as np
from scipy import signal

KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "lib"))
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "grind"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "model"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import r71b_cache as RC  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    import v293_flight_read as FR  # noqa: E402

OUT = []
HERE = os.path.dirname(os.path.abspath(__file__))
R1 = os.path.join(KIT, "analysis-2020accord", "reference", "toggle-config_V294_accel-trim_r1.decoded.json")
BANDS = (("0-5", 0, 5), ("5-10", 5, 10), ("10-15", 10, 15), ("15-22", 15, 22), ("22+", 22, 99))


def pr(s=""):
    print(s, flush=True)
    OUT.append(str(s))


def lp1(xs, fc, fs=100.0):
    """rp7_v293_null.lp1, verbatim semantics (first-order IIR, state starts at xs[0])."""
    a = math.exp(-2 * math.pi * fc / fs)
    y = np.zeros_like(xs)
    s = xs[0]
    for i, v in enumerate(xs):
        s = a * s + (1 - a) * v
        y[i] = s
    return y


def runs(mask):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


# ======================================================================================================================
# A. EXPOSURE
# ======================================================================================================================
def section_a(D, G):
    pr("=" * 110)
    pr("A. EXPOSURE (wire) -- route 75604b0a432fdc89_00000071--a7b8ba5d9d, tag r71b_v294")
    pr("=" * 110)
    import datetime as dt
    M = D["meta"]
    ga = M["gps_anchor"]
    t_first, t_last = float(G["t"][0]), float(G["t"][-1])
    u0 = ga["unix_ms"] / 1e3 - (ga["t"] - t_first)
    u1 = u0 + (t_last - t_first)
    f = lambda u: dt.datetime.fromtimestamp(u, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")  # noqa: E731
    fp = lambda u: dt.datetime.fromtimestamp(u - 7 * 3600, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S PDT")  # noqa: E731
    pr("  wall clock (GPS anchor, seg 0 +%.1f s): %s -> %s   (%s -> %s; PDT = UTC-7 is BELIEF)"
       % (ga["t"] - t_first, f(u0), f(u1), fp(u0), fp(u1)))
    pr("  initData.wallTimeNanos reads %s -- the device clock was NOT synced at boot; ignore it"
       % f(M["init"]["wallTimeNanos"] / 1e9))
    pr("  duration %.1f s (first..last 0x18F frame), %d segments %s, contiguous (gaps %s ms)"
       % (t_last - t_first, len(M["segments"]), M["segments"],
          sorted({round(1000 * (M["seg_spans"][str(b)]["lo_can"] - M["seg_spans"][str(a)]["hi"])) for a, b in
                  zip(M["segments"], M["segments"][1:])})))
    dtf = np.diff(G["t"], append=G["t"][-1] + 0.01)
    dtf = np.clip(dtf, 0, 0.05)
    eng = G["eng"]
    v = G["cs_vego"]
    press = np.nan_to_num(G["cs_pressed"]) > 0.5
    bar = G["s18_tq_raw"] * 1.024
    handsoff_b = eng & (np.abs(bar) < 400)
    pr("  LATERALLY ENGAGED (0xE4 STEER_REQUEST & 0x18F SCA): %.1f s = %.1f %% of the route; carControl.latActive %.1f s;"
       " both %.1f s" % (dtf[eng].sum(), 100 * dtf[eng].sum() / dtf.sum(), dtf[G["eng_ctl"]].sum(),
                          dtf[eng & G["eng_ctl"]].sum()))
    pr("  selfdriveState.enabled (longitudinal+lateral openpilot) %.1f s ; always-on lateral means lateral runs without it"
       % dtf[np.nan_to_num(G["sd_enabled"]) > 0.5].sum())
    pr("  engaged: steeringPressed share %.3f ; hands-off (not pressed) %.1f s ; hands-off by |bar| < 400 %.1f s"
       % (press[eng].mean(), dtf[eng & ~press].sum(), dtf[handsoff_b].sum()))
    pr("  %-8s %10s %10s %10s %12s" % ("band m/s", "engaged s", "pressed", "hands-off", "|bar|<400 s"))
    rows = {}
    for nm, lo, hi in BANDS:
        m = eng & (v >= lo) & (v < hi)
        rows[nm] = dict(eng_s=float(dtf[m].sum()), pressed=float(press[m].mean()) if m.any() else np.nan,
                        handsoff_s=float(dtf[m & ~press].sum()), bar400_s=float(dtf[m & (np.abs(bar) < 400)].sum()))
        pr("  %-8s %10.1f %10.3f %10.1f %12.1f" % (nm, rows[nm]["eng_s"], rows[nm]["pressed"], rows[nm]["handsoff_s"],
                                                   rows[nm]["bar400_s"]))
    er = runs(eng)
    lens = np.array([(G["t"][b - 1] - G["t"][a]) for a, b in er]) if er else np.zeros(0)
    pr("  engaged episodes: %d, longest %.1f s, median %.1f s; max speed %.1f m/s; engaged speed p50/p90 %.1f / %.1f m/s"
       % (len(er), lens.max() if len(lens) else 0, np.median(lens) if len(lens) else 0, np.nanmax(v),
          np.nanpercentile(v[eng], 50), np.nanpercentile(v[eng], 90)))
    return dict(t_utc=(f(u0), f(u1)), dur=t_last - t_first, eng_s=float(dtf[eng].sum()), bands=rows,
                handsoff_s=float(dtf[eng & ~press].sum()), pressed=float(press[eng].mean()))


# ======================================================================================================================
# B. FORK
# ======================================================================================================================
SNAKE = {"AccordRatePlantFF": "accord_rate_plant_ff", "SteerKP": "steerKp", "AccordTorqueKi": "accord_torque_ki",
         "SteerFriction": "friction", "SteerLatAccel": "latAccelFactor", "ForceAutoTuneOff": "force_auto_tune_off",
         "ForceAutoTune": "force_auto_tune", "AdvancedLateralTune": None,
         "KeepLearnedLatAccelOffset": "keep_learned_lat_accel_offset", "AccordTurnFFTaper": "accord_turn_ff_taper",
         "AccordHoldMap": "accord_hold_map", "AccordFrictionHyst": "accord_friction_hyst",
         "AccordRateLoopGain": "accord_rate_loop_gain", "AccordErrorNotchQ": "accord_error_notch_q",
         "AccordRefFilter": "accord_ref_filter", "AccordTorqueKiHigh": "accord_torque_ki_high",
         "AccordDobHz": "accord_dob_hz", "AccordHoldLevel": "accord_hold_level",
         "AccordFrictionHystBand": "accord_friction_hyst_band", "AccordDither": "accord_dither",
         "AccordDitherGate": "accord_dither_gate", "AccordJerkLpHz": "accord_jerk_lp_hz",
         "AccordFFRateGain": "accord_ff_rate_gain", "AccordEpsGainScale": "accord_eps_gain_scale",
         "AccordEpsSpringScale": "accord_eps_spring_scale", "LaneCentering": "lane_centering",
         "SteerRatio": "steerRatio", "SteerDelay": "steerActuatorDelay", "UseAutoSteerDelay": "use_auto_steer_delay",
         "AccordVariableSteerRatio": "accord_variable_steer_ratio", "ForceTorqueController": "force_torque_controller",
         "LaneChangeTurnGate": "lane_change_turn_gate", "LaneChangeSmoothing": "lane_change_pace", "NNFF": "nnff",
         "NNFFLite": "nnff_lite"}


def _num(s):
    try:
        return float(s)
    except Exception:
        low = str(s).strip().lower()
        if low in ("true", "1"):
            return 1.0
        if low in ("false", "0"):
            return 0.0
        return None


def section_b(D, G):
    pr("")
    pr("=" * 110)
    pr("B. FORK -- what flew (initData, runtime toggles, and the control path's own arithmetic)")
    pr("=" * 110)
    M = D["meta"]
    I = M["init"]
    pr("  initData: gitCommit %s  branch %s  dirty %s  remote %s  commitDate %s  version %s  device %s"
       % (I["gitCommit"], I["gitBranch"], I["dirty"], I["gitRemote"], I["gitCommitDate"], I["version"], I["deviceType"]))
    pr("  (every one of the 17 segments' initData carries the same commit: %s)"
       % (len({x["gitCommit"] for x in M["init_per_segment"]}) == 1))
    P = I["params"]
    pr("  initData.params: %d keys.  Accord* / Steer* / lateral keys present:" % len(P))
    lat_keys = sorted(k for k in P if k.startswith(("Accord", "Steer")) or k in (
        "AdvancedLateralTune", "ForceAutoTune", "ForceAutoTuneOff", "KeepLearnedLatAccelOffset", "UseAutoSteerDelay",
        "LaneCentering", "LaneChangeTurnGate", "LaneChangeSmoothing", "ForceTorqueController", "NNFF", "NNFFLite",
        "LateralTune", "AlwaysOnLateral", "SteerDelay", "LiveDelay", "LateralDelay"))
    for k in lat_keys:
        pr("    %-28s = %s" % (k, P[k][:80]))
    r1 = json.load(open(R1))
    T = M["starpilot_toggles"]["first"]["toggles"] if M["starpilot_toggles"]["first"] else {}
    pr("  starpilotPlan.starpilotToggles (the RUNTIME toggle object controlsd reads): %d keys, %d changes during the route"
       % (len(T), len(M["starpilot_toggles"]["changes"])))
    pr("  vs toggle-config_V294_accel-trim_r1.decoded.json (%d keys):" % len(r1))
    pr("    %-26s %-10s %-22s %-22s %s" % ("key", "r1 file", "initData.params", "runtime toggle", "verdict"))
    diffs = []
    for k, want in r1.items():
        have = P.get(k)
        sk = SNAKE.get(k)
        rt = T.get(sk) if sk else None
        if isinstance(rt, list) and k == "SteerKP":
            rt = rt[1][0]
        w = float(want) if not isinstance(want, bool) else (1.0 if want else 0.0)
        h = _num(have) if have is not None else None
        r = _num(rt) if rt is not None else None
        ok_p = (h is not None and abs(h - w) < 1e-6)
        ok_r = (r is not None and abs(r - w) < 1e-6)
        if ok_p and (ok_r or rt is None):
            verdict = "MATCH"
        elif have is None and ok_r:
            verdict = "MATCH (param absent = default; runtime equal)"
        elif have is None and rt is None:
            verdict = "UNREADABLE (absent in both)"
        else:
            verdict = "DIFF"
            diffs.append((k, want, have, rt))
        pr("    %-26s %-10s %-22s %-22s %s" % (k, want, str(have)[:22], str(rt)[:22], verdict))
    pr("  -> %d difference(s) from the r1 file: %s" % (len(diffs), diffs if diffs else "NONE"))
    extra = {k: T.get(v) for k, v in SNAKE.items() if k not in r1 and v in T}
    pr("  context keys NOT in the r1 file (runtime values): %s" % extra)
    pr("  runtime: use_custom_latAccelFactor %s, use_custom_friction %s, use_custom_steerRatio %s (steerRatio %s),"
       " use_auto_steer_delay %s (steerActuatorDelay %s), nnff %s, force_torque_controller %s"
       % (T.get("use_custom_latAccelFactor"), T.get("use_custom_friction"), T.get("use_custom_steerRatio"),
          T.get("steerRatio"), T.get("use_auto_steer_delay"), T.get("steerActuatorDelay"), T.get("nnff"),
          T.get("force_torque_controller")))
    cp = M["carparams"]
    pr("  carParams: %s steerRatio %.3f steerActuatorDelay %.3f lateralTuning %s" % (
        cp["carFingerprint"], cp["steerRatio"], cp["steerActuatorDelay"], cp["lateralTuning"]))

    # ---- the control path's own arithmetic ------------------------------------------------------------------------
    ctl_which = D["ctl_which"]
    act = D["ctl_active"] > 0.5
    names = {0: "pid", 1: "angle", 2: "debug", 3: "torque", -1: "none"}
    wc = {names[int(w)]: int(((ctl_which == w) & act).sum()) for w in np.unique(ctl_which)}
    pr("  controlsState.lateralControlState on ACTIVE frames: %s  (spl.active frames %d)" % (wc, int((D["spl_active"] > 0.5).sum())))
    p, e, i_, d_, f_, o = D["ctl_p"], D["ctl_error"], D["ctl_i"], D["ctl_d"], D["ctl_f"], D["ctl_output"]
    m = act & (np.abs(e) > 0.01)
    kp = p[m] / e[m]
    pr("  Kp read (torqueState.p / error, %d active frames |error|>0.01): median %.5f  p1 %.5f  p99 %.5f"
       % (m.sum(), np.median(kp), np.percentile(kp, 1), np.percentile(kp, 99)))
    # Ki: di = ki * dt * error when not frozen and not clipped
    tcs = D["ctl_t"]
    press = np.interp(tcs, D["cs_t"], D["cs_pressed"]) > 0.5
    vv = np.interp(tcs, D["cs_t"], D["cs_vego"])
    unw = np.interp(tcs, D["spl_t"], D["spl_unwind"]) > 0.5
    sat = D["ctl_saturated"] > 0.5
    # rate-limited frames: |d carControl.torque| > 0.03/frame (the Honda STEER_DELTA cap; carOutput's |d| max is exactly 0.03)
    cct = np.interp(tcs, D["cc_t"], D["cc_torque"])
    lim = np.r_[False, np.abs(np.diff(cct)) > 0.03]
    di = np.r_[np.nan, np.diff(i_)]
    ok = act & np.r_[False, act[:-1]] & ~press & np.r_[False, ~press[:-1]] & (vv > 1.0) & ~unw & ~sat & ~lim & (np.abs(e) > 0.02)
    ki = di[ok] / (0.01 * e[ok])
    pr("  Ki read (di / (0.01*error), %d unfrozen frames): median %.4f  IQR [%.4f, %.4f]" % (
        ok.sum(), np.median(ki), np.percentile(ki, 25), np.percentile(ki, 75)))
    # LAF used: output_torque = (p+i+d+f)/LAF (linear torque_from_lateral_accel), logged output = -output_torque
    m2 = act & (np.abs(o) > 0.02) & ~sat
    laf = (p[m2] + i_[m2] + d_[m2] + f_[m2]) / (-o[m2])
    pr("  LAF read ((p+i+d+f) / -output, %d unsaturated frames |out|>0.02): median %.4f  p1 %.4f  p99 %.4f"
       % (m2.sum(), np.median(laf), np.percentile(laf, 1), np.percentile(laf, 99)))
    pr("  d term: max |d| on active frames %.2e (Kd %s)" % (np.nanmax(np.abs(d_[act])), "0" if np.nanmax(np.abs(d_[act])) == 0 else "!=0"))
    # friction used: f = des_curv*v^2 - roll*g*fade - offset*fade + friction_term
    roll = np.interp(tcs, D["lpar_t"], D["lpar_roll"])
    fade = np.interp(vv, [0.5, 2.5], [0.0, 1.0])
    ltp_off = np.interp(tcs, D["ltp_t"], D["ltp_off"])
    ltp_use = np.interp(tcs, D["ltp_t"], D["ltp_use"]) > 0.5
    base = D["ctl_des_curv"] * vv ** 2 - roll * 9.81 * fade
    fr0 = f_ - base
    m3 = act & (vv > 3)
    k3 = np.linalg.lstsq(np.vstack([np.ones(m3.sum()), ltp_off[m3] * fade[m3]]).T, fr0[m3], rcond=None)[0]
    fric = fr0 + np.where(ltp_use, ltp_off, 0.0) * fade
    pr("  f minus (desiredCurvature*v^2 - roll*g*fade): median %+.4f, p1 %+.4f, p99 %+.4f m/s^2; regressed on "
       "latAccelOffsetFiltered*fade: slope %+.3f intercept %+.4f; useParams frac %.2f" % (
           np.median(fr0[m3]), np.percentile(fr0[m3], 1), np.percentile(fr0[m3], 99), k3[1], k3[0], ltp_use[m3].mean()))
    pr("  friction term (offset restored when useParams): |.| p50 %.4f p90 %.4f p95 %.4f p99 %.4f m/s^2 -- a RELAY of plateau"
       " ~p95; opendbc get_friction scales it by LAF: SteerFriction %s x LAF %s = %.4f m/s^2 = %.4f torque = %.0f CAN counts"
       % (np.median(np.abs(fric[m3])), np.percentile(np.abs(fric[m3]), 90), np.percentile(np.abs(fric[m3]), 95),
          np.percentile(np.abs(fric[m3]), 99), T.get("friction"), T.get("latAccelFactor"),
          float(T.get("friction", 0)) * float(T.get("latAccelFactor", 0)), float(T.get("friction", 0)),
          float(T.get("friction", 0)) * 4096))
    pr("  friction plateau / LAF = %.4f torque (the flown SteerFriction read back from the relay's plateau)"
       % (np.percentile(np.abs(fric[m3]), 95) / float(T.get("latAccelFactor", 1))))
    pr("  starpilotLateralState: ff == torqueState.f on %.4f of active frames; lowSpeedFactor p50 %.3f; unwind frac %.3f;"
       " frictionThreshold p50 %.3f; dob max |.| %.2e" % (
           (np.mean(np.abs(D["spl_ff"][act] - f_[act]) < 1e-6) if len(D["spl_ff"]) == len(f_) else np.nan),
           np.median(D["spl_lsf"][D["spl_active"] > 0.5]), (D["spl_unwind"][D["spl_active"] > 0.5]).mean(),
           np.median(D["spl_fric_thr"][D["spl_active"] > 0.5]), np.nanmax(np.abs(D["spl_dob"]))))
    # liveDelay, liveTorqueParameters, liveParameters
    pr("  liveDelay.lateralDelay: p50 %.3f min %.3f max %.3f s; status %s; estimate p50 %.3f; blocks max %d" % (
        np.median(D["ldel_delay"]), D["ldel_delay"].min(), D["ldel_delay"].max(),
        {int(s): int((D["ldel_status"] == s).sum()) for s in np.unique(D["ldel_status"])},
        np.median(D["ldel_est"]), int(np.nanmax(D["ldel_blocks"]))))
    pr("  liveTorqueParameters: LAF filt p50 %.3f, offset filt p50 %+.3f (last %+.3f), friction filt p50 %.3f, liveValid %.2f,"
       " useParams %.2f  (LAF/friction NOT used: custom toggles; offset used only if useParams)" % (
           np.median(D["ltp_laf"]), np.median(D["ltp_off"]), D["ltp_off"][-1], np.median(D["ltp_fric"]),
           D["ltp_valid"].mean(), D["ltp_use"].mean()))
    pr("  liveParameters.steerRatio p50 %.3f (IGNORED for the Accord: the variable-ratio map runs); angleOffset p50 %+.3f deg;"
       " roll p50 %+.4f rad" % (np.median(D["lpar_sr"]), np.median(D["lpar_off"]), np.median(D["lpar_roll"])))
    # steer ratio shape test
    sr_bp = [0.0, 23.0, 31.0, 61.0, 76.0, 95.0, 116.0, 151.0, 178.0, 227.0, 236.0, 303.0, 380.0]
    sr_v = [16.88, 16.88, 16.88, 16.25, 15.97, 15.45, 15.03, 14.68, 14.45, 14.09, 14.25, 12.98, 12.31]
    lvl = float(T.get("steerRatio", 16.88)) / 16.88
    ang = np.interp(tcs, D["cs_t"], D["cs_angle"]) - np.interp(tcs, D["lpar_t"], D["lpar_off"])
    sa = np.radians(ang)
    curv_m = -D["ctl_curv"]
    pr("  STEER RATIO SHAPE TEST: q = (-controlsState.curvature)/rad(angle-offset) at 3-10 m/s; q*SR_map(angle) should be FLAT"
       " across angle bins if the variable map ran (level %.4f = %s/16.88); q*const flat if a constant ratio ran" % (lvl, T.get("steerRatio")))
    sel = (vv > 3) & (vv < 10) & (np.abs(ang) > 15) & np.isfinite(curv_m)
    q = curv_m[sel] / sa[sel]
    srm = np.interp(np.abs(ang[sel]), sr_bp, sr_v) * lvl
    bins = [15, 30, 60, 90, 130, 200, 400]
    rowsq = []
    for lo, hi in zip(bins, bins[1:]):
        b = (np.abs(ang[sel]) >= lo) & (np.abs(ang[sel]) < hi)
        if b.sum() < 20:
            continue
        rowsq.append((lo, hi, int(b.sum()), float(np.median(q[b] * srm[b])), float(np.median(q[b] * 16.84)),
                      float(np.median(srm[b]))))
    for r in rowsq:
        pr("    |angle| %3d-%3d deg  n=%5d   q*SR_map %.5f   q*16.84 %.5f   (SR_map %.2f)" % r)
    if rowsq:
        a1 = np.array([r[3] for r in rowsq]); a2 = np.array([r[4] for r in rowsq])
        pr("    spread (max/min - 1): variable map %.2f %%  vs constant ratio %.2f %%  -> %s" % (
            100 * (a1.max() / a1.min() - 1), 100 * (a2.max() / a2.min() - 1),
            "the VARIABLE map ran" if a1.max() / a1.min() < a2.max() / a2.min() else "a CONSTANT ratio fits better"))
    return dict(diffs=diffs, kp=float(np.median(kp)), ki=float(np.median(ki)), laf=float(np.median(laf)), which=wc,
                sr_rows=rowsq)


# ======================================================================================================================
# C. FIRMWARE
# ======================================================================================================================
def v294_calibration(c):
    """a golden-model Calibration built from the V294 IMAGE's cells (not from replace() constants)."""
    import eps_lkas_chain_model as M
    base = M.Calibration()
    cal = replace(base, fb_clamp=int(c["fb_clamp"]), fb_lag_a=int(c["fb_a"]), fb_lag_b=int(c["fb_b"]),
                  kp_x=tuple(int(x) for x in c["kp_X"]), kp_y=tuple(int(y) for y in c["kp_Y"]),
                  kd_x=tuple(int(x) for x in c["kd_X"]), kd_y=tuple(int(y) for y in c["kd_Y"]),
                  pid_d_clamp=int(c["d_clamp"]), pid_p_clamp=int(c["p_clamp"]), sum_clamp=int(c["sum_clamp"]),
                  out_clamp=int(c["t_clamp"]), out_lag_a=int(c["lag_a"]), out_lag_b=int(c["lag_b"]),
                  lkas_forward_gain=int(c["gain"]), pid_ki=int(c["ki"]),
                  assist_map_x=tuple(int(x) for x in c["map_X"]), assist_map_y=tuple(int(y) for y in c["map_Y"]),
                  e_shift=int(c["e_shift"]), fb_op=c["fb_op"])
    return M, cal


def march(sp_sign, idx, m, c, x1k=None, trim=False):
    """rp7b_dynamic_pred.march with EVERY constant read from the image cells c (V294) -- 1 kHz integer ZOH march."""
    LERP = np.array([int(np.interp(i, c["map_X"], c["map_Y"])) for i in range(241)])
    kp = int(c["kp_Y"][0]); sh = int(c["e_shift"]); fa, fb = int(c["fb_a"]), int(c["fb_b"]); fcl = int(c["fb_clamp"])
    pcl, scl, tcl = int(c["p_clamp"]), int(c["sum_clamp"]), int(c["t_clamp"])
    la, lb, gain = int(c["lag_a"]), int(c["lag_b"]), int(c["gain"])
    assert all(int(y) == kp for y in c["kp_Y"]) and all(int(y) == 0 for y in c["kd_Y"]) and int(c["ki"]) == 0
    n = len(idx) * 10
    T = np.zeros(n)
    s_fb = 0
    o = 0
    for i in range(n):
        k = i // 10
        sp = int(sp_sign[k]) * int(LERP[int(idx[k])])
        r26 = 0
        if trim:
            x = int(max(-12000, min(12000, x1k[i])))
            s_new = ((fa * s_fb) >> 10) + ((fb * x) >> 10)
            r26 = max(-fcl, min(fcl, s_new - s_fb)) if c["fb_op"] == "diff" else max(-fcl, min(fcl, s_new + s_fb))
            s_fb = s_new
        P = max(-pcl, min(pcl, (((sp << sh) - r26) * kp) >> 8))
        S = max(-scl, min(scl, (int(m[k]) * P) >> 8))
        o2 = ((la * o) >> 10) + ((S * lb) >> 10)
        y = (o + o2) >> 5
        o = o2
        T[i] = max(-tcl, min(tcl, (y * gain) >> 15))
    return T


def quant(T):
    return np.sign(T) * (np.abs(T).astype(np.int64) >> 3) * 8.0


def hp(x, fc, fs=100.0):
    b, a = signal.butter(2, fc / (fs / 2), "high")
    return signal.filtfilt(b, a, x)


def instrument(tag, c, win_s=20.0, synth=True, want_frames=False):
    """rp7b_dynamic_pred.analyse, ported with image-read constants; returns windows + frame arrays for pooled fits."""
    with contextlib.redirect_stdout(io.StringIO()):
        r = FR.load_route(tag, "V293")          # loads the v280 cache; cells replaced by c below
    g = r.g
    t100 = g["t"]; n100 = len(t100)
    m100 = FR.fade_multiplier(c, g["bar"], g["vego"], "bar")[:n100]
    idx100, sgn100 = FR.GI.demand_live(np.round(g["cmd"]), g["bar"], c)
    idx100 = np.clip(np.round(idx100[:n100]), 0, 240).astype(int)
    sgn = (-np.asarray(sgn100[:n100])).astype(int)
    Tn = march(sgn, idx100, m100, c)
    t_tap, T_tap = g["T_t"], g["T"]
    keep = (t_tap > t100[0]) & (t_tap < t100[n100 - 1])
    t_tap, T_tap = t_tap[keep], T_tap[keep]
    j100 = np.clip(np.searchsorted(t100[:n100], t_tap, side="right") - 1, 0, n100 - 1)
    sub = np.clip(np.round((t_tap - t100[j100]) * 1000).astype(int), 0, 9)
    tick_of = lambda d: np.clip(10 * j100 + sub + d, 0, len(Tn) - 1)  # noqa: E731
    eng = g["eng"][:n100][j100] & (np.abs(g["bar"][:n100][j100]) < 400)
    best = None
    for d in range(-40, 61, 2):
        for sg in (+1, -1):
            res = T_tap - sg * quant(Tn[tick_of(d)])
            v = np.var(res[eng])
            if best is None or v < best[0]:
                best = (v, d, sg)
    _, dms, sg = best
    ticks = tick_of(dms)
    pred_dyn = sg * Tn[ticks]
    res_null = T_tap - pred_dyn
    pred100, _ = FR.predict_tap(c, idx100, np.asarray(sgn100[:n100]), m100)
    wire = np.nan_to_num(g["wire"][:n100]) / 8.0
    best_pol = None
    for s in (+1, -1):
        acc = np.gradient(lp1(s * wire, 15.0)) * 100
        a_, b_ = hp(sg * Tn[::10][:n100], 3.0), hp(acc, 3.0)
        e_ = g["eng"][:n100]
        cc = [np.corrcoef(a_[:n100 - L][e_[:n100 - L]], b_[L:][e_[:n100 - L]])[0, 1] for L in range(0, 8)]
        pk = cc[int(np.argmax(np.abs(cc)))]
        if best_pol is None or pk > best_pol[1]:
            best_pol = (s, pk, int(np.argmax(np.abs(cc))))
    s_x, pol_c, pol_lag = best_pol
    x_up = signal.resample_poly(s_x * wire * 8.0, 10, 1)[:n100 * 10]
    Tl = march(sgn, idx100, m100, c, x1k=np.round(x_up), trim=True)
    Ti = march(sgn, idx100, m100, c, x1k=-np.round(x_up), trim=True)   # SIGN CONTROL: the trim with x inverted
    trim_inv = sg * (quant(Ti[ticks]) - quant(Tn[ticks]))
    trim_delta = sg * (quant(Tl[ticks]) - quant(Tn[ticks]))        # the modelled trim as the tap would carry it
    trim_delta_raw = sg * (Tl[ticks] - Tn[ticks])
    tap_live = T_tap + trim_delta
    res_live = tap_live - pred_dyn
    lr = lp1(wire, -math.log(int(c["fb_a"]) / 1024) / (2 * math.pi * 1e-3))
    R = -np.gradient(lr) * 100.0
    Rm = lp1(R, 5.05)
    dff = np.gradient(pred100) * 100.0
    out = []
    dd = np.diff(np.r_[0, eng.astype(int), 0])
    for a, b in zip(np.flatnonzero(dd == 1), np.flatnonzero(dd == -1)):
        nw = int(win_s * 50)
        for s0 in range(a, b - nw + 1, nw):
            sl = slice(s0 + 50, s0 + nw)
            jr = j100[sl]
            row = dict(v=float(np.mean(g["vego"][jr])), t=float(t_tap[s0] - t100[0]))
            for nm, y in (("null", res_null[sl]), ("live", res_live[sl]), ("model", trim_delta[sl])):
                X = np.column_stack([np.ones(len(y)), Rm[jr], pred_dyn[sl], dff[jr]])
                row[nm + "_E3"] = float(np.linalg.lstsq(X, y, rcond=None)[0][1])
                X = np.column_stack([np.ones(len(y)), R[jr]])
                row[nm + "_E1"] = float(np.linalg.lstsq(X, y, rcond=None)[0][1])
            out.append(row)
    res = dict(tag=tag, dms=dms, sg=sg, s_x=s_x, pol_c=pol_c, pol_lag=pol_lag, windows=out,
               resid_null=float(np.sqrt(np.mean(res_null[eng] ** 2))),
               resid_livepred=float(np.sqrt(np.mean((T_tap - pred_dyn - trim_delta)[eng] ** 2))))
    if want_frames:
        res.update(frames=dict(t=t_tap - t100[0], y=res_null, Rm=Rm[j100], R=R[j100], pred=pred_dyn, dff=dff[j100],
                               trim=trim_delta, trim_raw=trim_delta_raw, trim_inv=trim_inv, eng=eng, eng_all=g["eng"][:n100][j100],
                               v=g["vego"][:n100][j100], T=T_tap, cmd=g["cmd"][:n100][j100],
                               bar=g["bar"][:n100][j100], pred100=pred100, j100=j100, idx=idx100[j100]))
    return res


def boot_beta(F, mask, cols, block_s=10.0, nb=1000, seed=0):
    """pooled OLS of y on [1, Rm, pred, dff] over mask, CI by block bootstrap (blocks of block_s seconds)."""
    idx = np.flatnonzero(mask)
    if len(idx) < 500:
        return None
    X = np.column_stack([np.ones(len(idx))] + [F[k][idx] for k in cols])
    y = F["y"][idx]
    b0 = np.linalg.lstsq(X, y, rcond=None)[0][1]
    blk = np.floor(F["t"][idx] / block_s).astype(int)
    ub = np.unique(blk)
    groups = [np.flatnonzero(blk == u) for u in ub]
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(nb):
        pick = rng.integers(0, len(groups), len(groups))
        ii = np.concatenate([groups[p] for p in pick])
        bs.append(np.linalg.lstsq(X[ii], y[ii], rcond=None)[0][1])
    return dict(beta=float(b0), lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)), n=len(idx),
                n_blocks=len(groups), seconds=len(idx) / 50.0)


def section_c(D, G):
    pr("")
    pr("=" * 110)
    pr("C. FIRMWARE -- is this route V294, from the wire?")
    pr("=" * 110)
    c294 = RC.v294_cells()
    c293 = FR.cells_for("V293")
    c282 = FR.cells_for("V282")
    pr("  V294 image %s...: e_shift %d, fb_op %s, fb pole a %d (%.3f Hz), b %d, fb clamp %d, Kp %s, Kd %s, Ki %d, out lag %d/%d,"
       " gain %d, P/sum/T clamps %d/%d/%d" % (c294["_img_sha256"][:16], c294["e_shift"], c294["fb_op"], c294["fb_a"],
                                               -math.log(c294["fb_a"] / 1024) / (2 * math.pi * 1e-3), c294["fb_b"],
                                               c294["fb_clamp"], sorted(set(int(y) for y in c294["kp_Y"])),
                                               list(c294["kd_Y"]), c294["ki"], c294["lag_a"], c294["lag_b"], c294["gain"],
                                               c294["p_clamp"], c294["sum_clamp"], c294["t_clamp"]))
    same = all(np.array_equal(np.asarray(c294[k]), np.asarray(c293[k])) for k in ("map_X", "map_Y", "fadeB", "taperS", "taperO"))
    pr("  V294 vs V293 image: map / fade / setpoint-taper cells identical: %s ; V293 Kp %s, fb clamp %d" % (
        same, sorted(set(int(y) for y in c293["kp_Y"])), c293["fb_clamp"]))
    # ---- C1 FF identity ----------------------------------------------------------------------------------------------
    with contextlib.redirect_stdout(io.StringIO()):
        r = FR.load_route("r71b_v294", "V293")
        ib = FR.identity_block(r, [("V293", c293), ("V282", c282)])
    pr("  C1. FF IDENTITY (v293_flight_read.identity_block, |427 tap| vs surface(idx) x fade, zero free parameters, all"
       " laterally engaged tap frames, n=%d):" % ib["n_tap"])
    for k, row in ib["fits"].items():
        if row is None:
            continue
        pr("    %-14s best lag %+4.0f ms  R2 %+.4f  resid %6.1f counts  pearson %.4f  sign(T)==sign(pred) %.4f  n %d" % (
            k, row["lag_ms"], row["r2"], row["resid"], row["pearson"], row["sign_pred"], row["n"]))
    g = r.g
    # low-acceleration engaged frames, with the V293 cells at the best bar-mode lag
    best = ib["fits"]["V293/bar"]
    m100 = FR.fade_multiplier(c294, g["bar"], g["vego"], "bar")
    idx100, sgn100 = FR.GI.demand_live(np.round(g["cmd"]), g["bar"], c294)
    idx100 = np.round(idx100)
    pred293, _ = FR.predict_tap(c293, idx100, sgn100, m100)
    j = np.searchsorted(g["t"], g["T_t"], side="right") - 1
    ok = (j >= 0) & (j < len(g["t"]))
    jj = np.clip(j + best["lag_frames"], 0, len(g["t"]) - 1)
    wire = np.nan_to_num(g["wire"]) / 8.0
    lr = lp1(wire, 2.03)
    Racc = np.abs(np.gradient(lr) * 100.0)                      # |d/dt LPF_2.03(rate)| deg/s^2
    sel_all = ok & g["eng"][jj]
    rows = []
    for nm, thr in (("all engaged", 1e9), ("|acc|<50", 50), ("|acc|<20", 20), ("|acc|<10", 10)):
        sel = sel_all & (Racc[jj] < thr)
        y, yh = np.abs(g["T"][sel]), np.abs(pred293[jj[sel]])
        rows.append((nm, int(sel.sum()), FR.r2(y, yh), float(np.sqrt(np.mean((y - yh) ** 2))),
                     float(np.mean(np.sign(g["T"][sel]) == np.sign(g["cmd"][jj[sel]])))))
    pr("    by wheel acceleration (|d/dt LPF_2.03(rate)| deg/s^2, lag %+d ms):" % (best["lag_ms"]))
    for rw in rows:
        pr("      %-12s n %6d  R2 %.4f  resid %5.1f counts  sign(T)==+sign(cmd) %.4f" % rw)
    # second implementation: the GOLDEN MODEL's surface on a Calibration built from the V294 image cells, taper 254
    M, cal = v294_calibration(c294)
    tab = np.array([M.lkas_rate_pid_surface(i, cal)["T"] for i in range(241)], float)
    tab293 = np.array([FR.L.surface(c293, np.array([float(i)]), fb=0.0, fade=254.0)["T"][0] for i in range(241)])
    pr("    golden-model V294 surface (taper 254) vs v293_lib V293 surface: identical at %d/241 indices; max |diff| %d;"
       " rail T(240) = %d / %d" % (int(np.sum(np.abs(np.abs(tab) - np.abs(tab293)) == 0)),
                                   int(np.max(np.abs(np.abs(tab) - np.abs(tab293)))), tab[240], tab293[240]))
    import eps_lkas_chain_model as MM
    cal293 = replace(cal, e_shift=5, fb_op="sum", fb_clamp=int(c293["fb_clamp"]), fb_lag_a=int(c293["fb_a"]),
                     fb_lag_b=int(c293["fb_b"]), kp_y=tuple(int(y) for y in c293["kp_Y"]))
    tabg293 = np.array([MM.lkas_rate_pid_surface(i, cal293)["T"] for i in range(241)], float)
    pr("    golden V294 (image cells) vs golden V293 (image cells, e_shift 5 / Kp 120 / fb clamp 0): identical at %d/241"
       " indices (the FF identity, two images, one implementation); golden vs v293_lib closed form differ by <= 4"
       " counts = the closed-form lag vs the integer march, below the tap's 8-count LSB" % int(np.sum(tab == tabg293)))
    s254 = sel_all & (m100[jj] == 254) & (Racc[jj] < 20)
    yg = FR.tap_quantise(np.abs(tab[np.clip(idx100[jj[s254]].astype(int), 0, 240)]))
    pr("    golden-model predictor on taper-254, |acc|<20 frames: n %d  R2 %.4f  resid %.1f" % (
        s254.sum(), FR.r2(np.abs(g["T"][s254]), yg), float(np.sqrt(np.mean((np.abs(g["T"][s254]) - yg) ** 2)))))
    # ---- C2 the trim instrument -----------------------------------------------------------------------------------
    pr("")
    pr("  C2. THE PRE-REGISTERED TRIM-LIVE INSTRUMENT (HANDOFF-2026-09-23 item 2; port of rp7b_dynamic_pred.py with every"
       " constant read from the V294 image)")
    pr("      estimator E3: residual(tap - dynamic null predictor) ~ 1 + Rm + pred + dFF/dt ; Rm = lp1(-d/dt lp1(wire/8,"
       " 2.03 Hz), 5.05 Hz) [deg/s^2]; beta in T counts per deg/s^2; 20 s hands-off windows (|bar|<400)")
    pr("      PORT CONTROLS on the V293 null routes (must reproduce rp7b_out.txt: null E3 ~ +0.005, synthetic live ~ +0.20):")
    ctrl = {}
    for tag in ("r75_v293r4", "r70_v293"):
        try:
            o = instrument(tag, c294, synth=True)
            W = o["windows"]
            A = {k: np.array([w[k] for w in W]) for k in W[0]} if W else {}
            ctrl[tag] = o
            pr("        %-11s tap delta %+d ms sign %+d  x_tapconv %+d*wire (HP corr %+.2f)  %d windows  null E3 median %+.3f"
               " [%+.3f,%+.3f]  synthetic-live E3 median %+.3f [%+.3f,%+.3f]" % (
                   tag, o["dms"], o["sg"], o["s_x"], o["pol_c"], len(W), np.median(A["null_E3"]),
                   np.percentile(A["null_E3"], 5), np.percentile(A["null_E3"], 95), np.median(A["live_E3"]),
                   np.percentile(A["live_E3"], 5), np.percentile(A["live_E3"], 95)))
        except Exception as e:
            pr("        %s: FAILED %s" % (tag, str(e)[:160]))
    o = instrument("r71b_v294", c294, synth=True, want_frames=True)
    W = o["windows"]
    A = {k: np.array([w[k] for w in W]) for k in W[0]}
    pr("      r71b_v294: tap delta %+d ms, tap sign %+d, POLARITY x_tapconv = %+d * wire (HP corr %+.2f at %d ms); %d windows"
       % (o["dms"], o["sg"], o["s_x"], o["pol_c"], o["pol_lag"] * 10, len(W)))
    pr("      ** E3 (the pre-registered estimator) on the REAL tap: median %+.3f  5-95%% [%+.3f, %+.3f]  mean %+.3f"
       "  frac > +0.10: %.2f  frac < +0.04: %.2f" % (
           np.median(A["null_E3"]), np.percentile(A["null_E3"], 5), np.percentile(A["null_E3"], 95),
           np.mean(A["null_E3"]), np.mean(A["null_E3"] > 0.10), np.mean(np.abs(A["null_E3"]) < 0.04)))
    pr("         E3 on the MODELLED trim alone (what a live V294 would read on THIS route's excitation): median %+.3f"
       " [%+.3f, %+.3f]" % (np.median(A["model_E3"]), np.percentile(A["model_E3"], 5), np.percentile(A["model_E3"], 95)))
    pr("         E3 on real tap + a SECOND synthetic trim (live + live): median %+.3f" % np.median(A["live_E3"]))
    pr("         E1 (no nuisance, unfiltered R) real: median %+.3f" % np.median(A["null_E1"]))
    # windows list
    pr("      per-window (t route s, mean v, E3 real, E3 model):")
    for w in W:
        pr("        t %7.1f  v %5.1f  E3 %+.3f   model %+.3f" % (w["t"], w["v"], w["null_E3"], w["model_E3"]))
    F = o["frames"]
    F["t"] = F["t"]
    pooled = boot_beta(F, F["eng"], ["Rm", "pred", "dff"])
    pr("      POOLED E3 over all hands-off engaged tap frames, 10 s block bootstrap (1000): beta %+.3f  95%% CI [%+.3f, %+.3f]"
       "  (%.0f s, %d blocks)" % (pooled["beta"], pooled["lo"], pooled["hi"], pooled["seconds"], pooled["n_blocks"]))
    Fm = dict(F); Fm["y"] = F["trim"]
    pm = boot_beta(Fm, F["eng"], ["Rm", "pred", "dff"])
    pr("      POOLED E3 on the MODELLED trim (expected if live at design gain): beta %+.3f [%+.3f, %+.3f]" % (
        pm["beta"], pm["lo"], pm["hi"]))
    band_rows = {}
    for nm, lo, hi in BANDS:
        mb = F["eng"] & (F["v"] >= lo) & (F["v"] < hi)
        b = boot_beta(F, mb, ["Rm", "pred", "dff"], nb=500)
        bm = boot_beta(Fm, mb, ["Rm", "pred", "dff"], nb=200)
        band_rows[nm] = (b, bm)
        if b is None:
            pr("        band %-6s : < 10 s of hands-off engaged frames" % nm)
        else:
            pr("        band %-6s : beta %+.3f [%+.3f, %+.3f]  (%.0f s)   model %+.3f" % (
                nm, b["beta"], b["lo"], b["hi"], b["seconds"], bm["beta"] if bm else np.nan))
    # ratio-of-trim (scale) and model selection
    idx = np.flatnonzero(F["eng"])
    X = np.column_stack([np.ones(len(idx)), F["trim"][idx], F["pred"][idx], F["dff"][idx]])
    k = np.linalg.lstsq(X, F["y"][idx], rcond=None)[0]
    blk = np.floor(F["t"][idx] / 10.0).astype(int)
    groups = [np.flatnonzero(blk == u) for u in np.unique(blk)]
    rng = np.random.default_rng(1)
    bs = []
    for _ in range(500):
        ii = np.concatenate([groups[p] for p in rng.integers(0, len(groups), len(groups))])
        bs.append(np.linalg.lstsq(X[ii], F["y"][idx][ii], rcond=None)[0][1])
    pr("      SCALE: residual regressed on the MODELLED trim (+ FF nuisance): gain %+.3f  95%% CI [%+.3f, %+.3f]"
       "  (1 = live at the design gain, 0 = not live, <0 = inverted)" % (k[1], np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
    big = F["eng"] & (np.abs(F["trim_raw"]) >= 24)
    rn = np.sqrt(np.mean(F["y"][big] ** 2)); rl = np.sqrt(np.mean((F["y"] - F["trim"])[big] ** 2))
    ri = np.sqrt(np.mean((F["y"] - F["trim_inv"])[big] ** 2))
    pr("      SIGN CONTROL: the same march with the operand INVERTED (x = -x): rms(tap - inverted march) %.1f counts on those"
       " frames (null %.1f, correct sign %.1f)" % (ri, np.sqrt(np.mean(F["y"][big] ** 2)), np.sqrt(np.mean((F["y"] - F["trim"])[big] ** 2))))
    pr("      MODEL SELECTION on frames where the modelled trim is >= 24 counts (n %d, %.0f s): rms(tap - null march) %.1f"
       " vs rms(tap - live march) %.1f counts -> %s" % (big.sum(), big.sum() / 50.0, rn, rl,
                                                      "LIVE fits better" if rl < rn else "NULL fits better"))
    pr("      whole hands-off engaged: rms null %.1f, live %.1f counts" % (o["resid_null"], o["resid_livepred"]))
    return dict(ib=ib, rows=rows, E3=A["null_E3"], model_E3=A["model_E3"], pooled=pooled, pooled_model=pm,
                bands=band_rows, scale=(float(k[1]), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))),
                ctrl={t: dict(null=float(np.median([w["null_E3"] for w in v["windows"]])),
                              live=float(np.median([w["live_E3"] for w in v["windows"]]))) for t, v in ctrl.items()},
                ms=(float(rn), float(rl), int(big.sum())), pol=(o["s_x"], o["pol_c"]), dms=o["dms"], sg=o["sg"], F=F)


# ======================================================================================================================
# D. EVENTS
# ======================================================================================================================
def section_d(D, G):
    pr("")
    pr("=" * 110)
    pr("D. FAULTS, EVENTS, LIMITS")
    pr("=" * 110)
    M = D["meta"]
    eng = G["eng"]
    pr("  0x18F STEER_STATUS nibble: values %s over %d frames (0 = normal); CONFIG_INDEX %s" % (
        dict(zip(*[x.tolist() for x in np.unique(D["s18_status"], return_counts=True)])), len(D["s18_status"]),
        np.unique(D["s18_cfg"]).tolist()))
    pr("  carState steerFaultTemporary frames %d, steerFaultPermanent frames %d" % (
        int((D["cs_fault_tmp"] > 0.5).sum()), int((D["cs_fault_perm"] > 0.5).sum())))
    od = (D["tap_b2"] >> 6) & 1
    engt = RC.zoh(G["t"], eng.astype(float), D["tap_t"]) > 0.5
    pr("  0x1AB OUTPUT_DISABLED (byte 2 bit 6): set on %d of %d tap frames (%d while engaged)" % (
        int(od.sum()), len(od), int((od.astype(bool) & engt).sum())))
    pr("  onroadEvents message counts: %s" % M["onroad_event_msg_counts"])
    pr("  starpilotOnroadEvents counts: %s" % M["sp_onroad_event_msg_counts"])
    bad = [k for k in M["onroad_event_msg_counts"] if any(s in k.lower() for s in ("steer", "eps", "fault", "can", "lkas", "controls"))]
    pr("  steer/EPS/fault/CAN-class event names: %s" % bad)
    pr("  alerts (selfdriveState.alertType changes): %s" % [(round(a["t"] - D["t0"], 1), a["alertType"]) for a in M["alerts"] if a["alertType"]])
    pr("  pandaStates: controlsAllowed frac %.3f, safetyRxInvalid max %s, safetyTxBlocked max %s, faults max %s, rxChecksInvalid frames %d" % (
        D["panda_allowed"].mean(), np.nanmax(D["panda_rx_inv"]), np.nanmax(D["panda_tx_blk"]), np.nanmax(D["panda_nfaults"]),
        int((D["panda_rxchk_inv"] > 0.5).sum())))
    cmd = D["e4_cmd"]
    et = RC.zoh(G["t"], eng.astype(float), D["e4_t"]) > 0.5
    pr("  0xE4 STEER_TORQUE: max %+d  min %+d  max |cmd| engaged %d ; share of engaged frames |cmd| >= 4096 (the Bosch"
       " STEER_MAX, CarParams torqueV[-1] = 4096): %.4f (%d frames = %.2f s); >= 3840: %.4f" % (
           cmd.max(), cmd.min(), np.abs(cmd[et]).max(), np.mean(np.abs(cmd[et]) >= 4096), int((np.abs(cmd[et]) >= 4096).sum()),
           (np.abs(cmd[et]) >= 4096).sum() / 100.0, np.mean(np.abs(cmd[et]) >= 3840)))
    dcmd = np.abs(np.diff(cmd))
    la = D["cc_lat_active"] > 0.5
    dcc = np.abs(np.diff(D["cc_torque"]))
    pr("  slew: engaged 0xE4 frames with |d cmd| >= 120 counts/frame: %.4f ; latActive frames where the controller asked for"
       " |d torque| > 0.03/frame (the Honda STEER_DELTA cap, 123 counts) %.4f ; carOutput |d torque| max %.6f/frame (= the cap)"
       % (np.mean(dcmd[et[1:]] >= 120), np.mean(dcc[la[1:]] > 0.03), np.max(np.abs(np.diff(D["co_torque"])))))
    big = et & (np.abs(cmd) >= 4000)
    if big.any():
        tb = RC.zoh(D["tap_t"], D["tap_T"], D["e4_t"][big])
        bb = RC.zoh(D["s18_t"], D["s18_tq_raw"] * 1.024, D["e4_t"][big])
        vb = RC.zoh(D["cs_t"], D["cs_vego"], D["e4_t"][big])
        pb = RC.zoh(D["cs_t"], D["cs_pressed"], D["e4_t"][big])
        pr("  at |cmd| >= 4000 while engaged (%d frames): |tap| p50 %.0f max %.0f ; |bar| p50 %.0f ; v p50 %.1f m/s ; pressed %.2f"
           " (the tap is tapered by the driver-torque fade and the setpoint taper, so |cmd| at the limit does not reach the"
           " 2461 rail)" % (big.sum(), np.median(np.abs(tb)), np.max(np.abs(tb)), np.median(np.abs(bb)), np.median(vb), np.mean(pb)))
    pr("  wheel rate: max |steeringRateDeg| %.0f deg/s (engaged %.0f); p99 engaged %.0f; max |angle| %.0f deg (engaged %.0f)" % (
        np.max(np.abs(D["cs_rate"])), np.nanmax(np.abs(G["cs_rate"][eng])), np.nanpercentile(np.abs(G["cs_rate"][eng]), 99),
        np.max(np.abs(D["cs_angle"])), np.nanmax(np.abs(G["cs_angle"][eng]))))
    pr("  427 tap: max |T| %d counts (engaged %d; rail 2461 -> 2456 quantised); share of engaged tap frames at |T| >= 2456: %.4f ;"
       " tap nonzero while NOT engaged: %d frames (max |T| %d)" % (
           np.abs(D["tap_T"]).max(), np.abs(D["tap_T"][engt]).max(), np.mean(np.abs(D["tap_T"][engt]) >= 2456),
           int(((D["tap_T"] != 0) & ~engt).sum()), np.abs(D["tap_T"][~engt]).max() if (~engt).any() else 0))
    pr("  driver torque: max |steeringTorque| %.0f ; steeringPressed frames %d" % (np.max(np.abs(D["cs_torque"])), int((D["cs_pressed"] > 0.5).sum())))


def main():
    D = RC.load()
    G = RC.grid100(D)
    a = section_a(D, G)
    b = section_b(D, G)
    c = section_c(D, G)
    section_d(D, G)
    c.pop("F", None)
    json.dump(dict(a=a, b=dict((k, v) for k, v in b.items() if k != "sr_rows"), sr_rows=b["sr_rows"],
                   c=dict(E3=c["E3"].tolist(), model_E3=c["model_E3"].tolist(), pooled=c["pooled"],
                          pooled_model=c["pooled_model"], scale=c["scale"], ctrl=c["ctrl"], ms=c["ms"], pol=c["pol"],
                          bands={k: (v[0], v[1]) for k, v in c["bands"].items()}, rows=c["rows"])),
              open(os.path.join(HERE, "r71b_attribution_out.json"), "w"), indent=1, default=str)
    open(os.path.join(HERE, "r71b_attribution_out.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
