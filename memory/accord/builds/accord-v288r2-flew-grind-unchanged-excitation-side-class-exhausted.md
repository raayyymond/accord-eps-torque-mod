---
name: accord-v288r2-flew-grind-unchanged-excitation-side-class-exhausted
description: "V288 rev 2 FLEW 2026-09-08 (route 75604b0a…0000005e--03a9714d78, 642 s engaged, 3 operator bookmarks): the cave is LIVE (b4.5 = sign(y) agrees with the mirror 99.5 %), the D-clamp bind duty fell x0.03 as designed — and the grinding is UNCHANGED: same 20.0–20.4 Hz line, mark 3 louder than any V282 episode, rate/amplitude/class/frequency inside V282's route spread. The excitation-side (reference) class is exhausted; the ring's size is set by the loop's damping. Also: the +1 rounding fix makes the filter a unit-slew follower below 16 counts, so the small 20 Hz echo passes at 0.93."
metadata:
  type: project
---

# V288 rev 2 flew: grind unchanged, the reference-side class is exhausted (2026-09-08)

| claim | status | method |
|---|---|---|
| build on the car = V288 rev 2 | EVIDENCE | 0x14A b4.5 == sign(y_model) 99.50 % of engaged frames; duty per segment strictly in (0,1); b0–b2 = 1 |
| D-clamp bind duty 0.0095 → 0.00028 (x0.03) on the same route with/without the filter | EVIDENCE | 1 kHz mirror over every engaged run, bit-for-bit vs GI.simulate |
| line frequency 19.99 vs 19.93 Hz (KS p 0.18); episodes 258/h vs 239/h; env-peak p50 126 vs 127 (MW p 0.92) | EVIDENCE | grind1_census_v282 pipeline, thresholds frozen, reproduction of r39/r3a/r3c exact |
| rung-bell post/pre ratio at capped onsets 2.41 vs 2.25 — unchanged | EVIDENCE | census 5c |
| marks at 129.3 / 331.5 / 820.1 s: 20.12 / 20.00 / 20.39 Hz; 18–22 Hz bar envelope 450 / 177 / 651 (V282 r39 route max 397) | EVIDENCE | orchestrator recompute + marks agent |
| nothing above 22 Hz carries > ~15 % of the 18–22 Hz amplitude | EVIDENCE | marks agent; the operator's "higher frequency" guess is not on the wire |
| below |sp−y| < 16 the cave steps y by exactly 1/tick (unit-slew follower); 18–22 Hz attenuation 0.93 in small-signal windows (2/3 of engaged time), 0.47 in large-error windows | EVIDENCE | arithmetic of the +1 fix + route measurement (qlive) |
| no new 1–3 Hz wallow on straight hands-off driving | descriptive | one route per arm |

**Why it matters:** the whole V288 rationale was "cut the excitation and the bell shrinks". The excitation the
filter targeted (capped-frame D kicks) is measurably gone and the bell did not shrink. The 20 Hz ring's amplitude
is therefore governed by the LOOP's damping, not by the reference. Both filters that could add phase at 20 Hz sit
INSIDE the rate loop and have never been touched in ~290 builds: the feedback lag 0xC63E8/EA (923/1560, 16.5 Hz, on
gp-0x6a56 → r26) and the output lag 0xC63EC/EE (992/507, 5.05 Hz, on the clamped P+I+D sum at 0x2A174–0x2A1B0,
|H(20 Hz)| = 0.24). Design study: `docs/specs/design/DESIGN-20HZ-DAMPING-LOOPSHAPE-2026-09-08.md`.

**How to apply:** do not propose another reference-side filter, another D-kick reduction, or a re-cut of K. The next
lever is in-loop phase (a pole move or an in-loop filter cave) with GATE 2 on the measured mode. Reads:
`rlog-tools/studies/grind/V288-QLIVE-R5E-2026-09-08.md`, `V288-MARKS-R5E-2026-09-08.md`, `GRIND1-CENSUS-V288-R5E-2026-09-08.md`.
Caches: `analysis-2020accord/_scratch/cache/{r5e_v288/, v280/r5e_v288*}` (key `5e2`; `r5e/` is an unrelated 2026-08 route).
See [[accord-v288r2-setpoint-prefilter-cave-built-adversarial-pass-passed]], [[accord-the-creep-grind-is-the-lkas-rate-loop-crossover-resonance-d-dominated]].
