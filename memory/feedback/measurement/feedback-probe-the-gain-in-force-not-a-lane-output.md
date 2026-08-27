---
name: feedback-probe-the-gain-in-force-not-a-lane-output
description: "🛑 FOUR consecutive probes returned an uninterpretable zero by reading a lane OUTPUT. V70's bit6 is not vacuous (replay predicts 311 hits, stock 52, observed 0) — but the SAME rung read 0/47,990 on V69 at double the dose, which arm-selection cannot explain, so [BELIEF] a mis-reconstructed rung is the better reading. The durable part is the rule: spend a probe bit on the SELECTOR/MASK first."
metadata:
  type: feedback
---

# 🛑 READ THE GAIN IN FORCE, NOT A LANE OUTPUT

**Four probes in a row have now returned an uninterpretable zero by reading a lane output:** V64, V67
and V68 (`gp-0x67df`, the oscillation detector), and **V70's bit6** (`gp-0x6ada >= +512`, **0/18,010**).

## ★ V70's is the informative one, because it is NOT vacuous [EVIDENCE]
A replay through the **shipped** surface, driven by **route 50's own data**, predicts **311 hits**;
**stock predicts 52**; **observed 0**. And `|dtorque|` computed off a 100 Hz grid is a **LOWER** bound,
so **the gap cannot be closed in the safe direction.**
⇒ **delivered gain < ~1574 Q10, below stock's 3072** ⇒ **`0xC6442` = 1024 — the `gp-0x671d` mask arm —
is the ONLY arm in the selector that predicts exactly 0.**

✅ **The identification was verified first-hand and is not at fault:** `0x3AC42`–`0x3AC54` is
`r24 = clamp(r6, ±0x2000)`, and `0x3AD5A st.h r24,-0x6ada,gp` stores exactly that, with r24 unclobbered
through the add chain.

## ⚠⚠ BUT ARM SELECTION IS THE WEAKER READING — softened 2026-08-04
**The same rung read 0 / 47,990 frames on V69's route `4f`, at DOUBLE V70's dose**, where it needed only
**49 counts** of `|dtorque|` against a repo max of **839**. **That anomaly is far larger, and it does
NOT fit arm selection:** under (b) the mask arm is **1024 on every build**, so it cannot produce a
**dose-dependent** miss. And **V67 read `gp-0x671d` 0 / 150,327 on route 47**, so the mask would have to
be set near-continuously on `4f` *and* `50` but never on `47`.
⇒ **[BELIEF] (a) — an under-ranged or MIS-RECONSTRUCTED rung — is the better-supported reading.** The
`dtorque` figure is a **4-sample 1 kHz difference rebuilt from a 100 Hz bus copy of a different,
filtered torque cell**; **polarity** is the other candidate.
**(b) arm selection is possible but less parsimonious. The corpus cannot settle it** — and grind #1
cannot adjudicate it either, being **blind to r24 gain**
([[accord-r24-r26-two-selectors-one-gate]]).

## The rule
> **Spend a probe bit on the SELECTOR / MASK that decides which gain is in force, BEFORE spending one on
> the lane's output.**

A mask bit is **one bit and never ambiguous**. An output null cannot separate *"the lane is quiet"* from
*"the gain you think you shipped is not the gain in force"* — and this kit has now burned four rungs on
exactly that ambiguity.

**V71's `bit6 = gp-0x671d != 0` is the first rung in this kit built to that rule** — and it carries a
**two-sided, low-threshold r24 mirror rung** alongside it, so an under-ranged reconstruction cannot hide
again. Filed as **GATE 4 for probes** in `docs/BUILD-LINEAGE.md` Part 2.
🛑 **The DURABLE part of this note is the rule, not the mechanism** — the mechanism behind the four
zeros is still open.

⊕ **This is the companion to, not a replacement for,
[[feedback-size-probe-rungs-against-lane-reachable-output]]** (GATE 3: size the threshold against the
producing lane's own ceiling) and [[feedback-probe-the-gate-not-just-the-output]] (budget bits for the
enable and the raw input). GATE 4 says **which cell**; GATE 3 says **which threshold**.

See [[accord-r24-r26-two-selectors-one-gate]], [[accord-v70-flew-grind1-back-at-stock]],
[[feedback-telemetry-must-reserve-a-did-not-fire-value]].
