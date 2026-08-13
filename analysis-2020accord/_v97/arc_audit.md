# ARC AUDIT for V97 — V38 → V96 read as ONE arc, from the RECORD

**Author:** arc-audit agent, 2026-08-12. **Scope:** repo/record only — no Ghidra, no builds, no edits
outside `analysis-2020accord/_v97/`. A separate agent is checking the same questions against the
**image**; where I say "the record says", that is what I checked.

**Sources actually read:** `docs/STATE.md` (§A1–A7 + §0–§6b), `docs/BUILD-LINEAGE.md` (RULES 3–13,
struck lists, Parts 2/3/4), `docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md` (extracted to a compact index,
`_lever_index_compact.txt`, because whole-file reads blow the cap),
`docs/ARC-AUDIT-2026-08-10.md` (the prior V38→V89 audit — this file **extends** it, it does not
replace it), `docs/TRACE-2026-08-11-return-to-centre-gate.md`,
`docs/HANDOFF-2026-08-11-routes-78-79-and-the-inertia-reversal.md`,
`docs/HANDOFF-2026-08-11-v90-flew-and-the-lever-search-closed.md`,
`docs/HANDOFF-2026-08-12-v94-aborted-and-the-override-regime.md`,
`docs/REDTEAM-2026-08-11-term0-verdict.md`, `memory/MEMORY.md` + `MEMORY-PART2.md` +
`accord-return-centre-and-detent-dead-engaged.md` + `accord-r26-is-structurally-inert.md`,
`analysis-2020accord/build_v96_tva.py`, and a grep of all 92 `build_v*_tva.py`.

**Convention.** Every decision-bearing claim is marked **[EVIDENCE]** (with method) or **[BELIEF]**.
Where the record contradicts itself I quote **both sides** and do not pick one (§7).
🛑 Kit jargon ("the ring", "grind #1/#2", "S1…S4") is a **band name**, not a symptom the operator
named. His words are grinding · vibrating · stuttering · micro-ratcheting · ratcheting · excess
friction. I quote him verbatim wherever the record preserved his words.

---

## §0 — THE CRUX, AND WHAT THE ARC ALREADY SAYS ABOUT IT

> *"notice how in capture 1 and 3 there is ringing in the driver torque, and a wiggle in the steering
> angle as it returns to center. Notice how normally, without LKAS engaged, there is no ringing in
> driver torque sensor and no wiggle in the steering angle as it returns to center. The 2nd case is
> how the LKAS return to center should look, AND it should be faster than with LKAS disengaged.
> THIS is the crux of micro-ratcheting and grinding."* — operator, 2026-08-12

Four things in the arc bear on this **before any new tracing**:

1. 🛑🛑 **The firmware's only active-return lane is measured DEAD in both arms, and every cell in it is
   virgin.** Return-to-centre is not being *suppressed by LKAS* — on the current evidence it is not
   being *delivered at all*, engaged or manual. §3.
2. ✅ **"Ringing only when engaged" is CONFIRMED by the instrument, in his own regime.** 6–9 Hz
   column-torque OVR/MAN-ON = **1.43…2.90, median ~2.2×, 10 of 10 routes across 9 builds**
   (`STATE.md` §A2), on top of the standing corpus result that engagement multiplies the 6–9 Hz band
   by **2.8× band-specifically** (+0.413 [+0.146, +0.667], 235 episode blocks). *"Literally every bad
   symptom is LKAS engaged only"* — corroborated. An orchestrator claim that *"~80 % of what you feel
   isn't gated on LKAS"* was **retracted**; ~55 % of the 6–9 Hz energy is engagement-attributable.
3. ⭐ **A "wiggle as it returns" is a SLOW object, and the arc has exactly one slow mechanism**: the
   authority-collapse surge at **~0.5–1.7 Hz**, authority pinned at exactly 0 for **17.5–40.5 % of
   override time** while openpilot winds up 6.7–15×. **Virgin on all 90 images.** 🛑 It is explicitly
   **NOT** the 6–9 Hz object (refuted five ways) and **the operator has not yet said whether he feels
   it** — the question is outstanding. §3.5.
4. 🛑 **The 5.12 s band estimator does not survive the override regime.** 5013 contiguous override runs
   make up 994.9 s: median run **0.02 s**, p90 **0.55 s**, only **SEVEN runs corpus-wide** reach 5.12 s.
   Any return-to-centre scoring must be **event-triggered / point-process**, or 1.28 s windows, **and
   must say which.** [EVIDENCE, `STATE.md` §A2]

---

## §1 — THE CROSS-BUILD MATRIX, V38 → V96

Class taxonomy, as the arc's own builds declare it:
`V38–V52` authority / filters / poles / caves · `V53–V61` telemetry + lane mutes · `V62–V73` the rate
lane (r24/r26) · `V74–V83a` the base-assist damper · `V84–V86B` damper reverts + phase ·
`V87` **subtractive** · `V88` Lever B restored · `V89` the **plant model** · `V90` pure instrument ·
`V91/V92` the `0xCBE74` ×1.5 dose + instrument · `V93/V94` the `0xCBE74` **cut** (aborted) ·
`V96` pure instrument + revert.

Verdict words are used strictly:
**FIXED** = the operator called it fixed · **NULL** = flown, measured no change · **FALSIFIED** = flown,
measured worse or a pre-registration excluded · **INERT-BY-MODE** = the edit was never in force ·
**REVERTED** = silently lost at a rebase · **NEVER-FLASHED** = built, never driven · **ABORTED** = flown
and the operator stopped driving it.

| build | base | class | cells moved (from → to) | operator's words | instruments | verdict |
|---|---|---|---|---|---|---|
| **V38** | — | authority + fault fix | `0xC646C` 1782→3564 · `0xC61B2`/`4` 1024→2048 · `0xC61C0/C2/C4`→`0xFFFF` · `0xC64B4/B6`→`0xFF` · corridor/boost INT `0xC674F…` ±1024→±5120 + 7 FP mirrors · ARB setpoint 15360→16384 ×8 copies | fault-free | — | **FOUNDATION.** Never reverted. Everything since is judged against it |
| **V39** | V38 | telemetry cave + conditional lane kill | cave `0xC4B34` 44 B · `0x3AC78` · r24 conditional kill (`0xC6440/42/46`, `0xC61F6`) | — | — | FALSIFIED — and near-inert by construction (±3 deadzone). ⚠ tested the lane **DOWNWARD** |
| **V40** | V38 | cal (speed selector) | `0xC6206`/`0xC6208` → `0xFFFF` | ☠ EPS lamp, no power steering at ignition | — | ☠ **BRICKED.** Magnitude, not direction |
| **V41** | V38 | revert | undoes V40 · `0xC5030`/`0xC521A`/`0xC5232` | boots clean | — | FALSIFIED the motor-rate cap (clean subtractive test) |
| **V42** | V38 | pole + macro-ratchet fix | `0x454FE` `BA`→`B5` · `gain_A` all 4 recs → 0 · `0xC643E`→0 · `0xC6444`→0 | ***"ratchet fixed"*** | — | **FIXED** — but **RE-ATTRIBUTED 2026-08-05**: ch.1 (`0x454FE`) never executes while driving (`gp-0x67fa==4` = 0/123,277) ⇒ the live delta was **ch.2, the r26 kill** |
| **V43** | V42 | pole | `0xC644A` 1024→32 | — | — | **NULL.** Lane later eliminated by V56. frozen 52 builds |
| **V44** | V42 | mode-indexed | FactorC raise (`0xD27C6`/`0xD27DA`) | — | — | **INERT-BY-MODE** (RULE 7) + FactorE re-zeroes the product |
| **V45** | V42 | cal | `0xC6206` hands-off slew | — | — | FALSIFIED |
| **V46** | V42 | filter | `0xC6450` 1024→32 | — | — | **NULL.** Moot — V56 deleted the lane. frozen 51 builds |
| **V47** | V42 | mode-indexed, C **and** E | `0xD2802/04/06`, `0xD2816/18/1A` | ***"marginally quieter at 5 mph, no effect in motion"*** | — | the only real simultaneous C/E test. ⚠ its "confirmed LIVE table" finding was **WITHDRAWN 2026-08-08** |
| **V48a** | V42 | cal | `0xC4120` + `FUN_0003a382` `uVar27`→256 | — | — | NULL — one branch of three |
| **V48b** | V42 | **CODE CAVE — 1 kHz biquad notch** | new cave in the always-on base-assist loop | ☠ | — | ☠ **BRICKED.** (a) RAM collision `gp-0x14FA` aliased a live monitor byte (b) unmodelled resonator |
| **V49–V52c** | V42 | filter / EMA | `0x3A836` stage-C flip · `gp-0x4f60` broad EMA cave | ***"V52C did not fix the vibration; it clearly changed manual feel"*** | −6.1 dB @21 Hz is the **filter's designed attenuation, not a measurement** | **NULL.** 🛑 The "halved the mode" claim is **STRUCK** — it was never a number |
| **FOURFRAME** | V52c | telemetry cave | 4-frame CAN piggyback | — | silent | own bug — STRB=0x80 / SSAM=0 |
| **V53** | V52c | telemetry + cal | `0xC62EA` 320→**0** ("steer to zero") + FOURFRAME2 | — | ST=0 in 5,995/5,995; 226 frames of `STEER_CONTROL_ACTIVE=1` below 5 km/h | ✅ **CONFIRMED WORKING.** 🛑 also the build where `0x454FE` was **REVERTED** and stayed lost for 18 builds |
| **V54** | V53 | telemetry cave | 5-bit authority probe → `0x14A` byte4 bits 7:3 | — | byte4 `0x07`→`0x0F`, 100 % | ★ first working firmware telemetry channel. Authority is **0 BY DESIGN** |
| **V55** | V54 | telemetry cave | dual probe (damper bit + 4-bit `gp-0x6b98`) | — | 21 Hz **inside** the EPS, not commanded | ★★ partition, not a lever |
| **V56** | V55 | **lane mute** | `0xC6AFC`/`0xC6AFE` 32768→0 | ***damping removed*** | 21 Hz unchanged (786× vs V55's 877×) | 🛑 **FALSIFIED *AND* HARMFUL.** ⚠ **scored 15–26 Hz, NEVER 6–9 Hz** — a band-scoping gap, not a clean kill |
| **V57** | V56/V38 | decouple | `0x2A1F0` `0x746C`→`0x7CD0` · `0xC6CD0` −1→3564 · `0xC646C` 3564→891 | — | fault-free | correctness fix, expected NULL for the grinding |
| **V58** | V57 | telemetry | angle-rate/boost-lane probe | — | bit5=0 in all 35,964 ⇒ ceiling `0xD20C0` ELIMINATED | flight-clean |
| **V59** | V58 | telemetry | boost-index DEPTH probe | — | 42.19 Hz = 2× the 21.09 Hz mode, engagement-gated; eps 0.013–0.169 vs thr 0.147 | ★★ pump is **MARGINAL** |
| **V60** | V59 | cal | `0xD2006` 102→43 | ***"It did not fix the vibration issue"*** | — | **NULL.** Closes the V58/59/60 parametric-pump arc |
| **V61** | V59 | **subtractive — r24+r26 dual kill** | `0x3AB6C` `37E1`→`37E0` · `0x3AC16` `4001`→`4000` | ***grinding significantly worse with LKAS on, and newly present in MANUAL*** | — | 🛑 **FALSIFIED, and it INVERTS the record**: this lane is the mode's **DAMPER**. Cutting it is closed for good |
| **V62** | V57/61 | **rate lane** | `0x3AB76`/`0x3AC20` `AA`→`A9` (`sar` ×2) | ***"Original grinding at 2–5 mph is gone!"*** | 18–22 Hz **0.124 [0.036,0.387]** vs V59 | ★★★★ **FIXED — the kit's first measured fix.** 🛑 2× ≈ OPTIMUM, not a point on a ramp |
| **V63–V66** | V62 | rate-lane variants | `0xC6440` 2048→4096 · `0xC643E` 1536→3072 (V63) · detector probe (V64) · saturation ladder (V65) · V62 revert + gate probe (V66) | — | V64 detector **never armed**; V65: the aggregator **never rails** (0/120,049) | V64 = **null on the GATE.** V66 identified V62's own fix as the cause of grind #2 (40–49 Hz **11.71×**, p=0.0003) |
| **V67/V68** | V62 | **rate lane — "Lever B"** | `0x3AA96` `C5`→`FB` · `0xC6446` 512→**5244** | grinding improved; **highway grind persists** | bit6 == `latActive` 99.983 % | ★★★★ **the best-measured lever in the kit, AT ITS CEILING.** V68: the lane-change object is ~28 Hz |
| **V69/V70** | V67/68 | rate lane, mode-indexed | `gain_B` **mode 10** `0xD2A7E`/`80`/`0xD2ABA`/`BC` ×4 | grind #1 back at creep | — | 🛑 **INERT-BY-MODE.** Car is TVCA4 = modes 24/26. **The r24 dose ladder never existed on this car** |
| **V71a/b/c** | V69/70 | rate-lane variants | V71c: `0xC6444` 512→**3072** | — | grind #1 higher (P=0.0215), grind #2 returned, ratchet at corpus RECORD | 🛑 **V71c FALSIFIED — WORSE ON EVERY AXIS.** V71a/b NEVER-FLASHED |
| **V72/V73** | V67/68 | damper arming (unintentional) | `0xC63A0` 1024→**2048** · `0xC407E` 511→**850** (V73) · friction ×1.5 (V73) | — | V73 first build to read the r24 probe as designed | `0xC63A0` **INERT** until V74 opened the dead zones (×2 on zero is zero) |
| **V74** | V73 | **base-assist damper — new class** | FactorC/E engaged columns opened (both dead zones) | ☠ latched total loss of power steering, over a bump, **in MANUAL** | mode-24 records byte-stock ⇒ the edits were not in force when it faulted | ☠ **HARD-FAULTED.** Cause = `0xC407E`=850 (RULE 11) |
| **V75** | V74 | damper dose ↑ | `k` = 1.5798 | ☠ hard-faulted mid-drive | | ☠ **HARD-FAULTED.** ⊕ the only build that ever *eliminated* the grinding |
| **V76** | **V38 (rebase)** | damper, ReLU shape | FactorC `Y[0..2]`→566 · FactorE `X`=[0,119,…] `Y`=[0,300,539,927], `k`=1.3866 | ***"There is still grind #1 and micro-ratcheting at creep"*** | friction probe a clean real null (0/63,477, positive control 99.93 %) | fault-free — 🛑🛑 **and the build that SILENTLY REVERTED SEVEN LEVERS.** §4 |
| **V78** | V76 | damper dose | FactorE `Y[1]` 300→449, `k`=2.0840 | — | — | **NEVER-FLASHED** |
| **V79** | V78 | damper dose | FactorE `Y[1]`→897, `Y[2]`→912, `k`=4.1597 | — | rails **38.9 %** of the envelope; shipped without `0x454FE` | **NEVER-FLASHED — pulled pre-flight.** `SUPERSEDED-…` |
| **V80** | V79 | flat FactorC | `0xC9E9C`[m26] `Y[3]` 908→566 (flat at every speed) | 🛑🛑🛑 ***"the worst grinding this car has ever produced"*** — loud, felt through the whole car, ~90 % of engaged time, **noticeable vehicle instability** | damper emits a constant 495 ct (3.4 % variation over a 34× rate range) at 97 % of ceiling; `N(50)/N(500)` 3.27×; a sustained ~27.4 Hz limit cycle no other build produces | 🛑🛑🛑 **FALSIFIED, WORST.** Moved the relay onto FactorE's knee **17 counts under its own rail** ⇒ **GATE 2 COROLLARY.** ★ but 6–9 Hz did improve at `k`=4.16: 0.418 [0.33,0.61] |
| **V81** | flown V75 | **damper revert** | `0xC407E` 850→**511** · friction ×1.5 → **stock** at all 14 sites | (flew later in the chain) | — | ⚠ *"removes drag the operator is used to"* |
| **V83a** | V81 | damper revert cont'd | FactorE m26→Honda (`k` 1.5798→0.2265) · `gain_A` rec0/1→stock · `0xC63A0` 2048→**1024** | — | grind #1 **2.674× V81** [1.956,3.885]; micro-ratchet **1.526×** [1.174,2.019]; **its own falsifier fired** | 🛑🛑 **FALSIFIED — WORST BUILD IN THE MODERN LINEAGE FOR BOTH SCORED SYMPTOMS.** ⚠ left mode **27** carrying V81's whole damper |
| **V84** | V83a | Lever B + damper→Honda | `0x3AA96`→`FB` · `0xC6446`→5244 · FactorC `Y[0]` 566→0 at `0xD77DA`+`0xD77EE` · FactorE m27→60/400/140 | 🛑 ***"None of these have been fully fixed in V84"*** | ONE band moved: 26–31 Hz burst duty 25.1 %→2.54 % on 3.4–4.9× more highway | **FIXED NOTHING.** All four pre-registered tests FAIL. Band movement **not causally established** |
| **V85** | V84 | **plant-model friction — new class** | `0xC40BC` 600→**6000** | grinding ***"a little better"***, micro-ratcheting ***"barely, perceptibly better (somewhat unsure)"***, **ratcheting STILL UNFIXED** | relay saturation 33.3 %→4.6 % engaged (**7.21×**); bands a clean null (6–9 Hz 1.088 [0.746,1.451]) | cleanest flight in the lineage. 🛑🛑 **LATER INVERTED**: `0xC40BC`=6000 makes 6–9 Hz **2.3× WORSE** (2.89× @600 vs 6.58× @6000) ⇒ **do not restore 6000** |
| **V86** | V85 | **plant-model phase** | `0xC40D4` 573→**286** (EMA α) | — | `f(V86)/f(V85)` = **1.001 [0.976,1.060]**, CI disjoint from the pre-registered [0.797,0.875]; the line stayed at 8.00 Hz | 🛑🛑 **FALSIFIED, WELL-POWERED** ⇒ **the firmware phase-lever search for the ~8 Hz mode is CLOSED.** ⚠ parking-lot only |
| **V86B** | V85 | damper zero-point | FactorC m26 `Y[0]` 0→**908**, m27 0→**875** | ***"still present, dampened I think"***, ratcheting **definitely perceptible**, + ***"extra dampening on LKAS and in general at slow speed"*** | parking-lot only; recovery test **cannot be scored** | the predicted heavier-at-creep cost **CONFIRMED as felt.** FactorE stayed 0 below 12.7 °/s ⇒ **the micro regime was never armed** |
| **V87** | **V38 (deliberate rebase)** | **SUBTRACTIVE — first of its kind** | `0x2A1F0`·`0xC646C`·`0xC6CD0` (V57) · `0x454FE`→`B5` · `0xC62EA`→0 · `0x55DF2` `e893`→`6894` (427 ← `gp-0x6b98`) | ***grinding, micro-ratcheting AND ratcheting all present*** — the PREDICTED result | 427 went to 99.02 % non-zero / 946 distinct; `\|gp-0x6b98\|` engaged median **208 ct**, 6–9 Hz ripple p-p **162 ct** | ★★★★ **the probe fired** — the kit's biggest instrument gain since the cave. Byte-stock at all four grind-#1 addresses |
| **V88** | V87 | rate lane restored + probe fix | `0x3AA96`→`FB` · `0xC6446`→**5244** · `0xC4B38` `9094`→`6894` · `0xC4B46` `a6`→`a8` | ***grinding FIXED*** | 15–22 Hz command **0.549× [0.407,0.844]**; 0.5–3 Hz 1.192 = NULL; identity 0.9654 vs chance 0.6028 | ★★★★ **FIXED (grinding).** 🛑 **NOT a ratcheting lever** — `e_6-9` V88/V67 = 1.040 [0.759,1.260]. First route with real highway |
| **V89** | V88 | **PLANT MODEL — first of its kind** | `0xC40D2` 102→**204** (K1, modelled Coulomb friction ×2.000) + cave probe → `gp-0x6ae2` | — | **FLAT** — order-clean stratum contrast **0.947 [0.827,0.979]** inside a same-build placebo band [0.900,1.111] = 0.92σ | **NULL.** 🛑 the block bootstrap **excluded 1.00** and would have been reported as a 5 % fix — **the placebo control earned its keep on first use.** Left on deliberately |
| **V90** | V89 | **pure instrument** | ZERO cal. Cave 62→74 B · `0x55DF2` `6894`→`da94` (427 ← `gp-0x6b26`) | — | identity single-frame `b4==0` on 124,362/124,362; **1074.6 s engaged (86.41 %), 316.4 s ≥50 km/h** | best exposure to date. **`R` flat at 6–9 Hz, no dip** ⇒ damping lane back in play |
| **V91** | V90 | `0xCBE74` ×1.5 | `0xD7A5C` m26 + `0xD7A6C` m27 `(−9830,−5734,−1966)` → `(−14745,−8601,−2949)` | fault-free (route 78) | dose measured **0.99 [0.91,1.26]** engaged vs a pre-registered **1.50**; duty 0.161 vs a needed 0.204 | 🛑 **THE LEVER WAS NOT IN FORCE — a null on the LEVER, not the flash. UNEXPLAINED.** ⚠ **route 78 cannot be attributed to V91** — no cave bit separates it from V90 and the operator could not confirm the flash |
| **V92** | V90 | same cal + **116 B cave** | V91's 12 cal bytes **identical** · cave 74→116 B · `0x55DF2`→`4294` (427 ← `gp-0x6bbe`) · `0x55E10` `sar3`→`sar4` | fault-free (route 79) | **identity PROVEN single-frame** (`0x14A` byte7[7:6] ≠ 0, 16,236 frames). Return-centre + detent **DEAD** (§3) | same null. **The last configuration the operator drove and did not abort.** ⚠ its lineage row still reads UNFLASHED — §7.3 |
| **V93** | flown V90 | 🛑 **first build EVER to LOWER `0xCBE74`** | m24 ×0.50 · m26/m27 ×0.25 · `0xC640A` −8192→−6144 · `0xC640C` −3277→−2458 | — | — | **NEVER-FLASHED.** Its instrument was not sized for its own edit (87.5 % of frames would read wire ≤1) |
| **V94** | flown V90 | same cal + packer rescale | V93's 22 cal bytes **identical** + `0x55E10` `sar3`→**`sar1`** | 🛑🛑 ***"made the stuttering and grinding worse, by a lot. So much so that it vibrated the entire car, and I decided it was not safe to drive."*** | motor accel **3–7× up** above 9 Hz; column↔wheel coherence 18–31 Hz **the highest of any drive in the corpus**; **no fault of any kind** | 🛑🛑🛑 **ABORTED. STILL ON THE CAR.** ⇒ `gp-0x6b26` is a **REAL 6–9 Hz DAMPER** (+518/+565 ct positive `Re(Z)`, two drives, ω-partialled vs shuffled). ⊕ the code byte is **EXONERATED** — the regression is the CALIBRATION |
| ~~V95~~ | — | — | — | — | — | 🛑🛑 **VACATED — A BURNED NUMBER.** Three artefacts wore it in two hours; `build_v95_tva.py` deleted |
| **V96** | **V92** | **pure instrument + revert** | 🛑 **ZERO calibration bytes.** cave 116→112 B (no growth) · `0x55DF2` `4294`→`9094` (427 ← `gp-0x6b70`) · `0x55E10` `sar4`→`sar6` | — | not flown | ✅ **BUILT, VERIFIED, UNFLASHED — the live candidate.** 166/166, reproduces bit-for-bit. **JOB 1: get the car back to V92. JOB 2: measure `f'`.** 🛑 **explicitly NOT a fix** |

**What V96 carries, cumulatively, per the record** (the image agent is checking this independently):
V38's foundation (4× LKAS gain `0xC61B2`/`4`=2048, gentle-EME disabled, corridor/boost ×5, ARB setpoint
16384) + V57's decouple (`0x2A1F0`=`0xD07C`, `0xC6CD0`=3564, `0xC646C`=**891** stock) + `0x454FE`=`B5` +
`0xC62EA`=0 + **Lever B** (`0x3AA96`=`FB`, `0xC6446`=5244) + **K1** (`0xC40D2`=204) + **`0xCBE74` m26/m27
at ×1.5** (V91/V92's dose — the one that measured NOT IN FORCE) + the 112-byte cave + the 427 repoint.
**`0xC407E`=511 stock · `0xC40BC`=600 stock · `0xC63A0`=1024 stock · friction table stock · FactorB/C/D/E
and the ceiling byte-stock for modes 24/26/27 · mode 24 `0xCBE74` STOCK.**

---

## §2 — 6–9 Hz DAMPING AND PHASE: EVERYTHING EVER TRIED, AND WHICH WAY IT WENT

Ordered by what it targeted, not by build number. **Direction matters more than address** — this arc's
two most expensive errors (V39/V42/V61 vs V62; V91/V92 vs V93/V94) were both *right lane, wrong way*.

| lever | direction | flown | what happened |
|---|---|---|---|
| `0xC644A` (V43) 1024→32; (V49) →64 | pole DOWN | ✅ | **NULL.** Lane later eliminated by V56. Re-framed twice: it was *re-introducing a defeated pole*, not filtering |
| `0xC6450` (V46) 1024→32 | pole DOWN | ✅ | **NULL.** Moot |
| `0xC6AFC`/`0xC6AFE` (V56) 32768→0 | mute the whole `gp-0x6ad4` lane | ✅ | 🛑 **FALSIFIED *AND* HARMFUL** — damping removed, an 8.69 Hz line appeared (later identified as **wheel order 1**, not V56's doing). ⚠ **scored 15–26 Hz, NEVER 6–9 Hz.** A band-scoping gap; **not a clean kill of the lane for ratcheting** |
| `0x3AB6C`/`0x3AC16` (V61) | r24+r26 **KILL** | ✅ | 🛑 **WORSE, engaged AND manual** ⇒ the lane is the mode's **DAMPER** |
| `0x3AB76`/`0x3AC20` `sar` ×2 (V62/V65/V71a) | rate lane **UP** | ✅ | ★★★★ **FIXED the grinding** (18–22 Hz down 8–42×) — **and CAUSED grind #2** (40–49 Hz 11.71×, p=0.0003). **STRUCK** (ungated ⇒ *"the whole car vibrates like a subwoofer"* in manual). Frozen OFF 27 builds |
| `0x3AA96`+`0xC6446` "Lever B" (V67/68/84/85/86/86B/88) | r24 engaged arm **UP** 512→5244 | ✅ ×7 | ★★★★ **the kit's only grinding fix**, at its ceiling. 🛑 **NOT a ratcheting lever** (V88/V67 `e_6-9` 1.040 [0.759,1.260]). ⊕ **CLEARED** by V94-session controls ⇒ need not be traded away |
| `0xC6444` (V71c) 512→3072 | r26 arm **UP** | ✅ | 🛑 **FALSIFIED, WORSE on every axis.** ⚠ note V42 tested it **DOWN** (→0); up and down are now both spent |
| FactorC/FactorE damper (V74–V83a, 11–17 builds) | base-assist damper **UP** then **DOWN** | ✅ ×6 | ☠ V74/V75 hard-faulted (cause `0xC407E`) · V80 **worst grinding ever** · V83a **worst for both symptoms** · V84 fixed nothing. 🛑🛑 **CLOSED as a micro-ratcheting lever ON ARITHMETIC**: `ch₀` is a PRODUCT of two dead zones ⇒ **exactly ZERO on 95.91 % of engaged frames and 100 % of the micro regime.** Sizing kills it too — 25 % authority at 10 °/s needs `Y[0]` off zero = a step at zero rate = the V80 move |
| `0xC63A0` (V72–V76, V76g, V81) 1024→2048 | Path-2 damper weight **UP** | ✅ ×4 | **INERT — no mechanism** (×2 on a zero product). ⊕ **EXONERATED** as the fault cause. Frozen at 1024 for 13 builds |
| `0xC40BC` (V85) 600→6000 | de-relay the Coulomb friction | ✅ | duty win **7.21×**, bands a clean null — 🛑🛑 **but 6–9 Hz got 2.3× WORSE** (2.89× @600 vs 6.58× @6000, contrast +0.682 [+0.213,+1.166]). **The car is at 600 and that is the better value.** ⚠ association is EVIDENCE; attributing it *specifically* to `0xC40BC` is **BELIEF** (V86 also moved `0xC40D4`) |
| `0xC40D4` (V86) 573→286 | EMA **phase** | ✅ | 🛑🛑 **FALSIFIED, WELL-POWERED** ⇒ **the firmware phase-lever search for ~8 Hz is CLOSED.** ⊕ `H(0)=1` exactly for every α — only transient tracking changes |
| `0xC40D2` (V89) 102→204 | plant-model friction **UP** | ✅ | **FLAT** (0.947, inside placebo). Structural reason found by V90: above 1 °/s friction and `\|model\|` are **near-collinear** exactly where the symptom lives |
| `0xCBE74` m26/m27 ×1.5 (V91/V92) | inertia/damper **UP** | ✅ | **DOSE NOT IN FORCE** — 0.99 [0.91,1.26] vs 1.50. **UNEXPLAINED.** The instrument was structurally incapable of measuring its own dose (`gp-0x6b26 = K·α` where α is what K damps ⇒ the product is invariant to K in a stable loop) |
| `0xCBE74` m24 ×0.50, m26/m27 ×0.25 (V93/V94) | inertia/damper **DOWN** — **the first cut in 13 builds** | ✅ (V94) | 🛑🛑🛑 **ABORTED.** *"vibrated the entire car … not safe to drive."* ⇒ **the lane IS a real 6–9 Hz damper.** The premise (*"−K·α adds apparent inertia and dissipates nothing, so lowering is strictly safe"*) was **backwards**, and a **133/133-green assertion suite encoded the wrong premise as a PASS condition** |
| a biquad notch (V48b) | notch | ✅ | ☠ **BRICKED** |
| the 3-tap FIRs `0xC4018`/`1C`/`20`, `0xC4048`/`4C`/`50` | notch | ❌ | **CLOSED ON ARITHMETIC** — identity FIRs; a 21 Hz notch at 1 kHz costs −35.2 dB at DC, normalising needs 229× peak gain |
| FactorD (`0xC9DB4`) | frequency-selective | ❌ | **STRUCK — REFUTED.** Axis is *absolute steering angle*, not a tracking error ⇒ no 1/ω selectivity. **This firmware has NO frequency-selective lever anywhere** |

**Two structural results that bound the whole class:**
- **The ratchet is a lightly-damped RESONANCE, ζ 0.017–0.036 (Q 14–40), motor/rack-side**, driven by
  **broadband** command content, **not** by a commanded tone (V87/V88, prominence 11.17 in the column vs
  5.46 signed command; signed ≈ rectified ⇒ V87's null was correct). **Limit cycle EXCLUDED.**
  ⇒ the lever class is *"less broadband HF in the delivered command"* or *"more damping"* — **not a notch.**
- **`Re(Z) < 0` at 6–9 Hz replicated on THREE drives** (−3375/−3176/−3073, ±5 %), sign flip to damped at
  ~24–26 Hz on all three, **strongest in the MICRO 1–13 °/s regime (−3480, coh² 0.804)** — the regime he
  says is unfixed. ⊕ `Re(Z)` anchored on-car parameter-free: `mean(T·ω)` pooled **+3859**, P(>0)=0.9238,
  n=20,159; it independently ranks **V80 worst**. 🛑 Never quote `Re(Z)` below 6 Hz from a
  `steeringPressed` mask — 2–4 Hz reverses sign. 🛑 **The hands-off coast is STILL UNRUN** — if the
  anti-damping lives in the PLANT, no firmware lever removes it. ~15–20 min, no firmware needed.

---

## §3 — RETURN-TO-CENTRE / ACTIVE RETURN / SAT / DETENT / ON-CENTRE / LOW-SPEED ENGAGED

**🛑 HEADLINE: the neighbourhood is 100 % VIRGIN and the lane is MEASURED DEAD.**

### 3.1 The lane, end to end [EVIDENCE — full disasm, `TRACE-2026-08-11-return-to-centre-gate.md`]

```
FUN_000360fe (0x360fe)
    gp-0x6b64 = -clamp( LERP_Y1(gp-0x6bda) x gp-0x6abc(RAW motor rate) x cal(0xC63BE) >>10 , ±0x2800 )
    LERP table 0xC695C:  X = [-397,-192, 140, 294, 384]
                         Y = [   0, 2560,2560, 717,   0]      <-- ZERO outside (-397, 384)
FUN_00036388 (0x36388)
    two counters: gp-0x6a82 (snap relay, threshold cal 0xC627E = 20)
                  gp-0x6990 (ramp)
    arm test  |gp-0x6b64| < cal(0xC618A) = 1024 ;  past 20 ticks the output SNAPS to ±1024
    -> gp-0x6b62
    called from FUN_0002214a (1 kHz), state-gated gp-0x67fa mask 0x830 => states {4,5,11}
FUN_0003aa2c (0x3aa2c)
    11-lane aggregator: gp-0x6b62 (return) + gp-0x6b4c (LKAS) + 9 others, UNCONDITIONAL ADD
    -> gp-0x6b94 (clamp ±10240) -> FUN_0004503c governor -> gp-0x6ace
    -> FUN_000456a4 comp-add -> gp-0x6acc -> FUN_00042af8 shaper -> gp-0x6b08 -> gp-0x6b98 -> FOC
```
🛑 **There is NO angle term anywhere in either producer.** It is `−sign(motor rate)` gated by a
driver-torque **margin** — a brake, not a position controller. Calling it "return-to-centre" is the
kit's own label; the arithmetic is a rate brake.

### 3.2 The measurement — DEAD IN BOTH ARMS [EVIDENCE]

V92, route 79, 2026-08-11. 87,317 `0x14A` frames / 75,227 engaged.
`memory/accord-return-centre-and-detent-dead-engaged.md`, tool `rlog-tools/extract_r78_r79.py health 79`.

| rung | meaning | ENGAGED duty | MANUAL duty |
|---|---|---|---|
| byte4 b6 | `gp-0x6b62 < 0` (return-centre **sign**) | **0.0000** | 0.0045 |
| byte4 b5 | `gp-0x6b62 ≠ 0` (**lane LIVE**) | **0.0000** | 0.0074 |
| byte4 b4 | `gp-0x6bda ∈ (−397, 384)` (**outer gate OPEN**) | **0.0000** | 0.0074 |
| byte7 b6 | `gp-0x6a82 > 20` (**dwell SNAP**) | **0.0000** | **0.0000** |

`b4 ≡ b5` **exactly**, on every one of 87,317 frames — gate shut ⇒ `gp-0x6b64 ≡ 0` ⇒ lane ≡ 0.
Structural check `(b6,b5) = (1,0)` = **0 frames**, as required.
⇒ **The outer LERP gate is SHUT for 100 % of engaged driving.** The lane contributes a flat −1024 bias,
not a relay. **Do not propose a detent/dwell lever.**

🛑 **The `byte7 b6` rung is INDICTED, not informative.** `(gate=0, snap=0)` on **99.898 %** of frames —
87,228 frames in **3 runs, longest 855 s, 0.0 % adjacent to a gate falling edge**. That is the
**pre-registered SUSTAINED-RUN condition** that indicts the rung map. Read it as a null on the GATE
(V64 class), **never** as "the detent never snaps". Candidates: the arm-condition model is wrong,
`cal(0xC627E) ≠ 20`, or `gp-0x6a82` is not the counter. **Resolve in Ghidra before re-flying that bit.**

⚠ **Why the gate is shut** [BELIEF, well-supported]: `gp-0x6bda` is the **margin to a peak-hold envelope
of driver assist torque `gp-0x6bf0`** (`FUN_00036022` @`0x36068`–`0x3608C`; envelope half-width never
< 9390). A kit memory puts its hands-off value at **≈9262 = 24× outside** the ±384 window
(`memory/accord-r26-is-structurally-inert.md`). So the gate opens only when driver torque sits *at* the
peak-hold envelope. **It did not open even in route 79's override frames.**

### 3.3 Direct relevance to the crux

The operator wants the engaged return to be **smooth and faster than manual**. On the record:
- **The firmware's own return lane cannot deliver that**, because it contributes 0.0000 engaged and
  0.0074 manual. Whatever return trajectory he is watching is **base assist + the LKAS command + the
  plant (caster / SAT)**, not an active-return term. [EVIDENCE for the duties; **BELIEF** that this
  fully accounts for the observed return, since the plant contribution has never been isolated.]
- **The engaged/manual difference in the return is therefore NOT a return-lane difference.** It has to
  come from something that is present engaged and absent manual: the LKAS command itself, or a
  nonlinearity the command's entry moves the loop through. That is precisely §1b's mechanism
  (`FUN_0003b8f6`, a Coulomb relay **proportional to the command**) and the 2.8× engagement contrast.
- 🛑 **NO `if (LKAS != 0) suppress return` branch exists anywhere in this firmware** [EVIDENCE — full
  disasm of both producers, plus structural closure of both candidate hard gates: `gp-0x67ac` proven
  unreachable, `gp-0x67fa` proven decoupled from LKAS engagement by a 33-writer census].

### 3.4 Every cal in the lane — **NEVER WRITTEN BY ANY BUILD** [EVIDENCE, grep of all 92 `build_v*_tva.py`]

| cell | what it is | ever written? |
|---|---|---|
| `0xC63BE` | return-lane gain (×1024 on the LERP product) | **NEVER** — appears only in `build_v92_tva.py`, read-only |
| `0xC695C` | the 5-knot LERP table (count, 5 X knots, 5 Y knots) = **the outer gate's shape** | **NEVER** — V92 reads it *from the image* |
| `0xC618A` = 1024 | dwell **ARM** threshold *and* the snap **CEILING** | **NEVER** — `build_v92_tva.py:524` marks it 🛑 READ-ONLY |
| `0xC627E` = 20 | dwell **SNAP** threshold (~20 ms at 1 kHz) | **NEVER** — `build_v92_tva.py:525` READ-ONLY |
| `0xC63C0` | return-lane companion cal | **NEVER — 0 grep hits in any build script** |
| `0xC6132` | return-lane companion cal | **NEVER — 0 grep hits** |
| `0xC6970` | LERP table tail | **NEVER — 0 grep hits** |
| `0xC63C2` = 1024 | sibling trapezoid scale (`gp-0x6b5e`, r26's own gate) | **NEVER** — V92 READ-ONLY |
| `0xC66CC` | that trapezoid, X=[−384,−128,128,294,384] Y=[0,4762,4762,717,0] | **NEVER — 0 grep hits** |
| `0xC74AC` | the "reduced" aggregator branch that *could* zero return-centre | **NEVER — and PROVEN STRUCTURALLY UNREACHABLE** (`gp-0x67ac` ≡ 0) |

**Probed, never edited:**
- **V69 bit5** `gp-0x6b62 ≥ +4096` — *"the operator's own hypothesis, never probed in 69 builds."*
  🛑 **INSENSITIVE, not vacuous**: reachable max is **5786**, so the rung sampled only the top **29 %**.
  **This is not a null on the lane.** (`feedback-size-probe-rungs-against-lane-reachable-output`)
- **V92 byte4 b6/b5/b4 + byte7 b6** — §3.2. b4/b5/b6 sound; byte7 b6 indicted.

### 3.5 What DOES couple LKAS to the return trajectory — three mechanisms, ranked

1. ⭐⭐ **The rate-adaptive governor ceiling** [EVIDENCE for the mechanism; **BELIEF** for the
   return-to-centre application]. `gp-0x4f64 = MIN(gp+0x130, gp+0x128, …) × 1024`, where `gp+0x128`
   is looked up from **motor electrical rate** `gp-0x6ac0` against `0xC520C`:
   `X = [1050,1700,2500,3700,4100]`, `Y = [5325,3584,2406,1587,512]` — **falling**. Nominal ceiling
   4762; at rate ≥ 4100 it collapses to **512, a ~90 % cut.** It caps the **combined** sum that holds
   both `gp-0x6b62` and `gp-0x6b4c`. **LKAS aligned with return makes the wheel turn faster ⇒ shrinks
   the ceiling ⇒ throttles both terms exactly when the combined push is largest.** Symmetric, not
   LKAS-specific — but `FEASIBILITY-8X-LKAS.md` item 10 already found that **at today's 4× gain,
   moderately fast steering already clips here.** This is the best-supported account on record of
   *"return is restricted even when LKAS agrees."*
   🛑 **The one number that would turn it into EVIDENCE is missing:** `gp-0x6ac0`'s counts-per-°/s is
   **not established** (it is a *different* signal from `gp-0x6abe`, whose 4.7121 ct/(°/s) is settled).
   Whether an ordinary return reaches `X=[1050…4100]` is **the single most important open item** in
   this neighbourhood.
   ⚠ `0xC520C` was written only by **V39/V40/V41**; V40 **BRICKED** on a neighbouring governor cal.
   It sits beside the DTC-0x1d lockstep monitor ⇒ **full GATE 1 + GATE 2 before any edit.**
   ⊕ If this reading holds, the indicated move is closer to **lowering `0xC6CD0` toward stock** than to
   a new lever — but see §5: `0xC6CD0` is the 4× LKAS gain and the record's standing rule is
   **NEVER lower it**. That tension is unresolved and belongs to the operator.
2. ⭐ **The shaper's one-sided hard relay.** `FUN_00042af8` `0x431d0`–`0x431d8`: `gp-0x6acc > +8192`
   hard-zeroes the **entire base-assist leg — return-centre included — for that cycle**, a single
   combinational compare with **no hysteresis** and **only on one sign**. A textbook one-sided
   limit-cycle generator, and a one-sided artefact is exactly the shape of *"a wiggle as it returns."*
   **Never probed, never edited.** [EVIDENCE for the structure; **BELIEF** that it is the wiggle.]
3. ⭐ **The authority-collapse curve** — the only mechanism in the kit at the timescale of a "wiggle".
   Mode-7 records `0xE547C`/`0xE5404` (X = 70/72/78/80 → Y = 254/234/12/**0**) and `0xE52FC`/`0xE5284`
   (X = 32/42/80/112 → Y = 255/255/255/**0**). **Authority goes 254 → 0 across raw 2240 → 2560 — a
   320-count near-step.** 🛑🛑 **All four are VIRGIN across all 90 `_v*` images.**
   Measured **median override torque 2235 against a first knot of 2240** — he drives on its knee.
   Produces the measured **~0.5–1.7 Hz surge**: authority pinned at exactly 0 for **17.5–40.5 % of
   override time** while openpilot winds up **6.7–15×**; ease back below the knot and authority returns
   with a command an order of magnitude larger.
   🛑 **It is NOT a 6–9 Hz lever** — refuted five ways in one session (knot crossing rate 0.47–1.69 Hz;
   reconstructed spectrum 88.4–94.9 % inside 0.5–3 Hz, peak 0.79 Hz; unit-scale sweep never exceeds
   1.22 Hz; the chatter↔energy correlation **inverts against its own control**; and 6–9 Hz energy
   *falls* after a collapse edge).
   🛑 **The operator has NOT said whether he feels it.** Until he does, it is a measured behaviour with
   no scored symptom attached.
   🛑🛑 **The safety direction is NOT symmetric.** Honda collapses authority when the driver pushes —
   that is driver-override behaviour. Widening the window makes the car **fight the driver harder and
   for longer.** The only defensible shape change is **MONOTONE-NON-INCREASING**: never above stock at
   any torque, start the decay earlier, reach 0 at the same place. **Anything that raises `Y` at any
   `X` is a different and far more serious proposal.**

### 3.6 ⭐ The 10× LEFT/RIGHT ramp asymmetry — virgin, and nobody has ever asked

`0xC63F8` = **33** vs `0xC63FC` = **328** on the `gp-0x69b0` authority ramp (`0x8000/33` ≈ 993 ms at
1 kHz; the down cal `0xC63F6` = 16, `0xC63F4` = 328). **VIRGIN on all 85+ images** [EVIDENCE, the V94
handoff's own ledger matrix]. A 10× directional asymmetry in the authority ramp is a first-class
candidate for a return that behaves differently one way than the other.
🛑 **Outstanding operator question: does the car feel different turning left versus right?**
It has been on the open list since 2026-08-12 and has not been asked.

### 3.7 On-centre / low-speed-engaged — everything ever tried

| lever | build | flashed | result, in HIS words where the record has them |
|---|---|---|---|
| `0xC62EA` 320→**0** low-speed steer lockout | V53 | ✅ | ✅ **CONFIRMED WORKING** — ST=0 in 5,995/5,995, 226 frames of `STEER_CONTROL_ACTIVE=1` below 5 km/h, no fault/no dash light. **On the car** |
| `0xC64DE` `0x11`→`0x1B` re-engage ramp | V18 | ✅ | *"drives well"* — ⚠ ~10 s timescale, **wrong for a 7.8 Hz object**, **label DISPUTED since 2026-07-18**, and **carried 85 builds without ever being isolated.** The longest-carried unmeasured cell in the image |
| FactorC creep damper `Y[0]`→908/875 | V86B | ✅ r70 | *"still present, dampened I think"*, ratcheting **definitely perceptible**, + *"extra dampening on LKAS and in general at slow speed"* — **the predicted heavier-at-creep cost CONFIRMED as felt.** FactorE stayed 0 below 12.7 °/s ⇒ **the micro regime was never armed** |
| flat FactorC | V80 | ✅ r66 | 🛑🛑🛑 *"the worst grinding this car has ever produced"* … **vehicle instability** |
| FactorC **and** FactorE together | V47 | ✅ | *"marginally quieter at 5 mph, no effect in motion"* — the only real simultaneous C/E test, and its "hit the live table" claim was **WITHDRAWN 2026-08-08** |
| K1 `0xC40D2` ×2 | V89 | ✅ | measured **FLAT**. ⚠ its own build note: *"may feel notchier/heavier on-centre — the instrument cannot see that"* |
| friction ×1.5 + `0xC407E`→850 | V73–V75 | ✅ | ☠ **both hard-faulted.** Creep-heaviness attributed here |
| `0xC407E` 850→511 + friction→stock | V81 | ✅ | ⚠ *"removes drag the operator is used to"* |
| `0xC61B8` pre-gain deadband = 102 | — | ❌ | **VIRGIN 85 builds** — eliminated as a hazard by structural argument, **not by edit** |
| `0xC61F6` r24 deadzone = 3 | — | ❌ | **VIRGIN** — **STRUCK**: a deadband is the DUAL of a relay; deleting it ADDS small-signal gain, the destabilising direction |
| `0xC6316` governor speed cal (~10 km/h) · `0xC6158` ceiling fallback | — | ❌ | **VIRGIN, never touched** |

---

## §4 — THE SEVEN SILENT REVERTS, AND `0x454FE`'s SIX LOSS/RESTORE CYCLES

**[EVIDENCE — machine-detected from the images, `HANDOFF-2026-08-12` cross-build matrix; the clustering
matches `STATE.md`'s own "seven silent reverts" list exactly.]**

The **V76 rebase-from-V38** silently reverted, because V38 predates them and nothing in
V76→V78→V79→V80 re-applied them:
1. `0x2A1F0` disp `0x7CD0` → `0x746C` — the V57 decouple, **undone**
2. `0xC6CD0` → inert (`0xFFFF`) — the private 4× forward gain, **lost**
3. `0xC646C` 891 → **3564** — the *shared* 4× sensor scale back in force
4. `0xC62EA` 0 → **320** — V53's low-speed steer lockout **restored** (steer-to-zero lost)
5. `0xC63A0` 2048 → 1024
6. `0x454FE` `B5` → **`BA`** — V42's fix **lost again**
7. 🛑 **the seventh, never logged anywhere until 2026-08-08:** `gain_A` rec0/rec1 —
   `0xC6A72`–`0xC6A78` and `0xC6A86`–`0xC6A8C` — went 512 → Honda's `3072/2434/2048` and
   `3072/2488/1536` on **V76/V78/V79/V80**.
⇒ **any V80-vs-V75 or V76-vs-V75 contrast carries FIVE silent confounds, not four.**

**Lever B was lost three separate times:** V69–V71b, V72–V76, and V87 (the deliberate V38 rebase).
**Restored at V88; frozen 7+ builds since.**

**`0x454FE` (V42's macro-ratchet fix) — six loss/restore cycles**, the worst being **V53 → V70, an
18-build stretch during which every "the ratchet is build-independent" measurement was taken.**
Restored at V80; carried V81/V83a/V84/V87→V96.

### 🛑 Is anything that once worked currently OFF the car? — the answer, checked against the record

| lever | measured result | on V96? |
|---|---|---|
| **Lever B** `0x3AA96`=`FB` + `0xC6446`=5244 | ✅ **the kit's only grinding fix** | ✅ **ON** (frozen since V88) |
| **`0x454FE`** `B5` | *"ratchet fixed"* at V42 — **but RE-ATTRIBUTED and MEASURED INERT** (`gp-0x67fa==4` reads 0/123,277 while driving) | ✅ ON — kept because it costs nothing, **not because it does anything** |
| **`0xC62EA`** = 0 | ✅ CONFIRMED WORKING on-car | ✅ ON |
| **V57 decouple** (`0x2A1F0`/`0xC6CD0`/`0xC646C`) | ✅ decouple confirmed | ✅ ON |
| **V38 foundation** (4× gain, gentle-EME, corridor, setpoint) | ✅ fault-free, measured | ✅ ON |
| **Lever A** `0x3AB76`/`0x3AC20` `sar` ×2 | ✅ **FIXED the grinding 8–42×** at V62 | 🛑 **OFF — frozen off for 27 builds.** Deliberately: it CAUSED grind #2 and is ungated (*"the whole car vibrates like a subwoofer"* in manual). **This is a deliberate trade, not a loss.** |
| **`0xC40BC`** = 6000 | duty win 7.21×, bands clean-null | 🛑 **OFF (600)** — deliberately: 6000 made **6–9 Hz 2.3× worse** |
| **V75's damper** (`k`=1.5798) | the **only build that ever eliminated the grinding** | 🛑 **OFF** — deliberately: V75 **hard-faulted** |

⇒ **Nothing that measured as a fix is currently off the car by accident.** The one that would be a
headline — Lever A — is off by an explicit, evidenced trade. **The V96 delta is fully attributed.**
⚠ **But the car right now is V94, not V96** (§7.3): V94 carries `0xCBE74` **cut 6×** and the operator
has stopped driving it. **That is the live headline, and it is a regression that is still installed.**

---

## §5 — DO-NOT-RE-PROPOSE (flashed result) and NEVER-TRIED (same neighbourhood)

### 5.1 DO-NOT-RE-PROPOSE — one line each, verdict word first

```
FALSIFIED / NULL (flown)
  0xC644A  1024->32 (V43), ->64 (V49)         NULL. lane later eliminated by V56. frozen 52 builds
  0xC6450  1024->32 (V46)                      NULL. moot - V56 deleted the lane. frozen 51 builds
  0xC6AFC/0xC6AFE  32768->0 (V56)              FALSIFIED *and* HARMFUL. !! scored 15-26 Hz, NEVER 6-9 Hz
  0xD2006  102->43 (V60)                       NULL. "It did not fix the vibration issue"
  0x3AB6C/0x3AC16 r24+r26 kill (V61)           WORSE, engaged AND manual. cutting this lane is CLOSED
  0xC6444  512->3072 (V71c)                    FALSIFIED, WORSE on every axis
  0xC6206  hands-off slew (V45)                FALSIFIED
  0xC5030/0xC521A/0xC5232 (V40/V41)            FALSIFIED (V41 = clean subtractive test)
  0xC40D4  573->286 (V86)                      FALSIFIED, WELL-POWERED => phase-lever search CLOSED
  0xC40D2  102->204 (V89)                      FLAT (0.947, inside placebo). left on deliberately
  0xC40BC  600->6000 (V85)                     duty win, but 6-9 Hz 2.3x WORSE. DO NOT restore 6000
  0xC9E9C[m26] flat FactorC (V80)              WORST GRINDING EVER + vehicle instability
  FactorE->Honda + gain_A->stock (V83a)        WORST BUILD IN THE MODERN LINEAGE for BOTH symptoms
  Lever B + damper->Honda (V84)                "None of these have been fully fixed in V84"
  0xCBE74 m26/m27 x1.5 (V91/V92)               DOSE NOT IN FORCE (0.99 vs 1.50). UNEXPLAINED
  0xCBE74 m24 x0.5 / m26,m27 x0.25 (V93/V94)   ABORTED ON-CAR. "not safe to drive". LOWERING IS CLOSED
  0xC640A/0xC640C x0.75 (V93/V94)              same flight, same abort. virgin before V93
BRICKED / FAULTED
  0xC6206+0xC6208 <- 0xFFFF (V40)              BRICKED. magnitude, not direction
  0xC407E  511->850 (V73-V75)                  V74 AND V75 BOTH HARD-FAULTED. RULE 11: this is the
                                               DTC-0x1d INTERLOCK. NEVER RAISE
  V48b biquad notch cave                       BRICKED (RAM collision + unmodelled resonator)
  V24 / V27 trampoline caves                   BRICKED (magnitude/type mismatch; lockstep ASYMMETRY)
INERT (edit was never in force - NOT a tested lever)
  gain_B mode-10 ladder (V69/70/72/73)         INERT-BY-MODE. car is TVCA4 = modes 24/26
  FactorC alone (V44), FactorC alone (V47 leg) INERT-BY-MODE
  0xC63A0  1024->2048 (V72-V76,V76g,V81)       INERT - no mechanism (x2 on a zero product). EXONERATED
                                               as the fault cause; the "do not double" directive stands
                                               with a KNOWN-WRONG rationale
  0x454FE  BA->B5 (V42)                        MEASURED INERT - the guarded state is unreachable driving
  0xC64B8  112->0xFF (V37)                     VERIFIED AND DEAD 2026-08-12: at mode 7 BOTH ARMS deliver
                                               0 everywhere the branch could fire => stock and V37 are
                                               bit-identical on this car. V37 REMOVED NOTHING
  gain_A rec0/rec1 lowered                     ENGAGED-INERT - Lever B's armed path OVERWRITES gain_A
                                               with [0xC6444]=512 at 0x3AB5E. FAILED on V84 and V85
MEASURED FIXES - do not trade away without saying so
  0x3AA96 + 0xC6446 (Lever B)                  the kit's ONLY grinding fix. NOT a ratcheting lever.
                                               CLEARED by the V94-session controls. frozen 7+ builds
  0x3AB76/0x3AC20 sar x2 (Lever A)             FIXED grinding 8-42x - and CAUSED grind #2. STRUCK
                                               (ungated: "the whole car vibrates like a subwoofer")
  0xC62EA 320->0                               CONFIRMED WORKING on-car
REJECTED ON REVIEW - never flashed, and must stay that way
  0xC61D6  0->14                               "Highest-risk lever; last/never." 11-round, 4-analyst
                                               review: ACTIVATES a dormant uncalibrated 2D map onto the
                                               live command. DO NOT PROPOSE
  0xC6424  29491->20000                        INERT while slew=0; coupled to 0xC61D6
  0xC6202                                      buys nothing (4762 > max cmd) and gp-0x4f64 is shadowed
                                               => fault 0x17, hard-fault-eligible
  0xC6194                                      DEAD calibration - its gain cal 0xC63CC = 0
  0xC4018/1C/20, 0xC4048/4C/50 (3-tap FIRs)    CLOSED ON ARITHMETIC - identity FIRs, 229x peak gain
  0xC6372 / 0xC636E                            DEAD BRANCH - result never consumed
  FactorD 0xC9DB4                              STRUCK - axis is ABSOLUTE angle, no 1/w selectivity
  13-point LERP 0xC6B66/0xC6B80                STRUCK - 88.6% of engaged driving is in its flat segment
  0xC61F6 -> 0                                 STRUCK - deleting a deadband ADDS small-signal gain
NEVER RAISE / NEVER TOUCH (virgin, and must stay so)
  0xC4080  K0                                  pure Coulomb relay, no |model| factor, unbounded index
  0xC63AE -> 0                                 LERP index ==0 => output == +-Y[0] = full-authority relay
  0xC6200 < Y[0]                               same hazard from the clamp side. 3/15 readers unidentified
  0xC616C                                      0 on stock and every build. a NEVER-RAISE cell
  role 7 in 0xC4124                            would activate a never-exercised mixer branch onto the
                                               live command (the 0xC61D6 hazard class verbatim)
  0xC61B2/0xC61B4, 0xC646C, 0xC6CD0            the 4x LKAS gain. FROZEN, and NOT the culprit.
                                               NEVER recommend lowering it (see the tension in 3.5)
```

### 5.2 NEVER-TRIED, in the crux's neighbourhood

Each is a genuine gap. **None is a recommendation** — several carry named hazards.

| cell / lever | what it is | why it is untried, and the hazard |
|---|---|---|
| `0xC63BE` | the return lane's own gain | virgin. **But the lane is gated off** ⇒ raising the gain multiplies zero |
| `0xC695C` X/Y | **the outer gate's SHAPE** — `X=[−397,−192,140,294,384]`, `Y=[0,2560,2560,717,0]` | 🛑 **the only cal that can un-deaden the return lane.** Widening `X[0]`/`X[4]` opens the gate. ⚠ **`Y[0]`/`Y[4]` are 0 by design** — raising either off zero is a **step at the window edge = a relay**, the V78/V79/V80 move recorded as *"worst grinding ever"*. **RULE 12 / GATE 2 COROLLARY applies in full** |
| `0xC618A` = 1024 | dwell ARM threshold **and** the snap CEILING — one cal, two roles | virgin. ⚠ **moving it moves BOTH** ⇒ not single-variable |
| `0xC627E` = 20 | dwell SNAP threshold | virgin. ⚠ **the rung that measures it is INDICTED** — resolve the map first |
| `0xC63C0`, `0xC6132`, `0xC6970` | return-lane companions | virgin, **0 grep hits anywhere** — not even characterised |
| `0xC63C2`, `0xC66CC` | the r26 sibling trapezoid and its scale | virgin |
| `0xC63F8` / `0xC63FC` = 33 / 328 | **the 10× L/R authority-ramp asymmetry** | ⭐ virgin on all 85+ images, **never once asked about**. See §3.6 |
| `0xE547C`/`0xE5404`/`0xE52FC`/`0xE5284` | **the authority collapse curve** | ⭐⭐ virgin on all 90 images, **he drives on its knee**. 🛑 targets the ~0.5–1 Hz SURGE, **not** 6–9 Hz. 🛑🛑 **MONOTONE-NON-INCREASING only** |
| `0xC520C` | the rate-adaptive governor table | last written at V39–V41; **V40 bricked on a neighbour**. Beside the DTC-0x1d lockstep monitor ⇒ full GATE 1+2 |
| `gp-0x6acc` positive-only zero-gate (`0x431d0`) | the one-sided, no-hysteresis hard relay on the whole base-assist leg | ⭐ **never probed, never edited.** A one-sided artefact matches "a wiggle" |
| `0xC63A2`/`A4`/`A6`/`A8`/`AA` | five of the six `FUN_00038148` lane weights | virgin on all 85 images. 🛑 **`0xC63A6` was TRACED AND STRUCK on 2026-08-12** — and the argument (`f'` unresolved) applies to **all five** |
| `0xC61DA`, `0xC64C8`, `0xC64C9`, `0xC6442`, `0xC407C`, `0xC61B8`, `0xC6316`, `0xC6158`, `0xC646E` | assorted virgins | `0xC64C8` **mode 1 deletes the entire aggregator contribution** — a large hammer, no mechanism proposed |
| `gain_A` rec2/rec3 (`0xC6A90`/`0xC6AA4`) · mode-26 `gain_B` `0xD7A88`/`0xD7AC4` | the ≥50 km/h r26 records; the *correct-mode* gain_B | virgin. ⭐ the mode-26 `gain_B` cells are **the ones V69/V70 should have written** — the mode-10 ladder was inert, so **the real r24 dose ladder has genuinely never been run** |

---

## §6 — WHAT WOULD BE GENUINELY NEW FOR V97, VERSUS A RE-RUN

**The honest framing first.** The record's own summary, from the V94 handoff:
> *"The last cell with a measured symptom fix is Lever B (`0xC6446` + `0x3AA96`), frozen 7 builds since
> V88. **Nothing since V88 has produced one.**"*
Eight builds — V89, V90, V91, V92, V93, V94, (V95 vacated), V96 — and the only on-car movements were a
**FLAT** (V89) and a **REGRESSION he stopped driving** (V94).

### 6.1 Genuinely NEW — no build has ever done this

| candidate | why it is new | what would make it work | hazard |
|---|---|---|---|
| **Open the return lane's outer gate** (`0xC695C` `X[0]`/`X[4]`) | 🛑 **the return lane has NEVER been edited by any build — not one cell in ten.** And it is now *measured dead*, so this is the first lever in the arc aimed at a lane proven to be contributing nothing | it is the only firmware term that could make the engaged return *faster*, which is half of the operator's crux verbatim | 🛑🛑 **`Y[0]`/`Y[4]` = 0 by design.** Widen `X` only. Raising `Y` off zero at the window edge is the V80 relay move. And the lane is `−sign(motor rate)` ⇒ **it is a rate BRAKE; opening it makes the return SLOWER, not faster.** ⚠ **That direction must be settled before anyone builds this** |
| **Probe the `gp-0x6acc` one-sided zero-gate** | never probed in 96 builds; a one-sided no-hysteresis relay on the *whole* base-assist leg is the best structural match to *"a wiggle"* | a cave rung on `gp-0x6acc > +8192` costs ~14 B inside the proven extent | probe-only ⇒ GATE 2 vacuous. **The right next instrument if the crux is the wiggle** |
| **Soften the authority-collapse curve, monotone-non-increasing** | ⭐⭐ **virgin on all 90 images**; the operator's measured median override torque is **2235 against a 2240 knot** | it targets the measured ~0.5–1 Hz surge with a quantified mechanism | 🛑 **NOT a 6–9 Hz lever** (refuted five ways). 🛑 **the operator has not said he feels the surge** — ask first. 🛑🛑 monotone-non-increasing ONLY |
| **`0xC63F8`/`0xC63FC` L/R symmetry** | virgin, 10× asymmetry, never asked about | one question to the operator settles whether it is worth anything | ask before building |
| **mode-26 `gain_B` (`0xD7A88`/`0xD7AC4`)** | ⭐ **the r24 dose ladder on the mode the car actually reads has never been run** — V69/V70/V72/V73 all wrote mode 10 | it is the *correct-mode* version of a ladder the kit thinks it ran | ⚠ it is still the **rate lane**, and Lever B already sits near its ceiling |

### 6.2 RE-RUNS, and what would have to be different

| candidate | which earlier lever it re-runs | what is different this time |
|---|---|---|
| **`0xCBE74` m26/m27 UP** (undo V94, go past V92's ×1.5) | V91/V92 ran ×1.5 and it **measured not in force**; V93/V94 ran it DOWN and the car became undriveable | 🛑 **the direction is now MEASURED for the first time in 13 builds** (+518/+565 ct of positive `Re(Z)`, two drives, ω-partialled). **But the ×1.5 dose measured 0.99 — the mechanism by which it fails to arrive is STILL UNEXPLAINED**, and ×1.5 is already ~94 % of the cell's range before int32 wraparound at 1.6005×. ⇒ **re-raising it is a re-run of a dose that has already been shown not to arrive.** Say that out loud before he drives it |
| **`0xC63AA` / `0xC63A8`** (Path-2 lane weights) | the same class as `0xC63A6`, **traced and struck 2026-08-12** | 🛑 **nothing is different.** The blocker is `f'`, the RAM-LERP's local slope — unresolved for all six lanes. **V96 was built to measure exactly this and it has not flown.** ⇒ **blocked** |
| **`0xC6446` bigger** | Lever B, flown 7× | 🛑 blocked by the ±8192 rail (2.5× at the hot end, 3× pins) **and** the elasticity failed its out-of-sample dose test |
| **base-assist damper** (FactorC/E) | 11–17 builds, V74–V86B | 🛑 **CLOSED ON ARITHMETIC** — the product is exactly zero on 100 % of the micro regime, and reaching 25 % authority requires the V80 relay move |
| **any notch / phase lever** | V43, V46, V48b, V52c, V86 | 🛑 **CLOSED** — V86's falsification was well-powered and this firmware has **no frequency-selective lever anywhere** |
| **lowering `0xC6CD0` toward stock** | the 4× LKAS gain, frozen since V38/V57 | ⚠ **§3.5's return-to-centre trace recommends it; the standing rule says NEVER lower it** (it scales EXCITATION, not loop gain, and the operator has driven all three values reporting no manual-feel change). **Unreconciled — operator's call** |

### 6.3 My reading of where V97 should sit [BELIEF, stated as one]

The crux is a **trajectory**, and the arc has never once instrumented a trajectory — every cave from
V53 to V94 put a *single cell's magnitude or sign* on the wire, and V96 is the first to put a *transfer*
on it. **The crux needs a third thing: a time-aligned capture of a return event.** Two of the three
mechanisms in §3.5 (the shaper's one-sided zero-gate; the governor ceiling collapsing with rate) would
each leave an unmistakable signature in a 100 Hz return-event capture, and **neither has ever been on
any wire.** A probe-only build costs nothing in GATE 2 and cannot regress the car — which matters,
because the last two builds cut on a mechanism story were both refuted after the flash.
🛑 **And V96 has not flown.** Cutting V97 as a fix before V96 answers `f'` repeats the exact pattern
(V93, V94) that put an aborted build on the car.

---

## §7 — ADJUDICATING THE STANDING V97 DECLARATION, AND FOUR UNRECONCILED CONTRADICTIONS

### 7.1 🛑🛑 THE V97 DECLARATION IS CONTRADICTED BY THE RECORD — `gp-0x6b4e` IS PROVEN IDENTICALLY ZERO

`docs/STATE.md` §A5 (and the identical text in `BUILD-LINEAGE.md`'s V95 row):
> *"`gp-0x6b4c`/`gp-0x6b4e` are the **disjoint partition sums of the same 11-slot request array
> `gp-0x62f8[]`** (split by the mode bytes at `0xC4124` = `00 00 05 00 05 05 00 00 00 05 00`),
> **±10240 each — 5× and 10× the other two lanes** — and `gp-0x6b4c` is **also** a direct unity-weight
> aggregator summand (`0x3AA3E`, both branches) so it reaches the motor by **both** paths.
> **Both gates are structurally always open** (producer clamps to exactly ±0x2800; the gate passes
> ±10240 inclusive) ⇒ **the V64-class null is excluded BY ARITHMETIC.**"*

Against it, **two independent traces one day earlier, plus a red-team confirmation**:
> `docs/HANDOFF-2026-08-11-v90-flew-and-the-lever-search-closed.md:478-483` —
> *"🛑 **`gp-0x6afe` ≡ `gp-0x6b4e` ≡ 0, ALWAYS, ON EVERY BUILD.** … `gp-0x3d8c` is a straight sum over
> all 11 mixer lanes of `gp-0x62c8[lane]`; the per-lane role dispatch (`0xC4124` =
> `[0,0,5,0,5,5,0,0,0,5,0]`) either writes an explicit **zero** or does not write at all, **role 7
> never appears on any build**, and the `.data` boot initialiser for `gp-0x62c8[0..10]` is **22 bytes,
> all zero**."*

> `docs/TRACE-2026-08-11-return-to-centre-gate.md` §3.3 — the same closure, derived independently by
> `fw-return`, with the `.data` read at flash offset `0x86DE8`, and the explicit role table:
> role 7 → `r10` (real) but **never appears in `0xC4124` on any build**; roles 6/4/3/2/1/0 → explicit
> `st.h r0` = **ZERO**; role 5 → **not written at all**, retains a boot value of zero.

> `docs/REDTEAM-2026-08-11-term0-verdict.md:362-364` — *"`gp-0x6b4e ≡ gp-0x6afe` **CONFIRMED
> (EVIDENCE)**"* (`FUN_00042ac6` does `gp-0x6afe = param_1`, no scaling).

**ADJUDICATION [EVIDENCE for the contradiction; I did not re-derive either trace]:**

1. **The declaration prices the wrong failure mode.** *"Both gates are structurally always open"* is a
   statement about **gate WIDTH**. The V64 class is **the signal never being non-zero**. A ±10240 gate
   held wide open on a cell that is identically 0 delivers exactly nothing. **This is the V64 null, not
   its exclusion.** [The gate-width claim itself is almost certainly correct and is corroborated by
   REDTEAM's six-lane table — it is simply not the binding constraint.]
2. **The array identifier disagrees.** §A5 says `gp-0x62f8[]`; both traces say `gp-0x62c8[]`. One is
   wrong, or they are different arrays and §A5's identification is unsourced. **48 bytes apart.**
3. **"Disjoint partition sums" is corroborated nowhere else.** Both traces describe `gp-0x6b4e` as the
   **FULL 11-lane sum** (`clamp(Σ gp-0x62c8[i], ±0x2800)`), not a partition of it. And if it *were* a
   partition split by role, the role-5 partition is the never-written one and the role-0 partition is
   the explicit-zero one — **both would be zero**, which contradicts `gp-0x6b4c` being live.
4. **The `gp-0x6b4c` half is blocked by the argument that struck `0xC63A6` one day earlier.** Per
   REDTEAM's read of the image, `0xC63A8` and `0xC63AA` are the weights on lanes 5 and 6 of
   `FUN_00038148`'s six-lane sum — the *same* sum whose output `gp-0x6b70` is a **PID reference that
   gets SUBTRACTED through a RAM-resident LERP of unknown local slope `f'`**. `STATE.md` §A6b killed
   `0xC63A6` on exactly that: *"A lever whose SIGN is unresolved is not a lever. That is exactly how
   V94 reached the car."* **That argument is indifferent to which of the six lanes you weight.**
   `gp-0x6b4c`'s escape is its **other** path — the direct unity-weight aggregator summand at
   `0x3AA3E` — but a `0xC63AA` **cal** edit reaches only the Path-2 half, the blocked one. Reaching the
   direct path requires a **code** edit at `0x3AA3E`, which is a different and never-tried class.
5. **All six weights are unity and virgin.** `0xC63A2`/`A4`/`A6`/`A8`/`AA` are **VIRGIN on all 85
   images**; only `0xC63A0` has any history, and that history is **INERT**.
6. **The only way to make `gp-0x6b4e` non-zero is to introduce role 7 into `0xC4124`** — a branch that
   has never appeared on any build, writing a stack-sourced value onto the live command. **That is the
   `0xC61D6` hazard class verbatim** (*"activates an uncalibrated map onto the live command"*).
   **Do not.**

⇒ **RECOMMENDATION:** the `gp-0x6b4e` half of the V97 declaration should be **withdrawn** unless the
image agent finds the two traces wrong; the `gp-0x6b4c` half should be **held until V96 flies and
returns `f'`** — and V96's own pre-registration is already partly VOID (`gp-0x374c` M pinned at 0 ⇒
S1/S2 void, `f'` NOT RESOLVED), so that hold is currently open-ended.

### 7.2 🛑 `0xCBE74`'s direction — the record says both things, one day apart

> `docs/HANDOFF-2026-08-11-routes-78-79-and-the-inertia-reversal.md` §7.5:
> *"**Do not re-raise `0xCBE74`** — it is an inertia term and cannot damp."*

> `docs/STATE.md` §A1 (2026-08-12): the delivered lane sits at **+137°/+139°** vs WHEEL rate at 6–9 Hz
> ⇒ **+518/+565 counts of POSITIVE `Re(Z)`. It is a REAL 6–9 Hz DAMPER and V94 removed 6/6ths of it.**

STATE supersedes — but **the handoff carries no supersession banner**, and an agent that reads only
that handoff (it is the second-most-recent) gets the reversed instruction. ⊕ Two successive *desk*
phase stories about this one lane were both wrong, four days apart; the rule the session drew is
**measure the delivered lane, do not do the arithmetic.**

### 7.3 🛑 V92's flash status — the tables say one thing, the prose says another

> `STATE.md` §A5 table: **"V92 | built, verified, never flashed — ⇐ THE REVERT CANDIDATE"**
> `STATE.md` §A5, three lines below: *"V92 **flew as route `79`** in the earlier lineage with identity
> proven single-frame; it is **the last configuration the operator drove and did not abort**."*
> `BUILD-LINEAGE.md` V92 row: *"✅ **CUT, VERIFIED, UNFLASHED** 2026-08-11."*

Route 79's V92 identity is **proven single-frame and parameter-free** (`0x14A` byte7[7:6] ≠ 0 on 16,236
frames; impossible on every build V53–V91). **The prose is right and both tables are stale.** This is
at least the **sixth** instance of the kit's own recorded *"the row still says UNFLASHED after it
flew"* defect (V83a, V84, V85, V86, V86B, V89 — now V92).

### 7.4 🛑 `gp-0x6bbe`'s identity — refuted in place, no banner on the handoff

> `HANDOFF-2026-08-11-routes-78-79…md` §3: *"`gp-0x6bbe` identified — it is the **base-assist output**
> … flat gain ≈ 90 ct/(rad/s), phase through zero at 5–6 Hz ⇒ **viscous**."*
> `STATE.md` §A4: *"**`gp-0x6bbe` is RATE-derived, NOT the base-assist output** — contradicting the
> previous headline. Dead as a lever."*

Same pattern as 7.2. **The handoffs are records and are correct as written for the day they were
written; nothing in them warns a reader that the headline was overturned the next day.** Two of the
three most recent handoffs now carry a superseded decision-bearing claim in their body text.

### 7.5 ⚠ One contradiction the record itself flags as OPEN, and I confirm is unresolved

`STATE.md` §A6b: the claimed inversion boundary at `0xC63A0` 1024→2048 (0.59/0.56 "damping" →
1.18/1.12 "INVERTED") *"should have produced a large qualitative change on-car, and `0xC63A0` = 2048
**flew four times** (V72, V73, V76g, V81) and measured **INERT**. Either the model is wrong, or 'inert'
was measured hands-off in the wrong regime, or Path 2 is small at the flown operating point (which
would contradict Q2). **Unreconciled.**"
⊕ **§A2's regime finding gives the second horn real weight**: every `Re(Z)` number ever produced used a
`steeringPressed` hands-off mask, which **excludes the symptom regime by construction**. The `0xC63A0`
"INERT" verdicts inherit that. **This is worth re-scoring before any Path-2 weight lever is proposed.**

---

## §8 — RESIDUALS AND THINGS I COULD NOT CLOSE FROM THE RECORD

1. **`docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md` stops at ~V81.** V83a → V96 have rows in
   `BUILD-LINEAGE.md`'s recent tables but **not** in the by-address lookup table that CLAUDE.md makes
   mandatory before proposing a cal edit. **An agent grepping Part 1 for `0xCBE74`, `0xC40D2`,
   `0xC40BC` or `0xC640A` by address will find nothing** — the exact failure mode the file exists to
   prevent. **Reported, not fixed** (outside my scope).
2. **`gp-0x6ac0`'s counts-per-°/s is not established anywhere.** It gates whether §3.5's governor
   mechanism is EVIDENCE or BELIEF, and it is the single most valuable open number in this
   neighbourhood.
3. **The hands-off coast is still owed** (routes 78/79 held 1.8 s and 0.0 s). If the 2–26 Hz
   anti-damping lives in the plant, no firmware lever removes it. ~15–20 min, no firmware needed.
   **This has been the #1 open item for two sessions and has not been run.**
4. **Two operator questions are outstanding and cheap:** (a) does he feel the ~0.5–1 Hz surge — a slow
   lurch or "catch" during override, distinct from the fast buzzing? (b) does the car feel different
   turning left versus right (`0xC63F8`=33 vs `0xC63FC`=328)? **Both bear directly on the crux.**
5. **`gp-0x6733` identity**, **task 5's true rate** (the 100 Hz claim is RETRACTED and nothing replaces
   it; `memory/accord-task5-is-100hz-damper-cannot-damp-21hz.md` carries a **DISPUTED — DO NOT SIZE A
   BUILD ON THIS FILE** banner), **the `gp-0x67fa == 4` record inconsistency**, and
   **`FUN_0003897a`/`gp-0x6350`/the LERP `X[0]`** all remain open.
6. **`0xC64DE` = 25627 since V22** — non-stock for 85 builds, label disputed since 2026-07-18, **never
   once isolated.** The longest-carried unmeasured cell in the image, and it sits in the
   re-engage/on-centre neighbourhood the crux lives in.
7. 🛑 **SUPERSEDED BY §9 — the record's "the car is V94" is WRONG. The car is V96.** This item read
   *"the car right now is V94, the aborted build"* when §1–§8 were written, because that is what
   `STATE.md` and `BUILD-LINEAGE.md` both say. **The team lead proved single-frame that V96 is on the
   car and routes `7e`/`7f` are its flight.** See §9 for the evidence and the corrective text. Every
   other statement in §1–§8 is unaffected — none of them turns on which of V94/V96 is installed —
   **except** §1's V96 row ("not flown") and §6.3's *"V96 has not flown"*, both of which are corrected
   in §9.4.

---

## §9 — CORRECTIVE TEXT: THE FLASH-STATUS ROWS FOR V96 AND V92

**Written 2026-08-12 at the team lead's request, to be applied by him at close-out. I did not edit
`docs/`.** This is the **seventh** instance of the kit's own recorded *"the row still says UNFLASHED
after it flew"* defect (V83a · V84 · V85 · V86 · V86B · V89 · V92 — and now V96), and the first one
with a **measured cost**: `fw-loop` closed its final verdict with *"fly V96, S2 measures the missing
factor, no flash needed"* when V96 had **already flown** and its regressor was sized **34× over-range**,
so **S1 and S2 are both VOID**. A stale flash-status row sent the session's best analyst to a
measurement that does not exist.

### 9.1 The identity evidence — write it into the rows so the next session cannot re-doubt it

**[EVIDENCE — team-lead measurement, routes `7e`/`7f`; I did not re-derive it. The structural
impossibility arguments below are from the record and I did verify those.]**

```
V96 IDENTITY, SINGLE-FRAME AND PARAMETER-FREE
  measured   0x14A byte7 bit6 == 1 on 100.0000 % of 164,096 frames  (routes 7e / 7f)

  vs V94 -- STRUCTURALLY IMPOSSIBLE, not merely improbable
     V94 carries the 74-byte V90 cave, which writes 0x14A BYTE 4 BITS 7:3 AND NOTHING ELSE.
     It cannot write byte 7 at all. Every build V53..V91 is excluded the same way: the only two
     writers of gp-0x1511 are 0x55C02 (andi 0xcf, the redundancy-voted counter at bits 5:4) and
     0x55C2A (andi 0xf0, the checksum nibble at bits 3:0) -- BOTH EXPLICITLY MASK BITS 7:6 OFF.
     Verified two ways in the record: a decompile of FUN_00055a98 plus an independent Python byte
     scan of the whole image for any st.b/st.h rX,-0x1511[gp] -> exactly those two hits.

  vs V92 -- NOW EVIDENCE, no longer BELIEF.  <-- THIS IS THE UPGRADE; RECORD IT
     V92 also writes byte 7, so the record correctly logged the V92/V96 separation as BELIEF at cut
     time (STATE.md A6: "Separation from V92 is BELIEF, not EVIDENCE ... the separator is its b6
     measuring duty 0.0000, which is a measured duty, not an impossibility").
     THE FLIGHT SETTLES IT. V92's byte7 b6 is `gp-0x6a82 > cal(0xC627E)=20` -- the DWELL-SNAP rung --
     and it measured duty 0.0000 ENGAGED **and** 0.0000 MANUAL over 87,317 frames on route 79, in
     3 runs, longest 855 s. V96's byte7 b6 is a HARD-WIRED CONSTANT 1 (the fingerprint bit).
     A 164,096-frame unbroken rail at 1 is a reading V92's rung has never produced ONE frame of.
     => 7e/7f are V96. The BELIEF caveat in STATE.md A6 is DISCHARGED and should be struck.
```

### 9.2 `docs/BUILD-LINEAGE.md` Part 4 — replace the "CURRENT" line at the head of the section

Part 4's current head line is dated **2026-08-07 (night)** and stops at V81. Insert this **above** it
and demote the existing one to the same "STALE BELOW THIS LINE" treatment Part 4 already uses:

> 🛑🛑 **CURRENT, 2026-08-12 (late) — THIS LINE IS THE ONE TO READ; EVERYTHING BELOW IT IS HISTORY.**
> **ON THE CAR: V96.** Flown as routes `7e` / `7f`, **fault-free**. Identity **proven single-frame and
> parameter-free**: `0x14A` **byte7 bit6 = 1 on 100.0000 % of 164,096 frames**. V94 carries the 74-byte
> V90 cave and **physically cannot write byte 7**; every build V53–V91 is excluded because
> `gp-0x1511`'s only two writers (`0x55C02` `andi 0xcf`, `0x55C2A` `andi 0xf0`) mask bits 7:6 off; and
> **V92 is excluded by the flight itself** — its byte7 b6 is the dwell-snap rung `gp-0x6a82 > 20`,
> which measured duty **0.0000 engaged and 0.0000 manual over 87,317 frames** on route `79`, so it has
> never produced a single frame of the 164,096-frame rail V96 shows.
> 🛑 **V94 IS NO LONGER ON THE CAR.** It flew as route `7d` and was **ABORTED by the operator**
> (*"made the stuttering and grinding worse, by a lot. So much so that it vibrated the entire car, and
> I decided it was not safe to drive"*); V96 was flashed after it. Any text in this file or in
> `docs/STATE.md` that says "V94 is on the car" is **stale as of 2026-08-12 and must not be relied on.**
> 🛑 **V96 IS AN INSTRUMENT BUILD, NOT A FIX** — zero calibration bytes; its calibration is V92's,
> byte for byte. **It has now flown, and its own pre-registration did not survive:** `gp-0x374c` M
> pinned at 0 and the regressor sized **34× over-range** ⇒ **S1 and S2 are BOTH VOID and `f′` is NOT
> RESOLVED.** **Do not plan a build that assumes `f′` is in hand, and do not re-fly V96 expecting S2 to
> answer — the rung must be re-sized first.**
> Flash order since V88: **V88 → V89 → V90 → (V91 unconfirmed, route `78`) → V92 (route `79`) →
> V94 (route `7d`, ☠ ABORTED) → V96 (routes `7e`/`7f`).**
> 🛑 `docs/STATE.md` remains the authority for what is on the car — **and it is being corrected in the
> same pass as this line.**

### 9.3 `docs/BUILD-LINEAGE.md` — the V96 and V92 row status cells

**V96 row (line ~51), final column — replace `**BUILT, VERIFIED, UNFLASHED** 2026-08-12.` with:**

> ✅ **FLASHED AND FLOWN — routes `7e` / `7f`, 2026-08-12, fault-free.** (This row read *"BUILT,
> VERIFIED, UNFLASHED"* until 2026-08-12 late — the **seventh** instance of this file's own
> *"row says UNFLASHED after it flew"* defect, and **the first with a measured cost**: an analyst
> closed a verdict with *"fly V96, S2 measures the missing factor"* against a build that had already
> flown.) **Identity single-frame and parameter-free: `0x14A` byte7 b6 = 1 on 100.0000 % of 164,096
> frames** — V94 cannot write byte 7 (74-byte V90 cave), V53–V91 cannot (both `gp-0x1511` writers mask
> bits 7:6), and **V92 is excluded by its own measured 0.0000 dwell-snap duty over 87,317 frames** ⇒
> **the "separation from V92 is BELIEF" caveat is DISCHARGED.** 166/166 assertions, reproduces
> bit-for-bit. image `876cf2be5800f0f8…` rwd `7e9a65f11cab4ffc…`. 🛑🛑 **THE PRE-REGISTRATION DID NOT
> SURVIVE THE FLIGHT: `gp-0x374c` M pinned at 0, regressor 34× over-range ⇒ S1 AND S2 ARE BOTH VOID,
> `f′` IS NOT RESOLVED.** The Path-2 weight class (`0xC63A2`/`A4`/`A6`/`A8`/`AA`) therefore **stays
> blocked**, and `0xC63A6`'s 2026-08-12 NO-GO stands unchanged. **Re-size the rung before re-flying it.**

**V92 row (line ~94), final column — replace `✅ **CUT, VERIFIED, UNFLASHED** 2026-08-11.` with:**

> ✅ **FLASHED AND FLOWN — route `79`, 2026-08-11, fault-free.** (This row read *"CUT, VERIFIED,
> UNFLASHED"* until 2026-08-12 — the **sixth** instance of this file's *"row says UNFLASHED after it
> flew"* defect.) **Identity PROVEN SINGLE-FRAME: `0x14A` byte7[7:6] ≠ 0 on 16,236 frames**, impossible
> on every build V53–V91. 198/198 assertions, reproduces bit-for-bit. image `c8e89fe35ebc445e…`
> rwd `388a1974d5702e17…`. ⊕ **It is the last configuration the operator drove and did not abort**, and
> was the standing revert candidate until V96 (which carries V92's calibration byte for byte) was
> flashed on 2026-08-12.

### 9.4 `docs/STATE.md` §A5 — the whole table and the paragraph under it

Replace the §A5 table and the "Revert candidate" paragraph with:

> ### A5. WHAT IS ON THE CAR, WHAT IS BUILT, AND THE REVERT CANDIDATE
>
> | build | status | image / rwd |
> |---|---|---|
> | **V96** | ✅ **ON THE CAR.** Flown routes `7e`/`7f` 2026-08-12, **fault-free**. Identity proven single-frame (below). **An INSTRUMENT, not a fix — zero cal bytes; its calibration IS V92's** | image `876cf2be5800f0f8…` rwd `7e9a65f11cab4ffc…` |
> | **V94** | 🛑 **FLEW route `7d` AND WAS ABORTED BY THE OPERATOR. NO LONGER ON THE CAR** — V96 was flashed after it | image `cd971c05d483fe9c…` rwd `3feccc09d8cbdd05…` |
> | **V93** | built, verified, **never flashed**; carries V94's cal without the packer rescale | image `779180f8aaf88f29…` rwd `9c93dca63e9e404e…` |
> | **V92** | ✅ **FLEW route `79` 2026-08-11, fault-free**, identity proven single-frame. ⊕ **V96 carries its calibration byte for byte**, so the revert it represented is already installed | image `c8e89fe35ebc445e…` rwd `388a1974d5702e17…` |
> | ~~V95~~ | 🛑🛑 **VACATED — A BURNED NUMBER. NEVER REUSE IT.** | see the DEAD hashes below |
>
> **🛑 IDENTITY, so this is never re-doubted:** `0x14A` **byte7 bit6 = 1 on 100.0000 % of 164,096
> frames** across routes `7e`/`7f`. **V94 cannot write byte 7** (it carries the 74-byte V90 cave, which
> writes byte 4 bits 7:3 and nothing else). **No build V53–V91 can** — `gp-0x1511`'s only two writers,
> `0x55C02` (`andi 0xcf`) and `0x55C2A` (`andi 0xf0`), explicitly mask bits 7:6 off, verified by
> decompile of `FUN_00055a98` **and** an independent whole-image Python byte scan. **V92 is excluded by
> the measurement itself**: its byte7 b6 is the dwell-snap rung `gp-0x6a82 > cal(0xC627E)=20`, measured
> at duty **0.0000 engaged and 0.0000 manual over 87,317 frames** on route `79` (3 runs, longest 855 s),
> so it cannot produce a 164,096-frame unbroken rail. ⇒ **§A6's "Separation from V92 is BELIEF, not
> EVIDENCE" caveat is DISCHARGED — strike it there too.**
>
> **🛑🛑 THERE IS NO REVERT PENDING.** V96 *is* the revert: its calibration is V92's byte for byte, so
> V94's `0xCBE74` cut is already off the car. The only remaining question is what V97 does, not what to
> roll back to. 🛑 Any flash is still gated on the operator naming the file and the bus.
>
> **🛑🛑 AND V96's PRE-REGISTRATION DID NOT SURVIVE ITS OWN FLIGHT.** `gp-0x374c` M pinned at **0**, the
> regressor sized **34× over-range** ⇒ **S1 and S2 are BOTH VOID; `f′` is NOT RESOLVED.** Per §A6's own
> rule — *"if S1's CI spans zero the answer is `f′` is NOT RESOLVED by this flight, NOT `f′` is zero,
> and the weight class stays blocked"* — **the Path-2 weight class remains blocked**, `0xC63A6`'s NO-GO
> stands, and **no build may be sized on `f′`.** ⚠ **Do not write "fly V96 and S2 will answer it"
> anywhere** — V96 has flown; the rung must be **re-sized** before that measurement exists.

**Also correct, in the same pass** (all currently say or imply V94 is installed):
- `STATE.md` **line 3**, the "Last updated" line — *"V94 flew and was ABORTED; … V96 cut as an
  instrument build"* → add *"and V96 has since FLOWN as routes `7e`/`7f`; **V96 is on the car**"*.
- `STATE.md` **lines 6–9**, the 🛑🛑 **"ON THE CAR: V94 — AND THE OPERATOR STOPPED DRIVING IT"** block —
  it must now read **"ON THE CAR: V96"**, with V94's abort kept as the reason V96 was flashed, and
  *"**It is still flashed**"* struck. **This is the single most-read line in the kit; it is the one
  that misled `fw-loop`.**
- `STATE.md` **§A6**, *"⚠ Separation from **V92** is **BELIEF, not EVIDENCE**"* → **DISCHARGED**, per
  §9.1 above.
- `STATE.md` **§A6**'s pre-registered **S1/S2** block → mark **VOID, measured**, not pending.
- **`memory/MEMORY.md`** — no memory currently asserts V94 is on the car, but a new one is warranted:
  *"V96 flew as routes `7e`/`7f` and is on the car; S1/S2 void; `f′` unresolved; the Path-2 weight class
  stays blocked."* ⊕ and the flash-status defect itself now has **seven** instances and a **measured
  cost**, which is memory-worthy in its own right as a `feedback_*` fact.

### 9.5 The structural fix for the recurring defect

The kit's existing rule — *"write the flight result in the SAME pass that scores the flight"* — was
authored after the fifth instance and has now been violated twice more. It fails because it depends on
whoever scores the flight remembering to touch two other files. **A rule that only fires if someone
remembers is not a control.** The cheap control that would have caught all seven:

> **At close-out, `grep -n "ON THE CAR\|UNFLASHED\|never flashed" docs/STATE.md docs/BUILD-LINEAGE.md`
> and reconcile every hit against the identity bit measured on the most recent route.** One command,
> mechanical, and it fails loudly rather than silently.

---

## §10 — DEFECT I: THE PART-1 INDEX IS FIFTEEN BUILDS BEHIND

**One-line framing, as requested:**

> **`docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md` stops at ~V81, so V83a→V96 — fifteen builds, including
> every cell the last four sessions actually moved (`0xCBE74`, `0xC40D2`, `0xC40BC`, `0xC40D4`,
> `0xC640A`/`0xC640C`, `0xC63A6`) — return NOTHING to the by-address grep that `CLAUDE.md` makes
> mandatory before proposing any calibration edit, which is precisely the failure the file was created
> to prevent.**

**The fix is APPEND, not regenerate** — the rows are hand-written narrative with on-car results and
operator quotes in them, so there is nothing to regenerate *from*; the fifteen rows already exist in
`BUILD-LINEAGE.md`'s recent tables and only need moving into the by-address index in the same shape.
🛑 **But appending alone will not hold** — this file was already backfilled once (V76–V81, on
2026-08-07, whose own note reads *"this file had been five builds behind, which is precisely the gap it
exists to prevent"*) and it fell behind again by ten more. **Make the row-write a close-out gate in
`CLAUDE.md`'s four-part deliverable**, alongside `STATE.md` and the golden model: *a build is not
closed out until its address rows are in Part 1.* Without that, the next backfill is due at ~V110.
