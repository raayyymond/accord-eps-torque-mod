---
name: reference_accord_assist_map_rom_source_found_and_shares_stage2_fork
description: FUN_000352b4's own X/Y breakpoint table (gp-0x37fc[]/gp-0x37e8[], feeding gp-0x6b86 = magnitude_6b86/Path-1) DOES have a static ROM source -- it forks off the SAME gp-0x373c[]/gp-0x3714[] intermediate array inside FUN_000389ec that the already-characterized Stage-2 LERP (gp-0x64b8[]/gp-0x641c[], feeding gp-0x6b70/Path-2 PID-reference-clamp) copies directly. Both ultimately trace to FUN_000382d8's mode+speed-indexed ROM flash records (0xC7B40-pointer array -> 0xD6158(m24)/0xD7130(m26) family). 0xC6564 (40 bytes, confirmed zero a 3rd time) is a SEPARATE feedback/gating side-channel, not the knot source. Net result: no single edit is both Path-1-scoped AND mode-conditional at once -- corrects a blast-radius claim in the stage2-knot-edit memory.
metadata:
  type: reference
---

# The assist map's ROM source, found -- and it forks off the ALREADY-CHARACTERIZED Stage-2 LERP

2026-08-21, task from `V104-design` orchestrator: "find the ROM source of `gp-0x37fc[]`/`gp-0x37e8[]`
(the 10-point breakpoint table `FUN_000352b4` builds each tick and searches to produce `gp-0x6b7a`
→ biquad → `gp-0x6b86`, i.e. `magnitude_6b86`/Path-1), and say whether it's cal-editable and
mode-indexed." Full trace: `docs/TRACE-2026-08-21-assist-map-rom-source.md`. Program `code.bin`,
GhidraMCP only, fresh `decompile_function` on `FUN_000352b4`(`0x352b4`), `FUN_000352a0`(`0x352a0`),
`FUN_000389ec`(`0x389ec`), `FUN_00039702`(`0x39702`), `FUN_000382d8`(`0x382d8`) this session, plus
`read_memory`/`get_function_callers`/build-script grep.

## The chain, both directions confirmed fresh this session [EVIDENCE]

```
0xC7B40-pointer array (mode+speed-indexed flash records, m24 @0xD6158+0x78*j, m26 @0xD7130+0x78*j)
  -> FUN_000382d8 (mode byte @ gp+0x63fd [positive disp, NOT gp-0x63fd -- confirmed via
     disassemble_bytes: hw bytes a40ffd63, disp16=0x63fd, top bit clear])
  -> writes gp-0x6350[]=Xsrc / gp-0x630c[]=Ysrc (9 elts, blended across 2 adjacent of 7 speed
     breakpoints, 8 monotone-enforcement rungs on Ysrc)
  -> FUN_000389ec (SAME sole caller as FUN_000382d8: FUN_00022ca0)
     K1/K2-rescales (gp-0x6982/gp-0x6984, proven identity=1024 [RELAYED]) -> local_50[]/auStack_8e[]
     "remap loop" (thresholds tp+0x713e/0x7140/0x717a/0x717c + speed-ceiling LERP tp+0x769a-family)
     -> gp-0x373c[1..9] (X-ish) / gp-0x3714[1..9] (Y-ish)          <-- THE FORK
        |
        +-- Branch A [direct copy, loop's 9th iter]: gp-0x64b8[]=X / gp-0x641c[]=Y
        |     -> FUN_00038148's Stage-2 LERP -> gp-0x6b70 (Path-2, PID-reference-clamp lane)
        |     ALREADY fully priced: [[reference_accord_stage2_knot_edit_is_a_hands_on_specific_lever]]
        |
        +-- Branch B [slot-fill/slew loop, runs BEFORE the 9th-iter copy, reads same gp-0x373c/0x3714]:
              SCALE = (cal(0xC6468)=2639 * cal(0xC613A)) >>7<<10 / uVar48
              slew_target = gp-0x3714[iter] * SCALE >> 0x12
              uStack_b8 = 0x1000000 / cal(0xC6468)
              delta = (gp-0x373c[iter] - slew_target) * uStack_b8 >> 0xe
              floor@0 if delta<0; SNAP to cal(0xC6178)=5274 if 0<=delta<5274; else pass-through
              -> gp-0x6442-family[iter] (Y raw target) / gp-0x642e-family[iter] (X seed, = gp-0x3714[iter])
              -> FUN_000352b4's OWN build loop (this task's target):
                   X[k+1] = FUN_000352a0(seed[k],X[k]) = max(seed[k], X[k]+1)   [monotone pass-through,
                                                                                  trivial function, verified]
                   Y[k+1] = slope-limited-difference, per-segment slope CAPPED at cal(tp+0x7384)=
                            cal(0xC6384)=2048 (Q10=2.000) -- confirmed EXACT match to a prior-given bound
              -> gp-0x37fc[]=X / gp-0x37e8[]=Y  <-- MY TASK'S TABLE
              -> breakpoint search on |clamp(gp-0x4f60,+-cal(0xC6200))| -> gp-0x6b7a -> biquad -> gp-0x6b86
```
`gp-0x69a4` ("a") = the raw LERP-interpolated Y VALUE at the current index (not literally a slope;
loosely slope-like only near the origin since X[0]=Y[0]=0), zeroed when `|gp-0x4f60|>25600` [RELAYED +
re-confirmed]. Written a few lines after the breakpoint search in `FUN_000352b4`.

## `0xC6564` blocker RESOLVED -- NOT the off-by-0x1000 trap, mechanism now fully mapped [EVIDENCE]

Fresh `decompile_function 0x39702` shows the literal displacement is `tp+0x7564` (not `tp+0x6564`) —
`0xC6564` is correct, not a page-read artifact. Fresh `read_memory 0xC6564` len 40: **all zero** (3rd
independent confirmation, after 2026-08-05's decompile + `build_v67..v70_tva.py`'s own assertions,
grep-verified this session — `R26_AVG_CAL=0xC6564`, referenced only as an unchanged-assertion, never an
edit target, in v67/v68/v69/v70).

**Mechanism**: `local_5c[k] = cal(0xC6564-family)[k]/1024 + gp-0x6444-family[k]/1024` is `FUN_00039702`
reading `gp-0x6444`-family's OWN PREVIOUS-TICK value (it runs before `FUN_000389ec` recomputes it this
tick — `FUN_000389ec` reads `FUN_00039702`'s own output, `gp-0x6704`-family, "at its own entry"),
blended by a temperature/voltage hysteresis selector, driving a STATE/GATE FLAG (`gp-0x6926`/`gp-0x3740`),
**not** the numeric knot content. The zero cal genuinely contributes nothing; this does not mean no ROM
source exists for the knots themselves — that's Branch A/B above, structurally separate.

## 🛑🛑 THE CENTRAL TRADE-OFF: no edit found is both Path-1-scoped AND mode-conditional at once

- **Shared ROM record (mode-26-only, `0xD7130` Y-knots — exactly `stage2_knot_edit`'s KNOT F/H2
  proposal)**: engagement-conditional (mode-24/manual untouched, records physically separate) — but
  reaches **BOTH** Path 1 (`gp-0x6b86`) **and** Path 2 (`gp-0x6b70`) at once, since both fork from the
  same `gp-0x373c[]`/`gp-0x3714[]`. **This corrects `stage2_knot_edit`'s own "Blast radius = the
  Stage-2 LERP ALONE" claim** — that memory did not know about Branch B. Flagged, not edited (per
  "ask before updating" — the correction lives here and is cross-linked, the original file is untouched).
- **Path-1-specific downstream cals (`0xC6468`=2639, `0xC6178`=5274, Branch B only)**: Path-2-clean
  (Stage-2 LERP untouched — Branch A copies before Branch B transforms) — but **NOT mode-indexed**, the
  slot-fill loop runs unconditionally every tick regardless of mode; only the upstream Xsrc/Ysrc
  selection is mode-gated. Editing these changes manual AND engaged steering equally.

**[BELIEF, single decompile pass, NOT instruction-confirmed]**: `cal(0xC6468)` appears twice in Branch
B (SCALE's numerator AND `uStack_b8`'s divisor) and both appearances compound in the SAME direction —
**lowering `cal(0xC6468)` should monotonically RAISE `gp-0x6442`-family's content** (and hence `a`'s
dose), a promising Path-2-clean lever whose MAGNITUDE is not yet numerically resolved (see Open Items
in the full trace doc).

## Dose ceiling, structural, independent of which edit path

`cal(0xC6384)=2048` (2.000) is the hard per-segment slope cap on `gp-0x37e8[]`, confirmed exact match to
a previously-given bound, downstream of everything in this chain. The task's target dose (~0.098→~0.146)
sits well below this and below the independently-given "mean slope ≤0.644" bound — unlikely to be the
first thing that binds for THIS specific dose, though not proven for the current live operating point.

## Blast-radius grep [EVIDENCE] — every cell in this chain is FALSIFIED-NEVER

`0xC6564`: v67/v68/v69/v70, assertion-only, never edited. `0xC7B40`/`0xD6158`/`0xD7130`/`0xC6384`/
`0xC6178`: zero build-script references, ever. `FUN_000352b4`/`gp-0x69a4`: docstring mentions only
(v103, v62, v70), no edits. **No prior on-car result exists for anything in this trace.**

## Open items (see the full trace doc for the exact next-tool-call for each)
1. Numeric transfer function (ROM-knot-edit -> `gp-0x37e8[]` dose) — not simulated, needs
   `tp+0x713e/0x7140/0x717a/0x717c`, `tp+0x7b66..0x7b98`, `tp+0x713a`, and current `0xD7130` bytes.
2. `cal(0xC6468)`'s magnitude (not just direction) — needs `disassemble_bytes` + simulation.
3. Byte-identity of `0xD6158` vs `0xD7130` for the SPECIFIC knots that matter here — not re-read this
   session (relayed from `stage2_lerp_rescale`, which itself says NOT fully identical, unlike r24/damper
   families — differs at Y[8] and rec[0]/[3]/[4]/[5]).
4. Other readers of `0xC6468`/`0xC6178`/`0xC613A` — not independently re-swept (flagged open since
   2026-08-05, still open).
5. `FUN_00022ca0`'s own call order (not directly decompiled — believed from data-flow necessity only).

## Related
[[reference_accord_stage2_lerp_rescale_is_identity_and_ivar6_bound]] — Branch A's own destination,
geometry fully mapped there. [[reference_accord_stage2_knot_edit_is_a_hands_on_specific_lever]] — the
KNOT F/H2 lever whose blast radius this session's finding expands (correction flagged above).
[[reference_accord_gp69a4_slot_fill_slew_mechanism_and_0xc6564_link_corrected]] — Branch B's mechanism,
confirmed and extended (not superseded) — this session independently re-derived `cal(0xC6468)`'s
address from a completely different starting point (forward from `FUN_000352b4`, not backward from
`gp-0x69a4`) and it matches exactly, cross-confirming both.
[[reference_accord_r24r26_live_gain_is_default_lerp_and_phase_discrepancy]] — same-day sibling trace,
same mode-byte mechanism (`gp+0x63fd`), independent confirmation of the mode-indexing pattern.
