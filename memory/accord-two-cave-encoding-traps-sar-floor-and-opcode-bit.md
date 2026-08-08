---
name: accord-two-cave-encoding-traps-sar-floor-and-opcode-bit
description: Two V850 cave-encoding traps caught by build-time gates — sar floors toward -inf so a naive cmp/bgt rung fires 255 counts early on the negative side, and ld.h 0x39 vs st.h 0x3B differ by one bit on a displacement the firmware already uses for a store.
metadata:
  type: reference
---

🛑 **TWO CAVE-ENCODING TRAPS, BOTH CAUGHT BY BUILD-TIME GATES RATHER THAN BY REVIEW.** 2026-08-08.
Neither is exotic; both would have shipped a probe that reads as a measurement and is not one.

## TRAP 1 — `sar` FLOORS TOWARD −∞, so a symmetric-looking rung is asymmetric by 255 counts

A rung written as *"fire when the lane is past ±1024"* is normally coded by shifting right and comparing
the shifted value. **`sar` is an arithmetic shift: it floors toward −∞, it does not truncate toward
zero.** So `sar 8` maps −1024…−769 all to −4, and a naive `cmp -0x4` / `bgt` rung **fires at
r24 ≤ −769, not −1024** — a **255-count asymmetry** between the two arms of what looks like one
threshold.

**The correct immediates:**

| arm | encode | fires at |
|---|---|---|
| positive | `cmp 0x4` / `blt` | **+1024** |
| negative | `cmp -0x5` / `bgt` | **−1025** |

Found by an **exhaustive self-check over all 16,385 values of r24 in ±8192** — which is the right
shape of gate for this: a rung's mapping is small enough to enumerate completely, so enumerate it.
⇒ 📋 **Never reason about a shifted comparator's threshold; enumerate its whole input range in the
builder.**

## TRAP 2 — `ld.h` `0x39` vs `st.h` `0x3B` differ by ONE BIT, on a displacement already used for a store

For `gp-0x6ada`, **the firmware's only other instance of that displacement IS the store**
(`st.h` `64c72695` @`0x3AD5A`), and it carries the same displacement halfword an `ld.h` probe must emit
(`24372695`). **One bit turns a read into a write into a 1 kHz aggregator lane.** Assert the opcode field
**by value**, in the builder **and independently in the verifier** — see
[[accord-aggregator-lane-mirrors-6ada-6adc]], which carries this in full.

## ⚠ AND THE ALIGNMENT VARIANT — `gp-0x6a10` is WORD-ALIGNED

An `ld.w` slip on `gp-0x6a10` **would not fault.** It would silently read `gp-0x6a10` **and**
`gp-0x6a0e` as one 32-bit word and return a plausible-looking number. ⇒ **A probe on `gp-0x6a10` must
assert the operand width by value too** — the CPU will not catch this one for you.
See [[accord-factord-is-the-angle-error-lever]].

Related: [[accord-v850-scan-traps-formatv-and-storezero]] · [[accord-formatv-aliasing-five-false-positives]] ·
[[feedback-decompile-first-then-assembly]] · [[feedback-size-probe-rungs-against-lane-reachable-output]]
