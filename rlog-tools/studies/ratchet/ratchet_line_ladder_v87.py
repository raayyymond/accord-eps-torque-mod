#!/usr/bin/env python3
"""PART 4 of the symptom<->band<->build ladder: the ~7.79 Hz RATCHET LINE across V81/V83a/V84/V85.

🛑 THE INSTRUMENT IS THE CORPUS'S, NOT A NEW ONE.  Windowing, spectra, prominence and the episode
bootstrap are `relay_fingerprint_r6e`'s, imported verbatim.  This file adds ONE route (V83a/r68,
which the fingerprint never ran) and ONE statistic the fingerprint printed without a CI (the
per-build CENTRE FREQUENCY).  Nothing numeric is redefined.

Resampling unit is `blk` (~10 s block), the corpus's `EPKEY` for every band ratio already reported.
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod")
# repo reorg 2026-08-26 moved rlog_parse into rlog-tools/lib/ -- the old single-dir insert
# stopped resolving it, which killed this whole extractor family silently (the caches were
# already on disk, so nothing surfaced it). Put the kit root AND every code subfolder on.
for _p in [ROOT / "rlog-tools"] + [d for d in (ROOT / "rlog-tools").iterdir() if d.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import relay_fingerprint_r6e as RF  # noqa: E402

MACRO = RF.MACRO          # 7.79 Hz, the recorded line
CIRC = RF.CIRC            # 2.0805 m
RNG = np.random.default_rng(87_7790)

# route table -- V83a's cache/prefix/parked taken from score/score_v84_r6d.py's registry
ROUTES = [("V81/r67",  "_scratch/cache/r67x", "r67xs", [s for s in range(13) if s != 13]),
          ("V83a/r68", "_scratch/cache/r68x", "r68xs", [s for s in range(8) if s not in (0, 7)]),
          ("V84/r6d",  "_scratch/cache/r6d",  "r6ds",  list(range(11))),
          ("V85/r6e",  "_scratch/cache/r6e",  "r6es",  list(range(7)))]

OUT = {}


def boot_slope(fv, vv, units, nboot=2000):
    """OLS slope of f_free on speed, block-bootstrapped over `units`."""
    fv, vv, units = np.asarray(fv, float), np.asarray(vv, float), np.asarray(units)
    ok = np.isfinite(fv) & np.isfinite(vv)
    fv, vv, units = fv[ok], vv[ok], units[ok]
    if len(fv) < 6:
        return np.nan, np.nan, np.nan
    groups = {}
    for i, u in enumerate(units):
        groups.setdefault(u, []).append(i)
    keys = list(groups)
    full = np.polyfit(vv, fv, 1)[0]
    draws = []
    for _ in range(nboot):
        idx = np.concatenate([groups[keys[i]] for i in RNG.integers(0, len(keys), len(keys))])
        if len(set(vv[idx])) < 3:
            continue
        draws.append(np.polyfit(vv[idx], fv[idx], 1)[0])
    if len(draws) < 50:
        return float(full), np.nan, np.nan
    return float(full), float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def load(route, cache, pfx, segs, engaged):
    W = RF.windows(route, cache, pfx, segs, engaged=engaged)
    W = RF.spectra(W)
    from scipy.signal import butter, filtfilt, hilbert
    for r in W:
        b = butter(2, [MACRO - 1.0, MACRO + 1.0], btype="band", fs=r["fs"])
        r["a779"] = float(np.percentile(np.abs(hilbert(filtfilt(*b, r["x"]))), 99))
        r["p779"] = RF.prom_at(r, MACRO, half=0.5)      # 🛑 T3's half-width, not prom_at's default
    return W


def main():
    RF.hdr("PART 4  THE ~7.79 Hz RATCHET LINE, four builds.  ENGAGED arm.\n"
           "    f_c   = median free 5-12 Hz prominence argmax, block-bootstrap CI\n"
           "    prom  = prominence at the FIXED 7.79 Hz line over the local floor\n"
           "    a779  = ABSOLUTE p99 envelope amplitude in 7.79+-1 Hz, counts\n"
           "    slope = OLS d(f_c)/d(speed); wheel order 2 predicts +0.961, a fixed line 0.000")
    per = {}
    for route, cache, pfx, segs in ROUTES:
        e = load(route, cache, pfx, segs, True)
        m = load(route, cache, pfx, segs, False)
        per[route] = (e, m)
        print(f"  {route:10s} engaged {len(e):4d} windows / {len({r['blk'] for r in e}):3d} blk"
              f"   manual {len(m):4d} / {len({r['blk'] for r in m}):3d} blk", flush=True)

    print(f"\n{'build':10s} {'n':>4s} {'blk':>4s} | {'centre f_c (Hz), 95% CI':>28s} | "
          f"{'prominence at 7.79 Hz':>26s} | {'a779 (counts)':>26s}")
    for route, _, _, _ in ROUTES:
        e = [r for r in per[route][0] if np.isfinite(r["f_free"])]
        u = [r["blk"] for r in e]
        fc = RF._boot_med([r["f_free"] for r in e], u)
        pr = RF._boot_med([r["p779"] for r in e], u)
        aa = RF._boot_med([r["a779"] for r in e], u)
        print(f"{route:10s} {len(e):4d} {len(set(u)):4d} | "
              f"{fc[0]:8.3f} [{fc[1]:7.3f},{fc[2]:7.3f}] | "
              f"{pr[0]:8.2f} [{pr[1]:7.2f},{pr[2]:7.2f}] | "
              f"{aa[0]:8.1f} [{aa[1]:7.1f},{aa[2]:7.1f}]")
        OUT.setdefault(route, {}).update(n=len(e), blk=len(set(u)), f_c=list(fc),
                                         prom779=list(pr), a779=list(aa))

    print(f"\n{'build':10s} | {'slope Hz per m/s, 95% CI':>30s} | "
          f"{'frac argmax within 0.6 Hz of 7.79':>34s}")
    for route, _, _, _ in ROUTES:
        e = [r for r in per[route][0] if np.isfinite(r["f_free"])]
        sl = boot_slope([r["f_free"] for r in e], [r["v"] for r in e], [r["blk"] for r in e])
        fr = float(np.mean([abs(r["f_free"] - MACRO) <= 0.6 for r in e]))
        print(f"{route:10s} | {sl[0]:+9.4f} [{sl[1]:+8.4f},{sl[2]:+8.4f}] | {100*fr:32.1f}%")
        OUT[route].update(slope=list(sl), frac_at_line=fr)

    print(f"\n{'build':10s} {'nE':>4s} {'nM':>4s} | {'a779 ENG':>22s} | {'a779 MAN':>22s} | "
          f"{'ENG/MAN':>8s}")
    for route, _, _, _ in ROUTES:
        e, m = per[route]
        u_e, u_m = [r["blk"] for r in e], [r["blk"] for r in m]
        ae = RF._boot_med([r["a779"] for r in e], u_e)
        am = RF._boot_med([r["a779"] for r in m], u_m)
        rat = ae[0] / am[0] if (np.isfinite(am[0]) and am[0] > 0) else np.nan
        print(f"{route:10s} {len(e):4d} {len(m):4d} | {ae[0]:7.1f} [{ae[1]:6.1f},{ae[2]:6.1f}] | "
              f"{am[0]:7.1f} [{am[1]:6.1f},{am[2]:6.1f}] | {rat:8.2f}")
        OUT[route].update(a779_eng=list(ae), a779_man=list(am), eng_man=float(rat),
                          nE=len(e), nM=len(m))

    print("\n  🛑 MANUAL ARMS ARE TINY (9-14 windows on three of four routes).  The ENG/MAN column\n"
          "     is a POINT ESTIMATE ONLY -- do not score a build on it.")

    (ROOT / "_scratch/cache/r6e" / "_v87_ratchet_line_ladder.json").write_text(
        json.dumps({k: {kk: (list(map(float, vv)) if isinstance(vv, list) else vv)
                        for kk, vv in v.items()} for k, v in OUT.items()}, indent=1))
    print(f"\nwrote {ROOT / '_scratch/cache/r6e' / '_v87_ratchet_line_ladder.json'}")


if __name__ == "__main__":
    main()
