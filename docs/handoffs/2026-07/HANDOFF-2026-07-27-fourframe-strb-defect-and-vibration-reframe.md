# HANDOFF 2026-07-27 — FOURFRAME never transmitted (STRB/SSAM defect), and the vibration model is reframed

**Nothing was flashed. No CAN was sent.** Two builds were produced, both unflashed.

This session answered the operator's two questions:
1. *"FOURFRAME's frames are absent from the rlog — could it be our firmware?"* → **Yes. Confirmed defect,
   root-caused, fixed, rebuilt.**
2. *"What else can we try for the 4×-gain vibration?"* → substantial progress, **mostly by elimination**,
   plus three retractions of claims made earlier in this same session.

---

## 1. ★ CONFIRMED DEFECT — FOURFRAME's mailboxes were configured "not used"

The cave wrote **`STRB = 0x80`** to mailboxes 16–19. Per the V850E2/Px4 manual (p.1249/1268), `STRB` is
`bit7 SSOW | bits6-3 SSMT[3:0] | bit2 SSRT | bit1 | bit0 SSAM`, and:

> `FCNnMmSSAM` — Message Buffer Assignment: **0 = Message buffer not used. 1 = Message buffer used.**

§20.8.1 makes `SSAM = 1` a hard precondition for a buffer to join the transmit priority search. `0x80`
sets `SSOW` (the **receive-side** overwrite control, meaningless on a TX buffer) and leaves `SSAM = 0`.

**Empirical corroboration, decoded from stock `FUN_0001cf30`:**
- TX mailboxes 0–6: `mov 0x1,r23` @`0x1D02C` → `st.b r23,0x24[r24]` @`0x1D08C` ⇒ **`STRB = 0x01`**
- unused free pool 7–32: `st.b r0,0x24[r10]` @`0x1D1AC` ⇒ **`STRB = 0x00`**

`0x80` has bit0 clear — **the same as the unused pool.** The frames never left the CAN controller. No
gateway, harness, or panda was ever involved.

**Root cause:** `builds/telemetry/build_vcantx_test_tva.py:54` labelled bit7 `SSOW` as "TX direction". FOURFRAME inherited
it verbatim. **The VCANTX seed carries the same defect** and would also have been silent.

**Everything else in the cave was correct** — target addresses (`0xFF481024 + m*0x40`), `MID0W` as a
32-bit `ID<<18` with IDE=0, `DTLGB = 8`, and `CTL = 0x0100` then `0x0200` byte-identical to stock's own
sequence at `0x1D7EE`/`0x1D7FC`.

### Consequence: the gateway-whitelist theory is WEAKENED

`0x19F` was the strongest control for "a downstream gateway drops unknown IDs". It is **not a clean
control**: its callback `FUN_00055F2E` is an unconditional `return 1`, but **slot 8 is gated at its
request site** — `0x5559E andi 0x40,r15,r16` → `FUN_0001eaa6` (enable) / `FUN_0001eaf4` (disable) — and
**there is no equivalent conditional site for slot 9 (`0x18F`)**. `0x1AB` goes through the same gated
structure and *does* reach the bus, so the difference is one runtime bit in `[gp+0x6400]`, not the
mechanism. That bit is a dynamic status word (~90 readers, 3 writers) and is not statically determinable.

**Do not cite the absent-ID set as gateway evidence without first pinning `[gp+0x6400]` bits 4/6.**

### Piggyback channel corrected: 11 bits, not 16

- `0x18F` byte5 bits **5-4 are LIVE** (`gp-0x6880 & 3`, packer `0x55CAE`–`0x55CC2`) → 6 bits free
- `0x14A` byte4 bits **2-0 are three live status flags** (`gp-0x679a/9b/99`) → 5 bits free
- Both bytes are **inside their frame checksums** — any piggyback must write before `FUN_00057b24`
- They read constant on route 13 only because those live bits happened not to change

---

## 2. Builds produced (both UNFLASHED)

### FOURFRAME2 — the fix, plus a re-spent payload
```
_vfourframe2_plain_image.bin  SHA 826809239588355ae3724565612083a8cd219fd456d4d0a548237b7933f2976c
39990-TVA,A160-FOURFRAME-...-onV38-STRB01FIX-authority-refmodel-0x13000-0x100000.rwd
                              SHA 8de8372e1fafd32455e9cf0db6473ebbe0652827cf30fc67a79379a93a654a22
```
**12 bytes differ from the image on the car**, verified by independent byte diff:
```
0x0C4B6C / 0x0C4C1C / 0x0C4CCC / 0x0C4D7C   80 -> 01     (STRB, SSAM=1)
0x0C4D42                                    2395 -> 9b96 (ld.hu -0x6ade -> -0x6966  AUTHORITY)
0x0C4DF2                                    5598 -> 2b95 (ld.hu -0x67ac -> -0x6ad6  reference model)
0x0C4FFC                                    MAIN CRC
```
Both replaced slots were dead weight (`gp-0x6ade` has 0 writers image-wide; `gp-0x67ac` is proven
constant 0 on the A160), so nothing was given up. The payload now captures **all three terms** of the
prime suspect loop: `gp-0x4f60` (sensor), `gp-0x6ad6` (model), `gp-0x6ad4` (output).

⚠ **`_vfourframe_plain_image.bin` was deliberately NOT overwritten** — it is the record of the image that
produced the route-13 rlog, and Ghidra is backed by it.

⚠ **ALIASING LIMIT:** FOURFRAME2 still transmits at **100 Hz** and samples instantaneously. A true mode
at 78.91 Hz folds to exactly 21.09 Hz. **FFT-ing this telemetry cannot distinguish them.** The
non-commensurate tick was deliberately *not* stacked onto this build — the cave has never once
transmitted, so changing the rate in the same step would make a null uninterpretable. **Prove TX first.**

### The `0xC646C` decoupling — designed and verified, NOT built
One 2-byte retarget. See §4.

---

## 3. The vibration — what changed, including three retractions

### ★ The A/B/C split (the strongest new result)
Raw CAN 399, `STEER_STATUS=(d[4]>>4)&0xF`, `STEER_CONTROL_ACTIVE=(d[4]>>3)&1`. Invariant check passes
(0 frames with SCA=1 alongside ST=3). Hands-OFF, `vEgo>0.3`, Nfft=128/hop=64:

| cell | K | peak | P(21.09) | mean \|cmd\| |
|---|---|---|---|---|
| **A** openpilot off | 18 | 0.78 Hz | 5.28e3 | 0 |
| **B** commanding, EPS in lockout (SCA=0) | 5 | 0.78 Hz | 7.02e3 | 2,749 |
| **C** commanding, EPS **applying** (SCA=1) | 17 | **21.09 Hz** | **1.03e8** | 2,529 |

**C/B = 14,750×. B/A = 1.33× (noise).** openpilot commands *harder* in B than C.
⇒ **The vibration requires the EPS to actually APPLY LKAS torque. Merely transmitting does nothing.**

**Confound, honestly stated:** on this route `SCA` is a deterministic function of speed (ST=3 *is* the
sub-5 km/h gate); B and C have zero speed overlap. Partial rescue: cell A spans both ranges, and
**A-high (mean 1.67 m/s) vs C-slow (mean 1.67 m/s) differ by 578×**; within C, speed is irrelevant
(corr −0.040, K=102). So speed alone does not produce it. **Cannot exclude** "needs v>1.4 m/s *and* OP
engaged, with applied torque incidental" — B2 and C-low are both empty on this route.

**The discriminating experiment is the `0xC62EA` cal edit** (320→64, lockout 5 km/h→1 km/h) from the
low-speed workstream: it populates C-low. Cal-only, already located.

### 🛑 RETRACTION 1 — the 21 Hz IS in the openpilot command
The premise "we don't see the resonance in the output LKAS torque CAN signal" is **false**, and the
reason is a genuine trap: **`0xE4` appears on src=2 and src=128, both identically zero in 100% of ~22,395
frames each.** Only **src=129 (bus 1 TX echo)** carries data (10,177 of 22,390 nonzero) — verified by the
lead independently. Looking at bus 0 or bus 2 shows a flat line.

Magnitude is **disputed between two methods and unresolved**: the subagent's validated pipeline (which
reproduces the established K=25 / P=7.03e7 benchmark) reports the command's 21 Hz at **+12.0 dB over its
own shoulder, rank 1 of 47 bins in 8–45 Hz**; the lead's independent (cruder, run-concatenating) pass got
**+1.7 dB**. Both agree the sensor is far stronger (+19 to +26 dB). **Treat "21 Hz is present in the
command" as established and the magnitude as open.**

Coherence(command, CAN399) @21 Hz = **0.685** (1/K floor 0.040, 95% null 0.117) vs **0.171** at 1–3 Hz.
⚠ Coherence is symmetric and does **not** establish direction.

### 🛑 RETRACTION 2 — "openpilot cannot oscillate at 21 Hz because of latency" was bad control theory
Delay does not preclude high-frequency oscillation; it creates a **comb** of frequencies where phase
wraps to a multiple of 360°. What closes a loop off at high frequency is **gain rolloff**, and the
measured openpilot rolloff at 21 Hz is only **−2.70 dB** — *less* than at 14.8 or 25 Hz, because the peak
pokes through it. **There is no OP-side low-pass at 21 Hz**, and the controller output itself carries the
peak (+9.3 dB over shoulder, rank 1 of 47).
⇒ **An OP-side 21 Hz notch is UNTESTED, not a no-op.** Zero brick risk. This is the recommended next test.

### 🛑 RETRACTION 3 — the saturation hypothesis is empirically dead
The lead proposed that 4× pushed `FUN_00036682`'s hardcoded ±512 clamp into saturation (threshold falls
from `|gp-0x4f60| ≥ 18,829` at stock to `≥ 4,707` at 4×). Tested against real telemetry:
```
route 13, 10,178 active-LKAS CAN399 frames:
  |STEER_TORQUE_SENSOR|  p50=576  p90=2325  p95=2645  p99=3056  MAX=3530
  frames >= 4x threshold (4597): 0   (max reaches only 76.8% of it)
```
Corroborated on the archived b9 route (54,445 frames, also 0). **The clamp never engages. Dead.**

### Openpilot build on the vibration route
`openpilot 0.10.3`, branch **StarPilot**, `github.com/firestar5683/openpilot.git`,
commit `8640f060548ecf92cc2b6f3b5c1e8b1e66bdf9ae`, device `mici`. `steerActuatorDelay=0.10`,
`steerLimitTimer=0.80`, `minSteerSpeed=0.0`, `steerAtStandstill=False`, `STEER_MAX=4096`.
⚠ **14.0% of gated frames are at the ±4096 rail, and railed windows show no 21 Hz** — keep the rail
fraction comparable between baseline and notched runs or any retest is confounded.

### 21 vs 78.91 Hz aliasing — test ran, INCONCLUSIVE, leans 21.09
The comma IMU is the only non-commensurate channel in the log: measured ODR **101.049 Hz** (accel) /
101.043 (gyro) — *not* 104 — so the alias target is **22.14 Hz**, separation 1.049 Hz. Lomb-Scargle on
irregular hardware timestamps was validated on synthetic injections (21.09→21.090, 78.91→22.120).
**Real data: a perfect tie at the noise floor.** Cause identified: the steering barely couples into a
windshield mount (MSC 0.009–0.265 at 21 Hz), and the gyro's sensitivity floor is **1,770× below** the
wheel's measured motion — so the null is about **coupling, not existence**.

Two indirect discriminators, both favouring 21.09, neither airtight:
- **Linewidth → implied Q.** Measured −3 dB width 1.099 Hz ⇒ **Q = 19.2 at 21.09 Hz** vs **Q = 71.8 at
  78.91 Hz**. Q≈72 for a bushed, greased, friction-loaded steering system is not credible.
- **rate/angle amplitude ratio** (self-calibrated against the 3.12 Hz bin): measured **6.51**, predicted
  6.75 for a true 21.09 Hz derivative, **25.25** for 78.91. ⚠ **Void if the sensor forms rate as a 100 Hz
  first-difference** — both hypotheses then predict 6.28, and the two models could not be separated
  (log-residuals 2.7% vs 3.1%).

⚠ Cutting the other way: a 100 Hz ZOH command containing 21.09 Hz puts energy at 78.91 Hz only −11.5 dB
down, so a 78.91 Hz mode driven by that image and resampled at 100.000 Hz folding to exactly 21.09 Hz is
fully self-consistent. **The rlog cannot close this.**

---

## 4. ★ `0xC646C` is NOT "the LKAS authority gain" — CORRECTION OF RECORD

Independently enumerated **twice** (subagent + lead byte scan, both encodings, `disp|1` form included):
**exactly 6 readers, no stores, no float mirror**, and **neither hard-shutdown monitor is among them**.

| # | addr | function | multiplicand | verdict |
|---|---|---|---|---|
| 1 | `0x2a1ee` | `FUN_00028ea6` arbitration | IIR-blended LKAS setpoint × gain × polarity | **FORWARD** |
| 2 | `0x2a904` | unclaimed gap `[0x2a507,0x2a93a)` | — | **DEAD** (0 xrefs, re-confirmed on the 2086-fn program) |
| 3 | `0x2b656` | `FUN_0002b62c` (~100 Hz assist task) | gain × polarity × `0xC6428`, mode-gated | FEEDBACK (by elimination) |
| 4 | `0x2c488` | `FUN_0002c478` (1 kHz) | `(gp-0x4f60 × gain)>>15` + delivered-cmd delta | feedback-shaped, **DEAD OUTPUT** |
| 5 | `0x36686` | `FUN_00036682` (called by aggregator) | **`(gp-0x4f60 RAW SENSOR × gain)>>15`** | **FEEDBACK, full chain** |
| 6 | `0x3684a` | `FUN_00036828` (~100 Hz) | **`(gp-0x4f60 RAW SENSOR × gain)>>15`** | **FEEDBACK, feeds #5** |

**#5 verified end-to-end by the lead:** `get_function_callers(0x36682)` → exactly `FUN_0003aa2c`;
`jarl 0x36682` @`0x3acdc`; `add r14,r10` @`0x3ace6` sums the r10 return into the accumulator; clamped
±0x2800; stored to `gp-0x6b94` @`0x3acfa`/`0x3ad12`/`0x3ad20` → governor reads @`0x453e0`.

⇒ **`0xC646C` is the firmware's single shared Q15 sensor-to-command-domain scale**, reused across three
subsystems. Raising it for "4× LKAS authority" silently raised the gain on two raw-sensor feedback paths.

### But it is probably NOT the 21 Hz driver
`FUN_00036682`'s output passes a first-order IIR with coefficient `tp+0x73d2 = 14`/1024 → **fc ≈ 2.18 Hz,
−19.7 dB at 21 Hz** — and is clamped to ±512, **5% of the aggregator's ±10240**. A slow, small-authority
trim loop. Combined with the dead saturation hypothesis, this thread is closed as a *21 Hz mechanism*.

### The asymmetry is still real and worth fixing
| | gain | headroom |
|---|---|---|
| forward (reader #1) | `0xC646C` 891 → **3564** (×4) | `0xC61B4` 512 → **2048** (×4), `0xC61B2` likewise |
| feedback (#5/#6) | same shared cal → **×4** | hardcoded `±0x200` literals @`0x367E0/E4/EA/EE`, **byte-identical to stock** |

### The verified minimal fix (designed, NOT built)
No LKAS-only upstream gain exists (`FUN_00028ea6` fully decompiled; everything before `0x2a1ee` is
clamp/limit LERPs, shared IIR blend coefficients, or the runtime authority ramp). So:

1. Write `3564` at **`0xC6CD0`** — inside a verified contiguous `0xFF` run **`0xC6CA4`–`0xC6FEF` (844
   bytes)**, byte-identical in stock, **0 displacement readers and 0 `movea …,tp,rX` table bases landing
   in the run** (the check a plain displacement scan cannot do). Metadata resumes at `0xC6FF0`.
2. Revert `0xC646C` → stock **891**.
3. Retarget **only** `0x2a1ee`: `253f6c74` → `253fd07c` (`ld.h 0x746c[tp],r7` → `0x7cd0[tp]`). **2 bytes.**
4. Recompute the `0xC6FFC` CRC.

Readers #2–#6 are left untouched and automatically revert to stock. **One retargeted displacement
operand, no new instructions, no cave.** Safety argument: it *reduces* deviation from stock everywhere
except the one site the operator intended.

⚠ A prior report claimed the tail of that `0xFF` run holds a version string and an `affedead` footer.
**That is wrong** — the run extends to `0xC6FEF` and what follows is CRC linked-list metadata.

---

## 5. The `FUN_0003a382` lane — the remaining prime suspect

Architecture (verified by decompile + lead disassembly):
```
errorterm = clamp(gp-0x4f60[sensor] − clamp(gp-0x6ad6[model], ±8192), ±0x2800)
  Stage A proportional (gain ∝ motor rate, table 0xC6B20: 256 low → 153 high)
  Stage B integrator   (L2 = 98/1024 flat, table 0xC6B0C)
  Stage C derivative   (L3 = 2048/1024 = 2.0 flat, table 0xC6AE0)
combined = (A+B+C)>>5 × state-gain(gp-0x671a) × polarity(gp-0x6752)
gp-0x6ad4 = clamp(combined, ± BOUND)          ← authority enters HERE, on the BOUND
```
**Phase at 21 Hz / 1 kHz** (computed): Stage B −86.2°, Stage C +86.2° — they nearly cancel; net
**−3.3° to −5.4°**, proportional-dominated 8–10:1. **The damping-vs-anti-damping sign is NOT determined**
— it is a plant-transfer-function question. This is the single thing blocking a decision on this lane.

**Authority gates the OUTPUT BOUND, not an input gain** (lead-verified: `ori 0x8000,r0,r15` →
`cmovnh r21,r15,r15` → `mul r15,r10` → `sar 0xf`, then r10 is applied as a symmetric clamp at `0x3a88c`
before `st.h r10,-0x6ad4[gp]`). LERP at **`0xC6AF0`** (single reader, `movea 0x7af0,tp,r15` @`0x3a636`;
no float twin; inside the cal block every build already touches):
```
X (authority) :     0    3277    3604   19661   32768
Y (Q15 gain)  : 32768   32768       0       0       0
```
Unity below 3277, **clamped to ZERO above 3604** — identical stock and on-car.

**`gp-0x6966` (authority) has exactly ONE command-path reader in the whole image: `0x3a632`.** The other
five are one store (`0x432c8`) and four monitor reads. It is `|gp-0x3570>>15| × 1092>>10`
(`0xC61DA = 1092`, verified), **shadow-protected** against `gp-0x4c5a` with mismatch handler
`FUN_0006b9fa` (adjacent to the known fault-`0x17` handler → motor-off), and is **produced inside
Monitor 1 `FUN_00042af8`**. The integrator winds on **`gp-0x6acc`** (post-governor aggregate, ±8192
gated, mode-selected) versus the corridor/IIR/boost bound — **`gp-0x6806`/`STEER_CONTROL_ACTIVE` appears
nowhere in that chain.**

### 🛑 THE EDIT DIRECTION IS UNRESOLVED, AND THAT IS THE FINDING
The lead argued **mute (Y=0)** and then **keep-live (Y=32768)**, from the same data, one turn apart. Both
arguments hinged on authority's runtime value, which is **not statically determinable**. It is genuinely
open, not merely unknown: V31's boost floor sets the bound at 4096 and V38's command reaches ~4342, so
the integrator *can* wind.

**No edit to `0xC6AF0` may be built until `gp-0x6966` is measured on-car.** That is why FOURFRAME2 now
carries it.

### `gp-0x67a4` — investigated and CLOSED NEGATIVE
`gp-0x6b3c` (hence the LKAS content in `gp-0x6ad6`) is zeroed unless `gp-0x67a4 ∈ {2,3}`. Of its four
inputs: **`gp-0x67a2` and `gp-0x67a3` are unconditional literal 1** — lead-verified, `mov 0x1,r11`
@`0x2a2e4` with r11 untouched through both stores and no branch between (`0x2a2e6`, `0x2a2f4`).
`gp-0x67a1` is a `FUN_00025c32` (`distribute_clamp`) return code; `gp-0x67a7` is a truncated Q10 ramp
fraction. **Not an engagement switch.**

### PATH-A (`FUN_00038148`) — how LKAS reaches the reference model
`gp-0x6b4c` (LKAS) is **one of six equally-weighted lanes** (all six weights `0xC63A0`–`0xC63AA` = 1024
exactly), overall gain `0xC6468 = 2639`, then an EMA with `0xC63AC = 102` (**α≈0.0996, ~16 Hz corner** —
a real low-pass, unlike the unity Stage A/B/C poles). It enters `gp-0x6ad6`'s 7-lane sum with weight
`0xC64B0 = 1` (byte), same as its six siblings. No sign inversion beyond the shared polarity multiply.

⇒ Best framing: **4× LKAS shifts the reference model's operating point / steady demand level**, moving
which LERP breakpoints and clamp regions the *unfiltered* `FUN_0003a382` machinery works in — **not** a
21 Hz ripple injected into the reference (the ~16 Hz EMA attenuates that). This is consistent with why
V43/V46/V52C, all signal-domain filters, were null.

**OPEN:** `gp-0x67ab`'s trigger (traced to a runtime RAM flag array `gp-0x617c`/`gp-0x6170`, producer
untraced); `gp-0x6bfa`/`gp-0x6bfe` and the RAM-resident LERP at `gp-0x64b8..gp-0x641c`.

---

## 6. Method traps recorded this session

1. **★ Two separate agents independently re-proposed `0xC6450` 1024→32 as a "new, never-flashed" lever.
   It is V46 verbatim — flashed, null.** A third nearly did the same with `0xC644A` (V43, flashed, null).
   ⇒ **Rule: grep `analysis-2020accord/build_v*_tva.py` for any calibration address before proposing it,
   and state its on-car result.** See `docs/BUILD-LINEAGE.md`, created for exactly this.
2. **`hw2 = disp|1` for `ld.hu`/`ld.w`.** The lead's first byte scan for `gp-0x6966` found only a store
   and missed the `ld.hu` at `0x3a632` that was visible in the disassembly. Scan both `disp` and `disp|1`.
3. **A displacement scan cannot find free calibration space.** 1723 of 2048 words in `tp+0x6000..0x6FFE`
   show zero displacement-readers purely because LERP tables are read via `movea base,tp,rX` + index.
   A real free-space answer must enumerate table bases and exclude their spans.
4. **Whole-file diffs against the stock dump are meaningless.** `build_*.full_image()` writes `0xFF`
   filler below `0x13000`; a naive diff reports **51,137 bogus bytes**. Restrict to `[0x13000,0x100000)`.
5. **Subagents' plain-text output is invisible to the lead.** Two agents completed all work and signalled
   idle having reported nothing. Brief agents to use SendMessage explicitly.
6. **An off-by-0x1000 recurred again**: `tp+0x6000` is `0xC5000` (the risky model-coeff block), not
   `0xC6000`. The cal block is `tp+0x7000..0x7FFF`.

---

## 7. Recommended next steps, in order

1. **openpilot-side 21 Hz notch.** Zero brick risk, now known untested rather than null, on a
   demonstrably open path (−2.70 dB rolloff there today). Keep the rail fraction matched between runs.
2. **Flash FOURFRAME2** when a firmware answer is wanted. One parking-lot drive measures `gp-0x6966`
   (settling the `0xC6AF0` direction) and captures all three terms of the `FUN_0003a382` loop so its
   transfer function can be identified rather than inferred. ⚠ It cannot settle 21 vs 79 Hz.
3. **The `0xC62EA` lockout edit** (320→64) — populates the empty C-low cell and breaks the
   speed/applied-torque collinearity. Cal-only.
4. **The `0xC646C` decoupling** (§4) — a correctness fix, not the vibration fix. Sequence it after.
5. Only then consider a `0xC6AF0` edit, and only in the direction the telemetry indicates.
