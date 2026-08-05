---
name: reference_accord_fun757a2_torque_model_and_lerp6_cluster
description: NEW function discovered below gp-0x6b98 — FUN_000757a2, a huge (~8KB) 1kHz float torque-model/estimator run under the aggregator state-gate (mask 0xc30), sandwiched by the SAME shadow-checksum pair (FUN_00071042/FUN_00071166) that guards FUN_00071272. Converts gp-0x6b98 to float (Q10/1024), contains a 6-branch shared-index LERP cluster (candidate ripple/sector table, index NOT identified), and terminates by writing the confirmed CAN427 motor-torque telemetry cell gp-0x4f74 plus 3 sibling cells. Does NOT feed FUN_00071272 directly (its main scratch cell gp-0xb4 has 0 accesses inside the FOC core).
metadata:
  type: reference
---

# FUN_000757a2 — a torque/current model function below gp-0x6b98, previously unmapped

Found while chasing the open "Iq/Id reference bridge" item from
[[reference_accord_foc_inner_current_loop_architecture]]. Not the bridge (see Negative result below),
but a genuinely new, safety-critical, previously-undocumented piece of the torque→motor pipeline.

## Identity and dispatch (EVIDENCE)

`FUN_000757a2` `[0x757a2, ~0x7ab00+]` — one of the largest functions in the image (comparable to the
FOC core `FUN_00071272`), single self-contained body, calls out only to `FUN_0006b9ee` (shadow-fault
handler) and the `FUN_000825xx` telemetry-logger cluster (same helpers `FUN_00071272` uses).

Called from `FUN_0006bcb2` (the 1kHz `w_steer_control_task` phase dispatcher), under **mask `0xc30`**
— the confirmed **aggregator** state mask (state ∈ {4,5,10,11} per
[[accord-gp67fa-state-gate-on-assist-chain]]). The exact call sequence in that mask's block:
`FUN_0006964c(2)` → `FUN_00071166()` → **`FUN_000757a2()`** → `FUN_00071042()` →
`FUN_00070a98(3)` (the torque-delivery consistency monitor / DTC 0x26) → `FUN_0007d16a(4)`.

`FUN_00071166` and `FUN_00071042` are NOT more math — they are a matched **pre/post 24-byte checksum
pair** over `gp+0x368..0x378` (shadow cell `gp-0x4f9c`/`gp-0x449c`, mismatch → `FUN_0006ce7c(0x16)`,
a DTC-0x16-class fault call) — **the identical safety pattern** (`FUN_000711f8`/`FUN_000710d4`) that
sandwiches the FOC core in the ADC ISR. **`FUN_000757a2` is treated as equally safety-critical.**

## What it computes (EVIDENCE, disasm + decompile)

Entry: `0x7580c ld.h -0x6b98,gp,ep` → `cvtf.ws` → `×(1/1024)` (movhi `0x3A80,r0` = float bit pattern
for 2^-10) — **the torque command, Q10 → float**, conditionally substituted with `gp-0x6b52` under a
`tp+0x74bf`-byte + `gp-0x67af`-flag gate (mirrors the same conditional-substitution shape seen
elsewhere in this firmware). Stored to `gp-0xB4` (`unaff_gp[-0x2d]`), which is then read/written
**42 times total across the function** as its primary working "commanded torque" register.

Draws on the **same `tp+0x60xx-0x66xx` motor-parameter cal block** (`0xC50D0`-`0xC56xx`ish) that
`FUN_00071272` reads (`&DAT_0000617e/617f/617d/6126/609a/642c/6418/641a + unaff_tp`, all inside
`[0xC5000,0xC5FFC)`) — corroborates that this is part of the same motor-model complex.

## A 6-branch shared-index LERP cluster (candidate ripple/harmonic/sector table — UNRESOLVED)

Near the tail (~line 4820-5015 of the decompile), the function runs a generic
binary-search-interpolation routine **six times** against six DIFFERENT short-array tables
(`unaff_gp[-0xa3]/-0x9e/-0xad/-0xa8/-0xb7/-0xb2`), all six sharing **the SAME fractional index**
(`fVar46`/`iVar18`, derived once from a value `fStack_b8 * 16.0`), each result scaled by its own gain
constant (`unaff_gp[-0xa1]/-0x9c/-0xab/-0xa6/-0xb5/-0xb0`) and written to six consecutive output
cells (`unaff_gp[0x10..0x15]`). **Six parallel same-index table lookups is the textbook shape of a
per-phase (3-phase ×2) or per-electrical-sector compensation/injection scheme** — a strong structural
candidate for the torque-ripple/cogging compensation the mission asked about. **NOT resolved this
session**: the index's physical identity (`fStack_b8`'s ultimate source — rotor angle vs. something
else) was not traced back; would need a dedicated follow-up narrowing `fStack_b8`'s producer.

## Final outputs — telemetry/CAN, not (confirmed) the FOC core's reference (EVIDENCE)

The function's last four writes, all in the `gp-0x4Exx/0x4Fxx` telemetry-staging neighborhood:
- `gp-0x4f74` = `uVar41` (a rounded int16) — **the CONFIRMED CAN 427 MOTOR_TORQUE source** per
  [[reference_accord_can427_source_is_gp4f74_not_gp6b98]]. **This settles that memory's open
  question of who produces it: `FUN_000757a2`.**
- `gp-0x4EA4`, `gp-0x4F5C`, `gp-0x4F48` — three sibling int16 writes, not previously catalogued.
  Plausible candidates: estimated Id/Iq or a second torque estimate for the consistency monitor
  `FUN_00070a98` that runs immediately after it under the same mask — **not confirmed**.

## Negative result — this is NOT the Iq/Id bridge into `FUN_00071272`

Exhaustive `search_instructions` scan for `-0xb4, gp` (the function's main scratch cell): **all 42
hits are inside `FUN_000757a2` itself; zero inside `FUN_00071272` `[0x71272,0x75717]`.** The actual
cell(s) that hand a converted reference from this 1kHz aggregator-gated stage into the 4kHz FOC ISR
core remain **unidentified** — candidates not yet checked: `FUN_0006964c` and `FUN_0007d16a`, the two
still-untraced siblings in the same `0xc30` dispatch block.

## Open items
1. `fStack_b8`'s producer (the 6-LERP cluster's shared index) — needed to settle the ripple/sector
   hypothesis.
2. The 3 unnamed output cells `gp-0x4EA4/0x4F5C/0x4F48`.
3. `FUN_0006964c` and `FUN_0007d16a` — untraced siblings in the same dispatch block; either could be
   the real bridge to `FUN_00071272`.
4. Whether `FUN_00071272` reads a torque/current reference via `tp`-relative or a struct-indirect (ep
   register from another table) path not caught by the `-0x6b98,gp` / `-0xb4,gp` literal scans.

## Related
[[reference_accord_foc_inner_current_loop_architecture]] — the FOC core this function does NOT
directly feed (bridge still open).
[[reference-accord-below-gp6b98-foc-delivery-path-swept]] — this function sits in the same
`[0x60000,0x84000)` FOC region swept there but was not individually examined in that pass.
[[reference_accord_can427_source_is_gp4f74_not_gp6b98]] — its producer question is answered here.
