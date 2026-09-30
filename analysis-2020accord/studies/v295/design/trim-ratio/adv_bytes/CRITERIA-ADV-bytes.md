# ADV "bytes+instrument" on V295 trim-ratio (b 0xC63EA 567 -> 964) — FAIL criteria, written BEFORE computing

Adversary subagent, 2026-09-30. Written after reading the design report, its CRITERIA file and the census, and
before running any script or opening Ghidra. Anything added later is marked ADDED-LATER.

The pass must be able to return "do not flash". Any ONE of the following = REFUTED (do not flash) unless marked
SURVIVES_WITH_CHANGES-eligible (a fix exists that changes the design without changing its lever).

## (a) Bytes and arithmetic, from the V294 IMAGE (sha256 3143616d...dbdd85)
- A1 The image hash does not match, or u16 LE at 0xC63EA is not 567, or the reader of it is not a 16-bit load
  (a byte or word load would mean the width/neighbour is wrong). -> REFUTED.
- A2 A SECOND CONSUMER of any byte of [0xC63EA, 0xC63EC) exists in any encoding — tp disp16 (4-byte), 6-byte
  disp23 on any base incl. r0-absolute, a word load at 0xC63E8 that spans a and b, a byte load of 0xC63EB,
  an ep (r30) base set near the cell and an sld, a register base built by mov imm32 / movhi+movea within disp16 reach,
  a cal->RAM block copy that is later read — and it is not the uncalled twin island or a checksum routine. -> REFUTED
  unless proven inert. Every scan positive-controlled (a@0x28F8A, C@0x28F96, 6-byte gp-0x6752@0x48E56, mov imm32 0xCB994).
- A3 Any int32 intermediate of the fb former, the PID, the output lag or the forward gain overflows on a REACHABLE
  state at b = 964 (x in [-12000, 12000] by the bail, s at its floor-asymmetric supremum, worst sign) — or the
  margin a*s is < 2.0 (the designer's own rule). -> REFUTED.
- A4 The delivered surface T(idx) at x = 0 differs from V294 at any of 241 idx (x 3 taper states), is non-monotone
  where V294 is monotone, or the rail (+2461/-2463), zero-command cap (616) or sub-rail slope differ. -> REFUTED
  (the design's central "FF byte-identical" claim is false).
- A5 The designer's quoted numbers do not reproduce within 2 % by my own independent integer mirror (not the harness
  Lane, not the golden model): K_alpha 0.356, |P/x|20 3.535, restart peaks 24/73/246/542, int32 margin 2.39,
  zero-command 616. A non-reproducing number that is decision-bearing -> REFUTED; non-decision-bearing -> finding.

## (b) Interlocks
- B1 The candidate's reachable lane output T (open-loop replay of r71b's recorded x and cmd through the byte-exact lane,
  and the bounded worst case) newly exceeds a monitor threshold V294 could not reach (forward-lane monitor
  FUN_0002b57a bound, lane/forward clamps 3072, aggregator 0x2800, soft-EME 5120). -> REFUTED.
- B2 A monitor that reads a PID internal or the fb state (r26, s, gp-0x3d30) exists that the census missed. -> REFUTED
  unless the value cannot trip it.
- B3 Finding (not FAIL): replayed |T| distribution shift and time-at-cap under b964 vs V294, reported with numbers.

## (c) Lineage
- C1 0xC63EA on the DIFFERENCE operand (0x28FA4 subr) at a value >= 964 has been flown and falsified, or a record says
  "do not raise b" for this operand. -> REFUTED.
- C2 The design's lineage table (stock 1560 / V289 2301 / V291-V292 958-962 / V294 567) does not match my own byte read
  of the images on disk. -> finding; decision-bearing if it hides a flown same-operand value.

## (d) Observability (the one changed value is b)
- D1 On the byte-exact lane + r71b's own residual noise, the pre-registered E3 beta from ONE 15-30 s window
  cannot separate b964 from V294: the 5-95 % intervals of per-window beta (windows drawn the way a short
  symptomatic drive supplies them — ANY engaged window, not only hand-picked hands-off ones) overlap. -> FAIL
  (the build cannot attribute its own edit from one short drive). If they separate only on hands-off windows and
  hands-off windows cannot be guaranteed in 15-30 s, -> SURVIVES_WITH_CHANGES (name the window rule).
- D2 The designer's fake-tap construction is circular (the separation is entailed by construction, e.g. residual
  noise understated, the regressor derived from the same march it scores). -> finding; FAIL if the honest method
  loses the separation.
- D3 The null sentences leave a gap in the outcome space (a beta value that licenses nothing). -> finding,
  SURVIVES_WITH_CHANGES (close the gap).
- D4 The instrument named (427 tap = gp-0x6b38, 0x14A rate field) is not on the wire on V294 + b, byte-identical. -> FAIL.

## (e) One build, cal-only
- E1 More than one cell or any code byte must change, or 0xC63EA is not in a region V294's pipeline already
  re-CRC'd successfully (V294 flew with this cell edited). -> REFUTED.

## Decision rule
REFUTED if any A1-A4, B1, B2 (unmitigated), C1, D1 (full FAIL), D4, E1 fires. SURVIVES_WITH_CHANGES if only D1-partial,
D3 or non-decision-bearing A5/C2 findings fire. SURVIVES otherwise.
