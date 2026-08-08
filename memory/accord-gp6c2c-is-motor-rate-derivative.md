---
name: accord-gp6c2c-is-motor-rate-derivative
description: "gp-0x6c2c (the oscillation detector's input) is a motor-rate DERIVATIVE off gp-0x4f50, not torque and not a raw per-tick difference; tripping T=12800 needs ~1683 counts at 21.3 Hz."
metadata: 
  node_type: memory
  type: reference
  originSessionId: bc782257-b6f6-4f50-b561-9f5907a74209
  modified: 2026-07-31T22:46:07.852Z
---

`gp-0x6c2c` is what `FUN_000428d4`'s FSM compares against `T` = cal `0xC620A` = 12800. It is produced in
`FUN_00041464` @`0x4184E`. Traced and byte-verified 2026-07-31 (cals 37 / 22 / 3 read LE):

```python
K1 = 37     # cal 0xC643C, >>7      K2 = 22   # cal 0xC40DC, >>6
x      = s16(gp-0x4f50)                            # resolver/motor ELECTRICAL RATE
if abs(x) > 13000: gp_0x6c2c = 0x7fff; return      # validity ceiling -> fault sentinel
target = x * 1024
step   = ((target - old) * K1) >> 7 ; old += step   # EMA #1 increment -- THE DIFFERENCE
acc    = clamp(step * 0x20, -0xfa0000, 0xfa0000)    # x32, clamp +-16,384,000
state += ((acc - state) * K2) >> 6                  # EMA #2
gp_0x6c2c = state >> 9                              # range +-32,000; T = 40.0% of that
```

⇒ **It is an ACCELERATION** — differencing kills DC, so a sustained large steering input cannot drive it.
A sibling `gp-0x6c2e` takes the same `acc` through a slower EMA (cal `0xC40DA` = 3, `>>7`).

**Sizing:** driving the integer chain with a 21.3 Hz sinusoid, tripping T needs `|gp-0x4f50|` ≈ **1683**
counts @1 kHz / **1821** @100 Hz — inside that signal's own ±13000 validity ceiling, so the detector is
**not** structurally blind to the mode. Independently reproduced in the frequency domain
(`|1-H1|`=0.43041 × `|H2|`=0.95375 ⇒ `gp_0x6c2c = 7.5965·U` ⇒ U = **1685**) — 4 significant figures by a
different method. The `acc` clamp bites at U ≈ 4017, so T is reached at ~42% of saturation and the
response is linear there.

🛑 **Do NOT size T from bus torque.** An earlier pass derived a "T ≈ 2048–2560" band and a "LSB ≤3.29×
finer" bound from the `0x18F` torque channel; both are **VOID** — `gp-0x6c2c` is not torque-derived and
does not share that LSB. Also void: a "per-tick rate ⇒ effectively dead" reading that priced the chain at
unity gain and missed the `×1024` and `×32` pre-scales, which are invisible from the bus.

⚠ `gp-0x4f50`'s physical units are still untraced (needs the ISR writing `gp-0x29c4`, or a probe), so the
1683 figure is in raw counts of a signal whose scale is unknown. See [[accord-v64-null-is-on-the-gate]]
and [[accord-gp671a-blast-radius-not-a-free-lever]].
