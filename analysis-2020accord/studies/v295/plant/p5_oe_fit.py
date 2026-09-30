# -*- coding: utf-8 -*-
"""p5_oe_fit.py -- TASK 1, the estimate of record: OUTPUT-ERROR fit of the stick-slip plant per speed band, through the
byte-exact V294 lane, on the FIT segments; scored on the HELD-OUT segments.

    python p5_oe_fit.py              -> p5_oe_out.txt, _scratch/p5_oe.json          (relaxed mask, the estimate of record)
    python p5_oe_fit.py --strict     -> p5_oe_strict_out.txt                          (|bar| < 400 robustness row)
    python p5_oe_fit.py --synthetic  -> p5_oe_synth_out.txt   (gate G3a: the same fit on SIMULATED data from a KNOWN plant
                                        + coloured road disturbance, same command/segments -- must recover the truth)

Model (v294_plant): J om' + b om + k sat tanh(th/sat) + Ffric = -T(t - 2 ms) + c0 ;  Karnopp friction Fc (sliding) /
Fs (breakaway) ;  x = 8 om through a 3 ms rate former ;  sat(v) = the prior hold map's (BELIEF, fixed).
Per band, free: J, b, k, Fc, Fs/Fc in [1, 1.8].  The replay is CLOSED on the inner loop (command -> lane -> plant -> x ->
lane), so the fitted plant is the one that, with the flown V294 trim, reproduces the flown motion from the command alone.
Cost: mean over scored frames of (om_sim - om)^2 / var(om) + (th_sim - th - mean)^2 / var(th), pooled over the band's
fit segments.  Nelder-Mead from two starts (the p4 OLS scale; the prior).  CI: leave-one-group-out JACKKNIFE over the fit
segments (K = min(4, n) groups), 95 % = +-1.96 SE, each refit from the main solution.
Held-out rows: the FIT; the PRIOR light-b world (BELIEF); the fit with the trim OFF in the replay (fb clamp 0 -- the plant
alone under the same command; NOT a V293 replay).
LIMIT (stated, not hidden): the command is replayed as flown, so the fork's OUTER loop is not simulated; if the command's
reaction to road-driven motion is large, the fit can absorb part of it.  G3a cannot test that (its command is the same).
"""
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
from scipy import optimize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

TAU = 2
START_K = [5.0, 11.0, 28.0, 39.0, 53.0]         # p4 OLS k by band (scale only)
TRUTH = dict(J=0.20, b=2.0, Fc=30.0, Fs=39.0)    # G3a synthetic truth (k = START_K of the band)


def unpack(q):
    J, b, k, Fc = (math.exp(v) for v in q[:4])
    Fs = Fc * (1.0 + 0.8 / (1.0 + math.exp(-q[4])))
    return J, b, k, Fc, Fs


def pack(J, b, k, Fc, ratio):
    r = min(max((ratio - 1.0) / 0.8, 1e-3), 1 - 1e-3)
    return [math.log(J), math.log(b), math.log(k), math.log(Fc), math.log(r / (1 - r))]


def _synthesise(Bx, member, seed):
    """replace the batch's measured th/om/u by a simulation of `member` + a coloured road disturbance (1 Hz one-pole,
    rms 15 T counts) under the SAME command; u is rebuilt from the simulated T (the fit's c0 uses u)."""
    import v294_plant as VP
    rng = np.random.default_rng(seed)
    n = 10 * Bx.L
    wn = rng.normal(0.0, 1.0, (Bx.B, n))
    a = math.exp(-2 * math.pi * 1.0 / 1000.0)
    dd = np.zeros_like(wn)
    for i in range(1, n):
        dd[:, i] = a * dd[:, i - 1] + wn[:, i]
    dd *= 15.0 / np.std(dd)
    lane = VP.Lane294(Bx.cells, Bx.B)
    lane.init_state(np.round(-8.0 * Bx.om[:, 0]).astype(np.int64), Bx.T0)
    out = VP.simulate(member, n, Bx.v, Bx.th[:, 0], Bx.om[:, 0], lane=lane, sp=Bx.sp, m=Bx.m, c0=np.zeros(Bx.B), d=dd)
    Bx.th = out["th"][:, ::10][:, :Bx.L].copy()
    Bx.om = out["om"][:, ::10][:, :Bx.L].copy()
    T100 = out["T"].reshape(Bx.B, Bx.L, 10).mean(axis=2)
    Bx.u = -T100
    Bx.tap = [(tk, np.interp(tk, np.arange(n), out["T"][i])) for i, (tk, _) in enumerate(Bx.tap)]


def fit_band(bi, mode="relaxed"):
    import plib as P
    import oe_lib as O
    import v294_plant as VP
    t0 = time.time()
    d = P.load()
    c = VP.v294_cells()
    segs = O.segments(d, strict=(mode == "strict"))
    fit = [s for s in segs if s["band"] == bi and s["role"] == "fit"]
    held = [s for s in segs if s["band"] == bi and s["role"] == "held"]
    if not fit:
        return dict(band=bi, error="no fit segments")
    Bf = O.Batch(d, fit, c)
    truth = None
    if mode == "synthetic":
        truth = (TRUTH["J"], TRUTH["b"], START_K[bi], TRUTH["Fc"], TRUTH["Fs"])
        _synthesise(Bf, O.band_member(*truth, TAU), seed=11 + bi)
    sth = np.sqrt(np.mean(np.concatenate([(Bf.th[i][Bf.mask[i]] - Bf.th[i][Bf.mask[i]].mean()) ** 2 for i in range(Bf.B)])))
    som = np.sqrt(np.mean(np.concatenate([Bf.om[i][Bf.mask[i]] ** 2 for i in range(Bf.B)])))

    def cost_on(Bx, q):
        J, b, k, Fc, Fs = unpack(q)
        out, _ = Bx.replay(O.band_member(J, b, k, Fc, Fs, TAU))
        return Bx.cost(out, sth, som)

    best = None
    for qs in (pack(0.15, 3.0, START_K[bi], 30.0, 1.3), pack(0.21, 1.6, START_K[bi] * 0.7, 31.5, 1.6)):
        r = optimize.minimize(lambda q: cost_on(Bf, q), qs, method="Nelder-Mead",
                              options=dict(maxfev=260, xatol=0.02, fatol=1e-4))
        if best is None or r.fun < best.fun:
            best = r
    qb = best.x
    K = min(4, len(fit))
    jk = []
    if mode != "synthetic":
        for g in range(K):
            keep_idx = [i for i in range(len(fit)) if i % K != g]
            if not keep_idx:
                continue
            Bk = O.Batch(d, [fit[i] for i in keep_idx], c)
            r = optimize.minimize(lambda q: cost_on(Bk, q), qb, method="Nelder-Mead",
                                  options=dict(maxfev=120, xatol=0.02, fatol=1e-4))
            jk.append(unpack(r.x))
    jk = np.array(jk)
    val = np.array(unpack(qb))
    se = (np.sqrt((len(jk) - 1) / len(jk) * np.sum((jk - jk.mean(axis=0)) ** 2, axis=0)) if len(jk) >= 2
          else np.full(5, np.nan))
    J, b, k, Fc, Fs = val
    mem = O.band_member(J, b, k, Fc, Fs, TAU)
    res = dict(band=bi, n_fit=len(fit), n_held=len(held), fit_s=sum(s["b"] - s["a"] for s in fit) / 100.0,
               held_s=sum(s["b"] - s["a"] for s in held) / 100.0, cost=float(best.fun), nfev=int(best.nfev),
               names=["J", "b", "k", "Fc", "Fs"], val=val.tolist(), se=se.tolist(), jk=jk.tolist(),
               vbar=float(np.mean([s["vbar"] for s in fit])), truth=truth)
    out, _ = Bf.replay(mem)
    res["fit_scores"] = Bf.scores(out)
    if mode != "synthetic":
        fam = VP.family(path=os.path.join(HERE, "_scratch", "__none__.json"))
        lb = fam["light_b"]
        for nm_h, segs_h in (("held", held), ("fit", fit)):
            if not segs_h:
                continue
            Bh = O.Batch(d, segs_h, c)
            res[nm_h + "_nominal"] = Bh.scores(Bh.replay(mem)[0])
            res[nm_h + "_light_b"] = Bh.scores(Bh.replay(lb)[0])
            res[nm_h + "_trim_off"] = Bh.scores(Bh.replay(mem, lane_kw=dict(fb_clamp=0))[0])
    res["seconds"] = time.time() - t0
    return res


def main():
    mode = "strict" if "--strict" in sys.argv else ("synthetic" if "--synthetic" in sys.argv else "relaxed")
    with Pool(5) as pool:
        results = pool.starmap(fit_band, [(bi, mode) for bi in range(5)])
    import plib as P
    lines = []

    def pr(s=""):
        print(s, flush=True)
        lines.append(s)

    pr("OUTPUT-ERROR FIT, closed inner-loop replay through the byte-exact V294 lane (tau %d ms, rate window 3 ms, sat = prior)"
       " -- mode: %s" % (TAU, mode))
    js = {"tau_ms": TAU, "mask": mode, "nominal": {}}
    for r in results:
        bn = P.BANDS[r["band"]][0]
        if "error" in r:
            pr("band %s: %s" % (bn, r["error"]))
            continue
        pr("")
        pr("BAND %s m/s: %d fit segs (%.0f s, v %.1f), %d held (%.0f s); NM cost %.4f (%d evals); %.0f s wall" % (
            bn, r["n_fit"], r["fit_s"], r["vbar"], r["n_held"], r["held_s"], r["cost"], r["nfev"], r["seconds"]))
        v, se = np.array(r["val"]), np.array(r["se"])
        J, b, k, Fc, Fs = v
        fn = math.sqrt(k / J) / (2 * math.pi)
        z = b / (2 * math.sqrt(k * J))
        pr("  J %.4f +-%.4f T/(deg/s^2) | b %.3f +-%.3f T/(deg/s) | k %.2f +-%.2f T/deg | Fc %.1f +-%.1f T | Fs %.1f +-%.1f T"
           % (J, 1.96 * se[0], b, 1.96 * se[1], k, 1.96 * se[2], Fc, 1.96 * se[3], Fs, 1.96 * se[4]))
        if r.get("truth"):
            t = r["truth"]
            pr("  G3a TRUTH   J %.4f b %.3f k %.2f Fc %.1f Fs %.1f  -> recovered/true J %.2f b %.2f k %.2f Fc %.2f" % (
                t[0], t[1], t[2], t[3], t[4], J / t[0], b / t[1], k / t[2], Fc / t[3]))
        pr("  -> open-plant mode f_n %.2f Hz, zeta %.3f (linear, sliding); in x units J_x %.5f, b_x %.4f T per count(/s)" % (
            fn, z, J / 8, b / 8))
        for key in ("fit_scores", "held_nominal", "held_light_b", "held_trim_off", "fit_light_b"):
            if key in r:
                s = r[key]
                pr("  %-14s th R2 %+.3f fit %5.1f%% rms %5.2f deg | om R2 %+.3f fit %5.1f%% rms %5.2f deg/s | tap R2 %+.4f rms %5.1f"
                   % (key, s["th_R2"], s["th_fit"], s["th_rms"], s["om_R2"], s["om_fit"], s["om_rms"], s["T_R2"], s["T_rms"]))
        lo = np.maximum(v - 1.96 * np.nan_to_num(se), v * 0.05)
        hi = v + 1.96 * np.nan_to_num(se)
        js["nominal"][bn] = {nm: dict(val=float(v[i]), lo=float(lo[i]), hi=float(hi[i]), se=float(se[i]))
                             for i, nm in enumerate(r["names"])}
        js["nominal"][bn]["scores"] = {k2: r[k2] for k2 in r if k2.startswith(("held_", "fit_"))}
        js["nominal"][bn]["n_fit"], js["nominal"][bn]["n_held"] = r["n_fit"], r["n_held"]
        js["nominal"][bn]["jk"] = r["jk"]
        js["nominal"][bn]["vbar"] = r["vbar"]
    tag = {"relaxed": "", "strict": "_strict", "synthetic": "_synth"}[mode]
    json.dump(js, open(os.path.join(HERE, "_scratch", "p5_oe%s.json" % tag), "w"), indent=1)
    open(os.path.join(HERE, "p5_oe%s_out.txt" % tag), "w", encoding="utf-8").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
