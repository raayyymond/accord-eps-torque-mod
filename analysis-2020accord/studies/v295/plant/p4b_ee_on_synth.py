# -*- coding: utf-8 -*-
"""p4b_ee_on_synth.py -- how biased are the EQUATION-ERROR estimators (p4: OLS, IV-ff) in a world where the truth is KNOWN?
python p4b_ee_on_synth.py -> p4b_ee_on_synth_out.txt

The G3a synthetic worlds of p5 (J 0.20, b 2.0, k = band scale, Fc 30, Fs 39, tau 2 ms, the flown command through the
byte-exact lane, a 1 Hz coloured road disturbance of 15 T counts rms) are regenerated on ALL segments of each band and
the p4 regressions are run on them exactly as on the drive (8 Hz zero-phase LP, al = central difference, tanh friction,
per-segment constants).  No fork outer loop exists in the synthetic world, so IV-ff is a VALID instrument there: the gap
between OLS and IV-ff here is the bias the TRIM + road disturbance put into OLS; on the drive the IVs are additionally
exposed to the outer loop (p4 header), which this control cannot reproduce.
"""
import math
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oe_lib as O  # noqa: E402
import p5_oe_fit as P5  # noqa: E402
import plib as P  # noqa: E402
import v294_plant as VP  # noqa: E402
from p4_plant_td import instr_bank, tsls, demean_blocks  # noqa: E402

FS = 100.0


def lpf(x, fc=8.0):
    sos = signal.butter(4, fc / (FS / 2), output="sos")
    return signal.sosfiltfilt(sos, x, axis=-1)


def main():
    d = P.load()
    c = VP.v294_cells()
    segs = O.segments(d)
    lines = []
    for bi, (bn, lo, hi) in enumerate(P.BANDS):
        ss = [s for s in segs if s["band"] == bi]
        Bx = O.Batch(d, ss, c)
        truth = (P5.TRUTH["J"], P5.TRUTH["b"], P5.START_K[bi], P5.TRUTH["Fc"], P5.TRUTH["Fs"])
        uff = np.zeros_like(Bx.u)
        for i, s in enumerate(ss):
            n = s["b"] - s["a"]
            uff[i, :n] = d["u_ff"][s["a"]:s["b"]]
            uff[i, n:] = uff[i, n - 1]
        P5._synthesise(Bx, O.band_member(*truth, P5.TAU), seed=101 + bi)
        om = lpf(Bx.om)
        th = lpf(Bx.th)
        al = np.gradient(om, axis=1) * FS
        u = lpf(Bx.u)
        sg = np.tanh(om / 0.5)
        rows_X, rows_y, rows_Z, rid = [], [], [], []
        for i in range(Bx.B):
            mk = Bx.mask[i]
            rows_X.append(np.column_stack([al[i], om[i], th[i], sg[i]])[mk])
            rows_y.append(u[i][mk])
            rows_Z.append(instr_bank(uff[i])[mk])
            rid.append(np.full(mk.sum(), i))
        X, y, Z, rid = np.vstack(rows_X), np.concatenate(rows_y), np.vstack(rows_Z), np.concatenate(rid)
        Xd, yd, Zd = demean_blocks(X, rid), demean_blocks(y, rid)[:, 0], demean_blocks(Z, rid)
        ols = np.linalg.lstsq(Xd, yd, rcond=None)[0]
        Q, _ = np.linalg.qr(Zd)
        omh = Q @ (Q.T @ Xd[:, 1])
        iv = tsls(yd, Xd, np.column_stack([Zd, np.sign(omh)]))
        ln = ("band %-6s (%3.0f s): TRUTH J %.3f b %.2f k %.1f Fc %.1f | OLS J %.3f (x%.2f) b %.2f (x%.2f) k %.1f (x%.2f) Fc %.1f"
              " | IV-ff J %.3f (x%.2f) b %.2f (x%.2f) k %.1f (x%.2f) Fc %.1f" % (
                  bn, Bx.mask.sum() / FS, truth[0], truth[1], truth[2], truth[3], ols[0], ols[0] / truth[0], ols[1],
                  ols[1] / truth[1], ols[2], ols[2] / truth[2], ols[3], iv[0], iv[0] / truth[0], iv[1], iv[1] / truth[1],
                  iv[2], iv[2] / truth[2], iv[3]))
        print(ln, flush=True)
        lines.append(ln)
    open(os.path.join(HERE, "p4b_ee_on_synth_out.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
