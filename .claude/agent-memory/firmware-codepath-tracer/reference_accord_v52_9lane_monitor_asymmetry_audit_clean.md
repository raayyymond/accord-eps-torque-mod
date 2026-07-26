---
name: reference_accord_v52_9lane_monitor_asymmetry_audit_clean
description: V27-class monitor-asymmetry audit of the 9 gp-0x4f60 read sites being newly added to V52's repoint list (beyond the original 10) — all 9 destination chains traced one level downstream via raw byte scan + GhidraMCP decompile; verdict is SAFE for all 9, no raw-vs-filtered lockstep divergence hazard found.
metadata:
  type: reference
---

# V52 9-lane monitor-asymmetry audit (2026-07-24, code.bin/stock, gp=0xFEDF8000)

Requested by team-lead to close the "9 newly-repointed lanes" gap flagged in CLAUDE.md's V52
completeness note. Method: raw Python byte scan (op range 0x38-0x3D, reg1==4/gp, per the
verified encoding in `reference_accord_v48b_freeram_and_v850_encoding_formulas` /
`reference_accord_can_tx_mailbox16_freecheck_and_v850_mov_imm32_stb_encodings`) over
`[0x13000,0xC4FFC)` in `code.bin` for every destination's disp16, then GhidraMCP
`decompile_function` on every reader classified as a monitor/comparison. Every "zero readers"
claim below was corroborated by a SECOND method (`search_instructions` operand-pattern, plus
`get_xrefs_to` where applicable) per the domain's misleading-zero trap — none contradicted the
byte scan this session.

## Verdict table

| lane (read site) | destination | #readers of dest | monitor? | shape | DTC (if any) | verdict |
|---|---|---|---|---|---|---|
| 0x29A90 (`FUN_00028ea6`) | gp-0x6a32 | **0** (2 writers only: 0x29D72 live-fn, 0x2AC68 in the CONFIRMED-DEAD `FUN_0002a93a`) | no | n/a — no consumer | n/a | **SAFE (vacuous)** |
| same fn, same read | gp-0x6b2c | **5 reads** (corrected 2026-07-24 follow-up — see note below; NOT 6), 9 writers, all inside the same E1-gate cluster | no — structurally dead | n/a | n/a | **SAFE** — re-derived this session: `gp-0x6809` (gate `cVar44`) still has exactly 4 reads / 0 writes program-wide (re-confirmed via `search_instructions -0x6809`), so every `cVar44=='\x01'` branch is unreachable and gp-0x6b2c is written `=0` on every live pass. Matches `reference_accord_gp6809_zero_writers_confirmed_dead_gate`. |
| 0x2B69E (`FUN_0002b62c`) | gp-0x6aea | consumer `FUN_0004e96a` | no | n/a | none | **SAFE** — `FUN_0004e96a` is a UDS/CAN diagnostic-snapshot packer (fixed 0x38-byte record, length field literal `0x38`), not a fault monitor. |
| 0x2DF32 (`FUN_0002db94`) | gp-0x6b1a (+ same-cycle raw-negated copy at gp-0x6b16, same local var) | consumer `FUN_0002e52e` | yes | **(a) literal** | DTC 0x18 present in same fn (see below) — unrelated | **SAFE** |
| 0x33D2A (`FUN_00033d10`) | gp-0x6b78 | consumer `FUN_0003405a` | yes | **(a) literal** (`&PTR_FUN_00005000`+val<bound idiom, the codebase's usual magnitude-bound-via-pointer-arith pattern) | DTC 0x18 (unrelated); 2 shadow pairs present (gp-0x6a8c/gp-0x4cbc, gp-0x68b1/gp-0x4c4d) but both derive from OTHER inputs, not gp-0x4f60 | **SAFE** |
| 0x36682 (`FUN_00036682`) | gp-0x6b46 | producer is itself a rate-limiter/IIR (self-filter, flagged separately for cascade review — efficacy question, not this audit); consumer `FUN_00038148` (6-term weighted-sum aggregator → gp-0x6b70, clamp vs literal cal) | no | (a) | none in either fn | **SAFE** |
| 0x36846 (`FUN_00036828`) | gp-0x6b44 | internal self-referential slew (compares current filtered value against the SAME function's own prior-cycle state `gp-0x3798`, literal-threshold gated) | yes, but shared-input/self | **(a)/(b)-degenerate** | DTC 0x23 present in same fn — traced to an UNRELATED electrical-angle-rate/resolver-position check (different local-var chain entirely, no touch of gp-0x6b44); `record[+8]=0` → **NOT hard-eligible** | **SAFE** |
| 0x3B908 (`FUN_0003b8f6`) | gp-0x6bfc → gp-0x6bfe (`FUN_0003bc20`) | float-derivative PID chain; `FUN_0003bc20` is a pure ±20000 literal-bound clamp+flag | yes | **(a) literal** | none | **SAFE** |
| 0x3F8E2 (`FUN_0003f884`) | feeds `gp-0x69ca` chain (angle-rate integrator), NOT gp-0x6a0a directly | comparisons found are literal-bound / sign-dependent rounding only | no raw-twin compare | (a) | none in this fn | **SAFE** (mode-gate liveness of this lane is a SEPARATE open question, see below) |
| 0x3FCC6 (`FUN_0003fc16`) | gp-0x6a0a | consumer `FUN_0003b338` (literal-bound clamp → gp-0x6b6e) | shadow-lockstep pairs present (gp-0x6a02↔gp-0x4c8c, gp-0x6a10↔gp-0x4c90) | **NOT a hazard** — both shadow pairs protect an angle-rate accumulator (`gp-0x6a02`, fed from `gp-0x69ca`/FUN_0003f884) that is fully resolved and shadow-verified BEFORE the gp-0x4f60(-filtered)-derived correction term is additively applied; the sum (gp-0x6a0a) itself has **zero shadow twin** (no compare pattern found, matches its 1-reader/3-writer profile) | shadow mismatch → generic `FUN_0006b9fa`→`FUN_0006ce7c(4)` (just a class-flag write, NOT itself a DTC call); the fn's own `FUN_0001cba6()` call → DTC 0x18 (task-execution-count watchdog, unrelated to value) | **SAFE** |

## DTC hard-fault-eligibility bytes read this session (formula: `record=0xB7D58+(idx-1)*0x1c`, eligibility flag at `record[+8]`)

- **0x18** (task-execution-count watchdog, `FUN_0001cba6`, called from `FUN_0002e52e`/`FUN_0003405a`/`FUN_0003fc16`): `record[+8]=1` → **hard-eligible** by the same bit pattern as 0x17/0x1c/0x1d (all read `=1` this session, vs `=0` for known-non-eligible 0x49/0x23). Structurally UNRELATED to any of the 9 lanes — it counts function-call sequence numbers per task slot, not a torque/signal value, so filtering gp-0x4f60 cannot perturb it.
- **0x23** (`FUN_00036828`, electrical-angle/resolver-position check, co-located with lane gp-0x6b44 but proven on a disjoint variable chain): `record[+8]=0` → **NOT hard-eligible**.
- **0x49** (`FUN_00028ea6`, the known DTC-0x49 fail counter from the V36/V37 lineage): re-confirmed `record[+8]=0` → **NOT hard-eligible**, consistent with the existing V37 project record.

## Key instruction-level facts (new this session)

- `ld.h -0x4f60,gp,r12` at **0x29A90** is byte-confirmed (`24 67 a0 b0`) as the sole repoint instruction for that site; it feeds ONLY a sign-test (`cmp r0,r12` / `blt`/`bge`) selecting between two symmetric assist-curve LERP table pairs — the SELECTED MAGNITUDE comes from `gp-0x682f` (driver torque byte), not from the sign-tested value itself. The result lands in gp-0x6a32, which has zero readers.
- FUN_00028ea6 contains exactly **2** gp-0x4f60 reads total (byte-scanned over its full body 0x28ea6-0x2a30d): 0x28F26 (existing raw literal-vs-±25600 gate, NOT being repointed) and 0x29A90 (new repoint). They share no downstream consumer — the "read both raw and filtered in one function" special-attention case from the brief is CLOSED, no hazard.
- `gp-0x6809`'s dead-gate status (0 writers, 4 reads, all in `FUN_00028ea6`) re-verified fresh this session via `search_instructions` — unchanged from the earlier finding.

## Correction (2026-07-24, team-lead re-verification pass)

The "6 reads, all inside the same E1-gate cluster" line above is imprecise. Whole-program
`search_instructions` on operand `0x6b2c` (186,069 instructions, `truncated:false`) actually finds
**14 hits: 5 reads (`ld.h`) + 9 writes (`st.h`)**. Four reads (0x29846/0x29882/0x2995c/0x29a22) are
inside live `FUN_00028ea6`. The 5th, at **0x2A8FC**, has no Ghidra function attribution — it sits in a
1074-byte `has_orphaned_instructions` gap (0x2A508-0x2A939, per `find_code_gaps`) bounded by
`FUN_0002a30e` (before) and `FUN_0002a93a` (after). Both bounding functions were independently
reconfirmed this pass to have **0 callers and 0 xrefs to their entry points**
(`get_function_callers`/`get_xrefs_to`, both empty) — consistent with the project's standing record
that `FUN_0002a30e`/`FUN_0002a93a` are dead duplicate debounce/arb logic superseded by the inline copy
in `m_steer_torque_arbitration`. **The 5th read is dead code in that same unreachable block, not a live
6th consumer — verdict SAFE is unchanged, only the count/wording was wrong.** Also independently
reconfirmed this pass: gp-0x6a32 (0 readers, 2 writers) via the same whole-program sweep; gp-0x6809
dead-gate (4 reads/0 writes); the `FUN_0006b9ee` (real DTC-0x17 hard-fault setter,
callers cluster in the 0x59xxx-0x69xxx ADC/resolver subsystem) vs `FUN_0006b9fa` (generic
`FUN_0006ce7c(4)` class-flag, callers include `FUN_0002214a`/`FUN_0003405a`/`FUN_00034350`/
`FUN_000352b4`/`FUN_0003aa2c` — the torque/assist chain) distinction, confirming the gp-0x6a0a-area
shadow pairs feed the weaker non-DTC function, not the hard-fault path; DTC-0x18/0x23/0x49
eligibility bytes (`record[+8]` = 1/0/0) via direct `read_memory`; and the 0x28F26 baseline
±25600-literal gate as a genuinely separate `ld.h` from the repointed 0x29A90 sign-test site.

## Bottom line

**YES** — all 9 newly-added lanes can be repointed to the filtered `gp-0x4f60` copy without creating
a raw-vs-filtered lockstep divergence. No monitor/DTC check anywhere in the traced destination
chains compares a filtered-leg value against an independently-raw-derived twin; every comparison
found is either against a literal/calibration constant, against the same function's own prior
filtered state, or occurs on a shadow pair that resolves before the gp-0x4f60 term is even added
in. This closes the "monitor-asymmetry (V27-class) audit for the 9 new lanes" item from the V52
completeness gap.

## Related
[[reference_accord_gp6809_zero_writers_confirmed_dead_gate]] — the E1-gate/gp-0x6b2c dead-path finding this session re-derived independently.
[[reference_accord_v48b_freeram_and_v850_encoding_formulas]] — the encoding formulas used for the byte scan.
