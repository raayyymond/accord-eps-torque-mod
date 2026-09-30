# -*- coding: utf-8 -*-
"""d3_attribution.py -- lens "dynamics", design rule 6 / criterion F8: can ONE short drive attribute each candidate
on the EXISTING wire (the 427 tap, 50 Hz, 8-count quantiser; 0x18F rate; 0xE4 command)?

Method (a synthetic flight built from the real V294 flight, r71b):
  1. march V294 and each candidate, byte-exact, on r71b's own 0xE4 command and 1 kHz rate operand (open-loop replay:
     the same command and wheel motion, so only the cells differ) -> T_V294, T_c (tap sign).  V294 must equal plib's
     march bit for bit (positive control of the replay).
  2. real residual e = T_tap - quant(T_V294[tap tick])  (what the exact model does not capture on the real flight).
     synthetic tap of a candidate flight = quant(T_c[tap tick]) + e   (same noise, same quantiser, same tap timing).
  3. ESTIMATOR (pre-registered, CRITERIA F8): on hands-off engaged tap frames, y = tap - quant(T_V294[tick]),
     r = T_c[tick] - T_V294[tick];  beta = sum(y r)/sum(r^2) per 30 s window; SE by a 1 s block bootstrap (200).
     beta = 1 -> the candidate flew; beta = 0 -> V294 flew.  NULL CONTROL: the REAL r71b tap must read beta ~ 0.
  4. SECOND READ, no model of the candidate needed: the FF-identity LAG -- the tap against the STATIC surface
     sign*surface(idx)*m/254 shifted by L ms; the best L (resid rms minimum over hands-off engaged frames with
     |d cmd/dt| large) moves with the output-lag time constant.
Output: d3_attribution_out.txt, d3_attribution.json
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
sys.path.insert(0, HERE)
import v295_harness as H  # noqa: E402
from d1_linear import lag_cells  # noqa: E402
import plib as P  # noqa: E402


def windows(mask_frames, n):
    """consecutive groups of n hands-off engaged tap frames in time order (= 'n/50 s of hands-off engaged frames' of
    one short drive; the |bar| < 400 mask breaks contiguous runs, so no 30 s contiguous run exists on r71b).
    Returns index arrays."""
    idx = np.flatnonzero(mask_frames)
    return [idx[j * n:(j + 1) * n] for j in range(len(idx) // n)]


def beta_se(y, r, rng, blk=50, nb=200):
    den = float(np.sum(r * r))
    if den <= 0:
        return float("nan"), float("nan")
    beta = float(np.sum(y * r) / den)
    nbk = len(y) // blk
    if nbk < 3:
        return beta, float("nan")
    Y = y[:nbk * blk].reshape(nbk, blk)
    R = r[:nbk * blk].reshape(nbk, blk)
    bs = []
    for _ in range(nb):
        ii = rng.integers(0, nbk, nbk)
        d_ = np.sum(R[ii] ** 2)
        bs.append(np.sum(Y[ii] * R[ii]) / d_ if d_ > 0 else np.nan)
    return beta, float(np.nanstd(bs))


def main():
    lines = []
    pr = lambda *a: (print(*a, flush=True), lines.append(" ".join(str(x) for x in a)))  # noqa: E731
    base = H.Cells.v294()
    C = [lag_cells(base, f) for f in (7.0, 8.0, 10.0, 12.0)] + [
        base.replace(kd_y=(256,) * 4, d_clamp=10240, sum_clamp=15240, name="D256"),
        base.replace(fb_a=1014, name="A1014_bheld"), base.replace(fb_a=1017, name="A1017_bheld"),
        lag_cells(base, 10.0).replace(fb_a=1014, name="L10+A1014")]
    d = H.route()
    L = H.Lane([base] + C)
    B = L.B
    x1k = np.clip(np.round(d["x1k"]), -12000, 12000).astype(np.int64)
    sp = d["sgn"].astype(np.int64)[None, :] * L.map_tab[:, d["idx"]]
    tt = d["tick_tap"]
    sg = d["sg"]
    cache = os.path.join(HERE, "_scratch", "d3_march_%s.npz" % "_".join(c.name for c in C).replace("+", "p"))
    if os.path.exists(cache):
        z = np.load(cache)
        liveT, ok = z["liveT"], int(z["ok"])
        pr("d3_attribution: loaded the march at the tap ticks from %s" % os.path.basename(cache))
    else:
        t0 = time.time()
        T = L.march(np.repeat(x1k[None, :], B, 0), sp, np.repeat(d["idx"][None, :], B, 0), np.repeat(d["m"][None, :], B, 0))
        pr("d3_attribution: marched %d lanes x %d ticks in %.0f s" % (B, T.shape[1], time.time() - t0))
        live = sg * T
        ok = int(np.sum(live[0] != d["T1k_live"]))
        liveT = live[:, tt]
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        np.savez(cache, liveT=liveT, ok=ok)
        del T, live
    pr("positive control: V294 march vs plib T1k_live mismatching ticks = %d (must be 0)" % ok)
    j = d["j100"]
    ho = d["eng"][j] & (np.abs(d["bar"][j]) < 400) & ~d["pressed"][j]
    tap = d["T_tap"].astype(float)
    q0 = P.quant(liveT[0])
    e = tap - q0
    pr("real residual (tap - quant(V294 march)), hands-off engaged: %.2f counts rms over %d tap frames (%.0f s)" % (
        np.sqrt(np.mean(e[ho] ** 2)), ho.sum(), ho.sum() / 50.0))
    W = windows(ho, 1500)                           # 30 s of hands-off engaged tap frames (50 Hz)
    pr("30 s groups of hands-off engaged tap frames: %d" % len(W))
    rng = np.random.default_rng(71)
    J = {}
    for ci, c in enumerate(C, start=1):
        r = (liveT[ci] - liveT[0]).astype(float)
        qc = P.quant(liveT[ci])
        tap_syn = qc + e
        y_syn = tap_syn - q0
        y_null = tap - q0
        zs, zn, bs_, bn_ = [], [], [], []
        for w in W:
            bs, ss = beta_se(y_syn[w], r[w], rng)
            bn, sn = beta_se(y_null[w], r[w], rng)
            zs.append(bs / ss if ss > 0 else np.nan); zn.append(bn / sn if sn > 0 else np.nan)
            bs_.append(bs); bn_.append(bn)
        zs, zn = np.array(zs), np.array(zn)
        # pooled
        bP, sP = beta_se(y_syn[ho], r[ho], rng)
        bN, sN = beta_se(y_null[ho], r[ho], rng)
        pr("  %-12s |dT| rms at tap (hands-off) %.2f counts, p99 %.1f | 30 s windows: synthetic beta median %.3f, z median %.1f, "
           "min %.1f, frac z>3 %.2f | NULL (real tap) beta median %+.3f, |z| median %.2f, frac |z|>3 %.2f | pooled syn %.3f+-%.3f "
           "null %+.3f+-%.3f" % (c.name, np.sqrt(np.mean(r[ho] ** 2)), np.percentile(np.abs(r[ho]), 99), np.median(bs_),
                                np.nanmedian(zs), np.nanmin(zs), np.nanmean(zs > 3), np.median(bn_), np.nanmedian(np.abs(zn)),
                                np.nanmean(np.abs(zn) > 3), bP, sP, bN, sN))
        J[c.name] = dict(dT_rms=float(np.sqrt(np.mean(r[ho] ** 2))), syn_beta_med=float(np.median(bs_)), syn_z_med=float(np.nanmedian(zs)),
                         syn_z_min=float(np.nanmin(zs)), syn_frac_z3=float(np.nanmean(zs > 3)), null_beta_med=float(np.median(bn_)),
                         null_absz_med=float(np.nanmedian(np.abs(zn))), null_frac_absz3=float(np.nanmean(np.abs(zn) > 3)),
                         pooled_syn=[bP, sP], pooled_null=[bN, sN], n_windows=len(W))
    # ---- second read: FF-identity lag vs the STATIC surface (no model of the candidate needed)
    pr("\nSECOND READ: FF-identity lag.  tap vs static surface sign*surface(idx)*m/254 at tick (tap tick - L); best L by resid rms")
    surf = H.surface(base, range(0, 241))                      # V294 static surface (T counts, marched from cold)
    Ts = sg * (-d["sgn"]) * surf[d["idx"]] * d["m"] / 254.0      # frame values; sign as the march (checked below)
    # sign check against the V294 null march on low-acceleration frames
    fr = np.clip(tt // 10, 0, len(Ts) - 1)
    cc = np.corrcoef(Ts[fr][ho], q0[ho])[0, 1]
    if cc < 0:
        Ts = -Ts
    lags = np.arange(-70, 21, 2)
    dcmd = np.abs(np.gradient(d["cmd"].astype(float)))[fr]
    fast = ho & (dcmd > np.percentile(dcmd[ho], 70))
    res = {}
    for nm, yv in [("V294 real tap", tap)] + [("%s synthetic" % c.name, P.quant(liveT[ci]) + e) for ci, c in enumerate(C, start=1)]:
        rr = []
        for Lm in lags:
            f2 = np.clip((tt - Lm) // 10, 0, len(Ts) - 1)
            rr.append(np.sqrt(np.mean((yv[fast] - Ts[f2][fast]) ** 2)))
        rr = np.array(rr)
        k = int(np.argmin(rr))
        # per 30 s window best lag (spread = the one-short-drive resolution)
        wl = []
        for w in W:
            m_ = fast[w]
            if m_.sum() < 100:
                continue
            ww = w[m_]
            rw = [np.sqrt(np.mean((yv[ww] - Ts[np.clip((tt[ww] - Lm) // 10, 0, len(Ts) - 1)]) ** 2)) for Lm in lags]
            wl.append(int(lags[int(np.argmin(rw))]))
        res[nm] = dict(best_lag_ms=int(lags[k]), resid_min=float(rr[k]), window_best_lags=wl)
        pr("   %-26s best lag %+d ms (resid %.1f) | per-30 s-window best lags median %+.0f IQR [%+.0f, %+.0f] n %d" % (
            nm, lags[k], rr[k], np.median(wl), np.percentile(wl, 25), np.percentile(wl, 75), len(wl)))
    J["ff_identity_lag"] = res
    json.dump(J, open(os.path.join(HERE, "d3_attribution.json"), "w"), indent=1)
    open(os.path.join(HERE, "d3_attribution_out.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
