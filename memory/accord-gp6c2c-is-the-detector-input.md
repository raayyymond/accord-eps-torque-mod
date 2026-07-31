# ★★ `gp-0x6c2c` is a MOTOR-RATE DERIVATIVE — the oscillation detector's only input

**Traced 2026-07-31** while deciding whether lowering `T` (cal `0xC620A` = 12800) could rescue the
detector-gated damping approach after V64's null. It is the **only** signal `FUN_000428d4`'s FSM tests
against `T`, and it is **not** what two independent passes assumed.

## The chain — `FUN_00041464` @`0x4184E`, cals byte-read LE

```python
K1 = 37     # cal 0xC643C, >>7        K2 = 22   # cal 0xC40DC, >>6
x      = s16(gp-0x4f50)                            # resolver/motor ELECTRICAL RATE
if abs(x) > 13000: gp_0x6c2c = 0x7fff; return      # 0x415be validity gate -> fault sentinel @0x41AC2
target = x * 1024                                  # 0x415d0  Q10
step   = ((target - old) * K1) >> 7 ; old += step   # 0x415e8  EMA #1 increment -- THE DIFFERENCE
acc    = clamp(step * 0x20, -0xfa0000, 0xfa0000)    # 0x41604  x32, clamp +-16,384,000
state += ((acc - state) * K2) >> 6                  # 0x41622  EMA #2
gp_0x6c2c = state >> 9                              # 0x4184e  range +-32,000; T = 40.0% of that
```

⇒ **It is an ACCELERATION.** The differencing stage kills DC, so **a sustained large steering input
cannot drive it** — it needs the motor rate actively reversing. Structurally consistent with an
oscillation detector, structurally inconsistent with "driver holds the wheel hard" as a trigger.
A slower sibling `gp-0x6c2e` takes the same `acc` through cal `0xC40DA` = 3 (`>>7`).

Live in the golden model as `eps_lkas_chain_model.detector_input_6c2c()`, which reproduces the threshold
exactly (amplitude 1683 trips, 1682 does not).

## Sizing — the detector is NOT blind to the ~21 Hz mode

Driving the integer chain with a 21.3 Hz sinusoid, tripping `T` needs `|gp-0x4f50|` ≈ **1683** counts
@1 kHz / **1821** @100 Hz — inside that signal's own **±13000 validity ceiling**, so the mechanism is
reachable in principle and route `35` was only **~1.7–2× short**, not 5× and not 30×.

Independently reproduced in the frequency domain by a different analyst and a different method:
`|1−H1|` = 0.43041 (differencing) × `|H2|` = 0.95375 ⇒ `gp_0x6c2c = 7.5965·U` ⇒ **U = 1685**. Agreement to
**four significant figures**. The `acc` clamp bites at U ≈ 4017, so `T` is reached at ~42% of saturation
and the response is genuinely linear there.

## 🛑 Three numbers that are VOID — do not carry them forward

All three came from assuming `gp-0x6c2c` shares the `0x18F` **torsion-bar torque** LSB. It is not
torque-derived at all:
- ~~"T ≈ 2048–2560" sizing band~~
- ~~"gp-0x6c2c's LSB is at most 3.29× finer than the bus torque LSB"~~
- ~~"if it is a per-tick rate ⇒ effectively dead, T would need to fall 30–90×"~~ — this one priced the
  chain at unity gain; the **`×1024` and `×32` pre-scales are invisible from the bus.**

⚠ **The bus can bound a signal's amplitude but not its scale.** Sizing a firmware threshold from a bus
channel requires proving the two share an LSB — and this firmware demonstrably rescales: the two
`STEER_ANGLE_RATE` copies differ by exactly **8.000×** in raw counts (corr 1.0000 across 16 segments).

## Why `T` is still not the lever

Viable on sizing, **rejected on blast radius**: `gp-0x671a` has four external consumers, one of them
using it as a *continuous LERP index* into the live P/I/D lane. See
[[accord-state671a-is-an-oscillation-detector]].

⚠ **Open:** `gp-0x4f50`'s physical units are untraced (needs the ISR writing `gp-0x29c4`, or a probe), so
1683 is in raw counts of a signal whose scale is unknown. A future detector probe should carry
`gp-0x6c2c` itself.
