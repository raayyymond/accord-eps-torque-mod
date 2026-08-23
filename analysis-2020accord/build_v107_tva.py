#!/usr/bin/env python3
"""
V107 -- gp-0x6b26's SPEED SCHEDULE, on a V106 base.

WHY THIS BUILD EXISTS
---------------------
V106 (gp-0x6b26's Y row x3.0 stock on the two ENGAGED mode records) FLEW as route `a6`:
1,224.0 s engaged, fault-free, and it EXTINGUISHED the 21-27 Hz mode at low speed.

    engaged, <16 km/h, |e4tq| >= 1600      peak Hz   PROMINENCE   18-30 RMS
      STOCK 1x                              18.23       1.46        0.3121
      V104  6x                              22.23       6.89        7.6624
      V105  notch                           20.48       3.42        5.6967
      V106                                  18.23       1.51        3.7255   <- stock-level

V106's argmax FOLLOWS the search-band edge exactly as stock's does, while V104's and V105's stay
pinned -- two independent within-spectrum signatures of NO LINE PRESENT.  The 18-30 RMS ratio
a6/V105 = 0.347 CLEARS route a6's own within-drive split-half null [0.482, 1.982]: the FIRST
band-power result in this kit's history to do so.  Positive control a6/STOCK = 5.735, so the
instrument had not gone dead.

WHAT SURVIVES, AND WHY IT SURVIVES EXACTLY THERE
------------------------------------------------
Prominence by regime (pooled, episode-bootstrapped; stock in parentheses):
      low  12.5 -> 4.2 -> 2.0  (2.5)      <- AT STOCK
      mid   4.3 -> 5.9 -> 3.2  (2.4)
      hwy  13.3 -> 24.0 -> 6.5 (1.3)      <- THE RESIDUAL
      hwy-matched 55-70  6.1 -> 5.1 -> 1.4 (1.6)   <- AT STOCK

The residual is at the TOP of the speed range -- and that is precisely where Honda's own speed
taper makes V106's dose weakest.  The schedule is X = (0, 1280, 5760) counts = (0, 20, 90) km/h
at 64 counts/km/h, and above 90 km/h the delivered coefficient is FLAT at Y[2]:

      delivered coefficient      5 mph    20 km/h   30 mph   >=90 km/h
        V106 (on the car)       -24546    -17202   -12681    -5898      <- 4.2x weaker at highway

THE UNIFORM AXIS IS EXHAUSTED -- this build cannot be "more dose"
-----------------------------------------------------------------
Y is SIGNED INT16 (the builder writes it with `<3h`).  Y[0] stock = -9830, so:

      k_max = 32768 / 9830 = 3.3335        V106 is at x3.0 == 90.00 % of the int16 floor.

x4 / x5 / x6 stock are int16 OVERFLOW, not merely risky.  Room to the floor is Y[0] x1.11,
Y[1] x1.90, **Y[2] x5.56** -- and Y[2] is the >=90 km/h knot, i.e. exactly where the line lives.
Every variant below therefore holds Y[0] EXACTLY at V106's -29490, so creep-speed clamp duty and
the relay index are UNCHANGED BY CONSTRUCTION.  The +-511 clamp bounds the term identically at
every speed, so a reshape changes only WHERE the term reaches its authority, never how much it
can have.  That is the opposite risk profile from another dose step -- which is how V80 became a
relay ("worst grinding ever recorded").

THE TERM IS NOT SATURATING
--------------------------
Reconstructed clamp duty on route a6's own engaged alpha distribution (r77-calibrated law,
held-out validated on r78 to +-20 % and CONSERVATIVE on the tail):

      stratum          n eng     p50     p99    duty>=511
      engaged all     123802    15.1   268.5     0.00121
      <8 km/h (S1)      3173    16.2   221.1     0.00047
      <16 km/h         10186    30.2   333.3     0.00185
      40-95 (S3)       34593    13.3   208.1     0.00056
      S2c hard turn     1913    50.9   371.8     0.00305
      |rate| 40-100     2757    41.9   477.9     0.00861   <- worst cell

All below 1 %.  And the ASSUMPTION-FREE test: if |gp-0x6b26| were railing, b5 would collapse to
(|gp-0x6ae2| >= 511) with no alpha dependence and the duty-vs-alpha curve would go flat.  V106's
is still FALLING at its top alpha decile (slope -0.097/log unit).  Not saturating.

THE ARITHMETIC, CONFIRMED FROM THE BINARY (orchestrator, program `code.bin`)
----------------------------------------------------------------------------
    FUN_00036c12:
        iVar4 = ((c2c_gated * Y_eff) >> 6) * 0x111      # 0x36CBE .. 0x36CC6
        iVar5 = iVar4 >> 0x12                           # 0x36CCA   => net >>24, x273
        gp-0x6b26 = clamp(iVar5, +-(short)*(tp+0x507E))  # tp+0x507E == 0xC407E == 511
        then the gp-0x6b26 / gp-0x4cd0 shadow-pair store

The clamp PRECEDES the store and 511 < the 512 trip in FUN_00036d74, so RULE 11 is intact BY
CONSTRUCTION at any Y.  V73 raised a different clamp past its own trip; V74/V75 both hard-faulted.

*** THE GATE -- WHY THIS FILE HAS TWO VARIANTS ***
--------------------------------------------------
The mode-record LERP is only ONE of THREE branches in FUN_00036c12:

    if (gp-0x671a < 0xff) and (gp-0x67f4 == 1):
        if gp-0x671a < 0xC64FD (=5):  Y_eff = LERP(mode record)   <- what E1_RESHAPE edits
        else:                         Y_eff = 0xC640A = -8192     <- FIXED, bypasses the records
    else:                             Y_eff = 0xC640C = -3277     <- FIXED, bypasses the records

|-8192| is LARGER than V106's own delivered value at >=90 km/h (-5898).  If the car takes the
fallback at road speed then the mode records are bypassed there, a reshape buys NOTHING at
highway, and the correct lever is the single cell 0xC640A instead.  That would also explain, in
one stroke, both the highway-only residual AND a6-score's measured delivered multiplier of
1.68x [1.16, 1.88] against an expected 2.00x.

    => VARIANT is not a preference.  It is decided by what gp-0x671a actually does on the road.
       Do not run this builder until that is answered.

Usage:
    ACCORD_FIRMWARE_ROOT=C:/Users/dudei/Desktop/Projects/accord-firmwares \
    ACCORD_V107_VARIANT=RESHAPE_A ACCORD_V107_WRITE=rwd python build_v107_tva.py
"""

import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_vfourframe_tva as FF                                                # noqa: E402
import build_v53_tva as V53                                                      # noqa: E402
import build_v106_tva as V106B                                                   # noqa: E402
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table    # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                 # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V107_WRITE", "").strip().lower()
VARIANT = os.environ.get("ACCORD_V107_VARIANT", "").strip().upper()

GP, TP = 0xFEDF8000, 0xBF000

BASE_NAME = "_v106_V105BASE-GP6B26.X3.0.D7A5C-D7A6C_plain_image.bin"
BASE_BIN = str(plain_image_path(BASE_NAME))
BASE_SHA = "78528aa35b9ea2fa1ea990b2c8d41c7adc784fc17f0b481d66ddcfd3667cb65a"
STOCK_BIN = str(plain_image_path("stock_fw_dump/code.bin"))
STOCK_SHA = V106B.STOCK_SHA

# --------------------------------------------------------------------------------------------
# The dose family.  Inherited from V106's own builder, never retyped.
# --------------------------------------------------------------------------------------------
FRICTION_PTR_ARRAY = V106B.FRICTION_PTR_ARRAY          # 0xCBE74
REC_X_OFF, REC_Y_OFF = V106B.REC_X_OFF, V106B.REC_Y_OFF
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES
Y_STOCK = V106B.Y_STOCK                                # (-9830, -5734, -1966)
Y_V106 = V106B.Y_V106                                  # (-29490, -17202, -5898)  == x3.0 stock
X_EXPECT = (0, 1280, 5760)                             # counts, 64 counts/km/h => (0, 20, 90) km/h

CLAMP_CAL = V106B.CLAMP_CAL                            # 0xC407E, 511, NOT TOUCHED
MONITOR_TRIP = V106B.MONITOR_TRIP                      # 512
INT16_MIN = -32768

# The gate cells found in FUN_00036c12.  FROZEN in the reshape variants; E1 in the fallback one.
GATE_IDX_THRESH = 0xC64FD       # byte, = 5.  gp-0x671a < this  =>  LERP branch
FALLBACK_A = 0xC640A            # int16, = -8192.  Taken when gp-0x671a >= 5
FALLBACK_B = 0xC640C            # int16, = -3277.  Taken when gp-0x671a >= 0xff or gp-0x67f4 != 1

# --------------------------------------------------------------------------------------------
# THE VARIANTS.  Y triples for modes 26/27 (X untouched), or a fallback-cell edit.
# Delivered coefficient after LERP, and ratio vs V106, at the speeds that matter:
#
#   variant        Y triple                    5mph   20kmh  50kmh  90+kmh   ratio@90+  int16 worst
#   V106 (base)    (-29490,-17202, -5898)     -24546 -17202 -12358  -5898       1.00x     90.0%
#   RESHAPE_A      (-29490,-29490,-29490)     -29490 -29490 -29490 -29490       5.00x     90.0%
#   RESHAPE_B      (-29490,-24000,-16000)     -27282 -24000 -20572 -16000       2.71x     90.0%
#   RESHAPE_C      (-29490,-29490,-20000)     -29490 -29490 -25423 -20000       3.39x     90.0%
#   HIGHWAY_ONLY   (-29490,-17202,-29490)     -24546 -17202 -22468 -29490       5.00x     90.0%
#
# HIGHWAY_ONLY holds Y[1] at V106's value too, so 20 km/h -- where the line is ALREADY
# extinguished -- gains nothing it does not need.  It is the surgical version of RESHAPE_A.
# --------------------------------------------------------------------------------------------
RESHAPES = {
    "RESHAPE_A":    (-29490, -29490, -29490),
    "RESHAPE_B":    (-29490, -24000, -16000),   # <- CHOSEN.  See the duty table below.
    "RESHAPE_C":    (-29490, -29490, -20000),
    "HIGHWAY_ONLY": (-29490, -17202, -29490),
}
# The fallback-cell variant: a two-byte edit to 0xC640A, for when gp-0x671a >= 5 on the road.
# 🛑 RETAINED ONLY AS A RECORD.  The branch is DEAD -- see [3] below.  Do not select it.
FALLBACK_DOSE = {"FALLBACK_X3": -24576}                # -8192 x 3, exactly as V106 dosed the records

# --------------------------------------------------------------------------------------------
# WHY B AND NOT A -- measured clamp duty, constant-free.
#   |b26|_X(v) = |b26|_measured(v) * Y_X(v)/Y_route(v)  -- measured wire x a ratio of two flash
#   tables.  No >>24, no 0x111, no reconstruction.  From r77 (x1.0, UNDAMPED = conservative):
#
#     variant       <16      16-40     40-70     70-90
#     V106 today  0.00643   0.00044   0.00007   0.00000
#     RESHAPE A   0.01871   0.00519   0.01174   0.06223   <- 6.2 % at 70-90.  RELAY TERRITORY.
#     RESHAPE B   0.01218   0.00180   0.00255   0.01048   <- <=1.05 % everywhere
#     RESHAPE C   0.01871   0.00414   0.00607   0.03391   <- 3.4 % at 70-90
#
#   B's clamp knee (1963) sits ABOVE r77's undamped 70-90 p99 of 1836 -- safe against the worst
#   distribution the corpus has ever measured, not merely against the damped one.  And route a6
#   spent 809 s of its 1,224 s engaged ABOVE 70 km/h: this is the majority of the operator's
#   engaged driving, not a rare corner.  V80's damper lived at 97 % of ceiling and produced the
#   worst grinding ever recorded -- "does not clip" and "is not a relay" are different statements.
# --------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------
# E2 -- THE 427 TELEMETRY TAP, RE-AIMED.
# The tap currently watches gp-0x6b86, the biquad lane -- a filter we have now decided not to
# build on.  Meanwhile the cell that SIZES V108 has never been measured above 90 km/h at
# anything near V106's dose: the entire corpus is 99.8 s from r78, at x1.5.  Re-aiming costs
# two bytes of displacement plus one byte of shift, and V104 already flew this exact edit.
#
#   0x55DF0  ld.h disp16[gp],r6      disp16 halfword at 0x55DF2
#            stock e8 93 = gp-0x6c18  ->  V104/V105/V106  7a 94 = gp-0x6b86
#   0x55E10  sar imm5,r6             halfword 0x32XX, imm5 = low 5 bits
#            stock a3 = sar 3,r6      ->  V104/V105/V106  a4 = sar 4,r6
# --------------------------------------------------------------------------------------------
TAP_SRC_ADDR = 0x55DF2                 # the disp16 halfword of the 427 source load
TAP_SCALER_ADDR = 0x55E10              # low byte of `sar imm5,r6`; imm5 = byte & 0x1F
TAP_SRC_V106 = 0x947A                  # gp-0x6b86, what V104/V105/V106 carry
TAP_SCALER_V106 = 0xA4                 # sar 4
TAP_SAR_OPCODE_MASK = 0xE0             # the non-imm5 bits of that byte; must not move

TAP_TARGETS = {                        # gp-relative offset -> what it measures
    "gp-0x6c2c": (0x6C2C, "RAW motor-rate derivative -- the term's INPUT, pre-gain, pre-clamp"),
    "gp-0x6b26": (0x6B26, "post-clamp inertia term -- measures THIS build's own clamp duty"),
}
TAP_TARGET = os.environ.get("ACCORD_V107_TAP", "").strip()
TAP_SAR = os.environ.get("ACCORD_V107_SAR", "").strip()

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
        print(f"    {OK} {msg}")
        return True
    print(f"    {BAD} {msg}")
    raise SystemExit(f"ABORTING -- assertion {_checks[0]} FAILED: {msg}")


u16, s16, rd, rdw = V106B.u16, V106B.s16, V106B.rd, V106B.rdw
rec_addr, rec_y, rec_x = V106B.rec_addr, V106B.rec_y, V106B.rec_x


def lerp_delivered(y, kmh):
    """Honda's LERP in FUN_00036c12 @0x36C60-0x36CB0, integer, truncating divq."""
    c = int(kmh * 64)
    xs = X_EXPECT
    if c <= xs[0]:
        return y[0]
    if c >= xs[-1]:
        return y[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= c < xs[i + 1]:
            return y[i] + ((y[i + 1] - y[i]) * (c - xs[i])) // (xs[i + 1] - xs[i])
    return y[-1]


# Everything V106 froze, PLUS the two gate cells and V106's own Y rows as carried state.
FROZEN = dict(V106B.FROZEN)
FROZEN[GATE_IDX_THRESH] = (1, 5, "gp-0x671a gate threshold -- selects LERP vs the fixed fallback")
# 🛑 rdw() returns UNSIGNED for 2-byte cells, so a negative cal must be registered as its u16
# image.  V106's FROZEN table is all-positive, so this had never bitten; the assertion caught it.
FROZEN[FALLBACK_B] = (2, -3277 & 0xFFFF,
                      "fallback B (gp-0x671a>=0xff or gp-0x67f4!=1) -- branch DEAD, not edited")


def assert_frozen(buf, label, extra_exempt=()):
    bad = []
    for a, (w, want, why) in sorted(FROZEN.items()):
        if a in extra_exempt:
            continue
        got = rdw(buf, a, w)
        if got != want:
            bad.append((a, got, want, why))
    for a, got, exp, why in bad:
        print(f"    {BAD} 0x{a:05X} is {got!r}, expected {exp!r} -- {why}")
    check(not bad, f"{label}: all {len(FROZEN) - len(extra_exempt)} FROZEN cells at expected values")


def assert_family(buf, label, engaged_want):
    print(f"\n    dose family 0x{FRICTION_PTR_ARRAY:05X} ({label})")
    bad = []
    for m in MANUAL_MODES + ENGAGED_MODES:
        ra = rec_addr(buf, m)
        want = Y_STOCK if m in MANUAL_MODES else engaged_want
        got, gx = rec_y(buf, m), rec_x(buf, m)
        role = "MANUAL " if m in MANUAL_MODES else "ENGAGED"
        if got != want or gx != X_EXPECT:
            bad.append(m)
        print(f"      {OK if got == want and gx == X_EXPECT else BAD} mode {m:2d} {role} "
              f"0x{ra:05X} Y = {got}  x{got[0] / Y_STOCK[0]:.2f} stock   X = {gx}")
    check(not bad, f"{label}: 4 records as expected (manual STOCK, engaged {engaged_want}, X fixed)")


def build():
    print("=" * 102)
    print("  V107 -- gp-0x6b26's SPEED SCHEDULE.  The uniform axis is exhausted; this is the")
    print("          remaining one.  Cal-only, on a V106 base.")
    print("=" * 102)

    if VARIANT not in RESHAPES and VARIANT not in FALLBACK_DOSE:
        raise SystemExit(
            f"\n  ACCORD_V107_VARIANT must be one of: {', '.join(sorted(RESHAPES))}\n"
            f"  (FALLBACK_X3 is retained as a record only -- that branch is DEAD, see [3].)\n")
    is_reshape = VARIANT in RESHAPES
    if is_reshape and VARIANT != "RESHAPE_B":
        print(f"\n  ⚠  VARIANT = {VARIANT}, not the chosen RESHAPE_B.  A costs 6.2 % clamp duty at\n"
              f"     70-90 km/h on the conservative reference -- V80 relay territory.  Deliberate?\n")
    if TAP_TARGET not in TAP_TARGETS:
        raise SystemExit(
            f"\n  ACCORD_V107_TAP must be one of: {', '.join(sorted(TAP_TARGETS))}\n"
            "  The 427 tap currently watches gp-0x6b86, the biquad lane -- a filter this build\n"
            "  has decided not to pursue.  Re-aim it, or the drive carries no new instrument.\n")
    if not (TAP_SAR.isdigit() and 0 <= int(TAP_SAR) <= 31):
        raise SystemExit(
            "\n  ACCORD_V107_SAR must be an integer 0..31 -- the `sar imm5,r6` shift for the tap.\n"
            "  🛑 Size it against the lane's OWN reachable output at >=70 km/h, not a downstream\n"
            "     gate (GATE 3; V96 violated this and under-used its channel 4x).  The wire is 10\n"
            "     bits and rails at 1023.  State the LSB in counts and the p99.9 clip fraction.\n")
    sar_imm = int(TAP_SAR)

    print("\n  [1] THE BASE -- V106, which FLEW as route a6 (1,224.0 s engaged, fault-free)")
    base = bytearray(Path(BASE_BIN).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base is V106, sha256 {BASE_SHA[:24]}...")
    check(len(base) == 0x100000, f"base is {len(base)} bytes")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    stock = bytearray(Path(STOCK_BIN).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA and len(stock) == 0x100000,
          f"stock reference loaded, sha256 {STOCK_SHA[:24]}...")

    print("\n  [2] FROZEN CELLS -- every one at its expected value BEFORE the edit")
    exempt = (TAP_SRC_ADDR, TAP_SCALER_ADDR) + (() if is_reshape else (FALLBACK_A,))
    assert_frozen(base, "V106 base", exempt)
    print("      (0x55DF2 / 0x55E10 exempt -- E2 re-aims them; their pre-images are checked in [5b])")

    print("\n  [3] THE GATE IN FUN_00036c12 -- three branches, and we can only edit one")
    check(base[GATE_IDX_THRESH] == 5, f"  0xC64FD = {base[GATE_IDX_THRESH]} (the gp-0x671a threshold)")
    check(s16(base, FALLBACK_A) == -8192, f"  0xC640A = {s16(base, FALLBACK_A)} (fallback, gp-0x671a >= 5)")
    check(s16(base, FALLBACK_B) == -3277, f"  0xC640C = {s16(base, FALLBACK_B)} (fallback, invalid/off)")
    print(f"      |0xC640A| = 8192 vs V106's delivered {abs(Y_V106[2])} at >=90 km/h "
          f"-- the fallback is {8192 / abs(Y_V106[2]):.2f}x STRONGER than our own highway dose")

    print("\n  [4] THE POINTER TABLE -- four modes, resolved from the image")
    for m in MANUAL_MODES + ENGAGED_MODES:
        ra = rec_addr(base, m)
        n = bytes(stock).count(struct.pack("<I", ra))
        check(n == 1, f"mode {m}: record 0x{ra:05X} occurs EXACTLY {n} time as an LE32 literal")
    assert_family(base, "V106 base", Y_V106)

    print("\n  [5] E1 -- THE EDIT")
    code = bytearray(base)
    attributed = set()

    if is_reshape:
        Y_NEW = RESHAPES[VARIANT]
        check(Y_NEW[0] == Y_V106[0],
              f"  Y[0] held EXACTLY at V106's {Y_V106[0]} -- creep clamp duty and the relay "
              f"index are UNCHANGED BY CONSTRUCTION")
        for i, v in enumerate(Y_NEW):
            check(INT16_MIN <= v <= 32767,
                  f"  Y[{i}] = {v} fits int16 ({100 * abs(v) / abs(INT16_MIN):.1f} % of the floor)")
            check(abs(v) >= abs(Y_V106[i]), f"  Y[{i}] does not REDUCE the dose ({Y_V106[i]} -> {v})")
        print("\n      delivered coefficient after Honda's own LERP:")
        print(f"      {'km/h':>8} {'V106':>9} {VARIANT:>11} {'ratio':>8}")
        for kmh in (8, 20, 50, 70, 90, 120):
            a, b = lerp_delivered(Y_V106, kmh), lerp_delivered(Y_NEW, kmh)
            print(f"      {kmh:>8} {a:>9} {b:>11} {b / a:>7.2f}x")
        for m in ENGAGED_MODES:
            ya = rec_addr(code, m) + REC_Y_OFF
            check(rec_y(code, m) == Y_V106, f"  mode {m} Y@0x{ya:05X} pre-image = {Y_V106}")
            struct.pack_into("<3h", code, ya, *Y_NEW)
            attributed |= set(range(ya, ya + 6))
            print(f"      0x{ya:05X}  {bytes(base[ya:ya+6]).hex()} -> {bytes(code[ya:ya+6]).hex()}")
        check(len(attributed) == 12, f"E1 wrote exactly {len(attributed)} bytes (expected 12)")
        engaged_after = Y_NEW
    else:
        newv = FALLBACK_DOSE[VARIANT]
        check(s16(base, FALLBACK_A) == -8192, "  0xC640A pre-image = Honda's -8192")
        check(INT16_MIN <= newv <= 32767, f"  {newv} fits int16")
        check(newv == -8192 * 3, f"  {newv} == -8192 x 3, the SAME multiple V106 applied to the "
                                 f"records -- computed, never typed as hex")
        struct.pack_into("<h", code, FALLBACK_A, newv)
        attributed |= set(range(FALLBACK_A, FALLBACK_A + 2))
        print(f"      0x{FALLBACK_A:05X}  {bytes(base[FALLBACK_A:FALLBACK_A+2]).hex()} -> "
              f"{bytes(code[FALLBACK_A:FALLBACK_A+2]).hex()}   -8192 -> {newv}")
        check(len(attributed) == 2, f"E1 wrote exactly {len(attributed)} bytes (expected 2)")
        engaged_after = Y_V106

    print("\n  [5b] E2 -- THE 427 TAP, RE-AIMED")
    off, what = TAP_TARGETS[TAP_TARGET]
    new_disp = (0x10000 - off) & 0xFFFF
    check(u16(code, TAP_SRC_ADDR) == TAP_SRC_V106,
          f"  pre-image disp16 = 0x{TAP_SRC_V106:04X} = gp-0x6b86 (V104's aim), as V106 shipped it")
    check(code[TAP_SCALER_ADDR] == TAP_SCALER_V106,
          f"  pre-image scaler byte = 0x{TAP_SCALER_V106:02X} = sar {TAP_SCALER_V106 & 0x1F},r6")
    check((new_disp & 1) == 0,
          f"  disp16 0x{new_disp:04X} is EVEN -- bit0 selects ld.h vs ld.w on V850; an odd "
          f"displacement would silently become a WORD load")
    check(0x8000 <= new_disp <= 0xFFFF,
          f"  disp16 0x{new_disp:04X} is negative-signed, i.e. a real gp-MINUS-offset")
    new_scaler = (TAP_SCALER_V106 & TAP_SAR_OPCODE_MASK) | sar_imm
    check((new_scaler & TAP_SAR_OPCODE_MASK) == (TAP_SCALER_V106 & TAP_SAR_OPCODE_MASK),
          f"  scaler 0x{new_scaler:02X} keeps the sar opcode bits -- only imm5 moves "
          f"({TAP_SCALER_V106 & 0x1F} -> {sar_imm})")
    struct.pack_into("<H", code, TAP_SRC_ADDR, new_disp)
    code[TAP_SCALER_ADDR] = new_scaler
    attributed |= set(range(TAP_SRC_ADDR, TAP_SRC_ADDR + 2)) | {TAP_SCALER_ADDR}
    print(f"      0x{TAP_SRC_ADDR:05X}  {bytes(base[TAP_SRC_ADDR:TAP_SRC_ADDR+2]).hex()} -> "
          f"{bytes(code[TAP_SRC_ADDR:TAP_SRC_ADDR+2]).hex()}   gp-0x6b86 -> {TAP_TARGET}")
    print(f"      0x{TAP_SCALER_ADDR:05X}  {TAP_SCALER_V106:02x} -> {new_scaler:02x}"
          f"                 sar {TAP_SCALER_V106 & 0x1F},r6 -> sar {sar_imm},r6")
    print(f"      => the 427 lane now carries: {what}")
    print(f"      => LSB = {1 << sar_imm} counts; the 10-bit wire rails at 1023 "
          f"=> full scale {(1 << sar_imm) * 1023} counts")
    check(rd(code, 0x55D50, 4) == rd(base, 0x55D50, 4),
          "  the 399 packer at 0x55D50 is untouched -- E2 is on the 427 lane only")

    print("\n  [6] POST-IMAGE -- the family, and everything that must NOT have moved")
    assert_family(code, VARIANT, engaged_after)
    for m in MANUAL_MODES:
        check(rec_y(code, m) == Y_STOCK, f"  mode {m} (MANUAL) still Honda stock -- untouched")
    for a, n in V106B.BQ_CELLS:
        check(rd(code, a, 4) == rd(base, a, 4), f"  biquad {n} @0x{a:05X} byte-identical to base")
    check(rd(code, V106B.CAVE_BASE, V106B.CAVE_LEN) == rd(base, V106B.CAVE_BASE, V106B.CAVE_LEN),
          "  the whole cave is byte-identical to V106 -- b5 still means what a6 measured")
    check(s16(code, V106B.B5_OPERAND_B_ADDR) == V106B.B5_OPERAND_B_DISP,
          "  b5's operand B is still gp-0x6b26 -- the dose still reads itself out")
    check(s16(code, CLAMP_CAL) == 511 and 511 < MONITOR_TRIP,
          f"  🛑 0xC407E = 511 < {MONITOR_TRIP} -- RULE-11 interlock intact BY CONSTRUCTION")
    for m in ENGAGED_MODES:
        check(rec_x(code, m) == X_EXPECT,
              f"  mode {m} X row untouched {X_EXPECT} -- no LERP denominator can reach zero")
    assert_frozen(code, VARIANT, exempt)

    print("\n  [7] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{old:08X} -> 0x{new:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    print("\n  [8] FULL BYTE DIFF vs THE V106 BASE")
    bruns = [i for i in range(START, END) if code[i] != base[i]]
    runs = []
    for i in bruns:
        if runs and i == runs[-1][1]:
            runs[-1][1] = i + 1
        else:
            runs.append([i, i + 1])
    stray = []
    for lo, hi in runs:
        if (lo & 0xFFF) >= 0xFFC:
            tag = "CRC trailer"
        elif lo in (TAP_SRC_ADDR, TAP_SCALER_ADDR) and set(range(lo, hi)) <= attributed:
            tag = f"E2 -- 427 tap -> {TAP_TARGET}"
        elif set(range(lo, hi)) <= attributed:
            tag = f"E1 -- {VARIANT}"
        else:
            tag, _ = "?? UNATTRIBUTED", stray.append((lo, hi))
        print(f"      0x{lo:05X}..0x{hi-1:05X}  {hi-lo:>3} B  "
              f"{bytes(base[lo:hi]).hex():<14} -> {bytes(code[lo:hi]).hex():<14} {tag}")
    check(not stray, "every changed run vs V106 is E1, E2, or a CRC trailer")

    print("\n  [9] FULL BYTE DIFF vs HONDA STOCK -- zero unattributed")
    # Re-attribute the two spans this build owns.  🛑 IMPORTED from V106's proven ledger, never
    # retyped -- a hand-copied stale map is exactly how DOSE_FAMILY_Y came to be missing mode 25.
    tap_span = set(range(TAP_SRC_ADDR, TAP_SRC_ADDR + 2)) | {TAP_SCALER_ADDR}
    vs_stock = [r for r in V106B.VS_STOCK
                if r[0] not in (0xD7A5C, 0xD7A6C) and not (set(range(r[0], r[1])) & tap_span)]
    vs_stock += [(TAP_SRC_ADDR, TAP_SRC_ADDR + 2, "V107", f"427 tap source -> {TAP_TARGET}"),
                 (TAP_SCALER_ADDR, TAP_SCALER_ADDR + 1, "V107", f"427 tap scaler -> sar {sar_imm}")]
    if is_reshape:
        vs_stock += [(0xD7A5C, 0xD7A62, "V107", f"mode 26 ENGAGED Y -- {VARIANT}"),
                     (0xD7A6C, 0xD7A72, "V107", f"mode 27 ENGAGED Y -- {VARIANT}")]
    else:
        vs_stock += [(0xD7A5C, 0xD7A62, "V106", "mode 26 ENGAGED Y -- carried"),
                     (0xD7A6C, 0xD7A72, "V106", "mode 27 ENGAGED Y -- carried"),
                     (FALLBACK_A, FALLBACK_A + 2, "V107", f"gp-0x671a>=5 fallback -- {VARIANT}")]
    sruns = [i for i in range(START, END) if code[i] != stock[i]]
    scrc = {b + 0xFFC + k for b in range(0x13000, 0x100000, 0x1000) for k in range(4)}
    sattr = set()
    for lo, hi, bld, what in vs_stock:
        sattr |= {i for i in sruns if lo <= i < hi}
    sun = sorted(set(sruns) - sattr - scrc)
    print(f"      {len(sruns)} bytes differ from STOCK, {len(sattr)} attributed, "
          f"{len(set(sruns) & scrc)} CRC trailers")
    check(not sun, "ZERO unattributed bytes vs stock"
                   + ("" if not sun else f"  -- {[hex(x) for x in sun[:16]]}"))

    print("\n  [10] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 OK")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V107 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    token = f"V106BASE-GP6B26.{VARIANT}-TAP.{TAP_TARGET.split('-0x')[-1].upper()}.SAR{sar_imm}"
    bin_out = str(plain_image_path(f"_v107_{token}_plain_image.bin"))
    out = os.path.join(RWD_DIR, f"39990-TVA,A160-V107-{token}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(bin_out).write_bytes(bytes(code))
        Path(out).write_bytes(rwd)
        print(f"\n  [11] WRITTEN\n      {bin_out}\n      {out}")
        disk = bytearray(Path(bin_out).read_bytes())
        check(hashlib.sha256(bytes(disk)).hexdigest() == img_sha, "plain image re-read from disk")
        assert_frozen(disk, "SHIPPED image", exempt)
        assert_family(disk, "SHIPPED image", engaged_after)
        check(walk_all_blocks(bytes(disk)) == 0, "SHIPPED image CRC 50/50, from disk")
    else:
        print("\n  [11] NOT WRITTEN -- set ACCORD_V107_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  V107 [{token}]   {_checks[1]}/{_checks[0]} assertions PASSED")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    if is_reshape:
        print(f"  E1  0xD7A5C / 0xD7A6C -- gp-0x6b26's Y row, {Y_V106} -> {RESHAPES[VARIANT]}")
        print(f"      Y[0] UNCHANGED, so creep -- which route a6 showed is already at stock-level")
        print(f"      prominence (1.51 vs stock's 1.46) -- is untouched.  The raise lands where the")
        print(f"      residual ~27 Hz line actually is: the top of the speed range.")
    else:
        print(f"  E1  0x{FALLBACK_A:05X} -- the gp-0x671a>=5 fallback, -8192 -> "
              f"{FALLBACK_DOSE[VARIANT]}")
        print(f"      The mode records are BYPASSED on that branch, so this is the only cell that")
        print(f"      can reach it.  Same x3 multiple V106 applied to the records.")
    print(f"  E2  0x{TAP_SRC_ADDR:05X} + 0x{TAP_SCALER_ADDR:05X} -- the 427 tap, gp-0x6b86 -> "
          f"{TAP_TARGET}, sar {sar_imm}")
    print(f"      The biquad lane is a filter we are no longer building on.  The cell that sizes")
    print(f"      V108 has NEVER been measured above 90 km/h near this dose -- the whole corpus is")
    print(f"      99.8 s from r78 at x1.5.  This drive closes that.  V104 flew this same edit.")
    print(f"  UNTOUCHED: 0xC407E = 511 (interlock), 0xC6CD0 = 5346 (the 6x gain), both MANUAL")
    print(f"      modes, the X breakpoints, the biquad, the cave, Lever B, b5 (the dose readout),")
    print(f"      and 0xC640A/0xC640C (the gp-0x671a fallback branch -- PROVEN DEAD, not edited).")
    print(f"  CRC: {len(blocks)} trailer(s), {', '.join(f'0x{b[1]:06X}' for b in blocks)}.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
