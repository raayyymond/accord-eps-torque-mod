#!/usr/bin/env python3
"""studies/sessions/v74_v75/v75_fault_attribute.py -- attribute EVERY differing byte between two images.

Builds an address->label map from the actual pointer arrays in the image (not from the
build script's prose), plus the known CRC word positions, then reports any byte that
differs and cannot be attributed.

CRC words: the bootloader's block chain stores a 4-byte word at <block>+0xFFC for each
0x1000 block. Verified structurally here by position only (every diff at X..XFFC).
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
import os, struct, sys
import v75_fault_tables as T

NAMES = {"B": ("FactorB", 4), "C": ("FactorC", 4), "D": ("FactorD", 5),
         "E": ("FactorE", 4), "CEIL": ("Ceiling", 2)}

CAVE = (0xC4B34, 0xC4B78)   # 68 B, from the stock->V74 and stock->V75 diffs (0xFF filler on stock)


def build_map(img, nmodes=34):
    """addr -> human label, for every halfword the LERPs actually index."""
    m = {}
    for which, (nm, npts) in NAMES.items():
        for mode in range(nmodes):
            base = T.rec_addr(img, which, mode)
            m.setdefault(base + 0, []).append("%s[mode %d].hdr" % (nm, mode))
            m.setdefault(base + 1, []).append("%s[mode %d].hdr" % (nm, mode))
            for i in range(npts):
                for k in (0, 1):
                    m.setdefault(base + 2 + 2 * i + k, []).append("%s[mode %d].X[%d]" % (nm, mode, i))
                    m.setdefault(base + 2 + 2 * npts + 2 * i + k, []).append("%s[mode %d].Y[%d]" % (nm, mode, i))
    return m


def attribute(a_name, b_name, lo=0x13000, hi=0x100000):
    a, b = T.load(a_name), T.load(b_name)
    m = build_map(a)
    buckets = {}
    unattributed = []
    for i in range(lo, hi):
        if a[i] == b[i]:
            continue
        if CAVE[0] <= i < CAVE[1]:
            lab = "PROBE CAVE 0xC4B34..0xC4B77"
        elif (i & 0xFFF) >= 0xFFC:
            lab = "CRC word @0x%05X (block 0x%05X)" % (i & ~3, i & ~0xFFF)
        elif i in m:
            lab = " | ".join(sorted(set(m[i])))
        else:
            lab = None
            unattributed.append(i)
        if lab:
            buckets.setdefault(lab, []).append(i)

    print("=== ATTRIBUTION  %s -> %s  over [0x%X,0x%X) ===" % (a_name, b_name, lo, hi))
    tot = 0
    for lab in sorted(buckets, key=lambda k: buckets[k][0]):
        idxs = buckets[lab]
        tot += len(idxs)
        if "CRC" in lab or "CAVE" in lab:
            print("  0x%05X..0x%05X  %2dB  %s" % (idxs[0], idxs[-1], len(idxs), lab))
        else:
            lo_i, hi_i = idxs[0] & ~1, (idxs[-1] | 1)
            ov = a[lo_i] | (a[lo_i + 1] << 8)
            nv = b[lo_i] | (b[lo_i + 1] << 8)
            print("  0x%05X  %2dB  %-34s  %5d -> %5d" % (idxs[0], len(idxs), lab, ov, nv))
    print("  ---- attributed: %d bytes" % tot)
    if unattributed:
        print("  !!!! UNATTRIBUTED: %d bytes at %s"
              % (len(unattributed), ["0x%05X" % x for x in unattributed[:40]]))
    else:
        print("  ---- UNATTRIBUTED: 0 bytes   [every differing byte accounted for]")
    return unattributed


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "v74"
    b = sys.argv[2] if len(sys.argv) > 2 else "v75"
    attribute(a, b)
