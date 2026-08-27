---
name: reference-accord-v48b-monitor1-dtc1c-notch-safety-closed
description: CLOSES the open item in reference-accord-v48b-repoint-asymmetry-review — traced gp-0x6af8/gp-0x6afa through FUN_00042af8's corridor-wall computation to the terminal DTC-0x1c trip compare; verdict SAFE, matched int/float shadow computation, not a magnitude gate.
metadata:
  type: reference
---

2026-07-21 session, stock `code.bin`, GhidraMCP only (`decompile_function` on `FUN_00042af8`@0x42af8 and
`FUN_00043e44`@0x43e44, both returned in full — 0x42af8 is ~1420 decompiled lines / large but did NOT
truncate this time; corroborated with `disassemble_bytes dry_run:true` at every load-bearing address and
`search_instructions` for two exact-match cal/variable xref counts). Closes the open item flagged in
[[reference-accord-v48b-repoint-asymmetry-review]] ("did not trace how far downstream the debounced
`gp-0x6af8` state ultimately sets the corridor arm's final width fed into the integrator wind-up compare
... `FUN_00042af8` is too large for one decompile call").

## Verdict: SAFE. The DTC-0x1c trip is a matched int/float SHADOW-COMPUTATION lockstep, not a magnitude/
upper-bound gate, and V48B's notch perturbs BOTH sides of every relevant comparison identically.

## The terminal mechanism (FUN_00042af8, DTC 0x1c via integrator `gp-0x3564`)

`gp-0x6af8` (raw-only term, `st.h r14,-0x6af8[gp]`@**0x42c3a**) and `gp-0x6afa` (clamped raw+cal-gated-
mixer sum, `st.h r22,-0x6afa[gp]`@**0x42c62**) are built at 0x42be0-0x42c6e: raw driver torque `gp-0x4f60`
(`ld.h -0x4f60[gp],r16`@0x42c20) range-checked to ±25600, PLUS (only if cal `tp+0x74cb`==1,
`ld.bu 0x74cb[tp],r7`@**0x42c12**, abs **0xC64CB**) the type-8 mixer output `gp-0x6b4a`
(`ld.h -0x6b4a[gp],r7`@**0x42bf6** — the exact carrier V48B's notch perturbs, via the repointed
`FUN_0002c478` feeding the mixer). `gp-0x6afa` feeds a LERP (keyed on the clamped sum) whose output blends
through a polarity-select (`gp-0x6752`) into `iVar27`/`iVar38`, which get written as the "wall"
`gp-0x6af6`/`gp-0x6b00` at **0x43213/0x43215** (decompiled store sites, byte-identical to the segment-E
memory's gate 7-9 corridor/IIR/boost max chain).

**Monitor-1's actual trip compare (0x43172-0x4318e, freshly disassembled):**
```
0x43172  ld.w   -0x6db0[gp], r8      ; float dir1 mirror (written by FUN_00043e44)
0x43176  movhi  0x4480, r0, r17      ; 0x44800000 = 1024.0f
0x4317a  mulf.s r17, r8, r10         ; r10 = float_mirror * 1024.0
0x4317e  trncf.sw r10, r12           ; truncate to int
0x43182  ld.h   -0x6af6[gp], r6      ; int wall (this cycle, computed above)
0x43186  ld.w   -0x6db8[gp], r10     ; float dir2 mirror
0x4318c  sub    r6, r12              ; delta = float_scaled - int_wall
0x4318e  addi   0x5, r12, r15        ; delta+5 (unsigned-wrap ±5 tolerance idiom)
```
This is a **shadow-computation agreement check** (int wall vs float twin, tolerance ±5 counts /
±0.0049 normalized), not a comparison of the wall against a fixed cal ceiling or against the delivered
command's magnitude.

**Full fault word** (decompiled 0x42af8 lines ~1194-1303, all 7 bits, max 127):
| bit | compares | gp-0x6b4a-dependent? |
|---|---|---|
| 1 | float `gp-0x6db0` vs int `gp-0x6af6` | YES — both sides |
| 2 | float `gp-0x6db8` vs int `gp-0x6b00` | YES — both sides |
| 4 | float `gp-0x6dc0` vs int `gp-0x6b0a` (=\|authority integrator\|) | no (authority-domain) |
| 8 | int `gp-0x6b04` (self, prior cycle) within [`gp-0x6b00`-5,`gp-0x6af6`+5] | indirectly, both operands share upstream lineage |
| 16 | shadow-pair `iVar45` vs `gp-0x6b08` (RAM-integrity self-check) | matched by construction |
| 32 | float `gp-0x6dbc` vs int `gp-0x6b98` (the DELIVERED MOTOR COMMAND) | YES — both sides (downstream of everything) |
| 64 | float `gp-0x6c84` vs saved int `gp-0x6966`/`gp-0x3566` (authority) | no (authority-domain) |

Integrator: `sVar24=*gp-0x3564`; if fault-word==0 → decay -5/cyc (floor 0, also -5 extra on the falling
edge); elif `sVar24<100` → **+10/cyc**; else → report bit `+0x400`. Store gated by cal `tp+0x74ca`
(0xC64CA, enable byte, ≠0 forces the integrator to 0/disabled). Trip: `if (0x80 < uStack_ec)` (report
word, only exceeds 128 once the integrator has already saturated ≥100 over ~10 cycles AND ≥1 fault bit
is still live this cycle) → **`FUN_0004613e(0x38c7,&uStack_ec,...)`** → decompiled body:
`FUN_00016de6(0x1c,param_1,1,1)` — confirms CLAUDE.md's DTC-0x1c chain exactly, fresh this session.

## The cross-function matched-shadow proof (the load-bearing evidence)

`FUN_00043e44` (the OTHER monitor, DTC 0x1d) independently computes the FLOAT twin of the exact same wall.
Its decompile (full function, no truncation) shows, in order: raw `gp-0x4f60` range-checked to ±25.0 →
`fVar16`; `gp-0x6b4a` range-checked to ±25.0 → `fVar9`; **`fVar26 = fVar16; if (*(char*)(tp+0x74cb)==1)
fVar26 = fVar16+fVar9;`** — the FLOAT-domain sibling of the int side's exact same sum, gated by the exact
same cal byte. Instruction-verified:
```
0x43f64  ld.bu  0x74cb[tp], r12      ; SAME cal read as the int side's 0x42c12
0x43f68  cmp    0x1, r12
0x43f6a  bne    0x43f72
0x43f6c  addf.s r6, lp, r10          ; r10 = mixer_term(range-checked) + raw_term(range-checked)
```
`search_instructions operand_pattern=74cb` returns **exactly 2 matches program-wide**: `0x42c12`
(`FUN_00042af8`, int side) and `0x43f64` (`FUN_00043e44`, float side). No third or alternate path exists.
This clamped sum flows into a LERP (`fVar26`) that eventually blends into `fVar8`, which
`FUN_00043e44` stores to `gp-0x6db0` and `gp-0x6db8` (`fVar28*fVar33`) at its own tail (**0x449e8-0x44a30**,
freshly disassembled: `st.w r9,-0x6dbc,gp`@0x44a22, `st.w r10,-0x6dc0,gp`@0x44a2a,
`st.w r20,-0x6db8,gp`@0x44a30 — plus the `movhi 0x4300,r0,r12`@0x44a26/`cmp r12,r7`@0x44a2e/
`bgt 0x44a3e`@0x44a34 sequence, confirming this is ALSO exactly gate 16's DTC-0x1d 128.0-threshold trip,
independently re-verified this session).

`search_instructions` on `6db0`/`6db8`/`6dbc`/`6dc0` each return exactly 2 hits program-wide: one write in
`FUN_00043e44`, one read in `FUN_00042af8` (the reverse holds for `gp-0x6b04`: 2 writes in `FUN_00042af8`,
1 read in `FUN_00043e44`). **Every cross-monitor variable is single-writer/single-reader across exactly
these two functions** — a clean, exhaustively-confirmed producer/consumer pair, not a fan-out that could
hide a third, unmatched path.

## Answers to the three questions

1. **Must-track / shadow-agreement condition, NOT a magnitude/upper-bound gate.** The compare is
   "does the int computation of the wall agree with an independently-coded float computation of the same
   formula," not "does the wall/command exceed a threshold."
2. **Both sides of every `gp-0x6b4a`-relevant bit (1, 2, 8, 32) derive from the SAME `gp-0x6b4a` memory
   cell through the IDENTICAL cal-gated (`0xC64CB`) combine formula**, replicated in two datatypes by
   design — not one side raw/notched and the other side an independent un-notched recomputation. This is
   the same "matched, not V27-class-asymmetric" pattern the prior review validated for the type-8 lockstep
   (Q1) and the damper/boost mux (Q2). Bits 4 and 64 are authority-domain and don't touch `gp-0x6b4a` at
   all.
3. **No realistic path to increased wind-up.** (a) A shared-input perturbation cannot by itself erode
   int/float agreement — int and float arithmetic on the SAME sampled value still agree to their normal
   rounding envelope (≪ the ±5-count tolerance) regardless of what that value numerically is. (b) The
   producer/consumer relationship between the two monitors carries a genuine ~1 control-tick
   (~1 ms @ ~1 kHz) latency baked into STOCK firmware (float candidate frozen at tick N, checked against
   int wall computed at tick N+1) — orthogonal to V48B. Since the notch strictly ATTENUATES (up to −8 dB,
   no passband peaking in a well-formed 2nd-order notch) the 21 Hz content flowing through the single
   `gp-0x6b4a` cell, the per-tick delta at 21 Hz can only shrink relative to stock, never grow — a
   sinusoid's peak derivative scales linearly with amplitude at fixed frequency, so attenuating amplitude
   strictly attenuates the worst-case one-tick swing this tolerance has to absorb.

## Open items (not full closure, but low residual risk, explicitly flagged rather than asserted)

- Bit 8's exact int-domain self-consistency formula (`gp-0x6b04` vs prior-cycle wall ±5) was read from the
  decompiler, not independently re-derived instruction-by-instruction the way bits 1/2/32 were — flagged,
  not verified to the same standard. Low risk: both operands still trace to the same upstream corridor
  pipeline (no raw-vs-filtered split found), so even unverified in full instruction detail it does not fit
  the asymmetry pattern.
- The notch's frequency-response claim ("unity at DC, ≤8 dB attenuation at 21 Hz, no peaking") is taken as
  design input from the V48B handoff/design doc (`studies/models/eps_v48b_notch_design.py`), not re-derived in this
  session — this tracer verified the CODE PATH, not the DSP coefficients.
- FUN_0004613e's call site address inside `FUN_00042af8` (~line 1376 of the decompile, "if (0x80 <
  uStack_ec)") was read from the decompiler and not independently disassembled to a raw address in this
  session (unlike every other cited hop) — the DTC-0x1c mapping itself WAS independently confirmed by
  decompiling `FUN_0004613e` directly (`FUN_00016de6(0x1c,param_1,1,1)`), so the DTC number is solid; only
  the exact call-site address within 0x42af8..0x43e44 is unpinned.

## Related
[[reference-accord-v48b-repoint-asymmetry-review]] · [[reference-accord-segmentE-arbitration-shaper-dtc-gate-table]] · [[reference-accord-fun43e44-report-only-and-gp6acc-slew-limiter]] · [[reference_accord_consistency_monitor_hardshutdown]]
