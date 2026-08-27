#!/usr/bin/env python3
"""studies/sessions/v89/v89_e3_leak_profile.py -- the BAND-PROFILE shape test, with a PER-BAND wheel-order veto.

v89_e2's R2/R5 were degenerate: they vetoed a window if a wheel order landed in ANY of the bands
being scored.  With 14 contiguous 3 Hz slices covering 3-45 Hz that is almost every window (11 of
~100 survived).  The veto must be applied PER BAND: a window is admissible for slice S if no order
1..N lands in S, and separately for the control slice.

The observer-leak model's signature is not one band -- it is a MONOTONE DECREASING log-ratio with
frequency (+0.96 at 3-6 Hz down to +0.12 at 42-45 Hz).  Correlating the measured A286 profile
against that curve is a sharper test than any single band, and it is free of the choice of control.
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
from scipy.signal import butter, sosfiltfilt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from v89_e1_leak_retrodiction import (ALPHA, DAMPER_FC, VMAX_MATCH, CORPUS, NW, HOP,
                                      blocks_of, fit, ci, spec, brms, order_hits)

RNG = np.random.default_rng(890812)
ORD = int(sys.argv[1]) if len(sys.argv) > 1 else 6
OUT = Path(__file__).resolve().parents[3].parent / "_scratch/cache/r73" / "v89_e3_profile.json"
FS_FW = 1000.0
SLICES = {"{}-{}".format(a, b): (float(a), float(b))
          for a, b in [(3, 6), (6, 9), (9, 12), (12, 15), (15, 18), (18, 21), (21, 24),
                       (24, 27), (27, 30), (30, 33), (33, 36), (36, 39), (39, 42), (42, 45)]}


def model_log_ratio(lo, hi):
    def H(f, al, d):
        z = np.exp(-1j * 2 * np.pi * f / FS_FW)
        return (z ** d) * al / (1 - (1 - al) * z)

    def leak(f, al):
        return np.abs(H(f, al, 1) - H(f, 102 / 1024., 0))

    g = np.arange(lo, hi, 0.05)
    return float(np.log(np.sqrt(np.mean(leak(g, 286 / 4096.) ** 2))
                        / np.sqrt(np.mean(leak(g, 573 / 4096.) ** 2))))


def harvest_all(vmax=VMAX_MATCH):
    """No veto applied here -- every slice energy plus the window speed, so the veto can be
    applied per band downstream."""
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
            f, p = spec(tq[sl], fs)
            b = {k: brms(f, p, lo, hi) for k, (lo, hi) in SLICES.items()}
            if min(b.values()) <= 0:
                continue
            rows.append({"route": rt, "a286": 1.0 if ALPHA[rt] == 286 else 0.0,
                         "fc": float(DAMPER_FC[rt]), "seg": int(np.median(seg[sl])), "i0": s,
                         "eng": 1.0 if e > 0.98 else 0.0, "v": vm, "rate": rm, "hands": hm,
                         **{"e_" + k: b[k] for k in SLICES}})
    return rows


def band_fit(rows, key, nb=2000):
    """A286 coefficient for one slice, on the windows admissible for THAT slice."""
    lo, hi = SLICES[key]
    keep = [r for r in rows if not order_hits(r["v"], lo, hi, ORD)]
    if len(keep) < 25 or len(set(r["a286"] for r in keep)) < 2:
        return None
    b = blocks_of(keep)
    n = len(keep)
    lv = np.log([r["v"] for r in keep])
    lr = np.log([r["rate"] for r in keep])
    lh = np.log([r["hands"] for r in keep])
    X = np.column_stack([np.ones(n), np.array([r["a286"] for r in keep]),
                         lv - lv.mean(), lr - lr.mean(), lh - lh.mean(),
                         np.array([r["fc"] for r in keep])])
    y = np.log([r["e_" + key] for r in keep])
    obs = fit(X, y)[1]
    uq = np.unique(b)
    idx = {g: np.where(b == g)[0] for g in uq}
    D = []
    for _ in range(nb):
        pick = np.concatenate([idx[g] for g in RNG.choice(uq, len(uq), replace=True)])
        try:
            D.append(fit(X[pick], y[pick])[1])
        except np.linalg.LinAlgError:
            pass
    return {"b": float(obs), "ci": list(ci(np.array(D))), "n": n, "blocks": int(len(uq)),
            "n286": int(sum(r["a286"] for r in keep))}


def main():
    rows = harvest_all()
    print("harvested {} windows (v<{}, no veto yet); engaged {}".format(
        len(rows), VMAX_MATCH, sum(r["eng"] for r in rows)))
    rep = {}
    for lab, sel in (("ENGAGED", 1.0), ("MANUAL", 0.0)):
        rws = [r for r in rows if r["eng"] == sel]
        print("\n" + "=" * 100)
        print("BAND PROFILE, per-slice wheel-order veto (orders 1-{}".format(ORD) + ")   [{}]".format(lab))
        print("  model signature: MONOTONE DECREASING, +0.96 at 3-6 Hz -> +0.12 at 42-45 Hz")
        print("=" * 100)
        print("  {:8s} {:>8s} {:>17s} {:>8s}  {:>5s} {:>4s}".format(
            "band", "A286", "95% CI", "model", "n", "blk"))
        prof = {}
        for k in SLICES:
            r = band_fit(rws, k)
            m = model_log_ratio(*SLICES[k])
            if r is None:
                print("  {:8s}  -- too few admissible windows --".format(k))
                continue
            sig = "*" if (r["ci"][0] > 0 or r["ci"][1] < 0) else " "
            bar = ("-" if r["b"] < 0 else "+") + "#" * min(40, int(round(abs(r["b"]) * 14)))
            print("  {:8s} {:+8.3f} [{:+6.3f},{:+6.3f}]{} {:+8.3f}  {:5d} {:4d}  {}".format(
                k, r["b"], r["ci"][0], r["ci"][1], sig, m, r["n"], r["blocks"], bar))
            prof[k] = dict(r, model=m)
        if len(prof) >= 6:
            o = np.array([prof[k]["b"] for k in prof])
            mm = np.array([prof[k]["model"] for k in prof])
            cc = float(np.corrcoef(o, mm)[0, 1])
            # Spearman
            ro = np.argsort(np.argsort(o)).astype(float)
            rm = np.argsort(np.argsort(mm)).astype(float)
            sp = float(np.corrcoef(ro, rm)[0, 1])
            print("\n  corr(observed, model) = {:+.3f}   Spearman = {:+.3f}   "
                  "(model predicts +1; refutation predicts <= 0)".format(cc, sp))
            print("  mean A286 across slices = {:+.3f} (a route-level offset; the SHAPE is the "
                  "test)".format(o.mean()))
            oc = o - o.mean()
            mc = mm - mm.mean()
            cc2 = float(np.corrcoef(oc, mc)[0, 1])
            print("  offset-removed corr     = {:+.3f}".format(cc2))
            rep[lab] = {"prof": prof, "corr": cc, "spearman": sp, "mean_b": float(o.mean())}
    OUT.write_text(json.dumps(rep, indent=1, default=float))
    print("\nwrote {}".format(OUT))


if __name__ == "__main__":
    main()
