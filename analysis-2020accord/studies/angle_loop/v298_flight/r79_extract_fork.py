# -*- coding: utf-8 -*-
"""r79_extract_fork.py -- ONE-PASS FORK-SIDE CACHE OF A ROUTE (route 79 = the V298 angle-loop flight by default).

    python analysis-2020accord/studies/angle_loop/v298_flight/r79_extract_fork.py [--procs 16]
            [--route <dongle_counter--hash>] [--commit auto|<sha>] [--out <npz>]

GENERALISED 2026-10-02 FOR DRIVE 2 (V299); route 79's arrays unchanged (a re-run on r79 reproduces every array of the
existing r79_fork.npz bit for bit; the only additions are the keys below and meta fields):
  * --route: any route (default route 79).  Output: CACHE/r79_fork.npz for route 79 (the panel's path, unchanged),
    else CACHE/<tag>_fork.npz, tag = r<counter>_<hash6>_al (the drive read's own tag; the counter alone is REUSED).
    ALIGN 2026-10-02: the name comes from ONE function, drive_read_v299.fork_cache_path (default_out calls it; the
    drive read passes it as --out and never re-runs this script when that file exists).  --print-out prints the path.
  * THE SCHEMA IS PINNED TO A COMMIT, not to whatever the fork's working tree holds: each schema file is read with
    `git -C <fork> show <commit>:<path>` (opendbc_repo is a vendored tree in the fork, not a submodule, so one
    commit pins all five files; the blobs are git's canonical LF text -- the clone has core.autocrlf=true, so the old
    working-tree copy, stamp 'sha1 51e7b68af19fc408', was the same five files with CRLF: EVIDENCE, each working-tree
    file == its 2712e1336 blob after CRLF->LF, all five; the pinned stamp at 2712e1336 is 'sha1 dc2036e24425c226').
    --commit auto (default) = the route's own initData GitCommit, read from segment 0
    with the bootstrap schema at 2712e1336 (initData is in the stable base schema).  The full sha, the schema files'
    sha1 and whether the schema defines starpilotCarState.accordAngleStatus are written into meta_json.
  * NEW KEYS: cs_canvalid (carState.canValid -- the spec's F8 "any canValid drop in angle mode") and spcs_angstat
    (starpilotCarState.accordAngleStatus @31, the V299 fork's status word, DESIGN-V299-SYNTHESIS-rev2 §2.2 F8:
    4 rate/jerk-bound, 8 EPS-torque stale/bad, 16 clip-bound) -- spcs_angstat only when the pinned schema defines it.

WHAT IT DOES
  Decodes every segment of 75604b0a432fdc89_00000079--a1f5d2a272 ONCE, in parallel (one process per
  segment), with the FORK'S OWN cereal schema (raayyymond-StarPilot/StarPilot @ Dom 2712e1336 -- the
  commit initData.params.GitCommit names for this route), and writes

      analysis-2020accord/_scratch/cache/v280/r79_fork.npz

  holding the openpilot/fork side of the drive (controlsState angleState, carControl, carOutput,
  liveParameters, liveDelay, modelV2, carState, selfdriveState, onroadEvents, pandaStates, the 0xE4
  frames from every source, carParams scalars, initData params).  The WIRE cache
  (r79_a1f5d2_al.npz: 0x18F / 0x14A / 0x1AB / the fork's echoed 0xE4 / carState) is NOT redone; this
  cache ADDS to it, on the SAME clock: every t_* here is evt.logMonoTime * 1e-9 (absolute mono seconds),
  exactly as v293_flight_read.extract() stamps the wire cache's t14 / t18 / te4 / tcs.  The script
  verifies that by matching its own carState rows to the wire cache's (tcs, cs_ang) and reports the
  residual.

WHY THE FORK'S OWN SCHEMA, NOT THE KIT'S PATCHED ONE
  v293_flight_read.fork_log_schema() patches a COPY of the KIT's cereal so two colliding custom structs
  (@137 starpilotLateralState vs the kit's epsTelemetry; @116) decode.  That patch was written against
  fork 4247cb09e.  For a route logged at 2712e1336 the authoritative schema is the fork's own: same
  builder pattern (copy into _scratch, stamp, capnp.load) -- but the copy is of the fork's
  cereal/{log,custom,legacy}.capnp + include/c++.capnp + opendbc_repo/opendbc/car/car.capnp (cereal/car.capnp
  is a git symlink to it, which a Windows checkout materialises as a 37-byte text file).  No collision
  exists in the fork's own schema, so no patch is needed.  The kit's schema is NOT touched.

PERFORMANCE (operator rule): one decode pass per segment, multiprocessing over the 21 segments, lists
-> np.array at the end of each worker.  Measured wall time is printed and written into the npz
(`meta_wall_time_s`) and the README.

ANALYSIS ONLY.  Reads rlogs; writes only the npz above, its README, and the schema copy under the repo's
_scratch/.  Sends nothing, flashes nothing.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  Put EVERY kit root in the repo, and every code subfolder under
# each, on sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import argparse
import glob
import hashlib
import io
import json
import os
import shutil
import sys
import time
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT_A = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))          # analysis-2020accord
REPO = os.path.dirname(KIT_A)
RLOGS = os.path.join(KIT_A, "rlogs")
CACHE = os.path.join(KIT_A, "_scratch", "cache", "v280")
PREFIX = "75604b0a432fdc89_00000079--a1f5d2a272"
WIRE = os.path.join(CACHE, "r79_a1f5d2_al.npz")
OUT = os.path.join(CACHE, "r79_fork.npz")
FORK = "C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot"
FORK_COMMIT = "2712e1336"            # the BOOTSTRAP / default pin (route 79's initData GitCommit)
SCHEMA_DIR = os.path.join(REPO, "_scratch", "cereal_fork_dom_" + FORK_COMMIT)


def _naming():
    """THE fork-cache naming lives in ONE place, drive_read_v299.route_tag / fork_cache_path (ALIGN 2026-10-02): the
    drive read looks up exactly the file this script writes.  Imported lazily, in the parent process only (the decode
    workers never call it)."""
    import drive_read_v299 as V2
    return V2


def route_tag(prefix):
    """the drive read's cache tag for a route: r<counter>_<hash6>_al (drive_read_v299.route_tag)."""
    return _naming().route_tag(prefix)


def default_out(prefix):
    """route 79 with no --out: the panel's legacy CACHE/r79_fork.npz (unchanged); every other route: the drive read's
    own name, drive_read_v299.fork_cache_path(prefix) = CACHE/<route_tag>_fork.npz.  The drive read always passes that
    path as --out, so the two agree for route 79 as well (CACHE/r79_a1f5d2_al_fork.npz)."""
    return OUT if prefix == PREFIX else str(_naming().fork_cache_path(prefix, CACHE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PARAM_SUBSTR = ("Steer", "Accord", "Lateral", "Torque", "Lane", "AlwaysOn")
MD_K = 17          # modelV2 trajectory points kept (T_IDXS[0..16] = 0 .. 2.5 s)


# ======================================================================================================
# 0.  THE SCHEMA -- the fork's own cereal, copied into _scratch and stamped (v293_flight_read pattern)
# ======================================================================================================
_SRC = (("cereal/log.capnp", "log.capnp"), ("cereal/custom.capnp", "custom.capnp"),
        ("cereal/legacy.capnp", "legacy.capnp"), ("cereal/include/c++.capnp", "include/c++.capnp"),
        ("opendbc_repo/opendbc/car/car.capnp", "car.capnp"))


def _git(*args):
    import subprocess
    return subprocess.run(["git", "-C", FORK] + list(args), check=True, capture_output=True).stdout


def resolve_commit(commit):
    """full sha of <commit> in the fork repo (SystemExit if the fork clone does not have it: fetch it first)."""
    try:
        return _git("rev-parse", "--verify", commit + "^{commit}").decode().strip()
    except Exception as e:
        raise SystemExit("fork commit %s is not in %s -- fetch it (%s)" % (commit, FORK, str(e)[:120]))


def build_schema(commit=FORK_COMMIT):
    """the fork's cereal AT <commit> (git show, never the working tree) copied into _scratch and stamped.
    -> (stamp, schema_dir, full sha).  The stamp keeps the pre-2026-10-02 format ('fork <short> sha1 <16 hex>')."""
    full = resolve_commit(commit)
    short = full[:9]
    blobs = [_git("show", "%s:%s" % (full, s)) for s, _ in _SRC]
    h = hashlib.sha1()
    for b in blobs:
        h.update(b)
    schema_dir = os.path.join(REPO, "_scratch", "cereal_fork_" + short)
    want = "fork %s sha1 %s\n" % (short, h.hexdigest()[:16])
    stamp = os.path.join(schema_dir, ".stamp")
    have = io.open(stamp, encoding="utf-8").read() if os.path.exists(stamp) else ""
    if have != want:
        if os.path.isdir(schema_dir):
            shutil.rmtree(schema_dir)
        os.makedirs(os.path.join(schema_dir, "include"))
        for b, (_, d) in zip(blobs, _SRC):
            with open(os.path.join(schema_dir, d), "wb") as fh:
                fh.write(b)
        io.open(stamp, "w", encoding="utf-8").write(want)
    return want.strip(), schema_dir, full


_LOG = {}


def load_log(schema_dir=SCHEMA_DIR):
    if schema_dir not in _LOG:
        import capnp
        capnp.remove_import_hook()
        _LOG[schema_dir] = capnp.load(os.path.join(schema_dir, "log.capnp"))
    return _LOG[schema_dir]


def route_commit_fast(seg0):
    """the 40-hex GitCommit of a route from segment 0's raw bytes (the first 40-hex run within 256 bytes after the
    initData param key b"GitCommit").  A GUESS that main() verifies against the decoded initData."""
    import re
    import zstandard
    data = zstandard.ZstdDecompressor().stream_reader(open(seg0, "rb")).read(16 << 20)
    i = data.find(b"GitCommit")
    m = re.search(rb"[0-9a-f]{40}", data[i:i + 256]) if i >= 0 else None
    return m.group(0).decode() if m else None


def route_commit(seg0, schema_dir):
    """initData.params GitCommit of a route, read from its first segment with the bootstrap schema."""
    import zstandard
    log = load_log(schema_dir)
    data = zstandard.ZstdDecompressor().stream_reader(open(seg0, "rb")).read()
    for ev in log.Event.read_multiple_bytes(data):
        try:
            if ev.which() == "initData":
                for e in ev.initData.params.entries:
                    if str(e.key) == "GitCommit":
                        return bytes(e.value).decode("utf-8", "replace").strip()
                return str(ev.initData.gitCommit).strip() or None
        except Exception:
            continue
    return None


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 65536 if v >= 32768 else v


# ======================================================================================================
# 1.  THE WORKER -- one segment, one pass
# ======================================================================================================
def _carparams_dict(cp):
    out = {}
    for k in ("carFingerprint", "brand", "maxLateralAccel", "steerActuatorDelay", "steerRatio", "wheelbase",
              "centerToFront", "mass", "tireStiffnessFront", "tireStiffnessRear", "tireStiffnessFactor",
              "steerLimitTimer", "minSteerSpeed", "minEnableSpeed", "lateralSmoothSeconds", "steerAtStandstill",
              "alternativeExperience", "flags", "pcmCruise", "openpilotLongitudinalControl", "rotationalInertia",
              "steerRatioRear", "fingerprintSource", "passive", "dashcamOnly"):
        try:
            v = getattr(cp, k)
            out[k] = v if isinstance(v, (bool, int, float, str)) else str(v)
        except Exception as e:
            out[k] = "ERR " + str(e)[:60]
    try:
        out["steerControlType"] = str(cp.steerControlType)
    except Exception:
        pass
    try:
        out["lateralTuning_which"] = str(cp.lateralTuning.which())
        out["lateralTuning"] = cp.lateralTuning.to_dict()
    except Exception:
        pass
    try:
        out["lateralParams"] = cp.lateralParams.to_dict()
    except Exception:
        pass
    try:
        out["safetyConfigs"] = [dict(safetyModel=str(s.safetyModel), safetyParam=int(s.safetyParam))
                                for s in cp.safetyConfigs]
    except Exception:
        pass
    try:
        out["carFw_eps"] = [dict(ecu=str(f.ecu), fwVersion=bytes(f.fwVersion).decode("latin-1"),
                                 address=int(f.address), bus=int(f.bus))
                            for f in cp.carFw if str(f.ecu) == "eps"]
    except Exception:
        pass
    return out


def work(job):
    import zstandard
    path, schema_dir = job if isinstance(job, tuple) else (job, SCHEMA_DIR)
    log = load_log(schema_dir)
    has_angstat = None                  # does the pinned schema define starpilotCarState.accordAngleStatus?
    sn = int(os.path.basename(path).split("--")[2])
    data = zstandard.ZstdDecompressor().stream_reader(open(path, "rb")).read()
    L = {}

    def ap(k, v):
        L.setdefault(k, []).append(v)

    meta = dict(seg=sn, n_events=0, failed=None, initdata=None, carparams=None, sp_toggles=None,
                sp_toggles_changes=0, counts={})
    counts = meta["counts"]
    sp_tog_last = None
    it = log.Event.read_multiple_bytes(data)
    while True:
        try:
            ev = next(it)
        except StopIteration:
            break
        except Exception as e:
            meta["failed"] = str(e)[:160]
            break
        try:
            w = ev.which()
        except Exception:
            continue
        meta["n_events"] += 1
        counts[w] = counts.get(w, 0) + 1
        t = ev.logMonoTime * 1e-9

        if w == "can":
            for m in ev.can:
                if m.address != 0xE4:
                    continue
                s = m.src
                d = bytes(m.dat)
                if len(d) < 5:
                    continue
                # src = bus (+0x80 RETURNED = our TX echo, +0xC0 REJECTED = blocked by panda safety;
                # StarPilot selfdrive/pandad/panda.h CAN_RETURNED_BUS_OFFSET / CAN_REJECTED_BUS_OFFSET)
                key = {0: "e4rx0", 1: "e4rx1", 2: "e4cam", 128: "e4tx0", 129: "e4tx1", 192: "e4rej0",
                       193: "e4rej1", 194: "e4rej2"}.get(s)
                if key is None:
                    key = "e4src%d" % s
                ap("t_" + key, t)
                ap(key + "_raw", d[:5])
        elif w == "sendcan":
            for m in ev.sendcan:
                if m.address != 0xE4:
                    continue
                d = bytes(m.dat)
                if len(d) < 5:
                    continue
                ap("t_e4send", t)
                ap("e4send_raw", d[:5])
                ap("e4send_bus", m.src)
        elif w == "controlsState":
            c = ev.controlsState
            ap("t_ctl", t)
            ap("ctl_curv", c.curvature)
            ap("ctl_dcurv", c.desiredCurvature)
            ls = c.lateralControlState
            lw = str(ls.which())
            ap("ctl_lat_is_angle", lw == "angleState")
            if lw == "angleState":
                a = ls.angleState
                ap("ang_des", a.steeringAngleDesiredDeg)
                ap("ang_meas", a.steeringAngleDeg)
                ap("ang_active", a.active)
                ap("ang_sat", a.saturated)
                ap("ang_output", a.output)
            else:
                ap("ang_des", np.nan); ap("ang_meas", np.nan); ap("ang_active", False)
                ap("ang_sat", False); ap("ang_output", np.nan)
                counts["ctl_lat_" + lw] = counts.get("ctl_lat_" + lw, 0) + 1
        elif w == "carControl":
            c = ev.carControl
            a = c.actuators
            ap("t_cc", t)
            ap("cc_ang", a.steeringAngleDeg)
            ap("cc_tq", a.torque)
            ap("cc_curv", a.curvature)
            ap("cc_tqcan", a.torqueOutputCan)
            ap("cc_latActive", c.latActive)
            ap("cc_enabled", c.enabled)
            ap("cc_longActive", c.longActive)
            ap("cc_curcurv", c.currentCurvature)
            ap("cc_lblink", c.leftBlinker)
            ap("cc_rblink", c.rightBlinker)
        elif w == "carOutput":
            a = ev.carOutput.actuatorsOutput
            ap("t_co", t)
            ap("co_ang", a.steeringAngleDeg)
            ap("co_tq", a.torque)
            ap("co_tqcan", a.torqueOutputCan)
        elif w == "carState":
            c = ev.carState
            cr = c.cruiseState
            ap("t_cs", t)
            ap("cs_vego", c.vEgo); ap("cs_vegoraw", c.vEgoRaw)
            ap("cs_ang", c.steeringAngleDeg); ap("cs_rate", c.steeringRateDeg)
            ap("cs_tq", c.steeringTorque); ap("cs_tqeps", c.steeringTorqueEps)
            ap("cs_press", c.steeringPressed)
            ap("cs_ftemp", c.steerFaultTemporary); ap("cs_fperm", c.steerFaultPermanent)
            ap("cs_cr_avail", cr.available); ap("cs_cr_en", cr.enabled)
            ap("cs_vcruise", c.vCruise); ap("cs_yawrate", c.yawRate)
            ap("cs_lblink", c.leftBlinker); ap("cs_rblink", c.rightBlinker)
            ap("cs_gaspress", c.gasPressed); ap("cs_brakepress", c.brakePressed)
            ap("cs_aoff", c.steeringAngleOffsetDeg)
            ap("cs_steerdis", c.steeringDisengage); ap("cs_stocklkas", c.stockLkas)
            ap("cs_invlkas", c.invalidLkasSetting)
            ap("cs_canvalid", c.canValid)
        elif w == "selfdriveState":
            s = ev.selfdriveState
            ap("t_sd", t)
            ap("sd_enabled", s.enabled); ap("sd_active", s.active)
            ap("sd_state", s.state.raw); ap("sd_engageable", s.engageable)
            txt = (str(s.alertText1) + " | " + str(s.alertText2)).strip(" |")
            if not L.get("_sd_alert_last") or L["_sd_alert_last"][-1] != txt:
                ap("_sd_alert_last", txt)
                ap("t_sdalert", t); ap("sdalert_text", txt)
        elif w == "starpilotSelfdriveState":
            s = ev.starpilotSelfdriveState
            txt = (str(s.alertText1) + " | " + str(s.alertText2)).strip(" |")
            if not L.get("_spsd_alert_last") or L["_spsd_alert_last"][-1] != txt:
                ap("_spsd_alert_last", txt)
                ap("t_spsdalert", t); ap("spsdalert_text", txt)
        elif w == "starpilotCarState":
            s = ev.starpilotCarState
            ap("t_spcs", t)
            ap("spcs_aol_en", s.alwaysOnLateralEnabled); ap("spcs_aol_allowed", s.alwaysOnLateralAllowed)
            ap("spcs_pauselat", s.pauseLateral)
            if has_angstat is None:
                has_angstat = "accordAngleStatus" in s.schema.fieldnames
                meta["has_accordAngleStatus"] = has_angstat
            if has_angstat:
                ap("spcs_angstat", s.accordAngleStatus)
        elif w == "starpilotPlan":
            s = ev.starpilotPlan
            ap("t_spp", t)
            ap("spp_latcheck", s.lateralCheck); ap("spp_roadcurv", s.roadCurvature)
            tog = str(s.starpilotToggles)       # published ~1 Hz; empty on the other frames
            if tog and tog != sp_tog_last:
                if sp_tog_last is not None:
                    meta["sp_toggles_changes"] += 1
                sp_tog_last = tog
                if meta["sp_toggles"] is None:
                    meta["sp_toggles"] = tog
        elif w == "starpilotLateralState":
            s = ev.starpilotLateralState
            ap("t_spls", t)
            for k in ("active", "frictionThreshold", "frictionScale", "feedforward", "frictionJerk",
                      "frictionJerkDeadzone", "lowSpeedFactor", "unwindDetected", "accordObserverTorque",
                      "accordObserverFrozen"):
                ap("spls_" + k, getattr(s, k))
        elif w == "liveParameters":
            p = ev.liveParameters
            ap("t_lp", t)
            ap("lp_roll", p.roll); ap("lp_sr", p.steerRatio); ap("lp_aoff", p.angleOffsetDeg)
            ap("lp_aoffavg", p.angleOffsetAverageDeg); ap("lp_stiff", p.stiffnessFactor)
            ap("lp_valid", p.valid); ap("lp_sensorvalid", p.sensorValid)
        elif w == "liveDelay":
            p = ev.liveDelay
            ap("t_ld", t)
            ap("ld_lat", p.lateralDelay); ap("ld_est", p.lateralDelayEstimate); ap("ld_status", p.status.raw)
        elif w == "modelV2":
            m = ev.modelV2
            ap("t_md", t)
            ap("md_act_curv", m.action.desiredCurvature)
            orz = list(m.orientationRate.z)[:MD_K]
            vx = list(m.velocity.x)[:MD_K]
            px = list(m.position.x)[:MD_K]
            py = list(m.position.y)[:MD_K]
            if len(orz) < MD_K or len(vx) < MD_K or len(px) < MD_K:
                orz = vx = px = py = [np.nan] * MD_K
                counts["md_short"] = counts.get("md_short", 0) + 1
            elif "md_T" not in L:
                L["md_T"] = [list(m.position.t)[:MD_K]]
            ap("md_yawrate", orz); ap("md_vx", vx); ap("md_px", px); ap("md_py", py)
            ap("md_lcstate", m.meta.laneChangeState.raw); ap("md_lcdir", m.meta.laneChangeDirection.raw)
            ap("md_frameid", m.frameId)
        elif w == "onroadEvents":
            ap("t_evmsg", t)
            n = 0
            for e in ev.onroadEvents:
                ap("t_ev", t); ap("ev_name", str(e.name))
                ap("ev_flags", "".join(c for c, f in (("E", e.enable), ("N", e.noEntry), ("W", e.warning),
                                                      ("U", e.userDisable), ("S", e.softDisable),
                                                      ("I", e.immediateDisable), ("P", e.permanent),
                                                      ("L", e.overrideLateral)) if f))
                n += 1
            ap("evmsg_n", n)
        elif w == "starpilotOnroadEvents":
            ap("t_spevmsg", t)
            n = 0
            for e in ev.starpilotOnroadEvents.events:
                ap("t_spev", t); ap("spev_name", str(e.name))
                n += 1
            ap("spevmsg_n", n)
        elif w == "pandaStates":
            ps = ev.pandaStates
            if len(ps):
                p = ps[0]
                ap("t_ps", t)
                ap("ps_txblocked", p.safetyTxBlocked); ap("ps_ctrl_allowed", p.controlsAllowed)
                ap("ps_safetymodel", p.safetyModel.raw); ap("ps_safetyparam", p.safetyParam)
                ap("ps_altexp", p.alternativeExperience); ap("ps_rxinvalid", p.safetyRxInvalid)
                ap("ps_rxchkinvalid", p.safetyRxChecksInvalid); ap("ps_ign", p.ignitionLine or p.ignitionCan)
                ap("ps_hblost", p.heartbeatLost)
                if "ps_safetymodel_name" not in meta:
                    meta["ps_safetymodel_name"] = {int(p.safetyModel.raw): str(p.safetyModel)}
        elif w == "carParams" and meta["carparams"] is None:
            meta["carparams"] = _carparams_dict(ev.carParams)
        elif w == "initData" and meta["initdata"] is None:
            pd = {}
            allkeys = 0
            for e in ev.initData.params.entries:
                allkeys += 1
                k = str(e.key)
                if any(s in k for s in PARAM_SUBSTR) or k in ("GitCommit", "GitBranch", "Version"):
                    try:
                        pd[k] = bytes(e.value).decode("utf-8", "replace")
                    except Exception:
                        pd[k] = repr(bytes(e.value)[:200])
            # CarParams/LiveParameters-style blobs are binary capnp/json -- keep only short readable ones
            pd = {k: (v if len(v) <= 400 else v[:400] + "...<truncated %d>" % len(v)) for k, v in pd.items()}
            meta["initdata"] = dict(params=pd, n_keys=allkeys)

    # list -> array, ONCE, in the worker
    A = {}
    for k, v in L.items():
        if k.startswith("_"):
            continue
        if k.endswith("_raw"):
            A[k] = np.frombuffer(b"".join(v), np.uint8).reshape(-1, 5) if v else np.zeros((0, 5), np.uint8)
        elif k in ("sdalert_text", "spsdalert_text", "ev_name", "spev_name", "ev_flags"):
            A[k] = np.array(v, dtype=str)
        elif k in ("md_yawrate", "md_vx", "md_px", "md_py", "md_T"):
            A[k] = np.asarray(v, np.float32)
        elif k.startswith("t_"):
            A[k] = np.asarray(v, np.float64)
        else:
            A[k] = np.asarray(v)
    return sn, A, meta


# ======================================================================================================
# 2.  MERGE, DERIVE, VERIFY, WRITE
# ======================================================================================================
def _enum(path):
    try:
        o = load_log()
        for part in path.split("."):
            o = getattr(o, part)
        return {int(v): str(k) for k, v in o.schema.enumerants.items()}
    except Exception as e:
        return {"ERR": str(e)[:80]}


def derive_e4(D, key):
    raw = D.get(key + "_raw")
    if raw is None or not len(raw):
        return
    d = raw.astype(np.int32)
    v = (d[:, 0] << 8) | d[:, 1]
    D[key + "_i16"] = np.where(v >= 32768, v - 65536, v).astype(np.int32)
    D[key + "_req"] = ((d[:, 2] >> 7) & 1).astype(np.int8)
    D[key + "_arm"] = ((d[:, 2] >> 2) & 3).astype(np.int8)
    D[key + "_b2"] = raw[:, 2].copy()


def main():
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--procs", type=int, default=16)
    ap_.add_argument("--route", default=PREFIX)
    ap_.add_argument("--commit", default="auto")
    ap_.add_argument("--out", default=None)
    ap_.add_argument("--print-out", action="store_true", help="print the output path this run would write, and exit")
    a = ap_.parse_args()
    T0 = time.perf_counter()
    prefix = a.route
    out_path = a.out or default_out(prefix)
    if a.print_out:
        print(out_path)
        return
    wire_path = WIRE if prefix == PREFIX else os.path.join(CACHE, route_tag(prefix) + ".npz")
    segs = sorted(glob.glob(os.path.join(RLOGS, prefix + "--*--rlog.zst")),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    if not segs:
        raise SystemExit("no segments for " + prefix)
    commit, commit_src = a.commit, "--commit"
    if commit == "auto":
        # a byte search of segment 0 (no capnp in THIS process: a schema loaded here before the decode Pool spawns
        # kills the run -- measured 2026-10-02, exit 127, no traceback), VERIFIED after the decode against the
        # initData GitCommit the pinned schema reads (a mismatch stops the run)
        commit = route_commit_fast(segs[0])
        commit_src = "initData GitCommit of %s" % os.path.basename(segs[0])
        if not commit:
            raise SystemExit("no GitCommit in the route's initData: pass --commit")
    stamp, schema_dir, full_sha = build_schema(commit)
    print("schema: %s  (%s; commit %s from %s)" % (schema_dir, stamp, full_sha, commit_src))
    print("segments: %d -> %d procs" % (len(segs), min(a.procs, len(segs))), flush=True)
    # biggest segments first so the tail is short
    order = sorted(segs, key=lambda p: -os.path.getsize(p))
    with Pool(min(a.procs, len(segs))) as pool:
        res = pool.map(work, [(p, schema_dir) for p in order], chunksize=1)
    T_dec = time.perf_counter() - T0
    res.sort(key=lambda r: r[0])
    seg_ids = [r[0] for r in res]
    metas = [r[2] for r in res]

    keys = []
    for _, A, _m in res:
        for k in A:
            if k not in keys:
                keys.append(k)
    D = {}
    for k in keys:
        if k == "md_T":
            D[k] = next(A[k][0] for _, A, _m in res if k in A)
            continue
        parts = [A[k] for _, A, _m in res if k in A]
        D[k] = np.concatenate(parts, axis=0)
    for key in [k[:-4] for k in list(D) if k.endswith("_raw")]:
        derive_e4(D, key)

    # monotonic check per time key
    nonmono = {k: int(np.sum(np.diff(v) < 0)) for k, v in D.items() if k.startswith("t_") and len(v) > 1}

    # ---- carParams / initData / toggles: first segment that has them; record whether later ones differ
    cp = next((m["carparams"] for m in metas if m["carparams"]), None)
    cp_diff = sorted({m["seg"] for m in metas if m["carparams"] and m["carparams"] != cp})
    ini = next((m["initdata"] for m in metas if m["initdata"]), None)
    gc = ((ini or {}).get("params") or {}).get("GitCommit", "").strip()
    if commit_src.startswith("initData") and gc != full_sha:
        raise SystemExit("the schema pin %s != the decoded initData GitCommit %r: re-run with --commit" % (full_sha, gc))
    ini_diff = sorted({m["seg"] for m in metas if m["initdata"] and m["initdata"]["params"] != ini["params"]})
    tog = next((m["sp_toggles"] for m in metas if m["sp_toggles"]), None)
    tog_changes = sum(m["sp_toggles_changes"] for m in metas)
    tog_diff = sorted({m["seg"] for m in metas if m["sp_toggles"] and m["sp_toggles"] != tog})
    psname = {}
    for m in metas:
        psname.update(m.get("ps_safetymodel_name", {}))
    counts = {}
    for m in metas:
        for k, v in m["counts"].items():
            counts[k] = counts.get(k, 0) + v

    # ---- ALIGNMENT against the wire cache (skipped, and said so, when the route has no wire cache yet)
    if os.path.exists(wire_path):
        W = np.load(wire_path)
    else:
        print("no wire cache %s: alignment checks skipped" % wire_path)
        W = dict(tcs=D["t_cs"][:0], cs_ang=D["cs_ang"][:0], t14=np.zeros(0), ang=np.zeros(0))
    tcs_w, ang_w = W["tcs"], W["cs_ang"]
    idx = np.searchsorted(D["t_cs"], tcs_w)
    idx = np.clip(idx, 0, len(D["t_cs"]) - 1)
    dt = D["t_cs"][idx] - tcs_w
    exact = np.abs(dt) < 1e-9
    res_ang = (D["cs_ang"][idx] - ang_w)[exact]
    align = dict(n_wire_cs=int(len(tcs_w)), n_fork_cs=int(len(D["t_cs"])), n_exact_time_match=int(exact.sum()),
                 max_abs_dt_s=float(np.max(np.abs(dt))),
                 max_abs_ang_residual_deg=float(np.max(np.abs(res_ang))) if len(res_ang) else float("nan"))
    # second, independent check: carState angle vs the 0x14A wire angle (different CAN source), lag-fit
    t14, a14 = W["t14"], W["ang"]
    m = ((D["t_cs"] > t14[0]) & (D["t_cs"] < t14[-1])) if len(t14) else np.zeros(len(D["t_cs"]), bool)
    best = (float("nan"), float("nan"), float("nan"))
    for lag in np.arange(-0.05, 0.0501, 0.005) if m.any() else []:
        r = D["cs_ang"][m] - np.interp(D["t_cs"][m] + lag, t14, a14)
        s = float(np.median(np.abs(r)))
        if not np.isfinite(best[1]) or s < best[1]:
            best = (float(lag), s, float(np.percentile(np.abs(r), 99)))
    align["cs_vs_0x14A_best_lag_s"] = round(best[0], 4)
    align["cs_vs_0x14A_median_abs_deg"] = best[1]
    align["cs_vs_0x14A_p99_abs_deg"] = best[2]
    # third: this cache's src-129 0xE4 echo must BE the wire cache's te4/cmd/req, row for row
    if "t_e4tx1" in D and "te4" in W:
        te4, cmd, req = W["te4"], W["cmd"], W["req"]
        same_n = len(te4) == len(D["t_e4tx1"])
        align["e4tx1_equals_wire_te4_cmd_req"] = bool(
            same_n and np.array_equal(te4, D["t_e4tx1"]) and np.array_equal(cmd.astype(np.int64), D["e4tx1_i16"])
            and np.array_equal(req.astype(np.int64), D["e4tx1_req"].astype(np.int64)))
    # fourth: each sendcan 0xE4 equals the carOutput.actuatorsOutput.torqueOutputCan published NEXT (card
    # sends the CAN first, then carOutput, in the same loop)
    if "t_e4send" in D and "t_co" in D:
        j = np.clip(np.searchsorted(D["t_co"], D["t_e4send"]), 0, len(D["t_co"]) - 1)
        align["e4send_eq_next_co_tqcan_frac"] = float(np.mean(D["e4send_i16"] == D["co_tqcan"][j]))
        align["e4send_to_next_co_median_dt_s"] = float(np.median(D["t_co"][j] - D["t_e4send"]))

    wall = time.perf_counter() - T0
    has_as = sorted({mm["has_accordAngleStatus"] for mm in metas if mm.get("has_accordAngleStatus") is not None})
    D["meta_json"] = np.array(json.dumps(dict(
        route=prefix, segments=seg_ids, fork_commit=full_sha[:9], fork_commit_full=full_sha,
        fork_commit_source=commit_src, schema=stamp, schema_dir=schema_dir,
        has_accordAngleStatus=(has_as[0] if len(has_as) == 1 else has_as), wire_cache=wire_path,
        decode_wall_s=round(T_dec, 2), wall_time_s=round(wall, 2), procs=min(a.procs, len(segs)),
        failed_segments=[dict(seg=mm["seg"], err=mm["failed"]) for mm in metas if mm["failed"]],
        event_counts=counts, nonmonotonic_steps=nonmono, alignment=align,
        carparams_differs_in_segs=cp_diff, initdata_differs_in_segs=ini_diff,
        sp_toggles_changes=tog_changes, sp_toggles_differs_in_segs=tog_diff,
        ps_safetymodel_names=psname,
        sd_state_enum=_enum("SelfdriveState.OpenpilotState"),
        md_lcstate_enum=_enum("LaneChangeState"),
        ld_status_enum=_enum("LiveDelayData.Status"),
    ), default=str))
    D["carparams_json"] = np.array(json.dumps(cp, default=str))
    D["initdata_params_json"] = np.array(json.dumps(ini, default=str))
    D["sp_toggles_json"] = np.array(tog or "")
    D["meta_wall_time_s"] = np.array(wall)
    np.savez(out_path, **D)
    wall2 = time.perf_counter() - T0
    print("decode %.1f s   total (incl. merge+verify+save) %.1f s" % (T_dec, wall2))
    print("wrote %s  (%.1f MB, %d keys)" % (out_path, os.path.getsize(out_path) / 1e6, len(D)))
    print("starpilotCarState.accordAngleStatus in the pinned schema: %s" % (has_as,))
    print("alignment:", json.dumps(align, indent=1))
    print("counts:", {k: counts[k] for k in sorted(counts) if k in (
        "controlsState", "carControl", "carOutput", "carState", "selfdriveState", "liveParameters",
        "liveDelay", "modelV2", "onroadEvents", "pandaStates", "starpilotLateralState", "carParams",
        "initData", "starpilotOnroadEvents", "sendcan", "can")})
    print("non-monotonic time steps:", {k: v for k, v in nonmono.items() if v})
    print("carParams differs in segs:", cp_diff, " initData differs in segs:", ini_diff,
          " toggles changes:", tog_changes)
    for k in sorted(D):
        v = D[k]
        print("  %-22s %-10s %s" % (k, v.dtype, v.shape))


if __name__ == "__main__":
    main()
