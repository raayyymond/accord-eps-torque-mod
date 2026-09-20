"""Recover the EPS's own transmit clock from batch membership, to sub-batch precision.

The EPS sends 0x14A (and 0x18F, 0x1AB) on its own periodic schedule.  pandad delivers CAN in batches
(one 'can' event per ~10 ms, one logMonoTime per batch).  A frame in batch n arrived after batch n-1 was
read and before batch n was read:  cb_t[n-1] - d < e_k <= cb_t[n] - d, with d pandad's read->publish offset
(common to every frame of the can stream, so it cancels in any comparison between two frames of that stream).
Model e_k = a + T*k over windows short enough that clock drift is negligible; scan T, take the feasible
interval for a (robust: the q and 1-q quantiles of the bounds, since pandad's read time jitters ~1 ms
around its publish time).  With the EPS clock incommensurate with pandad's poll, the interval tightens to ~poll jitter.
Windows with a batch gap or an infeasible fit (a dropped/duplicated frame breaks k) are dropped.
"""
import numpy as np


def fit_clock(t_frames, bi, cb_t, win=3000, T_nom=0.010, ppm_span=1500, n_scan=1501, q=0.01, min_width=-0.0005):
    """Returns e (fitted arrival time on the can-batch clock, NaN where not fitted), width (feasible
    interval width, s) and T (fitted period) per frame."""
    N = len(t_frames)
    e = np.full(N, np.nan); width = np.full(N, np.nan); Tf = np.full(N, np.nan)
    lo_all = cb_t[np.clip(bi - 1, 0, None)]
    up_all = cb_t[bi]
    Ts = T_nom * (1 + np.linspace(-ppm_span, ppm_span, n_scan) * 1e-6)
    k = np.arange(win, dtype=float)
    for s in range(0, N - win, win):
        up = up_all[s:s + win]; lo = lo_all[s:s + win]
        if np.any(np.diff(t_frames[s:s + win]) > 3.5 * T_nom) or bi[s] == 0:
            continue
        amax = np.quantile(up[None, :] - Ts[:, None] * k[None, :], q, axis=1)
        amin = np.quantile(lo[None, :] - Ts[:, None] * k[None, :], 1 - q, axis=1)
        wid = amax - amin
        ib = int(np.argmax(wid))
        if wid[ib] <= min_width:
            continue
        e[s:s + win] = 0.5 * (amax[ib] + amin[ib]) + Ts[ib] * k
        width[s:s + win] = wid[ib]
        Tf[s:s + win] = Ts[ib]
    return e, width, Tf
