# HANDOFF 2026-08-22 — V104 FLEW AND FAILED · THE 26 Hz MODE IS THE TARGET · V105 IS A 25.5 Hz NOTCH

🛑 **ON THE CAR: V104** (route `a4`). **V105 is BUILT, VERIFIED, UNFLASHED.**
🛑 **Nothing was flashed this session. No CAN. No UDS.**

---

## 0. THE ONE-PARAGRAPH VERSION

V104 flew as route `a4` and **fixed nothing** — the operator's verdict on both symptoms. Its dose
provably arrived (**1.824×**, predicted 1.66–1.85) and it still produced no felt change, which closes
the `c4` flat-gain lever. Scoring `a4` at **the operator's own window (<16 km/h)** — a methodological
correction he supplied — found **one mode at 21–28 Hz that is essentially CONTINUOUS at 6× and ABSENT
on stock** (burst duty **0.056 vs 0.93–0.95**, longest burst **0.69 s vs 7–14 s**, disjoint CIs), and
that **no lever on V104 touched.** A structural analysis then showed **every in-loop low-pass fails
GATE 2 on phase** and **a NOTCH is the only shape that survives** — so V105 retunes Honda's own dormant
biquad from its 55 Hz notch to **25.5 Hz**, four floats, pure cal, zero blast radius, DC held at unity.
Along the way the operator's own LKAS-contamination hypothesis was **cleanly refuted** by a partial-
coherence test nobody had run, and **the 26 Hz mode was found to be driven by STEERING RATE, not speed**
— ~90× stock at 15–40 °/s, collapsing to stock above 100 °/s.

---

## 1. WHAT IS ON THE CAR — V104, and both docs were WRONG about it

🛑 **`docs/STATE.md` and `docs/BUILD-LINEAGE.md:26` both said "V104 — BUILT, NOT FLASHED. V103 IS ON THE
CAR." Both were STALE.** The operator flashed V104 and drove it as route `a4`. **This is the SECOND
consecutive build where the record was wrong about what is on the car** (V103's own block said "built,
not flashed, decision deferred" while it was being driven).

⭐ **And it was settled from the TELEMETRY, not from a document or a report:** route `a4` carries **57
frames with a CAN-427 wire code > 800**, max **850**. V103/V102's packer is `|gp-0x6b4c|·5>>6` against a
±10240 writer clamp ⇒ **structural ceiling 800**; observed max on `0x9e` was 117. **A code of 850 is
arithmetically impossible on V103.** ⇒ **the build on the car during `a4` is V104, proven from the wire.**

**Lesson, now standing: verify the flown build from the telemetry, never from the record.**

---

## 2. ROUTE `a4` — THE BEST CAPTURE IN THE CORPUS

```
938.1 s total · ENGAGED 670.4 s (71.6 %) in 8 episodes, longest 255.5 s
engaged median 50.05 km/h · >=50 km/h 336.1 s · >=80 km/h 140.4 s (2 runs) · max 113.3 km/h
engaged by band: 0-5 19.7s · 5-20 126.3s · 20-50 188.3s · 50-80 195.7s · 80+ 140.4s
FAULT-FREE: 0 sentinels, DTC bit2 duty 0.00000, STEER_STATUS {0: 93618, 3: 7}, CONFIG_VALID 1.0
```
Cache `analysis-2020accord/_cache_ra4/ra4.npz`, 99 keys, 93,624 rows. Identity passes both legs.

---

## 3. THE OPERATOR'S REPORTS — verbatim, and they drove the whole session

> *"On this route, both grinding and ratcheting are still an issue."*
> *"I would say this route is just as bad as any other 6x before it, I don't think I could tell the difference."*
> *"I also did not feel any [change in] normal, manual, LKAS-disengaged OR LKAS-engaged steering feel."*
> *"I wonder if the normal steering feel tracker is compensating for this hence why I cant feel it."*
> *"Structurally this is all related to LKAS unexpectedly feeding into the driver torque signal and this not being accounted for."*
> *"I think the grind #3 at high speed is also somehow resulting in a lower ratcheting-like mode of oscillation on the highway."*
> *"1 Hz is too slow to match my observation."* → placed it at **"several per second (~6–12 Hz)"**
> *"But its not a clean singular oscillation its like a ratchet ontop of a higher frequency vibration."*
> *"Its like vibration comes in and out while highway driving and the ratchet-like oscillation shows up on top of it when its happening sometimes."*
> *"Ok if you say grinding improved I was not able to observe this. I hope you are measuring in the right windows (low speed < 10 mph)."*
> *"Most I would expect from audio is maybe grind #1, #2, or #3."*

🛑 **VERDICT: BOTH SYMPTOMS UNFIXED. GRINDING UNFIXED — his words override any band statistic.**

---

## 4. V104 SCORED — the dose arrived and the lever is dead

### 4.1 THE DOSE PROVABLY ARRIVED
Within-drive, `|gp-0x6b86|` engaged vs manual, binned by `|tq|` **AND speed** (5–20 km/h overlap):
**pooled median ratio 1.824×**, predicted 1.66–1.85. ✅
🛑 **A trap that would have inverted the verdict:** the pre-registration's literal `|tq|`-only binning
returns **0.600 / 0.760 / 1.000 / 1.000 / 1.429** ⇒ *"≈1.00, the edit is not in force"* — because
**`a4`'s manual arm is 74 % PARKED** and the assist map is **speed-scheduled** (~2× steeper at parking).
**Anyone running §6.4 as written would have reported an arm failure on a perfectly delivered dose.**

### 4.2 CLIPPING — CANDIDATE (d) IS DEAD
`|gp-0x6b86|` engaged p50 **25.6** · p99 2186 · **MAX 2720** vs the ±12288 clamp ⇒ **4.5× clear**,
duty at 90 % of clamp **0.000000**, 427 field saturation **0.000000**. **No clipping, no relay.**

### 4.3 🛑 THE 6–9 Hz RESULT DOES NOT SURVIVE THE OPERATOR'S WINDOW — a withdrawal
```
V104/V103 at 6-9 Hz      raw [CI]              placebo-corrected
0-40 km/h  (reported)    0.445 [0.24, 0.66]          0.63
< 20 km/h                0.58  [0.29, 0.77]          0.85
< 16 km/h  (HIS WINDOW)  0.69  [0.30, 0.96]          0.86
< 10 km/h                1.07  [0.30, 1.64]          1.29   <- WORSE, CI spans 1
```
⭐ **And the tighter window is the BETTER-CONTROLLED one** — `a4`'s own split-half at 6–9 Hz is **2.14
at 0–40** but **0.71 at <16**. **The window originally reported was the one whose internal control was
worst.** ⇒ **"the band responded, therefore the lane was not rejected" is NOT SUPPORTED.**

### 4.4 THE DRIVE-LEVEL OFFSET IS REAL
The 32–45 Hz placebo (V104/V103) is **0.83 / 0.80 / 0.68 / 0.71** at <10 / <16 / <20 / 0–40 — it
**persists at every window**, so `a4` is genuinely a quieter drive than `r9e` across 6–45 Hz.
⇒ **PLACEBO CORRECTION IS MANDATORY on every V104-vs-V103 number.**

---

## 5. ⭐⭐ THE FINDING — ONE MODE AT 21–28 Hz, AND IT IS A STEERING-RATE PHENOMENON

### 5.1 IT IS ESSENTIALLY BINARY BETWEEN STOCK AND 6×
Engaged, **<16 km/h**, pre-declared Schmitt detector (THR_ON = p95 of stock's engaged envelope,
THR_OFF = 0.70×, MIN_BURST 0.25 s, MERGE_GAP 0.15 s, **true analytic envelope**):
```
                  burst duty [95% CI]     in-burst A     longest burst
STOCK 1x          0.056 [0.000, 0.149]      1.23           0.69 s
V102  6x          0.945 [0.836, 1.000]      9.43           7.43 s
V103  6x          0.948 [0.892, 1.000]     15.71          11.23 s
V104  6x          0.933 [0.874, 0.970]      4.32          13.91 s
```
🛑 **Stock never sustains it for one second. The 6× builds run 7–14 s bursts and are "on" 93–95 % of
the time. Disjoint CIs.** ⇒ **at low speed the mode is CONTINUOUS at 6× and ABSENT on stock.**
**No V104-vs-V103 comparison resolves** — the three 6× builds are indistinguishable on duty and on
in-burst amplitude (CIs heavily overlapping). **No lever on V104 touched it.**

### 5.2 TWO REGIMES, AND THE OPERATOR DESCRIBED BOTH PRECISELY
```
BURST DUTY      < 16 km/h    40-80 km/h    80-95 km/h
STOCK             0.056        0.045         0.054
V102  6x          0.945        0.361         0.459
V104  6x          0.933        0.528         0.736
```
⇒ **continuous at his grinding window; genuinely INTERMITTENT at highway (36–74 %).** His *"vibration
comes in and out while highway driving"* and his low-speed grinding are **two regimes, and we had been
pooling them.**

### 5.3 ⭐ IT IS DRIVEN BY STEERING RATE, NOT SPEED — the largest separation in the corpus
Median 21–28 Hz level, engaged, <16 km/h, rate corrected by 1/0.7996 to true deg/s:
```
             0-5 deg/s   5-15    15-40    40-100    100+
STOCK 1x        0.12      0.30    0.24      0.48    0.57
V102  6x        0.92      8.27   24.31     25.56    0.57
V103  6x        1.71     13.79   21.64     20.01    0.67
V104  6x        1.17      4.78   20.79     14.47    0.76
```
🛑 **~90× stock at 15–40 °/s · only 8–14× at 0–5 °/s · COLLAPSES TO STOCK above 100 °/s.**
⭐ **This independently corroborates the operator's own earlier claim** — *"applying torque kills the
buzz"*, previously measured at **16.12× [5.29, 41.29]** — from a different direction.

**THE OPERATOR-CONFIRMABLE SENTENCE:** *"Below about 16 km/h, whenever you are steering at a moderate
rate — roughly 15–40 °/s, not gentle and not a hard turn — there is a 21–28 Hz oscillation running
almost continuously, about 90× stronger than stock, in bursts of about half a second separated by
tenth-of-a-second gaps. It fades as you speed up and vanishes if you turn hard."*
🛑 **NOT claimed to be "grinding" — that is his word and his call.**

### 5.4 🛑 DUTY SATURATES AT 4× — a scoring correction that would have cost the next drive
```
build   gain   burst duty   in-burst LEVEL
STOCK    1x      0.072          0.883
V100     4x      0.824          2.250
V102     6x      0.804         14.151
V103     6x      0.882         14.885
V104     6x      0.845         11.274
V101     8x      0.894         18.625
```
**Duty saturates at 4× (0.82 → 0.89); LEVEL climbs 21× to 8×.** ⇒ **above 4× the gain sets AMPLITUDE,
not INCIDENCE. Any build scored on duty above 4× is scoring a saturated variable.**
🛑 **V105 MUST BE SCORED ON IN-BURST LEVEL, NOT DUTY.**

### 5.5 WHEEL ORDER EXCLUDED
Per-window regression of the in-band peak on speed: **`f_peak = −0.027·v + 27.4`, R² = 0.039** on `a4`
(and `+0.055·v + 27.6`, R² = 0.037 on stock) against the **0.962 (order 2) / 1.442 (order 3)** a tyre
order requires. **The peak does not move with speed. It is a fixed mode.**

---

## 6. THE STRUCTURAL RESULT — WHY A NOTCH IS THE ONLY SHAPE LEFT

### 6.1 THE JUNCTION / REJECTION TOPOLOGY [EVIDENCE, fresh decompiles]
`FUN_0003aa2c` (aggregator) sums `gp-0x6ad4` (the PID's own output), `gp-0x6b86` (the biquad lane),
`gp-0x6b26`, `gp-0x6bbe`, `gp-0x6bd0`, and r24/r26 via `iVar21`/`iVar16` — **all sibling addends at ONE
junction.** `FUN_00037fe6` builds the reference `gp-0x6ad6` from **8 other, LKAS-derived terms** and is
**architecturally blind to all of them**. Feedback is the **physical column-torque sensor `gp-0x4f60`**
via `FUN_0003a382`.
⇒ **every hand-feel lane this kit has ever edited is a DISTURBANCE, not a reference.**
⚠ **QUALIFIER:** at 6–9 Hz this is **NOT quiet rejection — it is measured AMPLIFICATION (2.28×, gain
margin 1.2–1.6)**, reconciled by the **4:1 (6–9 Hz) vs 1.68:1 (21–22.5 Hz) lane:sum cancellation law**,
which also retrodicts why **V62/V88 (15–22 Hz) are the only two wins in sixty builds.**

### 6.2 🛑 EVERY IN-LOOP LOW-PASS FAILS GATE 2 ON PHASE
```
1-pole corner   |H(26 Hz)|     phase @26 Hz     phase @3 Hz
   15 Hz          0.500          -60.0            -11.3
   10 Hz          0.359          -69.0            -16.7
    5 Hz          0.189          -79.1            -31.0
```
**Gain margin 1.2–1.6 = only 1.6–4.1 dB. Even −6 dB at 26 Hz costs −60°.**
⇒ **CLEAN STRUCTURAL KILL: there is NO corner high enough to be safe and low enough to matter.**

### 6.3 ⭐ A NOTCH BREAKS THE TRADE — its phase returns to zero at its own centre
`−23 dB at the mode for −0.1 dB and −8.6° at 3 Hz.` **And this firmware already has one, already armed
by V103/V104.** It just sat at 55 Hz.

### 6.4 COMMAND-PATH FILTERING CANNOT WORK
The mode is **SELF-EXCITED** — `f0` = **21.90 / 23.61 / 24.90 Hz at 1× / 4× / 6×**. **A driven response
does not move its frequency with loop gain; a closed-loop pole does.** ⇒ feedforward filtering cannot
starve it. ⊕ And **Route B**: `gp-0x6b4c` reaches the aggregator **DIRECT at `0x3AA3E`**, bypassing the
5.05 Hz arbitration IIR — which resolves the long-unexplained 0.71–1.06 attenuation discrepancy.

---

## 7. V105 — BUILT, VERIFIED, UNFLASHED

| artifact | SHA256 |
|---|---|
| `_v105_…NOTCH25.5HZ…_plain_image.bin` | `2666a000415a29fef98ac9cd6c183536269c3e61a61fc822c17586f2adde7e00` |
| `39990-TVA,A160-V105-…NOTCH25.5HZ….rwd` | `5592f7ca52d07247152e5930c579b6ba35e2f5fa5a3adcafcb08b95fff6c89a8` |

**Base V104. 24 bytes differ in 8 runs: 4 coefficient runs + 2 cave halfwords + 2 CRC trailers. ZERO
unattributed.** 165/165 assertions, 3 runs to identical SHA256, both SHAs hard-asserted.

### 7.1 EDIT 1 — the notch, four floats, PURE CAL
```python
R_POLE, F_POLE, F_ZERO, FS = 0.950, 22.0, 25.5, 1000.0
a1 = -2*R_POLE*cos(2*pi*F_POLE/FS)   # -1.8818767088236372  0xC60A8  56e1f0bf
a2 = R_POLE*R_POLE                    #  0.9025              0xC60AC  3d0a673f
b1 = -2*cos(2*pi*F_ZERO/FS)           # -1.9743840279896383  0xC60B0  9eb8fcbf
c4 = (1+a1+a2)/(2+b1)                 #  0.8050950074438165  0xC60B4  b51a4e3f
```
```
notch 25.499979 Hz |z|=1.000000000 (a TRUE null)   pole 21.999984 Hz r=0.949999986 STABLE
H(0) = 0.999999581      max|H| over 0-500 Hz = 0.999999564   <- NEVER reaches unity anywhere
|H|  7.79 0.9863 · 20.0 0.5893 · 21.73 0.4150 · 24.0 0.1601 · 24.9 0.0621 · 25.5 2.09e-6
     26.8 0.1229 · 42.3 0.6801            tau 19.496 ms, 99% ring 89.7 ms
```
**BLAST RADIUS ZERO:** each cell has **1 reader, 0 writers**, all four inside a 40-byte window
(`0x035A30`–`0x035A58`), and **0 `movea`/`movhi` hits on the imm16s** ⇒ nothing can reach them by
absolute addressing either.

### 7.2 EDIT 2 — the `b6` probe, 4 bytes
`0xC4B36` `2695`→`6c94` · `0xC4B42` `2495`→`9cb0` ⇒ **`b6 = |gp-0x6b94| ≥ |gp-0x4f64|`** — aggregator
sum versus governor ceiling, **a live duty readout of the governor clamp**, on the wire for the first
time. `b5` UNTOUCHED. Cave 164 B, PASS2/PASS3/BYTE7/RET byte-identical, RET sole exit and last.

### 7.3 WHY 25.5 AND NOT 26.0
**The mode's own −3 dB bandwidth is `f/Q` = 0.90–1.86 Hz** — it is not a tone, so **band coverage beats
a point-null**. 25.5 wins at every rung of the ladder (**21.90 / 23.61 / 24.90 Hz**) and straddles the
two disagreeing estimates (`f0` says 24.90 at 6×; `a4` scores the peak at 26.0–26.8):
```
mode at    centre 26.0    centre 25.5
21.90 Hz     -7.2 dB       -8.0 dB
23.61 Hz    -12.0 dB      -13.8 dB
24.90 Hz    -19.1 dB      -24.1 dB
worst over 24.0-27.1 Hz:  0.216  vs  0.160
```

### 7.4 THE COSTS, STATED
- **42 Hz gets 1.75× worse** (0.385 → 0.680).
- **Engagement ring 20 ms → 90 ms** — the operator may feel a soft settle when LKAS grabs.
- **6–9 Hz costs 2.7–5.1° of extra lag**, magnitude essentially unchanged (0.9863 vs 0.9829).
- **`c4` 1.512023 → 0.805095 is FORCED by the unity-DC constraint**, landing 1.5 % from stock's
  0.817310. **V104's ×1.85 boost is reverted as a consequence** — a measured null, not a confound.

### 7.5 VERIFICATION — three-control harness, independent of the builder
**PASS, 0 failures.** All four coefficients tagged **exact-formula**; **five transfer-function deltas
EXACTLY ZERO**, not merely inside tolerance. Harness control-tested against **V104 (16 correct FAILs)**,
the **superseded 26 Hz build (11 correct FAILs, 0 false positives)** and a **synthetic-correct build
(0 FAILs)**. Ghidra's own decoder independently confirms both repointed loads, after **anchoring** the
cave extract with `image.find(blob)` → `0xC4B34`. **Two independent legs, agreeing on every quantity.**

---

## 8. THE OPERATOR'S OWN HYPOTHESIS — TESTED AND REFUTED, CLEANLY

His claim: *"LKAS unexpectedly feeding into the driver torque signal and this not being accounted for."*

**The test nobody had run: partial coherence `γ²(e4, bar | angle)`** — the command→bar relationship with
everything predictable from steering angle removed.
```
route  gain   g2 ordinary (e4,bar)        g2 PARTIAL (e4,bar|ang)
r97      1x   0.0768 [0.040, 0.126]       0.0006 [0.0001, 0.0164]
r96      6x   0.3470 [0.210, 0.552]       0.0165 [0.0005, 0.0691]
r9e      6x   0.2302 [0.097, 0.441]       0.0028 [0.0003, 0.0569]
ra4      6x   0.5142 [0.191, 0.676]       0.0027 [0.0003, 0.0328]
r95      8x   0.3302 [0.266, 0.479]       0.0134 [0.0025, 0.0599]
```
🛑 **Ordinary coherence rises with gain; partial coherence is FLAT and at or below its own shuffled null
on all five routes. It does NOT scale with `0xC6CD0`, which his hypothesis requires.**

⚠ **HONEST LIMIT:** if the contamination is **collinear with the angle response** — which it partly
would be, since both flow through the same mechanics — partialling out angle removes it too. **Strong
evidence, not proof.**

⭐ **The architectural answer is stronger and independent: there is no decoupler because there cannot be
one.** A torsion bar measures the **differential twist** between the driver side and the motor side, so
motor torque appearing there is **the sensor's operating principle, not an oversight**. Subtracting it
would need the exact mechanical transfer *and* the instantaneous hand impedance, which varies with grip
frame to frame. **Honda's answer is the closed loop itself, tuned to stay stable while reading a signal
that inherently includes some of its own output.**

**Three concrete decoupler candidates were traced and all three refuted:**
- **`gp-0x6b4a`** — sole writer `FUN_00026c80`; `gp-0x4f60` never appears in it; built from a 10-slot
  arbitration accumulator plus **speed-voted** (`gp-0x6a62`) slew/LERP terms. **Speed-derived, not
  torque-derived.** Its range gate at `0x35504` is a **NO-OP** (the producer clamps to exactly the range
  the test admits) ⇒ it is added **unconditionally, every tick, coefficient +1**. **And the addition
  happens INSIDE `gp-0x6b86`'s own computation — the exact lane V104 proved is rejected**, so the sign
  question is moot.
- **`cal(0xC616C)` = 0** — its 3 readers are all in `FUN_00033d10`, feeding a **self-closing diagnostic
  loop** (`FUN_00033d10` → `FUN_0003405a` → `FUN_00025c32` → `FUN_0002cc2a` → back to the gate) that
  never reaches the aggregator, PID, reference or `gp-0x6b98`. **A torque-plausibility/driver-override
  confirmation timer, not an assist term.** Its NEVER-RAISE status is now explained: raising it changes
  a **fault detector's** sensitivity.
- **`cal(0xC63CC)` = 0** kills the shared-source theory (`gp-0x6b4a` ∝ −`gp-0x6b4c`) outright.

---

## 9. THE ACOUSTIC WORKSTREAM — a new instrument, and what it can and cannot do

⭐ **Every drive in the corpus carries CONTINUOUS 16 kHz PCM** (`rawAudioData`, 800 int16/block,
20 blocks/s), on **all six routes**, coverage 0.83–1.00, gapless to 0.1–0.5 %, clipping 10 samples in
17.2 M on `r97` and **zero elsewhere**. **Nyquist 8000 Hz** against the CAN channels' ~25–50 Hz.
**Sixty builds were fought on instruments that go deaf above 50 Hz.**

### 9.1 🛑 THE MICROPHONE IS BLIND TO THE 21–28 Hz MODE — instrument failure, not a negative
Identical detector, both channels, engaged <16 km/h:
```
channel               STOCK   V102   V103   V104   separation
wheel rate 21-28 Hz   0.072  0.804  0.882  0.845    11.6x
ACOUSTIC   21-28 Hz   0.109  0.043  0.029  0.065     0.4x
```
In-burst level: wheel rate **0.88 → 18.63** across the ladder; **acoustic FLAT at 380–510 on every
build.** Envelope correlation r(log) = −0.13…+0.05, every value inside its surrogate CI.
⚠ **21 Hz is a ~16 m wavelength and a steering rack is a hopeless radiator there — the direct-radiation
null is close to PREDICTED physics, not evidence of absence.**

### 9.2 BUT THE MIC IS ALIVE IN THE AUDIBLE RANGE — so the 100 Hz–8 kHz null IS real
Speed control **PASS decisively** (0.14–0.28 dB per km/h through 100–1600 Hz). Turn-signal control
**PASS on `r97`** (localised 1.2–2.2 Hz envelope bump, z ≈ 3.8–4.4).
⇒ **No third-octave band from 100 Hz to 8 kHz separates stock from 6×.** The three 6× builds disagree
with each other by up to **36×** in the same band.

### 9.3 🛑 AND ABSOLUTE ACOUSTIC LEVEL IS NOT COMPARABLE ACROSS DRIVES
**Parked, engine on, LKAS off, v < 1 km/h — no tyres, no wind, no steering — the cabin sounds 3–12×
different between drives.** Difference-in-differences: **corr(log E, log M) = +0.836 / +0.914 / +0.919**.
⇒ **the between-route acoustic contrast is STRUCTURALLY UNAVAILABLE, not merely null.** Fixing it needs
a per-drive reference clip (parked, engine on, HVAC off, windows up, 30 s at the start of every drive).

---

## 10. RETRACTIONS AND CORRECTIONS

| # | what was wrong | corrected to |
|---|---|---|
| 1 | 🛑 *"V104 is unflashed, V103 is on the car"* — **`STATE.md` AND `BUILD-LINEAGE.md:26`** | **V104 FLEW as route `a4`**, proven from telemetry. Second consecutive build with a stale on-car record |
| 2 | orchestrator: *"V103 changed the lane 1.7 % at 7.79 Hz; V104 is 49× larger"* | **a magnitude-only read of a COMPLEX quantity.** `arg H = −10.61°` ⇒ `\|H−1\|` = **18.4 %**, ratio **4.54×**. **Third time this kit has made this error on this cell** |
| 3 | orchestrator: *"the rejection loop swallows lane perturbations"* | **NOT SUPPORTED** — it rested on a 6–9 Hz result that dies at the operator's window (§4.3). **Candidate (c) is OPEN** |
| 4 | orchestrator: *"P and I are net pumping at 6–9 Hz, D is the lone damper"* | **BACKWARDS.** `gp-0x6752` = −1 multiplies the whole combine ⇒ **D PUMPS, P and I DAMP.** Also kills the `Kd`-raise idea |
| 5 | orchestrator: *"pooling DILUTES the symptom ~6×"* | **at low speed it INFLATES it ~12×** — a 6× arm on 95 % of the time against a stock arm on 5.6 % |
| 6 | orchestrator: *"your ratcheting is a 2× problem"* (from 2.03× at 0–40 km/h) | **an artifact of the window in BOTH directions**: 23× at highway, 4–5× at <10 km/h. **The 2.03 reference is RETIRED** |
| 7 | orchestrator: *"the 10.4× ceiling collapse is the mechanism"* | **9.30×, not 10.4×** (`0xC6202`=4762 is a MIN, not a ×4.65 gain), and X=4100 ≈ 870 °/s is a corner ordinary steering never visits |
| 8 | orchestrator: *"`gp-0x6b4a` is a dormant, cal-disabled adder gated by `0xC616C`"* | **Neither dormant nor cal-gated.** The gate is a hardcoded range test that is a **NO-OP**; `0xC616C` gates a different, diagnostic chain |
| 9 | orchestrator + verifier: *"the builder repointed `b5`"* | **FALSE ALARM.** A **headerless blob's file offsets are not image addresses**. The builder had `b6` right throughout |
| 10 | orchestrator: *"the builder kept the convention; keep both prefixed"* | **I overruled it and it deleted on my instruction.** Credit misdirected; corrected on the builder's own insistence |
| 11 | *"grind #3 is the 2nd harmonic of the 21 Hz mode"* | **REFUTED 4 ways** — phase locking null, a 1.65× non-harmonic control identical, amplitude scaling 7× wrong (fundamental 13.6×, "harmonic" 1.93×), and the π-ambiguous parametric variant also null |
| 12 | *"the ~1 Hz authority ramp explains the ratchet"* | **Operator: "1 Hz is too slow."** Ruled out on the primary evidence |
| 13 | agent: *"low-speed is 61–65 % of engaged time"* | **`cs_v` is m/s, not km/h.** Corrected to **~16 %** |
| 14 | agent: *"the biquad cannot amplify, peak \|H\| = 1.0000"* | **TRUE-BUT-STALE** — correct at stock `c4`, trivially false at V104's (peak 1.85006) |
| 15 | *"duty is the headline separator"* | **Duty SATURATES at 4×.** Above that the gain sets amplitude. **V105 must be scored on LEVEL** |
| 16 | *"reviving `cal(0xC63CC)` gives a free LKAS slew limiter"* | **Retracted by its own author** — the rate-limited state is an **additive term**, so enabling it ADDS content |
| 17 | *"`gp-0x67fa` is a constant 5 while driving"* | **UNSOURCED and provably unreachable.** Use **{4, 11}**. No downstream consequence (bit 11 is in every mask) |
| 18 | *"a 6-dp decimal specifies a float32"* | **It does not.** `a1` needs 8 significant digits, `b1` needs 9. **The FORMULA is the specification** |

---

## 11. OPEN ITEMS — with what closes each

| # | item | what closes it |
|---|---|---|
| 1 | **Is the rejection loop real?** Candidate (c) reopened by §4.3 | a build that moves `c4` ALONE — a 4-byte edit |
| 2 | **`chanA` may start near zero on engagement** ⇒ `b6` under-reports for up to 993 ms | trace the 3 lane targets `gp-0x693c`/`0x693a`/`0x6938`; needs Ghidra to define `0x44600–0x45700` |
| 3 | **The `Kd` sign at 26 Hz is unknown** — `0xC6AE6` = 2048, VIRGIN across ~95 images, `\|H_D\|` sensitivity exactly linear, but **firmware cannot settle the sign** | an on-car gain-step system-ID centred at 21–28 Hz, the same method as routes `0x85`/`0x95` |
| 4 | **The PID rails hands-on** (`AUTH ≈ 227 ct` vs median override **2235 ct**) ⇒ D sets a relay's switching instants. **A build-stopper on any `Kd` change** | decode the 3 anti-windup LERPs on `gp-0x6bda`/`gp-0x6a5e`/`gp-0x6966` in `FUN_0003a382` |
| 5 | **The mode's true centre** — `f0` says 24.90 at 6×, `a4` scores 26.0–26.8 | 25.5 straddles both; `b1` is one float if it needs re-centring |
| 6 | **`\|Z\|` rolls off un-modelled above ~13 Hz** ⇒ every kit `\|Z\|` above ~10 Hz inherits it, including the 21–26 Hz work | identify whether `tq` is internally low-passed near 13 Hz |
| 7 | **The 6–12/s ratchet has never been found in any channel** — 4 independent instruments null | a carrier nobody has identified; the **IMU (Nyquist ~50 Hz)** is the untried channel |
| 8 | **`gp-0x381c` / `cal(0xC6382)`** — a live, unconditional single-pole IIR whose LERP table at `tp+0x78fc..0x790c` was never decoded. **The one unsized damping candidate** | decode that table's axis and Y values |
| 9 | **`gp-0x6448`–`0x647x` may be a RAM COLLISION**, not a calibration block — `gp-0x6468` has a live writer in an unrelated module | trace the `FUN_0003d04c` cluster (17 call sites) |
| 10 | **Absolute acoustic level is not comparable across drives** | a per-drive parked reference clip at the start of every drive |
| 11 | **The `tq` discriminator is underpowered** — split-half null spans ±26–59 % on 6–8 episodes | more engaged low-speed exposure on both builds |
| 12 | **A single alternating-LKAS drive would remove the one-stock-route confound entirely** | ~30 s on / 30 s off at 5–15 km/h, same road, same session. **No build required** |

---

## 12. THE DRIVE CARD FOR V105

**PRIMARY:** 21–28 Hz **IN-BURST LEVEL** (not duty — §5.4), engaged, **< 16 km/h**, stratified by
steering rate with **15–40 °/s as the headline cell**. Reference: V104 on `a4` at the same window.
**Predicted: substantially reduced. The notch is −24.1 dB at 24.9 Hz.**
**SECONDARY:** `b6` duty = governor clip fraction — **the first time this has ever been on the wire.**
🛑 **DISCARD THE FIRST ~1 s OF EACH ENGAGED EPISODE** when scoring `b6`: the ceiling is scaled by an
authority ramp (`cal(0xC6492)` = 33 ct/tick ⇒ **993 ms** full traverse) that is **active above
`cal(0xC6316)` = 640 ct ≈ 10 km/h** — i.e. exactly at highway speed. **An early-episode `b6` = 0 is
uninformative, not headroom.** ⚠ 993 ms is a WORST-CASE bound (open item 2).
**DOSE GATE:** CAN 427 carries `|gp-0x6b86|` at `sar 4` — **`0x55DF2` = `0x7a` is the byte that decides
whether the drive is interpretable at all.**
**WATCH FOR:** a soft settle at LKAS engagement (ring 20 → 90 ms), and anything new at ~42 Hz (1.75×).
**EXPOSURE NEEDED:** engaged, below 16 km/h, with deliberate moderate steering at 15–40 °/s.

---

## 13. HOW THIS BUILD DIFFERS FROM THE ARC SINCE V38

**V38–V52** authority/filters/poles/caves · **V53–V61** probes and lane mutes · **V62–V73** the rate
lane · **V74–V83a** the base-assist damper · **V84** damper reverted · **V85–V99** observer/plant probes ·
**V100–V103** the gain ladder and arming the biquad · **V104** `c4` flat-gain raise — **FLOWN, NULL.**

🛑 **V105 IS THE FIRST BUILD IN THE PROJECT'S HISTORY TO CHANGE THE SHAPE OF A FILTER RATHER THAN THE
LEVEL OF A SIGNAL.** Every prior lever scaled something. This one moves a pole pair and a zero pair.
- **Not a re-run.** `0xC60A8`/`AC`/`B0` are **byte-stock in all 74 built images V38→V104**; only
  `0xC60B4` (`c4`) has ever moved, once, at V104.
- **Not the refused notch.** The 2026-08-20 refusal was for re-centring at **6–9 Hz**, killed on
  `Re(u/T)` phase. **This targets 26 Hz — a different band and a different argument.**
- **It is the only shape that survives GATE 2** (§6.2), which is why it is the last candidate standing
  rather than one of several.
- **It is aimed at the loud thing.** Every build since V62 has targeted 6–9 Hz or 15–22 Hz. **The
  21–28 Hz mode is 3–5× louder than either and no build has ever touched it.**

---

## 14. METHOD FINDINGS

- 🛑 **FOUR TOOLING TRAPS, all the same family — they return an authoritative-looking WRONG answer, not
  an error:** `get_xrefs_to` false "No references found" on tp-relative cells · `decompile_function`
  silently returning the **wrong function** in undefined regions · **Ghidra answering against whatever
  program is `is_current`** (a 92-byte blob, live this session) · and **a headerless blob's file offsets
  read as image addresses.** ⭐ **Defence for the last: anchor with `image.find(blob)` before trusting
  any address in it.**
- 🛑 **TWO SILENT ZEROS in one extraction tool, both found independently by two agents:** `segments()`
  stopping at the first absent index (**route `85` silently skipped**), and the 5–15 / 21–28 Hz
  third-octave columns being **identically zero** (1024-pt FFT ⇒ 15.625 Hz bins, no bin centre).
- ⭐ **A verifier must be control-tested in BOTH directions.** Three controls: all-different (16 FAILs),
  nearly-identical (11 FAILs, 0 false positives), **synthetic-correct (0 FAILs)**. *"A verifier that
  rejects two wrong builds tells you nothing until it accepts a right one."*
- ⭐ **A bicoherence detector returned a 300× "detection" that was ONE WINDOW** (N_eff = 1.0; drop-one
  collapsed it 14×; and it was **largest on stock**, where there is no mode). Same family as the
  estimator that reads 79 on white noise.
- **Turn a rule into an assertion.** `build_v105_tva.py` asserts **against** the lossy 6-dp encodings —
  a rule someone must remember became a check that cannot be forgotten.
- **Audit your own claims before others act on them.** Six self-caught errors from one agent, **two of
  them inside its own memory files.**

---

## 15. ADDENDUM — THE ACOUSTIC LINE IS CLOSED WITH A BOUNDED NEGATIVE

### 15.1 ALL THREE GRINDS: NULL, ON BOTH READINGS, WITH A SENSITIVITY BOUND
Six builds, engaged, `< 16 km/h`. **PASS A** direct sub-100 Hz content at NFFT **16384** (0.9766 Hz bins,
whole 0–100 Hz stored so the search is not pre-committed). **PASS B** amplitude modulation of six audible
carriers, envelopes low-passed at 200 Hz and decimated to **500 Hz** (modulation Nyquist 250 Hz).

| AM excess | grind #1 ~21.7 | grind #2 ~44 | grind #3 ~46 | null p97.5 |
|---|---|---|---|---|
| r97 STOCK | 0.747 | 1.111 | 1.031 | 2.045 |
| r85 4× | 1.477 | 0.912 | 0.888 | 2.339 |
| r96 6× | 0.927 | 1.046 | 1.233 | 2.400 |
| r9e 6× | 0.936 | 0.881 | 0.852 | 1.955 |
| ra4 6× | 0.787 | 1.217 | 1.269 | 2.197 |
| r95 8× | 1.225 | 1.245 | 1.510 | 2.658 |

**Not one of 18 cells reaches its own null.** **Detection limit: a 10 % modulation is caught with
67–100 % power.** ⇒ **a bounded negative, not an absence of a number.**
⭐ **Direct content is a TROUGH:** 21.7 Hz prominence **0.50–0.88 on every build including stock** —
all **below 1.0** — where **wheel rate at the same frequency has prominence 39.18.** The whole 12–60 Hz
acoustic spectrum never exceeds ~1.1. **There is no line there to find.**
**The 35–55 Hz scan produced 4 candidates from 48 tests; a block-wise label permutation gives median 2,
p95 5, and p(null ≥ real) = 0.890 ⇒ chance. None at 43–47 Hz.**

### 15.2 🛑 A METHOD ERROR CAUGHT BY THE AGENT THAT MADE IT — AND IT IS A PROJECT-WIDE LESSON
> **A phase-shuffled surrogate preserves the magnitude spectrum EXACTLY, so it has NO POWER against a
> spectral LINE.** `|X|` at 21.7 Hz: original **924.9376**, surrogate **924.9376**, ratio **1.000000**.
> **An injected 35 % modulation — unmistakably audible — gave a detection rate of 0.11.**

**THE RULE:** phase surrogates are **INVALID as a null for a LINE/amplitude test** and **VALID for a
COUPLING/correlation test** (they destroy cross-structure while preserving each spectrum).
✅ **CHECKED: the 2:1 harmonic refutation used `R = \|mean exp(iφ)\|` against cross-window shuffles — a
PHASE-COUPLING statistic. It STANDS.** So does the positive control's leg 3.
**Replaced with an empirical no-line distribution from 12 control frequencies inside the same episodes;
false-positive rate 0.00–0.11. No conclusion reversed — they were unsupported before and are supported
now.** ⊕ A bootstrap `max(denominator, 1e-300)` guard was also producing CI upper bounds of ~1e300.

### 15.3 AND THE AGENT WITHDREW ITS OWN 6–12/s ACOUSTIC RESULT
Under the corrected null it reported "LINE" on **stock** — but the **m = 0 % false-positive rate on
`r97` is 1.00**: it fires on every stock episode with nothing injected. **Cause: the envelope spectrum is
RED, so 6–12 Hz sits higher on the slope than the 15.5–58.5 Hz controls — they are NOT exchangeable with
that target.** ⇒ **WITHDRAWN as UNINTERPRETABLE, neither null nor positive.** ✅ The same construction
**is** valid at 21.7 / 44 / 46 Hz, where the controls bracket the target and the false-positive rates
behave — **which is why the grind results are trustworthy and that one is not.**

### 15.4 THE VERDICT AND THE NEXT CHANNEL
**[BELIEF, strongly held] Grinding is not detectable in the cabin microphone. The acoustic line is
RETIRED, not left open.** Combined with the positive control — **the mic shows ZERO response to a mode
that moves 21× on wheel rate** — this is the wrong instrument for these symptoms.
⭐ **NEXT CHANNEL: the IMU.** Nyquist ~50 Hz covers **21–47 Hz entirely**, and it measures **what his
hands feel**, which the mic does not. 21–47 Hz is 7–16 m of wavelength and a steering rack is a hopeless
radiator there — **the acoustic null is close to predicted physics.**
**And two standing needs:** a **per-drive acoustic calibration clip** if that line is ever reopened
(parked, engine on, HVAC off, windows up, 30 s at drive start), and **a second STOCK drive** — stock is
one route, that confound is not fixable by analysis, and it is worth more than another 6× build.
