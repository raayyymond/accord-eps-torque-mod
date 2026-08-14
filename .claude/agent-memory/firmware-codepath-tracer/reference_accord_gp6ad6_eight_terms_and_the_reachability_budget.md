---
name: reference-accord-gp6ad6-eight-terms-and-the-reachability-budget
description: "The complete 8-term map of gp-0x6ad6 (the PID reference) written by FUN_00037fe6, with each term's OWN writer clamp read from the image. THREE of eight terms are identically zero (0, 2, 4) -- gp-0x6bbc and gp-0x6bce have NO WRITER AT ALL. Total reachable is 17,152 = 2.09x the 8192 threshold, NOT the ~12x that sizing against the zero-reject windows gives. On measured data the +-8192 clamp may never bind at all. Also: a speed-LERP multiply nobody named, a 16-bit wrap between terms 1 and 2, and 0xC6200's fifth consumer is a MOTOR FAULT THRESHOLD."
metadata:
  type: reference
---

# `gp-0x6ad6` — all eight terms, and the budget that is 8× smaller than the kit thought

Traced 2026-08-13, task `tracer-6ad6-terms`. Program `code.bin` (stock). Writer is
**`FUN_00037fe6` @`0x37fe6`–`0x38146`**. Every Python scan carries a **positive control**:
`gp-0x4f60` → 64 `ld.h` / 5 `st.h` four-byte + **7 six-byte at Ghidra's identical addresses**.

## 🛑🛑 THE HEADLINE — the zero-reject WINDOW is not the term's RANGE

The kit has been sizing these terms against their **admission windows** (±10240 / ±15360), giving
"~12× the threshold". That is a **GATE-3 error**. Every term's own writer clamps it far lower:

| # | cell | add addr | weight cal | **own clamp / reachable** | % of 8192 |
|---|---|---|---|---|---|
| 0 | `gp-0x6b4a` | `0x38002` (**NEGATED**) | *(implicit 1)* | **≡ 0** (`0xC616C`=0) | 0 % |
| 1 | `gp-0x6b6e` | `0x3803e` | `0xC64B1` | **±1024** (cal `0xC617E`) | 12.5 % |
| 2 | `gp-0x6bbc` | `0x38044`/`48` | `0xC64AF` | **≡ 0 — NO WRITER** | 0 % |
| 3 | `gp-0x6b70` | `0x38046`/`4e` | `0xC64B0` | ±8192 (cal `0xC6200`) | 100 % |
| 4 | `gp-0x6bce` | `0x38068`/`6e` | `0xC64AD` | **≡ 0 — NO WRITER** | 0 % |
| 5 | `gp-0x6b2a` | `0x38080`/`8a` | `0xC64B3` | **±1024** (cal `0xC61C6`) | 12.5 % |
| 6 | `gp-0x6b60` | `0x38094`/`9a` | `0xC64B2` | **±6144** (LERP Y `0xC66F8`, gain `0xC63C4`=1024 ⇒ ×1.000) | 75 % |
| 7 | `gp-0x6bc2` | `0x380ac`/`ae` | `0xC64AE` | **±512** (≤50 km/h) / ±768 @100 | 6.3 % |

All seven weight bytes `0xC64AD..0xC64B3` = 1. ⚠ **The weight→cell map is NOT in address order.**
**Total reachable = 17,152 = 2.09×, not ~12×.**

⭐ **AND THE CONSEQUENCE:** term 3's measured max is 3162 (14,289 frames). With the others at their
**clamps** (hard upper bounds): `3162 + 1024 + 1024 + 768 = 5,978 < 8,192`.
⇒ **With term 6 out, `|gp-0x6ad6|` cannot reach 8192 on measured data — the clamp never binds.**
Term 6's axis is **`gp-0x6bda`** (`0x362b2`), the detent, which
[[accord-return-centre-and-detent-dead-engaged]] measured at **duty 0.0000 over 75,227 engaged
frames**; its gate is `gp-0x67fe != 0` (`setfe` @`0x362c0` → `0x36332 bne` → 0).

## Terms 2 and 4 are writerless — verified THREE ways, not a tool zero
4-byte gp form, 6-byte extended form (`disp = (s16(hw3)<<7)|((hw2>>4)&0x7F)`, positive control
passes), and the `movea`-base route. The four `movea` bases near `gp-0x6bbc` (`0x34376`–`0x34386`)
feed `jarl 0x4613e`; **`FUN_0004613e` only DEREFERENCES them as sources** into a diag record at
`gp-0x6920` then `FUN_00016de6(0x1c,…)`. It writes nothing back.

## Two structural things nobody had named
1. **A SPEED-LERP MULTIPLY sits between the sum and the ±25600 clamp** —
   `0x38124 mul r12,r10,r0` / `0x38128 sar 0xa,r10`. Exact identity at stock (Y `0xC6ACA..0xC6AD8`
   all 1024, fallback `0xC6448`=1024) but a **live virgin multiplier on the reference**.
2. **16-BIT WRAP between terms 1 and 2**: `0x38048 add r9,r15` then **`0x3804c sxh r6`** truncates
   that pair to int16; every other term accumulates in 32 bits. Raising `0xC64B1`/`0xC64AF` to 2
   makes it wrap.

⚠ Terms 1, 5, 7 all write **`0x7FFF` on gate FAIL** — 32767 fails the ±10240 window ⇒ rejected to 0.
⚠ Term 7's speed gain `gp-0x69be` is **0 below ~30 km/h** ⇒ **term 7 is ZERO at creep.**
⚠ `gp-0x6b60`'s writer `0x36352` is in a region **Ghidra never analysed** — Python only.

## `0xC6200`: the fifth consumer is a FAULT THRESHOLD, and a global edit is SELF-CANCELLING
15 sites, 5 consumers. The long-unchased `0x39ff6` is in **`FUN_00039702`**, the motor-phase
plausibility monitor: `ld.hu 0x7200,tp,r9` → `0x3a00e cvtf.uws` ⇒ a **float threshold 8192/1024 =
8.0** gating faults into `gp-0x6924` / `FUN_000462e6(0x4377,…)`. Ghidra mangles it as
`FUN_000071fe + unaff_tp + 2` — **that is why it was never chased.**

🛑 **A global raise of `0xC6200` buys EXACTLY ZERO margin**: it clamps **term 3** (`FUN_00038148`)
and **the reference threshold** (`FUN_0003a382`) with the same cell, so the ratio is invariant —
full blast radius, no effect. **The only edit that changes anything is repointing the three PID
loads** (`0x3a7a2` hw2=`0x7200`; `0x3a7b2` and `0x3a7c4` hw2=**`0x7201`**, `ld.hu` keeps the `|1`)
to a spare cal — 6 bytes, in-place displacement, precedent = V57's `0xC646C`→`0xC6CD0`.

## The ±10240 error clamp is FOUR halfwords, editable in place
`0x3a7d2`, `0x3a7d6`, `0x3a7dc`, `0x3a7e0` (`addi`/`movea`, signed 16-bit, ceiling ±32767).
It sits **downstream** of the reference clamp ⇒ widening it does **not** restore
`∂/∂(gp-0x6b70)`, which dies upstream at `0x3a7b8`/`0x3a7c8`.

## Output path
`0x3a8a0 st.h r10,-0x6ad4[gp]` → **1 reader** `0x3aca8` in `FUN_0003aa2c`, entering the 11-term
aggregator at **unit weight, window ±10240**, → clamp ±10240 → `gp-0x6b94` **in shadow-lockstep with
`gp-0x4ce0`**. 🛑 Stores are at **`0x3acfa`/`0x3ad12`/`0x3ad20`** (the kit record's `0x3acf6`/`0x3ad0e`
are the compares).

## 🛑 UNRESOLVED — do not repeat the brief's claim
**`gp-0x67ab ≡ 0 STRUCTURALLY` is NOT confirmed.** Its one writer `0x2775c` copies **`gp-0x3d94`**
(shadow `gp-0x4c36`) — a propagated state byte. Terms 1–7 drop iff it equals **exactly 1**.
Next step: trace `gp-0x3d94`'s writers.

## Golden-model gap
`eps_chain_lanes.py:477–545, 642–738` carries `6ad6`/`6b70`/`6ad4`/`0xC64AD`/`0xC6ABA`/`37fe6` **in
comments only**, as a "7-lane sum". **Six of the eight terms are absent entirely**, as are their
writers, clamps, the speed-LERP multiply, and the PID internals.

Related: [[reference_accord_c6200_clamps_gp6ad6_inside_the_pid]] ·
[[accord-4x-gain-feeds-6b4c-not-term0-and-the-struct-offset-map]] ·
[[reference_accord_aggregator_is_unweighted_and_427_rectification_costs_4.9x]] ·
[[reference_accord_aggregator_zero_reject_window_map]]
