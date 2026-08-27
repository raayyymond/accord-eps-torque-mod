---
name: accord-lateral-engagement-signals
description: The three lateral-engagement proxies and where 0xE4 STEER_TORQUE_REQUEST actually lives; cruiseState.enabled is long+lat and must never be used.
metadata: 
  node_type: memory
  type: reference
  originSessionId: a179e27a-7fe7-49ee-b2a8-e84c074404f9
  modified: 2026-07-30T02:43:21.111Z
---

`carState.cruiseState.enabled` is **longitudinal + lateral**. For any EPS/LKAS analysis it is the
wrong conditioner and must not be labelled "engaged" — call it "long+lat". On route 28 it reads 84.0%
while LKAS is actually applying 49.9%; on route 1c (V55) it is **0% for the whole route** while
lateral is active 21.2%.

The three lateral proxies, and their measured agreement (2026-07-29):

| proxy | where | route 28 | route 24 | route 1c |
|---|---|---|---|---|
| `carControl.latActive` | cereal | 14,964 (49.89%) | 73,092 (77.45%) | 2,358 (21.19%) |
| `STEER_CONTROL_ACTIVE` | CAN `0x18F` byte4 **bit3**, src 1 | 14,962 (49.88%) | 73,068 (77.43%) | 2,358 (21.19%) |
| `STEER_TORQUE_REQUEST` | `0xE4` **byte2 bit7** | 14,948 (49.87%) | — | 2,357 (22.52%) |

Pairwise agreement **99.94-100.00%**. Any of the three works; they are interchangeable.

🛑 **`0xE4` is in the `sendcan` event on src 1 at ~100 Hz — NOT `can` src 0.** In `can` it appears
only as the TX echo (src `0x80`) and as the blocked stock-camera copy (src 2). Looking on `can` src 0
yields **zero frames on route 28** and 762 frames at 0.8 Hz on route 24 — a silent null that
"agrees" with anything. Identify the request bit empirically (`|STEER_TORQUE|` is 0 whenever the bit
is clear) rather than from a DBC start-bit.

Route 1c's 2,357-2,358 lateral frames match the recorded V55 baseline's "998 + 1359 = 2,357 samples",
so **the V55 figures in the record were already computed on lateral engagement** and are like-for-like
with lateral-conditioned work. Also note `STEER_STATUS` is `0x18F` byte4 **bits 7:4**, not bits 2:0
(bits 2:0 are constant 7 there).
