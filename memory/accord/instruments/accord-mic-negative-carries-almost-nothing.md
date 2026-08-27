---
name: accord-mic-negative-carries-almost-nothing
description: The microphone read 1.061 — inside its null — on grind #1, a large real measured oscillation; a mic positive is informative, a mic negative on a tactile event is not
metadata:
  type: reference
---

🛑 **THE CLEANEST DEMONSTRATION OF THE MICROPHONE'S BLIND SPOT IN THE CORPUS.**

On **grind #1** — an oscillation this kit has measured at **12.87× [9.0, 14.9]** on the torsion bar
over 48 creep events, large, real, and the subject of four builds — the microphone reads

> **1.061 [1.004, 1.233]** un-weighted, against its own null of **[1.03, 1.24]**. **Inside the null.**

The A-weighted channel reads 1.612 against a null of [1.47, 1.96] — also inside.

## The rule this fixes
- **A mic POSITIVE is informative.** Its one validated positive control **replicates**: creep
  grind #2 at **4.59× [2.95, 8.31]** here, by a different estimator and a different control design
  (speed × effort × |rate|-matched), against the **4.14×** already on record. And via the
  A/un-weighted contrast a positive carries **genuine spectral information** —
  [[accord-mic-two-weightings-are-a-filter-bank]].
- **A mic NEGATIVE on a TACTILE event carries almost nothing.** Grind #1 proves the failure mode
  directly: a real, large vibration can move this channel by nothing at all. Never read "the mic saw
  nothing" as "there was no vibration"; it means **"nothing this instrument can hear."**

Reasons already on record that compound it: one RMS over **0–8000 Hz** vs the ear's ~1/3-octave
critical bands is a **26.4 dB** bandwidth penalty for a narrow tone; the highway ambient is ~9.9×
higher in power than the creep floor where the control was validated; and the operator reports
**feeling** the highway symptom, not hearing it. See [[accord-both-instruments-blind-above-50hz]].

⚠ Note the mechanism differs from the 50 Hz ceiling: grind #1 is inaudible here because it is a
**torsional column mode that never radiates**, not because of any bandwidth limit
([[accord-grind1-is-torsional-grind2-reaches-the-chassis]]).

⇒ `analysis-2020accord/studies/grind2/grind2_trichannel.py` §4/§7 · `_scratch/out/_grind2_trichannel.json`.
