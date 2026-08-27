---
name: project-accord-torque-mod-v0
description: "✅ 2026-07-02 (LATEST) V33 BUILT = DISABLE the GENTLE-EME torque disengage — a mechanism DISTINCT from the soft-EME/corridor lineage below. Gentle EME = LKAS-only cut (STEER_STATUS=no_torque_alert_2, no DTC) in the engage-SM decider FUN_00040d58 when sensor-A column-torque voter gp-0x6a62 ≥ cal 0xC6312 (stock 320); root-caused in the V32 handoffs. Operator judged its trigger always-unsafe for hands-off LKAS → V33 = builds/v18_v49/build_v33_tva.py = V31 + raise 0xC6312 320→65535 (u16 datatype MAX; the gate is ld.hu/unsigned & gp-0x6a62 is voter-clamped to 32000, so gp-0x6a62<threshold is unconditionally true → torque disengage NEVER fires; the separate gp-0x6a62==0xffff invalid-sensor sentinel is KEPT). Cal-only, decider code byte-identical to stock, 49/49 CRC, V33-vs-V32 delta = ONLY the 2-byte threshold + its 0xC6000-block CRC, UNFLASHED. Handoff docs/handoffs/2026-07/HANDOFF-2026-07-02-v33.md. Verified radare2 v850.gnu (⚠ r2's DEFAULT v850 plugin MIS-DECODES V850E2 — use v850.gnu): 0xC6312 has exactly 3 readers (cal reads at 0x40db8/0x40dd0/0x40df4, NOT 0x40dae/dc6/dea = the gp-0x6a62 VALUE reads — base reg r5=tp vs r4=gp decoded from raw bytes), 0 writers, no absolute/indexed access, no twin; also fixed that address typo in the sensorA handoff + build_v32 docstring + engage-SM memory. V32 (0xC6312 320→1280) = partial-raise predecessor. --- ✅ 2026-06-03 V31 BUILT (V30 + matched FLAT BOOST FLOOR 4096 — fixes V30's residual soft EME on a hard sustained HANDS-OFF turn; the soft-EME bound is a gated 3-way max/min and V30's corridor is the DRIVER-OVERRIDE arm gated OFF hands-off [|gp-0x6bf0|≤9216] AND when authority≠0, so boost — the authority-gated arm, ON at authority≈0 — is the correct floor; self-stable fixpoint, builds/v18_v49/build_v31_tva.py 49/49 CRC 0 code edits, UNFLASHED, see [[reference-accord-soft-eme-bound-arm-gating]]). V30 FLASHED→drove well but one residual soft EME on a hard sustained turn. V30 BUILT (corridor ×4 = holds LKAS+COMP) + V29 BUILT (corridor ×2 = holds 2× LKAS) — both build_vNN_tva.py, cal-only, 49/49 CRC, byte-verified 0 code edits, UNFLASHED. V30 = V29 with the corridor at 4096/float 4.0 (int 0xC674E + matched float mirror 0xC6598/0xC65AC) to ALSO contain the post-governor COMP_TORQUE (driver-override comp added in FUN_000456a4, ceiling 2560) on top of governed_LKAS(≤1024): worst-case |gp-0x6acc|=1024+2560=3584 < 4096. ⚠ TRADE: 4096≥3584 means the integrator gp-0x3570 never winds up in any regime → the corridor/SM soft-EME cutback is functionally inert (holds 2× even under driver override — the 'fights the driver' regime); hard-EME lockstep intact. Comp magnitude UNCERTAIN (ceiling 2560 but realized=(gp-0x6ac0−LERP1)×3072>>10 may be far smaller; right-size via gp-0x6ac0 trace). Handoff docs/handoffs/2026-06/HANDOFF-2026-06-03-v30.md. --- WALL-ARM IDENTITIES (re-traced this session, two mislabels fixed): the int wall is a THREE-WAY MAX gp-0x6af6 = max(dir_corridor[cal 0x774e velocity-flat ±1024], velocity/cmd-envelope IIR[gp-0x3574 — NOT driver torque (that's gp-0x69ca); input gp-0x4f60 CONTESTED velocity-vs-LKAS-command, range cap 0x3000=12288 typ 512-2048], boost[cal 0x7760 = steering ANGULAR-RATE LERP, input gp-0x6ac2 ∈[0,13000], out 0-2048]) × polarity; both monitors compare FLOAT twins gp-0x6db0/gp-0x6db8 ×1024 vs INT walls gp-0x6af6/gp-0x6b00 ±5 LSB → ≥128.0 → 0x3f1b DTC 0xF00049. V29 = the same lockstep at corridor ×2 (2048). ⚠ Fixed TWO prior address errors: the FLOAT corridor mirror Y = 0xC6598/0xC659C(dir1,+1.0)/0xC65AC/0xC65B0(dir2,−1.0), NOT 0xC6590/0xC65A4 (those are X breakpoints — the V28-handoff's V29 proposal was a V26-class wrong-table mistake); and 0xC6664 = ENVELOPE LERP_B (feeds gp-0x6da8/envelope monitor gp-0x6c84, V26's rest-fault), NOT the corridor. Traced r11=LERP(0xC6590)/r7=LERP(0xC65A4) feed ONLY the float twin's corridor arm. V29 = V18 GAIN/clamps/ramp (real 2×, GAIN 0xC646C monitor-INDEPENDENT, flashed+validated) + INT corridor ×2 (0xC674E/50/5A/5C) + FLOAT corridor mirror ×2 (0xC6598/9C/AC/B0) + PN; NO trampoline/tolerance/0xC6664. Holds where V25/26/27 faulted: doubles ONLY the matched corridor arm on BOTH sides → IIR/boost arms + the stock ±5/1024 residual UNTOUCHED (V27 doubled the whole twin → 2× residual → fault). 27B/16 runs, byte-diffed vs stock + re-decoded .rwd from scratch. Conf ~85%; road-test arbiter; if the soft EME is the driver-override PLAUSIBILITY dropout ([[reference-accord-driver-override-plausibility-eme]]) not corridor overflow, the corridor widen won't fix it (but V29 still delivers safe 2× & must not hard-fault). Output ../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V29-LKAS-2x-corridor2x-floatmirror-PNfix-…rwd + _v29_plain_image.bin. Live model [[reference-accord-corridor-lockstep]]; handoff docs/handoffs/2026-06/HANDOFF-2026-06-03-v29.md. --- (V28, ANALYSIS-FALSIFIED) the V28 disasm trace (0x43040-0x43172) claimed gp-0x6af6 = max(driver-column-torque IIR gp-0x3574, corridor LERP r23 [cal 0x774e]) via cmovgt r11,r23,r10 @0x4313c — but the full decompile shows r23 is the BOOST arm (cal 0x7760) and the corridor is a SEPARATE third arm; V28's proposal to double float 0xC6590/0xC65A4 was wrong (X breakpoints). V28 (trampoline doubles the WHOLE float twin + tolerance widen) is LIKELY BROKEN, DO NOT FLASH: turning → demand-dominated → float twin=2×torque vs int wall=torque → divergence ≈ FULL torque → ±10/1024 tolerance can't cover → faults like V27. Live model: [[reference-accord-corridor-lockstep]]; handoff docs/handoffs/2026-06/HANDOFF-2026-06-03-v28.md (correction banner). --- (V28 as-built, FALSIFIED) V28 BUILT (builds/v18_v49/build_v28_tva.py) — after V27 FLASHED→HARD-FAULTED the instant the wheel was turned (wheel un-turnable). V27 root cause (decomp+algebra): doubling BOTH float twin (trampoline) AND int wall (cal) reaches exactly 2× and the primary corridor tables match, BUT the watchdog twin is polarity×max(corridor, SECONDARY tables 0xC65B8 Y→2.0); the secondary's stock residual ≤5/1024 DOUBLES under 2× → divergence_V27=2×stock≤10/1024 > ±5/1024 monitor window → 0x3f1b hard shutdown when turning. No symmetric doubling avoids it (the residual doubles). V28 = V27 + PROPORTIONAL 2× widen of BOTH corridor monitors: Monitor2 watchdog movhi r7/r14/r16 5/1024→10/1024 (0x3ba0/0xbba0→0x3c20/0xbc20 @0x44640/0x44648/0x4466C); Monitor1 shaper addi 0x5→0xf + cmp 0xb→0x1e @0x43190/96+0x431B4/B6 (±5→±15 LSB). Provably sufficient (stock≤5/1024⇒V27≤10/1024⇒passes; real faults ~1024 LSB caught — recalibration not blinding). Only dir1/dir2 corridor checks widened; integrator(wt4)/torque(wt32) track. Negatives are SEPARATE movhi per check (byte-scan, not search_instructions); non-corridor negatives 0x4478C/0x448E6 LEFT STOCK. 49/49 CRC, cipher round-trips, all readbacks pass, 46B/22 runs, UNFLASHED. Live model: [[reference-accord-corridor-lockstep]]; handoff docs/handoffs/2026-06/HANDOFF-2026-06-03-v28.md. --- (V27, prior, FLASHED→FAULTED) V27 BUILT (builds/v18_v49/build_v27_tva.py) — the CORRECTED corridor-lockstep fix after V26 FLASHED→HARD-FAULTED immediately at rest (wheel un-turnable). V26 doubled cal 0xC6664 to 'match the float corridor twin' but 0xC6664 is LERP_B (a velocity ENVELOPE multiplier), NOT the twin — at rest lerp_a=2.0 so doubling it added a constant +2.0 envelope offset → watchdog desync from t=0 → DTC 0xF00049 + latched motor-off. V27 = V18 GAIN + INT corridor ×2 (0xC674E/0xC6750/0xC675A/0xC675C ±1024→±2048) + a CODE TRAMPOLINE at the free 0xC4E00 cave that doubles the REAL float twins lp/r20 (RAM gp-0x6db0/gp-0x6db8, computed in FUN_00043e44 as corridor_mag×polarity) so BOTH lockstep monitors (FUN_00042af8 @0x43172 + FUN_00043e44 @0x4463a/0x44662) track the widened corridor and stay live. 36 bytes/15 runs, 49/49 CRC, built image Ghidra-verified (trampoline+cave decode correctly), 0xC6664 left STOCK, UNFLASHED. Live model: [[reference-accord-corridor-lockstep]]. ⚠ analyze STOCK code.bin (the /master.bin program, 2113 fns) — NEVER _v22/_v23/_v24 (experimental code edits). (prior) V25 FLASHED → HARD-FAULTED at full lock (DTC 0xF00049) → V26 BUILT→FLASHED→FAULTED (builds/v18_v49/build_v26_tva.py). Root cause: the DIRECTION CORRIDOR IS LOCKSTEP-MONITORED (int walls gp-0x6af6/gp-0x6b00 from cal 0xC674E/0xC675A ↔ float twin from a velocity-LERP cal 0xC6664); V25 doubled only the integer side → 1024-LSB monitor desync → DTC. V26 = V25 + the FLOAT corridor twin ×2 (0xC6664 seven f32 1.0→2.0) → 1024×2.0=2048=wall → exact 0 → lockstep restored; one float edit fixes dir1/dir2/integrator (all = same flat magnitude × direction sign, direction-gated). 33 bytes/19 runs, 49/49 CRC, zero code edits, UNFLASHED. SM2/SM3 threshold raises are NOT the lever (V19/V20 empirically failed). Live model: [[reference-accord-corridor-lockstep]]. (prior) V25 CLEAN BUILT (builds/v18_v49/build_v25_tva.py) = V18 GAIN + DIRECTION CORRIDOR ×2 (dir1 Y 0xC674E/0xC6750 +1024→+2048, dir2 Y 0xC675A/0xC675C −1024→−2048); the entire integer-envelope (shl) / consistency-monitor thread DROPPED. CORRECTED causal model (instruction-verified): the IIR envelope (gp-0x3574→gp-0x6af6) is a WATCHDOG REFERENCE only — gates NEITHER delivered torque (gp-0x6b98 = clamp(min(lanes, governor), ±0x2000); envelope absent) NOR the EME; the V19–V24 hard fault (DTC 0xF00049) was a SELF-INFLICTED consistency-monitor desync from doubling it; the soft EME (no DTC) is the command exiting the DIRECTION CORRIDOR tp+0x7748/0x7754 → integrator gp-0x3570 → SM2/SM3. So V25 = GAIN (real 2×) + corridor ×2 (soft-EME headroom). 19 bytes/12 runs, 49/49 CRC, NO code edits, UNFLASHED. Full model: [[reference-accord-corridor-vs-envelope]]. (prior) 🔬 2026-05-30: V19 BUILT (builds/v18_v49/build_v19_tva.py) = V18 + SM2/SM3 override-gate PROPORTIONAL RESCALE (0xC6422 16384→32768 + 0xC61DC 30720→61440) for HIGH-END 2× that survives hard driver-override without the EME snap; 49/49 CRC, ECU-decode==patched, 17-byte diff, UNFLASHED (operator road-tests next). Trace A pinned ALL 3 SM arming thresholds (SM1 0xC61DE=2048, SM2 0xC6422=16384, SM3 0xC61DC=30720, all COMMAND-driven via integrator gp-0x3570); SM1 left stock (velocity+opposition-gated, not the 2×-only culprit). The rescale preserves each monitor's RELATIVE trip point at 2× (loosen-proportionally, not defeat); operator signed off on the trade. Residual: command full-scale ambiguity → SM3 edit may be inert if full-scale≈8192; CAN 0x427 capture is the recommended pre-flash discriminator. Full mechanism: [[reference-accord-override-snap-state-machines]]. (Prior:) ✅ CURRENT 2026-05-27: V18 (2× gain/clamps + EME ramp-only 0xC64DE 17→27, calibration-only, NO code patch / NO trampoline) is FLASHED + road-validated — drives well. A 4-analyst Ghidra review (../assessment/) REJECTED V16 (slew 0→14 activates a dormant 2D shaping lane, not a damper) and found V17 deadband-only INERT (slew=0 pins gp-0x356c at 0); the real EME cut is the override-SM node gp-0x6960, and the ramp lever LENGTHENS the re-engage (was mislabeled 'faster'). No output rate-limiter exists as cal; the trampoline output-limiter was scoped but never built. ⚠ EME FOUND 2026-05-26 (late): the 2x build (V14/V15A/V15B) has a recurring driver-override / column-torque-sensor PLAUSIBILITY DROPOUT on sharp LOW-SPEED turns — driver adds hand torque, LKAS abruptly zeroes (wheel snaps straight), steering degrades ~10s, recovers. Mechanism Ghidra-verified: the 2x arb-output gain amplifies a pre-existing driver-override inhibition. SUPERSEDES the 'WORKS, saga closed' optimism (2x DOES deliver torque, but with this hazard). Full record + addresses + mitigation: [[reference-accord-driver-override-plausibility-eme]]. SAFE mitigation = reduce gain 0xC646C 1782→~1300; DO NOT widen the torque-sensor plausibility threshold (real fault detector). (Prior:) ✅ RESOLVED 2026-05-26: V14 FLASHED + ROAD-TESTED — IT WORKS (perceptible ~2x LKAS torque at the wheel). Confirms the arb OUTPUT GAIN tp+0x746c=0xC646C=891 + the ±512 clamps tp+0x71b2/b4 were the real LKAS magnitude binder; the LKAS path is REQUEST-LIMITED well below the 4762 governor, so V14's gain×2+clamp×2 reaches the motor uncut and the governor never bound (Case A confirmed). V15/governor 0xC6202 edit NOT needed for 2x. Closes the open gp-0x6b94 magnitude question affirmatively and the whole V11/V12/V13 'no high-end change' saga. ⚠⚠ CURRENT 2026-05-26(late): the arb output is NOT a monitor dead-end — the LKAS arb torque REACHES the motor (gp-0x6b4c->gp-0x6b94->gp-0x6ace->gp-0x6acc->shaper->gp-0x6b98->FOC, xref-verified), so V14's arb-source edits ARE on a live path (NOT inert). V14 BUILT (build_v14_tva.py, 49/49 CRC, unflashed). Dominant high-end binder on the COMBINED command = runtime governor gp-0x4f64 = cal const tp+0x7202=0xC6202=4762 (NOT 8192). Two levers: V14 arb-source scaling (LKAS share) + governor 0xC6202 (combined ceiling); a perceptible 2x may need both. See [[reference-accord-lkas-delivery-and-governor]]. (Prior 2026-05-26 eve:) tp(app)=0xBF000 NOT 0xF8000 — the LKAS high-end binder is the arb OUTPUT GAIN tp+0x746c=0xC646C=891; 2x recipe = gain 891->1782 + clamps tp+0x71b2/b4=0xC61B2/B4 512->1024 (flashable .rwd cal, no code rewrite). The entire absent-partition / V11-V13 / gain=-1 / gp-0x6b98-carrier arc is RETRACTED (wrong tp base). See CORRECTION block at top of body. (Prior desc:) Accord TVA torque-mod for the 2020 Accord (39990-TVA-A160). V0 plan drafted 2026-05-25 (analysis-2020accord/TORQUE_MOD_V0.md); SUPERSEDED IN PART by V11 build same day. Goal: more LKAS assist torque at full-scale comma command via static edits. Stock full-scale delivered ~8192 (0x2000). HARD STATIC-EDIT CEILING is ~2.0x (16383/0x3FFF), NOT the 3.99x the V0 plan claimed — both the gate FUN_00042ac6 AND the shaper input-check (0x43ae8, V0 plan MISSED it) cap their window at ±0x3FFF (imm16). 2.5x and 3x are NOT value edits (code rewrite). V11A (~2x) BUILT + CRC-validated, unflashed. See [[reference-accord-lkas-window-ceiling]]."
metadata:
  node_type: memory
  type: project
---

> ## 2026-07-19 CURRENT STATE - V38 FLASHED CLEAN; REVISED V39 BUILT, VERIFIED, UNFLASHED
>
> This banner supersedes the historical "LATEST V33" header below. V38's 4x build is on-car and has no
> dashboard/DTC errors. Remaining feedback separates into a several-Hz hard-turn ratchet and a common
> tens-of-Hz vibration under high LKAS torque while the wheel moves, at low and high road speed. Strong
> driver torque moves the wheel quickly without either symptom, contradicting an intrinsic moving-motor
> limit. The revised V39 zeros direct derivative lane `r24` for both signs when `|LKAS|>=417` (the lower
> exact V9 full-scale magnitude; V9 is +417/-418 after Q15 rounding) and voted
> driver torque `<320`; adaptive `r26` and the complete governor stay live. Exact V38 baseline, 52-byte
> diff including CRC, 49/49 blocks, independently Ghidra-decoded. See
> `docs/handoffs/2026-07/HANDOFF-2026-07-19-v39-direct-torque-rate-guard.md`. The live golden mechanism model is
> `analysis-2020accord/model/eps_lkas_chain_model.py` and must be updated as findings are validated.

> ## ✅ 2026-07-02 (LATEST) — GENTLE-EME torque disengage DISABLED → V33 BUILT (0xC6312 → u16 max). UNFLASHED. Handoff: docs/handoffs/2026-07/HANDOFF-2026-07-02-v33.md.
>
> **Distinct failure from the soft EME below.** The **gentle EME** (LKAS-only cut, `STEER_STATUS=no_torque_alert_2`,
> no DTC) is the **engage-SM decider `FUN_00040d58`** disengaging when the sensor-A column-torque voter
> `gp-0x6a62 ≥ cal 0xC6312` (stock 320, no debounce) — root-caused across the V32 handoffs
> (`handoffs/2026-06/HANDOFF-2026-06-29-gentle-eme-v32.md`, `handoffs/2026-06/HANDOFF-2026-06-30-sensorA-identity-gate-scale.md`). It is NOT the
> soft-EME SM2/SM3 / corridor mechanism (that cuts the *merged* command and was addressed by V31's boost floor).
>
> **The operator judged the gentle-EME trigger always-unsafe for hands-off LKAS control and directed disabling
> it. V33 = `builds/v18_v49/build_v33_tva.py` = V31 (unchanged) + raise `0xC6312` from 320 → `0xFFFF` (65535 = the u16 datatype
> maximum).** The gate is `ld.hu` (unsigned 16-bit) compared unsigned (`bnl`); `gp-0x6a62` is voter-clamped to
> 32000, so at 65535 the stay-engaged condition (`gp-0x6a62 < threshold`) is unconditionally true → **the
> torque-magnitude disengage can never fire.** The separate `gp-0x6a62 == 0xffff` invalid-sensor sentinel
> (a torque-SENSOR-FAULT path) is **left intact**.
> - **Build/verify:** 49/49 CRC PASS, ECU-decode==patched, all readbacks pass. **Cal-only:** the decider code
>   region `0x40d58–0x40e78` is **byte-identical to stock** (0 code bytes). 33-byte diff / 23 runs. **V33 vs V32
>   delta = exactly 6 bytes** (the 2-byte threshold `0005`→`ffff` + its 4-byte 0xC6000-block CRC). Output
>   `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V33-…-gentleEME-OFF-thresh65535-PNfix-…rwd` + `../accord-firmware/analysis-2020accord/_v33_plain_image.bin`.
>   **UNFLASHED (iron rule).**
> - **⚠ SAFETY TRADE (operator's call):** the driver can no longer wrest LKAS authority via column torque through
>   this sensor-A gate (openpilot brake/cancel/steering-override, upstream of the EPS, still disengage). Hard-EME
>   (DTC 0xF00049) lockstep + the invalid-sensor sentinel are intact.
> - **Tooling / verification:** radare2 `v850.gnu` (⚠ r2's *default* `v850` plugin MIS-DECODES V850E2 — use
>   `v850.gnu`). Whole-image enumeration confirmed `0xC6312` = exactly **3 readers** (cal reads `ld.hu 0x7312[r5=tp]`
>   at `0x40db8/0x40dd0/0x40df4`; the `gp-0x6a62` VALUE reads `ld.hu -0x6a62[r4=gp]` are the neighboring
>   `0x40dae/dc6/dea`), **0 writers, no absolute/indexed access, no int/float twin, no consistency monitor.**
>   Fixed the swapped reader-address labels in `handoffs/2026-06/HANDOFF-2026-06-30-sensorA-identity-gate-scale.md`,
>   `builds/v18_v49/build_v32_tva.py`, and the engage-SM agent memory. Full gentle-EME model:
>   [[reference-accord-lkas-engage-sm-disengage-trigger]] (agent memory). V32 (320→1280) = the partial-raise step.
>
> ## ✅ 2026-06-03 — V30 FLASHED→drove well but residual soft EME on ONE hard sustained hands-off turn → V31 BUILT (boost floor). UNFLASHED. Handoff: docs/handoffs/2026-06/HANDOFF-2026-06-03-v31.md.
>
> **V30 was flashed and drives well** — far better than V18, no hard EME, and every turn that used to soft-EME
> stopped — **except one very hard SUSTAINED turn that LKAS held hands-off**, which still soft-EME'd. Debugged
> by walking `FUN_00042af8` on STOCK `code.bin` myself: the soft-EME integrator `gp-0x3570` bound is the SAME
> gated 3-way max/min as the lockstep wall — `MAX/MIN(corridor, IIR gp-0x3574, boost)` — NOT corridor-alone (the
> V30 build comment's premise was wrong). **The corridor is the DRIVER-OVERRIDE arm**: gated OFF when
> `|gp-0x6bf0 driver-assist| ≤ 9216` (cal `0xC6156`, i.e. hands-off) AND when authority `r13 ≠ 0`. On a hands-off
> held turn the corridor is OFF, boost ≈ 0 (wheel not rotating → angular rate ≈ 0), IIR decaying (column
> velocity ≈ 0) → bound collapses → the 2× command (~1024) winds up the integrator → SM2/SM3 cut. **V30 widened
> the one arm that's gated off in exactly that regime.** (This also resolves the contested IIR input identity →
> column velocity.) Full gating model + the verified `r13 = gp-0x6966 = authority` chain:
> [[reference-accord-soft-eme-bound-arm-gating]].
>
> **V31 = `builds/v18_v49/build_v31_tva.py`** = V30 (unchanged) **+ a matched FLAT BOOST FLOOR 4096** (int `0xC6768`/`0xC676A`/
> `0xC676C` 0/1536/2048→4096; float mirror `0xC65C4`/`0xC65C8`/`0xC65CC` 0.0/1.5/2.0→4.0, exact ÷1024). Boost is
> gated only by AUTHORITY (not driver-assist/pos), so at the initiation instant (authority ≈ 0) it is ON and
> floored to 4096 → bound ≥ 4096 > worst-case command 3584 → integrator can't wind up → authority never climbs →
> the boost-zeroing SM (`gp-0x3562`, latches at authority > `0xC641E`=16384 for ~20 cyc) never fires → **self-
> stable fixpoint**; the runaway/both-off state is unreachable from normal operation. The corridor (V30) couldn't
> do this — it's driver-assist-gated, gone at the hands-off instant; boost is authority-gated, present there.
> Lockstep-safe: the float twin (`FUN_00043e44`) is a 3-way max/min that INCLUDES boost (float Y = int Y ÷1024),
> so the matched edit keeps the int↔float monitor at delta 0, incl. at rest (verified). **Build:** 49/49 CRC,
> ECU-decode==patched, 31-byte diff / 22 runs, **0 executable code edits** (independent file-level byte-diff),
> LERP_B `0xC6664`/speed-gain/boost-X all stock, cave `0xFF`. Output
> `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V31-LKAS-2x-corridor4x-boostfloor4096-floatmirror-PNfix-…rwd` +
> `../accord-firmware/analysis-2020accord/_v31_plain_image.bin`. **UNFLASHED (iron rule).** Residual: 4096−3584=512 margin rests on COMP ceiling 2560
> (cal `0xC67D8`); raise the floor or trace `gp-0x6ac0` if a larger realized COMP is suspected.
>
> ## ✅ 2026-06-03 — V30 BUILT: corridor ×4 (holds LKAS + COMP_TORQUE). FLASHED→drove well (see V31 above). Handoff: docs/handoffs/2026-06/HANDOFF-2026-06-03-v30.md.
>
> V30 = `builds/v18_v49/build_v30_tva.py` = V29 with the direction corridor at **4096 / float 4.0** (int `0xC674E`/`0xC6750`/
> `0xC675A`/`0xC675C` ±1024→±4096 + matched float mirror `0xC6598`/`0xC659C`/`0xC65AC`/`0xC65B0` ±1.0→±4.0).
> Operator-directed: size the corridor to ALSO contain the post-governor **COMP_TORQUE** (not just the 2× LKAS).
> - **Why 4096:** the shaper compares `gp-0x6acc = governed_LKAS(≤1024) + COMP_TORQUE` against the wall. COMP is
>   the driver-override comp added by `FUN_000456a4` (gate `LERP1(|driver torque gp-0x69ca|) < gp-0x6ac0`), ceiling
>   cal `0xC67D8`=**2560**. Worst-case `|gp-0x6acc| = 1024+2560 = 3584` → corridor 4096 contains it (~512 margin).
> - **⚠ SAFETY TRADE (operator's call):** 4096 ≥ 3584 ⇒ the integrator `gp-0x3570` (the override SMs `gp-0x6960`
>   arm off it) never winds up in any regime ⇒ the corridor/SM soft-EME cutback is **functionally inert** —
>   holds 2× LKAS even when the driver overrides ("fights the driver", see
>   [[reference-accord-driver-override-plausibility-eme]]). V30 edits NO monitor *code*; **hard-EME (DTC)
>   lockstep is fully intact** (corridor matched int↔float). V19's SM-gate rescale is the proportional alternative.
> - **Residuals [I]:** (1) comp magnitude UNCERTAIN — ceiling 2560 but realized `(gp-0x6ac0−LERP1)×3072>>10` may
>   be far smaller; right-size by tracing `gp-0x6ac0`'s range, then corridor = `1024 + realized_comp`. (2) if the
>   felt EME is the torque-sensor PLAUSIBILITY dropout (voter path, not the integrator), V30 won't fix it.
> - **Build/verify:** cipher round-trips, **49/49 CRC PASS**, all readbacks pass (corridor int ±4096 / float ±4.0;
>   envelope/boost/speed/code STOCK; cave 0xFF), 23-byte diff / 16 runs, **0 executable code edits** (byte-diffed
>   vs stock + re-decoded `.rwd`). Output
>   `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V30-LKAS-2x-corridor4x-LKASplusCOMP-floatmirror-PNfix-…rwd` +
>   `../accord-firmware/analysis-2020accord/_v30_plain_image.bin`. **UNFLASHED (iron rule).**
>
> ## ✅ 2026-06-03 — V29 BUILT: cal-only matched corridor (int + the CORRECT float mirror). UNFLASHED.
>
> Re-traced both monitor functions on STOCK `code.bin` myself (shaper `FUN_00042af8` decompile + watchdog
> `FUN_00043e44` disasm) → overturned BOTH the V27 and V28 models. Full model + the two fixed address errors:
> [[reference-accord-corridor-lockstep]]; handoff `docs/handoffs/2026-06/HANDOFF-2026-06-03-v29.md`.
> - **The int wall is a THREE-WAY MAX:** `gp-0x6af6 = max(dir_corridor[cal 0x774e, velocity-flat ±1024],
>   velocity/cmd-envelope IIR[gp-0x3574 sar-8, NOT driver torque; input vel-vs-cmd contested], boost[cal 0x7760 = X700/800/1100 Y0/1536/2048]) × polarity`. The dir
>   corridor IS one arm (that's why V25 faulted); the boost is a SEPARATE arm (Tracer B's "r23", not the
>   corridor as V28 assumed). Both monitors (shaper Monitor1 @line642/~0x43190; watchdog Monitor2 @0x4463a)
>   compare the FLOAT twins `gp-0x6db0`/`gp-0x6db8` ×1024 vs the INT walls `gp-0x6af6`/`gp-0x6b00`, ±5 LSB.
> - **⚠ Two prior ADDRESS errors fixed:** (a) the FLOAT corridor mirror Y is `0xC6598`/`0xC659C` (dir1,+1.0)
>   and `0xC65AC`/`0xC65B0` (dir2,−1.0) — **NOT `0xC6590`/`0xC65A4`** (those are the X velocity/torque
>   BREAKPOINTS; the V28-handoff's V29 proposal named them, which would have been a V26-class wrong-table
>   brick). (b) `0xC6664` is the ENVELOPE LERP_B (feeds early `lp→gp-0x6da8` + the separate envelope monitor
>   `gp-0x6c84`, nonzero at rest = V26's rest-fault), NOT the corridor. Traced `r11=LERP(0xC6590)`/`r7=LERP(0xC65A4)`
>   feed ONLY the float twin's corridor arm (sign/plausibility-gated off at rest, not stored elsewhere).
> - **V29 = `builds/v18_v49/build_v29_tva.py`** = V18 GAIN/clamps/ramp (the real 2×; GAIN `0xC646C` is monitor-INDEPENDENT,
>   flashed+road-validated) + INT corridor ×2 (`0xC674E`/`0xC6750`/`0xC675A`/`0xC675C`) + FLOAT corridor
>   mirror ×2 (`0xC6598`/`0xC659C`/`0xC65AC`/`0xC65B0`) + PN. **NO trampoline, NO tolerance widen; `0xC6664`,
>   boost, speed-gain LEFT STOCK & guarded.**
> - **Why it holds where V25/V26/V27 faulted:** it doubles ONLY the matched corridor arm on BOTH the int and
>   float sides → the IIR & boost arms AND the stock ±5/1024 float-vs-int residual are UNTOUCHED. V27's fatal
>   flaw was doubling the *whole* twin → the residual itself doubled → fault when demand-dominated. V25 doubled
>   int corridor only → desync; V26 doubled the envelope → rest offset. Monitors stay live (wrong corridor
>   ~1024 LSB still caught).
> - **Build/verify:** 49/49 CRC PASS, ECU-decode==patched, 27-byte diff / 16 runs, **0 executable code edits**
>   (independently byte-diffed `../accord-firmware/analysis-2020accord/_v29_plain_image.bin` vs stock + re-decoded the `.rwd` from scratch). All
>   readbacks pass (cal values set; envelope/boost/speed/code sites STOCK; cave 0xFF). **UNFLASHED (iron rule).**
> - **Confidence ~85%.** Residual (road test = arbiter): if the felt soft EME is the driver-override
>   torque-sensor PLAUSIBILITY dropout ([[reference-accord-driver-override-plausibility-eme]]) rather than
>   corridor overflow, the corridor widen won't fix THAT — but V29 still delivers safe 2× and must not
>   hard-fault. If so, pursue the V19 SM-gate route, not more corridor widening.
>
> ## ⚠⚠ 2026-06-03 (CORRECTION, prior) — V28 ANALYSIS-FALSIFIED, DO NOT FLASH (the model below was itself superseded by the V29 retrace above)
>
> A follow-up trace (operator asked "is the command compared to the envelope or the corridor?") read shaper
> disasm `0x43040–0x43172` directly and **overturned the V28 model.** `gp-0x6af6` is **NOT a pure corridor
> wall** — it is `max(driver-column-torque IIR gp-0x3574 [×256, sar-8 @0x43136], corridor LERP r23 [cal 0x774e])`
> (`cmovgt r11,r23,r10 @0x4313c` → r29 → `st.h gp-0x6af6`). So the monitors (`FUN_00043e44` + shaper) are an
> **INT-vs-FLOAT LOCKSTEP on `max(driver-torque, corridor)`** (the V13A dual-path lockstep, corridor as floor),
> NOT a corridor twin. Full record: [[reference-accord-corridor-lockstep]]; handoff banner in
> `docs/handoffs/2026-06/HANDOFF-2026-06-03-v28.md`.
> - **⇒ V28 is LIKELY BROKEN (do not flash).** V27/V28's trampoline doubles the WHOLE float twin =
>   `2×max(torque,corridor)`; the cal doubled only the corridor arm on the int side. **Turning applies hand
>   torque → demand-dominated** → twin `2×torque` vs wall `torque` → divergence ≈ FULL torque, not a 5/1024
>   residual → the ±10/1024 / ±15-LSB tolerance widen can't cover it → faults like V27. The "divergence =
>   2×residual" premise was a **mis-ID of the max's secondary arm** (read as a small fixed table `0xC65B8`; it
>   is the large driver-torque demand).
> - **Model now explains ALL three flashes:** V25 (int-corridor-only ×2) full-lock = corridor-dominated; V26
>   (`0xC6664` LERP_B) +2.0 envelope offset → rest; V27 (trampoline) turning = demand-dominated.
> - **V29 (proposed, NOT built; simpler):** DROP the trampoline AND the tolerance widen. The 2× torque already
>   comes from V18's GAIN (`0xC646C`, flashed/works — the gain is inside BOTH lockstep paths, so the monitor
>   stays matched). To widen the corridor *floor* for the soft EME without breaking the lockstep, double
>   **both** corridor tables in lockstep: int cal `0xC674E` **and the float corridor mirror `0xC6590`/`0xC65A4`**
>   (exact float mirrors of the int corridor). Cal-only, no code patch, monitor fully intact = "V26 done right"
>   (right float table = the corridor mirror, NOT LERP_B `0xC6664`).
> - **~90% confidence.** Before a V29 build verify: (1) walk `r11`'s load to confirm it = `gp-0x3574`
>   driver-torque IIR (the one inferred link; the V28-unsafe conclusion is robust to it); (2) the watchdog
>   float "secondary" arm = the float recomputation of that torque; (3) `0xC6590`/`0xC65A4` is the matched
>   table to double with `0xC674E`. Method: read the disasm MYSELF after Tracer 3 ("corridor-only") and
>   Tracer 5 ("max(IIR,corridor)") conflicted.
>
> ## ✅ 2026-06-03 — V27 FLASHED → HARD-FAULTED WHEN TURNING → V28 BUILT (corridor-monitor tolerance 2×) [ANALYSIS-FALSIFIED above]. UNFLASHED.
>
> **V27 was flashed and HARD-FAULTED the instant the wheel was turned** (wheel un-turnable). Same *class*
> as V26 (a near-t=0 divergence), different quantity. Full corrected model + the V28 build:
> [[reference-accord-corridor-lockstep]]; handoff `docs/handoffs/2026-06/HANDOFF-2026-06-03-v28.md`.
> - **Root cause of V27 (decomp `FUN_00043e44`/`FUN_00042af8` + 4 tracers + algebra + real table bytes):**
>   V27 doubles the float **twin** (`gp-0x6db0/db8`, trampoline) AND the int **wall** (`gp-0x6af6/b00`,
>   cal `0xC674E`). Both reach **exactly 2×**, and the primary float corridor tables (`0xC6590`/`0xC65A4`)
>   are exact mirrors of the int corridor (residual 0) — so by steady-state math V27 should pass. BUT the
>   watchdog twin is `polarity × max(corridor_mirror, SECONDARY tables)`; secondary `0xC65B8` =
>   X[700,800,1100] Y[0,1.5,**2.0**] makes the twin exceed the corridor by a small **residual R ≤ 5/1024**
>   (inside the window). The divergence collapses to `R = polarity×max(0, secondary−corridor)`, and the 2×
>   **doubles it**: `divergence_V27 = 2R ≤ 10/1024` > the ±5/1024 window the moment `polarity ≠ 0` (any
>   steering) → `FUN_000462e6(0x3f1b)` hard shutdown in ~10 cycles. **No symmetric doubling avoids it.**
> - **V28 = `builds/v18_v49/build_v28_tva.py` = V27 + a PROPORTIONAL 2× widen of BOTH corridor monitors** so `2R` fits:
>   - **Monitor 2 (watchdog):** `movhi` `±5/1024 → ±10/1024` — `r7` `0x3ba0→0x3c20` (@`0x44640`, shared
>     positive), `r14` `0xbba0→0xbc20` (@`0x44648`, dir1 neg), `r16` `0xbba0→0xbc20` (@`0x4466C`, dir2 neg).
>   - **Monitor 1 (shaper):** `±5 → ~±15` LSB — `addi 0x5→0xf` + `cmp 0xb→0x1e` per direction
>     (`0x43190`/`0x43196`, `0x431B4`/`0x431B6`). `±15` for the `±1` `trunc` rounding margin.
>   - **Provably sufficient** for the corridor checks (stock `R≤5/1024` ⇒ V27 `2R≤10/1024` ⇒ a 10/1024
>     window passes; real faults ~1024 LSB still caught → recalibration, not blinding). Only dir1/dir2
>     widened; integrator (weight 4) + delivered-torque (weight 32) checks **track** (twins not doubled by
>     the trampoline) → left stock. The two non-corridor negatives (`0x4478C`/`0x448E6`) **LEFT STOCK**.
> - ⚠ The negatives are **separate `movhi`** constants per check; `search_instructions` MISSED the
>   `0xbba0` @`0x44646` — a raw **byte scan** found all 5. (A positive-only widen would have bricked
>   asymmetrically.) Full Ghidra emulation of the watchdog remains impractical (`emulate_function` returns
>   only registers; twin/divergence are memory writes; 30+ RAM inputs + sub-calls).
> - **Build/verify:** cipher round-trips, **49/49 CRC PASS**, all readbacks pass (widened constants decode
>   correctly; non-corridor negatives stock; `0xC6664` stock; cave tail `0xFF`), 46-byte diff / 22 runs.
>   Output `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V28-LKAS-2x-corridor2x-twindbl-MONtol2x-PNfix-0x13000-0x100000.rwd`
>   + `../accord-firmware/analysis-2020accord/_v28_plain_image.bin`. **UNFLASHED (iron rule).**
> - **Residual [I-low]:** only the corridor checks were widened (the integrator/torque checks reasoned to
>   track, not emulated). **Pre-flash:** import `../accord-firmware/analysis-2020accord/_v28_plain_image.bin` + disassemble the 10 tolerance sites;
>   cautious first drive ready to power-cycle. Road test is the arbiter.
>
> ## ✅ 2026-06-02 — V26 FLASHED → HARD-FAULTED AT REST → V27 BUILT → FLASHED → FAULTED (see V28 above). corrected corridor-twin fix.
>
> **V26 was flashed and HARD-FAULTED immediately on startup — the wheel could not be turned at all**
> (worse than V25, which faulted only at full lock after driving a few feet). This **falsifies** the V26
> premise. Full corrected model: [[reference-accord-corridor-lockstep]].
> - **Root cause of the V26 failure:** cal `0xC6664` is **LERP_B**, a velocity *envelope* multiplier —
>   **not** the float corridor twin. The float watchdog envelope = `base/1024 + lerp_b·lerp_a`, and at
>   rest `lerp_a = 2.0`. So doubling `0xC6664` (1.0→2.0) ADDED a constant **+2.0** envelope offset at
>   every operating point including parked/centered → the watchdog diverged from the (un-widened) integer
>   side from t=0 → DTC `0xF00049` + latched motor-off in ~10 cycles. (`0xC6664`=LERP_B is instruction-
>   verified twice: [[reference-c6664-lerp-b-envelope]].)
> - **The REAL float corridor twins** are RAM `lp` (dir1, →`gp-0x6db0`) and `r20` (dir2, →`gp-0x6db8`),
>   computed in `FUN_00043e44` as `corridor_mag × float(polarity gp-0x6752)` (`lp=r2×r13` @0x4461e/0x44624,
>   `r20=r13×r9` @0x4462e). BOTH monitors compare twin vs `wall/1024`: Monitor 1 (`FUN_00042af8` @0x43172,
>   `trunc(twin×1024)≈int_wall`) and Monitor 2 (`FUN_00043e44` @0x4463a/0x44662, `|twin−wall/1024|≤5/1024`
>   → weights 1.0/2.0 → fault_word ≥128 → `FUN_000462e6(0x3f1b)` → shutdown).
> - **Why lock-not-rest:** wall and float corridor magnitude are command/angle LERPs (~0 at center, max at
>   lock) → divergence ≈0 at rest, ±1.0 at full lock when only one side is doubled.
> - **The V24/V25/V26/V27 ladder** (each had only part of the fix): V24 doubled float twins only (cave,
>   stock int corridor) → fault; V25 widened int corridor only → fault at lock; V26 widened int + doubled
>   `0xC6664` (wrong table) → fault at rest; **V27 = BOTH (int corridor ×2 + double the real float twins).**
> - **V27 = `builds/v18_v49/build_v27_tva.py`** = V18 GAIN/clamps/ramp + INT corridor ×2 (`0xC674E`/`0xC6750`/`0xC675A`/
>   `0xC675C` ±1024→±2048) + a **code trampoline** at the free `0xC4E00` cave that doubles `lp`/`r20`:
>   `0x4463A subf.s r2,lp,r10 → jr 0xC4E00`; cave `addf.s lp,lp,lp` / `addf.s r20,r20,r20` /
>   `subf.s r2,lp,r10` / `jr 0x4463e`. `0xC6664` **left STOCK** (V26's mistake reverted). Doubling lp/r20
>   reaches both divergences + both twin stores → at full lock twin 1.0→2.0 matches wall/1024=2.0 → both
>   monitors pass AND stay live (a genuinely wrong corridor still diverges).
> - **Build/verify:** cipher round-trips, **49/49 CRC PASS**, all readback asserts pass, 36-byte diff /
>   15 runs, `0xC6664` confirmed stock, cave tail still `0xFF`. The built `../accord-firmware/analysis-2020accord/_v27_plain_image.bin` was
>   imported into Ghidra and the trampoline + all 4 cave instructions disassemble exactly as designed
>   (incl. the new `jr 0x4463e` = `b70732f8`). Collateral-verified on STOCK `code.bin`: after 0x4463a,
>   `lp`/`r20` feed only the divergences + stores, no `jarl`. Output
>   `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V27-LKAS-2x-corridor2x-twindbl-codetrampoline-PNfix-0x13000-0x100000.rwd`.
>   UNFLASHED (iron rule).
> - **Residual:** the trampoline doubles the twin exactly and the cal doubles the wall exactly, so the
>   small stock float-vs-int residual `R=(twin−wall/1024)` also doubles (→`2R`) vs the ±5/1024 tolerance.
>   Typically `R`≪tolerance, but not measured across all angles → emulation sweep or cautious first drive.
> - ⚠ **.bin discipline (hard lesson this session):** analyze stock on `code.bin` (the `/master.bin`
>   program, 2113 fns) ONLY — `_v22/_v23/_v24` carry experimental CODE edits (incl. a `0xC4E00` trampoline)
>   that produce wrong answers. Sanity-check `0xC4E00==0xFF` before trusting stock analysis.
>
> ## 2026-06-02 (earlier) — V25 ROAD-TESTED → HARD FAULT → V26 BUILT (corridor lockstep fix) → V26 FLASHED → FAULTED (see V27 above). UNFLASHED.
>
> **V25 was flashed and HARD-FAULTED.** Operator drove ~5–10 ft, made a hard right turn out of a parking
> spot, and the instant the wheel hit full RIGHT lock the EPS shut down + threw a dash fault (DTC 0xF00049).
> This **falsifies** the V25-CLEAN prediction of "no hard fault." Root cause (instruction-verified — full
> record [[reference-accord-corridor-lockstep]]): **the direction corridor IS lockstep-monitored.** It is
> computed in both integer (walls `gp-0x6af6`/`gp-0x6b00` from cal `0xC674E`/`0xC675A`) and float (a
> velocity-LERP over a SEPARATE cal table `0xC6664`, stock flat 1.0). A monitor cross-checks them — inline
> check A `|int(1024×float_twin) − int_wall| ≤ 5` (@0x43172–0x431c0) + the float twin in FUN_00043e44
> (|twin − wall/1024| ≤ 5/1024; bit-weight accumulator ≥ 128.0 @0x44a26 → DTC). V25 doubled ONLY the integer
> corridor → `|2048 − 1024| = 1024 ≫ 5` constant desync → DTC, accumulating fastest at full lock (where
> `gp-0x6acc` assist demand drives the integrator hardest). So V25 walked into the SAME monitor-desync trap
> the `shl` caused in V19–V24, just on the corridor instead of the envelope. (Also confirmed dead this
> session: SM2/SM3 threshold raises are NOT the lever — operator reports V19 raised SM2 and the soft EME
> still triggered, V20 raised SM3 further and threw HARD EMEs requiring restart.)
> - **V26 = `builds/v18_v49/build_v26_tva.py` = V25 + the float-corridor twin ×2.** Adds the matched float edit V25 missed:
>   `0xC6664`/`68`/`6C`/`70`/`74`/`78`/`7C` seven f32 **1.0→2.0** (= the doubled integer corridor in the
>   monitor's /1024 units). Restores lockstep: `1024.0×2.0 = 2048` = the wall, **exact 0 divergence**. One
>   float edit fixes all checks (dir1/dir2/integrator all derive from the same flat magnitude table × direction
>   sign; direction-gated, so only the active side matters). The "weight-8 proportional window" that bit V24 IS
>   this corridor lockstep check — V26's match is exact so the fixed ±5 tolerance isn't even stressed (V24's
>   "no fixed-LSB widen can cover" was an ENVELOPE-side problem, not a corridor one).
> - **Build:** 33 bytes / 19 runs vs stock, **49/49 CRC PASS**, cipher round-trips, int+float corridor
>   X-breakpoints/N asserted unchanged, **zero code edits**, cave region all-`0xFF`. Output
>   `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V26-LKAS-2x-corridor2x-floattwin2x-PNfix-0x13000-0x100000.rwd`.
>   UNFLASHED (iron rule).
> - **Calibration:** dir1 lockstep is [V] instruction-proven (stock 0 / V25 −1024 fail / V26 0 pass);
>   dir2 + integrator are [I-high] (same magnitude table × sign, direction-gated, pinned by the
>   stock-never-faults constraint). The road test is the arbiter. Verification was static instruction
>   analysis (live emulation of the monitor was impractical — agents fell back to static; I cross-checked
>   their results against the stock-never-faults constraint and caught a wrong "dir2 PARTIAL" verdict).
> - **Next:** operator names file + bus to flash; capture CAN `0x427` + steering through a full-lock event
>   and a held-2× LKAS event (confirms the hard fault is gone AND pins the still-open command full-scale).
>
> ## ✅ 2026-06-02 (earlier) — V25 CLEAN BUILT: V18 GAIN + DIRECTION CORRIDOR ×2 (the shl/envelope thread DROPPED). FLASHED → hard-faulted (see V26 above).
>
> The V21–V24 integer-envelope (`shl 0x8→0x9`) thread was attacking the WRONG quantity. Corrected, instruction-verified model (full record: [[reference-accord-corridor-vs-envelope]]):
> - **Three distinct 2× levers — do not conflate:** (1) GAIN `tp+0x746c`=`0xC646C` — the ONLY real torque 2×; (2) `shl` IIR envelope `gp-0x3574`/`gp-0x3578` → shadows `gp-0x6af6`/`gp-0x6b00` — a WATCHDOG REFERENCE only (delivered torque `gp-0x6b98` = clamp(min(lanes `gp-0x6afe`+r20, governor `gp-0x4f64`), ±0x2000); envelope absent, verified `@0x43ae0–0x43b52`); (3) DIRECTION CORRIDOR `tp+0x7748` (dir1 UPPER)/`tp+0x7754` (dir2 LOWER) — the soft-EME integrator reference.
> - **Two faults, two causes:** SOFT EME (recoverable ~10s, NO DTC/dash) = command exits corridor `[dir2,dir1]` → integrator `gp-0x3570` wind-up → SM2/SM3 cutback (the GAIN doubled the command past the stock ±1024 corridor). HARD fault (DTC 0xF00049, dash) = `FUN_00043e44` consistency-monitor desync, which exists ONLY because the `shl` doubled `gp-0x6af6`/`gp-0x6b00` without their float twins/sibling shadows (`gp-0x6b04`=f(`gp-0x6acc`), `gp-0x6b0a`=ABS(`gp-0x3570`>>15) stay stock). V18 (gain, no `shl`) NEVER hard-faulted → the hard fault is self-inflicted by lever 2.
> - **V25 = `builds/v18_v49/build_v25_tva.py`:** GAIN `0xC646C` 891→1782 + clamps `0xC61B4`/`0xC61B2` 512→1024 + ramp `0xC64DE` 0x11→0x1B (V18 lineage) + **corridor ×2** (dir1 Y `0xC674E`/`0xC6750` +1024→+2048; dir2 Y `0xC675A`/`0xC675C` −1024→−2048) + PN. **NO `shl`, no caves, no consistency-monitor edits** — the entire V24 "B" cleanup (FP-twin caves, ±10 widen, weight-8 exclusion, inline-A neutralize) evaporates because it only existed to undo the `shl`. X breakpoints + N counts asserted UNCHANGED; zero code-section edits; cave region all-`0xFF`. **19 bytes / 12 runs vs stock, 49/49 CRC PASS, cipher round-trips, UNFLASHED.** Output `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V25-LKAS-2x-V18gain-corridor2x-PNfix-0x13000-0x100000.rwd`; plot `analysis-2020accord/figures/aggregator/v25_corridor_before_after.png`.
> - **Expected:** 2× LKAS like V18; no V19–V24 hard fault; soft-EME headroom raised proportional to gain; manual driving byte-identical to V18 (cal-only). **Safety:** corridor ×2 proportionally loosens the anti-fight/anti-oscillation gate. **Open:** not road-tested; command full-scale still ambiguous (CAN 0x427 capture pins it).
> - **MODE note:** A160 command mode = `tp+0x74c8`=0 (MODE 0), distinct from variant mode `gp-0x674e`=1; the byte-offset confusion (`0x74c8` vs `0x74ca`) is resolved.
> - ⚠ The earlier same-day V24 (shl + FP-twin caves + ±10 widen + weight-8 exclude) and the "bit32 = V18 EME" agent-memory are SUPERSEDED/contested — see [[reference-accord-corridor-vs-envelope]] §"Contested neighbor".
>
> ## 🔬 2026-05-30 — V19 BUILT: HIGH-END 2× via override-SM gate rescale (Trace A complete). UNFLASHED — operator road-tests next.
>
> Goal this session: enable the full 2× LKAS torque to SURVIVE the high-end (hard mid-turn driver-override) regime without the EME snap — by understanding exactly what the snap is and rescaling its trigger PROPORTIONALLY, not defeating it. Operator signed off on the trade (2026-05-30) before the build.
> - **Trace A (the gating prerequisite) is COMPLETE** (4-agent `firmware-codepath-tracer` swarm + operator-directed instruction-level re-verification of `FUN_00042af8`). The EME snap = THREE OR-linked authority-gate SMs in the shaper, ALL arming off the **command-magnitude path** (integrator `gp-0x3570`), NOT column velocity — which is *why* it is 2×-only. Full mechanism + the corrected command-vs-velocity seed: [[reference-accord-override-snap-state-machines]] (Trace A resolution section).
> - **Complete arming-threshold set (cal-addressable):** SM1 `0xC61DE`=2048 (+ velocity > `0xC61E0`=7168 + command-opposes-motion) · SM2 `0xC6422`=16384 · SM3 `0xC61DC`=30720 (= integrator saturation clamp; `30720 = 2×15360`). The earlier SM1 "scale puzzle" was a misread (the compare operand is the cal, not the Q15 node). `gp-0x4f60` confirmed [STRONG] = column/motor angular velocity → the SMs are anti-oscillation / fight-on-motion monitors. ⚠ **CORRECTED 2026-07-18 — `gp-0x4f60` is SENSOR-B (TAS) DRIVER COLUMN TORQUE**, per CAN-399 packer `FUN_00055c42`; see [[reference-accord-gp4f60-is-sensor-b-column-torque]]. The "anti-oscillation / fight-on-motion" reading of the SMs rests partly on this now-falsified label and should be re-examined before being relied on.
> - **V19 = `builds/v18_v49/build_v19_tva.py` = V18 (road-validated 2× gain/clamps + ramp) + TWO cal halfwords:** `0xC6422` 16384→32768 (SM2 gate → 2× envelope) + `0xC61DC` 30720→61440 (SM3 trip + integrator clamp → 2× envelope; arithmetic-safe, `0xF000×0x8000=0x78000000 < INT32_MAX`). **SM1 left stock** (its 2048 floor is already crossed at 1×; raising it would desensitize a genuine fight detector). Both halfwords in CRC block #48 (`0xC6000`). Build clean: stock-value asserts pass, **49/49 bootloader CRC PASS**, ECU-decode==patched, clean **17-byte diff** in 10 runs (the two new high-end edits show as single high-byte changes `0xC6423` `0x40`→`0x80` and `0xC61DD` `0x78`→`0xF0`). Output: `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V19-LKAS-2x-highend-SMgate-rescale-PNfix-0x13000-0x100000.rwd`. UNFLASHED (iron rule — operator must name file + bus).
> - **The rescale loosens anti-oscillation monitors** but to the *same relative* trip points at 2× authority (SM2 ~100%, SM3 ~200% of the new envelope) — you cannot have 2× authority AND a monitor cutting at 1× torque. Operator accepted this inherent trade.
> - **Residual / pre-flash [OPEN]:** (1) command full-scale ambiguity (mode gate at decompile L651; active mode `FUN_000074c4[tp+4]` unverified) → if full-scale≈8192 the `0xC61DC` edit is harmless-but-inert (necessary only if ≈15360); (2) WHICH SM fires in the real EME is undiscriminated on-car. **Recommended discriminator before flash: CAN `0x427` motor-torque + steering capture through one real EME** — confirms the firing SM and pins the scale. Open items recorded in `analysis-2020accord/notes/EME_OVERRIDE_SM_NONVERIFIED.md` §0.
>
> ## ✅✅ 2026-05-27 — V18 (2× + RAMP-ONLY) FLASHED + ROAD-VALIDATED: drives well. V16 rejected, V17 inert.
>
> A 4-analyst Ghidra review (`../assessment/`, 11 rounds, decode-verified) dismantled the V16/V17 mechanism below, and the operator road-tested the survivor (V18) — **it drives well.** Per [[feedback-operator-lived-experience]] that is the authoritative outcome.
> - **V18 = `builds/v18_v49/build_v18_tva.py` (CALIBRATION-ONLY):** 2× gain `0xC646C`=1782 + clamps `0xC61B2`/`0xC61B4`=1024 + **ramp `0xC64DE` `0x11`→`0x1B` (17→27) only** — deadband stock (29491), slew stock (0). Decode-verified on the on-disk `.rwd`: exactly **15 byte changes** (2 PN + 3 cal halfwords + 1 cal byte + 2 recomputed CRCs), 49/49 CRC; **no code patch, no trampoline.** Output: `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V18-LKAS-2x-EMEfix-ramponly-PNfix-0x13000-0x100000.rwd`.
> - **V16 REJECTED:** slew `0xC61D6` 0→14 does not "re-enable a damper" — slew=0 FREEZES a dormant speed×torque 2D shaping lane (`gp-0x356c`, fed by curves `0xC6770`×`0xC69E8`); 0→14 ACTIVATES an uncalibrated map onto the live command (mux `0xC64C9`=0). Highest-risk lever; last/never.
> - **V17 deadband-only INERT:** `0xC6424` gates only the `gp-0x356c` limiter; with slew=0 that state is pinned at 0, so 29491→20000 is behaviorally null. Deadband/slew coupled.
> - **The real EME cut node = override SM `gp-0x6960`** (NOT the shaper deadband); **ramp `0xC64DE` LENGTHENS** the re-engage (was mislabeled "faster") and targets the recovery ratchet, not the initial snap.
> - **No output rate-limiter as cal:** `gp-0x6b98` has only ±0x2000 + a ±5 change detector. An asymmetric down-rate limiter would need a trampoline code patch (`0x43b52`→`0x8B218+` cave) — **scoped in the review, never built; verified absent from every `.rwd` and from the Ghidra project.** "aragon asymmetric rate-limit prior art" RETRACTED.
> - Full mechanism + addresses: [[reference-accord-driver-override-plausibility-eme]] (corrected), [[reference-accord-eme-lever-semantics]] (new).
>
> *The "V16 EME-FIX BUILT" block below is preserved for the record; its slew/deadband rationale is wrong — do not act on it.*
>
> ## ✅ 2026-05-27 [⚠ SUPERSEDED — see the V18 block above; V16's slew/deadband mechanism is INVERTED and V16 was rejected] — V16 EME-FIX BUILT (keeps 2×): re-enable the disabled delivered-command slew limiter
>
> Root cause of the EME refined this session (operator: "whole power steering cuts out, not just LKAS") via a 4-agent program-wide inventory + disasm verification. Base assist + LKAS share the final command `gp-0x6b98`; a hard override drives a transient (no-DTC) re-init and the shaper deadband zeroes the command — and because the **slew limiter `tp+0x71d6`=`0xC61D6`=0 is DISABLED**, the drop is a hard cut+hold+jump (the felt cut + ~10 s ratchet) instead of a soft dip. **V16 (`build_v16_tva.py`) = V15B (2× gain/clamps + PN-string fix) + slew `0xC61D6` 0→14 + deadband `0xC6424` 29491→20000 + re-engage ramp `0xC64DE` 17→27.** All in CRC block 0xC6000. Build clean: stock-value asserts pass, ECU-decode==patched, **49/49 bootloader CRC PASS**, 18-byte diff in 10 runs (6 cal + 2 PN + 2 block CRCs). 2× magnitude (`0xC646C`=1782) untouched; no fault-detection logic modified (`FUN_00041eec` OFF-LIMITS). UNFLASHED (iron rule). Output: `../accord-firmware/flashing-2020accord/archive/39990-TVA,A160-V16-LKAS-2x-EMEfix-slew-deadband-ramp-PNfix-0x13000-0x100000.rwd`. Full record: [[reference-accord-driver-override-plausibility-eme]], inventory `analysis-2020accord/reference/fw_inventory/MASTER_INVENTORY.md`, pointer audit [[reference-accord-pointer-base-audit]].
>
> ## ⚠⚠⚠ EME FOUND 2026-05-26 (late) — the 2× build has a driver-override / torque-sensor PLAUSIBILITY DROPOUT (supersedes "saga closed")
>
> Operator road-reported a recurring, scary EPS-misbehavior event (EME) on the 2× build (V15B ≡ V14A torque path: arb-output gain `0xC646C` 891→1782 + clamps `0xC61B2`/`0xC61B4` 512→1024). **Always op-engaged. On sharp low-speed turns where op falls short and the driver adds significant hand torque, LKAS abruptly zeroes (wheel snaps straight, commands lose effect), steering degrades (heavy + jerky/"ratchets in the turn direction") for ~10s, then recovers; once felt "too easy/2×" after.**
> - **Mechanism (Ghidra-verified this session):** the 2× arb-output gain (applied AFTER the integrator) amplifies a pre-existing driver-override / column-torque-sensor plausibility inhibition. Driver torque enters via the dual-coil column torque sensor (5 ADC channels `gp-0x6a44/40/3c/38/46`) → voter `FUN_00041eec` → fused driver torque `gp-0x6a5e`(0xFEDF15A2) + plausibility flag `gp-0x67f4`(0xFEDF180C). `gp-0x6a5e` is the axis of `g_pArbSetpointLimitCurves` (LKAS limited by driver torque) AND feeds gates that ZERO the LKAS integrator (`bVar1=false` if any channel >0x7D00=32000 or `gp-0x67f4≠1`). Delivered LKAS = `clamp((integ+term)×pol×GAIN[0xC646C],±[0xC61B4]) × ENABLE`, ENABLE=(byte `0xFEDF195C`∈{2,3}; sole writer `0x2b51e`). Re-enable needs the channels to re-converge within 65 counts → integrator re-ramps through 2× → the ratchet.
> - **The exact gate that fires in the EME is NOT discriminated statically** (override-curve collapse vs transient dual-coil disagreement vs +32000 ceiling). Decisive next step = bench RAM or CAN 0x427 + steering-torque log through one EME.
> - **SAFE mitigation:** reduce gain `0xC646C` (e.g. 1782→~1300, ~1.5×) / clamp `0xC61B4` — shrinks the snap+re-ramp and the driver fights less hard. **DO NOT widen the torque-sensor plausibility threshold** (`FUN_00041eec` is a genuine column-torque-sensor fault detector). SAFETY: this is a reproducible mid-turn assist loss — weigh reverting to a known-good build / dropping the gain before more aggressive driving.
> - Full record + all addresses + verified-vs-inferred markers: **[[reference-accord-driver-override-plausibility-eme]]**.
>
> *The "IT WORKS" block below remains true that 2× reaches the wheel — but it is no longer the whole story; this EME is the open hazard.*
>
> ## ✅✅✅ RESOLVED 2026-05-26 — V14 FLASHED + ROAD-TESTED: IT WORKS
>
> Operator confirmed V14 delivers the intended ~2× LKAS torque at the wheel. This is the FIRST Accord torque-mod that delivers — it closes the V11/V12/V13 "no high-end change" saga and settles every open question this project carried:
> - **The binder was the arb OUTPUT stage all along.** Doubling the Q15 gain `tp+0x746c` (891→1782) and the two ±512 clamps (`tp+0x71b2`/`tp+0x71b4` 512→1024) doubled the delivered LKAS torque. Confirms the request-limited model: stock full-command arb output ≈ 15360×891≫15 ≈ **418** (gain-limited, below the ±512 clamp); V14 ≈ 15360×1782≫15 ≈ **835** (the clamp×2 is what lets 835 through instead of being re-cut to 512).
> - **The 4762 governor did NOT bind (Case A confirmed empirically).** The LKAS path is request-limited far below the governor, so the doubled ~835 reaches the motor uncut. **V15 / governor `0xC6202` edit is NOT needed for 2×** — it stays a contingency for a >~9× push only.
> - **The full delivery chain is confirmed live by road feel**, not just by static trace: arb→limit_and_pack→distribute_clamp(idx1)→gp-0x6b4c→gp-0x6b94→governor→shaper→gp-0x6b98→FOC actually moves the wheel.
> - **Disasm independently re-verified 2026-05-26 (this session):** arb math `out=clamp((combined×pol×GAIN[891])≫15, ±512)→gp-0x6b3c` (FUN_00028ea6 @0x2a1ee–0x2a2ea); `limit_and_pack` packs source idx 1 + clamped torque into the distribute struct and calls FUN_00025c32 (@0x2b522/0x2b526/0x2b52c/0x2b53e) — the live path, NOT the monitor; governor `clamp(gp-0x6b94, ±(gp-0x4f64=4762×speed≫15))→gp-0x6ace` (FUN_0004503c).
> - **Status: V14 = FLASHED + WORKING.** Residual comma-side item (per the build header): openpilot lateral PID/feedforward should know it now drives ~2× plant gain (rescale to avoid oscillation). Firmware side is DONE.
>
> *The blocks below are preserved for the record; they were correct on the mechanism and are now confirmed by road test.*
>
> ## ⚠⚠⚠ STATE 2026-05-26 (late) — the arb output REACHES the motor; V14 is on a live path; the governor (0xC6202=4762) is the combined-command binder
>
> A 3-tracer swarm + operator-directed self-verification (every claim re-checked in Ghidra) resolved the delivery topology. Full record: [[reference-accord-lkas-delivery-and-governor]].
> - **The arb output is NOT a monitor dead-end.** An earlier turn this session wrongly concluded `gp-0x6b3c` only fed a redundancy monitor and that V14 was "a no-op" — the decompiler had hidden the torque as a constant struct. Assembly proves `limit_and_pack` (FUN_0x2b422) packs the clamped arb torque into the `distribute_clamp` struct (`0x2b52c sst.h r12,0x4[ep]`, `struct[0]=1`=LKAS source index) and calls it. **Verified chain to the motor:** arb→limit_and_pack→distribute_clamp(idx1)→`gp-0x62f8[1]`→mixer ch1/mode0→`gp-0x62b0[1]`→`gp-0x3d88`→`gp-0x6b4c`→FUN_0003aa2c→`gp-0x6b94`→FUN_0004503c(governor)→`gp-0x6ace`→FUN_000456a4→`gp-0x6acc`→shaper FUN_00042af8→`gp-0x6b98`→FOC (45 readers). The two mixer lanes (mode-0 LKAS via gp-0x6b4c, mode-5 via gate→gp-0x6afe) RECONVERGE at the shaper. (Resolves [[reference-accord-demand-aggregator-pipeline]] GAP 2: gp-0x6b98 IS read by on-chip FOC.)
> - **V14 (build_v14_tva.py) is therefore NOT inert.** Its edits — gain `tp+0x746c` 891→1782, clamps `tp+0x71b2`/`tp+0x71b4` 512→1024 — scale the LKAS source's contribution on a live path. Built, 49/49 CRC, ECU-decode==patched, clean 8-byte diff, UNFLASHED.
> - **The dominant high-end binder is the runtime governor `gp-0x4f64`** (0xFEDF309C), applied in FUN_0004503c AND the shaper, = `float(cal)×1024` where cal = `tp+0x7202` = `0xC6202` = `0x129A` = **4762** (byte-verified; the adjacent `0xC6200`=8192 is NOT read). Steady-state branch (uVar26==1) = `MIN(gp+0x128 LERP, fVar54, gp+0x130=4762)×1024`, nominal 4762, never above. ⚠ **CORRECTED 2026-07-17: the gp+0x128 LERP axis is the MOTOR electrical-angle RATE (motor angular velocity), NOT vehicle road speed** — the governor tapers under fast steering motion, not at highway speed. **So the cap is ~4762, not the ±0x2000=8192 static** — this corrects the long-standing "delivered ~8192 / ±0x2000 is the wall" framing.
> - **Two distinct levers now identified:** (a) V14's arb-source scaling raises the LKAS *share*; (b) the governor cal `0xC6202` raises the *combined ceiling* (lockstep-shadowed at gp-0x448a — safety-sensitive). A perceptible 2× at the wheel may need BOTH. **OPEN (magnitude):** what fraction of the summed `gp-0x6b94` is the LKAS source at full hands-off command vs the ~4762 governor — decides whether V14 alone moves the wheel. Road test or a magnitude trace closes it.
> - **Why V11/V12/V13 saw no high-end change:** they edited the mode-5/gate/shaper clamps + setpoint shl3 — NEITHER the arb-source lever NOR the governor. V14 is the first build to touch a live lever; prior road results don't predict it.
> - **Variant mode `gp-0x674e`** (16-entry ECU-ID table @0xCD000; A160→key `TVAA1`→entry 2→mode 1) selects the arb/driver-assist LERP curve SETS — it does NOT directly set delivered LKAS gain (that's the separate per-channel mixer mode array `tp+0x5124`). Don't conflate the two.
>
> *The 2026-05-26 (eve) block below remains correct on the tp=0xBF000 base and the gain/clamp values; this block ADDS the verified delivery chain + governor and rehabilitates V14 from the "monitor dead-end" mis-call.*

> ## ⚠⚠ CURRENT STATE 2026-05-26 (eve) — `tp=0xBF000` correction supersedes the entire absent-partition arc below
>
> The root cause of every "high-end won't move" dead end was a wrong pointer base. **The EPS application `tp(r5) = 0xBF000`** (set @`0x140ce` in `FUN_00014084`), NOT `0xF8000` (that's only the bootloader's transient tp). All `tp+offset` cal therefore lives in the **programmed `0xBF000–0xC6FFF`** region — present in our dump and in the `0x13000–0xFFFFF` you flash. **There is no absent calibration partition.**
> - **The LKAS high-end binder is the arb OUTPUT GAIN** `tp+0x746c` = **`0xC646C` = 891** (`0x037B`). Full-command output = curve-pinned demand (~15360) × 891 >>15 ≈ **±418**, below the output clamp `tp+0x71b4`=`0xC61B4`=**512** and `limit&pack` clamp `tp+0x71b2`=`0xC61B2`=**512**. So the GAIN caps LKAS torque; `shl3` only lifted low/mid (slope), never the top.
> - **Why V11A/V12A/V13A all failed at the top:** they edited downstream code clamps and the *erased* `0xFF1B4`/`0xFF46C` (wrong base) — never the real gain at `0xC646C`. The whole "absent partition / gain=−1 / arb output ≈0 / motor-thermal limiter / dual-path lockstep is the binder / gp-0x6b98 is the carrier" chain is **RETRACTED**.
> - **V14 recipe (3 flashable `.rwd` cal halfword edits, no code rewrite):** gain `0xC646C` 891→1782; arb clamp `0xC61B4` 512→1024; limit&pack clamp `0xC61B2` 512→1024. Gain×2 doubles torque at *every* level incl. full 4096 — so pick gain×2 *or* `shl3`, not both (both ≈ 4× low/mid). Expect oscillation → openpilot lateral retune. Downstream code clamps (mixer ±0x2800 `0x276ec`, shaper ±0x2000 `0x43b12`, FOC ±8192 gates) appear to have headroom (LKAS is a modest contributor, distribute ratio unity `0x400`) — **OPEN: confirm via CAN 0x427 motor-torque telemetry that the LKAS channel isn't amplified to motor-scale before those clamps.** UNFLASHED/unbuilt.
> - Verified comma→motor chain: CAN 0xE4 → `lkas_process_steer_cmd`(`0x52676`, setpoint `0xFEDF1652`) → `arbitration`(`0x28ea6`: curve-limit → integrator → ×gain`0xC646C` → clamp`0xC61B4` → `0xFEDF14C4`) → `limit_and_pack`(`0x2b422`: clamp`0xC61B2` → `0xFEDF14C6`) → `channel_router`(`0x2b57a`) → `motor_cmd_mixer`(`0x26c80`, ±0x2800 → `0xFEDF14B6`) → `rate_shaper`(`0x42af8`, governor `0xFEDF309C` + ±0x2000 → `0xFEDF1468`) → FOC(`0x3b8f6`/`0x370b6`/`0x56420`) → TSG21 `0xFFFFD000` / CSIG.
>
> *Everything below is preserved for the record; the V11/V12/V13 builds and all "absent partition" reasoning targeted the wrong cal base.*

Torque-mod for the 2020 Accord (`39990-TVA-A160`). The **V0 plan** (`analysis-2020accord/TORQUE_MOD_V0.md`, drafted 2026-05-25) was the recipe; **V11** is the build that resulted after Ghidra-verifying it the same day. Builds on [[reference-accord-arbitration-limit-family]] and [[reference-accord-demand-aggregator-pipeline]]. The window-ceiling correction lives in [[reference-accord-lkas-window-ceiling]].

**WHAT THE V0 PLAN GOT WRONG (Ghidra-verified 2026-05-25, code.bin port 8193) — supersedes §0/§3a-iii/§4 of the doc:**
- **Hard ceiling is ~2.0× (16383 / 0x3FFF), NOT 3.99×.** The V0 plan saw only the int16 *storage* limit (0x7FFF). But the gate `FUN_00042ac6` (`0x42ac6/aca`) AND the shaper input-check (`0x43ae8/aec`) both use the `+0x2800/-0x5001` plausibility idiom; widening the window to ±W needs 2nd imm `-(2W+1)`, and `W=0x4000` overflows imm16. So `±0x3FFF` is the max. **2.5× (0x5000) and 3× (0x6000) are NOT value edits** — they need both comparison sequences restructured (a code rewrite).
- **The shaper is a dual range-check, not a plain ±0x2000 clamp.** `FUN_00042af8` @ `0x43ae8` re-runs the gate's `±0x2800` check on `0xFEDF1502` and `cmovc 0x0` **ZEROES anything outside** (incl. the `0x7FFF` sentinel). The V0 plan MISSED `0x43ae8/aec`. Overshooting the window kills LKAS (the Civic V10A failure mode), it does not add torque.
- **Mixer LKAS lane pinned = the `0x27442` block** (`gp-0x3d8c` accumulator → `r26` → `jarl 0x42ac6` @ `0x277f6`). The other three ±0x2800 mixer blocks are not the LKAS lane. (Resolves the V0 §3a-iii "MUST identify the lane first.")
- **Residual runtime limiter [OPEN]:** the shaper also clamps by `*(gp-0x4f64)=0xFEDF309C`, itself zeroed if >0x2800. May bind below target → delivered < 2× even with every static edit raised. Bench RAM probe only.

**V11A — built, flashed, ROAD-TESTED 2026-05-25: NOT PERCEPTIBLE.** The ~2× ceiling-raise (widens distributor lane+4, mixer `0x27442` lane, gate, shaper input-check, shaper final clamp to ±0x3FFF/±0x4000 + arb table `0xE4180`+mirror `0xE5180` 15360→16384; 49/49 CRC; flashed cleanly). Operator could not tell it was a 2× mod. **Root cause [V]: V11A is a pure ceiling-raise — it left the SETPOINT GAIN untouched.** `s_lkas_process_steer_cmd` @`0x52676`: `setpoint = clamp(-(comma_cmd << 2), ±0x4000)`. The downstream clamps only bind at FULL-scale comma command (4096×4=16384=`0x4000`); in normal lane-keeping openpilot commands far below that, so the setpoint never reaches even the *stock* clamps → raised ceilings never engage. **A ceiling-raise is invisible unless the command saturates.** (Operator diagnosed this correctly: "we forgot the multiplier/shape.")

**V12A — built 2026-05-25 (`build_v12_tva.py`, its own script; imports V11's clamp recipe), UNFLASHED.** V11A's clamps **+ the setpoint gain `shl 0x2 → shl 0x3` @`0x526d2`** (byte `0xC2→0xC3`; `×4 → ×8` = doubles the internal command at EVERY level, saturating at `±0x4000` at half comma input). The clamps stop the doubled value being re-cut by the staircase; the gain makes it felt across the normal operating range. 49/49 CRC, byte-diff = V11A's 144 sites + 1 gain byte. Output: `../accord-firmware/flashing-2020accord/archive/39990-TVA-A160-V12A-LKAS-gain2x-shl3+clamps-…rwd`. **Caveats:** (a) doubling plant gain without an openpilot PID retune risks oscillation — low-speed test first; (b) the runtime limiter `0xFEDF309C` may still cap the top end (the low-mid range will still feel the gain). This is the §4 "gain/slope" variant; ceiling-raise (V11A) and gain (V12A) are the two distinct levers.

**V12A ROAD-TESTED 2026-05-26 — both caveats confirmed.** (a) Low/mid command shows the 2× gain AND the predicted oscillation; operator accepts it as expected, no firmware change wanted — openpilot just needs to know it's now driving ~2× torque at the low end (lateral-PID/feedforward rescale). (b) FULL command still delivers stock (~1×): the high end is capped by the **motor current/thermal output limiter** `FUN_0007b022 → 0xFEDF309C` (≈8192 counts), confirmed via Ghidra — the stock "2:1 throttle to 8192" WAS this limit, co-set with the static ±0x2000 clamp, so raising only static clamps couldn't move the top. Its params are in the absent `0xF8000+` partition; the only static lever is bypassing the limit in the shaper (motor-damage risk — not recommended). See [[reference-accord-lkas-window-ceiling]]. **Net usable win = the low/mid 2× (with openpilot retune); peak torque is fixed by the motor's protective envelope.**

**V13A — built 2026-05-26 (`build_v13_tva.py`; imports V11 clamp recipe + V12 gain), UNFLASHED.** The high-end re-investigation RETRACTED the "motor thermal limiter" claim (operator's physical objection was right): the binder is a **dual-path lockstep redundancy monitor** — the LKAS demand is computed in BOTH an integer path (shaper `FUN_00042af8` → `gp-0x6b98`) and a parallel float path (`FUN_00043e44` → shadow `gp-0x6dbc`), cross-checked to `|shadow*1024 − demand| ≤ ~5 counts`; the ~8192 ceiling lives identically in both (int `±*(gp-0x4f64)` then `±0x2000`; float `±limit/1024≤10` then `±8.0`). V11A/V12A raised only the int static clamp, so the locked pair never moved. **V13A raises the ceiling in BOTH paths in lockstep** to ~2× (int 0x3FFF ↔ float 15.999×1024=16383): 2 int edits (0x43ae4 force limit 0x3FFF, 0x43af6 widen its window-check) + 4 float edits (0x4486e force float limit, 0x4487e cap 10→16, 0x448c2 +8→+16, 0x448ce −8→−16). 49/49 CRC PASS, ECU-decode==patched. Output: `../accord-firmware/flashing-2020accord/archive/39990-TVA-A160-V13A-LKAS-gain2x-lockstep-ceiling16383-…rwd`. **Residual risk (no bench read available):** int vs float must also agree within ±5 counts in the 8192→16383 region previously masked by saturation — unverifiable statically; if they diverge LKAS faults/cuts at high command (road-testable, recoverable). See [[reference-accord-lkas-window-ceiling]].

**V13A ROAD-TESTED 2026-05-26 — IDENTICAL to V12A (low-end 2× + oscillation, high-end still stock), NO EPS errors.** This is the decisive result: V13 raised every clamp through the shaper demand `gp-0x6b98` (int gp-0x4f64 clamp + float shadow in lockstep) and produced NO fault and NO high-end change. No fault ⇒ the int/float lockstep stayed consistent (the demand likely DID reach ~0x3FFF). No high-end change ⇒ **the binding ceiling is DOWNSTREAM of the entire torque-demand pipeline** — in the motor current-control / FOC stage. The gain reaching the motor (low-end 2×) proves `gp-0x6b98` is the torque-command path, so a downstream saturation re-caps it. Forward trace: `gp-0x6b98` feeds `FUN_0007c4f2` (FOC voltage/PWM output) only as a power feed-forward (`demand/1024 × speed × 2π/60`), clamped against calibration `DAT_66xx`=`tp+0x66xx` (ABSENT 0xF8000+ partition); and `FUN_00059912` (CAN telemetry packer). The motor current/torque ceiling is calibration-driven and its parameters live in the **absent partition we don't have in this dump** (same family as `FUN_0007b022`/`FUN_0007c4f2` params, all `tp+0x60xx/66xx`). **Conclusion: the LKAS high-end cap is NOT reachable by editing our code image [0x13000,0x100000); it requires the 0xF8000+ calibration partition** (a different dump), OR it is a physical back-EMF/voltage limit at test speed (discriminable: does the cap rise at lower vehicle speed?). V13A is lockstep-correct but does NOT achieve 2× at the top — not worth re-flashing. See [[reference-accord-lkas-window-ceiling]].

**2026-05-26 ARBITRATION-OUTPUT RE-INVESTIGATION (5-subagent swarm + operator-directed deep RE) — supersedes the V13A "downstream FOC/absent-partition" conclusion above with a more precise location.** Triggered by operator: "triple-check every leaf; where did we mis-infer?" Key results:
- **The V13A "no fault ⇒ demand reached the ceiling ⇒ binder is downstream" inference was a LOGICAL ERROR.** The lockstep monitor only checks int-vs-float *agreement*; a clamp at ~8192 biting both paths leaves them agreeing → no fault → top stays stock, with the demand never actually exceeding 8192. No-fault did NOT prove the demand rose. The cap can be (and is) upstream of the demand pipeline we kept raising.
- **`tp = 0xF8000` VERIFIED FROM STARTUP (2026-05-26 eve).** Real running init at `0x914a`–`0x9156`: `gp=0xFEDF8000`, `tp=0x000F8000` (`movhi 0x10,r0,tp` / `movea -0x8000,tp,tp` — direct, not a literal pool). The reset stub `FUN_00000080`'s `mov r0,tp` is only the power-on clear. (The earlier "confirmed by reading bytes" was CIRCULAR.) **CORRECTION: `0xF8000–0xFFFFF` is NOT an "absent partition" — `code.bin` is a COMPLETE `0x0–0xFFFFF` UART dump of a spare 2020 Accord Touring EPS (CRC word near `0xFFFFF` confirms; UART→flash-controller path needs no firmware handler). It genuinely reads `0xFF`, nothing in firmware writes it → these ARE the real cal values on a working-variant unit.** So arb gain `0xFF46C`=`0xFFFF` (−1 as s16, NOT a normal positive gain) and clamps `0xFF1B4`/`0xFF1B2`=`0xFFFF`; the arb output `gp-0x6b3c` is degenerate (≈0). The live torque path is therefore most likely `gp-0x6b98` (shaper/demand), under active swarm trace — NOT settled.
- **The real LKAS-torque MAGNITUDE stage is the arbitration OUTPUT, not the demand pipeline.** `m_steer_torque_arbitration` (FUN_00028ea6) final math (decompile lines ~1271–1292): `iVar28 = (combined_torque) * (signed char *(gp-0x6752)) * (short *(tp+0x746c)); uVar13 = iVar28 >> 15; uVar13 = clamp(uVar13, ±*(tp+0x71b4));` → writes `gp-0x6b3c`(0xFEDF14C4) + `gp-0x6b38`. The **Q15 gain `tp+0x746c`** and **output clamp `±tp+0x71b4`** are CALIBRATION in the absent partition. Every clamp V11/V13 raised (mixer/gate/shaper/demand/float-lockstep) is DOWNSTREAM of this point, so a setpoint-derived value already cut here had nothing above stock to pass → explains 3 builds of "no high-end change, no fault."
- **`gp-0x6752` is a ±1 assist-POLARITY flag (mirrored with gp-0x4c2d, set by cal parser from records), NOT a throttle.** Ruled out as a lever.
- **NO runtime RAM mirror/governor of the arb gain/clamp exists** (unlike `gp-0x4f64`'s FUN_0007b022 governor). The clamp is applied directly from absent ROM each call. So the only ways to move it: (a) source the cal partition, or (b) override the *code* that reads `tp+0x71b4`/`tp+0x746c` with immediates (the V13 technique, applied at the arb stage) — but with the absent values unknown we can't tell which of the series clamps binds, so a blind override risks being a V13-style no-op.
- **Editable secondary binder found: distribute CLAMP C `±0x2800` (10240)** at `0x25c9c/0x25ca2/0x25ca8/0x25cac` in `m_motor_cmd_distribute_clamp` (FUN_00025c32), on the LKAS torque (struct field +4), NEVER raised. 10240 > stock-8192 so it isn't the stock binder, but it WOULD cap a 2× push (16384>10240) → must be raised alongside any successful top-end lift.
- **Possible WRONG-CURVE mis-edit:** the arb input clamp is a mode-indexed FAMILY of LERP curves; the active curve is chosen by mode byte `gp-0x674e`, set ONCE at init by FUN_00042692→FUN_00057f8e (a HARDWARE-VARIANT selector matching a 5-byte ECU ID at `gp+0x6408..640C` against a 16-entry table at `0xCD000`). Production "15360-flat" variants use modes 0/1/5/6/16 → curves `0xE4180`/`0xE41A8`/`0xE4248`/`0xE5180`/`0xE6220`. V11 raised only `0xE4180` + `0xE5180` (modes 0 and 6). If TVA-A160's variant is mode 1/5/16, **we raised the wrong arb curve.** Must confirm the active variant before trusting the arb-curve raise. (Low-value curves 112/64 would barely steer → TVA-A160 is almost certainly one of the 15360-flat variants.)

**SETPOINT-CLAMP LEVER — calculated then RETRACTED (2026-05-26).** Op asked to compute the setpoint clamp for full-range 2×. Math: setpoint `= clamp(-(cmd<<N), ±0x4000)`, int16 @0xFEDF1652; stock N=2 hits `0x4000` at full cmd; 2× wants `cmd<<3` (the shl3 gain we have) peaking at `0x8000`=32768 which overflows int16 → so the int16-max clamp is `±0x7FFF`. **Overflow is SAFE:** `s_clamp_i32` (FUN_00049a90) is a verified 32-bit signed clamp; `0x8000` exists only as a 32-bit `+32768` intermediate (bit-31=0, positive), the clamp bounds the result into `[-0x7FFF,+0x7FFF]` BEFORE the `st.h` low-16 truncation, so it's lossless. (`±0x7FFF` is exactly the bound that avoids the wrap; `±0x8000` would let `st.h` flip `0x8000→−32768`.) **BUT the lever is inert/risky and is RETRACTED:** the arb pins the setpoint below `0x4000` two ways — (1) an engagement/debounce gate `bVar2 = (setpoint+0x4000U)<0x8001` (arb line 208) that requires `setpoint∈±0x4000` and gates a ramp state-machine (gp-0x6758→cVar44→gain); a setpoint >0x4000 makes bVar2 false and skips engagement (imm16-window-family, can't widen past ±0x3FFF); and (2) the LERP curve clamp (arb lines 153–159) cuts setpoint to ±curve(~15360) regardless. So no useful headroom above ~0x4000; stock is already there. The 2×-at-top lever is the absent-cal Q15 gain `tp+0x746c`, not the setpoint clamp. See [[reference-accord-lkas-window-ceiling]].

**Net 2026-05-26 (midday) verdict:** low/mid 2× (from shl3 gain) is real and is the usable win; **the high-end ceiling is set by absent-partition calibration (arb Q15 gain `tp+0x746c` + output clamp `tp+0x71b4`)** plus the imm16-bounded plausibility windows (setpoint gate, arb curve) which can't widen past ±0x3FFF. To break the top cleanly: source the `0xF8000+` cal partition (may already be in the original `.rwd` — this Ghidra `code.bin` has it erased), or bench-probe `gp-0x6b3c`/`gp-0x6b98` at full command. Blind code-override of the arb clamp loads is possible but V13 showed the no-op risk when the overridden stage isn't the binder.

**[SUPERSEDED 2026-05-26 eve — the above absent-partition framing is WRONG.]** Operator confirmed `code.bin` is a COMPLETE `0x0–0xFFFFF` spare-EPS UART dump (trailing CRC), so the `0xF8000+` cal is present-and-`0xFF`, NOT missing — "source the partition"/"re-dump" is a dead end (same `0xFF` result). With arb gain `0xFF46C`=`0xFFFF`(−1), the arb output `gp-0x6b3c` is degenerate (≈0) → the arb gain/clamp are NOT the live high-end binder. `gp-0x6b3c`'s sole consumer is `m_steer_torque_limit_and_pack` @0x2b422 (re-clamps `0xFF1B2`, calls `m_motor_cmd_distribute_clamp`=clamp C); the arbitration never reads `gp-0x6b98`. Working hypothesis: the LIVE torque path is the `gp-0x6b98` shaper/demand chain (consistent with shl3 giving low/mid 2× via that path). New 2× levers will come from tracing `gp-0x6b98` upstream+downstream — all in editable code + present cal. UNDER ACTIVE SWARM INVESTIGATION; topology not yet settled.

**V11B (3× / 2.5×) deliberately NOT built** — above the ±0x3FFF wall (see ceiling). Operator chose 2026-05-25 to leave it; revisit only if road feel warrants the comparison-sequence restructure.

**Still-open gating (per [[feedback-rigorous-validation]]):** (1) the runtime limiter `0xFEDF309C` — does ~2× actually reach the motor? bench probe; (2) GAP 2 — shaper output routes to a CSIG0 serial frame, on-chip FOC handoff unproven; (3) counts→Nm units unknown; (4) FOC/thermal limit in the absent 0xF8000+ partition; (5) openpilot PID retune for the plant-gain change. No flash until the operator names file + bus.


## 2026-05-30 — V20A / V20B built (UNFLASHED)
Lineage V18(flashed)→V19→V20. Builder `analysis-2020accord/builds/v18_v49/build_v20_tva.py` (decodes the
validated V19 .rwd, patches cal halfwords, recomputes block#48 CRC, re-encodes; the
build_v19 path needs stock code.bin + iHDS template which are absent here).
- **V20A** `39990-TVA,A160-V20A-LKAS-SM3max-PNfix-0x13000-0x100000.rwd` — SM3 arm 0xF000→0xFFFF
  (architectural max @0xC61DC), SM2 stays 0x8000. Expected ~inert vs V19 (SM2 binds first) =
  controlled "isolate SM3" test. 986042 B, 6-byte diff vs V19, build+independent verify OK
  (SM3=0xFFFF, both block CRCs valid). sha256 3f7cb2949a1cb98ab84d6f3ee87214fb6a901cda31c6c9e5c9278ffed0dc83fe.
- **V20B** `39990-TVA,A160-V20B-LKAS-SM3max-SM2x3-PNfix-0x13000-0x100000.rwd` — SM3→0xFFFF +
  SM2 0x8000→0xC000 (49152, 3× of stock 16384 @0xC6422). The real "3× gate" set. 986042 B,
  7-byte diff vs V19, build+independent verify OK (SM2=0xC000, SM3=0xFFFF, both CRCs valid).
  sha256 9afc645cba3ab434e8069916617eae7f5aa55a9a1e0e2cd659409a0605bd85af.
  (Hashes also in `analysis-2020accord/_v20_hashes.txt`; V19 base sha256
  7a492ca3b3b7c1409f81df6d2549e6eb81b8fc209ad174f99d48334e23f603b3.)
Full mechanism + rationale + numbers: [[analysis-2020accord/notes/SESSION-2026-05-30-EME-RESOLUTION.md]] (= analysis-2020accord/notes/SESSION-2026-05-30-EME-RESOLUTION.md).
NO FLASH until operator names file+bus.
