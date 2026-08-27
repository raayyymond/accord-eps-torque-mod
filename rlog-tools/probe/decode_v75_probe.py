#!/usr/bin/env python3
"""probe/decode_v75_probe.py -- read V75's probe: a MAGNITUDE THERMOMETER on the damper, plus the
back-drive gate.

🛑🛑 STATUS: V75 is **BUILT, UNFLASHED, FLIGHT CONDITIONAL** -- not cleared to fly. The route-5d
abort check put V74's own 5x-f0 prominence at 2.884 [2.301, 3.575] against a 3.0 abort line, and its
CREEP-ONLY arm at 5.844 against a 0.632 baseline, and creep is exactly where LEVER CY0 acts. If you
are running this decoder on a log, someone made a flight decision -- confirm the .rwd filename below
before reading a single number out of it.

WHAT V75 IS -- so a reader of this file cannot mistake the artefact
--------------------------------------------------------------------
V74 put the damper in force for the first time in this kit (its `bit7` fired), but at only ~50 counts
on the live mode 26, and its four state bits read a CONSTANT 5 in 101,117 of 101,118 frames -- four
bits spent on a cell that never moved. V75 is V74 **plus additions only**:

  LEVER CY0  FactorC `Y[0] := 566` on the ENGAGED column of all 16 rows (the 13 modes below).
          Raises only the CREEP end of the speed axis; the plateau `C_Y[3]` that sets the surface
          maximum is untouched.
  LEVER EX1  FactorE `X[1] := 200` on the same 13 modes. Moves a BREAKPOINT left, steepening the
          low-rate ramp. The plateau `Y[1] = Y[2]` and the maximum `Y[3]` are untouched.
          🛑 FactorE's whole Y ROW IS FROZEN -- it has zero verified headroom.
  ★ THE TWO LEVERS ARE INDEPENDENTLY TOGGLEABLE and the flown cut is named in `RWD_NAME` below.
    Alone they deliver: CY0 only 66 (1.32x) · EX1 only 104 (2.08x) · both 137 (2.74x), all at the
    measured in-burst rate 99 on mode 26. 🛑 **The cave is byte-identical across all three**, so
    THIS DECODER CANNOT TELL THEM APART -- the filename is the only discriminator.
  ⇒ On the live mode 26: **50 -> 137 counts (2.74x)** at the measured in-burst rate 99, and
    66 -> 181 at the 6-9 Hz arm's rate 127. Both edits are free under the no-clip rule, verified two
    ways: 0 raised points above the ceiling floor on a 98,988-point grid, and the GLOBAL PEAK
    byte-identical to V74's on every engaged mode.
  ⚠ Modes 2 and 3 are HELD at V74's `C_Y[0] = 1356`, not lowered to 566 -- writing 566 there would
    SUBTRACT 790 counts. Their own no-clip cap is 2076, so this is the add-only rule, not a cap.
  UNTOUCHED  the friction records (V74's x1.5), `0xC407E` = 850, the whole r24/r26 rate lane incl.
          V72's r26 cut, both `sar` sites at STOCK (**reintroducing V62's `a9` causes grind #2 --
          the fix is an ABSENCE**), the gate, both scalar arms, `0x454FE`, and `0xC77A0` -- the
          ceiling table is explicitly NOT this build's lever.

THE PAYLOAD -- CAN 0x14A byte4, bits 7:3
-----------------------------------------
    bit7 = (*(short *)(gp - 0x6BD0) != 0)      ★ THE POSITIVE CONTROL, **UNCHANGED FROM V74**.
                                                 Same cell, same test -- the cross-build anchor.
    bit6 = (|*(short *)(gp - 0x6BD0)| >= 128)
    bit5 = (|*(short *)(gp - 0x6BD0)| >= 288)
    bit4 = (|*(short *)(gp - 0x6BD0)| >= 448)  the near-ceiling indicator; the ceiling FLOOR is 512
    bit3 = (*(ushort *)(gp - 0x6AC2) != 0)     ★★ THE BACK-DRIVE GATE. Never measured in this kit.
    bits 2:0 = live STEER_SENSOR_STATUS, preserved.

★★★★ BUILD IDENTITY IS **STRUCTURAL** FOR THE FIRST TIME IN THIS KIT.
The four damper bits are a THERMOMETER by construction -- bit4 => bit5 => bit6 => bit7 -- so only
**10 of the 32** payloads in bits 7:3 can ever occur. V74's own on-car payload was `0x28`/`0xA8`
(its constant state 5) and V73's was `0xC0`/`0xD0`; **`0x28`, `0xA8` and `0xD0` are all ILLEGAL
here.** Every previous probe in this kit shared V7x's cell and bit positions, so another build's log
decoded silently and produced a confident wrong answer -- that is exactly how V74's decoder once
certified V73's flight as "LEVER E' IS DELIVERING". `identify()` below rejects on the payload
ALPHABET, not on a behavioural threshold.
🛑 It still cannot CONFIRM: a build whose payloads happened to be all-legal would pass. **The .rwd
FILENAME remains the pre-drive discriminator and CAVE_HEX the post-hoc one.**

WHAT THE BACK-DRIVE BIT DOES AND DOES NOT SAY -- [EVIDENCE], from the decompiles
---------------------------------------------------------------------------------
`gp-0x6AC2` is the ceiling table's OWN LERP index: FUN_00034350 computes
`if (gp-0x6ac2 < 0x32c9) { ceiling = LERP(gp-0x6ac2, 0xC77A0[mode]) } else { ceiling = tp+0x7158 }`
and that ceiling is the +/- clamp applied to `gp-0x6bd0`. Its producer FUN_00041464 sets
`gp-0x6ac2 = |rate| >> 10` when `sign(rate) != sign(gp-0x6b98)`, and **0 otherwise** -- the
back-drive condition.
⚠ TWO HONEST CAVEATS, both of which bound what bit3 licenses:
  1. The ceiling record is `X = [300, 800], Y = [512, 1024]`, so the ceiling only RISES above 512
     once the index exceeds **300**. `bit3 = 1` means the index is merely NON-ZERO ⇒ NECESSARY but
     NOT SUFFICIENT for a lifted ceiling. A 300-count threshold did not fit in the 68-byte extent.
  2. The cell is forced to the sentinel **0xFFFF** when `|gp-0x6b98| >= 0x2000`, which also reads as
     `bit3 = 1` -- and 0xFFFF > 0x32c9, so that path takes the `tp+0x7158` fallback ceiling instead.
  ⇒ Read bit3 as **"the back-drive/sentinel path is live at all"**, which is the open question. A
  duty of ~0 is the DECISIVE result: it would mean the ceiling is pinned at 512 and the whole
  ceiling-table lever class is dead.

HOW TO READ THE ANSWER
-----------------------
  any ILLEGAL payload                     ⇒ REFUSED. This is not a V75 log. Check the .rwd filename.
  bit7 duty ~ 0                           ⇒ the damper is dead again despite 2.74x. That would be a
                                            NEW fact -- V74 measured bit7 firing.
  bit7 fires, bit6 rarely                 ⇒ delivering, but |gp-0x6bd0| stays under 128: the dose is
                                            reaching the plant far smaller than the table predicts.
  bit6/bit5 duty rises vs V74's bit7 duty ⇒ the crank landed. This is the intended reading.
  bit4 fires at all                       ⇒ 🛑 |gp-0x6bd0| >= 448 against a 512 ceiling: report it.
                                            The next build must NOT crank further.
  bit3 duty ~ 0                           ⇒ the back-drive gate never opens; the ceiling is pinned
                                            at 512 and 0xC77A0 is not a usable lever.

Usage:  python probe/decode_v75_probe.py <rlog-or-segment-dir> [...]
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
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
import os
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decode_v67_gate import collect                                        # noqa: E402
from decode_v69_ratchet import MIN_SAMPLES                                 # noqa: E402

# 🛑 THE MECHANICAL LINK TO THE IMAGE. build_v75_tva.assert_decoder_matches() FAILS THE BUILD if this
# hex does not equal the cave it just emitted, so this decoder cannot silently describe a different
# build. Do not hand-edit it.
CAVE_HEX = "003a24373094e031c205ae058031483a85326432a605443a6932a605423a6e32a605413ac43ae4373f95e031a205483a8437edeac636070007314437ecea2436e8ea7f00"  # noqa: E501
#
#   0xC4B34  003a      mov   0x0,r7           r7 = 0                     (real instance @0x34114)
#   0xC4B36  24373094  ld.h  -0x6bd0[gp],r6   ★ THE DAMPER'S OWN OUTPUT. **SIGNED** -- op field
#                                             0x39. Its one-bit twin `st.h` (0x3B) is a REAL
#                                             instruction at 0x34730 writing this very cell.
#   0xC4B3A  e031      cmp   r0,r6            🛑 ONE cmp feeds TWO branches. Legal only because a
#                                             Bcond does not touch the PSW.
#   0xC4B3C  c205      be    +8               zero -> skip the abs AND the bit7 setter, landing on
#                                             the `shr` with r6 = 0 and r7 = 0. (real `be` @0xC02)
#   0xC4B3E  ae05      bge   +4               x > 0 -> skip the negate    (real @0x244CE)
#   0xC4B40  8031      subr  r0,r6            r6 = -r6.  🛑 op 0x0C, NOT 0x0D `sub`, whose operands
#                                             are the other way round -- `sub r0,r6` is r6 - 0 = r6
#                                             and the negate would VANISH. (real @0x2A150)
#   0xC4B42  483a      add   0x8,r7           bit7 = (gp-0x6bd0 != 0)     THE POSITIVE CONTROL
#   0xC4B44  8532      shr   0x5,r6           q = |x| >> 5. ★ This is WHY the build fits: 128, 288
#                                             and 448 are 4, 9 and 14 times 32, so all three
#                                             thresholds become `cmp imm5`. (real @0x18264)
#   0xC4B46  6432      cmp   0x4,r6           q >= 4  <=> |x| >= 128
#   0xC4B48  a605      blt   +4               (real `blt` @0x290A8)
#   0xC4B4A  443a      add   0x4,r7           bit6
#   0xC4B4C  6932      cmp   0x9,r6           q >= 9  <=> |x| >= 288
#   0xC4B4E  a605      blt   +4
#   0xC4B50  423a      add   0x2,r7           bit5
#   0xC4B52  6e32      cmp   0xe,r6           q >= 14 <=> |x| >= 448
#   0xC4B54  a605      blt   +4
#   0xC4B56  413a      add   0x1,r7           bit4
#   0xC4B58  c43a      shl   0x4,r7           the 4-bit thermometer -> bits 7:4. 🛑 `shl 0x4`, not
#                                             V74's `shl 0x3`: bit7's natural pre-shift weight of 16
#                                             is OUTSIDE `add imm5`'s -16..15 range, so the shift is
#                                             split and bit3 is added AFTERWARDS. (real @0x1C1C2)
#   0xC4B5A  e4373f95  ld.hu -0x6ac2[gp],r6   ★★ THE BACK-DRIVE GATE / ceiling LERP index.
#                                             🛑 hw2 = 0x953F -- LSB **SET**. Opcode 0x3F with an
#                                             EVEN hw2 is `ld.w`, a MISALIGNED 32-bit read spanning
#                                             gp-0x6ac2 AND gp-0x6ac0. Matches the firmware's own 8
#                                             readers, all `ld.hu`. (hw2 donor @0x346A4)
#   0xC4B5E  e031      cmp   r0,r6
#   0xC4B60  a205      be    +4
#   0xC4B62  483a      add   0x8,r7           bit3 -- SAME BYTES as the bit7 setter; only its
#                                             position AFTER the `shl` distinguishes them.
#   0xC4B64  8437edea  ld.bu -0x1514[gp],r6   CAN-330 payload byte4 (r6 is free: the field is in r7)
#   0xC4B68  c6360700  andi  0x7,r6,r6        preserve live STEER_SENSOR_STATUS bits 2:0
#   0xC4B6C  0731      or    r7,r6            THE MERGE. 🛑 **NOT** `or r6,r7` (0639) -- same
#                                             opcode, register fields SWAPPED, and both are real
#                                             instructions in this image.
#   0xC4B6E  4437ecea  st.b  r6,-0x1514[gp]   THE ONLY STORE. GATE 1 is vacuous.
#   0xC4B72  2436e8ea  movea -0x1518,gp,r6    the displaced hook instruction, re-executed LAST
#   0xC4B76  7f00      jmp   [lp]             -> 0x55C12, which is `mov 0x8,r7` (083a) ⇒ r7 is
#                                             PROVABLY DEAD across the hook
#   ⊕ 68 of 68 bytes. **There is NO padding in this cave** -- unlike every V7x before it.

BIT_DAMP_NZ = 0x80            # bit7   the damper is non-zero   ★ THE POSITIVE CONTROL
BIT_MAG128 = 0x40             # bit6   |damper| >= 128
BIT_MAG288 = 0x20             # bit5   |damper| >= 288
BIT_MAG448 = 0x10             # bit4   |damper| >= 448   -- near the 512 ceiling floor
BIT_BACKDRIVE = 0x08          # bit3   the ceiling LERP index is non-zero
PROBE_MASK = 0xF8
STATUS_MASK = 0x07            # STEER_SENSOR_STATUS, preserved

MAG_THRESHOLDS = (128, 288, 448)
MAG_BITS = (BIT_MAG128, BIT_MAG288, BIT_MAG448)
# ★ The complete reachable alphabet of bits 7:3. Ten values, because the four damper bits are a
# THERMOMETER and bit3 is independent. builds/v50_v79/build_v75_tva.py asserts this tuple against its own model.
LEGAL_PAYLOADS = (0x00, 0x08, 0x80, 0x88, 0xC0, 0xC8, 0xE0, 0xE8, 0xF0, 0xF8)
# 🛑 The payloads that PROVE a foreign log. V74 measured a constant state 5; V73's field was
# `mode & 0xF` and this car's engaged mode 26 gives 10.
FOREIGN_PAYLOADS = {0x28: "V74 (state 5, damper zero)", 0xA8: "V74 (state 5, damper non-zero)",
                    0xD0: "V73 (mode 26 -> field 10)", 0x50: "V73 (mode 26, seed clear)",
                    0x40: "V73 (mode 24 -> field 8, seed clear)"}

DAMP_DISP = 0x6BD0            # the base-assist damper output -- SIGNED, ld.h
BACKDRIVE_DISP = 0x6AC2       # the ceiling LERP index -- UNSIGNED, ld.hu
# 🛑 BOTH probed cells are LOCKSTEP-SHADOWED: gp-0x6bd0 at gp-0x4cf2, gp-0x6ac2 at gp-0x4cc6. Every
# writer compares the pair and escalates to FUN_0006b9fa on disagreement. The probe only READS, so
# the blast radius is zero -- and the builder asserts the cave touches neither shadow.
CEILING_TABLE = 0xC77A0       # X = [300, 800], Y = [512, 1024], indexed by the back-drive cell
CEILING_FLOOR = 512
CEILING_LIFT_INDEX = 300      # ⚠ bit3 fires from 1; the ceiling only LIFTS above this
BACKDRIVE_SENTINEL = 0xFFFF   # ⚠ also reads as bit3 = 1 -- see below, it does NOT lift the ceiling
CEILING_FALLBACK = 512        # tp+0x7158 = 0xC6158, the ceiling taken when the index >= 0x32C9
# ★★ [EVIDENCE] THE CEILING IS 512 ON BOTH BRANCHES, so bit3 = 1 can never mean "the clamp got
# looser by the sentinel route". The ceiling's own reader is `ld.hu -0x6ac2,gp,r12` @0x346A4
# (UNSIGNED, pinned in Ghidra), then `addi -0x32c9,r12,r0` / `bnc` -- an unsigned compare. So the
# 0xFFFF sentinel is 65535 >= 0x32C9 and SKIPS the LERP entirely, taking `ld.hu 0x7158,tp,r6`
# @0x346AE -- and that cell holds 512, byte-identical to the LERP's own Y[0].

ENGAGED_MODES = (2, 3, 5, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33)
DISENGAGED_MODES = (0, 1, 4, 10, 12, 13, 16, 22, 24, 25, 28, 30, 31)
LIVE_MODE = 26                # row 11 TVCA4, e014 -- V73's on-car probe, not an inference
MANUAL_MODE = 24
HELD_AT_BASE = (2, 3)         # ⚠ C_Y[0] left at V74's 1356: writing 566 would have SUBTRACTED

BURST_RATE = 99               # measured |gp-0x6ac0| p50 IN-BURST, [94.2, 113.0]
BURST_RATE_69HZ = 127         # the 6-9 Hz arm's p50 (⚠ 3 episodes, unpowered)
LIVE_DOSE_V74, LIVE_DOSE = 50, 137          # counts at BURST_RATE on mode 26 -- 2.74x
LIVE_DOSE_69HZ = 181
OBSERVED_PEAK_V74 = 225       # |gp-0x6bd0| peak actually driven on V74
PREDICTED_PEAK = 354          # 69% of the 512 floor -- the basis for the bit4 threshold
CREEP_MAX_MS = 4.0            # the ratchet and grind #1 are creep symptoms (1-4 m/s)
NEARZERO_RATE_DEGS = 0.5      # |column rate| below this is "the wheel is not moving"
# ⚠ DO NOT "FIX" THE UNITS HERE. This is openpilot's COLUMN rate off CAN 0x18F, in real deg/s, used
# only as a build-identity test. It is NOT `gp-0x6ac0` and there is NO conversion applied to it. The
# firmware's rate axis is 4.7121 counts per column deg/s, but that constant belongs to anything that
# converts BETWEEN the two -- nothing in this file or in builds/v50_v79/build_v75_tva.py does, because the dose
# model works in raw counts natively.
RATE_COUNTS_PER_COLUMN_DEGS = 4.7121   # recorded for the next reader; deliberately UNUSED here

# 🛑 ONE LINE, deliberately. builds/v50_v79/build_v75_tva.py asserts this exact basename appears in this file;
# splitting it across a concatenation makes the substring vanish and the check silently harder.
RWD_NAME = "39990-TVA,A160-V75-V74BASE-ENGCOLS13-levers-CY0.566-magprobe-6bd0-thermo-6ac2-0x13000-0x100000.rwd"  # noqa: E501
# 🛑🛑 THE LEVER SET IS IN THAT FILENAME FOR A REASON. V75's two edits (`CY0` = FactorC Y[0] := 566,
# `EX1` = FactorE X[1] := 200) are independently toggleable, and **the cave is BYTE-IDENTICAL across
# every lever set** -- so this decoder reads a CY0-only, an EX1-only and a both cut exactly alike.
# The payload CANNOT tell them apart. If a re-cut is flown, `builds/v50_v79/build_v75_tva.py` will refuse to build
# until this constant names that cut's own .rwd. Do not "fix" a mismatch by editing it to match a
# file you did not flash.
#
# ⊕ RETARGETED 2026-08-06 — from the BOTH-levers cut to the CY0-ONLY cut. **THE BOTH-LEVERS CUT FLEW
# AND HARD-FAULTED THE ECU**: after a stoplight stop, pulling away with openpilot engaged, the EPS
# lamp lit and ALL power steering was lost, latched. 🛑 The superseded cut's full basename is
# DELIBERATELY NOT WRITTEN ANYWHERE IN THIS FILE — `builds/v50_v79/build_v75_tva.py`'s guard is a plain substring
# test, so naming both cuts here would make it vacuous for BOTH. Refer to it in prose only (the
# `…-CY0.566` + `EX1.200` cut) and never paste its filename back in.
# Why the re-cut: the ramp-regime incremental gain k = (C_Y0*Y[1]>>10)/(X[1]-X[0]) is a
# FREQUENCY-INDEPENDENT scalar on the whole damper path — stock 0.0000 · V74 0.5799 (1,011 s clean) ·
# BOTH-cut 1.5798 (+8.70 dB over V74, faulted) · this CY0-only cut 0.7655 (+2.41 dB). Dropping EX1
# keeps the plateau (M = 297) and so ~99% of the grind-band and ~88% of the ratchet damping, while
# spending only 2.41 of the ≤8.70 dB of margin V74 empirically demonstrated. It is ALSO
# single-variable against BOTH flown builds (V74 + CY0 ; the faulted cut − EX1).
# ⚠ Consequence, accept it knowingly: this decoder will now WARN on a log from the faulted cut. That
# is correct — there are no rlogs from that drive, and a decoder that silently accepts both is worse.


def level(b4):
    """0..4: how far up the thermometer each frame sat. 0 = damper exactly zero."""
    return (((b4 & BIT_DAMP_NZ) != 0).astype(np.int8) + ((b4 & BIT_MAG128) != 0)
            + ((b4 & BIT_MAG288) != 0) + ((b4 & BIT_MAG448) != 0))


LEVEL_BANDS = ("|damper| == 0", "1 <= |damper| < 128", "128 <= |damper| < 288",
               "288 <= |damper| < 448", "|damper| >= 448  🛑 near the 512 ceiling")


def identify(b4, engaged=None, speed_ms=None, rate_degs=None, override=False):
    """Is this a V75 payload? 🛑 THE GUARD CAN REJECT STRUCTURALLY, BUT STILL CANNOT CONFIRM.

    T1 [DECISIVE, STRUCTURAL] **THE PAYLOAD ALPHABET.** The four damper bits are a thermometer, so
       only the 10 values in LEGAL_PAYLOADS are reachable. Any other value in bits 7:3 proves the
       bytes were not produced by this cave. This is new: every earlier probe in this kit could be
       rejected only behaviourally, and V74's decoder once certified V73's flight because the two
       alphabets overlapped completely.
    T2 [DECISIVE] **MANUAL CREEP.** V75 doses only the ENGAGED column; mode 24 (manual) is
       byte-stock, so FactorC Y[0] = 0 => dose 0 => bit7 = 0. ⚠ SCOPED: manual ABOVE ~35 km/h
       legitimately gives bit7 = 1, so the cell is manual **AND** creep.
    T3 [DECISIVE] **NEAR-ZERO STEERING RATE, any mode.** FactorE's Y[0] is preserved at 0, so at
       zero rate the product is 0 and bit7 must be 0 -- engaged or not, fast or slow.

    🛑 AN UNPOWERED CHECK IS REPORTED AS **UNPOWERED**, NEVER AS A PASS. That distinction is the
    whole lesson of V64/V68's five uninterpretable nulls.
    """
    decisive, corroborating, unpowered = [], [], []
    field = b4 & PROBE_MASK
    nz = (b4 & BIT_DAMP_NZ) != 0
    seen = Counter(int(f) for f in field)
    eng = np.asarray(engaged, bool) if engaged is not None and len(engaged) == len(b4) else None
    v = np.asarray(speed_ms, float) if speed_ms is not None and len(speed_ms) == len(b4) else None
    r = np.asarray(rate_degs, float) if rate_degs is not None and len(rate_degs) == len(b4) else None

    # ---- T1: the payload alphabet -- STRUCTURAL, and it needs no covariate --------------------
    illegal = {p: n for p, n in seen.items() if p not in LEGAL_PAYLOADS}
    if illegal:
        who = {p: FOREIGN_PAYLOADS.get(p, "unknown schema") for p in illegal}
        decisive.append(
            f"T1 PAYLOAD ALPHABET: {sum(illegal.values())} frame(s) carry bits 7:3 outside the 10 "
            f"reachable thermometer values -- {[(hex(p), n) for p, n in illegal.items()]}. "
            f"Attribution: { {hex(p): w for p, w in who.items()} }. The thermometer invariant "
            "bit4 => bit5 => bit6 => bit7 is STRUCTURAL, so these bytes did not come from V75's cave.")
    else:
        corroborating.append(f"T1 passes: all {len(b4)} frames carry a LEGAL thermometer payload "
                             f"({sorted(hex(p) for p in seen)})")

    # ---- T2: manual creep ------------------------------------------------------------------------
    if eng is None or v is None:
        unpowered.append("T2 (manual creep): no latActive/vEgo in this log")
    else:
        m = (~eng) & np.isfinite(v) & (v <= CREEP_MAX_MS)
        n = int(m.sum())
        if n < MIN_SAMPLES:
            unpowered.append(f"T2 (manual creep): only {n} frames (< {MIN_SAMPLES}) -- UNPOWERED, "
                             "NOT a pass")
        elif nz[m].all():
            decisive.append(f"T2 MANUAL CREEP: bit7 is set on ALL {n} manual-creep frames. Mode "
                            f"{MANUAL_MODE} is byte-stock on V75, so FactorC Y[0] = 0 => dose 0 => "
                            "bit7 MUST be 0 there.")
        else:
            corroborating.append(f"T2 passes: bit7 is clear on "
                                 f"{100 * (1 - nz[m].mean()):.1f}% of {n} manual-creep frames")

    # ---- T3: near-zero steering rate -------------------------------------------------------------
    if r is None:
        unpowered.append("T3 (near-zero rate): no 0x18F rate in this log")
    else:
        m = np.isfinite(r) & (np.abs(r) < NEARZERO_RATE_DEGS)
        n = int(m.sum())
        if n < MIN_SAMPLES:
            unpowered.append(f"T3 (near-zero rate): only {n} frames (< {MIN_SAMPLES}) -- "
                             "UNPOWERED, NOT a pass")
        elif nz[m].all():
            decisive.append(f"T3 NEAR-ZERO RATE: bit7 is set on ALL {n} frames with |column rate| "
                            f"< {NEARZERO_RATE_DEGS} deg/s. FactorE's Y[0] is preserved at 0 by "
                            "design, so the product is 0 and bit7 MUST be 0 there.")
        else:
            corroborating.append(f"T3 passes: bit7 is clear on "
                                 f"{100 * (1 - nz[m].mean()):.1f}% of {n} near-zero-rate frames")

    # ---- verdict ---------------------------------------------------------------------------------
    if unpowered:
        print("  ⚠ UNPOWERED CHECKS (these are NOT passes):")
        for u in unpowered:
            print(f"     · {u}")
    if decisive:
        print("\n  " + "=" * 92)
        print("  🛑🛑 REFUSING TO DECODE -- THESE BYTES ARE NOT A V75 PAYLOAD.")
        print("  " + "=" * 92)
        for w in decisive:
            print(f"     · [DECISIVE] {w}")
        for w in corroborating:
            print(f"     · [corroborating] {w}")
        print("     ⇒ Every V7x cave writes the SAME cell (gp-0x1514, CAN 0x14A byte4) in the SAME")
        print("       bit positions, so another build's log decodes here silently and produces a")
        print("       CONFIDENT WRONG answer. That has already happened once in this kit.")
        print(f"     🛑 Confirm the flashed .rwd is {RWD_NAME}")
        print("     Re-run with --i-confirm-v75 to override AFTER checking the filename.")
        if not override:
            return False
        print("  ⚠ --i-confirm-v75 given: proceeding under protest. Every number below is suspect.")
    elif corroborating:
        print("  ⊕ build-identity checks that ran clean:")
        for w in corroborating:
            print(f"     · {w}")
    if set(seen) == {0x00}:
        print("  🛑🛑 VOID-SHAPED: bits 7:3 are IDENTICALLY 0 across the whole drive.")
        print("     ⚠ 0x00 is a LEGAL V75 payload (damper zero AND back-drive zero), so unlike V74")
        print("       this does NOT prove the cave never fired -- the two hypotheses are not")
        print("       separable from the payload alone. Check the .rwd filename, then read it as")
        print("       'the damper never left zero and the back-drive gate never opened'.")
    print(f"  ✅ not excluded as V75: {len(seen)} distinct payload(s) "
          f"{sorted(hex(p) for p in seen)}, bit7 duty {100.0 * np.mean(nz):.3f}%")
    print("     🛑 'not excluded' is NOT 'confirmed' -- a build whose payloads happened to be all")
    print("        legal would pass, and the FILENAME remains the pre-drive discriminator.")
    return True


def report(b4, engaged, speed_ms):
    """The thermometer, the back-drive gate, and the slices that carry the symptom."""
    lv = level(b4)
    nz = (b4 & BIT_DAMP_NZ) != 0
    bd = (b4 & BIT_BACKDRIVE) != 0

    # 🛑 the invariant, re-checked on the DATA rather than trusted from the design
    bad = int(np.sum(((b4 & BIT_MAG128) != 0) & ~nz)
              + np.sum(((b4 & BIT_MAG288) != 0) & ((b4 & BIT_MAG128) == 0))
              + np.sum(((b4 & BIT_MAG448) != 0) & ((b4 & BIT_MAG288) == 0)))
    print(f"\n  ★ THERMOMETER INVARIANT (bit4 => bit5 => bit6 => bit7): "
          f"{'HOLDS on all frames' if bad == 0 else f'🛑 VIOLATED on {bad} frames'}")

    print("\n  ★★ THE DAMPER MAGNITUDE |gp-0x6BD0| -- what V74 could not measure:")
    for i, band in enumerate(LEVEL_BANDS):
        n = int((lv == i).sum())
        print(f"     level {i}  {band:<44s} {n:8d} frames  {100.0 * n / len(b4):6.2f}%")
    hi = int((lv >= 4).sum())
    if hi:
        print(f"     🛑 bit4 FIRED on {hi} frames ({100.0 * hi / len(b4):.3f}%): |gp-0x6BD0| reached "
              f">= {MAG_THRESHOLDS[2]} against a ceiling FLOOR of {CEILING_FLOOR}.")
        print("        The margin to saturation is thin. DO NOT crank the dose further without")
        print("        re-deriving the no-clip caps against the MEASURED distribution.")
    else:
        print(f"     ✅ bit4 never fired ⇒ |gp-0x6BD0| stayed below {MAG_THRESHOLDS[2]}, i.e. below "
              f"{100 * MAG_THRESHOLDS[2] // CEILING_FLOOR}% of the {CEILING_FLOOR} ceiling floor.")

    print(f"\n  ★★ bit3 -- THE BACK-DRIVE GATE (gp-0x6AC2 != 0), the first measurement in this kit:")
    print(f"     duty {100.0 * bd.mean():.3f}% of {len(b4)} frames")
    if bd.mean() < 0.001:
        print(f"     ⇒ the ceiling LERP index is essentially always 0, so the ceiling is PINNED at")
        print(f"       {CEILING_FLOOR} and the ceiling table 0x{CEILING_TABLE:05X} is NOT a usable")
        print("       lever. That retires a whole class of candidates.")
    else:
        print(f"     ⚠ NECESSARY BUT NOT SUFFICIENT for a lifted ceiling: the record is "
              f"X = [{CEILING_LIFT_INDEX}, 800], Y = [{CEILING_FLOOR}, 1024], so the ceiling only")
        print(f"       rises once the index exceeds {CEILING_LIFT_INDEX}, and the cell is forced to "
              f"the sentinel 0x{BACKDRIVE_SENTINEL:04X} when")
        print("       |gp-0x6b98| >= 0x2000 -- which reads as bit3 = 1 and takes the tp+0x7158")
        print("       fallback ceiling instead. Read this duty as 'the path is live at all'.")

    print("\n  ★ bit7 -- THE POSITIVE CONTROL (unchanged from V74, so the two builds compare):")
    slices = [("all frames", np.ones(len(b4), dtype=bool))]
    if engaged is not None and len(engaged) == len(b4):
        slices += [("ENGAGED", engaged), ("manual", ~engaged)]
        if speed_ms is not None and len(speed_ms) == len(b4):
            v = np.asarray(speed_ms, dtype=float)
            slices += [("ENGAGED creep (<= 4 m/s)", engaged & (v <= CREEP_MAX_MS)),
                       ("ENGAGED cruise (> 4 m/s)", engaged & (v > CREEP_MAX_MS))]
    print(f"     {'slice':26s} {'bit7':>8s} {'bit6':>8s} {'bit5':>8s} {'bit4':>8s} {'bit3':>8s} "
          f"{'mean lvl':>9s}  n")
    for lab, m in slices:
        n = int(m.sum())
        if n < MIN_SAMPLES:
            print(f"     {lab:26s}: only {n} frames (< {MIN_SAMPLES}) -- not reportable")
            continue
        cols = [100.0 * ((b4[m] & bit) != 0).mean()
                for bit in (BIT_DAMP_NZ, BIT_MAG128, BIT_MAG288, BIT_MAG448, BIT_BACKDRIVE)]
        print(f"     {lab:26s} " + " ".join(f"{c:7.3f}%" for c in cols)
              + f" {lv[m].mean():9.3f}  {n}")

    print("\n  THE VERDICT THIS DRIVE LICENSES:")
    if not nz.any():
        print("     🛑 bit7 is IDENTICALLY 0 ⇒ the damper output never left zero, DESPITE the")
        print(f"       {LIVE_DOSE_V74} -> {LIVE_DOSE} crank. V74 measured bit7 FIRING, so this would")
        print("       be a REGRESSION or a build-identity problem, not a repeat of any prior null.")
        print("       Check the .rwd filename FIRST.")
    elif not (b4 & BIT_MAG128).any():
        print(f"     ⚠ bit7 fires but bit6 NEVER does ⇒ |gp-0x6BD0| stayed under "
              f"{MAG_THRESHOLDS[0]} for the whole")
        print(f"       drive, while the table predicts {LIVE_DOSE} counts at the measured burst "
              f"rate {BURST_RATE}.")
        print("       ⇒ something downstream of FactorC/FactorE is holding the magnitude down.")
        print("       Do NOT score the crank as delivered.")
    else:
        print(f"     ✅ THE CRANK LANDED: bit6 fires on "
              f"{100.0 * ((b4 & BIT_MAG128) != 0).mean():.3f}% of frames ⇒ |gp-0x6BD0| exceeded "
              f"{MAG_THRESHOLDS[0]}")
        print(f"       counts, which V74's {LIVE_DOSE_V74}-count dose could not reach at the "
              f"measured burst rate. Score the")
        print("       6-9 Hz ratchet and grind #1 against the ENGAGED frames only.")
    print(f"     ⊕ LEVER D' (friction x1.5) and the X[0] = 12 gate are CARRIED from V74 unchanged, so")
    print("       they are live exactly when bit7's mode is. Do not re-credit them here.")
    print(f"     ⚠ Modes {list(HELD_AT_BASE)} were HELD at V74's C_Y[0] rather than written to 566 "
          "(that would have")
    print("       SUBTRACTED). They are TWAA-chassis modes and inert on this car either way.")
    return Counter(int(x) for x in lv)


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    override = "--i-confirm-v75" in argv[1:]
    if not args:
        print(__doc__)
        return 2
    refused = 0
    for target in args:
        print("=" * 100)
        print(f"  {target}")
        # 🛑 GLUE: `collect()` takes a LIST of paths and returns `b4` / `lat` / `v`. Passing the bare
        # string makes it iterate the path's CHARACTERS.
        data = collect([target])
        b4 = np.asarray(data["b4"], dtype=np.uint8)
        if not len(b4):
            print("  🛑 no 0x14A frames found.")
            refused += 1
            continue
        engaged = np.asarray(data["lat"], dtype=bool) if data.get("has_lat") else None
        speed_ms = data.get("v")
        print(f"  frames: {len(b4)}")
        print(f"  payload histogram: {dict(Counter(hex(int(x)) for x in b4).most_common(12))}")
        if not identify(b4, engaged, speed_ms, data.get("rate"), override=override):
            refused += 1
            continue
        report(b4, engaged, speed_ms)
        print(f"\n  🛑 REMINDER: the ENGAGED column {list(ENGAGED_MODES)} is dosed; the DISENGAGED")
        print(f"     column {list(DISENGAGED_MODES)} is byte-stock, so manual and parking steering")
        print(f"     are UNTOUCHED. This car's manual mode is {MANUAL_MODE}, engaged {LIVE_MODE}.")
        print("  🛑 V75 still carries V72's UNGATED r24/r26 rate lane -- that dose applies in MANUAL")
        print("     below ~30 km/h too, and it is NOT what this probe measures. Score it separately.")
    # 🛑 EXIT NON-ZERO ON ANY REFUSAL. A guard that returns success is only half a guard: the loud
    # banner is for a human, this is for anything that pipes, wraps or CI-checks the decoder.
    if refused:
        print(f"\n🛑 {refused} of {len(args)} target(s) REFUSED or empty -- exiting non-zero.")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
