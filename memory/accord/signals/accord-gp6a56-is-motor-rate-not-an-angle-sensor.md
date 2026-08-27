---
name: accord-gp6a56-is-motor-rate-not-an-angle-sensor
description: "🛑★★ gp-0x6a56 — what the EPS transmits as STEER_ANGLE_RATE on 0x14A[2:4]/0x18F[2:4] — is NOT independently sensed. FUN_0003f776 synthesizes it as a fixed Q15 scale of gp-0x6abe, the MOTOR resolver electrical rate. Kills 'the only control-path signal with an external anchor' and leaves gp-0x6bbe's damping sign unresolved."
metadata:
  type: reference
---

# 🛑★★ `gp-0x6a56` is synthesized MOTOR rate, not a steering-angle sensor

`FUN_0003f776` is the **sole producer** (4 `st.h` on `6a56`, all inside it, `truncated:false`), called
from `FUN_00022ca0` @`0x22de2` before `FUN_00034a72`/`FUN_00035154` each tick:

```python
# mirrors the decompiled arithmetic; V850 is LITTLE-ENDIAN, byte-read every constant LE
iVar4     = polarity(gp_0x6752) * ((gp_0x6abe * 48 * cal_tp_0x713a) >> 15)   # Q15 scale of MOTOR rate
gp_0x6a56 = max(-12000, min(12000, iVar4))     # MAGNITUDE clamp, recomputed fresh EVERY tick
gp_0x6a60 = min(abs(gp_0x6a56), 65535)         # 0x3f7f6-0x3f800; the min never binds -> dead safety net
```

- The **±12000 is a magnitude clamp, not a rate/slew limit** — there is no cross-tick delta anywhere in
  this chain.
- `gp-0x6a60` merely **mirrors `gp-0x6a56`'s magnitude**; it is not a second clamp. It IS a live consumer
  signal (decider RATE_GATE `0xC6310` = 1600, only 13% of the 12000 ceiling).

## Why this matters — two conclusions it damages

1. 🛑 **`STEER_ANGLE_RATE` is opendbc-named but is NOT an independent angle sensor.** The recorded framing
   "the only control-path signal in this firmware with an external anchor" is wrong in substance. So
   *"the mode measures 996× on `STEER_ANGLE_RATE` vs 877× on the torsion bar"* is **two EPS-internal
   derivations**, not independent corroboration of a physical mode.
2. 🛑 **`gp-0x6bbe`'s damping sign is UNRESOLVED.** `rate_error = baseline − angle_rate_raw`
   (`sub r6,r28` @`0x34e96`) looked like clean viscous damping once `baseline` was shown to read no
   angle rate. But `baseline`'s Branch A input is **also `gp-0x6abe`-derived** (via `FUN_0003b66a`), so
   the two sides are **correlated copies of the same root signal through different pipelines** and may
   partially cancel. Static analysis flipped four times on this; **V58 measures the phase on-car
   instead** — see [[accord-v58-boostlane-probe-built]].

## Provenance of the flip-flop, so it is not re-litigated

(a) "net damping" off the torque-EMA framing → (b) "unresolved, `baseline` isn't slow" (that pass wrongly
attributed `a = 102/1024` to `baseline`; it is Y1's blend into `gp-0x69bc`) → (c) "damping, `baseline`
reads no angle rate" → (d) **unresolved**, this memory. The golden model cannot settle it:
`base_driver_assist_lane` is flagged `[SIMPLIFIED]` at exactly that point and the angle-rate tributary is
absent from it entirely.

Related: [[accord-angle-rate-lane-gp6bbe-top-candidate]],
[[accord-ratchet-and-grinding-are-two-symptoms]], [[accord-v58-boostlane-probe-built]]
