# -*- coding: utf-8 -*-
"""s6_attribution.py -- p-gain lens: can ONE short drive read the changed value on the EXISTING wire?

Instrument: the 427 tap (50 Hz, 8-count quantiser) against the byte-exact V294 march of the SAME drive's own 0xE4
command and 0x18F rate, split into its FF part F (fb operand forced 0) and its trim part R (= live - F).
Regression, hands-off laterally engaged tap frames, |T| < 2300 (off the rail):  T_tap = a*F + b*R + c.
  V294 as flown          -> a = b = 1 (the NULL: this is what "the new cells are not live" reads as)
  flat Kp x g            -> a = b = g   (Kp multiplies the FF and the trim alike)
  a Kp(idx) schedule     -> a(idx) = Kp(idx)/960 per demand-index bin, b(idx) likewise
Method: (1) the regression on r71b itself, whole drive and in every 20 s window (the resolution one short drive
buys); (2) POSITIVE CONTROL: the candidate lane marched byte-exact on r71b's recorded command and rate, quantised like
the tap, plus r71b's OWN tap residual (tap - V294 prediction) as the noise -> the same regression must recover g
(and a Kp schedule's shape by idx bin) in every 20 s window.  Open loop (the command is r71b's), which is what the
regression conditions on anyway.
ANALYSIS ONLY."""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pg_lib as G  # noqa: E402
H = G.H
import plib as P  # noqa: E402
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def regress(y, F, R, mask):
    X = np.vstack([F[mask], R[mask], np.ones(mask.sum())]).T
    co, *_ = np.linalg.lstsq(X, y[mask], rcond=None)
    res = y[mask] - X @ co
    r2 = 1 - np.sum(res ** 2) / max(np.sum((y[mask] - y[mask].mean()) ** 2), 1e-9)
    return co, float(np.sqrt(np.mean(res ** 2))), float(r2)


def windows(n_frames_mask, j100, ok, secs=20.0):
    """20 s windows on the 100 Hz frame axis, returning tap-frame masks with >= 500 usable tap frames."""
    out = []
    step = int(secs * 100)
    for a in range(0, int(j100.max()) + 1, step):
        m = ok & (j100 >= a) & (j100 < a + step)
        if m.sum() >= 500:
            out.append(m)
    return out


def main():
    d = P.load()
    base = H.Cells.v294()
    tk = d["tick_tap"]
    j = d["j100"]
    F = d["T1k_null"][tk]
    R = d["T1k_live"][tk] - F
    y = d["T_tap"].astype(float)
    ok = d["ho"][j] & (np.abs(y) < 2300)
    print("tap frames usable (hands-off engaged, off-rail): %d (%.0f s)" % (ok.sum(), ok.sum() / 50))
    co, rms, r2 = regress(y, F, R, ok)
    print("(1) r71b whole drive: a %.4f  b %.4f  c %+.2f  resid %.2f  R2 %.5f   (V294 flown: expect a = b = 1)" % (co[0], co[1], co[2], rms, r2))
    W = windows(None, j, ok)
    A = np.array([regress(y, F, R, m)[0] for m in W])
    print("    20 s windows (%d): a median %.4f  [p2.5 %.4f, p97.5 %.4f]   b median %.3f  [p2.5 %.3f, p97.5 %.3f]" % (
        len(W), np.median(A[:, 0]), np.percentile(A[:, 0], 2.5), np.percentile(A[:, 0], 97.5), np.median(A[:, 1]),
        np.percentile(A[:, 1], 2.5), np.percentile(A[:, 1], 97.5)))
    res = dict(r71b=dict(a=co[0], b=co[1], c=co[2], rms=rms, R2=r2, win_a=A[:, 0].tolist(), win_b=A[:, 1].tolist()))
    # (2) positive controls: candidate lanes marched on r71b, + r71b's own tap residual
    noise = y - P.quant(d["T1k_live"][tk])
    from s3_shapes import cands
    C = {c.name: c for c in cands()}
    cl = [C["g1.2"], C["g1.3"], C["K-regress"], C["M-regress"]]
    x1k = np.clip(np.round(d["x1k"]), -12000, 12000).astype(np.int64)
    L = H.Lane(cl)
    t0 = time.time()
    sp = np.vstack([d["sgn"].astype(np.int64) * L.map_tab[i, d["idx"]] for i in range(L.B)])
    T = L.march(np.repeat(x1k[None, :], L.B, 0), sp, np.repeat(d["idx"][None, :], L.B, 0), np.repeat(d["m"][None, :], L.B, 0))
    print("    candidate march %.0f s" % (time.time() - t0))
    idx_t = d["idx"][j]
    bins = [(0, 6), (6, 14), (14, 25), (25, 40), (40, 70), (70, 241)]
    for i, c in enumerate(cl):
        yc = P.quant(d["sg"] * T[i][tk]) + noise
        okc = ok & (np.abs(yc) < 2300)
        co, rms, r2 = regress(yc, F, R, okc)
        Wc = windows(None, j, okc)
        Ac = np.array([regress(yc, F, R, m)[0] for m in Wc])
        kp = H.lerp_table(c.kp_x, c.kp_y)
        print("(2) %-10s whole: a %.4f b %.4f resid %.2f R2 %.5f | 20 s windows: a %.4f [%.4f, %.4f]  b %.3f [%.3f, %.3f]" % (
            c.name, co[0], co[1], rms, r2, np.median(Ac[:, 0]), np.percentile(Ac[:, 0], 2.5), np.percentile(Ac[:, 0], 97.5),
            np.median(Ac[:, 1]), np.percentile(Ac[:, 1], 2.5), np.percentile(Ac[:, 1], 97.5)))
        byb = []
        for lo, hi in bins:
            mb = okc & (idx_t >= lo) & (idx_t < hi)
            if mb.sum() < 200:
                continue
            cb, _, _ = regress(yc, F, R, mb)
            want_a = float(np.mean(G.surface_table(c)[np.clip(idx_t[mb], 1, 240)] / np.maximum(G.surface_table(base)[np.clip(idx_t[mb], 1, 240)], 1)))
            want_b = float(np.mean(kp[idx_t[mb]] / 960.0))
            byb.append(dict(bin=(lo, hi), n=int(mb.sum()), a=float(cb[0]), b=float(cb[1]), expect_a=want_a, expect_b=want_b))
            print("       idx %3d-%3d n %5d: a %.3f (surface ratio %.3f)  b %.3f (Kp/960 %.3f)" % (lo, hi, mb.sum(), cb[0], want_a, cb[1], want_b))
        res[c.name] = dict(a=co[0], b=co[1], rms=rms, R2=r2, win_a=Ac[:, 0].tolist(), win_b=Ac[:, 1].tolist(), by_idx=byb)
    # the null on r71b itself by idx bin (what V294 reads -> the comparison for a schedule)
    print("(1b) r71b (V294) by idx bin:")
    for lo, hi in bins:
        mb = ok & (idx_t >= lo) & (idx_t < hi)
        if mb.sum() < 200:
            continue
        cb, _, _ = regress(y, F, R, mb)
        print("       idx %3d-%3d n %5d: a %.3f  b %.3f" % (lo, hi, mb.sum(), cb[0], cb[1]))
    json.dump(res, open(os.path.join(OUT, "s6_attribution.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
