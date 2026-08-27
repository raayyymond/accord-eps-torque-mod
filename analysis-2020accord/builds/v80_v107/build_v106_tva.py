#!/usr/bin/env python3
"""
=====================================================================================================
V106 -- THE APPARENT-INERTIA / ACCELERATION-DAMPING TERM, x3.0 STOCK-RELATIVE ON THE ENGAGED MODES
=====================================================================================================
BASE: V105 (`_v105_V104BASE-NOTCH25.5HZ...`), which FLEW as route `a5`.

TWELVE BYTES.  PURE CAL.  NO CAVE CHANGE.  ONE CRC TRAILER.

    0xD7A5C  mode 26 (ENGAGED) Y[0..2]   (-14745,-8601,-2949) -> (-29490,-17202,-5898)
    0xD7A6C  mode 27 (ENGAGED) Y[0..2]   (-14745,-8601,-2949) -> (-29490,-17202,-5898)

i.e. x3.0 of Honda's stock (-9830,-5734,-1966), which is x2.0 of what is on the car today.

-----------------------------------------------------------------------------------------------------
WHY THIS LEVER, AND WHY THIS DIRECTION
-----------------------------------------------------------------------------------------------------
`gp-0x6b26 = -K(speed) * angular_acceleration`, produced by FUN_00036c12 from `gp-0x6c2c` (an EMA of
the first difference of the filtered motor rate), summed UNWEIGHTED into the aggregator FUN_0003aa2c
alongside gp-0x6ad4 / gp-0x6b86 / gp-0x6bbe / gp-0x6bd0 / r24 / r26.

1. IT IS THE ONLY LEVER IN THE KIT WITH A SIGNED ON-CAR PRECEDENT POINTING THIS WAY.
   V93/V94 LOWERED it (mode 24 x0.50, modes 26/27 x0.25) and the operator aborted the drive:
   "made the stuttering and grinding worse, by a lot.  So much so that it vibrated the entire car,
   and I decided it was not safe to drive."  Grinding is one of this build's two targets.
   The RAISE direction has never been tested at 18-28 Hz -- the "closed both directions" verdict
   rested on a dose-VERIFICATION check at 6-9 Hz, never a symptom-band measurement.
   FALSIFIED != INERT != UNTESTED.

2. IT IS DAMPING, NOT ATTENUATION -- and that distinction is now MEASURED, not argued.
   Route `a5` showed V105's 25.5 Hz notch RELOCATED the mode (peak 22.73 -> 20.48 Hz at low speed,
   UP at highway) with total 18-30 Hz power CONSERVED.  |H_V105| evaluated at each build's OWN peak
   went 0.304 -> 0.544: the mode slid to where the notch costs it less.  A notch displaces a
   describing-function intersection; damping removes it.

3. IT REACHES ALL THREE OF THE OPERATOR'S GRINDS.  Cascade gain vs raw rate at x3.0:
       7.79 Hz  1.478      21.73 Hz  3.706      26.0 Hz  4.224
   The operator states (2026-08-22) that his grind #1 / #2 / #3 are the SAME FREQUENCY under three
   different CONDITIONS, and route-`a5` measurement agrees: all three of his scenarios peak at
   21-27 Hz and NONE shows a 38-48 Hz line (prominence 0.3-4.9, median ~1.0 = baseline).

4. 🛑 IT CANNOT RATE-LIMIT HIM, STRUCTURALLY.  H(f=0) = 0 EXACTLY: the cascade's differencer term
   32*(1 - z^-1) is identically zero at DC for ANY a1/a2/K.  A HELD 6x command sees nothing from
   this term at any multiplier.  That is a proof, not a measurement.

5. AND IT DOES NOT COST HIM HARD-STEERING AUTHORITY.  Conditioned on real fast steering in the
   corpus (`ra4`, V104), reconstructed |gp-0x6c2c| runs p99 = 397-416 at |rate_c| >= 150-200 deg/s
   against the x3.0 clamp knee of 1065 -- 100% of those frames clamp at NEITHER multiplier.
   Acceleration content is LOWER when steering fast, because a sustained fast rate has little
   acceleration once its ramp settles.  Even fully saturated this term is 511/10240 = 4.99% of the
   aggregate authority.

-----------------------------------------------------------------------------------------------------
WHY 26/27 ONLY -- AND WHY THAT IS NOT AN OVERSIGHT
-----------------------------------------------------------------------------------------------------
The family has FOUR members, read from the pointer table at 0xCBE74, each record base occurring
EXACTLY ONCE as an LE32 literal in the whole image (verified, both methods, zero disagreements):

    slot0 0xCBED4 -> 0xD6A64  Y@0xD6A6C  mode 24  MANUAL   stock, NEVER DOSED
    slot1 0xCBED8 -> 0xD7A44  Y@0xD7A4C  mode 25  MANUAL?  stock, NEVER DOSED
    slot2 0xCBEDC -> 0xD7A54  Y@0xD7A5C  mode 26  ENGAGED  x1.5 since V96   <- DOSED HERE
    slot3 0xCBEE0 -> 0xD7A64  Y@0xD7A6C  mode 27  ENGAGED  x1.5 since V96   <- DOSED HERE

Mode 24 is MANUAL.  Dosing it would be INERT for an engagement-conditional symptom and would
instead change manual / LKAS-off steering feel -- a consequence nobody asked for.  Mode 25 shares
mode 24's primary selector bit (gp-0x67f6 = 0) and differs only in gp-0x67e2, whose two states have
NOT been traced.  Dosing a mode whose role is unconfirmed is the V69/V70 trap (mode-10 tables on a
modes-24/26 car; the whole dose ladder never existed).  So both are left alone, and both arms of
this build move by the same factor -- no unequal-arms artefact to explain afterwards.

-----------------------------------------------------------------------------------------------------
🛑 THE BUILD PROVES ITS OWN PREMISE -- RULE 7, CLOSED WITH ZERO EXTRA BYTES
-----------------------------------------------------------------------------------------------------
"mode-proof or it is a bet."  The engaged MODE RECORD has been the SUSPECTED cause of V91's and
V92's nulls since 2026-08-11 and was never directly measured -- V93 was built as a discriminator
and never flown.  This build settles it without a single extra byte:

    the cave's PASS2 rung `b5` = ( |gp-0x6ae2| >= |gp-0x6b26| )   -- FRICTION vs INERTIA
    operand B at 0xC4B72 = da94 = disp -0x6b26   (read off the V105 image, asserted below)

`gp-0x6b26` is the cell this build doubles.  So:
    b5 engaged duty COLLAPSES  => the car IS reading mode 26/27 when engaged.  Dose arrived.
    b5 engaged duty UNCHANGED  => the car is NOT reading them engaged.  That is the V91/V92
                                  suspicion CONFIRMED, and it invalidates the whole dose family.
Either way the drive answers it.  b5's own baseline is measured: 0.2533 pooled / 0.4019 engaged
< 16 km/h on route `a5`.  MANUAL is the built-in control -- the engaged arm must move and the
manual arm must not.

-----------------------------------------------------------------------------------------------------
WHAT A NULL LICENSES
-----------------------------------------------------------------------------------------------------
"gp-0x6b26 on its current flat-Y-table mechanism is not the lever for this mode, in either
direction, up to a 2x step past what is already on the car -- redirect to the banked wide-notch
biquad candidates or to the band-pass damper cave."
It does NOT license any claim about the collapse above 100 deg/s, which this build does not address.

🛑 NOT WITHIN-DRIVE DECIDABLE: any cross-build 18-30 Hz or 6-9 Hz BAND-POWER change.  Route `a5`'s
within-drive split-half null spans 0.26-3.8, so a single drive at this exposure cannot resolve a
2-3x change.  Mark any such comparison NOT-CURRENTLY-DECIDABLE.
WITHIN-DRIVE DECIDABLE: b5's duty shift (dose arrival + mode proof), and the operator's own report,
which is the PRIMARY readout and not a fallback to the telemetry.

-----------------------------------------------------------------------------------------------------
SAFETY
-----------------------------------------------------------------------------------------------------
🛑 0xC407E IS NOT TOUCHED.  FUN_00036c12 clamps gp-0x6b26 to +-cal(0xC407E) = +-511 BEFORE the
RULE-11 monitor FUN_00036d74 compares it (trips at |gp-0x6b26| > 512).  511 < 512 by exactly one
count, so the interlock is structurally untrippable at ANY Y-table multiplier as long as this one
cal stays where Honda put it.  This build does not touch it, so the interlock stays intact BY
CONSTRUCTION, NOT BY CARE.  (V73 raised a different cell's clamp past its own trip point and V74
and V75 both hard-faulted with a mid-drive total loss of assist.)

Int32 overflow in FUN_00036c12's internal `mid * 0x111` product: threshold on |gp-0x6c2c| is
503342400/Y = 17068 at Y = 29490.  Measured maximum across the corpus is 5141-5320 -- 3.3x of
margin, and zero frames anywhere near it at any multiplier up to x3.0.
=====================================================================================================
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import build_vfourframe_tva as FF                                                # noqa: E402
import build_v53_tva as V53                                                      # noqa: E402
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table    # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                 # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V106_WRITE", "").strip().lower()

GP, TP = 0xFEDF8000, 0xBF000

BASE_NAME = "_v105_V104BASE-NOTCH25.5HZ.C60A8-C60B4-PROBE.B6.6B94.GE.4F64_plain_image.bin"
BASE_BIN = str(plain_image_path(BASE_NAME))
BASE_SHA = "2666a000415a29fef98ac9cd6c183536269c3e61a61fc822c17586f2adde7e00"
STOCK_BIN = str(plain_image_path("stock_fw_dump/code.bin"))
STOCK_SHA = "3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822"

# -----------------------------------------------------------------------------------------------
# E1 -- THE DOSE.  Derived from Honda's own stock row by an integer multiple; never typed as hex.
# -----------------------------------------------------------------------------------------------
FRICTION_PTR_ARRAY = 0xCBE74
REC_X_OFF, REC_Y_OFF = 0x02, 0x08
MANUAL_MODES, ENGAGED_MODES = (24, 25), (26, 27)

Y_STOCK = (-9830, -5734, -1966)          # Honda, all four modes
Y_V92 = (-14745, -8601, -2949)           # x1.5, engaged pair, on the car since V96
DOSE = 3                                 # x3.0 stock-relative == x2.0 of what is on the car
Y_V106 = tuple(v * DOSE for v in Y_STOCK)

CLAMP_CAL = 0xC407E                      # the RULE-11 interlock. 511. NOT TOUCHED.
MONITOR_TRIP = 512                       # FUN_00036d74 trips above this
OVF_NUM = 503342400                      # int32 overflow numerator for the mid*0x111 product
GP6C2C_MAX_OBSERVED = 5320               # corpus max, both stock and V104 arms

# b5 -- the carried comparator that makes this build mode-proof.  Operand B is the dosed cell.
B5_OPERAND_B_ADDR = 0xC4B70          # the disp16 halfword of `movea -0x6b26,gp,r6` at 0xC4B6E
B5_OPERAND_B_DISP = -0x6B26
B5_OPERAND_A_ADDR = 0xC4B64          # ditto for `movea -0x6ae2,gp,r6` at 0xC4B62
B5_OPERAND_A_DISP = -0x6AE2
CAVE_BASE, CAVE_LEN, CAVE_FREE_END = 0xC4B34, 0xA4, 0xC4FF0

TOKEN = "V105BASE-GP6B26.X3.0.D7A5C-D7A6C"
BIN_OUT = str(plain_image_path(f"_v106_{TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V106-{TOKEN}-0x{START:X}-0x{END:X}.rwd")

EXPECT_IMG_SHA = "78528aa35b9ea2fa1ea990b2c8d41c7adc784fc17f0b481d66ddcfd3667cb65a"
EXPECT_RWD_SHA = "e5ac6927a112a0cdf944971aebf7aa14efe6ad8597e17835bbc62d1589bfecbc"

# -----------------------------------------------------------------------------------------------
# EVERYTHING THAT MUST NOT MOVE.  V105's ledger, PLUS the four biquad coefficients V105 itself
# wrote -- those are CARRIED state now and a stray edit to them would be silent.
# -----------------------------------------------------------------------------------------------
FROZEN = {
    0x3AA96: (1, 0xFB, "LEVER B GATE -- ld.bu -0x6806[gp]. Carried from V104"),
    0x3AB76: (1, 0xAA, "Lever A r26 sar -- V62's edit is ABSENT (stock). Carried"),
    0x3AC20: (1, 0xAA, "Lever A r24 sar -- V62's edit is ABSENT (stock). Carried"),
    0x454FE: (1, 0xB5, "V42 byte -- MEASURED INERT (state 4 fires 0/123,277). Carried"),
    0x55DF2: (1, 0x7A, "CAN 427 SOURCE low byte -- gp-0x6b86, the biquad lane. Carried"),
    0x55E10: (1, 0xA4, "CAN 427 SCALER -- sar 0x4. Carried"),
    0x55D50: (4, bytes.fromhex("2436e0eb"), "CAN 399 packer -- BYTE-STOCK. The never-used hook"),
    0xC407E: (2, 511, "🛑 HARD-FAULT INTERLOCK -- Honda's 511, one under its own 512 trip"),
    0xC4080: (2, 0, "K0 -- NEVER RAISE (latent pure Coulomb relay)"),
    0xC40BC: (2, 300, "Coulomb ramp knee (V99). Closed at 6-9 Hz; carried"),
    0xC40D0: (2, 408, "friction EMA alpha"),
    0xC40D2: (2, 204, "K1 (V89) -- instrumented by b5, not dosed. Carried"),
    0xC40D4: (2, 573, "command-branch EMA -- VIRGIN"),
    0xC40D6: (2, 246, "accel/inertia EMA -- VIRGIN. THE INPUT SIDE OF THIS BUILD'S TERM"),
    0xC40D8: (2, 3686, "sensor-branch EMA -- VIRGIN"),
    0xC61F6: (2, 3, "r24 deadband -- TESTED AND REJECTED 2026-08-22, left at Honda's 3"),
    0xC6200: (2, 8192, "🛑 FOUR ROLES + a fault threshold. DO NOT EDIT"),
    0xC63A6: (2, 1024, "w[3] gp-0x6b26 INERTIA weight -- VIRGIN (b5's operand B lane)"),
    0xC63AA: (2, 1024, "w[5] gp-0x6b4c LKAS weight -- VIRGIN"),
    0xC63AE: (2, 1024, "🛑 LERP INDEX SCALE. NEVER -> 0 (flatten-into-relay). DO NOT EDIT"),
    0xC6446: (2, 5244, "LEVER B ARM (r24 engaged). Carried"),
    0xC6444: (2, 512, "r26 arm -- stock. 0xC6444 is FALSIFIED (flew as V71c). Carried"),
    0xC649B: (1, 1, "biquad ARM (V103). Carried -- E1 is inert without it"),
    0xC6CD0: (2, 5346, "🛑 THE 6x LKAS GAIN. The operator's stated requirement. UNTOUCHED"),
    0xC61B2: (2, 3072, "arbitration clamp, tracks the gain"),
    0xC61B4: (2, 3072, "arbitration clamp, tracks the gain"),
    0xC62EA: (2, 0, "low-speed steer lockout -- 0 since V53. Why Lever B's gate is live at creep"),
}

# V105's four biquad coefficients, byte-exact off the base -- carried, must not move.
BQ_CELLS = ((0xC60A8, "a1"), (0xC60AC, "a2"), (0xC60B0, "b1"), (0xC60B4, "c4"))

# Attributed non-stock spans, for the "zero unattributed" diff vs Honda.
# 🛑 IMPORTED FROM V105's OWN LEDGER, not retyped -- a hand-written copy of this table is exactly
# how an inherited-but-stale map goes unnoticed (see DOSE_FAMILY_Y).  Only the two spans THIS
# build owns are re-attributed from V92 to V106.
import build_v105_tva as V105B                                                    # noqa: E402

VS_STOCK = [row for row in V105B.VS_STOCK if row[0] not in (0xD7A5C, 0xD7A6C)] + [
    (0xD7A5C, 0xD7A62, "V106", "🛑 mode 26 ENGAGED Y -- THIS BUILD, x1.5 -> x3.0 stock"),
    (0xD7A6C, 0xD7A72, "V106", "🛑 mode 27 ENGAGED Y -- THIS BUILD, x1.5 -> x3.0 stock"),
]

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


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def s16(b, a):
    return struct.unpack_from("<h", b, a)[0]


def rd(b, a, w):
    return bytes(b[a:a + w])


def rdw(b, a, w):
    return u16(b, a) if w == 2 else (b[a] if w == 1 else rd(b, a, w))


def rec_addr(b, mode):
    return struct.unpack_from("<I", b, FRICTION_PTR_ARRAY + mode * 4)[0]


def rec_y(b, mode):
    return struct.unpack_from("<3h", b, rec_addr(b, mode) + REC_Y_OFF)


def rec_x(b, mode):
    return struct.unpack_from("<3h", b, rec_addr(b, mode) + REC_X_OFF)


def assert_frozen(buf, label):
    bad = []
    for a, (w, want, why) in sorted(FROZEN.items()):
        got = rdw(buf, a, w)
        if got != want:
            bad.append((a, got, want, why))
    for a, got, exp, why in bad:
        print(f"    {BAD} 0x{a:05X} is {got!r}, expected {exp!r} -- {why}")
    check(not bad, f"{label}: all {len(FROZEN)} FROZEN cells at their expected values")


def assert_family(buf, label, engaged_want):
    print(f"\n    friction/inertia dose family 0x{FRICTION_PTR_ARRAY:05X} ({label})")
    bad = []
    for m in MANUAL_MODES + ENGAGED_MODES:
        ra = rec_addr(buf, m)
        want = Y_STOCK if m in MANUAL_MODES else engaged_want
        got = rec_y(buf, m)
        role = "MANUAL " if m in MANUAL_MODES else "ENGAGED"
        if got != want:
            bad.append(m)
        mult = got[0] / Y_STOCK[0]
        print(f"      {OK if got == want else BAD} mode {m:2d} {role} record 0x{ra:05X} "
              f"Y@0x{ra + REC_Y_OFF:05X} = {got}  = x{mult:.2f} stock   X = {rec_x(buf, m)}")
    check(not bad, f"{label}: all 4 records as expected (manual STOCK, engaged {engaged_want})")


def build():
    print("=" * 102)
    print("  V106 -- gp-0x6b26 ACCELERATION-DAMPING TERM, x3.0 STOCK-RELATIVE, ENGAGED MODES ONLY")
    print("          12 cal bytes on a V105 base.  No cave change.  One CRC trailer.")
    print("=" * 102)

    # -------------------------------------------------------------------------------------------
    print("\n  [1] THE BASE -- V105, which FLEW as route a5 (verified from the wire, 3 legs)")
    base = bytearray(Path(BASE_BIN).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base is V105, sha256 {BASE_SHA[:24]}...")
    check(len(base) == 0x100000, f"base is {len(base)} bytes")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    stock = bytearray(Path(STOCK_BIN).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA and len(stock) == 0x100000,
          f"stock reference loaded, sha256 {STOCK_SHA[:24]}...")

    # -------------------------------------------------------------------------------------------
    print("\n  [2] FROZEN CELLS -- every one at its expected value BEFORE the edit")
    assert_frozen(base, "V105 base")
    print("\n    V105's four biquad coefficients -- CARRIED, must be byte-identical after E1")
    bq_before = {a: rd(base, a, 4) for a, _ in BQ_CELLS}
    for a, n in BQ_CELLS:
        v = struct.unpack_from("<f", base, a)[0]
        print(f"      0x{a:05X} {n} = {bq_before[a].hex()} = {v:+.9f}f")
    check(rd(base, 0xC60A8, 16) != rd(stock, 0xC60A8, 16),
          "the biquad block IS non-stock on the base (V105's notch) -- E1 must not disturb it")

    # -------------------------------------------------------------------------------------------
    print("\n  [3] THE POINTER TABLE -- four modes, resolved from the image, not from a map")
    print("      🛑 builds/v80_v107/build_v100_tva.py's DOSE_FAMILY_Y listed THREE. The row for this car has FOUR.")
    for m in MANUAL_MODES + ENGAGED_MODES:
        ra = rec_addr(base, m)
        lit = struct.pack("<I", ra)
        n = bytes(stock).count(lit)
        check(n == 1,
              f"mode {m}: record 0x{ra:05X} occurs EXACTLY {n} time as an LE32 literal image-wide "
              f"(at its own pointer slot 0x{FRICTION_PTR_ARRAY + m * 4:05X}) -- no aliasing table")
    assert_family(base, "V105 base", Y_V92)

    # -------------------------------------------------------------------------------------------
    print("\n  [4] 🛑 THE MODE PROOF -- b5's operand B is the cell this build doses")
    for lbl, a, want in (("A", B5_OPERAND_A_ADDR, B5_OPERAND_A_DISP),
                         ("B", B5_OPERAND_B_ADDR, B5_OPERAND_B_DISP)):
        got = s16(base, a)
        check(got == want,
              f"cave 0x{a:05X} = {rd(base, a, 2).hex()} = disp {got:+#07x} = gp{want:+#07x} "
              f"-- b5 operand {lbl}")
    print("      => b5 = ( |gp-0x6ae2| >= |gp-0x6b26| ) = ( FRICTION >= INERTIA ), and INERTIA")
    print("         is EXACTLY the cell E1 doubles.")
    print("      => b5 engaged duty MUST collapse if the car reads modes 26/27 engaged.")
    print("         b5 baseline on route a5: 0.2533 pooled, 0.4019 engaged < 16 km/h.")
    print("         MANUAL is the built-in control: the engaged arm moves, the manual arm does not.")
    print("      => RULE 7 ('mode-proof or it is a bet') is CLOSED by this build, at zero cost.")

    # -------------------------------------------------------------------------------------------
    print("\n  [5] E1 -- THE DOSE, DERIVED FROM HONDA'S OWN ROW BY AN INTEGER MULTIPLE")
    check(Y_V106 == tuple(v * DOSE for v in Y_STOCK),
          f"target {Y_V106} == {DOSE} x Honda's stock {Y_STOCK} -- computed, never typed as hex")
    check(Y_V92 == tuple(round(v * 1.5) for v in Y_STOCK),
          f"the carried value {Y_V92} is exactly x1.5 stock -- so E1 is a x2.0 step from the car")
    for v in Y_V106:
        check(-32768 <= v <= 32767, f"  {v} fits int16 (no wrap)")
    ovf = OVF_NUM // abs(Y_V106[0])
    check(ovf > GP6C2C_MAX_OBSERVED,
          f"int32 overflow threshold on |gp-0x6c2c| = {OVF_NUM}/{abs(Y_V106[0])} = {ovf} > "
          f"corpus max {GP6C2C_MAX_OBSERVED} -- {ovf / GP6C2C_MAX_OBSERVED:.1f}x of margin")

    code = bytearray(base)
    attributed = set()
    for m in ENGAGED_MODES:
        ya = rec_addr(code, m) + REC_Y_OFF
        pre = rec_y(code, m)
        check(pre == Y_V92, f"  mode {m} Y@0x{ya:05X} pre-image = {pre} (V92's x1.5)")
        struct.pack_into("<3h", code, ya, *Y_V106)
        attributed |= set(range(ya, ya + 6))
        print(f"      0x{ya:05X}  {bytes(base[ya:ya+6]).hex()} -> {bytes(code[ya:ya+6]).hex()}  "
              f"{pre} -> {rec_y(code, m)}")
    check(len(attributed) == 12, f"E1 wrote exactly {len(attributed)} bytes (expected 12)")

    print("\n  [6] POST-IMAGE -- the family, and everything that must NOT have moved")
    assert_family(code, "V106", Y_V106)
    for m in MANUAL_MODES:
        check(rec_y(code, m) == Y_STOCK,
              f"  mode {m} (MANUAL) still Honda stock {Y_STOCK} -- untouched by design")
    for a, n in BQ_CELLS:
        check(rd(code, a, 4) == bq_before[a],
              f"  biquad {n} @0x{a:05X} byte-identical to the V105 base")
    check(rd(code, CAVE_BASE, CAVE_LEN) == rd(base, CAVE_BASE, CAVE_LEN),
          f"  the whole {CAVE_LEN}-byte cave is byte-identical to V105 -- b5 still means what its "
          f"baseline was measured against")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          "  the cave's 0xFF tail is still virgin")
    check(s16(code, CLAMP_CAL) == 511 and 511 < MONITOR_TRIP,
          f"  🛑 0xC407E = 511 < {MONITOR_TRIP} -- the RULE-11 interlock is intact BY "
          f"CONSTRUCTION, not by care. V73 raised a clamp past its trip; V74/V75 both faulted")
    assert_frozen(code, "V106")

    # -------------------------------------------------------------------------------------------
    print("\n  [7] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    check(len(blocks) == 1,
          f"the edits span exactly 1 CRC block (both records are in the same 0x1000 page) -- "
          f"{[hex(b[1]) for b in blocks]}")
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

    # -------------------------------------------------------------------------------------------
    print("\n  [8] FULL BYTE DIFF vs THE V105 BASE -- every changed run, named")
    bruns = [i for i in range(START, END) if code[i] != base[i]]
    runs = []
    for i in bruns:
        if runs and i == runs[-1][1]:
            runs[-1][1] = i + 1
        else:
            runs.append([i, i + 1])
    stray = []
    for lo, hi in runs:
        span = set(range(lo, hi))
        if (lo & 0xFFF) >= 0xFFC:
            tag = "CRC trailer"
        elif span <= attributed:
            tag = "E1 -- engaged-mode Y row, x3.0 stock"
        else:
            tag = "?? UNATTRIBUTED"
            stray.append((lo, hi))
        print(f"      0x{lo:05X}..0x{hi-1:05X}  {hi-lo:>3} B  "
              f"{bytes(base[lo:hi]).hex():<14} -> {bytes(code[lo:hi]).hex():<14} {tag}")
    check(not stray, f"every changed run vs V105 is E1 or a CRC trailer"
                     + ("" if not stray else f"  -- STRAY {[(hex(a), hex(b)) for a, b in stray]}"))
    check(len(bruns) == 16, f"exactly {len(bruns)} bytes differ from V105 (12 payload + 4 CRC)")

    print("\n  [9] FULL BYTE DIFF vs HONDA STOCK -- zero unattributed")
    sruns = [i for i in range(START, END) if code[i] != stock[i]]
    scrc = {b + 0xFFC + k for b in range(0x13000, 0x100000, 0x1000) for k in range(4)}
    sattr = set()
    for lo, hi, bld, what in VS_STOCK:
        sattr |= {i for i in sruns if lo <= i < hi}
    sun = sorted(set(sruns) - sattr - scrc)
    print(f"      {len(sruns)} bytes differ from STOCK, {len(sattr)} attributed, "
          f"{len(set(sruns) & scrc)} CRC trailers")
    check(not sun, "ZERO unattributed bytes vs stock"
                   + ("" if not sun else f"  -- {[hex(x) for x in sun[:16]]}"))

    # -------------------------------------------------------------------------------------------
    print("\n  [10] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 OK")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V106 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if EXPECT_IMG_SHA:
        check(img_sha == EXPECT_IMG_SHA, "image SHA matches the frozen expectation")
        check(rwd_sha == EXPECT_RWD_SHA, ".rwd SHA matches the frozen expectation")
    else:
        print("      (SHAs not yet frozen -- first clean run; paste them into EXPECT_*_SHA)")

    if WRITE_MODE == "rwd":
        Path(BIN_OUT).write_bytes(bytes(code))
        Path(OUT).write_bytes(rwd)
        print(f"\n  [11] WRITTEN\n      {BIN_OUT}\n      {OUT}")
        disk = bytearray(Path(BIN_OUT).read_bytes())
        check(hashlib.sha256(bytes(disk)).hexdigest() == img_sha, "plain image re-read from disk")
        assert_frozen(disk, "SHIPPED image")
        assert_family(disk, "SHIPPED image", Y_V106)
        check(s16(disk, B5_OPERAND_B_ADDR) == B5_OPERAND_B_DISP,
              "shipped: b5's operand B still gp-0x6b26, re-read from disk")
        check(rd(disk, CAVE_BASE, CAVE_LEN) == rd(base, CAVE_BASE, CAVE_LEN),
              "shipped: cave byte-identical to V105, from disk")
    else:
        print("\n  [11] NOT WRITTEN -- set ACCORD_V106_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  V106 [{TOKEN}]")
    print(f"    {_checks[1]}/{_checks[0]} assertions PASSED")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  E1  0xD7A5C / 0xD7A6C -- gp-0x6b26's Y row on the two ENGAGED modes,")
    print(f"      {Y_V92} -> {Y_V106}  = x{DOSE}.0 stock, x2.0 of the car.")
    print(f"      An ACCELERATION-damping term: H(0) = 0 EXACTLY, so it cannot rate-limit a held")
    print(f"      6x command at any multiplier.  Gain 1.478 @7.79 Hz, 3.706 @21.73 Hz.")
    print(f"      Modes 24/25 (MANUAL) left at Honda's stock -- dosing them would be inert for an")
    print(f"      engagement-conditional symptom and would change manual feel instead.")
    print(f"  MODE PROOF: the carried b5 rung ( |gp-0x6ae2| >= |gp-0x6b26| ) reads out the dose.")
    print(f"      Engaged duty MUST collapse from its 0.4019 baseline if the car reads 26/27")
    print(f"      engaged; unchanged means the V91/V92 mode-record suspicion is CONFIRMED.")
    print(f"  UNTOUCHED: 0xC407E = 511 (the interlock), 0xC6CD0 = 5346 (the 6x gain), the biquad,")
    print(f"      the cave, Lever B, and both manual modes.")
    print(f"  CRC: one trailer, 0x{blocks[0][1]:06X}.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
