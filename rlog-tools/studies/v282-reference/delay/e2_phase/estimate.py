"""Frequency-domain D_act estimator: per speed bin, cross-spectra command -> steering angle / rate, fit
H(jw) = exp(-jwD) * ZOH(jw) * 1/(J s^2 + b s + k)  [ * s for rate ]  by weighted complex NLS over coherent bins.

Two spectral estimators of H:
  DIRECT  H = S_uy / S_uu                      (biased toward -1/C in closed loop)
  IV      H = S_zy / S_zu, z = exogenous input  (real data: controlsState desiredLateralAccel, the setpoint;
                                                synthetic: the exogenous command). Coherence gate for IV =
                                                min(coh_zu, coh_zy) > cmin.
Block bootstrap over 20.48 s chunks (the resampling unit) for CIs; profile over fixed J for D-J identifiability.
"""
import numpy as np
from scipy import optimize
import common as C

FMAX_KEEP = 12.0


def chunk_stack(R, mask, zkey="sp", ukey="u"):
    ch = C.chunks(mask, R["v"])
    rows = []
    for i0, i1, vmed in ch:
        u = R[ukey][i0:i1]; a = R["sa"][i0:i1]; r = R["sr"][i0:i1]; z = R[zkey][i0:i1]
        f, Suu, Saa, Sua = C.chunk_spectra(u, a)
        _, _, Srr, Sur = C.chunk_spectra(u, r)
        _, Szz, _, Szu = C.chunk_spectra(z, u)
        _, _, _, Sza = C.chunk_spectra(z, a)
        _, _, _, Szr = C.chunk_spectra(z, r)
        keep = f <= FMAX_KEEP
        rows.append(dict(v=vmed, i0=i0, Suu=Suu[keep], Saa=Saa[keep], Srr=Srr[keep], Sua=Sua[keep], Sur=Sur[keep],
                         Szz=Szz[keep], Szu=Szu[keep], Sza=Sza[keep], Szr=Szr[keep]))
    f = f[f <= FMAX_KEEP] if ch else None
    return f, rows


def combine(rows, idx=None):
    if idx is None:
        idx = range(len(rows))
    S = {}
    for i in idx:
        for k, x in rows[i].items():
            if k.startswith("S"):
                S[k] = S.get(k, 0) + x
    return S


def H_of(S, est, out):
    y = "a" if out == "angle" else "r"
    if est == "direct":
        H = S[f"Su{y}"] / S["Suu"]
        coh = np.abs(S[f"Su{y}"]) ** 2 / (S["Suu"] * S[f"S{y}{y}"])
    else:
        H = S[f"Sz{y}"] / S["Szu"]
        c1 = np.abs(S["Szu"]) ** 2 / (S["Szz"] * S["Suu"])
        c2 = np.abs(S[f"Sz{y}"]) ** 2 / (S["Szz"] * S[f"S{y}{y}"])
        coh = np.minimum(c1, c2)
    return H, coh


def fit_bin(f, rows, est="direct", out="angle", fband=(1.5, 8.0), cmin=0.5, nboot=100, rng=None, jgrid=None, sign=-1.0):
    """sign: u enters as sign*e4/4089; the cache's u = +e4/4089, the +angle torque is -e4 (checked at low frequency)."""
    if len(rows) < 1:
        return None
    nseg_per_chunk = 7
    S = combine(rows)
    H, coh = H_of(S, est, out)
    H = H * sign
    nave = len(rows) * nseg_per_chunk
    res = C.fit_tf(f, H, coh, nave, fband=fband, cmin=cmin, out=out)
    if res is None:
        return dict(n_chunks=len(rows), fit=None)
    ps_raw = C.phase_slope_delay(f, H, coh, fband, cmin)
    ps_corr = C.phase_slope_delay(f, H, coh, fband, cmin, plant=(res["J"], res["b"], res["k"]))
    out_d = dict(n_chunks=len(rows), fit=res, group_delay_raw=ps_raw, group_delay_plant_removed=ps_corr,
                 coh_bins=[(round(float(ff), 2), round(float(c), 2)) for ff, c in zip(f, coh) if fband[0] <= ff <= fband[1]])
    if jgrid is not None:
        prof = []
        for Jf in jgrid:
            r = C.fit_tf(f, H, coh, nave, fband=fband, cmin=cmin, out=out, fixJ=Jf)
            if r:
                prof.append(dict(J=Jf, D=r["D"], cost=r["cost"], b=r["b"], k=r["k"]))
        out_d["J_profile"] = prof
    if nboot and len(rows) >= 3:
        rng = rng or np.random.default_rng(0)
        Ds = []
        for _ in range(nboot):
            idx = rng.integers(0, len(rows), len(rows))
            Sb = combine(rows, idx)
            Hb, cb = H_of(Sb, est, out)
            rb = C.fit_tf(f, Hb * sign, cb, nave, fband=fband, cmin=cmin, out=out)
            if rb:
                Ds.append(rb["D"])
        if len(Ds) >= 10:
            out_d["D_boot_ci95"] = [float(np.percentile(Ds, 2.5)), float(np.percentile(Ds, 97.5))]
            out_d["n_boot_ok"] = len(Ds)
    return out_d
