#!/usr/bin/env python3
"""studies/sessions/v89/v89_c2_powered_discriminator.py -- the rate x engagement x LEVER-B test, on the FULL corpus.

v89_a6 ran this on 12 routes / 93 blocks and returned an underpowered non-answer. The corpus is
~2.4x bigger than that glob saw (studies/sessions/v89/v89_c1_full_corpus.py): 30 routes, 284 min, 10 Lever-B routes
against 20 without. This re-runs the same model with that data.

MODEL (per band, identical windows)
    log e_band ~ route + eng + eng x log|rate| + eng x log|rate| x LEVERB + eng x LEVERB
                       + eng x log|rate| x DAMPER + eng x DAMPER
                       + log|rate| + LEVERB + DAMPER + log v + log hands

  `eng x log|rate|`          -- the operator's axis: does engagement's amplification grow with
                                how fast the wheel is being turned?
  `... x LEVERB`             -- is r24's ENGAGED arm (2622 -> 5244 while `gp-0x6806` holds) the
                                thing doing it?  r24 is a rate derivative on the column, i.e. the
                                only known lever that is BOTH engagement-gated and rate-driven.
  `... x DAMPER`             -- the base-assist damper (FactorC m26 Y[0] != 0 on V74..V86B), so a
                                6-9 Hz claim cannot ride on damper state by accident.

Every claim is reported as a BAND CONTRAST (6-9 minus 32-38 on the same windows) and every verdict
carries an explicit POWER check: a CI wider than the effect it tests is a non-answer, not a null.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[3].parent
CORPUS = ROOT / "_scratch/cache/r73" / "v89_c1_corpus.npy"
OUT = ROOT / "_scratch/cache/r73" / "v89_c2_powered.json"
RNG = np.random.default_rng(890707)

NW, HOP = 256, 128
CIRC_LO, CIRC_HI = 2.073, 2.088


def order_hits(v, lo, hi, nmax=6):
    if v <= 0.05:
        return False
    for circ in (CIRC_LO, CIRC_HI):
        for n in range(1, nmax + 1):
            if lo <= n * v / circ < hi:
                return True
    return False


def spec(x, fs):
    x = x - x.mean()
    w = np.hanning(len(x))
    X = np.fft.rfft(x * w)
    p = (np.abs(X) ** 2) / (np.sum(w ** 2) * fs)
    p[1:-1] *= 2.0
    return np.fft.rfftfreq(len(x), 1.0 / fs), p


def brms(f, p, lo, hi):
    m = (f >= lo) & (f < hi)
    return float(np.sqrt(np.sum(p[m]) * (f[1] - f[0])))


def windows():
    rows = []
    for rec in np.load(CORPUS, allow_pickle=True):
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
            vm = float(np.median(v[sl]))
            rm = float(np.median(np.abs(rate[sl])))
            hm = float(np.median(np.abs(lf[sl])))
            if not (0.3 < vm < 8.0) or rm < 1.0 or hm < 1.0:
                continue
            if order_hits(vm, 6.0, 9.0) or order_hits(vm, 32.0, 38.0):
                continue
            f, p = spec(tq[sl], fs)
            a, b = brms(f, p, 6.0, 9.0), brms(f, p, 32.0, 38.0)
            if a <= 0 or b <= 0:
                continue
            rows.append({"route": rec["route"], "lb": 1.0 if rec["lever_b"] else 0.0,
                         "dm": (1.0 if rec["damper"] else 0.0) if rec["damper"] is not None else None,
                         "seg": int(np.median(seg[sl])), "i0": s,
                         "eng": 1.0 if e > 0.98 else 0.0,
                         "v": vm, "rate": rm, "hands": hm, "e69": a, "e32": b})
    return [r for r in rows if r["dm"] is not None]


def blocks(rows):
    out, cur, last = [], 0, None
    for r in rows:
        if last is not None and (r["route"] != last["route"] or r["seg"] != last["seg"]
                                 or r["i0"] - last["i0"] > 3 * HOP or r["eng"] != last["eng"]):
            cur += 1
        out.append(cur)
        last = r
    return np.array(out)


def report(name, b69, b32, D69, D32, i, ref=None):
    """`ref` = the effect size this term must be able to resolve for a null to MEAN anything.
    For `eng x lr` that is v89_a5's 12-route claim of +0.144, which the full corpus can now test.
    A CI that excludes `ref` turns a non-significant result into a REFUTATION of `ref`."""
    c69 = [np.percentile(D69[:, i], 2.5), np.percentile(D69[:, i], 97.5)]
    c32 = [np.percentile(D32[:, i], 2.5), np.percentile(D32[:, i], 97.5)]
    d = D69[:, i] - D32[:, i]
    cd = [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]
    obs = b69[i] - b32[i]
    excl = cd[0] > 0 or cd[1] < 0
    if excl:
        tag = "EXCLUDES 0"
    elif ref is not None and not (cd[0] <= ref <= cd[1]):
        tag = f"NULL, and REFUTES {ref:+.3f}"
    elif ref is not None:
        tag = f"inconclusive (cannot resolve {ref:+.3f})"
    else:
        tag = "includes 0"
    print(f"  {name:26s} 6-9 {b69[i]:+7.3f} [{c69[0]:+6.3f},{c69[1]:+6.3f}]  "
          f"ctl {b32[i]:+7.3f} [{c32[0]:+6.3f},{c32[1]:+6.3f}]  "
          f"CONTRAST {obs:+7.3f} [{cd[0]:+6.3f},{cd[1]:+6.3f}]  {tag}")
    return {"b69": float(b69[i]), "ci69": [float(x) for x in c69],
            "b32": float(b32[i]), "ci32": [float(x) for x in c32],
            "contrast": float(obs), "ci_contrast": cd, "verdict": tag}


def main():
    rows = windows()
    routes = sorted({r["route"] for r in rows})
    print(f"{len(rows)} windows over {len(routes)} routes")
    lb = np.array([r["lb"] for r in rows])
    dm = np.array([r["dm"] for r in rows])
    eng = np.array([r["eng"] for r in rows])
    print(f"  engaged {int(eng.sum())} / manual {int((1-eng).sum())}   "
          f"LeverB {int(lb.sum())} / {int((1-lb).sum())}   "
          f"damper {int(dm.sum())} / {int((1-dm).sum())}   "
          f"corr(lb,dm) = {np.corrcoef(lb,dm)[0,1]:+.3f}")
    for arm, nm in ((1.0, "engaged"), (0.0, "manual ")):
        a = [r for r in rows if r["eng"] == arm]
        print(f"  {nm} |rate| p10/50/90 = "
              f"{np.percentile([r['rate'] for r in a],[10,50,90]).round(1)}  "
              f"hands = {np.percentile([r['hands'] for r in a],[10,50,90]).round(0)}")

    lr = np.log([r["rate"] for r in rows])
    lr_c = lr - lr.mean()
    lv = np.log([r["v"] for r in rows])
    lh = np.log([r["hands"] for r in rows])
    y69 = np.log([r["e69"] for r in rows])
    y32 = np.log([r["e32"] for r in rows])

    cols = [np.ones(len(rows)), eng, eng * lr_c, eng * lr_c * lb, eng * lb,
            eng * lr_c * dm, eng * dm, lr_c, lb, dm, lv, lh]
    names = ["const", "eng", "eng x lr", "eng x lr x LEVERB", "eng x LEVERB",
             "eng x lr x DAMPER", "eng x DAMPER", "log rate", "LeverB", "damper",
             "log v", "log hands"]
    for rt in routes[1:]:
        cols.append(np.array([1.0 if r["route"] == rt else 0.0 for r in rows]))
        names.append(f"route[{rt}]")
    X = np.column_stack(cols)
    fit = lambda y, Xm=X: np.linalg.lstsq(Xm, y, rcond=None)[0]
    b69, b32 = fit(y69), fit(y32)

    blk = blocks(rows)
    uq = np.unique(blk)
    idx = {g: np.where(blk == g)[0] for g in uq}
    D69, D32 = [], []
    for _ in range(3000):
        pick = np.concatenate([idx[g] for g in RNG.choice(uq, len(uq), replace=True)])
        try:
            D69.append(fit(y69[pick], X[pick]))
            D32.append(fit(y32[pick], X[pick]))
        except np.linalg.LinAlgError:
            pass
    D69, D32 = np.array(D69), np.array(D32)
    print(f"  {len(uq)} episode blocks  (v89_a6 had 93)\n")

    print("=" * 118)
    print("FULL-CORPUS MODEL")
    print("=" * 118)
    rep = {"n": len(rows), "routes": routes, "blocks": int(len(uq)), "terms": {}}
    # REF = the prior claim each term must be able to resolve. v89_a5 (12 routes) claimed the
    # `eng x lr` band contrast was +0.144; the LEVERB/DAMPER modulations must be able to resolve
    # an effect the size of the `eng x lr` term itself to be worth calling a null.
    REF = {"eng x lr": 0.144, "eng x lr x LEVERB": 0.144, "eng x lr x DAMPER": 0.144,
           "eng x LEVERB": 0.413, "eng x DAMPER": 0.413}
    for nm in ["eng", "eng x lr", "eng x lr x LEVERB", "eng x LEVERB",
               "eng x lr x DAMPER", "eng x DAMPER", "log hands"]:
        i = names.index(nm)
        rep["terms"][nm] = report(nm, b69, b32, D69, D32, i, REF.get(nm))

    print("\n  Engagement's 6-9 Hz amplification vs wheel rate, BY LEVER-B STATE")
    rmean = np.exp(lr.mean())
    ie, il, ilb, ib = (names.index(x) for x in
                       ("eng", "eng x lr", "eng x lr x LEVERB", "eng x LEVERB"))
    rep["amp"] = []
    print(f"    {'|rate|':>8s}  {'Lever B OFF':>22s}  {'Lever B ON':>22s}")
    for rate in (2, 5, 10, 20, 50, 100):
        g = np.log(rate) - np.log(rmean)
        off = np.exp(D69[:, ie] + D69[:, il] * g)
        on = np.exp(D69[:, ie] + D69[:, il] * g + D69[:, ilb] * g + D69[:, ib])
        print(f"    {rate:6d}    {np.median(off):6.2f}x [{np.percentile(off,2.5):4.2f},"
              f"{np.percentile(off,97.5):5.2f}]   {np.median(on):6.2f}x "
              f"[{np.percentile(on,2.5):4.2f},{np.percentile(on,97.5):5.2f}]")
        rep["amp"].append({"rate": rate, "off": float(np.median(off)), "on": float(np.median(on))})

    OUT.write_text(json.dumps(rep, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
