---
name: accord-v62-flashed-grinding-is-fixed
description: ★★★ V62 FLASHED 2026-07-31 (route 37) -- the 20.9 Hz grinding is FIXED, 8-42x, the kit's first measured fix. The reported "new grinding" is NOT an established regression.
metadata:
  type: project
---

# ★★★ V62 FLASHED → THE GRINDING IS FIXED. First measured fix in 60+ builds.

**Route `00000037--6231e33f3d`**, 15 segs, 86,278 frames, 862.65 s. V62 = `sar 0xa`→`sar 0x9` at
`0x3AC20` (r24) and `0x3AB76` (r26) in `FUN_0003aa2c`. Image/RWD SHAs verified from the artifacts and
the two edited bytes re-read from the image before any analysis.

## The result
Engaged creep, speed-standardised, **episode-clustered** bootstrap, order-track ceilings enforced:

| | V62 / V59 |
|---|---|
| 18–22 Hz, creep | **0.124 [0.036, 0.387]** — 8× |
| 18–22 Hz at \|rate\| 16–32 deg/s | **0.024 [0.016, 0.234]** — **42×** |
| 30–40 Hz negative control | **~1.0** ⇒ band-specific, not a route offset |

Transient distribution moved down too: `|d(tq)|` >200/>500/>1000 rate ratios **0.793 / 0.486 / 0.338** —
monotonically cleaner as the threshold rises. V62 has the **lowest p90, p99 and >1000/s of any build**.

★ V61 quantified on the same statistic: p50 roughness **730** vs V59's 101, >1000 excursions **376.7/s vs
24.3/s**. That is the operator's "significantly worse", at 15×.

## 🛑 The reported "new grinding" is NOT an established regression
Operator reported new grinding turning manually with LKAS engaged at ~10–20 mph, at **10:12:15** and
**10:23:24**. Wall clock measured (±0.05 s) ⇒ **seg 1 t=9.67 s** and **seg 12 t=18.63 s**. Both were
relocated **independently of the operator's memory** by scanning `|d(tq)|` with no gating.

**They are two different phenomena:**
- **Instant #2** (16.3 mph) — an ordinary roughness burst, never exceeded 2000. **V59 produces these
  ~3× MORE often** (1.042/s vs 0.354/s). This is the **unmasking**: ordinary transient load fell 2–3×,
  so what remains is salient.
- **Instant #1** (5.4 mph, **not** 10–20 mph) — a **0.92 s singleton**, unique in the dataset, max 3,694,
  carried by **38–46 Hz** (8,478× median, 100th pct) while 18–22 Hz sat at 1.4× median (52nd pct).

🛑🛑 **V62's 43 excursions >2000 are ONE burst. The correct n is 1.** By distinct bursts per engaged
second: V62 **0.00142 [0.00004, 0.00793]**, V59 **0 [0, 0.00986]**, V61 0.10204, V64 0.
⇒ **V62's CI is contained inside V59's**; V61's rate is **72×** V62's.
**Exposure-matched** (v 2–4 m/s ∧ |rate| ≥32 deg/s): V62 16.14 s, V59 15.75 s, one event ⇒ **p = 0.51**.
**A coin flip — no evidence of regression, and no evidence of absence.**

⚠ The one genuinely out-of-family number: 38–46 Hz **max** 6.30e5 vs V59's 1.43e3 (440×). But through
p90 they are indistinguishable (438 vs 329) — an ordinary distribution with one outlier.

⇒ **RECOMMENDED: no new build. Fly V62 again and count bursts.** The open question is the *rate of a rare
event*, which needs exposure, not firmware. Revisit the burst corner: **v 2–4 m/s at high steering rate
under LKAS.** See [[accord-r26-is-structurally-inert]], [[accord-ratchet-is-a-saturated-resonance]].

⚠ **Trigger sits outside the firmware:** instant #1 occurs with openpilot's command **railed at ±4096**
for 0.64 s with the driver turning against it. Engaged-creep rail duty **V62 42.4% vs V59 25.3%** — itself
a confound. 🛑 No openpilot-side modifications (standing instruction); recorded as observation only.

FLIGHT-CLEAN: `ST==4` **0/86,278** (ST==4 is the *fault* value — zero is clean; streak now >229,278),
ST==3 = 119 all at vEgo 0, six watched events 0 except `steerSaturated` ×2 (not at either instant).
