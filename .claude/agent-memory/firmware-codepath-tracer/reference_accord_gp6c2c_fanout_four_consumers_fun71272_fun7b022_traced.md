---
name: reference_accord_gp6c2c_fanout_four_consumers_fun71272_fun7b022_traced
description: "GATE 1 CLOSED, verdict SAFE. gp-0x6c2c fans out to FOUR reader functions (FUN_00036c12 friction lane -- the lever's target, FUN_000428d4 oscillation detector -- SAFE margin improves, FUN_00071272, FUN_0007b022), not three. FUN_00071272's flag byte gp-0x4b0 traced to a fixed record/log array (gp-0x26e8, 36B stride) -- not a command path. FUN_0007b022's chain traced to its true end: 4 of 5 possible output cells are DEAD (0 readers, triple-method), the 5th (gp-0x4f64 governor ceiling) is confirmed NOT fed by gp-0x6c2c in any of its 3 write branches. gp-0x6c2e (sibling EMA2, cal 0xC40DA>>7, separate state gp-0x35a4) is PRODUCER-LEVEL INDEPENDENT of cal(0xC40DC), proven from a fresh FUN_00041464 decompile; its 3 consumers (FUN_00034350/34a72/36f30, feeding Honda's stock damper gp-0x6bd0 and the K1 rate-lane gp-0x6bbe) are disjoint from gp-0x6c2c's 4. Two of this agent's own SSA-name-reuse misreads caught and corrected mid-trace, both documented."
metadata:
  type: reference
---

# `gp-0x6c2c` fan-out — FOUR consumers confirmed, two previously-unexamined ones now traced (a2gate task)

2026-08-27, `a2gate` task (team-lead brief: close GATE 1 on the `0xC40DC`/α2 fan-out for the V109
band-limit lever, see [[accord-c40dc-is-the-band-limit-lever]]). Fresh `code.bin` stock, GhidraMCP +
independent Python LE byte scan, both agreeing exactly.

## Census — 2 methods agree, 8 disp16 hits, 4 distinct reader functions [EVIDENCE]

```
writers (2, FUN_00041464, mutually exclusive): 0x4184e (normal), 0x41ac2 (|gp-0x4f50|>13000 fault sentinel -> 0x7fff)
readers (6 instructions, 4 functions):
  0x36c1a  FUN_00036c12   -- friction/inertia lane (the α2 lever's actual target)
  0x428fa/0x4292c/0x42968  FUN_000428d4   -- oscillation detector FSM, 3 reads
  0x71378  FUN_00071272   -- NOT previously named in the team-lead's brief as a consumer
  0x7b1a2  FUN_0007b022   -- NOT previously named in the team-lead's brief as a consumer
```
`get_xrefs_to` on the raw RAM address (0xFEDF13D4) returned **"No references found"** — a live
reproduction of the documented Ghidra gp-relative xref blind spot; only `search_instructions` + Python
found these. **Confirms, does not merely repeat, this agent's own 2026-08-22
[[reference_accord_gp6c2c_gp6b26_fun36c12_chain_and_v106_gate1]]**, which flagged the same 4-function
count via `search_instructions` alone and left the Python cross-check as an open item — that cross-check
is now done and agrees exactly.

⚠ NOT re-run this session: the 6-byte extended-displacement and register-indirect (`movhi -0x121,r0,rN`)
forms — inherited from [[reference_accord_v850_ldw_stw_lsb_encoding_and_fun36c12_pcode_liveness]]
(2026-08-22, same cell, 3-method census, 0 additional hits). BELIEF-carried-from-recent-EVIDENCE, not
independently re-derived today.

## FUN_00071272 — traced fresh, resolves an open item [EVIDENCE, fresh decompile 0x71272]

`0x71378`, unconditional top-of-function preamble: `*(float*)(gp-0x428) = (float)(int16)(gp-0x6c2c) *
1.5625e-05` (=2⁻¹⁶) — one term in a ~7-signal float staging block (alongside gp-0x4f0a/4f0c/6abe/etc).
Surrounding code does mod-2π angle wrapping (`x*0.15915494...*6.2831855`) — consistent with FOC
electrical-angle synthesis, not a filter. This is this agent's best candidate for the team-lead's
"FOC motor-model float term."

`gp-0x428` is touched 3 more times (lines ~346-350/802-806/2149-2153 of the decompile, all structurally
identical), each a **sequential MIN/bound-tightening comparator** (verified by truth-table, not
eyeballing): `held=*(gp-0x428); if (candidate<held || (candidate=-candidate, held<candidate)) { held =
candidate; *(gp-0x428)=held; flags|=0x10; }`. gp-0x6c2c's value only ever enters as the STARTING
candidate — never differentiated, integrated, or phase-processed inside this function.

Consequence traced to ground: `*(byte*)(gp-0x4b0) = bVar25` (accumulated flag byte: bit 0x10 from this
comparator, bits 0x2/0x1 from two unrelated ones). **`gp-0x4b0`'s own consumers were NOT traced this
session — concrete open item.** No `FUN_000462e6` (DTC dispatch signature used elsewhere in this kit)
appears anywhere in this function — not a direct DTC trigger.

Task context [BELIEF]: caller chain `FUN_0001492a -> FUN_0006404c -> FUN_00071272`; `FUN_0001492a` has
**no static caller found** — consistent with a dedicated task entry, NOT the confirmed 1kHz task-1
(`FUN_0002214a`). Plausibly the FOC/motor loop (cf. this agent's
[[reference_accord_gp4f50_4khz_to_1khz_decimation_and_polepair_derivation]], "FOC core=4kHz"). If true,
gp-0x6c2c (1kHz-updated) is read ~4x more often than it changes here. NOT verified this session.

## FUN_0007b022 — traced fresh, POSITIVELY RULES OUT reaching the governor ceiling [EVIDENCE]

Same giant function already on record ([[reference_accord_gp4f64_governor_ceiling_chain_and_v41_force_proof]])
as the `gp-0x4f64` cap-table axis writer via `gp-0x6ac0` — but gp-0x6c2c feeds a SEPARATE internal chain:

```c
// 0x7b1a2, unconditional:
fVar55 = (float)(int16)(gp-0x6c2c) * 0.015625;         // = 2^-6
// lines 287-293, a genuine clamp (verified by truth-table):
result = clamp(fVar55, -cal(0xC55A4), +cal(0xC55A4));  // cal(0xC55A4) = 500.0 float32, fresh-read
*(gp+0x104) = result;
```
Corpus max `|gp-0x6c2c|` ≈5,141-5,320 counts (this agent's own
[[reference_accord_gp6c2c_real_distribution_overflow_wall_not_binding]]) scales to ≈80.3-83.1 — **~6x
below this clamp.** Same "overflow wall not binding" pattern as the OTHER gp-0x6c2c ceiling already on
record, now independently confirmed a second time on a DIFFERENT clamp in a DIFFERENT function.

Chain continues: read back -> `abs()` -> scale by `*(gp+0x150)` -> round-and-saturate to int16 ->
binary-search into a calibration Y-table (same bracket-and-interpolate LERP idiom as the `0xC520C`
cap-table already on record) -> interpolated result SUBTRACTED from two earlier bias terms (`gp+0xfc`,
`gp+0x100`) -> feeds further products/comparisons through at least decompile line ~977, where this
session's trace stopped. **Final destination past line ~977 is UNRESOLVED — concrete open item.**

🛑 **Positively ruled out the scariest possibility, not merely left unconfirmed**: traced `gp+0x184` (the
ONLY cell feeding any of the 3 `gp-0x4f64` writes, each shadow-lockstep-protected against `gp-0x448a`)
back to its producer — a completely DIFFERENT chain (`fVar39`/`fVar44`, lines ~555-590), unrelated to
gp-0x6c2c. **Corrects/closes this agent's own 2026-08-22 flagged uncertainty** ("gp-0x6c2c's content may
indirectly reach the governor ceiling. NOT traced this session") in
[[reference_accord_gp6c2c_gp6b26_fun36c12_chain_and_v106_gate1]] — **it does NOT reach gp-0x4f64 via this
route.** ⚠ Trap encountered and self-caught while tracing this: Ghidra reuses the SSA name `fVar43` for
at least 3 unrelated logical values across this 1263-line function; matching by variable name alone
without checking line/program order nearly produced a false-positive link.

## Oscillation detector (consumer 3) — re-confirmed fresh, not re-derived [EVIDENCE for the bytes, citing
record for the mechanism — see [[accord-state671a-is-an-oscillation-detector]],
[[accord-gp6c2c-is-the-detector-input]], [[accord-gp671a-blast-radius-not-a-free-lever]]]

Fresh LE byte reads, `code.bin` stock: `cal(0xC620A)=12800` (T), `cal(0xC40DC)=22` (α2, the lever, virgin),
`cal(0xC643C)=37` (α0, shared, confirmed untouched). On-car V64 (route `35`) already showed this detector
NEVER arms during real severe grinding at today's α2=22 (1,158 reversals, zero arms). **Lowering α2 to 14
is SAFE, high confidence** — it cuts the 61-300Hz content that dominates this acceleration signal's peaks
by 20-35% while only raising 3-8Hz by 2-7% (much lower energy in a steering spectrum), so the detector
becomes structurally LESS reachable, not more.

## Shadow-lockstep / ASIL check [EVIDENCE for what was checked, explicit about scope]

`gp-0x6c2c`/`gp-0x6c2e` are NOT individually shadow-paired at the producer (cross-checked against
[[reference_accord_fun41464_rate_signal_hub_and_fun34350_damper_hook]]'s 6-pair list, which does not
include them). None of the 6 read sites show an *adjacent* shadow-check idiom (inspected each site's
immediate disasm context) — but no full pcode/CFG sweep was run to rule out a shadow-check further away;
residual gap, not a proof of absence. `FUN_0007b022` DOES shadow-protect `gp-0x4f64` itself, but (per
above) gp-0x6c2c doesn't feed that write, so it's irrelevant here. The scratch cells gp-0x6c2c flows
through in both newly-traced functions (`gp-0x428`, `gp+0x104`/`0x150`/`0x184`) are ordinary, unprotected
working RAM.

## Verdict delivered to team-lead — GATE 1 NOT closed today, real progress made

Friction lane = the lever's target (n/a as a safety question). Oscillation detector = SAFE. FOC candidate
(FUN_00071272) = BELIEF-grade SAFE (pure per-tick magnitude, no bandwidth/phase use found) but `gp-0x4b0`'s
consumers untraced. FUN_0007b022 (the 4th, previously unnamed consumer) = UNDECIDABLE at today's depth —
governor-ceiling reachability positively ruled out, but the chain's final destination past line ~977 is
open. **Two concrete next steps to actually close the gate**: (a) trace `gp-0x4b0`'s readers in
FUN_00071272, (b) finish FUN_0007b022's chain from line ~977 to its final write.

## ADDENDUM 2026-08-27 — `gp-0x6c2e`, the sibling EMA2, traced after a parallel agent (`closedloop`)
flagged it. PRODUCER-LEVEL PROOF it is independent of `cal(0xC40DC)`, not just a consumer-side inference.

### Census — triple method, fresh, 5 hits, disjoint from gp-0x6c2c's 8 [EVIDENCE]
```
writers (2, FUN_00041464, same two branches as gp-0x6c2c): 0x4185a (normal), 0x41ac6 (fault-sentinel 0x7fff)
readers (3 functions): 0x343b4 FUN_00034350, 0x34afe FUN_00034a72, 0x36f3a FUN_00036f30
```
Disjointness from gp-0x6c2c's set checked programmatically (empty intersection), not assumed — the
`disp|1` marker separates them (`0x93d2/0x93d3` for -0x6c2e vs `0x93d4/0x93d5` for -0x6c2c). Register-
indirect (667 `movhi -0x121,r0,rN` sites checked) and 6-byte extended-displacement (formula from
[[accord-gp4f60-two-encodings-enumeration-trap]]: `disp=(sext16(hw2)<<7)|((hw1>>4)&0x7F)`, hw0=0x0784/
0x07a4) both **0 hits for BOTH gp-0x6c2c and gp-0x6c2e** — closes the "not re-run this session" gap left
open above, now genuinely triple-method-clean for both cells.

### The decisive fact — fresh `FUN_00041464` decompile, byte-exact [EVIDENCE]
```c
uVar4 = cal(0xC40DA);                                              // tp+0x50da = 3, stock AND V108
iVar17 = ((iVar14-gp-0x35a0)*cal(0xC40DC))>>6 + gp-0x35a0; gp-0x35a0=iVar17;  // gp-0x6c2c's OWN state/cal/shift
iVar11 = ((iVar14-gp-0x35a4)*uVar4)>>7 + gp-0x35a4;        gp-0x35a4=iVar11;  // gp-0x6c2e's OWN state/cal/shift
gp-0x6c2c = (short)(iVar17>>9);  gp-0x6c2e = (short)(iVar11>>9);
```
The two EMA2 recursions run on **completely separate state cells** (`gp-0x35a0` vs `gp-0x35a4`), separate
cals (`0xC40DC` vs `0xC40DA`), different shifts (`>>6` vs `>>7`), sharing only the upstream `iVar14`
("acc"/d32) computed once before either update. **`cal(0xC40DC)` cannot move `gp-0x6c2e` at any K2 — a
producer-level proof, stronger than "no consumer reads both" (also true, see census).** Shared behavior
unrelated to the lever: both cells share the same upstream fault gate (`|gp-0x4f50|` out of range) — both
set to `0x7fff` and both EMA2 states zeroed together on that path only.

### What gp-0x6c2e feeds — traced past the census, not a bare count [EVIDENCE]
`FUN_00034350` **is the SAME function already on this kit's record as Honda's stock viscous damper**
([[reference_accord_fun41464_rate_signal_hub_and_fun34350_damper_hook]]) — gp-0x6c2e feeds one of its
LERP-key computations, reaching the damper's shadow-lockstep-protected final output `gp-0x6bd0`/
`gp-0x4cf2`. `FUN_00034a72` is a structurally near-identical sibling computation whose own final output
is `gp-0x6bbe` — a DIFFERENT signal already in this kit's index (the K1 rate-lane term). `FUN_00036f30`
is smaller, produces `gp-0x6bc2` with its own `0x7fff`-style sentinel on the same ~32000/25600 validity
ceiling gp-0x6c2c's consumers use (both siblings independently re-implement the same producer ceiling).
gp-0x6c2e itself has **no shadow-lockstep pair** (confirmed from the fresh decompile — unlike gp-0x6abc/
e/6ac0/2, which DO get full CRC-gated shadow reconstruction on mismatch in this same function, gp-0x6c2c/
6c2e get only a bare `0x7fff` on the fault path) — same "unprotected at the signal, protected one hop
downstream" topology as gp-0x6c2c -> gp-0x6b26. No `FUN_0004613e` plausibility monitor found on gp-0x6c2e
itself either — the ones nearby in `FUN_00034350`/`FUN_00034a72`/`FUN_00041464` check *other*, adjacent
signals (a 4-deep history buffer at `gp-0x6bc4..ca`; float reference channels at `gp-0x6d84..90`).

### Verdict this addendum delivered
Closed, not open. Does not merge into or change the two real open items above (`gp-0x4b0`'s consumers;
`FUN_0007b022`'s tail past line ~977) — it rules out one more way GATE 1 could have failed, on a strand a
parallel agent raised, not one this agent had missed on its own pass.

## ADDENDUM 2 2026-08-27 — BOTH OPEN ITEMS CLOSED. VERDICT: SAFE / SAFE / GATE 1 CLOSEABLE for
`cal(0xC40DC)` 22->14. Two of my own SSA-name-reuse near-misses caught and corrected in this pass.

### (a) `gp-0x4b0` (FUN_00071272's flag byte) -> a fixed record array, NOT a command path [EVIDENCE]
Census: 11 hits, all inside `FUN_00071272` (3 `st.b` writes, one per phase-block; 6 `movea` address-only;
1 `ld.bu` value read @`0x7532a`). Raw disasm at the read site: `FUN_0008253c(&ep_slot)` computes
`ep_slot = gp-0x26e8 + gp-0x2786*0x24` (a 36-byte-stride record array indexed by `gp-0x2786`, a state
selector `FUN_00082550` normalizes to 0/1 right after -- a 2-slot rotating log). gp-0x4b0's byte lands at
record-offset `0x10` (`sst.b r12,0x10,ep`) alongside 8 other real signals. No `FUN_000462e6` (DTC
dispatch) anywhere near it. **SAFE — record/log write, not torque command or fault raise.**
🛑 Self-correction: first read of the DECOMPILE (not disasm) made me think this byte was overwritten 10
lines later by a same-offset word write (`puStack_e8[1]=gp-0x3cc`, both looked like "+4"). Wrong — that
"+4" is POINTER ARITHMETIC scaled by the inferred 4-byte element type (`puStack_e8+4` = +0x10 bytes),
not raw bytes; the raw disasm resolves it cleanly (byte at ep+0x10, the word write at ep+0x4, no overlap).
Caught via `disassemble_bytes(dry_run=true)` before reporting, not left in the record.
Open, low-stakes: who reads the `gp-0x26e8` record array — not chased, doesn't gate the verdict.

### (b) `FUN_0007b022`'s chain past line ~977 -> 4 of 5 possible exits are DEAD, the 5th is CLEARED [EVIDENCE]
The tail (lines 1080-1259) is a 3-way branch on `uVar26`, each computing 5 outputs: `gp-0x4f52`,
`gp-0x4e98`, `gp-0x4f64`/`gp-0x448a` (shadow-protected governor ceiling), `gp-0x4f66`, `gp-0x4ea2`.
Triple-method output census (disp16 + 6-byte-extended + register-indirect, all agree): **`gp-0x4f52`,
`gp-0x4e98`, `gp-0x4f66`, `gp-0x4ea2` each have 0 readers anywhere in the image** — dead writes, one
per branch, all confirmed by all 3 methods. `gp-0x4f64` is the one live cell (8 readers, already on
record); traced all 3 of its write-branch sources precisely: branch 0/2 fed by `gp+0x184` (traced to an
unrelated chain at line ~590, per ADDENDUM 1); branch else fed by `gp+0x130`-derived `fVar45` (line
1217) — **NOT gp-0x6c2c in any of the 3 branches.** Verdict does not depend on resolving every internal
SSA hop of gp-0x6c2c's own sub-chain, because every possible EXIT is accounted for (4 dead, 1 cleared).
🛑 Self-correction, second one this session on this function: believed `fVar45` at decompile line 1072
was still the gp-0x6c2c-derived value from line 922. A precise line-ordered grep of every `fVar45`
mention between 1064-1230 shows it is REASSIGNED at line 1068 (`fVar45=fVar47`, sourced from `gp+0x130`,
unrelated) before that store. Caught by exhaustive grep-in-program-order, not by re-reading prose —
worth repeating as method: **when SSA-reuse is suspected, grep every mention of the variable in file-line
order and check each one for reassignment vs read; do not trust a remembered impression of the chain.**
Not fully resolved (explicitly not claimed): where the TRUE gp-0x6c2c value goes after the line 1064-1065
comparison (`if(fVar45<=fVar34) fVar34=max(0,fVar45)`) — irrelevant to the verdict per the output census.

Related: [[accord-c40dc-is-the-band-limit-lever]] (the lever this gate is for),
[[reference_accord_gp6c2c_gp6b26_fun36c12_chain_and_v106_gate1]] (the 2026-08-22 census this confirms and
extends), [[reference_accord_gp4f64_governor_ceiling_chain_and_v41_force_proof]] (the governor chain this
rules gp-0x6c2c OUT of), [[reference_accord_gp6c2c_real_distribution_overflow_wall_not_binding]] (the
corpus-max numbers used to size both clamps as non-binding).
