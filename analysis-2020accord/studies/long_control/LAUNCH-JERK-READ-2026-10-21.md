# Launch jerk read, routes b5–b9 (2026-10-21, accord-PTM 311c4cc0, Honda Bosch long)

Script: `long_launch_jerk_read.py` (all 131 segments b0–b9 extracted once, re-runs in ~3 s). Per-route JSON + `population.json` in `_scratch/out/long_launch_jerk/`.
Figure: `analysis-2020accord/figures/long_launch_jerk_000000b9--d974cafee9_bookmark_360.png`.

## Bookmark (the operator's one bookmark on b5–b9)
- **b9 `000000b9--d974cafee9`, segment 6 + 30.1 s (route t = 390.0 s)**: both `bookmarkButton` and `userBookmark`, same instant. No bookmarks on b5, b6, b8. (b0 has one at seg 5 + 7.8 s, long NOT engaged — out of scope.) EVIDENCE: Event union scan.
- The jerk is the **launch 13.2 s before the press** (onset route t = 376.8 s, 0 → 18.9 m/s, lead present, chill mode). EVIDENCE: figure.

| bookmark launch (t from onset) | value |
|---|---|
| aTarget | 0.93 → 2.07 (step at +2.3 s), then a smooth ramp down; peak→trough change per cycle −0.05 / −0.09 / −0.32 m/s² |
| aEgo overshoot / undershoot vs aTarget | +0.78 / −0.95, +1.26 / −1.60, +1.61 / −1.25 m/s² (3 gas-cut cycles, peaks at +5.3, +7.2, +9.3 s, ~2.0 s apart) |
| aEgo peak→trough drop | 1.78, 2.96, 3.19 m/s² in 0.3–0.8 s |
| GAS_COMMAND | on the 1600 rail 22 % of the launch; cuts 1600→1034, →393, →333 counts |
| gas-factor (replayed) | 0.24 at launch (persisted value) → 1.75 by +3 s (wind-up, turbo lag + gas rail) → 0.10 FLOOR at +7.2 s → 1.6 → 0.14; max slew 2.8 /s |
| aEgo lag behind gas | 320 ms (xcorr r 0.70) |
| rpm at each overshoot peak / upshift | 2443 (2→3), 2519 (3→4), 2424 (4→5); every cut is inside ±0.3 s of an upshift |

## Mechanism (decomposition)
1. **aTarget is smooth; it does not reverse.** Over all 28 gas-cut cycles the planner moves a median 0.16 m/s² peak→trough while aEgo drops 1.37 m/s². EVIDENCE (logged `longitudinalPlan.aTarget`). The planner/MPC is not the source.
2. **Every gas swing is the learner's factor swing.** `gas = interp(force × factor)` and force ≈ aTarget is smooth, so the factor carries a median **89 %** of each gas drop (log split; p10 18 %). EVIDENCE: code (carcontroller.py 311c4cc0, non-MVL Bosch branch) + offline replay of the learner, which reproduces the logged GAS_COMMAND to p50 6–28 / p90 9–76 counts per launch (of 1600).
3. **The plant starts each cycle; the learner turns it into an oscillation.** Sequence, every full launch:
   (a) turbo lag in 1st/2nd → aEgo < aTarget → factor integrates up at `err × force` per second (0.24 → 1.75 in 3 s in the bookmark) and the gas pins at the 1600 rail, where the learner keeps integrating (no anti-wind-up except a force ≥ 2.0 cap) — EVIDENCE (code + replay);
   (b) boost arrives (rpm 1630–2520, median 1970 at the overshoot peak) with a wound-up factor → aEgo overshoots +0.57 median (to +1.6);
   (c) the gas cut starts at the overshoot peak (onset − peak median −0.14 s) and the factor falls up to 2.8 /s, the gas drops a median 372 counts (to ~330 in the bookmark);
   (d) aEgo follows the gas 250–370 ms later and, with the upshift's own torque dip, undershoots −0.56 median (to −1.6);
   (e) error flips, factor climbs, gas returns to the rail → next overshoot one gear later.
   Period ≈ 2.0 s (median of 16 intervals, 1.4–3.6 s) = the 2→3→4→5 shift interval: the cycle is **phase-locked to the upshifts** (23 of 28 cycles contain an upshift within ±0.3 s). EVIDENCE for timing; BELIEF that the cadence locks *because* the shift schedule sets it.
4. Upshift vs gas-cut order is **not consistent** (upshift − cut onset median +0.56 s, p10 −0.44, p90 +1.03). I cannot say whether the gas lift triggers the shift (lift-to-shift) or the shift dip triggers the cut. UNRESOLVED — would need the TCU shift-activity byte decoded (`0x1A3` byte 0 is extracted, not interpreted).
5. **The operator's reading — turbo lag + gear-dependent torque — is right about the trigger**, and the learner is what makes it a sustained over/under cycle rather than one lag. BELIEF (no counterfactual run with a frozen factor exists in the logs).

## Population (launch = longActive, v < 3 m/s, aTarget crosses 0.5; window −2…+25 s)
Classes: `gas_cut` = gas on, no brake, not the 1st-gear brake-release lurch; `gas_brake` = cycle includes BRAKE_REQUEST (stop-and-go, planner-driven); `lurch` = 1st gear, rpm < 1000, the release kick at ~+1 s (+1.1–1.2 m/s² for 0.3 s, every full launch).

| route | launch t (s) | full | aTarget max | gas_cut / brake / lurch cycles | factor min–max | rail frac | replay err p50/p90 | aEgo lag (ms, r) |
|---|---|---|---|---|---|---|---|---|
| b9 | 376.8 (bookmark) | Y | 2.07 | 3 / 0 / 1 | 0.10–1.75 | 0.22 | 28 / 76 | 320, 0.70 |
| b8 | 450.1 | Y | 1.89 | 6 / 0 / 1 | 0.40–1.46 | 0.12 | 18 / 29 | 330, 0.59 |
| b8 | 509.7 | Y | 1.77 | 2 / 1 / 1 | 0.42–1.44 | 0.03 | 11 / 15 | 330, 0.60 |
| b8 | 612.4 | Y | 1.77 | 2 / 1 / 1 | 0.36–1.36 | 0.01 | 13 / 16 | 250, 0.46 |
| b6 | 886.3 | Y | 1.62 | 2 / 0 / 0 | 0.47–1.40 | 0 | 12 / 21 | 270, 0.69 |
| b6 | 962.5 | Y | 1.60 | 1 / 2 / 0 | 0.51–1.64 | 0 | 6 / 10 | 240, 0.57 |
| b6 | 1009.8 | Y | 1.72 | 3 / 2 / 1 | 0.53–1.60 | 0.10 | 6 / 14 | 250, 0.46 |
| b6 | 1058.5 | Y | 2.24 | 3 / 1 / 1 | 0.39–2.40 | 0.14 | 14 / 21 | 320, 0.49 |
| b6 | 1148.8 | Y | 2.22 | 4 / 0 / 1 | 0.42–2.26 | 0.15 | 8 / 20 | 110, 0.43 |
| b5 | 157.7 | Y | 2.12 | 1 / 0 / 0 | 0.43–2.53 | 0.57 | 0 / 12 | 370, 0.64 |
| b6 | 7 creep launches (453–697) | N | 0.66–1.12 | 0–1 / 0–2 / 0–1 | swing 0.35–0.88 | 0 | ≤ 6 / 12 | — |

- **10 of 10 full launches** show ≥ 1 gas-cut overshoot→undershoot cycle (> 0.4 m/s² each way within 3 s); 1 of 7 creep launches. b0–b4 have no launch episodes.
- The pattern scales with the **requested launch accel**: corr(cycles, aTarget max) **+0.75**, with factor swing +0.51, with rail fraction +0.29 (n = 17). The gentlest long pull, b6 522.8 (1.3 → 16.9 m/s, aTarget max 1.12, never on the rail), had **zero** cycles.
- Overshoots sit in gears 2–4 (21 of 28), rpm 1630–2520.

## Caveats
- Factor = offline replay seeded from the inverse lookup at the first clean frame after onset; `wind_factor` assumed 1.0 (wind term < 0.05 m/s² below 13 m/s). The 0.10 floor hit in the bookmark is replay-only (the inverse at that instant reads 0.18). BELIEF for the exact factor value, EVIDENCE for its direction and timing (replay matches the wire).
- `TRANS_TARGET_GEAR` (0x1A3 byte 1 low nibble, `_gearbox_common.dbc`) is the target, not the engaged gear; shift-completion timing is not known.
- Analysis only; no fix designed.

## PROPOSED REPLAY (`--proposed`; 10 full launches, the bookmark launch is b9 376.8)
Variants: **A** = 311c4cc0 learner (learn speed 50). **B** = learn speed 2000 plus no learning while force × factor ≥ 2.0 (gas lookup saturated). A and B are both seeded with the median inverse-lookup factor from clean pid frames before the launch. The window is 30 s, widened to 60, 120 or 300 s until at least 25 frames exist; six launches needed it widened because the car was braking to the stop. **B_logged** uses the logged start value as the seed. **OPEN LOOP**: the logged aEgo drives every variant, so this is the factor's own behaviour on the same car response. The car's response under B is not simulated.

| launch | seed: cruise (window s) / logged | A swing, max slew/s | B swing, slew/s, cut removed | B_logged swing, cut removed, freeze frames |
|---|---|---|---|---|
| b9 376.8 | 0.63 (120) / 0.23 | 1.96, 2.77 | 0.05, 0.07, 90 % | 0.05, 95 %, 0 |
| b8 450.1 | 0.61 (120) / 0.40 | 1.08, 1.48 | 0.03, 0.04, 77 % | 0.03, 84 %, 0 |
| b8 509.7 | 0.68 (60) / 0.42 | 1.05, 1.11 | 0.03, 0.03, 88 % | 0.03, 93 %, 0 |
| b8 612.4 | 0.48 (60) / 0.57 | 1.01, 1.15 | 0.03, 0.03, 94 % | 0.03, 93 %, 0 |
| b6 886.3 | 0.81 (300) / 0.73 | 0.93, 1.15 | 0.02, 0.03, 100 % | 0.02, 100 %, 0 |
| b6 962.5 | 0.57 (60) / 0.85 | 1.20, 1.97 | 0.03, 0.05, 94 % | 0.03, 92 %, 0 |
| b6 1009.8 | 0.83 (60) / 0.53 | 1.11, 0.88 | 0.03, 0.02, 74 % | 0.03, 83 %, 0 |
| b6 1058.5 | 0.79 (60) / 0.62 | 2.02, 1.85 | 0.05, 0.05, 69 % | 0.05, 75 %, 0 |
| b6 1148.8 | 0.71 (120) / 0.42 | 1.86, 1.74 | 0.05, 0.04, 87 % | 0.05, 90 %, 0 |
| b5 157.7 | 0.73 (30) / 1.14 | 2.10, 3.57 | 0.05, 0.09, 85 % | 0.03, 100 %, 238 |

"Cut removed" is the share of the logged peak-to-gas-minimum drop, summed over the launch's gas-cut cycles, that the variant's own gas would not make. The variant's gas uses the logged force and that variant's factor.

- **B removes the mechanism in replay: the factor swing is below 0.1 in 10 of 10 launches** (median 0.029, max 0.053; A median 1.15, max 2.10). The max slew falls from a median 1.61 per second to 0.04 per second. A median **88 %** of the logged gas-cut depth disappears (min 69 %). The rest is force, which means the planner's target. EVIDENCE for the replay arithmetic; the closed-loop outcome is BELIEF.
- **The rail freeze is inert inside B.** At speed 2000 the factor never climbs high enough to saturate the lookup, so the freeze fires on 0 frames with the cruise seed. It fires on 238 frames only in B_logged on b5, whose logged seed was 1.14. Speed alone gives results identical to B. Freeze alone at speed 50 leaves a 0.93 median swing (0 of 10 launches below 0.1) and fires on 2336 frames. **All the effect comes from the speed change.** The freeze is a guard for a high seed.
- **Cost of B (BELIEF, open loop):** B's gas over the first 4 s is a median **72 %** of the logged gas (684 against 962 counts). Over 4 to 12 s it is 85 %. With the logged seed the figures are 59 % and 74 %. Bosch long has kp = ki = 0, so nothing else closes the acceleration loop inside a launch. Expect a softer launch through turbo lag, where aEgo is already 0.33 below aTarget on average over 0 to 4 s, and the jerk should be gone. The persisted factor sets the launch strength, and the logged start values ranged from 0.23 to 1.14.

## PRE-REGISTERED READOUT for the first drive on B
Run `long_launch_jerk_read.py <routes>` twice: once at the default settings and once with `--learn-speed=2000 --rail-freeze`. Score only full launches (from below 1 m/s to above 10 m/s).

| readout | baseline (b5–b9, 10 launches) | B is live and works if |
|---|---|---|
| deployment check: replay vs wire, p90 gas error per launch, `--learn-speed=2000` | 338–1083 counts (wrong learner) | ≤ 80 counts, while the default (speed 50) replay p90 rises above 300 |
| inverse-lookup factor p10–p90 swing per launch (`inv_fac_p10_p90`, learner-agnostic) | median 0.55 (0.42–1.86) | median < 0.15 |
| gas-cut cycles per full launch (`n_cycles`, class gas_cut) | 27 in 10 (median 2.5; 10 of 10 have ≥ 1) | median ≤ 1, and ≤ half of launches have any |
| factor share of the gas drop in the remaining cycles | median 0.89 | median < 0.3 |
| launch shortfall, mean aEgo − aTarget over 0–4 s (`err_mean_0_4s`) | median −0.33 m/s² | expected to become MORE negative. This is the price, not a fail. Score it for the operator. |

**Null sentence, fixed now:** *If the deployment check passes and the factor swing is below 0.15, but full launches still show a median of 2 or more gas-cut overshoot–undershoot cycles, then the learner was not the cause. The cycle belongs to the plant (turbo spool plus shift torque) or to the planner. The next instrument is the 0x1A3 shift-activity byte and the planner's aTarget, not the learner.* If the deployment check fails, the drive says nothing about B.
