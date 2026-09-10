#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""V290 feedback-operand hook: independent byte-level verification (agent `fbhook`, 2026-09-09).

INDEPENDENT of analysis-2020accord/verify/v290_q1q3_rateop_and_ram_census.py -- own decoder tables,
own free-run finder, own boot-image mapping, positive-controlled before any null is trusted.

Sections:
  A  V289 image identity + the hook site 0x29D72 + the cals that bound the operand
  B  gp-relative census of the candidate RAM runs (all load/store widths, bit-ops, 6-byte ext form)
  C  absolute-pointer + movhi/movea register-indirect check on the winning run
  D  boot (.data) values, with the flash->RAM mapping validated by a positive control
  E  free flash
"""
import hashlib
import struct
import os
from pathlib import Path

FWROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                             "C:/Users/dudei/Desktop/Projects/accord-firmwares"))
A2020 = FWROOT / "analysis-2020accord"
V289 = A2020 / ("_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6"
                "-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
V282 = A2020 / ("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X"
                ".FEEDBACK46080.TORQUE.TAP_plain_image.bin")
STOCK = A2020 / "stock_fw_dump" / "code.bin"

img = V289.read_bytes()
base = V282.read_bytes()
stk = STOCK.read_bytes()
GP, TP = 0xFEDF8000, 0xBF000


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


print("=" * 100)
print("A -- IMAGE IDENTITY AND THE HOOK SITE")
print("V289 sha256 = %s   len=%d" % (hashlib.sha256(img).hexdigest(), len(img)))
print("V282 sha256 = %s" % hashlib.sha256(base).hexdigest())
diff = [i for i in range(len(img)) if img[i] != base[i]]
print("V289 vs V282 full-file byte diff: %d bytes; ranges:" % len(diff))
if diff:
    runs = []
    s = p = diff[0]
    for a in diff[1:]:
        if a == p + 1:
            p = a
        else:
            runs.append((s, p))
            s = p = a
    runs.append((s, p))
    for a, b in runs:
        print("    0x%06X-0x%06X  (%d B)" % (a, b, b - a + 1))

for name, addr, n in [("hook site 0x29D72 (st.h r16,-0x6a32,gp)", 0x29D72, 4),
                      ("E-former 0x29D76 shl/sub", 0x29D76, 4),
                      ("fb clamp load 0x28F96 (ld.hu tp+0x72e6)", 0x28F96, 4)]:
    same = "IDENTICAL" if img[addr:addr + n] == stk[addr:addr + n] else "*** DIFFERS ***"
    print("  %s:\n     V289 %s | V282 %s | stock %s  %s"
          % (name, img[addr:addr + n].hex(" "), base[addr:addr + n].hex(" "),
             stk[addr:addr + n].hex(" "), same))

print("\n  cals bounding the feedback operand (little-endian u16):")
for cell, label in [(0xC62E6, "fb sum clamp (r26)"), (0xC63E8, "fb pole a"), (0xC63EA, "fb pole b"),
                    (0xC62E4, "E clamp (E>>5)"), (0xC61BE, "sum clamp"), (0xC61B6, "D clamp"),
                    (0xC61BC, "P clamp"), (0xC61B4, "T clamp")]:
    print("    0x%05X %-22s  V289 = %6d   V282 = %6d   stock = %6d"
          % (cell, label, u16(img, cell), u16(base, cell), u16(stk, cell)))

# ---------------------------------------------------------------- B: gp census
print("\n" + "=" * 100)
print("B -- gp-RELATIVE CENSUS (own decoder)")
GPREG = 4


def census(image):
    hits = {}

    def add(d, a, k):
        hits.setdefault(d & 0xFFFF, []).append((a, k))

    n = len(image)
    for a in range(0, n - 5, 2):
        hw1 = u16(image, a)
        op = (hw1 >> 5) & 0x3F
        if op < 0x38:
            continue
        reg1 = hw1 & 0x1F
        reg2 = (hw1 >> 11) & 0x1F
        hw2 = u16(image, a + 2)
        if op in (0x38, 0x3A):                      # ld.b / st.b, disp = hw2, any parity
            if reg1 == GPREG:
                add(hw2, a, "ld.b" if op == 0x38 else "st.b")
        elif op in (0x39, 0x3B):                    # ld.h/ld.w, st.h/st.w -- hw2 bit0 selects width
            if reg1 == GPREG:
                d = hw2 & 0xFFFE
                w = 4 if (hw2 & 1) else 2
                k = ("ld" if op == 0x39 else "st") + (".w" if w == 4 else ".h")
                add(d, a, k)
                add(d + 1, a, k)
                if w == 4:
                    add(d + 2, a, k)
                    add(d + 3, a, k)
        elif op in (0x3C, 0x3D):                    # ld.bu (reg2!=0, hw2 odd) | ext6 (reg2==0) | jr/jarl
            if reg2 == 0:
                hw3 = u16(image, a + 4)
                d = ((hw3 << 1) | ((hw2 >> 15) & 1)) & 0xFFFF
                if reg1 == GPREG:
                    for k in range(4):
                        add(d + k, a, "ext6")
            elif (hw2 & 1) == 1:
                if reg1 == GPREG:
                    add((hw2 & 0xFFFE) | (op & 1), a, "ld.bu")
        elif op == 0x3E:                            # set1/not1/clr1/tst1 bit ops, disp16 = hw2
            if reg1 == GPREG:
                add(hw2, a, "bitop")
        elif op == 0x3F:                            # ld.hu, hw2 bit0 fixed 1, disp even
            if reg1 == GPREG:
                add(hw2 & 0xFFFE, a, "ld.hu")
                add((hw2 & 0xFFFE) + 1, a, "ld.hu")
    return hits


H = census(img)
CTRL = {0x3D30: "fb filter state (2 accesses)",
        0x6A56: "the rate operand (25 readers/4 writers)",
        0x6A32: "setpoint publish (st.h @0x29D72)",
        0x6C44: "V289 cave state s1",
        0x674E: "variant selector",
        0x6B38: "delivered lane torque",
        0x6CF8: "Honda first-tick sentinel"}
print("  positive controls (a scanner that misses these is broken):")
ok = True
for m, lab in CTRL.items():
    d = (0x10000 - m) & 0xFFFF
    c = len(H.get(d, []))
    print("    gp-0x%04X  %-34s hits=%3d  %s" % (m, lab, c, "PASS" if c else "*** FAIL ***"))
    ok &= c > 0
print("  positive-control battery: %s" % ("PASS" if ok else "FAIL -- DO NOT TRUST ANY NULL BELOW"))


def run_report(lo_disp, hi_disp, label):
    occ = []
    for m in range(lo_disp, hi_disp + 1):
        d = (0x10000 - m) & 0xFFFF
        if d in H:
            occ.append((m, H[d]))
    print("\n  %s: gp-0x%04X..gp-0x%04X  (%d bytes)"
          % (label, hi_disp, lo_disp, hi_disp - lo_disp + 1))
    if not occ:
        print("     -> ZERO gp-relative hits under all forms  [FREE, pending C/D]")
    else:
        for m, hs in occ[:14]:
            print("     gp-0x%04X: %s" % (m, ", ".join("0x%05X/%s" % (a, k) for a, k in hs[:4])))
        print("     -> %d occupied displacements  [NOT FREE]" % len(occ))
    return len(occ)


run_report(0x6D2D, 0x6D74, "PRIMARY candidate (prior trace's 72-byte run)")
run_report(0x6927, 0x692E, "smaller candidate #1")
run_report(0x6B8B, 0x6B8E, "smaller candidate #2")
run_report(0x6AAA, 0x6AB0, "CONTROL: gp-0x6ab0 run (record says FALSIFIED/occupied)")
run_report(0x68AA, 0x68B0, "CONTROL: gp-0x68b0 run (record says FALSIFIED/occupied)")
run_report(0x6C3A, 0x6C44, "CONTROL: V289 cave state (must show OCCUPIED)")

# widen: find every free run >= 12 bytes in the neighbourhood of the primary candidate
print("\n  free runs >= 12 bytes in gp-0x7000..gp-0x6000:")
free_runs = []
cur = None
for m in range(0x6000, 0x7001):
    d = (0x10000 - m) & 0xFFFF
    if d not in H:
        if cur is None:
            cur = [m, m]
        else:
            cur[1] = m
    else:
        if cur and cur[1] - cur[0] + 1 >= 12:
            free_runs.append(tuple(cur))
        cur = None
if cur and cur[1] - cur[0] + 1 >= 12:
    free_runs.append(tuple(cur))
for lo, hi in free_runs:
    print("     gp-0x%04X..gp-0x%04X  %3d bytes   (addr 0x%08X..0x%08X)"
          % (hi, lo, hi - lo + 1, GP - hi, GP - lo))

# ---------------------------------------------------------------- C: indirect
print("\n" + "=" * 100)
print("C -- ABSOLUTE-POINTER AND movhi/movea CHECK on the primary run")
LO_A, HI_A = GP - 0x6D74, GP - 0x6D2D
print("  address range 0x%08X .. 0x%08X" % (LO_A, HI_A))
hits = 0
for a in range(0, len(img) - 3):
    v = u32(img, a)
    if LO_A <= v <= HI_A:
        print("    literal LE address 0x%08X at file offset 0x%06X" % (v, a))
        hits += 1
print("  literal 4-byte LE address occurrences (any alignment): %d" % hits)

mh = []
for a in range(0, len(img) - 3, 2):
    hw1 = u16(img, a)
    if ((hw1 >> 5) & 0x3F) == 0x32 and u16(img, a + 2) == 0xFEDF:
        mh.append((a, (hw1 >> 11) & 0x1F))
pairs = 0
for a, dst in mh:
    for b in range(a + 4, min(a + 24, len(img) - 3), 2):
        hw1 = u16(img, b)
        if ((hw1 >> 5) & 0x3F) == 0x31 and (hw1 & 0x1F) == dst:
            imm = u16(img, b + 2)
            if (LO_A & 0xFFFF) <= imm <= (HI_A & 0xFFFF):
                print("    movhi 0xFEDF @0x%05X + movea 0x%04X @0x%05X -> LANDS IN THE RUN"
                      % (a, imm, b))
                pairs += 1
print("  movhi 0xFEDF sites image-wide: %d; movhi+movea pairs landing in the run: %d"
      % (len(mh), pairs))

# ---------------------------------------------------------------- D: boot values
print("\n" + "=" * 100)
print("D -- BOOT (.data) VALUES, mapping validated by positive control")


def MAP(addr):
    return 0x86260 + (addr - 0xFEDF11B0)


ctl_addr = GP - 0x6AB0
ctl = u32(img, MAP(ctl_addr))
print("  control: gp-0x6AB0 = 0x%08X -> flash 0x%06X = 0x%08X (record says 0x02880288: %s)"
      % (ctl_addr, MAP(ctl_addr), ctl,
         "MAPPING VALIDATED" if ctl == 0x02880288 else "*** MAPPING SUSPECT ***"))
for m in range(0x6D74, 0x6D2C, -4):
    a = GP - m
    print("    gp-0x%04X = 0x%08X -> flash 0x%06X = 0x%08X" % (m, a, MAP(a), u32(img, MAP(a))))

# ---------------------------------------------------------------- E: free flash
print("\n" + "=" * 100)
print("E -- FREE FLASH")
for lo, hi, lab in [(0xC4A00, 0xC4BD8, "before 0xC4BD8"),
                    (0xC4BD8, 0xC4C00, "V288's cave region (V282 base -> should be virgin)"),
                    (0xC4C00, 0xC4C8C, "V289 notch cave (OCCUPIED)"),
                    (0xC4C8C, 0xC4FF0, "after the V289 cave")]:
    seg = img[lo:hi]
    nff = sum(1 for b in seg if b != 0xFF)
    print("  [0x%05X,0x%05X) %5d B  non-0xFF = %5d   %s" % (lo, hi, len(seg), nff, lab))
print("  0xC4FF0..0xC4FFC verbatim: %s" % img[0xC4FF0:0xC4FFC].hex(" "))
print("  CRC trailer 0xC4FFC:       %s" % img[0xC4FFC:0xC5000].hex(" "))
