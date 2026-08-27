---
name: reference_accord_tau_env_fills_the_2to13hz_gap_amplitude_modulation
description: "The 2-13 Hz (75-500 ms) 'ratchet-on-top-of-vibration' timescale is NOT in the firmware -- it is the 21-26 Hz mode's OWN amplitude envelope, tau_env = Q/(pi*f) = 171-440 ms for the measured Q 14-29. A ceiling-collapse relaxation cycle then modulates at 2*tau*ln(R) = 2.8-7.2 Hz, hitting 7.19 Hz unfitted against the kit's measured 7.79 Hz ratchet. Carries the falsifiable discriminator f_mod ~ f_carrier/Q (no firmware time constant can mimic it) and the sideband test that separates it from the old resonance."
metadata:
  type: reference
---

# The two-decade gap is filled by the PLANT, not by any line of code

Derived 2026-08-22 after the orchestrator asked what lives in the **75-500 ms (2-13 Hz)** band, having
found only fast elements all session. Operator's description: *"the vibration comes in and out... the
ratchet-like oscillation shows up on top of it"* — i.e. **amplitude modulation of the 21-26 Hz mode**,
not an independent slow oscillation.

## The firmware side of the gap is near-empty — EVIDENCE
Everything I characterised in the governor/ceiling/authority chain (stock `code.bin`):
| element | value | timescale |
|---|---|---|
| `gp-0x6ac0` rate EMA, `FUN_00041464`, cal `0xC643C`=37 Q7, 1 kHz | alpha = 37/128 | **tau = 2.93 ms** (f_-3dB **54.83 Hz**) |
| governor OUTPUT slew, `FUN_0004503c`, cals `0xC6206`=512 / `0xC6208`=205 | **asymmetric — limited only AWAY from zero** | full 512->4762 in **8.3 / 20.7 ms** |
| authority ramp final limiter, cal `0xC6492`=33 ct/tick, rising-only | 32768/33 | **993 ms** |
| authority slot-2 steps, cals `0xC6438`=33 / `0xC6436`=3 | via setter `0x45648` | 993 ms / 10.9 s |
| authority slot-0 step, cal `0xC6454`=32768 | via setter `0x45648` | **1 tick — instant** |

⇒ **2.93 ms, 8.3-20.7 ms, then a jump to 993 ms.** Nothing attributable in 75-500 ms.
⚠ **One BELIEF-grade lead, deliberately NOT claimed:** `0xC6434` = **144 -> 227.6 ms = 4.4 Hz**, adjacent
in the same cal block. **Adjacency is worthless here** — the same block holds `0xC6444`/`0xC6446` = 512,
which this kit knows are *not* ramp cells (`0xC6444` FALSIFIED as V71c; `0xC6446` is Lever B's arm).
Closing it needs Ghidra to define `0x44600-0x45700` (a MUTATING action; not taken).

## ⭐ What actually lives there: the mode's own envelope
For a lightly-damped second-order mode the amplitude envelope decays as `exp(-zeta*w_n*t)`, so with
`Q = 1/(2*zeta)`:

```python
tau_env = Q / (math.pi * f)      # seconds; amplitude envelope e-folding time
```
Using the kit's own measured resonance ([[accord-ratchet-is-a-lightly-damped-resonance]]: **Q ~ 14-29**,
ring-down **zeta 0.017-0.036**, the only estimator that passed its control; carrier **21-26 Hz**):

| Q | f | tau_env |
|---|---|---|
| 14 | 26 Hz | **171 ms** |
| 14 | 21 Hz | **212 ms** |
| 29 | 26 Hz | **355 ms** |
| 29 | 21 Hz | **440 ms** |

**171-440 ms — the entire gap, supplied by the mode itself.**

## The relaxation period it predicts
Firmware collapses the ceiling fast (~0 ms) and recovers in 8.3-20.7 ms; the *mode* must then decay and
regrow. For an amplitude swing of factor `R`, period = `2 * tau_env * ln(R)`:

| swing R | Q=14, f=26 | Q=29, f=21 |
|---|---|---|
| 1.5x | **7.19 Hz** | 2.81 Hz |
| 2x | 4.21 Hz | 1.64 Hz |
| e | 2.92 Hz | 1.14 Hz |

⇒ **2.8-7.2 Hz for a modest 1.5-2x swing.** `R=1.5, Q=14, f=26` gives **7.19 Hz** against this kit's
measured ratchet median of **7.79 Hz** — **unfitted**; it falls out of Q, f and the firmware's own
fast-collapse/slow-regrow asymmetry. **This is why no firmware element was ever found in the band: there
does not need to be one.**

## 🛑 The objection I pre-empted, and the test that settles it
`accord/mechanism/accord-ratchet-is-a-lightly-damped-resonance.md` reports a calibrated peak-aligned Welch ladder reading
the car at **20.9** vs a pure tone at **53.8** and a bursty **AM** tone at **52.1-52.5** => *"limit cycle
EXCLUDED"*. **That control was aimed at the 8 Hz LINE (is *it* AM?), not at the 21-26 Hz CARRIER being
AM'd.** Different object; the ladder was not pointed at it.

**Discriminating tests — both free, on data already in hand:**
1. **Sidebands.** True AM of carrier `f_c` at `f_m` puts energy at **`f_c +/- f_m`**, not at `f_m`. Look
   for **~14-19 Hz and ~28-34 Hz** sidebands whose amplitude tracks the 22-26 Hz carrier.
2. **Envelope demodulation.** Band-pass 20-28 Hz, take the **envelope**, spectrum-analyse the envelope.
   A ~7 Hz line **in the envelope** = this mechanism; a ~7 Hz line only in the **raw** signal = the old
   resonance.
3. ⭐ **THE CLINCHER — `f_mod` is proportional to `f_carrier / Q`.** When the carrier moves (the kit's own
   record has it at **21.90 / 23.61 / 24.90 Hz at 1x / 4x / 6x** gain), the modulation rate must move
   **with it, proportionally**. **No firmware time constant can do that** — a cal-defined tau is fixed.
   This is a cross-build discriminator needing no new build.

**Grade:** the arithmetic and the firmware timescales are **EVIDENCE**; Q is the kit's own measured value;
**that this mechanism IS the operator's percept is BELIEF** until test 2 or 3 returns.

Related: [[reference_accord_gp6ac0_rectify_after_iir_and_governor_bound_census]] (the rectify-after-filter
peak-follower that drives the ceiling), [[accord-ratchet-is-a-lightly-damped-resonance]] (Q source),
[[accord-f0-crossover-is-the-endpoint]] (the carrier's gain-dependent frequency).
