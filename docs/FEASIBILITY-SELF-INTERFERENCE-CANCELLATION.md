# FEASIBILITY — LKAS SELF-INTERFERENCE CANCELLATION

**Written 2026-08-06 · agent `selfcancel` · standalone report, meant to be actionable cold.**
**Study/analysis only. Nothing was built, flashed, sent on CAN, or modified in openpilot.**

**The operator's question, verbatim:**

> *"is there a way we can cancel out the LKAS signal on the steering column? look into the openpilot
> lateral maneuvers capability, i think we can measure the transfer function from LKAS -> steering
> column (hands off), though I'm not sure honestly... maybe this self interference cancellation is only
> done at below highway speeds. maybe this isn't needed until we get to higher LKAS torque values like 8x."*

---

## 0. THE THREE VERDICTS

| | verdict | one-line reason |
|---|---|---|
| **(i) Measure the LKAS→column transfer with existing tools** | **NEEDS-X** | You already have it at 21 Hz (γ² = 0.917) from natural operation. openpilot's lateral-maneuver mode is a **sub-2 Hz** tool and cannot reach 6-9 or 18-22 Hz. The X is an **engagement-edge, event-triggered** estimate — not a spectral one. §1 |
| **(ii) Implement cancellation in firmware** | **NO-GO** | Necessarily a Q≈20 biquad cave whose own poles sit at **r = 0.9988** — ~17× more lightly damped than V48B's r = 0.979, which bricked the ECU. `f0` moves −14% with load while the mode's phase rotates 180° over a **5%** band ⇒ a mistuned term is delivered **inverted**. And the aggregator **zero-rejects**, so the term vanishes discontinuously exactly when it is most needed. §3 |
| **(iii) Is it needed before 8×?** | **NO — and the premise is inverted.** | The loop is already at \|L\| ≈ 1 **at today's authority**: grind #1 is an established limit cycle, and V74's flight confirms it is **still live at 2.72× over its own 24-28 Hz control floor**. LKAS gain does not appear in the loop gain. And **8× is unreachable without a clamp raise — V74 already delivers 4.27× stock and the clamp sits at 4.91×, i.e. 14.9% headroom left.** §4 |

**The single most important structural finding, and it reframes the question:**

> **The firmware contains no LKAS-to-assist feedback path at all.** No base-assist producer reads any
> LKAS-descended cell. The loop closes **mechanically**, outside the ECU. "Cancel the LKAS signal" is a
> solution to a problem this firmware does not have. §2.4 states the right frame.

---

## 1. Q1 — CAN WE MEASURE THE TRANSFER FUNCTION, HANDS-OFF?

### 1.1 What openpilot's lateral-maneuver capability actually is

**[EVIDENCE — comma.ai 0.11.1 release notes; `tools/lateral_maneuvers/generate_report.py`]**

A validation mode that commands prescribed **lateral-acceleration** profiles and logs the response, so
commanded-vs-measured exposes rate limits, delays and tuning error.

- **Enabling:** a **developer-settings toggle**, set before going onroad. Maneuvers then fire
  automatically once conditions are met.
- **Conditions:** straight, level road; constant speed held ≥ 2 s; **20 mph and 30 mph**.
- **Waveforms** — 3 maneuvers × 3 repeats each:
  - step right: `+0.5 m/s² × 1 s`, then `−0.5 m/s² × 1.5 s`
  - step left: mirror
  - **sine 0.5 Hz**, amplitude 1.0 m/s², 2 s period
- **Report:** upload rlogs to connect, then `tools/lateral_maneuvers/generate_report.py <route_id>`.

**Usable without modifying openpilot? YES.** It ships in the product and is armed from a settings
toggle — running it *uses* an existing capability rather than forking the controller, so it sits inside
`memory/feedback-no-openpilot-side-modifications.md`.
⚠ Flag for the operator's own call: the mode makes openpilot command steering on a public road. It is a
driving decision even though it is not a code change.

### 1.2 Why it cannot answer this question — two independent kills

**(a) Spectral content.** Exact Fourier magnitude of that step pair, relative to its own 0.2 Hz content:

| f | step-pair \|X\| | + LKAS lane pole (`gp-0x3d3c` = 0.96875 @1 kHz ⇒ **fc 5.05 Hz**) | net |
|---|---|---|---|
| 7.79 Hz (micro ratchet) | **−31.2 dB** | −5.3 dB | **≈ −37 dB** |
| 21.09 Hz (grind #1) | **−39.5 dB** | −12.6 dB | **≈ −52 dB** |

The 0.5 Hz sine is a pure tone — **literally zero energy** in either band. The closed-loop lateral
controller low-passes it further before it reaches `0xE4`.

**(b) Tyre-order collision — fatal on its own.** At the kit's measured circumference **C = 2.088 m**:

| speed | order 1 | order 2 | order 3 |
|---|---|---|---|
| **20 mph** = 8.94 m/s | 4.28 Hz | **8.56 Hz** ← in band | 12.85 Hz |
| **30 mph** = 13.41 m/s | **6.42 Hz** ← in band | 12.85 Hz | 19.27 Hz |

**Both mandated maneuver speeds put a tyre order directly inside the 6-9 Hz ratchet band.** Per
`memory/accord-averaged-spectrum-needs-matched-speed-distributions.md` this manufactures exactly the
kind of spurious line this kit has already retracted once. Even with adequate excitation the result
would be uninterpretable.

⇒ **Lateral maneuvers are a sub-2 Hz lateral-controller tuning tool. Correct instinct, wrong band.**

### 1.3 What you already have — and the trap inside it

**[EVIDENCE, on record]**
- `command → bar` transfer **peaks at 21.09 Hz — the global maximum — coherence 0.917**
  (`docs/STATE.md`).
- V55 measured the **reverse** leg (`memory/reference-accord-v55-flashed-oscillation-is-internal.md`):
  H1 = **0.192 @0.98 Hz → 0.216 @21.09 Hz**, phase +171° → −161°, i.e. ~28° of rotation across the whole
  band ⇒ **flat, inverted, ~4 ms-lagged, no low-pass**.

🛑 **The trap, and it is decision-bearing.** Both are measured on data the loop generated *itself*. In
closed loop with an internally generated oscillation, `H1 = P_uy/P_uu` estimates the **inverse of the
FEEDBACK path**, not the forward plant — and coherence is high *precisely because* the loop is closed.
openpilot's lane-following command is **not exogenous** to the EPS loop (the camera sees the car's own
yaw). ⇒ **γ² = 0.917 does not license calling 1/0.216 = 4.63 the plant gain.**

**The exogenous input you already have for free: ENGAGEMENT EDGES.** Traffic-driven, uncorrelated with
the loop's own noise, and a near-step in the LKAS command. Route `5a` produced 18 episodes in 120 s of
stop-and-go, and the V74 flight instruction already targets that traffic.

⇒ **Estimate an event-triggered impulse response over ≥ 40 edges. Do not run a spectral H1 on
continuous engaged data.**

### 1.4 Channels, true rates, Nyquist — stated plainly

| role | signal | message | rate |
|---|---|---|---|
| **u** | LKAS torque command | `0xE4` (sendcan **src1**, not can src0) | 100 Hz |
| **y** | torsion-bar torque | `0x18F` / 399 `STEER_TORQUE_SENSOR` | 100 Hz |
| y (alt) | steering angle | `0x156` | 100 Hz |
| ⚠ **not independent** | `STEER_ANGLE_RATE` | `0x18F`[2:4] / `0x14A`[2:4] | — |
| ❌ **not anchors** | `steeringTorqueEps`, raw `0x427` | — | always ≈ 0 |

`STEER_ANGLE_RATE` is a fixed Q15 scale of the motor/resolver electrical rate (`FUN_0003f776`), **not**
an independent angle sensor — so it cannot corroborate the bar.

**Nyquist = 50 Hz.** Three consequences, in severity order:

1. **Aliasing is real and unresolved at 21 Hz.** The ECU samples internally at 1 kHz and publishes at
   100 Hz **with no anti-alias filter** ⇒ every line has a `100 − f` twin. **6-9 Hz is safe** (twins at
   91-94 Hz, physically implausible). **21.09 Hz is NOT** — the **78.91 Hz** twin is on record as OPEN
   and this measurement cannot close it.
2. **Phase is recoverable — but only off the index lattice.** CAN frames are timestamped per log
   *packet*, so timestamps wander **7.5-10.3 ms** from the grid = **75.6° of apparent phase jitter at
   21 Hz**. Reconstruct with `t[0] + i/fs`, `fs = (n−1)/(t[-1]−t[0])`. Never `1/median(dt)` (reads
   100.76 Hz on a grid that is 100.000 Hz to 2e-5).
3. **Trustworthy bands: DC-40 Hz magnitude, DC-25 Hz phase.** Both symptom bands are inside that; the
   28 Hz lane-change transient is at the edge; ≥ 50 Hz is out of reach
   (`memory/accord-both-instruments-blind-above-50hz.md`).

### 1.5 The coherence bar — stated in advance, so it cannot drift

Bendat-Piersol: relative sd of |H| = `√((1−γ²)/(2Kγ²))`. At **K = 10** independent (non-overlapping,
non-spliced) episodes:

| γ² | 95% CI on \|H\| |
|---|---|
| **0.072** ← *the estimate this kit correctly refused* | **±157%** |
| 0.30 | ±67% |
| 0.50 | ±44% |
| **0.80** | **±22%** |
| 0.917 | ±13% |

Significance floor (α = 0.05, `γ²_crit = 1 − 0.05^(1/(K−1))`): **0.527** (K=5) · **0.312** (K=9, matching
the kit's own recorded figure) · **0.283** (K=10) · 0.146 (K=20).

> 📋 **PRE-REGISTERED: a decision-bearing transfer claim needs γ² ≥ 0.8 over K ≥ 10 non-overlapping
> EPISODES. Refuse below 0.5.** Bootstrap over episodes, never windows
> (`memory/feedback-episodes-not-windows-and-the-noise-floor.md`). The 0.072 refusal was correct; this
> bar is set so it cannot recur.

---

## 2. Q2 — IS THERE A REAL SELF-INTERFERENCE MECHANISM?

### 2.1 The firmware answer, plainly: **NO — the path does not exist in firmware**

**[EVIDENCE — method given so the crux is checkable.]** Byte-scanned
`../accord-firmwares/analysis-2020accord/stock_fw_dump/code.bin` for the gp-relative displacement
halfwords of **every** LKAS-descended cell — `gp-0x69ae` (setpoint), `gp-0x6b3c` (arb command),
`gp-0x6b4c` (LKAS lane), `gp-0x6afe` (gated), `gp-0x6b94` (demand) — both parities, then confirmed every
hit on an instruction boundary by decompiling the containing function.

> **No base-assist producer reads any LKAS-descended cell.**
> Not `FUN_00034a72` (boost) · not `FUN_00034350` (damping) · not `FUN_00036c12` (friction comp) · not
> `FUN_000352b4` (friction magnitude) · not `FUN_0003a382` (residual) · not `FUN_00036388`
> (return-to-centre) · not `FUN_00036682` (filtered Sensor-B).
>
> The one candidate that looked live — `0x34904` inside `FUN_000348e0` — is a **pointer-array constant,
> not a load.** Decompile confirms.

⇒ The firmware has **exactly one summing junction** (the aggregator `FUN_0003aa2c`) and **no
compensation, decoupling or cancellation term anywhere.** Nothing in the ECU knows the LKAS command is
contaminating the torque sensor.

### 2.2 What DOES exist — and its measured gain

The **base-assist** leg is real, and it is the thing that would re-amplify anything appearing on the bar:

```
LKAS cmd → aggregator → governor → shaper → FOC → motor torque at pinion 2
   → rack → back-drives the input pinion → TORSION BAR TWISTS
   → 3-coil sensor (FUN_00041eec voter → gp-0x6a62)
   → boost curve FUN_00034a72 → gp-0x6bbe → SAME aggregator          [loop closed]
```

**Gain of the `bar → command` leg, measured on-car [EVIDENCE, V55]: 0.216 counts per count, FLAT from
1 Hz to 21 Hz, inverted, ~4 ms lag.**

🛑 **But this is NOT an LKAS self-interference path.** It is the **base-assist loop**, present
identically with LKAS off. LKAS is a **disturbance injected into** that loop, not a participant in it.
The firmware cannot distinguish LKAS-induced bar torque from driver-induced bar torque, because **it
never sees the LKAS command on that side of the loop at all.**

**The coupling into the bar is inertial ⇒ it rises as ω².** Hands-off at DC the wheel is not
accelerating, so the bar carries only upper-column friction ⇒ **DC gain ≈ 0**; the term scales as
`J_wheel · θ̈`. Normalised at f₀ = 8.4 Hz:

| f | \|T_bar / T_motor\| ∝ (f/f₀)² |
|---|---|
| 0.5 Hz *(the maneuver band)* | **−49 dB** |
| 2 Hz | −24.9 dB |
| 7.79 Hz *(ratchet)* | −1.3 dB |
| 21.09 Hz | **+16 dB** |

⇒ **Independent confirmation of §1.2:** the lateral maneuvers would characterise the band where the
effect is **~300× smaller** than where it matters. Two unrelated arguments, same conclusion.

**★ And the mode identity falls out of the same arithmetic.** `J_wheel` 0.035-0.055 kg·m² on a torsion
bar of 100-180 Nm/rad gives **f₀ = 6.8-11.4 Hz**, bracketing the measured **7.79 Hz** ratchet and its
**9.0 → 7.7 Hz** fall under load. `docs/STATE.md` already names it — *"the driver's hands damp the very
mass that resonates (wheel inertia on the torsion bar)."*
**[BELIEF** — J and k are not measured on this car. A plausibility bracket, not a fit. Worth one bench
measurement if the ratchet becomes the headline again.**]**

### 2.3 Distinguishing (a), (b), (c) — they are not three things

- **(a) plant resonance** — one lightly-damped mode, Q ≈ 14, ring-down 4.4 cycles, no trigger in any
  recorded channel, `f0` **falls** 9.0 → 7.7 Hz with load ⇒ **not stick-slip** (a stick-slip rate
  *rises* with drive velocity).
- **(b) torsion-bar feedback** — the base-assist loop of §2.2.
- **(c) engaged-only 21 Hz** — 9,200× less power with LKAS off; needs **applied** torque (14,750×
  applying vs **1.33×** commanding into a dead lockout).

**(a) and (b) are the same object seen from two sides.** The Q ≈ 14-40 resonance *is* the
wheel-inertia-on-torsion-bar mode, and (b) *is* the feedback loop wrapped around it. **(c) is that same
loop with the excitation switched on** — which is why it is engagement-required (73/88 engaged hands-off
vs **0/118 manual hands-off**, Fisher p = 3.8e-41) and applied-torque-required. Three labels, one
mechanism.

### 2.4 ⇒ THE RIGHT FRAME

> The loop is marginally stable because **base assist feeds back around a mode that has no damping below
> 35 km/h**. LKAS is the **disturbance**, not a term in the loop gain.
>
> **You cannot stabilise a marginally-stable loop by shaping its disturbance. You damp the mode.**

That is what V74 is already doing (opening the FactorC speed dead zone and the FactorE rate dead zone).
**"Self-interference cancellation" is a solution to a problem this firmware does not have.**

---

## 3. Q3 — WHERE COULD A CANCELLATION TERM BE INJECTED?

### 3.1 The notch audit — **"no notch exists anywhere" STILL HOLDS [EVIDENCE]**

Every filter decompiled in the assist chain is **first-order**:

| structure | coefficient | corner |
|---|---|---|
| `FUN_00038148` EMA | `0xC63AC` = 102/1024 | **16.7 Hz** @1 kHz |
| `FUN_00036682` final IIR | `0xC63D2` = 6/1024 | 0.94 Hz @1 kHz |
| LKAS lane pole | `gp-0x3d3c` = 0.96875 | 5.05 Hz @1 kHz |

**No biquad. No complex pole pair. No resonator. No notch.** V48B had to *build* one as a cave — that is
the proof, and it is the same proof that killed the ECU.

### 3.2 The one adjacent structure — verified, and already tested by deletion

**`FUN_00038148` is a second, parallel aggregator, and it is the only place in this firmware that
subtracts a modelled command from anything.** Fresh decompile:

```
model = EMA_α( Σ[ gp-0x6b4e·w + gp-0x6b4c·w_LKAS + gp-0x6b26·w + gp-0x6b46·w
                + gp-0x6bd0·w + gp-0x6bbe·w ] · sgn(gp-0x6752) · 2639 >>10 )  → gp-0x374c
resid = gp-0x6bfe − (model >> 4) + gp-0x6bfa
gp-0x6b70 = sgn(resid) · LERP(|resid|·cal),  clamped ±0xC6200 (8192)
```

- **`w_LKAS` = `0xC63AA` = tp+0x73AA = 1024 (unity).** **[EVIDENCE]** Both-parity byte scan: **exactly
  ONE reader (`0x381d8`), ZERO writers.** The only other hit, `0x8010e`, disassembles as
  `sst.b r14,0x2b,ep` — a **false positive, boundary-confirmed**. Identical standing to `0xC63A0`, which
  `build_v72_tva.py` verified the same way. All six weights are unity/stock ⇒ **no hidden loop gain in
  the aggregation.**
- **Task rate: caller is `FUN_0002214a` = task 0 = 1000 Hz.** On the *right* side of the task-5 lag
  argument.
- ⚠ **It is NOT a plant observer.** `gp-0x6bfe` ← `gp-0x6bfc`, and `gp-0x6bfa`, are **both mixer
  outputs** (`FUN_00026c80`). This is a residual between **two internal command reconstructions**, not
  command-vs-measurement ⇒ **it cannot cancel a physical coupling.**
  [EVIDENCE: structure. **BELIEF: role** — see OPEN #1, one decompile closes it.]
- 🛑 **Already tested end-to-end by deletion.** Its terminus `0xC6AF0` was zeroed and flashed as
  **V56 → NULL on the grinding, and it cost damping** (`docs/BUILD-LINEAGE.md:201`). `gp-0x6ad4` has only
  2 accesses image-wide, so that mute removed the whole chain's contribution.

⇒ `0xC63AA` is a legitimate cal-only, 2-byte, mode-proof lever — but expect little, and its chain is
already known to be small.

### 3.3 ★ The zero-reject window is a hard blocker for ANY injected term

**[EVIDENCE]** The aggregator's per-lane gates **zero-reject rather than saturate** — a lane outside its
window contributes **0**, not a clipped value:

| lane | cell | window (inclusive) | producer ceiling |
|---|---|---|---|
| friction comp | `gp-0x6b26` | **±1024** | `0xC407E` = 850 on V74 (511 stock) |
| damping | `gp-0x6bd0` | **±2048** | ≤1024 highway, **0 at creep** |
| boost | `gp-0x6bbe` | ±2048 | ≤512 |
| LKAS | `gp-0x6b4c` | ±10240 | ±10240 — **equals the window exactly** |
| resonance | `gp-0x6ad4` | ±10240 | ≤1024 |

**Consequence for a cancellation term.** Any term riding an existing lane must live entirely inside that
lane's window *including its own contribution*. One count past the cliff and the lane delivers
**zero — a full-magnitude, discontinuous dropout.** Because the cancellation term scales with the LKAS
command, **the dropout happens exactly when the cancellation is most needed.** A full-magnitude
discontinuity inside a marginally-stable loop at a lightly-damped mode is a textbook limit-cycle
generator — the same failure mode already identified in V72's flatten-to-relay error.

★ The kit has internalised this once already: V74's `0xC407E` was capped at **850, never 1024**, exactly
because *"a lane on the cliff contributes nothing."* Any cancellation design inherits that constraint
with far less headroom.

⚠ Note the contrast: the **aggregator OUTPUT** clamp (±0x2800 = 10240) is a **true saturating** clamp,
not a zero-reject. Different nonlinearity, different consequence — see §4.3.

### 3.4 If it must be a cave — the obligations, and why GATE 2 fails

**Shape required.** Because the coupling rises as ω² and flips sign past f₀, cancellation needs a
double-differentiator plus a resonant pole pair at f₀ ≈ 7.8-9 Hz with **Q ≈ 14-40**. That is a biquad.
That is a cave. **Code caves are this kit's only bricking class — V24, V27 and V48B all bricked the ECU;
every success since V29 has been cal-only or a single in-place branch/displacement edit.**

**GATE 1 — RAM ownership (writers *and* register-indirect access).** A biquad needs 4 state cells
(x₁, x₂, y₁, y₂) ⇒ **four collision chances**. V48B died on exactly one: `gp-0x14FA`'s high byte aliased
a live monitor/DTC status bitfield, an external write injected full-scale through a near-unity b₂, and
the motor slammed to the clamp. 🛑 **Static clearance is not sufficient — `gp-0x1500` passed BOTH static
methods and still failed on-car.** A probe build reading the candidate cells is mandatory before any
cave is trusted.

**GATE 2 — closed-loop stability, magnitude AND phase, in every loop the signal is in. This is where it
dies.**

- **Its own poles.** `r = exp(−π·f₀/(Q·fs)) = exp(−π·7.79/(20·1000)) = **0.99878**`. V48B's resonator was
  **r = 0.979, Q ≈ 3.2** — and *that* bricked the car when dropped into the always-on base-assist loop
  with no closed-loop check. **A cancellation filter must be ~17× more lightly damped than the thing
  that bricked it.**
- **Tuning sensitivity — the killer.** At Q = 20 the mode's phase rotates **180° across a fractional
  bandwidth of 1/Q ≈ 5%**. `f₀` is *measured* to move **9.0 → 7.7 Hz (−14%)** with load, and the 21 Hz
  mode moves 20.12 → 21.68 Hz with speed. ⇒ **an f₀ error of one bandwidth delivers the cancellation
  term fully INVERTED — anti-damping of the same magnitude as the signal it was meant to remove.** The
  kit already recorded the general form: *"no fixed-frequency notch can track it."*
- Plus §3.3: the term must also never cross its lane's zero-reject cliff.

**DTC-0x18 timing budget — the one gate it comfortably passes.** DTC 0x18 is the per-task cadence/overrun
watchdog, record `0xB7FDC` = `0x3D01` ⇒ **hard-fault eligible, motor-off, power-cycle to recover** — same
class as monitors 0x1C/0x1D. Budget for a 41-instruction biquad (V48B's size), once per 1 ms tick, no
loop/divide/call:

- optimistic (1 cyc/mem): 41 cycles = 0.51 µs = **0.051%** of the tick
- pessimistic (3 cyc/mem): 123 cycles = 1.54 µs = **0.154%**

Even a 100× estimate error leaves > 84% headroom. ⚠ Standing rule still applies: **any cave introducing a
LOOP, DIVIDE or CALL must re-check this.**

⇒ **Timing is not the constraint. Stability is.**

---

## 4. Q4 — THE OPERATOR'S TWO HEDGES

### 4.1 *"maybe this is only done below highway speeds"* — **RIGHT, for the opposite reason**

**[EVIDENCE]** `FactorC` (`0xC9E9C[mode]`) is speed-indexed with `X[0] = 2240 counts = **35.0 km/h**` and
`Y[0] = 0` on the live modes 24/26. A LERP clamps flat to `Y[0]` below `X[0]`, and the five damping
factors **multiply** ⇒

> **Base-assist damping is EXACTLY ZERO below 35 km/h — stock included. This car has never had creep
> damping.**

⚠ The onset is mode-dependent (X[0] = 1280/20 km/h on modes 0-3, 1920/30 km/h on 4/5, 2240/35 km/h on
10-15 and 22-27) — **never quote "35 km/h" without the mode.**

Both symptoms live below it: the ratchet at 4.9-8.0 km/h (speed-**invariant** in frequency, median
7.79 Hz), the 21 Hz mode at 1-4 m/s (**moves** with speed, 20.12 Hz @1.0 → 21.68 Hz @4.0 m/s). Highway
30-49 Hz has **no line**; highway grind #2 is struck (0 in 253.4 s, P(0) = 0.456).

⇒ **The hedge is correct, but the reason is inverted: it is not that the interference is larger at low
speed — it is that the damping which would suppress it is architecturally absent there.** Corroborating
speed structures: `0xC62EA` ≈ 5 km/h lockout (V53 → 0, carried on V74), the friction-comp speed LERP
`0xCBE74[mode]`, and the r24/r26 blend breakpoints at 0/10/50/100 km/h.

### 4.2 *"maybe this isn't needed until 8×"* — **NO. And 8× is much closer than it looks.**

🛑 **CORRECTION TO MY OWN FIRST DRAFT.** I originally computed today's LKAS command off `0xC646C` = 891
and got 417 counts. **That is the wrong cell.** V57 decoupled the forward path: the reader at `0x2A1F0`
was retargeted so the forward gain comes from a private cell, and `0xC646C` reverted to stock 891 for the
four *feedback* readers only. **Independently byte-verified on the flown V74 image:**

```
0x2A1EE  stock: 25 3f 6c 74 04 6f   disp 0x746C → 0xC646C
0x2A1EE  V74  : 25 3f d0 7c 04 6f   disp 0x7CD0 → 0xC6CD0      ← retarget IS in force
0xC6CD0  stock 0xFFFF (free)   V74 = 3564        ← the FORWARD gain, 4.00× stock
0xC646C  stock 891            V74 = 891          ← feedback readers only
```

**The corrected budget.** The setpoint limit is a degenerate flat 9-point LERP; V38 raised it
15360 → 16384, and 16384/32768 = ½ exactly, so **output = gain / 2**:

| | gain `0xC6CD0` | delivered LKAS counts | vs stock |
|---|---|---|---|
| stock | 891 (at `0xC646C`, limit 15360) | **417** | 1.00× |
| **V74 today** | **3564** | **1782** | **4.27×** |
| clamp knee | 4096 | 2048 | **4.91×** |
| nominal 8× gain | 7128 | 3564 → **clamped to 2048** | 4.91× |

> **⇒ The corrected ceiling is 4.91× stock, and V74 already delivers 4.27×. Only 14.9% headroom remains
> before `0xC61B2`/`0xC61B4` = 2048 binds.** True 8× requires raising both (in lockstep) from 2048 to
> **≥ 3564**.

Sanity check on the debounce channel at 8×: `gp-0x682f = 3564 >> 5 = 111` — under V37's raised gates
(255), but **1 count under stock's 112 DTC-0x49 gate.** ⇒ **8× is structurally dependent on V37's fix
being carried, with essentially zero margin.** Verify before any 8× build.

**And the substantive point survives the correction intact:** self-interference is
**amplitude-INDEPENDENT**, so it is already binding. The LKAS lane enters the aggregator **additively**,
and §2.1 shows no assist producer reads it back. **A linear loop's stability does not depend on the size
of a disturbance injected into it.** `L(jω)` is set by the boost curve, r24/r26, the damper, friction
comp and the plant — **the forward LKAS gain appears in none of them.**

The loop is already at |L| ≈ 1: **grind #1 is an established limit cycle**, and V74's own flight confirms
it is **still live at 2.72× over its 24-28 Hz control floor** in the clean speed window. The dose ladder
proves the amplitude is set by the nonlinearity, not the drive — **duty spans 64× (0.015 → 0.958) while
in-burst amplitude spans 1.24× (1232 → 1533) against a 5.62× dose ladder.**

⇒ **8× buys DUTY, not amplitude.** Expect the cycle to *start* far more often at roughly the same p-p.
That is the recorded rule: *"successful builds stop the cycle STARTING, they never shrink it."*

### 4.3 The one genuinely NEW risk between 4.91× and 8× — and it is not self-interference

At 3564 LKAS counts plus the base lanes, the aggregator's **output** clamp — a **true saturating** clamp
to ±0x2800 = 10240, unlike the per-lane zero-reject gates of §3.3 — becomes reachable for the first time.
`memory/accord-aggregator-never-rails-loop-is-linear.md` was established at today's authority. At 8× the
aggregator converts from a linear summer into a **saturating element inside a marginally-stable loop** —
the classic describing-function limit-cycle condition.

**[BELIEF — needs a per-frame census of the summed lanes on the V74 corpus to price. Purely analytical,
cheap, no drive required. Do it before any 8× build.]**

---

## 5. WHERE THE CONSTRAINT ACTUALLY IS — the intake rails

Folded in from a sibling analysis this session, because it independently supports the same thesis.

**[EVIDENCE, `FUN_00052676` decompiled]** `lkas_setpoint = clamp(request × −4, ±0x4000)`. openpilot's
`STEER_MAX` = 4096, and **4096 × 4 = 16384 = 0x4000 exactly.** ⇒ **zero upstream headroom** — the intake
clamp is dimensioned precisely to openpilot's full scale and cannot pass more, whatever the gain
downstream.

**And a second, openpilot-side limiter:** a hard slew cap at **123 counts/frame** (`0.03 × STEER_MAX`),
with **zero frames exceeding it**, binding **8.01% of engaged frames** and dominant at highway speed.

> **Together, 16.07% of engaged time is against one rail or the other.**

⇒ This is the operator's question answered from a third direction: **the binding constraint is not the
column coupling, and not the EPS gain — it is the intake dimensioning and the command slew rate.** A
cancellation term would do nothing about either.

---

## 6. ★ THE MOST ACTIONABLE ITEM — `FUN_00036c12`, and how to verify it

**This is the recommendation to act on.** It is the only structurally-correct-shape term that already
exists, is cal-reachable, and lives in the **only task where anything aimed at 18-22 Hz can work.**

### 6.1 What it is

**[EVIDENCE, decompiled this session]**

```c
// FUN_00036c12, called from task 0 (FUN_0002214a) => 1000 Hz
gain  = speed_LERP( 0xCBE74[mode] )              // mode-INDEXED (RULE 7 applies)
raw   = ( gp-0x6c2c_clipped * gain ) >> 6        // gp-0x6c2c = MOTOR-RATE DERIVATIVE
out   = ( raw * 0x111 ) >> 0x12                  // net scale ~ 1.628e-5
gp-0x6b26 = clamp( out, ±cal(tp+0x507e = 0xC407E) )   // 850 on V74, 511 stock
// -> aggregator FUN_0003aa2c, entering with a + sign, zero-reject window ±1024
```

`gp-0x6c2c` is motor **acceleration**. A gain × acceleration term added to the motor command is
**inertia compensation** — the textbook inverse-plant term. **Its sign versus the aggregator determines
whether it currently *reduces* or *increases* effective inertia, and that sign is UNVERIFIED.**

- If it **reduces** effective inertia: it raises f₀, cuts phase margin at the mode, and **backing it off
  is a cal-only, mode-proof damping lever nobody has tried.**
- If it **increases** effective inertia: it is already doing useful work and should be left alone — or
  raised.

### 6.2 Why this is the right place to look

- **Task 0 = 1000 Hz.** Per the ZOH table in §7, task 5 (100 Hz) carries 38-76° of lag at 21 Hz and may
  be *anti*-damping there. **V74's damper is task 5 and is structurally limited to the 7.79 Hz mode.**
  Anything aimed at grind #1 must live in task 0. This does.
- **`0xC407E` is mode-proof** (a direct `tp` scalar, RULE 7 clean) and is **already a characterised
  lever** — V73 flew it 511 → 850, live on ~80% of burst frames, **no band change**, a weak but real
  falsification bounded at +339 counts.
- 🛑 **The untested direction is DOWN.** Raising it did nothing. **Lowering it has never been tried**, and
  that is precisely the direction that tests the "reduces effective inertia" hypothesis.

### 6.3 Concrete verification plan — three steps, no flash until step 3

**Step 1 — settle the sign, statically (one session, no drive).**
1. Byte-dump `0xCBE74[mode]` for the live engaged/manual modes (**26 / 24**, per RULE 7) and confirm the
   LERP Y values are positive.
2. Decompile `gp-0x6c2c`'s producer and pin its sign convention: does positive mean positive motor
   acceleration, in the same frame as `gp-0x6abe`?
3. Confirm the aggregator add order/sign at `0x3acc8..0x3ace6` (golden model says `total += friction`,
   i.e. `+`).
4. Cross-check against the damper, which is *known* dissipative by construction
   (`sign = −sgn(gp-0x6abe)` @`0x3469e-0x3469a2`). **If `gp-0x6b26`'s effective sign is opposite the
   damper's, it is anti-dissipative.**
   **Deliverable: an EVIDENCE-grade sign, or a stated reason it cannot be settled statically.**

**Step 2 — price it, analytically (same session).**
Using the V74 corpus's measured `gp-0x6c2c` distribution in-burst, compute the lane's actual contribution
in aggregator counts at the ratchet and at 21 Hz. **Check headroom to the ±1024 zero-reject cliff (§3.3)
at every proposed value** — `0xC407E` = 850 already sits at 83% of it.

**Step 3 — only if steps 1-2 say anti-dissipative: a cal-only ladder.**
`0xC407E` **downward** (850 → e.g. 512 → 256), single-variable, mode-proof, no cave, DTC-0x18 cost zero.
Pre-register the same success/abort criteria V74 used (6-9 Hz duty and duration fall with |Δf0| ≤ 0.3 Hz;
abort if 5×f0 prominence > 3.0 — V74's flight read **2.227** against that gate).
⚠ **The speed LERP `0xCBE74` is MODE-INDEXED.** If step 2 says the *gain* rather than the *clamp* is the
lever, **write the engaged column of every row** — RULE 7, no exceptions.

---

## 7. THE RIGHT FRAME, OPERATIONALISED — which symptom is winnable where

Damp the mode, phase-correctly, **in a 1 kHz task**. Zero-order-hold transport lag:

| f | @100 Hz (task 5: boost + damping) | @1000 Hz (task 0: arb, aggregator, governor, shaper, `FUN_00036c12`) |
|---|---|---|
| **7.79 Hz** (micro ratchet) | 14.0° avg / 28.0° worst — **damping works** | 1.4° / 2.8° |
| 21.09 Hz (grind #1) | **38.0° / 75.9° — may be ANTI-damping** | 3.8° / 7.6° |
| 28.1 Hz (lane-change transient) | 50.6° / 101.2° — **anti-damping** | 5.1° / 10.1° |

⇒ **V74's FactorC/FactorE dead-zone opening is the correct lever for the 7.79 Hz ratchet and is
structurally incapable of fixing the 21 Hz mode.** **Anything aimed at 18-22 or 28 Hz must live in
task 0** — which is why §6 is the top recommendation.

---

## 8. RECOMMENDED NEXT STEPS, RANKED

1. **`FUN_00036c12` sign check (§6).** Highest value. Cal-only, mode-proof clamp, task 0, untested
   direction. Three steps, no flash until step 3.
2. **Aggregator saturation + zero-reject census at 8× (§4.3).** Purely analytical on the existing V74
   corpus. Prices the one genuinely new 8× risk and checks no lane sits near its cliff.
3. **Engagement-edge impulse-response estimate (§1.3).** Uses the corpus you have plus V74's stop-and-go
   route. Report γ² and K; **refuse below 0.5** per §1.5.
4. **`0xC63AA`** (1024, one reader, zero writers, boundary-confirmed) — cal-only, 2 bytes, mode-proof.
   Cheap, but its chain terminates at `0xC6AF0`, already zeroed by V56 with a NULL. Low expected value.

**Not recommended:** a cancellation biquad, in any form. §3.4.

---

## 9. OPEN ITEMS — what is unresolved, and what would change the answers

**OPEN #1 — `gp-0x6bfc`'s producer is un-decompiled.** I traced `gp-0x6bfe ← gp-0x6bfc`
(`FUN_0003bc20`, a range gate) and established `gp-0x6bfa`/`gp-0x6b4e` come from the mixer
`FUN_00026c80`, but did **not** decompile the mixer to confirm what `gp-0x6bfc` physically represents.
My "not a plant observer" conclusion in §3.2 is [EVIDENCE] for two of the three operands and **[BELIEF]
for `gp-0x6bfc`**. **If `gp-0x6bfc` turned out to be sensor-derived, §3.2 upgrades from
"command-consistency residual" to "genuine disturbance observer" and `0xC63AA` becomes a materially more
interesting lever.** One decompile closes it.

**OPEN #2 — ⚠ the setpoint-limit table has un-raised records, and the selector carries a RULE 7-class
assumption.** Auditing the bank at `0xE4180` on the flown V74 image: **4 of 6 records raised to 16384;
records at `0xE41D0` and `0xE4248` are still stock 15360.**

```
rec 0 0xE4180  15360 -> 16384  YES      rec 3 0xE41F8  15360 -> 16384  YES
rec 1 0xE41A8  15360 -> 16384  YES      rec 4 0xE4220  15360 -> 16384  YES
rec 2 0xE41D0  15360 -> 15360  no       rec 5 0xE4248  15360 -> 15360  no
```

V38 patched only the records believed reachable for this part number. The selector is **`gp-0x674e`** —
a *different* variable from the `gp+0x63fd` that RULE 7 demolished, and the golden model's assumed-live
record (`0xE41A8`, selector 1) **is** raised. **So this is not a claimed error.** It is an unverified
assumption **of exactly the class that has already failed once in this kit**, and it is decision-bearing:
if an un-raised record is live, the delivered command is **1670**, not 1782 (−6.3%), and §4.2's ladder
shifts. **Cheaply probeable — `gp-0x674e` is one probe rung.**
⚠ My record stride (40 bytes / 20 halfwords) is **[BELIEF]** inferred from the byte pattern; the
per-halfword reads are [EVIDENCE].

**OPEN #3 — `FUN_00036c12`'s sign.** §6. Not resolved; it is the top recommendation precisely because it
is both unresolved and cheap.

**OPEN #4 — the wheel-inertia bracket (§2.2) is unvalidated.** J and k are class-typical values, not
measured on this car. The 6.8-11.4 Hz bracket is a plausibility argument.

**OPEN #5 — `f₀`'s load dependence is taken from the record, not re-derived here.** The 9.0 → 7.7 Hz
figure is load-bearing for §3.4's tuning-sensitivity argument, so it is worth one independent
re-measurement if that argument is ever contested.

---

## 10. CORRECTION LOG

| # | claim | status |
|---|---|---|
| 1 | *"`0xC646C` = 891 is the forward LKAS gain ⇒ 417 counts today"* | **WRONG — mine.** V57 retargeted the forward reader to `0xC6CD0` = 3564. Today is **1782 counts = 4.27× stock**. Byte-verified on the flown image, both the retargeted displacement at `0x2A1F0` and both cells. The **conclusion survives** — the clamp still binds before 8× — but the headroom statement inverts: I implied ample room; there is **14.9%**. §4.2 |
| 2 | *"at 8× the aggregator becomes a saturating element"* | **Stands, refined.** The per-lane gates **zero-reject**; the **output** clamp saturates. Different nonlinearities with different consequences — §3.3 vs §4.3. |

---

**Grounding:** `docs/STATE.md` · `docs/BUILD-LINEAGE.md` RULE 6 / RULE 7 ·
`analysis-2020accord/eps_lkas_chain_model.py` §2/3/3B/5/6/6B/9/10 · memories on the LKAS low-pass,
vibration characterisation, engagement signals, task rates, DTC 0x18, V48B, V55, V56, V57.

**Key artefacts (absolute paths):**
- `C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\eps_lkas_chain_model.py`
- `C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\docs\BUILD-LINEAGE.md` (line 201 — the
  `FUN_00038148` chain row)
- `C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\memory\reference-accord-v55-flashed-oscillation-is-internal.md`
- `C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\memory\accord-task5-is-100hz-damper-cannot-damp-21hz.md`
- `C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord\_v74_engagedcols_x0_12_addonly_plain_image.bin`
- `C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord\stock_fw_dump\code.bin`

**External sources:** [openpilot 0.11.1 release notes](https://blog.comma.ai/0111release/) ·
[commaai/openpilot RELEASES.md](https://github.com/commaai/openpilot/blob/master/RELEASES.md)
