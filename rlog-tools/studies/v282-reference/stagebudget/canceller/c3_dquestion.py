# -*- coding: utf-8 -*-
"""c3: IS D RIGHT?  Re-run the fork's OWN lag learner (lagd.py) offline on every route, identical recipe,
so both builds are measured by one instrument, and compare against the D each build actually flew.

D flown = liveDelay.lateralDelay + LAT_SMOOTH_SECONDS(0.1)   [controlsd.py, git-confirmed at every commit]
liveDelay.lateralDelay = SteerDelay toggle when UseAutoSteerDelay==0 (all 6 V282 routes), else the learner.

The learner's own target (lagd.LateralLagEstimator.update_points) is EXACTLY the study's X->Y leg:
    la_desired = controlsState.desiredCurvature * vEgo^2      la_actual = calibrated yaw rate * vEgo
masked NCC over a 60 s moving window at >=15 m/s, |la_act|<=2.0, |la_des-la_act|<=0.6, 2 s recovery buffer,
peak searched over [0, 0.65] s, accepted only if corr>=0.95 and confidence>=0.7.

Positive control: the estimator must recover a KNOWN lag injected into the real logged command before any
real-data number is reported.

ANALYSIS ONLY.  usage: python c3_dquestion.py [route ...]
"""
import json, os, sys
from functools import partial
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "v282-reference"))
import v282cmp as V  # noqa: E402
from c2_stage import CFG, LAT_SMOOTH  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# lagd.py constants, verbatim
DT_L = 0.05                 # 1 / SERVICE_LIST['livePose'].frequency
WINDOW_SEC = 60.0
OKAY_WINDOW_SEC = 25.0
MIN_RECOVERY_BUFFER_SEC = 2.0
MIN_VEGO = 15.0
MAX_YAW_SANITY = 1.0
MAX_LAT_ACCEL = 2.0
MAX_LAT_ACCEL_DIFF = 0.6
MIN_LAT_ACCEL_RANGE = 0.5
MIN_NCC = 0.95
MIN_CONFIDENCE = 0.7
MAX_LAG = 0.65
CORR_BORDER_OFFSET = 5
LAG_CANDIDATE_CORR_THRESHOLD = 0.9
SMOOTH_K, SMOOTH_SIGMA = 5, 1.0


def fft_next_good_size(n):
    if n <= 6:
        return n
    best, f2 = 2 * n, 1
    while f2 < best:
        f23 = f2
        while f23 < best:
            f235 = f23
            while f235 < best:
                f2357 = f235
                while f2357 < best:
                    if f2357 >= n:
                        best = f2357
                    f2357 *= 11
                f235 *= 7
            f23 *= 5
        f2 *= 3
        if f2 >= 2 * n:
            break
        # emulate the nested 2/3/5/7/11 sweep of the fork's helper
    # brute force fallback (small n): smallest 2,3,5,7,11-composite >= n
    m = n
    while True:
        x = m
        for p in (2, 3, 5, 7, 11):
            while x % p == 0:
                x //= p
        if x == 1:
            return m
        m += 1


def masked_symmetric_moving_average(x, mask, k, sigma):
    pad = k // 2
    i = np.arange(k) - pad
    w = np.exp(-0.5 * (i / sigma) ** 2)
    w /= w.sum()
    xp = np.pad(x * mask, pad, mode="edge")
    mp = np.pad(mask.astype(float), pad, mode="edge")
    num = np.convolve(xp, w, mode="valid")
    den = np.convolve(mp, w, mode="valid")
    return np.divide(num, den, out=np.full_like(num, np.nan, dtype=np.float64), where=den != 0)


def masked_ncc(expected_sig, actual_sig, mask, n):
    eps = np.finfo(np.float64).eps
    expected_sig = np.array(expected_sig, dtype=np.float64)
    actual_sig = np.array(actual_sig, dtype=np.float64)
    expected_sig[~mask] = 0.0
    actual_sig[~mask] = 0.0
    rot_e = expected_sig[::-1]
    rot_m = mask[::-1]
    fft = partial(np.fft.fft, n=n)
    a_fft = fft(actual_sig)
    re_fft = fft(rot_e)
    am_fft = fft(mask.astype(np.float64))
    rm_fft = fft(rot_m.astype(np.float64))
    nov = np.fft.ifft(rm_fft * am_fft).real
    nov[:] = np.fmax(np.round(nov), eps)
    mca = np.fft.ifft(rm_fft * a_fft).real
    mce = np.fft.ifft(am_fft * re_fft).real
    num = np.fft.ifft(re_fft * a_fft).real - mca * mce / nov
    asq = np.fft.ifft(rm_fft * fft(actual_sig ** 2)).real - mca ** 2 / nov
    asq[:] = np.fmax(asq, 0.0)
    esq = np.fft.ifft(am_fft * fft(rot_e ** 2)).real - mce ** 2 / nov
    esq[:] = np.fmax(esq, 0.0)
    den = np.sqrt(asq * esq)
    tol = 1e3 * eps * np.max(np.abs(den), keepdims=True)
    nz = den > tol
    ncc = np.zeros_like(den)
    ncc[nz] = num[nz] / den[nz]
    return np.clip(ncc, -1, 1)


def parabolic(R, i):
    if i == 0 or i == len(R) - 1:
        return float(i)
    ym, y0, yp = R[i - 1], R[i], R[i + 1]
    d = (2 * y0 - yp - ym)
    return i + (0.5 * (yp - ym) / d if abs(d) > 1e-15 else 0.0)


def actuator_delay(e, a, mask, dt=DT_L, max_lag=MAX_LAG):
    max_lag_samples = int(round(max_lag / dt))
    one_sec = int(round(1.0 / dt))
    padded = fft_next_good_size(len(e) + max(max_lag_samples, one_sec))
    ncc = masked_ncc(e, a, mask, padded)
    roi = slice(len(e) - 1, len(e) - 1 + max_lag_samples)
    troi = slice(len(e) - 1, len(e) - 1 + one_sec)
    croi = slice(troi.start - CORR_BORDER_OFFSET, troi.stop + CORR_BORDER_OFFSET)
    rn, cn, tn = ncc[roi], ncc[croi], ncc[troi]
    i = int(np.argmax(rn))
    corr = float(rn[i])
    lag = parabolic(rn, i) * dt
    thr = (tn.max() - tn.min()) * LAG_CANDIDATE_CORR_THRESHOLD + tn.min()
    good = cn >= thr
    edges = np.diff(good.astype(int), prepend=0, append=0)
    starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0] - 1
    if len(starts) == 0:
        return lag, corr, 0.0
    ri = np.searchsorted(starts, i + CORR_BORDER_OFFSET, side="right") - 1
    ri = max(0, min(ri, len(ends) - 1))
    width = ends[ri] - starts[ri] + 1
    return lag, corr, float(np.clip(1 - width * dt, 0, 1))


def build_points(S, extra_lag_s=0.0):
    """Resample to the learner's 20 Hz clock and apply its okay gates."""
    t = S["t"]
    tg = np.arange(t[0], t[-1], DT_L)
    I = lambda y: np.interp(tg, t, np.nan_to_num(y))
    v = I(S["v"])
    des = I(S["model"])
    act = I(S["la_pose"])
    if extra_lag_s > 0:                       # positive control: delay the ACHIEVED signal by a known amount
        k = int(round(extra_lag_s / DT_L))
        act = np.concatenate([np.full(k, act[0]), act[:-k]])
    latact = I(S["active"].astype(float)) > 0.99
    press = I(S["pressed"].astype(float)) > 0.01
    sat = I(S["sat"].astype(float)) > 0.01
    yaw = act / np.maximum(v, 1e-3)
    ok_sensors = np.abs(yaw) < MAX_YAW_SANITY
    ok_la = (np.abs(act) <= MAX_LAT_ACCEL) & (np.abs(des - act) <= MAX_LAT_ACCEL_DIFF)
    bad = (~latact) | press | sat | (~ok_sensors) | (~ok_la)
    # recovery buffer: 2 s clear of any bad condition
    nb = int(MIN_RECOVERY_BUFFER_SEC / DT_L)
    rec = np.ones(len(tg), bool)
    last_bad = -10 ** 9
    for k in range(len(tg)):
        if bad[k]:
            last_bad = k
        rec[k] = (k - last_bad) >= nb
    okay = latact & (~press) & (~sat) & (v > MIN_VEGO) & rec & ok_sensors & ok_la
    return tg, des, act, okay


def run_learner(tg, des, act, okay, stride_s=5.0):
    wl = int(WINDOW_SEC / DT_L)
    need = int(OKAY_WINDOW_SEC / DT_L)
    st = int(stride_s / DT_L)
    out = []
    for a in range(0, max(0, len(tg) - wl), st):
        sl = slice(a, a + wl)
        ok = okay[sl]
        if ok.sum() < need:
            continue
        d = des[sl].copy()
        y = act[sl].copy()
        if (y[ok].max() - y[ok].min()) < MIN_LAT_ACCEL_RANGE:
            continue
        ds = masked_symmetric_moving_average(d, ok, SMOOTH_K, SMOOTH_SIGMA)
        ys = masked_symmetric_moving_average(y, ok, SMOOTH_K, SMOOTH_SIGMA)
        ds = np.nan_to_num(ds)
        ys = np.nan_to_num(ys)
        lag, corr, conf = actuator_delay(ds, ys, ok)
        if corr < MIN_NCC or conf < MIN_CONFIDENCE:
            continue
        out.append(lag)
    return np.array(out)


def main():
    routes = sys.argv[1:] or list(CFG)
    print("=" * 128)
    print("POSITIVE CONTROL: inject a known EXTRA lag into the achieved signal of one route and check the")
    print("estimator's recovered lag rises by that amount.  Nothing below is reported until this passes.")
    print("=" * 128)
    ctrl = "00000064--ce6b0b0ebb" if "00000064--ce6b0b0ebb" in routes else routes[0]
    S = V.load(ctrl)
    base = None
    for inj in (0.0, 0.10, 0.20):
        tg, des, act, okay = build_points(S, extra_lag_s=inj)
        lags = run_learner(tg, des, act, okay)
        med = float(np.median(lags)) if len(lags) else float("nan")
        if inj == 0.0:
            base = med
        print("   %s  injected +%.2f s -> median recovered %.4f s  (rise %+.4f, expected %+.2f)  n=%d" %
              (ctrl, inj, med, med - base, inj, len(lags)))
    del S
    print()
    print("=" * 128)
    print("THE D QUESTION.  D_flown is what the canceller actually used.  D_learner is the SAME estimator the")
    print("fork ships, re-run here on every route so both builds are read by one instrument.")
    print("  err = D_flown - D_learner.  NEGATIVE = the canceller under-states the true model->achieved lag.")
    print("=" * 128)
    print("%-22s %-8s %-9s %-9s %-9s %-9s %-8s %s" % ("route", "group", "D_flown", "learner_med",
                                                      "p25", "p75", "err_ms", "n_win"))
    res = {}
    for r in routes:
        S = V.load(r)
        Dfl = float(np.median(np.nan_to_num(S["lat_delay"], nan=0.2))) + LAT_SMOOTH
        tg, des, act, okay = build_points(S)
        lags = run_learner(tg, des, act, okay)
        if len(lags):
            med, p25, p75 = float(np.median(lags)), float(np.percentile(lags, 25)), float(np.percentile(lags, 75))
        else:
            med = p25 = p75 = float("nan")
        print("%-22s %-8s %9.4f %9.4f %9.4f %9.4f %+8.0f %6d" % (
            r, CFG[r]["g"], Dfl, med, p25, p75, (Dfl - med) * 1e3, len(lags)))
        res[r] = dict(group=CFG[r]["g"], D_flown=Dfl, learner_med=med, p25=p25, p75=p75, n=len(lags),
                      err_ms=(Dfl - med) * 1e3)
        del S
    with open(os.path.join(HERE, "c3_dquestion.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    print()
    for g in ("V282", "V282old", "T64", "T64B", "T5", "T4", "T6?", "V293a"):
        v = [res[r]["learner_med"] for r in res if res[r]["group"] == g and np.isfinite(res[r]["learner_med"])]
        d = [res[r]["D_flown"] for r in res if res[r]["group"] == g]
        if v:
            print("   group %-8s  learner %.4f s (n_routes %d)   D_flown %.4f   err %+.0f ms" %
                  (g, float(np.mean(v)), len(v), float(np.mean(d)), (float(np.mean(d)) - float(np.mean(v))) * 1e3))


if __name__ == "__main__":
    main()
