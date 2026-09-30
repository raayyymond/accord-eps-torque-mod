# -*- coding: utf-8 -*-
"""ADV-A a4: the restart pulse (filter bail -> sentinel 2 -> next tick reads s_old = 0) over the FULL demand
envelope idx 0..240 x demand sign x rate sign, at 10/30/100/300/1500 deg/s (x = 8 counts per deg/s, 1500 = the
guard), for V294 and V295, from BOTH ends of the output lag's fixed-point interval.  Bail lengths 1 (the design's
case) and 2/5/20/100 ticks (b-dependent part reported as |T295 - T294| on the same lane).
Pulse = max |T - T_pre| over the bail tick(s) + 1500 restart ticks (and the same excluding the bail ticks).
The vector lane is validated tick-for-tick against the scalar mirror (advA_lane) on 24 lanes first."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import advA_lane as A  # noqa: E402
import advA_vec as V  # noqa: E402

J = json.load(open(os.path.join(HERE, "a1_cells.json")))
IDX = np.arange(241)
lanes = [(i, ds, rs) for i in IDX for ds in (1, -1) for rs in (1, -1)]
NL = len(lanes)
li = np.array([l[0] for l in lanes]); lds = np.array([l[1] for l in lanes]); lrs = np.array([l[2] for l in lanes])


def run(c, rate, end, bail_len=1, n_after=1500, want_trace=False):
    """end: 'lo' / 'hi' end of the output-lag fixed-point interval (also 'boot' = wherever the cold march lands)."""
    VL = V.VecLane(c, NL)
    x = (lrs * int(round(8 * rate))).astype(np.int64)
    sp = lds * VL.map_tab[li]
    for _ in range(3000):
        VL.tick(x, sp, li)
    # the output-lag fixed-point interval at the settled S
    S = VL.last["S"].copy()
    assert np.all(VL.last["r26"] == 0), "fb not settled"
    q = (S * VL.lb) >> 10
    if end in ("lo", "hi"):
        o_new = VL.o.copy()
        for j in range(NL):
            base = int(VL.o[j])
            fx = [o for o in range(base - 200, base + 200) if o == ((int(VL.la) * o) >> 10) + int(q[j])]
            assert fx, (j, base)
            o_new[j] = fx[0] if end == "lo" else fx[-1]
        VL.o = o_new
    T = None
    for _ in range(300):
        T = VL.tick(x, sp, li)
    T_pre = T.copy()
    T2 = VL.tick(x, sp, li)
    assert np.array_equal(T2, T_pre), "T not settled before the bail"
    trace = []
    pk_all = np.zeros(NL, np.int64); pk_after = np.zeros(NL, np.int64); sg = np.zeros(NL, np.int64)
    for k in range(bail_len + n_after):
        bail = k < bail_len
        T = VL.tick(x, sp, li, bail=np.full(NL, bail))
        d = T - T_pre
        upd = np.abs(d) > pk_all
        sg = np.where(upd, d, sg)
        pk_all = np.maximum(pk_all, np.abs(d))
        if not bail:
            pk_after = np.maximum(pk_after, np.abs(d))
        if want_trace:
            trace.append(T.copy())
    return dict(T_pre=T_pre, pk_all=pk_all, pk_after=pk_after, signed=sg, maxp=VL.maxp,
                trace=np.array(trace) if want_trace else None)


def main():
    # ---- validation: vector lane == scalar mirror on 24 lanes (full protocol, 'boot' end, rate 100, bail 1)
    c5 = J["v295"]
    sel = list(range(0, NL, NL // 24))[:24]
    R = run(c5, 100.0, "boot", want_trace=True)
    bad = 0
    for j in sel:
        i, ds, rs = lanes[j]
        L = A.Lane(c5)
        x = rs * 800
        sp = L.sp_of(i, ds)
        for _ in range(3000 + 300 + 1):
            L.tick(x, sp, i)
        tr = []
        for k in range(1 + 1500):
            tr.append(L.tick(x, sp, i, valid=(k >= 1)))
        if not np.array_equal(np.array(tr), R["trace"][:, j]):
            bad += 1
    print("vector lane vs scalar mirror, 24 lanes x 4801 ticks (restart protocol): lanes differing =", bad)
    assert bad == 0

    out = {}
    for rate in (10.0, 30.0, 100.0, 300.0, 1500.0):
        for bl in ((1, 2, 5, 20, 100) if rate in (100.0, 1500.0) else (1,)):
            row = {}
            for nm in ("v294", "v295"):
                r_lo = run(J[nm], rate, "lo", bail_len=bl); r_hi = run(J[nm], rate, "hi", bail_len=bl)
                r_bt = run(J[nm], rate, "boot", bail_len=bl)
                pk = np.maximum(np.maximum(r_lo["pk_all"], r_hi["pk_all"]), r_bt["pk_all"])
                pka = np.maximum(np.maximum(r_lo["pk_after"], r_hi["pk_after"]), r_bt["pk_after"])
                row[nm] = dict(pk=pk, pka=pka, boot=r_bt["pk_all"], lo=r_lo["pk_all"], hi=r_hi["pk_all"],
                               tpre_lo=r_lo["T_pre"], tpre_hi=r_hi["T_pre"], maxp=r_bt["maxp"])
            p4, p5 = row["v294"]["pk"], row["v295"]["pk"]
            j = int(np.argmax(p5))
            zc = [k for k, l in enumerate(lanes) if l[0] == 0]
            ratio = np.where(p4 > 0, p5 / np.maximum(p4, 1), np.nan)
            jr = int(np.nanargmax(ratio))
            print("rate %6.1f deg/s bail %3d: V295 max %4d (idx %d ds %+d rs %+d; lo/hi/boot %d/%d/%d) | V294 max %4d | "
                  "zero-cmd V294 %d -> V295 %d | lanes > 288: %d | worst per-lane ratio x%.3f (idx %d) | worst/worst x%.3f | "
                  "excl. bail ticks V295 max %d"
                  % (rate, bl, p5[j], lanes[j][0], lanes[j][1], lanes[j][2], row["v295"]["lo"][j], row["v295"]["hi"][j],
                     row["v295"]["boot"][j], p4.max(), max(p4[zc]), max(p5[zc]), int(np.sum(p5 > 288)),
                     ratio[jr], lanes[jr][0], p5.max() / max(p4.max(), 1), row["v295"]["pka"].max()))
            if bl == 1 and rate == 100.0:
                # distribution of the top lanes, and the lo/hi/boot spread
                top = np.argsort(-p5)[:8]
                for t in top:
                    print("     top lane idx %3d ds %+d rs %+d: V295 %d (lo %d hi %d boot %d) V294 %d  T_pre lo/hi %d/%d"
                          % (lanes[t][0], lanes[t][1], lanes[t][2], p5[t], row["v295"]["lo"][t], row["v295"]["hi"][t],
                             row["v295"]["boot"][t], p4[t], row["v295"]["tpre_lo"][t], row["v295"]["tpre_hi"][t]))
                print("     lanes where the lo/hi end changes the V295 pulse: %d ; max spread %d"
                      % (int(np.sum(row["v295"]["lo"] != row["v295"]["hi"])), int(np.max(np.abs(row["v295"]["lo"] - row["v295"]["hi"])))))
                print("     products (boot run): V295", row["v295"]["maxp"])
            out["%g_%d" % (rate, bl)] = dict(v295_max=int(p5.max()), v294_max=int(p4.max()), n_over_288=int(np.sum(p5 > 288)),
                                              worst_ratio=float(ratio[jr]), zero_cmd=[int(max(p4[zc])), int(max(p5[zc]))])
    json.dump(out, open(os.path.join(HERE, "a4_restart.json"), "w"), indent=1)


if __name__ == '__main__':
    main()
