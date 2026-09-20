"""ADVERSARY A6 - how big is the ESTIMATOR's own bias, and is it GROUP-DEPENDENT?

The comparison pools 93 windows for V282 and 12 / 6 / 3 / 4 for the torque groups, at coherences 0.97 down to
0.63. Two biases scale with exactly those two things:

  * magnitude-averaging the cross-spectrum (|Pxy| summed over windows, the study's own fix for the phasor bias)
    is POSITIVELY biased when coherence < 1, because E|z| > |E z| for a noisy complex z. With ONE window per bin
    it degenerates exactly to the amplitude ratio sqrt(Pyy/Pxx), which is inflated by output noise. The bias
    shrinks as the number of windows grows - so the group with 93 windows is measured with a smaller bias than
    the group with 3.
  * complex-averaging (the modulus taken after summing) is NEGATIVELY biased whenever the phase varies across
    the pooled windows.

Both push V282 and torque mode in opposite directions. This script measures the bias of each estimator against a
KNOWN truth, at the n and coherence each real group actually has, and asks whether the measured 0.20 gap at
0.08-0.25 Hz could be manufactured.

usage: python a6_estimator_bias.py
"""
import sys
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from a2_hindep import windows, band_stats, FS

rng = np.random.default_rng(11)
NPS = 4096
f = np.fft.rfftfreq(NPS, 1 / FS)
BAND = (0.08, 0.25)
BAND3 = (0.30, 0.60)


def lp(x, fc, order=2):
    return signal.sosfiltfilt(signal.butter(order, fc, btype="low", fs=FS, output="sos"), x)


def make(nwin, Htrue, coh_target, lagspread_s=0.0, band=BAND, nps=NPS):
    """nwin independent windows of a first-order-ish plant with gain Htrue, output noise sized to hit the target
    band coherence, and an optional window-to-window lag spread."""
    Ws = []
    for i in range(nwin):
        n = nps
        x = lp(rng.standard_normal(n * 2), 0.5)[:n] * 30
        lag = int(rng.uniform(0, lagspread_s) * FS)
        y = Htrue * (np.concatenate([np.zeros(lag), x[:-lag]]) if lag else x.copy())
        # size the noise for the wanted coherence: coh = S/(S+N) in band
        nse = lp(rng.standard_normal(n * 2), 0.6)[:n]
        sx = float(np.std(signal.sosfiltfilt(signal.butter(2, band, btype="band", fs=FS, output="sos"), y)))
        sn = float(np.std(signal.sosfiltfilt(signal.butter(2, band, btype="band", fs=FS, output="sos"), nse)))
        k = sx / max(sn, 1e-12) * np.sqrt(max(1.0 / coh_target - 1.0, 0.0))
        y = y + k * nse
        for pxx, pyy, pxy, _ in windows(x, y, nps, nps):
            Ws.append(dict(pxx=pxx, pyy=pyy, pxy=pxy))
    return Ws


print("=== bias of each band-|H| estimator vs a KNOWN truth, at the n and coherence the real groups have ===")
print(f"{'case':34s} {'nwin':>5s} {'cohTgt':>6s} {'Hmag':>6s} {'Hphas':>6s} {'R':>6s} {'cohMeas':>7s} {'biasMag':>8s} {'biasPhas':>8s}")
CASES = [("V282-like  0.08-0.25", 93, 0.97, 0.0), ("T64-like   0.08-0.25", 12, 0.95, 0.0),
         ("T64B-like  0.08-0.25", 6, 0.97, 0.0), ("T5-like    0.08-0.25", 3, 0.95, 0.0),
         ("T4-like    0.08-0.25", 4, 0.95, 0.0),
         ("V282-like  0.30-0.60", 93, 0.84, 0.0), ("T64-like   0.30-0.60", 12, 0.90, 0.0),
         ("T5-like    0.30-0.60", 3, 0.85, 0.0),
         ("V282-like  0.60-1.20", 93, 0.84, 0.0), ("T4-like    0.60-1.20", 4, 0.63, 0.0)]
REP = 24
for name, nwin, coh, spread in CASES:
    bm, bp, bR, cm = [], [], [], []
    band = BAND if "0.08" in name else (BAND3 if "0.30" in name else (0.6, 1.2))
    for _ in range(REP):
        Ws = make(nwin, 1.00, coh, spread, band)
        st = band_stats(Ws, f, *band)
        bm.append(st["H_mag"]); bp.append(st["H_phas"]); bR.append(st["R"]); cm.append(st["coh"])
    print(f"{name:34s} {nwin:5d} {coh:6.2f} {np.mean(bm):6.3f} {np.mean(bp):6.3f} {np.mean(bR):6.3f} "
          f"{np.mean(cm):7.3f} {np.mean(bm)-1:+8.3f} {np.mean(bp)-1:+8.3f}")

print("\n=== the group-dependent part: same TRUE |H| = 1, V282's (n=93, coh 0.97) vs T5's (n=3, coh 0.95) ===")
d = []
for _ in range(40):
    a = band_stats(make(93, 1.0, 0.97), f, *BAND)["H_mag"]
    b = band_stats(make(3, 1.0, 0.95), f, *BAND)["H_mag"]
    d.append(b - a)
print(f"  apparent |H| difference from ESTIMATOR ALONE: {np.mean(d):+.4f} +/- {np.std(d):.4f} "
      f"(the real V282->T64 gap to explain is +0.21)")

print("\n=== and at 0.60-1.20 Hz, where coherence really is 0.63-0.84 ===")
d = []
for _ in range(40):
    a = band_stats(make(93, 1.0, 0.84, band=(0.6, 1.2)), f, 0.6, 1.2)["H_mag"]
    b = band_stats(make(4, 1.0, 0.63, band=(0.6, 1.2)), f, 0.6, 1.2)["H_mag"]
    d.append(b - a)
print(f"  apparent |H| difference from ESTIMATOR ALONE: {np.mean(d):+.4f} +/- {np.std(d):.4f}")

print("\n=== phase spread: what a within-group lag spread does to each estimator (n=12, coh 0.95) ===")
for spread in (0.0, 0.2, 0.4):
    r = [band_stats(make(12, 1.0, 0.95, spread, b), f, *b) for b in (BAND, BAND3) for _ in range(12)]
    m1 = np.mean([x["H_mag"] for x in r[:12]]); p1 = np.mean([x["H_phas"] for x in r[:12]])
    m3 = np.mean([x["H_mag"] for x in r[12:]]); p3 = np.mean([x["H_phas"] for x in r[12:]])
    print(f"  spread 0-{spread:.1f} s: band1 Hmag {m1:.3f} Hphas {p1:.3f} | band3 Hmag {m3:.3f} Hphas {p3:.3f}")
