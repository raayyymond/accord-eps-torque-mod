---
name: reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz
description: MAJOR CORRECTION — FUN_0002214a's `uVar2 = 1<<(gp-0x67fa&0xf)` and the 0x830/0xc30/0xd30 "andi" gates are STATE bitmasks (which of 16 states are active), NOT phase/tick-rate dividers as a prior memory claimed. Since gp-0x67fa's reachable set is {11} in practice, the WHOLE estimator/residual/PID/aggregator/governor/shaper loop runs at ONE uniform 1kHz rate with exactly 1 tick of transport delay (the gp-0x6b98 readback)
metadata:
  type: reference
---

**Corrects `reference-accord-base-assist-lane-architecture.md`'s "phase mask 0xD30 (5/16 base ticks)" / "0xC30 (4/16)" framing** — that was a misreading. Decompiled `FUN_0002214a` (0x2214a) directly, full body (the master control-loop dispatcher):

```c
uVar2 = 1 << (*(byte*)(gp-0x67fa) & 0xf);   // ONE-HOT bitmask of the CURRENT STATE (0-15), not a tick counter
...
if ((uVar2 & 0x830) != 0) { FUN_0003b8f6(); FUN_0003bc20(); ... }   // states {4,5,11}
uVar3 = uVar2 & 0xc30;                                               // states {4,5,10,11}
if (uVar3 != 0) { FUN_00038148(); FUN_0003b338(); FUN_0003b49a(); FUN_00036f30(); FUN_00037fe6(); }
if (uVar3 != 0) { FUN_0003a382(); }
...
if (uVar3 != 0) { FUN_0003aa2c(0x20); }
if ((uVar2 & 0xd30) != 0) { FUN_0004503c(0x21); FUN_0004595a(); FUN_000456a4(0x22); FUN_00045a20(); FUN_00042af8(0x23); FUN_00043e44(0x24); }
```

Also calls `FUN_0006bb08(3, uVar2)` early — a SUB-dispatcher using the SAME `uVar2` state mask, which itself gates `FUN_0007f3f8` (torque-sensor fusion, computes `gp-0x4f60`, calls `FUN_0007e74a` = the `gp-0x4f62` torque-RATE producer using cal `0xC6C42`) on `andi 0xd30`.

**Since `gp-0x67fa`'s reachable set is {11} ALONE in practice** ([[accord-gp67fa-reachable-set-is-11]] / MEMORY.md "🛑 gp-0x67fa's REACHABLE SET IS EFFECTIVELY {11} ALONE"), state 11 satisfies ALL of 0x830, 0xc30, 0xd30 (bit 11 is set in each) ⇒ **every one of these gated blocks fires on EVERY call of `FUN_0002214a`** — there is NO tick-rate division happening among them during real driving. `FUN_0007f3f8`/`FUN_0007e74a` (torque sensing + torque-rate) run at the SAME rate as `FUN_0003b8f6`/`FUN_00038148`/`FUN_00037fe6`/`FUN_0003a382`/`FUN_0003aa2c`/governor/comp-add/shaper — all inside ONE call of `FUN_0002214a`.

**Consequence for the loop model**: taking `FUN_0002214a` = 1kHz (the established "control task ~1000Hz" fact — BELIEF, not re-derived from OSTM0 this session), the WHOLE direct signal path `gp-0x6b98 → FUN_0003b8f6[0xC40D4] → FUN_0003bc20 → FUN_00038148[0xC63AC] → FUN_00037fe6 → FUN_0003a382[PID] → FUN_0003aa2c[+gp-0x4f62 r24/r26] → FUN_0004503c[governor] → FUN_000456a4[comp-add] → FUN_00042af8[shaper] → gp-0x6b98` has **exactly ONE tick of pure transport delay** — the `gp-0x6b98` readback at the top of `FUN_0003b8f6`, which reads the PREVIOUS tick's motor command (written at the very end of the SAME dispatcher, after this whole chain runs). Every OTHER hop in the chain is same-tick / delay-free, because the call order in `FUN_0002214a` has each stage consume a value a strictly-earlier stage already wrote THIS tick. (Reconciles exactly with the existing "-0.87dB,-36.06° incl. 1-tick transport" figure for `0xC40D4` — my bare-cascade number + one 1kHz-tick delay = that figure exactly.)

⚠ NOT corrected by this: `FUN_00034350` (damper→`gp-0x6bd0`) and `FUN_00034a72` (boost→`gp-0x6bbe`) are called from a DIFFERENT dispatcher (`FUN_00022ca0`, established 100Hz elsewhere) — neither appears in `FUN_0002214a`'s call list, so the existing "100Hz damper" finding stands untouched; this correction is specific to the estimator/residual/PID/aggregator/governor/shaper chain and the torque-sensing/rate chain, all of which share `FUN_0002214a`.

See [[reference_accord_c63ac_second_phase_lag_lever_and_estimator_phase_table]] for the phase numbers this enables, and [[reference_accord_gp4f62_torque_rate_producer_and_c6c42_window]] for the torque-rate/`0xC6C42` connection this surfaced.
