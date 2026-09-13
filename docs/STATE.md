# STATE — living current state of the kit

> 🛑 **READ THIS BOX FIRST.** Everything you need to make a decision is in this box. The superseded decision
> boxes and the 84 finding/correction blocks that used to follow it are ARCHIVED under `docs/archive/` (pointers
> at the end of this file). They are a record, not a briefing; nothing was retracted by the moves.

## ✈ THE DECISION, IN ONE PLACE — updated 2026-09-13 (**V292 BUILT — the loop-opening dose, byte-exact — and CLEARED as the flight candidate by the orchestrator over one dissent; V291 SUPERSEDED-DO-NOT-FLASH. Nothing flashed, nothing sent.**)

**ON THE CAR: V282** — route `…0000006c` (2026-09-12, 62 segments, mostly motorway, 326 s engaged in the 8
segments read) attributed from the tap (b7 → 0.000 after disengage, b5 engaged 0.156), not the label.
**Flash target, if the operator chooses to fly the loop-opening class: V292** (rwd sha256
`6d2784b5e27e2f21a909f552ac786f74fe28991dcbc275bf7ae03fb61f9fc20c`). V291's rwd and image carry
`SUPERSEDED-DO-NOT-FLASH-` on disk. The flight is the operator's decision; the read and the revert signatures are below.

---

### 🛑🛑 V292 — WHAT IT IS, WHAT THE PASS SAID, AND THE VERDICT

**V292 = V282 + 69 bytes:** V291's three cells — `0xC63E8/EA` 923/1560 → **962/958** (the LKAS rate-PID
feedback lag pole 16.53 → **9.94 Hz, DC 30.89 held**), `0xC6446` 5244 → **4725** (the r24 engaged arm,
−9.9 %, a partial revert of V84's Lever B), the 0x14A cave's **b3 = sign(fb state gp-0x3d30)** — plus a
**52-byte cave at 0xC4C00** hooked at the filter's own first multiply (`0x28F8E` `mul r16,r7,r0` → `jr`)
that computes the filter's two floored terms with **error-feedback remainders** (halfwords at
gp-0x6D74/6D72; `t = mul + rem; rem' = t & 0x3FF; step = t sar 10`), so the integer filter's mean equals
the linear filter's at every amplitude (V291's own floors leaked a constant −32 count feedback bias, one
permanent phantom setpoint count). Forward path byte-identical (map ×6, Kp 248, Kd 128, Ki 0, clamps, ×6
gain, output lag; peak 2505). rwd **`6d2784b5…fc20c`** · image **`d1128232…aef33`** · script
`analysis-2020accord/builds/v108_plus/build_v292_tva.py` · design
`docs/specs/design/DESIGN-V292-FBLP-CAVE-2026-09-13.md` (+ errata) · prereg and verdicts
`docs/review/ADVERSARIAL-V292-PREREG-2026-09-13.md` · lineage entry · page
https://claude.ai/code/artifact/19038e6d-729b-4a79-ba3b-a07aeefcc067.

**CLASS — genuinely new in the V38 → V292 arc: OPEN THE RATE LOOP ABOVE ~8 Hz.** Every prior in-loop
lever shaped the loop AT the mode and returned a null under the authority gates; V291/V292 lower the
servo's feedback bandwidth so the loop stops acting where the grinding object lives, pay the 7.3 Hz gate
with the r24 cut, and (V292) keep the integer arithmetic faithful to the linear design.

**Predicted (byte-exact z-domain, 121-fit family, r24 folded at the wire-settled effective arm κ 0.449):**
max |1/(1+L)| over 12–26 Hz **19.4 → 3.6 unfolded / ×3.7–5.2 folded** (the record's fold omitted the motor
gain K and over-weighted r24 ×6.13 — pessimistic; corrected folded f0 **18.4 Hz**, clear of 15–17),
sensitivity at 20.3 Hz **×0.34**, ring **×3.3 shorter** (half-life 170 → 52 ms), PM +39 → +57°, GM
1.15 → 1.55, 0/121 unstable, 0/121 fits gain a ζ < 0.05 pole, transient authority UP (pkR 1.026 worst,
overshoot ×1.21), steady state ×1.000 at ±330 and ≤ 2 % at ±33, |T(3.9)| ×1.07, 5–9 Hz bump 0.91.

**REPLAY PREDICTION ON THE OPERATOR'S OWN RECORDED EPISODES** (`rlog-tools/studies/grind/V292-REPLAY-PREDICTION-2026-09-13.md`; byte-exact closed loop, 10 loudest r39/V282 grinding windows × 23 plant fits, disturbance recovered by causal inversion so the V282 arm reproduces every recorded window exactly; positive control: the mirror matches the recorded 427 ring to a 12.8 % median): **V292 delivers ×0.55 [0.54, 0.57] of V282's 18–22 Hz ring amplitude (×0.71 on the freshest route r6c) and ×0.29–0.36 of the mode's ring-down time** (free half-life 108–197 → 39–71 ms; linear closed-loop ζ 0.02–0.04 → 0.07–0.14); the 6–9 Hz strong-turn ripple ×1.03 pooled on r39's loaded turns and ×0.94 on r35's (3 of 15 fits above ×1.05, worst ×1.10 — the high-authority tail); delivered torque outside the ring bands ×0.999–1.000; **the 9–18 Hz shoulder ×1.09–1.11 on r39 and ×1.17 on r6c's own loudest 12–17 Hz episodes (worst fit ×1.36)** — far below the linear model's ×1.99 worst case. The r24 fold barely matters at these episodes (ring ratio 0.554 folded vs 0.534 unfolded); the gp-0x6806 deadband premise cannot reach them (|y| p10 2963 ≫ 102). Two defects in the record's mirror `grind_incident_r35.simulate` corrected on the way (one floor where the bytes have two; a float output lag) — neither moves the ring. **A model prediction on the fitted plant family, not a drive.**

**ADVERSARIAL PASS (four independent agents, FAIL criteria written before the image existed):**
- **A arithmetic PASS** (cave decoded independently; mean gain exact; DF gain 0.9995–1.0009 and phase
  ≤ 0.16° at A = 1…24 — more faithful to the linear model than V282's own filter) · **C build audit PASS**
  (independent rebuild reproduces both hashes; 17/17 mutations caught; write guard; V291 renamed) ·
  **D interlocks PASS** (the remainders have exactly the cave's accessors plus the boot copy loop that
  zeroes them; every interlock cal byte-identical; the hook's r7/r9 are live-in and replicated).
- 🛑 **B: FAIL on ONE clause only — the byte-exact steady state at sp = ±3 setpoint counts against the
  LINEAR V282 chain (×0.78–1.16, 20–21 of 21 fits outside ±1 %)** — every other clause PASS, no instability.
  B2 showed why: the loop has five floors and the cave repairs one; **the linear chain is a surface no
  integer build can sit on at 1-count demand — V282 itself reads ×0.96 / ×0.72 against it.** Against
  byte-exact V282, V292 reads **×1.0000 at +3** (median) and has the smallest sign asymmetry of the three
  builds (×0.89 vs V282 ×1.33, V291 ×1.41); the absolute spread is 0.22–0.33 deg/s. B2: *"I would not defend
  a do-not-flash on physics here"* and *"that is a change of criterion after the fact, and I am not making
  it"* — both recorded.
- ⇒ **ORCHESTRATOR'S VERDICT: CLEARED as the flight candidate**, by the kit's standing rule that a check
  which condemns the flown build is a broken check (the amended clause condemns V282). The dissent, the
  sp = 3 numbers, and two premises are on the page: (a) gp-0x6806's state while engaged (B2 §7.2: if 0,
  a ±102 deadband on y zeroes sp = 3 on every build — the record's V103/V104 evidence says it is 1 while
  engaged, the 55 Hz notch and the r24 rung both key on it and were measured live; BELIEF); (b) the 9–18 Hz
  sensitivity shoulder (byte-exact ×1.33–1.70 of V282's at 12.85 Hz, well damped, in absolute terms inside
  what V282 carries symptom-free at 16–18 Hz) — pre-registered as a REVERT SIGNATURE with numbers, not a
  gate (reasoning in the prereg). Also from B2: B5 is fragile in phase (V292's 5–9 Hz worst reaches 1.0 at
  −5.9° of loop-phase error vs V282's −31.6°), and the loop closes ~6× sooner after engage at near-zero
  wheel rate — correct behaviour, but the most likely thing the operator could feel that no gate scores.

**THE READ (one ~20 s hands-off creep episode):** 18–22 Hz envelope **half-peak** decay ≈545 → ≈183 ms;
T-vs-0x18F-rate cross-spectrum phase **−14° ± 4° at 10 Hz** over 16 s of creep (the LANDED check);
**0x14A b3 DUTY 0.47–0.50 at every amplitude** (V282-pole 0.54–0.70; V291 pinned at 1.0 below 3 counts;
**idle duty 0.000 with the wheel still = the cave is live**), conditioned on |rate| ≥ 2 counts and mean
rate ≤ ~1.5 deg/s; b5/b6 duties the r24 cut's control (~−10 %). **The null:** decay not below 1.23× V282's
while the phase HAS moved ⇒ the object's damping is not set by the rate loop's return ratio ⇒ the whole
in-loop class is closed. **REVERT IF:** the 6–9 Hz strong-turn ripple returns (F7 ≥ 2/100 s or tap
ripple/level ≥ 0.25); new roughness or a line at 10–18 Hz (worst-fit sensitivity ×1.3–1.7 of V282's, peak
near 13 Hz; the integer cycle near 15 Hz); a 22–30 Hz line; the grinding unchanged; a darty/loose
lane-centring feel; a one-sided pull at rest. **`AccordCurvatureLead` must be OFF** (with it ON, B5 fails).

**V291 (C10), the same dose without the cave:** built, NOT CLEARED by its pass (B4 ×1.34–1.80 at sp = 3 from
the coarser feedback quantum; B3 re-scored PASS once `biv` settled the r24 arm), **SUPERSEDED-DO-NOT-FLASH
by V292** the same day. Its record stays in `docs/BUILD-LINEAGE.md` and `ADVERSARIAL-V291-PREREG-2026-09-13.md`.

---

### ⭐⭐ THE MEASUREMENT THAT SET THE DIRECTION — with the loop OPEN there is NO 18–22 Hz object

`OPENLOOP-RING-DAMPING-2026-09-13.md`, 35 routes, 4,759 s lateral-disengaged (STEER_REQUEST = 0, which
opens the rate loop AND the engaged-only r24 lane): the pooled spectrum carries **no resonance in 16–26 Hz**
(prominence 1.00 / 1.25, below a no-mode control); a synthetic mode of **ζ ≤ 0.03 at the same energy WOULD
have been found** ⇒ **ζ_open ≥ 0.05 or non-modal**. Engaged on the same routes: ζ 0.034–0.036; **V282 alone
0.0164 [0.0126, 0.0222]** at 20.01 Hz. Load-matched amplitude OFF/engaged **0.21** (×4.5; mode-specific
×2.5–3.2 against the 26–34 Hz neighbour band). **V289's relocated 15–17 Hz ring is ALSO engagement-gated**,
and **V289's notch — an in-situ loop-opening at 20 Hz — removed the 20 Hz mode outright.** 🛑 Limit: opening
the loop also removes the LKAS excitation, so "no object" has two readings (ζ_open ≥ 0.05, or a low-ζ mode
only LKAS torque excites); both say the same thing for a build. **Estimator corrections:** the free-decay ζ
behind DESIGN-V290B §A.2 returns 0.036–0.040 for NO mode (void); coherence-time ζ is sound only for 0.02–0.05;
the 12–14 Hz "road line" is not a resolvable resonance. **Unit trap:** the ring is **~16 LSB on the 0x18F
RATE channel** (1.98 deg/s); "0.17–0.28 LSB" was the ANGLE channel — the feedback leg is LINEAR (0.879 of the
T ring; quantiser kicks 0.35 %).

### 🛑🛑 THE DESIGN LAW, AS OF 2026-09-13

> **The grinding object is a creature of the closed engaged loop. The lever is to make the LKAS rate loop
> stop acting in 12–26 Hz while keeping its action below ~8 Hz — and the price of that, in this loop, is
> paid at three places: the 7.3 Hz gate (the r24 pump arm), the 9–18 Hz sensitivity waterbed, and the
> feedback quantum at tiny rates. Score every candidate on ALL THREE, pointwise over 3–30 Hz, r24-folded,
> byte-exact — not on a band maximum.**

- **The fb-pole-down class does everything except the 7 Hz gate** (`DESIGN-V291-FBLP` body): Ms 12–26
  19.4 → 1.4–5.1, PM/GM up, pkR UP, 0/121 unstable, no new lightly damped pole — and fails gate73 at every
  dose because **94 % of the gate damage is phase lag at 7.3 Hz priced against the FIXED r24 arm**. Closed
  axes: fb × Kd (dominated; Kd ≥ 160 destabilises 77–112/121), 2nd-order fb LP (up to 70/121 unstable),
  output-lag pairing (93–109/121 unstable), the P-path-only split (passes five gates, hollows out 3–4 Hz:
  |T(3.9)| ×2.4 — parked). Readability floor ×2.43 (from the record's CI ×0.34–2.01): C12 (12 Hz) cannot
  observe its own edit; C10 and C8 can.
- **The r24 lane, traced and measured** (`TRACE-2026-09-13-r24-lane-transfer.md`, `B-OF-F-V282-2026-09-13.md`):
  r24 = −clip(deadband₃(trunc(clip(0.5·(bar[n]−bar[n−4]), ±5120)·g/1024)), ±8192), g = 0xC6446, 1 kHz, from
  the torsion-bar torque; **unit-weight sibling of the LKAS lane (gp-0x6b4c) at gp-0x6b94 ⇒ 1 : 1 at the
  motor.** On the wire: pure PUMP at 3–7 Hz (∠+170°), near-pure DAMPER at 18–22 Hz (∠+9…+15°), **73–86 % of
  the electronic 20 Hz damping**; gate73 improves monotonically with any r24 cut and the 20 Hz damping falls
  monotonically — **no sweet spot, and a high-pass on r24 is DEAD** (it adds lead where r24 already sits at
  +171°; HP 5/8 Hz re-arm the 7 Hz cycle). κ dispute open: effective ≈ 0.45× (b6 inversion, V281r3's
  cycle-gone), 0.10–0.20 (V289 bound), 1.45 (the record's pooled split). 10–14 Hz unidentified in every
  stratum. The gp-0x671d fault latch that would collapse r24 ×0.195 is UNARMED (5530 never reached on 4,653 s).
- **The LKAS lane's true path** (`TRACE-2026-09-13-lkas-lane-to-aggregator-and-ghidra-gap.md`): T @0x2A23C →
  gated copy **@0x2A2EA** → gp-0x6b3c → clamp ±0xC61B2 → ep-relative request array → **gp-0x6b4c** (unit
  weight) → aggregator → governor → comp → shaper → gp-0x6b98. **gp-0x6ad4 is a driver-torque tracking PID**,
  not the LKAS output. **0x2A508–0x2B421 was undefined and is an uncalled TWIN of the LKAS output path** —
  analysed and SAVED (functions 2086 → 2090); the 0x2B41C "forward" the record cites is dead; 0xC646C has
  5 live readers.

### FORK (`raayyymond-StarPilot` @ Dom, HEAD 305732c85) — one patch, UNCOMMITTED, OFF by default
`ModelCurvatureLead` (`selfdrive/controls/lib/drive_helpers.py`, wired in `controlsd.py` before
`clip_curvature`; toggle `AccordCurvatureLead` default OFF, `AccordCurvatureLeadGain` 0.75; tests in
`selfdrive/controls/tests/test_model_curvature_lead.py`): slope-continuous extrapolation of the 20 Hz
modelV2 staircase. Removes 63–66 % of the camera-locked leg but cuts the 0xE4 18–22 Hz band only **−2.4 dB
(r39) / −4.2 dB (r63)** (the plan's share is the limit), adds +0.9–2.5 dB at 5–18 Hz, |H| ≥ 1 everywhere
(no authority loss), a lead vs today's hold below ~3.5 Hz and a lag above it. **Design B (trajectory-shaped,
"lag-negative") FALSIFIED** — orientationRate is a different head and a worse predictor. ~−18 % ring:
unreadable from one drive; ride it free on a drive spent on something else. The operator's own uncommitted
SR-map refit (route 6c) in `latcontrol_vehicle_tunes.py` is untouched. The rate-plant FF is bandwidth-blind
to a 10 Hz inner loop (~2 % perturbation); `AccordTorqueKi` 0.30 → 0.15 is the conservative knob;
`AccordRatePlantFF = False` is NOT conservative (×2.4–4.3 steady FF).

### CORRECTIONS OF RECORD, 2026-09-13
1. `DESIGN-V290B` §A.2's per-build free-decay ζ are NOT measurements (estimator at the no-mode floor).
2. "The ring is 0.17–0.28 LSB" is the ANGLE channel; on the rate channel it is ~16 LSB.
3. "r24 is a 4-tap FIR on gp-0x6ada" — it is a lag-4 backward difference on gp-0x4f62; gp-0x6ada is a
   write-only output mirror. `grind_loop_shape.py` §G ("5244 → 512 improves both bands") is falsified on
   the car (V70 at 512 put grind #1 back at stock).
4. The record's "×33–72 engagement gating" is a presence RATE; the amplitude ratio is ×4.5.
5. The bar-to-rate phase swing is downward ~130–150° through a ~9.4 Hz mode, not upward 210°; the
   creep-vs-loaded 7 Hz difference was a selection artefact of gating on instantaneous |bar|.
6. `reference_accord_gp671d_arm_inverts…` (tracer store) is wrong to favour gp-0x6ad4; the 2026-08-01 memory
   is right (gp-0x6b4c); the 08-26 census memory needs the word "driver-torque". Neither edited — ask first.
7. `TRACE-2026-09-13-fb-lag-filter-bytes.md` §4: "P = product >> 7 at 0x29F18" is the I accumulator; P is
   `mul` @0x29E36 then `sar 0x8` @0x29E3E.
8. Two V850 opcode-field collisions worth a scanner rule: field 0x3C/0x3D is shared by Format-V jr/jarl and
   the 6-byte extended load (hw2 bit 0 discriminates); field 0x3F by ld.hu, mul and setfcc (a real ld.hu
   has hw2 bit 0 = 1). Reject any Format-V hit whose target is ODD.

### ✈ NEXT — in order
1. **The operator decides on V292.** If he flies it, the read and the revert signatures above apply and
   `AccordCurvatureLead` stays OFF. Score the band; he scores the symptom.
2. **If V292 flies and the 20 Hz object survives at ζ ≥ 0.05 with the loop's phase moved, the in-loop class is
   closed; if it goes and a 10–18 Hz roughness appears, the next lever is the shoulder's own (a lead at
   10–14 Hz costs 20 Hz; a V293 with error feedback through the output lag closes the sp = 3 clause but buys
   ~0.1 deg/s). Resolve gp-0x6806's engaged state and the deadband premise before spending on sp = 3 again.
3. **The IMU stays the top missing instrument** (road vs rack vs motor).
4. **The transient test** (`SPEC-COMB-TRANSIENT-TEST-2026-09-10.md`) is now second to the loop-opening
   result; keep it as the ζ_eff measurement.
5. Standing: golden model **90 symbols**, `_self_check()`+`_demo()` sha256
   `740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d` (2,512 B) — re-verified this close-out;
   `docs/BUILD-LINEAGE.md` (229 KB) and `BUILD-LINEAGE-PART1-LEVER-INDEX.md` (193 KB) are over the 150 KB
   soft target — split at the next close-out; `0xC61C0/C2/C4` still has no lineage entry.

**Session reports:** `docs/specs/design/DESIGN-V291-FBLP-2026-09-13.md`, `DESIGN-V292-FBLP-CAVE-2026-09-13.md` ·
`docs/review/ADVERSARIAL-V291-PREREG-2026-09-13.md` + `ADV-V291-{A,B,C,D}`, `ADVERSARIAL-V292-PREREG-2026-09-13.md` + `ADV-V292-{A,B,C,D}` ·
`rlog-tools/studies/grind/B-IV-AND-KAPPA-2026-09-13.md` · `docs/traces/TRACE-2026-09-13-{fb-lag-filter-bytes,r24-lane-transfer,lkas-lane-to-aggregator-and-ghidra-gap}.md`
· `rlog-tools/studies/grind/{OPENLOOP-RING-DAMPING,B-OF-F-V282,ROUTE-6C-ATTRIBUTION}-2026-09-13.md` ·
`docs/research/FORK-COMB-RECONSTRUCTION-2026-09-13.md` · handoff `docs/handoffs/2026-09/HANDOFF-2026-09-13-V291-LOOP-OPENING-BUILT-NOT-CLEARED.md`.
**The 2026-09-10 and 2026-09-09 decision boxes are archived in `docs/archive/STATE-ARCHIVE-2026-09-13-decision-boxes-0909-0910.md`** —
their excitation-census verdict (the grinding is an excited resonance; the camera comb is real at lock
≈0.50; the estimator and ζ corrections) still stands and is folded into the paragraphs above.

---


## 📁 **THE V279-ERA REFERENCE AND 84 FINDING BLOCKS (2026-08-30 → 2026-09-11) ARCHIVED 2026-09-13**

Moved to `docs/archive/STATE-ARCHIVE-2026-09-13-v279-to-v290-blocks.md` at the V291 close-out to keep this file
under its working target. **A record, not an instruction.** Nothing was retracted by the move; the decision box
above carries every correction that was still decision-bearing.

## 📁 **EARLIER BLOCKS (24) ARCHIVED 2026-08-30**

Moved to `docs/archive/STATE-ARCHIVE-2026-08-30-probe-audit-era.md` to keep this file under its
working target. **A record of what was believed then, not an instruction.** Nothing was retracted
by the move.

## 🗂 INDEX TO THE BLOCKS BELOW

| what you want | look for the block titled |
|---|---|
| the flight order | *FLIGHT ORDER — A CHOICE, NOT A SINGLE BUILD* |
| why V222’s ratchet is a risk | *THE 8× IS COVERED WHERE THE OPERATOR FELT IT — BUT NOT AT THE RATCHET* |
| what V228 is | *V228 BUILT — V222 WITHOUT THE 8×* |
| the audible side effect | *"V228 CANNOT MAKE ANYTHING WORSE" IS FALSE* · *THE 40–49 Hz LIFT IS UNAVOIDABLE* |
| **my own withdrawn claims** | *SELF-CORRECTION: THE ABSOLUTE "r24 DAMPS" LABEL IS DOWNGRADED* · *CORRECTION TO THE BLOCK BELOW — AND TO MY OWN r24 ANCHOR* · *CORRECTION: "V62’s lever CREATED grind #2" is NOT settled* |
| what measurement can and cannot do | *THE RATCHET BAND CANNOT BE SCORED BY BAND POWER* · *RING-DOWN COMPUTED* · *CROSS-BUILD EVIDENCE HAS NEVER BEEN PRICED AGAINST ROUTE VARIATION* |
| what is closed and will not be re-proposed | *THE CAL-LEVEL SEARCH IS COMPLETE IN EVERY DIRECTION* · *THE NOTCH IS NOW CLOSED* · *EXACTLY ONE BIQUAD* · *FOC CURRENT LOOP IS TRANSPARENT* · *LEVER A r26-HALF ONLY* · *r24 IS AT 94 % OF A STRUCTURAL PHASE CEILING* |
| what is still open | *THE TWO REMAINING QUESTIONS BOTH NEED A CAVE* · *OPEN OBSERVATION — an 11.4× residual* · *THE FRAME TEST IS INCONCLUSIVE* |
| the session narrative | *SESSION HANDOFF* (last block) |

---



## 📁 **EARLIER BLOCKS (22) ARCHIVED 2026-08-30**

Moved to `docs/archive/STATE-ARCHIVE-2026-08-30-probe-audit-era.md` to keep this file under its
working target. **A record of what was believed then, not an instruction.** Nothing was retracted
by the move.

## 📁 **EARLIER STATE (V204 → V208) IS ARCHIVED — with its closures kept here**

Split out 2026-08-30 at **138.6 KB**, against the ~150 KB soft target. The narrative, the numbers
and the retractions now live in `docs/archive/STATE-ARCHIVE-2026-08-30-v204-v208.md` — **a record,
not an instruction.** What that era CLOSED is kept below, because a closure is what stops a lever
being re-proposed:

| closed | verdict |
|---|---|
| the notch shelf | was cutting a **real 6–9 Hz damper 7.15× below the car**; fixed V214–V217 |
| the saturation census | **closed** — the last gate cannot fire; V207 retired **before** flight |
| `gp-0x6b70` saturation | **does not saturate**; V206’s best argument retracted |
| the command-gated-saturation model | **no mechanism exists** in this path — no gate rejects either |
| the 8 Hz ratchet notch | **stays rejected**; the friction lane is NOT "reverted to Honda" |
| two authority levers | **checked and closed**; a latent 18.52 Hz injector found silent |
| `0xC63AA` sensitivity | **41× understated** in the old record |
| the relay | a **SOFT** relay, curve **built at runtime** — unreadable from the image |
| `0xC63AE` sign | established **without a drive**; V206 built and priced |

🛑 **Tooling gotcha kept live, because it still bites:** `stock_fw_dump/code.bin` reads `0xFFFF`
at `0xC6CD0` because **V57 created that cell**. Do not use the stock dump as a stock reference for
post-V57 migrated cals — it hands you 65535 and a 0.08× "stock gain". `0xC646C`, `0xC61BE` and
`0xC64DE` read correctly from it.

## 📁 **EARLIER STATE (V184 → V202) IS ARCHIVED**

Split out 2026-08-30 at **173.6 KB**, past the ~150 KB soft target. Everything from the V202 notch work downward now lives in `docs/archive/STATE-ARCHIVE-2026-08-30-v184-v202.md` — **a record, not an instruction.** All of it is superseded: the candidate is **V222**, the ladder is V223–V226, and that notch was replaced at V208 and again at V217/V222.
