#!/usr/bin/env python3
"""v89_a2_rate_mechanism.py -- WHAT KIND of rate dependence is the ratchet?

v89_a1 established, on route 73 (V88): the 6-9 Hz column-torque energy scales with
|steering rate| with a speed-partialled slope of +0.490 [+0.218, +0.906], perm p = 0.0000,
while grind #1's 18-22 Hz band does NOT (+0.039, p = 0.63).

That leaves three mechanisms, and they make DIFFERENT predictions:

  M1  POSITION QUANTIZATION / spatial ratchet (a cogging or step artefact)
      f0 = |rate| / quantum   ->  f0 RISES PROPORTIONALLY with rate.
      Amplitude roughly rate-independent per event.

  M2  RESONANCE EXCITED BY RATE-PROPORTIONAL BROADBAND INPUT
      f0 FIXED (it is the mode), amplitude proportional to excitation.
      The envelope should follow |rate| with a short, causal lag.

  M3  COMMON CAUSE (driver effort / road input moves every band at once)
      Every band responds equally; the negative control is not a control.

TESTS
  T1  f0 vs |rate|            -- M1 predicts slope ~ 1 in log-log; M2 predicts ~ 0
  T2  band slope CONTRAST     -- ratchet slope minus negative-control slope, paired bootstrap
  T3  envelope cross-correlation at 100 Hz: does |rate| LEAD the 6-9 Hz envelope?
                                 A control: the same against the negative-control envelope.
  T4  engaged vs manual at matched |rate|, POOLED over every cache that has one
  T5  the MACRO axis -- angle excursion as a predictor once rate is partialled out
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.signal import butter, hilbert, sosfiltfilt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_cache_r73" / "v89_a2_rate_mechanism.json"
RNG = np.random.default_rng(890209)

NW, HOP = 256, 128
CIRC_LO, CIRC_HI = 2.073, 2.088


def order_hits(v, lo, hi, nmax=6):
    if v <= 0.05:
        return False
    for circ in (CIRC_LO, CIRC_HI):
        for n in range(1, nmax + 1):
            if lo <= n * v / circ < hi:
                return True
    return False


def envelope(x, fs, lo, hi):
    """Analytic envelope of x band-limited to [lo, hi]."""
    sos = butter(4, [lo / (fs / 2), hi / (fs / 2)], btype="band", output="sos")
    return np.abs(hilbert(sosfiltfilt(sos, x - np.mean(x))))


def spec(x, fs):
    x = x - x.mean()
    w = np.hanning(len(x))
    X = np.fft.rfft(x * w)
    f = np.fft.rfftfreq(len(x), 1.0 / fs)
    p = (np.abs(X) ** 2) / (np.sum(w ** 2) * fs)
    p[1:-1] *= 2.0
    return f, p


def band_rms(f, p, lo, hi):
    m = (f >= lo) & (f < hi)
    return float(np.sqrt(np.sum(p[m]) * (f[1] - f[0])))


def peak_in(f, p, lo, hi):
    """Argmax frequency and prominence (peak / median of the surrounding band)."""
    m = (f >= lo) & (f < hi)
    if not m.any():
        return float("nan"), float("nan")
    pm, fm = p[m], f[m]
    k = int(np.argmax(pm))
    floor = np.median(pm)
    return float(fm[k]), float(pm[k] / floor if floor > 0 else np.nan)


# ------------------------------------------------------------------ T1 / T2 / T5
def windows(z):
    t = z["t"]
    fs = 1.0 / float(np.median(np.diff(t)))
    tq, ang, rate = z["tq"].astype(float), z["ang"].astype(float), z["rate_c"].astype(float)
    v, sstat = z["cs_v"].astype(float), z["sstat"].astype(float)
    eng = z["cc_lat"].astype(float) > 0.5
    seg = z["seg"].astype(int)
    rows = []
    for s in range(0, len(t) - NW + 1, HOP):
        sl = slice(s, s + NW)
        e = eng[sl].mean()
        if not (e > 0.98 or e < 0.02):
            continue
        if (sstat[sl] != 0).any() or not np.isfinite(tq[sl]).all():
            continue
        f, p = spec(tq[sl], fs)
        vm = float(np.median(v[sl]))
        f0, prom = peak_in(f, p, 6.0, 9.5)
        rows.append({
            "i0": s, "seg": int(np.median(seg[sl])), "engaged": e > 0.98,
            "v_med": vm, "rate_med": float(np.median(np.abs(rate[sl]))),
            "rate_p90": float(np.percentile(np.abs(rate[sl]), 90)),
            "ang_ptp": float(np.ptp(ang[sl])),
            "e_6-9": band_rms(f, p, 6.0, 9.0),
            "e_18-22": band_rms(f, p, 18.0, 22.0),
            "e_32-38": band_rms(f, p, 32.0, 38.0),
            "f0": f0, "prom": prom,
            "veto69": order_hits(vm, 6.0, 9.5),
        })
    return fs, rows


def blocks_of(rows):
    b, cur, last = [], 0, None
    for r in rows:
        if last is not None and (r["seg"] != last["seg"] or r["i0"] - last["i0"] > 3 * HOP):
            cur += 1
        b.append(cur)
        last = r
    return np.array(b)


def main():
    z = np.load(ROOT / "_cache_r73" / "r73.npz", allow_pickle=True)
    fs, rows = windows(z)
    rep = {"fs": fs}
    eng = [r for r in rows if r["engaged"]]

    # ---------------------------------------------------------------- T1
    print("=" * 78)
    print("T1  DOES THE RATCHET FREQUENCY MOVE WITH |steer rate|?")
    print("    M1 quantization predicts log-log slope ~ +1.0 ; M2 resonance predicts ~ 0")
    print("=" * 78)
    sel = [r for r in eng if not r["veto69"] and r["rate_med"] > 1.0
           and r["prom"] > 4.0 and np.isfinite(r["f0"])]
    lr = np.log(np.array([r["rate_med"] for r in sel]))
    lf = np.log(np.array([r["f0"] for r in sel]))
    X = np.column_stack([np.ones_like(lr), lr])
    b = np.linalg.lstsq(X, lf, rcond=None)[0]
    blk = blocks_of(sel)
    uq = np.unique(blk)
    dr = []
    for _ in range(3000):
        pick = RNG.choice(uq, size=len(uq), replace=True)
        idx = np.concatenate([np.where(blk == g)[0] for g in pick])
        if len(np.unique(lr[idx])) < 3:
            continue
        dr.append(np.linalg.lstsq(X[idx], lf[idx], rcond=None)[0][1])
    ci = [float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))]
    print(f"  n={len(sel)} windows, {len(uq)} blocks, |rate| span "
          f"{np.exp(lr.min()):.1f}-{np.exp(lr.max()):.1f} deg/s ({np.exp(lr.max()-lr.min()):.0f}x)")
    print(f"  d(log f0)/d(log |rate|) = {b[1]:+.4f}  [{ci[0]:+.4f}, {ci[1]:+.4f}]")
    print(f"  f0 median = {np.median(np.exp(lf)):.2f} Hz   "
          f"corr(log rate, log f0) = {np.corrcoef(lr, lf)[0,1]:+.3f}")
    for lo, hi in [(1, 3), (3, 8), (8, 20), (20, 1e9)]:
        bb = [r for r in sel if lo <= r["rate_med"] < hi]
        if len(bb) >= 3:
            print(f"    |rate| {lo:3.0f}-{hi if hi<1e8 else 999:3.0f} deg/s  n={len(bb):3d}  "
                  f"f0 med={np.median([r['f0'] for r in bb]):5.2f} Hz  "
                  f"e_6-9={np.median([r['e_6-9'] for r in bb]):7.1f}")
    rep["T1"] = {"slope": float(b[1]), "ci": ci, "n": len(sel),
                 "f0_median": float(np.median(np.exp(lf))),
                 "rate_span": float(np.exp(lr.max() - lr.min()))}
    verdict = ("M1 QUANTIZATION" if ci[0] > 0.5 else
               "M2 FIXED-FREQUENCY RESONANCE" if ci[1] < 0.3 else "AMBIGUOUS")
    print(f"  => {verdict}")
    rep["T1"]["verdict"] = verdict

    # ---------------------------------------------------------------- T2
    print("\n" + "=" * 78)
    print("T2  BAND-SLOPE CONTRAST -- ratchet slope MINUS negative-control slope, paired")
    print("=" * 78)
    sel2 = [r for r in eng if not r["veto69"] and r["rate_med"] > 0.5 and r["v_med"] > 0.3]
    y69 = np.log([r["e_6-9"] for r in sel2])
    y32 = np.log([r["e_32-38"] for r in sel2])
    y18 = np.log([r["e_18-22"] for r in sel2])
    lr2 = np.log([r["rate_med"] for r in sel2])
    lv2 = np.log([r["v_med"] for r in sel2])
    X2 = np.column_stack([np.ones_like(lr2), lr2, lv2])
    fit = lambda y, Xm=X2: np.linalg.lstsq(Xm, y, rcond=None)[0][1]
    d_obs = fit(y69) - fit(y32)
    d18 = fit(y69) - fit(y18)
    blk2 = blocks_of(sel2)
    uq2 = np.unique(blk2)
    dd, dd18 = [], []
    for _ in range(3000):
        pick = RNG.choice(uq2, size=len(uq2), replace=True)
        idx = np.concatenate([np.where(blk2 == g)[0] for g in pick])
        try:
            dd.append(fit(y69[idx], X2[idx]) - fit(y32[idx], X2[idx]))
            dd18.append(fit(y69[idx], X2[idx]) - fit(y18[idx], X2[idx]))
        except np.linalg.LinAlgError:
            pass
    ci_d = [float(np.percentile(dd, 2.5)), float(np.percentile(dd, 97.5))]
    ci_d18 = [float(np.percentile(dd18, 2.5)), float(np.percentile(dd18, 97.5))]
    print(f"  n={len(sel2)}  slope(6-9)={fit(y69):+.3f}  slope(18-22)={fit(y18):+.3f}  "
          f"slope(32-38)={fit(y32):+.3f}")
    print(f"  ratchet - negctrl = {d_obs:+.3f} [{ci_d[0]:+.3f}, {ci_d[1]:+.3f}]  "
          f"{'EXCLUDES 0 => band-specific' if ci_d[0] > 0 else 'includes 0 => COMMON CAUSE not excluded'}")
    print(f"  ratchet - grind#1 = {d18:+.3f} [{ci_d18[0]:+.3f}, {ci_d18[1]:+.3f}]  "
          f"{'EXCLUDES 0' if ci_d18[0] > 0 else 'includes 0'}")
    rep["T2"] = {"slope_69": fit(y69), "slope_18": fit(y18), "slope_32": fit(y32),
                 "d_negctrl": float(d_obs), "ci_negctrl": ci_d,
                 "d_grind1": float(d18), "ci_grind1": ci_d18, "n": len(sel2)}

    # ---------------------------------------------------------------- T3
    print("\n" + "=" * 78)
    print("T3  ENVELOPE CROSS-CORRELATION at 100 Hz -- does |rate| LEAD the 6-9 Hz envelope?")
    print("=" * 78)
    t = z["t"]
    eng_m = z["cc_lat"].astype(float) > 0.5
    ok = eng_m & (z["sstat"].astype(float) == 0) & np.isfinite(z["tq"])
    rep["T3"] = []
    for name, seglist in [("creep segs 0/8/9", [0, 8, 9]), ("highway segs 4/5", [4, 5])]:
        m = ok & np.isin(z["seg"].astype(int), seglist)
        runs, i = [], 0
        while i < len(m):
            if m[i]:
                j = i
                while j < len(m) and m[j]:
                    j += 1
                if j - i > int(20 * fs):
                    runs.append((i, j))
                i = j
            else:
                i += 1
        if not runs:
            continue
        lags = np.arange(-int(1.0 * fs), int(1.0 * fs) + 1)
        acc69, acc32, nn = np.zeros(len(lags)), np.zeros(len(lags)), 0
        for i0, i1 in runs:
            tq = z["tq"][i0:i1].astype(float)
            rr = np.abs(z["rate_c"][i0:i1].astype(float))
            if len(tq) < int(30 * fs):
                continue
            e69 = envelope(tq, fs, 6.0, 9.0)
            e32 = envelope(tq, fs, 32.0, 38.0)
            # smooth both to the envelope timescale and standardise
            def z_(x):
                x = np.convolve(x, np.ones(21) / 21, mode="same")
                return (x - x.mean()) / (x.std() + 1e-12)
            a, b69, b32 = z_(rr), z_(e69), z_(e32)
            for k, L in enumerate(lags):
                if L >= 0:
                    acc69[k] += np.dot(a[:len(a) - L], b69[L:]) / (len(a) - L)
                    acc32[k] += np.dot(a[:len(a) - L], b32[L:]) / (len(a) - L)
                else:
                    acc69[k] += np.dot(a[-L:], b69[:len(a) + L]) / (len(a) + L)
                    acc32[k] += np.dot(a[-L:], b32[:len(a) + L]) / (len(a) + L)
            nn += 1
        if nn == 0:
            continue
        acc69 /= nn
        acc32 /= nn
        k69 = int(np.argmax(acc69))
        print(f"  {name}: {nn} runs")
        print(f"    |rate| vs 6-9 Hz env  : peak r={acc69[k69]:+.3f} at lag "
              f"{lags[k69] / fs * 1000:+.0f} ms   (r at lag 0 = {acc69[len(lags)//2]:+.3f})")
        print(f"    |rate| vs 32-38 env   : peak r={acc32[int(np.argmax(acc32))]:+.3f} at lag "
              f"{lags[int(np.argmax(acc32))] / fs * 1000:+.0f} ms  <- CONTROL")
        rep["T3"].append({"stratum": name, "runs": nn,
                          "peak_r_69": float(acc69[k69]),
                          "peak_lag_ms_69": float(lags[k69] / fs * 1000),
                          "r0_69": float(acc69[len(lags) // 2]),
                          "peak_r_32": float(acc32[int(np.argmax(acc32))]),
                          "peak_lag_ms_32": float(lags[int(np.argmax(acc32))] / fs * 1000)})
    print("    (positive lag = |rate| LEADS the envelope => wheel motion EXCITES the ratchet)")

    # ---------------------------------------------------------------- T4
    print("\n" + "=" * 78)
    print("T4  ENGAGED vs MANUAL at MATCHED |rate| -- pooled over every cache with both arms")
    print("=" * 78)
    caches = sorted((ROOT).glob("_cache_r*/r*.npz"))
    pool = []
    for c in caches:
        if c.stem.endswith("s0") or any(ch.isdigit() and c.stem[-2:].isdigit()
                                        and len(c.stem) > 4 for ch in ""):
            pass
        if len(c.stem) > 4 and c.stem[3:].isdigit() is False and "s" in c.stem[3:]:
            continue          # per-segment files
        try:
            zz = np.load(c, allow_pickle=True)
            if not {"tq", "rate_c", "cc_lat", "cs_v", "sstat", "seg"} <= set(zz.files):
                continue
            f2, rr = windows(zz)
        except Exception:
            continue
        for r in rr:
            r["route"] = c.stem
        pool += rr
    print(f"  pooled {len(pool)} windows from "
          f"{len(set(r['route'] for r in pool))} routes")
    rep["T4"] = []
    for lo, hi in [(1, 3), (3, 8), (8, 20), (20, 50), (50, 1e9)]:
        e = [r for r in pool if r["engaged"] and lo <= r["rate_med"] < hi
             and 0.3 < r["v_med"] < 8.0 and not r["veto69"]]
        m = [r for r in pool if not r["engaged"] and lo <= r["rate_med"] < hi
             and 0.3 < r["v_med"] < 8.0 and not r["veto69"]]
        lab = f"{lo:3.0f}-{hi if hi < 1e8 else 999:3.0f}"
        if len(e) < 4 or len(m) < 4:
            print(f"  |rate| {lab}: eng n={len(e):3d}  man n={len(m):3d}  -- insufficient")
            rep["T4"].append({"lo": lo, "hi": hi, "n_eng": len(e), "n_man": len(m),
                              "ratio": None})
            continue
        ee = float(np.median([r["e_6-9"] for r in e]))
        mm = float(np.median([r["e_6-9"] for r in m]))
        # control band
        ec = float(np.median([r["e_32-38"] for r in e]))
        mc = float(np.median([r["e_32-38"] for r in m]))
        print(f"  |rate| {lab}: eng n={len(e):3d} {ee:8.1f}   man n={len(m):3d} {mm:8.1f}   "
              f"ratio {ee/mm:6.2f}x   [negctrl ratio {ec/mc:5.2f}x]")
        rep["T4"].append({"lo": lo, "hi": hi, "n_eng": len(e), "n_man": len(m),
                          "eng": ee, "man": mm, "ratio": ee / mm,
                          "negctrl_ratio": ec / mc})

    # ---------------------------------------------------------------- T5
    print("\n" + "=" * 78)
    print("T5  THE MACRO AXIS -- angle excursion, once |rate| is partialled out")
    print("=" * 78)
    s5 = [r for r in eng if not r["veto69"] and r["rate_med"] > 0.5
          and r["v_med"] > 0.3 and r["ang_ptp"] > 0.2]
    y = np.log([r["e_6-9"] for r in s5])
    lr5 = np.log([r["rate_med"] for r in s5])
    lp5 = np.log([r["ang_ptp"] for r in s5])
    lv5 = np.log([r["v_med"] for r in s5])
    X5 = np.column_stack([np.ones_like(y), lr5, lp5, lv5])
    b5 = np.linalg.lstsq(X5, y, rcond=None)[0]
    blk5 = blocks_of(s5)
    uq5 = np.unique(blk5)
    d_r, d_p = [], []
    for _ in range(3000):
        pick = RNG.choice(uq5, size=len(uq5), replace=True)
        idx = np.concatenate([np.where(blk5 == g)[0] for g in pick])
        try:
            bb = np.linalg.lstsq(X5[idx], y[idx], rcond=None)[0]
            d_r.append(bb[1])
            d_p.append(bb[2])
        except np.linalg.LinAlgError:
            pass
    print(f"  n={len(s5)}   corr(log rate, log ang_ptp) = {np.corrcoef(lr5, lp5)[0,1]:+.3f}")
    print(f"  |rate|   slope {b5[1]:+.3f} "
          f"[{np.percentile(d_r,2.5):+.3f}, {np.percentile(d_r,97.5):+.3f}]")
    print(f"  ang_ptp  slope {b5[2]:+.3f} "
          f"[{np.percentile(d_p,2.5):+.3f}, {np.percentile(d_p,97.5):+.3f}]")
    rep["T5"] = {"n": len(s5), "slope_rate": float(b5[1]),
                 "ci_rate": [float(np.percentile(d_r, 2.5)), float(np.percentile(d_r, 97.5))],
                 "slope_angptp": float(b5[2]),
                 "ci_angptp": [float(np.percentile(d_p, 2.5)), float(np.percentile(d_p, 97.5))],
                 "corr_rate_angptp": float(np.corrcoef(lr5, lp5)[0, 1])}

    OUT.write_text(json.dumps(rep, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
