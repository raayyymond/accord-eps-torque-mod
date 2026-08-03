# HANDOFF 2026-08-03 — the detector was always there

**★★★★ THE RESULT: the ">50 Hz blindness" that has bounded every vibration conclusion in this kit for
five sessions is an INSTRUMENT limitation, never a physical one. Honda has been running a 1 kHz
oscillation detector the whole time, and its input is a band-pass peaking at ~61 Hz. We were the only
ones who could not see up there.**

Alongside that: route `4a` **closed** the last open arm of the V67 result, and the operator's highway
symptom resolved into a **well-powered null** that refuted a hypothesis I pre-registered before looking.

Read alongside `docs/STATE.md`, `docs/BUILD-LINEAGE.md`, `docs/V66-V67-DESIGN.md` and the predecessor
`HANDOFF-2026-08-02-v67-flew-and-the-highway-grind-is-not-the-rate-lane.md`.

---

## 1. ★★★★ THE HEADLINE — `gp-0x6c2c` IS A BAND-PASS PEAKING AT ~61 Hz

Every highway null this kit has published carries the same caveat: CAN is **100.000 Hz exactly**
(Nyquist **50.00**) and the comma IMU lattice **101.026 Hz** (Nyquist **50.51**), so *"we see nothing
above 50 Hz"* has always meant **silence, not absence**. The microphone was the only channel without
the ceiling, and §6 explains why it bears less weight than it looks.

**`FUN_000428d4` — Honda's own oscillation detector, running at 1 kHz — has no such ceiling.** Its
input `gp-0x6c2c` is not a low-pass on motor rate; simulated through the decompiled arithmetic it is a
**band-pass**, and its peak sits almost exactly where our instruments go deaf. Gain relative to the
21.09 Hz grind #1 mode:

| f | 1 Hz | 21.09 Hz | 45 Hz | **61 Hz** | 100 Hz | 150 Hz | 200 Hz |
|---|---|---|---|---|---|---|---|
| relative gain | **0.05×** | 1.00× (ref) | 1.54× | **1.61× (max)** | 1.43× | 1.15× | 0.94× |

It stays above **90 %** of the 21 Hz gain out to ~**180 Hz**. Trip amplitude required on `gp-0x4f50`:

| f | 21.3 Hz | 45 Hz | 60 Hz | 80 Hz | 100 Hz | 150 Hz | 200 Hz |
|---|---|---|---|---|---|---|---|
| counts to trip | 1683 | **1104** | **1056** | 1092 | **1186** | 1478 | 1735 |

★★ **The 45–100 Hz band needs LESS amplitude than 21 Hz already required**, and **none of it is
structurally untrippable** — `gp-0x4f50`'s own clamp is **±13000**, far above every figure in the row.
Sanity-checked against the golden model's recorded pair: **1683 → 12804 trips; 1682 → 12797 does not.**
✅ **I re-simulated the whole table independently and got the same numbers.**

🛑 **Units caveat, and it is the exact shape of a mistake this kit already made.** `gp-0x4f50`'s
conversion to deg/s is **[OPEN]**. Do **not** borrow `gp-0x6ac0`'s 4.7121 counts/deg-s to close it —
composing those two scale chains is what produced the retracted *"bus = 8 × deg/s"*. The amplitudes
above are in **counts on `gp-0x4f50`**, and that is all they are.

⇒ **V67 was already reading this detector and got 0.000 % — but at threshold `gp-0x671a >= 5`.** The
revised **V68 reads it at `>= 1`** and adds a strictly-lower rung. That converts a null that could
mean *"nothing up there"* or *"the gate never armed"* — the exact ambiguity V64 cost us a session to
learn — into a measurement.

---

## 2. ★★★ ROUTE `4a` CLOSED THE OPEN GAP — no further drive needed

`STATE.md` carried the V67 creep result with one arm unresolved: *"needs a parking lot, not a build."*
**It is satisfied.**

Build confirmed from the probe first, per the V64 lesson: byte4 ∈ **{0x87, 0xC7}**, bit3 = **0/35,994**
⇒ V67, and V68 excluded absolutely (V68 sets bit3 on every frame).

★★ **Engaged-creep grind #2 is RESOLVED.** **0 bursts in 158.7 s** of pooled engaged exposure against
an expected **7.62** at the Kd=2 rate ⇒ **P(0) = 0.0005**. The manual arm reads **0.0015** and the
corner-conditioned cut **0.0001**. Route 47's engaged arm was 22 s at P(0) = 0.35; this is a different
class of evidence.

★★ **Grind #1 still fixed, and now stronger.** `r4a` alone **0.38 [0.21, 0.55]**; V67 pooled
**0.40 [0.27, 0.58]** against a split-half null of **[0.88, 1.13]** — statistically on top of the Kd=2
pool (0.39). Arm-matched, replicating route 47's one-arm-only signature more strongly:

| arm | ratio vs Kd = 1.00× |
|---|---|
| **ENGAGED** (gate open) | **0.321 [0.218, 0.541]** |
| **DISENGAGED** (gate closed) | **1.151 [0.698, 1.521]** |

✅ **FLIGHT-CLEAN both ways**: `ST == 4` **0/35,994**.

⚠ Route `4a` has **zero highway seconds** (max 13.92 m/s), so it adds nothing to §3's population. Its
caches carry a `probe` field the older caches lack.

---

## 3. ★★★ THE HIGHWAY RESULT — a well-powered null, and my own pre-registered hypothesis refuted

🛑 **I pre-registered H1 before the analysis ran, and it failed.** H1: *"the highway resonance is
grind #2's mechanism at a higher mode"* — `gp-0x4f62` is a 4-sample finite difference so its gain rises
with frequency (1.93× at 41.6 Hz vs 20.9 Hz); V62's flat ×2 cut grind #1 by 2.9× and raised grind #2 by
11.7×; V67 delivers its **maximum** 2.44× dose at highway. The sharp prediction was **P2: event RATE
should rise with dose, 1.00 < 2.00 < 2.44.** Recording the failure in full is the point of this section.

### The veto ran first, and it vetoed everything

**There is no spectral line anywhere in 30–49.5 Hz at highway, on any channel, on any build.** Peak of
the **averaged** periodogram, per route × speed bin — prominence against its own local floor:

| channel | 30–49.5 Hz | 8–30 Hz (positive control) |
|---|---|---|
| torsion bar `0x18F` | **1.32 – 3.83** | **8.4 – 78.8** |
| comma IMU `ay` | **1.23 – 2.13** | 2.0 – 8.5 |
| comma IMU `gz` | **1.26 – 1.76** | 1.5 – 7.6 |

The kit's criterion for a real line is **> 4**. ✅ The control recovers wheel order 1 to within 0.5 Hz
in every speed bin (10.94 / 12.61 / 13.66 / 15.40 Hz vs predictions 11.30 / 12.74 / 14.18 / 15.87),
free-order fit **1.07**, Theil-Sen slope **+0.4836 [+0.4806, +0.4863]** vs order 1's 0.4808. **The
instrument would see a line. There isn't one.**

### P2, with the power stated

Detector: contiguous excursions above **10× the Kd=1 median envelope in the same speed band** —
threshold from this population, nothing imported from creep's 500 counts. 10 s blocks, split-half null
with the identical estimator.

| band, v ≥ 12 m/s | Kd 2/1 | Kd 2.44/1 | split-half null | min detectable @ 80 % |
|---|---|---|---|---|
| **18–22** (positive control) | **0.565 [0.329, 0.984]** | **0.319 [0.130, 0.661]** | [0.50, 2.30] | 1.51× |
| 30–40 | 1.296 [0.666, 3.686] | 1.489 [0.627, 4.476] | [0.16, 7.70] | 1.75× |
| **40–49** | 0.855 [0.432, 1.702] | **1.152 [0.496, 2.690]** | [0.36, 2.50] | **1.61×** |

**Monotone rising in no band and no speed cut**; at 40–49 Hz above 22 m/s the maximum-dose build has the
*lowest* rate (286.3 / 398.4 / **218.1** events per hour). ✅ Grind #1's own event rate falls
monotonically with dose and clears its null, matching the published level result (0.509 [0.39, 0.92]).

★★ **Two independent statistics — pooled level and event rate — reach the same null.** The earlier null
was **not** a statistic-choice artefact, which was the substantive objection against it.

**P3** untestable (no covariate cell holds ≥3 events on both arms). **P4** fails — no line to locate.
**P5** fails: command→bar coherence at 40–49 Hz is **0.169** in event windows vs **0.166** background,
against grind #1's **0.917 at 21.09 Hz**. **P1** untestable by construction, see §4.

### What the events actually are

The top tail of the smooth maneuver-loading effect already on record. P(window inside an event) by
decile of steering-rate peak, 40–49 Hz, n = 1820: `0.7 · 0.9 · 1.1 · 1.9 · 1.7 · 6.4 · 6.9 · 10.5 ·
22.1 · 61.2 %` — rising through **every** decile from the 5th, **no step**. Envelope-vs-`rate_pk`
ρ **+0.654 / +0.705 / +0.721**, inside the recorded +0.64…+0.93. Trigger is a **~1.5 s steering-rate
transient** (median |rate| 1.0 → 5.0 → 6.5 → **18.0** → 5.0 deg/s at lags −3.0 → 0.0 s, controls flat at
1.0). ✅ **Hands-off confirmed 19/20**; **rail duty 0.00 on every event**; duration 0.22–0.87 s.

⚠ A 2-component mixture "prefers bimodal" (ΔBIC 174) — **do not read it**: the high component is 42 % of
windows at 2.4×, a heavy body, not a rare class.

---

## 4. WHAT THE OPERATOR TOLD US, AND WHY IT REFRAMED THE SESSION

The previous session's analysis did not have these five facts, and four of them are directly testable:

| operator | data |
|---|---|
| **the pitch stays about the same** as speed changes | ✅ **confirmed as a negative** — it is not an order; but see the caveat below |
| **hands OFF for sure** | ✅ **confirmed** — effort p50 **92 counts** (criterion ≤ 200), `steeringPressed` p50 **0.00**, 19/20 events satisfy both |
| **threshold-like** — it happens or it does not | 🛑 **contradicted** — no step in any conditioning variable; smooth through every decile |
| **feels it, does not hear it** | ⇒ the microphone bears little weight here (§6) |
| **has never driven LKAS-off at highway** | 🛑 **and neither has the corpus** — see below |

🛑 **The corpus contains 1,177.4 s of engaged driving above 25 m/s and 0.0 s disengaged**, verified two
ways (`carControl.latActive` **and** the firmware's own `0x18F` byte4 bit3). ★ **The 0.0 s holds at
EVERY threshold** — engaged / disengaged seconds are 2403.9 / **0.0** at v ≥ 12, 2006.0 / **0.0** at
v ≥ 15, 1438.3 / **0.0** at v ≥ 20, 1177.4 / **0.0** at v ≥ 25, 781.2 / **0.0** at v ≥ 28. ⚠ Always
quote this figure **with its speed threshold**: a bare "1,184.8 s of highway" was in circulation and
reconciles with no threshold. **P1 is untestable by construction, not weakly testable.** ⚠ `cruiseState.enabled` would have manufactured a fake 123–187 s
LKAS-off arm per route — it is the wrong signal, as the kit already records.

🛑 **Fixed pitch rules out an ORDER; it does not rule out >50 Hz.** Aliasing preserves apparent-frequency
stability, so a stable pitch is equally consistent with a true sub-50 Hz mode and an aliased higher one.
Given §1, the higher one is now the live possibility.

---

## 5. 🛑 CORRECTIONS AND RETRACTIONS

**(a) "At highway, 40–49 Hz is wheel order 3" — RETIRED.** The recorded per-window order p50 of
**2.994** is an **arithmetic tautology**: `order = f0·CIRC/v` returns ≈3.00 whenever a band-limited
argmax sits near the centre of 30–49.5 Hz at the corpus's median ~28 m/s, **whatever the spectrum
contains**. Only a slope or a binned table tests it, and both refute order 3 — there is no line at all.
⚠ **The 10–16 Hz order-1 half STANDS** (prominence up to 79, order 1.00–1.02 per bin), and so does the
general warning about mistaking a wheel order for a firmware effect — it is now better founded.

**(b) My own "fixed ~42 Hz mode" — WITHDRAWN, and it was seductive.** A *median-of-per-window-argmax*
estimator reported ~42 Hz in every speed bin on four independent IMU axes across 22→35 m/s and beat
"wheel order 3" by **ΔBIC 249–460**. It matched the operator's fixed-pitch description exactly.
**It was an artefact**: with no line present the argmax scatters and its median lands at band centre
(39.75 Hz for a 30–49.5 band). **The fix that exposed it: average the periodograms FIRST, then find the
peak.** The mode vanished. Before withdrawing it I also killed the best physical alternative — the
Accord's **CVT** holds rpm near-constant at cruise, so an engine order would also sit still; extracted
`ENGINE_RPM` (`0x17C` bytes 2:3 BE, src 1) over 33 highway segments, rpm 1330–2400, `corr(rpm, v)` only
**+0.270**; an aliased engine order 2 requires slope **−0.0333 Hz/rpm**, measured **−0.00071 [−0.00251,
+0.00084]**. **Refuted.**

**(c) `gp-0x6a5e` is voted VEHICLE SPEED**, relabelled in `eps_lkas_chain_model.py` and at
`STATE.md:892`. The downstream *"the timer reloads constantly so the latch is permanently sticky"*
conclusion is **superseded**: the real release is **held below 10 km/h and clears 5.0 s after the last
reversal above it** (`0xC62DE` = 640 = 10.0 km/h, `0xC6270` = 5000; both byte-read, `bh` direction
verified).

**(d) `soundPressure` analyses 0–8000 Hz**, not the recorded "16–48 kHz".

**(e) `diff_build_vs_stock.py` was emitting false positives** that made a genuine stray edit
indistinguishable from noise. Fixed, with a `--self-test` that proves it can still fail.

**(f) The retracted "bus = 8 × deg/s" struck from `build_v68_tva.py`.**

⚠ Minor, recurring: `argsort(argsort(x))` is **not** a tie-aware rank transform. On a binary indicator
it produced a Spearman of **+0.393** against a covariate whose own decile table fell monotonically.

---

## 6. THE MICROPHONE AND THE IMU — both closed

**The microphone bears very little weight on a TACTILE event.** Its validation was at **creep**, where
the acoustic floor is **9.9× lower in power**, giving a **64× validation gap** against highway. And it
is one RMS over **0–8000 Hz** versus the driver's ear resolving ~1/3-octave critical bands — a **26.4 dB**
bandwidth penalty. A narrow tone the operator *feels* can move that number by essentially nothing.

**Raising the comma IMU's ODR was DECLINED, on structure.** It is not confined to the measurement path:
`locationd` → `livePose` → `controlsd.py:120-121` roll compensation, plus validity limits derived from
the declared service frequency. The fork already shows **84 `selfdrivedLagging` / 52 `commIssue` /
24 `locationdTemporaryError`**. ⇒ real regression risk for a measurement convenience — and **moot given
§1**, which reaches the same band from inside the ECU at 1 kHz.

---

## 7. ✅ V68 — REVISED, BUILT, UNFLASHED

Control path **byte-identical to V67**. Payload:

| bit | V68 |
|---|---|
| 7 | liveness |
| 6 | `gp-0x6806 != 0` — the LKAS gate |
| **5** | **`gp-0x67df != 0`** |
| **4** | **`gp-0x671a >= 1`** — the detector at its lowest rung |
| 3 | build fingerprint, always 1 |

★★ **bit4 at `>= 1` is the whole point.** V67 read this detector at `>= 5` and got 0.000 %, which cannot
distinguish *"no oscillation up there"* from *"the arm needs 5 reversals and got 4"*. bit3 keeps V68's
payload set **structurally disjoint** from V66/V67's, so a log identifies its own firmware without the
`.rwd` filename. **GATE 1 vacuous** (read-only). **GATE 2 un-engaged** (no control-path change).

Image SHA <!-- SHA-PENDING --> · RWD SHA <!-- SHA-PENDING -->

---

## 8. RECOMMENDED NEXT STEPS

1. **Flash the revised V68 and drive ONE highway run with LKAS OFF.** Two questions in one drive: the
   `>= 1` rung answers whether Honda's detector sees anything in its 45–100 Hz sweet spot, and the
   disengaged arm is **the only entirely missing arm in the corpus** — **1,177.4 s engaged above
   25 m/s and 0.0 s disengaged**, with the 0.0 s holding at every threshold from 12 to 28 m/s, verified
   two ways. Everything the operator says about "only when engaged" currently rests on nothing
   measurable.
2. **~4 min of engaged highway above 28 m/s on any non-V67 build.** **79.8 %** of all corpus exposure
   above 28 m/s is route `47` alone (623.8 s of 781.2 s; Kd=1 holds **39.2 s**), so above 28 m/s dose is
   confounded **1:1 with route**. The same drive closes §3's remaining power gap (v ≥ 28 needs 235 s per
   arm; v ≥ 22 at 40–49 Hz needs 308 s and Kd=1 has 214 s).
3. 🛑 **No control-path change is supported, and the reason is not "we found nothing."** It is that the
   rate lane was tested at three doses by two independent statistics with the power stated, both
   positive controls fired, and both said null. Changing r24 again would be aimed at a lever that has
   now been measured not to move this symptom. **Keep V67 on the car until V68 flies.**

---

## 9. OPEN RESIDUALS

- **`gp-0x61a0`'s writer and `gp-0x61e8`'s identity** — unresolved. ⚠ Does **not** affect any verdict
  here: `gp-0x67ac` is unreachable via the role table, which is a **calibration** fact, re-checkable in
  one byte read, not a structural one.
- **`gp-0x4f50`'s physical units — [OPEN]**, and deliberately left open (§1).
- 🛑 **Two live Kd=1 reference pools exist and they are not the same.** `r47_orchestrator_checks`
  includes `r2b`; `_grind2_lib.DOSE` does **not**. And **two envelope estimators disagree by 2.3×**
  (tapered `win_env` vs the untapered whole-record form). **Never cross-compare tables produced by
  different ones** — that is what put the superseded first-pass highway figures into
  `BUILD-LINEAGE.md`, corrected in this session.
- **Engaged-creep grind #2 is resolved (§2); the highway symptom is not explained.** The honest state is
  *"the bus cannot see it, and here is the bound"* — not *"there is nothing there."*

---

## 🛑 METHOD NOTES

1. **An estimator can manufacture a finding that matches the operator's own words.** The ~42 Hz mode had
   ΔBIC 249–460, four independent axes, and a perfect narrative fit. **Average before you peak-find**,
   and never test with a ratio built from a band-limited estimate divided by the variable under test.
2. **A pre-registered prediction that fails is worth more than a post-hoc one that succeeds.** H1's P2
   was written down before the numbers existed, so its failure is interpretable.
3. **A null without power is not a result.** Every null here carries its minimum detectable effect and
   the seconds needed to improve it — which turns an open question into a **drive**, not a build.
4. **Run the order veto first.** This kit has now come close to publishing a wheel order as a firmware
   effect three times.

---

# 10. ★★★ ADDENDUM — THE TRI-CHANNEL ANALYSIS: THE MICROPHONE PLACED GRIND #2 ABOVE 50 Hz

*Appended after the sections above were written and committed. The analysis did not exist when §1–§9
were drafted, and it changes what §1's "we were the only ones who could not see up there" is worth:
we could, and the instrument was already in the logs.*

## 10.1 What was asked, and what had never been done

The operator asked for the **IMU data in the rlogs analysed alongside the steering-column torque and
the audio**, on grind #2. Each channel had been used on grind #2 **separately** — the IMU dose
response, the microphone's 4.14× positive control, the CAN torque band — and **never jointly on the
same events**. Reproduce with `analysis-2020accord/grind2_trichannel.py`; every number below is
printed by that script and stored in `_grind2_trichannel.json`.

Event list: the kit's own 30–49 Hz burst detector restricted to creep (v ≤ 4 m/s) — **10 events**,
8 LKAS **ON** (`3a`/V65) and 2 LKAS **OFF** (`3b` seg 2/V65), f0 31.0–48.5 Hz. Re-derived
independently here: **12/12 (`3a`) and 22/23 (`3b`)** of the recorded bursts recovered. Every event
matched to controls in its **exact** (speed, effort, |rate|) cell — 18–304 control blocks, no
relaxation needed.

## 10.2 ★★★ THE RESULT — the two weightings are a TWO-POINT FILTER BANK

`soundPressure` and `soundPressureWeighted` are the same 100 ms RMS through two different filters.
A-weighting is **−32.41 dB at 44.6 Hz** but **−19.14 dB at 100 Hz**, so their **ratio reports where
the energy sits** even though neither channel alone can name a frequency. ✅ Validity checked first:
`soundPressureWeightedDb = 20·log10(spw / 2.0000e-05)` with sd **1.7e-12** ⇒ `spw` is a real
A-weighted RMS in Pa; and the ambient mean A-weight **rises with speed on every route**
(`3b` 2.5e-3→6.5e-3, `2b` 5.2e-3→1.2e-2, `47` 1.2e-2→1.7e-2 creep→highway), as wind noise must.

**The A-weighted channel rose MORE than the un-weighted one** — 6.514 vs 4.591 in amplitude:

| quantity | point | 95 % CI (event bootstrap) |
|---|---|---|
| excess mean A-weight / w(44.6 Hz) | **4.28** | **[2.28, 9.86]** |
| ⇒ **effective spectral centroid** | **63.5 Hz** | **[54.2, 79.6] Hz** |
| energy fraction above the band if f_h = 100 Hz | 16.2 % | [6.3, 43.8] |

⇒ **THE GRIND #2 ACOUSTIC EXCESS IS NOT ALL AT 40–49 Hz.** A pure 44.6 Hz excess gives 1.00× by
construction and is **excluded** (CI lower bound 2.28). **The whole centroid interval is above the
50 Hz ceiling.** This is the **first data-based evidence of >50 Hz content in this kit**, and it needs
**no acoustic transfer model** — both numbers come from the same microphone on the same 100 ms blocks.

★ **It corroborates V68 from a channel with no shared assumption.** 63.5 Hz sits essentially on
`gp-0x6c2c`'s band-pass peak (**61 Hz**, §1). The firmware arithmetic and the acoustics reached the
same band independently.

Robust to the burst statistic — we/w(44.6) = **5.64** (p90) / **3.07** (median) / **3.31** (max) — and
not one loud event: the mic fires on **8 of 10** bursts and tracks torsion-bar magnitude.

## 10.3 🛑 RETRACTION — my "95.5 Hz [66.8, 170.5]" was WRONG

I published an effective centroid of **95.5 Hz [66.8, 170.5]** in review. **It does not reproduce**:
`a_weight(95.5)/a_weight(44.6)` is **18.29×**, not the measured 4.28×, and that interval maps to
[5.20×, 97.2×]. The correct inversion is **63.5 Hz [54.2, 79.6]**.

**Root cause: I inverted 4.28× against the AMPLITUDE weight `w(f)` instead of the POWER weight
`w(f)²`.** Confirmed two ways, both reproducing 4.2769 exactly: the amplitude-weight ratio at 95.5 Hz
is **4.277**, i.e. precisely `√18.29`; and the same run's *"16.2 % at 100 Hz"* decomposition gives
`0.838·W(44.6) + 0.162·W(100) = 4.277·W(44.6)`.

🛑 **THE RULE: A-weighting is tabulated in dB on POWER. `w = 10**(A_db/20)` is an AMPLITUDE weight and
must be SQUARED before mixing energies.** Getting this backwards moves an inferred frequency by
**+32 Hz** — enough to have put the answer outside `gp-0x6c2c`'s peak instead of on it.

✅ The conclusion survived the correction and one part got **stronger**; but the margin above the
ceiling is **54.2 Hz, not 66.8**. ⚠ Two roundings of this bound were produced in review (54.1 vs
54.2) from A-curve implementations differing by ~0.02 Hz; **normalised to 54.2 everywhere** (exact
54.157 Hz). 🛑 **The first decimal is below the resolution of the bootstrap that produced the
interval — quote this bound as "~54 Hz" and do not treat the last digit as meaningful.**

## 10.4 ★★ GRIND #1 IS TORSIONAL; GRIND #2 IS CHASSIS-BORNE — two independent estimators

| channel | axis is | **grind #2** (40–49) | clears null | transfer | **grind #1** (18–22) | clears |
|---|---|---|---|---|---|---|
| `tq` 0x18F | torsion bar | **77.1** [53.5, 130.9] | ✅ | 1.000 | **12.87** [9.0, 14.9] | ✅ |
| IMU `ay` | **lateral** | **58.8** [29.8, 87.6] | ✅ | **0.763** | 1.451 | ✗ |
| IMU `gz` | **roll** | **36.2** [21.4, 49.3] | ✅ | 0.470 | 1.463 | ✗ |
| IMU `gy` / `ax` / `az` | pitch / vert / long | 21.3 / 20.1 / 19.2 | ✅ | 0.28 / 0.26 / 0.25 | 1.51 / 1.68 / 2.10 | ✗ |
| IMU `gx` | yaw | 11.4 [7.2, 14.3] | ✅ | 0.148 | 1.465 | ✗ |
| mic un-weighted | 0–8 kHz | **4.59** [2.95, 8.31] | ✅ | 0.060 | **1.061** | ✗ |

Axes identified **from the data**: `ax` carries 9.67 m/s² ⇒ vertical; `az` ρ **−0.839** vs d(vEgo)/dt
⇒ longitudinal; `gx` ρ **+0.975** vs v·steer ⇒ yaw; `gy`/`gz` split by |ρ| vs d(surge)/dt **0.690**
against d(sway)/dt **0.723** ⇒ pitch / roll.

**Second estimator — bar→chassis COHERENCE, which uses no level at all:** grind #2 reads
**0.823–0.880 on every axis** in event windows against **0.296–0.605** in controls; grind #1, over
**48 events**, shows **no contrast on any axis** (0.270–0.403 vs 0.258–0.465 control).

⇒ **grind #1 is a TORSIONAL COLUMN MODE**, and that is **why the IMU never showed its reduction** —
the instrument was never coupled to it, at any frequency, independently of the 50 Hz ceiling.

**BELIEF, not measurement:** the ordering lateral ≫ roll > pitch ≈ vertical ≈ longitudinal ≫ yaw reads
as a **lateral rack/subframe force with a roll couple** (the comma sits high on the windscreen). Not
wheel-hop, not a yaw mode.

## 10.5 🛑 THE MICROPHONE READ 1.061 ON GRIND #1 — INSIDE ITS NULL

On an oscillation measured at **12.87× [9.0, 14.9]** on the bar over 48 events, the microphone reads
**1.061 [1.004, 1.233]** against a null of [1.03, 1.24]. **The cleanest demonstration of its blind
spot in the corpus.**

⇒ **A mic POSITIVE is informative** — its creep grind #2 control **replicates at 4.59× [2.95, 8.31]**
against the 4.14× on record, by a different estimator *and* a different control design, and §10.2
extracts real spectral information from it. **A mic NEGATIVE on a TACTILE event carries almost
nothing.** Never read "the mic saw nothing" as "there was no vibration."

## 10.6 ⚠ THE LIMITS, STATED AT FULL STRENGTH

- **§10.2 is a MEAN-WEIGHT inversion.** It proves the excess is not all sub-50 Hz; it **does NOT
  locate the energy**. 16 % at 100 Hz, 1.4 % at 250 Hz and 0.27 % at 1 kHz are identical to this test.
  Harmonics at 89.2 / 133.8 / 178.4 Hz are **BELIEF**.
- **Tyre scrub is NOT eliminated.** The partial correlation survives control for |rate|, effort and
  speed (**+0.507 [+0.297, +0.634]**, n = 2956 creep blocks), but **rack force is uncontrolled**.
- **The highway energy budget CANNOT BEAR THE WEIGHT.** κ = **0.0091 [0.0059, 0.0159]** predicts an
  8.5–12.7 % acoustic excess against a measured mic floor of 19.3–109.9 % ⇒ **2–9× under the
  instrument**. A highway acoustic null is therefore **uninformative**, and the honest output is the
  **bound**: unexplained acoustic energy up to **2–9×** the sub-50 Hz-implied amount is invisible.
  Three assumptions, each failing in a known direction: radiation efficiency ~f² against a 9.9×
  louder ambient (partly cancelling, **neither measured**); a torsional highway mode would be
  invisible to the IMU even at creep; the floor is a steady-tone floor.
- **The joint detector is MIC-LIMITED** — the microphone is the minimum channel in **97 %** of burst
  blocks ⇒ **"joint" buys SPECIFICITY, not sensitivity.** Highway counts 1/0/1/4 with exact Poisson
  intervals that **all overlap**.
- ⚠ **The highway tri-channel coincidence is REAL but DOSE-INDEPENDENT** — chassis clears its
  circular-shift null on **4/4** routes (`ay` 1.347 / 1.866 / 1.372 / 1.437) and the mic on 2/4, but
  it is not monotone and the **stock Kd = 1.00 lane is not the lowest**. It is §3's manoeuvre-loading
  tail. 🛑 **IT DOES NOT REVIVE THE RATE LANE** — three independent statistics now agree.

## 10.7 TWO INSTRUMENT CONSTANTS NOBODY HAD PINNED DOWN

1. 🛑 **`1/median(dt)` is the WRONG CAN rate.** Frames are timestamped **per log packet**; on route
   `47`, **12 % of `dt` exceed 15 ms and p10 is exactly 0**, so `median(dt)` reads **100.76 Hz** on a
   grid that is **100.000 Hz to 2e-5**. Use the mean rate plus an index lattice. Recorded timestamps
   wander **7.5–10.3 ms** — that is the CAN alignment uncertainty.
2. ★ **The microphone pipeline delay is 115 ms**, MEASURED against road impacts (sound and chassis
   shock are simultaneous to ~3 ms): 35 road segments, peak ρ **0.512**. `micd.py` alone predicts
   **75 ms**; the extra **~40 ms is audio-capture buffering**. Subtract it from any sound↔CAN
   alignment.
3. 🛑 **No lead/lag is resolvable.** Accel and gyro carry **separate** hardware-timestamp offsets, and
   bar→IMU lags read +45/+80 ms on bursts but **+90/+40 ms on road excitation with no grind — same
   magnitudes, order swapped**. ⇒ **±50 ms is the empirical floor**, true transit is 0.2–3 ms
   (30–500× below the finest step), and all three channels rise **within one 100 ms block**. A
   lead/lag test **cannot** distinguish "column drives chassis which radiates" from "a common input
   excites all three" — **coherence** (§10.4) carries that discrimination instead.
