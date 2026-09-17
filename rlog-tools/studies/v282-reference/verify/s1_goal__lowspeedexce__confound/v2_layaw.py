"""Confound check 2: independent cross-check using la_yaw (carState yaw rate x v) instead of
la_pose (livePose yaw rate x v, what the original finding used as its primary channel). Mirrors
s1_reduce.py's 'D' (on-schedule, route median lat_delay) construction exactly, band 0.6-1.2 Hz,
same speed bins and tercile edges as the original finding, one route at a time.
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

S1 = Path('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s1_goal')
OUT = Path(__file__).resolve().parent
FS = V.FS
F1, F2 = 0.60, 1.20
VB = [(2.0, 8.0), (8.0, 15.0)]
VBN = ["2-8", "8-15"]
rng = np.random.default_rng(11)

R1 = json.load(open(S1 / "s1_results.json"))
TERC_EDGES = R1["tercile_edges"]

# routes to check: the ones behind the headline T64-vs-V282(-vs-T64B) cells
ROUTES = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac",
          "0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
          "00000075--6c8687d5bd", "00000076--d0b7ea7e4d"]


def bp(x, f1, f2):
    sos = signal.butter(2, [f1, f2], btype="band", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x, padtype="even")


def vbin(v):
    b = np.full(len(v), -1, int)
    for k, (a, c) in enumerate(VB):
        b[(v >= a) & (v < c)] = k
    return b


def process_route(route):
    S = V.load(route)
    t, v = S["t"], S["v"]
    m = V.usable(S, 2.0)
    x_all = np.nan_to_num(S["model"])
    yaw_all = S["la_yaw"].copy()
    pose_all = S["la_pose"].copy()
    has_yaw = np.isfinite(yaw_all).mean() > 0.9
    yaw_all = np.nan_to_num(yaw_all)
    pose_all = np.nan_to_num(pose_all)
    ld = float(np.nanmedian(S["lat_delay"][m])) if np.isfinite(S["lat_delay"][m]).any() else 0.2
    LD = int(round(ld * FS))
    runs = V.runs(m, t, min_s=8.0)
    trim = int(0.5 / F1 * FS)
    recs = []
    for ri, (i0, i1) in enumerate(runs):
        n = i1 - i0
        if n < 2 * trim + LD + 50:
            continue
        x = x_all[i0:i1]; ya = yaw_all[i0:i1]; po = pose_all[i0:i1]
        vb = vbin(v[i0:i1])
        xb = bp(x, F1, F2); yb = bp(ya, F1, F2); pb = bp(po, F1, F2)
        env = np.abs(signal.hilbert(xb))
        valid = np.zeros(n, bool); valid[trim: n - trim - LD] = True
        ii = np.arange(n)
        yD = yb[np.minimum(ii + LD, n - 1)]
        pD = pb[np.minimum(ii + LD, n - 1)]
        chunk = ((t[i0:i1] - t[i0]) // 60).astype(np.int32)
        idx = np.arange(0, n, 4)
        recs.append(dict(x=xb[idx], yD=yD[idx], pD=pD[idx], env=env[idx], vb=vb[idx], valid=valid[idx],
                          run=np.full(len(idx), ri), chunk=chunk[idx]))
    del S
    out = {k: np.concatenate([r[k] for r in recs]) for k in recs[0]} if recs else None
    return dict(route=route, has_yaw=bool(has_yaw), ld=ld, data=out)


def chunk_sums(d, sel, ykey):
    key = d["run"][sel].astype(np.int64) * 10 ** 9 + d["chunk"][sel]
    uk, inv = np.unique(key, return_inverse=True)
    x = d["x"][sel].astype(np.float64); y = d[ykey][sel].astype(np.float64)
    cols = [np.ones_like(x), x * x, x * y, y * y]
    return np.stack([np.bincount(inv, weights=c, minlength=len(uk)) for c in cols], 1)


def rE(A):
    n, Sxx, Sxy, Syy = A[:, 0].sum(), A[:, 1].sum(), A[:, 2].sum(), A[:, 3].sum()
    err = max(Syy - 2 * Sxy + Sxx, 0)
    return float(np.sqrt(err / max(Sxx, 1e-12))), float(n * 4 / FS)


def boot_rE(routes, A, nb=1000):
    ur = np.unique(routes)
    if len(ur) == 0:
        return (np.nan, np.nan)
    idx_by_r = [np.where(routes == r)[0] for r in ur]
    vals = []
    for _ in range(nb):
        rs = rng.integers(0, len(ur), len(ur))
        tot = np.zeros(4)
        for ri in rs:
            ii = idx_by_r[ri]
            tot += A[ii[rng.integers(0, len(ii), len(ii))]].sum(0)
        n, Sxx, Sxy, Syy = tot
        err = max(Syy - 2 * Sxy + Sxx, 0)
        vals.append(np.sqrt(err / max(Sxx, 1e-12)))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def main():
    perroute = {}
    for rk in ROUTES:
        r = process_route(rk)
        perroute[rk] = r
        n = 0 if r["data"] is None else len(r["data"]["x"])
        print(rk, "has_yaw", r["has_yaw"], "ld", round(r["ld"], 3), "n", n, flush=True)

    GROUPMAP = {
        "V282": ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"],
        "T64": ["0000006c--68c6e94b17", "0000006d--05e83bb04f"],
        "T64B": ["0000006e--6ca3e014fd"],
        "T5": ["00000076--d0b7ea7e4d"],
        "T4": ["00000075--6c8687d5bd"],
    }
    results = []
    for vi, vname in enumerate(VBN):
        for tname in ("all", "hi"):
            for g, rks in GROUPMAP.items():
                if tname == "hi":
                    e1, e2 = TERC_EDGES[f"{vname}|0.6-1.2"]
                parts_yaw = []; parts_pose = []; routeids = []
                per_route_yaw = []
                for rk in rks:
                    d = perroute[rk]["data"]
                    if d is None or not perroute[rk]["has_yaw"]:
                        continue
                    sel = d["vb"] == vi
                    if tname == "hi":
                        sel = sel & (d["env"] >= e2)
                    if sel.sum() < 10:
                        continue
                    Ay = chunk_sums(d, sel, "yD")
                    Ap = chunk_sums(d, sel, "pD")
                    key = d["run"][sel].astype(np.int64) * 10 ** 9 + d["chunk"][sel]
                    uk = np.unique(key)
                    routeids.append(np.full(len(uk), rk))
                    parts_yaw.append(Ay); parts_pose.append(Ap)
                    e_y, s_y = rE(Ay)
                    per_route_yaw.append(dict(route=rk, rE_yaw=e_y, sec=s_y))
                if not parts_yaw:
                    continue
                rid = np.concatenate(routeids)
                Ay_all = np.concatenate(parts_yaw, 0); Ap_all = np.concatenate(parts_pose, 0)
                e_yaw, sec_yaw = rE(Ay_all)
                e_pose, sec_pose = rE(Ap_all)
                lo_y, hi_y = boot_rE(rid, Ay_all)
                lo_p, hi_p = boot_rE(rid, Ap_all)
                results.append(dict(vb=vname, terc=tname, group=g, sec=sec_yaw,
                                     nroutes=len(np.unique(rid)),
                                     rE_layaw=e_yaw, rE_layaw_ci=[lo_y, hi_y],
                                     rE_lapose_samepool=e_pose, rE_lapose_ci=[lo_p, hi_p],
                                     per_route_yaw=per_route_yaw))
                print(f"{vname:6s} {tname:4s} {g:8s} la_yaw rE={e_yaw:.3f} [{lo_y:.3f},{hi_y:.3f}]  "
                      f"la_pose(same pool) rE={e_pose:.3f} [{lo_p:.3f},{hi_p:.3f}]  sec={sec_yaw:.0f} nroutes={len(np.unique(rid))}",
                      flush=True)
    json.dump(results, open(OUT / "v2_layaw_results.json", "w"), indent=1)
    print("wrote v2_layaw_results.json")


if __name__ == "__main__":
    main()
