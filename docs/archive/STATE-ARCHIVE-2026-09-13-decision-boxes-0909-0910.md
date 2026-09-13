# STATE ARCHIVE — the decision boxes of 2026-09-10 (the excitation census) and 2026-09-09 (V289 flew / V290 designed)

Moved out of `docs/STATE.md` on 2026-09-13 at the V291 close-out, superseded in place by the 2026-09-13 box.
**A record of what was believed when written, not an instruction.** Nothing was retracted by the move.

---

## ✈ THE DECISION, IN ONE PLACE — updated 2026-09-10 (**ROOT-CAUSE SESSION. NO BUILD CUT. The grinding is an EXCITED RESONANCE and there is NO excitation to remove.**)

**ON THE CAR: V289 rev 1.** **RECOMMENDED, AND THE OPERATOR'S OWN STANDING DECISION (2026-09-09): revert to V282.**
Flash target unchanged — see the *FLASH TARGET* block further down. **Nothing was built, flashed or sent on any bus on 2026-09-10.**

---

### 🛑🛑🛑 THE VERDICT — (C) EXCITED RESONANCE. STOP HUNTING THE EXCITATION.

Six agents on disjoint surfaces, 17 routes, 6 builds **plus stock**. Full note:
`memory/accord/mechanism/accord-grinding-is-an-excited-resonance-no-excitation-to-remove.md`.

**THE DECISIVE MEASUREMENT — coherence time EQUALS ring-down time.** A noise-rung damped pole gives
|ρ(τ)| = exp(−ζω₀τ) exactly; a drive or a limit cycle keeps phase for seconds. Measured τ_c **0.35–0.87 s
= 6.5–17.4 cycles**, implied ζ **0.009–0.025, matching the independently measured free-decay ζ on every
build** (sham band 0.18–0.38 s). ⇒ **There is no persistent phase, therefore no persistent source.**

**THE EXCITATION CENSUS — every candidate bounded or dead [EVIDENCE]:**

| candidate | bound | source |
|---|---|---|
| discrete command kicks (cap binds, idx steps, Δ² spikes, sign reversals) | **≤ 13 %** of 514 burst onsets; cap binds **RR 0.83 [0.69, 0.96]** — *below* chance | `BURST-ONSET-TRIGGERS-2026-09-10.md` |
| road / chassis input | **null**, 30 route×IMU tests; the chassis does not carry the mode | same |
| self-oscillation / limit cycle | **falsified on 5 independent signatures** | `FORCED-VS-LIMIT-CYCLE-2026-09-10.md` |
| outer loop through openpilot | **\|L\| = 0.026–0.165**, bound 0.096–0.189, ≤ 0.38 adverse; needs 1.0 | `OUTER-LOOP-ID-2026-09-10.md` |
| steering-angle quantiser echo | **falsified as a coherent link** — residual cmd↔angle coherence **0.022** after removing the camera clock | `COMB-VS-ECHO-SIZING-2026-09-10.md` |
| camera comb (modeld's 20 Hz staircase) | **REAL and LARGER THAN FIRST REPORTED — lock fraction ≈ 0.50**; perfect deletion buys **≈29 % amplitude (~3 dB)**. ⚠ But V289 already flew the un-forced case and it got WORSE (confounded) | `COMB-VS-ECHO-SIZING-2026-09-10.md` §12 |

**Command side in total:** whole-band ablation through the byte-exact mirror — the command's *entire*
in-band content delivers **11.56 of 57.21 counts (20.2 %) on r39/V282** and **5.21 of 125.86 (4.1 %) on
r63/V289**. **The feedback leg carries 88–100 % on every route.** Comb and echo are **competing
partitions of ONE command-side budget**, not additive sources.

**⭐ THE GRINDING IS ENGAGEMENT-GATED** — 20,761 engaged vs 5,905 lateral-disengaged windows, 17 routes.
Load-matched at creep on **both** driver-torque and wheel-rate IQR: **0.3617 engaged vs 0.0108 disengaged
(×33) with MORE driver torque (376 vs 267) and MORE wheel motion (205 vs 100)**; **×72** at high demand.
Disengaged rate **0.000–0.0505 on all 17 routes including stock**. ⇒ The 20 Hz object needs LKAS torque.
🛑 It **cannot separate inner from outer** (`STEER_REQUEST = 0` opens the EPS's own rate loop too) — the
|L| bound does that. ⚠ Decisive at 0–8 m/s only; **120 disengaged windows total at 8–25 m/s, ZERO above 25.**
🛑 The **shape-only** gate does NOT go to zero disengaged (0.25–0.50 at **12–14 Hz**) — the low-demand
road/plant line. **The two-object picture holds on this cut.**

🛑 **WITHDRAWN 2026-09-11 — both halves of what stood here were artefacts of a BIASED ESTIMATOR.**
The retracted text claimed *"bar is 34 % camera-locked, the ANGLE only 2 %, so a torque comb barely moves
the column's inertia and openpilot measures the angle"*, and separately that *"the comb does not grow when
the car grinds"*. **Debiased, r39 reads command 0.624 · bar 0.534 · ANGLE 0.401** — the angle is ~40 %
camera-locked, not 2 %, **and the column-inertia explanation goes with it.** And the comb **does** grow:
×0.94–1.81 against the ring's ×1.62–2.68 (r39's CI now excludes 1 **in the opposite direction**, 1.29
[1.08, 1.59]). **What survives at true strength: the response outpaces the drive by ×1.3–2.3, not ×2.5–4.0
— consistent with partial amplification, and NOT a "constant driver, varying damping" signature.**
⇒ **The crux-3 synthesis below loses one of its six premises.** [`COMB-VS-ECHO-SIZING-2026-09-10.md` §12]

**⭐ THE 20 Hz COINCIDENCE, RESOLVED:** the loop's own mode sits at **20.07 / 20.10 / 20.11 Hz** on
V281r3 / V282 / V288 against modeld's **20.02 Hz** — within 0.1 Hz, inside the mode's ~1.2 Hz bandwidth.
**A coincidence, not a mechanism**, and it is what made the comb look causal. **V289 separated them**
(mode → 16.46/16.55 Hz, forcing stayed at 20.0) **and the grinding got LOUDER.**

---

### 🛑🛑 THE DESIGN LAW THIS REPLACES THE OLD ONE WITH

> **Under (C) the lever is the SENSITIVITY PEAK |1/(1+L)| across the WHOLE 12–26 Hz band, not a notch at
> one frequency. Design against max Ms over 12–26 Hz and PRE-REGISTER THE WHOLE BAND.**

**V289 is the proof and the trap in one drive:** it killed the 20 Hz object completely (18–22 Hz band
empty, 0/1414) and spent the 30° of margin the already-present 15–17 Hz pole had. The 18–22 Hz census
gate was blind to exactly what went wrong.
**RULED OUT: drive-hunting, and nonlinearity-hunting** — the D clamp, the sum clamp, the 123/frame slew
cap and rack stiction are **not** what sets the amplitude.

---

### 🛑🛑 CORRECTIONS OF RECORD, 2026-09-10 — premises the kit reasoned from that are FALSE

1. 🛑🛑 **"V288 cut 20 Hz by ×0.457, so THE REFERENCE-SIDE CLASS IS EXHAUSTED" — WRONG, and it is the
   most consequential error in the recent record.** The cave is **non-LTI**: `delta = sp − y_prev;
   step = delta>>4; if step==0 and delta!=0: step=1`. The anti-stick branch makes it a 1-count/tick
   follower below |d| = 16. Measured fundamental gain at 20.3 Hz: **≈1.00 at A = 4–8**, 0.62 at 16,
   0.44 at 40. **The ring is 4.0–10.7 sp counts** (15–40 raw ÷ 16.125736 idx LSB × 4.30 sp/idx); a
   slew-capped frame is 32.8. ⇒ **V288 changed the ring band by −1 % to +9 %, and its phase by 0.0°.**
   **Its null is UNINFORMATIVE IN BOTH DIRECTIONS. The reference-side class is UNTESTED, not exhausted.**
   Four independent derivations (`fwpath`, orchestrator, `cyclekind`, `combsize`).
   🛑 The caveat was in **our own adversarial pass three days before the build flew**
   (`ADV-V288-A-ARITHMETIC-2026-09-07.md` ll. 285–287: *"below ~8 counts the filter is essentially
   transparent"*) and was not applied when the drive was read.
2. 🛑 **`clip_curvature` NEVER rate-limits — binding fraction 0.000 in every route × stratum.**
   `STARPILOT-FORK-COMMAND-PIPELINE-2026-09-07.md` §2.1 is **false in practice**; 60–71 % of engaged
   ticks at v < 12 carry `modelV2.action.desiredCurvature` bit-for-bit. **`jerk_filter` is likewise
   transparent at 20 Hz** (|setpoint/F| = 1.000) and must not be counted as command smoothing.
3. 🛑 **The live openpilot gains are NOT the config defaults** — measured exactly (p5 == p95):
   **kp 0.8000 (r39), 0.9000 (r5e/r62/r63), 0.6000 only (r35)**; **latAccelFactor 2.1100 (r39/r35),
   6.0000 (r5e/r62/r63)**, not carParams' 1.68933 nor torqued's 2.46–2.50. Any gain chain built on
   1.6893 is **×3.6 too large** on the recent routes.
   ⇒ **`accord-honda-kp-ki-scale-never-acted-kp-is-0600-on-all-60-routes` no longer holds for these routes.**
4. 🛑 **`pid_log.output` is the NEGATED torque** ⇒ characteristic equation `1 − P·K = 0`: **critical
   point L = +1, metric |1 − L|, critical phase ~0°, NOT ±180°.** The old convention makes the *safest*
   route read as the most dangerous. |1 − L|: 1.069 / 1.088 / 1.022 / 0.974 / 1.154.
5. 🛑 **`wire_0xe4_20hz.episodes_of` HARD-CODES the 18–22 Hz gate** — 12 and 15 episodes on r62/r63
   against a band-aware detector's **57 and 83** (225 corpus-wide). **Every V289 rate number computed
   with it is wrong.** Use `rlog-tools/studies/grind/fvlc_lib.py`. **V289's cleanest band is 15–18.5 Hz**
   (median episode demand index 13.2, f0 16.16 Hz); 13–18 catches the road line (7.0), 14–18 is 10.0.
6. ⚠ **"f0 pinned to +0.4 Hz across Kp 248→696" is NOT supported** — acting Kp is confounded with demand
   index. Identified matched-cell contrast **+1.80 Hz [−0.02, +4.46]**. Correct statement: *any gain
   effect on f0 is small and poorly determined; the phase effect is large and unambiguous* (−3.78 Hz).
   **f0 falls with vehicle speed** (−0.11 to −0.21 Hz per m/s), a plant-stiffness signature.
7. ⚠ **"A Q ≈ 17 mode rings 12–32× its impulse" is FALSE** (orchestrator's error). A unit-area impulse
   peaks at ωn ⇒ a 10 ms kick of height h rings to ≈**1.26 h**; ζ buys the **5.5-cycle length**, not
   amplitude. Phase-locked ceiling **1/(1−e^(−2πζ)) = 6.00**, degraded by |cos ψ|.
8. ⚠ **The device's `0xE4` tx counter fits 99.53–99.56 Hz, not 100** — 0.45 % bias on that axis.
8b. 🛑 **"Slew-capped on 13–21 % of grinding frames" is WRONG — measured bind duty at the 122.88 cap is
   **1.45–4.29 %** (engaged baseline 0.50–1.86 %, enrichment only ×1.24–2.92).** The 13–21 % figure is most
   likely the ≥ 40-count column (9.9–15.0 %), and ≥ 40 is a third of the cap and is **not binding**.
   ⇒ At ~2 % duty the two-tone describing function gives **|N| = 1.000 at 0° — the rate limiter is
   TRANSPARENT at 20 Hz**, and the ring line is demonstrably present in the **post-limiter** `0xE4` stream
   at 5.6–40.7 counts. **Raising `STEER_DELTA_UP` changes 20 Hz content by essentially nothing** — it is an
   authority decision needing its own drive, **not an excitation lever in either direction**. (An earlier
   claim that raising it would admit ×15–67 more 20 Hz energy rested on a synthetic 99.8 %-duty sweep and is
   **retracted**.) ⚠ Safety unchanged and still binding: **panda enforces NO Honda steer limit at all**
   (`opendbc/safety/modes/honda.h:274-282`).
8c. ⚠ **The ring at the wheel is SMALLER than first reported: 0.17–0.28 LSB**, measured through `0x18F`
   STEER_ANGLE_RATE (0.125 °/s LSB, ~100× finer in this band) rather than through the quantised angle
   itself, which reads 1.4× high as expected at ~2× the quantiser floor. ⇒ **~40 % of the ring-band content
   the controller sees in that channel is quantisation NOISE, not motion** — and the residual is **not
   white dither**: it is coherent with the independent rate channel at **0.78–0.90** in grinding vs
   0.48–0.68 baseline, at the same f0 as bar. **The quantiser is DRIVEN by a real ring, not manufacturing
   one.** It is nonetheless **not** what puts the 20 Hz line in the command: P-on-the-measured-angle
   accounts for only **0.27–0.37** of the command's ring line.
8d. ⚠ **The record's "open-loop 9 % / feedback 63 %" split is the MOTOR TORQUE's, not openpilot's** — 63 %
   is the **EPS's own internal rate feedback**, and openpilot's angle echo lives entirely inside the 9 %.
   Any fork-side measurement lever attacks that ~9 %, of which the echo is at most a third.
9. 🛑 **The EPS itself builds CAN `0x14A`** (`FUN_00055a98`; the Accord uses the **Civic-hatchback**
   powertrain DBC, `BO_ 330 STEERING_SENSORS: 8 EPS`) and **floor-truncates the broadcast STEER_ANGLE by
   5 bits (32:1), undithered** — internal ~0.003°, transmitted 0.1° (`FUN_00040a50`, `0x40B70` / `0x40B7A` /
   `0x40B80`). A real defect. **NOT established as causal** — the ring at the wheel is **sub-LSB
   (0.29–0.47 of one step)** and the echo is falsified. Lockstep is a **bit-exact dual-copy check with
   nothing recomputed ⇒ a dithered value would pass**; the fault path is **debounced**, and what the
   confirmed state does (DTC / MIL / assist cut) is **NOT traced — a required gate before any build there.**
   ⚠ **No clean hook exists** at `0x40B70`–`0x40B92` (unrelated work interleaved) and **no free flash was
   located in that region.** Design pass only, not build-ready.

---

### 🛑🛑 THE ESTIMATOR CORRECTION — `R2 − floor` IS BIASED LOW. USE `R2_deb`.

🛑 **Three agents published camera-lock fractions differing 4×; the data were all correct and two of the
three estimators were biased.** Settled 2026-09-11 by reproducing **all three** published numbers on one
loader, varying one factor at a time, then testing both estimators **against a synthetic signal with a
KNOWN locked fraction**.

| windowing | estimator | quantity | r39 bar 18–22 Hz | whose published cell |
|---|---|---|---|---|
| 20 s blocks | `R2 − maxfloor` | excess | **0.1309** | `cyclekind` (0.131) ✓ |
| 20 s blocks | `R2_deb` | excess | 0.5356 | |
| whole | `R2 − maxfloor` | excess | **0.3956** | `combsize` (0.357, own strata) |
| whole | `R2_deb` | grind total | **0.4948** | `modelrate` (0.501) ✓ |

**Factor decomposition: estimator ×4.09 · windowing ×3.02 · total-vs-excess ×0.98.**

- 🛑 **`R2 − maxfloor` is biased LOW by ~0.12 whole-stratum and ~0.22 in 20 s blocks**, at every p ≥ 0.1.
  **`R2_deb = √(max(R2² − mean(R2²_detuned), 0))` recovers the truth to ±0.04.** The reason is dimensional:
  **noise adds in POWER, so subtracting a floor in AMPLITUDE over-subtracts, and it worsens as power falls.**
  ⇒ **Use `R2_deb`. Never quote `R2 − floor` as an estimate — it is a conservative lower bound that
  degrades with sample size.**
- ⚠ **TOTAL vs EXCESS is NOT the explanation** (×0.98) — they agree to 2–5 % here, because the quiet stratum
  holds only ~10 % of the grinding stratum's in-band energy at a similar locked fraction. An orchestrator
  hypothesis that they differed was **wrong**.
- **Proximity control:** a *free* mode 0.08 Hz from the clock — where r39's ring actually sits (19.92 vs
  19.9997) — reads `R2_deb` = **0.018** over 182 s. **The lock is real, not mere nearness.**
- ⭐ **The number is ≈0.50**, and all three agents reconcile once each estimator's bias is restored
  (0.131 + 0.22 ≈ 0.35 · 0.396 + 0.13 ≈ 0.53 · 0.495). **Nobody's data was wrong.**
- ⭐ **Reconciling a 50 % locked OUTPUT with a 20 % command-side DRIVE share** — not a contradiction: a
  **phase-locked** drive accumulates **coherently** (amplitudes add) while random-phase drive accumulates
  **incoherently** (powers add). **The comb is a minority of the drive, over-represented in the response
  because it is the only coherent part of it.** Both measurements stand.
- ⇒ **At lock 0.50, perfectly removing the comb cuts ring amplitude by 1 − √(1−0.50) = ≈29 %, ~3 dB.**
  🛑 **TWO COUNTERWEIGHTS OF EQUAL WEIGHT:** (1) **V289 is ALREADY the flown version of "remove the
  coherent 20 Hz forcing" and the symptom got WORSE** — its relocated ring carries **0.000** camera lock
  and is **1.71×** r39's on **0.30–0.45×** the command drive. ⚠ **Confounded** (the notch also spent 30° of
  margin at 15–17 Hz), so not decisive — but it is the only configuration ever flown with no coherent
  forcing and it went the wrong way. (2) The 29 % assumes the locked energy **vanishes**; if the mode is
  rung by whatever broadband excitation remains at unchanged loop gain, the ring returns lower but
  non-zero. **Nothing measures that — only the transient test would.**

---

### 🛑🛑 THE ζ CORRECTION — EVERY SUFFICIENCY VERDICT IN THIS KIT WAS HOSTAGE TO AN ASSUMED NUMBER

🛑 **ζ = 0.029 was INHERITED, never measured. `cyclekind` MEASURED it from the ring's coherence decay:
ζ = 0.0091–0.0224 per build.** Lower ζ **raises** the phase-locked accumulation ceiling 1/(1−e^(−2πζ)),
so every "is this excitation big enough" verdict computed at 0.029 was **too harsh**. Re-swept ceilings
(command leg ÷ measured ring, at ψ = 0):

| route | build | ζ=0.0091 | ζ=0.0150 | ζ=0.0224 | ζ=0.029 (as previously quoted) | crossing ζ |
|---|---|---|---|---|---|---|
| r35 | V281r3 | 4.88 | 3.02 | 2.07 | *1.63* | 0.0503 |
| r39 | V282 | **3.64** | **2.25** | **1.54** | *1.21* | 0.0359 |
| r5e | V288 | 2.39 | 1.48 | 1.01 | *0.80* | 0.0227 |
| r62 | V289 | 1.64 | 1.02 | 0.70 | *0.55* | 0.0152 |
| **r63** | **V289** | **0.75** | **0.46** | **0.32** | *0.25* | **0.0067** |

⇒ **"NEITHER MECHANISM IS SUFFICIENT" is WITHDRAWN for V282, V288 and V281r3** — at measured ζ the command
side reaches 1.54–3.64 on r39, tolerant of ψ up to 49–74°. **Only r63 stays below unity at every measured
ζ.** ⭐ **`cyclekind`'s coherence-time measurement is now the SOURCE OF RECORD for ζ. Do not quote 0.029.**

⚠ **Two further reductions, both self-reported:** the cross-build contrast is **1.71×, not 2.20×** once
matched on speed × demand (r63's loud windows sit at v p50 12.6 vs 8.9 and |bar| p50 581 vs 243; demand
*was* matched at 51.5 vs 49.8) — 12 of 13 matched cells still above 1, and the equal-bandwidth check
passes (2.15–2.18 at 2/3/4 Hz). And the **initiator-vs-amplifier question is NOT settled on V282**: the
accumulation ceiling was what converted proximate delivery into origination, and it now bites only on
r63. The verdict rests on the **ζ-free** evidence instead — the comb not growing with the symptom, the
0.022 coherence collapse, the cross-build inverse relation, and the flat forcing against a ×98 response.

---

### ⭐⭐ THE ANSWER, IN THE FORM THAT SURVIVES ALL OF THIS

> **At ζ ≈ 0.01–0.03 with the loop de-damping, no identifiable excitation is NEEDED. The ever-present
> camera comb — constant across six builds — SUFFICES, and what varies is the DAMPING, not the drive.
> "What excites it" is the wrong question. The lever is ζ_eff, and that is EPS-side.**

⚠ **Two earlier phrasings are RETRACTED:** *"no excitation is big enough to be worth preventing"* **and**
*"removing it perfectly buys ~3 %, at most 8 %"*. Correctly: **the excitation is always there and cannot
be prevented, because it IS the camera clock — but it is a LARGER contributor than first reported.**
**FIVE** premises survive, each measured, each from a different agent or method: drive flat across builds ·
response varies ×98 on it · **the ever-present drive IS enough at measured ζ** · the ring is a rung mode
(not forced, not a limit cycle) · no discrete trigger and no road. **A sixth — "the drive does not track
the symptom within a route" — is WITHDRAWN** (biased estimator; debiased, the comb does grow, just ×1.3–2.3
slower than the ring).

🛑 **THE ONE RESIDUAL, AND THE ONLY TEST THAT CAN CLOSE IT: a TRANSIENT test, not a spectral one.**
**Interrupt or phase-step `modelV2.action.desiredCurvature` for ONE model frame and time the ring
envelope's decay.** A rung mode decays with its ring-down time (0.27–0.87 s, 5–17 cycles) and stays down
until re-excited; a regeneratively sustained one decays on the much slower closed-loop envelope or not at
all. **Fork-side, zero authority cost, zero lag, no flash, in scope under the 2026-09-10 amendment.**
Spec: `docs/specs/design/SPEC-COMB-TRANSIENT-TEST-2026-09-10.md`. **Nothing further in the steady-state
spectral class will settle it.**

---

### ⭐ THE ONE EXPERIMENT THAT CAN STILL CLOSE IT — and it needs the operator's SPECIFIC consent

`docs/specs/design/SPEC-COMB-TRANSIENT-TEST-2026-09-10.md`. **It is NOT the one-frame interruption** that
was first proposed — that was killed on two grounds, both computed: it decays the envelope only
**5.5–13.1 %** before drive resumes (d = 0.11–0.25 ⇒ hundreds of perturbations), **and it costs up to
50 ms of added group delay, which is exactly the class the operator forbade by name.**

⭐ **The replacement inverts it: ADD comb rather than remove it.** Removal can move the ring by at most the
locked fraction (−30 %); **adding 2× moves it +125 %, because in-band powers add — ~16× the power for the
same seconds of driving.**

- **Manipulation:** at each `modelV2` publish, add `G·s[k]` — **the plan's OWN per-frame step, re-used and
  held**, not a synthesised sinusoid (the step distribution is violently heavy-tailed, median 0.09–6.45
  counts vs rms 12.6–63, so **a median-sized synthetic step under-doses ~10×**). `G` cycles 0→1→2 on a 2 s
  cadence. **Zero lag, proved**: `s[k]` exists at the instant frame *k* publishes — no state, no buffer,
  no filter ⇒ no group delay at any frequency, and authority is **increased**, not limited.
- **Discriminator:** fit `log A(G)/A(0) = α·log(1+G)`. **α ≈ 1 ⇒ INITIATOR · α ≈ 0 ⇒ AMPLIFIER · α ≈ 0.5 ⇒
  the band matters, not the clock.** Predicted A(G)/A(0) at lock 0.51: **1.00 / 1.59 / 2.25.**
- ⭐ **A fourth arm injects the SAME amplitude at a DETUNED clock (f_model + 0.5 Hz, still in-band).**
  That is what makes it an experiment rather than a dose ramp.
- ⭐ **It measures ζ_eff as a by-product** from the onset/offset transients — the number every sufficiency
  verdict in this kit is hostage to. **That may be worth more than the test's own answer.**
- **Power: ≈10–15 s of symptomatic engaged time. It FITS one short drive** (G = 1 entry point: +59 %,
  d = 1.13, ≈6 s/arm). ⚠ **G = 0.5 predicts only +28 % and needs 27 s/arm — no longer one drive.**
- 🛑 **SAFETY — THIS IS A PROVOCATION TEST. At G = 2 it deliberately makes the grinding ~2.25× LOUDER for
  2 s at a time. The operator WILL feel it, and he must consent to THAT SPECIFICALLY, not to "a test."**
  Bounds: ≈60 raw counts total against a 122-count slew cap so it cannot reach the rate limiter; same kind
  of signal already on the wire, tripled; no lag and no attenuation so path margins are unchanged;
  fork-side only, no flash, reverted by `G ≡ 0`. **If G = 1 is unacceptable to him, the test cannot be done
  in one drive and must not be attempted.**
- ⭐ **STEP ONE IS OFFLINE AND COSTS NOTHING** — synthesise the injection, verify the dose lands and that
  the detuned arm shows no rise at f_model, then push each arm through the byte-exact mirror.
  🛑 **But offline gives the x-axis ONLY:** *"`GI.simulate` is open-loop — it reads the measured wheel rate
  as feedback and cannot produce a plant response to a command never sent. Offline gives the x-axis
  exactly and NONE of the y-axis. Anyone quoting a predicted ring response from the mirror has mistaken
  the drive for the answer."*
- ⚠ **A positive α licenses BUILDING the comb fix; it does NOT predict the symptom goes away.** V289 is
  already the flown experiment for removing the 20 Hz forcing, and the grinding relocated and got worse.

---

### ✈ NEXT — in order
1. **Operator flashes V282** when he chooses to. Nothing is pending on the car.
2. 🛑 **Any future build is scored on max Ms over 12–26 Hz, pre-registered across the whole band.**
   A single-frequency notch is the V289 trap. **Option C (`docs/specs/design/DESIGN-V290B-2026-09-09.md`)
   must be re-scored on that criterion before it is cut** — its 21.5 Hz Q1.5 notch was designed against
   the old single-frequency framing.
3. ⭐ **THE TOP OPEN ITEM IS AN INSTRUMENT, NOT A LEVER: the IMU.** Every proxy used to date is a CAN
   channel from *inside* the steering system, so none can say whether the residual excitation is **road,
   rack or motor**. Cached for one route only. **Extract it corpus-wide before designing anything.**
4. **The reference-side class is UNTESTED and re-opened** — but a correctly-sized reference filter
   **still could not separate (B) from (C)**, since a reference-path filter never enters
   `1 + N(A)L(jω) = 0`. If it is revisited it needs a **fractional accumulator / error-feedback
   remainder word**; a `>>k` integer IIR is transparent at small amplitudes by construction.
5. **The fork-side comb reconstruction is legal and cheap but worth only 3–8 %** — and **unreadable from
   one drive** (the kit already judged ×1.22 unreadable). **Ride it free on a drive spent on something
   else; do NOT pre-register it as the thing under test.** Lag-free forms: slope extrapolation (0 ms) or
   trajectory-shaped reconstruction from `modelV2.orientationRate` (**lag-NEGATIVE up to 50 ms**).
   🛑 **A command LPF is forbidden by the operator by name** (2026-09-10) — the colleagues' filter costs
   100–280 ms of group delay and −32° to −59° at 1 Hz. **A measurement-side filter buys almost nothing**
   (80–97 % of the command's ring is setpoint-derived; residual cmd↔angle coherence 0.022).
6. **Standing: the golden model still lacks the LKAS rate-PID stage.** Contract re-verified unchanged at
   this close-out — **90 symbols**, `_self_check()` + `_demo()` stdout 2,512 B sha256
   `740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d`.
7. **`0xC61C0/C2/C4` still has NO lineage entry** despite 12 live readers across 249 images.

**Session reports:** `rlog-tools/studies/grind/{FORCED-VS-LIMIT-CYCLE,COMB-VS-ECHO-SIZING,OUTER-LOOP-ID,BURST-ONSET-TRIGGERS,MODELD-CADENCE-VS-RING}-2026-09-10.md`
· `docs/traces/TRACE-2026-09-10-command-intersample-zoh.md` · `docs/research/OPENPILOT-EXCITATION-SOURCES-2026-09-10.md`
· handoff `docs/handoffs/2026-09/HANDOFF-2026-09-10-THE-EXCITATION-CENSUS.md`

---

> 🛑 **SUPERSEDED 2026-09-10 — the decision box as it stood after the V289 drives.** Kept for the
> V289/V290 detail, the FLASH TARGET block and the cumulative-delta pointers. **Its "reference-side class
> is exhausted" framing is WRONG — see CORRECTIONS 1 above.**

### V289 rev 1 — the verdict, the operator's words first
**Operator, 2026-09-09, after two routes (`…00000062--1c7daa54e8`, 975 s / 619 s engaged; `…00000063--1d4b188022`,
707 s / 588 s engaged): "Grinding is still an issue."** V289 rev 1 = V282 + a Q14 TDF-II notch cave on the
clamped LKAS rate-loop output (20.036 Hz, Q 3.0; hook `0x2A174` → cave `0xC4C00`) + the feedback lag pole
`0xC63E8/EA` 923/1560 → 875/2301 (16.5 → 25 Hz). Image `f0c10c29…`, rwd `20fa1757…`.

🛑 **V289 hit its own pre-registered REVERT SIGNATURE.** It is a **MIXED** result, and the two halves must
be stated separately because the first pass at this box got the reading wrong:

1. **THE NOTCH WORKED — completely.** The 18–22 Hz band is **EMPTY on V289: 0 of 1414 present windows**
   (V282: 501 windows in 19–21 Hz alone; demand-gated 20 Hz prevalence ×34 down). Independent, no census
   gate at all: the pooled wheel-rate spectral peak in 12–26 Hz reads V282 19.92 Hz, V288 19.92 Hz,
   **V289 16.80 Hz (×10.3 above the band median)**. The notch did not *move* the 20 Hz line; it **removed
   the loop gain feeding it** (|N| = 0.011, −39.3 dB). [EVIDENCE — `rlog-tools/studies/grind/MODE-NATURE-V289-RECENSUS-2026-09-09.md` §1]
2. **IT RELOCATED THE RING TO A DIFFERENT, PRE-EXISTING POLE at 15–17 Hz** — one V282 *already carried*
   at |L| 1.13 with 30° of phase margin, which the notch skirt (−41.6°) plus the new fb pole (+11.5°)
   spent. **That one is the loop's own crossover.** Measured ζ **0.029 on both builds — the frequency
   moved, the damping did not.** Dominant line at the two operator bookmarks: 15.92 Hz (r62), 15.09 Hz (r63);
   demand-gated median 16.47 Hz [15.81–16.91] vs V282's 19.98 Hz.
3. **Not quieter; some episodes louder** (725–826 raw envelope on r63 vs V288's loudest 640), **shorter
   events but in trains** — one r63 episode re-fires every 1.5–2 s for 10 s, hands off, wheel nearly still.
4. **The cave was confirmed LIVE from the wire, not the label**: b5 duty 0.500 engaged on both routes,
   phase-locked to the 20 Hz wheel rate (coherence 0.55–0.99 in loud windows); b7 reads 0.95–1.00 on SCA = 0
   frames > 3 s after disengage — V289's own signature (V282/V288 read 0.00 there).
5. 🛑 **The V282-yardstick census (gate 18–22 Hz ≥ 40 raw) is BLIND to the relocated line.** Its "2.1–2.2 %
   presence" is a **gate miss, not an improvement**, and must never be quoted as a rate improvement across
   V282/V288/V289.

### THE TWO-OBJECT PICTURE — what the band actually holds
The widened 12–26 Hz band contains **two different lines, separable on LKAS DEMAND, not on speed**
(`MODE-NATURE-V289-RECENSUS-2026-09-09.md`; every pooled median that ignored this landed at a spurious
~14.8 Hz):
- **Low-demand line (idx < 5): 12.4–13.8 Hz**, falls with speed, ~4 raw of command amplitude, **at the same
  frequency on V282, V288, V289 and the Kp-LERP builds.** A road/plant line. Not the grinding mode.
- **High-demand line (idx ≥ 20): 20.0 Hz on V278r3/V280r2/V281r3/V282/V288, 16.2–16.7 Hz on V289**, at every
  speed bin 0–20 m/s, carrying 15–40 raw of command amplitude. **This is the grinding mode.**

### WHAT THIS SESSION CLOSED
1. **"The 20 Hz line is a PLANT MODE the loop de-damps" SURVIVES and is stronger.** The Kp-pinning is now
   confirmed **model-free at matched load**, and **the clamp explanation for it is FALSIFIED**. What broke
   is the *one-plant-one-pole* model, not the classification: no single LTI plant carries both V289's move
   and the Kp-pinning (best joint χ² 25.8, ζ wrong by 2–14×).
2. 🛑 **A FILTER'S PLACEMENT DECIDES ITS AUTHORITY COST, and the two placements are otherwise identical.**
   Forward (loop-output) and feedback placement of the *same* filter give **algebraically identical** return
   ratios — poles, ζ, Ms, PM, GM and the 7 Hz gate agree to **machine precision (max |pole difference| 0.000e+00)**.
   They differ **only** in the reference transfer, i.e. in capped-step transient authority: **pkR 0.78 → 0.98**.
   **V289's own design scored the feedback row and the build shipped the loop-output one; no blocker was ever
   recorded** — the design preferred the sum node on one physics argument ("the setpoint's 20 Hz kick still
   reaches the motor") and left the feedback hook explicitly open. **The ×0.91 authority price V289 paid was a
   price for the TOPOLOGY, not for the damping.** [`docs/review/ADV-V290-NULL-2026-09-09.md`,
   `docs/traces/TRACE-2026-09-09-v290-feedback-operand-hook.md` Q6]
3. **Both colleague hypotheses are FALSE.** **H1** ("the operator is switching between two torque-table
   points; scaling the map spreads them so resolution is lost") — the index quantiser sits **before** the
   assist map and is **map-independent** (1 index LSB = **16.126** raw `0xE4` counts on every build, using the
   live taper arm 255); its whole residual carried through the loop is 2.3–2.5 output counts at 18–22 Hz and
   is **identical in grinding and quiet windows**, while the measured torque there is 29–41 counts — **12–32×
   larger**. openpilot's only command-indexed table is the identity `[0,4096] → [0,4096]`. **H2** ("a 20 Hz
   stair-step command held 4 frames") fails again on the wire: 96–99 % of 100 Hz frames change; ±1-alternation
   and two-value 100 ms windows sit at ~0.000 in every stratum. ⭐ **The kernel of truth in H1: scaling the map
   raises loop gain per command count — a GAIN effect, not a resolution effect** (and V288 made every setpoint
   step ~11× finer with the grinding unmoved).
4. **The Kp/Kd schedule class is CAPPED.** Both schedules are indexed by the demand index at exactly
   **16.125736 wire counts per LSB** (Kd record `0xE511C`, X = 0/11/22/32; Kp record `0xE5378`). Because
   **roughly half of grinding seconds sit above the knot (idx 32)**, where every Y-only edit is byte-identical
   to base, the class ceils at **×2.1 ring improvement at infinite dose** — and setting `Y[0..2] = 0` (deleting
   D below the knot) blows the 7 Hz gate to 1.0604. **Moving the knot X is DOMINATED everywhere** by deepening
   Y — the X lever is closed. Under the operator's own gate exactly **one** record qualifies, S′ (Y0 = 112), at
   ×1.22. [`docs/traces/TRACE-2026-09-09-kp-kd-schedule-axis.md` + its scalecheck VERIFICATION section]
5. **Row S is not readable from one drive** — and the estimator, not the control, is why. The within-drive
   stratified contrast is **unbiased but 2.6× too imprecise** (confound-correction CI ×0.34–2.01 against a
   ×2.29 effect), and the two operator-facing channels are confounded **in the flattering direction**:
   on the base builds low-demand rings are already **41 % quieter (×0.585)** and **half as long (×0.500)**.
   A naive "the low-demand grinding got better" report would be reporting the confound.
   [`docs/review/V290-ROWS-READABILITY-2026-09-09.md`]
6. **The parametric hazard is measured SAFE for the schedule class** — the modulation row S could produce is
   15–50× too slow and 50–500× too shallow, and the measured `Kd(t)` trace through the byte-exact clamped
   mirror never pumped (decay ≥ V282's in 9 of 9). 🛑 **But a Floquet analysis of the UNCLAMPED electronics is
   NOT a sufficient parametric-safety argument for this loop** — linear reads ~2 % where the clamped mirror
   reads 0.42×. [`docs/review/V290-PARAMETRIC-HAZARD-2026-09-09.md`]

### CORRECTIONS OF RECORD, 2026-09-09
1. 🛑 **The first version of this box read V289 as "the line moved, the notch failed." That is WRONG and is
   corrected above: the notch removed the 20 Hz object completely; a *different*, pre-existing 15–17 Hz pole
   became dominant.** "Under adjudication" is withdrawn — the plant-mode verdict survives.
2. **The V282-census gate (18–22 Hz) is BLIND to V289's relocated line.** Re-census at 13–18 Hz, demand-gated,
   before any cross-build rate comparison.
3. **The notch cave keeps executing 1–3 s after SCA falls** (Honda's disengage fade leaves a decaying nonzero
   loop state). Score b5/b7 **engaged-only**, never on raw SCA = 0.
4. **The idx quantiser LSB is 16.126 raw `0xE4` counts, not 16.19** — the earlier figure used the superseded
   taper cliff-arm (254); the live arm is 255. Strengthens H1's falsification; changes no conclusion.
5. **`docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md` has no rows for `0xC63E8`/`0xC63EA`, `0x2A174`, `0x28F4C` or the
   Kd record `0xE511C`** — that index's stated coverage stops at **V108** and none of those cells was touched
   before V289. Their on-car and design record lives in `docs/BUILD-LINEAGE.md`'s V289/V290 entries. **Absence
   from the index is not evidence of untested.**
6. ⚠ **Two hook addresses appear for option C in the record and they are not interchangeable:** `0x29D72`
   (the fb **sum** `r26`, the first pass) and **`0x28F4C`** (the rate operand `x`, ±12000-bounded — the final
   choice; it sits below the engagement guard so the cave runs on every tick and needs no sentinel seeding).
   `docs/review/V290-DECISION-TABLE-2026-09-09.md` §1.2 still quotes the earlier one.

### ✈ NEXT — in order
1. **Operator flashes V282** when he chooses to. Nothing else is pending on the car.
2. **If and when he relaxes the worst-case transient-authority floor (0.928 vs 0.95): cut option C.** It is
   fully specified and traced; its pre-registered revert signature is written down — a 15–18 Hz line in trains,
   grinding lower-pitched than V282's, a new 10–14 Hz line (C's sensitivity there is ×2.0 V282's), or audible
   HF hiss (rms |R| 30–500 Hz ×1.91). 🛑 **If C's 16.5 Hz pole is audible, the whole loop-shaping class is
   closed — both placements, both bases, and the Kd schedule — and V291 must come from outside it.**
3. **The fork-side echo lever stands regardless** (`docs/research/STARPILOT-FORK-COMMAND-PIPELINE-2026-09-07.md`):
   openpilot's unfiltered 100 Hz angle measurement is what makes the command's own 20 Hz line an echo of the ring.
4. **Standing open item — the golden model still lacks the LKAS rate-PID stage.** Verified unchanged and passing
   at this close-out: **90 symbols**, `_self_check()` + `_demo()` stdout 2,512 B sha256
   `740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d`. To close the gap it would need: the
   **E-former** (`E = 32·setpoint − feedback`, feedback = two-sample sum, DC 30.89, through the `0xC63E8/EA` lag
   pole), the **P and D terms** (`P = E·Kp>>8` with the Kp schedule `0xE5378` indexed at 16.126 wire counts/LSB;
   D on the *error* with clamp `0xC61B6`), the **sum clamp** `0xC61BE`, the **per-variant gain LERPs**, and the
   5.05 Hz output lag `0xC63EC/EE` — plus a hook point where a cave filter (V288's pre-filter, V289's notch,
   V290-C's operand notch) can be inserted at either placement. **Do not add it piecemeal**; the 90-symbol +
   sha256 contract must be re-run on any edit.
5. **`0xC61C0/C2/C4` (row 19 of the V282 delta) still has NO lineage entry** despite 12 live readers across 249
   images. A tracer task is owed before the next authority change.
---

> 🛑 **SUPERSEDED 2026-09-09 — the decision box as it stood before V289's first two drives.** Kept for
> the pre-flight spec/design detail (adversarial verdicts, risk statement, cell-level diff) the box
> above trims; the "ON THE CAR" / "NEXT" lines below are stale — see the live box above.
>
> **BUILT, UNFLASHED, FLASH CANDIDATE: V289 rev 1 = V282 + a notch code cave on the clamped loop output + two calibration bytes (feedback lag pole).**
> `39990-TVA,A160-V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP-0x13000-0x100000.rwd`
> rwd sha256 **20fa175721eb9712cd9aada27c6ecc84e43108fcdd0c21d387b80db4a105625c** · image `_v289_…_plain_image.bin` sha256 **f0c10c29752d2b9bc4ec510800cd4de58166ebbb87f05613b5ee8e7af339a3ed** · script `analysis-2020accord/builds/v108_plus/build_v289_tva.py` (FAST 2 s / `--full` 4 s; writes only with `ACCORD_V289_WRITE=rwd`). Diff vs V282: **185 bytes, 10 runs** — hook 0x2A174 (`ld.hu 0x73ee,tp,r7` → `jr 0xC4C00`), 0x14A cave exit 0xC4BD6 → 0xC4BDC, telemetry tail 0xC4BDC–F7 (28 B), notch cave 0xC4C00–8B (140 B, 52 instr), cal 0xC63E8 923 → 875 and 0xC63EA 1560 → 2301, CRC 0xC4FFC AND 0xC6FFC (two blocks — the fb-pole cells live in the cal page). Exactly one V289 rwd on disk.
>
> ### WHAT V289 DOES (all read from the built image)
> 1. **Notch on the clamped loop output S** (r12 at 0x2A174, the value after P+D and the per-variant gain LERPs, clamped ±15360 by 0xC61BE), BEFORE the 5.05 Hz output lag: Q14 TDF-II, b = [16048, −31842, 16048], a = [16384, −31842, 15712], first-order error feedback (remainder word) so DC is EXACTLY 1 (254/254) and constants settle to exactly X; realised centre **20.036 Hz**, −3 dB 16.98–23.64 Hz, Q 3.007, −47.6 dB at 20.05 Hz; output clamped to ±cal(0xC61BE); state gp-0x6c44/−0x6c40/−0x6c3c, FLAG halfword gp-0x6c3a (12-byte run, censused free by raw scan incl. byte forms + Ghidra, boots to 0). Every route passes the hook every tick (disengaged S = 0 → state decays), so no sentinel init (switch in the script, off).
> 2. **Feedback lag pole 0xC63E8/EA 923/1560 → 875/2301**: 16.53 → 25.03 Hz, DC 30.891 → 30.886 (held), +11.8° of phase at 20 Hz, +7.6° at 7.3 Hz, +4.4° at 3.9 Hz. Never moved in 285 images.
> 3. **Telemetry 0x14A byte 4: b5 = sign(S − y) (the notched-out component), b7 = |S − y| ≥ |y| (comparator)**; b4/b6 = V282's r24 comparators kept as positive controls; b3 as V282; b0–2 stock. Computed at 1 kHz into one FLAG halfword, ORed in atomically by the 100 Hz tail (mask 0x5F).
> Kp 248 flat, Kd 128, the map, tapers, D clamp, sum clamp, r26 clamp, the 427 tap: byte-identical to V282.
>
> ### WHY THIS CLASS — what the V288 drive proved (rlog-tools/studies/grind/{V288-QLIVE,V288-MARKS,GRIND1-CENSUS-V288}-R5E-2026-09-08.md)
> - V288's cave ran (b4.5 = sign(y_model) on 99.5 % of engaged frames) and did what it was sized to do: D-clamp bind duty ×0.03 on the same route. **The grinding did not move**: same 20.0–20.4 Hz line at all three bookmarks (mark 3 louder than any V282 episode), 258 vs 239 episodes/h, envelope p50 126 vs 127, f 20.06 vs 20.03 Hz, rung-bell ratio 2.41 vs 2.25, no new line > 22 Hz [EVIDENCE, V282 census pipeline reproduced exactly]. ⇒ **the reference-side class is exhausted**. (V288's +1 rounding fix also makes it a unit-slew follower below 16 counts — irrelevant to the outcome.)
> - **Mode nature (9 routes, 5 builds, 529 episodes): a PLANT MODE the loop de-damps.** f 20.03–20.08 Hz on every build while Kp ran 248 → 696; +0.4 Hz with gain; ζ 0.036 → 0.019 with gain while staying stable; ζp ≈ 0.05 with the loop spending ~30 %. A −180°-limited crossover predicts −2..−4 Hz and instability above Kp ~350: falsified. Plant rate/T: ×1.7 bump 18–21 Hz, flat phase −85..−100° over 15–23 Hz [EVIDENCE]. The record's "PM 35–60°" was the un-removed 3.9 ms stream offset (+28° spurious lead).
> - **Loop phase at 20.3 Hz, byte-exact electronics (V282):** output lag −72.4°, fb pole −47.3°, two two-sample sums −7.4°, one tick −7.3°, D lead +61.6° ⇒ −72.6°; the plant supplies ≈ −100°. Both lag filters sit INSIDE the rate loop and had never been touched (`docs/traces/TRACE-2026-09-08-rate-loop-lags-and-inloop-filter-hooks.md`). The V287 design doc's reason for striking the fb pole ("|fb| multiplier at 0x2A1E6") was a misread: 0x2A1E6 is y × the engagement ramp gp-0x69b0.
> - **Ranking (`docs/specs/design/DESIGN-20HZ-DAMPING-LOOPSHAPE-2026-09-08.md`):** the PAIR (notch + fb pole 25 Hz) is the only row neutral on every gate (7 Hz gate 1.005 vs 1.003; 3.9 Hz +0.6°; |L| < 5 Hz within 2 %); a bare notch re-arms the 7 Hz strong-turn ring (gate 1.079); fb pole alone is a blind dose (verdict flips between fits); output-lag pole, every lead and the D filter are STRUCK. Predicted: ζ of the mode 0.019 → 0.024 on the census fit (Ms 3.8 → 2.0, min|1+L| 0.27 → 0.49), byte-exact step-ring ζ 0.016 → 0.038 (adversary B). **Not a cure: rings decay ≈ 1.7× faster and stop being sustained.**
>
> ### ADVERSARIAL PASS (FAIL criteria pre-registered in `docs/review/ADVERSARIAL-V289-PREREG-2026-09-08.md`, verdicts appended there)
> **A PASS · B FAIL on §B3, ACCEPTED BY THE OPERATOR · C PASS (docstring fixes, hashes unchanged) · D PASS.** B3: on a capped-frame command step the byte-exact closed-loop mirror gives peak wheel rate ×0.909 and peak accel ×0.929 (criterion 0.95) — the ring's own overshoot removed, t90 28 → 35 ms; steady-state ×1.00; open-loop peak torque into the motor identical for every step size. The design's "×1.00" row was the feedback-operand notch, not the built topology. Operator, 2026-09-09: *"accept rev 1 (sum notch)."*
> Residuals carried: on one plant fit the pair's ζ falls (0.022 → 0.016) while the notch alone holds → a NEW line at **22–24 Hz** is a second revert signature next to **14–17 Hz**; if the plant is smooth the build is Nyquist-unstable → a sustained ~16 Hz lower-pitch grind = revert; FLAG halfword transiently 0 for ~30 instructions per tick (preemption residual); fs = 1 kHz rests on the CAN dwell measurement; the register-indirect RAM residual common to every flown cave.
>
> ### ✈ RISK BEFORE THE DRIVE, and how it will be read
> Steady-state authority unchanged; capped-step transient peak ~9 % lower and ~7 ms later (accepted). New HF cost: ×1.48 rms noise into D from the raised pole (guarded by the 26–33 Hz statistic). **Revert to V282 if:** a new line at 14–17 Hz or 22–24 Hz, a sustained lower-pitch (~16 Hz) grind, or any new vibration on straight engaged driving. Reading: (1) liveness — b4.5 duty ≈ 0.50 engaged is ALIVE (zero-mean component; only its cross-spectrum with the 0x18F rate at the line is informative), b4.7 must rise at episode onsets (predicted 0.10–0.11 engaged at the 100 Hz instants, 0.12–0.37 in bookmark windows) — 🛑 **b4.7 reads 1.000 while DISENGAGED (0 ≥ 0): score engaged-only**; (2) the 18–22 Hz line's decay rate and duration at the operator's bookmarks vs r5e_v288/r39 (the census pipeline `grind1_census_v288_r5e.py` takes a new route in minutes); (3) the 13–17 and 22–24 Hz bands; (4) the operator scores the grinding.
>
> ### ✈ NEXT — in order (STALE — see the live box above)
> 1. ~~Operator decides on V289 rev 1.~~ Decided: flown 2026-09-09.
> 2. ~~Read the first V289 route~~ — done: `V289-QLIVE/MARKS-R62-R63-2026-09-09.md`.
> 3. openpilot-side echo lever unchanged (`docs/research/STARPILOT-FORK-COMMAND-PIPELINE-2026-09-07.md`).
> 4. Golden model: `lkas_sum_notch` and `lkas_fb_lag` added (contract 90 symbols, hash unchanged); the rate PID stage itself (E former, P/D, the per-variant gain LERPs 0xCBB54/0xCBC34/0xCBBC4/0xCBAE4) is STILL absent — next model task.
> 5. Open: 1 kHz task slack (no period field, no overrun counter found); outer-loop PM; `0xC61C0/C2/C4` intent; the 12 bytes at 0xC4FF0.
>
> ### CORRECTIONS OF RECORD (2026-09-08/09, pre-drive)
> 1. "Grind #1 is the LKAS rate loop's crossover resonance" → it is a **plant mode the loop de-damps**; the loop owns ~30 % of its damping at Kp 248. (⚠ now itself under adjudication — see the live box.)
> 2. "PM 35–60°, Ms 2–3" (creep20) → an artefact of the 3.9 ms inter-stream offset; the loop sits at |L| 0.8–0.95, −170..−185° at 20.3 Hz.
> 3. V287 design doc: 0x2A1E6 multiplies y (the output-lag result) by the engagement ramp gp-0x69b0 — not |q32(H_fb·rate)|; the fb pole is a phase element.
> 4. V288 spec: "15 ms at zero crossings" → ~3 ms by construction (the +1 fix); "ΔE 3936 → 224" was in raw 0xE4 counts (sp counts: 1088 → 96, ×11); the D clamp 0xC61B6 = 10240 binds at |ΔE| ≥ 640 and is never reached by the filtered steps.
> 5. A tracer's "free RAM" verdicts by halfword sweep were wrong on 2 of 3 runs (gp-0x68b0 has 19 byte accesses; gp-0x6ab0 boots to initialised data) — a free-cell census must include ld.b/st.b/bit-op forms (the builder's and adversary D's scanners do).
> 6. The dongle's route counter collides: `r5e_v288` (cache key `5e2`) is the 2026-09-08 V288 route; `r5e` is a 2026-08-06 route.

---

