#!/usr/bin/env python3
"""decode_v74_probe.py -- read V74's probe: the damper's OWN OUTPUT and the assist-chain STATE.

WHAT V74 IS -- so a reader of this file cannot mistake the artefact
--------------------------------------------------------------------
V73's probe read the damper's mode selector `*(byte)(gp+0x63fd)` on-car over 104,061 frames. The
answer was **not 10**. The car is config row **11 = `TVCA4`**, running mode **24 disengaged / 26
ENGAGED**. Every mode-indexed lever this kit has ever flown -- V44's, V72's LEVER B, V73's EDIT 1 and
EDIT 2 -- addressed modes 0-5/10/11/12/14 and was therefore **INERT BY CONSTRUCTION**.

**V74 writes the ENGAGED COLUMN (`e014`/`e015`) OF ALL 16 ROWS** -- the 13 modes
{2,3,5,11,14,15,17,23,26,27,29,32,33}. The disengaged column {0,1,4,10,12,13,16,22,24,25,28,30,31} is
**disjoint** and left byte-stock, so manual and parking steering are untouched.

  LEVER E'  **open BOTH dead zones** (the core). `dose = (FactorC x FactorE) >> 10`. FactorC is
            speed-indexed and dead below 35 km/h; FactorE is rate-indexed and dead below 60 counts;
            **the symptom sits under BOTH**, at a measured `|gp-0x6ac0|` of 99 counts [94, 113].
            Per engaged mode:  FactorC `Y[0] := Y[2]` · FactorE `X[0] := 12` · FactorE `Y[1] := Y[2]`.
            On the live mode 26 that is 0 -> **50 counts** at rate 99 (stock 0; FactorC alone 6), and 66 at
            the 6-9 Hz arm's rate 127. ★ At the stock X[0], FactorE is EXACTLY 0 in **32.3% of
            in-burst frames** and **98.72%** of engaged-highway frames sit below the breakpoint --
            which is why the damper has always produced essentially nothing, and why V72's `bit4`
            null needs no exotic explanation.
            ★ **The OPPOSITE of V72's error, not a larger version.** V72 raised FactorE's *floor*
            (Y[0] 0 -> 927), giving a CONSTANT -- a near-bang-bang relay. Here `Y[0] = 0` is
            PRESERVED, so magnitude still vanishes with rate: no discontinuity, no chatter mechanism.
  LEVER D'  the friction lane x1.5 on the same 13 modes (`0xCBE74[mode*4] + 8`).
  LEVER D'b `0xC407E` = 850. **NOT mode-indexed, and V73 already flew it LIVE** (~80% of burst
            frames, no band change) -- V74 asserts it and does not re-write it. 🛑 Hard cap 1000,
            never 1024: the aggregator's +/-0x400 window is a ZERO-REJECT.
  UNTOUCHED both `sar` sites at STOCK (**reintroducing V62's `a9` causes grind #2, and the fix is an
            ABSENCE**), the whole r24/r26 rate lane, V72's r26 cut (`0xC6A68`/`0xC6A7C` flat 512),
            the gate, both scalar arms, LEVER C, the carried 0x454FE.

THE PAYLOAD -- CAN 0x14A byte4, bits 7:3
-----------------------------------------
    bit7      = (*(short *)(gp - 0x6BD0) != 0)   ★★★★ **THE POSITIVE CONTROL.** The damper's OWN
                                                 output. It goes non-zero exactly when LEVER E'
                                                 delivers. The last five probes had no such control.
    bits 6:3  = (*(byte *)(gp - 0x67FA)) & 0xF   ★★ the assist-chain STATE.
    bits 2:0  = stock STEER_SENSOR_STATUS         preserved, untouched.

★★ LIVENESS IS **STRUCTURAL**, WHICH IS NEW. `gp-0x67FA`'s complete value set is
{1, 3, 4, 5, 6, 7, 8, 9, 10, 11} -- all 33 `st.b` writers store literals, re-verified by the builder
on the image itself. **0 is impossible and 4 bits are lossless**, so `bits 6:3 == 0` for a whole
drive can ONLY mean the cave never fired. V64 and V68 each burned a build on a null that could not be
told apart from "the gate never armed"; this payload cannot have that ambiguity.
🛑 **READ THE LIVENESS FIRST.** If `bits 6:3` is constant 0, nothing else in the log is interpretable.

⚠ WEAK BUILD IDENTITY, STATED: 32 payload values are legal and there is no structural invariant among
them, so the value SET alone proves only that "some V74-shaped cave ran". **The .rwd FILENAME is the
pre-drive discriminator and CAVE_HEX below is the post-hoc one.**

HOW TO READ THE ANSWER
-----------------------
  bit7 duty > 0, concentrated in ENGAGED creep frames   ⇒ LEVER E' IS DELIVERING. Score the 6-9 Hz
                                                          ratchet and grind #1 against it.
  bit7 identically 0 while bits 6:3 vary                ⇒ the cave ran, the damper is STILL dead.
                                                          🛑 That is a NEW fact, not a repeat of
                                                          V72's null: V72 asked `|x| >= 64` on an
                                                          INERT mode; this asks `!= 0` on the LIVE
                                                          one. It would mean the mode-26 records are
                                                          not what FUN_00034350 reads.
  bits 6:3 constant 0                                   ⇒ VOID. The cave did not fire.

📋 PRE-REGISTERED (from STATE.md): success = 6-9 Hz duty AND duration fall with f0 unchanged
(|df0| <= 0.3 Hz). **ABORT the lever if 5x f0 prominence > 3.0** (baseline 0.80) -- that is the relay
generating a new cycle. Also abort-worthy: duty ratio > 1.2 *with* prominence ratio > 1.3, or
|df0| > 0.5 Hz.

Usage:  python decode_v74_probe.py <rlog-or-segment-dir> [...]
"""
import os
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from decode_v67_gate import collect                                        # noqa: E402
from decode_v69_ratchet import MIN_SAMPLES                                 # noqa: E402

# 🛑 THE MECHANICAL LINK TO THE IMAGE. build_v74_tva.assert_decoder_matches() FAILS THE BUILD if this
# hex does not equal the cave it just emitted, so this decoder cannot silently describe a different
# build. Do not hand-edit it.
CAVE_HEX = "003a24373094e031b205203e100084370798c6360f000639c33a8437edeac636070007314437ecea2436e8ea7f0000000000000000000000000000000000000000000000"  # noqa: E501
#
#   0xC4B34  003a      mov   0x0,r7           r7 = 0                     (real instance @0x34114)
#   0xC4B36  24373094  ld.h  -0x6bd0[gp],r6   ★★★★ THE DAMPER'S OWN OUTPUT. **SIGNED** -- op field
#                                             0x39. Its one-bit twin `st.h` (0x3B) is a REAL
#                                             instruction at 0x34730 writing this very cell, so the
#                                             wrong bit would have the cave OVERWRITE the damper.
#   0xC4B3A  e031      cmp   r0,r6            🛑 sets Z iff the output is exactly 0 (real @0x3401E)
#   0xC4B3C  b205      be    +6               reads the cmp's OWN flags -- NOTHING sits between them.
#                                             +6, not +4: it skips a FOUR-byte instruction, and +4
#                                             would land INSIDE the movea. (real `be` @0x34CFA)
#   0xC4B3E  203e1000  movea 0x10,r0,r7       bit7 = (gp-0x6bd0 != 0). 0x10 is OUTSIDE `add imm5`'s
#                                             signed -16..15 range, which is why it is a movea --
#                                             the same reason V72 and V73 folded their own bit7 in.
#   0xC4B42  84370798  ld.bu -0x67fa[gp],r6   ★★ THE STATE. Byte cell; NEGATIVE displacement; op
#                                             field 0x3C because -0x67FA = 0x9806 is EVEN.
#                                             Byte-identical to the real `ld.bu -0x67fa,gp,r6`
#                                             @0x18C7C. The st.b twin @0x19862 is 44370698 -- and
#                                             this cell is LOCKSTEP-checked against gp-0x4c39, so a
#                                             stray write escalates.
#   0xC4B46  c6360f00  andi  0xf,r6,r6        4 bits (real instance @0x45EBC)
#   0xC4B4A  0639      or    r6,r7            r7 |= state.  🛑 **NOT** `or r7,r6` (0731) -- SAME
#                                             opcode, register fields SWAPPED, and both forms are
#                                             real instructions in this image, so a byte pin alone
#                                             cannot catch the swap. The wrong one would OR the state
#                                             into the SCRATCH register and every frame would read
#                                             "state 0" -- which would look exactly like a VOID cave.
#   0xC4B4C  c33a      shl   0x3,r7           the 5-bit field -> bits 7:3 (Honda's own @0x4FB82)
#   0xC4B4E  8437edea  ld.bu -0x1514[gp],r6   CAN-330 payload byte4 (r6 is free: the field is in r7)
#   0xC4B52  c6360700  andi  0x7,r6,r6        preserve live STEER_SENSOR_STATUS bits 2:0
#   0xC4B56  0731      or    r7,r6            the MERGE -- this one IS `or r7,r6`
#   0xC4B58  4437ecea  st.b  r6,-0x1514[gp]   THE ONLY STORE. GATE 1 is vacuous.
#   0xC4B5C  2436e8ea  movea -0x1518,gp,r6    the displaced hook instruction, re-executed LAST
#   0xC4B60  7f00      jmp   [lp]             -> 0x55C12, which is `mov 0x8,r7` (083a) ⇒ r7 is
#                                             PROVABLY DEAD across the hook
#   0xC4B62  00 x 22   nop                    padding, AFTER the return ⇒ unreachable

BIT_DAMP_NZ = 0x80            # bit7  (gp-0x6BD0 != 0)   ★ THE POSITIVE CONTROL
STATE_FIELD = 0x78            # bits 6:3  (gp-0x67FA) & 0xF
STATE_SHIFT = 3
STATE_MASK = 0xF
PROBE_MASK = 0xF8
STATUS_MASK = 0x07            # STEER_SENSOR_STATUS, preserved

STATE_DISP = 0x67FA           # 🛑 a NEGATIVE gp displacement. gp-0x67FA.
DAMP_DISP = 0x6BD0            # the base-assist damper output -- SIGNED
STATE_VALUE_SET = (1, 3, 4, 5, 6, 7, 8, 9, 10, 11)     # ★ 0 IMPOSSIBLE ⇒ liveness is STRUCTURAL
STATE_SHADOW_DISP = 0x4C39    # 🛑 gp-0x67FA is LOCKSTEP-SHADOWED here. Every writer reads BOTH,
#                               compares them, and stores only on agreement -- otherwise it calls
#                               FUN_0006b9fa(gp-0x4c39). The probe only READS, so blast radius is
#                               zero. This is also HOW the value set was pinned: 30 of the 33 writers
#                               store an inline literal, and the 3 that store a register were read in
#                               Ghidra -- 0x19862 -> 3, 0x19D24 -> 6, and 0x1A0BA re-stores the
#                               cell's OWN value during the shadow compare.
#                               ⇒ 🛑 **0 IS UNREACHABLE, so a CONSTANT `bits 6:3` field means THE
#                               CAVE NEVER FIRED. It is not a null result -- it is a VOID drive.**
# ⊕ Modes 2/3 have a DIFFERENT FactorE record entirely: X = [70,450,1000,4000], Y = [115,115,177,253]
#   -- stock X[0] is 70, not 60, and Y[0] is non-zero. They are the only engaged modes whose dose is
#   unchanged by the X[0] 6->12 revision (168 either way). Not an error.
ROLE_TABLE = 0xC4124          # asserted unchanged by the builder; a role 6/7 voids every lever

FACTOR_C_PTRS, FACTOR_E_PTRS = 0xC9E9C, 0xC9F84
FRICTION_PTR_ARRAY = 0xCBE74
ENGAGED_MODES = (2, 3, 5, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33)
DISENGAGED_MODES = (0, 1, 4, 10, 12, 13, 16, 22, 24, 25, 28, 30, 31)
LIVE_MODE = 26                # row 11 TVCA4, e014 -- V73's on-car probe, not an inference
MANUAL_MODE = 24
BURST_RATE = 99               # measured |gp-0x6ac0| p50 IN-BURST, [94.2, 113.0]
LIVE_DOSE = 50                # counts at BURST_RATE on mode 26, against a requirement of ~43 [30,60]
LIVE_DOSE_69HZ = 66           # at the 6-9 Hz arm's p50 rate of 127
BURST_RATE_69HZ = 127         # ⚠ 3 episodes, unpowered
OUT_OF_BURST_RATE = 9         # 🛑 NOT the sizing input -- an earlier pricing mis-took it for one
CREEP_MAX_MS = 4.0            # the ratchet and grind #1 are creep symptoms (1-4 m/s)

# 🛑 ONE LINE, deliberately. build_v74_tva.py asserts this exact basename appears in this file;
# splitting it across a concatenation makes the substring vanish and the check silently harder.
RWD_NAME = "39990-TVA,A160-V74-V73BASE-ENGCOLS13-x12-addonly-FactorCY0eqY2-FactorEX0to12-Y1eqY2-frictionx1p5-C407E850-probe-67fa-6bd0nz-0x13000-0x100000.rwd"  # noqa: E501


def identify(b4):
    """Is this a V74 payload at all? 🛑 The FILENAME is the pre-drive discriminator; this is the
    post-hoc one, and it can only ever say 'consistent with', never 'is'."""
    vals = sorted({int(v) & PROBE_MASK for v in b4})
    illegal = [v for v in vals if v & ~PROBE_MASK]
    if illegal:
        print(f"  🛑 payload values {illegal} carry bits outside 7:3 -- NOT a V74 log.")
        return False
    states = {(v & STATE_FIELD) >> STATE_SHIFT for v in vals}
    if states == {0}:
        print("  🛑🛑 VOID: bits 6:3 are IDENTICALLY 0 across the whole drive. gp-0x67FA can never")
        print("     hold 0 (value set {1,3..11}, all 33 writers verified), so THE CAVE DID NOT FIRE.")
        print("     Nothing else in this log is interpretable. Check the flashed .rwd is")
        print(f"     {RWD_NAME}")
        return False
    unknown = states - set(STATE_VALUE_SET)
    if unknown:
        print(f"  ⚠ states {sorted(unknown)} are outside the verified value set "
              f"{list(STATE_VALUE_SET)} -- either the cell moved or the reading is wrong.")
    print(f"  ✅ consistent with V74: states seen {sorted(states)}, "
          f"bit7 duty {100.0 * np.mean((b4 & BIT_DAMP_NZ) != 0):.3f}%")
    return True


def report(b4, engaged, speed_ms):
    """bit7 (the damper) and bits 6:3 (the state), sliced by engagement and by creep."""
    damp = (b4 & BIT_DAMP_NZ) != 0
    state = (b4 & STATE_FIELD) >> STATE_SHIFT
    counts = Counter(int(s) for s in state)
    print("\n  STATE (bits 6:3) -- gp-0x67FA:")
    for s, n in counts.most_common():
        print(f"     {s:3d}  {n:8d} frames  {100.0 * n / len(b4):6.2f}%"
              f"{'   ⚠ OUTSIDE the verified set' if s not in STATE_VALUE_SET else ''}")

    print("\n  ★★ bit7 -- THE POSITIVE CONTROL (gp-0x6BD0 != 0, the damper's OWN output):")
    slices = [("all frames", np.ones(len(b4), dtype=bool))]
    if engaged is not None and len(engaged) == len(b4):
        slices += [("ENGAGED", engaged), ("manual", ~engaged)]
        if speed_ms is not None and len(speed_ms) == len(b4):
            v = np.asarray(speed_ms, dtype=float)
            slices += [("ENGAGED creep (<= 4 m/s)", engaged & (v <= CREEP_MAX_MS)),
                       ("ENGAGED cruise (> 4 m/s)", engaged & (v > CREEP_MAX_MS))]
    for lab, m in slices:
        n = int(m.sum())
        if n < MIN_SAMPLES:
            print(f"     {lab:26s}: only {n} frames (< {MIN_SAMPLES}) -- not reportable")
            continue
        print(f"     {lab:26s}: {100.0 * damp[m].mean():7.3f}% of {n} frames")

    print("\n  THE VERDICT THIS DRIVE LICENSES:")
    duty = float(damp.mean())
    if duty == 0.0:
        print("     🛑 bit7 is IDENTICALLY 0 while the state field varies ⇒ the cave RAN and the")
        print("       damper output is STILL exactly zero. **This is a NEW fact, not a repeat of")
        print("       V72's null**: V72 asked `|x| >= 64` on modes it now turns out the car never")
        print(f"       read; this asks `!= 0` on the LIVE mode {LIVE_MODE}, whose records V74 dosed")
        print(f"       to {LIVE_DOSE} counts at the measured burst rate {BURST_RATE}.")
        print("       ⇒ FUN_00034350 is not reading the mode-26 records, or a factor upstream of")
        print("       FactorC/E is zero. Do NOT score LEVER E' as falsified -- score it as ZERO")
        print("       EXPOSURE, exactly as V73's Lever E turned out to be.")
    else:
        print(f"     ✅ bit7 fires on {100.0 * duty:.3f}% of frames ⇒ **LEVER E' IS DELIVERING** and")
        print("       the damper is in force for the first time in this kit. Score the 6-9 Hz")
        print("       ratchet and grind #1 against it, ENGAGED frames only.")
        print("     🛑 ABORT CHECK, pre-registered: if 5x f0 prominence > 3.0 (baseline 0.80) the")
        print("       relay is generating a new cycle -- pull the lever regardless of duty.")
    print(f"     ⊕ LEVER D' (friction x1.5) rode the same 13 engaged modes, so it is LIVE exactly")
    print("       when bit7's mode is. 0xC407E = 850 is NOT mode-indexed and was already live on")
    print("       V73, where it produced no band change ⇒ do not re-credit it here.")
    return counts


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    for target in argv[1:]:
        print("=" * 100)
        print(f"  {target}")
        # 🛑 GLUE: `collect()` takes a LIST of paths and returns `b4` / `lat` / `v`. Passing the bare
        # string makes it iterate the path's CHARACTERS.
        data = collect([target])
        b4 = np.asarray(data["b4"], dtype=np.uint8)
        if not len(b4):
            print("  🛑 no 0x14A frames found.")
            continue
        engaged = np.asarray(data["lat"], dtype=bool) if data.get("has_lat") else None
        speed_ms = data.get("v")
        print(f"  frames: {len(b4)}")
        print(f"  payload histogram: {dict(Counter(hex(int(v)) for v in b4).most_common(12))}")
        if not identify(b4):
            continue
        report(b4, engaged, speed_ms)
        print(f"\n  🛑 REMINDER: the ENGAGED column {list(ENGAGED_MODES)} is dosed; the DISENGAGED")
        print(f"     column {list(DISENGAGED_MODES)} is byte-stock, so manual and parking steering")
        print(f"     are UNTOUCHED by LEVER E'/D'. This car's manual mode is {MANUAL_MODE}.")
        print("  🛑 V74 still carries V72's UNGATED r24/r26 rate lane -- that dose applies in MANUAL")
        print("     below ~30 km/h too, and it is NOT what this probe measures. Score it separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
