---
name: accord-r26-is-structurally-inert
description: ★★★ r26's multiplier avg (gp-0x69a4) is ~zero on this calibration -- its cal base 0xC6564 is 40 bytes of exact zero. r24 carries the ENTIRE torsion-bar rate lane, which re-attributes V42, V61 and V62.
metadata:
  type: reference
---

# ★★★ r26 IS STRUCTURALLY INERT — r24 carries the whole rate lane

`FUN_00039702` (a third reader of the same range) shows the RAM array `gp-0x641E`…`gp-0x6444` is an
**adjustment added in Q10 float to a fixed cal base at `tp+0x7564`**:
```c
local_5c[2] = (float)*(short*)(tp+0x7564) * 0.0009765625 + (float)*(ushort*)(gp-0x6444) * 0.0009765625;
```
**`0xC6564`–`0xC658C` byte-reads as 40 bytes of EXACTLY ZERO** (orchestrator-verified), and the zero run
is **bounded by non-zero data on both sides** ⇒ a deliberately-zeroed table, not sparse filler. No writer
found for the RAM adjustment cells (10 of 18 checked individually, sign + instruction context confirmed).

⇒ `stage1 = (dtorque × avg2) >> 10 ≈ 0` **regardless of dtorque** ⇒ **r26 contributes ~nothing**, and
**V62's `0x3AB76` edit was a NO-OP.**

## This re-attributes three builds
| build | edit | result | what actually happened |
|---|---|---|---|
| V42 | zeroed r26's gain | NULL | **r26 was already zero** |
| V61 | killed both taps | **WORSE** | this was killing **r24** |
| V62 | doubled both | grinding fixed 8–42× | this was doubling **r24** |

🛑 **SUPERSEDES the standing claim** *"r24 and r26 are not independent — killing either alone leaves the
other transmitting, so each null is uninformative about the lane."* **r26 was never transmitting.**
🛑 **A one-byte revert of `0x3AB76` would change NOTHING.** It was the leading mid-session candidate and
is dead.

⚠ **BELIEF, not proof.** Rests on a zero cal base + no writer in 10 of 18 cells. `read_memory` on live RAM
fails as it does for every RAM table here. A diagnostic/adaptive write path via the 8 unchecked cells or a
register-indirect method would overturn it.

## Related structural facts, byte-verified same session
- **Two-level scheduling.** Inner (per tick, `FUN_0003aa2c`): 4-point LERP on **motor rate** `gp-0x6ac0`.
  Outer (periodic rebuild `FUN_0003ad74`): selects **speed-class** records via voted speed `gp-0x6a5e`,
  breakpoints `0xC6010` = [0, 640, 3200, 6400] = **0/10/50/100 km/h**.
- **gain_A (r26) is NOT mode-indexed** (`0xC6A68`/`0xC6A7C`/`0xC6A90`/`0xC6AA4`, all modes).
  **gain_B (r24) IS**, via `gp+0x63fd`; mode 10 `0xD2AEC` X=[0,400,1500,3000] Y=**[2305,2304,2149,1948]**
  (nearly flat).
- 🛑 **LERP record layout: `count` is u16 at +0**, then X[n], then Y[n]. A u32 read shifts every field by
  2 bytes and yields absurd counts.
- ★ **8 of 10 aggregator lanes are ZERO-GATES, not clamps** (`value × (bool: in_range)`, e.g.
  `0x3ACB0`–`0x3ACB8`): full pass-through in range, **hard zero out of range** — deletes the lane exactly
  when the signal is largest. Only r24/r26 use true saturating clamps (±8192 @`0x3AB82`/`0x3AC42`;
  aggregate ±10240 hard clip @`0x3ACE8`).
- **Saturation is NOT a mechanism here:** measured amplitudes give dtorque **123–839**; the route's most
  violent transient implies **739**, r24 = 3,326 against a lane clamp of 8,192. Reaching ±10240 needs
  `avg2` ≥ 1,598, and `avg2 ≈ 0`.

See [[accord-v62-flashed-grinding-is-fixed]], [[accord-ratchet-is-a-saturated-resonance]].
