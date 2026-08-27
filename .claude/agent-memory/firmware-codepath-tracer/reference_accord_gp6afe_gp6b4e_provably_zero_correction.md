---
name: reference_accord_gp6afe_gp6b4e_provably_zero_correction
description: gp-0x6afe/gp-0x6b4e (the "LKAS overlay" final-summation term into the shaper, produced by FUN_00042ac6 <- FUN_00026c80's per-lane accumulator gp-0x3d8c <- array gp-0x62c8[0..10]) is PROVABLY, STRUCTURALLY ALWAYS ZERO on every build. CORRECTS memory/accord/firmware/accord-aggregator-reaches-motor-via-gp6acc-bridge.md's "CAN/arbitration term" label and reference-accord-shaper-fun42af8.md's "feed-forward / error correction addend" label.
metadata:
  type: reference
---

# gp-0x6afe / gp-0x6b4e are dead cells — always zero — traced 2026-08-11, `fw-return` task

Dispatched to hunt the operator's "return-to-centre suppressed by LKAS command" hypothesis. Team-lead's
brief named `gp-0x6afe`/`gp-0x6b4e` (via `FUN_00042ac6`) as "the LKAS overlay [that] reaches the motor."
Traced the producer chain fresh and found the opposite — this is a genuine correction, not confirmation.

## The chain [EVIDENCE, full disasm this session]

`FUN_00042ac6(param_1)`: `gp-0x6afe = param_1` (clamped to `0x7fff` only on wild out-of-range input).
Sole caller (`get_function_callers`): `FUN_00026c80` (the mixer). Call site `0x277f6`, parameter is
`r26 = clamp(gp-0x3d8c, +/-0x2800)` (computed at `0x2743e-0x27454`), which is ALSO stored (lockstep) to
`gp-0x6b4e` at `0x27458-0x2746a` — confirms the brief's "gp-0x6b4e ≡ gp-0x6afe bit-for-bit" claim, but
both are the SAME structurally-dead value.

`gp-0x3d8c` (written `0x27318`) = the running sum `r6`, accumulated over all 11 mixer lanes in the
per-lane loop (`0x271de-0x27304`) from array `gp-0x62c8[lane]` (base pointer `r28 = gp-0x62c8`, set once
at `0x26cc8`, incremented `+2`/lane at `0x2716c`).

## `gp-0x62c8[lane]` is always zero — two-method closure, same pattern as `gp-0x67ac` [EVIDENCE]

`gp-0x62c8` is populated inside `FUN_00026c80`'s OWN per-lane role-dispatch switch (`0x26d1a-0x2712e`),
selected by `tp+0x5124[lane]` (`0xC4124`, fresh byte-read this session `[0,0,5,0,5,5,0,0,0,5,0]`, matches
every prior census in this kit — only values 0 and 5 ever appear).

Scoped `search_instructions(function=FUN_00026c80, operand_pattern="r28")`, 15 hits, `truncated:false`,
adjudicated by role branch:

| role value (`0xC4124[lane]`) | write to `gp-0x62c8[lane]` (via r28) |
|---|---|
| 7 (`0x26d66`) | `r10` (real value, but sourced from a STACK param at `0x26d2e`, NOT the arb/LKAS chain) |
| 6 (`0x26d9c`), 4 (`0x26ee4`), 3 (`0x26f66`), 2 (`0x26fee`), 1 (`0x27080`), 0/default (`0x270d6`) | explicit `st.h r0,0x0[r28]` — **ZERO** |
| 5 | **no `[r28]` write anywhere in that case body** — leaves the cell untouched |

Role 7 is required to get a non-zero write, but **role 7 never appears in `0xC4124` on any build this
kit has produced** — same closed fact already used to prove `gp-0x67ac` (`gp-0x617c[i]`) unreachable in
[[reference_accord_gp67ac_reduced_branch_unreachable]]. Roles 0/1/2/3/4/6 (7 of 11 lanes, including lane
1 = the established LKAS lane) explicitly zero it every cycle. Role 5 (lanes 2,4,5,9) never writes it at
all — so its value is whatever boot left there.

**Boot closure**: `gp-0x62c8` = `0xFEDF8000 - 0x62C8` = `0xFEDF1D38`; `.data` boot source (per
[[reference_accord_app_ram_layout_and_boot_init_loops]]'s formula `flash[0x86260 + (addr-0xFEDF11B0)]`)
= `0x86260 + 0xB88` = `0x86DE8`. Fresh `read_memory(0x86DE8, 22)` = **all zero** (11 halfwords, covers
every lane).

⇒ **`gp-0x62c8[lane] = 0` for every lane, at boot and forever, on every build in this kit's history.**
`gp-0x3d8c` ≡ 0 ⇒ `r26` ≡ 0 ⇒ **`gp-0x6afe` ≡ `gp-0x6b4e` ≡ 0, always, structurally.**

## Consequence — corrects two prior memories

1. `memory/accord/firmware/accord-aggregator-reaches-motor-via-gp6acc-bridge.md` calls `gp-0x6afe` "CAN/arbitration term,
   validity-gated" in its final-summation formula `iVar45 = gp-0x6afe(...) + uVar34`. That formula is
   structurally correct but **`gp-0x6afe` contributes nothing** — the equation reduces to `iVar45 = uVar34`
   at every cycle, on every build. The "CAN/arbitration term" label was inherited from an earlier,
   unverified characterization and should be corrected/flagged.
2. `reference-accord-shaper-fun42af8.md` (this agent's own older memory) calls `gp-0x6afe` a
   "Feed-forward / error correction addend" — same correction applies.
3. There is **no second, independent LKAS injection point at the shaper's final stage.** The entire LKAS
   contribution to the delivered command flows through `gp-0x6b4c` (inside the 11-lane aggregator,
   alongside `gp-0x6b62`/return-centre) and through `gp-0x6b4a` (into `FUN_0003a382`'s PID reference
   `gp-0x6ad6` — a *different* aggregator lane, resonance, not return-centre). The "LKAS overlay reaches
   the motor as gp-0x6b4e≡gp-0x6afe" framing used in a prior session's brief is WRONG as a live-signal
   claim, though the bit-for-bit lockstep observation (both cells share one producer) is correct.

## Not yet checked

Whether `gp-0x6b4e` (as opposed to `gp-0x6afe`) has any OTHER consumer that matters even at a constant 0
— not swept this session, but a constant-zero cell is unlikely to be structurally interesting either way.

## Related
[[reference_accord_gp67ac_reduced_branch_unreachable]] — the identical two-method closure pattern
(role-7-never-fires + boot-zero) applied to a sibling per-lane array in the SAME mixer function.
[[reference_accord_gp6b4a_direct_lkas_term_and_v41_lineage_correction]] — the OTHER LKAS injection point
(`gp-0x6b4a`, into the PID reference), which IS live, unlike `gp-0x6afe`.
