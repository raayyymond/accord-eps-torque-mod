# -*- coding: utf-8 -*-
"""p5b_ms_fit.py -- TASK 1, THE ESTIMATE OF RECORD: MULTIPLE-SHOOTING output-error fit of the stick-slip plant, per band.

    python p5b_ms_fit.py              -> p5b_ms_out.txt, _scratch/p5b_ms.json   (read by v294_plant.family())
    python p5b_ms_fit.py --synthetic  -> p5b_ms_synth_out.txt  (gate G3a for THIS estimator: known plant + road noise)

WHY NOT p5 (the 20 s free-run output error).  p5 was run first and is kept as a record: over 20 s the replay is dominated by
stick-slip TIMING and by slow road/aligning drift the model does not carry; its fits traded friction against damping
(Fc 0.1-145, b 4-18, J 0.04-0.56 across bands, jackknife CIs spanning the range) and held-out om R2 was 0.0-0.53.  The
design needs the dynamics a 1 kHz inner loop acts on (0.1-1 s), so the estimator of record uses 1 s windows:
  * each window starts from the MEASURED th, om and the march's EXACT lane state (fb lag s, output lag o) at that tick
    (plib.march records them), so no start transient and no start-state guess;
  * the route command drives the byte-exact V294 lane, which is CLOSED through the simulated x (inner loop simulated);
  * one nuisance per window: c0 = the model's mean equation residual over the window +-0.5 s (road crown, bank, the
    slow aligning torque, sensor offset) -- the < ~0.5 Hz part of the plant is NOT identified here, by construction;
  * cost = mean (om_sim - om)^2 / var + mean (dth_sim - dth)^2 / var over every frame of every window (dth from the start).
Free per band: J, b, k, Fc, Fs/Fc in [1, 1.8]; tau 2 ms (the 6-20 Hz cross-correlation peak), rate former 3 ms, sat = prior.
Windows come from the SAME fit/held parent segments as p5 (parity split by 20 s parent), so held-out windows are disjoint.
CI: leave-one-group-out jackknife over PARENT segments (K = min(8, n_parents) groups), 95 % = +-1.96 SE.
Then a tau scan (0/2/5/10/15 ms) of the nominal on the fit windows, and held-out scores of: nominal, the prior light-b
world, the nominal with the trim OFF (fb clamp 0), and a 'hold' predictor (om held at its start value) as the floor.
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
START_K = [5.0, 11.0, 28.0, 39.0, 53.0]
TRUTH = dict(J=0.20, b=2.0, Fc=30.0, Fs=39.0)


BAR = "--bar" in sys.argv       # motor-side model with the MEASURED bar torque as an input (-g*bar), g fitted


def unpack(q):
    J, b, k, Fc = (math.exp(v) for v in q[:4])
    Fs = Fc * (1.0 + 0.8 / (1.0 + math.exp(-q[4])))
    return J, b, k, Fc, Fs


def gain_of(q):
    return math.exp(q[5]) if len(q) > 5 else 0.0


def pack(J, b, k, Fc, ratio):
    r = min(max((ratio - 1.0) / 0.8, 1e-3), 1 - 1e-3)
    return [math.log(J), math.log(b), math.log(k), math.log(Fc), math.log(r / (1 - r))]


def _synth_windows(Wb, member, seed):
    """overwrite a WindowBatch's measured th/om (and its c0 spans) by the known plant + a coloured road disturbance."""
    import v294_plant as VP
    rng = np.random.default_rng(seed)
    n = 10 * Wb.L
    a = math.exp(-2 * math.pi * 1.0 / 1000.0)
    wn = rng.normal(0.0, 1.0, (Wb.B, n + 3000))
    dd = np.zeros_like(wn)
    for i in range(1, wn.shape[1]):
        dd[:, i] = a * dd[:, i - 1] + wn[:, i]
    dd = dd[:, 3000:] * (15.0 / np.std(dd[:, 3000:]))
    lane = VP.Lane294(Wb.cells, Wb.B)
    lane.s, lane.o = Wb.sfb0.copy(), Wb.o0.copy()
    # a real per-window offset (crown/bank), N(0, 40) T counts: the control must be able to catch a c0 defect
    c0_true = rng.normal(0.0, 40.0, Wb.B)
    Wb.c0_true = c0_true
    out = VP.simulate(member, n, Wb.v, Wb.th[:, 0], Wb.om[:, 0], lane=lane, sp=Wb.sp, m=Wb.m, c0=c0_true, d=dd)
    th = np.c_[Wb.th[:, :1], out["th"][:, 9::10][:, :Wb.L - 1]]
    om = np.c_[Wb.om[:, :1], out["om"][:, 9::10][:, :Wb.L - 1]]
    Wb.th, Wb.om = th, om
    T100 = out["T"].reshape(Wb.B, Wb.L, 10).mean(axis=2)
    for i, cw in enumerate(Wb.cw):
        cw.update(u=-T100[i], th=th[i], om=om[i], al=np.gradient(om[i]) * 100.0, v=Wb.v[i], bar=np.zeros(Wb.L))


def fit_band(bi, mode="relaxed", bar=False):
    import plib as P
    import oe_lib as O
    import v294_plant as VP
    t0 = time.time()
    d = P.load()
    c = VP.v294_cells()
    segs = O.segments(d)
    wins = O.windows(segs, d=d)
    wf = [w for w in wins if w["band"] == bi and w["role"] == "fit"]
    wh = [w for w in wins if w["band"] == bi and w["role"] == "held"]
    if not wf:
        return dict(band=bi, error="no fit windows")
    Wf = O.WindowBatch(d, wf, c)
    truth = None
    if mode == "synthetic":
        truth = (TRUTH["J"], TRUTH["b"], START_K[bi], TRUTH["Fc"], TRUTH["Fs"])
        _synth_windows(Wf, O.band_member(*truth, TAU), seed=21 + bi)
    som = float(np.std(Wf.om[:, 1:] - Wf.om[:, 1:].mean(axis=1, keepdims=True)))
    dth = Wf.th[:, 1:] - Wf.th[:, :1]
    sth = float(np.std(dth - dth.mean(axis=1, keepdims=True)))

    def cost_on(Wx, q, tau=TAU):
        J, b, k, Fc, Fs = unpack(q)
        Wx.bar_gain = gain_of(q)
        out, _ = Wx.replay(O.band_member(J, b, k, Fc, Fs, tau))
        return Wx.cost(out, sth, som)

    best = None
    starts = [pack(0.2, 3.0, START_K[bi], 30.0, 1.3), pack(0.1, 6.0, START_K[bi], 60.0, 1.3),
              pack(0.4, 1.5, START_K[bi] * 0.6, 20.0, 1.5)]
    if bar:
        starts = [q + [math.log(0.28)] for q in (pack(0.03, 3.0, START_K[bi], 20.0, 1.3),
                                                 pack(0.1, 2.0, START_K[bi], 30.0, 1.3),
                                                 pack(0.01, 3.0, START_K[bi] * 0.6, 15.0, 1.5))]
    for qs in starts:
        r = optimize.minimize(lambda q: cost_on(Wf, q), qs, method="Nelder-Mead",
                              options=dict(maxfev=300, xatol=0.01, fatol=1e-5))
        if best is None or r.fun < best.fun:
            best = r
    qb = best.x
    val = np.array(unpack(qb))
    g_bar = gain_of(qb)
    res = dict(band=bi, g_bar=g_bar, n_fit=len(wf), n_held=len(wh), cost=float(best.fun), nfev=int(best.nfev), truth=truth,
               names=["J", "b", "k", "Fc", "Fs"], val=val.tolist(), vbar=float(np.mean([w["vbar"] for w in wf])),
               som=som, sth=sth)
    if mode != "synthetic":
        parents = sorted(set(w["parent"] for w in wf))
        K = min(8, len(parents))
        jk = []
        for g in range(K):
            drop = set(parents[g::K])
            keep = [w for w in wf if w["parent"] not in drop]
            if not keep:
                continue
            Wk = O.WindowBatch(d, keep, c)
            r = optimize.minimize(lambda q: cost_on(Wk, q), qb, method="Nelder-Mead",
                                  options=dict(maxfev=150, xatol=0.01, fatol=1e-5))
            jk.append(unpack(r.x) + (gain_of(r.x),))
        jk = np.array(jk)
        se = (np.sqrt((len(jk) - 1) / len(jk) * np.sum((jk - jk.mean(axis=0)) ** 2, axis=0)) if len(jk) >= 2
              else np.full(6, np.nan))
        res["jk"], res["se"] = jk.tolist(), se.tolist()
        # tau scan on the fit windows at the nominal
        res["tau_scan"] = [(t, cost_on(Wf, qb, tau=t)) for t in (0, 2, 5, 10, 15)]
        J, b, k, Fc, Fs = val
        mem = O.band_member(J, b, k, Fc, Fs, TAU)
        fam = VP.family(path=os.path.join(HERE, "_scratch", "__none__.json"))
        for nm_h, ww in (("fit", wf), ("held", wh)):
            if not ww:
                continue
            Wh = O.WindowBatch(d, ww, c)
            Wh.bar_gain = g_bar
            res[nm_h + "_nominal"] = Wh.scores(Wh.replay(mem)[0])
            res[nm_h + "_trim_off"] = Wh.scores(Wh.replay(mem, lane_kw=dict(fb_clamp=0))[0])
            Wh.bar_gain = 0.0
            res[nm_h + "_light_b"] = Wh.scores(Wh.replay(fam["light_b"])[0])
    else:
        res["se"] = [float("nan")] * 6
        res["jk"] = []
    res["seconds"] = time.time() - t0
    return res


def main():
    mode = "synthetic" if "--synthetic" in sys.argv else "relaxed"
    with Pool(5) as pool:
        results = pool.starmap(fit_band, [(bi, mode, BAR) for bi in range(5)])
    import plib as P
    lines = []

    def pr(s=""):
        print(s, flush=True)
        lines.append(s)

    pr(("MOTOR-SIDE MODEL, MEASURED BAR TORQUE AS AN INPUT (-g*bar). " if BAR else "") + "MULTIPLE-SHOOTING OUTPUT-ERROR FIT (1 s windows from the measured state + the march's lane state; command -> byte-exact"
       " V294 lane -> plant -> x -> lane; tau %d ms, rate former 3 ms, sat = prior) -- mode: %s" % (TAU, mode))
    js = {"tau_ms": TAU, "mode": mode, "win_s": 1.0, "nominal": {}}
    for r in results:
        bn = P.BANDS[r["band"]][0]
        if "error" in r:
            pr("band %s: %s" % (bn, r["error"]))
            continue
        pr("")
        pr("BAND %s m/s: %d fit windows (v %.1f), %d held; cost %.4f (%d evals); om sd %.2f deg/s, dth sd %.3f deg; %.0f s wall" % (
            bn, r["n_fit"], r["vbar"], r["n_held"], r["cost"], r["nfev"], r["som"], r["sth"], r["seconds"]))
        v, se = np.array(r["val"]), np.array(r["se"], float)
        J, b, k, Fc, Fs = v
        fn = math.sqrt(k / J) / (2 * math.pi)
        z = b / (2 * math.sqrt(k * J))
        pr("  J %.4f +-%.4f T/(deg/s^2) | b %.3f +-%.3f T/(deg/s) | k %.2f +-%.2f T/deg | Fc %.1f +-%.1f T | Fs %.1f +-%.1f T"
           % (J, 1.96 * se[0], b, 1.96 * se[1], k, 1.96 * se[2], Fc, 1.96 * se[3], Fs, 1.96 * se[4]))
        if BAR:
            pr("  bar input gain g %.4f +-%.4f T counts per bar count (the motor side sees -g*bar)" % (
                r["g_bar"], 1.96 * (se[5] if len(se) > 5 else float("nan"))))
        if r.get("truth"):
            t = r["truth"]
            pr("  G3a TRUTH   J %.4f b %.3f k %.2f Fc %.1f Fs %.1f  -> recovered/true J %.2f b %.2f k %.2f Fc %.2f Fs %.2f" % (
                t[0], t[1], t[2], t[3], t[4], J / t[0], b / t[1], k / t[2], Fc / t[3], Fs / t[4]))
        pr("  -> open-plant mode f_n %.2f Hz, zeta %.3f (linear, sliding); x units: J_x %.5f, b_x %.4f T per count(/s)" % (
            fn, z, J / 8, b / 8))
        if "tau_scan" in r:
            pr("  tau scan (fit-window cost): %s" % "  ".join("%d ms %.4f" % (t, cst) for t, cst in r["tau_scan"]))
        for key in ("fit_nominal", "held_nominal", "held_light_b", "held_trim_off"):
            if key in r:
                s = r[key]
                pr("  %-13s om R2 %+.3f fit %5.1f%% rms %5.2f (0-.25s %.2f .25-.5s %.2f .5-1s %.2f) skill-vs-hold %+.2f |"
                   " dth R2 %+.3f rms %.3f deg | tap R2 %+.4f rms %4.1f" % (
                       key, s["om_R2"], s["om_fit"], s["om_rms"], s["om_h025_rms"], s["om_h050_rms"], s["om_h100_rms"],
                       s["om_skill_vs_hold"], s["dth_R2"], s["dth_rms"], s["T_R2"], s["T_rms"]))
        lo = np.maximum(v - 1.96 * np.nan_to_num(se[:5]), v * 0.05)
        hi = v + 1.96 * np.nan_to_num(se[:5])
        js["nominal"][bn] = {nm: dict(val=float(v[i]), lo=float(lo[i]), hi=float(hi[i]), se=float(se[i]))
                             for i, nm in enumerate(r["names"])}
        js["nominal"][bn]["g_bar"] = dict(val=float(r["g_bar"]), se=float(se[5]) if len(se) > 5 else float("nan"))
        js["nominal"][bn].update(scores={k2: r[k2] for k2 in r if k2.startswith(("held_", "fit_"))},
                                 n_fit=r["n_fit"], n_held=r["n_held"], jk=r["jk"], vbar=r["vbar"],
                                 tau_scan=r.get("tau_scan"), truth=r.get("truth"))
    tag = ("_synth" if mode == "synthetic" else "") + ("_bar" if BAR else "")
    json.dump(js, open(os.path.join(HERE, "_scratch", "p5b_ms%s.json" % tag), "w"), indent=1)
    open(os.path.join(HERE, "p5b_ms%s_out.txt" % tag), "w", encoding="utf-8").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
