"""verify pass 2: pool verify_reduce.py's per-route _red/*.npz, and re-test the finding under:
  (a) full group (as the finding computed it, but from an independently re-reduced cache)
  (b) leave-one-route-out -- V282 without its dominant 62-segment route 2bc842dbac; T64 as each
      single route alone (it only has two)
  (c) achieved channel = la_act (angle-based, sR-dependent) instead of la_pose, as the closest
      available substitute for la_yaw -- la_yaw (carState.yawRate) is IDENTICALLY ZERO in every
      cached route (confirmed in verify_reduce.py's meta, all yaw_std == 0.0): this fork build does
      not populate carState.yawRate, so the requested la_yaw cross-check cannot be run on this data.
      Reported as a finding in itself, not folded into the main verdict.
Metric = rE_D (rms(y_delayed_by_route's_own_lat_delay - x) / rms(x)) at the demand "mid" tercile,
and the phasor lag (route's own lat_delay minus the cross-spectral phase / (2*pi*f_center), matching
the finding's "Phasor lag model"). Hierarchical bootstrap (route, then 60s chunk) where >1 route is
pooled; chunk-only bootstrap for single-route cells (LOO, per-route-alone).
"""
import json, glob
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
RED = HERE / "_red"
BANDS = [(0.15, 0.30), (0.30, 0.60)]
VBN = ["8-15", "15-22", ">22"]
CHLET = {"pose": "p", "act": "a", "yaw": "y"}
NB = 2000
rng = np.random.default_rng(7)


def load_all():
    files = sorted(glob.glob(str(RED / "*.npz")))
    routes = {}
    for f in files:
        D = np.load(f, allow_pickle=True)
        M = json.loads(str(D["meta"]))
        routes[M["route"]] = dict(meta=M, D={k: D[k] for k in D.files if k != "meta"})
    return routes


def wquant(x, w, qs):
    o = np.argsort(x); cw = np.cumsum(w[o]); cw /= cw[-1]
    return [float(x[o][np.searchsorted(cw, q)]) for q in qs]


def tercile_edges(routes, band_i, vb_i, group_of):
    """Pooled envelope terciles, equal weight per GROUP (V282 vs T64), like s1_analyze.py but 2 groups."""
    xs, ws = [], []
    groups = sorted(set(group_of[r] for r in routes))
    for g in groups:
        rs = [r for r in routes if group_of[r] == g]
        e = []
        for r in rs:
            D = routes[r]["D"]
            s = D[f"b{band_i}_valid"] & (D["vb"] == vb_i)
            e.append(D[f"b{band_i}_env"][s])
        e = np.concatenate(e) if e else np.array([])
        if len(e) == 0:
            continue
        xs.append(e); ws.append(np.full(len(e), 1.0 / max(len(e), 1)))
    if not xs:
        return None
    x = np.concatenate(xs); w = np.concatenate(ws)
    return wquant(x, w, [1 / 3, 2 / 3])


def route_chunk_sums(routes, rsel, band_i, vb_i, edges, ch, terc_i=1):
    """Per (route, chunk) sums of n, Sxx, Sxy_D, Syy_D, Sxy_L, Syy_L, restricted to demand tercile terc_i
    (0=lo, 1=mid, 2=hi). Returns route_id array, chunk_key array, and A[:, cols]."""
    rows = []
    for ri, r in enumerate(rsel):
        D = routes[r]["D"]
        s = D[f"b{band_i}_valid"] & (D["vb"] == vb_i)
        if not np.any(s):
            continue
        env = D[f"b{band_i}_env"][s]
        e1, e2 = edges
        terc = np.digitize(env, [e1, e2])
        mid = terc == terc_i
        if not np.any(mid):
            continue
        cl = CHLET[ch]
        x = D[f"b{band_i}_x"][s][mid].astype(np.float64)
        yD = D[f"b{band_i}_{cl}D"][s][mid].astype(np.float64)
        yL = D[f"b{band_i}_{cl}L"][s][mid].astype(np.float64)
        run = D["run"][s][mid]; chunk = D["chunk"][s][mid]
        key = run.astype(np.int64) * 1000 + chunk
        uk, inv = np.unique(key, return_inverse=True)
        cols = [np.ones_like(x), x * x, x * yD, yD * yD, x * yL, yL * yL]
        A = np.zeros((len(uk), 6))
        for j, c in enumerate(cols):
            A[:, j] = np.bincount(inv, weights=c, minlength=len(uk))
        rows.append((np.full(len(uk), ri), A))
    if not rows:
        return np.array([]), np.zeros((0, 6))
    rid = np.concatenate([r for r, _ in rows])
    A = np.concatenate([a for _, a in rows], axis=0)
    return rid, A


def metrics(Asum):
    n, Sxx, SxyD, SyyD, SxyL, SyyL = Asum
    errD = max(SyyD - 2 * SxyD + Sxx, 0)
    errL = max(SyyL - 2 * SxyL + Sxx, 0)
    return dict(sec=n * 4 / 100.0, x_rms=np.sqrt(Sxx / max(n, 1)),
                G_D=SxyD / max(Sxx, 1e-12), G_L=SxyL / max(Sxx, 1e-12),
                rE_D=np.sqrt(errD / max(Sxx, 1e-12)), rE_L=np.sqrt(errL / max(Sxx, 1e-12)),
                E_D=np.sqrt(errD / max(n, 1)))


def boot_ci(rid, A, nb=NB):
    if len(rid) == 0:
        return (float("nan"), float("nan"))
    ur = np.unique(rid)
    idx_by_r = [np.where(rid == r)[0] for r in ur]
    out = np.zeros(nb)
    for b in range(nb):
        tot = np.zeros(6)
        if len(ur) > 1:
            rs = rng.integers(0, len(ur), len(ur))
        else:
            rs = [0]
        for k in rs:
            ii = idx_by_r[k]
            tot += A[ii[rng.integers(0, len(ii), len(ii))]].sum(0)
        out[b] = metrics(tot)["rE_D"]
    return (float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5)))


def lag_seconds(routes, rsel, band_i, vb_i, edges, ch, ld_by_route, terc_i=1):
    """Phasor lag: route's own lat_delay minus phase(sum(analytic(y_at_ld) * conj(analytic(x)))) / (2*pi*fc),
    on the given demand tercile's samples only, pooled across rsel. Matches s1_analyze.py's lag_pDa/lag_aDa."""
    f1, f2 = BANDS[band_i]; fc = (f1 * f2) ** 0.5
    xs, ys, lds, ns = [], [], [], []
    for r in rsel:
        D = routes[r]["D"]
        s = D[f"b{band_i}_valid"] & (D["vb"] == vb_i)
        if not np.any(s):
            continue
        env = D[f"b{band_i}_env"][s]
        e1, e2 = edges
        terc = np.digitize(env, [e1, e2])
        mid = terc == terc_i
        if not np.any(mid):
            continue
        run = D["run"][s][mid]
        brk = np.r_[0, np.where(np.diff(run) != 0)[0] + 1, len(run)]
        cl = CHLET[ch]
        x = D[f"b{band_i}_x"][s][mid].astype(np.float64)
        y = D[f"b{band_i}_{cl}D"][s][mid].astype(np.float64)
        for i0, i1 in zip(brk[:-1], brk[1:]):
            if i1 - i0 < 8:
                continue
            xa = signal.hilbert(x[i0:i1]); ya = signal.hilbert(y[i0:i1])
            xs.append(xa); ys.append(ya); ns.append(i1 - i0)
            lds.append(ld_by_route[r])
    if not xs:
        return float("nan")
    xa = np.concatenate(xs); ya = np.concatenate(ys)
    ldmean = float(np.average(lds, weights=ns))
    den = float(np.sum(np.abs(xa) ** 2))
    hc = complex(np.sum(ya * np.conj(xa))) / max(den, 1e-30)
    return ldmean - float(np.angle(hc)) / (2 * np.pi * fc)


def main():
    routes = load_all()
    group_of = {r: routes[r]["meta"]["group"] for r in routes}
    ld_by_route = {r: routes[r]["meta"]["lat_delay"] for r in routes}
    V282 = [r for r in routes if group_of[r] == "V282"]
    T64 = [r for r in routes if group_of[r] == "T64"]
    DOM = "0000006c--2bc842dbac"

    variants = {
        "V282_full": V282,
        "V282_LOO_no_dom": [r for r in V282 if r != DOM],
        "V282_dom_only": [r for r in V282 if r == DOM],
        "T64_full": T64,
    }
    for r in T64:
        variants[f"T64_only_{r.split('--')[1][:6]}"] = [r]
    for r in V282:
        if r != DOM:
            variants[f"V282_only_{r.split('--')[1][:6]}"] = [r]

    report = []
    for band_i, (f1, f2) in enumerate(BANDS):
        for vb_i, vbn in enumerate(VBN):
            edges = tercile_edges(routes, band_i, vb_i, group_of)
            if edges is None:
                continue
            for ch in ("pose", "act"):
                for name, rsel in variants.items():
                    rid, A = route_chunk_sums(routes, rsel, band_i, vb_i, edges, ch)
                    if A.shape[0] == 0 or A[:, 0].sum() < 25:
                        continue
                    m = metrics(A.sum(0))
                    ci = boot_ci(rid, A)
                    lag = lag_seconds(routes, rsel, band_i, vb_i, edges, ch, ld_by_route)
                    meanv = float(np.average([routes[r]["meta"]["meanv"] for r in rsel],
                                              weights=[1 for _ in rsel])) if rsel else float("nan")
                    report.append(dict(band=f"{f1}-{f2}", vb=vbn, ch=ch, variant=name,
                                        nroutes=len(np.unique(rid)) if len(rid) else 0,
                                        sec=round(m["sec"], 1), meanv=round(meanv, 1),
                                        x_rms=round(m["x_rms"], 4),
                                        rE_D=round(m["rE_D"], 3), rE_D_ci=[round(ci[0], 3), round(ci[1], 3)],
                                        G_D=round(m["G_D"], 3), lag_s=round(lag, 3)))
    json.dump(report, open(HERE / "verify_results.json", "w"), indent=1)
    # console summary for the key cells the finding cites
    print(f"{'band':10s}{'vb':7s}{'ch':5s}{'variant':22s}{'nrt':4s}{'sec':7s}{'meanv':7s}{'rE_D':7s}{'ci':18s}{'lag_s':7s}")
    for c in report:
        print(f"{c['band']:10s}{c['vb']:7s}{c['ch']:5s}{c['variant']:22s}{c['nroutes']:<4d}{c['sec']:<7.1f}{c['meanv']:<7.1f}{c['rE_D']:<7.3f}{str(c['rE_D_ci']):18s}{c['lag_s']:<7.3f}")
    print("wrote verify_results.json,", len(report), "cells")


if __name__ == "__main__":
    main()
