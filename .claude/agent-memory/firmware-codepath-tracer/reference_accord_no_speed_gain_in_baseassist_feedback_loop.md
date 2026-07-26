---
name: reference_accord_no_speed_gain_in_baseassist_feedback_loop
description: Exhaustive check of all 9 base-assist aggregator lanes (boost/damping/friction/carrier/filtered-Sensor-B) finds zero vehicle-speed-keyed gain terms; every shaping factor is torque-magnitude, motor-electrical-rate, or flat per-car mode index.
metadata:
  type: reference
---

**Context**: team-lead asked whether a SPEED-DEPENDENT gain multiplies the base-assist feedback loop
(driver torque → boost/damping/friction → motor torque → column deflection → torque sensor), on the
theory that assist gain peaking at low speed could explain a self-excited ~21Hz limit cycle that's
independent of LKAS command magnitude and peaks around 5mph.

**Result: no such term exists, anywhere in the traced base-assist path.** All 9 lanes feeding the
aggregator `FUN_0003aa2c` (`gp-0x6b94`) were checked this session or in prior sessions (cited below).
Every one of them is keyed on driver torque magnitude, motor electrical-angle rate, or a flat per-car
mode index (`gp+0x63fd`, this car always mode 10) — never on a decoded vehicle/wheel speed.

| Lane | Producer | Axis (what varies the gain) |
|---|---|---|
| Boost (`gp-0x6bbe`) | `FUN_00034a72` | AVG torque `gp-0x6a5e` (main curve), MAX torque `gp-0x6a62` (ceiling), motor-rate-domain `gp-0x6c2e`+EMA of raw torque `gp-0x4f60` (the "rate-keyed" table's real key — see correction below), mode index (flat scalars) |
| Damping (`gp-0x6bd0`) | `FUN_00034350` | AVG torque (2 factors), `gp-0x6a10` (flat unity, no-op), `gp-0x6ac0` motor rate magnitude (only non-unity factor) |
| Friction (`gp-0x6b26`) | `FUN_00036c12` | AVG torque `gp-0x6a5e` only |
| Return-centre (`gp-0x6b62`) | `FUN_00036388` | motor rate `gp-0x6ac0` + assist substate, NOT torque (its torque gate cal `0xC62E2=0` is vacuous) |
| Filtered Sensor-B (inline, `FUN_00036682`) | `FUN_00036682` | torque-like internal state `gp-0x6b48` combined with raw Sensor-B `gp-0x4f60` via cal `0xC646C` (the 4x LKAS gain constant); pure IIR/hysteresis, no external axis |
| `FUN_0003a382` residual (`gp-0x6ad4`) | `FUN_0003a382` | raw Sensor-B derivative, unfiltered (see [[reference-accord-fun3a382-unfiltered-residual-lane]]) |
| `gp-0x6b86` carrier | `FUN_000352b4` | deadbanded Sensor-B magnitude (10-pt LERP), see [[reference-accord-fun352b4-untested-carrier-and-dead-biquad]] |
| LKAS command (`gp-0x6b4c`) | mixer | LKAS setpoint, not base-assist |
| Small unidentified lane (`gp-0x6ade`) | UNLOCATED | **[OPEN]** one read in the aggregator (`0x3aa48`), zero writers found by `search_instructions` — could be a real gate with a movhi/movea write this tool misses, or a genuinely dead/near-zero lane like the confirmed-dead `gp-0x6809`. Narrowest gate of all 9 (±1024), lowest priority to chase further. |

**Correction to `eps_lkas_chain_model.py`'s `FUN_00034a72` docstring**: the four previously-undumped
tables (`0xCA324` gain-scalar, `0xCA4F4` "rate-keyed" LERP, `0xC7A58` per-mode clamp, `0xCA23C`
`gp-0x69ba`-keyed LERP) are now identified by full decompile:
- `0xCA324`, `0xC7A58`: flat per-mode SCALAR constants (one value per mode, not a curve) — gain-scalar
  and a clamp bound respectively. Not axis-indexed by anything continuous.
- `0xCA4F4` and `0xCA23C`: both keyed on the SAME derived quantity (`puVar15` in the decompile), which
  in production (cal `tp+0x7499=0` selects this branch) is `clamp(|(gp-0x6c2e * cal_0xC6370)>>5 *
  polarity_scale + boost_EMA(gp-0x4f60)>>5|, ±25600)` with a plausibility fallback to `|gp-0x4f60|`
  against `gp-0x4f68`. **`gp-0x4f68` = `abs(gp-0x4f60)` clamped ≤0xFFFE, computed by the raw Sensor-B
  ADC/decode driver itself (`FUN_0007f3f8`, sole writer @`0x7feca` — the function that produces
  `gp-0x4f60` in the first place)** — i.e. a cached magnitude of the SAME torque signal, not a separate
  physical channel. `gp-0x6c2e` is written only by `FUN_00041464` (the SAME function that produces
  `gp-0x6ac0`/`gp-0x6abe`, the established motor-electrical-rate signals) — motor-rate domain, not speed.
  **So "rate-keyed" in the old docstring meant motor-rate/torque-blend, not vehicle speed** — worth
  fixing the comment to avoid a future session reading "rate" as "vehicle speed."

**Consequence for the team-lead's loop-gain-vs-speed theory**: it cannot be evaluated as stated because
there is no vehicle-speed input anywhere in this loop to design against. The one genuinely rate-shaped
multiplicative factor in the whole base-assist path (damping's `f4`, keyed on `|gp-0x6ac0|` MOTOR
electrical rate: Q10 values 0→140→539→927 as rate climbs 60→400→2500→4000, see
[[reference-accord-fun34350-damping-term-live-and-gated]]) is **monotonically INCREASING with rate**,
the opposite shape needed for a "gain highest when nearly still" story — and it's motor rate (steering
activity), not vehicle road speed, so it doesn't have an obvious 5mph relationship at all (a driver can
produce any motor rate at any vehicle speed).

**Engaged-mode gating**: `FUN_00034a72`'s `valid` gate requires `gp-0x67fe` (assist substate) in `{1,2}`
— but this is the EPS's OWN power-assist active/ramping state (motor is on and providing torque), not
openpilot/LKAS engagement. Base assist runs whenever the EPS is actively assisting the driver,
independent of whether LKAS is commanding anything. No "only-when-openpilot-engaged" gain switch was
found inside any of the 9 lane producers.

**Related**: [[reference_accord_no_vehicle_speed_in_arbitration_steerstatus3]] — the companion finding
that the STEER_STATUS/arbitration FSM also has zero speed reads. Between the two, every function on the
known LKAS + base-assist command path has now been checked for a vehicle-speed input, with a consistent
negative result.
