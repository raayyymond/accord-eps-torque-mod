#!/usr/bin/env python3
r"""DIFF EVERY CANDIDATE AGAINST THE LAST *FLOWN* IMAGE -- NOT AGAINST ITS BUILD PARENT.

WHY THIS EXISTS
---------------
2026-08-28.  V133 was recommended to the operator as "every measured-good edit ever flown" and as
a CLEAN TEST of V62's Lever A.  Against its build parent (V131) it was 3 bytes.  Against V122 --
the last build actually FLOWN -- it was SIX cells, two of them large:

    0xC407E  b26 clamp        511 -> 1023    apparent-mass ceiling, NOT mode-gated
    0x3AB76  Lever A r26 arm  0xAA -> 0xA9   sar 10 -> 9  =  x2 on the arm
    0x3AC20  Lever A r24 arm  0xAA -> 0xA9   x2, and RECORDED as having caused grind #2
    0xC40DC  alpha2             8 -> 5
    0xC640A  oscillation Y  -8192 -> -1966
    0xC6CD0  LKAS gain       5346 -> 7128    6x -> 8x, +33 % excitation

It regressed hard on-car: "massive, violent grinding after enabling LKAS which continues after
disengaging ... also grind #2 while disengaged doing a hard turn."  The build-parent chain HID the
accumulated drift; the flown image does not.

THE RULE THIS ENFORCES
----------------------
A build presented as a test of one lever must differ from the LAST FLOWN build by that lever
alone.  Run this before recommending ANY flight, and report the payload-byte count.

USAGE
-----
    python analysis-2020accord/verify/diff_vs_flown.py                  # audit the default set
    python analysis-2020accord/verify/diff_vs_flown.py v137 v138        # audit specific tags
    python analysis-2020accord/verify/diff_vs_flown.py --flown v122 v137
"""
import glob
import os
import struct
import sys

ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT",
                      "C:/Users/dudei/Desktop/Projects/accord-firmwares")
IMGDIR = os.path.join(ROOT, "analysis-2020accord")
START, END = 0x13000, 0x100000

# Cells worth naming in a diff.  A cell NOT in this map still prints -- it is just unlabelled.
NAMES = {
    0xC407E: "b26 clamp (APPARENT MASS ceiling, NOT mode-gated)",
    0xC4004: "  its FLOAT twin (must satisfy float*1024 == int+1)",
    0x3AB76: "Lever A r26 arm   sar10->9 = x2 on the arm",
    0x3AC20: "Lever A r24 arm   x2  -- RECORDED as having CAUSED grind #2",
    0xC40DC: "alpha2 (b26 post-EMA; the identified creep lever)",
    0xC40DA: "  its >>7 twin feeding gp-0x6c2e",
    0xC640A: "oscillation-branch Y",
    0xC640C: "implausible-sensor branch Y",
    0xC6CD0: "LKAS gain  (5346 = 6x, 7128 = 8x)",
    0xC61B2: "forward clamp A (must match the gain)",
    0xC61B4: "forward clamp B (must match the gain)",
    0xC40BC: "relay knee",
    0xC40D2: "K1 (ceiling 1023)",
    0xC4080: "relay offset K0 -- NEVER RAISE",
    0xC40D0: "friction EMA pole (the only PHASE cell in the lane)",
    0xC63D2: "trim IIR",
    0xC620A: "hard-reversal detector arm threshold",
    0xC64FA: "gp-0x671a CEIL",
    0x55DF2: "427 probe tap",
    0x55E10: "427 packer sar",
}
# Cells whose movement is LOUD: each has an on-car regression or an operator instruction behind it.
LOUD = {
    0x3AB76: "PRIME SUSPECT for V133's regression -- not LKAS-gated, +6 dB loop gain",
    0x3AC20: "PRIME SUSPECT -- recorded as having CAUSED grind #2, reproduced on V133",
    0xC6CD0: "operator: '8x only IF we dont get even more oscillation and grinding'.  We did.",
    0xC407E: "raised in V133; probe says it is likely INERT (never reached), do not re-blame it",
    0xC4080: "raising the relay offset introduces a Coulomb FLOOR -- never done, never safe",
}
DEFAULT_FLOWN = "v122"
DEFAULT_SET = ("v124", "v125", "v127", "v137")


def load(tag):
    pats = ["/**/*_%s_*plain_image.bin" % tag, "/**/*%s*plain_image.bin" % tag]
    for p in pats:
        g = [x for x in glob.glob(IMGDIR + p, recursive=True) if "SUPERSEDED" not in x]
        if g:
            return open(g[0], "rb").read(), os.path.basename(g[0])
    return None, None


def is_crc_trailer(addr):
    return (addr & 0xFFF) >= 0xFFC


def diff(base, img):
    runs = []
    for a in range(START, END):
        if img[a] == base[a]:
            continue
        if runs and a == runs[-1][1]:
            runs[-1][1] = a + 1
        else:
            runs.append([a, a + 1])
    return [(lo, hi) for lo, hi in runs if not is_crc_trailer(lo)]


def audit(flown_tag, tags):
    base, bname = load(flown_tag)
    if base is None:
        print("  cannot find the flown image for %r" % flown_tag)
        return 1
    print("=" * 100)
    print("  DIFF vs THE LAST FLOWN BUILD: %s" % bname)
    print("=" * 100)
    worst = 0
    for tag in tags:
        img, name = load(tag)
        if img is None:
            print("\n  %-6s (no image found)" % tag.upper())
            continue
        runs = diff(base, img)
        n = sum(hi - lo for lo, hi in runs)
        worst = max(worst, n)
        print("\n  %-6s %s" % (tag.upper(), name))
        for lo, hi in runs:
            lbl = NAMES.get(lo, "")
            print("        0x%05X  %d B  %-52s %s -> %s"
                  % (lo, hi - lo, lbl, base[lo:hi].hex(), img[lo:hi].hex()))
            if lo in LOUD:
                print("                 \U0001f6d1 %s" % LOUD[lo])
        verdict = ("SINGLE-VARIABLE -- interpretable" if n <= 2 else
                   "MULTI-VARIABLE -- a result cannot be attributed to one lever")
        print("        => %d payload byte(s) vs %s   %s" % (n, flown_tag.upper(), verdict))
    print("\n" + "=" * 100)
    print("  A build presented as a test of ONE lever must differ from the last FLOWN build")
    print("  by that lever alone.  V133 was 3 bytes vs its PARENT and 6 cells vs the last FLOWN")
    print("  build, and it regressed hard on-car.  Diff against what is on the CAR.")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flown = DEFAULT_FLOWN
    if "--flown" in sys.argv:
        i = sys.argv.index("--flown")
        flown = sys.argv[i + 1]
        args = [a for a in args if a != flown]
    sys.exit(audit(flown, args or list(DEFAULT_SET)))
