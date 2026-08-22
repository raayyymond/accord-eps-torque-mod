---
name: reference_accord_fun41464_rate_signal_hub_and_fun34350_damper_hook
description: "FUN_00041464 is THE central motor-rate signal-conditioning hub (task 1, 1kHz): from raw gp-0x4f50 it produces gp-0x6abc (raw shadow-copy), gp-0x6abe (slew-limited signed rate, alpha=37/128 corner 54.8Hz -- Honda's OWN damper input), gp-0x6ac0 (|gp-0x6abe|), gp-0x6ac2 (sign-gated |rate| vs gp-0x6b98 motor command), gp-0x6c2c/gp-0x6c2e (two independent EMA accelerations). FUN_00034350 (Honda's viscous damper, FactorC*FactorE) reads gp-0x6abe at 0x34604, computes sign=-sgn(gp-0x6abe)*|shaped magnitude| in r8, THEN clamps r8 to +-r6 (a separate ceiling LERP) and shadow-stores to gp-0x6bd0/gp-0x4cf2. A cave hook at 0x346a4 (old bytes e4673f95 = ld.hu -0x6ac2[gp],r12) sits AFTER r8 is finalized (sign-flip at 0x346a2) and BEFORE the clamp/shadow sequence begins (0x34720) -- inserting there lets a new term be ADDED to r8 while Honda's own +-ceiling clamp and shadow-lockstep protection bounds the COMBINED result untouched, same proven-safe pattern as the gp-0x6b26/FUN_00036c12 hook. r11 already holds gp-0x6abe at this point (loaded 0x34604, not clobbered through 0x3469e) -- free input, no extra load needed."
metadata:
  type: reference
---

# FUN_00041464 (rate-signal hub) + FUN_00034350 (Honda's viscous damper) -- full map, for the V106 band-pass damper task

Traced 2026-08-22, `damper-cave` subagent, GhidraMCP fresh decompile + disassembly on stock `code.bin`,
for the operator's band-limited active-damper mandate (`gp-0x6c2c`/`gp-0x6abc`/`gp-0x6bbe` candidates).

## FUN_00041464 [EVIDENCE, fresh decompile 0x41464] -- produces SIX shadow-paired signals from ONE raw input

Caller: `FUN_0002214a` (task 1, 1 kHz), mask `0xd30` = states `{4,5,8,10,11}`, gapless on road-reachable
`{4,11}`. Normal-path (non-fault-sentinel) formulas, all derived from `gp-0x4f50` (RAW resolver/motor
ELECTRICAL RATE, signed):

```python
raw          = s16(gp-0x4f50)                      # RAW, unfiltered, this tick
gp_0x6abc    = raw                                  # shadow-paired copy of raw (gp-0x4cc0), ~unfiltered
target       = raw * 1024
tracked      = tracked_prev + ((target-tracked_prev)*K)>>7   # K = cal(tp+0x743c)=0xC643C=37 stock
                                                     # -> alpha=37/128=0.2891, 1-pole corner 54.83 Hz @1kHz
gp_0x6abe    = tracked >> 10                        # SIGNED, SLEW-LIMITED rate -- Honda's OWN damper input
gp_0x6ac0    = |tracked>>10|                         # UNSIGNED magnitude twin, FactorE's LERP index
gp_0x6ac2    = |gp_0x6ac0| if sign(tracked)==sign(gp-0x6b98) else 0   # gated on agreement with the
                                                     # DELIVERED FOC command's sign (co-directional rate)
acc          = clamp((tracked-tracked_prev_word)*32, +-16384000)     # feeds the 2 accel EMAs below
gp_0x6c2c    = EMA(acc, alpha=K1/128, K1=cal 0xC643C=37) >> 9        # fast accel EMA (see gp6c2c memory)
gp_0x6c2e    = EMA(acc, alpha=K2/128, K2=cal(tp+0x50da)) >> 9        # slow accel EMA (sibling)
```
All six (`gp-0x6abc/-0x4cc0`, `gp-0x6abe/-0x4cc2`, `gp-0x6ac0/-0x4cc4`, `gp-0x6ac2/-0x4cc6`) are
individually shadow-lockstep-paired (each own `FUN_0006b9fa` resync on mismatch) -- 4 MORE pairs beyond
the 5 scoped in [[reference-accord-fun45a20-monitor-and-shadow-lockstep-pairs]] and the 6th
(`gp-0x6b26`/`gp-0x4cd0`) this agent found earlier today in
[[reference_accord_gp6c2c_gp6b26_fun36c12_chain_and_v106_gate1]]. **Do not cite "5 pairs" as a ceiling
anywhere in this kit again.**

⚠ **`gp-0x6abc` and `gp-0x6abe` are DIFFERENT signals**, contrary to a loose brief-level pairing
("gp-0x6abc / gp-0x4f50, ~4.7121 ct/(deg/s), inherited"): `gp-0x6abc` is the raw/unfiltered echo,
`gp-0x6abe` is the slew-limited (54.8 Hz corner) one Honda's damper actually reads. The 4.7121 ct/(deg/s)
scale claim (unverified this session, carried from an earlier one) most likely belongs to `gp-0x6abe` or
`gp-0x6ac0`, not `gp-0x6abc` -- re-derive the scale before quoting it on either specific address.

## FUN_00034350 (Honda's base-assist viscous damper, FactorC x FactorE) [EVIDENCE, fresh decompile+disasm 0x34350]

```python
uVar16 = |gp-0x6abe|                                 # = gp-0x6ac0, re-read here (0x345fa)
if uVar16 < 0x32c9 and gp-0x6abe in-range:
    shape = (FactorC(gp-0x698a) * FactorE(uVar16) * angle_factor(gp-0x6a10) * col_speed_factor) >> 30
    r8 = shape                                       # ALWAYS NON-NEGATIVE (unsigned LERP products)
    if gp-0x6abe > 0: r8 = -r8                        # <<< THE SIGN LINE, 0x3469e-0x346a2
else:
    r8 = 0
# r8 == uVar7 == Honda's raw damper magnitude*sign, FINAL at 0x346a2.
r6 = separate_ceiling_LERP(gp-0x6ac2)                 # table 0xC77A0, fallback tp+0x7158; INDEPENDENT of r8
gp_0x6bd0 = clamp(r8, -r6, +r6)                       # 0x34720-0x3475c, shadow-paired gp-0x4cf2
```
**Sign rule, confirmed directly from the disassembly** (matches
`docs/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md` §6.3's citation exactly):
`sign(gp-0x6bd0_unclamped) = -sign(gp-0x6abe)` -- i.e. Honda's damper OPPOSES the signed slew-limited
motor rate. `gp-0x6bd0` enters `FUN_0003aa2c` (the aggregator) as a **plain "+" addend**, zero-reject
window **±0x800 = ±2048** (byte-exact from `FUN_0003aa2c`'s own decompile, confirming RULE 14).

## THE HOOK POINT for a new band-pass term riding this damper [EVIDENCE, byte-exact]

```
0x346a4: ld.hu -0x6ac2[gp],r12    old bytes: e4 67 3f 95   (4-byte instr, confirmed via search_instructions)
0x346a2: subr r0,r8               <- r8 (uVar7) is FINAL here, one instruction earlier
0x34720: ld.h -0x4cf2[gp],r10     <- the clamp/shadow-store sequence STARTS here
```
Hooking `0x346a4` with a `jr`-trampoline (same class as V39's `0x3AC78` and V48B's `0x7FEAC`, both
task-1/1kHz, both flown -- see [[reference_accord_v39_v48b_1khz_hook_precedent_correction]]): a cave can
add a new term to **r8** (Honda's own value), replicate the displaced `ld.hu -0x6ac2[gp],r12`, then jump
back to `0x346a8`. **Honda's own clamp-to-±r6 and shadow-store at `0x34720` then bounds the COMBINED
value untouched** -- structurally cannot desync the shadow pair or bypass the ceiling, because that code
runs byte-for-byte unmodified on whatever `r8` holds when it gets there.

**Register liveness at the hook, established (not a full pcode sweep — flagged open below):**
- **r8** = Honda's `uVar7`, must be preserved/augmented (this is the whole point).
- **r11** = `gp-0x6abe` (loaded at `0x34604`, not reassigned anywhere in `0x3460c`-`0x3469e`, read again at
  `0x3469e` for the sign test) — **still holds `gp-0x6abe` at `0x346a4`, free to read again at zero cost.**
  Not read again anywhere later in the function after `0x3469e` — free to clobber as scratch after use.
- r6/r7/r9/r10/r12/r13/r14/r16/ep get reused by the immediately-following ceiling LERP (`0x346a4`-`0x3471c`)
  — **NOT safe as cave scratch without a full liveness check.** r12 specifically is the destination of the
  displaced instruction itself and must hold its correct value (`gp-0x6ac2`) when the cave jumps back.

## Open items — what's needed before cutting real cave bytes
1. Full liveness sweep (pcode or exhaustive manual trace) at `0x346a4` to name 2+ safe scratch registers
   for the EMA arithmetic beyond r8/r11 (a 2-stage EMA needs several temporaries for the multiply/shift
   chain) — NOT done this session, this is the concrete next step.
2. `gp-0x6bd0`'s / `r8`'s typical live magnitude distribution — unmeasured this session. Needed to size the
   new term's gain `K` as a sane FRACTION of Honda's own signal (avoid the V80 "flatten into a relay"
   failure even though Honda's own clamp bounds the absolute worst case).
3. Exact byte encoding of the `subr`/`ble`/`cmp` sequence at `0x3469e-0x346a2` if a build ever needs to
   verify old-bytes there too (not required for the `0x346a4` hook itself, which is one instruction later).

Related: [[reference_accord_gp6c2c_gp6b26_fun36c12_chain_and_v106_gate1]] (sibling trace, same day, adjacent
signal family) · [[reference_accord_v39_v48b_1khz_hook_precedent_correction]] (the hook-class precedent
this hook point relies on) · `docs/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md` §6 (the original
`gp-0x6abe`-sign citation this independently re-confirms).
