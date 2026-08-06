#!/usr/bin/env python3
"""v75_fault_attribute.py -- attribute EVERY differing byte between two images.

Builds an address->label map from the actual pointer arrays in the image (not from the
build script's prose), plus the known CRC word positions, then reports any byte that
differs and cannot be attributed.

CRC words: the bootloader's block chain stores a 4-byte word at <block>+0xFFC for each
0x1000 block. Verified structurally here by position only (every diff at X..XFFC).
"""
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
