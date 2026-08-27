#!/usr/bin/env python3
r"""builds/v80_v107/build_v88_tva.py -- V88 = V87 + LEVER B restored + the probe's rectification hole closed.

★ THE ONE-LINE REASON THIS BUILD EXISTS
----------------------------------------
V87 flew (route `71`) and did exactly what it promised: it MEASURED, and it changed nothing. The
operator reported grinding, micro-ratcheting and ratcheting on it. **That is the predicted result of
a build that is byte-stock at every grind-#1 lever the kit has ever measured** -- verified here, on
V87's own image, at all four addresses. V88 restores the better of the two measured fixes and fixes
the one defect that stopped V87's probe from closing its fork.

WHAT V87's TELEMETRY ACTUALLY SAID (route 71, 240 s, 124 s engaged, creep, no faults)
--------------------------------------------------------------------------------------------------
The 427 probe FIRED: `MOTOR_TORQUE` went from 56-67 % non-zero / 240-297 distinct values on V86/V86B
to **99.0 % non-zero / 946 distinct / railing 3.2 %** -- a different signal, measured against both
predecessor routes as controls.

  * `|gp-0x6b98|` engaged: median **208 counts**, p90 **966**, railed (>=1637) **2.35 %**.
  * Its 6-9 Hz ripple engaged: **rms 29.0 counts, p-p 162 counts.**  The kit's ASSUMED value was
    "~120 counts p-p" and STATE.md warned the answer might swing 5x. It did not: the assumption was
    low by 1.35x. **That unknown is now closed.**
  * THE FORK, on rectification-transparent unclipped engaged windows: the ~7.7 Hz line is
    **prominence 12.9 in the COLUMN torque (50 % of windows above the white-noise p95 floor)** and
    **4.0 in the DELIVERED COMMAND (7.1 % of windows -- i.e. chance)**. openpilot's own command:
    2.96, 7.1 %.  ⇒ the ratcheting is NOT a line the EPS is commanding.
  * BUT the link is real and frequency-selective: pooled coherence `|gp-0x6b98|` <-> column torque
    is **0.439 at 7.79 Hz against a shuffled-pairs control of 0.178** and a background of 0.03-0.16,
    and the command's own line prominence correlates **+0.62** with the column's across windows,
    rising to 12.7 in the top ratchet quartile.
  ⇒ **A lightly-damped mode driven by BROADBAND command content, not by a commanded oscillation.**
    The lever is therefore "less broadband HF in the delivered command", NOT "notch out a tone".
  * And the broadband content is engagement-made. SPEED-MATCHED (2-4 m/s), engaged/manual band rms
    of the delivered command: 0.5-3 Hz **0.42x**, 3-6 Hz 0.73x, 6-9 Hz 1.73x, 9-12 Hz 1.76x,
    12-15 Hz 1.79x, **15-22 Hz 3.37x (CIs disjoint)**. Engagement REMOVES low-frequency command
    motion and ADDS high-frequency motion, most of all in grind #1's own band.

🛑 TWO READINGS FROM THAT SESSION WERE WITHDRAWN BEFORE THEY REACHED THIS BUILD, by their controls:
   1. a "differentiator" transfer `op cmd -> delivered` rising 9x with frequency. At coherence
      0.035-0.077 against a 1/n_avg = 0.043 null, the zero-coherence estimator
      `sqrt(Pyy/Pxx)/sqrt(n_avg)` reproduces the measurement in ALL SEVEN bands (ratio 0.89-1.08).
      It carried no transfer information.
   2. the phase-randomised surrogate as a "no line" control. Phase randomisation PRESERVES |X(f)|,
      so for a single-window periodogram it preserves the line's power. The load-bearing control is
      the white-noise floor at the same `nw`, plus the PAIRED column-torque comparison.

THE BASE -- V87, so the control delta is SINGLE-VARIABLE against a build that has flown
--------------------------------------------------------------------------------------------------
`_v87_V38BASE-V57GAIN-RATCHET454FE-STEER0-PROBE.427.6B98_plain_image.bin`
sha256 27530836dfc121ecf9f62a4dd136abc79484ef2e12af54f55591ac71c334e034

THE EDIT SET -- 4 sites, 5 bytes actually changed.  No cave is created, moved, grown or shrunk.
--------------------------------------------------------------------------------------------------
  #  addr       w  from    to      what
  1  0x3AA96    1  c5      fb      LEVER B gate: ld.bu -0x683c[gp] -> -0x6806[gp] ("LKAS applying")
  2  0xC6446    2  512     5244    LEVER B arm: r24's gain = flat 5244 while LKAS applies = 2.000x
  3  0xC4B38    2  9094    6894    cave probe source: gp-0x6b70 -> gp-0x6b98  <<< THE SIGN FIX
  4  0xC4B46    1  a6      a8      cave magnitude rung: sar 0x6 -> sar 0x8, trips at 256 not 64
  (#3 writes two bytes but only ONE differs: -0x6b70 = 0x9490 and -0x6b98 = 0x9468 share the high
   byte.  So the whole build is 1 + 2 + 1 + 1 = 5 changed bytes, plus CRC trailers.)

★ WHY #1+#2 (LEVER B) AND WHY IT IS *THE* GRIND-#1 LEVER
   Two grind-#1 fixes have ever been MEASURED on this car, and **V87 carries neither** -- asserted
   below from V87's own bytes:
       Lever A  V62's `sar` x2   0x3AB76 / 0x3AC20 = `aa` (stock)   effect 0.39 [0.32, 0.48]
       Lever B  V67/V68's gate   0x3AA96 = `c5`, 0xC6446 = 512      effect 0.40 [0.27, 0.58]
   Lever B is chosen over Lever A on three grounds already in the record:
     - it is the best measured result in the kit AND took creep grind #2 to **zero bursts**;
     - Lever A's `sar` is STRUCTURALLY SHARED across all four priority-chain arms, so it cannot be
       made LKAS-conditional, and its unconditional r24 half is what produced the operator's
       *"makes the entire car vibrate regardless of LKAS engagement"*;
     - Lever B is gated on "LKAS applying", so it costs the driver nothing when disengaged.

★ THE `TVCA4` HAZARD, CHECKED AND CLEARED -- this could have voided the dose
   `v66_v67_explained` derives the arm from **mode-10** gain_B records, and
   `reference-accord-car-is-tvca4-mode-24-26` records that this car reads modes **24/26** and that
   three earlier builds shipped byte-stock because they wrote mode 10. Re-derived here from the
   image's OWN pointer arrays: mode 24 and mode 26 gain_B are **byte-identical to each other**, and
   differ from mode 10 by at most **2 counts (0.09 %)**. The LERP at grind #1's operating point is
   **2622 in all three modes**, so `5244 / 2622 = 2.0000x` exactly on the car's real records.
   Asserted, not assumed: `assert_mode24_dose()` fails the build otherwise.
   ⚠ RESIDUAL, unchanged from V67 and restated rather than smoothed: a SCALAR arm cannot track a
   CURVE. Across the LKAS-on regime the multiplier runs **1.77x - 2.55x** (1.77 at 2 km/h with a
   slow wheel, 2.55 at 80 km/h with a fast one). 2.00x is V62's proven dose and, per
   `accord-v62-fixed-the-grinding`, **2x is the OPTIMUM, not a point on a ramp** -- do not raise it.

🛑 THE "RESIDUAL" OF LEVER B IS NOT A RESIDUAL -- IT IS PART OF THE FIX. THIS CORRECTS THE RECORD.
   The repoint puts **r26's arm on the same gate**: while LKAS applies, `0xC6444` = 512 replaces
   r26's own LERP (3072 at creep), a 6x REDUCTION on that lane. V67 excused it as "r26 is inert";
   LEG 1 of that claim was later REVERSED, and the memory
   `accord-rate-lane-builds-were-never-single-variable` therefore names `0xC6444` as the decoupler
   and calls raising it **"UNTESTED: a candidate"**.
   🛑 **THAT MEMORY IS WRONG, and this build's own cross-image matrix caught it.** `0xC6444` = 3072
   has FLOWN -- it is **V71c**, which is exactly `V67 + 0xC6444 512->3072 + 0x454FE` and nothing
   else. `archive/LEDGER-V38-TO-V84.md:236` records the result:
       * grind #1 `e_18-22` = **223** vs V67/V68's **109** -- below stock, but **excluded HIGHER
         than V67 (P = 0.0215)**, i.e. removing the r26 cut made grind #1 WORSE;
       * **grind #2 came BACK**: 7 bursts at 44.31 Hz, p99 = **12.2x** the max of any non-bursting
         build, against V67/V68's **zero** bursts at creep;
       * **the ratchet hit 8,521 counts p-p -- the corpus RECORD.**
   ⇒ **Raising `0xC6444` is FALSIFIED, not untested**, and the 6x r26 cut is a LOAD-BEARING part of
   Lever B rather than a defect in it. `0xC6444` stays at Honda's 512 here, and it is **not** a
   candidate for V89 either. FALSIFIED != untested; the memory is corrected in this session.

★ WHY #3 -- THE PROBE'S ONE DEFECT, AND IT IS THE ONE THAT BLOCKED THE FORK
   427 delivers `clamp(|gp-0x6b98|*5>>3, 0, 0x3FF)`. `abs()` is transparent only while the signal
   holds one sign. On route 71 it did so in **0 of 42** 10.28 s windows, and in only 14 of 37 at
   5.14 s -- at creep the driver passes through centre constantly. A 7.79 Hz oscillation about zero
   folds to 15.58 Hz, so "no line at 7.7 Hz in the probe" is ALSO what a real line would produce.
   V88 repoints the flown cave's source load to the same cell, giving **b7 = sign(gp-0x6b98) at
   100 Hz**. Combined with 427's magnitude at 50 Hz that reconstructs the SIGNED delivered command,
   and the fork closes on evidence instead of on a screened subset.
   ★ THE ENCODING IS NOT HAND-DERIVED. `24376894` is byte-identical to the 427 packer's own source
   load at `0x55DF0` on this very base -- an instruction that has already flown reading exactly this
   cell. Asserted from the image, both halfwords.

★ WHY #4 -- placing the 1-bit rung where it carries information
   `sar 0x6` trips the magnitude rung at +-64 counts. Against a measured engaged median of 208 that
   rung would sit saturated. `sar 0x8` moves it to +-256, i.e. onto the distribution's centre, which
   is where a 1-bit comparator has maximum information (`accord-probe-underranges-to-one-bit-
   comparator`: under-ranged, but a USABLE SPECTRAL probe). At 100 Hz it is also an
   ALIAS-INDEPENDENT check on the 50 Hz 427 channel, whose 24.9 Hz Nyquist cannot separate the
   15-22 Hz shelf from a folded 28-35 Hz object.

★ THE IDENTITY TEST FOR THE FLIGHT, WITH ITS CONTROL ALREADY MEASURED
   On V88 the cave and the 427 packer read the SAME cell, so `b6` must agree with
   `wire >= (256*5)>>3 = 160` frame by frame. On route 71 (V87) that same predicate agrees only
   **40.2 %** of the time, because the cave was reading `gp-0x6b70`. ⇒ a parameter-free
   discriminator with a measured control: **~1.00 means V88 flew, ~0.40 means V87 did.**

GATE 1 -- RAM OWNERSHIP: **nothing new is written.** #1 and #3 change the DISPLACEMENT of two loads;
   #4 changes an immediate; #2 is a calibration halfword. The cave's only store is still
   `st.b r6,-0x1514[gp]`, the established telemetry byte, byte-identical and asserted below.
GATE 2 -- CLOSED-LOOP STABILITY: #3 and #4 are read-only telemetry and touch no loop. #1+#2 raise
   r24's DERIVATIVE feedback by 2.000x while LKAS applies -- phase LEAD, i.e. damping, in the band
   that rings; it has flown twice (V67, V68) at exactly this dose on a build carrying exactly this
   4.000x forward LKAS gain. Linearity: the lane's +-8192 clamp needs |dtorque| >= 1601 counts
   against V65's measured 123-839 over 120,049 frames, and the ten-lane sum clip to +-10240 was
   measured never reached. Both re-derived from `v66_v67_explained` here, not quoted.

🛑 HONEST LABEL -- AND IT IS NOT "THIS FIXES THE GRINDING"
   Lever B has flown **seven times** (V67, V68, V71c, V84, V85, V86, V86B) and the record calls it
   **"CONFIRMED-FIX, AT ITS CEILING ... tops out at V67's level, which the operator still calls
   grinding"**. V88 does not beat that ceiling and is not claimed to. What it does:
     1. **puts the car back to the best state the kit has ever measured**, which V87's V38 rebase
        deliberately gave up;
     2. **makes Lever B's MECHANISM observable for the first time.** Every previous Lever B flight
        was scored on the column torque -- an OUTPUT. V87's probe now exposes `|gp-0x6b98|`, the
        delivered command, so V88 vs V87 is a single-variable A/B on the thing Lever B actually
        changes. The pre-registration is in the handoff: Lever B must CUT the delivered command's
        15-22 Hz broadband content (measured on V87 at 3.37x manual, CIs disjoint). If it does not,
        the "broadband HF in the command drives a lightly-damped plant mode" reading is wrong, and
        that is worth more than another attenuation point.
   It is **NOT a ratcheting lever**: nothing in it targets the ~7.8 Hz mode, whose firmware search
   the record marks CLOSED by a shape argument. If the ratcheting is unchanged, that is the
   PREDICTION, not a surprise.
   ⊕ The operator scores the symptoms. Bands are the instrument, never the verdict.
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

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
import build_v67_tva as V67                # noqa: E402  -- Lever B's constants, never re-typed
import build_v86_tva as V86                # noqa: E402  -- the cave listing
import build_v86b_tva as V86B              # noqa: E402  -- the flown payload + bit weights
import v66_v67_explained as EX             # noqa: E402
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V88_WRITE", "").strip().lower()

BASE_BIN = str(plain_image_path(
    "_v87_V38BASE-V57GAIN-RATCHET454FE-STEER0-PROBE.427.6B98_plain_image.bin"))
BASE_SHA = "27530836dfc121ecf9f62a4dd136abc79484ef2e12af54f55591ac71c334e034"

# ---- the cave, on V87's image -----------------------------------------------------------------
CAVE_BASE = 0xC4B34
CAVE_LEN = 62                                   # V87 wrote V86B's payload minus its 6-byte 0xFF pad
CAVE_PAD_LEN = 6
PROBE_LOAD_OFF = 4                              # hw2 of `ld.h -0x6b70[gp],r6`
MAG_SAR_OFF = 18                                # `sar 0x6,r6`
TWIN_LOAD_ADDR = 0x55DF0                        # the 427 packer's own `ld.h -0x6b98[gp],r6`

OLD_DISP, NEW_DISP = 0x6B70, 0x6B98
OLD_SHIFT, NEW_SHIFT = 6, 8
NEW_MAG_T = 1 << NEW_SHIFT                      # 256 counts
WIRE_OF = lambda c: (c * 5) >> 3                # noqa: E731  Honda's packer, for the identity test

# ---- control edits: (addr, width, expect_before, value_after, label) ----------------------------
EDITS = [
    (V67.REPOINT_BYTE, 1, bytes([V67.REPOINT_FROM[2]]), bytes([V67.REPOINT_TO[2]]),
     "LEVER B gate: ld.bu -0x683c[gp],r15 -> -0x6806[gp],r15  (LKAS-applying)"),
    (V67.ARM_ADDR, 2, struct.pack("<H", V67.ARM_STOCK), struct.pack("<H", V67.ARM_NEW),
     f"LEVER B arm: r24 gain = flat {V67.ARM_NEW} while LKAS applies = 2.000x the LERP"),
]
CAVE_EDITS = [
    (CAVE_BASE + PROBE_LOAD_OFF, 2, struct.pack("<H", (-OLD_DISP) & 0xFFFF),
     struct.pack("<H", (-NEW_DISP) & 0xFFFF),
     "cave probe source: gp-0x6b70 -> gp-0x6b98 (the delivered motor command)  <<< SIGN FIX"),
    (CAVE_BASE + MAG_SAR_OFF, 1, bytes([0xA0 | OLD_SHIFT]), bytes([0xA0 | NEW_SHIFT]),
     f"cave magnitude rung: sar 0x{OLD_SHIFT:x} -> sar 0x{NEW_SHIFT:x}, trips at +-{NEW_MAG_T}"),
]

VARIANT_TOKEN = "V87BASE-LEVERB.GATE6806.ARM5244-PROBE.427.6B98-CAVE.6B98.SIGN.MAG256"
TAG = VARIANT_TOKEN
BIN_OUT = str(plain_image_path(f"_v88_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V88-{TAG}-0x{START:X}-0x{END:X}.rwd")

# cells that must NOT move -- levers excluded, known traps, and everything V87 froze
FROZEN = {
    0x3AB76: (1, "Lever A r26 `sar` -- EXCLUDED (structurally shared, cannot be LKAS-gated)"),
    0x3AC20: (1, "Lever A r24 `sar` -- EXCLUDED (its unconditional half caused the V62 complaint)"),
    0xC6444: (2, "r26's arm -- the DECOUPLER. Deliberately stock 512: V89's single variable"),
    0xC6440: (2, "r24 third arm (gp-0x671a) -- untouched"),
    0xC6442: (2, "r24 mask arm (gp-0x671d) -- untouched, and it OUTRANKS Lever B's arm"),
    0xC643E: (2, "r26 state<5 arm -- untouched"),
    0xC40BC: (2, "V85 friction relay -- not on this base, stays Honda 600"),
    0xC40D4: (2, "command EMA -- V86's FALSIFIED lever, stays 573"),
    0xC63B4: (2, "8 Hz bandpass alpha -- REFUTED, stays 51"),
    0xC63B8: (2, "8 Hz bandpass gain -- REFUTED five ways, stays 41"),
    0xC646E: (2, "INERTIA gain -- its sizing figure is an UNMEASURED estimate, stays 1428"),
    0xC407E: (2, "the hard-fault interlock clamp -- Honda's 511, one under its own 512 trip"),
    0xD77DA: (2, "FactorC m26 Y[0] -- V86B's engaged creep damper, stays 0"),
    0xD77EE: (2, "FactorC m27 Y[0] -- V86B's engaged creep damper, stays 0"),
    0xC646C: (2, "shared sensor scale -- Honda 891 (V57 decoupling preserved)"),
    0xC6CD0: (2, "private forward LKAS gain -- 3564 = 4.000x, NEVER lower it"),
    0xC62EA: (2, "steer-to-zero -- 0"),
}


def rd(buf, addr, w):
    return bytes(buf[addr:addr + w])


def u16(buf, addr):
    return struct.unpack_from("<H", buf, addr)[0]


def i16(buf, addr):
    return struct.unpack_from("<h", buf, addr)[0]


# ===================================================================================================
#  THE `TVCA4` DOSE CHECK -- re-derived from the image's OWN pointer arrays, for modes 24 and 26
# ===================================================================================================
GAIN_B_PTR_ARRAYS = (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214)
CAR_MODES = (24, 26)


def _rec(buf, p):
    n = i16(buf, p)
    return n, [i16(buf, p + 2 + 2 * i) for i in range(n)], \
        [i16(buf, p + 2 + 2 * n + 2 * i) for i in range(n)]


def _gain_q10(buf, mode, speed_counts, motor_rate):
    """r24's default LERP for `mode`, read from the image -- the mode-agnostic form of
    `EX.r24_gain_q10`, whose GAIN_B_MODE10 table is hard-coded to mode 10."""
    recs = []
    for A in GAIN_B_PTR_ARRAYS:
        p = struct.unpack_from("<I", buf, A + 4 * mode)[0]
        assert 0 < p < 0x100000, f"gain_B ptr array 0x{A:X}[{mode}] = 0x{p:X}, out of image"
        n, xs, ys = _rec(buf, p)
        assert n == 4, f"gain_B mode {mode} record at 0x{p:X} declares {n} points"
        recs.append((xs, ys))
    xs = [EX._lerp_flat(speed_counts, EX.CROSS_X, [r[0][i] for r in recs]) for i in range(4)]
    ys = [EX._lerp_flat(speed_counts, EX.CROSS_X, [r[1][i] for r in recs]) for i in range(4)]
    key = 0 if motor_rate >= EX.RATE_FOLD else motor_rate
    return EX._lerp_flat(key, xs, ys)


def assert_mode24_dose(buf):
    """🛑 RULE 7: mode-proof or it is a bet.  The arm's 2.000x must hold on the CAR's records."""
    sc, mr = V67.GRIND1_SPEED_COUNTS, V67.GRIND1_RATE_COUNTS
    print("\n  🛑 `TVCA4` DOSE CHECK -- the arm re-derived on the CAR's own mode-24/26 records")
    ref = None
    for mode in CAR_MODES + (10,):
        g = _gain_q10(buf, mode, sc, mr)
        tag = "the car" if mode in CAR_MODES else "the helper's hard-coded table"
        print(f"    mode {mode:2d}: LERP = {g:5d}   {V67.ARM_NEW}/LERP = "
              f"{V67.ARM_NEW / g:.4f}x   ({tag})")
        if mode in CAR_MODES:
            assert g == V67.GRIND1_LERP, \
                f"🛑 mode {mode} LERP is {g}, not {V67.GRIND1_LERP} -- the dose is NOT 2.000x " \
                "on this car and 5244 is the wrong number. STOP."
            ref = g if ref is None else ref
    for A in GAIN_B_PTR_ARRAYS:
        p24 = struct.unpack_from("<I", buf, A + 4 * 24)[0]
        p26 = struct.unpack_from("<I", buf, A + 4 * 26)[0]
        assert rd(buf, p24, 18) == rd(buf, p26, 18), \
            f"🛑 gain_B mode 24 and 26 differ at ptr array 0x{A:X} -- mode 26 must be re-checked"
    print(f"    ✅ mode 24 == mode 26 byte-identical in all 4 gain_B arrays; "
          f"{V67.ARM_NEW}/{V67.GRIND1_LERP} = 2.0000x EXACTLY")
    lo = min(V67.ARM_NEW / _gain_q10(buf, 24, int(k * 64.0625),
                                     int(d * EX.RATE_COUNTS_PER_DEGS))
             for k in (2, 5, 7.2, 15, 30, 50, 80) for d in (32, 128, 400))
    hi = max(V67.ARM_NEW / _gain_q10(buf, 24, int(k * 64.0625),
                                     int(d * EX.RATE_COUNTS_PER_DEGS))
             for k in (2, 5, 7.2, 15, 30, 50, 80) for d in (32, 128, 400))
    print(f"    ⚠ a SCALAR arm against a CURVE: the multiplier runs {lo:.2f}x-{hi:.2f}x across the "
          f"LKAS-on regime")
    assert 1.5 < lo and hi < 3.0, f"the multiplier leaves [1.5,3.0]: {lo:.2f}-{hi:.2f}"
    return lo, hi


def assert_lane_linearity():
    """The lane must stay LINEAR at the doubled gain, or the dose does not propagate faithfully."""
    thresh = None
    for d in range(1, EX.INPUT_CLAMP + 1):
        if abs(EX.r24_lane(d, V67.ARM_NEW, 10)) >= EX.LANE_CLAMP:
            thresh = d
            break
    print(f"    lane +-{EX.LANE_CLAMP} clamp is reached at |dtorque| >= {thresh} counts, against "
          f"V65's MEASURED 123-839 over 120,049 frames")
    assert thresh is not None and thresh > 1000, f"the lane clamps at {thresh} -- too close"
    assert EX.r24_lane(839, V67.ARM_NEW, 10) == (839 * V67.ARM_NEW >> 10) - EX.DEADZONE, \
        "the lane is not linear at the top of the measured input range"
    return thresh


# ===================================================================================================
#  THE CAVE, DERIVED -- V86's listing with exactly two substitutions, never re-typed
# ===================================================================================================
def build_cave_v88():
    body = bytearray(V86B.CAVE_PAYLOAD[:CAVE_LEN])          # == V87's payload, byte-for-byte
    assert rd(body, PROBE_LOAD_OFF, 2) == struct.pack("<H", (-OLD_DISP) & 0xFFFF)
    assert body[MAG_SAR_OFF] == (0xA0 | OLD_SHIFT) and body[MAG_SAR_OFF + 1] == 0x32
    body[PROBE_LOAD_OFF:PROBE_LOAD_OFF + 2] = struct.pack("<H", (-NEW_DISP) & 0xFFFF)
    body[MAG_SAR_OFF] = 0xA0 | NEW_SHIFT
    out = bytes(body)
    # ⊕ -0x6b70 = 0x9490 and -0x6b98 = 0x9468 share their HIGH byte, so the displacement edit
    # ⊕ changes ONE byte of the two written.  The cave therefore moves by 2 bytes, not 3.
    diff = [i for i in range(CAVE_LEN) if out[i] != V86B.CAVE_PAYLOAD[i]]
    assert diff == [PROBE_LOAD_OFF, MAG_SAR_OFF], \
        f"🛑 the V87->V88 cave differs at {diff}, expected exactly " \
        f"[{PROBE_LOAD_OFF}, {MAG_SAR_OFF}]"
    return out


CAVE_V88 = build_cave_v88()

# ---- the V88 bit map. Weights are V86B's (V87 flew them); only the SOURCE CELL and the rung move.
BIT_SIGN, BIT_MAG, BIT_NONZERO = V86B.BIT_SIGN, V86B.BIT_MAG, V86B.BIT_NONZERO   # 0x80/0x40/0x20
BIT_GATE, BIT_FINGERPRINT = V86B.BIT_GATE, V86B.BIT_FINGERPRINT                  # 0x10/0x08
GATE_T = V86B.GATE_T
M32 = 0xFFFFFFFF


def wire_byte4(v6b98, gate, status_bits=0x7):
    """Python mirror of V88's cave, structurally identical to V86B's with sar 0x8 and a new source.

    b7 = gp-0x6b98 < 0   b6 = |gp-0x6b98| >= 256   b5 = gp-0x6b98 != 0   b4 = gp-0x67ab < 2  b3 = 1
    """
    r7, r6 = 0, v6b98
    if not (r6 & M32) <= 0:                                  # cmp 0 / bnh  (UNSIGNED) => v != 0
        r7 += 2
    if not r6 >= 0:                                          # cmp 0 / bge  (SIGNED)   => v < 0
        r7 += 8
    r6 = (r6 >> NEW_SHIFT) + 1
    if not (r6 & M32) <= 1:                                  # => |v| >= 256 (trips +256 / -257)
        r7 += 4
    r6 = gate & 0xFF
    if not (r6 & M32) >= GATE_T:
        r7 += 1
    r7 = ((r7 << 4) & M32) + BIT_FINGERPRINT
    return ((status_bits & V86B.PAYLOAD_KEEP_MASK) | r7) & 0xFF


def decode_byte4(b):
    if not b & BIT_FINGERPRINT:
        return None
    return {"sign": bool(b & BIT_SIGN), "mag": bool(b & BIT_MAG),
            "nonzero": bool(b & BIT_NONZERO), "gate": bool(b & BIT_GATE)}


def _self_check_wire():
    for v in (0, 1, -1, 255, 256, -256, -257, 1000, -1000, 32767, -32768):
        d = decode_byte4(wire_byte4(v, 0))
        assert d["sign"] == (v < 0), f"b7 wrong at v={v}"
        assert d["nonzero"] == (v != 0), f"b5 wrong at v={v}"
        assert d["mag"] == (v >= NEW_MAG_T or v <= -NEW_MAG_T - 1), f"b6 wrong at v={v}"
    for g in (0, 1, 2, 3, 255):
        assert decode_byte4(wire_byte4(0, g))["gate"] == (g < GATE_T)
    # the rung MUST have moved, or edit #4 bought nothing
    assert wire_byte4(100, 0) & BIT_MAG == 0 and V86B.wire_byte4(100, 0) & BIT_MAG, \
        "🛑 v=100 must set MAG on V86B/V87 and clear it on V88 -- the rung did not move"
    # the identity discriminator must be a real discriminator
    assert WIRE_OF(NEW_MAG_T) == 160, WIRE_OF(NEW_MAG_T)


def assert_cave_encoding(buf):
    """The new load must be BYTE-IDENTICAL to an instruction already flying on this base."""
    twin = rd(buf, TWIN_LOAD_ADDR, 4)
    ours = CAVE_V88[PROBE_LOAD_OFF - 2:PROBE_LOAD_OFF + 2]
    assert ours == twin, (f"🛑 the cave's new load {ours.hex()} differs from the 427 packer's own "
                          f"`ld.h -0x6b98[gp],r6` at 0x{TWIN_LOAD_ADDR:05X} ({twin.hex()})")
    assert struct.unpack("<h", twin[2:])[0] == -NEW_DISP
    print(f"    ✅ cave load {ours.hex()} == the FLOWN 427 packer's load at "
          f"0x{TWIN_LOAD_ADDR:05X} -- same cell, same encoding, already proven on-car")
    tail = bytes.fromhex(V86.CAVE_LISTING[-2][0] + V86.CAVE_LISTING[-1][0])
    assert CAVE_V88[-6:] == tail == bytes.fromhex("2436e8ea7f00"), \
        "the cave tail moved -- it must stay `movea -0x1518,gp,r6` + `jmp [lp]`"
    assert bytes.fromhex("4437ecea") in CAVE_V88, "the cave's ONLY store (gp-0x1514) is missing"
    assert CAVE_V88.count(bytes.fromhex("4437ecea")) == 1, "more than one store in the cave"


# ===================================================================================================
def build():
    base = bytearray(Path(BASE_BIN).read_bytes())
    assert len(base) == 0x100000
    base_sha = hashlib.sha256(bytes(base)).hexdigest()
    assert base_sha == BASE_SHA, f"the V87 base is {base_sha}, expected {BASE_SHA}"
    assert walk_all_blocks(bytes(base)) == 0, "the V87 base's CRC chain does not verify"
    print("=" * 102)
    print("  V88 -- V87 + LEVER B restored + the probe's rectification hole closed")
    print(f"    base {os.path.basename(BASE_BIN)}\n    sha256 {base_sha}")
    print("=" * 102)

    # ---- V87 carries NEITHER measured grind-#1 fix: proved from ITS OWN bytes -------------------
    print("\n  🛑 V87 IS BYTE-STOCK AT EVERY MEASURED GRIND-#1 LEVER -- read from the base image")
    for addr, w, stock, name in ((0x3AB76, 1, 0xAA, "Lever A r26 `sar 0xa`"),
                                 (0x3AC20, 1, 0xAA, "Lever A r24 `sar 0xa`"),
                                 (0x3AA96, 1, 0xC5, "Lever B gate byte"),
                                 (0xC6446, 2, 512, "Lever B arm")):
        got = u16(base, addr) if w == 2 else base[addr]
        assert got == stock, f"0x{addr:05X} is {got}, expected stock {stock}"
        print(f"    0x{addr:05X} = {got if w == 2 else f'0x{got:02x}':<6} STOCK   {name}")
    print("    ⇒ the grinding the operator reported on V87 is an ABSENCE OF ANY FIX, not a")
    print("      regression.  ⚠ Unlike V81's, this absence was NOT silent -- V87's own handoff")
    print("      states the V38 rebase dropped Lever B.  It is a KNOWN cost being paid back here.")

    _self_check_wire()
    assert_cave_encoding(base)
    lo_mult, hi_mult = assert_mode24_dose(base)
    print("\n  GATE 2 -- lane linearity at the doubled gain")
    assert_lane_linearity()

    # ---- the V67 consumer chain must be intact on THIS base ------------------------------------
    print("\n  LEVER B -- the `lp` chain, asserted from the base image (V67's own anchors)")
    for a, want, why in V67.LP_CHAIN:
        assert rd(base, a, len(want)) == want, f"0x{a:05X} is not {want.hex()} -- {why}"
        print(f"    0x{a:05X} {want.hex():<10} {why}")
    assert rd(base, V67.REPOINT_ADDR, 4) == V67.REPOINT_FROM, "the repoint site is not stock"
    for t in V67.REPOINT_TWINS:
        assert rd(base, t, 4) == V67.REPOINT_TO, \
            f"0x{t:05X} is not a byte-identical twin of what the repoint writes"
    print(f"    ✅ the bytes the repoint WRITES ({V67.REPOINT_TO.hex()}) already exist verbatim at "
          f"{', '.join(f'0x{t:05X}' for t in V67.REPOINT_TWINS)}")
    assert V67.FIRST_JARL_AFTER > V67.LP_CHAIN[-1][0], "a `jarl` precedes a consumer -- lp unsafe"

    code = bytearray(base)
    attributed = set()

    print("\n  CONTROL EDITS")
    for addr, w, pre, post, lbl in EDITS:
        got = rd(code, addr, w)
        assert got == pre, f"0x{addr:05X}: expected {pre.hex()}, found {got.hex()}"
        code[addr:addr + w] = post
        attributed.update(range(addr, addr + w))
        print(f"    0x{addr:05X} {w}B  {pre.hex():>8} -> {post.hex():<8}  {lbl}")

    print("\n  INSTRUMENT EDITS (in place, inside the thrice-flown cave)")
    for addr, w, pre, post, lbl in CAVE_EDITS:
        got = rd(code, addr, w)
        assert got == pre, f"0x{addr:05X}: expected {pre.hex()}, found {got.hex()}"
        code[addr:addr + w] = post
        attributed.update(range(addr, addr + w))
        print(f"    0x{addr:05X} {w}B  {pre.hex():>8} -> {post.hex():<8}  {lbl}")
    assert rd(code, CAVE_BASE, CAVE_LEN) == CAVE_V88, \
        "the patched cave is not the independently derived V88 payload"
    assert all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_BASE + CAVE_LEN + CAVE_PAD_LEN]), \
        "the cave pad is not 0xFF"
    assert rd(code, V67.HOOK_ADDR, 4) == bytes.fromhex("86ff26ef"), "the cave hook moved"
    print(f"    ✅ the 62-byte cave now equals the derived V88 payload; hook and 6-byte pad "
          f"untouched")

    print("\n  FROZEN CELLS (must equal the V87 base)")
    for addr, (w, why) in sorted(FROZEN.items()):
        assert rd(code, addr, w) == rd(base, addr, w), f"0x{addr:05X} MOVED -- {why}"
        v = u16(code, addr) if w == 2 else code[addr]
        print(f"    0x{addr:05X} = {v:<6} unchanged   {why}")

    # ---- CRC ------------------------------------------------------------------------------------
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    print(f"\n  CRC -- {len(blocks)} block(s) move")
    for blk in blocks:
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(code[blk[0]:blk[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        owners = [a for a in touched if blk[0] <= a < blk[1]]
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old:08X} -> 0x{new:08X}"
              f"   owns {len(owners)} byte(s)")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    assert walk_all_blocks(bytes(code)) == 0, "CRC chain FAILED"
    assert not [a for a in attributed if 0xC5000 <= a < 0xC5FFC], \
        "🛑 an edit landed in [0xC5000,0xC5FFC) -- the block the bootloader SKIPS (V40's brick)"
    assert not [a for a in attributed if a < START or a >= END], "an edit landed outside the region"
    print("    ✅ full 50-block chain: 50/50 PASS · 0 bytes into [0xC5000,0xC5FFC)")

    # ---- zero-unattributed full diff --------------------------------------------------------------
    by_addr = {}
    for addr, w, pre, post, lbl in EDITS + CAVE_EDITS:
        for k in range(w):
            by_addr[addr + k] = f"0x{addr:05X}  {lbl}"

    def attribute(d):
        return by_addr.get(d, "CRC trailer" if d in crc_only else None)

    runs, i = [], 0
    while i < len(code):
        if code[i] != base[i]:
            j = i
            while j < len(code) and code[j] != base[j]:
                j += 1
            runs.append((i, j - 1))
            i = j
        else:
            i += 1
    stray = [d for a, b in runs for d in range(a, b + 1) if attribute(d) is None]
    total = sum(b - a + 1 for a, b in runs)
    print("\n" + "=" * 102)
    print("  🛑 FULL BYTE DIFF: BUILT V88 vs the V87 base -- over the WHOLE 1 MiB image")
    print(f"    {len(runs)} differing run(s), {total} byte(s) total")
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X} {b - a + 1:4d}  {attribute(a)}")
    assert not stray, f"🛑 UNATTRIBUTED bytes vs V87: {[hex(x) for x in stray[:16]]}"
    rt = bytearray(code)
    for a in attributed | crc_only:
        rt[a] = base[a]
    assert hashlib.sha256(bytes(rt)).hexdigest() == base_sha, "the round trip does not reproduce V87"
    print("    ⇒ ZERO unattributed bytes; restoring the attributed set reproduces V87 BIT-FOR-BIT.")

    # ---- value-anchored verification, read back from the BUILT image ------------------------------
    print("\n  VALUE ANCHORS (read back from the BUILT image)")
    for addr, w, want, why in ((0xC6446, 2, V67.ARM_NEW, "LEVER B arm = 2.000x the LERP"),
                               (0xC6444, 2, 512, "r26 arm STOCK -- V89's variable, not V88's"),
                               (0xC6CD0, 2, 3564, "forward LKAS gain = 4.000x, unchanged"),
                               (0xC646C, 2, 891, "shared sensor scale = Honda stock"),
                               (0xC646E, 2, 1428, "INERTIA untouched"),
                               (0xC63B8, 2, 41, "8 Hz bandpass untouched"),
                               (0xC40BC, 2, 600, "friction relay at Honda stock"),
                               (0xC407E, 2, 511, "fault interlock at Honda's 511")):
        got = u16(code, addr)
        assert got == want, f"0x{addr:05X} = {got}, expected {want}"
        print(f"    0x{addr:05X} = {got:<6} {why}")
    assert code[0x3AA96] == 0xFB and rd(code, V67.REPOINT_ADDR, 4) == V67.REPOINT_TO
    assert code[0x454FE] == 0xB5, "V42 ratchet fix lost"
    assert rd(code, 0x55DF2, 2) == bytes.fromhex("6894"), "the 427 probe was lost"
    assert rd(code, 0x2A1F0, 2) == bytes.fromhex("d07c"), "the V57 repoint was lost"
    assert code[0x3AB76] == 0xAA and code[0x3AC20] == 0xAA, "Lever A must stay stock"
    print(f"    0x3AA96 = fb     LEVER B gate -> gp-0x6806 (ld.bu {V67.REPOINT_TO.hex()})")
    print("    0x454FE = b5     V42 ratchet fix intact")
    print("    0x55DF2 = 6894   427 MOTOR_TORQUE <- |gp-0x6b98| intact")
    print(f"    0xC4B38 = 6894   cave probe    <- gp-0x6b98  (b7 = SIGN, at 100 Hz)")
    print(f"    0xC4B46 = a8     cave rung     <- |gp-0x6b98| >= {NEW_MAG_T}")

    # ---- the flight's identity test, with its measured control ------------------------------------
    print("\n  IDENTITY TEST FOR THE FLIGHT (parameter-free, control already measured on route 71)")
    print(f"    On V88 the cave and the 427 packer read the SAME cell, so per frame")
    print(f"        b6  ==  (MOTOR_TORQUE >= {WIRE_OF(NEW_MAG_T)})        [ = (256*5)>>3 ]")
    print(f"    must hold. Measured on route 71 (V87, cave reading gp-0x6b70): agreement 0.402")
    print(f"    ⇒ ~1.00 means V88 flew · ~0.40 means V87 did.  No free parameter.")

    # ---- .rwd -------------------------------------------------------------------------------------
    source_rwd = Path(FF.V38_RWD).read_bytes()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd drifted"
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(decode))])
    FF.assert_x31_checksum(rwd, "V88 output")
    back = parse_x31(rwd)
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(dec) == bytes(code), "the readback is not byte-identical to the built image"
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    assert dec[0x3AA96] == 0xFB and u16(dec, 0xC6446) == V67.ARM_NEW
    assert rd(dec, CAVE_BASE, CAVE_LEN) == CAVE_V88
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print("\n    ✅ READBACK: the decoded .rwd payload is byte-identical to the built image; "
          "anchors and the 50/50 chain re-verified from it.")

    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V88_WRITE=rwd to cut.")
    else:
        existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
        if existing is not None and existing != bytes(code):
            raise SystemExit(f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists.")
        Path(BIN_OUT).write_bytes(bytes(code))
        print(f"  wrote {BIN_OUT}\n    SHA256 {img_sha}  ({len(code)} bytes)")
        if WRITE_MODE == "rwd":
            if os.path.exists(OUT) and Path(OUT).read_bytes() != rwd:
                raise SystemExit(f"🛑 a DIFFERENT {OUT} already exists -- ONE .rwd per build number.")
            Path(OUT).write_bytes(rwd)
            print(f"  wrote {OUT}\n    SHA256 {rwd_sha}  ({len(rwd)} bytes)")
            shipped = Path(OUT).read_bytes()
            assert hashlib.sha256(shipped).hexdigest() == rwd_sha
            FF.assert_x31_checksum(shipped, "V88 shipped")
            sd = bytearray(base)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(decode)
            assert bytes(sd) == bytes(code), "🛑 the SHIPPED .rwd does not decode to the built image"
            assert walk_all_blocks(bytes(sd)) == 0, "shipped-from-disk CRC chain FAILED"
            on_disk = Path(BIN_OUT).read_bytes()
            assert hashlib.sha256(on_disk).hexdigest() == img_sha and on_disk == bytes(code)
            print("  ✅ FROM-DISK: the shipped .rwd was re-read, re-hashed, checksum-verified, "
                  "decoded and re-verified INDEPENDENTLY.")

    print(f"\n  V88 [{VARIANT_TOKEN}]")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print("  🛑 HONEST LABEL: Lever B has flown SEVEN times and the record calls it CONFIRMED-FIX,")
    print("     AT ITS CEILING -- V88 does not beat that ceiling. It (1) puts the car back to the")
    print("     best state the kit has measured, and (2) makes Lever B's MECHANISM observable for the")
    print("     first time, via V87's probe. It is NOT a ratcheting lever.")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


def _self_check():
    assert len(CAVE_V88) == CAVE_LEN == 62
    assert len(EDITS) == 2 and sum(w for _, w, _, _, _ in EDITS) == 3
    assert len(CAVE_EDITS) == 2 and sum(w for _, w, _, _, _ in CAVE_EDITS) == 3
    assert len({a for a, *_ in EDITS + CAVE_EDITS}) == 4, "duplicate address"
    assert 0xC6444 in FROZEN and 0x3AB76 in FROZEN and 0x3AC20 in FROZEN
    assert 0xC63B8 in FROZEN and 0xC646E in FROZEN
    assert "+" not in VARIANT_TOKEN and all(c.isalnum() or c in ".-" for c in VARIANT_TOKEN)
    assert len(OUT) < 250, len(OUT)
    _self_check_wire()


if __name__ == "__main__":
    _self_check()
    build()
