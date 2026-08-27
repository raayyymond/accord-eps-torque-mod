#!/usr/bin/env python3
"""studies/sessions/v74_v75/v75_fault_diff.py -- exhaustive byte diff between stock / V74 / V75 / V76 plain images.

Pure Python byte work (per CLAUDE.md: byte-level work is Python, never a disassembler).
Reports every differing run in [0x13000, 0x100000) with old/new bytes.

Usage:  python studies/sessions/v74_v75/v75_fault_diff.py [--lo 0x13000] [--hi 0x100000]
"""
import os, sys, argparse

ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT",
                      "C:/Users/dudei/Desktop/Projects/accord-firmwares")
A = os.path.join(ROOT, "analysis-2020accord")

IMAGES = {
    "stock": os.path.join(A, "stock_fw_dump", "code.bin"),
    "v73":   os.path.join(A, "_v73_plain_image.bin"),
    "v74":   os.path.join(A, "_v74_engagedcols_x0_12_addonly_plain_image.bin"),
    "v75":   os.path.join(A, "_v75_CY0.566-EX1.200_magprobe_plain_image.bin"),
    "v76":   os.path.join(A, "_v76_gate_fb_arm5244_gateprobe_plain_image.bin"),
}


def load(name):
    with open(IMAGES[name], "rb") as f:
        return f.read()


def runs(a, b, lo, hi, gap=8):
    """Yield (start, end) half-open runs where a != b, merging runs separated by < gap equal bytes."""
    out = []
    i = lo
    while i < hi:
        if a[i] != b[i]:
            j = i
            last = i
            while j < hi:
                if a[j] != b[j]:
                    last = j
                    j += 1
                elif j - last < gap:
                    j += 1
                else:
                    break
            out.append((i, last + 1))
            i = last + 1
        else:
            i += 1
    return out


def hx(bs):
    return " ".join("%02X" % x for x in bs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lo", default="0x13000")
    ap.add_argument("--hi", default="0x100000")
    ap.add_argument("--a", default="v74")
    ap.add_argument("--b", default="v75")
    ap.add_argument("--gap", type=int, default=8)
    args = ap.parse_args()
    lo, hi = int(args.lo, 0), int(args.hi, 0)

    a, b = load(args.a), load(args.b)
    rs = runs(a, b, lo, hi, args.gap)
    tot = sum(e - s for s, e in rs)
    print("=== %s -> %s  over [0x%X,0x%X)  : %d runs, %d differing-or-bridged bytes ==="
          % (args.a, args.b, lo, hi, len(rs), tot))
    for s, e in rs:
        n = e - s
        print("\n0x%05X  len=%d" % (s, n))
        print("  %-5s: %s" % (args.a, hx(a[s:e])))
        print("  %-5s: %s" % (args.b, hx(b[s:e])))
    # exact differing byte count (no bridging)
    nd = sum(1 for i in range(lo, hi) if a[i] != b[i])
    print("\nEXACT differing bytes: %d" % nd)


if __name__ == "__main__":
    main()
