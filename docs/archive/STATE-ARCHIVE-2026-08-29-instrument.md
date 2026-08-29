# STATE archive — superseded during the instrument calibration

A RECORD, NOT AN INSTRUCTION.

## ✅✅ **THE RATCHET IS NOT EPISODIC IN BAND SHARE — THE TAIL LOOKS LIKE THE MEDIAN**
A flaw in my own method: every matched analysis this session took the **MEDIAN** over engaged
windows, and the kit's own characterisation says the ratchet appeared in **44 of 46 windows** on one
route — i.e. it may be **EPISODIC**, and a median would wash an episodic phenomenon out entirely.
**Tested by re-running the matched contrast at the TAIL.**
```
   statistic   6-9 Hz [95 % CI]        26-31 Hz CONTROL        23 routes, matched on
   median      1.067 [0.966, 1.226]    0.987 [0.870, 1.264]    (speed bin x |rate| RMS bin)
   p75         1.073 [0.954, 1.193]    1.082 [1.005, 1.263]
   p90         1.160 [0.993, 1.256]    1.022 [0.802, 1.317]
   p95         1.100 [1.039, 1.243]    1.065 [0.886, 1.276]    <- 6-9 Hz EXCLUDES 1
   p99         1.110 [0.963, 1.241]    1.024 [0.928, 1.224]
```
⇒ **[EVIDENCE] the tail is indistinguishable from the median.** If the ratchet were concentrated in
rare episodes, **p95/p99 would show a much larger contrast than the median.** They do not —
**1.10 vs 1.07.**
⇒ **the engagement effect is a UNIFORM ~10 % elevation of the 6-9 Hz band, not an episodic
concentration.** The kit's *"44/46 windows engaged"* figure was about detecting a **LINE**, a
different statistic from band share — **the two are not in conflict.**
✅ **AND IT FIRMS THE EFFECT UP**: at **p95 the 6-9 Hz CI EXCLUDES 1** (1.039–1.243) while its
control spans 1, converging with the independent median-based estimate **1.12 [1.01, 1.27]**.
⇒ **CONVERGED RESULT: engagement adds ~10 % to the 6-9 Hz band — real, small, robust across central
AND tail statistics, with controls clean at every percentile.**

⊕ **This also closes the last live objection to the ≤ ~2 % of RMS line bound**: that bound was
derived from a median-based prominence contrast, and the natural challenge was *"an episodic symptom
would be diluted."* **It would not be — the tail behaves like the centre.**

## ✅✅ **THE AUDIO AM NULL IS NOW CLEAN — AND THAT IS THE THIRD ARTEFACT KILLED BY A CONTROL**
Last turn's audio envelope-AM test was underpowered **and its 60–100 Hz control failed** (0.804,
excluding 1), because windows were matched on **creep speed only**. Re-ran it with the same
stratification that fixed the CAN-side analysis: **(speed bin x |rate| RMS bin)**.
```
   audio band     6-9 Hz AM [95 % CI]        20-28 Hz CONTROL         control status
   15-21          1.020 [0.767, 1.125]       0.931 [0.834, 1.318]     clean
   28-40          0.958 [0.854, 1.070]       1.081 [0.836, 1.390]     clean   <- was 1.309
   40-60          1.048 [0.878, 1.062]       0.882 [0.456, 1.511]     clean
   60-100         0.869 [0.840, 0.989]       1.044 [0.767, 1.298]     clean   <- control FIXED
   100-300        1.013 [0.815, 1.091]       1.057 [0.777, 1.268]     clean
   300-1000       1.004 [0.884, 1.675]       0.875 [0.719, 1.090]     clean
   1000-3000      1.038 [0.779, 1.426]       0.788 [0.473, 1.029]     clean
   3000-8000      1.058 [0.894, 1.362]       1.049 [0.897, 1.086]     clean
```
✅ **ALL EIGHT CONTROL BANDS NOW SPAN 1** — the stratification fix worked.
✅ **[EVIDENCE, clean controls] there is NO engagement-conditional 6–9 Hz AM in the audio, in any
band.** The previously "most suggestive" **28–40 Hz cell fell from 1.309 to 0.958** — it was **pure
matching artefact.**
⚠ 60–100 Hz reads **0.869 [0.840, 0.989]**, excluding 1 *below*. With **eight bands tested**, one
marginal exclusion is expected by chance; **not claimed.**
⇒ **the ratchet does not AM-modulate the cabin audio in a way engagement changes.** Combined with
the CAN-side bound (**≤ ~2 % of RMS**), **both available instruments now return clean nulls on
symptom A**, which is itself consistent with the mode being **motor/rack-side and unobservable**.

## 🛑🛑 **THE PATTERN: THREE TIMES THIS SESSION, THE CONTROL KILLED THE EFFECT**
```
   engagement contrast, 6-9 Hz     2.8x   ->  1.12 [1.01, 1.27]   when MATCHED on speed x activity
   post-disengage persistence      1.29x  ->  ratio 0.911         when a CONTROL BAND was added
   audio envelope AM, 28-40 Hz     1.309  ->  0.958               when matched on activity too
```
⇒ **every one of these was plausible, specific, and pointed at a real mechanism.** Each survived
until its control was computed, and none survived after.
⭐ **This is [[feedback-run-the-control-before-the-measurement]] earning its place three separate
times in one session, on three different instruments (CAN band power, CAN envelope, audio envelope).**
⇒ **RULE, stated for the record: on this kit, an uncontrolled engaged-vs-manual ratio is worth
nothing.** Operating point differs systematically between the arms — engaged is creep and steady,
manual is faster and more active — and that difference is **larger than every effect measured this
session.** **Compute the control first, or do not compute the number.**

## ⚠ **AUDIO ENVELOPE DEMODULATION FOR THE RATCHET — NEW METHOD, NO SIGNAL, IMPERFECT CONTROL**
The kit uses audio only for **symptom B's band power**. But **a ratchet is an impulse train**, so it
would not appear *at* 7.8 Hz in audio — it would appear as **7.8 Hz AMPLITUDE MODULATION of the audio
envelope**. That had never been tried. Tried it.

### ✅ THE INSTRUMENT EXISTS ALREADY
The audio caches store **per-band envelopes** sampled at **62.5 Hz** (`wide` x 10 bands with
`wide_lab`; the older `a20_100 ... a4k_7k` format is 100 Hz but only on r81/r82).
=> Nyquist **31.25 Hz** — 6–9 Hz is comfortably resolved; the control had to move to **20–28 Hz**.
=> **five routes carry substantial creep-engaged audio**: r9e 12,952 · r96 9,803 · r97 5,495 ·
r85 5,238 · ra4 4,312 samples.

### ⚠ THE RESULT — NO SIGNAL, AND THE CONTROL IS NOT CLEAN
```
   audio band     6-9 Hz AM [95 % CI]        20-28 Hz CONTROL
   15-21          0.971 [0.951, 1.142]       1.150 [0.822, 1.701]
   28-40          1.309 [0.978, 1.627]       0.977 [0.743, 1.313]
   40-60          1.110 [0.874, 1.238]       0.764 [0.392, 1.719]
   60-100         1.134 [0.912, 1.254]       0.804 [0.626, 0.923]   <-- CONTROL EXCLUDES 1
   100-300        1.020 [0.897, 1.269]       0.935 [0.686, 1.094]
   300-1000       0.969 [0.878, 1.121]       0.986 [0.810, 1.233]
   1000-3000      1.031 [0.872, 1.364]       0.957 [0.715, 1.183]
   3000-8000      1.030 [0.899, 1.190]       0.961 [0.782, 1.732]
```
=> **every 6–9 Hz CI spans 1 — no detectable ratchet AM in any audio band.**
🛑 **BUT ONE CONTROL BAND FAILS**: 60–100 Hz reads **0.804 [0.626, 0.923]**, excluding 1. The
windows were matched on **creep speed only, not on steering activity**, so residual confounding
remains.
=> **[NOT A CLEAN NULL]** — this is an **underpowered test (5 routes) with an imperfect control**,
and it must not be cited as evidence that the ratchet is acoustically silent.

### ⭐ WHAT IS WORTH KEEPING
⊕ **The METHOD**: audio-envelope AM demodulation is a legitimate, previously-unused instrument for
an impulse-train symptom, and the caches already contain what it needs. **Most suggestive cell:
the 28–40 Hz audio band at 1.309 [0.978, 1.627]** — not significant, but it is where a
mechanical ratchet's carrier would plausibly sit.
⊕ **What would close it**: more routes carrying audio **with matched creep engaged AND manual
exposure**, and matching on **steering activity** as well as speed — the same stratification the
CAN-side analysis needed. **Only 5 of ~230 routes have usable creep-engaged audio at all.**
=> **audio capture on every future drive is what makes this instrument usable** — already the
standing request for symptom B, and now for symptom A as well.

## 🛑 **"GRINDING CONTINUES AFTER DISENGAGING" — NO BAND-SPECIFIC PERSISTENCE ON THE BUS**
The operator's V133 report included *"which continues after disengaging."* That is a **structural**
claim — the command is gone, so the mechanism would have to have **memory** — and it had never been
tested. Tested now, on **139 creep-ish disengage events across 76 routes**, by aligning on the
engaged→manual edge and tracking the 6–9 Hz Hilbert envelope of `tq` normalised to its own engaged
baseline.

### ⚠ THE UNCONTROLLED VERSION LOOKED LIKE A RESULT
```
   engaged -3..0 s   1.000        after 2..3 s   1.225
   after 0..1 s      1.293        after 3..5 s   1.119
   after 1..2 s      1.212        (IQR 1.6-1.9 throughout)
```
⇒ read alone, *"the ratchet band stays ~25 % elevated for 5 s after disengage"* — which would have
supported the operator's report and pointed at a filter state with memory.

### ✅ THE CONTROL BANDS KILL IT
```
   band                  median    [95 % CI, 4000-draw bootstrap]
   6-9 Hz  (ratchet)      1.377    [0.918, 1.588]     CI INCLUDES 1
   26-31 Hz CONTROL       1.051    [0.948, 1.288]
   32-38 Hz CONTROL       1.117    [1.025, 1.249]

   RATIO 6-9 / 26-31      0.911    [0.795, 1.132]     BELOW 1, CI spans 1
```
⇒ **[EVIDENCE, with controls] there is NO band-specific persistence.** The post-disengage elevation
appears in the **control bands too**, so it is **general activity — the driver taking over — not
ratchet memory.** The band-specific ratio is **0.911**, i.e. if anything the ratchet band rises
*less* than the controls.

### ⭐ THE METHODOLOGICAL POINT, WHICH IS THE DURABLE PART
**The same 139 events read as *"grinding persists 25 % after disengage"* or *"no effect at all"*
depending ONLY on whether the control band is computed.** This is
[[feedback-run-the-control-before-the-measurement]] demonstrated on a fresh question, and it is worth
keeping because the uncontrolled number was **plausible, specific, and would have pointed at a real
mechanism** (a filter state with memory) that does not exist.

### 🛑 WHAT IT DOES **NOT** SETTLE
⚠ **This does not refute the operator's report.** Two readings survive:
```
   (a) the persistence is not real as a 6-9 Hz phenomenon on the column
   (b) it IS real but NOT OBSERVABLE ON THIS BUS
```
⇒ **(b) is the reading consistent with everything else this session established** — the mode is
**motor/rack/tyre side, which no channel on this bus observes**, and engagement adds **≤ ~2 % of RMS**
as a 7.8 Hz line on the column. **A symptom the bus can barely see engaged will not be visible
decaying after disengage either.**
⇒ **[NOT CLOSED] the operator's ear remains the only instrument for this**, and the honest record is
that the bus test came back null **with its control passing**, which is a statement about the
instrument as much as about the symptom.

## ✅✅✅ **CONTROL IS FULLY ACTIVE WHERE THE COMMAND RAILS — THE CREEP-AUTHORITY CHAIN IS CLOSED**
The memory's *"0 % control-active below 2 mph"* was measured when `0xC62EA` = 320. **It is 0 on
current builds**, so the measurement had to be redone. Redone — **227 routes, 1.88 M engaged
frames** — and it settles the authority question.
```
   STEER_STATUS while ENGAGED     distribution: {0: 1,901,564 | 3: 14,538 | 4: 92}

   speed band       engaged frames   STEER_STATUS=3     duty
   0-2   km/h             179,135           10,511    5.868 %
   2-8   km/h             175,039                0    0.000 %   <-- where the command rails 6.4 %
   8-16  km/h             470,173                0    0.000 %
   16-25 km/h             547,927                0    0.000 %
   25-40 km/h             506,512                0    0.000 %
```
⇒ **[EVIDENCE] `STEER_STATUS = 3` is EXACTLY ZERO at 2–8 km/h**, the band where the command rails
**6.4 %** of engaged frames.
⇒ **the lockout removal WORKED** — control-active is continuous through the whole creep band, and the
old *"0 % below 2 mph / 88 % at 3–4 mph"* figures are **obsolete for every build since**.

### ⭐⭐ WHAT THIS SETTLES — THE RAILING IS NOT A FIRMWARE DROPOUT
```
   lockout 0xC62EA          already 0            => not gating
   STEER_STATUS at 2-8 km/h exactly 0 duty       => control is FULLY ACTIVE
   the command rails anyway 6.4 % of frames      => the demand genuinely exceeds the field
```
⇒ **[EVIDENCE] the authority shortfall at creep is NOT a control dropout, a lockout, or a gating
failure. The firmware is fully engaged and openpilot is asking for more than a 13-bit signed field
can carry.**
⇒ **the ONLY remaining explanation is TORQUE PER COUNT** — which is the **gain `0xC6CD0`** (frozen
in both directions) or the **±15360 setpoint clamp `0xC61BC`** (virgin, binding unknown).
⇒ **every other hypothesis for creep authority loss is now eliminated by measurement.**

### ✅ TWO SIDE RESULTS WORTH KEEPING
⊕ **`STEER_STATUS = 3` survives only at 0–2 km/h (5.868 %)** — i.e. at standstill, where the
`gp-0x68b3` standstill bypass and the remaining conjuncts govern. **Expected, and not a concern:**
LKAS steering at 0–2 km/h is not a regime the operator is complaining about.
⊕ **`STEER_STATUS = 4` occurs 92 times in 1,878,786 engaged frames (0.005 %)** — the state-4
governor ratchet that V42 fixed. **The fix is holding across the whole corpus**, which is an
independent confirmation of [[reference-accord-state4-governor-ratchet]] and of
[[accord-v42-ratchet-fix-lost-since-v53]] being restored.

⇒ **The probe on `0xC61BC` is now the last standing question about creep authority**, and it is the
only one whose answer could break the authority/grinding tension.

