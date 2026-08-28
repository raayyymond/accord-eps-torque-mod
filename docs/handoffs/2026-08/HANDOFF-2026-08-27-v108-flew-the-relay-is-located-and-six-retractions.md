# HANDOFF — 2026-08-27 (late) · V108 FLEW · THE COULOMB RELAY IS LOCATED · **SIX RETRACTIONS**

> **Read `docs/STATE.md` first.** This is the narrative; STATE is the live state. Everything here is
> committed and pushed on `main` in both repos.

---

## 0. THE ONE-PARAGRAPH VERSION

V108 flew and its rail-duty prediction held across a build change. The **command-proportional Coulomb
relay** the kit has named since V80 was **located in the code** for the first time, both its gates
were closed, and its cost was priced. Two builds are on disk and unflashed. **The acoustic price of
the 6× gain was measured against a stock control.** And **six claims made during this session were
retracted or qualified by their own controls** — that ratio is the honest signature of the day, and
every one is recorded rather than quietly dropped.

---

## 1. WHAT IS ON THE CAR, WHAT IS BUILT

| | build | state |
|---|---|---|
| **on the car** | **V108** | flew 2026-08-27, fault-free. Operator: high speed *"has been fixed"*; ≥20 mph *"the best it's ever been at 6×"*; low speed unchanged |
| built, unflashed | **V109** | V108 + `0xC40DC` α2 22→14. 1 payload byte |
| built, unflashed | **V111** | V109 + 427 tap re-point. 3 payload bytes |
| **PARKED — do not flash** | V110 | killed twice over (§4) |

```
V108  image 7a9577dd…  .rwd 4fbfda0d76af2f1b…
V109  image e9eb51fc…  .rwd 83047f0fd3b5b656…
V110  image 3de48a49…  .rwd becaab6d7ecce18d…   PARKED
V111  image 9c4865cf…  .rwd 221d99c605d2d9d9…
```
All four tracked and pushed in `accord-firmwares`; working tree clean, in sync with origin.

### 🛑 THE FLIGHT-ORDER CORRECTION — **V109 AND V111 DRIVE IDENTICALLY**
⚠ **I recommended "V109 first, then V111" repeatedly during this session. That was WRONG.**
Every dynamics cell is byte-identical between them — α2 = 14 on both, knee 600, gain 5346, the
`gp-0x6b26` row, the biquad. **V111 is V109 plus three telemetry bytes.** The choice is which
measurement the drive buys:
- **V109** → tap on `gp-0x6c2c` (sizes the `gp-0x6b26` Y row, open since V107)
- **V111** → tap on `gp-0x6abc`, **the relay's input amplitude**

⭐⭐ **RECOMMEND V111.** GATE 2 shows the knee only bites **below ~200–400 counts** of `|gp-0x6abc|`
(describing-function ratio 0.96–0.99 above ~400). **That amplitude decides whether the ratchet lever
exists at all.** Both builds deliver the identical α2 test, so nothing about the fix is given up.

---

## 2. ⭐⭐ THE HEADLINE — THE COULOMB RELAY IS **LOCATED**

`FUN_0003b8f6` @`0x3B8F6`. The kit has described this mechanism since V80 without ever pointing at
the instruction that makes it a relay:
```
iVar20   = POL * gp-0x6abc * 12                        # POL = *(char*)(gp-0x6752)
fVar13   = clamp(iVar20 / cal(0xC40BC), -1.0, +1.0)    # <-- THE RELAY.  tp+0x50bc
friction = EMA(|model| * cal(0xC40D2)/1024 * fVar13
               + cal(0xC4080)/1024 * fVar13,  pole cal(0xC40D0))
gp-0x6ae2 = friction * 1024
iVar20   = (model - friction - inertia) * gain
```
Below the knee it is **linear in rate (viscous)**; above it a pure **±1 sign (Coulomb)**.
**Saturation at `|gp-0x6abc| ≥ knee/12`:** stock 300 → 5.3 °/s; **V108's 600 → 10.6 °/s**.
⭐ **V108's corner sits at the bottom edge of the 8–20 °/s band where the ratchet isolates.**
⭐ **`0xC4080` = 0** ⇒ no Coulomb floor; the term **vanishes with no command**, confirming
*"command-proportional"* at the instruction level rather than by inference.

### ✅ GATE 1 — CLOSED, two methods agreeing
Exactly **one** tp-relative access image-wide at file `0x3BAB4`, zero writers. Python LE scan
(`disp16 ∈ {0x50BC, 0x50BD}`, base-filtered) and the decompile agree on count and location.
⚠ Residual: neither method sees register-indirect access to a cal.

### ✅ GATE 2 — CLOSED. No phase risk, but the **same sign reversal that killed Kd**
The knee is an **odd, memoryless saturation** ⇒ describing function **real at every amplitude** ⇒
**zero added phase, cannot rotate into a new sector.** GATE 2 does not block it.
🛑 **But the lane reverses sign between 16–18 and 18–22 Hz** (EMA `cal(0xC40D0)` = 408, corner
15.9 Hz, rotated through the measured `arg Z`), and a magnitude-only knee raise shrinks `|H|` in
**every band at once**:
```
  band     f Hz   |H_f|  argH_f  cos(argZ+argH)  |H|*cos
  6-9      7.79  0.9063  -23.6     -/+ 0.865      0.784   <- RATCHET
  18-22   20.00  0.6414  -46.6     +/- 0.254      0.163   <- GRIND
  22-26   24.00  0.5717  -50.9     +/- 0.602      0.344   <- GRIND
  26-31   28.50  0.5062  -54.6     +/- 0.983      0.497   <- GRIND

  benefit 0.784  vs  cost 1.004   =>  ~1.28 : 1 AGAINST
```
⭐ **Far better than Kd's 2.9–4.4:1 — which is exactly why Kd is dead and this is not.**
⇒ **A genuine TRADE the operator must choose, not a fix.** How ratcheting weighs against 18–31 Hz
grinding is his judgement, not a number this kit can settle.

### THE INSTRUMENT — V111, and why it is a probe not a dose
The assist cost is **large and unmeasured**: friction clamps at ±10.0 float ⇒ `gp-0x6ae2` spans
**±10,240 counts** against a residual clamped at **±20,000** ⇒ up to **51 % of the residual range**,
and by the verified polarity ([[accord-friction-polarity-more-assist]]) raising the knee **reduces
assist** — the direction that made V93/V94 undriveable. **V111 measures the amplitude before any
dose is spent**, at 3 payload bytes and **no cave edit** (outside the only bricking class).

---

## 3. ⭐ THE OTHER SURVIVING RESULTS

### 3.1 The ratchet and the 20–26 Hz grind are **COMMAND-GATED**
Band SHAPE (power normalised by 1–3 Hz in the same window), <20 mph, engaged, hands-off:
```
  fold-rise vs <1k cmd   3-5 ctl   6-9 RATCHET   10-13 ctl   14-18 ctl   20-26 grind
  1k-2k                     0.7x         3.0x        0.7x        1.1x         4.0x
  2k-3k                     0.6x         4.7x        0.7x        1.1x         5.7x
  3k+                       1.9x        52.0x        3.3x       12.7x        11.8x
```
⭐ **Two control bands FALL while 6–9 Hz rises.** And the 2-D control separates it from the known
rate effect: **at matched rate (8–20 °/s) command drives a 48× fold; at matched command, rate drives
2.8×.** ⇒ genuinely command-gated. **Sixty builds hunted a LINEAR lever for a command-triggered
nonlinearity.**

### 3.2 The acoustic cost of the gain is **MEASURED** — +1.16 dB from 4× to 6×
Eleven-route spectrogram ladder **with a STOCK arm**. Statistic **MECH (60–400 Hz) − FAR
(1200–2000 Hz)**, engaged-minus-manual, matched speed <10 mph, hands-off, within drive.
```
  gain   n     MECH     FAR   MECH-FAR        6x - 4x = +1.158 dB [+0.475, +1.817]
   1x    1    +0.01   +0.74     -0.73         P(>0) = 1.000
   4x    3    +0.36   +1.16     -0.80         8 of 9 routes outside their own null
   6x    6    +0.95   +0.58     +0.36
   8x    1    +2.01   +0.39     +1.62         n=1 for stock and 8x
```
⇒ **goals #1 and #4 are in tension THROUGH THE GAIN, now numerically.** ⊕ Independently consistent
with `accord-the-8x-gain-is-the-carrier`, from the 20–26 Hz steering-rate band — **two unrelated
instruments, same conclusion.** 🛑 A **price, not a prescription**.
✅ **And NOT command-modulated** (within-engaged high-cmd vs low-cmd: signs both ways, stock in
range, no ordering) ⇒ **a command-domain lever cannot reach it. V111 must not be expected to.**

### 3.3 The two symptom families are cleanly separated
| family | instrument | command-gated? | lever |
|---|---|---|---|
| 6–9 Hz ratchet + 20–26 Hz grind | steering RATE | **YES**, 48× at matched rate | the relay knee — V111 tests reachability |
| 60–400 Hz cabin noise | AUDIO | **NO** | **none but the gain** |

### 3.4 Closed cheaply, before they cost a drive
- **`gp-0x69b0` authority ramp RETIRED** — all five rate cals mapped (`0xC63F4/F6/F8/FA/FC` =
  328/16/33/66/328, virgin); **STEER_STATUS is identically 0 over 3,312 s engaged, zero transitions**,
  control passes (status 3 exists, only at 0.0 mph, only disengaged). ⭐ **Correction:** the record
  files `0xC63F8`/`0xC63FC` as a *"10× LEFT/RIGHT asymmetry"* — `gp-0x6803` is a **MODE fork** (three
  values, two parallel SM chains). Right answer, wrong reason.
- **The Kd lever CLOSED entirely** — `0xC6AE6` is **one knot of a FLAT four-knot LERP**
  (X = 50/400/1500/3000, Y all 2048). ⭐ **On a flat table a one-knot edit is never a gain change** —
  it converts a constant into a rate-dependent nonlinearity. ⭐ **GATE-1 RULE ADDED:** counting
  *accesses* to a cal cannot tell a scalar from a table knot; read the **reader's structure**.
  ⚠ **`Ki` (`0xC6B12/14/16/18`, flat 98) is the same shape and `BUILD-LINEAGE.md:397` floats it.**
- **The V36-blanked cells** `0xC61C0/C2/C4` — benign, correctly in force since V37.
- **openpilot's `STEER_MAX` = 4096** is a hard clamp (histogram spikes 13,783× at the edge; zero
  frames above it in ~200 caches), railed **40 % / 37 % / 21 %** below 6 / 6–10 / 10–15 mph.

---

## 4. 🛑 V110 IS DEAD — TWO INDEPENDENT KILLS
1. **The sign.** `cos(argZ + argH_D)` = **−0.802 at 7.79 Hz but +0.894 at 20 Hz** — D pumps at the
   ratchet and **damps** at 18–31 Hz. Replicated on three drives; 18–22 needs τ ≥ +8.6 ms to flip and
   26–31 needs τ ≤ −5.9 ms — **opposite directions, so no single skew saves it.**
2. **It is not "Kd 2048→1024"** — one knot of a flat LERP (§3.4).

---

## 5. 🛑🛑 SIX RETRACTIONS — every one caught by its own control

| # | claim | what killed it |
|---|---|---|
| 1 | *"the gain scales NOWHERE"* | no hands-off mask — **measured the DRIVER**, not LKAS |
| 2 | *"the gain stops delivering at low speed"* | **speed-matching**: with 2 mph cells, 1.292 [0.925, 1.673] — 1.500 INSIDE. The `<15 mph` bin held a speed gradient (6.2 vs 8.3 mph medians) |
| 3 | *"confirmed within-route"* | same mismatch hidden in a denominator — looked like corroboration, wasn't |
| 4 | *"it is stick-slip"* | its own test: stuck duty **falls** with command, 0.609 → 0.009 |
| 5 | *"the ~100 Hz mode is ours"* | three **adjacent control bands rise equally**; residual ≤ 0 on 6 of 10 routes |
| 6 | *"an 83.5 Hz comb is the grinding"* | **STOCK fires too**; plus a **sub-harmonic ambiguity** (a comb at `f0` always scores at `f0/2`) |

⊕ A seventh was an **over**-retraction, corrected in the conservative direction: stock's comb sits at
49.5 Hz with a **null 2× (−0.14 dB at 99 Hz)**, matching the third-octave stock reading, so the two
findings agree rather than conflict.
⊕ An eighth test was run and is **uninformative rather than null**: the odd-harmonic test. A Q 14–29
plant attenuates 3f by **12,500–54,000× in power**, so the null was guaranteed either way.

### ⭐ THE TWO METHOD RULES THIS SESSION EARNED
1. **A narrow-band acoustic claim needs ADJACENT CONTROL BANDS.** The steering-rate work always did
   this and its results held; the acoustic work did not, and two claims died. The spectrogram makes
   controls free.
2. **When a claim's whole force is "this is OURS", build the STOCK arm BEFORE publishing.** r97's
   rlogs were on disk the entire time and cost one background job.
⊕ And: **to test for a torque ceiling, measure ACCELERATION, not rate** — rate is an integral, so a
rate-vs-command test is structurally blind to it. That is why V108's E3 null was correct *and* could
not have seen what it was later asked about.

---

## 6. NEW TOOLS (all committed)
| path | what |
|---|---|
| `rlog-tools/decode/extract_route_audio.py` | spectrograms for **any** route, prefix auto-discovered. Eleven built |
| `rlog-tools/score/band_100hz.py` | fixed-band engaged-minus-manual with null + control bands |
| `rlog-tools/score/comb_score.py` | harmonic-comb score; **refuses to report without a null** |
| `rlog-tools/studies/authority/steer_max_saturation.py` | the `STEER_MAX` / ramp tests |
| `rlog-tools/studies/authority/gain_delivery_and_command_gate.py` | gain delivery + the command gate |
| `analysis-2020accord/builds/v108_plus/build_v111_tva.py` | the relay probe, 36/36 |

⚠ **`V106B.assert_frozen` is THREE BUILDS STALE** — V107 (tap), V108 (knee, sar) and V109 (α2) all
legitimately moved cells in it, so it fails on *correct* edits. `build_v111_tva.py` uses a
**base-relative** form instead. **Any builder inheriting `V106B.FROZEN` has the same latent bug.**

---

## 7. OPEN ITEMS — with what would close each

| open | closer | drive? |
|---|---|---|
| Relay operating amplitude `|gp-0x6abc|` | **fly V111** | **yes** |
| Does α2 help the low-speed grinding | fly V109 **or** V111 (identical dynamics); score **MECH − FAR** vs V108, same road | **yes** |
| Does the gain deliver at low speed | matched hands-off segments 2–15 mph at large command, both a 4× and a 6× build, same road | **yes** |
| `arg Z` phase slope (−7.80 deg/Hz) | on-car gain-step system ID at 18–31 Hz | **yes** |
| `gp-0x6b26` Y-row solve | needs the `gp-0x6c2c` tap ⇒ **V109**, not V111 | **yes** |
| Cross-drive acoustic comparability | **drive-card manoeuvre 0**: 30 parked seconds, engine on, HVAC off | **yes** |
| Assist cost of a knee dose in counts | `gp-0x6ae2` magnitude — needs a cave rung | **yes** |
| Global sign convention | one Ghidra trace `gp-0x6ad4` → delivered motor torque | no |
| `Ki` flat-LERP trap | read all four knots before any Ki proposal | no |

🛑 **Nearly everything left is drive-gated.** The corpus has been mined with stock controls,
adjacent-band controls, within-engaged contrasts and route-level bootstraps.

---

## 8. THE FIVE GOALS — honest status

| goal | status |
|---|---|
| **Eliminate audible grinding** | **Splits in two.** The 6–9/20–26 Hz pair is command-gated with a candidate lever (V111 tests it). The 60–400 Hz cabin noise is **priced at ~1.2 dB for 4×→6× and has no lever but the gain** |
| **Eliminate visible oscillation** | **Closed** — openpilot's lateral loop (command leads angle +46.8°, hands lag −63.2°, car follows every event). **His call**, not a firmware lever |
| **Eliminate ratcheting** | Mechanism **located**, both gates closed, **~1.28:1 trade priced**. V111 decides reachability |
| **6× LKAS torque** | **Delivered** |
| **Higher max angular velocity** | Bounded by openpilot's **`STEER_MAX` = 4096**. A second firmware-side ceiling was claimed and **RETRACTED as underpowered** |

🛑 **A 100 % guarantee was not achievable and is not claimed.** Two goals have limits outside a
calibration edit; the third has a mechanism and an instrument but needs a drive. That was stated
plainly to the operator throughout rather than at the end.
