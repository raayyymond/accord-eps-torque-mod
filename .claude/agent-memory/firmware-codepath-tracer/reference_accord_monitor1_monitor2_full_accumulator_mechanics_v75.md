---
name: reference_accord_monitor1_monitor2_full_accumulator_mechanics_v75
description: Full instruction-level accumulator/tolerance/trip mechanics for both hard-shutdown monitors (FUN_00042af8 int-domain "Monitor 1", FUN_00043e44 float-domain "Monitor 2") built for the V75 incident. Corrects a same-session Monitor-2-gate off-by-0x1000 error another agent made. Settles sign-alternation (does not cancel) and computes break-even duty = 1/3 exactly.
metadata:
  type: reference
---

Built 2026-08-06, V75 incident follow-up. Program: stock `code.bin`. Method: decompile-first
(`decompile_function`), then `disassemble_function` for exact addresses, `read_memory` for byte
confirmation. `gp=0xFEDF8000`, `tp=0xBF000`.

## 🛑 Correction of a same-session error: Monitor 2's gate is LIVE, not dead [EVIDENCE]

Another agent this session read `0xC74A4=0xEA` and concluded Monitor 2 (`FUN_00043e44`/`FUN_00044666`)
is "permanently gated off." **That is the exact off-by-0x1000 tp-relative trap already documented and
fixed once before in `reference_accord_consistency_monitor_hardshutdown.md`'s own "CORRECTIONS"
section.** The instruction that actually gates Monitor 2, `0x44950: ld.bu 0x74a4[tp],r11`, reads
`tp+0x74a4 = 0xBF000+0x74A4 = 0xC64A4`, **not** `0xC74A4`. `read_memory` on stock `code.bin`:
`0xC64A4 = 0x00` (gate condition `==0` TRUE, armed) vs `0xC74A4 = 0xEA` (a real byte, just the wrong
address). **Monitor 2 is LIVE.** If any downstream analysis or build decision relied on "Monitor 2
dead," it needs revisiting.

## Monitor 1 — `FUN_00042af8` (int domain, the LKAS shaper function itself)

Sole caller: `FUN_0002214a` (the 1 kHz task, confirmed via `get_function_callers`). Also the producer
of `gp-0x6b98` (final LKAS torque demand — see `reference-accord-shaper-fun42af8.md`) and of the int
corridor walls `gp-0x6af6`/`gp-0x6b00`/`gp-0x6b04`/`gp-0x6b0a` that Monitor 2 independently re-derives.
**Confirmed [EVIDENCE, full-decompile grep]: FUN_00042af8 never references `gp-0x6bd0` or `gp-0x6b94`**
— it is a self-contained corridor/shaper computation, not directly sensitive to the V75 damper edit.

7 weighted fault flags (1,2,4,8,16,32,64), all `|diff|>tolerance` (magnitude) checks, summed each cycle
into `uStack_ec` (range 0-127 alone). The one tied to the actual delivered command:
```
0x43b24: ld.w -0x6dbc[gp],r12      ; float re-derived corridor edge (Monitor 2's fVar23, cross-function)
0x43b28: movhi 0x4480,r0,r17       ; 1024.0
0x43b2c: mulf.s r17,r12,r14
0x43b30: trncf.sw r14,r7           ; int(float*1024)
0x43b34: ld.h -0x6b98[gp],r15      ; gp-0x6b98 = delivered torque
0x43b38: sub r15,r7                ; diff = int(float*1024) - gp-0x6b98
0x43b3a: addi 0x5,r7,r10           ; diff+5
0x43b3e: cmp 0xb,r10 / bc 0x43b48  ; |diff|<=5 (unsigned add-5-cmp-11 idiom) -> weight=0
0x43b44: movea 0x20,r0,r25         ; else weight=32
```
Tolerance: exactly **±5 raw counts** (out of a ~10240-count-max signal).

Accumulator `gp-0x3564` (SHORT, integer units):
```
0x43ba0: ld.h -0x3564[gp],r15      ; accumulator
0x43bac: bne 0x43bc0               ; sum!=0 this cycle (fault present) -> charge path
  0x43bc0: addi -0x64,r15,r0 / bge 0x43bca   ; accumulator>=100?
  0x43bc6: add 0xa,r15              ; CHARGE: +10/cycle (if accumulator<100)
  0x43bca: addi 0x400,r6,r6         ; else: output += 1024 (guarantee-trip kicker, every such cycle)
        (else, sum==0 this cycle -- no fault)
  0x43bb0/0x43bb4: cmovle 0x0,...    ; floor accumulator at 0
  0x43bba: add -0x5,r15             ; LEAK: -5/cycle
```
Trip: `0x43d12: addi -0x81,r1,r0 / bnc 0x43d4a` — output > 128 (0x80) → `FUN_0004613e(0x38c7,...)` →
`FUN_00016de6(0x1c,...)` → DTC 0x1c/0xF00049, per the already-established hard-latch chain
(threshold=1, single-cycle, in `reference_accord_hard_shutdown_full_map_v75_incident.md`).

## Monitor 2 — `FUN_00043e44` (float domain, "corridor lockstep")

Sole caller: `FUN_0002214a` (1 kHz). Independently re-derives the SAME corridor in float and compares
against Monitor 1's int outputs — confirmed **not** an assist-aggregator re-derivation (matches
`reference-accord-fun43e44-no-assist-chain-float-twin.md`; `gp-0x6bd0`/`gp-0x6b94`/every aggregator
lane absent from this function too).

Weight-32 (the flag tied to `gp-0x6b98`), full asm:
```
0x448d6: ld.h -0x6b98[gp],r12
0x448de: nmsubf.s r14,r1,r9,r1      ; r1 = fVar23(float-recomputed corridor edge) - gp-0x6b98/1024
0x448e2: cmp r7,r1  (r7=+0.0048828125=5/1024, loaded @0x4463e movhi 0x3ba0,r0,r7)
0x448e6: movhi -0x4460,r0,r8        ; r8 = -0.0048828125
0x448ee: movhi 0x4200,r0,r12        ; fault=32.0 if |diff|>5/1024
```
`fVar23` is built from `gp-0x4f64`(governor)+`gp-0x6dac`(persisted float, producer STILL unresolved,
see `reference-accord-fun43e44-no-assist-chain-float-twin.md`)+mode-selected consensus of `gp-0x6b04`
(an EARLIER pipeline stage of the SAME `FUN_00042af8` shaper computation — pre-governor-clamp,
pre-feed-forward, pre-final-±0x2000-hard-clamp snapshot of the value that becomes `gp-0x6b98`). **It is
NOT a byte-replica of `gp-0x6b98`'s own formula** — a genuine independent (int-pipeline-stage-derived)
re-derivation, so a fast/discontinuous change in the delivered command is structurally the kind of
signal most likely to expose a transient int/float divergence, though this was NOT numerically closed
this session (see Open Questions).

State machine (`gp-0x3540` byte: 0=reset,1=armed,2=counting,3=PERMANENT LATCH), accumulator `gp-0x3550`
(float):
```
0x44950: ld.bu 0x74a4[tp],r11       ; gate = tp+0x74a4 = 0xC64A4 = 0x00 -> armed (see correction above)
State 1 (armed): gate==0 && sum>0 THIS CYCLE -> state=2; accumulator += 0.001 (0x44966 mov 0x3a83126f,r12
    = 0.001f exact); output=raw weighted sum (0-127, alone cannot trip) -> trip check.
  else (no fault or gate off): output=0; if accumulator>0, falls to shared decay block.
State 2 (counting): sum>0 this cycle:
    if accumulator>=0.01 (0x449a6 mov 0x3c23d70b,r8 = 0.01f exact): state=3; output += 1024.0
        (0x449b6 movhi 0x4480,r0,r7 = 1024.0) -> GUARANTEED TRIP.
    else: accumulator += 0.001 (continue charging); output=raw sum (no trip yet).
  sum==0 this cycle: state->1; output=0; accumulator -= 0.0005 (0x4498e mov 0x3a03126f,r16 = 0.0005f
    exact, at 0x44994 subf.s r16,r12,r8) -- LEAK, HALF the charge rate.
State 3 (latched): EVERY cycle, output += 1024 unconditionally (0x449d2-0x449da) -- permanent re-trip,
  matches the outer FUN_00018738 hard-latch (threshold=1, gp-0x685c=1, no reset path but power-cycle).
```
Trip: `0x44a26: movhi 0x4300,r0,r12` (128.0) `/ 0x44a2e: cmp r12,r7 / bgt 0x44a3e` → `FUN_000462e6
(0x3f1b, word, 0, 128.0)` → `FUN_00016de6(0x1d,...)` → DTC 0x1d/0xF00049.

## Cross-monitor structural findings [EVIDENCE]

1. **Charge:leak ratio is 2:1 in BOTH monitors** (Monitor 1: +10:-5 int; Monitor 2: +0.001:-0.0005
   float) — a consistent firmware design pattern, not coincidence.
2. **Break-even duty = 1/3, exactly**, from `0.001*d - 0.0005*(1-d) = 0` (or the integer equivalent).
   Below 1/3 duty (fraction of 1 kHz cycles with `sum>0`) the accumulator loses net ground on average;
   above it, drifts toward the trip threshold (~10 cycles at 100% duty, ~40 at 50% duty).
3. **Sign-alternation does NOT cancel** [EVIDENCE]. Every one of the 7 weight flags in both monitors is
   a bilateral `diff>+tol OR diff<=-tol` (i.e. `|diff|>tol`) test. The accumulator only ever asks
   "is `sum(flags) > 0` THIS cycle" — never a signed running total. A relay alternating sign trips the
   same flags with the same magnitude regardless of polarity.
4. **No minimum-duration gate** [EVIDENCE]. A single isolated 1 kHz-cycle excursion (`gate==0 && sum>0`
   that one cycle) charges the accumulator exactly like the first cycle of a sustained fault — there is
   no "must persist N cycles" precondition in either state machine.
5. Both monitors run at **1 kHz** (`FUN_0002214a`, confirmed via `get_function_callers`) — same task
   as `FUN_00045a20`/`FUN_000456a4`/`FUN_00070a98`'s caller `FUN_0006bcb2`.

## `FUN_00070a98` (DTC 0x26, commanded-vs-achieved delivery consistency) — structural only, NOT
byte-resolved this session

Sole caller `FUN_0006bcb2` → `FUN_0002214a` (1 kHz, confirmed). Decompile shows a lateral-dynamics
model (cos/sin LERP on steering angle, gains ~0.9-1.1 depending on a consensus ratio) producing a
residual, integrated through two accumulators (`gp-0x2880`, `gp-0x2884`) with what reads as a leaky
structure (thresholds via what Ghidra renders as `DAT_00006050`-`DAT_00006064`-style symbols added to
`unaff_tp`, i.e. probably `tp+0x60xx` = `0xC5000`-block cal cells — **NOT verified against `tp=0xBF000`
arithmetic this session**, flagged open). Explicit `FUN_0005ae6a(0x26,...)`/`FUN_0005afba(0x26,...)`/
`FUN_0005b650(0x26,...)`/`FUN_0005bb04(0x26)`/`FUN_0005b68c(0x26,...)` calls confirm this is the DTC 0x26
delivery-consistency monitor. Deprioritized mid-session by the operator/coordinator in favor of Monitor
2; not swept to instruction level. If prioritized later: resolve the `DAT_0000605x`/`DAT_0000606x`
symbols against `tp+0x605x` before trusting any threshold value (same off-by-0x1000 risk as the Monitor
2 gate above).

## Related
[[reference_accord_hard_shutdown_full_map_v75_incident]] (per-DTC latch table, DTC 0x1c/0x1d both
single-cycle hard-latch eligible) · [[reference_accord_gp6bd0_shadow_faultpath_0x4179_0x417a]] (the
gp-0x6bd0-adjacent FUN_00034350/FUN_000347b8 pair, a DIFFERENT monitor, already closed this session by
another agent per the redirect I received — FactorE's own LERP has no headroom past X[3]=4000, supremum
of the raw product = 512 = the ceiling's own floor, unreachable regardless of gp-0x6ac2 timing).

## Open questions
1. **Does weight-32 (or any of the 7 flags) actually exceed tolerance during a real relay transition or
   plateau dwell?** Not numerically closed — needs either `gp-0x6dac`'s producer resolved + a byte-exact
   simulation of `fVar23` vs `gp-0x6b98` through one relay step, or telemetry of the fault-flag/
   accumulator state during the incident.
2. **Rolling-window duty, not global average**: route-5d's global plateau-occupancy (V74 7.53%, V75
   15.08%, both below the 1/3 break-even) is NOT dispositive by itself — the accumulator is sensitive to
   LOCAL bursts. V75's structure (282 entries/10ms median dwell = chattering) vs V74's (35 entries/210ms
   = settled) could produce local rolling-window duty spikes above 1/3 even with a low global average.
   Needs a fine-grained (≤1 kHz-equivalent) time series, not a 28s-window average.
3. Confirm route-5d's actual sample rate — "median dwell = one tick = 10ms" implies ~100 Hz logging,
   which is 10x coarser than Monitor 2's 1 kHz evaluation cadence; conflating the two "ticks" would
   misstate the duty arithmetic by up to 10x.
