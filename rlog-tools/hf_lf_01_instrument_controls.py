#!/usr/bin/env python3
r"""CONTROLS BEFORE MEASUREMENT -- can a 20-50 Hz band on `tq` carry an ENVELOPE at all?

THE CONFOUND THIS FILE EXISTS TO KILL
  The hypothesis under test is "the envelope of a high-frequency band drives a low-frequency
  oscillation".  There is an INSTRUMENTAL mechanism that produces exactly that signature with no
  physics behind it whatsoever:

      the CAN timestamps jitter (dt p05 8.77 / med 9.90 / p95 11.36 ms, plus ~2.5 % dropped
      frames), and every kit pipeline `np.interp`s onto a uniform 100 Hz grid.  Interpolating with
      timing error eps injects an error of order  eps * ds/dt.  That error is BROADBAND -- it
      lands in 20-50 Hz -- and its amplitude is PROPORTIONAL TO THE LOW-FREQUENCY SLOPE OF THE
      SIGNAL.

  i.e. a pure resampling artefact has a high-frequency envelope that tracks low-frequency steering
  activity, which is the exact statistic hypothesis 1 predicts.  Unmeasured, ANY positive result
  here is uninterpretable.

WHAT IS MEASURED, IN ORDER
  C-A  ZOH periodicity.  If the ECU recomputed `tq` at 80 Hz and transmitted at 100 Hz the repeat
       indicator would carry a 20 Hz line.  (STATE.md defect #5: 0x18F staleness is 12.5 ms.)
  C-B  Drop-free native runs -- how long a stretch of true ECU lattice actually exists.
  C-C  THE ARTEFACT NULL.  A synthetic signal with ONLY <12 Hz content, known in CONTINUOUS time,
       sampled at the REAL logged timestamps and pushed through the REAL `np.interp` pipeline.
       Whatever 20-50 Hz comes out is manufactured.  Reported against the real band RMS.
  C-D  Parked floor -- the same bands with the car stationary and the wheel still.
  C-E  Pipeline positive control -- a carrier AM'd at a known f_LF and depth must come back right.
  C-F  Interpolation transfer -- a synthetic BROADBAND signal, known in continuous time, through
       the same pipeline: how much of each band survives, and how much leaks in.

OUTPUT  `rlog-tools/_hf_lf_controls.json`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTE_LABEL = {"97": "STOCK (V9b)", "9e": "V103", "96": "V102 6x", "85": "V100 4x", "95": "V101 8x"}
ROUTES = ["9e", "97", "96"]
KMH = 3.6
HF_BANDS = {"6-9": (6.0, 9.0), "15-22": (15.0, 22.0), "20-30": (20.0, 30.0),
            "22-26": (22.0, 26.0), "26-31": (26.0, 31.0), "32-38": (32.0, 38.0),
            "40-49": (40.0, 49.0)}


def reg(rt):
    if rt not in L.ROUTES:
        L.ROUTES[rt] = L._mk(rt, ROUTE_LABEL.get(rt, rt), gain=0, clamp=0, leverB=False,
                             idcode=0, bits="")
    return bool(L.ROUTES[rt]["segs"])


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104, flush=True)


def native_segs(rt):
    for s in L.ROUTES[rt]["segs"]:
        yield s, L.load_seg(rt, s)


# ------------------------------------------------------------------ shared helpers --------------
def band_rms(x, fs, lo, hi):
    return L.bandrms(np.asarray(x, float), fs, lo, hi, np.hanning(len(x)))


def analytic_env(x, fs, lo, hi):
    """TRUE analytic envelope of the [lo,hi) component.

    🛑 NOT `_r31_common.band_envelope`, which is RECTIFIED, not analytic
    (`accord-band-envelope-is-rectified-not-analytic`).  Here the negative-frequency half is
    ZEROED and the positive half DOUBLED on the FULL complex FFT, so `ifft` returns the complex
    analytic signal and `abs` is a genuine envelope.
    """
    x = np.asarray(x, float)
    n = len(x)
    X = np.fft.fft(x - x.mean())
    f = np.fft.fftfreq(n, 1.0 / fs)
    Z = np.zeros(n, complex)
    m = (f >= lo) & (f < hi)
    Z[m] = 2.0 * X[m]
    return np.abs(np.fft.ifft(Z))


def mod_index(e, fs, flo, fhi):
    """Modulation index of an envelope in [flo,fhi): sqrt(2)*bandRMS / mean, dimensionless."""
    e = np.asarray(e, float)
    mu = float(np.mean(e))
    if mu <= 0:
        return np.nan
    return float(np.sqrt(2.0) * band_rms(e, fs, flo, fhi) / mu)


def synth_from_psd(f_c, amp_c, t):
    """Evaluate a random-phase Fourier sum in CONTINUOUS time -- exact at any t."""
    ph = synth_from_psd.rng.uniform(0, 2 * np.pi, len(f_c))
    return (amp_c[None, :] * np.cos(2 * np.pi * f_c[None, :] * t[:, None] + ph[None, :])).sum(1)


synth_from_psd.rng = np.random.default_rng(11)


# ------------------------------------------------------------------ C-A ZOH periodicity ---------
def c_a_zoh(rt):
    ind, n = [], 0
    for _, d in native_segs(rt):
        x = np.asarray(d["tq"], float)
        dt = np.diff(np.asarray(d["t"], float))
        ok = (dt > 0.006) & (dt < 0.015)
        ind.append(((np.diff(x) == 0.0) & ok).astype(float))
        n += int(ok.sum())
    x = np.concatenate(ind)
    nfft, P, k = 1024, np.zeros(513), 0
    for s in range(0, len(x) - nfft + 1, nfft):
        seg = x[s:s + nfft] - x[s:s + nfft].mean()
        P += np.abs(np.fft.rfft(seg * np.hanning(nfft))) ** 2
        k += 1
    P /= max(k, 1)
    f = np.fft.rfftfreq(nfft, 1.0 / 100.85)
    m20 = (f > 18) & (f < 22)
    top = np.argsort(P[1:])[::-1][:4] + 1
    return dict(n_pairs=n, repeat_frac=float(x.mean()),
                peaks_hz=[float(f[i]) for i in top],
                peak_over_med=[float(P[i] / np.median(P[1:])) for i in top],
                line_at_20hz_over_med=float(P[m20].max() / np.median(P[1:])))


# ------------------------------------------------------------------ C-B drop-free runs ----------
def c_b_runs(rt):
    lens = []
    for _, d in native_segs(rt):
        dt = np.diff(np.asarray(d["t"], float))
        good = (dt > 0.006) & (dt < 0.015)
        i = 0
        while i < len(good):
            if not good[i]:
                i += 1
                continue
            j = i
            while j < len(good) and good[j]:
                j += 1
            lens.append(j - i + 1)
            i = j
    a = np.asarray(lens, float)
    return dict(n_runs=int(len(a)), med=float(np.median(a)), p90=float(np.percentile(a, 90)),
                max=float(a.max()), s_ge_128=float(a[a >= 128].sum() / 100.85),
                s_ge_512=float(a[a >= 512].sum() / 100.85),
                s_ge_1024=float(a[a >= 1024].sum() / 100.85))


# ------------------------------------------------------------------ C-C the artefact null -------
def c_c_artefact(rt, nfft=1024, fc_lf=12.0, nmax=120, seed=5):
    """Synthetic <12 Hz signal, known in continuous time, through the REAL timestamp pipeline.

    The synthetic's LF amplitude spectrum is matched to the route's own engaged-highway `tq`, so
    the manufactured HF is the amount THIS route's LF activity would produce.
    """
    synth_from_psd.rng = np.random.default_rng(seed)
    T = 1.0 / L.FS
    # 1. measure the route's engaged-highway LF amplitude spectrum on the uniform grid
    win = np.hanning(nfft)
    acc, k = None, 0
    for blk in L.all_blocks(rt):
        v = np.asarray(blk["v_rear"], float) * KMH
        eng = np.asarray(blk["cc_lat"], float) > 0.5
        for s in range(0, len(v) - nfft + 1, nfft // 2):
            sl = slice(s, s + nfft)
            if eng[sl].mean() < 0.98 or np.median(v[sl]) < 70.0:
                continue
            f, p = L.psd(np.asarray(blk["tq"][sl], float), L.FS, win)
            acc = p if acc is None else acc + p
            k += 1
    if not k:
        return {"n": 0}
    P = acc / k
    m = (f > 0.05) & (f <= fc_lf)
    f_c, amp_c = f[m], np.sqrt(2.0 * P[m])
    # 2. run it through the real timestamps
    rows = []
    for _, d in native_segs(rt):
        t = np.asarray(d["t"], float)
        x = np.asarray(d["tq"], float)
        v = np.asarray(d.get("v_rear", np.zeros_like(t)), float) * KMH
        eng = np.asarray(d["cc_lat"], float) > 0.5
        for s in range(0, len(t) - nfft + 1, nfft):
            sl = slice(s, s + nfft)
            if eng[sl].mean() < 0.98 or np.median(v[sl]) < 70.0:
                continue
            ts = t[sl]
            if ts[-1] <= ts[0]:
                continue
            u = np.arange(ts[0], ts[-1], T)
            if len(u) < nfft // 2:
                continue
            truth = synth_from_psd(f_c, amp_c, u)                 # exact continuous-time value
            samp = synth_from_psd.last if False else None         # (unused; see below)
            # the SAME realisation sampled at the logged times -- reuse identical phases by
            # re-seeding is avoided: build both from one evaluation instead.
            rows.append((ts, u, truth, f_c, amp_c, sl, float(np.median(v[sl])), x))
            if len(rows) >= nmax:
                break
        if len(rows) >= nmax:
            break
    out = {"n": len(rows)}
    if not rows:
        return out
    # regenerate with a FIXED phase vector so `truth` and `sampled` are the same realisation
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 2 * np.pi, len(f_c))

    def ev(tt):
        return (amp_c[None, :] * np.cos(2 * np.pi * f_c[None, :] * tt[:, None]
                                        + ph[None, :])).sum(1)

    stats = {bn: ([], []) for bn in HF_BANDS}
    for ts, u, _, _, _, sl, vv, x in rows:
        clean = ev(u)
        dirty = np.interp(u, ts, ev(ts))
        art = dirty - clean
        for bn, (lo, hi) in HF_BANDS.items():
            stats[bn][0].append(band_rms(x[sl], L.FS, lo, hi))
            stats[bn][1].append(band_rms(art, L.FS, lo, hi))
    for bn in HF_BANDS:
        real = np.asarray(stats[bn][0]); art = np.asarray(stats[bn][1])
        out[bn] = dict(real_med=float(np.median(real)), art_med=float(np.median(art)),
                       art_over_real_med=float(np.median(art / np.maximum(real, 1e-9))),
                       art_over_real_p90=float(np.percentile(art / np.maximum(real, 1e-9), 90)))
    return out


# ------------------------------------------------------------------ C-D parked floor ------------
def c_d_parked(rt, nfft=512):
    rows = []
    for blk in L.all_blocks(rt):
        v = np.asarray(blk["v_rear"], float) * KMH
        rc = np.abs(np.asarray(blk["rate_c"], float))
        x = np.asarray(blk["tq"], float)
        for s in range(0, len(v) - nfft + 1, nfft):
            sl = slice(s, s + nfft)
            if np.max(v[sl]) > 2.0 or np.max(rc[sl]) > 2.0:
                continue
            rows.append({bn: band_rms(x[sl], L.FS, lo, hi) for bn, (lo, hi) in HF_BANDS.items()})
    out = {"n": len(rows)}
    for bn in HF_BANDS:
        if rows:
            out[bn] = float(np.median([r[bn] for r in rows]))
    return out


# ------------------------------------------------------------------ C-E pipeline positive ctrl --
def c_e_positive(fs=100.0, n=4096, f_c=25.0, seed=3):
    rng = np.random.default_rng(seed)
    t = np.arange(n) / fs
    out = []
    for f_lf, depth, snr in ((1.20, 0.35, 0.0), (1.20, 0.35, 0.3), (0.60, 0.15, 0.3),
                             (2.50, 0.35, 0.3)):
        car = (1.0 + depth * np.sin(2 * np.pi * f_lf * t)) * np.sin(2 * np.pi * f_c * t)
        x = 100.0 * car + (100.0 * snr) * rng.standard_normal(n)
        e = analytic_env(x, fs, 20.0, 30.0)
        ee = e - e.mean()
        f, P = L.psd(ee, fs, np.hanning(n))
        m = (f > 0.25) & (f < 6.0)
        fpk = float(f[m][np.argmax(P[m])])
        out.append(dict(f_lf=f_lf, depth=depth, noise=snr, f_found=fpk,
                        depth_found=mod_index(e, fs, fpk - 0.3, fpk + 0.3)))
    return out


# ------------------------------------------------------------------ C-F interp transfer ---------
def c_f_transfer(rt, nfft=1024, nmax=60, seed=7):
    """A synthetic FLAT broadband signal through the real timestamp pipeline: band-by-band gain."""
    rng = np.random.default_rng(seed)
    T = 1.0 / L.FS
    f_c = np.arange(0.5, 50.0, 0.25)
    amp = np.ones_like(f_c)
    ph = rng.uniform(0, 2 * np.pi, len(f_c))

    def ev(tt):
        return (amp[None, :] * np.cos(2 * np.pi * f_c[None, :] * tt[:, None]
                                      + ph[None, :])).sum(1)

    g = {bn: [] for bn in HF_BANDS}
    k = 0
    for _, d in native_segs(rt):
        t = np.asarray(d["t"], float)
        for s in range(0, len(t) - nfft + 1, nfft):
            ts = t[s:s + nfft]
            if ts[-1] <= ts[0]:
                continue
            u = np.arange(ts[0], ts[-1], T)
            if len(u) < nfft // 2:
                continue
            clean, dirty = ev(u), np.interp(u, ts, ev(ts))
            for bn, (lo, hi) in HF_BANDS.items():
                a = band_rms(clean, L.FS, lo, hi)
                g[bn].append(band_rms(dirty, L.FS, lo, hi) / max(a, 1e-12))
            k += 1
            if k >= nmax:
                break
        if k >= nmax:
            break
    return {"n": k, **{bn: float(np.median(v)) if v else np.nan for bn, v in g.items()}}


def main():
    res = {}
    hdr("C-E  PIPELINE POSITIVE CONTROL (synthetic AM, no car data)")
    pc = c_e_positive()
    for r in pc:
        print("   f_LF=%.2f depth=%.2f noise=%.1f  ->  found f=%.3f Hz  depth=%.3f"
              % (r["f_lf"], r["depth"], r["noise"], r["f_found"], r["depth_found"]))
    res["positive_control"] = pc

    for rt in ROUTES:
        if not reg(rt):
            continue
        hdr("ROUTE %s  (%s)" % (rt, ROUTE_LABEL.get(rt, rt)))
        a = c_a_zoh(rt)
        print("C-A  tq repeat frac=%.4f over %d single-tick pairs; 18-22 Hz line = %.2fx median"
              % (a["repeat_frac"], a["n_pairs"], a["line_at_20hz_over_med"]))
        print("     top lines: %s" % ", ".join("%.2f Hz (x%.1f)" % (h, r)
                                               for h, r in zip(a["peaks_hz"], a["peak_over_med"])))
        b = c_b_runs(rt)
        print("C-B  drop-free native runs n=%d med=%.0f p90=%.0f max=%.0f | >=128 samp: %.1f s, "
              ">=512: %.1f s, >=1024: %.1f s"
              % (b["n_runs"], b["med"], b["p90"], b["max"], b["s_ge_128"], b["s_ge_512"],
                 b["s_ge_1024"]))
        ff = c_f_transfer(rt)
        print("C-F  interp band GAIN on a flat synthetic (n=%d): %s"
              % (ff["n"], "  ".join("%s:%.3f" % (bn, ff[bn]) for bn in HF_BANDS)))
        c = c_c_artefact(rt)
        print("C-C  ARTEFACT manufactured from <12 Hz only, engaged >=70 km/h, n=%d" % c["n"])
        for bn in HF_BANDS:
            if bn in c:
                o = c[bn]
                print("     %-6s real=%9.3f  artefact=%9.4f  art/real med=%.4f p90=%.4f"
                      % (bn, o["real_med"], o["art_med"], o["art_over_real_med"],
                         o["art_over_real_p90"]))
        dd = c_d_parked(rt)
        print("C-D  PARKED floor n=%d: %s" % (dd["n"], "  ".join("%s:%.3f" % (bn, dd[bn])
                                                                 for bn in HF_BANDS if bn in dd)))
        res[rt] = dict(zoh=a, runs=b, transfer=ff, artefact=c, parked=dd)
    (HERE / "_hf_lf_controls.json").write_text(json.dumps(res, indent=1))
    print("\nwrote", HERE / "_hf_lf_controls.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
