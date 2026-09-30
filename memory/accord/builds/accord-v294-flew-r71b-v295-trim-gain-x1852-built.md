---
name: accord-v294-flew-r71b-v295-trim-gain-x1852-built
description: V294 FLEW 2026-09-29 (route 00000071--a7b8ba5d9d, trim live +0.210, no grinding/stutter; jerky medium-speed hard turns, loose at low speed, loose/understeer highway); V295 BUILT 2026-09-30 NOT FLOWN = V294 + ONE cal cell b 0xC63EA 567->1050 (trim x1.852), four adversaries pass with defects; the literal cmd-vs-alpha metric is fork-dominated; the plant is overdamped + friction; under-delivery is the fork's LAF
metadata:
  type: project
---

**V294 flew 2026-09-29** on route `75604b0a432fdc89_00000071--a7b8ba5d9d` (tag `r71b_v294`; the dongle counter 0x71 is
reused — key on the hash), fork `Dom 20d24ab79` + `toggle-config_V294_accel-trim_r1.json` (generic torque controller Kp 0.9 /
Ki 0.3 / LAF 14 / friction 0.011, every Accord torque-mode term off, VSR map 16.84). EVIDENCE from the wire: FF identity R²
0.987, the pre-registered trim read **+0.210 [+0.208, +0.212] T counts per deg/s² vs modelled +0.211**, inverted-operand
control 125.6 vs 7.5 counts rms, no EPS fault. Operator, verbatim: *"No grinding or stuttering!"* · *"Jerky on hard turns at
medium speed"* · *"Loose on straights and turns at low speed."* · *"Loose/understeer at highway turns."*

**What the drive taught (`analysis-2020accord/studies/v295/`):**
- The pre-registered outcome held: hard-turn 1.6–3 Hz wheel-rate ×0.56–0.91 vs V293 flights (still 2–3× V282); HF the quietest of
  the class (ring presence 0.5 %, F7 0, tap ripple ×0.04 of V282).
- **The outer loop under-delivers** — turn-hold act/plan 0.69 at 8–22 m/s (0.91 above 22), tracking gain 0.80–0.83, straight
  delivery 58 %, integrator share 25–41 %. The harness counterfactual puts ≤ 0.004 of it on the trim: **it is the fork's
  feedforward level (SteerLatAccel 14, measured through the old rate servo) — a fork tuning value, ~14 → 10.**
- **The plant is OVERDAMPED and friction-dominated**, not the prior's lightly damped 2 Hz mode: J ≈ 0.2 T/(deg/s²) (identified only
  at 0–5 m/s), b 5–26 T/(deg/s), k 7–80 T/deg, Coulomb 76 → 4 T with speed, ζ_open 1.3–4.0; nothing above ~8 Hz identifiable.
- **The literal goal metric (0xE4 vs d²θ/dt²) cannot score a firmware edit from ordinary driving**: above 1 Hz it is the fork's P
  term reacting to the wheel (α LEADS the command); below 1 Hz 55–95 % of the command holds angle against the spring, 0–3 %
  accelerates the wheel. The firmware-attributable read is the tap regression (c1/c2 or the trim-footprint |K|).
- The 0x18F rate is rack-side: κ = d(angle)/dt ÷ x/8 = 1.16 on centre, 0.965 beyond 80°, every build. **The Accord DBC's 0x18F
  rate factor (−0.1) is WRONG for this EPS — the wire says −0.125 (a 25 % trap).**

**V295 BUILT 2026-09-30, NOT FLOWN** = V294 + `0xC63EA` b 567 → 1050 (LE `37 02` → `1a 04`) + the `0xC6FFC` trailer; 6 diff bytes,
0 code bytes; surface/rail/slope/616 T cap byte-identical. K_α 0.210 → 0.388 T per deg/s² (per steering-wheel unit on centre
×0.86), damping 1.60 → 2.96 T per deg/s at 2 Hz, |P/x| 20 Hz 2.079 → 3.850 (V282 44.90). Image `5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed`,
rwd `f42a06bda5a737eb9f678d617603745ec21fb93c4bd229344f33259cfbeaae87`. Four adversaries on the built image PASS_WITH_DEFECTS:
restart pulse 288 T = the design's own 2×-V294 cap with ZERO margin at 1 tick, 308 at 2 (ruled as ≤ 2× V294 per lane, any bail
length; fault path only); 13–17 Hz sim torque ×1.59 crosses one lens's ×1.5 clause (HF guard re-decided as gain < ×3);
20 Hz anti-damping from ~4–6 ms delay at 3–6 % of V282's removal; outer PM at 5 m/s −7.7°; driver-override resistance ~2×
(p99 166 → 307 T, max 554 under the 616 cap); |trim| > 300 T dwell 0.04 → 1.36 s (< 5 m/s, hands-on).

**Why:** the design panel (four lenses, eight adversaries) found b the only PID value that moves the acceleration loop without
touching the map; **the ceiling is structural** — |L| peaks 0.34 → 0.63 (5–10 m/s) at 2–3 Hz; "tracking acceleration" needs
|L| ≫ 1 = a 13–20 Hz crossover, where V282 ground. Ki integrates the COMMAND with no leak (V283's class) and stays 0; Kd is a
command-rate feedforward; the pole move 1011 → 1017 was REFUTED on direction across J; the regressive Kp schedule reaches the
under-delivery but is the fork's LAF by another name (excluded by scope).

**How to apply:** predicted — jerky hard turns modestly better (BELIEF; the same lever V294 already applied at a comparable
predicted step), low-speed looseness unchanged-to-slightly-worse, highway understeer UNCHANGED. **Wire read:** march V294's
cells on the new drive's own 0xE4/0x18F; OLS `T_tap = c0 + c1·FF + c2·TRIM`; calibrate on r71b first (c2 0.96–1.02, c1 0.97–1.01,
residual ≤ 3.0 — a negated rate flips c2); gate windows on rms(TRIM_V294) ≥ 4 counts; **c2 > 1.45 pooled = live (predicted 1.837);
< 1.45 = not V295, stop; < 0 = inverted, revert**; FF identity gate 0.90 (expected 0.965); no secondary outcome is decidable
from one drive — the operator scores the feel. Related: [[accord-v294-acceleration-trim-on-the-v293-torque-map-built]],
[[accord-quasi-static-zeta-estimate-overstates-low-speed-damping-compute-exact-poles]],
[[feedback-validate-the-pre-registered-instrument-on-a-real-null-route-before-the-drive]].
