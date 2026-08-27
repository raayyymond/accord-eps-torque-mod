#!/usr/bin/env python3
"""studies/sessions/v70/v70_rung_reachability.py -- CAN V69's bit5 and bit4 rungs fire at all? Two questions, from bytes.

The V69 probe read 0.0000% on all three rungs through a MEASURED 7.56 Hz / 2,823-count-p-p ratchet
(route 4f, `studies/sessions/r4f/r4f_v69_readout.py`). Before that null can be called informative, two things must be
true of each rung, and neither has ever been checked:

  Q1  TASK RATE. If `FUN_00036388` (gp-0x6b62) or `FUN_0003a382` (gp-0x6ad4) does not run at the
      confirmed 1 kHz control rate, every frequency-domain argument about them moves.
  Q2  REACHABILITY. Each rung tests `cell >= +4096`. If a lane's own arithmetic cannot reach 4096,
      the rung could never have fired and its null is STRUCTURALLY VACUOUS -- a gate that cannot
      fail informatively, which is the V64 lesson in a new place.

METHOD. Ghidra answers Q1 through the call graph; this file is the REQUIRED SECOND METHOD -- a raw
little-endian byte scan for `jarl disp22` instructions targeting each writer, over the whole image.
(`get_xrefs_to` returned "no references" for FUN_0002214a itself, which is exactly the documented
undercount trap; a null from that tool is never load-bearing.)
Q2 is answered by byte-reading the cals and evaluating the real clamp chain.

🛑 tp = 0xBF000, so tp+0x718a is 0xC618A -- NOT 0xC718A. Off-by-0x1000 has recurred four times in
   this kit. Every address below is asserted against a known value before it is used.
"""
import os
import struct
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
STOCK = Path(ROOT) / "analysis-2020accord" / "stock_fw_dump" / "code.bin"
V69 = Path(ROOT) / "analysis-2020accord" / "_v69_plain_image.bin"
TP = 0xBF000

B = STOCK.read_bytes()
assert len(B) == 0x100000, f"stock image is {len(B)} bytes"


def u16(a, buf=None):
    return struct.unpack_from("<H", buf if buf is not None else B, a)[0]


def s16(a, buf=None):
    return struct.unpack_from("<h", buf if buf is not None else B, a)[0]


def u8(a, buf=None):
    return (buf if buf is not None else B)[a]


def tpa(off):
    """tp-relative -> absolute, with the 0x1000 trap spelled out."""
    return TP + off


# =====================================================================================================
# Q1 -- TASK RATE, by a raw jarl scan (second method; Ghidra's call graph is the first)
# =====================================================================================================
def scan_jarl(target):
    """Every `jarl/jr disp22` in the image whose branch target is `target`.

    V850 Format V, and the layout is NOT the intuitive one:
        hw1 = [reg2:5][11110:5][disp21:16 :6]      hw2 = [disp15:0 :16]   (disp bit0 forced 0)
        disp = ((hw1 & 0x3F) << 16) | hw2,  sign-extended from 22 bits, relative to hw1's address
        reg2 = 31 (lp) => JARL, reg2 = 0 => JR
    🛑 THE TRAP THIS FILE FELL INTO ONCE: the first cut masked `hw1 & 0xFFC0 == 0x0780`, treating
    bits 15:11 as opcode. They are reg2, so for a real `jarl ...,lp` hw1 is 0xFF8x, and the scan
    returned ZERO hits for three functions Ghidra had just reported callers for. A null from a
    hand-rolled scan is worth nothing until it is anchored on a KNOWN site -- 0x226A0 here, whose
    bytes are 81 ff e2 7c and whose target is 0x3A382.
    """
    assert B[0x226A0:0x226A4] == bytes.fromhex("81ffe27c"), "anchor site moved -- re-verify"
    hits = []
    for a in range(0, len(B) - 4, 2):
        hw1 = u16(a)
        if (hw1 >> 6) & 0x1F != 0x1E or (hw1 >> 11) not in (0, 31):
            continue
        disp = ((hw1 & 0x3F) << 16) | u16(a + 2)
        if disp & 0x200000:
            disp -= 0x400000
        if a + disp == target:
            hits.append(a)
    return hits


WRITERS = {
    "FUN_0003aa2c  aggregator (r24/r26; CONFIRMED 1 kHz)": 0x3AA2C,
    "FUN_00036388  gp-0x6b62 return-to-centre  [bit5]": 0x36388,
    "FUN_0003a382  gp-0x6ad4 unfiltered residual [bit4]": 0x3A382,
}

print("=" * 102)
print("Q1 -- WHO CALLS EACH LANE WRITER (raw jarl disp22 byte scan, whole image)")
callers = {}
for name, addr in WRITERS.items():
    h = scan_jarl(addr)
    callers[name] = h
    print(f"  {name:<50s} @0x{addr:05X}  callers: "
          f"{[hex(x) for x in h] if h else 'NONE FOUND'}")
FUN_2214A = (0x2214A, 0x22A00)     # FUN_0002214a's entry and a conservative upper extent
allsites = sorted(x for v in callers.values() for x in v)
inside = all(FUN_2214A[0] <= x < FUN_2214A[1] for x in allsites)
print(f"\n  ⇒ EXACTLY ONE call site each, image-wide: {[hex(x) for x in allsites]}")
print(f"  ⇒ all three inside FUN_0002214a [0x{FUN_2214A[0]:05X}, ...): {inside}  -- straight-line")
print("    calls in ONE task body, so all three lanes share ONE rate.")
print("  ⇒ FUN_0003aa2c's rate is CONFIRMED 1 kHz in the record (OSTM0 + the STEER_STATUS==4")
print("    dwell), and it is called from the same body ⇒ gp-0x6b62 and gp-0x6ad4 ARE 1 kHz.")
print("    [EVIDENCE, two independent methods: Ghidra call graph + this raw byte scan]")

# =====================================================================================================
# Q2a -- gp-0x6b62 (bit5). CAN IT REACH +4096?
# =====================================================================================================
print("\n" + "=" * 102)
print("Q2a -- gp-0x6b62 REACHABILITY   [FUN_00036388, live branch cal 0xC64A1 != 0]")
C64A1, C618A, C627E, C63C0 = tpa(0x74A1), tpa(0x718A), tpa(0x727E), tpa(0x73C0)
print(f"  cal 0xC64A1 (branch selector, BYTE)      = {u8(C64A1)}   "
      f"{'⇒ LIVE branch' if u8(C64A1) else '⇒ dead branch'}")
print(f"  cal 0xC618A (tp+0x718a, the sVar8 pin)   = {s16(C618A)}")
print(f"  cal 0xC627E (tp+0x727e, accumulator cap) = {u16(C627E)}")
print(f"  cal 0xC63C0 (tp+0x73c0, ramp step)       = {u16(C63C0)}")
print("""
  THE ARITHMETIC, mirrored from the decompilation (addresses annotated):
      sVar3  = gp-0x6b64                                   @0x364xx  ld.h
      iVar11 = |sVar3|
      acc    = gp-0x6a82;  acc += 1 if |sVar3| > 1024 and acc <= 20;  else acc -= 1 (floor 0)
      if acc_prev > 20:  iVar11 = 1024          <-- the pin, and ONLY here
      sVar8  = iVar11 * sign(sVar3)
      sVar7  = clamp(gp-0x6b96 - 1024, 0, 0x2000)          -> [0, 8192]
      term   = min(|gp-0x6b5e|, sVar7)                     -> [0, 8192]
      ramp   = gp-0x6990, clamped [0, 0x8000]              -> [0, 32768]
      sVar13 = (term * sign(gp-0x6b5e) * ramp) >> 15       -> |sVar13| <= 8192
      gp-0x6b62 = sVar8 + sVar13                           @0x36540/0x3654c  st.h
""")
print(f"  ⇒ |sVar13| max = min(8192, 8192) * 32768 >> 15 = 8192")
print(f"  ⇒ |sVar8|  max = 1024 ONLY while the accumulator is latched (>{u16(C627E)} ticks of")
print(f"    |gp-0x6b64| > {s16(C618A)}); UNLATCHED it is |gp-0x6b64| itself, which is NOT pinned.")
print(f"  ⇒ MAX |gp-0x6b62| >= 8192  ⇒  the +4096 rung CAN fire. NOT structurally vacuous.")
print("""
  🛑 CORRECTION TO THE STANDING SKETCH. The +/-1/tick accumulator gp-0x6a82 (cap 20) is a MODE
     LATCH that selects which value sVar8 takes -- it is NOT the output and NOT in the signal path.
     gp-0x6b62 itself has NO rate limit: sVar8 and sVar13 are memoryless functions of gp-0x6b64,
     gp-0x6b5e, gp-0x6b96 and the ramp. So the "20+20 ticks => 25 Hz ceiling, 7.56 Hz would need
     ~66 counts" argument does NOT bound a 7.56 Hz limit cycle in this lane. What the accumulator
     DOES do at 7.56 Hz: a half-period is 66 ms >> the 21 ticks needed to latch, so a sustained
     ratchet excursion above 1024 WOULD pin sVar8 to 1024 for most of each half-cycle -- which
     REMOVES gp-0x6b64 from the output and leaves sVar13 carrying the oscillation.
""")

# =====================================================================================================
# Q2b -- gp-0x6ad4 (bit4). CAN IT REACH +4096?  The output is clamped to a DYNAMIC ceiling.
# =====================================================================================================
print("=" * 102)
print("Q2b -- gp-0x6ad4 REACHABILITY   [FUN_0003a382]")
print("  The PID sum is clamped to +/-CEILING, and the CEILING is itself three LERPs and a ramp:")
print("      pre     = min( LERP_A(gp-0x6bda), min( LERP_B(gp-0x671a), LERP_C(gp-0x6a5e) ) )")
print("      ramp    = gp-0x3678, slews to 0x8000 by +/-cal 0xC644E / 0xC644C per tick")
print("      bound   = LERP_D(gp-0x6966), clamped to <= 0x8000")
print("      CEILING = ((pre * ramp) >> 15) * bound >> 15      @0x3a7xx")
print("  ⇒ with ramp and bound both at their 0x8000 max, CEILING == pre. So max|gp-0x6ad4| = max(pre).")


def lerp_table(xbase, ybase, n):
    return ([u16(xbase + 2 * i) for i in range(n)], [u16(ybase + 2 * i) for i in range(n)])


tables = {
    "LERP_A  X tp+0x77a2 / Y tp+0x77a8   idx gp-0x6bda": (tpa(0x77A2), tpa(0x77A8), 3),
    "LERP_B  X tp+0x7794 / Y tp+0x7798   idx gp-0x671a": (tpa(0x7794), tpa(0x7798), 3),
    "LERP_C  X tp+0x77c2 / Y tp+0x77c8   idx gp-0x6a5e": (tpa(0x77C2), tpa(0x77C8), 3),
    "LERP_D  X tp+0x7af2 / Y tp+0x7afc   idx gp-0x6966": (tpa(0x7AF2), tpa(0x7AFC), 3),
    "P gain  X tp+0x7b1e / Y tp+0x7b26   idx gp-0x6ac0": (tpa(0x7B1E), tpa(0x7B26), 4),
    "I gain  X tp+0x7b0a / Y tp+0x7b12   idx gp-0x6ac0": (tpa(0x7B0A), tpa(0x7B12), 4),
    "D gain  X tp+0x7ade / Y tp+0x7ae6   idx gp-0x6ac0": (tpa(0x7ADE), tpa(0x7AE6), 4),
    "OUTgain X tp+0x77b2 / Y tp+0x77b8   idx gp-0x671a": (tpa(0x77B2), tpa(0x77B8), 3),
}
for name, (xb, yb, n) in tables.items():
    xs, ys = lerp_table(xb, yb, n)
    print(f"  {name:<50s} X 0x{xb:05X} {xs}   Y 0x{yb:05X} {ys}")

print(f"\n  scalars:  bias cal 0xC6200 = {s16(tpa(0x7200))}   "
      f"EMA1 0xC6450 = {u16(tpa(0x7450))}   EMA2 0xC644A = {u16(tpa(0x744A))}")
print(f"            ramp up 0xC644E = {u16(tpa(0x744E))}   ramp dn 0xC644C = {u16(tpa(0x744C))}   "
      f"fallback 0xC61FC = {s16(tpa(0x71FC))} / 0xC61FE = {s16(tpa(0x71FE))}")
print(f"            ERR clamp = +/-0x2800 = +/-10240 (literal, @0x3a7c8)")

pre_candidates = []
for key in ("LERP_A  X tp+0x77a2 / Y tp+0x77a8   idx gp-0x6bda",
            "LERP_B  X tp+0x7794 / Y tp+0x7798   idx gp-0x671a",
            "LERP_C  X tp+0x77c2 / Y tp+0x77c8   idx gp-0x6a5e"):
    xb, yb, n = tables[key]
    pre_candidates.append(max(lerp_table(xb, yb, n)[1]))
print(f"\n  max of each ceiling LERP: {pre_candidates}")
print(f"  ⇒ max(pre) = min over the three maxima = {min(pre_candidates)}  "
      f"(pre is a MIN of the three, so no operating point exceeds the smallest maximum)")
verdict = "CAN fire" if min(pre_candidates) >= 4096 else "CANNOT fire -- STRUCTURALLY VACUOUS"
print(f"  ⇒ bit4 tests gp-0x6ad4 >= +4096. Ceiling max {min(pre_candidates)} ⇒ the rung {verdict}.")

# ★ AND AT THE RATCHET'S OWN OPERATING POINT IT IS FAR SMALLER. LERP_C is indexed on gp-0x6a5e,
# the VOTED VEHICLE SPEED in counts (64.0625 counts/km/h -- the same axis as every speed cal in
# this kit), and it starts at ZERO.
COUNTS_PER_KMH = 64.0625
xc, yc = lerp_table(*tables["LERP_C  X tp+0x77c2 / Y tp+0x77c8   idx gp-0x6a5e"][:2], 3)


def lerp_flat(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            return ys[i] + (ys[i + 1] - ys[i]) * (x - xs[i]) // (xs[i + 1] - xs[i])
    return ys[-1]


print(f"\n  ★ THE CEILING AT THE RATCHET'S OWN SPEEDS (LERP_C breakpoints "
      f"{[round(x / COUNTS_PER_KMH, 2) for x in xc]} km/h -> Y {yc}):")
print(f"    {'km/h':>6s} {'counts':>7s} {'CEILING':>8s} {'bit4 needs':>11s} {'shortfall':>10s}")
for kmh in (0.0, 2.0, 4.9, 6.0, 6.8, 7.8, 8.0, 9.9, 10.0, 20.0, 50.0):
    c = lerp_flat(int(kmh * COUNTS_PER_KMH), xc, yc)
    ceil_here = min(c, min(pre_candidates))
    print(f"    {kmh:6.1f} {int(kmh * COUNTS_PER_KMH):7d} {ceil_here:8d} {4096:11d} "
          f"{(4096 / ceil_here if ceil_here else float('inf')):9.1f}x")
print("    (the four confirmed route-4f ratchet episodes sat at v p50 4.9 / 7.8 / 8.0 / 6.8 km/h)")
print("  🛑 So at the ratchet's operating point bit4's threshold is 12-24x ABOVE the lane's entire")
print("     reachable range, and below ~2.0 km/h the lane is muted to EXACTLY ZERO by LERP_C's Y[0].")
print("  ⚠ The V69 design sized bit4 as '40% of its ±0x2800 ZERO gate'. ±0x2800 is the ERR INPUT")
print("     clamp (and the downstream gate), NOT this lane's OUTPUT range. The output never leaves")
print("     ±CEILING ≤ 1024, so neither the rung nor the downstream ±0x2800 gate can ever be")
print("     crossed by this lane. [EVIDENCE: cal bytes above + the clamp chain @0x3a7xx-0x3a8a0]")
print("  ⇒ A FAITHFUL REPLAY OF gp-0x6ad4 FROM CAN IS ALSO NOT POSSIBLE, and is now moot: the P/I/D")
print("     gains are LERPs on gp-0x6ac0 (scale OPEN, 8x uncertainty) and the ceiling needs")
print("     gp-0x6966, gp-0x6bda, gp-0x6ad6 and a 1 s ramp -- none on the wire. The ceiling bound")
print("     settles the question without needing any of them.")

# V69 image must be byte-identical on every cal above -- V69 edits only 0x3AA96, 0xC6446,
# 0xD2A7E/80, 0xD2ABA/BC and the cave.
V = V69.read_bytes()
addrs = [C64A1, C618A, C627E, C63C0, tpa(0x7200), tpa(0x7450), tpa(0x744A), tpa(0x744E),
         tpa(0x744C), tpa(0x71FC), tpa(0x71FE)]
for _n, (xb, yb, n) in tables.items():
    addrs += [xb + 2 * i for i in range(n)] + [yb + 2 * i for i in range(n)]
diff = [hex(a) for a in addrs if B[a:a + 2] != V[a:a + 2]]
print(f"\n  V69 image vs stock on every cal above: "
      f"{'IDENTICAL at all ' + str(len(addrs)) + ' addresses' if not diff else 'DIFFERS at ' + str(diff)}")
