#!/usr/bin/env python3
r"""`0xC6446` (Lever B's r24 arm) -- CLAMP HEADROOM as a function of dose.

WHY THIS EXISTS
    V88 flew Lever B at 5244 = 2.000x the LERP and CUT the delivered command's 15-22 Hz content to
    0.549x at ZERO cost to the 0.5-3 Hz LKAS command.  The obvious V89 is more of the same dose.
    🛑 V80's lesson is the counter-argument: a lane that PINS becomes a RELAY and buys broadband HF
    plus a limit cycle -- the worst grinding this car has produced -- and V80's no-clip gate missed it
    because it tested `product > ceiling` while the real state was `= ceiling - 17`.
    ⇒ size the dose against APPROACHING the rail, not exceeding it.

THE LANE, from `FUN_0003aa2c` (r24 branch `0x3ab98`-`0x3ac58`), 4 independent decompiles agreeing:

    d    = gp-0x4f62                       # N=4 backward difference, produced in FUN_0007e74a
    r1   = clamp(d, +-0x1400)              # 5120, @0x3aaa0-0x3aac0 -- SHARED by r24 and r26
    r8   = gain * r1                       # @0x3ac18  `mul r10,r8,r0`
    r8   = r8 >> 10                        # @0x3ac20  `sar 0xa`
    r8   = deadband(r8, D = cal 0xC61F6 = 3)   # @0x3ac22-3c, y = 0 if |x|<=D else sign(x)*(|x|-D)
    r24  = clamp(r8 * polarity, +-0x2000)  # @0x3ac3e-58, 8192  <<< THE RAIL THIS FILE SIZES

    ✅ ORDERING CONFIRMED against `lever-hf`'s byte-exact disassembly of the r24 branch
    (`reference_accord_fun3aa2c_r24_r26_pole_census_no_filter_exists`): mul -> sar 0xa -> deadband ->
    polarity -> clamp.  The deadband SUBTRACTS D from the magnitude, so the rail is actually met at
    |x| = 8192 + 3 = 8195 -- a 0.04% shift, folded in below and immaterial to every verdict.

    gain = 2622 (the mode-24/26 LERP at grind #1's operating point) on stock;
           5244 on V88 = 2.0000x exactly (byte-verified: mode 24 == mode 26, LERP 2622 in both).

🛑 THE INPUT DISTRIBUTION IS INHERITED, NOT MEASURED ON V88.
    `|dtorque|` = 123..839 counts over 120,049 frames comes from V65 (`v66_v67_explained`).  It is the
    only distribution on file.  Everything below is EVIDENCE about the arithmetic and BELIEF about the
    margin, because the margin depends on a distribution measured on a different build and route.
    The p99/max quoted are that range's endpoints, treated as p99 <= 839 and max = 839.

⚠ SCALAR-vs-CURVE: `0xC6446` substitutes a FLAT scalar for a curve, so the effective multiplier runs
    1.77x - 2.55x across the LKAS-on regime (record).  A nominal 2.00x therefore runs up to
    2.55/2.00 = 1.275x HOT at one end.  The hot end is what meets the rail first.
"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LERP = 2622                 # mode 24 == mode 26 at grind #1's operating point, byte-verified
RAIL = 0x2000               # 8192, the r24 output clamp
R1_CLAMP = 0x1400           # 5120, the shared pre-clamp on the differenced input
DT_P99, DT_MAX = 839, 839   # V65's |dtorque| range endpoints -- INHERITED, see the docstring
HOT = 2.55 / 2.00           # scalar-vs-curve spread at the hot end of the LKAS-on regime

DOSES = [(2622, "1.000x  stock LERP"),
         (5244, "2.000x  V88, FLOWN"),
         (6555, "2.500x"),
         (7866, "3.000x"),
         (10488, "4.000x")]


DEADBAND = 3                # cal 0xC61F6, SUBTRACTED from the magnitude before the clamp


def rail_input(gain):
    """|r1| at which the r24 output first touches +-8192, deadband subtraction included."""
    return (RAIL + DEADBAND) * 1024.0 / gain


print(f"r24 = clamp( (clamp(dtorque, +-{R1_CLAMP}) * gain) >> 10, +-{RAIL} )")
print(f"LERP = {LERP} (mode 24 == 26)   |dtorque| p99/max = {DT_P99}/{DT_MAX} counts (V65, INHERITED)")
print(f"scalar-vs-curve hot end = {HOT:.3f}x nominal\n")

print(f"{'0xC6446':>8} {'dose':<18} {'|r1| to RAIL':>12} {'margin vs max':>14} "
      f"{'HOT |r1| to RAIL':>17} {'HOT margin':>11}   verdict")
print("-" * 104)
for gain, label in DOSES:
    r = rail_input(gain)
    rh = rail_input(gain * HOT)
    m, mh = r / DT_MAX, rh / DT_MAX
    if mh >= 1.5:
        v = "clear"
    elif mh >= 1.2:
        v = "THIN -- inside V80's blind spot"
    elif mh >= 1.0:
        v = "🛑 AT THE RAIL at the hot end"
    else:
        v = "🛑🛑 PINS -- relay class, do not build"
    print(f"{gain:>8} {label:<18} {r:>12.0f} {m:>13.2f}x {rh:>17.0f} {mh:>10.2f}x   {v}")

print(f"\n⚠ The shared pre-clamp at +-{R1_CLAMP} is never the binding constraint here: V65's max is "
      f"{DT_MAX}, which is {R1_CLAMP/DT_MAX:.1f}x below it.")

print("\nWHAT THE TABLE SAYS")
print("  * V88's flown 2.000x has a hot-end margin of "
      f"{rail_input(5244*HOT)/DT_MAX:.2f}x -- real but not generous.")
print("  * 3.000x lands the hot end essentially ON the rail. 4.000x pins outright.")
print("  * ⇒ THE USABLE DOSE WINDOW ABOVE V88 IS NARROW, and 2.5x is already inside the margin band")
print("    where V80's no-clip gate would have reported 'no clipping' while the lane behaved as a relay.")
print("\n🛑 THE HONEST READING: `accord-v62-fixed-the-grinding` records '2x is the OPTIMUM, not a point")
print("   on a ramp'. This arithmetic offers a MECHANISM for that being true -- the rail, not the")
print("   tuning -- but it rests on a |dtorque| distribution measured on V65, a different build and")
print("   route. ⇒ THE RIGHT NEXT STEP IS TO MEASURE |dtorque| ON V88, not to bet on this table.")
print("   `gp-0x6ada` (r24's post-clamp RAM mirror) is a free, blast-radius-zero telemetry tap and is")
print("   exactly the cell that would settle it.")
