# HANDOFF 2026-08-05 — THE TWO-LANE RULE ANSWERS THE OPERATOR'S CENTRAL QUESTION

*(An earlier title of this file claimed grind #2 is grind #1's 2nd harmonic. That claim was retracted
within the session — see the headline. The filename is kept for link stability.)*

**Session type:** operator-directed global re-investigation. He asked for a step back from the kit's
accumulated analysis, a fresh read of the whole firmware, and a **V72** that fixes grind #1 without
introducing grind #2 **and** addresses the ratchet. He supplied two new flights: **V71B = route `54`**,
**V71C = route `58`**.

**Fleet:** 14 agents — 8 firmware (GhidraMCP), 6 data. Full reports are cited inline; the durable
findings are in `docs/specs/design/V72-DESIGN.md` and `memory/`.

---

## ★★★★★ THE HEADLINE — the operator's central question is ANSWERED

> *"Somehow one of our grind #1 fixes introduces a grind #2 … they feel like the same thing."*

**They are TWO separate excitations sharing ONE differentiator-fed lever, and that lever moves them in
OPPOSITE directions.** One knob; raise it and grind #1 falls while grind #2 rises. That is why every fix
for one has fed the other, and why they feel the same through the wheel.

🛑🛑 **A HARMONIC CLAIM WAS PUBLISHED AS THIS SESSION'S HEADLINE AND RETRACTED THE SAME SESSION.** An
agent measured **f_hi/f_lo = 2.003 [1.997, 2.008]** and concluded grind #2 **is** grind #1's 2nd
harmonic; the orchestrator promoted it to the design doc, this handoff, a memory file, the commit
message and the operator report. **It was a bad test.** A ratio of two narrow lines is a property of
their **marginals** — two *independent* lines with these marginals return **median ratio 2.048
[2.012, 2.072]** (orchestrator-verified by simulation). Harmonicity needs f_hi to **TRACK** f_lo: a
**SLOPE** of 2.0. **Shuffling the window pairing REPRODUCED the observed ratio** (2.238 → 2.227;
2.288 → 2.268), and every tracking slope **contains 0 and excludes 2.0** on four routes.
⇒ **The corpus's original finding — slope 0.173 [−0.92, +1.59], NOT a harmonic — is CONFIRMED, not
reversed.** Method rule recorded in `memory/feedback/measurement/feedback-a-ratio-is-not-a-tracking-test.md`.

### And the two-lane rule explains every build in the corpus
High-rate corner of both surfaces (creep, rate index 3000), gains read from the shipped images:

| build | **r24 high-rate ×** | **r26 high-rate ×** | creep grind #2 |
|---|---|---|---|
| stock · V69 · V70 | 1.000 | 1.000 | **none** |
| **V71B/`r54`** | **1.000** | **2.000** | **none** (0 bursts, max 61) |
| V62/V65 | **3.414** | 2.000 | **YES — worst in corpus** |
| **V71C/`r58`** | **3.414** | 1.500 | **YES — 3 events** |
| **V67/V68** | **3.414** | **0.250** | **none** |

> **Creep grind #2 requires r24 high-rate ≳ 3.4× AND r26 high-rate ≳ 1.5×. Cutting EITHER kills it.**
**Six builds, no exceptions.** Neither lane's multiplier predicts the outcome alone.
⇒ **Raising r24 to kill grind #1 feeds grind #2 UNLESS r26 is also cut.** Every previous attempt moved
only one. **That is the operator's question, answered.**

---

## 1. THE TWO FLIGHTS — the operator was right on all six calls

| | grind #1 (median `e_18-22`, engaged creep) | grind #2 | ratchet |
|---|---|---|---|
| **V71B/`r54`** | **545** — excluded lower from stock only at P = 0.044; **indistinguishable from V69 (P = 0.85) and V70 (P = 0.21)** | **ABSENT** — 0 / 646.4 s engaged, expected 10.16, **P(0) = 0.0000** | present, 171.5 s of episodes |
| **V71C/`r58`** | **223** — excluded lower from stock **P = 0.0006**; excluded HIGHER from V67 **P = 0.0215** | **PRESENT** — 7 bursts / 485.1 s, matching V62/V65's rate | present, **8,521 counts p-p = corpus record** |

**V71C better than V71B at P = 0.0000 — exactly the operator's own ranking.** His *"attenuated but still
present, I think I could still hear it"* on V71C and *"I definitely experienced grind #1"* on V71B are
both precisely right.

★★ **The only functional difference between V71C and V67/V68 is `0xC6444` (r26 arm 3072 vs 512), and
V71C is significantly worse on grind #1 AND has grind #2** ⇒ **the r26 cut is load-bearing.** Cleanest
single-variable result in the corpus.
★★ **grind #2 follows the GATE, not the driver's hands** — V62/V65 (ungated) burst in *both* arms at
equal rates (0.0444/s engaged vs 0.0430/s manual); V71C (gated) bursts **only** engaged (0.0478 vs 0.000).
⚠ **This contradicts the operator's recollection that grind #2 was worse WITHOUT openpilot.** The corpus
does not carry it. Likeliest reason: on the ungated builds it was equally present hands-on with LKAS off,
which is far more salient. His V71C observation is exactly what a gated design predicts.

---

## 2. 🛑 FIVE RETRACTIONS, FOUR OF THEM THE ORCHESTRATOR'S OWN

0. **"Grind #2 IS grind #1's 2nd harmonic" — RETRACTED, see the headline.** Published as the session
   headline and withdrawn the same session after a shuffle control reproduced the statistic.

1. **`0x454FE` is NOT falsified for the ratchet — the test was VACUOUS.** V71's bit5 measured
   `gp-0x67fa == 4` at **0/123,277** (r54) and **8/92,826** (r58), all eight an 80 ms burst **in park**.
   **State 4 never occurred while driving ⇒ V42's substitution never ran ⇒ a null by construction.**
   ★ What survives is stronger: the substitution **never runs on stock either**, so it is **structurally
   eliminated** as the 7.79 Hz ratchet's cause. ⚠ **[OPEN] tension:** V42 was confirmed on-car against the
   *hard-turn recovery* ratchet; if state 4 never occurs that fix could not have acted either.
2. **"V69/V70 dosed the wrong part of the curve" — REFUTED.** Measured operating point is **p50 = 104
   counts** (not the ~603 the orchestrator quoted, which was the median per-window WORST INSTANT). V70
   delivered 2.000× and V69 3.999× at the measured points and it did nothing.
3. **"Modulation depth ranks the corpus" — REFUTED on measured data.** Within-cycle depth over 2,330
   burst windows is **1.002 / 1.004 / 1.000** — the index never leaves the plateau. The parametric-pump
   family is now closed from the data side as well as the intervention side (V60).
4. **"V67/V68 showed zero creep grind #2" is a SHARED ZERO, not a result** — every non-V62 build reads
   0.0, including stock. Only V62/V65 and V71C have ever produced bursts.

⊕ **Also corrected:** grind #2's tail is **ENGAGED, not manual** (6/6 on the clean route, Fisher
p = 0.0025) — the torque/angle description of the corner was right, the arm was wrong.
⊕ **The axis scale is settled at 4.7121 counts per column deg/s**, three independent ways — the CAN
divisibility/quantile test, the regression on differentiated angle, and firmware disassembly of the
packers (`0x14A` packs `(-gp-0x6a56)>>3`; `0x18F` packs it unshifted). **P × G = 56.5**, physically
ordinary. The 0.58901 candidate is the right factor on the **wrong CAN copy**.

---

## 3. FIRMWARE RESULTS — the structural map

- ★★★★ **The engagement question is ANSWERED, and the operator's objection was correct.** The rate lanes
  read **ZERO** LKAS-domain signals; `gp-0x67fa` is a **fault/diagnostic** state machine (all 33 writers
  decompiled, ~20 guard conditions, **no** engagement cell in any); `gp-0x683c` has **1 read / 0 writers**
  image-wide. ⇒ **The engagement-dependence is PHYSICAL, not tabular** — base-assist damping is exactly
  zero below 35 km/h, so at creep the driver's hand is the only damping in the system.
- ✅ **`gp-0x67ac` — the vacuity gate — is PROVABLY always 0.** An 11-channel sticky-OR whose only trigger
  is `gp-0x617c[i] != 0`, written only for roles 6/7 of static cal `0xC4124`, which reads
  `00 00 05 00 05 05 00 00 00 05 00` **byte-identical across all 65 built images**. The reduced-sum branch
  is unreachable; every lever this kit has flown lives in the only branch that executes.
- ✅ **FactorC byte-confirmed:** `0xD27BC` X = [2240, 3840, 5120, 8960] = **[35.0, 60.0, 80.0, 140.0] km/h
  exactly** at 64 counts/km/h, **Y[0] = 0**. **No base-assist damping anywhere below 35 km/h.**
- ★ **The damper runs on task 5 at 100 Hz** ⇒ 37.6°/75.2° lag at 21 Hz (why V44/V47 were null against the
  vibration) but only **14.0°/28.0° at 7.79 Hz**. **V47 was tested against a target its own sample rate
  made unreachable.**
- 🛑 **PWM carrier corrected 8 kHz → 4.000 kHz** (PCLK is 40 MHz; the 80 MHz figure was falsified
  elsewhere in the kit and never propagated). Resolver/FOC ISR = 4 kHz ⇒ `gp-0x6ac0` = **30 × f_electrical**.
- ⚠ **Two BUILD-LINEAGE ledger errors:** `0xC6442`/`0xC61F6` attributed to V39 were **never written by any
  build** (V39's whole delta is `0x3AC78`); and **V71B/V71C carry NEITHER of V62's `sar` bytes** — those
  live in V62, V65, V71A only.
- 🛑 **The ratchet's Q is NOT measurable at any window length.** Q(2N)/Q(N) = **2.06** over 34 doublings.
  **The recorded Q ≈ 40 is a window artefact.** ⚠ And *"a hand on the wheel kills it"* does **not**
  generalise (p = 0.31 / 0.39 on the new routes) — though engagement-conditionality replicates at
  **p = 6.3e-13** (V71B), with manual hands-off **1/150** across both drives.

---

## 4. ⇒ V72 — BUILT, UNFLASHED. Spec: `docs/specs/design/V72-DESIGN.md`

**Calibration-only, three levers, plus the proven 68-byte probe cave (extent unchanged).**

| lever | what | why |
|---|---|---|
| **A** | gain_B m10 rec0/rec1 → **5244 ×4**; gain_A rec0/rec1 → **512 ×4**; 50/100 km/h records **stock** | **Reproduces V67/V68's engaged multipliers EXACTLY at 0–10 km/h at every rate index**, and is **exactly 1.000× at ≥ 50 km/h** — fixing V67/V68's only failure (highway). Puts V72 in the **safe row** of §1's table |
| **B** | FactorC Y[0..1] → **430/431**; FactorE Y[0..2] → **927**, both modes | The ratchet. **Derived, not chosen:** 430 is the largest value keeping the speed curve **monotone**, and `430 × 927 >> 10 = 389 < 512` ⇒ **no clipping**. **2.1–2.4× V47's dose**, whose under-dose was one of four conditions making its null uninformative |
| **C** | `0xC63A0` **1024 → 2048** | The damper's own weight into `FUN_00038148`. Same authority as raising the ceiling `0xD209C`, with **zero lockstep/DTC-0x1d exposure** |

**Probe:** liveness · **`gp-0x69a4 >= 512` and `>= 1024`** (★ `a`, the weight that has blocked every
r24-vs-r26 attribution for ~10 builds, never measured) · `|gp-0x6bd0| >= 64` (is Lever B in force) ·
`gp-0x6ac0 >= 512` (📋 pre-registered at **2.750%** engaged duty).
`0x454FE` = `B5` carried as **inert and UNTESTED** — not a fix, not falsified.

### 🛑 DISCLOSED RISKS — not bounded away
1. **V72's r24 value is the one V71C carried when it produced grind #2.** The r26 cut is the protection,
   and **V67/V68's cell — the row V72 occupies — is the weakest evidence in the 6-build table** (~42 s of
   engaged creep).
2. **V72 is UNGATED**, and grind #2 follows the gate ⇒ **if it appears, it will appear in manual too.**
   Not jointly avoidable with cal-only edits (a scalar gated arm cannot be highway-clean while dosing at
   creep). The operator has authorised manual-feel changes.
3. **Highway grind #2 is cleared on NO build.** Routes 54/58 show the corpus's highest 40-49/24-28 fraction
   at highway (1.57 / 1.32) at 121–136 counts — inaudible, zero bursts, but **P(0) = 0.54 / 0.47**.
4. **Not single-variable**, by explicit operator instruction. Separable by symptom and band: Lever A owns
   18–22 / 40–49 Hz, Lever B owns 7.8 Hz, and Lever B carries its own in-force readout.

### ★ THE FLIGHT INSTRUCTION — it is load-bearing, and it costs nothing
**Drive deliberate ENGAGED hard cornering at creep**: < 4 m/s, sustained driver torque ≥ 1200, |angle|
≥ 100°, **openpilot engaged**, for **~90 s**. The corpus has **essentially no unprovoked engaged corner
exposure** — V67 and V70 have **2 engaged corner blocks each**, P(0) ≈ 0.69. Ninety seconds takes the
power from ~25% to ~80% and settles grind #2 on one drive, whichever way it falls.

---

## 5. OPEN
- **`a` (`gp-0x69a4`) is unmeasured** — V72's probe measures it. Bounds so far: not vanishing (r26's
  mirror cleared 128 on 149 frames), and small above 30 km/h (0/32,388).
- **V42's hard-turn fix vs state 4 never occurring** (§2.1).
- **The ratchet's true Q** — unresolved, > ~50, or the line is non-stationary in-window.
- **`FUN_000757a2`'s 6-branch shared-index LERP cluster** — if its index is rotor angle it is a
  torque-ripple/cogging table, the first plausible home for the operator's *"micro-grinding as the wheel
  turns"*, which is separate from all three tracked symptoms.
- **Motor pole-pair count and gear ratio individually** — only their product (56.5) is pinned.
