# -*- coding: utf-8 -*-
"""studies/grind/modeld_cadence_extract.py -- TIMING-ONLY extraction of the openpilot-side command
pipeline, for the question "is the ~20 Hz grinding line a FORCED response to modeld's 20 Hz frame
cadence, or a plant resonance?"  Subagent `modelrate`, 2026-09-10.  ANALYSIS ONLY.

Nothing in the existing corpus caches carries modeld timing: `analysis-2020accord/_scratch/cache/v280/*.npz`
is CAN-only (t18/te4/t1ab/t14/tcs).  `analysis-2020accord/studies/oversteer/_scratch/r39_modelv2.npz`
carries mdl_t/mdl_frameid/mdl_descurv for r39/r3a/r3c but NOT timestampEof, frameDropPerc, or any of
the 100 Hz controlsd channels.

EVERY timestamp here is `evt.logMonoTime * 1e-9` -- THE SAME CLOCK AND THE SAME ZERO the v280 caches
use (extract_r39_v280cache.py stores raw logMonoTime seconds; it does NOT subtract a t0).  So mdl_t
and te4/t18 are directly comparable with no reconciliation step.  `timestampEof` is the CAMERA's
end-of-frame stamp in ns on the device boottime clock (a different clock origin from logMonoTime, but
the same rate); it is kept for the cadence fit, where only DIFFERENCES matter.

Channels written to _scratch/modeld/<tag>_cad.npz
  modelV2 (20 Hz)     mdl_t mdl_fid mdl_eof mdl_age mdl_drop mdl_exec mdl_curv mdl_accel
  drivingModelData    dmd_t dmd_fid dmd_curv
  controlsState 100Hz cs_t cs_descurv cs_curv cs_latmono cs_err cs_p cs_i cs_d cs_f cs_out
                      cs_sat cs_errate cs_actla cs_desla cs_desjerk cs_active
  carControl 100 Hz   cc_t cc_curv cc_torque cc_latact cc_enab
  carOutput 100 Hz    co_t co_torque co_tqcan
  carState 100 Hz     st_t st_v st_ang st_tq
  livePose 20 Hz      lp_t lp_yaw lp_ts
  roadCameraState     rc_t rc_fid rc_eof rc_sof
  cameraOdometry      od_t od_fid od_eof

Run:  python modeld_cadence_extract.py r39 r5e_v288 r62_v289 r63_v289 r22
"""
import glob
import os
import sys
import multiprocessing as mp

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
OUT = os.path.join(HERE, "_scratch", "modeld")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))

ROUTES = {
    "r22":      ("75604b0a432fdc89_00000022--00f57626e0", "V112 (STOCK MAP x1)"),
    "r35":      ("75604b0a432fdc89_00000035--580292087d", "V281 rev 3"),
    "r39":      ("75604b0a432fdc89_00000039--f56039af87", "V282"),
    "r3a":      ("75604b0a432fdc89_0000003a--283a39a1d6", "V282"),
    "r3c":      ("75604b0a432fdc89_0000003c--927965c2b4", "V282"),
    "r5e_v288": ("75604b0a432fdc89_0000005e--03a9714d78", "V288 rev 2"),
    "r62_v289": ("75604b0a432fdc89_00000062--1c7daa54e8", "V289 rev 1"),
    "r63_v289": ("75604b0a432fdc89_00000063--1d4b188022", "V289 rev 1"),
}

_TS = {"torqueState", "pidState", "angleState", "indiState", "lqrState", "debugState"}


def _f(x, d=np.nan):
    try:
        return float(x)
    except Exception:
        return d


def read_segment(path):
    """Parse one segment; return a dict of lists.  Runs in a worker process."""
    import zstandard
    from cereal import log as clog
    with open(path, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    it = clog.Event.read_multiple_bytes(data)
    o = {}
    A = lambda k, v: o.setdefault(k, []).append(v)  # noqa: E731
    n = 0
    while True:
        try:
            evt = next(it)
        except StopIteration:
            break
        except Exception:
            break
        n += 1
        try:
            w = evt.which()
        except Exception:
            continue
        t = evt.logMonoTime * 1e-9
        try:
            if w == "modelV2":
                m = evt.modelV2
                A("mdl_t", t); A("mdl_fid", float(m.frameId)); A("mdl_eof", float(m.timestampEof))
                A("mdl_age", _f(m.frameAge)); A("mdl_drop", _f(m.frameDropPerc))
                A("mdl_exec", _f(m.modelExecutionTime))
                A("mdl_curv", _f(m.action.desiredCurvature)); A("mdl_accel", _f(m.action.desiredAcceleration))
            elif w == "drivingModelData":
                m = evt.drivingModelData
                A("dmd_t", t); A("dmd_fid", float(m.frameId)); A("dmd_curv", _f(m.action.desiredCurvature))
            elif w == "controlsState":
                m = evt.controlsState
                A("cs_t", t); A("cs_descurv", _f(m.desiredCurvature)); A("cs_curv", _f(m.curvature))
                A("cs_latmono", float(m.lateralPlanMonoTime) * 1e-9)
                lc = m.lateralControlState
                try:
                    kind = lc.which()
                except Exception:
                    kind = None
                if kind in _TS:
                    s = getattr(lc, kind)
                    g = lambda nm: _f(getattr(s, nm, np.nan))  # noqa: E731
                    A("cs_err", g("error")); A("cs_p", g("p")); A("cs_i", g("i")); A("cs_d", g("d"))
                    A("cs_f", g("f")); A("cs_out", g("output"))
                    A("cs_sat", 1.0 if getattr(s, "saturated", False) else 0.0)
                    A("cs_active", 1.0 if getattr(s, "active", False) else 0.0)
                    A("cs_errate", g("errorRate")); A("cs_actla", g("actualLateralAccel"))
                    A("cs_desla", g("desiredLateralAccel")); A("cs_desjerk", g("desiredLateralJerk"))
                else:
                    for k in ("cs_err", "cs_p", "cs_i", "cs_d", "cs_f", "cs_out", "cs_sat",
                              "cs_active", "cs_errate", "cs_actla", "cs_desla", "cs_desjerk"):
                        A(k, np.nan)
            elif w == "carControl":
                m = evt.carControl
                A("cc_t", t); A("cc_curv", _f(m.actuators.curvature)); A("cc_torque", _f(m.actuators.torque))
                A("cc_latact", 1.0 if m.latActive else 0.0); A("cc_enab", 1.0 if m.enabled else 0.0)
            elif w == "carOutput":
                m = evt.carOutput
                A("co_t", t); A("co_torque", _f(m.actuatorsOutput.torque))
                A("co_tqcan", _f(getattr(m.actuatorsOutput, "torqueOutputCan", np.nan)))
            elif w == "carState":
                m = evt.carState
                A("st_t", t); A("st_v", _f(m.vEgo)); A("st_ang", _f(m.steeringAngleDeg))
                A("st_tq", _f(m.steeringTorque))
            elif w == "livePose":
                m = evt.livePose
                A("lp_t", t); A("lp_yaw", _f(m.angularVelocityDevice.z)); A("lp_ts", float(m.timestamp))
            elif w == "roadCameraState":
                m = evt.roadCameraState
                A("rc_t", t); A("rc_fid", float(m.frameId)); A("rc_eof", float(m.timestampEof))
                A("rc_sof", float(m.timestampSof))
            elif w == "cameraOdometry":
                m = evt.cameraOdometry
                A("od_t", t); A("od_fid", float(m.frameId)); A("od_eof", float(m.timestampEof))
        except Exception:
            continue
    o["_n"] = [float(n)]
    o["_seg"] = [float(int(os.path.basename(path).split("--")[2]))]
    return o


def main(tag):
    prefix, build = ROUTES[tag]
    segs = sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % prefix)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    if not segs:
        print("  *** no segments on disk for %s (%s)" % (tag, prefix)); return
    have = [int(os.path.basename(p).split("--")[2]) for p in segs]
    missing = [i for i in range(max(have) + 1) if i not in have]
    print("%s  %s  %d segs%s" % (tag, build, len(segs),
                                 ("  MISSING %s" % missing) if missing else ""), flush=True)
    nproc = min(8, max(1, mp.cpu_count() - 1))
    with mp.Pool(nproc) as pool:
        parts = pool.map(read_segment, segs)
    merged = {}
    for p in parts:
        for k, v in p.items():
            merged.setdefault(k, []).extend(v)
    D = {k: np.asarray(v, np.float64) for k, v in merged.items()}
    for k in list(D):                     # keep every channel sorted on its own clock
        pass
    for pre in ("mdl", "dmd", "cs", "cc", "co", "st", "lp", "rc", "od"):
        tk = pre + "_t"
        if tk not in D:
            continue
        order = np.argsort(D[tk], kind="stable")
        for k in list(D):
            if k.startswith(pre + "_") and len(D[k]) == len(order):
                D[k] = D[k][order]
    D["build"] = np.array(build); D["prefix"] = np.array(prefix)
    D["segments_present"] = np.asarray(have, float)
    D["segments_missing"] = np.asarray(missing, float)
    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(os.path.join(OUT, "%s_cad.npz" % tag), **D)
    print("  wrote %s_cad.npz  modelV2 n=%d  controlsState n=%d  span %.1f s"
          % (tag, len(D.get("mdl_t", [])), len(D.get("cs_t", [])),
             (D["mdl_t"][-1] - D["mdl_t"][0]) if len(D.get("mdl_t", [])) > 1 else 0.0), flush=True)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        main(a)
