# -*- coding: utf-8 -*-
"""rj7_wire_read.py -- lens robust-joint: can ONE short drive attribute each changed value on the EXISTING wire?

The pick changes two cal cells: the Kp bank level (FF gain g AND trim scale) and the fb gain b (trim scale).  On the
wire (427 tap = the delivered lane torque gp-0x6b38, 0x18F rate, 0xE4 command) they separate as:
    T_tap = c0 + c1 * FF_V294(cmd) + c2 * TRIM_V294(cmd, x)            (per 30 s window, OLS)
  where FF_V294 / TRIM_V294 are the byte-exact V294 null / live-minus-null marches on the drive's OWN recorded cmd and x.
  V294 reads (c1, c2) = (1, 1).  A V295 with FF gain g and trim t = Kp*b ratio reads (g, t) -- because FF is linear in Kp
  at a fixed map, and the trim at a fixed pole is linear in Kp*b (floors aside).
(1) the NULL distribution: the V294 tap on r71b, cut into 30 s windows of hands-off engaged tap frames -> (c1, c2) spread
(2) the POSITIVE CONTROL: a synthetic V295 tap = quant(V295 byte-exact march on r71b's own cmd/x) + r71b's REAL tap residual
    (tap - quant(V294 march)), same windows -> must recover (g, t) within the spread.  Candidates: the pick and neighbours.
(3) the byte-exact identity (G1 form): residual rms of the tap against the V294 march and against the V295 march.
ANALYSIS ONLY."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rj_cands as RC  # noqa: E402
from rj_lin import H  # noqa: E402
import plib as P  # noqa: E402


def windows(mask_tap, n_per=1500):
    idx = np.flatnonzero(mask_tap)
    return [idx[i:i + n_per] for i in range(0, len(idx) - n_per + 1, n_per)]


def ols(y, X):
    X1 = np.column_stack([np.ones(len(y))] + list(X))
    co, *_ = np.linalg.lstsq(X1, y, rcond=None)
    r = y - X1 @ co
    return co, float(np.sqrt(np.mean(r ** 2)))


def main():
    d = P.load()
    sg = d["sg"]
    tt = d["tick_tap"]
    j = d["j100"]
    ho = d["eng"][j] & ~d["pressed"][j] & (np.abs(d["bar"][j]) < 400)
    FF = d["T1k_null"][tt]
    TR = d["T1k_live"][tt] - d["T1k_null"][tt]
    Tq = d["T_tap"]
    resid = Tq - P.quant(d["T1k_live"][tt])
    W = windows(ho)
    print("hands-off engaged tap frames %d -> %d windows of 1500 (~30 s at the tap's ~50 Hz)" % (ho.sum(), len(W)))
    # (1) null distribution on the real V294 tap
    C = np.array([ols(Tq[w], (FF[w], TR[w]))[0] for w in W])
    print("(1) V294 real tap, per 30 s window: c1 (FF) median %.4f  [p5 %.4f, p95 %.4f]  sd %.4f | c2 (trim) median %.3f [p5 %.3f, p95 %.3f] sd %.3f"
          % (np.median(C[:, 1]), *np.percentile(C[:, 1], [5, 95]), C[:, 1].std(), np.median(C[:, 2]),
             *np.percentile(C[:, 2], [5, 95]), C[:, 2].std()))
    print("    trim rms per window (T counts): median %.1f  min %.1f ; FF rms median %.1f"
          % (np.median([TR[w].std() for w in W]), min(TR[w].std() for w in W), np.median([FF[w].std() for w in W])))
    # (2) positive control
    base = RC.base()
    cands = [("pick g1.20 t1.95", RC.make(g=1.2, t=1.95, name="p1")), ("g1.10 t1.95", RC.make(g=1.1, t=1.95, name="p2")),
             ("g1.20 t1.00", RC.make(g=1.2, t=1.0, name="p3")), ("g1.00 t1.95", RC.make(g=1.0, t=1.95, name="p4"))]
    L = H.Lane([c for _, c in cands] + [base])
    x1k = np.clip(np.round(d["x1k"]), -12000, 12000).astype(np.int64)
    B = L.B
    sp = d["sgn"][None, :].astype(np.int64) * L.map_tab[:, d["idx"]]
    T = L.march(np.repeat(x1k[None, :], B, 0), sp, np.repeat(d["idx"][None, :], B, 0), np.repeat(d["m"][None, :], B, 0))
    T294 = sg * T[-1]
    assert np.array_equal(T294, d["T1k_live"]), "the harness lane march != plib's V294 march"
    print("    harness Lane V294 march == plib T1k_live on all %d ticks (second method)" % len(T294))
    for k, (nm, c) in enumerate(cands):
        Tc = sg * T[k]
        syn = P.quant(Tc[tt]) + resid
        Cc = np.array([ols(syn[w], (FF[w], TR[w]))[0] for w in W])
        g_true = c.kp_y[0] / 960.0
        t_true = c.kp_y[0] * c.fb_b / (960.0 * 567.0)
        print("(2) %-18s design (g %.3f, t %.3f): recovered c1 median %.4f [p5 %.4f p95 %.4f] | c2 median %.3f [p5 %.3f p95 %.3f]"
              "  | windows with |c1-1| > 0.05: %d/%d, with c2 > 1.5: %d/%d"
              % (nm, g_true, t_true, np.median(Cc[:, 1]), *np.percentile(Cc[:, 1], [5, 95]), np.median(Cc[:, 2]),
                 *np.percentile(Cc[:, 2], [5, 95]), np.sum(np.abs(Cc[:, 1] - 1) > 0.05), len(W), np.sum(Cc[:, 2] > 1.5), len(W)))
        # (3) identity: residual vs the V294 march and vs the candidate's own march, hands-off
        r294 = np.sqrt(np.mean((syn[ho] - P.quant(T294[tt])[ho]) ** 2))
        rc = np.sqrt(np.mean((syn[ho] - P.quant(Tc[tt])[ho]) ** 2))
        print("    identity: synthetic-V295 tap vs V294 march %.2f counts rms, vs its own march %.2f" % (r294, rc))
    r_real = np.sqrt(np.mean((Tq[ho] - P.quant(T294[tt])[ho]) ** 2))
    print("(3) the REAL r71b tap vs the V294 march: %.2f counts rms (plib G1 3.64)" % r_real)


if __name__ == "__main__":
    main()
