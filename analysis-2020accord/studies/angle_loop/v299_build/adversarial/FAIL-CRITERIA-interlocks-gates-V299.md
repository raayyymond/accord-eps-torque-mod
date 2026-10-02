# FAIL criteria — adversary (interlocks / GATE 1 / GATE 2), V299 built image

Written BEFORE the attack. Image under test: `_v299_V299-ANGLELOOP...A16B_plain_image.bin`,
sha256 30ff05fa464e87ab7eecfcbab9cbf6dfb3afcb57ceb5c89e4a29c1f748c38f08, base V298 177abf04....
Every check re-derives from the IMAGE bytes (Python LE scan + Ghidra decode of a disasm-only copy),
never from build_v299_tva.py constants or the spec's claims.

## DO NOT FLASH if ANY of these is observed

1. **Stray diff.** Any byte differing V298 -> V299 outside {cave span 0xC4C00..0xC4D04, F181 string
   0x1310D, main-block CRC trailer 0xC4FFC..0xC4FFF}; or the diff count != 67; or any changed byte
   lands in a gain / table / clamp / cal cell (Kp, Kd, Ki, ICL, DCL, fb a/b/C, GB-P rows, assist map,
   EME, governor, lockstep, DTC thresholds). => GATE 2 "by construction" claim is FALSE.
2. **Write set non-empty.** Any store instruction (st.b/st.h/st.w, sst.*, set1/clr1/not1 on memory,
   caxi, prepare/push to a non-stack base, or bit-ops) anywhere in the V299 cave, or any change of a
   stack/state word the cave did not have in V298 (GATE 1: the cave must still own no RAM).
3. **Control-flow break.** Any branch/jump in the rewritten span whose target is not an instruction
   start (mid-instruction landing), leaves the cave other than to the V298-verified exits
   (0x29D7E FRZ/CAM tail, `jmp [r6]` DONE), or any new entry into the cave span other than the
   single `jarl` from the V298 hook (xref census by raw LE scan for jarl/jr/jmp hitting 0xC4C00..0xC4D04).
   A fall-through off the end of the rewritten region into data or the unchanged tail at a
   non-instruction boundary.
4. **Exit-semantics regression.** Engage / disengage / bail / 0xE4 fault sentinel / request-drop /
   camera-gate (r25=0) / op-skip paths take a different exit in V299 than V298 for the same inputs,
   other than the intended rev-2 edits (freeze 512->1229, asymmetric bound, two-level cap).
   Specifically: camera gate or sentinel paths no longer reaching freeze/bail -> FAIL.
5. **Register clobber.** The cave writes a register that the caller relies on after return
   (outside the V298 scratch/exit set: r6 on FRZ/CAM, r16 = E', r26 = op), or leaves sp/lp/gp/tp/ep
   changed.
6. **Downstream consumer change.** Any consumer of the cells the cave reads (a4f68 raw, op, angle,
   integrator I, v) is a different instruction sequence in V299 than in V298 (outside the cave span).
7. **Unbounded output.** Any input reachable on the car that yields |E'| beyond what V298's
   downstream clamps admit, or an output bound that grows without limit (e.g. the uncapped `shl 6`
   path reachable at a speed where it was not intended), producing authority above V298's rail.
8. **Nonlinear hazard judged UNSAFE** (not merely a cost): if, in the moderate-hand band
   (driver torque raw 500-1200, no fork override), the lane holds more than the driver can
   reasonably overcome AND does not release (no path to freeze/bail), or if the outward light
   co-steer release or the 6144 cap's curve-hold shortfall can produce an unannounced loss of
   lane hold at a speed/curvature where the driver has no warning (e.g. above the v=2880 gate where
   the cap is removed) — and no stop band / operator-visible signal exists.
9. **CRC.** The main-block CRC over [0x13000, 0xC4FFC) does not reproduce the trailer, or any
   other block's CRC chain breaks (walk != 0).

## PASS_WITH_DEFECTS
All of 1-7 and 9 hold clean; one or more nonlinear items (8) are real but bounded, declared on the
page with a stop band; or documentation/assertion defects that do not change the bytes.

## PASS
All clean, nonlinear costs declared with stop bands, no documentation defects worth fixing before flight.
