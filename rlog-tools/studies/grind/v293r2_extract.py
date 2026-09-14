# -*- coding: utf-8 -*-
"""v293r2_extract.py -- ONE-PASS extraction (rev-2 drive variant of v293_ident_extract.py: adds
cs_jerk = torqueState.desiredLateralJerk and lpar_roll = liveParameters.roll; tag=route pairs on argv)
ORIGINAL DOCSTRING: v293_ident_extract.py -- ONE-PASS extraction of every channel the V293 plant identification needs,
for route 70 (the first V293 "torque mode" flight).  Subagent v293plant, 2026-09-13.

ANALYSIS ONLY.  Reads rlogs, writes an npz cache.  Builds nothing, sends nothing, flashes nothing.

This merges what `extract_v292_routes.py` pulls (raw CAN: 0x18F bar/rate/SCA, 0x14A angle + byte 4,
0x1AB = the CAN-427 delivered-torque tap, 0xE4 command/STEER_REQUEST) with what `tau_extract_lat.py`
pulls (carControl / controlsState.torqueState / livePose / liveDelay / liveParameters / modelV2 /
cameraOdometry / raw gyroscope), in a SINGLE decompression pass per segment, so the 19 segments of
route 70 are read once instead of twice.

🛑 CEREAL COLLISION: never touch `epsTelemetry` (@137) or `modelDataV2SP` (@116) from these rlogs --
the fork declares `starpilotLateralState` and `customReserved9` at the same union slots.  Every field
read here is stock schema.

Writes  analysis-2020accord/_scratch/cache/tau/<TAG>_ident.npz
        analysis-2020accord/_scratch/cache/tau/<TAG>_ident_meta.json
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

ROUTES = {
    # full route id (NEVER the bare counter -- the dongle counter was reset and 00000070 is ambiguous)
    "r70_v293": "75604b0a432fdc89_00000070--717f5a7866",
}

# params we name explicitly; everything short + printable is captured too (see grab_params)
WANT_PARAMS = ["SteerDelay", "UseAutoSteerDelay", "AdvancedLateralTuning", "AdvancedLateralTune",
               "SteerRatio", "SteerFriction", "SteerLatAccel", "SteerKP", "SteerKI",
               "AccordRatePlantFF", "AccordFFRateGain", "AccordTorqueKi", "AccordVariableSteerRatio",
               "ForceTorqueController", "ForceAutoTune", "ForceAutoTuneOff", "AccordCurvatureLead",
               "AccordCurvatureLeadGain", "AccordTurnFFTaper", "AccordEpsGainScale",
               "AccordEpsSpringScale", "LateralTuning", "GitCommit", "GitBranch", "GitCommitDate",
               "CarParams"]


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 65536 if v >= 32768 else v


def segments(route):
    segs = sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % route)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    return segs


def grab_params(evt):
    """every short printable param, so attribution is not limited to a hard-coded list."""
    out = {}
    n = 0
    for e in evt.initData.params.entries:
        n += 1
        k = e.key
        try:
            v = bytes(e.value)
        except Exception:
            continue
        if len(v) > 160:
            out["_len_" + k] = len(v)
            continue
        try:
            s = v.decode("utf-8")
        except Exception:
            out["_bin_" + k] = repr(v[:40])
            continue
        if all((32 <= ord(ch) < 127) or ch in "\n\r\t" for ch in s):
            out[k] = s
    out["_n_entries"] = n
    return out


def extract(tag):
    route = ROUTES[tag]
    segs = segments(route)
    if not segs:
        raise SystemExit("no segments on disk for %s" % route)
    have = [int(os.path.basename(p).split("--")[2]) for p in segs]
    print("%s (%s): %d segments %s" % (tag, route, len(segs), have), flush=True)

    KEYS = (
        # --- raw CAN, the yardstick every other kit tool uses -------------------------------------
        "t18", "tq", "rate", "sca",            # 0x18F  100 Hz  driver-torque bar, wheel rate, SCA
        "t14", "ang",                          # 0x14A  100 Hz  steering angle (x -0.1 deg)
        "t14b", "b4",                          # 0x14A byte 4   cave duty bits
        "t1ab", "b0", "b1",                    # 0x1AB   50 Hz  CAN-427 delivered-torque tap
        "te4", "cmd", "req",                   # 0xE4   100 Hz  LKAS torque command + STEER_REQUEST
        # --- openpilot, 100 Hz --------------------------------------------------------------------
        "t_cc", "lat_active", "cc_enabled", "cc_curv_cmd", "cc_torque", "cc_curv_now", "cc_yaw",
        "t_cs", "cs_des_curv", "cs_curv", "cs_la_des", "cs_la_act", "cs_out", "cs_err",
        "cs_f", "cs_p", "cs_i", "cs_sat", "cs_active", "cs_jerk",
        "t_cst", "vego", "aego", "sa_deg", "sr_deg", "spress", "storque", "storque_eps",
        "cs_standstill", "cs_gas", "cs_brake", "cs_yaw",
        # --- lower-rate estimators ----------------------------------------------------------------
        "t_lp", "lp_wx", "lp_wy", "lp_wz", "lp_valid", "lp_ok",
        "t_lc", "lc_r", "lc_p", "lc_y", "lc_valid",
        "t_ld", "ld_delay", "ld_est", "ld_std", "ld_blocks", "ld_status", "ld_cal",
        "t_lpar", "lpar_sr", "lpar_stiff", "lpar_ao", "lpar_valid", "lpar_roll",
        "t_mv", "mv_curv",
        "t_co", "co_rot_x", "co_rot_y", "co_rot_z",
        "t_gy", "gy_x", "gy_y", "gy_z",
    )
    C = {k: [] for k in KEYS}
    marks, failed, params_dump = [], [], None
    seg_span = {}

    for p in segs:
        sn = int(os.path.basename(p).split("--")[2])
        with open(p, "rb") as fh:
            data = zstandard.ZstdDecompressor().stream_reader(fh).read()
        it = clog.Event.read_multiple_bytes(data)
        lo = hi = None
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
            hi = tm
            try:
                if w == "can":
                    for m in evt.can:
                        d = bytes(m.dat)
                        if m.src == 1:
                            if m.address == 0x18F and len(d) >= 5:
                                C["t18"].append(tm); C["tq"].append(i16be(d, 0))
                                C["rate"].append(i16be(d, 2)); C["sca"].append((d[4] >> 3) & 1)
                            elif m.address == 0x14A and len(d) >= 4:
                                C["t14"].append(tm); C["ang"].append(i16be(d, 0) * -0.1)
                                if len(d) >= 5:
                                    C["t14b"].append(tm); C["b4"].append(d[4])
                            elif m.address == 0x1AB and len(d) >= 2:
                                C["t1ab"].append(tm); C["b0"].append(d[0]); C["b1"].append(d[1])
                        elif m.src == 129 and m.address == 0x0E4 and len(d) >= 3:
                            C["te4"].append(tm); C["cmd"].append(i16be(d, 0))
                            C["req"].append((d[2] >> 7) & 1)
                elif w == "carControl":
                    m = evt.carControl
                    C["t_cc"].append(tm); C["lat_active"].append(1 if m.latActive else 0)
                    C["cc_enabled"].append(1 if m.enabled else 0)
                    C["cc_curv_cmd"].append(m.actuators.curvature)
                    C["cc_torque"].append(m.actuators.torque)
                    C["cc_curv_now"].append(m.currentCurvature)
                    C["cc_yaw"].append(m.angularVelocity[2] if len(m.angularVelocity) > 2 else np.nan)
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
                    C["cs_f"].append(getattr(st, "f", np.nan))
                    C["cs_p"].append(getattr(st, "p", np.nan))
                    C["cs_i"].append(getattr(st, "i", np.nan))
                    C["cs_sat"].append(1 if getattr(st, "saturated", False) else 0)
                    C["cs_active"].append(1 if getattr(st, "active", False) else 0)
                    C["cs_jerk"].append(getattr(st, "desiredLateralJerk", np.nan))
                elif w == "carState":
                    m = evt.carState
                    C["t_cst"].append(tm); C["vego"].append(m.vEgo)
                    C["sa_deg"].append(m.steeringAngleDeg); C["storque"].append(m.steeringTorque)
                    C["spress"].append(1 if m.steeringPressed else 0)
                    for fld, key, dflt in (("steeringRateDeg", "sr_deg", np.nan),
                                           ("aEgo", "aego", np.nan),
                                           ("steeringTorqueEps", "storque_eps", np.nan),
                                           ("yawRate", "cs_yaw", np.nan),
                                           ("gas", "cs_gas", np.nan),
                                           ("brake", "cs_brake", np.nan)):
                        try:
                            C[key].append(float(getattr(m, fld)))
                        except Exception:
                            C[key].append(dflt)
                    C["cs_standstill"].append(1 if m.standstill else 0)
                elif w == "livePose":
                    m = evt.livePose
                    C["t_lp"].append(tm)
                    C["lp_wx"].append(m.angularVelocityDevice.x)
                    C["lp_wy"].append(m.angularVelocityDevice.y)
                    C["lp_wz"].append(m.angularVelocityDevice.z)
                    C["lp_valid"].append(1 if m.angularVelocityDevice.valid else 0)
                    C["lp_ok"].append(1 if (m.inputsOK and m.posenetOK) else 0)
                elif w == "liveCalibration":
                    m = evt.liveCalibration
                    r = list(m.rpyCalib) if len(m.rpyCalib) >= 3 else [np.nan] * 3
                    C["t_lc"].append(tm); C["lc_r"].append(r[0]); C["lc_p"].append(r[1])
                    C["lc_y"].append(r[2])
                    C["lc_valid"].append(1 if str(m.calStatus) in ("calibrated", "1") else 0)
                elif w == "liveDelay":
                    m = evt.liveDelay
                    C["t_ld"].append(tm); C["ld_delay"].append(m.lateralDelay)
                    C["ld_est"].append(m.lateralDelayEstimate)
                    C["ld_std"].append(m.lateralDelayEstimateStd)
                    C["ld_blocks"].append(m.validBlocks)
                    C["ld_status"].append({"unestimated": 0, "estimated": 1,
                                           "invalid": 2}.get(str(m.status), -1))
                    C["ld_cal"].append(m.calPerc)
                elif w == "liveParameters":
                    m = evt.liveParameters
                    C["t_lpar"].append(tm); C["lpar_sr"].append(m.steerRatio)
                    C["lpar_stiff"].append(m.stiffnessFactor); C["lpar_ao"].append(m.angleOffsetDeg)
                    C["lpar_valid"].append(1 if m.valid else 0)
                    C["lpar_roll"].append(float(getattr(m, "roll", np.nan)))
                elif w == "modelV2":
                    C["t_mv"].append(tm)
                    try:
                        C["mv_curv"].append(evt.modelV2.action.desiredCurvature)
                    except Exception:
                        C["mv_curv"].append(np.nan)
                elif w == "cameraOdometry":
                    r = list(evt.cameraOdometry.rot)
                    C["t_co"].append(tm); C["co_rot_x"].append(r[0]); C["co_rot_y"].append(r[1])
                    C["co_rot_z"].append(r[2])
                elif w == "gyroscope":
                    s = evt.gyroscope
                    try:
                        v = list(s.gyroUncalibrated.v) if s.which() == "gyroUncalibrated" else list(s.gyro.v)
                    except Exception:
                        continue
                    if len(v) >= 3:
                        C["t_gy"].append(tm); C["gy_x"].append(v[0]); C["gy_y"].append(v[1])
                        C["gy_z"].append(v[2])
                elif w == "userBookmark":
                    marks.append(dict(seg=sn, mono=tm))
                elif w == "initData" and params_dump is None:
                    params_dump = grab_params(evt)
                    params_dump["_seg"] = sn
            except Exception:
                continue
        seg_span[sn] = dict(lo=lo, hi=hi)
        print("   seg %-2d  %s" % (sn, os.path.basename(p)), flush=True)

    D = {k: np.asarray(v, dtype=float) for k, v in C.items() if len(v)}
    os.makedirs(CACHE, exist_ok=True)
    np.savez_compressed(os.path.join(CACHE, tag + "_ident.npz"), **D)
    meta = dict(tag=tag, route=route, segments=have, failed=failed, params=params_dump or {},
                marks=marks, seg_span=seg_span,
                counts={k: int(len(v)) for k, v in D.items()})
    with open(os.path.join(CACHE, tag + "_ident_meta.json"), "w") as fh:
        json.dump(meta, fh, indent=1, default=float)
    print("\n%s -> %s_ident.npz" % (tag, tag), flush=True)
    for k in ("t18", "t14", "t1ab", "te4", "t_cc", "t_cs", "t_cst", "t_lp", "t_ld", "t_lpar",
              "t_mv", "t_co", "t_gy"):
        print("   %-8s %8d" % (k, len(D.get(k, []))), flush=True)
    if params_dump:
        print("\n   --- named params ---", flush=True)
        for k in WANT_PARAMS:
            if k in params_dump:
                print("      %-26s = %s" % (k, str(params_dump[k])[:100]), flush=True)
        print("   (%d param entries total)" % params_dump.get("_n_entries", -1), flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    maxsegs = None
    if "--max-segs" in args:
        i = args.index("--max-segs"); maxsegs = int(args[i + 1]); del args[i:i + 2]
    for a in args:
        if "=" in a:
            tag, route = a.split("=", 1)
            ROUTES[tag] = route
    if maxsegs is not None:
        _segments = segments
        def segments(route):  # noqa: F811
            return _segments(route)[:maxsegs]
    for t in ([a.split("=")[0] for a in args] or list(ROUTES)):
        extract(t)
