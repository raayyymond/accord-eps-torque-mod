"""Equation-error delay sweep: u(t-D) = J*acc + b*rate + ks*kmap(v)*angle + F*sgn(rate) + c.

Time conventions (both the real data and the positive control use these exactly):
  * the command u is a ZERO-ORDER HOLD from each sendcan logMonoTime (physical: EPS holds the last frame), built on
    a 1 ms grid, delayed by D (integer ms on that grid = the sub-sample interpolation of the command), band-passed
    zero-phase at 1 kHz, then read at each carState logMonoTime.
  * measurements (angle, rate) are the carState samples, treated as a uniform 100 Hz sequence (EPS clock), their
    derivatives by central difference, band-passed with the same zero-phase Butterworth designed at 100 Hz.
  * D is therefore "sendcan logMonoTime -> carState logMonoTime", with the ZOH hold as part of the physical input.
    Under a sample-point (no-hold) convention the same data read D + 5 ms.
Regressors variants: 'rate' (rate = logged rate, acc = d rate/dt) and 'angle' (rate = d angle/dt, acc = d2 angle/dt2).
Dwell handling: frames with |raw rate| < RMIN deg/s are excluded from the LS sums (still filtered through).
"""
import numpy as np
from scipy import signal

FS = 100.0
DGRID = np.arange(0, 121)            # ms
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
BINS = [(0.0, 8.0), (8.0, 15.0), (15.0, 99.0)]
NAMES = ["acc", "rate", "kang", "sgn", "c"]


def kmap(v):
    return np.interp(v, HOLD_V_BP, HOLD_K_V)


def runs(mask, t, min_s=10.0, max_gap=0.04):
    out, n, i = [], len(mask), 0
    while i < n:
        if not mask[i]:
            i += 1; continue
        j = i
        while j + 1 < n and mask[j + 1] and (t[j + 1] - t[j]) < max_gap:
            j += 1
        if t[j] - t[i] >= min_s:
            out.append((i, j + 1))
        i = j + 1
    return out


def design(band):
    lo, hi = band
    if lo is None or lo <= 0:
        return (signal.butter(2, hi, btype="low", fs=FS, output="sos"),
                signal.butter(2, hi, btype="low", fs=1000.0, output="sos"))
    return (signal.butter(2, [lo, hi], btype="band", fs=FS, output="sos"),
            signal.butter(2, [lo, hi], btype="band", fs=1000.0, output="sos"))


def accumulate(t_cs, ang, rate, v, mask, t_u, u, band=(0.3, 6.0), variant="rate", rmin=2.0, blk_s=10.0, edge_s=1.0,
               keep_series=False, guard=0, demean_block=False, sgn_src="rate"):
    """Returns list of blocks: dict(bin, n, XX (5x5), Xy (nD x 5), yy (nD)). Optionally per-run series for residuals."""
    sos100, sos1k = design(band)
    blocks, series = [], []
    for a, b in runs(mask, t_cs):
        tc = t_cs[a:b]
        A = ang[a:b]; Rr = rate[a:b]; V = v[a:b]
        if variant == "rate":
            rr = Rr
            acc = np.gradient(Rr) * FS
        elif variant == "angle":
            rr = np.gradient(A) * FS
            acc = np.gradient(rr) * FS
        elif variant == "hyb_rateA":        # rate regressor from angle, acc from logged rate
            rr = np.gradient(A) * FS
            acc = np.gradient(Rr) * FS
        elif variant == "hyb_accA":         # rate regressor logged, acc from angle
            rr = Rr
            acc = np.gradient(np.gradient(A)) * FS * FS
        if sgn_src == "rate":
            sref = Rr
        else:                                # sign/dwell from zero-phase 3 Hz low-passed angle derivative
            sref = signal.sosfiltfilt(signal.butter(2, 3.0, fs=FS, output="sos"), np.gradient(A) * FS)
        sg = np.sign(sref)
        kang = kmap(V) * A
        X = np.column_stack([signal.sosfiltfilt(sos100, x) for x in (acc, rr, kang, sg)])
        # command: ZOH on 1 ms grid covering [tc0-0.2-0.12, tc_end+0.2]
        tf0 = tc[0] - 0.4; nf = int(np.ceil((tc[-1] + 0.4 - tf0) * 1000.0)) + 1
        tf = tf0 + np.arange(nf) / 1000.0
        idx = np.searchsorted(t_u, tf, side="right") - 1
        if idx[0] < 0 or idx[-1] >= len(t_u):
            continue
        uf = signal.sosfiltfilt(sos1k, u[idx])
        # u(t-D) at carState times
        pos = (tc - tf0) * 1000.0
        Y = np.empty((len(DGRID), len(tc)))
        for kD, Dm in enumerate(DGRID):
            p = pos - Dm
            i0 = np.floor(p).astype(int); fr = p - i0
            Y[kD] = uf[i0] * (1 - fr) + uf[i0 + 1] * fr
        ne = int(edge_s * FS)
        use = np.zeros(len(tc), bool); use[ne:len(tc) - ne] = True
        dwell = np.abs(sref) < rmin
        if guard > 0:
            dwell = np.convolve(dwell.astype(float), np.ones(2 * guard + 1), mode="same") > 0
        use &= ~dwell
        Xc = np.column_stack([X, np.ones(len(tc))])
        nb = int(blk_s * FS)
        for s in range(0, len(tc), nb):
            sl = slice(s, min(s + nb, len(tc)))
            for bi, (vlo, vhi) in enumerate(BINS):
                m = use[sl] & (V[sl] >= vlo) & (V[sl] < vhi)
                if m.sum() < 50:
                    continue
                Xm = Xc[sl][m]; Ym = Y[:, sl][:, m]
                if demean_block:
                    Xm = Xm - Xm.mean(0); Xm[:, -1] = 1.0 / np.sqrt(m.sum()) * 0 + 1.0
                    Ym = Ym - Ym.mean(1, keepdims=True)
                blocks.append(dict(bin=bi, n=int(m.sum()), XX=Xm.T @ Xm, Xy=Ym @ Xm, yy=np.einsum("ij,ij->i", Ym, Ym)))
        if keep_series:
            series.append((Xc, uf, pos, use, V))
    return blocks, series


def solve(blocks):
    """Pooled SSR(D) and parameters for a list of blocks."""
    XX = sum(bk["XX"] for bk in blocks); Xy = sum(bk["Xy"] for bk in blocks); yy = sum(bk["yy"] for bk in blocks)
    n = sum(bk["n"] for bk in blocks)
    sc = np.sqrt(np.diag(XX)) + 1e-30
    XXn = XX / np.outer(sc, sc)
    th = np.linalg.solve(XXn[None], (Xy / sc)[..., None])[..., 0] / sc     # nD x 5
    ssr = yy - np.einsum("dj,dj->d", th, Xy)
    return ssr, th, n


def argmin_sub(ssr):
    k = int(np.argmin(ssr))
    if 0 < k < len(ssr) - 1:
        y0, y1, y2 = ssr[k - 1], ssr[k], ssr[k + 1]
        den = y0 - 2 * y1 + y2
        off = 0.5 * (y0 - y2) / den if den > 0 else 0.0
        return float(DGRID[k] + off), k
    return float(DGRID[k]), k


def curvature_ci(ssr, n_eff_frac, n):
    """95% profile-likelihood interval: SSR(D) - SSR_min <= 3.84 * SSR_min / N_eff."""
    k = int(np.argmin(ssr)); smin = ssr[k]
    neff = max(n * n_eff_frac, 5.0)
    thr = smin + 3.84 * smin / neff
    lo = k
    while lo > 0 and ssr[lo - 1] <= thr:
        lo -= 1
    hi = k
    while hi < len(ssr) - 1 and ssr[hi + 1] <= thr:
        hi += 1
    return float(DGRID[lo]), float(DGRID[hi]), neff


def neff_frac(series, th, kD, bi):
    """N_eff/N from the residual autocorrelation (Bartlett sum to first zero crossing) in one speed bin."""
    num, den = 0.0, 0.0
    for Xc, uf, pos, use, V in series:
        vlo, vhi = BINS[bi]
        m = use & (V >= vlo) & (V < vhi)
        if m.sum() < 200:
            continue
        p = pos - DGRID[kD]; i0 = np.floor(p).astype(int); fr = p - i0
        r = uf[i0] * (1 - fr) + uf[i0 + 1] * fr - Xc @ th
        r = np.where(m, r, 0.0)
        r0 = float(np.dot(r, r))
        s = 1.0
        for L in range(1, 200):
            rho = float(np.dot(r[:-L], r[L:])) / (r0 + 1e-30)
            if rho <= 0:
                break
            s += 2 * rho
        num += m.sum(); den += m.sum() * s
    return (num / den) if den > 0 else np.nan


def bootstrap(blocks_by_unit, nboot=500, seed=0):
    """Resample units (list of block-lists) with replacement; return D_opt per resample."""
    rng = np.random.default_rng(seed)
    U = len(blocks_by_unit)
    # precompute unit sums
    sums = []
    for bl in blocks_by_unit:
        sums.append((sum(b["XX"] for b in bl), sum(b["Xy"] for b in bl), sum(b["yy"] for b in bl)))
    out = []
    for _ in range(nboot):
        pick = rng.integers(0, U, U)
        XX = sum(sums[i][0] for i in pick); Xy = sum(sums[i][1] for i in pick); yy = sum(sums[i][2] for i in pick)
        sc = np.sqrt(np.diag(XX)) + 1e-30
        try:
            th = np.linalg.solve((XX / np.outer(sc, sc))[None], (Xy / sc)[..., None])[..., 0] / sc
        except np.linalg.LinAlgError:
            continue
        ssr = yy - np.einsum("dj,dj->d", th, Xy)
        out.append(argmin_sub(ssr)[0])
    return np.array(out)
