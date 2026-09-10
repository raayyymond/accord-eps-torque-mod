# DESIGN — V290 LIVE TELEMETRY (CAN 0x14A byte 4, bits 3/5/7)

**Agent** `instr290` (SUBAGENT; orchestrator `main`). **Design and analysis only — nothing built,
flashed or sent.** 2026-09-09.

**Scripts (everything numeric below reproduces from these three; all under `rlog-tools/studies/grind/`)**
- `v290_telemetry_sizing.py` → `_scratch/v290_telemetry_sizing.txt` + `.json` — notch response, the
  `|n| ≥ |x|>>S` family, the ±12000 guard headroom.
- `v290_telemetry_sizing2.py` → `_scratch/v290_telemetry_sizing2.txt` + `.json` — the synthetic
  frequency calibration and the `|n| ≥ |d|<<k` family.
- `v290_telemetry_sizing3.py` → `_scratch/v290_telemetry_sizing3.txt` + `.json` — the `|n|`
  distribution and the threshold/ratio families that decided the bit table.

**Routes** `r39` (V282 — **V290's base**), `r62_v289`, `r63_v289` (V289 — they carry the 15–17 Hz
line V290 has to handle). Caches `analysis-2020accord/_scratch/cache/v280/<key>.npz`, read-only.

---

## 0. HEADLINE — and the three candidate rungs this pass KILLED

**The bit table is `b5 = sign(n)` · `b7 = |n| ≥ 16` · `b3 = |d2| > |d|`, with `b4`/`b6`/`b0–2` left
exactly as V282 wrote them, as the "must not move" controls.** `n = x − y` is the notch's removed
component; `d = x − x_prev`, `d2 = d − d_prev` at 1 kHz.

Three rungs that looked obvious were **measured and discarded**, which is the whole point of doing
this before cutting rather than after:

| candidate | why it was discarded | evidence |
|---|---|---|
| `\|n\| ≥ \|x\|>>S` (S = 0…6) — "is the operand's content in the notch band?" | **NEGATIVE separation** between symptomatic and quiet engaged frames on all 3 routes × both upsampling models. It reads the operand's LOW-FREQUENCY magnitude, not its band content: engaged p50 \|x\| is **4–8 raw counts** while p99 is 1257–1883, so on quiet frames the comparator is a coin flip at the LSB floor and on loaded turns it is dominated by the wheel slewing. | `sizing.txt`, "SEPARATION (sympt-quiet)" rows: −0.006 … −0.238 |
| `\|n\| ≥ \|d\|<<k` — the same idea with the LF killed by a first difference | Its **synthetic** calibration IS band-selective (k = 3 peaks at duty 0.50 at 20 Hz, half-max ≈ 10 and ≈ 30 Hz) but on the car it is **flat**: r39 symptom 0.438 vs quiet 0.460. Both numerator and denominator sit at the LSB floor on quiet frames. | `sizing2.txt` §A and §B |
| **`\|n\| ≥ \|y\|` — V289's own b7 form, reused unchanged** | **Inverted** on this operand: symptom duty is *lower* than quiet on every route and both models (r39 0.061 / 0.189; r62 0.169 / 0.263; r63 0.166 / 0.283). Reusing V289's bit here would have produced a bit that falls when the grinding rises. | `sizing3.txt`, `\|n\|>=\|y\|>>k`, k = 0 |

⇒ **The kit's design law held exactly as written.** The rungs that survived are a **sign bit paired
with a magnitude channel** whose threshold is sized from a distribution measured on three routes —
not a bare threshold, and not a ratio whose scale was assumed.

---

## 1. WHAT THE CAVE SEES, AND FIVE BUILD-RELEVANT FACTS THAT FELL OUT OF SIZING IT

The V290 element is a **Q14 TDF-II RBJ notch, 21.5 Hz, Q 1.5, fs 1 kHz**, on the **rate operand
`x = gp-0x6a56`**, hook **`0x28F4C`** (`ld.h -0x6a56,gp,r7`), cave **`0xC4C90`**; plus the feedback
lag pole `0xC63E8`/`0xC63EA` 16.5 → 40/50 Hz.

Quantised coefficients (`a0 = 16384` implied): **`b0 = b2 = 15680`, `b1 = a1 = −31074`, `a2 = 14976`**.
`x` reaches the wire as `0x18F[2:3] = −(gp-0x6a56)`, raw counts, LSB 1 — so `x = −rate` and the
100 Hz cache column *is* the operand.

|H(f)| and the removed component's gain |1−H(f)| (EVIDENCE, `freqz` of the quantised coefficients):

```
 f Hz :   0    5    7.5   10   12   14   15   16  16.5  17   18   20  21.5  23   25   27   30   40   60  100  200
 |H|  : 1.000 .987 .967 .930 .880 .800 .742 .670 .628 .581 .474 .214 .002 .198 .414 .568 .715 .894 .965 .990 .998
 |1-H|: 0.000 .161 .255 .367 .474 .600 .670 .742 .778 .814 .880 .977 1.00 .980 .910 .823 .700 .448 .261 .144 .063
```

**Five facts, each EVIDENCE, each of which the build should know:**

1. ⭐ **Honda's ±12000 implausibility BAIL at `0x28F50` NEVER binds.** Measured max |x| is
   3011 / 3301 / 3872 raw across r39 / r62 / r63; the notch's worst output |y| is 3008–3877, i.e.
   **headroom ×3.1–4.0**. A "the clamp fired" rung would be a dead bit. The cave must still carry the
   ±12000 output clamp (a Q-class notch overshoots ×1.155 and the bail is catastrophic, not graceful),
   but it should be treated as a guard rail, not an instrument.
2. ⭐ **No int32 pre-shift is needed at THIS hook.** The `0x29D72` (post-lag `r26`) placement needed a
   `sar 3` / `shl 3` pair because |r26| ≤ 46080; here |x| ≤ 12000 by Honda's own guard and the worst
   `b0·x` is 1.88e8 — the same headroom V289's cave already ships with (its bound was 15360).
   The 0.032 deg/s of feedback resolution `fbhook` priced is **not spent** at this hook.
3. 🛑 **V289's "b5 duty = 0.500" signature does NOT transfer.** V289 filtered the PID sum S
   (|S| ≤ 15360); here the operand sits at the quantisation floor most of the time (engaged
   p50 |x| = 4–8 raw counts), so the notch's floor-shift bias (`y = acc >> 14` floors, biasing
   `n = x − y` positive) is a large fraction of |n|. **Predicted b5 duty is 0.41–0.45 engaged, not
   0.50.** Scoring V290 against "≈ 0.500" would read as a FAIL on a working cave.
4. 🛑 **A Q1.5 notch at 21.5 Hz is WIDE.** It removes **67 % at 15 Hz and 74 % at 16 Hz** — i.e. it
   *does* act on the line V289 relocated to — but it also removes **16 % at 5 Hz and 26 % at 7.5 Hz**,
   right where the 7.5 Hz strong-turn ring the operator's bookmarks sit on lives. The loop metric
   already prices this (`gate73` 0.989/1.009 in the decision table); for **telemetry** the consequence
   is that `n` is *not* a clean band indicator during loaded turns, which is the second reason the
   ratio rungs failed.
5. ⚠ **The operand-refresh rate (100 Hz vs 1 kHz) is still BELIEF**, per
   `TRACE-2026-09-09-v290-postlag-hook-rate-operand-ram.md` Q1(i) ("same-tick freshness is BELIEF").
   I could not design a clean one-bit test for it (see §6). **But the sizing is robust to it**: every
   duty below was computed under BOTH a zero-order-hold upsample (correct if the cell refreshes at
   100 Hz) and a linear interpolation (optimistic if faster), and the two differ by ≤ 0.03 on every
   scored rung. The bit table does not depend on resolving it.

---

## 2. THE BIT TABLE

Bits 0–2 are stock Honda (frame builder `0x55AC0`/`0x55AE8`/`0x55B06`); bits 3–7 are ours. **b4 and b6
keep V282's r24 comparators untouched** — they are the "must not move" control (§4).

### b5 — `n < 0` — LIVENESS

**Computes** (integer, 1 kHz, full precision inside the cave, before any quantisation exists):

```python
acc = b0*x + s1 + e            # b0 = 15680
y   = acc >> 14                # arithmetic shift: floors
e   = acc & 0x3FFF             # the 14-bit residual, carried so DC is preserved
n   = x - y                    # THE REMOVED COMPONENT
b5  = 1 if n < 0 else 0
```

**Why this quantity.** `n = (1 − H)(x)` has **exactly zero DC gain by construction** — the notch has
unity gain at DC and at Nyquist — so `n` is zero-mean whatever the car is doing, and its sign is a
bit whose duty cannot be driven to 0 or 1 by any driving regime. It is the one rung in V289 that
worked exactly as designed (duty 0.500, spectral share 2.6–2.9× flat, coherence 0.55–0.99 with the
band-passed wheel rate), and it is the rung that *attributed the build from the tap*.

**Predicted duty** (EVIDENCE, mirror on 3 routes × 2 upsampling models):

| | ENGAGED | SYMPTOMATIC | QUIET | DISENGAGED |
|---|---|---|---|---|
| r39 (V282) | 0.443 / 0.451 | 0.495 / 0.494 | 0.437 / 0.446 | 0.294 / 0.319 |
| r62 (V289) | 0.406 / 0.425 | 0.495 / 0.495 | 0.397 / 0.407 | 0.180 / 0.224 |
| r63 (V289) | 0.438 / 0.450 | 0.491 / 0.492 | 0.432 / 0.445 | 0.291 / 0.290 |

⇒ **predict 0.40–0.46 engaged, 0.18–0.32 disengaged, ≈ 0.49 on symptomatic frames.**
Synthetic control: for a pure line at ANY frequency 3–300 Hz the duty is 0.47–0.50 — the departure
from 0.5 on the car is the quiet-frame LSB regime, nothing else.

**Second read, the one that actually proves the filter ran:** the spectrum of `(2·b5 − 1)` on engaged
runs ≥ 8 s must show a peak near **21.5 Hz** (V289's read 19.9 / 16.8 Hz against its own 20.05 Hz
centre), an 18–25 Hz share well above the flat 0.095, and a correlation with the band-passed 0x18F
rate far above the circular-shift null.

**Reads on V282 / V288 / V289 (the controls):** V282 r39 = 0.134, V288 r5e = 0.412 *and 99.7 %
agreement with the command sign*, V289 = 0.500 *with a 20 Hz spectrum*. **V290's signature is
0.40–0.46 with a 21.5 Hz spectrum AND a disengaged duty of 0.18–0.32** — V289's b5 stopped toggling
entirely 3 s after SCA fell (its hook is inside the engaged path); this cave sits above the
engagement guard, so **sustained disengaged toggling is a V290-only signature.**

---

### b7 — `|n| ≥ 16` — THE MAGNITUDE CHANNEL

**Computes** `b7 = 1 if abs(n) >= 16 else 0`, with `n` at full precision as above; 16 = raw counts of
the rate operand.

**Why a threshold and not a comparator.** The kit's law prefers a comparator *when the scale is
unknown*. Here it is **known and measured**: `n` is band-limited by construction (|1−H| ≥ 0.5 only
over **12.44–37.13 Hz**, → 0 at both DC and Nyquist), so **nothing above 50 Hz can inflate it** and
the 100 Hz wire predicts its magnitude honestly. The measured distribution, three routes, both models:

```
|n| raw counts        ENGAGED p50/p90/p99      SYMPTOM p50/p90/max      QUIET p50/p90
 r39 (V282)              4-5 / 20-22 / 54-57      23-25 / 53-56 / 254-282     4 / 15-17
 r62 (V289)              2-3 / 15-16 / 42-44      17    / 41-43 / 545-618     2 / 11
 r63 (V289)              3-4 / 18-19 / 61-65      23-24 / 61-64 / 218-237     3 / 13-14
```

**Predicted duty at T = 16** (EVIDENCE, `sizing3.txt`):

| route | ENGAGED | SYMPTOMATIC | QUIET | DISENGAGED | symptom : quiet |
|---|---|---|---|---|---|
| r39 (V282, the base) | 0.156–0.174 | **0.677–0.691** | 0.098–0.117 | 0.074–0.078 | **5.9–6.9×** |
| r62 (V289) | 0.092–0.102 | **0.535–0.554** | 0.043–0.052 | 0.034–0.036 | **10.7–12.3×** |
| r63 (V289) | 0.124–0.136 | **0.660–0.670** | 0.065–0.076 | 0.117–0.122 | **8.8–10.2×** |

**Why T = 16.** It is the threshold that maximises symptom : quiet contrast while keeping the engaged
duty comfortably inside (0,1) on every route and both models. The full sweep is in `sizing3.txt`;
T = 12 is the 2-byte-cheaper alternative (fits V850's 5-bit `cmp` immediate) at contrast 3.9–7.6×
and engaged duty 0.14–0.25 — **acceptable if the builder wants the bytes; T = 16 is the pick.**
T ≥ 32 pushes the engaged duty below 0.05 and starts to look like V96's under-used channel.

**What it adds that the wire does not have.** The wire's 13–22.5 Hz envelope is what defined
"symptomatic" above, so b7 does not tell us *where* the line is — **it tells us how much of it the
loop's own operand actually carried, at 1 kHz, at full precision, inside the loop.** Paired with b5
it is the design law's sign-plus-magnitude: **b5 says the filter ran, b7 says how much there was to
remove.** That pairing is what makes a low b7 duty interpretable — see §5.

⚠ **Read the direction correctly.** These predictions are computed on the **V282 and V289** operand.
If V290 works, the ring shortens, the operand carries less 12–37 Hz content, and **b7's symptomatic
duty FALLS below the r39 value of 0.68.** A falling b7 with a healthy b5 is the *success* signature,
not a dead cave. That is precisely why b5 is independent.

---

### b3 — `|d2| > |d|` — THE HIGH-FREQUENCY PRICE OF THE 40–50 Hz FEEDBACK POLE

**Computes**, at 1 kHz, with two extra RAM words:

```python
d  = x  - x_prev ;  x_prev = x          # first difference
d2 = d  - d_prev ;  d_prev = d          # second difference
b3 = 1 if abs(d2) > abs(d) else 0       # STRICT >, see below
```

**Why this quantity, and why it is the only genuinely new thing on the page.** The V290 decision table
(`docs/review/V290-DECISION-TABLE-2026-09-09.md` §0) names one cost nobody has priced: *"HF noise into
the motor rises ×2.21 (fb 50 Hz) or ×1.91 (fb 40 Hz), rms |R| over 30–500 Hz vs V282 … a NEW class of
risk for this kit — no flown build has raised HF loop gain by 2×."* **Every model this kit has of this
loop was fit to 100 Hz wire data. Nobody has ever seen the 1 kHz spectrum of the rate operand.** For a
line at frequency f, `|d2|/|d| = 2 sin(π f / 1000)` — the ratio rises monotonically with frequency, so
this rung is a pure high-frequency detector that **sees exactly what the 100 Hz wire cannot**, and it
sits UPSTREAM of the pole, so it measures the *source* content. That makes every candidate pole
(16.5 / 25 / 40 / 50 Hz) sizeable offline from one drive — the kit's ⭐ *"prefer the inert tap to the
blind dose"* rule, applied to a cost rather than to a lever.

**Its null is calibrated, not assumed.** Synthetic, a 200-count line on a 400-count 0.5 Hz sweep, duty
of b3 **conditioned on b7 = 1** (i.e. on frames with real signal):

```
 f Hz    3     5    7.5    10    12    15    17    20   21.5   25    30    35    40    50    60    80   100   150   200
 duty  .000  .000  .003  .029  .036  .047  .056  .072  .078  .103  .112  .141  .174  .226  .208  .223  .229  .475  .863
```

and on the three real routes, the same conditional read:

```
 P(b3 | b7=1), engaged :  r39 0.093 / 0.120   r62 0.094 / 0.103   r63 0.095 / 0.098      (zoh / lin)
```

⇒ **the null prediction is P(b3 | b7 = 1) = 0.09–0.13.** A measured value **≥ 0.20 engaged is content
above ≈ 50 Hz that no instrument in this kit has ever recorded**, and it converts the ×2.21 from a
model number into a measurement. A value at or below 0.13 says the HF risk is immaterial on the
source side and the 50 Hz pole variant is the right one to keep.

**Why STRICT `>` and not `≥`.** With `≥`, ties dominate: `d == 0` on **91 %** of ticks under the
100 Hz-refresh model, so `0 ≥ 0` pins the bit at 1.000 and it carries nothing. With `>`, the engaged
duty is 0.091–0.189 and the conditional read above is stable to ±0.015 across three routes and both
refresh models. **This is a real trap: the `≥` form is a dead bit, and it would have looked alive.**

**Which bit it spends.** b3 currently carries V282's `sign(gp-0x3680)`, which V289's own design
listed as spendable ("nothing to put on it that a null would need") and which has never appeared in an
analysis. **b4 and b6 are NOT spent** — they stay as the control.

---

## 3. THE TWO QUESTIONS THE DRIVE MUST ANSWER

### (a) Is the cave LIVE and filtering? → **b5, alone and unambiguously.**

PASS requires all three:
1. `b5` engaged duty in **0.38–0.48** (predicted 0.40–0.46), and per-engaged-segment duty inside that
   band on every segment ≥ 8 s;
2. the `(2·b5 − 1)` spectrum on engaged runs ≥ 8 s peaks at **20–23 Hz** with an 18–25 Hz share ≥ 0.15
   (flat = 0.095), and correlates with the 18–25 Hz band-passed 0x18F rate far above a 20-shift
   circular null;
3. `b5` **disengaged duty in 0.10–0.40** — i.e. it keeps toggling with the loop off, which no previous
   build's b5 does (V289 froze 3 s after SCA fell; V282/V288 hooks are inside the engaged path).

FAIL looks like: duty pinned at 0.000 or 1.000 (cave skipped, or FLAG frozen), or duty in range but
with a flat spectrum and null-level correlation (the cave ran on something that is not the rate
operand — the wrong-cell failure).

### (b) Did the RING GET SHORTER? → **the wire, NOT the cave bits.**

The 15–22 Hz line's frequency, envelope, half-peak duration and decay τ / ζ_eff are read exactly as
`v289_marks_r62_r63.py` already reads them, from **0x18F wheel rate**, **driver torque** and the
**0x1AB/427 tap** — three independent 100 Hz streams that resolved V289's line to 15.92 Hz ± 0.43 Hz.
**The cave bits must not duplicate this** (`CLAUDE.md`: cave bits COMPLETE the picture the operator
already reasons from). The headline number to beat: V282's ring falls to 10 % in **582 ms / 11.7
cycles**, V289's in **786 ms / 13.1**; V290 predicts **≈ 424 ms / 7.1 cycles**.

**What the cave ADDS to that picture, and only the cave can:**

| cave bit | what it adds |
|---|---|
| **b7** | the in-loop band energy at 1 kHz — converts *"the ring got shorter on the wire"* into *"…and the loop's own feedback operand carried less of it"*, and separates **"the notch removed the content"** from **"the content was never there on this drive"**. A short ring with b7 symptomatic duty still ≈ 0.68 (r39's value) means the wire got quieter for a reason other than the notch. |
| **b3** | the >50 Hz source content, invisible on every 100 Hz stream, which prices the ×2.21 HF cost of the 40–50 Hz feedback pole. **The only bit that can catch a new whine/hiss/harshness complaint before the operator has to name it.** |
| **b5** | the phase relation of the removed component to the wheel rate at the line (V289 read coherence 0.55–0.99, phase −27…−64°) — the in-loop half of the phase picture the 427 tap gives from outside. |

---

## 4. THE POSITIVE CONTROL

**MUST MOVE if the cave runs:** `b5` — duty strictly inside (0,1) engaged **and** disengaged, with a
20–23 Hz spectral peak. It cannot read that way unless the cave executed, read the rate operand, and
ran the recursion; a frozen FLAG cannot toggle at all (V289 proved exactly this reasoning on r62/r63,
§3 of `V289-QLIVE-R62-R63-2026-09-09.md`).

**MUST NOT MOVE:**

| bit | what it is | V282 r39 | V288 r5e | V289 r62 / r63 | V290 requirement |
|---|---|---|---|---|---|
| **b0–2** | stock Honda frame builder | 1.000 | 1.000 | 1.000 / 1.000 | **1.000** — any other value means our tail mask (0x57) is wrong and the frame is corrupted. FAIL-A, do not score anything else. |
| **b4** | V282 `sign(r24)`, untouched | 0.404 | 0.404 | 0.389 / 0.433 | **0.36–0.47.** Stable across four routes and three builds; a move means the 0x14A cave or the r24 lane was disturbed. |
| **b6** | V282 `\|r24\| ≥ \|T\|`, untouched | 0.114 | 0.146 | 0.149 / 0.228 | **reported, not scored** — regime-dependent, per V289's own honesty ledger. Non-zero and non-unity is all that is required of it. |

**A second, sharper control that costs nothing:** `b3` and `b7` are computed from the same `x` in the
same tick, so `P(b3 | b7 = 1)` and `P(b3 | b7 = 0)` must differ in the direction the calibration
predicts (conditional read *lower* than the unconditional, because b7 = 1 selects frames with real
low-frequency-band signal). If they are equal, the cave is reading noise.

---

## 5. THE SENTENCE A NULL LICENSES — written out

> **NULL:** *"`b5` sat at 0.40–0.46 engaged with a 21.5 Hz spectral peak coherent with the 0x18F wheel
> rate, and 0.18–0.32 disengaged — so the notch cave executed on every tick and removed real
> notch-band content from the rate operand. `b7`'s symptomatic duty fell from V282's 0.68 to X — so
> the loop's feedback operand carried [less / the same] 12–37 Hz energy. And yet the 15–22 Hz line on
> the wheel rate, the driver torque and the 427 tap is unchanged in frequency and in decay at the
> operator's marks. ⇒ Filtering the loop's feedback operand at the crossing does not change how long
> the mode rings. Since V288 rev 2 already closed the reference side (a setpoint pre-filter flew, the
> grinding was unchanged) and V289 closed the loop-output side (a notch on S relocated the crossing
> instead of damping it), **the in-loop linear-filter class is CLOSED at all three of its
> injection points** and the next lever must be a gain/schedule lever (the scheduled Kd rows S / S′ of
> the decision table) or something outside this loop entirely."*

> **FAIL branch, pre-registered:** *"a NEW line at 24–30 Hz, or the 15–17 Hz line moving again rather
> than shortening ⇒ the notch relocated the crossing a second time, the same failure mode as V289 →
> REVERT."* Note the notch removes 67–74 % at 15–16 Hz, so if the line stays at 15–17 Hz *and* b7
> reads healthy, that is the strong form of the null above, not a relocation.

> **HF branch:** *"`P(b3 | b7 = 1)` ≥ 0.20 engaged ⇒ the rate operand carries material content above
> ≈ 50 Hz that no 100 Hz instrument in this kit could see; the decision table's ×2.21 rms|R| over
> 30–500 Hz for the 50 Hz feedback pole is real rather than a modelling artefact, and the 40 Hz
> variant (×1.91) or a retreat to 25 Hz is indicated regardless of what the ring did."*

**Is any of this "we could not tell"?** No. The three branches partition the outcome space: b5
decides whether the cave ran; b7 decides whether there was band energy to remove and whether it fell;
the wire decides whether the ring shortened; b3 decides whether the pole's HF cost is real. **Every
combination of those four reads maps to a sentence above.** The one thing this build cannot decide is
*why* the mode rings if it is not the loop — that is the next session's question, and the null
sentence says so explicitly rather than pretending otherwise.

---

## 6. DECODE NOTE FOR THE READER OF THE FIRST V290 ROUTE

**Bit semantics, CAN `0x14A` byte 4** (100 Hz; the FLAG is computed at 1 kHz and OR'd in atomically by
the frame builder, so all three of our bits come from the *same* 1 kHz tick):

```
 bit 7  (0x80)  |n| >= 16          n = x - y, the notch's removed component, raw rate counts
 bit 6  (0x40)  |r24| >= |T|       V282, UNTOUCHED — regime-dependent control
 bit 5  (0x20)  n < 0              the removed component's SIGN — the liveness bit
 bit 4  (0x10)  sign(r24)          V282, UNTOUCHED — the stable control (0.36-0.47)
 bit 3  (0x08)  |d2| >  |d|        d = x-x_prev, d2 = d-d_prev; STRICT >; the >50 Hz detector
 bits 2-0       STOCK HONDA        must read 1.000
```

**Scoring rules:**
1. **Engaged = LATERAL engaged** — `0x18F` steer-control-active **AND** `0xE4` STEER_REQUEST. A
   longitudinal-only engagement is a confound (`feedback-engaged-means-lateral-engaged…`).
2. **Score b7 and b3 ENGAGED-ONLY.** Score `P(b3 | b7 = 1)` as the primary HF read, not b3's
   unconditional duty.
3. 🛑 **UNLIKE V289's cave, this one runs while DISENGAGED**, because hook `0x28F4C` sits above the
   engagement guard. **That is itself a control, not a nuisance**: b5's disengaged duty must be
   0.10–0.40. Do **not** carry over V289's rule that b7 reads 1.000 while disengaged — that was an
   artefact of V289's `|S−y| ≥ |y|` reading `0 ≥ 0` on a frozen S. Here b7 = `|n| ≥ 16` goes to **0**
   as x decays to zero, and b3 (strict `>`) goes to **0** as well. **At a standstill with the cave
   running, expect (b3, b5, b7) = (0, 0, 0);** a frozen FLAG instead holds whatever the last engaged
   tick wrote, so the two are told apart by whether the triple *changes* during the standstill.
4. Honda's disengage fade means the loop keeps running 1–3 s after SCA falls (V289 §3) — **do not
   treat SCA = 0 as "hook off" for the first 3 s.**
5. **Attribute the build from the TAP, not from the label** (r32/r33 were mis-filed). V290's
   signature is: b5 engaged **0.40–0.46** with a **20–23 Hz** spectrum **and disengaged 0.10–0.40**.
   V289 reads 0.500 / 20 Hz / ~0.00 disengaged; V288 reads 0.412 with 99.7 % agreement with the
   command sign; V282 reads 0.134. **No two of these overlap.**
6. Re-verify the image's cells from the built image before scoring: notch coefficients in the cave,
   `0xC63E8`/`0xC63EA` = the chosen pole pair, and the two CRC words.

**Residual, stated:** the operand-refresh rate is unresolved (§1.5). If the on-car b3 unconditional
duty comes back ≈ 0.09 *and* the conditional ≈ 0.09 with almost no spread, that is the signature of a
100 Hz staircase (`d == 0` on 9 of 10 ticks makes the strict `>` fail on ties); if the unconditional
duty is ≈ 0.17–0.19 it is the signature of a genuinely faster refresh. **This is a bonus read, not a
designed test** — I could not find a one-bit discriminator that survives the LSB floor, and I am not
claiming one.

---

## 7. CAVE BUDGET

**RAM** — five words in the certified free run `gp-0x6D74 .. gp-0x6D2D` (72 B, boots to zero, zero
hits under the 9-form scanner plus the absolute-pointer and `movhi`/`movea` checks;
`TRACE-…-postlag-hook-rate-operand-ram.md` Q3):

```
 gp-0x6D74  s1      int32   notch state 1
 gp-0x6D70  s2      int32   notch state 2
 gp-0x6D6C  e       low halfword  (0..16383, masked with andi 0x3fff on load)
 gp-0x6D6A  FLAG    high halfword of the same word — the telemetry handoff, values in
                    {0, 0x08, 0x20, 0x28, 0x80, 0x88, 0xA0, 0xA8}
 gp-0x6D68  x_prev  int16   (padded to a word)
 gp-0x6D64  d_prev  int16   (padded to a word)
```

20 of the 72 bytes used. All boot to 0, so the first-tick state is well defined; the notch is stable
and driven by a bounded input, so no engage-init is needed (same argument as V289's, and stronger —
this hook is on the tick path unconditionally, so there is no skip to recover from).

**Instruction count and cost** [BELIEF for the cycle figures, EVIDENCE for the instruction counts,
which are counted from the listing]:

| block | instructions | notes |
|---|---|---|
| displaced `ld.h -0x6a56,gp,r7` | 1 | done first; `x` also kept in `r11` (free at the hook) |
| notch recursion (V289's, unchanged in shape) | ≈ 23 | 3 `mul`, 6 RAM accesses |
| ±12000 output clamp | ≈ 7 | guard rail; measured never to bind (§1.1) |
| **b5** `n < 0` | 4 | |
| **b7** `\|n\| ≥ 16` | 6 | (4 at T = 12, which fits `cmp imm5`) |
| **b3** `\|d2\| > \|d\|` | ≈ 16 | 4 RAM accesses, two `abs` idioms |
| FLAG assemble + `st.h` | 4 | one atomic halfword store |
| `jr` home | 1 | |
| **total** | **≈ 62** | ≈ 190 bytes of the 868 free at `[0xC4C8C, 0xC4FF0)` |

**Telemetry is ≈ 30 of those 62 instructions** — roughly half the cave, which is the right ratio for a
build whose whole point is to be interpretable. At PCLK 40 MHz (`SPEC-V288…` §; the 80 MHz derivation
is refuted) and ≈ 2 cycles/instruction, **≈ 125 cycles ≈ 3.1 µs, ≈ 0.31 % of the 1 ms tick** —
the same order as V289's declared ≤ 3 µs / 0.3 %. 🛑 The tick's actual slack has still never been
measured; this remains BELIEF, as it was for V289 and V288.

**Registers.** The cave needs 5 (`r6, r7, r8, r9, r13`) plus `r11` to carry `x` past the recursion.
The hook's free-scratch census gives **r1, r6, r8, r9, r11, r12, r13, r16, r21, r26, r28** — no
liveness claim has to be created, and the comparator's two-operand form (the V96 buildability note)
is affordable without recomputing operands inside each rung.

**The 100 Hz FLAG rung** — V289's `telemetry_rung` at `0xC4BD6`, unchanged in mechanism, **two mask
constants and one displacement changed**:

```
 ld.hu -0x6d6a[gp],r7      ; FLAG  — one atomic halfword load (was -0x6c3a)
 andi  0xa8,r7,r7          ; keep bits 7,5,3 ONLY            (was 0xa0)
 ld.bu -0x1514[gp],r6      ; 0x14A byte 4
 andi  0x57,r6,r6          ; clear 7,5,3; keep stock 0-2 and 6,4  (was 0x5f)
 or    r7,r6
 st.b  r6,-0x1514[gp]      ; runs AFTER the flown rungs, so it wins
 movea -0x1518,gp,r6       ; relocated epilogue
 jmp   [lp]
```

8 instructions at 100 Hz — negligible. The build must assert, as V289's did, that `0x55AC0` /
`0x55AE8` / `0x55B06` are the only stock writers of bits 0–2 and that mask `0x57` clears exactly bits
7, 5, 3 and preserves 6, 4, 2, 1, 0.

---

## 8. WHAT THIS DESIGN DOES **NOT** CLAIM

- It does not claim the notch will fix the grinding. The decision table predicts **shorter, not
  gone** (582 → 424 ms), and §5's null sentence is written for the case where it does neither.
- It does not claim to locate the line. The wire does that far better; the cave bits are deliberately
  *complementary*.
- It does not resolve the operand-refresh rate (§1.5, §6 residual).
- The b3 calibration curve is synthetic plus a 100 Hz-derived null; the on-car number **is** the
  measurement, and if it lands between 0.13 and 0.20 the honest answer is "inconclusive on the HF
  cost, re-read on the next route with the same bit".
- **The duties in §2 are computed with a byte-exact mirror of the intended cave arithmetic, driven by
  the 100 Hz wire copy of the operand — not from a built image.** Once V290 is built, the build's own
  emulator must reproduce them from the emitted bytes, and any disagreement is the build's to explain.
