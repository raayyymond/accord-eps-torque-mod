#!/usr/bin/env python3
"""studies/sessions/v89/v89_h4_load_axis.py -- is the command coefficient a LOAD axis, or just steering geometry?

WHERE v89_h3 LEFT IT (all with the Hann-window fix; step 0 reproduces the original +1.074 exactly):
    log e_6-9 ~ log cmd_RAW rms (contains DC)   +1.064 [+0.790,+1.418]   contrast +0.949
    log e_6-9 ~ log cmd DEMEANED (AC only)      -0.037 [-0.055,+0.119]   contrast -0.025  NULL
    log e_6-9 ~ log mean|cmd| (pure LOAD proxy) +0.955 [+0.696,+1.276]   contrast +0.860
=> the effect is carried ENTIRELY by how hard LKAS is pushing, and NOT AT ALL by how much the
   command fluctuates.  That kills BOTH alternatives I proposed:
     A1 circularity -- the shared 6-9 Hz component lives in the AC part, which contributes zero;
     A2 "the mode's own Q" -- a lightly-damped resonance is excited by FLUCTUATION.  A DC offset
        cannot excite 7.8 Hz.  If Q-amplification of broadband command content were the mechanism,
        the AC regressor would carry the effect.  It carries none.

WHAT IS STILL OPEN, and this file tests it.  `mean|cmd|` is not uniquely rack-mesh load.  It rises
with steering angle, curvature and lateral acceleration.  If any of those explains the coefficient
away, the axis is GEOMETRY, not load.  Competitors entered against it:
    |ang| (steering angle)  ·  |ang| x v^2 (a lateral-acceleration / tyre-load proxy)  ·  |rate|
Also here: PART B, the hysteresis (Coulomb) width vs command, with the corrected regressor.
"""
from __future__ import annotations
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from v89_h3_decompose_1074 import bandrms, blocks_of, fit, FS, NW, HOP, ARMED  # noqa: E402
from v89_h2_hysteresis_and_challenge import coulomb  # noqa: E402

RNG = np.random.default_rng(890842)
ROOT = Path(__file__).resolve().parents[3].parent
OUT = ROOT / "_scratch/cache/r73" / "v89_h4_load.json"
ALL = {"r6d": "v84", "r6e": "v85", "r6f": "v86", "r70": "v86b", "r71": "v87", "r73": "v88"}


def harvest():
    from scipy.signal import butter, sosfiltfilt
    rows = []
    for rt in ALL:
        z = np.load(ROOT / ("_cache_" + rt) / (rt + ".npz"), allow_pickle=True)
        n = len(z["t"])
        tq = np.asarray(z["tq"], float)
        ang = np.asarray(z["ang"], float)
        rate = np.asarray(z["rate_c"], float)
        v = np.asarray(z["cs_v"], float)
        eng = np.asarray(z["cc_lat"], float) > 0.5
        sst = np.asarray(z["sstat"], float)
        seg = np.asarray(z["seg"], int) if "seg" in z.files else np.zeros(n, int)
        cmd = np.asarray(z["sc_tq"], float)
        sos = butter(4, 3.0 / (FS / 2), btype="low", output="sos")
        g = np.isfinite(tq)
        lf = np.zeros(n)
        if g.sum() > 30:
            lf[g] = sosfiltfilt(sos, tq[g])
        for s0 in range(0, n - NW + 1, HOP):
            sl = slice(s0, s0 + NW)
            if eng[sl].mean() < 0.999 or (sst[sl] != 0).any():
                continue
            if not (np.isfinite(tq[sl]).all() and np.isfinite(cmd[sl]).all()):
                continue
            vm = float(np.median(v[sl]))
            rm = float(np.median(np.abs(rate[sl])))
            hm = max(float(np.median(np.abs(lf[sl]))), 1e-3)
            am = max(float(np.mean(np.abs(ang[sl]))), 1e-3)
            if vm <= 0.3 or rm < 1.0 or hm < 1.0:
                continue
            c = cmd[sl]
            raw = float(np.sqrt(np.mean(c ** 2)))
            if raw <= 0:
                continue
            cw = coulomb(tq[sl], ang[sl], rate[sl])
            rows.append({"route": rt, "seg": int(np.median(seg[sl])), "i0": s0,
                         "v": vm, "rate": rm, "hands": hm, "ang": am,
                         "alat": max(am * vm * vm, 1e-6),
                         "cmd_raw": raw,
                         "cmd_absmean": max(float(np.mean(np.abs(c))), 1e-6),
                         "cmd_ac": max(bandrms(c, 0, 0, exclude=True), 1e-6),
                         "coul": (cw[0] if cw and cw[0] > 0 else None),
                         "visc": (cw[1] if cw and cw[1] > 0 else None),
                         "e69": max(bandrms(tq[sl], 6.0, 9.0), 1e-9),
                         "e32": max(bandrms(tq[sl], 32.0, 38.0), 1e-9)})
    return rows


def multi(rows, xnames, yname, nb=2000, placebo_on=None):
    rows = [r for r in rows if r.get(yname) is not None]
    blk = blocks_of(rows)
    n = len(rows)
    cols, names = [np.ones(n)], ["const"]
    for k in xnames:
        a = np.log([r[k] for r in rows])
        cols.append(a - a.mean())
        names.append(k)
    rts = sorted({r["route"] for r in rows})
    for rt in rts[1:]:
        cols.append(np.array([1.0 if r["route"] == rt else 0.0 for r in rows]))
        names.append("route[" + rt + "]")
    X = np.column_stack(cols)
    y = np.log([r[yname] for r in rows])
    b = fit(X, y)
    uq = np.unique(blk)
    idx = {g: np.where(blk == g)[0] for g in uq}
    D = []
    for _ in range(nb):
        pick = np.concatenate([idx[g] for g in RNG.choice(uq, len(uq), replace=True)])
        try:
            D.append(fit(X[pick], y[pick]))
        except np.linalg.LinAlgError:
            pass
    D = np.array(D)
    out = {"_n": n, "_blocks": int(len(uq))}
    for k in xnames:
        j = names.index(k)
        lo, hi = np.percentile(D[:, j], [2.5, 97.5])
        out[k] = {"b": float(b[j]), "ci": [float(lo), float(hi)],
                  "verdict": "EXCLUDES 0" if (lo > 0 or hi < 0) else "NULL"}
    if placebo_on:
        j = names.index(placebo_on)
        lx = np.log([r[placebo_on] for r in rows])
        P = []
        for _ in range(400):
            perm = RNG.permutation(uq)
            xs = np.empty(n)
            for a, c in zip(uq, perm):
                ia, ic = idx[a], idx[c]
                xs[ia] = lx[ic][np.arange(len(ia)) % len(ic)]
            Xp = X.copy()
            Xp[:, j] = xs - xs.mean()
            P.append(fit(Xp, y)[j])
        out["_placebo_p95"] = float(np.percentile(np.abs(P), 95))
    return out


def show(lab, r, keys):
    line = "   {:44s} n={:4d}/{:3d}blk".format(lab, r["_n"], r["_blocks"])
    print(line)
    for k in keys:
        d = r[k]
        print("        {:14s} {:+7.3f} [{:+6.3f},{:+6.3f}]   {}".format(
            k, d["b"], d["ci"][0], d["ci"][1], d["verdict"]))
    if "_placebo_p95" in r:
        print("        placebo |b| p95 {:.3f}".format(r["_placebo_p95"]))


def main():
    rows = harvest()
    stock = [r for r in rows if r["route"] not in ARMED]
    rep = {}
    print("=" * 104)
    print("CORRELATIONS among the candidate load/geometry axes (stock-damper, engaged)")
    print("=" * 104)
    ks = ["cmd_absmean", "ang", "alat", "rate", "v"]
    M = np.array([np.log([r[k] for r in stock]) for k in ks])
    C = np.corrcoef(M)
    print("        " + "".join("{:>13s}".format(k) for k in ks))
    for i, k in enumerate(ks):
        print("   {:11s}".format(k) + "".join("{:+13.3f}".format(C[i, j])
                                              for j in range(len(ks))))

    print("\n" + "=" * 104)
    print("IS IT LOAD, OR GEOMETRY?  competitors entered against the command  (y = log e_6-9)")
    print("=" * 104)
    for lab, xs in (("command alone", ["cmd_absmean"]),
                    ("+ steering angle", ["cmd_absmean", "ang"]),
                    ("+ angle and a_lat proxy", ["cmd_absmean", "ang", "alat"]),
                    ("+ angle, a_lat, wheel rate", ["cmd_absmean", "ang", "alat", "rate"])):
        r = multi(stock, xs + ["hands", "v"], "e69", placebo_on="cmd_absmean")
        rep["e69 " + lab] = r
        show(lab, r, xs)
    print("\n   the same on the 32-38 Hz CONTROL band:")
    for lab, xs in (("command alone", ["cmd_absmean"]),
                    ("+ angle, a_lat, wheel rate", ["cmd_absmean", "ang", "alat", "rate"])):
        r = multi(stock, xs + ["hands", "v"], "e32")
        rep["e32 " + lab] = r
        show(lab, r, xs)

    print("\n" + "=" * 104)
    print("PART B -- HYSTERESIS (Coulomb) WIDTH vs COMMAND, with the CORRECTED regressor")
    print("   M1 predicts FLAT.  M2 predicts RISING.  `visc` is the negative control.")
    print("=" * 104)
    for yn, ylab in (("coul", "COULOMB width"), ("visc", "VISCOUS (neg. control)")):
        for lab, xs in (("vs command alone", ["cmd_absmean"]),
                        ("vs command + angle + a_lat", ["cmd_absmean", "ang", "alat"])):
            r = multi(stock, xs + ["rate", "v", "hands"], yn, placebo_on="cmd_absmean")
            rep[ylab + " " + lab] = r
            show(ylab + " " + lab, r, xs)
        print()
    c = np.array([r["coul"] for r in stock if r["coul"]])
    print("   Coulomb width: p10 {:.1f}  median {:.1f}  p90 {:.1f} counts   ({} windows)".format(
        *np.percentile(c, [10, 50, 90]), len(c)))

    OUT.write_text(json.dumps(rep, indent=1, default=float))
    print("\nwrote {}".format(OUT))


if __name__ == "__main__":
    main()
