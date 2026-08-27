---
name: reference_accord_kd_ratchet_gate2_verdict_and_dispatcher_gating
description: "GATE-2 verdict for PID Kd (0xC6AE6) as a ratchet lever: it IS a genuine loop-gain (L) term (ERR derives from gp-0x4f60, closing through the plant), byte-verified virgin on stock/V108/V109, exactly 1 reader/0 writers reconfirmed fresh. The 'D damps 16-35Hz, costs 3-4x the ratchet benefit' verdict in accord-six-levers-closed-on-arithmetic.md is STALE/REFUTED (no computation anywhere supports it; superseded by BUILD-LINEAGE's own 22-26Hz crossover). D's own internal phase (relative to ERR) never reverses 2-500Hz -- any reversal is plant-side, unknown beyond the 7.79Hz G_bar anchor. Also resolves the FUN_0003a382/FUN_000352b4 gating question directly from the 1kHz dispatcher: PID+aggregator run on state-mask 0xc30 (bits 4,5,10,11); assist-map+gp-0x6b26 run on 0x830 (bits 4,5,11) -- DIFFERENT, overlapping clusters, NEITHER is LKAS-only. gainD_raw (L4 table) byte-confirmed flat 1024 (unity) at all 3 knots, closing a gap flagged unresolved since 2026-07-28."
metadata:
  type: reference
---

# Kd (0xC6AE6) GATE-2 verdict for the ratchet, + dispatcher gating resolved — task `ratchlever`, 2026-08-27

Briefed by team-lead/`main` to gate+price Kd as a 7.8Hz ratchet lever, given the same-day topology
result that additive-only Re(Z) census is void (`[[reference_accord_aggregator_11term_loop_census_units_and_fork]]`).
Program: stock `code.bin` (sole open program, confirmed `list_open_programs`). Fresh
`decompile_function` on `0x3a382` (whole function) and `0x2214a` (the 1kHz dispatcher) this session;
cross-validates 4 of my own prior sessions' independent decompiles of the same D-branch
(`[[reference_accord_kd_pid_dterm_priced_and_manual_gate]]`, `[[reference_accord_kd_dbranch_order_and_flight_history]]`,
`[[reference_accord_dterm_grindband_unresolved_and_pid_net_damping]]`, `[[reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse]]`).

## 1. Virginity, byte-verified fresh this session [EVIDENCE]

Python raw LE read, three images: `stock_fw_dump/code.bin`, `_v108_..._plain_image.bin`,
`_v109_..._plain_image.bin` (the two named in the brief). `0xC6AE6`(Kd)=2048, `0xC644A`(pole)=1024,
byte-identical across all three. Matches the N=0/102 scan already on record.

## 2. GATE 1, reconfirmed [EVIDENCE, dual method]

`get_bulk_xrefs(0xC6AE6)` returns `[]` — reproduces the documented misleading-zero trap on tp-relative
cells. Raw Python LE scan (both `disp16` and `disp16|1` forms) finds exactly **1 hit**, `0x3a460`
(matches the known reader at `0x3a45e`+2, the displacement-field offset within the `ld.hu` encoding).
0 writers (tp-relative flash constant, architecturally cannot have one). **No shadow-lockstep twin on
Kd itself** (unnecessary — ROM) **nor on its direct output `gp-0x6ad4`** (unlike `gp-0x6b86`, see the
sibling `0xC6384` memory) — `FUN_0003a382`'s decompiled tail is a bare `*(short*)(gp-0x6ad4)=...; return;`,
no `FUN_0006b9fa` call anywhere in the function. The aggregate sum downstream (`gp-0x6b94`/`gp-0x4ce0`)
IS shadow-checked, per prior memory — so a Kd-only edit is not un-monitored, just not monitored at its
own output stage.

## 2b. 🛑 Dispatcher gating, resolved directly from `FUN_0002214a` (the 1kHz dispatcher) [EVIDENCE]

Fresh decompile of `0x2214a`. State mask `uVar2 = 1<<(gp-0x67fa & 0xf)`. Two DIFFERENT sub-masks gate
the PID and the assist map:
```
uVar3 = uVar2 & 0xc30      # bits {4,5,10,11}  -> gates FUN_0003a382 (PID/Kd) AND FUN_0003aa2c (aggregator)
uVar4 = uVar2 & 0x830      # bits {4,5,11}     -> gates FUN_000352b4 (assist map) AND FUN_00036c12 (gp-0x6b26)
```
**Both clusters overlap on {4,5,11} and both are OUTSIDE any LKAS-engagement-specific mask** — confirms
(does not merely repeat) the prior "Kd changes MANUAL steering too" finding, and extends it: **the
assist map (Candidate 2) is ALSO not LKAS-gated**, structurally expected (a power-assist curve must
serve manual steering) and now EVIDENCE not BELIEF. State 10 is a genuine asymmetry — PID+aggregator
run there, assist-map+`gp-0x6b26` do not; not further resolved this session, low priority (both share
the {4,5,11} core).

## 3. `gainD_raw` (L4 table) closed — byte-confirmed unity, was BELIEF since 2026-07-28 [EVIDENCE]

`read_memory(0xC67B0, 24)`: header/X=[3,5,10,15], **Y=[1024,1024,1024]** (3 knots, all flat, matching
the flat-Y pattern already seen in L1/L2/L3). `gainD_raw ≡ 1.000` (Q10) across its entire domain —
closes the gap `[[reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse]]` flagged
as "not independently re-verified" and now used with confidence below.

## 4. D IS a loop-gain term, not additive [EVIDENCE, structural]

`ERR = clamp(gp-0x4f60 - bias, ±0x2800)` — `gp-0x4f60` is the torque sensor, itself driven by `Ω_w`
through the mechanical column/bar (the same physical path every other `L`-table lane in
`[[reference_accord_aggregator_11term_loop_census_units_and_fork]]` uses). D differentiates ERR and
its output is ADDED into `gp-0x6ad4`, which is ADDED unconditionally into the aggregator
(`FUN_0003aa2c`, re-confirmed `0x3aca8-0x3acda` plain `add`, no negation). ⇒ **D belongs in the
denominator `L`, exactly like the census reclassified P/I/D collectively. A Kd dose moves Q, not merely
an additive torque** — this is the answer to the orchestrator's central question for Candidate 1.

## 5. Exact math, dual-verified this session against the task's own census [EVIDENCE]

Fresh decompile confirms byte-for-byte: `D_raw=clamp(((ERR[n]-ERR[n-1])*Kd)>>10,±0x2800)` at
`0x3a836/38/44`, EMA `D_state += ((D_raw*32-D_state)*alphaD)>>10` at `0x3a85c-7a` (alphaD=cal(0xC644A)
@`0x3a860`=unity pass-through), combine `((D+I+P)>>5)*gainD/1024*polarity*validity` at `0x3a874-88`
(validity = `gp-0x671a < 0xff` AND `gp-0x6752 ∈ {-1,0,1}`), final clamp+store to `gp-0x6ad4` at `0x3a8a0`.

```python
# H(z) INTERNAL to ERR (no plant needed — pure firmware, exact):
#   P = gainA/1024                              (real, 0 deg, gainA=256 at the low/most-visited knot)
#   I = (gainB/1024) / (32*(1-z^-1))             (gainB=98, flat all 4 knots)
#   D = (Kd/1024) * (1-z^-1)                     (Kd swept; zero phase-dependence on Kd's value)
#   combine = (P+I+D) * gainD/1024               (gainD=1024 flat, confirmed sec.3)
fs=1000.0; z_inv=lambda f: cmath.exp(-1j*2*pi*f/fs)
```
Reproduces the task's own P/I/D Re(Z) table EXACTLY (P=0.2500∠+180.00°, I=0.0611∠+91.40°,
D=0.09788∠-91.40°, sum=0.2565∠-171.76°) once rotated by `G_bar(7.79Hz)=1∠180°` — the ONE anchor point
available, taken from the assist-map's own memoryless identity (§7 of the sibling `0xC6384` memory).
**D's own internal phase is Kd-independent** (Kd only scales magnitude) and is a near-uniform 72-90°
LEAD from 1-100Hz — **never reverses sign in its own frame anywhere 2-500Hz** (cross-validated 3
independent sessions, `[[reference_accord_kd_dbranch_order_and_flight_history]]`).

| f(Hz) | Kd=2048(stock) | 1024 | 512 | 256 | 0 |
|---|---|---|---|---|---|
| 1.00 | 0.0126∠+89.8° | 0.0063∠+89.8° | 0.0031∠+89.8° | 0.0016∠+89.8° | 0 |
| 3.00 | 0.0377∠+89.5° | 0.0188∠+89.5° | 0.0094∠+89.5° | 0.0047∠+89.5° | 0 |
| 7.79 | 0.0979∠+88.6° | 0.0489∠+88.6° | 0.0245∠+88.6° | 0.0122∠+88.6° | 0 |
| 21.73 | 0.2729∠+86.1° | 0.1364∠+86.1° | 0.0682∠+86.1° | 0.0341∠+86.1° | 0 |
| 40.0 | 0.5013∠+82.8° | 0.2507∠+82.8° | 0.1253∠+82.8° | 0.0627∠+82.8° | 0 |
| 100.0 | 1.2361∠+72.0° | 0.6180∠+72.0° | 0.3090∠+72.0° | 0.1545∠+72.0° | 0 |

`d|H_D|/dKd` is EXACT linear scaling at every frequency, zero phase shift, DC=0 exactly (structural,
any Kd). Full P+I+D combine sweep (same doses/freqs, internal-to-ERR) computed and archived in the
session transcript; magnitude range is bounded (0.25-1.33 across the whole sweep), settling toward the
pure-P value 0.25 as Kd→0.

## 6. 🛑🛑 Correction flagged — `accord-six-levers-closed-on-arithmetic.md`'s Kd row is STALE

That file (2026-08-11, `memory/accord/builds/`, NOT my agent-memory dir — flagging, not editing per the
"ask before updating" rule) states *"D damps 16-35Hz... cost 3-4x the benefit"* as a closed verdict.
**This has no computational source anywhere in the kit** — provenance-chased twice
(`[[reference_accord_dterm_grindband_unresolved_and_pid_net_damping]]`, 2026-08-20) to a review file
(`docs/review/GATE2-2026-08-11-cbe74-independent.md` §N1) that explicitly DECLINES to compute 18-22/26-31Hz,
and is CONTRADICTED by `docs/BUILD-LINEAGE.md`'s own current Kd row (22-26Hz crossover) and by the real,
3-drive-replicated on-car Re(Z) (`memory/accord/mechanism/accord-rez-antidamping-replicated-three-drives.md`):
**the worst measured band is 9-12Hz (-4130 to -4593), 12-16Hz is STILL strongly anti-damped (-3858 to
-4020, third-worst), crossover is 22-26Hz, damped only 26-31Hz+.** Nothing in this real measurement
supports "16-35Hz damps" as a description of where the crossover sits. `main`/team should reconcile or
retire that row; I have not touched the file myself.

## 7. Calibration caveat carried forward

My own prior file (`[[reference_accord_dterm_grindband_unresolved_and_pid_net_damping]]`) warns against
projecting D's isolated-stage phase into a real Re(Z) ct claim — the one directly comparable precedent
(`gp-0x6b26`) was off by ~227° once the loop closed. I have NOT done that here: every closed-loop
magnitude claim in this file is sourced from the REAL 3-drive measurement, not from D's own code-side
phase. The code-side table above is offered strictly as the firmware's own contribution, G_bar-free.

## 8. Sizing within the loop [EVIDENCE, from the task's own `L`-table]

`|D|=0.0979` vs nominal `|L|=1.876` / ceiling `|L|=2.825` (`[[reference_accord_aggregator_11term_loop_census_units_and_fork]]`
§3) ⇒ **D is 3.5-5.2% of the total loop-gain magnitude at 7.79Hz** — the smallest named term after
`FUN_00036682` (0.32%), well below r24 (½-3×), r26 (1-12×) and `gp-0x6b86` (5-20× larger). Halving Kd
(2048→1024) removes ~1.7-2.6% of `|L|` — small, bounded, DC-free, directionally consistent with the
real 6-9Hz anti-damping measurement, but structurally incapable of being the WHOLE fix for a loop
cancelling ~93% of its natural damping on its own.

## Related
[[reference_accord_c6384_slopecap_role_confirmed_binding_unresolved]] — Candidate 2, the memoryless-vs-
shaped structural comparison. [[reference_accord_aggregator_11term_loop_census_units_and_fork]] — the
loop topology and `L`-table this file prices Kd against.
