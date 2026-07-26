---
name: reference-tva-bootloader-crc-scheme
description: "Accord TVA V850 bootloader integrity = CRC-32 linked-list walk verified by checkProgrammingDependencies (0xFF01). Solved the long-open 0xFCB8212C 'final word' = CRC-32 over [0xFD000,0xFFFFC). code.bin passes all 49 blocks. A single block mismatch -> UDS NRC 0x72."
metadata:
  node_type: memory
  type: reference
  source: claude
---

**Solved 2026-05-24** by radare2 v850 disasm of `code.bin` + Python replay (`analysis-2020accord/verify_bootloader_crc.py`, all 49 blocks reproduced). Full writeup now: `analysis-2020accord/HOW_TO_BUILD_ACCORD_TVA_RWD.md` §5 (was `BOOTLOADER_CRC_SOLVED.md`, since distilled). The CRC walk is the **pre-flash validation gate**, and it has now been vindicated end-to-end: the V9b build passed 49/49 and **flashed successfully** (see [[project-2020accord-v9-cipher-fix-2026-05-24]]).

## What the dependency check actually verifies

`checkProgrammingDependencies` = UDS RoutineControl `0x31 01 FF01`. Handler chain:
`FUN_0xCC4E` (RoutineControl) → verdict worker `FUN_0xB0AE` → CRC verifier `FUN_0xB006` → CRC primitive `FUN_0xAE4C` (HW DCRA unit @`0xFF836020` = Ethernet CRC-32 = `zlib.crc32`, accumulator seeded `0xFFFFFFFF`).

`FUN_0xB006` walks a **backward linked list of variable-length CRC-32 blocks**:
- Region end `E = start + length` (for the accepted window: `0x13000 + 0xED000 = 0x100000`).
- Each block's trailer is `{start_page:u16, num_pages:u16}` at `[E-8]/[E-6]`; page `p` → byte addr `p<<12`; block length = `(num_pages<<12) - 4`; stored CRC at `block_start + length`.
- The next (lower) block's page fields live 8/6 bytes below the current block's start.
- Special bridge: when a block start == `0xC6000`, jump to the **main block** `[0x13000, 0x13000+0xB1FFC) = [0x13000, 0xC4FFC)`, CRC stored at `0xC4FFC`.
- Walk terminates when block start == region start (`0x13000`).

For stock `code.bin` this is **49 blocks** (calibration band `0xFD000`→`0xC6000` as ~4 KB/variable blocks, then the bridge to the one big main block). All 49 verify.

## The solved "final word"

| addr | stored | = zlib.crc32 over |
|---|---|---|
| `0xFFFFC` | `0xFCB8212C` | `[0xFD000, 0xFFFFC)` (0x2FFC bytes) — the long-"unsolved" top-of-flash word |
| `0xFCFFC` | `0x0B1AFC21` | `[0xF9000, 0xFCFFC)` |
| `0xC4FFC` | `0x48F24975` | `[0x13000, 0xC4FFC)` (main, 0xB1FFC bytes) |

## How to apply

- To validate any candidate `.rwd` BEFORE flashing: decrypt its payload into a 1 MB image at `0x13000` and run `verify_bootloader_crc.walk(img)`. 49/49 PASS ⇒ the image will satisfy `0xFF01`. The cipher-match caveat is now closed: V9b's cipher is confirmed (see [[reference-tva-cipher-operand-order]]), so for a V9b-encoded build a 49/49 walk is a true green light, not a conditional one.
- NRC `0x72` from `0xFF01` after a clean transfer means the bytes physically in flash failed this CRC walk — i.e. content/decryption is wrong, NOT addressing/state. (The granular `0x72` vs `0x22` distinction is real and surfaces on the wire; `0x72` = CRC-fail branch, `0x22` = region-not-programmed.)
- The actual erase/program/CRC primitives execute through a RAM function pointer `0xFEDF600C` (downloaded kernel, absent from `code.bin`); the decrypt + verdict logic, however, is all resident and analyzed.

## Cross-refs

- [[reference-tva-cipher-operand-order]] — why a CRC-valid `code.bin` can still fail this check (V8: wrong cipher → garbage flashed)
- [[reference-pilot-tg7-is-v850]] / [[reference-v850-sa-algorithm-tva]] — the V850 family context
- [[reference-rizin-ghidra-v850-quirks]] — tooling cautions when reading V850 disasm
- [[feedback-lightweight-inspection-over-ghidra]] — radare2 + Python script approach that cracked this
