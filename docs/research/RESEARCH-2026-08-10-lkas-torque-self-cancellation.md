# External literature review — LKAS torque overlay self-interference in a column EPS

**Date:** 2026-08-10 · **Scope:** external literature and OEM engineering practice only. No firmware was read or
modified for this document. Every claim is marked **EVIDENCE** (with citation) or **BELIEF** (my inference).

---

## 0. HEADLINE — read this before anything else

### 0.1 🛑 The operator's *mechanism* is REFUTED by its own evidence. The operator's *symptom chain* survives.

The hypothesis as briefed has two separable parts:

| Part | Claim | Verdict |
|---|---|---|
| **A** | The LKAS motor torque contaminates the torque-sensor reading with an apparent driver torque of **opposite sign**, and the base assist law reacts to it. | **SUPPORTED — and confirmed by Honda's own patent.** |
| **B** | The contamination arises because the motor **accelerates the steering-wheel inertia** (`J·α`). | **REFUTED by the operator's own measurement.** |

Part B cannot be the dominant path, and the operator already has the data that kills it. An inertial
reaction is `T ≈ J_h · θ̈`. In the frequency domain that is `J_h s²` — it **must** scale with command
*acceleration*, i.e. it rises at **+40 dB/decade** and is strongly rate-dependent. The corpus result
(`accord-engagement-amplifies-6-9hz`) is that the 6–9 Hz amplification is **command-magnitude
proportional and does NOT grow with wheel rate** (+0.022 [−0.070, +0.116]). A `J·α` coupling with a
flat-in-rate signature is a contradiction in terms.

**The brief already identified this tension and asked me to take it seriously. I am: the tension resolves
against inertia.**

### 0.2 What the magnitude-proportional signature actually points to

Two mechanisms in the literature produce a **magnitude-proportional** (not rate-proportional) apparent
driver torque. Both survive; I rank the second higher.

1. **Quasi-static reaction through driver grip and road compliance** — a *static* (DC) gain from motor
   torque to torque sensor, nonzero only when the wheel is restrained. Derived in §3.2. This is
   magnitude-proportional by construction, and it is exactly the form Honda uses (§1.1).
2. ★ **Load-dependent Coulomb friction in the worm mesh** — the normal force on the worm/wheel contact is
   **proportional to the transmitted torque**, so the Coulomb friction it generates is
   **proportional to command magnitude**. Combined with a velocity-weakening (Stribeck) friction law this
   is a classic **stick–slip self-excitation** whose *strength* scales with command magnitude and whose
   *frequency* is set by a structural mode, not by the command. §6.

**Mechanism 2 explains every measurement in the kit's record simultaneously** (BELIEF, but a tight fit):

| Kit observation | Explained by load-dependent stick–slip? |
|---|---|
| Amplification is **magnitude**-proportional, not rate-proportional | ✅ `F_n ∝ T_transmitted` ⇒ friction ∝ command magnitude |
| Engagement multiplies the 6–9 Hz band **2.8×** | ✅ engagement raises mean transmitted torque ⇒ raises `F_n` |
| The ratchet is a **lightly damped resonance, Q 14–29**, at a fixed frequency | ✅ stick–slip excites a structural mode; it does not set the frequency |
| **Driver grip damps it** (−0.655 vs control −0.266) | ✅ the hand adds damping to a Q≈20 mode; a few % of critical is enough |
| Frequency is **speed-invariant** | ✅ a structural mode, not a wheel/tyre order |
| The LKAS command itself has little 6–9 Hz content (~1–5 Hz low-pass) | ✅ this is **load-modulated excitation**, not direct injection — the DC command sets the friction load, the structure rings |

The kit's own memory title — *"a COMMAND-PROPORTIONAL COULOMB RELAY"* — is, as far as the tribology
literature is concerned, the correct name for this. **The firmware finding and the mechanical literature
have independently converged.**

### 0.3 What this means for V89 — the current build is aimed at the right physics

`0xC40D2` is described in the kit record as **K1, the `|model|`-proportional modelled Coulomb friction**.
A friction term proportional to the *magnitude* of the modelled torque is precisely the functional form
the worm-gear literature says real EPS friction takes (`F_n,T = T_wh·√(1+tan²γ+tan²α)/R_p`, §6.2). Honda
did not choose that form by accident.

**BELIEF:** V89 is the first build in the arc aimed at the mechanism the external evidence supports.
That is a point in its favour, and it is independent of the kit's internal reasoning.

**Caveat, stated plainly:** the literature supports the *form* of the term. It does not tell you the
*sign* of the on-car effect, and it does not tell you whether raising modelled friction reduces the
observer's chasing (good) or increases delivered friction (bad). §7.3.

### 0.4 One remedy the kit may have discarded too early

The corpus refuted **rate-limiting** the LKAS command. **A rate limit and an in-band low-pass are not the
same lever**, and the refutation of the first does not touch the second. §8. Denso's production answer to
"lane-keep causes steering vibration" is explicitly to **low-pass the tracking command and lower its
response gain** — not to slew-limit it (**EVIDENCE**, US10035538B2).

---

## 1. Self-interference and assist-cancellation architectures

### 1.1 ★★★ The smoking gun: Honda US11685438B2 — same OEM, priority 2020-03-13

**EVIDENCE.** *Vehicle control apparatus and vehicle*, **Honda Motor Co Ltd**, inventors Atsuhiro Eguchi,
Shuichi Kosaka, Ryo Kawaguchi, priority **13 March 2020**.
<https://patents.google.com/patent/US11685438B2/en>

This patent exists because **the problem the operator describes is real and Honda knows about it**. It
states that the detected steering torque must be corrected by *removing the torque due to intervention of
the lane keeping assistance system* in order to recover the true driver torque.

The architecture:

```
        detected steering torque To
                  │
        ┌─────────┴─────────┐
        │                   │
   LPF X (fc ≈ 5 Hz)   LPF S (fc ≈ 1 Hz)
        │  Tx               │  Ts   (slow offset)
        │                   │
LKAS instruction Li         │
        │                   │
  conversion unit U         │
        │  Lu               │
        ▼                   │
      ADDER 204 ──► Tu ──► SUBTRACT ──► Tsu  (corrected driver torque)
                                        │
                                        ▼
                              hands-off determination
```

**The formula, verbatim in structure:**

```
Tsu = (Tx + Lu) − Ts
```

- `Tx` = torque sensor, low-passed at **≈5 Hz**
- `Lu` = **the LKAS instruction signal converted to an estimated torque** by "conversion unit U"
- `Ts` = slow offset, low-passed at **≈1 Hz**

**Sign convention — quoted verbatim, and this is the single most load-bearing sentence in this document:**

> *"The reason why addition is performed for removal is that, if the torque applied by the rack 14 and the
> torque applied by the steering wheel 15 are torques in the same direction, the values of these torques
> have opposite signs."*

**⇒ Honda states, in its own words, that the LKAS-induced component appears in the torque sensor with the
OPPOSITE SIGN to the commanded torque.** That is Part A of the operator's hypothesis, confirmed by the
manufacturer of this exact ECU family. Removal is performed by **addition**.

**Two things this patent does NOT say, and they matter:**

1. 🛑 **The correction is used for hands-off determination, not for the base assist law.** There is nothing
   in this patent that says Honda subtracts the overlay reaction from the signal entering the boost curve.
   The operator's Part A is confirmed as a *phenomenon*; it is **not** confirmed that the shipped assist
   law is blind to it, nor that it is not. **BELIEF:** the fact that Honda built a dedicated corrector for
   the hands-off path is weak evidence that the assist path does *not* get the same treatment — otherwise a
   corrected signal would already have been available to reuse.
2. ★ **`Lu` is produced by a static "conversion unit", not by a double differentiator.** If the coupling
   were inertial (`J s²`), `Lu` would have to be a second derivative of the command. It is not — it is a
   **static conversion followed by a 5 Hz low-pass**. **This is independent OEM evidence that the dominant
   contamination in the sub-5 Hz band is a quasi-static, magnitude-proportional gain, not an inertial
   term.** It corroborates §0.1 from a completely different direction.

### 1.2 Model-based residual: GM's dynamic steering model (CN101746412B)

**EVIDENCE.** *Detection of driver intervention during a torque overlay operation in an EPS system*,
**GM Global Technology Operations**, priority 17 Dec 2008.
<https://patents.google.com/patent/CN101746412B/en>

Rather than subtract a gain, GM runs a forward model of the steering plant driven by the torque overlay
command, and treats the **mismatch** as driver intervention:

```
J_s·θ̈_s + B_s·θ̇_s + K_s·θ_s ≈ K·T_Cmd

θ_s(s)/T_Cmd(s) = (K/J_s)/(s² + (B_s/J_s)s + K_s/J_s) = K_ss·ω_n²/(s² + 2ζω_n s + ω_n²)
```

Detection is on **ΔG**, the gradient difference between the modelled angle `θ_CALC` and measured `θ_S`;
exceeding a tolerance flags intervention and the overlay is overridden.

**Relevance to this kit:** this is the *same architectural idea* as the residual observer the kit has
already traced (`residual = MODEL − ACTUAL`), but with the **overlay command as a known model input**.
That is exactly the distinction §5 turns on.

### 1.3 Frequency-domain separation instead of subtraction (EP2604487B1)

**EVIDENCE.** *Hands on steering wheel detect in lane centering operation*, **Steering Solutions IP Holding
Corp**, priority 15 Dec 2011. <https://patents.google.com/patent/EP2604487B1>

A third production approach: **do not subtract anything**. Exploit the fact that hands-on and hands-off
produce different *vibrational signatures*. A notch removes the **"normal column mode", stated as
8 Hz–15 Hz**; an envelope detector and thresholds (≈0.7 / 1.0 / 1.5 Nm) then classify the residual.

★ **This is an independent OEM statement that a column-type steering system's first structural mode sits
at 8–15 Hz**, and that its amplitude changes with hand contact. Both facts corroborate the kit's 6–9 Hz
band and its measured grip-damping result. See §6.1.

### 1.4 Overlay scaling and arbitration (the "manage it, don't cancel it" school)

**EVIDENCE.** Several OEMs never cancel the reaction; they scale or arbitrate the overlay instead:

- *Method and system for adaptation of a steering wheel torque overlay of a lane keeping aid system*,
  US8849516 — scales the overlay by a factor that is **a function of driver-applied steering wheel torque**.
  <https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8849516>
- *Intelligent scaling of torque overlay intervention for semi-autonomous road vehicle steering systems*,
  EP3018040A1. <https://patents.google.com/patent/EP3018040A1/tr>
- *Steer torque manager for an advanced driver assistance system of a road vehicle*, US10625773B2 — an
  explicit arbitration layer between ADAS torque requests and the base assist.
  <https://patents.google.com/patent/US10625773B2/en>

**BELIEF:** this school is not applicable to this kit — every one of these levers lives in the *ADAS*
controller, which is openpilot here, and the standing instruction is no openpilot-side modifications.

---

## 2. Inertia compensation — what it is, and why it is the WRONG band for this symptom

### 2.1 The canonical EPS compensation stack

**EVIDENCE.** US11208142 (steering feel control apparatus, MDPS) enumerates the production stack:
> *"a hysteresis compensation component for imitating a hysteresis characteristic due to mechanical
> friction; a damping compensation component for viscously preventing or reducing a micro-vibration
> generated in the steering wheel; and an inertia compensation component for preventing or reducing a
> catching feeling at the start of operation and an overshoot at the end of operation."*
<https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11208142>

Note the assignment of duties: **micro-vibration is the DAMPING term's job**, not the inertia term's.
"Catching feeling" is the inertia term's job. The operator's symptom vocabulary — grinding, vibrating,
micro-ratcheting — maps onto **damping**, and onto **hysteresis/friction**, in the OEM taxonomy.

### 2.2 Formulation, signs, and bandwidth (US9415798B2)

**EVIDENCE.** *Inertia compensation to remove or reduce effects of torque compensation in EPS*,
**Steering Solutions IP Holding Corp**, priority 26 Feb 2014.
<https://patents.google.com/patent/US9415798B2/en>

From **motor velocity**:

```
IC = J_mot · s · [ (s + a·2π) / (s + b·2π)² ] · (b²·2π / a)
```

From **motor acceleration** (no leading `s`):

```
IC = J_mot · [ (s + a·2π) / (s + b·2π)² ] · (b²·2π / a)
```

Worked design example, verbatim:

```
G_v = s(s + 35·2π) / (s + 200·2π)²
```

— a zero at **35 Hz** giving phase lead from ~10 Hz, two poles at **200 Hz** for noise rejection. The
acceleration-based form requires a measurement bandwidth of **≥250 Hz** (45° phase-lag criterion).

**Sign:** the inertia compensating torque is **added** at the summing junction with the base torque
command (`Σ` block 206, positive input). Signals: **motor velocity** or **motor angular acceleration**.

**Purpose, and the reason this is the wrong lever here:** the patent's stated problem is that motor inertia
**shifts the phase crossover frequency by ~40 Hz**, and the compensator exists so that low-frequency notch
filters can be *removed* to protect steering feel. It is a **stability lever at tens of Hz**, deliberately
designed to be inert at low frequency.

🛑 **EVIDENCE + BELIEF:** inertia compensation is formulated to act from ~10 Hz upward with its design zero
at 35 Hz. It is **not** a 6–9 Hz lever. Applying it to the operator's primary band would require detuning
it far below its intended range, where it is functionally indistinguishable from raising damping — and
raising damping is far simpler (§7.1).

### 2.3 Does routing the LKAS command through the inertia path cancel the apparent driver torque?

**Answer: NO — and I want to be blunt about this because the brief asks directly.**

**BELIEF, with a supporting EVIDENCE anchor.** Inertia compensation is driven by **measured motor
velocity/acceleration**, i.e. by what the column *actually did*. It therefore compensates the inertial
reaction of **any** torque source — driver, road, or LKAS — automatically and without knowing which. Feeding
the LKAS *command* through it in addition would **double-count** the inertial term.

The supporting evidence is §1.1: Honda's own overlay corrector uses a **static conversion plus a 5 Hz
low-pass**, not a `J s²` path. If the inertia path were the cancellation mechanism, Honda would have built
it that way and did not.

**Where the LKAS command genuinely does belong as a feed-forward is the *observer's plant model* (§5), not
the inertia compensator.**

### 2.4 Other inertia-compensation sources (for completeness)

- **EVIDENCE.** *Compensation for motor inertia in electric power assisted steering systems*, **TRW
  LucasVarity Electric Steering**, US6597136 / EP1211158A2.
  <https://patents.google.com/patent/EP1211158A2/en>
- **EVIDENCE.** *Inertia Compensation Based on Torque Signal in an EPS System* — derives motor angular
  acceleration **from the torque signal** rather than by differentiating the angle, because
  *"the angular acceleration signal cannot be derived from direct differentiation of angle signal because
  of the amplified noise."* <https://link.springer.com/chapter/10.1007/978-3-642-33829-8_71>
- **EVIDENCE.** *Inertia compensation with frequency dependent damping*, **Steering Solutions**, priority
  9 Sep 2011, US20130066520A1 — a single second-order filter (coefficients a₀..b₂) that **transitions from
  inertia compensation into frequency-dependent damping "between about 10 Hz to about 20 Hz."**
  <https://patents.google.com/patent/US20130066520A1/en>

★ **That last one is directly relevant.** It is OEM confirmation that **10–20 Hz is where you stop doing
inertia compensation and start doing damping** — which straddles the operator's second band (18–28 Hz) and
sits above the first (6–9 Hz). Both of the operator's bands are, by this OEM's own crossover choice, in
**damping territory**.

---

## 3. Feed-forward cancellation of the overlay in the torque-sensor path

### 3.1 Is there a standard technique of the form `T_driver_est = T_sensor + K·T_lkas`?

**YES — EVIDENCE, §1.1.** Honda US11685438B2 implements exactly

```
T_driver_est = LPF_5Hz(T_sensor) + U(LKAS_command) − LPF_1Hz(·)
```

with `U(·)` a static command→torque conversion, and **addition** (not subtraction) performing the removal
because of the opposite sign convention. The brief's guessed form `T_sensor + K·T_lkas` is **correct in
sign and correct in structure**, and it is first-order low-passed, not second-order.

Related but distinct: **US11180186B2**, *Disturbance feedforward compensation for position control in
steering systems*, **Steering Solutions**, priority 5 Apr 2018.
<https://patents.google.com/patent/US11180186B2/en>

```
T̂_d = D_t·T_a + D_ω·ω_m           (disturbance estimated from motor torque command and motor velocity)
T_b  = T_base + K_d·T̂_d           (adjusted command)
```
> *"The transfer functions Hd and Gd are zero at steady state … irrespective of the parameter estimates.
> Hence, steady state disturbance rejection is always achieved."*

This is the same *shape* — estimate a contaminating torque from the **commanded** torque and a measured
velocity, then feed it forward with a scalar gain `K_d`.

### 3.2 What is `K` physically? — derivation

**BELIEF (my derivation), structurally standard and consistent with the cited models.** Three-mass
column-EPS model, all quantities referred to the column:

| Symbol | Meaning |
|---|---|
| `θ_h`, `J_h` | steering wheel + upper column angle and inertia |
| `k_tb`, `c_tb` | torsion bar stiffness / damping — **the torque sensor** |
| `θ_c`, `J_c` | lower column + worm wheel; `J_c = J_col + N²·J_motor`, `N` = worm ratio (~16–20) |
| `T_m` | **motor torque referred to the column** = `N · τ_motor` (this is where LKAS lands) |
| `k_r`, `c_r` | compliance from the lower column to ground via I-shaft, pinion, rack, tie rods, tyre |
| `Z_d(s) = c_d s + k_d` | **driver impedance at the rim** (grip) |

Equations of motion:

```
J_h θ̈_h  =  −Z_d(s)θ_h  −  K(s)(θ_h − θ_c)                     … upper mass
J_c θ̈_c  =  T_m  +  K(s)(θ_h − θ_c)  −  (k_r + c_r s)θ_c  −  T_fric·sgn(θ̇_c)
where     K(s) = k_tb + c_tb·s
Torque sensor reads:   T_s = K(s)·(θ_h − θ_c)
```

Let `Z_u(s) = J_h s² + c_d s + k_d`. Eliminating `θ_h`:

```
θ_h = K(s)·θ_c / (Z_u(s) + K(s))

T_s = K(s)(θ_h − θ_c) =  − K(s)·Z_u(s) / (Z_u(s) + K(s))  ·  θ_c
```

and at DC (`s → 0`), with `θ_c = T_m/(k_r + k_eq)`:

```
              k_tb · k_d
  k_eq  =  ───────────────                (grip and torsion bar in SERIES)
             k_tb + k_d

              T_s            k_eq
  G_0  ≡  ─────────  =  − ───────────      ◄── THE STATIC COUPLING GAIN
              T_m          k_r + k_eq
```

**Read four things off this:**

1. **`G_0` is NEGATIVE.** The torque sensor reads *opposite* in sign to the commanded motor torque — exactly
   Honda's quoted sign statement (§1.1). ✅
2. **`G_0` is a pure static gain — magnitude-proportional, with no `s` in it.** This is a
   **magnitude-proportional coupling mechanism that has nothing to do with inertia.** It is the analytic
   form of the operator's measurement.
3. **Hands-off (`k_d = 0`) ⇒ `k_eq = 0` ⇒ `G_0 = 0`.** With a free wheel there is **no static coupling at
   all**; the only path left is the inertial/dynamic one. **⇒ Testable prediction:** the magnitude-
   proportional amplification should be *grip-dependent*, and should collapse toward a rate-dependent
   signature genuinely hands-off.
4. **`K` in the brief's formula is `−1/G_0`-ish, i.e. `K = k_eq/(k_r + k_eq)`** — a dimensionless
   **impedance-divider ratio between the restrained upper path and the road path**. It is *not*
   `J_wheel/(J_wheel + J_motor)`, as the brief conjectured. The inertia split governs the **high-frequency
   asymptote**; the **stiffness/impedance split governs the DC gain**, and the DC gain is what the
   operator's magnitude-proportional measurement is seeing.

🛑 **This corrects a specific premise in the brief.** `K` is an impedance ratio set by driver grip and road
compliance, so it is **operating-point dependent** — it changes with grip, speed, and tyre load. Honda's
`U(·)` conversion unit is presumably calibrated/scheduled for this reason. **A single fixed `K` cannot be
right at all operating points.**

### 3.3 Filter order and bandwidth used in production

**EVIDENCE.** Honda uses **first-order, ≈5 Hz** on the sensor path and **≈1 Hz** for the slow offset
(§1.1). Not second-order, not wide-band.

**BELIEF:** a 5 Hz corner is *below* the operator's 6–9 Hz band. If this kit ever implements a
feed-forward canceller, copying Honda's 5 Hz corner would leave the primary symptom band **outside** the
correction. Honda's corner is chosen for a hands-off decision (a slow, DC-ish judgement), not for
suppressing a 6–9 Hz ring.

---

## 4. Interaction with the base assist loop — is it a fight, or a de-amplification?

**BELIEF (analysis), grounded on an EVIDENCE anchor about phase margin.**

With base assist `T_assist = A·T_s` (boost gain `A`, same sign as sensed driver torque), and the static
coupling `T_s = G_0·T_m` with `G_0 < 0`:

```
T_assist = A·G_0·T_m          with A·G_0 < 0     ⇒  assist OPPOSES the overlay
```

Closing that loop around the overlay gives an effective overlay authority of

```
T_eff  =  T_m / (1 + A·|G_0|)
```

**At DC this is a DE-AMPLIFICATION, and it is stable.** The base assist quietly *eats* part of the LKAS
authority. It is not, at DC, a fight or a limit cycle — it is a tax.

**The instability is not at DC. It is at the phase crossover.** `T_s/T_m` is not a constant — it is
`−K(s)Z_u(s)/(Z_u(s)+K(s))` divided through by the lower-path impedance, and it has a **resonant peak and
180° of phase rotation at the wheel-on-torsion-bar mode**. Where that rotation makes `A·G_0(jω)` turn
*positive*, the same loop that de-amplifies at DC **peaks**.

**EVIDENCE that the margin is genuinely thin in production EPS:**
> *"Electric power steering (EPS) systems are prone to oscillations because of a very small phase angle
> margin, so a stable controller is required to increase the stability margin. In addition, the EPS system
> has parameter disturbances in the gain of the torque map under different conditions…"*
> — *Structured Control of an Electric Power Steering System*, Complexity (2020).
> <https://www.hindawi.com/journals/complexity/2020/9371327/>

**EVIDENCE.** Marginal stability and disturbance amplification are a named, recognised EPS failure mode:
US9731757 (*Closed loop EPAS systems*) describes prior EPS as *"only marginally stable … with resultant
amplification of external disturbances"* and notes the difficulty of applying servo techniques *"without
knowledge of where undesired resonances arise."*
<https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9731757>

**⇒ Synthesis (BELIEF):** the operator's "self-interference" intuition is **directionally right as a loop
concern** even though its stated mechanism (inertia) is wrong and its stated effect at DC (a fight) is
actually a de-amplification. The correct statement is:

> *The LKAS overlay injects a magnitude-proportional disturbance into an assist loop that has very little
> phase margin near the column mode, and the loop acts as a resonant amplifier there.*

That framing is consistent with **every** measured number in the kit, and it makes the primary lever
**damping / phase margin**, not cancellation.

---

## 5. Disturbance observers in EPS — is the LKA overlay a known input or an unknown disturbance?

This is the brief's sharpest question and the literature gives a clean answer.

### 5.1 Published EPS observers overwhelmingly treat the *driver* as the unknown and the *command* as known

**EVIDENCE.** *Driver torque and road reaction force estimation of an Electric Power Assisted Steering
using sliding mode observer with unknown inputs*, IEEE. The **driver torque and road reaction force are
the unknown inputs**; the motor command is a known plant input.
<https://ieeexplore.ieee.org/document/5625043/>

**EVIDENCE.** *Driver torque estimation in Electric Power Steering system using an H∞/H2 Proportional
Integral observer*, IEEE. Same partition.
<https://ieeexplore.ieee.org/iel7/7396016/7402066/07402334.pdf>

**EVIDENCE.** *Experimental Verifications of Electric Power Steering Controller Based on Discrete-Time
Sliding Mode Control with Disturbance Observer*, Int. J. Automotive Technology (2023).
<https://link.springer.com/article/10.1007/s12239-023-0072-z>

**EVIDENCE.** US11180186B2 (§3.1) explicitly forms the disturbance estimate **from the motor torque
command `T_a`** — the command is a known model input, by construction.

**EVIDENCE.** In autonomous/angle-following mode the partition **inverts**: *"the EPS role is to follow the
steering angle requested by lateral driver assistance functions, with driver torque considered as
disturbance to be rejected."* (surveyed in the ADRC/lateral-control literature, e.g.
<https://our.oakland.edu/bitstream/handle/10323/11953/Khasawneh_oakland_0446E_10306.pdf>)

**EVIDENCE.** GM's DSM (§1.2) feeds the **torque overlay command into the model** and treats only the
residual as intervention.

### 5.2 Verdict on the operator's suspected bug

🛑 **The universal published practice is: the actuator's own command is a KNOWN input to the plant model.
An observer that leaves its own command as an unknown disturbance will chase it.** I found **no**
published EPS observer that does otherwise — doing so would be a design error, not a design choice.

**BELIEF (this is the important qualification):** that does **not** establish that this firmware has the
bug. It establishes only that *if* the kit's traced observer omits the LKAS overlay from its plant model,
that omission is contrary to universal practice and is worth a targeted trace. **The crux to verify in
Ghidra is narrow and specific:** does the modelled-torque input to the residual computation include the
LKAS/overlay contribution, or only the base-assist contribution?

**BELIEF on what "chasing it" would look like:** an observer that treats its own overlay as an unknown
disturbance produces a residual proportional to the overlay **magnitude** — again magnitude-proportional,
again matching the data. This is therefore a **third** viable magnitude-proportional mechanism, and it is
the one that lives entirely in firmware. It is co-equal with §0.2 mechanisms 1 and 2 on the current
evidence; I cannot rank it without the trace.

---

## 6. Why 6–9 Hz and 18–28 Hz — the classic mode map

### 6.1 Published frequencies for each mode

| Mode | Published frequency | Citation |
|---|---|---|
| **Steering wheel on torsion bar** ("normal column mode") | **8–15 Hz** | EP2604487B1 (**EVIDENCE**, quoted in §1.3) |
| Lowest eigenfrequency of a column EPS model | **≈50 rad/s ≈ 8 Hz** | steer-by-wire modelling thesis, DiVA <https://uu.diva-portal.org/smash/get/diva2:1732738/FULLTEXT01.pdf> |
| Controlled EPS system resonance | **≈10 Hz**; crossover chosen **≥30 Hz** | EPS modelling literature (§ links below) |
| Dual-mode EPS first transfer function resonance | **≈12 Hz** | <https://dl.acm.org/doi/fullHtml/10.1145/3575882.3575894> |
| **Steering / suspension resonance** (nibble target) | **12–20 Hz**, most sensitive **10–15 Hz** | US8219283B2 (**EVIDENCE**) <https://patents.google.com/patent/US8219283B2/en> |
| Inertia-comp → damping crossover (OEM design choice) | **10–20 Hz** | US20130066520A1 (**EVIDENCE**) |
| Column with cantilever support (idle-shake band) | **20–50 Hz** | EPS vibration-mode literature (§ links below) |
| Steering feel design band | **0–40 Hz** | EPS design literature |
| Motor shaft order + 2nd harmonic | **460 Hz / 920 Hz** | EPS vibration-mode literature |

Supporting: *Analysis of vibration modes for electric power steering system* — three lumped masses
(**steering wheel, motor rotor, output shaft**) for a column-type EPS, *"low damping, especially at low
resonance frequency, which leads to a sharp peak on the Bode plot around the low resonance frequency."*
<https://www.researchgate.net/publication/287070902_Analysis_of_vibration_modes_for_electric_power_steering_system>

### 6.2 Mapping to the operator's two bands

**BELIEF, with the frequency evidence above:**

- **6–9 Hz** = the **steering-wheel-on-torsion-bar mode** (mass 1 against masses 2+3). Published as 8–15 Hz;
  6–9 Hz is at the low end, which is what you expect with **added hand/arm inertia** on the rim. It is the
  **lowest and most lightly damped** mode in the system — the literature's *"sharp peak … around the low
  resonance frequency"*. The kit's measured **Q 14–29** is entirely consistent.
  🛑 It is **on the far side of the torque sensor from the motor**, which is precisely why an overlay
  reaction shows up there and why grip damps it.
- **18–28 Hz** = the **motor-rotor / worm-mesh mode** (mass 2 against mass 3, through worm backlash,
  anti-rattle spring preload, and mesh stiffness), overlapping the steering/suspension band at 12–20 Hz.
  This is the band where nibble lives and where OEMs switch from inertia compensation to damping.

### 6.3 Which one does an un-cancelled overlay excite?

**BELIEF:** the **6–9 Hz** mode, for a structural reason: the torque sensor is *inside* the loop that
contains it. The motor pushes on `θ_c`; the sensor measures `θ_h − θ_c`; the assist reacts to the sensor;
the wheel-on-torsion-bar mode is the resonance of exactly that coordinate. Any assist-loop peaking lands
there first. The 18–28 Hz mode is *downstream* of the sensor in the mesh, which points at
friction/backlash excitation (§6.4) rather than at loop peaking.

### 6.4 ★★★ The magnitude-proportional mechanism, with citations

**EVIDENCE — normal force at the worm mesh is proportional to transmitted torque.** From the open-access
worm-gear efficiency model for EPS (Mechanical Sciences 9:201, 2018)
<https://ms.copernicus.org/articles/9/201/2018/>:

```
F_n,T  =  T_wh · √(1 + tan²γ + tan²α) / R_p
```

with efficiency

```
η = [cos α − μ tan γ] / [cos α + μ cot γ] × 100 (%)
```

and, for the steel-worm/polymer-wheel contact used in column EPS,

```
μ = a · P_n^n        with  n ≈ −0.9   (sliding)
```

reaching **μ = 0.029 at 130 MPa**. Misalignment from the anti-rattle preload:
`x = [d₂·T_wh − M] / [k(d₁ + d₂)]` — **−1.10 mm at zero output torque, perfect alignment at 19.67 Nm** —
so the paper notes *"the efficiency with misalignment shows lower efficiency values than efficiency
without misalignment at low output torque conditions."*

**⇒ Coulomb friction torque at the mesh scales as `μ·F_n·r ∝ T_transmitted`. Load-dependent friction is
MAGNITUDE-proportional by construction.** This is the mechanism the operator's data is pointing at.

**EVIDENCE — gear friction is split into load-independent and load-dependent parts, and the load-dependent
part is asymmetric in the direction of power flow:** *Dynamics modeling of gear transmissions with
asymmetric load-dependent friction*, Mechanism and Machine Theory.
<https://www.sciencedirect.com/science/article/abs/pii/S0094114X22003627>

**EVIDENCE — the anti-rattle spring is itself a friction source in column EPS:** *"a worm gear is used in
column-type electric power steering systems, and an anti-rattle spring is employed to prevent rattling,
but it also generates undesirable friction by causing misalignment of the worm shaft."* (same MS paper;
see also TRW US6357313 <https://patents.google.com/patent/US6357313>).

**EVIDENCE — stick–slip at the worm mesh is a recognised EPS phenomenon:** friction noise in EPS worm-gear
systems arises from stick–slip, *"where the static friction coefficient exceeds the dynamic one, coupled
with system elasticity, which creates intermittent sliding."*
<https://www.zhygear.com/research-on-friction-noise-in-worm-gear-systems-of-electric-power-steering/>
(trade source — lower evidentiary weight than the patents and journals above; cited for the phenomenon's
existence in this specific component, not for numbers.)

**EVIDENCE — the instability mechanism is negative damping from the Stribeck curve:** *Friction-Induced
Vibration by Stribeck's Law*, Tribology Letters.
<https://link.springer.com/article/10.1007/s11249-012-0100-z> and
<http://perso.ec-lyon.fr/alain.le.bot/triblet43.pdf> — a 1-DOF mass-spring-damper under a velocity-
dependent friction force following Stribeck's law goes unstable where the friction–velocity gradient is
negative; *"stick-slip is more likely to occur in the range of the Stribeck curve where friction and
velocity have negative gradient characteristics."*

**⇒ The complete magnitude-proportional chain (BELIEF, but every link is individually EVIDENCE):**

```
LKAS command magnitude ↑
   → transmitted torque through worm mesh ↑
      → normal force F_n ∝ T ↑                                    [MS 9:201, EVIDENCE]
         → Coulomb friction μ·F_n·r ↑                             [Coulomb, EVIDENCE]
            → negative friction–velocity slope supplies negative damping   [Stribeck, EVIDENCE]
               → self-excited stick–slip                          [EVIDENCE]
                  → rings the lightly damped structural mode      [Q 14-29, kit's own measurement]
                     → felt as GRINDING / MICRO-RATCHETING at the rim
```

**Nothing in this chain is rate-dependent in the way an inertial coupling would be.** The frequency comes
from the structure; the amplitude comes from the load; the load comes from the command **magnitude**.

**EVIDENCE that this is not exotic — an OEM already schedules damping on torque magnitude for exactly this
reason.** US6122579A, **Delphi Technologies**, priority 28 May 1999:
> *"the gain factor increases with the magnitude of I_DAMPED, since more damping compensation is desired
> at high torque."*
<https://patents.google.com/patent/US6122579>

### 6.5 ★ The independent corroboration: felt friction scales with assist gain

**EVIDENCE.** Li et al., *Research on Friction Compensation Control for Electric Power Steering System*,
Mathematical Problems in Engineering 2016:8470786 (also SAE 2016-01-1542).
<https://onlinelibrary.wiley.com/doi/10.1155/2016/8470786> · <https://www.sae.org/publications/technical-papers/content/2016-01-1542/>

> *"The change of EPS assist torque under fixed amplitude friction compensation torque can cause the
> driver's steering feeling fuzzy. That is due to the fact that **the friction torque felt by driver varies
> with EPS assist gain**. Therefore, a further modified friction compensation control method is proposed
> based on EPS assist gain to make the driver have similar friction feeling."*

Their remedy is *"a variable friction compensation control method which the friction compensation current
changes according to the assist characteristic gain."*

🛑 **This is a peer-reviewed paper independently concluding that friction compensation must be scaled by
the assist/command magnitude.** That is the same functional form as `0xC40D2` (K1, `|model|`-proportional
modelled Coulomb friction). **The kit's V89 lever has an OEM-adjacent literature precedent.**

Standard friction-compensation formulation for reference (**EVIDENCE**): *"Coulomb friction is estimated as
a fixed value that is added to or taken away from the motor torque (current) command according to the
**sign of the velocity command**"*; production implementations use *"the sign function of angular velocity
or the saturation function of angular velocity"*, sometimes via a **map from steering wheel angular
velocity to Coulomb friction compensation value**. See also US9493183 (*Friction compensation logic of
motor driven power steering*) <https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9493183>
and CN105292246A <https://patents.google.com/patent/CN105292246A/en>.

### 6.6 Other candidate mechanisms, assessed

| Candidate | Magnitude-proportional? | Verdict |
|---|---|---|
| **Load-dependent Coulomb friction, worm mesh** | ✅ `F_n ∝ T` | **PRIMARY.** §6.4 |
| **Quasi-static grip/road impedance divider** | ✅ static gain `G_0` | **STRONG.** §3.2. Requires grip or a compliant road path. |
| **Observer chasing its own overlay** | ✅ residual ∝ command | **STRONG, and firmware-local.** §5.2. Needs a trace. |
| **Gear mesh preload / anti-rattle spring** | Partly — preload is *constant*, but misalignment is torque-dependent | **CONTRIBUTING.** §6.4; explains why the effect is worst at low output torque. |
| **Motor cogging / torque ripple under load** | ✅ **partly** | **PLAUSIBLE SECONDARY.** **EVIDENCE:** *"all electric motors exhibit torque ripple, primarily due not to cogging, but to **armature reaction**. As the current level rises, flux in the magnetic circuit shifts, introducing harmonics into the motor torque constant waveform."* <https://www.kollmorgen.com/en-us/blogs/everywhere-cogging-torque-and-torque-ripple-what-you-need-to-know> — **load-dependent ripple, magnitude-proportional.** But ripple frequency is locked to *rotor position*, so it would be speed-dependent, not fixed at 6–9 Hz. 🛑 Does not fit the speed-invariant frequency. |
| **Current-loop nonlinearity** (deadtime, quantisation) | Usually *inversely* — worst at low current | **UNLIKELY** to produce a magnitude-*increasing* effect. |
| **Torque-sensor hysteresis under load** | ✅ hysteresis grows with twist | **CONTRIBUTING.** **EVIDENCE:** *"hysteresis is generated from the sensor, the torsion bar itself, bearings on the upper and lower shafts, and any misalignment of the shafts. The amount of hysteresis of the sensor, torsion bar, and bearings can be **0.5 Nm or larger**"*; and *"Higher torque can … bring in more hysteresis as a result of the torsion bar being twisted beyond its primary linear range."* — US6817439 <https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6817439>, MATEC torsion bar study <https://www.matec-conferences.org/articles/matecconf/pdf/2018/91/matecconf_eitce2018_04051.pdf>. A 0.5 Nm hysteresis band inside a loop with high assist gain is a textbook micro-limit-cycle generator. |
| **Inertial reaction `J·α`** | ❌ rate/acceleration-proportional | 🛑 **REFUTED** as dominant by the operator's own rate-null. |

---

## 7. Remedies, ranked by implementation cost

Ranking assumes the kit's hard constraints: **no biquad/notch exists anywhere**, **no frequency-selective
lever exists**, **code caves are the only bricking class**, and pure-gain remedies are strongly preferred.

### 7.1 ★ R1 — Raise damping compensation (motor-velocity feedback), ideally scheduled on torque magnitude

- **Physically:** adds `−c·θ̇_m` to the motor command. Directly lowers the **Q** of both bands. A mode with
  Q≈20 needs only a few percent of critical damping added to be halved.
- **Cost:** **CALIBRATION — a single gain**, if a damping gain cell exists and is live in the regime.
- **Precedent (EVIDENCE):** the OEM taxonomy assigns micro-vibration to the damping term (US11208142, §2.1);
  10–20 Hz is explicitly the damping band (US20130066520A1, §2.4); and **damping gain scheduled on torque
  magnitude is production practice** — US6122579A, `GAIN = max(0, K_G·(I_MAG − G_OFFSET))`, *"more damping
  compensation is desired at high torque"* (§6.4). See also US9738309 (*Active-damping based approach to
  mitigate effects of rack disturbances on EPS*) <https://patents.justia.com/patent/9738309> and
  US6658335 (*motor velocity measurement compensation in EPS damping*) — the latter notes EPS has *"a free
  rotational oscillation resonance that may result in lack of crisp, controlled feel."*
- **Instability risk:** **LOW-to-MODERATE.** Damping is phase-lead-ish and generally stabilising, but
  velocity is a differentiated signal — too much gain amplifies sensor noise and, with loop delay, can
  destabilise at higher frequency. Sizing matters.
- **Expected symptom change:** reduced grinding/micro-ratcheting amplitude in both bands; **cost is a
  heavier, more "damped/dead" wheel**, especially on-centre.
- 🛑 **The kit already knows the plain version of this lever is blocked:** `accord-damper-cannot-reach-micro-regime`
  records that `ch0 = (FactorC(speed) × FactorE(rate)) >> 10` is a product of two dead zones and is zero on
  100 % of the micro regime. **The literature's answer to that is R1′ below** — do not schedule damping on
  *rate*; schedule it on *torque magnitude*, which is nonzero exactly when the symptom occurs. That is
  precisely what US6122579A does, and it sidesteps the FactorE `Y[0]`-off-zero problem that produced the
  V80 "worst grinding ever" result.

### 7.2 R1′ — Damping (or friction) scheduled on **command magnitude** rather than rate

- **Physically:** the excitation is magnitude-proportional (§6.4), so the compensation should be too.
- **Cost:** **CALIBRATION if a magnitude-indexed cell exists; otherwise a small CODE change** to re-index an
  existing table's axis.
- **Precedent (EVIDENCE):** US6122579A (damping gain ∝ torque magnitude) and Li 2016 (friction compensation
  ∝ assist gain), §6.4–6.5. **Two independent sources, one patent and one journal.**
- **Risk:** MODERATE — an axis change is a bigger edit than a value change, and the kit's record
  (`accord-damper-cannot-reach-micro-regime`) shows axis/breakpoint work on this surface has bitten before.
- **BELIEF: this is the single best match between the external literature and the measured symptom.**

### 7.3 R2 — Raise modelled Coulomb friction in the observer (the current V89 lever)

- **Physically:** if the observer under-models friction, it chases real friction as a disturbance —
  a positive-feedback-like interaction with stick–slip.
- **Cost:** **CALIBRATION, one cell** (`0xC40D2`). Already built.
- **Precedent (EVIDENCE):** Li 2016's assist-gain-scaled friction compensation (§6.5) is the same functional
  form. The worm-gear model (§6.4) says load-proportional friction is the physically correct form.
- **Risk:** **MODERATE.** Over-compensated friction is a known failure: the Li paper's whole premise is that
  a *fixed-amplitude* friction compensation makes steering feel *"fuzzy"*. The kit's own note that V89
  *"may feel notchier on-centre"* is the same concern from the same physics.
- **Honest assessment:** the literature endorses the **form** of this lever and is silent on its **sign and
  dose** in this specific implementation. That matches the kit's own EVIDENCE/BELIEF split.

### 7.4 R3 — Feed-forward cancellation of the overlay in the torque-sensor path

- **Physically:** `T_driver_est = LPF(T_sensor) + K·LPF(T_lkas)` — Honda's own form (§1.1, §3.1).
- **Cost:** **CODE (a cave)** unless a summing point already exists — the LKAS command must reach the assist
  path's sensor input, and a gain and a first-order filter must be evaluated there.
- **Risk:** **HIGH, and specifically a SIGN risk.** `G_0 < 0`, removal is by **addition**, and `K` is an
  operating-point-dependent impedance ratio (§3.2), not a constant. A sign error converts a de-amplification
  into positive feedback around a loop that already has *"a very small phase angle margin"* (§4). Combined
  with GATE 1 / GATE 2 and the kit's three cave bricks, **I do not recommend this as the next step.**
- **Expected symptom change:** would restore full LKAS authority (removing the `1/(1+A|G_0|)` tax) and
  remove one of three candidate mechanisms. **It would do nothing for the friction/stick-slip mechanism**,
  which I rank higher.

### 7.5 R4 — Lower the base assist boost gain in the affected regime

- **Physically:** lowers `A`, raising phase margin and shrinking `A·|G_0|`.
- **Cost:** **CALIBRATION.**
- **Risk:** LOW for stability, but **heavier steering** — a direct feel regression.
- 🛑 **Not the 4× LKAS gain** — `accord-4x-lkas-gain-is-the-frozen-variable` is explicit that it scales
  *excitation*, not loop gain, and must never be lowered. The boost/assist gain is a different quantity.

### 7.6 R5 — Inertia compensation

- **Cost:** CODE (a filter). **Risk:** HIGH.
- 🛑 **Wrong band** (§2.2): designed for the ~35 Hz zero / ~40 Hz phase-crossover problem, deliberately inert
  at low frequency, and needs ≥250 Hz measurement bandwidth in the acceleration form.
- **Not recommended.**

### 7.7 R6 — Notch / resonator cancellation

- 🛑 **NOT IMPLEMENTABLE.** The kit has established there is no biquad anywhere. For the record, this is the
  standard industry answer to a fixed-frequency steering vibration: US8219283B2 (Ford) uses a tuned
  resonator
  `SN(z) = [N₀z² + N₁z + N₂]/[D₀z² + D₁z + D₂]·T_column(z)`, with `N₀=(1−R)`, `N₁=0`, `N₂=(R−1)`, `D₀=1`,
  `D₁=−2R·cos θ`, `D₂=R²`, `R≈0.985`, `θ=ω_n·T_s`, giving *"0° phase lag and gain of 1 at the front wheel
  frequency."* US8744682B2 (GM) uses adaptive learning with `SWT_n = X_n·ACF_n` instead.
  <https://patents.google.com/patent/US8744682B2/en> · US8271163 (smooth road shake)
  <https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8271163>
- **Value of citing it:** it confirms the kit's structural conclusion — **without a biquad you cannot do
  what the industry does, so you must attack Q and excitation with gains instead.** That is R1/R1′/R2.

### 7.8 Summary ranking

| # | Remedy | Cost | Instability risk | Fit to the magnitude-proportional evidence |
|---|---|---|---|---|
| 1 | **R1′ damping/friction scheduled on command MAGNITUDE** | Cal → small code | Low–Mod | ★★★★★ |
| 2 | **R1 raise damping gain (if reachable in-regime)** | Calibration | Low–Mod | ★★★★ |
| 3 | **R2 modelled Coulomb friction (V89, built)** | Calibration | Moderate | ★★★★ |
| 4 | **R7 in-band low-pass of the overlay** (§8) | Depends | Low | ★★★ |
| 5 | R4 lower base assist boost gain | Calibration | Low | ★★★ (feel cost) |
| 6 | R3 feed-forward overlay cancellation | **Code cave** | **High (sign)** | ★★★ |
| 7 | R5 inertia compensation | Code | High | ★ (wrong band) |
| 8 | R6 notch | **Impossible** | — | — |

---

## 8. Rate limiting vs in-band shaping of the overlay — the brief's internal tension, resolved

### 8.1 The literature's position

**EVIDENCE.** Denso US10035538B2 (priority 10 Nov 2014, inventors Akatsuka, Kataoka, Matsumoto, Iida)
<https://patents.google.com/patent/US10035538B2/en> is the closest production analogue to this kit's
situation: an EPS whose final command is `DC = AC (assist) + TC (tracking/lane-keep)`, i.e. **a simple
additive overlay with no torque-sensor correction**:

> *"The final command DC is the sum of an assist command AC that is a current value required for the
> electric motor 6 to produce the assist torque and a tracking command TC that is a current value required
> for the electric motor 6 to produce the automatic steering torque"*

and — critically — Denso confirms this architecture **causes steering vibration**, and gives their remedy:

> *"the electric power steering system is engineered to control the response rate at which the automatic
> steering torque is produced, so that it will be insensitive to noise, thus suppressing the steering
> vibration"*

Two embodiments: **scale the PID gains** by a responsiveness factor α (`α·Kp, α·Ki, α·Kd`), or **change the
cut-off frequency `fc` of a low-pass filter** on the tracking command. The tracking-response calculator
*"sets the responsiveness α to a lower value … in order to enhance the suppression of the steering
vibration."* The torque sensor signal is **not** corrected.

★ **Note what Denso does NOT do: they do not slew-limit. They lower a GAIN and lower a LOW-PASS CORNER.**

### 8.2 Resolving the tension

The brief frames this as: *if the coupling were inertial, the symptom should scale with command RATE; our
data says MAGNITUDE; is rate-limiting therefore the wrong lever?*

**Answer: the data is right, rate-limiting is the wrong lever, and the literature agrees — but the
conclusion generalises less far than the kit has taken it.**

🛑 **A slew-rate limit and an in-band low-pass are different operations, and the kit's refutation covers
only the first.**

- A **slew limiter** is a *nonlinear* clip on `dT/dt`. It only binds on fast transients and does nothing to
  a large, slowly varying command. Against a magnitude-proportional friction mechanism it is **useless** —
  the kit's null is correct and expected.
- An **in-band low-pass** (Denso's `fc`) reduces the command's **magnitude at specific frequencies**. If a
  meaningful part of the 6–9 Hz ring is being *driven* rather than merely *load-enabled*, lowering `fc`
  attacks it. If the ring is purely load-modulated, it does not.
- A **flat gain reduction** (Denso's α) reduces command magnitude at *all* frequencies. Against a
  magnitude-proportional mechanism this is **the direct lever** — but it also reduces lane-keeping
  authority proportionally, which is a functional regression, and the kit's own record already establishes
  that de-relaying in that direction made things **worse** (`0xC40BC` 600 → 6000 gave 6.58× vs 2.89×).

**BELIEF:** given `accord-v88-flew-grinding-fixed-command-intact` (15–22 Hz command content already
0.549 [0.407, 0.844] with 0.5–3 Hz a null at 1.192) and `reference-accord-lkas-lane-is-a-lowpass` (the LKAS
lane is already a ~1–5 Hz low-pass), **there is little 6–9 Hz content left in the command to remove.** That
argues the ring is **load-modulated, not directly driven** — which is mechanism §6.4, and which points back
to R1′/R2 rather than to any command-shaping lever.

**⇒ Final position on §7 of the brief: the kit's refutation of rate-limiting is sound and the literature
supports it. The kit should not, however, generalise it into "do not shape the command" — Denso's
production answer to this exact architecture is gain-and-low-pass shaping. It is a lower-priority lever
here only because the kit's own spectra show the in-band content is already small.**

---

## 9. Signals required — all of which this ECU has internally

| Remedy | Signal(s) needed | Notes |
|---|---|---|
| R1 / R1′ damping | **motor angular velocity** (or column rate); **motor torque command magnitude** for the schedule | Kit has `gp-0x6abc ← gp-0x4f50` = motor rate, and `gp-0x6c2c` = motor-rate derivative |
| R2 modelled friction | **modelled torque magnitude** (`|model|`) and **sign of column/motor velocity** | `0xC40D2` K1 is already `|model|`-proportional |
| R3 feed-forward cancel | **LKAS command torque**, and a first-order LPF state | Must reach the assist path's sensor input |
| R5 inertia comp | **motor angular acceleration** (≥250 Hz bandwidth) or velocity + differentiator | Bandwidth is the binding constraint |
| Observer fix (§5) | **LKAS command as a known plant-model input** | The trace to run |

---

## 10. Recommended next actions (for the orchestrator to weigh — not a decision)

1. 🛑 **Run the §5.2 trace, and treat it as the crux.** Narrow question: *does the modelled-torque input to
   the residual/disturbance computation include the LKAS overlay contribution, or only base assist?*
   This is the one candidate mechanism that is entirely firmware-local, is magnitude-proportional,
   contradicts universal published practice if absent, and is cheap to answer.
2. **Re-examine the damping surface for a TORQUE-MAGNITUDE axis** rather than the rate axis that
   `accord-damper-cannot-reach-micro-regime` showed is dead on 100 % of the micro regime. US6122579A is the
   existence proof that a torque-magnitude-indexed damping schedule is normal production practice, and it
   avoids the `FactorE Y[0]`-off-zero step that caused V80.
3. **Design a mechanism discriminator, not another dose ladder.** §3.2 predicts the quasi-static coupling
   **vanishes hands-off** (`k_d = 0 ⇒ G_0 = 0`) while the load-dependent-friction mechanism does **not**.
   The kit already has a grip covariate and already knows grip damps the mode. A matched
   **grip × command-magnitude** contrast at matched wheel rate separates §0.2 mechanism 1 from mechanism 2.
   🛑 `accord-leverb-discriminator-underpowered` says the binding constraint is **exposure**, not analysis —
   so this needs to be designed into a drive, not extracted from the existing corpus.
4. **Do not reach for a code cave for R3.** The sign risk (§7.4) is real, `K` is not a constant, and three
   caves have bricked this ECU.

---

## 11. Citation index

| # | Source | Type | Used in |
|---|---|---|---|
| 1 | **US11685438B2** — Honda, *Vehicle control apparatus*, prio 2020-03-13 <https://patents.google.com/patent/US11685438B2/en> | Patent | §1.1, §3.1, §3.3 ★★★ |
| 2 | **CN101746412B** — GM, *Detection of driver intervention during torque overlay*, prio 2008-12-17 <https://patents.google.com/patent/CN101746412B/en> | Patent | §1.2, §5.1 |
| 3 | **EP2604487B1** — Steering Solutions, *Hands on steering wheel detect in lane centering*, prio 2011-12-15 <https://patents.google.com/patent/EP2604487B1> | Patent | §1.3, §6.1 |
| 4 | **US9415798B2** — Steering Solutions, *Inertia compensation…*, prio 2014-02-26 <https://patents.google.com/patent/US9415798B2/en> | Patent | §2.2, §2.3 |
| 5 | **US20130066520A1** — Steering Solutions, *Inertia compensation with frequency dependent damping*, prio 2011-09-09 <https://patents.google.com/patent/US20130066520A1/en> | Patent | §2.4, §6.1 |
| 6 | **US11180186B2** — Steering Solutions, *Disturbance feedforward compensation*, prio 2018-04-05 <https://patents.google.com/patent/US11180186B2/en> | Patent | §3.1, §5.1 |
| 7 | **US6122579A** — Delphi, *EPS control with torque ripple and road disturbance damper*, prio 1999-05-28 <https://patents.google.com/patent/US6122579> | Patent | §6.4, §7.1, §7.2 ★★★ |
| 8 | **US10035538B2** — Denso, *EPS with motor controller*, prio 2014-11-10 <https://patents.google.com/patent/US10035538B2/en> | Patent | §8.1 ★★★ |
| 9 | **US8219283B2** — Ford, *Active steering nibble control algorithm*, prio 2007-11-14 <https://patents.google.com/patent/US8219283B2/en> | Patent | §6.1, §7.7 |
| 10 | **US8744682B2** — GM, *Reducing the effects of vibrations in an EPS system*, prio 2008-05-30 <https://patents.google.com/patent/US8744682B2/en> | Patent | §7.7 |
| 11 | **US11208142** — *Steering feel control apparatus… MDPS* <https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11208142> | Patent | §2.1 |
| 12 | **US6817439** — *Controlling an EPAS with low hysteresis and torque ripple* <https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6817439> | Patent | §6.6 |
| 13 | **US6597136 / EP1211158A2** — TRW LucasVarity, *Compensation for motor inertia* <https://patents.google.com/patent/EP1211158A2/en> | Patent | §2.4 |
| 14 | **US9731757** — *Closed loop EPAS systems* <https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9731757> | Patent | §4 |
| 15 | **US9738309** — *Active-damping based approach to mitigate rack disturbances* <https://patents.justia.com/patent/9738309> | Patent | §7.1 |
| 16 | **US9493183** — *Friction compensation logic of MDPS* <https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9493183> | Patent | §6.5 |
| 17 | **US8849516** — *Adaptation of a steering wheel torque overlay of a lane keeping aid* <https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8849516> | Patent | §1.4 |
| 18 | **EP3018040A1** — *Intelligent scaling of torque overlay intervention* <https://patents.google.com/patent/EP3018040A1/tr> | Patent | §1.4 |
| 19 | **US10625773B2** — *Steer torque manager for an ADAS* <https://patents.google.com/patent/US10625773B2/en> | Patent | §1.4 |
| 20 | **US10179602B2** — Toyota, *Driver assistance system*, prio 2017-01-13 (cites **JP2007-030612A** for the LKA-torque-corrected compensating-torque architecture) <https://patents.google.com/patent/US10179602B2/en> | Patent | §1, lineage |
| 21 | **US6357313B1** — TRW, *EPS comprising a worm gear* <https://patents.google.com/patent/US6357313> | Patent | §6.4 |
| 22 | **Mechanical Sciences 9:201 (2018)** — *Worm gear efficiency model considering misalignment in EPS* <https://ms.copernicus.org/articles/9/201/2018/> | Journal (OA) | §6.4 ★★★ |
| 23 | **Li et al., Math. Problems in Eng. 2016:8470786 / SAE 2016-01-1542** — *Friction Compensation Control for EPS* <https://onlinelibrary.wiley.com/doi/10.1155/2016/8470786> | Journal | §6.5 ★★★ |
| 24 | **Mechanism and Machine Theory** — *Dynamics modeling of gear transmissions with asymmetric load-dependent friction* <https://www.sciencedirect.com/science/article/abs/pii/S0094114X22003627> | Journal | §6.4 |
| 25 | **Tribology Letters** — *Friction-Induced Vibration by Stribeck's Law* <https://link.springer.com/article/10.1007/s11249-012-0100-z> · PDF <http://perso.ec-lyon.fr/alain.le.bot/triblet43.pdf> | Journal | §6.4 |
| 26 | **Complexity 2020:9371327** — *Structured Control of an EPS System* (phase margin) <https://www.hindawi.com/journals/complexity/2020/9371327/> | Journal | §4 |
| 27 | **IEEE** — *Driver torque and road reaction force estimation of an EPAS using sliding mode observer with unknown inputs* <https://ieeexplore.ieee.org/document/5625043/> | Conference | §5.1 |
| 28 | **IEEE** — *Driver torque estimation in EPS using an H∞/H2 PI observer* <https://ieeexplore.ieee.org/iel7/7396016/7402066/07402334.pdf> | Conference | §5.1 |
| 29 | **Int. J. Automotive Technology (2023)** — *EPS Controller Based on Discrete-Time SMC with Disturbance Observer* <https://link.springer.com/article/10.1007/s12239-023-0072-z> | Journal | §5.1 |
| 30 | **Springer** — *Inertia Compensation Based on Torque Signal in an EPS System* <https://link.springer.com/chapter/10.1007/978-3-642-33829-8_71> | Chapter | §2.4 |
| 31 | **ACM/ICVISP** — *Modeling and Analysis of a Dual-mode EPS for Manual and Autonomous Driving* <https://dl.acm.org/doi/fullHtml/10.1145/3575882.3575894> | Conference | §6.1 |
| 32 | **DiVA (Uppsala)** — *Development and Analysis of a Detail Model for Steer-by-Wire* <https://uu.diva-portal.org/smash/get/diva2:1732738/FULLTEXT01.pdf> | Thesis | §6.1 |
| 33 | **ResearchGate** — *Analysis of vibration modes for electric power steering system* <https://www.researchgate.net/publication/287070902_Analysis_of_vibration_modes_for_electric_power_steering_system> | Paper | §6.1 |
| 34 | **MATEC Web Conf.** — *EPS Sensor Torsion Bar Design and Structure Analysis* <https://www.matec-conferences.org/articles/matecconf/pdf/2018/91/matecconf_eitce2018_04051.pdf> | Conference (OA) | §6.6 |
| 35 | **Kollmorgen** — *Cogging Torque vs Torque Ripple* (armature reaction ⇒ load-dependent ripple) <https://www.kollmorgen.com/en-us/blogs/everywhere-cogging-torque-and-torque-ripple-what-you-need-to-know> | Trade | §6.6 |
| 36 | **ZHY Gear** — *Research on Friction Noise in Worm Gear Systems of EPS* <https://www.zhygear.com/research-on-friction-noise-in-worm-gear-systems-of-electric-power-steering/> | Trade (low weight) | §6.4 |
| 37 | **Oakland Univ.** — *Robust and Adaptive Lateral Controller for Autonomous Vehicles* <https://our.oakland.edu/bitstream/handle/10323/11953/Khasawneh_oakland_0446E_10306.pdf> | Dissertation | §5.1 |

**37 sources, 21 of them patents or peer-reviewed journal/conference papers cited for a specific technical
claim.**

---

## 12. Sources I could not retrieve (stated so the record is honest)

Paywalled or blocked; their content is used **only** via the search-result abstracts, which I have marked
as such where relied upon, and never as the sole basis for a decision-bearing claim:

- Complexity 2020:9371327 full text — HTTP 403. The phase-margin quote in §4 is from the abstract.
- Li 2016 full text (Wiley 402 / Hindawi 403) — the §6.5 quotes are from the published abstract, which
  states the assist-gain-varying-friction result explicitly.
- Sagepub *Model-based feedforward control for suppressing torque oscillation of EPS* (2022) — HTTP 403.
- ACM *Dual-mode EPS* full text — HTTP 403; the 12 Hz figure is from the search index.
- Chalmers *Functional Modelling and Simulation of an EPS* PDF — retrieved but not text-extractable.

🛑 **No numerical parameter value in this document (inertias, stiffnesses) comes from a source I could not
read.** The one derivation with numbers (§3.2) is symbolic and marked BELIEF.

---
---

# APPENDIX A — follow-up, 2026-08-10

Commissioned after the orchestrator's Ghidra trace established that **this firmware does NOT violate
universal practice**: the overlay is a known input on *both* sides of the observer (plant input
`gp-0x6b98`; reconstruction lane `gp-0x6b4e` at unity weight `0xC63A8` = 1024). §5 of the main report is
therefore **answered and closed** — the ECU is not a counterexample to the "zero counterexamples" finding.

What replaced it is a **filter-mismatch residue** between the two copies of the overlay, giving two
mechanisms with the same statistical signature:

- **M1** — observer cancellation residue from the filter mismatch (control-loop origin, firmware-local).
- **M2** — load-dependent worm-mesh friction (tribological origin, physical).

---

## A.0 HEADLINE — three results, two of which correct my own earlier work

### A.0.1 ★★★ The kit's "not a relay" evidence does NOT refute M2. It refutes the wrong form of M2.

**This is the single most important thing in this appendix, and it is a correction to how I framed §6.4.**

Friction-induced vibration has **two distinct regimes**, not one, and they have been distinguished in the
tribology literature since 1970:

| | **Stick-slip (relaxation oscillation)** | **Quasi-harmonic FIV (pure slip)** |
|---|---|---|
| Sticking phases | **Yes** — velocity genuinely reaches zero | **No** — never sticks, oscillates about a nonzero sliding velocity |
| Waveform | Sawtooth / discontinuous, **strongly non-sinusoidal** | **"of near-sinusoidal form"** |
| Harmonic content | Rich odd-harmonic comb | **Low** — near-pure tone |
| Phase-locking to velocity reversals | **Strong** — it *is* a relay | **None** — there are no reversals to lock to |
| Governed by | Static-vs-kinetic friction difference | **"solely governed by dynamic friction forces"** |
| Occurs at | **Lower** sliding velocity | **Higher** sliding velocity |
| Frequency | Depends on drive velocity | **Pinned at the structural natural frequency** |
| Looks like, in ring-down | A relay | **A lightly damped linear resonance** |

**EVIDENCE.** Brockley, C. A. & Ko, P. L., *Quasi-Harmonic Friction-Induced Vibration*, ASME **Journal of
Lubrication Technology 92(4):550–556, October 1970**.
<https://asmedigitalcollection.asme.org/tribology/article/92/4/550/429814/Quasi-Harmonic-Friction-Induced-Vibration>
The vibration *"is of near-sinusoidal form and solely governed by dynamic friction forces, though the
friction-velocity curve must be of a particular shape for the vibration to occur"*; *"the amplitude of the
quasi-harmonic vibration increases with sliding velocity until oscillation ceases at some upper velocity
boundary"*; and — decisive for §7 — ★ ***"The introduction of suitable damping will quench the vibration
entirely."***

**EVIDENCE.** *A new approach of stick-slip based on quasi-harmonic tangential oscillations*, Wear.
<https://www.sciencedirect.com/science/article/abs/pii/S0043164897002962> — *"quasi-harmonic tangential
oscillations occur during friction induced by a negative instantaneous force-relative velocity gradient"*;
*"stick-slip vibrations occur generally at lower sliding velocity and quasi-harmonic vibrations at higher
sliding velocity."*

🛑 **Now re-read the kit's four null results against the right column of that table:**

| Kit result | Refutes stick-slip? | Refutes quasi-harmonic FIV? |
|---|---|---|
| Odd/even harmonic comb **0.858 [0.739, 1.000]** vs positive control 1.204 at 15 % injection | ✅ yes | ❌ **No — quasi-harmonic FIV is near-sinusoidal, so a comb ratio at unity is exactly what it predicts** |
| 3:1 phase-locking **PLV z ≤ 1.05** | ✅ yes | ❌ **No — pure slip has no reversals to lock to** |
| Switching-surface time-locking **−0.0375** ⇒ <15 % relay-generated | ✅ yes | ❌ **No — there is no switching surface in pure slip** |
| Ring-down **ζ = 0.017–0.036**, passed its control | ✅ yes (a relay would fail a ring-down control) | ❌ **No — quasi-harmonic FIV IS a lightly damped resonance with reduced effective damping** |

**⇒ Every one of the kit's four null results is precisely what quasi-harmonic FIV predicts.** The kit did
not falsify the friction hypothesis; it **falsified the relay form of it and thereby identified which
form is running.** Far from being "a serious problem for M2", the "not a relay" evidence is
**positive evidence for the quasi-harmonic branch of M2** — the branch that produces a clean, lightly
damped, near-sinusoidal resonance at a structural frequency.

**Two further consistency checks that now land the right way up (BELIEF, from the EVIDENCE above):**
- Brockley–Ko: amplitude **increases with sliding velocity**. The kit measured 6–9 Hz engaged/manual at
  **1.16× at 2 °/s → 3.94× [2.19, 6.70] at 100 °/s** (`accord-ratchet-axis-is-wheel-rate`). ✅ Match.
- Quasi-harmonic frequency is **pinned to the structural mode**, unlike stick-slip whose frequency tracks
  drive velocity. The kit measured the ratchet as **speed-invariant at median 7.79 Hz**. ✅ Match. A
  classical stick-slip oscillator would *not* be speed-invariant.

### A.0.2 ★★★ I reproduced the M1 residue exactly — and it is intrinsically a HIGH-BAND mechanism

Your filters run at **1 kHz**, not 100 Hz. I confirmed this by fitting: at 100 Hz nothing reproduces your
numbers (every variant peaks near 2.5–3.7 Hz and *declines* to 21 Hz); at **1 kHz the match is exact**.

```
H_A(z) = z⁻¹ · [ α_A / (1 − (1−α_A)z⁻¹) ]²      α_A = 573/4096 = 0.139893   (model side, EMA² + 1 tick)
H_B(z) =        α_B / (1 − (1−α_B)z⁻¹)          α_B = 102/1024 = 0.099609   (reconstruction side, IIR¹)
                                                 fs = 1000 Hz
```

| f (Hz) | \|H_A − H_B\| | **arg(H_A − H_B)** | your value |
|---|---|---|---|
| 0 | 0.0000 | — | 0.005 ✅ |
| 3 | 0.0796 | −101.7° | |
| 6 | 0.1549 | −113.4° | |
| **7.79** | **0.1960** | **−120.3°** | **0.196 ✅ exact** |
| 9 | 0.2216 | −124.9° | |
| 15 | 0.3165 | −146.1° | |
| 18 | 0.3438 | −155.4° | |
| **21** | **0.3598** | **−163.7°** | **0.360 ✅ exact** |
| **25.8** | **0.3681 ← PEAK** | −175.0° | |
| 28 | 0.3668 | −179.6° | |
| 35 | 0.3509 | +168.7° | |

**Two hard, falsifiable predictions fall out, and neither needs new telemetry:**

1. ★★★ **BAND RATIO.** `|d|(21 Hz) / |d|(7.79 Hz) = **1.836**`, fixed by the two filter constants alone.
   **M1 must produce a symptom that is ~1.8× stronger at 21 Hz than at 7.79 Hz, and maximal at 25.8 Hz.**
   🛑 **This is a structural embarrassment for M1 as the cause of the 6–9 Hz complaint.** M1's residue
   *peaks in the 18–28 Hz band* and is at less than 55 % of peak at 7.79 Hz. If the operator's primary
   symptom is in the 6–9 Hz band, M1 is fighting its own transfer function to explain it.
   **BELIEF: M1 is the better candidate for 18–28 Hz; M2 is the better candidate for 6–9 Hz.** The two
   mechanisms may both be real and may own different bands. That would explain why no single lever has
   ever fixed both.
2. ★★★ **PHASE.** The residue's phase relative to the arbitrated overlay command is **deterministic and
   computable** — **−120.3° at 7.79 Hz**, **−163.7° at 21 Hz**. M2 has no reason to produce that phase.
   This is the cleanest single discriminator available and it is measurable from data you already have.

### A.0.3 🛑 CORRECTION TO MY OWN REMEDY #1 — production damping schedules mostly go the WRONG WAY

I built remedy #1 on US6122579A and over-generalised. Digging into the full patent text and two more
patents, the mainstream production schedule is **the opposite of what I implied**:

| Patent | Schedule direction | Stated reason |
|---|---|---|
| **US6122579A** (Delphi, 1999) | damping gain **INCREASES** with current magnitude | *"more damping compensation is desired at high torque"* |
| **US6768283B2** (Mitsubishi Electric, prio 2001-09-04) | damping gain **INCREASED when reaction torque is SMALL, DECREASED when LARGE** | *"prevent the steering from becoming heavier than needed even when the steering wheel is steered fast"* |
| **US7523806B2** (Delphi/SSIH, prio 2005-09-20) | a handwheel-torque-dependent scaling factor that **REDUCES damping at high torques** | reduce "sticky" on-center feel |

**Two of three reduce damping as torque rises.** My §7.2 presented magnitude-increasing damping as
established practice; **it is not — it is the minority case, specific to torque-ripple damping.**

🛑 **This is directly actionable for the agent hunting a torque-indexed damping axis: if one is found,
CHECK ITS SLOPE BEFORE ASSUMING ANYTHING.** If Honda followed the majority practice, the shipped schedule
**reduces damping exactly when the load-dependent friction excitation is largest** — which would be an
active contributor to the symptom, and flattening or inverting that slope becomes a *calibration* fix
rather than a new lever. **BELIEF, but a cheap and high-value thing to check.**

---

## A.1 — Q1: HOW TO TELL M1 FROM M2 WITH 100 Hz SIGNALS

**Short answer: YES, they are separable from the outside — by at least three independent tests, two of
which need no new telemetry at all.** I am not returning "not separable."

### A.1.1 ★★★ TEST 1 — The M1 phase test (no new telemetry, uses existing caches)

**What:** cross-spectrum between the **arbitrated overlay command** and the **column torque ring**, at
7.79 Hz and at 21 Hz.

**Predictions:**
- **M1:** phase = **−120.3° ± (plant phase)** at 7.79 Hz and **−163.7° ± (same)** at 21 Hz. Critically,
  the *difference between the two bands is fixed at 43.4°* and is independent of the plant, because the
  plant transfer function is common to both mechanisms. **⇒ Test the band-to-band phase DIFFERENCE, not
  the absolute phase.** That cancels everything you do not know.
- **M2:** no reason to produce −43.4° of band-to-band phase difference; friction excitation is
  in-phase-with-velocity (i.e. ~−90° relative to displacement) at *both* frequencies, so the predicted
  band-to-band difference is **≈ 0°**.

🛑 **This is the highest-value test in this appendix: a 43.4° vs 0° discrimination, fully computed, using
signals already in the caches.** Beware the kit's own recorded trap — `accord-raw14-offbyone-in-every-cache`
— a one-sample pairing error is **28° at 7.79 Hz** and would corrupt exactly this measurement. Use the
safe pairs `(t, probe)` or `(raw14_t, raw14_b4)`.

### A.1.2 ★★★ TEST 2 — The band-ratio test (no new telemetry)

M1's `|d|(21)/|d|(7.79) = 1.836` is fixed by the filter constants. Measure the ratio of the two bands'
response, normalised by the command magnitude in each band.
- **M1 alone:** ratio ≈ 1.836 × (plant response ratio).
- **M2 alone:** ratio set by the two modes' Q and the friction coupling — no reason to hit 1.836.
- **Both:** the 6–9 Hz band should show a *magnitude-proportional excess* over what M1's 0.196 can explain.

### A.1.3 ★★★ TEST 3 — Q-versus-load (reuses the ONE estimator the kit already trusts)

This is the mechanistically sharpest test, and it exploits the difference between **a disturbance injected
into a fixed plant** and **a change to the plant's own damping**.

```
M1:  linear filter mismatch  ⇒  injects a DRIVE into an UNCHANGED plant
        response amplitude ∝ command magnitude
        ζ (and Q) INVARIANT with command magnitude          ◄── superposition

M2:  friction acts ON the plant, with a negative friction-velocity slope
        ζ_eff = ζ_structural − ζ_friction(load)
        load ↑  ⇒  ζ_friction ↑  ⇒  ζ_eff ↓  ⇒  Q RISES WITH COMMAND MAGNITUDE
        response amplitude grows FASTER than linearly, and diverges as ζ_eff → 0
```

**EVIDENCE for the negative-damping formulation:** Brockley & Ko (A.0.1) — the vibration exists only where
the friction-velocity curve has the right (negative-gradient) shape, and *"suitable damping will quench
the vibration entirely."* Also *Friction-Induced Vibration by Stribeck's Law*, Tribology Letters
<https://link.springer.com/article/10.1007/s11249-012-0100-z>, and the mode-coupling/NFVS literature
<https://www.researchgate.net/publication/229639024_Effects_of_damping_on_mode-coupling_instability_in_friction_induced_oscillations>.

**Protocol:** bin existing **ring-down events by the LKAS command magnitude in the second before the
ring-down**, and fit ζ per bin.
- **M1 ⇒ ζ flat across bins.**
- **M2 ⇒ ζ falls monotonically with command magnitude.**

★ **This reuses the ring-down estimator, which is the only estimator in the kit's record that passed its
own control** (`feedback-run-the-control-before-the-measurement`). That makes it the most trustworthy
instrument available, and it is being asked a question it is well suited to.

### A.1.4 ★★ TEST 4 — Hysteresis-loop width vs command magnitude

**What:** plot column torque against steering angle over slow, large reversals; measure the **width** of
the hysteresis loop (the vertical gap between the two branches).

- **M2 ⇒ loop width grows with command magnitude.** Coulomb friction produces a parallelogram loop whose
  width is `2 × T_friction`, and `T_friction ∝ F_n ∝ T_transmitted` (§6.4,
  `F_n,T = T_wh·√(1+tan²γ+tan²α)/R_p`, MS 9:201). **A load-proportional friction MUST show a
  load-proportional hysteresis width.** This is nearly a direct measurement of the mechanism.
- **M1 ⇒ no systematic width change** — a linear filter residue adds no hysteresis.

**EVIDENCE that this is a real and sizeable quantity in EPS:** total steering hysteresis from sensor,
torsion bar, bearings and misalignment is *"0.5 Nm or larger"* (US6817439), which is well above the noise
floor of a 100 Hz column-torque channel.

🛑 **Confound to control:** the base assist itself creates apparent hysteresis via the boost curve. Run the
comparison at **matched steering angle and matched vehicle speed**, and use **engaged-vs-manual at matched
driver torque** as the contrast, not raw engaged loops.

### A.1.5 ★★ TEST 5 — Dwell-time dependence at reversals

**EVIDENCE.** Rate-and-state friction (Dieterich 1978/79; Ruina 1983) — static friction grows
logarithmically with the time of stationary contact ("frictional aging"/"log time healing"). Reviews:
<https://academic.oup.com/gji/article/240/3/1855/7943683> and
<https://arxiv.org/pdf/2402.04478>; incorporation into the LuGre model for mechanical systems:
<https://www.sciencedirect.com/science/article/abs/pii/S0957415820300258>.

**Protocol:** bin the first post-reversal torque excursion by **time since the previous velocity
zero-crossing**.
- **Stick-slip M2 ⇒ excursion grows with dwell (log-time healing).**
- **Quasi-harmonic M2 ⇒ NO dwell effect** (it never sticks).
- **M1 ⇒ no dwell effect.**

🛑 **Note carefully what this test can and cannot do.** Given A.0.1, quasi-harmonic FIV and M1 give the
**same** (null) answer here. **This test does not separate M1 from M2 — it separates the two branches
WITHIN M2.** Useful for confirming the quasi-harmonic reading, useless as an M1/M2 discriminator. I flag
this because it is the test most likely to be mistaken for a discriminator.

### A.1.6 ★ TEST 6 — The hands-off protocol (developing my §3.2 prediction, as asked)

**The prediction.** From §3.2, the quasi-static coupling gain is
`G_0 = −k_eq/(k_r + k_eq)` with `k_eq = k_tb·k_d/(k_tb + k_d)`. With **no hands, `k_d = 0 ⇒ k_eq = 0 ⇒
G_0 = 0`** — the entire quasi-static sensor-contamination path vanishes.

**What each mechanism predicts for the same protocol:**

| | Hands **firmly on** | Hands **fully off** |
|---|---|---|
| **§0.2-mech-1** (quasi-static grip coupling) | present, magnitude-proportional | **VANISHES** |
| **M1** (filter residue) | present | **UNCHANGED** — it is inside the ECU and never touches the driver |
| **M2** (worm-mesh friction) | present; grip adds damping ⇒ **lower Q, but excitation unchanged** | **excitation UNCHANGED**, Q **rises** (hand damping removed) ⇒ **ring gets BIGGER** |

★ **The signature is sharp and the three mechanisms fully separate:** hands-off should make the ring
**disappear** under mechanism 1, be **unchanged** under M1, and get **larger** under M2.

**Concrete drive protocol:**
- **Route:** divided highway, constant radius or straight, **90–110 km/h**, smooth surface, low crosswind.
- **Cells:** {hands firmly on, fingertips, hands off} × {low, high LKAS command magnitude}. Induce the
  command-magnitude contrast by lane-position offset, not by changing firmware.
- **Exposure:** `accord-leverb-discriminator-underpowered` establishes the binding constraint is exposure
  and that closing a comparable question needs **~4× the episode blocks**. Budget **≥25 clean episode
  blocks per cell**, i.e. **≥150 blocks total**, bootstrapped **over EPISODES, not windows**
  (`feedback-episodes-not-windows`). Get a **split-half null first**.
- 🛑 **Safety and validity:** hands-off on a public road conflicts with the driver-monitoring system and
  with safe practice. **This cell must be either (a) very brief, supervised, on a closed course, or
  (b) approximated by "fingertips only" as the lightest grip cell.** I am flagging this rather than
  designing around it — it is the operator's call, and the fingertip approximation weakens but does not
  destroy the test, because `k_d` still drops by a large factor.
- **Covariates to log per block:** speed, wheel rate, command magnitude, steering angle, grip proxy.
  Match speed distributions per band (`accord-averaged-spectrum-needs-matched-speed-distributions`).

### A.1.7 What to spend the five spare telemetry bits on

**BELIEF, but strongly held: spend them on the M1 residue itself, not on anything else.**

```
bit 4  : SIGN of the residue (H_A − H_B) applied to the overlay, sampled at 100 Hz
bits 3-0: coarse magnitude of |residue| (4-bit, log or comparator ladder)
```

**Why the sign bit is the whole game:** a 1-bit sign channel at 100 Hz is sufficient to recover **phase**
by cross-spectrum against the column torque — the kit has already proven this pattern works
(`accord-v88-lever-b-restored`, b7 = SIGN @ 100 Hz; and V87's probe fired). With the sign bit you get a
**direct** measurement of the residue's phase, which A.1.1 shows is the sharpest discriminator. Without
it you are inferring the residue from the command, which requires trusting my filter reconstruction.

🛑 **Heed the kit's own two probe lessons:** size the rung against **the lane's own reachable output**, not
a downstream gate's width (`feedback-size-probe-rungs-against-lane-reachable-output`, V69 wasted three
rungs); and **probe the gate and the input, not just the output**
(`feedback-probe-the-gate-not-just-the-output`, V64's null was on the gate). Here that means: confirm the
residue is non-zero *at all* before spending four bits resolving its magnitude — the residue is a
**difference of two nearly-equal numbers**, and if it is being computed in a narrow integer type it may
be quantised to zero at small command magnitudes. **A positive control is mandatory.**

### A.1.8 Discriminator summary

| Test | New telemetry? | M1 predicts | M2 predicts | Power |
|---|---|---|---|---|
| **1. Band-to-band PHASE difference (7.79 vs 21 Hz)** | No | **−43.4°** | **≈ 0°** | ★★★ |
| **2. Band ratio 21/7.79** | No | **1.836 ×** plant ratio | unrelated to 1.836 | ★★★ |
| **3. ζ (Q) vs command magnitude** | No | **flat** | **falls with load** | ★★★ |
| **4. Hysteresis-loop width vs command** | No | **flat** | **grows ∝ command** | ★★ |
| **5. Dwell-time at reversals** | No | null | null (quasi-harmonic) / positive (stick-slip) | ★ — separates M2's branches only, **NOT M1/M2** |
| **6. Hands-off / grip ladder** | No | **unchanged** | **ring grows** | ★★ (safety-constrained) |
| **7. Residue sign bit @100 Hz** | **Yes, 1 bit** | direct phase measurement | — | ★★★ (confirmatory) |

**Verdict on Q1: separable, by tests 1, 2 and 3 alone, using data already on disk.** I would run those
three before spending a build on telemetry — and note that tests 1–3 are *analysis of existing caches*,
so the exposure constraint that blocks test 6 does not apply to them.

---

## A.2 — Q2: SIZING THE MAGNITUDE-SCHEDULED DAMPING REMEDY

### A.2.1 US6122579A in full (Delphi, priority 1999-05-28)

<https://patents.google.com/patent/US6122579>

- **`I_MAG`** — *"signal I_DAMPED, which approximates the actual motor current, and thus torque, is
  separated into its magnitude (IMAG) and direction (IDIR)."* ⇒ **magnitude of the estimated actual motor
  current**, not a commanded value, not a voltage.
- **Formula** — verbatim construction: *"Signal IMAG … is provided as a positive input to a summer 90.
  Summer 90 also receives, as a negative input, a predetermined constant gain offset GOFFSET. The output
  of summer 90 is provided to a positive limit block 92 … The output of positive limit block 92 is
  provided to multiplier 94, in which it is multiplied by a predetermined gain constant K_G."*
  ⇒ **`GAIN = max(0, K_G · (I_MAG − G_OFFSET))`**. 🛑 **No numerical values for `K_G` or `G_OFFSET` are
  given in the patent** — I will not invent them.
- **What GAIN multiplies** — 🛑 **correction to my §7.1/§7.2 framing:** it multiplies the **differentiated
  estimated motor voltage**, not motor velocity. *"The differentiated estimated voltage signal from
  differentiator 74 is then limited in limiter 75 and scaled by a gain factor in multiplier 76."* Since
  estimated voltage ≈ back-EMF ∝ motor velocity, the differentiated signal is **≈ motor acceleration**.
  **This is therefore a torque-ripple damper closer in form to a scheduled inertia compensation than to a
  classical viscous damper.** The transferable principle — *schedule the compensation gain on torque
  magnitude* — survives; the literal signal does not. I over-claimed in §7.2 and am correcting it here.
- **Filters** — a differentiator (*"eliminates the DC components … highly influenced by the voltage spikes
  which are associated with torque ripple"*) then a low-pass (*"provides anti-aliasing … and reduces high
  frequency noise"*). **No cutoff values given.**
- **`G_OFFSET`'s purpose** — 🛑 **not what you suspected, but your instinct about the trap is still right.**
  Verbatim: *"The reason for the offset is that, in many systems, the relationship will be invalid at low
  currents, due to specifics in the operation of the PWM current control. The offset assures that the
  damping correction is applied only at high currents."* So the stated reason is **current-estimate
  validity**, not step-avoidance. **However**, the `max(0, ·)` construction means the gain **ramps
  continuously from zero** at `I_MAG = G_OFFSET` — there is **no step at the breakpoint**. That
  ramp-from-zero property is exactly the anti-V80 shape you were looking for; it is a *consequence* of the
  design rather than its stated motive.
- **Sign** — *"Summer 62 also receives, on a negative input, the output of an EPS damper 64."*
  ⇒ **the damping correction is SUBTRACTED from the commanded torque.**
- **Frequency range** — none stated for the damper. The only frequency in the patent is context: *"a
  notch … at about 10 Hz, the resonant frequency of particularly important parts of the steering system"*,
  which describes the pre-existing compensator, **not** the damper.

### A.2.2 Other magnitude/assist-scheduled damping and friction schedules

| Source | Scheduled on | Direction | Signal damped |
|---|---|---|---|
| **US6122579A** Delphi, prio 1999-05-28 | motor current magnitude | **↑ with torque** | differentiated estimated voltage |
| **US6768283B2** Mitsubishi Electric, prio 2001-09-04 <https://patents.google.com/patent/US6768283B2/en> | steering shaft reaction torque | **↓ with torque** | **motor speed** (true viscous damping) |
| **US7523806B2** Delphi/SSIH, prio 2005-09-20 <https://patents.google.com/patent/US7523806> | vehicle speed × handwheel velocity × **handwheel torque** | **↓ with torque** | handwheel/motor velocity |
| **US20130066520A1** SSIH, prio 2011-09-09 | **base assist command** + vehicle speed | (FDD coefficient) | 2nd-order filtered velocity |
| **Li 2016** MPE 8470786 / SAE 2016-01-1542 | **EPS assist gain** | **↑ with assist gain** | friction compensation current |

**US6768283B2 gives a genuinely useful damping-design formula (EVIDENCE, verbatim relations):**
```
ζ      = K_damp / (2·√(K_tire · J'))
K_damp = 2·ζ·√(K_tire · J')            with  ω_n = √(K_tire/J'),  J' = J_m − K_iner
```
and *"the motor speed is multiplied by the damping F/B gain found in step S6 to find a damping
compensation current."* Its schedule is *"increased when the steering shaft reaction torque is small and
decreased when the steering shaft reaction torque is large"*, to *"prevent the steering from becoming
heavier than needed even when the steering wheel is steered fast."*

**US7523806B2 supplies the anti-V80 shape explicitly (EVIDENCE):** the velocity scaling factor is
*"zero or near zero at zero motor velocity, and monotonically increasing as motor velocity increases."*
🛑 **That is the published way to avoid a step at zero — ramp the SCALING FACTOR from zero, do not lift
the table's `Y[0]` off zero.** It is precisely the distinction the V80 result turned on.

### A.2.3 ★★★ THE SIZING ANSWER

**The algebra.** For a lightly damped mode, peak amplification `Q = 1/(2ζ)`. To **halve the peak** you must
**double the damping ratio**: `ζ' = 2ζ`, i.e. `Δζ = ζ`. The added viscous coefficient is

```
c_add = 2·Δζ·√(k·J) = 2·ζ·J·ω_n = 2·ζ·k/ω_n
```

Evaluate the added damper's torque at the resonant response amplitude `A` (modal coordinate), where the
response is at frequency `ω_n`:

```
T_damp = c_add · (ω_n · A) = 2·ζ·k·A
```

The modal **spring** torque at that same amplitude — which is what the torsion bar carries and what the
ring "is" — is `T_spring = k·A`. Therefore

```
    T_damp        2·ζ·k·A         1
  ──────────  =  ──────────  =  2ζ = ───          ◄──  THE RESULT
   T_spring         k·A             Q
```

★ **To halve the resonant peak, the added damper must produce, at the ring amplitude, a torque equal to
`1/Q` of the ring's own amplitude.**

| Q | ζ | Added damping torque needed, as a fraction of the ring amplitude |
|---|---|---|
| 14 | 0.036 | **7.1 %** |
| 20 | 0.025 | 5.0 % |
| 29 | 0.017 | **3.4 %** |

**Now the feasibility bound — and it is a HARD bound, not an estimate.** Both the ring and the damper
output live at the same aggregator node, so no referral factor is needed. The ring amplitude at that node
cannot exceed the clamp, `R ≤ 10240`. Hence:

```
  needed_damper_counts  =  R / Q  ≤  10240 / 14  =  731 counts        (worst case, Q = 14)
                                  ≤  10240 / 29  =  353 counts        (Q = 29)

  damping-lane zero-reject window                =  ±2048 counts
  aggregator clamp                               =  ±10240 counts
```

🛑 **731 < 2048. The authority requirement CANNOT exceed the damping lane's window — it is arithmetically
impossible, because the ring itself must fit inside the ±10240 clamp.** Even at the most pessimistic Q and
with the ring pinned at the clamp, halving the peak costs **at most ~7.1 % of full authority**, and for a
realistic ring of a few hundred counts it costs **a few tens of counts**.

**⇒ ANSWER TO YOUR SIZING QUESTION: the remedy does NOT die on sizing. This is the opposite of how the
rate-indexed damper died.** The rate-indexed damper died because a *product of two dead zones* was
identically zero over the entire micro regime — an **availability** failure. Here, availability is the
only question; the **magnitude** required is comfortably inside budget.

🛑 **The binding constraint is therefore DEADBAND and RESOLUTION, not authority — and which one depends on
a fact I do not have:**
- If the **±2048 zero-reject window is on the damper's OUTPUT**, it swallows the entire required
  correction (which is ~10²–10³ counts). **The remedy is dead as-implemented** and needs the window
  narrowed or bypassed.
- If the window is on the damper's **INPUT** (e.g. a rate signal), then the question is whether an 8 Hz
  ring clears it. **BELIEF, worth checking:** a ±0.5° ring at 7.79 Hz has a peak rate of
  `2π·7.79·0.5 ≈ 24.5 °/s`, which comfortably clears a 12.7 °/s rate dead zone — so the *rate* gate may
  well be open during the symptom even though `accord-damper-cannot-reach-micro-regime` shows the
  **speed** gate (FactorC, 35 km/h) is what actually zeroes the product.
- **Quantisation:** at a few tens of counts the correction is well above a 1-count LSB, so resolution
  is not the limiter. Good.

### A.2.4 The M2 caveat that raises the requirement

If the mechanism is quasi-harmonic FIV (A.0.1), the sizing target is **not** "halve a passive peak" but
**overcome a negative damping term**:

```
ζ_eff(load) = ζ_structural − ζ_friction(load)
```

The measured `ζ = 0.017–0.036` is `ζ_eff` **at the ring-down condition**, which is presumably a low-load,
post-disengagement state. At high command magnitude `ζ_eff` is **lower** than that, so the required
`c_add` is **larger** than the table above and is **load-dependent**.

★ **This is the physics that makes a magnitude-scheduled damping gain the right shape rather than merely a
convenient one** — you need more damping exactly where the negative-damping term is biggest. And
Brockley & Ko give the encouraging half: *"the introduction of suitable damping will quench the vibration
entirely."* A quasi-harmonic FIV does not need to be out-muscled; it needs its instability condition
broken, after which the oscillation **ceases** rather than merely shrinking.

🛑 **Corollary, and it matters for how you read a flight result:** under M2 the response to added damping
is **threshold-like, not proportional**. A dose that is slightly too small does **nothing visible**; a dose
just past the threshold **removes the symptom**. **Do not read a small-dose null as "the lever is
falsified"** — that inference is valid for a linear mechanism and invalid for this one. Given the kit's
history of dose ladders, this is the single most important caveat in A.2.

---

## A.3 — Q3: THE HONDA `Lu` CONVERSION, IN DETAIL

Re-read of US11685438B2 targeting `Lu` specifically. **The honest headline: the patent is deliberately
vague about `Lu`, and I could not extract a gain, units, or a schedule — because they are not disclosed.**

### A.3.1 What the patent DOES say (EVIDENCE, verbatim)

- **The conversion:** *"The LKAS instruction signal Li is input to a conversion unit U 203, and is
  converted to a torque Lu to be exerted on the steering shaft 19."*
- **Its form:** *"the conversion unit U 203 may be a unit that performs mapping for converting the value
  of the LKAS instruction signal Li to a torque, for example."*
  ⇒ **a MAP (table), not a formula.** "may be … for example" is deliberate claim-broadening language.
- **Filter X cutoff:** *"upper limit of the pass frequency is about **5 Hz**"*, chosen to detect torque
  including offset and noise, and *"can also be experimentally determined so as to pass the frequency of
  the change in steering torque due to steering wheel operation **or driving by the EPS motor**."*
- **Filter S cutoff:** *"about **1 Hz** or lower"*, for extracting the offset torque.
- **Sign:** as quoted in §1.1 — removal is by **addition**, because the two torques carry opposite signs.

### A.3.2 What the patent does NOT say — stated plainly

| Question | Answer |
|---|---|
| Exact conversion formula / gain value / units | **NOT DISCLOSED** |
| Fixed or scheduled (speed, angle, grip)? | **NOT DISCUSSED** — no scheduling is mentioned either way |
| Any filter on `Lu` itself | **NONE mentioned** — `Lu` goes straight to adder 204 |
| Conversion approximate or degrading at higher frequency? | **NOT DISCUSSED** |
| Vehicle platform / model / model year | **NOT NAMED** — only generic "automobiles" and "vehicles" |
| Does `Lu` appear in the claims? | **NO** — claims 1–7 reference *"a torque caused due to the steering assistance unit"* but do not recite the conversion unit |

🛑 **So I must retract half of the inference you were leaning on.** I cannot tell you that Honda's gain is
static, because Honda does not say. What I *can* say is narrower and still useful:

**The load-bearing fact survives: `Lu` is produced by a MAP from the instruction signal, with NO
differentiator and NO filter of its own, and it is summed with a signal band-limited to 5 Hz.**
- An inertial coupling would require `Lu ∝ d²(command)/dt²`. **There is no differentiator anywhere in this
  signal path.** ⇒ **Honda's engineers modelled the contamination as a memoryless function of command
  magnitude.** That still supports M2/quasi-static over an inertial mechanism — which was your question —
  and it does so without needing the gain to be a constant. A *map* is magnitude-dependent (possibly
  nonlinear), but it is **not rate-dependent**.
- **BELIEF:** a nonlinear map rather than a scalar is *mildly* more consistent with a friction-like
  coupling (which saturates) than with a pure linear impedance divider, but this is weak and I would not
  build on it.

### A.3.3 Bandwidth implication for any correction here

**EVIDENCE:** the correction's usable band is set by filter X at **≈5 Hz**.
**BELIEF:** ⇒ **Honda's corrector would be substantially attenuated across the operator's entire 6–9 Hz
band and effectively absent at 18–28 Hz.** If this kit ever implements a feed-forward canceller, copying
Honda's 5 Hz corner would place the correction **below the primary symptom band** and it would do very
little. Any correction aimed at 6–9 Hz needs a corner of **≥20 Hz**, which is a materially harder filter to
justify — a wider corner passes more sensor noise into the assist path and eats the phase margin that §4
shows is already thin. **This is an argument against R3 (feed-forward cancellation) that I did not have in
the main report, and it reinforces the §7.4 recommendation not to spend a cave on it.**

### A.3.4 On the 2020 priority date

**EVIDENCE:** Honda Motor Co Ltd; inventors Atsuhiro Eguchi, Shuichi Kosaka, Ryo Kawaguchi; priority
**13 March 2020**. **The patent names no platform or model year.**

**BELIEF, and I want to be careful not to oversell this:** a 2020-priority Honda filing on LKAS torque
contamination is *consistent* with the 2020 Accord's EPS generation, and the physics it describes must
apply to any column EPS with an LKAS overlay. But a priority date is **not** evidence that this ECU
contains this algorithm — the filing could equally postdate the car, target a later platform, or describe
an approach Honda never shipped. 🛑 **Do not treat US11685438B2 as documentation of `39990-TVA-A160`.**
It is EVIDENCE about the *phenomenon* and about *Honda's model of it*; it is **BELIEF at best** about this
firmware's contents.

---

## A.4 — Revised bottom line

1. **M1 and M2 are both alive, and they probably own different bands.** M1's residue peaks at **25.8 Hz**
   and is only 0.196 at 7.79 Hz, with a fixed 21/7.79 ratio of **1.836** — it is a natural explanation for
   **18–28 Hz** and a strained one for **6–9 Hz**. M2 (quasi-harmonic FIV at the wheel-on-torsion-bar mode)
   fits 6–9 Hz. **BELIEF: this two-band split is why no single lever has fixed both.**
2. **The kit's "not a relay" evidence is positive evidence for the quasi-harmonic branch of M2**, not
   evidence against M2. All four null results are exactly what Brockley–Ko predict.
3. **Three discriminators are available from data already on disk** — band-to-band phase (−43.4° vs 0°),
   band ratio (1.836), and ζ-vs-load (flat vs falling). **Run these before spending a build.**
4. **The damping remedy does not die on sizing** — halving the peak costs at most `R/Q ≤ 731` counts
   against a ±2048 window, a hard bound. It lives or dies on **where the zero-reject window sits**.
5. 🛑 **Check the SLOPE of any torque-indexed damping axis you find.** Two of three production patents
   schedule damping **downward** with torque. If Honda did the same, the shipped calibration is actively
   working against a load-dependent-friction instability, and flattening it is a *calibration* fix.
6. 🛑 **Under M2 the response to damping is threshold-like.** A small-dose null does **not** falsify the
   lever.

## A.5 — Citations added in this appendix

| # | Source | Used in |
|---|---|---|
| 38 | **Brockley & Ko**, *Quasi-Harmonic Friction-Induced Vibration*, ASME J. Lubrication Technology **92(4):550–556, 1970** <https://asmedigitalcollection.asme.org/tribology/article/92/4/550/429814/Quasi-Harmonic-Friction-Induced-Vibration> | A.0.1, A.1.3, A.2.4 ★★★ |
| 39 | *A new approach of stick-slip based on quasi-harmonic tangential oscillations*, **Wear** <https://www.sciencedirect.com/science/article/abs/pii/S0043164897002962> | A.0.1 |
| 40 | **US6768283B2** — Mitsubishi Electric, *EPS control device*, prio 2001-09-04 <https://patents.google.com/patent/US6768283B2/en> | A.0.3, A.2.2 |
| 41 | **US7523806B2** — Delphi/SSIH, *Improved active damping of steering systems*, prio 2005-09-20 <https://patents.google.com/patent/US7523806> | A.0.3, A.2.2 |
| 42 | *Effects of damping on mode-coupling instability in friction induced oscillations* <https://www.researchgate.net/publication/229639024_Effects_of_damping_on_mode-coupling_instability_in_friction_induced_oscillations> | A.1.3 |
| 43 | *Reconciling aging and slip state evolutions… rate-and-state friction*, **Geophys. J. Int. 240(3):1855** <https://academic.oup.com/gji/article/240/3/1855/7943683> · preprint <https://arxiv.org/pdf/2402.04478> | A.1.5 |
| 44 | *Inclusion of the dwell time effect in the LuGre friction model* <https://www.sciencedirect.com/science/article/abs/pii/S0957415820300258> | A.1.5 |
| 45 | *The Influence of Vibration on Friction: A Contact-Mechanical Perspective*, **Frontiers in Mech. Eng.** (OA) <https://www.frontiersin.org/journals/mechanical-engineering/articles/10.3389/fmech.2020.00069/full> | A.0.1 |
| 46 | *Friction-induced stick-slip vibration and its experimental validation*, **MSSP** <https://www.sciencedirect.com/science/article/abs/pii/S0888327020300911> | A.0.1 |

**Running total: 46 sources.**

## A.6 — Reproducibility and honesty notes

- The M1 computation is my own, from your two filter constants. Script:
  `…/scratchpad/m1_final.py`. **The 1 kHz sample rate was INFERRED by fitting to your three reported
  values, not told to me** — it reproduces 0.196 at 7.79 Hz and 0.360 at 21 Hz exactly, and no 100 Hz
  variant comes close. 🛑 **If the true rate is not 1 kHz, every number in A.0.2 changes** — please
  confirm the rate before acting on the phase prediction.
- **Paywalled / blocked in this round, used only via abstracts and flagged at point of use:** Brockley &
  Ko 1970 (ASME, abstract only — the three quoted phrases are from the published abstract); the Wear
  quasi-harmonic paper (403); the UBC Ko thesis (access-blocked); the Leine et al. PDF (not
  text-extractable). **No numerical parameter in this appendix comes from any of them** — they are cited
  for the qualitative stick-slip/quasi-harmonic distinction only, which is corroborated across four
  independent sources.
- **US6122579A, US6768283B2, US7523806B2 and US11685438B2 were all read directly**, and every quoted
  string in A.2.1, A.2.2 and A.3.1 is from the patent text.
- 🛑 **A.2.3's hard bound depends on two kit-supplied numbers I cannot verify** (±10240 clamp, ±2048
  window) and on the assumption that the ring and the damper output share a node. If they do not share a
  node, a referral factor enters and the bound must be recomputed.
