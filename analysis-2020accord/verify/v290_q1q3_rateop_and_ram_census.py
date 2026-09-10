# -*- coding: utf-8 -*-
"""V290 design subagent -- Q1 (gp-0x6a56 writer census) + Q3 (free-RAM run scan).

Raw little-endian V850E2 gp-relative decoder, built on the byte-verified opcode table from
docs/traces/TRACE-2026-09-08-rate-loop-lags-and-inloop-filter-hooks.md (both FINAL ADDENDA) and
re-used/extended from analysis-2020accord/verify/adv_v289_d1_ram_census.py's corrected forms.

Forms decoded (gp-relative, reg1==4 only):
  ld.b   op 0x38  disp = hw2 exact (both parities)
  st.b   op 0x3A  disp = hw2 exact (both parities)
  ld.h   op 0x39, hw2&1==0   disp = hw2 & 0xFFFE
  ld.w   op 0x39, hw2&1==1   disp = hw2 & 0xFFFE
  ld.hu  op 0x3F             disp = hw2 & 0xFFFE
  st.h   op 0x3B, hw2&1==0   disp = hw2 & 0xFFFE
  st.w   op 0x3B, hw2&1==1   disp = hw2 & 0xFFFE
  ld.bu  op 0x3C/0x3D, reg2!=0   disp = hw2 & 0xFFFE   (4-byte form)
  ext6   op 0x3C/0x3D, reg2==0   6-byte extended, disp = sign_extend23((hw3<<7)|((hw2>>4)&0x7F))
  bitops op 0x3E  (set1/clr1/tst1/not1), both signed and raw-positive hw2 interpretations

Positive controls run first; census aborts loudly if any control fails.
"""
import struct
import sys

IMG_PATH = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
GP = 0xFEDF8000
FLASH_DATA_SRC = 0x86260   # flash source of .data
DATA_RAM_LO = 0xFEDF11B0   # gp - 0x6E50
DATA_RAM_HI = 0xFEDF5A68   # gp - 0x2598 (exclusive-ish, .data end)

img = open(IMG_PATH, "rb").read()
N = len(img)


def u16(off):
    return img[off] | (img[off + 1] << 8)


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def s23(v):
    v &= 0x7FFFFF
    return v - 0x800000 if v & 0x400000 else v


def opfield(hw1):
    return (hw1 >> 5) & 0x3F


def reg1(hw1):
    return hw1 & 0x1F


def reg2(hw1):
    return (hw1 >> 11) & 0x1F


# ------------------------------------------------------------------------------------------------
# Core decode: yield (off, kind, disp_signed, reg2) for every gp-relative (reg1==4) access found
# at instruction-start-aligned offsets (2-byte stride; V850 instructions are halfword-aligned).
# ------------------------------------------------------------------------------------------------
def scan_gp_accesses(lo=0, hi=None):
    hi = N - 6 if hi is None else hi
    out = []
    off = lo
    while off < hi:
        hw1 = u16(off)
        r1 = reg1(hw1)
        op = opfield(hw1)
        if r1 == 4 and op in (0x38, 0x3A, 0x39, 0x3F, 0x3B, 0x3C, 0x3D, 0x3E):
            hw2 = u16(off + 2)
            r2 = reg2(hw1)
            if op == 0x38:
                out.append((off, "ld.b", s16(hw2), r2))
            elif op == 0x3A:
                out.append((off, "st.b", s16(hw2), r2))
            elif op == 0x39:
                d = s16(hw2 & 0xFFFE)
                out.append((off, "ld.w" if (hw2 & 1) else "ld.h", d, r2))
            elif op == 0x3F:
                d = s16(hw2 & 0xFFFE)
                out.append((off, "ld.hu", d, r2))
            elif op == 0x3B:
                d = s16(hw2 & 0xFFFE)
                out.append((off, "st.w" if (hw2 & 1) else "st.h", d, r2))
            elif op in (0x3C, 0x3D):
                if r2 != 0:
                    # CRITICAL: 0x3C/0x3D with reg2!=0 is ALSO the jr/jarl encoding (Format IV/V).
                    # Discriminator (per ADV-V289-A's own documented trap): hw2 bit0 == 1 -> real
                    # ld.bu; hw2 bit0 == 0 -> this is actually jr/jarl, NOT a memory access at all.
                    if hw2 & 1:
                        d = s16(hw2 & 0xFFFE)
                        out.append((off, "ld.bu", d, r2))
                    # else: jr/jarl -- not a gp-relative access, skip
                else:
                    # 6-byte extended form; hw3 is the 3rd halfword
                    if off + 6 <= N:
                        hw3 = u16(off + 4)
                        d = s23(((hw3 << 7) | ((hw2 >> 4) & 0x7F)))
                        out.append((off, "ext6", d, None))
            elif op == 0x3E:
                out.append((off, "bitop_signed", s16(hw2), r2))
                out.append((off, "bitop_raw", hw2, r2))
        off += 2
    return out


print("Decoding whole image (this takes a little while)...")
_RAW = scan_gp_accesses()
# Convert every displacement to the positive "gp-0xNNNN" convention (d = -signed_disp).
# Only negative signed displacements are gp-0xNNNN style; positive (gp+NNNN) accesses are a
# different addressing idiom (rare/absent for our targets) and are dropped here explicitly.
ALL = []
dropped_positive = 0
for off, kind, d, r2 in _RAW:
    if d < 0:
        ALL.append((off, kind, -d, r2))
    elif d > 0:
        dropped_positive += 1
    # d == 0 (gp+0) dropped silently, not relevant to any target here
print(f"Total gp-relative candidate decodes: {len(ALL)} (dropped {dropped_positive} positive-offset gp+NNNN forms)")

# ------------------------------------------------------------------------------------------------
# Positive controls
# ------------------------------------------------------------------------------------------------
def disp_of(addr):
    return GP - addr


controls = [
    ("gp-0x3d3c (output-lag state)", 0x3d3c, {"ld.w", "st.w"}, 2, None),
    ("gp-0x6a32 (V288 state, 4 in cave + 1 orphan)", 0x6a32, {"st.h"}, 1, None),
    ("gp-0x6752/0x6757 (ld.b)", 0x6752, {"ld.b"}, 1, None),
    ("gp-0x6758 (st.b)", 0x6758, {"st.b"}, 1, None),
    ("gp-0x6c44 (cave state, ld.w+st.w)", 0x6c44, {"ld.w", "st.w"}, 2, None),
]
fails = 0
for label, disp, kinds, min_hits, _ in controls:
    hits = [a for a in ALL if a[2] == disp and a[1] in kinds]
    ok = len(hits) >= min_hits
    print(f"CONTROL {label}: disp=0x{disp:x} hits={len(hits)} (need >= {min_hits}) -> {'PASS' if ok else 'FAIL'}")
    if not ok:
        fails += 1
if fails:
    print(f"\n{fails} CONTROL(S) FAILED -- do not trust results below without fixing the decoder.")
    sys.exit(1)

# ------------------------------------------------------------------------------------------------
# Q1 -- gp-0x6a56 writer/reader census, raw scan
# ------------------------------------------------------------------------------------------------
print("\n" + "=" * 90)
print("Q1 -- gp-0x6a56 raw-scan census (all gp-relative forms)")
print("=" * 90)
target_disp = 0x6a56
hits = [a for a in ALL if a[2] == target_disp]
readers = [a for a in hits if a[1] in ("ld.b", "ld.h", "ld.w", "ld.hu", "ld.bu")]
writers = [a for a in hits if a[1] in ("st.b", "st.h", "st.w")]
bitops = [a for a in hits if a[1].startswith("bitop")]
ext = [a for a in hits if a[1] == "ext6"]
print(f"Total raw hits: {len(hits)}  (readers={len(readers)}, writers={len(writers)}, bitops={len(bitops)}, ext6={len(ext)})")
print("\n-- READERS --")
for off, kind, d, r2 in sorted(readers):
    print(f"  0x{off:06x} {kind:6s} disp=gp-0x{d:x} reg2={r2}")
print("\n-- WRITERS --")
for off, kind, d, r2 in sorted(writers):
    print(f"  0x{off:06x} {kind:6s} reg2={r2}")
if bitops:
    print("\n-- BITOPS (both interpretations; adjudicate individually) --")
    for off, kind, d, r2 in sorted(bitops):
        print(f"  0x{off:06x} {kind:12s} reg2={r2}")
if ext:
    print("\n-- EXT6 --")
    for off, kind, d, r2 in sorted(ext):
        print(f"  0x{off:06x} {kind:6s}")

print("\nExpected from Ghidra search_instructions (this session, code.bin, program-wide, 'operand_pattern:6a56'):")
print("  READERS: 0x28f4c(r7) 0x2bbaa(r21) 0x2f07a(r13) 0x34ab8(r13) 0x34e8e(r6) 0x3b49a(r9)")
print("           0x3ec2a(r11) 0x3f782(r12) 0x40b48(r9) 0x40c42(r26) 0x4d946(r14) 0x4d956(r16)")
print("           0x4de62(r14) 0x4de72(r16) 0x4e8bc(r7) 0x4e8cc(r6) 0x4fe3e(r6) 0x51850(r15)")
print("           0x557d6(r6) 0x55c62(r6)   [19 ld.h readers, all outside FUN_00028ea6 except 0x28f4c]")
print("  WRITERS: 0x3f7b8 0x3f7d0 0x3f7e0 (st.h r6,...) ; 0x3f81e (st.h r0,...)  [4, all in FUN_0003f776]")
print("  (0x46a50/0x6a48a/0x6a4aa/0x6a4d4/0x6a4fe are branch-target digit coincidences, not gp accesses -- excluded)")

# ------------------------------------------------------------------------------------------------
# Q3 -- free-RAM run scan, app .data band gp-0x6E50..gp-0x2598, exclude nothing else (already
# outside the true stack range gp-0xC000..gp-0x86E4 by construction: 0x2598 < 0x6E50 << 0x86E4)
# ------------------------------------------------------------------------------------------------
print("\n" + "=" * 90)
print("Q3 -- free-RAM run scan, disp 0x2598..0x6E50 (gp-0x6E50..gp-0x2598)")
print("=" * 90)
BAND_LO, BAND_HI = 0x2598, 0x6E50  # displacement bounds, inclusive both ends conceptually

occ = set()
for off, kind, d, r2 in ALL:
    if kind in ("bitop_signed", "bitop_raw"):
        # only count if BOTH interpretations plausible is not required; count each independently
        pass
    if BAND_LO <= d <= BAND_HI:
        occ.add(d)
    # also mark the byte(s) actually touched -- for h/w forms these span 2/4 bytes
    width = {"ld.b": 1, "st.b": 1, "ld.h": 2, "ld.hu": 2, "st.h": 2, "ld.w": 4, "st.w": 4, "ld.bu": 1}.get(kind, 1)
    for k in range(width):
        dd = d - k  # displacement counts DOWN as address increases (gp - d), so byte at addr+k is disp d-k
        if BAND_LO <= dd <= BAND_HI:
            occ.add(dd)

print(f"Occupied displacement values in band: {len(occ)} / {BAND_HI-BAND_LO+1}")

# find maximal runs of >=8 contiguous FREE displacement values (contiguous disp values == contiguous addresses)
free_runs = []
d = BAND_LO
while d <= BAND_HI:
    if d in occ:
        d += 1
        continue
    start = d
    while d <= BAND_HI and d not in occ:
        d += 1
    end = d - 1  # inclusive, disp values start..end are free (start is the LOWER disp = HIGHER address)
    length = start - end + 1  # disp counts down as address goes up; run length in bytes
    if length >= 8:
        free_runs.append((end, start, length))  # (lo_disp=addr-high side? clarify below)
    d += 1

print(f"\nMaximal free runs (>= 8 bytes), by displacement range (gp-0x{{hi_disp}} .. gp-0x{{lo_disp}}):")
print(f"Total runs found: {len(free_runs)}")


def boot_value(addr, width):
    off = FLASH_DATA_SRC + (addr - DATA_RAM_LO)
    if width == 4:
        return struct.unpack_from("<I", img, off)[0]
    elif width == 2:
        return struct.unpack_from("<H", img, off)[0]
    else:
        return img[off]


shown = 0
for lo_disp, hi_disp, length in sorted(free_runs, key=lambda x: -x[2]):
    # lo_disp = smaller displacement = HIGHER address (end of run going up)
    # hi_disp = larger displacement = LOWER address (start of run going up)
    addr_lo = GP - hi_disp  # lower address
    addr_hi = GP - lo_disp  # higher address
    bv4 = boot_value(addr_lo, 4) if length >= 4 else None
    flag = "" if (bv4 == 0 or bv4 is None) else "  <-- BOOTS NON-ZERO, FLAGGED"
    print(f"  gp-0x{hi_disp:x}..gp-0x{lo_disp:x}  ({length} bytes)  addr=0x{addr_lo:08x}..0x{addr_hi:08x}"
          f"  boot_u32@start=0x{bv4:08x}{flag}" if bv4 is not None else
          f"  gp-0x{hi_disp:x}..gp-0x{lo_disp:x}  ({length} bytes)")
    shown += 1
    if shown >= 60:
        print(f"  ... ({len(free_runs)-shown} more, truncated for display)")
        break

# adjacency check to the cave's own state gp-0x6c44..gp-0x6c39 (already occupied by cave itself)
print("\n-- Adjacency check around the cave's own state (gp-0x6c48/6c4c specifically asked) --")
for probe in (0x6c48, 0x6c4c, 0x6c50, 0x6c54, 0x6c38, 0x6c34, 0x6c30):
    occupants = [a for a in ALL if a[2] == probe]
    print(f"  gp-0x{probe:x}: {len(occupants)} raw hit(s)" + (f"  e.g. off=0x{occupants[0][0]:x} kind={occupants[0][1]}" if occupants else "  FREE"))

print("\nDone.")
