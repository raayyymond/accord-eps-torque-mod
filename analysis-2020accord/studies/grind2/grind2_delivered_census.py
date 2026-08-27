#!/usr/bin/env python3
"""THE GRIND-#2 CENSUS RE-CUT ON **DELIVERED** RATE-LANE MULTIPLIERS -- one instrument, every build.

WHY. `docs/STATE.md` carries a two-lane rule ("creep grind #2 needs r24 >= 3.4x AND r26 >= 1.5x")
tabulated on NOMINAL multipliers, and a retraction on the same page reading "every non-V62 build reads
0.0". This file rebuilds both on ONE instrument and on the multipliers each image ACTUALLY delivered
on a mode-24/26 car (`_grind2_delivered_lib`).

🛑 ONE INSTRUMENT, NO EXCEPTIONS. `r47_orchestrator_checks._windows` UNCHANGED -- 2.56 s window, 50%
overlap, butter+hilbert 40-49 Hz envelope, p99, **500-count burst threshold**. This is the estimator
that produced every burst count already on record (`studies/sessions/r58/r58_grind2.py`, `studies/sessions/r59/d4_r59_grind2.py`). The tapered
`_grind2_lib.win_env` is NOT substituted: they differ by 1.4-1.9x and cross-comparing them is a
recorded error in this kit.

WHAT IS NEW HERE vs `studies/sessions/r59/d4_r59_grind2.py`:
  * V73 (`r5a`) and V74 (`r5d`) added -- 2 more builds in the r26-cut cell, which is V76's cell.
  * builds are grouped by their DELIVERED (r24, r26) pair, not by a nominal `kd` label.
  * bursts are counted per EPISODE as well as per window, so a single 10 s event cannot read as 3.
  * a per-window SPEED CENSUS of every burst window (tyre orders 1/2/3 are speed-locked bands).
  * a split-half null on the burst RATE inside the one pool that has enough bursts to support one.
  * the power calculation for V76's cell, stated as an MDE.

Usage:  python studies/grind2/grind2_delivered_census.py
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
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import poisson

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import r47_orchestrator_checks as R47  # noqa: E402
import _grind2_delivered_lib as D  # noqa: E402

BURST = 500.0          # counts, 40-49 Hz envelope p99 -- the kit's standing threshold
BAND = "40-49"
CREEP = (0.3, 4.0)     # m/s
HWY = 14.0
WIN_S = R47.WIN_S if hasattr(R47, "WIN_S") else 2.56

# route -> (build, cache). One cache per flown build; V65 flew two routes on one image.
ROUTES = [
    ("V61",  "r31",  ["_scratch/cache/r31"]),
    ("V58",  "r2b",  ["_scratch/cache/r2b"]),
    ("V59",  "r2c",  ["_scratch/cache/r2c"]),
    ("V64",  "r35",  ["_scratch/cache/r35"]),
    ("V62",  "r37",  ["_scratch/cache/r37"]),
    ("V65",  "r3ab", ["_scratch/cache/r3a", "_scratch/cache/r3b"]),
    ("V67",  "r47",  ["_scratch/cache/r47"]),
    ("V68",  "r4e",  ["_scratch/cache/v68"]),
    ("V69",  "r4f",  ["_scratch/cache/r4f"]),
    ("V70",  "r50",  ["_scratch/cache/r50"]),
    ("V71B", "r54",  ["_scratch/cache/r54"]),
    ("V71C", "r58",  ["_scratch/cache/r58"]),
    ("V72",  "r59",  ["_scratch/cache/r59"]),
    ("V73",  "r5a",  ["_scratch/cache/r5a"]),
    ("V74",  "r5d",  ["_scratch/cache/r5d"]),
]
# The operating point the table is quoted at: 0 km/h, rateKey 3000 -- the same point STATE.md's
# existing V67/V68 (3.414, 0.250) and V71C (3.414, 1.500) cells were computed at, so the rebuilt
# numbers are directly comparable to the ones on record.
OP_KMH, OP_RK = 0, 3000
OUT = {}


def hdr(s):
    print("\n" + "=" * 122 + f"\n{s}\n" + "=" * 122)


# ============================================================ delivered multipliers ===============
B = D.load_all()
st = B["stock"]
DEL = {}
for name, route, _ in ROUTES:
    DEL[name] = dict(
        eng=D.delivered(B[name], st, OP_KMH, OP_RK, engaged=True),
        man=D.delivered(B[name], st, OP_KMH, OP_RK, engaged=False),
    )
DEL["V76"] = dict(eng=D.delivered(B["V76"], st, OP_KMH, OP_RK, engaged=True),
                  man=D.delivered(B["V76"], st, OP_KMH, OP_RK, engaged=False))

# ============================================================ window harvest ======================
print("harvesting windows ...", flush=True)
ROWS = {}
for name, route, caches in ROUTES:
    rows = []
    for c in caches:
        rows += R47._windows(c, name, lambda v: True)
    ROWS[name] = rows
    print(f"   {name:5s} {route:5s} {len(rows):6d} windows", flush=True)


def cell(rows, arm, vlo=None, vhi=None, ratemin=None, angmin=None):
    """arm: 'eng' (lat>0.5) / 'man' (lat<0.5). Windows are binned by their OWN covariates."""
    out = []
    for r in rows:
        if arm == "eng" and r["lat"] <= 0.5:
            continue
        if arm == "man" and r["lat"] >= 0.5:
            continue
        if vlo is not None and not (vlo <= r["v"] < (vhi if vhi is not None else 1e9)):
            continue
        # 🛑 `ratemax` is column deg/s; the rate-lane index `gp-0x6ac0` is COUNTS. The kit's scale is
        # 4.7121 counts per column deg/s (settled three ways). Comparing raw `ratemax` against the
        # design's 1400-count breakpoint under-selects by 4.7x and empties the cell.
        if ratemin is not None and r["ratemax"] * 4.7121 < ratemin:
            continue
        if angmin is not None and r["ang"] < angmin:
            continue
        out.append(r)
    return out


def stat(rows):
    n = len(rows)
    secs = n * WIN_S / 2.0                      # 50% overlap
    b = [r for r in rows if r[BAND] > BURST]
    eps = len({r["ep"] for r in b})
    mx = max((r[BAND] for r in rows), default=float("nan"))
    return dict(n=n, secs=secs, bursts=len(b), burst_eps=eps, mx=mx,
                rate=len(b) / secs if secs else float("nan"), rows=b)


CELLS = [
    ("creep 0.3-4 m/s", dict(vlo=CREEP[0], vhi=CREEP[1])),
    ("creep & HIGH RATE (ratemax>=1400)", dict(vlo=CREEP[0], vhi=CREEP[1], ratemin=1400)),
    ("creep & corner |ang|>=100", dict(vlo=CREEP[0], vhi=CREEP[1], angmin=100)),
    ("NON-HIGHWAY 0.3-14 m/s", dict(vlo=0.3, vhi=HWY)),
    ("highway >=14 m/s", dict(vlo=HWY)),
    ("ALL moving >=0.3 m/s", dict(vlo=0.3)),
]

# ============================================================ §1 ==================================
hdr("§1  THE TWO-LANE TABLE, REBUILT ON DELIVERED MULTIPLIERS.\n"
    f"    Delivered = what the image computes at {OP_KMH} km/h, rateKey {OP_RK}, ENGAGED (mode 26) vs "
    f"STOCK at the same point.\n"
    "    ⚠ `nominal` is what docs/STATE.md tabulates. Burst = 40-49 Hz envelope p99 > 500 counts.")
NOMINAL = {"stock": (1.000, 1.000), "V69": (1.000, 1.000), "V70": (1.000, 1.000),
           "V71B": (1.000, 2.000), "V62": (3.414, 2.000), "V65": (3.414, 2.000),
           "V71C": (3.414, 1.500), "V67": (3.414, 0.250), "V68": (3.414, 0.250),
           "V72": (3.414, 0.250)}
print(f"   {'build':6s} {'route':6s} {'DELIVERED eng':>16s} {'DELIVERED man':>16s} {'NOMINAL':>16s}  "
      f"{'creep eng: bursts/secs':>24s} {'creep man: bursts/secs':>24s}   max eng")
for name, route, _ in ROUTES:
    e, m = DEL[name]["eng"], DEL[name]["man"]
    ce = stat(cell(ROWS[name], "eng", **CELLS[0][1]))
    cm = stat(cell(ROWS[name], "man", **CELLS[0][1]))
    nom = NOMINAL.get(name)
    ns = f"{nom[0]:6.3f}/{nom[1]:6.3f}" if nom else f"{'-':>13s}"
    flag = "  ← WRONG on r24" if nom and abs(nom[0] - e[0]) > 0.01 else ""
    print(f"   {name:6s} {route:6s} {e[0]:7.3f}/{e[1]:7.3f} {m[0]:7.3f}/{m[1]:7.3f} {ns:>16s}  "
          f"{ce['bursts']:6d} / {ce['secs']:8.1f} s {cm['bursts']:12d} / {cm['secs']:8.1f} s   "
          f"{ce['mx']:8.1f}{flag}")
e76 = DEL["V76"]["eng"]
print(f"   {'V76':6s} {'(none)':6s} {e76[0]:7.3f}/{e76[1]:7.3f} {'  1.000/  1.000':>15s} "
      f"{'-':>16s}  {'UNFLOWN -- byte-identical rate lane to V67/V68':>50s}")

# ============================================================ §2 ==================================
hdr("§2  EVERY CELL, EVERY BUILD -- exposure in seconds, burst windows, and burst EPISODES.\n"
    "    `eps` = distinct ~10 s episode blocks containing a burst. 3 windows in 1 episode is ONE "
    "event, not three.")
for cname, kw in CELLS:
    print(f"\n   --- {cname} ---")
    print(f"   {'build':6s} {'del eng r24/r26':>16s} | {'ENG n':>6s} {'secs':>8s} {'burst':>6s} "
          f"{'eps':>4s} {'max':>9s} | {'MAN n':>6s} {'secs':>8s} {'burst':>6s} {'eps':>4s} {'max':>9s}")
    for name, route, _ in ROUTES:
        e = DEL[name]["eng"]
        a = stat(cell(ROWS[name], "eng", **kw))
        b = stat(cell(ROWS[name], "man", **kw))
        print(f"   {name:6s} {e[0]:7.3f}/{e[1]:7.3f} | {a['n']:6d} {a['secs']:8.1f} "
              f"{a['bursts']:6d} {a['burst_eps']:4d} {a['mx']:9.1f} | {b['n']:6d} {b['secs']:8.1f} "
              f"{b['bursts']:6d} {b['burst_eps']:4d} {b['mx']:9.1f}")

# ============================================================ §3 ==================================
hdr("§3  WHERE EVERY BURST IN THE CORPUS ACTUALLY IS -- speed census, one row per burst WINDOW.\n"
    "    Tyre order 1 is in-band at 12.5-18.7 m/s, order 2 at 6.2-9.4, order 3 at 4.2-6.2 (40-49 Hz)."
    "\n    A burst inside one of those speed windows could be a wheel order rather than the lane.")
print(f"   {'build':6s} {'arm':4s} {'v m/s':>7s} {'|ang|':>7s} {'ratemax':>8s} {'p99 40-49':>10s} "
      f"{'episode':>28s}   order-1?  order-2?  order-3?")
allburst = []
for name, route, _ in ROUTES:
    for arm in ("eng", "man"):
        for r in stat(cell(ROWS[name], arm, vlo=0.3))["rows"]:
            o1 = "IN" if 12.5 <= r["v"] <= 18.7 else "-"
            o2 = "IN" if 6.2 <= r["v"] <= 9.4 else "-"
            o3 = "IN" if 4.2 <= r["v"] <= 6.2 else "-"
            ep = f"{Path(r['ep'][0]).stem}#{r['ep'][1]}"
            print(f"   {name:6s} {arm:4s} {r['v']:7.2f} {r['ang']:7.1f} {r['ratemax']:8.0f} "
                  f"{r[BAND]:10.1f} {ep:>28s}   {o1:>8s}  {o2:>8s}  {o3:>8s}")
            allburst.append(dict(build=name, arm=arm, v=r["v"], ang=r["ang"],
                                 ratemax=r["ratemax"], p99=r[BAND], ep=ep))
print(f"\n   TOTAL burst windows corpus-wide (>=0.3 m/s, both arms): {len(allburst)}")
print(f"   distinct episodes                                       : "
      f"{len({(b['build'], b['ep']) for b in allburst})}")

OUT["bursts"] = allburst
OUT["delivered"] = {k: dict(eng=list(v["eng"]), man=list(v["man"])) for k, v in DEL.items()}
(HERE / "_scratch/out/_grind2_delivered_census.json").write_text(json.dumps(OUT, indent=1), encoding="utf-8")
print(f"\nwrote {HERE / '_scratch/out/_grind2_delivered_census.json'}")
