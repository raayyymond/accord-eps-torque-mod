#!/usr/bin/env python3
"""Task #5 -- the shared instrument for pricing each build's rate-lane dose AT the rateKey the
oscillation actually runs at.

🛑 NOTHING numeric is re-implemented here. The burst detector, the band envelope, the window
cutting, the episode grouping and the sample-rate estimator all come from `_grind2_lib`,
`_r31_common`, `_r47_lib`, `_r4f_lib` and `_r50_lib`. This file adds exactly two things:

  1. `ratekey(rate_c, scale)` -- the bus -> gp-0x6ac0 map, on BOTH open axis scales.
     `rate_c` in the caches is `-raw(0x14A[2:4])`, i.e. RAW COUNTS with a sign flip.
         SCALE_A  gp-0x6ac0 = |raw 0x14A| * 2**18/(48*1159) = |rate_c| * 4.7121081
         SCALE_B  gp-0x6ac0 = |raw 0x14A| * 2**15/(48*1159) = |rate_c| * 0.5890135
     They differ by exactly 8x and the tie is [OPEN] in the record. Every result is reported twice.

  2. `Lane` -- the r24 rate-lane gain of ONE build, byte-read from its own image and evaluated
     per sample at (vehicle-speed counts, rateKey). Mirrors FUN_0003aa2c 0x3AB9C-0x3AC20 and
     FUN_0003ad74 exactly; validated against `studies/sessions/t5/_t5_gain_check.py` and `studies/sessions/v70/v70_rate_lane_gain_model.py`.

The point of the pair is the "delivered multiplier": for each 10 ms sample inside a grind burst,
what factor did THAT BUILD apply to the rate lane at that sample's own (speed, rate)? A dose priced
at a nominal rateKey is not the dose the oscillation received.
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
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

FW = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")

# ---------------------------------------------------------------- the axis scale -----------------
SCALE_A = 2 ** 18 / (48 * 1159)          # 4.7121081  -- the repo's live assumption [BELIEF]
SCALE_B = 2 ** 15 / (48 * 1159)          # 0.5890135  -- the chain-direct alternative [BELIEF]
SCALES = (("A 4.7121 c/deg-s", SCALE_A), ("B 0.5890 c/deg-s", SCALE_B))
KMH_CTS = 64.0625                        # gp-0x6a5e counts per km/h
MS_TO_KMH = 3.6


def ratekey(rate_c, scale):
    """gp-0x6ac0 counts from the cached `rate_c` channel (raw 0x14A counts, sign-flipped)."""
    return np.abs(np.asarray(rate_c, float)) * scale


def speed_counts(v_ms):
    """gp-0x6a5e counts from openpilot vEgo (m/s). ⚠ vEgo is openpilot's vote, not the EPS's."""
    return np.abs(np.asarray(v_ms, float)) * MS_TO_KMH * KMH_CTS


# ---------------------------------------------------------------- the lane ------------------------
TP = 0xBF000
SAR_R24, SAR_R26 = 0x3AC20, 0x3AB76
GATE_BYTE = 0x3AA96
ARM1, ARM2, ARM3 = TP + 0x7442, TP + 0x7446, TP + 0x7440
CNT = TP + 0x74FA
CROSS = TP + 0x7010
PTRS = (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214)
MODE = 10

IMG = {"stock": FW / "stock_fw_dump" / "code.bin"}
for _v in ("v58", "v59", "v61", "v62", "v64", "v65", "v66", "v67", "v68", "v69", "v70"):
    IMG[_v] = FW / f"_{_v}_plain_image.bin"


class Lane:
    """One build's r24 rate-lane gain surface, byte-read LE from its own image."""

    def __init__(self, name):
        self.name = name
        b = self.buf = IMG[name].read_bytes()
        hw = struct.unpack_from("<H", b, SAR_R24)[0]
        assert hw in (0x42AA, 0x42A9), f"{name}: sar hw 0x{hw:04X}"
        self.sar24 = 10 if hw == 0x42AA else 9
        hw26 = struct.unpack_from("<H", b, SAR_R26)[0]
        self.sar26 = 10 if hw26 == 0x42AA else (9 if hw26 == 0x42A9 else None)
        self.gate_live = b[GATE_BYTE] == 0xFB
        self.arm = [struct.unpack_from("<H", b, a)[0] for a in (ARM1, ARM2, ARM3)]
        self.cthr = b[CNT]
        self.cross = np.array(struct.unpack_from("<4h", b, CROSS), np.int64)
        recs = [struct.unpack_from("<I", b, p + 4 * MODE)[0] for p in PTRS]
        self.X = np.array([struct.unpack_from("<4h", b, r + 2) for r in recs], np.int64)
        self.Y = np.array([struct.unpack_from("<4h", b, r + 0x0A) for r in recs], np.int64)

    # --- FUN_0003ad74: cross-interpolate the four mode records in VEHICLE SPEED, vectorised -------
    def _ram(self, sc):
        sc = np.asarray(sc, np.int64)
        k = np.zeros(len(sc), np.int64)
        for j in range(4):
            k += (self.cross[j] <= sc).astype(np.int64)
        Xr = np.empty((len(sc), 4), np.int64)
        Yr = np.empty((len(sc), 4), np.int64)
        lo_m, hi_m = k == 0, k > 3
        Xr[lo_m], Yr[lo_m] = self.X[0], self.Y[0]
        Xr[hi_m], Yr[hi_m] = self.X[3], self.Y[3]
        mid = ~(lo_m | hi_m)
        if mid.any():
            km = k[mid]
            n = sc[mid] - self.cross[km - 1]
            d = self.cross[km] - self.cross[km - 1]
            for i in range(4):
                dx = self.X[km, i] - self.X[km - 1, i]
                dy = self.Y[km, i] - self.Y[km - 1, i]
                Xr[mid, i] = self.X[km - 1, i] + _tdiv(dx * n, d)
                Yr[mid, i] = self.Y[km - 1, i] + _tdiv(dy * n, d)
        return Xr, Yr

    # --- FUN_0003aa2c 0x3AB9C-0x3ABFA: 4-knot piecewise linear on the rate axis, vectorised -------
    def gain(self, sc, rk, engaged):
        """Q10 gain applied to the rate lane, per sample. `engaged` selects the LKAS arm."""
        sc = np.asarray(sc, np.int64)
        rk = np.asarray(rk, np.int64)
        idx = np.where(rk >= 13001, 0, rk)                     # 0x3AAC8 fold -> index 0
        X, Y = self._ram(sc)
        out = Y[:, 3].copy()
        out = np.where(idx <= X[:, 0], Y[:, 0], out)
        for k in range(3):
            m = (idx > X[:, k]) & (idx < X[:, k + 1]) & (idx < X[:, 3])
            if m.any():
                num = (Y[m, k + 1] - Y[m, k]) * (idx[m] - X[m, k])
                den = X[m, k + 1] - X[m, k]
                out[m] = Y[m, k] + _tdiv(num, den)
        out = np.where(idx >= X[:, 3], Y[:, 3], out)
        if self.gate_live:
            eng = np.asarray(engaged, bool)
            out = np.where(eng, self.arm[1], out)               # 0xC6446 arm, V67/V68 only
        return out

    def slope(self, sc, rk, engaged):
        """d(lane out)/d(dt input) -- gain >> sar, the physically delivered multiplier's numerator."""
        return self.gain(sc, rk, engaged) / (1 << self.sar24)


def _tdiv(n, d):
    """C/V850 integer division: truncate toward zero."""
    q = np.abs(n) // np.abs(d)
    return np.where((n < 0) != (d < 0), -q, q)


_LANES = {}


def lane(name):
    if name not in _LANES:
        _LANES[name] = Lane(name)
    return _LANES[name]


def delivered(build_img, sc, rk, engaged):
    """Per-sample delivered multiplier vs STOCK's own r24 lane at the SAME (speed, rate)."""
    a = lane(build_img).slope(sc, rk, engaged)
    b = lane("stock").slope(sc, rk, engaged)
    return a / b


# ---------------------------------------------------------------- the corpus ---------------------
# build tag -> (cache dir, prefix, segments, image name, nominal-creep label)
# Segment lists and cache prefixes are taken from `_grind2_lib.BUILDS` / `_r4f_lib` / `_r50_lib`
# so this cannot drift from the instrument that produced the recorded ladder.
def corpus():
    import _grind2_lib as G
    import _r50_lib  # noqa: F401  -- registers V68/r4e, V69/r4f and V70/r50 into G.BUILDS
    img = {"V61/r31": "v61", "V59/r2c": "v59", "V64/r35": "v64", "V58/r2b": "v58",
           "V62/r37": "v62", "V65/r3a": "v65", "V65/r3b": "v65", "V67/r47": "v67",
           "V68/r4e": "v68", "V69/r4f": "v69", "V70/r50": "v70"}
    out = {}
    for k, v in img.items():
        if k in G.BUILDS:
            out[k] = dict(G.BUILDS[k], img=v)
    return out
