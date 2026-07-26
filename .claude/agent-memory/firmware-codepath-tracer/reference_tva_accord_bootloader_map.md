---
name: tva-accord-bootloader-map
description: Honda 39990-TVA (2020 Accord) RH850/V850E2 bootloader region boundaries, UDS service inventory, flash primitives, SA algorithm, and function table — byte/Ghidra verified 2026-06-01
metadata:
  type: reference
---

# Honda TVA Accord Bootloader Map (39990-TVA-A110/A160)

**ISA:** Renesas RH850 / V850E2, little-endian 32-bit  
**Flash execution base:** 0x00000000 (file offset = execution address; mirror at 0x07800000 for programming)  
**Verified:** byte-level + Ghidra decompile, 2026-06-01

## Bootloader Region Boundaries

- **Bootloader:** file 0x00000 – 0x0FFFF (64KB)
  - Dense code/config 0x0000-0x0FFF (vector table + config data)
  - Main BL code 0x1000-0x8C38 (confirmed by function map)
  - SA + flash primitives 0x5000-0x8BFF
  - SA seed gen (HW RNG) 0x816C, 0x8134
  - SRAM-resident flash writer: copied from 0x8BF0–0x8E3E to SRAM 0xFEDF0000 at runtime
- **Erased gap:** 0x10000–0x13FFF (16KB flash sector boundary)
- **Application code:** 0x14000–0x8B217 (continuous)
- **Large erased gap:** 0x8B218–0xB6FFF (unused)
- **Cal/data/config:** 0xB7000–0xFFFFF

## Entry & Boot

- **Reset vector:** file 0x0000 = `0x07800000` (self-referential; actual startup = second vector at 0x0004 = 0x07800012)
- **Vector table:** 0x0000–0x00FF — pointer array to flash addresses; also contains config data (MM register addresses at 0x0080–0x00BF, interrupt enablers at 0x00C0–0x00FF)
- **Startup code:** 0x0012 (second vector target)
- **Exception handler:** 0x7FFA
- **Secondary handler:** 0x3000 (vector slot 17)
- **Master BL API table:** 0x2000–0x205C (24 function pointers, stride-4)

## Master API Table at 0x2000

| Offset | Target | Name (inferred) |
|--------|--------|-----------------|
| 0x2000 | 0x7A16 | FlashLowLevel_1 (erase-enable) |
| 0x2004 | 0x7AF4 | FlashLowLevel_2 |
| 0x2008 | 0x7B84 | FlashLowLevel_3 (program) |
| 0x200C | 0x7ACC | FlashLowLevel_4 |
| 0x2010 | 0x7B3C | FlashLowLevel_5 |
| 0x2014 | 0x4C8C | BL_Init (takes block-descriptor ptr) |
| 0x2018 | 0x4DC4 | BL_StartSequence (sentinel 0x5555555A→0x555555A5) |
| 0x201C | 0x4C0E | BL_MainTick (periodic dispatcher) |
| 0x2020 | 0x4E4C | BL_GetStatus |
| 0x2024 | 0x4DFE | BL_StartDownload (sentinel 0x555555A5→0x55555A55) |
| 0x2028 | 0x4992 | BL_GetFreeSpace |
| 0x202C | 0x4A6A | BL_DownloadHandler (RD/TD logic) |
| 0x2030 | 0x4E9A | BL_GetResult_2 |
| 0x2034 | 0x4EE0 | BL_ClearEvent |
| 0x2038 | 0x4F20 | BL_GetLastError |
| 0x203C | 0x4F5A | BL_GetVersionInfo (ptr to EV850T05 string) |
| 0x2040 | 0x5D2C | SA_Init |
| 0x2044 | 0x5B0C | SA_GetSeed |
| 0x2048 | 0x5B4E | SA_SendKey |
| 0x204C | 0x5C80 | SA_GetState |
| 0x2050 | 0x5BAA | SA_Reset |
| 0x2054 | 0x5C4E | SA_related |
| 0x2058 | 0x5B4C | SA_boundary |
| 0x205C | 0x5D1A | SA_related2 |

## UDS State Machine

The BL implements UDS via a **state machine**, NOT a direct SID→handler dispatch table.

- **State variable:** `_DAT_fedf0228` (SRAM 0xFEDF0228)
- **State 9:** "scan all channels" (initial)
- **State 8:** no-op / return early
- **States 1–7:** channel-specific download states
- **Dispatch function:** `FUN_000048CA` at 0x48CA — loads handler table at 0x4F80, dispatches by `iVar1 * 0x10` index
- **Handler table:** 0x4F80–0x5033 (45 entries × 4 bytes, targets 0x322E–0x486C)
- **Main tick:** `FUN_00004C0E` at 0x4C0E (calls dispatch + handles sentinel)
- **Per-channel state:** 8 slots of 0x10 bytes each at `DAT_fedf0074[0..7]`

## UDS Services Implemented (by BL)

**BL implements services via the state machine + API table, not direct SID comparison in BL code. The SID-to-state mapping happens in the APPLICATION's UDS router (0x14000+), which calls into the BL API table at 0x2000.**

Inferred from BL API functions and state machine:

| SID | Service | BL Handler | Notes |
|-----|---------|-----------|-------|
| 0x10 | DiagnosticSessionControl | Application routes to BL_Init | Prog session triggers BL_Init (0x4C8C) |
| 0x27 | SecurityAccess | SA_GetSeed (0x5B0C) / SA_SendKey (0x5B4E) | HW RNG at 0x816C; gates download |
| 0x31 | RoutineControl (CheckMemory) | FUN_000082BC | CRC verify; calls FUN_000081C8 |
| 0x31 | RoutineControl (Erase) | FUN_00005386 | FACI erase command 0x02 |
| 0x34 | RequestDownload | FUN_00004A6A (subtype 0) | Address/size check; sets fedf0104 |
| 0x36 | TransferData | FUN_00004A6A (subtypes 1/2) | Calls FUN_000049DC + FUN_00002C48 |
| 0x37 | RequestTransferExit | FUN_00004A6A (subtype 6) | Finalizes transfer |
| 0x11 | ECUReset | Via application routing | Resets sentinel to 0x55555555 |

**NOT directly in BL:** SID 0x10, 0x11, 0x22, 0x3E — handled by application's UDS layer.

## Flash Primitives

- **FACI base:** 0xFF434000 (code flash sequencer), 0xFF438000 (secondary FACI)
- **FENTRYR:** 0xFF83A000 — written 0x80 (programming mode enable) by FUN_00008446
- **Erase initiate:** FUN_000051A4(2) — writes 0xA5 (key) to 0xFF434000, then cmd byte to 0xFF434008
- **Address setup:** FUN_000051EC — writes start+0x2000000 to 0xFF43400C, end to 0xFF434010
- **Program write:** FUN_00008BF0 — writes 0xA5 to 0xFF438004, data to 0xFF438000 (SRAM-resident)
- **Block erase orchestrator:** FUN_00005386 (issues FACI cmd 0x02)
- **Multi-sector erase FSM:** FUN_0000875A (with busy-wait loop; timeout=0xFFFF iterations)
- **SRAM flash write:** FUN_00008446 copies 0x8BF0–0x8E3E to SRAM 0xFEDF0000, jumps there via thunk_EXT_FUN_fedf0048
- **Checksum verify:** FUN_000082BC — calls FUN_000081C8(start, len, &result), compares to expected

## SecurityAccess in Bootloader

- **Seed generation:** HW RNG at registers 0xFFFFE000/088/094 (FUN_0000816C, FUN_00008134)
- **State machine:** SRAM 0xFFFF8404 (channel state); value 0x08 = seed sent / awaiting key, 0x06 = alt path
- **SA gates download:** `SA_SendKey` (0x5B4E) accepts key, transitions state, then calls `BL_DownloadHandler` (0x4A6A)
- **Algorithm:** CONFIRMED NOT the standard Civic/Clarity 0x0111/0x0112/0x1120 algorithm. Uses Renesas RH850 hardware crypto / LFSR. Exact algorithm UNRESOLVED (needs deeper trace of FUN_000081C8 and the seed path through FUN_0000559C).

## Distinctive Strings & Features

- `"EV850T05xxxxxV105"` @ 0x5034 — BL Erase block version marker
- `"DV850T05xxxxxV104"` @ 0x5AF8 — BL Download block version marker
- `"SV850T05xxxxxV103"` @ 0x7C1C — BL Start/Verify block version marker (end of BL code)
- `"39990-TVA-A11039990-TVA-A160"` @ 0x9011 — variant descriptor (both A110 and A160 in same BL)
- `"Honda_TVAA_Limphome"` @ 0x130D5 — limphome mode identifier (in application, not BL proper)
- `"DFFORMAT"` check @ 0x86F4 — data flash format validation signature at 0xA6010
- `"C30_800_D_03_01"` @ 0x9000 — module version string (BL config block A)
- `"C30_802_D_08_00"` @ 0x13056 — module version string (BL config block B)
- German debug strings @ 0xBAA80: `"Springt in den ESB zum Nachflashen"` — application-side reflash trigger
- Magic sentinel chain: `0x5555555A` → `0x555555A5` → `0x55555A55` → `0x55555555` (reset/abort)

## Open Questions

- Exact SA key algorithm (not the Civic algo; possibly hardware LFSR-based — needs FUN_000081C8 decompile + RNG trace)
- Which function is the APPLICATION-side SID router that calls into the BL API table at 0x2000 (in 0x14000+ region)
- Whether SID 0x11 ECUReset clears SA lockout (no lockout counter found in BL scan; may be handled by app)
- BL block at 0xAD000-0xAFFFF role (copied in FUN_0000851C — self-update source?)

See also: [[accord-tva-downstream-chain]], [[accord-tva-hw-id-provenance]]
