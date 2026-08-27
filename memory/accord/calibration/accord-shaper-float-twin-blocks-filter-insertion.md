---
name: accord-shaper-float-twin-blocks-filter-insertion
description: "FUN_00043e44 is a float twin of the shaper with a ±5-count tolerance and a 10 ms dwell that raises an EPS-DISABLING DTC. Any filter between gp-0x6acc and gp-0x6b98 trips it — the two best hook sites are inside its coverage."
metadata:
  node_type: memory
  type: reference
---

🛑🛑 **A FILTER IN THE SHAPER DOES NOT BRICK THE ECU — IT SWITCHES OFF THE POWER STEERING WHILE
DRIVING.** This is the V74/V75 loss-of-assist class, and it closes the cave route that every
filter-design line of reasoning converges on.

**`FUN_00043e44` is a FLOAT TWIN of the integer shaper** [EVIDENCE, orchestrator-verified by decompile]:
- It reads **`gp-0x6acc` at `0x4467a`** with an ±8.0 (=8192 count) range gate.
- It applies the **SAME** `0xC64C8` mode byte and **SAME** `0xC61D4` cal that the shaper loads at
  `0x431CC` / `0x431C8` — that is what makes it a twin rather than a coincidence.
- It compares against the delivered command with tolerance **`0.0048828125` = 5/1024 counts**,
  contributing **32.0** to a bit-weighted accumulator (1/2/4/8/16/32/64).
- A state machine dwells on `gp-0x3550`, incrementing **0.001 s per 1 kHz tick**, and at
  **`0x3c23d70b` = 0.01 s** escalates by adding **1024.0** against a **128.0** threshold ⇒
  `FUN_000462e6(0x3f1b)` ⇒ **DTC 0xF00049.**

⇒ **Any filter inserted between `gp-0x6acc` and `gp-0x6b98` diverges from the twin by its own filter
error. At 8 Hz a half-cycle is 62 ms — SIX TIMES the trip dwell.**

## 🛑 THE TWO "BEST" HOOK SITES ARE INSIDE ITS COVERAGE
A cave survey ranked `0x431C4` (shaper reads `gp-0x6acc`) **#1** and `0x43206` (shaper writes
`gp-0x6b08`) **#2**, with byte-exact `jarl` encodings ready. **Both sit below the twin's branch point at
`0x4467a`.** `gp-0x6b08` looks especially attractive — it is the narrowest node in the chain (1 writer /
2 readers, all inside `FUN_00042af8`, no lockstep shadow) — **and it is the one node that must not be
used.** Narrowness is not safety.

**Measured phase budget inside that region: 2.4°** (from `A·|1−H| < 5` at the ratchet's ~120-count
amplitude). **No useful filter exists in 2.4°.**

## ✅ WHERE A FILTER *COULD* GO
**`0x453e0`, the read of `gp-0x6b94`** — the only monitor-clean single-instruction site on the spine.
Filtering there leaves `gp-0x6b94` itself untouched, so `0x4595e`'s float identity check stays
consistent, and everything downstream (`gp-0x6ace` → `gp-0x6acc` → the twin → `gp-0x6b98`) **re-derives
from the filtered value**, so all three monitors see a self-consistent chain.
⚠ Still a code cave ⇒ GATE 1 + GATE 2 mandatory.

## ⊕ OTHER MONITORS ON THIS SPINE, none previously in kit memory
- **`0x43ab4`–`0x43ad6`** — one-sided overshoot (`|slewed| > |raw| + 5` → fault tag 0x10) plus a
  sign-agreement test with a ±5 deadband. ⇒ **attenuation between `gp-0x6b08` and the output is
  permitted; amplification is not.** Any filter with >5 counts of step overshoot trips it — that alone
  rules out Butterworth ≥2nd order and any sharp/resonant filter at that node.
- **`FUN_00041b8e`** — a float redundant recomputation of the rate chain, ±5.0 tolerance, using the
  **SIGN of `gp-0x6b98`** as a motoring/regenerating discriminator; reports via `FUN_000462e6` ids
  `0x43b7`/`0x43b5`/`0x43b3`/`0x3f5e`.
- **`FUN_000370b6`** — `gp-0x6bb0 = EMA(gp-0x6b98)`, cal `0xC40C0`, with **two** lockstep shadows.

## ⊕ THE FOC BRIDGE IS `ep`-RELATIVE — why every gp-relative hunt returned null
`0x6136e`: `mov r24, ep` ; `sld.hu 0x0[ep], r7` ; `st.h r7, -0x4e1c, gp`. **The PWM duty values arrive
through a pointer in `r24`.** Same failure shape as the `gp-0x6acc` miss, one level deeper.
[BELIEF] that torque magnitude reaches PWM through that buffer; one backward trace from `0x61372` closes it.

Related: [[accord-v87-built-measurement-on-v38-base]],
[[accord-aggregator-reaches-motor-via-gp6acc-bridge]], [[accord-c407e-is-the-fault-interlock-c63a0-exonerated]].
