# -*- coding: utf-8 -*-
"""s10_attr_finalists.py -- p-gain lens: the WIRE READ for the finalists (positive control on r71b's own data).

For each finalist c, a synthetic "flight" tap is built exactly as the real tap would read if c were on the car and the
command/rate were r71b's:  y_c = quant( byte-exact march of c on r71b's 0xE4 + 0x18F )  +  r71b's OWN tap residual
(tap - quant(V294 march)), so the noise is the real instrument's.  Three reads, each on hands-off engaged off-rail tap
frames, whole drive and per 20 s window:
  R1  identity on the CANDIDATE's own march:  y = a F_c + b R_c + k      -> a = b = 1 if c is live
  R2  identity on V294's march:               y = a F_294 + b R_294 + k  -> per demand-index bin, a = Kp_c(idx)/960
  R3  discrimination: resid(R1) < resid(R2) in every 20 s window        -> the edit is live (the null: V294 on the car
      reads resid(R1_c) > resid(R2) -- checked on r71b's REAL tap, which is V294)
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
from s6_attribution import regress, windows  # noqa: E402
from s8_finalists import finalists  # noqa: E402
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
BINS = [(0, 5), (5, 9), (9, 18), (18, 30), (30, 50), (50, 80), (80, 241)]


def main():
    d = P.load()
    base, F = finalists()
    tk, j = d["tick_tap"], d["j100"]
    y = d["T_tap"].astype(float)
    ok = d["ho"][j] & (np.abs(y) < 2300)
    noise = y - P.quant(d["T1k_live"][tk])
    x1k = np.clip(np.round(d["x1k"]), -12000, 12000).astype(np.int64)
    cl = F
    L = H.Lane(cl)
    Ln = H.Lane([c.replace(fb_clamp=0, name=c.name + "_null") for c in cl])
    sp = np.vstack([d["sgn"].astype(np.int64) * L.map_tab[i, d["idx"]] for i in range(L.B)])
    rep = lambda a: np.repeat(a[None, :], L.B, 0)  # noqa: E731
    t0 = time.time()
    T = L.march(rep(x1k), sp, rep(d["idx"]), rep(d["m"]))
    Tn = Ln.march(rep(x1k), sp, rep(d["idx"]), rep(d["m"]))
    print("marches %.0f s" % (time.time() - t0))
    F294 = d["T1k_null"][tk]
    R294 = d["T1k_live"][tk] - F294
    idx_t = d["idx"][j]
    out = {}
    # the null on the REAL r71b tap (V294 on the car): the candidate identities must fit WORSE than V294's
    W = windows(None, j, ok)
    for i, c in enumerate(cl):
        Fc = d["sg"] * Tn[i][tk]
        Rc = d["sg"] * T[i][tk] - Fc
        yc = P.quant(d["sg"] * T[i][tk]) + noise
        okc = ok & (np.abs(yc) < 2300)
        co1, r1, q1 = regress(yc, Fc, Rc, okc)
        co2, r2, q2 = regress(yc, F294, R294, okc)
        Wc = windows(None, j, okc)
        live_wins = sum(regress(yc, Fc, Rc, m)[1] < regress(yc, F294, R294, m)[1] for m in Wc)
        # null: the REAL tap (V294 flown) against the candidate's march vs V294's
        n1 = regress(y, Fc, Rc, ok)
        n2 = regress(y, F294, R294, ok)
        null_wins = sum(regress(y, Fc, Rc, m)[1] < regress(y, F294, R294, m)[1] for m in W)
        kp = H.lerp_table(c.kp_x, c.kp_y)
        print("\n%s  Kp X %s Y %s" % (c.name, c.kp_x, c.kp_y))
        print("  R1 identity on own march (synthetic flight): a %.4f b %.4f resid %.2f R2 %.5f" % (co1[0], co1[1], r1, q1))
        print("  R2 identity on V294 march (synthetic flight): a %.4f b %.4f resid %.2f R2 %.5f" % (co2[0], co2[1], r2, q2))
        print("  R3 own-march fits better in %d / %d 20 s windows (live)" % (live_wins, len(Wc)))
        print("  NULL (real r71b tap = V294): own-march a %.4f resid %.2f vs V294-march a %.4f resid %.2f; candidate fits better in %d / %d windows"
              % (n1[0][0], n1[1], n2[0][0], n2[1], null_wins, len(W)))
        byb = []
        for lo, hi in BINS:
            mb = okc & (idx_t >= lo) & (idx_t < hi)
            mb0 = ok & (idx_t >= lo) & (idx_t < hi)
            if mb.sum() < 200:
                continue
            cb, _, _ = regress(yc, F294, R294, mb)
            c0, _, _ = regress(y, F294, R294, mb0)
            want = float(np.mean(kp[idx_t[mb]] / 960.0))
            per_s = mb.sum() / 50.0
            byb.append(dict(bin=[lo, hi], sec=per_s, a=float(cb[0]), a_V294=float(c0[0]), ratio=float(cb[0] / c0[0]), expect=want))
            print("   idx %3d-%3d (%5.0f s of tap): a %.3f / V294's own %.3f = %.3f  (Kp/960 mean %.3f)" % (lo, hi, per_s, cb[0], c0[0], cb[0] / c0[0], want))
        # per 20 s window: the plateau ratio (idx 0-9) -- the ONE number a short drive reads
        pr = []
        for m in Wc:
            mm = m & (idx_t < 9)
            m0 = [w & (idx_t < 9) for w in W]
            if mm.sum() < 150:
                continue
            cb, _, _ = regress(yc, F294, R294, mm)
            pr.append(cb[0])
        base_pl = regress(y, F294, R294, ok & (idx_t < 9))[0][0]
        pr = np.array(pr) / base_pl
        print("  plateau ratio (idx 0-8) per 20 s window, / V294's own baseline %.3f: median %.3f [p2.5 %.3f, p97.5 %.3f] n %d"
              % (base_pl, np.median(pr), np.percentile(pr, 2.5), np.percentile(pr, 97.5), len(pr)))
        out[c.name] = dict(R1=dict(a=co1[0], b=co1[1], resid=r1, R2=q1), R2=dict(a=co2[0], b=co2[1], resid=r2, R2=q2),
                           live_windows=[int(live_wins), len(Wc)], null=dict(own_resid=n1[1], v294_resid=n2[1],
                                                                              cand_better_windows=[int(null_wins), len(W)]),
                           by_idx=byb, plateau_ratio_windows=pr.tolist())
    json.dump(out, open(os.path.join(OUT, "s10_attr_finalists.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
