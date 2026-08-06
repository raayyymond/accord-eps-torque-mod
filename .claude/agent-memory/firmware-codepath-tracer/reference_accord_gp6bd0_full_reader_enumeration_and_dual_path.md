---
name: reference_accord_gp6bd0_full_reader_enumeration_and_dual_path
description: FULL reader enumeration of gp-0x6bd0 (FUN_00034350's damper output) via 4 independent methods (search_instructions, disp16 byte scan, disp23 byte scan, LE32 literal scan) -- exactly 3 writers (all in FUN_00034350) and 5 readers. Reveals gp-0x6bd0 enters the gp-0x6b98 aggregator TWICE: once directly (±2048-bounded lane) and once indirectly via FUN_00038148(task1/1kHz)->gp-0x6b70->FUN_00037fe6->gp-0x6ad6->FUN_0003a382's P/I/D bias->gp-0x6ad4 (the aggregator's widest-bandwidth 0dB ±10240 lane).
metadata:
  type: reference
---

# gp-0x6bd0 full reader/writer census -- 2026-08-06, stock code.bin

Task: enumerate every reader of `gp-0x6bd0` (the FactorB×C×D×E×sign(rate) damper output from
`FUN_00034350`, clamped by FactorF ceiling `0xC77A0[mode]`). Extends
[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]] and
[[reference_accord_gp6b98_aggregator_full_lane_inventory]] with a closed, 4-method-verified census.

## Census [EVIDENCE, 4 independent methods agree exactly]

1. `search_instructions(operand_pattern="6bd0")` — 11 raw hits, 183,429 instructions scanned,
   `truncated:false`.
2. Raw Python disp16 4-byte-form byte scan (reg1=gp=r4, per-opcode LSB rules) — **8 hits, byte-identical
   addresses** to method 1 after excluding 3 branch-target-text false positives (`0x6bcf8`, `0x76bb6`,
   `0x76bc8` — all `be`/`bgt`/`bnh` whose OPERAND happens to contain the substring "6bd0" as part of an
   unrelated branch target `0x6bd04`/`0x76bd0`, not a gp-relative access at all).
3. Raw Python 6-byte extended-disp23-form scan (formula from
   [[v850e2-extended-disp23-encoding-solved]]) — **0 hits.**
4. LE32 literal scan for the resolved absolute address `0xFEDF1430` — **0 hits.**

**⇒ 8 real accesses, closed.** 3 writers (all inside `FUN_00034350`, the shadow-lockstep pair
`gp-0x6bd0`/`gp-0x4cf2`, `FUN_0006b9fa` on mismatch — unchanged from prior memory):
`0x34730`, `0x34744`, `0x34752`. **5 readers:**

| addr | function | role |
|---|---|---|
| `0x34726` | `FUN_00034350` (self) | pre-write shadow-consistency read (`sVar2` vs `gp-0x4cf2`) |
| `0x347bc` | `FUN_000347b8` | int/float clamp-consistency shadow check — see [[reference_accord_gp6bd0_shadow_faultpath_0x4179_0x417a]] |
| `0x38150` | `FUN_00038148` (task 1, 1kHz) | weighted-sum IIR feeding `gp-0x6b70` — the SECOND path, below |
| `0x3ac78` | `FUN_0003aa2c` (the `gp-0x6b98` aggregator) | THE direct torque-sum lane, ±2048-bounded |
| `0x1c114` | `FUN_0001bf88` | diagnostic/UDS byte-packer (records `gp-0x6bd0` into a diagnostic response buffer alongside `gp-0x6bbe`, `gp-0x6b98`, `gp-0x67fa`, `gp-0x6d78`) — NOT a control-path consumer |

## PATH 1 — direct aggregator lane [EVIDENCE, fresh disasm this session, `FUN_0003aa2c` @0x3ac78-0x3ac9c]

```
r9 = gp-0x6bd0
r12 = (|r9+0x800| < 0x1001) ? r9 : 0     ; ±2048 INCLUSIVE window, SILENT clamp-to-zero if exceeded (no fault call here)
... r12 added into the running total via plain `add`, no sign flip (matches
    [[reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse]]'s ADD-sign proof
    for the whole lane family)
```
Confirms [[reference_accord_gp6b98_aggregator_full_lane_inventory]]'s prior entry exactly (same ±2048
bound, same input-EMA fc=35.6Hz upstream inside `FUN_00034350` itself). **Given FactorF's ceiling caps
`|gp-0x6bd0|` at 512-1024 (mode-dependent, well inside this ±2048 window), this reject window is
architecturally unreachable in practice — it is a defensive band, not a live gate.**

## PATH 2 — NEW this session: an INDIRECT second entry into the SAME aggregator, via a different lane

`FUN_00038148` (task 1, 1kHz — confirmed via `get_function_callers`→`FUN_0002214a`, the DTC-0x18-monitored
task-1 dispatcher) reads `gp-0x6bd0` alongside `gp-0x6bbe`, `gp-0x6b4c`, `gp-0x6b4e`, `gp-0x6b26`, `gp-0x6b46`
— **the SAME set of aggregator-lane cells** — each weighted by its own byte cal (`gp-0x6bd0`'s weight =
`tp+0x73a0` = `0xC63A0`, **stock=1024/unity**, confirmed by prior memory's byte read
[[reference_accord_gp6bd0_seed_ruled_out_and_engagement_gates_found]]), sums them, passes through a
first-order IIR (`gp-0x374c` accumulator, coeff `tp+0x73ac`), and writes the result to **`gp-0x6b70`**.

`gp-0x6b70` is read by exactly one consumer, `FUN_00037fe6` (also task 1), which folds it (unity weight,
`tp+0x74b0`=1, confirmed byte-read in
[[reference_accord_fun3a382_gp6ad6_model_closure_and_bias_clamp_correction]]) into a 7-lane weighted sum
alongside `gp-0x6bc2`/`gp-0x6b60`/`gp-0x6b2a`/`gp-0x6bce`/`gp-0x6b6e`/`gp-0x6bbc`, gated by
`gp-0x67ab != 1` (open trigger, not resolved), speed-scaled by a LERP confirmed FLAT/no-op at stock cal,
clamped ±25600, and written to **`gp-0x6ad6`**.

`gp-0x6ad6` feeds `FUN_0003a382`'s P/I/D lane as the **bias term**: `ERR[n] = clamp(gp-0x4f60 - clamp(gp-0x6ad6,
±8192), ±0x2800)` — the damper contribution SUBTRACTS from raw driver torque before the P/I/D combine, whose
output `gp-0x6ad4` is then **ADDED** (confirmed, no sign flip) into the aggregator as its **widest-bandwidth
lane (0dB @20Hz, ±10240 bound)** — see [[reference_accord_gp6b98_aggregator_full_lane_inventory]].

**⇒ `gp-0x6bd0` reaches the SAME torque sum by two routes: PATH 1 direct (±2048, -1.2dB@20Hz, ADD) and
PATH 2 indirect-as-a-bias-on-driver-torque (unity-weighted at every hop on stock cal, then P/I/D-processed,
0dB@few-Hz rising to +42..+55° phase-lead@21Hz, ADD via `gp-0x6ad4`).** PATH 2 was not previously connected
to `gp-0x6bd0` specifically in this kit's memory (prior work on `gp-0x6ad6`/`gp-0x6b70` treated it as an
"LKAS-derived" term without tracing its OWN upstream producer `FUN_00038148` back to the damper). Both paths
existed on stock and V74/V75 alike (cal-only edits to FactorC do not touch either path's structure).

## Open
- `gp-0x67ab`'s trigger condition (whether PATH 2's 7-lane sum usually runs) — inherited open item, not
  re-investigated this session.
- Quantitative weight of PATH 2 vs PATH 1 at the operating point (both are unity-gain-ish on stock, but
  PATH 2 passes through an extra IIR at `gp-0x374c` + `FUN_00037fe6`'s own combine before reaching P/I/D) —
  not simulated end-to-end this session.

## Related
[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]],
[[reference_accord_gp6b98_aggregator_full_lane_inventory]],
[[reference_accord_fun3a382_gp6ad6_model_closure_and_bias_clamp_correction]],
[[reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse]],
[[reference_accord_gp6bd0_shadow_faultpath_0x4179_0x417a]] — the hard-fault-adjacent shadow check on this
same cell, found the same session.
