---
name: accord-ram-lerp-is-flash-derived-and-fprime-nonneg
description: The FUN_00038148 "RAM-resident" LERP is 100% flash-derived (speed-blended, mode-selected) and its slope f' is >= 0 ENFORCED IN CODE at three ungated sites — so it can never invert a signal; plus the measured phase of its output gp-0x6b70.
metadata:
  type: reference
---

**`STATE.md` §A6b's claim that the LERP transfer "cannot be read from the image" is FALSE.** It can,
and better: the non-negative slope does not even depend on the cal values.

## Provenance — flash, not runtime state (EVIDENCE, GhidraMCP on `code.bin`)
`FUN_000382d8` @`0x382d8` is the **sole writer** of both source arrays; only caller `FUN_00022ca0`.
```
mode = byte at gp+0x63fd                                        0x382e0
brk  = *(int*)(0xCC9FC + mode*4)             7 speed breakpoints: 0/15/40/80/120/160/200 km/h
recs = *(int*)(B + mode*4), B in {0xC7B40 0xC7C28 0xC7D10 0xC7DF8 0xC7EE0 0xC7FC8 0xC80B0}
record: +0x00 count(9), +0x02..+0x12 nine X shorts, +0x14..+0x24 nine Y shorts
writes gp-0x6350[0..8] = Xsrc  @0x38880/0x388aa    gp-0x630c[0..8] = Ysrc  @0x3884c/0x38886/0x388b0
```
`FUN_000389ec` @`0x389ec` rescales into `gp-0x64b8[]` (X) / `gp-0x641c[]` (Y) — stores `0x39522`,
`0x39548`, copy loop `0x395d4`. `FUN_00038148` @`0x38148` reads exactly `gp-0x64b8..gp-0x64a6` and
`gp-0x641c..gp-0x640a`. Both ends verified: same 10-point table.
Nominal `K1 = K2 = 1024` (`FUN_0003897a` slews to `clamp(gp-0x6982 or 1024, 204, 2048)`, bounds
`0xC6392`/`0xC639C`) ⇒ **the built table equals the flash record.**

## f' >= 0 is ENFORCED IN CODE — holds for ANY cal, mode, speed, build
```
FUN_000382d8 0x388c4+   EIGHT consecutive UNCONDITIONAL rungs  Ysrc[i] = max(Ysrc[i], Ysrc[i-1])
FUN_000382d8 interp     if (i != 0 && y < prev) y = prev                  (float path)
FUN_000389ec 0x38de2 / 0x38e48   Y[i] = max(Y[i], Y[i-1])   (both branches)
FUN_000389ec 0x38e9c / 0x38ea2   Y[i] = min(Y[i], cal 0xC6200 = 8192)
FUN_000389ec 0x38d1c / 0x38d22   X[0] = 0, Y[0] = 0   (hard-stored zeros — confirms [[accord-ram-lerp-y0-zero-corrects-v86-relay-claim]])
```
Flash data agrees with margin: **14/14 records (7 speeds x 2 modes) X and Y strictly increasing.**
15 km/h record: X `0 150 300 618 1200 1800 3000 5000 10000 14490`, Y `0 429 788 1350 2029 2358
2763 3297 4625 8192`, **f' per segment `2.860 2.393 1.767 1.167 0.548 0.338 0.267 0.266 0.794`** —
a saturating assist curve, ~10x steeper near zero. Hands-off (driver torque ~0) ⇒ **f' ~ 2.86.**

⇒ **The LERP is a MEMORYLESS, SIGN-PRESERVING, gain-varying element. It cannot invert a signal at
any frequency.** `gp-0x6b70 = sign(iVar6)*LERP(|iVar6|)` with `LERP(0)=0` is odd and monotone.

🛑 **This closes the OPEN-loop sign only.** The closed loop still needs `arg L` — see
[[reference_accord_path2_bracket_criterion_closes_openloop_not_closedloop]] (`B = 1 + Q`).

## Closed-form sign, and the ONE residual bit
`0xC64B0` = **1** (Path 2 live, unity into `gp-0x6ad6`); `FUN_00037fe6` speed-gain table **1024 flat**.
```
d(assist)/dW_i = + f' * polarity * 2.577 * |H_IIR| * lane_i / 1024      Path-2 gain = polarity x 6.71 @7.79 Hz
```
Only `sign(polarity * lane_i)` is free. **`gp-0x6752` is a +-1 CONFIG CONSTANT, never 0, does NOT
track steering direction** — writers `0x48e68`, `0x48e88`, `0x490c0`, `0x49838`, `0x49844`;
`FUN_000497e6`: `if (*(char*)(*(int*)(gp-0x34b8)+4) == 0x2C) = +1 else = -1`. Sourced from an
EEPROM/RAM config record ⇒ **NOT in the flash image.** ⊕ Consequence: Path 2 is **not** muted
hands-off; all six weights are live in the symptom regime.

## MEASURED: gp-0x6b70 is ~acceleration-proportional and WEAKLY ANTI-DAMPING
V86 probe b7 (`sign(gp-0x6b70)`) vs wheel rate, route 6f, Welch, contiguous segments:
```
ENGAGED all speeds  n=14115  phase(6-9Hz) = -100.4 deg  coh^2 = 0.507
ENGAGED 6-20 km/h   n=10851  phase(6-9Hz) = -104.4 deg  coh^2 = 0.460
MANUAL  coh^2 = 0.002 | CONTROL rate-reversed 0.003 | CONTROL sign-shuffled 0.002
```
🛑 **SIGN CORRECTED 2026-08-12.** These were first reported as **+100.4/+104.4** — wrong sign.
**`scipy.signal.csd(x,y)` returns `arg(Y) − arg(X)`, NOT `arg(X) − arg(Y)`** (verified on a
synthetic 45° lag). Caught only because an independent measurement (`fw-loop`/lead's `Q`) disagreed
by a replicated **~90°**; after correction the two pipelines agree to **2.9°/6.8°** on routes 7e/7f.
**Check any cross-spectral phase against a synthetic known-lag pair before trusting its sign.**
⚠ The ANTI-DAMPING conclusion is UNAFFECTED — `cos` is even, so the dissipative projection
`cos(-100.4°) = cos(+100.4°)` is unchanged. Only *direction-of-fix* claims were affected: the
corrected sign says **raising `0xC63AC` REDUCES the anti-damping** (lowering it makes things worse).

|90 deg| = pure acceleration ⇒ **dominated by apparent INERTIA** (echoes
[[accord-gp6b26-is-inertia-not-damping]] at aggregate level). Dissipative projection
`cos(100.4°) = -0.181`; with `assist ∝ -gp-0x6b70` that is **assist pushing WITH the motion —
weakly ANTI-DAMPING at 6-9 Hz**, consistent with the corpus `Re(Z) < 0` on three drives.
🛑 EVIDENCE for the **aggregate** only — does not decompose into which input drives it, so it does
NOT give the sign for any single weight.

## Traps hit
- `search_instructions operand_pattern="-0x6350\[gp\]"` returned **0 / 183,570 / `truncated:false`**
  on an array with nine real accesses — they are `movea -0x6350,gp,r11` + register-indirect
  `ld.h -0x6350,r15,r13`. Search the **bare** `0x6350`.
- Mode 24 != mode 26 in **this** family (rec[0],[3],[4],[5] + breakpoints differ);
  [[accord-stock-mode24-equals-mode26-damper-is-ours]] is scoped to the *damper* families.
  ⊕ rec[1]/rec[2] ARE identical ⇒ in the 6-20 km/h regime mode choice barely moves this curve.

Scripts: `analysis-2020accord/sessions/v97/read_ram_lerp_provenance.py`, write-up `sessions/v97/close_the_sign.md`.
