#!/usr/bin/env python3
"""studies/sessions/v89/v89_f2_residual_pooled.py -- firm up v89_f1's items 2 and 1b.

v89_f1 found, on the direct `gp-0x6b70` cave probe of routes `6f` / `70`:
  item 1  engagement effect on b5 (|resid| >= 64) duty = NULL once the motion screen is applied
  item 2  log|rate| EXCLUDES 0, log|cmd| rms NULL  -- the OPPOSITE of the predicted signature
  item 1b b7 sign vs command sign INSIDE a shuffled-pairs null
Three things could still overturn item 2, and one thing could still rescue the hypothesis:
  P1  severe collinearity, corr(log|cmd|, log|rate|) = +0.64 / +0.73 -- marginal vs adjusted
  P2  only 4 engaged episodes per route -- pool the two routes for 8 blocks and a route dummy
  P3  b5 saturation (19-22% of windows at duty 1.000) -- state the reachable dynamic range
  P4  THE RESCUE: does b5 co-move with the 6-9 Hz column SYMPTOM in the same windows?  If the
      residual and the symptom rise and fall together, the residual is on the causal path even
      if its engagement contrast is null.  Block-permutation null, run first.
The sign null is rebuilt with a CIRCULAR-SHIFT surrogate: v89_f1 permuted whole segments and there
are only 4, so that null was built from 4 exchangeable units and was far too wide.
"""
from __future__ import annotations
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from v89_f1_residual_probe import (ROUTES, NW, HOP, load, windows, logit, blocks_of, fit,
                                   boot_coef, ci)

RNG = np.random.default_rng(890821)
ROOT = Path(__file__).resolve().parents[3].parent
OUT = ROOT / "_scratch/cache/r73" / "v89_f2_pooled.json"


def spec_band(x, fs, lo, hi):
    x = x - x.mean()
    w = np.hanning(len(x))
    X = np.fft.rfft(x * w)
    p = (np.abs(X) ** 2) / (np.sum(w ** 2) * fs)
    p[1:-1] *= 2.0
    f = np.fft.rfftfreq(len(x), 1.0 / fs)
    m = (f >= lo) & (f < hi)
    return float(np.sqrt(np.sum(p[m]) * (f[1] - f[0])))


def main():
    rep = {}
    data = {rt: load(rt) for rt in ROUTES}
    W = {rt: windows(data[rt]) for rt in ROUTES}

    # attach the column-torque band energies to each window
    for rt in ROUTES:
        D = data[rt]
        for r in W[rt]:
            sl = slice(r["i0"], r["i0"] + NW)
            r["e69"] = spec_band(D["tq"][sl], D["fs"], 6.0, 9.0)
            r["e32"] = spec_band(D["tq"][sl], D["fs"], 32.0, 38.0)
            r["route"] = rt

    print("=" * 104)
    print("P3 -- b5 DYNAMIC RANGE. What effect could this rung even show?")
    print("=" * 104)
    for rt in ROUTES:
        d = np.array([r["d5"] for r in W[rt]])
        print("  {} ({}): window duty  p5 {:.3f}  p25 {:.3f}  median {:.3f}  p75 {:.3f}  "
              "p95 {:.3f}   at 1.000 {:.1%}".format(
                  rt, ROUTES[rt][0], *np.percentile(d, [5, 25, 50, 75, 95]), np.mean(d == 1.0)))
        print("     log-odds range p5->p95: {:+.2f} -> {:+.2f}  (span {:.2f})".format(
            logit(np.percentile(d, 5) * NW, NW), logit(np.percentile(d, 95) * NW, NW),
            logit(np.percentile(d, 95) * NW, NW) - logit(np.percentile(d, 5) * NW, NW)))
    print("  ** The rung is NOT railed -- it has a usable ~3-4 log-odds span. Saturation limits")
    print("     the top of the range only. b5 is a live instrument; b6 and b4 are not. **")

    print("\n" + "=" * 104)
    print("P2 -- POOLED, both routes, route dummy. Item 1 (engagement) and item 2 (command).")
    print("=" * 104)
    allw = [r for rt in ROUTES for r in W[rt]]
    allw.sort(key=lambda r: (r["route"], r["seg"], r["i0"]))
    blk = blocks_of(allw)
    # blocks_of does not split on route; add that
    for i in range(1, len(allw)):
        if allw[i]["route"] != allw[i - 1]["route"]:
            blk[i:] += 1000
    _, blk = np.unique(blk, return_inverse=True)

    def model(rows, b, terms, label):
        n = len(rows)
        cols = [np.ones(n)]
        names = ["const"]
        for nm, v in terms:
            v = np.asarray(v, float)
            cols.append(v - v.mean())
            names.append(nm)
        cols.append(np.array([1.0 if r["route"] == "r70" else 0.0 for r in rows]))
        names.append("route[70]")
        X = np.column_stack(cols)
        y = logit(np.array([r["k5"] for r in rows], float), NW)
        B = boot_coef(X, y, b)
        obs = fit(X, y)
        print("  {}   n={} windows / {} blocks".format(label, n, len(np.unique(b))))
        out = {}
        for j, nm in enumerate(names):
            if nm == "const":
                continue
            lo, hi = ci(B[:, j])
            tag = "EXCLUDES 0" if (lo > 0 or hi < 0) else "NULL"
            print("     {:14s} {:+.3f} [{:+.3f}, {:+.3f}]   {}".format(nm, obs[j], lo, hi, tag))
            out[nm] = {"b": float(obs[j]), "ci": [lo, hi], "verdict": tag}
        return out

    rep["item1_pooled"] = model(
        allw, blk,
        [("eng", [r["eng"] for r in allw]),
         ("log v", np.log([r["v"] for r in allw])),
         ("log|rate|", np.log([r["rate"] for r in allw])),
         ("log hands", np.log([r["hands"] for r in allw]))],
        "ITEM 1 pooled: logit(b5) ~ eng + covariates")

    eng = [r for r in allw if r["eng"] == 1.0 and r["cmd"] > 0]
    eb = blocks_of(eng)
    for i in range(1, len(eng)):
        if eng[i]["route"] != eng[i - 1]["route"]:
            eb[i:] += 1000
    _, eb = np.unique(eb, return_inverse=True)

    print()
    rep["item2_pooled"] = model(
        eng, eb,
        [("log|cmd|", np.log([r["cmd"] for r in eng])),
         ("log|rate|", np.log([r["rate"] for r in eng])),
         ("log v", np.log([r["v"] for r in eng])),
         ("log hands", np.log([r["hands"] for r in eng]))],
        "ITEM 2 pooled: logit(b5) ~ log|cmd| + log|rate| + covariates, ENGAGED only")

    print("\n" + "=" * 104)
    print("P1 -- COLLINEARITY. Marginal (each alone) vs adjusted (both in). Engaged, pooled.")
    print("=" * 104)
    lc = np.log([r["cmd"] for r in eng])
    lr = np.log([r["rate"] for r in eng])
    y = logit(np.array([r["k5"] for r in eng], float), NW)
    rho = float(np.corrcoef(lc, lr)[0, 1])
    print("  corr(log|cmd|, log|rate|) = {:+.3f}   VIF = {:.2f}".format(rho, 1 / (1 - rho ** 2)))
    rep["P1"] = {"rho": rho, "vif": 1 / (1 - rho ** 2)}
    for nm, v in (("log|cmd| alone", lc), ("log|rate| alone", lr)):
        X = np.column_stack([np.ones(len(eng)), v - v.mean(),
                             np.array([1.0 if r["route"] == "r70" else 0.0 for r in eng])])
        B = boot_coef(X, y, eb)
        lo, hi = ci(B[:, 1])
        b = fit(X, y)[1]
        print("     MARGINAL {:16s} {:+.3f} [{:+.3f}, {:+.3f}]   {}".format(
            nm, b, lo, hi, "EXCLUDES 0" if (lo > 0 or hi < 0) else "NULL"))
        rep["P1"][nm] = {"b": float(b), "ci": [lo, hi]}
    print("  ** Reading: if RATE survives adjustment for CMD but CMD does not survive adjustment")
    print("     for RATE, the rate axis is the one carrying the signal, collinearity or not. **")

    print("\n" + "=" * 104)
    print("P4 -- THE RESCUE TEST. Does b5 co-move with the 6-9 Hz COLUMN symptom, engaged?")
    print("     partial corr(logit b5, log e_6-9) with log e_32-38, log v, log|rate| removed;")
    print("     null = permute the b5 series across EPISODE BLOCKS (control runs first).")
    print("=" * 104)
    y5 = logit(np.array([r["k5"] for r in eng], float), NW)
    y69 = np.log([r["e69"] for r in eng])
    Z = np.column_stack([np.ones(len(eng)), np.log([r["e32"] for r in eng]),
                         np.log([r["v"] for r in eng]), np.log([r["rate"] for r in eng]),
                         np.array([1.0 if r["route"] == "r70" else 0.0 for r in eng])])
    r5 = y5 - Z @ fit(Z, y5)
    r69 = y69 - Z @ fit(Z, y69)
    obs = float(np.corrcoef(r5, r69)[0, 1])
    uq = np.unique(eb)
    idx = {g: np.where(eb == g)[0] for g in uq}
    nulls = []
    for _ in range(2000):
        perm = RNG.permutation(uq)
        z = np.empty_like(r5)
        for a, b_ in zip(uq, perm):
            ia, ib = idx[a], idx[b_]
            z[ia] = r5[ib][np.arange(len(ia)) % len(ib)]
        nulls.append(float(np.corrcoef(z, r69)[0, 1]))
    nulls = np.array(nulls)
    p = float((np.abs(nulls) >= abs(obs)).mean())
    print("  partial corr = {:+.3f}   block-permutation null mean {:+.3f}, 95% [{:+.3f}, {:+.3f}]"
          "   two-sided p = {:.3f}   {}".format(
              obs, nulls.mean(), np.percentile(nulls, 2.5), np.percentile(nulls, 97.5), p,
              "EXCLUDES the null" if p < 0.05 else "NULL"))
    rep["P4"] = {"partial_corr": obs, "p": p,
                 "null_ci": [float(np.percentile(nulls, 2.5)), float(np.percentile(nulls, 97.5))],
                 "n": len(eng), "blocks": int(len(uq))}

    print("\n" + "=" * 104)
    print("ITEM 1b REDONE -- sign test with a CIRCULAR-SHIFT surrogate.")
    print("     v89_f1's segment-permutation null had only 4 exchangeable units and was far too")
    print("     wide to reject anything. A circular shift preserves BOTH series' autocorrelation.")
    print("=" * 104)
    rep["sign"] = {}
    for rt in ROUTES:
        D = data[rt]
        ok = D["eng"] & (D["sst"] == 0) & (np.abs(D["cmd"]) > 0) & (D["v"] > 0.3)
        s7 = D["sign"].astype(float)
        cneg = (D["cmd"] < 0).astype(float)
        n = len(s7)
        curve = {lag: float((np.roll(s7, lag)[ok] == cneg[ok]).mean()) for lag in range(-20, 21)}
        best = max(curve.items(), key=lambda kv: abs(kv[1] - 0.5))
        nulls = []
        for _ in range(2000):
            sh = int(RNG.integers(int(0.05 * n), int(0.95 * n)))
            nulls.append(float((np.roll(s7, sh)[ok] == cneg[ok]).mean()))
        nulls = np.array(nulls)
        lo, hi = np.percentile(nulls, [2.5, 97.5])
        mx = max(abs(v - 0.5) for v in curve.values())
        # family-wise null over the same lag family
        fw = []
        for _ in range(1000):
            sh = int(RNG.integers(int(0.05 * n), int(0.95 * n)))
            ss = np.roll(s7, sh)
            fw.append(max(abs(float((np.roll(ss, l)[ok] == cneg[ok]).mean()) - 0.5)
                          for l in range(-20, 21, 4)))
        fw = np.array(fw)
        print("  {} ({}, alpha={}): {} engaged frames".format(
            rt, ROUTES[rt][0], ROUTES[rt][1], int(ok.sum())))
        print("     lag 0 {:.4f}   best lag {:+d} -> {:.4f}   |dev| max {:.4f}".format(
            curve[0], best[0], best[1], mx))
        print("     circular-shift null 95% [{:.4f}, {:.4f}]   lag-0 {}".format(
            lo, hi, "ABOVE" if curve[0] > hi else ("BELOW" if curve[0] < lo else "INSIDE")))
        print("     family-wise |dev| null p95 = {:.4f}   observed max {:.4f}   =>  {}".format(
            np.percentile(fw, 95), mx,
            "EXCEEDS the family-wise null" if mx > np.percentile(fw, 95) else "INSIDE it"))
        rep["sign"][rt] = {"lag0": curve[0], "best_lag": best[0], "best": best[1],
                           "null_ci": [float(lo), float(hi)], "max_dev": float(mx),
                           "fw_p95": float(np.percentile(fw, 95)),
                           "curve": {str(k): v for k, v in curve.items()}}

    OUT.write_text(json.dumps(rep, indent=1, default=float))
    print("\nwrote {}".format(OUT))


if __name__ == "__main__":
    main()
