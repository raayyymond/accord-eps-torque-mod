# THE SYMPTOM ↔ BAND ↔ BUILD LADDER — so a new number can be placed instantly

**Built 2026-08-08 for the V87 design session.** Everything numeric below was read from the cache JSONs
and the record on disk, or recomputed with the corpus's own instrument. Nothing is quoted from a build
script or from an agent's report.

> 🛑 **TERMINOLOGY.** *"grind #1"*, *"grind #2"*, *"the ring"*, *"S1…S4"* are **KIT JARGON for frequency
> bands**. They are **not** symptoms the operator named. His vocabulary is **grinding · vibrating ·
> micro-ratcheting · macro-ratcheting · ratcheting · excess friction · heaviness**. Every table here
> carries **both columns** and never substitutes one for the other.
> On record, 2026-08-09: *"Not even sure what the ring is. We are working on grinding, vibrating, and
> ratcheting issues."*

---

# PART 1 — THE SYMPTOM ↔ BAND MAPPING, AND HOW STRONG EACH LINK ACTUALLY IS

| band | kit jargon | operator's word | link strength | the evidence, and what it rests on |
|---|---|---|---|---|
| **~6–9 Hz** (line at 7.79–8.2 Hz) | micro-ratchet / "the ratchet" | **micro-ratcheting** ("not audible, only felt in the column") | ★★★★ **STRONG — the only band the operator himself named against a number** | (a) **V57, verbatim: *"grinding is not 7.4 Hz, that is the ratcheting."*** He was shown the 7.4 Hz line and assigned it. (b) **V72: he settled the naming — TWO ratchets, MACRO (fixed) and MICRO ≡ the 7.79 Hz line**, *"not audible, only felt in the column"*. (c) Mechanically consistent: **engagement-required** (V70: 73/88 = 83.0% engaged hands-off vs **0/118** manual hands-off, Fisher p = 3.8e-41), **in the bar and in angle rate but NOT in openpilot's command** (V69). ⚠ **Both operator statements are single comments**; there has never been a blind A/B. |
| **18–22 Hz** | grind #1 | **grinding** (at creep, 2–5 mph, wheel near centre) | ★★★★ **STRONG, via a fix that moved together with the symptom** | **V62**: 18–22 Hz creep **0.124 [0.036, 0.387]** vs V59 with a 30–40 Hz control ≈ 1.0, and the operator's verbatim *"Original grinding at 2–5 mph is gone!"* That is one **matched positive**: band down, symptom reported gone. **V67/V68** replicate it (pooled **0.40 [0.27, 0.58]**). ⚠ The link rests on **band-and-symptom co-movement across builds**, not on a within-drive experiment; and the reverse direction has failed — **V84 was byte-identical to V67/V68 at every grind cell and he still reported grinding**. |
| **26–31 Hz** | **"the ring"** | 🛑 **NONE. He has explicitly disclaimed it** | ☆ **NO SYMPTOM ATTRIBUTION AT ALL** | Operator, 2026-08-09: *"Not even sure what the ring is."* The band is real as an instrument (**V81: an 11.25 s sustained 27.75 Hz limit cycle, amp 978 ct, column angle p-p 1.29°, Q ≲ 6 ⇒ actively sustained, not forced**), and V84 moved its burst duty **96.6% → 25.1% → 2.54%**. 🛑 **But no operator symptom has ever been attached to it, and the one time a band move was headlined as a fix the operator corrected it twice.** Treat 26–31 Hz as a **stability instrument**, never as a symptom. |
| **32–38 Hz** | **PRE-DECLARED NEGATIVE CONTROL** | — | n/a | Declared in `studies/grind/compare_v75_v76_v80_grind.py` and printed beside every claim. Chosen because it does **not** overlap the ~28 Hz lane-change band (unlike the older 24–28 control). 🛑 **It has failed at least once and that failure was load-bearing: on V80 the 30–49 Hz "HF lift" was 2.091 and the control moved 2.035 ⇒ the whole HF region moved and nothing band-specific was measured.** |
| **40–49 Hz** | grind #2 | **vibrating** — *"makes the entire car vibrate, almost like I have a subwoofer"* | ★★★ **MODERATE-TO-STRONG for the OBJECT, WEAK for the BAND EDGE** | (a) Operator V65 verbatim above, and *"happens regardless of LKAS engagement"*. (b) **It is a different physical object from grind #1**: grind #1 is a **torsional column mode that never reaches the chassis** — IMU coherence **0.82–0.88 for grind #2 vs no contrast across 48 grind-#1 events**. (c) Acoustic inversion puts its real centroid at **63.5 Hz [54.2, 79.6]** — **above both instruments' Nyquist (CAN 50.00 Hz, IMU 50.51 Hz)**. 🛑 ⇒ **40–49 Hz is the visible skirt of an out-of-band object, not the object.** A 40–49 Hz null is weak evidence about grind #2. |
| **~28 Hz lane-change transient** | (inside 26–31) | *"Definitely felt the grind-#2-like vibration when changing lanes"* (V68, `4e`); V67 *"a higher-speed grind #2 on lane changes/turns, only LKAS-engaged"* | ★★★ **MODERATE — a captured event with a verbatim report** | V68 captured it: **27.34–28.90 Hz, envelope 20× route median**. 🛑 **It is EXCITATION, NOT GAIN — dose-independent**: 2.000/1.000 dose = **1.176 [0.641, 2.320]**, Theil-Sen on dose **+5.736 [−25.4, +34.9]**. **Do not chase the rate lane for it.** ⚠ *"only when engaged"* is **REFUTED at 40–49 Hz** (ON 2.516 vs OFF 2.558); the engaged-conditional part is **18–28 Hz**. |
| **macro-ratcheting** | (no band) | **ratcheting** (≤30 mph under strong command) | ☆ **NO INSTRUMENT** | 🛑 **Macro-ratcheting has never been given a band.** V42 was reported *"fixed"* on feel alone, and that attribution is **VOID** (`gp-0x67fa == 4` fires 0/123,277 while driving). The operator reported it **"still unfixed"** on V85. ⇒ **there is no measurement to place a V87 number into.** |

### 🛑 The caveat that governs the top two rows — MICRO vs MACRO COULD NOT BE SEPARATED

Verified from `_scratch/cache/r6e/relay_fingerprint_b.json` (P4). Splitting each build's engaged ~8 Hz envelope
at its own median and asking whether the halves are two **kinds** of signal or two **amplitudes** of one:

| build | LOW-half f₀ | HIGH-half f₀ | LOW speed | HIGH speed | log-amp skew / kurtosis | verdict |
|---|---|---|---|---|---|---|
| V85/`6e` | 8.50 [8.15, 9.28] | 7.91 [7.81, 8.06] | **8.95 m/s** | **4.42 m/s** | −0.944 / 3.871 | **ONE population** |
| V84/`6d` | 9.52 [8.59, 10.64] | 8.20 [7.91, 8.45] | **23.64 m/s** | **13.82 m/s** | +0.078 / 2.085 | bimodal-ish |
| V81/`67` | 8.69 [8.20, 9.42] | 8.69 [8.35, 9.18] | 15.42 m/s | 13.57 m/s | −0.144 / 2.381 | **ONE population** |

⇒ **The split is dominated by SPEED, not by kind** (the HIGH half is simply the slower half on every
build), and kurtosis ≈ 3 is what a single log-normal gives. 🛑 **Do not treat micro- and
macro-ratcheting as two measurable objects on this evidence.** Carry the caveat forward.

---

# PART 2 — THE BUILD LADDER

## 🛑 2.0 THE COMPARABILITY RULE, STATED BEFORE THE NUMBERS

There are **three incompatible number families** in the record. Putting them in one column is the single
easiest way to manufacture a false trend.

| family | what it is | which builds | comparable to? |
|---|---|---|---|
| **A — the modern ladder** | `score/score_v85_r6e_bands.py` → `score/score_v84_r6d.py` → `compare_v75_v76_v80_grind` → `_grind2_lib`. NFFT 256 / hop 128, p99 analytic band envelope, `blk` (~10.2 s) episode units, **4 speed strata, creep = <10 km/h** | **V67, V68, V76, V80, V81, V83a, V84, V85** — all eight loaded from **one** pickle (`_scratch/cache/r6d/records_v84_score.pkl`, read-only), so they are **bit-identical across sessions** | ✅ **each other, and nothing else** |
| **B — the `e_18-22` yardstick** | the numbers quoted throughout `BUILD-LINEAGE.md` / `archive/LEDGER-V38-TO-V84.md`. **Same envelope estimator**, but **engaged creep = <20 km/h** and a different route pool | V58, V59, V61, V62, V64, V65, V67, V68, V69, V70, V71b, V71c, V72 | ⚠ **each other only** |
| **C — pre-statistical** | mean-Welch engaged-vs-disengaged ratios. **No CI, no null**, and engagement/motion are collinear on those routes | V38 → V57 | 🛑 **nothing. Upper bounds of unknown looseness** |

### 🛑 A AND B ARE NOT THE SAME COLUMN — proved, with the size of the error

The two families share the estimator and differ **only in the creep cut**, and that alone moves a build
by ~6×. Read off `_scratch/out/_r59_grind1.json`:

| build | family B, creep **<20 km/h** (the quoted `e_18-22`) | family B, creep **<10 km/h** | family A, creep **<10 km/h** |
|---|---|---|---|
| **V67/`47`** | **110.7** [74.2, 172.1] · n=28 | **654.3** [240.2, 711.6] · n=11 | **654.3** [240.2, 711.6] · n=11 |
| V62/`37` | 268.0 [204.9, 335.9] · n=129 | 343.3 [268.0, 383.2] · n=86 | — (not in family A) |
| V65/`3a` | 94.0 [60.8, 181.1] | 74.2 [53.8, 154.1] | — |
| V69/`4f` | 745.9 [225.6, 1108.9] | 1034.4 [302.0, 1238.6] | — |
| V70/`50` | 729.1 [40.2, 1013.6] | 1006.0 [38.5, 1686.3] | — |

⇒ ✅ **At a matched cut, A and B agree bit-for-bit** (V67 654.3 [240.2, 711.6] in both). ⇒ 🛑 **The famous
*"V67/V68 is the best grind #1 in the kit, `e_18-22` = 109"* is a `<20 km/h` figure. Against the modern
`<10 km/h` creep stratum V67 reads 654.3 — worse than V81's 69.4.** Never place a family-B number in a
family-A column.

---

## 2.1 THE COMPARABLE LADDER (family A) — the only rows that may be ranked against each other

**Exposure.** Window-level, engaged only, parked segments dropped, 1.28 s per window.

| build | route | cache | date¹ | eng frac | s engaged | s ≥50 km/h | s ≥80 km/h | s creep 2–9 m/s | blk |
|---|---|---|---|---|---|---|---|---|---|
| **V76** | `65` | `_scratch/cache/r65` | 2026-08-07 | 84.8% | 419.8 | 184.3 | 42.2 | 103.7 | 48 |
| **V80** | `66` | `_scratch/cache/r66` | 2026-08-07 | 32.9% | 275.2 | 106.2 | 30.7 | 71.7 | 33 |
| **V67** | `47` | `_scratch/cache/r47` | 2026-08-01 | 77.7% | **1103.4** | **933.1** | **792.3** | 85.8 | 119 |
| **V68** | `4e` | `_cache_r4e` | 2026-08-03 | 100.0%² | 230.4 | 206.1 | 103.7 | **14.1** | 24 |
| **V81** | `67` | `_scratch/cache/r67x` | 2026-08-08 | 87.0% | 633.6 | 366.1 | 44.8 | 144.6 | 69 |
| **V83a** | `68` | `_scratch/cache/r68x` | 2026-08-08 | 85.5% | 286.7 | **37.1** | **19.2** | 161.3 | 32 |
| **V84** | `6d` | `_scratch/cache/r6d` | 2026-08-09 | 83.7% | 518.4 | 354.6 | 151.0 | 79.4 | 56 |
| **V85** | `6e` | `_scratch/cache/r6e` | 2026-08-09 | 85.8% | 340.5 | **34.6** | **23.0** | **199.7** | 37 |

¹ session/handoff date — a proxy for the drive date, not read from the rlog clock.
² V68 has **zero** manual windows after parked-drop ⇒ **no within-route manual isolator exists on `4e`.**

### 🛑 EXPOSURE GATES — cells that are UNSCOREABLE, marked before any number is read

| build | unscoreable regime | reason |
|---|---|---|
| **V85/`6e`** | 🛑 **highway AND the 26–31 Hz band** | **34.6 s ≥50 km/h, 23.0 s ≥80** against V84's 354.6 / 151.0. `score/score_v85_r6e_bands.py` hard-codes `DO_NOT_SCORE = {"26-31"}` for this route. **The number is computed and printed so it exists; it is not a verdict in either direction.** |
| **V83a/`68`** | 🛑 **highway and 26–31 Hz** | 37.1 s ≥50 / 19.2 s ≥80. Same class as V85. The *"damper-dose model of the ring is FALSIFIED"* headline was **retracted** partly for this. |
| **V68/`4e`** | 🛑 **creep, and every engaged-vs-manual test** | **1 creep window** (n=1). Its creep null is *undefined* in `B1b`. Zero manual windows. |
| **V67/`47`** | ⚠ creep is thin | 11 creep windows / 7 blocks, against 619 windows above 80 km/h. **V67 is a highway route with a creep footnote**, and it has been read the other way round. |
| **V80/`66`** | ⚠ every band | engaged fraction **32.9%**, and its `>80 km/h` row is a **3-block** sample sitting 20–40× above every other build (18–22 Hz = 1791.6, 26–31 Hz = 2338.6). Those are the limit-cycle windows, not a band level. |

### The band table — engaged, `e_band` = p99 analytic band envelope AMPLITUDE of the torsion bar, counts (p-p = 2×)

**CREEP < 10 km/h** — the stratum both scored symptoms live in

| build | n | blk | **6–9 Hz** (micro-ratcheting) | **18–22 Hz** (grinding) | **40–49 Hz** | **32–38 Hz** ctrl | 26–31 Hz 🛑 |
|---|---|---|---|---|---|---|---|
| V76 | 24 | 11 | 416.6 [256.1, 600.6] | 307.3 [80.2, 674.7] | 38.8 [27.1, 61.0] | 40.4 [20.4, 43.4] | 90.7 |
| V80 | 35 | 11 | 78.3 [39.7, 332.8] | 32.8 [12.6, 73.9] | 15.4 [9.6, 65.5] | 18.0 [12.0, 104.0] | 11.7 |
| V67 | 11 | 7 | 1159.7 [341.5, 1623.6] | 654.3 [240.2, 711.6] | 58.0 [37.5, 134.1] | 43.7 [31.5, 50.4] | 91.5 |
| V68 | — | — | 🛑 n=1, no sample | 🛑 n=1 | 🛑 n=1 | 🛑 n=1 | 🛑 n=1 |
| V81 | 25 | 11 | 314.1 [166.7, 616.4] | **69.4 [53.8, 104.3]** | 30.8 [22.2, 71.0] | 40.8 [22.5, 53.9] | 134.6 |
| V83a | 24 | 7 | **1713.9 [534.9, 1865.1]** | **1269.5 [887.2, 1441.5]** | 128.6 [67.3, 163.2] | 112.1 [40.9, 134.7] | 246.6 |
| V84 | 15 | 7 | 261.6 [115.4, 975.4] | 484.1 [158.0, 1241.3] | 41.1 [33.3, 82.5] | 38.1 [10.8, 56.4] | 68.0 |
| **V85** | **68** | **15** | 1112.2 [700.1, 1550.2] | 486.2 [310.3, 642.3] | 49.8 [41.6, 65.8] | 44.7 [36.0, 56.7] | 97.5 |

**10–40 km/h**

| build | n | blk | 6–9 Hz | 18–22 Hz | 40–49 Hz | 32–38 ctrl | 26–31 🛑 |
|---|---|---|---|---|---|---|---|
| V76 | 111 | 24 | 254.9 | 118.6 | 54.3 | 42.9 | 72.6 |
| V80 | 66 | 17 | 179.8 | 128.0 | 219.9 | 139.9 | 132.2 |
| V67 | 89 | 22 | 387.8 | 125.3 | 57.8 | 37.3 | 77.1 |
| V68 | 13 | 3 | 194.6 | 75.0 | 50.9 | 55.9 | 103.3 |
| V81 | 130 | 29 | 215.3 | 78.9 | 54.0 | 41.7 | 63.1 |
| V83a | 157 | 25 | 613.7 | **494.7** | 88.6 | 52.4 | 99.2 |
| V84 | 74 | 17 | 643.8 | 163.1 | 58.6 | 44.8 | 93.1 |
| V85 | 147 | 27 | 492.4 | 143.0 | 65.7 | 45.4 | 72.9 |

**40–80 km/h**

| build | n | blk | 6–9 | 18–22 | 40–49 | 32–38 ctrl | 26–31 🛑 |
|---|---|---|---|---|---|---|---|
| V76 | 160 | 27 | 217.3 | 75.9 | 60.4 | 34.0 | 52.1 |
| V80 | 90 | 18 | 131.1 | 82.8 | 158.3 | 90.2 | 73.7 |
| V67 | 143 | 27 | 214.2 | 64.5 | 74.6 | 42.9 | 62.1 |
| V68 | 85 | 15 | 124.8 | 54.9 | 41.5 | 27.9 | 49.0 |
| V81 | 305 | 49 | 136.7 | 59.1 | 52.7 | 33.7 | 48.2 |
| V83a | 28 | 7 | 191.4 | 150.6 | 76.0 | 49.4 | 54.6 |
| V84 | 198 | 31 | 265.1 | 77.0 | 81.8 | 48.1 | 69.6 |
| V85 | 33 | 7 | 271.0 | 118.4 | 72.9 | 47.1 | 81.9 |

**> 80 km/h** — 🛑 **V83a and V85 are UNSCOREABLE here (4 blocks each); V80's 3-block row is limit-cycle windows**

| build | n | blk | 6–9 | 18–22 | 40–49 | 32–38 ctrl | 26–31 🛑 |
|---|---|---|---|---|---|---|---|
| V76 | 33 | 5 | 117.6 | 63.7 | 44.1 | 37.7 | 39.9 |
| V80 | 24 | 3 | 818.2 | **1791.6** | 217.9 | **227.0** | **2338.6** |
| V67 | 619 | 83 | 69.3 | 33.3 | 39.1 | 25.0 | 43.3 |
| V68 | 81 | 13 | 81.2 | 34.2 | 39.4 | 37.0 | 33.6 |
| V81 | 35 | 6 | 112.0 | 65.7 | 48.5 | 35.4 | 64.4 |
| V83a | 15 | 4 | 🛑 137.4 | 🛑 64.4 | 🛑 53.1 | 🛑 41.3 | 🛑 42.7 |
| V84 | 118 | 16 | 85.3 | 42.5 | 51.3 | 35.8 | 52.5 |
| V85 | 18 | 4 | 🛑 111.7 | 🛑 61.5 | 🛑 62.1 | 🛑 46.4 | 🛑 54.9 |

### Operator's verbatim verdicts — family A builds

| build | route | HIS words |
|---|---|---|
| **V76** | `65` | *"There is still grind #1 and micro-ratcheting at creep."* |
| **V80** | `66` | *"loud, strong, felt through the whole car, ~90% of LKAS-engaged time, **noticeable vehicle instability**."* 🛑 Worst grinding ever recorded, **and no fault** ⇒ a stability failure. |
| **V67** | `47` | *"Grind #2 seems mostly gone… but a higher-speed grind #2 on lane changes/turns, only LKAS-engaged."* |
| **V68** | `4e` | *"Definitely felt the grind-#2-like vibration when changing lanes."* |
| **V81** | `67` | *"all grinding stopped the instant LKAS disengaged; hand mass did not damp it; **highway was worst**; manual steering much heavier when engaged, even turning WITH the command."* |
| **V83a** | `68` | 🛑 **"Feels just like V38, like we have made no progress since then."** — and it was a **byte fact**. |
| **V84** | `6d` | *"grind #1 barely got better, might just be placebo… 2 instances of grind #2… **Both microratcheting and ratcheting were very obviously present**."* Then: 🛑 **"None of these have been fully fixed in V84."** |
| **V85** | `6e` | grinding *"still barely perceptible", "got a little bit better"* · micro-ratcheting *"seems like it got barely, perceptibly better (somewhat unsure)"* · 🛑 **ratcheting "was still unfixed"** · grind #2 *"I did not experience any grind #2 from my hard turning or on the highway"* — 🛑 **an absence of complaint is NOT a cure.** |

---

## 2.2 FAMILY B — the `e_18-22` yardstick (engaged creep **< 20 km/h**). 🛑 DO NOT MIX WITH 2.1

| build | route | date¹ | n | blk | r24 | r26 | **`e_18-22` [CI]** | operator |
|---|---|---|---|---|---|---|---|---|
| **V61** | `31` | 2026-07-31 | 26 | 4 | **0.000** | 1.000 | **2501.0** [1994.6, 2574.0] | *"significantly worse"*; LKAS **off**: *"grinding newly present"* |
| **V59** | `2c` | 2026-07-30 | 67 | 15 | 1.000 | 1.000 | 995.1 [394.8, 1340.3] | (ordinary commute) |
| **V64** | `35` | 2026-07-31 | 57 | 8 | 1.000 | 1.000 | 1031.4 [445.9, 1363.8] | *"The vibration/grinding at low speeds is not fixed."* |
| **V58** | `2b` | 2026-07-30 | 58 | 16 | 1.000 | 1.000 | 634.7 [291.3, 992.7] | (baseline) |
| **V69** | `4f` | 2026-08-04 | 107 | 23 | 1.000 | 1.000 | 745.9 [225.6, 1108.9] | — |
| **V70** | `50` | 2026-08-04 | 19 | 5 | 1.000 | 1.000 | 729.1 [40.2, 1013.6] | *"stiffer"* (mechanism REFUTED) |
| **V62** | `37` | 2026-07-31 | 129 | 29 | **2.000** | 2.000 | **268.0** [204.9, 335.9] | ★ **"Original grinding at 2–5 mph is gone!"** |
| **V65** | `3a` | 2026-08-01 | 176 | 29 | 2.000 | 2.000 | **94.0** [60.8, 181.1] | *"makes the entire car vibrate, almost like I have a subwoofer… happens regardless of LKAS engagement"* |
| **V65** | `3b` | 2026-08-01 | 49 | 14 | 2.000 | 2.000 | 144.7 [85.1, 202.3] | (same drive pair) |
| **V67** | `47` | 2026-08-01 | 28 | 13 | 2.452 | 0.167 | **110.7** [74.2, 172.1] | see 2.1 |
| **V68** | `4e` | 2026-08-03 | 7 | 2 | 2.452 | 0.167 | ⚠ 70.2 [58.3, 419.3] — **n = 7, 2 blocks** | see 2.1 |
| **V71b** | `54` | 2026-08-05 | 160 | 42 | 1.000 | 2.000 | 545.2 [348.6, 767.8] | *"I definitely experienced grind #1."* |
| **V71c** | `58` | 2026-08-05 | 49 | 12 | 0.931 | 1.000 | 223.0 [94.5, 356.4] | *"attenuated but still present"*; ranked V71c > V71b |
| **V72** | `59` | 2026-08-05 | 86 | 22 | 1.862 | 0.169 | 613.9 [310.6, 1187.1] | 🛑 settled the naming: **MICRO ≡ the 7.79 Hz line**, *"not audible, only felt in the column"* |

**Family-B split-half nulls (18–22 Hz):** stock pool [0.817, 1.266] · V62+V65 [0.856, 1.186] ·
V67+V68 [0.885, 1.131] · V71b [0.760, 1.258] · V71c [0.818, 1.261] · V72 [0.676, 1.528] ·
V69 [0.506, 2.120] · **V70 undefined (4 blocks)**.

🛑 **After RULE 7 the family-B "dose ladder" collapses to THREE mode-proof points: 0× (V61, much worse) →
1× (stock) → 2× (V62/V65).** V69's 4× and V70's 2× were **mode-10 `gain_B` and never happened.**

---

## 2.3 FAMILY C — V38 → V57. 🛑 NO CI, NO NULL. Verdicts only.

| build | route | date¹ | delivered | operator |
|---|---|---|---|---|
| **V38** | — | 2026-07-17 | LKAS authority ×2.13 (G1–G6) | 🛑 **the cause.** *"hard turns appear authority-limited by a feedback loop"* |
| V39 | — | 2026-07-19 | cave, r24 conditional zero | *"fixed neither symptom"* |
| V40 | — | 2026-07-19 | slew → 0xFFFF | ☠ **BRICK** — EPS lamp, no power steering |
| V41 | — | 2026-07-20 | cap table flat | *"boots and drives cleanly, fixed neither"* |
| V42 | — | 2026-07-20 | 🛑 six groups at once | ch.1 *"FIXED THE HARD-TURN RATCHET"*; ch.2 *"No effect"* ⚠ attribution **VOID** |
| V43 | — | 2026-07-21 | `0xC644A` → 32 | *"fixed neither symptom"* |
| V44 / V47 | — | 2026-07-20/21 | FactorC/E **m10/m11** | 🛑 **INERT BY MODE — UNTESTED, not falsified** |
| V45 / V46 / V48A | — | 2026-07-21 | slew / poles / SUM gate | null; *"no noticeable change"* |
| V48B | — | 2026-07-21 | 21.4 Hz notch biquad | ☠ **BRICK** — wheel spun full-authority at startup |
| V52C | — | 2026-07-24 | 12 Hz EMA on 19 carriers | *"did not fix the vibration; clearly changed manual feel"* 🛑 **no rlog exists** |
| V53 | `1a` | 2026-07-27 | `0xC62EA` → 0 | *"the steer-to-zero feature worked"* |
| V54 | `1b` | 2026-07-27 | authority probe | *"this drive exhibits the vibration issue"* |
| V55 | `1c` | 2026-07-28 | partition probe | *"demonstrated the vibration in a parking lot"* |
| V56 | `24` | 2026-07-29 | mute `gp-0x6ad4` | *"damping removed and a new few-Hz resonance"* 🛑 the *"new 8.69 Hz"* is **wheel order 1, a tyre** |
| **V57** | `28`,`29` | 2026-07-29 | LKAS-gain decouple | ★★★★ **"grinding is not 7.4 Hz, that is the ratcheting."** — the mapping's anchor |
| V60 | — | 2026-07-31 | `0xD2006` 102→43 | *"It did not fix the vibration issue."* |
| V73 | `5a` | 2026-08-05 | `0xC407E` → 850 | *"grind #1 audible, micro-ratchet not"* |
| V74 | `5d`,`61` | 2026-08-06 | first ENGAGED damper | ☠ **HARD FAULT** on route `61` |
| V75 | `5e` | 2026-08-06 | FactorC 566 / FactorE X[1] 200 | *"got rid of the audible grind #1 and strongly attenuated the micro-ratcheting… then a hard fault"* ☠ |

¹ session/handoff date, proxy for drive date.

---

# PART 3 — THE NULL, STATED UP FRONT

## 3.1 The split-half null, confirmed from the data, PER BAND

Method: `_grind2_lib.split_half_null` — randomly halve the build's **own** episodes, run the **identical**
cell-stratified estimator, 300 halvings. **Any effect inside this interval is not distinguishable from
route/exposure noise.** Verified from `_scratch/cache/r6e/score_v85_bands.json`.

| band | tightest build (widest exposure) | **widest build** | the null a V85-vs-V84 ratio is judged against |
|---|---|---|---|
| **6–9** | V67 [0.817, 1.236] (862 win) | V84 [0.694, 1.520] | **[0.69, 1.52]** |
| **18–22** | V67 [0.879, 1.145] | V80 [0.598, 1.562] | **[0.63, 1.50]** ← ✅ **this is the origin of the quoted figure**: min(V85 0.628, V84 0.777), max(V85 1.504, V84 1.270) |
| **40–49** | V67 [0.868, 1.148] | V80 [0.631, 1.608] | [0.69, 1.38] |
| **32–38** ctrl | V67 [0.878, 1.156] | V80 [0.642, 1.524] | [0.71, 1.39] |
| **26–31** | V76 [0.828, 1.213] | V83a [0.707, 1.495] | [0.71, 1.39] |
| **30–49** | V67 [0.869, 1.146] | V80 [0.677, 1.473] | [0.71, 1.48] |

⇒ ✅ **CONFIRMED: a ratio must clear ~1.5 (or fall below ~0.67) to mean anything**, on every band, at
the exposures this corpus actually has. **The null is set by the WORSE-exposed arm**, so a route like
`6e` or `68` cannot produce a tight verdict no matter how the analysis is done.

🛑 **The creep-only null is far wider and is the one that governs the creep verdicts:**
V85 6–9 Hz **[0.593, 1.944]**, 18–22 Hz [0.675, 1.555], 40–49 Hz [0.479, 1.964];
V80 6–9 Hz **[0.241, 3.690]**, 18–22 Hz **[0.203, 4.962]**.
**V76, V67, V81 and V84 have NO defined creep null at all (NaN — too few blocks), and V68's is undefined.**
⇒ 🛑 **A creep-stratum ratio for those builds cannot be scored against its own noise floor.**

## 3.2 The exact scripts and functions a downstream agent must reuse

**Do not write a new instrument.** Score a new route by adding **one row**:

```
rlog-tools/score/score_v85_r6e_bands.py          # ADD YOUR ROUTE HERE — copy this file's pattern
  └─ imports score_v84_r6d as S            # the harness: register(), PARKED, augment3(), eng(), man()
       └─ imports compare_v75_v76_v80_grind as M   # BANDS_EXT, STRATA, PARKED, frac_ci()
            └─ imports _grind2_lib as G            # ★ THE INSTRUMENT
       └─ imports compare_r67_v81_grind as C67     # owns the V81/r67 registration (register5())
       └─ imports _r47_lib as R47                  # augment()
```

| you need | call **exactly** this |
|---|---|
| build the window records | `S.augment3(M.augment2(R47.augment(G.wrecs(build))))` |
| band envelope (the number in every table) | `G.win_env(xw, fs, lo, hi, taper, cw)` → **p99 of the analytic band envelope**, linear-detrended, Hann-tapered, read over the **central 60%** with the taper divided back out |
| **the null — run this FIRST** | `G.split_half_null(recs, "e_<band>", RNG, nrep=300, min_ep=2, min_win=4)` |
| cross-build ratio | `G.boot_cellwise(engA, engB, "e_<band>", RNG, nboot=1500, min_ep=2, min_win=4)` |
| single-build median | `G.boot_median_ci(recs, "e_<band>", RNG, nboot=1500)` |
| duty above a threshold | `M.frac_ci(recs, "e_18-22", thr, RNG, nboot=2000)` |
| the ~7.79 Hz line (Part 4) | `relay_fingerprint_r6e.windows()` + `.spectra()` + `.prom_at(r, 7.79, half=0.5)` + `._boot_med` |

**Non-negotiable settings:** `NFFT = 256`, `HOP = 128`, `G.EPKEY = "blk"` (~10.2 s blocks; `"ep"` is
reported as a sensitivity check only), `CIRC = 2.0805`, strata
`[creep <10, 10–40, 40–80, >80 km/h]`, negative control `32-38`.

🛑 **Load the other builds, never recompute them.** `score_v85_r6e_bands.build_records()` opens
`_scratch/cache/r6d/records_v84_score.pkl` **read-only** and asserts `__bands__ == sorted(M.BANDS_EXT)`. That is
what makes V84's numbers here bit-identical to the ones already reported for route `6d`. **A new script
that rebuilds them has silently changed the column.**

## 3.3 Speed matching and wheel-order cleaning — how it is actually done

**Wheel order n sits at `n · v / 2.0805` Hz and MOVES WITH SPEED.** Circumference is 2.073–2.088 m on
record; the scripts use **2.0805**.

Three defences, all already implemented:

1. **Cell stratification (the primary defence).** `G.boot_cellwise` computes a **weighted log-ratio over
   cells occupied by BOTH routes**, where a cell is
   `(engaged, v-bin, effort-bin, |rate|-bin)` with
   `V_BINS = [0–0.5, 0.5–2, 2–4, 4–8, 8–14, 14–30] m/s`, `E_BINS = [0–200, 200–800, 800–2000, 2000+]`,
   `R_BINS = [0–4, 4–16, 16–32, 32+] °/s`. Weight `w_c = 1/(1/nepA_c + 1/nepB_c)` ⇒ **a cell one build
   barely visited cannot dominate.** A cell needs `min_ep` episodes and `min_win` windows on **both**
   sides or it is dropped.
2. **A mandatory per-window speed census (B0b)** printed **before** any averaged comparison, plus a
   **wheel-order contamination table**: the % of engaged windows whose order-1 and order-2 lines land
   **inside** each band. On route `6e`, **order 2 lands inside 6–9 Hz on 20.7% of engaged windows**,
   against `6d`'s 6.7% and `67`'s 8.7%.
3. **Explicit order-cleaning (W0)** — drop every window whose order-1…order-4 line falls in the band
   being scored, then re-run the identical estimator.

### 🛑 The retraction this machinery produced — and it is the template

| pair, 6–9 Hz | all windows | **order-CLEAN** | dropped |
|---|---|---|---|
| V85/V84 | 1.088 [0.725, 1.456] | 0.925 [0.608, 1.671] | V85 134/266, V84 192/405 |
| **V85/V81** | **1.625 [1.191, 2.059]** — *"V85 worse than V81"* | 🛑 **1.273 [0.853, 2.507] — INSIDE the null** | V85 134/266, V81 317/495 |
| V84/V81 | 1.432 [1.097, 1.770] | 1.346 [0.952, 2.029] | — |

⇒ **The 6–9 Hz "V85 is worse" result was a PURE WHEEL-ORDER ARTEFACT.** The 18–22 Hz result **survives**
order-cleaning (1.957 → **1.928**), which is what makes it reportable. 🛑 **Order-clean every 6–9 Hz
ratio before quoting it. The band-centre test alone is NOT sufficient — run the per-window census too.**

**Road-roughness falsifier (B2):** chassis vertical IMU 20–49 Hz envelope over the same cells.
V85/V84 **0.958 [0.705, 1.136]**, V85/V81 0.900, V85/V83a 0.930, V84/V81 1.074. ⇒ V85's road was
*smoother*, i.e. moving **for** V85 — so V85's higher bands are not a rougher road.

**Validity check (B7a):** 1–4 Hz driver input must **not** differ once cells are matched —
V85/V84 **1.005 [0.745, 1.436]**, V85/V81 1.084, V85/V67 1.011. ✅ holds on every pair.

---

# PART 4 — THE ~7.79 Hz RATCHET LINE ACROSS V81 / V83a / V84 / V85

**Instrument:** `relay_fingerprint_r6e.windows()` + `.spectra()`, NW = 1024 (10.13 s), hop 512, bar
channel, engaged arm, `blk` episode bootstrap (2000 draws). **V83a was never in the fingerprint's route
table** — it was added here with `_scratch/cache/r68x` / `r68xs` / parked `[0, 7]`, exactly as
`score/score_v84_r6d.py` registers it. Prominence uses **`half = 0.5`**, T3's own half-width.
✅ **Reproduces the published values bit-for-bit:** V85 prominence 17.10, V84 6.37, V81 5.36.

| build | route | n | blk | **centre f_c (Hz), 95% CI** | **prominence at 7.79 Hz** | **a779 (counts)** | **slope Hz per m/s** | frac argmax within 0.6 Hz of 7.79 | **ENG/MAN** (a779) |
|---|---|---|---|---|---|---|---|---|---|
| **V81** | `67` | 105 | 55 | **8.736 [8.496, 9.226]** | 5.36 [4.98, 6.22] | 145.2 [118.9, 196.0] | **−0.0004 [−0.048, +0.044]** | 22.9% | 1.39 ⚠ nM=12 |
| **V83a** | `68` | 47 | 25 | **8.186 [7.884, 8.316]** | 9.06 [5.76, 15.85] | 549.2 [442.9, 741.2] | **+0.0999 [+0.009, +0.172]** | 63.8% | 7.92 ⚠ nM=6 |
| **V84** | `6d` | 87 | 45 | **8.479 [8.227, 9.086]** | 6.37 [4.74, 8.81] | 275.1 [170.4, 351.2] | **+0.0333 [−0.020, +0.089]** | 40.2% | 179.15 ⚠ nM=14 |
| **V85** | `6e` | 57 | 30 | **8.207 [8.108, 8.311]** | 17.10 [10.01, 26.00] | 597.6 [442.0, 782.4] | **+0.0740 [+0.039, +0.139]** | 66.7% | 1.90 ⚠ nM=9 |

**Wheel order 2 predicts a slope of +0.961 Hz per m/s. A fixed line predicts 0.000.**
⇒ ✅ **The line is SPEED-INVARIANT on every build** — the largest slope (V83a, +0.0999) is **9.6× below**
the order-2 prediction and its CI excludes +0.961 by an order of magnitude. **This is the firmware ridge,
not a tyre.**

### 🛑 Three readings that must travel with this table

1. **PROMINENCE IS A RATIO TO THE LOCAL FLOOR, NOT AN AMPLITUDE.** V85's 17.10 vs V81's 5.36 is
   **3.2×**, and it is a **FLOOR EFFECT** — V85 drove slower on a smoother road (cell-matched IMU
   **0.958**), which lowers the floor and raises prominence with **no change in the line itself.**
   The amplitude column (`a779`) is the one to rank on.
2. **The speed-matched ABSOLUTE amplitude is the real trend** (P2, equal weight per shared v-bin):
   **V85/V81 = 2.742** over 6 shared bins · **V85/V84 = 0.850** over 5.
   ⇒ **the line grew ~3× at V84 and V85 KEPT it.** My independent pooled medians agree in direction:
   V81 145.2 → V84 275.1 → V85 597.6, with V83a already at 549.2.
3. 🛑 **The ENG/MAN column is a POINT ESTIMATE ONLY.** Manual arms are **6–14 windows** on all four
   routes (V84's manual `a779` = **1.5 counts** on 14 windows, which is what makes its ratio read 179×).
   **Do not score a build on it.** The properly-powered engaged/manual statement on record is V70's
   **73/88 = 83.0% engaged vs 0/118 manual, Fisher p = 3.8e-41**, and that the rate is
   **build-independent (80/81/79/94%) ⇒ no build has ever moved it.**

### What this constrains for V87

The line is **not a relay** (odd/even comb **0.858 [0.739, 1.000]** against a positive control firing at
**1.204** on only 15% injection; 3:1 PLV z ≤ 1.05; switching-surface excess **−0.0375**) and **not a plant
resonance** (the wheel-on-torsion-bar mode is **12.8 Hz [12.1, 13.6]**, *above* it; 7.79 Hz is unreachable
through the plant, floor 12.65 Hz). ⇒ **a LINEAR loop oscillation whose frequency is set by accumulated
estimator lag** `[BELIEF]`.

**V86's pre-registered test is a FREQUENCY ratio**, `f(V86)/f(V85) ∈ [0.797, 0.875]`, i.e. the peak must
land in **[6.2, 6.9] Hz**. Against V85's measured centre of **8.207 [8.108, 8.311]** that is a shift of
**≈ 1.3–2.0 Hz, or 13–20 FFT bins at NFFT 1024 / fs ~101 Hz** — comfortably resolvable by this
instrument. 🛑 **Score it on `f_c` with the CI above, not on amplitude: amplitude ratios have failed four
builds running against a [0.63, 1.50] null, and V85's own centre CI is only ±0.10 Hz wide.**

---

## Reproducing Part 4

`_scratch/cache/r6e/_v87_ratchet_line_ladder.json` holds the values. The generator adds V83a to
`relay_fingerprint_r6e`'s route table and bootstraps `f_free` over `blk`; run it from `rlog-tools/`.
