---
name: reference_accord_v106_gp6b26_mechanism_ceiling_and_reshape
description: "V106's freq-UP/amplitude-DOWN puzzle SETTLED from the arithmetic: gp-0x6b26's torque phasor sits between 180deg (damping) and 270deg (ADDED inertia) vs motor rate at every frequency, so it can NEVER enter the 90-180deg sector that raises a 2nd-order resonance -- the mechanical-resonance model is falsified for BOTH signs, and the pitch rise must be amplitude-mediated. Also: UNIFORM Y scaling is hard-capped at x3.334 by int16 on Y[0] (V106 x3.0 = 90% of it) so the uniform axis is EXHAUSTED; the reshape axis has 5.0x of highway headroom at ZERO extra creep clamp duty; and gp-0x6b26 has FIVE sites including a SECOND consumer path via FUN_00038148 that the direct-aggregator framing misses."
metadata:
  type: reference
---

# V106 / `gp-0x6b26` — mechanism, ceiling, reshape. Integer mirror: `analysis-2020accord/v106_gp6b26_mechanism.py`

2026-08-22, `mechanism` task. Everything below is re-derived fresh this session (GhidraMCP decompile-first,
then assembly, then a raw Python LE byte scan as the second method). Runs clean; re-run it.

## THE PHASE TABLE — nobody had computed it [EVIDENCE: closed form and the exact integer recurrence agree to 4 s.f.]
```
 f(Hz)   |H|    phase    cos (DAMPING)   sin (ADDED INERTIA)
  5.00   2.00   +81.26     +0.152             +0.988
  8.00   3.16   +76.07     +0.241             +0.971
 15.00   5.68   +64.30     +0.434             +0.901
 20.00   7.24   +56.31     +0.555             +0.832
 21.73   7.72   +53.64     +0.593             +0.805
 25.00   8.57   +48.76     +0.659             +0.752
 30.00   9.65   +41.69     +0.747             +0.665
 40.00  11.15   +29.09     +0.874             +0.486
```
`H = 1024·EMA1·(1−z⁻¹)·32·EMA2/512`, a1=37/128 (`0xC643C`), a2=22/64 (`0xC40DC`), fs=1 kHz.

## 🛑🛑 THE MECHANICAL-RESONANCE MODEL IS FALSIFIED FOR **BOTH** SIGNS — the decisive result
`gp-0x6b26 = −k·gp-0x6c2c` enters the aggregator at **+1**, so its torque phasor sits at
`phase(H)+180°` vs motor rate — i.e. **between 180° (pure damping) and 270° (pure ADDED inertia)** at
every frequency. Flip every sign in the chain and it lands between 0° and 90° (anti-damping + REDUCED
inertia). **The only sector that RAISES a 2nd-order resonance while damping it is 90°–180°, and this
term cannot reach it in either polarity.** ⇒ `ω_n = √(k/J)` cannot explain "quieter AND higher pitch".
The pitch rise is **amplitude-mediated**, via the kit's own measured law
(`[[accord-f0-crossover-is-the-endpoint]]`: **−1.93 Hz per e-fold of amplitude**, within-route,
speed-matched, disjoint CIs ⇒ a 2× amplitude cut predicts **+1.34 Hz**, a 3× cut **+2.12 Hz**).
**One mechanism, two symptoms.** Falsifiable within the existing V106 telemetry: **pitch should track
amplitude WITHIN the drive** — loud moments lower-pitched than quiet ones. No build needed.

`ΔJ(f)` FALLS with frequency (0.0301→0.0219→0.0104 counts/accel-count at 5→21.7→40 Hz, ×3.0) while
`c(f)` RISES 32× — the term morphs from near-pure inertia at low f to increasingly dissipative at high f.

## 🛑 THE CEILING — the UNIFORM axis is EXHAUSTED, and two independent limits land on the same number
Record layout, byte-read on stock AND the V106 image: `n@+0`, **`X[3]@+2` = (0, 1280, 5760) counts =
(0, 20, 90) km/h** at 64 ct/km/h, `Y[3]@+8`. `k = |Y|·273/2²⁴`.
```
int16 ceiling, stock-relative:   Y[0] x3.333   Y[1] x5.715   Y[2] x16.667
=> UNIFORM scaling hard-capped at x3.334 by Y[0].  V106 (x3.0) is at 90% of it.
relay index N(p50)/N(p99):  x3.0 -> 1.35   x3.334 -> 1.48   x4 -> 1.74   x6 -> 2.56   x8 -> 3.38
                            (V75 = 1.45 fine; V80 = 3.27 = the worst grinding ever recorded)
```
⇒ **MAX SAFE UNIFORM MULTIPLIER = ×3.33, binding constraint = int16 overflow on `Y[0]`** — and the
V75/V80 relay boundary arrives at ×3.4, essentially the same place. **Two independent limits coincide.**
`x4/x5/x6/x8` are all int16-OVERFLOW, not merely risky. Non-binding at ≤×3.334: int32 overflow on the
`×0x111` product (threshold 15,362 vs corpus max 5,141 = 3.0× margin) and RULE-11 (below).

## Clamp duty — the model reproduces the independently published FFT numbers
Log-interp on the V104 engaged-<16 km/h percentile grid (p50 119, p90 1064, p95 1296, p99 1704,
p99.9 2053, max 5141): **×1.5 → 0.10 % (published 0.088) · ×2.0 → 1.94 % (published 1.563) ·
×3.0 → 9.98 % (published 9.969)**. Extrapolating: ×3.334 → 11.9 %, ×4 → 15.2 %, ×8 → 27.9 %.
⚠ **That corpus is <16 km/h only** — there is NO measured `|gp-0x6c2c|` distribution above 16 km/h,
which is exactly what a `Y[2]` reshape would need.

## RULE-11 — untrippable by construction, at any multiplier [EVIDENCE, byte-exact]
`0x36CCC..0x36CE2` clamp to ±cal(`0xC407E`)=511 · `0x36CF0 st.h` the sole writer · `FUN_00036d74`
@`0x36D78` trips at 512. **Clamp precedes both the store and the monitor, 511 < 512 by one count.**
The aggregator's ±1024 validity window (`0x3ACB0`) is likewise unreachable. 🛑 Raising `0xC407E` past
1024 would *acquire* a full-magnitude dropout the lane does not have today — do not touch it.

## 🛑 FIVE SITES — and a SECOND CONSUMER PATH the "direct aggregator addend" framing misses
Ghidra `search_instructions` and a raw Python LE disp16 scan **agree exactly on 5** (Ghidra's extra
`0x6B25A`/`0x6B25E` are branch-target TEXT collisions, adjudicated out):
```
0x36CE4 ld.h FUN_00036c12  shadow-lockstep compare vs gp-0x4cd0
0x36CF0 st.h FUN_00036c12  THE SOLE WRITER, post-clamp
0x36D78 ld.h FUN_00036d74  RULE-11 monitor -> DTC 0x1d
0x3815C ld.h FUN_00038148  PATH 2 -> gp-0x6b70 -> gp-0x6ad6   <-- weight 0xC63A6 = 1024
0x3AC98 ld.h FUN_0003aa2c  PATH 1 -> aggregator, UNWEIGHTED +1 (add chain 0x3ACC8..0x3ACDA)
```
The ±511 clamp is upstream of both ⇒ the ceiling analysis is unaffected. **But the 4.99 % authority
figure is PATH 1 ONLY.** Path 2 refers ×1.601 @21 Hz to `gp-0x6ad6` (≈10 % of its own 8192 clamp) and
then meets a **runtime-scheduled PID gain that is NOT statically boundable**. 🛑 The two paths'
relative polarity is **UNRESOLVED** (`[[accord-gp6b26-is-inertia-not-damping]]` warns "two paths, two
polarities — do not merge them"). The NET sign is settled only by the on-car dose-response below.

## D5 — this term CANNOT be the steering-rate limit [EVIDENCE, proof + arithmetic]
`H(0) = 0` exactly ⇒ a **sustained** constant rate produces zero acceleration and zero term. **The term
cannot bound the maximum sustained steering rate at any multiplier.** It opposes only the *approach*.
Steady state under a constant-acceleration ramp: `gp-0x6c2c → 64·δ`.
```
accel deg/s^2   |gp-0x6b26| V105/V106   % of the aggregate +-10240 clamp   DELTA
    500            36 / 72                 0.35% / 0.70%                  +0.35%
   1000            73 / 146                0.71% / 1.43%                  +0.71%
   2000           144 / 288                1.41% / 2.81%                  +1.41%
   3532+          256 / 511 (saturated)    2.50% / 4.99%                  +2.49% max
```
**Fully saturated the term is 4.99 % of Path-1 authority; the V106−V105 delta never exceeds 2.5 %.**
⇒ **NOT the main cause.** Look instead at the aggregate ±0x2800 clamp and the state-4 governor
(`[[reference-accord-state4-governor-ratchet]]`), and at whatever `feedforward` finds.

## D4 — the RESHAPE is not an optimisation, it is the ONLY REMAINING AXIS
V106's schedule delivers **−24,546 at 5 mph but only −5,898 above 90 km/h** — the term is **4.2×
weaker at highway than at creep**, yet highway is one of the three symptomatic scenarios.
```
candidate                  5 mph      20 km/h    30 mph    >=90 km/h    int16   ratio vs V106 @highway
V106  x3.0 uniform        -24546      -17202     -12681      -5898       OK        1.00x
MAX uniform x3.334        -27278      -19122     -14096      -6556       OK        1.11x
RESHAPE A  flat -29490    -29490      -29490     -29490     -29490       OK        5.00x
RESHAPE B  flat -32767    -32767      -32767     -32767     -32767       OK        5.56x
RESHAPE C  -29490/-29490/-20000                             -20000       OK        3.39x
```
⭐ **RESHAPE A holds `Y[0]` EXACTLY at V106's value ⇒ creep clamp duty UNCHANGED (~10 %), relay index
UNCHANGED (1.35), while highway authority rises 5.00×, 30 mph 2.33×, 20 km/h 1.71×.** And the cost is
bounded identically at every speed, because the same ±511 clamp caps the term everywhere — a reshape
changes only WHERE the term reaches its authority, never how much authority it can have.
🛑 Costs to state: it deletes Honda's speed schedule (the operator will feel heavier/slower steering at
speed), and `Y[2]`'s clamp duty at highway is **unmeasured**. RESHAPE C is the conservative variant.

## Related
[[accord-gp6b26-is-inertia-not-damping]] · [[accord-f0-crossover-is-the-endpoint]] ·
[[reference_accord_fun36c12_sign_settled_dissipative]] ·
[[reference_accord_gp6c2c_real_distribution_overflow_wall_not_binding]] ·
[[reference_accord_gp6b26_v106_transfer_function_correction_and_disqualification]] ·
[[accord-v80-damper-relay-and-grind1-inert]] · [[accord-c407e-is-the-fault-interlock-c63a0-exonerated]]
