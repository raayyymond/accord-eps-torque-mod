---
name: accord-the-creep-grind-is-the-lkas-rate-loop-crossover-resonance-d-dominated
description: 2026-09-03 (rlog-tools/studies/grind/CREEP-20HZ-LOOP-ID-2026-09-03.md, creep20). The operator's "grind" at 3-6 mph hands-OFF is a 20.3-21.0 Hz line pinned in frequency (does not track wheel rate 18x, speed, angle or torque; cogging excluded), present only when engaged, whose PRESENCE follows loop gain (13 % of windows at idx 0, 42 % at idx 1-20, 83 % at 20-60) and not torque. The LKAS rate PID's inner loop on the tap-identified creep plant crosses unity at 17-21 Hz with PM 35-60 deg and Ms 2-2.9 at 19-23 Hz (Ms 4.3-4.6 at Kp 470); the chain mirror reproduces the tap's 20 Hz content (corr 0.82-0.88, coh 0.99) with D carrying ~55 %, P ~45 %. No rail active, amplitude bounded -> a lightly damped mode rung by broadband input, not a limit cycle. The whole record agrees: the band scales with the x6 forward gain (V38 origin, 1x/4x/6x/8x monotone), was only ever reduced by 1 kHz motor-side rate/acceleration feedback, never by a filter/notch. Less D moves the resonance to ~8 Hz with a bigger peak (the strong-turn regime); Kp cap 341 changes it -6 %; lag pole 2.5 Hz halves it open-loop. CAN receive times are batch-jittered up to 10 ms: take 20 Hz cross-spectra on the nominal frame counter. The fix is a loop-shaping design with a 7-9 Hz trade-off (handed to a deep-analysis agent 2026-09-03).
metadata:
  type: reference
---

# The creep grind is the LKAS rate loop's crossover resonance, D-dominated -- 2026-09-03

Studies: `rlog-tools/studies/grind/CREEP-20HZ-LOOP-ID-2026-09-03.md` (+ `creep20_loop_id.py`), `rlog-tools/studies/osc-highangle/HIGHANGLE-r34-2026-09-03.md` §8-9,
`docs/research/GRINDING-ROOT-CAUSE-LEDGER-2026-09-03.md` (98 hypotheses, 26 contradictions), `docs/traces/TRACE-2026-09-03-engaged-only-loops-at-20hz.md`.
Handoff for the fix: `docs/handoffs/2026-09/HANDOFF-2026-09-03-GRINDING-for-deep-analysis.md`.

| claim | status | method |
|---|---|---|
| f fixed 20.3-21.0 Hz on r31-r34; +0.5 Hz over an 18x rate range | EVIDENCE | 491 line windows |
| presence 13/42/83 % at idx 0 / 1-20 / 20-60; zero when manual | EVIDENCE | per-window census |
| inner loop crossover 17-21 Hz, PM 35-60, Ms 2-2.9 | BELIEF (28 s creep data, off-line coh 0.3-0.6) | tap plant x firmware loop |
| D ~55 % / P ~45 % of the tap's 20 Hz | EVIDENCE | chain mirror on the measured rate |
| no 20 Hz in the 0xE4 command; freezing cmd removes 23 % | EVIDENCE | mirror counterfactual |
| Kd 0/64 -> resonance at ~8 Hz with larger peak | BELIEF | closed-loop model |
| band scales with the x6 forward gain; only rate/accel feedback ever reduced it on car | EVIDENCE (record) | ledger §3 |

Open dispute: whether the engaged-only r24 twist-derivative lane (0xC6446 = 5244) pumps or damps at 20 Hz -- see
[[accord-grind-happens-hands-off-the-bar-signal-is-twist-and-the-engaged-rate-lane-gate-is-live]]. Related:
[[accord-the-8x-gain-is-the-carrier]], [[accord-v62-rate-lane-was-silently-lost]], [[accord-lanechange-ring-is-the-outer-loop-the-map-never-touches-the-eps-rate-feedback-gain]].
