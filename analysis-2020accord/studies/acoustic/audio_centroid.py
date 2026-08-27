#!/usr/bin/env python3
"""studies/acoustic/audio_centroid.py -- did the grind move UP in frequency?  Measured on the MICROPHONE.

The operator's V106 report: "grind #1/#2/#3 attenuated and the fundamental frequency has notably
increased (audible tone is higher pitch and more quiet)."  No CAN instrument could test this: every
bus channel is <=101 Hz sampled, Nyquist 50.57 Hz.  `rawAudioData` (16 kHz PCM, present from route
77) has no such ceiling.

STATISTIC: the power-weighted SPECTRAL CENTROID over 20-100 Hz of the engaged audio.  A centroid is
used instead of an argmax because a stationary-mode calibration showed argmax pipelines manufacture
+/-1.7 Hz/e-fold of fake frequency slope when the amplitude axis is independent of the band power
(`feedback-a-stationary-mode-returns-a-fake-frequency-slope`).  A centroid has no such failure mode:
it cannot scatter to a band centre, because it IS a weighted mean, and every window contributes.

CONTROLS, all reported, none optional:
  1  MUSIC     -- stratified by modpeak tercile (level- and speed-blind beat feature, 3.58 sd on
                  standstill ground truth).  The effect must survive in the LOW tercile.
  2  SPEED     -- computed inside speed bins; cross-build comparisons are within-bin only.
  3  ENGAGED   -- if this is the assist chain, it must be larger engaged than manual.
  4  BAND EDGE -- the centroid band is swept; a result that moves with the edges is the edges.
  5  BOOTSTRAP -- resampled over SEGMENTS, not windows.  Window bootstraps manufacture significance
                  (`feedback-episodes-not-windows`).
"""
import numpy as np

RT = [("9e", "V103"), ("a4", "V104"), ("a5", "V105"), ("a6", "V106")]
BINS = [(30, 50), (50, 70), (70, 95), (95, 130)]


def join(r):
    d = np.load(f"_audio_r{r}.npz", allow_pickle=True)
    fx = np.load(f"_audioflux_r{r}.npz", allow_pickle=True)
    rows = fx["rows"]
    cov = d["cov"]
    idx = {(int(s), round(t, 3)): i for i, (t, s, _, _) in enumerate(rows)}
    sel = np.array([idx.get((int(c[1]), round(c[0], 3)), -1) for c in cov])
    return d["psd"], d["freq"], cov, rows[np.clip(sel, 0, None)][:, 3]


def centroid(psd, freq, lo, hi):
    m = (freq >= lo) & (freq < hi)
    f, P = freq[m], psd[:, m]
    return (P * f).sum(axis=1) / (P.sum(axis=1) + 1e-30)


def boot_seg(vals, segs, n=4000, rng=None):
    rng = rng or np.random.default_rng(0)
    us = np.unique(segs)
    if len(us) < 3:
        return np.nan, np.nan
    out = np.empty(n)
    by = {s: vals[segs == s] for s in us}
    for i in range(n):
        pick = rng.choice(us, len(us), replace=True)
        out[i] = np.median(np.concatenate([by[s] for s in pick]))
    return np.percentile(out, 2.5), np.percentile(out, 97.5)


def table(lo_f, hi_f, terc, engaged=True, label=""):
    print(f"\n=== centroid {lo_f:.0f}-{hi_f:.0f} Hz | modpeak tercile {terc} | "
          f"{'ENGAGED' if engaged else 'MANUAL'} {label}")
    print("  speed      " + "".join(f"{b:>22}" for _, b in RT))
    for lo, hi in BINS:
        cells = []
        for r, _ in RT:
            psd, freq, cov, mp = join(r)
            v = cov[:, 2] * 3.6
            eng = cov[:, 3]
            m = (v >= lo) & (v < hi) & np.isfinite(mp)
            m &= (eng > 0.9) if engaged else (eng < 0.1)
            if m.sum() < 25:
                cells.append("        --            ")
                continue
            q = np.percentile(mp[m], [33.3, 66.7])
            m = m & {0: mp <= q[0], 1: (mp > q[0]) & (mp <= q[1]), 2: mp > q[1]}[terc]
            if m.sum() < 12:
                cells.append("        --            ")
                continue
            c = centroid(psd[m], freq, lo_f, hi_f)
            a, b = boot_seg(c, cov[m, 1])
            cells.append(f"{np.median(c):7.2f} [{a:5.1f},{b:5.1f}] n{m.sum():<4d}")
        print(f"  {lo:3d}-{hi:3d}  " + "".join(f"{c:>22}" for c in cells))


if __name__ == "__main__":
    table(20, 100, 0, True, "<- PRIMARY (least music)")
    table(20, 100, 1, True)
    table(20, 100, 2, True, "<- most music (CONTROL 1)")
    table(20, 100, 0, False, "<- CONTROL 3: manual")
    for a, b in [(18, 90), (22, 110), (20, 120), (25, 80)]:
        table(a, b, 0, True, "<- CONTROL 4: band sweep")
