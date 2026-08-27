#!/usr/bin/env python3
"""Extract the V57 gp-0x6806 gate probe from routes 28 and 29 into repo-root caches.

Same grid/decode conventions as decode/extract_r29_cache.py: CAN 0x14A src1 arrivals are the sampling
grid (100 Hz), 0x18F is held-last onto it, 0x0E4 comes from src 129 (sendcan).

V57 byte4 packing (rlog-tools/probe/decode_v57_deadband.py):
    bit7 = 1                    LIVENESS (field==0 => cave did not fire => VOID)
    bit6 = (gp-0x6806 == 0)     <-- THE GATE BIT
    bit5 = (gp-0x69b0 != 0)
    bit4 = (gp-0x6b30 == 0)
    bit3 = (gp-0x6b30 <  0)
    bits 2:0 = stock STEER_SENSOR_STATUS (never written by fw; reads 0)

Usage:  python decode/extract_v57_gate_cache.py
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

sys.path.insert(0, str(Path(__file__).parents[1]))
from rlog_parse import read_messages  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"

ROUTES = {
    "r28": ("75604b0a432fdc89_00000028--66ab5a2233", ["10", "11", "12", "13", "14"]),
    "r29": ("75604b0a432fdc89_00000029--47bc9c9d99", ["0", "1"]),
}


def i16be(b, o):
    v = (b[o] << 8) | b[o + 1]
    return v - 0x10000 if v & 0x8000 else v


def extract(path, tag, outdir):
    rows, e4hist = [], []
    last18, lastE4 = None, (0.0, 0)
    cs = {"t": [], "v": [], "eng": [], "ang": [], "tq": [], "press": []}
    cc = {"t": [], "lat": [], "en": [], "req": []}

    for evt in read_messages(path):
        try:
            w = evt.which()
        except Exception:
            continue
        tm = evt.logMonoTime * 1e-9
        if w == "can":
            for m in evt.can:
                src, addr = int(m.src), int(m.address)
                d = bytes(m.dat)
                if src == 1 and addr == 0x18F and len(d) >= 5:
                    last18 = (i16be(d, 0) * -1.0, i16be(d, 2) * -0.1,
                              (d[4] >> 3) & 1, (d[4] >> 4) & 0x0F, d[4] & 0x07)
                elif src == 129 and addr == 0x0E4 and len(d) >= 3:
                    lastE4 = (float(i16be(d, 0)), (d[2] >> 7) & 1)
                    e4hist.append((tm, lastE4[0], lastE4[1], d[2]))
                elif src == 1 and addr == 0x14A and len(d) >= 7:
                    if last18 is None:
                        continue
                    rows.append((tm, i16be(d, 0) * -0.1, i16be(d, 2) * -1.0,
                                 i16be(d, 5) * -0.1, d[4],
                                 last18[0], last18[1], last18[2], last18[3], last18[4],
                                 lastE4[0], lastE4[1]))
        elif w == "carState":
            c = evt.carState
            cs["t"].append(tm); cs["v"].append(c.vEgo)
            cs["eng"].append(float(bool(c.cruiseState.enabled)))
            cs["ang"].append(c.steeringAngleDeg)
            cs["tq"].append(c.steeringTorque)
            try:
                cs["press"].append(float(bool(c.steeringPressed)))
            except Exception:
                cs["press"].append(0.0)
        elif w == "carControl":
            cc["t"].append(tm); cc["lat"].append(float(bool(evt.carControl.latActive)))
            cc["en"].append(float(bool(evt.carControl.enabled)))
            try:
                cc["req"].append(float(evt.carControl.actuators.torque))
            except Exception:
                cc["req"].append(np.nan)

    a = np.array(rows, dtype=float)
    names = ["t", "ang", "rate_c", "wang", "probe", "tq", "rate_f", "sca", "sstat", "slow3",
             "e4tq", "e4req"]
    d = {n: a[:, i].copy() for i, n in enumerate(names)}
    t0 = d["t"][0]
    d["t"] = d["t"] - t0
    cst = np.array(cs["t"]) - t0
    for k in ("v", "eng", "ang", "tq", "press"):
        d["cs_" + k] = np.interp(d["t"], cst, np.array(cs[k]))
    cct = np.array(cc["t"]) - t0
    for k in ("lat", "en", "req"):
        d["cc_" + k] = np.interp(d["t"], cct, np.array(cc[k]))
    e4 = np.array(e4hist, dtype=float)
    if len(e4):
        e4[:, 0] -= t0
    np.savez_compressed(outdir / f"{tag}.npz", **d, e4hist=e4)
    fs = 1.0 / np.median(np.diff(d["t"]))
    print(f"{tag}: {len(a)} samples  0..{d['t'][-1]:.1f}s  fs={fs:.2f}  "
          f"lat {100*np.mean(d['cc_lat']>0.5):.1f}%  sca {100*np.mean(d['sca']==1):.1f}%  "
          f"vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f}")
    return d


if __name__ == "__main__":
    for rt, (route, segs) in ROUTES.items():
        outdir = ROOT / f"_cache_{rt}"
        outdir.mkdir(exist_ok=True)
        for s in segs:
            p = RLOGDIR / f"{route}--{s}--rlog.zst"
            if not p.exists():
                print(f"MISSING {p}")
                continue
            extract(p, f"{rt}s{s}", outdir)
