---
name: feedback-a-nonlinear-lever-must-be-priced-in-every-driving-stratum-not-only-where-the-symptom-lives
description: 2026-09-06. The V287 rev 1 D-clamp (2560) passed its design analysis on creep and bookmarked-episode windows and FAILED adversary B, which stratified the same mirror over hands-on bar>700, loaded ang>60 and fast wheel >25 deg/s (20-28 % of engaged time): there the clamp bound on the FEEDBACK derivative and became a 0.6x Kd cut that re-arms the 7.3 Hz ring. Rule: an amplitude-selective (clamp/deadband/relay) lever changes the loop wherever the signal is large, so its admissibility test (dominance by the intended operand AND p99 of the unintended operand below the threshold) must be run in EVERY stratum the car drives, and the prereg must carry a statistic in the stratum where the trade would show. Companion rules from the same pass: a FAIL threshold must sit outside the baseline's own CI and route spread (Q5 0.980 was inside [0.971,0.983]; Q6 x1.3 inside a x1.52 spread); a primary endpoint that accrues on ordinary driving beats one that needs the symptom to occur; and "a check that condemns the flown build is broken" caught a double-counted Kd scaling in the re-sizing.
metadata:
  type: feedback
---

# A nonlinear lever must be priced in every driving stratum -- 2026-09-06

**Why:** the design's own admissibility test was correct and was run only where grind #1 lives (hands-off creep, 4-7 % of engaged time). The adversarial pass exists to run it where the design did not look, and it returned the do-not-flash the doctrine says it must be able to return.

**How to apply:** for any clamp/deadband/relay/limiter build, reuse the stratification in `rlog-tools/studies/grind/adv_v287_b_units_strata.py` (creep, low-mid, suburban, highway, hands-on, hands-on hard, loaded high-angle, fast wheel) and report dominance %, p99 ratio and bind % per stratum per dose before naming a dose; then compute the ring/grind trade in the stratum where the lever is NOT selective. Related: [[feedback-a-check-that-condemns-the-flown-build-is-broken]], [[accord-grind1-cal-only-levers-on-v282-are-exhausted-the-lag-pole-is-a-waterbed-and-the-d-clamp-trades-the-ring]].
