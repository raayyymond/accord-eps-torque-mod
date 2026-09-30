# ADV "bytes+instrument" vs candidate A (robust-joint) — FAIL criteria, written BEFORE computing

Subagent adversary, 2026-09-30. Written after reading only the design report, its CRITERIA, and the census
report; before running any script or opening Ghidra. Candidate A = V294 image with ONE cal cell changed:
0xC63EA (fb-lag gain b) 567 -> 1106 (LE 37 02 -> 52 04). Default verdict if a claim cannot be reproduced: REFUTED.

## What a FAIL looks like (any one -> REFUTED or "do not flash" on that axis)

### (a) Bytes / arithmetic
- A1  The V294 image (sha256 3143616d...dbdd85) does NOT hold u16 LE 567 at 0xC63EA, or 0xC63EA is not the b cell
      (reader at 0x28F86 not `ld.hu` of tp+0x73EA), or the reader is signed (ld.h) such that 1106 changes sign
      semantics (it would not at 1106 < 32768, but the width/sign is checked anyway).
- A2  A second consumer of 0xC63EA exists (any reader other than 0x28F86 and the uncalled twin), found by Ghidra
      xrefs OR by a positive-controlled raw LE scan (4-byte disp16 incl. hw2|1, 6-byte extended form, absolute LE32,
      mov imm32 / movhi+movea pair building the address, tp/gp/r0-relative). Any live second reader not in the LKAS PID
      = FAIL unless its effect is proven harmless.
- A3  Any int32 intermediate overflows at b = 1106 over the full reachable state space: b*x (|x| <= 12000),
      a*s with s at its reachable extreme (incl. the pre-bail edge and the restart), s_new - s_old, E*Kp, the LERP
      products, the output-lag products, (y*ramp), (yr*pol*5346). int32 min margin < 2.0 (the designer's own bound)
      recomputed independently = FAIL of the claim; < 1.0 = hard FAIL.
- A4  The delivered surface T(idx) at zero wheel motion differs from V294's at ANY of the 241 demand indices (both
      signs), or the rail |T| max differs from +2461/-2463, or zero-command torque bound exceeds 616 T.
- A5  The restart pulse at 100 deg/s recomputed from bytes exceeds the pre-registered 288 T cap, or its derivation
      in the design mis-models the bail/restart path (e.g., restart happens on a path other than the ones stated,
      or happens routinely rather than only on faults).
- A6  Floor/truncation asymmetry introduced or magnified by b such that a zero-mean x produces a non-zero mean r26
      (a DC torque bias) larger than V294's by > 1 T.
- A7  The page CRC(s) the build would need cannot be computed/located, or the edit touches more than the 2 data bytes
      plus the CRC(s) — i.e. it is not "one build, cal-only".

### (b) Interlocks
- B1  The candidate can newly reach any interlock V294 cannot: soft-EME band 5120-5325 on the post-governor total,
      the forward-lane monitor FUN_0002b57a trip, lane/forward clamps, lockstep mirror disagreement, the |x| <= 12000
      bail (b does not feed x — verify), DTC plausibility on any cell that reads r26/s/T. A proof that the lane
      peak (|T| <= 3072 hard, rail 2461) is unchanged is necessary; a changed DWELL near the rail must be quantified.
- B2  Any monitor or DTC reads gp-0x3d30 (fb state), r26, or a quantity b scales, and was not in the designer's census.

### (c) Lineage
- C1  b on the DIFF operand at a value >= 1106 (or its class, "trim gain raised") was flown and falsified, or the
      design's lineage statement (V289 2301, V291/V292 958, stock/V293 1560, V294 567) does not match the images /
      build scripts. A mismatch in the lineage record = FAIL of the lineage claim (not necessarily of the build).
- C2  "What is different this time" is not real — e.g. the stock/V282/V293 value 1560 on the SUM operand at a=923 is
      the same physical trim class at a comparable Kp*b, and it was flown and falsified.

### (d) Observability
- D1  On the byte-exact model + r71b's measured tap residual/noise, ONE 15-30 s symptomatic window does NOT separate
      c2 (trim gain) for A from V294 with the 90 % intervals disjoint -> FAIL (the changed value is invisible).
- D2  The separation depends on hands-off driving that a 15-30 s symptomatic episode does not supply (e.g. needs
      30 s of hands-off with enough wheel acceleration), or the c2 CI in a short / low-excitation / high-speed window
      overlaps V294's -> FAIL of "one short drive".
- D3  c2 is confounded by a plausible non-b change (e.g. a pole a change, a plant J change, driver torque, x scale
      error, output-lag change) such that c2 ~ 1.9 does not uniquely identify b 1106 -> weaker claim, report.
- D4  The null sentence licenses a conclusion the instrument cannot support (e.g. "EPS-side damping does not limit
      the symptom" when the 1.6-3 Hz band cannot be measured to the needed precision in 15-30 s) -> FAIL of the sentence.

### (e) One build, cal-only
- E1  The candidate needs any code byte, or a second cal cell (e.g. a CRC not accounted for, a checksum cell in the
      calibration header), or relies on e_shift/opcode change -> FAIL of "cal-only".

## PASS looks like
Every A-E item reproduced from the IMAGE by two methods (Ghidra + Python) where load-bearing; the observability
simulation shows disjoint c2 intervals on short windows with r71b's own residual; the null sentence is honest.
