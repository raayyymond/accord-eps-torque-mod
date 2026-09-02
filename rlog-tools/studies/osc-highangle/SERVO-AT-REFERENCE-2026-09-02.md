# Is the 7 Hz high-angle stutter the rate servo chattering AT its reference? — 2026-09-02, subagent r3servo

Script `servo_at_reference.py` (beside this note; full tables in `<scratch>/r3servo/servo_at_reference.txt`). Chain = `v280_map_profiles.py`'s
frame-by-frame FUN_00028ea6 mirror, run on the MEASURED 0x18F rate of the 13 `highangle_stutter.py` episodes on r31, rev 3 cells (map ×2,
fb clamp 15360, gain 5346, cap 3072 — read from the V278r3 image). **Open loop throughout:** the rate is what rev 3's closed loop produced.
E is signed in the setpoint's direction (E < 0 = feedback past the reference = lane braking). EVIDENCE unless marked BELIEF.

## Verdict (one line)
**Neither as posed: E is LARGE (+7–9k, P railed 56–67 % of ticks) and the wheel is STALLED at 30 % of its reference — but the 7 Hz rate ripple
(±25 deg/s = ±6000 in E) swings P from its rail to near zero every cycle. It is a partially-saturated lane pushing against a stiff load, not a servo
hunting at its crossover — and the ×6 top REMOVES the modulation (sim T ripple 744 → 235) rather than feeding it.**

## 1. The F7 episodes through the chain (rev 3 cells)
| # | fdom | rate p50 / ref (deg/s) | rate/ref | \|E\| p50 / p90 | brake | E flips/s | fb clamped | P railed | 7 Hz amp fb / E / P / T_sim / T_meas | \|T\| sim / meas p50 | T_meas flips/s | sim vs meas corr / slope / phase |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 7.44 | 13.9 / 44.5 | 0.32 | 6869 / 10972 | 0.18 | 17.4 | 0.01 | 0.59 | 5749 / 5860 / 8765 / 821 / 598 | 1656 / 870 | 11.6 | 0.88 / 0.50 / +14° |
| 5 | 7.14 | 13.2 / 39.0 | 0.37 | 8135 / 12982 | 0.14 | 14.3 | 0.00 | 0.61 | 6133 / 5981 / 6860 / 701 / 536 | 1746 / 953 | 1.4 | 0.83 / 0.52 / +20° |
| 6 | 7.05 | 15.2 / 44.5 | 0.38 | 8289 / 13240 | 0.16 | 15.4 | 0.00 | 0.60 | 6387 / 6474 / 7843 / 758 / 537 | 1783 / 924 | 4.4 | 0.86 / 0.53 / +18° |
| 7 | 7.03 | 12.7 / 44.5 | 0.30 | 9418 / 14973 | 0.15 | 16.1 | 0.00 | 0.67 | 6801 / 6870 / 7242 / 729 / 544 | 1806 / 997 | 5.1 | 0.85 / 0.54 / +15° |
| 8 | 7.42 | 20.2 / 44.5 | 0.49 | 7988 / 26339 | 0.12 | 12.0 | 0.13 | 0.61 | 4629 / 4548 / 5773 / 592 / 472 | 1857 / 1011 | 0.0 | 0.60 / 0.55 / +15° |
| 11 | 7.58 | 10.5 / 36.3 | 0.31 | 7217 / 10801 | 0.17 | 15.6 | 0.00 | 0.56 | 5661 / 5438 / 8603 / 782 / 539 | 1668 / 823 | 10.9 | 0.87 / 0.49 / +15° |
| 12 | 7.46 | 11.3 / 42.8 | 0.30 | 8858 / 12869 | 0.15 | 14.9 | 0.00 | 0.62 | 6361 / 6247 / 7559 / 775 / 544 | 1764 / 942 | 8.0 | 0.86 / 0.50 / +16° |
| 1 | 6.54 | 72.9 / 44.5 | 1.66 | 4352 / 4371 | 0.83 | 13.7 | 0.65 | 0.02 | 2446 / 2344 / 6543 / 640 / 557 | 1454 / 842 | 9.2 | 0.87 / 0.59 / +21° |
| 3 | 7.47 | 66.9 / 44.5 | 1.56 | 4352 / 5432 | 0.80 | 13.8 | 0.56 | 0.02 | 3426 / 3278 / 9046 / 841 / 618 | 1376 / 690 | 12.6 | 0.91 / 0.51 / +16° |
| 4 | 7.03 | 52.0 / 40.2 | 1.40 | 4702 / 8929 | 0.63 | 13.9 | 0.33 | 0.26 | 3840 / 3830 / 7008 / 671 / 517 | 1536 / 973 | 1.4 | 0.83 / 0.60 / +12° |

- **Seven of ten (#2,5,6,7,8,11,12) are a STALLED wheel under full demand:** rate p50 10–20 deg/s against a 36–45 deg/s reference, E +7–9k, P railed
  56–67 %, fb never clamped. E "flips" 12–17/s only because the ±6000 ripple dips through zero for ~15 % of each cycle — E is not small. T_meas keeps
  the command's sign 91–99 % of frames (p10 79–430): the lane pushes hard with ~100 % modulation; it does not alternate push/brake.
- **Three (#1,3,4) are the wheel ABOVE the reference** (52–73 deg/s, driver spinning into 118–196° at 4–5 m/s): fb clamp binds 33–65 % of ticks, E sits
  at 11008−15360 = −4352 (the flat \|E\| p50 = 4352 is the clamp), the lane BRAKES (T_meas sign = cmd only 8–31 %). Only these three touch "at/over reference".
- **The 7 Hz is already in fb, hence in E** (amp fb ≈ amp E: sp is flat at the rail), passes P amplified 1.1–1.6× by Kp (partly clipped), and the chain reproduces
  T_meas: corr 0.83–0.91, slope 0.50–0.60 (= r3rate's low-speed multiplier, not a phase error), sim leads measured by 12–21° at 7 Hz (my T_meas is np.interp'd;
  the stutter note's sample-hold adds ~25° → its +78–88° and my +104–111° are the same phase). **The ripple in T IS the PID acting on the rate ripple.**
- 🛑 **"Driver torque 1170–1370 raw, hand on" is a MISREAD of a ringing torque sensor.** In every F7 episode the SIGNED 0x18F torque has mean −11…−436 raw
  and a 6–8.5 Hz amplitude of 1470–1960 raw, coherence 1.00 with the rate, lagging it by 87–107° (torque ∝ −∫rate = column twist). The hand is light; the
  torsion bar is being wound and unwound at 7 Hz, and its peaks (2000–2300) graze the 2240 override cliff on 3–12 % of frames (idx dips inside the cycle).
  The stall is the road/lock load at 58–196° and 4–9 m/s, not the driver.

## 2. Counterfactuals on the same measured rate, pooled F7 ticks (22.4 s), open loop
| map / fb clamp | ref deg/s | rate/ref | \|E\| p50 / p90 | brake | E flips/s | fb clamped | P railed | 7 Hz amp E / P / T_sim | \|T_sim\| p50 | T_sim flips/s | T ripple/level |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rev 3 ×2 / 15360 | 44.4 | 0.55 | 6083 / 12530 | 0.31 | 14.9 | 0.15 | 0.48 | 5649 / 7401 / 744 | 1663 | 0.4 | 0.45 |
| (a) V276 ×6 / 46080 | 133.3 | 0.18 | 24727 / 34039 | 0.01 | 1.3 | 0.00 | **0.97** | 5852 / **602** / **235** | 2194 | 0.0 | **0.11** |
| (b) ×6 / clamp KEPT 15360 | 133.3 | 0.18 | 24727 / 34036 | 0.01 | 1.1 | 0.15 | 0.97 | 5386 / 578 / 232 | 2226 | 0.0 | 0.10 |
| (c) stock ×1 / 7680 | 22.2 | 1.09 | 2728 / 7668 | 0.47 | 12.8 | 0.40 | 0.18 | 4069 / 9939 / 893 | 949 | **13.8** | **0.94** |
| (d) V280 2@96→6 / 46080 | 129.7 | 0.27 | 17898 / 33179 | 0.08 | 5.1 | 0.00 | 0.83 | 5506 / 2791 / 371 | 2066 | 0.0 | 0.18 |
- **×6 pins P to its rail on 97 % of ticks.** The same ±6000 E ripple then rides on a +25k–34k bias: P's 7 Hz amplitude falls 7401 → 602 (12×), T_sim's
  744 → 235 (3.2×), and the ripple-to-level ratio 0.45 → 0.11. To desaturate P at ×6 the rate ripple would have to reach ±100 deg/s. The clamp (a vs b)
  is irrelevant here (\|fb\| > 15360 on 15 % of ticks, E ≥ 24k either way).
- **The stock map on these frames would REVERSE the lane at 7 Hz** (13.8 flips/s, ripple/level 0.94, brake 0.47) — the true servo-at-reference picture — and yet
  stock never stuttered, because its delivery caps at 417 (§3). The V280 candidate (d) is between: P railed 83 %, ripple/level 0.18 (the knee at 96 still
  leaves idx 237 on the ×6 slope: Y(237) ≈ 1020).
- ⚠ **Closed loop, BELIEF:** what the sim cannot show is the rate ripple itself. If the 7 Hz line is loop-generated (lineage: 100 % loop at 6–9 Hz, gain margin
  1.2–1.6), cutting the lane's small-signal 7 Hz gain 3× at this operating point takes it below unity and the limit cycle cannot start through P; the remaining
  7 Hz path is D (16·ΔE ≈ 0.70·A_E at 7 Hz, half-wave through the sum clamp once P rails ≈ 13 % of P's linear gain), which is map-independent and already present
  on rev 3. If instead the line is a plant mode rung by the steady push, ×6 pushes ~1.3× harder (2194 vs 1663 sim; ~1000–1100 measured after the ~0.5 low-speed
  factor) and the ring would persist at similar amplitude — the pre-registered read below separates the two.

## 3. Stock and V112 high-angle frames (|angle| ≥ 30°, engaged), each through its own cells
| route / build | frames | s | rate / ref | rate/ref | \|E\| p50 | brake | E flips/s | fb clamped | P railed | 7 Hz amp fb / T_sim | \|T_sim\| p50 (cap) | sat |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r97 stock | idx ≥ 200 | 20.0 | 18.6 / 22.3 | 0.84 | 8191 | 0.18 | **0.5** | 0.36 | **0.75** | 466 / 15 | 402 (512) | 0.30 |
| r22 V112 (×1 map, 6× torque) | idx ≥ 200 | 11.9 | 25.7 / 22.3 | **1.16** | **2106** | 0.57 | **18.5** | 0.32 | 0.03 | 628 / 119 | 650 (3072) | 0.01 |
| r31 rev 3 | idx ≥ 200 | 31.3 | 38.0 / 44.5 | 0.85 | 4352 | 0.37 | 14.6 | 0.17 | 0.32 | **2954** / 444 | 1422 (3072) | 0.02 |
| r31 rev 3, the 7 F7 stalls | — | 15.7 | 13 / 44 | 0.30 | 6900–9400 | 0.15 | 12–17 | 0.00 | 0.56–0.67 | 4600–6800 / 590–820 | 1650–1860 | 0.00 |
- **V112 IS the literal servo-at-reference regime** — wheel at 1.16× its 22.3 reference, \|E\| 2106, sign flipping 18.5/s, lane at 21 % of its cap — for 12 s at
  4.3 m/s, **and it does not chatter** (fb ripple 628 = 2.5 deg/s vs r31's 12 deg/s in the same frames). A small, sign-flipping E with the 6× delivery is not sufficient.
- **Stock has rev 3's STRUCTURE** (E +8k, P railed 75 %, wheel at 84 % of reference, E flips 0.5/s) **at one-sixth the torque** (417-count ceiling, 30 % saturated)
  and does not chatter either. Rev 3 is the first build to put the stalled, P-railed structure on the 5346/3072 delivery: 7 Hz fb ripple 2954 vs 466 / 628.
- ⚠ Not speed-matched beyond "all 4–11 m/s"; r22's set is 11.9 s. Why rev 3's stalled frames (13 deg/s) exist at all while its idx ≥ 200 average reaches 38 deg/s:
  they are the frames at or near lock (154–196°) or heavy tyre load (58–80° at 7–9 m/s) with the planner still railed — the load, not the hand, holds the wheel.

## 4. Implication for V280 and the pre-registered instrument
**Raising the map top (2@96→6, clamp 46080) predicts LESS 7 Hz chatter in high-angle full-demand turns, not more** — mechanism: deep P saturation removes the
lane's 7 Hz modulation (open-loop ratio 0.45 → 0.18; ×6 uniform 0.11) — **at the price of a steadier, ~1.3× harder push** against the load, and, on the
driver-spinning frames (#1,3,4), a lane that pushes WITH the driver at the rail instead of braking (E_brake 0.63–0.83 → 0.01). BELIEF for the closed loop; §2's
plant-mode alternative is the failure branch.
**Instrument, already on the wire (no new tap):** in engaged frames with \|0x14A\| ≥ 30° and idx ≥ 200, per ≥ 1 s run: (i) T_meas 6–8.5 Hz amplitude ÷ \|T_meas\| p50 —
rev 3 baseline **0.55–0.70 (amp 470–620 on level 820–1010)**, predicted V280 ≤ 0.25 with level ≥ 1000; (ii) 0x18F signed driver-torque 6–8.5 Hz amplitude — rev 3
baseline **1470–1960 raw**, corpus-normal < 300; (iii) F7 episode count per 100 s of high-angle engaged time — rev 3 **10 per 102 s**.
**Pre-registered FAIL:** ripple/level ≥ 0.45 or torque-ring ≥ 1200 raw while \|T\| sits at its low-speed rail ⇒ the mode is not P-modulation-fed (D or plant), the
map top is not the lever, and the softer choice is to reduce the ripple path (Kd, or the taper cliff that the ring's peaks graze) rather than to raise the top further.
