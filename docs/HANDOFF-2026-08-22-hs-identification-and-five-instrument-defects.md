# HANDOFF 2026-08-22 — `H(s)` identification: five instruments retired or rescaled, and the orchestrator's own premise falsified

**Measurement-only session. NO BUILD. Nothing flashed, no CAN, no UDS, no openpilot file modified.**
**On the car: V103, unchanged. V104 remains the current unflashed candidate.**
Two subagents (`rec1-coherence`, `rec2-ringdown`), both confirmed stopped from the harness before
close-out; both repos verified from disk (only untracked additions, zero tracked-file modifications).

---

## 0. How this started, and why it is worth reading

The operator asked for the "steering wheel feel tracker" — driver torque plus calibrated inertia and
friction. That is **`FUN_0003b8f6`** (§1). It led to a design question: *if we were Honda's engineers
adding LKAS, how would we stop it feeding back into the driver-torque path?* The answer needed
**`H(s)`**, the transfer from motor torque to torsion-bar torque, so a decoupler could be designed.

The orchestrator asserted that `H(s)`'s dominant factor is a **wheel-inertia resonance at ~8 Hz**, and
built an architecture argument on it (a 180° phase rotation through that mode ⇒ no scalar decoupler can
work). **That premise was then measured and is wrong.** The session's real product is that the
measurement happened *before* a build was cut on the premise, and that five instruments the kit has been
quoting were retired or rescaled on the way.

---

## 1. The tracker — `FUN_0003b8f6` @ `0x3b8f6` (answering the original question)

1 kHz plant-model / disturbance observer. Sole caller `FUN_0002214a` @`0x2240e`.
Gate: `|gp-0x6b98| ≤ 0x2000` (tautology — producer pre-clamps) · `|gp-0x4f60| ≤ 0x6400` ·
`|gp-0x6abc| ≤ 13000` · `gp-0x6752 ∈ {−1,0,1}`; else it writes the `0x7FFF` sentinel and the lane drops.

```
model    = EMA2(gp-0x6b98 * pol / 1024, a=0xC40D4/4096)                        # command branch
         + clamp(FIR(EMA2(gp-0x4f60/1024, a=0xC40D8/4096) * 0xC613A/32768), ±15)
           * LERP13(gp-0x6a10, X@0xC6B66, Y@0xC6B80)/1024                      # DRIVER TORQUE branch
iVar20   = pol * gp-0x6abc * 12                                        @0x3bab0
ratio    = clamp(iVar20 / cal(0xC40BC), ±1)                            @0x3bab4..0x3bae4   <-- RELAY
FRICTION = clamp(EMA(|model|*ratio*K1/1024 + K0/1024*ratio, a=0xC40D0/4096), ±10)  K1@0x3bafe K0@0x3baf6
INERTIA  = clamp(EMA2(d(iVar20)*0.5*17.453293, a=0xC40D6/4096) * 0xC646E * 2^-24, ±10)
gp-0x6bfc = clamp((model − FRICTION − INERTIA) * 0xC6468, ±20000)      @0x3bbbe..0x3bc1a
```

Cals re-read from the stock image this session: `0xC40D4`=573 · `0xC40D8`=3686 · `0xC613A`=1159 ·
FIR `0xC4048/4C/50` = 1.0f/0.0f/0.0f (degenerate passthrough) · **`0xC40D2` K1 = 102** ·
**`0xC4080` K0 = 0** (🛑 never raise — latent pure relay) · `0xC40BC` = 600 · `0xC40D0` = 408 ·
**`0xC646E` J = 1428** · `0xC40D6` = 246 · `0xC6468` = 2639. LERP13 Y = 899…1084.

**Two corrections to the operator's recollection, both confirmed:**
1. It is **command-dominated, not driver-torque-driven** — branch A outweighs branch B ~27–32:1 per
   equal-magnitude count at DC (branch A reaches ±8.0, branch B ±0.88).
2. **The output is a torque residual, not an angular acceleration.** The acceleration is real
   (`d/dt(rate) × 1000·π/180` @`0x3bb4e`–`0x3bb6a`) but is immediately multiplied by the preset inertia
   gain `0xC646E` — i.e. `J·α`, a torque. Pinned by the consumer: `FUN_00038148` @`0x38238`–`0x3823A`
   differences it against a six-lane **torque** sum with coefficient **exactly −1** (`subr r15,r6`,
   opcode `0x0C`). A torque cannot be subtracted from an acceleration. **[EVIDENCE]**

**19 command-path carriers of `gp-0x4f60`** (73 accesses found by operand scan; the kit's raw
dual-encoding scan puts the true total at 76 — `search_instructions` undercounts). Heaviest three:
`FUN_0003a382`'s PID setpoint (`0x3A7CA`), lane-9 CORDIC (`FUN_0002eda8`, 3 reads → `gp-0x6b6c`), and
aggregator terms 3 and 5. All three `gp-0x4f60` monitors compare against **literal constants only**, so
there is no V27-class raw-vs-filtered lockstep on this cell.

---

## 2. THE HEADLINE — the passive column cannot host the 8.16 Hz line

`rlog-tools/plant_phase_corner.py`, `plant_Jb_absolute.py`, `plant_falsifiers.py`.
**Orchestrator re-ran all three and checked the arithmetic independently.**

### The single-bin form — immune to every band-consistency objection
Hands off, the upper column obeys `J_w·θ'' + b_w·θ' = −T_bar`, so `Z = T_bar/Ω_w = −(b_w + jωJ_w)` and
`tan(180° − |arg Z|) = ω·J_w/b_w`. Since `Q = ω_n·J_w/b_w`, **at `ω = ω_n` these collapse:**

> **`Q(at the mode) = tan(180° − |arg Z|)`, from ONE bin.** No band, no `k`, no counts scale, no deg/s
> scale, no cross-frequency model.

| route | eps | coh² | \|arg Z\| @8 Hz | Q | Q [95 % CI] |
|---|---|---|---|---|---|
| **V9b STOCK** | **13** | 0.742 | **117.4°** | **1.93** | [1.51, **2.77**] |
| V103 | 6 | 0.842 | 132.2° | 1.10 | [0.30, 1.33] |
| V102 | 8 | 0.759 | 150.2° | 0.57 | [0.41, 0.64] |
| V88 | 4 | 0.711 | 131.4° | 1.13 | [0.96, 1.27] |
| V100 4x | 3 | 0.888 | 117.2° | 1.94 | [0.85, 2.08] |

**Q = 10 would require `|arg Z| = 95.71°`** (`Z` within 5.7° of pure inertia). Measured 117–150°.
Verify in one line: `tan(180−117.4) = 1.93`; `180 − atan(10) = 95.71`.

### The absolute fit, and the physical check it could have failed
Scale resolved from data (§3.2). 4–12 Hz, episode bootstrap 3000, engaged hands-off:
**STOCK `J_w` = 1.248 [1.110, 1.358], `b_w` = 35.8, `b/J` = 28.7 rad/s** · **V100 `J_w` = 1.202,
`b_w` = 35.0, `b/J` = 29.1** — **two independent drives agreeing to 4 % on `J_w` and 2 % on `b_w`.**
⭐ **`J_w` = 0.033–0.078 kg·m², against the handbook 0.03–0.06 that `ANALYSIS-2026-08-20` §2 itself
assumed.** An absolute number landing on the range the disputed analysis presupposed.

🛑 **`J_w s²` is NOT dominant at 6–9 Hz — merely the larger term.** Column corner **4.6 Hz**;
`|J_w ω|/b_w` = 1.32 / 1.64 / 1.97 at 6 / 7.5 / 9 Hz ⇒ **the damper carries 45–60 % of `|Z|`.**
⇒ **The orchestrator's premise is wrong by ~2× in magnitude and ~55° in phase.**

### 🛑🛑 THE ONE UNTESTED ASSUMPTION — cite it every time
Falsifier **F1** was a **manual (LKAS-off) + hands-off** arm. The data **exists** — 98 windows, 502 s
corpus-wide — it had simply not been run. Run: **coherence at 4–10 Hz is 0.005–0.016, 20–60× below the
falsifier's own 0.30 gate.**
⇒ **F1 IS UNTESTABLE ON THIS CORPUS FOR A PHYSICAL REASON.** LKAS-off *and* hands-off means no
4–14 Hz excitation, so the cross-spectrum measures noise. This is
`accord-vibration-requires-lkas-engaged` (9,200× less power) from the other side: **the excitation the
estimator needs only exists when engaged.** A scripted maneuver cannot close it either
(`lateralManeuverPlan` requires `latActive`). **Closing it needs a bench measurement of the column.**

⇒ The conclusion rests on engaged arms **plus the anti-damping direction argument** (loop anti-damping
reduces apparent `b_w` ⇒ engaged `J/b` overstates passive ⇒ measured Q is an upper bound). Directionally
sound, **load-bearing, and the weakest link.**

### Falsifier F2 and the arm spread
**F2** (per-bin CV > ~0.5 on bins with coh ≥ 0.50): **4 of 5 survive** — STOCK 0.146, V103 0.454,
V88 0.181, V100 0.376 — **V102 genuinely TRIPS at 0.721**, not explained away. Post-hoc: no route shows
a *localised* 8 Hz excursion (7.5–9 Hz residual −0.85…+0.83 sd; V102 least at +0.07); V102's failure is
a steep *smooth* slope. ⚠ **The log-log slope is negative on EVERY route (−0.51 to −4.32) where a pure
`J·s+b` demands zero** ⇒ systematic smooth model error everywhere. The single-bin form is immune.
**Arm spread:** hands-on is a different mechanical system (the identity assumes zero driver torque), so
arms must differ — control C4 passing, not an inconsistency. **Hard bound over EVERY arm, admissible or
not: most permissive upper 95 % CI is Q = 5.24–7.34. No arm reaches Q = 10.**

### How to state it
> *"The passive upper column, as measured engaged and hands-off, cannot support a Q≈10 resonance at
> 8.16 Hz; the passive-arm cross-check that would rule out a loop artefact in that measurement is not
> available on this corpus."*

🛑 **A STRONG CONSTRAINT WITH ONE NAMED UNTESTED ASSUMPTION — NOT a retraction of
`accord-ratchet-is-a-lightly-damped-resonance`.** Corroborates `accord-the-8hz-mode-is-the-loop-not-the-plant`
from an independent instrument.

---

## 3. FIVE INSTRUMENT DEFECTS — every one found by running a control BEFORE a measurement

### 3.1 Both ring-down estimators saturate at ζ≈0.05 and REVERSE
`rlog-tools/ringdown_validate.py`. f_n = 8.16 Hz, 40 reps/cell, SNR 20 dB, truth ζ 0.005→0.200 (40× span).

| estimator | ρ | dynamic range | verdict |
|---|---|---|---|
| E1 `hilbert_env` — *"the only estimator that passed its control"* | +0.829 | **7.6×** | 🛑 does not order |
| E2 `demod` | **+0.371** | **1.7×** | 🛑 does not order |
| **E3 matrix pencil (NEW)** | **+1.000** | **41.3×** | ✅ |

`0.200 → E1 0.0359 / E2 0.0084` — **E2 is 24× too lightly damped.** And the **fit-window length alone**
swings E1 by **3.5×**, E2 by **6.3×**; E3 is flat (0.0460→0.0483 over 0.5–4.0 s).

⇒ 🛑 **`rlog-tools/_stock_r97_ringdown.json` is UNQUOTABLE.** Route 0x97 has **exactly one qualifying
edge** at that script's own criteria; **E3 refuses it while E1 at `fit_s = 2.0` returns ζ = 0.0030, i.e.
Q = 167.** ⇒ 🛑 **the recorded `ζ 0.017–0.036 / Q 14–29` is an E1 number ⇒ Q is an UPPER BOUND.**

**E3 refuses every null** — 0/40 white noise, 0/40 perfect step, 0/40 phase-randomised real-data
surrogate, 0/200 step in the separation test — while returning ζ 0.0490 [0.0445, 0.0530] on 200/200 true
ζ = 0.049 decays. E1/E2 return a *finite* ζ on **40–55 % of pure-noise draws** (the `q_of = 79.00`
failure mode, still live in the kit's code). Sensitivity sweep passes: recovery identical to 4 dp across
{residue, min-ζ} × gate {0.15…0.65}; only gate 0.65 breaks it.
🛑 **E3's own self-reported defect: the ANALYSIS WINDOW LENGTH moves it** (detections at A=4:
3/7 @0.75 s → 0/7 @3.0 s). Any future use must state the window.
🛑 **And the real-data null licenses nothing** — the positive control says **0/7 at A=1 across all 50
setting combinations**. Both the kit's number and this 0/7 are honest nulls; neither is evidence.

### ✅ NOT a defect — `Q 10.21` vindicated, and the bracket closes
Run in its own configuration (white-noise-driven 2-pole, 400 s @100 Hz, Welch NFFT 512), the 2026-08-20
fit recovers 0.0525 at truth 0.049 — **essentially unbiased**. Its one vulnerability is broadband
contamination, which biases ζ **HIGH** ⇒ Q **smaller**. Measured floor/peak = **0.033** (spread
0.009–0.186) ⇒ bias 1.14× ⇒ **true ζ ≈ 0.0412, Q ≈ 12.1 [10.7, 13.3]. UNDERSTATED, not overstated.**

### 3.2 `rate_f` is 0.7996× true deg/s — and `rate_c`/`rate_f` are ONE channel
`plant_scale_resolve.py`. `ang == wang == cs_ang` bit-for-bit ⇒ its degree scale is the DBC's. At
0.2–0.7 Hz (SNR ~300): **`rate_c` gain 0.9994 [0.9671, 1.0236]**, `rate_f` **0.7996**, coherence
0.95–0.999 over 12 windows / 6 routes. ⇒ **`rate_c = 1.2506 × rate_f`, identical phase.**
🛑 **Any past `|Z|`/impedance/inertia on `rate_f` is 1.25× too large**, and any "agreement between
`rate_c` and `rate_f`" is **vacuous**. Ratios like `J/b` are untouched.

### 3.3 427's source cell changes build to build
Read from the images at `0x55DF2` / `0x55E10`: **eight sources, four `sar` shifts.** Full map in
`memory/accord-427-source-cell-changes-by-build.md`. **Only r71/r73/r75/r76 (V87–V89) carry
`gp-0x6B98`.** And 427 ships `|cell| >> shift` — **RECTIFIED** — so a directed cross-spectrum needs the
sign, and **only V88/route 73 has a cave on the same cell**. Rectified routes give γ² = 0.0018–0.0119 at
0.5–3 Hz against route 73's **0.53**. Signed reconstruction validated: ±2-row skew moves H1 <3 %, and
`(raw14_t, raw14_b4)` reproduces `(t, probe)` **bit-identically**.

### 3.4 427 aliasing is band-dependent — 20–24 Hz is a NULL, never a magnitude
`fs = 49.835 Hz`. Fold onto **6–9 Hz** (from 40.8–43.8 Hz): ratio **0.0031 / 0.0200 / 0.0204** ⇒
negligible, ~1 % on derived amplitude. Fold onto **20–24 Hz** (from 25.8–29.8 Hz): **0.23 / 2.57 / 0.28**
— on route 75 the folded energy is **2.6× the true in-band energy**. Same error class as the retracted
30–49 Hz control band, pointed the other way.

### 3.5 0x18F staleness is 12.5 ms, and `ang` is quantisation-limited in band
`arg(rate_f / d(ang)/dt)` is linear at **−4.51 deg/Hz** across 2–24 Hz ⇒ **12.5 ms, not the recorded
~10.** And `ang` (LSB 0.1 deg) has 6–9 Hz band-RMS 0.0155–0.032 deg against a 0.0071 deg quantiser floor
(SNR 2.2–4.8, below one LSB); `|rate_f / d(ang)/dt|` falls to 0.15 by 20 Hz ⇒ **~7× pure noise there.**
🛑 **Never differentiate `ang` as an in-band denominator.**

---

## 4. The openpilot excitation ceiling was wrong by 41× — and the lane is transparent at 8 Hz

### The correction [orchestrator-verified TWO ways]
`STEER_DELTA_UP = 3` is **3 normalised units/s applied BEFORE the ×`STEER_MAX`**, not 3 counts/frame.
`carcontroller.py:291` rate-limits `torque_cmd` while normalised; `×STEER_MAX` is 14 lines later at
`:305`. `DT_CTRL = 0.01`, `STEER_MAX = 4096` (`interface.py:137`) ⇒ **12,288 ct/s.** The comment on
`values.py:39` says it: `# min/max in 0.33s for all Honda`.
**Bus confirmation:** p99 `|Δe4|` = **123 ct/frame** on r75 and r76 vs `0.03 × 4096 = 122.88` — bit-exact;
**67–73 % of engaged frames already exceed the wrong ceiling.**
⇒ clean-sine ceiling **244.5 ct at 8 Hz** (not 5.97), 93.1 ct at 21 Hz.
⊕ **The panda does not constrain 0xE4 while engaged** (`honda.h:267-275`) — nothing needs raising.

### The measured transfer (route 73, engaged hands-off, 224 s / 21 blocks / 55 windows)
| band | γ² [95 %] | shuffled p50/p95 | H1 |
|---|---|---|---|
| 0.5–3 Hz | **0.5304** [0.385, 0.680] | 0.0043 / 0.0234 | **1.027** |
| 6–9 Hz | **0.0225** [0.0084, 0.0485] | 0.0016 / 0.0060 | **0.72–1.07** |
| 20–24 Hz (control) | **0.0007** | 0.0009 / 0.0039 | — |

**Control band sits AT the null ⇒ clean instrument.** ⇒ **band ratio 0.71–1.06 — essentially NO
attenuation.** Corroborated from firmware: arbitration IIR corner **5.05 Hz at 1 kHz**, gain **0.534**
at 8 Hz. 🛑 **Scopes `reference-accord-lkas-lane-is-a-lowpass` to ≥~10 Hz** — its blanket claim is too
strong at 8 Hz. It stands at tens of Hz.

### The decision it would have supported (NOT BUILT)
8 Hz sine, **A = 100 ct (41 % of the limiter budget, 2.4 % of full scale)**, 15 s dwells, engaged +
hands-off ⇒ **γ² ≈ 0.88** on `gp-0x6b98`. Worst required amplitude anywhere in the with/without-aliasing
table is 36.6 ct against a 244.5 ct ceiling — **6.7× margin.**
🛑 **Operator scoped the session to analysis only.** It is an openpilot-side change against a standing
instruction, and it injects into the band he calls grinding. **Not built. His call, open.**

### 🛑 A result found and killed by its own author
`γ²(e4, torsion bar)` at 6–9 Hz = **0.085 / 0.138 / 0.280** (r73/75/76), 67–538× the null, control clean.
**REVERSE CAUSALITY.** Kills: (1) `γ²(e4, ANGLE)` is **higher** — 0.399 / 0.526 / 0.709 — and `ang` is a
current-frame field with no staleness; (2) the bar gain rises **6–11× with near-zero phase**
(−1.8/−6.6/−9.2°), which is a same-frame algebraic relation, not actuation; (3) the bar ratio tracks
`γ²(e4, ang)` across routes.
⚠ A 4th kill (zero-lag cross-correlation) was **withdrawn by its author** — `tq` IS `0x18F` held-last onto
the `0x14A` grid, so lag-0 bounds the true lag to ±10 ms rather than proving zero. Kills 1–3 stand.
⇒ **openpilot's command is NOT exogenous at 6–9 Hz. Never pre-register column torque as a co-primary
against an 0xE4-derived quantity.** Corollary: an injected tone is the only exogenous input available.

---

## 5. The lateral maneuver tool (StarPilot) — assessed, not used

`tools/lateral_maneuvers/lateral_maneuversd.py`, consumed at `controlsd.py:472-473`.
**Runnable as written** — params registered, process wired (`process_config.py:159`, gate `:49`),
`lateralManeuverPlan` at 20 Hz, no car whitelist, UI toggle present, Honda Bosch `minEnableSpeed` 3 mph.

🛑🛑 **B0 — BLOCKER: no extractor captures `lateralManeuverPlan` or `alertDebug`. Without the logged
trigger the drive is UNANALYSABLE.** And no amplitude threshold can recover the trigger post-hoc: the
step onset sits at ordinary driving's **99.99th percentile** (0.500 vs p99.99 = 0.460 over 10 frames) and
the reversal at its **maximum** (1.000 vs max 1.015 over 20 frames).
⭐ **Corollary the operator should be told: the maneuver is NOT a bigger shove than ordinary driving.**
Its entire value is the **known trigger instant** and **~36 replicates** (√36 = 6× SNR).

Other blockers: **B1** aborts on `steeringPressed` ⇒ hands-off only ⇒ **this drive measures the PLANT,
not the symptom, and must not be scored against grinding/ratcheting** · **B2** hard road gates
(500 m radius, 4.6° roll, ±0.7 m/s, 2 s stable) · **B3** manual ACC at 20 then 30 mph · **B4** 0.5 m/s²
≈ **16° of steering at 20 mph** · **B5** `LateralManeuverMode` is CLEAR_ON_MANAGER_START · **B6**
`LongitudinalManeuverMode` must be OFF · **B7** the two 0.5 Hz sines contribute nothing and cost ~1/3 of
the drive (skipping needs an openpilot edit — don't; just don't analyse them).

🛑 **Excitation limit:** `drive_helpers.py:clip_curvature` slews at `MAX_LATERAL_JERK = 5.0 m/s³`, so the
delivered input is a **ramp** of `|Δa|/5.0` s with `|sinc(fT)|` spectrum ⇒ **pre-declared EXCLUDED bins:
9.5–10.5 Hz always, 4.5–5.5 Hz on reversal edges.** A dip there is openpilot's jerk limiter — reporting
it would be the V97 failure class. The 12–19 dB attenuation is **not fatal** (`H = T/u` is a ratio; the
sinc divides out except at a null) — it costs coherence, not accuracy.

**Pre-registration written before any drive:** `rlog-tools/prereg_maneuver_hs.py`.
**E1 (primary, scale-free):** `Q_implied(8.16 Hz)`; **PASS-LOOP ≤ 3**, **PASS-PLANT ≥ 7**, ambiguous
between, claimed as ambiguous. **E2 (shape):** `|T_bar/e4tq|` peak vs the 3–5 Hz level; PASS-PLANT ≥ 5×
with peak in 7.5–8.8 Hz, PASS-LOOP ≤ 2.5×. ⭐ *This is what the drive actually buys:* on ordinary driving
`e4tq` is not exogenous (§4), which is why the 2026-08-20 `12.38 at 7.90 Hz` is ambiguous — **under a
scripted open-loop step, if the peak survives it is the plant; if it collapses, the 12.38 was feedback.**
**E3 (ring-down, secondary):** quotable only if E3 fires on ≥ 8 of ~18, else declared underpowered.
🛑 **Honest "could we tell?" — YES for E1 and E2, NO for E3.** If a drive is justified on the ring-down
alone, **it is not ready.**

---

## 6. OPEN ITEMS — with what closes each

| # | item | what closes it |
|---|---|---|
| 1 | 🛑 **`\|Z\|` rolls off un-modelled above ~13 Hz** (STOCK `\|Z\|/ω`: flat 1.54→1.33 over 6–12 Hz, then 1.15 @14, 0.45 @16). **If `tq` is internally low-passed there, every kit `\|Z\|` above ~10 Hz inherits it — including the 21–24 Hz work.** Not rate-channel noise, not torque noise. | Ghidra trace of the `0x18F` torque path for an internal filter; or a swept comparison against an unfiltered tap |
| 2 | Systematic smooth error in the 2-parameter column model (log-log slope −0.5…−4.3 where 0 is required); V102 trips F2 at 0.721 | a 3-parameter model, or identifying the extra low-frequency torque term |
| 3 | **F1 untestable** — no LKAS-off excitation exists | a **bench** measurement of the column |
| 4 | `\|gp-0x6b98\|` engaged p50 = **664 ct** vs record's **208** | reconcile which mask produced 208 |
| 5 | `\|ang\|` 6–9 Hz = **0.0155–0.032 deg** vs `ANALYSIS-2026-08-20`'s **0.089** | reconcile masks |
| 6 | 2-pole fit lands at **10.5 Hz**, not 8.162, under an explicit hands-off mask | resolve the §2 mask |
| 7 | C2 Coulomb test underpowered (`d log b_w/d log V = −0.11 [−1.12, +0.72]`) | a rate range wider than the 1.0–5.3 °/s hands-off windows give |
| 8 | 6–9 Hz forward gain bracketed **0.5–1.07**, not pinned | circular on existing data — needs the injection itself |
| 9 | Extractor captures neither `lateralManeuverPlan` nor `alertDebug` | an extractor change (specified, not written — no openpilot edit needed, it is kit-side) |
| 10 | Aliasing bound uses `0x18F` spectral shape as a proxy for `gp-0x6b98` **[BELIEF]** | a cave rung reporting `\|gp-0x6b98\|` above a threshold at 100 Hz |

---

## 7. RETRACTIONS AND WITHDRAWALS THIS SESSION

1. **Orchestrator's own premise** — `H(s)` peaking at a ~8 Hz wheel-inertia mode with a 180° phase
   rotation. **Falsified.** The architecture argument built on it (§"no scalar decoupler can work")
   **weakens**: with no sharp in-band feature, a low-order or near-static decoupler may suffice at
   6–9 Hz. What survives untouched: the two-loop framing, the known-input observer requirement,
   sum-first-clamp-once, rate-matching, and the hand-impedance envelope (which rested on the
   independently-measured 6.3× `f'` compression).
2. **Orchestrator's "`T_bar/θ_w` is only valid above the assist crossover"** — **wrong.** It is Newton's
   law on the upper column; the assist acts on the lower side and enters only through `T_bar`, so the
   control law changes the *excitation*, not the *ratio*. Real limits: column Coulomb friction, and SNR
   where `|J s² + b s| → 0`. Measured validity band **5 to ~13 Hz**.
3. **Orchestrator's 300 ct/s slew ceiling** — wrong by **41×** (§4).
4. **`γ²(e4, torsion bar)` at 6–9 Hz** — retracted as reverse causality by its own author (§4).
5. **`_stock_r97_ringdown.json`** — unquotable (§3.1).
6. **`ζ 0.017–0.036 / Q 14–29`** — Q downgraded to an **upper bound** (§3.1).
7. **`rate_c` vs `rate_f` "agreement"** — vacuous; they are one channel (§3.2).
8. **`rec1`'s zero-lag kill** — withdrawn by its author; kills 1–3 stand (§4).
9. **`rec2`'s `plant_fit_final.py` `J_w`/`f_n`** — withdrawn by its author (R² 0.01–0.32, negative J²).
10. **`rec2`'s "~14 % ring-down power at A=1"** — corrected by its author to **0/7 at all 50 settings**.

---

## 8. Process notes

- **Every decision-bearing claim in this handoff was reproduced by the orchestrator**, not relayed:
  the `carcontroller.py` normalisation, the measured slew, `plant_phase_corner.py`, `plant_Jb_absolute.py`,
  `plant_falsifiers.py`, and the `tan(180−a)` arithmetic.
- **Running the control before the measurement is what produced this session's value.** Every one of the
  five defects surfaced that way. Two agents corrected themselves against their own interest, unprompted.
- **Pushing back on a subagent's conclusion improved it.** `rec2`'s first version leaned on STOCK's low CV
  without applying its own `coh ≥ 0.50` qualifier and had not run the decisive F1 cell. Challenged, it ran
  both — F2 resolved to one failing route, F1 turned out physically untestable — and it produced the
  single-bin form, a better argument than the one under challenge.
- **Roll-call discipline held:** both agents `TaskStop`ped and confirmed absent from `ListAgents` before
  close-out; both repos checked from disk (untracked additions only, zero tracked modifications).
