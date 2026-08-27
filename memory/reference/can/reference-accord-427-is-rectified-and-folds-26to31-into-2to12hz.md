---
name: reference-accord-427-is-rectified-and-folds-26to31-into-2to12hz
description: "CAN 427 transmits a MAGNITUDE, so aliasing runs on 2f, not f — and the fold law is |2f - 50*round(2f/50)|, not f mod 25. The kit used the wrong law twice in one session. Real exposed band on a 427-carried probe is 2-12 Hz."
metadata:
  type: reference
---

# 🛑 CAN 427 IS RECTIFIED — ALIASING RUNS ON `2f`, AND THE FOLD LAW IS NOT `mod 25`

Established 2026-08-12 while sizing a 427-carried telemetry probe. **Two wrong versions of this were
used in the same session before it was pinned**, so it is written down.

## THE LAW [EVIDENCE — derived, then checked against the flown 427 series]

427 carries `|x|`, a **magnitude**. Rectification doubles the fundamental, so a physical line at `f`
appears on the wire at `2f` *before* sampling. The sampler then folds it:

```python
def alias(f, fs=100.0):          # 427 is on the 100 Hz CAN-TX base tick
    g = 2.0 * f                  # RECTIFIED  -> the wire carries 2f, not f
    return abs(g - fs/2 * round(g / (fs/2)))   # fold about Nyquist/2 = 25 Hz
```

🛑 **It is `|2f − 50·round(2f/50)|`.** It is **NOT** `f mod 25`, and it is **NOT** applied to `f`.
Both of those were used in this kit's own analysis and both give wrong answers.

| physical line | `2f` | aliased to |
|---|---|---|
| 26 Hz | 52 | **2 Hz** |
| 29 Hz | 58 | **8 Hz** |
| 31 Hz | 62 | **12 Hz** |

## THE CONSEQUENCE

**The band a 427-carried magnitude probe actually exposes is 2–12 Hz** — the fold image of the
26–31 Hz grinding band — **not 19–24 Hz.** Any probe sized or scored on a 19–24 Hz expectation was
sized against a band that cannot appear there.

⊕ Corollary: a 2–12 Hz feature seen on a 427 channel is **ambiguous** — it may be a genuine 2–12 Hz
line, or the fold image of a 26–31 Hz one. **A 427 probe cannot distinguish them.** If the
distinction matters, carry a **signed** value (which is not rectified, so aliasing runs on `f`) or
put the signal on a spare-bit channel instead. This is why the V95 four-lane instrument spec calls
for signed-427 plus an explicit sign bit.

## HOW TO APPLY
- Before quoting any frequency read off a 427-derived series, state whether the packer emits a
  **magnitude** or a **signed** value, and apply the matching law.
- Cross-check any 427 line against the same physical quantity on a non-rectified channel before
  attributing it to a mechanism.

## REPRODUCE
`rlog-tools/studies/v95-override/v95_427_aliasing_and_cadence.py`

Links: [[accord-can-tx-100hz-base-tick-and-gateway]] · [[reference-accord-gp6bbe-is-rate-derived-not-base-assist]] ·
[[accord-can-tx-gateway-whitelist-and-20-free-bits]] · [[accord-v94-flew-and-the-lane-is-a-damper]] ·
[[feedback-a-count-is-not-a-physical-fact]]
