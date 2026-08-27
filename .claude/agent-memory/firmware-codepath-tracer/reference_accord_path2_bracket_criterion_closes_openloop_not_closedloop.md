---
name: reference-accord-path2-bracket-criterion-closes-openloop-not-closedloop
description: "Path 2 enters the loop as B = 1 + Q, not in series, so raising the 0xC63AC pole ADDS lead only if sign(|Q| + cos(arg Q)) > 0 -- inversion is possible iff |Q| < 1 AND cos(arg Q) < -|Q|. close-the-sign's f' >= 0 closes the OPEN-loop sign; arg L(7.79 Hz) and hence arg Q is still open, so V96's S2 (not S1) is the gate. Also: the 1.38x 21 Hz cost of alpha=205 is a Path-2 figure -- Path 1 dilutes it to +4..+22% on the command."
metadata:
  type: reference
---

# The Path-2 BRACKET — why DC-gain invariance does NOT close a Path-2 lever's sign

2026-08-12 (`fw-loop`). Model: `analysis-2020accord/sessions/v97/loop_phase_model.py`.
Applies to **every** `FUN_00038148` lever — the six lane weights `0xC63A0..AA` **and** the pole
`0xC63AC`.

## THE STRUCTURE [EVIDENCE, from the decompile]

Path 2 does **not** sit in series with the loop. It sits inside a bracket with a `1`:
```
d(iVar6)     = -2.5771 * H_iir(f) * d(sum6)              # 0xC6468/1024, the >>4 and *16 cancel
d(gp-0x6b70) = f' * d(iVar6)                             # the two sign(iVar6) factors cancel
d(error)     = d(T) + 2.5771 * f' * H_iir(f) * d(sum6)   # the reference is SUBTRACTED
d(sum6)      = L(f) * d(T)                               # the sensor-fed lanes
=> d(error) = d(T) * B,   B = 1 + Q,   Q(f) = 2.5771 * f' * H_iir(f) * L(f)
```

## THE CRITERION [EVIDENCE, algebra + numeric check]
```
d(arg B)/d(arg Q) = |Q| (|Q| + cos(arg Q)) / |B|^2
=> sign( d(arg B)/d(arg Q) ) = sign( |Q| + cos(arg Q) )
```
🛑 **Raising `0xC63AC` (which increases arg Q, i.e. removes lag) ADDS lead to the loop only if
`|Q| + cos(arg Q) > 0`. INVERSION is possible iff `|Q| < 1` AND `cos(arg Q) < -|Q|`.**

Worked: |Q| = 0.5, arg Q = 180°, α 102→205 (+12.56° on the lane) ⇒ **arg B goes 0.00° → −11.99°.
The intended +12.6° of lead arrives as −12.0° of lag.**

## WHAT `f′ ≥ 0` DOES AND DOES NOT CLOSE

`close-the-sign` proved `f′ ≥ 0` is enforced in code (monotone guards at `0x388c4`, the float interp
branch, `0x38de2`/`0x38e48`, clamp `0x38e9c`, `X[0]`/`Y[0]` zero at `0x38d1c`/`0x38d22`). **That is
real and it closes the OPEN-LOOP sign.**
🛑 **It does NOT close `arg Q`, because `sign(Q) = sign(f′)·sign(L)` and `L(f)` — the net sensor-fed
lane transfer into `sum6` at 7.79 Hz — is still open.** `gp-0x6b26`'s *measured* delivered phase is
**+137°**, i.e. in the sector where inversion lives. `gp-0x6bbe`'s measured "+73.6 ct, P(<0)=0.887"
is a **DC/low-rate pedestal**, not a 7.79 Hz small-signal transfer.

⇒ **V96's S2 (coherence-weighted closed-loop slope) is the gate, not S1.** S1 gives `f′`; **S2 gives
`|Q|` and `arg Q`.** V96 was cut with two slopes for exactly this reason.

⊕ `fw-levers`' DC-gain argument ("unity DC gain ⇒ a POLE not a GAIN ⇒ escapes `f′`") is **correct as
far as it goes** — the operating point, and `f′` at it, really are unchanged. It simply does not
address the bracket.

## THE α SWEEP, AND A COST CORRECTION IN THE FAVOURABLE DIRECTION

| α | fc | Δphase @7.79 | ×@21 Hz | ×@28 Hz |
|---|---|---|---|---|
| 102 (stock) | 15.9 Hz | — | 1.000 | 1.000 |
| 130 | 20.2 Hz | **+5.18°** | 1.152 | 1.193 |
| 150 | 23.3 Hz | +7.82° | 1.234 | 1.306 |
| 170 | 26.4 Hz | +9.90° | 1.300 | 1.402 |
| 205 | 31.9 Hz | **+12.62°** | 1.383 | 1.534 |

🛑 **No sweet spot — the exchange rate is flat at 0.33° per 1 % of extra 21 Hz** (0.340/0.334/0.330/
0.329). A smaller step buys proportionally less.
⊕ **But 1.383× is PATH-2 throughput, not command.** Path-2's share at 21 Hz is
`2.5771·f′·|H(21)|·|K(21)|/(1+same)` = **9.9 %** (f′=0.19) to **57.7 %** (f′=2.36) ⇒ **the real cost
of α=205 is +4 % to +22 % on the command.** Against V88's measured 0.549 [0.407, 0.844], worst case
0.670 — **still inside the CI. α=130 costs +1.5 % to +6 %.** Reading a Path-2 figure as a command
figure overstates the cost 2–10×.

## `0xC63A4` / `gp-0x6b46` — share, and a corrected identity

Path-2 share of the lane at 7.79 Hz (Path 1 = **1.0, unweighted, no cal on it**):
f′ 0.191 → **10.3 %** · 0.50 → 23.1 % · 1.00 → 37.5 % · 2.355 → **58.5 %**.
⇒ doubling `0xC63A4` moves the lane **1.10×–1.59×**. Size after S1, not before.

🛑 **`gp-0x6b46` is NOT "low-passed backlash-gated column torque".** From `FUN_00036682` @0x36682:
`target = gp-0x6b48 + pol*((gp-0x4f60 * 0xC646C(891))>>15)` (**0.0272× torque**, so a full 4096-count
torque contributes only ~111), then `sVar15 = target − gp-0x6b46` — **a RESIDUAL, self-referencing** —
hysteresis ±`0xC619C`(1024), re-arm `0xC61A6`(20), clamp ±512, IIR `0xC63D2`(6) → 0.93 Hz.
⇒ **a slow, backlash-gated estimate of the torque-tracking RESIDUAL, not a filtered copy of torque.**
Raising its weight injects more slow tracking *error*, not more low-frequency torque.

## ⭐ `|Q|` SIZED — and `close-the-sign`'s 6.71 is NOT `|Q|` [EVIDENCE + estimate]

`g·f′·|H(7.79)|` = 2.336 (f′=1.0) · 5.501 (f′=2.355) · **6.704 (f′≈2.87)** ⇒ **6.71 is the
`sum6 → gp-0x6b70` gain, missing `L`.** `Q = 6.71·L`; `|Q| > 1` needs **`|L| > 0.149`**.

`L` from the kit's own MEASURED lane amplitudes at 7.79 Hz (torque ~342 ct amplitude):
`gp-0x6b26` ~15 ct → 0.0439 · `gp-0x6bbe` ~6.5 ct → 0.0190 · `gp-0x6b46` ~1.1 ct → 0.0032
⇒ **`L ≈ 0.066` ⇒ `|Q| ≈ 0.44` — BELOW 1, i.e. in the inversion-possible zone**, which needs
`|arg Q| > 116.3°`. `arg Q = 0 + (−23.6°) + arg(L)`, and `arg(L)` referred to **torque** is the one
unknown. **V96's S2 measures exactly that product.**

## 🛑 CORRECTION TO MY OWN PART-2 HEADLINE

*"Total firmware phase at 6–9 Hz is −3° to +10° ⇒ 7.8 Hz cannot be a firmware pole"* — **that budget
was LOOP A ONLY and omitted the bracket.** Corrected:
`total = arg K + arg B − transport = +8.24° + arg(1+Q) − 2.8°`, and at `|Q| = 0.44`,
`arg B ∈ [−26°, +26°]` ⇒ **total ≈ [−21°, +31°]**. **The conclusion survives** (still nowhere near
180°) but it survives with a ±26° term I had left out. ⊕ **+12.6° is FILTER lag removed; the
~2.8°/tick transport term is untouched by α.**

## 🛑 DESCRIBING-FUNCTION LIMITS — what the phase numbers do and do not cover

- **PID output saturation: phase arithmetic SURVIVES.** A symmetric memoryless saturation's
  describing function is **real and positive** — gain reduction, **zero phase**.
- **Anti-windup (`0x3a7ae`) is NOT memoryless** — a conditional integrator, state-dependent.
  **Not derived.**
- **`FUN_00036682`'s hysteresis (±`0xC619C` = 1024) carries REAL LAG** that grows as amplitude falls
  toward the width — and `gp-0x6b46`'s amplitude (~1.1 ct) is **three orders below** it, so it may
  not break out at all. **Not derived.**
⇒ **Every phase figure here is linear-small-signal.**

## ☠ `0xC63A4` DEFLATED — the tilt is real, the lane carrying it is not

`L_6b46 = 0.0032` ≈ **1.1 counts of a 342-count signal — the smallest sensor-fed lane by 6–14×.**
Doubling `0xC63A4` moves `sum6`'s composition by **~5 %**; making the tilted lane dominate needs ~20×.
⊕ **A weight is frequency-flat by construction**: `0xC63A4` ×2 gives 1.103× @7.79 Hz and 1.100×
@21 Hz (f′=0.19) — **within 1 %** — so it buys a tiny tilt at a full-price 21 Hz cost. **Not the build.**
⊕ **`sign(polarity)` CANCELS** — `gp-0x6752` multiplies `FUN_00036682`'s target, `FUN_00038148`'s
target *and* the PID output, so it drops out of the loop.

## ✅ TWO OTHER MECHANISMS STRUCK ON DATA (team-lead, this session)
`0xC520C` ceiling: **0.00 %** of engaged-return samples reach the 1050 knot. **AUTH/`0xC67C8`**:
`log(plateau) ~ log(AUTH)` β = **−0.013 [−0.344, +0.319]**, CI excludes +1 ⇒ **refuted**; the
"2.13× faster return" for `0xC63AC` was the accumulator settling, not the wheel. **⇒ the kit has NO
mechanism for the operator's clause 2 (faster engaged return).**

## ⭐⭐ `Q` IS ONE CROSS-SPECTRUM BETWEEN TWO CHANNELS ALREADY ON THE WIRE

**`Q(f) = − d(gp-0x6b70)/d(T)`**, `T` = `gp-0x4f60` = STEER_TORQUE_SENSOR on `0x18F`, and
`gp-0x6b70` is V96's CAN-427 channel. **The decomposition into `f′ × H × L` (V96's S1/S2, which
regress on `gp-0x374c>>4`) was never needed — the decision only ever required the composite.**
🛑 V96 **flew** as routes 7e/7f; its **regressor** channel is dead (`|gp-0x374c>>4| < 2048` on
99.90/99.97 % of frames — sized off a ~68,600 structural bound, ~34× over-range) but its **primary**
`gp-0x6b70` channel is healthy (p50 ~154 ct, max ~3520, zero clipping). **So S1/S2 are void and `Q`
is still recoverable from the same flight.**

**And the phase was already measured in the opening brief:** `gp-0x6b70` vs the torque sensor
**+45°/+43° ±28°** ⇒ `arg Q` = measured **+ 180°**:

| measured | arg Q | cos(arg Q) | \|Q\| needed to ADD lead |
|---|---|---|---|
| +15° (−1σ) | 195° | −0.966 | 0.966 |
| **+43/45°** | **223/225°** | **−0.731/−0.707** | **0.731/0.707** |
| +73° (+1σ) | 253° | −0.292 | 0.292 |

Against `|Q| ≈ 0.444`: **0.444 − 0.707 = −0.263 ⇒ INVERTS.** `0xC63AC` 102→205 would deliver ≈ −12°
of **LAG**, not +12.6° of lead. ⚠ Flips to "adds" only at the **+1σ edge** ⇒ strongly indicative,
**not conclusive**. Closing it: compute `|Q| = |gp-0x6b70| / |gp-0x4f60|` at 7.79 Hz on hands-off
engaged returns and **report the CI on `|Q| + cos(arg Q)` as one expression**, not on the factors.
⚠ The ±28° is a CAN-join artefact — a 10 ms join error **is** 28° at 7.79 Hz; use the safe pairings
from [[accord-raw14-offbyone-in-every-cache]].

## 🛑 A SEPARATE RISK THAT WOULD ZERO PATH 2 OUTRIGHT
`FUN_0003a382` uses `uVar24 = clamp(gp-0x6ad6, ±0xC6200 = 8192)` before `error = gp-0x4f60 − uVar24`.
**If `|gp-0x6ad6| ≥ 8192` then `d(error)/d(gp-0x6b70) = 0`, `Q = 0`, and EVERY Path-2 lever is void.**
`gp-0x6ad6 = clamp(−gp-0x6b4a + … + gp-0x6b70, ±25600)` and the LKAS command rails 52–70 % of the
return ⇒ **the reference-clamp duty is a first-class check.** One rung; cheapest possible kill.

## `sign(gp-0x6752)` IS NOT NEEDED FOR A PATH-2 POLE LEVER
Polarity multiplies `FUN_00038148`'s target **and** the PID output ⇒ it appears **twice** in the
Path-2→PID chain and **cancels**. It matters for Path-1 weights, not for `0xC63AC`.

## ⚠ SOFT SPOT IN MY OWN CHAIN
`FUN_00038148`'s "sole caller = `FUN_0002214a`" rests on `get_function_callers` alone. Not
load-bearing for the above, but it is the one claim I did not corroborate with a second method.

Links: [[reference_accord_6to9hz_loop_is_pid_torque_tracker_phase_budget]] ·
[[reference_accord_c63a6_gate_trace_forward_vs_closed_loop_sign_split]] ·
[[reference_accord_rate_limits_c6194_partition_and_c520c_ceiling_scale]]
