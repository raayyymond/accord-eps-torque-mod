#!/usr/bin/env python3
"""§1 CENSUS for routes 54 (V71B) and 58 (V71C), against the recent corpus.

Every null in the symptom scripts must be read against this. Frame-level exposure (not window
counts), so the numbers are physical seconds, and the parked segments are called out separately.
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
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r58_lib as R  # noqa: E402

R.install_fs()
KMH = 1 / 3.6
CREEP, CORNER, HWY = 20 * KMH, None, 50 * KMH
OUT = Path(__file__).resolve().parents[4] / "_scratch/out/_r58_census.json"

BUILDS = ["V61/r31", "V59/r2c", "V58/r2b", "V62/r37", "V65/r3b", "V67/r47", "V68/r4e",
          "V69/r4f", "V70/r50", "V71B/r54", "V71C/r58"]


def seconds(build):
    """Frame-level exposure table for one build, in seconds."""
    B = G.BUILDS[build]
    acc = dict(tot=0.0, eng=0.0, man=0.0, park=0.0, eng_creep=0.0, man_creep=0.0,
               eng_hwy=0.0, man_hwy=0.0, eng_corner=0.0, man_corner=0.0,
               eng_ho_creep=0.0, man_ho_creep=0.0, eng_ho=0.0, man_ho=0.0, nseg=0,
               gate_agree=np.nan, gate_n=0.0, gate_hi=0.0)
    ga_n = ga_k = 0
    for s in B["segs"]:
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, B["cache"], B["pfx"])
        fs = G.fs_of(d)
        dt = 1.0 / fs
        n = len(d["t"])
        acc["nseg"] += 1
        acc["tot"] += n * dt
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        gear = np.asarray(d["cs_gear"], float) if "cs_gear" in d else np.full(n, np.nan)
        parked = (v < 0.05) & (np.nan_to_num(gear, nan=2.0) == C.PARK)
        acc["park"] += parked.sum() * dt
        eff = np.abs(C.sustained(np.asarray(d["tq"], float), fs))
        ho = eff <= 300.0                       # the headline test's hands-off criterion
        ang = np.abs(np.asarray(d["ang"], float))
        corner = ang >= 30.0
        for tag, m in (("eng", lat), ("man", ~lat)):
            acc[tag] += m.sum() * dt
            acc[tag + "_creep"] += (m & (v < CREEP)).sum() * dt
            acc[tag + "_hwy"] += (m & (v >= HWY)).sum() * dt
            acc[tag + "_corner"] += (m & corner).sum() * dt
            acc[tag + "_ho"] += (m & ho).sum() * dt
            acc[tag + "_ho_creep"] += (m & ho & (v < 4.0)).sum() * dt
        # 🛑 `g6806` is a NaN PLACEHOLDER on r4f / r50 / r54 / r58 -- those extractors write
        # `np.full(n, nan)` because the probe spends all four bits elsewhere. Treating NaN as
        # "gate low" would report a spurious 0 s gate-high on builds whose gate IS live (V71C).
        if "g6806" in d and np.isfinite(np.asarray(d["g6806"], float)).any():
            g = np.asarray(d["g6806"], float) > 0.5
            ga_n += n
            ga_k += int((g == lat).sum())
            acc["gate_hi"] += g.sum() * dt
    acc["gate_n"] = ga_n
    acc["gate_agree"] = (ga_k / ga_n) if ga_n else np.nan
    return acc


def main():
    R.hdr("§1  CENSUS -- frame-level exposure, seconds. `creep` < 20 km/h, `hwy` >= 50 km/h,\n"
          "     `corner` |angle| >= 30 deg, `ho` (hands-off) |lowpass(tq,3Hz)| <= 300 counts.")
    rows = {}
    hdr = (f"{'build':<11}{'nseg':>5}{'total':>9}{'engaged':>9}{'manual':>9}{'parked':>8}"
           f"{'engCreep':>10}{'manCreep':>10}{'engHwy':>9}{'manHwy':>9}"
           f"{'engCorner':>10}{'engHO':>8}{'manHO':>8}{'engHOcreep':>11}{'manHOcreep':>11}")
    print(hdr)
    print("-" * len(hdr))
    for b in BUILDS:
        if b not in G.BUILDS:
            continue
        a = seconds(b)
        rows[b] = a
        print(f"{b:<11}{a['nseg']:>5}{a['tot']:>9.1f}{a['eng']:>9.1f}{a['man']:>9.1f}"
              f"{a['park']:>8.1f}{a['eng_creep']:>10.1f}{a['man_creep']:>10.1f}"
              f"{a['eng_hwy']:>9.1f}{a['man_hwy']:>9.1f}{a['eng_corner']:>10.1f}"
              f"{a['eng_ho']:>8.1f}{a['man_ho']:>8.1f}{a['eng_ho_creep']:>11.1f}"
              f"{a['man_ho_creep']:>11.1f}")

    R.hdr("§1b  FIRMWARE GATE gp-0x6806 vs openpilot latActive -- where the cache carries it")
    for b, a in rows.items():
        if a["gate_n"]:
            print(f"  {b:<11} agreement {a['gate_agree'] * 100:8.3f}%  over {a['gate_n']:,} frames"
                  f"   gate-high {a['gate_hi']:7.1f} s")

    R.hdr("§1c  SPEED CENSUS per window, the mandatory matched-distribution check")
    store = R.records()
    print(f"{'build':<11}{'nwin':>7}{'nepi':>6}" + "".join(f"{n:>9}" for n in R.VBIN_NAMES))
    for b in BUILDS:
        if b not in store:
            continue
        rs = R.driving(store[b], b)
        e = [r for r in rs if r["eng"] == 1]
        cnt = [sum(1 for r in e if r["vb"] == i) for i in range(len(R.VBIN_NAMES))]
        ne = len({r["ep"] for r in e})
        print(f"{b:<11}{len(e):>7}{ne:>6}" + "".join(f"{c:>9}" for c in cnt) + "   (engaged)")
        m = [r for r in rs if r["eng"] == 0]
        cnt = [sum(1 for r in m if r["vb"] == i) for i in range(len(R.VBIN_NAMES))]
        nm = len({r["ep"] for r in m})
        print(f"{'':<11}{len(m):>7}{nm:>6}" + "".join(f"{c:>9}" for c in cnt) + "   (manual)")

    with open(OUT, "w") as fh:
        json.dump({k: {kk: (None if isinstance(vv, float) and not np.isfinite(vv) else vv)
                       for kk, vv in v.items()} for k, v in rows.items()}, fh, indent=1)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
