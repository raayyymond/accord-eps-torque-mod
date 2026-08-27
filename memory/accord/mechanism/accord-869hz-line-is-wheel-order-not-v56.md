---
name: accord-869hz-line-is-wheel-order-not-v56
description: "The \"8.69 Hz line V56 introduced\" is wheel order 1 at V56's driving speed; it tracks speed on V57 too, so it was never a firmware artifact."
metadata: 
  node_type: memory
  type: reference
  originSessionId: a179e27a-7fe7-49ee-b2a8-e84c074404f9
  modified: 2026-07-30T02:32:16.271Z
---

Measured 2026-07-29 on route 28 (V57) and route 24 (V56) through one identical pipeline.

At 15-20 m/s, LKAS-active + hands-off, nfft=256, per-window: the 7-11 Hz peak sits at each window's
OWN predicted wheel-order frequency `0.489*v - 0.186`, on **both** builds.

- V56's 35 windows are almost all at v = 17.9-18.2 m/s, where fpred = 8.56-8.71 Hz. **That is why it
  looked like a fixed "8.69 Hz" line — 8.69 IS wheel order at the speed V56 happened to drive.**
- Its own edge windows move: v=15.15 -> peak 7.03 Hz (pred 7.22); v=19.80 -> 9.77 Hz (pred 9.50).
- V57 tracks identically: v=15.44 -> 7.03; v=18.55 -> 8.98; v=19.50 -> 9.38 Hz (prominence 69x).

⇒ The line is **absent from V57 at exactly 8.69 Hz** but **present as the same tyre line at V57's own
speeds**. Reporting it as "V56's mute introduced a resonance, and V57 removed it" would be wrong in
both halves. It is a road input, firmware-independent — consistent with [[accord-v57-confirms-wheel-order-tyre-line]].

**Why:** the kit nearly banked "the 8.69 line vanished" as proof the V56 mute was live on the car.
It proves nothing of the kind, and no liveness conclusion may rest on it.

**How to apply:** never quote a fixed frequency for this line. Quote `0.489*v` and the speed. Before
attributing any 5-12 Hz feature to firmware, compute wheel order 1 for that subset's speed first.
