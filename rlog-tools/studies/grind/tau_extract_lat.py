# -*- coding: utf-8 -*-
"""tau_extract_lat.py -- pull the LATERAL-IDENTIFICATION channels the v280 caches do not carry, for the
actuator-delay (tau) measurement.  Subagent taumeasure, 2026-09-13.

Analysis only.  Reads rlogs, writes an npz cache.  Builds nothing, sends nothing, flashes nothing.

The v280 caches carry only CAN + carState.vEgo.  The closed-loop-consistent identification needs the
EXOGENOUS command channel (the planner's desired curvature, which comes from the camera and the road,
not from the steering wheel) and an INDEPENDENT response channel (yaw rate).  Both are in the rlogs.

Channels, with the rate each is logged at on these routes:
  carControl      100 Hz  latActive, actuators.curvature (the COMMANDED curvature), actuators.torque,
                          currentCurvature, angularVelocity[2] (calibrated yaw rate as controlsd saw it)
  controlsState   100 Hz  desiredCurvature, curvature, and the whole torqueState: desiredLateralAccel,
                          actualLateralAccel, output, error, f/p/i, saturated
  carState        100 Hz  vEgo, steeringAngleDeg, steeringRateDeg, steeringPressed, steeringTorque
  livePose         20 Hz  angularVelocityDevice x/y/z + valid, inputsOK, posenetOK   (lagd's own input)
  liveCalibration   4 Hz  rpyCalib  (lagd calibrates the pose with this before taking yaw)
  liveDelay         4 Hz  lateralDelay, lateralDelayEstimate(+Std), validBlocks, status, calPerc
  liveParameters   20 Hz  steerRatio, stiffnessFactor, angleOffsetDeg
  modelV2          20 Hz  action.desiredCurvature  (the model's raw output, upstream of controlsd)
  cameraOdometry   20 Hz  rot[2]  (vision yaw rate -- an instrument independent of the IMU)
  gyroscope       ~93 Hz  raw gyro (highest-rate yaw instrument on the car)
  can                     0xE4 cmd/STEER_REQUEST (src 129) and 0x18F rate/SCA (src 1), to tie the
                          identification back to the wire the firmware sees

Run:  python rlog-tools/studies/grind/tau_extract_lat.py r39 r35 r6d r6e r6f r6c
Writes analysis-2020accord/_scratch/cache/tau/<TAG>_lat.npz
"""
import glob
import json
import os
import sys

import numpy as np
import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "tau")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
from cereal import log as clog  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# route prefix, cache TAG (matched to the v280 caches so the two can be joined), nominal segment count
ROUTES = {
    "r6c": ("75604b0a432fdc89_0000006c--2bc842dbac", "r6c", 62),
    "r6d": ("75604b0a432fdc89_0000006d--5e7b4d2ceb", "r6d_v292", 18),
    "r6e": ("75604b0a432fdc89_0000006e--64b4a5fef4", "r6e_v292", 23),
    "r6f": ("75604b0a432fdc89_0000006f--d876c761bc", "r6f_v292", 13),
    "r39": ("75604b0a432fdc89_00000039--f56039af87", "r39", 17),
    "r35": ("75604b0a432fdc89_00000035--580292087d", "r35", 20),
}
WANT_PARAMS = ["SteerDelay", "UseAutoSteerDelay", "AdvancedLateralTuning", "SteerRatio", "SteerFriction",
               "SteerLatAccel", "SteerKP", "AccordRatePlantFF", "AccordFFRateGain", "AccordTorqueKi",
               "AccordVariableSteerRatio", "ForceTorqueController", "ForceAutoTune", "AccordCurvatureLead",
               "AccordCurvatureLeadGain", "AccordTurnFFTaper", "AccordEpsGainScale", "AccordEpsSpringScale",
               "LateralTuning", "GitCommit", "GitBranch", "GitCommitDate"]


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 65536 if v >= 32768 else v


def resolve(prefix):
    """the route prefixes for the older routes are not all known; resolve by counter if need be."""
    segs = sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % prefix)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    if segs:
        return prefix, segs
    counter = prefix.split("--")[0]               # dongle_counter
    cand = sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % counter)))
    if not cand:
        return prefix, []
    real = "--".join(os.path.basename(cand[0]).split("--")[:2])
    segs = sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % real)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    return real, segs


def extract(key):
    prefix, tag, nseg = ROUTES[key]
    prefix, segs = resolve(prefix)
    if not segs:
        print("%s: NO SEGMENTS on disk for prefix %s" % (key, prefix), flush=True)
        return
    have = [int(os.path.basename(p).split("--")[2]) for p in segs]
    print("%s (%s) %d segments: %s" % (key, tag, len(segs), have), flush=True)

    C = {k: [] for k in (
        "t_cc", "lat_active", "cc_curv_cmd", "cc_torque", "cc_curv_now", "cc_yaw", "cc_enabled",
        "t_cs", "cs_des_curv", "cs_curv", "cs_la_des", "cs_la_act", "cs_out", "cs_err", "cs_f",
        "cs_p", "cs_i", "cs_sat", "cs_active",
        "t_cst", "vego", "sa_deg", "sr_deg", "spress", "storque",
        "t_lp", "lp_wx", "lp_wy", "lp_wz", "lp_valid", "lp_ok",
        "t_lc", "lc_r", "lc_p", "lc_y", "lc_valid",
        "t_ld", "ld_delay", "ld_est", "ld_std", "ld_blocks", "ld_status", "ld_cal",
        "t_lpar", "lpar_sr", "lpar_stiff", "lpar_ao",
        "t_mv", "mv_curv",
        "t_co", "co_rot_x", "co_rot_y", "co_rot_z",
        "t_gy", "gy_x", "gy_y", "gy_z",
        "t_e4", "cmd", "req", "t_18", "rate", "sca", "tq")}
    marks, params_dump, failed = [], None, []
    seg_lo = {}

    for p in segs:
        sn = int(os.path.basename(p).split("--")[2])
        with open(p, "rb") as fh:
            data = zstandard.ZstdDecompressor().stream_reader(fh).read()
        it = clog.Event.read_multiple_bytes(data)
        lo = None
        while True:
            try:
                evt = next(it)
            except StopIteration:
                break
            except Exception as e:
                failed.append(dict(seg=sn, err=str(e)[:120])); break
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if lo is None:
                lo = tm
            try:
                if w == "carControl":
                    m = evt.carControl
                    C["t_cc"].append(tm); C["lat_active"].append(1 if m.latActive else 0)
                    C["cc_curv_cmd"].append(m.actuators.curvature); C["cc_torque"].append(m.actuators.torque)
                    C["cc_curv_now"].append(m.currentCurvature)
                    C["cc_yaw"].append(m.angularVelocity[2] if len(m.angularVelocity) > 2 else np.nan)
                    C["cc_enabled"].append(1 if m.enabled else 0)
                elif w == "controlsState":
                    m = evt.controlsState
                    C["t_cs"].append(tm); C["cs_des_curv"].append(m.desiredCurvature)
                    C["cs_curv"].append(m.curvature)
                    lcs = m.lateralControlState
                    st = getattr(lcs, lcs.which())
                    C["cs_la_des"].append(getattr(st, "desiredLateralAccel", np.nan))
                    C["cs_la_act"].append(getattr(st, "actualLateralAccel", np.nan))
                    C["cs_out"].append(getattr(st, "output", np.nan))
                    C["cs_err"].append(getattr(st, "error", np.nan))
                    C["cs_f"].append(getattr(st, "f", np.nan)); C["cs_p"].append(getattr(st, "p", np.nan))
                    C["cs_i"].append(getattr(st, "i", np.nan))
                    C["cs_sat"].append(1 if getattr(st, "saturated", False) else 0)
                    C["cs_active"].append(1 if getattr(st, "active", False) else 0)
                elif w == "carState":
                    m = evt.carState
                    C["t_cst"].append(tm); C["vego"].append(m.vEgo)
                    C["sa_deg"].append(m.steeringAngleDeg); C["storque"].append(m.steeringTorque)
                    C["spress"].append(1 if m.steeringPressed else 0)
                    try:
                        C["sr_deg"].append(m.steeringRateDeg)
                    except Exception:
                        C["sr_deg"].append(np.nan)
                elif w == "livePose":
                    m = evt.livePose
                    C["t_lp"].append(tm)
                    C["lp_wx"].append(m.angularVelocityDevice.x); C["lp_wy"].append(m.angularVelocityDevice.y)
                    C["lp_wz"].append(m.angularVelocityDevice.z)
                    C["lp_valid"].append(1 if m.angularVelocityDevice.valid else 0)
                    C["lp_ok"].append(1 if (m.inputsOK and m.posenetOK) else 0)
                elif w == "liveCalibration":
                    m = evt.liveCalibration
                    r = list(m.rpyCalib) if len(m.rpyCalib) >= 3 else [np.nan] * 3
                    C["t_lc"].append(tm); C["lc_r"].append(r[0]); C["lc_p"].append(r[1]); C["lc_y"].append(r[2])
                    C["lc_valid"].append(1 if str(m.calStatus) in ("calibrated", "1") else 0)
                elif w == "liveDelay":
                    m = evt.liveDelay
                    C["t_ld"].append(tm); C["ld_delay"].append(m.lateralDelay)
                    C["ld_est"].append(m.lateralDelayEstimate); C["ld_std"].append(m.lateralDelayEstimateStd)
                    C["ld_blocks"].append(m.validBlocks)
                    C["ld_status"].append({"unestimated": 0, "estimated": 1, "invalid": 2}.get(str(m.status), -1))
                    C["ld_cal"].append(m.calPerc)
                elif w == "liveParameters":
                    m = evt.liveParameters
                    C["t_lpar"].append(tm); C["lpar_sr"].append(m.steerRatio)
                    C["lpar_stiff"].append(m.stiffnessFactor); C["lpar_ao"].append(m.angleOffsetDeg)
                elif w == "modelV2":
                    C["t_mv"].append(tm)
                    try:
                        C["mv_curv"].append(evt.modelV2.action.desiredCurvature)
                    except Exception:
                        C["mv_curv"].append(np.nan)
                elif w == "cameraOdometry":
                    r = list(evt.cameraOdometry.rot)
                    C["t_co"].append(tm); C["co_rot_x"].append(r[0]); C["co_rot_y"].append(r[1]); C["co_rot_z"].append(r[2])
                elif w == "gyroscope":
                    s = evt.gyroscope
                    try:
                        v = list(s.gyroUncalibrated.v) if s.which() == "gyroUncalibrated" else list(s.gyro.v)
                    except Exception:
                        continue
                    if len(v) >= 3:
                        C["t_gy"].append(tm); C["gy_x"].append(v[0]); C["gy_y"].append(v[1]); C["gy_z"].append(v[2])
                elif w == "can":
                    for cm in evt.can:
                        d = bytes(cm.dat)
                        if cm.src == 1 and cm.address == 0x18F and len(d) >= 5:
                            C["t_18"].append(tm); C["tq"].append(i16be(d, 0)); C["rate"].append(i16be(d, 2))
                            C["sca"].append((d[4] >> 3) & 1)
                        elif cm.src == 129 and cm.address == 0x0E4 and len(d) >= 3:
                            C["t_e4"].append(tm); C["cmd"].append(i16be(d, 0)); C["req"].append((d[2] >> 7) & 1)
                elif w == "userBookmark":
                    marks.append(dict(seg=sn, mono=tm))
                elif w == "initData" and params_dump is None:
                    pd = {}
                    for e in evt.initData.params.entries:
                        if e.key in WANT_PARAMS:
                            try:
                                pd[e.key] = bytes(e.value).decode("utf-8", "replace")
                            except Exception:
                                pd[e.key] = repr(bytes(e.value)[:200])
                    pd["_seg"] = sn
                    params_dump = pd
            except Exception:
                continue
        seg_lo[sn] = lo
        print("   %s" % os.path.basename(p), flush=True)

    D = {k: np.asarray(v, dtype=float) for k, v in C.items() if len(v)}
    os.makedirs(CACHE, exist_ok=True)
    np.savez_compressed(os.path.join(CACHE, tag + "_lat.npz"), **D)
    meta = dict(tag=tag, prefix=prefix, segments=have, failed=failed, params=params_dump or {},
                marks=[dict(seg=m["seg"], mono=m["mono"]) for m in marks],
                t0=float(D["t_cc"][0]) if "t_cc" in D else None,
                counts={k: int(len(v)) for k, v in D.items()})
    with open(os.path.join(CACHE, tag + "_lat_meta.json"), "w") as fh:
        json.dump(meta, fh, indent=1, default=float)
    print("%s -> %s_lat.npz   carControl %d  controlsState %d  livePose %d  liveDelay %d  gyro %d"
          % (key, tag, len(D.get("t_cc", [])), len(D.get("t_cs", [])), len(D.get("t_lp", [])),
             len(D.get("t_ld", [])), len(D.get("t_gy", []))), flush=True)
    if params_dump:
        for k in WANT_PARAMS:
            if k in params_dump:
                print("      %-26s = %s" % (k, params_dump[k][:90]), flush=True)


if __name__ == "__main__":
    for k in (sys.argv[1:] or list(ROUTES)):
        extract(k)
