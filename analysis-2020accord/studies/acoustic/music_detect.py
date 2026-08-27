#!/usr/bin/env python3
"""studies/acoustic/music_detect.py -- flag audio windows containing MUSIC, with the speed confound removed.

Operator, 2026-08-23: "sometimes there was music, you should find a way to separate out sections
with and without music playing."

CALIBRATION (route a6, 338 standstill windows -- no wind, no tyre noise, so anything above 300 Hz
is engine idle or cabin audio).  The 2-3 kHz band separates by 35-43 dB:
      quietest standstill windows   2-3 kHz = 43.5 .. 44.0 dB
      loudest  standstill windows   2-3 kHz = 77.5 .. 86.6 dB
=> 2-3 kHz is the discriminating band.  It is far above any mechanical grind, so excluding on it
   cannot bias the grind measurement toward any particular grind frequency.

THE CONFOUND: wind and tyre noise also raise the high bands (raw mid/high energy correlates
+0.52..+0.67 with vEgo), so an absolute threshold is a speed detector.  Fix: compare each window to
the QUIET FLOOR of its own speed bin -- the 15th percentile, not the median, because a median is
contaminated whenever music plays more than half the time in that bin.

CONTROL: an independent feature that never sees speed -- the movement of narrowband partials
between adjacent 0.512 s windows.  Music changes pitch; road noise and a mechanical resonance do
not.  Reporting both, and requiring the speed distributions of the two classes to be comparable,
is what keeps this from silently becoming a speed filter.
"""
import numpy as np

SPEED_EDGES = np.array([0, 2, 6, 12, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200.0])


def partial_move(psd, freq, lo=150.0, hi=500.0, prom_db=8.0):
    """Centroid movement of prominent narrowband partials. Never sees speed."""
    m = (freq >= lo) & (freq <= hi)
    P = 10.0 * np.log10(psd[:, m] + 1e-12)
    f = freq[m]
    k = 41
    pad = np.pad(P, ((0, 0), (k // 2, k // 2)), mode="edge")
    W = P - np.median(np.lib.stride_tricks.sliding_window_view(pad, k, axis=1), axis=2)
    ctr = np.full(len(P), np.nan)
    for i in range(len(P)):
        w = W[i]
        pk = np.where((w[1:-1] > w[:-2]) & (w[1:-1] > w[2:]) & (w[1:-1] > prom_db))[0] + 1
        if len(pk):
            ctr[i] = float(np.average(f[pk], weights=w[pk] - prom_db + 1e-9))
    return np.abs(np.diff(ctr, prepend=ctr[0]))


def detect(npz, db_thresh=8.0, floor_pct=15.0):
    d = np.load(npz, allow_pickle=True)
    cov, hi, psd, freq = d["cov"], d["hi"], d["psd"], d["freq"]
    hc = list(d["hicols"])
    v = cov[:, 2] * 3.6
    band = 10.0 * np.log10(hi[:, hc.index("2000-3000")].astype(float) + 1e-12)

    idx = np.clip(np.digitize(v, SPEED_EDGES) - 1, 0, len(SPEED_EDGES) - 2)
    excess = np.full(len(v), np.nan)
    for b in range(len(SPEED_EDGES) - 1):
        m = (idx == b) & np.isfinite(band)
        if m.sum() >= 25:
            excess[m] = band[m] - np.percentile(band[m], floor_pct)

    music = np.isfinite(excess) & (excess > db_thresh)
    return dict(v=v, eng=cov[:, 3], band=band, excess=excess, move=partial_move(psd, freq),
                music=music, clean=np.isfinite(excess) & ~music,
                cov=cov, psd=psd, freq=freq, hi=hi, hicols=hc)


if __name__ == "__main__":
    import sys
    for r in sys.argv[1:]:
        o = detect(f"_audio_r{r}.npz")
        mu, cl = o["music"], o["clean"]
        print(f"\nroute {r}: {len(mu)} windows -> MUSIC {mu.sum()} ({100*mu.mean():.1f}%)  clean {cl.sum()}")
        print(f"  speed p50   music {np.nanmedian(o['v'][mu]):6.1f}   clean {np.nanmedian(o['v'][cl]):6.1f} km/h"
              "   <- comparable => not a speed detector")
        print(f"  2-3kHz dB   music {np.nanmedian(o['band'][mu]):6.1f}   clean {np.nanmedian(o['band'][cl]):6.1f}")
        print(f"  partial move (CONTROL, speed-blind)"
              f"  music {np.nanmedian(o['move'][mu]):6.2f}   clean {np.nanmedian(o['move'][cl]):6.2f} Hz")
