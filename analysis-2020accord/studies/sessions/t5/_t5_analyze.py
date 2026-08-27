#!/usr/bin/env python3
"""Task #5 -- PART B/C: where in rateKey does grind #1 actually live, and what dose did each build
deliver THERE?

Instruments are reused, never re-implemented (`_grind2_lib`, `_r31_common`, `_r4f_lib`, `_r50_lib`).
This script only slices, prices and reports.
"""
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
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _t5_ratekey_lib as T      # noqa: E402
import _t5_samples as S          # noqa: E402

CREEP = 4.0          # m/s, r47_rate_axis.CREEP upper edge (14.4 km/h)
CREEP20 = 20 / 3.6   # m/s, the brief's "creep < 20 km/h"
HWY = 14.0           # m/s
ORDER = ["V61/r31", "V59/r2c", "V64/r35", "V58/r2b", "V62/r37", "V65/r3a", "V65/r3b",
         "V67/r47", "V68/r4e", "V69/r4f", "V70/r50"]
# The record's own dose LABEL for each build, priced at the nominal rateKey 603 the design used.
NOMINAL = {"V61/r31": 0.000, "V59/r2c": 1.000, "V64/r35": 1.000, "V58/r2b": 1.000,
           "V62/r37": 2.000, "V65/r3a": 2.000, "V65/r3b": 2.000, "V67/r47": 2.000,
           "V68/r4e": 2.000, "V69/r4f": 3.508, "V70/r50": 1.836}
IMG = {"V61/r31": "v61", "V59/r2c": "v59", "V64/r35": "v64", "V58/r2b": "v58", "V62/r37": "v62",
       "V65/r3a": "v65", "V65/r3b": "v65", "V67/r47": "v67", "V68/r4e": "v68", "V69/r4f": "v69",
       "V70/r50": "v70"}
# V61 zeroed BOTH lane taps (0x3AB6C mul r1->r0, 0x3AC16 mov r1->r0), so its delivered multiplier is
# structurally 0 regardless of the gain table. builds/v50_v79/build_v61_tva.py, byte-verified in _t5_gain_check.
ZERO_LANE = {"V61/r31"}


def hdr(s):
    print(f"\n{'=' * 118}\n{s}\n{'=' * 118}")


def cat(store, tag, key, sel):
    return np.concatenate([r[key][sel(r)] for r in store[tag] if sel(r).any()]) if store[tag] else np.array([])


def slab(store, tag, eng=1, vlo=0.0, vhi=1e9):
    """One flat table of every sample of `tag` in the engagement arm and speed band."""
    cols = ("env18", "env40", "env24", "rate", "v", "eff", "ang", "t")
    acc = {c: [] for c in cols}
    acc["ep"] = []
    for i, r in enumerate(store[tag]):
        if r["eng"] != eng:
            continue
        m = (r["v"] >= vlo) & (r["v"] < vhi)
        if not m.any():
            continue
        for c in cols:
            acc[c].append(r[c][m])
        acc["ep"].append(np.full(int(m.sum()), i))
    if not acc["ep"]:
        return None
    return {c: np.concatenate(v) for c, v in acc.items()}


def q(v, ps=(50, 75, 90, 99)):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if not len(v):
        return "n=0"
    return "  ".join(f"p{p}={np.percentile(v, p):8.1f}" for p in ps) + f"  max={v.max():8.1f}"


def main():
    store = S.load()

    # =============================================================================================
    hdr("PART A -- the bus rate channel, and the two candidate maps onto gp-0x6ac0")
    print("""  `rate_c` in every cache is `-raw(0x14A[2:4])`; `rate_f` is `-0.1*raw(0x18F[2:4])`.
  The repo's anchor: raw 0x18F = 8 * raw 0x14A, and raw 0x14A is TRUE deg/s (regressed against the
  differentiated angle, slope 0.987-0.997).  So on BOTH scales rateKey is a fixed multiple of the
  SAME cached channel and the two differ by exactly 8x:
      SCALE A  rateKey = |rate_c| * 4.71211   (breakpoints 400/1400/1500/3000 = 85/297/318/637 deg/s)
      SCALE B  rateKey = |rate_c| * 0.58901   (breakpoints           = 679/2377/2547/5093 deg/s)""")
    for tag in ORDER:
        sl = slab(store, tag, eng=1)
        if sl is None:
            continue
        print(f"  {tag:10s} engaged |rate_c| counts:  {q(sl['rate'])}")

    # =============================================================================================
    hdr("PART B -- WHERE IN rateKEY DOES GRIND #1 LIVE?  (engaged, creep, during 18-22 Hz bursts)")
    print("  Burst = samples whose 18-22 Hz analytic band envelope (the record's own instrument,")
    print("  _r31_common.band_envelope) exceeds the threshold. Envelope is AMPLITUDE, so p-p = 2x.")
    for vhi, vlab in ((CREEP, "creep <14.4 km/h"), (CREEP20, "creep <20 km/h")):
        for thr in (300.0, 600.0, 1000.0):
            print(f"\n  --- {vlab},  env18 >= {thr:.0f} counts amplitude ({2 * thr:.0f} p-p) ---")
            print(f"    {'build':10s} {'nburst':>7s} {'%ofcreep':>8s} | "
                  f"{'|rate_c| deg/s  p50':>20s} {'p90':>7s} {'p99':>7s} {'max':>7s} | "
                  f"{'A: rateKey p50':>15s} {'p90':>7s} {'p99':>7s} | {'%>=400':>7s} {'%>=1400':>8s}"
                  f" | {'B: rk p99':>10s} {'%>=400':>7s}")
            pool_rate = []
            for tag in ORDER:
                sl = slab(store, tag, eng=1, vhi=vhi)
                if sl is None:
                    continue
                m = sl["env18"] >= thr
                n = int(m.sum())
                tot = len(sl["env18"])
                if n < 20:
                    print(f"    {tag:10s} {n:7d} {100 * n / max(tot, 1):7.2f}%  (too few)")
                    continue
                rc = sl["rate"][m]
                pool_rate.append(rc)
                rkA, rkB = rc * T.SCALE_A, rc * T.SCALE_B
                print(f"    {tag:10s} {n:7d} {100 * n / tot:7.2f}% | "
                      f"{np.percentile(rc, 50):20.1f} {np.percentile(rc, 90):7.1f} "
                      f"{np.percentile(rc, 99):7.1f} {rc.max():7.1f} | "
                      f"{np.percentile(rkA, 50):15.1f} {np.percentile(rkA, 90):7.1f} "
                      f"{np.percentile(rkA, 99):7.1f} | {100 * (rkA >= 400).mean():6.2f}% "
                      f"{100 * (rkA >= 1400).mean():7.2f}% | {np.percentile(rkB, 99):10.1f} "
                      f"{100 * (rkB >= 400).mean():6.2f}%")
            if pool_rate:
                rc = np.concatenate(pool_rate)
                rkA, rkB = rc * T.SCALE_A, rc * T.SCALE_B
                print(f"    {'POOLED':10s} {len(rc):7d} {'':8s} | "
                      f"{np.percentile(rc, 50):20.1f} {np.percentile(rc, 90):7.1f} "
                      f"{np.percentile(rc, 99):7.1f} {rc.max():7.1f} | "
                      f"{np.percentile(rkA, 50):15.1f} {np.percentile(rkA, 90):7.1f} "
                      f"{np.percentile(rkA, 99):7.1f} | {100 * (rkA >= 400).mean():6.2f}% "
                      f"{100 * (rkA >= 1400).mean():7.2f}% | {np.percentile(rkB, 99):10.1f} "
                      f"{100 * (rkB >= 400).mean():6.2f}%")

    # --- the relative definition, so every build contributes its own worst windows --------------
    print("\n  --- RELATIVE burst definition: top 1% of each build's OWN engaged-creep env18 ---")
    print(f"    {'build':10s} {'thr(cts)':>9s} {'n':>7s} | {'rate p50':>9s} {'p90':>7s} {'p99':>7s}"
          f" | {'A rk p50':>9s} {'p90':>8s} {'p99':>8s} {'%>=400':>7s} {'%>=1400':>8s}"
          f" | {'B rk p99':>9s} {'%>=400':>7s}")
    for tag in ORDER:
        sl = slab(store, tag, eng=1, vhi=CREEP)
        if sl is None or len(sl["env18"]) < 200:
            print(f"    {tag:10s}  (no engaged creep exposure: n="
                  f"{0 if sl is None else len(sl['env18'])})")
            continue
        thr = np.percentile(sl["env18"], 99)
        rc = sl["rate"][sl["env18"] >= thr]
        rkA, rkB = rc * T.SCALE_A, rc * T.SCALE_B
        print(f"    {tag:10s} {thr:9.0f} {len(rc):7d} | {np.percentile(rc, 50):9.1f} "
              f"{np.percentile(rc, 90):7.1f} {np.percentile(rc, 99):7.1f} | "
              f"{np.percentile(rkA, 50):9.1f} {np.percentile(rkA, 90):8.1f} "
              f"{np.percentile(rkA, 99):8.1f} {100 * (rkA >= 400).mean():6.2f}% "
              f"{100 * (rkA >= 1400).mean():7.2f}% | {np.percentile(rkB, 99):9.1f} "
              f"{100 * (rkB >= 400).mean():6.2f}%")

    # =============================================================================================
    hdr("PART C -- THE RE-PRICED DOSE: the multiplier each build actually delivered AT those samples")
    print("  Per sample: evaluate the build's own byte-read LERP at (its own speed counts, its own")
    print("  rateKey) and divide by stock's at the SAME point. V61 is 0 by construction (both taps")
    print("  zeroed). Reported as the MEDIAN over burst samples; the mean is beside it.")
    for scale_name, scale in T.SCALES:
        print(f"\n  --- axis scale {scale_name} ---")
        print(f"    {'build':10s} {'nominal@603':>11s} | "
              + "".join(f"{c:>22s}" for c in ("burst env18>=600", "burst env18>=300",
                                              "ALL engaged creep")))
        print(f"    {'':10s} {'':11s} | " + "".join(f"{'median   mean':>22s}" for _ in range(3)))
        for tag in ORDER:
            sl = slab(store, tag, eng=1, vhi=CREEP)
            if sl is None:
                continue
            cells = []
            for sel in (sl["env18"] >= 600, sl["env18"] >= 300, np.ones(len(sl["env18"]), bool)):
                if sel.sum() < 20:
                    cells.append("        --        ")
                    continue
                if tag in ZERO_LANE:
                    cells.append(f"{0.0:9.3f}{0.0:9.3f}    ")
                    continue
                sc = T.speed_counts(sl["v"][sel]).astype(np.int64)
                rk = (sl["rate"][sel] * scale).astype(np.int64)
                dv = T.delivered(IMG[tag], sc, rk, np.ones(len(sc), bool))
                cells.append(f"{np.median(dv):9.3f}{np.mean(dv):9.3f}    ")
            print(f"    {tag:10s} {NOMINAL[tag]:11.3f} | " + "".join(f"{c:>22s}" for c in cells))


if __name__ == "__main__":
    main()
