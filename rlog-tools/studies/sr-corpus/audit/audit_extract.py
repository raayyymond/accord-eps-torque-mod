# -*- coding: utf-8 -*-
"""audit_extract.py -- INDEPENDENT extraction for the adversarial pass on the SR-vs-angle instrument.
Written from the cereal schema, not from sr_angle_sweep_r62_r63.py or sr-corpus's cache.
Adds channels the optune cache does NOT carry: angleOffsetAverageDeg, the lp *_valid/std flags,
posenetOK/sensorsOK, liveParameters validity flags, and raw 0x1D0 wheel speeds.
Usage: python audit_extract.py <tag> <route_id>
"""
import os, sys, json, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "rlog-tools"))
sys.path.insert(0, os.path.join(ROOT, "rlog-tools", "lib"))
RLOGS = os.path.join(ROOT, "analysis-2020accord", "rlogs")
OUT = os.path.join(HERE, "_scratch"); os.makedirs(OUT, exist_ok=True)
from rlog_parse import read_messages  # noqa: E402


def run(tag, route):
    files = sorted(glob.glob(os.path.join(RLOGS, route + "--*--rlog.zst")),
                   key=lambda p: int(os.path.basename(p).split("--")[2]))
    print("%s: %d segments" % (tag, len(files)), flush=True)
    A = {}
    cp = {}
    def ap(k, v):
        A.setdefault(k, []).append(v)
    for fi, f in enumerate(files):
        n = 0
        try:
            for evt in read_messages(f):
                n += 1
                try:
                    w = evt.which()
                except Exception:
                    continue
                tm = evt.logMonoTime * 1e-9
                if w == "carState":
                    c = evt.carState
                    ap("cs_t", tm); ap("cs_v", c.vEgo); ap("cs_ang", c.steeringAngleDeg)
                    ap("cs_rate", c.steeringRateDeg); ap("cs_pressed", int(c.steeringPressed))
                    ap("cs_drv", c.steeringTorque); ap("cs_yawrate_DEAD", float(c.yawRate))
                elif w == "carControl":
                    ap("cc_t", tm); ap("cc_lat", int(bool(evt.carControl.latActive)))
                elif w == "livePose":
                    p = evt.livePose
                    ap("lp_t", tm)
                    ap("lp_wx", p.angularVelocityDevice.x); ap("lp_wy", p.angularVelocityDevice.y)
                    ap("lp_wz", p.angularVelocityDevice.z); ap("lp_wzstd", p.angularVelocityDevice.zStd)
                    ap("lp_wvalid", int(p.angularVelocityDevice.valid))
                    ap("lp_ox", p.orientationNED.x); ap("lp_oxstd", p.orientationNED.xStd)
                    ap("lp_posenetOK", int(p.posenetOK)); ap("lp_sensorsOK", int(p.sensorsOK))
                    ap("lp_inputsOK", int(p.inputsOK))
                elif w == "liveCalibration":
                    c = evt.liveCalibration
                    r = list(c.rpyCalib) + [0.0, 0.0, 0.0]
                    ap("cal_t", tm); ap("cal_r", r[0]); ap("cal_p", r[1]); ap("cal_y", r[2])
                    ap("cal_ok", int(str(c.calStatus) == "calibrated")); ap("cal_perc", int(c.calPerc))
                elif w == "liveParameters":
                    c = evt.liveParameters
                    ap("lpar_t", tm); ap("lpar_roll", c.roll)
                    ap("lpar_aoff", c.angleOffsetDeg); ap("lpar_aoffavg", c.angleOffsetAverageDeg)
                    ap("lpar_sr", c.steerRatio); ap("lpar_stiff", c.stiffnessFactor)
                    ap("lpar_valid", int(c.valid)); ap("lpar_aoffstd", c.angleOffsetAverageStd)
                    ap("lpar_fastr_std", c.angleOffsetFastStd)
                elif w == "gyroscope":
                    g = evt.gyroscope
                    try:
                        v = list(g.gyroUncalibrated.v)
                    except Exception:
                        try:
                            v = list(g.gyro.v)
                        except Exception:
                            v = None
                    if v and len(v) >= 3:
                        ap("gy_t", tm); ap("gy_x", v[0]); ap("gy_y", v[1]); ap("gy_z", v[2])
                elif w == "can":
                    for m in evt.can:
                        if m.src != 1:
                            continue
                        d = bytes(m.dat)
                        if m.address == 0x1D0 and len(d) >= 8:
                            ap("w_t", tm)
                            ap("w_fl", (((d[0] << 7) | (d[1] >> 1)) * 0.01) / 3.6)
                            ap("w_fr", ((((d[1] & 0x01) << 14) | (d[2] << 6) | (d[3] >> 2)) * 0.01) / 3.6)
                            ap("w_rl", ((((d[3] & 0x03) << 13) | (d[4] << 5) | (d[5] >> 3)) * 0.01) / 3.6)
                            ap("w_rr", ((((d[5] & 0x07) << 12) | (d[6] << 4) | (d[7] >> 4)) * 0.01) / 3.6)
                        elif m.address == 0x18F and len(d) >= 5:
                            v = (d[2] << 8) | d[3]
                            ap("f18_t", tm); ap("f18_rate", v - 65536 if v >= 32768 else v)
                            ap("f18_sca", (d[4] >> 3) & 1)
                elif w == "carParams" and not cp:
                    c = evt.carParams
                    for k in ("mass", "wheelbase", "centerToFront", "steerRatio", "steerRatioRear",
                              "tireStiffnessFront", "tireStiffnessRear", "rotationalInertia",
                              "steerActuatorDelay", "minSteerSpeed"):
                        try:
                            cp[k] = float(getattr(c, k))
                        except Exception:
                            pass
                    cp["carFingerprint"] = str(c.carFingerprint)
        except Exception as exc:
            print("  seg %d torn after %d: %s" % (fi, n, str(exc).splitlines()[0][:70]), flush=True)
        print("  seg %d/%d done (%d evts)" % (fi + 1, len(files), n), flush=True)
    D = {k: np.asarray(v) for k, v in A.items()}
    D["carParams_json"] = json.dumps(cp)
    D["route"] = route
    np.savez_compressed(os.path.join(OUT, tag + "_audit.npz"), **D)
    print("wrote %s  keys=%d  cs=%d lp=%d cal=%d lpar=%d w=%d" %
          (tag, len(D), len(D.get("cs_t", [])), len(D.get("lp_t", [])),
           len(D.get("cal_t", [])), len(D.get("lpar_t", [])), len(D.get("w_t", []))), flush=True)
    print("carParams:", json.dumps(cp), flush=True)


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
