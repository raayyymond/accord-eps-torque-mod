# -*- coding: utf-8 -*-
"""outerloop_params.py -- read the lateral tuning parameters that set the OUTER loop's feedback gain:
carParams.lateralTuning.torque (latAccelFactor, friction, latAccelOffset, steeringAngleDeadzoneDeg) and
liveTorqueParameters (the learner's filtered values), one mid-route segment per route.
Subagent `echoloop`, 2026-09-10.  ANALYSIS ONLY.

WHY: latcontrol_torque.py:547 adds  friction_scale * get_friction(error_with_lsf + 0.22*friction_jerk,
lateral_accel_deadzone, friction_threshold, torque_params)  to the FEEDFORWARD -- and get_friction's
argument contains error_with_lsf, i.e. THE MEASUREMENT.  So `f` is a second feedback path whose slope is
friction*latAccelFactor/friction_threshold inside its linear region.  friction_threshold is
max(interp(v,[0.45,8.9,33.5],[0.16,0.19,0.27]), 0.30) = 0.30 everywhere (vehicle_tunes.py:15,1330-1335)
and friction_scale is 1.0 for the Accord (latcontrol_torque.py:381, the else branch).
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
sys.path.insert(0, HERE)
import numpy as np                                     # noqa: E402
import zstandard                                       # noqa: E402
from cereal import log as clog                         # noqa: E402
import outerloop_extract as EX                         # noqa: E402


def main():
    for tag, prefix in EX.ROUTES.items():
        segs = sorted(glob.glob(os.path.join(RLOGS, prefix + "--*--rlog.zst")),
                      key=lambda p: int(os.path.basename(p).split("--")[2]))
        if not segs:
            continue
        p = segs[len(segs) // 2]
        data = zstandard.ZstdDecompressor().stream_reader(open(p, "rb")).read()
        it = clog.Event.read_multiple_bytes(data)
        cp = None
        ltp = []
        while True:
            try:
                evt = next(it)
            except StopIteration:
                break
            except Exception:
                break
            try:
                w = evt.which()
            except Exception:
                continue
            if w == "carParams" and cp is None:
                cp = evt.carParams
            elif w == "liveTorqueParameters":
                m = evt.liveTorqueParameters
                ltp.append((m.latAccelFactorFiltered, m.frictionCoefficientFiltered,
                            m.latAccelOffsetFiltered, 1.0 if m.liveValid else 0.0))
        print("=" * 90)
        print("%s  %s" % (tag, os.path.basename(p)))
        if cp is not None:
            t = cp.lateralTuning.torque
            print("  carParams.carFingerprint      %s" % cp.carFingerprint)
            print("  lateralTuning.torque.latAccelFactor      %.5f" % t.latAccelFactor)
            print("  lateralTuning.torque.friction            %.5f" % t.friction)
            print("  lateralTuning.torque.latAccelOffset      %.5f" % t.latAccelOffset)
            print("  lateralTuning.torque.steeringAngleDeadzoneDeg %.5f" % t.steeringAngleDeadzoneDeg)
            print("  steerRatio %.4f  wheelbase %.4f  steerActuatorDelay %.4f"
                  % (cp.steerRatio, cp.wheelbase, cp.steerActuatorDelay))
            print("  lateralParams.torqueBP[-1] (STEER_MAX) %s" % (list(cp.lateralParams.torqueBP)[-1:],))
        if ltp:
            a = np.asarray(ltp, float)
            print("  liveTorqueParameters (n=%d): latAccelFactorFiltered p50 %.5f, frictionCoefficientFiltered"
                  " p50 %.5f, latAccelOffsetFiltered p50 %.5f, liveValid frac %.2f"
                  % (len(a), np.median(a[:, 0]), np.median(a[:, 1]), np.median(a[:, 2]), a[:, 3].mean()))


if __name__ == "__main__":
    main()
