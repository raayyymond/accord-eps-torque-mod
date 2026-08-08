---
name: accord-fun45608-authority-slots-not-motoroff
description: "FUN_00045608 is a generic authority-slot setter (3 parallel 7-slot arrays consumed by the G1 governor as a running MIN applied as a Q15 scale on the total command), NOT \"motor off\". Also — the governor DOES read vehicle speed, and its slot loop covers 0-5 not 0-3."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 999fba26-ffc6-4a2f-9832-a51b221c590a
  modified: 2026-07-25T07:32:51.351Z
---

# `FUN_00045608` is an authority-slot setter, not "motor off" (2026-07-25)

**Corrects CLAUDE.md**, which describes `FUN_00045608(3,0,0x8000,0x8000)` as "motor off" in the V25/V26
brick narrative. The *effect* is right; the *mechanism label* is wrong, and the wrong label hides what the
function actually is.

**What it really is:** a generic setter (guard `idx < 7`) writing three parallel 7-slot u16 arrays:
```
target   gp-0x652c + 2i      up-rate  gp-0x64fc + 2i      down-rate  gp-0x6514 + 2i
```
The **G1 governor `FUN_0004503c` consumes them** — `movea -0x652c, gp, r20` @`0x450C6` (op `0x31` = movea)
— rate-limiting each slot toward its target and accumulating a **running MIN** (`FUN_00049a78` = unsigned
MIN, seeded `0x8000`). That MIN is a **Q15 authority scale on the TOTAL command**:
```
gp-0x6ace = (clamp(gp-0x6b94 /* aggregator */) * MIN) >> 15
```
So `FUN_00045608(3, 0, 0x8000, 0x8000)` = *slot 3's target set to 0 with instant slew* ⇒ MIN → 0 ⇒ command
× 0. Any slot can do this: the CAN-commanded assist-shutdown path calls
`FUN_00045608(5, 0, 55, 164)` @`0x2D876` (cals `0xC6484`=0, `0xC6482`=55, `0xC6480`=164).

**⚠ The governor's slot loop covers slots 0-5, not 0-3.** `bVar3 = iVar20 != 1` is evaluated *after* the
do-while body (3 passes × 2 elements), then an unrolled block handles slot 6. Reading it as 2 passes is a
real trap — and slot 5 being processed is exactly why the shutdown path above is effective.

**★ The G1 governor DOES read vehicle speed** — `ld.hu gp-0x6a64` at `0x451E2` and `0x45308`, compared
against cal `0xC6316` = **640 ≈ 10 km/h**; `bc` at `0x45316` jumps to `0x45330` when speed is below that,
**skipping the slew-rate limiter**. Note the direction: below ~10 km/h the limiter is *bypassed* (more
responsive), so this is not a low-speed restriction.
**This falsifies the standing claim "there is NO vehicle-speed input anywhere in the command/base-assist
path"** (`reference-accord-governor-g1-total-command-not-thermal`, and that specific point in
`reference-accord-no-vehicle-speed-input-5mph-is-plant` — the latter's *empirical* content, band power vs
speed, is unaffected).

**Still open:** whether the governor's MIN chain can fall below unity at low speed. That matters because
`gp-0x69aa == 0x8000` ("no derate active", written `0x45342`) is a conjunct of the same AND-chain that
produces `STEER_STATUS=3`, so an on-car ST=3 cannot distinguish it from a speed-window failure. To settle
it, trace `r28` and the `FUN_00049a78` inputs at `0x45304` (`gp-0x694c`, `gp-0x6944`, `gp-0x6946`).

See [[accord-low-speed-lockout-window-c62ea]].
