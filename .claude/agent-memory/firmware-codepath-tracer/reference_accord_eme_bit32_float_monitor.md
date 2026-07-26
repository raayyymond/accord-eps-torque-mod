---
name: reference-accord-eme-bit32-float-monitor
description: FUN_00043e44 bit32 (weight=32) comparison at 0x448d6-0x448f4: confirmed the float cmd_final does NOT read tp+0x746c (arb gain cal), so V18 2x gain causes 1x vs 2x divergence every cycle, accumulating via SM to DTC 0xF00049 within ~10ms of sustained hold; fix address and patch values documented
metadata:
  type: reference
---

> ## ⚠ CONTESTED — DO NOT OVER-TRUST THE "bit32 = V18 EME" CONCLUSION (caveat added 2026-06-02)
>
> This file's headline — that bit32 is the V18 EME cause — rests on a **mis-primed brief** (the
> dispatching prompt asserted "V18 throws DTC 0xF00049"). The operator's account contradicts that:
> **V18 produced no dash light and self-recovered (~10s)** — i.e. NOT a logged DTC. V18's actual EME is
> the **direction-corridor → integrator gp-0x3570 → SM2/SM3** soft cutback. And bit32's `cmd_final` is
> almost certainly **gain-aware** (built from `gp-0x6acc`, the already-gained command), so it does not
> diverge under V18. The DTC 0xF00049 is the **V19–V24 hard fault** (consistency-monitor desync caused by
> the `shl` envelope doubling), not V18. Treat the analysis below as accurate **float-monitor structure**
> (the bit32 comparison sites, thresholds, dwell SM), but NOT as the V18 cause. Corrected model:
> `memory/reference_accord_corridor_vs_envelope.md`.

# Accord EME Bit32 — Float Monitor Divergence Under V18 (Verified 2026-06-02)

## Entry point
FUN_00043e44 (0x43e44–0x44a88), the float-domain rate-shaper monitor / EME accumulator.
gp=0xFEDF8000, tp=0xBF000. V850E2 firmware.

## Verdict (one line)
Bit32 (weight=32.0) fires at 0x448d6–0x448f4 by comparing float cmd_final (r9) vs gp-0x6b98/1024 (delivered torque). The float cmd_final is built WITHOUT reading tp+0x746c (arb gain cal) — confirmed by full disasm scan — so V18 (2x gain) creates a ~1x vs 2x divergence that fires bit32 every cycle during sustained LKAS hold, accumulating to 128.0 threshold and DTC 0xF00049 in ~10ms.

## Key instruction sequence (bit32 comparison)

| Address | Instruction (bytes) | Effect |
|---------|---------------------|--------|
| 0x448d6 | `ld.h -0x6b98[gp],r12` | r12 = gp-0x6b98 (delivered torque, signed int16) |
| 0x448da | `cvtf.ws r12,r14` | r14 = float(delivered_torque) |
| 0x448de | `nmsubf.s r14,r1,r9,r1` (ee 0f e0 4d) | r1 = r9 − (r14×r1) = cmd_final − delivered/1024 |
| 0x448e2 | `cmp r7,r1` | compare error vs +5/1024 |
| 0x448e4 | `bgt 0x448ee` | branch → weight=32 if error > threshold |
| 0x448e6 | `movhi -0x4460,r0,r8` | r8 = 0xBBA00000 = −5/1024 |
| 0x448ea | `cmp r8,r1` | compare error vs −5/1024 |
| 0x448ec | `bnh 0x448f4` | if error ≥ −5/1024 → weight=0 |
| 0x448ee | `movhi 0x4200,r0,r12` (40 66 00 42) | **r12 = 32.0** (bit32 weight) |
| 0x448f4 | `mov r0,r12` | r12 = 0.0 (no fault) |

- r1 = 0.0009765625 = 1/1024 (set at 0x43efe: `movhi 0x3a80,r0,r1` = 40 0e 80 3a). Never rewritten in FUN_00043e44.
- Threshold: ±5/1024 ≈ ±5 raw counts (r7 = 0x3BA00000 set at 0x4463e: `movhi 0x3ba0,r0,r7`).

## Float cmd_final does NOT read tp+0x746c

**Evidence:** Full disassembly scan of FUN_00043e44 (43e44–44a88) shows ZERO occurrences of displacement 0x746c in any `ld.*[tp]` instruction. The float monitor reads: tp+0x75d4/75ec/75d8/75f0, tp+0x7648/7660/764c/7664/767c, tp+0x74cb/74ca/74e3/741c/741a/741e/74a4, tp+0x75b8/75c0/75bc/75c4/75cc, tp+0x74c8/74c9, tp+0x71d4/71dc/7156/71da — 0x746c absent.

cmd_final (r9 at 0x448d6) is built from:
- gp-0x4f64 (governor limit, loaded at 0x4486e)
- gp-0x6dac (at 0x4487a) — ⚠ **LABEL CORRECTED 2026-07-20. It is NOT a "speed-scaled float".**
  Traced to its single write site image-wide: `0x42af2 st.w r6,-0x6dac,gp` inside `FUN_00042adc`, a thin
  sanitizing setter (clamp-to-FLT_MAX-if-invalid) whose ONLY caller is `FUN_00027b0a`. That function is
  a **multi-channel SENSOR REDUNDANCY / PLAUSIBILITY monitor** over a separate address family
  (gp-0x61xx/62xx/63xx — gp-0x62b4, gp-0x62c8, gp-0x6298, gp-0x6324, gp-0x61e8, gp-0x61d4 …), scoring
  channel agreement and tripping its own DTC set (0x3d00-0x3d04, 0x3ce6-0x3cff, 0x4157-0x4158) via
  `FUN_000462e6`. Same KIND as the 5-channel torque voter `FUN_00041eec`, but a different instance over
  a different channel set. Tail: `gp-0x6dac = clamp(channel-agreement score, ±10.0)`.
  **So it is an independent DIAGNOSTIC quantity, not a command-derived one** — its inputs never touch
  gp-0x6acc, gp-0x6b98, gp-0x6b94, gp-0x6ad4, or anything downstream of the shaper/governor.
  The old label's underlying CLASSIFICATION (independent of the command path) was right; its physical
  description was wrong. Corrected because this kit has already lost multiple builds to a wrong label
  left standing — see the `FUN_0003a382` "very heavily damped" (gain 4 vs 1024) precedent.
  [VERIFIED — adjudicated image-wide scan: 8 raw "6dac" hits, 6 branch-target coincidences excluded with
  reasons, 1 read @0x4487a, 1 write @0x42af2.]
  [OPEN, minor] `FUN_00027b0a`'s ~150 lines of channel arithmetic were not replayed literal-by-literal;
  the classification rests on its structure (5-channel loop, epsilon-gated DTCs, own DTC table) and on
  containing ZERO references to any torque-command address.
- tp+0x74c9 (mode selector byte, at 0x44896)
- ±8.0 code immediates (0x41000000/0xC1000000, applied at 0x448c2/0x448ce)

None of these apply the arb gain. The float side hard-clips to ±8.0, then computes error against the live motor output.

## Dwell/accumulation state machine

State byte: gp-0x3540 (0xFEDF_C4C0). Timer: gp-0x3550 (0xFEDF_CAB0).
Fault accumulator (fVar22) = sum of all weighted bits, updated each 1ms cycle.

| State | Condition | Next action |
|-------|-----------|-------------|
| 0 | any | Reset: gp-0x3550=0, state→1, fVar22=0. No fault this cycle. |
| 1 | `tp+0x74a4==0` AND fVar22>0 | state→2, timer+=0.001s |
| 1 | otherwise | fVar22=0, timer decrements |
| 2 | fVar22>0 AND timer≥0.01 (10ms) | state→3, fVar22+=1024.0 |
| 2 | fVar22>0 AND timer<10ms | timer+=0.001 |
| 3 | unconditional | fVar22+=1024.0 every call |

128.0 threshold trip: 0x44a26 `movhi 0x4300,r0,r12` (bytes 40 66 00 43) = 128.0; `cmp r12,r7` at 0x44a2e; `bgt 0x44a3e` at 0x44a34 (delay slot 0x44a30 = `st.w r20,-0x6db8[gp]` — store only, no control effect).

Fault call at 0x44a4c: `jarl 0x000462e6,lp` with r6=0x3f1b → fault_id=29 (0x1d) → DTC 0xF00049 (EPS-disabling).

**Minimum trip time under V18:** With bit32=32.0 firing every cycle, SM dwell through state=2 requires ~10ms (timer reaches 0x3c23d70b ≈ 0.01001). State=3 entry adds +1024 → fVar22 >> 128 → fault fires same cycle. Total: ~10ms of uninterrupted engagement. Operator "few seconds" experience explained by `tp+0x74a4` gate (likely post-engage settle flag that is 1 for seconds after disengage).

## Fix options (ranked)

### FIX A — Widen bit32 threshold (RECOMMENDED, surgical, no code cave)

Patch two code immediates to make the ±5/1024 window wide enough to contain the 2x gain error:

| Address | Current bytes | Current value | Proposed value | Proposed bytes |
|---------|---------------|---------------|----------------|----------------|
| 0x4463e | `movhi 0x3ba0,r0,r7` | +5/1024 = 0.00488 | +2.5 = 2560/1024 | `movhi 0x4020,r0,r7` → 0x40200000 |
| 0x448e6 | `movhi -0x4460,r0,r8` | −5/1024 = −0.00488 | −2.5 | `movhi -0x3fe0,r0,r8` → 0xC0200000 |

NOTE: These are embedded 16-bit immediates in 4-byte V850E2 `movhi` instructions. In the .rwd cal partition these are code bytes, not cal halfwords — this is a CODE patch, not a cal patch, and requires CRC recalculation on the code block covering 0x4463e.

Safety cost: The ±2.5 window means runaways up to 2.5 torque units above cmd_final go undetected. Given the governor ceiling (gp-0x4f64, typically capped at ~4762 counts / 4.64 float) and the ±8.0 hard shaper clamp, actual runaway space is bounded. Acceptable for 2x gain. DO NOT widen beyond ±max_cmd (≈8.0) or the monitor becomes meaningless.

### FIX B — Apply 2x gain to float cmd_final before nmsubf (code cave required)

Insert a `mulf.s r_gain,r9,r9` between 0x448d4 and 0x448de, where r_gain = 2.0 (= 0x40000000). Requires a code cave (no free slot) and the gain ratio would be hard-coded rather than tracking the cal. More complex, same safety profile as Fix A.

### FIX C — Suppress dwell SM (NOT recommended)

Blocking the state=3 transition or zeroing gp-0x3550 disables the torque-runaway monitor entirely.

## Open questions

1. **Confirm r7 = 0x3BA00000 survives from 0x4463e to 0x448e2 unmodified** — scan instructions 0x4463e→0x448e2 for any `mov`/`ld` targeting r7.
2. **tp+0x74a4 behavior** — read 0xC70a4 and trace its writer to confirm post-engage settle timing.
3. **gp-0x3540 writers outside FUN_00043e44** — confirm whether state resets on LKAS disengage.

[[reference-accord-dtc-construction-mechanism]]
[[reference-accord-v21-startup-fault-root-cause]]
[[reference-accord-integrator-update-form]]
