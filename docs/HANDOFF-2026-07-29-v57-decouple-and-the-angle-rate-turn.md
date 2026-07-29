# HANDOFF 2026-07-29 — V57 decoupling, and the search turns to the ANGLE-RATE domain

**Session shape:** orchestrator + 6 subagents, driven by four operator challenges to the kit's *inferred*
variable identities. Three of the four overturned something real. The session produced one build (V57),
eliminated one hypothesis by measurement, invalidated the stated rationale behind two flashed builds, and
moved the vibration search out of the torque domain for the first time in ~50 builds.

**Predecessor:** `HANDOFF-2026-07-29-v56-drive-mute-is-null-and-costs-damping.md`.

---

## 0. The operator's four challenges, and what each returned

| challenge | verdict |
|---|---|
| *"Move the LKAS 4× gain to only hit the LKAS path"* | ✅ **Correct and now BUILT as V57.** The 4× was leaking into four in-loop feedback readers |
| *"How do we know that's steer angle rate? Our only ground truth is opendbc"* | ✅ **Label earned, domain WRONG.** `gp-0x6ac0` is **motor resolver** rate. The column rate is `gp-0x6a56` — and that turned out to be the key to the whole session |
| *"Maybe the 2 torque sensors A/B are really 2 different sensors"* | ✅ **Real pair, wrong location on record.** Main/Sub live *inside* `gp-0x4f60`'s producer (`KFC_STORQUE_0/1`). "Sensor A" (`gp-0x6a5e`) was never a torque sensor at all |
| *"The plausible steering torque model — maybe it ignores LKAS torque"* | ❌ **Honest null.** `gp-0x6ad6` has 3 static refs image-wide, one exit door, already tested by V56. It *is* partly command-aware via `gp-0x6b70` |

Plus, raised mid-session and decisive: *"Highly doubt there is no return-to-center logic."* **Correct.**
`gp-0x6b62`/`FUN_00036388` is a real return-centre lane the record never mapped — and chasing it is what
surfaced the angle-rate finding below.

---

## 1. What was BUILT — V57

```
0x2A1F0  ld.h displacement  0x746C -> 0x7CD0   (tp+0x7CD0 = 0xC6CD0)   [MAIN]
0xC6CD0  private LKAS gain  0xFFFF -> 3564                             [CAL]
0xC646C  shared sensor scale  3564 -> 891 (stock)                      [CAL]

14 bytes off V55 (6 edit + 8 CRC), 88 off V38. 50/50 CRC. RWD round-trip with every gate re-run.
_v57_plain_image.bin  SHA 9a027e82c065d48721bd194e315528516ef6963fc4821511c7e7242676ab13ea
V57 .rwd              SHA 816d225522f7a327ee9b97bf096bec918e7e36c82f57a17225e0f5455216d019
```

Verified against the **built image**, not the builder's own claims: `25 3f 6c 74` → `25 3f d0 7c`, forward
reader resolves `0xC6CD0` = 3564, the other five resolve `0xC646C` = 891.

🛑 **It is a correctness fix and is expected to be NULL for the grinding** (≤0.28 dB at 22 Hz). Say that
plainly in any report. ⚠ Manual steering feel **will** change — readers #3-#6 are not engagement-gated.

**Flash V55 first.** V57 is cut from V55, so flashing it reverts V56's mute *and* changes feedback gains
simultaneously — confounding feel assessment and forfeiting the cleanest test that V56's mute was live
(the 8.69 Hz line should vanish on V55).

---

## 2. The hypothesis that died — and how

A deadband + sign-consistency relay in `FUN_00028ea6` (`0x2a1ae`-`0x2a206`) explained the **entire**
symptom profile: hands-off worst, engagement-dependent, killed by significant *directional* driver torque,
killed by saturation, frequency drifting with speed rather than sitting at a fixed pole. It also had a
motive — `0xC61B8` = 102 was **never rescaled** while its siblings `0xC61B2`/`0xC61B4` went ×4 with the
gain, so the dead zone covers ~4× more of the LKAS working range than the factory validated.

Four subagents disagreed about it. The lead resolved it two ways:

1. **Routing (subagent was wrong):** the block **is** on the forward path.
   `r9` → `add r9,r11` @`0x2a1fc` → ×POLARITY×GAIN → clamp → `mov r11,r1` @`0x2a226` →
   `cmove 0x0,r1,r16` @`0x2a2c2` → `st.h r16,-0x6b3c` @`0x2a2ea`. The `-0x6b38` store at `0x2a23c` is a
   **diagnostic copy**; a subagent met it first and called the whole block diagnostic-only.
2. **Liveness (hypothesis was wrong) — settled by MEASUREMENT.** `gp-0x6806`, the enable, is
   **transmitted**: CAN `0x18F` byte4 bit3 = `STEER_CONTROL_ACTIVE`.
   ```
   route 24, 18,000 frames, 180.0 s @100 Hz
   ==1 : 96.26%   ==0 : 3.74%   transitions: 2   max possible toggle: 0.1 Hz
   ```
   **Two transitions in three minutes against a 20-25 Hz mode.** Dead.

> **The transferable lesson:** static reachability told us the gate *can* activate; the bus told us how
> often it *does*. Four subagent traces and one wrong conclusion; the rlog answered it in one query.
> **Before building against any internal flag, check whether it is already on the bus.**

A second lesson worth keeping: the hypothesis explained *everything*, which should have raised suspicion
rather than confidence. The thing that actually explains "directional torque kills it" turned out to be a
plain authority cutoff (§3), not an oscillator.

---

## 3. What explains the operator's symptom — the driver-override curve

`FUN_00028ea6` @`0x29a74`, byte-verified at the pointer targets:

```
gp-0x682f = min(|gp-0x4f60| >> 5, 255)      ; magnitude
sign(gp-0x4f60)                              ; direction -> selects 0xCBA74 vs 0xCBA04
0xE4468/0xE447C/0xE43F0 : X=[70,72,78,80]   Y=[254,234,12,0]   -> raw torque 2240..2560
0xE4270/0xE42E8         : X=[32,38/42,80,112] Y=[255,255,255,0] -> raw torque 1024..3584
```

**LKAS authority collapses 254 → 0 between raw torque ~2240 and ~3584** (≈±2190..±3500 in DBC units), in
whichever direction the driver pushes. Route 24 engaged frames: 88.7% below 500 counts, 0.42% inside the
collapse band — so the band is genuinely reached on real drives.

⚠ **This is the KILL, not the CREATION.** Hands-off the curve is flat at 254 and contributes no gain
variation. It also explains why a naive rlog sweep appears to *contradict* the operator: above the band
LKAS authority is already zero, so you are measuring a disabled controller while broadband power from
active steering is at maximum. **Any driver-torque sweep must use a prominence estimator
(peak / local floor), never raw band power** — the conditioning variable is the measured channel.

---

## 4. ★★ The real turn — the search leaves the torque domain

```
FUN_00034a72 (boost, writes aggregator summand gp-0x6bbe):
  0x34AB8   ld.h -0x6a56[gp] -> r13
  0x34E8E   ld.h -0x6a56[gp] -> r6
```
Byte-verified by the lead after two subagents flatly contradicted each other.

`gp-0x6a56` is the **steering angle rate** and it is the single best-anchored control-path signal in this
firmware — it is what the EPS **transmits** as `STEER_ANGLE_RATE` on `0x14A[2:3]` (via `gp-0x69ea`, `>>3`)
and the 10× finer `0x18F[2:3]`. **opendbc ground truth, not inference.**

Why it is now the top candidate:
- **The mode is stronger there than on torque** — 996× on `STEER_ANGLE_RATE` vs 877× on the torsion bar.
- **The rate path is UNFILTERED** — an FSM result minus raw `gp-0x6a56`, clamped ±12000, scaled by two
  speed-indexed LERPs. **No EMA/IIR touches it.** ⇒ the recorded −1.29/−14.91 dB figures describe only the
  torque tributary, and **the unresolved `FUN_00022ca0` task rate matters far less than it appeared.**
- **Never flashed, never proposed.** Every one of the ~50 falsified levers is torque-domain.

### 🛑🛑 GATE 2 was answered before this handoff shipped — and it answered AGAINST cutting the lane

An earlier pass this same session called `gp-0x6bbe` "same-signed, reinforcing" off the torque-EMA
framing, and this document said so in draft. **A full disassembly re-trace corrects it**: the torque EMA is
a **multiplicative amplitude scale** (`term3 = (term2 * blendedMagnitude) >> 14` @`0x34ffa`), not an
additive branch, and the core signal is

```
0x34e96  sub r6,r28        rate_error = baseline - angle_rate_raw
```

Downstream multipliers are all non-negative, polarity `gp-0x6752` = +1 ⇒ with `baseline` slow at 22 Hz,
`gp-0x6bbe ≈ −(gain)·angle_rate` — **viscous DAMPING on angle rate, not reinforcement.**

⇒ **Cutting or muting this lane would REMOVE damping and likely make the grinding WORSE — the V56 error
exactly, one build later.** The lever **inverts**: the interesting direction is **RAISING** the gain to add
damping at 22 Hz. Cleanest single point: **`K1` @ `0xD200C` = 43** (Q7 gain on `rate_error`; pointer base
`0xCA324` has **1 hit image-wide, this function only**). Three further candidates — `clampBound` `0xD2000`
= 666, speedLERP1 Y row `0xD2834+0xE..0x18`, speedLERP2 `0xD20C0+0xC..0x14` — all inside the shared
`DAMP_BLOCK` but at bytes that do **not** overlap V44's or V47's edits (grep-checked, not
region-checked). None appears in any `build_v*_tva.py`.

⚠ **[INFERRED, moderate-high confidence, NOT time-domain simulated.]** The whole verdict rests on
`baseline` being slow at 22 Hz. 🛑 **Certify by simulation before building.** If `baseline` carries 22 Hz
content with the wrong phase, raising the gain makes it worse.

⚠ Two more corrections from the same trace: **speedLERP2 is FLAT** (five entries of 512 — a fixed ±512
clamp dressed as a table), and **speedLERP1 is a broad hump peaking at 40 km/h**, not a monotonic speed
rise, so it does not by itself explain `f = 0.177·v + 20.48`.

> **This is the session's second near-miss of the same kind.** The relay hypothesis fit every symptom and
> was wrong; the "reinforcing boost lane" fit the symptom and had the **sign backwards**. Both were caught
> only by going one level deeper than the first plausible answer. In this domain a lever's *sign* is worth
> more scrutiny than its magnitude — magnitude errors are null results, sign errors make the car worse.

### 🛑 The damping verdict's ONE assumption is contradicted by arithmetic — sign is UNRESOLVED both ways

The "net damping" reading rests entirely on *"`baseline` is slow relative to 22 Hz"*. The slew blend
named in `baseline`'s own construction is `PTR_DAT_ca06c[mode]` = **102/1024**:

```
alpha = 102/1024  ->  fc = 15.85 Hz
   1.0 Hz : |H| = 0.998  ( -0.02 dB)  phase  -3.3 deg
   8.7 Hz : |H| = 0.887  ( -1.04 dB)  phase -26.0 deg
  22.0 Hz : |H| = 0.605  ( -4.36 dB)  phase -48.9 deg     <- NOT slow
  25.0 Hz : |H| = 0.556  ( -5.10 dB)  phase -51.8 deg
# what "slow" actually looks like in this firmware, for contrast:
# FUN_00036682 alpha = 6/1024 -> fc = 0.933 Hz, |H(22)| = 0.043 (-27.4 dB)
```

⇒ `baseline` plausibly carries **~60% of a 22 Hz component at −48.9°**, so
`rate_error = baseline − angle_rate` is **not** `≈ −angle_rate` — it is a difference of two comparable
terms in quadrature. A quadrature component is exactly how a damper acquires enough phase shift to
destabilise, depending on the plant's torque→angle-rate phase.

🛑 **CONSEQUENCE: the sign is UNRESOLVED IN BOTH DIRECTIONS.** Cutting the lane may remove damping;
**raising `K1` may amplify a term that is not damping.** Neither direction is safe on assumption, and
"raise the gain" must NOT be read as a settled recommendation.

⚠ The two traces also disagree on where the slew blend lands — one puts `102/1024` in the multiplicative
`blendedMagnitude`, the other lists it inside `baseline`'s construction. **That ambiguity is itself the
blocker**: it decides whether the 22 Hz content is an amplitude modulation (second-order) or an additive
quadrature term (first-order). Resolve it before simulating, then simulate.

---

## 5. Corrections of record generated this session

Full detail in `STATE.md` "Corrections of record" and the five new memory files. The load-bearing ones:

1. 🛑 **`gp-0x6a5e` is voted vehicle SPEED** ⇒ the damper Factor C LERP is speed-indexed ⇒ `Y[0]=0` means
   *below ~35 km/h* ⇒ **V44 and V47 were aimed at a mechanism that does not exist.** Their on-car results
   stand; the rationale is withdrawn. The "2240 counts driver torque" figure is a **number collision** with
   the override curve's unrelated torque breakpoint.
2. 🛑 **Split every `FUN_00028ea6` scan at `0x2a30d`** — `gp-0x6806` has 16 raw writers = **8 live + 8
   dead-echo**; `gp-0x6b30` has 4 refs = 2 live + 2 dead.
3. 🛑 **The aggregator has ELEVEN summands, not 9** — `r24`/`r26` are computed inline at
   `0x3aa9c`-`0x3ac58` and were missing from every prior list. **Both already flashed and FALSIFIED**
   (V39, V42 ch.2) — and a subagent re-proposed them as "never previously proposed" this session. That is
   the **fourth** such re-proposal; `BUILD-LINEAGE.md` now carries an explicit warning on those rows.
4. 🛑 **`STEER_WHEEL_ANGLE` is not a second angle** — bit-identical to `STEER_ANGLE` in 11,999/11,999
   frames; `gp-0x69ec`/`gp-0x69ee` written from the same register in every branch. There is one angle,
   transmitted twice. (The torsion-bar-twist localizer this enabled is therefore a dead end — recorded so
   nobody rebuilds it.)
5. 🛑 **`reference_accord_no_steering_angle_tx_eps_does_not_own_angle.md` is wrong, not stale** — it
   searched for CAN ID `0x156`; this platform uses `0x14A`.
6. ⚠ **`gp-0x6b86` is a peak-hold** ⇒ its "#2 strongest carrier, −3.9 dB" ranking is invalid.
7. ⚠ **`gp-0x6ac0` is motor resolver rate**, not column rate.

---

## 6. Open items, ranked

1. **`gp-0x6bbe` angle-rate tributary**: end-to-end gain at 20-25 Hz, the two speed-LERP tables byte-read
   and evaluated at creep *and* road speed, and the **sign/phase at 22 Hz**. GATE 2 — nothing builds
   without it.
2. `gp-0x6a10`/`gp-0x6a02` (bound checks 10000/20000 in that lane's FSM enable). If either is a
   driver-torque magnitude, the lane has a directly testable override mechanism.
3. `gp-0x6abe`'s producer — upstream of the angle-rate signal itself.
4. `FUN_00022ca0`'s exact task rate — **downgraded**, see §4. Task table base `0xBB858` found; no
   dispatcher located; `OSTM1` confirmed unconfigured.
5. **The few-Hz shake remains a TYRE item** — wheel order 1, implied circumference 2.088 m.
   **Get a road-force/balance check.** No firmware edit addresses it.

---

## 7. Recommendation

**Flash V55.** Undo V56, which is falsified and which the operator reports degraded the car. Confirm the
8.69 Hz line disappears — that is also the cleanest available proof the mute was live. Then V57 when the
correctness fix is wanted, and V58 only once the angle-rate lane's damping sign is settled.

🛑 **Flash only on explicit operator instruction naming the file and the bus.**

---

## 7. LATE IN THE SESSION — the operator reopened the deadband, and found a real hole

The lead had eliminated the deadband + sign relay by measuring `STEER_CONTROL_ACTIVE`. The operator
asked for the telemetry to be repointed at it anyway. Checking the packer before arguing turned up the
flaw in the lead's own "no":

```
0x55c76  ld.bu -0x6806,gp,r15
0x55c7e  andi  0x1,r15,r15      <-- PARITY
0x55c82  shl   0x3,r15
```
The bus carries `gp-0x6806 & 1`. The gate tests **exact equality** (`cmp r0,r12 ; bne`, `0x2a1ba`).
Four of the flag's eight live writers store a **register**, not a literal, so a value of 2 reads as
bit0 = 0 while the gate is DISABLED — and a 0↔2 toggle at 22 Hz would have been wholly invisible:
bit3 flat, zero transitions. The elimination's last step rested on an argument, not a measurement.

⇒ **V57 was modified to carry a deadband-gate probe**, replacing V55's cave payload at the same base
`0xC4B34` / hook `0x55C0E` / 68-byte extent (no widening):

```
0x14A byte4  bit7 = 1                  liveness
             bit6 = (gp-0x6806 == 0)   the EXACT gate test the bus cannot give
             bit5 = (gp-0x69b0 != 0)   ramp gain live
             bit4 = (gp-0x6b30 == 0)   gate output exactly zero
             bit3 = (gp-0x6b30 <  0)   gate output sign
```
Bits 4+3 give the output's 3-state {neg, zero, pos}; a chattering relay visits zero between sign
flips, so bit4's spectrum carries a 20-25 Hz line if the mechanism is real. Decoder:
`rlog-tools/decode_v57_deadband.py`. **Expected NEGATIVE**, recorded up front.

⚠ This raises V57's risk class: it is now **code in the 1 kHz TX path**, not a cal-only edit. GATE 1 is
inherited rather than vacuous (same base/hook/extent, read-only, no scratch RAM, r6/r7 already scratch).

## 8. Two corrections the operator forced, both against the lead

**(a) "Manual steering feel WILL change" — WITHDRAWN.** The operator said feel had not changed from V9
through V31 or V38. The plain-image archive makes it a THREE-point A/B:

```
              0xC646C   0xC61B2/B4
stock / V9        891          512
V22 - V37        1782         1024
V38 +            3564         2048
```
All three driven, no felt difference. Disengaged, the forward reader `0x2A1EE` is idle, so manual feel
depends ONLY on readers #3-#6 — exactly the set V57 reverts. **V57's experiment has already been run
on-car, in both directions, with a null result.** The lead's claim was an inference from "not
engagement-gated", which establishes those readers are LIVE, not AUDIBLE.
⇒ It also strengthens the build: independent evidence the four feedback readers sit below perception
across a 4× range, corroborating the −46/−58 dB figure for #5 and extending it to #3/#4.

**(b) The gain was TWO doublings, not one.** `BUILD-LINEAGE` recorded `891→3564 at V22`. Wrong: V22 set
**1782**, V38 set **3564**. ★ **The golden model had this right all along** (`V31: 1782`, `V38: 3564`) —
the flat lineage file was the wrong source. Corrected. It also sharpens the deadband point: `0xC61B8`
stayed at 102 through **both** doublings while its sibling clamps doubled twice.

> **Session-wide pattern worth carrying forward.** Four times a confident answer had to be walked back:
> the relay hypothesis (fit every symptom, killed by a bus measurement), the "reinforcing" boost lane
> (sign backwards), the "net damping" reading (its one assumption contradicted by a 15.85 Hz filter),
> and "feel will change" (three-point A/B says no). Every one was caught by going one level past the
> first plausible answer — and two of the four were caught by the **operator**, not the analysis.
