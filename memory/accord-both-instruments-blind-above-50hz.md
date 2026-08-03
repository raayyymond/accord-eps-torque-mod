---
name: accord-both-instruments-blind-above-50hz
description: CAN and the comma IMU both Nyquist at ~50 Hz with no usable headroom between them; the microphone is the only uncapped instrument, and it has a validated positive control
metadata:
  type: reference
---

🛑🛑 **EVERY *VIBRATION* INSTRUMENT THIS KIT HAS IS BLIND ABOVE ~50 Hz — but the MICROPHONE is not.**

| instrument | measured rate | **Nyquist** |
|---|---|---|
| CAN `0x14A` / `0x18F` grid | **100.000 Hz exactly** | **50.00 Hz** |
| comma IMU accelerometer (LSM6DS3TR-C) | **101.02 Hz** | **50.51 Hz** |
| **comma MICROPHONE** (`soundPressure`, 10.000 Hz level) | **0–8000 Hz analysed** (⚠ corrected — see below) | **no ~50 Hz ceiling** |

⚠ **Corrected 2026-08-03.** My earlier 99.9–100.5 Hz came from the dt **mean**; ~1% of IMU samples are
**dropped**, inserting 20/30 ms gaps that inflate the mean but not the **median** (9.899 ms → 101.02 Hz).
Settled by test: lattice-fit residual **77 µs** median-seeded vs **2889 µs** forced to 100.03 (38× worse),
and a synthetic fold test sampling known tones at the *actual* timestamps — **7 of 7 fold per 101.02 Hz**.

⇒ The IMU has **0.51 Hz** of headroom over CAN, which is **not usable**. ★ And headroom is the wrong
quantity anyway: 55.6 Hz appears at 44.400 on CAN and 45.421 on the IMU while 44.9 Hz appears at 44.900
on both, so the discriminant is that **1.021 Hz apparent-peak difference**. Measured paired shift over
the 120 loudest windows: median +1.677 Hz, **sem 0.856**, where ≪0.34 is needed. **Resolving the alias
needs a log at a different IMU ODR (208/416 Hz)**, not more of the same data.
⚠ The IMU was introduced as the independent sensor for grind #2, and it genuinely is independent of the
EPS *signal path* — but it is **not** an independent *bandwidth*. Those are different properties and the
record conflated them.

## Two consequences that must be carried into every future analysis

1. **A null above ~50 Hz on CAN or the IMU is not a null — it is silence.** (The microphone escapes this;
   see below.) If a felt vibration is genuinely above 50 Hz,
   no measurement in this kit can see it, and any "we measured nothing" statement is only about the
   observable band. State that limit explicitly rather than letting the null read as an absence.
   This is live right now: the operator reports a highway resonance that shows **no** signature in
   either channel (see [[accord-v67-flew-both-grinds-fixed]]).

2. **IMU/CAN frequency agreement carries ZERO information about the alias.** Grind #2's "44.9 Hz" is
   aliased — 44.9 and ~55.6 Hz are the same observation on a 100.5 Hz grid — and because the two grids
   are only **0.5 Hz apart**, agreement between them cannot break the degeneracy. Never quote it as if
   it could. A dedicated fold test and a Lomb–Scargle test on true arrival timestamps both came back
   underpowered.

## What would actually break the barrier
The firmware's own control task runs at **1 kHz**. A probe that samples inside that task and reports a
**sticky / accumulating** flag on the 100 Hz CAN channel — e.g. a bit latched when `|gp-0x4f62|` crosses
a threshold and cleared when the payload is written — would report HF *energy* without aliasing.
🛑 It needs a RAM cell, so **GATE 1 stops being vacuous**, and that is the class that bricked V24/V27/
V48B. `gp-0x1500` passed both static clearance methods and still failed on-car. Prove ownership two ways
or do not build it.

★★ **THE PRACTICAL ANSWER IS THE MICROPHONE, and it is already validated.** `soundPressure` is computed
on-device as **one RMS over 1600 samples of 16 kHz PCM ⇒ 0–8000 Hz analysed**, published at 10.000 Hz —
no spectrum, but no ~50 Hz ceiling.

🛑 **CORRECTED 2026-08-03, and the correction changes how much this channel is worth.** This file
previously said *"audio at **16–48 kHz**"* in both the table above and here. That is wrong: `micd.py`
samples at 16 kHz, so 8 kHz is the analysis ceiling, not the floor. **Why it matters** — the argument
that downgrades the microphone null is a **bandwidth penalty**: one RMS over **0–8000 Hz** versus the
driver's ear resolving ~1/3-octave critical bands is a **26.4 dB** disadvantage for a narrow tone. That
arithmetic *depends* on the band being 0–8 kHz. **Anyone still reading "16–48 kHz" will over-weight the
null** — they will think a null covers a band the sensor never analysed, and conclude "nothing is there"
where the honest statement is "this instrument could not have seen it." Combined with a 64× validation
gap (validated at creep, where the acoustic floor is 9.9× lower in power), the microphone bears very
little weight on a **tactile** event the operator feels but does not hear.
It has a **working positive control**: on the creep grind #2 it reads **4.14×** un-weighted p95 and
**+9.7 dB(A)** burst-vs-quiet. 🛑 **A-weighting is the trap** — the A curve is −30 dB at 50 Hz, so
`soundPressureWeighted*` suppresses exactly the band of interest; the **un-weighted** channel is primary,
and *un-weighted up with A-weighted flat* is itself the low-frequency signature.
See `analysis-2020accord/r47_microphone_test.py` and `extract_sound_cache.py`.

Raising the comma's IMU sample rate would also work but is **out of bounds** — no openpilot-side
modifications ([[feedback-no-openpilot-side-modifications]]).
