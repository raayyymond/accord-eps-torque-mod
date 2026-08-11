---
name: reference-accord-gp4f50-is-a-rate-not-an-angle
description: SETTLES a standing conflict - gp-0x4f50 is a RATE (wrap-corrected first difference of a 16384-count electrical angle in FUN_00068f52), NOT an angle. The angle is gp-0x29c2. Gives the scale in closed form (333.333/f_tick ct per electrical deg/s) and two independent arguments that the tick is ~1 kHz.
metadata:
  type: reference
---

Settled 2026-08-10 by decompiling the producer chain, after ObserverMatch surfaced a direct conflict:
`gp-0x6abc` carries a **rate** scale (4.7121 ct/(deg/s) at the steering wheel) while
`reference_accord_state671a_is_oscillation_reversal_counter` read `gp-0x4f50` as most likely an **ANGLE**
(from `sin/cos` usage context, a reading that memory itself flagged as an inference, not a confirmation).
Since `gp-0x6abc` == `gp-0x4f50` identically
([[reference-accord-observer-filter-mismatch-leaks-the-command]]), both could not stand.

## The producer chain [EVIDENCE]

`gp-0x4f50` <- `gp-0x29c4` (1 writer / 1 reader; IRQ-guarded snapshot + shadow `gp-0x4484` in
`FUN_00068fbe`) <- **`FUN_00068f52`**, whose entire body is:

```c
uVar1 = u16(gp-0x29c2);                  // PREVIOUS raw angle
iVar2 = param_1 - uVar1;                 // FIRST DIFFERENCE
if (iVar2 >  0x2000) iVar2 -= 0x4000;    // *** WRAP CORRECTION, modulus 0x4000 ***
if (iVar2 < -0x2000) iVar2 += 0x4000;
iVar3 = (iVar2 * 120000) >> 14;          // scale
iVar2 = (s16(gp-0x4f4e) + iVar3) / 2;    // 2-point boxcar with the previous scaled diff
iVar2 = clamp(iVar2, -13000, +13000);
gp-0x29c2 = param_1;                     // save angle for next tick
gp-0x29c4 = iVar2;                       // -> gp-0x4f50
gp-0x4f4e = iVar3;
```

**You only wrap-correct the difference of a modular quantity.** The +-0x2000 correction on a 0x4000 span
is a textbook angular difference across a revolution.
⇒ **the ANGLE is `param_1` / `gp-0x29c2`; `gp-0x4f50` is its DERIVATIVE.** The prior memory conflated the
function's *input* with its *output*.

**Two corroborations an angle fails outright:**
- `FUN_00068fbe` plausibility-checks `|value|` against cals **`0xC491A` = 5500** and **`0xC491C` = 5000**,
  calling `FUN_0006d026(2,...)` on breach. A wrapping angle traverses its full range every revolution and
  would trip that continuously.
- `FUN_00041464` **EMAs** the value (`target = x*1024`, then a filter). EMA-ing a wrapping angle across
  the discontinuity is nonsense; EMA-ing a rate is routine.

**Why the sin/cos evidence was never discriminating:** `0.017453292` = pi/180 converts **deg OR deg/s** to
radians. `gp-0x4f50` @`0x70b4e` and `gp-0x4ee8` @`0x70b4a` are adjacent reads, so they are used together —
equally consistent with a rate feeding a rotating-frame transform.

## The scale, closed form [EVIDENCE for the formula]

Modulus **16384 counts / electrical revolution**; gain **120000 >> 14 = x7.32421875**:

```
gp-0x4f50 = boxcar2( dTheta * 7.324219 ), clamped +-13000
gp-0x4f50 per ELECTRICAL deg/s = 333.333 / f_tick_Hz
```

| f_tick | ct per elec deg/s | wheel->electrical ratio implied by the inherited 4.7121 ct/(deg/s) |
|---|---|---|
| 100 Hz | 3.3333 | 1.41 (not physical) |
| **1000 Hz** | **0.3333** | **14.14 — normal for a column-EPS motor-to-column reduction** |
| 2000 Hz | 0.1667 | 28.27 |

⊕ **Second, independent argument for the ~1 kHz tick:** the +-13000 clamp is `dTheta` = 1775 counts/tick =
**10.83% of an electrical revolution per tick** = **6500 elec RPM at 1 kHz** (a sane over-speed limit) but
only **650 at 100 Hz** (far too low for an EPS motor).
⇒ The inherited 4.7121 ct/(deg/s) is **corroborated**, and the tick is pinned at ~1 kHz. [BELIEF on the
exact ratio — the pole-pair/gear chain is not in the binary; this is a consistency check, not a derivation.]

## Why it was load-bearing

`0xC646E`'s identity as a **lagged velocity damper** (recorded in
[[reference-accord-observer-filter-mismatch-leaks-the-command]]) rests on the term's real part being
positive **with respect to `gp-0x6abc`**. With `gp-0x6abc` a RATE that reading stands. Had it been an
ANGLE, the identical phase result would have made it a **stiffness**, not a damper. The damper label is
therefore conditional on this file, and survives.

🛑 **`reference_accord_state671a_is_oscillation_reversal_counter`'s angle line is STALE** and should be
corrected at source (it belongs to ObserverMatch; flagged to them, not edited here). Suggested wording:
*"`gp-0x4f50` is a RATE — wrap-corrected first difference of a 16384-count electrical angle in
`FUN_00068f52`; the ANGLE is `gp-0x29c2`. The sin/cos context is non-discriminating."*
