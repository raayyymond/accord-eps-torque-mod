# -*- coding: utf-8 -*-
"""tau_lagd_replicate.py -- run the FORK'S OWN lateral-delay estimator offline, per speed band and per
build.  Subagent taumeasure, 2026-09-13.  Analysis only: builds nothing, sends nothing, flashes nothing.

WHY.  `liveDelay.lateralDelayEstimate` is a real identification (the toggle only overrides
`lateralDelay`, see lagd.py:236-248), but the fork's estimator is gated at **MIN_VEGO = 15.0 m/s**
(lagd.py:25).  It therefore says NOTHING about the 3-8 m/s band where the adversary's worst cell sits.
This replays lagd's exact algorithm -- its signals, its okay-gates, its 20 Hz rate, its masked NCC, its
block average -- with MIN_VEGO replaced by a per-band window, so the fork's own method can be read where
the fork refuses to look.  Everything else is left at the fork's constants.

Mirrored from StarPilot @ Dom a357cd2b5, selfdrive/locationd/lagd.py (read 2026-09-13):
  la_desired = controlsState.desiredCurvature * vEgo^2          (lagd.py:284)
  la_actual  = calibrated livePose yaw rate * vEgo              (lagd.py:285)
  okay       = latActive & !steeringPressed & !saturated & fast & turning & has_recovered
               & calib_valid & sensors_valid & la_valid         (lagd.py:306-307)
  la_valid   = |la_actual| <= 2.0 and |la_desired - la_actual| <= 0.6      (MAX_LAT_ACCEL / DIFF)
  recovery   = 2.0 s after any of the above going bad           (MIN_RECOVERY_BUFFER_SEC)
  window     = 60 s, needs >= 25 s okay, needs actual range >= 0.5 m/s^2
  estimate   = masked NCC over lags 0..0.65 s, accepted only if corr >= 0.95 and confidence >= 0.7
  block avg  = 50 blocks x 100 updates

DEVIATIONS, all deliberate and each stated in the output:
  * MIN_VEGO -> the band's own lower edge (the whole point).
  * The block-average SEED is dropped: the fork seeds all 50 blocks with the previous route's cached
    value, which is why r39's estimate is a single frozen number for 948 s.  Here only ACCEPTED windows
    enter, so every number below is measured on THIS route.
  * The yaw channel is offered twice: lagd's livePose (for comparability) and the RAW GYRO (87.8 Hz,
    verified -gyro_x = calibrated yaw to slope -1.0046 / corr -0.9965), which does not carry the
    livePose estimator's own lag.

Run: python rlog-tools/studies/grind/tau_lagd_replicate.py
Writes _scratch/tau_lagd_replicate.{txt,json}
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "tau")
sys.path.insert(0, HERE)
from tau_identify import masked_ncc, parabolic_peak_interp, _next_good  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# --- the fork's constants, lagd.py:19-38 --------------------------------------------------------------
BLOCK_SIZE, BLOCK_NUM = 100, 50
MOVING_WINDOW_SEC, MIN_OKAY_WINDOW_SEC, MIN_RECOVERY_BUFFER_SEC = 60.0, 25.0, 2.0
MAX_YAW_RATE_SANITY_CHECK, MIN_NCC, MAX_LAG, MAX_LAT_ACCEL = 1.0, 0.95, 0.65, 2.0
MAX_LAT_ACCEL_DIFF, MIN_LAT_ACCEL_RANGE, MIN_CONFIDENCE = 0.6, 0.5, 0.7
CORR_BORDER_OFFSET, LAG_CANDIDATE_CORR_THRESHOLD, SMOOTH_K, SMOOTH_SIGMA = 5, 0.9, 5, 1.0
DT = 0.05                                   # livePose is 20 Hz; lagd runs on that clock

BANDS = [(0.0, 3.0), (3.0, 8.0), (8.0, 15.0), (15.0, 25.0), (25.0, 99.0), (15.0, 99.0)]
ROUTES = [("r35", "V281r3"), ("r39", "V282"), ("r6c", "V282"),
          ("r6d_v292", "V292"), ("r6e_v292", "V292"), ("r6f_v292", "V292")]
OUT, RESULTS = [], []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def masked_symmetric_moving_average(x, mask, k=SMOOTH_K, sigma=SMOOTH_SIGMA):
    pad = k // 2
    i = np.arange(k) - pad
    w = np.exp(-0.5 * (i / sigma) ** 2); w /= w.sum()
    xp = np.pad(x * mask, pad, mode="edge"); mp = np.pad(mask.astype(float), pad, mode="edge")
    num = np.convolve(xp, w, mode="valid"); den = np.convolve(mp, w, mode="valid")
    return np.divide(num, den, out=np.full_like(num, np.nan, dtype=np.float64), where=den != 0)


def actuator_delay(expected, actual, mask, dt=DT, max_lag=MAX_LAG):
    """lagd.py:333-363, mirrored."""
    max_lag_samples = int(round(max_lag / dt))
    one_sec = int(round(1.0 / dt))
    n = _next_good(len(expected) + max(max_lag_samples, one_sec))
    ncc = masked_ncc(expected, actual, mask, n)
    base = len(expected) - 1
    roi = ncc[base: base + max_lag_samples]
    thr_roi = ncc[base: base + one_sec]
    conf_roi = ncc[base - CORR_BORDER_OFFSET: base + one_sec + CORR_BORDER_OFFSET]
    i = int(np.argmax(roi))
    corr = float(roi[i])
    lag = parabolic_peak_interp(roi, i) * dt
    thr = (thr_roi.max() - thr_roi.min()) * LAG_CANDIDATE_CORR_THRESHOLD + thr_roi.min()
    good = conf_roi >= thr
    edges = np.diff(good.astype(int), prepend=0, append=0)
    starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0] - 1
    if len(starts) == 0:
        return lag, corr, 0.0
    run = np.searchsorted(starts, i + CORR_BORDER_OFFSET, side="right") - 1
    run = int(np.clip(run, 0, len(starts) - 1))
    width = ends[run] - starts[run] + 1
    return lag, corr, float(np.clip(1 - width * dt, 0, 1))


def load20(tag, yaw_src):
    z = np.load(os.path.join(CACHE, tag + "_lat.npz"))
    t = np.arange(z["t_cc"][0], z["t_cc"][-1], DT)
    g = dict(t=t)
    g["v"] = np.interp(t, z["t_cst"], z["vego"])
    g["press"] = np.interp(t, z["t_cst"], z["spress"]) > 0.5
    g["lat"] = np.interp(t, z["t_cc"], z["lat_active"]) > 0.5
    g["sat"] = np.interp(t, z["t_cs"], z["cs_sat"]) > 0.5
    g["dc"] = np.interp(t, z["t_cs"], z["cs_des_curv"])
    if yaw_src == "livePose":
        g["yaw"] = np.interp(t, z["t_lp"], z["lp_wz"])
        g["pose_ok"] = np.interp(t, z["t_lp"], z["lp_ok"] * z["lp_valid"]) > 0.5
    else:
        g["yaw"] = np.interp(t, z["t_gy"], -z["gy_x"])
        g["pose_ok"] = np.ones(len(t), bool)
    return g


def run_band(g, vlo, vhi):
    """lagd's okay gate with MIN_VEGO -> [vlo, vhi), then its 60 s sliding window and block average."""
    la_des = g["dc"] * g["v"] ** 2
    la_act = g["yaw"] * g["v"]
    fast = (g["v"] >= vlo) & (g["v"] < vhi)
    sensors_valid = g["pose_ok"] & (np.abs(g["yaw"]) < MAX_YAW_RATE_SANITY_CHECK)
    la_valid = (np.abs(la_act) <= MAX_LAT_ACCEL) & (np.abs(la_des - la_act) <= MAX_LAT_ACCEL_DIFF)
    bad = (~g["lat"]) | g["press"] | g["sat"] | (~sensors_valid) | (~la_valid)
    # 2 s recovery buffer: a sample is only okay if nothing was bad in the preceding 2 s
    nrec = int(MIN_RECOVERY_BUFFER_SEC / DT)
    recovered = np.ones(len(bad), bool)
    c = 0
    for i, b in enumerate(bad):
        c = 0 if b else c + 1
        recovered[i] = c > nrec
    okay = (~bad) & recovered & fast
    W = int(MOVING_WINDOW_SEC / DT); need = int(MIN_OKAY_WINDOW_SEC / DT)
    accepted, rejected = [], dict(short=0, corr=0, conf=0, range=0)
    step = int(5.0 / DT)                                  # a fresh window every 5 s
    for s in range(0, len(okay) - W, step):
        sl = slice(s, s + W)
        m = okay[sl]
        if m.sum() < need:
            rejected["short"] += 1; continue
        d = masked_symmetric_moving_average(la_des[sl], m)
        a = masked_symmetric_moving_average(la_act[sl], m)
        if not np.all(np.isfinite(d)) or not np.all(np.isfinite(a)):
            rejected["short"] += 1; continue
        if a[m].max() - a[m].min() < MIN_LAT_ACCEL_RANGE:
            rejected["range"] += 1; continue
        lag, corr, conf = actuator_delay(d, a, m)
        if corr < MIN_NCC:
            rejected["corr"] += 1; continue
        if conf < MIN_CONFIDENCE:
            rejected["conf"] += 1; continue
        accepted.append((lag, corr, conf))
    return accepted, rejected, okay


def main():
    pr("=" * 140)
    pr("THE FORK'S OWN LATERAL-DELAY ESTIMATOR, REPLAYED PER SPEED BAND (lagd.py mirrored; MIN_VEGO replaced by the band)")
    pr("  Every constant except MIN_VEGO is the fork's.  Only ACCEPTED windows enter -- no seed carried in, so each")
    pr("  number is measured on THAT route.  Window 60 s stepped 5 s; accept needs corr >= 0.95 and confidence >= 0.7.")
    pr("=" * 140)
    for yaw_src in ("livePose", "rawgyro"):
        pr("")
        pr("#" * 140)
        pr("### RESPONSE CHANNEL: %s%s" % (yaw_src, "   (lagd's own input)" if yaw_src == "livePose"
                                           else "   (87.8 Hz raw gyro -- no estimator lag)"))
        pr("#" * 140)
        pr("%-10s %-8s %-10s %6s %7s | %8s %8s %8s %8s | %s"
           % ("route", "build", "band m/s", "okay_s", "n_acc", "median", "mean", "p16", "p84", "rejected (short/corr/conf/range)"))
        for tag, build in ROUTES:
            if not os.path.exists(os.path.join(CACHE, tag + "_lat.npz")):
                continue
            g = load20(tag, yaw_src)
            for vlo, vhi in BANDS:
                acc, rej, okay = run_band(g, vlo, vhi)
                lags = np.array([a[0] for a in acc])
                okay_s = okay.sum() * DT
                if len(lags):
                    row = "%8.3f %8.3f %8.3f %8.3f" % (np.median(lags), lags.mean(),
                                                       np.percentile(lags, 16), np.percentile(lags, 84))
                else:
                    row = "%8s %8s %8s %8s" % ("--", "--", "--", "--")
                pr("%-10s %-8s %-10s %6.0f %7d | %s | %d/%d/%d/%d"
                   % (tag, build, "%g-%g" % (vlo, vhi), okay_s, len(lags), row,
                      rej["short"], rej["corr"], rej["conf"], rej["range"]))
                RESULTS.append(dict(route=tag, build=build, yaw_src=yaw_src, band="%g-%g" % (vlo, vhi),
                                    okay_s=float(okay_s), n_accepted=len(lags),
                                    median=float(np.median(lags)) if len(lags) else None,
                                    mean=float(lags.mean()) if len(lags) else None,
                                    p16=float(np.percentile(lags, 16)) if len(lags) else None,
                                    p84=float(np.percentile(lags, 84)) if len(lags) else None,
                                    rejected=rej))
    with open(os.path.join(HERE, "_scratch", "tau_lagd_replicate.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT))
    with open(os.path.join(HERE, "_scratch", "tau_lagd_replicate.json"), "w", encoding="utf-8") as fh:
        json.dump(RESULTS, fh, indent=1, default=float)


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "_scratch"), exist_ok=True)
    main()
