---
name: accord-26hz-mode-is-a-steering-rate-phenomenon
description: "⭐⭐★★★★★ THE 21–28 Hz mode is driven by STEERING RATE, not speed — ~90× stock at 15–40 °/s, 8–14× at 0–5 °/s, and it COLLAPSES TO STOCK above 100 °/s. It is CONTINUOUS at 6× (burst duty 0.93–0.95, bursts 7–14 s) and ABSENT on stock (0.056, longest 0.69 s), disjoint CIs. Wheel order EXCLUDED. It is 3–5× louder than every other band and NO build has ever moved it. 🛑 And DUTY SATURATES AT 4× — score LEVEL, not duty."
metadata:
  node_type: memory
  type: reference
---

# The 21–28 Hz mode: a steering-RATE phenomenon, and the loudest thing on the car

**Measured on route `a4` (V104) against `r97` (STOCK), `r96` (V102), `r9e` (V103), `r85` (V100 4×),
`r95` (V101 8×). Engaged, at the operator's own window `< 16 km/h`.** EVIDENCE throughout unless marked.

## 1. IT IS ESSENTIALLY BINARY BETWEEN STOCK AND 6×
Pre-declared Schmitt detector on a **true analytic (Hilbert) envelope** — `THR_ON` = p95 of stock's
engaged envelope, `THR_OFF` = 0.70×, `MIN_BURST` 0.25 s, `MERGE_GAP` 0.15 s:

| | burst duty [95 % CI] | in-burst A | longest burst |
|---|---|---|---|
| STOCK 1× | **0.056** [0.000, 0.149] | 1.23 | **0.69 s** |
| V102 6× | 0.945 [0.836, 1.000] | 9.43 | 7.43 s |
| V103 6× | 0.948 [0.892, 1.000] | 15.71 | 11.23 s |
| V104 6× | 0.933 [0.874, 0.970] | 4.32 | 13.91 s |

🛑 **Stock never sustains it for one second. At 6× it runs 93–95 % of the time in bursts up to 14 s.
Disjoint CIs.** ⇒ **CONTINUOUS at 6×, ABSENT on stock.**
**No V104-vs-V103 comparison resolves** — the three 6× builds are indistinguishable on duty and on
in-burst amplitude. **No lever on V104 touched it.**

## 2. ⭐⭐ IT IS DRIVEN BY STEERING RATE, NOT SPEED
Median 21–28 Hz level, engaged, < 16 km/h, rate corrected by `1/0.7996` to true deg/s:

| | 0–5 °/s | 5–15 | **15–40** | 40–100 | 100+ |
|---|---|---|---|---|---|
| STOCK 1× | 0.12 | 0.30 | **0.24** | 0.48 | 0.57 |
| V102 6× | 0.92 | 8.27 | **24.31** | 25.56 | 0.57 |
| V103 6× | 1.71 | 13.79 | **21.64** | 20.01 | 0.67 |
| V104 6× | 1.17 | 4.78 | **20.79** | 14.47 | 0.76 |

🛑 **~90× stock at 15–40 °/s · only 8–14× at 0–5 °/s · COLLAPSES TO STOCK above 100 °/s.**
⭐ **Independently corroborates the operator's own claim** — *"applying torque kills the buzz"*,
previously measured at **16.12× [5.29, 41.29]** — from a completely different direction.

**Operator-facing sentence (his to confirm or reject; NOT claimed to be "grinding" — his word, his call):**
> *"Below about 16 km/h, whenever you are steering at a moderate rate — roughly 15–40 °/s, not gentle
> and not a hard turn — there is a 21–28 Hz oscillation running almost continuously, about 90× stronger
> than stock, in bursts of about half a second separated by tenth-of-a-second gaps. It fades as you
> speed up and vanishes if you turn hard."*

## 3. 🛑 DUTY SATURATES AT 4× — A SCORING RULE, NOT A DETAIL
| build | gain | burst duty | **in-burst LEVEL** |
|---|---|---|---|
| STOCK | 1× | 0.072 | **0.883** |
| V100 | 4× | 0.824 | **2.250** |
| V102 | 6× | 0.804 | **14.151** |
| V103 | 6× | 0.882 | **14.885** |
| V104 | 6× | 0.845 | **11.274** |
| V101 | 8× | 0.894 | **18.625** |

**Duty saturates at 4× (0.82 → 0.89 to 8×); LEVEL climbs 21×.** ⇒ **above 4× the gain sets AMPLITUDE,
not INCIDENCE.** 🛑 **ANY BUILD SCORED ON DUTY ABOVE 4× IS SCORING A SATURATED VARIABLE. SCORE LEVEL.**

## 4. TWO REGIMES — and the operator described both precisely
| burst duty | < 16 km/h | 40–80 km/h | 80–95 km/h |
|---|---|---|---|
| STOCK | 0.056 | 0.045 | 0.054 |
| V102 6× | 0.945 | 0.361 | 0.459 |
| V104 6× | 0.933 | 0.528 | 0.736 |

⇒ **continuous at his grinding window; genuinely INTERMITTENT at highway (36–74 %).** His *"vibration
comes in and out while highway driving"* and his low-speed grinding are **two regimes we had been pooling.**
⊕ The on/off cycling at 6× is **~1–2 per second** (bursts ~0.4 s median, gaps ~0.1 s) — **not** the
6–12/s ratchet he counts. **Two distinct phenomena.**

## 5. WHEEL ORDER EXCLUDED
Per-window regression of the in-band peak on speed: **`f_peak = −0.027·v + 27.4`, R² = 0.039** on `a4`
(and `+0.055·v + 27.6`, R² = 0.037 on stock) against the **0.962 (order 2) / 1.442 (order 3)** slope a
tyre order requires. **The peak does not move with speed. It is a fixed mode.**

## 6. IT MOVES WITH GAIN ⇒ IT IS A CLOSED-LOOP RESONANCE
`f0` = **21.90 / 23.61 / 24.90 Hz at 1× / 4× / 6×**. **A driven response does not move its frequency
with loop gain; a closed-loop pole does.** ⇒ **self-excited — feedforward/command-path filtering cannot
starve it.** And it needs LKAS engaged (**9,200× less power with it off**).

## 7. 🛑 IT IS THE LOUDEST THING AND NOTHING HAS EVER TOUCHED IT
At 0–40 km/h the stock→6× step is **6–9 Hz 2.03× · 18–22 Hz 21.2× · 21–28 Hz 17.3×**; at **<10 km/h the
21–28 Hz contrast is 64×**. **It is 3–5× louder than every other band** and **V104/V103 = 0.68–0.79 with
the CI spanning 1 at every window** — no lever on that build moved it. **Every build since V62 targeted
6–9 Hz or 15–22 Hz instead.**

## Related
[[accord-notch-is-the-only-shape-that-survives-gate2]] — the lever aimed at it (V105) ·
[[accord-the-8x-gain-is-the-carrier]] · [[accord-vibration-requires-lkas-engaged]] ·
[[accord-ratchet-is-a-lightly-damped-resonance]] · [[accord-v104-flew-and-failed-verify-from-telemetry]]
