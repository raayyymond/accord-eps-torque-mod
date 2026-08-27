---
name: reference-accord-arb-neardeadband-sign-latch
description: FUN_00028ea6 arb core has a deadband+sign-consistency latch on the IIR-shaped term (iVar34) right before the ramp-gain/output-gain multiply — cal 0xC64A3 enable, cal 0xC61B8=102 threshold, state gp-0x6b30. Strong structural match for near-zero-command chatter.
metadata:
  type: reference
---

# Arb core: deadband + same-sign latch immediately before the output gain (0x2a1ae-0x2a206)

2026-07-19/20 tracer pass (no r2/rizin available this session — GhidraMCP only: decompile_function +
disassemble_bytes + search_instructions + read_memory against `../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin`,
STOCK, image base 0). Dispatched to answer a team-lead question about upstream-of-gain near-zero-setpoint
behavior (tens-of-Hz LKAS vibration with the command dithering around zero, present only when openpilot
engaged).

## What FUN_00028ea6 does at this point (arb core, entry 0x28ea6)

By the time execution reaches `0x2a1a0`, a persisted 32-bit RAM accumulator `gp-0x3d3c` has just been
updated by a one-pole IIR blend (`cal 0xC63EC`=992/1024≈0.969 weight on old state, `cal 0xC63EE`=507/1024≈0.495
weight on a new raw term derived from a multi-table LERP cascade — NOT fully axis-identified, see Open below).
The tap `iVar34 = (gp-0x3d3c_old + iVar23_new) >> 5` is what feeds this gate.

```
0002a1ae  cmp   0x1,r16          ; r16 = cal[tp+0x74a3] = 0xC64A3, read ld.bu (UNSIGNED) at 0x2a198
0002a1b4  bne   0x2a1e6          ; cal != 1 -> SKIP gate entirely
0002a1b6  ld.bu -0x6806,gp,r12   ; r12 = gp-0x6806 (mode byte, shared with the re-engage/STEER_STATUS SM)
0002a1ba  cmp   r0,r12
0002a1bc  bne   0x2a1e6          ; mode != 0 -> SKIP gate
0002a1be  ld.h  0x71b8,tp,r6     ; r6 = cal[tp+0x71b8] = 0xC61B8 = L, SIGNED read
0002a1c2  mov   r9,r8
0002a1c4  sxh   r8               ; r8 = (int16)iVar34
0002a1c6  cmp   r6,r8
0002a1c8  bgt   0x2a1d4          ; (int16)iVar34 > +L -> to sign-check
0002a1ca  ld.hu 0x71b8,tp,r8     ; SAME cal, UNSIGNED read (mixed signedness on this cal — edit carefully)
0002a1ce  subr  r0,r8            ; r8 = -L
0002a1d0  cmp   r8,r9            ; r9 = iVar34 full 32-bit
0002a1d2  bge   0x2a1e2          ; iVar34 >= -L -> INSIDE BAND -> ZERO
0002a1d4  ld.h  -0x6b30,gp,r13   ; (outside band) r13 = LAST cycle's stored (post-gate) output
0002a1d8  mov   r9,r6
0002a1da  mul   r13,r6,r0        ; r6 = last_output * this_cycle_raw
0002a1de  cmp   r0,r6
0002a1e0  bgt   0x2a1e6          ; same sign, both nonzero -> pass through UNCHANGED
0002a1e2  mov   0x0,r9           ; else -> ZERO
0002a1e4  br    0x2a1ee
0002a1e6  mul   r14,r9,r0        ; NORMAL path: r9 := iVar34 * uVar18(ramp-gain, 0..0x8000 Q15)
0002a1ea  sar   0xf,r9
0002a1ec  sxh   r9
0002a1ee  ld.h  0x746c,tp,r7     ; <- GAIN cal 0xC646C, join point
...
0002a206  st.h  r9,-0x6b30,gp    ; unconditional: store whichever value resulted (0 or ramp-scaled) for next cycle
```

## Behavior (hand-simulated 4 cases, x=+100/-100/+1000/-1000 vs L=102, self-consistent symmetric result)

- **|iVar34| <= L (=102 stock) -> forced to 0.**
- **|iVar34| > L -> passed through ONLY if same sign as `gp-0x6b30` (last cycle's stored, already-gated
  output).** Sign flip, OR previous cycle having been zero (from the deadband OR a prior sign flip), forces
  this cycle to 0 too.

Because the comparison uses the *post-gate* stored value, this reads as a **self-latching zero**: once
triggered (by a dip through the deadband, or a genuine sign reversal), `gp-0x6b30` becomes 0, and the very
next cycle's sign product is `0 * anything = 0`, which fails the pass-through test again — indefinitely,
until `gp-0x6806` (the mode byte) goes nonzero and bypasses the whole block. `gp-0x6806`'s SM (`gp-0x3d38`,
8 states) is shared with re-engage/STEER_STATUS logic; whether it toggles nonzero periodically during
**steady engaged driving** (which would self-heal the latch on some cadence, possibly the "tens of Hz" beat)
was NOT traced this session — open question, see below.

## Cal values (fresh-read, STOCK)
- `0xC64A3` (tp+0x74a3) = **1** (ld.bu unsigned) — sole enable for this block. **Sole reader in the whole
  image** (`search_instructions` operand `0x74a3` -> 1 hit total).
- `0xC61B8` (tp+0x71b8) = **102** (0x0066) — deadband magnitude L, in the internal `iVar34` domain (post
  corridor-clamp, post multi-table blend, post-IIR — NOT directly CAN setpoint counts, not back-propagated).
  **Only 2 readers image-wide, both inside this same gate** (0x2a1be signed, 0x2a1ca unsigned — mixed
  signedness, same trap class as the memory-documented shadow-variable bricking risk: keep any edit within
  positive int16 range).
- `gp-0x6b30` state var — **exactly 2 references image-wide**, both inside this gate (0x2a1d4 read, 0x2a206
  write). No external consumer.

## Why this matters
Structural match for "tens-of-Hz LKAS vibration/grinding with a small command dithering around zero,
present only when openpilot engaged": any signal spending time near zero either sits inside the 102-count
flat band (forced 0) or gets zeroed on every sign change regardless of magnitude — textbook chatter/flat-spot
generator on a dithering near-zero command. See [[reference-accord-polarity-gp6752-is-static-boot-config]]
for the companion clean-negative finding (polarity does NOT chatter — it's build-time-fixed).

## Confidence / Open
[VERIFIED via raw disasm + concrete-value CFG simulation]: the gate structure, the two cal values, the
sole-consumer counts. [INFERRED, high confidence but not pcode-cross-checked]: the "self-latch" framing —
my parse of the decompiled C's flattened overflow-safe boolean did not cleanly reconcile with this reading
on casual inspection (I trust the ASM/simulation over that parse), and I did not pull `get_function_pcode`
on this exact slice to remove all doubt (risked another oversized-result truncation on the whole-function
call). [OPEN]: whether `gp-0x6806` toggles during steady engaged driving; the CAN-domain-equivalent size of
the 102-count threshold; full axis ID of the multi-table LERP cascade feeding the IIR's raw term.

## Suggested minimal cal-only mitigation (not yet built/tested)
`0xC64A3` (tp+0x74a3): 1 byte, unsigned load (no signedness risk), sole reader in the entire image, and
0x00 merely widens an ALREADY-LIVE bypass code path (the same one taken whenever `gp-0x6806!=0`, i.e. during
the SM's steady hold state) to apply unconditionally — not a novel/untested path. Smaller-scope alternative:
`0xC61B8` -> 0 removes the flat band but leaves the same-sign latch active.

## UPDATE 2026-07-20 — gp-0x6806 SM fully traced; latch mechanism CONFIRMED (pcode cross-check), gate liveness is NOT clean-inert

Followed up on the two open items from the first pass.

**Q2 (self-latch) settled via a scoped `get_function_pcode` pull over 0x2a1a0-0x2a206.** First read of the
pcode appeared to CONTRADICT the original branch-sense reading. Ran a calibration test — pulled pcode for
the ENABLE gate (0x2a222-0x2a250) whose ground truth is independently known (segmentF memory:
`gp-0x6b3c=(ENABLE∈{2,3})?clamp:0`) — and it read as similarly inverted/inconsistent. Diagnosis:
`get_function_pcode` returns Ghidra's post-SSA "high pcode" (contains `MULTIEQUAL`/phi nodes) which **reuses
temp names like `U11c00` across unrelated computations**; a naive last-write-before-use hand-parse is unsafe
on it. This was a tooling artifact, not a real contradiction. Falling back to raw disasm + the decompiled C's
actual brace-scoping (read carefully this time — `iVar23 = (iVar34*ramp_gain)>>15` at line 1246 sits AFTER
both closing braces, so it runs whenever the gate is disabled OR the deep condition didn't fire, not only in
an explicit else) confirms the ORIGINAL finding exactly: cal `0xC64A3` is a true enable, and the deadband +
same-sign latch on `gp-0x6b30` is real as first reported. **[VERIFIED, high confidence]**

**Q1 (does `gp-0x6806` sit at a value that makes the gate inert during normal driving) — traced the full
`gp-0x3d38` 9-state ramp SM.** `gp-0x6803`/`gp-0x6805` are live 100Hz per-CAN-frame bitfields extracted in
`FUN_00052676` (CAN 0xE4 intake) from a raw byte at `gp-0x1426`: `gp-0x6805 = bVar4>>7` (reads like
STEER_REQUEST, stable at 1 through a whole engagement). SM behavior:
- State 1 (waiting): starts ramp when `gp-0x6805==1 AND gp-0x6807(STEER_STATUS)<3`; sets `gp-0x6806:=1`,
  ramps `gp-0x69b0` up by cal `0xC63F8`=33/cycle (mode 0, slow) or `0xC63FC`=328/cycle (mode 2, fast),
  state->3 or 6.
- State 3 (ramping): at saturation (`gp-0x69b0` hits 0x8000) sets **`gp-0x6806:=1` explicitly**, state->2.
- **State 2 (steady hold): as long as `gp-0x6807 ∉ {3,4,7}`, falls through WITHOUT touching `gp-0x6806` —
  it stays 1 (gate INERT) for the entire hold.** This is the dominant state during ordinary engaged driving.
- **The instant `gp-0x6807==3` (or 4, or 7) while holding, the SM sets `gp-0x6806:=0` immediately, fast
  ramps down (cal `0xC63F4`=328/cycle, ~100 cycles), resets, then re-ramps up (~100-1000 cycles) before
  `gp-0x6806` returns to 1.** This is a real, evidenced periodic-reset pathway (not hypothetical) — the
  self-latch mechanism above IS reachable outside the transient engage/disengage window.

**Tie-in to existing history: `gp-0x6807==4` is the SAME "no_torque_alert_2" debounce as the V36/V37 gentle-EME
root cause** (`torque gp-0x682f > cal 0xC64B4=112` sustained 5cyc, OR `rate > cal 0xC61C0=1600` — see
`builds/v36-debounce-sm-root-cause-and-build.md`) — i.e. triggered by sustained MODERATE-HARD steering, not
near-zero dithering. Better structural fit for the boot card's separate "several-Hz hard-turn ratchet" than
for the near-zero vibration this file was originally dispatched to explain. `gp-0x6807==3`'s trigger is a
sibling branch in the same debounce cascade (same function, ~line 175-296 of the decompile, keys partly off
`bVar2`/`gp-0x67fe`) — **NOT resolved**, flagged as the concrete next step (bounded, same function, not a
new investigation).

**Net effect on the mitigation argument**: `0xC64A3=0` is still safe (same reasoning, now on firmer ground —
state 2 hold IS confirmed to be where the car spends most of normal engaged driving, so the bypass path it
forces is proven routine, not theoretical) but its **relevance to the specific near-zero-dithering symptom is
now uncertain** rather than clearly established: if that symptom occurs during genuinely fault-free steady
driving (STEER_STATUS never near 3/4/7), the gate is already inert and this cal is a no-op for that case.

## UPDATE 2026-07-20 (session 2) — on V37/V38's actual cal set, STEER_STATUS 4 and 7 are DEAD; ==3 depends on two unresolved live values

Re-traced `gp-0x6807`'s producer cascade (decompiled ~lines 175-296 of `FUN_00028ea6`, the SAME inline debounce
this file already covers) specifically against V37/V38's calibration (V36/V37 raised `0xC64B4/B5/B6/B7`=0xFF,
`0xC61C0/C2/C4`=0xFFFF, `0xC64B8`=0xFF — see `builds/v36-debounce-sm-root-cause-and-build.md`).

**STEER_STATUS=4 confirmed UNREACHABLE**: trip condition is an OR-chain of `cal < operand` tests; the torque
operand (`gp-0x682f`) is hard-saturated to max 254 (line 140: `(0xfe>=x)*x - (0xfe<x)`), the rate-ish operand
traces to `|gp-0x4f60>>5|` with `gp-0x4f60` hard-bailed to ±25600 elsewhere in the same function, ceiling 800.
Every cal is raised to its operand's own max/overflow value (255/65535) — `cal < operand` can never be true.
**[VERIFIED]**

**STEER_STATUS=7 confirmed UNREACHABLE**: gated by DTC-0x49 counter `gp-0x6758` saturating (`>= cal[0xC64E0]+
cal[0xC64E1]`, untouched by V37, stock 100). Found an apparent loophole — a THIRD increment site for
`gp-0x6758` (line 214, unconditional, no cal gate) — but traced it: that branch is only reachable once the
counter has ALREADY passed `cal[0xC64E1]`, and the ONLY way to climb there is via the line-198/208 increments,
both gated by `cal[0xC64B8] < gp-0x682f` (torque max 254 < cal 255 = dead). Counter can never leave 0, the
"unconditional" increment is unreachable in practice, V37's fix is complete. **[VERIFIED]**

**STEER_STATUS=3 trigger, formula fully derived but NOT resolved to reachable/unreachable:**
```
bVar2_first = !( (gp-0x6a5e<320 || gp-0x6a5e>12800) && gp-0x68b3==0 )   // cal 0xC62E8=12800, 0xC62EA=320
bVar2 = (gp-0x69aa in [0x8000,0x8001) && bVar1 && bVar2_first && gp-0x67fe==2) ? ~always-true : false
gp-0x6807 = 3  when !bVar2 (and outer gates pass, CAN healthy)
```
Two inputs are LIVE, not cal-gated, and I could not resolve their typical value: **`gp-0x69aa`** =
`(uVar17*uVar6)>>15`, a Q15 product computed every cycle in `FUN_0004503c` (large driver-assist blend fn,
touches `gp-0x6b94` — aggregator-adjacent); the gate needs it pinned almost exactly at 0x8000 (both blend
terms simultaneously at ceiling) — structurally reads as edge-case but not proven. **`gp-0x67fe`** — only 5
writer sites total, all in `FUN_0003bd7c`/`FUN_0003e760` (FOC-mode EPS assist substate, matches existing
`misc/eps-gp67fe-trump-engaged-holding-substate.md`) — that memory's "stuck at 1" observation is of a DERIVED CAN
bit from a different consumer phase, NOT re-verified here as this raw byte's value, so NOT reused as fact.
**If `gp-0x67fe` is not routinely 2, `==3` fires routinely (SM never settles into state-2 hold), which would
mean the deadband gate is live far more of the time than the "periodic reset" framing above suggests — open,
decisive, would need either a full trace of `FUN_0004503c`+`FUN_0003bd7c` or live telemetry of `gp-0x6807`.**

**Bonus finding**: `gp-0x6807` can also be set to **2** via a cal-independent path (line 213, `cVar19=2`,
reached when NOT(`gp-0x6802==2 AND uVar33==0`)) — `gp-0x6802` not identified. Relevant to a LOW_SPEED_LOCKOUT
hypothesis (Honda DBC STEER_STATUS=2) since it's reachable outside the whole debounce cascade V37 neutered.

**Recommendation carried to the operator**: live telemetry of `gp-0x6807` during a drive covering the vibration
condition is now cheaper and more decisive than continuing this static trace.

## Related
[[reference-accord-polarity-gp6752-is-static-boot-config]] · [[reference-accord-segmentE-arbitration-shaper-dtc-gate-table]] · [[reference-accord-segmentF-delivery-enable-motor-output-gate-table]] · [[v36-debounce-sm-root-cause-and-build]] · [[eps-gp67fe-trump-engaged-holding-substate]]
