# STATE — living current state of the kit

**Last updated: 2026-08-02.** This file is the single current-state record. Update it in place at every
close-out; do not append new dated blocks (that is what made `CLAUDE.md` unreadable). The narrative of how
each state was reached lives in `docs/HANDOFF-*.md`.

**Read alongside:** `docs/BUILD-LINEAGE.md` (what has already been flashed, falsified, or **rejected on
review** — check it before proposing any calibration edit) and the latest handoff,
`docs/HANDOFF-2026-08-02-v67-flew-and-the-highway-grind-is-not-the-rate-lane.md`
(predecessors: `HANDOFF-2026-08-01-grind2-is-v62s-own-fix-at-high-frequency.md`, then
`HANDOFF-2026-08-01-v62-flew-and-the-grinding-is-fixed.md`, then
`HANDOFF-2026-07-31-v64-the-null-is-on-the-gate.md`, then
`HANDOFF-2026-07-31-v61-worse-the-rate-lane-is-the-damper.md`, then
`HANDOFF-2026-07-31-v60-null-and-the-v52c-fabrication.md`, then
`HANDOFF-2026-07-30-v59-drive-and-the-loop-hypothesis.md`).

---

★★★★ **THE HEADLINE, 2026-08-02 (LATEST): V67 FLEW AND IT IS THE BEST BUILD THIS KIT HAS MEASURED —
GRIND #1 FIXED AND THE CREEP GRIND #2 ELIMINATED. THE NEW HIGHWAY SYMPTOM IS *NOT* THE RATE LANE.**

Route **`47`** (`75604b0a432fdc89_00000047--3e0b6134c0`), 26 segments, **1,495 s**, an ordinary
street → highway → street → parking-lot commute (not a provoked test route).

✅ **The probe is live and the gate works.** 150,327 frames, decoded two ways: byte4 takes exactly two
values `{0x87, 0xC7}`; **`bit6` == `carControl.latActive` in 150,302/150,327 = 99.983%** (the 25
disagreements are single-frame transition edges); **`bit5` (`gp-0x671d`, the masking risk) = 0** and
`bit4` (`gp-0x671a`) = **0 in every frame**; `illegal` = 0; VOID = 0. ⇒ V67's arm was a **clean binary**
— stock LERP vs `0xC6446` = 5244, nothing masking it. ⚠ `bit4` is now a **wasted rung** (V64 closed it).
✅ **FLIGHT-CLEAN:** `ST == 4` = **0/150,327** (zero-EME streak now past 500k frames), `ST == 3` = 12,
zero `steerUnavailable`/`steerTempUnavailable`/`canError`/`controlsMismatch`/`immediateDisable`/
`steerSaturated`.

★★ **THE WITHIN-ROUTE GATE A/B — route 47 is the first route containing BOTH doses**, with the arm state
recorded per frame, so the contrast needs no cross-route comparison. 18–22 Hz engaged-creep, cell-
stratified, episode-clustered: **ENGAGED arm 0.524 [0.337, 0.804]** vs the Kd = 1 pool (and 1.183
[0.773, 1.617] vs Kd = 2), **DISENGAGED arm 1.055 [0.669, 1.354]** vs Kd = 1. ⇒ **suppression in ONE arm
only** — V67's conditional design, measured, and the first evidence ever to separate V66 from V67
(their probe payloads cannot). 🛑 28 windows / 11 episodes — strong, not proof; confirm the `.rwd` name.

★★ **GRIND #1 IS STILL FIXED** — engaged creep, 18–22 Hz, p90 of window envelope p99, episode-bootstrapped
against the Kd = 1.00× pool (split-half null **[0.90, 1.12]**):

| dose | route(s) | secs | 18–22 p90 | **ratio [95%]** |
|---|---|---|---|---|
| Kd = 0 | V61 `r31` | 33 | 1290.0 | **1.50 [1.40, 1.62]** |
| Kd = 1.00× | V58 `r2b` + V59 `r2c` + V64 `r35` | 173 | 860.4 | 1.00 (ref) |
| **Kd = gated (V67 `r47`)** | | **22** | **480.9** | **0.55 [0.35, 0.65]** |
| Kd = 2.00× | V62 `r37` + V65 `r3a`/`r3b` | 375 | 337.2 | **0.39 [0.32, 0.48]** |

Monotone in dose, all far outside the null. V67 ≈ V62 (CIs overlap), as the arithmetic predicts.
⚠ **V67's engaged-creep exposure is only 22 s / 17 windows** — route 47 was a commute. Read the CI.

★★ **THE CREEP GRIND #2 IS GONE.** Creep, 40–49 Hz, burst = a 2.56 s window with envelope p99 > 500
(the V62/V65 bursts ran 2000–4000):

| dose | LKAS ON secs / MAX / bursts | LKAS OFF secs / MAX / bursts |
|---|---|---|
| Kd = 1.00× | 173 / 110.6 / **0** | 137 / 89.8 / **0** |
| **Kd = 2.00×** | 375 / **1830.7** / **18** | 140 / **1469.6** / **6** |
| **V67** | 22 / **83.5** / **0** | 91 / **48.8** / **0** |

🛑 **The two arms are NOT equally supported.** Manual: expected 3.91 bursts, **P(0) = 0.020** — solid.
**Engaged: expected only 1.04, P(0) = 0.35 — UNRESOLVED**, and that is exactly the operator's own
uncertainty. **It needs a parking lot, not a build.**

🛑🛑 **AND THE HIGHWAY SYMPTOM SHOWS NO RATE-LANE DOSE RESPONSE — a prediction of mine, refuted.**
The enabler: **route `2b` (V58, Kd = 1.00×) carries 227 s of highway-engaged driving** that two sessions
had assumed did not exist. v > 20 m/s, engaged throughout:

| dose pool | secs | 40–49 p90 | **40–49 MAX** | **bursts** | **ratio vs Kd=1 [95%]** |
|---|---|---|---|---|---|
| Kd = 1.00× (`r2b`+`r2c`) | 238 | 86.7 | 341.1 | **0** | 1.00 |
| Kd = 2.00× (`r37`+`r3b`) | 361 | 84.9 | 154.5 | **0** | **0.98 [0.71, 1.63]** |
| Kd = 2.44× (`r47`) | 797 | 67.1 | 267.0 | **0** | **0.77 [0.56, 1.44]** |

**Split-half null [0.53, 1.86] — both ratios inside it. No ordering. Zero bursts anywhere in ~1,400 s.**
And the identity question is settled by amplitude: creep grind #2 runs f0 43–45 Hz at prominence
**48–1062×** and envelope **2000–4000**; the highway population runs f0 45–47 Hz at prominence **~6×**
and envelope **155–370**. ⇒ **Not grind #2.** The operator's *"maybe this is a grind #3 or #2.5"* stands.

⇒ 🛑 **I PREDICTED THE OPPOSITE FROM ARITHMETIC AND WITHDREW IT.** V67 genuinely delivers **2.44×** at
highway — its maximum, 22% above V62's 2.00× — because a flat scalar arm replaces a surface Honda
**rolls off with speed**. That is correct arithmetic and it makes a tidy story with the operator's
report. **The data does not support it.** Building V68 on it would have been this kit's recorded failure
mode — *a statistic computed correctly over the wrong population* — for the fourth time.

**What IS real at highway:** within route 47, 21 maneuvers vs 21 **matched** straight-line controls give
1–4 Hz 1.21 · **6–9 2.78** · 10–16 1.41 · 18–22 1.86 · 24–28 1.88 · 30–40 1.58 · **40–49 2.13**
(nulls ~[0.6, 1.5]) ⇒ **broadband from 6 Hz up**, with 6–9 Hz rising *more* than 40–49 Hz, at absolute
levels ~50× below the creep bursts. A maneuver loads the wheel and everything gets noisier.

🛑🛑 **THE HARD LIMIT: BOTH INSTRUMENTS ARE BLIND ABOVE ~50 Hz.** CAN grid ~100.5 Hz (Nyquist 50.2);
comma IMU **99.9–100.5 Hz** (Nyquist **49.97–50.26**). **The IMU gives NO headroom over CAN.** If the
felt highway vibration is above 50 Hz, nothing in this kit can see it, and every null above is silent
about it. This also re-confirms that IMU/CAN frequency agreement carries **no** information about the
44.9 vs 55.6 Hz alias.

🛑🛑 **THREE CLAIMS OF MINE, MADE AND RETRACTED THE SAME NIGHT — read this before quoting any
rate-axis number.** I published (a) *"bus counts = 8 × deg/s"*, (b) *"the rate axis is arithmetically
dead — all three populations sit in the flat `[0,400]` segment"*, and (c) *"V67's build note has a units
error; its arm delivers 1.94×"*. **All three are WRONG.** Settled two ways: regressing `rate_c` on the
differentiated ANGLE channel gives slope **0.95–1.00, r ≥ 0.985** ⇒ **the bus rate field IS deg/s**; and
at 4.7121 counts/deg-s the inner breakpoints are **85 / 297 / 637 deg/s**, which real driving reaches
(|rate| peaks at **521 deg/s** over 407,617 frames), whereas the wrong scale would put them at
679 / 2377 / 5093 where Honda's 2× rolloff could **never engage**. ⇒ **V67's build note was CORRECT**
(LERP 2622 ⇒ exactly **2.00×**), and **the rate axis IS usable**: grind #1 ~603, creep grind #2 ~1206
(both on the `[400,1400]` rolloff), highway ~141–198 (flat; X1 = `0x0190` exactly and Y0 == Y1 in every
curve of both LERPs). **The error was composing two unverified structural relations into a scale instead
of measuring it against a channel already in the cache.**

★ **DESIGN A — the best-characterised alternative, ONE halfword**: `0xD2ABC` (the 10 km/h record's
`Y[1]`) **2561 → 7051**. grind #1 **2.00×** · creep grind #2 **1.22×** (vs V67's 2.18×) · highway
**1.00×** (vs V67's 2.44×). Blast radius clean two ways, no float mirror, CRC block #41 only, never
edited in any build; saturates at `|dtorque| ≥ 1190` vs a measured max of 839. 🛑 Costs: it is **not**
LKAS-gated (so unlike V67 it changes manual feel at low speed), and the multiplier **humps to ~2.45×
near 10 km/h** because `0xD2AB0` *is* the 10 km/h breakpoint record. **Not recommended while V67 already
has grind #1 fixed and creep grind #2 at zero bursts** — it would trade a measured property for margin
on quantities already at zero.

🛑🛑 **A TYRE TRAP THAT WOULD MANUFACTURE "GRIND #2 AT HIGHWAY":** at highway the persistent 40–49 Hz
**line is wheel order 3** (measured per-window order p50 **2.994**; 26–32 Hz is order 2 at **1.995**,
n > 600). At 30.8 m/s order 3 = **44.3 Hz**, one bin from grind #2. The bursts themselves are NOT the
order (on/off-order power ratio 6.94 in quiet windows, **0.82 inside bursts**). ⚠ And `fs_of()` is
biased **+0.5–1.4% route-dependently**: the true `0x14A` rate is **100.000 Hz**, so grind #2's
"44.9 Hz" is **44.6 Hz** and the between-route frequency spread was the instrument, not the car.

🛑 **NO SPEED- OR TORQUE-CONDITIONAL BYTE EXISTS TO GATE ON**, over two independent search passes —
every candidate is multi-valued, inline-only, standstill-only, dead (`0xC62EA` = 0 since V53), or
answers the same "LKAS applying" question V67 already found insufficient. The architectural reason:
this firmware's idiom for speed is **"always LERP, never threshold-and-latch."**
🛑 **Do NOT repoint the mask arm `gp-0x671d`**: it is a rising-edge counter driving **DTC 0x5e**, read by
**8 functions** including 4 reads in the motor-off dispatcher `FUN_0003d4a2`, where an edge-detector on
the counter forces a retry path. Unlike the dead `gp-0x683c` it is a **live fault response**.
🛑🛑 **The >50 Hz probe is DEAD at the proven cave site**: hook `0x55C0E` runs at **100 Hz (task 5)**,
not 1 kHz — it is the CAN-`0x14A` frame builder reached only via handler slot 10 ← `FUN_00022ca0` — so
the cave **cannot observe 1 kHz content at all**; and **no stock writer ever clears bits 7:3** of
`gp-0x1514` (8 accesses, all masked RMW), so a sticky latch could never clear. ✅ Separately,
`gp-0x683c` **is** a free `.data` byte on V67+ (V67 removed its only reader; two boot loops zero it) —
useful cave state in future, but it does not rescue the 100 Hz problem.
⚠ **`gp-0x67ac` is OPEN and matters**: when it is 1, `FUN_0003aa2c`'s very first instruction routes
around the branch that adds r24/r26 — **both lanes drop out of the aggregate entirely**, regardless of
which gain arm was selected. Close it before any future r24 build.

⇒ ★★★ **RECOMMENDED: KEEP V67 ON THE CAR. NO CONTROL-PATH CHANGE IS SUPPORTED.** The two real gaps are
**(A)** 22 s of engaged-creep exposure — closed by a 5-minute parking-lot drive, not a build — and
**(B)** the >50 Hz blindness, which needs a probe that samples inside the 1 kHz task and reports a
**sticky** HF flag. Reproduce every number above with
`analysis-2020accord/r47_orchestrator_checks.py`; the surface arithmetic is in
`analysis-2020accord/v68_design_math.py`.

★ **Open lead, recorded not chased:** the highway symptom may be the **RATCHET** (6–9 Hz), not grind #2 —
6–9 Hz rises most during maneuvers and the ratchet is strongly LKAS-gated (p = 1.09e-08), which matches
*"only during LKAS-engaged"* far better than grind #2's weak 84.5%-vs-54.7% association. ⚠ Counter:
between builds 6–9 Hz at highway runs 169.0 / 197.8 / **106.9** — V67 is the **lowest**.

★★★★ **THE HEADLINE, 2026-08-01 (LATEST): THE ROOT CAUSE OF "GRIND #2" IS V62's OWN FIX, AND THE
BAND TABLE SHOWS IT AS ONE KNOB DOING BOTH THINGS.**

The operator flew **V65** (= V62's control-path edits byte-identical + the saturation-ladder probe) on
two new routes — `3a` (`4e55c1e0f4`, grind #2 demonstrated **with LKAS ON**) and `3b` (`a4a7f4dbf1`,
demonstrated **with LKAS OFF**, then unrelated highway) — and reported that V62 fixed the original
grinding but **introduced a second one**: a whole-car resonance at low speed under significant *driver*
steering input, *"almost like I have a subwoofer"*, **present regardless of LKAS engagement**.

**Corner-conditioned extreme-tail maxima, Kd = 1× vs Kd = 2×, 219 blocks** (corner = creep ∧ |driver
torque| ≥ 1200 ∧ |angle| ≥ 100°):

| band | Kd=1× | Kd=2× | **ratio** | p |
|---|---|---|---|---|
| 1–4 Hz (driver) | 4709 | 4763 | **1.01** | 1.00 |
| 6–9 Hz (ratchet) | 2773 | 3335 | 1.20 | 0.037 |
| 10–16 Hz | 2520 | 2005 | **0.80** | 1.00 |
| **18–22 Hz — GRIND #1** | 3656 | 1269 | **0.35** | 1.00 |
| 24–28 Hz | 485 | 1289 | **2.66** | 0.013 |
| 30–40 Hz | 373 | 1113 | **2.98** | 0.013 |
| **40–49 Hz — GRIND #2** | 301 | **3526** | **11.71** | **0.0003** |

⇒ ★★★★ **A MONOTONE FREQUENCY RESPONSE WITH A CROSSOVER BETWEEN 22 AND 24 Hz** — `0.80 → 0.35 → 2.66
→ 2.98 → 11.71`, with **1–4 Hz flat at 1.01** as a control. **Not generic roughness.** V62 **cut grind
#1 by 2.9× and raised grind #2 by 11.7×, with one knob.**

**Why:** `gp-0x4f62` is a **4-sample finite difference at 1 kHz** (`2*(x[n]−x[n−4])/4`, delay cal
`0xC6C42` = 4). A differentiator's gain **rises** with frequency — **1.93× at 41.6 Hz vs 20.9 Hz** —
so V62's *flat* ×2 raised the high band harder, in absolute terms, than the mode it fixed. V62's build
note computed selectivity only against the **driver** (1 Hz, 14.6:1) and never against a **higher**
mode, where the ratio runs the wrong way. Arithmetic: `analysis-2020accord/rate_lane_frequency_response.py`.

🛑 **A FILTER CANNOT FIX IT — structural, not numeric.** A differentiator rises +20 dB/dec, one real
pole falls −20 dB/dec ⇒ the cascade is **flat** above the corner, so one pole drives the 41.6/20.9
selectivity toward 1.0 and never below. Two poles low enough to bite by 42 Hz cost −92° at 20.9 Hz and
**destroy the damping V62 bought**. Raising the delay cal `0xC6C42` fails identically. **Do not
re-propose either.** ⇒ the separation must come from an **operating condition**, not from frequency.

✅✅ **AND THE COMMA IMU REPRODUCES THE DOSE-RESPONSE INDEPENDENTLY.** Same corner, Kd=2×/Kd=1× on the
accelerometer/gyro — a sensor sharing **no signal path** with the EPS (first use of the IMU in this kit):
**1–4 Hz p95 0.76 · 18–22 Hz 1.20 · 24–28 Hz 0.65 · 30–40 Hz 1.25 · 40–49 Hz p95 6.27, max 6.71.**
Medians ~1 everywhere (the phenomenon is in the tail); the rise is confined to 40–49 Hz.
⚠ **The IMU does NOT show grind #1's reduction and its grind-#1 positive control is weak** — a real
limitation, but physically coherent: grind #1 is a **torsional column mode** that need not reach the
chassis, grind #2 is the one the operator says *"makes the entire car vibrate"*. **The IMU's
selectivity matches the operator's own description of which one shakes the car.**

**Grind #2 itself:** ~**44.9 Hz**, sd 5.4, n = 43, **Q ≈ 37**; **NOT a harmonic** of grind #1 (slope
0.173 [−0.92, 1.59] against the 2.0 a harmonic needs); during bursts the IMU carries **20–50× its own
baseline**, ρ 0.23–0.55 with the CAN band at p ≪ 1e-70.
🛑 **Its frequency is ALIASED and unresolved** — CAN is a ~100.5 Hz grid ⇒ 44.9 and ~55.6 Hz are the
same observation; the IMU's ~101 Hz median is only 0.5 Hz away so **IMU/CAN agreement says nothing
about the alias**. It does not block the fix.

**Gating:** grind #1's top-decile creep windows are **100% engaged** (engaged/disengaged p99 **6.63×**);
grind #2's are **84.5%** against a **54.7%** base rate (p99 **1.33×**) ⇒ **grind #1 is LKAS-gated,
grind #2 is not.** Driver torque separates them **>8×** (grind #1 hands-off; grind #2 at `tq_avg`
1600–2700, |angle| 150–265°); steering rate only ~2× at creep with overlapping p90s.

★★★ **AND V65's OWN PROBE ANSWERED ITS QUESTION: THE AGGREGATOR NEVER RAILS.** The 4-level ladder on
`gp-0x6b94`, **120,049 frames**, orchestrator-verified from the caches: liveness **100%**, zero
invariant violations, and **+RAIL 0 / −RAIL 0** — the sum never comes within 20% of its own ±10240
clip. Only **54** frames pass ±4096 (48 negative, 6 positive), and `bit6↔bit3` alternation is
**0.0000 flips/s in every arm**, not as a small number but because **no rail frame exists**.
⇒ **The loop is LINEAR at the aggregator.** No describing-function or saturation reasoning is needed
in this chain, and a linear gain change on any lane **propagates faithfully** — which is *why* V62's
flat ×2 produced the band table above.
★ **All 54 non-neutral frames sit inside grind #2 bursts**, at 36.3–106.1× the segment-median 30–49 Hz
envelope (54/54) ⇒ the aggregator's only large excursions on either route are grind #2, independent
corroboration that it is a real large-signal event **in the command path**.
🛑 **DO NOT apply V65's pre-committed "all four quiet ⇒ NOT another lane gain" clause to grind #2.**
That branch was written to test whether the **RATCHET** is a rail-to-rail limit cycle. Grind #2's
attribution rests on an **on-car dose-response on exactly a lane gain**; an intervention outranks an
inference drawn from a different hypothesis. What the null *does* close is the **ratchet's**
"amplitude-saturated at the aggregator" reading, and the *clipping* rationale for the `0xD2AEC`
breakpoint lever.
⚠ **Stroboscopic caveat:** 100 Hz sampling a ~43 Hz burst cannot claim the sum touched ±4096 only 54
times — the true count is higher and the peak under-estimated. The **route-wide ±8192 null is
unconditional**; "never rails *during a burst*" is the weaker claim. Do not quote 54 as a rate.

✅ **V65 IS FLIGHT-CLEAN AND ADDS TO THE ZERO-EME STREAK.** `ST == 4` = **0** across both routes
(36,991 + 83,058), confirmed a second way by a raw-CAN recount off the `0x18F` src-1 frames rather than
the gridded cache. `STEER_STATUS` only ever 0 or 3, every `ST == 3` in a park/reverse segment. Zero
`steerUnavailable` / `steerTempUnavailable` / `canError` / `immediateDisable`; one `controlsMismatch`
per route; three `steerSaturated` on 3b seg 5. `latActive` 88.2% / 75.4%; CAN 99.94–100.04 Hz.
⚠ **Route `3b`'s highway section starts seg 3 (t ≈ 25 s) — exclude segs 3–12** from any parking-lot
statistic. The demos: 3a LKAS-**ON** = segs 3/4 (six bursts); 3b LKAS-**OFF** = seg 2 only,
`latActive` 0.00.

⇒ **See `docs/V66-V67-DESIGN.md`** for the full design. **V66** (built this session) = V65 with both
`sar` immediates reverted to stock + a four-bit **gate probe**; it is the operator's requested stable
long-drive build **and** the confirmatory intervention. **V67** = keep the ×2 but gate it on a
hands-on/driver-torque cell by repointing the **dead `gp-0x683c` gate** — a **ONE-BYTE** code edit into
a calibration arm that already exists. 🛑 **V67 is blocked on V66's chatter measurement.**

---

★★★ **THE PRIOR HEADLINE, still standing: V62 FLEW AND THE GRINDING IS FIXED. The kit's first measured
fix.** Route `00000037--6231e33f3d`, 15 segs, 86,278 frames. Operator: *"Original grinding at 2–5 mph is
gone!"* Engaged creep, speed-standardised, **episode-clustered** bootstrap: 18–22 Hz **0.124 [0.036,
0.387]** vs V59 (8×), and **0.024 [0.016, 0.234] at |rate| 16–32 deg/s (42×)**, with a **30–40 Hz negative
control at ~1.0** ⇒ band-specific, not a route offset. Transient rates **0.793 / 0.486 / 0.338** at
>200/>500/>1000 counts per 10 ms — monotonically cleaner, and the **lowest p90/p99/>1000-rate of any
build**. ★ V61 quantified on the same statistic: p50 roughness **730** vs V59's 101, >1000 excursions
**376.7/s vs 24.3/s** — the operator's "significantly worse", at 15×.

🛑 **The reported "new grinding at 10–20 mph" is NOT an established regression.** Wall clock measured
(±0.05 s): **10:12:15 → seg 1 t=9.67 s** (5.4 mph, *not* 10–20), **10:23:24 → seg 12 t=18.63 s** (16.3 mph).
Both relocated **independently of the operator's memory**. They are **two different phenomena**:
instant #2 is an ordinary roughness burst **V59 produces ~3× MORE often** (1.042/s vs 0.354/s) — the
*unmasking*; instant #1 is a **0.92 s singleton** carried by **38–46 Hz** (8,478× median) while 18–22 Hz
sat at 1.4× median. 🛑🛑 **Its 43 excursions >2000 are ONE burst ⇒ n = 1.** By distinct bursts/engaged
second: V62 **0.00142 [0.00004, 0.00793]**, V59 **0 [0, 0.00986]** — **V62's CI is INSIDE V59's**;
V61 is **72×** V62. Exposure-matched (v 2–4 m/s ∧ |rate| ≥32 deg/s: 16.14 s vs 15.75 s, one event) ⇒
**p = 0.51, a coin flip.**
⇒ ★★★ **RECOMMENDED: NO NEW BUILD. Fly V62 again and count bursts.** The open question is the *rate of a
rare event*, which needs exposure, not firmware. See "Recommended next steps".

⇒ ★★★ **AND r26 IS STRUCTURALLY INERT.** `avg`'s cal base `0xC6564` byte-reads as **40 bytes of exact
zero** (bounded by non-zero data both sides), with no writer for the RAM adjustment ⇒ `stage1 ≈ 0`
regardless of dtorque. **V62's `0x3AB76` edit was a NO-OP, and r24 carries the entire rate lane.**
This re-attributes V42 (null because r26 was *already* zero), V61 (WORSE = killing **r24**) and V62
(fix = doubling **r24**), and **supersedes** the standing claim *"killing either alone leaves the other
transmitting."*

🛑 **THE PRIOR HEADLINE, still standing: V61 made the grinding WORSE, and that inverted the record.** The
torsion-bar RATE lane (`r24`/`r26` in `FUN_0003aa2c`) is the mode's **DAMPER**, not its amplifier. Every
build that touched it — V39, V42, V61 — tested it **downward**. The gradient points **up**.

🛑 **Explain firmware with Python that mirrors the decompiled arithmetic exactly** — standing operator
instruction, 2026-07-28. Integer `>>`, the real Q-format, the real branch conditions, each line annotated
with its instruction address, constants byte-read **little-endian** (V850 is LE). dB/Hz interpretation
comes *after* the code, never instead of it.

---

## 🛑🛑 THE TWO SYMPTOMS ARE DIFFERENT PHENOMENA — settled by the operator 2026-07-30

Everything before this date conflated them. Read this before any other section.

| | **RATCHET** | **GRINDING** |
|---|---|---|
| frequency | **~7.4 Hz** (Q≈36, 2nd harmonic locked at 15.0 Hz) | **FIXED ~20.9 Hz** ⚠ see below |
| where it dominates | parking-lot creep at large steering angle | ⚠ **CREEP-ONLY on V58** — see below |
| variance share, r29 burst | **33.0%** (6–9 Hz) | **5.3%** (19–24 Hz) |
| vs command saturation | **rises 8.42×** with rail duty | falls to 0.74× |
| in openpilot's command? | **no** — command's 6–9 Hz peak is 6.26 Hz, 6.4 bins away | ⚠ **YES** — see below |

🛑 **Three entries in that table were corrected by the V58 drive (route `2b`, 2026-07-30).** They are
left visible above with pointers rather than silently overwritten:

1. **The frequency law `f = 0.177·v + 20.48` does NOT reproduce.** Strict 18–26 Hz band, sub-bin peak,
   speed stable within 1.5 m/s: slope `a = −0.005 … +0.031` at every prominence cut (n = 23–75, v span
   1.13–17.5 m/s). **`a = 0` fits within 0.12–1.48σ; `a = 0.177` is rejected at 3.2–7.1σ.** Model-free
   per bin: 20.65 / 20.83 / 21.90 / 21.50 / 21.61 / 20.46 Hz over 0–20 m/s vs a predicted 20.66 → 23.49.
   ⚠ **Do not rewrite the law off one route yet** — the recorded value came from a *pooled cross-route*
   fit whose own source warned "steering angle shifts it ±2 Hz", and on route `2b`
   `spearman(v,|ang|) = −0.728`. Re-run the strict-band test over V55/V56/V57 first (step 2 below).
   ⚠ **Search-band trap:** a 15–30 Hz or 17–28 Hz band catches the **ratchet's 2nd harmonic**
   (2×8.0–8.9 = 16–17.8 Hz) at road speed; the argmax then steps down to ~15 Hz and fakes a *negative*
   slope. A creep-only window fakes a *positive* one. Use 18–26 Hz **plus a presence test**.
2. **Creep-only, not road speed.** 18–26 Hz prominence by speed (engaged): 141× / 138× / 518× at
   1–2 / 2–3 / 3–4 m/s, collapsing to 29× / 11× / 8× / 7× at 4–6 / 6–10 / 10–14 / 14–18 m/s — and above
   6 m/s the peak-frequency scatter (sd 1.5–2.2 Hz) shows there is no coherent line at all.
3. **~21 Hz IS in openpilot's command.** Verified on the **native 0xE4 grid**, so not a held-last
   resampling artifact: 20.89 Hz at prominence 34.0×, `coherence(cmd, bar) = 0.917` at 20.96 Hz (K=4,
   95% null 0.632); co-located command peak in 8/21 strong-line windows vs 1/11 weak. The bar's line is
   6–7× sharper, which reads as an echo — but **direction is unresolved.** Carrier phase cannot settle it
   (one-sample mailbox skew = 75° at 21 Hz), and the skew-robust **envelope** cross-correlation was
   **inconclusive** (2/4 runs bar-leads, 2/4 command-leads, peak corr only 0.33–0.44). ⇒ openpilot is
   inside this loop; that is a constraint on any firmware fix, not an action.

⚠ **Operator correction, authoritative:** the 7.4 Hz line is the **ratcheting**, not the grinding. An
earlier pass this session called it "the grinding" and concluded the kit had been chasing the wrong mode
for 50 builds. **That conclusion is withdrawn** — the 20–25 Hz focus was correct all along.
⚠ **Steering-angle excitation of the 7.4 Hz mode is a CORRELATION only**, related through return-to-centre.
Do not treat angle as causal.

**The ratchet is not the V42 ratchet.** `STEER_STATUS == 4` fires in **0 of 37,922 frames** across both
V57 routes, so the state-4 governor (`0x454FE`, root-caused and fixed by V42) is not producing it.
Mechanism unknown. It is a plant limit cycle gated by applied LKAS torque, not commanded: over 0.21 s the
command drifts 510 counts while the torsion bar swings **2,791 counts through 3 sign changes**.

---

## ★★ V59 FLEW 2026-07-30 (route `2c`) — the grinding mechanism is a PARAMETRIC PUMP, and it is MARGINAL

**V59 is FLIGHT-CLEAN.** 50,963 frames / 9 segments (2,5,6,7 not uploaded). `ST==4`: **0/50,963**.
No `steerUnavailable`/`steerTempUnavailable`/`canError`/`steerSaturated`. Probe **100% live, 100%
thermometer-monotonic, fault sentinel 0.000%**, stock low bits `&0x07 == 0b111` with zero exceptions.
`0x14A`/`0x18F` at 100 Hz. Two boundary transients only (a boot cluster in `wrongGear`, and one
`controlsMismatch`/`immediateDisable` at the tail of seg 12 — parked, LKAS off). ⚠ The route was NOT
the pure creep route specified: segs 4/8/9 are road speed to 23.6 m/s. It did deliver what `2b` could
not — **50.2 s of engaged + creep + SUSTAINED hands-off**.

### The mechanism
`gp-0x6ba6` is `|filtered signal|` — **rectified** — so it sweeps the boost-amplitude LERP at **2× the
mode frequency**. Measured, engaged+creep+hands-off (13 runs, K=30, periodograms averaged across
DISJOINT runs, never spliced): the thermometer's own spectrum peaks at **42.19 Hz** (= 2 × 21.09 to
within one bin), prominence 11.10×; the 18–26 Hz band shows only 1.23×. **Disengaged: bit5 NEVER
toggles — 0/4 runs, 61.2 s, K=90, prominence 0.00×.** Depth 76.93% <512 / 18.46% 512-1k / 4.57% 1k-2k
/ 0.04% ≥2048 engaged, vs **99.83% <512** disengaged. Toggle rate **25.55/s hands-off, 9.42/s
hands-ON, 0.00/s disengaged** — hands-on the index sits *pinned high*, it does not modulate.
`corr(env, lvl)` is **positive in 11/11 hands-off runs** (median +0.487, +0.485 partialling out
effort); the negative hands-ON value is pure Simpson's paradox. **0 of 33 windows have the index
sweeping with no grinding line.**

🛑 **What V59 did NOT establish.** The index is `|x|` of a bar-derived signal, so 2f coupling and
index-tracks-mode are **arithmetically forced** once the ripple exists — coherence against the bar is
circular and is not evidence. What is new is the **depth**, and that it survives hands-off.
**Causality is not settleable observationally.** Only an intervention separates drive from echo.

### ⇒ It is an AMPLITUDE-GATED BOOTSTRAP, and it is MARGINAL
A pump at 2f into a mode at f is the principal Mathieu resonance; threshold `eps_crit ≈ 2/Q = 0.147`
at the recorded Q = 13.6. Simulating the **literal integer arithmetic** with the confirmed blend
direction, across both open unknowns (task rate; series question):

| `\|tq\|` amp | 1 kHz y4-only | 1 kHz both | 500 Hz y4-only | 500 Hz both |
|---|---|---|---|---|
| 218 (median) | 0.013 | 0.020 | 0.013 | 0.020 |
| 829 (p90) | 0.072 | 0.104 | 0.055 | 0.080 |
| 1451 (p99) | 0.104 | **0.169** | 0.070 | 0.116 |

eps scales with amplitude ⇒ a **bootstrap**: a kick raises the oscillation → the index swings wider →
the modulation deepens → more pumping, until the curve flattens past index 3645 and the clamps bite.
That is why the grinding **bursts** rather than hums, and why it needs a road input to ignite.

🛑🛑 **THE THRESHOLD COMPARISON IS UNDECIDABLE FROM THIS DATA — do not quote a verdict either way.**
`eps_crit = 2/Q` needs the **PASSIVE** Q (the mode's damping when *not* being driven). That is not
measurable while the mode is active, and V59 contains no free decay to measure it from:
- **Ring-down: none exists.** 66 candidate decays, longest **0.63 cycles** — envelope wiggle, not
  damping. The mode does not ring down; it is sustained while conditions hold.
- **Autocorrelation analytic envelope** (biased-ACF triangular taper divided out, tau capped at 25%
  of record) gives apparent **Q median 102, range 22–1083** (n=8 hands-off runs). ⚠ That is the
  coherence of a *driven* oscillation, **NOT** the passive Q — a self-sustained limit cycle has
  near-infinite apparent Q. It cannot be substituted into `2/Q`.

| assumed Q | eps_crit | verdict vs measured eps (0.020 / 0.104 / 0.169) |
|---|---|---|
| 13.6 (recorded, provenance unverified) | 0.147 | marginal — crosses only at p99 |
| 22 (lowest apparent) | 0.091 | **above** at p90 and p99 |
| 102 (median apparent) | 0.020 | **above everywhere** |

⚠ **What the coherence DOES support:** a passive Q=13.6 mode kicked by broadband road noise would
show coherence ~`Q/(pi*f)` ≈ 205 ms. Observed is 0.33–17 s equivalent — **far more coherent than
random excitation of a lightly-damped mode can produce.** ⇒ there is an **active, phase-coherent
drive**. That is consistent with the parametric pump but does not prove it is the drive.

⇒ **Only an intervention decides it. V60 is the discriminator, not just a candidate fix.**

### The structure — golden model was WRONG, and there is a filter nobody had modelled
`FUN_00034a72`: the two amplitude curves do **not** multiply in series. `0xD2888` scales the final
assist term (`sar 0xe,r13` @`0x35008`); `0xD28DC` enters earlier (`shr 0xe,r28` @`0x34C26`) and is
**differenced against `gp-0x6a56`** then clamped ±12000. ⚠ **UNRESOLVED DISPUTE:** a subagent holds
`0xD28DC` is a dead end (3 image-wide refs to state cell `gp-0x69bc`, all in-function). That argument
is **structurally invalid** — a scan of the STATE CELL cannot show whether the blended value is
consumed in a REGISTER the same tick, which is what a slew-limited gain does. The decompiler shows the
blended y1 as an operand of a `>>14`, and a byte scan finds exactly two `>>14` sites in the function,
one of them at `0x34C26` inside the span the subagent claims to have traced. **Not called. It does not
change the verdict** (see the table — both columns are mostly sub-threshold).

★★ **BOTH LERP outputs are SLEW-BLENDED before use** — previously unmodelled entirely. Rate cal
`0xCA06C[10] -> 0xD2006 = 102` (Q10). **Direction CONFIRMED @`0x34be4`** (`cmp r25,r10 / ble` →
instant snap when raw ≤ old): **FALLING is instant, RISING is slowed** — a fast-attack/slow-release
gain reducer. This is what pulls eps down from the raw-LERP values.

### Levers — one clean, three closed
- ★★ **`0xD2006` = 102, the blend coefficient. THE LEVER, and GATE 1 is CLEAN.** Lowering it
  attenuates the 42 Hz pump **without moving the static gain map at all** (the blend converges to the
  same steady state ⇒ DC assist and manual feel untouched). Blast radius byte-verified: exactly one
  pointer (`0xCA094`) references it; the "three identical copies" in `0xD2000` are modes 10/11/12's
  independent entries, not an array; distinct from the ceiling (`0xD2000`) and gain scalar
  (`0xD200C`) for the same mode; not array-consumed. Only other hit is the CRC/block directory.
  ⚠ Expected benefit is **modest and uncertain** — eps is already mostly sub-threshold, so this bites
  only on the loudest bursts. The argument for it is that a *bootstrap* only needs to be kept below
  threshold at the amplitudes where it currently crosses. Feel cost: slower gain recovery after a
  sharp input (tau ≈ 10 ms now, ≈ 24 ms at cal 43 — short vs steering dynamics).
- 🛑🛑 **FactorC damping (`0xD27BC`/`0xD27C6`) — ALREADY FLASHED AND FALSIFIED. DO NOT RE-PROPOSE.**
  **`V44` set `0xD27C6` 0 → 235 and `0xD27DA` 0 → 234 (modes 10/11), flashed, and it was NULL** —
  because **Factor E (`0xC9F84[mode]`, the motor-rate deadzone) re-zeroes the product downstream.**
  **`V47` then attacked Factor E itself** (`0xD2802/04/06`, `0xD2816/18/1A`) → *"marginally quieter at
  5 mph, no effect in motion."* **Both were confirmed 2026-07-28 to hit the LIVE table** (PN → key
  `TVAA1` → config row 2 → INDEX 10 → `0xD27BC`). `BUILD-LINEAGE.md` states it outright: *"the
  missing-damping hypothesis was genuinely tested and IS falsified — do not resurrect it on a 'wrong
  variant' theory."*
  ⚠ **Damping IS exactly zero below 35 km/h** (`Y[0]=0`, all 34 mode tables) and that remains true and
  relevant as *context* — but the lever has been driven from **both** factors and neither moved the
  grinding. V44's *rationale* was withdrawn (it thought the axis was driver torque; it is speed), yet
  **its on-car NULL stands regardless of why it was built.**
  🛑 **This was re-proposed on 2026-07-30 by the orchestrator as "V61", after the loop hypothesis made
  it look freshly attractive — the operator caught it. The build script was written and deleted
  unexecuted.** Cause: the address was named without grepping `build_v*_tva.py` first. **That grep is
  mandatory and it is cheap. FALSIFIED ≠ untested, and a compelling new mechanism is exactly when the
  check gets skipped.**

  ✅ **Salvage — genuinely new and worth keeping regardless:** the damper's **int/float lockstep is
  SAFE for a FactorC-class edit.** `FUN_000347b8` @`0x347b8` *reads* `gp-0x6bd0` (first line,
  `(float)gp-0x6bd0 * 0.0009765625`) and only re-clamps it with an independently recomputed **ceiling**,
  faulting via `FUN_000462e6(0x417a,…)` if the two differ by more than `0.0048828125` = **5/1024**. It
  **never recomputes the four-factor product**, so FactorA/C/Ramp/MotorRate are *not* float-mirrored.
  And the two ceilings are the **same table in two number formats**, byte-verified:
  `INT 0xC77A0[10] → 0xD209C: X=[300,800] Y=[512,1024]` vs `FLOAT tp+0x7554 = 0xC6554: 300.0, 800.0,
  0.5, 1.0`. ⇒ exact agreement, tolerance never approached. **Damper authority at creep is hard-clamped
  to ±512 against the aggregator's ±10240 (≤5%)** — a firmware-enforced bound worth remembering for any
  future damper-lane work. Confirmed 4 ways (`search_instructions`, raw LE byte scan, `get_xrefs_to`,
  and a **split-encoding check** for `movhi`+`movea` construction of the address — only 2 `movhi 0xd`
  exist image-wide and neither resolves near `0xC9E9C`). Modes 8/11 byte-identical to mode 10.
  Escalation map, for any future damper work: `FUN_000347b8` → `FUN_000462e6(0x417a)` →
  `FUN_00016de6(0x1d)`; and `FUN_00034350`'s own entry-time re-check → `FUN_0004613e(0x4179)` →
  `FUN_00016de6(0x1c)` — **one tolerance in two representations** (0.0048828125 × 1024 = 5.0 exactly),
  not two independent gates.
- 🛑 **RECORD CORRECTION — `0xD2018` is not what we said.** It is **data**, one resolved pointer inside
  `FUN_00035154`'s `0xC7888[mode]` ceiling array — `search_instructions` finds zero because it scans
  instruction operands only. And `FUN_00035154` is simply the `gp-0x6bbe` **analog** of `FUN_000347b8`:
  ceiling-only, same ±0.0048828125 tolerance, same escalation, keyed on `gp-0x6a62` instead of
  `gp-0x6ac2`. The old note ("any edit to `gp-0x6bbe`'s ceiling math must update `FUN_00035154`/table
  `0xD2018` or it may trip") implied a stronger, different mechanism. It is the same pattern.
- 🛑 **`gp-0x6b70` — TRACED AND CLOSED 2026-07-30. It terminates at an already-falsified lever.**
  Full chain, measured: `FUN_00038148` (1 kHz) sums **six UNITY-weighted terms** — `gp-0x6bd0` (damper)
  and `gp-0x6bbe` (boost) among them, cals `0xC63A0/A2/A4/A6/A8/AA` **all = 1024 = exactly 1.0**,
  byte-read — EMA-blended at `0xC63AC` = 102/1024, → `gp-0x6b70` → `FUN_00037fe6` (one of seven
  unity-weighted terms, cals `0xC64AD-0xC64B3` all = 1) → `gp-0x6ad6` → **`FUN_0003a382`** (the real
  PID) → `gp-0x6ad4` → `FUN_0003aa2c`'s aggregator → `gp-0x6b94` → governor → `gp-0x6b98`.
  ⇒ **So boost and damper DO re-enter a second, parallel aggregator at unity gain.** That structural
  fact is new. But **every weight in the whole chain is unity and stock — there is no hidden loop gain
  in the aggregation.**
  ★★ **And the chain's only output-shaping calibration is `0xC6AF0`** — `FUN_0003a382`'s authority
  ceiling, which **V56 already zeroed, flashed: NULL on the grinding, and it cost damping** (V57/V58
  both carry the assertion `"0xC6AF0 must stay STOCK -- V56's mute is falsified"`). Since `gp-0x6ad4`
  has only 2 accesses image-wide, that mute was equivalent to deleting this entire chain's
  contribution. ⇒ **a second independent reason not to hunt loop gain down this path.**
  ⚠ Genuinely untouched by any build (`grep`ed): `0xC63A0-0xC63AC`, `0xC64AD-0xC64B3`, `0xC6200`, and
  whatever produces `gp-0x67ab`/`gp-0x69aa`. Not proposed as levers — recorded as unexplored.
  ⚠ Open: `gp-0x67ab` / `gp-0x69aa` semantic identity (structural role only); `FUN_00026c80`, the
  11-channel mixer feeding them, only partially read.
- ★ **SECOND instance of the over-count scan trap, same session.** `search_instructions` reported
  **21 hits** for `gp-0x6b70`; **19 were false positives** — substring collision against
  `jarl 0x0006b700,lp`. A raw byte scan finds **exactly 2** (writer `0x382d2`, reader `0x38006`).
  Together with the `6bd0`/`0x00076bd0` collision this is now a **recurring** failure mode, not a
  one-off. **Always confirm a hit is a gp-relative operand, not an address literal.**
- ⚠ **The off-by-0x1000 tp trap recurred again** (a subagent computed `tp+0x73a8` as `0xC73A8`; it is
  `0xC63A8`). Self-caught. That is now **five** recorded occurrences.
- ★ **NEW SCAN TRAP — `search_instructions` can OVER-count too.** `operand_pattern="6bd0"` returned
  false positives from **substring collision against the branch-target literal `0x00076bd0`** in
  `FUN_0006bcb2`/`FUN_000757a2`. Every trap on record so far was about *undercounting*; this is the
  first over-count. **Confirm the hit is a gp-relative operand, not an address literal.**
- 🛑 **`0xC63BA` (=512) — PARTIAL ONLY.** Byte-verified 2-stage EMA, alpha 0.5 both stages, blast
  radius fully contained (2 reads, both in `FUN_0003b66a`). But it filters only the **torque** lane;
  the index is a **sum** of that and a **resolver-rate-derivative** lane (`gp-0x6abc`, via
  `FUN_00041464` ← `FUN_00068f52`'s angle-delta differentiator). Both analysts were right.
- 🛑 **Speed-keyed assist concentration — REFUTED.** `0xD2834` is nearly flat (rel 0.856 / 0.979 /
  0.987 / 0.997 / 0.903 at 0.5 / 3 / 6 / 10 / 18 m/s).

### Closed and corrected by this drive
- ✅ **The damping SIGN is no longer open.** `gp-0x6bd0` (`FUN_00034350`, sole producer, 3 writes) has
  its sign forced to `-sign(gp-0x6abe)` @`0x3469e-0x346a2` — textbook velocity-proportional damping,
  correct by construction. Joins the aggregator at `0x3ac78` in `FUN_0003aa2c`.
- ✅ **The frequency law is rejected a SECOND time.** Route 2c: `a = 0.177` rejected at **2.60σ**
  presence-tested (n=19, 9 runs), up to 7.08σ without. `a = 0` fits at every cut, ~20.4–21.1 Hz flat.
  Crucially the fitted subset is **confound-free** (`spearman(v,|ang|) = +0.068` vs 2b's −0.728).
  ⇒ **The fixed ~20.9 Hz line is now the record.**
- ✅ **V58/V59 control PASSES** — grinding statistically identical: 7 of 8 jointly speed-and-effort
  matched cells in 0.76–1.41× with no systematic direction, peak frequency within 0.7 Hz everywhere.
  Exactly what CAL-CRC-unchanged predicts; validates the comparison chain.
- ⚠ **CORRECTION to "creep-only":** that holds for the **hands-off** arm. There is a second
  population at **10–13 m/s under driver load** at large angle (prominence 174–651×), verified NOT a
  tyre order (frequency CV 2.2% vs order CV 9.8%; 3.89 is not an integer order). Correct wording:
  *strongest at creep 1–4 m/s; sampling gap at 6–10; still coherent at 10–13 under steering load;
  absent above 14 m/s* (0 of 48 windows pass presence).
- ⚠ **~21 Hz IS in openpilot's command**, confirmed again: native-`0xE4` prominence median 35× (max
  46×) hands-off, coherence **5/5 above the K-appropriate 95% null**. **Direction still NOT settled**
  — envelope cross-correlation splits 2 bar-leads / 3 command-leads, same as V58.
- ★ **Route 2c contains hands-off engaged creep RATCHET episodes** — 7.56 ± 0.36 Hz, within-run sd
  0.07–0.10 Hz, prominence median 783× (max 2142×), 15 windows / 5 runs, at both 9–15° and 133°.
  `STATE.md` previously recorded route 2b gave **zero** and that a dedicated route was required.
  Mode identity unconfirmed — the data exists, that is all.

### Open gates before V60
1. ✅✅ **RESOLVED 2026-07-31 — TASK 5 IS 100 Hz, and it invalidates the eps table above.**
   The rate divider is `FUN_00014be4`, a mod-100 counter (`gp-0x4304`) on the 1 kHz tick. Verified by
   the orchestrator: `tp-0x3814` = `0xBB7EC` byte-reads **`0x000BB920`**, and `idx*0x30 + 0xBB920`
   reproduces **all seven** TCB entry points exactly (`+0x08`), so the wake argument is a **0-based
   task-slot index**, not an abstract group ID:

   | idx | TCB entry `+0x08` | task | condition | **rate** |
   |---|---|---|---|---|
   | 0 | `0x0002214A` | task 1 — arb, `FUN_0003b66a`, aggregator, governor, shaper | every tick | **1000 Hz** |
   | 1 | `0x00022A88` | task 2 | `c & 1` | 500 Hz |
   | 3 | `0x00022B24` | task 4 | `c % 5 == 2` | 200 Hz |
   | **4** | **`0x00022CA0`** | **task 5 — boost `FUN_00034a72` + damping `FUN_00034350`** | `c % 10 == 4` | **100 Hz** |
   | 5 | `0x0002351E` | task 6 | `c == 0x10` | 10 Hz |

   ⇒ **The V59 eps table bracketed 1 kHz and 500 Hz. Both are wrong.** The boost-amplitude LERPs are
   evaluated at **100 Hz**, so a 42 Hz index modulation is sampled ~2.4×/cycle — barely above Nyquist
   and heavily ZOH-attenuated. **The pump could barely act at all**, which is an independent structural
   reason for V60's null on top of the empirical one.

   ★★ **THE BIGGER CONSEQUENCE — a 100 Hz damper cannot damp a 20.9 Hz mode.** `gp-0x6bd0` is
   velocity-proportional damping (sign forced to `-sign(gp-0x6abe)`), and damping only works when the
   force is in phase with velocity. A zero-order hold at 100 Hz costs `360 · 20.9 · T` of transport
   lag: **37.6° average (T/2), 75.2° worst case**, before any plant phase. ⇒ **a structural explanation
   for why EVERY damper lever was null (V44 FactorC, V47 FactorC+FactorE together) that does not depend
   on the FactorC speed-axis argument** — even with both deadzones fully open, the damper is too slow
   to act on this mode. It may even be anti-damping at 21 Hz.
   ⇒ 🛑 **Any fix acting through boost or damping is fighting 38–75° of architectural lag at the mode
   frequency. Prefer task 1 (1 kHz).** V61's edit is in `FUN_0003aa2c`, task 1 — on the right side of
   this. Any future task-5 change needs this in its GATE 2.
2. **`gp-0x6986` / `gp-0x6988` values unmeasured** — they scale the pump. Both are ≤1024 clamps so
   they can only pull eps *down*.

---

## On the car right now — **V67** (flashed, driven route `47--3e0b6134c0` 2026-08-02)

**V67 = V66 + the grind #1 fix gated on LKAS**: `0x3AA96` `c5`→`fb` (repoint the dead `gp-0x683c` gate to
`gp-0x6806`) + `0xC6446` 512→5244, both `sar` sites left **stock**. See THE HEADLINE at the top of this
file for the full route-47 result. Summary: **grind #1 fixed (0.55 [0.35, 0.65]), creep grind #2
ELIMINATED (0 bursts in 113 s vs 24 at Kd = 2×), the gate confirmed on-car, `gp-0x671d` never fired**,
and the new highway symptom shows **no rate-lane dose response**.
⇒ ★★★ **RECOMMENDED: LEAVE V67 ON THE CAR.** The next action is a **targeted drive**, not a build:
a parking-lot segment with LKAS engaged at creep (closes the 22 s exposure gap that leaves
"creep grind #2 under LKAS" formally unresolved at P(0) = 0.35), plus the highway maneuvers that provoke
the reported symptom.

---

## Previously on the car — **V65** (flashed, driven routes `3a--4e55c1e0f4` and `3b--a4a7f4dbf1` 2026-08-01)

**V65 = V62's control-path edits byte-identical + the 4-level saturation ladder on `gp-0x6b94`.** The
operator drove two routes on it: `3a` (short — parking lot, then **grind #2 demonstrated with LKAS ON**)
and `3b` (longer — parking lot, **grind #2 demonstrated with LKAS OFF**, then unrelated highway lateral
tuning). **Grind #1 stays fixed on V65** (18–22 Hz 0.555 [0.467, 0.685] vs Kd=1×, replicating V62), and
**grind #2 is confirmed and characterised** — see THE HEADLINE at the top of this file.
⇒ ★★★ **RECOMMENDED NEXT FLASH: V66** (see "Built and UNFLASHED"). It is what the operator asked for —
a stable long-drive build with stock base assist — and it is simultaneously the confirmatory revert and
the pre-flight probe for V67's gate.

---

## Previously on the car — **V62** (flashed 2026-07-31, driven route `37--6231e33f3d`)

**See THE HEADLINE at the top of this file for the full V62 result** — it is the current state and is not
repeated here. Summary: **the 20.9 Hz grinding is FIXED (8–42×)**, the route is flight-clean
(`ST==4` 0/86,278, zero-EME streak now >229,278 frames), **no regression is established**, and the
recommended next action is **another V62 drive, not a build**. V62 carries **V59's probe unchanged** —
🛑 `0x14A` byte4 = `0x87` therefore means *"boost index ≥ 2048"* (the **deepest** thermometer reading),
**not** V64's *"detector unarmed"*. Same byte, opposite meaning; it is 9.24% of route 37.

---

## Previously on the car — **V64**

## 🛑🛑 V64 FLASHED AND DRIVEN 2026-07-31 (route `35--77808fe7ce`) → **GRINDING UNFIXED, AND THE PROBE DIAGNOSED THE NULL**

Operator: *"I drove disengaged then engaged after. The vibration/grinding at low speeds is not fixed."*

**The probe answered its question and the answer was not the one the build was hoping for.**
`0x14A` byte4 = **constant `0x87`, zero variance across 14,980 frames / 149.8 s**:

| bit | meaning | frames set |
|---|---|---|
| 7 | liveness | **14,980 / 14,980** — the cave ran, every tick |
| 6 | `gp-0x671a >= 5` — **V63/V64's raised arm selected** | **0** |
| 5 | `gp-0x671a != 0` — counter incremented at all | **0** |
| 4 | `gp-0x67df != 0` — FSM left neutral | **0** |
| 3 | `gp-0x671d != 0` — r24 override | **0** |

⇒ `|gp-0x6c2c|` **never crossed `T` = `0xC620A` = 12800**, the reversal counter never incremented once,
and **V64's two cal edits were never in force.** ⇒ **A null on the GATE, not on the damping hypothesis.**
🛑 **Do not record V64 as evidence against raising the rate lane.** It is not.

**Confirmed four ways:** raw byte histogram · `rlog-tools/decode_v64_detector.py` (run by the
orchestrator) · an independent raw-CAN rederivation · **V59's probe ruled out** (its bit5 was set
essentially always; here 0/14,981, and other routes show byte4 genuinely varying `0xBF/0x8F/0x9F/0x87`).

**Spectra confirm it independently — the car behaved exactly like V59:**

| build | n runs | peak | prominence | abs power |
|---|---|---|---|---|
| V59 route `2c` | 9 | 21.18 Hz | 227× | 5.26e8 |
| V61 route `31` | 3 | **18.25 Hz** | 486× | **4.15e9** |
| **V64 route `35`** | 2 | **21.30 Hz** | 149× | 4.31e8 |

Best-populated speed bin (2–3 m/s): **V59 20.98 Hz / env99 1811 vs V64 20.99 Hz / env99 1804** — three
significant figures on both. V61's manual/reverse spread is **gone**. FLIGHT-CLEAN: `ST==4` **0**, all six
watched events 0, `0x14A`/`0x18F` at 100.03 Hz. Route is 100% creep (vEgo max 4.58 m/s), 1,958 reverse
frames, log starts 43 s **before** first engagement.

### ✅ The build was aimed CORRECTLY — the V63 polarity dispute is closed
`0x3AA7C cmp r14,r12 / bc` sets **`r2 = 1` iff `gp-0x671a >= CEIL`**, and both `ld.hu 0x743e[tp]`
@`0x3AB68` and `ld.hu 0x7440[tp]` @`0x3AC12` are taken iff `r2 != 0`. ⚠ The golden model's
`selected_state_value` is **`r22`** (cals `0xC6138`=1 / `0xC6136`=0), a **different register** from the arm
selector `r2` — both model readings were right, describing different variables. The "dispute" dissolves.
⚠ **bit3 = 0% ⇒ r24 WAS covered**; the `gp-0x671d` override was idle throughout.

### ✅ The detector genuinely RAN — the `FUN_00046ea6(5)` gate is closed
`FUN_000428d4`'s entire body is gated on `FUN_00046ea6(5) == 0` (bit 5 of `gp-0x18d0 | gp-0x18d4`), and if
that bit were set the cells would simply never be written — **indistinguishable from "T never crossed"**.
Closed by raw byte scan of **all 47 `jarl` sites** (Ghidra found 44 — the documented undercount; the
conclusion survived the *more* complete method): **bit 5 has exactly ONE caller image-wide, the detector
itself** (`0x428DA`). The only dynamic indices are cal bytes `0xB9A14-16` = **0, 2, 6**. The mask is
DTC-driven (`tp-0x72c4` table, stride 28, u32 at +8) and **self-clearing** — `gp-0x18d4` is rebuilt by
plain assignment on each active-fault sweep. ⚠ Residual: 6 of 47 sites set `r6` further back than a
5-halfword window; all sit in clusters whose other members resolve to 0 or 7.

### 🛑 AND EVEN IF THE GATE HAD OPENED, V64 DELIVERS LITTLE — byte-read defaults
At the hands-off-creep LERP axis (X = 0):

| lane | default arm (state<5) | osc arm (state>=5) stock | V64's arm | delivered vs default |
|---|---|---|---|---|
| r24 | **2305** (`0xD2AEC`) | 2048 | 4096 | ×1.78 |
| r26 | **3072** (`gain_A` rec0/rec1) | 1536 | 3072 | **×1.00 — a no-op** |

⇒ **Honda's oscillation arms are gain REDUCTIONS, not boosts.** V63/V64 largely *cancel Honda's own
de-escalation* rather than adding damping. V62's `sar` edit gives a clean **×2 on both lanes under every
arm and every mode**.

---

## Previously on the car — **V61**

## ★★★ V61 FLASHED AND DRIVEN 2026-07-31 → **WORSE. And that is the best result this kit has had.**

**The first SIGNED on-car outcome on any vibration lever.** Every prior build was a null or a fault.
V61 made the symptom *worse*, which is strictly more informative — it measures the **gradient**, and the
gradient says every previous attempt on this lane was pushing the wrong way.

**What V61 did:** zeroed the torsion-bar torque-RATE lane at **both** taps of its shared
`r1 = clamp(gp-0x4f62, ±5120)` (`0x3AB6C mul r1,r6,r0 → mul r0,r6,r0`; `0x3AC16 mov r1,r8 → mov r0,r8`).
Two single-bit reg1 changes, no cave, no calibration moved.

**Operator, authoritative:**
- **LKAS ON, forward** — grinding still present and **significantly worse**: higher amplitude, louder.
- **LKAS OFF, forward** — grinding **newly present** in manual driving when turning.
- **LKAS OFF, reverse** — grinding **definitely newly present** in manual driving.

### ⇒ The rate lane is the mode's DAMPER, not its amplifier
Sign verified by the orchestrator from image bytes, not relayed:
- `gp-0x6752` (polarity) is **one load @`0x3AB78` reused unmodified by both lanes**, and the *same byte*
  is read by `FUN_0003a382`'s resonance lane @`0x3A71A` — the aggregator's one genuinely
  torque-**proportional** P-term. ⇒ **polarity CANCELS**; its value is not needed to answer the question.
- The combine chain `0x3ACC8`–`0x3ACDA` is **ten instructions, every lane entering with `add`**, each
  add's `reg1` threading the previous add's `reg2`. **Not one `sub`.**
- ⇒ `r24, r26 = +Kd·d(T_bar)/dt` **in phase with assist** — `Kp·x + Kd·dx/dt`, a lead compensator.

For the hands-off mode (steering-wheel inertia on the torsion bar), with motor torque on the column only:
```
phi'' + (Kd·k/J_c)·phi' + k·(1/J_w + (1+K)/J_c)·phi = T_road/J_c
```
The `phi'` coefficient is **`Kd·k/J_c > 0` — positive damping, LINEAR in Kd. At `Kd = 0` the mode has no
damping term at all.** That is V61, and that is what the car did — including in **manual** driving, where
base assist is the only loop running, and worst in **reverse**.

🛑 **A derivative term is DC-neutral** (zero at constant torque), so V61 cannot have "removed assist" — it
changed **only** dynamics. That is what makes this a clean signed measurement rather than a confound.

🛑 **This falsifies the golden model's framing.** `eps_lkas_chain_model.py:1792` called r26
*"excitation-to-amplifier: faster slew → bigger derivative → bigger r26 → more motor torque → repeat"* and
recommended the r26 kill. Both passages are **struck and corrected in place**. ⇒ **V39 (r24), V42 (r26)
and V61 (both) all tested this lane DOWNWARD.** Their results stand; they bracket the **wrong side**.

★ **Why this lane and not the dampers already tried:** `FUN_0003aa2c` is **task 1, 1000 Hz** ⇒ ~3.8° of
ZOH lag at 20.9 Hz. Boost/damping are **task 5, 100 Hz** ⇒ **37.6–75.2°** — the structural reason V44 and
V47 were null. **The rate lane is the only damping mechanism in the chain fast enough to act on this mode.**

### ✅ The rlog CONFIRMS all three of the operator's observations — and the mode MOVED

Route `00000031--0441e00d2b`, 4 segments, **22,052 frames / 222 s**, parking lot (v max 1.5–5.4 m/s),
segs 0/3 manual, segs 1/2 engaged (latActive 47.2% / 18.1%). **FLIGHT-CLEAN:** `STEER_STATUS` = 0 in
22,042/22,052, `ST==3` in 10 frames, **`ST==4`: 0** (the clean streak extends past 143,000 frames).
Zero `steerUnavailable` / `steerTempUnavailable` / `canError` / `immediateDisable` / `steerSaturated`;
one `controlsMismatch`. **2,851 frames ≈ 28 s of reverse** — a real analysable population.

🛑🛑 **THE MODE MOVED DOWN 3 Hz AND GOT 7.9× LOUDER.** Engaged creep, v ≤ 5.35 m/s, *identical method,
speed-matched, same channel*, V59's route `2c` as the control (`analyze_r31_manual_vs_engaged.py`):

| build | n runs | peak | prominence | abs power |
|---|---|---|---|---|
| **V59** route `2c` | 9 | **21.18 Hz** | 227× | 5.26e8 |
| **V61** route `31` | 3 | **18.25 Hz** | 486× | **4.15e9** |

⇒ **−2.93 Hz and ×7.9 power.** ★★ **The frequency shift is the decisive observable, and it is
structural: a pure GAIN change cannot move a resonance frequency — a PHASE change can.** Removing a lead
compensator lowers the frequency at which the loop phase reaches −180°, so the limit cycle drops. Both
observables agree, and the direction was predicted *before* the data was looked at.

**The three conditions, route 31, ordered exactly as the operator reported them:**

| condition | n | peak | prominence | abs power |
|---|---|---|---|---|
| **ENGAGED** creep | 3 | 18.25 Hz | 486× | **4.15e9** |
| **MANUAL reverse** | 2 | **17.82 Hz** | **1910×** | 5.78e8 |
| **MANUAL forward** | 5 | 18.54 Hz | **13.1×** | 3.82e6 |

⇒ **Manual reverse carries 151× the power of manual forward, at the same frequency as the engaged line.**
That is the *same mode*, unmasked by the loss of damping — not a new one.

🛑 **REFINEMENT — "manual forward is a floor" is WRONG, and the error is instructive.** The 13.1× above
is an **un-gated average** over all manual-forward driving, so it is diluted by ordinary quiet cruising.
Gated on **sustained effort ≥ 1000** it is **146×** (n=2 windows, f0 18.40 Hz) — the phenomenon *is*
present in manual forward, but **only while the driver is actually loading the wheel**, which is exactly
what the operator said (*"in some scenarios"*). A second analyst reached the same place from the other
side: the loudest manual windows are at **|v| = 0.00–0.6 m/s with the wheel cranked** (effort 2200–3300),
and a `|v| ≥ 0.3 m/s` "moving" gate **drops them entirely**, taking that arm from *"median prominence
5.3×, mostly floor"* to *"median 317×, envelope p99 median 2495"*, f0 **17.08 Hz, sd 0.76, n=7**.
⇒ **Two different gates each hid the same population.** Manual/reverse sits at **17.0–17.8 Hz**, about
0.5–1.3 Hz *below* the engaged 18.3 Hz — same mode family, frequency shifting with loading.
⇒ ★ **Adopt a near-stationary, high-effort manual arm as a standing convention.** That is where manual
EPS instability lives, and both a speed gate and a missing effort gate erase it.

★ **The ratchet stayed LKAS-gated while the grinding did not.** Engaged: 10 of 14 windows reach 10×
prominence at 6.56 Hz. Manual: **0 of 28**. Reverse: **0 of 10**. ⇒ under V61 the two symptoms
**separated further** — the grinding escaped into base assist, the ratchet did not. That is independent
support for them being different phenomena, and it is also the third exclusion of the
ratchet-2nd-harmonic reading (a harmonic cannot live where its fundamental fails a presence test; and
2 × 6.56 = 13.1 Hz, not 17.8).

⚠ **Caveats, stated:** n is small (3 engaged / 2 reverse runs) and this is one route against one control
route. The effect sizes (7.9×, 151×, −2.93 Hz) are far larger than that weakness, but a repeat on V62 is
what confirms them.

⚠ **A methodology trap caught in-flight and worth recording:** the first pass pre-restricted the search to
the strict 18–26 Hz band and the argmax **pinned to the band edge at 18.04 Hz with sd 0.00** — a
truncation artifact, because the mode had moved *below* the band. **The strict band is for
presence-testing a mode whose frequency you already know, not for locating one that has shifted.** Locate
over 12–30 Hz, then interpret. (The ratchet-2nd-harmonic trap is separately excluded here: in manual
reverse the 6–10 Hz fundamental is only 9.6× while the 17.8 Hz line is ~1900× — a "harmonic" 200× stronger
than its own fundamental is not a harmonic.)

---

## 🛑 V60 FLASHED AND DRIVEN 2026-07-31 → **NULL. The parametric pump is CLOSED.**

Operator: *"I drove on the V60 RWD. It did not fix the vibration issue."* **No rlogs** — V60 carries
V59's probe unchanged, so there was no new telemetry to upload.

**This null is a result, not a wasted drive.** V60 was built as a **discriminator** and the record
predicted the outcome: *"Expect it to be NULL… a null closes the parametric mechanism and leaves the
loop standing."* Pump causality was not settleable observationally (the index is `|x|` of a bar-derived
signal, so 2f coupling is arithmetically forced) and `eps_crit = 2/Q` needed a passive Q that V59 could
not measure. Only an intervention could separate drive from echo. It did.
⇒ **V58/V59/V60's whole arc closes. The 42.19 Hz index modulation is real, engagement-gated, and is NOT
the driver of the grinding.**

★ **Consequence — `0xC63BA` is pre-falsified by the same null and must NOT be proposed as a fix.** It
looked ideal (cal-only, 512 = 2-stage EMA α = 0.5 ≈ −0.30 dB at 21 Hz, exactly 2 readers at `0x3B7BA`/
`0x3B7D4`, never edited, explicitly reserved by `build_v59_tva.py:444` as *"a V60 candidate"*). But a
byte scan of its consumers closes it: readers of `gp-0x6b9a` (8) and `gp-0x6ba6` (7) are confined to
`FUN_00034350` (damping), `FUN_00034a72` (boost), their producer, and V59's probe cave — so the index
drives **only** the boost/damping amplitude LERPs, i.e. the mechanism V60 just falsified. Proposing it
would repeat the V44/FactorC pattern exactly.

⚠ **Two more lanes removed from the search, byte-verified:** `FUN_00036c12` (`gp-0x6b26`) and
`FUN_00036388` (`gp-0x6b62`, the return-centre lane that was the operator's own hypothesis) read **no
torque signal at all** — speed- and motor-rate-keyed only.

**V58** = V57's calibration + the angle-rate/boost-lane probe in the cave. Flashed and driven 2026-07-30,
route `2b` (normal commute, 14 segments, ~14 min, 83,959 frames, creep → highway → parking).

```
0xC646C  shared sensor scale = 891 (stock)     <- was 3564 on V38..V56
0xC6CD0  private LKAS forward gain = 3564      <- V57's new cell
0xC62EA  low-speed lockout = 0                 <- V53, unchanged
0xC64DE  re-engage ramp = 27                   <- V18, carried forward correctly
_v58_plain_image.bin  SHA 431117459a42dc2e7906446261c7175bf2d0cc35b88290f2fdeb9b779d654c48
V58 .rwd              SHA 7b3cfff05116a22137c1376b78e69d955ac75397b8091e089da4b0379a5948f7
```

**V58 is FLIGHT-CLEAN.** `steerUnavailable`/`steerTempUnavailable`/`canError`/`controlsMismatch`/
`immediateDisable`: **0 across all 14 segments** (raw `onroadEvents` scan, verified twice). The only
flags are `commIssue`×2 + `selfdrivedLagging`×1, all at seg 0 t≈8.5 s **in `wrongGear` before the drive
started** — a boot transient, unlike route 28's real mid-drive soft-disable. `STEER_STATUS == 0` in
**83,959/83,959** frames; **`ST==4`: 0**, extending V57's 0/37,922 to 121,881 combined clean frames.
Probe low bits `& 0x07 == 0b111`, zero exceptions. `0x14A`/`0x18F` at 100.00 Hz in every driving segment.

**V58's on-car result — see the handoff for the full numbers:**
- ★★ **The collinearity confound is BROKEN.** Seg 13 gives 60 s of *moving but disengaged* at
  0.5–4.8 m/s. Speed-matched grinding: **13.4×** [95% 3.9–19.8], **16.9×** speed+effort-matched, and
  **184×** on time-occupancy at matched creep. Better than any ratio — **the resonance is ABSENT
  disengaged**: prominence median 122.7× vs 3.6×, with the disengaged "peak" wandering 15–29.9 Hz
  (sd 2.49 Hz) i.e. the argmax of a floor. Confounds run *against* the engaged arm (disengaged has
  |ang| 167° vs 9°, effort 1638 vs 205). ⇒ **the grinding requires applied LKAS torque. Settled.**
- ✅ **bit5 = 0 in all 35,964 frames ⇒ the ceiling `0xD20C0` is ELIMINATED.** The lane never pins, so
  `K1` @`0xD200C` = 43 keeps its headroom.
- 🛑 **bit6 VOID BY CONSTRUCTION.** `gp-0x6bbe` crosses zero 0.00–1.10 /s where 22 Hz needs ~44/s; it is
  DC-dominated. **The damping sign is STILL OPEN.** ⚠ Pooling runs to force an answer manufactures a
  splice artifact (bit6 has 5/0/0/1 transitions *within* the four engaged runs, so a concatenated
  "coherence 0.5 at 25 Hz" is step discontinuities at the joins). **A sign comparator is a phase probe
  only for a signal that crosses zero at the frequency of interest.**
- ★★ **bit4 FIRED and is the lead.** `sign(gp-0x6b9a)` at 20.93 Hz, per-run coherence
  0.649/0.970/0.769/0.881, own-spectrum peak 10.8× median, `corr(envelope, toggle rate) = +0.834`.
  At matched creep: **13.69 toggles/s engaged vs 0.61 disengaged**, 20.93 Hz line present in one arm and
  absent in the other, duty cycle barely moving ⇒ it *oscillates*, it does not merely sit elsewhere.

🛑 **Hands-off could not be conditioned on anywhere on this route** — zero fully-hands-off windows in
either arm in any qualifying speed bin. Everything above is "any hands", matched on effort instead.

## 🛑🛑 CORRECTION — `gp-0x671a` IS A ONE-WAY LATCH, so V63/V64's decoupling is NARROWER than first stated

An earlier pass this session told the operator V63 had **"zero manual-feel cost by construction"**. **That was too strong and is withdrawn.** `FUN_000428d4`'s output stage (`0x429A0`–`0x42A12`, orchestrator-verified, cals byte-read) holds the counter:
```
0x429A8  cmp r15,r12 / bh   ; cal 0xC62DE = 640 > voted DRIVER TORQUE gp-0x6a5e -> RELOAD hold timer
0x429AC  cmp r0,r14  / bne  ; revcount != 0                                     -> RELOAD hold timer
0x429CA  reload = cal 0xC6270 = 5000 ticks = 5.0 s @ 1 kHz
0x429EA  once held >= CEIL, the output is RE-PINNED TO CEIL every tick
```
The only way down is **5000 consecutive ticks with driver torque ≥ 640 AND no reversals** — and driver torque dips below 640 on every direction change, so the timer reloads constantly.
⇒ **Accurate claim: a drive that never oscillates never sees the raised gain** (a real scope reduction against V62's always-on doubling) — **but once a single 5-reversal burst occurs, the raised gain latches on and carries into subsequent manual steering.** V63/V64 is *"V62, but only after an oscillation has happened"*.
✅ **And the latch is PROTECTIVE.** A gain switching per-tick with the reversals would modulate **at the mode frequency** — a parametric pump, the exact failure mode V58/V59/V60 spent three builds chasing. Honda's hold prevents that; a per-tick-gated damper would be actively dangerous.
⚠ Cell correction: the per-tick zeroing at `0x42906` is on **`gp-0x357c`** (raw count), not `gp-0x671a`.

## Built and UNFLASHED

| build | what | status |
|---|---|---|
| ★★★★ **V67** | **V66 + the grind #1 fix, GATED ON LKAS** — `0x3AA96` `c5`→`fb` + `0xC6446` 512→5244, both `sar` sites STOCK | ✅ **BUILT 2026-08-01, UNFLASHED. ★★★★ THE OPERATOR'S CHOICE FOR THE LONG DRIVE.** ★★★★ **THE FIX, AND THE OPERATOR'S CHOICE FOR THE LONG DRIVE.** V66's calibration and reverts, plus the grind #1 fix made conditional on LKAS. **LKAS off is byte-for-byte STOCK base steering; LKAS on gets 2.00× at grind #1's operating point** (creep 7.2 km/h, 128 deg/s, LERP 2622 ⇒ arm 5244). ✅✅ **THE GATE IS VALIDATED ON-CAR BEFORE THE FLASH** — V57's own probe put `(gp-0x6806 == 0)` on `0x14A` byte4 bit6 and flew routes `28`/`29` in July, and nobody had correlated it: **99.90% / 99.94% agreement with `carControl.latActive`** over **37,914 frames** at two very different duty cycles (21.73% / 49.88%), with **0.0505 / 0.0300 transitions per second**. ⇒ `gp-0x6806 != 0` **is** "LKAS is applying"; it does **NOT** drop out during steady engaged holding (the one ambiguity static analysis could not close — it is a ramp-FSM phase flag whose "settled" phases 5/6/7 could not be ruled out); and it toggles **three orders of magnitude** below the 21/45 Hz modes, so the parametric-pump criterion passes with enormous margin. Reproduce with `analysis-2020accord/validate_gp6806_gate.py`. ⭐ **Orchestrator-verified independently from the built image.** **15 bytes off V66**, restricted to `[0x13000,0x100000)`: `0x3AA96` (1), cave `0xC4B46`/`0xC4B52`/`0xC4B54`/`0xC4B56` (4), MAIN CRC (4), `0xC6446` (2), CAL CRC (4). The repoint leaves **hw1 untouched** and the result `84 7f fb 97` differs from the real `ld.bu -0x6806[gp],r12` = `84 67 fb 97` @`0x02A1B6` **only in the reg2 field**. `0xC6444` (r26's arm on the same gate) stays **stock 512** — r26 is inert. Both `sar` sites confirmed **stock `0xa`**, `0x3AB70` untouched, `0xD2000` block and **all four** mode-10 `gain_B` records byte-identical to V66. 50/50 CRC; x31 checksum PASS; **the RWD decodes exactly back to the image**. GATE 1 **vacuous** — the repoint is a read-only load displacement claiming no RAM, and the cave's sole store is the existing CAN-330 payload byte with bits 2:0 preserved. GATE 2 is **measured, not argued**: the lane is a **derivative ⇒ DC-neutral**, so a gain step at engagement is not a torque step, and the gate's toggle rate is the table above. Arithmetic `5120 × 5244 = 26.8 M` = **1.25% of INT32_MAX**; the lane saturates at |dtorque| ≥ 1599 against a measured 123–839. **Probe** (`0x14A` byte4): **bit7** liveness · **bit6** `gp-0x6806 != 0` (**the gate** — low duty while engaged ⇒ wrong cell and V67 is inert) · **bit5** `gp-0x671d != 0` (**the masking risk** — it OUTRANKS the arm and pins the gain to `0xC6442` = 1024, *below* stock, so if it fires V67 is worse than V66) · **bit4** `gp-0x671a >= 5` (the third arm). Cave re-decoded from the built image; the odd displacement `-0x671d` (bit 0 in **hw1 bit 5**) and the even `-0x671a` / `-0x6806` all encoded correctly. ⚠ bit4 **hardcodes 5** rather than reading cal `0xC64FA`; the cal is 5 and V67 does not move it, but a future change to `0xC64FA` would silently desync the probe from the firmware. 🛑 **GRIND #2 SURVIVES UNDER LKAS**, at **2.21×** — slightly above V62's 2.00×, because a scalar arm does not follow the LERP's own rolloff. That is the stated cost of an LKAS gate: measured gating is **98.7%** engaged for grind #1 but **84.3%** for grind #2 against a **54.7%** base rate. `0xC6446` is one halfword and is the knob for that trade. 🛑 **Do not read a V67 null without decoding the probe first** — that is the V64 lesson. Decoder `rlog-tools/decode_v67_gate.py`. Image SHA `5e01bcc4b34a52831fd524cb9af765a01a8dfa3e2c4782d81b3efcb6c94f8c96`; RWD SHA `33457613ea8635686baf94833e75688fe200c616d76cb4b38b3152d4a47a1caf` |
| ★★★★ **V66** | **V65 with BOTH `sar` immediates reverted to stock + a 3-bit GATE PROBE** — the operator's requested stable long-drive build, and the confirmatory revert | ✅ **BUILT 2026-08-01, UNFLASHED. ★ THE RECOMMENDED NEXT FLASH.** Restores **exactly stock** base assist (grind #1 returns as V38 has it; grind #2's cause is removed), carries V57's `0xC646C` decoupling + `0xC6CD0` = 3564 + `0xC62EA` = 0 + `0xC64DE` = 27 unchanged. Probe on `0x14A` byte4: **bit7** liveness · **bit6** `gp-0x6806 != 0` · **bit5** `gp-0x67f5 != 0` (**its toggle rate is V67's kill criterion**) · **bit4** `gp-0x67fe != 0` (**gate candidate C — one bit settles whether it is an LKAS flag or base assist**). **61 bytes off V65** (2 code + 52 cave + MAIN CRC); ⭐ **CAL block byte-identical to V65**, `0xD2000` block identical, all four mode-10 `gain_B` records unchanged = machine proof no calibration moved; `0x3AB70` still `sar 0xa`; **`gp-0x683c`'s load at `0x3AA94` UNCHANGED**. Same base/hook/68-byte extent as six clean flights; **62/68 used**. GATE 1 vacuous. 50/50 CRC; x31 PASS; RWD decodes exactly back to the image; ⭐ orchestrator-verified from the built image with the cave re-decoded from the bytes. 🛑 **Only three probe bits fit**, so `gp-0x671d` and `gp-0x67fe` are unmeasured. **Route:** ordinary long driving plus deliberate parking-lot creep, **and specifically reproduce grind #2** — creep with heavy manual steering, |angle| ≥ 100°, both engaged and disengaged. **Log from before the first engagement.** Decoder `rlog-tools/decode_v66_gateprobe.py`. Image SHA `0d4a0a5361e8ba91b1a24ad3298dd617ad541903070b02a58b9ae6df6709f246`; RWD SHA `41a4476ae9fb29fd2afd1b41238bf19b409b256abb8adfa3a8fb7b5569548fa9` |
| ~~**V64**~~ | V63's two cal edits + the probe repointed at the oscillation detector | 🛑 **FLASHED 2026-07-31 → GRINDING UNFIXED, DETECTOR NEVER ARMED. Do not re-flash for the damping.** See "On the car right now" above. The probe did its job — it converted an uninterpretable null into a diagnosed one. Original build note kept below for provenance. ✅ **BUILT 2026-07-31.** Operator's proposal, and it removes V63's fatal weakness: V63's probe still measured `gp-0x6ba6`, the parametric-pump index **V60 already falsified**, so a V63 null would have been uninterpretable. V64 keeps the cal edits byte-identical (**CAL block byte-identical to V63, machine-verified**) and repoints the cave: `0x14A` byte4 **bit7** liveness · **bit6** `gp-0x671a >= 5` (the arm is selected) · **bit5** `gp-0x671a != 0` · **bit4** `gp-0x67df != 0` (FSM left neutral ⇒ `\|gp-0x6c2c\|` crossed ±12800) · **bit3** `gp-0x671d != 0` (r24's override active). **Actionable in every failure mode:** bit6 never set + bit4 set ⇒ lower `CEIL` (`0xC64FA`); bit4 clear ⇒ lower `T` (`0xC620A`); bit6 live but no improvement ⇒ the rise was too small; bit3 set ⇒ also raise `0xC6442`. **60 bytes off V59** (50 cave + 2 cal + 8 CRC), **54 off V63 (cave + MAIN CRC only)**, 90 off V38. Same base `0xC4B34`, same hook `0x55C0E`, **same 68-byte extent** as V55/V57/V58/V59 — all four flown clean; **68/68 used, zero budget left.** GATE 1 vacuous (read-only; sole write is the existing CAN payload byte, bits 2:0 preserved). 50/50 CRC; RWD round-trips; cave re-decoded from the readback. ⭐ **Orchestrator-verified independently from the built image:** all three cave loads decode to `gp-0x671a`/`gp-0x67df`/`gp-0x671d` (V850 `ld.bu` carries displacement bit 0 in **hw1 bit 5**, not hw2 — a naive decode reports false mismatches), the `gp-0x671d` halfword is **byte-identical to the real firmware instance** @`0x3AB98`, and the only store is the CAN byte. Decoder `rlog-tools/decode_v64_detector.py` leads with **time-to-first-set** and **whether it ever clears** (see the latch note — occupancy saturates once set). 🛑 **Start the log BEFORE the first engagement**, or time-to-first-set is unmeasurable. Image SHA `e9dcd3b619cb35a4405861331a20807c4d0d2df074b6119a6690df728c68511e`; RWD SHA `7abbeba61ccc22852506e8747cedd12236210e93c23f8a13ad586e19914f0830` |
| ★★ **V63** | V59 + raise **only the OSCILLATION-DETECTED gain arms** of both rate lanes | ✅ **BUILT 2026-07-31, UNFLASHED — superseded by V64, which is the same cal edit plus instrumentation.** `0xC6440` 2048→4096 (r24) and `0xC643E` 1536→3072 (r26). **6 bytes off V59** (2 cal bytes + CAL CRC), 88 off V38. ⭐ **MAIN CRC UNCHANGED** = machine proof no code byte moved. V62's `sar` shifts and V61's tap kill both **asserted absent** ⇒ independent experiment, not layered. 50/50 CRC, RWD round-trips, re-verified from the built image. **Built in response to the operator's objection that V62 changes manual feel to fix an LKAS-specific symptom** — and the firmware turns out to already discriminate: both lanes' gain chains end in `assist_state gp-0x671a >= 5`, and `gp-0x671a` is a **HARD-REVERSAL COUNTER** (`FUN_000428d4`: neutral state resets it to 0 **every tick** and only exits if `\|gp-0x6c2c\| > 12800`; a reversal increments; 50 quiet ticks clear it). ⇒ it reads **0 during smooth steering** and `state>=5` means **an oscillation is happening**. Raising only those arms adds damping **only while oscillating**; both smooth-steering LERP defaults stay stock ⇒ **zero manual-feel cost by construction, and a smaller edit than V62.** ✅ **No new arithmetic risk: 3072 is already gain_A's own stock maximum**, so worst-case `stage1×gain` stays at 47% of INT32_MAX, unchanged. GATE 1 vacuous. 🛑 **Residual 1 — a NULL IS AMBIGUOUS:** whether `gp-0x6c2c` actually crosses ±12800 during the vibration is **unverified and load-bearing**; if it does not, V63 is inert. **Resolve with no probe and no cave: fly V63 first, and if null fly V62, which cannot miss.** 🛑 **Residual 2:** `gate_671d` outranks r24's arm and is live, so **expect r26 to carry this build**; r26's chain is clean (`gate_683c` dead). Image SHA `2f843bce8ff6fcab72cd3fafddcbdea926b40701e1425cabad03791f1a09019c`; RWD SHA `5e5f83d7cd9281000dcfa602a6e70b252037ad782728502d82e82d42c72b9abc` |
| ★★★ **V62** | V59 + **DOUBLE the torsion-bar RATE lane** — `sar 0xa` → `sar 0x9` on each lane's final shift | ✅ **BUILT 2026-07-31, UNFLASHED. ★★★ THE RECOMMENDED NEXT FLASH — promoted from fallback after V64's gate null.** It carries **no detector anywhere in its path**, so it is immune to the ambiguity that made V63/V64 inert. ⭐ **Re-verified from the built image 2026-07-31**: exactly 6 bytes vs V59 — `0x3AB76` `aa`→`a9`, `0x3AC20` `aa`→`a9`, MAIN CRC at `0xC4FFC`; `0x3AB70` correctly still `sar 0xa`; `0xC6440`/`0xC643E`/`0xC6442` confirmed stock. ✅ Lane clamps re-confirmed **±8192 each** (`0x3AB82`/`0x3AC42`), aggregate **±10240** ⇒ cannot produce an unbounded command. ⚠ **Pre-committed caveat:** r24 saturates once the input derivative exceeds `8192·1024/gain` — 3639 (71% of the ±5120 ceiling) at the stock 2305 default, **1820 (36%) under V62**; above that both clamp identically, so expect a **partial** improvement, not elimination. The benefit is that hitting the damping ceiling earlier in each cycle removes more energy per cycle from a limit cycle. **The matched inverse of V61.** `0x3AC20 42AA→42A9` (r24) and `0x3AB76 32AA→32A9` (r26). V61 took `Kd`→0 and the mode diverged; V62 takes `Kd`→2×, the same-sized step back. Stock sustains with **no ring-down at all** ⇒ `zeta_net ≈ 0`, so doubling should move it to `+zeta_lead`. **6 bytes off V59** (2 immediate bytes + MAIN CRC), 8 off V61, 88 off V38. ⭐ **CAL CRC unchanged** and ⭐ **`0xD2000`-block CRC unchanged** = machine proof no calibration moved and V60's falsified blend is absent. 50/50 CRC, RWD round-trips with every gate re-run on the readback; re-verified independently from the built image (taps back at `r1`, both shifts `sar 0x9`, `0x3AB70` still `sar 0xa`, exactly 2 code bytes). 🛑 **`sar` immediates chosen OVER the gain cals**, three traced reasons: the live gain arm is a **priority chain** that cannot be pinned statically (`gp-0x671a` is a bounded [0,5] *persistence ramp* that plausibly never saturates during a 21 Hz oscillation); **r24's default arm is MODE-INDEXED** via `gp+0x63fd` through four pointer arrays (`0xD2AEC`←`0xCC154` idx 10, `0xD6AEC`←`0xCC184` **idx 22** — ⚠ **a different MODE, not a redundancy twin; the "V27 desync" reading was wrong**); and `gp-0x683c` has **zero writers** ⇒ `0xC6446`/`0xC6444` are dead arms. A `sar` edit doubles the lane **under every arm and every mode**. 🛑 **`0x3AB76` not `0x3AB70`** — V850 `mul` discards the high word into `r0`, and doubling before the `×gain_A` multiply pushes the worst case to **94% of INT32_MAX** vs 47% (unchanged) after it. **Headroom is arm-dependent**: ~22× / ~11× / **~7.3× worst case**, so doubling keeps ≥3.6× margin. GATE 1 **vacuous** (no cave, no RAM, no new opcode). ⚠ **Residual:** `avg(gp-0x69a4)` magnitude is still unmeasured after three sessions — if r26 were already pinned at ±8192 doubling would deepen a saturation; bounded against by the fact that such a lane would dominate the ±10240 sum clamp and V61 would have been far more dramatic. r24 is immune. ⚠ Manual feel **will** change. Reversible by reflashing V59 or V61. Image SHA `80d9e1f721b741722a9d4b141a2d328fe8d999705765fedffab1ad23aa9264c7`; RWD SHA `1e0806a1eac69688e6d636fa02c5b1e864da40a65a4d3f8137d444d1ec5bff8e` |
| ~~V61~~ | V59 + **kill the torsion-bar RATE lane at BOTH taps of its shared value** | ★★★ **FLASHED 2026-07-31 → WORSE. Do not re-flash except as a deliberate revert.** The signed result that inverted the record — see the section above. Original build note kept below for provenance. **The one decisive subtractive test never performed.** r24 and r26 are **not independent** — both are gain-scalings of ONE value, `r1 = clamp(gp-0x4f62, ±5120)`, produced at `0x3AAAC-0x3AAC0` and tapped twice: `0x3AB6C mul r1,r6,r0` (r26) and `0x3AC16 mov r1,r8` (r24). **V39 killed only r24 — and only *conditionally*** (cave at `0x3AC78`, bypasses unless driver max torque < 320 AND \|LKAS\| ≥ 417); **V42 killed only r26** and says so outright (*"WHY r26 AND NOT r24: r24 was already zeroed by V39"*). Same sign, shared polarity load @`0x3AB78` ⇒ **killing either alone leaves the other transmitting, so each null is uninformative about the lane.** ⭐ **THE EDIT IS TWO SINGLE-BIT REGISTER-FIELD CHANGES** — `0x37E1→0x37E0` and `0x4001→0x4000`, both `reg1: r1→r0`, opcode and reg2 byte-identical (verified programmatically on the built image). **No cave** ⇒ GATE 1 vacuous, and the kit's only bricking class is avoided. r24's tail traced to zero: `mov 0x0,r6` @`0x3AC22` is the default and both deadzone arms skip. **5 bytes off V59** (2 code + 3 CRC), 88 off V38. ⭐ **CAL CRC unchanged** = machine proof no `0xC6xxx` cal moved; **`0xD2000`-block CRC unchanged** = machine proof V60's falsified blend is absent. Every r24/r26 gain cal (`0xC6440/42/46`, `0xC61F6`, `0xC6444`, `0xC643E`) and V42's `gain_A` Y rows asserted **STOCK**, so this is an independent lane test, not V39/V42 layered underneath. 50/50 CRC, RWD round-trips with every gate re-run on the readback. ⚠ **Expect a manual-feel change** — the rate lanes are a phase-lead term in **base** assist and this chain has no LKAS-only decoupling point. Reversible by reflashing V59. ⚠ V59's probe rides along but is **NOT a null control**: it reads `gp-0x6ba6`, upstream of the edit, so the edit cannot move it *directly* — but a quieter bar moves the index, making it a **secondary readout**. Image SHA `35da8600aa42584d0c5cf35bde8e9a751a0396e66f149f5fd18d07982498e23a`; RWD SHA `dd647870272aaa6342c425d25efb01a13eb540b1bd2c58fbbcbef132139f8a05` |
| ~~V60~~ | V59 + the boost-amplitude BLEND coefficient `0xD2006`: 102 → 43 | 🛑 **FLASHED 2026-07-31 → NULL on the vibration. Do not re-flash.** The discriminator fired and returned the predicted null ⇒ **the parametric pump is CLOSED**, and `0xC63BA` goes with it (the index drives only the boost/damping amplitude LERPs). Original build note kept below for provenance. **BUILT 2026-07-30.** **The intervention that settles whether the 42 Hz pump DRIVES the grinding or merely ECHOES it** — the only discriminator left, since causality is not settleable observationally and `eps_crit = 2/Q` needs a passive Q that V59 cannot measure. **5 bytes off V59**: one cal byte + the `[0xD2000,0xD2FFC)` block CRC. ⭐ **MAIN CRC and CAL CRC both UNCHANGED** = machine proof the cave/probe did not move and no `0xC6xxx` calibration moved. 91 bytes off V38. Q10 0.0996 → 0.0420; 42 Hz transmission ~0.37 → ~0.17; tau 10.0 → 23.8 ms @1 kHz. Predicted eps p99 **0.169 → 0.099**. 🛑 **The effect SATURATES** — the falling edge is instant regardless of the coefficient, so this lever buys ~1.7× and then flattens (cal 32 only reaches 0.086); 43 is the knee. **GATE 1 vacuous** (calibration halfword, no code, no RAM). **GATE 2 is the argument**: base-assist path, no LKAS-only decoupling point exists in this chain — but it is a pure *dynamics* change on a gain-**scheduling** variable, adds no gain, moves no static map, cannot change any steady-state value, and tau stays <50 ms worst case. Blast radius byte-verified: mode 10's cell is private (modes 11/12 have their own). **V59's probe is UNCHANGED and is the CONTROL** — it reads `gp-0x6ba6`, *upstream* of the blend, so the index distribution must return statistically identical (76.9/18.5/4.6/0.04). 50/50 CRC, RWD round-trips. Image SHA `6328cff064598cac8d9a7a4147626c8b55ddbad2e586ac3e1b8fca9c9459be5c`; RWD SHA `519aaab4908844d6a240d48f50d8a523b39353a3a4e3bffeb3de4bb4e1d19787` |
| **V59** | V58 + cave payload replaced by the **boost-index DEPTH probe** | ✅ **BUILT 2026-07-30, UNFLASHED.** `0x14A` byte4: bit7 liveness, bit6 = `gp-0x6ba6 < 0` (the `0xFFFF` fault sentinel), **bit5/4/3 = a THERMOMETER on `gp-0x6ba6` at 512 / 1024 / 2048** (sense is "index < T", which is what lets the whole cave run on the two pinned condition codes). **19 bytes off V58** (cave + MAIN CRC only; **CAL CRC unchanged** = machine proof no calibration moved), 86 off V38. Same base `0xC4B34`/hook `0x55C0E`/68-byte extent as V55/V57/V58, all flown clean. **No new encoder, no new condition code.** 50/50 CRC, RWD round-trip, cave re-disassembled from the built image; the build also asserts both LERPs still resolve at the same mode and `tp+0x7498/0x7499` are still 1. Decoder `rlog-tools/decode_v59_boostindex.py` (hard-stops above 1% non-monotonic rather than reporting on a surviving subset). RWD SHA `ce7f6af6d7475a94462505a5f989d282966e00c9717cf6f2bbbc8b43ccdd3fc7`; image SHA `c6020a32780c1c8d952782426deef25ae390afee4606f319b0aa3c3998158d6d` |
| **V55** | the pre-V56 revert target | ✅ built, driven, fault-free. SHA `2b0fbd61e6658726ea72248f5312f4521638acaebcbd6f09d8c999e1a9e81fbf` |
| ~~V56~~ | the `0xC6AF0` mute | 🛑 **FLASHED AND FALSIFIED.** Do not re-flash |
| ~~V57~~ | the `0xC646C` decoupling + deadband probe | ✅ flashed, fault-free; its calibration is carried by V58 |

🛑 **Flash only on explicit operator instruction naming the file and the bus.** Kill openpilot/pandad first.

---

## 🛑 METHODOLOGY — three conventions that were producing wrong answers

These invalidate *reasoning* behind earlier conclusions. None changes a measured on-car outcome, but
every historical amplitude comparison needs rebuilding before it can be trusted.

1. **`carState.cruiseState.enabled` is LONGITUDINAL + LATERAL and is the WRONG engagement proxy.**
   It reads **0.00%** on V55 route `1c`, V56 route `24` seg 0, and V57 route `29` seg 1 — parking-lot
   routes where lateral was demonstrably applying. On route 28 it reads 84.0% while lateral applied 49.9%.
   **Use `carControl.latActive`, corroborated by CAN `0x18F` byte4 bit3 (`STEER_CONTROL_ACTIVE`).** The
   three agree to **99.85–99.94%**. Using cruiseState flipped V57's headline verdict from INERT to
   NOT INERT, and inflates V56's creep baseline **28×** by sweeping in hands-on parking manoeuvres at
   |ang| 89.6°.
2. **Hands-off must be SUSTAINED effort `|lowpass(tq, 3 Hz)| ≤ 200`, never raw `|tq| ≤ 200`.**
   The oscillation is ±1400 counts *on the torsion-bar channel itself*, so it trips the raw test by
   itself: 68.3% of frames scored "hands-on" have the driver doing nothing sustained. On genuinely quiet
   frames the raw test **keeps** 390 frames with oscillation rms 103.5 and **drops** 746 with rms 909.2 —
   **8.79× the amplitude.** It selects *against* the phenomenon. Switching recovers 2.5× more usable
   frames and turns subsets that had no contiguous run into computable numbers.
3. **Mean Welch power is the wrong statistic for a bursty limit cycle — use peak/p99 envelope.**
   V57/V55 grinding: median 0.419 but **p99 0.891, max 0.898**. The "halving" lived entirely in the
   median, which is dominated by quiet time between bursts. Operator called this before the data did.

✅ **A fourth problem, SOLVED 2026-07-30 by route `2b`:** engagement and motion used to be collinear —
no speed bin on any route had ≥3 windows in both arms, so the recorded ratios (877×, 786×, 14,750×,
27.7×) were moving-vs-stopped contrasts wearing an engagement label. **Route `2b` breaks it**: seg 13 is
60 s of *moving but disengaged* at 0.5–4.8 m/s against engaged creep at overlapping speeds, giving 3 of
9 speed bins with windows in both arms (18 v 18 windows, but only ~10 independent episodes per arm —
treat n as episodes, not windows). ⇒ **13.4× amplitude [95% 3.9–19.8], 16.9× speed+effort-matched.**
🛑 The old ratios stay retired; **do not resurrect 877×/786×/14,750×** — they were never engagement
contrasts. Quote the route-`2b` numbers, or absolute engaged powers.

⚠ **A fifth convention, learned the hard way this session: use a STRICT 18–26 Hz band plus a presence
test, never a wider search band.** A 15–30 Hz or 17–28 Hz argmax catches the ratchet's 2nd harmonic
(2×8.0–8.9 Hz = 16–17.8 Hz) at road speed and steps down to ~15 Hz, manufacturing a *negative* frequency
slope out of a mode switch. Two independent analysts produced two contradictory "frequency laws" this way
before the band was tightened.

⚠ **A sixth: prominence, not envelope amplitude, is what separates a mode from broadband.** The
disengaged arm's loudest 18–26 Hz moments are single-digit prominence at |ang| up to 295° — a driver
cranking a wheel. An envelope-ratio headline divides one broadband spike by another; the prominence
contrast (34× grinding vs 6.1× ratchet) and the presence/absence are the defensible statistics.

---

## Signal-identity corrections of record

- 🛑★★ **`gp-0x6c2c` — the oscillation detector's input — is a MOTOR-RATE DERIVATIVE, not torque and not
  a raw per-tick difference.** Produced in `FUN_00041464` @`0x4184E`; all cals byte-read LE:
  ```python
  K1 = 37     # cal 0xC643C, >>7        K2 = 22   # cal 0xC40DC, >>6
  x      = s16(gp-0x4f50)                            # resolver/motor ELECTRICAL RATE
  if abs(x) > 13000: gp_0x6c2c = 0x7fff; return      # validity ceiling -> fault sentinel
  target = x * 1024
  step   = ((target - old) * K1) >> 7 ; old += step   # EMA #1 increment -- THE DIFFERENCE
  acc    = clamp(step * 0x20, -0xfa0000, 0xfa0000)    # x32, clamp +-16,384,000
  state += ((acc - state) * K2) >> 6                  # EMA #2
  gp_0x6c2c = state >> 9                              # range +-32,000; T = 40.0% of that
  ```
  ⇒ **an ACCELERATION** — differencing kills DC, so a sustained large steering input cannot drive it.
  Sibling `gp-0x6c2e` takes the same `acc` through a slower EMA (cal `0xC40DA` = 3, `>>7`).
  **Sizing:** a 21.3 Hz sinusoid needs `|gp-0x4f50|` ≈ **1683** counts @1 kHz / **1821** @100 Hz to trip
  `T` — inside that signal's own ±13000 validity ceiling, so **the detector is NOT structurally blind to
  the mode; the drive was ~1.7–2× short.** Independently reproduced in the frequency domain
  (`|1-H1|`=0.43041 × `|H2|`=0.95375 ⇒ `gp_0x6c2c = 7.5965·U` ⇒ U = **1685**) — 4 significant figures by
  a different method. The `acc` clamp bites at U ≈ 4017 ⇒ `T` is reached at ~42% of saturation, linear there.
  🛑 **Do NOT size `T` from bus torque.** A pass this session derived "T ≈ 2048–2560" and "LSB ≤3.29×
  finer" from the `0x18F` torque channel; **both are VOID** — `gp-0x6c2c` is not torque-derived and does
  not share that LSB. Also void: a "per-tick rate ⇒ effectively dead" reading that priced the chain at
  unity gain and missed the `×1024` and `×32` pre-scales, which are invisible from the bus.
  ⚠ `gp-0x4f50`'s physical units remain **untraced** (needs the ISR writing `gp-0x29c4`, or a probe), so
  1683 is in raw counts of a signal whose scale is unknown.
- 🛑★ **`gp-0x671a` is NOT private to the rate lanes — 4 external consumers.** Byte-scanned both
  encodings, whole image: 8 real hits, 6 reader functions, sole writer `0x42A12`. External:
  **`FUN_0003a382`** (a **continuous LERP index**, not a gate, shaping the live P/I/D lane `gp-0x6ad4`),
  **`FUN_00036c12`** (friction-comp `gp-0x6b26`, sums into the *same* aggregator; ⚠ its own gate uses cal
  `0xC64FD`, **not** CEIL), **`FUN_000352b4`** (gates a 2nd-order IIR update), **`FUN_00035b20`** (selects
  between two LERP-blend curves). ⇒ **lowering `T` changes five things at once.** By contrast `gp-0x67df`
  is **clean** (2 hits, both inside `FUN_000428d4`) and `T` itself has 4 readers, all inside the detector.
  `CEIL` (`0xC64FA`) is **not** private — 3 external readers.
  ✅ `gp-0x671a` is logged into a diagnostic record array each low-torque tick (`FUN_00045608(2,…)`) but
  the DTC-0x21 dispatch in that tail reads a *different* array (`gp-0x6544[2]`, producer untraced) ⇒
  "touches diagnostic logging, does not appear to gate a fault" — not chased to full closure.
- 🛑 **`0xC64FA` (CEIL) is a BYTE cal = 5, read by `ld.bu` @`0x3AA78`.** A halfword read gives **517** and
  is wrong. Lowering CEIL means writing one byte. (`T` at `0xC620A` *is* a halfword, `ld.h`, = 12800.)
- 🛑 **`gp-0x671d` is NOT "r24's override flag".** It is a **saturating rising-edge counter on a
  torque-residual/observer check** (`FUN_00041d56`, 5-tap filter combination vs `tp+0x71f8`/`0x71fa`),
  feeding DTC dispatch `FUN_00016de6(0x5e,…)`, reset only by `FUN_0003bcb2`'s resync — **not** every tick.
  8 reader functions including the motor-off dispatcher `FUN_0003d4a2`. It read **0** for all of route
  `35`, so r24 *was* covered by V64's arm. Writer/reader set confirmed exhaustive by whole-image raw byte
  scan in **both** encodings (disp16: 16 hits; disp23: 0).

- 🛑★★ **`gp-0x6ba6 == |gp-0x6b9a|`, and `gp-0x6ba6` — not `gp-0x6b9a` — is the boost amplitude index.**
  Byte-verified 2026-07-30; **`build_v58_tva.py`'s docstring was wrong on both counts** and is corrected
  in place. `FUN_0003b66a` writes both from the same r28 (`cmp r0,r28 / mov r28,r13 / bge / subr r0,r13`
  @`0x3b874-87c`, then `st.h` @`0x3b892` and `@0x3b8b0`; byte-scanned for **both** gp-relative encodings:
  exactly one writer each). `gp-0x6b9a`'s only live consumer in `FUN_00034a72` is a **five-input
  plausibility gate** (`|x| ≤ 25600` @`0x34c9c-cb4`, ANDed with `gp-0x6ba6`/`gp-0x4f68`/`gp-0x4f60`/
  `gp-0x6c2e` into r21, which zeroes r24 @`0x34fc8`) — **its sign has no effect on the output**, and two
  of its three reads there (`0x34b5e`, `0x34b68`) are **dead** (`tp+0x7499 = 1` takes the branch
  @`0x34b3c`). **`0xD28DC` hangs off pointer table `0xca4f4`, NOT `0xca23c`** (which resolves to
  `0xD2888`); resolved from image bytes across all 34 modes.
  ⇒ **THE MECHANISM:** V58 measured the *signed* sibling crossing zero at 20.93 Hz only when LKAS
  applies, so the index is that signal **full-wave rectified** — a minimum at every zero crossing,
  sweeping the boost amplitude curve (`0xD28DC` Y = 16384→8187, `0xD2888` Y = 16384→8176) at **~2× the
  mode frequency on the BASE ASSIST path**. ⚠ **INFERENCE, depth unmeasured**: a sign bit carries no
  amplitude, and the delivered swing depends on how far up the curve the index climbs —
  `<512 ⇒ ≤1.12×`, `1024 ⇒ 1.27×`, `2048 ⇒ 1.58×`, `2529 ⇒ 1.75×`, `≥5120 ⇒ 2.00×`. ⚠ **Not "inert"
  below 512** — the LERP interpolates from X = 0, so it is pinned at 16384 only at exactly zero.
  **V59 measures which regime. Do not move `0xD28DC`/`0xD2888` until it has flown.**
- ⚠ **`FUN_0003b66a` branch A is NOT a biquad** — a subagent claimed "a genuine floating-point 2-pole
  biquad, IIR by definition"; it is not. `tp+0x5018/501c/5020` = `0xC4018/1C/20` read **(1.0, 0.0, 0.0)**
  and the code is `y = b0·x[n] + b1·x[n−1] + b2·x[n−2]` with two *input* delay states — a delay line, not
  feedback. **Stateful ≠ recursive.** It is the identity 3-tap FIR already on record, so **"no biquad
  anywhere" survives and there is no new notch candidate.** Also new: `tp+0x74be = 0` (`0xC64BE`) makes
  `0x3b736–0x3b758` (the `divf.s` block) dead code.
- ⚠ **`search_instructions` undercounted again** — 8 access sites for `gp-0x6b9a` where a Python byte
  scan finds **9** (it missed V58's own cave read at `0xC4B4E`, an unanalysed region). The sole-writer
  conclusion held, but only because it was re-derived. **Never let a writer/reader set rest on it alone.**

- 🛑★★ **`gp-0x6a56` is NOT independently sensed.** `FUN_0003f776` (sole producer, 4 `st.h`, all inside it):
  `gp-0x6a56 = clamp(polarity × ((gp-0x6abe × 48 × cal(tp+0x713a)) >> 15), ±12000)` — a fixed Q15 scale of
  the **motor/resolver electrical rate**. The ±12000 is a magnitude clamp recomputed fresh each tick, not a
  rate limit; `gp-0x6a60` merely mirrors its magnitude. ⇒ **`STEER_ANGLE_RATE` is opendbc-named but is not
  an independent angle sensor**, so "996× on rate vs 877× on torque" is two EPS-internal derivations, not
  independent corroboration. And since `gp-0x6bbe`'s `baseline` is **also** `gp-0x6abe`-derived,
  `rate_error = baseline − angle_rate` may partially cancel ⇒ **the damping sign is UNRESOLVED.**
- 🛑 **`FUN_0004613e` is not a rate limiter.** It snapshots params into log cells and calls
  `FUN_00016de6(0x1c,…)`, a fault logger; **`0x3638` (13880) is a diagnostic TAG** (the same callee takes
  `0x38c7` elsewhere). The `gp-0x6bb2/4/6/8` cluster is a cross-tick **integrity watchdog** re-deriving the
  same ±512 ceiling in float, with **no forward path into any control signal**. Golden model corrected.
  ⚠ Its fault path calls `FUN_000462e6(0x39e9,…)` **ungated** — Monitor 2's hard-shutdown chain. Any edit
  to `gp-0x6bbe`'s ceiling math must update `FUN_00035154`/table `0xD2018` to match, or it may trip.
- 🛑 **`0xC6372`/`0xC636E` is a DEAD BRANCH.** `tp+0x7498 = tp+0x7499 = 1` (byte-verified, stock and every
  build) routes **both** boost and damping past the torque-EMA fallback to read `gp-0x6ba6` directly. Any
  GATE-2 analysis of those two cals is analysing a lever with zero effect on this firmware.
- **The FIR slots are real but cannot notch.** `FUN_0003b66a` implements a genuine **3-tap transversal FIR**
  (`y[n] = b0·x[n] + b1·x[n−1] + b2·x[n−2]`, two persisted delay states `gp-0x365c`/`gp-0x3658`) — **not a
  2-pole IIR biquad**, so it is unconditionally stable. Coefficients `0xC4018/1C/20` = floats
  **(1.0, 0.0, 0.0)** = identity; a second instance `0xC4048/4C/50` (`FUN_0003b8f6`) is also identity.
  Exactly **one consumer each**. See "closed levers" for why enabling them fails.
- 🛑 **The ±565/cycle slew in `FUN_0003b66a` is a CODE IMMEDIATE** (`mov 0x440d4000,r6` = 565.0f), not a
  calibration. Editing it is a code-patch-class change. The halfword 565 in the cal region
  (`[0,191,402,565,686,804,878]` at `0xCE43C` etc.) is an unrelated LERP entry — numeric coincidence.
- ⚠ **The two `STEER_ANGLE_RATE` copies disagree by a constant 1.25×** (`0x18F[2:4]×−0.1` reads 0.799–0.800
  of `0x14A[2:4]×−1.0`, corr +0.9997). One DBC scale factor is wrong. Frequencies, Q, prominence and ratios
  are unaffected; **absolute deg/s figures are not.**
- 🛑 **`STEER_STATUS` is `0x18F` byte4 bits 7:4**, not bits 2:0 (which are SPARE — never written anywhere in
  the image, boot-zeroed, read 0 forever). Reading bits 2:0 yields a tautological "always 0". Route 29 shows
  `ST==3` in **120 frames**, all at `vEgo == 0.000` exactly, never with LKAS applying, in two episodes
  (1.08 s at log start, 0.10 s at t=77.8 s). **Not a V57 regression** — `0xC62EA` is byte-identical across
  V55/V56/V57. Amends the record's "ST=3 never fires on V53+".
- 🛑 **The "8.69 Hz line V56 introduced" never existed — it is wheel order 1.** V56's 35 windows sat at
  v ≈ 18 m/s where `0.489·v − 0.186 = 8.69`; its own edge windows move to 7.03 and 9.77 Hz, and V57 tracks
  identically (7.03 → 8.98 → 9.38). **Its absence on V57 is NOT evidence the `0xC6AF0` mute was live** — a
  different liveness proof is needed.
- ⚠ **The recorded V56 baseline `7.66e4` is suspect** — within 5% of route 24 seg 0's *all-frames* power,
  and that segment contains **zero** LKAS-applying frames.

---

## ✅ The tyre line — CONFIRMED, firmware-independent, and actionable

Order tracking (rescale each window's frequency axis by its own wheel frequency before pooling) puts
**both** builds at **order 1.000**:

| build | K | v range | order peak | prom | implied circumference |
|---|---|---|---|---|---|
| **V57 / r28** | 9 | 4.2–20.1 m/s | **1.000** | 11.7 | **2.088 m** |
| V56 / r24 | 59 | 9.5–20.5 m/s | **1.000** | 6.2 | **2.088 m** |

Estimator calibrated on V56 first, where the answer was known. Decoys at order 0.70/1.40/1.80/2.00 all
score far below. Per-window on V57's road episode: 2.056–2.105 m, with a 715× prominence burst at
19.5 m/s. A 235/45R18 is 2.05–2.11 m ⇒ **one line per wheel revolution**.

⇒ 🛑 **Get a wheel balance / road-force check.** Firmware cannot move a road input, and it didn't.

★ Separately, a **fixed ~7.4 Hz resonance** is present on V57 (Q 36.2 at nfft=1024, prominence 40–136×) at
1.2 m/s where wheel order is only 0.59 Hz ⇒ **not the tyre**. It is the ratchet. Route 28's creep misses it
because that creep is |ang| 5.8° — **excitation, not absence** (r29 creep is 26.5°, matching the historical
set's 12.6–42.2°).

---

## Recommended next steps, in order

🛑 **NO openpilot-side modifications.** Standing operator instruction. openpilot remains a *measurement
instrument* only.

0. ★★★★ **OPERATOR'S DECISION 2026-08-01: FLASH V67 FOR THE LONG DRIVE.** V67 = V66 + the
   grind #1 fix gated on LKAS — `0x3AA96` `c5`→`fb` (repoint the dead `gp-0x683c` gate to
   `gp-0x6806`) + `0xC6446` 512→**5244**, with both `sar` sites left STOCK. **LKAS off is
   byte-for-byte stock behaviour; LKAS on gets 2.00× at grind #1's operating point.**
   ✅ **The gate is VALIDATED ON-CAR ALREADY** — V57's probe measured `gp-0x6806` at **99.90–99.94%
   agreement with `latActive`** over 37,914 frames and **0.03–0.05 toggles/s**, so it is the
   engagement flag, it does not drop out during steady holding, and it cannot parametrically pump.
   **Pre-committed interpretation:**
   - **grind #1 gone, grind #2 gone in manual, grind #2 remains under LKAS** ⇒ the expected outcome.
     Next lever is `0xC6446` itself (one halfword) to trade the two.
   - **grind #1 back** ⇒ check probe bit6 duty (gate not firing ⇒ wrong cell) then bit5
     (`gp-0x671d` firing ⇒ the arm is masked and the gain is pinned to 1024, *below* stock).
   - **grind #2 worse under LKAS** ⇒ 2.21× is too much there; lower `0xC6446`.
   🛑 Do NOT read a V67 null without decoding the probe first — that is the V64 lesson.

0a. **V66 remains built, verified and unflashed** — the pure stock-rate-lane control. It is still the
   cleanest confirmatory revert if V67's result is ambiguous.
   ~~FLASH V66 AND DRIVE IT LONG.~~ ✅ Built, verified, and it is exactly what the operator asked
   for: **V38 4× LKAS reach · steer-to-zero · stock rate lane (grind #1 left as V38 has it) · live
   telemetry.** It is simultaneously **the confirmatory revert** — the one knob that produced grind #2
   goes back to stock, so the drive tests the attribution for free — and **the pre-flight probe for
   V67's gate**, which is the fix.
   **Route:** ordinary long driving plus deliberate parking-lot creep, **and specifically reproduce
   grind #2** — creep with heavy manual steering, |angle| ≥ 100°, both engaged and disengaged.
   🛑 **Log from before the first engagement.** Decode with `rlog-tools/decode_v66_gateprobe.py`.
   **Interpretation pre-committed, so it cannot drift:**
   - **grind #2 GONE, grind #1 back** ⇒ attribution closed. Build V67 (gate the ×2 on whichever of
     `gp-0x67f5` / `gp-0x6806` the probe shows is chatter-free).
   - **grind #2 STILL THERE** ⇒ the rate lane is the wrong tree; V62 should go back on (it is a proven
     fix and would be being given up for nothing), and grind #2 becomes a ~44.9 Hz mechanical mode to
     attack in its own right.
   - **bit5 (`gp-0x67f5`) toggling anywhere near 15–60 Hz** ⇒ that gate is DEAD; a gain keyed on it
     would be a parametric pump. Fall back to `gp-0x6806`, or to V68's dose reduction.
   - **bit4 (`gp-0x683c`) ever 1** ⇒ the cell is not dead, and V67's repoint is not a clean
     substitution. Cancel it.

0-old. ~~**NO NEW BUILD. KEEP V62 ON THE CAR AND FLY IT AGAIN.**~~ — **SUPERSEDED 2026-08-01.** The
   "rare event needing exposure" framing was right to demand more data and the data arrived: the
   operator flew V65 twice and the events are **not** rare in the corner, they are **11.7× at 40–49 Hz
   with p = 0.0003**. See THE HEADLINE. ✅ V62 flew and **BETTER** was the
   pre-committed outcome — direction confirmed, and the grinding is fixed 8–42×. **There is nothing
   established to fix.** The one candidate event is a **0.92 s singleton at p = 0.51** against an
   exposure-matched control, and V62's burst-rate CI sits **inside** V59's. A fix would be aimed at a
   coin flip.
   **The open question is the RATE of a rare event, and that needs EXPOSURE, not firmware.** Two more
   V62 routes make it estimable: if it never recurs it was a one-off; if it recurs at ~1/700 s there are
   three events and a real CI.
   **Route:** ordinary driving plus deliberate creep passes, and specifically **revisit the corner the
   burst lived in — v 2–4 m/s at high steering rate (≥32 deg/s) under LKAS.** Log from before first
   engagement. 🛑 Do **not** re-run the pre-committed `sar 0x8` (4×) escalation yet — it would trade a
   confirmed fix against an unmeasured effect.

0a. **When a build does come, the target is the RATCHET — and the search space just shrank.**
   ❌ NOT the r26 revert (structurally inert — see the headline). ❌ NOT the base-assist damper
   `gp-0x6bd0` (f5 = 0 at both operating points; a **third** independent reason V44/V47 were null).
   ❌ NOT friction comp or a deadband — the ratchet waveform is **symmetric on every build**
   (skew(dx/dt) −0.16…+0.06 vs a −3.27 sawtooth calibration) ⇒ an **amplitude-saturated resonance**,
   pointing at damping/loop gain. ❌ NOT the motor-rate LERP as a discriminator — scale resolved at
   **4.7121 counts per deg/s** (`0xC613A` = 1159), so ratchet 9.4 counts and grinding 73.0 counts both
   sit inside gain_A's **flat first segment** (breakpoints 250/400).
   ✅ **STILL OPEN, the leading idea:** the modes **do** separate on motor rate, and **breakpoints are
   calibration**. r24's gain_B (mode 10, `0xD2AEC`) has X = [0, **400**, 1500, 3000], Y = [2305, 2304,
   2149, 1948]. Moving them to bracket the two operating points — e.g. X = [0, 40, 100, 3000],
   Y = [2305, 2305, 4610, 4610] — gives **stock gain where the ratchet lives and 2× where the grinding
   lives**. Arithmetic safe (5120 × 4610 = 23.6M vs 2³¹). Hold until the ratchet is worth attacking.
   ⚠ **The ratchet's trigger sits outside the firmware**: instant #1 occurs with openpilot's command
   **railed at ±4096** for 0.64 s with the driver turning against it (engaged-creep rail duty **V62 42.4%
   vs V59 25.3%** — itself a confound). 🛑 **NO openpilot-side modifications** is standing; recorded as
   observation, and the constraint is the operator's call.

0b. 🛑 **DO NOT re-propose lowering `T` (`0xC620A`) as a cheap fix.** It is *viable on sizing* — see the
   `gp-0x6c2c` section below, ~1.7–2× short, not 5× and not 30× — but `gp-0x671a` has **four external
   consumers** besides the rate lanes, one of them (`FUN_0003a382`) using it as a **continuous LERP
   index** into the live P/I/D lane `gp-0x6ad4`. Lowering `T` changes **five things at once**, four
   uncontrolled, one of them a shape parameter on a lane already known to be load-bearing. That is not a
   clean GATE 1 and not a clean experiment. It ranks **behind** V62 and behind the phase lever.

0c. ⚠ **Superseded, was step 0:** ~~FLASH V63 FIRST, THEN V62 IF NULL.~~ The reasoning was sound and the
   ordering did buy the answer it promised — V64 (V63 + the detector probe) established *for free and
   without a second flash* that the detector never trips. But the premise ("zero manual-feel cost by
   riding the firmware's own oscillation detector") turned out to be **moot**, because the arm is never
   selected, and **weak even if it were** (r24 ×1.78, r26 ×1.00 — Honda's osc arms are gain *reductions*).
   ⚠ **Operator's standing objection, and it was right:** *"we seem to be affecting manual steering feel
   even though the symptom is specific to LKAS-engaged only."* V62 did ignore that question. The answer
   is that stock `Kd` is not sufficient for manual either — **manual has `Kd` PLUS the driver's hands**,
   which damp the very mass that resonates (wheel inertia on the torsion bar). Measured 2×2: V59 manual
   9.2 / V59 engaged 1092 / V61 manual 163 / V61 engaged 3007 — removing `Kd` degraded **both** arms, so
   it was doing real work in manual all along. LKAS also *injects* energy at the mode frequency
   (command→bar transfer peaks at **21.09 Hz**, the global max, coherence 0.917).
   ⚠ V62's residual manual-feel cost is **small and computed, not hoped**: the lane is a *derivative*, so
   it is inherently frequency-selective — doubling adds **+50 counts at 1 Hz driver bandwidth (0.49% of
   the ±10240 sum clamp) vs +732 at the mode. 14.6:1 selectivity.**
1. ~~**FLASH V62 as the primary**~~ — superseded by step 0. It remains the matched inverse of the one
   build that produced a signed result: `Kd`→0 diverged, `Kd`→2× is the same-sized step back, and the
   damping coefficient is **linear in Kd**.
   **Route:** repeat the V61 route so the comparison is like-for-like — parking-lot creep, deliberate
   LKAS on/off passes at matched speed and angle, **plus the same manual-forward and manual-REVERSE
   passes**. 🛑 **Manual reverse is the highest-information single test**: V61 introduced grinding there
   from nothing, with no LKAS in the loop at all, so it reads the lane's damping with the cleanest
   possible confound structure. Probe unchanged (`rlog-tools/decode_v59_boostindex.py`) — secondary
   readout only, since `gp-0x6ba6` is upstream of the edit.
   **Interpretation set in advance, so it cannot drift:**
   - **BETTER** ⇒ the lane is the damper, the direction is confirmed, and the next question is *how much
     more* (V63 = 4×, or the phase lever below).
   - **NULL** ⇒ the lane's damping is already **phase-limited**, not gain-limited. Then the next lever is
     the lead's **PHASE**, not its gain: **`0xC6C42` (delay D) 4 → 2 halves the differentiator's transport
     lag, 15.1° → 7.6° at 20.9 Hz.** ⚠ Note the earlier objection to D — "it is half a lockstep pair" —
     is **RETRACTED**: `0xC6C42` has exactly one reader (`FUN_0007e74a`) and D feeds a single computation
     broadcast to both cells in sync. The real caveat is that D sets the differentiator's time window and
     its response at other D is uncharacterised. Characterise it before building.
   - **WORSE** ⇒ the lead has gone past optimum into noise amplification; back off to 1.5× rather than
     abandoning the lane.
1. **Analyse the V61 rlog, route `00000031--0441e00d2b`** (4 segments). Not blocking V62, but it is the
   only quantitative record of a *signed* change and it answers two things nothing else can: whether the
   newly-appearing **manual/reverse** line sits at the **same ~20.9 Hz and Q** as the engaged grinding
   (⇒ same mode, unmasked) or elsewhere (⇒ a different finding, and V62's rationale needs revisiting),
   and whether **`ST==4`** stayed at 0. Use the strict 18–26 Hz band + presence test, `latActive`,
   sustained-effort hands-off, and peak-frequency **scatter** as the mode-vs-floor discriminator.
2. 🛑🛑 **RESOLVED 2026-07-31 — AND THE ANSWER WAS THAT THERE WAS NEVER A NUMBER. V52C DID NOT HALVE
   ANYTHING.** This step used to read "re-derive V52C's halving under the corrected statistics; the
   rlogs exist." **Both halves of that were false.**
   - **"Halved the mode" is the FILTER'S OWN TRANSFER FUNCTION, relabelled as an on-car result.**
     V52C's EMA at α = 74/1024, fs = 1 kHz, gives `|H(20.9 Hz)| = 0.4963` = **−6.08 dB**. −6.1 dB **is**
     0.496× **is** "halved". The two figures in the record are the same statement written twice.
     Independently recomputed 2026-07-31 in `analysis-2020accord/eps_feedback_path_coverage.py`.
   - **Textual lineage, git-traced.** The phrase was born in `f0adb24`
     (`HANDOFF-2026-07-28-v55-...md:205`) as a **caveat explaining why V52C's NULL is weak evidence**:
     *"⚠ V52C's null is weak — only −6.1 dB at 21 Hz while adding 61° of lag. It halved the mode's
     content; it did not remove it."* By `59acdd2` (the V59 handoff) it had become *"halved the mode —
     the largest single effect any build has had"* and the word **null had vanished**.
   - **Every contemporaneous on-car record says NULL, including the operator's own words:**
     `HANDOFF-2026-07-26-route13-...md:8` — *"V52C did not fix the vibration; it clearly changed manual
     feel."* `ARCHIVE-CLAUDE-MD-2026-07-27.md:56` — *"V52C's null is MEANINGFUL: −6.1 dB at 20.9 Hz, so
     it WAS a fair test of the `gp-0x4f60` lane ⇒ real evidence AGAINST that lane."*
   - **There are no V52C rlogs and there never were.** Routes on disk: `13,1a,1b,1c,24,28,29,2b,2c`.
     The V52C window (`08`–`12`) is absent from the whole machine and was never in git.
   ⇒ **The loop hypothesis loses its retrodiction entirely.** It now rests only on the two things that
   were actually measured: the **21.09 Hz command→torsion-bar transfer peak** (global max over 3–46 Hz)
   and the **traced absence of any motor-command feedforward**. Both stand.
   ⚠ This does **not** falsify the loop: a 2× gain cut that also adds ~57–61° of lag is a poor
   stabiliser, so a null is what a real loop with <6 dB gain margin would also produce. V52C is
   **weak-to-moderate evidence against the `gp-0x4f60` VALUE path**, not against the loop.
2b. ~~**Flash V60 as a DISCRIMINATOR**~~ — ✅ **DONE 2026-07-31, null, pump closed.** Kept for provenance:
   It attacks the
   *pump*, and the pump now looks like a passenger. **A null is the informative outcome**: it would
   close the parametric mechanism this kit spent V58/V59/V60 on and leave the loop standing.
   **Route:** parking-lot creep **v ≤ 5 m/s**, LKAS applying, **sustained hands-off ≥ 3 s**
   (`|lowpass(tq,3Hz)| ≤ 200`), deliberate LKAS on/off passes at matched speed and angle, plus a pass
   at the **10–13 m/s under-load** population. Decode with `rlog-tools/decode_v59_boostindex.py` — the
   probe is **unchanged and is the CONTROL**: the index distribution must return statistically
   identical to V59 (76.9 / 18.5 / 4.6 / 0.04 at engaged+creep+hands-off). If the index matches and the
   grinding moved, the blend is the only thing that did.
3. 🛑 **Sizing any loop fix needs the phase margin, and the bus cannot give it.** One 100 Hz mailbox
   sample is **~76° at 21 Hz** — larger than any phase worth reading. Establishing loop phase needs a
   **firmware-side probe** (a V59-class thermometer on a signal that crosses zero at 21 Hz), not more
   rlog analysis. Until then, any gain reduction is empirical and iterative.
4. ⚠ **Base-assist loop gain (`0xCA154[mode]` → `0xD2834`, speed-keyed) is the untested handle** — and
   it is a **direct trade against steering weight**, so it is an operator decision, not an analyst's.
   Grep it and state its history before proposing it. The amplitude curves `0xD28DC`/`0xD2888` and
   `0xC63BA` are the other in-loop knobs; all sit on base assist, none has an LKAS-only decoupling
   point (traced and confirmed — unlike V57's `0xC646C`, this chain has no fork).
5. **Re-run the strict-band (18–26 Hz + presence test) analysis over the V55/V56/V57 routes.** Route 2c
   independently rejected `a = 0.177` (2.60σ presence-tested, up to 7.08σ raw) and its fitted subset is
   **confound-free** (`spearman(v,|ang|) = +0.068` vs 2b's −0.728), so the fixed ~20.9 Hz line is now
   the record — but the historical amplitude baselines still need re-deriving on lateral engagement +
   sustained-effort hands-off + envelope statistics. Treat `7.66e4` as provisional.
6. ★ **The ratchet: route `2c` HAS clean episodes, and the record says it shouldn't.** 7.56 ± 0.36 Hz,
   within-run sd 0.07–0.10 Hz, prominence median **783×** (max 2142×), **15 windows / 5 runs**,
   hands-off + engaged + creep, at both 9–15° and 133°. `STATE.md` previously recorded that route 2b
   gave **zero** and that a dedicated comma-commanded route would be required. **Mode identity
   unconfirmed** — this was found incidentally by an analyst outside its brief. Verify before building
   on it.
7. **The ratchet still has no cal lever and no mechanism.** All rate-limit candidates are closed (see
   `BUILD-LINEAGE.md`). Next step is measurement, not a build. The return-centre lane `gp-0x6b62`
   (aggregator, ZERO-gated ±0x2000) has never been probed and is the operator's own hypothesis.
   🛑 **Route `2b` cannot speak to the ratchet in either direction, and the operator said so before the
   data did.** Hands-off + engaged + `|e4tq| ≥ 3500` + v ≤ 3.0 m/s yields **9 runs / 139 frames (~1.4 s)**,
   all inside one 8 s window in seg 1 that overlaps a hands-on manoeuvre sweeping −24° → +302° — i.e.
   transient zero-crossings of the lowpassed effort signal *during* hands-on driving. **Zero clean
   episodes.** The driver-applied sharp turns don't show it either: 6–9 Hz sits at or below a strict
   quiet baseline in 8 of 11 long episodes, with the 5–10 Hz peak wandering 5.3–9.9 Hz rather than
   locking at 7.4 Hz with Q≈36. **A dedicated comma-commanded route is required.**
8. 🛑 **Do NOT move `0xD28DC`, `0xD2888`, or `tp+0x73ba` (`0xC63BA` = 512).** All sit on the **base
   assist** path with no LKAS-only decoupling point, so they change manual feel and all need GATE 2.
   ⚠ `0xC63BA` is **partial by construction**: byte-verified as a 2-stage EMA (α = 0.5 both stages,
   blast radius fully contained — 2 reads, both in `FUN_0003b66a`), but it filters only the **torque**
   lane, and the index is a **sum** of that and a **resolver-rate-derivative** lane (`gp-0x6abc`, via
   `FUN_00041464` ← `FUN_00068f52`'s angle-delta differentiator). It cannot touch the second lane.
9. **Re-derive the V31 boost-floor margin** (`0xC67D8`, `0xC61B4`) — the recorded arithmetic does not
   reconcile with the image. Not blocking; V54 measured the margin directly.
6. **The take-over beep is closed** — `commIssue`/`selfdrivedLagging` under device CPU load, clean CAN/EPS
   null. Seen again on both V57 routes (route 28's at t=126.5 s produced a real soft-disable).

🛑 **Do NOT re-drive at road speed merely to "see if authority moves."** `gp-0x6966` is wind-up-driven, not
speed-driven, and V31's boost floor makes wind-up unreachable (V54 measured this on-car under railed
command).

---

## Still-standing results worth not re-deriving

- **`gp-0x6966` authority ≡ 0 by design on V31+** — soft-EME wind-up magnitude, pinned by V31's boost
  floor; `0xC6AF0` selects unity in 100% of normal operation. Measured on-car, route `1b`, 5,989/5,989.
- **Steer-to-zero works** — `0xC62EA` = 0, `ST=3` never fires while moving, 226 frames of
  `STEER_CONTROL_ACTIVE=1` below 5 km/h on route `1a`.
- **The `0x14A` byte4 bits 7:3 piggyback is proven across FOUR flashes** (V54, V55, V56, V57). Use it for
  all future firmware telemetry; **do not build another new-mailbox channel** (FOURFRAME2 was never
  transmitted — that null remains uninterpretable).
- **No notch/biquad exists anywhere** on the arb, aggregator, r24/r26, comp-add, boost/damping/friction,
  shaper, or governor paths, nor in the three non-aggregator consumers of `gp-0x6b94`
  (`FUN_0004503c` governor, `FUN_0004595a` redundancy monitor, `FUN_0007ff08` boot interlock). Two regions
  remain unswept: the raw CAN → `gp-0x4f60` producer, and the FOC current loop below `gp-0x6b98`.
- **An rlog cannot identify the flashed build from the version string** — every build reports
  `fw='39990-TVA,A160'`. Behaviourally: `ST=3` never firing while moving ⇒ V53+; probe field semantics
  identify V54/V55/V56/V57/V58 exactly.
