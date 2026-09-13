# -*- coding: utf-8 -*-
"""sr_newroute.py -- validate the shipped variable-ratio map (57410c3b4) on ONE new route.

Two independent views:
  A. KINEMATIC (SR-free, same estimator as sr_final):  radians(ang_raw) = sR*u + off,
     u = denom / cfac, denom = -yaw_cal/v - roll_comp.  Single route -> one free intercept.
     Also a joint fixed-effects fit of corpus + this route.
  B. CLOSED LOOP (what the car actually did with the served map at the logged level):
     true curvature  k_true = -denom-ish = yaw_cal/v + roll term   vs   controlsState.curvature
     (the controller's own reading through the served sR) and vs desiredCurvature.
     k_true / k_ctrl  == served_sR / true_sR  per |sa| bin.

Run:  python sr_newroute.py <route id, e.g. 75604b0a432fdc89_000000a7--xxxxxxxxxx> [level]
"""
import glob, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "rlog-tools"))
from sr_extract import read_segment, out_name  # noqa: E402
from sr_pool import load_route, reduce_route, hold_idx  # noqa: E402
from sr_lib2 import fit3, episodes, stationary, FS  # noqa: E402
from sr_final import fe_fit  # noqa: E402
from sr_episodes import P2  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RLOGS = os.path.join(ROOT, "analysis-2020accord", "rlogs")
SCR = os.path.join(HERE, "_scratch")
BP = [0.0, 23.0, 31.0, 61.0, 76.0, 95.0, 116.0, 151.0, 178.0, 227.0, 236.0, 303.0, 380.0]
V = [16.89, 16.89, 16.89, 16.26, 15.97, 15.46, 15.02, 14.67, 14.45, 14.09, 14.25, 12.98, 12.31]
NOM = 16.89
CORPUS = {(20, 28): 16.89, (28, 36): 16.91, (36, 45): 16.73, (45, 55): 16.45, (55, 70): 16.26,
          (70, 85): 15.97, (85, 105): 15.46, (105, 130): 15.02, (130, 165): 14.67,
          (165, 210): 14.45, (210, 270): 14.09}
FINE = [(2, 5), (5, 10), (10, 20), (20, 28), (28, 36), (36, 45), (45, 55), (55, 70), (70, 85),
        (85, 105), (105, 130), (130, 165), (165, 210), (210, 270), (270, 330), (330, 400)]
L = []


def pr(s=""):
    print(s, flush=True); L.append(s)


def served(a, level):
    return np.interp(a, BP, V) * (level / NOM)


def closed_loop_segment(path):
    """controlsState curvature/desired + carControl latActive + initData SteerRatio params."""
    import zstandard
    from cereal import log as clog
    data = zstandard.ZstdDecompressor().stream_reader(open(path, "rb")).read()
    out = {"t": [], "k": [], "kd": []}
    params = {}
    for evt in clog.Event.read_multiple_bytes(data):
        try:
            w = evt.which()
        except Exception:
            continue
        if w == "controlsState":
            c = evt.controlsState
            out["t"].append(evt.logMonoTime * 1e-9); out["k"].append(c.curvature)
            out["kd"].append(c.desiredCurvature)
        elif w == "initData" and not params:
            try:
                for e in evt.initData.params.entries:
                    if e.key in ("SteerRatio", "SteerRatioStock", "AccordVariableSteerRatio", "SteerLatAccel",
                                 "SteerKP", "SteerKI", "AccordRatePlantFF", "SteerDelay"):
                        params[e.key] = bytes(e.value).decode(errors="replace")
            except Exception as exc:
                params["_err"] = str(exc)
    return {k: np.asarray(v, np.float64) for k, v in out.items()}, params


def main():
    rid = sys.argv[1]
    level = float(sys.argv[2]) if len(sys.argv) > 2 else 16.84
    segs = sorted(glob.glob(os.path.join(RLOGS, rid + "--*--rlog.zst")),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    pr("route %s  segments %d  level %.2f (scale %.4f)" % (rid, len(segs), level, level / NOM))
    # --- extraction (cached into the corpus segs dir so sr_pool picks it up later) ---
    npz = []
    cl_t, cl_k, cl_kd = [], [], []
    params = {}
    for p in segs:
        o = out_name(p)
        if not os.path.exists(o):
            D = read_segment(p)
            np.savez_compressed(o, **D)
        npz.append(o)
        cl, pa = closed_loop_segment(p)
        cl_t.append(cl["t"]); cl_k.append(cl["k"]); cl_kd.append(cl["kd"])
        params = params or pa
    pr("logged params: %s" % json.dumps(params))
    D, cp = load_route(rid, npz)
    # smuggle the absolute carState time through the (unused here) driver-torque column so the kept
    # rows can be aligned to controlsState after reduce_route's validity mask
    cs_t0 = float(D["cs_t"].min())
    drv_orig = D["cs_drv"].copy()
    D["cs_drv"] = (D["cs_t"] - cs_t0).astype(np.float32)
    R = reduce_route({k: val.copy() for k, val in D.items()}, cp, np.int32(0))
    D["cs_drv"] = drv_orig
    R2 = reduce_route(D, cp, np.int32(0))
    t_abs = R["drv"].astype(np.float64) + cs_t0
    R["drv"] = R2["drv"]
    R.pop("_sf"); R.pop("_wb")
    sa = R["sa_deg"].astype(np.float64); asa = np.abs(sa)
    ang = np.radians(R["ang_deg"].astype(np.float64))
    cfac = R["cfac"].astype(np.float64); denom = R["denom"].astype(np.float64)
    v = R["v"].astype(np.float64); rate = R["rate"].astype(np.float64)
    eng = R["eng"] > 0.5; calok = R["calok"] > 0.5; t = R["t"]
    u = denom / cfac
    base = calok & (v > 4.0) & (np.abs(rate) < 20.0) & np.isfinite(u) & np.isfinite(ang)
    pr("valid %.0f s, gated %.0f s, engaged-in-gate %.0f%%, calibrated %.0f%%"
       % (len(sa) / FS, base.sum() / FS, 100 * eng[base].mean() if base.any() else 0, 100 * calok.mean()))

    # ================= A. kinematic, this route alone =================
    pr("")
    pr("A. KINEMATIC sR (SR-free), this route, one free intercept")
    pr("   |sa|      n(s)   TLS    OLSy   OLSu  sprd | n_ep  long  | leadlag            | corpus  served@lvl  served-meas")
    rows = []
    for lo, hi in FINE:
        ok = base & (asa >= lo) & (asa < hi)
        if ok.sum() < 150:
            pr("   %-8s %5.0f   -- too few" % ("%d-%d" % (lo, hi), ok.sum() / FS)); continue
        r = fit3(u[ok], ang[ok], intercept=True)
        if r is None:
            continue
        e, _ = episodes(t, np.where(base, asa, np.nan), v, rate, lo, hi)
        el = [t[b] - t[a] for a, b in e]
        vals = []
        for k in range(0, 26, 3):     # one-sided lag sweep 0..250 ms (yaw lags angle)
            us = np.full_like(u, np.nan); us[:len(u) - k] = u[k:]
            dt = np.full_like(t, np.inf); dt[:len(t) - k] = t[k:] - t[:len(t) - k]
            us[np.abs(dt - k / FS) > 0.02] = np.nan
            mm = ok & np.isfinite(us)
            rr = fit3(us[mm], ang[mm]) if mm.sum() >= 150 else None
            vals.append(np.nan if rr is None else rr["tls"])
        vd, rng_, at = stationary(np.arange(0, 26, 3) * 10.0, vals)
        mid = 0.5 * (lo + hi)
        corp = CORPUS.get((lo, hi))
        srv = float(np.mean(served(asa[ok], level)))
        pr("   %-8s %5.0f %6.2f %6.2f %6.2f %5.2f | %4d %5.2f | %-18s d=%.2f | %s  %6.2f     %+.2f"
           % ("%d-%d" % (lo, hi), ok.sum() / FS, r["tls"], r["ols_y"], r["ols_u"], r["spread"],
              len(el), max(el) if el else 0, vd.split(" (")[0][:18], rng_,
              ("%6.2f" % corp) if corp else "  -- ", srv, srv - r["tls"]))
        rows.append(dict(lo=lo, hi=hi, n_s=ok.sum() / FS, tls=r["tls"], spread=r["spread"], off_deg=np.degrees(r["off"]),
                         ll=vd, ll_range=rng_, served=srv, corpus=corp, n_ep=len(el), longest=max(el) if el else 0))
    offs = [x["off_deg"] for x in rows if x["lo"] >= 20]
    pr("   fitted per-bin offsets (deg, >=20): %s   paramsd angleOffsetDeg median %.2f"
       % (" ".join("%.2f" % o for o in offs), float(np.median(R["aoff"]))))

    # ================= A2. wind-in / wind-out split on this route =================
    pr("")
    pr("A2. wind-in vs wind-out (sign(sa)*rate > 0 = winding in)")
    win = np.sign(sa) * rate > 0
    for lo, hi in [(20, 45), (45, 90), (90, 130), (130, 165), (165, 270), (270, 400)]:
        o = base & (asa >= lo) & (asa < hi)
        a = fit3(u[o & win], ang[o & win]); b = fit3(u[o & ~win], ang[o & ~win]); c = fit3(u[o], ang[o])
        f = lambda x: "%6.2f" % x["tls"] if x else "   -- "
        mp = ("%6.2f" % (0.5 * (a["tls"] + b["tls"]))) if a and b else "   -- "
        pr("   %-8s all %s  in %s  out %s  mid %s   (%.0f s)" % ("%d-%d" % (lo, hi), f(c), f(a), f(b), mp, o.sum() / FS))

    # ================= B. closed loop =================
    pr("")
    ct = np.concatenate(cl_t); ck = np.concatenate(cl_k); ckd = np.concatenate(cl_kd)
    o = np.argsort(ct); ct, ck, ckd = ct[o], ck[o], ckd[o]
    ci = hold_idx(ct, t_abs, 0.05)
    okc = ci >= 0
    cj = np.where(okc, ci, 0)
    k_ctrl = np.where(okc, ck[cj], np.nan)
    k_des = np.where(okc, ckd[cj], np.nan)
    # B1: which served ratio did the controller actually use?  |controlsState.curvature| at |sa|>30 deg is
    # dominated by cfac*sa/sR_served (roll comp is ~1e-4), so sR_served ~= cfac*|sa|/|k_ctrl|.
    pr("B1. SERVED-RATIO CHECK from controlsState.curvature (is the log flying the map at this level?)")
    for lo, hi in [(30, 60), (60, 100), (100, 165), (165, 270)]:
        m = okc & calok & (v > 4) & (asa >= lo) & (asa < hi) & (np.abs(k_ctrl) > 1e-4)
        if m.sum() < 50:
            pr("   %-8s too few" % ("%d-%d" % (lo, hi))); continue
        srv_log = np.median(cfac[m] * np.radians(asa[m]) / np.abs(k_ctrl[m]))
        shape = np.median(np.interp(asa[m], BP, V))
        pr("   %-8s served(log) %6.2f   map shape %6.2f   => level %6.2f   (%.0f s)"
           % ("%d-%d" % (lo, hi), srv_log, shape, NOM * srv_log / shape, m.sum() / FS))

    # B2: delivery, EXCLUDING driver override.  steeringPressed OR |steeringTorque| >= DRV_MAX, dilated by
    # GUARD_S either side (the wheel is still settling after the hand comes off), engaged only.
    DRV_MAX, GUARD_S = 600.0, 1.5   # a6: not-pressed |drv| p95 557, Honda press threshold ~1200
    pr("")
    pr("B2. CLOSED-LOOP DELIVERY, engaged and hands-off (no press, |drv|<%.0f raw, +-%.1f s guard)" % (DRV_MAX, GUARD_S))
    touch = (R["pressed"] > 0.5) | (np.abs(R["drv"]) >= DRV_MAX)
    tt = t_abs[touch]
    if len(tt):
        k = np.searchsorted(tt, t_abs)
        dn = np.abs(t_abs - tt[np.clip(k - 1, 0, len(tt) - 1)]); up = np.abs(tt[np.clip(k, 0, len(tt) - 1)] - t_abs)
        near = (np.minimum(dn, up) <= GUARD_S)
    else:
        near = np.zeros_like(eng)
    handsoff = eng & ~near & okc
    pr("   engaged %.0f s, of which hands-off after guard %.0f s (%.0f%% removed for overrides)"
       % ((eng & okc).sum() / FS, handsoff.sum() / FS, 100 * (1 - handsoff.sum() / max((eng & okc).sum(), 1))))
    # yaw curvature in the controller's frame: denom = cfac*sa/sR_true (steering part), sign-aligned to k_ctrl
    sgn = np.sign(np.nansum(denom[handsoff] * k_ctrl[handsoff])) or 1.0
    k_true = sgn * denom
    k_ctrl_steer = sgn * cfac * np.radians(sa) / served(asa, level)
    pr("   |sa|      n(s)   true/ctrl-read (=served/true sR)   implied true sR   |  true/desired  ctrl/desired")
    brows = []
    for lo, hi in [(10, 20), (20, 45), (45, 70), (70, 100), (100, 130), (130, 165), (165, 210), (210, 270), (270, 400)]:
        m = handsoff & base & (asa >= lo) & (asa < hi) & (np.abs(k_des) > 5e-4)
        if m.sum() < 100:
            pr("   %-8s %5.0f  -- too few hands-off engaged" % ("%d-%d" % (lo, hi), m.sum() / FS)); continue
        s1 = fit3(k_ctrl_steer[m], k_true[m], intercept=False)
        s2 = fit3(k_des[m], k_true[m], intercept=False)
        s3 = fit3(k_des[m], k_ctrl[m], intercept=False)
        srv = float(np.median(served(asa[m], level)))
        pr("   %-8s %5.0f        %6.3f                        %6.2f          |   %6.3f       %6.3f"
           % ("%d-%d" % (lo, hi), m.sum() / FS, s1["tls"], srv / s1["tls"], s2["tls"], s3["tls"]))
        brows.append(dict(lo=lo, hi=hi, n_s=m.sum() / FS, true_over_read=s1["tls"], sr_implied=srv / s1["tls"],
                          true_over_des=s2["tls"], ctrl_over_des=s3["tls"]))
    rows.append(dict(closed_loop=brows))

    json.dump(rows, open(os.path.join(SCR, "sr_newroute_%s.json" % rid.split("_")[1][:8]), "w"), indent=1, default=float)
    open(os.path.join(SCR, "sr_newroute_%s.txt" % rid.split("_")[1][:8]), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
