# V72 — DESIGN

**Status: SPEC FROZEN — three levers, calibration-only. Build in progress.** Written 2026-08-04.
Read with `docs/STATE.md`, `docs/BUILD-LINEAGE.md` (**RULE 3 first**), and the V71 flight results below.

---

## 0. WHAT CHANGED THIS SESSION

### 0.1 🛑🛑 `0x454FE` — THE TEST WAS **VACUOUS**, NOT A FALSIFICATION. ORCHESTRATOR CORRECTION.

**An earlier revision of this document, and the orchestrator's report to the operator, both stated
*"`0x454FE` is FALSIFIED for the ratchet — V71B and V71C flew with it restored and the ratchet is
unchanged."* THAT REASONING WAS WRONG AND IS WITHDRAWN.**

**[EVIDENCE — V71's own bit5 rung, `gp-0x67fa == 4`, decoded from both flights.]**
Route 54: **0 / 123,277 frames.** Route 58: **8 / 92,826** — and all eight are a single contiguous **80 ms**
burst at **0.00 km/h, gear = PARK, `latActive` = 0**, i.e. a key-on transient. Every 10-second block on
both routes reads **exactly 0.000000** (108/108 and 81/81).
⇒ **`gp-0x67fa` was NEVER 4 while either car was driving.** The V42 substitution fires **only** in state 4.
⇒ **The lever was never in force on either drive. Disabling something that never runs cannot change
anything, so the null carries NO information about the lever.** This is a **null by construction** — the
same class as `0xC6444` on gateless builds, and exactly what the kit's own conditional-null catalogue
exists to catch. **The probe caught it; the prose had already called it a falsification.**

★★ **What DOES survive, and it is stronger than the claim it replaces:** since state 4 never occurs while
driving, **the state-4 governor substitution never runs on STOCK either** ⇒ **it is STRUCTURALLY
ELIMINATED as a cause of the current 7.79 Hz ratchet**, rather than merely failing a test. That also
independently corroborates the symmetry argument (an asymmetric clamp should print a rectified waveform;
the ratchet measures symmetric, skew −0.16…+0.06, crest 2.07–2.45 vs a sine's 1.414).

⚠⚠ **A TENSION THIS OPENS, AND IT MUST NOT BE SMOOTHED.** V42 was **CONFIRMED on-car** to fix the ~10 s
hard-turn recovery ratchet — a *different* symptom from the current 7.79 Hz one. **If state 4 never
occurs, V42's fix could not have acted either.** Three readings, none yet established: (a) state 4 does
occur, but only under conditions absent from routes 54/58; (b) V42's original attribution was wrong;
(c) the bit5 measurement does not generalise beyond these two drives. **[OPEN.]**
⇒ **V72 still carries `0x454FE` = `B5`** — it is inert on any drive where state 4 does not occur, so it
costs nothing, and reverting it would risk regressing V42's confirmed (different) fix. **It is carried as
an UNTESTED, currently-inert byte. Do not describe it as a ratchet fix, and do not describe it as
falsified.**

### 0.2 ★★★★ THE ENGAGEMENT QUESTION IS ANSWERED — the mechanism is (d) PLANT, not firmware
The operator's own objection was the right one:
> *"Nowhere did I see anything about openpilot being engaged or not, so this table should be the same for
> manual driving as for openpilot-engaged driving."*

**He is correct, and it is now exhaustive [EVIDENCE]:**
- The r24/r26 rate lanes read **ZERO** LKAS-domain signals. `gp-0x67fe`, `gp-0x6806`, `gp-0x67fa`,
  `gp-0x69b0` are **all absent** from `FUN_0003aa2c` despite being computed earlier in the same 1 kHz tick.
- `gp-0x67fa` — the state machine whose `0x830`/`0x930`/`0xc30` masks gate the whole assist chain — is a
  **FAULT/DIAGNOSTIC/POWER-MODE** state machine, **not** an engagement one. All **33** `st.b` writer sites
  decompiled; across ~20 guard conditions, `gp-0x67fe` / `gp-0x6806` / `gp-0x69ae` / `gp-0x1426` appear in
  **NONE**. Every condition reduces to `gp-0x6d78` fault bits, UDS-session flags, or `FUN_00046ea6` DTC bits.
- `gp-0x683c`, the one gate inside the rate-lane logic itself, has **ONE read and ZERO writers image-wide**
  (183,429-instruction scan, not truncated). It is **structurally dead on stock.** The only thing that ever
  made it engagement-correlated is **this kit's own `0x3AA96` repoint** (V67/V68/V71C) — a build
  modification, not stock behaviour.

⇒ **The engagement-dependence of the symptoms is PHYSICAL, not tabular.** Base-assist damping is
**exactly zero below 35 km/h** (§2.2), so at creep **the driver's hand is the only damping in the system.**
Engagement removes the hand and substitutes an actively-driving motor. That single fact explains
*engagement-required* + *hands-off-required* + *Q ≈ 40* together, with no firmware table needing to know
LKAS exists.

### 0.3 ★★★★ WHY FIXING ONE GRIND FEEDS THE OTHER — [EVIDENCE, on-car, already in the corpus]
The operator's central complaint has a measured answer that had never been connected to it.
**V62's corner-conditioned band table, 219 blocks:**

| band | stock | V62 (both lanes ×2) | ratio | p |
|---|---|---|---|---|
| 1–4 Hz (driver/control) | 4709 | 4763 | 1.01 | 1.00 |
| **18–22 Hz — grind #1** | 3656 | 1269 | **0.35** | 1.00 |
| **40–49 Hz — grind #2** | 301 | 3526 | **11.71** | 0.0003 |

**Monotone crossover between 22 and 24 Hz — one knob, opposite directions.**
**Mechanism:** `gp-0x4f62`, the shared input to *both* rate lanes, is a **4-sample finite-difference
differentiator at 1 kHz**, so its gain **rises with frequency** — measured **1.93× larger at 41.6 Hz than
at 20.9 Hz**. A **flat** gain increase on that lane therefore feeds the 40–49 Hz band harder than the
18–22 Hz band it was aimed at. Independently reproduced on the **comma IMU**, which shares no signal path
with the EPS (40–49 Hz p95 **6.27×**) — matching the operator's description of grind #2 as the one felt
through the whole car.

🛑🛑 **A HARMONIC "REVERSAL" WAS CLAIMED HERE AND IS ITSELF WITHDRAWN. THEY ARE NOT THE SAME MODE.**
An intermediate revision of this section recorded, as [EVIDENCE], that grind #2 **is** grind #1's 2nd
harmonic, citing **f_hi/f_lo = 2.003 [1.997, 2.008]**. **That was a bad test and the claim is retracted.**

**Why it was wrong:** a **ratio of two narrow lines is not a harmonic test.** If f_lo sits near 21 Hz
(sd ≈ 1.2) and f_hi near 43 Hz (sd ≈ 2.6), then `median(f_hi/f_lo) ≈ 2` **whether or not the two ever
move together** — it is a property of the marginal distributions alone. Orchestrator-verified by
simulation: two **independent** lines with exactly those marginals return **median ratio 2.048,
CI [2.012, 2.072]**. Harmonicity requires f_hi to **TRACK** f_lo window-to-window, i.e. a **SLOPE** of
2.0, not a ratio of 2.0.

**The decisive check — shuffle the pairing** [EVIDENCE]. If the ratio encoded real locking, destroying
the window pairing must destroy it:

| route | n | observed ratio | **shuffled ratio** | **tracking SLOPE** |
|---|---|---|---|---|
| V71B/`r54` | 525 | 2.238 | **2.227 [2.215, 2.238]** | **0.106 [−0.056, +0.264]** |
| V71C/`r58` | 296 | 2.288 | **2.268 [2.252, 2.284]** | **0.097 [−0.120, +0.337]** |
| V69/`r4f` | 236 | 2.199 | — | −0.186 [−0.510, +0.099] |
| V62/`r37` | 393 | 2.249 | — | 0.119 [−0.070, +0.322] |

**The shuffled ratio reproduces the observed one.** ⇒ **the ratio carries NO pairing information.** Every
tracking slope **contains 0 and excludes 2.0**, on four routes.
⇒ 🛑 **The record's ORIGINAL finding — Theil-Sen slope 0.173 [−0.92, +1.59], NOT a harmonic — is
CONFIRMED on both new routes, not reversed.** The 2.003 figure is also not reproducible: free-geometry
peak-finding returns **2.24–2.29**, and a ±0.005 CI on a ratio of two lines this broad was implausibly
tight on its face.

★ **What stands instead:** grind #1 (18–22 Hz, ~100% engagement-gated) and grind #2 (~44.9 Hz, only
weakly so) are **two separate excitations sharing ONE differentiator-fed lever.** They feel identical
through the wheel because **one knob moves them in opposite directions** — which is what the crossover
table above measures, and what §2.1.5's two-lane rule operationalises. **That reading was right all
along and needed no harmonic.**

🛑 **CORRECTION — grind #2's 40–49 Hz TAIL IS ENGAGED, NOT MANUAL.** An earlier revision of this document
said grind #2 *"is excited by hard MANUAL cornering."* The **torque/angle description of the corner is
right** (driver torque 1600–2700, |angle| 150–265°, creep); **the ARM is wrong.** [EVIDENCE] On the one
route with clean exposure control (**V62/`r37`, ordinary driving, 41.0% engaged base**) the 40–49 Hz top
decile is **6 of 6 ENGAGED**, Fisher **p = 0.0025**. And the converse: **V62 dosed the MANUAL arm at
×2/×2 and manual 40–49 Hz did not move** — `e_40-49` p90 **56.5 [39.6, 67.8]** against stock-manual's
**73.4 [42.5, 111.1]**, i.e. **0.77×, inside its own split-half null**, speed-matched.
⇒ **Ungating is NOT the risk.** The risk, if any, is the **r24 raise in the ENGAGED arm.**

### 0.4 🛑 TWO RETRACTIONS FROM THIS SESSION'S OWN ORCHESTRATOR — recorded, not buried
1. **"V69/V70 delivered no dose where the grind lives" — REFUTED, and more decisively than first written.**
   The byte fact is real (they edited **only Y[0] and Y[1]**, the flat `[0, 400]` plateau, leaving Y[2]/Y[3]
   stock). But grind #1's operating point, **measured over 19,378 in-burst samples / 70 episodes / 11
   routes**, is **p50 = 104 counts** (p90 254 · p99 505 · max 1409) — **deep inside the plateau V69/V70
   edited.** Priced at the measured (speed, rate) per sample, **V70 delivers 2.000× and V69 3.999×.**
   The dose was fully delivered and it did nothing. ⚠ The orchestrator initially quoted **~603 counts**;
   that is not a sample-weighted operating point but the **median of the per-window WORST INSTANT**
   (`STATE.md` §9.2's own retracted-provenance statistic). **Damping force integrates over the sample
   distribution, not the per-window extreme.** 99.365% of burst samples sit below 603.
   ⚠ The orchestrator had also wrongly treated the axis scale as OPEN; it was settled in the golden model.
2. **"Rate-curve modulation depth ranks the corpus" — REFUTED ON THE MEASURED DATA, not merely
   uncredited.** Two independent kills: (a) V62/V65 has **identical idealised depth to stock** (a `sar`
   scales level, not shape) yet scores **168 vs 879**; (b) **measured** within-cycle depth over **2,330
   burst windows / 559 s** is **1.002 for stock/V62, 1.004 for V69, 1.000 for V67/V68** — the index never
   leaves the plateau, so **there is no modulation to underperform against.** The idealised 2.00× → 8.00×
   steepening requires an amplitude ~15× larger than measured. 🛑 **The parametric-pump / gain-collapse
   family is now closed from the data side as well as the intervention side (V60).**

★ **Independent corroboration of the scale from the firmware side, new this session [EVIDENCE]:**
`gp-0x6ac0 = |EMA(120000/16384 × Δθ_electrical per sample)|`, and the resolver ISR runs at **4.000 kHz**
(PWM carrier `TS0CMP0`=5000, HT-PWM triangular, PCLK **40 MHz** — 🛑 **corrects a standing kit belief of
~8 kHz that was computed off a falsified 80 MHz PCLK**). ⇒ **`gp-0x6ac0` = 30 × f_electrical(Hz)**, derived
two independent ways.

### 0.5 ⚠ WHAT REMAINS GENUINELY UNRESOLVED — do not let V72 imply otherwise
**No single-lane story fits the corpus.** V70 delivers **~1.84×** on r24 at the real operating point and
scores **729**; V62 delivers **2.00×** on r24 **and** 2.00× on r26 and scores **168** — near-equal r24,
wildly different outcome ⇒ the separating variable is **r26**. But **V71B moved r26 ×2 alone (r24 stock)
and grind #1 remained present** ⇒ r26 alone is not sufficient either.
⇒ **The best-supported reading is the operator's own, offered before any of this analysis:**
> *"Maybe we tried one of these steps before and alone it didn't work, but perhaps I need something else to
> be ON for a prior firmware modification to work."*

**V72 does not resolve this and does not claim to.** It is an **empirical** build: reproduce the
best-measured configuration and remove its one known failure.

---

### 0.6 ★★★★ THE STRONGEST REGULARITY IN THE CORPUS — the operator's own hypothesis, confirmed
Priced against what each build **actually carried in BOTH lanes** (median `e_18-22`, engaged creep):

| build | r24 | r26 | **lanes moved** | grind #1 |
|---|---|---|---|---|
| V61 | ×0 | ×0 | **both** (down) | **2501 — worst** |
| stock | ×1 | ×1 | — | 879 |
| V70 | ×2 | ×1 | **one** | 729 |
| V69 | ×4 | ×1 | **one** | 746 |
| **V71B** | ×1 | **×2** | **one** | **still present** |
| **V62 / V65** | **×2** | **×2** | **BOTH** | **168** |
| **V67 / V68** | **arm ≈2.44×** | **÷6.00** | **BOTH** | **109 — best in kit** |
| **V71C** | arm ≈2.44× | **×1 (cut removed)** | **one** | **worse than V67; grind #2 back** |

★★★★ **Every build that moved BOTH lanes fixed grind #1. Every build that moved ONE lane did not — in
either lane, in either direction, across a 4:1 r24 range and a 2:1 r26 range.** Five single-lane nulls,
two two-lane fixes. ⇒ **The operator's own instinct — *"alone it didn't work; something else needs to be
ON"* — is not merely the best-supported reading, it is the ONLY reading consistent with all seven rows.**
⇒ **Lever A must move BOTH lanes.** Any proposal to ship one half alone is a sixth single-lane test.

★★ **And V71C is a clean single-variable r26 test nobody framed as one:** 71 bytes off V67 = cave +
`0x454FE` + `0xC6445` + CRC. The only functional difference is `0xC6444` 512 → 3072, i.e. **removing the
6.00× r26 cut and nothing else.** It made grind #1 worse and brought grind #2 back ⇒ **[EVIDENCE] the r26
cut was the load-bearing half of V67/V68.**

### 0.7 ✅ THE V69/V70 NULL IS A **REAL DOSE NULL** — arm-selection is refuted [EVIDENCE]
Both arms that could bypass the mode-10 LERP on a gateless build have **never fired anywhere in this kit**:
`gp-0x671d` **0 / 402,424** frames (routes 4a, 47, 54, 58) and `gp-0x671a >= 5` **0 / 240,312**.
⇒ On V69/V70/V71B **the LERP was the gain in force**, so their surface dose was genuinely delivered and
their grind-#1 null is a real dose null — not an arm-selection artefact. This also retires the standing
"reading (b)" explanation for four builds' worth of uninterpretable zeros.

### 0.8 ⚠ TWO LEDGER ERRORS FOUND IN `BUILD-LINEAGE.md`, both running the dangerous way
1. **Part 1 attributes four cals to V39 that V39 never wrote.** V39's entire delta vs V38 is `0x3AC78`
   (4 bytes, a cave hook). **`0xC6442` and `0xC61F6` have been written by 0 of 65 built images** — they are
   **UNTESTED**, not falsified. (`0xC6442` is separately **unreachable**: `gp-0x671d` = 0 / 402,424.)
2. **V71B and V71C do NOT carry V62's `sar` fix.** `0x3AB76`/`0x3AC20` = `a9` in **exactly three images:
   V62, V65, V71A** — and V71A is unflashed. **The two builds that just flew carry neither of V62's bytes.**
   Say this before anyone reads V71B/V71C as "V62 plus something."
✅ **No third silent loss exists** — every carried edit was checked across all 65 images.

---

## 1. THE ARGUMENT FOR V72 — empirical, not mechanistic

**V67/V68 is the best result this car has ever produced:** grind #1 median `e_18-22` engaged creep **109**
against stock's **879**, and creep grind #2 **0 bursts** (P(0) = 0.0005). It flew **twice**, flight-clean.
**Its ONLY failure is highway grind #2.**

**V71C tested exactly what happens if you remove one half of it.** V71C = V67/V68's control path with
**only** `0xC6444` changed 512 → 3072 — the ~6× r26 cut removed. On-car: grind #1 **"attenuated but still
present"** (worse than 109) and grind #2 **"absolutely present"**. ⇒ **the r26 cut is load-bearing.**

**Why V67/V68 fails at highway is STRUCTURAL, not a tuning error.** It delivers its dose through a
**scalar gated arm that REPLACES a speed-rolled LERP**. The stock LERP falls with speed; a flat arm does
not; so `arm / LERP` necessarily **rises** toward highway — **r24 reaches 2.438× at 100 km/h.** No value of
the arm fixes it: lowering it enough for highway puts creep *below* stock.
⇒ **A scalar gated arm can never be highway-clean while dosing at creep.**

**V72's move:** deliver **the same creep operating point** through the **ungated, speed-shaped surfaces**,
editing only the 0 km/h and 10 km/h records and leaving the 50/100 km/h records byte-stock — so highway is
**exactly 1.000×** by the record-selection geometry, not by tuning.

---

## 2. THE THREE LEVERS

### 2.1 LEVER A — BOTH lanes, WHOLE RATE AXIS: reproduce V67/V68 at creep, stock at highway

🛑🛑 **THIS SECTION WAS REVISED TWICE AND THE HISTORY IS KEPT DELIBERATELY.** An intermediate
"plateau-only" version (Y[0]/Y[1] only) was specified on an *instantaneous* rate-occupancy statistic and
is **SUPERSEDED**. Two measurements killed it: (a) for a derivative/viscous term the occupancy that
matters is the **peak of each cycle** — per-window peak rate index **p50 = 523**, with **56.7% of windows
peaking above 400**; and (b) the on-car ladder separates the two shapes directly (§2.1.4). **The final
spec is the whole-axis form below.**

**32 bytes, 4 records, all four Y values each.**

| addr | record | lane | stock Y[0..3] | **V72 Y[0..3]** |
|---|---|---|---|---|
| `0xD2A7E`–`0xD2A85` | `0xD2A74` mode-10 gain_B, **0 km/h** | **r24** | 3072, 3072, 2322, 1536 | **5244 ×4** |
| `0xD2ABA`–`0xD2AC1` | `0xD2AB0` mode-10 gain_B, **10 km/h** | **r24** | 2561, 2561, 2247, 1947 | **5244 ×4** |
| `0xC6A72`–`0xC6A79` | `0xC6A68` gain_A, **0 km/h** | **r26** | 3072, 3072, 2434, 2048 | **512 ×4** |
| `0xC6A86`–`0xC6A8D` | `0xC6A7C` gain_A, **10 km/h** | **r26** | 3072, 3072, 2488, 1536 | **512 ×4** |

5244 and 512 are **V67/V68's own arm values**, used verbatim. `0xD2AEC` / `0xD2B28` / `0xC6A90` /
`0xC6AA4` stay **byte-stock** ⇒ **exactly 1.000× on both lanes at and above 50 km/h**, structurally.
⇒ **At 0 and 10 km/h this reproduces V67/V68's ENGAGED multipliers exactly at every rate index**
(r24 1.707 / 1.707 / 2.258 / **3.414**; r26 0.167 / 0.167 / 0.202 / **0.250** at 0 km/h) — **and V67/V68
is the best-measured configuration this car has ever had.**

### 2.1.4 ★★★★ WHY WHOLE-AXIS — the measured grind-#1 ladder [EVIDENCE, routes 54/58]

Median `e_18-22`, engaged creep, matched-exposure resampling (**not** CI overlap):

| build | r24 | r26 | median | blocks |
|---|---|---|---|---|
| V68/`r4e` | flat, **all rates** | 512, all rates | **70** | 2 |
| V65/`r3a` | ×2 all rates | ×2 all rates | 94 | 29 |
| **V67/`r47`** | **flat, all rates** | **512, all rates** | **111** | 13 |
| **V71C/`r58`** | **flat, all rates** | 3072 (≈1.0×) | **223** | 12 |
| V62/`r37` | ×2 all rates | ×2 all rates | 268 | 29 |
| **V71B/`r54`** | ×1 | **×2 all rates** | **545** | 42 |
| **V70/`r50`** | **×2 PLATEAU-ONLY** | ×1 | **729** | 5 |
| **V69/`r4f`** | **×4 PLATEAU-ONLY** | ×1 | **746** | 23 |
| stock pool | ×1 | ×1 | 879 | 39 |
| V61/`r31` | ×0 | ×0 | 2501 | 4 |

★ **Every build that raised r24 across the WHOLE rate axis lands at 70–268. Both plateau-only builds land
at 729–746 — the two worst dosed builds in the corpus, despite ×2 and ×4 doses.**
⚠ **Stated honestly: the direct test does not clear significance** (V71C vs V70 **P = 0.35**, vs V69
**P = 0.15**, because V70's arm is 5 blocks). It is a 3.3× point-estimate gap that is **under-powered,
not null.**
**What IS established:** V71C **excluded lower from the stock pool, P = 0.0006** · V71C **excluded HIGHER
from V67, P = 0.0215** (the only difference is r26 ⇒ **the r26 cut is load-bearing**) · V71B **excluded
higher from V62/V67/V71C, all P ≤ 1e-4** ⇒ **r26 raised alone does not fix grind #1** · **V71C better
than V71B, P = 0.0000 — exactly the operator's own ranking.**

### 2.1.5 ★★★★ AND THE GRIND-#2 SEPARATION PUTS V72 IN THE SAFE ROW — 6 builds, no exceptions
High-rate corner of both surfaces (creep, rate index 3000); gains read from the shipped images:

| build | **r24 high-rate ×** | **r26 high-rate ×** | creep grind #2, measured |
|---|---|---|---|
| stock · V69 · V70 | 1.000 | 1.000 | **none** |
| **V71B/`r54`** | **1.000** | **2.000** | **none** (0 bursts, max **61**) |
| V62/V65 | **3.414** | 2.000 | **YES — worst in corpus** |
| **V71C/`r58`** | **3.414** | 1.500 | **YES — 3 events** |
| **V67/V68** | **3.414** | **0.250** | **none** |
| **⇒ V72** | **3.414** | **0.250** | **← V67/V68's exact row** |

> **Creep grind #2 requires r24 high-rate ≳ 3.4× AND r26 high-rate ≳ 1.5×. Cutting EITHER kills it.**

**`r26`'s high-rate multiplier ranges 0.25 → 2.00 across these six and predicts nothing alone; neither
does r24.** ⇒ **V72 is the only configuration satisfying both constraints, and it is the one already
measured best on grind #1.**
★ **The direct test of the high-rate region — the red-team's open hole — is now closed by V71B**, the
corpus's ONLY high-rate dose on either lane (it doubled gain_A rec0/rec1 across **all four** Y):
**40–49 Hz p90 = 58.5 [55.1, 60.1], max 61.0** against a 500-count threshold, **below stock's own 77.4
in the same cell** and the **lowest 40-49/24-28 fraction in the corpus (0.52)**.
⚠ Count test **P(0) = 0.081** (marginal); **level test is not** — 24× non-overlapping vs V62/V65's 1441.9.
⚠ **Route 54 has ZERO manual high-rate exposure** (manual `|rate|` never crossed 1400) ⇒ that cell is
**empty, not null.**
🛑 **[EVIDENCE] for the association; the "product of the two lanes" mechanism is [BELIEF]. And V67/V68's
cell — the row V72 occupies — is the WEAKEST evidence in the table**, covering ~42 s of engaged creep.
★ In the corner regime **every burst-producing cell in the corpus is the ≥1400 rate cell** (V62/V65: 14
bursts at ≥1400 vs 1 at the knee vs 0 at the plateau) ⇒ grind #2 is a **high-rate-index phenomenon**.

🛑 **RECORD ADDRESSING — verified three ways, because one agent got it wrong.** gain_B is mode-indexed
through **FOUR SEPARATE ROM POINTER ARRAYS**, one per speed breakpoint, each indexed by `mode*4`:
`0xCBF5C`→`0xD2A74` (0 km/h) · `0xCC044`→`0xD2AB0` (10) · `0xCC12C`→`0xD2AEC` (50) · `0xCC214`→`0xD2B28`
(100), at m = 10. **The contiguous 0x14 stride inside the block is the MODE axis, not the speed axis** —
`0xD2A88` is *mode 11's* record-0 and must NOT be touched. Confirmed by (a) my own dereference, (b)
`FW-surface`'s independent dereference, (c) the Y values forming a monotone speed rolloff
(3072 → 2561 → 2305 → 2151). gain_A is **not** mode-indexed and its four records **are** contiguous.

★★★★ **WHY THIS SHAPE — it is the one combination never tried, and it satisfies both constraints at once:**

| | **one lane** | **both lanes** |
|---|---|---|
| **plateau only** (rate ≤ 400) | V69, V70 → **null** | ★ **NEVER TRIED = V72** |
| **whole rate axis** | V71B, V71C → **null** | V62, V67/V68 → **FIXED** |

- **§0.6 requires BOTH lanes** — five single-lane nulls, two two-lane fixes.
- **§0.9 requires PLATEAU ONLY** — grind #1 lives **97.77%** below rate 400; **creep grind #2 straddles the
  knee (41.45% above 400, 9.66% above 1400)**. Dosing above 400 buys nothing for grind #1 and feeds grind #2.

**VERIFIED by sweep [EVIDENCE, `analysis-2020accord/studies/models/v72_lane_model.py`]:**

| km/h | rate | V72 r24 | V67 r24 (eng) | V70 r24 | V72 r26 | V67 r26 (eng) |
|---|---|---|---|---|---|---|
| 0 | 0–400 | **1.707** | **1.707** | 2.000 | **0.167** | **0.167** |
| 0 | 700 | 1.534 | 1.842 | 1.755 | 0.341 | 0.176 |
| 0 | 1400 | **1.000** | 2.258 | 1.000 | 0.832 | 0.202 |
| 0 | 3000 | **1.000** | 3.414 | 1.000 | **1.000** | 0.250 |
| 10 | 0–400 | **2.048** | **2.048** | 2.000 | **0.167** | **0.167** |
| 50–100 | all | **1.000** | 2.275–2.438 | 1.000 | **1.000** | 0.192–0.200 |

⇒ **Exactly V67/V68's winning values where grind #1 lives; exactly STOCK where grind #2 lives; exactly
stock at highway.**

### 2.1.1 🛑 SUPERSEDED — the pointwise-bound argument no longer applies

**Two subsections here previously argued that V72 was pointwise ≤ V70 and ≤ V62 on both lanes, and that
this bounded its grind-#2 risk by an already-flown build. BOTH ARE FALSE FOR THE FINAL SPEC and are
removed rather than left standing.** The whole-axis form reaches **3.414×** on r24 at rate 3000, above
V62's flat 2.000×, so no pointwise bound exists. **Do not reintroduce that claim in any note.**
⇒ The grind-#2 case now rests on **§2.1.5's 6-build separation** — which is stronger evidence anyway,
because it identifies *which* variable separates rather than bounding one build by another.
⊕ One durable finding from the superseded argument, kept because it is a real correction:
***"V67/V68 showed zero creep grind #2" is a SHARED ZERO, not a result*** — every non-V62 build in the
corpus reads 0.0, **including stock-class V58/V59/V64 and V61**. Only V62/V65 (and now V71C) have ever
produced grind-#2 events at all. A zero that every arm shares carries no information about the arm that
was changed. **Strike that anchor wherever it appears.**

### 2.1.3 ⚠ THE RESIDUAL RISK, STATED HONESTLY — and it is an EXPOSURE problem, not a build problem

**[EVIDENCE]** V67/V68's "zero creep grind #2" cannot carry the weight that was put on it. Their **engaged
corner exposure is 6.8 s and 0.9 s respectively.** At V62's own measured burst rate (5.44 burst-seconds
per 100 s) that predicts **0.29** and **0.04** windows ⇒ **P(observe 0) = 0.748 and 0.963.**
⇒ **Those are nulls with ~25% and ~4% power. V67/V68 did not fly the relevant regime — they clipped it.**
⚠ And the whole grind-#2 corner analysis rests on **14 burst windows corpus-wide, 13 of them from two
PROVOKED routes** (V65/`r3a`, `r3b`); V62/`r37` contributes exactly **one**. **Nothing here is well
powered — not this analysis and not the 11.71× it rests on.** Say so rather than quoting the CI as if the
exposure were adequate.

⇒ 🛑 **FLIGHT INSTRUCTION FOR V72, and it is the cheapest de-risk available — it costs no bytes:**
**drive the engaged corner deliberately** — hard, slow, parking-lot-style cornering **with openpilot
engaged**. Going from ~7 s to ~100 s of engaged-corner exposure moves the power from ~25% to ~80% and
settles the question on a single drive, whichever way it falls.

### 2.2 LEVER B — the ratchet: FactorC + FactorE opened at creep

**[EVIDENCE — byte-read, three independent confirmations this session.]**
`0xD27BC` (FactorC, mode 10): **X = [2240, 3840, 5120, 8960]**, **Y = [0, 235, 430, 877]**.
The speed scale is pinned independently — `0xC6010` gives 640 counts = 10 km/h ⇒ **64 counts/km/h** —
so **X = [35.0, 60.0, 80.0, 140.0] km/h exactly** and the LERP **clamps flat to Y[0] = 0 below 35 km/h.**
`0xD27F8` (FactorE, mode 10): X = [60, 400, 2500, 4000] counts of |motor rate|, Y = [0, 140, 539, 927].
The five factors multiply in Q10, so **either zero alone kills the whole damping term**; FactorC binds below
35 km/h. The sign is **velocity-opposing by construction** (`0x3469e`–`0x346a2`, `if gp-0x6abe > 0: negate`).

⇒ **The car has NO base-assist damping anywhere below 35 km/h**, which is the entire region where the
ratchet (4.9–8.0 km/h, Q ≈ 40) and both grinds live.

| addr | cell | stock | V47 (flown) | **V72** |
|---|---|---|---|---|
| `0xD27C6`, `0xD27C8` | FactorC **m10** Y[0], Y[1] | 0, 235 | 235, 235 | **430, 430** |
| `0xD27DA`, `0xD27DC` | FactorC **m11** Y[0], Y[1] | 0, 234 | 234, 234 | **431, 431** |
| `0xD2802/04/06` | FactorE **m10** Y[0..2] | 0, 140, 539 | 700, 750, 800 | **927, 927, 927** |
| `0xD2816/18/1A` | FactorE **m11** Y[0..2] | 0, 140, 539 | 700, 750, 800 | **927, 927, 927** |

**10 cells = 20 bytes.** 🛑 **NOT V47's bytes, and NOT the table maximum. Both were rejected, each for a
specific reason — the values above are DERIVED from two hard constraints:**

1. **NO SATURATION.** The damper's ceiling is a 2-point record `0xD209C`, X = [300, 800], Y = [512, 1024],
   so below `gp-0x6ac2` = 300 the ceiling is **512**. Delivered authority is
   `FactorC × FactorE >> 10` at seed ≤ 1024. **`430 × 927 >> 10 = 389 < 512` ⇒ no clipping at any seed**,
   with 24% headroom. 🛑 **The rejected "raise to the table maximum" option gives `877 × 927 >> 10 = 793`,
   which CLIPS whenever seed > 661.** A hard-clipping element inside a feedback loop **at the frequency of
   a Q ≈ 40 resonance** is exactly the describing-function nonlinearity that *creates* limit cycles — §4's
   own ratchet analysis names that mechanism. **Saturation here is the hazard, not a safety bound.**
2. **MONOTONICITY.** FactorC = its own Y[2] gives `[430, 430, 430, 877]` — flat to 80 km/h, then rising.
   **It is the largest value that keeps the speed curve monotone**, and Y[1] must move with Y[0] or the
   curve dips. 🛑 The rejected maximum gives `[877, 877, 430, 877]` — **a dip at 80 km/h.**
   FactorE flat at its own Y[3] = 927 is likewise monotone, **and it removes the motor-rate deadzone
   entirely** — the co-requisite whose absence made V44's FactorC-only test null (conditional null **C5**).

⇒ **Delivered authority ≈ 389 counts, versus V47's 160–183 — 2.1–2.4× the dose, with no clipping.**
★ **This matters because under-dosing was one of V47's four failure conditions**, so re-flying V47's exact
bytes would have reproduced it and risked a fourth uninformative null on this lane.
✅ **Byte-confirmed NOT on the car:** all these cells are stock in `_v70_plain_image.bin`.

### 2.3 LEVER C — the damper's weight into the parallel sum (2 bytes)
**`0xC63A0` 1024 → 2048.** The weight applied to `gp-0x6bd0` — the damper's own output — inside
`FUN_00038148`. **Never edited by any build** (byte-read across stock/V47/V62/V67/V70/V71B/V71C).
★ **It buys the same authority increase as raising the ceiling `0xD209C`, with ZERO monitor exposure:**
`0xD209C` has a float twin `0xC6554` checked in lockstep at 5/1024 tolerance, escalating to **DTC 0x1d
hard shutdown**; `0xC63A0` is mirrored to nothing. **Take `0xC63A0`; leave `0xD209C` alone.**
⚠ Its "exactly one reader (`0x381AC`)" claim is decision-bearing and is being verified independently at
build time. **If more than one reader is found, the lever is dropped.**

🛑 **THE JUSTIFICATION, STATED HONESTLY.** V47 was flashed and driven, and the operator reported
***"marginally quieter at 5 mph, no effect in motion."*** It was then filed **null — against the 21 Hz
vibration.** The damping producer `FUN_00034350` runs on **task 5 at 100 Hz**, so a zero-order hold costs
**37.6° average / 75.2° worst-case at 20.9 Hz** — the damper **structurally cannot** damp grind #1 and may
be anti-damping there. **At the ratchet's 7.79 Hz the same hold costs only 14.0° / 28.0°**, so
**88–97%** of the velocity-proportional damping authority survives.
⇒ **V47 was tested against a target its own sampling rate made unreachable. It has NEVER been evaluated
against the ratchet.** That — not novelty — is why it is back. It is **not untested**; it is
**untested against this symptom**.
✅ **Byte-confirmed NOT on the car:** all eight cells are stock in `_v70_plain_image.bin`.

---

## 3. THE PROBE — measure the LEVER, the UNMEASURED WEIGHT, and a pre-registered CONTROL

**Standing lesson, earned across five uninterpretable nulls (V64/V67/V68/V69/V70):
*read the gate and the input, not just a lane output.*** V72 spends every rung on that.

| bit | test | why |
|---|---|---|
| **7** | liveness = 1 | field == 0 ⇒ the cave did not fire ⇒ frame VOID |
| **6** | ★★★★ `gp-0x69a4 >= 512` | **`a`, THE UNMEASURED WEIGHT.** `r26 = ((a × dtorque) >> 10) × gain_A >> 10`, so `a` sets r26's magnitude **relative to r24** and it has **never been measured.** It blocks every r24-vs-r26 attribution in the corpus and has done for ~10 builds |
| **5** | ★★★★ `gp-0x69a4 >= 1024` | the second thermometer step (`a >= 1.0`). ★ **`bit5 ⇒ bit6` is a monotone invariant** ⇒ a wrong build is **detectable rather than plausible** |
| **4** | `\|gp-0x6bd0\| >= 64` | **IS LEVER B IN FORCE?** The damping lane's own output. Non-zero here is the first direct proof the base damper is alive at creep on any build in this kit |
| **3** | `gp-0x6ac0 >= 400` | 📋 **PRE-REGISTERED, with a built-in positive control.** Engaged duty must read **3.74%** under the settled scale (4.7121 counts/deg-s) and **0.0000%** under the retired alternative — and it must fire frame-for-frame with bus `\|rate_c\| >= 84.9`. Threshold is the LERP's own breakpoint |

🛑 **`gp-0x67ac` is NOT probed — it is PROVABLY always 0** (§5), so a rung there would read 0 forever and
buy nothing. The freed rung goes to `a`, which is the single most consequential unmeasured quantity in
the kit: **it is what makes every "r24 vs r26" number in this record conditional.**

---

## 4. RISKS AND GATES

**GATE 1 (RAM ownership)** — **not applicable.** Both levers are calibration-only. The cave is the
existing proven 68-byte extent with rung contents changed. Code caves are this kit's only bricking class
(V24, V27, V48B); V72 does not grow or relocate one.

**GATE 2 (closed-loop stability, magnitude AND phase)** — the real exposure, in two places:
1. **Lever A in the MANUAL arm.** The most aggressive manual rate-lane configuration ever flown is V62's
   flat ×2 and V69's ×4-at-low-rate. Lever A puts manual r24 at 1.71× → 3.41× across the rate axis below
   30 km/h. **Open; under red-team.**
2. **Lever A and the 40–49 Hz band.** §0.3's differentiator makes any flat lane-gain increase feed grind #2
   harder than grind #1. Lever A raises r24 **and** cuts r26 to 0.167× — opposite directions, and which
   wins depends on `a = gp-0x69a4/1024`, which is **unmeasured**. ⚠ **V67/V68 flew this exact creep
   configuration twice with zero creep grind #2**, but **engaged-only** — and grind #2's own excitation is
   hard **manual** cornering. **Lever A exposes that regime for the first time. Open; under red-team. This
   is the most likely way the design is wrong.**

**Monitors** — clear. FactorC/E's Y-cells are read only by `FUN_00034350`'s LERP walker; the DTC-0x1d
ceiling lockstep (`FUN_000347b8`) re-derives the **ceiling** table and its float mirror, neither of which
V72 touches, and the proposed authority (~184) stays far under the ceiling floor (512). The entry
consistency check watches the upstream torque EMA, not these tables.

**CRC blocks touched:** **CAL** (ends `0xC6FFC`) for gain_A; **`0xD2000` block** (ends `0xD2FFC`) for
gain_B mode-10 and FactorC/E; **MAIN** (ends `0xC4FFC`) for the cave. All three are handled by existing
build tooling. Nothing lands in `[0xC5000, 0xC5FFC)` — the CRC-skipped block with the V40 ignition-brick
precedent.

**Not single-variable, by explicit operator instruction.** The operator asked for a build that addresses
both the grinds and the ratchet, and authorised a *"throw everything at the wall"* approach. The two levers
are separable **by symptom and by frequency band** — Lever A owns 18–22 and 40–49 Hz, Lever B owns 7.8 Hz —
and Lever B carries its own in-force readout (bit5). **State this limitation in the flight note.**

---

## 5. ✅ THE VETO IS CLOSED — `gp-0x67ac` IS PROVABLY ALWAYS 0

**Flagged independently by two agents this session.** In `FUN_0003aa2c`:
```
if ((gp-0x67ac clamped <2) == 1)   →  REDUCED sum: only gp-0x6b62 and gp-0x6ade survive
else                                →  FULL 11-lane sum: r24, r26, gp-0x6bd0 (damping), boost,
                                       friction, resonance, magnitude, gp-0x6b4c, + FUN_00036682()
```
**The risk was real: if `gp-0x67ac == 1` during the symptoms, r24, r26 AND the base-assist damping lane
would all contribute exactly ZERO, making every lever this kit has flown for fifteen builds — and both V72
levers — vacuous by construction.** ✅ **It is now closed, structurally rather than statistically.**

**[EVIDENCE — traced independently by the orchestrator and by a second agent, agreeing at every step.]**
1. **Polarity, from the literal case values:** the REDUCED branch fires **iff `gp-0x67ac == 1` exactly**
   (`x * (x < 2) == 1` ⟺ `x == 1`). No branch-sense ambiguity.
2. **Provenance:** `gp-0x67ac` has **3 accesses image-wide, 1 writer.** It is a shadow-lockstep copy of
   `gp-0x3d98` (`0x2772a`–`0x2773e`), which is the result of an **11-channel sticky-OR scan**. ⚠ `r22` is
   stored on every iteration so it *looks* like "last channel wins", but the latch `r27` is never reset
   within the scan and short-circuits every later channel to 1 ⇒ **it is a true OR across all 11.**
3. ★ **The OR's only trigger is dead.** It needs `gp-0x617c[i] != 0`, and `gp-0x617c` is written **only**
   inside `FUN_00026c80`'s dispatch switch, selected by the **static cal byte** `0xC4124[i]`. Only roles
   **6 and 7** write a 1. **`0xC4124` = `00 00 05 00 05 05 00 00 00 05 00` — byte-identical across ALL 65
   built images, stock through V71C. Only values 0 and 5 have ever existed.** The seven role-0 channels are
   never written at all, and their boot image (flash `0x86F34`) reads **all zero**.

⇒ **`gp-0x67ac` cannot read 1 without a calibration edit to `0xC4124`. Nothing in V72 touches it.**
**Both levers live in the FULL branch, which is the only branch that ever executes.**
⇒ 🛑 **Therefore V72 does NOT spend a probe rung here** — it would read 0 forever and buy no information.
The rung goes to `gp-0x69a4` instead (§3). ⊕ A **static byte-check on `0xC4124`** belongs in the build
script's assertions, which is the right place for this class of guarantee.

---

## 6. WHAT V72 DOES NOT DO
- It does **not** explain the corpus (§0.5). It reproduces the best-measured configuration and removes its
  one known failure.
- It does **not** carry `0x454FE` (§0.1, falsified).
- It does **not** touch the motor/FOC layer. That layer was mapped this session (4 kHz carrier, model-based
  FOC, no isolated PI gains, no cogging table found) and **nothing in it clears this kit's low-blast-radius
  bar.** Two live threads remain: `FUN_000757a2`'s 6-branch shared-index LERP cluster (a candidate ripple
  table) and the motor pole-pair count, which is not in this firmware at all.
- It does **not** address the ~28 Hz lane-change transient, which is **dose-independent** and reads as
  excitation rather than gain.
