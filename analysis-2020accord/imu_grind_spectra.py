#!/usr/bin/env python3
"""imu_grind_spectra.py -- does the comma IMU see grind #2, and can its grid break the alias?

TWO QUESTIONS, IN ORDER.

1. IS IT REAL? The IMU is physically independent of the EPS. If the 25-70 Hz band rises on the
   accelerometer during the operator's demonstrations, grind #2 is a mechanical vibration of the
   car, not a number in an EPS spectrum. A POSITIVE CONTROL at the ~20.9 Hz grind #1 mode is
   mandatory: without it, an IMU null is uninterpretable (it could just mean the device does not
   see the steering assembly at all).

2. CAN IT RESOLVE THE ALIAS? The CAN grid is 100.00 Hz, so 41.6 Hz and 58.4 Hz are literally the
   same observation there. The IMU's hardware ODR is ~101.03 Hz. For a true frequency f, the
   apparent peak difference (IMU - CAN) is:
           f < 50               ->   0.00 Hz
           50 < f < 100         ->  +1.03 Hz
           100 < f < 150        ->  -1.03 Hz
           150 < f < 200        ->  +2.06 Hz
   So the alias ORDER is readable from a ~1 Hz shift -- but only if the peak can be located to
   much better than 1 Hz, and only if the SAME burst is measured on both grids (the phenomenon's
   own frequency wanders by several Hz between bursts, which would swamp an unpaired comparison).

🛑 DROPPED SAMPLES, AND WHY NAIVE RESAMPLING WOULD DESTROY THE ANSWER.
   accel dt: median 9.898 ms but mean 9.998 ms and p99 12.1 ms -- samples are DROPPED, not jittered.
   Interpolating onto a NEW uniform rate would impose that new rate's alias mapping and silently
   fabricate the answer to question 2. Instead every sample is SNAPPED TO ITS OWN LATTICE INDEX on
   the sensor's true ODR, gaps are left as gaps and filled by interpolation, so the surviving
   samples keep the original sampling lattice. The lattice hypothesis is TESTED, not assumed.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from analyse_v65_routes import segs  # noqa: E402

AXES = ["ax", "ay", "az", "gx", "gy", "gz"]
NSEG = {"r3a": 7, "r3b": 14}

# The operator's demonstrations, from the burst analysis. (segment, t_start, t_end)
DEMOS = {
    "r3a": [(3, 6.5, 13.0), (3, 35.0, 39.5), (4, 7.5, 11.0), (4, 14.5, 17.5), (1, 26.5, 28.5)],
    "r3b": [(2, 0.0, 4.0), (2, 19.0, 22.5)],
}
# Matched quiet: same segment-type, same creep speed, no burst. (segment, t_start, t_end)
QUIET = {
    "r3a": [(3, 20.0, 30.0), (4, 35.0, 45.0), (3, 45.0, 55.0), (4, 45.0, 55.0)],
    "r3b": [(2, 8.0, 15.0), (2, 30.0, 40.0), (0, 20.0, 30.0), (2, 45.0, 55.0)],
}


def lattice(t, odr0, tag):
    """Snap samples to the sensor's own ODR lattice. Returns (index, refined_odr, resid_rms)."""
    n = np.round((t - t[0]) * odr0).astype(np.int64)
    # refine the ODR by regressing time on lattice index, then re-snap once
    for _ in range(3):
        A = np.vstack([n, np.ones_like(n)]).T.astype(float)
        slope, icpt = np.linalg.lstsq(A, t, rcond=None)[0]
        odr0 = 1.0 / slope
        n = np.round((t - icpt) / slope).astype(np.int64)
    resid = t - (icpt + n * slope)
    return n, odr0, float(np.sqrt(np.mean(resid ** 2))), float(np.abs(resid).max())


def uniform(t, v, odr0):
    """Lattice-snapped uniform series with gaps interpolated. Returns (series, odr, fill_frac)."""
    n, odr, rms, mx = lattice(t, odr0, "")
    n = n - n[0]
    out = np.full(int(n[-1]) + 1, np.nan)
    out[n] = v
    bad = ~np.isfinite(out)
    if bad.any():
        out[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), out[~bad])
    return out, odr, 1.0 - bad.mean(), rms, mx


def peak(x, fs, lo, hi, pad=32):
    """Zero-padded periodogram peak with parabolic interpolation. Returns (f_peak, power, floor)."""
    x = np.asarray(x, float)
    x = x - x.mean()
    w = np.hanning(len(x))
    N = int(2 ** np.ceil(np.log2(len(x) * pad)))
    P = np.abs(np.fft.rfft(x * w, n=N)) ** 2
    f = np.fft.rfftfreq(N, 1 / fs)
    k = (f >= lo) & (f <= hi)
    if not k.any():
        return np.nan, np.nan, np.nan
    idx = np.flatnonzero(k)[np.argmax(P[k])]
    if 0 < idx < len(P) - 1:                       # parabolic interpolation on the log spectrum
        a, b, c = np.log(P[idx - 1] + 1e-30), np.log(P[idx] + 1e-30), np.log(P[idx + 1] + 1e-30)
        d = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
        fpk = f[idx] + d * (f[1] - f[0])
    else:
        fpk = f[idx]
    return float(fpk), float(P[idx]), float(np.median(P[k]))


def band_power(x, fs, lo, hi):
    x = np.asarray(x, float) - np.mean(x)
    P = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / fs)
    k = (f >= lo) & (f <= hi)
    return float(P[k].sum()) if k.any() else 0.0


def load_imu(tag, s):
    return dict(np.load(ROOT / f"_cache_{tag}" / f"{tag}s{s}_imu.npz"))


def slice_imu(d, kind, t0, t1):
    tk = d["at"] if kind[0] == "a" else d["gt"]
    m = (tk >= t0) & (tk <= t1)
    return tk[m], d[kind][m]


def run(tag):
    print(f"\n{'=' * 104}\n== {tag.upper()} IMU\n{'=' * 104}")

    # ---- 1. THE SAMPLING LATTICE -----------------------------------------------------------------
    print("\n-- SAMPLING LATTICE (is the 'jitter' really dropped samples on a fixed ODR?) --")
    print(f"   {'seg':>4s} {'chan':>5s} {'n':>6s} {'fitted ODR':>11s} {'resid rms':>10s} "
          f"{'resid max':>10s} {'lattice fill':>12s}")
    odrs = {"a": [], "g": []}
    for s in range(NSEG[tag]):
        d = load_imu(tag, s)
        for kind, tk in (("a", "at"), ("g", "gt")):
            t = d[tk]
            _, odr, rms, mx = lattice(t, 101.03, tag)
            _, _, fill, _, _ = uniform(t, d[kind + "x"], 101.03)
            odrs[kind].append(odr)
            print(f"   {s:4d} {kind:>5s} {len(t):6d} {odr:11.5f} {1e3 * rms:9.4f}ms "
                  f"{1e3 * mx:9.4f}ms {100 * fill:11.2f}%")
    for kind in ("a", "g"):
        o = np.array(odrs[kind])
        print(f"   {kind}: ODR mean {o.mean():.5f} Hz  sd {o.std():.5f}  "
              f"range {o.min():.5f}..{o.max():.5f}")
    return float(np.mean(odrs["a"])), float(np.mean(odrs["g"]))


def spectra(tag, odr_a, odr_g):
    can = {s: d for s, d in segs(tag)}
    print(f"\n-- BAND POWER: DEMONSTRATIONS vs MATCHED QUIET (IMU, native grid) --")
    bands = [("18-22 Hz  [grind #1 CONTROL]", 18.0, 22.0),
             ("25-70 Hz  [grind #2 -> folded]", 25.0, 50.0),
             ("40-49 Hz  [grind #2 peak]", 40.0, 49.0),
             ("5-9 Hz    [ratchet]", 5.0, 9.0)]
    res = {}
    for label, lo, hi in bands:
        print(f"\n   *** {label} ***")
        print(f"   {'axis':>5s} | " + "  ".join(f"{n:>10s}" for n in
                                                ("demo", "quiet", "ratio")))
        for ax in AXES:
            odr = odr_a if ax[0] == "a" else odr_g
            dp, qp = [], []
            for (s, t0, t1), acc in ((w, dp) for w in DEMOS[tag]):
                d = load_imu(tag, s)
                t, v = slice_imu(d, ax, t0, t1)
                if len(t) < 32:
                    continue
                u, o, _, _, _ = uniform(t, v, odr)
                acc.append(band_power(u, o, lo, hi) / len(u))
            for (s, t0, t1), acc in ((w, qp) for w in QUIET[tag]):
                d = load_imu(tag, s)
                t, v = slice_imu(d, ax, t0, t1)
                if len(t) < 32:
                    continue
                u, o, _, _, _ = uniform(t, v, odr)
                acc.append(band_power(u, o, lo, hi) / len(u))
            if not dp or not qp:
                continue
            dm, qm = float(np.median(dp)), float(np.median(qp))
            r = dm / qm if qm > 0 else np.inf
            print(f"   {ax:>5s} | {dm:10.4g}  {qm:10.4g}  {r:10.2f}x")
            res[(label, ax)] = (dm, qm, r)
    return res


def alias(tag, odr_a):
    """PAIRED per-burst peak comparison: same window, EPS torsion bar vs comma accelerometer."""
    can = {s: d for s, d in segs(tag)}
    print(f"\n-- ALIAS DISCRIMINATION: same burst, two grids --")
    print(f"   CAN grid 100.00 Hz vs IMU lattice {odr_a:.4f} Hz  =>  predicted (IMU-CAN) peak shift:")
    for k, lab in ((0, "f < 50 (real, unaliased)"), (1, "50 < f < 100"), (-1, "100 < f < 150"),
                   (2, "150 < f < 200")):
        print(f"      {lab:26s} : {k * (odr_a - 100.0):+.4f} Hz")
    print(f"\n   {'seg':>4s} {'t0':>7s} {'t1':>7s} | {'CAN f_pk':>9s} {'SNR':>8s} | "
          f"{'IMU axis':>8s} {'IMU f_pk':>9s} {'SNR':>8s} | {'shift':>8s}")
    rows = []
    for s, t0, t1 in DEMOS[tag]:
        d = can[s]
        fs_can = 100.0
        m = (d["t"] >= t0) & (d["t"] <= t1)
        fc, pc, flc = peak(d["tq"][m], fs_can, 30.0, 49.5)
        di = load_imu(tag, s)
        best = None
        for ax in AXES:
            odr = odr_a
            t, v = slice_imu(di, ax, t0, t1)
            if len(t) < 64:
                continue
            u, o, _, _, _ = uniform(t, v, odr)
            fi, pi, fli = peak(u, o, 30.0, 49.5)
            snr = pi / fli if fli > 0 else 0
            if best is None or snr > best[3]:
                best = (ax, fi, pi, snr, o)
        if best is None:
            continue
        ax, fi, pi, snr, o = best
        print(f"   {s:4d} {t0:6.2f}s {t1:6.2f}s | {fc:9.4f} {pc / flc:8.1f} | {ax:>8s} "
              f"{fi:9.4f} {snr:8.1f} | {fi - fc:+8.4f}")
        rows.append(dict(seg=s, t0=t0, t1=t1, f_can=fc, snr_can=pc / flc,
                         axis=ax, f_imu=fi, snr_imu=snr, shift=fi - fc))
    if rows:
        sh = np.array([r["shift"] for r in rows])
        good = [r for r in rows if r["snr_imu"] > 10 and r["snr_can"] > 10]
        print(f"\n   shift over {len(rows)} bursts: med {np.median(sh):+.4f} Hz  "
              f"mean {sh.mean():+.4f}  sd {sh.std():.4f}  range {sh.min():+.4f}..{sh.max():+.4f}")
        print(f"   bursts with SNR>10 on BOTH grids: {len(good)}")
        if good:
            g = np.array([r["shift"] for r in good])
            print(f"     their shift: med {np.median(g):+.4f} Hz  sd {g.std():.4f}")
    return rows


if __name__ == "__main__":
    out = {}
    for tag in (sys.argv[1:] or ["r3a", "r3b"]):
        oa, og = run(tag)
        spectra(tag, oa, og)
        out[tag] = alias(tag, oa)
    (ROOT / "_cache_r3a" / "imu_alias.json").write_text(json.dumps(out, default=float))
