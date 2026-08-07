---
name: accord-fun3a382-is-a-torque-tracking-pid
description: FUN_0003a382 is a torque-tracking PID whose three gains are scheduled on the same motor-rate axis that indexes FactorE — and 0xC63A0's entire blast radius is the single-file chain feeding it.
metadata:
  type: reference
---

**`FUN_0003a382` is a genuine three-term controller — a TORQUE-TRACKING SERVO.** [EVIDENCE — orchestrator
decompiled it directly, 2026-08-07.]

```c
feedback = clamp(gp-0x6ad6, ±(tp+0x7200));            // Path 2 arrives HERE, as the FEEDBACK term
err      = clamp(gp-0x4f60 - feedback, ±0x2800);      // setpoint = driver torsion-bar torque
```
- **filtered-P** `gp-0x367c` — `state += (K·err·32 − state)·(tp+0x7450) >> 10`, a first-order lag.
- **integrator** `gp-0x3688` — `state += (K·err) >> 10`, **clamped into a window built from the authority
  limit** ⇒ anti-windup.
- **dirty derivative** `gp-0x3684` holds `err_prev`; `(err − err_prev)·K`, clamped ±0x2800, then
  low-passed into `gp-0x3680` with α = `tp+0x744a`.
- **output** `= ((D + I + P) >> 5) × LERP(gp-0x671a) × polarity(gp-0x6752)`, clamped to ±authority;
  authority soft-starts through `gp-0x3678` (up `tp+0x744e` / down `tp+0x744c`), scaled by
  `LERP(gp-0x6966)`. Stored to **`gp-0x6ad4`**.
- **hard gate → output 0** unless `|gp-0x6ad6| ≤ 0x6400` **and** `|gp-0x4f60| ≤ 0x6400` **and**
  `gp-0x6ac0 < 0x32c9`.

## 🛑🛑 THE GATE-2 FACT: its gains ride FactorE's own axis
**All three lane gains are LERPs indexed on `gp-0x6ac0`** (tables `tp+0x7b1e`, `tp+0x7b0a`, `tp+0x7ade`)
— **the same rectified motor rate that indexes FactorE**. A FactorE slope change and this PID's gain
schedule therefore move on **one axis; they are not independent.** That is the mechanism behind the
recorded **+41.8° to +55.0° phase lead at 21 Hz with |D| ≈ |P|**: at the grind frequency the loop is
**derivative-dominated**, precisely where a rate-scheduled gain on a **rectified** index (which sweeps at
**2f**) meets the parametric pump ([[accord-v59-parametric-pump-marginal]]).
⇒ **Size any FactorE edit against this, not just against dose.** See
[[accord-relu-plan-inverts-at-the-ceiling]] and [[accord-damper-evaluator-fun34350-ceiling-clamp]].

⚠ **[OPEN] the damper's NET SIGN through this loop.** `err = setpoint − feedback`, so more `gp-0x6ad6`
means **less** output — but whether the damper raises or lowers `gp-0x6ad6` needs the full sign chain
through `FUN_00038148` + `FUN_00037fe6` and their ± clamps walked. **Not asserted.**

## `0xC63A0`'s blast radius is a STRICT SINGLE-FILE CHAIN
[EVIDENCE — `reg1==gp`-validated byte scan over `[0x13000,0x100000)` plus decompiles.] Every hop has
**exactly one functional consumer** — no branch, no telemetry tap:

| cell | refs | |
|---|---|---|
| `0xC63A0` (`tp+0x73a0`) | **1** | `0x381AC`, in `FUN_00038148` |
| `gp-0x374c` | 2 | both internal to `FUN_00038148` (its own IIR state) |
| `gp-0x6b70` | 2 | the store + **one** read `0x38006` in `FUN_00037fe6` |
| `gp-0x6ad6` | 2 real | **both inside `FUN_0003a382`** |
| `gp-0x6ad4` | 1 real | `0x3ACA8`, in `FUN_0003aa2c` (the aggregator) |

**`FUN_00037fe6` is a UNITY-GAIN adder on stock** — its seven byte weights `0xC64AD..0xC64B3` are **all
1**, and the `tp+0x7aba` LERP is flat 1024.
🛑 **`0xC63A0` scales ONE SUMMAND, not a signal**: `FUN_00038148` sums 6 weighted inputs and
`FUN_00037fe6` sums 7, so friction / main-command / boost on the same wires are untouched.
⚠ **3 raw hits discarded as FALSE POSITIVES** — `0x767a8` / `0x767b2` land **inside 4-byte `mulf.s`
instructions** (not on an instruction boundary) and `0xBCC52` / `0xBDF92` sit in data with no function.
**Always validate a byte-scan hit against an instruction boundary** ([[accord-v850-scan-traps-formatv-and-storezero]]).
⚠ disp16 gp/tp only; extended-displacement and `ep`-relative forms were **not** swept image-wide.

## ⊕ Why STOCK has no damper at creep
Stock FactorC is `Y = [0,234,429,908]`; below `X[0]` = 2240 ct = **35.00 km/h** the evaluator hard-clamps
to `Y[0] = 0`, and the chain is four `mulu`+`>>10` with **zero `add`/`or`** ⇒ **FactorC = 0 zeroes the
output at every rate, with no additive rescue.** The knee is a clamp, not a fade: 35.0 km/h → 0,
35.1 km/h → 1. Even above it, stock `FactorE(99 ct)` = **16 of 927** (a 60-ct / 12.7 °/s deadband), so
stock delivers 3 counts at 60 km/h and 14 at 140 km/h at the grind's own rate. **Honda ships no steering
damping below 35 km/h — which is exactly where grind #1 and the ratchet live.**
