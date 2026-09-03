# -*- coding: utf-8 -*-
"""studies/grind/grind_r35_extra_read.py -- the streams the v280 cache does NOT carry, for the r35 incident study:
gpsLocationExternal (wall-clock anchor), clocks, gyroscope/accelerometer (IMU), carState extras (steeringTorque, steeringAngleDeg,
brake/gas, blinkers), controlsState (curvature, desiredCurvature, torque-controller state), liveTorqueParameters, and the FULL
0x14A frame (b0-1 angle, byte 4 = cave probe byte) with its receive time.  Segments SEG_LO..SEG_HI only (the incident is in seg 16).
Writes _scratch/r35_extra.npz beside this file.  Subagent grindr35, 2026-09-03.  Run: python grind_r35_extra_read.py [lo hi]
"""
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
PREFIX = "75604b0a432fdc89_00000035--580292087d"
SEG_LO, SEG_HI = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (13, 18)


def main():
    import zstandard
    from cereal import log as clog
    segs = sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % PREFIX)), key=lambda p: int(os.path.basename(p).split("--")[2]))
    segs = [p for p in segs if SEG_LO <= int(os.path.basename(p).split("--")[2]) <= SEG_HI]
    keys = ("tgps", "unixms", "gpsflags", "tclk", "wall", "gt", "gtm", "gx", "gy", "gz", "at", "atm", "ax", "ay", "az",
            "tcs", "vego", "csang", "cstq", "brake", "gas", "lblink", "rblink", "tco", "curv", "dcurv", "tcact", "tcerr", "tcout", "tcsat",
            "tlt", "laf", "fric", "lafraw", "fricraw", "ltvalid", "t14", "a14_0", "a14_1", "b4", "b14_2", "b14_3", "t18", "b18_4", "b18_5")
    out = {k: [] for k in keys}
    for p in segs:
        with open(p, "rb") as fh:
            data = zstandard.ZstdDecompressor().stream_reader(fh).read()
        it = clog.Event.read_multiple_bytes(data)
        while True:
            try:
                evt = next(it)
            except StopIteration:
                break
            except Exception as e:
                print("  torn: %s" % str(e)[:60]); break
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if w == "can":
                for m in evt.can:
                    if m.src != 1:
                        continue
                    d = bytes(m.dat)
                    if m.address == 0x14A and len(d) >= 5:
                        out["t14"].append(tm); out["a14_0"].append(d[0]); out["a14_1"].append(d[1]); out["b4"].append(d[4])
                        out["b14_2"].append(d[2]); out["b14_3"].append(d[3])
                    elif m.address == 0x18F and len(d) >= 6:
                        out["t18"].append(tm); out["b18_4"].append(d[4]); out["b18_5"].append(d[5])
            elif w == "gpsLocationExternal":
                g = evt.gpsLocationExternal
                out["tgps"].append(tm); out["unixms"].append(float(g.unixTimestampMillis)); out["gpsflags"].append(int(g.flags))
            elif w == "clocks":
                out["tclk"].append(tm); out["wall"].append(float(evt.clocks.wallTimeNanos))
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
                    out["gt"].append(g.timestamp * 1e-9); out["gtm"].append(tm); out["gx"].append(v[0]); out["gy"].append(v[1]); out["gz"].append(v[2])
            elif w == "accelerometer":
                a = evt.accelerometer
                try:
                    v = list(a.acceleration.v)
                except Exception:
                    continue
                if len(v) >= 3:
                    out["at"].append(a.timestamp * 1e-9); out["atm"].append(tm); out["ax"].append(v[0]); out["ay"].append(v[1]); out["az"].append(v[2])
            elif w == "carState":
                c = evt.carState
                out["tcs"].append(tm); out["vego"].append(c.vEgo); out["csang"].append(c.steeringAngleDeg); out["cstq"].append(c.steeringTorque)
                out["brake"].append(int(bool(c.brakePressed))); out["gas"].append(int(bool(c.gasPressed)))
                out["lblink"].append(int(bool(c.leftBlinker))); out["rblink"].append(int(bool(c.rightBlinker)))
            elif w == "controlsState":
                c = evt.controlsState
                out["tco"].append(tm)
                out["curv"].append(float(getattr(c, "curvature", np.nan)))
                out["dcurv"].append(float(getattr(c, "desiredCurvature", np.nan)))
                try:
                    ls = c.lateralControlState
                    st = getattr(ls, ls.which())
                    out["tcact"].append(int(bool(st.active))); out["tcerr"].append(float(getattr(st, "error", np.nan)))
                    out["tcout"].append(float(getattr(st, "output", np.nan))); out["tcsat"].append(int(bool(getattr(st, "saturated", False))))
                except Exception:
                    out["tcact"].append(-1); out["tcerr"].append(np.nan); out["tcout"].append(np.nan); out["tcsat"].append(-1)
            elif w == "liveTorqueParameters":
                l = evt.liveTorqueParameters
                out["tlt"].append(tm); out["laf"].append(float(getattr(l, "latAccelFactorFiltered", np.nan))); out["fric"].append(float(getattr(l, "frictionCoefficientFiltered", np.nan)))
                out["lafraw"].append(float(getattr(l, "latAccelFactorRaw", np.nan))); out["fricraw"].append(float(getattr(l, "frictionCoefficientRaw", np.nan)))
                out["ltvalid"].append(int(bool(getattr(l, "liveValid", False))))
        print("  read %s" % os.path.basename(p), flush=True)
    D = {k: np.asarray(v, float) for k, v in out.items()}
    f = os.path.join(HERE, "_scratch", "r35_extra.npz")
    os.makedirs(os.path.dirname(f), exist_ok=True)
    np.savez(f, **D)
    print("wrote", f, {k: len(v) for k, v in D.items()})


if __name__ == "__main__":
    main()
