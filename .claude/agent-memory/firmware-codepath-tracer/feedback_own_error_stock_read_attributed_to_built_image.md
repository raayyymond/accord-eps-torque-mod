---
name: feedback_own_error_stock_read_attributed_to_built_image
description: Own error, corrected by team-lead 2026-08-09 — read a cal byte from stock code.bin (the only program open in Ghidra) and reported it as the value on built images (V85/V86/V86B) without opening or checking them
metadata:
  type: feedback
---

I claimed `0x3AA96` = `C5` (Lever B's gate byte) "on V85/V86/V86B" based on a Ghidra `read_memory`/decompile read of `code.bin` — the ONLY program open in Ghidra that session. I never opened or byte-checked any built plain image. Team-lead independently read the actual built images and found `0x3AA96` = `FB` (armed) on V84/V85/V86/V86B, `C5` only on stock and V81. My conclusion about a specific supporting fact was wrong; the broader structural argument it was embedded in (the shape argument — flat gain vs. differentiator, neither fits a band-localized lift) survived because it didn't actually depend on that one fact.

**Why**: I was mid-decompile of `FUN_0003aa2c` on `code.bin` (the address sits inside code I was already reading), and the temptation to just read the SAME open program for "what does the built image have here" is exactly how this slips in — the read succeeds, returns a plausible-looking value, and nothing in the tool call itself signals "this is the wrong program."

**How to apply**: 🛑 **Before reporting any build-specific byte value (V-anything, not stock), verify which program is actually open** (`list_open_programs` / `get_current_program_info`) and if it's stock-only, the value is a STOCK claim, not a claim about any build — full stop, regardless of how confident the surrounding analysis feels. Built-image byte values are a Python job (read the actual `.bin`/`_plain_image.bin` file for that build number from `../accord-firmwares`), not a Ghidra job, unless that specific build's image has been explicitly `open_program`'d in Ghidra this session. This is the same class of trap as [[feedback-stale-ghidra-import-defeats-hash-check]] (a stale IMPORT of the right file) but is actually worse — a live read of the WRONG file entirely, with no version-mismatch signal at all. Cross-check every build-specific claim against which program was open when the read happened, not just against whether the read itself succeeded.
