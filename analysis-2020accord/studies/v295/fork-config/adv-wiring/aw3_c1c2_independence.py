# -*- coding: utf-8 -*-
"""aw3_c1c2_independence.py -- ADV "wiring+observability", part (c)/W9: is the FIRMWARE read (pooled OLS
tap = c0 + c1*FF + c2*TRIM, ADV-B protocol s6) independent of the FORK change?  Drive (1) = V295 + r1, drive (2) = V295 + r2alt:
both run V295; only the 0xE4 command differs.  If c2 moved with the command, the "identical on both drives" sentence is false.

Method: r71b's own inputs (x, bar, req) and ADV-B's byte-exact lane (advb_lane, cells read from the V294/V295 IMAGES),
with the command REPLACED by an r2alt-like command:
   wire' = wire - 4096 * k * (torque_r2alt - torque_r1)       (open-loop real-fork replay from aw2, ZOH to 1 kHz)
   k = 1.0 is a STRESS (open loop overstates the integrator change: 15-22 m/s rms 337 counts) ; k = 0.3 is milder.
Synthetic taps keep r71b's REAL residual (tap - quant(L4)) as the noise, per ADV-B's PA form:
   drive(1)  S1  = tap + quant(L5(wire))  - quant(L4(wire))      regressors FF=N4(wire),  TRIM=L4(wire)-N4(wire)
   drive(2)  S2k = tap + quant(L5(wire')) - quant(L4(wire))      regressors FF=N4(wire'), TRIM=L4(wire')-N4(wire')
   control   S0k = tap + quant(L4(wire')) - quant(L4(wire))      (V294 on the r2alt command: must read c2 ~0.99)
Frames = ADV-B's own hands-off settled mask (b5_frames.npz).  Second method = ADV-B's model selection (which march
reproduces the synthetic tap by rms), on the same frames.  x is NOT perturbed (the fork change moves the wheel too, but the
regression uses the measured x on both drives, so what matters is whether the lane stays linear in the new operating
region: max|T| vs the 2461 rail and the clamps).
ANALYSIS ONLY.
"""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
ADVB = os.path.join(KIT, "analysis-2020accord", "studies", "v295", "adversarial", "advB")
sys.path.insert(0, ADVB)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "lib"))
import b4_marches as B4  # noqa: E402
from advb_lane import cells_from_image  # noqa: E402

LOG = []


def pr(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


def quant(T):
    T = np.asarray(T, dtype=np.int64)
    return np.sign(T) * ((np.abs(T) >> 3) << 3)


M = dict(np.load(os.path.join(ADVB, "_scratch", "marches_d+4_lin.npz")))
F = dict(np.load(os.path.join(ADVB, "_scratch", "b5_frames.npz")))
HO = F["HO"]
tap = M["tap_T"].astype(np.int64)
tt = np.clip(M["tap_tick"], 0, len(M["L4"]) - 1)
I = B4.inputs(4.0, "lin")
assert np.array_equal(I["wire"].astype(np.int16), M["wire"]) and np.array_equal(I["x"].astype(np.int16), M["x"])
c4, c5 = cells_from_image("V294"), cells_from_image("V295")
pr("cells: V294 b %d, V295 b %d ; hands-off tap frames %d (%.0f s)" % (c4["b"], c5["b"], HO.sum(), HO.sum() / 50))

R = np.load(os.path.join(HERE, "_aw2_replay.npz"))
tk = I["t0"] + np.arange(I["n"]) * 1e-3
j = np.clip(np.searchsorted(R["t"], tk, side="right") - 1, 0, len(R["t"]) - 1)
dT = (R["torque_r2alt"] - R["torque_r1"])[j] * R["act"][j]


def ols(y, FF, TR):
    A = np.vstack([np.ones_like(FF), FF, TR]).T
    return np.linalg.lstsq(A, y, rcond=None)[0]


def block_ci(y, FF, TR, idx, secs=10, nb=400, seed=1):
    rng = np.random.default_rng(seed)
    n = secs * 50
    blocks = [idx[i:i + n] for i in range(0, len(idx), n)]
    cs = []
    for _ in range(nb):
        pick = np.concatenate([blocks[q] for q in rng.integers(0, len(blocks), len(blocks))])
        cs.append(ols(y[pick], FF[pick], TR[pick]))
    cs = np.array(cs)
    return np.percentile(cs[:, 1], [2.5, 97.5]), np.percentile(cs[:, 2], [2.5, 97.5])


def gated_windows(TR, secs=15):
    idx = np.flatnonzero(HO)
    n = secs * 50
    return [w for w in (idx[i:i + n] for i in range(0, len(idx) - n + 1, n)) if np.sqrt(np.mean(TR[w] ** 2)) >= 4.0]


def score(label, y, FF, TR, trueL, altL):
    idx = np.flatnonzero(HO)
    c = ols(y[HO].astype(float), FF[HO], TR[HO])
    ci1, ci2 = block_ci(y.astype(float), FF, TR, idx)
    wins = gated_windows(TR)
    c2w = np.array([ols(y[w].astype(float), FF[w], TR[w])[2] for w in wins])
    rms_true = np.sqrt(np.mean((y - quant(trueL))[HO] ** 2))
    rms_alt = np.sqrt(np.mean((y - quant(altL))[HO] ** 2))
    pr("   %-44s pooled c1 %.3f [%.3f, %.3f]  c2 %.3f [%.3f, %.3f] ; gated 15 s windows %d: c2 min %.2f med %.2f max %.2f,"
       " > 1.45: %d ; model selection rms V295-march %.2f vs V294-march %.2f"
       % (label, c[1], ci1[0], ci1[1], c[2], ci2[0], ci2[1], len(wins), c2w.min(), np.median(c2w), c2w.max(),
          int(np.sum(c2w > 1.45)), rms_true if "V295" in label else rms_alt, rms_alt if "V295" in label else rms_true))
    return c


N4 = M["N4"].astype(np.int64)[tt]; L4 = M["L4"].astype(np.int64)[tt]; L5 = M["L5"].astype(np.int64)[tt]
FF1, TR1 = N4.astype(float), (L4 - N4).astype(float)
resid = tap - quant(L4)
pr("\nDRIVE (1) = V295 + r1 command (r71b's own wire)")
S1 = tap + quant(L5) - quant(L4)
score("S1 V295 on r1 command", S1, FF1, TR1, L5, L4)
score("NULL real r71b tap (V294, calibration step)", tap, FF1, TR1, L4, L5)

for k in (0.3, 1.0):
    t_ = time.time()
    wire2 = np.clip(np.round(I["wire"] - 4096.0 * k * dT), -4096, 4096).astype(np.int64)
    I2 = dict(I)
    I2["wire"] = wire2
    eng = I["req"] > 0
    dw = (wire2 - I["wire"])[eng]
    N4b = B4.march(c4, I2, trim=False).astype(np.int64)
    L4b = B4.march(c4, I2).astype(np.int64)
    L5b = B4.march(c5, I2).astype(np.int64)
    pr("\nDRIVE (2) stand-in, k = %.1f: |wire' - wire| on req frames rms %.0f max %.0f counts ; max|L5'| %d (rail 2461) ; "
       "%.0f s" % (k, np.sqrt(np.mean(dw.astype(float) ** 2)), np.abs(dw).max(), np.abs(L5b).max(), time.time() - t_))
    n4, l4, l5 = N4b[tt], L4b[tt], L5b[tt]
    FF2, TR2 = n4.astype(float), (l4 - n4).astype(float)
    pr("   TRIM regressor rms on HO frames: drive(1) %.2f, drive(2) %.2f counts ; corr(FF, TRIM) drive(1) %.3f drive(2) %.3f"
       % (np.sqrt(np.mean(TR1[HO] ** 2)), np.sqrt(np.mean(TR2[HO] ** 2)), np.corrcoef(FF1[HO], TR1[HO])[0, 1],
          np.corrcoef(FF2[HO], TR2[HO])[0, 1]))
    S2 = resid + quant(l5)
    score("S2 V295 on r2alt-like command", S2, FF2, TR2, l5, l4)
    S0 = resid + quant(l4)
    score("S0 V294 on r2alt-like command (control)", S0, FF2, TR2, l4, l5)
    # the analyst error: drive (2) scored with drive (1)'s regressors
    c_bad = ols(S2[HO].astype(float), FF1[HO], TR1[HO])
    pr("   [misuse] S2 regressed on drive (1)'s regressors instead of its own: c1 %.3f c2 %.3f" % (c_bad[1], c_bad[2]))

open(os.path.join(HERE, "out", "aw3_c1c2_independence_out.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
