---
name: accord-v298-flew-route79-loop-live-freeze-and-o1-fire-on-reaction-twist
description: "V298 FLEW 2026-10-02 (route 79 `00000079--a1f5d2a272`, 1224 s, image A16A, fork Dom 2712e1336, angle mode): the angle loop is LIVE and correctly signed (ratio -1.0, D opposes in every band at 0.55-0.88x design, Ki 2.8 /s pooled); the kit instrument's 'R1 INVERTED' was ITS OWN artefact (direction-0 ramp, torque word 10 ticks late, un-anchored I) — repaired; operator: small-angle robust, big manoeuvres lacking/not 6x, bar wrong, stuttery. MEASURED: tap peak 59 % of the 2461 rail (rail byte-identical since V282 — 6x was never in this design); hard manoeuvres were HAND-steered AOL (steeringPressed 53 %, engaged 0 %) so the system yielded by design; in slews the wheel covered 0.37 of the setpoint travel with ~6 deg error and 5-32 % of rail (stiffness x the error the fork allows; A3 + clip cap low-speed P+I at ~62-65 % of rail); the FREEZE (512/300) and the fork's O1 (600) fire on the hands-off reaction twist (p90 607-681 below 8 m/s), freeze toggles 2-5/s, 26-37 % of integration discarded; stall-surges ENRICHED 2.7-5.6x within 0.25 s of a 300/512 crossing (V282/V294 show none) = the ratchet; small-correction stick 9x V282 (dwells 4.7/1.2/4.5/3.5 /min), bandwidth 0.4-0.6 Hz, lag 260-440 ms; the UI bar = (a_lat desired - roll)/0.3247 (actual accel cancels) pinned 60 %, |corr| with torque 0.14; no ring, F7 0, no new 5-30 Hz line"
metadata:
  type: reference
---

Synthesis + constraints C1–C13: `docs/scoring/DRIVE-READ-V298-r79-2026-10-02.md` (§5), corrected by
`analysis-2020accord/studies/angle_loop/v298_flight/reports/REFUTE-synthesis-{data,inference}.md` (the 120 deg/s cap
is the second half of the O1 relay, not an independent #1; O1 by TIME is 86 % real hand; the freeze is the enriched
ratchet mechanism; the > 22 m/s tracking FAIL did not reproduce). Six analyst reports beside them; caches
`analysis-2020accord/_scratch/cache/v280/r79_a1f5d2_al.npz` + `r79_fork.npz` (README). D-sign trace
`docs/traces/TRACE-2026-10-02-fresh-rate-D-sign-and-pol.md` (pol = −1 pinned by a run-time re-assert in
FUN_000497e6, which the record had wrongly called dead; the tap-vs-wire-rate D sign is pol-invariant by construction).
Camera LKAS was on for 3906 frames: the panda FORWARDED them to bus 0, none reached bus 1 (the EPS bus).
Related: [[accord-v298-angle-loop-built-not-flown-four-lenses-pass-with-defects]],
[[feedback-analysis-scripts-must-run-in-seconds-not-minutes]].
