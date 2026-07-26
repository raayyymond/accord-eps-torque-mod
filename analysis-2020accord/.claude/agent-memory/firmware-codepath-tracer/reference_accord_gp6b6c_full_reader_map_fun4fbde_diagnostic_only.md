---
name: reference-accord-gp6b6c-full-reader-map-fun4fbde-diagnostic-only
description: gp-0x6b6c has exactly 1 writer (FUN_0002eda8) and 3 reader instructions across 2 functions (not "exactly two readers" as an earlier search_instructions sweep claimed); the missed reader at 0x4FFD0 is inside the already-known FUN_0004fbde, is diagnostic-only, and is SAFE for the planned gp-0x4f60 low-pass repoint.
metadata:
  type: reference
---

## Context
Dispatched to check a raw byte-scan hit: `ld.h -0x6b6c[gp], r10` at `0x4FFD0`, which an earlier
`search_instructions` sweep did not report (that sweep claimed "exactly two readers" of `gp-0x6b6c`:
`FUN_000339cc`@0x339d8 and `FUN_0004fbde`@0x4FC08). This matters because an upcoming build repoints
`FUN_0002eda8` (the producer of `gp-0x6b6c`) to write a LOW-PASS-FILTERED copy of `gp-0x4f60` instead of
the raw sample — safe only if nothing does a same-cycle raw-vs-filtered "shadow lockstep" compare (the
V27 brick class; DTC 0x1c/0x1d etc. are no-debounce hard-shutdown → motor-off + power-cycle).

## Full corrected reader/writer map (search_instructions, operand_pattern="6b6c", bare substring —
the earlier bracketed form `-0x6b6c[gp]` is a FILTER-SYNTAX ARTIFACT that returns 0 matches even though
the operand exists; Ghidra's own `operands` field renders as `"-0x6b6c, gp"` comma-separated, not
bracketed — reconfirms the standing "search_instructions null can be a filter artifact" lesson with a
concrete new example):

| Address | Function | Instruction | Role |
|---|---|---|---|
| 0x2f6fa | FUN_0002eda8 | `st.h r14, -0x6b6c, gp` | **WRITER** (the producer the planned build repoints) |
| 0x339d8 | FUN_000339cc | `ld.h -0x6b6c, gp, r14` | reader (matches prior sweep) |
| 0x4fc08 | FUN_0004fbde | `ld.h -0x6b6c, gp, r9` | reader (matches prior sweep) |
| 0x4ffd0 | FUN_0004fbde | `ld.h -0x6b6c, gp, r10` | **reader MISSED by the prior sweep** — same function as the row above, not a new function |

**Verdict on the "exactly two readers" claim: it undercounted an INSTRUCTION, not a FUNCTION.** Both
gp-0x6b6c reads live inside the one function `FUN_0004fbde` (body 0x4fbde-0x50441); the prior sweep found
that function once and missed its second internal read.

## FUN_0004fbde full characterization (body 0x4fbde-0x50441)
- **Caller:** `FUN_0002214a` only (`get_xrefs_to` → one hit, `UNCONDITIONAL_CALL` @0x22480). `FUN_0002214a`
  is the confirmed ~1kHz control task (see `control-task-tick-confirmed-1khz` memory). The call itself is
  unconditional every control-task tick, but the function's substantive body is internally gated on an
  enable byte `gp-0x68a2==1` (a diagnostic/logging-session flag) — the whole path containing BOTH
  gp-0x6b6c reads only executes when that flag is set at some point in the capture cycle. Reads as an
  opt-in diagnostic/freeze-frame recorder, not an always-on monitor.
- **Zero callees** (`get_function_callees` → "No callees found"). Corroborated by manual disassembly walk:
  no `jarl` instruction anywhere in the function. It never calls `FUN_00016de6` / `FUN_0004613e` /
  `FUN_000462e6` / `FUN_00027802` (the DTC-setter/shadow-validator family) or anything else — it is a pure
  leaf function. This alone rules out classification (b) (monitor-with-DTC-trip).
- **What 0x4FFD0 does with the value:** `ld.h -0x6b6c[gp],r10` → `shl 7` → round (`sar 0x1f`/`shr 0x16`
  idiom) → `sar 0xa` (net: gp-0x6b6c ÷ 8, rounded) → `cmp r10,r9; bge +6; st.h r10,-0x33ba[gp]`. r9 at
  this program point is the PREVIOUSLY-STORED sample of the SAME signal (either the fresh 0x4FC08 capture
  from earlier in this same call, scaled identically, or the persisted prior-cycle value reloaded at
  0x4fc92). This is a **self-referential running-MIN tracker on gp-0x6b6c against itself** — never
  compared against gp-0x4f60 or any other signal.
- **No cross-signal comparisons anywhere in the function.** The function tracks 4 independent
  "diagnostic extremum" channels this same way — gp-0x6b6c→gp-0x33ba, gp-0x4f60→gp-0x339e,
  gp-0x6a02→gp-0x33b8/-0x33b6, gp-0x6a52→gp-0x33b4/-0x33b2 — each gated by its own
  cal-table-lookup-vs-elapsed-counter check (`uVar15` vs `uVar9`, tables at `DAT_000c8fe8`/`DAT_000c91bc`/
  `DAT_000c9084`/`LAB_000cc740` indexed by `gp-0x674f`), each comparing ONLY a fresh sample of its own
  signal against ITS OWN previously-stored sample. gp-0x4f60 is read at 0x4fc32 (first-capture block) and
  again at 0x5004c (its own min-clamp block) — **never combined arithmetically or compared against the
  gp-0x6b6c-derived value at any point.** No `cmpf.s` (float compare) anywhere in the function either.
- **No command-path writes.** All stores are to a local `-0x33xx`-range persisted-state block and a final
  ring-buffer/history-shift target region at `gp+0x657c`..`gp+0x6588`-ish (positive gp offset, i.e.
  ~0xFEDFE57C — a completely different address region from command-path cells like gp-0x6b94/-0x6acc/
  -0x6ace/-0x6b98, which sit at large NEGATIVE gp offsets around 0xFEDF13xx-0xFEDF15xx). One incidental
  `set1 0x0,0x4c5e[r18]` (0xFEDF4C5E) bit-set gated on an unrelated flag `gp-0x68a9==1` — not related to
  gp-0x6b6c/gp-0x4f60 at all.
- **Consumers of the write targets:** `get_xrefs_to` on the ring-buffer address 0xFEDFE57C and on the
  persisted slot 0xFEDF4646 (gp-0x33ba) both returned zero references. Corroborated by a second method
  (`search_instructions` bare-substring "33ba") — the only 4 real hits on gp-0x33ba are all inside
  `FUN_0004fbde` itself (0x4fc2e, 0x4fc92, 0x4ffc0, 0x4ffe4); the ring-buffer target has no other reader
  found by either method. (A truly exhaustive proof would need a raw byte scan for the `movea 0x657c,gp`
  idiom, not done this session — but the architecture — truncated int8 multi-cycle-old "extremum" samples
  — is inconsistent with how this kit's real hard-shutdown monitors work, which are same-cycle int/float
  shadow twins, not historical ring-buffer diagnostics.)

## Verdict
`FUN_0004fbde` (and specifically the `0x4FFD0` read) is classification **(a) benign/diagnostic**. It is a
freeze-frame-style extremum/history logger, gated on a diagnostic-session enable flag, running in the
1kHz task's call tree but doing no command-path writes and no DTC-setter calls, and its only use of
gp-0x6b6c is a same-signal running-min compare. **Making gp-0x6b6c hold a low-pass-filtered copy of
gp-0x4f60 (by repointing producer `FUN_0002eda8`) does not risk a fault trip or command-path corruption
via this reader.** The other reader, `FUN_000339cc`@0x339d8, is NOT re-verified by this session and
should be checked before green-lighting the repoint if it hasn't been already (see
[[reference-accord-v48b-repoint-asymmetry-review]] for the sibling-lane precedent methodology).

## Related
- [[reference-accord-v48b-repoint-asymmetry-review]] — the precedent methodology for auditing a
  gp-0x4f60 repoint's lockstep/asymmetry risk across consumer lanes.
- [[control-task-tick-confirmed-1khz]] — confirms FUN_0002214a's rate, which bounds this function's max
  call frequency (actual diagnostic-capture frequency is lower, gated on gp-0x68a2).
