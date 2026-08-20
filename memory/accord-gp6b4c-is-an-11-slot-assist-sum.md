---
name: accord-gp6b4c-is-an-11-slot-assist-sum
description: gp-0x6b4c is NOT the LKAS command - it is an 11-slot assist-channel SUM, which is why its sign agrees with openpilot's command at CHANCE
metadata:
  type: reference
---

🛑🛑 **`gp-0x6b4c` IS NOT THE LKAS COMMAND LANE. The kit's label on it is WRONG.**

**EVIDENCE — sole writer traced in `FUN_00026c80`** (decompile + byte read, 2026-08-20):
```python
# gp-0x6b4c = clamp(gp-0x3d88 + pol*((iVar13 * 0xC63CC) >> 10), ±0x2800)
#   0xC63CC = 0  ⇒  the rate-limiter term is nulled AFTER pooling  ⇒  gp-0x6b4c == gp-0x3d88
#
# gp-0x3d88 = Σ_{i=0..10} ( 0xC4118[i] != 0 ? slot_value(i) : 0 )      # 11 SLOTS
#
# mode byte = 0xC4124[i] = [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0]           # byte-verified on the V101 image
#   mode in (1,2,5,7) -> 0                                             # slots {2,4,5,9} FORCED ZERO
#   mode == 4         -> clamp((gp-0x633c[i] * 0xC646A) >> 14, ±0x2800)
#   else (0,3,6)      -> gp-0x62f8[i]                                  # slots {0,1,3,6,7,8,10} RAW PASSTHROUGH
#
# 0xC4118 = [1,1,1,1,1,1,1,1,1,1,1, 0]                                 # byte-verified: all admitted but the last
```
⇒ **`gp-0x6b4c` is the TOTAL ASSIST DEMAND — a sum of up to 7 live channel requests, of which LKAS
is ONE — and it is ALGEBRAICALLY FLAT at that stage** (no IIR, no EMA, no rate limit; the rate-limiter
block is the dead `0xC63CC` one).

**WHY IT MATTERS — the measurement that exposed it.** With openpilot's command **pinned at ±4096,
one-signed, for 19.4 s**, `sign(gp-0x6b4c)` agreed with `sign(command)` at **52.80 % against a chance
baseline of 54.36 % — AT CHANCE** — while flipping **8.2 /s versus the command's 0.31 /s**. A scaled,
low-passed or rate-limited copy would all agree ~100 %. The disagreement is the other ten slots.

**Consequences for reasoning that inherited the bad label:**
- A "no clamp binds on `gp-0x6b4c`" result is about **total assist demand**, not the LKAS lane.
- `0xC63AA` weights **this sum** — not the LKAS command — into `FUN_00038148`'s ACTUAL accumulator.
- 🛑 **Which slot is LKAS's, and whether the other mode-0 slots are live while engaged, is UNTRACED.**
  If a base-assist slot carries the 23 Hz ripple, the causal story changes. Next step:
  `get_xrefs_to gp-0x62f8`, then decompile its writers.
- ⚠ `0xC4118` is a **HARD NEVER-ARM** — zeroing a slot to route it into the limiter also removes it
  from the sum, and the limited path is ×0 ⇒ **LKAS steering silently dead while openpilot believes it
  is steering.** See [[accord-c4118-hard-never-arm]].

Related: [[accord-the-8x-gain-is-the-carrier]], [[reference-accord-lkas-only-rate-limiter-c6194]].
