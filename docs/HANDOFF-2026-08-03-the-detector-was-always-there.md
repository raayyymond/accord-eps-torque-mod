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
