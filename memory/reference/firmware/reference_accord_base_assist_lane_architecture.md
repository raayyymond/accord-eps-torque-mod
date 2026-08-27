---
name: reference-accord-base-assist-lane-architecture
description: "Base driver assist joins at FUN_0003aa2c as boost + 5 named sibling lanes + 2 inline Sensor-B torque-rate lanes + a filtered term. The direct r24 torque-rate lane can reach +/-8192 and is V39's narrow target. All assist joins before the shared governor/shaper."
metadata:
  node_type: memory
  type: reference
---

The base power-steering path (the always-on assist that responds to the driver's own hand torque), traced end to end 2026-07-18. Supersedes the abstract placeholder that previously stood in for it in `analysis-2020accord/model/eps_lkas_chain_model.py`.

## Correction: assist does NOT join at the LKAS mixer

The prior model merged assist into `limit_distribute_mixer_gate`. **Wrong.** `FUN_00026c80` (mixer) + `FUN_00025c32` (distribute) sum only ~11 **LKAS-internal** channels (the `tp+0x5124` mode array) into `gp-0x6b4c` — that whole stage is still an LKAS-only lane.

Assist joins **one stage later**, at `m_motor_torque_demand_aggregator` `FUN_0003aa2c` (`0x3aa2c-0x3ad70`).

"Distribute source index 1" and "the ~10 aggregator lanes" are **two separate summing stages** that had been conflated into one.

## The assist lanes and inline terms

All read the voter outputs directly. `gp-0x6a5e` (AVG) is the primary curve key; `gp-0x6a62` (MAX) is the safety-ceiling key and the `0xFFFF` sentinel check.

| producer | lane | role |
|---|---|---|
| `FUN_00034a72` | `gp-0x6bbe` | **the boost curve proper** [VERIFIED] |
| `FUN_00034350` | `gp-0x6bd0` | 5 multiplied mode-indexed gain factors (`0xC9CCC`, `0xC9E9C`, `0xC9DB4`, `0xC9F84` keyed on `gp-0x6ac0` motor electrical rate, `0xC77A0`); sign FORCED opposite `sign(gp-0x6abe)` — a velocity-opposing signature [INFERRED: viscous damping] |
| `FUN_00036c12` | `gp-0x6b26` | LERP `@0xCBE74` x `gp-0x6c2e`, gated `gp-0x671a` vs `tp+0x74fd` and `gp-0x67f4==1` [INFERRED: friction comp] |
| `FUN_0003a382` | `gp-0x6ad4` | 3-stage cascaded IIR over `gp-0x6ac0`, `gp-0x4f60`, `gp-0x6a5e`, `gp-0x67fe` [INFERRED: resonance damping — lowest confidence] |
| `FUN_00036388` | `gp-0x6b62` | slow +/-1/tick accumulator `gp-0x6a82` with hysteresis `tp+0x718a`; consumes `gp-0x6b96` [INFERRED: return-to-centre] |
| `FUN_000352b4` | `gp-0x6b86`, `gp-0x69a4` | normal Sensor-B torque inside +/-25600 PASSES; only invalid/out-of-window torque forces zero [INFERRED: friction magnitude] |
| inline in `FUN_0003aa2c` | `r24` | `gp-0x4f62` Sensor-B four-sample torque derivative x generated positive Q10 gain, +/-3 deadzone, clamp +/-8192 [VERIFIED] |
| inline in `FUN_0003aa2c` | `r26` | `gp-0x4f62` x averaged `gp-0x69a4` x generated positive Q10 gain, clamp +/-8192 [VERIFIED] |
| `FUN_00036682` | return `r10` | Sensor-B-derived term using `0xC646C`, final slow IIR with 6/1024 coefficient [role OPEN] |

The bracketed roles are **[INFERRED] from structure** (gating, signs, which signals combine). None of these functions carries a confirming string or symbol. The addresses and plumbing are [VERIFIED].

**Correction 2026-07-18:** the final `FUN_000352b4` branch was inverted in the first trace. At `0x35aa4..0x35ace`, `-25600 <= gp-0x4f60 <= 25600` stores the candidate `gp-0x6b86`; only an out-of-window value stores zero. This lane is active in normal driving. Its adaptive magnitude is still unresolved and remains an explicit replay input in `model/eps_lkas_chain_model.py`.

`gp-0x4f62` is produced by `FUN_0007e74a` from Sensor-B torque as `2*(current-delayed)/wrapped_sample_delta`, with delay cal `tp+0x7c42=4` and lockstep shadow `gp-0x4488`. The producer runs on phase mask `0xD30` (5/16 base ticks); `FUN_0003aa2c` consumes on `0xC30` (4/16). The direct `r24` lane can amplify a `+512` derivative to `+1533` at low voted torque/motor rate and can saturate at +/-8192. This is large relative to V38's ~1782-count full LKAS lane and is the strongest static match for the operator's tens-of-Hz high-LKAS vibration. Revised V39 suppresses `r24` for both signs at `|LKAS lane|>=417` (the lower exact V9 full-scale magnitude) and low voted driver torque; adaptive `r26` remains live.

## The boost curve (`FUN_00034a72`, `0x34a72-0x35150`)

- Mode select: `ld.bu 0x63fd[gp]` `@0x34abc` -> 34-entry array `@0xCA154`. Our car = index 10. See [[reference-accord-assist-curve-family-sport-mode]].
- Safety ceiling: `@0xC7970`, keyed on the MAX voter — **flat 512 in every mode in this image**, not a shaped curve. Default fallback `tp+0x715a` = 512, used when the key >= `0x7d01` (saturated / `0xFFFF` sentinel).
- Rate limiter at entry: `FUN_0004613e(0x3638, ...)` = 13880/tick over cluster `gp-0x6bb2/4/6/8`; its output keys the `@0xCA4F4` curve.
- Own 4-state engage ramp: byte `gp-0x682e` in {0,1,2,3}, timer `gp-0x68c8` vs `tp+0x74d1 * 10`. **Separate from the LKAS engage SM.**
- Validity gate: `gp-0x67fe in {1,2}` AND `gp-0x67f4 == 1` AND `gp-0x6a5e < 0x7d01` AND range checks on `gp-0x6ba6`/`gp-0x4f68`/`gp-0x4f60`/`gp-0x6c2e`.
- Store: `clamp(gain_modulated_signed, +/- ceiling)` x polarity `gp-0x6752` -> `gp-0x6bbe`, lockstep-shadowed at `gp-0x4cf0` (mismatch -> `FUN_0006b9fa`).

**[OPEN]** contents of `0xCA324` (gain scalar), `0xCA4F4`, `0xC7A58`, `0xCA23C`. **[OPEN]** whether `FUN_00034a72`'s call site carries an `andi` phase mask like arbitration's `@0x22522` does.

## The join, and why it matters

`FUN_0003aa2c` reads: `gp-0x6b62`, `gp-0x6b4c` (LKAS, `+/-0x2800`), `gp-0x6ade` (**DEAD** — read `@0x3aa48`, zero writers image-wide), `gp-0x6ad4`, `gp-0x6b26`, `gp-0x6bbe`, `gp-0x6bd0`, `gp-0x6b86`, inline `r26/r24`, plus `FUN_00036682` when `gp-0x67ac != 1`. The exact full-mode add order is pinned at `0x3acc8..0x3ace6` and reproduced in the canonical model.

Per-lane range gating idiom (verified `@0x3aa50-0x3aa6c`) — out-of-window lanes contribute **0** rather than clipping:

```
addi  <window>, rN, rM
addi -<limit>,  rM, r0
cmovc 0x0, rN, rX
```

Sum -> clamp `+/-0x2800` -> **`gp-0x6b94`** (`0xFEDF146C`), lockstep `gp-0x4ce0`. `gp-0x67ac == 1` selects a reduced subset, but its sole writer depends on source modes 6/7; A160's source-mode table contains none, so it remains zero in normal execution and is not an LKAS-active flag.

### The load-bearing consequence

`gp-0x6b94` is the **same** variable the governor chain already consumes: `m_motor_torque_governor` `FUN_0004503c` -> `m_post_governor_torque_comp_add` `FUN_000456a4` -> `s_motor_torque_rate_shaper` `FUN_00042af8` -> `gp-0x6b98` (final FOC command).

Because LKAS and base assist are summed into **one scalar before** all three of those stages, **base assist passes through the exact same governor and the exact same soft-EME shaper as LKAS. There is no bypass and no second path to the motor.**

This structurally explains the operator's Era 16 reframe — a soft-EME cut is felt as the *whole power steering* momentarily dropping out, not merely LKAS easing off. That was previously an observation; it is now a consequence of the topology.

Related: [[reference-accord-demand-aggregator-pipeline]], [[reference-accord-lkas-delivery-and-governor]], [[reference-accord-soft-eme-bound-arm-gating]], [[reference-accord-assist-curve-family-sport-mode]]
