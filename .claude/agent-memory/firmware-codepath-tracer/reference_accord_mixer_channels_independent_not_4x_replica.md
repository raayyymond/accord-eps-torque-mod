---
name: reference_accord_mixer_channels_independent_not_4x_replica
description: CORRECTS reference_accord_mixer_lkas_source_chain.md's "4 identical channels replicate gp-0x62f8[0]" model -- m_motor_cmd_distribute_clamp (FUN_00025c32) has 10 distinct callers, one per channel 0-9, each independently sourced. RESOLVED 2026-08-05 follow-up: channels 2/4/5/9 (role-5, gp-0x3d8c/gp-0x62c8 sum) are BASE ASSIST (torque-sensor + angle derived, confirmed by decompiling all three producers) -- NOT LKAS, a clean structural kill. LKAS reaches the motor via a SEPARATE accumulator in the SAME mixer function: gp-0x62b0[ch] (gated by tp+0x5118, byte-confirmed all-1/ungated) -> gp-0x3d88 -> gp-0x6b4c. Channel 1 (arb/LKAS, role-0) passes through to this second accumulator even though role-0 zeroes its role-5 contribution. V14's road-tested result is fully reconciled, no ledger correction needed.
metadata:
  type: reference
---

2026-08-05, team-lead mission "mixer headroom + the 20.9Hz gain peak" (grind #1 saturation hypothesis).
Program: code.bin (stock). This corrects a load-bearing error in
[[reference-accord-mixer-lkas-source-chain]] (2026-05-26) that the whole "4x2048 vs rail 8192" headroom
argument was built on.

## The old claim, and why it's wrong [EVIDENCE]

Old memory: "Switch case 5: ... r10 = ld.h @(gp-0x62f8[0]) (NOT channel-indexed; always reads slot 0)
-> gp-0x62c8[ch] = gp-0x62f8[0] for ch 2,4,5,9." I.e. 4 identical channels replicating ONE value.

**Fresh check**: `search_instructions(function=FUN_00026c80, operand_pattern="62f8")` returns exactly
**ONE hit**: `0x26d12 movea -0x62f8,gp,r11` — a single base-pointer setup. The mixer's 11-channel loop
increments `puStack_118` (initialized to this base) once per iteration in lockstep with every other
per-channel array pointer (role-table `tp+0x5124[ch]`, `gp-0x6298[ch]`, etc.), so case-5's
`uVar18 = *puStack_118` reads **`gp-0x62f8[ch]`, channel-indexed** — confirmed at the raw-instruction
level, not just decompile pointer arithmetic (which is the known danger zone, see
[[feedback-decompile-first-then-assembly]]).

`FUN_00025c32` (`m_motor_cmd_distribute_clamp`) writes `gp-0x62f8[ch] = clamp(param_1+4, ±0x2800)`
where `ch = param_1[0]` — genuinely per-channel, confirmed by its own decompile (e.g. the mode-1 default
branch: `*(short *)(unaff_gp + -0x62f8 + iVar11) = sVar24;` with `iVar11 = channel*2`).

## The 10 callers and their channel indices [EVIDENCE, disassembled every call site]

`get_xrefs_to(0x25c32)` returns exactly 10 call sites. Disassembled each (`mov 0xN,rX` immediately
before `sst.b rX,0x0,ep`):

| ch | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| caller addr | `FUN_0002e52e` | `FUN_0002b422` | `FUN_0003405a` | `FUN_0002c246` | `FUN_00023ad2` | `FUN_00023fe2` | `FUN_0003aff4` | `FUN_0003a8a8` | `FUN_0002caa2` | `FUN_000339cc` |
| call site | `0x2e618` | `0x2b53e` | `0x34212` | `0x2c374` | `0x23bd6` | `0x24176` | `0x3b25c` | `0x3a972` | `0x2cbe6` | `0x33b5c` |

Channel 10 has no caller found (stays at reset default, unwritten in normal operation). **⇒ 10 of 11
channels are independently sourced by 10 different functions — the "4 identical replicas" model is
FALSE.**

## Channel 1 = the arb/LKAS path, and it maps to a ZEROED mixer role — unresolved

`FUN_0002b422` = `m_steer_torque_limit_and_pack` (the function that clamps `gp-0x6b3c` by `tp+0x71b2`,
per [[reference-accord-mixer-lkas-source-chain]]). Disassembled its call site precisely:
```
0x2b522: mov 0x1,r10        ; channel = 1
0x2b526: sst.b r10,0x0,ep   ; struct[0] = 1
0x2b52c: sst.h r12,0x4,ep   ; struct[4] = r12 = the clamped arb value (same reg feeding gp-0x6b3a)
0x2b53e: jarl FUN_00025c32
```
So **`gp-0x62f8[1] = clamp(clamp(gp-0x6b3c, ±tp+0x71b2), ±0x2800)`** — channel 1 carries the arb/LKAS
command, exactly as the old memory believed, but at **index 1, not index 0**.

**But the mixer's role table `0xC4124` (=`tp+0x5124`) = `(0,0,5,0,5,5,0,0,0,5,0)` — index[1] = 0.** Role
0 in the mixer explicitly zeroes the channel's contribution to the summed output (`*puVar41 = 0` in the
decompile, the `gp-0x62c8[ch]` write for the default/role-0 branch). **⇒ On this trace, channel 1's real
arb/LKAS content never reaches the mixer's 4-channel sum (`gp-0x3d8c`, the accumulator that feeds
`FUN_00042ac6` at the end of the mixer).**

This directly contradicts the **road-tested** V14 result (raising `tp+0x71b2` 512->1024 alongside
`tp+0x746c` 891->1782 doubled delivered torque). Possible resolutions, none confirmed:
1. V14's doubling is fully attributable to the `tp+0x746c` arb-gain raise; the `tp+0x71b2` clamp raise
   was confounded and never load-bearing for that specific result.
2. LKAS reaches the motor via a completely different path than this mixer (the mixer may serve a
   different, non-LKAS torque-mixing role — e.g. base-assist/motor-current blending — and
   `reference-accord-mixer-lkas-source-chain`'s whole causal chain may need re-deriving from scratch).
3. Some other channel (2,4,5,9 — the true role-5 summed channels) ALSO carries an LKAS-derived value via
   a path not yet found.

## The 4 real (role-5) summed channels do NOT touch arb or LKAS setpoint — checked directly

`search_instructions` scoped to each of `FUN_0003405a`(ch2), `FUN_00023ad2`(ch4), `FUN_00023fe2`(ch5),
`FUN_000339cc`(ch9) for operand patterns `6b3` (catches `gp-0x6b3c`/`gp-0x6b3a`/`gp-0x6b38` etc.) and
`69ae` (LKAS setpoint): **zero hits in all four**, each function only 122-211 instructions (not a
coverage gap). Their actual sources (the register moved into `sst.h rX,0x4,ep` — `r9`/`r11`/`r12`/`r10`
respectively) were NOT traced back to origin this session — that is the single most important next step.

## RESOLVED 2026-08-05 follow-up — the puzzle fully closed

Decompiled all three role-5 producers fresh: `FUN_00023850`(ch4) is a float PID on `gp-0x6bde`/
`gp-0x6bdc`/`gp-0x6bf0`/`gp-0x6b96`; `FUN_00033d10`(ch2, also writes ch9's gate sibling `gp-0x6b76`)
reads `gp-0x4f60` (the torque sensor) directly; `FUN_0002eda8`(ch9, already known in this kit's memory
index as "lane9 raw torque command path") is a mode-selected (`gp-0x674f`), CORDIC-shaped angle
interpolation (`0x3243F7`≈π·2^20-style constants) combined with `gp-0x4f60`. **None touch `gp-0x6b3x`
(arb) or `gp-0x69ae` (LKAS setpoint) — confirmed BASE ASSIST (driver-torque + angle -> motor assist),
structurally unrelated to LKAS. Clean kill: the role-5/`gp-0x3d8c` sum is not the LKAS delivery path,
full stop.**

**LKAS's real path, found in the SAME mixer function**: it computes a SECOND, parallel accumulator every
iteration — `gp-0x62b0[ch]`, summed into `gp-0x3d88` when `tp+0x5118[ch] != 0`. **Byte-read `0xC4118`
(=`tp+0x5118`) this session: `01 01 01 01 01 01 01 01 01 01 01` — all 11 channels always included,
effectively ungated.** Mode-5 (role-5) channels explicitly **zero** `gp-0x62b0[ch]`
(`*puVar35 = 0`); mode-0 (role-0) channels **pass `gp-0x62f8[ch]` straight through**
(`*puVar35 = uVar18`). Channel 1 (arb/LKAS, role-0) therefore reaches `gp-0x3d88` -> **`gp-0x6b4c`**
even though its role-5 (`gp-0x62c8`) contribution is zero. `gp-0x6b4c` then feeds
`FUN_0003aa2c`'s aggregator exactly as `[[reference-accord-mixer-lkas-source-chain]]` and
`[[reference-accord-gp6b4c-lane-chain]]` already had it — **their DESTINATION was right all along; only
the "case-5 sum" belief about the intermediate mechanism was wrong.**

**V14 fully reconciled — no ledger correction needed.** `tp+0x71b2` genuinely reaches the motor via
`gp-0x6b4c`, so V14's doubling (raising `tp+0x71b2` AND `tp+0x746c` together) is attributable to both,
as originally believed.

**Still open**: `gp-0x3d88`/`gp-0x6b4c` sums `gp-0x62f8[ch]` over ALL SIX other role-0 channels too
(0,3,6,7,8,10 — callers `FUN_0002e52e`/`FUN_0002c246`/`FUN_0003aff4`/`FUN_0003a8a8`/`FUN_0002caa2`,
channel 10 uncalled/default). Whether those are zero/inactive in practice (making channel 1 the sole
real LKAS contributor to `gp-0x6b4c`, vs. genuinely summed with other torque content) was NOT checked
this session — the next hop if an exact LKAS headroom number is needed. `gp-0x6b4c`'s own clamp is
±0x2800 (10240), wider than the shaper's ±0x2000, so it is not the binding constraint either way.

## Related
[[reference-accord-mixer-lkas-source-chain]] — the memory this corrects (channel index 0->1, and the
"4 identical channels" model). Needs a full re-trace of channels 2/4/5/9's true sources before that
memory's causal chain can be trusted again.
[[reference-accord-shaper-fun42af8]] — downstream of this, the shaper's own ±0x2000 clamp is unaffected
by this correction (it clamps whatever the mixer/aggregator actually deliver, whatever that turns out
to be).
[[reference-accord-below-gp6b98-foc-delivery-path-swept]] — a separately-verified, reliable downstream
map that doesn't depend on this open item.
