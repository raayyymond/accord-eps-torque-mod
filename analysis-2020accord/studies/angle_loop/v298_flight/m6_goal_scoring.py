# -*- coding: utf-8 -*-
r"""m6_goal_scoring.py -- M6: THE GOAL CRITERIA on V298 route 79, per speed band x AMPLITUDE class.

    python analysis-2020accord/studies/angle_loop/v298_flight/m6_goal_scoring.py

ANALYSIS ONLY.  Reads the v280 wire cache (r79_a1f5d2_al + refs r6c, r39, r71b_v294) and the fork cache r79_fork.npz.
Writes _scratch/out/r79/m6/m6_goal_scoring.{txt,json}.  No rlog read, no per-sample Python loop (loops run over
runs / windows / detected events only).  Target wall time < 30 s.

Signs (drive-read docstring, EVIDENCE there): theta = 0x14A angle deg (carState sign); theta_sp = -raw/10;
w18 = -wire/8 deg/s (sign of d theta/dt); bar = 0x18F torque x1.024; tap T100 in field LSB (= T/8).
Criteria (STATE "THE GOAL" + drive-read THR): tracking 0.95-1.05, turn-hold >= 0.90 (bands >= 8 m/s), dwell-then-jump
<= V282 per band, ring presence <= 0.5 %, F7 = 0, no new 5-30 Hz line, 18-22 Hz eng/dis vs V294 r71b,
hard-turn 1.6-3 Hz wheel-rate energy <= V282.
"""
from __future__ import annotations
import contextlib, io, json, sys, time, types
from pathlib import Path
import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view

T0 = time.time()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m6_common as C                                                   # noqa: E402
from m6_common import runs, FS                                         # noqa: E402

OUT = C.REPO / "_scratch" / "out" / "r79" / "m6"
OUT.mkdir(parents=True, exist_ok=True)
LINES = []


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


SB = (("<3", 0, 3), ("3-8", 3, 8), ("8-12", 8, 12), ("12-18", 12, 18), ("18-25", 18, 25), (">25", 25, 99))
DRB = (("8-15", 8, 15), ("15-22", 15, 22), (">22", 22, 99))                    # drive-read goal bands (check)
DJB = (("5-8", 5, 8), ("8-10", 8, 10), ("10-12.5", 10, 12.5), ("12.5-15", 12.5, 15), ("15-22", 15, 22),
       (">22", 22, 99), ("<5", 0, 5))                                          # drive-read dwell_jump bands (check)
SIB = (("0-5", 0, 5), ("5-10", 5, 10), ("10-20", 10, 20), (">20", 20, 99))      # symptom-instrument bands (check)
AMP = (("<5", 0, 5), ("5-20", 5, 20), (">20", 20, 1e9))
RATE = (("<20", 0, 20), ("20-60", 20, 60), (">60", 60, 1e9))
SOS05 = signal.butter(4, 0.5, "lowpass", fs=FS, output="sos")
SOS2 = signal.butter(2, 2.0, "lowpass", fs=FS, output="sos")
CLIP_V = [3.1, 8, 10, 11.75, 17.5, 26.9]
CLIP_D = [17, 15.5, 19.5, 17, 8.5, 4.5]                       # fork carcontroller error clip (deg), per the brief


def cls(x, edges):
    out = np.full(len(x), -1, int)
    for k, (_, lo, hi) in enumerate(edges):
        out[(x >= lo) & (x < hi)] = k
    return out


def bmask(W, lo, hi):
    return (W["vego"] >= lo) & (W["vego"] < hi)


def filt_runs(x, rr, sos):
    y = np.full(len(x), np.nan)
    for a, b in rr:
        if b - a > 30:
            y[a:b] = signal.sosfiltfilt(sos, np.nan_to_num(x[a:b]))
    return y


def ols(x, y):
    if len(x) < 50 or np.std(x) < 1e-9:
        return np.nan, np.nan, np.nan
    A = np.vstack([x, np.ones_like(x)]).T
    b = np.linalg.lstsq(A, y, rcond=None)[0]
    yh = A @ b
    r2 = 1 - np.sum((y - yh) ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-12)
    return float(b[0]), float(b[1]), float(r2)


def block_boot(x, y, blk=500, nb=400, seed=79):
    """5-s block bootstrap of the pooled OLS slope (with intercept)."""
    n = len(x) // blk
    if n < 4:
        return np.nan, np.nan
    xb, yb = x[:n * blk].reshape(n, blk), y[:n * blk].reshape(n, blk)
    S = np.c_[xb.sum(1), yb.sum(1), (xb * xb).sum(1), (xb * yb).sum(1)]
    idx = np.random.default_rng(seed).integers(0, n, (nb, n))
    s = S[idx].sum(1)
    N = n * blk
    sl = (s[:, 3] - s[:, 0] * s[:, 1] / N) / (s[:, 2] - s[:, 0] ** 2 / N)
    return float(np.percentile(sl, 2.5)), float(np.percentile(sl, 97.5))


# =====================================================================================================================
def prep(W, F=None):
    rr = runs(W["eng"], 30)
    W["sp2"] = filt_runs(W["theta_sp"], rr, SOS2)
    W["sprate"] = np.abs(np.gradient(np.nan_to_num(W["sp2"])) * FS)
    W["th2"] = filt_runs(W["theta"], rr, SOS2)
    W["thrate"] = np.abs(np.gradient(np.nan_to_num(W["th2"])) * FS)
    if F is not None:
        t = W["t"]
        W["des"] = C._zoh(F["t_cc"], F["cc_ang"], t)                   # pre-limit desired (actuators.steeringAngleDeg)
        W["lat"] = C._zoh(F["t_cc"], F["cc_latActive"].astype(float), t) > 0.5
        W["co"] = C._zoh(F["t_co"], F["co_ang"], t)                     # post-limit (carOutput) = wire sp
        W["csang"] = C._zoh(F["t_cs"], F["cs_ang"], t)
        W["clipb"] = np.interp(W["vego"], CLIP_V, CLIP_D)
        W["at_clip"] = np.abs(W["co"] - W["csang"]) >= W["clipb"] - 0.15
        W["limited"] = np.abs(W["des"] - W["co"]) > 0.5
    return W


def exposure(W):
    pr("\nE. EXPOSURE (engaged = req & SCA & 0x18F present; free = not steeringPressed).  seconds")
    pr("   band     eng   free | free by |theta_sp| <5 5-20 >20 | free by |d theta_sp/dt| (2 Hz LPF) <20 20-60 >60")
    ex = {}
    ca, cr = cls(np.abs(W["theta_sp"]), AMP), cls(W["sprate"], RATE)
    for nm, lo, hi in SB:
        m = W["eng"] & bmask(W, lo, hi)
        mf = m & W["free"]
        a = [float((mf & (ca == k)).sum() / FS) for k in range(3)]
        r = [float((mf & (cr == k)).sum() / FS) for k in range(3)]
        ex[nm] = dict(eng=float(m.sum() / FS), free=float(mf.sum() / FS), amp=a, rate=r)
        pr("   %-6s %6.1f %6.1f | %6.1f %6.1f %6.1f | %6.1f %6.1f %6.1f" % (nm, ex[nm]["eng"], ex[nm]["free"], *a, *r))
    return ex


def goal_runs(W, lo, hi, min_s=15.0):
    return runs(W["eng"] & W["free"] & bmask(W, lo, hi), int(min_s * FS))


def tracking(W, bands, ref_key="theta_sp", amp_split=True):
    """method 1 = drive-read tracking_and_hold form (pooled concatenated OLS with intercept on 0.5 Hz zero-phase LPF,
    first 4 s of each run dropped) + turn-hold; amplitude split = 4-s windows of those runs classed by max|sp_LPF|
    and p95 |d sp/dt| (2 Hz), pooled OLS per class + median excursion ratio.  method 2 = per-run demeaned slope;
    lag-compensated slope (best pooled shift 0-600 ms)."""
    out = {}
    for nm, lo, hi in bands:
        X, Y, secs = [], [], 0.0
        Wa, Wr, holds = [], [], []
        for a, b in goal_runs(W, lo, hi):
            xr = W[ref_key][a:b]
            if not np.isfinite(xr).all():
                continue
            x = signal.sosfiltfilt(SOS05, xr)
            y = signal.sosfiltfilt(SOS05, W["theta"][a:b])
            X.append(x[400:]); Y.append(y[400:]); secs += (b - a - 400) / FS
            d = np.gradient(x) * FS
            msk = (np.abs(x) >= 3.0) & (np.abs(d) <= np.maximum(1.0, 0.05 * np.abs(x))) & (np.arange(b - a) >= 400)
            for p, q in runs(msk, 150):
                holds.append((float(y[p:q].mean() / x[p:q].mean()), float(np.abs(x[p:q]).mean())))
            spr = W["sprate"][a:b]
            for s in range(400, b - a - 399, 400):
                e = s + 400
                Wa.append((int(np.searchsorted([5, 20], np.abs(x[s:e]).max(), side="right")), x[s:e], y[s:e]))
                Wr.append(int(np.searchsorted([20, 60], np.percentile(spr[s:e], 95), side="right")))
        if not X:
            out[nm] = dict(secs=0.0)
            continue
        Xa, Ya = np.concatenate(X), np.concatenate(Y)
        sl, ic, r2 = ols(Xa, Ya)
        ci = block_boot(Xa, Ya)
        Xd = np.concatenate([x - x.mean() for x in X]); Yd = np.concatenate([y - y.mean() for y in Y])
        sl_dm = float((Xd @ Yd) / (Xd @ Xd))
        best = (-np.inf, 0, np.nan)
        for L in range(0, 61, 2):
            xs = np.concatenate([x[:len(x) - L] for x in X]); ys = np.concatenate([y[L:] for y in Y])
            s_, _, r_ = ols(xs, ys)
            if r_ > best[0]:
                best = (r_, L, s_)
        row = dict(secs=secs, n_runs=len(X), track=sl, ci=ci, icpt=ic, r2=r2, track_demeaned=sl_dm,
                   sp_std=float(Xa.std()), lag_best_ms=best[1] * 10.0, track_lagcomp=best[2],
                   pass_=bool(0.95 <= sl <= 1.05), scored=secs >= 60.0)
        hv = np.array([h[0] for h in holds]); ha = np.array([h[1] for h in holds])
        row["hold"] = dict(n=len(hv), min=float(hv.min()) if len(hv) else np.nan,
                           med=float(np.median(hv)) if len(hv) else np.nan, by_amp={})
        for k, l, h in (("3-5", 3, 5), ("5-20", 5, 20), (">20", 20, 1e9)):
            s_ = (ha >= l) & (ha < h) if len(ha) else np.zeros(0, bool)
            row["hold"]["by_amp"][k] = (int(s_.sum()), float(hv[s_].min()) if s_.any() else np.nan)
        if amp_split:
            for key, lab, cl in (("by_amp", AMP, [w[0] for w in Wa]), ("by_rate", RATE, Wr)):
                row[key] = {}
                for k, (cn, _, _) in enumerate(lab):
                    sel = [i for i, c in enumerate(cl) if c == k]
                    if not sel:
                        row[key][cn] = dict(s=0.0)
                        continue
                    xs = np.concatenate([Wa[i][1] for i in sel]); ys = np.concatenate([Wa[i][2] for i in sel])
                    s_, _, r_ = ols(xs, ys)
                    exr = [np.ptp(Wa[i][2]) / np.ptp(Wa[i][1]) for i in sel if np.ptp(Wa[i][1]) >= 1.0]
                    row[key][cn] = dict(s=len(sel) * 4.0, slope=s_, r2=r_,
                                        exc_ratio=float(np.median(exr)) if exr else np.nan, n_exc=len(exr))
        out[nm] = row
    return out


def print_tracking(T, title):
    pr("\n" + title)
    pr("   band    s runs track [95% CI]        dmean  lagcomp(lag ms) R2   sp_std | hold n min med | by max|sp| class:"
       " slope (s) | excursion ratio/n")
    for nm, r in T.items():
        if not r.get("secs"):
            pr("   %-6s   0  (no 15-s free run)" % nm)
            continue
        cl = r.get("by_amp", {})
        cs = "  ".join("%s %.3f(%3.0f)" % (k, v.get("slope", np.nan), v["s"]) for k, v in cl.items())
        ce = "  ".join("%s %.2f/%d" % (k, v.get("exc_ratio", np.nan), v.get("n_exc", 0)) for k, v in cl.items())
        pr("   %-6s %4.0f %3d  %.3f [%.3f %.3f] %s %.3f  %.3f(%3.0f)  %.2f  %5.2f | %2d %.3f %.3f | %s | %s"
           % (nm, r["secs"], r["n_runs"], r["track"], r["ci"][0], r["ci"][1],
              "PASS" if r["pass_"] else "FAIL", r["track_demeaned"], r["track_lagcomp"], r["lag_best_ms"], r["r2"],
              r["sp_std"], r["hold"]["n"], r["hold"]["min"], r["hold"]["med"], cs, ce))
        if "by_rate" in r:
            pr("          by p95|d sp/dt| class: " + "  ".join("%s %.3f(%3.0f s)" % (k, v.get("slope", np.nan), v["s"])
                                                            for k, v in r["by_rate"].items())
               + " ; hold by |sp| (n,min): " + "  ".join("%s %d %.3f" % (k, *v) for k, v in r["hold"]["by_amp"].items()))


FT = (0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0)


def frf(W, lo, hi, amp_cls=None, nper=1024, hop=256):
    """H1 = Syx/Sxx of theta on theta_sp over Hann windows (10.24 s, 75 % overlap) inside engaged-free runs."""
    m = W["eng"] & W["free"] & bmask(W, lo, hi)
    st = []
    for a, b in runs(m, nper):
        st += list(range(a, b - nper + 1, hop))
    if not st:
        return None
    idx = np.array(st)[:, None] + np.arange(nper)[None, :]
    x, y = W["theta_sp"][idx], W["theta"][idx]
    if amp_cls is not None:
        k = (np.abs(x).max(1) >= amp_cls[0]) & (np.abs(x).max(1) < amp_cls[1])
        x, y = x[k], y[k]
    if len(x) < 3:
        return None
    win = np.hanning(nper)
    X = np.fft.rfft(signal.detrend(x, axis=1) * win, axis=1)
    Y = np.fft.rfft(signal.detrend(y, axis=1) * win, axis=1)
    Sxx, Syy, Sxy = (np.abs(X) ** 2).mean(0), (np.abs(Y) ** 2).mean(0), (np.conj(X) * Y).mean(0)
    f = np.fft.rfftfreq(nper, 1 / FS)

    def sm(z):
        z2 = z.copy(); z2[1:-1] = (z[:-2] + z[1:-1] + z[2:]) / 3
        return np.where(f >= 0.4, z2, z)
    Sxx, Syy, Sxy = sm(Sxx), sm(Syy), sm(Sxy)
    return dict(f=f, H=Sxy / Sxx, coh=np.abs(Sxy) ** 2 / (Sxx * Syy), n=len(x))


def frf_summary(R, cgate=0.6):
    f, H, coh = R["f"], R["H"], R["coh"]
    rows = {}
    for ft in FT:
        k = int(np.argmin(np.abs(f - ft)))
        rows[ft] = dict(mag=float(np.abs(H[k])), ph=float(np.degrees(np.angle(H[k]))),
                        lag_ms=float(-np.angle(H[k]) / (2 * np.pi * f[k]) * 1000), coh=float(coh[k]), ok=bool(coh[k] >= cgate))
    sel = np.flatnonzero((f >= 0.15) & (f <= 5.0))
    bw, edge = None, 5.0
    for k in sel:
        if coh[k] < cgate:
            edge = float(f[k]); break
        if np.abs(H[k]) < 0.707 and bw is None:
            bw = float(f[k])
    ok = np.zeros(len(f), bool); ok[sel] = coh[sel] >= cgate
    pk = (float(np.abs(H[ok]).max()), float(f[ok][np.argmax(np.abs(H[ok]))])) if ok.any() else (np.nan, np.nan)
    return dict(rows=rows, bw=bw, coh_edge=edge, peak=pk, n=R["n"])


def xcorr_lag(W, lo, hi):
    """second method for the lag: pooled cross-correlation of 0.1-2 Hz band-passed theta and theta_sp (runs >= 10 s)."""
    sos = signal.butter(2, [0.1, 2.0], "bandpass", fs=FS, output="sos")
    acc = np.zeros(201)
    for a, b in runs(W["eng"] & W["free"] & bmask(W, lo, hi), 1000):
        x = signal.sosfiltfilt(sos, W["theta_sp"][a:b]); y = signal.sosfiltfilt(sos, W["theta"][a:b])
        c = signal.correlate(y, x, mode="full", method="fft")
        mid = len(x) - 1
        acc += c[mid - 100: mid + 101]
    if not acc.any():
        return np.nan
    k = int(np.argmax(acc))
    d = 0.0
    if 0 < k < 200:
        y0, y1, y2 = acc[k - 1], acc[k], acc[k + 1]
        d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
    return float((k - 100 + d) * 10.0)


def dwell_jump_events(W, bands):
    """nl_sim.dwell_jump re-implemented to return event frames (same constants)."""
    ker = np.ones(10) / 10.0
    out = {}
    for nm, lo, hi in bands:
        ev, secs = [], 0.0
        for a, b in runs(W["eng"] & bmask(W, lo, hi), 200):
            secs += (b - a) / FS
            om, th, rf = W["w18"][a:b], W["theta"][a:b], W["theta_sp"][a:b]
            rs = np.convolve(np.abs(om), ker, "same")
            rr = runs(rs < 0.25, 10)
            for q, (p, e0) in enumerate(rr):
                if e0 + 2 >= len(th) or abs(rf[e0 - 1] - rf[p]) < 0.1:
                    continue
                e = rr[q + 1][0] if q + 1 < len(rr) else len(th) - 1
                e = min(e, e0 + 50, len(th) - 1)
                jump = abs(th[e] - th[e0])
                if jump >= max(2.0 * abs(rf[e] - rf[e0]), 0.2):
                    ev.append((a + e0, jump))
        out[nm] = dict(secs=secs, ev=ev, n=len(ev), per_min=60.0 * len(ev) / secs if secs else np.nan)
    return out


def si_dwells(W, bands, th=0.25):
    """v293_symptom_instruments.dwells re-implemented to return dwell frames (same constants)."""
    ker = np.ones(10) / 10.0
    rate = np.abs(W["wire"]) / 8.0
    out = {}
    for nm, lo, hi in bands:
        ev, secs = [], 0.0
        for a, b in runs(W["eng"] & bmask(W, lo, hi), 200):
            secs += (b - a) / FS
            rs = np.convolve(rate[a:b], ker, "same")
            dws = runs(rs < th, 20)
            for q, (p, e0) in enumerate(dws):
                snap = abs(W["theta"][a + dws[q + 1][0]] - W["theta"][a + e0 - 1]) if q + 1 < len(dws) else np.nan
                ev.append((a + p, snap))
        out[nm] = dict(secs=secs, ev=ev, n=len(ev), per_min=60.0 * len(ev) / secs if secs >= 5 else np.nan)
    return out


def split_events(W, D, key, edges, bands):
    c = cls(np.abs(W[key]), edges)
    res = {}
    for nm, lo, hi in bands:
        m = np.zeros(len(W["t"]), bool)
        for a, b in runs(W["eng"] & bmask(W, lo, hi), 200):
            m[a:b] = True
        row = {}
        for k, (cn, _, _) in enumerate(edges):
            s = float((m & (c == k)).sum() / FS)
            n = sum(1 for i, _ in D[nm]["ev"] if c[i] == k)
            row[cn] = (n, s, 60.0 * n / s if s >= 10 else np.nan)
        res[nm] = row
    return res


def seg_psd(W, m, nper=256, ch="w18"):
    P = []
    win = np.hanning(nper)
    for a, b in runs(m, nper):
        st = np.arange(a, b - nper + 1, nper // 2)
        seg = W[ch][st[:, None] + np.arange(nper)[None, :]]
        seg = seg - seg.mean(1, keepdims=True)
        p = np.abs(np.fft.rfft(seg * win, axis=1)) ** 2 / ((win ** 2).sum() * FS)
        p[:, 1:-1] *= 2
        P.append(p)
    f = np.fft.rfftfreq(nper, 1 / FS)
    return f, (np.vstack(P) if P else np.zeros((0, len(f))))


def bamp_of(f, P, lo, hi):
    sl = (f >= lo) & (f <= hi)
    return float(np.sqrt(2.0 * P.mean(0)[sl].sum() * (f[1] - f[0])))


def excess_db(f, Pm, half_hz=2.0):
    L = 10 * np.log10(np.maximum(Pm, 1e-30))
    k = int(round(half_hz / (f[1] - f[0])))
    Lp = np.pad(L, k, mode="edge")
    return L - np.median(sliding_window_view(Lp, 2 * k + 1), axis=1)


def spectral(W):
    fd, Pd = seg_psd(W, ~W["eng"])
    dis1822 = bamp_of(fd, Pd, 18, 22)
    sos_b = signal.butter(4, (18, 22), btype="bandpass", fs=FS, output="sos")
    sos_h = signal.butter(2, (1.6, 3.0), btype="bandpass", fs=FS, output="sos")
    sos_a = signal.butter(2, (0.1, 5.0), btype="bandpass", fs=FS, output="sos")
    out = {}
    for nm, lo, hi in SB + (("ALL", 0, 99),):
        me = W["eng"] & bmask(W, lo, hi)
        f, P = seg_psd(W, me)
        r = dict(eng_s=float(me.sum() / FS), nseg=int(P.shape[0]))
        if P.shape[0] >= 5:
            r["eod_1822"] = bamp_of(f, P, 18, 22) / dis1822
            ex = excess_db(f, P.mean(0))
            sl = (f >= 5) & (f <= 30)
            k = int(np.argmax(ex[sl]))
            r["line"] = (float(f[sl][k]), float(ex[sl][k]))
            r["f"], r["ex"] = f, ex
        mh = me & W["handsoff"]
        st = []
        for a, b in runs(mh, 200):
            st += list(range(a, b - 199, 50))
        if st:
            seg = W["bar"][np.array(st)[:, None] + np.arange(200)[None, :]]
            y = signal.sosfiltfilt(sos_b, seg - seg.mean(1, keepdims=True), axis=1)
            amp = np.sqrt(2) * y.std(1)
            r["pres_ub"] = float(100.0 * (amp >= 40).mean()); r["n_win"] = len(st)
        num = den = 0.0
        ns = 0
        for a, b in runs(me, 200):
            w = W["w18"][a:b] - W["w18"][a:b].mean()
            yb = signal.sosfiltfilt(sos_h, w); ya = signal.sosfiltfilt(sos_a, w)
            s_ = W["free"][a:b] & (np.abs(W["theta"][a:b]) >= 20)
            num += (yb[s_] ** 2).sum(); den += (ya[s_] ** 2).sum(); ns += int(s_.sum())
        r["hard_s"] = ns / FS
        r["hard_rms"] = float(np.sqrt(num / ns)) if ns > 100 else np.nan
        r["hard_share"] = float(num / den) if ns > 100 and den > 0 else np.nan
        out[nm] = r
    return out


def f7_by_band(W):
    with contextlib.redirect_stdout(io.StringIO()):
        import strongturn_r32_r33 as ST
    r = types.SimpleNamespace(eng=W["eng"], ang=W["theta"], wire=W["wire"], vego=W["vego"], bar=W["bar"])
    eps = ST.fixed_thr_episodes(r, thr=103.0)
    res = {}
    for nm, lo, hi in SB:
        hs = float((W["eng"] & bmask(W, lo, hi) & (np.abs(W["theta"]) >= 30)).sum() / FS)
        f7 = [e for e in eps if e["ang"] >= 30 and e["fdom"] >= 6 and lo <= e["v"] < hi]
        res[nm] = (len(f7), hs)
    return res, len(eps), len([e for e in eps if e["ang"] >= 30 and e["fdom"] >= 6])


def authority(W):
    res = {}
    for nm, lo, hi in SB:
        rows = {cn: [] for cn, _, _ in AMP}
        for a, b in runs(W["eng"] & W["free"] & bmask(W, lo, hi), 400):
            for s in range(a, b - 399, 400):
                e = s + 400
                k = int(np.searchsorted([5, 20], np.abs(W["theta_sp"][s:e]).max(), side="right"))
                rows[AMP[k][0]].append((W["thrate"][s:e].max() / max(W["sprate"][s:e].max(), 1e-3),
                                        np.abs(W["theta"][s:e] - W["theta_sp"][s:e]).max(),
                                        np.nanmean(np.abs(W["T100"][s:e]) >= 300), W["at_clip"][s:e].mean(),
                                        W["limited"][s:e].mean(), W["sprate"][s:e].max(),
                                        np.nanmax(np.abs(W["des"][s:e] - W["theta"][s:e])),
                                        np.abs(W["theta_sp"][s:e]).max()))
        res[nm] = {}
        for cn, v in rows.items():
            if not v:
                res[nm][cn] = None
                continue
            A = np.array(v)
            res[nm][cn] = dict(n=len(v), rate_ratio=float(np.median(A[:, 0])), err_p50=float(np.median(A[:, 1])),
                               err_p90=float(np.percentile(A[:, 1], 90)), rail=float(A[:, 2].mean()),
                               clip=float(A[:, 3].mean()), limited=float(A[:, 4].mean()),
                               sprate_p90=float(np.percentile(A[:, 5], 90)), des_err_p90=float(np.percentile(A[:, 6], 90)),
                               sp_max=float(A[:, 7].max()))
    return res


def main():
    F = C.load_fork()
    W = prep(C.load("r79_a1f5d2_al"), F)
    REF = {t: prep(C.load(t)) for t in ("r6c", "r39", "r71b_v294")}
    pr("M6 GOAL SCORING -- r79_a1f5d2_al (V298 A16A, fork Dom 2712e1336); refs r6c, r39 (V282), r71b_v294 (V294)")
    pr("load %.1f s" % (time.time() - T0))
    J = {"exposure": exposure(W)}

    chk = tracking(W, DRB, amp_split=False)
    pr("\nCHECK vs drive_read.txt s3 (tracking 8-15 0.989 / 15-22 0.976 / >22 0.895; hold 15-22 min 0.900):")
    for nm, r in chk.items():
        pr("   %-6s %4.0f s track %.3f  hold n %d min %.3f" % (nm, r["secs"], r["track"], r["hold"]["n"], r["hold"]["min"]))
    J["check_drb"] = {k: dict(secs=v["secs"], track=v["track"], lagcomp=v["track_lagcomp"], lag=v["lag_best_ms"],
                              dmean=v["track_demeaned"], ci=v["ci"]) for k, v in chk.items()}
    pr("   (same bands: lag-comp slope / lag ms / demeaned: " + "  ".join(
        "%s %.3f/%.0f/%.3f" % (k, v["track_lagcomp"], v["lag_best_ms"], v["track_demeaned"]) for k, v in chk.items()) + ")")

    T1 = tracking(W, SB)
    print_tracking(T1, "T1. TRACKING vs the WIRE setpoint (theta_sp = what the EPS received) -- bands x amplitude")
    T2 = tracking(W, SB, ref_key="des")
    print_tracking(T2, "T2. TRACKING vs the fork's PRE-LIMIT desired angle (carControl.actuators.steeringAngleDeg)")
    J["track_wire"] = T1
    J["track_des"] = T2
    T3 = tracking(W, DRB, ref_key="des", amp_split=False)
    pr("   (drive-read bands vs desired: " + "  ".join("%s %.3f" % (k, v["track"]) for k, v in T3.items()) + ")")

    pr("\nF. FREQUENCY RESPONSE theta/theta_sp, hands-off engaged, H1 Welch 10.24 s / 75 %, coherence gate 0.6"
       " (* = gated out). cell = |H| phase lag_ms")
    pr("   band  nwin  " + " ".join("%-17s" % ("%.1f Hz" % f) for f in FT))
    J["frf"] = {}
    for nm, lo, hi in SB + (("8-18", 8, 18), (">18", 18, 99), ("ALL>3", 3, 99)):
        R = frf(W, lo, hi)
        if R is None:
            pr("   %-6s  -  (no 10.24-s free run)" % nm)
            continue
        S = frf_summary(R)
        xl = xcorr_lag(W, lo, hi)
        cells = " ".join("%-17s" % ("%.2f %4.0f %4.0f%s" % (v["mag"], v["ph"], v["lag_ms"], "" if v["ok"] else "*"))
                         for v in S["rows"].values())
        pr("   %-6s %4d  %s" % (nm, S["n"], cells))
        pr("          -3 dB bw %s ; coherence edge %.2f Hz ; peak |H| %.2f at %.2f Hz ; xcorr lag (0.1-2 Hz) %.0f ms"
           % ("%.2f Hz" % S["bw"] if S["bw"] else "not within coherent range", S["coh_edge"], S["peak"][0], S["peak"][1], xl))
        J["frf"][nm] = dict(S, xcorr_ms=xl)
        if nm in ("ALL>3", "8-18", ">18", "3-8"):
            for cn, a_, b_ in AMP:
                R2_ = frf(W, lo, hi, amp_cls=(a_, b_))
                if R2_ is None:
                    continue
                S2 = frf_summary(R2_)
                pr("            max|sp| %-5s n %3d: " % (cn, S2["n"]) + " ".join(
                    "%.1fHz %.2f/%.0fms%s" % (f_, v["mag"], v["lag_ms"], "" if v["ok"] else "*")
                    for f_, v in S2["rows"].items() if f_ in (0.1, 0.2, 0.5, 1.0, 2.0)))
                J["frf"][nm + "|" + cn] = S2

    pr("\nD. DWELL-THEN-JUMP (nl_sim form, ref = theta_sp) and DWELLS/min @0.25 (symptom instrument)")
    dj = dwell_jump_events(W, DJB)
    pr("   CHECK dwell_jump vs drive read (5-8 0.00 8-10 2.62 10-12.5 0.96 12.5-15 2.00 15-22 1.47 >22 0.65 <5 0.59): "
       + "  ".join("%s %.2f" % (k, v["per_min"]) for k, v in dj.items()))
    sic = si_dwells(W, SIB)
    pr("   CHECK SI dwells vs drive read (0-5 4.70 5-10 1.16 10-20 4.47 >20 3.53): "
       + "  ".join("%s %.2f" % (k, v["per_min"]) for k, v in sic.items()))
    dj6 = dwell_jump_events(W, SB)
    sp_dj = split_events(W, dj6, "theta_sp", AMP, SB)
    spr_dj = split_events(W, dj6, "sprate", RATE, SB)
    pr("   dwell-then-jump per min by band (n / engaged s), split n/s=per-min by |theta_sp| and by |d sp/dt| at the event:")
    for nm, _, _ in SB:
        d = dj6[nm]
        jm = np.array([j for _, j in d["ev"]]) if d["ev"] else np.array([np.nan])
        pr("     %-6s %5.2f (%2d / %5.0f s) jump p50 %.2f | |sp| " % (nm, d["per_min"], d["n"], d["secs"], np.nanmedian(jm))
           + "  ".join("%s %d/%.0f=%.2f" % (k, *v) for k, v in sp_dj[nm].items()) + " | rate "
           + "  ".join("%s %d/%.0f=%.2f" % (k, *v) for k, v in spr_dj[nm].items()))
    J["dwell_jump"] = {k: dict(n=v["n"], secs=v["secs"], per_min=v["per_min"]) for k, v in dj6.items()}
    J["dwell_jump_amp"] = sp_dj
    J["dwell_jump_rate"] = spr_dj
    pr("   DWELLS/min @0.25 deg/s by band [per-min in |theta| <5 / 5-20 / >20 over each class's own engaged time]:")
    J["dwells"] = {}
    for tag, X in [("r79", W)] + list(REF.items()):
        sd = si_dwells(X, SB)
        sp_ = split_events(X, sd, "theta", AMP, SB)
        J["dwells"][tag] = {k: dict(per_min=v["per_min"], secs=v["secs"], amp=sp_[k],
                                    snap_p50=float(np.nanmedian([s for _, s in v["ev"]])) if v["ev"] else np.nan)
                            for k, v in sd.items()}
        pr("     %-9s " % tag + " | ".join("%s %.2f [%s]" % (k, v["per_min"], " ".join("%.1f" % sp_[k][c][2]
                                                                                    for c in ("<5", "5-20", ">20")))
                                          for k, v in sd.items()))
        pr("               engaged s: " + "  ".join("%s %.0f [%s]" % (k, v["secs"], " ".join("%.0f" % sp_[k][c][1] for c in ("<5", "5-20", ">20"))) for k, v in sd.items()))

    pr("\nS. RING / LINES / 18-22 Hz / HARD-TURN 1.6-3 Hz (w18 deg/s), per band")
    J["spec"] = {}
    SPEC = {}
    for tag, X in [("r79", W)] + list(REF.items()):
        S = spectral(X)
        SPEC[tag] = S
        J["spec"][tag] = {k: {kk: vv for kk, vv in v.items() if kk not in ("f", "ex")} for k, v in S.items()}
        pr("   %s" % tag)
        for nm, r in S.items():
            pr("     %-5s eng %6.1f s  eng/dis 18-22 %s  max 5-30 excess %s  presence-UB %s  hard-turn(|th|>=20,free) %5.1f s rms %s share %s"
               % (nm, r["eng_s"], "%.2f" % r["eod_1822"] if "eod_1822" in r else "  - ",
                  "%4.1f dB @%4.1f Hz" % (r["line"][1], r["line"][0]) if "line" in r else "      -        ",
                  "%.2f %%" % r["pres_ub"] if "pres_ub" in r else "  -  ",
                  r["hard_s"], "%.2f" % r["hard_rms"] if np.isfinite(r["hard_rms"]) else " - ",
                  "%.2f" % r["hard_share"] if np.isfinite(r["hard_share"]) else " - "))
    pr("   NEW-LINE TEST per band (r79 excess >= 4 dB, and every ref < 2 dB within +-0.75 Hz):")
    J["newline"] = {}
    for nm, _, _ in SB + (("ALL", 0, 99),):
        r = SPEC["r79"][nm]
        if "ex" not in r:
            continue
        f, ex = r["f"], r["ex"]
        sl = (f >= 5) & (f <= 30) & (ex >= 4.0)
        new = []
        for fk in f[sl]:
            if all(("ex" in SPEC[t][nm]) and (SPEC[t][nm]["ex"][np.abs(SPEC[t][nm]["f"] - fk) <= 0.75].max() < 2.0)
                   for t in REF):
                new.append(float(fk))
        J["newline"][nm] = new
        pr("     %-5s lines >= 4 dB: %s ; NEW vs all refs: %s" % (nm, [round(float(x), 2) for x in f[sl]] or "none", new or "none"))
    f7, n_eps, n_f7 = f7_by_band(W)
    pr("   F7 (ST.fixed_thr_episodes thr 103, |angle| >= 30, fdom >= 6): episodes %d, F7 %d ; per band (n/high-angle s): %s"
       % (n_eps, n_f7, "  ".join("%s %d/%.0f" % (k, *v) for k, v in f7.items())))
    J["f7"] = f7

    pr("\nA. LARGE vs SMALL: 4-s free windows classed by max|theta_sp|: rate ratio = peak|dtheta/dt| / peak|dsp/dt| (2 Hz LPF);"
       " |theta - sp| p50/p90; tap at rail (|T| >= 300 LSB); fork error clip active; desired != wire sp (> 0.5 deg);"
       " sp-rate p90; |desired - theta| p90")
    A = authority(W)
    J["authority"] = A
    for nm, row in A.items():
        for cn, v in row.items():
            if v is None:
                continue
            pr("   %-6s %-5s n %3d  rate-ratio %.2f  err %.2f/%.2f  rail %4.1f%%  clip %4.1f%%  limited %4.1f%%  sp-rate p90 %5.1f  des-err p90 %5.1f  max|sp| %5.1f"
               % (nm, cn, v["n"], v["rate_ratio"], v["err_p50"], v["err_p90"], 100 * v["rail"], 100 * v["clip"],
                  100 * v["limited"], v["sprate_p90"], v["des_err_p90"], v["sp_max"]))

    pr("\nX. THE >22 m/s TRACKING FAIL -- decomposition (drive-read bands)")
    J["x22"] = {}
    for nm, lo, hi in (("15-22", 15, 22), (">22", 22, 99)):
        rr = goal_runs(W, lo, hi)
        m = np.zeros(len(W["t"]), bool)
        for a, b in rr:
            m[a + 400:b] = True
        e = W["theta"] - W["theta_sp"]
        pr("   %-6s runs %d %s s  sp p5..p95 %.2f..%.2f  sp sd %.2f  |err| mean %.2f p95 %.2f  mean err %+.2f  clip %.1f%%  "
           "limited %.1f%%  tap rail %.1f%%  |tap| p95 %.0f LSB"
           % (nm, len(rr), [int((b - a) / FS) for a, b in rr], np.percentile(W["theta_sp"][m], 5),
              np.percentile(W["theta_sp"][m], 95), np.std(W["theta_sp"][m]), np.abs(e[m]).mean(),
              np.percentile(np.abs(e[m]), 95), e[m].mean(), 100 * W["at_clip"][m].mean(), 100 * W["limited"][m].mean(),
              100 * np.nanmean(np.abs(W["T100"][m]) >= 300), np.nanpercentile(np.abs(W["T100"][m]), 95)))
        sl_r, X_, Y_ = [], [], []
        for a, b in rr:
            x = signal.sosfiltfilt(SOS05, W["theta_sp"][a:b])[400:]; y = signal.sosfiltfilt(SOS05, W["theta"][a:b])[400:]
            X_.append(x); Y_.append(y)
            s_, i_, r_ = ols(x, y)
            sl_r.append("%.3f(%.0fs sd %.2f R2 %.2f ic %+.2f)" % (s_, len(x) / FS, x.std(), r_, i_))
        pr("          per-run slopes: " + "  ".join(sl_r))
        Xa, Ya = np.concatenate(X_), np.concatenate(Y_)
        s_f = ols(Xa, Ya)[0]; s_rev = ols(Ya, Xa)[0]
        # frames NOT at the error clip only
        mk = np.concatenate([~W["at_clip"][a + 400:b] for a, b in rr])
        s_nc = ols(Xa[mk], Ya[mk])[0]
        pr("          forward %.3f ; 1/reverse %.3f (errors-in-variables bracket) ; excluding clip-active frames %.3f"
           % (s_f, 1 / s_rev, s_nc))
        J["x22"][nm] = dict(fwd=s_f, inv_rev=1 / s_rev, no_clip=s_nc, runs=[int((b - a) / FS) for a, b in rr])
    J["runtime_s"] = time.time() - T0
    pr("\nwall time %.1f s" % J["runtime_s"])
    (OUT / "m6_goal_scoring.txt").write_text("\n".join(LINES), encoding="utf-8")

    def js(x):
        if isinstance(x, (np.floating, np.integer)):
            return x.item()
        if isinstance(x, np.ndarray):
            return x.tolist()
        if isinstance(x, np.bool_):
            return bool(x)
        return str(x)
    (OUT / "m6_goal_scoring.json").write_text(json.dumps(J, default=js, indent=0))


if __name__ == "__main__":
    main()
