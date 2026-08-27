---
name: accord-gp6afe-gp6b4e-are-always-zero
description: "gp-0x6afe (== gp-0x6b4e), long carried as 'the LKAS overlay that reaches the motor', is PROVABLY, STRUCTURALLY ALWAYS ZERO on every build — its source array gp-0x62c8[0..10] is written to literal zero or not written at all, and its .data boot initialiser is 22 bytes of zero. The shaper's final sum reduces to iVar45 = uVar34; there is NO second, independent LKAS injection at the final stage. Corrects two starred memories."
metadata:
  type: reference
---

# `gp-0x6afe` ≡ `gp-0x6b4e` ≡ 0, always — traced 2026-08-11

**[EVIDENCE]**, from a fresh trace of the producer, closed two ways.

## The chain

`FUN_00042ac6(param_1)` writes `gp-0x6afe = param_1` (clamped to `0x7fff` only if wildly out of
range). Its **sole** caller is `FUN_00026c80` (the 11-lane mixer), which calls it with
`r26 = clamp(gp-0x3d8c, ±0x2800)`.

`gp-0x3d8c` is a straight sum over all 11 mixer lanes of a per-lane array `gp-0x62c8[lane]`
(base pointer `r28 = gp-0x62c8`, confirmed by a scoped `search_instructions`, 15 hits,
`truncated:false`). The per-lane role dispatch reads `tp+0x5124[lane]` = `0xC4124`, byte-read as
**`[0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0]`**:

| role value | what is written to `gp-0x62c8[lane]` |
|---|---|
| 7 | `r10` — a real, computed value. 🛑 **role 7 NEVER appears in `0xC4124` on any build** |
| 6, 4, 3, 2, 1, 0 (default) | explicit `st.h r0, …` ⇒ **ZERO** |
| 5 | **not written at all** ⇒ retains its boot value |

**Boot (`.data`) source for `gp-0x62c8[0..10]`** — flash offset `0x86260 + (0xFEDF1D38 − 0xFEDF11B0)`
= `0x86DE8`, fresh `read_memory`: **22 bytes, ALL ZERO.**

⇒ **`gp-0x62c8[lane] = 0` for every lane, at boot and forever, on every build** ⇒ `gp-0x3d8c ≡ 0`
⇒ **`gp-0x6afe` ≡ `gp-0x6b4e` ≡ 0, always.**

This is the same two-method closure (deterministic re-derivation for the reachable roles + the boot
initialiser for the one untouched role) already used to prove `gp-0x67ac` unreachable.

## What it corrects

- 🛑 **`accord/firmware/accord-aggregator-reaches-motor-via-gp6acc-bridge.md`** labels `gp-0x6afe` a **"CAN/arbitration
  term"**. It is a dead cell. The shaper's final summation `iVar45 = gp-0x6afe + uVar34` reduces to
  **`iVar45 = uVar34`** ⇒ **there is NO second, independent LKAS injection at the final stage.**
- 🛑 **`reference-accord-shaper-fun42af8.md`**'s "feed-forward / error-correction addend" label, same
  cell, same correction.
- ⚠ It also corrected the **team-lead's own brief**, which named this cell as *"the LKAS overlay that
  reaches the motor"*. The agent traced the producer fresh and reported the opposite rather than
  working around it.

## What the LKAS contribution actually does

The entire LKAS contribution to the delivered command flows through **`gp-0x6b4c`** inside the 11-lane
aggregator (alongside return-centre), and through **`gp-0x6b4a`** into `FUN_0003a382`'s PID reference
— a *different* aggregator lane. See [[accord-gp6b4a-is-a-second-direct-lkas-term]].

⚠ **`gp-0x6b4e`'s WEIGHT is still 1024 and that fact is unaffected** — `0xC63A8` = 1024 is confirmed
at the exact cal address, as are all five of its siblings. A unity weight on a zero lane is still
zero; the weight claim and the liveness claim are independent and both were checked.

Source: `docs/traces/TRACE-2026-08-11-return-to-centre-gate.md` §3.3 ·
`.claude/agent-memory/firmware-codepath-tracer/reference_accord_gp6afe_gp6b4e_provably_zero_correction.md`
Related: [[accord-aggregator-reaches-motor-via-gp6acc-bridge]] ·
[[accord-gp6b4a-is-a-second-direct-lkas-term]] · [[accord-c616c-never-raise-driver-torque-relay]]
