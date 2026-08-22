---
name: reference_accord_gp6c2c_gp6b26_fun36c12_chain_and_v106_gate1
description: "FUN_00036c12 is gp-0x6b26's sole producer (RULE 11's monitor target) -- exact address map, and gp-0x6b26 is ITSELF shadow-lockstep paired to gp-0x4cd0 (a SIXTH pair beyond the kit's known five). gp-0x6c2c (already an EMA-filtered signal, not raw) fans out to 4 consumers, gp-0x6b26 to 3 -- both wider than the naive gp-0x6c2c->gp-0x6b26->FUN_0003aa2c chain. GATE-1 assessment for a V106 stateful-filter cave: a RULE-11-safe hook point exists at 0x36c1a/0x36cca, but the CLASS (stateful insertion into a hot 1kHz function) has ZERO safe precedent in this kit -- every flown cave is a read-only tap at one site (0x55C0E/0xC4B34)."
metadata:
  type: reference
---

# gp-0x6c2c / gp-0x6b26 / FUN_00036c12 -- full chain, GATE 1 for a V106 filter cave

2026-08-22, `tq-lowpass` subagent, GATE-1/hook-inventory task for a proposed V106 highpass/biquad on
`gp-0x6c2c` reshaping `gp-0x6b26`'s authority. Fresh Ghidra decompile + disasm, `code.bin` stock.

## FUN_00036c12 IS gp-0x6b26's producer [EVIDENCE, disasm-exact]

```
0x36c1a  ld.h  -0x6c2c[gp],r9        ; read gp-0x6c2c (see below -- already Honda-EMA-filtered)
0x36c22-0x36c2c                      ; range-validity gate on r9 -> r13 (0 if out of [-0x7d00,0xfa01))
0x36c34-0x36cba                      ; speed-keyed LERP (axis gp-0x6a5e, voted vehicle speed) -> r12,
                                      ; a friction/inertia SCALE factor (fallback tp+0x740a/0x740c)
0x36cbe  mulh  r12,r13                ; r13 = high(r12*r13)
0x36cc0-0x36cca  movea/sar/mul/sar    ; r6 = ((r13>>6) * 0x111) >> 18          <- CANDIDATE VALUE
0x36ccc-0x36ce2  cmp/ble/subr/cmp/bge ; CLAMP r6 to +-cal(tp+0x507e)
0x36ce4  ld.h  -0x6b26[gp],r9         ; shadow-pair READ
0x36ce8  ld.h  -0x4cd0[gp],r11        ;
0x36cec  cmp r11,r9 / bne 0x36cfa     ; mismatch -> FUN_0006b9fa (resync)
0x36cf0  st.h  r6,-0x6b26[gp]         ; THE WRITE -- exact address RULE 11 (BUILD-LINEAGE.md) cites
0x36cf4  st.h  r6,-0x4cd0[gp]         ; shadow write
```

**`0xC407E` = `tp+0x507e`, confirmed exactly** (tp=0xBF000, 0xBF000+0x507E=0xC407E). `FUN_00036d74`
(the RULE-11 monitor) decompiled fresh: `fVar3 = gp-0x6b26 * 0.0009765625; if (fVar3>0.5 || fVar3<-0.5)
FUN_000462e6(0x39bc,...)` = `|gp-0x6b26| > 512 -> DTC 0x1d`, matching RULE 11 to the bit -- independently
re-derived, not just relayed.

**Both `FUN_00036c12` and `FUN_00036d74` run back-to-back inside `FUN_0002214a` (task 1, 1kHz) gated on
`uVar4 = uVar2 & 0x830` (states {4,5,11}).** Road-reachable states are {4,11}
([[accord-state4-cadence-refuted-state-is-sticky]]), both inside 0x830 -> **gapless 1kHz on every normal
drive.**

## 🛑 gp-0x6b26 is ITSELF shadow-lockstep paired to gp-0x4cd0 -- a SIXTH pair

Beyond the five in [[reference-accord-fun45a20-monitor-and-shadow-lockstep-pairs]] (which was a SCOPED
sweep of 5 seed addresses, not exhaustive -- don't cite "five" as a ceiling). Guarded at `0x36ce4-0x36cfe`
above, immediately before the write. **Writing gp-0x6b26 without its shadow desyncs the pair -> hard
fault via `FUN_0006b9fa`.** Any cave that stores to gp-0x6b26 directly (rather than feeding a value
through Honda's own 0x36ccc-0x36cfe unmodified) must replicate BOTH the clamp and the shadow-store, or
avoid writing gp-0x6b26 at all.

## gp-0x6c2c is NOT raw -- it's already an EMA, and it fans out to 4 consumers

Producer `FUN_00041464` (also task 1, mask `0xd30`={4,5,8,10,11}, gapless on {4,11}): two independent
one-pole EMAs, `y[n] = y[n-1] + ((x[n]-y[n-1])*alpha)>>shift`, state in **`gp-0x35a0`** (Q6, alpha
`cal(tp+0x50dc)`=`0xC50DC`) and **`gp-0x35a4`** (Q7, alpha `cal(tp+0x50da)`=`0xC50DA`), each further
`>>9` before storing to **`gp-0x6c2c`**/**`gp-0x6c2e`** respectively. **A "highpass on gp-0x6c2c" is a
highpass CASCADED after an existing Honda low-pass** -- whoever specs the filter needs `0xC50DC`'s actual
value to know the existing corner before choosing a highpass corner (not read this session).

Raw census (`search_instructions`, 8 hits, NOT yet cross-checked with a raw Python LE scan -- flagged
open): 2 writers (`FUN_00041464`@`0x4184e`/`0x41ac2`, mutually exclusive normal-vs-fault-sentinel `0x7FFF`
branches) and **4 independent reader functions**:
- `FUN_00036c12`@`0x36c1a` -- ours, above.
- `FUN_000428d4`@`0x428fa`/`0x4292c`/`0x42968` -- **the OSCILLATION DETECTOR**, 3 reads.
- `FUN_00071272`@`0x71378` -- unexamined this session.
- `FUN_0007b022`@`0x7b1a2` -- **the function that ALSO guards the `gp-0x4f64`/`gp-0x448a` governor-ceiling
  shadow pair** (see this agent's own `reference_accord_gp4f64_governor_ceiling_chain_and_v41_force_proof.md`).
  ⇒ gp-0x6c2c's content may indirectly reach the governor ceiling. NOT traced this session.

⇒ **Reshaping the shared RAM cell gp-0x6c2c touches all four.** Reshaping only what `FUN_00036c12` sees
(hook at `0x36c1a`, filter the LOCAL register r9, leave the gp-0x6c2c cell itself untouched) touches only
the friction/inertia path -- a materially smaller, better-bounded change.

## gp-0x6b26 fans out to 3 consumers, not 1

Raw census (`search_instructions`, 7 hits, 2 are false-positive branch-target text collisions in an
unrelated function `FUN_0006b162`@`0x6b25a`/`0x6b25e`, verified excluded): 1 writer (`0x36cf0`), 1
shadow-check read (`0x36ce4`), **3 independent downstream readers**:
- `FUN_00036d74`@`0x36d78` -- the RULE-11 monitor.
- **`FUN_00038148`@`0x3815c`** -- **Path-2 lane weights, a SECOND aggregator** distinct from
  `FUN_0003aa2c`. Not mentioned in the operator's own "gp-0x6c2c -> gp-0x6b26 -> FUN_0003aa2c" framing.
- `FUN_0003aa2c`@`0x3ac98` -- confirmed exact match to the address named in the brief that spawned this
  trace.

## GATE-1 verdict for a V106 stateful filter cave

**A RULE-11-safe hook point exists**: `0x36c1a` (read of gp-0x6c2c) or right after `0x36cca` (post-scale,
pre-clamp) -- filter the LOCAL register value, leave `0x36ccc-0x36cfe` (clamp + shadow-store) byte-for-
byte untouched. Structurally cannot trip the interlock or desync the new shadow pair, because Honda's own
bounding logic still runs unmodified on whatever the filter outputs.

Register liveness at `0x36cca` [BELIEF, manual disasm trace, NOT a pcode sweep]: `r7`, `r9` dead by
inspection; `r6` (holds the candidate) and `r16` (the clamp limit) are live and must be preserved/produced
correctly.

Candidate filter-state RAM: reuse `FUN_0003b66a`'s five pre-vetted W1R0 32-bit cells (`gp-0x6d08`/
`gp-0x6d04`/`gp-0x6d00`/`gp-0x6de8`/`gp-0x6de4`, see [[reference-accord-gate1-write-only-diag-taps-are-the-best-cave-ram]]
-- same task-1 context). **Refinement**: if `FUN_0003b66a`'s block runs BEFORE `FUN_00036c12`'s in the
same tick (BELIEF, not independently re-confirmed this session), a cave hooked in `FUN_00036c12` can
simply overwrite the cell after Honda's harmless dead-write, with no need to neutralize Honda's writer
(cheaper than that memory's own "nop the writer" suggestion).

**🛑 The class has zero safe precedent.** Every cave that has ever flown clean in this kit is a
READ-ONLY tap at ONE site (`0x55C0E` inside `FUN_00055a98`, the 100Hz CAN-TX chain -- NOT task 1), using
only r6/r7, writing only one telemetry byte, allocating NO persistent state. The one time this kit
considered even a READ-ONLY insertion into a hot 1kHz function (`FUN_000352b4`, structurally the same
risk class as `FUN_00036c12`), the orchestrator REJECTED it, citing "code caves are this kit's only
bricking class" and "cleared only by manual spot-check" (see
`reference_accord_v103_byte4_free_bits_and_clip_flag_cave_design.md`, Round 5). **V48B -- bricked -- is
the nearest precedent for a stateful filter inserted into an always-on loop.**

## Open items, explicit
1. Raw Python LE byte-scan cross-check on gp-0x6c2c/gp-0x6b26 census (only `search_instructions` run).
2. `FUN_00071272`'s use of gp-0x6c2c -- unexamined.
3. `FUN_0007b022`'s use of gp-0x6c2c and whether it reaches gp-0x4f64 -- unexamined.
4. Full pcode liveness sweep at `0x36c1a`/`0x36cca` (only manual spot-check done).
5. `FUN_0003b66a`-before-`FUN_00036c12` same-tick ordering -- not independently re-confirmed.
6. `cal(0xC50DC)`/`cal(0xC50DA)` values -- gp-0x6c2c's own existing EMA corner, unread.
7. GATE 2 (closed-loop/transient stability of the proposed filter itself) -- not attempted; this is
   dynamics analysis, a different kind of work than code-path tracing.

Related: [[reference_accord_v90_cave_gate1_census_and_hook_critical_section]],
[[reference_accord_crc_block_lookup_and_cave_hook_template]],
[[reference_accord_v103_byte4_free_bits_and_clip_flag_cave_design]],
[[reference-accord-fun45a20-monitor-and-shadow-lockstep-pairs]],
[[reference_accord_gp4f64_governor_ceiling_chain_and_v41_force_proof]]
