#!/usr/bin/env python3
"""Task #5 -- build the PER-SAMPLE dataset the rateKey question needs, once, and cache it.

For every build in the corpus, every 10 ms frame inside a contiguous run of the ENGAGEMENT mask
(and the disengaged complement, for the control) is tagged with:

    env18  the 18-22 Hz analytic band envelope of `tq`  (grind #1)   -- _r31_common.band_envelope
    env40  the 40-49 Hz envelope                         (grind #2)
    env24  the 24-28 Hz envelope   -- the record's PRE-DECLARED NEGATIVE CONTROL band
    rate   |rate_c| = |raw 0x14A[2:4]|  -- the rateKey numerator, RAW COUNTS
    v      |cs_v|, m/s
    eff    sustained |lowpass(tq, 3 Hz)| -- the driver's own push, oscillation removed
    eng    engagement (carControl.latActive)
    ep     episode id = (build, seg, run) -- the resampling unit

🛑 The envelope is computed over the whole contiguous RUN, exactly as `_r37_ratchet_lib.windows`
does it, never over a spliced concatenation, and `fs` is `_r4f_lib.fs_lattice` for EVERY build.

Usage:  python studies/sessions/t5/_t5_samples.py            # build/refresh the cache
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
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G          # noqa: E402
import _r31_common as C          # noqa: E402
import _r4f_lib as R4F           # noqa: E402
import _r50_lib as R50           # noqa: E402  -- registers V68/r4e, V69/r4f, V70/r50
import _t5_ratekey_lib as T      # noqa: E402

PKL = ROOT / "_scratch/data/_cache_t5_samples.pkl"
NFFT = G.NFFT                    # 256 -- runs shorter than this are not analysable, same as the record


def build_one(tag, B):
    R4F.install_fs()
    out = []
    for s in B["segs"]:
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, B["cache"], B["pfx"])
        fs = G.fs_of(d)
        le = np.asarray(d["cc_lat"], float) > 0.5
        for eng, mask in ((1, le), (0, ~le)):
            for a, b in C.runs_of(mask, d["t"], NFFT):
                x = np.asarray(d["tq"][a:b], float)
                if not np.all(np.isfinite(x)):
                    continue
                rec = dict(
                    build=tag, seg=int(s), eng=eng, fs=float(fs), a=int(a), b=int(b),
                    t=np.asarray(d["t"][a:b], float),
                    env18=C.band_envelope(x, fs, 18.0, 22.0),
                    env40=C.band_envelope(x, fs, 40.0, 49.0),
                    env24=C.band_envelope(x, fs, 24.0, 28.0),
                    rate=np.abs(np.asarray(d["rate_c"][a:b], float)),
                    v=np.abs(np.asarray(d["cs_v"][a:b], float)),
                    eff=np.asarray(C.sustained(d["tq"][a:b], fs), float),
                    ang=np.abs(np.asarray(d["ang"][a:b], float)),
                    tq=x,
                )
                out.append(rec)
    return out


def load(rebuild=False):
    if PKL.exists() and not rebuild:
        with open(PKL, "rb") as fh:
            return pickle.load(fh)
    corp = T.corpus()
    store = {}
    for tag, B in corp.items():
        store[tag] = build_one(tag, B)
        n = sum(len(r["t"]) for r in store[tag])
        ne = sum(len(r["t"]) for r in store[tag] if r["eng"])
        print(f"  {tag:10s} runs={len(store[tag]):4d}  samples={n:7d}  engaged={ne:7d}", flush=True)
    with open(PKL, "wb") as fh:
        pickle.dump(store, fh)
    return store


if __name__ == "__main__":
    load(rebuild="--rebuild" in sys.argv)
