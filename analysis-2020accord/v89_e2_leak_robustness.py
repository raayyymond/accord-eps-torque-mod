#!/usr/bin/env python3
"""v89_e2_leak_robustness.py -- does the v89_e1 wrong-direction result survive its own controls?

v89_e1 found the 6-9 Hz engaged band contrast for alpha=286 vs alpha=573 at -0.678
[-1.031, -0.287], where the observer-leak model predicts +0.654.  Before that is reported as a
refutation it has to survive:

  R1  the best-matched pair alone: 6f (286, parking lot) vs 70 (573, parking lot).
      6e's low-speed slice is only 2.7 engaged minutes out of a 28 m/s route.
  R2  a stricter wheel-order veto (orders 1-12, needed because 32-38 Hz is order 13+ at 5 m/s
      and so is NEVER vetoed by the orders-1-6 rule the kit uses)
  R3  no speed cap, speed as a covariate (uses 6e's whole route -- deliberately confounded,
      reported only as a sensitivity)
  R4  a LEAVE-ONE-BLOCK-OUT jackknife on the 6-9 contrast: is it one episode?
  R5  the full BAND PROFILE in 3 Hz slices -- the model's signature is a MONOTONE DECREASING
      log-ratio with frequency.  Shape is a stronger test than any single band.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v89_e1_leak_retrodiction import (ALPHA, BANDS, CTRL, PRED, DAMPER_FC, VMAX_MATCH,
                                      harvest, blocks_of, fit, ci, spec, brms, order_hits,
                                      CORPUS, NW, HOP)

RNG = np.random.default_rng(890811)
OUT = Path(__file__).resolve().parent.parent / "_cache_r73" / "v89_e2_robust.json"


def contrast(rows, bands=BANDS, ctrl=CTRL, nb=3000, flag="a286", extra=None):
    """Bootstrap the A286 coefficient per band and the (band - ctrl) contrast, over blocks."""
    b = blocks_of(rows)
    n = len(rows)
    lv = np.log([r["v"] for r in rows])
    lr = np.log([r["rate"] for r in rows])
    lh = np.log([r["hands"] for r in rows])
    cols = [np.ones(n), np.array([r[flag] for r in rows]),
            lv - lv.mean(), lr - lr.mean(), lh - lh.mean()]
    if extra:
        cols.append(np.array([r[extra] for r in rows]))
    X = np.column_stack(cols)
    ys = {k: np.log([r["e_" + k] for r in rows]) for k in bands}
    obs = {k: fit(X, ys[k])[1] for k in bands}
    uq = np.unique(b)
    idx = {g: np.where(b == g)[0] for g in uq}
    D = {k: [] for k in bands}
    for _ in range(nb):
        pick = np.concatenate([idx[g] for g in RNG.choice(uq, len(uq), replace=True)])
        try:
            for k in bands:
                D[k].append(fit(X[pick], ys[k][pick])[1])
        except np.linalg.LinAlgError:
            pass
    D = {k: np.array(v) for k, v in D.items()}
    out = {}
    for k in bands:
        c = np.array(D[k]) - np.array(D[ctrl])
        out[k] = {"b": float(obs[k]), "ci_b": list(ci(D[k])),
                  "contrast": float(obs[k] - obs[ctrl]), "ci_c": list(ci(c))}
    out["_n"] = n
    out["_blocks"] = int(len(uq))
    return out


def show(title, res, pred=PRED, ctrl=CTRL):
    print("  " + title + "   (n={} windows / {} blocks)".format(res["_n"], res["_blocks"]))
    for k in BANDS:
        r = res[k]
        pc = pred[k] - pred[ctrl]
        star = ""
        if k != ctrl:
            star = " WRONG SIGN" if (r["ci_c"][1] < 0 < pc) else (
                " excl.0" if (r["ci_c"][0] > 0 or r["ci_c"][1] < 0) else " null")
        print("    {:6s} A286 {:+7.3f} [{:+6.3f},{:+6.3f}]   CONTRAST {:+7.3f} "
              "[{:+6.3f},{:+6.3f}]  pred {:+.3f}{}".format(
                  k, r["b"], r["ci_b"][0], r["ci_b"][1], r["contrast"],
                  r["ci_c"][0], r["ci_c"][1], pc, star))


def profile_rows(vmax, nmax_order, slices):
    """Harvest with an arbitrary band set (3 Hz slices) for the shape test."""
    from scipy.signal import butter, sosfiltfilt
    rows = []
    for rec in np.load(CORPUS, allow_pickle=True):
        rt = rec["route"]
        if rt not in ALPHA:
            continue
        fs = rec["fs"]
        tq, rate, v = rec["tq"], rec["rate"], rec["v"]
        eng, sst, seg = rec["eng"], rec["sst"], rec["seg"]
        sos = butter(4, 3.0 / (fs / 2), btype="low", output="sos")
        g = np.isfinite(tq)
        lf = np.zeros_like(tq)
        if g.sum() > 30:
            lf[g] = sosfiltfilt(sos, tq[g])
        for s in range(0, len(tq) - NW + 1, HOP):
            sl = slice(s, s + NW)
            e = eng[sl].mean()
            if not (e > 0.98 or e < 0.02):
                continue
            if (sst[sl] != 0).any() or not np.isfinite(tq[sl]).all():
                continue
            vm, rm = float(np.median(v[sl])), float(np.median(np.abs(rate[sl])))
            hm = float(np.median(np.abs(lf[sl])))
            if not (0.3 < vm < vmax) or rm < 1.0 or hm < 1.0:
                continue
            if any(order_hits(vm, lo, hi, nmax_order) for lo, hi in slices.values()):
                continue
            f, p = spec(tq[sl], fs)
            b = {k: brms(f, p, lo, hi) for k, (lo, hi) in slices.items()}
            if min(b.values()) <= 0:
                continue
            rows.append({"route": rt, "a286": 1.0 if ALPHA[rt] == 286 else 0.0,
                         "fc": float(DAMPER_FC[rt]), "seg": int(np.median(seg[sl])), "i0": s,
                         "eng": 1.0 if e > 0.98 else 0.0, "v": vm, "rate": rm, "hands": hm,
                         **{"e_" + k: b[k] for k in slices}})
    return rows


def main():
    rep = {}
    rows6 = harvest(VMAX_MATCH, 6)
    eng6 = [r for r in rows6 if r["eng"] == 1.0]

    print("=" * 104)
    print("R1 -- BEST-MATCHED PAIR ONLY: 6f (alpha 286) vs 70 (alpha 573). Both parking-lot.")
    print("      Confound: 70 also arms the FactorC creep damper.  Engaged.")
    print("=" * 104)
    sub = [r for r in eng6 if r["route"] in ("r6f", "r70")]
    rep["R1_6f_vs_70"] = contrast(sub)
    show("6f vs 70", rep["R1_6f_vs_70"])

    print("\n      and 6f vs 6e alone (the TRUE single-variable pair, exposure-mismatched):")
    sub = [r for r in eng6 if r["route"] in ("r6f", "r6e")]
    rep["R1_6f_vs_6e"] = contrast(sub)
    show("6f vs 6e", rep["R1_6f_vs_6e"])

    print("\n" + "=" * 104)
    print("R2 -- STRICTER WHEEL-ORDER VETO, orders 1-12.")
    print("      NOTE: at v<5.2 m/s the fundamental is <2.51 Hz, so order 13+ is needed to reach")
    print("      32-38 Hz.  The kit's orders-1-6 rule NEVER vetoes the control band here.")
    print("=" * 104)
    rows12 = harvest(VMAX_MATCH, 12)
    eng12 = [r for r in rows12 if r["eng"] == 1.0]
    rep["R2_order12"] = contrast(eng12)
    show("orders 1-12", rep["R2_order12"])

    print("\n" + "=" * 104)
    print("R3 -- NO SPEED CAP (6e's whole 28 m/s route included, speed as covariate).")
    print("      DELIBERATELY CONFOUNDED -- sensitivity only, not evidence.")
    print("=" * 104)
    rows_all = harvest(99.0, 6)
    eng_all = [r for r in rows_all if r["eng"] == 1.0]
    rep["R3_nocap"] = contrast(eng_all, extra="fc")
    show("no speed cap", rep["R3_nocap"])

    print("\n" + "=" * 104)
    print("R4 -- LEAVE-ONE-BLOCK-OUT JACKKNIFE on the 6-9 minus 32-38 contrast (engaged, v<5.2).")
    print("=" * 104)
    b = blocks_of(eng6)
    uq = np.unique(b)
    vals = []
    for g in uq:
        keep = [eng6[i] for i in range(len(eng6)) if b[i] != g]
        if len(set(r["route"] for r in keep)) < 2 or len(keep) < 30:
            continue
        n = len(keep)
        lv = np.log([r["v"] for r in keep])
        lr = np.log([r["rate"] for r in keep])
        lh = np.log([r["hands"] for r in keep])
        X = np.column_stack([np.ones(n), np.array([r["a286"] for r in keep]),
                             lv - lv.mean(), lr - lr.mean(), lh - lh.mean(),
                             np.array([r["fc"] for r in keep])])
        y69 = np.log([r["e_6-9"] for r in keep])
        y32 = np.log([r["e_32-38"] for r in keep])
        vals.append(fit(X, y69)[1] - fit(X, y32)[1])
    vals = np.array(vals)
    print("    {} jackknife replicates: min {:+.3f}  median {:+.3f}  max {:+.3f}   "
          "sign flips: {}".format(len(vals), vals.min(), np.median(vals), vals.max(),
                                  int((vals > 0).sum())))
    rep["R4_jackknife"] = {"min": float(vals.min()), "med": float(np.median(vals)),
                           "max": float(vals.max()), "n_positive": int((vals > 0).sum()),
                           "n": len(vals)}

    print("\n" + "=" * 104)
    print("R5 -- BAND PROFILE, 3 Hz slices.  Model signature = MONOTONE DECREASING with f.")
    print("=" * 104)
    edges = [(3, 6), (6, 9), (9, 12), (12, 15), (15, 18), (18, 21), (21, 24),
             (24, 27), (27, 30), (30, 33), (33, 36), (36, 39), (39, 42), (42, 45)]
    slices = {"{}-{}".format(a, c): (float(a), float(c)) for a, c in edges}
    prow = [r for r in profile_rows(VMAX_MATCH, 6, slices) if r["eng"] == 1.0]
    res = contrast(prow, bands=slices, ctrl="33-36")

    fs_ = 1000.0

    def H(f, al, d):
        w = 2 * np.pi * f / fs_
        z = np.exp(-1j * w)
        return (z ** d) * al / (1 - (1 - al) * z)

    def leak(f, al):
        return np.abs(H(f, al, 1) - H(f, 102 / 1024., 0))

    print("  n={} windows / {} blocks".format(res["_n"], res["_blocks"]))
    print("  {:8s} {:>9s} {:>18s}   {:>9s}".format("band", "A286", "95% CI", "model"))
    prof = {}
    for k, (lo, hi) in slices.items():
        g = np.arange(lo, hi, 0.05)
        m = np.log(np.sqrt(np.mean(leak(g, 286 / 4096.) ** 2))
                   / np.sqrt(np.mean(leak(g, 573 / 4096.) ** 2)))
        r = res[k]
        bar = "#" * int(round(abs(r["b"]) * 12))
        print("  {:8s} {:+9.3f} [{:+6.3f},{:+6.3f}]   {:+9.3f}  {}{}".format(
            k, r["b"], r["ci_b"][0], r["ci_b"][1], m,
            "-" if r["b"] < 0 else "+", bar))
        prof[k] = {"b": r["b"], "ci": r["ci_b"], "model_log": float(m)}
    ks = list(slices)
    obs_v = np.array([prof[k]["b"] for k in ks])
    mod_v = np.array([prof[k]["model_log"] for k in ks])
    cc = float(np.corrcoef(obs_v, mod_v)[0, 1])
    print("\n  corr(observed A286 profile, model leak profile) = {:+.3f}   "
          "(model predicts +1; a refutation predicts <=0)".format(cc))
    rep["R5_profile"] = {"prof": prof, "corr_with_model": cc}

    OUT.write_text(json.dumps(rep, indent=1, default=float))
    print("\nwrote {}".format(OUT))


if __name__ == "__main__":
    main()
