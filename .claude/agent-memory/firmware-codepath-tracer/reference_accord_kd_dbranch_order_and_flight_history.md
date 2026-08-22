---
name: reference_accord_kd_dbranch_order_and_flight_history
description: PID Kd (0xC6AE6) is a pure scalar on the D-branch's raw error-difference, applied BEFORE the disarmed smoothing pole (0xC644A) -- since both are linear and the pole is unity (all-pass) at stock, H_D(f) = (Kd/1024)*(1-z^-1), a near-ideal +85-90 deg differentiator with ZERO phase dependence on Kd's value; doubling Kd exactly doubles D's magnitude at every frequency with no phase shift. Kd itself is confirmed virgin (1 reader image-wide, 0 writers, byte-identical to stock on every built image V43-V104) -- the ADJACENT pole 0xC644A flew (V43/V49, falsified on 15-26Hz) but that null does not cleanly transfer to Kd (bandwidth cut vs magnitude raise are different edits). Cross-validates reference_accord_loop_lag_map_v104_and_fun41464_1khz_correction.md's independently-computed D-branch row to 3 decimals.
metadata:
  type: reference
---

# Kd / D-branch order of operations, and why the 0xC644A null doesn't settle it (2026-08-22)

Traced for team-lead's "can Kd damp the 26Hz mode" question. `FUN_0003a382` decompiled fresh
(whole function). gp=0xFEDF8000, tp=0xBF000.

## The exact order [EVIDENCE, fresh decompile]
```
0x3a45e  ld.hu 0x7ae6,tp,r6      ; Kd = cal(0xC6AE6), LERP'd on gp-0x6ac0 (same index as Kp/Ki)
         iVar29 = (error[n] - error[n-1]) * Kd >> 10     ; Kd applied FIRST, to the raw diff
         iVar31 = clamp(iVar29, +-0x2800)
0x3a860  ld.hu 0x744a,tp,r11     ; the pole, cal(0xC644A)
         D_state[n] = D_state[n-1] + ((iVar31*32 - D_state[n-1]) * cal(0xC644A)) >> 10   ; EMA, AFTER Kd
```
`error[n-1]` is the persisted delay register at `gp-0x3684` (matches the prior V43-session
characterization exactly). Kd scales the differencer's output; the pole then filters the Kd-scaled
result. **Both operations are linear and in series, so order doesn't affect the overall transfer
function shape** — `H_D(f) = (Kd/1024) * (1-z^-1) * H_pole(f)`.

## Consequence: at stock, D is a pure phase-fixed differentiator [EVIDENCE]
`cal(0xC644A) = 1024` (Q10 unity) ⇒ `H_pole(f) ≡ 1`, all-pass, no filtering. So today:
```python
fs = 1000.0
Kd = 2048/1024.0        # stock, Q10
H_D(f) = Kd * (1 - exp(-1j*2*pi*f/fs))
```
| f (Hz) | \|H_D\| | arg |
|---|---|---|
| 6.00 | 0.0754 | +88.9° |
| 7.79 | 0.0979 | +88.6° |
| 21.7 | 0.2725 | +86.1° |
| 26.0 | 0.3264 | +85.3° |
| 42.0 | 0.5263 | +82.4° |
| 100 | 1.2361 | +72.0° |
| 250 | 2.8284 | +45.0° |

**Cross-validates [[reference_accord_loop_lag_map_v104_and_fun41464_1khz_correction]]'s independently
computed row (`0.326∠+85.3°` at 26Hz) to 3 decimal places** — two independent sessions, two
independent decompiles, same number.

**Sensitivity is exact and trivial** — no phase to shift, only magnitude:
```
d|H_D(26Hz)|/dKd_raw = |H_D(26Hz)|/Kd_raw = 0.3264/2048 = 0.0001594 per Q10 count (linear, exact)
2x Kd: |H_D(26Hz)| doubles exactly.  4x Kd: quadruples exactly.  Zero phase change at any dose.
```
**The "raising alpha on a filter is adverse-by-default" doctrine from the loop-lag-map memory does
NOT apply to Kd** — that doctrine is about de-tuning a LOW-PASS (widening its own passband costs
more than the phase credit buys). Kd is a scalar on an already-unity-bandwidth differentiator; there
is no passband to widen. Raising Kd is a pure, frequency-independent rescale.

## Flight history [EVIDENCE, both methods]
`0xC6AE6`: `search_instructions` → 1 hit (`0x3a45e`, inside `FUN_0003a382`). Independent raw Python
LE scan, both the raw and `ld.hu`/`ld.w` `hw2=disp|1`-biased forms → same 1 hit, confirmed.
`get_xrefs_to(0xC6AE6)` returns **"No references found"** — reproduced the misleading-zero trap live.
`grep build_v*_tva.py`: appears only in FROZEN/asserted-stock dicts, V43/V49/V97-V104 — **never set to
a different value on any built image.**

**Does `0xC644A`'s V43/V49 null (falsified on 15-26Hz) transfer to Kd? NO, not cleanly — argued from
the order-of-operations above, not asserted.** V43 LOWERED the pole's cutoff — a bandwidth CUT,
removing 15-26Hz content from D. Raising Kd is the opposite class of edit — a frequency-independent
magnitude RAISE across the whole spectrum including 15-26Hz, with zero phase change. A null from
"less D at that band" does not predict "more D everywhere" without an unverified monotonicity
assumption — especially if D is the loop's only damping term there (per `compensator`'s finding),
where a small reduction not crossing a qualitative threshold and a substantial increase are not
mirror-image tests. Treat as two separate, independently-untested levers.

## What Kd raising costs, structurally [EVIDENCE for the shape, no noise-floor measurement]
`|H_D(f)|` grows monotonically to Nyquist (500Hz) since the pole is disarmed — every Hz above 26Hz
gets proportionally MORE D gain than 26Hz itself (0.33 @26Hz → 0.53 @42Hz → 1.24 @100Hz → 2.83 @250Hz
→ 4.0 @500Hz, all scaling linearly with Kd). No structural corner currently limits this. Where this
first costs real margin (sensor/quantization noise floor) is not measured this session.

## Sign — explicitly NOT resolved by this trace, and the record already flags why
`docs/BUILD-LINEAGE.md`: *"22–26 Hz IS the measured Re(Z) crossover, where three drives disagree in
sign"* for PID Kd specifically, and separately *"Kd's sign flips on only 53.4° of an unmeasured plant
phase."* Since D's own phase is now nailed down as a fixed near-+90° lead independent of Kd's value,
whether raising Kd helps or hurts is entirely a question of the LOOP's phase at 26Hz (which side of
the crossover the real column/plant sits on) — not something firmware bytes can settle. The clean
linear dose-response above is sign-agnostic by construction; direction needs on-car Re(Z) data.

## Related
[[reference_accord_loop_lag_map_v104_and_fun41464_1khz_correction]] — the full 26Hz phase table this
entry cross-validates one row of. [[reference_accord_compensator_hypothesis_junction_confirmed_and_6to9hz_reframed]]
— source of the AUTH/rail-duty figures (P alone saturates ~ERR=908 vs measured override torque
2235ct) that make the anti-windup/relay safety question (item 3b) a real, unresolved build-stopper.
