---
name: accord-ram-lerp-is-flash-derived-and-fprime-is-nonneg
description: STATE.md's "the transfer cannot be read from the image" is FALSE — the RAM LERP is 100% flash-derived, and f' >= 0 is ENFORCED IN CODE at three ungated sites, so it holds for any cal, any mode, any build. Closes a blocker that stopped three sessions.
metadata:
  type: reference
---

🛑 **`STATE.md` §A6b's *"the transfer cannot be read from the image"* is FALSE, and it blocked three
separate sessions.** The LERP in `FUN_00038148` is **100 % flash-derived**:

```
FUN_000382d8 @0x382d8   SOLE WRITER of both source arrays.
  mode  = byte at gp+0x63fd
  brk   = *(int*)(0xCC9FC + mode*4)                      7 speed breakpoints
  recs  = *(int*)(B + mode*4) for B in 0xC7B40 0xC7C28 0xC7D10 0xC7DF8 0xC7EE0 0xC7FC8 0xC80B0
  record: +0x00 count(=9), +0x02..+0x12 nine X shorts, +0x14..+0x24 nine Y shorts
  writes gp-0x6350[0..8] (Xsrc), gp-0x630c[0..8] (Ysrc)
FUN_000389ec @0x389ec   rescales into gp-0x64b8[0..9] (X) / gp-0x641c[0..9] (Y)
FUN_00038148 @0x38148   reads exactly those.        BOTH ENDS VERIFIED.
```
It is a **2-D flash table interpolated on vehicle speed, selected by the mode byte** — nothing dynamic.

## 🛑 `f′ ≥ 0` IS A PROPERTY OF THE CODE, NOT OF THE NUMBERS [EVIDENCE]
Honda enforces monotone-nondecreasing Y at **three independent, ungated sites**:
- `FUN_000382d8` from `0x388c4`: **eight consecutive** `Ysrc[i] = max(Ysrc[i], Ysrc[i-1])` rungs
- the float interp branch: `if (i != 0 && y < prev) y = prev`
- `FUN_000389ec`: `Y[i] = max(Y[i], Y[i-1])` at `0x38de2`→`0x38f68` and `0x38e48`→`0x38e4c`,
  plus `Y[i] = min(Y[i], cal 0xC6200 = 8192)` at `0x38e9c`
- `X[0]` and `Y[0]` are hard-stored zeros at `0x38d1c` / `0x38d22`

⇒ **Y is non-decreasing for ANY cal values, ANY mode, ANY speed, on ANY build.** The flash data agrees
with margin: **14/14 records (7 speeds × 2 modes) strictly increasing in both X and Y**
(orchestrator-verified from the V96 image; anchors `0xC6468`=2639, `0xC40BC`=600, `0xC6200`=8192,
`0xC63AC`=102 all exact). Mode 24 rec[0] Y = `[0,471,880,1408,1689,1953,2376,2844,4181]` — a concave,
saturating boost curve, **steepest near the origin** (first-segment slope ≈ 2.36), which is where the
micro regime sits. Hands-off, `|iVar6|` is small ⇒ `f′ ≈ 2.86`.

**Closed form:** `sign(d(gp-0x6b70)/dW_i) = −sign(f′)·sign(polarity)·sign(lane_i)`, with `sign(f′)`
now **known and fixed at +**.

## ⊕ AND "THE 8 FLOAT COEFFICIENTS OF `FUN_0003b8f6`" NEVER EXISTED
It is **3 floats + 6 halfword Q-format cals** (type read from the opcode: `ld.w`+`mulf.s` vs
`ld.hu`+`cvtf.uws`). **Two of the three floats are hard ZERO**, so the 3-tap FIR is an **IDENTITY** —
unity gain, 0.000° at every frequency. The handover that named eight also **omitted `0xC4048`, the
only nonzero tap.** The real dynamics are four one-pole IIRs:
`0xC40D0` = 408 (friction) · `0xC40D4` = 573 (torque, ×2 cascaded, **V86 took it to 286 and was
FALSIFIED**) · **`0xC40D6` = 246 — corner 9.86 Hz, −73.9° at 7.79 Hz, the dominant phase element,
VIRGIN 92/92** · `0xC40D8` = 3686 (**a NO-OP, −0.6°; kill any proposal to move it**).

🛑 **No cal inside `FUN_0003b8f6` is a good bet for the 7.79 Hz ring**, including `0xC40D6`: it shapes
the **`A` branch (`gp-0x6bfe`)**, and `arg(V) − arg(B′) = −178.1°` shows the **B** branch sets the
phase. V86 already flew a −32.1° rotation of `A` and scored **1.001 [0.976, 1.060]** — **a real null on
a live lane** (its own probe: gate duty 1.0000, nonzero 0.9975). ⚠ An earlier "closed-loop
suppression" explanation for that null was **retracted** — it contradicts the measured 2.8×
amplification (if engaging multiplies 6–9 Hz by 2.8× then `|1+L| < 1`, so internal perturbations are
**amplified**, not suppressed). The correct explanation is **branch authority**.

⚠ `gp-0x6bfe`/`gp-0x6bfa` are real, distinct, live cells (`0x3bc3e`; `0x273b0`/`0x273c8`/`0x273d6`) —
**not** an off-by-2 on `6bfc`/`6bf6`. V96's pre-registration stood on the right cells.

Links: [[accord-v97-is-a-loop-pole-and-the-direction-is-measured]] ·
[[accord-v96-flew-as-7e-7f-and-the-record-said-v94]] · [[accord-gp6b26-is-inertia-not-damping]]
