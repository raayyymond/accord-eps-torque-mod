---
name: accord-acoustic-level-not-comparable-across-drives
description: "🛑🛑★★★★★ ABSOLUTE ACOUSTIC LEVEL IS NOT COMPARABLE BETWEEN DRIVES. Parked, engine on, LKAS off, v<1 km/h, the cabin sounds 3–12× different between routes — no tyres, no wind, no steering, no firmware. Difference-in-differences confirms it: corr(log E, log M) = +0.836…+0.919. ⇒ the between-route acoustic comparison is STRUCTURALLY UNAVAILABLE, not merely null. Only WITHIN-route contrasts travel."
metadata:
  node_type: memory
  type: reference
---

# The cabin microphone carries a 3–12× per-drive offset

**EVIDENCE**, 2026-08-21, six routes (`r97` stock 1× · `r85` 4× · `r96`/`r9e`/`ra4` 6× · `r95` 8×).

## THE CONTROL THAT SETTLES IT — parked, engine on, LKAS off, v < 1 km/h
No tyres, no wind, no steering, no firmware. Amplitude relative to STOCK's own parked level:

| route | build | parked s | 100 | 400 | 1600 | 6300 Hz | broadband |
|---|---|---|---|---|---|---|---|
| r97 | STOCK 1× | 319.0 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| r85 | V100 4× | 18.6 | 1.47 | 1.80 | 1.15 | **0.08** | 1.19 |
| r96 | V102 6× | 237.1 | 0.64 | 0.89 | 0.97 | **0.11** | 0.92 |
| r9e | V103 6× | 96.3 | 0.36 | 0.25 | 0.34 | **0.09** | 0.61 |
| ra4 | V104 6× | 200.9 | 0.69 | 0.47 | 0.88 | **0.10** | 0.98 |
| r95 | V101 8× | 56.5 | 0.34 | 0.37 | 0.43 | 0.22 | 0.78 |

**A stationary car with the engine idling sounds 3–12× different between drives.** Windows, HVAC fan,
radio, phone position in the mount, ambient. **It is larger than any effect we hunt.**

## THE INDEPENDENT CONFIRMATION — difference-in-differences
E = engaged(X)/engaged(STOCK), M = manual(X)/manual(STOCK), both speed-matched <16 km/h. The mic does
not know what the firmware is doing, so E ≈ M ⇒ the contrast is the drive:
**corr(log E, log M) = +0.836 (r85) · +0.914 (r9e) · +0.919 (r95)**, slopes 0.73–0.89, geo-mean E/M
1.06–1.38.
⭐ **The single cleanest illustration: V102 reads 7.7× stock at 1.6 kHz while V103 reads 0.29× in the
same band. Both are 6× builds. A 26× spread between two builds that share the gain cell is not the
gain cell.** (A retired agent measured 10.46 / 0.29 / 0.73 — same disagreement, different estimator.)

## TWO TRAPS THAT MAKE IT WORSE
- ⚠ **The manual arm below 16 km/h is 73–83 % PARKED on EVERY route**, not just `ra4` — r97 83.4 %,
  r96 82.2 %, r9e 72.8 %, ra4 79.2 %. A parked car has no tyre noise, no suspension excitation and a
  different engine load; it is **not exchangeable** with rolling engaged driving, and the speed slope
  is enough to fake the entire effect. **Use rolling manual, v ≥ 2 km/h (36–64 s per route).**
  ⊕ The parked *fraction* is near-equal across builds, so the **between-build** comparison survives
  while the **absolute** ratio does not.
- ⚠ **One loud transient destroys a mean.** `r96`'s engaged 1.6 kHz band has **97.8 % of its power in
  the top 1 % of frames** (mean/median = **945**). Its E/M falls **2.37 → 0.83** under a median
  estimator. Always check the top-1 % share before quoting an acoustic mean.

## THE FIX, IF THE ACOUSTIC LINE IS EVER REOPENED
**A per-drive reference clip: parked, engine on, HVAC off, windows up, 30 s at the start of every
drive.** Without it no acoustic level ever crosses drives.
🛑 **And STOCK IS ONE ROUTE** — every acoustic stock-vs-6× comparison is one drive against N, on
different days and roads. Not fixable by analysis. **A second stock drive is worth more than another
6× build.** See [[accord-mic-blind-below-100hz-alive-above]].
