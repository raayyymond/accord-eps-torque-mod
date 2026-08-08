---
name: accord-v68-lane-change-is-28hz
description: "V68 flew on routes 4c/4e; the felt lane-change vibration is a ~28 Hz transient, not grind #2's 40-49 Hz, and \"only when engaged\" is refuted at 40-49 Hz."
metadata: 
  node_type: memory
  type: project
  originSessionId: 95bceff4-4059-403e-a0cd-c57effc19f41
  modified: 2026-08-04T01:04:46.537Z
---

★★★★ **V68 FLEW 2026-08-03 on routes `4c` (LKAS OFF manual highway, "no grind felt") and `4e`
(LKAS ON, "definitely felt the grind #2-like vibration when changing lanes").** Confirmed from the
probe, not the filename: byte4 ∈ {0x8F, 0xCF}, **bit3 = 100.000% of 53,991 frames**. Flight-clean —
`ST==4` 0, `ST==3` 0, two methods, watchlist clean.

**THE EVENT IS CAPTURED — `4e` seg 33, t = 51.3 s.** openpilot ALC right lane change at 25.93 m/s:
bar **1468 counts p-p**, **26–30 Hz envelope 614** (20× route median), lines at 27.73/**28.12**/
**28.51** Hz at prominence **100–107** — while **40–49 Hz reads 69 in the same window**. Not wheel
order 2 (24.93) or 3 (37.40), not engine order 1 (26.10) or 2 (52.20). ✅ The estimator's own
control fires in that window: 37.10/37.49 Hz *is* wheel order 3.
⇒ **the felt lane-change vibration is ~28 Hz; grind #2's band is quiet during it.**

**"ONLY WHEN ENGAGED" IS REFUTED AT 40–49 Hz.** Maneuver/control inside each arm, own split-half
null: 40–49 **2.516 [1.561, 3.701] engaged vs 2.558 [1.469, 3.747] manual** — identical; 30–40 too.
The engagement-conditional part is at **18–28 Hz** (18–22: 3.13 vs 1.78; 24–28: 5.10 vs 2.06).
🛑 **Arm and dose are the SAME variable** — V68's gate makes LKAS-ON = Kd 2.00× and LKAS-OFF = Kd 1.

**THE MISSING ARM IS CLOSED:** `4c` gives **234.8 s disengaged above 20 m/s** vs the prior corpus's
0.0 s at every cut. ⚠ `4c`/`4e` are different roads 14 h apart — only within-arm contrasts count.

⚠ **The rate-lane suggestion is SUGGESTIVE, NOT ESTABLISHED:** maneuver-conditioned 26–30 Hz dose
ratio **3.334 [1.201, 6.492]** against a split-half null of **[0.33, 3.36]** — it does not clear its
own floor (Kd=1 maneuver arm is only 39 windows / 17 blocks ≈ 50 s).

⇒ ★★★ **NEXT: ONE HIGHWAY RUN ALTERNATING LKAS ON/OFF EVERY ~60 s ON ONE STRETCH, WITH DELIBERATE
LANE CHANGES IN BOTH ARMS — no build.** V68's gate carries both doses, so dose/road/tyres/time all
become within-route. Need ~150–250 s more active maneuvering LKAS-off ≈ 20–30 lane changes; null
ceiling falls 3.65× → 2.42× at 51 blocks → 1.96× at 102.

See [[accord-v68-detector-still-zero-no-positive-control]] and
[[accord-averaged-spectrum-needs-matched-speed-distributions]].
Reproduce: `analysis-2020accord/analyze_v68_highway_arms.py` + `_followups` + `_engaged_line` +
`_line28` + `_line28_identity`. Handoff: `docs/HANDOFF-2026-08-03-v68-flew-the-lane-change-is-28hz.md`.
