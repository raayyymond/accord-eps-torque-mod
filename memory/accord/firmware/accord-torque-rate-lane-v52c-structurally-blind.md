# ★★ The torque RATE `gp-0x4f62` is a second feedback path V52C's mechanism could not reach

**Byte-verified 2026-07-31 by the orchestrator (raw LE scan of `_v59_plain_image.bin`, base-register
field == r4 confirmed on every hit) and independently by two tracers via GhidraMCP disassembly.**

## The structure

| cell | disp16 | sites | note |
|---|---|---|---|
| `gp-0x4f60` torque VALUE | `0xB0A0` | **69** | V52C repointed 19 of them |
| `gp-0x4486` value SHADOW | `0xBB7A` | 15 | all within `0x7F2D4..0x7FD1E` (producer only) |
| `gp-0x4f62` torque RATE | `0xB09E` | **9** | V52C repointed **0** |
| `gp-0x4488` rate SHADOW | `0xBB78` | **8** | all within `0x7E7E4..0x7F44C` (producer only) |

`0x4f60 − 0x4486 == 0x4f62 − 0x4488 == 0xADA` — one matched shadow-pair architecture applied to both
cells. **`gp-0x4f62` appears ZERO times in `builds/v50_v79/build_v52c_tva.py` / `studies/caves/v52_cave_asm.py`.**

**V52C could not have caught it by repointing harder.** Its cave retargets instructions whose disp16
literally equals `-0x4f60`; the rate lives in a *different cell* written by a *different function*.
It is also an ordering problem: V52C hooks the **epilogue** of the producer `FUN_0007f3f8` at `0x7FEAC`,
while the rate is computed at `0x07F436`/`0x07F442`, earlier in that same function.

## The producer, as integer Python

```python
# FUN_0007e74a. Delay D = 4, BYTE-VERIFIED at tp+0x7c42 = 0xC6C42 (bytes 04 00).
# Called from FUN_0007f3f8, gated on gp-0x4e5f == 1 (a converged/settled flag).
current = ring[idx]                  # 0x07E78E  ld.h -0x4f60[gp],r8   <- RAW sensor, NOT V52C-filtered
delayed = ring[(idx - 4) % 8]        # 8-deep ring at gp-0x2814
num     = (current - delayed) << 1   # 0x7E832 sub, then the "2*"
rate    = trunc_toward_zero(num / dt_ticks)   # 0x7E84C divq
# 0x07E860  st.h r10,-0x4f62[gp]     (+ shadow store to gp-0x4488)
```

`|H(f)| = (4·Fs/D)·|sin(π·f·D/Fs)| → 4πf` in the small-angle limit — **≈ 264× at 21 Hz, essentially
independent of Fs** for any Fs ≳ 500 Hz. A derivative: +20 dB/decade. At 1 kHz it has **20.7× more gain
at 20.9 Hz than at 1 Hz.**

## Where it goes — 3 consumers, and only ONE is live magnitude

- `0x02C4E8` `FUN_0002c478` — **gate only** (one term of a multi-condition AND). Not a magnitude.
- `0x03B6A8` `FUN_0003b66a` — **gate only**; its magnitude use (`0x3B736-0x3B758`) is **dead code**,
  `tp+0x74be` = `0xC64BE` = **0** byte-verified. ⇒ the boost-amplitude index is **not** rate-driven.
- **`0x03AA9C` `FUN_0003aa2c` — THE ONE LIVE MAGNITUDE PATH.** A single load, clamped to ±0x1400
  (5120), **shared by BOTH r24 and r26**, each with its own Q10 gain and its own ±0x2000 clip, summed
  **ungated** (r24/r26 are saturating clips, not zero-range gates — the lowest discontinuity risk in
  the aggregator). ⚠ [INFERENCE] at ~264× gain, a bar oscillation of only ~20 counts at 21 Hz saturates
  the ±5120 clamp — so this lane may be running bang-bang during the mode. Not measured.

## 🛑 The gap that matters: r24 and r26 were each killed ALONE, never together

- **V39** suppressed **r24** — but *conditionally*, via a cave at `0x3AC78`: it bypasses unless driver
  max torque < 320 **and** LKAS is in a mid band. **Not an unconditional lane removal.** → null.
- **V42** zeroed **r26** ("r26 == 0 unconditionally, in every reachable state"), and its own docstring
  says *"WHY r26 AND NOT r24: r24 was already zeroed by V39 and changed nothing on-car."* → null.

**r24 and r26 are two gain-scalings of the SAME clamped signal loaded at `0x3AA9C`.** Killing one leaves
the other carrying the rate contribution, so **each null is uninformative about the lane as a whole.**
No build has ever removed the shared source. That is the decisive, never-performed subtractive test.
⚠ It sits adjacent to two falsified builds — state that plainly rather than presenting it as fresh.

## Monitor risk — clean, verified three ways
No monitor, DTC, or float mirror anywhere cross-checks `gp-0x4f62` against an independent recompute.
`FUN_00036828`'s DTC-0x23 first-difference is self-contained on `gp-0x4f60` (already V52C-repointed) and
never touches the rate. The `cmp r14,r12` @`0x7E858` is the generic shadow-pair integrity idiom, not an
A/B cross-check. `movhi`+`0xfedf` returns **0 matches** image-wide ⇒ no absolute-addressing bypass.
⚠ Static clearance is **not** sufficient on its own — `gp-0x1500` passed two static methods and still
failed on-car. Any RAM cell needs a live probe.

Related: [[accord-v60-null-closes-parametric-pump]], [[accord-a-caveat-can-mutate-into-a-result]],
[[reference-accord-v52c-complete-broad-lowpass]], [[reference_accord_loop_through_torque_sensor_uncompensated]].
