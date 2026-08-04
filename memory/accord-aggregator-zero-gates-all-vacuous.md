---
name: accord-aggregator-zero-gates-all-vacuous
description: "🛑 2026-08-04 [EVIDENCE, every ceiling byte-read]: ALL EIGHT of the aggregator's zero-type range gates are structurally vacuous — each producer's ceiling sits at or inside its own gate window, on every drive and every build. The aggregator stage contains no reachable hard nonlinearity; the relay/limit-cycle framing for it is REFUTED."
metadata:
  type: reference
---

# 🛑 THE AGGREGATOR IS ELIMINATED — all eight zero-type range gates are VACUOUS

**[EVIDENCE — every ceiling byte-read.]** Each gate is capped by its **own producer's** ceiling at or
inside its gate window, **on every drive, every build**:

| lane | producer ceiling | gate window |
|---|---|---|
| boost | 512 | 2048 |
| damping | **exactly 0 at creep** (FactorC `0xD27BC` Y[0] = 0, multiplicative; ≈35 km/h onset); ≤1024 at highway | 2048 |
| friction | 511 | 1024 |
| magnitude | ±0x3000 | **== window, exactly, inclusive** |
| LKAS | ±0x2800 | **== window, exactly** |
| `gp-0x6ade` | **0 writers** | — |
| resonance | max 1024 (**164–341** at the ratchet's speeds) | 2800 |
| return-centre `gp-0x6b62` | max 5786 | 8192 |

⇒ **the aggregator stage contains NO reachable hard nonlinearity**, joining the aggregator **SUM**
(V65, 120,049 frames — [[accord-aggregator-never-rails-loop-is-linear]]).
🛑 **The relay / limit-cycle framing for the aggregator is REFUTED. Do not re-propose it.**

★ Also [EVIDENCE]: **`FUN_00036388`'s own counters give ~20–40 ms or ~1 s periods** — nowhere near
7.8 Hz ⇒ **it INHERITS the ratchet, it does not GENERATE it.**

⊕ **Note the overlap with GATE 3:** the resonance row (164–341 reachable vs a 2800 window) is the same
arithmetic that made V69's bit4 structurally vacuous —
[[feedback-size-probe-rungs-against-lane-reachable-output]]. **A gate's width says what the CONSUMER
accepts; it says nothing about what the PRODUCER can emit**, and eight lanes in a row confirm it.

★ **The damping row is the one with a lever attached:** base-assist damping is **exactly zero below
~35 km/h** while the ratchet lives at **4.9–8.0 km/h with Q ≈ 40** —
[[accord-ratchet-q-measured-40]].

See [[reference_accord_demand_aggregator_pipeline]], [[accord-r24-r26-two-selectors-one-gate]].
