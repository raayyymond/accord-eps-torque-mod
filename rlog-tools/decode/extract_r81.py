#!/usr/bin/env python3
r"""Extract route `81` -- THE V98 FLIGHT (the first COMPARATOR probe in the kit) -- into
`analysis-2020accord/_scratch/cache/r81/`.

🛑 THE INSTRUMENT IS NOT REIMPLEMENTED.  Like `decode/extract_r80.py`, this file only adds a row to
`decode_v84_probe_r6d.ROUTES` and calls `extract_r7d`'s `extract_route()` -- the SAME code that
wrote every cache since `_scratch/cache/r6d/`.  Field names, ZOH/interp convention, sentinel definition
and `PASS_1D` are bit-for-bit the ones every prior route was scored with.  The 0x1AB full tap,
the 0x14A byte-7 tap and the `row2raw14` off-by-one fix all come along unchanged, including the
elementwise byte-4 assertion that kills the run rather than silently mispairing.

===================================================================================================
ROUTE 81 == V98.  V97 BASE + A CAVE REWRITE.  ZERO calibration bytes, ZERO 427 bytes.
===================================================================================================
    byte4 b7 0x80 = gp-0x6b70 < 0                      V96's rung, byte-identical
    byte4 b6 0x40 = |gp-0x6bfe| >= |gp-0x374c>>4|      ⭐ MODEL   vs ACTUAL
    byte4 b5 0x20 = |gp-0x6bfa| >= |gp-0x374c>>4|      ⭐ REQUEST vs ACTUAL
    byte4 b4 0x10 = (gp-0x374c>>4) < 0                 V96's OWN b6 rung = the converse pos. control
    byte4 b3 0x08 = gp-0x6752 >= 0                     the polarity constant's SIGN
    byte7[7:6]    = 2  (byte7 & 0xC0 == 0x80)          BUILD IDENTITY, hard-wired `mov 0x2,r7`

    427 (0x1AB) = clamp(|gp-0x6b70| * 5 >> 6, 0, 0x3FF)  -- V96/V97's packer, UNTOUCHED
                  => counts = wire * 64/5

🛑 **THE ~50-BUILD "byte4[7:3] IS ALWAYS ODD" CONVENTION DOES NOT HOLD HERE.**  `b3` is a
   MEASURAND, so byte4 goes EVEN whenever `gp-0x6752 < 0`.  That is THE FINDING, not a fault.
   Liveness has moved to byte7.  (`builds/v80_v107/build_v98_tva.py`, section VAL, pre-registered.)

🛑 **PRE-REGISTERED b6 EXCLUSION.**  `FUN_0003bc20` plausibility-latches `gp-0x6bfe` to `0x7FFF`
   when |model| > 20000; in that state b6 reads TRUE for an unrelated reason.  The latch rails
   `gp-0x6b70`, so **CAN 427 pins at exactly 1023** on precisely those frames.  Score b6 only on
   frames with `ab_mt != 1023`, and report the excluded count.  (Prior: 0 / 87,423 frames on
   routes 80/7e/7f.)

Usage:
    python decode/extract_r81.py                 # extract + identity + health + census
    python decode/extract_r81.py extract 81
    python decode/extract_r81.py identity 81
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
from collections import Counter
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import extract_r7d as X  # noqa: E402  -- installs the taps; brings D + rlog_parse with it

D = X.D

NEW = {
    "81": ("75604b0a432fdc89_00000081--c7103d2cb4", 3, "analysis-2020accord/_scratch/cache/r81",
           "r81s", "r81", "V98"),
}
for _k, _v in NEW.items():
    D.ROUTES[_k] = _v
D.ROUTES.setdefault("80", ("75604b0a432fdc89_00000080--6c8b103892", 2,
                           "analysis-2020accord/_scratch/cache/r80", "r80s", "r80", "V97"))

# V98 carries V96/V97's 427 spec verbatim: gp-0x6b70, `sar 6`, magnitude + sign bit on byte4 b7.
for _k in NEW:
    X.WIRE_SCALE[_k] = 64.0 / 5.0
    X.WIRE_SOURCE[_k] = "gp-0x6b70 (PID reference lane), sar 6  [V96/V97/V98 spec, UNTOUCHED]"
X.WIRE_SCALE.setdefault("80", 64.0 / 5.0)
X.WIRE_SOURCE.setdefault("80", "gp-0x6b70 (PID reference lane), sar 6")

# ---- V98's byte-4 map, read off `builds/v80_v107/build_v98_tva.py`'s PAYLOAD, not inferred.
M_B7, M_B6, M_B5, M_B4, M_B3 = 0x80, 0x40, 0x20, 0x10, 0x08
X.BITNAMES["81"] = {
    "b7_sign_6b70_neg": M_B7,          # gp-0x6b70 < 0
    "b6_MODEL_ge_ACTUAL": M_B6,        # |gp-0x6bfe| >= |gp-0x374c>>4|
    "b5_REQUEST_ge_ACTUAL": M_B5,      # |gp-0x6bfa| >= |gp-0x374c>>4|
    "b4_sign_374c_neg": M_B4,          # (gp-0x374c>>4) < 0
    "b3_pol_6752_ge0": M_B3,           # gp-0x6752 >= 0
}
X.BITNAMES.setdefault("80", {"b7_sign_6b70": 0x80, "b6_sign_374c": 0x40,
                             "b5_Mhi_bit1": 0x20, "b4_Mhi_bit0": 0x10,
                             "b3_mode_674e_lt28": 0x08})

IDENT_MASK, IDENT_V98 = 0xC0, 0x80        # byte7[7:6] == 2  ⇒  byte7 & 0xC0 == 0x80
IDENT_V96_V97 = 0x40                      # byte7[7:6] == 1  ⇒  V96 / V97
LATCH_WIRE = 1023                         # 427 == 1023 ⇒ the observer plausibility latch fired


# ======================================================================================
#  IDENTITY -- single-frame, structural.  byte7[7:6] == 2 proves V98.
# ======================================================================================
def identity(route="81"):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    b7 = np.asarray(z["raw14_b7"], int) & 0xFF
    n = len(b4)
    code = (b7 & IDENT_MASK) >> 6
    cu, cc = np.unique(code, return_counts=True)
    duty2 = float((code == 2).mean())
    field = (b4 >> 3) & 0x1F
    fu, fc = np.unique(field, return_counts=True)
    out = dict(route=route, build=lab, frames=int(n),
               byte7_code_hist={int(v): int(c) for v, c in zip(cu, cc)},
               byte7_code2_duty=duty2,
               byte7_code2_frames=int((code == 2).sum()),
               byte7_full_hist={int(v): int(c) for v, c in
                                zip(*np.unique(b7, return_counts=True))},
               byte4_field_hist={int(v): int(c) for v, c in zip(fu, fc)},
               byte4_field_even_n=int(((field & 1) == 0).sum()),
               byte4_field_even_frac=float(((field & 1) == 0).mean()))
    print(f"\n  === IDENTITY, route {route} (expected {lab}): {n:,} 0x14A frames ===")
    print("    byte7[7:6] code histogram: " +
          "  ".join(f"{int(v)}:{int(c):,}" for v, c in zip(cu, cc)))
    print(f"    ⭐ POS-1  byte7[7:6] == 2 duty = {duty2:.6f}  ({out['byte7_code2_frames']:,} frames)"
          f"   -- V98 hard-wires 2; V96/V97 hard-wire 1; builds <= V91 give 0")
    print("    byte4 field = (byte4>>3)&0x1F histogram: " +
          "  ".join(f"{int(v)}:{int(c):,}" for v, c in zip(fu, fc)))
    print(f"    ⚠ EVEN field values: {out['byte4_field_even_n']:,} "
          f"({100*out['byte4_field_even_frac']:.2f} %)  -- EXPECTED on V98 (b3 is a measurand). "
          f"NOT a fault.")

    if duty2 >= 0.999:
        out["verdict"] = ("✅ V98 IS ON THE CAR -- byte7[7:6] == 2 on >= 99.9 % of frames, which "
                          "V96/V97 (hard-wired 1) and every build <= V91 (0) cannot produce.")
    elif duty2 == 0.0:
        out["verdict"] = ("🛑 NOT V98 -- byte7[7:6] is never 2.  STOP: the wrong build is on the "
                          "car, or the cave did not run.")
    else:
        out["verdict"] = (f"⚠ byte7[7:6] == 2 on only {100*duty2:.2f} % of frames -- POS-1 FAILS "
                          f"its >= 99.9 % pre-registration.  Nothing may be reported.")
    print(f"    VERDICT: {out['verdict']}")
    (ROOT / cdir / f"{stem}_identity.json").write_text(json.dumps(out, indent=1, default=float))
    return out


# ======================================================================================
#  HEALTH -- fault sentinels + every rung's duty, with the 427==1023 exclusion applied to b6.
# ======================================================================================
def health(route="81"):
    return X.health(route)


def census(route="81"):
    return X.census(route)


def extract_route(route="81"):
    return X.extract_route(route)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        extract_route("81")
        identity("81")
        health("81")
        census("81")
    else:
        fn = {"extract": extract_route, "identity": identity, "health": health,
              "census": census}[args[0]]
        for r in (args[1:] or ["81"]):
            fn(r)
