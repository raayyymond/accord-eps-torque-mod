# HANDOFF 2026-08-02 — V67 flew, both grinds are fixed, and the new highway symptom is NOT the rate lane

**★★★★ THE RESULT: V67 is the best build this kit has measured — grind #1 fixed (0.55 [0.34, 0.65]) and
the creep grind #2 ELIMINATED (0 burst blocks in 113 s against 24 at Kd = 2×). And the operator's new
highway complaint shows NO rate-lane dose response, so the obvious fix would have been aimed at nothing.**

🛑 **I predicted the opposite from arithmetic and had to withdraw it.** The prediction — V67 delivers
**2.44×** at highway, its maximum over the whole operating plane, and 22% above the V62 dose that raised
40–49 Hz by 11.7× — is correct arithmetic and makes a tidy story with the operator's report. **The data
does not support it.** Recording that reversal in full is the most useful thing in this document.

Read alongside `docs/STATE.md`, `docs/BUILD-LINEAGE.md`, `docs/V66-V67-DESIGN.md` and the predecessor
`HANDOFF-2026-08-01-grind2-is-v62s-own-fix-at-high-frequency.md`.

---

## What the operator brought

Route **`47`** (`75604b0a432fdc89_00000047--3e0b6134c0`), 26 segments, **~25 min / 1,495 s**, on **V67**.
An ordinary drive: street → highway → street → parking lot. Not a provoked test route.

> *"Grind #2 seems mostly gone. However, and maybe this is a grind #3 or #2.5, on the way, when doing
> somewhat significant turns, there is sometimes a resonance that I can feel is similar to grind #2.
> This higher-speed grind #2 happens when changing lanes or on a somewhat significant turn on the
> highway. Also is only on during LKAS-engaged. Grind #2 might still be there somewhat during
> LKAS-disengaged or more so LKAS-engaged at low-speed, I am not sure. Might just be dampened."*

---

## ✅ THE PROBE IS LIVE AND THE GATE WORKS EXACTLY AS DESIGNED

V67's whole design rests on `gp-0x6806` being "LKAS is applying". Measured across **all 26 segments /
150,327 frames**, decoded two ways (my extraction, and `analyze_r47_grind1.py` independently):

| bit | signal | result |
|---|---|---|
| 7 | liveness | set on every frame; **VOID = 0, illegal = 0**; byte4 takes exactly **two** values, `{0x87, 0xC7}` |
| 6 | `gp-0x6806 != 0` — **the gate** | **== `carControl.latActive` in 150,302/150,327 frames = 99.983%**; the 25 disagreements are single-frame transition edges. Per-segment |bit6 duty − `cc_lat` duty| maxes at **0.0334 pp** (s0/s21/s22/s23). All 25 disagreements lie within **2 samples** of a bit6 edge (mean 0.56, median 1); **mid-hold dropouts: ZERO**. Cross-check vs `0x18F` b4 bit3 SCA: 99.992% |
| 5 | `gp-0x671d != 0` — **the masking risk** | **0 in all 150,327 frames** |
| 4 | `gp-0x671a >= 5` | **0 in all 150,327 frames** |

⇒ **The gate is confirmed on-car, the masking risk never fired, and V67's arm was a clean binary —
stock mode-10 LERP vs cal `0xC6446` = 5244, with nothing masking it.** This is the V64 lesson applied
correctly: the probe was decoded before any conclusion was drawn from the drive.
⚠ bit4 is now a **wasted rung** — V64 already closed the oscillation-detector approach, and this
confirms it a second time.

✅ **FLIGHT-CLEAN, two independent methods.** Gridded cache: 150,327 frames, `{0: 150315, 3: 12}`.
**Raw `0x18F` src-1 CAN re-parsed from the rlogs: 150,352 frames, `{0: 150339, 3: 13}`.** `ST == 4` = **0
by both**; the 12–13 `ST == 3` frames all sit in s25 at v ≈ 0 in park (shutdown lockout). **Zero**
`steerUnavailable` / `steerTempUnavailable` / `canError` / `immediateDisable` / `controlsMismatch` /
`steerSaturated`. `wrongGear` 106 (all soft/noEntry, none while driving); `commIssue` 4 +
`selfdrivedLagging` 4 confined to one 0.17 s device-boot window — **not** the chronic-saturation
take-over-beep pattern. ⇒ **the streak extends by 150,352 frames.**

★ **The arm actually delivered on 116,527 frames = 77.52%** of the route (stock LERP 22.48%, masked 0,
third arm 0).

★★ **THE GATE CANNOT PARAMETRICALLY PUMP — and the bound is arithmetic, not spectral.** **12 transitions
in 1,504.7 s = 0.0080/s** (V57's pre-flash figure was 0.0505/0.0300). *12 transitions over 1,504.7 s can
carry at most 0.00399 Hz of square-wave fundamental — **3,762× below** the 15–60 Hz kill band.* Because
that is arithmetic, the Nyquist alias cannot weaken it. The periodogram agrees (99.857% of AC power
below 1 Hz; **0.0088%** in 15–60 Hz).

⚠ **Two caveats on the log itself.** (i) The cache's own `wall_t0` is **wrong on 2 of 26 segments** — s0
still carries a pre-NTP RTC value and s25 has no `clocks` messages at all; a route-wide constant fit
(sd 0.025 s over the 24 good segments) puts the segments at one per minute, **06:31:17 … 06:56:19**.
(ii) **s24 contains 2,630 reverse frames** and s0/s25 are largely park — exclude them from creep
statistics.

### ★★ AND THE WITHIN-ROUTE GATE A/B CONFIRMS THE CONDITIONAL DESIGN DIRECTLY
Route 47 is the first route to contain **both doses**, with the arm state recorded frame-by-frame — so
the dose contrast can be made *inside one route*, with no cross-route confound at all. 18–22 Hz
engaged-creep envelope p99, cell-stratified and episode-clustered:

| arm | vs the Kd = 1.00× pool | vs the Kd = 2.00× pool |
|---|---|---|
| **ENGAGED** (gate open ⇒ 2.00×) | **0.524 [0.337, 0.804]** | 1.183 [0.773, 1.617] |
| **DISENGAGED** (gate closed ⇒ stock) | **1.055 [0.669, 1.354]** | — |

⇒ **Suppression in ONE arm only.** That is V67's conditional design, measured, and **no other built
artifact produces it** — it is also the first evidence that has ever separated V66 from V67 (their probe
payloads cannot). 🛑 Strong evidence, not proof: it rests on 28 engaged-creep windows / 11 episodes, so
**confirm the flashed `.rwd` filename as well.**

---

## ★★★★ GRIND #1 IS STILL FIXED — a clean four-point dose ladder

Engaged creep (0.3–4.0 m/s), 18–22 Hz, p90 of per-window 99th-percentile analytic envelope, ratio
against the Kd = 1.00× pool, **bootstrapped over episodes**:

| dose | route(s) | n win | secs | 18–22 p90 | **ratio vs Kd=1 [95%]** |
|---|---|---|---|---|---|
| **Kd = 0** | V61 `r31` | 26 | 33 | 1290.0 | **1.50 [1.40, 1.61]** |
| **Kd = 1.00×** | V58 `r2b` + V59 `r2c` + V64 `r35` | 135 | 173 | 860.4 | 1.00 (reference) |
| **Kd = gated** | **V67 `r47`** | 17 | 22 | 480.9 | **0.55 [0.34, 0.65]** |
| **Kd = 2.00×** | V62 `r37` + V65 `r3a`/`r3b` | 293 | 375 | 337.2 | **0.39 [0.32, 0.48]** |

**Split-half null inside the reference pool: [0.88, 1.13].** All three arms are far outside it, and the
ladder is **monotone in dose**. V67's CI overlaps Kd = 2×'s, so V67 ≈ V62 on grind #1 — which is what
the arithmetic predicts — both deliver **exactly 2.00×** at grind #1's operating point.

⚠ **V67's engaged-creep exposure is only 22 s / 17 windows.** Route 47 was a commute, not a parking-lot
test, so grind #1's own exposure is thin. **Read the CI, not the point estimate.**

---

## ★★★★ THE CREEP GRIND #2 IS GONE

Creep (0.3–4.0 m/s), 40–49 Hz. A "burst" is a 2.56 s window whose envelope p99 exceeds **500** — the
creep grind #2 bursts on V62/V65 ran **2000–4000**.

| dose | arm | secs | 40–49 p90 | **40–49 MAX** | **bursts > 500** |
|---|---|---|---|---|---|
| Kd = 0 (V61) | LKAS ON | 33 | 88.6 | 95.6 | **0** |
| Kd = 0 | LKAS OFF | 70 | 24.7 | 37.6 | **0** |
| Kd = 1.00× | LKAS ON | 173 | 92.2 | 110.6 | **0** |
| Kd = 1.00× | LKAS OFF | 137 | 34.5 | 89.8 | **0** |
| **Kd = 2.00×** | LKAS ON | 375 | 91.9 | **1830.7** | **18** |
| **Kd = 2.00×** | LKAS OFF | 140 | 50.0 | **1469.6** | **6** |
| **V67** | LKAS ON | 22 | 63.8 | **83.5** | **0** |
| **V67** | LKAS OFF | 91 | 40.9 | **48.8** | **0** |

⇒ **Zero bursts on V67, both arms, and the maximum envelope ever reached is 84 against Kd = 2×'s 1831.**

**Power, stated honestly — the two arms are NOT equally supported:**
- **LKAS OFF is solid.** Kd = 2×'s manual-creep burst rate is 0.0429/s ⇒ 3.90 expected in V67's 91 s;
  **P(0 | that rate) = 0.020.** The gate demonstrably removed the creep grind #2 from manual driving.
- 🛑 **LKAS ON is UNDERPOWERED.** Kd = 2×'s engaged-creep rate is 0.0480/s ⇒ only **1.06** expected in
  V67's 22 s; **P(0) = 0.35.** Observing zero is unsurprising either way. **This is exactly the operator's
  own uncertainty** (*"might still be there… more so LKAS-engaged at low-speed, I am not sure"*), and it
  is genuinely unresolved. It is the single cheapest gap to close: it needs a parking lot, not a build.

---

## 🛑🛑 THE HIGHWAY SYMPTOM SHOWS NO RATE-LANE DOSE RESPONSE — and I was wrong to predict otherwise

### ★ First, the enabler nobody had used: route `2b` has 227 s of highway

Highway-engaged seconds across the whole corpus, read straight off the caches:

| route | build | Kd | highway + engaged |
|---|---|---|---|
| **`2b`** | **V58** | **1.00×** | **227 s** ← the missing baseline |
| `2c` | V59 | 1.00× | 20 s |
| `37` | V62 | 2.00× | 176 s |
| `3b` | V65 | 2.00× | 193 s |
| **`47`** | **V67** | **2.44×** | **822 s** |
| `29`, `31`, `35`, `3a` | — | — | **0 s** |

Every previous session assumed no Kd = 1× highway baseline existed. It does. ⚠ `2b`'s cache is from the
older extractor (no `cs_gear`/`clk_*`/probe fields) but carries everything a band analysis needs.

### The three-dose highway comparison — NULL

v > 20 m/s, `latActive` throughout, 2.56 s windows, p90 of per-window envelope p99, ratio bootstrapped
over ~10 s episodes:

| dose pool | blocks | secs | 40–49 p50 | p90 | p99 | **max** | blk > 300 | 30–49 max |
|---|---|---|---|---|---|---|---|---|
| Kd = 1.00× (`r2b`+`r2c`) | 27 | 276 | 43.3 | 117.4 | 409.6 | **648.4** | 2/27 | **851.5** |
| Kd = 2.00× (`r37`+`r3b`) | 41 | 420 | 48.6 | 127.5 | 253.7 | **300.0** | 0/41 | 362.9 |
| Kd = 2.44× (`r47`) | 83 | 850 | 39.6 | 93.6 | 330.8 | **488.2** | 6/83 | 672.0 |

🛑 **CORRECTION TO MY OWN FIRST PASS.** I published *"max 341.1 / 154.5 / 267.0, and zero windows
above 500 at any dose."* **Both halves are wrong** — my envelope estimator ran ~1.4–1.9× low because it
skipped the detrend + Hann taper (divided back out) that `_grind2_lib.win_env` applies, which is the
estimator that produced the 2,000–4,000 creep-burst figures and therefore the only comparable scale.
**It strengthens the conclusion rather than weakening it:** the corpus-maximum highway envelope,
**851.5 counts, is on V58/`r2b` at Kd = 1.00×** — the *stock* rate lane — at prominence 2.26 (broadband).
Block rates 7.4% / 0% / 7.2%: **no ordering.**

Matched on speed × |rate| × angle-excursion, 1500 block-resampled draws, split-half null inside the
Kd = 1.00 pool, same estimator throughout:

| band | 2.00/1.00 [95%] | 2.44/1.00 [95%] | null |
|---|---|---|---|
| 1–4 | 0.843 [0.72, 1.00] | 0.778 [0.65, 0.96] | [0.79, 1.26] |
| 6–9 | 1.213 [0.99, 1.52] | 0.876 [0.73, 1.21] | [0.64, 1.53] |
| **10–16** | **1.551 [1.25, 1.83]** | **1.501 [1.24, 1.80]** | [0.69, 1.45] |
| **18–22** | **0.828 [0.65, 0.99]** (p95) | **0.791** (p95) | [0.81, 1.22] |
| 24–28 | 1.064 | 1.211 | [0.78, 1.29] |
| 30–40 | 1.051 | 0.981 | [0.79, 1.25] |
| **40–49** | **0.970 [0.787, 1.154]** | **0.938 [0.764, 1.184]** | [0.73, 1.37] |

Manoeuvre-conditioned (`dang` ≥ 2°): 40–49 = **0.999 [0.79, 1.31]** and **0.884 [0.67, 1.28]**.
My 0.98 / 0.77 are confirmed with ~2× tighter CIs.

✅ **THE ESTIMATOR IS NOT DEAD — there is a working positive control.** **18–22 Hz IS suppressed at
highway on the Kd = 2 arms**: p95 **0.828 [0.65, 0.99]**, manoeuvre-conditioned median **0.509
[0.39, 0.92]**, outside the null. V62's grind #1 fix is visible even at road speed. So a null at
40–49 Hz is a real null, not an insensitive one.

⚠ **The one band outside the null — 10–16 Hz at 1.55/1.50 — is WHEEL ORDER 1, not a dose effect.** At
20–33 m/s order 1 is 9.6–16 Hz; the order of the strongest 10–16 line is 0.996–0.999 on all five routes,
with 87–99% of windows within 5% of order 1. It is tyre balance between drives months apart. **Do not
publish it as a rate-lane effect.**



### And the amplitudes settle the identity question

| population | peak f0 | spectral prominence | envelope p99 |
|---|---|---|---|
| **creep grind #2** (V65 `3a`/`3b`, V62 `37`) | 43–45 Hz | **48–1062×** | **2000–4000** |
| **highway** (V65 `3b`, V67 `47`) | 45–47 Hz | **~6×** | **155–370** |

Same band, but **an order of magnitude weaker and roughly ten times less spectrally sharp.**
⇒ **The highway phenomenon is not grind #2.** The operator's own instinct — *"maybe this is a grind #3
or #2.5"* — is supported.

### What IS real at highway: a broadband maneuver effect, not a mode

Within route 47, the atlas's **21 highway maneuvers vs 21 matched straight-line controls** — same build,
same speed, same engagement, so **no cross-route confound at all** — paired ratio bootstrapped over
episode pairs:

| band | 1–4 | **6–9** | 10–16 | 18–22 | 24–28 | 30–40 | **40–49** |
|---|---|---|---|---|---|---|---|
| ratio | 1.21 | **2.78** | 1.41 | 1.86 | 1.88 | 1.58 | **2.13** |
| 95% | [0.89, 2.75] | [1.38, 4.71] | [1.15, 2.26] | [1.44, 3.56] | [1.10, 3.12] | [1.12, 2.26] | [1.26, 2.90] |
| null | [0.71, 1.41] | [0.57, 1.92] | [0.63, 1.53] | [0.66, 1.53] | [0.66, 1.53] | [0.76, 1.32] | [0.67, 1.50] |

⇒ **Everything from 6 Hz up rises during a maneuver, and 6–9 Hz rises MORE than 40–49 Hz.** Absolute
levels (43 vs 21) are ~50× below the creep bursts. That reads as *"a maneuver loads the wheel and
everything gets noisier"*, not as a resonance being excited.

Band elevation does scale steeply with maneuver severity (Spearman ρ vs `rate_peak`: 30–40 Hz **+0.93**,
24–28 **+0.87**, 40–49 **+0.82**, 6–9 **+0.64**), so the driver plausibly *is* feeling high-frequency
content during hard maneuvers — but that correlation is a property of maneuvering and does not by itself
implicate the firmware dose.

### 🛑🛑 A TRAP THAT WOULD HAVE MANUFACTURED "GRIND #2 AT HIGHWAY" OUT OF A TYRE
At highway the persistent 40–49 Hz **line** is **wheel order 3**, and 26–32 Hz is order 2 (per-window
measured order p50 **2.994** and **1.995**, n > 600). At 30.8 m/s, order 3 = **44.3 Hz — one bin from
grind #2's frequency.** ⇒ **anyone peak-finding in 40–49 Hz on a highway log will "find grind #2" and it
will be a tyre.** The bursts themselves are *not* the order: the on/off-order power ratio is 6.94 in
quiet windows and **collapses to 0.82 inside bursts** (off-order rises 78× against on-order's 9×).
This kit has already been burned once this way — the "8.69 Hz line V56 introduced" was 0.489·v.

⚠ **And a measurement correction that moves every frequency ever quoted here:** `fs_of()` is biased
**+0.5–1.4%, route-dependently**. The true `0x14A` rate is **100.000 Hz on every route**, so grind #2's
"44.9 Hz" is **44.6 Hz**, and the between-route frequency spread was the instrument, not the car.


### ✅✅ THE MICROPHONE — the only instrument with NO frequency ceiling — AND ITS NULL HAS TEETH
`soundPressure` is computed on-device from audio at **16–48 kHz**, logged as a level at exactly
**10.000 Hz**. No spectrum, but **no band limit either** — the only measurement here that can speak to a
>50 Hz event.

★★ **POSITIVE CONTROL FIRST: the microphone HEARS the creep grind #2, loudly.** r3a+r3b engaged creep,
18 burst windows (torsion-bar 40–49 env p99 > 500) vs 167 quiet:

| statistic | burst | quiet | **ratio** |
|---|---|---|---|
| `soundPressure` p95 | 0.0671 [0.0513, 0.1040] | 0.0162 [0.0152, 0.0175] | **4.14×** |
| `soundPressure` max | 0.1033 | 0.0176 | **5.88×** |
| A-weighted dB p95 | 45.16 | 35.47 | **+9.7 dB(A)** |

The operator's *"almost like I have a subwoofer"* is confirmed **acoustically**. **The instrument works.**

**HIGHWAY — nothing.** r47 atlas pairs (21 v 21, speed matched to 0.011 m/s): un-weighted **1.067×**
(my independent run: 1.069 [0.960, 1.184] against a split-half null of [0.793, 1.264]), A-weighted
**−0.59 dB(A)**, dB 0.985. The diagnostic signature — un-weighted up while A-weighted stays flat, which
is what a low-frequency event looks like through a −30 dB-at-50 Hz curve — is **absent**: un-weighted
barely moves and A-weighted goes *negative*.

★★ **AND THE Kd = 1.00 CONTROL KILLS IT.** Identical CAN-only manoeuvre rule, common 22–29 m/s band:

| route | build | Kd | n_man | n_ctl | v_man | v_ctl | **`soundPressure` p95 ratio [95%]** |
|---|---|---|---|---|---|---|---|
| **`r2b`** | **V58** | **1.00** | 42 | 12 | 26.14 | 24.83 | **1.071× [0.824, 1.559]** |
| `r47` | V67 | 2.44 | 50 | 28 | 27.57 | 27.74 | **0.976× [0.814, 1.126]** |

**The stock rate lane shows a manoeuvre-related acoustic rise at least as large as V67's.** Both CIs
span 1.

★ **SENSITIVITY — the null is quantitative, not merely quiet.** Highway is **4.0× louder** broadband
(floor 0.0601 vs 0.0149 at creep). A creep-grind-#2-sized *absolute* acoustic excess dropped onto the
highway floor would read **1.78×** — comfortably resolvable. We measure **~1.0×**.
⇒ **The highway event is at most ~9% of grind #2's absolute acoustic amplitude.**

⚠ **Two honest bounds:** this bounds *absolute* amplitude (felt similarity at 30 m/s need not mean equal
amplitude), and a narrow tone could be audible while barely moving a broadband 10 Hz level.

⇒ **FOUR independent instruments now agree** — EPS torsion bar, chassis IMU (no dose ordering; 40–49 Hz
is the *least*-elevated manoeuvre band once exposure-normalised, 0.72–0.93×), the microphone (validated
at 4.14× on grind #2, ~1.0× at highway on **both** V67 and a stock-Kd build), and the alias test
(unresolvable at this precision).
Reproduce: `analysis-2020accord/r47_microphone_test.py` and `analyze_r47_imu.py mic odr mic_dose atlas dose align`.

### 🛑 THE HARD LIMIT: BOTH INSTRUMENTS ARE BLIND ABOVE ~50 Hz

| instrument | measured rate | Nyquist |
|---|---|---|
| CAN `0x14A`/`0x18F` grid | **100.000 Hz exactly** | **50.00 Hz** |
| comma IMU (accelerometer) | **101.02 Hz** | **50.51 Hz** |

⚠ **Both numbers corrected.** My 99.9–100.5 Hz came from the dt **mean**; ~1% of IMU samples are
**dropped**, inserting 20/30 ms gaps that inflate the mean but not the **median** (9.899 ms → 101.02 Hz).
Settled by test, not assertion: a lattice fit residual of **77 µs** median-seeded vs **2889 µs** forced to
100.03 (38× worse), and a synthetic fold test that samples a known sinusoid at r47's *actual* timestamps
— **7 of 7 test tones fold according to 101.02 Hz.** So the IMU has **0.51 Hz** of headroom over CAN.
★ **But headroom is the wrong quantity for the alias anyway.** 55.6 Hz appears at 44.400 on CAN and
45.421 on the IMU; 44.9 Hz appears at 44.900 on both. The discriminant is that **1.021 Hz apparent-peak
difference**, and the measured paired shift over the 120 loudest windows is median +1.677 Hz with
**sem 0.856** where ≪0.34 is needed. Resolving it needs a log at a different IMU ODR (208/416 Hz).
⇒ *"essentially no usable headroom"* stands; only the raw numbers needed fixing. ⇒ **If the felt highway vibration is above 50 Hz,
nothing in this kit can currently see it**, and every null above is a null about the *observable* band
only. This also re-confirms that IMU/CAN frequency agreement carries **no** information about the
44.9 vs 55.6 Hz alias — the two grids are 0.5 Hz apart.

---

## ★★ RECORD CORRECTIONS — firmware structure, byte-verified first-hand

### 1. r24's gain is a TWO-AXIS SURFACE, and V67's flat arm INVERTS Honda's own schedule
`FUN_0003ad74` rebuilds the gain every cycle by cross-interpolating four ROM records on **vehicle speed**
(`gp-0x6a5e`, cross axis `0xC6010` = `[0, 640, 3200, 6400]` = 0 / 9.99 / 49.95 / 99.9 km/h) and then
LERPing on **motor rate** (`gp-0x6ac0`). Byte-verified in stock `code.bin` and in `_v65`/`_v66`/`_v67`:
record layout is **20 bytes** (`u16 count=4`, `X[4]`, `Y[4]`, pad); mode 10 → `0xD2A74` / `0xD2AB0` /
`0xD2AEC` / `0xD2B28`; mode 11 → `0xD2A88` / `0xD2AC4` / `0xD2B00` / `0xD2B3C`, **interleaved at stride
0x14** (the "not consecutive" warning is confirmed).

Honda **rolls the gain off with speed**: 3072 at 0 km/h → 2151 at 100 km/h. V67 replaces the whole
surface with a flat scalar, so it delivers its **largest** multiplier where the stock design wanted the
**least**:

| operating point | stock LERP | V62/V65 | **V67** |
|---|---|---|---|
| grind #1 — creep 7.2 km/h, 128 deg/s | 2622 | 2.00× | **2.00×** |
| grind #2 creep — 5 km/h, 256 deg/s | 2409 | 2.00× | **2.18×** |
| **highway — 100+ km/h** | 2151 | 2.00× | **2.44×** |

🛑 **A flat arm is structurally incapable of fixing the highway** — one degree of freedom, two
constraints. To give 1.00× at highway the arm must be 2151, which is **0.80× at grind #1**, i.e. *worse
than stock*. To give 2.00× at grind #1 the arm must be 5244 — which is exactly what V67 uses, and it is **2.44× at highway**.
Arithmetic: `analysis-2020accord/v68_design_math.py`.

### 2. 🛑🛑 A UNITS CLAIM OF MINE, MADE AND THEN RETRACTED THE SAME NIGHT
I published: *"V67's build note converted 128 bus counts as if they were 128 deg/s; the true LERP is
2704 and the arm delivers 1.94×, not 2.00×."* **That was wrong, and so were two conclusions built on
it.** Two measurements settle the units the other way:
1. **Regress `rate_c` on the differentiated ANGLE channel** (`0x14A` b0:1, factor −0.1 ⇒ degrees):
   slope **0.95–1.00**, r ≥ **0.985** on every clean segment ⇒ **the bus rate field IS deg/s.**
2. **Physical reachability.** Observed |rate| over **407,617 frames** peaks at **521 deg/s**
   (p99.9 = 408). At 4.7121 counts/deg-s the inner breakpoints are **85 / 297 / 637 deg/s** — fully
   exercised by real driving. Under my erroneous 0.589 counts/deg-s they would be 679 / 2377 / 5093
   and Honda's 2× rolloff would **never engage in any drive**. Decisive.

⇒ **V67's build note was CORRECT**: LERP 2622 at grind #1's operating point, arm 5244 = exactly 2.00×.
**The mechanism of my error:** I composed two structural relations I had **not verified myself**
(`gp-0x6ac0 = |gp-0x6abe|` and `bus = (gp-0x6abe × 48 × 1159) >> 15`) into a scale, instead of
**measuring** the scale against a channel already in the cache. One of those two premises is wrong;
**which one is still OPEN.**

### 3. ★★ AND THE RATE AXIS IS USABLE — the retraction that matters most
My *"the rate axis is arithmetically dead, all three populations sit in the flat `[0,400]` segment"*
followed directly from the bad scale and **is withdrawn.** Correctly:

| population | deg/s | gp-0x6ac0 | LERP segment |
|---|---|---|---|
| grind #1 | ~128 | ~603 | `[400, 1400]` — **on the rolloff** |
| grind #2 creep | ~256 | ~1206 | `[400, 1400]` — further along the same rolloff |
| grind #2 highway | 30–42 | ~141–198 | `[0, 400]` — flat |

⇒ grind #1 and the creep grind #2 sit at **different points on the same rolloff**, which is exactly
what makes a single-halfword calibration edit able to separate them (Design A below).
⚠ GATE 2 caution, weakened not withdrawn: `gp-0x6ac0` is **rectified**, so it sweeps at 2f and a
steeply rate-dependent gain modulates at the mode frequency. Stock already has a rolloff there, so the
mechanism is not new; any edit that **steepens** it must argue the pump margin.

### 4. ✅ The calibration route is SAFE — and DESIGN A is the best-characterised alternative
For `0xD2A74`/`0xD2AB0`: **exactly one pointer image-wide each** (`0xCBF84`, `0xCC06C`, `0xCC154`,
`0xCC23C` — full 32-bit LE scan); all four records in **one CRC block** `(0xD2000, 0xD2FFC)`; and a
full-image 32-bit float scan finds **no float mirror** for any Y value and no clustered mirror table
⇒ **the V27 int/float desync class does not apply.** The `0xD2A74`/`0xD2AB0` blindness in
`build_v62_tva.py`'s tripwire is already fixed — V66's `assert_gain_b_surface` watches all four records
and all four pointer slots.
★ **DESIGN A — one halfword, pure calibration, and it beats V67 at every operating point:**
`0xD2ABC` (`0xD2AB0` + 12, the 10 km/h record's `Y[1]`) **2561 → 7051**. Nothing else moves.

| operating point | stock | V62/V65 | **V67** | **Design A** |
|---|---|---|---|---|
| grind #1 — 7.2 km/h, 128 deg/s | 1.00× | 2.00× | **2.00×** | **2.00×** |
| grind #2 creep — 5 km/h, 256 deg/s | 1.00× | 2.00× | **2.18×** | **1.22×** |
| grind #2 highway — 110 km/h | 1.00× | 2.00× | **2.44×** | **1.00×** |

Saturation at `|dtorque| ≥ 1190` vs a measured max of 839 (**1.42×** margin, vs V67's 1.91×); `mul`
worst case 1.68% of INT32_MAX; fold discontinuity **byte-identical to stock** (Y[0] untouched); CRC
block #41 only; never edited in any build. ⚠ Design B (both records) has only **1.13×** saturation
margin; Design C (raising Y[0]) makes the fold jump 4.7× bigger. Both rejected.
🛑 **Known costs:** it is **not** LKAS-gated, so unlike V67 it changes manual feel at low speed; and
the multiplier **humps to ~2.45× near 9.9–10 km/h** because `0xD2AB0` *is* the 10 km/h record.

⇒ **Still not recommended, for a reason that is about evidence rather than safety:** V67 already has
creep grind #2 at **zero bursts** and grind #1 fixed, and the highway shows **no dose response**, so
Design A would trade a **measured** property (manual creep is byte-stock) for margin on quantities
already at zero. Recorded as ready if the engaged-creep gap turns out to matter.

### 5. The selector ladder, re-confirmed in Ghidra
`0x3ABFA`–`0x3AC16`: `gp-0x671d` → `0xC6442`(1024), then the `0x3AA96` gate → `0xC6446`, then
`gp-0x671a >= CEIL` → `0xC6440`(2048), else the LERP. Every arm is taken when its cell is **non-zero**
(`be` skips it). The inner-axis index is `r13` = `gp-0x6ac0` with a `>= 13001 ⇒ fold to 0` step at
`0x3AAC8`/`0x3AACC` that lands on the LERP's *first* breakpoint, i.e. **maximum** gain.

---

## ⇒ RECOMMENDATION: KEEP V67. NO CONTROL-PATH CHANGE IS SUPPORTED.

**V67 is the best build this kit has produced**, and three of its four behaviours are now measured:
grind #1 fixed, creep grind #2 eliminated in manual driving, base steering byte-stock when LKAS is off.

A V68 that re-schedules the rate lane would have been aimed at a dose response that **does not exist in
the data**. Building it on the 2.44× arithmetic would have been precisely this kit's recorded failure
mode — *a statistic computed correctly over the wrong population* — for the fourth time.

🛑 **This does not dismiss the operator's report.** Lived experience outranks analyst inference here, and
the honest position is: *the symptom is real, and the instrument is blind above 50 Hz.* The gap is
**measurement**, not calibration.

### The two gaps, and what closes each

| gap | why it matters | what closes it |
|---|---|---|
| **A — engaged creep exposure is 22 s** | the one place the creep grind #2 could still be live under LKAS; P(0 bursts) = 0.35 either way | **a drive, not a build** — a parking-lot segment with LKAS engaged at creep, ~5 min |
| **B — nothing can see above 50 Hz** | if the highway vibration is >50 Hz, every null above is silent about it | 🛑 **NOT achievable at the proven cave site — see below.** The remaining option is the comma's **microphone** (`soundPressure`, computed from 16–48 kHz audio), which has no frequency ceiling |

### 🛑🛑 THE >50 Hz PROBE IS DEAD AT THE PROVEN CAVE SITE — two independent structural reasons
I proposed a V68 that samples inside the 1 kHz task and reports a **sticky** HF flag on the 100 Hz CAN
channel. A dedicated trace killed it on both halves:
1. **The hook is NOT on the 1 kHz path.** `0x55C0E` sits in `FUN_00055a98`, the CAN-`0x14A` frame
   builder, reached only via handler-table slot 10 (`0xB72D4`, the sole pointer image-wide) ←
   `FUN_00055540` ← **`FUN_00022ca0` = TCB idx-4 = task 5 = `c % 10 == 4` = 100 Hz.** The suppression
   counter `gp-0x2f68` is a **one-shot** power-on decrement with **no reload path** (2 accesses
   image-wide), so in steady state the frame enqueues every task-5 tick and never sub-divides.
   ⇒ **the cave physically cannot observe 1 kHz content — it only runs at 100 Hz.** ⚠ This also
   corrects a docstring in the kit that called this a "1 kHz TX path"; the *"CAN-TX base tick is
   100 Hz"* memory is the correct one.
2. **A sticky bit could never clear.** `gp-0x1514` has **exactly 8 accesses image-wide** and **no stock
   writer ever touches bits 7:3** — `FUN_0002193e`'s word store is a masked RMW (`andi 0xff0000ff`)
   that writes the byte back bit-identical, and `FUN_00055a98`'s three stores each `andi 0xfb/0xfd/0xfe`
   to touch only bits 2/1/0. Checked for the access class a displacement scan is blind to: only two
   `movea` pointer constructions reach the frame region (`0x55C0E`, our hook, passed to the read-only
   checksum `FUN_00057b24`; and `0x56288`, a different frame), and the overlap candidates `gp-0x1515`/
   `gp-0x1517` have **zero** accesses while `gp-0x1516`'s single `st.h` writes bytes 2–3 only.
   ⇒ a latched bit would **stay set forever**.
⇒ Breaking the aliasing barrier from firmware needs a **different hook on a task-1 site** — a new and
riskier cave, not the 68-byte extent that has flown clean nine times. **Not recommended on this
evidence.** The cheap alternative is the comma's microphone, which has no ceiling at all.

★ **Two lane facts confirmed by the same trace, worth keeping:** `gp-0x4f62` is a **signed** halfword
(9 accesses, all `ld.h`/`st.h`), produced in `FUN_0007e74a` at **1 kHz** (task 1, `FUN_0002214a` →
`FUN_0006bb08` → `FUN_0007f3f8`) as `((x[n] − x[n−D]) << 1) / phase_delta` — the `<<1` is the ×2 and the
divisor is the *measured* phase step, not a hard-coded 4. And `gp-0x6ac0` is an **unsigned** halfword
(30 accesses, all `ld.hu`), with **X1 = 400 = 0x0190 exactly**, and **Y0 == Y1 in every curve except mode-10's
50 km/h record `0xD2AEC`** (2305 vs 2304, byte-verified) ⇒ the `[0, 400]` segment is flat to within
**1 count** at every speed. ⚠ That +1 is a cal-tool rounding artifact (0.04%, behaviourally nil) but
**an exact `Y0 == Y1` equality test WILL break on it** — I asserted the stronger claim and it was in my
own byte dump the whole time.

### Open leads, recorded not chased
- 🛑 **CLOSED, NEGATIVE — the highway symptom is NOT the ratchet.** I raised this as an open lead
  because 6–9 Hz rose most in the within-route maneuver contrast. It does not survive:

  | population | n | f0 | sd | prom | **2f0 lock** |
  |---|---|---|---|---|---|
  | parking-lot ratchet, V62 `r37` | 100 | **7.46** | 1.18 | 33.3 | **0.598** |
  | parking-lot ratchet, V65 `r3a` | 115 | **7.69** | 2.08 | 7.9 | 0.304 |
  | r47 highway manoeuvre | 35 | **9.13** | 1.69 | 8.3 | 0.294 |
  | r47 highway cruise | 233 | **11.13** | 1.47 | 7.6 | 0.378 |

  f0 is **9.13 Hz, not 7.4–7.7**, it **moves to 11.13 Hz in cruise** (a mode does not move), and the
  15 Hz harmonic lock that is the ratchet's signature is **absent** (0.294 vs 0.598). Cross-dose,
  manoeuvre-conditioned, 6–9 Hz is **1.050 [0.869, 1.546]** and **1.021 [0.683, 1.787]** against a null
  of [0.68, 1.38] — both inside. The counter-evidence I flagged (V67 lowest at 6–9 Hz) was right.
- **No route in the corpus has LKAS-off exposure above 10 m/s**, so the "is it the rate lane or is it
  LKAS torque" confound cannot be broken at highway by any engagement contrast on existing data.
  Confirmed independently: **zero** gate=0 seconds above 8 m/s on route 47.
- 🛑 **No speed- or torque-conditional byte exists in this firmware to repoint a gate to.** Two search
  passes over the plausible space: every candidate is multi-valued (`gp-0x6807`, `gp-0x67fa`), folded
  into inline arithmetic with no persisted flag (`0xC6316`'s guard), true-standstill-only (`gp-0x68b3`),
  now-dead (`0xC62EA` = 0 since V53, confirmed by grep across V53→V67), or answers the same
  "LKAS applying" question V67 already found insufficient (`gp-0x67fe`, `gp-0x679f` — the latter is
  *broader*, the wrong direction). The architectural reason: this firmware's idiom for speed is
  **"always LERP, never threshold-and-latch"** — every one of the `gp-0x6a5e` reader functions inspected
  consumes it as a continuous LERP axis or an SNA guard, never as a persisted classification byte.
- 🛑 **Do NOT repoint the mask arm (`gp-0x671d`).** It looked like a second free slot. It is not:
  `FUN_00041d56` makes it a **rising-edge event counter** on a filtered resolver-rate anomaly that
  **drives DTC `0x5e`**, and it is read by **8 functions**, including 4 reads in `FUN_0003d4a2`, the
  hardware phase-disable/motor-off dispatcher, where an edge-detector on the counter itself forces a
  retry path. Unlike `gp-0x683c` (zero writers, structurally dead) this is a live fault response.
  Severing r24's reaction to it is a different, untested failure mode — and 0/150k logged frames is
  exactly what a rare fault path looks like. **Hard no for a comfort fix.**
- ⚠ **`gp-0x67ac` is an open structural risk on this lane**: `FUN_0003aa2c`'s *first* instruction reads
  it, and when it is 1 the branch that adds r24/r26 into the aggregate **does not run at all** — r24/r26
  drop out silently regardless of which gain arm was selected. Sourced from `gp-0x3d98`, written once in
  the mixer `FUN_00026c80` at `0x27314` from a register whose origin was not traced. **Worth closing
  before any future r24 build.**

---


## ✅ V68 — BUILT, UNFLASHED. A MEASUREMENT BUILD, VERIFIED FROM THE IMAGE
V67's control path is carried **byte-identical**: **39 bytes** differ in `[0x13000,0x100000)` and every
one is inside the cave span `0xC4B36`–`0xC4B73` or the MAIN CRC at `0xC4FFC`. `0x3AA94` = `847ffb97`,
all three `sar` sites stock `aa`, `0xC6440/42/44/46` = 2048/1024/512/**5244**, deadzone 3, lockout 0,
decoupled gain 3564, and **all four mode-10 `gain_B` records unchanged**. Cave uses **64/68** bytes.
Image SHA `704ece2e…` · RWD SHA `387cc0be…`.

**Payload, decoded by the orchestrator from the built cave bytes** (not from the build script's claims):

| bit | V67 | **V68** | cave instruction |
|---|---|---|---|
| 7 | liveness `0x80` | **`0x88` = liveness + bit3** | `movea 0x88,r0,r7` @`0xC4B34` |
| 6 | `gp-0x6806 != 0` — the LKAS gate | **kept** | `ld.bu -0x6806[gp],r6` @`0xC4B38` |
| 5 | `gp-0x671d != 0` — the masking risk | **kept** | `ld.bu -0x671d[gp],r6` @`0xC4B44` |
| 4 | `gp-0x671a >= 5` — **read 0.000%, a wasted rung** | **`gp-0x6ac0 >= 400`** — the rate LERP's own inner axis, at its first breakpoint | `ld.hu -0x6ac0[gp],r6` / `addi -0x190,r6,r0` @`0xC4B50` |
| 3 | must be 0 | **always 1** | — |

★★ **bit3 is now a BUILD FINGERPRINT**, and it fixes a real gap the probe audit raised: *"I cannot tell
V66 from V67 from this log — both emit the same eight payload bytes with different meanings."* V67's
payloads have bit3 **clear** by construction; V68's have it **set** on every frame. The two builds'
byte4 value sets are now **structurally disjoint**, so a log identifies its own firmware without relying
on the `.rwd` filename or on a Kd-signature inference.

★ **And bit4 now measures the load-bearing structural claim of this session directly.** Everything about
which calibration cells the symptoms occupy rests on where `gp-0x6ac0` sits relative to its first
breakpoint (400 counts = 84.9 deg/s), and that has only ever been *inferred* from bus telemetry through
a scale chain — the same chain I got wrong once tonight. bit4 measures it **inside the ECU**.

🛑 **The sticky >50 Hz rung was rejected on structure, not budget** — the hook `0x55C0E` runs at
**100 Hz (task 5)**, so the cave cannot observe 1 kHz content at all, and **no stock writer clears bits
7:3** of `gp-0x1514` (8 accesses, all masked RMW), so a latched bit could never clear. ✅ Separately
established and worth keeping: `gp-0x683c` **is** a free `.data` byte on V67+ (boot value `0x00` from
flash `0x86874`; V67 removed its only reader), useful cave state for some future build.

---

## 🛑 METHOD NOTES FROM THIS SESSION

1. **I made a confident arithmetic prediction and the data refuted it.** The 2.44× calculation is right;
   the inference from it was wrong. What caught it was going and looking for a baseline
   (`r2b`) instead of accepting *"no Kd=1 highway exposure exists"* — a claim two sessions had repeated
   without checking. **Check whether the data you need already exists before concluding it does not.**
   This is the same lesson as V57's July probe sitting unread for a month.
2. **Report the mean and the tail together — again.** At highway the tail (max, burst census) and the
   mean both say null, which is what makes that null trustworthy. At creep they would have disagreed.
3. **Exposure before effect size.** Every headline number here is quoted with its seconds and its window
   count, and the two arms of the creep result are reported with *different* confidence because they have
   different exposure. The engaged arm is 22 s and is labelled unresolved rather than folded into a
   single "grind #2 is fixed" claim.
4. **A units error survived a build and a flash.** `128 counts` read as `128 deg/s` moved a sizing
   calculation by 8× on the axis. It changed the arm by only 3% by luck, not by design. **Byte-read the
   scale cal before converting any bus quantity into a firmware axis.**
