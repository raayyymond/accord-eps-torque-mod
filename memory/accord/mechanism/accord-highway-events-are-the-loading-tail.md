---
name: accord-highway-events-are-the-loading-tail
description: The highway "events" are the top tail of the already-measured smooth maneuver-loading effect, triggered by a ~1.5 s steering-rate transient — not a distinct threshold-like mode
metadata:
  type: reference
---

The operator described the highway symptom as **threshold-like** — it happens or it does not, and it
does not grow with how hard the maneuver is. **Tested; it is not.** What the bus calls an "event" at
highway is the upper tail of the smooth maneuver-loading effect already on record.

## No step function anywhere
P(a 2.56 s window lies inside an event) by decile of each conditioning variable, 40–49 Hz, n = 1820
engaged-highway windows:

```
rate_pk    0.7   0.9   1.1   1.9   1.7   6.4   6.9  10.5  22.1  61.2 %   rho +0.420
reqmax     0.5   3.3   3.8   7.7   6.0   8.8   9.9  14.8  26.8  39.0 %   rho +0.308
v         12.1  13.2  15.4  17.6  12.1   5.5  11.5  17.0  14.3   2.2 %   rho -0.056
eff        9.3  13.7  14.3   9.3  12.1   9.3   9.9   9.9   7.1  25.8 %   rho +0.045
```

`rate_pk` rises through **every** decile from the 5th up. **There is no value below which events never
occur and above which they do.** The smooth loading already recorded reproduces exactly: window
envelope vs `rate_pk` **ρ +0.654** (40–49), **+0.705** (6–9), **+0.721** (18–22) — inside the
established +0.64…+0.93. ⚠ Speed ρ is ≈0/negative: torsion-bar events are **not** more likely at high
speed.

⚠ A 2-component mixture formally prefers "bimodal" (ΔBIC 174 at 40–49 Hz) — **do not read that as
threshold-like.** The high component holds **42 % of windows** at only **2.4×** the low one. That is a
heavy body being fitted by two Gaussians, not a rare event class.

## What actually triggers one
3 s look-back, 18 events vs 17 matched non-event controls at the same speed, medians:

| lag s | −3.0 | −1.5 | −0.5 | **0.0** | +0.5 |
|---|---|---|---|---|---|
| \|rate\| deg/s ev / ctrl | 1.0 / 1.0 | 5.0 / 1.0 | 6.5 / 1.0 | **18.0** / 1.0 | 5.0 / 1.0 |
| speed m/s | 30.2 / 30.8 | — | — | 30.3 / 31.1 | — |

**A ~1.5 s steering-rate transient peaking near 18 deg/s**, at constant speed. Same mechanism as the
smooth loading, not a separate phenomenon.

## Event characterisation (22 distinct instants above 28 m/s)
- Duration **0.22–0.87 s**; **rail duty 0.00 on every single event** — no actuator saturation involved.
- ✅ **Hands-off confirmed**, matching the operator: effort `|lowpass(tq, 3 Hz)|` p50 **92 counts**
  (kit criterion ≤ 200), `steeringPressed` duty p50 **0.00**, **19/20 (95 %)** satisfy both.
- 🛑 **No closed-loop signature.** Command→bar coherence (`0x0E4` → `0x18F`) at 40–49 Hz is **0.169 in
  event windows vs 0.166 background**; 30–40 Hz 0.210 / 0.184. Grind #1's mechanism was **0.917 at
  21.09 Hz** — nothing here resembles it. ⚠ `e4tq` is held-last onto the `0x14A` grid, so the 40–49
  row is an upper bound.
- The two largest-amplitude events in the corpus are on route `3b` (**V65**), not on V67.

⇒ **A useful negative: the highway events are the loading tail, and the loading tail is not a firmware
target.** Reproduce with `analysis-2020accord/studies/highway/highway_event_hunt.py` (§5) and
`analysis-2020accord/studies/highway/highway_fast_lane.py` (§4, §6, §7). Related:
[[accord-highway-event-rate-null-with-power]], [[accord-highway-30-49hz-has-no-line]],
[[feedback-mean-and-tail-must-be-reported-together]], [[accord-v67-flew-both-grinds-fixed]].
