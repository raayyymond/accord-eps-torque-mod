---
name: reference_accord_loop_lag_map_v104_and_fun41464_1khz_correction
description: Full closed-loop lag/phase catalog at 8/20/23/26Hz for the V104 (8x gain) f0 problem -- every EMA/IIR/ZOH/transport-delay element quantified with a cross-validated Python mirror. CORRECTS FUN_00041464 (gp-0x6abe/6ac0 rate-estimator EMA) from a believed 312.5Hz "5/16 phase-gated" rate to a confirmed unconditional 1kHz (same state-mask misread class fun2214a_is_state_mask already fixed elsewhere, now independently re-derived for this specific function). Characterizes a NEW live filter (0xC6382/gp-0x381c inside FUN_000352b4, downstream neighbour of the dead biquad) and a NEW ZOH element (100Hz task5 damper/boost lanes held into the 1kHz aggregator). Headline: per this kit's own f0-dose-floor work, NO lag-only lever is sized to move f0 by the ~1.5Hz needed while holding gain fixed at 8x -- the tuner's "speed up the tracker" intuition is TESTED AND BACKWARDS on this firmware's own full-loop Bode sum.
metadata:
  type: reference
---

# The closed-loop lag map for V104's f0 problem — 2026-08-20

Full trace: `docs/traces/TRACE-2026-08-20-loop-lag-map.md`. Program: stock `code.bin`, GhidraMCP only.
Briefed to find/quantify every phase-lag element in the EPS loop and rank levers to push `f0` (the
`Re(Z)` zero-crossing) below the ~20-23Hz mechanical mode while V104 runs 8x LKAS gain.

## 🛑 NEW THIS SESSION: `FUN_00041464` is 1kHz, not 312.5Hz — corrects a standing rate misattribution

Fresh `disassemble_bytes(0x221e0,0x2223e)` (dry_run): `0x221f8 andi 0xd30,r25,r23` / `be 0x22204` /
`0x22200 jarl 0x41464` — a THIRD `andi 0xd30` state-mask gate (same mask family
`reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz.md` already proved fires on
every tick, since `gp-0x67fa`'s reachable set is `{11}` alone and bit 11 is set in `0xd30`).
⇒ **`FUN_00041464` (producer of `gp-0x6abe`/`gp-0x6ac0`, the common-mode motor-rate bus) runs
unconditionally at 1 kHz**, not the `fs_eff=312.5Hz` ("5/16 phase-gated") rate
`reference-accord-common-mode-rate-signal-6abe-6ac0-full-chain.md` computed its phase table at.
That file's own §3 phase numbers (−19.9°/−39.3°/−41.3° at 7.4/21/30Hz) are **stale** — recomputed at
the corrected 1kHz rate (same α=37/128=0.2891 EMA), the lag is much smaller:
**−7.0°/−16.8°/−19.1°/−21.2° at 8/20/23/26Hz** (roughly a third of the old figures at 21Hz). This
matters directly for any loop-phase-budget calculation that used the old number.
⚠ I did not edit that file directly — flag to operator before treating either figure as final;
this correction rests on ONE fresh disassembly this session, not a second independent method.

## Full cross-validated lag table (Python mirror, matches every pre-existing cross-checked figure to <0.5°)

| element | fn/addr | cal | 8Hz \|H\|∠φ | 20Hz | 23Hz | 26Hz | DC gain |
|---|---|---|---|---|---|---|---|
| resolver diff+boxcar | `FUN_00068f52`, 4kHz ISR | none | 1.000∠+89.3° | 1.000∠+88.2° | 1.000∠+87.9° | 1.000∠+87.7° | 0 |
| rate EMA `6abe`/`6ac0` | `FUN_00041464`, **1kHz-corrected** | `0xC643C`=37,Q7 | 0.989∠−7.0° | 0.939∠−16.8° | 0.922∠−19.1° | 0.903∠−21.2° | 1.0 |
| MODEL cmd branch ×2 | `FUN_0003b8f6`@`0x3b94e` | `0xC40D4`=573/4096 | 0.900∠−34.1° | 0.591∠−72.6° | 0.522∠−79.5° | 0.461∠−85.5° | 1.0 |
| MODEL friction EMA | `FUN_0003b8f6`@`0x3bb22` | `0xC40D0`=408/4096 | 0.902∠−24.2° | 0.641∠−46.6° | 0.588∠−50.0° | 0.541∠−52.7° | 1.0 |
| Path-2 accum (+1 tick) | `FUN_00038148`@`0x38202` | `0xC63AC`=102/1024 | 0.902∠−27.1° | 0.641∠−53.8° | 0.588∠−58.2° | 0.541∠−62.1° | 1.0 |
| `gp-0x6b46` filt. term | `FUN_00036682` | `0xC63D2`=6/1024 | 0.116∠−81.9° | 0.047∠−83.7° | 0.041∠−83.5° | 0.036∠−83.3° | 1.0 |
| PID D-branch alone | `FUN_0003a382`@`0x3a85c` | Kd=2048/1024, pole unity | 0.101∠+88.6° | 0.251∠+86.4° | 0.289∠+85.9° | 0.326∠+85.3° | 0 |
| `gp-0x381c` IIR, static cand. | `FUN_000352b4`@`0x359d8` | `0xC6382`=41/2048(Q11) | 0.373∠−66.7° | 0.159∠−77.3° | 0.139∠−77.9° | 0.123∠−78.3° | 1.0 |
| dead biquad (disarmed) | `FUN_000352b4`@`0x35a28` | `0xC649B`=0 | 0.982∠−10.9° | 0.879∠−28.5° | 0.837∠−33.2° | 0.786∠−38.1° | 1.0 |
| 100Hz→1kHz ZOH (damper/boost) | task5→task1 boundary | structural | 0.990∠−14.4° | 0.936∠−36.0° | 0.915∠−41.4° | 0.893∠−46.8° | 1.0 |
| 1-tick transport | call-order proof | structural | 1.000∠−2.9° | 1.000∠−7.2° | 1.000∠−8.3° | 1.000∠−9.4° | 1.0 |

`0xC63EC`/`0xC63EE` (LKAS-branch IIR): confirmed **exogenous** (filters the CAN-sourced setpoint,
upstream of the mixer, never reads a sensor) — excluded from the loop budget in EITHER direction.
Governor (`FUN_0004503c`) and comp-add (`FUN_000456a4`): confirmed NOT tunable linear filters
(nonlinear slew limiter; static memoryless LERP) — not in this table.
Soft-EME integrator: sits at 0 while `|command|` < corridor/boost bound (5120-12288ct) — zero
small-signal dynamics at the amplitudes in question.

## New live filter found: `0xC6382`/`gp-0x381c` inside `FUN_000352b4`

`0x358cc ld.hu 0x7382,tp,r2` is the ONLY real reader of `0xC6382` (search_instructions + raw scan
agree, 3 other hits are branch-target/wrong-address coincidences). Feeds a single-pole IIR on a
32-bit state `gp-0x381c` (`state += ((target<<7 - state)*K)>>11`, Q11, **unconditional — always
runs**, distinct from the disarmed biquad that follows it in the same function). `K` is selected
(`0x359be cmovne r2,r11,r15`) between the STATIC candidate `cal(0xC6382)=41` and an LERP-computed
alternative (table at `tp+0x78fc..0x790c`, NOT decoded this session), gated by a compound flag
built from `|gp-0x6b62|>8192` AND another `gp-0x6b7a`-based comparison. Clamp range [2,204]/2048
(α 0.001-0.0996) — **the ceiling 204/2048 is bit-identical to `0xC63AC`'s and `0xC40D0`'s α
(0.099609375)**, a fourth instance of that exact constant in this firmware.

🛑 [BELIEF, structural]: since `gp-0x6b62 ≡ 0` over 75,227 engaged frames (this kit's own prior
measurement, `reference_accord_dwell_relay_polarity_is_arm_on_LARGE_correcting_the_kit_record.md`),
the STATIC-41 branch's gate is essentially never true in engaged driving — **the LERP branch is
what's actually live in practice, and its real operating coefficient is unmeasured.** Not the same
function/gate as the dead biquad's own arm (`0xC649B`+`gp-0x671a`, re-confirmed unchanged this
session) — this is a DIFFERENT, currently-unattributed filter, one stage upstream, feeding an
unresolved consumer (not `r10`, the biquad's own forcing input — ruled out this session by tracing
`r10`'s lineage back to `gp-0x6b7a`/peak-hold instead). Next step to size: decode the LERP table +
find `gp-0x381c`'s downstream reader(s).

## 🛑🛑 THE HEADLINE: no lag-only lever clears the ~1.5Hz f0 bar at fixed 8x gain

Re-confirms and extends `reference_accord_f0_dose_floor_and_common_path_structure_search.md`
(same-day prior session, "damphunt round 4"): `f0` is linear in gain (21.90/23.61/24.90Hz at
1x/4x/6x, disjoint CIs), retrodicting ≈26.1Hz at 8x. A lever needs ~230 ct·s/rad of `Re(Z)` effect to
clear detection; the best-characterized filter lever in the whole kit (arming the dead biquad) prices
at +2 to +13 realistically (+50 at an unrealistic extreme) — **3-115× too small.** The governor and
comp-add are confirmed NOT tunable filters. A model-shape refit found even a full ±180° phase
rotation can't supply the needed `Re(Z)` swing — **the problem is loop-gain MAGNITUDE at 22-26Hz
being too small in every model tried, not primarily phase.** Working synthesis (prior session,
consistent with everything traced here): gain is privileged because it's the only variable that
changes PHYSICALLY DELIVERED TORQUE AMPLITUDE, re-linearizing multiple amplitude-dependent
nonlinearities (the `f′` observer LERP, plausibly the governor's duty cycle) SIMULTANEOUSLY — a
fixed linear filter on any one branch structurally cannot replicate that.

⭐ **Directly tests and REVERSES the openpilot-tuner's "speed up the tracker" intuition**: the ONE
lever that best matches "the tracker" (`0xC63AC`, Path-2's accumulator) was already given a full
closed-loop Bode-sum treatment and found to make `Q` WORSE at every dose 150-300 —
`reference_accord_c63ac_full_loop_bode_sum_net_negative.md`. Because every lag element catalogued
above is a single-pole LOW-PASS, removing its lag necessarily WIDENS its own HF passband, and that
gain cost dominates the phase-margin credit once the loop closes. **Generalizes**: raising the alpha
on ANY element in the table above should be treated as adverse-by-default, not neutral, absent its
own full-loop Bode sum.

## Ranked shortlist (full table in the trace doc)
1. Dead biquad arm (`0xC649B` 0→1) — favorable sign, GATE1/2/3 previously worked, but **+0.01 to
   +0.3Hz, 5-150× below threshold. Free rider, not a fix.**
2. `0xC63AC` raise — **REFUTED**, already flown-equivalent analysis says worse.
3. `0xC63EC`/`0xC63EE` — **excluded**, exogenous, confirmed this session.
4. `gp-0x381c`/`0xC6382` — **new candidate, unsized**, needs the LERP decode + a `q` estimate.
5. New 2nd-order allpass cave (`fc≈21Hz,r=0.90`, designed prior session, `|H|=1` exactly, low
   command-band cost) — **most structurally promising idea in the record**, but GATE-1 RAM
   unmatched and Hz-of-f0 deliberately unpriced (the loop model can't support that conversion
   honestly per the magnitude finding above). Design-stage only, not a lever yet.
6. Lowering `0xC6CD0` (give back gain) — the ONLY lever with a measured, monotone, linear f0 effect.
   Contradicts V104's stated constraint; stated for completeness.

## What's unresolved
The `gp-0x381c` LERP table and its downstream consumer; FOC current-loop Kp/Ki (assumed but not
measured to contribute little phase at ≤26Hz); a single composed 20-26Hz total-firmware-phase figure
(exists at 6-9Hz, not yet built at 20-26Hz — needs the same per-branch attribution fraction `q` that
has blocked every prior session's attempt at this); the allpass cave's GATE-1 RAM claim.

## Related
[[reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz]] — the state-mask fact this
session's correction extends. [[reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm]]
— the biquad this file's #1 lever reuses. [[reference_accord_c63ac_full_loop_bode_sum_net_negative]] —
the full-loop test that reverses the "speed up the tracker" intuition. [[reference_accord_v101_v102_resonance_mechanism_and_biquad_direction]]
— §4 independently re-confirmed this session (the `gp-0x381c` vs biquad-arm gate distinction).
