#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GATE-1 residual closers for the V290 fb-hook RAM candidate (agent `fbhook`, 2026-09-09).

The plain gp-relative census (v290_fbhook_census.py) cannot see two real access classes:
  (1) `movea/addi <disp>, gp, ep` + `sld.b/h/w` / `sst.b/h/w` -- an ep window over gp-relative RAM.
  (2) `movea/addi <disp>, gp, rN` + `ld/st <disp2>, rN, rX` -- a re-based disp16 access.
Both are scanned here, with an explicit positive control for each form.
"""
import struct
import os
from pathlib import Path

FWROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                             "C:/Users/dudei/Desktop/Projects/accord-firmwares"))
IMG = (FWROOT / "analysis-2020accord" /
       ("_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6"
        "-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"))
img = IMG.read_bytes()
GP = 0xFEDF8000


def u16(a):
    return struct.unpack_from("<H", img, a)[0]


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


CANDIDATES = {
    "PRIMARY gp-0x6D74..gp-0x6D2D": (GP - 0x6D74, GP - 0x6D2D),
    "CONTROL V289 cave state gp-0x6C44..gp-0x6C3A": (GP - 0x6C44, GP - 0x6C3A),
    "CONTROL gp-0x6AB0..gp-0x6AAA (initialised, unread)": (GP - 0x6AB0, GP - 0x6AAA),
    "CONTROL gp-0x7C28 ep base (form positive control)": (GP - 0x7C28, GP - 0x7C28 + 508),
}

# ---- collect every movea/addi that re-bases gp ------------------------------------------------
rebase = []          # (addr, dstreg, base_addr, mnem)
for a in range(0, len(img) - 3, 2):
    hw1 = u16(a)
    op = (hw1 >> 5) & 0x3F
    if op not in (0x30, 0x31):
        continue
    if (hw1 & 0x1F) != 4:                       # reg1 must be gp
        continue
    dst = (hw1 >> 11) & 0x1F
    if dst == 0:
        continue
    rebase.append((a, dst, (GP + s16(u16(a + 2))) & 0xFFFFFFFF,
                   "movea" if op == 0x31 else "addi"))
print("movea/addi re-basing gp: %d sites" % len(rebase))
ep_sites = [r for r in rebase if r[1] == 30]
print("  of which into ep (r30): %d" % len(ep_sites))
print("  positive control -- a known one: %s"
      % [("0x%05X %s ep <- 0x%08X" % (a, m, b)) for a, d, b, m in ep_sites[:3]])

# ---- (1) ep windows ---------------------------------------------------------------------------
print("\n(1) ep-window overlap (sld/sst reach: 0..508 bytes above the ep base)")
for lab, (lo, hi) in CANDIDATES.items():
    hits = [(a, b) for a, d, b, m in ep_sites if not (b + 508 < lo or b > hi)]
    print("  %-52s overlapping ep bases: %d %s"
          % (lab, len(hits), ["0x%05X->0x%08X" % (a, b) for a, b in hits[:4]]))

# ---- (2) re-based disp16 loads/stores ----------------------------------------------------------
print("\n(2) `movea/addi d,gp,rN` followed within 32 bytes by a disp16 ld/st using rN")
def eff_targets(a0, dst, base):
    out = []
    for a in range(a0 + 4, min(a0 + 36, len(img) - 3), 2):
        hw1 = u16(a)
        op = (hw1 >> 5) & 0x3F
        if op < 0x38 or op > 0x3F:
            continue
        if (hw1 & 0x1F) != dst:
            continue
        hw2 = u16(a + 2)
        if op in (0x38, 0x3A):
            d, n = s16(hw2), 1
        elif op in (0x39, 0x3B):
            d, n = s16(hw2 & 0xFFFE), (4 if hw2 & 1 else 2)
        elif op in (0x3C, 0x3D):
            if ((hw1 >> 11) & 0x1F) == 0 or (hw2 & 1) == 0:
                continue
            d, n = s16((hw2 & 0xFFFE) | (op & 1)), 1
        elif op == 0x3F:
            d, n = s16(hw2 & 0xFFFE), 2
        else:
            continue
        out.append((a, (base + d) & 0xFFFFFFFF, n))
    return out


allt = []
for a0, dst, base, m in rebase:
    allt.extend(eff_targets(a0, dst, base))
print("  re-based disp16 accesses resolved: %d" % len(allt))
for lab, (lo, hi) in CANDIDATES.items():
    hits = [(a, t, n) for a, t, n in allt if not (t + n - 1 < lo or t > hi)]
    print("  %-52s hits: %d %s"
          % (lab, len(hits), ["0x%05X->0x%08X" % (a, t) for a, t, n in hits[:4]]))

# ---- stack-range sanity (the kit's own recorded stack band) -------------------------------------
print("\n(3) stack-band check (record: real stack = gp-0xC000..gp-0x86E4)")
for lab, (lo, hi) in CANDIDATES.items():
    inside = not (hi < GP - 0xC000 or lo > GP - 0x86E4)
    print("  %-52s overlaps the stack band: %s" % (lab, inside))
