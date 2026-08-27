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
