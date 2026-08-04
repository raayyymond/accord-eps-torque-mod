---
name: accord-v69-built-speed-shaped-rate-lane
description: "V69 built and FLASHED 2026-08-04 (route 4f) — ×4 dose + a ratchet-aimed probe, reverting V67's flat LKAS-gated arm to scale the low-speed end of Honda's own gain surface. FLEW: dose fully delivered, grind #1 BACK at creep, dose-response non-monotone."
metadata:
  node_type: memory
  type: project
  originSessionId: 95bceff4-4059-403e-a0cd-c57effc19f41
  modified: 2026-08-04T04:34:47.697Z
---

🛑 **STATUS UPDATE 2026-08-04: V69 IS NO LONGER UNFLASHED — IT FLEW ROUTE `4f--61171e660d` AND IT IS THE
IMAGE ON THE CAR.** Flight-clean; the ×4 dose was **fully delivered** (transfer-corrected `|dtorque|`
max 633.9, **0.0000%** above the 683 rail, so the pre-flight 0.81× saturation worry did not bite); but
**grind #1 came BACK at creep (2.244 [1.438, 3.191] vs V62, holding under both resampling units)** and
**the dose–response is NON-MONOTONE with a minimum near 2×**. V69's stated purpose — the ~28 Hz
lane-change transient — is **dose-independent** and was not helped.
⇒ **V70 restores V67/V68's control path.** Full result:
[[accord-v69-flew-dose-response-non-monotone]]; probe post-mortem in [[accord-v69-ratchet-probe]];
lane-change verdict in [[accord-lane-change-transient-is-dose-independent]].
**Original build note follows.**

★★★ **V69 BUILT 2026-08-04, UNFLASHED.** Fixes the highway lane-change vibration (a ~28 Hz transient,
see [[accord-v68-lane-change-is-28hz]]) by deleting its mechanism: V67/V68's **flat** rate-lane arm
whose delivered multiplier *rises* with speed and peaks at highway (**2.4383×**), because a flat
scalar replaces a surface Honda rolls off (3072 → 2151).

🛑 **RE-CUT THE SAME DAY ON TWO OPERATOR INSTRUCTIONS: dose ×2 → ×4, and the probe re-aimed from the
grind detector to the RATCHET** (see [[accord-v69-ratchet-probe]]).

**7 edit sites / 70 bytes / 3 CRC blocks / cave extent UNCHANGED (66 of the proven 68 B):**
`0x3AA96` `fb`→`c5` (gate reverts to the dead `gp-0x683c`) · `0xC6446` 5244→512 ·
`0xD2A7E`/`0xD2A80` 3072→**12288** (mode-10 gain_B **0 km/h** Y[0..1]) · `0xD2ABA`/`0xD2ABC`
2561→**10244** (**10 km/h** Y[0..1]) · `0xC4B34`-`0xC4B77` the ratchet probe.
Image SHA `48bb4192…`, RWD SHA `e62fcbba…`. (The ×2 cut was `e6bcb2dd…`/`a0a7fd92…`.)

**Multiplier 4.000× to 10 km/h → 3.658 @15 → 3.307 @20 → 2.578 @30 → 1.808 @40 → EXACTLY 1.000× at
and above 50 km/h**, both arms. ★ **The highway 1.000× is STRUCTURAL**: ≥50 km/h reads only
rec2/rec3, which the edit does not touch (12,221-point sweep). ★ **Scale-invariant**: scaling the
whole flat `[0,400]` segment gives 4.000× on BOTH candidate axis scales, **no hump anywhere**.

🛑🛑 **WHAT ×4 COSTS — the shape is identical to ×2, only the dose moved.**
1. **THE FLOWN BRACKET IS BROKEN.** At 2.000× GATE 2's magnitude leg was an *interpolation* between
   stock (1.00×) and V62/V65 (2.00×, flown flight-clean). **4.000× extrapolates to twice the largest
   dose this kit has ever driven.** What survives: phase untouched (no filter/pole/delay/`sar`), the
   lane is linear, V65 measured the aggregator never railing (120,049 frames), grind #1's
   dose-response monotone through 2.00×.
2. **SATURATION CROSSES THE RECORD.** Peak gain 12288 rails r24 at `|dtorque|` **683** vs the
   repo-recorded max **839** ⇒ margin **0.81×**, *it can rail*; at ×2 (peak 6144, rails at 1366) it
   could not. Against the V68-route max 511 it is 1.34×. ⚠ every `|dtorque|` figure in this kit is a
   **LOWER BOUND** (50 Hz Nyquist), so the true margin is worse. ★ **probe bit6 measures this on-car.**
3. **Manual creep is 4.000×** on the pessimistic axis scale. Manual highway stays byte-identical to
   stock. Fold step at rateKey ≥ 13001 (unreachable) widens to 2.00 → **8.00×**.

🛑 **THE DESIGN IS FORCED**: the gate branch is 10 bytes with **zero slack** and **REPLACES** the LERP,
so "gated AND speed-shaped" needs a 1 kHz cave — the only bricking class. Rejected.
🛑 **~~Design A~~ rejected on three counts**: hump **2.753×** (not the recorded ~2.45×); swings
2.00×→1.22× across axis scales; delivers only **1.1–1.5× at |rate| 16–32 deg/s where V62's fix
measured LARGEST**.

🛑 **MECHANISM SUGGESTIVE, NOT ESTABLISHED** — 26–30 Hz dose ratio **3.334 [1.201, 6.492]** inside a
null of **[0.33, 3.36]**; the operator declined the settling drive. **P3 (40–49 Hz doesn't move) and
P4 (1–4 Hz doesn't move) are the negative controls that catch it being wrong.** ⚠ **P1/P2/P6 were
sized for ×2 and are NOT re-derived for ×4** — the dose-response is measured only to 2.00×, so
quoting their intervals at ×4 would be inventing precision; read them as directions. P7/P8/P9 are new.
An ordinary 20–30 min engaged highway commute tests the highway question; **add parking-lot creep
(engaged, hands-off, large angle) for the ratchet probe.**

See [[accord-v69-two-build-traps]], [[accord-v69-ratchet-probe]],
[[accord-aggregator-lane-mirrors-6ada-6adc]]. Spec `docs/V69-DESIGN.md` §0; builder
`build_v69_tva.py`; verifier `verify_v69_image.py`; decoder `rlog-tools/decode_v69_ratchet.py`.
