#!/usr/bin/env python3
"""studies/sessions/r47/r47_orchestrator_checks.py -- the orchestrator's own first-hand numbers for the V67 route-47 session.

Everything the 2026-08-02 handoff quotes as orchestrator-verified is reproduced here, so the claims are
checkable rather than asserted. Deliberately small and self-contained: it duplicates a little of
`lib/_grind2_lib.py` rather than depending on it, because its job is to be an INDEPENDENT second method.

🛑 THE HEADLINE IT EXISTS TO SUPPORT: the operator's new HIGHWAY symptom shows NO rate-lane dose
response, and I had predicted the opposite from arithmetic. The enabler was route `2b` (V58, Kd = 1.00x),
which carries 227 s of highway-engaged driving that three sessions had assumed did not exist -- hidden by
a hardcoded `_r31_common.SEGS_2B = [0,1,2,11,12,13]` that drops its highway leg (segments 3-10).

Sections, each runnable alone:
    exposure   highway/creep seconds per cached route -- finds the missing Kd=1 highway baseline
    creep      the creep dose ladder: grind #1 (18-22 Hz) and grind #2 bursts (40-49 Hz), by engagement
    highway    the three-dose highway comparison + split-half null
    modeid     peak frequency + prominence of the loudest windows, creep vs highway
    imurate    IMU vs CAN sample rate -- the >50 Hz blindness both VIBRATION instruments share
               (the comma MICROPHONE has no ceiling; see studies/acoustic/r47_microphone_test.py)

Usage:  python studies/sessions/r47/r47_orchestrator_checks.py [section ...]      (default: all)

METHOD RULES, each of which has retracted a claim in this kit:
  EPISODES   ratios bootstrap over contiguous ~10 s episode blocks, never over windows -- a window
             bootstrap shrinks the CI by ~sqrt(windows/episode) and manufactures significance.
  NULL       every ratio is quoted against a SPLIT-HALF null computed inside ONE dose pool with the
             identical estimator. A ratio inside that spread is not a finding.
  ENVELOPE   p99 of the analytic band envelope per window, then p90 or MAX across windows -- the
             phenomenon is bursty, so mean Welch power is the wrong statistic.
  EXPOSURE   seconds are printed next to every count. A burst census without exposure is meaningless.
  ALIAS      fs is 100.000 Hz EXACTLY => Nyquist 50.00, so 44.6 and ~55.4 Hz are ONE observation.
             Common mode across builds, so it cannot affect a regression test -- only the
             identification. NOTE `_grind2_lib.fs_of()` is biased +0.5-1.4% route-dependently, which
             is why grind #2 was long quoted as "44.9 Hz"; the between-route spread was the instrument.
  ORDERS     RETIRED 2026-08-03. This read: "At highway, 40-49 Hz is WHEEL ORDER 3 and 10-16 Hz is
             ORDER 1 (measured order p50 2.994 and 1.995) ... peak-finding in that band on a highway
             log will find grind #2 and it will be a tyre."
             The order-3 half is an ESTIMATOR TAUTOLOGY: order = f0*CIRC/v returns ~3.00 BY ARITHMETIC
             whenever a band-limited argmax sits near the centre of 30-49.5 Hz at ~28 m/s, and the
             order-2 figure has the identical defect (band centre 29 Hz at 28-30 m/s) -- one tautology
             counted twice, not mutual corroboration. THERE IS NO LINE AT ALL in 30-49.5 Hz at highway:
             averaged-periodogram prominence 1.23-3.83 vs a >4 criterion, every route/build/channel.
             SURVIVING: 10-16 Hz order 1 IS real (prominence up to 79, order 1.00-1.02 per bin), and
             the general "do not mistake a wheel order for a firmware effect" warning stands.
             RULE: a matching order is evidence only when the band is WIDE relative to the order
             spacing, or the order is TRACKED ACROSS A SPEED SWEEP. And average periodograms BEFORE
             peak-finding -- a median-of-per-window-argmax estimator manufactures a line at band
             centre when none exists. See studies/highway/highway_meanspec.py and the 2026-08-03 handoff.
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, detrend, get_window, hilbert, sosfiltfilt
from scipy.stats import poisson

ROOT = Path(__file__).resolve().parents[4]

BANDS = {"1-4": (1, 4), "6-9": (6, 9), "10-16": (10, 16), "18-22": (18, 22),
         "24-28": (24, 28), "30-40": (30, 40), "40-49": (40, 49)}
WIN_S, BURST = 2.56, 500.0        # window length; burst threshold (creep bursts ran 2000-4000)

# Dose = the r24 rate-lane multiplier. V67 is "gated": 2x only while gp-0x6806 says LKAS is applying.
CREEP_POOLS = {
    "Kd=0     (V61 r31)":                    ["_scratch/cache/r31"],
    "Kd=1.00  (V58 r2b + V59 r2c + V64 r35)": ["_scratch/cache/r2b", "_scratch/cache/r2c", "_scratch/cache/r35"],
    "Kd=2.00  (V62 r37 + V65 r3a/r3b)":      ["_scratch/cache/r37", "_scratch/cache/r3a", "_scratch/cache/r3b"],
    "Kd=gated (V67 r47)":                    ["_scratch/cache/r47"],
}
HWY_POOLS = {
    "Kd=1.00 (V58 r2b + V59 r2c)": ["_scratch/cache/r2b", "_scratch/cache/r2c"],
    "Kd=2.00 (V62 r37 + V65 r3b)": ["_scratch/cache/r37", "_scratch/cache/r3b"],
    "Kd=2.44 (V67 r47)":           ["_scratch/cache/r47"],
}


def _envelope(x, fs, lo, hi):
    sos = butter(4, [lo / (fs / 2), min(hi, fs / 2 * 0.98) / (fs / 2)], btype="band", output="sos")
    return np.abs(hilbert(sosfiltfilt(sos, detrend(x))))


def _windows(cache, tag, vsel):
    """Cut windows inside each segment. Bin by each window's OWN covariates -- never mask first."""
    rows = []
    for p in sorted(glob.glob(str(ROOT / cache / "*.npz"))):
        if "_imu" in p:
            continue
        d = dict(np.load(p))
        if "cs_v" not in d or "tq" not in d:
            continue
        t = d["t"]
        fs = 1.0 / np.median(np.diff(t))
        if not 95 < fs < 105:                      # a non-CAN grid would alias differently
            continue
        env = {k: _envelope(d["tq"], fs, *v) for k, v in BANDS.items()}
        n, hop = int(WIN_S * fs), int(WIN_S * fs) // 2
        lat = d["cc_lat"] > 0.5
        for i in range(0, len(t) - n, hop):
            sl = slice(i, i + n)
            v = float(np.median(d["cs_v"][sl]))
            if not vsel(v):
                continue
            rows.append(dict(tag=tag, ep=(p, i // (n * 4)), v=v, lat=float(lat[sl].mean()),
                             ang=float(np.abs(d["ang"][sl]).max()),
                             rate=float(np.percentile(np.abs(d["rate_c"][sl]), 90)),
                             # ADDITIVE 2026-08-04 (studies/sessions/r58/r58_r54_highrate_4049.py): the PEAK |rate_c|,
                             # for binding a window to the rate-lane gain it actually received.
                             # `gp-0x6ac0` is |rate|, so the gain index sweeps 0 -> peak -> 0 twice
                             # per cycle and the dose that matters is the one at PEAK velocity. A
                             # NEW KEY ONLY -- no existing statistic here is touched, so every
                             # count already on record is unchanged.
                             ratemax=float(np.abs(d["rate_c"][sl]).max()),
                             raw=d["tq"][sl].copy(), fs=fs,
                             **{k: float(np.percentile(env[k][sl], 99)) for k in BANDS}))
    return rows


def _boot_ratio(a, a_ep, b, b_ep, q=90, n=4000, seed=17):
    """Ratio of the q-th percentile, resampling EPISODES with replacement on both sides."""
    rng = np.random.default_rng(seed)
    ua, ub = np.unique(a_ep), np.unique(b_ep)
    out = []
    for _ in range(n):
        sa = np.concatenate([a[a_ep == e] for e in rng.choice(ua, len(ua))])
        sb = np.concatenate([b[b_ep == e] for e in rng.choice(ub, len(ub))])
        out.append(np.percentile(sa, q) / max(np.percentile(sb, q), 1e-9))
    return np.percentile(out, [2.5, 50, 97.5])


def _split_half_null(v, ep, q=90, n=800, seed=23):
    """The floor a ratio must clear: the same estimator applied inside ONE pool, split at random."""
    rng = np.random.default_rng(seed)
    u = np.unique(ep)
    out = []
    for _ in range(n):
        p = rng.permutation(len(u))
        h = len(u) // 2
        s1 = np.concatenate([v[ep == e] for e in u[p[:h]]])
        s2 = np.concatenate([v[ep == e] for e in u[p[h:2 * h]]])
        out.append(np.percentile(s1, q) / max(np.percentile(s2, q), 1e-9))
    return np.percentile(out, [2.5, 97.5])


# =================================================================================================
def sec_exposure():
    print("EXPOSURE PER CACHED ROUTE -- this is how route `2b` was found to hold the missing")
    print("Kd = 1.00x HIGHWAY baseline that two sessions had assumed did not exist.\n")
    print(f"  {'cache':16s} {'segs':>5s} {'total s':>9s} {'highway s':>10s} {'hwy+eng s':>10s} {'creep s':>9s}")
    for cache in sorted(glob.glob(str(ROOT / "_cache_r*"))):
        if not Path(cache).is_dir():
            continue
        tot = hw = hwe = cr = 0.0
        n = 0
        for p in sorted(glob.glob(f"{cache}/*.npz")):
            if "_imu" in p:
                continue
            d = dict(np.load(p))
            if "cs_v" not in d:
                continue
            n += 1
            dt = float(np.median(np.diff(d["t"])))
            v = d["cs_v"]
            lat = d.get("cc_lat", np.zeros_like(v)) > 0.5
            tot += len(v) * dt
            hw += int((v > 20).sum()) * dt
            hwe += int(((v > 20) & lat).sum()) * dt
            cr += int(((v < 4) & (v > 0.3)).sum()) * dt
        if tot:
            print(f"  {Path(cache).name:16s} {n:5d} {tot:9.0f} {hw:10.0f} {hwe:10.0f} {cr:9.0f}")


def sec_creep():
    print("CREEP (0.3-4.0 m/s) DOSE LADDER, split by engagement.")
    print(f"burst = a {WIN_S} s window whose 40-49 Hz envelope p99 exceeds {BURST:.0f} "
          "(creep grind #2 bursts ran 2000-4000)\n")
    D = {k: sum([_windows(c, k, lambda v: 0.3 < v < 4.0) for c in v], []) for k, v in CREEP_POOLS.items()}
    print(f"  {'dose pool':40s} {'arm':8s} {'secs':>7s} {'n':>5s} {'18-22 p90':>10s} "
          f"{'40-49 p90':>10s} {'40-49 MAX':>10s} {'bursts':>7s}")
    for k, ss in D.items():
        for lab, sel in (("LKAS ON", lambda r: r["lat"] > 0.9), ("LKAS OFF", lambda r: r["lat"] < 0.1)):
            s = [r for r in ss if sel(r)]
            if not s:
                continue
            b = sum(1 for r in s if r["40-49"] > BURST)
            print(f"  {k:40s} {lab:8s} {len(s) * WIN_S / 2:7.0f} {len(s):5d} "
                  f"{np.percentile([r['18-22'] for r in s], 90):10.1f} "
                  f"{np.percentile([r['40-49'] for r in s], 90):10.1f} "
                  f"{max(r['40-49'] for r in s):10.1f} {b:7d}")
        print()

    ref = [r for r in D["Kd=1.00  (V58 r2b + V59 r2c + V64 r35)"] if r["lat"] > 0.9]
    be, bv = np.array([hash(r["ep"]) for r in ref]), np.array([r["18-22"] for r in ref])
    print("  GRIND #1 (18-22 Hz), ENGAGED CREEP, ratio vs the Kd=1.00 pool, episode-bootstrapped:")
    for k in ("Kd=0     (V61 r31)", "Kd=gated (V67 r47)", "Kd=2.00  (V62 r37 + V65 r3a/r3b)"):
        s = [r for r in D[k] if r["lat"] > 0.9]
        if len(s) < 5:
            continue
        lo, md, hi = _boot_ratio(np.array([r["18-22"] for r in s]),
                                 np.array([hash(r["ep"]) for r in s]), bv, be)
        print(f"    {k:40s} n={len(s):4d}  {md:5.2f} [{lo:4.2f}, {hi:4.2f}]")
    nlo, nhi = _split_half_null(bv, be)
    print(f"    {'split-half NULL inside Kd=1.00':40s}        [{nlo:4.2f}, {nhi:4.2f}]")

    print("\n  🛑 POWER on the grind #2 elimination -- the two arms are NOT equally supported:")
    k2 = "Kd=2.00  (V62 r37 + V65 r3a/r3b)"
    for lab, sel, v67secs in (("manual", lambda r: r["lat"] < 0.1, None),
                              ("engaged", lambda r: r["lat"] > 0.9, None)):
        s2 = [r for r in D[k2] if sel(r)]
        s7 = [r for r in D["Kd=gated (V67 r47)"] if sel(r)]
        if not s2 or not s7:
            continue
        secs2, secs7 = len(s2) * WIN_S / 2, len(s7) * WIN_S / 2
        rate = sum(1 for r in s2 if r["40-49"] > BURST) / secs2
        exp = rate * secs7
        print(f"    {lab:8s}: Kd=2 rate {rate:.4f}/s -> expected {exp:.2f} in V67's {secs7:.0f} s;  "
              f"P(0 | that rate) = {poisson.pmf(0, exp):.4f}")


def sec_highway():
    print("HIGHWAY (v > 20 m/s, latActive throughout) -- THREE DOSES.")
    print("This is the comparison that REFUTED the orchestrator's own 2.44x prediction.\n")
    D = {k: sum([_windows(c, k, lambda v: v > 20) for c in v], []) for k, v in HWY_POOLS.items()}
    D = {k: [r for r in ss if r["lat"] > 0.99] for k, ss in D.items()}
    print(f"  {'dose pool':30s} {'n':>5s} {'secs':>6s} " + " ".join(f"{k:>9s}" for k in BANDS)
          + f" {'MAX40-49':>9s} {'bursts':>7s}")
    for k, ss in D.items():
        b = sum(1 for r in ss if r["40-49"] > BURST)
        print(f"  {k:30s} {len(ss):5d} {len(ss) * WIN_S / 2:6.0f} "
              + " ".join(f"{np.percentile([r[x] for r in ss], 90):9.1f}" for x in BANDS)
              + f" {max(r['40-49'] for r in ss):9.1f} {b:7d}")
    base = D["Kd=1.00 (V58 r2b + V59 r2c)"]
    be = np.array([hash(r["ep"]) for r in base])
    print("\n  RATIO vs Kd=1.00, episode-bootstrapped, with the split-half null underneath:")
    for k, ss in D.items():
        if k.startswith("Kd=1.00"):
            continue
        cells = []
        for x in BANDS:
            lo, md, hi = _boot_ratio(np.array([r[x] for r in ss]),
                                     np.array([hash(r["ep"]) for r in ss]),
                                     np.array([r[x] for r in base]), be, n=1500)
            cells.append(f"{md:4.2f}[{lo:4.2f},{hi:4.2f}]")
        print(f"  {k:30s} {len(ss):5d}        " + " ".join(f"{c:>16s}" for c in cells))
    cells = []
    for x in BANDS:
        nlo, nhi = _split_half_null(np.array([r[x] for r in base]), be, n=600)
        cells.append(f"null[{nlo:4.2f},{nhi:4.2f}]")
    print(f"  {'':30s} {'':5s}        " + " ".join(f"{c:>16s}" for c in cells))


def sec_modeid():
    print("MODE IDENTIFICATION -- 30-49 Hz peak in the LOUDEST windows of each population.")
    print("Prominence = peak / local median floor, so a driver cranking the wheel cannot pass it.")
    print("🛑 ALIAS: fs ~ 100.5 Hz => 44.9 and ~55.6 Hz are the SAME observation.\n")

    def peak(x, fs):
        w = get_window("hann", len(x))
        X = np.abs(np.fft.rfft(detrend(x) * w)) ** 2
        f = np.fft.rfftfreq(len(x), 1 / fs)
        m = (f >= 30) & (f <= 49.5)
        i = np.argmax(X[m])
        floor = np.median(X[(f >= 25) & (f <= 49.5)])
        return f[m][i], X[m][i] / max(floor, 1e-12)

    for lab, caches, vsel in (
            ("CREEP grind #2 (V65 r3a/r3b, V62 r37)", ["_scratch/cache/r3a", "_scratch/cache/r3b", "_scratch/cache/r37"],
             lambda v: v < 4),
            ("HIGHWAY        (V65 r3b, V67 r47)", ["_scratch/cache/r3b", "_scratch/cache/r47"], lambda v: v > 20)):
        rows = sum([_windows(c, lab, vsel) for c in caches], [])
        rows.sort(key=lambda r: -r["40-49"])
        top = rows[:15]
        f0 = np.array([peak(r["raw"], r["fs"])[0] for r in top])
        pr = np.array([peak(r["raw"], r["fs"])[1] for r in top])
        print(f"  {lab:40s} n={len(top):3d}  env99 max={top[0]['40-49']:8.1f}  "
              f"f0 med={np.median(f0):5.2f} sd={np.std(f0):4.2f} Hz  prominence med={np.median(pr):7.1f}x")
    print("\n  => same band, but the highway population is an order of magnitude weaker and")
    print("     ~10x less spectrally sharp. It is NOT the creep grind #2.")


def sec_imurate():
    print("INSTRUMENT BANDWIDTH -- the limit every null in this session is silent above.\n")
    print(f"  {'imu cache':34s} {'accel n':>8s} {'rate Hz':>9s} {'NYQUIST':>9s}")
    for p in sorted(glob.glob(str(ROOT / "_cache_r*" / "*_imu.npz")))[:6]:
        d = dict(np.load(p))
        da = np.diff(d["at"])
        print(f"  {Path(p).name:34s} {len(d['at']):8d} {1 / np.mean(da):9.3f} {0.5 / np.mean(da):9.2f}")
    print("\n  CAN 0x14A/0x18F grid: 100.000 Hz EXACTLY => Nyquist 50.00 Hz")
    print("  🛑 dt MEAN vs MEDIAN matters here: ~1% of IMU samples are DROPPED, so the mean reads")
    print("     ~100.0 Hz while the true ODR is 101.02 (median 9.899 ms). Settled by a lattice fit")
    print("     (77 us median-seeded vs 2889 us forced to 100.03) and a synthetic fold test in which")
    print("     7 of 7 known tones fold per 101.02 Hz. => Nyquist 50.51, i.e. 0.51 Hz over CAN.")
    print("  🛑 That headroom is NOT usable, and headroom is the wrong quantity anyway: the alias")
    print("     discriminant is a 1.021 Hz apparent-peak difference (55.6 Hz shows at 44.400 on CAN")
    print("     and 45.421 on the IMU) and the measured sem is 0.856 where <<0.34 is needed.")
    print("     Resolving it needs a log at a different IMU ODR (208/416 Hz), not more of this data.")
    print("  ★ THE MICROPHONE HAS NO CEILING (soundPressure, audio at 16-48 kHz, level at 10.000 Hz)")
    print("     and a validated positive control: 4.14x un-weighted p95 on the creep grind #2.")
    print("     See analysis-2020accord/studies/acoustic/r47_microphone_test.py.")


SECTIONS = {"exposure": sec_exposure, "creep": sec_creep, "highway": sec_highway,
            "modeid": sec_modeid, "imurate": sec_imurate}

if __name__ == "__main__":
    for name in (sys.argv[1:] or list(SECTIONS)):
        print("=" * 100)
        SECTIONS[name]()
        print()
