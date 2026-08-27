#!/usr/bin/env python3
"""Was the ONE surviving V73 lever -- `0xC407E` 511 -> 850 -- able to do anything?

CONTEXT. The orchestrator has corrected the mode reading: V73's 4-bit probe field dropped bit 4, the
true modes are **24 (manual) / 26 (engaged)**, and V73's friction LERP edit at `0xD2A44` is mode-10's
record, which this car never reads. ⇒ EDIT 1's LERP half was INERT. `0xC407E` is a scalar `tp` cell
read unconditionally by FUN_00036c12, so it acted in every mode -- but raising a CLAMP only changes
behaviour where the lane was ALREADY CLIPPING at +-511.

🛑 THIS IS A BYTE QUESTION, NOT A BUS QUESTION. Nothing on CAN carries the friction lane's output.
What CAN be settled exactly, in Python on the shipped images (the kit's required second method):

  1. VERIFY THE CORRECTION MYSELF. Read `0xCBE74[mode*4]` for mode 10 and mode 26 out of the image.
     If they differ, V73's LERP edit provably missed the record the car reads. Read the config-row
     table at 0xCD000 (stride 0x24, mode fields +0x12..+0x15) and check row 11 / the alias set.
  2. READ MODE 26's OWN friction record -- the X axis and the Y values the car ACTUALLY uses.
  3. COMPUTE THE LANE, exactly as the decompile states it, and find the input magnitude at which the
     +-511 clamp first binds:
         out = ((gate * Y_speed) >> 6) * 273 >> 18,  clamped to +-*(short *)(tp+0x507e)
     Integer `>>`, LE byte reads, addresses annotated -- the arithmetic, then the interpretation.

If the clamp cannot bind for any reachable input, the surviving half of EDIT 1 was inert too and
**V73 is spectrally identical to V72 by construction** -- which is exactly what the band scorecard
measured (0.874 [0.621, 1.144], control band moving identically).
"""
import os
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                           "C:/Users/dudei/Desktop/Projects/accord-firmwares")) / "analysis-2020accord"
TP = 0xBF000
PTR_ARRAY = 0xCBE74          # friction record pointer array, indexed [mode * 4]
ROW_TABLE = 0xCD000          # config rows, stride 0x24, mode fields at +0x12..+0x15
ROW_STRIDE = 0x24
CLAMP_ADDR = 0xC407E         # tp+0x507E
FRICTION_FN = 0x36C12


def u16(b, a):
    return int(b[a]) | (int(b[a + 1]) << 8)


def s16(b, a):
    v = u16(b, a)
    return v - 0x10000 if v & 0x8000 else v


def u32(b, a):
    return int.from_bytes(b[a:a + 4], "little")


def hdr(s):
    print(f"\n{'=' * 104}\n{s}\n{'=' * 104}")


imgs = {}
for tag, name in (("stock", "stock_fw_dump"), ("V72", "_v72_plain_image.bin"),
                  ("V73", "_v73_plain_image.bin")):
    p = ROOT / name
    if p.is_dir():
        cand = sorted(p.glob("*.bin"))
        p = cand[0] if cand else None
    if p and p.exists():
        imgs[tag] = bytearray(p.read_bytes())
        print(f"{tag:6s} {p.name}  {len(imgs[tag])} bytes")
    else:
        print(f"{tag:6s} NOT FOUND at {p}")
if "V73" not in imgs:
    sys.exit("no V73 image -- cannot proceed")
V73 = imgs["V73"]
BASE = imgs.get("V72", V73)

# ------------------------------------------------------------------ 1. verify the correction -----
hdr("1. VERIFY THE MODE CORRECTION MYSELF -- the record pointer array and the config-row table")
print(f"friction record pointer array @0x{PTR_ARRAY:05X}, entry = ptr[mode * 4], read LE:\n")
print(f"  {'mode':>5s} {'addr of entry':>14s} {'-> record':>12s}   note")
ptrs = {}
for m in list(range(16)) + [24, 25, 26, 27, 32, 33]:
    a = PTR_ARRAY + m * 4
    if a + 4 > len(V73):
        print(f"  {m:5d}  entry 0x{a:05X} is PAST THE IMAGE END -- mode not representable")
        continue
    p = u32(V73, a)
    ptrs[m] = p
    note = ""
    if m == 10:
        note = "<-- V73 EDIT 1's target"
    if m in (24, 26):
        note = "<-- the CORRECTED true mode" + (" (engaged)" if m == 26 else " (manual)")
    plaus = "" if 0xC0000 <= p < 0x100000 else "   ⚠ NOT a plausible cal pointer"
    print(f"  {m:5d}     0x{a:05X}     0x{p:06X}   {note}{plaus}")
print()
if 10 in ptrs and 26 in ptrs:
    same = ptrs[10] == ptrs[26]
    print(f"  ptr[mode 10] = 0x{ptrs[10]:06X}   ptr[mode 26] = 0x{ptrs[26]:06X}   "
          f"{'SAME RECORD' if same else '**DIFFERENT RECORDS**'}")
    print(f"  ⇒ V73's EDIT 1 LERP half was {'LIVE' if same else 'INERT'} on a mode-26 car "
          f"[EVIDENCE, byte read]")

print(f"\nconfig-row table @0x{ROW_TABLE:05X}, stride 0x{ROW_STRIDE:02X}, mode fields at +0x12..+0x15:")
print(f"  {'row':>4s} {'row addr':>10s} {'part/ID bytes 0..7':>28s} {'modes +0x12..+0x15':>22s}"
      f"   aliases &0xF")
alias_rows = []
for r in range(20):
    a = ROW_TABLE + r * ROW_STRIDE
    if a + ROW_STRIDE > len(V73):
        break
    ident = V73[a:a + 8]
    txt = "".join(chr(c) if 32 <= c < 127 else "." for c in ident)
    modes = [int(V73[a + 0x12 + k]) for k in range(4)]
    al = [m & 0xF for m in modes]
    mark = ""
    if al[0] == 8 and 10 in al:
        mark = "  <-- ALIASES TO (8, 10)"
        alias_rows.append((r, txt, modes))
    print(f"  {r:4d}  0x{a:05X} {txt:>28s} {str(modes):>22s}   {str(al)}{mark}")
print(f"\n  rows whose mode set aliases to (8, ..., 10) under &0xF: "
      f"{[(r, t, m) for r, t, m in alias_rows]}")
print("  🛑 If exactly one row does, the correction is forced. If several do, the probe cannot")
print("     discriminate them and the mode identification rests on the part number, not the data.")
raw8 = [r for r in range(20)
        if ROW_TABLE + r * ROW_STRIDE + 0x16 <= len(V73)
        and 8 in [int(V73[ROW_TABLE + r * ROW_STRIDE + 0x12 + k]) for k in range(4)]]
print(f"  rows containing the RAW value 8 in any mode field: {raw8}  "
      f"({'none ⇒ a raw-8 reading is impossible ⇒ the field aliased' if not raw8 else 'see above'})")

# ------------------------------------------------------------------ 2. mode 26's record ----------
hdr("2. THE FRICTION RECORD THE CAR ACTUALLY READS (mode 26) vs THE ONE V73 EDITED (mode 10)")
# layout from the build script, re-read here rather than trusted: count@+0, X@+2, Y@+8, term@+0x0E
KMH = 64.0          # counts of voted vehicle speed per km/h


def readrec(img, addr, npt=3):
    n = u16(img, addr)
    X = [s16(img, addr + 2 + 2 * i) for i in range(npt)]
    Y = [s16(img, addr + 8 + 2 * i) for i in range(npt)]
    return n, X, Y


for lab, m in (("mode 10 (V73's target)", 10), ("mode 26 (THE CAR)", 26),
               ("mode 24 (manual)", 24)):
    if m not in ptrs:
        continue
    a = ptrs[m]
    if not (0xC0000 <= a < 0x100000):
        print(f"  {lab:24s} ptr 0x{a:06X} is not a plausible record address -- SKIPPED")
        continue
    for tag, img in (("V73", V73), ("base", BASE)):
        n, X, Y = readrec(img, a)
        if tag == "V73":
            print(f"  {lab:24s} @0x{a:06X}  npt={n}  "
                  f"X={X} counts = {[round(x / KMH, 1) for x in X]} km/h")
        print(f"      {tag:5s} Y = {Y}")
    print()

# ------------------------------------------------------------------ 3. does the clamp bind? ------
hdr("3. CAN THE +-511 CLAMP EVER BIND?  the lane's own integer arithmetic, swept")
cl73 = s16(V73, CLAMP_ADDR)
cl72 = s16(BASE, CLAMP_ADDR)
print(f"  clamp *(short *)(tp+0x{CLAMP_ADDR - TP:04X}) @0x{CLAMP_ADDR:05X}: "
      f"base {cl72}   V73 {cl73}   [EVIDENCE, byte read]")
print(f"  lane @0x{FRICTION_FN:05X}:  out = ((gate * Y_speed) >> 6) * 273 >> 18, "
      f"clamped symmetrically to +-clamp\n")


def lane(gate, Y, clamp):
    """EXACTLY the decompiled arithmetic. Integer >>, V850 arithmetic shift (floor)."""
    t = (int(gate) * int(Y)) >> 6
    t = (t * 273) >> 18
    return max(-clamp, min(clamp, t)), t


if 26 in ptrs and 0xC0000 <= ptrs[26] < 0x100000:
    _, X26, Y26 = readrec(V73, ptrs[26])
else:
    X26, Y26 = None, None
    print("  ⚠ mode 26's record is not readable -- the sweep below uses mode 10's Y as a stand-in")
    _, X26, Y26 = readrec(V73, ptrs[10])

Yuse = min(Y26, key=lambda y: y)      # the largest-MAGNITUDE (most negative) Y = the 0 km/h end
print(f"  worst-case (largest |Y|) point of the car's own record: Y = {Yuse} "
      f"at {X26[Y26.index(Yuse)] / KMH:.0f} km/h\n")
print(f"  {'|gate| input':>14s} {'raw lane out':>13s} {'clipped @511':>13s} {'clipped @850':>13s}"
      f"   binds?")
prev = None
first511 = first850 = None
for g in (16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 12800, 16384, 32767):
    _, raw = lane(g, Yuse, 10 ** 9)
    c5 = max(-511, min(511, raw))
    c8 = max(-850, min(850, raw))
    b = ("511 BINDS" if abs(raw) > 511 else "-") + (" | 850 BINDS" if abs(raw) > 850 else "")
    print(f"  {g:14d} {raw:13d} {c5:13d} {c8:13d}   {b}")
    if first511 is None and abs(raw) > 511:
        first511 = g
    if first850 is None and abs(raw) > 850:
        first850 = g
# exact threshold by bisection on the integer function
def thr(limit):
    lo, hi = 0, 1 << 20
    while lo < hi:
        mid = (lo + hi) // 2
        if abs(lane(mid, Yuse, 10 ** 9)[1]) > limit:
            hi = mid
        else:
            lo = mid + 1
    return lo


t511, t850 = thr(511), thr(850)
print(f"\n  EXACT: |gate| must exceed {t511} counts for the 511 clamp to bind, "
      f"and {t850} for 850. [EVIDENCE, integer sweep of the decompiled expression]")
print(f"  ⇒ the V73 raise only changes the output for |gate| in ({t511}, {t850}] -> a window of "
      f"{t850 - t511} counts, and adds at most {850 - 511} counts above it.")
print("\n  🛑 WHAT `gate` IS: the gated `gp-0x6c2c`, the MOTOR-RATE DERIVATIVE (kit memory:")
print("     `accord-gp6c2c-is-motor-rate-derivative`, which also records that tripping the")
print("     detector's T=12800 needs ~1683 counts at 21.3 Hz). It is NOT observable on route 5a --")
print("     V73's probe field is spent on the mode byte -- so whether the car reaches these")
print("     magnitudes at creep is [UNMEASURED], and this file does not claim it either way.")
print("     A one-rung probe on |gp-0x6c2c| >= {} would settle it in one drive.".format(t511))

# ------------------------------------------------------------------ 4. the diff, for the record --
hdr("4. V73 vs V72 -- the functional byte diff, attributed")
d = [i for i in range(len(V73)) if V73[i] != BASE[i]]
print(f"  {len(d)} differing bytes total")
groups = {}
for i in d:
    k = ("EDIT 1 LERP 0xD2A44 Y[]" if 0xD2A4C <= i <= 0xD2A51 else
         "EDIT 1 clamp 0xC407E" if i in (CLAMP_ADDR, CLAMP_ADDR + 1) else
         "cave / probe" if 0x55A00 <= i <= 0x55D00 else "other (ratchet cells / CRC)")
    groups.setdefault(k, []).append(i)
for k, v in sorted(groups.items()):
    print(f"    {k:28s} {len(v):4d} bytes   first 0x{v[0]:05X}  last 0x{v[-1]:05X}")
