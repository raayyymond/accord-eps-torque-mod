---
name: accord-codecave-c4b34-c4fef-larger-than-documented
description: 2020 Accord TVA-A160 (V850E2, master.bin) — the documented code cave at 0xC4E00-0xC4FEF (496-528 bytes) is actually a SUBSET of a larger unbroken 0xFF run from 0xC4B34-0xC4FEF (1212 bytes), confirmed by direct read_memory and zero code/pointer references. Supersedes the smaller figure in [[reference_accord_can_tx_synthesis_2026-07-07]] for planning purposes.
metadata:
  type: reference
---

# Code cave re-measurement: true extent is 0xC4B34-0xC4FEF (1212 bytes), not 0xC4E00-0xC4FEF

Session 2026-07-13, read-only Ghidra MCP audit on `program="master.bin"`. Prior documentation
([[reference_accord_can_tx_synthesis_2026-07-07]], the mailbox-index-map file) cites "code cave
0xC4E00-0xC4FEF, ~528 bytes free" as the landing spot for a new CAN-TX builder stub (Table-B extension
plan). This session re-measured it directly.

## Method
`read_memory` sweeps (32-1212 byte reads) walking outward from the documented range in both directions
until hitting non-0xFF content, then one exhaustive single read across the full discovered span to prove
it's unbroken.

## Findings
- **0xC4E00-0xC4FEF (496 bytes, the exact documented sub-range): CONFIRMED all 0xFF** — direct
  `read_memory(0xC4E00, 496)` returned 496 bytes of `0xFF`, zero exceptions.
- **The 0xFF run extends further in BOTH directions than documented:**
  - High boundary: 0xFF continues through 0xC4FEF exactly, then **0xC4FF0 has real data**
    (`01 01 01 01 00 00 c6 00 13 00 b2 00 75 49 f2 48 ...`) — consistent with the CRC block boundary
    `[0x13000, 0xC4FFC)` cited in the mission brief (real data through ~0xC4FFB, then presumably outside
    the CRC-covered region from 0xC4FFC).
  - **Low boundary: real data (a float-constant-looking table, e.g. `00 00 16 43` = 150.0f at 0xC4000)
    continues through 0xC4B33, then 0xC4B34 onward is 0xFF.** Confirmed via a byte-level read at
    0xC4B20-0xC4B7F: bytes at offsets 0-19 (0xC4B20-0xC4B33) are real data ending `... 00 80 00 80 00 80
    00 80 00 00`, byte at offset 20 (0xC4B34) is the first `0xFF` and everything after is `0xFF` through
    the rest of the checked range.
- **Single confirming read**: `read_memory(0xC4B34, 1212)` (i.e. exactly through 0xC4FEF) returned **1212
  bytes, every single one 0xFF** — one unbroken run, not two coincidentally-adjacent free regions.
- **True length: 0xC4FEF - 0xC4B34 + 1 = 0x4BC = 1212 bytes** — roughly 2.3x the previously-documented
  ~528 bytes (which itself, on reflection, likely referred to the true 0xC4DE0-0xC4FEF sub-span = 528
  bytes exactly, i.e. the "~528" figure predates this session's discovery of the additional 0xC4B34-0xC4DDF
  span but was already more accurate than the "0xC4E00" round-number citation in this session's mission
  brief — the true full cave is bigger than BOTH prior figures).

## Reference check — no code or data references into the extended range
`search_instructions` (operand substring, program-wide, exhaustive/non-truncated each time) for `c4b3`,
`c4c`, `c4d`, `c4e`, `c4f`, plus anchored full-prefix forms `000c4e`/`000c4f`, plus `search_byte_patterns`
for the little-endian 32-bit literal of the range start (`0xC4B34` → `34 4b 0c 00`) and several points
inside the documented sub-range (`0xC4E00`, `0xC4F00`, `0xC4E80`, `0xC4F80`) — **zero genuine hits**. Every
raw substring match was individually verified to be either (a) an unrelated branch/jarl target address
with a different, non-overlapping high-order prefix (e.g. `0x0003c4e2`, `0x0007c4e6` — coincidental low
digits only), or (b) an unrelated gp/tp-relative displacement resolving to a completely different
absolute address (e.g. `-0x4c4c,gp` → 0xFEDF33B4 RAM, or `0x7c4d,tp` → 0xC6C4D, a different data blob
~0x1000+ bytes away). None resolve into [0xC4B34, 0xC4FEF].

## Verdict
**CONFIRMED via read_memory + search_instructions + search_byte_patterns, high confidence:** the true
free/unreferenced code cave is **0xC4B34-0xC4FEF, 1212 bytes**, entirely inside the CRC block
`[0x13000, 0xC4FFC)`. This is materially more headroom than the 496-528 byte figure used in prior CAN-TX
extension planning ([[reference_accord_can_tx_synthesis_2026-07-07]]) — worth revisiting if a builder
stub was scoped tightly against the smaller figure.
