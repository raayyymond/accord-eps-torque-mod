---
name: reference-accord-eme-lever-semantics
description: "Disasm-grounded semantics of the four Accord EME levers, from the 4-analyst Ghidra review (../assessment/, 2026-05-27, decode-verified). SLEW 0xC61D6 (tp+0x71d6, read once @0x43350) = step size of a rate limiter on internal state gp-0x356c (2 refs total: read 0x434ce, store 0x43504); step=0 FREEZES it at 0 (dormant lane, NOT a disabled output damper); 0→14 ACTIVATES an uncalibrated speed×torque 2D map (target = curve@0xC6770 × curve@0xC69E8, 25·r8>>10) onto the live command via mux byte 0xC64C9=0 → r28→r20→add@0x43af4→governor→±0x2000→gp-0x6b98. DEADBAND 0xC6424 (tp+0x7424, read once @0x43358, cmp @0x434ca) gates ONLY that limiter ⇒ inert while slew=0 (deadband/slew COUPLED). The real EME command-cut is the OVERRIDE STATE MACHINE node gp-0x6960 (states gp-0x355d; stores 0x4362a/0x436c2 incl ori 0x8000), NOT the deadband. RAMP 0xC64DE (tp+0x74de, stock 0x11=17) = COUNT CEILING of the re-engage/debounce SM in m_steer_torque_arbitration (counter gp-0x6756, init=(ceiling>>1)+1); 17→27 LENGTHENS/softens the re-engage (NOT 'faster'), targets recovery ratchet not the initial snap. NO output rate-limiter exists as a cal value; gp-0x6b98 has only ±0x2000 + a ±5 change detector. tp=0xBF000, gp=0xFEDF8000."
metadata:
  node_type: memory
  type: reference
---

The four EME levers debated across V16/V17/V18 for the 2020 Accord (`39990-TVA,A160`), with the **disassembly-verified** meaning of each, from the 4-analyst Ghidra review in `../assessment/` (`user-A-verdict.txt` is the 11-round trace; B/C corroborate). Bases `tp=0xBF000`, `gp=0xFEDF8000` (see [[reference-accord-pointer-base-audit]]). This memory is the lever vocabulary; the symptom/mechanism context lives in [[reference-accord-driver-override-plausibility-eme]] and the build state in [[project-accord-torque-mod-v0]].

## SLEW — `0xC61D6` (`tp+0x71d6`), stock 0 [V, deterministic from opcodes]

Read **exactly once**, @`0x43350` in `s_motor_torque_rate_shaper` (`FUN_00042af8`). It is the **step size** of a rate limiter applied to an internal persistent state `gp-0x356c`. The limiter math @`0x434d4`–`0x434f0`:
```
r9 = prev (gp-0x356c) ; r25 = target
down: r12 = r9 - slew ; if r12 <= target snap to target
up:   r12 = r9 + slew ; if r12 >= target snap to target
store gp-0x356c = r12
```
With slew=0 both branches give `r12 = prev ± 0 = prev`, and the snap fires only when already at/past target ⇒ **the state cannot converge; it FREEZES.** The deadband path resets it to 0 (`0x434ee`), so slew=0 pins `gp-0x356c` at **0 forever**. `gp-0x356c` has **exactly two references in the whole program** (read @`0x434ce`, store @`0x43504`) — no other writer.

**This is the keystone correction:** slew=0 is NOT "the delivered-command limiter is disabled / a drop passes through." A disabled limiter would be an infinite step or a bypass; step=0 is maximally restrictive = the lane is OFF. Setting **0→14 ACTIVATES a dormant speed×torque 2D shaping map**: the target `r25` is `curve(speed)@0xC6770 × curve(torque/vel)@0xC69E8`, combined `25·r8>>10`. The lane is LIVE (not inert): mux cal byte `0xC64C9` (`tp+0x74c9`) = 0 ⇒ `cmove @0x43aa0` selects the limiter value `r28`→`r20`, added @`0x43af4` → `min(governor gp-0x4f64)` → ±0x2000 clamp → delivered command `gp-0x6b98`. So 0→14 injects an **uncalibrated map** onto the live output. **Highest-risk lever; last/never.** (B located the target tables `tp+0x7770`=`0xC6770`, `tp+0x79E8/79EA`=`0xC69E8/EA`, corroborating the 2D-map framing.)

## DEADBAND — `0xC6424` (`tp+0x7424`), stock 29491 [V]

Read **exactly once** @`0x43358`, used at one `cmp` @`0x434ca`: `if (uVar34 < deadband) term = 0`. It gates **ONLY** the `gp-0x356c` limiter. Therefore **with slew=0 the deadband edit (29491→20000) is FULLY INERT** — both branches yield 0 (explicit-0 vs frozen-prev-0). Deadband and slew are **coupled**: the deadband acquires meaning only once slew≠0 lets `gp-0x356c` carry a value the threshold can gate. "deadband-only" (V17) is safe-because-inert, not a fix.

## The REAL command-cut node — override state machine `gp-0x6960` [V]

The EME's `gp-0x6b98`→0 is driven by the **override state machine**, not the shaper deadband: node `gp-0x6960`, states `gp-0x355d`, stores @`0x4362a` and @`0x436c2` (the latter writes an `ori 0x8000` sentinel). This is NOT gated by the `0x7424` deadband. The Era-16 memory's "shaper deadband zeroes the command via gp-0x6960" **conflated two distinct mechanisms** — that conflation is the root error that made V16/V17 look plausible.

## RAMP — `0xC64DE` (`tp+0x74de`), stock 0x11 = 17 [V; net feel MEDIUM]

Read **8×** in `m_steer_torque_arbitration` (`FUN_00028ea6`). It is the **count ceiling** of the re-engage/debounce state machine on the **driver-override path** (operands: fused driver torque `gp-0x6a5e`, transition states `gp-0x3d36`/`gp-0x6809`, ramp counter `gp-0x6756`). Init: `gp-0x6756 = (ceiling>>1)+1`; the SM increments by 1/cycle until it hits the ceiling. **`0x11`→`0x1B` raises init 9→14 and ceiling 17→27 ⇒ the ramp SPAN GROWS (≈8→≈13 steps) ⇒ re-engagement is SLOWER / more gradual** — the opposite of the "faster re-engage" label it was given. It is the **only V16 lever on the override path the EME traverses**, and it targets the **recovery ratchet** (the ~10 s jerky part), **not the initial snap**. Net road effect is a debounce trajectory question, not statically decidable.

## No output rate-limiter exists as a cal value [V]

`s_motor_torque_rate_shaper`'s output `gp-0x6b98` has only a **±0x2000 magnitude clamp** and a **±5 change DETECTOR** (for the dual-path lockstep monitor) — there is **no rate-of-change limit**. A gate-agnostic, 2×-preserving fix for the *snap* (convert the 1-sample drop into a ramp) would require an **asymmetric down-rate limiter injected as a CODE PATCH**: at the store `st.h r8,-0x6b98 @0x43b52` the previous command is already resident in `r15` (`ld.h -0x6b98 @0x43b34`), so a delta-clamp could go there, trampolining into the erased `0x8B218–0xB6FFF` cave. **This was scoped on paper in the review and explicitly NOT built** (DOWN-rate is a vehicle-dynamics safety trade, not a logic value; needs a CAN-0x427 EME-magnitude capture + emulation first). **No trampoline exists in any `.rwd` or in the Ghidra project** (verified 2026-05-27: `../accord-firmware/analysis-2020accord/ghidra_project/code.bin` is byte-identical to the stock dump; the cave is all-`0xFF`; `0x43b52` disassembles as the stock `st.h`). The prior "matches aragon's asymmetric rate-limit prior art" claim is **RETRACTED** — his `rwd-xray-2026` contains torque-table mods, min-steer-speed→0, a "leave the rate-side tables alone" rule, and a comma-side LPF, but no asymmetric output limiter; and a comma-side LPF cannot fix a firmware gate tripped by the driver's physical column torque.

## Observability constraint [V — operator]

The EME firing gate is **UNOBSERVABLE on-car**: `gp-0x6960`/`gp-0x356c`/`gp-0x6b98` and the override states are internal RAM (not CAN signals), and an EME is a transient on-road event (op engaged + sharp low-speed turn + real override torque), not bench-reproducible — you cannot attach a live debugger to a moving car. Only **passive CAN `0x427` motor torque** sees the outward signature. Consequence: no gate-specific fix can be validated at the mechanism level; only by outward behavior. This is why **V18 (ramp-only) was validated by road feel** ([[feedback-operator-lived-experience]]) and is the current good build — the survivor lever, judged by the only available signal.
