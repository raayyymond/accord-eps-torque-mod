---
name: accord-r35-grind-incident-is-a-20hz-burst-at-a-loaded-turn-start-and-kp-flat-248-cut-the-creep-line-3x
description: 2026-09-03 (rlog-tools/studies/grind/GRIND-INCIDENT-r35-2026-09-03.md, grind35). The operator's "largely pronounced grinding incident" at 23:48:21 (r35 t 1016.7, seg 16) is a 0.9 s EXPONENTIAL BURST (+1.42/s, e-fold 0.70 s = 14 cycles) of the same 20.1 Hz rate-loop mode at the start of a left turn from a standstill: idx 10 -> 137 in 1.5 s, wheel 37-60 deg/s, 2.6-3.8 m/s, HANDS ON and tightening (390 -> 1200 raw), NO rail active (chain linear), bar 240 raw (env peak 500), rate 13.8 deg/s, tap ripple/level 0.37, with a 7.5 Hz stutter ripple (596 raw) underneath; collapses in 0.44 s as the hands tighten. The mirror reproduces it (corr 0.86; D 2/3, P 1/3); the command's 20 Hz echo is inert. Not a larger peak than r34's loudest attenuated second -- what differs is the operating point (fast loaded wheel at a turn start, hands on, the 7 Hz pair). The bit-4 sign transform is UNREADABLE in the core (T never changes sign; the bar carries a 7.5 Hz tone as large as the 20 Hz). ROUTE-WIDE: V281 (Kp flat 248) has the creep line 3.5x LESS OFTEN (17 % vs 59 % of engaged v<6 windows) and 2.5x SMALLER (bar 18-22 p50 27 vs 78 raw; creep 1-3 m/s 13 % vs 63 %) than V280 at matched idx, and the amp-vs-idx dependence is gone -- the closed-loop sensitivity peak shrinks with Kp (BELIEF), which the open-loop mirror's -6 % could not see.
metadata:
  type: reference
---

# The r35 grind incident is a 20 Hz burst at a loaded turn start; Kp flat 248 cut the creep line 3x -- 2026-09-03

Related: [[accord-the-creep-grind-is-the-lkas-rate-loop-crossover-resonance-d-dominated]], [[accord-r24-pumps-at-7hz-and-damps-at-20hz-the-same-cell-pulls-the-two-symptoms-opposite-ways]],
[[accord-v281r3-flew-the-7hz-cycle-is-gone-the-p-only-deadband-arrived-understeer-is-mostly-sr-12-5]].
