---
name: reference_accord_config_key_gp6408_udsonly_writer_bss_no_boot_populator
description: gp+0x6408-0x640C (the 5-byte hardware-config key FUN_00057f8e matches against the 0xCD000 mode table) has EXACTLY ONE writer image-wide, confirmed 5 independent ways -- a UDS RoutineControl/WriteDataByIdentifier handler (FUN_000508e8) that takes bytes from an EXTERNAL request payload, NOT from the firmware's own ID string at 0x13100/0x14117. The cell is confirmed .bss (zero-cleared at boot, outside the .data-copy range). REFUTES team-lead's specific "ID-string tokenising broken by the build marker" hypothesis, but surfaces a bigger, NOT-YET-CLOSED question: if nothing else populates this key, mode 10/11 (what V72 and every prior mode-10/11-targeting build edited) may never be reached on a real running vehicle at all -- a computed-pointer boot-time populator (same blind-spot class as the known .data-copy loop) has not been ruled out.
metadata:
  type: reference
---

# gp+0x6408-0x640C config-key writer census — 2026-08-05, urgent dispatch

Team-lead traced the mode chain (`FUN_00042746` -> `FUN_00057f8e` -> `0xCD000` table, see
[[reference_accord_mode_selector_fun42746_closed_confined_to_10_11]]) to a hypothesis: the build script's
standard "39990-TVA-A160" -> "39990-TVA,A160" marker edit sits exactly inside the "TVA"+"A1" span that
forms the "TVAA1" signature `FUN_00057f8e` matches — if the signature is built by tokenising the ID string
on `-`, every modified build's config match would fail, defaulting to row 0 (modes 0-3) and explaining
every grind-#1-lever null in this kit's history. Task: find the writer of `gp+0x6408..0x640C` and
determine whether it depends on the ID string, and if so how.

## [EVIDENCE] The writer, confirmed 5 independent ways in one session

Exactly 5 `st.b` instructions, `0x509D4-0x509F0`, all inside `FUN_000508e8`, writing from `param_1[1..5]`
(an EXTERNAL buffer, i.e. an incoming request payload) gated behind a sub-function byte `==1`. Full
decompile: UDS-shaped (`FUN_0004cdfe(4)` session guard, NRC `0x31` rejection via `FUN_00020436(0x31)` on
no-match after write, re-init of CAN/session state on success). **This is a
WriteDataByIdentifier/RoutineControl-style diagnostic service handler — it never reads the firmware's own
ID strings at `0x13100`/`0x14117` at all.** `get_xrefs_to(0x63fd)`, `search_instructions("6408")`, a raw
disp16 byte scan (per-opcode rules), a raw disp23 6-byte extended-form scan, and an LE32-absolute-literal
scan for `0xFEDFE408-0xFEDFE40C` all agree: these 5 writes are the only ones image-wide. (One near-miss:
an LE32 hit at `0xFEDFE400`/`0xFEDFE404`, in an unrelated factory UART debug-menu function
`FUN_0004a8ca` printing "yeeVehCustomCod1/2" diagnostic fields — read-only, checked and excluded, does
not reach `0x6408`.)

**`get_function_callers(FUN_000508e8)` returns none** — reached only via one dispatch-table reference
found by LE32-literal-scanning its own address (file offset `0xB77A8`, record shape
`{0xCC, 8, &FUN_000508e8, 0x3B, 5}`, consistent with a UDS RID/DID table) — i.e. only reachable via an
actual diagnostic request, not a static/periodic call.

## [EVIDENCE] `gp+0x6408` confirmed `.bss`, per the boot-loop trace not a null scan

Per [[reference_accord_app_ram_layout_and_boot_init_loops]]: zero-clear loop `0x146C0` wipes
`0xFEDEC000..0xFEDFFFFF` unconditionally; `.data` copy `0x14766` only restores `gp-0x6E50..gp-0x2598` —
entirely NEGATIVE offsets. `gp+0x6408` (positive) is outside that range: zero-cleared at boot, never
restored from flash by either known boot loop.

## Direct answer to the hypothesis as posed

**Refuted, cleanly**: there is no ID-string-parsing code path into this cell, so "fixed-offset vs
delimiter-based" doesn't apply — neither mechanism exists. The build marker edit at `0x13109`/`0x14120`
does not touch anything this key-matching logic reads.

## 🛑 But this surfaces a LARGER, NOT-CLOSED question

If `FUN_000508e8` really is the only writer and no live UDS write has occurred on a given ECU, the key
sits at 5 zero bytes, matching none of the 16 ASCII-keyed rows (row 0's key is `"00000"`=`0x30`x5, not
`0x00`x5) — `FUN_00057f8e()` hits its no-match fallback (returns 0, indistinguishable from a genuine row-0
match), and mode resolves to row 0's candidates `[0,1,2,3]`, **never 10/11** — on ANY build, stock
included. This would mean the "mode 10/11" premise this kit's memory has assumed since
`docs/BUILD-LINEAGE.md`'s PN->key mapping was written may never be exercised on a live, driving ECU.

**NOT asserted as fact — the search for an alternate boot-time populator was not exhaustive.** The two
known boot loops (`0x146C0`, `0x14766`) both write via `sst.w rX, disp[ep]` with a COMPUTED `ep` — a
pattern this kit's own memory already documents as invisible to disp16 scans, disp23 scans,
`search_instructions`, and `get_xrefs_to` (the exact four methods used above, plus the LE32 scan which
only catches LITERAL pointer construction, not computed/looped addressing). A SEPARATE computed-pointer
loop (e.g. an EEPROM/NVM-restore step structured like the `.data` copy but targeting `gp+0x6400` region)
has not been ruled out. A real production ECU normally would have its config programmed at the factory and
retained in non-volatile storage — a purely-volatile, UDS-write-only config cell is an unusual enough
design that its absence should raise suspicion of a missed write path, not be taken as confirmation.

## Open items / next steps
- Find every `sst.b`/`sst.w` inside a loop whose base register is built via a `movhi -0x121`-style
  construction (same signature as the two known boot loops) and check whether any lands in
  `gp+0x6400..0x6410`. A blind `movhi -0x121` search returned far too many candidates (every gp-relative
  address construction in the image) to triage without narrowing by "feeds an `ep`-based store loop"
  specifically — not completed this session.
- If no such loop exists, the practical next step is an on-car UDS read of the current key value (subject
  to this kit's standing "never send CAN without explicit confirmation" rule) — the only way to settle
  whether a real vehicle's key is actually zero or has been factory/dealer-programmed at some point.

## Related
[[reference_accord_mode_selector_fun42746_closed_confined_to_10_11]] — the prior session's mode-chain
trace this one directly extends; its "TVAA1 = row 2, live mode is 10/11" conclusion is now conditional on
this open question, not independently settled.
[[reference_accord_app_ram_layout_and_boot_init_loops]] — source of the `.bss`/`.data` boundary and the
computed-`ep` blind-spot warning this entry's open item is built on.
