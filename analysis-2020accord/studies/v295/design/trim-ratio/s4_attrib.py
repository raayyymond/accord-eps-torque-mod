# -*- coding: utf-8 -*-
"""s4_attrib.py -- trim-ratio lens: can ONE SHORT DRIVE attribute each candidate on the EXISTING wire (the 427 tap,
0x18F rate, 0xE4)?  And does the candidate's fb clamp C ever bind (is C readable)?

Method (EVIDENCE for the arithmetic; the car's future x is BELIEF -- r71b's x is used as the excitation):
  * byte-exact 1 kHz harness Lane march over all 1.02 M r71b ticks for V294, the null (C = 0) and each candidate
    (plib inputs; the V294 row must equal plib's T1k_live bit for bit -- sanity).
  * FAKE CANDIDATE TAP = the real r71b tap - quant(V294 march) + quant(candidate march) at the tap's own ticks: the real
    drive's residual (tap LSB, 1 kHz vs 100 Hz operand, timing) is carried unchanged.
  * reads, on hands-off engaged tap frames (|bar| < 400, not pressed):
      E3     y = tap - quant(null) ~ 1 + Rm + pred + dFF/dt, Rm = lp1(-d/dt lp1(wire/8, 2.03 Hz), 5.05 Hz)  (the flown
             instrument, V294's pole) -> beta, T counts per deg/s^2 (V294 read +0.210)
      SCALE  y ~ 1 + m294 + pred + dFF/dt, m294 = quant(V294 march) - quant(null) -> 1.0 = V294's trim, G = G x V294
      SEL    rms(tap - quant(march_cells)) for every cell set: the smallest names the image
    pooled (10 s block bootstrap) and per 20 s window (the one-short-drive unit).
  * clamp census: fraction of engaged ticks with |r26| = C, per candidate.
Writes s4_attrib_out.txt.  Analysis only."""
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
import v295_harness as H  # noqa: E402
import plib as P  # noqa: E402

BASE = H.Cells.v294()
CELLS = [BASE.replace(name="V294"), BASE.replace(fb_clamp=0, name="null"),
         BASE.replace(name="b1134", fb_b=1134),
         BASE.replace(name="g3sh1", fb_b=850, e_shift=1, kp_y=(1920,) * 5, fb_clamp=512),
         BASE.replace(name="a1017g2", fb_a=1017, fb_b=567, e_shift=1, kp_y=(1920,) * 5, fb_clamp=512),
         BASE.replace(name="b1701", fb_b=1701),
         BASE.replace(name="b850", fb_b=850),
         BASE.replace(name="b964", fb_b=964)]


def lp1(xs, fc, fs=100.0):
    a = math.exp(-2 * math.pi * fc / fs)
    y = np.zeros_like(xs)
    s = xs[0]
    for i, v in enumerate(xs):
        s = a * s + (1 - a) * v
        y[i] = s
    return y


def ols(X, y):
    return np.linalg.lstsq(X, y, rcond=None)[0]


def main():
    t0 = time.time()
    d = H.route()
    n = len(d["t"])
    x1k = np.clip(np.round(d["x1k"]), -12000, 12000).astype(np.int64)
    L = H.Lane(CELLS)
    B = len(CELLS)
    sp = np.vstack([d["sgn"].astype(np.int64) * L.map_tab[j, d["idx"]] for j in range(B)])
    T, K = L.march(np.repeat(x1k[None, :], B, 0), sp, np.repeat(d["idx"][None, :], B, 0),
                   np.repeat(d["m"][None, :], B, 0), keep=("r26",))
    T = T * d["sg"]
    print("march %.0f s; V294 row == plib T1k_live: %s ; null row == plib T1k_null: %s" % (
        time.time() - t0, bool(np.array_equal(T[0], d["T1k_live"])), bool(np.array_equal(T[1], d["T1k_null"]))))
    eng1k = np.repeat(d["eng"], 10)[:T.shape[1]]
    print("\nclamp census (engaged ticks, |r26| == C):")
    for j, c in enumerate(CELLS):
        if c.fb_clamp == 0:
            continue
        r = K["r26"][j][eng1k]
        print("   %-8s C %5d : %.5f of %d engaged ticks bind ; max|r26| %d ; r26 p99.9 %.0f" % (
            c.name, c.fb_clamp, np.mean(np.abs(r) >= c.fb_clamp), r.size, np.abs(r).max(), np.percentile(np.abs(r), 99.9)))
    ticks = d["tick_tap"]
    j100 = d["j100"]
    q = {c.name: P.quant(T[j][ticks]) for j, c in enumerate(CELLS)}
    tap = d["T_tap"].astype(float)
    ho = d["eng"][j100] & (np.abs(d["bar"][j100]) < 400) & ~d["pressed"][j100]
    wire = np.nan_to_num(d["wire"]) / 8.0
    Rm = lp1(-np.gradient(lp1(wire, 2.03)) * 100.0, 5.05)[j100]
    pred = q["null"]
    dff = (np.gradient(d["T_null"]) * 100.0)[j100]
    m294 = q["V294"] - q["null"]
    tt = d["t"][j100] - d["t"][0]

    def reads(tp, mask):
        y = tp - pred
        X3 = np.column_stack([np.ones(mask.sum()), Rm[mask], pred[mask], dff[mask]])
        XS = np.column_stack([np.ones(mask.sum()), m294[mask], pred[mask], dff[mask]])
        return ols(X3, y[mask])[1], ols(XS, y[mask])[1]

    def boot(tp, nb=400, seed=1):
        idx = np.flatnonzero(ho)
        blk = np.floor(tt[idx] / 10.0).astype(int)
        groups = [idx[blk == u] for u in np.unique(blk)]
        rng = np.random.default_rng(seed)
        bs = []
        for _ in range(nb):
            ii = np.concatenate([groups[p] for p in rng.integers(0, len(groups), len(groups))])
            mk = np.zeros(len(tp), bool)
            mk[ii] = True
            bs.append(reads(tp, mk))
        bs = np.array(bs)
        return np.percentile(bs, 2.5, axis=0), np.percentile(bs, 97.5, axis=0)

    # 20 s hands-off windows (the one-short-drive unit): contiguous ho runs cut into 20 s pieces (tap is 50 Hz)
    wins = []
    for a, b in P.runs(ho, 1000):
        for s0 in range(a, b - 1000 + 1, 1000):
            wins.append((s0 + 50, s0 + 1000))
    print("\n%d hands-off tap frames (%.0f s), %d x 20 s windows" % (ho.sum(), ho.sum() / 50.0, len(wins)))
    names = [c.name for c in CELLS]
    print("\n%-8s  %-26s %-26s %-40s %s" % ("tap", "E3 beta pooled [95% CI]", "SCALE pooled [95% CI]",
                                             "per-20s-window E3 / SCALE median [5-95%]", "SEL: window-wise argmin rms"))
    for tapname in ["V294"] + [c.name for c in CELLS[2:]]:
        tp = tap if tapname == "V294" else tap - q["V294"] + q[tapname]
        b3, bS = reads(tp, ho)
        lo, hi = boot(tp)
        W3, WS, sel = [], [], []
        for a, b in wins:
            mk = np.zeros(len(tp), bool)
            mk[a:b] = True
            mk &= ho
            if mk.sum() < 500:
                continue
            e3, es = reads(tp, mk)
            W3.append(e3)
            WS.append(es)
            rm = [np.sqrt(np.mean((tp[mk] - q[nm][mk]) ** 2)) for nm in names]
            sel.append(names[int(np.argmin(rm))])
        W3, WS = np.array(W3), np.array(WS)
        hit = np.mean(np.array(sel) == tapname)
        print("%-8s  %+.3f [%+.3f,%+.3f]      %.3f [%.3f,%.3f]        E3 %+.3f [%+.3f,%+.3f] SC %.2f [%.2f,%.2f]   %.2f correct  (%s)" % (
            tapname, b3, lo[0], hi[0], bS, lo[1], hi[1], np.median(W3), np.percentile(W3, 5), np.percentile(W3, 95),
            np.median(WS), np.percentile(WS, 5), np.percentile(WS, 95), hit,
            {k: int(np.sum(np.array(sel) == k)) for k in set(sel)}))
    # pooled model-selection rms
    print("\npooled rms(tap - quant(march_cells)) on hands-off frames, rows = the tap, columns = the hypothesis:")
    print("%-8s " % "" + " ".join("%8s" % nm for nm in names))
    for tapname in ["V294"] + [c.name for c in CELLS[2:]]:
        tp = tap if tapname == "V294" else tap - q["V294"] + q[tapname]
        print("%-8s " % tapname + " ".join("%8.2f" % np.sqrt(np.mean((tp[ho] - q[nm][ho]) ** 2)) for nm in names))
    print("\ntotal %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
