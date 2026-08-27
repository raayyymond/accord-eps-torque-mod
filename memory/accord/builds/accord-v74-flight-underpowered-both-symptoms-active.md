---
name: accord-v74-flight-underpowered-both-symptoms-active
description: V74's flight CLEARED the pre-registered abort gate (5xf0 prominence 2.227 vs 3.0) but the success test is UNDERPOWERED -- all three metrics favourable, none clearing its CI on 9 episodes. Both symptoms remain active at 3.27x (6-9 Hz) and 2.72x (18-22 Hz) over the 24-28 Hz control.
metadata:
  type: project
---

# ★★ V74's FLIGHT: gate CLEAR, result UNDERPOWERED, both symptoms still active

⚠ **Provenance:** the spectral scoring was done by sibling measurement agents this session and relayed by
the orchestrator. **I measured the exposure and the probe** ([[accord-v74-flew-damper-is-in-force]]); I
did **not** reproduce the band ratios. Treat the numbers as the session's finding, not as independently
replicated.

## The pre-registered gate — ✅ CLEAR, so the lever is not generating a new cycle
`5 × f0` prominence **2.227** against the abort threshold **3.0** (baseline 0.80).
⇒ **the relay-chatter failure mode did not occur.** This was the specific risk of opening a rate dead
zone, and it is retired for this dose. ✅ `Y[0] = 0` was preserved, which is why.

## The success test — ❌ UNDERPOWERED, and it must not be read as a null
| metric | ratio | 95 % CI | reads |
|---|---|---|---|
| 6-9 Hz duty | **0.797** | [0.544, 1.045] | favourable, CI contains 1 |
| duration | **0.934** | — | favourable, CI contains 1 |
| envelope p99 | **0.835** | — | favourable, CI contains 1 |

**All three point the right way; none clears its confidence interval.** MDE ≈ **2.0–2.9×** on **9
episodes** — the route simply did not carry the power. See [[feedback-episodes-not-windows-and-the-noise-floor]]: 9 is the
sample size, not 56,753 frames.
🛑 **This is an UNDERPOWERED FAVOURABLE, not a falsification.** Do not file V74's lever as null; the
distinction is exactly what [[accord-0x454fe-test-was-vacuous-state4-never-occurs]] and
[[accord-state671a-is-an-oscillation-detector]] exist to protect.

## Both symptoms remain active
Over the 24-28 Hz control band: **6-9 Hz at 3.27×** and **18-22 Hz at 2.72×**.
⇒ the damper is now demonstrably in force ([[accord-v74-flew-damper-is-in-force]]) **and the symptoms
persist at this dose** — which is a genuinely new position. Every previous damper null was
uninterpretable because the lever was never delivered; this one is interpretable and says *the dose is
too small, or the damper is the wrong lever*.

## Why the route was thin — and what the next flight needs
Route `5d` gave **9 engagement episodes / 563.1 s engaged, but only 78.0 s of engaged creep**, against a
flight instruction that asked for congestion yielding ~40 events. The high-speed leg is well covered
(100.7 s ≥ 20 m/s); the **creep/ratchet arm is the underpowered one**.
⇒ **The next flight's binding requirement is engaged-creep episode COUNT, not duration.** Stop-and-go
traffic, not a long cruise.

## What follows for V75
The dose ladder is priced in [[reference-accord-factore-x1-is-the-free-dose-lever]]: `FactorE Y` has only
**1.318×** of verified headroom before the 512 ceiling clips, but **`FactorE X[1]` 400 → 200 gives 2.08×
at the symptom's operating point with the surface maximum unchanged.** ⚠ Its cost is ramp **phase**
(GATE 2), which no log can settle.

Related: [[accord-v74-flew-damper-is-in-force]] · [[reference-accord-factore-x1-is-the-free-dose-lever]] ·
[[reference-accord-two-dead-zones-speed-and-rate]] · [[feedback-episodes-not-windows-and-the-noise-floor]] ·
[[reference-accord-78hz-mode-characterisation]]
