# SPEC — THE COMB TRANSIENT TEST: does the camera comb INITIATE the grinding, or does the loop merely AMPLIFY it?

Subagent `combsize`, 2026-09-10 (power analysis and recommendation revised 2026-09-11 after the
estimator adjudication). **DESIGN AND SPECIFICATION ONLY — nothing built, nothing changed in the fork,
nothing sent on any bus.**

---

## 0. THE HEADLINE RECOMMENDATION, AND IT IS NOT THE TEST I WAS ASKED TO SPEC

I was asked to specify a **one-frame interruption / phase-step** of `modelV2.action.desiredCurvature`.
I worked it and **it fails the power gate by 2–3×**, so specifying it as written would hand the operator
an uninterpretable null — a design failure on our side, not a verdict. I am specifying the manipulation
that answers the same question and **does fit one short drive**, and I state plainly why each rejected
variant was rejected.

| variant | dose | predicted ring effect | symptomatic engaged time needed | verdict |
|---|---|---|---|---|
| **one dropped/held model frame** | 50 ms hold | **6–13 % envelope dip** | ≫ 1 drive | 🛑 **REJECT — underpowered, and it costs up to 50 ms of LAG** |
| **phase-step the comb by π** | — | flips the locked half | n/a | 🛑 **REJECT — not reachable without touching the camera pipeline, and it tests coherence, which R2 has already measured at 0.51** |
| **sustained comb REMOVAL (A/B)** | comb → 0 | **−30 % envelope** | **≈ 48 s** | ⚠ right question, **2–3× too slow** |
| ⭐ **COMB DOSE–RESPONSE (ADD)** | ×1 / ×2 / ×3 | **+59 % / +125 %** | **≈ 10–15 s** | ✅ **RECOMMENDED** |

⭐ **The insight that makes it fit: it is far cheaper to ADD comb than to remove it.** Removing the comb
can change the ring by at most the locked fraction (−30 %); adding 2× more of it can change the ring by
+125 %, because in-band powers add. **Same physics, same question, ~16× the statistical power for the
same seconds of driving.**

---

## 1. THE MANIPULATION, EXACTLY

### 1a. What is added

At each `modelV2` publish (the camera frame clock, `f_model` = 19.9986–19.9997 Hz, fitted per route from
`np.polyfit(mdl_fid, mdl_t, 1)`), add to the curvature the fork already computes a term that reproduces
**the comb's own morphology** — a zero-order hold that steps once per model frame and is flat between
steps. `modelrate` measured that the plan is a **pure ZOH**: rms deviation from the hold mean is
**exactly 0.000e+00 on all six routes**, bit-identical inside every hold. So the comb is a pure staircase
and the injected term must be one too.

```
on each modelV2 publish k:
    c_inject[k] = G * s[k]                      # s[k] = the step the plan itself just took, held
    desiredCurvature_out = desiredCurvature[k] + c_inject[k]
G cycles over {0, 1, 2} on a fixed schedule (see 1c);  G = 0 is the untouched baseline arm.
```

`s[k]` is **the plan's own per-frame step**, re-used and held — not a synthesised sinusoid. That matters:
it inherits the real step-size distribution, which `modelrate` measured to be **violently heavy-tailed**
(median 0.09–6.45 raw counts, rms 12.6–63 raw counts). **A median-sized synthetic step would under-dose
the comb by ~10×.** Read `<tag>_step_curv` from
`rlog-tools/studies/grind/_scratch/modeld_comb_for_combsize.npz` for the distribution.

**Dose in engineering units.** `modelrate` measured the command gain in-band: r39 **56 187 raw 0xE4
counts per 1/m** (r22 30 962 · r35 94 700 · r5e 44 700 · r62 74 900 · r63 37 200). The existing
camera-locked comb on r39 is **≈ 20 raw counts** (my §1d, debiased). So `G = 2` adds ≈ 40 raw counts,
taking the comb to ≈ 60. **Bounds check: the openpilot slew cap is 122 counts/frame and `STEER_MAX` is
far above that, so a ×3 comb stays inside the command envelope the car already produces** — it is more of
exactly the signal that is already on the wire, not a new kind of signal.

### 1b. Why this variant, and why NOT the others — with the lag cost proved, not asserted

🛑 **The one-frame DROP/HOLD is rejected on TWO independent grounds, and the second is disqualifying.**

1. **Power.** Holding the previous curvature for one extra model frame withholds drive for 50 ms. With
   the mode's time constant τ = 1/(ζω₀) = **0.357–0.878 s** (ζ = 0.0091–0.0224 from `cyclekind`'s
   coherence times, f0 = 19.92 Hz, ω₀ = 125.2 rad/s), the envelope decays by only
   `1 − exp(−0.05/τ)` = **5.5 % (τ = 0.878 s) to 13.1 % (τ = 0.357 s)** before the drive resumes.
   Against a Rayleigh envelope whose per-sample relative SD is **0.523**, that is an effect size of
   d = 0.11–0.25 and needs **hundreds** of perturbations.
2. 🛑 **It costs LAG, which is the class the operator forbade by name.** Holding frame *k* means the
   command follows a plan that is one frame stale: **up to 50 ms of added group delay on that frame.**
   `memory/feedback/builds/feedback-no-openpilot-side-modifications.md` (amended 2026-09-10) permits
   fork-side changes **only** if they do not limit the model's connection or steering authority, and
   names **added command lag** as forbidden. **A dropped frame is a 50 ms lag event. It is out of scope.**

**The phase-step is rejected** because the comb's phase *is* the camera frame clock; stepping it means
retiming `modeld`'s publish, which desynchronises the whole vision pipeline. And it would test
**coherence**, which is already measured: `R2_deb` = **0.51** on r39's bar (§12 of
`rlog-tools/studies/grind/COMB-VS-ECHO-SIZING-2026-09-10.md`). We do not need to re-measure that.

⭐ **Why ADD is lag-free and authority-free, proved rather than asserted:**
- **Lag = 0 exactly.** The added term is a function of information already available at the instant the
  frame is published — `s[k]` is the step the plan *just* took. Nothing is delayed, buffered, held over,
  or filtered. The output at time *t* still depends on the newest model frame available at *t*. There is
  no state, no memory, and therefore no group delay at any frequency: `H_add(f) = 1 + G·(the plan's own
  ZOH transfer)`, whose phase contribution is identically that of the unmodified path.
- **Authority is not reduced; it is increased.** Nothing is attenuated, clipped, rate-limited or
  low-passed. `|H_add| ≥ 1` at every frequency. The forbidden class is things that *limit* the model's
  connection — this does the opposite. ⚠ **That is also its risk, and §5 treats it as such.**
- **The operator's amendment explicitly permits this class**: *"slope-continuous reconstruction… quantiser
  dither / error-feedback noise shaping"* are listed as allowed because they cost no authority and no lag.

### 1c. The schedule

**Toggle `G` on a fixed 2 s cadence, cycling 0 → 1 → 2 → 0 …**, switching only at a model-frame boundary.
2 s is chosen as ≳ 2 τ at the fastest plausible ring-down (0.357 s) and ≳ 2 independent envelope samples
at the slowest (0.878 s), so each arm reaches steady state *and* its onset transient is resolvable.

Log `G` on the wire so the analysis can be gated exactly. **One spare bit of an existing openpilot-side
log field is sufficient; do not consume an EPS cave bit — no firmware change is involved in this test
at all.**

---

## 2. THE READOUT, AND THE DISCRIMINATOR

### 2a. The readout

The **ring envelope**, by complex demodulation of the driver-torque bar (`0x1AB`-derived `bar`, ×1.024)
at the route's own demand-gated `f0`, Gaussian-smoothed σ = 35 ms, zero phase — `burst_onset_triggers.demod_env`,
the detector already validated against the r35 incident to 0.4 s on onset and 0.02 s on peak. **Not a
bandpass:** a 4 Hz bandpass has a ~250 ms impulse response and would smear the very transient being measured.

Two statistics per dose arm:

1. **STEADY-STATE LEVEL** — median envelope over the last 1.0 s of each 2 s arm (after ≥ 1 τ of
   settling). This is the dose–response.
2. **ONSET/OFFSET TRANSIENT** — fit `env(t) = A_∞ + (A_0 − A_∞)·exp(−t/τ̂)` to the 1.0 s following each
   `G` change, pooled over cycles. **τ̂ is a direct measurement of ζ_eff = 1/(τ̂·ω₀)** — the number §X3
   showed every sufficiency verdict in this kit is hostage to.

### 2b. The two predicted curves, with numbers

Baseline r39: locked energy fraction **0.51**, free **0.49** (debiased, §12). Under **incoherent
superposition** of an independent added drive, the envelope scales as
`A(G) / A(0) = sqrt(E_free + (1+G)²·E_lock)`:

| G | added comb | **A(G)/A(0) if the comb drives the ring** | **A(G)/A(0) if the loop is amplifying something else** |
|---|---|---|---|
| 0 | — | 1.00 | 1.00 |
| 1 | ×2 total | **1.59** | ≈ 1.0–1.15 |
| 2 | ×3 total | **2.25** | ≈ 1.0–1.25 |

And the transient after each step:

| hypothesis | τ̂ | asymptote after returning to G = 0 |
|---|---|---|
| **rung mode** (excitation-limited) | **0.357–0.878 s** (5–17 cycles at 19.9 Hz) | returns to 1.00 |
| **regeneratively sustained** (ζ_eff → 0) | **≫ 1 s**, or no resolvable decay | stays elevated |

### 2c. The statistic that separates them

**Fit `log A(G)/A(0) = α · log(1+G)` and report α with a bootstrap CI over cycles.**

- **α ≈ 1.0** ⇒ the ring tracks the comb proportionally — **the comb is a genuine driver** and the
  incoherent-superposition model holds.
- **α ≈ 0** ⇒ the ring is indifferent to the comb — **amplifier; the comb is incidental.**
- **α ≈ 0.5** is the null-model value for a *purely* incoherent addition where the comb is only its
  measured share; values above it mean the comb is over-represented.

⭐ **And the built-in control that makes it a real experiment rather than a dose ramp: on a fourth arm,
inject the SAME amplitude at a DETUNED clock** (f_model + 0.5 Hz — still inside the 18–22 Hz ring band,
but not on the camera clock). If the ring responds to the on-clock arm and **not** to the detuned arm, the
effect is the **clock**, not merely energy in the band. If both respond equally, the mode simply
integrates any in-band drive and the camera clock is not special. **This control is what makes a positive
result mean something, and it costs one extra 2 s arm.**

---

## 3. 🛑 POWER — the gate, computed, and one variant fails it

**Inputs.** The ring envelope is **Rayleigh** (`cyclekind`, measured), so relative SD per independent
sample is `sqrt(4/π − 1)` = **0.523**. Independent samples arrive every coherence time, which `cyclekind`
measured **equal to the ring-down time**, τ_c = **0.357–0.878 s**; take **0.5 s**. A 2 s arm therefore
yields **≈ 4 independent samples**. Two-sided α = 0.05, 80 % power: `n = 2(1.96+0.842)²/d²`.

| test | effect to detect | d | n per arm | arms | **symptomatic engaged time** | fits one drive? |
|---|---|---|---|---|---|---|
| one dropped frame | 5.5–13.1 % | 0.11–0.25 | 250–1300 | 2 | **≫ 10 min** | 🛑 **NO** |
| sustained REMOVAL | 30 % | 0.574 | 48 | 2 | **≈ 48 s** | ⚠ **NO — 2–3× over budget** |
| ⭐ **DOSE ×3** | **125 %** | **2.40** | **3** | 2 | **≈ 3 s** | ✅ **yes** |
| ⭐ **full 4-arm protocol** | α with CI | — | 5/arm | 4 | **≈ 10–15 s** | ✅ **yes, with margin** |

**The operator gives ~15–30 s of symptomatic engaged driving per drive and stops the moment he feels the
symptom.** The 4-arm dose–response protocol needs **≈ 10–15 s** and therefore fits, with margin for one
aborted cycle.

🛑 **STATED PLAINLY, AS INSTRUCTED: the one-frame interruption I was asked to specify CANNOT be done in
one short drive, and neither can the sustained-removal A/B.** The removal test would need **≈ 48 s** of
symptomatic engaged time — realistically **2–3 drives with matched episodes**, which the kit's own
doctrine rules out as unbuildable. **If the removal test is wanted anyway, it must be run as the
confirmation of a positive dose–response, not as the discriminator.**

---

## 4. PRE-REGISTERED OUTCOMES — written before it runs

| result | reading | what it licenses |
|---|---|---|
| **α ≥ 0.8**, CI excluding 0.3; on-clock ≫ detuned; τ̂ ∈ 0.36–0.88 s | the ring tracks the comb, the clock is what matters, and the mode is excitation-limited | ⭐ **INITIATOR.** A comb-removing fork-side reconstruction is worth building and worth a drive. Expected benefit ≈ **29 % amplitude** (from lock fraction 0.51). |
| **α ≤ 0.3**, CI excluding 0.8 | tripling the comb barely moves the ring | 🛑 **AMPLIFIER.** The comb is incidental; **close the excitation-side class for good** and put every remaining effort on ζ_eff (EPS-side damping). |
| **α ≈ 0.5**, on-clock ≈ detuned | the mode integrates any in-band drive; the camera clock is not special | **NEITHER — the band matters, not the clock.** A comb fix buys only its energy share and is not worth a bespoke lever. |
| τ̂ ≫ 1 s or no resolvable decay | the loop is near self-sustaining | **Independent of α: ζ_eff is the lever.** Also flags that the ×6.00 ceiling used throughout this kit is too conservative. |
| CIs span 0.3–0.8 | underpowered | **AMBIGUOUS. Report as such and do not interpret.** Remedy: more cycles, or raise the top dose to G = 4 (predicted ratio 3.64, d = 5.05) — subject to §5's dose gate. |

⚠ **An ambiguous result is a real possible outcome and is not a verdict about the comb.** The remedy is
stated above so it does not have to be invented after a wasted drive.

---

## 5. SAFETY AND DRIVEABILITY — treated conservatively, because this is a live steering command

**What the manipulation physically does.** It adds, at the camera frame rate, a bounded staircase to the
curvature request. At `G = 2` on r39 that is **≈ 40 extra raw 0xE4 counts** of 20 Hz content on top of
≈ 20 already present.

**What bounds the risk:**
- It is **the same kind of signal already on the wire**, tripled — not a new mode of actuation.
- It stays **well inside the existing command envelope**: the openpilot slew cap is 122 counts/frame, so
  a ≈ 60-count comb cannot reach the rate limiter.
- It adds **no lag and no attenuation** (§1b), so the underlying path's stability margins are unchanged.
- It is **fork-side only** — no flash, no EPS change, none of this kit's bricking exposure — and is
  reverted by setting `G ≡ 0`.

🛑 **What is NOT safe about it, said plainly:**
- ⭐ **This is a PROVOCATION test. At `G = 2` it is predicted to make the grinding ~2.25× LOUDER for 2 s
  at a time. The operator WILL feel it, and that is the point.** He must consent to that specifically
  before it runs; it must not be presented as a neutral instrument.
- **It must be gated to low speed and a clear road** (v < 12 m/s, where the grinding census lives anyway),
  and to `latActive` — and the operator must be able to kill `G` instantly.
- **Start at `G = 1`, not `G = 2`.** If `G = 1` alone gives a clean α, the higher dose is never needed.
  The predicted effect at `G = 1` (+59 %, d = 1.13) needs **13 samples/arm ≈ 6 s/arm**, still inside one
  drive.
- **A smaller dose still discriminates**, at a time cost: `G = 0.5` predicts +28 %, d = 0.53, **55 samples
  per arm ≈ 27 s/arm** — i.e. it no longer fits one drive. **So the dose–time trade is explicit: `G = 1` is the smallest dose that fits one drive.**
- If the operator finds `G = 1` unacceptable, **the test cannot be done in one drive and should not be
  attempted** — say so rather than shrinking the dose into an uninterpretable null.

---

## 6. ⭐ STEP ONE IS OFFLINE, AND IT COSTS NOTHING

**Yes — and it must happen first.** The manipulation is entirely upstream of the EPS, so its *drive-side*
effect can be computed exactly from recorded data with no car and no drive.

**Offline step 1 — confirm the dose lands where it is supposed to.** For r39 (V282, the only clean mirror
route):
1. Read `<tag>_step_curv`, `<tag>_hold_len`, `<tag>_cnt_per_curv`, `<tag>_f_model`, `<tag>_model_icept`
   from `rlog-tools/studies/grind/_scratch/modeld_comb_for_combsize.npz`.
2. Synthesise `c_inject` for G ∈ {0, 1, 2} and the detuned control arm; convert to raw 0xE4 counts via
   `cnt_per_curv`; add to the recorded command.
3. **Check the dose actually landed**: `R2_deb` and the in-band amplitude of the modified command at the
   camera clock must rise by the intended factor, measured with `modeld_phase_lock.r2_full`. The detuned
   arm must show **no** rise in `R2_deb` at `f_model` — that validates the control before it is flown.
4. Run each modified command through the **byte-exact 1 kHz mirror** (`grind_incident_r35.simulate`) and
   report the delivered in-band torque per arm, on the same axis as everything else in this workstream
   (my §1b: r39 command leg 11.56 counts of 57.21 total).

**What offline CAN establish:** that the injection reproduces the comb's morphology; that the dose is the
intended multiple; that the detuned control is properly detuned; and the exact **delivered drive** change
per arm. **All of that is precondition, and all of it is free.**

🛑 **What offline CANNOT establish, and this is why the drive is unavoidable:** `GI.simulate` is
**open loop** — it reads the *measured* 0x18F wheel rate as its feedback and cannot produce the plant's
response to a command that was never sent. **The ring lives in the plant-plus-loop, which the mirror does
not close.** So offline gives the x-axis of the dose–response exactly and **none of the y-axis.** Anyone
who reports a predicted ring response from the mirror has mistaken the drive for the answer.

**openpilot's own replay** can validate that the fork change produces the intended `desiredCurvature`
stream and that nothing else in the lateral stack reacts badly to it — worth doing, and equally free —
but it has the same limitation: it does not contain the car.

---

## 7. WHAT THIS TEST DOES AND DOES NOT SETTLE

**Settles:** whether the ring's amplitude tracks the camera comb's amplitude, at a dose we choose, with a
detuned control that separates "the clock" from "energy in the band"; and — as a free by-product from the
onset transients — **ζ_eff measured directly**, which §X3 showed is the assumption every sufficiency
verdict in this kit rests on.

**Does not settle:** whether removing the comb would *cure the symptom the operator feels*. 🛑 **The
standing warning: V289 is already the flown experiment for "remove the 20 Hz forcing from the loop" — its
notch removed the 20 Hz object entirely (0/1414 windows) and the grinding relocated to 15–17 Hz and got
WORSE** (matched speed × demand, r63's ring is **1.71×** r39's on **0.30–0.45×** the command drive).
**A positive α licenses building the comb fix; it does not predict that the symptom goes away.**

**Cost if it returns AMPLIFIER:** one short drive, and it closes the excitation-side class permanently —
which is worth it, because that class has now consumed V288 (whose null was void), this session, and
three agents.
