---
name: accord-stock-mode24-equals-mode26-damper-is-ours
description: Honda ships mode 24 (manual) and mode 26 (engaged) byte-identical for all six factor families; the entire engaged-only damper is our own edit, introduced at V74.
metadata:
  type: reference
---

★★★★★ **In STOCK firmware, mode 24 and mode 26 are BYTE-IDENTICAL for all six factor families.**
Honda does **not** change the assist or damper surface when LKAS engages. **Every engaged-vs-manual
asymmetry on this car is one we created, and it did not exist before V74.**

**[EVIDENCE]** Orchestrator's own Python LE read, 2026-08-08, of `stock_fw_dump/code.bin` and all 76
`_v*_plain_image.bin`, dereferencing each pointer array at `arr + mode*4`, record layout
`[u16 n][n·i16 X][n·i16 Y][u16 term]`, **X at base+2**. Independently reproduced by a Ghidra tracer that
pinned the pointer-array addresses from `FUN_00034a72` / `FUN_0003ad74` decompiles and then re-read the
bytes.

## Stock: distinct value-sets across all 34 modes

| family | ptr array | distinct sets / 34 modes | note |
|---|---|---|---|
| FactorB | `0xC9CCC` | 2 | both flat `Y=[1024]×4` ⇒ **inert everywhere** |
| FactorC | `0xC9E9C` | 13 | 🛑 **`Y[0] == 0` in ALL THIRTEEN.** m{12,14,24,26} share `X=[2240,3840,5120,8960] Y=[0,234,429,908]` |
| FactorD | `0xC9DB4` | 2 | both flat `Y=[1024]×5` ⇒ **inert everywhere**, n=5 |
| FactorE | `0xC9F84` | 4 | m{10..15,22..27} share `X=[60,400,2500,4000] Y=[0,140,539,927]` |
| ceiling | `0xC77A0` | **1** | `X=[300,800] Y=[512,1024]`, all 34 modes |
| friction | `0xCBE74` | **1** | `X=[0,1280,5760] Y=[-9830,-5734,-1966]`, all 34 modes |

Also byte-identical m24 vs m26 in stock **and** in V81: r24 gain_B arrays
`0xCBF5C`/`0xCC044`/`0xCC12C`/`0xCC214`, boost curve `0xCA154`, boost amp `0xCA4F4`/`0xCA23C`, boost
ceiling `0xC7970`, boost scalars `0xCA324`/`0xCA40C`/`0xCA06C`/`0xC7A58`.
⇒ **The FactorC/E damper dose is the ONLY mode-26-vs-24 asymmetry that exists in V81.**

## When it was introduced — mode-26 FactorC `Y[0]`, across the whole lineage

**V22 → V73 are ALL byte-stock** (`Y[0] = 0`). First armed at **V74** (429), then V75/V76/V78/V79/V80/V81
(566). See [[accord-v81-carries-neither-grind1-fix]].

| build | m26 FactorC Y | m26 FactorE X | m26 FactorE Y |
|---|---|---|---|
| STOCK … V73 | `[0,234,429,908]` | `[60,400,2500,4000]` | `[0,140,539,927]` |
| V74 | `[429,…]` | `[12,400,…]` | `[0,539,539,927]` |
| **V75 / V81** | `[566,234,429,908]` | `[12,200,2500,4000]` | `[0,539,539,927]` |
| V80 | `[566,566,566,566]` | `[0,119,2500,4000]` | `[0,897,912,927]` |

## Why it matters — it explains "heavier when engaged"

The damper's sign is **`−sign(motor rate)`**, not `−sign(LKAS error)`. It cannot tell the driver's hand
from the LKAS motor, so it opposes the driver **even when the driver turns WITH the command** — the
operator's exact report on V81/route 67. Below 35 km/h Honda has **zero** damping and we have the full
dose. Dose `= min((FactorC_LERP(speed) × FactorE_LERP(rate)) >> 10, ceiling)`; FactorC axis is voted speed
`gp-0x6a5e` at **64 counts/km/h** ⇒ `X=[2240,3840,5120,8960]` = **35 / 60 / 80 / 140 km/h**;
FactorE axis is motor rate at **4.7121 counts per °/s**.

| | rate ct 20 | 50 | 100 | 200 | 300 | 1000 |
|---|---|---|---|---|---|---|
| | °/s 4 | 11 | 21 | 42 | 64 | 212 |
| 20 km/h m24 MANUAL | 0 | 0 | 0 | 0 | 0 | 0 |
| 20 km/h m26 ENGAGED V81 | 12 | 59 | 139 | 297 | 297 | 297 |
| 100 km/h m24 MANUAL | 0 | 0 | 9 | 32 | 56 | 145 |
| 100 km/h m26 ENGAGED V81 | 12 | 62 | 144 | 309 | 309 | 309 |

## 🛑 Honda's damper is VISCOUS; ours is a RELAY — at every speed, without ever saturating

Describing function `N(R)` (fundamental-harmonic gain of `−sign(rate)·M(|rate|)`; **N rising as R falls =
relay = limit-cycle generator**):

| 100 km/h, R (ct) | 25 | 50 | 100 | 200 | 500 | 1000 | `N(50)/N(500)` |
|---|---|---|---|---|---|---|---|
| m24 Honda | 0.000 | 0.000 | 0.060 | 0.142 | 0.185 | 0.153 | **0.00×** stabilising |
| m26 V81 (=V75) | 0.605 | 1.107 | 1.374 | 1.510 | 0.764 | 0.391 | **1.45×** relay |
| m26 V80 | 4.007 | 4.087 | 4.129 | 2.951 | 1.250 | 0.632 | 3.27× |

`N(200)` for m26 rises with speed: **0.60 @60 km/h → 1.51 @100 → 2.13 @130.** The relay comes from
FactorE's **plateau** (`Y=[0,539,539,927]` is flat from `X`=200 to 2500 ⇒ constant force whose sign flips
with rate = Coulomb). Honda's `Y=[0,140,539,927]` over `X=[60,400,2500,4000]` is a genuine ramp.
🛑 **Saturation is NOT required for relay behaviour** — on route 67 the damper's `≥448` level fired
**0.000%** of 67,127 engaged frames and the relay index is still 1.45×. The V80 lesson generalises:
*"does not clip" and "is not a relay" are different statements.* See [[accord-v80-damper-relay-and-grind1-inert]].

## Confirmed: mode 26 really is the engaged column

**[EVIDENCE]** two independent methods. (1) V73's `gp+0x63fd` probe over 104,061 frames → 8 manual /
10 engaged, disambiguated through table `0xCD000` to 24/26 — [[reference-accord-car-is-tvca4-mode-24-26]].
(2) Fresh decompile of **`FUN_00042746`**: `gp-0x67f6` (0/1) selects the disengaged pair vs the engaged
pair; the switch fires on a **`gp-0x6806` (= `latActive`) edge** with `gp-0x69b0` at a sentinel, and is
**debounced** by counter `gp-0x4f68` against cal `tp+0x7180` — matching the measured ~1 s engage /
~2 s disengage lag.

## Ruled out this session as engagement-conditional paths

`gp-0x67f4` = a 5-channel **vehicle-speed voter plausibility flag** (`FUN_00041eec`), zero engagement
reference ⇒ **the long-open "never probed" item is CLOSED, negative**. `gp-0x67fe` = EPS assist substate
(`FUN_0003bd7c`). `FUN_00036682` = torque-domain hysteresis + ~0.93 Hz IIR, no mode reference.
`0xC63A0` = 2048 on V81 is real but a bare `tp` scalar, **mode-proof** ⇒ symmetric, cannot explain the
asymmetry.
