---
name: reference_accord_c61be_gate1_clean_ladder_and_arb_curve_inputs
description: "GATE 1 PASSES for 0xC61BE: its downstream terminus gp-0x62f8[]/gp-0x4b88[] IS one of FUN_00028d22's 8 shadow-lockstep pairs and gp-0x6b4c is watched by FUN_00027b0a's ASIL float monitor, but a VALUE change (not a code/routing change) cannot desync either since both sides read the same live data. Exact ladder computed: 0xC61BE=18830 is the first hard stop (0xC61B2/0xC61B4=3072 start binding), 29189 matches gp-0x4f64's own max (4762), 31383 reaches 0xC674E=5120. The 0xC674E '~10x abort' is a SEPARATE constraint on the GAIN cal's own tracking formula (512*gain/891), not on 0xC61BE directly. Also: FUN_00028ea6's pre-clamp arb-curve value depends on gp-0x6a56 (measured/achieved steering rate, CAN 0x14A/0x18F source), gp-0x6a5e (fused driver torque, exogenous to openpilot), and gp-0x69ae (LKAS setpoint) -- NOT a function of CAN 0xE4 alone, so saturation cannot be inferred from the command channel without a probe."
metadata:
  type: reference
---

# `0xC61BE` GATE 1 clearance, the exact raise ladder, and why its saturation needs a probe

Traced 2026-08-26 (`ratecap` task, team-lead's 3-part follow-up after `0xC61BE` was reinstated).

## 1. [EVIDENCE] GATE 1 PASSES — the shadow-lockstep mechanism protects VALUE changes by construction

`gp-0x62f8[]/gp-0x4b88[]` (this chain's terminus, "the request") and `gp-0x62b0[]/gp-0x4b40[]` (LKAS's
registered slot) are two of the **8 shadow-lockstep array pairs** `FUN_00028d22` protects — already on
record in [[reference_accord_slot_array_asil_monitors_and_shadow_arrays]], re-confirmed here, not
rediscovered. `FUN_00027b0a`'s ASIL float monitor also watches `gp-0x6b4c` (int-vs-float, ±3/1024).

**Why raising `0xC61BE` is safe against both:** it's a read-only cal feeding ONE computation
(`FUN_00025c32`: `gp-0x62f8[slot]=clamp(struct[4],±0x2800)` plus shadow `gp-0x4b88[slot]`) that writes
BOTH the array and its shadow from the SAME instruction sequence, same value. A cal VALUE change alters
what flows through but both sides of every pair still get the identical (new) value — no desync
possible. Same argument clears the ASIL float monitor: it recomputes from the SAME live `gp-0x62b0[]`
data the integer path uses, so a magnitude change is invisible to it short of overflow (none at any
rung in section 2, all stay well under the `±0x2800`=10240 aggregate clamp).

**The risk class this DOESN'T cover: a CODE/ROUTING edit that touches one side of a pair only** — that's
what actually bricked V27 (see [[reference_accord_c61be_c61b4_c61b2_diagnostic_cluster_not_lkas_ceiling]]
section 6, the `0xC674E` int/float lockstep). A pure cal-value raise on `0xC61BE` is not that class.

`0xC407E` interlock: CLEAR, no shared cell or function with `gp-0x6b26`'s sole writer `FUN_00036c12`.

**VERDICT: GATE 1 PASS, no open item.**

## 2. [EVIDENCE] The exact ladder

```python
gain6x = 5346
ceiling = lambda c61be: (c61be * gain6x) >> 15

  0xC61BE   ceiling@6x   binds
   15360      2505       nothing (today, virgin)
   18830      3072       0xC61B2/0xC61B4 START BINDING  <- first hard stop (18829->3071, 18830->3072, exact)
   29189      4762       matches gp-0x4f64's own max within 1 count
   31377      5119       one under 0xC674E (0xC407E=511-style margin, IF that convention applies here)
   31383      5120       0xC674E itself
```
**First stop, `0xC61BE`=18,830 (+22.6%), is a pure single-cell edit** — `0xC61B2`/`0xC61B4` untouched,
GATE 1 unaffected.

🛑 **The "structural abort above ~9-10x" in this kit's record is about the GAIN (`0xC6CD0`), not
`0xC61BE`.** It's `0xC61B2`/`0xC61B4`'s own gain-tracking formula (`512*gain/891`) crossing `0xC674E`
=5120 at `gain`=8910 (exactly 10.0x): verified `891->512(OK), 5346->3072(OK), 8909->5119(OK),
8910->5120(VIOLATES)`. It only becomes relevant to `0xC61BE` if `0xC61B2`/`0xC61B4` ALSO need raising
past their gain-tracked value — i.e. above the 18,830 stop.

## 3. [EVIDENCE] `FUN_00028ea6`'s arb-curve is NOT a function of CAN 0xE4 alone

Full decompile of `FUN_00028ea6` (54KB, chunked via Python string search rather than losing it to the
token cap — the whole-function decompile exceeds the tool's per-call limit). Confirmed present, by
direct string search of the decompiled C, as inputs feeding the multi-stage LERP/product computation
whose output is clamped by `0xC61BE`:
- **`gp-0x6a56`** — the SAME cell already established as the source of CAN 0x14A/0x18F STEER_ANGLE_RATE
  ([[reference_accord_c520c_empirically_slack_on_route_a6_and_scale_anchor]]) — the car's MEASURED,
  ACHIEVED steering rate, a closed-loop consequence, not an independent input.
- **`gp-0x6a5e`** — fused driver torque (sole writer `FUN_00041eec`, per
  [[accord-arb-input-cluster]]) — exogenous to openpilot, openpilot cannot see or predict it.
- **`gp-0x69ae`** — the LKAS setpoint itself (openpilot-derived, the one input that IS visible).

At least 5 related clamps live in this cal cluster (`0xC61B2`/`B4`/`B6`/`BC`/`BE`), several LERP tables
selected by a mode/channel index (`iVar23`, pointer arrays `PTR_LAB_000cbb54`/`PTR_DAT_000cbc34`/
`PTR_LAB_000cbae4`/`DAT_000cbbc4` and more, NOT individually resolved this session), combined via
products and Q10/Q15 scales, feeding a persistent one-pole state (`gp-0x3d3c`) before the `0xC61BE`
clamp. `gp-0x6b30` and `gp-0x6b38` (the diagnostic mirror cells found earlier this session) sit
downstream of this exact block.

⇒ **Saturation at `0xC61BE` cannot be inferred from openpilot's `0xE4` command plus generic vehicle
state — it depends on driver torque (openpilot-invisible) and achieved rate (closed-loop feedback).**
A telemetry probe (or unwinding the LERP tables' actual X/Y knots, not done this session) is the only
way to size the dose from data rather than arithmetic alone.

## Related
[[reference_accord_c61be_c61b4_c61b2_diagnostic_cluster_not_lkas_ceiling]] — the base pricing and the
`0xC674E` lockstep-monitor safety flag this entry's GATE-1 section resolves (VALUE-change risk: clean).
[[reference_accord_slot_array_asil_monitors_and_shadow_arrays]] — the 8-pair census this reuses.
[[reference_accord_c520c_empirically_slack_on_route_a6_and_scale_anchor]] — `gp-0x4f64`'s own measured
distribution, used to derive the 29,189 rung.
