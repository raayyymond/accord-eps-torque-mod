# HANDOFF 2026-08-09 — V84 flew (route `6d`) and FIXED NOTHING; a command-scaled Coulomb relay is found

**Read `docs/STATE.md` first.** Predecessor: `handoffs/2026-08/HANDOFF-2026-08-08-v83a-flew-and-r24-is-the-actor.md`.

---

## ★★★★★ THE HEADLINE

0. 🛑🛑 **READ THIS FIRST — V84 FAILED ON ALL THREE OF THE OPERATOR'S OWN SYMPTOMS.** Grinding barely
   moved, and **micro-ratcheting and ratcheting were "very obviously present."** Everything below is
   secondary to that. ⚠ **TERMINOLOGY DISCIPLINE, operator instruction 2026-08-09:** *"Not even sure
   what the ring is. We are working on grinding, vibrating, and ratcheting issues."* **"The ring" is KIT
   JARGON for a 26–31 Hz oscillation. It is not a symptom the operator ever named. Do not headline a
   band index; name the symptom in the operator's own words and cite the band as the instrument.**
1. 🛑 **V84 FIXED NOTHING. Operator, verbatim, 2026-08-09: "None of these have been fully fixed in
   V84."** That is the verdict of record and it **overrides every instrument result in this handoff**
   (`CLAUDE.md`: *the operator's lived experience overrides analyst recommendations*).
   V84 flew route `6d` fault-free. **One BAND MOVED** — 26–31 Hz burst duty **96.6% (V80) → 25.1% (V81)
   → 2.54% (V84)**, longest event 18.29 → 11.25 → **1.34 s**, on 3.4–4.9× the exposure, with the
   negative control and the IMU falsifier both passing. **A band moving is not a symptom being fixed**,
   and this one rests on an **absence of a complaint** (*"I did not notice any odd behavior at normal
   speed"*), never on a report of improvement.
   📋 **METHOD RULE, added here because the orchestrator got it wrong in-session and the operator had to
   correct it twice: DO NOT PROMOTE A BAND-INDEX MOVEMENT TO A HEADLINE, AND NEVER CALL ANYTHING
   "FIXED" THAT THE OPERATOR HAS NOT CALLED FIXED. Score bands; let the operator score symptoms.**
2. 🛑 **A RETRACTION of V83a's headline.** *"The damper-dose model of the 26–31 Hz ring is FALSIFIED"* is
   void — V83a never removed the damper (mode 27 kept it) and had 19.2 s of highway.
3. 🛑 **The rate lane is at its ceiling.** V84 is byte-identical to V67/V68 at **every** grind-relevant
   cell. Lever B has now been delivered three times and tops out where the operator still hears grinding.
4. ★★★★★ **The loop does NOT close through openpilot** — the bar *leads* the command by **18.5 ms**;
   **91–98% of bar band power is incoherent with the command** ⇒ command-side filtering is closed.
5. ★★★★★ **At matched `θ̈` and matched speed the engaged bar carries 2.77× (6–9 Hz) and 1.66×
   (17–23 Hz) more torque than manual**, control 1.04 ⇒ **the firmware adds torque to the bar.**
6. ★★★★★ **`FUN_0003b8f6` contains a Coulomb RELAY proportional to the delivered command**, relay index
   **7.87** vs V80's 3.27, **virgin on all 84 builds**. **V85 linearises it — one cell, two bytes.**

---

## 1. THE OPERATOR'S FRAMING

> *"For V85, eliminate the grinding, microratcheting, and ratcheting … the Honda firmware is not built to
> sustain such high LKAS demands. I would need some filtering and/or self-interference cancellation of
> the LKAS torque signal which shows up on the driver-side torque signal (opposing torque under
> LKAS-driven angular acceleration due to the steering wheel inertia)."*

**The hypothesis splits, and both halves were settled this session:**
- *"Filter the LKAS signal"* — **CLOSED.** The coupling is not there (§4).
- *"The EPS re-amplifies its own output through the bar"* — **CORRECT**, and the loop is entirely inside
  the EPS + plant (§4, §5).

Standing constraint, restated: *"ratchet gone **without limiting the max steering angle rate under
strong LKAS command**."* V85 satisfies it by construction — it touches no command path, gain, rate limit,
filter or pole.

---

## 2. ROUTE `6d` — V84's flight

**Identity, no free parameter [EVIDENCE]:** the `0x14A` byte4 alphabet is exactly **{0x2F, 0x3F}** —
`b3` (V84's hard-coded fingerprint) = **1.00000**, `b7`/`b6` = **0.00000** across 68,236 frames. Routes
67/68 are perfect thermometers containing neither value. Orchestrator-verified from `_scratch/cache/r6d/`.

**Health:** 68,235 frames, 682.4 s, **79.71% engaged**, 0–113 km/h, `STEER_STATUS` {0: 68,219, 3: 17},
**0 DTC-active, 0 sentinels.**

### 2a. The 26–31 Hz band — a band moved; NO symptom was fixed

| build | damper relay index | eng >80 km/h | windows e26-31 >1000 | burst duty | longest |
|---|---|---|---|---|---|
| V80 | 3.27 | 30.7 s | 24/24 (100%) | 96.6% | 18.29 s |
| V81 | 1.45 | 44.8 s | 8/35 (22.9%) | 25.1% | 11.25 s |
| **V84** | **0.00** | **151.0 s** | **1/118 (0.8%)** | **2.54%** | **1.34 s** |

Adversarial checks pass: the 26–31 Hz *median* rise is a broadband floor shift (32–38 Hz control moves
with it, ratio-of-ratios 1.13) but the **tail is down 0.32×**; IMU says the road was **1.2× rougher**,
moving *against* V84. Orchestrator independently measured 370.8 s engaged >50 km/h, 158.1 s >80 km/h.

### 2b. 🛑 THE RETRACTION
V83a's falsifier fired on a build that **never removed the damper**: it reverted mode 26 and left
**mode 27 carrying V81's entire package** (mode 27 is a second ENGAGED column on this `TVCA4` car), on
19.2 s of highway. **V84 removed it in both columns on 151 s and the 26-31 Hz band fell to 2.54% burst duty.** ⚠ That is a BAND result; the operator reports no symptom fixed.
📋 **METHOD RULE: a pre-registered falsifier only fires if the lever was IN FORCE and the exposure was
adequate. Check both before scoring it — RULE 5, applied to a falsifier rather than a null.**

### 2c. The rest, scored
| | prediction | measured | verdict |
|---|---|---|---|
| S1 18–22 Hz | ≈0.40× V83a | **0.509 [0.396, 0.695]**, null [0.60,1.62], control 0.969 — but **1.10× V81** after control correction | falsifier did NOT fire; **no gain over V81** |
| S2 6–9 Hz | uncertain | 1.150× V83a (inside null); **1.548× V67, OUTSIDE null** | **FAIL** |
| S3 macro ratchet | improved | no instrument; operator: "very obviously present" | **FAIL** |
| S4 impedance | ≈1.00 structurally | **2.052 [1.089, 3.936]** vs V81's 1.484 | **FAIL and REVERSED** ⚠ manual arm 4.5 s |

⊕ **Orchestrator byte-check: V84 ≡ V67/V68 at every grind-relevant cell** except `0x454FE`, which
**cannot execute** (`gp-0x67fa==4` fires 0/123,277). ⇒ the 221.8-vs-109 gap is route composition, and
after the negative-control correction **V84/V67 = 0.92 at 18–22 Hz — flat.**

⊕ **Both operator-reported grind-#2 events found.** Event 2 (t=255.9 s, 56 km/h, 18.6°, cmd 1657) is
clean grind #2 — 48.77 Hz, Q 20.8, 3.10× IMU excess. Event 1 may be a **folded ring harmonic**
(2×26.6 Hz → ~47 Hz). **Neither had the blinker up**; lane-change windows as a class are flat.
🛑 The §7b protocol got **5.1 s of a 166 s floor (3.1%)** — fourth build in a row to miss it.

---

## 3. WHAT WAS RULED OUT — five candidates, honestly

| candidate | verdict |
|---|---|
| boost curve `FUN_00034a72` | **speed**-indexed, not torque; task 5 = 100 Hz; torque branch dead (`tp+0x7499`=1). The FEASIBILITY §2.2 diagram box is **mislabelled** |
| Path-2 PID `FUN_0003a382` | magnitude swings ~2×, phase −62°→+61° — PID bode shape, **not** flat/linear-phase |
| `FUN_00036682` | `0xC63D2`=6/1024 ⇒ 0.94 Hz corner. Far too slow |
| r24/r26 rate lanes | `\|gp-0x4f62\| < 201` all drive vs a ±5120 clamp; and its differentiator makes gain **rise** 2.7× where the measurement is flat |
| `FUN_00036c12` / `gp-0x6b26` | **dissipative** at every f and speed tested (`Re(H)` −0.052 / −0.353 / −1.218) ⇒ **the FEASIBILITY §6 "lower `0xC407E`" recommendation is the WRONG DIRECTION**; hard-capped at ±511 by the fault interlock |
| a road-feel HF passthrough | **does not exist** as a classical term |
| `FUN_0003b8f6`'s "biquad" | **it is a 3-tap FIR** (2 zeros, 0 poles) at **identity** — cannot ring. *"No biquad anywhere"* SURVIVES |

⇒ ⚠ **The 0.216 flat/inverted/~4 ms bar→command leg is STILL UNLOCATED.** Nobody knows what closes the
loop. That is the single most important open item in the project.

---

## 4. THE LOOP DOES NOT CLOSE THROUGH OPENPILOT [EVIDENCE]

| band | γ² | K | group delay `cmd→bar` |
|---|---|---|---|
| 26–31 Hz (V80) | 0.783, crit 0.259 | 11 | **−18.5 ms** [−20.8, +0.75] ⇒ **bar LEADS** |
| 18–22 Hz (pooled) | 0.031, floor 0.025 | 52 | **REFUSED — no coupling** |

Corroborated by openpilot's own `ang→cmd` = **+20.21 ms** (r²=0.972) — equal magnitude, opposite sign,
the signature of `H1 → 1/C` when the disturbance is in the plant. Granger: net `bar→cmd` in **9/9** cells,
positive control at 8×. Phase slope has the opposite sign to any causal forward path.
**Incoherent fraction: 18–22 Hz 96.9% · 6–9 Hz 91.1% · 40–49 Hz 98.3%.**
openpilot's 123 ct/frame cap refuted as a cycle source (predicts 0.75–5.1 Hz vs 26–30 Hz).

🛑 **INSTRUMENT CORRECTION:** the standing *"`0x18F` is one frame (~10 ms) stale"* rule is a
**cache-extractor artefact, not a bus property** (every frame in a panda batch shares one `logMonoTime`;
measured age 0.37 ms). Real for cache-derived work, absent when indexing by batch. **State which.**
⊕ *"bar/command ratio 15.8× at 27 Hz"* is a **tail** value — median **2.24**.

---

## 5. THE FIRMWARE ADDS TORQUE TO THE BAR [EVIDENCE, with caveats]

At matched `θ̈` **and** matched speed: engaged/manual = **2.77 [2.29, 3.32]** (6–9 Hz), **1.66
[1.29, 2.06]** (17–23 Hz), control **1.04**. Purely inertial coupling gives 1.00.
⚠ **The control FAILS above 8 m/s (0.62, 0.49)** ⇒ *"the excess vanishes at highway"* is NOT supported;
only the 2–8 m/s row is clean. ⚠ Residual speed gap inside it: 5.40 vs 2.99 m/s. ⚠ Manual arm pooled
over six caches. ⚠ The **transfer-function** contrast is REFUSED (manual γ² 0.09/0.04).

⊕ **The wheel-on-torsion-bar mode is 12.8 Hz [12.1, 13.6]** — **between** the symptom bands. Below it the
bar reads inertial (6/6 arms), above it stiffness (5/5) ⇒ **a single-gain `θ̈` feedforward tuned at
7.79 Hz arrives at 20 Hz INVERTED.** Corrects FEASIBILITY §2.2 (`f₀` bracket wrong; **7.79 Hz is NOT the
wheel-on-bar mode**) and §3.4 (the *"17× more lightly damped than V48B"* margin is wrong by ~10× —
measured r = **0.98823** vs V48B's 0.979 = **1.8×, same class**). **The NO-GO survives.**

⊕ **Command buys DUTY (5–45×), not AMPLITUDE (≤2.3×, median 1.29×)** — the standing rule SURVIVES.

---

## 6. ★★★★★ THE MECHANISM — and V85

`FUN_0003b8f6` @`0x3b8f6`, **1 kHz**, absent from the golden model until now:
```
ratio    = clamp(polarity * gp-0x6abc * 12 / cal(0xC40BC), +-1)     # saturates at cal/12
FRICTION = clamp(EMA(|model| * ratio * 102/1024, a=408/4096), +-10) # model ~ DELIVERED COMMAND
gp-0x6bfc = clamp(2639 * (model - FRICTION - INERTIA), +-20000)     -> ... -> aggregator -> motor
```
**`ratio` saturates at 50 counts against the function's own 13000 gate ⇒ pinned at ±1 across 99.62% of
its valid range.** It is `sign(motor rate)`, multiplied by the **delivered command**. Relay index
**7.87** — Honda's viscous 1.00, V75 1.45, **V80's bang-bang 3.27.**
**`0xC40BC` has 1 reader / 0 writers image-wide** (two methods; the disp encodes as **`0x50BD`**).
The whole plant-model cal block is **virgin across all 84 builds.**

**V85 = the flown V84 + `0xC40BC` 600 → 6000** ⇒ relay index **7.87 → 1.00**, linear to 500 counts,
delivered friction above 106 °/s **bit-identical**. Probe repointed onto the mechanism's own thresholds.

🛑 **THE HONEST RISK:** a **flat 10× reduction at and below 10.6 °/s** — most ordinary steering. The term
is dissipative; V56's lane mute cost damping. Reverting is two bytes.
🛑 **PRE-REGISTERED: S1 should NOT move** (V56 muted this lane's terminus → NULL at 18–22 Hz). Targets
are **S2/S3/S4**. **If S2 does not improve, revert — `N` is flat at 6000, there is no larger dose.**
🛑 **`b5` as specified (`|gp-0x6b98| > 8192`) was STRUCTURALLY VACUOUS** — `gp-0x6b98` is clamped to
exactly ±0x2000 by its own writers. **The orchestrator's "the lane drops out under strong command" is
REFUTED.** The real intermittency is the caller's state guard (`andi 0x830` ⇒ states {4,5,11}).

---

## 7. CORRECTIONS OF RECORD

| # | correction |
|---|---|
| 1 | **The golden model's "the B branch is DEAD CODE, coefficients all `0x0000`" is FALSE.** `0xC4048` = `00 00 80 3f` = **float 1.0**. They are **32-bit floats**; a u16 read of 1.0f returns 0. The branch is an **identity pass-through** ⇒ `gp-0x6bfc` IS sensor-derived ⇒ **FUN_0003b8f6 is a genuine disturbance observer** ⇒ **FEASIBILITY OPEN #1 resolved in the affirmative** and §2.1 is **incomplete** |
| 2 | **V83a's ring falsifier — retracted** (§2b) |
| 3 | **`0x18F` staleness is a cache artefact** (§4) |
| 4 | **FEASIBILITY §6's `0xC407E` DOWN is the wrong direction** — the lane is dissipative |
| 5 | **FEASIBILITY §2.2 `f₀` bracket and §3.4 damping margin** both wrong (§5) |
| 6 | **`0x454FE` is ELIMINATED, not falsified** — state 4 fires 0/123,277 driving frames. **And V42 was never single-lever** — its image shows six functional groups incl. zeroing all four `gain_A` records |
| 7 | **`0xC644A` on V43 is 32, not 64** (64 is V49's value) |
| 8 | **`0xC61B2`/`0xC61B4` are the arbitration/LKAS OUTPUT CLAMPS**, not a "pre-gain deadband arm" |
| 9 | **V84 was recorded UNFLASHED** — second consecutive build with this defect |
| 10 | **Two incompatible "engaged creep" rulers** in `rlog-tools/` — a **5.9× swing** on the pre-registration's own target (109 vs 654) |
| 11 | **`_grind2_lib.wrecs` returns NaN silently** for every engaged-vs-manual contrast |
| 12 | **`scan_gp_accesses.scan_ext` is unsound** — wrong disp23 packing, blind to positive disp. V85 ships a calibrated replacement |
| 13 | `decode/decode_two_angles.py`'s premise is void — the two `0x14A` angles are byte-identical on 280,598/280,598 frames. ⊕ `0x14A` angle/rate is **BELOW the bar**. `tq` LSB is **8**, not 1 |

---

## 8. RESIDUALS

- 🛑 **121 non-stock bytes sit in factor records this car never reads** (modes 0–5, 10–17, 23, 29, 32, 33;
  **0 bytes in any live mode**). Inherited, never chosen. **Latent hazard: the mode index is
  data-driven**, so a config re-code would make eight builds' worth of untested edits live at once —
  including V72's `FactorE Y[0..2]→927`, a near-bang-bang relay. **Revert them as base hygiene on the
  build AFTER V85**, pre-registered as an expected no-op; folding them into V85 would destroy its
  single-variable attribution. ⚠ 16 of the 121 are in the table region but not inside any record I could
  map — identify them before reverting.
- **The Ghidra project may hold a stale, unanalysed V85 import**; `close_program` timed out twice and
  `projectState` is dirty. Close it before the next session — a stale import is a recorded failure mode.
- **`gp-0x6abc`'s counts-per-°/s scale is unconfirmed.** V85's `b7`/`b6` pair measures it.
- **`S_T` (counts→N·m) is unmeasured** — every N·m and kg·m² figure is conditional on it.
- **The highway grind and the ~28 Hz lane-change transient remain unaddressed.**
- 🛑 **THE GRIND-#2 DRIVE PROTOCOL IS RETIRED, not outstanding.** Operator decision, 2026-08-09, after
  he asked what it meant. It prescribed: empty lot, **openpilot engaged throughout**, 4–11 km/h without
  stopping, wheel **≥100° from centre** sweeping 100–360°, continuous figure-eights at 100–500 °/s
  column rate, **6–9 minutes**, plus ~60 s of the same manoeuvre with LKAS off. Route `6d` accumulated
  **5.1 s of a 166 s floor (3.1%)**, and four builds in a row missed it the same way.
  **It is being retired rather than re-issued**: it asks for an artificial low-speed manoeuvre under
  LKAS that is awkward at best, and the 40–49 Hz events the operator actually reports occur on ordinary
  roads at **56–62 km/h** (both route-`6d` events), not in that regime. ⇒ **Any future claim about
  40–49 Hz at engaged creep is UNMEASURED and must be labelled so — do not schedule the drive, and do
  not quote a zero-count from it as evidence.**

## ⇒ NEXT
1. **Fly V85** with §6's pre-registration. 🛑 The flash decision and the bus are the operator's.
2. **Run the ≥166 s grind-#2 protocol** — four builds in a row have missed it.
3. **Base hygiene**: revert the 121 inert bytes on the next build.
4. 🛑 **CORRECTED 2026-08-09 (operator challenge). An earlier draft of this handoff claimed the
   `0xC6AE0–EC` D-GAIN table "has never been touched" and billed it the leading V86 candidate. That
   framing was WRONG and is withdrawn.** The *value* has indeed never been written (`0xC6AE6` = 2048 in
   stock and in every build through V85, byte-verified) — **but the D branch has already been attenuated
   on-car and nulled.** `0xC644A`, the D-branch smoothing pole, is unity (1024 = no smoothing) on stock,
   and **V43 FLEW it at 32**:

   | `0xC644A` | corner | `\|H\|` @7.79 Hz | `\|H\|` @21 Hz |
   |---|---|---|---|
   | 1024 (stock) | none | 1.000 (0.0 dB) | 1.000 (0.0 dB) |
   | 64 (V49, never flashed) | 10.27 Hz | 0.797 (−2.0 dB) | 0.440 (−7.1 dB) |
   | **32 (V43, FLOWN)** | **5.05 Hz** | **0.544 (−5.3 dB)** | **0.234 (−12.6 dB)** |

   ⇒ **V43 removed 12.6 dB of the derivative branch at 21 Hz and the vibration did not move.** Cutting
   the *gain* is a **weaker** version of the same test at that frequency, so **"the D term is falsified
   at ~21 Hz" is substantially ESTABLISHED, not open.**
   ⚠ **The narrow gap that DOES survive:** at **7.79 Hz V43 bought only −5.3 dB**, and the 6–9 Hz
   micro-ratchet was not a scored band when V43 flew. **The D branch is UNDER-tested at micro-ratchet
   frequencies — it is not untested in general.** Any V86 proposal here must be sized for 6–9 Hz and must
   say why −5.3 dB at that band was insufficient.
   ⊕ **V49 built (never flashed) a Stage-C SIGN FLIP** (`subr`→`sub` @`0x3a836`) plus pole 64 — a
   different class of intervention (sign, not magnitude) and still genuinely untested. It was gated on
   `gp-0x6752 = +1`; **this session confirmed that cell is a boot-time constant, always +1 in the
   field**, which removes the brick condition that gate was written for. GATE 2 still applies.
   📋 **METHOD RULE: "the VALUE was never written" is NOT the same as "the TERM was never tested."
   Attenuating a branch's pole tests the branch. Check what a lever's neighbours already did to the same
   signal path before calling it untried.**
5. **A firmware-side dither build** is the named highest-value experiment for identifying the forward
   path, which passive data cannot recover.
