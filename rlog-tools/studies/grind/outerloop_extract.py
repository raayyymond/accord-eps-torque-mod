# -*- coding: utf-8 -*-
"""outerloop_extract.py -- pull openpilot's OWN 100 Hz controller readout (error / P / I / D / FF /
output / actualLateralAccel / desiredLateralAccel) alongside carState, carOutput and the CAN wire, for
the outer-loop identification.  Subagent `echoloop`, 2026-09-10.  ANALYSIS ONLY -- reads rlogs, writes
one npz per route into rlog-tools/studies/grind/_scratch/.

WHY THIS SET: LatControlTorque's own log message carries, on ONE tick and ONE clock,
  setpoint  = torqueState.desiredLateralAccel
  measurement = torqueState.actualLateralAccel      (= -VM.calc_curvature(steeringAngleDeg-offset)*v^2)
  error     = torqueState.error   (NOTE: this is error_with_lsf, the low-speed-scaled error)
  output    = torqueState.output  (the PID output, pre rate-limit)
so the outer-loop return ratio can be estimated WITHOUT any inter-stream time-offset correction --
which is the error the record already made once ("PM 35-60 deg" was an un-removed 3.9 ms offset).

Run: python rlog-tools/studies/grind/outerloop_extract.py r62 r63 r39 r5e
"""
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
OUT = os.path.join(HERE, "_scratch")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))

ROUTES = {
    "r39": "75604b0a432fdc89_00000039--f56039af87",
    "r3a": "75604b0a432fdc89_0000003a--283a39a1d6",
    "r3c": "75604b0a432fdc89_0000003c--927965c2b4",
    "r35": "75604b0a432fdc89_00000035--580292087d",
    "r5e": "75604b0a432fdc89_0000005e--03a9714d78",
    "r62": "75604b0a432fdc89_00000062--1c7daa54e8",
    "r63": "75604b0a432fdc89_00000063--1d4b188022",
}


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 65536 if v >= 32768 else v


def read(tag, prefix):
    import zstandard
    from cereal import log as clog
    segs = sorted(glob.glob(os.path.join(RLOGS, prefix + "--*--rlog.zst")),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    print("%s: %d segments" % (tag, len(segs)), flush=True)

    # controlsState (one row per tick)
    cs_t, cs = [], []                      # 12 columns, see CS_COLS
    # carState
    st_t, st = [], []                      # 6 columns
    # carControl / carOutput
    cc_t, cc = [], []                      # 4 columns
    co_t, co = [], []                      # 2 columns
    # livePose yaw rate
    lp_t, lp = [], []
    # liveParameters / liveDelay (slow)
    par_t, par = [], []
    dly_t, dly = [], []
    # CAN
    t18, tq18, rate18, sca = [], [], [], []
    t14, ang, b4 = [], [], []
    te4, cmd, req = [], [], []
    marks = []

    for p in segs:
        sn = int(os.path.basename(p).split("--")[2])
        with open(p, "rb") as fh:
            data = zstandard.ZstdDecompressor().stream_reader(fh).read()
        it = clog.Event.read_multiple_bytes(data)
        while True:
            try:
                evt = next(it)
            except StopIteration:
                break
            except Exception as e:
                print("  truncated seg %d: %s" % (sn, str(e)[:50]), flush=True); break
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if w == "controlsState":
                m = evt.controlsState
                try:
                    ts = m.lateralControlState.torqueState
                except Exception:
                    continue
                cs_t.append(tm)
                cs.append((1.0 if ts.active else 0.0, ts.error, ts.p, ts.i, ts.d, ts.f,
                           ts.output, 1.0 if ts.saturated else 0.0, ts.errorRate,
                           ts.actualLateralAccel, ts.desiredLateralAccel, ts.desiredLateralJerk,
                           m.desiredCurvature))
            elif w == "carState":
                m = evt.carState
                st_t.append(tm)
                st.append((m.vEgo, m.steeringAngleDeg, m.steeringRateDeg, m.steeringTorque,
                           1.0 if m.steeringPressed else 0.0, m.steeringTorqueEps))
            elif w == "carControl":
                m = evt.carControl
                cc_t.append(tm)
                cc.append((1.0 if m.latActive else 0.0, m.actuators.torque,
                           m.actuators.curvature, m.currentCurvature))
            elif w == "carOutput":
                a = evt.carOutput.actuatorsOutput
                co_t.append(tm)
                co.append((a.torque, a.torqueOutputCan))
            elif w == "livePose":
                m = evt.livePose
                lp_t.append(tm)
                lp.append((m.angularVelocityDevice.x, m.angularVelocityDevice.y,
                           m.angularVelocityDevice.z, 1.0 if m.angularVelocityDevice.valid else 0.0))
            elif w == "liveParameters":
                m = evt.liveParameters
                par_t.append(tm); par.append((m.angleOffsetDeg, m.roll, m.steerRatio, m.stiffnessFactor))
            elif w == "liveDelay":
                dly_t.append(tm); dly.append(evt.liveDelay.lateralDelay)
            elif w == "userBookmark":
                marks.append((sn, tm))
            elif w == "can":
                for mm in evt.can:
                    d = bytes(mm.dat)
                    if mm.src == 1:
                        if mm.address == 0x18F and len(d) >= 5:
                            t18.append(tm); tq18.append(i16be(d, 0)); rate18.append(i16be(d, 2))
                            sca.append((d[4] >> 3) & 1)
                        elif mm.address == 0x14A and len(d) >= 5:
                            t14.append(tm); ang.append(i16be(d, 0) * -0.1); b4.append(d[4])
                    elif mm.src == 129 and mm.address == 0x0E4 and len(d) >= 3:
                        te4.append(tm); cmd.append(i16be(d, 0)); req.append((d[2] >> 7) & 1)
        print("  seg %d done" % sn, flush=True)

    A = np.asarray
    D = dict(
        cs_t=A(cs_t, float), cs=A(cs, float),
        st_t=A(st_t, float), st=A(st, float),
        cc_t=A(cc_t, float), cc=A(cc, float),
        co_t=A(co_t, float), co=A(co, float),
        lp_t=A(lp_t, float), lp=A(lp, float) if lp else np.zeros((0, 4)),
        par_t=A(par_t, float), par=A(par, float) if par else np.zeros((0, 4)),
        dly_t=A(dly_t, float), dly=A(dly, float),
        t18=A(t18, float), tq18=A(tq18, float), rate18=A(rate18, float), sca=A(sca, int),
        t14=A(t14, float), ang=A(ang, float), b4=A(b4, int),
        te4=A(te4, float), cmd=A(cmd, float), req=A(req, int),
        marks=A(marks, float) if marks else np.zeros((0, 2)),
    )
    os.makedirs(OUT, exist_ok=True)
    np.savez(os.path.join(OUT, "outer_%s.npz" % tag), **D)
    print("%s: controlsState %d  carState %d  livePose %d  0x18F %d  0xE4 %d  marks %d"
          % (tag, len(cs_t), len(st_t), len(lp_t), len(t18), len(te4), len(marks)), flush=True)


CS_COLS = ["active", "error", "p", "i", "d", "f", "output", "saturated", "errorRate",
           "meas", "setp", "djerk", "desCurv"]
ST_COLS = ["vEgo", "angDeg", "rateDeg", "dTorque", "pressed", "torqueEps"]
CC_COLS = ["latActive", "torque", "curv", "curCurv"]
CO_COLS = ["torqueOut", "torqueCan"]

if __name__ == "__main__":
    for t in (sys.argv[1:] or ["r62"]):
        f = os.path.join(OUT, "outer_%s.npz" % t)
        if os.path.exists(f):
            print("%s cached" % t, flush=True); continue
        read(t, ROUTES[t])
