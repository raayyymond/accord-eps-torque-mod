---
name: accord-loop-does-not-close-through-openpilot
description: "★★★★★ SETTLED 2026-08-09: the torsion bar LEADS openpilot's command by 18.5 ms — the loop closes inside the EPS+plant, not through openpilot. 91–98% of bar band power is INCOHERENT with the command ⇒ command-side filtering has nothing to remove. Closes that branch permanently."
metadata:
  node_type: memory
  type: reference
---

The operator's V85-session hypothesis was that a well-engineered EPS would **filter and/or cancel the
LKAS torque signal** where it contaminates the driver-side torque sensor. **The filtering half is now
closed by measurement.**

## The direction test — three independent methods, all agreeing
| band | γ² | K | group delay `cmd→bar` | reading |
|---|---|---|---|---|
| **26–31 Hz** (V80/r66) | **0.783**, crit 0.259 | 11 | **−18.5 ms** [−20.8, +0.75] | **bar LEADS ⇒ ECHO** |
| 26–31 Hz (4 builds pooled) | 0.506, crit 0.057 | 52 | −18.6 ms [−38.5, −0.7] | ECHO |
| 18–22 Hz (pooled) | **0.031**, null floor 0.025 | 52 | undefined | **REFUSED — no coupling at all** |

- **Corroboration on a different channel pair:** openpilot's own reaction lag `ang→cmd` = **+20.21 ms**
  (r² = 0.972). The `cmd→bar` delay is **minus that, within CI** — the signature of closed-loop `H1`
  collapsing to `1/C` when the disturbance originates in the **plant**.
- **Granger (Geweke spectral GC), 82 episodes, 4 builds:** net `bar→cmd` in every band at every lag
  order, CI excluding zero in **9/9** cells. Positive control (`ang→cmd`) returns the known direction at
  **8× the magnitude**.
- **Phase slope:** measured phase *rises* +8° → +69° over 26→35 Hz; any causal forward path with the
  measured ~20 ms delay must *fall* ~65°. Opposite sign.
- **Sensitivity:** the sign survives ±10 ms of deliberate misalignment; a cross-clock calibration pins
  alignment to **0.015 ms**.

## 🛑 The consequence for design
Fraction of torsion-bar band power **incoherent with the command in either direction** (pooled K=52):
**18–22 Hz 96.9% · 6–9 Hz 91.1% · 40–49 Hz 98.3%.**
⇒ **A filter on the LKAS command has essentially nothing to remove.** Do not propose one.
For the 26–31 Hz ring, 49.4% of bar power is shared with the command, but the direction tests say the
bar is the **source** — filtering the response would cut the *return* leg of a loop whose forward leg is
inside the EPS.

## Also refuted
**openpilot's 123 ct/frame slew cap as a limit-cycle source.** It binds 7.53% of engaged frames with
zero exceedances, but a rate-limited cycle at the observed command amplitude predicts **0.75–5.1 Hz
(median 1.34)** against an observed ring of **26.4–30.3 Hz** — off by 20×, and
`corr(predicted, observed) = −0.12`. The ring's apparent preference for cap-binding windows is
**confounded with speed** (cap duty 12.3% in the slowest speed quintile vs 0.4% in the fastest).

## 🛑 INSTRUMENT CORRECTION — supersedes a standing rule
`docs/STATE.md`'s *"`0x18F` is one frame (~10 ms) stale vs `0x14A` — corrects every `cmd`→`bar` phase
ever computed here"* is a **CACHE-EXTRACTOR ARTEFACT, not a bus property.** The panda publishes one
`can` batch per read and **every frame in a batch carries the same `logMonoTime`** (measured age of the
newest `0x18F` at each `0x14A`: mean 0.37 ms, p50 0.00). `extract66` builds one row per `0x14A` and
carries `last18` forward, and `0x18F` sits after `0x14A` in the batch list — hence a full frame.
**Indexing by batch removes it structurally.** ⚠ A sibling measured τ = 9.998–10.001 ms via
`phase(rate_f/rate_c)` **on the cache**, which is correct *for cache-derived work* — the two results are
consistent, they measure the extractor and the bus respectively. **State which you are using.**

## Corrections of record
- *"bar/command ratio at 27 Hz is 15.8×"* is a **tail** value. Distribution over 518 engaged windows:
  **median 2.24**, p5 0.91, p25 1.51, p75 3.54, p95 9.60. Its "+0.93 at lag 0" reproduces, and its
  `[BELIEF] an echo` is now **[EVIDENCE]**.
- The 26–31 Hz cmd↔bar coupling is largely a **V80 phenomenon**: γ² = 0.783 (V80) · 0.442 (V84) ·
  0.044 (V83a) · 0.032 (V81), the last two below their own significance floors.

## 🛑 Open, and named as the highest-value next experiment
**The forward path `cmd → bar` is NOT IDENTIFIABLE from passive data** — in a tight closed loop `H1 → 1/C`
at every frequency, and the low-frequency band does not rescue it (γ² = 0.011). Settling it needs an
**exogenous dither uncorrelated with the bar**. openpilot may not be modified
([[feedback-no-openpilot-side-modifications]]), so the only admissible form is a **firmware-side dither
build**. Tools: `rlog-tools/loop_op_*.py`, cache `_scratch/cache/loop_op/`.
