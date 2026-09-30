"""b8_second_method.py -- ADV-B step 8: a SECOND, model-selection form of the wire read (no regression): which image's
march reproduces the tap?  rms(tap - quant(march_V294)) vs rms(tap - quant(march_V295)) on hands-off settled frames,
pooled and per 15 s window, for the REAL r71b tap (V294 on the car) and the synthetic V295 taps (PA, PB2).
Run: python b8_second_method.py > b8_second_method_out.txt
"""
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def quant(T):
    T = np.asarray(T, dtype=np.int64)
    return np.sign(T) * ((np.abs(T) >> 3) << 3)


M = dict(np.load(os.path.join(HERE, "_scratch", "marches_d+4_lin.npz")))
F = dict(np.load(os.path.join(HERE, "_scratch", "b5_frames.npz")))
HO = F["HO"]
tt = np.clip(M["tap_tick"], 0, len(M["L4"]) - 1)
tap = M["tap_T"].astype(np.int64)
L4 = M["L4"].astype(np.int64)[tt]; L5 = M["L5"].astype(np.int64)[tt]; I5 = M["I5"].astype(np.int64)[tt]
S = dict(NULL=tap, PA=tap + quant(L5) - quant(L4),
         PB2=quant(np.round(L5 + (1050 / 567) * (tap + 4 * np.sign(tap) - L4))), INV5=tap + quant(I5) - quant(L4))
idx = np.flatnonzero(HO)
wins = [idx[i:i + 750] for i in range(0, len(idx) - 749, 750)]
TR = (L4 - M["N4"].astype(np.int64)[tt]).astype(float)
for k, y in S.items():
    r4 = np.sqrt(np.mean((y - quant(L4))[idx] ** 2)); r5 = np.sqrt(np.mean((y - quant(L5))[idx] ** 2))
    ri = np.sqrt(np.mean((y - quant(I5))[idx] ** 2))
    pick5 = []
    pick5g = []
    for w in wins:
        a = np.mean((y - quant(L4))[w] ** 2); b = np.mean((y - quant(L5))[w] ** 2)
        pick5.append(b < a)
        if np.sqrt(np.mean(TR[w] ** 2)) >= 4:
            pick5g.append(b < a)
    print("%-5s pooled HO rms vs V294 march %.2f | vs V295 march %.2f | vs inverted-V295 %.2f ; 15 s windows choosing V295:"
          " %d/%d (gated: %d/%d)" % (k, r4, r5, ri, sum(pick5), len(pick5), sum(pick5g), len(pick5g)))
