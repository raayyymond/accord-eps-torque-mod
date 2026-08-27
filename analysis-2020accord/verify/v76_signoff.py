#!/usr/bin/env python3
"""verify/v76_signoff.py -- build the patched V38 image IN MEMORY, re-read the tables back through the
pointer arrays, and confirm the surface. This is the kit's "re-disassemble from the built image
before declaring victory" rule applied to calibration records.

Nothing is written to disk. This produces the exact final record bytes for BuildV76 to assert.
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
import hashlib
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import v76_surface as V

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
IMG = os.path.join(ROOT, "analysis-2020accord", "_v38_plain_image.bin")
EXPECT_SHA = "a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8"
PTR_C, PTR_E, MODE, NPTS, REC_LEN = 0xC9E9C, 0xC9F84, 26, 4, 20

CX_NEW = [2240, 3840, 5120, 8960]
CY_NEW = [566, 566, 566, 908]
EX_NEW = [0, 119, 2500, 4000]
EY_NEW = [0, 300, 539, 927]

base = bytearray(open(IMG, "rb").read())
sha = hashlib.sha256(bytes(base)).hexdigest()
print("=" * 100)
print("V76 SIGN-OFF -- patched in memory, read back through the pointer arrays")
print("=" * 100)
print("  base sha256 %s  %s" % (sha, "MATCH" if sha == EXPECT_SHA else "*** MISMATCH ***"))
assert sha == EXPECT_SHA


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


recC, recE = u32(base, PTR_C + 4 * MODE), u32(base, PTR_E + 4 * MODE)
print("  FactorC m26 -> 0x%05X   FactorE m26 -> 0x%05X" % (recC, recE))

# -- patch: write ONLY the 8 Y bytes / 8 X bytes that the design changes ---------------------
patched = bytearray(base)
for rec, X, Y in ((recC, CX_NEW, CY_NEW), (recE, EX_NEW, EY_NEW)):
    for i, x in enumerate(X):
        struct.pack_into("<H", patched, rec + 2 + 2 * i, x)
    for i, y in enumerate(Y):
        struct.pack_into("<H", patched, rec + 2 + 2 * NPTS + 2 * i, y)

changed = [i for i in range(len(base)) if base[i] != patched[i]]
print("\n  bytes changed across the WHOLE 1 MB image: %d at %s"
      % (len(changed), ["0x%05X" % a for a in changed]))
runs = []
for a in changed:
    if runs and a == runs[-1][-1] + 1:
        runs[-1].append(a)
    else:
        runs.append([a])
print("  contiguous runs: %s" % ["0x%05X..0x%05X" % (r[0], r[-1]) for r in runs])

# -- the exact final record images ------------------------------------------------------------
print("\n" + "-" * 100)
print("FINAL RECORD BYTES -- assert these after writing (20 B each, tail included)")
print("-" * 100)
for nm, rec in (("FactorC m26", recC), ("FactorE m26", recE)):
    old = bytes(base[rec:rec + REC_LEN])
    new = bytes(patched[rec:rec + REC_LEN])
    print("  %s @ 0x%05X" % (nm, rec))
    print("    V38 base : %s" % " ".join("%02X" % b for b in old))
    print("    V76 final: %s" % " ".join("%02X" % b for b in new))
    print("    diff mask: %s"
          % " ".join("^^" if a != b else "  " for a, b in zip(old, new)))

# -- read BACK through the pointer arrays, exactly as the ECU would ---------------------------
print("\n" + "-" * 100)
print("READ-BACK through FACTOR_*_PTRS[26] on the PATCHED image (not the values we wrote)")
print("-" * 100)
ok = True
for w, wantX, wantY in (("C", CX_NEW, CY_NEW), ("E", EX_NEW, EY_NEW)):
    a, hdr, X, Y = V.read_rec(bytes(patched), w, MODE)
    good = (X == wantX and Y == wantY and hdr == NPTS)
    ok &= good
    print("  Factor%s m26 @0x%05X hdr=%d X=%-26s Y=%-24s  %s"
          % (w, a, hdr, X, Y, "PASS" if good else "*** FAIL ***"))

# -- mode 24 and the other tables must be untouched --------------------------------------------
print("\n  mode-24 and sibling-table integrity on the patched image:")
for w in ("B", "C", "D", "E", "CEIL"):
    for m in (24, 26):
        if w in ("C", "E") and m == MODE:
            continue
        pb, hb, Xb, Yb = V.read_rec(bytes(base), w, m)
        pp, hp, Xp, Yp = V.read_rec(bytes(patched), w, m)
        same = (Xb, Yb, hb) == (Xp, Yp, hp)
        ok &= same
        if not same:
            print("    *** Factor%s mode %d CHANGED ***" % (w, m))
print("    all Factor B/C/D/E/CEIL records in modes 24 and 26, except FactorC/E mode 26: %s"
      % ("UNCHANGED" if ok else "*** SOMETHING MOVED ***"))

# -- the surface, computed from the PATCHED image itself ---------------------------------------
print("\n" + "-" * 100)
print("SURFACE FROM THE PATCHED IMAGE (tables read back, not injected)")
print("-" * 100)
s26 = V.Surface(img=bytes(patched), mode=26)
s24 = V.Surface(img=bytes(patched), mode=24)
print("  mode 26  dose at 21 deg/s by speed:  %s"
      % "  ".join("%d km/h=%d" % (v, s26.mag(int(v * 64), 99)) for v in (5, 20, 35, 60, 80, 140)))
print("  mode 24  dose at 21 deg/s by speed:  %s   <- manual column, must be stock"
      % "  ".join("%d km/h=%d" % (v, s24.mag(int(v * 64), 99)) for v in (5, 20, 35, 60, 80, 140)))
M = (566 * 300) >> 10
print("  k = M/(E_X1-E_X0) = %d/%d = %.4f   dose@99 = %d   max|gp-0x6bd0| = %d"
      % (M, EX_NEW[1] - EX_NEW[0], M / (EX_NEW[1] - EX_NEW[0]), s26.mag(0, 99),
         max((V.lerp(CX_NEW, CY_NEW, v) * 927) >> 10 for v in range(0, 14001))))
stock24 = V.Surface("stock", 24)
match24 = all(s24.mag(int(v * 64), r) == stock24.mag(int(v * 64), r)
              for v in range(0, 200, 5) for r in (0, 50, 99, 200, 1000, 3000))
print("  mode 24 output identical to stock over a 240-point (speed,rate) grid: %s"
      % ("PASS" if match24 else "*** FAIL ***"))
print("\n  => %s" % ("SIGNED OFF" if ok and match24 else "*** DO NOT BUILD ***"))
