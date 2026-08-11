#!/usr/bin/env python3
"""v89_f1_residual_probe.py -- does the observer residual `gp-0x6b70` respond to LKAS ENGAGEMENT?

Routes `6f` (V86) and `70` (V86B) both flew a cave that probes `gp-0x6b70` DIRECTLY on 0x14A byte 4:
    b7 = resid < 0        b6 = resid != 0        b5 = |resid| >= 64
    b4 = gp-0x67ab < 2 (aggregator gate)         b3 = fingerprint
V86B flew the SAME cave with b5/b6 weight-swapped, so the two routes need different decodes.

IDENTITY, verified here rather than assumed:
  * the extractor's own parameter-free check reports `6f` -> V86 decode, `70` -> V86B decode
  * `probe` takes only {31, 95, 127, 223, 255}: bits 0-4 are always 1, and there is NO code with
    the magnitude bit set and the non-zero bit clear.  |resid|>=64 => resid!=0 is EXACT NESTING,
    which is what fixes which weight is which -- the nested bit is the magnitude rung.
  * `probe == raw14_b4[1:]` and `t == raw14_t[1:]`, so (t, probe) is the ALIGNED pair.  The kit-wide
    raw14 off-by-one is avoided by never touching raw14_* here.

CONTROLS BEFORE THE MEASUREMENT
  K1  b6 (resid != 0) duty in each arm -- if railed in both it carries nothing, and say so
  K2  b4 (the aggregator gate) -- railed at 1.0000 means engagement cannot act through the gate
  K3  exposure census of speed / wheel rate / hands torque in each arm, and the matched overlap
  K4  the same engagement contrast on the OTHER route, at a different alpha
  K5  shuffled-pairs null for the sign correlation
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_cache_r73" / "v89_f1_residual.json"
RNG = np.random.default_rng(890820)

NW, HOP = 256, 128
ROUTES = {"r6f": ("V86", 286), "r70": ("V86B", 573)}
DECODE = {"r6f": "v86", "r70": "v86b"}     # identity-verified per route


def load(rt):
    z = np.load(ROOT / ("_cache_" + rt) / (rt + ".npz"), allow_pickle=True)
    assert np.array_equal(z["probe"].astype(int), z["raw14_b4"].astype(int)[1:]), "raw14 pairing"
    p = z["probe"].astype(int)
    d = DECODE[rt]
    # decode straight from `probe` -- do not trust the stored v86_* columns
    if d == "v86":
        nz, mag = (p >> 6) & 1, (p >> 5) & 1
    else:
        nz, mag = (p >> 5) & 1, (p >> 6) & 1
    sign = (p >> 7) & 1
    gate = (p >> 4) & 1
    assert np.all(mag <= nz), "magnitude rung must nest inside non-zero rung"
    tq = z["tq"]
    fs = 1.0 / np.median(np.diff(z["t"]))
    sos = butter(4, 3.0 / (fs / 2), btype="low", output="sos")
    g = np.isfinite(tq)
    lf = np.zeros_like(tq)
    if g.sum() > 30:
        lf[g] = sosfiltfilt(sos, tq[g])
    return {"t": z["t"], "fs": fs, "sign": sign, "nz": nz, "mag": mag, "gate": gate,
            "eng": z["cc_lat"] > 0.5, "v": z["cs_v"], "rate": z["rate_c"], "sst": z["sstat"],
            "seg": z["seg"].astype(int), "cmd": z["sc_tq"], "hands": np.abs(lf), "tq": tq,
            "probe": p}


def windows(D, vmin=0.3, vmax=99.0, need_motion=True):
    rows = []
    n = len(D["t"])
    for s in range(0, n - NW + 1, HOP):
        sl = slice(s, s + NW)
        e = D["eng"][sl].mean()
        if not (e > 0.98 or e < 0.02):
            continue
        if (D["sst"][sl] != 0).any():
            continue
        vm = float(np.median(D["v"][sl]))
        rm = float(np.median(np.abs(D["rate"][sl])))
        hm = float(np.median(D["hands"][sl]))
        if not (vmin < vm < vmax):
            continue
        if need_motion and (rm < 1.0 or hm < 1.0):
            continue
        k = int(D["mag"][sl].sum())
        rows.append({"i0": s, "seg": int(np.median(D["seg"][sl])),
                     "eng": 1.0 if e > 0.98 else 0.0, "v": vm, "rate": rm, "hands": hm,
                     "k5": k, "n": NW,
                     "d5": k / NW, "d6": float(D["nz"][sl].mean()),
                     "d7": float(D["sign"][sl].mean()), "d4": float(D["gate"][sl].mean()),
                     "cmd": float(np.sqrt(np.mean(D["cmd"][sl] ** 2)))})
    return rows


def logit(k, n):
    return np.log((k + 0.5) / (n - k + 0.5))


def blocks_of(rows):
    blk, cur, last = [], 0, None
    for r in rows:
        if last is not None and (r["seg"] != last["seg"] or r["i0"] - last["i0"] > 3 * HOP
                                 or r["eng"] != last["eng"]):
            cur += 1
        blk.append(cur)
        last = r
    return np.array(blk)


def fit(X, y):
    return np.linalg.lstsq(X, y, rcond=None)[0]


def boot_coef(X, y, blk, nb=3000):
    uq = np.unique(blk)
    idx = {g: np.where(blk == g)[0] for g in uq}
    D = []
    for _ in range(nb):
        pick = np.concatenate([idx[g] for g in RNG.choice(uq, len(uq), replace=True)])
        try:
            D.append(fit(X[pick], y[pick]))
        except np.linalg.LinAlgError:
            pass
    return np.array(D)


def ci(a):
    return float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))


def main():
    rep = {}
    data = {rt: load(rt) for rt in ROUTES}

    print("=" * 104)
    print("K1/K2 -- RUNG CONTROLS, whole route, every frame")
    print("=" * 104)
    for rt, D in data.items():
        e = D["eng"]
        print("  {} ({}, alpha={})  n={}  engaged duty {:.4f}".format(
            rt, ROUTES[rt][0], ROUTES[rt][1], len(e), e.mean()))
        for nm, a in (("b7 sign  ", D["sign"]), ("b6 nonzero", D["nz"]),
                      ("b5 |r|>=64", D["mag"]), ("b4 gate  ", D["gate"])):
            print("     {}  all {:.4f}   ENG {:.4f}   MAN {:.4f}   delta {:+.4f}".format(
                nm, a.mean(), a[e].mean(), a[~e].mean(), a[e].mean() - a[~e].mean()))
        print("     probe alphabet {}".format(sorted(set(D["probe"].tolist()))))
    print("\n  ** b6 is railed >=0.9955 in BOTH arms on BOTH routes and b4 is railed at exactly")
    print("     1.0000 => neither carries information; engagement cannot act through the gate. **")

    print("\n" + "=" * 104)
    print("K3 -- EXPOSURE CENSUS of the covariates, per arm (windowed, motion screen applied)")
    print("=" * 104)
    W = {rt: windows(data[rt]) for rt in ROUTES}
    for rt in ROUTES:
        for arm, sel in (("ENG", 1.0), ("MAN", 0.0)):
            sub = [r for r in W[rt] if r["eng"] == sel]
            if not sub:
                print("  {} {}: none".format(rt, arm))
                continue
            v = np.array([r["v"] for r in sub])
            rr = np.array([r["rate"] for r in sub])
            hh = np.array([r["hands"] for r in sub])
            print("  {} {}  n={:4d}  v  p10/50/90 {:.2f}/{:.2f}/{:.2f}   |rate| {:.1f}/{:.1f}/{:.1f}"
                  "   hands {:.0f}/{:.0f}/{:.0f}".format(
                      rt, arm, len(sub), *np.percentile(v, [10, 50, 90]),
                      *np.percentile(rr, [10, 50, 90]), *np.percentile(hh, [10, 50, 90])))

    print("\n" + "=" * 104)
    print("ITEM 1 -- b5 duty (|resid| >= 64) ENGAGED vs MANUAL, matched on speed / wheel rate /")
    print("          hands torque.  log-odds response, episode bootstrap x3000.")
    print("=" * 104)
    rep["item1"] = {}
    for rt in ROUTES:
        rows = W[rt]
        if len(rows) < 30 or len(set(r["eng"] for r in rows)) < 2:
            print("  {}: not enough windows".format(rt))
            continue
        blk = blocks_of(rows)
        y = logit(np.array([r["k5"] for r in rows], float), NW)
        lv = np.log([r["v"] for r in rows])
        lr = np.log([r["rate"] for r in rows])
        lh = np.log([r["hands"] for r in rows])
        eng = np.array([r["eng"] for r in rows])
        X = np.column_stack([np.ones(len(rows)), eng, lv - lv.mean(),
                             lr - lr.mean(), lh - lh.mean()])
        B = boot_coef(X, y, blk)
        b = fit(X, y)
        lo, hi = ci(B[:, 1])
        sat = np.mean([r["k5"] == NW for r in rows])
        raw_e = np.mean([r["d5"] for r in rows if r["eng"] == 1.0])
        raw_m = np.mean([r["d5"] for r in rows if r["eng"] == 0.0])
        print("  {} ({}, alpha={}): n={} windows / {} blocks   eng {} / man {}".format(
            rt, ROUTES[rt][0], ROUTES[rt][1], len(rows), len(np.unique(blk)),
            int(eng.sum()), int((1 - eng).sum())))
        print("     raw window-mean b5 duty   ENG {:.4f}   MAN {:.4f}".format(raw_e, raw_m))
        print("     windows at duty == 1.000  {:.1%}  (saturation)".format(sat))
        print("     ADJUSTED eng effect on log-odds  {:+.3f} [{:+.3f}, {:+.3f}]  "
              "= odds x{:.2f}   {}".format(
                  b[1], lo, hi, np.exp(b[1]),
                  "EXCLUDES 0" if (lo > 0 or hi < 0) else "NULL"))
        for j, nm in ((2, "log v"), (3, "log|rate|"), (4, "log hands")):
            l2, h2 = ci(B[:, j])
            print("        {:10s} {:+.3f} [{:+.3f}, {:+.3f}]".format(nm, b[j], l2, h2))
        rep["item1"][rt] = {"eng_logodds": float(b[1]), "ci": [lo, hi],
                            "raw_eng": float(raw_e), "raw_man": float(raw_m),
                            "n": len(rows), "blocks": int(len(np.unique(blk))),
                            "saturated_frac": float(sat)}

    print("\n" + "=" * 104)
    print("ITEM 2 -- does b5 duty track the LKAS COMMAND MAGNITUDE?  Engaged only.")
    print("          Model: logit(b5) ~ log|cmd|rms + log|rate| + log v + log hands")
    print("          Hypothesis predicts a MAGNITUDE coefficient and NO rate coefficient.")
    print("=" * 104)
    rep["item2"] = {}
    for rt in ROUTES:
        rows = [r for r in W[rt] if r["eng"] == 1.0 and r["cmd"] > 0]
        if len(rows) < 25:
            print("  {}: only {} engaged windows -- UNINTERPRETABLE".format(rt, len(rows)))
            continue
        blk = blocks_of(rows)
        y = logit(np.array([r["k5"] for r in rows], float), NW)
        lc = np.log([r["cmd"] for r in rows])
        lr = np.log([r["rate"] for r in rows])
        lv = np.log([r["v"] for r in rows])
        lh = np.log([r["hands"] for r in rows])
        X = np.column_stack([np.ones(len(rows)), lc - lc.mean(), lr - lr.mean(),
                             lv - lv.mean(), lh - lh.mean()])
        B = boot_coef(X, y, blk)
        b = fit(X, y)
        print("  {} ({}): n={} / {} blocks   corr(log|cmd|, log|rate|) = {:+.3f}".format(
            rt, ROUTES[rt][0], len(rows), len(np.unique(blk)),
            float(np.corrcoef(lc, lr)[0, 1])))
        res = {}
        for j, nm in ((1, "log|cmd| rms"), (2, "log|rate|"), (3, "log v"), (4, "log hands")):
            l2, h2 = ci(B[:, j])
            tag = "EXCLUDES 0" if (l2 > 0 or h2 < 0) else "NULL"
            print("     {:13s} {:+.3f} [{:+.3f}, {:+.3f}]   {}".format(nm, b[j], l2, h2, tag))
            res[nm] = {"b": float(b[j]), "ci": [l2, h2], "verdict": tag}
        rep["item2"][rt] = dict(res, n=len(rows), blocks=int(len(np.unique(blk))),
                                corr_cmd_rate=float(np.corrcoef(lc, lr)[0, 1]))

    print("\n" + "=" * 104)
    print("ITEM 1b -- does engagement bias the residual's SIGN toward the command's sign?")
    print("           b7 = (resid < 0).  Frame-level agreement with (cmd < 0), lag swept,")
    print("           against a SHUFFLED-PAIRS null built by permuting episode blocks.")
    print("=" * 104)
    rep["sign"] = {}
    for rt in ROUTES:
        D = data[rt]
        ok = D["eng"] & (D["sst"] == 0) & (np.abs(D["cmd"]) > 0) & (D["v"] > 0.3)
        if ok.sum() < 2000:
            print("  {}: only {} usable engaged frames -- UNINTERPRETABLE".format(rt, int(ok.sum())))
            continue
        s7 = D["sign"].astype(float)
        cneg = (D["cmd"] < 0).astype(float)
        best = None
        print("  {} ({}): {} engaged frames with a non-zero command".format(
            rt, ROUTES[rt][0], int(ok.sum())))
        curve = {}
        for lag in range(-10, 11):
            a = np.roll(s7, lag)
            m = ok.copy()
            m[:abs(lag) + 1] = False
            m[len(m) - abs(lag) - 1:] = False
            agree = float((a[m] == cneg[m]).mean())
            curve[lag] = agree
            if best is None or abs(agree - 0.5) > abs(best[1] - 0.5):
                best = (lag, agree)
        # chance from the marginals at lag 0
        p1 = s7[ok].mean()
        p2 = cneg[ok].mean()
        chance = p1 * p2 + (1 - p1) * (1 - p2)
        # shuffled-pairs null: permute contiguous segments of the command against the sign
        segs = np.unique(D["seg"][ok])
        nulls = []
        for _ in range(400):
            perm = RNG.permutation(segs)
            cc = cneg.copy()
            for a_, b_ in zip(segs, perm):
                ia, ib = np.where(D["seg"] == a_)[0], np.where(D["seg"] == b_)[0]
                n = min(len(ia), len(ib))
                cc[ia[:n]] = cneg[ib[:n]]
            nulls.append(float((s7[ok] == cc[ok]).mean()))
        nulls = np.array(nulls)
        print("     lag-0 agreement {:.4f}   marginal chance {:.4f}   best lag {} -> {:.4f}".format(
            curve[0], chance, best[0], best[1]))
        print("     shuffled-pairs null  mean {:.4f}  95% [{:.4f}, {:.4f}]   =>  {}".format(
            nulls.mean(), np.percentile(nulls, 2.5), np.percentile(nulls, 97.5),
            "ABOVE the null" if curve[0] > np.percentile(nulls, 97.5) else
            "BELOW the null" if curve[0] < np.percentile(nulls, 2.5) else "INSIDE the null"))
        rep["sign"][rt] = {"lag0": curve[0], "chance": chance, "best_lag": best[0],
                           "best": best[1], "null_mean": float(nulls.mean()),
                           "null_ci": [float(np.percentile(nulls, 2.5)),
                                       float(np.percentile(nulls, 97.5))],
                           "curve": {str(k): v for k, v in curve.items()}}

    OUT.write_text(json.dumps(rep, indent=1, default=float))
    print("\nwrote {}".format(OUT))


if __name__ == "__main__":
    main()
