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
| 6 | `gp-0x6806 != 0` — **the gate** | **== `carControl.latActive` in 150,302/150,327 frames = 99.983%**; the 25 disagreements are single-frame transition edges. Per-segment duty matches to ~0.02 pp (19.580% vs 19.6%, 16.186% vs 16.2%, 78.359% vs 78.3%, 34.222% vs 34.3%, 13.419% vs 13.4%, 100.000% vs 100.0% on every highway segment) |
| 5 | `gp-0x671d != 0` — **the masking risk** | **0 in all 150,327 frames** |
| 4 | `gp-0x671a >= 5` | **0 in all 150,327 frames** |

⇒ **The gate is confirmed on-car, the masking risk never fired, and V67's arm was a clean binary —
stock mode-10 LERP vs cal `0xC6446` = 5244, with nothing masking it.** This is the V64 lesson applied
correctly: the probe was decoded before any conclusion was drawn from the drive.
⚠ bit4 is now a **wasted rung** — V64 already closed the oscillation-detector approach, and this
confirms it a second time.

✅ **FLIGHT-CLEAN, and the zero-EME streak extends past 500,000 frames.** `ST == 4` = **0 / 150,327**;
`ST == 3` = 12; **zero** `steerUnavailable` / `steerTempUnavailable` / `canError` / `controlsMismatch` /
`immediateDisable` / `steerSaturated`.

### ★★ AND THE WITHIN-ROUTE GATE A/B CONFIRMS THE CONDITIONAL DESIGN DIRECTLY
Route 47 is the first route to contain **both doses**, with the arm state recorded frame-by-frame — so
the dose contrast can be made *inside one route*, with no cross-route confound at all. 18–22 Hz
engaged-creep envelope p99, cell-stratified and episode-clustered:

| arm | vs the Kd = 1.00× pool | vs the Kd = 2.00× pool |
|---|---|---|
| **ENGAGED** (gate open ⇒ 1.94×) | **0.524 [0.337, 0.804]** | 1.183 [0.773, 1.617] |
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
the arithmetic predicts (V67 delivers 1.94× at grind #1's operating point, V62 delivers 2.00×).

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

| dose pool | n win | secs | 40–49 p90 | **40–49 MAX** | **bursts > 500** | **ratio vs Kd=1 [95%]** |
|---|---|---|---|---|---|---|
| Kd = 1.00× (`r2b`+`r2c`) | 186 | 238 | 86.7 | **341.1** | **0** | 1.00 |
| Kd = 2.00× (`r37`+`r3b`) | 282 | 361 | 84.9 | **154.5** | **0** | **0.98 [0.71, 1.63]** |
| Kd = 2.44× (`r47`) | 623 | 797 | 67.1 | **267.0** | **0** | **0.77 [0.56, 1.44]** |

**Split-half null: [0.53, 1.86]. Both ratios sit inside it. No dose ordering, and V67 is if anything the
lowest.** Over ~1,400 s of highway at three doses, **not one window anywhere exceeds 500**, against creep
where Kd = 2× produced 24 of them up to 1831.

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

### 🛑 THE HARD LIMIT: BOTH INSTRUMENTS ARE BLIND ABOVE ~50 Hz

| instrument | measured rate | Nyquist |
|---|---|---|
| CAN `0x14A`/`0x18F` grid | ~100.5 Hz | **50.2 Hz** |
| comma IMU (accelerometer, hardware timestamps) | **99.9–100.5 Hz** | **49.97–50.26 Hz** |

The IMU gives **no headroom whatsoever** over CAN. ⇒ **If the felt highway vibration is above 50 Hz,
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
| grind #1 — creep 7.2 km/h | 2704 | 2.00× | **1.94×** |
| grind #2 creep — 5 km/h | 2409 | 2.00× | **2.18×** |
| **highway — 100+ km/h** | 2151 | 2.00× | **2.44×** |

🛑 **A flat arm is structurally incapable of fixing the highway** — one degree of freedom, two
constraints. To give 1.00× at highway the arm must be 2151, which is **0.80× at grind #1**, i.e. *worse
than stock*. To give 2.00× at grind #1 the arm must be 5408, which is **2.51× at highway**.
Arithmetic: `analysis-2020accord/v68_design_math.py`.

### 2. 🛑 A UNITS ERROR IN V67's OWN BUILD NOTE
The note sized the arm as *"creep 7.2 km/h, **128 deg/s** ⇒ LERP 2622 ⇒ 5244 = 2.00×"*. It converted
**128 bus counts** as if they were **128 deg/s** (axis 603 instead of 75). Byte-read chain:
cal `tp+0x713a` = `0xC613A` = **1159**, so `bus = (gp-0x6abe × 48 × 1159) >> 15` = 1.697754 × `gp-0x6ac0`,
and `gp-0x6ac0` = `2^18/(48×1159)` = 4.71210813 counts per deg/s exactly ⇒ the two compose to
**bus counts = 8 × deg/s exactly**. The true LERP at grind #1's operating point is **2704**, so V67's arm
delivers **1.94×**, not 2.00×. Numerically small; a units error inside a load-bearing sizing calculation
is not.

### 3. ★★ THE RATE AXIS IS ARITHMETICALLY DEAD FOR EVERY SYMPTOM
Mapping the measured populations onto the LERP's own inner axis:

| population | bus counts | **gp-0x6ac0** | LERP segment |
|---|---|---|---|
| grind #1 | ~128 | ~75 | `[0, 400]` — **FLAT** |
| grind #2 creep | ~256 | ~151 | `[0, 400]` — **FLAT** |
| grind #2 highway (`r47` seg 4) | 30–42 | ~18–25 | `[0, 400]` — **FLAT** |

**100% of the windows in all three populations, on every build, land in the flat first segment**, where
`Y[0] == Y[1]`. ⇒ `Y[2]`/`Y[3]` never participate, and the rate axis is not a *weak* discriminator — it
is **incapable** of discriminating. That explains the previously-measured 81.1%/48.5% rather than being a
separate fact. **Only the SPEED axis can separate anything on this surface.**

⚠ Sharpening the rate breakpoints to force a rolloff between axis 75 and 151 is available and is
**rejected on GATE 2**: `gp-0x6ac0` is a *rectified* filtered motor rate, so it sweeps at 2× the mode
frequency, and a steep gain slope on it is a **parametric pump** — the failure mode V58/V59/V60 chased
for three builds. Keeping every operating point inside the flat segment gives zero local slope.
**Do not propose a rate-breakpoint move.**

### 4. ✅ The calibration route is SAFE — and it is on the shelf, not recommended
For `0xD2A74`/`0xD2AB0`: **exactly one pointer image-wide each** (`0xCBF84`, `0xCC06C`, `0xCC154`,
`0xCC23C` — full 32-bit LE scan); all four records in **one CRC block** `(0xD2000, 0xD2FFC)`; and a
full-image 32-bit float scan finds **no float mirror** for any Y value and no clustered mirror table
⇒ **the V27 int/float desync class does not apply.** The `0xD2A74`/`0xD2AB0` blindness in
`build_v62_tva.py`'s tripwire is already fixed — V66's `assert_gain_b_surface` watches all four records
and all four pointer slots.
⇒ A speed-scheduled Y-row edit is buildable and safe. **It is not recommended** (see below).

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
| **B — nothing can see above 50 Hz** | if the highway vibration is >50 Hz, every null above is silent about it | a firmware probe that samples inside the 1 kHz task and reports a **sticky** HF flag on the 100 Hz channel |

### Open leads, recorded not chased
- ★ **The highway symptom may be the RATCHET, not grind #2.** 6–9 Hz rises **2.78×** during maneuvers —
  more than 40–49 Hz — and the **ratchet is strongly LKAS-gated (p = 1.09e-08)**, which matches the
  operator's *"only during LKAS-engaged"* far better than grind #2's weak 84.5%-vs-54.7% association.
  ⚠ Counter-evidence: between builds, 6–9 Hz at highway runs 169.0 / 197.8 / **106.9** — V67 is the
  **lowest**, so it is not elevated by dose. Worth a dedicated test; not concluded.
- **No route in the corpus has LKAS-off exposure above 10 m/s**, so the "is it the rate lane or is it
  LKAS torque" confound cannot be broken at highway by any engagement contrast on existing data.

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
