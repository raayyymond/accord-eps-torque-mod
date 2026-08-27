# TRACE 2026-08-21 — the `magnitude_6b86` assist-map's ROM source, found and characterized

Subagent trace for the orchestrator's "is the assist map (`gp-0x37fc[]`/`gp-0x37e8[]`, feeding `gp-0x6b86`
via `FUN_000352b4`) a cal-editable, mode-indexed lever" question. Program: stock `code.bin`, GhidraMCP
only, read-only. All addresses below are freshly decompiled/disassembled this session unless marked
[RELAYED] (from `.claude/agent-memory/firmware-codepath-tracer/`).

## Headline

**The ROM source IS found.** The "no static ROM copy exists" blocker is WRONG for the main numeric
content. `gp-0x37fc[]`/`gp-0x37e8[]` trace, through `FUN_000389ec`, to the **exact same mode+speed
ROM record family already characterized by `reference_accord_stage2_knot_edit_is_a_hands_on_specific_lever.md`**
(`0xC7B40`-pointer array → `0xD6158`(m24)/`0xD7130`(m26) records). The `0xC6564`, 40-byte, all-zero cal
the analyst flagged is real and confirmed zero (three independent reads now), but it is a **separate
feedback/state-gating side-channel**, not the knot source.

**But the coupling this reveals cuts against the task's hoped-for lever**: the assist map's ROM knots
are **the same physical bytes** already feeding `FUN_00038148`'s Stage-2 LERP (`gp-0x6b70`, the PID
reference clamp lane) — so a mode-26-only edit of that ROM record is engagement-conditional but reaches
**two lanes at once**, and the one downstream lever that IS Path-1-specific (`0xC6468`/`0xC6178`) is
**not mode-indexed at all**. No single edit found this session is both scoped-to-Path-1 and
engagement-conditional simultaneously — see §6.

## 1. The build loop, fresh decompile [EVIDENCE]

`FUN_000352b4` (`decompile_function 0x352b4`), the top loop, 9 iterations (`bVar12`=1..9) after a
hard `X[0]=Y[0]=0`:
```
X[k+1] = FUN_000352a0(seed[k], X[k])     seed[k] read from gp-0x642e..gp-0x641e (9 halfwords)
Y[k+1] = slope-limited-difference using raw[k] read from gp-0x6442..gp-0x6432 (9 halfwords)
```
`FUN_000352a0` (`decompile_function 0x352a0`) is trivial: `return (param_1<=param_2) ? param_2+1 :
param_1;` — i.e. `X[k+1] = max(seed[k], X[k]+1)`, a monotonicity-enforcing pass-through. No hidden
logic; X is exactly the seed array, floor-bumped to stay strictly increasing.

The Y-side slope cap, confirmed exactly matching the task's given bound:
```
0x354xx  slope = (raw_target - Y[k]) / (X[k+1]-X[k])
         if slope >= cal(tp+0x7384)/1024:                 # tp+0x7384 = 0xBF000+0x7384 = 0xC6384
             X[k+1] is pushed OUTWARD so slope == cal(0xC6384)/1024 exactly (not simply clamping Y)
             if the pushed-out X[k+1] would exceed a further cal ceiling, X[k+1] clips there instead
             and Y[k+1] is correspondingly short of raw_target (slope still == the cap)
```
`cal(0xC6384) = 2048` (Q10 = **2.000**) — **CONFIRMED, fresh, this session, as the hard per-segment
slope ceiling for `gp-0x37e8[]`**, exactly matching the task brief's stated bound. It is downstream of
everything else in this trace and applies regardless of any upstream edit.

`gp-0x69a4` ("a" in the task's framing) is written a few lines later in the SAME function: it is the
**raw LERP-interpolated Y value** at the current breakpoint-search index (not literally a slope; loosely
slope-like only near the origin where X[0]=Y[0]=0), forced to 0 when `|gp-0x4f60| > 25600` (the
plausibility window [RELAYED/re-confirmed] from `reference_accord_stage2_lerp_rescale_is_identity...`
and `reference_accord_r24r26_live_gain_is_default_lerp...`).

## 2. Where the raw slot arrays come from — traced fresh, all the way to `FUN_000382d8` [EVIDENCE]

`FUN_000389ec` (`decompile_function 0x389ec`, ~230 decompiled lines, the largest function traced this
session) is a **shared per-tick builder** used by two downstream consumers:

```
Xsrc = gp-0x6350[0..8]   Ysrc = gp-0x630c[0..8]        <- READ at FUN_000389ec's own entry
   -> K1/K2 rescale (gp-0x6982/gp-0x6984, PROVEN identity=1024 always [RELAYED,
      reference_accord_stage2_lerp_rescale_is_identity_and_ivar6_bound.md], re-confirmed structurally
      this session via FUN_0003897a call sites)
   -> local_50[]/auStack_8e[]  (== Xsrc/Ysrc, unchanged)
   -> "remap loop" (uVar48=1..9), using thresholds tp+0x713e/0x7140/0x717a/0x717c and a
      speed-scheduled X-axis ceiling (tp+0x769a-family, matches the ALREADY-documented
      "speed-scheduled X-axis CAP" in reference_accord_stage2_lerp_rescale...):
        - below the speed ceiling: gp-0x373c[i]/gp-0x3714[i] ~= Xsrc[i]/Ysrc[i] DIRECTLY (1:1)
        - beyond it: locally interpolated/extrapolated from the neighbouring two Ysrc points
   -> gp-0x373c[1..9] (X-ish) / gp-0x3714[1..9] (Y-ish)      <-- THE FORK POINT, see below
```

**THE FORK** [EVIDENCE, both branches read from the SAME `gp-0x373c[]`/`gp-0x3714[]` this session]:

**Branch A — direct copy, on the loop's 9th iteration** (`if (9<bVar31) {...}` block):
```c
*(undefined2 *)(unaff_gp + -0x64b8) = *(undefined2 *)(unaff_gp + -0x373c);   // + a copy loop, k=0..8
*(undefined2 *)(unaff_gp + -0x641c) = *(undefined2 *)(unaff_gp + -0x3714);
```
`gp-0x64b8[]`/`gp-0x641c[]` are read by `FUN_00038148` — **this is exactly the Stage-2 LERP** already
fully priced by `reference_accord_stage2_knot_edit_is_a_hands_on_specific_lever.md` (KNOT F / H2
levers), feeding `gp-0x6b70` (the PID-reference-clamp lane, Path 2).

**Branch B — the slot-fill/slew loop** (`bVar31`=1..9, runs BEFORE the 9th-iteration copy above):
```c
SCALE       = ((cal(0xC6468) * cal(0xC613A)) >> 7 << 10) / uVar48        # uVar48: 1024 or a boost-curve LERP
slew_target = gp-0x3714[iter] * SCALE >> 0x12
uStack_b8   = 0x1000000 / cal(0xC6468)
delta       = (gp-0x373c[iter] - slew_target) * uStack_b8 >> 0xe
if delta < 0:                              slot = 0                       # floor
elif delta < cal(0xC6178) = 5274:          slot = cal(0xC6178) = 5274     # snap
else:                                       slot = delta                  # pass-through
gp-0x6442-family[iter] = slot                            # -> Y-side raw target for FUN_000352b4
gp-0x642e-family[iter] = gp-0x3714[iter]  (when shadow-check passes)      # -> X-side seed for FUN_000352a0
```
`gp-0x6444` (slot 0) and `gp-0x6430` are unconditionally hard-zeroed a few lines earlier (shadow-checked
via `FUN_0006b9fa`), matching `reference_accord_gp69a4_slot_fill_slew_mechanism...` exactly.

`cal(0xC6468) = 2639` and `cal(0xC613A)` are resolved this session by recognizing the Ghidra symbol
collision `FUN_00007462 + unaff_tp + 6` = `tp + 0x7468` = `0xC6468` — **matches, byte-for-byte, the
2026-08-05 memory's own finding** (independently re-derived from a different starting point this
session — cross-confirms both).

`cal(0xC6178) = 5274` re-confirmed [EVIDENCE, `tp+0x7178` visible directly in this session's
decompile of both `FUN_000389ec` and, separately, `FUN_00039702`'s comparison logic].

**⇒ `gp-0x6442`-family/`gp-0x642e`-family (feeding MY task's `gp-0x37fc[]`/`gp-0x37e8[]`) is a
Path-1-SPECIFIC, memoryless-per-tick transform of the SAME `gp-0x373c[]`/`gp-0x3714[]` array that
Branch A copies verbatim into the Stage-2 LERP's own table.** Both branches read `gp-0x373c[]`/
`gp-0x3714[]`; neither writes back to it; order within the tick doesn't create a race (confirmed no
`gp-0x373c`/`gp-0x3714` write occurs between the two reads).

## 3. `FUN_000382d8` — the actual ROM record reader, fresh decompile [EVIDENCE]

```
0x382e0  ld.bu 0x63fd,gp,r1        # mode byte (POSITIVE gp displacement, not gp-0x63fd -- disassembled
                                    # directly this session: hw bytes a40ffd63, disp16=0x63fd, top bit
                                    # clear = positive. Matches the memory's own "gp+0x63fd" notation.)
0x382e4  ld.hu -0x6a64,gp,r24      # speed
0x382e8  mov 0xcc9fc,r28           # breakpoint-table base (7 speed slots, +mode*4)
...
puVar23 = (&PTR_DAT_000c7b40)[mode]     # record pointer array, +mode*4 -- SAME array
                                          # reference_accord_stage2_knot_edit... already maps in full
...
*(short *)(gp-0x6350 + k*2) = <interpolated across 2 adjacent speed records>     # Xsrc write
*(short *)(gp-0x630c + k*2) = <interpolated across 2 adjacent speed records>     # Ysrc write
```
Plus 8 consecutive unconditional monotone-enforcement rungs on `gp-0x630c..gp-0x62fc` (Ysrc), matching
`reference_accord_ram_lerp_is_flash_derived_and_fprime_nonneg.md` exactly, re-confirmed fresh.

**This closes the loop, both directions, this session:** forward from `FUN_000352b4`/`FUN_000352a0`
landed on `gp-0x6444`-family; backward from `FUN_000382d8` (already known from memory to write
`gp-0x6350`/`gp-0x630c`) landed on the same cells via `FUN_000389ec`'s Branch A/B fork.

## 4. The `0xC6564` blocker — resolved, NOT the off-by-0x1000 trap [EVIDENCE, triple-confirmed]

Per the brief's explicit instruction to re-derive from the instruction, not the note:
- Fresh `decompile_function 0x39702` (`FUN_00039702`) shows the literal reads: `*(short
  *)(unaff_tp + 0x7564)` through `0x7588` — **the displacement really is `0x7564`, not `0x6564`**.
  `tp + 0x7564 = 0xBF000 + 0x7564 = 0xC6564`. **This is NOT the off-by-0x1000 trap** — the trap would
  require the code to say `tp+0x6564`, and it does not.
- Fresh `read_memory 0xC6564` length 40, this session: **all zero**, independent of the two prior
  memory confirmations (2026-08-05 and the `build_v67..v70_tva.py` assertions, `grep`-verified this
  session — `R26_AVG_CAL = 0xC6564`, asserted "40 bytes of exact zero" in v67/v68/v69/v70, never edited,
  only asserted-unchanged).
- **Mechanism, now clarified**: `local_5c[k] = cal(0xC6564-family)[k]/1024 + gp-0x6444-family[k]/1024`
  is a **feedback read of `gp-0x6444`-family's OWN PREVIOUS-TICK value** (since `FUN_00039702`'s sole
  caller is the same `FUN_00022ca0` that calls `FUN_000389ec`, and `FUN_000389ec` reads `gp-0x6704`-family
  — `FUN_00039702`'s own output — "at its own entry", meaning `FUN_00039702` runs FIRST, before
  `FUN_000389ec` has recomputed `gp-0x6444`-family this tick). Blended via a temperature/voltage
  hysteresis selector (`tp+0x7390..0x739e`), it drives **a state/gate flag** (`gp-0x6926`/`gp-0x3740`),
  **not** the numeric knot content. `FUN_000389ec`'s own caller: `get_function_callers` →
  `FUN_00022ca0` (sole caller, matches `FUN_000382d8`'s sole caller too).

**⇒ The zeros are real and the causal role is now fully mapped: a confirmed-inert feedback/gating
side-channel, structurally separate from the main numeric path in §2-3. It does not mean "no ROM
source" — it means this ONE specific side-input to a gate is zero.**

## 5. Blast radius / build-lineage grep [EVIDENCE]

`grep` of every `build_v*_tva.py` for `0xC6564`, `0xC7B40`, `0xD6158`, `0xD7130`, `0xC6384`, `0xC6178`,
`0x352a0`, `0x352b4`, `0x37fc`, `0x37e8`, plus a RAM-cell sweep (`0x6444`, `0x6442`, `0x642e`, `0x69a4`,
`0x6350`, `0x630c`):

| cal/cell | builds referencing it | what they do |
|---|---|---|
| `0xC6564` | v67, v68, v69, v70 | **assertion only** — "must still be 40 zero bytes", never edited |
| `0xC7B40`, `0xD6158`, `0xD7130`, `0xC6384`, `0xC6178` | **none** | never referenced by any build script |
| `FUN_000352b4` | v103 (docstring only, re: the dead biquad / DF-style filter) | not an edit to `gp-0x37fc`/`gp-0x37e8` |
| `gp-0x69a4` | v62, v70 (docstrings, "r26's slope factor", "unmeasured magnitude") | not an edit |

**⇒ Every cell named in this trace is FALSIFIED-NEVER — untouched by any build to date.** No prior
on-car result exists for any of them.

## 6. The mode-indexing / blast-radius reconciliation — the key trade-off [EVIDENCE + BELIEF]

**Mode-indexing of the ROM record itself: YES**, confirmed via the SAME `FUN_000382d8`/`0xC7B40`-array
mechanism already fully mapped for the Stage-2 LERP by `reference_accord_stage2_knot_edit...` (m24 @
`0xD6158+0x78*j`, m26 @ `0xD7130+0x78*j`, mode byte `gp+0x63fd`). [BELIEF, not re-read byte-for-byte
this session, but the SAME physical bytes are what `FUN_000382d8` writes into `gp-0x6350`/`gp-0x630c` —
this is the identical mechanism, not a re-derived analogous one.]

🛑 **Correction flagged for `reference_accord_stage2_lerp_rescale_is_identity_and_ivar6_bound.md`**:
that memory says mode 24 and mode 26 in this record family are **NOT fully byte-identical** ("mode 24
differs only in Y[8], <2%; rec[0]/[3]/[4]/[5] + breakpoints differ") — different from the clean
byte-identical case documented for r24's own gain table and the damper families. A mode-26-only edit
is still possible (the records are physically separate either way) but does not start from a perfectly
clean baseline.

🛑🛑 **THE CENTRAL FINDING: no single edit found this session is both scoped-to-Path-1 (`gp-0x6b86`)
and engagement-conditional at once.**

- **Editing the shared ROM record (mode-26 only, `0xD7130`-family Y-knots — exactly what
  `reference_accord_stage2_knot_edit...`'s KNOT F / H2 levers already propose)**: IS
  engagement-conditional (mode-24/manual untouched) — but **reaches BOTH Path 1 (`gp-0x6b86`, this
  task's target) AND Path 2 (`gp-0x6b70`→PID-reference-clamp, a separately-characterized lane) at
  once**, because both are downstream of the SAME `gp-0x373c[]`/`gp-0x3714[]` (§2). **This overturns
  `reference_accord_stage2_knot_edit_is_a_hands_on_specific_lever.md`'s own "Blast radius = the Stage-2
  LERP ALONE" claim** — that memory did not know about the Branch-B fork into Path 1. Flagging this
  correction explicitly; I have not edited that memory file per the operator's "ask before updating"
  standing instruction.
- **Editing the Path-1-specific downstream cals (`0xC6468`=2639, `0xC6178`=5274, in the slot-fill/slew
  loop, §2 Branch B)**: IS Path-2-clean (Stage-2 LERP/`gp-0x6b70` untouched, confirmed structurally —
  Branch A copies `gp-0x373c`/`gp-0x3714` BEFORE Branch B's transform, and Branch B never writes back
  to them) — **but is NOT mode-indexed at all**. The slot-fill loop runs unconditionally on every tick
  regardless of mode; only the upstream `Xsrc`/`Ysrc` selection consults the mode byte. **Raising or
  lowering `0xC6468`/`0xC6178` changes `gp-0x37e8[]` in manual steering exactly as much as in engaged
  steering** — directly at odds with the operator's "don't touch manual/base steering" preference.

**[BELIEF, single careful decompile pass, NOT instruction-level-confirmed or numerically simulated]**:
`cal(0xC6468)` appears twice in Branch B's formula (once in `SCALE`'s numerator, once as `uStack_b8`'s
divisor) and both appearances push the final slot value in the SAME direction — **lowering
`cal(0xC6468)` should RAISE the slot value monotonically** (higher `SCALE`→lower `slew_target`→larger
delta; lower `uStack_b8`... wait, corrected: lower `cal(0xC6468)` → lower `SCALE` → lower `slew_target`
→ LARGER `(gp-0x373c[iter] - slew_target)`; AND lower `cal(0xC6468)` → HIGHER `uStack_b8` (it's a
divisor) → the delta gets multiplied by a larger `uStack_b8`. Both effects raise the final slot value.
This is a **promising, narrow, Path-2-clean lever** but its magnitude has NOT been numerically resolved
this session — see Open Items.

## 7. Dose ceiling, independent of which edit is chosen

`cal(0xC6384) = 2048` (2.000, §1) is the hard per-segment slope ceiling on `gp-0x37e8[]`, **downstream
of every mechanism in this trace** and untouched by any upstream choice. The task's target dose
(`a`: 0.098 → ~0.146, i.e. +49%) sits far below this structural ceiling (2.000) and below the task's
own independently-derived "mean slope ≤ 0.644" bound — **the slope cap is very unlikely to be the
first thing that binds for this specific dose**, though I have not proven no single segment near the
current operating point is already close to ITS OWN local cap (would need the actual current `gp-0x37fc`/
`gp-0x37e8` runtime content at the operating point, not read this session).

## Open items — exact next step to close each

1. **Numeric transfer function, ROM-knot-edit → `gp-0x37e8[]` dose.** Not simulated this session.
   Next step: read `tp+0x713e`, `tp+0x7140`, `tp+0x717a`, `tp+0x717c` (the remap-loop thresholds),
   `tp+0x7b66..0x7b98` (the boost-curve LERP feeding `uVar48`/`uStack_b6`), `tp+0x713a` (`cal(0xC613A)`,
   already flagged multi-purpose/high-risk elsewhere), and the current live `0xD7130`-family Y-knot
   bytes; write a Python simulation of §2 Branch A+B and §1's loop end-to-end with concrete stock values.
2. **`cal(0xC6468)`'s magnitude, not just direction.** [BELIEF only, §6.] Next step: same simulation as
   #1, or `disassemble_bytes` on the exact instructions to remove any remaining risk of a hand-tracing
   sign error before this is treated as EVIDENCE.
3. **Byte-identity of `0xD6158` vs `0xD7130` records, specifically for the knots that matter to `a`'s
   dose.** [RELAYED from `reference_accord_stage2_lerp_rescale...`, not re-read this session.] Next
   step: `read_memory` both records' Y-arrays directly.
4. **Other readers of `cal(0xC6468)`/`cal(0xC6178)`/`cal(0xC613A)`.** Flagged as "not independently
   re-swept" in the 2026-08-05 memory and still not swept this session. Next step: `search_instructions`
   + raw Python LE scan (adjudicated) for each, per this kit's dual-method standing requirement.
5. **`FUN_00022ca0`'s own call order** (does it call `FUN_000382d8` → `FUN_00039702` → `FUN_000389ec` →
   `FUN_000352b4` in that sequence, same tick?). Believed yes from data-flow necessity (§2, §4) but not
   directly decompiled this session — `decompile_function 0x22ca0` would close this to EVIDENCE.

## Related memory

`reference_accord_stage2_lerp_rescale_is_identity_and_ivar6_bound.md`,
`reference_accord_ram_lerp_is_flash_derived_and_fprime_nonneg.md`,
`reference_accord_stage2_knot_edit_is_a_hands_on_specific_lever.md` (blast-radius correction flagged,
§6), `reference_accord_gp69a4_slot_fill_slew_mechanism_and_0xc6564_link_corrected.md` (fully confirmed
and extended, not superseded), `reference_accord_fun352b4_full_chain_gp6b82_tap_and_c6200_shared_clamp.md`,
`reference_accord_r24r26_live_gain_is_default_lerp_and_phase_discrepancy.md`.
