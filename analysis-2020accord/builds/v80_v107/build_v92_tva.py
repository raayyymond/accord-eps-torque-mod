#!/usr/bin/env python3
r"""builds/v80_v107/build_v92_tva.py -- V92 = V91's 12 CALIBRATION BYTES + a re-specced 110-byte TELEMETRY CAVE.

    base   _v90_V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26_plain_image.bin
           sha256 28ac817bc3f76958ad5a33316e420c734949f24b206ddb6d083a5254b3aa70db

    0xD7A5C  mode 26 friction/damping-comp LERP Y row  (-9830,-5734,-1966) -> (-14745,-8601,-2949)
    0xD7A6C  mode 27 friction/damping-comp LERP Y row  (-9830,-5734,-1966) -> (-14745,-8601,-2949)
    0xC4B34  cave payload 74 B -> 116 B   SEVEN rungs on CAN 0x14A byte4[7:3] AND byte7[7:6]
    0x55DF2  da94 -> 4294                 CAN 427 MOTOR_TORQUE: gp-0x6b26 -> gp-0x6bbe
    0x55E10  a332 -> a432                 CAN 427 packer scale: sar 3 -> sar 4, so the new source
                                          CANNOT CLIP (see THE 427 SCALE FIX below)

Five edits: 12 calibration bytes (identical to V91), 116 cave bytes, 2 repoint bytes, 1 scale byte,
8 CRC bytes.

===================================================================================================
🛑🛑 HONEST LABELLING -- READ THIS BEFORE THE PHYSICS   (verbatim from builds/v80_v107/build_v91_tva.py)
===================================================================================================
> **V92 carries the SAME LEVER at the SAME x1.5 DOSE that flew on V74 and V75. Both of those flights
> HARD-FAULTED with a latched total loss of power steering. The single difference is `0xC407E`: every
> artefact that ever carried this dose also carried 850; V92 carries Honda's 511, one count below the
> DTC-0x1d monitor's 512 trip, so the monitor is structurally untrippable at any multiplier.
> ZERO flights have ever separated the dose from the 850 interlock -- the separation is STRUCTURAL,
> never empirical. V81 (route 67, fault-free) is a control for the INTERLOCK ONLY: it is byte-stock on
> the friction row in all 34 modes, so it says nothing about the dose.
> Writing only modes 26/27 is a DELIBERATE NARROWING from V74/V75's 14 records, not a reproduction.**

🛑 **AND THE DOSE IS 5-69x BELOW THE MEASURABLE FLOOR** (orchestrator's sizing, carried as given, not
re-derived here). ⇒ **The operator's own report is the PRIMARY ENDPOINT of this flight, and the
TELEMETRY IS THE POINT OF FLYING IT.** Do not expect the 12 calibration bytes to show up in any band
statistic. If they do, that is a surprise to be explained, not a result to be claimed.

===================================================================================================
WHAT CLASS OF BUILD THIS IS -- against the whole arc since V38
===================================================================================================
V38-V52 authority/filters/poles/caves - V53-V61 telemetry + lane mutes - V62-V73 the rate lane
(r24/r26) - V74-V83a the base-assist damper - V84-V86B damper reverts and phase - V87 subtractive
measurement - V88 Lever B restored - V89 the first build to touch the PLANT MODEL - V90 pure
instrument - V91 (BUILT, UNFLOWN, frozen on disk) the cal-only 0xCBE74 dose.

**V92 is a MEASUREMENT build with a sub-floor cal edit riding along.** It is NOT a dose build: the
lever it carries is V91's, unchanged, and it is known to be too small to measure. What is genuinely
new is the INSTRUMENT, and it is new in a way no build in the whole arc has been:

    * It is the FIRST build ever to write CAN 0x14A **byte 7**. Every cave from V53 to V90 wrote
      byte 4 bits 7:3 and nothing else. The telemetry field grows from 5 bits to 7.
    * It is the first cave to instrument the **aggregator's own unresolved lanes** -- gp-0x6bbe
      (boost) and gp-0x6b62 (return-centre) -- rather than the observer/friction family
      (gp-0x6bf6 / gp-0x6ae2 / gp-0x6c00) that V86B..V90 all sampled.
    * It is the first rung anywhere in the kit to test a **relay/detent hypothesis** (the dwell-snap
      state) rather than a linear sign correlation.

RE-RUN vs NEW, stated plainly:
    * The 12 calibration bytes are a RE-RUN of V74/V75's lever D', narrowed to modes 26/27 -- see
      the honest-labelling block. V91 is the same 12 bytes; V92 is V91 + instrument.
    * The 427 repoint is the same CLASS of edit as V87/V88/V90 (a 2-byte source halfword), pointed
      at a cell no build has ever telemetered.
    * The cave rungs are ALL new signals. b7/b6/b5/b4 carry gp-0x6bbe / gp-0x6b62 / gp-0x6bda --
      none of which any prior build has ever put on the wire.

FROZEN CELLS, by count: 0xC40D2 (K1) unmoved since V89 = 3 builds. 0xC6446 (Lever B) unmoved since
V88 = 4 builds. 0x3AA96 unmoved since V88 = 4. 0x454FE unmoved since V80. 0xC407E at Honda's 511
since V81. 0xC6CD0 = 3564 (the 4.000x forward gain) on EVERY build. V92 moves NONE of them.

===================================================================================================
THE PAYLOAD -- what each bit measures     (docs/specs/SPEC-2026-08-11-telemetry-budget.md, VARIANT B)
===================================================================================================
    CAN 0x14A, 100 Hz
      byte4 b7  gp-0x6bbe < 0        SIGN of the BOOST lane            ~0.5 by construction
      byte4 b6  gp-0x6b62 < 0        SIGN of the RETURN-CENTRE lane    unknown
      byte4 b5  gp-0x6b62 != 0       lane LIVE  (disambiguates the disable branches from "tiny")
      byte4 b4  gp-0x6bda IN (-397,384)   🛑 THE OUTER GATE -- disambiguates the snap bit.
                                          OPEN interval: Y1 == 0 AT both end knots too.
      byte4 b3  1                    FINGERPRINT => every byte4[7:3] value is ODD
      byte7 b7  |gp-0x6b26| >= 15    🛑 DOSE-IN-FORCE for the 0xCBE74 x1.5 edit  (T=15, route 77)
      byte7 b6  gp-0x6a82 > cal(0xC627E)=20   the DWELL-RELAY SNAP STATE
    CAN 427 (0x1AB) MOTOR_TORQUE, 50 Hz
      clamp(|gp-0x6bbe| * 5 >> 4, 0, 0x3FF)          <- >>4, NOT Honda's >>3. See THE 427 SCALE FIX.

WHY THESE: the aggregator (FUN_0003aa2c) sums 11 lanes. Nine are settled -- already-known
dissipative, already measured, or ruled out by magnitude. gp-0x6bbe is the flagged best structural
match for anti-damping (same-signed as the raw torque sensor => REINFORCING). gp-0x6b62 is the
return-centre lane's own output.

===================================================================================================
🛑 THE (b4, byte7 b6) 2x2 -- why b4 is the OUTER GATE and not the convention anchor
===================================================================================================
    gp-0x6b64 = -clamp( Y1(gp-0x6bda) * gp-0x6abc(RAW motor rate) * cal(0xC63BE)>>10 , +-0x2800 )
    Y1 = LERP(gp-0x6bda, X=[-397,-192,140,294,384], Y=[0,2560,2560,717,0])       -- always >= 0

The table is at 0xC695C and this script READS IT FROM THE IMAGE and derives the window from it; the
values above are what it finds (count=5, byte-identical to STOCK).

**Y1 = 0 identically whenever gp-0x6bda is outside the window** => gp-0x6b64 = 0 AT ANY RATE. So the
dwell window |gp-0x6b64| < cal(0xC618A)=1024 opens by TWO physically different routes, and the snap
bit ALONE cannot tell them apart. Pairing it with the window bit gives a self-validating 2x2:

    (b4 in-window, byte7-b6 snapped)
      (0,1)  outer gate SHUT, gp-0x6b64 == 0, counter pinned  -> a FLAT -1024 BIAS. Detent DEAD.
      (1,1)  gate OPEN and the counter armed                  -> THE MECHANISM, genuine detent.
      (1,0)  gate open, not yet armed                         -> normal
      (0,0)  ⚠ RARE, and only as a ~21 ms TRANSIENT right after the gate shuts (the counter needs
             21 ticks at 1 kHz to climb to its ceiling) -- roughly 2 frames at 100 Hz per event.
             A SUSTAINED (0,0) run indicts the rung map. See MAP VALIDATOR 3.

⚠ The suspicion that drove this: a kit memory puts gp-0x6bda's HANDS-OFF value at ~9262, 24x outside
  the window. That number is NOT re-verified here and is a HANDS-OFF figure, while the operator
  reports micro-ratcheting during ACTIVE wheel motion. Suggestive, not settled -- which is exactly
  why it is worth a bit.

🛑 INITIATION vs SUSTAIN -- carry this into the reading, not just the duty. FUN_00036388 arms while
|gp-0x6b64| < 1024 and snaps once the counter passes 20 (~20 ms at 1 kHz). For a sustained 7.79 Hz
oscillation (128 ms period) the rate-proportional signal is near zero only ~8 ms per zero crossing,
against a 20 ms arm time. **The detent may NOT arm during sustained ratcheting at all.** Read it as a
candidate for INITIATING stick-slip, not sustaining it: **a LOW duty is NOT automatically a null** --
the informative question is whether it fires at ratchet ONSET, not what fraction of engaged time it
holds. Both rails are interpretable, which is what justifies the bit.

⚠ CARRIED RESIDUAL -- THE CONVENTION ANCHOR IS DROPPED. b4 was going to be sign(gp-0x6abc), tying
  internal motor rate to the CAN wheel-rate field. It lost the slot to the window bit. Recoverability,
  stated precisely: gp-0x6abc is assigned DIRECTLY from gp-0x4f50 (no EMA) by FUN_00041464, whose
  other arm gp-0x6abe is the FILTERED version of the same source, and gp-0x6abe/gp-0x6ac0's scale AND
  sign were arbitrated on-car (4.7121 vs 10.0, 8 of 9 episodes, V74's bit7). So the DC/low-frequency
  convention transfers. **The 6-30 Hz PHASE relationship does NOT** -- the arbitrated sibling is the
  filtered arm and its lag in exactly those bands is the unknown. Since the anchor existed to de-risk
  future PHASE claims, the part that does not carry over is the part it was for. Recorded as
  "recoverable at DC, unrecovered in the bands where every phase claim lives".

🛑 ONE-TICK CAVEAT ON b6, stated because it is real: FUN_00036388 evaluates the snap on the
   PRE-update counter and stores the POST-update counter to gp-0x6a82. Our 100 Hz read of gp-0x6a82
   therefore equals the snap condition that the 1 kHz task will evaluate on its NEXT tick -- an
   offset of at most 1 ms. Immaterial at 100 Hz; recorded so nobody rediscovers it as a defect.

===================================================================================================
🛑 THE 427 SCALE FIX -- one byte at 0x55E10, and why it is not optional
===================================================================================================
The 0x1AB packer is Honda's: FUN_00055d80 computes `clamp(|src| * 5 >> 3, 0, 0x3FF)`
(0x55E06 `mul 0x5,r6,r0`, 0x55E10 `sar 0x3,r6`, 0x55E12 the clamp call). gp-0x6b26 was clamped to
+/-511 upstream, so **V90 measured 0 clipped frames out of 62,180** -- and that clean property is
why V90's 427 data was trustworthy.

**gp-0x6bbe's aggregator window is +/-2048.** At Honda's >>3 the field would SATURATE from
|gp-0x6bbe| >= 1639 (1638*5>>3 = 1023 exactly; 1639*5>>3 = 1024 -> clamped): the top ~20 % of the
lane's range would read as a single value. **gp-0x6bbe is the top structural anti-damping candidate
-- "proportional-dominated AND positive-feedback, same-signed as the raw torque sensor, reinforcing
not opposing" -- and a positive-feedback lane's signature lives in its TAIL.** There is no measured
distribution for this cell, so the tail cannot be argued unreachable.

    >>3 :  2048*5>>3 = 1280 > 1023   🛑 CLIPS
    >>4 :  2048*5>>4 =  640 <= 1023  ✅ never clips, ~9.3 effective bits

**Cost: exactly one bit of resolution. Benefit: the top 20 % of the range stops being invisible.**
Both directions are asserted as booleans below. This is the ONLY edit V92 makes to Honda's packer.

===================================================================================================
🛑 CAVE DISCIPLINE -- V24, V27 and V48B all BRICKED the ECU. Every cave byte is risk.
===================================================================================================
NO INSTRUCTION IN THIS PAYLOAD IS HAND-ENCODED. Every opcode halfword and every displacement
halfword is copied from a Ghidra-verified twin -- either from V90's own flown cave in this base
image, or from Honda code elsewhere in this image -- with its source address cited and asserted.
The specific traps this defeats:
    * `subr r0,r6` is `8031`. The hand-derived `3080` is `satsubr`, which SATURATES instead of
      negating and corrupts the dose bit on negative values only -- a defect that survives a flight.
    * `ld.h X[gp],r7` and `ld.w X[gp],r7` SHARE hw1 `243f`; only hw2 bit 0 separates them. The
      register arrangement was chosen to put every load in r6 (hw1 `2437`, already flying) precisely
      so that no halfword is twinned against an instruction of a different class.
    * `ld.bu -0x1511` has op field 0x3D, not 0x3C: the displacement's bit 0 lives in hw1 bit 5.
      Both the load AND the store are copied WHOLE (4 bytes each) from the 0x14A builder's own
      byte-7 accesses 14 and 30 bytes below the hook, so the encoding cannot be got wrong.
    * The window rung uses `bnh`, NOT `bc`. Honda's own compiled range-test idiom at 0x498E0-0x498E6
      is `addi -imm,r6,r0` + `bc`, but after that `addi` the two are the SAME PREDICATE here:
      CY = (r6 >=u span) is the carry-OUT of the add, and Z implies r6 == span which already sets
      CY. They agree on every input. `bnh` (`a305`) is already flying in V90's cave, so the whole
      cave uses only {bge, bnh} -- V92 introduces NO new branch condition anywhere.

🛑 THE TWO 16-BIT IMMEDIATES ARE **DERIVED**, NOT TWINNED, AND THAT IS DELIBERATE.
A full-image scan finds ZERO `addi` instructions carrying imm16 = 0x018D (397) or 0xFCF2 (-782), so
no honest twin exists for them. They are instead COMPUTED IN THIS SCRIPT from the LERP table read
out of the image -- `bias = -X[0]`, `span = X[4] - X[0] + 1` -- and asserted. The twin rule exists to
defeat ENCODING ambiguity (opcode field, displacement bit 0, satsubr-vs-subr); a plain imm16 alone
in hw2 has none -- it is `struct.pack('<h', value)` and nothing else. Deriving it from the firmware's
own breakpoints and corner-gridding the predicate is a STRONGER check than copying a byte pair.
Twin coverage is asserted as 112 of 116 bytes, with the 4 derived bytes named explicitly.

GATE 1 -- RAM OWNERSHIP. Verified in this session, not inherited:
    reads   gp-0x6bbe (writer FUN_00034a72 @0x3508C/0x350A0/0x350AE, lockstep shadow gp-0x4cf0)
            gp-0x6b62 (writer FUN_00036388 @0x36514, lockstep shadow gp-0x4cda)
            gp-0x6bda (sole writer FUN_00036022 @0x3608C; 7 reader functions incl. FUN_000360fe,
                       FUN_00036388 x2 and FUN_0003a382 -- the PID's own authority-ramp softstart
                       index, so this bit reports a signal the PID consumes too, not a
                       return-centre-exclusive one)
            gp-0x6a82 (writer FUN_00036388 @0x36472)
            gp-0x6b26 (writer FUN_00036c12)      tp+0x727e = cal 0xC627E
            -- ALL are `ld.h`/`ld.hu`. A load has no side effect. NO new RAM is claimed anywhere.
    writes  gp-0x1514 bits 7:3   -- the byte ~50 flown builds have written
            gp-0x1511 bits 7:6   -- NEW. Justified below.
    scratch r6 and r7 ONLY. Asserted mechanically: every register referenced by the decoded payload
            is in {r0, gp, tp, r6, r7, lp}, and every register WRITTEN is in {r6, r7}.
            r6 is dead at the hook (the hooked `movea` overwrites it and the cave restores it).
            r7 is dead at the hook (0x55C12 `mov 0x8,r7` overwrites it two bytes after the return).
            r8/r10 are LIVE across the hook (0x55C20 `andi 0xf,r10,r8`) and the cave never touches
            them. lp is dead (0x55C18 `jarl 0x57b24,lp` clobbers it regardless).

🛑 byte7[7:6] -- WHY WRITING A VIRGIN BYTE IS SAFE. Verified two ways this session:
    (a) Decompiled FUN_00055a98: the ONLY two writers of gp-0x1511 are
            0x55BFC `andi 0xcf,r8,r8` -> 0x55C02 st.b   the redundancy-voted counter, bits 5:4
            0x55C24 `andi 0xf0,r6,r6` -> 0x55C2A st.b   the checksum nibble,           bits 3:0
        Both masks explicitly PRESERVE bits 7:6.
    (b) Independent Python byte scan of the whole image for any `st.b/st.h rX,-0x1511[gp]`:
        exactly TWO hits, 0x55C02 and 0x55C2A -- the same two. No cave, on any build, has ever
        written this byte. That is also this build's IDENTITY (below).
    CHECKSUM: FUN_00057b24(gp-0x1518, 8, 0x14a) is called at 0x55C18, AFTER the hook at 0x55C0E, so
    the checksum covers our two new bits automatically -- the same mechanism 10+ flights have used
    for byte 4. The nibble write at 0x55C2A that follows it preserves bits 7:4.

GATE 2 -- closed-loop stability: vacuous for the cave (a straight-line leaf: no loop, no call, no
divide, no float, 43 instructions at 100 Hz inside Honda's own di/ei critical section, the V90
hook site unchanged). For the CAL edit it is V91's argument, re-run here in full: a uniform x1.5 on
all three Y knots is a REAL SCALAR MULTIPLY -- zero phase at any frequency, no sign change, no
breakpoint moved -- and H(0) = 0 is proven three ways, so the lane contributes nothing at any
sustained steering rate at any multiplier.

===================================================================================================
IDENTITY -- single-frame, parameter-free, disjoint from every predecessor by CONSTRUCTION
===================================================================================================
**ANY single frame with `0x14A` byte7 bits[7:6] != 0 proves V92 is on the car.** No build V53..V91
can produce it: the only two writers of that byte mask those bits off, verified two ways above.
This does not depend on trusting any prior build's measured duty.
MAP VALIDATOR 1, unchanged: byte4 b3 == 1 => every observed byte4[7:3] value is ODD.
🛑 MAP VALIDATOR 2, NEW AND FREE: b6 and b5 read the SAME cell (gp-0x6b62), so b6 => b5 --
    "negative" implies "non-zero". **(b6,b5) = (1,0) is STRUCTURALLY UNREACHABLE**, and exactly 12
    of the 16 odd byte4 codewords are reachable, not 16 (V90 reached all 16). Any frame showing
    b6 = 1 with b5 = 0 proves the field is being read at the wrong bit offset. The scorer must
    PRE-REGISTER this. (b6,b5) is a deliberate THREE-state field: (0,0) zero, (0,1) positive,
    (1,1) negative.
⚠ MAP VALIDATOR 3, STATED CAREFULLY -- it is a RARITY check, NOT an impossibility. (b4, byte7 b6)
    = (0,0) means the outer gate is SHUT but the counter is not yet pinned. A shut gate forces
    gp-0x6b64 = 0, which satisfies the arm condition every tick, so the counter climbs 0 -> 21 and
    b6 goes 1. But that takes 21 ticks at 1 kHz = 21 ms, so (0,0) IS reachable as a TRANSIENT for
    ~21 ms after the gate shuts -- about 2 frames at 100 Hz per gate-shut event.
    🛑 So the correct pre-registration is "(0,0) is RARE and always adjacent to a b4 falling edge",
    NOT "(0,0) never occurs". A SUSTAINED (0,0) run is what would indict the rung map. Recorded
    because the sharper claim was made during design and would have mis-fired on real data.
SECONDARY: b4 is now the gp-0x6bda window bit, an unpredictable but genuinely two-sided duty;
    V90's b4 (gp-0x6c00 < 0) measured 0/62,180, so it could never be 1.

===================================================================================================
🛑 CRC -- TWO trailers, DERIVED IN CODE from the image's own 50-block map, never hard-coded
===================================================================================================
The blocks are NOT uniform 0x1000 below 0xC4000: block 50 is the single MAIN block spanning
[0x013000, 0x0C4FFC), which owns BOTH the cave (0xC4B34) and the 427 repoint (0x55DF2) -> 0xC4FFC.
The two cal writes lie in [0xD7000,0xD7FFC) -> 0xD7FFC. Expected {0xC4FFC, 0xD7FFC}, but DERIVED via
V53.owning_block and then ASSERTED. 0x055FFC is LIVE CODE (`6477b8f0`), not a trailer.
🛑 walk_all_blocks() == 0 is NECESSARY, NOT SUFFICIENT -- the recompute can hide corruption. The
zero-unattributed full byte diff is the independent check and both must pass.

===================================================================================================
THE TRAPS THIS SCRIPT IS BUILT AGAINST (V91's, carried verbatim)
===================================================================================================
* AN ADDRESS IS NOT A MODE. Every record address is DEREFERENCED from 0xCBE74 + mode*4.
* Y IS AT RECORD BASE + 8. Writing at base+2 lands in the X breakpoints, which the LERP compares
  UNSIGNED -- a silent flat Y[0] at all speeds that LOOKS like a working calibration.
* MODE 25's RECORD (0xD7A44) SITS EXACTLY 0x10 BELOW MODE 26's (0xD7A54). Modes 24 AND 25 asserted
  byte-identical, so a -0x10 slip onto a DISENGAGED column cannot pass.
* THE POINTER ARRAY HAS EXACTLY 34 SLOTS, modes 0..33 -- a GIVEN BOUND, never a walk. 0xCBEFC is
  the first slot PAST it and holds a perfectly valid-looking pointer into the gain_B tables.
* A CHECK THAT PRODUCES NO OUTPUT IS NOT A CHECK THAT PASSED. Every assertion emits a boolean.
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
import build_v53_tva as V53                # noqa: E402  -- owning_block, the REAL block map
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table   # noqa: E402
from firmware_paths import plain_image_path, ANALYSIS_ROOT, RWD_DIR              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V92_WRITE", "").strip().lower()

BASE_BIN = str(plain_image_path(
    "_v90_V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26_plain_image.bin"))
BASE_SHA = "28ac817bc3f76958ad5a33316e420c734949f24b206ddb6d083a5254b3aa70db"
STOCK_BIN = str(plain_image_path("stock_fw_dump/code.bin"))
V91_BIN = str(plain_image_path("_v91_V90BASE-CBE74.M26.M27.X1.5_plain_image.bin"))
V91_SHA = "0ea15ca9d5f811ddcf915b33237dc3f686461f6b84afb7c476e9f1d2b8a011b1"

# =================================================================================================
# PART 1 -- THE CALIBRATION LEVER.  Identical to builds/v80_v107/build_v91_tva.py, copied verbatim.
# =================================================================================================
FRICTION_PTR_ARRAY = 0xCBE74
FRICTION_N_MODES = 34                  # 🛑 modes 0..33. A GIVEN BOUND, not a walk. 0xCBE74+34*4
                                       #    = 0xCBEFC is the first slot PAST the array.
FRICTION_ARRAY_END = FRICTION_PTR_ARRAY + FRICTION_N_MODES * 4      # 0xCBEFC
REC_N_OFF, REC_X_OFF, REC_Y_OFF, REC_PAD_OFF, REC_LEN = 0x00, 0x02, 0x08, 0x0E, 0x10

MANUAL_MODES, ENGAGED_MODES = (24, 25), (26, 27)        # TVCA4: 24/25 MANUAL, 26/27 ENGAGED
TARGET_MODES = ENGAGED_MODES

FRICTION_NPT = 3
FRICTION_X = (0, 1280, 5760)           # counts of voted vehicle speed; 64 counts/km/h = [0,20,90]
FRICTION_Y_STOCK = (-9830, -5734, -1966)
SCALE_NUM, SCALE_DEN = 3, 2            # x1.5 -- EXACT in integers on all three knots
FRICTION_Y_NEW = tuple(y * SCALE_NUM // SCALE_DEN for y in FRICTION_Y_STOCK)

SPEED_COUNTS_PER_KMH = 64
CLAMP_ADDR, CLAMP_VALUE = 0xC407E, 511         # 🛑 Honda's own. The whole fault argument rests here.
DTC_1D_TRIP = 512
ROUTE77_ENGAGED_MAX = 319.1                    # measured |gp-0x6b26| at the STOCK Y row

# ---- ASSERTION 12: int32 wraparound in FUN_00036c12. Every constant re-read from the IMAGE.
INT32_MAX = 2 ** 31 - 1
TP = 0xBF000                                   # 🛑 tp+0x740A = 0xC640A, NOT 0xC740A
GATE_ORI_IMM_ADDR, GATE_ORI_IMM = 0x36C24, 0xFA01     # `ori 0xfa01,r0,r11`   @0x36C22
GATE_ADDI_IMM_ADDR, GATE_ADDI_IMM = 0x36C28, 0x7D00   # `addi 0x7d00,r9,r14`  @0x36C26
MUL_IMM_ADDR, MUL_IMM = 0x36CC2, 0x111                # `movea 0x111,r0,r6`   @0x36CC0
PRE_SAR_ADDR, PRE_SAR = 0x36CC4, bytes.fromhex("a66a")     # `sar 0x6,r13`
MUL_ADDR, MUL_BYTES = 0x36CC6, bytes.fromhex("ed372002")   # `mul r13,r6,r0` -- r0 = HIGH, DISCARDED
POST_SAR_ADDR, POST_SAR = 0x36CCA, bytes.fromhex("b232")   # `sar 0x12,r6`
SVAR7_FALLBACKS = {TP + 0x740A: -8192, TP + 0x740C: -3277}  # the two non-LERP sources of sVar7

V74_V75_MODES = (2, 3, 5, 10, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33)
V74_V75_IMAGES = ("_v74_engagedcols_x0_12_addonly_plain_image.bin",
                  "_v75_CY0.566-EX1.200_magprobe_plain_image.bin")

# =================================================================================================
# PART 2 -- THE INSTRUMENT
# =================================================================================================
CAVE_BASE, CAVE_FREE_END = 0xC4B34, 0xC4FF0
V90_CAVE = bytes.fromhex(
    "003a2437da946032ae05483a24370a946032ae058031a9326032a305443a24371e956032"
    "a305423a243700946032ae05413ac43a483a8437edeac636070007314437ecea2436e8ea7f00")

# ---- the Y1 gate table. DECLARED here, ASSERTED against the image before anything is built. -----
LERP_Y1_TABLE = 0xC695C                 # tp+0x795c. count, then 5 X knots, then 5 Y knots.
LERP_Y1_N = 5
LERP_Y1_X = (-397, -192, 140, 294, 384)
LERP_Y1_Y = (0, 2560, 2560, 717, 0)     # all >= 0, and ZERO at BOTH end knots
LERP_Y1_SCALE_ADDR, LERP_Y1_SCALE = 0xC63BE, 1024

# 🛑 OPEN interval (-397, 384), i.e. -396 <= x <= 383. Y1 is 0 AT the end knots as well as beyond
#    them -- asserted from the image below -- so the semantically EXACT "outer gate open" predicate
#    is the open form. The closed form would read 1 at exactly x == X[0] and x == X[4], where Y1 is
#    in fact 0: 2 of 782 integer values, 0.26 %, and the same instruction count either way. Exact
#    beats close when exact is free.
WINDOW_CLOSED = False
WIN_LO = LERP_Y1_X[0] if WINDOW_CLOSED else LERP_Y1_X[0] + 1
WIN_HI = LERP_Y1_X[-1] if WINDOW_CLOSED else LERP_Y1_X[-1] - 1
WIN_BIAS = -WIN_LO                      # OPEN form (shipped): 396 -- `addi 0x18c,r6,r6`
WIN_SPAN = WIN_HI - WIN_LO + 1          # OPEN form (shipped): 780 -- `addi -0x30c,r6,r0`, then bnh on CY
#    🛑 COMMENT-ONLY CORRECTION, 2026-08-11: these two comments previously read 397 / `0x18d` and
#    782 / `0x30e`, which are the CLOSED-window values. WINDOW_CLOSED is False, so the code has
#    always computed 396 / 780 and the BUILT IMAGE carries `addi 0x18c` + `addi -0x30c` (verified by
#    reading the cave back from the image and by Ghidra's own decode). The artefact was never wrong;
#    only the comment was. Recorded rather than silently patched because those two numbers are
#    exactly the kind that get quoted into a scorer spec and then cannot be reconciled with the bytes.
#    (x + BIAS) <u SPAN   <=>   WIN_LO <= x <= WIN_HI, for every int16 x, signs included.
WIN_BIAS_HW = struct.pack("<h", WIN_BIAS)      # DERIVED, not twinned -- see the header
WIN_SPAN_HW = struct.pack("<h", -WIN_SPAN)     # DERIVED, not twinned -- see the header

PAYLOAD = (bytes.fromhex(
    #  byte4 field -------------------------------------------------------------------------------
    "003a"          # +0x00  mov   0x0,r7
    "24374294"      # +0x02  ld.h  -0x6bbe[gp],r6      BOOST lane
    "6032" "ae05"   # +0x06  cmp 0x0,r6 / bge +4 -> +0x0C
    "483a"          # +0x0A  add   0x8,r7              b7 = gp-0x6bbe < 0
    "2437" "9e94"   # +0x0C  ld.h  -0x6b62[gp],r6      RETURN-CENTRE lane
    "6032" "ae05"   # +0x10  cmp 0x0,r6 / bge +4 -> +0x16
    "443a"          # +0x14  add   0x4,r7              b6 = gp-0x6b62 < 0
    "6032" "a305"   # +0x16  cmp 0x0,r6 / bnh +4 -> +0x1C   (r6 is the SAME sample)
    "423a"          # +0x1A  add   0x2,r7              b5 = gp-0x6b62 != 0
    "2437" "2694"   # +0x1C  ld.h  -0x6bda[gp],r6      THE OUTER GATE's own axis
    "0636")         # +0x20  addi  <BIAS>,r6,r6        r6 = x + 397
    + WIN_BIAS_HW   # +0x22  ...................       DERIVED from X[0]
    + bytes.fromhex(
    "0606")         # +0x24  addi  <-SPAN>,r6,r0       flags only; CY = (r6 >=u 782) = OUTSIDE
    + WIN_SPAN_HW   # +0x26  ...................       DERIVED from X[4]-X[0]+1
    + bytes.fromhex(
    "a305"          # +0x28  bnh   +4 -> +0x2C         skip iff OUTSIDE  (bnh == bc after this addi)
    "413a"          # +0x2A  add   0x1,r7              b4 = gp-0x6bda IN WINDOW
    "c43a" "483a"   # +0x2C  shl 0x4,r7 / add 0x8,r7   b3 = FINGERPRINT, always 1
    "8437edea"      # +0x30  ld.bu -0x1514[gp],r6
    "c6360700"      # +0x34  andi  0x7,r6,r6           keep Honda's bits 2:0
    "0731"          # +0x38  or    r7,r6
    "4437ecea"      # +0x3A  st.b  r6,-0x1514[gp]      0x14A byte 4
    #  byte7 field -- NEVER WRITTEN BY ANY BUILD -----------------------------------------------
    "2437" "7e95"   # +0x3E  ld.h  -0x6a82[gp],r6      DWELL COUNTER
    "e53f" "7f72"   # +0x42  ld.hu 0x727e[tp],r7       cal 0xC627E = 20
    "e731"          # +0x46  cmp   r7,r6               flags = counter - cal
    "003a"          # +0x48  mov   0x0,r7              🛑 MOV sets NO flags (witness 0x498E4)
    "a305"          # +0x4A  bnh   +4 -> +0x4E         skip iff counter <=u cal
    "413a"          # +0x4C  add   0x1,r7              byte7 b6 = SNAP ACTIVE
    "2437da94"      # +0x4E  ld.h  -0x6b26[gp],r6      the DOSED friction/damping lane
    "6032" "ae05"   # +0x52  cmp 0x0,r6 / bge +4 -> +0x58
    "8031"          # +0x56  subr  r0,r6               r6 = |gp-0x6b26|  (NOT satsubr 3080)
    "6e32" "a305"   # +0x58  cmp 0xe,r6 / bnh +4 -> +0x5E
    "423a"          # +0x5C  add   0x2,r7              byte7 b7 = |gp-0x6b26| >= 15  DOSE-IN-FORCE
    "c63a"          # +0x5E  shl   0x6,r7              -> bits 7:6
    "a437efea"      # +0x60  ld.bu -0x1511[gp],r6
    "c6363f00"      # +0x64  andi  0x3f,r6,r6          keep Honda's bits 5:0
    "0731"          # +0x68  or    r7,r6
    "4437efea"      # +0x6A  st.b  r6,-0x1511[gp]      0x14A byte 7
    #  return ------------------------------------------------------------------------------------
    "2436e8ea"      # +0x6E  movea -0x1518,gp,r6       restore the hooked instruction
    "7f00"))        # +0x72  jmp   [lp]

HOOK_ADDR, HOOK_BYTES = 0x55C0E, bytes.fromhex("86ff26ef")   # jarl 0xC4B34,lp -- V90's, UNCHANGED
R427_ADDR = 0x55DF2                          # hw2 of `ld.h ..[gp],r6` inside the 0x1AB builder
R427_OLD, R427_NEW = 0x6B26, 0x6BBE          # gp-relative, both negative, both even => ld.h form

# THE 427 SCALE FIX. `sar 0x3,r6` -> `sar 0x4,r6` in FUN_00055d80's packer, so the new source
# cannot reach the 0x3FF clamp anywhere in its own +-2048 aggregator window.
R427_SAR_ADDR = 0x55E10
R427_SAR_OLD, R427_SAR_NEW = bytes.fromhex("a332"), bytes.fromhex("a432")
R427_MUL, R427_FIELD_MAX = 5, 0x3FF          # clamp(|src| * 5 >> shift, 0, 0x3FF)
R427_LANE_WINDOW = 2048                      # gp-0x6bbe's aggregator window, +-2048

DWELL_CAL_ADDR, DWELL_CAL = 0xC627E, 20      # tp+0x727e -- the snap threshold FUN_00036388 tests
DOSE_T = 15                                  # |gp-0x6b26| >= 15; encoded as `cmp 0xe` + `bnh`

# 🛑 EVERY BYTE OF THE PAYLOAD, and the address it is COPIED FROM in this base image. Coverage is
#    asserted to be 110/110 -- nothing is hand-encoded, and nothing is left unaccounted for.
#    (offset, width, source, note).  Sources marked V90+ are V90's own flown cave.
TWINS = [
    (0x00, 2, CAVE_BASE + 0x00, "mov   0x0,r7                   V90 cave +0x00"),
    (0x02, 4, 0x3AC80, "ld.h  -0x6bbe[gp],r6           HONDA: the AGGREGATOR's own boost read"),
    (0x06, 2, CAVE_BASE + 0x06, "cmp   0x0,r6                   V90 cave +0x06"),
    (0x08, 2, CAVE_BASE + 0x08, "bge   +4                       V90 cave +0x08"),
    (0x0A, 2, CAVE_BASE + 0x0A, "add   0x8,r7                   V90 cave +0x0A"),
    (0x0C, 2, CAVE_BASE + 0x02, "ld.h hw1 `2437`                V90 cave +0x02"),
    (0x0E, 2, 0x36508, "hw2 -0x6b62                    HONDA: ld.h -0x6b62,gp,r13 @0x36506"),
    (0x10, 2, CAVE_BASE + 0x06, "cmp   0x0,r6                   V90 cave +0x06"),
    (0x12, 2, CAVE_BASE + 0x08, "bge   +4                       V90 cave +0x08"),
    (0x14, 2, CAVE_BASE + 0x1C, "add   0x4,r7                   V90 cave +0x1C"),
    (0x16, 2, CAVE_BASE + 0x06, "cmp   0x0,r6                   V90 cave +0x06"),
    (0x18, 2, CAVE_BASE + 0x1A, "bnh   +4                       V90 cave +0x1A"),
    (0x1A, 2, CAVE_BASE + 0x26, "add   0x2,r7                   V90 cave +0x26"),
    (0x1C, 2, CAVE_BASE + 0x02, "ld.h hw1 `2437`                V90 cave +0x02"),
    (0x1E, 2, 0x36104, "hw2 -0x6bda                    HONDA: the ld.h -0x6bda[gp],rX inside"
                       " FUN_000360fe, the very LERP this bit is about"),
    (0x20, 2, 0x29D1A, "addi hw1 `0636` (imm,r6,r6)    HONDA @0x29D1A"),
    # +0x22 WIN_BIAS_HW -- DERIVED from the image's own X[0], see DERIVED_IMM below
    (0x24, 2, 0x498E0, "addi hw1 `0606` (imm,r6,r0)    HONDA: addi -0x53,r6,r0 @0x498E0 -- Honda's"
                       " own compiled unsigned range-test idiom, r0 = discard, flags only"),
    # +0x26 WIN_SPAN_HW -- DERIVED from the image's own X[4]-X[0]+1
    (0x28, 2, CAVE_BASE + 0x1A, "bnh   +4                       V90 cave +0x1A"),
    (0x2A, 2, CAVE_BASE + 0x30, "add   0x1,r7                   V90 cave +0x30"),
    (0x2C, 4, CAVE_BASE + 0x32, "shl 0x4,r7 / add 0x8,r7        V90 cave +0x32 (fingerprint tail)"),
    (0x30, 14, CAVE_BASE + 0x36, "the byte4 RMW epilogue, 14 B   V90 cave +0x36, byte-identical"),
    (0x3E, 2, CAVE_BASE + 0x02, "ld.h hw1 `2437`                V90 cave +0x02"),
    (0x40, 2, 0x36430, "hw2 -0x6a82                    HONDA: ld.h -0x6a82,gp,r14 @0x3642E"),
    (0x42, 2, 0x1EA2E, "ld.hu hw1 `e53f` (tp,r7)       HONDA: ld.hu -0x738c,tp,r7 @0x1EA2E"),
    (0x44, 2, 0x36446, "hw2 0x727f                     HONDA: ld.hu 0x727e,tp,r6 @0x36444 -- the"
                       " very instruction FUN_00036388 uses to read this cal"),
    (0x46, 2, 0x1C5CC, "cmp   r7,r6  `e731`            HONDA @0x1C5CC (reg2=r6 => r6 - r7)"),
    (0x48, 2, CAVE_BASE + 0x00, "mov   0x0,r7                   V90 cave +0x00"),
    (0x4A, 2, CAVE_BASE + 0x1A, "bnh   +4                       V90 cave +0x1A"),
    (0x4C, 2, CAVE_BASE + 0x30, "add   0x1,r7                   V90 cave +0x30"),
    (0x4E, 4, CAVE_BASE + 0x02, "ld.h  -0x6b26[gp],r6           V90 cave +0x02, byte-identical"),
    (0x52, 2, CAVE_BASE + 0x06, "cmp   0x0,r6                   V90 cave +0x06"),
    (0x54, 2, CAVE_BASE + 0x08, "bge   +4                       V90 cave +0x08"),
    (0x56, 2, CAVE_BASE + 0x14, "subr  r0,r6  `8031`            V90 cave +0x14  🛑 NOT satsubr 3080"),
    (0x58, 2, 0x498EE, "cmp   0xe,r6 `6e32`            HONDA @0x498EE -- and Honda's own next"
                       " instruction there is a `bnh`, the identical idiom"),
    (0x5A, 2, CAVE_BASE + 0x1A, "bnh   +4                       V90 cave +0x1A"),
    (0x5C, 2, CAVE_BASE + 0x26, "add   0x2,r7                   V90 cave +0x26"),
    (0x5E, 2, 0x368B6, "shl   0x6,r7 `c63a`            HONDA @0x368B6"),
    (0x60, 4, 0x55C1C, "ld.bu -0x1511[gp],r6           HONDA: the 0x14A builder's OWN byte-7 read,"
                       " 14 bytes below the hook"),
    (0x64, 4, 0x59D0E, "andi  0x3f,r6,r6               HONDA @0x59D0E"),
    (0x68, 2, CAVE_BASE + 0x3E, "or    r7,r6                    V90 cave +0x3E"),
    (0x6A, 4, 0x55C2A, "st.b  r6,-0x1511[gp]           HONDA: the 0x14A builder's OWN byte-7 write,"
                       " 30 bytes below the hook"),
    (0x6E, 6, CAVE_BASE + 0x44, "movea -0x1518,gp,r6 / jmp [lp] V90 cave +0x44, the return"),
]

# 🛑 The ONLY payload bytes with no twin: two pure-data imm16 halfwords. They are DERIVED from the
#    LERP table read out of the image and asserted here. No encoding ambiguity exists in an imm16.
DERIVED_IMM = [
    (0x22, lambda: WIN_BIAS_HW, f"addi imm16 = +{WIN_BIAS}  = -(X[0]+1), the OPEN lower edge"),
    (0x26, lambda: WIN_SPAN_HW, f"addi imm16 = -{WIN_SPAN} = -((X[4]-1) - (X[0]+1) + 1)"),
]

# =================================================================================================
# EVERYTHING THAT MUST NOT MOVE. Asserted on the base AND re-asserted on the built image.
# =================================================================================================
FROZEN = {
    0xC407E: (2, 511, "🛑 HARD-FAULT INTERLOCK CLAMP -- Honda's 511, one under its own 512 trip"),
    0xC40D2: (2, 204, "K1 modelled Coulomb friction -- V89's lever, CARRIED unchanged"),
    0xC4080: (2, 0, "K0 pure-Coulomb arm -- the recorded NEVER-RAISE relay hazard, stays 0"),
    0xC40BC: (2, 600, "friction relay gate -- 600. 6000 measured 2.3x WORSE; DO NOT restore it"),
    0xC40D0: (2, 408, "friction EMA alpha (16.7 Hz)"),
    0xC40D4: (2, 573, "command-branch EMA -- V86's FALSIFIED lever"),
    0xC40D8: (2, 3686, "friction-family constant"),
    0xC646E: (2, 1428, "INERTIA/damping gain -- unmeasured sizing figure"),
    0xC63A0: (2, 1024, "INERT, no mechanism"),
    0xC63A2: (2, 1024, "loop-gain family"),
    0xC63A4: (2, 1024, "loop-gain family"),
    0xC63A6: (2, 1024, "observer weight on gp-0x6b26 (Path 2) -- FROZEN, so the dose is the ONLY"
                       " thing that moves in the observer"),
    0xC63A8: (2, 1024, "loop-gain family"),
    0xC63AA: (2, 1024, "loop-gain family"),
    0xC63AC: (2, 102, "loop-gain family"),
    0xC63AE: (2, 1024, "loop-gain family"),
    0xC6200: (2, 8192, "loop-gain family"),
    0xC6446: (2, 5244, "Lever B arm -- V88's 5244"),
    0xC6468: (2, 2639, "model output gain -- SHARED, 5 readers"),
    0xC646C: (2, 891, "shared sensor scale -- Honda 891"),
    0xC6CD0: (2, 3564, "private forward LKAS gain = 4.000x, NEVER lower"),
    0xC62EA: (2, 0, "steer-to-zero"),
    0xC61F6: (2, 3, "r24 deadzone"),
    # 🛑 the four cells V92 READS but does NOT move -- moving any of them would silently redefine
    #    what the new rungs mean.
    0xC618A: (2, 1024, "🛑 READ-ONLY FOR V92: the dwell ARM threshold (|gp-0x6b64| < this)"),
    0xC627E: (2, 20, "🛑 READ-ONLY FOR V92: the dwell SNAP threshold -- byte7 b6 reads this cal"),
    0xC63C2: (2, 1024, "🛑 READ-ONLY FOR V92"),
    0x3AA96: (1, 0xFB, "Lever B gate -- V88's"),
    0x454FE: (1, 0xB5, "V42's ratchet fix -- restored at V80, carried V87/V88/V89/V90"),
    0x3AB76: (1, 0xAA, "Lever A r26 sar -- DO NOT RESTORE"),
    0x3AC20: (1, 0xAA, "Lever A r24 sar -- DO NOT RESTORE"),
    0xC64A1: (1, 1, "🛑 READ-ONLY FOR V92"),
}

# 🛑 the token names the SIGNALS the cave actually reads. b4 is gp-0x6bda (the outer-gate window),
#    NOT gp-0x6abc -- the convention anchor lost the slot; SAR4 marks the 427 no-clip packer fix.
VARIANT_TOKEN = "V90BASE-CBE74.M26.M27.X1.5-CAVE.6BBE.6B62.6BDA.6A82-427.6BBE.SAR4"
TAG = VARIANT_TOKEN
BIN_OUT = str(plain_image_path(f"_v92_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V92-{TAG}-0x{START:X}-0x{END:X}.rwd")

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    """Every assertion prints a BOOLEAN. A check that produces no output is not a check that passed."""
    _checks[0] += 1
    if cond:
        _checks[1] += 1
        print(f"    {OK} {msg}")
        return True
    print(f"    {BAD} {msg}")
    raise SystemExit(f"🛑 ABORTING -- assertion {_checks[0]} FAILED: {msg}")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def rd(buf, a, w):
    return bytes(buf[a:a + w])


def rec_addr(buf, mode):
    """🛑 DEREFERENCE. An address is not a mode. Never hard-code a record address."""
    return struct.unpack_from("<I", buf, FRICTION_PTR_ARRAY + mode * 4)[0]


def rec_fields(buf, mode):
    p = rec_addr(buf, mode)
    return (p,
            u16(buf, p + REC_N_OFF),
            struct.unpack_from("<3h", buf, p + REC_X_OFF),
            struct.unpack_from("<3h", buf, p + REC_Y_OFF),
            u16(buf, p + REC_PAD_OFF))


def lerp_y(y_row, speed_counts):
    """Piecewise-linear interpolation over the SPEED axis, integer, knots read LE from the image.

    ⚠ SCOPE. An ILLUSTRATION of the surface SHAPE, not a byte-exact mirror of FUN_00036c12: the
      firmware's interior rounding is not re-derived. The load-bearing claim -- that the dose is
      exactly x1.5 -- rests on the THREE KNOTS, read from the built image, and is exact.
    """
    x = FRICTION_X
    if speed_counts <= x[0]:
        return y_row[0]
    if speed_counts >= x[FRICTION_NPT - 1]:
        return y_row[FRICTION_NPT - 1]
    for i in range(FRICTION_NPT - 1):
        if x[i] <= speed_counts < x[i + 1]:
            return y_row[i] + (y_row[i + 1] - y_row[i]) * (speed_counts - x[i]) // (x[i + 1] - x[i])
    raise AssertionError("speed fell outside every LERP segment")


def assert_frozen(buf, label):
    bad = [(a, u16(buf, a) if w == 2 else buf[a], want, why)
           for a, (w, want, why) in sorted(FROZEN.items())
           if (u16(buf, a) if w == 2 else buf[a]) != want]
    for a, got, want, why in bad:
        print(f"    {BAD} 0x{a:05X} is {got}, expected {want} -- {why}")
    check(not bad, f"{label}: all {len(FROZEN)} FROZEN cells at their expected values")


# =================================================================================================
# A V850E2 decoder covering exactly the formats this cave uses. It exists so the script
# RE-DISASSEMBLES THE PAYLOAD FROM THE BUILT IMAGE and checks it against the RUNG TABLE, rather
# than checking the bytes against the string it was handed. Every form confirmed in GhidraMCP.
# =================================================================================================
COND = {0x3: "bnh", 0xE: "bge"}
RN = {0: "r0", 3: "sp", 4: "gp", 5: "tp", 30: "ep", 31: "lp"}


def rn(i):
    return RN.get(i, f"r{i}")


def _s16(v):
    return v - 0x10000 if v >= 0x8000 else v


def decode(img, addr):
    """Return (text, length, kind, operand, writes, refs) for one instruction at `addr`."""
    hw1 = struct.unpack_from("<H", img, addr)[0]
    reg2, op, reg1 = (hw1 >> 11) & 0x1F, (hw1 >> 5) & 0x3F, hw1 & 0x1F
    imm5 = hw1 & 0x1F
    if op == 0x10:
        return f"mov   0x{imm5:x},{rn(reg2)}", 2, "mov", None, {reg2}, {reg2}
    if op == 0x12:
        return f"add   0x{imm5:x},{rn(reg2)}", 2, "add", imm5, {reg2}, {reg2}
    if op == 0x13:
        return f"cmp   0x{imm5:x},{rn(reg2)}", 2, "cmp", imm5, set(), {reg2}
    if op == 0x0F:
        return f"cmp   {rn(reg1)},{rn(reg2)}", 2, "cmp", None, set(), {reg1, reg2}
    if op == 0x15:
        return f"sar   0x{imm5:x},{rn(reg2)}", 2, "sar", imm5, {reg2}, {reg2}
    if op == 0x16:
        return f"shl   0x{imm5:x},{rn(reg2)}", 2, "shl", imm5, {reg2}, {reg2}
    if op == 0x0C:
        return f"subr  {rn(reg1)},{rn(reg2)}", 2, "subr", None, {reg2}, {reg1, reg2}
    if op == 0x08:
        return f"or    {rn(reg1)},{rn(reg2)}", 2, "or", None, {reg2}, {reg1, reg2}
    if op == 0x03 and reg2 == 0:
        return f"jmp   [{rn(reg1)}]", 2, "jmp", None, set(), {reg1}
    if (hw1 >> 7) & 0xF == 0xB:                                  # Format III  bcond disp9
        disp = (((hw1 >> 11) & 0x1F) << 4) | (((hw1 >> 4) & 0x7) << 1)
        disp -= 0x200 if disp & 0x100 else 0
        c = hw1 & 0xF
        return f"{COND.get(c, f'b?{c:x}'):5s} +{disp}", 2, "branch", disp, set(), set()
    hw2 = struct.unpack_from("<H", img, addr + 2)[0]
    if op == 0x30:                                # addi imm16,reg1,reg2 -- reg2 == r0 = flags only
        return (f"addi  {_s16(hw2):#x},{rn(reg1)},{rn(reg2)}", 4, "addi",
                (reg1, _s16(hw2)), {reg2}, {reg1, reg2})
    if op == 0x36:
        return (f"andi  0x{hw2:x},{rn(reg1)},{rn(reg2)}", 4, "andi", (reg1, hw2),
                {reg2}, {reg1, reg2})
    if op == 0x31:
        return (f"movea {_s16(hw2):#x},{rn(reg1)},{rn(reg2)}", 4, "movea",
                (reg1, _s16(hw2)), {reg2}, {reg1, reg2})
    if op == 0x39:                                # ld.h (hw2 bit0 == 0) / ld.w (bit0 == 1)
        name, d = ("ld.w", hw2 & ~1) if hw2 & 1 else ("ld.h", hw2)
        return (f"{name}  {_s16(d):#x}[{rn(reg1)}],{rn(reg2)}", 4, name,
                (reg1, _s16(d)), {reg2}, {reg1, reg2})
    if op == 0x38:                                # ld.b, full disp16
        return (f"ld.b  {_s16(hw2):#x}[{rn(reg1)}],{rn(reg2)}", 4, "ld.b",
                (reg1, _s16(hw2)), {reg2}, {reg1, reg2})
    if op in (0x3C, 0x3D):                        # ld.bu -- disp bit0 lives in the op field LSB
        d = (hw2 & ~1) | (op & 1)
        return (f"ld.bu {_s16(d):#x}[{rn(reg1)}],{rn(reg2)}", 4, "ld.bu",
                (reg1, _s16(d)), {reg2}, {reg1, reg2})
    if op in (0x3E, 0x3F):                        # ld.hu -- hw2 bit0 is a marker, disp is even
        d = hw2 & ~1
        return (f"ld.hu {_s16(d):#x}[{rn(reg1)}],{rn(reg2)}", 4, "ld.hu",
                (reg1, _s16(d)), {reg2}, {reg1, reg2})
    if op == 0x3A:                                # st.b, full disp16
        return (f"st.b  {rn(reg2)},{_s16(hw2):#x}[{rn(reg1)}]", 4, "st.b",
                (reg1, _s16(hw2)), set(), {reg1, reg2})
    if op == 0x3B:                                # st.h (bit0 == 0) / st.w (bit0 == 1)
        name, d = ("st.w", hw2 & ~1) if hw2 & 1 else ("st.h", hw2)
        return (f"{name}  {rn(reg2)},{_s16(d):#x}[{rn(reg1)}]", 4, name,
                (reg1, _s16(d)), set(), {reg1, reg2})
    return f"op{op:02x} ??", 4, f"op{op:02x}", None, {reg2}, {reg1, reg2}


def disassemble_cave(img, base, length):
    out, off = [], 0
    while off < length:
        text, n, kind, operand, writes, refs = decode(img, base + off)
        out.append((off, base + off, rd(img, base + off, n).hex(), text, kind, operand,
                    writes, refs))
        off += n
    assert off == length, f"the last instruction overruns the payload by {off - length} byte(s)"
    return out


# The rung table, as INTENT. The built image is checked against THIS, not against the spec string.
EXPECTED = [
    (0x00, "mov   0x0,r7", ""),
    (0x02, "ld.h  -0x6bbe[gp],r6", "the BOOST lane"),
    (0x06, "cmp   0x0,r6", ""), (0x08, "bge   +4", "-> +0x0C"),
    (0x0A, "add   0x8,r7", "b7 = gp-0x6bbe < 0"),
    (0x0C, "ld.h  -0x6b62[gp],r6", "the RETURN-CENTRE lane"),
    (0x10, "cmp   0x0,r6", ""), (0x12, "bge   +4", "-> +0x16"),
    (0x14, "add   0x4,r7", "b6 = gp-0x6b62 < 0"),
    (0x16, "cmp   0x0,r6", "same r6 sample"), (0x18, "bnh   +4", "-> +0x1C, unsigned: skip iff == 0"),
    (0x1A, "add   0x2,r7", "b5 = gp-0x6b62 != 0"),
    (0x1C, "ld.h  -0x6bda[gp],r6", "the OUTER GATE's axis"),
    (0x20, f"addi  {WIN_BIAS:#x},r6,r6", f"r6 = x + {WIN_BIAS}  (= -X[0])"),
    (0x24, f"addi  {-WIN_SPAN:#x},r6,r0", f"flags only; CY = (r6 >=u {WIN_SPAN}) = OUTSIDE"),
    (0x28, "bnh   +4", "-> +0x2C, skip iff OUTSIDE"),
    (0x2A, "add   0x1,r7", "b4 = gp-0x6bda IN WINDOW"),
    (0x2C, "shl   0x4,r7", ""),
    (0x2E, "add   0x8,r7", "b3 = FINGERPRINT, always 1"),
    (0x30, "ld.bu -0x1514[gp],r6", ""),
    (0x34, "andi  0x7,r6,r6", "keep Honda's bits 2:0"),
    (0x38, "or    r7,r6", ""),
    (0x3A, "st.b  r6,-0x1514[gp]", "0x14A byte 4"),
    (0x3E, "ld.h  -0x6a82[gp],r6", "the DWELL COUNTER"),
    (0x42, "ld.hu 0x727e[tp],r7", "cal 0xC627E = 20, the SNAP threshold"),
    (0x46, "cmp   r7,r6", "flags = counter - cal"),
    (0x48, "mov   0x0,r7", "🛑 MOV sets NO flags"),
    (0x4A, "bnh   +4", "-> +0x4E, skip iff counter <=u cal"),
    (0x4C, "add   0x1,r7", "byte7 b6 = SNAP ACTIVE"),
    (0x4E, "ld.h  -0x6b26[gp],r6", "the DOSED lane"),
    (0x52, "cmp   0x0,r6", ""), (0x54, "bge   +4", "-> +0x58"),
    (0x56, "subr  r0,r6", "r6 = |gp-0x6b26|"),
    (0x58, "cmp   0xe,r6", "THRESHOLD 15"), (0x5A, "bnh   +4", "-> +0x5E"),
    (0x5C, "add   0x2,r7", "byte7 b7 = |gp-0x6b26| >= 15  DOSE-IN-FORCE"),
    (0x5E, "shl   0x6,r7", "-> bits 7:6"),
    (0x60, "ld.bu -0x1511[gp],r6", ""),
    (0x64, "andi  0x3f,r6,r6", "keep Honda's bits 5:0"),
    (0x68, "or    r7,r6", ""),
    (0x6A, "st.b  r6,-0x1511[gp]", "0x14A byte 7  -- VIRGIN ON EVERY PRIOR BUILD"),
    (0x6E, "movea -0x1518,gp,r6", "restore the hooked instruction"),
    (0x72, "jmp   [lp]", ""),
]

M32 = 0xFFFFFFFF


def wire_byte4(x6bbe, x6b62, x6bda, honda_bits=0x7):
    """Mirrors the cave's integer arithmetic EXACTLY, one line per instruction offset."""
    r7 = 0
    r6 = x6bbe                                   # +0x02 ld.h   (SIGN-EXTENDS)
    if not r6 >= 0:         r7 += 8              # +0x06 cmp / +0x08 bge   b7 SIGN
    r6 = x6b62                                   # +0x0C ld.h
    if not r6 >= 0:         r7 += 4              # +0x10 cmp / +0x12 bge   b6 SIGN
    if not (r6 & M32) <= 0: r7 += 2              # +0x16 cmp / +0x18 bnh   b5 != 0 (same sample)
    r6 = x6bda                                   # +0x1C ld.h   (SIGN-EXTENDS)
    r6 = (r6 + WIN_BIAS) & M32                   # +0x20 addi   32-bit wrap, negatives go huge
    # +0x24 `addi -SPAN,r6,r0` sets CY = carry-OUT = (r6 >=u SPAN) and Z = (r6 == SPAN).
    # +0x28 `bnh` takes CY|Z, which is exactly (r6 >=u SPAN) since Z implies CY here.
    if not (r6 >= WIN_SPAN): r7 += 1             # +0x28 bnh / +0x2A add   b4 IN WINDOW
    return ((honda_bits & 0x7) | (((r7 << 4) & M32) + 8)) & 0xFF   # +0x2C shl / +0x2E add


def wire_byte7(x6a82, cal, x6b26, honda_bits=0x3F):
    """Mirrors the cave's integer arithmetic EXACTLY, one line per instruction offset."""
    r6 = x6a82                                   # +0x38 ld.h   (SIGN-EXTENDS)
    r7 = cal & 0xFFFF                            # +0x3C ld.hu  (ZERO-EXTENDS)
    lhs, rhs = r6 & M32, r7 & M32                # +0x40 cmp r7,r6 -> flags from (r6 - r7) UNSIGNED
    r7 = 0                                       # +0x42 mov 0x0,r7   -- sets NO flags
    if not lhs <= rhs:      r7 += 1              # +0x44 bnh / +0x46 add   b6 SNAP ACTIVE
    r6 = x6b26                                   # +0x48 ld.h
    if not r6 >= 0: r6 = 0 - r6                  # +0x4C cmp / +0x4E bge / +0x50 subr  r6 = |x|
    if not (r6 & M32) <= 14: r7 += 2             # +0x52 cmp 0xe / +0x54 bnh  b7 DOSE-IN-FORCE
    return ((honda_bits & 0x3F) | ((r7 << 6) & M32)) & 0xFF        # +0x58 shl


def assert_rung_semantics():
    """Corner grid over both signs, every threshold boundary and every sentinel."""
    vals = [-32768, -20000, -1024, -513, -512, -399, -398, -397, -396, -395, -16, -15, -14,
            -1, 0, 1, 14, 15, 16, 382, 383, 384, 385, 386, 511, 512, 1024, 2048, 9262,
            20000, 32767]
    n = 0
    for a in vals:
        for b in vals:
            for c in vals:
                w = wire_byte4(a, b, c)
                assert w & 0x08, "b3 fingerprint is not 1 -- every wire value must be ODD"
                assert bool(w & 0x80) == (a < 0), "b7 is not sign(gp-0x6bbe)"
                assert bool(w & 0x40) == (b < 0), "b6 is not sign(gp-0x6b62)"
                assert bool(w & 0x20) == (b != 0), "b5 is not (gp-0x6b62 != 0)"
                assert bool(w & 0x10) == (WIN_LO <= c <= WIN_HI), \
                    f"b4 is not (gp-0x6bda in [{WIN_LO},{WIN_HI}]) at c={c}"
                assert w & 0x07 == 0x07, "Honda's byte4 bits 2:0 were not preserved"
                n += 1
    # The window edges, called out by name -- an off-by-one here is the whole rung.
    # 🛑 X[0] and X[4] themselves must read 0: Y1 is zero AT the knots, not just beyond them.
    for c, want in ((LERP_Y1_X[0] - 1, 0), (LERP_Y1_X[0], 0), (LERP_Y1_X[0] + 1, 1),
                    (LERP_Y1_X[-1] - 1, 1), (LERP_Y1_X[-1], 0), (LERP_Y1_X[-1] + 1, 0),
                    (WIN_LO - 1, 0), (WIN_LO, 1), (WIN_HI, 1), (WIN_HI + 1, 0),
                    (-32768, 0), (32767, 0), (9262, 0), (0, 1)):
        assert bool(wire_byte4(0, 0, c) & 0x10) == bool(want), f"b4 wrong at the edge c={c}"
    # 🛑 `bnh` vs `bc` after `addi -SPAN,r6,r0`: CY = (r6 >=u SPAN) is the carry-OUT of the add, and
    #    Z implies r6 == SPAN which already sets CY. So CY|Z == CY on EVERY input -- proven by
    #    exhaustion over the reachable r6, not argued. This is why the cave needs no new branch cond.
    for x in range(-32768, 32768):
        r6 = (x + WIN_BIAS) & M32
        bc_taken = r6 >= WIN_SPAN                       # CY
        bnh_taken = (r6 >= WIN_SPAN) or (r6 == WIN_SPAN)  # CY | Z
        assert bc_taken == bnh_taken, f"bnh != bc at x={x}"
    print(f"    ✅ bnh == bc on all 65,536 int16 inputs after `addi {-WIN_SPAN:#x},r6,r0` "
          f"⇒ the cave uses only {{bge, bnh}}, NO new branch condition")
    # 🛑 b6 and b5 read the SAME cell, so b6 => b5: `negative` implies `non-zero`. (b6,b5) is a
    #    deliberate THREE-state field -- (0,0) zero, (0,1) positive, (1,1) negative -- and (1,0) is
    #    STRUCTURALLY UNREACHABLE. That is a SECOND MAP VALIDATOR, not a defect: any frame showing
    #    b6=1 with b5=0 means the field is being read at the wrong bit offset.
    codes = {wire_byte4(a, b, c, 0) >> 3 for a in (-1, 1) for b in (-1, 0, 1) for c in (0, 32767)}
    reachable = {v for v in range(32) if (v & 1) and not (v & 0x08 and not v & 0x04)}
    assert codes == reachable, f"byte4 reachable set is {sorted(codes)}, expected {sorted(reachable)}"
    assert len(codes) == 12, f"{len(codes)} reachable byte4 codewords, expected 12"
    assert not any((w & 0x40) and not (w & 0x20)
                   for a in vals for b in vals for c in vals
                   for w in [wire_byte4(a, b, c)]), "b6=1 with b5=0 was reachable -- impossible"
    print(f"    ✅ byte4: {n} corner cases, ZERO deviations; exactly 12 of the 16 odd codewords "
          f"are reachable")
    print(f"       🛑 VALIDATOR 2: b6 => b5 (same cell, negative implies non-zero) ⇒ "
          f"(b6,b5) = (1,0) is IMPOSSIBLE; seeing it means the field is read at the wrong offset")

    m = 0
    for ctr in [-1, 0, 1, 19, 20, 21, 22, 100, 32767]:
        for x in vals:
            w = wire_byte7(ctr, DWELL_CAL, x)
            want_b6 = (ctr & M32) > DWELL_CAL          # the firmware's own UNSIGNED compare
            assert bool(w & 0x40) == want_b6, f"byte7 b6 wrong at counter={ctr}"
            assert bool(w & 0x80) == (abs(x) >= DOSE_T), f"byte7 b7 wrong at gp-0x6b26={x}"
            assert w & 0x3F == 0x3F, "Honda's byte7 bits 5:0 were not preserved"
            m += 1
    seen = {wire_byte7(c, DWELL_CAL, x, 0) >> 6 for c in (0, 21) for x in (0, 100)}
    assert seen == {0, 1, 2, 3}, f"only {len(seen)}/4 byte7 codewords reachable"
    print(f"    ✅ byte7: {m} corner cases, ZERO deviations; all 4 codewords reachable "
          f"⇒ byte7[7:6] != 0 is REACHABLE and is V92's identity")
    # The identity claim, stated as arithmetic: bits 7:6 can be non-zero.
    assert wire_byte7(21, DWELL_CAL, 0, 0) == 0x40 and wire_byte7(0, DWELL_CAL, 100, 0) == 0x80


def build():
    # ==============================================================================================
    # 1. THE BASE
    # ==============================================================================================
    base = bytearray(Path(BASE_BIN).read_bytes())
    base_sha = hashlib.sha256(bytes(base)).hexdigest()
    print("=" * 102)
    print("  V92 -- V91's 12 CALIBRATION BYTES + a re-specced 110-byte TELEMETRY CAVE + a 427 repoint")
    print("         0xCBE74 friction/damping LERP Y row x1.5 on modes 26/27 (ENGAGED) ONLY")
    print("         0x14A byte4[7:3] AND byte7[7:6] -- the FIRST build ever to write byte 7")
    print("         🛑 SAME LEVER, SAME DOSE as V74/V75 -- both of which HARD-FAULTED at 0xC407E=850")
    print("         🛑 the dose is 5-69x BELOW the measurable floor: the TELEMETRY is the point")
    print(f"\n    base   {os.path.basename(BASE_BIN)}")
    print(f"    sha256 {base_sha}")
    print("=" * 102)

    print("\n  [1] BASE IMAGE")
    check(len(base) == 0x100000, f"base length = {len(base)} = 0x{len(base):X} bytes (1 MiB)")
    check(base_sha == BASE_SHA, f"base sha256 == the flown V90's {BASE_SHA}")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain verifies 50/50")

    # ==============================================================================================
    # 2. POINTER IDENTITY -- DEREFERENCED, never hard-coded
    # ==============================================================================================
    print("\n  [2] POINTER IDENTITY -- every record address DEREFERENCED from 0xCBE74 + mode*4")
    EXPECT_PTR = {24: 0xD6A64, 25: 0xD7A44, 26: 0xD7A54, 27: 0xD7A64}
    for mode, want in EXPECT_PTR.items():
        got = rec_addr(base, mode)
        check(got == want, f"mode {mode}: slot 0x{FRICTION_PTR_ARRAY + mode * 4:05X} -> "
                           f"0x{got:05X} (expected 0x{want:05X})")
    check(rec_addr(base, 23) == 0xD6A54,
          "mode 23 -> 0xD6A54 -- confirming 0xD6A5C is mode 23's Y, NOT mode 24's")
    check(FRICTION_ARRAY_END == 0xCBEFC,
          f"array bound: 0xCBE74 + {FRICTION_N_MODES}*4 = 0x{FRICTION_ARRAY_END:05X} "
          f"= the FIRST SLOT PAST the {FRICTION_N_MODES}-slot array (modes 0..{FRICTION_N_MODES - 1})")
    past = struct.unpack_from("<I", base, FRICTION_ARRAY_END)[0]
    check(past == 0xDAA44,
          f"0x{FRICTION_ARRAY_END:05X} holds 0x{past:05X} -- a VALID-LOOKING pointer. This is exactly "
          f"why an exhaustion walk over-runs into gain_B; the bound is GIVEN, never discovered")

    # ==============================================================================================
    # 3. PRE-EDIT STATE
    # ==============================================================================================
    print("\n  [3] PRE-EDIT -- n, X and Y read from the BASE for all four TVCA4 modes")
    for mode in MANUAL_MODES + ENGAGED_MODES:
        p, n, x, y, pad = rec_fields(base, mode)
        arm = "MANUAL " if mode in MANUAL_MODES else "ENGAGED"
        check(n == FRICTION_NPT and x == FRICTION_X and y == FRICTION_Y_STOCK,
              f"mode {mode} ({arm}) rec 0x{p:05X}: n={n} X@0x{p + REC_X_OFF:05X}={x} "
              f"Y@0x{p + REC_Y_OFF:05X}={y} pad@0x{p + REC_PAD_OFF:05X}=0x{pad:04X}")
    check(rec_addr(base, 26) - rec_addr(base, 25) == 0x10,
          f"mode 25's record 0x{rec_addr(base, 25):05X} sits EXACTLY 0x10 below mode 26's "
          f"0x{rec_addr(base, 26):05X} -- a -0x10 slip would land on a DISENGAGED column")

    print("\n      the DOSE arithmetic")
    want = tuple(y * SCALE_NUM // SCALE_DEN for y in FRICTION_Y_STOCK)
    check(SCALE_NUM / SCALE_DEN == 1.5, f"multiplier = {SCALE_NUM}/{SCALE_DEN} = "
                                        f"{SCALE_NUM / SCALE_DEN} -- ASSERTED to be exactly 1.5")
    check(all(y * SCALE_NUM % SCALE_DEN == 0 for y in FRICTION_Y_STOCK),
          f"x1.5 is EXACT in integers on all three knots: {FRICTION_Y_STOCK} -> {want} "
          f"(no rounding, so the multiplier is not silently something else)")
    check(want == FRICTION_Y_NEW, f"declared Y row {FRICTION_Y_NEW} == the derived x1.5 row")
    check(all(-32768 <= y <= 32767 for y in FRICTION_Y_NEW),
          f"every new knot fits int16 (Y[0] = {FRICTION_Y_NEW[0]}, int16 MIN is -32768)")
    pred = ROUTE77_ENGAGED_MAX * SCALE_NUM / SCALE_DEN
    check(pred < CLAMP_VALUE,
          f"NO-CLIP: route-77 engaged max |gp-0x6b26| = {ROUTE77_ENGAGED_MAX} ct at stock; "
          f"x1.5 -> {pred:.1f} ct vs the {CLAMP_VALUE} rail "
          f"({100 * (1 - pred / CLAMP_VALUE):.1f} % headroom)")
    check(ROUTE77_ENGAGED_MAX * 2.0 > CLAMP_VALUE,
          f"and the ceiling is REAL, not decorative: x2.0 -> {ROUTE77_ENGAGED_MAX * 2:.1f} ct "
          f"CLIPS => sign(gp-0x6c2c) x {CLAMP_VALUE} = a Coulomb RELAY = the V80 mechanism")
    k_int16 = 32768 / abs(FRICTION_Y_STOCK[0])
    print(f"    ---- int16 headroom would allow k_max = 32768/{abs(FRICTION_Y_STOCK[0])} = "
          f"{k_int16:.3f}. ⚠ That is a LOOSER, DIFFERENT bound and is NOT the dose ceiling.")

    # ==============================================================================================
    # 4. THE INTERLOCK -- the entire fault argument
    # ==============================================================================================
    print("\n  [4] 🛑 THE HARD-FAULT INTERLOCK -- refuse to build if this is not Honda's 511")
    got = u16(base, CLAMP_ADDR)
    check(got == CLAMP_VALUE,
          f"base 0x{CLAMP_ADDR:05X} = {got} == {CLAMP_VALUE}, which is {DTC_1D_TRIP - CLAMP_VALUE} "
          f"count below the DTC-0x1d monitor's {DTC_1D_TRIP} trip => the monitor is STRUCTURALLY "
          f"untrippable by this lane at ANY multiplier")
    print(f"    ---- 🛑 V74 and V75 both carried 0x{CLAMP_ADDR:05X} = 850 and both HARD-FAULTED. "
          f"No flight has\n         ever separated the DOSE from the 850 interlock. The separation "
          f"is STRUCTURAL, not empirical.")

    print("\n  [5] CARRIED-FORWARD CELLS on the BASE")
    assert_frozen(base, "base")
    check(rd(base, CAVE_BASE, len(V90_CAVE)) == V90_CAVE,
          f"V90 cave 0x{CAVE_BASE:05X}-0x{CAVE_BASE + len(V90_CAVE) - 1:05X} "
          f"({len(V90_CAVE)} B) byte-exact")
    check(all(b == 0xFF for b in base[CAVE_BASE + len(V90_CAVE):CAVE_FREE_END]),
          f"0x{CAVE_BASE + len(V90_CAVE):05X}-0x{CAVE_FREE_END:05X} all virgin 0xFF "
          f"({CAVE_FREE_END - CAVE_BASE - len(V90_CAVE)} B free; V92 needs "
          f"{len(PAYLOAD) - len(V90_CAVE)} more, leaving "
          f"{CAVE_FREE_END - CAVE_BASE - len(PAYLOAD)})")
    check(rd(base, HOOK_ADDR, 4) == HOOK_BYTES,
          f"cave hook 0x{HOOK_ADDR:05X} = {HOOK_BYTES.hex()} = jarl 0x{CAVE_BASE:05X},lp UNCHANGED")
    # 🛑 decode the hook's own displacement -- Format V puts disp[21:16] in hw1[5:0], disp[15:0]
    #    in hw2. Getting this backwards is the recorded `jarl` Format-V mask bug.
    hk1, hk2 = struct.unpack_from("<HH", base, HOOK_ADDR)
    hook_target = HOOK_ADDR + (((hk1 & 0x3F) << 16) | hk2)
    check(hook_target == CAVE_BASE,
          f"the hook's disp22 DECODES to 0x{hook_target:05X} == the cave base "
          f"(disp[21:16]=0x{hk1 & 0x3F:02X} in hw1[5:0], disp[15:0]=0x{hk2:04X} in hw2)")
    check(rd(base, R427_ADDR - 2, 4) == bytes.fromhex("2437") + struct.pack("<h", -R427_OLD),
          f"427 packer 0x{R427_ADDR - 2:05X} = {rd(base, R427_ADDR - 2, 4).hex()} "
          f"= V90's ld.h -0x{R427_OLD:04X}[gp],r6")
    check((-R427_NEW & 0xFFFF) % 2 == 0 and (-R427_OLD & 0xFFFF) % 2 == 0,
          "🛑 both 427 displacements are EVEN -- an odd one would select ld.w, not ld.h")

    # ==============================================================================================
    # 5b. 🛑 byte 7 OWNERSHIP -- the only genuinely new RAM this build writes
    # ==============================================================================================
    print("\n  [5b] 🛑 CAN 0x14A BYTE 7 (gp-0x1511) -- every writer in the WHOLE image, by byte scan")
    writers = []
    a = START
    while a < END - 3:
        h1, h2 = struct.unpack_from("<HH", base, a)
        if h2 == ((-0x1511) & 0xFFFF) and (h1 >> 5) & 0x3F in (0x3A, 0x3B):
            writers.append((a, rd(base, a, 4).hex(), (h1 >> 11) & 0x1F))
        a += 2
    for w in writers:
        print(f"       0x{w[0]:05X}  {w[1]}  st.b r{w[2]},-0x1511[gp]")
    check([w[0] for w in writers] == [0x55C02, 0x55C2A],
          f"exactly {len(writers)} writers, at 0x55C02 and 0x55C2A -- both inside FUN_00055a98, "
          f"NO cave on ANY build has ever written this byte")
    check(rd(base, 0x55BFC, 4) == bytes.fromhex("c846cf00"),
          "0x55BFC = `andi 0xcf,r8,r8` -- the counter writer PRESERVES bits 7:6 (0xcf = 1100 1111)")
    check(rd(base, 0x55C24, 4) == bytes.fromhex("c636f000"),
          "0x55C24 = `andi 0xf0,r6,r6` -- the checksum-nibble writer PRESERVES bits 7:4")
    check(HOOK_ADDR < 0x55C18 < 0x55C1C,
          "the checksum call `jarl 0x57b24` @0x55C18 runs AFTER the hook @0x55C0E "
          "=> the checksum COVERS both new bits automatically; no recompute needed")

    # ==============================================================================================
    # 6. THE TWINS -- 110/110 byte coverage, nothing hand-encoded
    # ==============================================================================================
    print("\n  [6] 🛑 TWINS -- every payload byte COPIED from a verified instruction in THIS image")
    covered = bytearray(len(PAYLOAD))
    for off, w, src, why in TWINS:
        got, twin = PAYLOAD[off:off + w], rd(base, src, w)
        check(got == twin,
              f"+0x{off:02X} {got.hex():<10s} == 0x{src:05X}  {why}")
        for k in range(w):
            covered[off + k] = 1
    n_twin = sum(covered)
    print("       ---- the ONLY untwinned bytes: two pure-data imm16 halfwords, DERIVED below")
    for off, fn, why in DERIVED_IMM:
        check(PAYLOAD[off:off + 2] == fn(),
              f"+0x{off:02X} {PAYLOAD[off:off + 2].hex():<10s} DERIVED   {why}")
        for k in range(2):
            covered[off + k] = 1
    check(sum(covered) == len(PAYLOAD),
          f"🛑 PAYLOAD COVERAGE {sum(covered)}/{len(PAYLOAD)} bytes = {n_twin} TWINNED from verified "
          f"instructions + {sum(covered) - n_twin} DERIVED imm16 -- NO INSTRUCTION HAND-ENCODED "
          f"(uncovered: {[hex(i) for i, c in enumerate(covered) if not c]})")
    check(PAYLOAD[0x56:0x58] == bytes.fromhex("8031"),
          "🛑 `subr r0,r6` is 8031; the hand-derived 3080 would be `satsubr`, which SATURATES "
          "instead of negating and corrupts the DOSE-IN-FORCE bit on negative values ONLY")
    check(len(PAYLOAD) == 116, f"payload length = {len(PAYLOAD)} bytes")
    check(rd(base, 0x498E4, 2) == bytes.fromhex("0052"),
          "🛑 FLAG-PRESERVATION WITNESS: Honda's own compiler emits `mov 0x0,r10` (0x498E4) BETWEEN "
          "a flag-setting `addi ..,r0` (0x498E0) and a `bc` (0x498E6) => MOV sets no flags")

    # ==============================================================================================
    # 7. SEMANTICS -- the rung table as arithmetic, before any byte is written
    # ==============================================================================================
    print("\n  [7] RUNG SEMANTICS -- integer mirrors of the cave, corner-gridded")
    print("       the Y1 GATE TABLE, read LE from the BASE IMAGE -- the window is DERIVED from it")
    got_n = u16(base, LERP_Y1_TABLE)
    got_x = struct.unpack_from(f"<{LERP_Y1_N}h", base, LERP_Y1_TABLE + 2)
    got_y = struct.unpack_from(f"<{LERP_Y1_N}h", base, LERP_Y1_TABLE + 2 + LERP_Y1_N * 2)
    check(got_n == LERP_Y1_N and got_x == LERP_Y1_X and got_y == LERP_Y1_Y,
          f"0x{LERP_Y1_TABLE:05X}: n={got_n} X={got_x} Y={got_y}  (declared, then asserted)")
    check(got_y[0] == 0 and got_y[-1] == 0 and all(v >= 0 for v in got_y),
          f"🛑 Y1(X[0]={got_x[0]}) = {got_y[0]} and Y1(X[4]={got_x[-1]}) = {got_y[-1]}, and Y >= 0 "
          f"everywhere => Y1 = 0 AT both end knots as well as beyond them => gp-0x6b64 = 0 AT ANY "
          f"RATE there. This is why b4 exists AND why the interval is OPEN, not closed")
    check(u16(base, LERP_Y1_SCALE_ADDR) == LERP_Y1_SCALE,
          f"cal 0x{LERP_Y1_SCALE_ADDR:05X} (tp+0x{LERP_Y1_SCALE_ADDR - TP:04X}) = {LERP_Y1_SCALE} "
          f"-- the lane's final scale; V92 reads it, does not move it")
    want_lo = got_x[0] if WINDOW_CLOSED else got_x[0] + 1
    want_hi = got_x[-1] if WINDOW_CLOSED else got_x[-1] - 1
    check(WIN_LO == want_lo and WIN_HI == want_hi
          and WIN_BIAS == -want_lo and WIN_SPAN == want_hi - want_lo + 1,
          f"WINDOW DERIVED FROM THE IMAGE: ({got_x[0]},{got_x[-1]}) OPEN = [{WIN_LO},{WIN_HI}] "
          f"=> bias = {WIN_BIAS} (0x{WIN_BIAS:X}), span = {WIN_SPAN} (0x{WIN_SPAN:X}); "
          f"imm halfwords {WIN_BIAS_HW.hex()} / {WIN_SPAN_HW.hex()}"
          if not WINDOW_CLOSED else
          f"WINDOW DERIVED FROM THE IMAGE: [{WIN_LO},{WIN_HI}] CLOSED => bias = {WIN_BIAS}, "
          f"span = {WIN_SPAN}")
    check(not WINDOW_CLOSED,
          f"🛑 the OPEN form is in force: b4 reads 0 AT x = X[0] = {got_x[0]} and x = X[4] = "
          f"{got_x[-1]}, where Y1 is genuinely 0 -- the closed form would read 1 at those 2 of "
          f"{got_x[-1] - got_x[0] + 1} values (0.26 %)")
    assert_rung_semantics()
    check(u16(base, DWELL_CAL_ADDR) == DWELL_CAL,
          f"cal 0x{DWELL_CAL_ADDR:05X} (tp+0x{DWELL_CAL_ADDR - TP:04X}) = {DWELL_CAL} -- the SNAP "
          f"threshold byte7 b6 compares against. 🛑 tp = 0x{TP:05X}, so this is "
          f"0x{DWELL_CAL_ADDR:05X} and NOT 0x{DWELL_CAL_ADDR + 0x1000:05X}")
    check(u16(base, 0xC618A) == 1024,
          "cal 0xC618A (tp+0x718a) = 1024 -- the dwell ARM threshold and the snap CEILING; "
          "V92 reads neither cal, it moves neither")

    # ==============================================================================================
    # 8. THE EDITS
    # ==============================================================================================
    before = {m: (rec_addr(base, m), rd(base, rec_addr(base, m), REC_LEN))
              for m in range(FRICTION_N_MODES)}
    code = bytearray(base)
    attributed, by_addr = set(), {}

    def apply(addr, pre, post, label):
        got = rd(code, addr, len(pre))
        assert got == pre, f"0x{addr:05X}: expected {pre.hex()}, found {got.hex()}"
        code[addr:addr + len(post)] = post
        for k in range(len(post)):
            attributed.add(addr + k)
            by_addr[addr + k] = label
        print(f"    0x{addr:05X}  {len(post):4d} B   {label}")

    print("\n  [8] THE EDITS")
    new_bytes = struct.pack("<3h", *FRICTION_Y_NEW)
    check(len(new_bytes) == 6, f"each Y row is {len(new_bytes)} bytes = 3 x int16 LE "
                               f"({new_bytes.hex()})")
    for mode in TARGET_MODES:
        p = rec_addr(code, mode)
        w0, w1 = p + REC_Y_OFF, p + REC_Y_OFF + 6 - 1
        x0, x1 = p + REC_X_OFF, p + REC_X_OFF + 6 - 1
        check(w1 < x0 or w0 > x1,
              f"mode {mode}: write span [0x{w0:05X},0x{w1:05X}] is DISJOINT from the X span "
              f"[0x{x0:05X},0x{x1:05X}] -- the LERP compares X UNSIGNED, so an X overwrite would "
              f"give a SILENT flat Y[0] at all speeds")
        old = rd(code, w0, 6)
        check(old == struct.pack("<3h", *FRICTION_Y_STOCK),
              f"mode {mode}: 0x{w0:05X} reads {old.hex()} = {FRICTION_Y_STOCK} before the write")
        apply(w0, old, new_bytes, f"EDIT 1.{mode}  mode {mode} friction LERP Y "
                                  f"{FRICTION_Y_STOCK} -> {FRICTION_Y_NEW}")
    check(len(attributed) == 12, f"TOTAL LEVER BYTES = {len(attributed)} (expected 12)")

    apply(CAVE_BASE, V90_CAVE + b"\xff" * (len(PAYLOAD) - len(V90_CAVE)), PAYLOAD,
          f"EDIT 2     cave payload {len(V90_CAVE)} B -> {len(PAYLOAD)} B, SEVEN rungs")
    apply(R427_ADDR, struct.pack("<h", -R427_OLD), struct.pack("<h", -R427_NEW),
          f"EDIT 3     CAN 427 MOTOR_TORQUE: gp-0x{R427_OLD:04X} -> gp-0x{R427_NEW:04X}")
    apply(R427_SAR_ADDR, R427_SAR_OLD, R427_SAR_NEW,
          "EDIT 4     CAN 427 packer scale: sar 0x3,r6 -> sar 0x4,r6 (NO-CLIP on the new source)")
    check(len(attributed) == 12 + len(PAYLOAD) + 2 + 2,
          f"TOTAL ATTRIBUTED = {len(attributed)} = 12 cal + {len(PAYLOAD)} cave + 2 repoint "
          f"+ 2 scale (1 byte differs; the halfword is written whole)")
    check(all(b == 0xFF for b in code[CAVE_BASE + len(PAYLOAD):CAVE_FREE_END]),
          f"tail 0x{CAVE_BASE + len(PAYLOAD):05X}-0x{CAVE_FREE_END:05X} still virgin 0xFF "
          f"({CAVE_FREE_END - CAVE_BASE - len(PAYLOAD)} B still free)")

    # ==============================================================================================
    # 9. POST-EDIT -- the cal lever
    # ==============================================================================================
    print("\n  [9] POST-EDIT -- read back from the BUILT image")
    for mode in TARGET_MODES:
        p, n, x, y, pad = rec_fields(code, mode)
        check(y == FRICTION_Y_NEW, f"mode {mode} rec 0x{p:05X}: Y@0x{p + REC_Y_OFF:05X} = {y}")
        check(x == FRICTION_X, f"mode {mode}: X@0x{p + REC_X_OFF:05X} = {x} UNCHANGED "
                               f"(no breakpoint moved => no phase, no new dead zone)")
        check(n == FRICTION_NPT, f"mode {mode}: n@0x{p:05X} = {n} UNCHANGED")
        check(pad == u16(base, p + REC_PAD_OFF),
              f"mode {mode}: pad@0x{p + REC_PAD_OFF:05X} = 0x{pad:04X} UNCHANGED")

    print("\n  [10] 🛑 EVERY OTHER MODE BYTE-IDENTICAL -- modes 0..33, the GIVEN 34-slot bound")
    moved = [m for m in range(FRICTION_N_MODES)
             if rd(code, before[m][0], REC_LEN) != before[m][1]]
    check(moved == list(TARGET_MODES),
          f"exactly modes {moved} moved out of {FRICTION_N_MODES} "
          f"(0..{FRICTION_N_MODES - 1}); every other 16-byte record is byte-identical")
    for mode in MANUAL_MODES:
        p, n, x, y, pad = rec_fields(code, mode)
        check(rd(code, p, REC_LEN) == before[mode][1] and y == FRICTION_Y_STOCK,
              f"🛑 MANUAL mode {mode} rec 0x{p:05X} BYTE-IDENTICAL, Y = {y} = STOCK "
              f"(the -0x10 slip did NOT happen)")
    check(rd(code, FRICTION_PTR_ARRAY, FRICTION_N_MODES * 4)
          == rd(base, FRICTION_PTR_ARRAY, FRICTION_N_MODES * 4),
          f"the pointer array itself [0x{FRICTION_PTR_ARRAY:05X},0x{FRICTION_ARRAY_END:05X}) "
          f"is byte-identical -- no pointer was rewritten")
    check(not [a for a in attributed if FRICTION_ARRAY_END <= a < FRICTION_ARRAY_END + 4],
          f"GUARD: 0x{FRICTION_ARRAY_END:05X} (the first slot PAST the array) is NOT written")
    check(rd(code, 0xCBEFC, 0xCBF60 - 0xCBEFC) == rd(base, 0xCBEFC, 0xCBF60 - 0xCBEFC),
          "GUARD: [0xCBEFC,0xCBF60) -- the slots past the array and gain_B[0] at 0xCBF5C -- "
          "byte-identical (the 'mode 68/126' phantom-diff region)")

    print("\n  [11] CARRIED-FORWARD CELLS on the BUILT image")
    assert_frozen(code, "built image")
    check(u16(code, CLAMP_ADDR) == CLAMP_VALUE,
          f"🛑 0x{CLAMP_ADDR:05X} = {u16(code, CLAMP_ADDR)} == {CLAMP_VALUE} on the OUTPUT too")
    check(rd(code, HOOK_ADDR, 4) == HOOK_BYTES, f"cave hook 0x{HOOK_ADDR:05X} byte-identical")

    # ==============================================================================================
    # 11b. ASSERTION 12 -- int32 wraparound in FUN_00036c12's `x 0x111` multiply (V91's, verbatim)
    # ==============================================================================================
    print("\n  [12] 🛑 ASSERTION 12 -- INT32 OVERFLOW in FUN_00036c12, PRE-CLAMP")
    print("       every constant re-read LE from the BUILT IMAGE (2nd method vs the Ghidra decode)")
    for a, want_v, what in ((GATE_ORI_IMM_ADDR, GATE_ORI_IMM, "ori 0xfa01,r0,r11   @0x36C22"),
                            (GATE_ADDI_IMM_ADDR, GATE_ADDI_IMM, "addi 0x7d00,r9,r14  @0x36C26"),
                            (MUL_IMM_ADDR, MUL_IMM, "movea 0x111,r0,r6   @0x36CC0")):
        g = u16(code, a)
        check(g == want_v, f"0x{a:05X} imm16 = 0x{g:04X} == 0x{want_v:04X}   {what}")
    for a, want_b, what in ((PRE_SAR_ADDR, PRE_SAR, "sar 0x6,r13   -- the >>6 before the multiply"),
                            (MUL_ADDR, MUL_BYTES,
                             "mul r13,r6,r0 -- r0 is the HIGH HALF and it is DISCARDED => the "
                             "product WRAPS, it does not saturate"),
                            (POST_SAR_ADDR, POST_SAR, "sar 0x12,r6   -- the >>18 after")):
        g = rd(code, a, len(want_b))
        check(g == want_b, f"0x{a:05X} = {g.hex()} == {want_b.hex()}   {what}")
    producer_ceiling = GATE_ORI_IMM - GATE_ADDI_IMM - 1        # x + 0x7D00 <u 0xFA01
    check(producer_ceiling == GATE_ADDI_IMM == 32000,
          f"the cmovnc GATE at 0x36C2C passes x only for x + 0x{GATE_ADDI_IMM:04X} <u "
          f"0x{GATE_ORI_IMM:04X}, i.e. |gp-0x6c2c| <= {producer_ceiling} -- DERIVED from the gate's "
          f"own two constants, inside THIS function, needing NO assumption about the producer")
    check(producer_ceiling == (0xFA0000 >> 9),
          f"and it agrees numerically with the briefed producer clamp 0xFA0000>>9 = {0xFA0000 >> 9}")
    for a, want_v in SVAR7_FALLBACKS.items():
        g = struct.unpack_from("<h", code, a)[0]
        check(g == want_v, f"sVar7 fallback 0x{a:05X} (tp+0x{a - TP:04X}) = {g} "
                           f"🛑 tp = 0x{TP:05X}, so this is 0x{a:05X} and NOT 0x{a + 0x1000:05X}")
    y_max_dosed = max(abs(y) for y in rec_fields(code, 26)[3])
    y_max_all = max([y_max_dosed] + [abs(v) for v in SVAR7_FALLBACKS.values()])
    check(y_max_all == y_max_dosed == abs(FRICTION_Y_NEW[0]),
          f"the BINDING |sVar7| is our DOSED Y[0] = {y_max_dosed}, larger than both fallbacks "
          f"{sorted(abs(v) for v in SVAR7_FALLBACKS.values())} => the worst case is V92's own cell")
    worst_product = producer_ceiling * y_max_all // 64 * MUL_IMM
    check(worst_product <= INT32_MAX,
          f"INT32 OVERFLOW IMPOSSIBLE: worst_product = {producer_ceiling} * {y_max_all} // 64 * "
          f"{MUL_IMM} = {worst_product:,} <= {INT32_MAX:,} = INT32_MAX")
    check(INT32_MAX / worst_product > 1.0,
          f"int32 headroom {INT32_MAX / worst_product:.4f}x at the producer ceiling "
          f"(anything below 1.0 aborts)")
    check(producer_ceiling * y_max_all % 64 == 0,
          f"|P|max = {producer_ceiling * y_max_all:,} is exactly divisible by 64, so the arithmetic "
          f"`sar 0x6` gives the same magnitude for a NEGATIVE product -- the floor is not a leak")
    m_overflow = INT32_MAX * 64 / (MUL_IMM * abs(FRICTION_Y_STOCK[0]) * producer_ceiling)
    m_clip = CLAMP_VALUE / ROUTE77_ENGAGED_MAX
    check(SCALE_NUM / SCALE_DEN <= m_overflow,
          f"the OVERFLOW bound is M <= {m_overflow:.4f}; V92 is at {SCALE_NUM / SCALE_DEN}")
    check(SCALE_NUM / SCALE_DEN <= m_clip,
          f"the CLIP bound is M <= {m_clip:.4f}; V92 is at {SCALE_NUM / SCALE_DEN}")
    print("    ---- ⚠ the two bounds agree at ~1.60 by COINCIDENCE, NOT by a shared mechanism: the")
    print("         clamp binds at |gp-0x6c2c| ~ 3,200, the overflow at ~34,000 -- an ORDER OF")
    print(f"         MAGNITUDE apart. No design intent is claimed. int16 k_max = "
          f"{32768 / abs(FRICTION_Y_STOCK[0]):.4f} is looser still and NON-BINDING.")
    for M in (1.0, 1.5, 1.6, 2.0, 3.0):
        t = INT32_MAX / MUL_IMM * 64 / (abs(FRICTION_Y_STOCK[0]) * M)
        flag = "SAFE" if t > producer_ceiling else "🛑 REACHABLE"
        star = "  <-- V92" if M == SCALE_NUM / SCALE_DEN else ""
        print(f"         M={M:<4} wraps at |gp-0x6c2c| = {t:10,.0f}  = {t / producer_ceiling:.4f}x "
              f"the {producer_ceiling} gate   {flag}{star}")

    # ==============================================================================================
    # 12. RE-DISASSEMBLE THE CAVE FROM THE BUILT IMAGE, against the RUNG TABLE
    # ==============================================================================================
    print("\n  [13] 🛑 RE-DISASSEMBLED FROM THE BUILT IMAGE, checked against the RUNG TABLE")
    listing = disassemble_cave(code, CAVE_BASE, len(PAYLOAD))
    check(len(listing) == len(EXPECTED) == 43,
          f"{len(listing)} instructions decoded, rung table has {len(EXPECTED)}, expected 43")
    boundaries = {off for off, *_ in listing}
    writes, refs = set(), set()
    bad_text, bad_tgt = [], []
    nbranch = 0
    for (off, addr, hx, text, kind, operand, w, r), (eoff, etext, note) in zip(listing, EXPECTED):
        if off != eoff or text.split() != etext.split():
            bad_text.append(f"+0x{off:02X} got `{text}` want `{etext}` @+0x{eoff:02X}")
        if kind == "branch":
            nbranch += 1
            if off + operand not in boundaries:
                bad_tgt.append(f"+0x{off:02X} -> +0x{off + operand:02X}")
        writes |= w
        refs |= r
        print(f"    +0x{off:02X}  0x{addr:05X}  {hx:8s}  {text:22s}  {note}")
    check(not bad_text,
          f"all {len(listing)} instructions match the RUNG TABLE offset-for-offset ({bad_text[:3]})")
    check(nbranch == 7 and not bad_tgt,
          f"{nbranch} branches, EVERY target lands on an instruction BOUNDARY ({bad_tgt[:3]})")
    check(not [1 for _, _, _, t, _, _, _, _ in listing
               if t.split()[0] in ("jarl", "jr", "callt", "div", "divh", "prepare", "op3e", "?")],
          "the cave is a STRAIGHT-LINE LEAF: no call, no loop, no divide, no float, no unknown op")
    check(writes <= {0, 6, 7},
          f"🛑 registers WRITTEN by the cave = {sorted(writes)} ⊆ {{r0, r6, r7}} -- r6 is restored by "
          f"the trailing movea, r7 is overwritten at 0x55C12 `mov 0x8,r7`, and r0 is the V850's "
          f"hardwired zero (the `addi ..,r6,r0` window compare writes it = discards, flags only)")
    check(refs <= {0, 4, 5, 6, 7, 31},
          f"🛑 every register REFERENCED = {sorted(refs)} ⊆ {{r0, gp, tp, r6, r7, lp}} -- r8 and "
          f"r10 are LIVE across the hook (0x55C20 `andi 0xf,r10,r8`) and the cave never touches them")
    stores = [(off, operand) for off, _, _, _, k, operand, _, _ in listing if k.startswith("st.")]
    check([(o, d) for o, (rb, d) in stores] == [(0x3A, -0x1514), (0x6A, -0x1511)]
          and all(rb == 4 for _, (rb, _) in stores),
          f"🛑 the cave STORES to exactly two addresses: gp-0x1514 (byte 4, ~50 flown builds) and "
          f"gp-0x1511 (byte 7, NEW). No other memory is written anywhere.")

    # ==============================================================================================
    # 13. VALUE-ANCHORED READBACK
    # ==============================================================================================
    print("\n  [14] VALUE-ANCHORED VERIFICATION, read back from the BUILT image")
    for off, disp, bit in ((0x02, 0x6BBE, "byte4 b7"), (0x0C, 0x6B62, "byte4 b6/b5"),
                           (0x1C, 0x6BDA, "byte4 b4"), (0x3E, 0x6A82, "byte7 b6"),
                           (0x4E, 0x6B26, "byte7 b7")):
        g = struct.unpack_from("<h", code, CAVE_BASE + off + 2)[0]
        check(g == -disp, f"{bit}: cave +0x{off:02X} = ld.h -0x{disp:04X}[gp],r6")
    got_bias = struct.unpack_from("<h", code, CAVE_BASE + 0x22)[0]
    got_span = -struct.unpack_from("<h", code, CAVE_BASE + 0x26)[0]
    check(got_bias == WIN_BIAS and got_span == WIN_SPAN,
          f"byte4 b4 window, read back from the BUILT image: "
          f"`addi {got_bias:#x},r6,r6` + `addi {-got_span:#x},r6,r0` + `bnh` "
          f"=> IN-WINDOW <=> {WIN_LO} <= gp-0x6bda <= {WIN_HI}, both immediates DERIVED from the "
          f"0x{LERP_Y1_TABLE:05X} knots X[0]={LERP_Y1_X[0]} X[4]={LERP_Y1_X[-1]}")
    cal_hw2 = u16(code, CAVE_BASE + 0x44)
    check(cal_hw2 & ~1 == DWELL_CAL_ADDR - TP,
          f"byte7 b6 cal: cave +0x44 hw2 = 0x{cal_hw2:04X} => tp+0x{cal_hw2 & ~1:04X} = "
          f"0x{TP + (cal_hw2 & ~1):05X} = {u16(code, TP + (cal_hw2 & ~1))} "
          f"(ld.hu sets hw2 bit 0 as a MARKER; the displacement is the masked value)")
    thr = code[CAVE_BASE + 0x58] & 0x1F
    check(code[CAVE_BASE + 0x58] & 0xE0 == 0x60 and thr + 1 == DOSE_T,
          f"DOSE-IN-FORCE threshold byte 0x{CAVE_BASE + 0x58:05X} = "
          f"0x{code[CAVE_BASE + 0x58]:02x} => `cmp 0x{thr:x},r6` + `bnh` => trips at "
          f"|gp-0x6b26| >= {thr + 1} = T ({DOSE_T}); a single byte to move on the next build")
    g427 = struct.unpack_from("<h", code, R427_ADDR)[0]
    check(g427 == -R427_NEW,
          f"427: 0x{R427_ADDR - 2:05X} = {rd(code, R427_ADDR - 2, 4).hex()} = "
          f"ld.h -0x{R427_NEW:04X}[gp],r6")

    # ---- the 427 NO-CLIP property, asserted in BOTH directions --------------------------------
    new_shift = code[R427_SAR_ADDR] & 0x1F
    check(code[R427_SAR_ADDR] & 0xE0 == 0xA0 and new_shift == 4
          and rd(code, R427_SAR_ADDR, 2) == R427_SAR_NEW,
          f"0x{R427_SAR_ADDR:05X} = {rd(code, R427_SAR_ADDR, 2).hex()} => `sar 0x{new_shift:x},r6` "
          f"=> 427 = clamp(|gp-0x{R427_NEW:04X}| * {R427_MUL} >> {new_shift}, 0, 0x{R427_FIELD_MAX:X})")
    packed_max = (R427_LANE_WINDOW * R427_MUL) >> new_shift
    check(packed_max <= R427_FIELD_MAX,
          f"🛑 NO-CLIP: at the lane's FULL +/-{R427_LANE_WINDOW} window the packed value is "
          f"{R427_LANE_WINDOW}*{R427_MUL}>>{new_shift} = {packed_max} <= {R427_FIELD_MAX} "
          f"=> the 427 channel CANNOT saturate anywhere gp-0x{R427_NEW:04X} can go "
          f"({100 * packed_max / R427_FIELD_MAX:.1f} % of the field, ~"
          f"{packed_max.bit_length()} effective bits)")
    old_shift = R427_SAR_OLD[0] & 0x1F
    would_clip = min(n for n in range(1 << 16) if (n * R427_MUL) >> old_shift > R427_FIELD_MAX)
    check(((R427_LANE_WINDOW * R427_MUL) >> old_shift) > R427_FIELD_MAX,
          f"🛑 AND THE FIX IS NECESSARY, not decorative: at Honda's `sar 0x{old_shift:x}` the same "
          f"window packs to {(R427_LANE_WINDOW * R427_MUL) >> old_shift} > {R427_FIELD_MAX} and the "
          f"field would go flat from |gp-0x{R427_NEW:04X}| >= {would_clip} -- the top "
          f"{100 * (R427_LANE_WINDOW - would_clip) / R427_LANE_WINDOW:.0f} % of the range")
    check(((511 * R427_MUL) >> old_shift) == 319,
          f"and the reason V90 never needed it: its source gp-0x6b26 was clamped to +/-511, so "
          f"511*{R427_MUL}>>{old_shift} = 319 of {R427_FIELD_MAX} -- V90 measured 0 clipped frames "
          f"of 62,180, the property this fix preserves for the new source")

    # ==============================================================================================
    # 14. CRC -- DERIVED IN CODE
    # ==============================================================================================
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    print(f"\n  [15] CRC -- {len(blocks)} block(s) move, trailer set DERIVED from the image's own "
          f"self-describing 50-block map")
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in touched),
              f"no edit landed on the trailer at 0x{blk[1]:06X}")
        old_crc = struct.unpack_from("<I", code, blk[1])[0]
        new_crc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new_crc)
        owners = [a for a in touched if blk[0] <= a < blk[1]]
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old_crc:08X} -> "
              f"0x{new_crc:08X}   owns {len(owners)} of {len(touched)} touched byte(s)")
    derived = {blk[1] for blk in blocks}
    check(derived == {0xC4FFC, 0xD7FFC},
          f"DERIVED trailer set {sorted(hex(t) for t in derived)} == {{0xc4ffc, 0xd7ffc}} -- the "
          f"cave and the 427 repoint share the MAIN block [0x013000,0x0C4FFC); the two cal writes "
          f"live in [0xD7000,0xD7FFC). Derived, then asserted; never hard-coded")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    check(0x055FFC not in crc_only,
          "🛑 0x055FFC is LIVE CODE (`6477b8f0`), NOT a CRC trailer -- writing there would "
          "silently overwrite 4 bytes of executable code and the recompute would HIDE it")
    check(walk_all_blocks(bytes(code)) == 0,
          "built image CRC chain 50/50 (NECESSARY, NOT SUFFICIENT -- see [17])")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "the CRC-SKIPPED block [0xC5000,0xC5FFC) is byte-identical to the base (V40's brick)")
    check(not [a for a in attributed if 0xC5000 <= a < 0xC5FFC],
          "no edit landed inside [0xC5000,0xC5FFC) -- the block the bootloader SKIPS")
    check(not [a for a in attributed if a < START or a >= END],
          f"every edit lies inside [0x{START:X},0x{END:X})")
    check(bytes(code[:START]) == bytes(base[:START]),
          f"nothing below 0x{START:X} changed (the bootloader region)")

    # ==============================================================================================
    # 15. ZERO-UNATTRIBUTED FULL BYTE DIFF -- the INDEPENDENT check
    # ==============================================================================================
    runs, i = [], START
    while i < END:
        if code[i] != base[i]:
            j = i
            while j < END and code[j] != base[j]:
                j += 1
            runs.append((i, j - 1))
            i = j
        else:
            i += 1
    def attribute(d):
        return by_addr.get(d, "CRC trailer" if d in crc_only else None)
    stray = [d for a, b in runs for d in range(a, b + 1) if attribute(d) is None]
    total = sum(b - a + 1 for a, b in runs)
    print("\n" + "=" * 102)
    print("  [16] 🛑 FULL BYTE DIFF: BUILT V92 vs the FLOWN V90 -- over [0x13000, 0x100000)")
    print(f"       {len(runs)} differing run(s), {total} byte(s) total")
    for a, b in runs:
        print(f"       0x{a:05X}-0x{b:05X} {b - a + 1:4d}  {attribute(a)}")
    check(not stray, f"ZERO unattributed bytes vs V90 (stray = {[hex(x) for x in stray[:16]]})")
    print(f"       reconciliation: 12 cal + 2 repoint + 2 scale + {len(PAYLOAD)} cave span + 8 CRC "
          f"= {12 + 2 + 2 + len(PAYLOAD) + 8} attributed; {total} actually DIFFER (the cave payload "
          f"shares {len(PAYLOAD) + 12 + 2 + 2 + 8 - total} byte(s) with V90's, and the sar halfword "
          f"differs in 1 byte of 2)")
    rt = bytearray(code)
    for a in attributed | crc_only:
        rt[a] = base[a]
    check(hashlib.sha256(bytes(rt)).hexdigest() == base_sha,
          "restoring the attributed set reproduces the flown V90 BIT-FOR-BIT")

    # ==============================================================================================
    # 16. CROSS-CHECK AGAINST THE FROZEN V91 ARTEFACT
    # ==============================================================================================
    print("\n  [17] 🛑 CROSS-CHECK vs the FROZEN V91 image -- the cal half must be IDENTICAL")
    v91p = Path(V91_BIN)
    if v91p.exists():
        v91 = v91p.read_bytes()
        check(hashlib.sha256(v91).hexdigest() == V91_SHA,
              f"V91 image on disk hashes to {V91_SHA} (read-only; V92 does not touch it)")
        check(bytes(code[0xD7000:0xD8000]) == v91[0xD7000:0xD8000],
              "🛑 the WHOLE block [0xD7000,0xD8000) -- both dosed Y rows AND the recomputed "
              "0xD7FFC trailer -- is BYTE-IDENTICAL to V91's. An INDEPENDENT confirmation that "
              "V92's cal half is V91's cal half, computed twice by two scripts")
        for mode in TARGET_MODES:
            check(rec_fields(code, mode)[3] == rec_fields(v91, mode)[3],
                  f"mode {mode}: V92 Y == V91 Y == {FRICTION_Y_NEW}")
        allowed = (set(range(CAVE_BASE, CAVE_BASE + len(PAYLOAD)))
                   | {R427_ADDR, R427_ADDR + 1, R427_SAR_ADDR, R427_SAR_ADDR + 1}
                   | set(range(0xC4FFC, 0xC5000)))
        d = [i for i in range(START, END) if v91[i] != code[i]]
        check(all(i in allowed for i in d),
              f"V92 vs V91 differs ONLY in the cave span, the 427 source halfword, the 427 scale "
              f"halfword and the 0xC4FFC trailer ({len(d)} bytes, stray "
              f"{[hex(i) for i in d if i not in allowed][:8]}) => V92 = V91 + INSTRUMENT, "
              f"and the calibration halves are provably identical")
    else:
        print(f"    ---- {os.path.basename(V91_BIN)}: not on disk, cross-check skipped")

    # ==============================================================================================
    # 17. THE DELIVERED SURFACE, and the V74/V75 comparison, read from the IMAGES
    # ==============================================================================================
    print("\n  [18] THE DELIVERED SURFACE -- LERP mirrored in integer Python, knots read from the "
          "BUILT image")
    y26 = rec_fields(code, 26)[3]
    y24 = rec_fields(code, 24)[3]
    print("       speed          Y  MANUAL (24/25)     Y ENGAGED (26/27)     ratio    |gp-0x6b26| "
          "at the route-77 envelope")
    for kmh in (0, 5, 10, 20, 40, 60, 90, 120):
        sc = kmh * SPEED_COUNTS_PER_KMH
        a, b = lerp_y(y24, sc), lerp_y(y26, sc)
        env = ROUTE77_ENGAGED_MAX * b / a if a else 0.0
        print(f"       {kmh:3d} km/h ({sc:5d} ct)   {a:8d}          {b:8d}       "
              f"{b / a:5.3f}    {env:6.1f} of {CLAMP_VALUE}")
    check(all(a * SCALE_NUM == b * SCALE_DEN for a, b in zip(y24, y26)),
          f"AT THE KNOTS -- the load-bearing claim -- the engaged row is EXACTLY 1.5x the manual "
          f"row: {y24} x 3/2 == {y26}, no rounding anywhere")
    worst = max(abs(lerp_y(y26, k * SPEED_COUNTS_PER_KMH) * SCALE_DEN
                    - lerp_y(y24, k * SPEED_COUNTS_PER_KMH) * SCALE_NUM)
                for k in range(0, 200))
    check(worst <= SCALE_DEN,
          f"BETWEEN the knots the ratio holds to {worst / SCALE_DEN:.1f} count over 0..199 km/h "
          f"-- and that residue is this MIRROR's own floor division, not the lever "
          f"=> a pure scalar multiply: no phase, no sign change, no breakpoint moved")
    check(all(lerp_y(y26, k * SPEED_COUNTS_PER_KMH) < 0 for k in range(0, 200)),
          "the engaged surface is NEGATIVE at every speed 0..199 km/h => gp-0x6b26 keeps the "
          "OPPOSITE sign to gp-0x6c2c: the term stays DISSIPATIVE, x1.5 cannot flip it")
    check(max(abs(lerp_y(y26, k * SPEED_COUNTS_PER_KMH)) for k in range(0, 200))
          == abs(FRICTION_Y_NEW[0]),
          f"the engaged surface peaks at |{FRICTION_Y_NEW[0]}| (at rest) and decays with speed "
          f"-- the shape is Honda's, only the scale moved")

    print("\n  [19] 🛑 V74 / V75 -- the SAME LEVER at the SAME DOSE, read from THEIR images")
    for name in V74_V75_IMAGES:
        p = plain_image_path(name)
        if not p.exists():
            print(f"    ---- {name}: not on disk, skipped")
            continue
        img = p.read_bytes()
        diff = [m for m in range(FRICTION_N_MODES)
                if struct.unpack_from("<3h", img, rec_addr(img, m) + REC_Y_OFF) != FRICTION_Y_STOCK]
        rows = {struct.unpack_from("<3h", img, rec_addr(img, m) + REC_Y_OFF) for m in diff}
        check(tuple(diff) == V74_V75_MODES and rows == {FRICTION_Y_NEW},
              f"{name[:46]}: {len(diff)} records at {FRICTION_Y_NEW}, modes {diff}")
        check(u16(img, CLAMP_ADDR) == 850,
              f"{name[:46]}: 0x{CLAMP_ADDR:05X} = {u16(img, CLAMP_ADDR)} -- the 850 interlock "
              f"that V92 does NOT carry")
    check(set(TARGET_MODES) < set(V74_V75_MODES),
          f"V92's {set(TARGET_MODES)} is a STRICT 2-of-{len(V74_V75_MODES)} SUBSET of V74/V75's "
          f"records => a DELIBERATE NARROWING, not a reproduction")

    stock_p = Path(STOCK_BIN)
    if stock_p.exists():
        stock = stock_p.read_bytes()
        same = [m for m in range(FRICTION_N_MODES)
                if rd(stock, rec_addr(stock, m), REC_LEN) == before[m][1]]
        check(len(same) == FRICTION_N_MODES,
              f"the V90 base is BYTE-STOCK on all {FRICTION_N_MODES} friction records "
              f"=> V92's 12 bytes are the FIRST movement of this lever since V75")

    # ==============================================================================================
    # 18. .rwd
    # ==============================================================================================
    print("\n  [20] .rwd ENCODE + READBACK")
    source_rwd = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 OK")
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V92 output")
    back = parse_x31(rwd)
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "the decoded .rwd payload is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC chain 50/50")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V92_WRITE=rwd to cut.")
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

            print("\n  [21] 🛑 FROM-DISK -- the SHIPPED .rwd re-read, re-hashed, decoded, re-asserted")
            shipped = Path(OUT).read_bytes()
            check(hashlib.sha256(shipped).hexdigest() == rwd_sha,
                  f"shipped .rwd re-read from disk, sha256 {rwd_sha}")
            FF.assert_x31_checksum(shipped, "V92 shipped")
            sd = bytearray(base)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(dec_tbl)
            check(bytes(sd) == bytes(code), "the SHIPPED .rwd decodes to the built image")
            check(walk_all_blocks(bytes(sd)) == 0, "shipped-from-disk CRC chain 50/50")
            assert_frozen(sd, "shipped .rwd from disk")
            for mode in TARGET_MODES:
                check(rec_fields(sd, mode)[3] == FRICTION_Y_NEW,
                      f"shipped .rwd: mode {mode} Y = {FRICTION_Y_NEW}")
                check(rec_fields(sd, mode)[2] == FRICTION_X,
                      f"shipped .rwd: mode {mode} X = {FRICTION_X} UNCHANGED")
            for mode in MANUAL_MODES:
                check(rec_fields(sd, mode)[3] == FRICTION_Y_STOCK,
                      f"shipped .rwd: MANUAL mode {mode} Y = {FRICTION_Y_STOCK} = STOCK")
            check(u16(sd, CLAMP_ADDR) == CLAMP_VALUE,
                  f"shipped .rwd: 0x{CLAMP_ADDR:05X} = {CLAMP_VALUE}")
            check(rd(sd, CAVE_BASE, len(PAYLOAD)) == PAYLOAD,
                  f"shipped .rwd: the {len(PAYLOAD)}-byte cave payload is byte-identical")
            check(struct.unpack_from("<h", sd, R427_ADDR)[0] == -R427_NEW,
                  f"shipped .rwd: the CAN 427 repoint reads gp-0x{R427_NEW:04X}")
            check(rd(sd, R427_SAR_ADDR, 2) == R427_SAR_NEW,
                  f"shipped .rwd: 0x{R427_SAR_ADDR:05X} = {R427_SAR_NEW.hex()} = `sar 0x4,r6` "
                  f"=> the 427 no-clip fix is in the shipped artefact")
            check(rd(sd, HOOK_ADDR, 4) == HOOK_BYTES, "shipped .rwd: the cave hook is unchanged")
            sd_listing = disassemble_cave(sd, CAVE_BASE, len(PAYLOAD))
            check([(row[0], row[3].split()) for row in sd_listing]
                  == [(e[0], e[1].split()) for e in EXPECTED],
                  f"shipped .rwd: the cave RE-DISASSEMBLES to the same {len(EXPECTED)}-instruction "
                  f"rung table, offset for offset")
            on_disk = Path(BIN_OUT).read_bytes()
            check(hashlib.sha256(on_disk).hexdigest() == img_sha and on_disk == bytes(code),
                  f"the plain image re-read from disk hashes to {img_sha}")

            # ------------------------------------------------------------------------------------
            # 🛑 EXACTLY ONE V92 ARTEFACT OF EACH KIND ON DISK. The rule exists because a
            # plausibly-named flashable .rwd for a superseded build is this kit's own recorded
            # hazard -- and a SUPERSEDED-DO-NOT-FLASH-* rename is a HOLDING measure, not the end
            # state, so this scan deliberately catches those too.
            # ------------------------------------------------------------------------------------
            print("\n  [22] 🛑 ARTEFACT UNIQUENESS -- every V92-matching file in both directories")
            stray_rwd = sorted(p for p in Path(RWD_DIR).iterdir()
                               if p.is_file() and "v92" in p.name.lower())
            stray_img = sorted(p for p in Path(ANALYSIS_ROOT).iterdir()
                               if p.is_file() and "v92" in p.name.lower())
            for p in stray_rwd + stray_img:
                mark = "  <-- THIS BUILD" if str(p) in (OUT, BIN_OUT) else "  🛑 STRAY"
                print(f"       {p.name}{mark}")
            check([str(p) for p in stray_rwd] == [OUT],
                  f"exactly ONE V92 .rwd in {RWD_DIR}: {os.path.basename(OUT)} "
                  f"(found {len(stray_rwd)})")
            check([str(p) for p in stray_img] == [BIN_OUT],
                  f"exactly ONE V92 image in {ANALYSIS_ROOT}: {os.path.basename(BIN_OUT)} "
                  f"(found {len(stray_img)})")
            v91_img = Path(V91_BIN)
            if v91_img.exists():
                check(hashlib.sha256(v91_img.read_bytes()).hexdigest() == V91_SHA,
                      "🛑 V91's image is STILL byte-identical after the V92 cut -- untouched")

    print("\n" + "=" * 102)
    print(f"  V92 [{VARIANT_TOKEN}]     {_checks[1]}/{_checks[0]} assertions PASSED")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  🛑 12 cal bytes (V91's, identical) + {len(PAYLOAD)} cave bytes + 2 repoint bytes")
    print("     + 1 packer-scale byte (427 NO-CLIP) + 8 CRC bytes.")
    print("  🛑 SAME LEVER, SAME DOSE as the hard-faulted V74/V75; only 0xC407E differs, and that")
    print("     separation is STRUCTURAL -- no flight has ever tested it. The dose is 5-69x below")
    print("     the measurable floor, so the OPERATOR'S OWN REPORT is the primary endpoint.")
    print("  🛑 IDENTITY: any single frame with 0x14A byte7 bits[7:6] != 0 proves V92 flew.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    assert len(PAYLOAD) == 116 and len(V90_CAVE) == 74
    build()
