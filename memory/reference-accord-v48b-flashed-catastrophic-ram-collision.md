---
name: reference-accord-v48b-flashed-catastrophic-ram-collision
description: V48B (21.4 Hz notch code cave) was FLASHED 2026-07-21 and bricked violently — at car startup, parked, NO LKAS command, the wheel slammed full-authority side to side (operator shut it off in seconds; recovered by reflashing a known-good image). Root cause dual & confirmed: (1) a RAM collision — the biquad x2 state cell high byte gp-0x14FA/0xFEDF6B07 aliases a live monitor/DTC status bitfield, injected near-unity into the filter; (2) a lightly-damped resonator placed inside the always-on base-assist loop with no closed-loop stability check. Clock rate was fine.
metadata:
  type: reference
---

# V48B FLASHED → CATASTROPHIC (2026-07-21). Root-caused. The kit's THIRD code-cave brick (V24/V27/V48B).

**Symptom (operator):** on car startup, **parked, with NO LKAS command**, the steering wheel immediately
spun fast one way then the other (full-authority oscillation). Operator killed the car within seconds and
**recovered by reflashing a known-good image**. EPS hardware undamaged (a few seconds of full-authority
motion does not harm the rack/motor). This is exactly the "code cave = the kit's only bricked class"
(V24/V27) risk the [[reference-accord-v48b-notch-cave-build]] handoff flagged; it is now realized.

## Root cause — TWO confirmed defects, same underlying gap. Verified by GhidraMCP trace on stock code.bin.

### 1. RAM COLLISION (confirmed; the likely proximate trigger of the *violent* onset)
The cave's DF-I biquad keeps state in `gp-0x1500` (y1/out), `gp-0x14FC` (x1), **`gp-0x14FA` (x2)**,
`gp-0x14F8` (y2). The **high byte of x2, `gp-0x14FA` → absolute `0xFEDF6B07` (disp `-0x14F9`), aliases a
LIVE per-monitor/DTC status bitfield**: read as a packed 2-sub-field byte (`bits[5:4]` and `bits[3:0]`) by
`FUN_00051fbc`@`0x52052` and `FUN_00053f32`@`0x53fc8` (both `case 8` of a per-index status dispatch;
`ld.bu -0x14f9,gp,r10`). In the biquad, **x2 is multiplied by `b2 = 3977/4096 ≈ 0.97` — a near-unity tap**
— so any external write to that status byte injects up to ~±16000 (bits used → high byte 0x00–0x3F) into
the accumulator → `>>12` → clamps to **±25600 = full-scale torque in ONE sample** → motor slams. The
collision is **bidirectional**: the cave also `st.h`'s x2 every 1 kHz tick, **stomping that live monitor
byte 1000×/s**. Either direction is disqualifying; the write-into-x2 direction is the clean mechanism for a
**sudden, violent** (not slowly-growing) onset.
⚠ **Writer of the status byte was NOT positively located** (register-indirect + a demonstrated 6-byte
extended-displacement encoding are blind spots for literal-disp scans). So "the monitor writes it at
key-on" is *highly plausible, not proven*. The **aliasing itself is confirmed** and is enough to condemn
the build. The other 3 cells (y1/x1/y2, all 8 bytes) are clean by two independent exhaustive methods.
⚠ `gp-0x14FA` lives inside the **documented sparse-flag RAM region `gp-0x1401..gp-0x1502`** — a POISON
zone for cave state. Vetted-safe 32-bit-clean alternative already on record: **`gp-0x14E0` / `0xFEDF6B20`**.

### 2. LIGHTLY-DAMPED RESONATOR DROPPED INTO THE ALWAYS-ON BASE-ASSIST LOOP (confirmed placement; closed-loop stability never modeled)
The notch's OWN poles are r=0.979 → **ζ≈0.157, Q≈3.2 at 21.4 Hz — a lightly-damped resonator**, not a
benign attenuator (its numerator zeros mask the ring open-loop; in a feedback loop the zeros do not protect
it). The 7 repointed lanes (`FUN_0002c478`@2c480, `FUN_000352b4`@354d2/@35aa4, `FUN_0003a382`@3a6ca/@3a7ca,
`FUN_0003b49a`@3b4a8, `FUN_0003b66a`@3b672) are the **always-on base power-steering assist loop** into the
aggregator `gp-0x6b94` → governor → delivered command `gp-0x6b98`, **gated only on EPS operating state
`gp-0x67fa`∈{4,5,8,10,11} / `gp-0x67fe` — NO LKAS-engaged gate, NO road-speed gate** (confirmed; zero speed
reads). That is why it fired **parked, hands-off, no LKAS**. The design validated the filter OPEN-LOOP
(pole radius <1, DC unity 73/73, no int32 overflow) and inserted only its **single-frequency magnitude**
`|N(21.4)|` into the *LKAS* loop-gain model — which actually predicts the notch *helps*. The **closed-loop
stability of the base-assist loop the signal actually lives in was never analyzed**; the notch injects
±25° of phase across 18–26 Hz (the design's phase check looked only at 1–5 Hz, the forward-LKAS crossover).
`eps_loop_gain_model.py` Task 4(d)'s placement claim — *"OFF the safety-critical motor-command path… base
assist loses only its 21 Hz response, which it does not need"* — is **falsified on-car** (see [[reference-accord-collocation-motor-rate-damper-dead]] for the loop-gain model this sits on).

### 3. EXONERATED: clock rate
Hook `0x7FEAC` is in `FUN_0007f3f8`, called from the confirmed ~1 kHz control task `FUN_0002214a`
(→`FUN_0006bb08`→`FUN_0007f3f8`), gated on the same `gp-0x67fa` mask as the undivided sign filter; reached
**exactly once per call, no loop, no sub-rate divider**. The biquad is **correctly clocked** at fs=1000 —
this was a worry and it is clean.

## The unifying lesson (see [[feedback-cave-two-gates-ram-ownership-and-closed-loop]])
Both defects come from validating the cave **in isolation**. "The filter is correct" ≠ "the change is
safe." A code cave is only as safe as **the RAM map it writes** and **the control loop it lands in** —
neither of which the disassembly/CRC/open-loop-DSP verification touched. Three caves have now bricked
(V24, V27, V48B); every cal-only build since V29 has been safe. **Code caves remain the highest-risk change
class; the ultimate check is still first-minutes on-car observation.**

## Related
[[reference-accord-v48b-notch-cave-build]] — the build (now amended with this outcome).
[[feedback-cave-two-gates-ram-ownership-and-closed-loop]] — the prevention gates.
[[reference-accord-collocation-motor-rate-damper-dead]] — the loop-gain/collocation model the notch rested on.
[[reference_accord_gp4f60_is_sensor_b_column_torque]] — gp-0x4f60 = the base-assist driver-torque input.
