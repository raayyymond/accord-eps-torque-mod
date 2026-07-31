---
name: reference_accord_boost_amp_series_question_corrected
description: CORRECTED trace -- both 0xD28DC (y1) and 0xD2888 (y4) reach gp-0x6bbe. y1 enters through a nonlinear path (multiply, then differenced against gp-0x6a56, clamped +-12000, gated by the 4-state ramp SM); y4 enters as a separate later multiplicative factor. Not a clean series product, but both live.
metadata:
  type: reference
---

**Supersedes the retracted `reference_accord_boost_amp_series_question_resolved_not_series.md`. Full
corrected trace of `FUN_00034a72`, credit to the operator's team-lead for catching the original error.**

## The y1 chain (`0x34be2`-`0x34cae`), following r25 (blended y1) forward correctly this time

```
r10 = LERP(gp-0x6ba6=amp, 0xD28DC-family via 0xCA4F4[mode])              y1_raw    [0x34b76-0x34be2]
r25 = old(gp-0x69bc) if raw<=old, else old + ((raw-old)*cal(0xCA06C[mode]))>>10    [0x34be4-0x34c02]
       -- the blend from reference_accord_boost_amp_blend_direction_and_d2000_block.md (rising-only)
r6  = gp-0x6986                                                                     [0x34c02]
r28 = clamp(r6, ·, 1024)  (cmovnc pattern: r28=r6 if r6<0x401 else 0x400)          [0x34c06-0x34c14]
r28 = (r25 * r28) >> 14              <-- THE >>0xe MULTIPLY, operands r25(y1-blended), r28(clamp(6986))
                                          [0x34c1c mulu, 0x34c26 shr 0xe]
r28 = r28 * cal_byte(0xCA40C[mode])                                                [0x34c2e]
r28 = r28 >> 7                                                                     [0x34c38]
r16 = LERP_friction(key=gp-0x6a10, bounds gp-0x6394/0x6382/0x6392/0x63a8-linked list) [0x34c20-0x34c86]
r28 = r28 * r16                                                                    [0x34c8c]
r28 = r28 * sign(gp-0x6a02)          (+1/-1 via cmovlt)                            [0x34c88-0x34c98]
r28 = -r28                                                                         [0x34cac]
r28 = r28 >> 10   =  "iVar13" (the y1-chain result)                                [0x34cae]
```

This `iVar13` then passes through the **4-state ramp state machine** (`gp-0x682e`, `0x34d40-0x34e8a`,
already on record elsewhere in this kit's memory as the assist ramp SM). In MOST states/transitions the
SM resets `iVar13 = 0` — but **not in all reachable paths**: state 1 with the ramp-permission flag
(`bVar10`) true falls through without resetting it, and one sub-branch of state 3 (`uVar5 < threshold &&
bVar10 && uVar5==uVar6`) jumps directly to `LAB_00034e8a` preserving `iVar13`. **So the y1-chain value
survives to the output in specific ramp-SM states, and is zeroed in others** — this is itself a real,
separate gating mechanism worth remembering (the y1 contribution is not merely "attenuated," it can be
fully gated OFF by ramp state, independent of index depth).

At `LAB_00034e8a`:
```
iVar30 = iVar13
if (gp-0x6a56 is within the window |sVar23+12000| < 0x5dc1):  iVar30 = gp-0x6a56   (re-read)
iVar13 = iVar13 - iVar30
iVar30 = clamp(iVar13, ±12000)          <- THIS is "angle_rate_delta" from the earlier (correct) trace
```
`iVar30` then enters the multiply at `0x34f20` exactly as previously documented:
`r13 = (cal(0xCA324[mode]) * iVar30) >> 7`, `r13 *= main_boost_curve_raw(0xCA154, key=gp-0x6a5e)`,
`r13 = clamp(r13>>10, ±cal(0xC7A58[mode]))`.

## The y4 chain — unchanged from the prior (correct) part of the trace

```
y4_raw = LERP(amp=gp-0x6ba6, 0xD2888-family via 0xCA23C[mode])                    [0x34f5e-0x34fc4]
y4 = slew_limit(y4_raw, prev=gp-0x69ba, rate=cal(tp+0xb06c, mode-indexed))          [0x34fc4-0x34fea]
   -- SAME rising-only blend shape confirmed at this site too
inner = (y4 * clamp(gp-0x6988, 0, 1024)) >> 10                                     [0x34fea-0x34ffe]
r13 = (r13 * inner) >> 14                                                          [0x35000-0x35008]
r13 = r13 * polarity                                                               [0x35010, mulh]
gp-0x6bbe = clamp(r13, ±ceiling(0xC7970[mode], key=gp-0x6a62 MAX voter))            [0x3507c-0x350c2]
```

## ⇒ Verdict: BOTH curves reach gp-0x6bbe. NOT a clean series product.

`gp-0x6bbe ∝ clamp( [y1-derived nonlinear term] − gp-0x6a56-ish, ±12000 ) × main_boost_curve × y4 ×
clamp(gp-0x6986)-ish × clamp(gp-0x6988)`, further gated by the 4-state ramp SM (which can zero the y1
term entirely in some states) and the plausibility/validity gates already on record. Team lead's original
"eps=0.165, marginally unstable" framing is closer to correct than the retracted "sub-threshold, y1 dead"
verdict — but the true composition is NOT literally `y1 * y4`; the intervening `- gp-0x6a56` subtraction
and ±12000/±`0xC7A58` clamps mean the two curves' contributions do not multiply cleanly, and the ramp-SM
gate adds a THIRD live/dead axis beyond index depth that the pump-depth table did not model. On-car
simulation of the literal arithmetic (not the clean-series approximation) is the only way to get a
trustworthy ε number now.

## gp-0x6986 / gp-0x6988 — producers and structural range (byte-scan confirmed sole producer)

Both cells are written **only** by `FUN_00026c80` (`0x26c80`-`0x27801`, one write site each: `0x27340`
for `gp-0x6986`, `0x27362` for `gp-0x6988` — confirmed via the same whole-image ST-opcode byte scan used
throughout this session). `FUN_00026c80` is called from `FUN_0002214a` (**RTOS task 1**, the
confirmed-~1kHz control task) — a different task from `FUN_00034a72`'s task 5, so these two producer/
consumer sides run on different (and for task 5, still-unconfirmed) rates.

Structurally: both are the **MAX-reduction over an 11-element array**, each element independently produced
by a per-slot state machine (state byte at `tp+0x5124+i`, states 0–7) that assigns either `0`, `0x400`
(1024, Q10 neutral/1.0), a raw per-slot input, or a `±0x2800`(±10240)-clamped derived value
(`slot_input * cal(tp+0x746a) >> 14`). Given `0x400` is the dominant/neutral value across most states,
**the natural operating range is `[0, 1024]` (Q10, ≤1.0)** — consistent with `FUN_00034a72` re-clamping
both to `[·,1024]` defensively before use, since the `±0x2800` path could in principle exceed that.
**Not resolved this session**: what the 11 channels/states physically represent (looks like an 11-way
gain-derate/failsafe voting scheme reusing "0x400 = no derate" as the default across most states, but the
per-channel state-byte semantics at `tp+0x5118`/`tp+0x5124`/etc. were not decoded). Flagging as open.

## 0xC9E9C blast radius — now corroborated by raw byte scan, not `search_instructions` alone

Independent Python scan of the whole 1,048,576-byte image for the literal 32-bit-LE value `0xC9E9C`
(any alignment): **exactly 1 hit, at `0x34508`** (inside the `mov 0xc9e9c,r16` immediate load at
`0x34506` in `FUN_00034350`). Matches the `search_instructions` result exactly — the "FactorC" table's
blast radius really is confined to that one function.

Method: full disassembly re-trace of `FUN_00034a72` (all ~440 instructions read, not partially), Ghidra
decompile cross-check, exhaustive Python byte scans (opcodes 0x39/0x3B/0x3F, reg1=gp) for `gp-0x6986`/
`gp-0x6988`/`gp-0x6988`'s producer, and a raw 32-bit pointer scan for `0xC9E9C`.

Related: [[reference_accord_boost_amp_blend_direction_and_d2000_block]],
[[reference_accord_tp73ba_ema_blast_radius_and_gp6bd0_damping]],
[[reference_accord_boost_index_input_is_resolver_rate_not_torque]]
