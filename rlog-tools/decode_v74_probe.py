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

🛑🛑 WEAK BUILD IDENTITY -- AND IT HAS ALREADY BITTEN. 32 payload values are legal and there is no
structural invariant among them, so the value SET alone proves only that "some V74-shaped cave ran".
**Every V7x cave writes the SAME cell in the SAME bit positions**, so a log from another build is
structurally decodable here. Fed V73's own flight (route 5a) this decoder reported *"bit7 fires on
100.000% of frames ⇒ LEVER E' IS DELIVERING and the damper is in force for the first time in this
kit"* -- reading V73's CONSTANT liveness seed as V74's damper. `identify()` now REFUSES on that
signature (see its docstring for the three tests). **The .rwd FILENAME remains the pre-drive
discriminator and CAVE_HEX below the post-hoc one; the guard can only reject, never confirm.**

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
# 🛑 V73's bits 6:3 were `mode & 0xF`, and this car's modes are 24 (manual) / 26 (engaged) -> 8 / 10.
# BOTH are legal V74 gp-0x67FA states, so the two builds' payload alphabets OVERLAP. See identify().
V73_MODE_FIELD_VALUES = {24 & 0xF, 26 & 0xF}
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


NEARZERO_RATE_DEGS = 0.5      # |column rate| below this is "the wheel is not moving"
FACTORC_ONSET_MS = 9.72       # 35 km/h -- below it, mode 24's stock FactorC Y[0] = 0
MAX_LAG_S = 3.5               # V73's mode byte lags engagement by 1.02 s rise / 2.08 s fall


def _lagged_agreement(field_hi, engaged, t):
    """Best agreement between a 2-valued field and latActive over ANY lag in +/-MAX_LAG_S.

    🛑 A LAG SWEEP IS REQUIRED, not a zero-lag correlation. V73's mode byte follows engagement with
    a 1.02 s rise / 2.08 s fall, so at zero lag the agreement understates badly -- and understating
    is the dangerous direction here, because it lets a V73 log through.
    """
    n = len(field_hi)
    if n < MIN_SAMPLES or len(t) != n:
        return None, None
    span = float(t[-1] - t[0])
    fs = (n - 1) / span if span > 0 else 100.0
    best, best_lag = 0.0, 0
    for k in range(-int(MAX_LAG_S * fs), int(MAX_LAG_S * fs) + 1, max(1, int(fs / 20))):
        a = field_hi[k:] if k >= 0 else field_hi[:k]
        b = engaged[:len(a)] if k >= 0 else engaged[-len(a):]
        if len(a) < MIN_SAMPLES:
            continue
        agree = float(np.mean(a == b))
        if agree > best:
            best, best_lag = agree, k / fs
    return best, best_lag


def identify(b4, engaged=None, speed_ms=None, rate_degs=None, t=None, override=False):
    """Is this a V74 payload? 🛑 THE GUARD CAN ONLY EVER REJECT, NEVER CONFIRM.

    🛑🛑 ADDED AFTER THIS DECODER WAS RUN AGAINST V73's OWN FLIGHT AND CERTIFIED A LEVER THAT DOES
    NOT EXIST ON THAT CAR. Every V7x cave writes the SAME cell (`gp-0x1514`, CAN 0x14A byte4) in the
    SAME bit positions, so another build's log is *structurally* decodable here. On route 5a this
    file printed "bit7 fires on 100.000% of frames => LEVER E' IS DELIVERING and the damper is in
    force for the first time in this kit." It was reading V73's CONSTANT liveness seed. Nothing in
    the schema tripped: V73's `bits 6:3` are `mode & 0xF`, and this car's modes 24/26 give 8/10 --
    BOTH legal V74 `gp-0x67fa` states. **The two alphabets overlap, so no positive test exists.**

    FOUR DISCRIMINATORS, each derived from the design rather than from a threshold that felt right.
      D1  [DECISIVE] **MANUAL CREEP.** V74 doses only the ENGAGED column; mode 24 (manual) is
          byte-stock, so FactorC Y[0] = 0 => dose 0 => `gp-0x6bd0` = 0 => `bit7` = 0. On V73 bit7
          was a constant-1 liveness bit. ⚠ SCOPED ON PURPOSE: manual ABOVE ~35 km/h legitimately
          gives bit7 = 1 on V74 (FactorC is non-zero there), so the cell is manual **AND** creep.
      D1b [DECISIVE] **NEAR-ZERO STEERING RATE, any mode.** FactorE's Y[0] is preserved at 0, so at
          zero rate the product is 0 and bit7 must be 0 -- engaged or not, fast or slow. This one
          stays powered on an all-manual or an all-engaged segment, where D1 and D2 do not.
          ⊕ Column rate stands in for motor rate here: the rigid-body relation is exact at DC, and
          this test only ever looks at the DC end.
      D2  [DECISIVE] **THE FIELD MUST NOT TRACK ENGAGEMENT.** On V73 it was the mode byte and
          tracked latActive at ~99% at matched lag. On V74 it is `gp-0x67fa`, a fault-state machine
          with no business toggling with engagement. Swept over lag, > 90% is decisive.
      D3  [corroborating] **THE V73 FINGERPRINT:** exactly two values differing by bit1 (8/10).

    🛑 AN UNPOWERED CELL IS REPORTED AS **UNPOWERED**, NEVER AS A PASS. That distinction is the
    whole lesson of V64/V68's five uninterpretable nulls.
    """
    decisive, corroborating, unpowered = [], [], []
    nz = (b4 & BIT_DAMP_NZ) != 0
    st = (b4 & STATE_FIELD) >> STATE_SHIFT
    seen = {int(s) for s in st}
    eng = np.asarray(engaged, bool) if engaged is not None and len(engaged) == len(b4) else None
    v = np.asarray(speed_ms, float) if speed_ms is not None and len(speed_ms) == len(b4) else None
    r = np.asarray(rate_degs, float) if rate_degs is not None and len(rate_degs) == len(b4) else None

    # ---- D1: manual creep ----------------------------------------------------------------------
    if eng is None or v is None:
        unpowered.append("D1 (manual creep): no latActive/vEgo in this log")
    else:
        m = (~eng) & np.isfinite(v) & (v <= CREEP_MAX_MS)
        n = int(m.sum())
        if n < MIN_SAMPLES:
            unpowered.append(f"D1 (manual creep): only {n} frames (< {MIN_SAMPLES}) -- UNPOWERED, "
                             "NOT a pass")
        elif nz[m].all():
            decisive.append(f"D1 MANUAL CREEP: bit7 is set on ALL {n} manual-creep frames. Mode "
                            f"{MANUAL_MODE} is byte-stock on V74, so FactorC Y[0] = 0 => dose 0 => "
                            "bit7 MUST be 0 there. This is V73's constant liveness seed.")
        else:
            corroborating.append(f"D1 passes: bit7 is clear on "
                                 f"{100 * (1 - nz[m].mean()):.1f}% of {n} manual-creep frames")

    # ---- D1b: near-zero steering rate ------------------------------------------------------------
    if r is None:
        unpowered.append("D1b (near-zero rate): no 0x18F rate in this log")
    else:
        m = np.isfinite(r) & (np.abs(r) < NEARZERO_RATE_DEGS)
        n = int(m.sum())
        if n < MIN_SAMPLES:
            unpowered.append(f"D1b (near-zero rate): only {n} frames (< {MIN_SAMPLES}) -- "
                             "UNPOWERED, NOT a pass")
        elif nz[m].all():
            decisive.append(f"D1b NEAR-ZERO RATE: bit7 is set on ALL {n} frames with |column rate| "
                            f"< {NEARZERO_RATE_DEGS} deg/s. FactorE's Y[0] is preserved at 0 by "
                            "design, so the product is 0 and bit7 MUST be 0 there.")
        else:
            corroborating.append(f"D1b passes: bit7 is clear on "
                                 f"{100 * (1 - nz[m].mean()):.1f}% of {n} near-zero-rate frames")

    # ---- D2: the field must not track engagement -------------------------------------------------
    if eng is None or len(seen) != 2 or t is None:
        unpowered.append(f"D2 (engagement tracking): field takes {len(seen)} value(s) -- "
                         "UNPOWERED, NOT a pass")
    else:
        agree, lag = _lagged_agreement(st == max(seen), eng, np.asarray(t, float))
        if agree is None:
            unpowered.append("D2 (engagement tracking): too few frames -- UNPOWERED")
        elif agree > 0.90:
            decisive.append(f"D2 ENGAGEMENT TRACKING: bits 6:3 track latActive at "
                            f"{100 * agree:.1f}% at lag {lag:+.2f} s. V73's mode byte toggles with "
                            "engagement; V74's fault-state machine does not.")
        else:
            corroborating.append(f"D2 passes: best lagged agreement with latActive is only "
                                 f"{100 * agree:.1f}% (at {lag:+.2f} s)")

    # ---- D3: the V73 fingerprint -----------------------------------------------------------------
    if len(seen) == 2:
        a, b = sorted(seen)
        if (a ^ b) == 2 and seen <= V73_MODE_FIELD_VALUES:
            corroborating.append(f"D3 FINGERPRINT: exactly two values {sorted(seen)} differing by "
                                 f"bit1 -- this car's mode byte & 0xF ({MANUAL_MODE} -> "
                                 f"{MANUAL_MODE & 0xF}, {LIVE_MODE} -> {LIVE_MODE & 0xF})")

    # ---- verdict ---------------------------------------------------------------------------------
    if unpowered:
        print("  ⚠ UNPOWERED CHECKS (these are NOT passes):")
        for u in unpowered:
            print(f"     · {u}")
    if decisive:
        print("\n  " + "=" * 92)
        print("  🛑🛑 REFUSING TO DECODE -- THIS LOOKS LIKE A **V73** PAYLOAD, NOT V74.")
        print("  🛑 The V73 MODE-BYTE schema applies to these bytes, not V74's damper/state schema.")
        print("  " + "=" * 92)
        for w in decisive:
            print(f"     · [DECISIVE] {w}")
        for w in corroborating:
            print(f"     · [corroborating] {w}")
        print("     ⇒ V73's cave writes the same byte in the same bit positions and its alphabet")
        print("       OVERLAPS V74's, so it decodes here silently and produces a CONFIDENT WRONG")
        print("       answer. Read it with decode_v73_probe.py instead.")
        print(f"     🛑 Confirm the flashed .rwd is {RWD_NAME}")
        print("     Re-run with --i-confirm-v74 to override AFTER checking the filename.")
        if not override:
            return False
        print("  ⚠ --i-confirm-v74 given: proceeding under protest. Every number below is suspect.")
    elif corroborating:
        print("  ⊕ build-identity checks that ran clean:")
        for w in corroborating:
            print(f"     · {w}")

    states = seen
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
    print(f"  ✅ not excluded as V74: states seen {sorted(states)}, "
          f"bit7 duty {100.0 * np.mean(nz):.3f}%")
    print("     🛑 'not excluded' is NOT 'confirmed' -- the payload alphabets overlap and the")
    print("        FILENAME remains the only pre-drive discriminator.")
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
    args = [a for a in argv[1:] if not a.startswith("--")]
    override = "--i-confirm-v74" in argv[1:]
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
        print(f"  payload histogram: {dict(Counter(hex(int(v)) for v in b4).most_common(12))}")
        if not identify(b4, engaged, speed_ms, data.get("rate"), data.get("t"),
                        override=override):
            refused += 1
            continue
        report(b4, engaged, speed_ms)
        print(f"\n  🛑 REMINDER: the ENGAGED column {list(ENGAGED_MODES)} is dosed; the DISENGAGED")
        print(f"     column {list(DISENGAGED_MODES)} is byte-stock, so manual and parking steering")
        print(f"     are UNTOUCHED by LEVER E'/D'. This car's manual mode is {MANUAL_MODE}.")
        print("  🛑 V74 still carries V72's UNGATED r24/r26 rate lane -- that dose applies in MANUAL")
        print("     below ~30 km/h too, and it is NOT what this probe measures. Score it separately.")
    # 🛑 EXIT NON-ZERO ON ANY REFUSAL. A guard that returns success is only half a guard: the loud
    # banner is for a human, this is for anything that pipes, wraps or CI-checks the decoder. The
    # failure it exists to stop -- V73's payload certified as "LEVER E' IS DELIVERING" -- was found by
    # running the decoder on the wrong log, which is exactly what a script would do silently.
    if refused:
        print(f"\n🛑 {refused} of {len(args)} target(s) REFUSED or empty -- exiting non-zero.")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
