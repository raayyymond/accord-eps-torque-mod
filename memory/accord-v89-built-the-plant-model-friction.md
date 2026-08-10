---
name: accord-v89-built-the-plant-model-friction
description: V89 raises the modelled Coulomb friction K1 (0xC40D2 102->204) in FUN_0003b8f6's plant model — the first build to touch the model rather than the command or a lane summing into it.
metadata:
  type: project
---

**V89 BUILT, VERIFIED, UNFLASHED, 2026-08-09.** Base = flown **V88**.
image `6eae6826881cb5fd737ab433919f64a556ed027126e3f056ed8f03c13206f159`
rwd `cdce053e3a86bf2c8857d7f229c015c747e209fa1222b91e3df863f1f44cf7ef` (986,042 B)
**4 runs / 8 bytes, ZERO unattributed; 50/50 CRC on image, readback and the shipped file.**

| addr | from | to | what |
|---|---|---|---|
| **`0xC40D2`** | 102 | **204** | K1, the `|model|`-proportional modelled Coulomb friction, **2.000×** |
| `0xC4B38` | `6894` | `1e95` | cave probe → `gp-0x6ae2` = **friction × 1024** |
| `0xC4B46` | `a8` | `a6` | rung `sar 0x8`→`0x6`, ±64 |

## The chain (Ghidra, decompile then assembly)
```
FUN_0003b8f6  friction = clamp( EMA_a( |model|*ratio*K1/1024 + ratio*K0/1024 ), ±10 )
              ratio    = clamp( polarity * gp-0x6abc * 12 / cal[0xC40BC] , ±1 )
              out      = clamp( (model − friction − damping) * cal[0xC6468], ±20000 )
  → gp-0x6bfc → FUN_0003bc20 → gp-0x6bfe → FUN_00038148:
              residual = MODEL − ACTUAL ;  gp-0x6b70 = sign(res) × LERP(|res|)
```
**A DISTURBANCE OBSERVER.** Under-modelled Coulomb friction lands in the residual and the observer
chases it = a stick-slip ratchet. `0xC64B0` = 1 ⇒ the path is live.

## Why this cell
★ **`0xC40D2`: ONE reader (`0x3BAFE`), ZERO writers, virgin on all 88 builds.** Censused twice
through the **`hw2 = disp|1`** trap (`ld.hu 0x50d2[tp]` encodes `0x50d3`; a naive scan returns a
FALSE ZERO — it did on the first pass).
★ K1 scales the `|model|` arm **alone** ⇒ raises magnitude without flattening anything into a relay.
**Not the V80 class.** 🛑 `0xC4080` (K0, the NEVER-RAISE pure-relay hazard) untouched at 0.
★ GATE 2: friction enters with a **minus** sign; the ±10 clamp binds at `|model| ≥ 50` vs a working
point of 0.2–1.0 ⇒ ~50× margin.
★ `gp-0x6ae2` is 1 writer / 0 readers ⇒ blast-radius-zero probe. The new load's two halfwords are
each already flying (`2437` @0x55DF0, `1e95` @0x3BC04).

## Pre-registration
**IDENTITY** ≈0.60 = V89 flew, ≈0.97 = V88 did (V88's `b6 == MOTOR_TORQUE ≥ 160` held at 0.9654,
chance 0.6028; V89's cave reads a different cell). **H1** probe rung duty strictly in (0,1) or the
flight is uninterpretable. **H2** engaged 6–9 Hz FALLS vs V88, rate- and speed-matched, control band
not falling as much. **H3** 0.5–3 Hz command unchanged (structural). **H4** the operator scores it.

🛑 **The dose DIRECTION is measured** ([[accord-engagement-amplifies-6-9hz-via-coulomb-relay]]);
**that K1 acts like the gate is BELIEF** — the gate confounds magnitude with relay-ness.
⚠ **COST: may feel notchier/heavier on-centre. The instrument cannot see that.**
