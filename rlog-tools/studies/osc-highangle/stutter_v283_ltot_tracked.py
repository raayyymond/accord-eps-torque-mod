# -*- coding: utf-8 -*-
"""studies/osc-highangle/stutter_v283_ltot_tracked.py -- |L_tot| at f0 from an f0-TRACKED, PER-EPISODE
estimator, replacing the pooled half-power width of stutter_v283_ltot_measured.py (which two good-faith
implementations disagreed on by 4x in Q).

WHY THE POOLED SPECTRUM FAILS: f0 wanders 7.2-8.4 Hz across and within routes.  Pooling runs of different
f0 into one Welch broadens the peak, so the measured width is the WANDER, not the mode's bandwidth, and
the answer depends on the peak-search band and nperseg -- exactly the two knobs that moved the orchestrator's
numbers.

WHY A PER-EPISODE SPECTRUM ALSO FAILS: a 2 s episode gives 0.5 Hz resolution and the bandwidth being
measured is ~0.6 Hz.  The spectrum cannot resolve it.

THE ESTIMATOR USED HERE -- the complex ACF, computed INSIDE each episode:
  for a narrowband mode, rho(tau) = <z(t) z*(t+tau)> / <|z|^2> = exp(-alpha|tau|) exp(j 2 pi f0 tau)
  so |rho(tau)| decays at the mode's own rate with NO frequency resolution limit and NO sensitivity to
  where the episode sits in frequency -- the wander is removed by construction because each ACF is
  computed within one episode.  Then, for a lightly damped second-order mode,
      alpha = zeta * 2 pi f0 ,  Q = 1/(2 zeta) = pi f0 / alpha ,  Ms ~ Q ,  |1 - L(j f0)| ~ 1/Q.
  The SIGN of alpha is itself a side-discriminator independent of F7: a decaying ring has |L| < 1.

Sections
  T1  per-episode f0 (refined FFT peak on that episode alone) and within-episode drift; the r36 8.4 Hz question
  T2  per-episode alpha and Q from the complex ACF; per-route median with a bootstrap CI over episodes
  T3  |L_tot(248)| per route and pooled, WITH an error bar, and the qualifying-seconds statement
  T4  SENSITIVITY to the two knobs that broke the pooled estimate: the peak-selection band, and the
      analysis-window/lag trade; plus the pooled-Welch number recomputed for comparison
  T5  the gate arithmetic redone on the tracked number

Run: python stutter_v283_ltot_tracked.py     Subagent stutter283, 2026-09-03.
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stutter_v283 as SV  # noqa: E402
import strongturn_r32_r33 as ST  # noqa: E402

V = SV.V
FS = SV.FS
CPD = SV.CPD

STOCK = ("r32", "r33", "r34")          # stock Kp LERP; F7 present -> |L| > 1
FLAT = ("r35", "r36", "r37", "r38")    # flat 248; F7 = 0.00 -> |L| < 1
RING_DOSE = 1.0544                     # A9.3 ratio for flat 341 and for M8*, identical to 3 dp


def episodes_for(r, tag):
    """The ring episodes, per route, by the SAME detector used throughout: fixed threshold, |ang| >= 30,
       fdom >= 6.  103 on the stock-Kp routes (where the cycle is above the floor), 60 on the flat-248
       routes (where it is a sub-detector residual)."""
    thr = 103 if tag in STOCK else 60
    return [e for e in ST.fixed_thr_episodes(r, thr=thr) if e["ang"] >= 30 and e["fdom"] >= 6]


def refine_f0(x, lo, hi, fs=FS):
    """Zero-padded FFT peak of one episode, parabolic-interpolated."""
    n = len(x)
    nfft = max(8192, 1 << int(np.ceil(np.log2(n * 16))))
    w = np.hanning(n)
    X = np.abs(np.fft.rfft((x - x.mean()) * w, nfft))
    f = np.fft.rfftfreq(nfft, 1.0 / fs)
    m = (f >= lo) & (f <= hi)
    j = np.flatnonzero(m)[np.argmax(X[m])]
    if 0 < j < len(X) - 1:
        a, b, c = X[j - 1], X[j], X[j + 1]
        d = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
        return float(f[j] + d * (f[1] - f[0]))
    return float(f[j])


def acf_alpha(x, f0, fs=FS, half_bw=2.0, max_lag_s=0.6):
    """alpha from the COMPLEX ACF of the analytic signal, computed inside this episode only.
       Returns (alpha, Q, n_lags, fit_r2).  alpha > 0 = decaying."""
    lo, hi = max(f0 - half_bw, 1.0), min(f0 + half_bw, 45.0)
    sos = signal.butter(3, [lo, hi], btype="bandpass", fs=fs, output="sos")
    z = signal.hilbert(signal.sosfiltfilt(sos, x - x.mean()))
    n = len(z)
    L = int(min(max_lag_s * fs, n // 3))
    if L < 8:
        return np.nan, np.nan, 0, np.nan
    lags = np.arange(1, L + 1)
    p0 = float(np.mean(np.abs(z) ** 2))
    rho = np.array([np.abs(np.mean(z[:n - k] * np.conj(z[k:]))) / p0 for k in lags])
    good = rho > 0.10                                    # fit only where the ACF is above the noise floor
    if good.sum() < 6:
        return np.nan, np.nan, int(good.sum()), np.nan
    t = lags[good] / fs
    y = np.log(rho[good])
    A = np.vstack([t, np.ones_like(t)]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    alpha = -float(coef[0])
    yy = A @ coef
    r2 = 1.0 - float(np.sum((y - yy) ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-12))
    Q = np.pi * f0 / alpha if alpha > 0 else np.nan
    return alpha, Q, int(good.sum()), r2


def boot_ci(vals, n=4000, q=(5, 95), seed=0):
    v = np.asarray([x for x in vals if np.isfinite(x)], float)
    if len(v) < 2:
        return (np.nan, np.nan, len(v))
    rng = np.random.default_rng(seed)
    m = [np.median(rng.choice(v, len(v), replace=True)) for _ in range(n)]
    return (float(np.percentile(m, q[0])), float(np.percentile(m, q[1])), len(v))


def main():
    L = []

    def pr(s=""):
        print(s, flush=True)
        L.append(s)

    routes = {t: V.Route(t) for t in STOCK + FLAT}

    pr("=" * 172)
    pr("|L_tot| AT f0 FROM AN f0-TRACKED, PER-EPISODE ESTIMATOR.  Subagent stutter283, 2026-09-03")
    pr("  Estimator: complex ACF inside each episode -- |rho(tau)| = exp(-alpha|tau|); alpha = zeta*2*pi*f0;")
    pr("  Q = pi*f0/alpha; Ms ~ Q; |1 - L(j f0)| ~ 1/Q.  No frequency-resolution limit, and between-episode")
    pr("  wander cannot broaden it because every ACF is computed within one episode.")
    pr("  SIDE: sign(alpha) is an independent discriminator -- a DECAYING ring has |L| < 1.  F7 is the cross-check, not the input.")
    pr("=" * 172)

    # -------------------------------------------------------------------------------------------- T1
    pr("\nT1 -- PER-EPISODE f0 (refined FFT peak on that episode alone, search band 5.0-10.0 Hz) and the r36 question.")
    pr("   %-5s %-9s %6s | %s" % ("route", "build", "eps", "per-episode f0, Hz"))
    EPS = {}
    for tag in STOCK + FLAT:
        r = routes[tag]
        eps = episodes_for(r, tag)
        rows = []
        for e in eps:
            a, b = int(e["t0"] * FS), int((e["t0"] + e["dur"]) * FS)
            x = r.wire[a:b]
            if len(x) < 80:
                continue
            f0 = refine_f0(x, 5.0, 10.0)
            rows.append(dict(t0=e["t0"], dur=e["dur"], f0=f0, a=a, b=b))
        EPS[tag] = rows
        pr("   %-5s %-9s %6d | %s" % (tag, "stock Kp" if tag in STOCK else "flat 248", len(rows),
                                      " ".join("%.2f" % x["f0"] for x in rows) or "-"))
    pr("\n   r36 RECONCILIATION: the orchestrator's pooled Welch put r36's peak at 8.43 Hz, mine at 7.71.")
    for tag in ("r35", "r36"):
        r = routes[tag]
        m = r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10)
        runs = V.runs(m, 256)
        f, P = signal.welch(r.wire[runs] - r.wire[runs].mean(), fs=FS, nperseg=1024)
        sel = (f >= 5.0) & (f <= 10.0)
        top = np.argsort(P[sel])[::-1][:6]
        pr("   %s pooled-Welch top 6 bins in 5-10 Hz: %s" % (tag, "  ".join("%.2f Hz (P %.0f)" % (f[sel][j], P[sel][j]) for j in top)))
    pr("   => if r36's pooled peak is a DIFFERENT bin from its per-episode f0 values above, the pooled number was")
    pr("      measuring a blend of episodes at different frequencies, which is exactly the failure this section removes.")

    # -------------------------------------------------------------------------------------------- T2/T3
    pr("\nT2/T3 -- PER-EPISODE alpha and Q, per-route median with a bootstrap 90 %% CI over episodes, and |L_tot(248)|.")
    pr("   QUALIFYING EPISODE: >= 0.8 s, >= 6 usable ACF lags, ACF fit r2 >= 0.80, alpha finite.")
    pr("   %-5s %-9s %7s %5s %5s | %-22s | %-22s | %-26s" % (
        "route", "build", "qual s", "eps", "qual", "f0 median (p10-p90)", "Q median [90% CI]", "|L_tot| = 1 -+ 1/Q  [90% CI]"))
    RES = {}
    for tag in STOCK + FLAT:
        r = routes[tag]
        qs, Qs, f0s, als = 0.0, [], [], []
        for x in EPS[tag]:
            if x["dur"] < 0.8:
                continue
            al, Q, nl, r2 = acf_alpha(r.wire[x["a"]:x["b"]], x["f0"])
            x["alpha"], x["Q"], x["r2"], x["nlag"] = al, Q, r2, nl
            if not np.isfinite(al) or not np.isfinite(r2) or r2 < 0.80 or nl < 6:
                continue
            qs += x["dur"]
            als.append(al)
            f0s.append(x["f0"])
            if np.isfinite(Q):
                Qs.append(Q)
        side = +1 if tag in STOCK else -1                        # |L| = 1 + 1/Q above, 1 - 1/Q below
        if len(Qs) >= 2:
            qlo, qhi, nq = boot_ci(Qs)
            Qm = float(np.median(Qs))
            Lm = 1 + side * 1.0 / Qm
            Llo, Lhi = 1 + side * 1.0 / qhi, 1 + side * 1.0 / qlo
            RES[tag] = dict(Q=Qm, Qlo=qlo, Qhi=qhi, L=Lm, Llo=min(Llo, Lhi), Lhi=max(Llo, Lhi), n=nq, s=qs, Qs=Qs)
            pr("   %-5s %-9s %7.1f %5d %5d | %5.2f (%4.2f-%4.2f)      | %5.1f [%5.1f-%5.1f]     | %5.3f [%5.3f-%5.3f]" % (
                tag, "stock Kp" if tag in STOCK else "flat 248", qs, len(EPS[tag]), nq,
                np.median(f0s), np.percentile(f0s, 10), np.percentile(f0s, 90),
                Qm, qlo, qhi, Lm, min(Llo, Lhi), max(Llo, Lhi)))
        else:
            pr("   %-5s %-9s %7.1f %5d %5d | -- TOO FEW QUALIFYING EPISODES TO CARRY AN ESTIMATE --" % (
                tag, "stock Kp" if tag in STOCK else "flat 248", qs, len(EPS[tag]), len(Qs)))
            RES[tag] = None
    for grp, nm in ((STOCK, "STOCK Kp (cycle present)"), (FLAT, "FLAT 248 (cycle absent)")):
        pool = [q for t in grp if RES.get(t) for q in RES[t]["Qs"]]
        if len(pool) < 2:
            pr("   POOLED %-26s: too few" % nm)
            continue
        qlo, qhi, nq = boot_ci(pool)
        Qm = float(np.median(pool))
        side = +1 if grp is STOCK else -1
        pr("   POOLED %-26s n %2d episodes: Q %5.1f [%5.1f-%5.1f]  =>  |L_tot| %5.3f [%5.3f-%5.3f]" % (
            nm, nq, Qm, qlo, qhi, 1 + side / Qm, min(1 + side / qhi, 1 + side / qlo), max(1 + side / qhi, 1 + side / qlo)))

    # -------------------------------------------------------------------------------------------- T4
    pr("\nT4 -- SENSITIVITY to the two knobs that broke the pooled estimate.")
    pr("   (a) PEAK-SELECTION BAND for the per-episode f0, and (b) the ACF max-lag (the window/resolution trade).")
    pr("   Reported as the pooled FLAT-248 |L_tot| under each setting.")
    for lo, hi in ((5.0, 10.0), (6.0, 8.5), (5.5, 9.5), (6.0, 10.0)):
        for ml in (0.4, 0.6, 0.9):
            pool = []
            for tag in FLAT:
                r = routes[tag]
                for e in episodes_for(r, tag):
                    a, b = int(e["t0"] * FS), int((e["t0"] + e["dur"]) * FS)
                    if b - a < 80 or e["dur"] < 0.8:
                        continue
                    f0 = refine_f0(r.wire[a:b], lo, hi)
                    al, Q, nl, r2 = acf_alpha(r.wire[a:b], f0, max_lag_s=ml)
                    if np.isfinite(Q) and np.isfinite(r2) and r2 >= 0.80 and nl >= 6:
                        pool.append(Q)
            if len(pool) >= 2:
                qlo, qhi, nq = boot_ci(pool)
                Qm = float(np.median(pool))
                pr("      band %.1f-%.1f Hz, max lag %.1f s: n %2d  Q %5.1f [%5.1f-%5.1f]  |L_tot| %5.3f [%5.3f-%5.3f]" % (
                    lo, hi, ml, nq, Qm, qlo, qhi, 1 - 1 / Qm, 1 - 1 / qlo, 1 - 1 / qhi))
            else:
                pr("      band %.1f-%.1f Hz, max lag %.1f s: n %2d -- too few" % (lo, hi, ml, len(pool)))
    pr("\n   (c) THE POOLED-WELCH NUMBER recomputed at several nperseg, for the comparison that failed to replicate:")
    for nps in (256, 512, 1024, 2048):
        cells = []
        for tag in FLAT:
            r = routes[tag]
            m = r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10)
            runs = V.runs(m, min(nps, 512))
            if runs.sum() < 2 * nps:
                cells.append("%s --" % tag)
                continue
            f, P = signal.welch(r.wire[runs] - r.wire[runs].mean(), fs=FS, nperseg=nps)
            b = (f >= 5.0) & (f <= 10.0)
            j = np.flatnonzero(b)[np.argmax(P[b])]
            base = np.median(P[(f >= 2) & (f <= 25)])
            half = base + (P[j] - base) / 2.0
            a1 = j
            while a1 > 1 and P[a1] > half:
                a1 -= 1
            b1 = j
            while b1 < len(f) - 2 and P[b1] > half:
                b1 += 1
            bw = f[b1] - f[a1]
            cells.append("%s f0 %.2f Q %5.1f" % (tag, f[j], f[j] / bw if bw > 0 else np.nan))
        pr("      nperseg %4d (%.3f Hz bins): %s" % (nps, FS / nps, " | ".join(cells)))

    # -------------------------------------------------------------------------------------------- T5
    pr("\nT5 -- THE GATE, redone on the tracked number.  Ring ratio at M8*'s and flat 341's dose = %.4f (A9.3, identical to 3 dp)." % RING_DOSE)
    pool = [q for t in FLAT if RES.get(t) for q in RES[t]["Qs"]]
    if len(pool) >= 2:
        qlo, qhi, _ = boot_ci(pool)
        Qm = float(np.median(pool))
        for nm, Q in (("median", Qm), ("CI low  (worst case: least damped)", qhi), ("CI high (best case: most damped)", qlo)):
            Lt = 1 - 1 / Q
            pr("      |L_tot(248)| %-36s = %5.3f  ->  after the raise: %5.3f  %s" % (
                nm, Lt, Lt * RING_DOSE, "PASS (< 1.00)" if Lt * RING_DOSE < 1.0 else "*** FAIL (>= 1.00) ***"))
        pr("      headroom at flat 248 = %.1f-%.1f %% ; the raise spends %.1f %%" % (
            100 * (1 - (1 - 1 / qlo)), 100 * (1 - (1 - 1 / qhi)), 100 * (RING_DOSE - 1)))

    out = os.path.join(HERE, "_scratch", "stutter_v283_ltot_tracked.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
