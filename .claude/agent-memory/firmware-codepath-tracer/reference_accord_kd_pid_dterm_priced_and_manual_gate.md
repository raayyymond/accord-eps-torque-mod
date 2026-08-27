---
name: reference_accord_kd_pid_dterm_priced_and_manual_gate
description: "Settles the Kp/Ki/Kd table-header-vs-Y[0] address split (arc_map=header, BUILD-LINEAGE=Y[0], header+0xA=Y[0] in all three); full instruction-level D-branch trace (0x3a798-0x3a8a0) with dual-method (closed-form + integer time-domain sim) frequency response; corrects V43/V49 alphaD value attribution; and finds FUN_0003a382 (hence Kd) is gated by the SAME gp-0x67fa state cluster as the base aggregator -- i.e. likely affects MANUAL steering, not LKAS-engaged-only. Also flags that the measured Re(Z) 3-drive crossover (~22-26Hz) contradicts the kit's own 'D damps 16-35Hz' belief on its specific crossover point."
metadata:
  type: reference
---

# Kd priced end to end (task `pidtrace`, briefed by team-lead 2026-08-19)

Stock `code.bin`. All addresses fresh `decompile_function`+`disassemble_function` this session, cross-checked
by raw Python LE byte scans over all 102 `*_plain_image.bin` in `ACCORD_FIRMWARE_ROOT/analysis-2020accord/`.

## Table header vs Y[0] — SETTLED [EVIDENCE, 3 independent confirmations]

`docs/archive/arc-maps/_v101_arc_map.md` §5.2g's addresses (`0xC6ADC`/`0xC6B08`/`0xC6B1C`) are the table **headers**
(`movea 0x7adc,tp,r6` etc. at `0x3a44a`/`0x3a3ea`/`0x3a38a`). `docs/BUILD-LINEAGE.md`'s addresses
(`0xC6AE6`/`0xC6B12`/`0xC6B26`) are **Y[0] = header+0xA** exactly (`addi 0xa,r6,r13` builds the Y base;
`addi 0x2,r6,ep` builds X base = header+2). Both documents are correct; same trap class as the kit's own
`0xC67BE`-vs-`0xC67C8` AUTH-table note. Matches and extends [[reference_accord_v100_rungs_proven_and_pid_gain_tables]]
with the byte-level table contents:
```
D: header 0xC6ADC=4, X@0xC6ADE=[50,400,1500,3000], Y@0xC6AE6=[2048,2048,2048,2048]
I: header 0xC6B08=4, X@0xC6B0A=[0,400,1500,3000],   Y@0xC6B12=[98,98,98,98]
P: header 0xC6B1C=4, X@0xC6B1E=[0,300,2000,4000],   Y@0xC6B26=[256,256,225,153]
```
Ki and Kd are **flat at all 4 knots** — the arc_map's own flagged 528-vs-1941ct `gp-0x6ac0` reachability
crux (§5.2g part 5) does not apply to Kd/Ki at all: there is no knot to cross for either. It only matters
for Kp, and even there Y[0]=Y[1]=256 flattens the first (by far the most visited) sub-range regardless.
**Kd is a pure scalar gain in practice.**

Virginity, Python byte scan, 102 images + stock: header/X/Y for all three terms **N=0/102, byte-identical
to stock including V101.** Fully virgin. `0xC644A` (D's own EMA "smoothing pole", see below) is the ONLY
non-virgin neighbour of the D term: N=2/102. 🛑 **Corrects an arc_map neighbour-note attribution**: the
"moved by V43 (1024→64)" claim is WRONG — byte-verified, `_v43_plain_image.bin` alphaD=**32** (matches
[[reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction]]'s "32, not 64" correction). The
value **64** belongs to a *different* image, `_v49_plain_image.bin` (distinct from `_v49p_plain_image.bin`,
which is stock/1024). Both reverted; alphaD sits at stock unity on V100 and V101.

## D-branch full instruction trace [EVIDENCE, `0x3a798`-`0x3a8a0`]

```python
ref   = clamp(gp_0x6ad6, -8192, +8192)                            # 0x3a798-0x3a7c8, cal 0xC6200 @0x3a7a2/b2/c4
ERR   = clamp(gp_0x4f60 - ref, -10240, 10240)                     # 0x3a7ca-0x3a7e6; 0x2800 is an IMMEDIATE
D_raw = clamp(((ERR[n]-ERR[n-1]) * Kd) >> 10, -10240, 10240)      # 0x3a836 sub / 0x3a838 mul / 0x3a844 sar 0xa / clamp
                                                                     # ERR[n-1] persists at gp-0x3684
D_state = D_state_prev + (((D_raw*32 - D_state_prev)*alphaD)>>10) # 0x3a85c-7a; alphaD=cal(0xC644A)@0x3a860; persists gp-0x3680
combine = ((D_state+I_state+P_state)>>5) * gainD/1024 * polarity  # 0x3a874-88
gp_0x6ad4 = clamp(combine, -ceiling, +ceiling)                    # 0x3a8a0 final store
```
At stock alphaD=1024=unity the EMA is a lossless pass-through (D_state=D_raw*32 exactly, both mults are
powers of 2) — D's net combine contribution = `D_raw` exactly. **P is a pure static 0°-phase gain at
every frequency** — instruction-verified: alphaP=cal(0xC6450)=unity, and `0x3a874 add r6,r12` reads
P_state from the SAME tick it was written at `0x3a806/26`, no delay register in between.

## Frequency response, dual-method verified [EVIDENCE]

`H_D(f) = (Kd/1024)*2*sin(pi*f/fs) ∠ [90 - 180*(f/fs)]`, fs=1000Hz. Closed-form cross-checked against an
integer time-domain sim of the exact recursion above (real `>>`, real clamp) — agree to 3-4 dp. Matches
the kit's existing 7.79/21Hz figures in [[reference_accord_6to9hz_loop_is_pid_torque_tracker_phase_budget]]
to <0.1°.

| f(Hz) | 1.0x (2048) | 1.5x (3072) | 2.0x (4096) | 3.0x (6144) |
|---|---|---|---|---|
| 2 | 0.0251∠+89.64° | 0.0377∠+89.64° | 0.0503∠+89.64° | 0.0754∠+89.64° |
| 7.8 | 0.0980∠+88.60° | 0.1470∠+88.60° | 0.1960∠+88.60° | 0.2940∠+88.60° |
| 21 | 0.2637∠+86.22° | 0.3956∠+86.22° | 0.5274∠+86.22° | 0.7911∠+86.22° |
| 35 | 0.4389∠+83.70° | 0.6584∠+83.70° | 0.8779∠+83.70° | 1.3168∠+83.70° |

**DC gain = 0 exactly, any Kd** (structural: `ERR[n]=ERR[n-1]` at DC regardless of Kd's value). **D's own
phase is a near-uniform lead, 83.7°-89.6°, with NO sign reversal anywhere in 2-35Hz** — the pump/damp
categorization can only come from folding in the plant's own torque→velocity phase, which is outside this
PID's code.

Net P+I+D (this block alone, small-signal): max `|phase|` across 2-35Hz at any dose up to 3x is **73.0°**
(at 3x/35Hz) — **no new ±180° crossover created by this block alone, at any dose tested.** Does NOT clear
the full loop (plant+governor+shaper+FOC+the Q≈14-29 resonance) — that's [[looptrace's]] remit.

## 🛑 Re(Z) measurement contradicts the "D damps 16-35Hz" belief's crossover point

Two same-day (2026-08-11) files disagree on D's pump/damp split:
[[reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction]] finds D the sole pumping term at
7.79Hz (robust across 3 plant-phase readings). `reference_accord_vehicle_bus_clearance_and_aggregator_probe_reaim_2026-08-11.md`
claims "D pumps ONLY 2-12Hz and DAMPS 16-35Hz" citing an unlocatable "parallel PID trace" — **I could not
find that source file this session.**

Anchored instead against `memory/accord/mechanism/accord-rez-antidamping-replicated-three-drives.md` (on-car measured
Re(Z), 3 drives, 5Hz resolution — the actual closed-loop damping sign, not a code-side guess):
2-4Hz anti-damped, **6-9Hz AND 9-12Hz anti-damped (9-12 is the WORST band, -4130 to -4593)**, **12-16Hz
still strongly anti-damped (-3858 to -4020)**, 18-22Hz weakly anti-damped, **crossover is actually
22-26Hz**, damped only 26-31Hz+. **This contradicts the specific "16-35Hz damps" crossover claim** —
12-16Hz is the third-worst measured band, not yet in the damping regime. Treat the vehicle_bus_clearance
crossover figure as superseded by this more precise, replicated measurement.

## Manual vs. engaged — likely BOTH, not LKAS-only [BELIEF, well-supported, not fully closed]

`FUN_0003a382` is called from the 1kHz dispatcher `FUN_0002214a` under
`if ((1<<(gp_0x67fa & 0xf)) & 0xc30) FUN_0003a382();` — **the IDENTICAL gate** also guards the base
aggregator `FUN_0003aa2c`. Per [[reference-accord-state4-ratchet-and-gp67fa-state-graph]] (the other
agent-memory dir), states {4,5,10,11} (bits of mask `0xc30`) are the normal-driving cluster, gated by
`gp-0x68ad` — tied to torque-sensor-plausibility convergence, NOT any LKAS-engagement flag. Reading:
**Kd changes manual steering feel too** — this PID sits in the base EPS torque-assist path. Not closed:
did not this session cross-check `gp-0x67fa`'s states against an explicit engagement flag (e.g.
`gp-0x6806`) — next step if this needs to be airtight before dosing.

## Blast radius [EVIDENCE, dual method, every raw-scan extra hit adjudicated]

Exactly 1 reader instruction each for Kd/Ki/Kp's header AND Y[0] (6 total), all inside `FUN_0003a382`.
Raw byte scan initially over-counted (3 extra for D-header, 5 extra for P-header) — every extra hit
disassembled directly and excluded (`shl 0x1c,r15`, `jarl 0x1fa42,lp`, `cmovge -0x1,r15,r15` x3 — none
are `movea …,tp,…`, pure byte-pattern coincidences). Also reconfirms the skill's `ld.hu`→`disp|1` trap:
a bare-displacement scan for Kd's Y0 (`0x7ae6`) returns **zero** hits; the real encoding is `0x7ae7`.
Writers: **0, architecturally** — `tp`-relative flash constants have no runtime writer; the only way the
value changes is a new flashed image (covered by the N=0/102 scan above).

## Recommendation given to team-lead

Against raising Kd blind. The one phase-uncertainty-robust argument in the kit's record (7.79Hz pumping)
is corroborated by Re(Z)'s worst-band being 6-16Hz on the real car; the "raise it, damps 16-35Hz" belief
is uncorroborated and wrong on its own crossover point. If a dose is wanted, **lowering** Kd (untried,
N=0/102) is the better-evidenced direction — reduces gain in a term proven pumping at the one frequency
carefully checked, zero DC cost either way. Sign for other frequencies (incl. the actual V101 oscillation,
frequency TBD by damphunt/looptrace) remains open — this is a recommendation, not a closed GATE-2 verdict.

## Related
[[reference_accord_v100_rungs_proven_and_pid_gain_tables]] · [[reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction]] ·
[[reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse]] · [[reference_accord_6to9hz_loop_is_pid_torque_tracker_phase_budget]] ·
[[reference_accord_c6200_clamps_gp6ad6_inside_the_pid]] · [[reference-accord-state4-ratchet-and-gp67fa-state-graph]] (other agent-memory dir)
