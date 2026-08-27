#!/usr/bin/env python3
"""Extract route `6d` (V84) and route `68` (V83a) into the corpus's OWN cache schema.

🛑 WHY THIS FILE EXISTS.  Route 68's scoring code and cache lived in a session scratchpad and were
lost -- logged as record defect 9.2 in `docs/handoffs/2026-08/HANDOFF-2026-08-08-v83a-flew-and-r24-is-the-actor.md`.
Every route-68 number in that handoff is currently irreproducible.  This file, and
`score/score_v84_r6d.py` beside it, are the promotion of that work into `rlog-tools/`.

🛑 THE INSTRUMENT IS NOT REIMPLEMENTED.  `compare_v75_v76_v80_grind.extract66` / `.split66` are
called verbatim with their module-level cache/route globals rebound, so the per-segment `.npz`
schema, the field names, the IMU axis pick, the ZOH/interp convention and the `PASS_1D` list are
bit-for-bit the ones every prior route in this corpus was scored with.  Rebinding globals is ugly;
copying the extractor would be worse, because a copy drifts and a rebind cannot.

Usage:
    python decode/extract_r6d_r68.py            # both routes
    python decode/extract_r6d_r68.py r6d        # one route
"""
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
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import compare_v75_v76_v80_grind as M  # noqa: E402  -- THE instrument; never reimplemented

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"

ROUTES = {
    # tag        route stem                                  segs           cache dir       prefix
    "r6d":  dict(stem="75604b0a432fdc89_0000006d--5d03a5adb4", segs=list(range(12)),
                 cache=ROOT / "_scratch/cache/r6d",  pfx="r6ds",  build="V84"),
    "r68":  dict(stem="75604b0a432fdc89_00000068--0b7efae911", segs=list(range(8)),
                 cache=ROOT / "_scratch/cache/r68x", pfx="r68xs", build="V83a"),
}


def extract(tag):
    R = ROUTES[tag]
    paths = [RLOGDIR / f"{R['stem']}--{s}--rlog.zst" for s in R["segs"]]
    missing = [p.name for p in paths if not p.exists()]
    if missing:
        raise SystemExit(f"missing rlogs: {missing}")
    R["cache"].mkdir(parents=True, exist_ok=True)

    # --- rebind the instrument's route globals, run it, restore ------------------------------
    old = (M.CACHE66, M.PFX66, M.ROUTE66, M.SEGS66)
    M.CACHE66, M.PFX66, M.ROUTE66, M.SEGS66 = R["cache"], R["pfx"], R["stem"], R["segs"]
    try:
        print(f"=== {tag} / {R['build']}: {len(paths)} segments -> {R['cache']}", flush=True)
        M.extract66(paths)
        M.split66()
    finally:
        M.CACHE66, M.PFX66, M.ROUTE66, M.SEGS66 = old

    # `extract66` hard-codes the route-global file name; give it this route's name so the cache is
    # self-describing, and stamp the real build label over the extractor's literal "V80".
    for src, dst in ((f"{R['cache']}/r66.npz", f"{R['cache']}/{tag}.npz"),
                     (f"{R['cache']}/r66_events.json", f"{R['cache']}/{tag}_events.json"),
                     (f"{R['cache']}/r66_census_seg.json", f"{R['cache']}/{tag}_census_seg.json")):
        p, q = Path(src), Path(dst)
        if p.exists():
            if q.exists():
                q.unlink()
            p.rename(q)
    for s in R["segs"]:
        p = R["cache"] / f"{R['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = dict(np.load(p))
        d["probe_build"] = np.array([R["build"]])
        np.savez_compressed(p, **d)
    print(f"=== {tag} done: {sorted(x.name for x in R['cache'].glob(R['pfx'] + '*.npz'))}")


if __name__ == "__main__":
    tags = [a for a in sys.argv[1:] if a in ROUTES] or list(ROUTES)
    for t in tags:
        extract(t)
