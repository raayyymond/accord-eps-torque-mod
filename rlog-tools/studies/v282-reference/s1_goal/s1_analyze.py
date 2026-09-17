"""s1_goal pass 2: the reference table.  Reads s1_goal/_red/*.npz (s1_reduce.py).

Cells: speed bin (2-8, 8-15, 15-22, >22 m/s) x band (0.05-0.15 ... 1.2-2.5 Hz) x demand-amplitude tercile
(instantaneous Hilbert envelope of the band-passed MODEL demand; tercile edges per speed x band, pooled over
all groups with EQUAL GROUP WEIGHT so strata are common).  Per cell, per group:
  G_L   = sum(x*yL)/sum(x^2)   describing-function gain at the measured lag (achieved vs desired, lag aligned)
  rho_L = normalised correlation at that lag
  E_D   = rms(yD - x)          tracking error at the route's learned lat_delay ('on schedule'), m/s^2
  rE_D  = E_D / rms(x)         relative error
  E_L   = rms(yL - x)          error with timing removed
  y = pose (yaw rate x v, primary) and act (controller's angle-based measurement, sR-dependent)
Controls per cell: ctrl (x delayed 0.30 s -> G_L must be 1.000, E_L 0), null (act circularly shifted -> G ~ 0),
positive (x -> x = 1 exactly, by construction of the estimator: checked once).
CIs: hierarchical bootstrap (routes with replacement, then 60-s chunks within route), 1000 reps; split-half by
time within group.  Spectral cross-check: band_H-equivalent (per-bin |Pxy|/Pxx power-weighted, fixed nperseg)
with a run bootstrap.
"""
import sys, json, glob
from pathlib import Path
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

HERE = Path(__file__).resolve().parent
RED = HERE / "_red"
GROUPS = ["V282", "V282old", "T64", "T64B", "T5", "T4"]
BANDS = [(0.05, 0.15), (0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.50)]
VB = ["2-8", "8-15", "15-22", ">22"]
TER = ["lo", "mid", "hi", "all"]
YS = ["aL", "aD", "pL", "pD", "cL", "nul"]
NB = 1000
rng = np.random.default_rng(1)


def wquant(x, w, qs):
    o = np.argsort(x); cw = np.cumsum(w[o]); cw /= cw[-1]
    return [float(x[o][np.searchsorted(cw, q)]) for q in qs]


def load_all():
    files = sorted(glob.glob(str(RED / "*.npz")))
    per = {b: [] for b in range(len(BANDS))}
    meta = {}; lvl = []; specs = []
    for ri, f in enumerate(files):
        D = np.load(f, allow_pickle=True)
        M = json.loads(str(D["meta"])); meta[M["route"]] = M
        g = GROUPS.index(M["group"])
        ck = D["run"].astype(np.int64) * 1000 + D["chunk"]
        for b in range(len(BANDS)):
            s = D[f"b{b}_valid"] & (D["vb"] >= 0)
            ph = {k: np.zeros(s.sum(), np.complex64) for k in ("xa", "pDa", "aDa")}
            runid = D["run"][s]
            brk = np.r_[0, np.where(np.diff(runid) != 0)[0] + 1, len(runid)]
            for i0, i1 in zip(brk[:-1], brk[1:]):
                for k, src in (("xa", "x"), ("pDa", "pD"), ("aDa", "aD")):
                    ph[k][i0:i1] = signal.hilbert(D[f"b{b}_{src}"][s][i0:i1].astype(np.float64))
            per[b].append(dict(g=np.full(s.sum(), g, np.int8), r=np.full(s.sum(), ri, np.int16), ck=ck[s],
                               vb=D["vb"][s], env=D[f"b{b}_env"][s], x=D[f"b{b}_x"][s], ld=np.full(s.sum(), M["lat_delay"], np.float32),
                               **ph, **{y: D[f"b{b}_{y}"][s] for y in YS}))
        s = D["l_valid"] & (D["vb"] >= 0)
        lvl.append(dict(g=np.full(s.sum(), g, np.int8), r=np.full(s.sum(), ri, np.int16), ck=ck[s], vb=D["vb"][s],
                        x=D["lx"][s], a=D["laL"][s], p=D["lpL"][s]))
        for sp in D["specs"]:
            specs.append(dict(sp, g=g, r=ri))
        del D
    cat = lambda L: {k: np.concatenate([d[k] for d in L]) for k in L[0]}
    return {b: cat(per[b]) for b in per}, cat(lvl), specs, meta, [Path(f).stem for f in files]


def chunk_sums(d, sel):
    """per (route, chunk) sums: n, Sxx, and Sxy/Syy for each y."""
    key = d["r"][sel].astype(np.int64) * 10 ** 9 + d["ck"][sel]
    uk, inv = np.unique(key, return_inverse=True)
    x = d["x"][sel].astype(np.float64)
    cols = [np.ones_like(x), x * x]
    for y in YS:
        yy = d[y][sel].astype(np.float64); cols += [x * yy, yy * yy]
    A = np.zeros((len(uk), len(cols)))
    for j, c in enumerate(cols):
        A[:, j] = np.bincount(inv, weights=c, minlength=len(uk))
    return (uk // 10 ** 9).astype(int), A


def metrics(A):
    n, Sxx = A[..., 0], A[..., 1]
    out = dict(sec=n * 4 / V.FS, x_rms=np.sqrt(Sxx / np.maximum(n, 1)))
    for j, y in enumerate(YS):
        Sxy, Syy = A[..., 2 + 2 * j], A[..., 3 + 2 * j]
        err = np.maximum(Syy - 2 * Sxy + Sxx, 0)
        out[f"G_{y}"] = Sxy / np.maximum(Sxx, 1e-12)
        out[f"rho_{y}"] = Sxy / np.sqrt(np.maximum(Sxx * Syy, 1e-24))
        out[f"E_{y}"] = np.sqrt(err / np.maximum(n, 1))
        out[f"rE_{y}"] = np.sqrt(err / np.maximum(Sxx, 1e-12))
    return out


def boot(routes, A, nb=NB):
    ur = np.unique(routes)
    idx_by_r = [np.where(routes == r)[0] for r in ur]
    tot = np.zeros((nb, A.shape[1]))
    for b in range(nb):
        rs = rng.integers(0, len(ur), len(ur))
        for ri in rs:
            ii = idx_by_r[ri]
            tot[b] += A[ii[rng.integers(0, len(ii), len(ii))]].sum(0)
    return tot


KEYM = ["G_pL", "rE_pD", "E_pD", "G_aL", "rE_aD", "rho_pL", "G_cL", "E_cL", "G_nul"]


def main():
    per, lvl, specs, meta, rnames = load_all()
    res = dict(meta=meta, cells=[], tercile_edges={}, spectral=[], levels=[], jerk=[])
    for b, (f1, f2) in enumerate(BANDS):
        d = per[b]
        for v in range(4):
            sv = d["vb"] == v
            if sv.sum() < 100:
                continue
            w = np.zeros(sv.sum())
            gg = d["g"][sv]
            for g in np.unique(gg):
                w[gg == g] = 1.0 / (gg == g).sum()
            e1, e2 = wquant(d["env"][sv], w, [1 / 3, 2 / 3])
            res["tercile_edges"][f"{VB[v]}|{f1}-{f2}"] = [e1, e2]
            terc = np.digitize(d["env"], [e1, e2])
            for g in range(len(GROUPS)):
                for ti, tn in enumerate(TER):
                    sel = sv & (d["g"] == g) & ((terc == ti) if tn != "all" else True)
                    if sel.sum() < 50:
                        continue
                    routes, A = chunk_sums(d, sel)
                    pt = metrics(A.sum(0))
                    bt = metrics(boot(routes, A))
                    # split half: chunks in (route, time) order split by cumulative samples
                    cs = np.cumsum(A[:, 0]); h = cs <= cs[-1] / 2
                    h1 = metrics(A[h].sum(0)) if h.any() else None
                    h2 = metrics(A[~h].sum(0)) if (~h).any() else None
                    cell = dict(group=GROUPS[g], vb=VB[v], band=f"{f1}-{f2}", terc=tn, sec=float(pt["sec"]),
                                nroutes=int(len(np.unique(routes))), nchunks=int(len(routes)), x_rms=float(pt["x_rms"]))
                    for k in KEYM + ["E_pL", "rE_pL", "E_aD", "rho_aL"]:
                        cell[k] = float(pt[k])
                        if k in KEYM:
                            cell[k + "_ci"] = [float(np.nanpercentile(bt[k], 2.5)), float(np.nanpercentile(bt[k], 97.5))]
                    xa = d["xa"][sel]; den = float(np.sum(np.abs(xa) ** 2)); fc = float(np.sqrt(f1 * f2))
                    for nm_ in ("pDa", "aDa"):
                        hc = complex(np.sum(d[nm_][sel] * np.conj(xa))) / den
                        cell["Hc_" + nm_] = abs(hc)
                        cell["lag_" + nm_] = float(d["ld"][sel].mean() - np.angle(hc) / (2 * np.pi * fc))
                    cell["Sxx"] = float(A[:, 1].sum()); cell["errE_pD"] = float(A[:, 1].sum() * pt["rE_pD"] ** 2)
                    for k in ("G_pL", "rE_pD", "G_aL"):
                        cell[k + "_half"] = [float(h1[k]) if h1 else None, float(h2[k]) if h2 else None]
                    res["cells"].append(cell)
        print(f"band {f1}-{f2} done", flush=True)
    # ---- spectral cross-check (band_H-equivalent), speed bins x bands x groups, y = pose / act / ctrl
    for b, (f1, f2) in enumerate(BANDS):
        for v in range(4):
            for g in range(len(GROUPS)):
                L = [s for s in specs if s["band"] == b and s["vb"] == v and s["g"] == g]
                if not L:
                    continue
                def est(Ls):
                    Pxx = sum(s["Pxx"] * s["n"] for s in Ls)
                    o = {}
                    for nm in ("pose", "act", "ctrl"):
                        Pxy = sum(s["Pxy_" + nm] * s["n"] for s in Ls); Pyy = sum(s["Pyy_" + nm] * s["n"] for s in Ls)
                        H = np.abs(Pxy) / np.maximum(Pxx, 1e-30)
                        coh = np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30)
                        o["H_" + nm] = float(np.average(H, weights=Pxx)); o["coh_" + nm] = float(np.average(coh, weights=Pxx))
                    return o
                pt = est(L)
                rr = np.array([s["r"] for s in L]); ur = np.unique(rr)
                bs = []
                for _ in range(300):
                    pick = []
                    for ri in rng.choice(ur, len(ur)):
                        cand = [s for s in L if s["r"] == ri]
                        pick += [cand[i] for i in rng.integers(0, len(cand), len(cand))]
                    bs.append(est(pick)["H_pose"])
                res["spectral"].append(dict(group=GROUPS[g], vb=VB[v], band=f"{f1}-{f2}", nseg=len(L), nroutes=len(ur),
                                            sec=float(sum(s["n"] for s in L) / V.FS), **pt,
                                            H_pose_ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]))
    # ---- level (large-accel) and jerk describing functions, broadband 0-2.5 Hz, sign-folded secant gain
    ABIN = [0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 99]
    JBIN = [0, 0.25, 0.5, 1.0, 2.0, 4.0, 99]
    d = lvl
    jx = np.zeros_like(d["x"]); jp = np.zeros_like(d["p"]); ja = np.zeros_like(d["a"])
    # derivative inside each (route, chunk-run) contiguous block: decimated at 25 Hz
    key = d["r"].astype(np.int64) * 10 ** 7 + d["ck"] // 1000
    brk = np.r_[0, np.where(np.diff(key) != 0)[0] + 1, len(key)]
    for i0, i1 in zip(brk[:-1], brk[1:]):
        if i1 - i0 > 3:
            jx[i0:i1] = np.gradient(d["x"][i0:i1]) * 25; jp[i0:i1] = np.gradient(d["p"][i0:i1]) * 25
            ja[i0:i1] = np.gradient(d["a"][i0:i1]) * 25
    for nm, X, YP, YA, BINS in (("level", d["x"], d["p"], d["a"], ABIN), ("jerk", jx, jp, ja, JBIN)):
        for v in range(4):
            for g in range(len(GROUPS)):
                for k in range(len(BINS) - 1):
                    sel = (d["vb"] == v) & (d["g"] == g) & (np.abs(X) >= BINS[k]) & (np.abs(X) < BINS[k + 1])
                    if sel.sum() < 25:
                        continue
                    sg = np.sign(X[sel])
                    kk = d["r"][sel].astype(np.int64) * 10 ** 9 + d["ck"][sel]
                    uk, inv = np.unique(kk, return_inverse=True)
                    cols = [np.ones(sel.sum()), np.abs(X[sel]), YP[sel] * sg, YA[sel] * sg]
                    A = np.stack([np.bincount(inv, weights=c, minlength=len(uk)) for c in cols], 1)
                    routes = (uk // 10 ** 9).astype(int)
                    bt = boot(routes, A, 500)
                    gp = bt[:, 2] / bt[:, 1]; ga = bt[:, 3] / bt[:, 1]
                    T = A.sum(0)
                    res[("levels" if nm == "level" else "jerk")].append(dict(
                        group=GROUPS[g], vb=VB[v], lo=BINS[k], hi=BINS[k + 1], sec=float(T[0] * 4 / V.FS),
                        nroutes=int(len(np.unique(routes))), mean_des=float(T[1] / T[0]),
                        secant_pose=float(T[2] / T[1]), secant_pose_ci=[float(np.percentile(gp, 2.5)), float(np.percentile(gp, 97.5))],
                        secant_act=float(T[3] / T[1]), secant_act_ci=[float(np.percentile(ga, 2.5)), float(np.percentile(ga, 97.5))]))
    json.dump(res, open(HERE / "s1_results.json", "w"), indent=1)
    print("wrote s1_results.json", len(res["cells"]), "cells")


if __name__ == "__main__":
    main()
