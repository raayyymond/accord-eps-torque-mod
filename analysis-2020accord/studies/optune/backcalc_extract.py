# -*- coding: utf-8 -*-
"""backcalc_extract.py -- per-route extraction for BACKCALC-LAF-FRICTION-2026-09-02.md (subagent opfit).

Reads every segment of a route and writes ONE npz of event-timestamped channels (no resampling here; the
analysis script joins onto a 100 Hz grid).  Channels:
  carOutput.actuatorsOutput.torque / torqueOutputCan          (co_t, co_tq, co_can)
  CAN 0xE4 src>=128: STEER_TORQUE i16be b0-1, STEER_REQUEST b2.7   (e4_t, e4_cmd, e4_req)
  CAN 0x18F src 1: driver torque b0-1, rate b2-3, SCA b4.3      (f18_t, f18_tq, f18_rate, f18_sca)
  carState: vEgo steeringTorque steeringAngleDeg steeringRateDeg steeringPressed  (cs_*)
  carControl.latActive                                           (cc_t, cc_lat)
  controlsState: desiredCurvature curvature + torqueState fields (ctl_*)
  livePose: angularVelocityDevice xyz, orientationNED xyz         (lp_*)
  liveCalibration.rpyCalib, calStatus                            (cal_*)
  liveParameters: roll angleOffsetDeg steerRatio stiffnessFactor (lpar_*)
  liveDelay.lateralDelay                                          (ld_t, ld_lag)
  liveTorqueParameters: all scalars                               (ltp_*)
  gyroscope (uncalibrated if present) xyz                         (gy_*)
  carParams (first seen): lateralTuning.torque, steerRatio, torqueBP/V, steerActuatorDelay  (json string)
Run: python backcalc_extract.py <tag>   (tag in ROUTES)   -> _scratch/<tag>_backcalc.npz
"""
import glob, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "rlog-tools"))
RLOGS = os.path.join(ROOT, "analysis-2020accord", "rlogs")
OUT = os.path.join(HERE, "_scratch"); os.makedirs(OUT, exist_ok=True)
ROUTES = {
    "r22": ("75604b0a432fdc89_00000022--00f57626e0", "V112"),
    "r97": ("75604b0a432fdc89_00000097--489d7896b3", "stock"),
    "r31": ("75604b0a432fdc89_00000031--a680e9b2ac", "V278r3"),
    "r32": ("75604b0a432fdc89_00000032--33a5dbbcb3", "V280r2"),
    "r33": ("75604b0a432fdc89_00000033--1948a2c354", "V280r2"),
}


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 65536 if v >= 32768 else v


def read_segment(path, out, cp_holder):
    import zstandard
    from cereal import log as clog
    with open(path, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    it = clog.Event.read_multiple_bytes(data)
    n = 0
    while True:
        try:
            evt = next(it)
        except StopIteration:
            break
        except Exception as exc:
            print("    torn after %d events: %s" % (n, str(exc).splitlines()[0][:70]))
            break
        n += 1
        try:
            w = evt.which()
        except Exception:
            continue
        tm = evt.logMonoTime * 1e-9
        A = out.setdefault
        if w == "can":
            for m in evt.can:
                d = bytes(m.dat)
                if m.src == 1 and m.address == 0x18F and len(d) >= 5:
                    A("f18_t", []).append(tm); A("f18_tq", []).append(i16be(d, 0)); A("f18_rate", []).append(i16be(d, 2)); A("f18_sca", []).append((d[4] >> 3) & 1)
                elif m.src >= 128 and m.address == 0x0E4 and len(d) >= 3:
                    A("e4_t", []).append(tm); A("e4_cmd", []).append(i16be(d, 0)); A("e4_req", []).append((d[2] >> 7) & 1)
        elif w == "carOutput":
            a = evt.carOutput.actuatorsOutput
            A("co_t", []).append(tm); A("co_tq", []).append(float(a.torque)); A("co_can", []).append(float(a.torqueOutputCan))
        elif w == "carState":
            c = evt.carState
            A("cs_t", []).append(tm); A("cs_v", []).append(c.vEgo); A("cs_drv", []).append(c.steeringTorque)
            A("cs_ang", []).append(c.steeringAngleDeg); A("cs_rate", []).append(c.steeringRateDeg); A("cs_pressed", []).append(int(c.steeringPressed))
        elif w == "carControl":
            A("cc_t", []).append(tm); A("cc_lat", []).append(int(bool(evt.carControl.latActive)))
        elif w == "controlsState":
            c = evt.controlsState
            A("ctl_t", []).append(tm); A("ctl_descurv", []).append(c.desiredCurvature); A("ctl_curv", []).append(c.curvature)
            ok = c.lateralControlState.which() == "torqueState"
            ts = c.lateralControlState.torqueState if ok else None
            for k in ("active", "error", "p", "i", "d", "f", "output", "saturated", "errorRate", "actualLateralAccel", "desiredLateralAccel", "desiredLateralJerk"):
                A("ctl_" + k, []).append(float(getattr(ts, k)) if ok else np.nan)
        elif w == "livePose":
            p = evt.livePose
            A("lp_t", []).append(tm)
            for nm, s in (("w", p.angularVelocityDevice), ("o", p.orientationNED)):
                A("lp_%sx" % nm, []).append(s.x); A("lp_%sy" % nm, []).append(s.y); A("lp_%sz" % nm, []).append(s.z)
        elif w == "liveCalibration":
            c = evt.liveCalibration
            A("cal_t", []).append(tm)
            r = list(c.rpyCalib) + [0, 0, 0]
            A("cal_r", []).append(r[0]); A("cal_p", []).append(r[1]); A("cal_y", []).append(r[2]); A("cal_ok", []).append(int(str(c.calStatus) == "calibrated"))
        elif w == "liveParameters":
            c = evt.liveParameters
            A("lpar_t", []).append(tm); A("lpar_roll", []).append(c.roll); A("lpar_aoff", []).append(c.angleOffsetDeg)
            A("lpar_sr", []).append(c.steerRatio); A("lpar_stiff", []).append(c.stiffnessFactor)
        elif w == "liveDelay":
            A("ld_t", []).append(tm); A("ld_lag", []).append(evt.liveDelay.lateralDelay)
        elif w == "liveTorqueParameters":
            c = evt.liveTorqueParameters
            A("ltp_t", []).append(tm)
            for k in ("liveValid", "latAccelFactorRaw", "latAccelOffsetRaw", "frictionCoefficientRaw", "latAccelFactorFiltered",
                      "latAccelOffsetFiltered", "frictionCoefficientFiltered", "totalBucketPoints", "decay", "maxResets", "useParams", "calPerc"):
                A("ltp_" + k, []).append(float(getattr(c, k)))
        elif w == "gyroscope":
            g = evt.gyroscope
            try:
                v = list(g.gyroUncalibrated.v)
            except Exception:
                try:
                    v = list(g.gyro.v)
                except Exception:
                    continue
            if len(v) >= 3:
                A("gy_t", []).append(g.timestamp * 1e-9); A("gy_tm", []).append(tm); A("gy_x", []).append(v[0]); A("gy_y", []).append(v[1]); A("gy_z", []).append(v[2])
        elif w == "carParams" and cp_holder.get("cp") is None:
            c = evt.carParams
            lt = c.lateralTuning
            cp_holder["cp"] = dict(which=lt.which(), steerRatio=c.steerRatio, steerActuatorDelay=c.steerActuatorDelay, mass=c.mass, wheelbase=c.wheelbase,
                                   centerToFront=c.centerToFront, tireStiffnessFront=c.tireStiffnessFront, tireStiffnessRear=c.tireStiffnessRear,
                                   torqueBP=list(c.lateralParams.torqueBP), torqueV=list(c.lateralParams.torqueV))
            if lt.which() == "torque":
                t = lt.torque
                cp_holder["cp"].update(friction=t.friction, latAccelFactor=t.latAccelFactor, latAccelOffset=t.latAccelOffset,
                                       steeringAngleDeadzoneDeg=t.steeringAngleDeadzoneDeg)
    return n


def main(tag):
    prefix, build = ROUTES[tag]
    segs = sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % prefix)), key=lambda p: int(os.path.basename(p).split("--")[2]))
    out, cp = {}, {}
    for p in segs:
        print("  %s" % os.path.basename(p), flush=True)
        read_segment(p, out, cp)
    D = {k: np.asarray(v, float) for k, v in out.items()}
    D["carParams_json"] = np.array(json.dumps(cp.get("cp"), default=float))
    D["build"] = np.array(build)
    D["prefix"] = np.array(prefix)
    np.savez(os.path.join(OUT, "%s_backcalc.npz" % tag), **D)
    print("wrote %s: %s" % (tag, {k: len(v) for k, v in D.items() if v.ndim}))


if __name__ == "__main__":
    for t in sys.argv[1:]:
        main(t)
