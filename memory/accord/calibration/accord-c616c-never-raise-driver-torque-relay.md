---
name: accord-c616c-never-raise-driver-torque-relay
description: "0xC616C (tp+0x716c) = 0 is a NEVER-RAISE cell. It is virgin on every build and looks like a free untried lever, but it feeds r14 = sign(driver torque) x constant into the driver-feel reference gp-0x6ad6 via gp-0x6b76 -> mixer lane 2 -> gp-0x6b4a -> term 0. Raising it turns that into a Coulomb relay on DRIVER-TORQUE SIGN — the V80 class, arguably worse than 0xC4080. Zero is the safe, shipped value, and it is also what makes mixer lane 2 structurally inert today."
metadata:
  type: reference
---

# 🛑🛑 `0xC616C` = 0 — NEVER RAISE. Traced 2026-08-11.

**A future session WILL find this cal at 0, virgin across every build, and be tempted to read it as
"a free, never-tried, unclipped lever." It is not.**

## The idiom it feeds

`FUN_00033d10`'s tail block (`0x33fec`–`0x3402c`), all three branches traced to their final register:

```
r14 = (gp-0x4f60 > 0) ?  cal(tp+0x716c)
    : (gp-0x4f60 < 0) ? -cal(tp+0x716c)
    :                    0
```

i.e. **`r14 = sign(driver torque) × constant`**, stored to `gp-0x6b76`.

`tp+0x716c` = `0xBF000 + 0x716C` = **`0xC616C`**. Read directly from the image: bytes `00 00` = **0**,
confirmed identically on stock `code.bin` and on the flown V90 image, and confirmed untouched by every
build (`grep 716c\|C616C analysis-2020accord/build_v*_tva.py` → **0 hits**).

⇒ **`r14 = 0` in all three branches, unconditionally**, so `gp-0x6b76` always holds either `0` (gate
open) or `0x7fff` (gate closed — a fault sentinel, itself caught and zeroed by `FUN_0003405a`'s own
first gate, `iVar7 > 0x5000`).

## Why raising it is the V80 class

`gp-0x6b76` → mixer lane 2 (`gp-0x62e0[2]` → `gp-0x6298[2]`) → **`gp-0x6b4a`** → **term 0 of
`FUN_00037fe6`** → **`gp-0x6ad6`, the driver-feel tracking reference**. Term 0 is unweighted and its
gate window equals the cell's own final clamp, so it can drive the reference to its full rail alone.

**Raising `0xC616C` off zero injects a Coulomb relay on DRIVER-TORQUE SIGN straight into that
reference.** That is exactly the class of lever this kit has spent fifteen builds removing — **V80:
"the worst grinding the car has ever produced"**, from a relay in this same class.

🛑 **It is arguably worse than the standing `0xC4080` (K0) NEVER-RAISE cell**, because this one relays
on **driver-torque sign** specifically, which **reverses on every micro-correction at the wheel** —
the exact input this kit's ratchet and grind investigations have shown is richest in sign reversals.

## The corollary: mixer lane 2 is INERT today

Because `0xC616C` = 0, **lane 2's contribution to `gp-0x6b4a` is unconditionally zero, on every path**,
regardless of the resolver dynamics feeding it. The elaborate resolver-derived PID cascade upstream
computes correctly every cycle and lands in **`gp-0x6b78`** — a cell whose only two readers are inside
`FUN_0003405a`'s internal state machine and which never reaches `gp-0x62e0[2]`. A frequency/phase
characterisation of lane 2 is therefore **moot**: there is no signal to have a phase relationship with.

⊕ **Supporting the "deliberately shipped disabled" reading [BELIEF — statics cannot distinguish
deliberate from accidental]:** two *other* gains inside the same cascade are also exactly `0.0`
(`0xC60C4` K_D1 and `0xC60BC` K_D3), and a third stage-2 derivative gain `0xC60CC` is `0.0` too. Three
unrelated zeroed gains inside one elaborate, fully-built filter is more consistent with an intentional
disable than with an accident — **but that is a plausibility argument, not a traced fact.**

**Zero is the safe, shipped value.**

Source: `docs/review/REDTEAM-2026-08-11-term0-verdict.md`, addendum.
Related: [[accord-gp6b4a-is-a-second-direct-lkas-term]] · [[accord-v80-damper-relay-and-grind1-inert]] ·
[[accord-six-levers-closed-on-arithmetic]] · [[accord-gp6afe-gp6b4e-are-always-zero]]
