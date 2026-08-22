---
name: reference_accord_fun352b4_clamp_address_map_and_biquad_output_target_resolved
description: Instruction-address map for every clamp in FUN_000352b4's Path-1 chain (gp-0x4f60 through gp-0x6b86), produced for a safety-gate audit of a proposed 0xC60A8/AC/B0/B4 biquad-coefficient boost. Resolves which value the +-12.0 float clamp targets (the FULL notch output y[n], symmetric BOTH bounds -- refutes an independent trace's "half-clamp" misread) and quantifies exactly when a c4-only boost starts clipping it (linearly, starting immediately above k=1.0, since stock's own margin is already ~0%). Proves gp-0x6b82's magnitude is bounded by a min() against gp-0x6b7a. CORRECTS an own first-pass lowball: the gp-0x6b7e pedestal (added AFTER the biquad, before the SECOND +-0x3000 clamp) is NOT negligible -- worst-case bound ~+-12288, same order as the whole second clamp. Also maps the DTC escalation chain (FUN_00045a20/FUN_0004613e/FUN_000462e6/FUN_00043e44) and proves FUN_00045a20's checked delta is ALGEBRAICALLY blind to gp-0x6b86/gp-0x6b94 by construction. Confirms the shadow-lockstep fault class (FUN_0006b9fa -> FUN_0006ce7c(4)) is structurally unreachable by any cal-only coefficient edit, and that gp-0x4cde (gp-0x6b86's shadow) is fully self-contained like its sibling pairs. ROUND 3 (2026-08-22): confirms address-pinned that c4 is read/used EXACTLY ONCE (0x35a30/0x35a3c) and gp-0x6b7e has ZERO dependency on it anywhere; gp-0x6b7e's EMA target is gated to exactly zero unless the friction-hold clamp is biting; corrects an own same-session "several seconds" residual-decay guess to the real figure (alpha=20/2048 fixed, 469ms to 1%, 960ms worst-case full clearance), cross-checked against the flat-LERP byte-read in reference_accord_biquad_is_a_notch_v103_armed_and_recentering_priced_short.md.
metadata:
  type: reference
---

Found 2026-08-21, `safety-gates` subagent task (team-lead orchestrated), auditing a proposed cal-only
boost of the dormant biquad's coefficients (`0xC60A8/AC/B0/B4`, armed engaged-only by V103's
`gp-0x671a`->`gp-0x6806` repoint). Program: stock `code.bin` only (confirmed via `list_open_programs`).
Fresh `decompile_function`+`disassemble_function` on the WHOLE of `FUN_000352b4` (`0x352b4-0x35b1c`),
cross-checked with `search_instructions` (full base-register adjudication) and a from-scratch numpy
transfer-function derivation. Extends [[reference_accord_fun352b4_full_chain_gp6b82_tap_and_c6200_shared_clamp]]
(which had the structural chain but not exact addresses for every clamp or the clamp-target resolution
below) and [[reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm]].

## Full clamp address map [EVIDENCE, one disassembly pass, all addresses below read directly]

```
gp-0x4f60 -> clamp +-cal(0xC6200)=+-8192      [0x354ce-354f4, INNER clamp]
  -> + gated gp-0x6b4a (zero-gate 0x354f6-35504, currently passes 0)
  -> clamp +-0x6400=+-25600                    [core 0x3550a-3551c, abs 0x35520-35526]
  -> 10-pt LERP gp-0x37fc[]/gp-0x37e8[]         [0x35528-355a4]
  -> xsign x polarity(gp-0x6752) x min(.,0x3000) [0x355d4-35606; STORE gp-0x6b7a @0x355fe,
                                                    shadow gp-0x4cdc @0x35602, mismatch->FUN_0006b9fa@0x3560c]
  -> friction-hold 2nd stage (min-bound, see below) -> STORE gp-0x6b82 @0x358dc
  -> gate cal(0xC649B)==1 AND cal(0xC64FA)<=gp-0x671a  [test 0x35a0c-35a26]
       ARMED: recursion 0x35a28-60, float clamp +-12.0 @0x35a54/70, state stores @0x35a64/6a (UNCLAMPED)
       DISARMED: 0x35a86 `mov r10,r6` = passthrough of the SAME gp-0x6b82 int value
  -> + gp-0x6b7e (gp-0x381c IIR term)
  -> clamp +-0x3000=+-12288                     [0x35a8c-35aa0]
  -> extreme-torque dropout test (raw gp-0x4f60 vs ~+-25600) [0x35aac-35aba]
  -> STORE gp-0x6b86 @0x35ac0 (normal) / 0x35ace (dropout=0); shadow gp-0x4cde; mismatch->FUN_0006b9fa@0x35ade
```

## gp-0x6b82 is provably bounded by gp-0x6b7a's own magnitude [EVIDENCE, instruction-level]

`0x358bc: cmovge r10,r6,r6` computes `r6 = min(r10=|gp-0x6b7a|, clamp(candidate,0x3000))`; the OTHER
branch (`0x358d0 cmovne r8,r12,r10`) stores `gp-0x6b7a` (r12) directly when the friction-hold branch
isn't taken. **Both branches satisfy `|gp-0x6b82| <= |gp-0x6b7a| <= 0x3000=12288` by construction** — the
friction-hold stage (a SEPARATE breakpoint search over `local_44`/`local_58`, cal/RAM block
`gp-0x644x`/`gp-0x647x`, physical meaning not re-derived) is a pure attenuator, never an amplifier. So the
CERTAIN worst-case ceiling on the biquad's input is `12287/1024 = 11.999023` float units, independent of
what the ROM assist-map table actually contains (that table's real, likely-lower, max Y was NOT
re-derived this session — see [[reference_accord_assist_map_rom_source_found_and_shares_stage2_fork]]'s
own "Open item 1", still open).

## 🛑🛑 The +-12.0 float clamp targets y[n] (the FULL notch output), NOT the raw pole-only state — and the two differ by 8.5x

```
00035a5c: maddf.s r12,r11,r13,r9     ; r9 = x2'_new + c3*x2_old
00035a60: addf.s r9,r16,r8           ; r8 = fVar38 = x1_old + c3*x2_old + x2'_new = y[n]  <- CLAMPED
00035a64: st.w r11,-0x3814,gp        ; x1_new = x2_old            <- UNCLAMPED
00035a6a: st.w r13,-0x3818,gp        ; x2_new = x2'_new (raw pole state) <- UNCLAMPED
```
Fresh numpy (exact stock coeffs `c1..c4`=-1.5372/0.63462/-1.8808/0.81731): the FULL response
`H(z)=c4*(1+c3 z^-1+z^-2)/(1+c1 z^-1+c2 z^-2)` is flat, peak `|H|`=1.000034 (+0.0003dB) at DC, notch null
at 55.225Hz — matches [[reference_accord_biquad_is_a_notch_v103_armed_and_recentering_priced_short]]
exactly, resolving what looked like a self-contradiction against the loop-lag-map's monotonic-roll-off
table (both are the SAME response; the "peak" is just at DC/0.01Hz, outside the 7-42Hz range that table
tabulates). **The PURE POLE-ONLY response** (`x2'` alone, i.e. `c4/(1+c1 z^-1+c2 z^-2)`, no zero) **has an
8.5x (+18.6dB) resonant peak at 22.7Hz** — had the clamp targeted the state instead of `y[n]`, this would
be a serious headroom risk; it doesn't, so it isn't. `gp-0x3814`/`gp-0x3818` themselves are float32,
dynamic range ~1e38 — unclamped state is not a numeric-safety issue at these physical magnitudes.

**Quantified clip onset for a boost of c4 by k (poles/zeros unchanged => `H_k=k*H_stock` exactly, at every
frequency, confirmed):** stock (k=1) full-scale-input theoretical max `|y|`=11.999, i.e. **stock is
ALREADY at ~100% of its own +-12.0 margin in the worst case.** Overshoot scales linearly:
k=1.25 -> 25.0% over : k=1.5 -> 50.0% over : k=2.0 -> 100.0% over (double the ceiling). Overshoot is
concentrated at LOW frequency/near-DC (`|H|` at k=1.25 is 1.229 @7.8Hz but only 0.983 @26Hz) — i.e. the
clipping risk is on sustained large low-frequency torque (hard turns, parking), NOT the 6-9/20-26Hz bands
this kit instruments. `gp-0x6b82` (write-only, confirmed no other reader) is the natural telemetry tap to
measure real headroom before choosing k, since no real on-car data exists (biquad has only ever run
armed with STOCK coefficients, V103).

## Lockstep fault class is structurally immune to a coefficient-only edit [EVIDENCE]

`FUN_0006b9fa(param_1): *(gp-0x4d6c)=param_1; FUN_0006ce7c(4); return;` — fixed index 4, fires on ANY
mismatch between a shadow pair. Both halves of every pair (incl. `gp-0x6b86`/`gp-0x4cde`,
`gp-0x6b7a`/`gp-0x4cdc`) are written by the SAME atomic instruction pair inside `FUN_000352b4`
(e.g. `0x35ac0`+`0x35ac4`) — a coefficient edit changes the VALUE flowing into that write, never the
write-both sequence, so this fault class cannot be tripped by S1/S2-style edits. Same fixed-index
pattern as `FUN_0006b9ee`->`FUN_0006ce7c(0x17)` (the `gp-0x4f64`/`gp-0x448a` pair) already on record in
[[reference-accord-fun45a20-monitor-and-shadow-lockstep-pairs]] — different index, same mechanism class.

## GATE 1 re-confirmed, third independent pass [EVIDENCE]

`gp-0x3814`/`gp-0x3818`: exactly 2 accesses each (1 read+1 write), both fresh-disassembly AND
`search_instructions` (adjudicated: 11 raw "3814" hits -> 2 real + 9 false positives, mix of tp-relative
collision and branch/jarl-target substring collision; 3 raw "3818" hits -> 2 real + 1 false positive)
agree exactly with each other and with
[[reference_v850_search_instructions_base_register_collision_trap]]'s prior-session result. `gp-0x6b86`:
4 real touches (3 in `FUN_000352b4`, 1 in `FUN_0003aa2c` the sole reader). `gp-0x6b82`: 1 real touch (the
write itself) — genuinely write-only, zero other consumers, confirmed clean telemetry tap.
`get_xrefs_to` on all 4 absolute addresses returned "No references found" on every one — a known
false-zero on this kit for gp-relative RAM cells, not relied on for any of the above.

## G5/governor link re-confirmed fresh, extends to the EME question [EVIDENCE for the FUN_0004503c half]

Fresh `decompile_function(0x4503c)`: `iVar7 = FUN_00049a90(gp-0x6b94, -((gp-0x4f64*uVar17)>>15))` —
confirms the retracted-ceiling replacement mechanism in `docs/STATE.md`/commit `66f40ef` exactly
(proportional, motor-rate-scheduled governor bound on the aggregator sum that `gp-0x6b86` feeds).
Since `gp-0x6ace` (this function's output) is on record (my own prior-session EME memory,
[[reference-accord-override-snap-state-machines]]) as feeding `gp-0x6acc` -> the EME integrator's
"command" input, **a boosted `gp-0x6b86` has a structural path to wind the EME integrator faster, but
its magnitude contribution is bounded by the SAME motor-rate-collapsing ceiling as G5** (peaks 5325,
collapses to 512) — it can increase DUTY near that ceiling, not exceed a new peak. Did not compute a
numeric time-to-arm change; that needs current (6x-era) telemetry, not static reading.

## 🛑🛑 CORRECTION (same task, round 2): the +-12.0 clamp IS symmetric — refutes a "half-clamp" claim

An independent trace reported `0x35a68-35a80` as floor-only (`maxf.s` against -12.0, "no ceiling check in
this snippet"). **Wrong** — re-traced register `r10` across the branch: `0x35a54 movhi 0x4140,r0,r10` sets
r10=12.0; `0x35a68 cmp r10,r8; 0x35a6e bgt 0x35a78` branches AROUND the `movhi -12.0`/`maxf.s` pair
(`0x35a70-74`) whenever `fVar38(y[n]) > 12.0`, in which case r10 is NEVER overwritten and STILL holds
12.0 when read at `0x35a7c`. **The ceiling is the branch-around leaving the earlier default in place, not
a second explicit instruction** — a snippet-only read of 0x35a68-80 without carrying r10's value in from
0x35a54 will misread this as floor-only. Verified 3 ways: (1) this manual trace, (2) Ghidra's own
decompiler independently collapsed the same logic to
`fVar22=12.0; if(fVar38<=12.0){fVar22=max(fVar38,-12.0);}` (both bounds explicit, already in hand from
round 1 of this same session), (3) hand-rederived the exact signed-overflow-safe compare idiom Ghidra
rendered and confirmed it correctly implements `fVar38<0x41400000(=12.0 bits)` for both positive and
negative fVar38. **Consequence: no asymmetric-clamp/rectification/DC-injection mechanism exists here** —
both this clamp and the downstream `+-0x3000` integer clamp (`0x35a8c-a0`, plain two-sided
`addi`/`ble`/`addi`/`bge`, unambiguous) are genuinely symmetric. The failure mode under a c4 boost is
flat-topping (odd-symmetric), matching the already-quantified linear 25/50/100% overshoot at k=1.25/1.5/2.0.

## 🛑🛑 CORRECTION (round 2): `gp-0x6b7e` pedestal is NOT negligible — own first-pass estimate was wrong

`search_instructions("6b7e")`: 3 raw hits, 1 real (`0x35a1e`, the sole write) + 2 false positives
(branch-target text collisions). **Confirmed zero readers anywhere** (matches an independent trace's
claim). But its MAGNITUDE bound, carefully re-derived (own first pass under-estimated this):
```
iVar33 = clamp(gp-0x6b7a - sVar15_frictionhold, +-0x3000)   ; difference of two |.|<=12288 quantities
iVar33 = iVar33 * bVar3                                       ; zeroed if friction-hold branch didn't fire
iVar20 = iVar33 << 7                                          ; IIR TARGET, bounded +-(12288*128)=+-1,572,864
iVar24 += (iVar20-iVar24)*iVar27 >> 0xb                        ; EMA (alpha=iVar27/2048 in [0,~0.0996])
                                                                ; -> gp-0x381c bounded to the SAME range as target
iVar14 = deadband(iVar24, +-0x80)
gp-0x6b7e = iVar14 >> 7                                        ; undoes the <<7 -> back to +-~12288
```
**Theoretical worst case `|gp-0x6b7e| ≲ 12288` — the SAME order of magnitude as the WHOLE second-stage
+-0x3000 clamp**, not a small pedestal as first assumed. It is added to `k*y[n]*1024` BEFORE the second
clamp (`0x35a88 add r15,r6`), so it competes for the SAME headroom the boost is spending. Does NOT change
the FIRST clamp's (±12.0 on y[n] alone) already-quantified overshoot table — that stage is earlier and
gp-0x6b7e hasn't entered yet. DOES mean the second clamp's true stock margin is uncertified — `gp-0x6b7e`
and the (possibly boosted) biquad term share upstream lineage (both descend from `gp-0x6b7a`) so are NOT
independent, and whether their individual maxima are reachable simultaneously is unresolved without either
a coupled-dynamics sim or telemetry. **Recommend telemetering `gp-0x6b7e` alongside `gp-0x6b82`** (both
write-only, zero other consumers, same cave tap) before choosing any k>1.

## DTC escalation chain, fully mapped [EVIDENCE, 4 fresh decompiles this round]

```
FUN_00045a20 (comp-term band monitor) --out-of-band--> FUN_000462e6(0x3a09,...)
FUN_00043e44 (Monitor2, ~150-line aggregate classifier) --sum>=128--> FUN_000462e6(0x3f1b,...)
  FUN_000462e6(idx,...):  ALWAYS FUN_00016de6(0x1d,idx,1,1)  [unconditional, no debounce in this fn]
                           + IF a before/after diagnostic-snapshot (tp-0x5604/tp-0x5600) differs:
                             also FUN_0004613e(0xffff,...)
                               FUN_0004613e: ALWAYS FUN_00016de6(0x1c,param_1,1,1)  [6 lines, trivial,
                                             separately also the escalation for Monitor1's gp-0x3564
                                             accumulator inside FUN_00042af8 -- NOT specific to FUN_00045a20]
```
**`FUN_00045a20`'s checked quantity `(gp-0x6acc-gp-0x6ace)/1024` is ALGEBRAICALLY EQUAL TO `comp_term`
by construction** (since `FUN_000456a4` defines `gp-0x6acc = gp-0x6ace + comp_term` in the SAME tick,
confirmed no intervening writer, per
[[reference_accord_fun456a4_signed_term_and_fun45a20_mismatch_refuted]]) — `gp-0x6ace`'s own value
cancels out of the subtraction regardless of magnitude, so **this monitor is structurally blind to
`gp-0x6ace`/`gp-0x6b94`/`gp-0x6b86` — not a "margin is wide enough" result, a "the checked signal
provably excludes this lane" result.**

`FUN_00043e44` (Monitor2) inputs, scanned the full decompile for `6b86`/`6b94` — **neither appears**.
Confirmed inputs: `gp-0x4f60`/`gp-0x6b4a`/`gp-0x6bf0` (silently zeroed if `|.|>25600`), `gp-0x6acc`
(silently zeroed if `|.|>8192` — the one input that DOES carry Path-1's governed contribution
indirectly, via the aggregator/governor chain), `gp-0x4f64` (zeroed if `>=10240`), `gp-0x6af6`/`gp-0x6b00`/
`gp-0x6b0a`/`gp-0x6b04`/`gp-0x6b98` (compared, not obviously sanitized the same way). Each contributes a
power-of-2 bit (1,2,4,8,16,32,64) to a debounced accumulator; raw per-cycle bits max at 127 (<128), so a
single cycle can never trip the `>=128` escalation threshold alone — requires the accumulator's own
multi-cycle state machine (`gp-0x3540`/`gp-0x3550`) to reach state>=2 and add a fixed +1024 penalty. One
term (the `32`-weight bit) compares `gp-0x6b98` against a locally-reconstructed reference built from
`gp-0x4f64`+polarity — traced far enough to see it's a self-consistency check, not an absolute-magnitude
test, but NOT traced back far enough to state its sensitivity to a boosted Path-1 — flagged open.

## `gp-0x4cde` (shadow of gp-0x6b86) is fully self-contained [EVIDENCE]

`search_instructions("4cde")`: 8 raw hits, 4 real (all inside `FUN_000352b4`: `0x35aa8` read,
`0x35ac4`/`0x35ad4` writes, `0x35ada` addr-calc for `FUN_0006b9fa`), 4 false positives (branch/jump-target
text collisions elsewhere). Zero external readers/writers — same self-contained pattern as the sibling
pairs (`gp-0x4cc8`, `gp-0x4ce0`). Combined with the atomic write-both proof already in this file: a
cal-only coefficient edit cannot desynchronize it.

## 🛑🛑🛑 ROUND 3 (2026-08-22, `feel-impact` task, V104 steering-feel quantification): c4 CONFIRMED to touch gp-0x6b7e NOWHERE, and its EMA rate is FIXED not adaptive

Fresh `decompile_function`+`disassemble_function(0x352b4)` again this session (3rd independent pass on
this exact function), specifically to settle whether `gp-0x6b7e` dilutes a `c4` boost. **Confirmed,
address-pinned, both branches:**

```
0x359e0-0x35a1e   gp-0x6b7e computed + STORED (st.h r15,-0x6b7e[gp] @0x35a1e) — BEFORE the arm-gate
                  check even runs. Zero dependency on tp+0x70b4 (c4) or any of the 4 biquad coeffs.
0x35a0c-0x35a26   ARM GATE (cal 0xC649B==1 && cal 0xC64FA<=gp-0x671a).
0x35a30           c4 LOADED (ld.w 0x70b4[tp],r9) — the ONLY place c4 is read in the whole function.
0x35a3c           mulf.s r9,r14,r12 — c4 multiplies ONLY u[n] (gp-0x6b82/1024). SOLE use of c4.
0x35a86           DISARMED fallback: r6 = raw iVar34 (=gp-0x6b82), c4 never read on this branch either.
0x35a88           add r15,r6 — gp-0x6b7e(c4-independent) + biquad-or-passthrough(c4-scaled-or-raw).
```
So boosting `c4` (V104's ONLY edit, confirmed via `build_v104_tva.py`: 0xC60B4 alone,
0.81730998f->1.51202345f, pure coefficient swap, no cave/control-flow change — this stock-image trace
transfers to V104 unmodified) rescales ONLY the biquad term; `gp-0x6b7e` is invariant to it.

**NEW: `gp-0x6b7e`'s EMA target is gated to EXACTLY ZERO unless a separate "friction-hold" min-clamp is
actively limiting the signal upstream.** `bVar3` (@0x35892-98) fires when a friction-hold ceiling table
(indexed by raw input-torque magnitude, cal/RAM block `gp-0x644x`/`gp-0x647x`) is LESS than
`|gp-0x6b7a|` (the assist-map's own output before friction-hold). When that clamp is slack — i.e. the
assist-map output isn't exceeding the friction-hold ceiling — the EMA target is 0 and `gp-0x6b7e` decays
toward 0 (settles to EXACTLY 0 once the accumulator `gp-0x381c` is within +-128 of zero, its own
x128-prescaled domain). **In that regime essentially 100% of `gp-0x6b86` is the c4-scaled biquad term.**
Physical meaning of the friction-hold table itself (what axis, what real torque threshold) NOT
re-derived this session — same open item as `fun352b4_full_chain_gp6b82_tap`'s note.

🛑 **CORRECTS my own "worst case ~several seconds" residual-decay guess from earlier the SAME session**
(before finding the table below) — the real number is much faster. `gp-0x6b7e`'s EMA rate is driven by a
breakpoint search (0x3595e-0x359ba, over `tp+0x78fe..0x790c` = `0xC68FE..0xC690C`) that
`reference_accord_biquad_is_a_notch_v103_armed_and_recentering_priced_short.md` §6 already byte-read as
**FLAT**: `read_memory(0xC68FC,32)` → count=4, X=[0,9830,26214,32768], Y=[20,20,20,20]. So the EMA rate is
**FIXED at alpha=20/2048=0.009766** (not the adaptive [2,204]/2048 the raw disassembly's clamp bounds
alone would suggest — those bounds are just the static ceiling on an always-flat table). Computed this
session (Python, exact): **time to decay to 1% of any starting excursion = 469 ms; worst-case full
clearance from the theoretical max excursion (+-12288 pre-shift, +-1,572,864 in the x128 domain) into
the +-128 deadband = 960 ms.** So a residual pedestal from a friction-hold-limited maneuver clears in
under a second, not "several seconds" as I first guessed.

**Practical read for any future `c4`-family lever**: in ordinary driving away from the friction-hold
ceiling, `gp-0x6b7e` does NOT dilute a `c4` boost — it is a genuine but narrow-duty bypass, active only
during/shortly after friction-hold-limited maneuvers (hard turns, parking, curb contact), decaying out
within ~0.5-1s.

## Related
[[reference_accord_fun352b4_full_chain_gp6b82_tap_and_c6200_shared_clamp]] — the structural chain this
extends with exact addresses. [[reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm]]
— original pole find, ζ/Q numbers unaffected by anything here.
[[reference_accord_biquad_is_a_notch_v103_armed_and_recentering_priced_short]] — the notch
characterization this session's fresh derivation matches exactly (and resolves an apparent
self-contradiction in, not a real one). [[reference_accord_gp671a_shared_starved_gate_biquad_and_r24r26]]
— V103's arm repoint this audit's gate condition assumes. [[accord-c407e-is-the-fault-interlock-c63a0-exonerated]]
— confirms 0xC407E is on gp-0x6b26, a different lane, not re-verified this session.
