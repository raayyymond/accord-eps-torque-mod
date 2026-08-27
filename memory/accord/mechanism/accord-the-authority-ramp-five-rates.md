---
name: accord-the-authority-ramp-five-rates
description: The gp-0x69b0 Q15 authority ramp has FIVE rate cals at 0xC63F4-FC (two up, three down), fully mapped from the decompile; the 33-vs-328 pair is a MODE fork on gp-0x6803, not the left/right asymmetry the record calls it. Measured null - STEER_STATUS never leaves 0 engaged, so the ramp is never knocked down.
metadata:
  node_type: memory
  type: reference
---

# THE `gp-0x69b0` AUTHORITY RAMP — ALL FIVE RATES, AND A CORRECTION TO THE RECORD

★★★★ **EVIDENCE** — decompile of `FUN_00028ea6` @`0x28ea6` plus a byte read of the V108 image,
2026-08-27. `gp-0x69b0` is the **Q15 multiplier on the whole LKAS lane** (`0x2A1E6 mul r14,r9,r0`),
range 0..0x8000 = 0.000..1.000, ticked at 1 kHz by the 8-state SM `gp-0x3d38`.

```
 cal      value  ms 0<->FS  role
 0xC63F4   328      99.9    DOWN  states 3(LAB_294d8)/4/5 -> reset to 0
 0xC63F6    16    2048.0    DOWN  LAB_296f8, SM->4
 0xC63F8    33     993.0    UP    state 1 (gp-0x6803==0) -> SM 3; state 3 climb, sat 0x8000 -> SM 2
 0xC63FA    66     496.5    DOWN  LAB_29680 SM->8; and state 8
 0xC63FC   328      99.9    UP    state 1 (gp-0x6803==2) -> SM 6; state 6 climb, sat 0x8000 -> SM 7
```
**All five are STOCK and VIRGIN across every build.** Climb gate:
`gp-0x6805 == 1` AND `gp-0x6803 in {0,2}` AND `gp-0x6807 (STEER_STATUS) <= 2`.

🛑 Read all five together — this is a table, and the one-knot trap in
[[accord-kd-is-one-knot-of-a-flat-lerp]] applies to reasoning about any single one of them.

## 🛑 CORRECTION — `gp-0x6803` IS A **MODE** FLAG, NOT LEFT/RIGHT
[[accord-steering-sign-convention-confirmed]] files `0xC63F8`=33 vs `0xC63FC`=328 as a
*"10x LEFT/RIGHT ramp-rate asymmetry"*, and [[accord-the-return-to-centre-crux-and-what-died-for-it]]
**deprioritised it on a left/right null.** **The identification is wrong**, three ways:
1. `gp-0x6803` takes **three** values in the decompile (`0`, `1`, `2`) — a direction flag would be two.
2. The two rates fork the SM into **two parallel chains with different terminal states** (1→3→2 vs
   1→6→7) and different `gp-0x679f` tags (1/3 vs 2/4). A direction flag does not fork a state machine.
3. The kit's own `reference-accord-driver-override-curve-kills-lkas-authority.md:16` already annotates
   `ld.bu -0x6803,gp,r10` as `; mode flag`, and handoff open-item F calls it *"which taper arm is live"*.
⇒ **The deprioritisation reached the right answer for the wrong reason.** Do not let a future session
revive these cals on the argument that *"left/right was never the issue"* — it wasn't, and they are
still dead, for the measured reason below.

## ✅ MEASURED NULL — THE RAMP IS NEVER KNOCKED DOWN
Pre-registered. **STEER_STATUS is identically 0 across 3,312 s engaged on r1e/r1b/r77/ra6, every speed
band, ZERO transitions.** ⊕ Control PASSES: status **3** does occur — 4 of 6 routes, **only at 0.0 mph
and only disengaged** (107 / 2 / 8 / 9 frames). ⇒ the ramp reaches `0x8000` ~1 s after engagement and
**holds**; the 10:1 down:up asymmetry is a **one-time 0.9 s engage transient**, not a steady-state
authority deficit.
⇒ **RETIRED as a candidate for the low-speed steering-rate limit** — which is
[[accord-low-speed-rate-limit-is-openpilot-steer-max]] instead.
⚠ Still live for one thing: the ~2.05 s post-disengage release, where `0xC63F6`=16 (2048 ms) sets the
mode-column hold. `build_v108_tva.py:286` already names it.
