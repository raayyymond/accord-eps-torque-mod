# ★ `FUN_0003a382` is a genuine discrete PID — and its D branch is UNATTENUATED

Traced 2026-07-29 on stock `code.bin` (identical in V55/V56 — only the two `0xC6AFC`/`0xC6AFE` cal
halfwords differ). **Every constant byte-verified two independent ways** (GhidraMCP `read_memory` and a
raw little-endian Python read).

This **supersedes the "three parallel lag stages" framing.** The three branches are not three similar
filters — they are the P, I and D terms of one controller.

```python
# ERR: the residual.  0x3a7ca-0x3a7e6
#   NOTE the correction: bias is a 2-STATE SELECTOR (+8192 / -8192, cal 0xC6200 = 8192 byte-verified),
#   NOT a continuous subtraction of the model gp-0x6ad6. So for AC content faster than gp-0x6ad6
#   crosses that boundary, ERR's AC content IS gp-0x4f60's AC content: unity gain, zero phase.
ERR = clamp(gp_0x4f60 - bias, -0x2800, +0x2800)

# ---- Stage A = PROPORTIONAL ---------------------------------------------- 0x3a7e8-0x3a826
#   mul lp,r8,r0 @0x3a7e8 ; sar 0xa,r8 @0x3a7f4 ; shl 0x5,r8 @0x3a7f6
gainA = LERP(0xC6B26, motor_rate)        # Y = [256, 256, 225, 153], X = [300, 2000, 4000] @0xC6B20
P = ((gainA * ERR) >> 10) * 32
#   its own EMA has pole cal 0xC6450 = 1024 = 2^10, so
#   state += ((P - state) * 1024) >> 10  ==  P   -- an algebraic identity, EVERY cycle, zero phase

# ---- Stage B = INTEGRAL --------------------------------------------------- 0x3a7e6-0x3a83c
gainB = 98                                # 0xC6B12, FLAT (all 4 Y points = 98)
I = I_prev + ((gainB * ERR) >> 10)        # true accumulator, no decay term
I = clamp_to_headroom(I, ceiling, P)      # 0x3a80e-0x3a832 anti-windup, relative to Stage A + ceiling

# ---- Stage C = DERIVATIVE ------------------------------------------------- 0x3a832-0x3a87a
gainC = 2048                              # 0xC6AE6, FLAT (all 4 Y points = 2048 = 2.0 in Q10)
D = clamp(((ERR - ERR_prev) * gainC) >> 10, -0x2800, +0x2800) * 32
#   its own smoothing pole cal 0xC644A = 1024 -> identity again, same trick as Stage A
#   => the RAW backward difference reaches the combine UNATTENUATED

# ---- Combine + bound ------------------------------------------------------ 0x3a874-0x3a8a0
combine = (((D + I + P) >> 5) * gainD) >> 10
combine *= polarity(gp_0x6752)            # = +1, boot-fixed, see below
gp_0x6ad4 = clamp(combine, -ceiling, +ceiling)   # ceiling = the 0xC6AF0 LERP mechanism
```

🛑 **What the two `1024/1024` cals actually mean.** They are each stage's *own extra smoothing EMA*, and
both collapse to identity. That does **not** mean "no derivative action" — it means the derivative's
extra smoothing is defeated, leaving the **raw** derivative in the sum. V43 (`0xC644A`→64) and V46
(`0xC6450`→32) were each re-introducing one of those defeated poles.

## Frequency response, fs = 1000 Hz

`H(z) = [ gainA/1024 + (gainB/1024)/(32(1−z⁻¹)) + (gainC/1024)(1−z⁻¹) ] · gainD/1024`

Cross-validated two ways (closed-form z-transform and a time-domain sinusoid sim), agreeing to 4 dp:

| gainA | 3 Hz | 5 Hz | 8 Hz | 21 Hz |
|---|---|---|---|---|
| 256 (low motor rate) | 0.279 / −25.7° | 0.255 / −7.3° | 0.257 / **+9.2°** | 0.361 / **+41.8°** |
| 225 | 0.252 / −28.6° | 0.225 / −8.3° | 0.228 / +10.4° | 0.339 / +45.2° |
| 153 (high motor rate) | 0.194 / −38.7° | 0.155 / −12.0° | 0.159 / +15.0° | 0.294 / +55.0° |

Per-branch (gainA=256): **P/32 = 0.250 flat at every frequency**; |I|/32 falls 0.159 → 0.023 from
3→21 Hz; |D|/32 rises 0.038 → 0.264. ⇒ **P-dominated in the few-Hz band; by 21 Hz D rivals P**, pulling
net phase to a +42°…+55° lead.

⚠ **This contradicts the recorded "net phase −3.3° to −5.4°, P dominates I+D by 8-10:1"** in
[[reference-accord-fun3a382-unfiltered-residual-lane]]. The new figure is cross-validated twice; the old
one is hand-symbolic and may have been evaluated at a lower implicit frequency. **Treat the table above
as authoritative and re-derive before quoting the old number.**

## The sign into the aggregator — PROVEN, no inversion

`FUN_0003aa2c` at `0x3aca8`-`0x3acda`:
```
0x3aca8  ld.h -0x6ad4[gp],r6
0x3acbc  addi 0x2800,r6,r9        # range-validity check |gp-0x6ad4| <= 0x2800
0x3acc4  cmovc 0x0,r6,r13         # in-range ? value : 0   <- a GATE, not a sign flip
0x3acd8  add r13,r7               # folded in by PLAIN ADD
0x3acda  add r7,r28               # running grand total
```
**All 9 aggregator lanes** (`gp-0x6b62, -0x6b4c, -0x6ade, -0x6ad4, -0x6b26 friction, -0x6bbe boost,
-0x6bd0 damping, -0x6b86`, plus `FUN_00036682`'s return) reach the sum through a plain `add` — **not one
`sub`**. Polarity `gp-0x6752` is set to literal `1` at boot in `FUN_000490ac` (`0x490b6`-`0x490c0`),
shadow-checked against `gp-0x4c2d`. ⇒ **polarity = +1 in normal running**; `gp-0x6ad4` carries the same
convention as the lanes already labelled boost/friction/damping.

## How to apply

- The lane is **eliminated as the 21 Hz source** by V56's branch-agnostic mute —
  [[reference-accord-v56-flashed-mute-is-null-and-costs-damping]]. Do not re-propose it.
- **The 9-lane `add` list is the next search space**: the 21 Hz enters `gp-0x6b98` through a different
  summand, and every one of them is now enumerated.
- **What firmware cannot settle:** whether a P-dominated few-Hz contribution nets out as damping once it
  passes the real motor→rack→column plant. That needs the plant transfer function, which is not in the
  binary. The on-car result is doing that work today.
- Open, flagged honestly: `gainD` (L4, `tp+0x77b0` region) is inherited as ~1024/no-op from an earlier
  session and was **not** independently re-read. It is a uniform scalar so it changes neither phase nor
  the P:I:D balance, but byte-read it before building on its exact value.
