# HANDOFF 2026-08-09 — V86 and V86B flew; the ratcheting is a resonance, and the firmware search on it is closed

**Session shape:** orchestrator + 17 subagents. **Two routes scored. Nothing built, deliberately.**
The deliverable is a diagnosis, a closed search space, eleven instrument defects, and a next-flight plan
that contains no calibration edit.

---

## 1. What flew

| | route `6f` | route `70` |
|---|---|---|
| build | **V86** (`0xC40D4` 573 → 286) | **V86B** (FactorC m26/m27 `Y[0]` 0 → 908/875) |
| frames / duration | 23,058 / 232.3 s | 21,428 / 216.0 s |
| engaged | 61.4% | 43.0% |
| `STEER_STATUS` | {0: 23,048, 3: 11} | {0: 21,409, 3: 20} |
| DTC-active / sentinels | 0 / 0 | 0 / 0 |
| **v_max** | **5.38 m/s** | **5.97 m/s** |
| **≥50 km/h engaged** | **0.0 s** | **0.0 s** |

Both fault-free (`STEER_STATUS` = 3 is the low-speed lockout, expected in a parking lot).
**Identity verified with no free parameter** — each route emits thousands of frames the other build is
structurally incapable of and zero of its own, per-segment, no mixing.

🛑 **Both routes are parking-lot only.** No highway verdict, no grind-#1-at-speed verdict, and **26–31 Hz
is unscoreable** on either. That is a harder limit than route `6e`, which at least had 35 s above 50 km/h.

**Operator's report — every symptom he scored FAILED, and the instrument agrees on every one:**
grinding and micro-ratcheting *"maybe a smidge better, if at all"* (`6f`) / *"still present, dampened I
think"* (`70`); **ratcheting definitely perceptible on both**; **his second grinding complaint present on
both**; plus *"extra dampening on LKAS and in general at slow speed"* on `70`.

---

## 2. The headline: V86's pre-registration is falsified, and the falsifier could fire

`f(V86)/f(V85)` = **1.001 [0.976, 1.060]** against a pre-registered **[0.797, 0.875]** — CI **disjoint**
from the entire range and including 1.00. The line stayed at **8.00 Hz**.

Five independent statistics, all null (free argmax, centroid, order-cleaned, NFFT 512, second signal).
Power confirmed by a faithful shift surrogate — the line removed and re-added shifted, amplitude,
envelope and coherence preserved — which recovers ×0.797/×0.843/×0.875 with CIs excluding 1.00.
**Smallest resolvable shift ×0.94 against a requested ×0.843 ⇒ 2.6× margin.** Lever in force three ways.

🛑 **The bound is worth more than the null: the build-to-build floor at constant α is 14× the entire
effect** — two builds *sharing* `0xC40D4` = 573 differ by 0.017 while the α-differing pair differs by 0.001.

⊕ **`STATE.md`'s absolute window was mis-derived**: [6.2, 6.9] = `7.79 × [0.797, 0.875]`, but V85's measured
centre is **8.207**, so it should have read **[6.54, 7.18]**. Verdict unaffected — all three defensible
denominators and both windows agree.

---

## 3. What the ~8 Hz ratcheting IS

**A lightly-damped resonance, Q ≈ 14–29.** Three methods, each having survived its own control:

- **Ring-down** — the only estimator that PASSES a control (log-log r = +0.937 over ζ = 0.005–0.02).
  Measured **ζ ≈ 0.017–0.036 ⇒ Q ≈ 14–29** [EVIDENCE, n = 5 edges]. ⚠ Measures the **disengaged** plant
  (the falling edge switches mode 26 → 24) — it bounds the mechanical mode, not the loop.
- **Peak-aligned pooled Welch with a calibration ladder** — pure tone reads **53.8**, bursty AM tone
  **52.1–52.5**, **the car reads 20.9** ⇒ **limit cycle EXCLUDED**, Q < 40.
- **The phase-slope bound** from V86's own null required **Q ≥ 2.4** — satisfied.

**What it is not:** not a relay (harmonic comb 0.858 against a control at 1.204; `frac_disc` 0.664 against
continuous-torque 0.615–0.621 and a hard-relay control at exactly 1.000) · not amplitude-dependent
(`d log f/d log A` = −0.034 [−0.069, −0.013] over 4× ⇒ kills rate-limit, backlash, classic stick-slip) ·
not cogging/commutation/worm/belt/U-joint/resolver (slope +0.0015 [−0.0014, +0.0147] against a required
0.354 over a 20:1 rate range — all die together) · not engine order (`df/drpm` +0.00007 vs required
+0.0083 over 422 rpm) · not wheel order (`f = 0.1215·v + 7.500` — an order passes through the origin) ·
not driver tremor (the line is *bigger* with hands off, r = −0.311) · not command jitter (peaks at
5.7/6.0/10.0 Hz) · not a ZOH/clock artefact (`0x14A` vs `0x18F` arrival rates differ by 4–28 **milli**hertz).

🛑 **And not a rim-side resonance** [EVIDENCE]: torque PSD peaks ~6×, rate PSD ~3×, but the transfer
function **`|T/Ω|` rises smoothly straight through** (63 → 75 → 93 → 121, coherence 0.86–0.91). Positive
control: injected Q=10 → **3.40×** admittance peak, Q=3 → **1.52×**; **the car → 1.30×, not at the line.**
⇒ **Also refutes "the 12.8 Hz wheel-on-bar mode pulled down by engagement"** — that mode is by definition
rim motion against the bar and would have to appear there.
⇒ **The mode is on the motor / rack / tyre side, which no channel on this bus observes.**

★ **Frequency tracks LOAD**: **+0.467 Hz [+0.111, +0.927]** over a 17.8× column-torque range at fixed
speed (+5.8% in f ⇒ **+12% stiffness**), against **−0.145 [−0.564, +0.325]** vs openpilot's command.

---

## 4. The firmware search on the ratchet is CLOSED — a shape argument

**Nothing in the firmware can produce a band-limited lift at 6–9 Hz.** Every gain-bearing element on the
torque path is either **a flat Q10 scalar** — which would lift the 26–31 and 32–38 Hz controls too, and
they went **down** to 0.61–0.76 — or **a differentiator**, which favours HF, the wrong direction. A
localised lift needs a **resonant/biquad structure, and none exists anywhere in the chain.**

Corroborating: **no −180° crossing anywhere in 0.5–200 Hz** even with the real PID gains loaded (PID is in
**lead** at 8.21 Hz, +10.08°; crossover 6.155 Hz; P dominates I 4.3:1); **`|L|` never reaches unity in
18–27 Hz**; and a 2-pole EMA has DC gain exactly 1, so **no EMA in the chain can be the amplifier.**

⇒ **The ~4× engaged/manual lift at 6–9 Hz** (3.91 [2.37, 5.70] on `6f`, 4.21 [2.16, 6.87] on `70`, both HF
controls below 1) **is the plant's transfer function being driven harder — not a firmware filter gain.**

---

## 5. The 4× is the one frozen variable — and it is not the culprit

```
build          0xC646C   0xC6CD0    forward LKAS gain
stock              891     blank    1.000x
V38/V42/V80       3564     blank    4.000x   <- 4x in the SHARED cell
V58 ... V86B       891      3564    4.000x   <- V57 decoupled it; magnitude NEVER changed
```

**Exactly 4.000× on every build in the modern lineage.** A variable with zero variance is invisible to
every dose–response, cross-build matrix and A/B **by construction**. ⚠ **And it migrated cells at V57**, so
a careful reader diffing images sees `0xC646C` go 3564 → 891 and concludes it was reverted. It was not.

🛑🛑 **But it is not the amplifier, on two independent grounds:**

1. **Path 1 and Path 2 are structurally decoupled.** `search_instructions(FUN_00028ea6, "6b98")` → **0 over
   1,874 instructions**, and a raw Python LE scan of the function extent (both `disp16` and `disp|1` forms)
   → **0 hits**, against a positive control finding **33 image-wide**. The arbitration function hosting the
   4× **never reads the delivered motor command.** ⇒ **The 4× scales excitation into Path 2, not Path 2's
   loop gain.**
2. **The keystone is retracted.** `LEDGER:192`'s **63.66×** is at **20–30 Hz**; the ratchet band's cell reads
   **1.41×**, inside the null. The source document calls that table *"uninterpretable"* for a speed
   confound. The underlying routes are on **a different comma device** and are unrecoverable.

⇒ 🛑 **DO NOT RECOMMEND LOWERING THE LKAS GAIN.** Standing operator instruction — *"that is the whole point
of this work, to increase max LKAS capability (ideally linearly)"* — **and the evidence now agrees.**

**Consequently the authority trade curve is FLAT.** Raising authority does not move Path 2's Q. The limit is
**clamp headroom**, and the failure mode on saturation is **a jump to relay behaviour (Q → ∞)**, per V80.
🛑 **`gp-0x6bfc` and `gp-0x6b70` have never been measured against real driving** — sizing a rung on either
is blind exactly the way V84's `|r24| ≥ 1024` and V69's bit4 were blind.

**Best damping candidate: `0xC646E`** (INERTIA gain, 1428, single reader, 0 writers, never touched).
Phase vs rate **+14.7° @ 7.79 Hz**, real part positive across the entire 7.79–28.5 Hz band, never crossing
±90° ⇒ **dissipative by construction.** At **1–6% of its ±10 clamp**; a 4× raise lands at 4–24%.
⚠ **Open, and it applies to every lever in this family:** `gp-0x6b98` **gates** the FOC current loop, it
does not feed it — the cell carrying its magnitude into the Iq/Id reference **has never been located.**

---

## 6. Instrument defects found — these invalidate published numbers

1. 🛑🛑 **`q_of` returns Q = 79.00 on pure white noise**, above its own 54.73 window limit. `C31.q_of`,
   `_grind2_lib.q_of` and `_r47_imu_lib.q_of` are identically defective; `_r37_ratchet_lib` delegates.
   **25 files call one of them.**
2. **Every spectral damping estimator fails its control** — linewidth returns **38.7 for Q = 1**, total
   range 1.37× against a single-window spread of 1.79×. **No Q ratio between builds is reportable.**
3. **The amplitude ladder is largely a speed-census artefact** — `a779` falls with speed inside every route;
   the census alone predicts ×2.0–2.8 of the observed ×3.8–4.1; **V81's own drive moved 2.11× half-to-half,
   V84's segments span 20×.** ⇒ the V81-vs-V83a puzzle is a speed artefact, not a Lever B failure.
4. **The ENG/MAN column is largely moving-vs-parked** — manual median speed 0.00 m/s on V58 and V85.
   **Route `4c` is the only manual arm with real road speed, and it shows no coherent line.**
5. **32–38 Hz is marginal, not quiet** (1.9–2.0), **and contaminated for grind #2** (a 63.5 Hz object folds
   into it at fs = 100.2 Hz).
6. **Exposure rules corrected** — 5 engaged min/arm resolves **~1.7×**, not 1.2×. 🛑 **Q obeys a different
   rule entirely**: unbroken runs longer than the coherence time (37 s for Q=100). **V86 had 2.3 engaged
   minutes, V86B 1.5** ⇒ several recent "clean nulls" were underpowered by construction.
7. `_scratch/cache/r6e/r6e.npz`'s `probe_build` reads **V85** (an earlier note claiming `V80` was itself wrong).
8. **`0xC63AE`'s hazard text is backwards** — `Y[0] = 0` definitively, so lowering it **silences** the lane.
9. **"V86 ↔ V86B are single-variable" is FALSE** — two control cells differ.
10. **`FUN_0002214a`'s `andi` masks are state bitmasks, not tick dividers** — uniform 1 kHz, one tick delay.
11. **427 `MOTOR_TORQUE` is not "always ~0"** — 22.4% non-zero, 255 distinct values, checksum-guarded.

**Retracted mid-session, by their own authors, after controls:** a "Q ≥ 68 / pure tone / needle" reading
(estimator returned Q = 8,000,000 on a synthetic Q = 2.4 mode) · a "forest of ≥8 coherent peaks" (a
phase-randomised surrogate returns 8 peaks *more* prominent than the real data; only white noise had been
tested, the wrong null) · a "torque with minimal rim motion" physical story (rim rate carries the line;
the trough is at 8.67 Hz, not 7.8, and is 1.15× deep) · the orchestrator's own impedance/admittance
reconciliation (circular to 4.4e-16) and its effective-inertia hypothesis (refuted).

---

## 7. Next flight — none of it is a calibration edit

1. **Measure the reproducibility floor** — one fixed loop, twice, same day, current build. **0 flashes,
   ~40 min.** Every ratio in `BUILD-LINEAGE.md` assumes a floor that has never been measured.
2. **Deliberate ring-downs** — ~30 engage / hold-until-it-runs / disengage cycles per arm, **~10 min**.
   30 independent ζ from the one controlled estimator, against the 5 usable edges in all three routes.
3. **Manual-arm broadband protocol** — LKAS off, 2–4 m/s, both hands, *irregular* 5–15 shakes/s, ≥6 runs of
   25 s, then repeat engaged. The only route to the 8 and 12.8 Hz structural question. **0 bytes.**
4. **A telemetry channel that can see the motor side.** `0x1AB`: **3 bits at ~50 Hz**, one of which must be
   a fingerprint (information-theoretic — Honda never writes those bits, so `000` is identical to "cave
   absent"). **`0x18F`: 6 clean bits at 100 Hz**, under a standing hold. ⊕ Honda already sends motor torque
   on 427 — as **`|gp-0x6c18|`, absolute value**, so **no sign ⇒ useless for a transfer function.**
5. **A stock baseline has never existed.** ✅ A genuine stock `.rwd` is verified on disk —
   `39990-TVA-A160-RECONSTRUCTED-v9b-…`, sha256 `7ad6d49d…`, **0 differing bytes vs `code.bin`** over
   [0x13000, 0x100000). ⚠ *"v9b"* is the **cipher table name**, not a build. ⚠ Open gate: whether the
   bootloader validates the `/` part-number string.

---

## 8. Method rules earned

- 🛑 **Run the control BEFORE the measurement.** Four separate claims died to controls this session, three
  of them retracted by their own authors. An estimator that returns 38.7 for Q = 1, or Q = 8,000,000 for
  Q = 2.4, or 8 "peaks" on phase-randomised noise, looks exactly like a result until it is calibrated.
- 🛑 **Test against the RIGHT null.** White noise is the wrong null for a coloured, non-stationary
  background. That single substitution manufactured the "forest".
- 🛑 **Built-image bytes are a Python job. Ghidra is for structure.** A tracer read `0x3AA96` from stock
  `code.bin` — the only program it had open — and reported it as the current builds' value, inverting a
  conclusion.
- 🛑 **A chain of citations to a summary is not a measurement.** The keystone was quoted through three
  documents; reading its own table showed 1.41× where the summary said 63.66×.
- 🛑 **A frozen variable is invisible to every instrument, by construction** — and one that *migrates cells*
  while holding its value is worse, because the diff looks like a change.
- 🛑 **Score the quantity the lever moves.** V86's cell controls damping; the pre-registration read out
  frequency; the frequency was mode-locked and could not move.
