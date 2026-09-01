---
name: firmware-decompile
description: Ghidra/V850E2 decompilation traps for the 2020 Accord EPS firmware — encoding forms that scans miss, tools that silently undercount or mutate the database, and address-arithmetic errors that have each produced confident wrong answers. Load whenever a session reads firmware bytes, disassembles, or scans for gp/tp-relative accesses.
---

# Ghidra / V850 traps — 2020 Accord EPS (`39990-TVA-A160`, Renesas V850E2, little-endian)

`gp = 0xFEDF8000`, `tp = 0xBF000`.

**Prime every subagent with these explicitly.** Each one below has produced a confident wrong answer in
this kit at least once; several have recurred.

## Encoding forms a naive scan misses

- **`hw2 = disp|1`** for `ld.hu`/`ld.w` — a scan for the bare displacement misses them entirely.
- **gp/tp-relative accesses have TWO encodings** — 4-byte disp16 and a 6-byte extended-displacement
  form. A disp16-only scan is blind to the second.
- **`ld.bu` carries displacement bit 0 in hw1 bit 5**, not in hw2 — so an **odd** displacement encodes
  as opcode field `0x3D` / hw1 `a437`, an **even** one as `0x3C` / hw1 `8437`. Two cells one apart sit
  on opposite parities: an encoder or scan assuming one parity **silently addresses the neighbouring
  cell with every other field perfect.**

- **`jarl` disp22 is opcode field `0x1E`** (hw1 bits 6-10), not `0x1B`. Getting it wrong is not a quiet
  failure: `0x1B` matches **4,448 sites** across the code region and resolves **zero** real calls, so
  the scan looks like it ran and returns a confident, empty answer. Cost a wrong "dead code" verdict
  on 2026-08-31 before the control below caught it.

## 🛑🛑 POSITIVE-CONTROL EVERY SCAN BEFORE YOU TRUST A NULL

**This is the rule that catches all of the above, including the ones not yet discovered.** Every trap in
this file has the same shape: a hand-rolled decoder returns **zero hits**, and zero hits reads as a
finding rather than as a broken tool.

> **Before reporting "N callers", "no writers", or "zero readers", run the SAME scanner against a case
> you already know exists.** If it cannot find the known one, its null is worth nothing.

Cheap controls that are always available: `FUN_00028ea6` is called from `0x22522`; `FUN_00034350` from
`0x23276`; `FUN_0003aa2c` from `0x2291e`. For a gp/tp cell, pick one the decompiler visibly reads and
confirm the scan finds that site. **A scan that finds the control and then finds nothing at the target
is EVIDENCE; a scan that was never controlled is a guess with a number attached.**

⊕ And when two methods disagree, **do not average them** — find which one the control breaks.

## Tools that lie

- **`search_instructions` counts only already-analysed instructions** and reports `truncated:false`
  while undercounting. It has produced wrong reader/writer sets **at least four times**. Always confirm
  a load-bearing count or null with a raw Python little-endian byte scan.
- **`disassemble_bytes` MUTATES the database** on undefined regions unless `dry_run:true`. Never
  `save_program` after exploratory disassembly.
- A **stale Ghidra import defeats hash-checking** — an open program can hold an earlier revision while
  the on-disk SHA verifies. Re-import fresh and spot-check one edited site against a Python byte read.

## Address arithmetic

- **Off-by-0x1000 on tp-relative cals has recurred four times.** `tp = 0xBF000`, so `tp+0x6000` is
  **`0xC5000`** (the risky model-coeff block), *not* `0xC6000`. The main cal block is
  `tp+0x7000..0x7FFF`. **Anchor against a known value before trusting any tp-relative address.**

## Byte-level work

- Diffing builds, CRC checks, dumping a table, checking an extent is **Python**, not Ghidra — and
  Python is the **required second method** whenever a count or a null result is load-bearing.
- **Never whole-file diff a built image against the stock dump** — `build_*.full_image()` writes `0xFF`
  filler below `0x13000` and a naive diff reports ~51,000 bogus bytes. Restrict to
  `[0x13000, 0x100000)`.

## Further reading

- `memory/reference/tooling/reference_rizin_ghidra_v850_quirks.md`
- `memory/accord/firmware/accord-v850-scan-traps-formatv-and-storezero.md` — includes a validation harness
- `docs/guides/FIRMWARE-DECOMPILE-GUIDE.md`, `docs/guides/GHIDRA-CHECKLIST.md`
