# THE 2020 ACCORD EPS ~21 Hz STEERING VIBRATION — MASTER DOSSIER

**Platform:** 2020 Honda Accord `39990-TVA-A160`, Renesas V850E2. **Baseline:** V38 on-car (4× stock LKAS
authority). **Created:** 2026-07-21, consolidating V38→V47 and a six-stream evidence audit (firmware
loop trace, damper-authority trace, measured route-b9 telemetry, community scrollback, OEM/patent/academic
research, plus the full handoff + memory record). **Status of the problem: UNSOLVED.**

This is the single reference for the vibration. It supersedes the scattered vibration narratives in the
per-build handoffs where they disagree. The **ratchet** is a *separate, solved* symptom and is treated
only where it intersects (Section 11).

> ⚠ **The operator's instruction that motivated this document (2026-07-21):** "The vibration also appears
> to create its own ratchet; I am no longer confident the ratchet fix works unless the vibration is
> solved too." See Section 11 — there are **two** ratchets, one solved and one that is a vibration
> symptom.

---

## 0. TL;DR — the one-paragraph diagnosis

The vibration is a **~21 Hz, Q≈13.6, two-inertia torsional resonance** of the steering system — the
**motor/rack inertia oscillating against the steering-wheel/column inertia, with the torsion bar (the
torque sensor itself) as the compliance between them.** This is a documented, ordinary EPS mode
(literature places it at ~20.9 Hz). It is lightly damped. **V38's 4× LKAS gain adds +12 dB of loop gain,
which erodes the phase/gain margin at that mode and turns it from benign into self-excited** (measured:
63.7× more band power at 20–30 Hz than the 2× era). It is **worst hands-off** (measured 75–314× stronger
than hands-on) because **the driver's grip supplies collocated mechanical damping at the wheel/column
antinode** — the one place the mode's energy actually lives. **Every firmware damper we have tried
(V44, V47) failed for a provable control-theory reason: they damp using the *motor-resolver rate*, which
sits on the far side of the torsion bar and is *non-collocated* with the wheel-side mode — it cannot
reach it, and can even anti-damp it.** The loop gain that sustains the ring is supplied by unfiltered,
*collocated*, positive-feedback base-assist lanes that read the torsion bar — chiefly `FUN_0003a382`,
which has **never been tested fully suppressed.** The evidence-based fixes that keep 4× are: (1) attenuate
the 21 Hz loop gain on those collocated positive-feedback lanes (cal-only, lowest risk), or (2) add a real
**notch at 21 Hz** or a **collocated torque-rate damper** (the OEM-standard answer; likely a code cave).

---

## 1. PHENOMENOLOGY — the measured/observed facts

### 1.1 What the operator feels
- **Vibration during any wheel movement driven purely by LKAS.** Hands-off (openpilot steering).
- **Adding hand torque / assisting the wheel makes it vanish.** (See §3 — collocated damping.)
- **Speed-independent phenomenon; audibility is speed-dependent** — felt at all speeds, audible as a
  "grinding" only near 5 mph (road-noise masking elsewhere), though it is also genuinely *strongest* at
  low speed.
- **Appeared at V38 (4×). Not reported on V31 (2×) or earlier.**
- **V47 (latest, flashed):** aggressively opening both damper deadzones only *barely* reduced the 5 mph
  noise and did **nothing** for the in-motion wheel vibration.

### 1.2 What was measured (route b9, the only post-V38 telemetry; raw CAN 399 @ 99.99849 Hz)
Provenance: recorded in `analysis-2020accord/model/eps_lkas_chain_model.py` (`vibration_hands_off_analysis`,
lines ~2455–2502) and the V44/V46-V47 handoffs. Raw FFT/coherence scripts lived in session scratch and
were **not persisted** — the numbers are recorded results, not re-runnable from the repo.

| Quantity | Value |
|---|---|
| Peak frequency | **21.4 Hz** (⚠ aliased at 100 Hz sampling — indistinguishable from 78.6 Hz) |
| Q | **≈ 13.6** (ζ ≈ 0.037, ~3.7% critical) |
| −3 dB width | 1.58 Hz |
| Auto-coherence (ring-down) | ~0.23 s (~4 cycles) |
| Amplitude | ~139 counts (in the CAN-399 driver-torque signal) |
| "Coherent driven line" test | slope **0.635** (1.0 = a fixed-frequency driven line) → **it is a broad resonance, NOT a command-driven line** |
| Band power 20–30 Hz, V38 vs 2× era | **63.66×** (while 0.5–5 Hz went *down* to 0.37× — proves it's band-localized, not a global scale) |
| Hands-off vs hands-on, 19–23 Hz, speed-matched | **314×** (2–10 mph), 106× (10–20), 75× (20–30) |
| Speed trend | present at all speeds, ~**10× stronger** at low speed; dip at 10–12 mph |
| STEER_STATUS during vibration | only 0 (NORMAL, 89%) / 3 (LOW_SPEED_LOCKOUT, 11%); **never 4 or 7; no per-cycle toggling** → not a fault/cut phenomenon |

### 1.3 Retracted measurements (do NOT resurrect)
- **"Sharp isolated 21.02 Hz clock-locked line."** RETRACTED — FFT windowing artifact (concatenated
  discontiguous windows). Redone: broad, Q=13.6. A digital limit cycle would be orders of magnitude
  sharper.
- **"Invariant across speed ⇒ clock-derived."** Withdrawn — the estimates only looked invariant because
  they all sit inside one broad hump.
- **The 1/A rate-limiter limit-cycle model** (predicts 13.4 Hz at high amplitude; measured 21.8) — falsified.

### 1.4 The single most important gap
**The 2–10 mph hands-off spectrum — the operator's worst regime — is UNAVAILABLE.** Route b9 has only
2.5 s contiguous hands-off below 10 mph, under one FFT window. A slow-speed hands-off log is the highest
value data to collect, and no measurement exists of the motor-side signals (`gp-0x6ac0`, internal LKAS
command, delivered torque) because they are not on CAN and live UDS RAM telemetry is blocked by the
comma-4 OBD-mux/steering-bus contention. **A direct command↔vibration cross-coherence was never
computed** — "self-excited vs command-driven" rests on the hands-off discriminator + the not-a-driven-line
test, not on a coherence estimate.

---

## 2. WHY ~5 MPH — and why it is NOT a firmware speed gate
- **There is no vehicle-speed input anywhere in the command or base-assist path** (all 9 aggregator
  lanes decompiled). The only rate adaptation is on **motor/resolver electrical-angle rate**, not road speed.
- "~5 mph" = openpilot `minEnableSpeed = 3 mph` (below it, OP can't engage → no LKAS → no excitation)
  **plus plant physics** (low speed demands the most assist torque = most excitation, and least road
  noise = most audible). `STEER_STATUS=3` "LOW_SPEED_LOCKOUT" is a fallback for "OP not engaged-steering,"
  not a speed comparison.
- **Consequence: a fix cannot be speed-conditional.** It must reduce the loop gain / add damping at the
  mode regardless of speed.

---

## 3. THE PHYSICAL MODEL — a two-inertia torsional mode, and the collocation problem

*(OEM patent / academic corroboration; see Section 8 for citations.)*

### 3.1 The mode
The steering driveline is a **two-inertia torsional resonator**: the assist **motor + rack-pinion
inertia** on one side, the **steering wheel + column inertia** on the other, coupled through the
**torsion bar** (which *is* the torque sensor). EPS modeling literature places this exact mode at a
"complex conjugate pole at 131 rad/s (**20.9 Hz**) representing the motor/rack inertia vibrating due to
the torsional stiffness of the steering wheel and column" — within rounding of the measured 21.4 Hz.
- **Plant hardware:** dual-pinion variable-ratio EPS (assist motor on a second, off-axis rack pinion,
  Showa/Hitachi-Astemo). **Sensor A and Sensor B are the MAIN and SUB Hall channels of ONE torsion-bar
  sensor** (Honda DTC C1420), not two physical sensors. Motor position = resolver.
- **Mode shape:** the **wheel/column end is the large-motion antinode**; the **motor/rack end is on the
  other side of the torsion bar.**

### 3.2 Why 4× triggers it
Raising assist gain lifts the whole loop-gain curve, pushing the gain-crossover frequency up and **eating
phase margin** at a lightly-damped mode. **4× = +12 dB of loop gain.** If the stock gain margin at the
21 Hz peak was under ~12 dB, the mode crosses 0 dB with negative phase margin → **self-excited limit
cycle** (describing-function / Nyquist criterion). This is exactly "V38's 4× excites the mode; zero
damping was an *enabling* condition; 2× did not vibrate."

### 3.3 ★ THE COLLOCATION KEYSTONE — why hands cure it but the firmware damper can't
This is the central result and it explains every failed damper build.
- **A collocated sensor/actuator pair** on a lightly-damped structure has interlaced poles/zeros near the
  imaginary axis; velocity feedback then adds real damping to the mode **for any gain** (guaranteed
  stable, Preumont).
- **Gripping the wheel is collocated with the mode** — the hand's mass + damping load the **wheel/column
  antinode**, on the **column side** of the torsion bar, directly across the compliance that stores the
  mode's energy. So a grip reliably injects modal damping. And the vibration is **worst hands-off**
  because that damping is then entirely absent.
  - ⚠ **Cure-mode refinement (operator, 2026-07-21): only an ACTIVE grip / turning quiets it — a light
    static rest does NOT — and openpilot KEEPS COMMANDING torque through the turn (the command does NOT
    drop when the driver assists).** So the cure is **not** a reduction in excitation. The excitation
    (LKAS command) is the *same* hands-on and hands-off; the only thing that changes is the **collocated
    mechanical impedance/damping the active grip adds at the wheel antinode** — and it must be an active
    (firm, co-contracted) grip because a relaxed rest's impedance is too low to suppress a Q≈13.6 mode.
    - **Consequence:** the measured 75–314× hands-off/hands-on ratio is the effect of **collocated hand
      damping alone**, at constant excitation. The firmware role is that the 4× loop gain has raised the
      *effective closed-loop Q* of the mode (positive feedback) to where it rings hands-off; the hand's
      damping pulls that Q back down. So the firmware fix is to **reduce the loop gain / effective Q at
      21 Hz** (attenuate the collocated positive-feedback carriers, or decouple the 4× from them) so the
      mode no longer rings even without hand damping — OR add collocated damping, which the firmware
      cannot do from the motor side (§3.3). Reducing the *forward* command is neither necessary nor the
      goal (we keep 4×).
- **The firmware damper (`FUN_00034350`, Factor E) senses MOTOR-RESOLVER RATE — non-collocated.** The
  motor is on the **far side** of the torsion bar. At 21 Hz the torsion-bar compliance **decouples** the
  wheel inertia from the motor: the motor barely *observes* the wheel-side oscillation, and its damping
  torque enters on the rack side, **isolated from the antinode** by the same compliance. Non-collocated
  velocity feedback can damp some modes while **destabilizing** others (pole-zero flip). **You cannot
  reliably damp a wheel-side mode from a rack-side velocity sensor at any gain.** This is why V44 and
  V47 (both motor-rate Factor E) produced nulls, and it predicts *continuing to tune that damper will
  keep failing.*
- **Corroboration from telemetry:** the voted torque `gp-0x6a5e` (Factor C's axis) is **so slew-limited
  it cannot even track a 21 Hz oscillation** (max trackable ≈ 4.6–45 counts vs the 2240 gate) — so the
  driver-torque damper factor responds to *DC hand torque*, not the ripple. V44's "open the hands-off
  deadzone" premise was doubly wrong: the factor is non-collocated *and* blind to the ripple.

---

## 4. THE FIRMWARE MODEL — how the 21 Hz loop closes

### 4.1 Topology
LKAS and base assist are summed at the **motor-torque demand aggregator** `FUN_0003aa2c → gp-0x6b94`,
which then passes through the **governor** `FUN_0004503c → gp-0x6ace`, the comp-add/shaper
`FUN_00042af8`, to the final FOC command `gp-0x6b98`. Base assist joins **one stage after** the LKAS-only
mixer, in parallel, then shares the governor and shaper.

### 4.2 The lanes that read the torsion bar (the candidate feedback paths)
The 21 Hz feedback CANNOT travel down the LKAS lane — that lane is a **~1–5 Hz low-pass** (arbitration
IIR `gp-0x3d3c`, pole 0.96875). So the loop closes through the **base-assist lanes that read Sensor-B
`gp-0x4f60` / the voter `gp-0x6a5e`**:

| Lane → gp- | Producer | Task rate | Filtered? | Polarity | 21 Hz carrier? |
|---|---|---|---|---|---|
| `0x6ad4` **residual** | `FUN_0003a382` | **1 kHz** | **UNFILTERED** (both poles `0xC6450`/`0xC644A` = 1024 unity) | **REINFORCING (positive feedback / anti-damping)** | ★ **strongest surviving; never fully suppressed** |
| `0x6bd0` damping | `FUN_00034350` | ~100 Hz (slow) | LERP, no IIR | NEGATIVE (velocity-opposing) but **non-collocated** | no — the (failed) fix, not the carrier |
| `0x6bbe` boost | `FUN_00034a72` | ~100 Hz (slow) | effectively unfiltered | **region-dependent** (positive-feedback slope below ~2560 counts) | possible, untested |
| `0x6b86` magnitude | `FUN_000352b4` | 1 kHz | peak-hold | [open] | weak (peak-hold kills phase) |
| `0x6b26` friction | `FUN_00036c12` | 1 kHz | ~unfiltered | angle-keyed (not torque-polarity) | doubtful |
| inline `r24` | `FUN_0003aa2c` | 1 kHz | raw derivative, ±3 deadzone | assist (collocated, anti-damping if it aids rate) | zeroed V39, null |
| inline `r26` | `FUN_0003aa2c` | 1 kHz | raw × adaptive gain | assist | zeroed V42, null |
| `filtered_36682` | `FUN_00036682`←`FUN_00036828` | 1 kHz | **genuine EMA, 0.94 Hz corner** | [open] | no — kills 21 Hz regardless |

### 4.3 Key firmware facts established this audit
- **`FUN_0003a382` is the strongest surviving unfiltered, reinforcing, 1 kHz, torsion-bar-reading lane —
  and it has never been tested fully suppressed.** V43 filtered only its Stage C (`0xC644A`), V46 only its
  Stage A (`0xC6450`); each alone was null, **and both were reverted.** As shipped in every build to date
  it is completely unfiltered on all branches. ⚠ Its Stage-C branch is a **raw one-sample difference** (a
  derivative) — a *collocated* torque-derivative term with **assist (reinforcing) sign = anti-damping.**
- **★ Topology CONFIRMED PARALLEL** (instruction-level, `0x3a382`–`0x3a8a7`, second-method corroborated
  via an `add`-chain trace to the sole `gp-0x6ad4` store `@0x3a8a0`). The output is a **3-way SUM of three
  independent branches computed from one `errorterm` (= `clamp(Sensor-B gp-0x4f60 − model gp-0x6ad6, ±0x2800)`):**
  - **Stage A** — EMA, pole cal `0xC6450` (V46's target), state `gp-0x367c`.
  - **Stage C** — a raw one-sample **derivative** then EMA, pole cal `0xC644A` (V43's target), state `gp-0x3680`.
  - **S3** — a **clamped ACCUMULATOR with NO time-constant cal at all** (state `gp-0x3688`), i.e. a
    bounded integrator that can rail/oscillate at the *input's* frequency; its only levers are its
    motor-rate-keyed pre-scale LERP `uVar16` (`≈0xC6B0A`) or the shared post-sum gain.
  - Then `gp-0x6ad4 = ((StageC + S3 + StageA) >> 5) × uVar27 >> 10 × polarity`, final dynamic clamp.
  **This proves why V43 and V46 each did nothing** (each attenuated 1 of 3 branches; the other stage AND
  the un-cal'd S3 accumulator still passed the ripple). **It also means "lower both stage poles" is
  necessary-but-not-sufficient — S3 has no pole to lower.** The clean single lever is the **post-sum
  magnitude gain `uVar27`** (table `≈0xC67B2`, keyed on `gp-0x671a`), which scales all three branches
  together and is a true magnitude scaler (kills 21 Hz *and* DC). It reads as flat-unity (1024) on a
  partial sample — **a full table dump + reader-count is in flight before it can be cut** (see §10). Pure
  leaf confirmed (0 `jarl` over 468 instructions) — no fault/shadow path under any cal-table edit.
- **★★ A SECOND carrier is CONFIRMED LIVE (the "type-8" path) — but it is NOT `0xC646C`-scaled
  (corrected).** Routing (instruction level, second-method corroborated): a value → `gp-0x6b12` →
  `FUN_0002caa2` (hysteresis latch) → `FUN_00025c32` **distribute slot 8** → `FUN_00026c80` mixer (static
  type 0 → plain copy, **no scaling, no EMA**) → summed into **`gp-0x6b4c`**, the LKAS-lane variable the
  aggregator reads. So it is a fast (1 kHz), UNFILTERED, positive-feedback carrier that **bypasses the
  LKAS ~5 Hz IIR** — meaning "the LKAS lane is purely a low-pass" is incomplete; `gp-0x6b4c` has an
  unfiltered parallel injection.
  - ⚠ **RESOLVED (lead decompiled `FUN_0002c478` directly, settling a two-tracer conflict):**
    `gp-0x6b12 = (envelope × iVar12) >> 5`, FSM-latched + validity-gated, where `iVar12` is the
    **delivered-command delta** (`gp-0x6b98 − prev`, i.e. a command DERIVATIVE feedback — a classic
    resonance destabilizer) and `envelope` is a MIN of LERPs keyed on `gp-0x6a5e`/`gp-0x6a10`/`gp-0x6ac0`.
    The `0xC646C`-scaled term (`gp-0x4f60 × 0xC646C >> 15`) feeds only (a) the *dead* `gp-0x6b10` and
    (b) a **LERP index that saturates at ±0x2800** — so `0xC646C` affects `gp-0x6b12` **weakly and
    nonlinearly**, NOT as a proportional factor. **Consequences:** (1) it scales mainly with the delivered
    command (≈4× under any 4× scheme), so Route B does not reliably reduce it → **Route B is hygiene-only**
    (§10); (2) the clean way to attack it is to **remove it from the sum** (the `0xC4120` mute), not to
    tune the gain.
  - **Direct cal-only mute available:** `FUN_00026c80`'s per-slot sum gate `tp+0x5118[8]` = **`0xC4120`**,
    byte **`1→0`**, removes slot 8 from `gp-0x6b4c` without touching `0xC646C` or forward authority.
    ⚠ Not yet certified collateral-free — `FUN_00027b0a` reads the same array; decompile it before building.
  - ⚠ **Activity uncertain.** Slot 8 is gated by `FUN_0002caa2`: an outer latch (`gp-0x3cba`) trips
    **permanently** (no reset path found) if `|gp-0x6b12| > 307` (`0xC61D2`), and an inner mode-FSM must
    sit in {2,3,4}. The gating is broad/plausibility-based (not fault-only), so it is *plausibly* live in
    normal driving, but the duty cycle could depend on drive history. Not closed statically
    (`unaff_r28`); needs `emulate_function` or live telemetry on `gp-0x678c`/`gp-0x3cba`.
- **The 4× gain `0xC646C` has 6 readers, not 5 (a 6th at `0x2a904`).** Only ONE feeds a base-assist lane
  (`FUN_00036682`) and that lane is heavily low-passed (0.94 Hz) → **4× does not amplify the 21 Hz path
  digitally; it amplifies it *physically* (4× motor torque → 4× plant ripple).** Two readers
  (`FUN_0002caa2`, `FUN_0002b62c`) remain unresolved (do they write back into torque? — under check).
- **The governor slew (`0xC6206`=512 / `0xC6208`=205) has 11–27× headroom over a 140-count 21 Hz ripple
  → it does NOT clip the ripple in either hands-on or hands-off state.** This cleanly explains V45's null
  (it never had a chance to act) and closes the "rate-limiter" idea for the 21 Hz.
- **Damper authority is a minority contributor:** absolute ceiling ~793 counts (all factors max),
  practical ~512 in steady motion, V47 realistic ~165–235 — vs a 1782-count LKAS lane and a 4342-count
  peak command. Safely raisable ~4× via the factor tables (no float-mirror/DTC trap) IF ever wanted — but
  §3.3 says raising a *non-collocated* damper is fighting physics.
- **The damper's output clamp is a DTC-0x1d no-debounce hard-shutdown trap** (int `0xD209C/0xD20A8` ↔
  float mirror `0xC6554/58/5C/60`). Never edit the int clamp without a bit-exact float edit.
- **The openpilot outer loop is bandwidth-incapable of 21 Hz** (100 Hz control, 100 ms actuator delay,
  ~3 Hz command rate limit; it aliases 21 Hz). The oscillation is entirely in the **fast firmware/plant
  inner loop.** openpilot's only contribution is a several-Hz effect (the 4×-loosened normalized rate limit).

---

## 5. THEORY LEDGER — every lever, and WHY it failed (the retrospective)

Ranked by build order. STATUS reflects on-car results where flashed. "Why it failed" is the post-audit
explanation.

| Lever | Build | Result | STATUS | Why it did/didn't work (post-audit) |
|---|---|---|---|---|
| Zero direct Sensor-B rate lane **r24** | V39 (flashed) | no change | **FALSIFIED** | r24 has a ±3 deadzone (already near-inert near zero); one of several parallel lanes, not dominant; and per §3.3 removing a collocated derivative moves toward *less* damping, wrong direction |
| Zero adaptive rate lane **r26** | V42 ch2 (flashed) | no change | **FALSIFIED** | another parallel derivative lane; not dominant. With r24, the *identified* Sensor-B derivative pair is out — but `FUN_0003a382`'s derivative stage was never in that pair |
| **State-4 governor ratchet byte** | V42 ch1 (flashed) | **fixed the ratchet** | **CONFIRMED (ratchet only)** | Real root cause of the hard-turn ratchet. Does not touch the vibration. See §11 |
| **Stage-C** dirty-derivative pole (`0xC644A` 1024→low) | V43 (flashed) | no change | **FALSIFIED (alone)** | Low-passed only ONE stage of `FUN_0003a382`; if the stages are parallel, Stage A still passed 21 Hz. Reverted. **Never combined with Stage A.** |
| **Factor C** hands-off damping floor (`0xD27C6/DA`) | V44 (built; subsumed) | no change | **FALSIFIED** | Damper is a 5-factor product; Factor E still zeroed it at low rate. AND the factor is non-collocated (§3.3) AND blind to the 21 Hz ripple (voter too slew-limited). Triply doomed |
| **Hands-off governor slew** (`0xC6206` 512→205) | V45 (flashed) | no change | **FALSIFIED** | The slew has 11–27× headroom over a 140-count ripple — it never clips it. A bandwidth gate on a signal it doesn't bind |
| **Stage-A** carrier low-pass (`0xC6450` 1024→32) | V46 (flashed) | no change | **FALSIFIED (alone)** | Low-passed only the OTHER stage of `FUN_0003a382`; Stage C (derivative) still passed 21 Hz. Reverted. **Never combined with Stage C.** |
| **Both damper deadzones** (Factor C + Factor E, aggressive) | V47 (flashed) | barely quieter 5 mph; nothing in-motion | **FALSIFIED / largely ineffective** | Non-collocated damper (§3.3). Factor E already open in motion (deadzone only bites near-stationary → tiny 5 mph help). Should have delivered ~165–235 counts in motion but didn't → damper is not the mechanism |
| openpilot `STEER_DELTA` slew | never isolated | — | **OPEN, several-Hz only** | Upstream of the LKAS ~1–5 Hz low-pass → cannot deliver 21 Hz. Cheap to try for jitter/ratchet (§10) |
| Motor-rate adaptive cap flatten | V41 (flashed) | no change | **FALSIFIED** | Downstream of the gain; an amplitude ceiling, not a filter |
| Pre-gain deadband (`0xC61B8`) dither | never built | — | **ELIMINATED** | Gate off above 4 mph; vibration is speed-independent |
| LKAS IIR self-oscillation / rate-limiter limit cycle / soft-EME oscillator / thermal-budget oscillator / `gp-0x67fe`/`gp-0x6752` chatter | analytical | — | **DEAD (proven)** | Each structurally impossible — see the per-item notes in the source memories |

**The cross-cutting pattern:** we picked off individual lanes and deadzones one at a time; **none moved
the in-motion vibration.** Two reasons, now understood: (1) the damper levers were **non-collocated** and
could never work; (2) the carrier levers each hit **one stage of a coupled lane** (`FUN_0003a382`), and
the community's own rule is "changing one member of a coupled filter trio just causes noise." The
never-tried configuration is **suppressing the whole `FUN_0003a382` lane at once**, and the never-tried
*class* is a **collocated** damper or a **notch**.

---

## 6. WHAT IS RULED OUT vs STILL OPEN

**Ruled out as the mechanism (with reason):**
- The motor-rate viscous damper as a *fix* — non-collocated (§3.3). *Stop tuning Factor E.*
- The governor slew / rate limiter — 11–27× headroom, doesn't bind.
- The 4× gain amplifying base assist *digitally* — it doesn't (only a heavily-filtered lane).
- The openpilot outer loop — bandwidth-incapable of 21 Hz.
- r24 / r26 as dominant carriers — zeroed, null.
- Any speed-gate / fault-path / STEER_STATUS mechanism — status is inert to the vibration.

**Still open (live hypotheses):**
1. **`FUN_0003a382` is the dominant collocated positive-feedback (anti-damping) carrier**, sustaining the
   ring; never tested fully suppressed. *Leading, cal-only, testable in V48.* (Contingent on parallel topology.)
2. **The anti-damping is distributed** across several collocated lanes (`FUN_0003a382` + boost +
   magnitude + r24/r26), so no single-lane edit is enough — needs an aggregate attenuation, a notch, or a
   collocated damper.
3. **The mode is mechanically dominant** with firmware only enabling — in which case no *cal* fully cures
   it and the practical firmware answers are a notch, a collocated damper, or reducing 4×.
   *(The broad Q=13.6 line rather than a razor-sharp digital limit cycle gives this real weight.)*

Hypotheses 1–3 are not mutually exclusive, and — importantly — **the same firmware action (attenuate the
21 Hz content in the collocated positive-feedback path) helps under all three.**

---

## 7. RETRACTED / CORRECTED CLAIMS OF RECORD (do not resurrect)
1. "Sharp isolated 21.02 Hz clock-locked line" → FFT artifact; it is a broad Q=13.6 resonance.
2. Vibration is "small dithering around zero / upstream of the gain" → it is a **large** command,
   downstream regime.
3. `gain_rescaling_invariance` covers the vibration → no; the carrier is a *physical* sensor reacting to
   real delivered torque (4× ripple), which nothing digital compensates.
4. `FUN_0003a382`'s two lag gains = 4 (heavily damped) → they are **1024 = unity passthrough**.
5. Motor ripple "ruled out" → downgraded; the comparison case was always hands-on (the damping condition).
6. Damper is 4 factors / 1 deadzone → **5 factors, 2 deadzones**; but note both deadzone framings are
   moot for the 21 Hz per §3.3.
7. Damper output clamp ±2048 → **dynamic ±512..1024**.
8. Half-wave-rectified damper / `gp-0x6abe` pinned in normal driving → both retracted.
9. `0xC6194` is the LKAS slew lever → **dead calibration** (×`0xC63CC`=0).
10. The V45 "rate-limiter" masking-by-r23 framing → superseded: the slew simply has 11–27× headroom and
    doesn't bind at all.

---

## 8. EVIDENCE SOURCES (this audit)
- **Firmware loop trace** (GhidraMCP): lane enumeration, `FUN_0003a382` never-fully-suppressed, 6 gain
  readers, slew headroom.
- **Damper-authority trace** (GhidraMCP): non-collocation implications, authority ceilings, DTC-0x1d
  trap, V47-should-have-helped discrepancy.
- **Measured telemetry** (route b9): the numbers in §1.2; openpilot bandwidth analysis.
- **Community scrollback** (`discord-export/`, `docs/research/HONDA-EPS-PID-KNOWLEDGE.md`): Aragon —
  "jackhammer = feedback loop registering false presses on the torque sensor," cured by the **filter
  table**; Brett — "tiny jitter = too much noise in the signal → filter/damp the plant path"; vfn —
  "reset rate tables to stock, use 2× not 4×," and "changing one member of a coupled filter trio just
  causes noise." **No community datapoint on this exact V850 plant; nobody has kept above-stock authority
  AND killed the oscillation** — their universal fix is to reduce gain.
- **OEM/patent/academic**: ~20.9 Hz two-inertia torsional pole (motor/rack vs column stiffness); notch on
  torque-sensor/current command is the **standard production fix** (US6107767, US8554417, GB2454788A);
  active damping must be **collocated** (US7549504, US9738309); collocated-vs-non-collocated theory
  (Preumont); 4× = +12 dB erodes margin (Complexity 2020, DF/Nyquist). **This firmware has no notch
  anywhere — that is the actionable gap.**

---

## 9. OPEN QUESTIONS / HIGHEST-VALUE MISSING DATA
1. **`FUN_0003a382` internal topology** — RESOLVED: **parallel 3-way sum** (Stage A + Stage C + S3
   accumulator). The remaining sub-question is the **`uVar27` post-sum gain table** (dump + reader-count)
   to lock the clean whole-lane lever. *(In flight.)*
2. **★ Does `FUN_0002caa2` "source type 8" reach `gp-0x6b4c`?** — the highest-value firmware trace open.
   Decides whether there is a **second, 4×-scaled, fast, unfiltered** carrier and therefore whether the
   V48 target is `FUN_0003a382` (physical) or this path (digital, 4×-gated). *(In flight.)*
3. **2–10 mph hands-off spectrum** and **motor-side `gp-0x6ac0`** — not on CAN; blocked on comma-4
   OBD-mux contention. The single highest-value *telemetry* to unblock.
4. **True (un-aliased) mode frequency** — 21.4 vs 78.6 Hz. Does not change the fix direction but sets a
   notch/filter center for Tier 2.
5. **Direct command↔vibration cross-coherence** — never computed.

---

## 10. V48 — THE FIX MENU AND RECOMMENDATION

**Design goal:** eliminate the vibration (and the vibration-induced ratchet, §11) while keeping 4× stock
LKAS peak authority. Everything below keeps the 4× LKAS lane untouched.

The evidence collapses the menu to **three classes**, in ascending risk:

### Tier 1 — cal-only, low risk (recommended first shot)
**V48-A: attenuate the whole `FUN_0003a382` reinforcing residual lane in ONE point — the post-sum gain
`uVar27` (`≈0xC67B2`).** Topology is confirmed **parallel** (Stage A + Stage C + the un-cal'd S3
accumulator), which is exactly why V43 (Stage C only) and V46 (Stage A only) were null — each left the
other two branches passing the ripple. `uVar27` sits **after** the 3-way sum, so lowering its Y-values
scales all three branches (including the pole-less S3) together; it is a true magnitude scaler, so it cuts
the 21 Hz content **and** the lane's DC bias in proportion. Rationale: `FUN_0003a382` is the strongest
surviving *collocated, unfiltered, positive-feedback (anti-damping)* 1 kHz carrier; cutting it raises the
mode's net damping. Pure leaf (0 `jarl`), no fault/shadow path, CRC-clean, keeps 4×.
- **Sizing:** start at a partial cut (e.g. `uVar27` Y → 512 = ½, or 256 = ¼) rather than zero, to preserve
  a scaled version of the lane's legitimate residual function while removing most of the anti-damping.
- **Gate — CLEARED:** the `uVar27` table (`0xC67B2`: X=[5,10,15], Y=[1024,1024,1024]) is confirmed
  flat-unity and **single-reader (only `0x3a4ae` inside `FUN_0003a382`; byte-scan corroborated)**. Lowering
  its 3 Y-values is a clean, collateral-free, whole-lane magnitude attenuator (covers Stage A + S3 + Stage
  C). S3's own pre-scale (`0xC6B0A`, Y=98≈0.096, single-reader) is available as a secondary lever.
- ⚠ Efficacy honesty: if the anti-damping is **distributed** across multiple collocated lanes (boost
  `FUN_00034a72`, magnitude `FUN_000352b4`) rather than concentrated here, one lane may not be enough and
  we escalate. And the confirmed-live **type-8** path (below) may be the better/primary target.

**V48-A′ — MUTE the "type-8" carrier (cal-only, one byte).** Set the mixer per-slot sum gate
`tp+0x5118[8]` = **`0xC4120`** from `1→0`, removing slot 8's command-delta feedback from `gp-0x6b4c`.
Does not touch `0xC646C` or forward authority. A clean, direct test of whether that carrier matters. ⚠
Gate before build: decompile `FUN_00027b0a` (a second reader of the same array) to confirm no
torque/DTC-relevant side effect; and note the carrier's *activity* is drive-history-dependent
(`FUN_0002caa2` latch), so a null could mean "muted successfully but the carrier wasn't active." Best run
as a combined shot with V48-A, or after the loop model says type-8 is the dominant carrier.

**V48-A″ — the DECOUPLE / Route-B idea (operator's "apply the 4× differently"): now assessed as
HYGIENE, NOT a vibration fix.** ⚠ Because Route B's forward lane `(4×setpoint × stock_gain)` equals V38's
`(setpoint × 4×gain)` product, the **delivered command `gp-0x6b98` is byte-identical to V38**, so every
unfiltered 21 Hz carrier (type-8 = a delta of `gp-0x6b98`; `FUN_0003a382` = reads the delivered-torque-
reflecting sensor) is **unchanged**. Only the explicitly-`0xC646C`-scaled paths change
(`FUN_00036682/36828`), and those are filtered (0.94 Hz) — no 21 Hz. **By the gain-rescaling-invariance
principle, re-splitting the 4× between gain and setpoint cannot move the vibration.** It remains worth
doing as *architecture hygiene* (removes an unintended 4× on a filtered lane) and is the right way to
"achieve 4× a cleaner way," but it is not a cure. (Feasibility/clamp-raise spec tracked separately;
16-bit overflow of a 4× setpoint is the main constraint.)

**V48-B (parallel, free, reversible — do alongside, not instead):** openpilot-side —
(i) **asymmetric `STEER_DELTA`** (rate-limit the rising edge only; community "removed 75–80% of jitter"),
(ii) lower the **sub-45-mph `_torque_lpf_tau`**, (iii) confirm the test rig is **not on an
oscillation-reverted lateral model**. These attack the several-Hz jitter/ratchet and cost nothing to try;
they will *not* by themselves kill a 21 Hz inner-loop mode (bandwidth), but they de-risk the outer loop
and may quiet the felt "ratchet."

### ★ Quantified loop-gain characterization (the "characterize before compensating" result)
Model: `analysis-2020accord/studies/models/eps_loop_gain_model.py` (runnable). Plant fitted to the measured Q=13.6 and
the 8× peaking; carriers modeled as the derivative/command-rate feedbacks that dominate at 21 Hz.

| build | \|L(21.4 Hz)\| | peaking | closed-loop Q | gain margin |
|---|---|---|---|---|
| stock 1× | 0.219 | 1.28× | 2.2 | 13.2 dB |
| 2× (V31) | 0.438 | 1.78× | 3.0 | 7.2 dB |
| **4× (V38)** | **0.875** | **8.0×** | **13.6** | **1.16 dB** |

- **The bare plant is only mildly resonant (Q≈1.7); ~88% of the felt Q=13.6 is FEEDBACK-INDUCED peaking.**
  The loop transmission at 21 Hz is real-positive (~0°) — **direct anti-damping** — because the carriers
  are command/torque-**rate** (derivative, +90°) feedbacks and the plant is −90° at its peak. That is
  *why* it peaks rather than merely tracks.
- **Self-excitation edge |L|→1 at 4.57×; palpable onset ~3.0×; usable ceiling ~2.6–3.0×** — matches
  "2× fine, 4× vibrates." 4× sits at 87.5% of the hard edge (1.16 dB margin) — strongly peaked but still
  decaying (finite Q), not a true limit cycle.
- **Route B ΔL(21 Hz) = 0.000** — confirmed quantitatively hygiene-only (no unfiltered gain-scaled carrier).

### Tier 2 — the OEM-standard fix, now DESIGNED (higher risk: a code cave)
- **V48-C: a NOTCH at 21.4 Hz on the torsion-bar / carrier-input signal.** De-aliasing is resolved from
  the data (ring-down τ = Q/πf = 0.202 s matches the measured 0.23 s; 78.6 Hz would be 0.055 s and need
  ~14× the torsion stiffness — not a wheel/column mode), so **center = 21.4 Hz.** Design: **6–8 dB depth,
  Q≈4–5** (BW ~4–5 Hz) → pulls |L| 0.875 → 0.35–0.44, **margin → 7–9 dB.** Phase cost at the forward
  crossover is negligible (−1.7° @ 5 Hz), so it does not threaten LKAS tracking. **Placement: on the
  torsion-bar signal BEFORE it fans out to the carriers** — attenuates every collocated carrier at once,
  sits OFF the safety-critical motor-command / DTC-0x1d lockstep path, and cannot eat forward-loop phase.
  ★ It is **split-independent — the only lever guaranteed to work regardless of which carrier dominates**
  — AND the **least feel-affecting** option (surgical at 21 Hz, DC assist untouched), which matches the
  operator's "avoid affecting steering feel" preference. Its only downside is that it requires a code cave
  — the kit's highest-risk change class (V24/V27 both faulted) — so it needs a dedicated adversarial
  pre-flash safety review.
- **V48-D: a COLLOCATED torque-rate damper** — bandpass `dτ/dt` of the torsion-bar torque (Sensor-B,
  which *is* collocated) around 21 Hz and feed it back with **damping** sign. Theoretically the cleanest
  cure. Note the firmware already has torque-derivative lanes (r24/r26) wired as *assist* (anti-damping);
  a collocated damper is the sign-correct version. Also a code cave (or a risky sign repurpose of
  r24/r26). Same safety bar as V48-C.

### Tier 3 — the guaranteed-but-unwanted fallback
**Reduce the LKAS gain toward the stability threshold** (the mode appeared between 2× and 4×, so ~2.5–3×
is likely stable). This is what the entire openpilot community does for this symptom. **Off the table by
the operator's constraint (keep 4×)** — documented only as the known-good fallback if Tiers 1–2 fail.

### Per-lever margin (from the model) — the decision table
| Lever | \|L\| → | margin → | cures the vibration when | risk |
|---|---|---|---|---|
| Route B (4× via setpoint, stock gain) | 0.875 (no change) | 1.16 dB | **never** (invariant) | cal + small code; hygiene only |
| Mute type-8 (`0xC4120` byte 1→0) | 0.35–0.61 | 4.3–9.1 dB | type-8 ≥ ~50% of loop gain | cal-only (needs `FUN_00027b0a` check) |
| Cut `FUN_0003a382` `uVar27` (`0xC67B8/BA/BC`→0) | 0.35–0.61 | 4.3–9.1 dB | `a382` ≥ ~50% of loop gain | cal-only (confirmed clean) |
| **Mute type-8 AND cut `a382`** | **~0.25–0.32** | **10–12 dB** | if these two ARE the carriers | cal-only |
| **Notch 21.4 Hz, 8 dB, Q5** | **0.348** | **9.2 dB** | **ANY split (guaranteed)** | **code cave** |
| Reduce gain to ~2.6–3× | ≤0.5 | ≥6 dB | always | cal-only, but SACRIFICES 4× (rejected) |

### ⚠ RESULT (2026-07-21): V48A FLASHED → did NOT fix the vibration
V48A muted BOTH the type-8 carrier (`0xC4120`) AND attenuated `FUN_0003a382` (`uVar27` ×0.25) — the two
strongest identified carriers — and the vibration was unchanged. Per the per-lever table below, a null
means these two do **not** dominate the 21 Hz loop gain: the anti-damping is **distributed** across more
lanes (boost / magnitude / damper / r24-r26) and/or the type-8 latch was inactive. **This is the model's
"→ notch" branch:** the split-independent 21.4 Hz notch (V48-C, now a validated design — biquad DF-I Q12,
`analysis-2020accord/studies/models/eps_v48b_notch_design.py`) is the remaining lever, since it attenuates the shared
torsion-bar input ahead of ALL sensor-reading carriers at once. See
`docs/handoffs/2026-07/HANDOFF-2026-07-21-v48-vibration-loopgain-notch.md`.

### ✅ V48B (the notch) is now BUILT + GHIDRA-VERIFIED, UNFLASHED (2026-07-21 late)
The notch is no longer just a design — it is a built candidate. `analysis-2020accord/builds/v18_v49/build_v48b_tva.py`
(+ `studies/caves/v48b_cave_asm.py`, `studies/models/eps_v48b_cave_model.py`): V38 + ratchet + a **138-byte, 41-instruction code cave
at `0xC4B34`** that runs the DF-I Q12 biquad on a fresh read of `gp-0x4f60` and stores the filtered copy
to a new RAM cell `gp-0x1500`; a 4-byte trampoline `jr` at `0x7FEAC` (displaces `cmp r0,r8`/`mov r8,r14`,
re-executed **last** so the `bge` at `0x7feb0` sees the correct flags); and **7 live carrier repoints**
`gp-0x4f60`→`gp-0x1500` (`FUN_0002c478` @2c480, `FUN_000352b4` @354d2/@35aa4, `FUN_0003a382` @3a6ca/@3a7ca,
`FUN_0003b49a` @3b4a8, `FUN_0003b66a` @3b672). The 2 **dormant** mode-gated reads (`0x34392`/`0x34ace`)
are left raw (they are the dormant fallback arm of a cal-gated mux, `0xC6498/99`=1) — the red-team
confirmed leaving them raw is correct. Raw `gp-0x4f60`, its shadow, the 2 hard-shutdown monitors, and the
2 CAN broadcasts are untouched. State RAM: y1/out=`gp-0x1500` (V31P flash-validated), x1/x2/y2=
`gp-0x14FC/FA/F8`. Verification: **50/50 CRC** (single MAIN block) + RWD round-trip, and **every code edit
re-disassembled in Ghidra from the built image** (cave = 41 correct instrs; trampoline `jr 0xC4B34`;
return path `bge`/`subr` intact; repoint `ld.h -0x1500[gp]` reg preserved; ratchet `br`). Notch is
**exactly unity at DC** (73/73 → zero steady torque offset). Adversarial review: type-8 lockstep
`FUN_00027b0a` = matched-safe (both sides trace to the one filtered read); all other lane consumers have
zero raw `gp-0x4f60` reads; corridor monitors read raw and are envelope checks (attenuation adds margin).
**All monitor-asymmetry items CLOSED, SAFE:** the DTC-0x1c/0x1d corridor pair (`FUN_00042af8`/
`FUN_00043e44`) is a matched int/float lockstep — both recompute the same cal-gated formula from the same
already-notched `gp-0x6b4a` cell (±5-count tolerance), so a shared-input perturbation cannot erode their
agreement, and a strictly-attenuating notch only shrinks the per-tick delta. No raw-vs-filtered
divergence-trip mechanism exists at any monitor. See `docs/handoffs/2026-07/HANDOFF-2026-07-21-v48b-notch-build.md`.
**CODE CAVE = the kit's only bricked class (V24/V27); the ultimate check is first-minutes on-car
observation — flash only on explicit operator instruction naming the file + bus.**

### Recommendation — a two-step plan, operator picks the entry point
1. **V48 (cal-only, low risk): the COMBINED carrier mute — mute type-8 (`0xC4120`) + cut `FUN_0003a382`
   `uVar27` (`0xC67B8/BA/BC`).** The model puts this at 10–12 dB margin *if* these two are the dominant
   carriers — a strong fix — and it keeps 4×, is fully reversible, and touches no safety-critical path
   (pending the one `FUN_00027b0a` collateral check on the type-8 gate). Run **V48-B** (openpilot-side
   asymmetric `STEER_DELTA` / LPF-tau) in parallel for free. If it fully clears the vibration → done.
2. **If V48 is null or partial → V49 = the DESIGNED NOTCH (Tier 2).** A null means the anti-damping is
   distributed across more lanes than these two, and only the notch (which attenuates the shared
   torsion-bar input ahead of *all* carriers) is guaranteed. It is now a *designed* filter (21.4 Hz,
   8 dB, Q5, torsion-bar placement) — the operator's "characterize before compensating" condition is met —
   but it is a code cave and needs a full adversarial safety review before flash.

> **The operator may prefer to go straight to the notch.** It is the only *guaranteed* lever, it is the
> *least* feel-affecting (surgical at 21 Hz), and the loop is now characterized so the design is not a
> guess. The single reason to try the cal-only combined mute first is that it avoids the code-cave risk
> class entirely — this is a genuine risk/reward call and it is the operator's.

> **Why not keep opening the damper (V47 direction)?** §3.3 + the model prove it is non-collocated and
> ~0° anti-damping — the one direction control theory says cannot succeed at any gain. V47's on-car null
> is that prediction confirmed. **Do not spend another flash on the motor-rate damper.**

---

## 11. THE RATCHET — two distinct phenomena
- **Ratchet #1 (SOLVED):** the **state-4 governor substitution** in `FUN_0004503c` (while `gp-0x67fa==4`
  the command magnitude can only decrease, written back cumulatively). Fixed by one byte at `0x454FE`
  (`bne→br`), **confirmed on-car in the V42 drive**, carried through every build since. This is the
  hard-turn ratchet, especially after a stop.
- **Ratchet #2 (a vibration symptom, UNSOLVED):** the operator's 2026-07-21 report that "the vibration
  creates its own ratchet." A high-Q limit cycle *is* a stepwise, catching resistance at the wheel — the
  21 Hz ring modulating the delivered torque reads as a ratchet/notchy feel. **This one will not resolve
  until the vibration does.** It does *not* impugn the Ratchet #1 fix (a different mechanism, confirmed);
  it means we should expect the residual "ratcheting" to disappear together with the vibration when a
  Tier-1/2 fix lands.

---

## 12. STANDING GUIDANCE FOR THE NEXT BUILDER
- **Do not tune the motor-rate damper (Factor E / `FUN_00034350`) for the vibration again** — it is
  non-collocated (§3.3); V44/V47 nulls are that prediction confirmed.
- **Do not edit one stage of `FUN_0003a382` in isolation** — move both poles together or not at all.
- **Never edit the damper int clamp (`0xD209C/0xD20A8`) without a bit-exact float-mirror edit
  (`0xC6554/58/5C/60`)** — no-debounce DTC-0x1d hard shutdown.
- **The safe, successful change class here is cal-only** (V29/V31/V37/V42-ch1). Code caves have a 100%
  fault record in this kit (V24/V27) — Tier 2 requires a dedicated adversarial safety review before flash.
- **Highest-value data to unblock everything: a 2–10 mph hands-off log of `gp-0x6ac0` / the internal
  command** (the regime route b9 can't see).
