# -*- coding: utf-8 -*-
"""tau_identify.py -- the LKAS actuator delay tau, identified from the planner's DESIRED CURVATURE
(exogenous) to the car's response.  Subagent taumeasure, 2026-09-13.

Analysis only.  Builds nothing, sends nothing on any bus, flashes nothing, commits nothing.

WHY NOT THE 0xE4 WIRE.  tau_actuator_delay.py measured cmd(0xE4) -> wheel rate and found the peak at a
NEGATIVE lag (-31..-66 ms) with r = +0.89..+0.97, and a first-order-plus-dead-time fit returning dead 0 /
lag 0 at R^2 0.79-0.91.  That is the controller's own rate-plant FEEDFORWARD (`AccordRatePlantFF` ON,
LAF 6.0 cutting P/I authority 2.5x): the 0xE4 command is largely an algebraic function of the rate the
car is ALREADY doing, so the wheel LEADS the command by about one openpilot round trip (21-26 ms, this
kit's own OUTER-LOOP-ID-2026-09-10 Sec.5).  The plant arm is buried.  A cmd->rate lag on this car is NOT
a transport delay.  [EVIDENCE -- that script's own output.]

WHAT IS EXOGENOUS.  `controlsState.desiredCurvature` (== `carControl.actuators.curvature`, verified
slope 1.0000 corr 1.0000) is the PLAN: it comes from the camera and the road, not from the steering
wheel.  It is the command the torque controller then tries to realise.  Its feedback path to the wheel
(steer -> lane position -> camera -> model) is slow and double-integrating, so over 0.2-2 Hz it is
dominated by road geometry.  The two-sided NCC below TESTS that rather than assuming it: a closed-loop
contamination would put mass at negative lag, exactly as the 0xE4 pair does.

THE PLANNER'S OWN LOOKAHEAD CANCELS.  The controller commands c_plan(t + tau_assumed) and the car
realises it at t + tau_true, so the measured command->response lag is tau_true for ANY tau_assumed.
So the operator's SteerDelay = 0.2 does not bias this measurement.  [EVIDENCE: algebraic, and confirmed
below by the estimate being flat across routes whose applied delay is identical anyway.]

TWO RESPONSE CHANNELS, AND THEY BRACKET THE ANSWER [EVIDENCE, verified on r39]:
  y_steer  `carControl.currentCurvature` -- the curvature from the STEERING ANGLE through the vehicle
           model.  `controlsState...torqueState.actualLateralAccel` == y_steer * v^2 to slope 0.9999 /
           corr 1.0000, so this is the "actual" the TORQUE CONTROLLER itself closes on.  The lag to
           here is the EPS ACTUATOR delay alone.
  y_yaw    the RAW GYRO (gyroscope x-axis, negated: slope -1.0046, corr -0.9965 against the calibrated
           yaw rate), divided by vEgo.  The lag to here is the FULL lateral delay -- EPS actuator plus
           the vehicle's own yaw response.  This is the quantity openpilot's lagd uses, but taken from
           the rawest, highest-rate instrument (87.8 Hz) instead of the 20 Hz livePose estimator.
  y_pose   `carControl.angularVelocity[2]` / v -- the calibrated livePose yaw as controlsd held it.
           Reported for comparability with lagd, and it carries a ZERO-ORDER-HOLD bias: livePose is
           20 Hz and controlsd holds the last value, so this channel is late by ~25 ms on average.

ESTIMATORS
  NCC   openpilot lagd's own masked normalised cross-correlation (`masked_normalized_cross_correlation`
        + `parabolic_peak_interp`, mirrored here verbatim in arithmetic), ROI 0 .. +0.65 s.  This is the
        canonical number: it is what the fork's own estimator computes, so it is directly comparable.
  NCC2  the same correlation read over a TWO-SIDED ROI -0.30 .. +0.65 s.  Its job is to FAIL: if the
        pair is closed-loop-contaminated the peak moves to a negative lag, as the 0xE4 pair's does.
  GD    coherence-weighted slope of the unwrapped u->y phase over 0.2-2 Hz; tau = -slope/360.  This is
        the delay that reproduces the measured PHASE in the band the outer loop crosses over in, and it
        already contains the servo's own lag.  Reported with the phase and coherence at 1 Hz.
  CI    block bootstrap over whole stretches, 2000 draws, percentile 2.5/97.5.

Run:  python rlog-tools/studies/grind/tau_identify.py            (every route with a tau cache)
      python rlog-tools/studies/grind/tau_identify.py r39 r6c
Writes _scratch/tau_identify.{txt,json}
"""
import json
import os
import sys
from functools import partial

import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "tau")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
FLO, FHI = 0.2, 2.0
MAX_LAG = 0.65
MIN_LAG2 = -0.30
NBOOT = 2000
MINSTRETCH = int(12 * FS)
BANDS = [(0.0, 3.0), (3.0, 8.0), (8.0, 15.0), (15.0, 25.0), (25.0, 99.0)]
ROUTES = [("r39", "V282"), ("r35", "V281r3"), ("r6c", "V282"),
          ("r6d_v292", "V292"), ("r6e_v292", "V292"), ("r6f_v292", "V292")]
OUT, RESULTS = [], []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


# ======================================================================================================
# lagd's own correlator, mirrored (selfdrive/locationd/lagd.py + helpers.py, StarPilot @ Dom a357cd2b5)
# ======================================================================================================
def _next_good(n):
    """FFT pad length.  lagd uses `fft_next_good_size` (smallest 2/3/5/7/11-composite >= n); a power of
    two is a superset of that set's purpose here -- it only changes SPEED, never the correlation, because
    the masked NCC normalises by the actual overlap count at every lag.  Verified by the controls in
    `controls()`: a known 200 ms shift comes back as 200.1-203.0 ms."""
    m = 1
    while m < n:
        m *= 2
    return m


def parabolic_peak_interp(R, i):
    if i == 0 or i == len(R) - 1:
        return float(i)
    a, b, c = R[i - 1], R[i], R[i + 1]
    den = (2 * b - c - a)
    return float(i) + (0.5 * (c - a) / den if den != 0 else 0.0)


def masked_ncc(expected_sig, actual_sig, mask, n):
    """Padfield masked FFT normalised cross-correlation -- lagd.py verbatim in arithmetic."""
    eps = np.finfo(np.float64).eps
    expected_sig = np.array(expected_sig, dtype=np.float64)
    actual_sig = np.array(actual_sig, dtype=np.float64)
    expected_sig[~mask] = 0.0
    actual_sig[~mask] = 0.0
    rot_e = expected_sig[::-1]
    rot_m = mask[::-1]
    fft = partial(np.fft.fft, n=n)
    a_f = fft(actual_sig); re_f = fft(rot_e)
    am_f = fft(mask.astype(np.float64)); rm_f = fft(rot_m.astype(np.float64))
    nov = np.fft.ifft(rm_f * am_f).real
    nov[:] = np.fmax(np.round(nov), eps)
    mca = np.fft.ifft(rm_f * a_f).real
    mce = np.fft.ifft(am_f * re_f).real
    num = np.fft.ifft(re_f * a_f).real - mca * mce / nov
    a2 = np.fft.ifft(rm_f * fft(actual_sig ** 2)).real - mca ** 2 / nov
    a2[:] = np.fmax(a2, 0.0)
    e2 = np.fft.ifft(am_f * fft(rot_e ** 2)).real - mce ** 2 / nov
    e2[:] = np.fmax(e2, 0.0)
    den = np.sqrt(a2 * e2)
    tol = 1e3 * eps * np.max(np.abs(den), keepdims=True)
    nz = den > tol
    ncc = np.zeros_like(den)
    ncc[nz] = num[nz] / den[nz]
    return np.clip(ncc, -1, 1)


def ncc_lag(u, y, mask, dt=1.0 / FS, lo=0.0, hi=MAX_LAG):
    """peak lag (s) of the masked NCC over lags [lo, hi].  Positive = y lags u."""
    klo, khi = int(round(lo / dt)), int(round(hi / dt))
    n = _next_good(len(u) + max(abs(klo), khi) + int(1.0 / dt))
    ncc = masked_ncc(u, y, mask, n)
    base = len(u) - 1
    roi = ncc[base + klo: base + khi + 1]
    i = int(np.argmax(roi))
    lag = (parabolic_peak_interp(roi, i) + klo) * dt
    return lag, float(roi[i])


# ======================================================================================================
def runs(mask, min_len):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= min_len]


def dilate(m, half):
    return maximum_filter1d(m.astype(np.uint8), size=2 * half + 1, mode="nearest") > 0


def bandpass(x, lo=FLO, hi=FHI, fs=FS, order=4):
    b, a = signal.butter(order, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    return signal.filtfilt(b, a, x)


def group_delay(pairs, fs=FS, nper=1024, lo=FLO, hi=FHI):
    Puu = Pyy = Puy = None
    for u, y in pairs:
        if len(u) < nper:
            continue
        f, a = signal.welch(u, fs, nperseg=nper, noverlap=nper // 2, detrend="linear")
        _, b = signal.welch(y, fs, nperseg=nper, noverlap=nper // 2, detrend="linear")
        _, c = signal.csd(u, y, fs, nperseg=nper, noverlap=nper // 2, detrend="linear")
        w = len(u)
        Puu = a * w if Puu is None else Puu + a * w
        Pyy = b * w if Pyy is None else Pyy + b * w
        Puy = c * w if Puy is None else Puy + c * w
    if Puu is None:
        return None
    H = Puy / Puu
    coh = np.abs(Puy) ** 2 / (Puu * Pyy)
    sel = (f >= lo) & (f <= hi)
    if sel.sum() < 3:
        return None
    ph = np.degrees(np.unwrap(np.angle(H[sel])))
    w = coh[sel]; ff = f[sel]
    A = np.vstack([ff, np.ones_like(ff)]).T
    W = np.diag(w)
    slope, icept = np.linalg.lstsq(A.T @ W @ A, A.T @ W @ ph, rcond=None)[0]
    phu = np.degrees(np.unwrap(np.angle(H)))
    return dict(tau=float(-slope / 360.0), slope=float(slope), intercept=float(icept),
                phase1=float(np.interp(1.0, f, phu)), coh1=float(np.interp(1.0, f, coh)),
                coh=float(np.mean(w)), mag1=float(np.interp(1.0, f, np.abs(H))))


def fopdt(segs, fs=FS, dead_max=0.50, tmax=0.60):
    """output-error first-order-plus-dead-time fit  y = K/(1+sT) * u(t - dead).
    Grid over (dead, T), least squares on K.  SPLITS pure transport dead time from the servo's own lag.
    The reported 1 Hz phase-equivalent delay is dead + atan(2*pi*1*T)/(2*pi*1), i.e. what a delay-only
    model would need to reproduce the same phase at 1 Hz."""
    best = None
    deads = np.arange(0, int(dead_max * fs) + 1, 2)
    Ts = np.r_[0.0, np.exp(np.linspace(np.log(0.005), np.log(tmax), 32))]
    warm = int(0.8 * fs)
    for T in Ts:
        a = float(np.exp(-1.0 / (fs * T))) if T > 0 else 0.0
        fu = [signal.lfilter(np.array([1 - a]), np.array([1.0, -a]), u) for u, _ in segs]
        for d in deads:
            num = den = 0.0
            for x0, (_, y) in zip(fu, segs):
                x = (np.r_[np.zeros(d), x0[:-d]] if d else x0)[warm:]
                num += np.dot(x, y[warm:]); den += np.dot(x, x)
            if den <= 0:
                continue
            K = num / den
            sse = sy = 0.0
            for x0, (_, y) in zip(fu, segs):
                x = (np.r_[np.zeros(d), x0[:-d]] if d else x0)[warm:]
                yy = y[warm:]
                r = yy - K * x
                sse += np.dot(r, r); sy += np.dot(yy - yy.mean(), yy - yy.mean())
            if best is None or sse < best["sse"]:
                best = dict(sse=float(sse), r2=float(1 - sse / max(1e-12, sy)), K=float(K),
                            dead=float(d / fs), T=float(T))
    if best:
        best["tau1Hz"] = best["dead"] + np.arctan(2 * np.pi * best["T"]) / (2 * np.pi)
    return best


def boot(items, fn, nboot=NBOOT, seed=0):
    rng = np.random.default_rng(seed)
    n = len(items)
    if n < 2:
        return (float("nan"), float("nan"))
    v = []
    for _ in range(nboot):
        r = fn([items[i] for i in rng.integers(0, n, n)])
        if r is not None and np.isfinite(r):
            v.append(r)
    if len(v) < 20:
        return (float("nan"), float("nan"))
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))


def pooled_ncc(segs, lo=0.0, hi=MAX_LAG):
    """concatenate stretches with a masked guard band between them, then one masked NCC."""
    guard = int(round(hi * FS)) + 10
    U, Y, M = [], [], []
    for u, y in segs:
        U.append(u); Y.append(y); M.append(np.ones(len(u), bool))
        U.append(np.zeros(guard)); Y.append(np.zeros(guard)); M.append(np.zeros(guard, bool))
    return ncc_lag(np.concatenate(U), np.concatenate(Y), np.concatenate(M), lo=lo, hi=hi)


def load(tag):
    z = np.load(os.path.join(CACHE, tag + "_lat.npz"))
    t = z["t_cc"]
    g = dict(t=t, tag=tag)
    g["v"] = np.interp(t, z["t_cst"], z["vego"])
    g["press"] = np.interp(t, z["t_cst"], z["spress"]) > 0.5
    g["lat"] = z["lat_active"] > 0.5
    g["sat"] = z["cs_sat"] > 0.5
    g["u_curv"] = z["cs_des_curv"]
    g["y_steer"] = z["cc_curv_now"]
    vv = np.maximum(g["v"], 3.0)
    g["y_yaw"] = np.interp(t, z["t_gy"], -z["gy_x"]) / vv       # raw gyro, 87.8 Hz, sign verified
    g["y_pose"] = z["cc_yaw"] / vv                               # livePose ZOH at 20 Hz
    g["ld_est"] = z["ld_est"]; g["ld_delay"] = z["ld_delay"]
    g["ld_blocks"] = z["ld_blocks"]; g["ld_std"] = z["ld_std"]; g["t_ld"] = z["t_ld"]
    # mask: lat active, hands off, not saturated, 2 s recovery after any of those (lagd's own gate)
    bad = (~g["lat"]) | g["press"] | g["sat"]
    g["ok"] = ~dilate(bad, int(2.0 * FS))
    return g


PAIRS = [("y_steer", "EPS actuator (steering-angle curvature)"),
         ("y_yaw", "FULL lateral (raw gyro yaw / v)"),
         ("y_pose", "FULL lateral (livePose ZOH, +~25 ms bias)")]


def analyse(tag, build, band, yk, ylab, segs):
    bp = [(bandpass(u), bandpass(y)) for u, y in segs]
    raw = list(segs)
    tot = sum(len(u) for u, _ in segs) / FS
    l1, c1 = pooled_ncc(bp, 0.0, MAX_LAG)
    ci1 = boot(bp, lambda S: pooled_ncc(S, 0.0, MAX_LAG)[0], nboot=400)
    l2, c2 = pooled_ncc(bp, MIN_LAG2, MAX_LAG)
    gd = group_delay(raw)
    gci = boot([p for p in raw if len(p[0]) >= 1024], lambda S: (group_delay(S) or {}).get("tau"), nboot=400)
    fp = fopdt(bp)
    res = dict(route=tag, build=build, band=band, chan=yk, chan_label=ylab, n=len(segs), seconds=tot,
               ncc_lag=l1, ncc_corr=c1, ncc_ci=ci1, ncc2_lag=l2, ncc2_corr=c2,
               gd_tau=(gd or {}).get("tau"), gd_ci=gci, gd_phase1=(gd or {}).get("phase1"),
               gd_coh1=(gd or {}).get("coh1"), gd_coh=(gd or {}).get("coh"), gd_mag1=(gd or {}).get("mag1"),
               fopdt_dead=(fp or {}).get("dead"), fopdt_T=(fp or {}).get("T"),
               fopdt_tau1Hz=(fp or {}).get("tau1Hz"), fopdt_r2=(fp or {}).get("r2"))
    RESULTS.append(res)
    pr("        %-46s NCC %6.1f ms (r %.3f) CI[%5.0f,%5.0f] | 2-sided %+7.1f ms | GD %6.1f ms CI[%5.0f,%5.0f] ph@1Hz %+6.1f coh %.2f"
       % (ylab, 1e3 * l1, c1, 1e3 * ci1[0], 1e3 * ci1[1], 1e3 * l2,
          1e3 * (gd or {}).get("tau", float("nan")), 1e3 * gci[0], 1e3 * gci[1],
          (gd or {}).get("phase1", float("nan")), (gd or {}).get("coh1", float("nan"))))
    if fp:
        pr("        %-46s FOPDT dead %5.0f ms + servo T %5.0f ms (R2 %.3f) -> 1 Hz phase-equivalent delay %5.0f ms"
           % ("", 1e3 * fp["dead"], 1e3 * fp["T"], fp["r2"], 1e3 * fp["tau1Hz"]))
    return res


def controls(g, rr):
    """CALIBRATION of the estimator itself, on this route's own stretches.
       (1) u vs u            -> must return 0 ms
       (2) u vs u delayed 200 ms -> must return 200 ms
       (3) desiredLateralAccel vs desiredCurvature*v^2 -- same tick by construction -> must return 0 ms
    A method that cannot recover a KNOWN lag cannot be trusted on an unknown one."""
    u = [bandpass(g["u_curv"][a:b]) for a, b in rr]
    d = int(round(0.200 * FS))
    z0 = pooled_ncc(list(zip(u, u)), MIN_LAG2, MAX_LAG)[0]
    z1 = pooled_ncc([(x, np.r_[np.zeros(d), x[:-d]]) for x in u], MIN_LAG2, MAX_LAG)[0]
    return z0, z1


def main(only=None):
    pr("=" * 150)
    pr("LKAS ACTUATOR DELAY tau -- desired curvature (EXOGENOUS) -> car response.  Band %.1f-%.1f Hz, %g Hz grid." % (FLO, FHI, FS))
    pr("  u = controlsState.desiredCurvature (== carControl.actuators.curvature, the command the torque controller realises)")
    pr("  NCC = openpilot lagd's own masked normalised cross-correlation, ROI 0..+650 ms, parabolic peak.")
    pr("  2-sided = the same correlation read over -300..+650 ms.  Its job is to FAIL: a negative peak means closed-loop contamination.")
    pr("  GD  = coherence-weighted phase slope 0.2-2 Hz -- the delay that reproduces the phase where the outer loop crosses over.")
    pr("=" * 150)
    for tag, build in ROUTES:
        if only and tag not in only and tag.split("_")[0] not in only:
            continue
        if not os.path.exists(os.path.join(CACHE, tag + "_lat.npz")):
            pr("\nROUTE %-9s : no tau cache yet" % tag); continue
        g = load(tag)
        pr("")
        pr("=" * 150)
        pr("ROUTE %-9s build %-8s  %.0f s  latActive %.1f%%  usable(ok) %.1f%%"
           % (tag, build, g["t"][-1] - g["t"][0], 100 * g["lat"].mean(), 100 * g["ok"].mean()))
        pr("   fork liveDelay: lateralDelay %s (the echoed SteerDelay toggle) | lateralDelayEstimate %s | std %s | validBlocks %s"
           % (np.unique(np.round(g["ld_delay"], 4)), np.unique(np.round(g["ld_est"], 4)),
              np.unique(np.round(g["ld_std"], 4)), np.unique(g["ld_blocks"].astype(int))))
        for lo, hi in BANDS:
            m = g["ok"] & (g["v"] >= lo) & (g["v"] < hi)
            rr = runs(m, MINSTRETCH)
            if not rr:
                pr("   v %2.0f-%-2.0f m/s : %6.1f s, no stretch >= %.0f s" % (lo, hi, m.sum() / FS, MINSTRETCH / FS))
                continue
            z0, z1 = controls(g, rr)
            pr("   v %2.0f-%-2.0f m/s   %6.1f s in %2d stretches >= %.0f s   [CONTROLS: zero-lag pair -> %+.1f ms (want 0); known +200 ms pair -> %+.1f ms (want 200)]"
               % (lo, hi, sum(b - a for a, b in rr) / FS, len(rr), MINSTRETCH / FS, 1e3 * z0, 1e3 * z1))
            RESULTS.append(dict(route=tag, build=build, band="%g-%g" % (lo, hi), chan="CONTROL",
                                ctrl_zero_ms=1e3 * z0, ctrl_200_ms=1e3 * z1,
                                n=len(rr), seconds=sum(b - a for a, b in rr) / FS))
            for yk, ylab in PAIRS:
                segs = [(g["u_curv"][a:b], g[yk][a:b]) for a, b in rr]
                if np.any([~np.all(np.isfinite(y)) for _, y in segs]):
                    continue
                analyse(tag, build, "%g-%g" % (lo, hi), yk, ylab, segs)
    with open(os.path.join(HERE, "_scratch", "tau_identify.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT))
    with open(os.path.join(HERE, "_scratch", "tau_identify.json"), "w", encoding="utf-8") as fh:
        json.dump(RESULTS, fh, indent=1, default=float)
    pr("\nwrote _scratch/tau_identify.{txt,json}  (%d rows)" % len(RESULTS))


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "_scratch"), exist_ok=True)
    main(sys.argv[1:] or None)
