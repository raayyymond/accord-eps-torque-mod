---
name: reference_accord_c63ae_dose_is_a_level_not_an_ac_change
description: 0xC63AE 1024->2048's headline "+28% / +177 ct clears the perceptual floor" is a LEVEL shift scored against an AC-calibrated bracket -- its in-band 6-9 Hz figure is 1.242 on the lane and 1.021-1.135 delivered, at or below V85's not-felt 1.088; the AC gain is also NON-MONOTONE in scale (1280 = 0.902, WORSE than stock); PIN and WRAP duty are 0.0000 at <=2048 but the real hazard is a 4.9-9.0x gain EXPANSION at the X[8] corner with only 1.14x margin at 2048 (1.53x at 1536); RULE 7 proven and passed -- the cell is a non-indexed tp scalar with one unconditional reader.
metadata:
  type: reference
---

# `0xC63AE` priced end to end — 2026-08-13, `tracer-c63ae`

Full trace: `docs/traces/TRACE-2026-08-13-c63ae-lever.md`. Verdict delivered: **NO-GO at 2048 as V100's lever.**
Supersedes the "only lever above the perceptual floor" framing in
`HANDOFF-2026-08-13-v98…` §8 item 2 and `TRACE-2026-08-13-path2-authority` Addendum 2 §5.

## ⭐ THE FINDING — a CHANNEL MISMATCH, and it is reusable on every future lever

The `+28 % / +177 ct` that made this the session's only above-floor candidate is a **median LEVEL
shift** of `gp-0x6b70`. The perceptual bracket (V88 15–22 Hz command **0.549** FELT; V85 6–9 Hz
**1.088** NOT felt; V89 **0.947** NOT felt) is calibrated in **in-band AC delivered ratios.**

> 🛑 **Never score a LEVEL change against the AC bracket.** They are different perceptual channels: a
> level change is felt as **steering weight** (V86B class), an AC change is felt as the **symptom**.

In-band figure for this lever, hands-on engaged, route 81 (n = 2,198): **AC 1.242 on the lane**;
applying V97's own Path-1 dilution φ ∈ [0.085, 0.556] (`builds/v80_v107/build_v97_tva.py:65-67`, 1.234× lane → "+2 %..
+13 % of the TOTAL") ⇒ **delivered 1.021–1.135 — straddles the not-felt line, midpoint below it.**
⊕ This trace applies the dilution **symmetrically to cost and benefit** — the asymmetry V97 committed.

## 🛑 THE AC GAIN IS NON-MONOTONE IN SCALE — a "dose ladder" here is a SAWTOOTH
`d(out)/d(iVar6) = (scale/1024) × f′((|iVar6|·scale)>>10)` — the "twice" claim **VERIFIED** from the
decompile. Consequence nobody had drawn, at the hands-on p50 (|iVar6| = 2,712):

| scale | 512 | 768 | **1024** | **1280** | 1536 | 1792 | **2048** | 3072 |
|---|---|---|---|---|---|---|---|---|
| AC ratio | 0.706 | 0.754 | **1.000** | **0.902** 🛑 | 1.076 | 1.245 | **1.242** | 2.138 |

**1280 is WORSE THAN STOCK.** Each step first pushes the operating point into a flatter LERP segment
before the multiplier catches up. ⊕ Reproduces the record's "512 is 0.71× worse" exactly (0.706).

## THE CLAMP QUESTION — answered, and the named hazard is the WRONG one
**PIN (`idx ≥ X[9]` ⇒ output ≡ 8192, marginal gain exactly 0) and WRAP duty are BOTH 0.0000 at 1280,
1536 AND 2048.** Zero, not small. WRAP margin at 2048 is 6.9× over the measured max.

🛑 **The real hazard is the `X[8]` corner: the last segment is a GAIN EXPANSION, not a saturation** —
`f′` jumps **0.212 → 1.036 (4.9×)** at 6.6 km/h and **0.181 → 1.638 (9.0×)** at 0 km/h. A slope rising
with amplitude is the limit-cycle setup — **V80 class**.

| scale | corner at \|iVar6\| | margin over measured max 4,743 | frac ≥ 0.8×corner |
|---|---|---|---|
| 1024 | 10,853 | 2.29× | 0.0000 |
| **1536** | **7,235** | **1.53×** | **0.0000** |
| **2048** | **5,426** | **1.14×** | **0.0332** |

⇒ **If it ever flies, 1536 — not 2048, and never 1280.**
⊕ Highway is benign: at 50/80 km/h the corner is reachable (24 %/41 %) but the jump is only 1.3×/0.9×.

## RULE 7 — PROVEN AND PASSED [EVIDENCE]
- The **cell** is a non-indexed `tp` scalar: `0x38242 ld.hu 0x73ae,tp,r10` (`e557af73`), **one
  unconditional read**, guarded only by the `|gp-0x6bfe| ≤ 20000` sentinel and the caller's `andi
  0x830` state gate. ⇒ **the V69/V70 wrong-record failure CANNOT recur.**
- The **knots** are mode-indexed (`FUN_000382d8`: `gp+0x63fd`, `0xC7B40 + mode*4`, brk `0xCC9FC +
  mode*4`), mode 24 manual / 26 engaged — but **m24 vs m26 differ ONLY at `Y[8]` (0.8–1.6 %) and the
  X knots AND breakpoints are IDENTICAL** ⇒ the dose is <2 % sensitive to the mode inference.
  ⚠ **Corrects a brief that said the breakpoints differ — they do not** (both `[0,960,2560,5120,7680,10240,12800]`).
- Census **1 reader / 0 writers**, Ghidra (1/183,570) ∖ raw LE both-parity Python (1, same address,
  `hw2=0x73af` = the `disp|1` form) = **EMPTY**; 6-byte form 0; no absolute literal in the image.

## ⭐ NEW STRUCTURAL FACT — `Y[9]` and the ±clamp are the SAME CELL
`FUN_000389ec` stores `*(gp-0x3702) = *(ushort*)(tp+0x7200)` ⇒ **`Y[9] = 0xC6200 = 8192`.** The LERP
output can never exceed the clamp, so **the ±8192 clamp is NEVER the binding constraint** — saturation
is the table pinning at `Y[9]`.

## 🛑 THE BLOCKING UNCERTAINTY — not dose, SIGN
Open-loop is closed by construction (`f′ ≥ 0` code-enforced at 3 ungated sites; sign re-applied at
`0x3824e`). **Closed-loop is NOT**: `gp-0x6b70` is a PID reference that is SUBTRACTED and Path 2 enters
as `B = 1 + Q`. Live priors both ways — the `f′`-compression story (BELIEF) vs `Re(Z) < 0` replicated
on three drives plus **V94** (*"not safe to drive"*, aborted) and **V85** (de-relaying made the ratchet
2.89× → 6.58× worse). **Until the sign is settled, no gain on this lane should fly as a fix.**

## ⚠ AND IT IS NOT ENGAGEMENT-GATED — its LARGEST effect is on the WRONG arm
Hands-OFF gets **+81 %** level at 2048 vs hands-ON **+29 %** (hands-off sits on the steep part). It acts
in MANUAL. ⇒ the most visible consequence is ordinary driving, not the symptom regime — a strong
confound for any operator report.

## Related
[[reference_accord_c63ae_arm_agnostic_residual_gain_and_zxh_wrap]] — the earlier census; its wrap
concern is real structurally but **does not bind at ≤2048** (duty 0.0000, 6.9× margin).
[[reference_accord_stage2_lerp_rescale_is_identity_and_ivar6_bound]] — the K1=K2=1024 result my
rebuild depends on; my positive control reproduces its curves bit-exactly.
[[reference_accord_ram_lerp_is_flash_derived_and_fprime_nonneg]] · [[reference_accord_path2_bracket_criterion_closes_openloop_not_closedloop]] · [[reference-accord-car-is-tvca4-mode-24-26]]
