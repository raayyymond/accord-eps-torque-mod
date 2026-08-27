---
name: reference_accord_gp683c_repoint_hypothesis_and_v850_bit5_encoding_rule
description: "gp-0x683c CONFIRMED zero writers (sole touch = the one ld.bu read @0x3aa94 in FUN_0003aa2c), verified by a 3-method cross-check that caught and corrected a real V850 decode trap. NEW ENCODING RULE for gp/tp-relative BYTE ops: for ld.b/ld.bu LOADS, the true displacement LSB lives in hw1 BIT 5, not hw2 (hw2's own bit0 is a don't-care); for st.b STORES, hw2 IS the exact canonical displacement, hw1 bit5 is a fixed opcode bit. A naive raw-byte scan that only checks hw2 will misclassify adjacent-address near-misses as hits (or vice versa) unless this is applied. 0xC6446/0xC6444 (r24/r26's dead-gate gain arms) confirmed FUN_0003aa2c-exclusive single readers, same CAL_BLOCK (0xC6000,0xC6FFC) as the rest of this cluster. gp-0x67a4 corrected from 'zero readers' to '1 reader + 1 writer, but semantically a saturation-DWELL state coupled to the arb command gp-0x6b3c, not an engagement flag' -- rejected as a repoint target on semantic grounds, not a re-derivation of the null. gp-0x67fe (LKAS engage-SM state) identified as the strongest untested candidate, beating all 3 signals team-lead proposed."
metadata:
  type: reference
---

# gp-0x683c repoint hypothesis -- traced 2026-08-01, same session as the r24/no-fork finding

Team-lead's hypothesis: `FUN_0003aa2c`'s r24/r26 gain-arm priority chain already has a THIRD arm gated on
`gp-0x683c`, which per [[reference-accord-v61-taps-gain-priority-and-sign-apples-to-apples]] has zero
writers (structurally dead). Repointing its single load to an LKAS-engagement byte would make cal
`0xC6446` (r24's `gp-0x683c!=0` arm, currently 512/Q10=0.5) an LKAS-ONLY override, cal-edit + one
displacement halfword, no code cave. Builds on
[[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]].

## 1. The gate, exact addresses [EVIDENCE, fresh disassembly of FUN_0003aa2c]

Sole load: **`0x3aa94: ld.bu -0x683c[gp],r15`**, raw bytes `84 7f c5 97` (4-byte disp16 form, reg1=gp(4),
reg2=r15). Flag computed once (`0x3aaa8: setfne lp`, `lp=(gp-0x683c!=0)`) and reused for BOTH lanes:
- r26 consumes it at `0x3ab56: cmp r0,lp` / `0x3ab58: be 0x3ab64` (branch when `683c==0`; fall-through
  `0x3ab5e: ld.hu 0x7444,tp,r8` = cal **0xC6444**, r26's `683c!=0` arm).
- r24 consumes it at `0x3ac04: cmp r0,lp` / `0x3ac06: be 0x3ac0e` (branch when `683c==0`; fall-through
  `0x3ac08: ld.hu 0x7446,tp,r10` = cal **0xC6446**, r24's `683c!=0` arm).

**Priority order, Q6, addresses confirmed:** `gp-0x671d` is tested FIRST (`0x3abfa cmp r0,r6` /
`0x3abfc be 0x3ac04`, `r6=(671d!=0)` computed at `0x3aba8`) -- if `671d!=0`, execution falls straight
through to `0x3abfe: ld.hu 0x7442,tp,r10` (cal 0xC6442, unity) and the `gp-0x683c` test at `0x3ac04` is
**never reached at all**. Only when `671d==0` does control reach the `683c` test. `671d` strictly outranks
`683c`, exactly as the golden model states, now pinned to instruction addresses.

## 2. gp-0x683c has ZERO writers -- CONFIRMED, 3-method cross-check, one method caught a real trap [EVIDENCE]

`search_instructions("683c")`: 2 hits total, the real read + 1 branch-target-address text collision in
`FUN_00066ab6` (excluded, standard false-positive class in this kit) -- `truncated:false`, 183,429
instructions.

**Raw Python byte scan, both possible hw2 encodings** (canonical `-0x683c` = `0x97C4`; "or-1" form =
`0x97C5`): `0x97C4` exact -> 0 raw hits anywhere in the 1,048,576-byte image. `0x97C5` -> 15 raw hits.
**Naively trusting "15 hits" here would have been WRONG** -- decoding each hit's `hw1` field showed they
split into two groups by `hw1` bit 5: the ONE hit with bit5=0 is the known read at `0x3aa94`
(`-0x683c`, even); the other 14 (bit5=1, or a genuinely different store opcode class) all resolved, via
fresh disassembly of their containing function (`FUN_00052e32`/`FUN_00053216`), to **`-0x683b`** (both loads
and stores, a DIFFERENT, adjacent RAM byte with its own shadow-lockstep pair, part of an unrelated
init/verify routine) -- confirmed by direct Ghidra mnemonic text (`ld.bu -0x683b[gp],r10`,
`st.b r14,-0x683b[gp]`, etc.), not by my own bit-guessing alone. **Zero real writers to gp-0x683c anywhere
in the image, both by exact-hw2 store scan and by the corrected load/store reclassification of every
"off-by-one-bit" candidate.**

## 3. NEW encoding rule, resolves team-lead's "decode carefully, hw1 bit 5" instruction [EVIDENCE, byte-level worked proof]

For V850 gp/tp-relative **BYTE** load/store (this session only directly verified `ld.bu`/`st.b`, both with
`reg1=gp`):
- **LOADS (`ld.bu`):** the TRUE 16-bit signed displacement is `(hw2 & 0xFFFE) | bit5(hw1)`. `hw2`'s own bit0
  is a don't-care (empirically 1 in every `ld.bu` example seen, but masked away, not load-bearing).
  Worked proof: `0x3aa94` (`hw1=0x7f84`, bit5=0) and `0x53174`/`0x53184` (`hw1=0x57a4`, bit5=1) have the
  **identical raw `hw2=0x97c5`** yet decode to `-0x683c` and `-0x683b` respectively -- confirmed against
  Ghidra's own mnemonic both times, not inferred.
- **STORES (`st.b`):** `hw2` IS the exact canonical displacement; `hw1` bit5 is a fixed part of the store
  opcode (0 in every `st.b` example seen), not a displacement bit. Worked proof: `0x293a6`
  (`st.b r6,-0x6806,gp`, `hw2=0x97fa` exact) and the four `st.b r14/r10/r12,-0x683b,gp` sites in
  `FUN_00052e32` (`hw2=0x97c5` exact, all `bit5=0` despite targeting the ODD `-0x683b`) -- if bit5 mattered
  for stores the same way it does for loads, these would have decoded to `-0x683c` instead; they didn't.

**Practical consequence for a repoint edit:** since `-0x683c`'s own displacement is EVEN (`bit5=0`), a pure
`hw2`-only edit (matching the V57 precedent exactly, no `hw1` change) is possible **only if the new target's
own canonical displacement is also EVEN**. Checked candidates: `-0x67fe`(even, OK), `-0x6806`(even, OK),
`-0x67a4`(even, OK), `-0x6807`(**ODD** -- would additionally require flipping `hw1` bit5, a slightly larger
edit, one more reason it's a worse choice even before its semantic problems below).

## 4. 0xC6446 / 0xC6444 blast radius [EVIDENCE]

`search_instructions("7446")`: 4 hits -- 1 real (`0x3ac08`, inside `FUN_0003aa2c`, r24's arm) + 3
branch-target-address text collisions (`0x74454`/`0x77406`/`0x77416`, all `br` mnemonics, excluded).
`search_instructions("7444")`: 2 hits -- 1 real (`0x3ab5e`, inside `FUN_0003aa2c`, r26's arm) + 1 collision
(`0x6743e`). **Both cals are FUN_0003aa2c-exclusive single readers**, matching the sibling cals
`0xC6440`/`0xC6442`/`0xC643E` already established this way. No second reader anywhere in the
183,429-instruction analyzed corpus -- no monitor/shadow function independently re-derives either value.
Current values (fresh `read_memory`, `0xC6440..0xC6446`): `0xC6440=2048`(r24 state>=5), `0xC6442=1024`(r24
671d unity), `0xC6444=512`(r26 683c-arm), `0xC6446=512`(r24 683c-arm) -- all Q10, all match the existing
record exactly. **CRC block**: `CAL_BLOCK=(0xC6000,0xC6FFC)` per `builds/v50_v79/build_v53_tva.py` line 147 -- same single
CRC-covered block as the rest of this cal cluster and as V57's edit, no cross-block complication.

## 5. LKAS-active-byte candidate evaluation [EVIDENCE + one semantic correction]

- **`gp-0x6806`** (deadband/sign-relay enable) -- **polarity resolved from the instruction, not prose**:
  fresh disassembly of `FUN_00028ea6` at `0x2a1b6-0x2a1bc` (`ld.bu -0x6806,gp,r12` / `cmp r0,r12` /
  `bne 0x2a1e6`) confirms the block runs **only when `gp-0x6806==0`**. Per
  [[reference_accord_gp6806_phase_flag_and_dead_writer_split]]'s phase table, `gp-0x6806=1` for phases
  1-4 (ramp-active) and `=0` for phase 0 (full reset) or 5/6/7 (settled). Team-lead's own on-car number
  (CAN `STEER_CONTROL_ACTIVE`, sourced from this cell's bit0, measured 96.26% HIGH with only 2 transitions
  in 180s during an engaged drive) is strong empirical evidence `gp-0x6806=1` tracks "LKAS actively
  controlling" for the great majority of real driving, not literally "mid-ramp-this-instant" -- but this
  reading leans on the on-car measurement to close a gap static analysis alone can't (whether "settled"
  phases 5/6/7 ever occur DURING steady engaged holding, vs only on disengage) -- **ACCEPT as viable,
  flagged not fully closed by structure alone.** Displacement even, pure hw2 edit possible.
- **`gp-0x6807`** (`STEER_STATUS`, values seen 0/3/4/7 per existing memory + this session's 30-hit
  `search_instructions` showing many DIFFERENT source registers writing it across `FUN_00028ea6` and
  `FUN_0002a30e`) -- **REJECT**. Multi-valued, not binary; value 3 is the SPEED-GATED LOCKOUT state per
  [[reference_accord_steerstatus3_speed_gated_but_report_only]], the OPPOSITE of "applying." A naive
  `!=0` test would read true during lockout too. Also odd-parity displacement (would need an `hw1` edit
  too, not pure `hw2`).
- **`gp-0x67a4`** -- **CORRECTS team-lead's prior record ("zero readers")**: fresh `search_instructions`
  found exactly 1 writer (`FUN_0002b422 @0x2b51e`) and 1 reader (`FUN_00028ea6 @0x2a222`, comparing the
  value against 2 and 3), not zero. Decompiled the writer in full: `FUN_0002b422` is a **7-state machine**
  (`gp-0x3d28`, states 0-6) whose PRIMARY input is `gp-0x6b3c` compared against the arbitration forward
  clamp cal (`0xC61B2`) -- i.e. it tracks how close/how-long the LKAS command sits near its clamp CEILING
  (a saturation-dwell monitor), not "is LKAS applying any torque." **REJECT on semantic grounds** (real,
  live, but the wrong signal -- testing it nonzero would gate on near-saturation specifically, a much
  narrower and differently-timed condition than "LKAS engaged").
- **`gp-0x6b4c`** (LKAS command into the aggregator) -- REJECT as stated in the brief: signed halfword,
  crosses zero during ordinary lane-keeping corrections, no byte-sized slice of it is a sane "applying"
  proxy (a low-byte-only test aliases wildly against magnitude; a high-byte test still chatters at
  ordinary steering-correction rates, not a clean state flag).
- **`gp-0x67fe` -- NEW CANDIDATE, not on team-lead's list, appears to be the strongest option found.**
  Established this session (see [[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]]): the
  LKAS engage state-machine's own state byte. Sole writer `FUN_0003bd7c` (4 `st.b` sites,
  `0x3bdb8/0x3be4e/0x3be5a/0x3be7a`). Per existing memory, `gp-0x67fe==0` is explicitly "EPS-assist-DOWN"
  and `gp-0x67fe∈{1,2}` gates "assist up" elsewhere in this codebase -- i.e. it is ALREADY a documented,
  reasonably clean 0-vs-nonzero engagement flag, not something inferred fresh this session. **Task-order
  confirmed**: `FUN_0003bd7c` runs well before `FUN_0003aa2c` in the same 1kHz cycle (see the r24-no-fork
  memory's task-order proof), so it is fresh at the read point. Displacement even (`-0x67fe`, canonical
  `0x9802`) -- pure `hw2`-only edit, matching the V57 pattern exactly. **NOT YET MEASURED for toggle
  rate on-car** (unlike `gp-0x6806`, which has the team's own 2-transitions/180s number) -- this is the one
  open gap before recommending it over `gp-0x6806`. Being a discrete lifecycle-state byte (not a per-tick
  continuous quantity), it should structurally NOT chatter at 20-60Hz, but this is inference from its
  role, not a measurement.

## Verdict

The hypothesis survives every check performed: `gp-0x683c` is genuinely dead (rigorously re-confirmed,
catching a real decode trap along the way), the priority chain places it below `671d` and above the
natural LERP exactly as assumed, `0xC6446`/`0xC6444` are private single-reader cals in the expected CRC
block, and a repoint is encodable as a pure 2-byte `hw2` edit (no `hw1`/opcode change) provided the target
displacement is even -- true for the best candidates. **Two live candidates, neither fully closed:**
`gp-0x6806` (structure resolved, on-car chatter number already exists, semantic gap on "settled-while-
engaged") and `gp-0x67fe` (structure resolved, semantically cleaner per existing memory, but no on-car
chatter measurement yet). `gp-0x6807` and `gp-0x67a4` are both ruled out on evidence, not assumption.

## Related
[[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]] -- source of the `gp-0x67fe` task-order
and producer evidence this entry reuses.
[[reference-accord-v61-taps-gain-priority-and-sign-apples-to-apples]] -- original `gp-0x683c` zero-writer
flag (single-method at the time), now closed with a 3-method cross-check.
[[reference_accord_gp6806_phase_flag_and_dead_writer_split]] -- phase-to-`gp-0x6806` mapping this entry's
polarity check corroborates.
[[reference_accord_steerstatus3_speed_gated_but_report_only]] -- source of `gp-0x6807`'s lockout-state
identity used to reject it here.
