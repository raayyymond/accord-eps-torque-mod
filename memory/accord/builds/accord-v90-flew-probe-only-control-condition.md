---
name: accord-v90-flew-probe-only-control-condition
description: "V90 flew as route 77 — 17.91 engaged min, 86.41%, fault-free, identity PASS b4==0 on 124,362/124,362 frames. It is PROBE-ONLY (byte-identical to V89 in every calibration cell), so the operator's report of all three symptoms still present is the CONTROL CONDITION, not a failed fix. Deliverables: gp-0x6b26's full distribution with EXACTLY ZERO clamp duty in every stratum, and the observer gate gp-0x6c00 measured for the first time — it never fails, 0 of 124,362 frames."
metadata:
  type: reference
---

# V90 flew, route `77` — the probe-only control condition. 2026-08-11.

Route `00000077--7411859c54`, 21 segments, 1245.3 s, cache `_scratch/cache/r77/`.
Scoring: `docs/scoring/SCORING-2026-08-11-v90-flight.md`.

**Exposure:** engaged **1074.6 s = 17.91 min = 86.41 %**, 9 episodes all ≥10 s (longest 276.8 s);
≥50 km/h **316.4 s**, ≥80 km/h 42.0 s, v_max 90.4 km/h; micro-ratcheting regime (1–13 °/s) 437.6 s ·
ratcheting (13–50 °/s) 196.0 s · macro 76.7 s; manual 169.0 s of which **67.7 % parked**.
**Fault-free:** `STEER_STATUS` {0: 124,358, 3: 3}, DTC-active duty **0.000000** / 0 transitions,
**0 sentinels** on `0x14A` and `0x18F`, `CONFIG_VALID` 1.0000, no EPS entry in 3,489 `onroadEvents`.

★ **IDENTITY PASS, parameter-free and SINGLE-FRAME: `b4 == 0` on 124,362 / 124,362 frames** —
impossible on V86B/V87/V88/V89, where `b4` railed at exactly 1.0000 over 254,085 frames. The
`(byte4>>3)&0x1F` histogram lands entirely in the V90-only alphabet `{1,5,9,13,17,21,25,29}` with
**zero** frames in `{3,7,15,23,31}`; every value is odd ⇒ `b3 ≡ 1` and the field is read at the right
bit offset.
⊕ **This is why reclaiming a rung stuck at duty 1.0000 is worth more than whatever you put on it — it
MOVES THE ALPHABET**, and that is what makes an identity test single-frame.

## 🛑 It is PROBE-ONLY, so the operator's report is a CONTROL, not a failure

**V90 is byte-identical to V89 in every calibration cell** — `0xC40D2` stays 204. It changes only the
cave (62 → 74 bytes) and repoints CAN 427 `MOTOR_TORQUE` to `gp-0x6b26`.

**Operator, verbatim:** *grind #1 still exists · micro-ratcheting still exists · grind #2 can be felt
on the highway-speed curves or lane changes · parking lot testing · highway and street level testing.*

⇒ **the same firmware, driven three ways, still produces all three complaints.** Nothing is fixed.

## The two deliverables

1. **`gp-0x6b26` measured for the first time on any build.** Engaged p50 **5.5** / p90 39.1 / p99
   **114.3** / **max 319.1** against the ±511 clamp; **clamp duty EXACTLY 0.000000 in every stratum**;
   wire saturation 0.000000 ⇒ every sample is an honest measurement. **The lane is NOT a relay today.**
   Clipping ladder: never pins to **1.60×** · <0.1 % to 2.75× · <1 % to 4.45×.
   🛑 **That is a CLIPPING ladder, NOT a dose budget** — see
   [[accord-six-levers-closed-on-arithmetic]] for the int32 wraparound that binds first at ≈1.6005×.
2. **The observer gate, never once measured before: `gp-0x6c00 < 0` on 0 of 124,362 frames**,
   20.49 minutes, engaged **and** manual, in **every** wheel-rate bin. The observer's success path ran
   on every frame of this drive.

⊕ **b6's guessed threshold (512), V90's ONE free parameter, landed inside its predicted 0.10–0.50
bracket** at 0.2535 ⇒ **do not move `0xC4B4A`.**

## Artefacts

```
image  _v90_V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26_plain_image.bin
       sha256 28ac817bc3f76958ad5a33316e420c734949f24b206ddb6d083a5254b3aa70db
rwd    39990-TVA,A160-V90-V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26-0x13000-0x100000.rwd
       sha256 bc04a56f986455d15c02c0ded8aa40c0a290e950bcd7fe9ca50f746a414ecf37   (986,042 B)
```

Related: [[accord-anti-damping-is-not-the-pid]] · [[accord-six-levers-closed-on-arithmetic]] ·
[[accord-placebo-pair-is-mandatory-for-cross-build-claims]] ·
[[accord-v89-built-the-plant-model-friction]] · [[feedback-probe-the-gate-not-just-the-output]]
