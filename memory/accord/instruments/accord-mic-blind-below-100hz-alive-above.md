---
name: accord-mic-blind-below-100hz-alive-above
description: "⭐⭐★★★★★ THE POSITIVE CONTROL, AND THE DISTINCTION IT LICENSES. Wheel rate separates the 21–28 Hz mode 11.6×; the ACOUSTIC channel separates it 0.4× with in-burst level FLAT at 380–510 across a ladder where wheel rate climbs 21×; envelopes uncorrelated. ⇒ the sub-100 Hz acoustic null is an INSTRUMENT FAILURE. But the mic is demonstrably ALIVE above 100 Hz (0.14–0.28 dB/km/h; blinker control z≈4) ⇒ the 100 Hz–8 kHz null IS a genuine negative. Two different claims."
metadata:
  node_type: memory
  type: reference
---

# The microphone is blind below ~100 Hz and alive above it — and that distinction is the point

**EVIDENCE**, 2026-08-21. This is the most reusable thing the acoustic workstream produced: it says
**when a mic null means something and when it means nothing.**

## LEG 1 — THE DETECTOR IS VALIDATED FIRST
Pre-declared Schmitt detector (THR_ON = p95 of stock's engaged <16 km/h envelope, THR_OFF = 0.70×,
MIN_BURST 0.25 s, MERGE_GAP 0.15 s, **true analytic envelope**) reproduces the known wheel-rate
result: **duty 0.072 stock vs 0.804 / 0.882 / 0.845 at 6×**, longest burst 2.42 s vs 6.6–16.0 s.

## LEG 2 — THE MIC CANNOT SEE THE MODE
| channel | STOCK | V102 | V103 | V104 | separation |
|---|---|---|---|---|---|
| wheel rate 21–28 Hz | 0.072 | 0.804 | 0.882 | 0.845 | **11.6×** |
| **acoustic 21–28 Hz** | 0.109 | 0.043 | 0.029 | 0.065 | **0.4×** |

**In-burst level: wheel rate 0.88 → 2.25 → 14.15/14.89/11.27 → 18.63 across 1×/4×/6×/8× (21×);
acoustic FLAT at 380–510 on every build.**
**LEG 3:** the two envelopes are uncorrelated — r(log) = −0.13…+0.05, every value inside its
phase-shuffled surrogate CI. *(Phase surrogates ARE the correct null for a coupling test — see
[[feedback-phase-surrogate-is-no-null-for-a-spectral-line]] for where they are NOT.)*

⇒ **The acoustic 21–28 Hz energy is REAL and non-zero; it simply does not CHANGE between stock and
6×.** Those are different claims and only the second decides whether the channel is an instrument.

## ⭐ AND THEN — PROVE THE MIC WORKS, or the null means nothing
A failure at 25 Hz says nothing about 1 kHz. Two controls with known ground truth:
- **SPEED: passes decisively.** Band power rises **0.14–0.28 dB per km/h** through 100–1600 Hz
  (14–28 dB of range). Tyre/wind noise is the loudest thing in a car; if these were flat the channel
  would be dead.
- **TURN SIGNAL: passes on `r97`**, the one route whose blinker arms are tightly speed-matched — a
  localised **1.2–2.2 Hz** envelope bump at **z ≈ 3.8–4.4** in 100–300, 300–800 and broadband.
  ⚠ Under-powered elsewhere (`r96`'s off-arm spans 4–109 km/h).
  ⚠ **The first version of this control was confounded**: an envelope PSD is RED, so a 0.9–2.2 Hz
  peak sits above a 3–8 Hz floor with or without the blinker. The fix is the **same-frequency ON/OFF
  ratio normalised by the broadband ratio**.

## 🛑 THE RULE THIS LICENSES
> **A mic null below ~100 Hz is an INSTRUMENT FAILURE. A mic null above ~100 Hz is a real negative.**

**And the physics agrees:** 21 Hz is a **16 m wavelength** and a steering rack is a hopeless radiator
there — the direct-radiation null is close to **predicted**, not evidence of absence. ⇒ any sub-100 Hz
mechanical mode must be hunted as **amplitude modulation of broadband audible noise**, never as a tone.
Refines [[accord-mic-negative-carries-almost-nothing]].
⭐ **NEXT CHANNEL: the symptom is likely TACTILE, not acoustic. The IMU (Nyquist ~50 Hz) covers
21–47 Hz entirely and measures what the operator's hands feel.** See
[[accord-26hz-mode-is-a-steering-rate-phenomenon]].
