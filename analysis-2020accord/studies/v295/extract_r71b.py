# -*- coding: utf-8 -*-
"""extract_r71b.py -- ONE-PASS CACHE of route 75604b0a432fdc89_00000071--a7b8ba5d9d (V294 + fork Dom, 2026-09-29/30).

    python analysis-2020accord/studies/v295/extract_r71b.py [--force] [--workers 8]

🛑 THE DONGLE COUNTER WAS REUSED: 00000071--f2c9d073a3 is a DIFFERENT, older route (V293 rev 2, 2026-09-13) and
   00000071--ac50da2a6a a third one.  Everything here is keyed on the FULL counter--hash id.  The kit short tag for this
   route is  r71b_v294  (never "r71").

WHAT IT WRITES (all regenerable, all under gitignored _scratch/):
  <KIT>/_scratch/cache/75604b0a432fdc89_00000071--a7b8ba5d9d/
      can.npz        native-rate CAN, one (t, dat[N,8], dlen, bus) set per (address, bus) -- raw bytes, decode in the loader
      svc.npz        every service stream at its native rate, absolute mono seconds (logMonoTime * 1e-9)
      meta.json      initData (git, params -- ALL keys, decoded), carParams, wall clock anchors, onroadEvents census,
                     starpilotToggles text (distinct values), Testing Ground heartbeat, bookmarks, per-segment spans
  <KIT>/analysis-2020accord/_scratch/cache/v280/r71b_v294{.npz,_b4.npz,_marks.json,_params.json}
      the kit's v280-format cache, decoded EXACTLY as v293_flight_read.extract / extract_v292_routes do, so
      creep20_loop_id.load('r71b_v294') and v293_flight_read.load_route('r71b_v294', <build>) work unchanged.
  <KIT>/rlog-tools/studies/grind/_scratch/cs_r71b_v294.npz   the flight-read control-path cache (build_cs_cache format)
  <KIT>/rlog-tools/_scratch/cache/<route>/CACHE-POINTER.json

SCHEMA: the FORK'S OWN cereal (Dom @ 20d24ab79, copied to <KIT>/_scratch/cereal_fork_native/ with opendbc's car.capnp),
so `starpilotLateralState` and `customReserved9` decode under their real names -- the kit schema's slot-137/116
collisions do not arise.  POSITIVE CONTROL (in the loader's self-test): segment 0 decoded with the kit's PATCHED schema
(v293_flight_read.fork_log_schema) must give identical CAN / carState / torqueState arrays.

ANALYSIS ONLY.  Reads rlogs; writes only under _scratch/.  Sends nothing, flashes nothing.
"""
import argparse
import glob
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
ROUTE = "75604b0a432fdc89_00000071--a7b8ba5d9d"
TAG = "r71b_v294"
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
OUTDIR = os.path.join(KIT, "_scratch", "cache", ROUTE)
V280 = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
GRIND_SCR = os.path.join(KIT, "rlog-tools", "studies", "grind", "_scratch")
PTR = os.path.join(KIT, "rlog-tools", "_scratch", "cache", ROUTE)
SCHEMA = os.path.join(KIT, "_scratch", "cereal_fork_native", "log.capnp")

CAN_ADDRS = (0x0E4, 0x18F, 0x14A, 0x1AB, 0x158, 0x1D0, 0x309, 0x33D)

_log = None


def schema():
    global _log
    if _log is None:
        import capnp
        capnp.remove_import_hook()
        _log = capnp.load(SCHEMA)
    return _log


def seg_files():
    segs = sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % ROUTE)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    return segs


def g(obj, name, default=np.nan):
    try:
        return getattr(obj, name)
    except Exception:
        return default


def fl(x):
    try:
        return float(x)
    except Exception:
        return np.nan


def one_segment(path):
    """decode one segment -> dict of lists (numeric) + meta."""
    import zstandard
    log = schema()
    sn = int(os.path.basename(path).split("--")[2])
    with open(path, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    can = {}          # (addr, bus) -> [t list, dat list, dlen list]
    sendcan = {}
    S = {}            # stream -> dict(field -> list)

    def put(stream, t, **kw):
        d = S.setdefault(stream, {"t": []})
        d["t"].append(t)
        for k, v in kw.items():
            d.setdefault(k, []).append(v)

    meta = dict(seg=sn, lo=None, hi=None, n_events=0, failed=None, onroad_changes=[], onroad_counts={},
                sp_onroad_changes=[], sp_onroad_counts={}, toggles=[], tg=[], bookmarks=[], alerts=[],
                gps_anchor=None, clocks_anchor=None, init=None, carparams=None, which_counts={})
    last_on, last_spon, last_tog, last_alert = None, None, None, None
    it = log.Event.read_multiple_bytes(data)
    while True:
        try:
            evt = next(it)
        except StopIteration:
            break
        except Exception as e:
            meta["failed"] = str(e)[:200]
            break
        try:
            w = evt.which()
        except Exception:
            continue
        meta["n_events"] += 1
        t = evt.logMonoTime * 1e-9
        if meta["lo"] is None:
            meta["lo"] = t
        meta["hi"] = t
        if w == "can":
            if meta.get("lo_can") is None:
                meta["lo_can"] = t
            for m in evt.can:
                a = m.address
                if a in CAN_ADDRS:
                    d = bytes(m.dat)
                    L = can.setdefault((a, m.src), ([], [], []))
                    L[0].append(t); L[1].append((d + b"\0" * 8)[:8]); L[2].append(len(d))
        elif w == "sendcan":
            for m in evt.sendcan:
                if m.address == 0x0E4:
                    d = bytes(m.dat)
                    L = sendcan.setdefault((0x0E4, m.src), ([], [], []))
                    L[0].append(t); L[1].append((d + b"\0" * 8)[:8]); L[2].append(len(d))
        elif w == "carState":
            c = evt.carState
            cr = g(c, "cruiseState", None)
            put("cs", t, angle=fl(c.steeringAngleDeg), rate=fl(c.steeringRateDeg), torque=fl(c.steeringTorque),
                torque_eps=fl(g(c, "steeringTorqueEps")), pressed=float(bool(c.steeringPressed)),
                vego=fl(c.vEgo), aego=fl(c.aEgo), vego_raw=fl(g(c, "vEgoRaw")), yaw=fl(g(c, "yawRate")),
                standstill=float(bool(g(c, "standstill", False))),
                fault_tmp=float(bool(g(c, "steerFaultTemporary", False))),
                fault_perm=float(bool(g(c, "steerFaultPermanent", False))),
                blink_l=float(bool(g(c, "leftBlinker", False))), blink_r=float(bool(g(c, "rightBlinker", False))),
                cruise_en=float(bool(g(cr, "enabled", False))) if cr is not None else np.nan,
                angle_off=fl(g(c, "steeringAngleOffsetDeg")))
        elif w == "controlsState":
            m = evt.controlsState
            try:
                lcs = m.lateralControlState
                wh = lcs.which()
                st = getattr(lcs, wh)
            except Exception:
                wh, st = "none", None
            code = {"pidState": 0, "angleState": 1, "debugState": 2, "torqueState": 3}.get(wh, -1)
            f = lambda nm: fl(g(st, nm)) if st is not None else np.nan  # noqa: E731
            put("ctl", t, which=float(code), active=f("active"), error=f("error"), error_rate=f("errorRate"),
                p=f("p"), i=f("i"), d=f("d"), f=f("f"), output=f("output"), saturated=f("saturated"),
                la_act=f("actualLateralAccel"), la_des=f("desiredLateralAccel"), jerk_des=f("desiredLateralJerk"),
                version=f("version"), curv=fl(g(m, "curvature")), des_curv=fl(g(m, "desiredCurvature")))
        elif w == "carControl":
            m = evt.carControl
            a = m.actuators
            put("cc", t, enabled=float(bool(m.enabled)), lat_active=float(bool(g(m, "latActive", False))),
                torque=fl(a.torque), angle=fl(a.steeringAngleDeg), curv=fl(a.curvature),
                torque_can=fl(g(a, "torqueOutputCan")))
        elif w == "carOutput":
            a = evt.carOutput.actuatorsOutput
            put("co", t, torque=fl(a.torque), torque_can=fl(g(a, "torqueOutputCan")), angle=fl(a.steeringAngleDeg),
                curv=fl(a.curvature))
        elif w == "selfdriveState":
            m = evt.selfdriveState
            try:
                stt = float(m.state.raw)
            except Exception:
                stt = np.nan
            put("sd", t, enabled=float(bool(m.enabled)), active=float(bool(m.active)), state=stt,
                engageable=float(bool(g(m, "engageable", False))))
            try:
                at = str(m.alertType)
            except Exception:
                at = ""
            if at != last_alert:
                meta["alerts"].append(dict(t=t, alertType=at, text1=str(g(m, "alertText1", "")),
                                           text2=str(g(m, "alertText2", ""))))
                last_alert = at
        elif w == "starpilotLateralState":
            s = evt.starpilotLateralState
            put("spl", t, active=float(bool(s.active)), fric_thr=fl(s.frictionThreshold), fric_scale=fl(s.frictionScale),
                ff=fl(s.feedforward), fric_jerk=fl(s.frictionJerk), fric_jerk_dz=fl(s.frictionJerkDeadzone),
                lsf=fl(s.lowSpeedFactor), unwind=float(bool(s.unwindDetected)),
                dob=fl(g(s, "accordObserverTorque", 0.0)), dob_frozen=float(bool(g(s, "accordObserverFrozen", False))))
        elif w == "modelV2":
            m = evt.modelV2
            try:
                dc = fl(m.action.desiredCurvature)
            except Exception:
                dc = np.nan
            put("mdl", t, des_curv=dc, frame=fl(g(m, "frameId")))
        elif w == "drivingModelData":
            m = evt.drivingModelData
            try:
                dc = fl(m.action.desiredCurvature)
            except Exception:
                dc = np.nan
            put("dmd", t, des_curv=dc)
        elif w == "liveParameters":
            m = evt.liveParameters
            put("lpar", t, sr=fl(m.steerRatio), roll=fl(m.roll), off=fl(m.angleOffsetDeg),
                off_avg=fl(m.angleOffsetAverageDeg), stiff=fl(m.stiffnessFactor), valid=float(bool(m.valid)),
                sr_valid=float(bool(g(m, "steerRatioValid", True))), sensor_valid=float(bool(g(m, "sensorValid", False))),
                sr_std=fl(g(m, "steerRatioStd")))
        elif w == "livePose":
            m = evt.livePose
            av, ac, on = m.angularVelocityDevice, m.accelerationDevice, m.orientationNED
            put("pose", t, wz=fl(av.z), wx=fl(av.x), wy=fl(av.y), ay=fl(ac.y), ax=fl(ac.x), roll=fl(on.x),
                pitch=fl(on.y), ok=float(bool(g(m, "inputsOK", False))))
        elif w == "liveTorqueParameters":
            m = evt.liveTorqueParameters
            put("ltp", t, laf=fl(m.latAccelFactorFiltered), off=fl(m.latAccelOffsetFiltered),
                fric=fl(m.frictionCoefficientFiltered), laf_raw=fl(m.latAccelFactorRaw), off_raw=fl(m.latAccelOffsetRaw),
                fric_raw=fl(m.frictionCoefficientRaw), valid=float(bool(m.liveValid)),
                use=float(bool(g(m, "useParams", False))), pts=fl(g(m, "totalBucketPoints")), cal=fl(g(m, "calPerc")))
        elif w == "liveDelay":
            m = evt.liveDelay
            try:
                stt = float(m.status.raw)
            except Exception:
                stt = np.nan
            put("ldel", t, delay=fl(m.lateralDelay), est=fl(g(m, "lateralDelayEstimate")),
                est_std=fl(g(m, "lateralDelayEstimateStd")), blocks=fl(m.validBlocks), status=stt,
                cal=fl(g(m, "calPerc")))
        elif w == "pandaStates":
            for i_, ps in enumerate(evt.pandaStates):
                if i_ > 0:
                    break
                try:
                    sm = float(ps.safetyModel.raw)
                except Exception:
                    sm = np.nan
                try:
                    nf = float(len(ps.faults))
                except Exception:
                    nf = np.nan
                put("panda", t, allowed=float(bool(ps.controlsAllowed)), rx_inv=fl(g(ps, "safetyRxInvalid")),
                    tx_blk=fl(g(ps, "safetyTxBlocked")), safety=sm, nfaults=nf,
                    rxchk_inv=float(bool(g(ps, "safetyRxChecksInvalid", False))), ign=float(bool(g(ps, "ignitionLine", False))))
        elif w == "onroadEvents":
            names = []
            for e in evt.onroadEvents:
                try:
                    nm = str(e.name)
                except Exception:
                    nm = "?"
                fl_ = [k for k in ("softDisable", "immediateDisable", "userDisable", "noEntry", "warning",
                                   "overrideLateral") if bool(g(e, k, False))]
                names.append(nm + ("[" + ",".join(fl_) + "]" if fl_ else ""))
                meta["onroad_counts"][nm] = meta["onroad_counts"].get(nm, 0) + 1
            key = tuple(sorted(names))
            if key != last_on:
                meta["onroad_changes"].append(dict(t=t, events=list(key)))
                last_on = key
        elif w == "starpilotOnroadEvents":
            names = []
            for e in evt.starpilotOnroadEvents.events:
                try:
                    nm = str(e.name)
                except Exception:
                    nm = "?"
                names.append(nm)
                meta["sp_onroad_counts"][nm] = meta["sp_onroad_counts"].get(nm, 0) + 1
            key = tuple(sorted(names))
            if key != last_spon:
                meta["sp_onroad_changes"].append(dict(t=t, events=list(key)))
                last_spon = key
        elif w == "starpilotPlan":
            try:
                tg = str(evt.starpilotPlan.starpilotToggles)
            except Exception:
                tg = None
            if tg is not None and tg != last_tog:
                meta["toggles"].append(dict(t=t, text=tg))
                last_tog = tg
        elif w == "customReserved9":
            m = evt.customReserved9
            meta["tg"].append(dict(t=t, slotId=str(m.slotId), slotName=str(m.slotName), variant=str(m.variant),
                                   variantLabel=str(m.variantLabel), reason=str(m.reason)))
        elif w == "userBookmark":
            meta["bookmarks"].append(dict(t=t))
        elif w == "gpsLocationExternal" and meta["gps_anchor"] is None:
            try:
                m = evt.gpsLocationExternal
                if int(m.unixTimestampMillis) > 1.6e12:
                    meta["gps_anchor"] = dict(t=t, unix_ms=int(m.unixTimestampMillis))
            except Exception:
                pass
        elif w == "clocks" and meta["clocks_anchor"] is None:
            try:
                meta["clocks_anchor"] = dict(t=t, wall_ns=int(evt.clocks.wallTimeNanos))
            except Exception:
                pass
        elif w == "initData" and meta["init"] is None:
            m = evt.initData
            params = {}
            try:
                for e in m.params.entries:
                    raw = bytes(e.value)
                    try:
                        s = raw.decode("utf-8")
                        params[e.key] = s if len(s) <= 4000 else s[:4000] + "...<truncated %d>" % len(s)
                    except UnicodeDecodeError:
                        params[e.key] = "<binary %d bytes>" % len(raw)
            except Exception as ex:
                params["_error"] = str(ex)[:200]
            try:
                dev = str(m.deviceType)
            except Exception:
                dev = "?"
            meta["init"] = dict(t=t, gitCommit=str(m.gitCommit), gitBranch=str(m.gitBranch), gitRemote=str(m.gitRemote),
                                gitCommitDate=str(g(m, "gitCommitDate", "")), gitSrcCommit=str(g(m, "gitSrcCommit", "")),
                                dirty=bool(m.dirty), version=str(m.version), osVersion=str(g(m, "osVersion", "")),
                                deviceType=dev, wallTimeNanos=int(g(m, "wallTimeNanos", 0)), params=params)
        elif w == "carParams" and meta["carparams"] is None:
            m = evt.carParams
            lt = {}
            try:
                wh = m.lateralTuning.which()
                lt["which"] = str(wh)
                if wh == "torque":
                    tt = m.lateralTuning.torque
                    lt.update(friction=fl(tt.friction), latAccelFactor=fl(tt.latAccelFactor),
                              latAccelOffset=fl(tt.latAccelOffset), steeringAngleDeadzoneDeg=fl(tt.steeringAngleDeadzoneDeg))
                elif wh == "pid":
                    pp = m.lateralTuning.pid
                    lt.update(kpBP=list(pp.kpBP), kpV=list(pp.kpV), kiBP=list(pp.kiBP), kiV=list(pp.kiV), kf=fl(pp.kf))
            except Exception as ex:
                lt["_error"] = str(ex)[:120]
            try:
                lp = m.lateralParams
                lt["torqueBP"] = list(lp.torqueBP); lt["torqueV"] = list(lp.torqueV)
            except Exception:
                pass
            try:
                sct = str(m.steerControlType)
            except Exception:
                sct = "?"
            meta["carparams"] = dict(t=t, carFingerprint=str(g(m, "carFingerprint", "")), steerRatio=fl(m.steerRatio),
                                     steerActuatorDelay=fl(m.steerActuatorDelay), steerLimitTimer=fl(g(m, "steerLimitTimer")),
                                     wheelbase=fl(m.wheelbase), mass=fl(m.mass), centerToFront=fl(m.centerToFront),
                                     tireStiffnessFactor=fl(g(m, "tireStiffnessFactor")), minSteerSpeed=fl(g(m, "minSteerSpeed")),
                                     steerControlType=sct, lateralTuning=lt,
                                     openpilotLongitudinalControl=bool(g(m, "openpilotLongitudinalControl", False)))
        meta["which_counts"][w] = meta["which_counts"].get(w, 0) + 1
    # to arrays
    can_a = {}
    for (a, b), (T, Dd, Ln) in can.items():
        can_a[(a, b)] = (np.asarray(T), np.frombuffer(b"".join(Dd), np.uint8).reshape(-1, 8), np.asarray(Ln, np.uint8))
    snd_a = {}
    for (a, b), (T, Dd, Ln) in sendcan.items():
        snd_a[(a, b)] = (np.asarray(T), np.frombuffer(b"".join(Dd), np.uint8).reshape(-1, 8), np.asarray(Ln, np.uint8))
    S_a = {s: {k: np.asarray(v, float) for k, v in d.items()} for s, d in S.items()}
    return dict(seg=sn, can=can_a, sendcan=snd_a, S=S_a, meta=meta)


def i16be_arr(dat, i):
    v = (dat[:, i].astype(np.int32) << 8) | dat[:, i + 1].astype(np.int32)
    return np.where(v >= 32768, v - 65536, v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    segs = seg_files()
    have = [int(os.path.basename(p).split("--")[2]) for p in segs]
    print("route %s: %d segments on disk %s" % (ROUTE, len(segs), have), flush=True)
    if os.path.exists(os.path.join(OUTDIR, "svc.npz")) and not a.force:
        print("cache exists; --force to rebuild"); return
    t0 = time.time()
    with Pool(min(a.workers, len(segs))) as pool:
        R = pool.map(one_segment, segs)
    R.sort(key=lambda r: r["seg"])
    print("decoded in %.1f s" % (time.time() - t0), flush=True)
    # ---------------- concatenate ----------------
    os.makedirs(OUTDIR, exist_ok=True)
    can_out, keys = {}, set()
    for r in R:
        keys |= set(r["can"])
    for (addr, bus) in sorted(keys):
        pre = "x%03X_b%d" % (addr, bus)
        parts = [r["can"][(addr, bus)] for r in R if (addr, bus) in r["can"]]
        can_out[pre + "_t"] = np.concatenate([p[0] for p in parts])
        can_out[pre + "_dat"] = np.concatenate([p[1] for p in parts])
        can_out[pre + "_dlen"] = np.concatenate([p[2] for p in parts])
    skeys = set()
    for r in R:
        skeys |= set(r["sendcan"])
    for (addr, bus) in sorted(skeys):
        pre = "send_x%03X_b%d" % (addr, bus)
        parts = [r["sendcan"][(addr, bus)] for r in R if (addr, bus) in r["sendcan"]]
        can_out[pre + "_t"] = np.concatenate([p[0] for p in parts])
        can_out[pre + "_dat"] = np.concatenate([p[1] for p in parts])
        can_out[pre + "_dlen"] = np.concatenate([p[2] for p in parts])
    np.savez_compressed(os.path.join(OUTDIR, "can.npz"), **can_out)
    svc = {}
    streams = set()
    for r in R:
        streams |= set(r["S"])
    for s in sorted(streams):
        flds = set()
        for r in R:
            if s in r["S"]:
                flds |= set(r["S"][s])
        for f in sorted(flds):
            svc["%s_%s" % (s, f)] = np.concatenate([r["S"][s].get(f, np.full(len(r["S"][s]["t"]), np.nan))
                                                   for r in R if s in r["S"]])
    np.savez_compressed(os.path.join(OUTDIR, "svc.npz"), **svc)
    # ---------------- meta ----------------
    M = [r["meta"] for r in R]
    init = next((m["init"] for m in M if m["init"]), None)
    inits = [dict(seg=m["seg"], gitCommit=m["init"]["gitCommit"], dirty=m["init"]["dirty"],
                  wallTimeNanos=m["init"]["wallTimeNanos"]) for m in M if m["init"]]
    oc = {}
    for m in M:
        for k, v in m["onroad_counts"].items():
            oc[k] = oc.get(k, 0) + v
    spc = {}
    for m in M:
        for k, v in m["sp_onroad_counts"].items():
            spc[k] = spc.get(k, 0) + v
    # starpilotPlan.starpilotToggles is a JSON text republished at 20 Hz; keep the FIRST full dict and then only the
    # keys that changed (with the time), so meta.json stays small.
    # 🛑 the field is EMPTY on most frames (published only when it changes); an empty/unparseable text is skipped,
    # otherwise every key "changes" on every alternation (first extraction reported 1961 bogus changes).
    tog_first, tog_changes, prev = None, [], None
    for m in M:
        for x in m["toggles"]:
            try:
                d = json.loads(x["text"])
            except Exception:
                continue
            if not isinstance(d, dict) or not d:
                continue
            if tog_first is None:
                tog_first = dict(t=x["t"], toggles=d)
            elif prev is not None:
                ch = {k: d.get(k) for k in set(d) | set(prev) if d.get(k) != prev.get(k)}
                if ch:
                    tog_changes.append(dict(t=x["t"], changed=ch))
            prev = d
    toggles = dict(first=tog_first, changes=tog_changes)
    alerts, last = [], None
    for m in M:
        for x in m["alerts"]:
            if x["alertType"] != last:
                alerts.append(x); last = x["alertType"]
    meta = dict(route=ROUTE, tag=TAG, schema=SCHEMA, fork_schema_commit="20d24ab79 (Dom HEAD at extraction)",
                segments=[m["seg"] for m in M],
                seg_spans={str(m["seg"]): dict(lo=m["lo"], lo_can=m.get("lo_can"), hi=m["hi"], n_events=m["n_events"],
                                               failed=m["failed"])
                           for m in M},
                init=init, init_per_segment=inits,
                carparams=next((m["carparams"] for m in M if m["carparams"]), None),
                gps_anchor=next((m["gps_anchor"] for m in M if m["gps_anchor"]), None),
                gps_anchor_per_seg={str(m["seg"]): m["gps_anchor"] for m in M},
                clocks_anchor=next((m["clocks_anchor"] for m in M if m["clocks_anchor"]), None),
                onroad_event_msg_counts=oc, onroad_changes=[dict(seg=m["seg"], **c) for m in M for c in m["onroad_changes"]],
                sp_onroad_event_msg_counts=spc,
                sp_onroad_changes=[dict(seg=m["seg"], **c) for m in M for c in m["sp_onroad_changes"]],
                starpilot_toggles=toggles, alerts=alerts,
                testing_ground=[x for m in M for x in m["tg"]][:50],
                bookmarks=[dict(seg=m["seg"], **b) for m in M for b in m["bookmarks"]],
                which_counts={k: sum(m["which_counts"].get(k, 0) for m in M)
                              for k in sorted(set().union(*[m["which_counts"] for m in M]))})
    json.dump(meta, open(os.path.join(OUTDIR, "meta.json"), "w"), indent=1, default=str)
    print("wrote can.npz (%d keys), svc.npz (%d keys), meta.json" % (len(can_out), len(svc)), flush=True)
    write_kit_caches(can_out, svc, meta)
    print("done in %.1f s" % (time.time() - t0))


def write_kit_caches(can_out, svc, meta):
    """the kit's v280-format cache + the flight read's control-path cache, decoded EXACTLY as
    v293_flight_read.extract / build_cs_cache do (src 1 for 0x18F/0x14A/0x1AB, src 129 for 0xE4)."""
    c18 = "x18F_b1"; c14 = "x14A_b1"; c1ab = "x1AB_b1"; ce4 = "x0E4_b129"
    d18 = can_out[c18 + "_dat"]; l18 = can_out[c18 + "_dlen"]
    k = l18 >= 5
    D = dict(t18=can_out[c18 + "_t"][k], tq=i16be_arr(d18[k], 0).astype(float), rate=i16be_arr(d18[k], 2).astype(float),
             sca=((d18[k, 4] >> 3) & 1).astype(int))
    d14 = can_out[c14 + "_dat"]; l14 = can_out[c14 + "_dlen"]
    k = l14 >= 4
    D["t14"] = can_out[c14 + "_t"][k]; D["ang"] = i16be_arr(d14[k], 0) * -0.1
    kb = l14 >= 5
    B4 = dict(t14b=can_out[c14 + "_t"][kb], b4=d14[kb, 4].astype(int))
    dab = can_out[c1ab + "_dat"]; lab = can_out[c1ab + "_dlen"]
    k = lab >= 2
    D["t1ab"] = can_out[c1ab + "_t"][k]; D["b0"] = dab[k, 0].astype(int); D["b1"] = dab[k, 1].astype(int)
    de4 = can_out[ce4 + "_dat"]; le4 = can_out[ce4 + "_dlen"]
    k = le4 >= 3
    D["te4"] = can_out[ce4 + "_t"][k]; D["cmd"] = i16be_arr(de4[k], 0).astype(float); D["req"] = ((de4[k, 2] >> 7) & 1).astype(int)
    D["tcs"] = svc["cs_t"]; D["vego"] = svc["cs_vego"]; D["cs_ang"] = svc["cs_angle"]; D["cs_tq"] = svc["cs_torque"]
    D["cs_press"] = svc["cs_pressed"].astype(int); D["cs_rate"] = svc["cs_rate"]
    os.makedirs(V280, exist_ok=True)
    np.savez(os.path.join(V280, TAG + ".npz"), **D)
    np.savez(os.path.join(V280, TAG + "_b4.npz"), **B4)
    t0 = float(D["t18"][0])
    segs = meta["segments"]
    spans = meta["seg_spans"]
    # 🛑 a segment's FIRST event is initData / sentinel carrying the PROCESS-START stamp (28.96 s on every segment of
    # this route) -- the segment start is its first CAN event, recorded per segment as lo_can.
    lo_can = {s: float(spans[str(s)]["lo_can"]) for s in segs}
    marks = []
    for b in meta["bookmarks"]:
        marks.append(dict(seg=b["seg"], mono=b["t"], t_route=b["t"] - t0, t_in_seg=b["t"] - lo_can[b["seg"]]))
    out = dict(t0_mono=t0, route_prefix=ROUTE, tag=TAG, marks=marks, present_segments=segs, missing_segments=[],
               failed_segments=[dict(seg=s, err=spans[str(s)]["failed"]) for s in segs if spans[str(s)]["failed"]],
               gaps=[dict(after_seg=a_, before_seg=b_, gap_s=round(lo_can[b_] - spans[str(a_)]["hi"], 3),
                          contiguous_index=(b_ == a_ + 1)) for a_, b_ in zip(segs, segs[1:])],
               segs={str(s): dict(lo_route=lo_can[s] - t0, hi_route=spans[str(s)]["hi"] - t0,
                                  lo_can_route=lo_can[s] - t0) for s in segs},
               lo_route_note="use lo_can_route; lo_route is the first event of the segment",
               written_by="analysis-2020accord/studies/v295/extract_r71b.py")
    json.dump(out, open(os.path.join(V280, TAG + "_marks.json"), "w"), indent=1)
    pd = dict(meta["init"]["params"]) if meta["init"] else {}
    pd["_all_keys_n"] = len(pd); pd["_seg"] = 0; pd["_written_by"] = "extract_r71b.py (ALL initData params)"
    pd["GitCommit_initData"] = meta["init"]["gitCommit"] if meta["init"] else None
    pd["GitBranch_initData"] = meta["init"]["gitBranch"] if meta["init"] else None
    json.dump(pd, open(os.path.join(V280, TAG + "_params.json"), "w"), indent=1)
    # control-path cache in build_cs_cache's format
    C = dict(t_cs=svc["ctl_t"], la_des=svc["ctl_la_des"], la_act=svc["ctl_la_act"], f=svc["ctl_f"], p=svc["ctl_p"],
             i=svc["ctl_i"], err=svc["ctl_error"], out=svc["ctl_output"], active=svc["ctl_active"], sat=svc["ctl_saturated"],
             version=svc["ctl_version"], des_curv=svc["ctl_des_curv"], curv=svc["ctl_curv"],
             t_sp=svc.get("spl_t", np.zeros(0)), sp_ff=svc.get("spl_ff", np.zeros(0)),
             sp_active=svc.get("spl_active", np.zeros(0)), sp_lsf=svc.get("spl_lsf", np.zeros(0)),
             sp_dob=svc.get("spl_dob", np.zeros(0)), sp_dobfrozen=svc.get("spl_dob_frozen", np.zeros(0)),
             t_ltp=svc["ltp_t"], ltp_off=svc["ltp_off"], ltp_fac=svc["ltp_laf"], ltp_fric=svc["ltp_fric"],
             ltp_valid=svc["ltp_valid"], t_lpar=svc["lpar_t"], roll=svc["lpar_roll"], _patched=np.asarray([1.0]))
    os.makedirs(GRIND_SCR, exist_ok=True)
    np.savez(os.path.join(GRIND_SCR, "cs_%s.npz" % TAG), **C)
    os.makedirs(PTR, exist_ok=True)
    json.dump(dict(route=ROUTE, tag=TAG, v280_cache=os.path.join(V280, TAG + ".npz"),
                   b4_cache=os.path.join(V280, TAG + "_b4.npz"), marks=os.path.join(V280, TAG + "_marks.json"),
                   params=os.path.join(V280, TAG + "_params.json"), full_cache=OUTDIR,
                   loader="analysis-2020accord/studies/v295/lib/r71b_cache.py",
                   note="v280-format cache decoded as extract_v292_routes.py; the full native-rate cache is full_cache"),
              open(os.path.join(PTR, "CACHE-POINTER.json"), "w"), indent=1)
    print("wrote kit caches: %s.npz / _b4 / _marks / _params, cs_%s.npz, CACHE-POINTER" % (TAG, TAG), flush=True)


if __name__ == "__main__":
    main()
