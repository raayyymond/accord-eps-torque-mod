---
name: reference_accord_0x28f4c_rate_operand_hook_runs_every_tick
description: 0x28F4C (ld.h -0x6a56,gp,r7, bytes 24 3f aa 95) is the LKAS rate PID's own and ONLY read of the rate operand, sits ABOVE the engagement guard so it runs on EVERY tick (engaged and disengaged -- no freeze, no gp-0x6cf8 seeding), has 11 free scratch registers and no PSW hazard, and Q14 coefficients fit int32 there at x1.405 with no pre-shift. Its one hazard: Honda's +-12000 plausibility BAIL at 0x28F50 tests r7, so a cave substituting a notched value MUST clamp to +-12000 or it will spuriously trip the bail. All 25 image-wide reads of gp-0x6a56 are ld.h (signed) -- "the only signed read" is FALSE.
metadata:
  type: reference
---

# `0x28F4C` — the rate-operand hook: runs every tick, 11 free registers, one mandatory clamp

2026-09-09, subagent `fbhook`. GhidraMCP `disassemble_bytes dry_run:true` + raw-Python LE scans.
Trace: `docs/traces/TRACE-2026-09-09-v290-feedback-operand-hook.md` (ADDENDUM).

## Census, both methods, set-differenced

`gp-0x6a56`: **25 readers, 4 writers.** Ghidra `operand_pattern:"0x6a56, gp"` returns 25 (21 ld.h +
4 st.h) with zero digit-coincidence false positives — the tighter pattern is worth using instead of
`"6a56"`. The raw scan returns 29 and finds **4 readers Ghidra misses**: `0x2D9BE`, `0x4F942`,
`0x4F964`, `0x5150E`. All 4 writers are `st.h` in the producer `FUN_0003F776`; 2 of the 25 reads are
self-reads there, leaving **23 external reads across 17 functions**. 🛑 **Never write the cell.**

⚠ **All 25 reads are `ld.h` (SIGNED). There is no `ld.hu` on this cell** — "0x28F4C is the only signed
read" is FALSE; what distinguishes it is that it is the only access inside `FUN_00028ea6`.

## Why this site beats `0x29D72`

`0x28F4C` is **below** the engagement guard `0x29A48`-`0x29A70`, whose three skip jumps
(`0x29A5C`/`0x29A64` → `0x2A164`, `0x29A70` → `0x2A0C6`; complete by `get_xrefs_to` on both targets)
are all at HIGHER addresses. **⇒ a cave here runs on every tick, engaged and disengaged — no state
freeze, and the `gp-0x6cf8 == 0x7FFFFFFF` seeding V288 rev 1 failed for is NOT needed.**
See [[reference_accord_0x29d72_is_the_feedback_operand_hook_flagsafe]].

- **FREE scratch (11)**: `r1, r6, r8, r9, r11, r12, r13, r16, r21, r26, r28` — each written before any
  read on every path out, **including the bail path** `0x290B0`-`0x290C0`.
- **LIVE**: `r14` (read `0x28F5E`), **`r10` and `r2` — via the BAIL path only** (`cmp r2,r10` @`0x290C8`,
  `cmp lp,r10` @`0x290D2`; easy to miss), `r25` (`0x29A60`), `r20/22/23/24/27/29`, `r15` (unproven),
  `lp` ⇒ **`jr` only**.
- **No PSW hazard**: entering flags were consumed by `bc` @`0x28F46`; the next consumer `bnc` @`0x28F58`
  is armed by `addi -0x5dc1,r11,r0` @`0x28F54`, after the return point.
- `r7` holds `x` only over `[0x28F4C, 0x28F8E]`; exactly two readers, the guard `addi` @`0x28F50` and
  `mul r16,r7,r0` @`0x28F8E`.
- `jr` to a cave at `0xC4C90`: `disp = 0x9BD44` ⇒ bytes **`89 07 44 bd`**; return to `0x28F50`.

## 🛑 The mandatory clamp

The producer clamps `|gp-0x6a56| <= 12000` (`movea ±0x2ee0,r0,r6` before all three `st.h`, `0x3F7B4`/
`0x3F7CC`). The consumer's own ±12000 test at `0x28F50`-`0x28F58` is **a BAIL, not a clamp**, and it
reads **`r7`** — so a cave that substitutes a filtered value into `r7` puts *its own output* through
Honda's sensor-implausibility test. A Q3 notch overshoots 1.155x on a step (V289's build script), i.e.
13,860 > 12,000 ⇒ **spurious bail**: `r26 := 0` @`0x290B6`, `gp-0x682f := 0`, `gp-0x6a34 := 0`,
`gp-0x3d2c := 2` (fb filter disabled next tick). **The cave MUST clamp its output to ±12000.**
Guard-safe alternatives that leave the guard on raw `x`: `0x28F6A` (`e5 e7 e5 73`, not a branch target)
or `0x28F86` (`e5 87 eb 73`), both with a smaller free-scratch set.

## Arithmetic

Q14 (`b0=16048, b1=a1=-31842, b2=16048, a2=15712`) at `xmax = 12000`: conservative bound
`31842*12000*4 = 1.528e9 < 2^31`, **margin x1.405** — better than the x1.098 V289 shipped on its own
±15360 sum. **No pre-shift needed.** (`sar 1` buys x2.81 but costs 2 counts = **0.25 deg/s** of rate
resolution, far coarser than the 0.032 deg/s a `>>3` costs on the ×30.89 fb sum.) See
[[reference_accord_fb_operand_clamp_46080_overflows_a_q14_notch]].

## LTI equivalence to notching the fb sum

The only elements between `x` and `r26` are the linear EMA, the linear `(1+z^-1)`, and the ±46080 clamp.
Measured on the two V289 routes: median engaged `|r26|` = **180/182**; ticks at the rail **0.0000 %**
(r62 engaged) and **0.2413 %** (r63 engaged). Equivalent in the grinding regime; **not a strict
identity**.
