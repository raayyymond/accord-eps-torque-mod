# -*- coding: utf-8 -*-
"""tau_actuator_delay.py -- MEASURE the LKAS actuator delay tau (0xE4 command -> steering response)
from the cached rlogs.  Subagent taumeasure, 2026-09-13.

Analysis only.  Builds nothing, sends nothing on any bus, flashes nothing, commits nothing.

WHY.  The outer-loop stability verdict on the V293 torque-mode candidate hinges on tau.  The fork's
`liveDelay.lateralDelay` reads 0.2000 flat, but that is the operator's `SteerDelay` toggle ECHOED
(`UseAutoSteerDelay = 0`), not an identification; the Honda port's prior is `steerActuatorDelay = 0.1`.

POLARITY, fixed once here [EVIDENCE, tau_orient.py Q1]:
    rate_x = -wire/CPD  and  ang = 0x14A b0-1 * -0.1  share ONE sign convention; d(ang)/dt = +1.00*rate_x
    (slope 0.994-1.017, corr 0.987-0.994 on all six routes).  BOTH are opposite in sign to a positive
    0xE4 command.  So the PHYSICAL-polarity response variables used below are
        y_rate = -rate_x = +wire/CPD   [deg/s]        y_ang  = -ang = +0x14A*0.1   [deg]
    and a positive cmd produces a positive y_rate.  (Asserted at run time, not assumed.)

STRUCTURE, measured before any lag is quoted [EVIDENCE, tau_struct.py]:
    cmd -> y_rate  is a GAIN  (|H| 0.012-0.024 deg/s per count, flat 0.2-2 Hz; coh 0.93-0.98)
    cmd -> y_ang   is an INTEGRATOR (|H| ~ 1/f, phase ~ -90 deg)
  A correlation lag is only a transport delay if the path is a gain over the band used; it is, on
  cmd -> y_rate, so that is the pair every estimator below uses.

THE CLOSED-LOOP PROBLEM, and how each estimator is biased.
  openpilot reacts to the wheel, so with plant G, controller C, exogenous reference r (the model's
  desired path -- road geometry, exogenous) and wheel-side disturbance d:
        cmd  = (r - C d)/(1+CG)          y = (G r + d)/(1+CG)
        E[cmd* y]/E[cmd* cmd] = (G Prr - conj(C) Pdd) / (Prr + |C|^2 Pdd)
  -> r-dominated  (curvy road, big commands): the estimate tends to G.  UNBIASED, what we want.
  -> d-dominated  (dead-straight road, wheel noise): the estimate tends to -1/conj(C), the INVERSE
     CONTROLLER, whose apparent delay is the FEEDBACK arm's (~ -23 ms, the wrong sign) -- it drags the
     estimate DOWN.  So every closed-loop plain-correlation tau here is a LOWER BOUND on the true tau.
  THE VALIDITY TEST run below is invariance: split each speed band by command activity (curvy vs
  straight) and by |steering angle|, and check the estimate does not move.  If it does not, Pdd is not
  driving it.  The two-sided impulse response makes the two arms visible SEPARATELY in lag, which is the
  discriminator the brief asked for.

ESTIMATORS (all on the SAME stretches, so they are comparable)
  A  XCORR      two-sided normalised cross-correlation of band-passed (0.2-2 Hz) cmd vs y_rate; peak lag
                by parabolic interpolation.  Cheap, and its two-sidedness exposes the feedback arm.
  B  FIR        ridge-regularised two-sided FIR (Wiener) deconvolution y_rate[n] = sum_k h[k] cmd[n-k],
                k = -0.40 .. +0.80 s.  Divides out the command's own autocorrelation, which XCORR does
                not.  Reports the CAUSAL ONSET (pure dead time) and the CAUSAL CENTROID separately.
  C  GROUPDELAY coherence-weighted slope of the unwrapped cmd -> y_rate phase over 0.2-2 Hz.
                tau_eff = -slope/360 (s per Hz -> s).  THIS IS THE NUMBER THE OUTER-LOOP MODEL NEEDS:
                it is the delay that reproduces the measured phase in the band the loop crosses over in,
                and it already CONTAINS the rate servo's own lag.  Reported with the phase at 1 Hz.
  D  FOPDT      first-order-plus-dead-time output-error fit: y = K/(1+sT) * cmd(t-tau_dead); grid over
                tau_dead and T, least squares on K.  Splits PURE DEAD TIME from SERVO LAG.
  CI: block bootstrap, resampling whole stretches with replacement, 2000 draws, percentile 2.5/97.5.

Run:  python rlog-tools/studies/grind/tau_actuator_delay.py            (all routes, all bands)
      python rlog-tools/studies/grind/tau_actuator_delay.py r6c        (one route)
Writes _scratch/tau_actuator_delay.txt beside this file.
"""
import json
import os
import sys

import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20   # noqa: E402
import v280_map_profiles as V   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
FS = 100.0
FLO, FHI = 0.2, 2.0                       # the band the outer loop crosses over in
LAG_LO, LAG_HI = -0.40, 0.80              # two-sided FIR / xcorr lag window, seconds
NBOOT = 2000
MINSTRETCH = 800                          # 8 s
ROUTES = [("r6c", "V282"), ("r39", "V282"), ("r35", "V281r3"),
          ("r6d_v292", "V292"), ("r6e_v292", "V292"), ("r6f_v292", "V292")]
BANDS = [(0.0, 3.0), (3.0, 8.0), (8.0, 15.0), (15.0, 25.0), (25.0, 99.0)]
OUT = []
RESULTS = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


# ======================================================================================================
# masks and stretches
# ======================================================================================================
def runs(mask, min_len):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= min_len]


def handsoff(g, tag, barmax=800.0):
    """engaged AND rolling-max |bar| over +-0.3 s < barmax AND not steeringPressed (dilated +-0.5 s).

    `bar` is the TORSION BAR: it carries road and assist reaction with the driver's hands off (engaged,
    not-pressed p50 |bar| = 139 raw), so this is a 'driver is not fighting the wheel' cut, not a literal
    zero-torque cut.  carState.steeringPressed exists only on the V292 caches."""
    m = g["eng"] & (maximum_filter1d(np.abs(g["bar"]), size=61, mode="nearest") < barmax)
    raw = dict(np.load(os.path.join(CACHE, tag + ".npz")))
    if "cs_press" in raw:
        p = np.interp(g["t"], raw["tcs"], raw["cs_press"].astype(float)) > 0.5
        m &= ~(maximum_filter1d(p.astype(np.uint8), size=101, mode="nearest") > 0)
    return m


def bandpass(x, lo=FLO, hi=FHI, fs=FS, order=4):
    b, a = signal.butter(order, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    return signal.filtfilt(b, a, x)          # zero phase: adds NO lag of its own


# ======================================================================================================
# A -- two-sided cross-correlation
# ======================================================================================================
def xcorr_lag(segs, lo=LAG_LO, hi=LAG_HI, fs=FS):
    """segs = list of (u, y) already band-passed.  Pooled normalised cross-correlation, peak lag (s).
    Positive lag = y lags u = the FORWARD (plant) arm."""
    klo, khi = int(round(lo * fs)), int(round(hi * fs))
    lags = np.arange(klo, khi + 1)
    num = np.zeros(len(lags)); nu = ny = 0.0
    for u, y in segs:
        u = u - u.mean(); y = y - y.mean()
        nu += np.dot(u, u); ny += np.dot(y, y)
        for i, k in enumerate(lags):
            if k >= 0:
                num[i] += np.dot(u[:len(u) - k], y[k:]) if k else np.dot(u, y)
            else:
                num[i] += np.dot(u[-k:], y[:len(y) + k])
    r = num / np.sqrt(nu * ny)
    return lags / fs, r


def peak_parabolic(lags, r):
    i = int(np.argmax(np.abs(r)))
    if 0 < i < len(r) - 1:
        y0, y1, y2 = r[i - 1], r[i], r[i + 1]
        den = (y0 - 2 * y1 + y2)
        d = 0.5 * (y0 - y2) / den if den != 0 else 0.0
        d = float(np.clip(d, -1, 1))
    else:
        d = 0.0
    step = lags[1] - lags[0]
    return lags[i] + d * step, r[i]


# ======================================================================================================
# B -- ridge two-sided FIR (Wiener) deconvolution
# ======================================================================================================
def fir_ir(segs, lo=LAG_LO, hi=LAG_HI, fs=FS, ridge=1e-3):
    """Least-squares two-sided FIR: y[n] = sum_{k=klo..khi} h[k] u[n-k].  Returns lags (s), h.
    Built by normal equations from the pooled autocorrelation of u and cross-correlation u,y, which is
    exact for the stationary case and far cheaper than stacking the design matrix."""
    klo, khi = int(round(lo * fs)), int(round(hi * fs))
    m = khi - klo + 1
    maxlag = m
    Ruu = np.zeros(maxlag + 1); Ruy = np.zeros(m); nu = 0.0
    for u, y in segs:
        u = u - u.mean(); y = y - y.mean()
        n = len(u); nu += n
        # autocorrelation of u, lags 0..maxlag
        fu = np.fft.rfft(u, 2 * n)
        ac = np.fft.irfft(fu * np.conj(fu), 2 * n)[:maxlag + 1]
        Ruu += ac
        # cross-correlation, lag k means y[n] vs u[n-k]
        fy = np.fft.rfft(y, 2 * n)
        cc = np.fft.irfft(fy * np.conj(fu), 2 * n)        # cc[k] = sum y[n] u[n-k], k>=0
        for i, k in enumerate(range(klo, khi + 1)):
            Ruy[i] = Ruy[i] + (cc[k] if k >= 0 else cc[(2 * n) + k])
    Ruu /= nu; Ruy /= nu
    from scipy.linalg import solve_toeplitz
    c = Ruu[:m].copy()
    c[0] *= (1.0 + ridge)
    try:
        h = solve_toeplitz((c, c), Ruy)
    except Exception:
        R = np.array([[Ruu[abs(i - j)] for j in range(m)] for i in range(m)])
        R[np.diag_indices(m)] *= (1.0 + ridge)
        h = np.linalg.solve(R, Ruy)
    return np.arange(klo, khi + 1) / fs, h


def ir_stats(lags, h, frac=0.25):
    """causal onset (first lag >=0 where |h| crosses frac of the causal peak) and causal centroid."""
    cz = lags >= 0
    hc, lc = h[cz], lags[cz]
    ip = int(np.argmax(np.abs(hc)))
    pk = np.abs(hc[ip])
    thr = frac * pk
    onset = lc[ip]
    for i in range(ip, -1, -1):
        if np.abs(hc[i]) < thr:
            # linear interpolation of the crossing
            if i + 1 <= ip:
                x0, x1 = np.abs(hc[i]), np.abs(hc[i + 1])
                onset = lc[i] + (thr - x0) / max(1e-12, (x1 - x0)) * (lc[i + 1] - lc[i])
            break
    w = np.abs(hc) * (np.abs(hc) > 0.1 * pk)
    cent = float(np.sum(lc * w) / max(1e-12, np.sum(w)))
    # peak by parabola
    pkl, _ = peak_parabolic(lc, hc)
    anti = float(np.sum(np.abs(h[lags < 0])) / max(1e-12, np.sum(np.abs(h))))
    return dict(onset=float(onset), peak=float(pkl), centroid=cent, anticausal_share=anti,
                peak_amp=float(hc[ip]))


# ======================================================================================================
# C -- coherence-weighted group delay from the cmd -> y_rate phase slope
# ======================================================================================================
def group_delay(segs, fs=FS, nper=1024, lo=FLO, hi=FHI):
    nov = nper // 2
    Puu = Pyy = Puy = None
    for u, y in segs:
        if len(u) < nper:
            continue
        f, a = signal.welch(u, fs, nperseg=nper, noverlap=nov, detrend="linear")
        _, b = signal.welch(y, fs, nperseg=nper, noverlap=nov, detrend="linear")
        _, c = signal.csd(u, y, fs, nperseg=nper, noverlap=nov, detrend="linear")
        w = len(u)
        Puu = a * w if Puu is None else Puu + a * w
        Pyy = b * w if Pyy is None else Pyy + b * w
        Puy = c * w if Puy is None else Puy + c * w
    if Puu is None:
        return None
    H = Puy / Puu
    coh = np.abs(Puy) ** 2 / (Puu * Pyy)
    sel = (f >= lo) & (f <= hi)
    fs_, ph = f[sel], np.degrees(np.unwrap(np.angle(H[sel])))
    w = coh[sel]
    if len(fs_) < 3:
        return None
    A = np.vstack([fs_, np.ones_like(fs_)]).T
    W = np.diag(w)
    coef = np.linalg.lstsq(A.T @ W @ A, A.T @ W @ ph, rcond=None)[0]
    slope, icept = coef
    tau = -slope / 360.0
    ph1 = np.interp(1.0, f, np.degrees(np.unwrap(np.angle(H))))
    return dict(tau=float(tau), slope_deg_per_Hz=float(slope), intercept_deg=float(icept),
                phase_1Hz=float(ph1), coh_mean=float(np.mean(w)), coh_min=float(np.min(w)),
                mag_1Hz=float(np.interp(1.0, f, np.abs(H))), f=f, H=H, coh=coh)


# ======================================================================================================
# D -- FOPDT output-error fit:  y = K/(1+sT) * u(t - tau_dead)
# ======================================================================================================
def fopdt(segs, fs=FS, dead_max=0.60, tmax=0.40):
    best = None
    deads = np.arange(0, int(dead_max * fs) + 1)
    taus = np.r_[0.0, np.exp(np.linspace(np.log(0.005), np.log(tmax), 28))]
    for T in taus:
        a = float(np.exp(-1.0 / (fs * T))) if T > 0 else 0.0
        bb, aa = np.array([1 - a]), np.array([1.0, -a])
        filt = [signal.lfilter(bb, aa, u) for u, _ in segs]
        for d in deads:
            num = den = 0.0; sse = 0.0; sy = 0.0
            for fu, (_, y) in zip(filt, segs):
                if d:
                    x = np.r_[np.zeros(d), fu[:-d]]
                else:
                    x = fu
                x = x[int(0.6 * fs):]; yy = y[int(0.6 * fs):]
                num += np.dot(x, yy); den += np.dot(x, x)
            if den <= 0:
                continue
            K = num / den
            for fu, (_, y) in zip(filt, segs):
                x = (np.r_[np.zeros(d), fu[:-d]] if d else fu)[int(0.6 * fs):]
                yy = y[int(0.6 * fs):]
                r = yy - K * x
                sse += np.dot(r, r); sy += np.dot(yy - yy.mean(), yy - yy.mean())
            if best is None or sse < best["sse"]:
                best = dict(sse=float(sse), r2=float(1 - sse / max(1e-12, sy)), K=float(K),
                            dead=float(d / fs), T=float(T))
    return best


# ======================================================================================================
def boot_ci(items, fn, nboot=NBOOT, seed=0):
    """block bootstrap over whole stretches."""
    rng = np.random.default_rng(seed)
    n = len(items)
    if n < 2:
        return (np.nan, np.nan)
    vals = []
    for _ in range(nboot):
        idx = rng.integers(0, n, n)
        v = fn([items[i] for i in idx])
        if v is not None and np.isfinite(v):
            vals.append(v)
    if len(vals) < 20:
        return (np.nan, np.nan)
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


def analyse(tag, build, lab, segs_raw, note=""):
    """segs_raw: list of dicts with u (cmd), y (y_rate deg/s), plus metadata."""
    if len(segs_raw) < 1:
        return None
    bp = [(bandpass(s["u"]), bandpass(s["y"])) for s in segs_raw]
    raw = [(s["u"], s["y"]) for s in segs_raw]
    tot = sum(len(s["u"]) for s in segs_raw) / FS

    lags, r = xcorr_lag(bp)
    xl, xr = peak_parabolic(lags, r)
    xci = boot_ci(bp, lambda S: peak_parabolic(*xcorr_lag(S))[0])

    flg, h = fir_ir(bp)
    st = ir_stats(flg, h)
    fci = boot_ci(bp, lambda S: ir_stats(*fir_ir(S))["peak"])
    oci = boot_ci(bp, lambda S: ir_stats(*fir_ir(S))["onset"], nboot=400)

    gd = group_delay(raw)
    gci = boot_ci([s for s in raw if len(s[0]) >= 1024],
                  lambda S: (group_delay(S) or {}).get("tau"), nboot=400) if gd else (np.nan, np.nan)

    fp = fopdt(bp)

    res = dict(route=tag, build=build, stratum=lab, n_stretch=len(segs_raw), seconds=tot,
               xcorr_lag=float(xl), xcorr_peak=float(xr), xcorr_ci=xci,
               fir_peak=st["peak"], fir_onset=st["onset"], fir_centroid=st["centroid"],
               fir_anticausal_share=st["anticausal_share"], fir_ci=fci, fir_onset_ci=oci,
               gd_tau=(gd or {}).get("tau"), gd_ci=gci, gd_phase1=(gd or {}).get("phase_1Hz"),
               gd_coh=(gd or {}).get("coh_mean"), gd_mag1=(gd or {}).get("mag_1Hz"),
               gd_slope=(gd or {}).get("slope_deg_per_Hz"), gd_intercept=(gd or {}).get("intercept_deg"),
               fopdt_dead=fp["dead"] if fp else None, fopdt_T=fp["T"] if fp else None,
               fopdt_r2=fp["r2"] if fp else None, fopdt_K=fp["K"] if fp else None, note=note)
    RESULTS.append(res)

    pr("      %-26s n=%2d  %6.1f s" % (lab, len(segs_raw), tot))
    pr("          A XCORR   peak lag %+7.1f ms  (r %+.3f)   CI [%+.0f, %+.0f] ms"
       % (1e3 * xl, xr, 1e3 * xci[0], 1e3 * xci[1]))
    pr("          B FIR     causal peak %+7.1f ms  CI [%+.0f, %+.0f] | onset(25%%) %+6.1f ms CI [%+.0f, %+.0f] | centroid %+6.1f ms | anticausal share %.2f"
       % (1e3 * st["peak"], 1e3 * fci[0], 1e3 * fci[1], 1e3 * st["onset"], 1e3 * oci[0], 1e3 * oci[1],
          1e3 * st["centroid"], st["anticausal_share"]))
    if gd:
        pr("          C GROUPDEL tau_eff %7.1f ms  CI [%.0f, %.0f]  (slope %+.1f deg/Hz, intercept %+.1f deg, phase@1Hz %+.1f deg, coh %.2f, |H|@1Hz %.4f)"
           % (1e3 * gd["tau"], 1e3 * gci[0], 1e3 * gci[1], gd["slope_deg_per_Hz"], gd["intercept_deg"],
              gd["phase_1Hz"], gd["coh_mean"], gd["mag_1Hz"]))
    if fp:
        pr("          D FOPDT   dead %5.0f ms + servo T %5.0f ms  (K %.4f, R2 %.3f)  -> total phase-equiv at 1 Hz %5.0f ms"
           % (1e3 * fp["dead"], 1e3 * fp["T"], fp["K"], fp["r2"],
              1e3 * (fp["dead"] + np.degrees(np.arctan(2 * np.pi * 1.0 * fp["T"])) / 360.0)))
    return res


def main(only=None):
    pr("=" * 132)
    pr("LKAS ACTUATOR DELAY tau -- 0xE4 command -> steering rate, from the cached rlogs")
    pr("  u = cmd (0xE4 b0-1 raw, src 129).   y = +wire/%.1f deg/s (PHYSICAL polarity: = -rate_x = -d(ang)/dt)." % V.CPD)
    pr("  Band %.1f-%.1f Hz.  Engaged = SCA & STEER_REQUEST & no CAN gap.  Hands-off per handsoff()." % (FLO, FHI))
    pr("  Positive lag = the wheel LAGS the command = the forward (plant) arm.")
    pr("=" * 132)

    for tag, build in ROUTES:
        if only and tag not in only:
            continue
        g = C20.load(tag)
        # --- polarity assertion, not assumption ---------------------------------------------------
        y_rate = -g["rate_x"]                      # = +wire/CPD
        ho = handsoff(g, tag)
        rr = runs(ho, MINSTRETCH)
        if not rr:
            pr("\nROUTE %-9s %-8s : no engaged hands-off stretch >= %.0f s" % (tag, build, MINSTRETCH / FS))
            continue
        up = np.concatenate([bandpass(g["cmd"][a:b]) for a, b in rr])
        yp = np.concatenate([bandpass(y_rate[a:b]) for a, b in rr])
        lg, rc = xcorr_lag([(up, yp)])
        ipk = int(np.argmax(np.abs(rc)))
        pr("")
        pr("=" * 132)
        pr("ROUTE %-9s build %-8s   engaged %.1f%%  hands-off-engaged %.0f s  stretches>=%.0fs: %d"
           % (tag, build, 100 * g["eng"].mean(), ho.sum() / FS, MINSTRETCH / FS, len(rr)))
        pr("   POLARITY CHECK: pooled xcorr extremum r = %+.3f at lag %+.0f ms -> %s"
           % (rc[ipk], 1e3 * lg[ipk],
              "POSITIVE, y = +wire/CPD is the right polarity" if rc[ipk] > 0 else
              "*** NEGATIVE -- polarity wrong, every lag below is meaningless ***"))

        for lo, hi in BANDS:
            m = ho & (g["vego"] >= lo) & (g["vego"] < hi)
            rr = runs(m, MINSTRETCH)
            if not rr:
                pr("   v %2.0f-%-2.0f m/s : %6.1f s, no stretch >= %.0f s" % (lo, hi, m.sum() / FS, MINSTRETCH / FS))
                continue
            pr("   v %2.0f-%-2.0f m/s  (%6.1f s in %d stretches >= %.0f s)"
               % (lo, hi, sum(b - a for a, b in rr) / FS, len(rr), MINSTRETCH / FS))
            segs = [dict(u=g["cmd"][a:b], y=y_rate[a:b], ang=g["ang"][a:b], a=a, b=b) for a, b in rr]
            analyse(tag, build, "ALL", segs)
            # --- validity test: curvy (r-dominated) vs straight (d-dominated) -------------------
            act = np.array([np.std(bandpass(s["u"])) for s in segs])
            if len(segs) >= 4:
                med = np.median(act)
                hi_s = [s for s, a_ in zip(segs, act) if a_ >= med]
                lo_s = [s for s, a_ in zip(segs, act) if a_ < med]
                if len(hi_s) >= 2:
                    analyse(tag, build, "CURVY (cmd rms>=med)", hi_s, note="r-dominated: least biased")
                if len(lo_s) >= 2:
                    analyse(tag, build, "STRAIGHT (cmd rms<med)", lo_s, note="d-dominated: most biased")

    with open(os.path.join(HERE, "_scratch", "tau_actuator_delay.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT))
    with open(os.path.join(HERE, "_scratch", "tau_actuator_delay.json"), "w", encoding="utf-8") as fh:
        json.dump(RESULTS, fh, indent=1, default=float)
    pr("")
    pr("wrote _scratch/tau_actuator_delay.{txt,json}  (%d strata)" % len(RESULTS))


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "_scratch"), exist_ok=True)
    main(sys.argv[1:] or None)
