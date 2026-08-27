# HANDOFF — 2026-08-20 — V102: the 8× gain is the carrier, and nine levers died on evidence

**Chain:** ← `handoffs/2026-08/HANDOFF-2026-08-18-v101-eme-audit.md` ← `handoffs/2026-08/HANDOFF-2026-08-14-v100-flew-and-six-levers-closed.md`

---

## THE ONE-LINE RESULT

**V101's 8× LKAS gain is the sole measured cause of the ~23 Hz vibration the operator reported at all
speeds.** Every calibration lever this session generated — nine of them — was killed on measurement or
on a gate, *before* the cut. **V102 flies the operator's own chosen dose: `0xC6CD0` = 5346 (6×), plus a
two-comparator instrument cave.**

---

## 1. THE OPERATOR'S REPORT (his words, 2026-08-19, after driving V101 as route `0x95`)

> *"Our grinding/vibration now exists at all speeds (I only went up to 30-40 mph) due to the 8x torque
> mod. It seems like some kind of instability or resonance. It only occurs during LKAS command, I do not
> think openpilot is part of the loop (like before). I can actually get it to go away, if I apply some
> torque to the steering wheel. However, as soon as I let go of it, or stop applying as much torque, the
> grinding returns and grows into a steady state."*

Plus two constraints issued mid-session:
- *"I am doubtful that the 8x torque mod could actually apply 8x torque… Seems like it could've been clamped."*
- *"We must not dampen or limit the max torque applied by the LKAS path… One of the supposed fixes from
  the 4x torque era was to just increase some dampener… it made the steering wheel move so slowly under
  the max LKAS torque command."* Refined: **an LKAS *command* rate limit is acceptable; a steering-wheel
  *angle* rate limit is not.** He also stated he does **not** mind changed driver feel *while engaged*.

---

## 2. WHAT ROUTE `0x95` MEASURED

**Identity PASS** — `byte7[7:6]==3 AND b3==1`, duty **1.000000** over 25,551 frames. Fault-free:
sentinels 0/0, DTC bit2 0.00000, `CONFIG_VALID` 1.0000, `OUTPUT_DISABLED` 0.00047,
`STEER_STATUS` {0: 25538, 3: 13}. **176.1 s engaged in 3 episodes**, speed p50 31.3 / p90 61.2 / max
68.3 km/h.

### 2.1 🛑 NO FIRMWARE CLAMP BINDS ANYWHERE — the operator's clamp suspicion is refuted, three ways
- **Structural**: the LKAS setpoint is LERP-clipped to **15360 UPSTREAM of the gain**, so
  `max |lkas_term| = (15360·G)>>15` against a clamp of `0.5746·G` ⇒ **81.5 % of rail on EVERY build
  since stock**, locked in lockstep since V14. The clamp has never been reachable at any gain.
- **Measured**: cave `b6` (`|gp-0x6b4c| ≥ 4096`) duty **0.000000** over 17,614 engaged frames, **zero
  transitions**, in all 10 command deciles, all speed bins, both oscillating and quiet strata —
  including **20.6 s with openpilot at its own ±4096 rail**. All four positive controls pass
  (b3 duty 1.000000 emitted *after* b6 ⇒ the rung provably ran; b5/b7 flipping 19.7–32.9 /s).
  **This is not a V64/V68 gate null.**
- **Corroborated**: `|gp-0x6b94|` max **2,188** of a ±10,240 writer clamp (21 %) and of the governor's
  **4,762** (46 %); 427 max **171** of a structural 800; no histogram pile-up on either route.
- ⇒ **The only saturating element in the chain is openpilot's own ±4096 wire rail, at ~12 % duty on
  BOTH builds** (0.1227 V100 / 0.1197 V101). It is not what changed.

### 2.2 THE PROTECTED METRIC — the operator felt correctly, and the reason is the buzz
`rate_f` (CAN `0x18F` bytes 2:4, the EPS's own 100.74 Hz fine angle-rate channel), low-passed <5 Hz to
remove the buzz, engaged, at openpilot's max command, hands-light:

| | V100 (4×) | V101 (8×) | ratio |
|---|---|---|---|
| delivered command `gp-0x6b94` p50 | 102.4 | 204.8 | **2.00×** |
| achieved wheel rate p50 | 16.9 °/s | 19.3 °/s | **1.14×** |
| achieved wheel rate p99 | 48.8 | 49.3 | **1.01×** |
| achieved wheel rate max | 62.7 | 51.8 | **0.83×** |

⚠ Exposure 4.4 s / 6.4 s — p90 usable, max indicative. The event-level command-ramp framing (matched
ramp time as a control) gives **peak wheel rate 58.0 → 106.5 °/s, 1.84× [1.00, 3.08]**. **The two
framings disagree on significance and agree on magnitude class; the honest reading is ~1.7–2.1× on
ramps and ~1.1–1.3× at the median, against a 2.00× command increase.**

### 2.3 ⭐ THE MECHANISM, READ OFF THE ECU'S OWN OUTPUT
`gp-0x6b94` sign reversals per second, matched on speed and wheel rate:

| wire code | 4–8 | 8–16 | **16–32** | **32–64** |
|---|---|---|---|---|
| V100 (4×) | 13.8 | 6.7 | **3.2** | **0.7** |
| V101 (8×) | 33.5 | 36.3 | **37.2** | **24.6** |

V100 shows the textbook quantisation signature (reversals collapse as the signal grows). **V101 does
not** — at 205–820 counts of real commanded torque the sign reverses **25–37 /s**. Re-weighting V101's
per-magnitude rates onto V100's own magnitude distribution: **34.19 vs 11.17 = 3.06×**, i.e. the excess
*grows*. **The quantisation-artefact hypothesis is refuted.** Internal control **b4 (PID reference sign)
flat at 1.24×** ⇒ specific to the aggregator output.
⇒ **The firmware is commanding a torque whose sign reverses tens of times a second at substantial
amplitude. That is the grinding, measured on the ECU's own demand.**

### 2.4 THE LINE IS IN THE FIRMWARE'S OWN DEMAND
`gp-0x6b94` 21–24 Hz shape **1.71× [1.33, 2.29]** above the lane's own broadband dose, every other band
flat at 1.3–1.6×. The bus channels carry 7.1× band / 3.0× shape. **A demand that already contains ~23 Hz,
driving a plant that resonates there. A loop — not a pure plant limit cycle, not a bus artefact.**
⚠ An earlier "the line is NOT in `gp-0x6b94`" null was **retracted** — it was measured in the wrong band
on a belief that `0x1AB` samples at 41.7 Hz. **It samples at 49.79 Hz (Nyquist 24.9 Hz); 23 Hz is
directly observable.** Independently confirmed at 49.78 Hz by a second agent.

### 2.5 OPENPILOT IS NOT IN THE LOOP — the operator is right
Coherence is high (cmd↔rate coh² 0.828 at 23 Hz vs 0.013 rotated) but coherence is symmetric and cannot
decide direction. **The plant-gain test decides it**: if openpilot drove the wheel, `|cmd|/|ang|` must
rise ≥ (f/3.5)² above 5 Hz through the firmware's ~1–5 Hz LKAS intake low-pass. Predicted **35.1×** at
24 Hz; observed **0.38×** — **wrong by ~92×.** openpilot is *echoing* the oscillation through its own
angle feedback.

### 2.6 DRIVER TORQUE IS DAMPING, NOT AN OPERATING-POINT EFFECT
Matched on speed **and** wheel rate: 7–9 Hz **0.14× [0.08, 0.27]**, 22–26 Hz **0.40× [0.12, 0.49]**,
control band **2.15× [1.75, 3.51]** (moves the opposite way — the negative control passes).
`|ang−centre|` is 1–2° in every bin ⇒ **not** off-centre. 7 GRIP + 7 RELEASE events; median release
profile −0.5 s **155** → 0 s **703** → +0.2 s **1468** → +0.5 s **1848** ct ⇒ **re-growth σ ≈ 2.5–5 s⁻¹,
plateau in ~0.5 s.** That is the operator's *"returns and grows into a steady state."*
⊕ Independent confirmation from an untuned channel: `|driver torque|` p50 **174 → 931 ct (5.35×)** while
his **sustained** push (127 → 116, 0.91×) and **hands-light duty** (0.581 → 0.591, 1.02×) are unchanged.
**The torsion bar carries 5× more signal because it is buzzing.**

### 2.7 IT IS NOT A LIMIT CYCLE
Growth σ against a phase-randomised surrogate: observed/surrogate **1.13 / 0.91 — inside the null**.
Kurtosis **3.85 / 3.38** (3.0 = narrowband Gaussian, 1.5 = sinusoid). Envelope std/mean 0.88/0.74 vs
Rayleigh 0.523. **⇒ a very lightly damped resonance driven by broadband excitation.** Consistent with
§2.1: **there is no amplitude-setting saturation anywhere inside the ECU.**
⊕ Wheel order explicitly ruled out: the ~8 Hz line's per-window peak slope is **−0.0105
[−0.0678, +0.0367] Hz/(m/s)**, excluding the tyre slope +0.4816 by ~14 σ.

---

## 3. 🛑 THE 2×2 — AND WHY THE FIRST ATTRIBUTION WAS WRONG

V101 changed three things at once (gain, clamps, Lever B removal). **Route `71` = V87 (4×, Lever B
already dead, rate lane byte-identical to V101's) is the third arm**, and it was already extracted at the
repo root — *not* under `analysis-2020accord/`.

### 3.1 THE SHAPE FLOOR — measured, and ~2× more sensitive than raw band power
Placebo **r75 vs r76, two drives on byte-identical V89 firmware**, 8 cells, 150/218 windows,
shape = band ÷ 32–38 Hz:

| floor | 6–9 | 18–22 | **22–26** | 26–31 | 40–49 |
|---|---|---|---|---|---|
| **shape** | **1.35×** | 1.23× | **1.45×** | 1.54× | 1.22× |
| raw band | 1.82× | 1.79× | 2.18× | 2.42× | 1.74× |

**Use the shape floor.** The raw numbers misled: V91's whole spectrum sits ~0.75× below V90's — normal
drive-to-drive level, exactly what the placebo says. Raw `k` = 0.66 was an artefact of that; shape
`k` = 0.87.

### 3.2 THE CONFOUND, MEASURED — `0xCBE74` (single variable, V90 r77 vs V91 r78)
`k` = **0.86–0.90 at 22–26 Hz** against a **1.45× floor** ⇒ **`0xCBE74` ×1.5 is INERT at 22–26 Hz, and
inert at 6–9 Hz.** The T10-invalid null is now replaced by a direct in-band measurement with a floor
behind it. **The cell is retired on evidence.**

### 3.3 THE DE-CONFOUNDED 2×2, 22–26 Hz, shape units

| channel | A = G·k | B = B/k | C = G·B | k | **G (gain)** | **B (Lever B)** |
|---|---|---|---|---|---|---|
| `tq` | 2.91 [2.08,5.35] | 0.97 [0.79,1.28] | 2.97 [1.95,5.21] | 0.87 | **3.34** | **0.84** |
| `rate_c` | 2.32 [1.75,4.62] | 1.00 [0.67,2.01] | 2.37 [1.45,5.51] | 0.86 | **2.69** | **0.86** |
| `cs_ang` | 3.49 [2.23,5.62] | 1.45 [0.97,2.16] | 4.90 [2.39,8.59] | 0.90 | **3.89** | **1.30** |

A×B reproduces C on all three channels ⇒ internally consistent. Sensitivity across `k`'s whole CI
(0.77–0.96): G = 3.02–3.77, B = 0.75–0.93. **The conclusion does not depend on `k`.**

> **⇒ THE 8× GAIN CARRIES THE ~23 Hz LINE (G = 2.7–3.9×, clearing the 1.45× floor by 1.9–2.7×).**
> **LEVER B CARRIES NONE OF IT (0.84–1.30×, entirely inside the floor).**

⚠ **An earlier 74/26 split, computed in raw band units, is SUPERSEDED by this.**

### 3.4 ⭐ AND LEVER B'S REMOVAL WAS A WIN — BUT ONLY AT CREEP
6–9 Hz, arm B = Lever B **removal**, `k`(6–9) ≈ 1.01–1.14:

| speed | `tq` | `rate_c` | `cs_ang` |
|---|---|---|---|
| **creep 5–15 km/h** | **0.45** | **0.26** | **0.58** |
| 15–35 km/h | 1.14 | 0.43 | 1.42 |
| 35–65 km/h | 1.13 | 1.06 | 1.30 |

**Removing Lever B cut the 6–9 Hz band to ~⅓ at creep; NEUTRAL at road speed** (inside the 1.35×
floor). ⚠ 2 cells, thin V100 arm, and route 71 tops out at 21 km/h so the isolated arm cannot be
extended. **⇒ "do not restore Lever B" stands — neutral-to-good, harmful nowhere.**
🛑 This is a BAND result. **The operator has not called anything fixed and only he scores symptoms.**

---

## 4. THE PEAK MOVED — AND THE Q DISAGREEMENT IS UNRESOLVED

| route | build | gain | `tq` peak, 20–28 Hz | prominence |
|---|---|---|---|---|
| r7e / r7f | V96 | 4× | 20.3 Hz | 1.00 / 1.05 |
| r85 | V100 | 4× | 20.3 Hz | 1.29 |
| **r95** | **V101** | **8×** | **23.0 Hz** | **3.67** |

**Three separate 4× routes at 20.3 Hz; the 8× build at 23.0.** A peak that *moves in frequency* is a
**pole moving** — loop dynamics, not excitation.

🛑 **THE TWO ANALYSTS DISAGREE ON THE WIDTH, IN SIGN, AND NEITHER NUMBER MAY CARRY A CONCLUSION:**
- one measures **Q 31.4 → 47.4, width ×0.71** (taller and narrower);
- the other measures **Q falling** — `tq` 34.5 → 23.6, `rate_c` 69.0 → 23.6, `cs_ang` 69.3 → 33.7
  (taller and broader), with prominence rising 14.9 → 18.4.

Both are sub-Hz widths (0.29–0.98 Hz) at a resolution where 3 bins decide it, and the half-height point
moves when the broadband floor moves — which it does, by ~2×. **UNRESOLVED. Barred from any build
decision.** Nothing above depends on it: the attribution rests on the shape ratio against a measured
placebo floor, which both analysts find in the same direction.

---

## 5. 🛑 NINE LEVERS KILLED — ALL BEFORE THE CUT, NONE ON THE ROAD

| lever | verdict | basis |
|---|---|---|
| **`0xC61B2`/`0xC61B4` clamps** | **INERT — 0 % of the effect** | 81.5 % of rail on every build since V14; `b6` duty 0.000000 |
| **Lever B** `0x3AA96`/`0xC6446` | **null at 22–26 Hz** (0.84–1.30×, inside floor); **removal is a ~3× win at 6–9 Hz at creep** | de-confounded 2×2 |
| **`0xCBE74`** accel lane | **INERT at 22–26 AND 6–9 Hz** (`k` = 0.86–0.90) | single-variable pair V90/V91 |
| **`0xC40D2`** (K1) | **NULL at both bands, real exposure** | single-variable pair V88/V89, shape stat vs measured floor. ⊕ Not T10-invalid |
| **`0xC63AC`** | **predicted WORSE** — HF gain beats the phase credit; \|L\| = 0.875×1.38 = **1.208** at cal 205 | full-loop Bode sum, robust across both anchors and all 3 attribution fractions |
| **`0xC63AA`** | **sign is frequency-dependent, not fixed** — `d(iVar6)/d(0xC63AA)` carries `gp-0x6b4c`'s instantaneous sign | tracer refused to guess a dose |
| **dead biquad `0xC649B`** | **guaranteed uninterpretable null** — forcing input gated on `gp-0x6b62 ≠ 0`, measured **duty 0.0000 over 75,227 engaged frames** | two agents independently derived 42.4 Hz / ζ 0.649 / −1.32 dB / −30.15° @21 Hz; the **gate** kills it |
| **PID `Kd` `0xC6AE6`** | **NOT READY — sign unresolvable at the symptom frequency**, and it changes MANUAL steering (`FUN_0003a382` gated on `gp-0x67fa & 0xc30`, the normal-driving cluster, **not** an LKAS flag) | 22–26 Hz is the measured Re(Z) crossover where 3 drives disagree in sign |
| **`0xC6194`** cmd rate limiter | **dead-dead** — `0xC63CC` = 0 nulls it after pooling; and a limit cycle would not respond to reduced input anyway | decompile + byte read |

**⇒ Every calibration lever this session generated is dead, and the cause is the cell the operator wants
to keep.** That is why the decision went to him as a dose-response curve rather than as a build.

---

## 6. THE DOSE-RESPONSE, AND THE OPERATOR'S CHOICE

🛑 **NO THIRD RUNG EXISTS.** Every cached route is `0xC6CD0` = 3564 (4×) except r95 (8×). **Two points,
one exponent, zero degrees of freedom. `p` is an empirical exponent, NOT a physical law.**

🛑 **AND THE OBVIOUS MECHANISM IS REFUTED.** Within either route the 22–26 Hz band **does not scale with
command amplitude** — slope of log(band) on log(command RMS) is **+0.01 [−0.36, +0.31] on V101** and
**+0.12 [+0.01, +0.40] on V100**, across a >10× command range. **The command is not the excitation; the
road and the driver are. The gain acts on the LOOP.** *"More gain = more excitation = more buzz"* is
wrong as a mechanism.

**Anchors:** 22–26 Hz shape **3.34× [2.69–3.89]** for a 2× gain step ⇒ **p = 1.74 [1.43, 1.96]**.
Wheel rate under hard command **1.84× [1.00, 3.08]** ⇒ **q = 0.88 [0.75, 1.04]**.

| `0xC6CD0` | mult | 22–26 Hz vs TODAY | vs V100 | wheel rate vs TODAY | vs V100 | status |
|---|---|---|---|---|---|---|
| 7128 | 8.0× | 1.00 | 3.34× | 1.00 | 1.84× | **V101, flown** |
| 6413 | 7.2× | 0.83 | 2.78× | 0.91 | 1.68× | interpolation |
| **5346** | **6.0×** | **0.61 [0.57–0.66]** | **2.02×** | **0.78 [0.74–0.81]** | **1.43×** | ⭐ **V102 — OPERATOR'S CHOICE** |
| 4455 | 5.0× | 0.44 | 1.47× | 0.66 | 1.22× | interpolation |
| 3564 | 4.0× | 0.30 | 1.00 | 0.54 | 1.00 | V88–V100, flown |
| 2673 | 3.0× | 0.18 | 0.61× | 0.42 | 0.78× | 🛑 EXTRAPOLATION |

**Benefit:cost — 7.2× = 1.89:1 · 6.0× = 1.76:1 · 5.0× = 1.65:1.** The operator was shown this table and
**chose 6×.**

⭐ **A STRUCTURAL CEILING, discovered at build time:** the build **ABORTS at 10×**, because the soft-EME
authority floor `0xC674E` = 5120 must stay **>** the tracking clamp and at 10× the clamp reaches 5120
exactly. **This firmware structurally caps the LKAS gain below 10×.**

---

## 7. V102 — WHAT IT IS

**Base V101. Three calibration cells + the cave + the 427 repoint.**

| address | V101 | **V102** | what |
|---|---|---|---|
| `0xC6CD0` | 7128 | **5346** | LKAS forward gain, 8× → **6×** (Honda stock 891) |
| `0xC61B2` | 4096 | **3072** | fwd-path clamp, tracking `GAIN × 512 // 891`, zero rounding |
| `0xC61B4` | 4096 | **3072** | arb output clamp, same |
| `0x55DF2` | `gp-0x6b94` | **`gp-0x6b4c`** | 427 source repoint, `sar 6` carried |
| `0xC4B34` | 114 B | **154 B** | the comparator cave |

**FROZEN and asserted (41 cells)** — including `0x3AA96`=0xC5, `0xC6446`=512 (**Lever B stays removed**),
`0xC40D2`=204 (**held deliberately, instrumented not dosed**), `0xC407E`=511, `0xC4080`=0,
`0xCBE74` m24/m25 stock + m26/m27 ×1.5.

### 7.1 THE CAVE — comparators, per the design law
| bit | measurand | form |
|---|---|---|
| `byte7[7:6]` = 3 **AND** `b3` = 0 | **IDENTITY = ID3 6** | const + `andi` mask |
| **b6** | `\|gp-0x6ada\| ≥ \|gp-0x6adc\|` — r24 arm vs r26 arm | **COMPARATOR** |
| **b5** | `\|gp-0x6ae2\| ≥ \|gp-0x6b26\|` — modelled friction vs inertia | **COMPARATOR** |
| **b4** | `gp-0x6ada < 0` | sign |
| **b7** | `gp-0x6b4c < 0` | sign |

**154 B / 58 instructions**, 12.7 % of the `0xC4B34..0xC4FF0` extent, 7.9× margin.
**PASS ORDER: comparators → comparators → SIGNS.** Straight-line leaf, so a live bit in the last pass
proves every earlier pass ran — this replaces V101's b3-as-constant-1 liveness witness, which the
identity change consumed.
**GATE 1 — no new claim:** `gp-0x6ada`/`gp-0x6adc` are written-but-never-read lane mirrors ⇒ pure loads.
**Store SET unchanged `{gp-0x1514, gp-0x1511}`; COUNT is 3 RMWs, not 2.**
**Verified from the built image by Ghidra: all 58 instructions, `truncated:false`, every branch `bge`,
zero `ba05`/`b205`.** Comparator direction confirmed 3 ways (V850 `cmp reg1,reg2` ⇒ flags on
`reg2−reg1`; Honda's own `ae05` = cond 0xE signed GE at `0x244CE`; V101's flown b6 measured on-car).
⭐ Honda's own stores to those cells decode as `st.h r26,-0x6adc,gp` and `st.h r24,-0x6ada,gp` —
**independent corroboration of the r24/r26 lane-mirror identification**, and proof both are halfwords.

### 7.2 IDENTITY — ID3 = 6
`byte7[7:6]` is a **2-bit field, exhausted** (0 = ≤V91, 1 = V96/V97, 2 = V98–V100, 3 = V101), and
`byte7[5:0]` is a live Honda field (all 64 values, every bit at duty 0.487–0.501). The extension:
**`ID3 = (byte7[7:6] << 1) | byte4 b3`**, V102 = **(3, 0) = 6**, V101 = (3, 1) = 7. V101's b3 is an
**unconditional constant 1** in the flown image ⇒ **(3,0) is structurally unreachable on V101.**
⚠ **V102 ⇒ `byte4[7:3]` is EVEN on 100 % of frames** (V101 was always ODD). **That IS the identity —
decoder authors must not pull the build for it.**
🛑 **Generation-3 identity space is EXHAUSTED after V102.** V103 must sacrifice a data rung or hook a
second CAN ID.

### 7.3 ARTIFACTS
```
image SHA256   61197f8ceffc401f9396e9023d07995820e17bb957007a6cd48d227dbfe32455   1,048,576 B
.rwd  SHA256   b49e7efa8c47bfe1fcdb639885c90ce840143fece8a7d87fdf62b66f2308b5cb     986,042 B
token          V101BASE-GAIN6X.C6CD0.5346-CAVE.CMP.6ADA.6AE2-SIGNS-427.6B4C-ID.ID3.6
```
`accord-firmwares/analysis-2020accord/_v102_…_plain_image.bin`
`accord-firmwares/flashing-2020accord/rwd/39990-TVA,A160-V102-…-0x13000-0x100000.rwd`

**Independently re-verified by the orchestrator from the shipped files on disk** (not from the build
script's claims): both SHA256s reproduce; `0xC6CD0` 7128→**5346**, `0xC61B2`/`0xC61B4` 4096→**3072**,
and **every other cell byte-identical to V101** — `0x3AA96`=197, `0xC6446`=512, `0xC40D2`=204,
`0xC407E`=511, `0xC4080`=0, `0xC674E`=5120, `0xC40BC`=300, `0xC63AC`=102, `0x454FE`=0xB5,
`0xCBE74` m26 = (−14745,−8601,−2949). `5346 × 512 // 891 = 3072` **exact**. `5120 > 3072` ✓.
`[0xC5000,0xC5FFC)` byte-identical to base. **156 bytes differ from V101**, matching the build's own
accounting (143 cave + 1 × 427 halfword + 2 × `0xC6CD0` + `0xC61B3` + `0xC61B5` + 8 CRC).
427 source halfword reads `B4 94` = **−0x6B4C** ⇒ repoint confirmed (V101 was `6C 94` = −0x6B94).

⚙ **`GAIN_DEFAULT = 5346` is the script default**, not env-var-only, so a bare
`python builds/v80_v107/build_v102_tva.py` reproduces the flown artifact bit-for-bit. `ACCORD_V102_GAIN=8x`/`4x`
remain available for exploration.
Verified from the built image: 41/41 FROZEN · EME audit 8 ranges + 6 scalars + 7 floats ALL PASS
(`0xC674E`=5120 > clamp 3072; `0xC407E`=511; `0xC4080`=0) · CRC 50/50 · `[0xC5000,0xC5FFC)` identical to
base (V40's brick) · **zero unattributed bytes vs stock** · bit-for-bit reproducible across two runs.

---

## 8. 🛑 THE PRE-REGISTERED READOUT — write the null sentence before the drive

**PRIMARY — within-route shape ratio**, `tq` band-RMS(21.5–25.5 Hz) ÷ band-RMS(2.5–4.5 Hz), median over
1 s engaged windows. Needs **no cross-route normalisation, no matched speed, no matched driver
behaviour.** Baselines: **V101 = 5.07** (n=173) · **V100 = 0.62** (n=245).
**PREDICTION at 6×: the 22–26 Hz band falls to 0.61× [0.57–0.66] of V101's.**

| outcome | licensed conclusion |
|---|---|
| **≈0.6× of V101 or lower** | the gain carries the line; the dose-response holds; V103 chooses a further step on a **three-point** curve |
| **≈1.0× of V101** | **the gain is NOT the carrier — this session's whole attribution is refuted** |
| **well below 0.6×** | the exponent is steeper than 1.74; less gain reduction buys the same result |

**POWER (subsampling consecutive windows from one contiguous stretch, 2000 draws):**
15 s **79.8 %** · **20 s 94.2 %** · 25 s **97.1 %** · 30 s **100 %**. ✅ **Buildable at one ~15–30 s
symptomatic episode.**

**SECONDARY, diagnostic, never disqualifying:** peak frequency (8 s contiguous, df 0.125 Hz ⇒ 13.6 bins
across a 1.7 Hz separation) · `d(b6)` · `d(b5)` — **which is what makes a V103 K1 dose scoreable** ·
the `gp-0x6b4c` distribution from 427 + b7.
🛑 **Q / −3 dB width is NOT an endpoint** — see §4.
**PROTECTED METRIC to re-measure:** wheel-angle rate under a hard command, hands-light — predicted
**0.78× [0.74–0.81] of V101, still 1.43× [1.35–1.53] of V100.**

---

## 9. CORRECTIONS TO THE KIT'S OWN RECORD

1. 🛑 **`gp-0x6b4c` IS NOT THE LKAS COMMAND.** It is `gp-0x3d88 = Σ_{i=0..10} (0xC4118[i]≠0 ?
   gp-0x62b0[i] : 0)` — an **11-slot assist framework**, LKAS being one slot, **algebraically flat** (no
   IIR, no EMA, no rate limit at that stage). `0xC4124` = `[0,0,5,0,5,5,0,0,0,5,0]` puts slots
   {0,1,3,6,7,8,10} at mode 0 (raw passthrough) and {2,4,5,9} at mode 5 (forced zero).
   **This explains why its sign agreed with openpilot's command at CHANCE (52.80 % vs 54.36 %) while
   flipping 8.2/s against the command's 0.31/s.** Much inherited reasoning about "the LKAS lane" rests
   on the wrong label.
2. 🛑 **V101's GATE 2 premise is MEASURED FALSE.** `builds/v80_v107/build_v101_tva.py`: *"The LKAS command enters the
   control loop as an EXOGENOUS INPUT… doubling the gain doubles the EXCITATION but does NOT change any
   closed-loop pole."* **The pole moved (20.3 → 23.0 Hz) and the demand itself now oscillates there.**
3. 🛑 **The D-term damping crossover is 22–26 Hz, not ~14–16 Hz.** The measured Re(Z) from three drives
   puts 12–16 Hz as the **third-most anti-damped** band. Supersedes the "D damps 16–35 Hz" line in
   `reference_accord_vehicle_bus_clearance_and_aggregator_probe_reaim_2026-08-11.md`, whose cited
   "parallel PID trace" could not be located.
4. 🛑 **`band_envelope` IS BROKEN IN TWO SHARED HELPERS** — `analysis-2020accord/lib/_r31_common.py` and
   `rlog-tools/lib/_r2b_common.py`. Both build `H[band] = 2*X[band]` on a **one-sided** spectrum then call
   `irfft`, forcing a REAL output, so `abs()` returns the **rectified** band-passed signal ×2, not an
   analytic envelope. `_r31_common`'s docstring asserting *"this is the AMPLITUDE A"* is **wrong**:
   median = 1.414A, RMS = 1.414A, and `2 * band_envelope` (used as peak-to-peak at
   `studies/gates/analyze_bus_amplitude_vs_detector_T.py:282`) is **2× too large**. **Ratios between conditions are
   unaffected; every envelope-SHAPE result — growth rate, decay τ, ring-down ζ/Q, p50 "amplitude" — is
   wrong.** ~20 callers. **REPORTED, NOT FIXED.**
5. **PID gain addresses settled** — `0xC6ADC`/`0xC6B08`/`0xC6B1C` are table **headers**;
   `0xC6AE6`/`0xC6B12`/`0xC6B26` are **Y[0]** at header+0xA. Kd and Ki are **flat at all four knots**
   ⇒ pure scalars, no knot-crossing risk. **All three N = 0/102, fully virgin.**
6. **`0xC6446` is NOT "10×".** Honda's 512 is **INERT** (the stock gate never fires); the live stock r24
   gain comes from the speed×rate LERP. **5244 = 2.00 × 2622**, the LERP's own value at grind #1's
   measured point (7.2 km/h, 128 °/s), and **the ratio drifts from 2.00 elsewhere.**
7. **`gp-0x4f62` is a 4-SAMPLE finite difference** — `2*(x[n] − x[n−4]) / 4` in **torque counts**, delay
   cal `tp+0x7c42` = `0xC6C42` = 4. ⚠ **The divisor is the SAMPLE DELTA, not `dt` in seconds** — reading
   it as `/dt` puts every value 1000× high.
8. **`0xC646E` (1428) is a lagged velocity damper running at 1–6 % of its clamp**, not an inertia lever,
   and it is a **different lane** from `gp-0x6b26`. Effectively dead.
9. **`0xCBE74` records vs Y arrays**: records `0xD6A64` (m24) / `0xD7A44` (m25) / `0xD7A54` (m26) /
   `0xD7A64` (m27); **Y arrays at +8.** Car is TVCA4: **24/25 MANUAL, 26/27 ENGAGED.**
10. **A verifier defect worth adopting kit-wide**: attributing a changed byte-run by its **first
    address** mislabels any **single-high-byte** cal edit (`4096 → 3072` moves only `0xC61B3`).
    **The failure mode is a FALSE ALARM on a correct build — which is how a good build gets pulled.**
    Attribute by **intersection with the byte set actually written**.
11. 🛑 **V102's IDENTITY ASSERTS A *CLEARED* BIT — a first for this kit, and a weakness.**
    `(byte7[7:6]==3 AND b3==0)` shares byte7 code 3 with V101, so **a stuck-low bit or a cleared mask
    forges it**; every prior identity asserted a bit **SET**. The structural argument still holds
    (V101's b3 is an unconditional constant 1 ⇒ `(3,0)` is unreachable on V101; a total cave failure
    leaves `byte7[7:6] ≠ 3`), and the 2-bit field is genuinely exhausted with every byte4 data bit
    spent — so V102 ships as built.
    **MITIGATION, mandatory at scoring time:** identity is PROVEN only when `byte7[7:6]==3 AND b3==0`
    **AND the PASS-3 sign bits (b7, b4) are live and flipping.** `rlog-tools/score/score_v102.py` implements
    this and reports **UNPROVEN** when only b3 differs.
    ⭐ **V103 RULE: GO BACK TO A SET BIT.** Generation-3 space is exhausted; V103 must sacrifice a data
    rung or hook a second CAN ID, and should pick whichever lets identity assert a **1**.
12. **Cache-layer traps, reported not fixed**: `_scratch/cache/r71` lives at the **repo root**, not under
    `analysis-2020accord/` — **two cache roots, and no resolver outside `rlog-tools/lib/v102_xb_lib.py`**.
    **`v84_r24_*` columns are written into EVERY cache but are meaningful only on V84's route** — a
    cross-build misdecode waiting to happen. `extract_r95.derive()`'s docstring calls `v_rear` km/h
    when it is **m/s**.

---

## 9a. THE THREE HABITS THAT CARRIED EVERY RESULT

Recorded verbatim from the analyst who produced the load-bearing numbers, because each one changed an
answer this session:
1. **Run the placebo pair FIRST.** r75 vs r76 (two drives on byte-identical V89 firmware) gave a
   **shape floor of 1.45×** at 22–26 Hz versus a **raw-band floor of 2.18×** — twice as sensitive — and
   it caught V91's **0.75× whole-spectrum offset** that would otherwise have manufactured a fake `k`.
2. **Stratify on WHEEL RATE, not just speed.** The naive pooled contrast came out at 4–5× and was
   **entirely exposure**: the excess appeared in the pre-declared 32–38 Hz negative control band too.
3. **Check the sample rate before believing a null.** The "the line is not in the firmware's own demand"
   result was measured in the wrong band on an assumed 41.7 Hz; the caches say **49.79 Hz**, so 23 Hz is
   below Nyquist and directly observable. **The null was retracted.**

---

## 10. OPEN ITEMS

- **No route in the corpus has LKAS-off exposure ≥20 km/h** (r85 0, r95 0, r75 0, r76 5, r77 0).
  ⇒ **engagement-specificity of the 23 Hz line is NOT established.** An earlier 6.73–8.15× engaged÷manual
  figure was **withdrawn** — it compared engaged-at-road-speed against manual-at-standstill.
- **The Q/width disagreement (§4) is unresolved.**
- **`0xC63AA`** remains the best *structural* zero-DC-cost lever (1 reader, 0 writers, virgin, DC cost
  zero by construction) but needs the **dilution ratio** — `gp-0x6b4c`'s share of `gp-0x6b98`'s sum —
  before its sign can be signed. **V102's 427 repoint + b7 supplies exactly that distribution.**
- **Which of the 11 assist slots is LKAS's**, and whether the other mode-0 slots are live during engaged
  driving, is untraced. If a base-assist slot carries the 23 Hz ripple, the causal story changes.
- **The FOC current/thermal limit has never been located** (`FUN_00071272`).
- **`0xC6202` = 4762**, the governor's flat nominal, is the tightest clamp in the chain and has **never
  moved in 62 builds**. Not editable — `gp-0x4f64` is shadowed ⇒ DTC `0x17`, hard-fault-eligible.

---

## 11. WHAT IS NON-STOCK ON THE ECU AFTER V102

See §7 for the V101→V102 delta. **The cumulative delta vs Honda stock is unchanged from V101 except for
the three cells above** — the 8× becomes 6×, the two clamps track it down, the cave grows, and the 427
source moves. Everything else — the EME corridor, the boost floors, the LKAS clamp taper, the V42
governor byte, the V89 friction K1, the V92 acceleration-lane ×1.5, the V99 relay knee — is carried
forward from V101 unchanged and asserted at build time.

---

## 12. HOW THIS BUILD DIFFERS FROM THE ARC SINCE V38

**Class of intervention: this is the FIRST build in the whole post-V38 arc to move `0xC6CD0` DOWNWARD.**
The gain has been frozen at exactly 4× (3564) on **every build from V38 to V100** — 62 builds — and V101
was the first to move it at all. The arc: V38–V52 authority/filters/poles/caves · V53–V61 telemetry and
lane mutes · V62–V73 the rate lane · V74–V83a the base-assist damper · V84 damper reverted · V85–V99 the
observer/friction path · V100 a zero-calibration instrument · V101 the 8× · **V102 the first downward
gain step, chosen by the operator from a measured dose-response curve.**

**What is genuinely new:** a **measured dose-response on the gain cell itself**, with a benefit:cost
ratio, put to the operator as a choice. **What is a re-run:** nothing — no prior build has moved this
cell down. **Why a different result is likely:** the previous 62 builds all searched for a *lever* while
holding the gain fixed; this session proved by de-confounded measurement that **the gain is the carrier
and every other lever is dead**, so the only remaining variable is the one that was never allowed to move.
