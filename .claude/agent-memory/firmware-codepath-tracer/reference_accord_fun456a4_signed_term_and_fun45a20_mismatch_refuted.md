---
name: reference_accord_fun456a4_signed_term_and_fun45a20_mismatch_refuted
description: FUN_000456a4's post-governor compensation term is SIGNED (negated when gp-0x6abe>0, kept positive when gp-0x6abe<=0), correcting an earlier always->=0 assumption -- but a hypothesized structural mismatch between its gate (LERP1) and FUN_00045a20's asymmetric WIDE-tolerance threshold (fVar4) is REFUTED by direct calculation: LERP1(INDEX) >= fVar4(INDEX) throughout the checked domain, so the monitor's tolerance widens no later than the term generator's gate opens. Both run back-to-back in the same 1kHz tick with no timing lag. Confirms the exact FUN_0002214a call order.
metadata:
  type: reference
---

2026-08-07, dispatched by team-lead to test whether `FUN_00045a20` (1kHz, undebounced comp-bound monitor)
is consistent with the V74/V75 hard-fault conditions (mode 26, damper live ~448 max, driver bar torque at
route max, |d(angle rate)/dt| at route max). Extends
[[reference_accord_hard_shutdown_full_map_v75_incident]] and
[[reference-accord-fun456a4-gate-no-hysteresis-and-index-identity]]. Fresh decompile+disasm,
`FUN_00045a20`@0x45a20, `FUN_000456a4`@0x456a4, `FUN_0002214a`@0x2214a, code.bin.

## Call order, confirmed [EVIDENCE, fresh decompile FUN_0002214a]
Inside the `uVar2&0xd30` branch: `FUN_0004503c(0x21)` [governor->gp-0x6ace] `; FUN_0004595a(); FUN_000456a4(0x22)`
[comp term->gp-0x6acc] `; FUN_00045a20()` [the monitor] `; FUN_00042af8(0x23)` [Monitor1] `;
FUN_00043e44(0x24)` [Monitor2]. **Back-to-back, same 1kHz tick, no intervening writer of gp-0x6a10/
gp-0x6ac0/gp-0x6abe** — FUN_00045a20 reads the value FUN_000456a4 just wrote, same-cycle, no lag.

## NEW: the compensation term is SIGNED, not always >=0 [EVIDENCE, fresh disasm 0x458a6-0x458b8]
Corrects [[reference-accord-fun456a4-gate-no-hysteresis-and-index-identity]]'s implicit framing (that
memory only traced the magnitude path). After the LERP1-gated, LERP2-clamped MAGNITUDE is computed in r6
(always >=0 up to that point):
```
0x458a6: ld.h -0x6abe[gp],r16      ; r16 = signed rate
0x458aa: cmp r0,r16
0x458ac: ble 0x458b8               ; gp-0x6abe <= 0 -> keep r6 positive
0x458ae: mov r0,r12
0x458b0: sub r6,r12                ; r12 = -r6
0x458b2: mov r12,r6                ; r6 = -r6  (NEGATED when gp-0x6abe > 0)
0x458b8: ld.h -0x6acc[gp],r13 ...  ; r6 (signed term) then added: r12(gp-0x6ace)+r6 -> stored to gp-0x6acc
```
**Term = +magnitude when `gp-0x6abe<=0`, -magnitude when `gp-0x6abe>0`** — a genuine `-sign(gp-0x6abe)`
relay, i.e. term OPPOSES the current rate direction (damping/stabilizing structure, consistent with its
position right after the governor). Store path: after a shadow-lockstep check (`gp-0x6acc` old value vs
`gp-0x4cc8`, `FUN_0006b9fa` on mismatch) and a rare diagnostic-blend branch (`tp+0x74ba==0xE9`, almost
certainly inactive in production), the ordinary path is `0x45942: st.h r12,-0x6acc[gp]` where
`r12 = gp-0x6ace + signed_term` — confirms `gp-0x6acc = gp-0x6ace + signed_term` exactly, i.e.
`comp := (gp-0x6acc-gp-0x6ace)/1024 = signed_term/1024` in `FUN_00045a20`.

## Hypothesis tested: does FUN_00045a20's asymmetric tolerance mismatch the term's own gate? REFUTED
[EVIDENCE, direct LERP calculation, both tables read fresh this session]
`FUN_00045a20`'s bounds: LOWER (fVar7) widens to -5.001 (~-5121 counts) iff `gp-0x6abe >= fVar4(gp-0x6a10)`;
UPPER (fVar3) widens to +5.001 iff `gp-0x6abe <= -fVar4(gp-0x6a10)`; else each stays TIGHT (+-0.001, ~1
raw count). `fVar4 = LERP(gp-0x6a10*0.1; X=[350,410] Y=[5000,400], flat-clamped)`, cal `0xC6610-1C`
byte-confirmed `350.0/410.0/5000.0/400.0`. Since term<=0 needs the WIDE **lower** bound (`gp-0x6abe>=fVar4`,
matching `gp-0x6abe>0` sign case) and term>=0 needs the WIDE **upper** bound (`gp-0x6abe<=-fVar4`, but the
term is only forced POSITIVE for `gp-0x6abe<=0`, so the relevant sub-case is `gp-0x6abe` between `-fVar4`
and `0` -- STILL TIGHT there), a mismatch would require the term generator's own gate (`FUN_000456a4`'s
`LERP1`, X=[3800,4000,4150] Y=[5000,3037,1000], cal `0xC6830` block) to open at a `|gp-0x6ac0|` SMALLER
than `fVar4(gp-0x6a10)` — i.e. `LERP1(INDEX) < fVar4(INDEX)` somewhere.

**Computed at 3 points spanning the active domain** (both LERPs evaluated at the same raw `gp-0x6a10`):
| INDEX(raw gp-0x6a10) | LERP1 (gate threshold) | fVar4 (monitor's WIDE threshold) | margin |
|---|---|---|---|
| 3600 (both flat/near-flat) | 5000 | ~4233 | gate MORE conservative |
| 3800 (LERP1's X0) | 5000 | ~2700 | gate MORE conservative |
| 4000 (LERP1's midpoint) | 3037 | ~1167 | gate MORE conservative |
| 4150 (LERP1's X2/floor) | 1000 | 400 (fVar4's own floor) | gate MORE conservative |

**`LERP1(INDEX) >= fVar4(INDEX)` holds at every point checked, with ~2-2.5x margin.** Consequence: by the
time `|gp-0x6ac0|` (assumed ~= `|gp-0x6abe|`, same producer, BELIEF not re-confirmed this session — see
open items) exceeds `LERP1(INDEX)` and the term generator's gate opens at all, `|gp-0x6abe|` has ALREADY
exceeded `fVar4(INDEX)` (the monitor's own, smaller, WIDE-permit threshold) — **the monitor's tolerance
widens no later than the term becomes nonzero.** No timing lag exists to exploit (confirmed same-cycle,
above). **⇒ My initial hypothesis (that this pairing has an exploitable gap) is REFUTED, not confirmed —
stated plainly per project convention: check the hypothesis before reporting it as fact.**

## What remains open [BELIEF / unresolved]
1. `gp-0x6ac0 ~= |gp-0x6abe|` was assumed, not re-confirmed this session (flagged as unresolved already in
   [[reference-accord-fun456a4-gate-no-hysteresis-and-index-identity]]) — if the two differ by filtering
   or scale, the margin above could close or invert. Would need `FUN_00041464`'s store logic decompiled.
2. Only 3 spot points checked (piecewise-linear on both sides, so likely representative, but not an
   exhaustive continuous proof).
3. **No alternative confirmed candidate among Monitor 1 (`FUN_00042af8`) / Monitor 2 (`FUN_00043e44`)** for
   the actual fault mechanism — neither was numerically checked against the stated fault conditions this
   session (both are further downstream, post-shaper, and would need the shaper's own gp-0x6acc->gp-0x6b98
   transform plus the corridor-wall producers traced, not done here).
4. The compensation term's ACTUAL magnitude/sign at either real fault moment is unmeasured — this
   refutation shows the mechanism is *structurally sound as designed*, not that the term never got large;
   whether it reached a magnitude that FUNCTIONALLY mattered downstream (e.g. via Monitor 1/2, or via the
   shaper's own corridor snapshots) is untested.

## Table-only lever, if the source term is still wanted as a precaution regardless of which monitor trips
Already on record, addresses confirmed, ZERO other consumers of any of these cals image-wide (per
[[reference-accord-fun456a4-gate-no-hysteresis-and-index-identity]]'s exhaustive search): lower
`0xC67DC`/`0xC67DA`/`0xC67D8` (LERP2 ceiling/mid/floor, currently 2560/1024/512) to cap the worst-case
single-cycle injection into `gp-0x6acc`; and/or raise `0xC6832/34/36` (LERP1 X, currently 3800/4000/4150)
to require a bigger rate margin before the term activates at all. **Caution carried forward from that
memory: this term's structure (opens more easily as tracking-error rises, magnitude opposes rate sign)
reads as a genuine stabilizing/back-EMF-style corrective term, not cosmetic — do not zero it outright.**

## Related
[[reference-accord-fun456a4-gate-no-hysteresis-and-index-identity]] — source of the LERP1/LERP2 tables and
mitigation ranking, both reused here. [[reference_accord_hard_shutdown_full_map_v75_incident]] — original
FUN_00045a20 paraphrase, now superseded by this session's exact sign-relay finding and the refuted
mismatch hypothesis. [[reference_accord_ceiling_race_v74_manual_reconciliation_and_dtc_index_sharing]] —
the Surface A (gp-0x6bd0 ceiling-race) finding this session's team-lead confirmed dead via telemetry
(peak 448 vs floor 512), redirecting attention to this cluster.
