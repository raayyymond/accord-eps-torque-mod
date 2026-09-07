# ADVERSARY B — V287 (`0xC61B6` 10240 → 2560), UNIT/SCALE CHAIN and UNSAMPLED STRATA

Adversary B, 2026-09-06. Surface: unit chain re-derived from bytes/wire, and the strata the design
did not sample. Analysis only; nothing built, sent or flashed.

Script: `rlog-tools/studies/grind/adv_v287_b_units_strata.py` → `_scratch/adv_v287_b_units_strata.txt`.
Re-run it to reproduce every number here. Cells read fresh from the built V282 image; route statistics
from the r39 / r3a / r3c caches through `grind_incident_r35.simulate`, the byte-exact 1 kHz mirror.

## 0. WHAT A FAIL LOOKS LIKE — written BEFORE any number was computed

I return **FAIL** (do not flash as specified) if any of the following holds:

- **F1 (unit chain).** Re-deriving the chain from bytes/wire gives a physical rail for `|dE| = 160`
  that differs from the design's implied one by more than 1.5×, OR the design never states one (so the
  dose was chosen in raw counts with no physical meaning attached).
- **F2 (unsampled stratum).** There exists a stratum reachable in **normal driving** — highway lane
  change, hands-on correction, the 7.3 Hz loaded high-angle ring, road/bump input at speed — in which
  the **feedback part** of `dE` exceeds 160 on a materially larger fraction of ticks than the 0.6–0.7
  p99-ratio the design quotes for creep, i.e. where 2560 acts as a **Kd cut** rather than an excitation
  limiter. The record says Kd cuts re-arm the 7.3 Hz ring and move the sensitivity peak down, so such a
  stratum is a safety-relevant regression the pre-registration does not cover.
- **F3 (circular authority claim).** The "max-rate unchanged" result is an artefact of the mirror being
  driven by *measured* rate (so the plant cannot respond), and a proper open-loop-torque × plant-DC-gain
  estimate shows a delivered-rate loss greater than 5 % in creep or high-angle.
- **F4 (uncomputable / swallowed endpoints).** Any prereg FAIL statistic (Q1, Q5, Q6, Q7, Q8) cannot
  actually be computed from one short drive with the instruments on the wire, or has a route-to-route
  spread that swallows its own threshold.

**PASS** requires all four clean.

---

# VERDICT: **FAIL** at the specified dose of 2560. F2 and F4 both trip. F1 and F3 are clean.

**The crux in one sentence.** The design proved the clamp is an excitation limiter **in the hands-off
strata**, and that is TRUE at every speed from creep to highway. But in **loaded high-angle cornering,
hands-on corrections and fast wheel motion** — three ordinary-driving strata it never computed, together
**20–28 % of engaged time against creep's 4.4–6.7 %** — 2560 becomes a **local Kd cut of 38–40 % in the
18–22 Hz band**, and the design's OWN Appendix A4 says a Kd cut of that size **raises `|S|@20` and drags
the sensitivity peak from 26.3 Hz down toward 20.7 Hz, i.e. INTO the grind band**. The pre-registration
has no statistic in any of those strata, so the drive cannot see it happen.

## 1. F1 — UNIT CHAIN: **CLEAN**, and here are the physical numbers the design never wrote down

Re-derived from the image bytes, nothing inherited [EVIDENCE].

| step | from bytes | value |
|---|---|---|
| fb filter | `s' = floor((923·s + 1560·x)/1024)`, `fb = s + s'` | DC gain **30.8911** (record's 30.89 confirmed) |
| rate scale | 0x18F b2-3, `CPD` = 8 raw counts per deg/s | fb = **247.13 counts per deg/s** at DC |
| Kd | bank `0xCB7D4` = 128 flat | `D = dE·Kd>>3` = **16·dE** |
| rail | 2560 / 16 | **\|dE\| = 160** (today 10240 → 640) |

**What rails the FEEDBACK part alone**, two ways, both exact from that filter:

| form | \|dE\| = 160 (V287) | \|dE\| = 640 (today) |
|---|---|---|
| sustained wheel-rate acceleration | **647 deg/s²** | 2590 deg/s² |
| sinusoid at 7.3 Hz (the ring) | **15.4 deg/s** amplitude | 61.7 deg/s |
| sinusoid at 20.3 Hz (the grind) | **8.06 deg/s** amplitude | 32.2 deg/s |

**What rails the SETPOINT part**: `dE_sp = 32·d(sp)`, so `|dE| = 160` at `|d(sp)| = 5` map counts. On the
V282 linear-to-6× map the slope is 4.25–4.38 sp counts per demand-index count, so **one demand count of
command change per 10 ms frame gives `dE_sp` = 136–140** — 85–88 % of the 2560 rail. **At 2560 a
two-count command step rails the D clamp.** At 10240 it takes about 4.7 counts. That is the correct
physical statement of the dose and it is not in the design.

⚠ **One structural caveat on the whole mirror [BELIEF, unmeasurable from CAN].** The transfer from wheel
rate to `|d(fb)|` per tick is **essentially FLAT from 30 Hz to 200 Hz** (2.80 / 3.01 / 3.01 / 2.59 at
30 / 50 / 100 / 200 Hz, versus 2.48 at 20.3 Hz). The mirror reconstructs the rate from a **100 Hz** wire
by band-limited interpolation (`creep20_loop_id.up1k`, a `resample_poly` FIR), so it sees nothing above
50 Hz — while the ECU differentiates its own 1 kHz sample. Any real rate content at 50–250 Hz enters
`d(fb)` with **the same or greater weight** than the 20 Hz grind and is invisible to every number in
Appendix B. So B2's feedback shares are **lower bounds**, not estimates. I cannot size the residual from
CAN; it needs a probe.

## 2. F2 — UNSAMPLED STRATA: **FAIL**, and this is the decision-bearing finding

First, the check that says my machinery is not the problem. Recomputing the design's OWN window
selection with my own code reproduces Appendix B to the third digit:

| | design B2 (2560) | mine |
|---|---|---|
| creep windows, bind % | 2.11–4.38 | **2.10–4.43** |
| creep windows, D_sp-dominated % | 97.8–100.0 | **96.3–100.0** |
| creep windows, p99\|D_fb\|/clamp | 0.600–0.705 | **0.601–0.727** |
| r35 incident, bind / dom / ratio | 17.62 / 39.5 / 3.181 | **17.46 / 39.8 / 3.181** |

Now the census over whole strata, undilated, contiguous runs ≥ 1 s, at 2560. `dom %` is the share of
**binding** ticks that are setpoint-dominated; the design's own admissibility test is high `dom` and
`p99|D_fb|/clamp < 1`.

| stratum | % of engaged time (r39/r3a/r3c) | bind % | **dom %** | **p99\|D_fb\|/clamp** |
|---|---|---|---|---|
| CREEP hands-off *(the design's stratum)* | 6.7 / 4.4 / 5.2 | 0.9–2.2 | **100 / 100 / 100** | 0.38–0.59 |
| LOW-MID hands-off 3–8 m/s | 19.1 / 8.2 / 10.0 | 0.6–2.0 | 89–98 | 0.49–0.63 |
| SUBURBAN hands-off 8–15 m/s | 33.0 / 20.5 / 18.5 | 0.7–1.3 | 89–98 | 0.53–0.59 |
| HIGHWAY hands-off >15 m/s | 24.0 / 56.5 / 50.8 | 0.6–1.8 | 94–98 | 0.48–0.58 |
| **HANDS-ON \|bar\|>700** | **10.2 / 5.3 / 9.2** | **7.9–12.9** | **38 / 40 / 53** | **1.56 / 1.56 / 1.99** |
| **HANDS-ON HARD \|bar\|>1500** | 7.5 / 3.3 / 6.4 | 8.7–12.5 | **39 / 44 / 53** | **1.53–1.85** |
| **LOADED HIGH-ANGLE \|ang\|>60 deg** | **8.1 / 5.3 / 8.4** | **16.9–18.4** | **26 / 35 / 36** | **2.16 / 2.16 / 2.59** |
| **FAST WHEEL >25 deg/s (lane-change class)** | **10.5 / 5.8 / 9.3** | **11.5–14.4** | **43 / 49 / 57** | **1.45–1.73** |

**The design's hands-off claim is correct and I strengthened it** — it holds not just in creep but at
every speed up to highway. **Its generalisation to the car is false.** In loaded high-angle cornering only
**26–36 %** of binding ticks are setpoint-dominated and the feedback part's p99 is **2.2–2.6× the clamp**.
That is the design's own definition of a local Kd cut, and it happens in ordinary cornering, not in a
burst. B0 item 6 concedes this "inside an r35-class burst" only; B6's risk paragraph then asserts `|S|`,
Ms, gain margin, the 7.3 Hz ring and the reversal detector are "exactly as-built **by construction**,
because the clamp never binds on the feedback part in steady creep." The premise is about creep; the
conclusion is about the ring, which the record places in the **loaded high-angle** stratum.

### How large a Kd cut, in band

Measured as the in-band gain of the clamped D against the unclamped D on the mirror:

| stratum | eff. Kd × at 6–9 Hz (ring) | eff. Kd × at 18–22 Hz (grind) |
|---|---|---|
| creep / low-mid / suburban / highway, hands-off | 0.70–0.99 | **0.90–0.99** |
| HANDS-ON HARD \|bar\|>1500 (r39) | 0.66 | **0.587** |
| **LOADED HIGH-ANGLE \|ang\|>60** | **0.62 / 0.70 / 0.75** | **0.597 / 0.623 / 0.600** |
| FAST WHEEL >25 deg/s | 0.94–1.02 | 0.78–0.79 |

**An effective Kd of 0.60 is Kd 128 → about 77**, inside the range Appendix A4 already swept. A4's rows:

- Kd 128 → 96: `Ms` 2.38 @ **26.3 Hz** → 1.93 @ **24.2 Hz**, `|S|@20` 1.61 → 1.71.
- Kd 128 → 64: `Ms` 1.69 @ **20.7 Hz**, i.e. the sensitivity peak lands **in the grind band**.

A4 states it plainly: *"Cutting Kd raises `|S|@20` and drags the sensitivity peak down from 26.3 Hz into
20.7 Hz — i.e. it moves the peak into the grind band instead of out of it."* So by the design's own grid,
V287 at 2560 is predicted to make the loop **more** sensitive at 20 Hz in the high-angle stratum, and to
cut the 6–9 Hz phase lead by 25–38 % in exactly the stratum the record assigns to the 7.3 Hz strong-turn
ring. **Appendix B's risk statement and Appendix A4's grid contradict each other, and no Q statistic is
computed in the stratum where they disagree.**

## 3. F3 — THE "MAX-RATE UNCHANGED" CLAIM: **CLEAN**. I attacked it properly and it survived.

The circularity objection is real: the mirror is driven by *measured* rate, so it cannot show the plant
responding more slowly, and B4's result is therefore an **open-loop torque** statement, not a
delivered-rate one. B4's method is also underpowered — it compared **pooled medians of different steps**
per clamp (n = 24 each), which is why its own numbers are non-monotone at ±3 %.

I ran the powered version: **PAIRED**, the same step simulated at both clamps, on 130–199 measured
hands-light full-demand steps per route.

| route | n | paired median T ratio 0–50 ms | 0–100 ms | 0–200 ms | peak | 95 % CI on 0–100 ms |
|---|---|---|---|---|---|---|
| r39 | 199 | 0.988 | 0.992 | 1.003 | 0.969 | [0.979, 1.017] |
| r3a | 157 | 1.009 | 1.008 | 1.002 | 0.990 | [0.987, 1.021] |
| r3c | 130 | 1.011 | 1.002 | 1.002 | 0.986 | [0.981, 1.019] |

Every interval straddles 1.0; about half the steps move each way. Since the **open-loop** torque change is
statistically zero, the closed-loop delivered-rate change is zero to first order regardless of the plant
DC gain (measured at 2.1–2.4 deg/s per 100 T in creep, 4.8–6.5 at high angle, 10.0–12.8 at fast wheel).
Only the **peak** over 200 ms falls, by 1.0–3.1 %. **B4's conclusion stands. The authority axis is not
where this build fails.**

## 4. F4 — PREREG FAIL CRITERIA: **FAIL**. Two of the five are mis-specified.

- 🛑 **Q5 (ring) is a coin flip.** Today 0.980, CI [0.971, 0.983]. The FAIL threshold is *"rises above
  0.980"* — the threshold **is** the point estimate and sits **inside its own confidence interval**. A
  perfectly null build trips this FAIL about half the time.
- 🛑 **Q6 (shelf) has more noise than threshold.** Threshold is ×1.30. Measured spread of the statistic
  itself in the creep stratum: **route-to-route ×1.52**, and **within-route, window-to-window ×1.79 to
  ×2.61** (n = 2–3 windows per route). The FAIL criterion is swallowed by its own estimator.
- **Q2/Q3, the primary endpoint and its negative control, may not read out at all.** Both are defined on
  operator-bookmarked **episode** windows. r39's 952 s contained two; r3a and r3c contributed none the
  design used. A drive without an episode returns no primary endpoint.
- **Exposure.** Strict creep runs ≥ 2 s total **11.7 / 5.0 / 9.9 s per route**. The build is always on
  across 480–880 s of engaged driving. The stratum the design optimised in is about 1 % of the drive.
- ✅ **Q1 (liveness) is sound and is the one statistic with real power** [EVIDENCE]. One clipped tick
  removes up to 7680 counts of D; through fade, the sum clamp, the 992/507 lag and the 5346 gain that is
  a T impulse of **38 counts peak decaying with τ ≈ 31 ms**, i.e. **4.8 LSB** of the 8-count 427 tap, at
  **22 binding ticks/s in creep and 100–173/s in the hands-on and high-angle strata**. Q1 will fire.
- **Q8 (authority)** is fine as a criterion; my §3 is the stronger version of it and it passes.

## 5. What would make me return PASS

Both are cheap and neither touches the hypothesis.

1. ⭐ **Take the dose to 7680, or add the missing strata to the pre-registration and accept 2560 as a
   deliberate Kd cut outside creep.** The design's own admissibility test (`dom` high,
   `p99|D_fb|/clamp < 1`) holds at **7680 in every stratum I measured**: dom 82–100 %, ratio 0.48–0.87,
   bind 0.08–4.3 %. 5120 is already borderline (dom 51–97 %, ratio up to 1.30 at high angle). 2560 fails
   it everywhere outside hands-off. 7680 keeps the excitation-limiter character universally; it buys a
   smaller onset effect, which is a real cost the operator should be told about, not one I can decide.

   | dose | CREEP dom / ratio | HANDS-ON dom / ratio | HIGH-ANGLE dom / ratio | FAST-WHEEL dom / ratio |
   |---|---|---|---|---|
   | 10240 *(today)* | 100 / 0.10–0.15 | 97–100 / 0.39–0.50 | 97–99 / 0.54–0.65 | 100 / 0.36–0.43 |
   | **7680** | **100 / 0.13–0.20** | **92–99 / 0.52–0.66** | **82–96 / 0.72–0.87** | **100 / 0.48–0.58** |
   | 5120 | 100 / 0.19–0.30 | 72–91 / 0.78–0.99 | **51–78 / 1.08–1.30** | 91–97 / 0.73–0.86 |
   | 3840 | 100 / 0.25–0.40 | 60–81 / 1.04–1.33 | 37–60 / 1.44–1.73 | 76–87 / 0.97–1.15 |
   | **2560** *(V287 as specified)* | 100 / 0.38–0.59 | **38–53 / 1.56–1.99** | **26–36 / 2.16–2.59** | **43–57 / 1.45–1.73** |

2. **Re-specify Q5 and Q6 before the drive.** Q5's threshold must sit above its own CI (0.983, not
   0.980). Q6's must exceed its measured spread (×1.6 route-to-route at minimum, plus a stated minimum
   number of windows). Add one statistic in the **loaded high-angle** stratum — the 6–9 Hz and 18–22 Hz
   rate bands with `|ang| > 60` — because that is where my objection lives and the current prereg is
   blind there.

## 6. Two smaller corrections, not decision-bearing

- `rlog-tools/studies/grind/grind1_dclamp_decompose.py` line 47 still reads the dose from
  **`u16(0xC61BA)`**, the integrator anti-windup cell, not from `0xC61B6`. Both hold 10240 so every
  number in Appendix B is unaffected, but the script contradicts B7.1's own correction and would
  silently read the wrong cell against any image where the two differ — V287 itself included.
- B7.1's arithmetic assertion that the D clamp "rails at |dE| = 640 today, 160 at 2560, 80 at 1280" is
  **confirmed exactly** from the bytes.

**None of this is licence to act.** These are findings for the orchestrator; I have built nothing, sent
nothing and flashed nothing.

---

# REV 2 (`0xC61B6` = 7680) — **PASS WITH CONDITIONS**

Re-run 2026-09-06 against the built rev 2 image and prereg §C5. Scripts:
`adv_v287r2_b_units_strata.py`, `adv_v287r2_power.py`, `adv_v287r2_auth.py` (all in
`rlog-tools/studies/grind/`, outputs beside them in `_scratch/`). Analysis only.

**Crux.** My F2 objection is answered: 7680 is admissible in every stratum on my machinery, and F1 and F3
are clean at the new dose. Two things are not closed. **The 7.3 Hz ring gate has zero margin and the
quantity it turns on is not measured reproducibly** — Appendix C4 puts the loaded 6–9 Hz multiplier ratio
at 0.9895, I measure 0.969–0.983, and that difference alone is larger than the whole gate. And **Q2's
power statement is understated about 3.4×**, with a floor that makes it unresolvable against the V282
baseline that exists today.

## R1. The image is what it says it is [EVIDENCE, full-file diff]

sha256 `e75ae7eb5c5bcba564f445a7223260b25c4b476b9df1d8c9ad8e171f79498f15`. Exactly **5 bytes** differ from
V282: `0xC61B7` `28`→`1e` (the D clamp's high byte, 10240 → 7680) and the 4-byte cal-page CRC at
`0xC6FFC`. Every other chain cell — out clamp, deadband, anti-windup, P clamp, sum clamp, both lag
halfwords, fb clamp, r24 gain — is byte-identical. The cell reads back from the image as **7680**.

## R2. F1 at 7680 — clean

`D = 16·dE`, so 7680 rails at `|dE| = 480`. The feedback part alone now needs **1942 deg/s²** sustained,
**46.3 deg/s** at 7.3 Hz, or **24.2 deg/s** at 20.3 Hz. The setpoint part rails at 15 map counts, about a
**3.5-count** command step per frame (2560 took 2, today's 10240 takes about 4.7).

## R3. F2 admissibility — **PASSES in every stratum on my machinery**

Pooled r39+r3a+r3c, my segment sampling, at 7680:

| stratum | dom % | p99 \|D_fb\| / clamp | bind % |
|---|---|---|---|
| CREEP / LOW-MID / SUBURBAN / HIGHWAY hands-off | 100.0 | 0.17–0.20 | 0.03–0.23 |
| HANDS-ON \|bar\|>700 | 97.5 | 0.57 | 2.64 |
| HANDS-ON HARD \|bar\|>1500 | 98.7 | 0.56 | 2.92 |
| LOADED \|ang\|>60 | 93.8 | 0.75 | 3.77 |
| FAST WHEEL >25 deg/s | 99.6 | 0.54 | 4.04 |

I do **not** reproduce C2's SUBURBAN 79.7 % — I get 100.0 %. Our dominance numbers diverge by segment
sampling in several strata, and the dominance metric is evidently sampling-sensitive. **The p99 ratio is
the criterion both of us measure the same way** (mine 0.17–0.75, C2's 0.20–0.79) and it is below 1
everywhere. On that criterion 7680 is admissible, not borderline. The 2560 objection is fully answered.

## R4. F3 authority at 7680 — clean, and now trivially so

Paired, same steps at both clamps, 130–199 measured full-demand steps per route:

| route | n | 0–50 ms | 0–100 ms | 0–200 ms | peak | 95 % CI on 0–100 ms |
|---|---|---|---|---|---|---|
| r39 | 199 | 0.994 | 1.000 | 0.999 | 0.998 | [0.994, 1.005] |
| r3a | 157 | 1.000 | 1.000 | 1.000 | 1.000 | [1.000, 1.000] |
| r3c | 130 | 1.008 | 1.004 | 1.000 | 1.000 | [0.998, 1.008] |

Q8 will pass. Authority is not an axis of concern at this dose.

## R5. 🛑 THE RING — the one open item, and it is a zero-margin gate

C4 gates on the measured 6–9 Hz in-band multiplier in the loaded stratum, scaled **relative** to today,
against the CI upper bound 0.983. C4's input: m 0.951 → 0.941, a ratio of **0.9895**. Mine, same
quantity, same stratum, per route:

| route | m @ 6–9 Hz, 10240 | m @ 6–9 Hz, 7680 | ratio | implied Kd_eff |
|---|---|---|---|---|
| r39 | 0.9368 | 0.9140 | **0.9756** | 119.9 → 117.0 |
| r3a | 0.9336 | 0.9049 | **0.9693** | 119.5 → 115.8 |
| r3c | 0.9258 | 0.9102 | **0.9832** | 118.5 → 116.5 |

I measure a Kd loss of **1.7–3.1 %** where C4 assumed **1.05 %** — **1.6× to 2.9× larger**. Propagating my
ratio through C4's own ladder (its `|L_tot|` moves −0.286 per unit of m across its rows) gives
**`|L_tot|` about 0.985 / 0.988 / 0.985**, against the gate 0.983. C4's own table marks 0.987, its 6144
row, a **FAIL**.

I am not claiming 7680 fails the ring. I am claiming something weaker and, for a flash decision, worse:
**the gate has no margin by C4's own words, "exactly at the bound", and two independent measurements of
the single quantity it turns on differ by more than the entire margin.** A gate that cannot be measured
to better precision than its own width has not been passed. This is the one item I would put in front of
the operator before flashing, and it is adjudicable cheaply: reconcile the two in-band multiplier
measurements, or move the gate off the CI edge.

## R6. F4 on the re-specified thresholds — two fixed, one not, one wrong

- ✅ **Q5 is fixed.** 0.983 is the CI upper bound, outside the point estimate. My original objection is
  answered.
- ✅ **Q10 is the best-specified statistic in the prereg, and it is safer than C5 thought.** I recompute
  the loaded-stratum route spread at **×1.09** (6–9 Hz) and **×1.30** (18–22 Hz), tighter than C5's quoted
  ×1.44 / ×1.86. Against thresholds ×1.9 / ×2.3 that leaves margins of ×1.75 and ×1.78.
- 🛑 **Q6 is still inside its own noise.** Route-wide engaged, my pooled statistic is 0.2647 / 0.4840 /
  0.3020 across r39 / r3a / r3c — a route-to-route spread of **×1.83** against the re-specified **×1.60**
  threshold. Raising it from ×1.3 to ×1.6 was the right move and did not go far enough. Also, "≥ 20
  qualifying windows" is ambiguous: on a **creep** reading only 2–3 windows exist per route and Q6 would
  be structurally unevaluable; on the route-wide reading there are 241–439 two-second tiles. C5 says every
  statistic is route-wide, so route-wide it is, but the word belongs in the definition before the drive.
- 🛑 **Q2's power statement is understated by about 3.4×, and as written it cannot resolve at all.**

## R7. The Q2 power arithmetic, in detail

I reproduce Appendix C's onset extraction verbatim and get its numbers exactly: r39 **435 events,
×0.947**; r3c **229 events, ×0.9299** (C3 says ×0.930). So the disagreement below is arithmetic, not
method.

**(a) C3's SE formula is wrong, and on r3c it is wrong in the build's favour.** `1.253·(IQR/1.349)/√n` is
the normal-theory median SE; the onset pool is strongly right-skewed (r3c p75/p50 = 2.98 against
p50/p25 = 1.82). Bootstrap, 4000 resamples, on the same pools:

| route | C3's normal-theory SE | bootstrap SE |
|---|---|---|
| r39 | 4.3 % | **3.9 %** |
| r3c | 14.9 % | **4.0 %** |

C3's r3c line, "resolvable only beyond ×0.701", is too pessimistic by 3.7×; the true figure is ×0.920.

**(b) But the comparison is UNPAIRED, and that is decisive.** C3's ×0.947 is a *paired* number: the same
435 events simulated at both clamps in the mirror (paired bootstrap SE 0.47 %, resolvable beyond ×0.991).
**One drive on the car cannot do that** — it yields one clamp, compared against a V282 baseline from a
different drive. The variance of that ratio is the sum of both sides'. With the V282 baseline left at the
n it has today:

| route | baseline n | baseline SE | 2·SE floor on the ratio | effect | resolves? |
|---|---|---|---|---|---|
| r39 | 435 | 3.9 % | **7.8 %** | 5.3 % | **no, at any drive length** |
| r3c | 229 | 4.0 % | **8.0 %** | 7.0 % | **no, at any drive length** |

Growing both sides: **n about 1,900 events each, about 64 minutes of engaged driving on EACH side**, so
about **128 minutes total**, against C3's stated 38. C3's 1,150 is the correct *one-sample* answer to the
wrong question.

**(c) Between-route confounding, ×12 the effect.** The same statistic on the same build reads **4.03 on
r39 and 6.56 on r3c — ×1.63**. The predicted effect is 5.3 %. Unless the V287 drive is route-matched to
the V282 baseline, route composition dominates the comparison outright.

⭐ **The fix is free and already in the prereg.** Q1 compares the measured 427 tap against the mirror at a
chosen clamp, on the same drive. Run Q2 the same way — measured onset envelope against the
**10240-mirror prediction on that same drive** — and the comparison becomes paired and within-drive. That
removes the between-route nuisance and the two-sample penalty at once, and by the paired SE above it
resolves ×0.947 comfortably on a single normal route.

## R8. Verdict and conditions

**PASS WITH CONDITIONS.** Admissibility, the unit chain and authority are all clean at 7680, and the
rev 1 FAIL is fully answered. Before flashing:

1. 🛑 **Adjudicate the ring gate.** Two measurements of the loaded 6–9 Hz multiplier ratio differ by more
   than the gate's entire margin, and my value lands in C4's own FAIL band. Either reconcile them or move
   the gate off the CI edge. This is the only item with a safety consequence.
2. **Re-specify Q2 as a within-drive comparison against the 10240 mirror**, as Q1 already is. If it stays
   a cross-drive median comparison, state plainly that it needs about 64 minutes on each side and a grown
   V282 baseline, and that it licenses nothing below that.
3. **Raise Q6's threshold above ×1.83**, and write "route-wide" into the window definition.
4. Q5 and Q10 need nothing further.

**None of this is licence to act.** Findings for the orchestrator; nothing built, sent or flashed.
