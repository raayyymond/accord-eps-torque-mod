# V290 — WHAT BASE DOES IT SIT ON?  V282 or V289?

**Agent** `basepick` (SUBAGENT; orchestrator `main`). **Analysis only — nothing built, flashed or sent.**
Date 2026-09-09.

**Scripts (everything below reproduces from these four, and only these four)**

| script | what it produces |
|---|---|
| `rlog-tools/studies/grind/basepick_v290.py [kd\|table]` | the Kd interaction sweep, the decision table, the full 8–30 Hz pole census, the notch shapes → `_scratch/basepick_v290_{kd,table}.txt` (+ `.json`) |
| `rlog-tools/studies/grind/basepick_kd_reach.py` | the DELIVERED Kd per regime, off the wire → `_scratch/basepick_kd_reach.txt` |
| `rlog-tools/studies/grind/basepick_effective_kd.py` | every metric on a fine Kd grid, read off at each regime's delivered Kd → `_scratch/basepick_effective_kd.txt` (+ `.json`) |
| the scratchpad CRC/diff probes | the CRC block map and the V282↔V289 image diff (reproduced inline in §8) |

**Inputs read, not re-derived:** `reconcile_v290.py`'s `ElecP` feedback placement; `design290b_candidates.py`'s
`Elec` / `metrics` / `step_lin` / `plant_free` / `mkplant` / `rbj`; `_scratch/design290b_family.json` (304 fits,
**121** linear-stable on V289, **87** also burst-consistent); `reqaxis`'s byte-exact `demand()` mirror in
`kpkd_axis_r62_r63.py`; the census episode cache `_scratch/grind1_census_v289_r62_r63_cache.pkl`; route caches
`r62_v289`, `r63_v289`, `r5e_v288`; `paramod`'s parametric-hazard verdict (`docs/review/V290-PARAMETRIC-HAZARD-2026-09-09.md`).

---

## 0. THE ANSWER

> # 🛑 **V290 SITS ON THE V282 BASE.**
>
> **Not because the revert is safe, and not because V289 failed — V289's notch did exactly what it was
> aimed at. Because every option that survives the operator's own constraints is a fresh image built from
> V282, and the V289 base is carried forward by none of them.**
>
> **Recommended build: option A′ — V282 + a scheduled Kd, `0xE511C` `Y = (112, 112, 112, 128)`.
> 6 cal bytes, ONE CRC trailer (`0xE5FFC`), no cave, no code byte, no new hook.**
> Second choice, if the operator wants the larger dose and will accept ~1.7 % more 7 Hz ring:
> **option A, `Y = (96, 96, 96, 128)`.**

**Why the V289 base loses, in two sentences.** Its unique asset — the emptied 18–22 Hz band — is bought with
a **capped-step transient-authority loss of 19–26 % that NO calibration edit recovers** (pkR_med 0.799–0.806
at every Kd from 64 to 128; the loss lives in the reference transfer `fwd()`, not in the loop), and it leaves
a **16.1–16.9 Hz pole present in 100 % of the surviving fits** — the object the operator is hearing right now,
three times louder than the one it replaced. Reverting to V282 hands the 20 Hz mode back, but the scheduled Kd
damps that mode at **zero measurable authority cost**, and by the operator's own report the 20 Hz line was the
*quieter* of the two symptoms.

**The risk statement, before the drive.** Option A′ **does not remove the 20 Hz line — it damps it.**
The 19.8 Hz pole stays, ζ 0.038 → 0.056 at cruise (ring-to-10 % 545 ms → 360 ms, 10.9 → 7.1 cycles), and the
worst-case sensitivity peak `Ms` falls 19.4 → 7.4. Authority is untouched at both yardsticks: capped-step
pkR **0.995–0.997**, 7 Hz gate **1.006–1.010**, steady-state ×1.000, t90 13 ms unchanged. HF noise into the
motor goes **down** (×0.88). No fit destabilises. **The honest ceiling: in the measured grinding population
the schedule delivers only Kd 117–124 of 128, so ζ there improves ×1.3–1.5, not ×1.7.** If the operator still
hears grinding on A′, that is an informative null, not a wasted drive — it says the ring is not Kd-reachable
in the band where he hears it, and the next lever is the feedback-operand notch (option C), on the same base.

---

## 1. THE TWO OBJECTS ARE DIFFERENT, AND EVERY OPTION MUST BE SCORED AGAINST BOTH

EVIDENCE — all poles 8–30 Hz over the 87 burst-consistent fits (`basepick_v290.py table`, TASK 3).
`frac` = poles per fit in the band (a fit can contribute two).

| candidate | **18–22 Hz — the "20 Hz line"** | **15–18 Hz — the "16 Hz crossing"** |
|---|---|---|
| **V282** (the revert) | frac **1.47**, f 19.94, ζ_med **+0.038**, ζ_min +0.013 | frac 0.17, ζ_med +0.503 → **absent** |
| **V289 rev 1** (on the car) | frac **0.38**, f 21.64, ζ_med +0.081 → **emptied** | frac **1.00**, f **16.66**, ζ_med **+0.033**, min +0.020 |
| **A** V282 + Kd Y0=96 | frac 1.30, f 19.69, ζ_med **+0.076**, min +0.029 | frac 0.48, ζ_med +0.501 → **absent** |
| **A′** V282 + Kd Y0=112 | frac 1.38, f 19.76, ζ_med **+0.056**, min +0.021 | **absent** |
| **B** V289 + Kd Y0=96 | frac 0.77, ζ_med +0.406 → emptied | frac **1.00**, f **16.14**, ζ_med +0.063, min +0.043 |
| **C** V282 + fb-notch 21.5 Q1.5 + fb 40 | frac 0.34, f 21.51, ζ_med **+0.113** → emptied | frac **1.00**, f **16.53**, ζ_med +0.057, min +0.035 |
| **D** C + Kd Y0=96 | frac 0.43, ζ_med +0.113 → emptied | frac 0.93, f 15.87, ζ_med **+0.089**, min +0.066 |

**Read this table and the base question answers itself.**

1. **The 20 Hz object is a real, lightly damped pole on V282** (ζ 0.038, ζ_min 0.013 — the least-damped thing
   in the whole family) and reverting *does* hand it back. That is not a reason to keep V289.
2. **Every notch-class option re-creates the 16 Hz object.** C's 16.53 Hz ζ_med +0.057 is the *same pole* as
   V289's 16.66 Hz ζ_med +0.033, at 1.7× the damping — a better version of the thing the operator has just
   told us he hears, louder, in trains. This is structural: killing loop gain at 20 Hz drops the crossover
   into 15–17 Hz. **It is not a defect of V289's tuning; it is what the class does.** 🛑 BELIEF-level
   consequence: ζ 0.057 may still be audible, because V289's *median* ζ was 0.033 and its measured burst
   ζ_eff spanned 0.02–0.13 — C sits inside the range the operator already rejected.
3. **The Kd class is the only one that does not create the 16 Hz object at all.** On the V282 base a Kd cut
   moves nothing into 15–18 Hz (ζ_med stays +0.50, i.e. no resonance), it just damps the pole that is
   already there. **That is the whole argument for A/A′.**

---

## 2. 🛑 THE MODELLING CORRECTION THAT CHANGES EVERY EARLIER SCORE OF THIS LEVER

`design290b` and `reconcile_v290` scored "Kd 96" as a **flat** Kd 96 and got `gate73 = 1.073` (a hard FAIL)
and `pkR_med = 0.942`. **Both numbers are wrong for a scheduled Kd, and not conservatively wrong — wrong in
the direction that rejects a good lever.**

The Kd record's X axis is the **DEMAND INDEX**, and the record is `X = (0, 11, 22, 32)`, `Y = (128,128,128,128)`
— EVIDENCE, byte-read from **both** the V282 and V289 plain images at `0xE511C`
(`04000000 0b00 1600 2000 8000 8000 8000 8000 0000`); axis chain and layout from
`reference_accord_kp_kd_schedule_axis_is_the_demand_index`. `0x29EA0` clamps the lookup at `X[3] = 32`.

MEASURED delivered mean Kd per regime under row S (`Y[0..2]=96`), straight off the wire
(`basepick_kd_reach.py`, r62 / r63 / r5e_v288):

| regime | idx p50 | **delivered mean Kd, row S** | row S′ (Y0=112) |
|---|---|---|---|
| 25 m/s cruise | 3 | **96.0 / 96.1 / 96.0** — the full dose | 112.0 ×3 |
| all engaged | 5 | 101.4 / 102.0 / 102.7 | 114.7 / 115.0 / 115.3 |
| **census grinding episodes** | 8 / 46 / 37 | **106.5 / 118.9 / 115.5** — only a third of the dose | 117.3 / 123.5 / 121.7 |
| **capped step** (the pkR yardstick) | 110 / 86 / 88 | **124.9 / 122.8 / 123.6** — nearly untouched | 126.4 / 125.4 / 125.8 |
| **low-speed full-lock turn** (the 7 Hz gate) | 123 / 74 / 98 | **124.8 / 121.4 / 124.3** — nearly untouched | 126.4 / 124.7 / 126.2 |

(Cross-check: my r5e grinding mean 115.5 reproduces `paramod`'s independently computed 115.5 to 0.1 —
two scripts, two authors.)

⇒ **Read every column at the Kd its own regime delivers.** That is neither the optimistic (`Y[3]=128`) nor
the pessimistic (`Y[0]=96`) idealisation, and it is the number to quote.

---

## 3. THE DECISION TABLE — EFFECTIVE-Kd READING

EVIDENCE: `basepick_effective_kd.py`, 87 burst-consistent fits. Grinding ζ_w and the two authority columns
are read at each regime's delivered Kd (r62 / r63 / r5e). Cruise columns are at Y[0].

| # | option | base | bytes | CRC trailers | **cruise ζ_w** | **grinding ζ_w** | **capped-step pkR_med** | **7 Hz gate** | dc | Ms_w | noise | new peak 10–14 Hz | unstable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A′** | V282 + Kd (112,112,112,128) | **V282** | **6 cal** | **1** (`0xE5FFC`) | **+0.0214** | +0.0191 / 0.0166 / 0.0173 | **0.997 / 0.995 / 0.996** | **1.006 / 1.010 / 1.007** | 1.000 | 7.4 | ×0.88 | 1.2× | **0** |
| **A** | V282 + Kd (96,96,96,128) | **V282** | **6 cal** | **1** | **+0.0290** | +0.0239 / 0.0184 / 0.0198 | **0.994 / 0.990 / 0.992** | 1.010 / **1.017** / 1.011 | 1.000 | 4.6 | ×0.77 | 1.4× | **0** |
| Ap | V282 + paramod (96,96,112,128) | V282 | 6 cal | 1 | +0.0290 | ≈ A, slightly weaker | ≈ A | ≈ A | 1.000 | 4.6 | ×0.77 | 1.4× | 0 |
| **C** | V282 + fb-notch 21.5 Q1.5 + fb 40 | **V282** | 4 cal + **cave** | **3** | +0.0349 | +0.0349 (Kd-independent) | 0.971 (worst **0.928**) | 1.009 | 1.000 | 9.2 | **×1.91** | **2.0×** | 0 |
| **D** | C + Kd (96,96,96,128) | **V282** | 10 cal + **cave** | **3** | **+0.0546** | +0.0492 / 0.0412 / 0.0435 | 0.964 / 0.963 / 0.964 (worst 0.92) | 1.016 / **1.024** / 1.017 | 1.000 | 7.0 | ×1.46 | **3.9×** | 0 |
| C50 | V282 + fb-notch + fb 50 | V282 | 4 cal + cave | 3 | +0.0400 | +0.0400 | 0.960 (worst **0.908**) | **0.989** | 1.000 | 7.4 | **×2.21** | 1.6× | 0 |
| **B** | **V289** + Kd (96,96,96,128) | **V289** | 6 cal | 1 | +0.0433 | +0.0347 / 0.0259 / 0.0282 | **0.806 / 0.806 / 0.806** ❌ | 1.012 / 1.020 / 1.013 | 1.000 | 7.6 | ×1.08 | 3.3× | 0 |
| B′ | V289 + Kd (112,…) | V289 | 6 cal | 1 | +0.0306 | +0.0270 / 0.0229 / 0.0241 | **0.806** ❌ | 1.009 / 1.012 / 1.009 | 1.000 | 9.4 | ×1.24 | 2.2× | 0 |
| — | V282 as flown | — | 0 | 0 | +0.0129 | +0.0129 | 1.000 | 1.003 | 1.000 | 19.4 | ×1.00 | 1.0× | 0 |
| — | V289 rev 1 as flown | — | 0 | 0 | +0.0202 | +0.0202 | **0.805** (worst 0.745) | 1.005 | 1.000 | 14.1 | ×1.40 | 1.6× | 0 |

Supporting columns for A′/A/C/D, at the cruise dose (`basepick_v290.py table`): min |1+L| 0.135 / 0.215 /
0.109 / 0.143 · t90 13 ms on all four (V289: 15 ms) · Δphase at 3.9 Hz −2.5° / −5.1° / +0.6° / −4.5° ·
new peak 22–35 Hz 1.0× / 0.9× / 1.0× / 0.9× · ring-to-10 % at the median fit 360 ms (7.1 cycles) /
257 ms (5.0) / 387 ms (6.4) / 265 ms (4.2), against V282's 545 ms (10.9 cycles).

### Constraint compliance, stated per the operator's own thresholds

| constraint | A′ | A | C | D | B |
|---|---|---|---|---|---|
| steady-state authority ×1.000 | ✅ 1.000 | ✅ | ✅ | ✅ | ✅ |
| capped-step pkR ≥ 0.95, **median** | ✅ 0.995 | ✅ 0.992 | ✅ 0.971 | ✅ 0.964 | ❌ **0.806** |
| capped-step pkR ≥ 0.95, **worst fit** | ✅ (≈0.99) | ✅ (≈0.98) | ❌ **0.928** | ❌ **0.92** | ❌ **0.745** |
| 7 Hz gate ≤ 1.01 | ✅ 1.006–1.010 | ⚠ **1.010–1.017** | ✅ 1.009 | ❌ 1.016–1.024 | ⚠ 1.012–1.020 |
| no fit destabilised | ✅ 0/87 | ✅ 0/87 | ✅ 0/87 | ✅ 0/87 | ✅ 0/87 |

**A′ is the only row that passes every constraint on both the median and the worst-case reading.**

⚠ Two honest caveats on this table. (i) The 7 Hz gate for A is **1.010–1.017**, not the `1.003` an
idealised `Y[3]=128` reading gives — the full-lock regime delivers Kd 121–125, not 128. A therefore sits
**at or just over** the operator's limit on r63. `gate73` is near-linear in Kd (1.0028 at 128 → 1.0731 at 96,
+0.0022 per count), so substituting the regime-mean Kd is a fair approximation — but it is an approximation:
**EVIDENCE for the curve, BELIEF for the regime substitution.** (ii) C's and D's pkR **worst-fit** values
(0.928 / 0.92) fail the ≥ 0.95 floor even though their medians pass; V289's flown 0.91 was accepted as a
one-off and explicitly is not the new floor.

---

## 4. 🛑 THE OPTION-B INTERACTION TEST — the reason the question was not obvious

**The brief's fear:** the D term is the loop's lead element and carries ~88 % of |C| at 20 Hz; on the V289
base the crossing already sits at 16.6 Hz with little margin; **does cutting Kd there pull the crossing down
again, or destabilise it?**

**VERDICT: the fear is NOT borne out. Cutting Kd on the V289 base is stabilising, not destabilising — it is
option B's *authority* that kills it, not its stability.**

EVIDENCE — `basepick_v290.py kd`, 87 burst-consistent fits, V289 base:

| Kd | crossover wc (median) | PM_worst | ζ_worst | f @ ζ_worst | ζ_med | GM_worst | Ms_worst | min\|1+L\| | **pkR_med** | unstable |
|---|---|---|---|---|---|---|---|---|---|---|
| **128** (as flown) | 15.0 Hz | **+7°** | +0.020 | 15.6 Hz | +0.033 | 1.09 | 14.1 | 0.071 | **0.805** | 0 |
| 112 | 13.8 | +10° | +0.031 | 16.7 | +0.046 | 1.15 | 9.4 | 0.106 | **0.801** | 0 |
| **96** | 12.6 | **+12°** | **+0.043** | 16.4 | +0.059 | 1.20 | 7.6 | 0.132 | **0.799** | 0 |
| 80 | 11.7 | +12° | +0.047 | 22.1 | +0.071 | 1.22 | 7.0 | 0.142 | 0.800 | 0 |
| 64 | 10.8 | +11° | +0.049 | 22.1 | +0.083 | 1.22 | 7.7 | 0.131 | 0.807 | 0 |

- **The crossing does not move down** — f at the least-damped pole goes 15.6 → 16.4 Hz, *up*, and its ζ more
  than **doubles** (+0.020 → +0.043). The gain crossover `wc` falls 15.0 → 12.6 Hz, which is exactly what
  removing lead gain does, but **phase margin RISES** (+7° → +12°) because the plant's own phase is flatter
  down there. Gain margin rises 1.09 → 1.20, min|1+L| 0.071 → 0.132, worst-case Ms 14.1 → 7.6. **0 of 87
  fits destabilise at any Kd from 64 to 128.**
- **Same test on the C base** (rows in `_scratch/basepick_v290_kd.txt`): also stabilising — ζ_worst +0.035 →
  +0.055, PM +10° → +12°, 0 unstable. **Option D carries no destabilising Kd interaction either.**
- 🛑 **What kills option B is a different number in the same table: `pkR_med` is 0.799–0.807 at EVERY Kd.**
  The Kd schedule moves capped-step authority by **less than 1 %**, because V289's notch sits in `fwd()` —
  the reference transfer — not only in the loop. **No calibration edit on the V289 base recovers it.** The
  only fix is to move the notch to the feedback operand, and that is option C, which is a **new cave on the
  V282 base**. So even "keep V289's notch" leads to a V282-based image.

`paramod` separately cleared the *parametric* half of the same question — a scheduled Kd is a time-varying
gain, and its verdict was **row S is safe to build, no mitigation required**: 94–96 % of the Kd(t) modulation
energy is below 2 Hz, the knot-crossing rate inside grinding episodes is 1.2–3.5 /s against a 16–20 Hz ring,
the drive depth is 47–160× under V59's measured pump, and the measured Kd(t) trace through the byte-exact
clamped mirror never pumped (decay ≥ V282's in 9 of 9). `paramod` also judged its own `Y=[96,96,112,128]`
alternative **not worth the 4 extra bytes** — my table agrees (row Ap is indistinguishable from A on every
small-signal column, and reaches *less* of the population: **65–70 %** of engaged time at the full dose vs
**77–81 %** for row S, and **17–59 %** of grinding-episode time vs **25–66 %**).

---

## 5. WHAT EACH NOTCH ACTUALLY DOES — why V289's cost what it cost

EVIDENCE, Q14-rounded exactly as a build would round it (`basepick_v290.py`, TASK 4):

| f | 14 Hz | 16 Hz | 16.6 Hz | 18 Hz | 20.0 Hz | 21.5 Hz | 24 Hz |
|---|---|---|---|---|---|---|---|
| **V289** notch 20.04 Q3 \|N\| dB | −0.8 | −1.9 | **−2.5** | −5.3 | **−39.3** | −8.2 | −2.6 |
| **V289** arg | −24° | −36° | **−41°** | −57° | −89° | +67° | +43° |
| **C** notch 21.5 Q1.5 \|N\| dB | −1.9 | −3.5 | −4.2 | −6.5 | **−13.4** | −56.2 | −10.1 |
| **C** arg | −37° | −48° | **−52°** | −62° | −78° | −90° | +72° |

C's Q14 integers: `b = [15680, −31074, 15680]`, `a = [16384, −31074, 14976]`.

**The skirt is the cost, and C's skirt at 16 Hz is WORSE, not better (−48° vs −36°).** C survives only
because the *placement* changes: on the feedback operand the same return ratio is obtained with the filter
absent from `fwd()`, so the phase is spent on the loop but not on the reference. **This is why C keeps
pkR ≈ 0.97 while the identical element forward-placed gives 0.78.** It also explains why C still puts a
16.5 Hz pole in 100 % of fits — the loop phase is spent either way.

---

## 6. RANKING

| rank | option | one-line case | one-line risk |
|---|---|---|---|
| **1** | **A′** V282 + Kd (112,112,112,128) | The only row passing every constraint on median AND worst case; damps the 20 Hz pole ζ ×1.65 at cruise, Ms 19.4 → 7.4, ring 545 → 360 ms, at **zero** measurable authority cost and **less** motor noise; 6 cal bytes, 1 CRC trailer, no cave. | **Small dose.** In grinding it delivers Kd 117–124 of 128 → ζ only ×1.3–1.5. The 20 Hz line is damped, not removed. May be an audible-null. |
| **2** | **A** V282 + Kd (96,96,96,128) | ~2× the dose: ζ ×2.2 at cruise, Ms 19.4 → **4.6**, ring 545 → **257 ms**, pkR still 0.990–0.994. | 7 Hz gate **1.010–1.017** — at/over the operator's limit on one of three routes. His bookmarks sit on exactly that manoeuvre. **His call, not mine.** |
| **3** | **C** V282 + fb-operand notch 21.5 Q1.5 + fb 40 | Kills the 20 Hz object as thoroughly as V289 did (18–22 ζ_med +0.113) while keeping pkR_med 0.971 — the fix for V289's real defect. | **Re-creates the 16.5 Hz pole** (frac 1.00, ζ_med 0.057) the operator is complaining about *now*; pkR worst 0.928 fails the floor; ×1.91 HF noise into the motor; new 10–14 Hz sensitivity peak 2.0×; a **new cave at a hook that has never flown**, 3 CRC trailers. |
| **4** | **D** C + Kd (96,…) | Best small-signal numbers in the table (ζ_med +0.089 at 15.9 Hz, +0.113 at 21.4 Hz). | Everything wrong with C, **plus** gate 1.016–1.024 (fails), and the Kd protection of the new 16 Hz pole applies only at cruise — 56–67 % of grinding time sits above idx 32 where D **is** C. Two levers, one drive: uninterpretable. |
| **5** | Ap paramod (96,96,112,128) | — | Dominated by A: same small-signal, less reach, 0 byte saving. `paramod` says the same. |
| ❌ | **B / B′** on the V289 base | — | **pkR 0.806 at every Kd**, unrecoverable by calibration; keeps a 16.1–16.4 Hz pole in 100 % of fits. **Do not build.** |

---

## 7. WEIGHTING THE FIT-FREE MEASURED FACTS ABOVE THE FAMILY

Per `modenat2`'s standing instruction, the family numbers above are subordinate to these. All four point the
same way:

1. **The demand-gated census / the empty 18–22 Hz band on V289** (0 of 1414 present windows vs 501 on V282,
   prevalence ×34): the notch works on the 20 Hz object. ⇒ *do not conclude V289 failed;* conclude its
   **placement** failed. That is what routes the decision to option C-on-V282 rather than to option B.
2. **The measured relocation** — the line moved to 15–17 Hz, **3× louder**, in trains, and the operator says
   "grinding is still an issue". ⇒ a 16 Hz pole at ζ 0.033 is *worse for him* than a 20 Hz pole at ζ 0.038.
   **This is the single fact that demotes every notch-class option below the Kd class**, because C re-creates
   a 16.5 Hz pole at ζ 0.057, inside the range he has already rejected.
3. **The demand-axis distribution** (idx p50: cruise 3, grinding 8/46/37, capped step 86–110, full-lock
   74–123): the Kd schedule reaches cruise fully and grinding only partly, and **does not touch either
   authority yardstick.** This fact alone overturns `design290b`'s and `reconcile`'s rejection of the lever.
4. **The 16.63 Hz plant point, the matched-load Kp contrast and the clamp null** — I did **not** re-derive
   these; they are `modenat2`'s and `advnull`'s. They were used only through `design290b_family.json`, whose
   87-fit sub-family is already conditioned on the measured V282 (20.0 Hz) and V289 (15.6–17.3 Hz) poles and
   on the V289 burst decay ζ_eff 0.02–0.13. **BELIEF, not my EVIDENCE.**

---

## 8. THE FLASH PATH, HONESTLY

For the recommendation (**A′**, and identically for A):

- **Build a FRESH image from the V282 plain image**
  `_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`.
  Do **not** derive it from V289 — reverting a 107-byte cave in place is strictly more risk than not writing it.
- **Bytes written vs the V282 image: 6.** `Y[0]`, `Y[1]`, `Y[2]` of the Kd record at **`0xE5126`, `0xE5128`,
  `0xE512A`** (u16 LE), `112 → 0x7000` each (or `96 → 0x6000` for option A). `Y[3]` at `0xE512C` stays `128`.
  `X` at `0xE511E/20/22/24` stays `(0, 11, 22, 32)` — **strictly increasing, so the `divq` segment-width
  divide is safe.** Plus 4 bytes of CRC trailer ⇒ **10 bytes differ from the V282 image.**
- **CRC pages: exactly ONE.** EVIDENCE — the build toolchain's own `crc_block_map` on the V282 image
  (50 blocks) puts `0xE511C`, `0xE5126/28/2A/2C` **and** the Kp record `0xE5378` all in
  **`[0xE5000, 0xE5FFC)`**, trailer at **`0xE5FFC`**. Nothing else moves: the fb-pole cells `0xC63E8/EA` sit
  in `[0xC6000, 0xC6FFC)` and V289's cave `0xC4C00` + hook `0x2A174` sit in `[0x13000, 0xC4FFC)`, and A′
  touches neither.
- **Bytes differing from what is ON THE CAR (V289 rev 1): 195.** EVIDENCE — a full-image diff gives
  **185 differing bytes in 10 runs** between V282 and V289 rev 1 (hook `0x2A174` 4 B; cave `0xC4BD6–0xC4BD9`
  4 B, `0xC4BDC–0xC4BF7` 28 B, `0xC4C00–0xC4C09` 10 B, `0xC4C0B–0xC4C1F` 21 B, `0xC4C21–0xC4C8B` 107 B;
  trailer `0xC4FFC` 4 B; fb pole `0xC63E8` 1 B and `0xC63EA/EB` 2 B; trailer `0xC6FFC` 4 B), plus this
  build's 10. **So flashing A′ reverts V289's cave, its hook, its fb pole and its 0x14A telemetry bits, and
  adds 6 Kd bytes.** The three trailers `0xC4FFC`, `0xC6FFC`, `0xE5FFC` all differ from the car's image.
- **Telemetry consequence — 🛑 THIS BUILD DOES NOT YET CARRY THE INSTRUMENT FOR ITS OWN EDIT.** Reverting to
  the V282 cave restores V282's `0x14A` byte-4 bits (b3, b4/b6 = the r24 comparators, b5/b7 = V289's notch
  taps, which vanish). **Nothing on the wire would report the delivered `Kd`.** Per the standing instruction,
  A′ is **not ready to cut** until either (i) a bit is spent publishing `Kd(t) < 128` (or the demand index
  crossing knot 22), or (ii) it is accepted that `Kd` is fully reconstructible offline — which it **is**:
  `reqaxis`'s `demand()` mirror reproduces the firmware index frame-for-frame at 1.0000 agreement from
  `cmd` and `bar`, both already on the wire, so `Kd(t)` is computable to the byte with **no new cave**.
  **My reading: (ii) genuinely satisfies the instrument requirement for this edit — the state to watch is a
  pure function of two signals already logged — and it is what makes A′ a 6-byte, one-trailer, cave-free
  build.** That judgement is the orchestrator's to accept, not mine.
- 🛑 **I have not verified the V282 image's own CRC chain replays clean, nor run any build script.** No
  firmware was built. The byte addresses, the record decode, the block map and the image diff are all
  EVIDENCE (Python, little-endian, re-read from the images this session); everything about how a build script
  should apply them is for the build agent.

---

## 9. WHAT A "DO NOT FLASH" WOULD HAVE LOOKED LIKE — written before the runs

- A Kd cut **destabilising** any fit on any base (it would have shown as `unst > 0`, or `ζ_worst` going
  negative, or PM collapsing). **0 of 87 at every Kd from 64 to 128 on all three bases.** Did not occur.
- The scheduled Kd failing to protect the authority yardsticks — i.e. the capped-step and full-lock regimes
  turning out to live **below** idx 32. **They live at idx p50 74–123, 76–89 % of their time above idx 32.**
  Did not occur.
- `paramod`'s parametric hazard firing. **Did not occur** (his §0, independently).
- **One check DID come back FAIL-shaped and is reported as such, not smoothed:** the 7 Hz gate for option A
  is **1.010–1.017** on the effective-Kd reading, over the operator's 1.01. That is why the recommendation is
  **A′ (Y0 = 112)**, not A.

## 10. WHAT I DID NOT VERIFY

- The feedback-operand hook `0x28F4C` / cave `0xC4C90` (option C's landing site). I scored C's *dynamics*
  from `reconcile_v290`'s placement model; I did **not** re-derive the hook's reachability, RAM ownership or
  register liveness. That is `fbhook`'s and the trace's. **BELIEF that C is implementable.**
- The four 2026-09-08 plant fits and the 16.63 Hz plant point — used only via the shipped family JSON.
- Anything about how audible ζ 0.057 at 16.5 Hz is. **The operator scores symptoms; I score bands.**

---

*Agent `basepick`, 2026-09-09. Analysis only — nothing was built, flashed or sent.*

---
---

# ADDENDUM — RE-RANK AFTER `powerS` AND `paramod` (2026-09-09, later the same day)

Three findings arrived after §0–§10 were written and they change the ranking **logic**, not just numbers:
`powerS` — row S as a pure cal-only build is UNINTERPRETABLE, so **it needs a cave regardless**, and the
delivered dose weighted by grinding-episode SECONDS is **Kd 112.8 (×0.882)**, not the nominal 96 (×0.75).
`paramod` — the mitigation family is sized, the brief's "put the cut wholly below the band the rings visit"
CANNOT be built, and one rung is worth spending on the demand-axis premise.

**Script for everything below: `rlog-tools/studies/grind/basepick_delivered_dose.py` →
`_scratch/basepick_delivered_dose.txt` (+ `.json`). Every column is read at the DELIVERED Kd. Nothing in
this addendum is scored at a nominal `Y[0]`.**

## A1. 🛑 THE HEADLINE: THE Kd-SCHEDULE CLASS IS CAPPED — HARDER THAN ×0.88

EVIDENCE. Delivered Kd is the episode-seconds-weighted mean over the pooled r62+r63 grinding episodes
(25.5 s, 2553 samples; my per-route means 106.5 / 118.9 reproduce `powerS`'s exactly). `gate73` is the worst
of the three routes read at each route's **full-lock delivered Kd**; `pkR_m` likewise at the capped-step
delivered Kd. **Ring = time to 10 % at the delivered dose.**

| record | B | protection | delivered Kd | ×base | ζ_w | **ring ms (cyc)** | **gate73** | pkR_m |
|---|---|---|---|---|---|---|---|---|
| base V282 | 0 | — | 128.0 | 1.000 | +0.0129 | **545 (10.9)** | 1.0028 | 1.000 |
| **S′ Y=(112,112,112,128)** | 6 | byte-id | **120.4** | **0.941** | +0.0178 | **448 (8.9)** | **1.0100 ✅** | 0.995 |
| M2 Y=(96,104,116,128) | 6 | byte-id | 115.7 | 0.904 | +0.0198 | 395 (7.8) | 1.0116 ❌ | 0.994 |
| **M1 Y=(96,96,112,128)** | 6 | byte-id | 113.8 | 0.889 | +0.0206 | 375 (7.4) | 1.0139 ❌ | 0.992 |
| **S  Y=(96,96,96,128)** | 6 | byte-id | **112.8** | **0.882** | +0.0210 | **367 (7.3)** | **1.0171 ❌** | 0.990 |
| S80 Y=(80,80,80,128) | 6 | byte-id | 105.3 | 0.822 | +0.0245 | 313 (6.2) | 1.0243 ❌ | 0.985 |
| S64 Y=(64,64,64,128) | 6 | byte-id | 97.7 | 0.763 | +0.0282 | 266 (5.2) | 1.0315 ❌ | 0.980 |
| **S0 Y=(0,0,0,128)** — the class's ABSOLUTE ceiling | 6 | byte-id | 67.4 | 0.526 | +0.0290 | **257 (5.0)** | **1.0604 ❌** | 0.962 |
| X48 X=(0,11,22,48) | 8 | **SPENT** | 111.0 | 0.867 | +0.0218 | 351 (7.0) | 1.0216 ❌ | 0.987 |
| X64 | 8 | **SPENT** | 109.4 | 0.855 | +0.0225 | 338 (6.7) | 1.0255 ❌ | 0.984 |
| X96 | 8 | **SPENT** | 106.9 | 0.835 | +0.0237 | 321 (6.3) | 1.0316 ❌ | 0.979 |
| X240 | 8 | **SPENT** | 101.1 | 0.790 | +0.0265 | 286 (5.6) | 1.0485 ❌ | 0.961 |
| X64+deep Y=(64…) X=(…,64) | 8 | **SPENT** | 90.8 | 0.709 | +0.0290 | 257 (5.0) | 1.0484 ❌ | 0.969 |

**Three conclusions, each answering a question that was put to me:**

1. **Under the operator's own 7 Hz gate ≤ 1.01, exactly ONE schedule record qualifies — S′ (Y0 = 112), and
   it sits AT the limit (1.0100).** Its delivered effect is **ring 545 → 448 ms, ×1.22**. Row S itself is
   **1.0171 — a FAIL**, and so is every deeper variant. The earlier §3 recommendation of A′ survives as the
   only *legal* schedule, but its effect is now known to be a fifth of what the nominal reading implied.
2. **The class cannot be rescued by a bigger dose.** Setting `Y[0..2] = 0` — deleting the D term entirely
   below the knot, an absurd build — reaches only **ring 257 ms (×2.1)** and blows the gate to **1.0604**.
   **×2.1 is the class's ceiling at infinite dose.** The reason is exactly the one `powerS` and `paramod`
   identified: roughly half of grinding seconds sit above idx 32, where every Y-only record is
   byte-identical to base.
3. **Moving the knot X is DOMINATED — never worth it.** S80 (ring 313 ms at gate 1.0243) beats X64
   (338 ms at 1.0255) on **both** axes, with **2 fewer bytes** and in the **safer byte class**. Deepening Y
   weakly dominates extending X along the whole (effect, gate) frontier, because an X extension buys reach
   by spending precisely the full-lock protection it was chosen to preserve. **The X lever is closed.**

⇒ **Answering the question as put: the schedule class is capped at roughly ×0.88 delivered / ×1.22 ring
under the gate, and no (Y, X) combination reaches a worthwhile delivered dose while keeping the protection.
Therefore the feedback notch — which acts on every episode regardless of demand — is the better build, and
row S is not even a good companion (see A3).**

### M1 versus S on delivered dose, as asked

**M1 dominates S.** M1 delivers **113.8 vs S's 112.8** — it gives up **one Kd count** of delivered dose
(ring 375 vs 367 ms, a 2 % difference, far inside any fit uncertainty) and buys `paramod`'s 25–35 % cut in
parametric drive **plus a materially better gate (1.0139 vs 1.0171)**. The damping M1 trades away in the
11–22 band is real but small, because that band is only 11–16 % of engaged seconds and 8–16 % of grinding
seconds. **If a Y0 = 96 schedule is ever built, build M1, not S.** Both fail the gate, so the comparison is
academic unless the operator relaxes it; at the legal dose the analogous mitigation is
**Y = (112, 112, 120, 128)**.

## A2. OPTION D — THE TWO EDITS COMPOSE IN THE DYNAMICS AND COLLIDE IN THE BUDGET

**Dynamics: they compose, favourably and additively. No interference.** On the C base
(`basepick_delivered_dose.py`, lower block): C alone ζ_w +0.0349, ring 387 ms → +S′ ζ_w +0.0402, ring 353 ms
→ +S ζ_w +0.0453, ring 321 ms. **0 of 87 fits destabilise at any Kd from 64 to 128 on the C base** (§4).
Nothing about the notch makes the Kd cut dangerous or vice versa.

**But they collide twice, and each collision is fatal on its own:**

1. 🛑 **GATE BUDGET.** C alone already spends **1.0092** of the 1.01 allowance. Every schedule variant pushes
   it over: **S′ → 1.0164 · M2 → 1.0181 · M1 → 1.0204 · S → 1.0237.** Even Y0 = 120 lands ≈ 1.013.
   **No schedule composes with C under the operator's own gate.**
2. 🛑 **TELEMETRY PAYLOAD — asked directly, and the answer is NO.** `instr290`'s design
   (`DESIGN-V290-TELEMETRY-2026-09-09.md` §2) allocates 0x14A byte 4 as: **b0–2 stock Honda · b3 `|d2| > |d|` ·
   b5 `sign(n)` · b7 `|n| ≥ 16`** (the three notch rungs, whose Q14 coefficients `b0 = b2 = 15680`,
   `b1 = a1 = −31074`, `a2 = 14976` are **exactly** the 21.5 Hz Q1.5 integers I derive in §5 — the telemetry
   design is already built for option C) **· b4 and b6 held UNTOUCHED as V282's r24 cross-build control,
   explicitly marked "must not move".** We own five bits and all five are committed. D needs those three
   notch rungs **plus** `powerS`'s `|D| ≥ T` magnitude comparator **plus** `paramod`'s premise bit
   `Kd_selected > Y_floor` = **five rungs**, obtainable only by spending b4/b6 and destroying the one channel
   that lets us compare this build against V282 and V289. **There is no room.**

⇒ **Option D is not buildable as one interpretable image under the operator's constraints. Drop it.**

## A3. THE RE-RANK

**Counting the instrument cost honestly, as instructed. `powerS` killed "cal-only, no cave" as an advantage —
row S needs a cave for its own readability — so every surviving option carries a cave and 3 CRC trailers.**

| rank | option | gate73 | pkR_med / worst | delivered ring | ζ_w | 16 Hz pole | cave & payload |
|---|---|---|---|---|---|---|---|
| **1** | **C** — V282 + fb-operand notch 21.5 Q1.5 (hook `0x28F4C`, cave `0xC4C90`) + fb 40 Hz | **1.0092 ✅** | 0.971 ✅ / **0.928 ❌** | **545 → 387 ms (×1.41)** | **+0.0349 (×2.7)** | **CREATES**, ζ_med 0.057, frac 1.00 | cave inherent; payload **fits exactly** (b3/b5/b7), b4/b6 preserved |
| **2** | **S′** — V282 + Kd (112,112,112,128) + a cave for `\|D\| ≥ T` + premise bit | **1.0100 ✅** (at the limit) | **0.995 ✅ / ≈0.99 ✅** | **545 → 448 ms (×1.22)** | +0.0178 | **none** | cave now REQUIRED; 3 free rungs, fits |
| ❌ | **D** = C + any schedule | 1.016–1.024 ❌ | 0.963 / 0.92 ❌ | 321–353 ms | +0.040–0.045 | created | **needs 5 rungs, has 3** |
| ❌ | S / M1 / M2 / S80 / S64 / all X variants | 1.012–1.060 ❌ | — | 257–395 ms | — | none | — |
| ❌ | **B / B′** on the V289 base | 1.012–1.020 | **0.806 ❌** at every Kd | — | — | kept, ζ 0.046–0.063 | — |

**The base answer is UNCHANGED and is now over-determined: V290 sits on V282.** Both surviving options are
fresh images from the V282 plain image; the V289 base is carried forward by neither.

### 🛑 THE DECISION THAT MUST GO TO THE OPERATOR, STATED PLAINLY

**No build with a worthwhile effect passes every constraint as written.** The constraint set admits only
S′, and S′'s effect is ×1.22. So one constraint has to give, and it is his call which:

- **Relax pkR on the WORST fit (0.928 vs the 0.95 floor; the median is 0.971) → build C.** A ~7 % transient
  peak-rate loss on the least favourable plant fit, in exchange for ×2.7 damping on the 20 Hz object, acting
  on **every** episode rather than half of them.
- **Keep every constraint → build S′,** and accept that it is a ×1.22 ring improvement.

### 🛑 AND A REASON S′ IS NOT READY TO CUT EVEN THOUGH IT IS LEGAL

Two independent findings now say the same thing, and they compound:

1. **`powerS`:** the within-drive stratified contrast is unpowered — the confound correction's CI
   (×0.34–2.01) is **2.6× wider than the ×2.29 effect** it was meant to resolve, and the two operator-facing
   channels are confounded **in the flattering direction** (low-demand rings are 41 % quieter and half as
   long on the base builds), so a naive "the low-demand grinding got better" report would be reporting the
   confound.
2. **This addendum:** the effect S′ can legally deliver is **×1.22 on ring time**, not the ×2.1 the nominal
   dose implied.

⇒ **A ×1.22 change, read through a contrast whose own error bar is 2.6× the effect, cannot be resolved by one
short symptomatic drive.** `powerS`'s `|D| ≥ T` rung would confirm the edit is LIVE and its DOSE — worth
having — but liveness is not efficacy. **Under the skill's own law, S′ is a build that cannot observe its own
edit's effect, and I do not recommend spending a drive on it.** That closes the schedule class for now, as
lever *and* as companion.

### Pre-registered revert signature for C — write it down before the drive

**C re-creates the 16 Hz object**: a pole at **16.5 Hz, ζ_med +0.057, in 100 % of the surviving fits**, 1.7×
better damped than V289's 16.66 Hz ζ 0.033 but **inside the burst range (ζ_eff 0.02–0.13) the operator has
already rejected**. Watch for: a 15–18 Hz line in trains; grinding that is lower-pitched than V282's;
a new 10–14 Hz line (C's sensitivity peak there is **2.0× V282's**); and audible HF hiss from the motor
(**rms |R| 30–500 Hz is ×1.91**). 🛑 **If C's 16.5 Hz pole is audible, the entire loop-shaping class is
closed — both notch placements, both bases, and the Kd schedule as well — and V291 must come from outside
it.** That is the most valuable thing C can tell us, and it is why C is worth the drive and S′ is not.

## A4. THE METHODOLOGICAL FINDING, CARRIED INTO THE RISK SECTION AS INSTRUCTED

🛑 **A Floquet analysis of the UNCLAMPED electronics is NOT a sufficient parametric-safety argument for this
loop.** `paramod` measured the linear excess at full swing at **+3.8e-4/tick (~2 %)**, while the **same**
modulation in the byte-exact **CLAMPED integer mirror cut ring decay to 0.42×** — off by an order of
magnitude **in the unsafe direction**. **Any future scheduled-gain or time-varying-gain build in this kit
must be checked in the clamped integer mirror, not only in the linear/Floquet model.** This generalises well
beyond row S and belongs in the standing doctrine, not in a single build's memo.

Two related notes for the record: the parametric exposure is **not** hypothetical — 52–70 % of grinding
episodes cross the idx 32 knot during their body, at a median 0.7–2.0 crossings/s (max 16/s) — and
`paramod`'s verdict that row S is nonetheless safe on depth and rate is accepted here. And the hazard itself
needs **zero cave bits**: the demand index is free on the wire at 100 Hz and frame-locked, so a probe adds
nothing. `paramod`'s premise bit `Kd_selected > Y_floor` is a **different** and genuinely valuable rung — it
would confirm the demand-axis premise on-car for the first time, and **if it read otherwise, row S is simply
wrong** — but it is only needed by a build that carries the schedule, and no such build is now recommended.

## A5. FOR THE CLOSE-OUT ARTIFACT

**Any before/after surface must be drawn at the DELIVERED dose, not the nominal Y[0].** The nominal reading
overstates row S's ring improvement by ~1.5× (257 ms vs the true 367 ms at Y0 = 96; 360 ms vs 448 ms at
Y0 = 112) **and** overstates its 7 Hz gate cost by ~4× (1.073 vs the true 1.017). Both errors are large,
they point in opposite directions, and the LERP plot must show the delivered `Kd(idx)` curve with the
measured grinding-episode idx histogram underneath it — otherwise the page shows a 25 % cut where the car
sees 12 %.

*Addendum by agent `basepick`, 2026-09-09. Analysis only — nothing was built, flashed or sent.*
