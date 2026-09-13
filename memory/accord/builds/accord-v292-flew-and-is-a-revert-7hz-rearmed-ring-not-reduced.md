---
name: accord-v292-flew-and-is-a-revert-7hz-rearmed-ring-not-reduced
description: "🛑🛑⭐⭐⭐⭐⭐ V292 FLEW 2026-09-13 (routes …0000006d / …6e / …6f, 54 segments, 1,723 s engaged-lateral, cave LIVE) and is a REVERT by its own pre-registration: the 6–9 Hz strong-turn ripple returned (F7 4.17/100 s vs V282 0.51, ripple/level 0.21–0.34 vs 0.10–0.17, 6–9 Hz rate ×1.6–2.2 with exposure AND excitation controls passing, P NOT railed ⇒ the 7 Hz mode re-armed by the fb pole's lag, not the V278r3 stall class), the 13–17 Hz shoulder fired (×1.8–2.1, a new 14.84 Hz line at +6.3 dB), and the 18–22 Hz ring was NOT reduced (route-normalised engaged ÷ same-route disengaged ×1.20–2.00; present-window ×1.07–1.38 vs a predicted ×0.71; f0 19.92 Hz unmoved) while the loop phase moved +15…+38° at 10 Hz, opposite in sign to the −14° prediction. The byte-exact replay's ×0.55 was FALSIFIED on the wire; the prereg's b3 DUTY read did NOT discriminate. Operator: grinding still present, stuttering worse. The fallback is V282."
metadata:
  node_type: memory
  type: project
---

**What flew.** V292 = V282 + V291's loop-opening dose (`0xC63E8/EA` 962/958 = fb lag pole 16.5 → 9.94 Hz
DC-held, `0xC6446` 4725, `0x14A` b3 = sign(fb state)) + the 52-byte error-feedback cave at `0xC4C00`
(hook `0x28F8E`). Routes `75604b0a432fdc89_0000006d--5e7b4d2ceb`, `…6e--64b4a5fef4`, `…6f--d876c761bc`.
🛑 **The dongle counter was RESET — these are NOT the August `r6d`/`r6e`/`r6f` of V84/V85**; caches carry
a `_v292` suffix. Read: `rlog-tools/studies/grind/V292-FLIGHT-READ-2026-09-13.md` (+ `v292_flight_*.py`,
`extract_v292_routes.py`); lineage verdict in `docs/BUILD-LINEAGE.md` under the V292 entry.

| read | V292 (r6d / r6e / r6f) | V282 (r6c / r39) | verdict |
|---|---|---|---|
| F7 per 100 s high-angle (revert ≥ 2) | 3.99 / 2.22 / 6.30 — pooled **4.17** [1.68, 8.59] | 1.03 / 0.00 (0.51); V281r3 r35 0.00 | 🛑 **FIRED** (×8.1, p = 0.022) |
| tap ripple/level (revert ≥ 0.25) | 0.214 / **0.327** / **0.339** | 0.104 / 0.166 (r35 0.161) | 🛑 FIRED on two |
| 6–9 Hz rate, high-angle hands-light | ×2.05 / ×1.62 / ×1.70 vs r6c | r39 ×1.19, r35 ×1.51 | EPS-internal — `0xE4` 6–9 Hz ≤ ×1.3 |
| 13–17 Hz shoulder | ×1.85 / ×1.91 / ×2.14; r6d line **14.84 Hz +6.3 dB** (r6c +2.8) | predicted ×1.33–1.70 | 🛑 **FIRED** |
| 18–22 Hz engaged ÷ same-route disengaged | 5.48 / 6.80 / 4.09 ⇒ **×1.61 / ×2.00 / ×1.20** | 3.40 / 3.92 (r39 ×1.15, r35 ×1.06) | **not reduced** |
| 18–22 Hz present-window amplitude vs r6c | ×1.38 / ×1.07 / ×1.25 | r39 ×1.05, r35 ×1.33 | predicted ×0.71 — **falsified** |
| half-peak decay (predicted 545 → 183 ms) | 273 / 315 / 130 ms | 190 / 187 | **confounded metric**, did not fall |
| T-vs-rate phase Δ at 10 Hz (predicted −14 ± 4°) | **+38.4 / +25.9 / +15.5** | — | moved, **opposite sign**; a closed-loop mixture |
| f0 of the object | 19.96 / 20.02 / 19.99 Hz | 20.06 / 20.07 | **did not move** (V289 had moved it to 15–17) |
| b5 / b6 (the r24 cut's control) | ×0.897/×0.823, ×0.933/×0.849, ×1.340/×1.250 | **r39 (V282) reads ×0.887/×0.870** | **uninformative at this dose** |
| 22–30 Hz line | peak excess +0.43…+2.37 dB | r39 +2.00, r35 +1.88 | ✅ none |

**Attribution [EVIDENCE].** The prereg's **b3 DUTY read does NOT discriminate** — V292 0.418/0.445/0.453
against V282's r6c **0.467**, overlapping, and the idle control reads backwards (0.035–0.049 vs r6c 0.000).
What discriminates is the bit's **meaning**: b3 tracks `sign(0x18F rate)` at lag **+1 frame**, split
0.642–0.764, peak corr +0.771…+0.818, against four reference builds (V282 ×2, V288r2, V289r1) flat within
±0.06 at every lag. ⇒ V292 on all three routes, cave LIVE. Cells re-verified byte by byte from the images;
the 427 tap is identical on both, so `T` is directly comparable.

**Mechanism [EVIDENCE for the numbers, BELIEF for the attribution].** P is **not railed on any of the seven
F7 episodes** (duty 0.00–0.20, five of seven ≤ 0.05) ⇒ **not** the V278r3 "P desaturating on a stalled
wheel" class. The seven sit at 7.03 / 7.14 / 6.64 / 7.47 / 7.03 / 7.04 / 7.03 Hz — the **7.3 Hz gate
`DESIGN-V291-FBLP` predicted every dose at a ≥ 927 would pay**; V292 carries a = 962. The frequency did not
move (f0 p50 7.00 Hz on the V292 routes **and** on r6c); the amplitude roughly doubled. ⇒ the linear 7 Hz
mode V281 rev 3 damped out was **re-armed by the fb pole's phase lag**.

**Controls.** Exposure (speed, |angle|, demand index, |bar| percentiles) matches across all six routes;
excitation — openpilot's own `0xE4` content in the same band and stratum is at most ×1.3 while the response
moved ×2, so **the extra ripple is not commanded**; route-normalisation cancels a quieter or rougher drive,
and r6e is the cleanest case (disengaged ×0.52–0.64 of r6c's in every band while engaged is up ×1.24–2.38 —
**quieter road, louder loop**); speed-matched re-weighting survives. ⚠ One confound stands: the driving
model changed `tsfdo` → `gyhu3`, which is why those controls exist. **RESOLVED, not a confound:** every
`Accord*` param was ABSENT from `initData.params` and each code default equals the 2026-09-10 backup value,
so the effective outer loop was unchanged; `AccordCurvatureLead` absent on both sides ⇒ default OFF.

**Why it matters.** V292's own pre-registered null sentence — *decay not below 1.23× V282's while the phase
HAS moved ⇒ the object's damping is not set by the rate loop's return ratio* — **has fired**. Either the
fit family mis-sizes what a feedback pole does at 20 Hz (the opposite-sign phase is the tell) or the
engaged-only de-damping is not the LKAS loop's return ratio at all. **V293 (torque mode, `fb ≡ 0` at every
frequency) is the model-independent test of that disjunction.**

**How to apply.** (1) **Score any future build's ring by the DRIVE-CONTROLLED measure** — engaged ÷ the
SAME route's lateral-disengaged 18–22 Hz amplitude, plus present-window amplitude vs r6c — **never by the
driven half-peak decay**, which this flight showed is confounded. (2) **Pre-register MARGINS, not points**:
the operator's revert threshold (0.25) and V292's own prediction (0.22) were 13 % apart. (3) **A duty read
is not an attribution** — design the identity read on the bit's *meaning*, with a lag profile and reference
builds, and check before the drive that the predicted duty does not overlap the reference's.

Related: [[accord-v292-built-loop-opening-dose-byte-exact-error-feedback-cave-cleared-over-one-dissent]],
[[accord-v293-torque-mode-built-the-model-independent-test]],
[[accord-with-the-loop-open-there-is-no-18-22hz-object-zeta-open-ge-0-05]],
[[accord-fb-pole-down-class-does-everything-but-fails-the-7hz-gate-r24-arm-is-the-blocker]],
[[accord-r24-lane-is-a-lag4-bar-difference-unit-weight-sibling-of-the-lkas-lane-damps-20hz-pumps-7hz]],
[[feedback-attribute-the-build-from-the-tap-not-from-the-label]].
