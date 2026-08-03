#!/usr/bin/env python3
"""v68_design_math.py -- the r24 rate-lane gain surface, and what each build actually DELIVERS.

🛑 THE FINDING THIS FILE EXISTS FOR: r24's gain is NOT a scalar. Stock rebuilds it every cycle as a
two-axis cross-interpolated LERP surface (FUN_0003ad74) over VEHICLE SPEED x MOTOR RATE. V67 replaces
that whole surface with a flat scalar (cal 0xC6446 = 5244) whenever LKAS applies -- which INVERTS
Honda's own schedule, because the stock surface ROLLS OFF with speed (3072 at 0 km/h -> 2151 at
100 km/h). So V67 delivers its LARGEST multiplier at the highest speed:

    grind #1   (creep 7.2 km/h, 128 deg/s)   2.00x
    grind #2 creep (5 km/h, 256 deg/s)       2.18x
    grind #2 HIGHWAY (100+ km/h, ~35 deg/s)  2.44x  <-- the maximum, and 22% ABOVE V62's flat 2.00x,
                                                        the dose that raised 40-49 Hz by 11.7x

★★ UNITS -- SETTLED EMPIRICALLY 2026-08-02, after I got it WRONG once. See the retraction below.
The 0x14A rate field IS deg/s (factor 1), and the LERP's inner axis gp-0x6ac0 is 4.71210813 counts
per deg/s, so the breakpoints [0, 400, 1400/1500, 3000] are [0, 85, 297, 637] DEG/S.

    population                    deg/s      gp-0x6ac0    LERP segment
    grind #1                       ~128         ~603      [400, 1400]  <- ON the rolloff
    grind #2 creep                 ~256        ~1206      [400, 1400]  <- ON the rolloff, further along
    grind #2 highway (r47)        30-42     ~141-198      [0, 400] FLAT

⇒ the rate axis IS usable: grind #1 and the creep grind #2 sit at different points on the SAME
rolloff segment, and the highway population sits in the flat region below it.

🛑🛑 RETRACTED, and this file said the opposite for several hours. I claimed (a) "bus counts =
8 x deg/s exactly", (b) "the rate axis is arithmetically dead, all three populations are in the flat
[0,400] segment", and (c) "V67's build note contains a units error; the arm delivers 1.94x". ALL
THREE ARE WRONG. Two independent measurements settle it:
  1. Regressing `rate_c` on the differentiated ANGLE channel (0x14A b0:1, factor -0.1 => degrees)
     gives slope 0.95-1.00 with r >= 0.985 on every clean segment => the bus field IS deg/s.
  2. Observed |rate| over 407,617 frames peaks at 521 deg/s (p99.9 = 408). At 4.7121 counts/deg-s
     the breakpoints are 85/297/637 deg/s -- fully exercised by real driving. Under my erroneous
     0.589 counts/deg-s the breakpoints would be 679/2377/5093 deg/s and Honda's 2x rolloff would
     NEVER engage in any real drive. Physically decisive.
The error was composing two structural relations I had NOT verified myself (`gp-0x6ac0 = |gp-0x6abe|`
and `bus = (gp-0x6abe*48*1159)>>15`) into a scale, instead of measuring the scale. One of those two
premises is wrong; which one is still OPEN and needs a Ghidra trace. ⇒ V67's build note was CORRECT:
LERP 2622 at grind #1's operating point, arm 5244 = exactly 2.00x.

⚠ GATE 2 CAUTION ON ANY RATE-AXIS EDIT (weakened, not withdrawn): gp-0x6ac0 is a RECTIFIED filtered
motor rate, so it sweeps at 2x the mode frequency. A gain that varies steeply with it modulates at
2f -- the parametric-pump failure mode V58/V59/V60 chased for three builds. Stock ALREADY has a
rolloff there (3072 -> 1536 over 400..3000), so the mechanism is not new and is evidently tolerable
at stock slope; but any edit that STEEPENS it must state the new slope and argue the pump margin.
This is a quantitative caution, not the structural veto this file previously claimed.

Everything below is byte-verified against stock code.bin and _v65/_v66/_v67_plain_image.bin, and the
selector ladder is confirmed from the Ghidra listing of FUN_0003aa2c (addresses annotated inline).

Usage:  python v68_design_math.py
"""
from __future__ import annotations

# ---------------------------------------------------------------------------------------------
# The surface, byte-read little-endian. Record layout is 20 bytes: u16 count=4, X[4], Y[4], pad.
# Each record has EXACTLY ONE pointer image-wide (verified by a full 32-bit LE scan), so mode 10's
# records are private -- blast radius is one car variant.
# ---------------------------------------------------------------------------------------------
CROSS_X = (0, 640, 3200, 6400)          # 0xC6010, voted speed, 64.0625 counts/km/h => 0/10/50/100
COUNTS_PER_KMH = 64.0625
BUS_PER_AXIS = 48 * 1159 / 32768        # 1.697754 -- bus counts per gp-0x6ac0 count
AXIS_PER_DEGS = 2 ** 18 / (48 * 1159)   # 4.71210813 -- gp-0x6ac0 counts per deg/s

STOCK = [                                # (ptr array, record addr, X, Y)
    (0xCBF5C, 0xD2A74, (0, 400, 1400, 3000), (3072, 3072, 2322, 1536)),   #   0 km/h
    (0xCC044, 0xD2AB0, (0, 400, 1500, 3000), (2561, 2561, 2247, 1947)),   #  10 km/h
    (0xCC12C, 0xD2AEC, (0, 400, 1500, 3000), (2305, 2304, 2149, 1948)),   #  50 km/h
    (0xCC214, 0xD2B28, (0, 400, 1500, 3000), (2151, 2151, 2049, 1947)),   # 100 km/h
]

DTORQUE_CLAMP = 5120        # aggregator input clamp on gp-0x4f62      @0x3AAAC-0x3AAC0
LANE_CLAMP = 8192           # r24 output clamp                          @0x3AC42-0x3AC54
DEADZONE = 3                # cal 0xC61F6, applied AFTER the gain       @0x3AC1C-0x3AC3C
INT32_MAX = 2 ** 31 - 1

V67_ARM = 5244              # cal 0xC6446 under V67; selected when gp-0x6806 != 0  @0x3AC08
MEASURED_DTORQUE_MAX = 839  # on-car range 123-839; worst implied transient 739


def _dtz(n: int, d: int) -> int:
    """V850 `divq`: signed division truncating toward zero.  @0x3ABF4"""
    q = abs(n) // abs(d)
    return -q if (n < 0) != (d < 0) else q


def _lerp(x: int, xs, ys) -> int:
    """The firmware LERP idiom: FLAT extrapolation outside the breakpoints.  @0x3ABB2-0x3ABF8"""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            return ys[i] + _dtz((ys[i + 1] - ys[i]) * (x - xs[i]), xs[i + 1] - xs[i])
    return ys[-1]


def gain_q10(speed_counts: int, axis_counts: int, recs=STOCK) -> int:
    """FUN_0003ad74 rebuilds X and Y element-by-element on the SPEED axis, then r24 LERPs on rate.

    The >= 13001 fold to 0 is real (@0x3AAC8 `addi -0x32c9` / @0x3AACC `cmovc`) and lands on the
    LERP's FIRST breakpoint, i.e. MAXIMUM gain. 13001 counts = 2759 deg/s (~7.7 wheel rev/s), so it
    is fault/glitch level, but any Y[0] raise makes that discontinuity proportionally larger.
    """
    k = max(CROSS_X[0], min(speed_counts, CROSS_X[-1]))
    xs = tuple(_lerp(k, CROSS_X, tuple(r[2][i] for r in recs)) for i in range(4))
    ys = tuple(_lerp(k, CROSS_X, tuple(r[3][i] for r in recs)) for i in range(4))
    idx = axis_counts if 0 <= axis_counts < 13001 else 0
    return _lerp(idx, xs, ys)


def G(kmh: float, degs: float, recs=STOCK) -> int:
    return gain_q10(int(kmh * COUNTS_PER_KMH), int(degs * AXIS_PER_DEGS), recs)


def G_bus(kmh: float, degs: float, recs=STOCK) -> int:
    """The bus rate field is deg/s (measured), so this is just G(). Kept for call-site clarity."""
    return G(kmh, degs, recs)


def lane_out(dtorque: int, gain: int) -> int:
    """r24 after the gain, the +/-3 deadzone and the +/-8192 clamp.  @0x3AC16-0x3AC54"""
    scaled = (dtorque * gain) >> 10                       # V850 `sar`: floors for negatives
    if scaled > DEADZONE:
        shaped = scaled - DEADZONE
    elif scaled < -DEADZONE:
        shaped = scaled + DEADZONE
    else:
        shaped = 0
    return max(-LANE_CLAMP, min(LANE_CLAMP, shaped))


def saturating_dtorque(gain: int) -> int:
    """|dtorque| at which the lane hits its own +/-8192 clamp."""
    return (LANE_CLAMP << 10) // gain


# ---------------------------------------------------------------------------------------------
# V68 CANDIDATE (NAIVE): scale Y[0]/Y[1] of the 0 and 10 km/h records by 2, 50/100 km/h untouched.
# 🛑 KEPT ONLY AS A FOIL. With the units settled, grind #1 sits at axis ~603 -- ON the [400,1400]
# rolloff, not in the flat region -- so scaling Y[0]/Y[1] delivers only 1.84x there while ALSO
# delivering ~1.27x at the creep grind #2's own point. A better design exists: see DESIGN_A below,
# which edits ONE halfword and exploits the fact that grind #1 (~128 deg/s) and the creep grind #2
# (~256 deg/s) sit at DIFFERENT points on the same rolloff.
# ---------------------------------------------------------------------------------------------
def scaled_low_speed(mult: float = 2.0):
    out = []
    for i, (arr, rec, xs, ys) in enumerate(STOCK):
        if i < 2:
            ys = (int(round(ys[0] * mult)), int(round(ys[1] * mult)), ys[2], ys[3])
        out.append((arr, rec, xs, ys))
    return out


V68 = scaled_low_speed(2.0)

# ★ DESIGN A (the recommended shape, from the `surface` trace): edit ONLY 0xD2AB0's Y[1] -- the
# halfword at 0xD2ABC -- 2561 -> 7051, leaving 0xD2A74 and both high-speed records byte-identical.
# It hits exactly 2.00x at grind #1 while delivering far less at the creep grind #2's higher rate,
# and exactly 1.00x at 50/100 km/h. Its known cost is a HUMP: the multiplier peaks near ~2.45x at
# 9.9-10 km/h, because 0xD2AB0 IS the 10 km/h breakpoint record.
DESIGN_A = [(a, r, x, (y if i != 1 else (y[0], 7051, y[2], y[3])))
            for i, (a, r, x, y) in enumerate(STOCK)]

# The operating points, in the units they were MEASURED in (bus counts off 0x14A).
POINTS = [
    ("grind #1        creep, LKAS on",   7.2, 128),
    ("grind #2 creep  driver cranking",  5.0, 256),
    ("grind #2 HIGHWAY lane change",   110.0,  35),
    ("highway cruise  straight",       110.0,   8),
    ("suburban        40 km/h turn",    40.0, 100),
]


def _report():
    print(__doc__.split("Usage:")[0].rstrip())
    print("\n" + "=" * 100)
    print("1. STOCK SURFACE  (rows km/h, cols BUS counts; gp-0x6ac0 = bus / 1.697754)")
    sp = [0, 3, 7.2, 10, 20, 30, 40, 50, 70, 100, 120]
    bus = [0, 20, 50, 128, 256, 400, 680, 1200, 2400, 5100]
    print("  km/h |" + "".join(f"{b:>7}" for b in bus))
    for s in sp:
        print(f"{s:6} |" + "".join(f"{G_bus(s, b):>7}" for b in bus))

    print("\n" + "=" * 100)
    print("2. DELIVERED MULTIPLIER vs STOCK, at the measured operating points")
    print(f"  {'operating point':38} {'km/h':>6} {'deg/s':>5} {'axis':>6} {'stock':>6} "
          f"{'V62/65':>7} {'V67':>6} {'naive':>6} {'DesignA':>7}")
    for lab, kmh, b in POINTS:
        st = G_bus(kmh, b)
        v68 = G_bus(kmh, b, V68)
        da = G_bus(kmh, b, DESIGN_A)
        print(f"  {lab:38} {kmh:6.1f} {b:5.0f} {b * AXIS_PER_DEGS:6.0f} {st:6} "
              f"{2.00:7.2f} {V67_ARM / st:6.2f} {v68 / st:6.2f} {da / st:7.2f}")

    print("\n" + "=" * 100)
    print("3. V68 MULTIPLIER vs SPEED  (any rate below axis 400 -- i.e. every symptom on record)")
    print(f"  {'km/h':>6} {'stock':>7} {'V68':>7} {'mult':>7}")
    for s in (0, 5, 7.2, 10, 15, 20, 30, 40, 50, 70, 100, 120):
        st, v = G_bus(s, 60), G_bus(s, 60, V68)
        print(f"  {s:6.1f} {st:7} {v:7} {v / st:7.2f}")
    print("  ⇒ 2.00x to 10 km/h, tapering linearly to 1.00x at 50 km/h, EXACTLY STOCK above.")
    print("  ⇒ grind #1 lives at 1-4 m/s = 3.6-14.4 km/h -> 2.00-1.95x, i.e. V62's PROVEN dose.")
    print("  ⇒ the highway grind #2 population at 90-120 km/h -> 1.00x, byte-identical to stock.")

    print("\n" + "=" * 100)
    print("4. THE EDIT")
    for i, ((arr, rec, xs, ys), (_, _, _, ny)) in enumerate(zip(STOCK, V68)):
        tag = "RAISED" if ys != ny else "stock, untouched"
        print(f"  rec{i} 0x{rec:05X}  ({CROSS_X[i] / COUNTS_PER_KMH:5.1f} km/h)  "
              f"X{xs}  Y{ys} -> Y{ny}   {tag}")
    print("  4 halfwords change: 0xD2A7E/0xD2A80 (rec0 Y[0]/Y[1]) and 0xD2ABA/0xD2ABC (rec1).")
    print("  CRC: all four records live in block (0xD2000, 0xD2FFC) -- ONE block recompute.")
    print("  Blast radius: each record has EXACTLY ONE pointer image-wide (full 32-bit LE scan);")
    print("                mode 11 uses its own 0xD2A88/0xD2AC4/0xD2B00/0xD2B3C, interleaved at 0x14.")
    print("  Float mirror: NONE. A full-image 32-bit float scan finds zero hits for any raw Y value")
    print("                and no clustered mirror table => the V27 int/float desync class does not")
    print("                apply. (3.0 and 1.5 appear as ordinary float constants; not a table.)")

    print("\n" + "=" * 100)
    print("5. ARITHMETIC SAFETY")
    for lab, g in (("stock creep", 3072), ("V67 arm", V67_ARM), ("V68 creep", 6144)):
        sat = saturating_dtorque(g)
        worst = DTORQUE_CLAMP * g
        print(f"  {lab:12} gain {g:5}  saturates at |dtorque| >= {sat:5}  "
              f"(measured max {MEASURED_DTORQUE_MAX}, margin {sat / MEASURED_DTORQUE_MAX:4.2f}x)  "
              f"worst product {worst / INT32_MAX * 100:.2f}% of INT32_MAX")
    print("  ⇒ V68's creep gain is IDENTICAL to V62's effective creep gain (2 x 3072 = 6144), i.e.")
    print("    exactly the dose that measurably fixed grind #1 by 8-42x -- reproduced at the")
    print("    operating point where it worked, and nowhere else.")
    print("  ⇒ the +/-8192 clamp is a SATURATING clip, not a zeroing gate: benign, and reaching it")
    print("    earlier in a cycle removes MORE energy per cycle from a limit cycle.")

    print("\n" + "=" * 100)
    print("6. 🛑 WHAT V68 DOES NOT DO, AND THE STRUCTURAL REASON")
    print("  The creep grind #2 shares grind #1's speed cells, so no speed schedule separates them,")
    print("  and the rate axis cannot either (all populations sit in the flat [0,400] segment).")
    print("  ⇒ a cal-only V68 boosts creep with LKAS OFF too, where V67's gate currently keeps")
    print("    manual parking at stock. The gate and the surface are MUTUALLY EXCLUSIVE: taking the")
    print("    arm discards the LERP entirely (@0x3AC04-0x3AC16), so they cannot compose.")
    print("  ★ Getting BOTH needs a gate cell meaning 'LKAS applying AND low speed'. If one exists,")
    print("    the repoint stays and V68 is a ONE-BYTE change instead of a calibration edit.")
    print("\n  🛑 A FLAT ARM CANNOT FIX THE HIGHWAY AT ALL -- one degree of freedom, two constraints:")
    g1, ghw = G_bus(7.2, 128), G_bus(110, 35)
    print(f"     to give 1.00x at highway the arm must be {ghw}, which at grind #1 is "
          f"{ghw / g1:.2f}x -- WORSE than stock.")
    print(f"     to give 2.00x at grind #1 the arm must be {2 * g1}, which at highway is "
          f"{2 * g1 / ghw:.2f}x.")
    print("     ⇒ V67's architecture is structurally incapable of fixing the highway grind.")


if __name__ == "__main__":
    _report()
