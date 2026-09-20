"""The decision-bearing real-data run, given that the estimator FAILED its realistic positive control.

cl_test.py established that on closed-loop data with an unmeasured road-torque disturbance -- i.e. the
actual data-generating situation -- the plain equation-error minimum lands anywhere from -27 to +201 ms
for a TRUE D_act of 30 or 60 ms, and iv_test.py showed the GMM/IV form still carries +15..+25 ms of bias
in its best band.  So the argmin is not reportable as a delay.  What IS reportable:

  1. PROFILE  -- SSE and R2 at FIXED D on a coarse grid (0..120 ms), per speed bin, so the orchestrator
     can see the curvature of the criterion and how much of it is real.
  2. DISCRIMINATION -- the paired, per-10-s-block difference SSE(60 ms) - SSE(30 ms), block-bootstrapped.
     This is the direct answer to "can these logs tell 30 ms from 46-61 ms apart", and it is a signed
     quantity with a CI, not an argmin.  Sign convention: NEGATIVE prefers 60 ms.
  3. PHYSICS   -- (J, b, g_k, F) at a FIXED D = 40 ms, per speed bin, route-cluster CI, because the
     coefficients are what the fit is actually good at and they bear on the plant facts independently.
  4. IV        -- the GMM delay sweep with the vision reference (desired wheel angle from
     controlsState.desiredCurvature and liveParameters.steerRatio) as the instrument, best band 0.3-8 Hz,
     reported RAW and with the -19 ms bias the closed-loop control measured for exactly this setting.
"""
import sys, json, math
from pathlib import Path
import numpy as np
from scipy import signal
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eqerr as E

HERE = Path(__file__).resolve().parent
WB = 2.83                                  # 2020 Accord wheelbase, m
DG = np.arange(0, 121, 2)
DFIX = 40.0
IV_BIAS_MS = 19.0                          # mean bias of IV@0.3-8 on the closed-loop control (+23, +15)
LAGS_MS = [0, 20, 40, 60, 80, 120, 160, 200]
BANDS = {"plain_0.3-8": (0.3, 8.0), "plain_1-6": (1.0, 6.0), "plain_0.5-4": (0.5, 4.0)}
SPD = E.SPD


def route_pack(rk, band, dwell=2.0, blk_s=10.0):
    """Per-10 s block: A=X'X, Bd=X'u_D, UU, and the IV blocks (ZZ, ZX, Zu_D)."""
    sos = E.make_L(band)
    D = np.load(E.V.CACHE / f"{rk}.npz", allow_pickle=True)
    t_cst = D["t_cst"]; t_e4 = D["t_e4"]; e4 = D["e4_cmd"] / E.E4_SCALE
    act = np.interp(t_cst, D["t_cs"], (D["cs_active"] > 0.5).astype(float)) > 0.5
    lat = np.interp(t_cst, D["t_cc"], (D["lat_active"] > 0.5).astype(float)) > 0.5
    ok = act & lat & (D["spress"] < 0.5)
    # exogenous instrument: the vision model's desired WHEEL angle
    sR = np.interp(t_cst, D["t_lp"], D["sR"]) if "t_lp" in D.files else np.full(len(t_cst), 16.3)
    des = np.interp(t_cst, D["t_cs"], D["cs_des_curv"]) * WB * sR * 180.0 / math.pi
    vego = D["vego"]; sa_all = D["sa_deg"]; sr_all = D["sr_deg"]
    del D
    out = []
    n = len(t_cst); i = 0; runs = []
    while i < n:
        if not ok[i]:
            i += 1; continue
        j = i
        while j + 1 < n and ok[j + 1] and (t_cst[j + 1] - t_cst[j]) < 0.04:
            j += 1
        if t_cst[j] - t_cst[i] >= 2 + blk_s:
            s = i
            while s < j + 1:
                e = min(s + 12000, j + 1)
                if t_cst[e - 1] - t_cst[s] >= 2 + blk_s:
                    runs.append((s, e))
                s = e
        i = j + 1
    for a, b in runs:
        g = np.arange(t_cst[a], t_cst[b - 1], 1 / E.FS)
        if len(g) < int((2 + blk_s) * E.FS):
            continue
        vv = np.interp(g, t_cst, vego)
        sa = np.interp(g, t_cst, sa_all); sr = np.interp(g, t_cst, sr_all)
        X = E.prep_run(g, sa, sr, vv, sos, "hold")
        rf = signal.sosfiltfilt(sos, np.interp(g, t_cst, des))
        Z = np.column_stack([np.interp(g - L * 1e-3, g, rf) for L in LAGS_MS])
        keep = np.abs(sr) >= dwell
        UB = np.empty((len(DG), len(g)), dtype=np.float32)
        for q, dms in enumerate(DG):
            UB[q] = signal.sosfiltfilt(sos, np.interp(g - dms * 1e-3, t_e4, e4))
        bs = int(blk_s * E.FS); ed = int(1.0 * E.FS)
        for s in range(ed, len(g) - ed - bs + 1, bs):
            sl = slice(s, s + bs); m = keep[sl]
            if m.sum() < 0.25 * bs:
                continue
            Xb = X[sl][m]; Zb = Z[sl][m]; ub = UB[:, sl][:, m]
            out.append(dict(route=rk, v=float(np.median(vv[sl])), nrow=int(m.sum()),
                            A=Xb.T @ Xb, Bd=(ub @ Xb).astype(np.float64),
                            UU=np.einsum("dn,dn->d", ub, ub).astype(np.float64),
                            ZZ=Zb.T @ Zb, ZX=Zb.T @ Xb, Zu=(ub @ Zb).astype(np.float64)))
        del UB, X, Z
    return out


def agg(blocks, w=None):
    w = np.ones(len(blocks)) if w is None else np.asarray(w, float)
    S = {}
    for kk in ("A", "Bd", "UU", "ZZ", "ZX", "Zu"):
        S[kk] = sum(wi * bl[kk] for wi, bl in zip(w, blocks) if wi)
    return S


def ls(S):
    Ai = np.linalg.inv(S["A"] + 1e-12 * np.trace(S["A"]) / 4 * np.eye(4))
    beta = S["Bd"] @ Ai.T
    return S["UU"] - np.einsum("dj,dj->d", beta, S["Bd"]), beta


def iv(S):
    W = np.linalg.pinv(S["ZZ"]); ZX = S["ZX"]
    Mi = np.linalg.pinv(ZX.T @ W @ ZX)
    b = (S["Zu"] @ W.T) @ ZX @ Mi.T            # (nD,4)
    e = S["Zu"] - b @ ZX.T
    return np.einsum("di,ij,dj->d", e, W, e), b


def main():
    rep = {}
    for bname, band in BANDS.items():
        allb = []
        for rk in E.TORQUE:
            allb += route_pack(rk, band)
        print(f"\n=== band {band[0]}-{band[1]} Hz   blocks {len(allb)} rows {sum(b['nrow'] for b in allb)} ===",
              flush=True)
        rng = np.random.default_rng(11)
        for lo, hi in SPD + [(0.0, 99.0)]:
            sel = [b for b in allb if lo <= b["v"] < hi]
            if len(sel) < 6:
                continue
            S = agg(sel)
            sse, beta = ls(S)
            R2 = 1 - sse / np.maximum(S["UU"], 1e-30)
            i30 = int(np.argmin(np.abs(DG - 30 - E.ZOH_CORR_MS)))
            i60 = int(np.argmin(np.abs(DG - 60 - E.ZOH_CORR_MS)))
            i40 = int(np.argmin(np.abs(DG - DFIX - E.ZOH_CORR_MS)))
            # paired block bootstrap on SSE(60) - SSE(30) and on the argmin
            dd, am, ivam = [], [], []
            sse_iv, _ = iv(S)
            for _ in range(500):
                w = rng.multinomial(len(sel), np.ones(len(sel)) / len(sel))
                Sb = agg(sel, w)
                s, _ = ls(Sb)
                dd.append(s[i60] - s[i30])
                am.append(DG[int(np.argmin(s))] - E.ZOH_CORR_MS)
                si, _ = iv(Sb)
                ivam.append(DG[int(np.argmin(si))] - E.ZOH_CORR_MS)
            dd = np.array(dd) / max(abs(sse[i30]), 1e-30)     # normalised: fraction of SSE(30)
            Jf, bf, gk, Ff = beta[i40]
            print(f"  v {lo:4.0f}-{hi:<4.0f} n{len(sel):4d}  R2@30 {R2[i30]:.3f}  R2@40 {R2[i40]:.3f}  "
                  f"R2@60 {R2[i60]:.3f}   plain argmin {DG[int(np.argmin(sse))]-E.ZOH_CORR_MS:+6.1f} "
                  f"[{np.percentile(am,2.5):+.0f},{np.percentile(am,97.5):+.0f}]   "
                  f"IV argmin {DG[int(np.argmin(sse_iv))]-E.ZOH_CORR_MS:+6.1f} "
                  f"[{np.percentile(ivam,2.5):+.0f},{np.percentile(ivam,97.5):+.0f}] "
                  f"(-{IV_BIAS_MS:.0f} bias -> {DG[int(np.argmin(sse_iv))]-E.ZOH_CORR_MS-IV_BIAS_MS:+.0f})")
            print(f"              [SSE(60)-SSE(30)]/SSE(30) = {np.median(dd)*100:+7.3f} % "
                  f"[{np.percentile(dd,2.5)*100:+.3f},{np.percentile(dd,97.5)*100:+.3f}] "
                  f"(negative prefers 60 ms)   beta@40ms: J {Jf:.2e} b {bf:+.2e} g_k {gk:+.3f} F {Ff:+.4f}",
                  flush=True)
            rep[f"{bname}|{lo:.0f}-{hi:.0f}"] = dict(
                n_blocks=len(sel), n_rows=int(sum(b["nrow"] for b in sel)),
                R2_30=float(R2[i30]), R2_40=float(R2[i40]), R2_60=float(R2[i60]),
                plain_argmin=float(DG[int(np.argmin(sse))] - E.ZOH_CORR_MS),
                plain_argmin_ci=[float(np.percentile(am, 2.5)), float(np.percentile(am, 97.5))],
                iv_argmin=float(DG[int(np.argmin(sse_iv))] - E.ZOH_CORR_MS),
                iv_argmin_ci=[float(np.percentile(ivam, 2.5)), float(np.percentile(ivam, 97.5))],
                iv_debiased=float(DG[int(np.argmin(sse_iv))] - E.ZOH_CORR_MS - IV_BIAS_MS),
                d_sse_pct=float(np.median(dd) * 100),
                d_sse_ci_pct=[float(np.percentile(dd, 2.5) * 100), float(np.percentile(dd, 97.5) * 100)],
                beta40=dict(J=float(Jf), b=float(bf), g_k=float(gk), F=float(Ff)),
                R2_profile={int(d): float(r) for d, r in zip(DG - E.ZOH_CORR_MS, R2)})
        # per route, best band only
        if bname == "plain_0.3-8":
            for rk in E.TORQUE:
                sub = [b for b in allb if b["route"] == rk]
                line = f"  {rk} {E.V.ROUTES[rk]['group']:5s}"
                for lo, hi in SPD:
                    s2 = [b for b in sub if lo <= b["v"] < hi]
                    if len(s2) < 3:
                        line += f"  {lo:.0f}-{hi:.0f}: --"; continue
                    S2 = agg(s2); s, _ = ls(S2); si, _ = iv(S2)
                    line += (f"  {lo:.0f}-{hi:.0f}: plain {DG[int(np.argmin(s))]-E.ZOH_CORR_MS:+5.0f} "
                             f"IV {DG[int(np.argmin(si))]-E.ZOH_CORR_MS:+5.0f} (n{len(s2)})")
                print(line, flush=True)
        del allb
    (HERE / "real_final.json").write_text(json.dumps(rep, indent=1, default=float))


if __name__ == "__main__":
    main()
