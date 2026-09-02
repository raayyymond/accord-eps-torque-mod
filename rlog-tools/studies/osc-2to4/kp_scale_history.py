"""
kp_scale_history.py -- did the StarPilot `HondaLateralPidKpScale` / `KiScale` UI values ever act
on the TORQUE lateral path?  Settle it EMPIRICALLY from the 60 rlog routes.

WHY: the operator sets the Honda Kp/Ki scale in the UI (1.0 for the 2x EPS mod, 0.5 for 4x, 0.33
for 6x) and is confident from driving that it acts.  Source reading says the only consumer is
`latcontrol_pid.py`, gated on `lateralTuning.which() == "pid"`, so with `force_torque_controller`
on it would be inert and the torque controller's kp would be `SteerKP` (default 0.6) regardless.
Two readers of the source vs one driver of the car -> ask the wire.

WHAT IT MEASURES (per route, every segment):
  * `controlsState.lateralControlState.torqueState` on active frames -> p, i, f, error, output.
    In StarPilot `pid.p = k_p * error` and `pid_log.error` is the SAME error passed to the PID
    (`error_with_lsf`), so  kp_eff = p / error  is the live proportional gain EXACTLY, per frame.
    The integrator is `i[n] = i[n-1] + k_i * dt * error[n]` (clipped), so on frames where it moved
    ki_eff = (i[n] - i[n-1]) / (dt * error[n]).
  * `starpilotPlan.starpilotToggles` -- StarPilot serialises its whole toggle namespace as JSON
    into the rlog.  We tabulate `steerKp`, `honda_lateral_pid_kp_scale`, `honda_lateral_pid_ki_scale`,
    `force_torque_controller`, `nnff`.  NOTE: `honda_lateral_pid_*_scale` in that namespace is the
    value AFTER `get_value(condition=honda_pid_lateral)` -- when the condition is false it is the
    default 1.0 regardless of what the UI param holds.  So a logged 1.0 does not tell us the UI
    value; kp_eff does.
  * `initData` (wall clock, gitCommit, gitBranch), `carParams` (lateralTuning.which, torque.*,
    EPS fw string), `liveTorqueParameters` (useParams, latAccelFactorFiltered).

The rlogs are decoded with StarPilot's OWN cereal schema (copied into the session scratchpad with
the car.capnp symlink resolved), because the kit's generic cereal does not carry `starpilotPlan`.

Usage:  python rlog-tools/studies/osc-2to4/kp_scale_history.py [--workers 8] [--json OUT] [--routes 2e,95]
Python = the `bin_decompile` conda env, invoked as `python`.
"""
# --- PATH BOOTSTRAP -------------------------------------------------------------------------
import os, sys
_here = os.path.dirname(os.path.abspath(__file__))
_root = _here
while _root and not os.path.exists(os.path.join(_root, ".pkgroot")):
    _parent = os.path.dirname(_root)
    if _parent == _root:
        _root = None
        break
    _root = _parent
if _root:
    for _sub in ("", "lib", "decode", "score", "probe"):
        _p = os.path.join(_root, _sub)
        if _p not in sys.path:
            sys.path.insert(0, _p)
# ------------------------------------------------------------------------------------------------
import glob, json, argparse, datetime, collections, shutil
import numpy as np

KIT = os.path.normpath(os.path.join(_here, "..", "..", ".."))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
STARPILOT = os.environ.get("STARPILOT_ROOT", "C:/Users/dudei/Desktop/Projects/openpilots/StarPilot")
SCHEMA_DIR = os.path.join(KIT, "rlog-tools", "_scratch", "spcereal")
DT = 0.01  # controlsd rate, 100 Hz


def ensure_schema():
    """Copy StarPilot's cereal into a loadable dir: on Windows `cereal/car.capnp` is a symlink text
    file pointing at opendbc, so capnp cannot import it in place."""
    os.makedirs(os.path.join(SCHEMA_DIR, "include"), exist_ok=True)
    src = os.path.join(STARPILOT, "cereal")
    for f in ("log.capnp", "custom.capnp", "legacy.capnp"):
        shutil.copy(os.path.join(src, f), SCHEMA_DIR)
    shutil.copy(os.path.join(STARPILOT, "opendbc_repo", "opendbc", "car", "car.capnp"), SCHEMA_DIR)
    for f in glob.glob(os.path.join(src, "include", "*")):
        shutil.copy(f, os.path.join(SCHEMA_DIR, "include"))


_LOG = None


def schema():
    global _LOG
    if _LOG is None:
        import capnp
        capnp.remove_import_hook()
        _LOG = capnp.load(os.path.join(SCHEMA_DIR, "log.capnp"), imports=[SCHEMA_DIR])
    return _LOG


TOGGLE_KEYS = ("steerKp", "honda_lateral_pid_kp_scale", "honda_lateral_pid_ki_scale",
               "force_torque_controller", "nnff", "nnff_lite", "steerActuatorDelay",
               "use_custom_steerActuatorDelay", "steerRatio")


def read_segment(path, acc):
    import zstandard
    log = schema()
    data = zstandard.ZstdDecompressor().stream_reader(open(path, "rb")).read()
    vego = 0.0
    for evt in log.Event.read_multiple_bytes(data):
        try:
            w = evt.which()
        except Exception:
            acc["undecodable"] += 1
            continue
        if w == "carState":
            vego = evt.carState.vEgo
        elif w == "controlsState":
            lcs = evt.controlsState.lateralControlState
            lw = lcs.which()
            acc["which"][lw] += 1
            if lw == "torqueState":
                t = lcs.torqueState
                if t.active:
                    acc["frames"].append((evt.logMonoTime * 1e-9, t.p, t.i, t.f, t.error, t.output,
                                          float(t.saturated), vego, t.d, t.version))
            elif lw == "pidState":
                t = lcs.pidState
                if t.active:
                    acc["pid_frames"].append((evt.logMonoTime * 1e-9, t.p, t.i, t.f, t.error, t.output,
                                              float(t.saturated), vego))
        elif w == "starpilotPlan":
            s = evt.starpilotPlan.starpilotToggles
            if s:
                try:
                    tog = json.loads(s)
                except Exception:
                    continue
                key = tuple((k, json.dumps(tog.get(k))) for k in TOGGLE_KEYS)
                acc["toggles"][key] += 1
        elif w == "liveTorqueParameters":
            q = evt.liveTorqueParameters
            acc["ltp"].append((float(q.useParams), q.latAccelFactorFiltered, q.frictionCoefficientFiltered,
                               q.latAccelFactorRaw, float(q.liveValid)))
        elif w == "initData":
            d = evt.initData
            acc["init"].append({"wall": datetime.datetime.fromtimestamp(d.wallTimeNanos * 1e-9).strftime("%Y-%m-%d %H:%M"),
                                "gitCommit": d.gitCommit[:9], "gitBranch": d.gitBranch, "gitRemote": d.gitRemote,
                                "version": d.version, "dirty": bool(d.dirty)})
        elif w == "carParams":
            c = evt.carParams
            lt = c.lateralTuning
            entry = {"fingerprint": c.carFingerprint, "which": lt.which(), "steerActuatorDelay": c.steerActuatorDelay}
            if lt.which() == "torque":
                tq = lt.torque
                entry.update({"latAccelFactor": tq.latAccelFactor, "friction": tq.friction,
                              "kpDEPRECATED": getattr(tq, "kpDEPRECATED", None), "kiDEPRECATED": getattr(tq, "kiDEPRECATED", None),
                              "kfDEPRECATED": getattr(tq, "kfDEPRECATED", None), "latAccelOffset": tq.latAccelOffset})
            elif lt.which() == "pid":
                entry.update({"kpV": list(lt.pid.kpV), "kiV": list(lt.pid.kiV), "kf": lt.pid.kf})
            eps = [bytes(f.fwVersion).decode("latin1") for f in c.carFw if str(f.ecu) == "eps"]
            entry["epsFw"] = eps
            acc["carParams"].append(entry)


def new_acc():
    return {"frames": [], "pid_frames": [], "toggles": collections.Counter(), "which": collections.Counter(),
            "ltp": [], "init": [], "carParams": [], "undecodable": 0}


def pct(x, q):
    return [round(float(v), 4) for v in np.percentile(x, q)] if len(x) else None


def analyse(prefix, segs):
    acc = new_acc()
    for p in segs:
        try:
            read_segment(p, acc)
        except Exception as e:
            acc.setdefault("errors", []).append(f"{os.path.basename(p)}: {e!r}")
    out = {"route": prefix, "nseg": len(segs), "which": dict(acc["which"]), "undecodable": acc["undecodable"],
           "errors": acc.get("errors", [])}
    out["init"] = acc["init"][0] if acc["init"] else None
    out["carParams"] = acc["carParams"][0] if acc["carParams"] else None
    out["toggles"] = [(dict((k, json.loads(v)) for k, v in key), n) for key, n in acc["toggles"].most_common()]
    if acc["ltp"]:
        a = np.array(acc["ltp"], float)
        out["ltp"] = {"n": len(a), "useParams_frac": round(float(a[:, 0].mean()), 3),
                      "LAF_filt_p50": round(float(np.median(a[:, 1])), 3), "LAF_raw_p50": round(float(np.median(a[:, 3])), 3),
                      "friction_filt_p50": round(float(np.median(a[:, 2])), 4), "liveValid_frac": round(float(a[:, 4].mean()), 3)}
    else:
        out["ltp"] = None
    fr = np.array(acc["frames"], float) if acc["frames"] else np.zeros((0, 10))
    out["active_frames"] = int(len(fr))
    out["torque_version"] = sorted(set(int(v) for v in fr[:, 9])) if len(fr) else []
    if len(fr):
        t, p, i, f, err, outp, sat, v = (fr[:, k] for k in range(8))
        m = np.abs(err) > 0.05
        kp = p[m] / err[m]
        out["kp_eff"] = {"n": int(m.sum()), "p5_p50_p95": pct(kp, [5, 50, 95])}
        # speed-split: the stock KP_INTERP table rises steeply below ~10 m/s; the `steerKp` override
        # ([[0],[x]]) makes kp flat at every speed.  Flatness across speed bins is itself diagnostic.
        for lo, hi, name in ((0, 5, "kp_v<5"), (5, 10, "kp_5-10"), (10, 20, "kp_10-20"), (20, 99, "kp_v>20")):
            mm = m & (v >= lo) & (v < hi)
            out[name] = {"n": int(mm.sum()), "p50": round(float(np.median(p[mm] / err[mm])), 4)} if mm.sum() > 20 else None
        # ki from the integrator step on consecutive frames (dt ~ 0.01 s, same segment)
        di = np.diff(i)
        dtv = np.diff(t)
        e1 = err[1:]
        ok = (np.abs(e1) > 0.05) & (np.abs(di) > 1e-7) & (dtv > 0.005) & (dtv < 0.02) & (sat[1:] == 0)
        ki = di[ok] / (DT * e1[ok])
        out["ki_eff"] = {"n": int(ok.sum()), "p5_p50_p95": pct(ki, [5, 50, 95])}
        # least-squares fit as a second estimate (robust to per-frame noise)
        if ok.sum() > 50:
            x = DT * e1[ok]
            out["ki_lsq"] = round(float(np.dot(x, di[ok]) / np.dot(x, x)), 4)
        out["f_over_output_p50"] = round(float(np.median(np.abs(f[np.abs(outp) > 0.05]) / np.abs(outp[np.abs(outp) > 0.05]))), 3) if (np.abs(outp) > 0.05).sum() else None
        out["|p|_p50"] = round(float(np.median(np.abs(p))), 4)
        out["|i|_p50"] = round(float(np.median(np.abs(i))), 4)
        out["|f|_p50"] = round(float(np.median(np.abs(f))), 4)
        out["|err|_p50"] = round(float(np.median(np.abs(err))), 4)
        out["sat_frac"] = round(float(sat.mean()), 3)
    pf = np.array(acc["pid_frames"], float) if acc["pid_frames"] else None
    out["pid_active_frames"] = int(len(pf)) if pf is not None else 0
    if pf is not None and len(pf):
        m = np.abs(pf[:, 4]) > 0.05
        out["pid_kp_eff_p50"] = round(float(np.median(pf[m, 1] / pf[m, 4])), 4) if m.sum() else None
    return out


def _worker(args):
    return analyse(*args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--json", default=os.path.join(_here, "_kp_scale_history.json"))
    ap.add_argument("--routes", default="", help="comma list of route suffixes (e.g. 2e,95) to restrict")
    ap.add_argument("--max-seg", type=int, default=0, help="cap segments per route (0 = all)")
    a = ap.parse_args()
    ensure_schema()
    files = glob.glob(os.path.join(RLOGS, "*--rlog.zst"))
    routes = collections.defaultdict(list)
    for f in files:
        routes["--".join(os.path.basename(f).split("--")[:2])].append(f)
    want = [r.strip().lower() for r in a.routes.split(",") if r.strip()]
    jobs = []
    for pre in sorted(routes):
        rid = pre.split("--")[0].split("_")[1].lstrip("0") or "0"
        if want and rid not in want:
            continue
        segs = sorted(routes[pre], key=lambda p: int(os.path.basename(p).split("--")[2]))
        if a.max_seg:
            segs = segs[:a.max_seg]
        jobs.append((pre, segs))
    print(f"{len(jobs)} routes, {sum(len(s) for _, s in jobs)} segments, {a.workers} workers", flush=True)
    if a.workers > 1:
        import multiprocessing as mp
        with mp.Pool(a.workers) as pool:
            res = []
            for r in pool.imap_unordered(_worker, jobs):
                res.append(r)
                print(f"  done {r['route'][-14:]} nseg={r['nseg']} active={r['active_frames']} kp={r.get('kp_eff')}", flush=True)
    else:
        res = [analyse(*j) for j in jobs]
    res.sort(key=lambda r: (r["init"] or {}).get("wall", ""))
    json.dump(res, open(a.json, "w"), indent=1, default=str)
    print_table(res)


def print_table(res):
    print()
    print("route  date              gitCommit  ver         ctrl        tog.steerKp  hKp  hKi  FTC  kp_eff p5/p50/p95            kp<5  kp5-10 kp10-20 kp>20   ki_p50  ki_lsq  LAF_use LAF_filt  nAct   epsFw")
    for r in res:
        init = r["init"] or {}
        cp = r["carParams"] or {}
        tog = r["toggles"][0][0] if r["toggles"] else {}
        sk = tog.get("steerKp")
        sk = sk[1][0] if isinstance(sk, list) and len(sk) == 2 and sk[1] else sk
        kp = r.get("kp_eff") or {}
        ki = r.get("ki_eff") or {}
        ltp = r.get("ltp") or {}
        rid = r["route"].split("--")[0].split("_")[1]
        which = ",".join(f"{k}:{v}" for k, v in sorted(r["which"].items(), key=lambda kv: -kv[1]))[:11]
        def g(name):
            x = r.get(name)
            return f"{x['p50']:.3f}" if x else "  -  "
        print(f"{rid[-4:]:>4}  {init.get('wall','?'):16} {init.get('gitCommit','?'):9}  {str(init.get('version','?'))[:10]:10}  {which:11} "
              f"{str(sk):>11}  {tog.get('honda_lateral_pid_kp_scale','?'):>4} {tog.get('honda_lateral_pid_ki_scale','?'):>4} "
              f"{str(tog.get('force_torque_controller','?'))[0]:>3}  {str(kp.get('p5_p50_p95')):22} "
              f"{g('kp_v<5')} {g('kp_5-10')} {g('kp_10-20')} {g('kp_v>20')}  "
              f"{str((ki.get('p5_p50_p95') or [None,None])[1]):7} {str(r.get('ki_lsq')):7} "
              f"{str(ltp.get('useParams_frac')):7} {str(ltp.get('LAF_filt_p50')):8} {r['active_frames']:6} {str(cp.get('epsFw'))[:24]}")
        if len(r["toggles"]) > 1:
            for tg, n in r["toggles"][1:]:
                print(f"       ^ also toggles x{n}: steerKp={tg.get('steerKp')} hKp={tg.get('honda_lateral_pid_kp_scale')} hKi={tg.get('honda_lateral_pid_ki_scale')} FTC={tg.get('force_torque_controller')}")
        if r["errors"]:
            print("       errors:", r["errors"][:3])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--table":
        print_table(json.load(open(sys.argv[2] if len(sys.argv) > 2 else os.path.join(_here, "_kp_scale_history.json"))))
    else:
        main()
