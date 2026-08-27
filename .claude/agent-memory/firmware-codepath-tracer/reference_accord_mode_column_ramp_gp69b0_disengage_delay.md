---
name: reference_accord_mode_column_ramp_gp69b0_disengage_delay
description: "The engaged/manual mode-pair selector (gp-0x67f6, feeding gp+0x63fd) does not flip on the same tick LKAS disengages -- it is gated behind gp-0x69b0, a 1kHz ramp inside FUN_00028ea6 (true extent 0x28ea6-0x2a30d) that must land EXACTLY on 0 or -32768 before FUN_00042746 (100Hz) will reselect. Five calibrated per-tick rates found (16/33/66/328 ct), giving 100ms-2048ms full-range traverse, plus a further ~40ms commit-hold. Mechanistically explains the multi-second post-disengage 'damper still active' tail already measured on-car in accord-v74-fault-damper-WAS-in-force-mode-lag. Entirely stock/untouched by V106/V107."
metadata:
  type: reference
---

# The mode-pair selector has a real, multi-branch, non-instantaneous release ramp

**2026-08-26, subagent trace for `main`, task: "why does grinding persist a few seconds after LKAS
disengages on V107."** All addresses fresh-decompiled/read this session on `code.bin` (stock), GhidraMCP
only. `gp=0xFEDF8000`, `tp=0xBF000`.

## THE CHAIN [EVIDENCE]

```
FUN_00028ea6 (1kHz, sole caller FUN_0002214a — the confirmed control task)
   ramps gp-0x69b0 toward one of two literal-constant rest states:
      DISENGAGED rest = 0            ENGAGED rest = -32768 (0x8000)
   via ADD/SUB of one of >=5 distinct calibrated rates per tick (see table)
        |
        v  (gp-0x69b0 must land EXACTLY on 0 or -0x8000)
FUN_00042746 (100Hz, sole caller FUN_00022ca0 = task 5)
   only THEN may flip gp-0x67f6 (0=disengaged pair 24/25, 1=engaged pair 26/27)
        |
        v  (further gated by a ~40ms "commit hold", see below)
   writes gp+0x63fd = the mode-index byte FUN_00034350 (damper)/FUN_00034a72 (boost)/
   FUN_00036c12 (friction, gp-0x6b26) and everyone else in the TVCA4 family reads.
```

`FUN_00042746` decompile (key fragment, disengage side):
```c
cVar2 = *(gp-0x6806);   // latActive
sVar4 = *(gp-0x69b0);   // the ramp value — must be EXACTLY at a rest state
if (cVar2 == 0) {                                // DISENGAGED
   if (sVar4 != 0) return;                        // not settled yet -> no reselect this tick
   if (cal(0xC6180)=1024 <= *(gp-0x4f68)) return;  // plausibility gate, see caveat below
   cVar5 = 0;
}
...
gp-0x67f6 = cVar5;   // ONLY written once gp-0x69b0 has fully settled
```

## `gp-0x69b0`'s ramp rates [EVIDENCE — Ghidra `search_instructions` + mandatory Python raw-LE
byte scan honoring the `ld.hu hw2=disp|1` encoding, cross-checked, every hit adjudicated]

| cal | tp-relative | value (ct/1kHz-tick) | full 32768-count traverse |
|---|---|---|---|
| `0xC63F4` | tp+0x73f4 | 328 | 100 ms |
| `0xC63F6` | tp+0x73f6 | 16  | **2048 ms** (slowest found) |
| `0xC63F8` | tp+0x73f8 | 33  | 993 ms |
| `0xC63FA` | tp+0x73fa | 66  | 497 ms |
| `0xC63FC` | tp+0x73fc | 328 | 100 ms |

**All five read EXCLUSIVELY by `FUN_00028ea6` — zero external readers, confirmed two ways.** `FUN_00028ea6`'s
TRUE extent is `0x28ea6`–`0x2a30d` (~5.7 KB, `get_function_by_address`) — nearly double what a first-pass
`decompile_function` call rendered (it truncates around ~1300 lines / ~`0x29734`). A raw byte scan found
extra real occurrences of every rate cal in an un-decompiled tail (`~0x2a570`–`0x2a8xx`, confirmed real
V850 code via `disassemble_bytes` dry_run, e.g. a THIRD engage/disengage-rate site at `0x2a5ac`/`0x2a5b6`
using rate 328 to set `gp-0x6806=1`) — **still inside the same function, so "sole reader" stands, but the
state machine has more branches than a single `decompile_function` call will show you.** Budget for this:
either read the saved-JSON-then-Python-slice pattern across the WHOLE `0x28ea6-0x2a30d` range, or use a
live probe on `gp-0x69b0` across a real disengage.

**The commit-hold**: `gp-0x68ab` (a "reselect in progress" flag) blocks the ACTUAL `gp+0x63fd` byte-write
even after `gp-0x67f6` is ready to flip, until `cal(0xC624E)=40` ticks of `gp-0x3e54` (confirmed the
1kHz free-running tick counter — written in `FUN_0002214a` at `0x22182`) have elapsed since the hold was
armed. **~40ms.** This is the SAME cell the pre-existing `accord-v74-fault-damper-WAS-in-force-mode-lag`
memory cited as "0xC624E=40, not the multi-second lag" — that framing is CORRECT (it IS short), the
multi-second budget comes from the `gp-0x69b0` ramp instead, which that earlier session had not found.

## 🛑 CORRECTION to `accord-stock-mode24-equals-mode26-damper-is-ours` (shared project memory)

That memory's decompile note says `FUN_00042746` is "**debounced by counter `gp-0x4f68` against cal
`tp+0x7180`**." Re-traced this session: **`gp-0x4f68` is NOT a counter.** It is a shadow-locked
(paired with `gp-0x448c`, the same `FUN_0006b9ee`-mismatch-faults-to-DTC pattern as `gp-0x4f64`/`gp-0x448a`
in the governor) **resolver/motor-angle-residual magnitude**, computed and written exactly once, in
`FUN_0007f3f8` (a dense DEM-style sensor-plausibility function, ~250 lines decompiled, full of
`FUN_0005bb04`/`FUN_0005ae6a`/`FUN_0005afba` DTC-debounce calls). Its use in `FUN_00042746`
(`< cal(0xC6180)=1024`, `< cal(0xC6182)=512`) reads as a **plausibility interlock** ("don't reselect the
assist mode while the resolver disagrees with itself"), essentially always-pass in healthy driving — not
a time-domain debounce. **Flag for the project memory's owner to correct** — I did not edit the shared
file myself (subagent, project memory belongs to the operator/orchestrator to update).

🛑 Also note for the record: I personally hit the kit's own documented **off-by-0x1000 tp-relative trap**
mid-session while re-deriving these very addresses (computed `tp+0x724e` as `0xC724E` instead of the
correct `0xC624E`, read the wrong cell, got a plausible-looking wrong number) — caught it against
`firmware-decompile` skill before reporting. Correct method: `tp=0xBF000`; add in hex digit-by-digit,
or just use Python (`tp + offset`) rather than mental hex arithmetic.

## Why this matters — mechanistic explanation, not just corroboration, of an existing telemetry finding

`accord-v74-fault-damper-WAS-in-force-mode-lag` (V74 era) measured the ENGAGED-mode damper active-flag
holding for up to 4-6s post-disengage on two separate drives (bulk of activity in 0-3s: 28-45% in the
first second, decaying to 0.000% by 4-6s) and left the ROM mechanism for that hold explicitly **unpinned**
("closeable only with a live probe... bytes alone will not get the number"). This session found that
mechanism: a real, calibrated, multi-branch ramp with a slowest confirmed segment alone worth ~2.05s,
entirely independent of and predating any dose this kit has ever applied. **`0xC63F4/F6/F8/FA/FC`,
`0xC624E`, `FUN_00028ea6`, `FUN_00042746` are all byte-identical stock through V107** (only
`0xD7A5C`/`0xD7A6C` Y-rows and V107's 427-tap bytes differ) — the delay is Honda's, the audible
consequence during it (3x/reshaped `gp-0x6b26` opposition instead of stock's flat ~1.5x) is ours.

## OPEN — exact rate for the ordinary fault-free disengage
Not closed. At least 3 distinct rate-selection sites exist in `FUN_00028ea6` (`~0x296f8` rate=16,
`~0x2a5ac` rate=328 but that one is the ENGAGE direction, and at least one more unlocated near
`0x2a6xx-0x2a8xx`). The branches key off `gp-0x6807` (=STEER_STATUS, confirmed via
`v36-debounce-sm-root-cause-and-build`), `gp-0x6803`, `gp-0x6805`, `gp-0x679e`, `gp-0x3d38` (an internal
sub-state), none of which I fully enumerated. Best current candidate for "ordinary case" is rate=16
(2048ms), flagged BELIEF not EVIDENCE. Next step: full read of `FUN_00028ea6` across its whole
`0x28ea6-0x2a30d` extent (one `decompile_function` call exceeds the tool's token cap at 54KB — read the
saved JSON with Python line-slicing, as done this session), or a live probe on `gp-0x69b0` across a real
disengage event.

## UPDATE, same session — V107's OWN delta narrows the reachable branches, and two more discoveries

**[EVIDENCE]** Byte-exact diff of the flashed V107 image vs stock (`[0x13000,0x100000)`) shows V107 carries
**`0xC61C0/C2/C4`→0xFFFF and `0xC64B4-B8`→0xFF** (V36/V37's gentle-EME debounce disable — `STEER_STATUS`
can never become 4) **and `0xC62EA`→0** (low-speed lockout disabled since V53, per the parallel `hfmech`
session's `reference_accord_c62ea_disabled_since_v53_does_not_explain_lowspeed_dropoff.md` — `STEER_STATUS`
can never become 3 either). ⇒ **on V107 specifically, `gp-0x6807`(STEER_STATUS) can only be 0 (nominal) or 7
(hard DTC fault) during ordinary driving.** My original candidate branch for the ~2048ms rate
(`LAB_000296f8`, gated on `STEER_STATUS==3` exactly) is therefore **very likely UNREACHABLE on this specific
build** — the branch exists in the code but the precondition that would select it is disabled by two earlier,
unrelated builds in the same lineage. **Which branch fires for `STEER_STATUS==0` specifically is still not
resolved** — traced partway (sub-state `gp-0x3d38`==2, `STEER_STATUS==0`: at least one path is a pure NO-OP,
`gp-0x69b0` unchanged, control passing to `LAB_000296c6`/`LAB_00029734`, contents not read this session).

**Two more discoveries while tracing `FUN_00028ea6` for other purposes:**
1. **`0xC6CD0`, "the 8x gain carrier," is read from INSIDE `FUN_00028ea6` at `0x2a1ee`**
   (`ld.h 0x746c,tp,r7` in stock, repointed to `0x7cd0,tp,r7` — i.e. `0xC646C`→`0xC6CD0` — by an earlier
   build in the lineage; V107 carries stock=`6c74`→dosed=`d07c` at `0x2a1f0-2` as a 2-byte diff). Confirms/
   pins the exact address for `reference-accord-c646c-shared-gain-not-lkas-only`'s "V57 decouples the
   forward reader onto `0xC6CD0`" — that decouple point is inside the SAME function as the engage-ramp, not
   a separate one. Then `mulh r7,r13` against `sign(gp-0x6752)`. The surrounding block (`0x2a1a0-0x2a1e6`)
   has an internal branch gated on `latActive==0 AND r16==1` (meaning of `r16` not identified). **`gp-0x69b0`
   does NOT appear anywhere in this block's operands** — ruled out as this multiply's input.
2. **A previously-unidentified mode/gear-table pointer array, `0xCB844`→{`0xE4180`,`41A8`,`41D0`,`41F8`,
   `4220`}, is read ONLY from inside `FUN_00028ea6`** (`get_xrefs_to(0xCB844)` → `0x28fd6`/`0x28fda`, both
   in that function; matches `MEMORY_CONSTELLATION.md`'s "mode/gear LERP pointer arrays 0xCB844→0xE4180.."
   note, now with the reader pinned). **Selector is `gp-0x674e`, set exactly ONCE at boot** by
   `FUN_00042692` (`(&DAT_0000e01a)[FUN_00057f8e()*0x24+tp]` — the same car-variant config-row lookup that
   picks TVCA4/row 11) — **NOT `gp-0x67f6`/the mode column.** ⇒ whatever this 9-breakpoint LERP computes is
   IDENTICAL manual or engaged on a given car. V107's lineage raised the Y-values (`0x3C00`→`0x4000`,
   +6.7%) on 4 of the 5 records — **not the one this specific car actually selects, most likely** (role/
   selected-index not resolved), so likely inert on THIS car regardless, but flagged as unidentified rather
   than assumed. What this LERP's output (`r16` at `0x28fec`/`0x29002`) feeds into downstream — possibly
   the same `r16` gating the `0xC6CD0` block above — **not traced.**

**`gp-0x69b0` — GATE, not multiplier.** [EVIDENCE, with an honest gap] Of 45 raw `search_instructions` hits
on operand `69b0`, ~40 real touches are ALL inside `FUN_00028ea6` and are exclusively load/compare/add-
subtract/store on the ramp's own state (zero `mul`/`mulu`/`mulh` found operating on it anywhere traced);
1 touch is in `FUN_0002a93a`, already established dead code; 1 is the `FUN_00042746` sentinel-equality
check; 2 are branch-target coincidences. Structural support: `gp-0x69b0` is SIGNED (rests at `0`/`-32768`),
unlike every genuine Q15 crossfade weight elsewhere in this firmware (governor authority MIN-chain, EME
`gp-0x6966`), which are unsigned `0..32768` — a direct multiply would need an unseen `abs()`/remap step.
**Gap**: did not forward-trace all ~20 individual load sites for a register-mediated multiply a few
instructions later (invisible to an operand-text search), and ~30% of the function (`0x2a570-0x2a8xx` tail)
still unread. High but not exhaustive confidence.

Related: [[reference-accord-car-is-tvca4-mode-24-26]] (external, `memory/reference/firmware/`),
[[accord-stock-mode24-equals-mode26-damper-is-ours]] (external, needs the gp-0x4f68 correction above),
[[accord-v74-fault-damper-WAS-in-force-mode-lag]] (external — the telemetry this mechanism explains),
[[accord-v106-built-gp6b26-x3-mode-proof]], [[accord-v107-built-reshape-b-and-tap]] (external — the doses
riding on this stock ramp).
