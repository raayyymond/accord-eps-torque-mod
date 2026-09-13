# -*- coding: utf-8 -*-
"""openloop_zeta.py -- the three damping estimators and their POSITIVE AND NEGATIVE CONTROLS.
Subagent `openloop`, 2026-09-13.  ANALYSIS ONLY.

Three estimators, deliberately different in what they assume:
  E1 FREE-DECAY   design290d_anchors.decay's recipe: bandpass f0 +- bw, Hilbert envelope, find envelope
                  maxima above a high percentile, fit log(env) over [wlo, whi] s after each peak,
                  zeta = -slope / (2 pi f0).  Assumes the post-peak envelope is a free decay.
  E2 COHERENCE    fvlc_parts2.part2c's recipe: demodulate at f0, pool the complex-envelope
                  autocorrelation |rho(tau)| over runs, fit log|rho| vs tau, zeta = 1/(tau_c w0).
                  For a noise-rung pole |rho(tau)| = exp(-zeta w0 tau) EXACTLY.
  E3 LINE WIDTH   NOT in the record: fit the 2nd-order Lorentzian |H|^2 = A/((f^2-f0^2)^2+(2 z f0 f)^2)
                  plus a local floor to the pooled Welch PSD.  Independent of any envelope or filter
                  bandwidth -- which is exactly the artefact E1 and E2 are exposed to.

🛑 THE ARTEFACT THAT MAKES THIS WORTH CONTROLLING.  E1 and E2 both band-limit first, and a bandpass of
half-width HB imposes its OWN coherence floor of about 1/(pi*2*HB).  At HB = 3 Hz that is 0.053 s, i.e.
an APPARENT zeta of 1/(0.053 * 2 pi * 20) = 0.15 on a signal with NO MODE IN IT AT ALL.  0.15 is inside
the range that would be read as "the loop was doing all the de-damping".  So the NEGATIVE control --
filtered noise, no mode -- is not optional here; it is the number that decides whether a high
disengaged zeta means anything.

Run: python openloop_zeta.py controls
"""
import os
import sys

import numpy as np
from scipy import optimize, signal, stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import openloop_lib as L                       # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def save(name):
    with open(os.path.join(L.SCR, name), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")


# ==============================================================================================
# SYNTHESIS -- a 2nd-order mode of KNOWN zeta, rung by white noise, at 100 Hz
# ==============================================================================================
def resonator(zeta, f0, n, seed=0, fs=FS):
    """white-noise-driven discrete 2nd-order pole.  |rho(tau)| = exp(-zeta w0 tau) by construction;
    PSD is the Lorentzian A/((f^2-f0^2)^2+(2 zeta f0 f)^2)."""
    rng = np.random.default_rng(seed)
    w0 = 2 * np.pi * f0
    r = np.exp(-zeta * w0 / fs)
    th = w0 * np.sqrt(max(1.0 - zeta ** 2, 0.0)) / fs
    b = [1.0]
    a = [1.0, -2 * r * np.cos(th), r ** 2]
    y = signal.lfilter(b, a, rng.standard_normal(n + 2000))[2000:]
    return y / np.std(y)


def synth(zeta, f0, n, snr_db, seed=0, lsb=0.0, fs=FS, noise_lo=4.0, noise_hi=45.0):
    """mode + band-limited broadband noise at a given in-band SNR, optionally quantised.

    SNR is defined the way the wire defines it: mode power in f0 +- 2 Hz over noise power in the same
    f0 +- 2 Hz band -- so snr_db = 0 means the line is exactly level with the floor under it.
    """
    m = resonator(zeta, f0, n, seed, fs)
    rng = np.random.default_rng(seed + 9999)
    nz = signal.sosfiltfilt(signal.butter(4, (noise_lo, noise_hi), btype="band", fs=fs, output="sos"),
                            rng.standard_normal(n))
    pm = np.var(L.bp(m, f0 - 2, f0 + 2, fs))
    pn = np.var(L.bp(nz, f0 - 2, f0 + 2, fs))
    nz *= np.sqrt(pm / max(pn, 1e-30) / (10 ** (snr_db / 10.0)))
    x = m + nz
    if lsb > 0:
        x = np.round(x / lsb) * lsb
    return x


# ==============================================================================================
# E1 -- FREE DECAY  (design290d_anchors.decay, verbatim in substance)
# ==============================================================================================
def zeta_decay(runs_, f0, bw=3.0, wlo=0.06, whi=0.25, pct=90.0, fs=FS, seed=0):
    lo, hi = max(1.0, f0 - bw), min(0.98 * fs / 2, f0 + bw)
    sos = signal.butter(4, [lo, hi], btype="band", fs=fs, output="sos")
    envs = []
    for x in runs_:
        if len(x) < 200:
            continue
        envs.append(np.abs(signal.hilbert(signal.sosfiltfilt(sos, signal.detrend(x)))))
    if not envs:
        return dict(z=np.nan, lo=np.nan, hi=np.nan, n=0, grow=np.nan)
    thr = np.percentile(np.concatenate(envs), pct)
    n0, n1 = int(wlo * fs), int(whi * fs)
    zs, grow, n = [], 0, 0
    for env in envs:
        pk, _ = signal.find_peaks(env, height=thr, distance=int(0.15 * fs))
        for p in pk:
            if p + n1 >= len(env):
                continue
            seg = env[p + n0:p + n1]
            if seg.min() <= 0:
                continue
            tt = np.arange(len(seg)) / fs
            s = np.polyfit(tt, np.log(seg), 1)[0]
            n += 1
            if s >= 0:
                grow += 1
                continue
            zs.append(-s / (2 * np.pi * f0))
    if len(zs) < 3:
        return dict(z=np.nan, lo=np.nan, hi=np.nan, n=n, grow=grow / max(n, 1))
    m, a, b = L.boot_ci(np.array(zs), np.median, 2000, seed)
    return dict(z=m, lo=a, hi=b, n=n, nfit=len(zs), grow=grow / max(n, 1))


# ==============================================================================================
# E2 -- COHERENCE TIME  (fvlc_parts2.part2c, verbatim in substance)
# ==============================================================================================
def zeta_coh(runs_, f0, HB=3.0, taumax=0.60, taumin=0.02, fs=FS, nboot=0, seed=0):
    lags = np.arange(int(taumin * fs), int(taumax * fs) + 1)
    per = []                                   # per-run (re, im, pow) so a bootstrap over runs is possible
    for x in runs_:
        if len(x) < len(lags) + 40:
            continue
        z = signal.hilbert(L.bp(np.asarray(x, float), f0 - HB, f0 + HB, fs))
        tt = np.arange(len(z)) / fs
        zd = z * np.exp(-2j * np.pi * f0 * tt)
        re = np.array([np.real(np.vdot(zd[:-k], zd[k:])) for k in lags])
        im = np.array([np.imag(np.vdot(zd[:-k], zd[k:])) for k in lags])
        p0 = float(np.mean(np.abs(zd) ** 2)) * (len(zd) - 1)
        per.append((re, im, p0))
    if len(per) < 2:
        return dict(z=np.nan, tau=np.nan, lo=np.nan, hi=np.nan, n=len(per))

    def fit(sel):
        re = np.sum([per[i][0] for i in sel], axis=0)
        im = np.sum([per[i][1] for i in sel], axis=0)
        p0 = np.sum([per[i][2] for i in sel])
        rho = np.hypot(re, im) / max(p0, 1e-30)
        rho = np.clip(rho / max(rho[0], 1e-30), 1e-6, 1.0)
        sl = stats.linregress(lags / fs, np.log(rho))
        return (-1.0 / sl.slope) if sl.slope < 0 else np.inf

    tau = fit(range(len(per)))
    z = 1.0 / (tau * 2 * np.pi * f0) if np.isfinite(tau) and tau > 0 else np.nan
    lo = hi = np.nan
    if nboot:
        rng = np.random.default_rng(seed)
        bs = []
        for _ in range(nboot):
            t = fit(rng.integers(0, len(per), len(per)))
            if np.isfinite(t) and t > 0:
                bs.append(1.0 / (t * 2 * np.pi * f0))
        if len(bs) > 10:
            lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    return dict(z=z, tau=tau, lo=lo, hi=hi, n=len(per))


# ==============================================================================================
# E3 -- LORENTZIAN LINE WIDTH  (new here; no envelope, no bandpass)
# ==============================================================================================
def _lor(f, A, f0, z, C):
    return A / ((f ** 2 - f0 ** 2) ** 2 + (2 * z * f0 * f) ** 2) + C


def pooled_psd(runs_, nperseg, fs=FS):
    P, W = None, 0.0
    f = None
    for x in runs_:
        if len(x) < nperseg:
            continue
        f, p = signal.welch(signal.detrend(np.asarray(x, float)), fs, nperseg=nperseg,
                            noverlap=nperseg // 2, window="hann")
        P = p * len(x) if P is None else P + p * len(x)
        W += len(x)
    if P is None:
        return None, None, 0
    return f, P / W, W


def zeta_width(runs_, f0_guess, nperseg=1024, half=6.0, fs=FS, nboot=0, seed=0, flo=None, fhi=None):
    f, P, W = pooled_psd(runs_, nperseg, fs)
    if f is None:
        return dict(z=np.nan, f0=np.nan, lo=np.nan, hi=np.nan, n=0, r2=np.nan)
    lo = flo if flo is not None else f0_guess - half
    hi = fhi if fhi is not None else f0_guess + half
    m = (f >= lo) & (f <= hi) & (P > 0)
    if m.sum() < 12:
        return dict(z=np.nan, f0=np.nan, lo=np.nan, hi=np.nan, n=int(m.sum()), r2=np.nan)
    ff, PP = f[m], P[m]

    def resid(th):
        A, f0, z, C = np.exp(th[0]), th[1], np.exp(th[2]), np.exp(th[3])
        return np.log(_lor(ff, A, f0, z, C)) - np.log(PP)

    j = int(np.argmax(PP))
    best, bres = None, np.inf
    for z0 in (0.005, 0.02, 0.05, 0.15, 0.4):
        A0 = (PP[j] - np.median(PP)) * ((2 * z0 * ff[j] ** 2) ** 2)
        th0 = [np.log(max(A0, 1e-30)), ff[j], np.log(z0), np.log(max(np.median(PP), 1e-30))]
        try:
            r = optimize.least_squares(resid, th0, method="lm", max_nfev=6000)
        except Exception:
            continue
        if r.cost < bres:
            bres, best = r.cost, r
    if best is None:
        return dict(z=np.nan, f0=np.nan, lo=np.nan, hi=np.nan, n=int(m.sum()), r2=np.nan)
    z = float(np.exp(best.x[2]))
    f0 = float(best.x[1])
    ss = 1.0 - np.sum(best.fun ** 2) / np.sum((np.log(PP) - np.log(PP).mean()) ** 2)
    out = dict(z=z, f0=f0, lo=np.nan, hi=np.nan, n=int(m.sum()), r2=float(ss),
               nseg=len(runs_), secs=W / fs)
    if nboot and len(runs_) > 3:
        rng = np.random.default_rng(seed)
        bs = []
        for _ in range(nboot):
            sel = rng.integers(0, len(runs_), len(runs_))
            rr = zeta_width([runs_[i] for i in sel], f0_guess, nperseg, half, fs, 0, 0, flo, fhi)
            if np.isfinite(rr["z"]):
                bs.append(rr["z"])
        if len(bs) > 10:
            out["lo"], out["hi"] = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    return out


# ==============================================================================================
def chop(x, seclen, fs=FS):
    n = int(seclen * fs)
    return [x[i:i + n] for i in range(0, len(x) - n + 1, n)]


def controls():
    pr("=" * 120)
    pr("POSITIVE AND NEGATIVE CONTROLS FOR THE THREE DAMPING ESTIMATORS")
    pr("=" * 120)
    pr("Synthetic 2nd-order mode at f0 = 20.00 Hz rung by white noise, plus band-limited broadband")
    pr("noise at a stated in-band SNR, sampled at 100 Hz.  Every estimator sees the SAME realisation.")
    pr("E1 = Hilbert free-decay (design290d_anchors recipe, bw +-3 Hz)")
    pr("E2 = coherence time     (fvlc_parts2 part2c recipe, HB 3 Hz, tau 0.02-0.60 s)")
    pr("E3 = Lorentzian PSD fit (new; nperseg as stated, +-6 Hz fit window)")
    pr()
    F0 = 20.0
    ZS = (0.005, 0.010, 0.020, 0.030, 0.050, 0.100, 0.200, 0.300)

    for lab, secs, seclen, nperseg, snr in (
            ("A  LONG record, high SNR   (the ENGAGED stratum's situation)", 600.0, 20.0, 1024, 10.0),
            ("B  LONG record, low SNR    (SNR 0 dB: line level with its own floor)", 600.0, 20.0, 1024, 0.0),
            ("C  SHORT 2 s pieces, 200 s total, low SNR  (the DISENGAGED stratum's situation)",
             200.0, 2.0, 200, 0.0),
            ("D  SHORT 2 s pieces, 60 s total, low SNR   (the WORST disengaged case)", 60.0, 2.0, 200, 0.0)):
        pr("-" * 120)
        pr(lab)
        pr("   %-8s | %-26s | %-26s | %-30s" % ("true z", "E1 free-decay", "E2 coherence", "E3 line width"))
        for zt in ZS:
            x = synth(zt, F0, int(secs * FS), snr, seed=int(zt * 1e5))
            rr = chop(x, seclen)
            e1 = zeta_decay(rr, F0) if seclen >= 2.0 else dict(z=np.nan)
            e2 = zeta_coh(rr, F0, taumax=min(0.60, seclen * 0.4))
            e3 = zeta_width(rr, F0, nperseg=nperseg)
            pr("   %-8.4f | %8.4f  (n=%4s, bias x%5.2f) | %8.4f  (bias x%5.2f)   | %8.4f f0 %6.3f R2 %.3f"
               % (zt, e1["z"], e1.get("nfit", "-"), e1["z"] / zt if np.isfinite(e1["z"]) else np.nan,
                  e2["z"], e2["z"] / zt if np.isfinite(e2["z"]) else np.nan,
                  e3["z"], e3["f0"], e3["r2"]))
        # NEGATIVE control: no mode at all
        rng = np.random.default_rng(4242)
        nz = signal.sosfiltfilt(signal.butter(4, (4.0, 45.0), btype="band", fs=FS, output="sos"),
                                rng.standard_normal(int(secs * FS)))
        rr = chop(nz, seclen)
        e1 = zeta_decay(rr, F0)
        e2 = zeta_coh(rr, F0, taumax=min(0.60, seclen * 0.4))
        e3 = zeta_width(rr, F0, nperseg=nperseg)
        pr("   %-8s | %8.4f  (n=%4s)             | %8.4f                | %8.4f f0 %6.3f R2 %.3f   <-- NEGATIVE CONTROL"
           % ("NO MODE", e1["z"], e1.get("nfit", "-"), e2["z"], e3["z"], e3["f0"], e3["r2"]))
        # quantised negative control at the rate channel's own LSB scale
    pr()
    pr("-" * 120)
    pr("E  QUANTISATION control -- the 0x18F rate channel is 0.125 deg/s LSB and the record measures the")
    pr("   ring at 0.17-0.28 LSB [STATE correction 8c].  Mode amplitude set to 0.25 LSB rms, 600 s.")
    pr("   %-8s | %-26s | %-26s | %-30s" % ("true z", "E1 free-decay", "E2 coherence", "E3 line width"))
    for zt in (0.010, 0.030, 0.100, 0.300):
        x = synth(zt, F0, int(600 * FS), 0.0, seed=int(zt * 1e5))
        x = x * (0.25 * 0.125 / np.std(L.bp(x, 18, 22)))
        xq = np.round(x / 0.125) * 0.125
        rr = chop(xq, 20.0)
        e1 = zeta_decay(rr, F0)
        e2 = zeta_coh(rr, F0)
        e3 = zeta_width(rr, F0, nperseg=1024)
        pr("   %-8.4f | %8.4f  (n=%4s, bias x%5.2f) | %8.4f  (bias x%5.2f)   | %8.4f f0 %6.3f R2 %.3f"
           % (zt, e1["z"], e1.get("nfit", "-"), e1["z"] / zt, e2["z"], e2["z"] / zt,
              e3["z"], e3["f0"], e3["r2"]))
    pr()
    pr("READ THE NEGATIVE CONTROL ROWS FIRST.  Whatever they return is the CEILING of what each")
    pr("estimator can say: a measured zeta at or above that row is indistinguishable from 'no mode'.")


if __name__ == "__main__":
    controls()
    save("openloop_zeta_controls.txt")


# ==============================================================================================
# E3b -- THE HONEST LINE-WIDTH FIT: a POWER-LAW BACKGROUND times a resonance, with f0 confined to
# the interior of the window and an explicit BUMP statistic.
#
# WHY: the first cut of E3 fitted a bare Lorentzian plus a constant.  On a spectrum with NO line in
# it that model is degenerate -- it parks f0 on the window edge and uses a very broad, very tall
# Lorentzian tail as the 1/f skirt, scoring R2 0.83-0.88 while measuring nothing.  Three of the
# disengaged rows did exactly that (f0 15.83 / 16.08 / 16.37 against a 16.0 Hz window edge).
# So: model the background explicitly, force f0 inside, and report how big a BUMP over that
# background the resonance actually is.  bump ~ 1.0 means there is no line and zeta is UNIDENTIFIED,
# whatever the fit returns.
# ==============================================================================================
def _model(f, th, fmid, flo, fhi):
    c0, p, lA, u, lz = th
    bg = np.exp(np.clip(c0, -300, 300)) * (f / fmid) ** (-p)
    f0 = flo + 0.5 + (fhi - flo - 1.0) / (1.0 + np.exp(-np.clip(u, -30, 30)))
    z = np.exp(np.clip(lz, -20, 2))
    res = np.exp(np.clip(lA, -300, 300)) / ((f ** 2 - f0 ** 2) ** 2 + (2 * z * f0 * f) ** 2)
    return bg + res, bg, f0, z


def enbw(nperseg, fs=FS):
    """equivalent noise bandwidth of a Hann-windowed Welch bin, in Hz."""
    return 1.5 * fs / nperseg


def fit_line(f, P, flo, fhi, nperseg=1024, fs=FS, excl=2.5):
    """background power law + one resonance, with the BACKGROUND PINNED.

    Three degeneracies were observed on real data and each is closed here:
      1. f0 parks on a window edge and the Lorentzian tail plays the 1/f skirt
         -> f0 is confined to the interior by a logistic transform.
      2. zeta shrinks below the Welch resolution, where the peak height between bins is
         unconstrained, so A and zeta run away together
         -> zeta >= ENBW/(2 f0), the width this spectrum can actually resolve.
      3. the BACKGROUND collapses toward zero and a very broad Lorentzian becomes the continuum,
         giving fitted peak/background ratios of 1e9 on spectra whose real line is ~20 dB
         -> the power law is fitted FIRST on the bins OUTSIDE +-`excl` Hz of the peak and then held
            to within +-0.3 in log amplitude and +-1.0 in slope of that fit.
    `bump` is the model's peak-over-background.  `prom_data` is the MODEL-FREE version of the same
    thing -- max(P within +-1 Hz of the fitted f0) over median(P across the window) -- and it is the
    statistic to trust when the two disagree.
    """
    m = (f >= flo) & (f <= fhi) & (P > 0)
    if m.sum() < 14:
        return None
    ff, PP = f[m], P[m]
    fmid = 0.5 * (flo + fhi)
    lPP = np.log(PP)
    sst = np.sum((lPP - lPP.mean()) ** 2)
    zmin = float(enbw(nperseg, fs) / (2.0 * fmid))
    zmax = 0.80

    def bgv(c0, p_):
        return np.exp(np.clip(c0, -300, 300)) * (ff / fmid) ** (-p_)

    # --- stage 1: background from the out-of-line bins only
    sm = signal.medfilt(PP, 5)
    jpk = int(np.argmax(PP / np.maximum(sm, 1e-300)))
    jpk = int(np.argmax(PP / np.maximum(np.exp(np.polyval(np.polyfit(np.log(ff), lPP, 1), np.log(ff))), 1e-300)))
    fpk = ff[jpk]
    out = np.abs(ff - fpk) > excl
    if out.sum() < 8:
        out = np.ones(len(ff), bool)
    cb = np.polyfit(np.log(ff[out] / fmid), lPP[out], 1)
    p0_, c0_ = -cb[0], cb[1]
    ssb = float(np.sum((np.log(bgv(c0_, p0_)) - lPP) ** 2))

    # --- stage 2: resonance, with the background held near stage 1
    def resid(th):
        c0, p_, lA, u, lz = th
        f0 = flo + 0.5 + (fhi - flo - 1.0) / (1.0 + np.exp(-np.clip(u, -30, 30)))
        z = np.exp(np.clip(lz, -20, 2))
        mod = bgv(c0, p_) + np.exp(np.clip(lA, -300, 300)) / ((ff ** 2 - f0 ** 2) ** 2 + (2 * z * f0 * ff) ** 2)
        return np.log(np.maximum(mod, 1e-300)) - lPP

    lo_b = [c0_ - 0.3, p0_ - 1.0, np.log(PP.min() * 1e-6) + 4 * np.log(max(flo, 1.0)), -6.0, np.log(zmin)]
    hi_b = [c0_ + 0.3, p0_ + 1.0, np.log(PP.max() * 1e4) + 4 * np.log(fhi), 6.0, np.log(zmax)]
    best, bc = None, np.inf
    for z0 in (zmin * 1.5, 0.02, 0.06, 0.20, 0.50):
        z0 = float(np.clip(z0, zmin * 1.01, zmax * 0.99))
        for fsd in (fpk,):
            f0s = float(np.clip(fsd, flo + 0.7, fhi - 0.7))
            u0 = float(np.clip(np.log((f0s - flo - 0.5) / max(fhi - 0.5 - f0s, 1e-6)), -5.5, 5.5))
            A0 = max((PP[jpk] - bgv(c0_, p0_)[jpk]) * ((2 * z0 * f0s ** 2) ** 2), 1e-300)
            th0 = [c0_, p0_, float(np.clip(np.log(A0), lo_b[2] + 1, hi_b[2] - 1)), u0, np.log(z0)]
            try:
                r = optimize.least_squares(resid, th0, bounds=(lo_b, hi_b), max_nfev=4000)
            except Exception:
                continue
            if r.cost < bc:
                bc, best = r.cost, r
    if best is None:
        return None
    c0, p_, lA, u, lz = best.x
    f0 = flo + 0.5 + (fhi - flo - 1.0) / (1.0 + np.exp(-np.clip(u, -30, 30)))
    z = float(np.exp(np.clip(lz, -20, 2)))
    bg = bgv(c0, p_)
    res = np.exp(np.clip(lA, -300, 300)) / ((ff ** 2 - f0 ** 2) ** 2 + (2 * z * f0 * ff) ** 2)
    n = len(ff)
    ss = float(np.sum(best.fun ** 2))
    near = np.abs(ff - f0) <= 1.0
    prom = float(np.max(PP[near]) / np.median(PP)) if near.any() else np.nan
    return dict(z=z, f0=float(f0), bump=float(np.max((bg + res) / bg)), prom_data=prom,
                r2=float(1 - ss / sst), r2_bg=float(1 - ssb / sst),
                dAIC=float(n * np.log(ss / n) - n * np.log(ssb / n) + 2 * 3),
                n=n, zmin_res=zmin,
                edge=bool(f0 < flo + 0.75 or f0 > fhi - 0.75),
                atfloor=bool(z <= zmin * 1.05))


def zeta_line(runs_, flo, fhi, nperseg=1024, fs=FS, nboot=0, seed=0):
    f, P, W = pooled_psd(runs_, nperseg, fs)
    nil = dict(z=np.nan, f0=np.nan, bump=np.nan, r2=np.nan, dAIC=np.nan, lo=np.nan, hi=np.nan,
               blo=np.nan, bhi=np.nan, secs=(W / fs if f is not None else 0.0),
               nseg=len(runs_), edge=True, atfloor=False, zmin_res=np.nan)
    if f is None:
        return nil
    r = fit_line(f, P, flo, fhi, nperseg, fs)
    if r is None:
        return nil
    r["secs"] = W / fs
    r["nseg"] = len(runs_)
    r["lo"] = r["hi"] = r["blo"] = r["bhi"] = np.nan
    if nboot and len(runs_) > 4:
        rng = np.random.default_rng(seed)
        zs, bs = [], []
        for _ in range(nboot):
            sel = rng.integers(0, len(runs_), len(runs_))
            fb, Pb, _ = pooled_psd([runs_[i] for i in sel], nperseg, fs)
            rr = fit_line(fb, Pb, flo, fhi, nperseg, fs) if fb is not None else None
            if rr:
                zs.append(rr["z"]); bs.append(rr["bump"])
        if len(zs) > 10:
            r["lo"], r["hi"] = float(np.percentile(zs, 2.5)), float(np.percentile(zs, 97.5))
            r["blo"], r["bhi"] = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    return r


def inject(runs_, zeta, f0, amp, fs=FS, seed=0, lo=18.0, hi=22.0):
    """add a synthetic mode of KNOWN zeta to real segments, scaled so its lo-hi band amplitude
    (sqrt(2)*std of the band-passed synthetic) equals `amp` in the channel's own units."""
    out = []
    for i, x in enumerate(runs_):
        m = resonator(zeta, f0, len(x), seed + i, fs)
        s = np.std(L.bp(m, lo, hi, fs)) * np.sqrt(2.0)
        out.append(np.asarray(x, float) + m * (amp / max(s, 1e-30)))
    return out
