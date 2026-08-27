---
name: accord-rate-channel-rule-and-its-scope
description: "Which bus rate channel to use, and it depends on the QUESTION. For PHASE/IMPEDANCE use rate_f (0x18F) — tq and rate_f share a frame so the skew cancels exactly; using rate_c instead INVERTS the sign at 18-22 and 26-31 Hz at identical coherence and would have produced the opposite build decision. For ABSOLUTE MAGNITUDE use rate_c (0x14A) — rate_f reads ~24% LOW (slopes 0.743-0.767 vs 0.952-0.963 against differentiated angle). Always state which channel you used."
metadata:
  type: reference
---

# The rate-channel rule — and it is SCOPED. Settled 2026-08-11.

🛑 **There is no single "correct" rate channel. It depends on the question, and getting it backwards
inverts an answer.**

## For PHASE and IMPEDANCE work → `rate_f` (`0x18F`)

`tq` and `rate_f` are **both fields of the same held `0x18F` frame** (`last18[0]`/`last18[1]` in the
extractor), so the ~9.15 ms staleness is **common to numerator and denominator and cancels exactly**
in `Z = S_Tω/S_ωω`. `rate_c`/`ang`/`wang` come from `0x14A` and carry the relative delay.

**Proved, not asserted:** recomputing `Z` with `rate_c` separates the phase by exactly the skew —
−11.1° vs −9.9° predicted at 3 Hz, −100.1° vs −93.9° at 28.5 Hz, −116.6° vs −108.7° at 33 Hz.

> **Had `rate_c` been used, 26–31 Hz would read −30.3° instead of +69.6°, giving `+0.184 PUMPING`
> instead of `−0.336 DAMPING` — the OPPOSITE BUILD DECISION, from the same data, at the same
> coherence (0.827 vs 0.834). Same flip at 18–22 Hz (+45.8° ⇒ +0.180 PUMPING).**

That is the sign that closed the `Kd` cut. It rests entirely on this channel choice.

## For ABSOLUTE MAGNITUDE → `rate_c` (`0x14A`)

Regressed on the differentiated **angle** (`0x14A`, 0.1 °/count — a solid LSB anchor), four routes:

| channel | slope vs d(angle)/dt | r |
|---|---|---|
| **`rate_f` (`0x18F`)** | **0.743 · 0.756 · 0.763 · 0.767** | 0.96–0.98 |
| **`rate_c` (`0x14A`)** | **0.952 · 0.958 · 0.962 · 0.963** | 0.98–0.99 |

⇒ **`rate_f` reads ~24 % LOW.** The kit's old "`rate_f` scale ~25 % low" note is **confirmed and
pinned to that channel specifically**. Any counts-per-°/s or absolute-amplitude claim built on
`rate_f` is ~24 % under.

## 🛑 STATE WHICH CHANNEL YOU USED, EVERY TIME.

A phase result quoted without naming its rate channel is not checkable, and this session showed the
two channels can disagree on the **sign**.

Source: `docs/scoring/SCORING-2026-08-11-v90-flight.md` §4 (the rule), §4.1b (the proof), §12.2 (the scope
correction). Related: [[accord-averaged-spectrum-needs-matched-speed-distributions]] ·
[[accord-raw14-offbyone-in-every-cache]] · [[feedback-run-the-control-before-the-measurement]]
