---
name: accord-angle-rate-lane-gp6bbe-top-candidate
description: "The boost lane gp-0x6bbe reads the steering ANGLE RATE gp-0x6a56 UNFILTERED (0x34AB8/0x34E8E, byte-verified). That signal carries the 20-25 Hz mode at 996x — MORE than torque's 877x — and the lane is same-signed/reinforcing. First candidate ever in the angle-rate domain; all ~50 falsified builds were torque-domain."
metadata:
  node_type: memory
  type: project
---

**Identified 2026-07-29. NOT YET BUILT — GATE 2 is open. This is the top surviving vibration candidate
after V56 eliminated `gp-0x6ad4`.**

## The finding

```
FUN_00034a72 (boost, writes aggregator summand gp-0x6bbe):
  0x34AB8   ld.h -0x6a56[gp] -> r13
  0x34E8E   ld.h -0x6a56[gp] -> r6
```
Byte-verified by the lead with an independent Python disp16 scan over `[0x34A72, 0x35000)`, after two
subagents disagreed. **`gp-0x6bbe`'s input is NOT torque-only.**

`gp-0x6a56` is the **steering angle rate**, and it is the single best-anchored control-path signal in this
firmware, because it is what the EPS TRANSMITS:
- CAN `0x14A` bytes[2:3] `STEER_ANGLE_RATE` ← `gp-0x69ea` = `-gp-0x6a56 >> 3`, gated `|raw*0.125| <= 1500`
- CAN `0x18F` bytes[2:3] `STEER_ANGLE_RATE` (10x finer) ← `-gp-0x6a56` directly
- sole writer `FUN_0003f776`: `gp-0x6a56 = clamp(polarity*(gp-0x6abe*48*cal(tp+0x713a)>>15), ±12000)`

⇒ opendbc ground truth, not inference. **We can measure this lane's input directly in any rlog.**

## Why it is the top candidate

1. **The mode is STRONGER on the rate channel than on torque.** Route 1c, V55: **877x** engaged/disengaged
   on the torsion bar, **996x on `STEER_ANGLE_RATE`**.
2. **The rate path is UNFILTERED.** Per a full decompile of `FUN_00034a72`'s tail: an internal 4-state FSM
   result MINUS the raw `gp-0x6a56`, clamped ±12000, then scaled by TWO speed-indexed LERPs (avg voted
   speed `gp-0x6a5e`, then max voted speed `gp-0x6a62`). **No EMA or IIR touches the rate path** — it
   bypasses the torque EMA (`0xC6372` = 205) entirely.
   ⇒ The recorded `-1.29 dB @1 kHz / -14.91 dB @100 Hz` figures describe only the TORQUE tributary and do
   NOT characterise this lane. **The unresolved `FUN_00022ca0` task rate therefore matters much less than
   it first appeared** — an unfiltered path passes 21 Hz regardless.
3. 🛑 **SIGN CORRECTED 2026-07-30 — IT IS NET DAMPING, NOT REINFORCING. This INVERTS the lever.**
   An earlier same-session pass called it "same-signed reinforcing" off the torque-EMA framing. A full
   disassembly re-trace shows the torque EMA is a **multiplicative amplitude scale**, not an additive
   branch, and the core signal is:
   ```
   0x34e96  sub r6,r28        rate_error = baseline - angle_rate_raw
   ```
   All downstream multipliers are non-negative and polarity `gp-0x6752` = +1, so **if `baseline` is slow
   relative to 22 Hz then `gp-0x6bbe ≈ −(gain)·angle_rate` — viscous DAMPING on angle rate.**
   ⇒ **CUTTING THIS LANE WOULD REMOVE DAMPING AND LIKELY MAKE THE GRINDING WORSE.** That is the V56
   mistake exactly — muting a lane whose sign was unproven, one build later.
   ⇒ **The lever inverts: the interesting direction is RAISING the gain to ADD damping at 22 Hz**, not
   cutting it.
   ⚠ **[INFERRED, moderate-high confidence, NOT time-domain simulated.]** It hinges on `baseline` being
   slow at 22 Hz (built from a slew-blended torque magnitude + a `gp-0x6a10`-indexed LERP +
   `sign(gp-0x6a02)`). **Certify by simulation before any build** — if `baseline` carries 22 Hz content
   with the wrong phase, the "damping" is compromised and raising the gain makes it worse.
4. **Speed-scheduled by two LERPs** — testable against the measured `f = 0.177*v + 20.48` and the
   amplitude-vs-speed behaviour.
5. **Never flashed, never proposed.** `0xC6372`/`0xC636E` appear in `build_v44/v56/v57_tva.py` only as
   ASSERTED-STOCK. Lineage-checked.

## 🛑 Why it was NOT built as V57

- The rate path's own bandwidth is **uncomputed**.
- The damping-vs-anti-damping **sign at 22 Hz is undetermined**.
- `gp-0x6bbe` is **base power steering**. Adding phase lag to the always-on assist loop is the **V48B
  brick class**, and V56 is the fresh precedent for muting a lane whose sign was unproven (bought nothing,
  cost damping).
⇒ Any V58 here needs a full GATE 2, and a **gain/clamp/LERP-Y edit that reduces authority WITHOUT adding
dynamics** is a different and far safer class than an alpha reduction. If only a lag insertion exists,
there is no safe build here.

## The full chain, byte-verified (mode INDEX 10 for this car)

```
0x34ab8  ld.h -0x6a56[gp],r13          raw angle rate
0x34ae6  setfnc r24                    validity: |angle_rate| < 12000
         [4-state FSM gp-0x682e -> baseline iVar13; override gate reads gp-0x6a10 (>10000)
          and gp-0x6a02 (>20000, CONFIRMED torque-domain: (gp-0x4f60*10)/gp-0x4ebc); dwell
          counter gp-0x68c8 vs cal tp+0x74d1 = 3760 x10]
0x34e8e  ld.h -0x6a56[gp],r6           raw angle rate, read #2
0x34e96  sub  r6,r28                   rate_error = baseline - angle_rate      <- THE DAMPING TERM
0x34e98  clamp +/-12000
0x34f20  term1 = (rate_error * K1[mode]) >> 7            K1 @0xD200C = 43
0x34f44  term2 = (term1 * speedLERP1(gp-0x6a5e)) >> 10
         clamp +/- clampBound[mode]                      @0xD2000 = 666
0x34ffa  term3 = (term2 * blendedMagnitude) >> 14        <- the torque EMA enters HERE, as a SCALE
0x35010  x polarity(gp-0x6752) = +1
0x35078  gp-0x6bbe = clamp(., +/- speedLERP2(gp-0x6a62))
```
**No EMA/IIR anywhere on the raw angle rate** — one subtraction and static clamps. Genuinely unfiltered
on the phase-carrying signal.

**speedLERP1** (`0xCA17C` → `0xD2834`): count=6, X=[0,640,2560,5120,7808,10240] = **[0,10,40,80,122,160]
km/h**, Y=[541,639,653,551,439,439] Q10 ⇒ a **broad hump peaking at 40 km/h**, 0.55-0.62 at creep and
0.61-0.55 on road — **NOT a strong monotonic speed rise**, so it does not by itself explain
`f = 0.177·v + 20.48`.
**speedLERP2** (`0xC7998` → `0xD20C0`): count=5, Y = **512 five times — FLAT.** It is a fixed ±512 clamp
dressed as a table, speed-independent on this calibration.

## Lever candidates — all four are pure static gain/clamp, none in any build script

All sit inside `DAMP_BLOCK` (`0xD2000`-`0xD2FFC`, shared CRC at `0xD2FFC`, already touched by V44/V47) but
at bytes that do **not** overlap either build's edits (`0xD27C6/DA`, `0xD2802/04/06`, `0xD2816/18/1A`,
`0xD209C/A8`) — checked by direct grep, not by "same 4 KB region".
- **`K1` @ `0xD200C` = 43** (Q7 gain on `rate_error`) — **cleanest single-point lever**; the pointer-array
  base `0xCA324` has **1 hit image-wide, this function only**.
- `clampBound` @ `0xD2000` = 666 — first byte of the shared block; handle CRC with care.
- speedLERP1 Y row @ `0xD2834+0xE..0x18`.
- speedLERP2 flat clamp @ `0xD20C0+0xC..0x14` — already flat, so uniform change has no shape side effect.

## Open items

- 🛑 **Certify the damping SIGN by time-domain simulation** before any build. This is now the gating item.
- `gp-0x6a10`'s domain (still unresolved); `gp-0x6a02` **closed — torque-domain**.
- `gp-0x6abe`'s own producer (upstream of the rate signal).
- Whether `baseline` carries any 22 Hz content — the one assumption the damping verdict rests on.

## Correction of record this supersedes

🛑 `reference_accord_aggregator_domain_audit_no_angle_lane_found.md` states *"No angle or angle-rate input
found in any of the 11 lanes"* and lists `gp-0x6bbe`'s domain as **TORQUE only**. That is **wrong** — the
audit characterised the dominant outer torque-EMA path and did not unwind the tail of a 625-instruction
function. Also 🛑 `reference_accord_no_steering_angle_tx_eps_does_not_own_angle.md` ("this EPS does not
transmit/own steering-wheel angle") is **wrong, not stale**: it searched for CAN ID `0x156`; this platform
puts `STEERING_SENSORS` at `0x14A`.

**How to apply:** this is the first lever candidate in the ANGLE-RATE domain. Every falsified vibration
lever on record (V39, V41, V42ch2, V43, V45, V46, V48A, V52C, V56) is torque-domain. Do not rank it
against them by analogy. See [[reference-accord-gp6a5e-is-speed-reclassifies-v44-v47]] and
[[accord-check-build-lineage-before-proposing-lever]].
