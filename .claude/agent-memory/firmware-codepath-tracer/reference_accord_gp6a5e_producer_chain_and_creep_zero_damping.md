---
name: accord-gp6a5e-producer-chain-and-creep-zero-damping
description: SETTLED with bytes — gp-0x6a5e/62/64 are voted VEHICLE SPEED; full producer chain FUN_00053216 -> FUN_000534da -> FUN_00041eec proven, and damper FactorC is arithmetically ZERO below 35 km/h in all 12 modes
metadata:
  type: reference
---

Closes the two-identities contradiction between the golden model (which called
`gp-0x6a5e` the AVG driver-column-torque voter) and `docs/BUILD-LINEAGE.md` (which called it
voted vehicle speed). **BUILD-LINEAGE was right.** Extends [[accord-gp6a5e-is-voted-vehicle-speed]]
with the producer chain, which prior work had not walked.

## Producer chain (all VERIFIED, stock `code.bin`)

`FUN_00053216` @0x53216 — per-corner wheel-speed decoder. Takes a corner index 0..3, pulls a
byte pair from the CAN buffer at `gp-0x13e0` via four distinct extractors
(`FUN_00021646/21622/2169e/21672`), scales `(raw * 0x29) >> 6`, returns `0x7fff` on fault and
sets a per-wheel bit in `gp-0x3300`.

`FUN_000534da` @0x534da — calls `FUN_00053216(1/0/3/2)` and writes the four corners to
`gp-0x6a44 / gp-0x6a40 / gp-0x6a3c / gp-0x6a38`. Limp-home path writes `(byte)gp-0x6753 << 6`
to **all four at once**.

`FUN_000522fe` @0x522fe — writes the CAN vehicle-speed reference `gp-0x6a46`, same `*41>>6`
scaling (`FUN_00021706` reads the raw 0.01 km/h pair at `gp-0x140c/140b`), same `(byte)gp-0x6753 << 6`
limp-home, invalid sentinel `0x7fff`.

`FUN_00041eec` @0x41eec — **the voter**. Reads exactly those five cells (four wheels +
`gp-0x6a46`), NOT `gp-0x4e8c/8a/88`. Writes the only stores image-wide:
`gp-0x6a5e` @0x42342 (1 writer), `gp-0x6a62` @0x42312/0x4231c (2), `gp-0x6a64` @0x42360 (1).

Scale is therefore **64.0625 counts/km/h** on every input and every output.

## Why it cannot be torque

- Output is **slew-rate limited**: up-step LERP Y=(16,14,11,8,5) @0xC6864, down-step flat 27
  @0xC684C, on a 32000-count full scale — a 2-20 s full-scale transit. Impossible for driver
  torque, textbook for a speed estimate.
- Validity window is `value+6400 unsigned< 38401` i.e. **[-6400, +32000]** — asymmetric, and
  precisely engineered to reject the `0x7fff` invalid sentinel the decoders emit.
- Invalid-speed fallback `tp+0x7314` = **0xC6314 = 5120 = 79.9 km/h**. A "assume 80 km/h"
  failsafe is meaningless as a torque.
- `FUN_0004d0d0` @0x4d140 sets the standstill-bypass `gp-0x68b3` only when `gp-0x6a62 == 0`.

## The three outputs are NOT AVG/MAX of one vote

- `gp-0x6a5e` = the vote (average when >=2 channels agree within a speed-scaled spread limit,
  else the channel closest to the previous accepted value), then slew-limited. **The primary axis.**
- `gp-0x6a62` = a separately bounded variant; **`0xFFFF` when the CAN reference channel is
  invalid or too few wheels are valid**, which deliberately fails every `< 0x7d01` consumer guard.
- `gp-0x6a64` = a second slew-limited variant, step `tp+0x74ee`=27, floored at `tp+0x731a`=640.

## Consumer re-key (index-load addresses)

| consumer | axis | index load |
|---|---|---|
| boost curve `PTR_LAB_000ca154[mode]` (mode10 = 0xD2834) | **speed** `gp-0x6a5e` | 0x034ecc |
| ceiling `PTR_DAT_000c7970[mode]` (flat 512, all 12 modes) | **speed** `gp-0x6a62` | 0x035004 |
| damper FactorC `0xc9e9c[mode]` (mode10 = 0xD27BC) | **speed** `gp-0x6a5e` | 0x0344e0 |
| `FUN_0003ad74` r24/r26 cross-interp, breakpoints tp+0x7010 = **0xC6010** = (0,640,3200,6400) | **speed** `gp-0x6a5e` | 0x03ad7e |
| `FUN_00040d58` "decider dec_torque_max" vs cal 0xC6312=320 | **speed** `gp-0x6a62`, 3 compares | 0x040dae/dc6/dea |
| `FUN_0004503c` governor vs cal 0xC6316=640 | **speed** `gp-0x6a64` | 0x0451e2, 0x045308 |
| `0xca4f4` / `0xca23c` / FactorB `0xc9ccc` | **torque** (`gp-0x4f60` EMA -> `gp-0x6bba`/`gp-0x6bcc`) | — |

`0x034d06` is a **gate** (`gp-0x6a5e < 0x7d01`), not an index. The real torque axis was never
missing — it already keys three surfaces; the error was giving `gp-0x6a5e`'s job to torque.

## 🛑 The load-bearing consequence

Damper **FactorC Y[0] = 0** and the LERP clamps to Y0 below X0. X0 is 1280-2240 counts
(20-35 km/h) depending on mode; mode 10 = 2240 = **35.0 km/h**. FactorC is a *multiplicative*
term in `FUN_00034350`'s damping product, so:

**the base-assist damping lane is EXACTLY zero below 35 km/h, in all 12 modes** — 0 at 5 km/h,
0 at 18 km/h, first nonzero (9/1024) at 36 km/h.

This means every "hands-off deadzone" claim keyed on the 2240 breakpoint is really a
**LOW-SPEED deadzone**, and V44/V47's "marginally quieter at 5 mph" was a partial hit judged
against the wrong regime. Relevant to the creep-only ~20.9 Hz grinding.
See [[accord-check-build-lineage-before-proposing-lever]] before acting on this.
