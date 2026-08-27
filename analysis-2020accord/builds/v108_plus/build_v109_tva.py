#!/usr/bin/env python3
r"""
V109 -- V108 PLUS THE BAND-LIMIT.  ONE CELL, TWO BYTES, AND THE GATE IS CLOSED.

WHAT THIS IS
------------
V109 = V108, plus `cal(0xC40DC)` 22 -> 14.  Nothing else.  **Two payload bytes and one CRC trailer.**

`0xC40DC` is alpha2, the SECOND one-pole EMA in the acceleration cascade that feeds `gp-0x6b26`:

    FUN_00041464:
      y0        += ((gp-0x4f50*1024 - y0) * cal(0xC643C)=37) >> 7     # EMA1, alpha0  -- SHARED, untouched
      gp-0x6abe  = (short)(y0 >> 10)                                   # Honda's damper input
      gp-0x6ac0  = (short)(|y0| >> 10)                                 # the 0xC520C cap-table index
      d32        = clamp((y0[n] - y0[n-1]) * 32, +-0xFA0000)
      gp-0x35a0 += ((d32 - gp-0x35a0) * cal(0xC40DC)=22) >> 6          # EMA2, alpha2  <- THE LEVER
      gp-0x6c2c  = (short)(gp-0x35a0 >> 9)                             # read at ld.hu 0x50dc,tp,r11 @0x41626

**IT IS VIRGIN ON ALL 103 BUILT IMAGES.**  Every prior touch of this lane changed its MAGNITUDE (V106's
uniform x3.0) or its SPEED SCHEDULE (V107's reshape).  **Nothing has ever changed its SHAPE.**

WHY SHAPE IS THE RIGHT AXIS
---------------------------
The lane is not a damper above ~30 Hz.  It is a BANDPASS peaking at 61.1 Hz, -3 dB from 25.1 to
153.0 Hz, never below 4.49x anywhere to Nyquist -- and at 100 Hz it runs at 10.86x, **40 % MORE gain
than at the 21.7 Hz mode it was designed to damp.**  V107 delivered x8.14 of that at highway speed and
the operator reported a NEW grinding at several hundred Hz.

Lowering alpha2 moves the bandpass peak DOWN toward the mode and rolls off the skirt.  Uncompensated
(no Y change -- see below for why), at alpha2 = 14:
```
     f Hz     1      3     7.79   21.73    27     40    61.1    100    200    300    499
   a2=22    0.402  1.203  3.080  7.723  9.029 11.150 12.136 10.860  7.151  5.445  4.488
   a2=14    0.402  1.201  3.042  7.105  8.022  9.099  8.881  7.133  4.339  3.245  2.656
   ratio    1.000  0.998  0.988  0.920  0.888  0.816  0.732  0.657  0.607  0.596  0.592
```
⇒ **~0 % cost at manoeuvre frequencies, 1.2 % at the 7.8 Hz ratchet, 8 % at the mode -- and a 27-40 %
CUT across 61-300 Hz, exactly where the operator's new symptom is.**  That is the trade the whole
V104-V107 arc was missing: every one of those builds could only move the lane's HEIGHT, which pays for
any high-frequency reduction one-for-one at 21.7 Hz.  **Shape does not.**

WHY UNCOMPENSATED -- DO NOT SPEND Y[0]
--------------------------------------
Holding `|H|` at 21.73 Hz exactly would need Y x1.087, and Y[0] = -29490 is already **90.0 %** of the
int16 floor (-32768), leaving only x1.11.  It fits -- but it should not be spent:
  1. The only knot with room to give is Y[0], the CREEP knot, and creep is where the relay is WORST
     (measured 33.5 % rail duty at 10-25 km/h).  Compensating would push Y[0] to 97.8 % of the int16
     floor **at the knot where the relay is already worst**, to recover a number nobody can feel.
  2. An 8 % magnitude change at the mode is **below the ~9 % perceptual floor on record**, and V103's
     own build note prices ~10 % as "PREDICTED IN ADVANCE TO READ 'NO CHANGE'".
  3. Uncompensated, the dose at creep goes slightly DOWN, which nudges that 33.5 % the right way.
⭐ **And the exact boundary, worth remembering: 29490 x 1/0.90 = 32,767 against a floor of 32,768 -- a
-10 % alpha2 cut is the LAST one Y[0] could compensate at all.**  Past that the int16 door closes.

🛑 GATE 1 -- CLOSED.  ALL FOUR CONSUMERS OF `gp-0x6c2c`, NOT THREE.
-------------------------------------------------------------------
The cell itself: **exactly ONE gp/tp access image-wide** (`ld.hu 0x50dc,tp,r11` @`0x41626`), **zero
writers**, confirmed by Ghidra AND an independent Python LE scan with the `disp|1` trap handled
(`hw2 = 0x50DD`, one hit at file offset `0x41628`); the 6-byte extended form and the register-indirect
form (667 `movhi -0x121,r0,rN` sites) both return **zero additional hits**.

The SIGNAL's fan-out was the real gate, and the first census undercounted it:
| consumer | verdict |
|---|---|
| `FUN_00036c12` -- the friction/inertia lane | **the lever's intended target.**  Not a safety question. |
| `FUN_000428d4` -- the oscillation-detector FSM | **SAFE, and the direction IMPROVES margin.**  It arms on `\|gp-0x6c2c\| > cal(0xC620A) = 12800` against a corpus max of ~5,300 -- already 2.4-2.5x below threshold -- and V64 flew with **1,158 steering-rate reversals and ZERO arms**.  Cutting the 61-300 Hz content that dominates this signal's peaks makes it structurally LESS reachable. |
| `FUN_00071272` -- the FOC-adjacent float staging | **SAFE.**  `gp-0x6c2c` enters only as an instantaneous magnitude (`x 2^-16`) into a sequential bound-tightening MIN comparator; its flag bit reaches `gp-0x4b0`, whose ONE genuine value read (`ld.bu -0x4b0,gp,r12` @`0x7532A`) stores it into **byte 0x10 of a 36-byte-stride record array at `gp-0x26e8`** -- a 2-slot rotating diagnostic log, alongside 8 other signals.  **No `FUN_000462e6` DTC dispatch anywhere near it.** |
| `FUN_0007b022` -- the cap-table/governor-ceiling function | **SAFE.**  `gp-0x6c2c` x 2^-6 -> clamp to +-`cal(0xC55A4)` = 500.0 (corpus scales to ~80-83, **6x below**, non-binding) -> abs -> LERP.  The function's tail has FIVE possible outputs; **four (`gp-0x4f52`, `gp-0x4e98`, `gp-0x4f66`, `gp-0x4ea2`) have ZERO readers by every census method**, and the fifth -- `gp-0x4f64`, the governor ceiling -- was cleared by tracing **its own three producers** in all three branches: fed by `gp+0x184` (line ~590's chain) and `gp+0x130`-derived `fVar45`, **neither `gp-0x6c2c`**. |
🛑 **`gp-0x6c2e` and its own cal `0xC40DA` = 3 are PROVEN INDEPENDENT AT THE PRODUCER**, not merely
uncorrelated: separate state cell (`gp-0x35a4` vs `gp-0x35a0`), separate cal, separate shift (`>>7` vs
`>>6`).  `cal(0xC40DC)` appears nowhere in `gp-0x6c2e`'s recursion and **structurally cannot move it at
any K2.**  Second, independent reason: their reader sets are **completely disjoint** (`FUN_00034350` /
`FUN_00034a72` / `FUN_00036f30` vs the four above), so no consumer could compare them even in principle.
⊕ No shadow-lockstep pair on `gp-0x6c2c` or `gp-0x6c2e` themselves; the protection lands one hop
downstream on `gp-0x6b26` vs `gp-0x4cd0`, and that check runs unmodified on whatever value it computes.

🛑 GATE 2 -- CLEAN AT THE MODE, WITH ONE REAL COST STATED
---------------------------------------------------------
The torque phasor stays in the proven-safe **180-270 deg** sector at 21.73 Hz for every K2 from 22 down
to **3**; it crosses out at K2 = 2.  K2 = 14 is comfortably inside.
⚠ **THE COST NOBODY HAD PRICED, and it is real:** lowering alpha2 slides the **90-180 deg sector ENTRY
DOWN**, 74.1 -> 54.0 Hz -- *widening* by ~20 Hz the band in which this lane can structurally sustain an
oscillation.  The magnitude there is also cut (to 80-85 %), so the net is very likely positive, but the
earlier hope that this was "an independent second benefit" was **REFUTED**: the sector boundary and the
mode-band authority trade against the same knob in the same direction.
🛑🛑 **AND THAT IS EXACTLY WHY THIS MUST SHIP ON A V108 BASE.**  Across 54-74.5 Hz -- the band K2 = 14
newly opens -- V105's biquad coefficients leave the parallel base-assist lane a geometric-mean **5.15x
(+14.2 dB)** louder than Honda's, and **21.8x at the sector's new entry point**, because Honda's own
zero sits at 55.225 Hz and V105 moved it to 25.5.  **V108 reverts that notch to Honda's, so the
prerequisite is already on the car in this build.  DO NOT ship alpha2 on a V107 base.**

🛑 THE OLD "POLE FORK IS DEAD" VERDICT DOES NOT TRANSFER
--------------------------------------------------------
`reference_accord_gp6b26_two_paths_reinforce_and_pole_fork_dead` moved **this same pole** to rotate the
21.7 Hz operating point **further INTO** 90-180 deg for more inertia-reduction, and found the Y cost
prohibitive.  **This lever moves the same pole in the OPPOSITE direction -- toward pure damping, AWAY
from that crossing at the mode** -- which is why it stays inside the proven-safe sector down to K2 = 3.
The old verdict was about crossing INTO 90-180 at the mode; it does not apply to staying further away
from it, which is what this does.

🛑 WHAT CANNOT BE PREDICTED, AND WHY THIS IS AN EXPERIMENT
----------------------------------------------------------
**Rail duty under a candidate alpha2 is NOT computable.**  The only available method is the open-loop
push-through that was measured **32x WRONG** on this exact lane (V107 predicted <=1.05 %, route `1e`
measured 33.49 %), because `gp-0x6b26` -> aggregator -> motor -> motor rate -> `gp-0x6c2c` **is a closed
loop** and the input distribution is not invariant to the gain.  The loop term is now measured at
**14-16x** (median `|gp-0x6c2c|` engaged vs manual at matched speed), i.e. **~94 % of the engaged signal
is loop-generated**.  And alpha2 sits UPSTREAM of `gp-0x6c2c`, so it changes the very distribution any
solve would stand on -- which the 49.8 Hz, 1636.8-count-censored 427 channel cannot recover.
Pushing route `1e`'s measured marginal through the filter identity gives a BRACKET, and at
alpha2 <= 14 the required threshold falls beyond the fitted tail's finite upper endpoint, so the answer
becomes tail-family-dependent and spans essentially the full width.  **A closed-loop simulator is also
unavailable: the identified column model's validity band is 5-13 Hz while this lane's -3 dB span is
25-153 Hz, so 100 % of it is extrapolation.**
⇒ **The direction is supported (probably better, plausibly a lot better); the MAGNITUDE is not.
V109 is a deliberate single-variable experiment against V108, and that two-point contrast is the only
thing that can size this cell.**  Read it that way, and read a null as informative.

WHAT V109 DOES NOT DO
---------------------
It does not touch the ratcheting (a ~7.8 Hz LOOP resonance whose Re(Z) census is a DENOMINATOR problem
-- the loop cancels ~93 % of the mode's own damping, which no additive term can produce), and it does
not touch the visible oscillation (route `1e` contains nothing of that magnitude on four independent
channels; that search is live and has been redirected).  **Say so plainly to the operator.**

Usage:
    ACCORD_FIRMWARE_ROOT=C:/Users/dudei/Desktop/Projects/accord-firmwares \
    ACCORD_V109_WRITE=rwd python builds/v108_plus/build_v109_tva.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------

import cmath
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

import build_vfourframe_tva as FF                                                 # noqa: E402
import build_v53_tva as V53                                                       # noqa: E402
import build_v106_tva as V106B                                                    # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table     # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                 # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V109_WRITE", "").strip().lower()

BASE_NAME = "_v108_V108-V107BASE-NOTCH.HONDA-GP6B26.Y1REVERT-C40BC.600-TAP.SAR5_plain_image.bin"
BASE_SHA = "7a9577dd181a235845e87e592fbd1a191957674aef7b0f17caac6907c114a9e4"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd, rdw = V106B.u16, V106B.s16, V106B.rd, V106B.rdw
rec_y, rec_x = V106B.rec_y, V106B.rec_x
Y_STOCK = V106B.Y_STOCK
Y_V108 = (-29490, -17202, -16000)
X_EXPECT = (0, 1280, 5760)
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES

ALPHA2_CAL = 0xC40DC                   # THE ONLY EDIT
ALPHA2_OLD, ALPHA2_NEW = 22, 14
ALPHA2_DEN = 64                        # the >>6 in FUN_00041464
ALPHA0_CAL, ALPHA0_VAL, ALPHA0_DEN = 0xC643C, 37, 128
SIBLING_CAL, SIBLING_VAL = 0xC40DA, 3  # alpha2's twin -> gp-0x6c2e.  MUST NOT MOVE.
DETECTOR_T = 0xC620A                   # 12800, the oscillation detector's threshold
CLAMP_CAL, MONITOR_TRIP = V106B.CLAMP_CAL, V106B.MONITOR_TRIP
BQ_ADDR, BQ_LEN = 0xC60A8, 16          # V108's Honda-restored notch -- the PREREQUISITE
GAIN_CAL = 0xC6CD0

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


def lane_H(a0, a2, f, fs=1000.0):
    """|H(f)| of 64 * EMA(a0) * (1 - z^-1) * EMA(a2), mirroring FUN_00041464's cascade."""
    z = cmath.exp(-2j * cmath.pi * f / fs)
    h1 = (a0 / ALPHA0_DEN) / (1 - (1 - a0 / ALPHA0_DEN) * z)
    h2 = (a2 / ALPHA2_DEN) / (1 - (1 - a2 / ALPHA2_DEN) * z)
    return abs(64 * h1 * (1 - z) * h2)


def lane_phase(a0, a2, f, fs=1000.0):
    z = cmath.exp(-2j * cmath.pi * f / fs)
    h1 = (a0 / ALPHA0_DEN) / (1 - (1 - a0 / ALPHA0_DEN) * z)
    h2 = (a2 / ALPHA2_DEN) / (1 - (1 - a2 / ALPHA2_DEN) * z)
    return (cmath.phase(64 * h1 * (1 - z) * h2) * 180 / cmath.pi + 180) % 360


FROZEN = dict(V106B.FROZEN)
FROZEN[GAIN_CAL] = (2, 5346, "0xC6CD0 -- the 6.000x forward LKAS gain.  NEVER lower it.")
FROZEN[SIBLING_CAL] = (2, SIBLING_VAL, "0xC40DA -- alpha2's SIBLING -> gp-0x6c2e.  Proven independent; untouched.")
FROZEN[ALPHA0_CAL] = (2, ALPHA0_VAL, "0xC643C -- alpha0, SHARED with the 0xC520C cap-table index.  Untouched.")
FROZEN[DETECTOR_T] = (2, 12800, "0xC620A -- the oscillation detector's threshold.  Untouched.")
FROZEN[0xC40BC] = (2, 600, "0xC40BC -- Honda's 600, restored by V108.")
FROZEN[0xC40D2] = (1, 204, "K1 -- kept knowingly; reverting makes the wheel HEAVIER")
FROZEN[0xC61BE] = (2, 15360, "0xC61BE -- the LKAS request clip.  Measured IDLE; E3 was pulled at V108.")
FROZEN[0x55E10] = (1, 0xA5, "427 SCALER -- sar 5, from V108")
FROZEN[0x55DF2] = (1, 0xD4, "427 SOURCE low byte -- gp-0x6c2c, from V107")
FROZEN[ALPHA2_CAL] = (2, ALPHA2_NEW, "0xC40DC -- alpha2, THE EDIT")


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


def build():
    print("=" * 102)
    print("  V109 -- V108 + the BAND-LIMIT.  One cell, two bytes, and GATE 1 is closed.")
    print("=" * 102)

    print("\n  [1] LOAD AND PIN THE BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    stock = bytearray(Path(plain_image_path("stock_fw_dump/code.bin")).read_bytes())
    check(hashlib.sha256(base).hexdigest() == BASE_SHA, f"base is V108 ({BASE_SHA[:16]}...)")
    check(hashlib.sha256(stock).hexdigest() == STOCK_SHA, "stock image sha256 matches the record")
    check(walk_all_blocks(bytes(base)) == 0, "base image CRC chain 50/50 before we touch it")
    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE PREREQUISITE -- V109 MUST SIT ON A V108 BASE, NOT A V107 ONE")
    check(rd(base, BQ_ADDR, BQ_LEN) == rd(stock, BQ_ADDR, BQ_LEN),
          "  the biquad is Honda's (V108's E1) -- required, because alpha2 moves the 90-180 deg")
    print("      sector entry DOWN to 54.0 Hz, and across 54-74.5 Hz V105's notch left the parallel")
    print("      base-assist lane a geometric-mean 5.15x (+14.0 dB) louder than Honda's.")
    check(rec_y(base, ENGAGED_MODES[0]) == Y_V108, f"  the Y row is V108's {Y_V108}")
    check(u16(base, ALPHA2_CAL) == ALPHA2_OLD == u16(stock, ALPHA2_CAL),
          f"  0x{ALPHA2_CAL:05X} = {ALPHA2_OLD} on the car AND in stock -- VIRGIN in 103 builds")
    check(u16(base, SIBLING_CAL) == SIBLING_VAL == u16(stock, SIBLING_CAL),
          f"  0x{SIBLING_CAL:05X} = {SIBLING_VAL} (alpha2's sibling) -- byte-stock, and it stays that way")
    assert_frozen(base, "BASE(V108)", extra_exempt=(ALPHA2_CAL,))

    print("\n  [3] THE EDIT -- alpha2 22 -> 14.  TWO BYTES.")
    struct.pack_into("<H", code, ALPHA2_CAL, ALPHA2_NEW)
    attributed |= {ALPHA2_CAL, ALPHA2_CAL + 1}
    print(f"      0x{ALPHA2_CAL:05X}  {ALPHA2_OLD} -> {ALPHA2_NEW}   "
          f"(alpha2 {ALPHA2_OLD}/{ALPHA2_DEN} = {ALPHA2_OLD/ALPHA2_DEN:.4f} -> "
          f"{ALPHA2_NEW}/{ALPHA2_DEN} = {ALPHA2_NEW/ALPHA2_DEN:.4f})")
    print()
    print(f"      {'f Hz':>7} {'a2=22':>8} {'a2=14':>8} {'ratio':>7}   {'phase(14)':>9}  sector")
    worst_in_band = 1.0
    for f in (1, 3, 7.79, 21.73, 27, 40, 61.1, 74.5, 100, 200, 300, 499):
        a, b = lane_H(ALPHA0_VAL, ALPHA2_OLD, f), lane_H(ALPHA0_VAL, ALPHA2_NEW, f)
        ph = lane_phase(ALPHA0_VAL, ALPHA2_NEW, f)
        sec = "180-270 SAFE" if 180 <= ph <= 270 else "90-180"
        if 18 <= f <= 30:
            worst_in_band = min(worst_in_band, b / a)
        print(f"      {f:7.2f} {a:8.3f} {b:8.3f} {b/a:7.3f}   {ph:9.2f}  {sec}")

    ph_mode = lane_phase(ALPHA0_VAL, ALPHA2_NEW, 21.73)
    check(180 <= ph_mode <= 270,
          f"  GATE 2: the phasor at 21.73 Hz is {ph_mode:.2f} deg -- INSIDE the proven-safe 180-270 sector")
    r_mode = lane_H(ALPHA0_VAL, ALPHA2_NEW, 21.73) / lane_H(ALPHA0_VAL, ALPHA2_OLD, 21.73)
    check(r_mode > 0.90,
          f"  the mode-band cost is {100*(1-r_mode):.1f} % -- below the ~9 % perceptual floor on record")
    r100 = lane_H(ALPHA0_VAL, ALPHA2_NEW, 100) / lane_H(ALPHA0_VAL, ALPHA2_OLD, 100)
    check(r100 < 0.75, f"  and 100 Hz is cut to {r100:.3f} -- the band the operator now reports")
    check(lane_H(ALPHA0_VAL, ALPHA2_NEW, 3) / lane_H(ALPHA0_VAL, ALPHA2_OLD, 3) > 0.99,
          "  manoeuvre frequencies (3 Hz) are untouched -- this costs NO steering rate")

    print("\n  [4] EVERYTHING THAT MUST NOT HAVE MOVED")
    check(u16(code, SIBLING_CAL) == SIBLING_VAL,
          "  0xC40DA (gp-0x6c2e's own cal) untouched -- proven independent at the producer")
    check(u16(code, ALPHA0_CAL) == ALPHA0_VAL,
          "  0xC643C (alpha0) untouched -- it is SHARED with the 0xC520C cap-table index")
    check(u16(code, DETECTOR_T) == 12800,
          "  0xC620A untouched -- and the detector gets LESS reachable, not more")
    check(s16(code, CLAMP_CAL) == 511 and 511 < MONITOR_TRIP,
          f"  0xC407E = 511 < {MONITOR_TRIP} -- RULE-11 interlock intact BY CONSTRUCTION")
    check(rd(code, V106B.CAVE_BASE, V106B.CAVE_LEN) == rd(base, V106B.CAVE_BASE, V106B.CAVE_LEN),
          "  THE CAVE IS BYTE-IDENTICAL -- no code-cave edit, the kit's only bricking class")
    for m in MANUAL_MODES:
        check(rec_y(code, m) == Y_STOCK, f"  mode {m} (MANUAL) still Honda stock")
    for m in ENGAGED_MODES:
        check(rec_y(code, m) == Y_V108 and rec_x(code, m) == X_EXPECT,
              f"  mode {m} Y row unchanged from V108 -- alpha2 is UNCOMPENSATED, by design")
    check(rd(code, BQ_ADDR, BQ_LEN) == rd(stock, BQ_ADDR, BQ_LEN),
          "  the biquad is still Honda's -- alpha2's prerequisite holds in the built image")
    assert_frozen(code, "V109")

    print("\n  [5] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{old:08X} -> 0x{new:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    print("\n  [6] FULL BYTE DIFF vs V108 -- ZERO UNATTRIBUTED")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    runs, unattributed = [], [a for a in diff if a not in attributed]
    for a in diff:
        if runs and a == runs[-1][1]:
            runs[-1][1] = a + 1
        else:
            runs.append([a, a + 1])
    for lo, hi in runs:
        tag = "CRC" if any(lo <= x < hi for x in (b[1] for b in blocks)) else "payload"
        print(f"      0x{lo:05X}..0x{hi-1:05X}  {hi-lo:3d} B  {tag:8s} "
              f"{bytes(base[lo:hi]).hex()} -> {bytes(code[lo:hi]).hex()}")
    check(not unattributed,
          f"every one of {len(diff)} differing bytes in {len(runs)} runs is attributed")

    print("\n  [7] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V109 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V109-V108BASE-ALPHA2.C40DC.14"
    img_out = plain_image_path(f"_v109_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [8] NOT WRITTEN -- set ACCORD_V109_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
