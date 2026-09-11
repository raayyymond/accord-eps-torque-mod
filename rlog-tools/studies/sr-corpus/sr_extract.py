# -*- coding: utf-8 -*-
"""sr_extract.py -- SLIM per-SEGMENT extraction for the corpus-wide steering-ratio measurement.

Only the channels the SR-free estimator is allowed to touch (the independence requirement):
    carState        vEgo steeringAngleDeg steeringRateDeg steeringPressed steeringTorque
    livePose        angularVelocityDevice xyz
    liveCalibration rpyCalib + calStatus
    liveParameters  roll angleOffsetDeg stiffnessFactor  (+ steerRatio, CENSUS ONLY, never used in the fit)
    carControl      latActive   (a SPLIT LABEL only -- never enters the estimator)
    carParams       mass wheelbase centerToFront tireStiffnessFront/Rear steerRatio  (first seen)

NOT extracted, deliberately: desiredCurvature, controlsState.torqueState.*, carOutput.torque,
carControl actuators -- those are what we are trying to be independent OF.
CAN is not decoded at all (it is the expensive branch and nothing here needs it).

One npz per SEGMENT under _scratch/segs/ so the run is resumable at 1-minute granularity.
Run:  python sr_extract.py [--jobs N] [--limit N]
"""
import glob, json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # kit root
sys.path.insert(0, os.path.join(ROOT, "rlog-tools"))
RLOGS = os.path.join(ROOT, "analysis-2020accord", "rlogs")
SEGDIR = os.path.join(HERE, "_scratch", "segs")
os.makedirs(SEGDIR, exist_ok=True)

CS_KEYS = ("v", "ang", "rate", "pressed", "drv")


def read_segment(path):
    import zstandard
    from cereal import log as clog
    with open(path, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    it = clog.Event.read_multiple_bytes(data)
    out = {}
    cp = None
    A = out.setdefault
    n = 0
    torn = 0
    while True:
        try:
            evt = next(it)
        except StopIteration:
            break
        except Exception:
            torn = 1
            break
        n += 1
        try:
            w = evt.which()
        except Exception:
            continue
        if w == "can" or w == "sendcan":
            continue
        tm = evt.logMonoTime * 1e-9
        if w == "carState":
            c = evt.carState
            A("cs_t", []).append(tm)
            A("cs_v", []).append(c.vEgo)
            A("cs_ang", []).append(c.steeringAngleDeg)
            A("cs_rate", []).append(c.steeringRateDeg)
            A("cs_pressed", []).append(int(c.steeringPressed))
            A("cs_drv", []).append(c.steeringTorque)
        elif w == "livePose":
            p = evt.livePose.angularVelocityDevice
            A("lp_t", []).append(tm)
            A("lp_wx", []).append(p.x); A("lp_wy", []).append(p.y); A("lp_wz", []).append(p.z)
        elif w == "liveCalibration":
            c = evt.liveCalibration
            r = list(c.rpyCalib) + [0.0, 0.0, 0.0]
            A("cal_t", []).append(tm)
            A("cal_r", []).append(r[0]); A("cal_p", []).append(r[1]); A("cal_y", []).append(r[2])
            A("cal_ok", []).append(int(str(c.calStatus) == "calibrated"))
        elif w == "liveParameters":
            c = evt.liveParameters
            A("lpar_t", []).append(tm)
            A("lpar_roll", []).append(c.roll)
            A("lpar_aoff", []).append(c.angleOffsetDeg)
            A("lpar_stiff", []).append(c.stiffnessFactor)
            A("lpar_sr", []).append(c.steerRatio)
        elif w == "carControl":
            A("cc_t", []).append(tm)
            A("cc_lat", []).append(int(bool(evt.carControl.latActive)))
        elif w == "carParams" and cp is None:
            c = evt.carParams
            cp = dict(mass=c.mass, wheelbase=c.wheelbase, centerToFront=c.centerToFront,
                      tireStiffnessFront=c.tireStiffnessFront, tireStiffnessRear=c.tireStiffnessRear,
                      steerRatio=c.steerRatio, steerActuatorDelay=c.steerActuatorDelay,
                      carFingerprint=str(c.carFingerprint))
    D = {}
    for k, v in out.items():
        D[k] = np.asarray(v, dtype=np.float64 if k.endswith("_t") else np.float32)
    D["carParams_json"] = np.array(json.dumps(cp, default=float))
    D["n_events"] = np.array(n)
    D["torn"] = np.array(torn)
    return D


def out_name(path):
    return os.path.join(SEGDIR, os.path.basename(path).replace("--rlog.zst", ".npz"))


def work(path):
    o = out_name(path)
    if os.path.exists(o):
        return (path, "skip", 0.0, 0)
    t0 = time.time()
    try:
        D = read_segment(path)
    except Exception as exc:
        return (path, "ERR:%s" % str(exc).splitlines()[0][:80], time.time() - t0, 0)
    tmp = o + ".tmp.npz"
    np.savez_compressed(tmp, **D)
    os.replace(tmp, o)
    return (path, "ok", time.time() - t0, len(D.get("cs_t", [])))


def main():
    import multiprocessing as mp
    jobs = 8
    limit = None
    av = sys.argv[1:]
    for i, a in enumerate(av):
        if a == "--jobs":
            jobs = int(av[i + 1])
        if a == "--limit":
            limit = int(av[i + 1])
    segs = sorted(glob.glob(os.path.join(RLOGS, "*--rlog.zst")))
    todo = [p for p in segs if not os.path.exists(out_name(p))]
    print("segments on disk: %d   already done: %d   todo: %d"
          % (len(segs), len(segs) - len(todo), len(todo)), flush=True)
    if limit:
        todo = todo[:limit]
    if not todo:
        return
    t0 = time.time()
    done = 0
    with mp.Pool(jobs) as pool:
        for path, status, dt, ncs in pool.imap_unordered(work, todo, chunksize=1):
            done += 1
            if status != "ok" or done % 10 == 0:
                el = time.time() - t0
                print("[%4d/%4d] %6.1fs elapsed=%6.0fs eta=%6.0fs  %-12s %s"
                      % (done, len(todo), dt, el, el / done * (len(todo) - done), status,
                         os.path.basename(path)), flush=True)
    print("DONE %d segments in %.0f s" % (done, time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
