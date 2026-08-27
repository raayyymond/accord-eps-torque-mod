# V66 / V67 design note — the LKAS-gated rate lane

**Status: DESIGN, 2026-08-01.** Written by the orchestrator; every firmware fact below was verified
first-hand (Ghidra decompile + raw byte scan), not relayed. Data-dependent numbers are marked
**[PENDING DATA]** and must be filled from the route `3a`/`3b` analysis before either build is flashed.

---

## The problem, in one paragraph

V62 (`sar 0xa` → `sar 0x9` on the r24 torsion-bar torque-RATE lane) **fixed the 20.9 Hz LKAS-engaged
grinding** — the kit's first measured fix, 8× at creep and 42× at |rate| 16–32 deg/s. The operator
reports it **introduced a second symptom** ("grind #2"): a whole-car resonance at low speed under
significant *driver* steering input, also felt at 10–20 mph on semi-hard turns, and **present with LKAS
off**. V65 carries V62's control-path edits byte-identical, so grind #2 is present on the current build.

The mechanism is arithmetic, not mysterious. `gp-0x4f62` is a **4-sample finite difference** at 1 kHz
(`2*(x[n] − x[n−4])/4`, delay cal `0xC6C42` = 4, byte-read). Its magnitude at 41.6 Hz is **1.93×** its
magnitude at 20.9 Hz, and at 58.9 Hz it is **2.60×** — a differentiator's gain *rises* with frequency.
V62's ×2 is flat in frequency, so it raised the high band harder, in absolute terms, than the mode it
fixed. The V62 build note computed selectivity only against the **driver** (1 Hz, 14.6:1) and never
against a **higher** mode, where the ratio runs the wrong way.
Full arithmetic: `analysis-2020accord/studies/models/rate_lane_frequency_response.py`.

---

## ★★★ THE ON-CAR EVIDENCE — and it lives in the TAIL, not the mean

🛑 **THE MEAN SAYS NOTHING HAPPENED. THE TAIL SAYS 12× WITH A DOSE-RESPONSE AND A REPLICATION.**
Anyone re-reading this must not stop at the first table.

**Matched-cell, episode-bootstrapped mean, Kd = 2× vs Kd = 1×:**

| band | ratio [95%] | read |
|---|---|---|
| **18–22 Hz (grind #1)** | **0.555 [0.467, 0.685]** | ✅ the V62 fix is real and replicates on V65 |
| 30–49 Hz (grind #2 band) | **0.913 [0.791, 1.026]** | inside the split-half null floor ⇒ **no elevation** |
| 1–4 / 6–9 / 10–16 / 24–28 Hz | 0.888 / 1.017 / 0.868 / 0.797 | controls |

**The extreme tail, same data, blocks not windows:**

| build | Kd | blocks | **burst blocks** | max |
|---|---|---|---|---|
| V61 `r31` | **0** | 22 | **0** | 362 |
| V59 `r2c` | **1×** | 53 | **1** | 448 |
| V64 `r35` | **1×** | 16 | **0** | 314 |
| V62 `r37` | **2×** | 89 | **9** | 3837 |
| **V65 `r3a`** | **2×** | 40 | **10** | **4046** |
| **V65 `r3b`** | **2×** | 90 | **8** | 3024 |

⇒ **27/219 blocks at Kd = 2× vs 1/91 at Kd ≤ 1×**, maximum **325 → 4046 (12.4×)**. Block-level
Fisher **p = 7.8e-4**, and an **FFT-free zigzag detector agrees independently** (p = 0.0072 in the
provocation cell) — so the effect is not an artifact of spectral estimation.

### ★★★★ THE BAND-SPECIFICITY TEST — and it is the root-cause identification

Corner-conditioned extreme-tail maxima, Kd = 1× vs Kd = 2×, 219 blocks:

| band | max Kd=1× | max Kd=2× | **ratio** | p |
|---|---|---|---|---|
| 1–4 Hz (driver) | 4709 | 4763 | **1.01** | 1.00 |
| 6–9 Hz (ratchet) | 2773 | 3335 | 1.20 | 0.037 |
| 10–16 Hz | 2520 | 2005 | **0.80** | 1.00 |
| **18–22 Hz (GRIND #1)** | 3656 | 1269 | **0.35** | 1.00 |
| 24–28 Hz | 485 | 1289 | **2.66** | 0.013 |
| 30–40 Hz | 373 | 1113 | **2.98** | 0.013 |
| **40–49 Hz (GRIND #2)** | 301 | **3526** | **11.71** | **0.0003** |

⇒ ★★★★ **A MONOTONE FREQUENCY RESPONSE WITH A CROSSOVER BETWEEN 22 AND 24 Hz.**
`0.80 → 0.35 → 2.66 → 2.98 → 11.71`, with **1–4 Hz flat at 1.01** as a control. This is **not generic
roughness** — the driver band and 10–16 Hz are untouched or down.

**This is exactly what doubling a finite-difference derivative does** in a loop whose phase margin
degrades with frequency: below the crossover the lane is a damper and the ×2 helps; above it the lane
is an amplifier and the ×2 hurts, increasingly with frequency. The prediction was made from the
arithmetic *before* this test was run (`studies/models/rate_lane_frequency_response.py` gives 1.93× more lane gain at
41.6 Hz than at 20.9 Hz), and the measurement is steeper still because the plant has a lightly-damped
mode at ~44.9 Hz, Q ≈ 37, that the extra loop gain pushes past its stability threshold — hence
**bursts** rather than a hum, and hence **zero** bursts at Kd = 0 and Kd = 1×.

⇒ **V62 cut grind #1 by 2.9× and raised grind #2 by 11.7×. That is the root cause, and it is one
knob doing both.**

### Why the attribution survived the confounds

Three things had to be checked; **all three came back for the mechanism**:

1. **`3a` and `3b` are PROVOKED routes.** The operator drove them *deliberately to demonstrate grind
   #2*. They cannot be evidence that the burst *rate* rose. Only **V62 route `37`** (ordinary driving)
   is a fair high-dose sample, and on its own it is **9/89 vs 1/91** — suggestive, not decisive.
2. **The matched-cell exceedance analysis says the OPPOSITE**, at every threshold:
   30–49 Hz ratios 0.924 / 0.549 / 0.540 / 0.642 / 0.544 at q50…q99 — Kd = 2× has *fewer*
   exceedances. ⚠ The reconciliation is that **the matched thresholds never reach the burst
   amplitudes**: the matched q99 threshold is **317** while the bursts are **3000–4000**. The matched
   analysis describes the bulk and is structurally blind to the phenomenon.

   ✅ **AND THE EXPOSURE EXPLANATION IS DEAD — measured, not argued.** Seconds spent in grind #2's
   corner (creep ∧ |driver torque| ≥ 1200 ∧ |angle| ≥ 100°), read straight off the caches:

   | build | Kd | corner s |
   |---|---|---|
   | V61 `r31` | 0 | 43.1 |
   | V59 `r2c` | 1× | 36.8 |
   | V64 `r35` | 1× | 25.4 |
   | **pooled Kd ≤ 1×** | | **105.3** |
   | **V62 `r37`** (ordinary driving) | **2×** | **49.8** |
   | V65 `r3a` / `r3b` | 2× | 111.7 / 64.9 — **provoked, excluded from rate claims** |

   The low-dose arm had **more than twice** V62's exposure in exactly that corner and produced
   **1 burst block** (maxima 362 / 448 / 314) against V62's **9** (max 3837). ⇒ *"they never went
   there"* is refuted. Rough rate 0.0095/s vs 0.181/s ≈ **19×**, Poisson p ≈ 0.008 on 1 vs 9.
3. **The UNMASKING hypothesis is weakened but not dead.** V62 removed the 21 Hz grinding, so the
   operator may now *notice* a vibration that was always present. But unmasking predicts the
   **amplitude** is flat with dose, and the corner maxima are **362 / 448 / 314 → 3837**, an 8.6×
   rise. Perception cannot move a number. What survives of the hypothesis is only that *some* of the
   salience change is unmasking.

### ✅ A REAL DEFECT FOUND AND FIXED IN THE MEASUREMENT ITSELF — and it invalidates earlier numbers

`_r31_common.band_envelope`, the function every prior session used for band envelopes, **subtracts only
the mean and applies no taper.** On a high-effort window the driver's own torque **ramp** has a 1/f
spectrum plus a rectangular-window discontinuity, and both leak into 30–49 Hz **in proportion to the
ramp — i.e. in proportion to driver effort**, which is precisely the covariate that separates these
routes. Demonstrated on one V65 burst: the **steering-ANGLE** channel, which is visibly smooth,
reported a **35.8 deg "30–49 Hz envelope"** that was pure leakage.

⇒ Every number in this document uses a replacement (`_grind2_lib.win_env`): **linear detrend, Hann
taper, read the central 60% with the taper divided back out**, plus two independent cross-checks — an
**FFT-free zigzag/threshold-crossing counter** and the **steering-angle channel as a leakage control**.
🛑 **Prior 30–49 Hz numbers computed with `band_envelope` are inflated on high-effort windows** — that
includes the V62 handoff's "rank every engaged window by 30–49 Hz env99" instance table. **Re-derive
before quoting any of them.**

✅ **The band-specificity test — the one that could have overturned it — PASSED.** See the table above:
1–4 Hz flat, 10–16 Hz down, the effect confined to 24 Hz and above and rising monotonically with
frequency. Generic roughness is excluded.

⚠ **What is still weak, stated honestly:** conditioned strictly on the corner, V62's *unprovoked*
route contributes **1 burst block in 47.1 s** against **0 in 104.4 s** at Kd ≤ 1×. On counts alone that
is not significant. **The weight is carried by the AMPLITUDE ratios in the band table, not by the burst
count** — and those have p = 0.0003 at 40–49 Hz over 219 blocks. Quote the amplitudes.

⇒ ★★ **V66 IS ALSO THE CONFIRMATORY INTERVENTION, and it costs nothing.** The operator asked for a
stock-rate-lane build for unrelated reasons (a long stable drive), and that build reverts the one knob.
**Pre-commit the reading now, before the drive: if grind #2 disappears on V66 the attribution is
closed; if it persists, the rate lane is the wrong tree** and the target becomes a ~44.9 Hz mechanical
mode in its own right — in which case the `sar` revert traded a proven fix for nothing and V62 should
go back on.

🛑 **METHODOLOGICAL NOTE, for the standing conventions:** the matched-cell mean is a *mean* statistic,
and the kit already records that *"mean Welch power is the wrong statistic for a bursty limit cycle."*
A mean ratio of **0.913 with a tight CI reads as a confident null** and would have closed a real
effect unexamined. Equally, a burst census with unmatched exposure reads as a confident positive.
**Report both, state which population each describes, and never let one stand alone.**

---

## 🛑 WHAT SEPARATES THE TWO SYMPTOMS — measured, and it is NOT what was assumed

Creep windows only (v < 4 m/s), routes `3a` + `3b`, n = 946, 517 engaged (base rate 54.7%):

| band | top-decile windows engaged | engaged/disengaged p99 |
|---|---|---|
| **18–22 Hz (grind #1)** | **100.0%** | **6.63×** |
| **30–49 Hz (grind #2)** | 84.5% | **1.33×** |

⇒ **Grind #1 is strongly LKAS-gated. Grind #2 is barely.** The operator's report — *"happens
regardless of LKAS engagement"* — is confirmed.
🛑 **CONSEQUENCE: gating the fix on LKAS alone CANNOT remove grind #2.** It would only remove it from
disengaged driving. The requirement *"decidedly LKAS-dependent"* was formed before this was known; it
still matters for **not disturbing base steering**, but it is no longer sufficient on its own.

⚠ **Steering rate separates them only ~2×**, not the 6.6× a first pass suggested. Restricted to creep:
30–49 Hz top decile rate p10/med/p90 = 32 / **256** / 371 raw `0x14A` counts; 18–22 Hz = 26 / **128** /
359. **The p90s overlap.** The 6.6× came from a top-25 selection that let grind #1's road-speed windows
(median v 8.41 m/s) into the comparison — a confound, caught and withdrawn.

★ **What DOES separate them is DRIVER TORQUE.** Grind #1 is the hands-off creep mode (sustained effort
≤ 200). The grind #2 windows carry `tq_avg` **1600–2700** at |angle| 150–265° — the driver cranking the
wheel. That is a **>8×** separation, and it is the axis a gate should use.

🛑 **A filter cannot fix this.** A differentiator rises at +20 dB/dec and one real pole falls at
−20 dB/dec, so the cascade is **flat** above the corner: a single pole drives the 41.6/20.9 selectivity
toward 1.0 and can never push it below. Two poles placed low enough to bite by 42 Hz cost
≈2·atan(20.9/fc) of phase at 20.9 Hz — at fc = 20 Hz that is −92°, which turns the lane's +75° lead into
−17° and **destroys the 20.9 Hz damping V62 bought**. The dirty-derivative idea is dead on structure,
not on numbers. **Do not re-propose it.** (Raising the delay cal `0xC6C42` is dead for the same reason:
D = 24 puts an exact zero on 41.7 Hz but leaves the lane at −0.3° phase at 20.9 Hz, i.e. a pure spring.)

⇒ The separation must come from a **variable that differs between the two symptoms**, not from frequency.

---

## 🛑 The alias, stated up front

The torsion-bar channel is sampled on the ~100.5 Hz `0x14A`/`0x18F` grid ⇒ **Nyquist 50 Hz**, so
**41.64 Hz and 58.86 Hz are the same observation** and no rlog analysis can separate them. Every number
above is given for both, and the ranking of every candidate fix is the same for both — which is the
argument for acting without resolving it. Two ways to resolve it are being tried (the comma IMU on its
own sample rate; Lomb–Scargle on true arrival timestamps) and a third needs a firmware probe.
**No conclusion here may depend on the frequency being 41.6 rather than 58.9.**

---

## ★★ The firmware already has an LKAS-conditional gain arm for r24. It is wired to a dead cell.

All of this is **EVIDENCE**, verified by the orchestrator this session:

| fact | how |
|---|---|
| `gp-0x683c` has **exactly one access image-wide**: `ld.bu -0x683c[gp],r15` @`0x3AA94`, bytes `84 7f c5 97`. **Zero writers.** Zero extended-displacement hits. | raw byte scan with per-opcode displacement rules, self-check pinned on `gp-0x6b94` (`analysis-2020accord/studies/firmware_scan/scan_gp_accesses.py`) |
| Its only consumer is `cmp r0,r15` @`0x3AAA6` / `setfne lp` @`0x3AAA8`. **r15 is dead after that** — reused by `mov r13,r15` @`0x3AAD4`. | Ghidra assembly context |
| `lp` gates **both** rate lanes: r24 `ld.hu 0x7446[tp],r10` @`0x3AC08` (cal `0xC6446`), r26 `ld.hu 0x7444[tp],r8` @`0x3AB5E` (cal `0xC6444`) | Ghidra |
| r24 priority @`0x3ABFA`–`0x3AC16`: `gp-0x671d` → `0xC6442`(1024), **then** `lp` → `0xC6446`(512), **then** `gp-0x671a ≥ CEIL` → `0xC6440`(2048), **else** the LERP | Ghidra |
| `0xC6446` and `0xC6444` each have **exactly one reader** image-wide | raw tp-relative byte scan |
| `FUN_00028ea6` (arbitration, writes `gp-0x6806`) is called @`0x22522`; `FUN_0003aa2c` @`0x2291E` ⇒ **arbitration runs first on every tick that runs both** | Ghidra |
| `gp-0x6806` writers in `FUN_00028ea6` store literal **1** (@`0x293A6`, from `mov 0x1,r6`) and literal **0** (@`0x029696`, `st.b r0`) | Ghidra |

⇒ **Repointing one load makes `0xC6446` an LKAS-only gain override for r24.**

```
0x3AA94   84 7f c5 97   ld.bu -0x683c[gp],r15      CURRENT (dead cell)
0x3AA94   84 7f fb 97   ld.bu -0x6806[gp],r15      PROPOSED  -- ONE BYTE, at 0x3AA96
0x02A1B6  84 67 fb 97   ld.bu -0x6806[gp],r12      a REAL instruction, differs only in reg2
```
`-0x6806` = `0x97FA` is **even**, so on V850 `ld.bu` (displacement bit 0 lives in **hw1 bit 5**, not
hw2) the opcode field, both register fields, and the high displacement byte are all untouched.

**GATE 1 is vacuous** — read-only, no cave, no new RAM cell, no new opcode.
**GATE 2** is the argument below.

---

## V67 — V66 PLUS the grind #1 fix, gated on LKAS

**Operator's design, 2026-08-01, and it is the right shape.** Building on **V66** rather than on V65
inverts the gate polarity usefully: the `sar` stays **stock**, so *gate false* is byte-for-byte stock
behaviour, and the boost is something the arm *adds* rather than something it *cancels*.

| # | site | from | to | what |
|---|---|---|---|---|
| 1 | `0x3AA96` | `c5` | `fb` | repoint `ld.bu -0x683c[gp],r15` → `ld.bu -0x6806[gp],r15`. **ONE BYTE** |
| 2 | `0xC6446` | 512 | **5244** | = 2.00× the LERP at grind #1's operating point (creep 7.2 km/h, 128 deg/s ⇒ LERP 2622) |
| — | `0x3AC20`, `0x3AB76` | — | **stock `aa`** | V66's reverts are **kept** |

- **LKAS off** → arm not taken → LERP × 1 ⇒ **exactly stock, every condition.** The
  *"not affecting base steering"* requirement met exactly rather than approximately.
- **LKAS on** → flat 5244 ⇒ **2.00× at grind #1's operating point**, i.e. V62's proven fix.

Arithmetic: `5120 × 5244 = 26.8 M` = **1.25% of INT32_MAX**; the lane saturates at |dtorque| ≥ 1599
against a measured 123–839. `0xC6444` (r26's arm, same gate) stays stock 512 — r26 is inert.

### ✅✅ THE GATE IS VALIDATED ON-CAR — from data that was already on disk

**V57's own probe put `(gp-0x6806 == 0)` on `0x14A` byte4 bit6 and flew routes `28` and `29` in July.
Nobody had correlated it.** Decoded 2026-08-01:

| | route `29` | route `28` |
|---|---|---|
| frames / span | 7,924 / 79.2 s | 29,990 / 299.9 s |
| **agreement with `carControl.latActive`** | **99.90%** (8 frames disagree) | **99.94%** (17 frames) |
| duty | 21.73% | 49.88% |
| **transitions** | **4 in 79.2 s = 0.0505/s** | **9 in 299.9 s = 0.0300/s** |

1. ✅ `gp-0x6806 != 0` ⟺ **LKAS is applying**. Polarity confirmed, at two very different duty cycles.
2. ✅ **It does NOT drop out during steady engaged holding** — the one structural ambiguity a trace
   had flagged (the cell is a ramp-FSM phase flag, `= 0` for "settled" phases 5/6/7, and static
   analysis could not rule out those occurring mid-drive). 99.9% agreement over 37,914 frames says
   they do not. **Measurement closed what structure could not.**
3. ✅ **The parametric-pump kill criterion passes with enormous margin** — 0.03–0.05 toggles/s against
   modes at 21 and 45 Hz, **three orders of magnitude**.

⇒ **V67 does not have to wait for V66's drive.** The gate is the part that could have made it inert,
and it is closed.

🛑 The lesson is about where to look: this measurement existed since July while every session treated
the polarity as an open Ghidra question. **Before tracing a signal, check whether a past probe already
flew on it** — `BUILD-LINEAGE.md` lists every probe payload and `lib/route_build_registry.py` maps every
route to its build.

### 🛑 What it costs, stated plainly

**Grind #2 SURVIVES under LKAS**, and at 2.21× — slightly *more* than V62's 2.00×, because a scalar
arm does not follow the LERP's own rolloff (it drifts ~1.8× at the slowest creep to ~2.7× at road
speed with a fast wheel). `0xC6446` is one halfword, so it is trivially re-tunable after a drive.

### 🛑 NO AVAILABLE AXIS CLEANLY SEPARATES THE TWO SYMPTOMS — measured, creep, top decile of each

| axis | grind #1 | grind #2 | best single threshold: keep #1 boosted / remove #2 |
|---|---|---|---|
| **LKAS engaged** | **98.7%** | 84.3% (base rate 54.7%) | **98.7% / 15.7%** ← V67 uses this |
| driver torque | median 1268 | median 2158 (**1.70×**) | 96.8% / 50.5% |
| steering rate (**the LERP's own axis**) | median 128 deg/s | median 256 (**2.00×**) | 81.1% / 48.5% |

🛑 **CORRECTION.** An earlier pass in this document said driver torque separates the symptoms
**">8×"**. **It does not.** That number compared grind #2's *measured* torque (1600–2700) against the
*definition* of hands-off (≤ 200) rather than against grind #1's *measured* distribution. The real
separation is **1.70×**, with heavy overlap.

⇒ LKAS preserves grind #1's fix best (98.7%) and is the only axis that leaves base steering exactly
stock. It removes grind #2 only where LKAS is off — **15.7% of these PROVOKED test windows**, but
these routes are 54.7% engaged *because they were test routes*; ordinary driving is mostly LKAS-off,
so in practice it removes grind #2 from most real driving.

## Why not just edit the LERP instead?

You can — it is **cal-only** (no code edit at all), mode-10-private, one CRC block (**#41**,
`[0xD2000,0xD2FFC)`), and in that one respect **safer** than the repoint. It was not chosen for three
reasons, in order of weight:

1. **The rate axis is the WEAKEST discriminator of the three.** Its best possible threshold keeps
   81.1% of grind #1 boosted while removing only **48.5%** of grind #2 — *half* the grind #2
   population sits below any threshold that preserves grind #1. The medians differ 2.00× and the
   distributions overlap heavily (p90s 359 vs 371 counts).
2. **It changes base steering at ALL times** — the LERP is the *default* arm, used in every condition,
   LKAS or not. That is precisely what a gate avoids and what the operator asked to avoid.
3. **Bigger surface**: 4 records × 8 halfwords = 32 halfwords plus CRC, versus one byte and one
   halfword. ⚠ And `builds/v50_v79/build_v62_tva.py`'s tripwire watches only 2 of the 4 records, so an edit landing
   on `0xD2A74` or `0xD2AB0` would go unnoticed by the existing gates.

⚠ It is **not closed** — it remains a legitimate cal-only lever, and it is mutually exclusive with
the gate (when the arm is taken the LERP is discarded entirely, so the two cannot compose). If the
LKAS gate proves unusable it is the fallback, at roughly half effectiveness.

### ✅ RESOLVED — the gate cell is `gp-0x6806`, and the candidate field is closed

**Superseded but kept for provenance.** This section read *"the gate cell is NOT yet chosen, and
choosing it wrong is the whole risk"* until `gp-0x6806` was validated on-car from V57's July probe
(see above: 99.90–99.94% agreement with `latActive`, 0.03–0.05 transitions/s). The two rivals below
are now moot for V67 and are left as the record of why:
- `gp-0x67f5`'s chatter risk was never measured and no longer needs to be — ⚠ and the ">8×" claim in
  its row is **WITHDRAWN** (the real driver-torque separation is **1.70×**, see the table above).
- `gp-0x67fe`'s semantic dispute is **still open**; V66's probe would settle it if that build ever flies.

| candidate | what it is | status |
|---|---|---|
| **`gp-0x67f5`** | governor slew-step selector, written only by the column-torque voter `FUN_00041eec`: driver torque ≥ cal `0xC531E` (1062) sustained cal `0xC64E7` (10) cycles | ★ **leading on the physics** — exactly the hands-on discriminator, and driver torque is the axis that separates the symptoms >8×. 🛑🛑 **KILL CRITERION: chatter.** The oscillation puts **±1400 counts** on the torsion bar; at 1 kHz a 10-cycle sustain is **10 ms** against a 21 Hz half-period of 24 ms — **the mode's own amplitude can satisfy it**, switching the gain at the mode frequency. That is a parametric pump. **Must be measured on-car before use.** |
| **`gp-0x67fe`** | reported by a trace as the **LKAS engage state-machine's state byte** — sole writer `FUN_0003bd7c` (4 `st.b` @`0x3BDB8/0x3BE4E/0x3BE5A/0x3BE7A`), `==0` = assist down, `∈{1,2}` = up; even displacement `0x9802`; fresh in the tick | 🛑 **SEMANTICS DISPUTED.** `model/eps_lkas_chain_model.py` calls the same cell `assist_substate` — **BASE assist**, not LKAS. If that is right it is non-zero whenever the car is running and is **worthless as a gate.** One bit of on-car duty settles it: ≈100% ⇒ useless; tracks engagement ⇒ the best candidate found. **Do not resolve this by argument.** |
| **`gp-0x6806`** | the LKAS enable; `STEER_CONTROL_ACTIVE` on CAN `0x18F` byte4 bit3 is sourced from it. Polarity resolved from the instruction (`0x2A1B6`–`0x2A1BC`): the deadband block runs **only when `gp-0x6806 == 0`**. Prior on-car: 96.26% high, **2 transitions in 180 s** | ✅ **CHOSEN.** Safe on chatter by a 3-orders-of-magnitude margin, and now measured to track engagement at 99.9%. ⚠ It still **cannot remove grind #2 under LKAS** — only the disengaged share. That is V67's stated cost, not a surprise |

**Rejected, with reasons** — `gp-0x6807` (`STEER_STATUS`: multi-valued, and value 3 is the speed-gated
*lockout*, the opposite of "applying"; odd displacement); `gp-0x67a4` (⚠ **corrects the record's "zero
readers"** — it has 1 writer + 1 reader and is a **saturation-dwell** monitor on the LKAS command's
clamp ceiling, not an engagement flag); `gp-0x6b4c` (signed halfword, crosses zero during ordinary
lane-keeping).

### 🛑 A RISK TO V67 THAT GOT SHARPER, NOT SOFTER

`gp-0x671d` **strictly outranks** the repointed arm — pinned at instruction level: `0x3ABFA cmp r0,r6`
/ `0x3ABFC be 0x3AC04`, so if `gp-0x671d != 0` control falls through to `0xC6442` = **1024** and the
`gp-0x683c` test at `0x3AC04` is **never reached at all**. 1024 is *below* the LERP default (3072 at
creep), so a firing `gp-0x671d` does not merely mask V67's arm — it **cuts the lane to a third**.

⚠ Unlike `gp-0x683c`, **`gp-0x671d` is LIVE**: two static `st.b` writers, `FUN_0003bcb2` @`0x3BD2A`
(writes 0) and `FUN_00041d56` @`0x41EC6` (writes a computed value). Its producer is a 3-state float
filter over `gp-0x501c` and `gp-0x4fd8` — **resolver/FOC domain, not LKAS** (`gp-0x4fd8` scales by
0.0015339808 ≈ 2π/4096, i.e. radians per count of a 4096-count/rev resolver).
🛑 **Domain is not the same as immunity.** A resolver-domain event counter can perfectly well fire
*during a 21 or 45 Hz mechanical oscillation* — which would mask V67's arm **exactly when it is needed
most**. V64's probe read it 0 across 14,980 frames, but that route was 149.8 s of creep.
⚠ **V66 does not measure it** — the third rung went to `gp-0x67fe`. This is the largest unmeasured
risk in the V67 design and it should be closed before or alongside the flash.

### Units for any breakpoint move — now exact

`gp-0x6ac0` is **`|gp-0x6abe|`**, verified at instruction level: both come from one EMA accumulator in
`FUN_00041464` (`gp-0x6abe = state >> 10`, `gp-0x6ac0 = abs(state) >> 10`). Same signal, same scale.
The **4.7121 counts per deg/s** figure was independently reproduced this session as an exact rational —
`2^18 / (48 × 1159) = 16384/3477 = 4.71210813…` — so the mode-10 breakpoints are:

| raw | deg/s |
|---|---|
| 400 | **84.89** |
| 1400 (array1 / 10 km/h record only) | **297.11** |
| 1500 | **318.33** |
| 3000 | **636.66** |

⚠ **A genuine step discontinuity at the top.** `0x3AAC8`/`0x3AACC` folds a rate **≥ 13001** to **0**,
and 0 is the LERP's *first* breakpoint ⇒ **maximum** gain. 13001 counts = **2759 deg/s** (~7.7 wheel
rev/s), so it is fault/glitch-level and not ordinary driving — but it is real, it doubles the gain
(array1 jumps 1.5× → 3.0×), and anyone moving breakpoints near the top of the axis must know it exists.

⚠ Two further structural residuals worth carrying: **`FUN_0003aa2c` is itself state-gated** (its caller
invokes it only when the one-hot `gp-0x67fa` falls in mask `0xC30`), and **`gp-0x67ac`'s trigger is
still unresolved** — if it is ever 1, r24/r26 **and six other lanes** silently drop out of the sum.

✅ **Two structural questions closed by the same trace:** there is **no V57-style cal fork** for r24 —
the torque sensor `gp-0x4f60` is a *single physical measurement* of driver and motor-reaction torque
combined, so no earlier tap separates them (unlike `0xC646C`'s six independent read sites). And
`gp-0x4f62`'s producer `FUN_0007e74a` contains **no EMA or IIR anywhere** — the dirty-derivative
low-pass does not exist in stock and would have to be *built*, i.e. a cave. Both confirm that gating,
not filtering, is the only route.

⇒ **V66 exists to answer this.** Its probe puts `gp-0x6806` on bit 6 and `gp-0x67f5` on bit 5 and
measures their **toggle rates** over a long drive. **Do not flash V67 until that is in.**
This is the V64 lesson applied in advance: *probe the gate, not just the output.*

---

## V68 — the no-gate fallback: reduce the DOSE instead of gating it

If no gate cell survives the chatter test, the remaining lever is to **turn the knob less far**. The
evidence that this could work is that the side effect looks like a **threshold**: burst blocks are
**0 at Kd = 0, 0 at Kd = 1×, 8 at Kd = 2×**, and corner p95 goes **131 → 134 → 762**. If the ~44.9 Hz
mode's loop gain crosses 1 between 1× and 2×, a **1.5×** dose may sit below it while still delivering
most of the 18–22 Hz benefit.

**Implementation is cal-only, no code edit:** revert both `sar` immediates to `0xa` and raise mode 10's
four `gain_B` Y rows by 1.5× (creep record `0xD2A74`: `3072 → 4608`, and the matching rows in
`0xD2AB0` / `0xD2AEC` / `0xD2B28`). Records are private per mode, one reader each.
Arithmetic: `5120 × 4608 = 23.6 M` = 1.1% of INT32_MAX.

⚠ **Honest uncertainty:** the band table shows a *monotone amplification*, not a pure threshold, so a
1.5× dose may simply deliver 1.5/2 of **both** effects — 18–22 Hz at ~0.5 instead of 0.35, and 40–49 Hz
at ~8× instead of 11.7×. **1.5× is an untested dose and the threshold reading is an inference.** It is
a fallback, not the recommendation.
⚠ It also changes base steering at every operating point, which is the thing the operator asked to
avoid. **Rank it behind the gate.**

### GATE 2 — closed-loop stability
- The lane is a **derivative ⇒ DC-neutral**, so a gain step at engagement produces **no torque step**.
- The gain now switches with `gp-0x6806`. **A gain that switches near the mode frequency is a
  parametric pump** — the exact failure mode V58/V59/V60 chased for three builds. The prior on-car
  measurement is **2 transitions in 180 s (≤0.1 Hz)**, four orders of magnitude below 20 Hz.
  🛑 **[PENDING DATA] This must be confirmed on the V57 probe (`0x14A` byte4 bit6 = `gp-0x6806 == 0`)
  before flashing.** If `gp-0x6806` toggles anywhere near 15–60 Hz, V67 is cancelled.
- State-mask residual: arbitration runs under `andi 0x930` (states 4/5/8/11), the aggregator under
  `andi 0xc30` (states 4/5/10/11). **State 10 runs the aggregator but not arbitration**, so
  `gp-0x6806` is one-or-more ticks stale there. Harmless for a ≤0.1 Hz signal; recorded, not ignored.
- Masking residual: `gp-0x671d` **outranks** the LKAS arm. If it latches non-zero, r24's gain is pinned
  to `0xC6442` = 1024, *below* the LERP default, and V67's arm never applies. V64's probe measured it
  **0 across all 14,980 frames** of route 35. **[PENDING] re-measure over a long drive — that is V66's job.**
- 🛑 **Polarity of `gp-0x6806` is the load-bearing unknown.** The kit's own record is ambiguous (one
  note has the deadband gate enabled when `gp-0x6806 == 0`; another has `== 1` in 96.26% of an engaged
  route). **Resolve from the instructions and from the V57 probe before building.** If the polarity is
  inverted, the whole design inverts with it and the arm value changes meaning entirely.

---

## What grind #2 IS, as far as the data goes

- **~44.9 Hz, sd 5.4 Hz, n = 43 events, Q ≈ 37** — a sharp resonance, not broadband roughness.
- ✅ **NOT a harmonic of grind #1.** Regressing the high-band peak on the 20.76 Hz mode's peak gives
  slope **0.173 [−0.92, 1.59]** against the 2.0 a harmonic requires. Independent mode.
- ✅ **It is a real mechanical vibration, not an EPS signal artifact** — it appears on the **comma
  device's IMU**, a sensor sharing no path with the EPS. (Kit's first use of the IMU. ⚠ Its positive
  control — grind #1 visible on the same sensor — must be reported or the detection is uninterpretable.)
- 🛑 **The frequency is ALIASED and stays unresolved.** CAN is a ~100.5 Hz grid ⇒ Nyquist 50 Hz, so
  **44.9 Hz and ~55.6 Hz are the same observation.** The IMU runs at ~101 Hz median — only 0.5 Hz from
  CAN — so **IMU/CAN frequency agreement is NOT evidence about the alias** and must not be quoted as
  such. A dedicated alias test came back **underpowered** (slope −1.16 [−4.15, 2.26]).
  ⇒ Recorded as unresolved. **It does not block anything**: every candidate fix ranks identically for
  both candidates, because the lane's problem is a *selectivity* ratio that is bad at both.
- **Where it lives:** creep, large driver steering input (`tq_avg` 1600–2700, |angle| 150–265°), and
  **both engaged and disengaged**.

---

## V66 — the requested long-drive build

Operator's spec: *V38 4× LKAS enable · steer-to-zero · live telemetry on the most valuable bits ·
no V62-style edits, leave grind #1 as V38 has it.*

= **V65 with both `sar` immediates reverted to `0xa`, plus a new cave payload.** Everything else — the
V57 `0xC646C` decoupling with the private forward cal `0xC6CD0` = 3564, the `0xC62EA` = 0 steer-to-zero,
the `0xC64DE` = 27 re-engage ramp — is carried unchanged from a build that is flying clean today.
Reverting the `sar` restores **stock base assist**, which is the operator's "more stable" requirement
and also makes V66 the clean **Kd = 1× control** for the three-dose comparison.

**Probe payload — `0x14A` byte4 bits 7:3, in priority order.** V66 is the pre-flight for V67: it
measures every load-bearing unknown in the design above, with no code risk.

| bit | signal | what it decides |
|---|---|---|
| 7 | liveness = 1 | field == 0 ⇒ cave did not fire ⇒ VOID |
| 6 | `gp-0x6806 != 0` | gate candidate A — duty and toggle rate |
| 5 | `gp-0x67f5 != 0` | gate candidate B, driver-torque — **its toggle rate is V67's kill criterion** |
| 4 | `gp-0x67fe != 0` | gate candidate C — **settles the LKAS-vs-base-assist semantic dispute in one bit** |
| ~~3~~ | ~~`gp-0x683c != 0`~~ | 🛑 **DID NOT FIT — see below.** It was the control for the repoint's premise |

✅ **BUILT AND VERIFIED 2026-08-01.** Image SHA `0d4a0a5361e8ba91b1a24ad3298dd617ad541903070b02a58b9ae6df6709f246`;
RWD SHA `41a4476ae9fb29fd2afd1b41238bf19b409b256abb8adfa3a8fb7b5569548fa9`.
**61 bytes off V65**, restricted to `[0x13000,0x100000)`: `0x3AB76` `a9`→`aa`, `0x3AC20` `a9`→`aa`, the
cave `0xC4B38`–`0xC4B71`, and the MAIN CRC at `0xC4FFC`. ⭐ **CAL block byte-identical to V65** and the
**`0xD2000` block identical**, with all four mode-10 `gain_B` records unchanged = machine proof no
calibration moved. `0x3AB70` correctly still `sar 0xa`. **`gp-0x683c`'s load at `0x3AA94` is UNCHANGED**
— V66 must not carry V67's repoint, and it does not. 50/50 CRC blocks PASS; RWD x31 checksum PASS and
the RWD decodes **exactly** back to the image.

⭐ **Orchestrator-verified independently from the built image**, cave re-decoded from the bytes:
```
movea 0x80,r0,r7                                              ; liveness -> bit7
ld.bu -0x6806[gp],r6 ; cmp 0x1,r6 ; blt +6 ; movea 0x40,r7,r7  ; bit6
ld.bu -0x67f5[gp],r6 ; cmp 0x1,r6 ; blt +6 ; movea 0x20,r7,r7  ; bit5
ld.bu -0x683c[gp],r6 ; cmp 0x1,r6 ; blt +6 ; movea 0x10,r7,r7  ; bit4
ld.bu -0x1514[gp],r6 ; andi 0x7,r6,r6 ; or r7,r6               ; preserve stock bits 2:0
st.b  r6,-0x1514[gp]                                           ; THE ONLY STORE
movea -0x1518,gp,r6  ; jmp [lp]                                ; displaced hook insn + return
```
⚠ `ld.bu -0x67f5[gp]` carries its displacement's **odd bit 0 in hw1 bit 5** (opcode field reads `0x3D`),
which is correct and is exactly the trap that has produced false mismatches before.

🛑 **ONLY THREE PROBE BITS FIT.** A fourth rung costs 12 bytes against ~6 spare in the 68-byte extent,
so the build carries **all three gate candidates** and drops the two lower-priority signals:
- ❌ **`gp-0x683c`** — the control on the repoint's premise. Its deadness now rests on **two independent
  static methods** (my raw byte scan in both encodings at every offset, and a tracer's 3-method
  cross-check), which is why it was the one to give up. ⚠ **But static clearance has failed this kit
  before** (`gp-0x1500` passed both static methods and still failed on-car), so this is a real residual:
  if something writes `gp-0x683c` through a computed pointer, V67's arm would already be firing on V65
  today. Nothing in V62/V65's behaviour suggests it is.
- ❌ **`gp-0x671d`** — the masking risk. V64's probe already read it 0 across 14,980 frames.

All four are plain `!= 0` boolean tests on gp-relative cells — no thresholds, no arithmetic, no new
condition codes, and every emitted load pinned byte-for-byte to a real instance in the image.

🛑 **Start the log BEFORE the first engagement**, or bit6's transition structure is unmeasurable.
🛑 A constant `0x87` is **ambiguous with V64's null and with V65's neutral bucket** — the decoder must
refuse to interpret it and say which `.rwd` is on the car.

---

## Record corrections this session (byte-verified, folded into the golden model)

★ **`FUN_0003ad74` resolves r24's `gain_B` through FOUR SEPARATE POINTER ARRAYS**, each indexed by
`mode*4`: `0xCBF5C`, `0xCC044`, `0xCC12C`, `tp+0xD214` = `0xCC214`. For mode 10 they resolve to records
**`0xD2A74` / `0xD2AB0` / `0xD2AEC` / `0xD2B28`** — *not* four consecutive records at a stride. Reading
them as consecutive from `0xD2AEC` lands on modes 10/11's interleaved rows and yields a nearly flat
surface (2305 → 1948), **understating the real rolloff by 2×**. The golden model's
`ASSIST_RATE_B_RECORDS` values were right; their provenance was not recorded.
⚠ `builds/v50_v79/build_v62_tva.py`'s `GAIN_B_LERP_MODE10` tripwire watches only `0xD2AEC` and `0xD2B28`, so it is
**blind** to an edit landing on `0xD2A74` or `0xD2AB0`. Widen it before any cal work on this lane.

★ **The real mode-10 surface**: at creep the gain is **3072**, flat out to motor rate **400 counts**
(≈85 deg/s at 4.7121 counts per deg/s), falling to **1536** at 3000 (≈637 deg/s) — a genuine 2× rolloff.
At road speed it flattens (0.80× at 32 km/h). So Honda **already** de-escalates this lane when the wheel
moves fast, and only at low speed. The frequently-quoted *"r24 default arm = 2305"* is the **50 km/h**
record; at the hands-off-creep operating point it is **3072**.

★ **`gain_A` (r26) is NOT mode-indexed** — four fixed records at `tp+0x7a68/7a7c/7a90/7aa4` =
`0xC6A68/7C/90/A4`, hard-coded in the instruction stream. (Moot in practice: r26 is structurally inert.)

★ The cross axis is **`tp+0x7010` = `0xC6010`** = `[0, 640, 3200, 6400]` = 0 / 9.99 / 49.95 / 99.9 km/h,
keyed on `gp-0x6a5e` (voted vehicle **speed**), substituting cal `tp+0x7314` when `gp-0x67f4 != 1`.

★ The runtime LERP lands in `gp-0x6e40` (X) / `gp-0x6e38` (Y) for r24, and `gp-0x6e30` / `gp-0x6e28`
for r26.

---

## The cal-only alternative, kept on the table

Because the breakpoints above are **calibration**, r24's motor-rate rolloff can be sharpened instead of
gated: e.g. mode 10's X row `[0, 400, 1500, 3000]` → `[0, 150, 400, 3000]` with a raised low end gives
**boosted gain where grind #1 lives and stock-or-less where a fast-moving wheel puts grind #2**. Records
are **private per mode** (mode 11 → `0xD2A88`…), so blast radius is one car variant.
🛑 **Blocked on data**, and possibly fatally: a prior correction found band power tracks **motor rate**
for *both* the grinding *and* the ratchet (partial ρ +0.573/+0.701), which is exactly the axis this
lever uses. If both symptoms live at the same motor rate, this lever cannot separate them and it is
dead — **[PENDING DATA]** from routes `3a`/`3b`.
