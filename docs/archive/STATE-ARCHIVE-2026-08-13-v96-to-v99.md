# STATE-ARCHIVE 2026-08-13 -- V96 to V99 superseded headlines

**A RECORD, NOT AN INSTRUCTION.** Every section below once lived in `docs/STATE.md`
and was superseded by a later flight (V99 on the car) or a later correction (the
`0xC6200` rail finding conditioning `0.2565`). Kept verbatim so no result is lost and a
claim can be traced to the form it was made in.

**Do not reason from this file.** The authorities are, in order: `docs/STATE.md`
(current state) -> `docs/BUILD-LINEAGE.md` (per-lever, per-build, on-car results) ->
the latest `docs/HANDOFF-*.md` -> `memory/`.

Split by `analysis-2020accord/archive/shrink_state_md_2026_08_13.py`.

---

## Contents

- (orig. STATE.md line 328) ⚠ SUPERSEDED 2026-08-12 (latest) — the block below described V96 as on the car and V97 as unflashed
- (orig. STATE.md line 408) ⊕ SUPERSEDED HEADLINE, 2026-08-12 — V94 REGRESSED THE CAR, AND IN DOING SO MEASURED THE LEVER'S SIGN FOR THE FIRST TIME
- (orig. STATE.md line 741) ⊕ SUPERSEDED HEADLINE, 2026-08-11 — ROUTES 78/79 SCORED; "THE DOSE DID NOTHING AND THE LEVER IS THE WRONG PHYSICS"
- (orig. STATE.md line 1021) ★★★★★ SUPERSEDED HEADLINE, 2026-08-09 — V88 FLEW, THE FORK CLOSED, AND THE HIGHWAY ARRIVED

---

<!-- original STATE.md line 328 -->
## ⚠ SUPERSEDED 2026-08-12 (latest) — the block below described V96 as on the car and V97 as unflashed
## ★★★★★ HEADLINE, 2026-08-12 LATE (SUPERSEDED) — V96 FLEW, THE CRUX IS THE RETURN TRAJECTORY, AND V97 MOVES A LOOP POLE

Narrative: **`docs/handoffs/2026-08/HANDOFF-2026-08-12-v97-the-loop-pole.md`.** Agent outputs: `analysis-2020accord/sessions/v97/`.

### A8. V97 — ONE BYTE. `0xC63AC` 102 → 150. THE ARC'S FIRST LOOP-POLE LEVER
```
39990-TVA,A160-V97-V96BASE-C63AC.102to150-0x13000-0x100000.rwd
  .rwd  78c674a899971a6a9763c2d7c89bf4c9169f35dfba3fbe4ce62d9bc445a17372
  image 7ac009044b46eeb2fd38d9ab6c7cb634e1be6ca44eb6f5083b9897c33829c2b3
  builder analysis-2020accord/builds/v80_v107/build_v97_tva.py   131/131 assertions   BASE = V96 (on the car)
```
**The whole delta is ONE BYTE** (102 = `0x0066`, 150 = `0x0096`; the high byte is `0x00` in both) plus
its own CRC trailer at `0xC6FFC`. `gp-0x374c += ((target − gp-0x374c) × A) >> 10`, `@0x38202`,
**1 reader / 0 writers established FIVE ways.** 🛑 **DC gain is 1.000000 at any A — it is a POLE, not
a GAIN.** That is why it escapes the sign problem that disqualified all six lane weights.

**THE DIRECTION IS MEASURED, NOT MODELLED — two independent instruments agreeing to <7°:**
- `Q = −d(gp-0x6b70)/d(T)`, hands-off engaged returns, episode-bootstrapped
  (`rlog-tools/studies/damping-q/v97_measure_Q.py`): **|Q| = 1.233 on BOTH routes**, arg Q −133.7°/−131.5°, coherence
  **0.974/0.978**. The criterion is *inversion iff |Q| < 1 and cos(arg Q) < −|Q|* ⇒ **|Q| > 1 excludes
  inversion at ANY phase**, so the ±28° CAN-join uncertainty is moot.
- The V96 cave's own sign bits: `arg(V) − arg(B′) = −178.1°` on both routes (orchestrator reproduced
  the separation independently at +179.8°/+178.6°). `arg(V)` sits just below −90° ⇒ **cos < 0 =
  ANTI-DAMPING**, the corpus `Re(Z) < 0` seen on a firmware-internal signal for the first time.
  Adding lead rotates it **toward** the damping axis. Better on both routes at every k.

🛑 **COST, and it lands on a symptom he calls FIXED:** +2 %…+13 % at 21 Hz on the total command
(Path-1 dilution — a MODEL, not a measurement). V62 bought grinding by taking 18–22 Hz down 8–42×;
V88's Lever B is on the car. Worst case 1.13 × 0.549 = 0.620, inside V88's CI. **Exchange rate is FLAT
at 0.33°/% — no sweet spot. A = 150 was the OPERATOR'S choice with the trade stated.** RULE 9.

🛑 **V97 IS NOT A RETURN-SPEED FIX.** Clause 2 has **no mechanism** — see §A9. Do not score it as one.

🛑🛑 **THE DIRECTION WAS INVERTED ONCE AND CAUGHT.** `scipy.signal.csd(x,y)` returns `arg(Y)−arg(X)`;
an agent labelled every cross-spectrum backwards and recommended **lowering** this cell. The tell was a
**replicated ~90°** disagreement with the independent `Q` measurement — a bug signature, not physics.
⇒ **The build exists because two instruments were run and allowed to disagree.** Add `csd`'s convention
to the trap list.

### A9. WHAT DIED THIS SESSION — seven levers, each before a build was cut
| lever | how it died |
|---|---|
| **pre-declared V97** (`gp-0x6b4c`/`gp-0x6b4e`) | `gp-0x6b4e` **provably ≡ 0**; §A5's "gates open ⇒ V64 excluded" priced gate WIDTH when the failure mode is the signal never being non-zero. The array is `gp-0x62c8[]`, not `gp-0x62f8[]`, and they are **two different arrays 0x18 apart**, not one split by mode |
| return-to-centre lane | 🛑 **it is a RACK END-STOP CUSHION**, not a centring lane — arms on `\|gp-0x6b98\|>4096` AND motor rate `<200` (a STALL detector), splits by sign into left/right stop enums, **no angle term anywhere**. Gate needs `\|gp-0x6bf0\| > 8878`. **~99.3 % dead in MANUAL too** ⇒ its absence cannot explain the engaged/manual difference |
| `0xC520C` governor ceiling | `gp-0x6ac0` scale reconstructed = **4.7121 ct per column °/s** ⇒ first knot **222.8 °/s**. Measured returns max **528 ct vs a 1050 knot — 0.00 %** reach it |
| `0xC6194` LKAS slew limiter | **REAL and calibrated** (3 ct/tick = 1.37 s full scale) but its input partition `0xC4118` is **all-1** ⇒ 100 % bypasses it. 🛑 The record's "output ×0" reason is WRONG — that is `0xC6196` |
| **AUTH / `0xC67C8`** | β(log AUTH) = **−0.013 [−0.344, +0.319]**, CI excludes the predicted +1 — **and** `gp-0x6b4c` is a second LKAS route that never sees AUTH (lane mode 0 at `0xC4124`, `REQ_B` written at runtime `@0x26496`). ⊕ `0xC6CD0`, our own 4× gain, sits on that lane. ⚠ **The table header is `0xC67BE`; `0xC67C8` is its `Y[0]`** |
| PID Ki `0xC6B12` | **INERT** — at 6–10 km/h the P term alone (16,000 at e=2000) exceeds the anti-windup bound (7,264) ⇒ the integrator is pinned |
| `0xC63A6` / `0xC63A4` | `0xC63A6` is **a cliff edge, not a lever** (V91/V92 ×1.5 null + V94 ×0.25 catastrophe fit closed-loop invariance, not a dose-response). `0xC63A4`'s lane carries **~1.1 ct of a 342 ct signal** |

### A10. TWO BLOCKERS CLOSED, AND ONE `STATE.md` CLAIM RETRACTED
🛑 **§A6b's "the transfer cannot be read from the image" is FALSE.** The LERP is **100 % flash-derived**:
`FUN_000382d8` @`0x382d8` (sole writer) interpolates a 2-D flash table on speed selected by the mode
byte, `FUN_000389ec` rescales into `gp-0x64b8[]`/`gp-0x641c[]`, which is what `FUN_00038148` reads.
⇒ **`f′ ≥ 0` is ENFORCED IN CODE** at three ungated sites (`0x388c4` eight `max(Y[i],Y[i-1])` rungs;
the float-path monotone guard; `0x38de2`/`0x38e48`) ⇒ **holds for any cal, any mode, any build.**
Flash data agrees **14/14 records strictly increasing** (orchestrator-verified).
⊕ **"The 8 float coefficients of `FUN_0003b8f6`" never existed** — 3 floats (two hard ZERO ⇒ the 3-tap
FIR is an **identity**, unity gain, 0.000°) + 6 halfword Q-format cals. The handover also omitted
`0xC4048`, the only nonzero tap.
⊕ **`0xC64DE` identified**: a **BYTE** 17→27, not a halfword 25617→25627 — the half-period of a
relaxation oscillator (`gp-0x6b2c` sign-flips every N ticks, counter re-arms at `(N>>1)+1`).
⚠ 8 of its 16 read sites are in a region Ghidra never analysed ⇒ "dead" is a **tool zero**.

### A11. 🛑 FOUR TOOL-ZEROS IN ONE SESSION — ONE IS A NEW CLASS
1. `get_xrefs_to` tp-relative blind spot (known). 2. `search_instructions` undercounting (known).
3. `movea` + **register-indirect** — `operand_pattern="-0x6350\[gp\]"` returned **0 / 183,570 /
   `truncated:false`** on an array with nine real accesses.
4. ⭐ **NEW — `ep`-relative short-format aliasing.** An array is based once via `movea <off>,gp,ep`,
   then every access is `sld`/`sst` off `ep` with **no offset in the operand text**. `-0x62f8` →
   **15 hits, 14 of them base setups, ZERO actual loads/stores.** 🛑 **Worse than a zero: a healthy
   non-zero count that misses 100 % of accesses.** Recipe in `sessions/v97/fw_return.md` §8h.
   ⊕ Also: a *filtered* zero is not a fact — `operand_pattern="0x0[ep]"` returns 0 because Ghidra
   renders operands as `r6, 0x0, ep` (commas, no brackets).
🛑 **`0xC63AC`'s census was re-tested against trap 4 and is CLEAN** — 98 `movea imm,tp,ep` sites
image-wide, **0** within the 254-byte `sld` reach; a gp-based `ep` cannot reach the cal block at all.

---


<!-- original STATE.md line 408 -->
## ⊕ SUPERSEDED HEADLINE, 2026-08-12 — V94 REGRESSED THE CAR, AND IN DOING SO MEASURED THE LEVER'S SIGN FOR THE FIRST TIME

**Superseded by §A8–A11.** 🛑 **V94 is NO LONGER ON THE CAR** — V96 flew as routes `7e`/`7f`.

Narrative: **`docs/handoffs/2026-08/HANDOFF-2026-08-12-v94-aborted-and-the-override-regime.md`.**

### A1. 🛑🛑 V94 IS A DAMPER REMOVAL, NOT AN INERTIA REDUCTION [EVIDENCE]

V94 cut `0xCBE74` — mode 24 ×0.50, modes 26/27 ×0.25, fallbacks ×0.75 — **a 6× cut against V92** on
the premise that `gp-0x6b26 = −K·α` is *apparent inertia, nothing is dissipated*, so *"lowering is
strictly safe on both binding bounds"* (`builds/v80_v107/build_v94_tva.py:106`).

**Measured on-car after the fact, on TWO independent drives, ω-partialled against a shuffled control:
the DELIVERED lane sits at `+137°` / `+139°` versus WHEEL rate at 6–9 Hz ⇒ |cos| = 0.73 ⇒
`+518` / `+565` counts of POSITIVE `Re(Z)`.** It is a **real 6–9 Hz damper**, and V94 removed 6/6ths
of it. The car got much worse in exactly the band the damper covers.

| symptom instrument on route `7d` | result |
|---|---|
| motor acceleration > 9 Hz | **3–7× up** vs corpus |
| column-torque ↔ wheel-rate coherence, 18–31 Hz | **highest of any drive in the corpus** |
| faults / DTCs / sentinels | **none** |

⊕ **The code byte is EXONERATED.** `0x55E10` `sar 3`→`sar 1` is the CAN-427 packer shift;
instruction-level walk shows `r6` is consumed only by the `jarl` two instructions later, and
openpilot's `steeringTorqueEps` dead-ends in `carstate.py`. It changes what we *see*, not what the car
*does*. **The regression is the CALIBRATION.**

⊕ 🛑 **The desk correction was ALSO wrong.** *"+75°, 26 % dissipative, structurally cannot damp
6–9 Hz"* (`analysis-2020accord/studies/dose/v94_damping_fraction.py`, now header-marked SUPERSEDED) was the
**producer's filter phase vs MOTOR rate**; the measurement above is the **delivered lane vs WHEEL
rate, with the plant in between**. Two successive phase stories about one lane, both decision-bearing,
both wrong, four days apart. ⇒ the rule is **measure the delivered lane**, not *do the arithmetic*.

⇒ `memory/accord/builds/accord-v94-flew-and-the-lane-is-a-damper.md` ·
`memory/accord/signals/accord-gp6b26-is-a-real-6to9hz-damper.md` ·
`memory/feedback/builds/feedback-reducing-a-gain-is-not-a-safety-class.md` (the five-failure process RCA, incl. a
**133/133-green assertion suite that encoded the wrong premise as a PASS condition**).

### A2. 🛑🛑 THE SYMPTOM REGIME IS **ENGAGED + HANDS-ON + OVERRIDE** — AND EVERY `Re(Z)` NUMBER EVER PRODUCED EXCLUDED IT

Operator, 2026-08-12: ***"Steering override is how I get the steering into such a scenario where
grinding and micro ratcheting can be observed."***

The kit's hands-off mask is `steeringPressed` = `|STEER_TORQUE_SENSOR| > 1200` — a threshold on the
**numerator of `Re(Z)`**, and **override is `steeringPressed == True` by definition**. The instrument
was pointed away from the symptom, and the exposure followed: **7121.6 s engaged hands-off against
994.9 s engaged hands-on.**

**Scored in the right regime, on band power, with grip matched out on BOTH arms** (override vs
manual-hands-on), 6–9 Hz column-torque envelope:

```
OVR / MAN-ON  =  1.43  1.65  1.74  1.93  2.22  2.25  2.35  2.38  2.55  2.90
                 10 of 10 routes, 9 builds, every one above 1.4   median ~2.2x
```

🛑 **The operator's report — *"literally every bad symptom is LKAS engaged only"* — is CONFIRMED by the
amplitude instrument in his own regime**, and agrees with the standing 2.8× engagement contrast.
An orchestrator claim that *"~80 % of what you feel isn't gated on LKAS"* was **retracted**; roughly
**55 %** of the 6–9 Hz energy he feels is engagement-attributable. **An LKAS-gated lever is fully back
on the table** — the class V62 and V88 came from.

⊕ **`Re(Z)` and band power never disagreed.** `Re(Z)` is **LATENT** (energy that *would* grow if
excited; hands-off there is almost no excitation — manual 6–9 Hz coherence 0.040 against a 1/n ≈ 0.014
bias floor). **Band power is the FELT quantity.** 1.24× latent and 2.2× felt are different
measurements and both are correct.

🛑 **Override does not support the kit's 5.12 s band estimator.** 5013 contiguous override runs make up
the 994.9 s: median run **0.02 s**, p90 **0.55 s**, and **only SEVEN runs corpus-wide reach 5.12 s**.
Use point-process / event-triggered methods or 1.28 s windows, **and say which.**

⇒ `memory/reference/measurement/reference-accord-steeringpressed-mask-excludes-the-symptom-regime.md`

### A3. ☠ TWO NAMED MECHANISMS DIED IN THAT REGIME — AND ONE NEW ONE APPEARED

**Mechanism A — "the LKAS authority collapse curve is the 6–9 Hz exciter": DEAD, five ways**, with
**perfect exposure** (median override torque **2235** against a **2240** knot; 33–70 % of override time
above 2560 with authority at exactly zero):
1. knot crossing rate **0.47–1.69 Hz**;
2. reconstructed authority spectrum **88.4–94.9 % in 0.5–3 Hz**, peak **0.79 Hz**, every route;
3. sweeping the unit scale 0.6×–2.0× **never exceeds 1.22 Hz**;
4. 🛑 the chatter↔energy correlation **INVERTS against its own negative control** — OVR
   **−0.194 / −0.255** vs MAN-ON **+0.400 / +0.495** ⇒ it tracks **how hard the driver is working**;
5. **not an exciter either** — 6–9 Hz energy *falls* after a collapse edge, below the shuffled baseline.

**Mechanism B — "a sign-guard relay chatters when the driver opposes": DEAD.** Request-bit duty
**1.0000**, drops/s **0.000**, every route ⇒ the gate never opens. And **openpilot does not back off
when overridden — it winds UP 6.7–15×**, so the premise is false. Direction reversals **0.23–2.66 Hz**
and *lower* during override.

★★★★ **THE NEW ONE — a real surge, at ~0.5–1 Hz.** The EPS holds LKAS authority at **exactly zero for
17.5–40.5 % of override time**, cycling **~0.5–1.7 Hz**, *while* openpilot winds up **6.7–15×**. Ease
back below the knot and authority returns with a command an order of magnitude larger.
🛑 **It is ~0.5–1 Hz, NOT 6–9 — it is not the grinding and not the micro-ratchet.** It would be felt as
a **slow lurch or a "catch"**. **The operator has NOT yet said whether he feels it. Until he does it is
a measured behaviour with no scored symptom attached** and must not be reported as a cause of anything
he has complained about.

⇒ `memory/accord/mechanism/accord-override-surge-and-two-dead-mechanisms.md`

### A4. INSTRUMENT RESULTS OF RECORD FROM THIS SESSION

- **`Re(Z)` anchored on-car for the FIRST time, parameter-free**: `mean(T·ω)` pooled **+3859**,
  **P(>0) = 0.9238**, n = 20,159, 8 routes / 8 builds. It independently ranks **V80 worst** at
  12–16 / 18–22 Hz (−8883 / −3581) — the build the operator called *"worst grinding ever."* Detection
  floor **~60 ct at ≥12 episodes; use 150.** 🛑 **Never quote `Re(Z)` below 6 Hz from a
  `steeringPressed` mask — 2–4 Hz reverses sign.** ⇒ `memory/reference/measurement/reference-accord-rez-anchored-on-car-and-its-floor.md`
- **CAN 427 is RECTIFIED** ⇒ aliasing runs on `2f` and the fold law is `|2f − 50·round(2f/50)|`,
  **not** `f mod 25`. 26/29/31 Hz fold to **2/8/12 Hz**. The band a 427 magnitude probe exposes is
  **2–12 Hz, not 19–24.** ⇒ `memory/reference/can/reference-accord-427-is-rectified-and-folds-26to31-into-2to12hz.md`
- **`gp-0x6bbe` is RATE-derived, NOT the base-assist output** — contradicting the previous headline.
  Dead as a lever: 9–15 % of `Re(Z)`, rate part 4–9 % of a 73–80 ct DC pedestal.
  ⇒ `memory/reference/firmware/reference-accord-gp6bbe-is-rate-derived-not-base-assist.md`
- **Four more 6–9 Hz stories killed by their own controls**, including **Lever B `0xC6446` CLEARED**
  (⇒ V88's grinding fix need not be traded away) and **0 of 41 varying cells** separating 6–9 Hz.
  ⇒ `memory/reference/measurement/reference-accord-controls-killed-four-6to9hz-stories.md`
- 🛑 **RETRACTED: task 5 = 100 Hz.** The derivation rested on an address coincidence.
  **Task 5's rate is OPEN.** Task 1 (`FUN_0002214a`) = 1 kHz still survives on two independent methods.
  ⇒ `memory/accord/firmware/accord-task5-is-100hz-damper-cannot-damp-21hz.md` now carries a **DISPUTED — DO NOT SIZE A
  BUILD ON THIS FILE** banner.
- **`FUN_0002a93a` is DEAD CODE** (zero callers) and two engagement-gate candidates were struck.
  ⇒ `memory/reference/firmware/reference-accord-two-engagement-gate-candidates-struck.md`

### A5. WHAT IS BUILT — AND THE REVERT CANDIDATE

| build | status | image / rwd |
|---|---|---|
| **V97** | ☠ **SUPERSEDED — FLEW as route `0x80`, then superseded by V98.** Its `0xC63AC` = 150 is carried on V98 and is now believed **WRONG-DIRECTION** (it broke Honda's exact 51/512 pole match) | image `7ac009044b46eeb2…` rwd `78c674a899971a6a…` |
| **V96** | ☠ **SUPERSEDED — no longer on the car.** Flew as routes `7e`/`7f`, 2026-08-12, both fault-free | image `876cf2be5800f0f8…` rwd `7e9a65f11cab4ffc…` |
| **V94** | ☠ flown as `7d` and **ABORTED**; **superseded — no longer on the car** | image `cd971c05d483fe9c…` rwd `3feccc09d8cbdd05…` |
| **V93** | built, verified, **never flashed**; carries V94's cal without the packer rescale | image `779180f8aaf88f29…` rwd `9c93dca63e9e404e…` |
| **V92** | flown as route `79`; its calibration is carried byte-for-byte by V96 ⇒ **no revert is pending** | rwd SHA256 `388a1974d5702e17…` |
| ~~V95~~ | 🛑🛑 **VACATED — A BURNED NUMBER. NEVER REUSE IT.** | see the DEAD hashes below |

🛑 **V96's SEPARATION FROM V92 IS NOW EVIDENCE, NOT BELIEF.** §A6 logged at cut time that the separator
was V92's measured b6 duty rather than an impossibility. **The flight discharges it:** V92's byte7 b6
is the dwell-snap rung, measured **0.0000 engaged AND manual over 87,317 frames** (3 runs, longest
855 s); V96's byte7 b6 is a **hard-wired constant 1**, and a **164,096-frame unbroken rail** is a
reading V92's rung has never produced one frame of.

🛑 **V96's INSTRUMENT FAILED AND MUST BE RE-SIZED BEFORE ANY RE-FLY.** `gp-0x374c`'s magnitude code M
is **pinned at 0** on 99.90 % / 99.97 % of frames and **100 %** of route 7f's engaged elicitation time
⇒ `|gp-0x374c>>4| < 2048` throughout, against a field sized for ~68,600 — a **34× over-range**.
**S1 AND S2 ARE BOTH VOID; `f′` is NOT RESOLVED by this flight** (though it was later closed
analytically — §A10). Next regressor LSB should be **128–256**, not 2048.

**Revert candidate, full name:**
`39990-TVA,A160-V92-V90BASE-CBE74.M26.M27.X1.5-CAVE.6BBE.6B62.6BDA.6A82-427.6BBE.SAR4-0x13000-0x100000.rwd`
🛑 **Not flashed. Flashing is gated on the operator naming the file and the bus.** V92 flew as route
`79` in the earlier lineage with identity **proven single-frame**; it is the last configuration the
operator drove and did not abort.

### A6. V96 — THE BUILD THAT WAS CUT (and why V95 is a burned number)

**Class: an INSTRUMENT build, not a fix.** Base **V92**, with V94's cal cut reverted **by construction**.
```
image  876cf2be5800f0f8e315f8b1d63dd103ec11ee7293577808ecff5f19a849cda3
.rwd   7e9a65f11cab4ffc6286f0365ce5196c11dc461468b9ec85022775e35ebdf093
39990-TVA,A160-V96-V92BASE-REVERT.CBE74-PROBE.6B70.374C.674E-427.6B70.SAR6-0x13000-0x100000.rwd
builder: analysis-2020accord/builds/v80_v107/build_v96_tva.py   166/166 assertions, reproduces bit-for-bit
```
**107 bytes differ from V92 in 7 runs. ZERO are calibration** — no diff anywhere in `[0xC6000,0xC7000)`
or `[0xD6000,0xD8000)`; all four authority-curve records byte-identical to stock. **112-byte cave
payload inside V92's proven 116-byte footprint — no growth**, same hook, same `jarl`, 4 bytes back to
virgin.

**What it measures, and why this and nothing else.** The blocker on every remaining lever is that
`gp-0x6b70` is a **PID reference that gets subtracted**, so no `FUN_00038148` weight can be moved
without knowing the LERP's local slope (§A6b). V96 puts the **pair** on the wire:
- **CAN 427** ← `gp-0x6b70`, `sar 6`, magnitude + explicit sign bit. **LSB 12.8 counts**, no-clip
  (`8192×5>>6 = 640 ≤ 1023`), 6–9 Hz floor ≈ 3.6 ct.
- **`0x14A` byte4/byte7** ← `gp-0x374c >> 4` — **the firmware's own shift** (`@0x38236`, the
  instruction that forms this very term of `iVar6`) — **saturating at 12288, LSB 2048**, deliberately
  below the 68,614 structural bound because **no build has ever put either cell on the wire**. The
  saturation duty and the 8-code histogram are **first-class reported outputs** so the next build sizes
  off data instead of guessing. ⊕ `b3` = `gp-0x674e < 28`, settling RULE 7 for the authority curve.
- **Identity:** `byte7 b6 ≡ 1` ⇒ **any single frame with `0x14A` byte7[7:6] ≠ 0 proves V96.** V94, the
  build on the car, carries the 74-byte V90 cave and *cannot* write byte 7. ⚠ Separation from **V92**
  is **BELIEF, not EVIDENCE** — V92 also writes byte 7, and the separator is its b6 measuring duty
  0.0000 over 75,227 engaged frames, which is a measured duty, not an impossibility.

**Pre-registered scoring — TWO SLOPES, never merged:**
- **S1** — lag-0/lag-1 slope of `gp-0x6b70` on `gp-0x374c>>4` ⇒ the **OPEN-LOOP `f'`**. **Its SIGN
  decides whether any Path-2 weight lever helps or inverts.** Valid because
  `d(gp-0x6b70)/d(gp-0x374c>>4) = −f'` **independently of `sign(iVar6)`, `gp-0x6bfe` and `gp-0x6bfa`**
  — the two sign factors square to +1 and cancel.
- **S2** — coherence-weighted longer-window slope ⇒ the **CLOSED-LOOP** transfer, folding in `L`.
- ⚠ Errors-in-variables attenuates both magnitudes and **preserves both signs** ⇒ magnitudes are
  **lower bounds**. 🛑 **If S1's CI spans zero the answer is "`f'` is NOT RESOLVED by this flight" —
  NOT "`f'` is zero" — and the weight class stays blocked.**
- Secondary: hands-on 6–9 Hz band power in **override**, event-triggered **1.28 s onset windows**,
  episode bootstrap, POS-1/2/3 · NEG-1/2 · shuffled-pairs, 2× placebo floor.

🛑 **FREEZE EXCLUSION (heuristic, and labelled as one):** `FUN_00038148` sits behind a `gp-0x67fa`
state gate; when it shuts, **both** members of the pair freeze and would enter the regression as
spurious zero-slope samples. The exact gate is **not readable by a cave** — its boolean is **never
stored** (`r28` written once `@0x221D6`, tested `@0x22672`, no store in `[0x2214A,0x22700)` sources it),
recomputing needs a **Format IX `shl reg,reg,reg`** (the hand-encoding class that bricked V24/V27/V48B),
and the affordable `4 ≤ s ≤ 11` approximation is a **superset that would silently read "live" while the
pair is held — worse than no bit, because it would be trusted.** ⇒ the wire-side fallback: drop runs of
≥5 consecutive frames where the 427 code **and** the byte4 field are both bit-exactly unchanged, and
**report the dropped fraction.**

### 🛑🛑 V95 IS A VACATED NUMBER — NEVER REUSE IT
Three artefacts wore it inside two hours as the spec moved. **Retiring the number is cheaper than
disambiguating it forever.** DEAD hashes, written out so a grep finds them:
```
DEAD  lane build (6B4C/6B4E)   image ad8643c1f37ac128c57606c60ad6225420884f3fa250ffd978f9efa6a5fb7faf
DEAD  lane build (6B4C/6B4E)   .rwd  3a791446c268b2b0660e4035a82c51f93572b662faa6225167f16e331277c9d6
DEAD  pair build numbered V95  image 876cf2be…  .rwd 7e9a65f1…   <- SAME BYTES, now correctly V96
```
`analysis-2020accord/build_v95_tva.py` was **deleted** — it would rebuild a vacated number.
⊕ **The lane design is not lost.** `gp-0x6b4c`/`gp-0x6b4e` are the **disjoint partition sums of the
same 11-slot request array** `gp-0x62f8[]` (split by the mode bytes at `0xC4124`), `±10240` each — 5×
and 10× the other two lanes — and `gp-0x6b4c` is **also a direct unity-weight aggregator summand**
(`0x3AA3E`) so it reaches the motor by both paths. Both gates are **structurally always open**, so the
V64-class null is excluded *by arithmetic*. **That is V97, cut fresh from whatever base is current.**

### A6b. ⭐ TWO NEW LEADS THE CELL LEDGER TURNED UP — both sit in the override regime

Both came out of reading all **85** build images against stock (`analysis-2020accord/studies/ledger/ledger_v94_cells.py`,
`diff` · `matrix` · `grid` · `mask`; `LEDGER_TARGET=V92` to retarget). **Net V94-vs-stock delta: 245
bytes in 114 runs, zero unattributed**, reconciled two ways (215 + 30 = 245, 107 + 7 = 114).

**LEAD 1 — `0xC63A6`. ☠ TRACED AND STRUCK THE SAME DAY. NO-GO — but for a reason that matters more
than the cell does.**
`0xC63A6` is `w[3]` in `FUN_00038148`, **stock 1024 (Q10 = ×1.000)**, on the **`gp-0x6b26`** lane, and
**VIRGIN across all 85 images**. `0xC63A2`/`A4`/`A8`/`AA` are virgin too; only `0xC63A0` has history
(2048 at V72–V75, V76g, V81 — **inert**, frozen at 1024 for 13 builds since V83a). It looked like a
second, independent multiplier on the one signal whose direction is now measured, with `0xCBE74`
exhausted at ×1.5 (≈94 % of its range before int32 wraparound at 1.6005×).

- **Q1 CLOSED [EVIDENCE, three methods].** It weights **only** `gp-0x6b26`, through exactly **one**
  instruction — `ld.hu 0x73a6,tp,r15 @ 0x381ca` in `FUN_00038148`. **Zero writers.** Path 1
  (`FUN_0003aa2c`) never reads it. ⚠ `get_xrefs_to` returned *"No references found"* — **the Ghidra
  tp-relative xref blind spot, not a real zero**; caught and overridden by `search_instructions` plus
  a raw Python LE scan (disp16, LE32 absolute, movea lower-half). Two false positives
  (`be 0x000473a6`, a `jarl` displacement coincidence at `0x652aa`) were each disassembled and excluded.
- 🛑 **Q2 KILLED IT, and NOT on magnitude.** Path 2 is **not** negligible. The problem is that
  **`gp-0x6b70` is not an aggregator addend — it is a PID REFERENCE** (`error = measured torque −
  reference`), so the **sign** of Path 2's contribution depends on the sign of `iVar6` and on the
  **local slope of a RAM-resident LERP** at the operating point. **Neither is known.**

```
sum6 ──(*polarity*2639)>>10, *16──> target                  # 0xC6468 = 2639
gp-0x374c += ((target - gp-0x374c) * 102) >> 10             # 0xC63AC = 102, IIR pole
iVar6 = gp-0x6bfe + gated(gp-0x6bfa, ±20000) - (gp-0x374c >> 4)
gp-0x6b70 = sign(iVar6) * RAM_LERP(|iVar6| * 1024 >> 10)    # <-- THE UNKNOWN SLOPE
            clamped ±8192                                    # 0xC6200 = 8192
        --> gp-0x6ad6 --> PID reference --> aggregator
```
Path 2's IIR alone is **|H| = 0.94/0.91/0.88 and −18.7°/−23.6°/−26.8°** at 6/7.79/9 Hz; stacked on the
PID's own −11° to −27° at that band, **Path 2 runs ≈ −30° to −54° of lag against Path 1's 0°, unity,
unconditional.**

🛑 **A lever whose SIGN is unresolved is not a lever. That is exactly how V94 reached the car.**
⚠ **One contradiction is still open and is being adjudicated:** the claimed inversion boundary at
`0xC63A0` 1024→2048 (0.59/0.56 "damping" → 1.18/1.12 "INVERTED") should have produced a large
qualitative change on-car, and **`0xC63A0` = 2048 flew four times (V72, V73, V76g, V81) and measured
INERT.** Either the model is wrong, or "inert" was measured hands-off in the wrong regime, or Path 2 is
small at the flown operating point (which would contradict Q2). **Unreconciled.**

**LEAD 2 — `0xC64B8`. ☠ VERIFIED AND DEAD. But it handed back the best lever in the kit.**

The claim was structurally true and behaviourally empty. `0xC64B8` really does gate a branch that
**hard-kills the LKAS authority weight to 0**, the comparison really is `cal < torque_byte`, and with
V37's `0xFF` against a byte that saturates at 255 the kill path is **unreachable**. ⊕ The compared
signal really **is a torque, not a counter** — the "fail-counter" label describes only one of three
live readers; `gp-0x682f = min(|gp-0x4f60| >> 5, 254)`, so the gate would fire at **|raw| ≥ 3616**.

🛑 **But at mode 7 BOTH ARMS DELIVER 0 everywhere the branch could fire** — all four curve records
clamp to `Y[last] = 0` above `X[last]` = 80 or 112, below the gate's 113. **Stock and V37 are
bit-identical on this car. V37 removed nothing.** ⇒ **do not re-propose it.**
⊕ Blast radius closed: **6 readers, 0 writers**, two methods, set difference **empty** — 3 live (all
`FUN_00028ea6`), 3 in dead functions. 🛑 **New parity trap:** `0x4549E`/`0x4556E` have hw2 = `0x74B9`
but opcode field `0x3D` (disp bit0 = 1) ⇒ they address **`0xC64B9`, the neighbour**. A scan keying on
hw2 alone **over-reports by two.**

### ⭐⭐ LEAD 3 — THE AUTHORITY COLLAPSE CURVE. VIRGIN ON ALL 90 IMAGES, AND HE DRIVES ON ITS KNEE

Mode-7 records: `0xE547C` / `0xE5404` (primary, X = 70/72/78/80 → Y = 254/234/12/**0**) and
`0xE52FC` / `0xE5284` (blend, X = 32/42/80/112 → Y = 255/255/255/**0**).
**Authority goes 254 → 0 between raw 2240 and 2560 — a 320-count window, nearly a step.**
🛑🛑 **All four are VIRGIN across all 90 `_v*` images. No build has ever touched them.**

| quantity | raw | torque byte |
|---|---|---|
| curve first knot `X[0]` | 2240 | 70 |
| **measured median override torque** | **2235** | **69** |
| fully collapsed `X[3]` | 2560 | 80 |
| `0xC64B8` gate (dead) | 3616 | 113 |

**One count below the first knot.** A few counts either side is the difference between full authority
and none — and it is the mechanism behind the measured **~0.5–1 Hz surge** (§A3).

🛑 **IT IS NOT A 6–9 Hz LEVER**, and the curve was already refuted as one **five ways** this session.
**Softening it targets the SURGE, not the grinding or the micro-ratchet.** Do not conflate them, and
do not propose it until the operator says whether he feels the surge.

🛑🛑 **THE SAFETY DIRECTION IS NOT SYMMETRIC.** Honda collapses authority when the driver pushes hard —
that is **driver-override behaviour**. Widening the window makes the car **fight the driver harder and
for longer**. ⇒ **the only defensible shape change is MONOTONE-NON-INCREASING** — authority never
higher than stock at any torque; start the decay *earlier* and make it gradual, reaching 0 at the same
place. **Anything that raises `Y` at any `X` is a different and far more serious proposal.** GATE 2 is
entirely untouched, and the curve gates the whole LKAS delivery path.

⚠ **One gap, and V96 closes it with one rung** (`b3` = `gp-0x674e < 28`). `gp-0x674e` = 7 comes from code + the config table +
V73's on-car variant row — **never a direct on-car read of the byte.** It matters: **modes 28–39 have
`Y[last] = 51`, not 0**, and there the `0xC64B8` branch would *not* be redundant.
⊕ Table trap: the ASCII key sits at block `+0x24`, so it renders as the **next** row's label — row 11
is `18 19 1a 1b` (24/25/26/27 ✓ TVCA4) while the string in the same window reads "TVCA6". **A naive
`+0x12` dump is off by one row.**

⇒ `memory/accord/calibration/accord-authority-curve-is-virgin-and-the-override-sits-on-its-knee.md`

⊕ Also flagged, not implicated: **`0xC64DE` = 25627 since V22 — non-stock for 85 builds, its label
disputed since 2026-07-18, and never once isolated.** The longest-carried unmeasured cell in the image.

### A7. 🛑 STILL OPEN

1. **Task 5's true rate** — the 100 Hz claim is retracted; nothing replaces it.
2. **`gp-0x6733` identity** — it drives `gp-0x67e2`, which picks the mode-table column A/B.
   Both **26 AND 27** are engaged columns.
3. **The `gp-0x67fa == 4` record inconsistency.**
4. **`FUN_0003897a` / `gp-0x6350` / the LERP `X[0]`.**
5. **The ~0.5–1 Hz surge** — measured, unattributed to any complaint. **Question outstanding to the
   operator** (§A3).
6. **The left/right ramp-rate asymmetry** — `0xC63F8` = 33 vs `0xC63FC` = 328, a **10×** difference.
   **Question outstanding to the operator: does the car feel different turning left versus right?**

---


<!-- original STATE.md line 741 -->
## ⊕ SUPERSEDED HEADLINE, 2026-08-11 — ROUTES 78/79 SCORED; "THE DOSE DID NOTHING AND THE LEVER IS THE WRONG PHYSICS"

**Superseded by §A1.** Narrative: `docs/handoffs/2026-08/HANDOFF-2026-08-11-routes-78-79-and-the-inertia-reversal.md`.
The V90-flight-session block that sat here went verbatim to
`docs/archive/STATE-ARCHIVE-2026-08-11-v90-flight-session.md`.

**What it got RIGHT and is still live:**
- Both drives **fault-free**. Route 78 = 927 s / 67.0 % engaged / **160 s ≥ 80 km/h**; route 79 =
  875 s / 86.2 % engaged.
- **The ×1.5 dose measured 0.99 [0.91, 1.26]** engaged (manual control 1.009), against a pre-registered
  1.50 — **and the explanation is now known**: `gp-0x6b26 = K·α` where α is *what K damps*, so in a
  stable closed loop **the product is invariant to K. The instrument was structurally incapable of
  measuring its own dose.** ⇒ measure the **input** (`gp-0x6c2c`) or a symptom, never the product.
- **`Re(Z) < 0` replicated on three drives** — 6–9 Hz −3375 / −3176 / −3073, sign flip to damped at
  ~24–26 Hz on all three; strongest in the **micro 1–13 °/s** regime (−3480, coh² 0.804).
- **Return-centre + detent are DEAD ENGAGED** — `gp-0x6b62 ≠ 0` and the `gp-0x6bda` gate both **0.0000
  over 75,227 engaged frames**, with an **855 s sustained (0,0) run**. **Do not propose a detent lever.**
- **Routes 77/78/79 are the same functional car** ⇒ the kit's largest **placebo floor**: 6–9 Hz
  **1.37×**, 18–22 **1.31×**, 26–31 **1.99×**, 32–38 control **1.54×**. **No claim below 2× is
  supportable in either direction.**

**What it got WRONG:**
- 🛑 *"`gp-0x6b26 = −K·α` ADDS APPARENT INERTIA and dissipates nothing ⇒ LOWER it"* — **refuted by the
  V94 flight and by direct measurement of the delivered lane.** See §A1.
- 🛑 *"`gp-0x6bbe` = the base-assist output"* — **refuted**; it is rate-derived. See §A4.

---


<!-- original STATE.md line 1021 -->
## ★★★★★ SUPERSEDED HEADLINE, 2026-08-09 — V88 FLEW, THE FORK CLOSED, AND THE HIGHWAY ARRIVED
**Superseded as the headline by the 2026-08-11 block at the top; the findings below are NOT
superseded.** V88's grinding fix is still on the car (Lever B, carried through V89/V90/V91/V92).

### 0. ✅ V88 FLEW — route `73` (`75604b0a432fdc89_00000073--9380c74d52`), 11 segments, cache `_scratch/cache/r73/`
61,161 frames / 613.4 s, **72.7 % engaged = 7.41 min**, **fault-free**: `STEER_STATUS` {0: 61,147, 3: 15},
DTC-active duty **0.000000**, 0 sentinels, no EPS event in 1,786 `onroadEvents`.
**Operator, in his words: the audible GRINDING IS FIXED · hints of grind #2 but he could not elicit it ·
MICRO-RATCHETING and RATCHETING (stuttering) are now the main remaining issues.**

★★ **THE ≥50 km/h DROUGHT IS OVER — 119.6 s engaged ≥50 km/h, 80.2 s ≥80, v_max 116.6 km/h**, against
**0.0 s on each of the four prior routes.** Highway = segments 4–5, both 100 % engaged.

**IDENTITY, parameter-free, triple-measured:** `b6 == (427 wire ≥ 160)` = **0.9654** vs the V87 control
**0.4022**, with **chance = 0.6028** from the marginals ⇒ V87 sits essentially *at* chance. Duty match
0.27330 vs 0.27334; edge-conditioned agreement 0.9901; lag sweep peaks at lag 0.

### 1. ★★★★★ H1 CONFIRMED — THE FIX DID NOT COST STEERING AUTHORITY
Speed-matched 2–4 m/s, engaged, unclipped, episode-bootstrapped (orchestrator's independent crude
estimator in brackets):

| band | V88/V87 | verdict |
|---|---|---|
| **0.5–3 Hz — the peak effective LKAS command** | **1.192 [0.780, 1.812]** [1.121] | **NULL — untouched** |
| 3–6 Hz | 1.165 [0.959, 1.375] | null |
| 6–9 Hz | 0.859 [0.503, 1.171] [0.720] | null |
| 9–12 Hz | 0.604 [0.465, 0.943] | FALL |
| **15–22 Hz** | **0.549 [0.407, 0.844]** [0.625] | **FALL** |

**Aliasing excluded on two independent 100 Hz channels** (427's Nyquist is 24.9 Hz): `tq` 15–22 Hz
**0.33×**, `rate_c` **0.31×**, while **28–35 Hz is FLAT (1.13× / 0.94×)**. Column `tq` 15–22 Hz rms
**259.4 → 84.6**. ⇒ **Lever B halved the delivered command's HF content at zero low-frequency cost.**

🛑 **THE ORCHESTRATOR'S PRE-FLIGHT HYPOTHESIS WAS REFUTED.** He predicted a 15–22 Hz **RISE**, reasoning
that r24 is a differentiator whose gain Lever B doubles. **r24 is rate FEEDBACK inside the loop and
`gp-0x6b98` is the loop's OUTPUT, not its input** ⇒ more derivative feedback = more damping = **less** HF
everywhere. V87's engaged spectrum rising with frequency (29 / 29 / 52 ct rms) against a **flat** manual
arm (~9) is the signature of an **under-damped closed loop at stock derivative gain.**

### 2. ★★★★★ H2 — THE FORK CLOSED, AGAINST THE FIRMWARE
V88's `b7` sign bit reconstructed the **SIGNED** delivered command and V87's rectification screen was
**dropped entirely** — 75 unclipped engaged windows vs V87's 14 screened. Controls first: the sign bit
flips at median `|cmd|` **36.8 ct = the 22.9th percentile** (a noise bit sits at the 50th); `b5`/`b6`
agree with the 427 magnitude in 99.56 % / 96.02 %; corr(0.2–3 Hz signed cmd, column) = **−0.671** where
the *rectified* magnitude gives **+0.030**.

| channel | 6–9 Hz prominence | above the p95 floor (10.64) |
|---|---|---|
| column torque `0x18F` | **11.17 [7.85, 16.30]** | **52.0 %** |
| **SIGNED `gp-0x6b98`** | **5.46 [5.12, 5.94]** | **13.3 %** |
| rectified `\|cmd\|` (V87's view) | 5.62 [5.10, 6.80] | 12.0 % |
| openpilot `0x0E4` | 4.43 [3.87, 4.93] | 1.3 % |

**Signed ≈ rectified ⇒ rectification was NEVER hiding a line; V87's null was CORRECT** and is now
established rather than assumed. ⇒ **THE RATCHETING IS NOT A TONE THE EPS COMMANDS. No notch, and no
phase lever at 7.79 Hz.** Reproduced at nw=256 and on the independent 100 Hz cave grid.

★ **AND THE GATE-2 HAZARD MOVED.** Signed-cmd↔column coherence² vs a shuffled-pairs control of
**0.009 [0.001, 0.061]**: 2–4 Hz 0.038 · 6–9 **0.123** · 9–12 0.090 · 12–18 0.133 · **18–24 Hz 0.310 —
the HIGHEST, above the ratchet's own band.** The loop is tightest in **grind #1's** band ⇒ **any future
filter's phase cost lands at ~21 Hz, not at 7.8 Hz.** (At 7.79 Hz: coh² 0.343, `|tq/cmd|` 6.24, phase
−30.9°; the rectified channel returns 0.009 = *exactly* the control.)

### 3. ★★★★ THE THREE SYMPTOMS — the instrument agrees with the operator on all three
**Grinding (he says FIXED).** `e_18-22`, engaged creep, on the ruler the ~109 target was measured on —
and the ruler is calibrated: this session reads V67 at **110.7** against the record's ~109.

| build | `e_18-22` |
|---|---|
| V67/r47 | 110.7 [75.2, 172.1] |
| V81/r67 | 69.1 · V84/r6d 221.8 · V85/r6e 343.7 · V86B/r70 186.5 |
| **V87/r71** | **400.2 [261.6, 917.4]** |
| **V88/r73** | **150.5 [118.5, 183.8]** |

**V88/V67 = 1.101 [0.424, 2.206] — a clean null ⇒ V88 is statistically indistinguishable from the kit's
best-ever grind-#1 result.** On the tighter creep ruler the separation from V87 is disjoint (161.0
[127.3, 420.0] vs 932.8 [442.6, 1532.5]). Negative control 32–38 Hz inside its null ⇒ band-specific.
🛑 V88/V87 = 0.549 [0.277, 0.979] excludes 1.00 but does **NOT** clear V87's own split-half null of
[0.30, 3.40] ⇒ **the load-bearing statement is the absolute level against V67, not the ratio.**

**Grind #2 (he says hints, could not elicit).** **ZERO events** in the strict creep-cornering regime
(0.3–4 m/s, |ang| ≥ 100°), max 367.3 against the 500 ct criterion — the same zero as V67/V68.
🛑 **Exposure 47.4 s = 29 % of the 166 s interpretability floor ⇒ formally UNINTERPRETABLE**; the zero is
real but weak, and is not upgraded. 5 marginal crossings elsewhere (1.02–1.31× threshold vs V86's 2796.5),
**four of them at highway speed** — events no prior route could have detected, not creep grind #2.

**Micro-ratcheting and ratcheting (he says these are the main remaining issues).** 🛑 **UNCHANGED, and
unchanged all the way back to V67**: `e_6-9` V88/V67 = **1.040 [0.759, 1.260]** over 14 matched cells —
the tightest null in the session. V88/V87 = 1.278 [0.801, 2.073], inside null. **That is exactly V88's
pre-registration.** ⇒ **The ratcheting did not get worse; the grinding above it came down, so it is now
the loudest thing left.**
🛑 **The data do NOT separate "micro-ratcheting" from "ratcheting" as two objects** — the apparent 9–10.5
and 10.5–12 Hz clusters are **wheel order 2** at higher speed. That is a statement about the instrument,
**not** about the car: the operator names two symptoms and he is the one feeling them.

### 4. ★★★★★ THE HIGHWAY — the ratchet is SPEED-INVARIANT, and it is now PROVEN
Never testable before; the four prior routes had 0.0 s engaged above 50 km/h. Every row carries a
per-window speed census and a wheel-order veto (orders 1–6, circumference swept 2.073–2.088 m).

| stratum | n | v med (m/s) | **f0 [CI] Hz** | prominence | **e_6-9 ct** | order-vetoed |
|---|---|---|---|---|---|---|
| creep <10 km/h | 26 | 2.11 | 8.01 [7.87, 8.47] | 9.01 | 402 | 10/36 dropped |
| 10–40 km/h | 60 | 7.40 | 8.08 [7.93, 8.18] | 5.18 | 286 | 114/174 dropped |
| 40–80 km/h | 36 | 13.20 | 8.31 [8.24, 8.69] | 2.85 | 195 | 21/57 dropped |
| **>80 km/h** | 58 | 30.23 | **8.36 [8.23, 8.49]** | 2.37 | **83.5** | **0/58 — intrinsically clean** |

**The discriminating test is the SLOPE: `f0 = +0.0102·v + 7.998 Hz`, against wheel order 1's 0.4807 —
47× flatter**, corr(f0, v) = +0.106. ⇒ **SPEED-INVARIANCE CONFIRMED [EVIDENCE].**
★ **The >80 km/h stratum is intrinsically order-clean** — at 30 m/s order 1 has climbed to 14.5 Hz, above
the band, so **no order 1–6 can reach 6–9 Hz at highway speed** ⇒ the cleanest ratchet measurement in the
corpus, and it cannot be a road-input artefact.
★ **Amplitude decays 4.8× from creep to highway (402 → 83.5 ct)** ⇒ **the ratchet is a LOW-SPEED
phenomenon in AMPLITUDE while being FIXED in FREQUENCY** — consistent with eliciting it in the car park.

### 5. ★★★★ THE 26–31 Hz RING IS REAL, AND IT IS 29.02 Hz
Marked UNSCOREABLE on `6f`/`70`/`6e`/`71` for exposure. Free argmax 24–34 Hz over 115 engaged windows
above 40 km/h: **f0 median 29.02 Hz**, prominence 10.25. Order 2 lands within 0.8 Hz in 41.7 % of windows
⇒ contamination is real; **after the veto 49/115 survive: `e_26-31` = 121.4 [77.6, 176.5], prominence
5.67 [4.82, 8.40]. The line SURVIVES the veto — it is not wheel order 2.** Same family as V81's 27.75 Hz
and V80's 27.4 Hz. **Above 80 km/h it is the dominant non-order band on every channel** (`tq` 32.28 vs
18–22 Hz 16.30; `rate_c` 3.46, the largest of six bands). **Grind #1 falls away at highway** —
`e_18-22` 161.0 (creep) → 43.0 [32.6, 86.1] (>80 km/h).

### 6. 🛑 WHAT ROUTE 73 COULD NOT ANSWER — recorded verbatim, unedited
1. **Ring-down ζ / Q.** 2 usable edges, one with the wrong sign. Needs a deliberate engage/hold/disengage protocol.
2. **The V88/V87 grind-#1 ratio against route 71's own noise floor** — V87's split-half null is [0.30, 3.40]; nothing under ~3× is resolvable on that arm.
3. **Grind #2 at creep cornering** — 47.4 s = 29 % of the 166 s floor.
4. **Any engaged-vs-manual contrast above 20 km/h** — zero manual seconds exist there.
5. **Micro-ratcheting vs ratcheting as two objects** — no instrument here separates them.
6. **Any 15–22 Hz claim from the 427 probe alone at highway** (the 28–35 Hz alias). The creep-band claim in §1 *was* separated, on the 100 Hz channels.
⊕ And the ladder at speed is null across V67/V81/V84/V85/V88 — **74 s above 80 km/h would need ~10 min** to resolve a 1.15× effect.

### 7. 🛑 INSTRUMENT DEFECT FOUND THIS SESSION — kit-wide, all 13 caches
`z["t"] == z["raw14_t"][1:]` and `z["probe"] == z["raw14_b4"][1:]` in **every** cache `_scratch/cache/r5e` …
`_scratch/cache/r73`. `extract()` appends `raw14_*` on every 0x14A frame but a **row** only after the first
0x18F, so the row family is permanently one sample shorter. **Pairing `t` with `raw14_b4` reads the cave
byte one frame (~10 ms) early = 28° of phase at 7.79 Hz.** It cost the orchestrator's own identity check
0.9437 instead of 0.9654. **Safe pairings: `(t, probe)` and `(raw14_t, raw14_b4)` — never cross them.**
Audit: `analysis-2020accord/verify/audit_raw14_offbyone.py`. **H2's script was checked and uses the aligned pair
⇒ H2 is unaffected.** ⚠ **NOT audited: whether any HISTORICAL result rests on the crossed pairing.**

### 8. 🛑 FIRMWARE LEVERS EXAMINED AND KILLED THIS SESSION — structure, not nulls
- **FactorD / `gp-0x6a10`** — the axis is **ABSOLUTE STEERING ANGLE, not a tracking error**, so the
  1/ω selectivity argument is dead: **this firmware has NO frequency-selective lever.** Also inert below
  ~35 km/h because FactorC's `Y[0]` = 0 multiplies in first. ⚠ **Scope: the inertness is speed-scoped and
  does NOT apply above ~35 km/h**, where 210 of route 73's engaged seconds now sit.
  🛑 The **auto-memory** copy of `accord-factord-is-the-angle-error-lever` was the stale pre-correction
  version and **sent a subagent down a dead thread this session** — corrected. **When a `reference_*` fact
  is corrected, correct BOTH copies.**
- **`0xC64C8` mode 2** — byte-exact **no-op**: `0xC61D4` = 0 on stock and on V88 (orchestrator-verified),
  so mode 2 = `clamp(gp-0x6acc[±8192] + 0, ±12288)` = mode 0. And even non-zero it is a flat scalar bias,
  never a filter. **Structurally impossible, not merely untested.**
- **`0xC61F6` (r24 deadzone, frozen at 3 in all 59 builds)** — **raising it cuts the WRONG way.** A
  fixed-count deadband clips the *smaller* signal first, and LF-sourced `dtorque` is ~12× smaller than
  HF-sourced for equal physical amplitude ⇒ it spends its budget on low-frequency content. Dead on
  arithmetic. (The record's standing "DO NOT" is about *lowering* it — a different claim.)
- **r24 has NO pole anywhere** between the difference and the aggregator sum (4 independent decompiles).
  r26 has a 2-tap boxcar but on its **gain**, not its signal: `|H(7.79 Hz)| = 0.9997`. ⇒ **adding a pole
  on this lane is a CODE edit, not a cal edit.**
- **Both friction relays are speed-gated only** ⇒ neither can explain the engaged-vs-manual asymmetry.
- ★ **The `<3 Hz` row is STRUCTURALLY protected from any r24-side edit**: the N=4 backward difference gives
  `|H(18 Hz)|/|H(1 Hz)| = 17.85×`, so a derivative-lane change cannot reach the LKAS command band.

### 9. 🛑🛑 THE OBVIOUS V89 — A BIGGER `0xC6446` DOSE — IS BLOCKED BY THE CLAMP
Orchestrator-computed, `analysis-2020accord/studies/models/orch_c6446_clamp_headroom.py`.
`r24 = clamp( (clamp(dtorque, ±5120) * gain) >> 10, ±8192 )`, LERP 2622 (mode 24 ≡ 26), V88 = 5244.
Against V65's `|dtorque|` = **123–839 ct over 120,049 frames**, folding in the **1.77×–2.55×**
scalar-vs-curve spread (hot end = 1.275× nominal, and the hot end meets the rail first):

| `0xC6446` | dose | `\|r1\|` to rail | hot-end margin | verdict |
|---|---|---|---|---|
| 2622 | 1.000× stock | 3199 | 2.99× | clear |
| **5244** | **2.000× — V88, FLOWN** | **1600** | **1.50×** | **thin — inside V80's blind spot** |
| 6555 | 2.500× | 1280 | **1.20×** | 🛑 at the rail at the hot end |
| 7866 | 3.000× | 1066 | **1.00×** | 🛑🛑 pins — relay class |
| 10488 | 4.000× | 800 | 0.75× | 🛑🛑 pins |

⇒ **The usable dose window above V88 is narrow to non-existent.** ★ **This gives a MECHANISM for
`accord-v62-fixed-the-grinding`'s "2× ≈ OPTIMUM, not a ramp" — the RAIL, not the tuning.**
🛑 **But the margin rests on a `|dtorque|` distribution measured on V65, a different build and route.**
The arithmetic is EVIDENCE; the margin is BELIEF.
⇒ **V89 should MEASURE `|dtorque|` on V88, not bet on V65's distribution.** `gp-0x6ada` is r24's
post-clamp RAM mirror — **1 writer / 0 readers, free, blast-radius-zero telemetry** — and settles it.
### 10. 🛑🛑 THE CO-MOVEMENT FAILED ITS OWN DOSE TEST — a retraction, out-of-sample
The +0.364 co-movement looked like a lever. **V88 is the experiment that settles it, against the slope.**
- Speed-partialled elasticity `d(log ratchet)/d(log 15–22 Hz cmd)` = **+1.082 [+0.814, +1.329]**
  (band rms, corr +0.646); prominence gives +0.682 [+0.256, +1.200].
- **Predicted from V88's 0.549× cut: ratchet ratio 0.523 [0.451, 0.614]** — far below the resolvable
  floor of 0.759, i.e. **plainly visible if real**.
- **Measured: `e_6-9` V88/V67 = 1.040 [0.759, 1.260]. The intervals DO NOT OVERLAP.**
- Inverting V88 into a causal elasticity: **b_causal = −0.065 [−0.385, +0.460]** — consistent with ZERO,
  and its **upper bound sits BELOW the observational slope's lower bound.** Not the same quantity.
- ⊕ **The 32–38 Hz NEGATIVE CONTROL also responds** (elasticity **+0.664 [+0.441, +0.827]**) — a band
  that is neither symptom tracks the command at ~60 % of the ratchet's rate ⇒ **operating-point
  covariation a firmware dose does not reproduce.**

⇒ 🛑 **DO NOT spend V89 on further HF command reduction hoping the ratchet follows.** On the most
optimistic elasticity still consistent with V88 (b = +0.46), halving the ratchet needs the 15–22 Hz
command at **0.22× of V87 — a further 2.5× cut on top of V88** — which reaches into the range where
0.5–3 Hz authority is at risk. **On the central estimate, no achievable cut moves it at all.**
⊕ **The operator's sentence:** *"Cutting high-frequency content out of the delivered steering command is
now a measured fix for the grinding and a measured NON-fix for the ratcheting."*

### 11. 🛑🛑 NEXT STEPS ARE ANALYSIS ON EXISTING LOGS — **NOT another drive.** Operator-corrected.
**The orchestrator recommended a dedicated ring-down driving session and was corrected: the diagnosis of
micro-ratcheting and ratcheting is a parking-lot-speed question, and route `73` already contains it** —
segments 0/8/9 give ~118 s engaged below ~15 km/h, exactly where D5 measured the ratchet at its largest
(402 ct). **A new drive buys nothing diagnostic.**

★ **And ring-down is no longer the only route to Q. V88 changed that and the session under-used it.**
Ring-down *was* the only ζ estimator that had passed its own control, so "we cannot measure Q" had
collapsed into "we need more disengagement edges". **V88's sign bit broke that**: H2 already produced
`|tq/cmd|` = **6.24 at 7.79 Hz, phase −30.9°**, with coherence² going **0.009 (rectified — exactly the
shuffled control) → 0.343 (signed)**. **That is a transfer-function measurement, and a resonance's Q falls
out of its peak shape and phase roll-through with no disengagement at all.** V87 could not do this because
rectification destroyed the phase — which is precisely why that session fell back on ring-down.

**⇒ THREE ANALYSES, all on data already on disk:**
1. **Fit `cmd → column` across 4–15 Hz on route 73's creep segments (0, 8, 9).** Extract Q from the peak
   and from the phase slope, coherence as the quality gate. **This is the measurement V88 was built to
   make possible, and the session used it only for a yes/no.**
2. **Pool ring-down edges across all 13 caches**, not just `r71`/`r73`. Only those two were screened, and
   only on `latActive` falling edges under strict criteria. ⚠ Screen by damper state: V87/V88 are stock on
   FactorC and pool cleanly; **V74–V86B do not.**
3. **Partial coherence against the IMU** (`imu_vert`/`imu_lat`, wheel speeds), run alongside 1 because it
   can undercut it: **if the mode is excited mainly by ROAD input rather than by the command, `cmd→column`
   is the wrong transfer function and its Q is biased.** Which path dominates is itself the result — it
   decides whether *any* command-side lever could ever work.

🛑 **The only thing that genuinely needs new driving is a BUILD comparison — and that needs a new build,
not a new drive.** Everything diagnostic about the two remaining symptoms at parking-lot speed is on tape.

⊕ **The ring-down sizing below is retained as knowledge, not as a request.** Revisit only if 1–3 return
coherence too low to fit — and even then, prefer a probe on a build being flashed anyway.

Ring-down is the only ζ estimator that passes its own control; route 73 gave **2 usable edges from 5
disengagements, one with the wrong sign.** Monte-Carlo of the actual fit through route 73's own beds:

| pre-edge amplitude | sd(log ζ) | N for ±50 % | N for ±30 % |
|---|---|---|---|
| 400 ct (creep) | 0.636 | 10 | 23 |
| **250 ct (35–45 km/h)** | 0.783 | **15** | **35** |
| 90 ct (highway) | 1.077 | 28 | 65 |

🛑 **NOT the parking lot — 35–45 km/h, straight, empty road.** 7–14 km/h is where **wheel orders 4–7 land
inside 6–9 Hz**, and an order does not decay when LKAS drops ⇒ it pins the floor and flattens the fit;
below ~5 km/h the lockout means LKAS is barely applying (6.9 s engaged below 5 km/h all route).
**Order-clean bands for 6–9 Hz: 1.8–3.6 · 33.8–44.6 · 67.7+ km/h.**
🛑 **The orchestrator's counter-argument was TESTED AND REFUTED** — he argued a persistent order should
land in the estimator's subtracted floor and cost dynamic range, not bias. Injecting a non-decaying tone:
**bias 1.01× (none) → 3.53× (25 % at −0.93 Hz) → 5.69× (50 % at +0.27 Hz).** Head-to-head, creep-with-order
needs **38** edges for ±50 % at sd_log 1.26; **road-no-order needs 16 at sd_log 0.80.** Road wins on both.
**Route 73's 5 edges failed as:** 3.5 s / 3.4 s manual after (needs 4) · 0.1 s engaged before (needs 3) ·
**envelope GREW after the edge** (re-excited by hands or road) · 1 USABLE. ⇒ **hold engaged ≥5 s, stay
hands-off ≥5 s after, disengage with the cancel button — never by grabbing the wheel or braking.**
✅ **The confound is ABSENT on V88, byte-checked**: FactorC is stock in all four modes and **mode 24 ≡
mode 26** (`0xD77DA`/`0xD77EE` = 0 where V86B had 908/875), and the full-image delta has **no edit
anywhere in `0xD6000–0xD8000`** ⇒ **disengaging removes the excitation and nothing else.**

---

