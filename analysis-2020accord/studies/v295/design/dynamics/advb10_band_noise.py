"""ADV-bytes step 10: can the SYMPTOM-side band read (hard-turn 1.6-3 Hz wheel-rate rms, 5-15 m/s) resolve the design's
predicted x0.89-0.98 in one drive?  Null spread from r71b itself (a V294 flight against itself): split its hard-turn
15 s windows into two random groups of k windows (k = 1, 2, 4, 8 = 15 s .. 2 min of hard-turn driving) and read the
ratio of group means.  If the 90 % null interval is wider than the predicted effect, the band read cannot see it."""
import os, sys
import numpy as np
from scipy import signal as S
HERE = os.path.dirname(os.path.abspath(__file__))
V295 = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(V295, "plant")); sys.path.insert(0, os.path.join(V295, "lib"))
import plib as P  # noqa: E402
d = P.load()
om = np.nan_to_num(d["om"]); sos = S.butter(2, [1.6, 3.0], "bandpass", fs=100, output="sos")
rb = S.sosfiltfilt(sos, om)
n = 1500
W = []
for s0 in range(0, len(om) - n, n):
    sl = slice(s0, s0 + n)
    if d["eng"][sl].mean() >= 0.8 and 5.0 <= d["v"][sl].mean() < 15.0:
        W.append((float(np.abs(d["cmd"][sl]).mean()), float(np.sqrt(np.mean(rb[sl] ** 2)))))
W = np.array(W)
hard = W[W[:, 0] >= np.percentile(W[:, 0], 50)]
pr = []
pr.append("15 s engaged windows at 5-15 m/s: %d; hard-turn half (|cmd| >= median): %d; 1.6-3 Hz rate rms med %.2f deg/s, "
          "CV %.2f" % (len(W), len(hard), np.median(hard[:, 1]), np.std(hard[:, 1]) / np.mean(hard[:, 1])))
rng = np.random.default_rng(3)
for k in (1, 2, 4, 8):
    if 2 * k > len(hard):
        break
    R = []
    for _ in range(4000):
        ii = rng.permutation(len(hard))
        R.append(hard[ii[:k], 1].mean() / hard[ii[k:2 * k], 1].mean())
    R = np.array(R)
    pr.append("  k = %d windows per 'drive' (%3d s of hard-turn driving): null ratio 5-95 %% [%.2f, %.2f]; P(ratio <= 0.94) %.2f, "
              "P(<= 0.89) %.2f" % (k, 15 * k, np.percentile(R, 5), np.percentile(R, 95), np.mean(R <= 0.94), np.mean(R <= 0.89)))
print("\n".join(pr))
open(os.path.join(HERE, "advb10_band_noise_out.txt"), "w").write("\n".join(pr) + "\n")
