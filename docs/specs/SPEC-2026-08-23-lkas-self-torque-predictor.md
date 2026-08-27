# SPEC — LKAS SELF-TORQUE PREDICTOR (code cave)

**2026-08-23. SPECIFICATION ONLY — operator instruction: *"just put this code cave together as a spec
document, no need to create an actual firmware from it."* Nothing built, nothing flashed, no CAN sent.**

---

## 0. The idea, in the operator's words

> *"Let's create a code cave that tries to predict the resulting driver torque signal from LKAS only.
> Input = LKAS demand, some relevant state information like steering angle or steering angular velocity
> and acceleration, output = expected torque sensor signal."*

The problem it solves:

> *"Ideally LKAS torque command is directly output onto the steering column and the steering wheel simply
> follows. The torque sensor will naturally maybe oscillate or on sharp torque transient (LKAS-driven),
> it will inject an opposing signal due to steering wheel inertia. Ideally these torque signals are
> ignored unless the driver is commanding the wheel. The hard part is allowing the driver to command the
> wheel while being able to ignore the non-ideal signals from the torque sensor as a result of LKAS
> torque."*

And the constraint that kills the textbook approach:

> *"This paper relies on a well defined and measurable model of the vehicle's steering dynamics. We do
> not have access to such information."*

**The resolution: do not derive the model — LEARN it, offline, from the corpus we already have.**
Hands-off engaged frames are a labelled training set: with no hands on the wheel, the ENTIRE torque
sensor signal is self-induced. Fit there; the residual on hands-ON frames is the driver.

🛑 **This document reports a COMPLETED offline feasibility study (§2). It is not a proposal resting on an
analogy.** Every number below is held out on data the fit never saw.

---

## 1. Why filtering can never solve this, and prediction can

Driver torque and self-induced torque **overlap in frequency**. A driver correcting during a ratchet
episode produces in-band 6–9 Hz torque. Every notch / cancellation / damping argument this kit has run
has been a frequency-domain attempt at a problem that is not separable in frequency.

**The separation is model-based:** predict what our own actuation does to the bar, subtract it, and what
remains is the human — by construction, at every frequency. This is the disturbance-feedforward
structure of Bao et al. 2020 (`10.1177_0036850420950138`), whose steering plant is

```
Jeq*ddot(delta) + Beq*dot(delta) + tau_di + tau_f*sign(dot(delta)) = Ns*Nm*tau_m      (their eq. 10)
```

⚠ **That paper cannot be used directly: its `Jeq` lumps front wheel + motor + column + rack into ONE
RIGID inertia. There is no torsion bar, so the exact phenomenon this spec targets is the thing their
model deletes by assumption.** Their own conclusion flags it — *"not the change of system stiffness."*
Their HIL bottom loop also carries 0.3 s step-tracking delay = 2.4 periods at 8 Hz.
**Borrow the architecture, not the model.**

---

## 2. OFFLINE FEASIBILITY — COMPLETED, and it is the reason to build

Corpus: routes `9e` / `a4` / `a5` / `a6` = V103 / V104 / V105 / V106. Target `tq` (0x18F b0:2, torsion bar
counts). Candidate inputs at 100 Hz: `sc_tq` (LKAS demand), `ang`, `rate_f`, and `alpha = d(rate_f)/dt`.
Train on **alternate contiguous hands-off runs**, test on the others — no within-run leakage.
Gate: engaged, `cs_press == 0`, 5–60 km/h.

### 2.1 The 8 Hz line is NOT in the LKAS command — so a demand-driven predictor cannot work

Share of each signal's own 0.5–30 Hz power, hands-off engaged:

```
     band        tq (bar)    LKAS cmd      rate
   0.5-2.0 Hz      11.54%      72.42%     19.13%
   2.0-4.0          4.45%      11.22%      4.72%
   4.0-6.0          3.50%       3.23%      2.86%
   6.0-9.0         20.03%       2.56%      4.80%     <-- the bar PEAKS where the command has nothing
   9.0-13.0        20.07%       1.24%      7.81%
  13.0-18.0        14.08%       1.07%     15.57%
  18.0-30.0        16.89%       1.14%     38.53%
```

Confirms the standing record (`reference-accord-lkas-lane-is-a-lowpass`): the LKAS lane is a ~1–5 Hz
low-pass. **The line is the plant's RESPONSE, not the command.**

### 2.2 ABLATION — angular ACCELERATION carries it, exactly as the operator's model predicts

Held-out R² within 6–9 Hz, 25 taps per input group:

```
  LKAS command alone   +0.185
  angle alone          +0.517
  rate alone           +0.677
  ACCELERATION alone   +0.735    <-- J*alpha : the wheel-inertia reaction, MEASURED
  all four             +0.766
```

⭐ **Acceleration alone recovers +0.735 of the +0.766.** The other three inputs buy +0.031 between them.
**The predictor is an inertia model, and the operator identified the mechanism correctly.**

### 2.3 STRUCTURE — Honda's existing path CANNOT do it; a 2-pole IIR can

```
A  Honda's EXISTING structure (FUN_0003b8f6): gain x EMA2(alpha), cals 0xC646E / 0xC50D6
     even with BOTH refitted optimally      R2 6-9 Hz  +0.243     <-- CANNOT REACH IT
B  FIR( 4) on alpha                                    +0.525
   FIR( 8)                                             +0.677
   FIR(16)                                             +0.728
   FIR(25)                                             +0.735
C  2-POLE IIR on alpha  (3 coefficients, 2 states)     +0.704     <-- CHOSEN
```

🛑 **This is the finding that justifies a cave and forecloses a cheaper cal edit.** The required response
is RESONANT; Honda's term is a cascade of two low-passes. Retuning `0xC646E` and `0xC50D6` tops out at
`R² = +0.243`. **Do not spend a build on that cal pair for this purpose.**

### 2.4 THE FITTED PREDICTOR

```
T_hat[n] = b0*alpha[n] - a1*T_hat[n-1] - a2*T_hat[n-2]

    b0 = -0.229242      a1 = -1.504108      a2 = +0.808414
    pole f0 = 9.232 Hz      |r| = 0.89912      Q = 4.96
```

### 2.5 CONTROLS — all four pass

Transfer across builds, from ONE coefficient set fitted on `a6` only:

```
              hands-OFF                        hands-ON
  V106   n= 7908  R2 6-9 Hz +0.7040     n=2266  R2 6-9 Hz -2.2718
  V105   n=17490            +0.6608     n=1419            -1.5046
  V104   n=23929            +0.6919     n=1570            -1.1389
  V103   n= 8288            +0.6544     n= 763            -0.1719
```

- ✅ **TRANSFER:** +0.65 to +0.70 on all four builds from one coefficient set. Fixed cave coefficients are
  viable; this is not a per-build fit.
- ✅ **SEPARATION:** hands-ON R² collapses to strongly negative on every build. The predictor models the
  self-induced case and FAILS when the driver is present — which IS the separation working.
  🛑 **AND IT IS ALSO A HAZARD — see §5, GATE 4.** A negative R² means subtracting the prediction ADDS
  6–9 Hz energy hands-on. The gate is mandatory, not advisory.
- ✅ **SHUFFLE NULL:** inputs offset by 5,000 samples give `R² = −8.23`. Clean.
- ✅ **BAND-SPECIFIC:** hands-off TOTAL R² is only −0.05…+0.33 across builds while the 6–9 Hz R² holds at
  +0.65…+0.70. The predictor is targeted, not a broadband curve-fit.

---

## 3. 🛑 THE COEFFICIENTS IN §2.4 ARE NOT THE COEFFICIENTS TO CUT

The offline fit used **`alpha = d(rate_f)/dt`** — the derivative of the BUS steering-rate channel
(0x18F b2:4, 0.1 deg/s LSB, 100 Hz). The cave would use **`gp-0x6c2c`**, which is:

- **motor-side**, sourced from `gp-0x4f50` via `FUN_00041464` (sole writer, 4 stores at `0x416FC`,
  `0x4170C`, `0x41968`, `0x4197C`);
- already **twice-EMA'd inside that function** (cals `0xC50DC`, `0xC50DA`) and `>> 9`;
- sampled at the **1 kHz** control rate, not 100 Hz.

**Different signal, different scale, different phase, different sample rate. The numbers do not
transfer.** Structure transfers; coefficients must be re-fitted.

⭐ **V107 ALREADY CARRIES THE INSTRUMENT.** Its E2 edit points the 427 tap at `gp-0x6c2c`
(`0x55DF2` = `d4 93`, `0x55E10` = `a3`, LSB 8, full scale 8184). **One V107 drive puts the cave's actual
input on the wire at 100 Hz alongside `tq`, and the fit in §2 re-runs unchanged against it.**

🛑 **AND A PREREQUISITE THAT GATES THE WHOLE SPEC:** `gp-0x4f50` has NOT been confirmed as the motor
resolver rather than another tap off the column sensor. The bus already burned us here — `ang` and
`wang` are byte-identical (corr 1.000000, difference exactly 0), and `rate_f` / `rate_c` are ONE signal
one CAN frame apart (coherence² 0.997–1.000, phase exactly −3.5 deg/Hz = 9.7 ms on all four routes).
**If `gp-0x4f50` is column-derived, this cave is predicting the wrong side of the bar.** Trace it first.

---

## 4. THE CAVE

### 4.1 Tap

**`gp-0x6c2c`** — the acceleration, read in the same tick. Sole writer `FUN_00041464`; ordering vs the
injection site must be confirmed from `FUN_0002214a`'s dispatch order (OPEN, §7.2).
Optional second input `gp-0x6b4c` (LKAS lane sum) — **not recommended for v1**: §2.2 prices it at +0.185
alone and it adds a second scale to calibrate.

### 4.2 Inject

**`FUN_000352b4`, between `0x354D2` and `0x354D6`.** `[EVIDENCE — get_assembly_context]`

```
000354ce   ld.h  0x7200[tp],r14      ; r14 = cal(0xC6200) = 8192, LIVE, must be preserved
000354d2   ld.h  -0x4f60[gp],r16     ; r16 = raw torque      <-- CAVE CALL HERE
000354d6   cmp   r14,r16             ; downstream clamp / breakpoint search begins
```

`r16 = r16 - round(T_hat_scaled)`. **Corrects the LOCAL COPY only — `gp-0x4f60` is never written**, so
every fault monitor and every other reader still sees the true sensor. The second `gp-0x4f60` read at
`0x35AA4` (the extreme-value force-zero) is untouched and keeps checking the real sensor.

⚠ **Consequence, stated plainly:** this cancels self-interference in the friction / base-assist lane only.
Boost (`FUN_00034a72`), damping (`FUN_00034350`) and the residual/D-term lane (`FUN_0003a382`) each read
raw `gp-0x4f60` independently and forward their own uncancelled contribution to the same aggregator.
**Nobody has censused what fraction of the total this lane is.** OPEN (§7.3).

### 4.3 Arithmetic

```
    T_hat[n] = b0*alpha[n] - a1*T_hat[n-1] - a2*T_hat[n-2]
    r16     -= (T_hat[n] * g) >> S            with g = 0 on the first flight
```

**Q-format: IEEE754 single**, matching the adjacent idiom (`FUN_0003b8f6` already uses `mulf.s` /
`addf.s` / `maddf.s` throughout). Two float states, three float cals.

🛑 **SPECIFY EVERY COEFFICIENT BY ITS FORMULA, NEVER BY A ROUNDED DECIMAL.**
`feedback-float-spec-must-be-the-formula`: three agents once produced three byte strings for one
coefficient, none mis-encoded — they encoded three DIFFERENT NUMBERS. **Ship an assertion against the
lossy encoding, so the rule cannot be forgotten.**

```python
R_POLE, F_POLE, FS = <fitted>, <fitted>, 1000.0     # THE FORMULA IS THE SPECIFICATION
a1 = -2*R_POLE*cos(2*pi*F_POLE/FS)
a2 =  R_POLE*R_POLE
b0 = <fitted from the V107 gp-0x6c2c drive>
```

### 4.4 Registers

`r14` holds `cal(0xC6200)` and is used at `0x354D6` — **must be preserved.** The preceding
`do{...}while(bVar12<10)` loop's registers (`r20`–`r27`, `ep`) have exited in program order but **no
formal liveness pass has been run.** **Save/restore any scratch via stack push/pop** — a few bytes
against an unverified liveness claim is the correct trade, and is the discipline the flown V96 cave used.

---

## 5. GATES

### GATE 1 — RAM ownership
Two float states needed. **Do NOT reuse Honda's biquad states `gp-0x3814` / `gp-0x3818`** unless
`cal(0xC649B)` is held at 0 — and V103+ ARM that biquad, so on the current lineage those cells are LIVE.
This design needs its **own** 8 bytes, with a full five-method sweep: operand-pattern scan, fresh
decompile, register-indirect access, the 6-byte disp23 form, and an LE32-literal-table scan.
🛑 **`gp-0x1500` passed BOTH static methods and still failed on-car; `gp-0x14FA` bricked V48B.**
**A dedicated on-car probe reading the chosen cells is mandatory before any cave writes to them.**

### GATE 2 — closed-loop stability
- **First flight `g = 0`:** the filter computes and telemeters, the subtraction is multiplied by zero.
  **Provably unchanged closed loop. This is the only configuration with zero GATE-2 exposure.**
- **`|r| = 0.89912`** — compare the 2026-08-20 design's proposed `|r| = 0.998704`. ⭐ **The fitted pole is
  MORE damped than V48B's `r = 0.979`, the resonator that bricked the ECU.** A large, unplanned safety
  improvement that came from the data, not from a safety argument.
- **Mistuning:** a frequency error is the dangerous direction, but a 2-pole section at Q ≈ 5 has a broad
  response, so drift degrades toward ineffective rather than toward reinforcing.
- **New-resonance risk:** this is still a new recursive structure with a new summing junction. At Q ≈ 5 it
  is far from V48B's class, but it is not zero. **This is why `g = 0` flies first.**

### GATE 3 — dropouts
The extreme-torque force-zero at `0x35AA4` re-reads RAW `gp-0x4f60`, so the correction cannot trigger or
avoid it — correct by design. The aggregator's ±12288 zero-reject is structurally unreachable for this
lane. Injection sits UPSTREAM of both shadow pairs (`gp-0x6b7a`/`gp-0x4cdc`, `gp-0x6b86`/`gp-0x4cde`), so
it changes what they mirror, never whether they stay mirrored.

### 🛑 GATE 4 — HANDS-ON, AND IT IS NEW
§2.5 measured hands-ON R² at 6–9 Hz of **−2.27 / −1.50 / −1.14 / −0.17** across four builds.
**Negative R² means subtracting the prediction ADDS energy in the band.** Physically: hands-on kills the
ratchet (the kit measured 16.12× [5.29, 41.29] hands-off vs hands-on), so a predictor trained on the
large hands-off case over-predicts when a hand is on the wheel.

⇒ **The correction MUST be gated or blended on hands-on state.** Candidate gate `gp-0x6806`
(== `latActive` on 150,302/150,327 = 99.983 %) is the wrong quantity — it is engagement, not hands-on.
**The hands-on signal available in firmware has not been identified. This is a BLOCKING open item.**
An ungated build would make the symptom worse in exactly the condition the operator most often drives in.

---

## 6. TELEMETRY — the first flight is an instrument, not an actuator

`g = 0`. The 427 channel carries **`T_hat`** (10 bits, `clamp(|T_hat| >> S, 0, 1023)`); pick `S` against
the measured `T_hat` distribution from the V107 re-fit, not a guess.
Cave rungs, following the design law (*a sign bit paired with a magnitude channel, or a deliberate
control* — never a bare threshold on an unmeasured distribution):

```
  b7   sign(T_hat)                      pairs with the 427 magnitude
  b6   |T_hat| >= |gp-0x4f60|           COMPARATOR -- immune to under/over-range by construction
  b5   hands-on gate state              THE GATE-4 DECISION, read out directly
  b4   sign(gp-0x6c2c)                  the input's own sign
```

**The sentence a null will license, written before the cut:** *"`T_hat` tracked the bar torque at 6–9 Hz
with duty X on rung b6, and the hands-on gate fired with duty Y — so the correction would have been in
force for Z % of engaged frames."* If a drive cannot produce that sentence, the instrument is wrong.

---

## 7. OPEN ITEMS — with what closes each

1. **`gp-0x4f50` provenance: motor resolver or column sensor?** Ghidra trace of its writer.
   🛑 **BLOCKING — if column-derived, this cave predicts the wrong side of the bar.**
2. **`FUN_0002214a` dispatch order** — is `gp-0x6c2c` fresh or one tick stale at the injection point?
   Decompile `FUN_0002214a` directly; §4.1 currently infers it from data-flow necessity.
3. **Per-lane contribution census** — what fraction of total self-interference does the `gp-0x6b86` lane
   carry, vs boost / damping / residual? Needs engaged telemetry, not statics.
4. **The hands-on signal in firmware.** BLOCKING for GATE 4.
5. **Coefficients against `gp-0x6c2c`.** Closes with one V107 drive — the tap is already cut.
6. **8 bytes of verified-free RAM + 12 bytes of free flash cal space.** Standard surveys.

---

## 8. HOW THIS DIFFERS FROM `specs/design/DESIGN-2026-08-20-self-interference-cancellation.md`

| | 2026-08-20 design | this spec |
|---|---|---|
| input | `gp-0x6b98`, motor command, 1 tick old | **`gp-0x6c2c`, acceleration** — measured at +0.735 vs the command's +0.185 |
| filter | matched resonator **f0 7.79 Hz, Q 18.9, \|r\| 0.998704** | **fitted f0 9.23 Hz, Q 4.96, \|r\| 0.899** |
| safety | *"~17× more lightly damped than V48B's r = 0.979, the resonator that bricked the ECU"* | **MORE damped than V48B** |
| `b0` | *"I cannot responsibly hand you a number"* — needs unmeasured `k/J_c` | **fitted from data**; re-fit against `gp-0x6c2c` from one V107 drive |
| evidence | reasoned from the operator's 2-pole model | **held-out fit, 4 builds, 4 controls** |
| ranking | *"not the recommended next cut"* — notch first | **the notch route is closed**: the 6–9 Hz notch was refused on `Re(u/T)` phase; V105's 25.5 Hz notch is −0.149 dB at 7.79 Hz |
| hands-on | not considered | **GATE 4, blocking** |
| RAM | reuse `gp-0x3814` / `gp-0x3818` | **cannot** — V103+ arm Honda's biquad, those cells are live |

**Its §8 argued cancellation was worse because *"it addresses only the LKAS-attributable component."*
That argument is dead:** the line has EXACTLY ZERO power on stock in 3 of 4 highway cells, 0 of 97
fully-manual windows carry it, and engaged/manual is 24.29× [10.77, 48.37] matched on speed and rate.
**There is only one excitation source, so "only the LKAS-attributable component" means all of it.**

---

## 9. STATUS

**SPEC ONLY. Nothing built. Nothing flashed. No CAN sent.**
Blocking before any cut: open items 1 and 4.
Cheapest next step that advances it: **fly V107 and re-fit §2 against `gp-0x6c2c`** — the tap is already
in the built image, so this costs a drive and no new build.
