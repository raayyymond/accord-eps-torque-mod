"""Shared data prep + spectral estimator for the e2_phase delay study.

Time base: a uniform 100 Hz grid on host time. The sent command u (0xE4, in torque units u = e4/4089, sign chosen so
that +u produces +angle at low frequency) is placed on the grid by LINEAR interpolation of its sendcan logMonoTime
samples; the steering angle / rate by linear interpolation of carState logMonoTime samples. The SAME prep is applied
to the synthetic positive control, whose true plant receives the zero-order-held command starting D after each send
stamp -- so the recovered D is defined exactly as "sendcan logMonoTime -> effect in carState logMonoTime", with the
command hold modelled explicitly (a ZOH of T = 10 ms contributes exp(-jwT/2) sinc(wT/2), included in the fit model).
"""
import sys
from pathlib import Path
import numpy as np
from scipy import signal, optimize

KIT = Path(__file__).resolve().parents[5]
CACHE = KIT / "analysis-2020accord" / "_scratch" / "cache" / "v282ref"
FS = 100.0
T_ZOH = 0.010
E4_SCALE = 4089.0
TORQUE_ROUTES = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
                 "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]
V282_ROUTES = ["0000006c--2bc842dbac", "00000064--ce6b0b0ebb"]
SPEED_BINS = [(0.0, 8.0), (8.0, 15.0), (15.0, 99.0)]
CHUNK_S = 10.24          # analysis chunk (1024 samples); chunks are the bootstrap unit (block bootstrap)
NPS = 256                # Welch segment inside a chunk: 2.56 s, df 0.39 Hz


def load_route(route):
    D = np.load(CACHE / f"{route}.npz", allow_pickle=True)
    t_cst = D["t_cst"]; t_e4 = D["t_e4"]
    t0 = max(t_cst[0], t_e4[0]); t1 = min(t_cst[-1], t_e4[-1])
    tg = np.arange(t0, t1, 1.0 / FS)
    R = dict(route=route, t=tg,
             sa=np.interp(tg, t_cst, D["sa_deg"]), sr=np.interp(tg, t_cst, D["sr_deg"]),
             v=np.interp(tg, t_cst, D["vego"]), pressed=np.interp(tg, t_cst, D["spress"]) > 0.5,
             u=np.interp(tg, t_e4, D["e4_cmd"]) / E4_SCALE,
             lat=np.interp(tg, D["t_cc"], D["lat_active"]) > 0.5,
             csact=np.interp(tg, D["t_cs"], D["cs_active"]) > 0.5,
             req=np.interp(tg, t_e4, D["e4_req"]) > 0.5 if "e4_req" in D.files else None,
             sp=np.interp(tg, D["t_cs"], D["cs_la_des"]), jk=np.interp(tg, D["t_cs"], D["cs_la_jerk"]),
             curv=np.interp(tg, D["t_cs"], D["cs_des_curv"]),
             t_cst=t_cst.copy(), t_e4=t_e4.copy(), e4=D["e4_cmd"].copy())
    # clock-gap guard: a grid point is valid only if both streams have a sample within 25 ms
    gap_c = np.abs(t_cst[np.clip(np.searchsorted(t_cst, tg), 0, len(t_cst) - 1)] - tg)
    gap_e = np.abs(t_e4[np.clip(np.searchsorted(t_e4, tg), 0, len(t_e4) - 1)] - tg)
    R["clock_ok"] = (gap_c < 0.025) & (gap_e < 0.025)
    D.close()
    return R


def handsoff_mask(R):
    m = R["lat"] & R["csact"] & ~R["pressed"] & R["clock_ok"]
    if R["req"] is not None:
        m &= R["req"]
    # guard: drop 0.5 s around every steeringPressed edge (transients of hand removal)
    p = R["pressed"].astype(float)
    near = np.convolve(p, np.ones(101), mode="same") > 0
    return m & ~near


def chunks(mask, v, n=int(CHUNK_S * FS)):
    """Non-overlapping chunks of n contiguous valid samples; returns (i0, i1, median speed)."""
    out = []
    i, N = 0, len(mask)
    while i < N:
        if not mask[i]:
            i += 1; continue
        j = i
        while j < N and mask[j]:
            j += 1
        for k in range(i, j - n + 1, n):
            out.append((k, k + n, float(np.median(v[k:k + n]))))
        i = j
    return out


def chunk_spectra(u, y, nps=NPS):
    """Welch auto/cross spectra of one chunk (detrended). Returns f, Suu, Syy, Suy (Suy = E[conj(U) Y])."""
    f, Suu = signal.welch(u, FS, nperseg=nps, noverlap=nps // 2, detrend="linear")
    _, Syy = signal.welch(y, FS, nperseg=nps, noverlap=nps // 2, detrend="linear")
    _, Suy = signal.csd(u, y, FS, nperseg=nps, noverlap=nps // 2, detrend="linear")
    return f, Suu, Syy, Suy


def zoh(w, T=T_ZOH):
    x = w * T / 2
    return np.exp(-1j * x) * np.sinc(x / np.pi)


def model_H(w, D, J, b, k, out="angle"):
    s = 1j * w
    P = 1.0 / (J * s * s + b * s + k)
    if out == "rate":
        P = P * s
    return np.exp(-s * D) * zoh(w) * P


def fit_tf(f, H, coh, nave, fband=(0.5, 8.0), cmin=0.5, out="angle", D0=0.03, fixJ=None):
    """Weighted complex NLS of log H (log-magnitude and phase residuals) over bins with coherence > cmin.
    Weight = 1/var: var(log|H|) ~ var(phase) ~ (1-coh)/(2 nave coh)  (Bendat & Piersol)."""
    sel = (f >= fband[0]) & (f <= fband[1]) & (coh > cmin) & np.isfinite(H) & (np.abs(H) > 0)
    if sel.sum() < 4:
        return None
    w = 2 * np.pi * f[sel]; Hs = H[sel]; c = coh[sel]
    wt = np.sqrt(2 * nave * c / np.maximum(1 - c, 1e-3))
    lnH = np.log(Hs)

    def resid(p):
        D, lJ, lb, lk = p
        J = np.exp(lJ) if fixJ is None else fixJ
        m = model_H(w, D, J, np.exp(lb), np.exp(lk), out)
        r = np.log(m) - lnH
        r = r.real + 1j * np.angle(np.exp(1j * r.imag))
        return np.concatenate([r.real * wt, r.imag * wt])

    best = None
    for Dg in (0.0, 0.03, 0.06, 0.09):
        for Jg in (8e-5, 3e-4, 1e-3):
            p0 = [Dg, np.log(Jg), np.log(3e-3), np.log(5e-3)]
            try:
                r = optimize.least_squares(resid, p0, bounds=([-0.05, np.log(1e-6), np.log(1e-6), np.log(1e-5)],
                                                              [0.25, np.log(1e-1), np.log(1.0), np.log(1.0)]))
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
    D, lJ, lb, lk = best.x
    # covariance from the Jacobian (residuals are whitened by wt -> sigma^2 ~ cost*2/(n-p))
    Jm = best.jac
    dof = max(len(best.fun) - 4, 1)
    s2 = 2 * best.cost / dof
    try:
        cov = np.linalg.pinv(Jm.T @ Jm) * s2
        corr = cov / np.sqrt(np.outer(np.diag(cov), np.diag(cov)))
        sdD = float(np.sqrt(cov[0, 0]))
        rDJ = float(corr[0, 1])
    except Exception:
        sdD, rDJ = float("nan"), float("nan")
    return dict(D=float(D), J=float(np.exp(lJ)) if fixJ is None else fixJ, b=float(np.exp(lb)), k=float(np.exp(lk)),
                sdD=sdD, corr_D_J=rDJ, nbins=int(sel.sum()), fmin=float(f[sel].min()), fmax=float(f[sel].max()),
                cost=float(best.cost), dof=dof)


def phase_slope_delay(f, H, coh, fband, cmin=0.5, plant=None):
    """Model-free group delay: -d(unwrapped phase)/dw by weighted linear regression over the band.
    If plant=(J,b,k) is given, the plant's own phase (and the ZOH) is first removed."""
    sel = (f >= fband[0]) & (f <= fband[1]) & (coh > cmin)
    if sel.sum() < 3:
        return None
    w = 2 * np.pi * f[sel]
    ph = np.angle(H[sel])
    if plant is not None:
        J, b, k = plant
        ph = np.angle(H[sel] / (zoh(w) / (J * (1j * w) ** 2 + b * 1j * w + k)))
    ph = np.unwrap(ph)
    c = coh[sel]
    wt = c / np.maximum(1 - c, 1e-3)
    A = np.vstack([w, np.ones_like(w)]).T
    W = np.sqrt(wt)
    sol, *_ = np.linalg.lstsq(A * W[:, None], ph * W, rcond=None)
    return dict(tau=float(-sol[0]), n=int(sel.sum()))


def fit_joint(f, Ha, ca, Hr, cr, nave, fband=(1.5, 8.0), cmin=0.5, fixJ=None, Dstarts=(0.0, 0.03, 0.06, 0.09)):
    """Joint fit of angle and rate transfer functions with shared D, J, b, k."""
    sa = (f >= fband[0]) & (f <= fband[1]) & (ca > cmin)
    sr = (f >= fband[0]) & (f <= fband[1]) & (cr > cmin)
    if sa.sum() + sr.sum() < 5:
        return None
    parts = []
    for sel, H, c, o in ((sa, Ha, ca, "angle"), (sr, Hr, cr, "rate")):
        if sel.sum():
            parts.append((2 * np.pi * f[sel], np.log(H[sel]), np.sqrt(2 * nave * c[sel] / np.maximum(1 - c[sel], 1e-3)), o))

    def resid(p):
        D, lJ, lb, lk = p
        J = np.exp(lJ) if fixJ is None else fixJ
        out = []
        for w, lnH, wt, o in parts:
            r = np.log(model_H(w, D, J, np.exp(lb), np.exp(lk), o)) - lnH
            out += [r.real * wt, np.angle(np.exp(1j * r.imag)) * wt]
        return np.concatenate(out)

    best = None
    for Dg in Dstarts:
        for Jg in (8e-5, 3e-4, 1e-3):
            try:
                r = optimize.least_squares(resid, [Dg, np.log(Jg), np.log(3e-3), np.log(5e-3)],
                                           bounds=([-0.05, np.log(1e-6), np.log(1e-6), np.log(1e-5)],
                                                   [0.25, np.log(1e-1), np.log(1.0), np.log(1.0)]))
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
    D, lJ, lb, lk = best.x
    dof = max(len(best.fun) - 4, 1)
    try:
        cov = np.linalg.pinv(best.jac.T @ best.jac) * (2 * best.cost / dof)
        rDJ = float(cov[0, 1] / np.sqrt(cov[0, 0] * cov[1, 1])); sdD = float(np.sqrt(cov[0, 0]))
    except Exception:
        rDJ = sdD = float("nan")
    return dict(D=float(D), J=float(np.exp(lJ)) if fixJ is None else fixJ, b=float(np.exp(lb)), k=float(np.exp(lk)),
                sdD=sdD, corr_D_J=rDJ, nbins=int(sa.sum() + sr.sum()), cost=float(best.cost), dof=dof)


def innovation(R, mask, ukey="u", nlag=40, bins=((0.0, 8.0), (8.0, 15.0), (15.0, 99.0)), ridge=1e-6, use_u=None):
    """Command INNOVATION instrument: residual of u_t regressed (per speed bin, least squares) on lags 1..nlag of u,
    steering angle and steering rate (all strictly past on the 100 Hz grid; the command at t can only see carState
    >= 11 ms old). The residual is by construction orthogonal to the past measurement, so it carries none of the
    feedback of past disturbances/noise, and IV H = S_ey / S_eu is consistent for the causal plant."""
    import os
    if use_u is None:
        use_u = os.environ.get("INNOV_ULAGS", "1") != "0"
    u = R[ukey]; a = R["sa"]; r = R["sr"]; v = R["v"]
    N = len(u)
    valid = mask.copy()
    # need nlag of contiguous valid history
    run = np.zeros(N, int); c = 0
    for i in range(N):
        c = c + 1 if mask[i] else 0; run[i] = c
    valid &= run > nlag
    e = np.zeros(N)
    for lo, hi in bins:
        idx = np.where(valid & (v >= lo) & (v < hi))[0]
        if len(idx) < 20 * nlag:
            continue
        X = np.empty((len(idx), 3 * nlag + 1))
        for L in range(1, nlag + 1):
            X[:, L - 1] = u[idx - L]; X[:, nlag + L - 1] = a[idx - L]; X[:, 2 * nlag + L - 1] = r[idx - L]
        X[:, -1] = 1.0
        if not use_u:
            X[:, :nlag] = 0.0
        sc = X.std(0) + 1e-12; sc[-1] = 1
        Xs = X / sc
        beta = np.linalg.solve(Xs.T @ Xs + ridge * len(idx) * np.eye(Xs.shape[1]), Xs.T @ u[idx])
        e[idx] = u[idx] - Xs @ beta
    return e
