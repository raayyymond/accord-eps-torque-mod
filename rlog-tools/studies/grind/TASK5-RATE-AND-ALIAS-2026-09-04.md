# Is `gp-0x6a56` (CAN `0x18F` bytes[2:3]) band-limited, or an aliasing sample-and-hold?

**Subagent `task5rate`, 2026-09-04. Empirical half; `telem285` took the firmware half.**
Routes r34 (V280 rev 2) · r35 (V281 rev 3) · r36/r37/r38 (V283). Analysis only — nothing built,
flashed, or sent on any bus.

Scripts, all in `rlog-tools/studies/grind/`:
`task5_rate_alias.py` · `task5_nyquist_shape.py` · `task5_imu_extract.py` ·
`task5_imu_crosscheck.py` · `task5_1ab_discriminator.py` · `task5_consequence.py`
Outputs in `_scratch/task5_*.txt`; IMU caches `_scratch/imu_r3{5..8}.npz`.

---

## THE ONE-LINE ANSWER

**The channel is NOT band-limited — it demonstrably carries folded power — and I could NOT determine
what fraction of the 27–32 Hz band is folded. But the false-all-clear risk splits cleanly by the TYPE
of endpoint, and only one of the two types is unsafe.**

| endpoint V286 might rest on | safe on this channel? |
|---|---|
| **ENERGY** — "did HF energy grow when Kd went 128→160?" | ✅ **SAFE.** There is no anti-alias filter, so folded power is *not attenuated*: it arrives at full amplitude somewhere in 0–50 Hz. Aliasing destroys the frequency label, not the energy. A destabilising mode cannot disappear from this channel. |
| **FREQUENCY** — "the binding mode is AT 27–32 Hz, therefore the phase margin there is X" | 🛑 **NOT SAFE.** The label could equally be 68–73 Hz (or 127–132 …). The controller's own phase differs by **11°** between 30 and 70 Hz and its D/P ratio by **2.3×**; the plant differs by far more. |

⇒ **If V286's 16 % gain-margin spend is justified by a frequency-specific margin computed at 27–32 Hz
from this channel, that justification is unsound.** If it is monitored by an energy endpoint, the
existing 100 Hz channel suffices and no 1 kHz code cave is needed.

---

## TEST-BY-TEST VERDICTS

### Test 2 — STALENESS / REPEAT STRUCTURE → **PASS, and it bounds only one direction**

**[EVIDENCE]** Consecutive samples are essentially always fresh. `P(x[n]==x[n-1])` conditioned on the
**local slope** (LS slope over a ±4-sample window, so the scored repeat does not drive its own
predictor — this is the quantisation-immune form the brief asked for):

| \|slope\| LSB/sample | r36 measured | band-limited null | S&H ×2 positive control |
|---|---|---|---|
| 0.00–0.25 | 0.208 | 0.263 | 0.601 |
| 1.00–2.00 | 0.079 | 0.067 | 0.531 |
| ≥ 8 | 0.018 | 0.009 | 0.507 |

Measured tracks the **band-limited null** and is nowhere near the **50 Hz sample-and-hold control**
(pinned at ~0.50 at every slope). Constant-value runs: p90 = 1–2 samples, mean 1.10–1.13.

⇒ The producer is **not slower than 100 Hz and not asynchronous to the frame**. Those hypotheses are
dead. **But this test cannot distinguish "a synchronous 100 Hz producer" from "an instantaneous
100 Hz sample of a 1 kHz process" — they look identical.** It bounds the "stale" direction only, and
the stale direction was never the dangerous one.

### Test 3 — HIGH-FREQUENCY SHAPE → **THE DECISIVE POSITIVE RESULT**

**[EVIDENCE] On all five routes the engaged PSD of the 0x18F rate reaches a minimum near 36–38 Hz and
then RISES MONOTONICALLY to Nyquist.** A band-limited signal cannot do that. Folded power piling up
below Nyquist is the standard cause.

PSD normalised to the 10–15 Hz band, engaged, Welch `nperseg=4096` Hann on the **frame index**:

| route | 27–32 | 33–38 | 38–44 | 44–47 | 47–49 | 49–49.9 | rise from the minimum |
|---|---|---|---|---|---|---|---|
| r34 | 0.436 | 0.130 | 0.122 | 0.147 | 0.249 | 0.308 | **2.5×** |
| r35 | 0.633 | 0.166 | 0.181 | 0.202 | 0.279 | 0.302 | **1.8×** |
| r36 | 0.570 | 0.181 | 0.170 | 0.235 | 0.375 | 0.453 | **2.7×** |
| r37 | 1.229 | 0.265 | 0.332 | 0.474 | 0.752 | 1.277 | **4.8×** |
| r38 | 0.352 | 0.116 | 0.106 | 0.160 | 0.274 | 0.327 | **3.1×** |

**Four artifact explanations excluded, each by its own control:**

1. **Frame loss / splice.** The "2 % gaps" my first pass counted were **batch jitter, not loss**
   (dt has a mode at 0 s — two frames handed over in one `logMonoTime` — and another at 0.0195 s).
   The honest measure is the count deficit against the wall clock: **r37 = 0 frames, r38 = 3 in
   84,828, r34/r35/r36 ≈ 0.17 %.** The frame index *is* the true grid. And r37, the cleanest grid,
   shows the **largest** rise.
2. **Window leakage from the strong 20–24 Hz mode.** A synthetic band-limited signal (Butterworth
   22 Hz) pushed through the identical estimator reads **0.000** in every band above 27 Hz. No leakage.
3. **A two-phase / alternating producer at exactly fs/2.** `|corr(x, (−1)^n)|` sits **at** its
   1/√n noise floor on every route (e.g. r36 0.0008 vs floor 0.0120). Not a 50 Hz line — a shelf.
4. **A logging- or CAN-path artifact.** The `0x14A` steering angle, same bus, same 100 Hz cadence, is
   **flat** at HF (r37: 0.257 / 0.247 / 0.262 / 0.245 / 0.272) — it does not rise. A white
   quantisation floor, exactly as expected, and proof the rise is not in the transport.

⚠ The `0x18F` **driver-torque** channel (same frame) rises too, more weakly. So the rise is not unique
to the rate, but it is not universal to the frame either.

**Corollary, and it matters more than the rise itself: there is no averaging anywhere in this path.**
A boxcar average over the 10 ms frame would impose a sinc rolloff (−3.9 dB at 50 Hz, null at 100 Hz)
and would *suppress* the near-Nyquist region. We measure a **rise**. ⇒ The payload is an
**instantaneous sample**, and folded power is therefore **unattenuated**. This is measured, not
assumed — it does not depend on `telem285`'s firmware read.

### Test 1 — CROSS-SENSOR → **STRUCTURALLY IMPOSSIBLE; the kit already knew, and I reconfirmed the crux**

🛑 **This test cannot work and no further agent time should be spent on it.**
`memory/accord/instruments/accord-both-instruments-blind-above-50hz.md` already records it:
the comma IMU runs at **101.02 Hz**, giving 0.51 Hz of headroom over CAN — the discriminant is a
**1.01 Hz apparent-peak shift per alias order**, and the kit's own paired-shift measurement over the
120 loudest windows gave **median +1.68 Hz, sem 0.856, where ≪0.34 is needed. Underpowered.**

**[EVIDENCE] I re-measured the IMU hardware clock independently** on r35–r38 (`accelerometer.timestamp`
and `gyroscope.timestamp`, not `logMonoTime`): the hw dt histogram is quantised at 9.9 / 19.8 / 29.7 ms
⇒ **native ODR 101.01–101.03 Hz**, with 7–13 % of samples dropped as isolated 1s and 2s. That
reproduces the record's 101.02 Hz exactly. The record stands.

The other two candidate comparison sensors are also dead, for reasons worth writing down:

- **`livePose.angularVelocityDevice`** — 20 Hz, **Nyquist 10 Hz**. Cannot cover 32 Hz at all.
- **`0x14A` steering angle** — quantisation-blind in this band, and by a wide margin. r36's engaged
  27–32 Hz rate content is 36.8 counts² ⇒ **0.758 deg/s rms**, which at 29.5 Hz is
  **0.0041 deg of angle rms — 24× below the 0.1 deg LSB.** The measured coherence rolloff
  (0.55 at 10–15 Hz → 0.25 at 27–32 Hz) is this, not physics. **Do not read that rolloff as evidence
  about the rate channel.**
- **The microphone** is the kit's only uncapped instrument (16 kHz PCM, 8 kHz analysed) but is
  separately recorded as blind below 100 Hz with a bounded null on grinding
  (`accord-grinds-not-detectable-in-cabin-sound.md`).

### Test 4 — CROSS-FRAME → **POWERLESS. Three independent reasons.**

The brief called this "possibly the most informative". It is not, and it is worth recording exactly why.

1. **Rate contrast buys nothing, provably.** 50 exactly divides 100. True 30 Hz and true 70 Hz alias to
   the *same* 20 Hz on the 50 Hz `0x1AB` stream, exactly as they alias to the same 30 Hz on the 100 Hz
   `0x18F` stream. The `0x1AB` timestamps are every other `0x18F`. Zero discrimination.
2. **The known 1 kHz filter between the taps IS a real 6.8 dB discriminator — but it is swamped.**
   `0x18F` carries `gp-0x6a56` unfiltered; `0x1AB` carries `T`, the same signal through the rate-PID
   chain. Mirroring the decompile exactly (EMA `923/1024` + two-sample sum → `Kp` 248 →
   `D = dE*16` → `254/256` → lag `992/507` `>>5` → gain `5346/32768`):
   `|H(70)|/|H(30)| = 0.458`, i.e. **a 70 Hz source reaches the tap 6.79 dB weaker.** Both land in the
   same 18–23 Hz band there. That is a genuine ~4.8× power discriminator.
   🛑 **It fails because true 18–23 Hz content lands in that same observed band DIRECTLY** — 18–23 is
   *below* the 50 Hz tap's 25 Hz Nyquist — and 18–23 Hz is where the dominant grind mode lives. It is
   **2.4–4.9× larger than the 27–32 candidate on `0x18F`** and passes through a larger `|H|²`
   (0.78 at 20 Hz vs 0.43 at 30 vs 0.086 at 70), so its contribution is **9–45× either candidate.**
3. **The statistic announced its own invalidity, which is how I caught it.** Run naively, the estimator
   returns an "implied real fraction" of **10–16 on every route. A fraction cannot exceed 1.** The
   chain model also under-predicts the measured `0x1AB` band powers by ~2× (clamps, the `sp` path, the
   `P`/`D`/`S` saturations), so no subtraction of the direct term is trustworthy either.
   `task5_1ab_discriminator.py` now prints the diagnosis instead of the verdict.

---

## THE BOUND I TRIED TO PUT ON THE FOLDED FRACTION — AND WHY I AM WITHDRAWING IT

The tempting argument: observed 33→50 Hz is the folded image of true 67→50 Hz, and it *rises* toward
50, so the true spectrum **decays** from 50 to 67 Hz. If that decay continues to 68–73 Hz (the fold
partner of 27–32), the folded contribution at 27–32 is ≤ the observed 33–38 level — giving a folded
fraction of **≤ 22 % (r37), 26 % (r35), 30 % (r34), 32 % (r36), 33 % (r38)**.

🛑 **I do not stand behind this**, and the reason came out of my own control:

**[EVIDENCE] the folded shelf is itself ENGAGEMENT-GATED, as strongly as the 27–32 excess is.**
Using the 33–38 Hz shelf as the adjacent control band:

| route | 27–32 excess over shelf, eng/manual | near-Nyquist shelf 45–49.9 / 33–38, eng/manual |
|---|---|---|
| r34 | 3.26× | 3.38× |
| r35 | 1.68× | 1.38× |
| r36 | 1.54× | 3.13× |
| r37 | 2.15× | 2.20× |
| r38 | 1.35× | 1.45× |

The two move together. **I cannot separate the 27–32 feature from the fold by engagement gating**, and
— more importantly — **engaging LKAS raises the true >50 Hz content by 1.4–3.4×.** The content above
Nyquist is *driven by our own loop*, so there is no basis for assuming its spectrum decays smoothly
across 62→73 Hz. A loop-driven resonance sitting at 68–73 Hz is exactly the shape that would break the
monotonicity assumption, and it is exactly the shape a raised Kd could create.

⇒ **The folded fraction of the 27–32 Hz band is NOT bounded by anything I measured.**

---

## WHAT WOULD ACTUALLY SETTLE IT

Ranked, and the first is much cheaper than the third.

1. ⭐ **Change the endpoint, not the instrument.** Score V286 on an **energy** endpoint over the whole
   0–50 Hz observable band (with the 33–49.9 Hz folded shelf carried as an explicit reported band),
   not on a frequency-specific margin at 27–32 Hz. This is sound on the existing channel *today*,
   needs no build, and follows directly from "aliasing conserves energy and destroys labels".
2. **A different IMU ODR (208 or 416 Hz)** would break the degeneracy outright — the kit's own file
   names this. ⚠ It is recorded as **out of bounds** (`feedback-no-openpilot-side-modifications`), so
   this is a note, not a proposal.
3. **The 1 kHz sticky/accumulating flag** already described in
   `accord-both-instruments-blind-above-50hz.md`: a bit latched inside the 1 kHz task when a band-passed
   quantity crosses a threshold, cleared when the 100 Hz payload is written. It reports HF **energy**
   without aliasing. 🛑 It needs a RAM cell, so **GATE 1 is not vacuous** — this is the class that
   bricked V24/V27/V48B, and `gp-0x1500` passed both static clearance methods and still failed on-car.
   Given (1) exists, this is not worth the bricking risk for V286.

## LIMITS OF THIS WORK

- All spectra are on the **frame index**, per the brief's warning about 10 ms batch jitter. Verified
  sound: r37's frame deficit is exactly 0.
- Engagement is `0x18F` SCA **AND** `0xE4` STEER_REQUEST throughout, per
  `feedback-engaged-means-lateral-engaged-and-v276-is-not-a-reference`.
- Every estimator here ships a null: a band-limited surrogate, a white-noise surrogate, a 50 Hz S&H
  positive control, and the 33–38 Hz adjacent control band. The retired pooled half-power Welch width
  is not used anywhere.
- I did **not** establish what the >50 Hz loop-driven content actually is. That is open, and it is now
  a more interesting question than when I started.
