# -*- coding: utf-8 -*-
"""sr_pool.py -- stage 2: per-route reduction of the slim segment npz into ONE pooled cache
carrying only what the SR estimator and its splits need, one row per carState sample.

Columns (all float32 except t/blk):
    sa_deg   wheel angle minus liveParameters.angleOffsetDeg          [deg]
    ang_deg  RAW steeringAngleDeg (for the free-intercept variant)    [deg]
    cfac     curvature_factor(v) = 1/(1 - sf v^2)/wheelbase           [1/m]
    denom    -yaw_cal/v - roll_comp(roll, v)                          [1/m]
    v        vEgo                                                     [m/s]
    rate     steeringRateDeg                                          [deg/s]
    drv      carState.steeringTorque                                  [raw]
    pressed  carState.steeringPressed                                 [0/1]
    eng      carControl.latActive  (SPLIT LABEL ONLY)                 [0/1]
    calok    liveCalibration.calStatus == calibrated                  [0/1]
    stiff    liveParameters.stiffnessFactor                           (census)
    aoff     liveParameters.angleOffsetDeg                            (census)
    ri       route index into the route table
    blk      cluster-bootstrap block id (route, 2 s)

GATES APPLIED HERE (none of the analysis gates, only validity):
    - a livePose sample within 0.10 s, a liveCalibration within 5 s, a liveParameters within 5 s
    - finite everything
Run: python sr_pool.py
"""
import glob, json, os, re, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SEGDIR = os.path.join(HERE, "_scratch", "segs")
OUT = os.path.join(HERE, "_scratch", "pooled.npz")
G = 9.81
BLOCK_S = 2.0

RID = re.compile(r"(75604b0a432fdc89_[0-9a-f]{8}--[0-9a-f]{10})--(\d+)\.npz$")


def rot_from_euler(e):
    r, p, y = e
    cr, sr, cp, sp, cy, sy = np.cos(r), np.sin(r), np.cos(p), np.sin(p), np.cos(y), np.sin(y)
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def yaw_cal_vec(r, p, y, wx, wy, wz):
    """(rot_from_euler([r,p,y]).T @ w)[2] == third COLUMN of R dotted with w, in closed form."""
    cr, sr_, cp, sp, cy, sy = np.cos(r), np.sin(r), np.cos(p), np.sin(p), np.cos(y), np.sin(y)
    return (cy * sp * cr + sy * sr_) * wx + (sy * sp * cr - cy * sr_) * wy + (cp * cr) * wz


def _selfcheck():
    rng = np.random.default_rng(0)
    for _ in range(5):
        e = rng.normal(0, 0.3, 3); w = rng.normal(0, 1, 3)
        a = (rot_from_euler(e).T @ w)[2]
        b = yaw_cal_vec(e[0], e[1], e[2], w[0], w[1], w[2])
        assert abs(a - b) < 1e-12, (a, b)


def hold_idx(ts, t, maxgap):
    """index of last ts <= t, or -1 when none / staler than maxgap."""
    i = np.searchsorted(ts, t, side="right") - 1
    ok = i >= 0
    j = np.where(ok, i, 0)
    ok &= (t - ts[j]) <= maxgap
    return np.where(ok, j, -1)


def load_route(rid, segfiles):
    segs = sorted(segfiles, key=lambda p: int(RID.search(os.path.basename(p)).group(2)))
    acc = {}
    cp = None
    for p in segs:
        z = np.load(p, allow_pickle=True)
        if cp is None:
            c = json.loads(str(z["carParams_json"]))
            if c:
                cp = c
        for k in z.files:
            if k in ("carParams_json", "n_events", "torn"):
                continue
            acc.setdefault(k, []).append(z[k])
    D = {k: np.concatenate(v) for k, v in acc.items()}
    return D, cp


def reduce_route(D, cp, ri):
    need = ("cs_t", "lp_t", "cal_t", "lpar_t", "cc_t")
    for k in need:
        if k not in D or len(D[k]) < 10:
            return None
    o = np.argsort(D["cs_t"])
    for k in list(D):
        if k.startswith("cs_"):
            D[k] = D[k][o]
    for pre in ("lp_", "cal_", "lpar_", "cc_"):
        o2 = np.argsort(D[pre + "t"])
        for k in list(D):
            if k.startswith(pre):
                D[k] = D[k][o2]

    m_, l_, aF = cp["mass"], cp["wheelbase"], cp["centerToFront"]
    cF, cR = cp["tireStiffnessFront"], cp["tireStiffnessRear"]
    aR = l_ - aF
    sf = m_ * (cF * aF - cR * aR) / (l_ ** 2 * cF * cR)

    # yaw_cal at livePose ticks
    ci = hold_idx(D["cal_t"], D["lp_t"], 30.0)
    ok_c = ci >= 0
    cj = np.where(ok_c, ci, 0)
    yc = yaw_cal_vec(D["cal_r"][cj].astype(np.float64), D["cal_p"][cj].astype(np.float64),
                     D["cal_y"][cj].astype(np.float64), D["lp_wx"].astype(np.float64),
                     D["lp_wy"].astype(np.float64), D["lp_wz"].astype(np.float64))
    yc = np.where(ok_c, yc, np.nan)
    calok_lp = np.where(ok_c, D["cal_ok"][cj], 0.0)

    t = D["cs_t"].astype(np.float64)
    li = hold_idx(D["lp_t"], t, 0.10)          # 20 Hz -> 0.10 s is <= 2 ticks
    pi = hold_idx(D["lpar_t"], t, 5.0)
    ei = hold_idx(D["cc_t"], t, 0.10)
    good = (li >= 0) & (pi >= 0) & (ei >= 0)
    lj, pj, ej = np.where(li >= 0, li, 0), np.where(pi >= 0, pi, 0), np.where(ei >= 0, ei, 0)

    v = D["cs_v"].astype(np.float64)
    roll = D["lpar_roll"][pj].astype(np.float64)
    aoff = D["lpar_aoff"][pj].astype(np.float64)
    cfac = 1.0 / (1.0 - sf * v ** 2) / l_
    rollc = (G * roll) / ((1.0 / sf) - v ** 2)
    yaw = yc[lj]
    denom = (-yaw / np.maximum(v, 1e-3)) - rollc

    ang = D["cs_ang"].astype(np.float64)
    good &= np.isfinite(denom) & np.isfinite(cfac) & np.isfinite(ang) & np.isfinite(aoff)
    if good.sum() < 100:
        return None

    t0 = t[good][0]
    R = dict(
        t=(t[good] - t0).astype(np.float64),
        sa_deg=(ang - aoff)[good].astype(np.float32),
        ang_deg=ang[good].astype(np.float32),
        cfac=cfac[good].astype(np.float32),
        denom=denom[good].astype(np.float32),
        v=v[good].astype(np.float32),
        rate=D["cs_rate"][good].astype(np.float32),
        drv=D["cs_drv"][good].astype(np.float32),
        pressed=D["cs_pressed"][good].astype(np.float32),
        eng=D["cc_lat"][ej][good].astype(np.float32),
        calok=calok_lp[lj][good].astype(np.float32),
        stiff=D["lpar_stiff"][pj][good].astype(np.float32),
        aoff=aoff[good].astype(np.float32),
        ri=np.full(int(good.sum()), ri, np.int32),
        blk=(ri.astype(np.int64) * 10 ** 7 + np.floor((t[good] - t0) / BLOCK_S).astype(np.int64)),
    )
    R["_sf"] = sf
    R["_wb"] = l_
    return R


def main():
    _selfcheck()
    files = glob.glob(os.path.join(SEGDIR, "*.npz"))
    byroute = {}
    for p in files:
        m = RID.search(os.path.basename(p))
        byroute.setdefault(m.group(1), []).append(p)
    routes = sorted(byroute)
    print("routes: %d  segments: %d" % (len(routes), len(files)), flush=True)
    cols = None
    parts = []
    meta = []
    for i, rid in enumerate(routes):
        D, cp = load_route(rid, byroute[rid])
        if cp is None:
            print("  %-46s NO carParams -- dropped" % rid, flush=True)
            meta.append(dict(route=rid, n=0, note="no carParams"))
            continue
        R = reduce_route(D, cp, np.int32(i))
        if R is None:
            print("  %-46s too little valid data -- dropped" % rid, flush=True)
            meta.append(dict(route=rid, n=0, note="no valid frames"))
            continue
        meta.append(dict(route=rid, n=int(len(R["sa_deg"])), segs=len(byroute[rid]),
                         sf=R.pop("_sf"), wheelbase=R.pop("_wb"),
                         steerRatio_cp=cp["steerRatio"], mass=cp["mass"]))
        if cols is None:
            cols = [k for k in R if not k.startswith("_")]
        parts.append(R)
        print("  [%2d/%2d] %-46s n=%7d (%6.0f s)" % (i + 1, len(routes), rid, len(R["sa_deg"]),
                                                     len(R["sa_deg"]) / 100.0), flush=True)
    P = {k: np.concatenate([p[k] for p in parts]) for k in cols}
    P["routes"] = np.array(routes)
    P["meta_json"] = np.array(json.dumps(meta, default=float))
    np.savez_compressed(OUT, **P)
    print("pooled: %d samples (%.0f s) -> %s" % (len(P["sa_deg"]), len(P["sa_deg"]) / 100.0, OUT))


if __name__ == "__main__":
    main()
