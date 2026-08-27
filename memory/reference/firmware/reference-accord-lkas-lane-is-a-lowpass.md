---
name: reference-accord-lkas-lane-is-a-lowpass
description: "The arbitration IIR gp-0x3d3c (pole 0.96875, tau ~31.5 cycles) makes the entire LKAS command lane a ~1-5 Hz low-pass. A tens-of-Hz component cannot be COMMANDED through it - this eliminates every upstream-of-gain source for a fast vibration in one stroke."
metadata:
  node_type: memory
  type: reference
  originSessionId: 6a579c19-b22f-4385-a786-8205eb6c7a7e
  modified: 2026-07-20T05:30:33.656Z
---

**★ A structural constraint that eliminates half a search space at a time. Apply it before tracing any fast-oscillation hypothesis in the LKAS path.**

Byte-verified 2026-07-20 in `FUN_00028ea6` (arbitration core) @`0x2a174`-`0x2a1b0`, stock `code.bin`:

```
term1[n] = floor(507 * x[n]   / 1024)      cal 0xC63EE, ld.hu  (UNSIGNED)
term2[n] = floor(992 * s[n-1] / 1024)      cal 0xC63EC, ld.h   (SIGNED - see trap)
s[n]     = term1[n] + term2[n]             -> stored to gp-0x3d3c
out[n]   = floor((s[n-1] + s[n]) / 32)     -> iVar34, the LKAS command carried onward
```

`x[n]` is the divq-based LERP-cascade result clamped ±`0xC61BE`=15360. All three shifts are `sar` (arithmetic/floor); **no rounding term is added before any of them**. `gp-0x3d3c` is exclusively owned — exactly one `ld.w` and one `st.w` image-wide.

**Pole = 992/1024 = 0.96875 ⇒ τ ≈ 31.5 cycles, unity DC gain ⇒ corner ~0.5–5 Hz** at any plausible loop period.

**THE CONSEQUENCE:** a tens-of-Hz component **cannot be COMMANDED through the LKAS lane**. Everything upstream of the gain — CAN intake, setpoint, the setpoint-limit LERP, the whole LERP cascade, **and openpilot's own command dynamics including `STEER_DELTA`** — is band-limited to a few Hz before it ever reaches the gain. This stage *smooths* a fast component rather than creating or forwarding one. A fast LKAS-conditional vibration must therefore arise **downstream of this IIR**, and be **high-pass in character** — which is why `r26` (a *derivative* of driver column torque) ended up the last mechanism standing.

**Both IIR self-oscillation hypotheses are DEAD — proven, not merely unobserved:**
- **Free-running limit cycle:** impossible. For constant input the recursion is the affine map `s[n] = K + floor(a·s[n-1])` with `0<a<1`. `floor(a·s)` is monotone non-decreasing in integer `s`, and `a<1` forbids overshoot ⇒ monotone bounded ⇒ lands on an exact fixed point and stays. A period >1 orbit is structurally impossible. Classic granularity limit cycles need a **negative** pole or round-to-nearest with sign-dependent bias; neither is present.
- **Dead-band / stick-slip:** dead band enumerated over X=0..2200 → 1089 plateaus, mean width **2.02 X-units** = `1024/507`, i.e. ordinary input quantisation, not a recursive pathology. ⚠ The naive `LSB/(1−pole)` = 32 applies to the raw **state**, not the output: `iVar34 = (s[n-1]+s[n])>>5` is a **two-sample rolling average that RECOVERS resolution**. Ramp sweeps 0.25→25 X/cycle show step sizes tracking instantaneous slope with dwell ≤4-5 cycles at the slowest rate and 1 cycle above rate 2 — no freeze-then-jump anywhere. At the motor: an `iVar34` step of 1-2 yields **0 counts** on both builds; even a 25 X/cycle ramp gives 0 stock / 2 on V38 = 0.046% of the lane.
- **Upstream-LERP quantisation** (the one door left open) is closed analytically: a step into a **single positive real pole** low-pass emerges as a smooth exponential over ~31 cycles, never a fast edge. Coarse upstream quantisation ⇒ low-frequency stepping, not a buzz.

⚠ **SIGNEDNESS TRAP:** `0xC63EC` (the pole weight) is loaded `ld.h` **SIGNED**. Inert at 992, but raising it to ≥`0x8000` would read **negative**, flipping the pole sign — the one change that *could* create genuine sign-alternating oscillation. A reason to leave it alone, not a lever.

⚠ **CAL CORRECTION:** an earlier note cited `tp+0x73e8` (`0xC63E8`). That is a **different** cal (=923), not read by this recurrence. Only `0xC63EC` and `0xC63EE` are.

**How to apply:** when a fast-oscillation hypothesis is proposed anywhere in the LKAS command path, first ask *which side of this filter is it on?* Upstream ⇒ dead on frequency grounds, no trace needed. This retroactively downgraded [[openpilot-steer-delta-not-rescaled-for-gain]] from leading candidate to a several-Hz-only explanation. Sibling tool: [[reference-accord-gain-rescaling-invariance-partition]] (eliminates by *units*; this one eliminates by *bandwidth*). Modelled as `lkas_iir_quantization_analysis()` in `analysis-2020accord/model/eps_lkas_chain_model.py`.
