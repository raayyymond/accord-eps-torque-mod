---
name: reference_accord_tva_bootloader_map
description: "2026-06-01 map of Ray's full Honda 39990-TVA Accord EPS bootloader (code.bin, V850E2/RH850 LE). CONFIRMS the dump path: the BOOTLOADER hosts SID 0x35 RequestUpload (read-out) + the full flash chain (0x34/0x36/0x37/0x31 erase+CRC) + its own SecurityAccess. Boot-mode entered on every power-up, kept resident via the programming/erased-sentinel gate. DIFFERENT ISA than SH-2A C120 -> architectural/conceptual transfer only, NOT byte-for-byte. Vindicates 'soft-mod-only, no physical' (dump = boot-mode UDS)."
metadata:
  type: reference
---

# Accord 39990-TVA EPS bootloader map (horde wta84r7ra)

`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin` — 1MB, V850E2/RH850 LE. **The structural template for the
boot-mode dump path.** DIFFERENT MCU/ISA than the SH-2A C120 (TBA) — addresses are Accord-specific;
the ARCHITECTURE transfers conceptually, the bytes do not.

## Why this matters: the dump command lives in boot mode
The application layer has no read-out (matches the SH-2A app finding), but the **BOOTLOADER does** —
this is the byte-confirmation that "soft-mod-only, no physical access" is real: enter boot mode →
the BL's own UDS stack exposes `0x35`/flash-chain. My earlier app-layer "needs physical" was scoped
to the wrong region.

## Bootloader layout
- BL region: file `0x0-0xFFFF` (64KB), flash `0x07800000-0x0780FFFF`. **SBK** (Security Boot Code)
  `0x0-0x7FFF` = IVT + flash-primitive vtable @`0x2000` + erase/write/verify + CAN/ISO-TP driver + SA
  infra; **AUTOSAR programming shell** `0x8000-0xFFFF` = BL comms main loop (`0x875A`), flash-prog
  entry (`0x896E→0x851C`), UDS dispatch.
- App starts at file `0x14000` (after a 16KB erased gap); ID/string block at `0x13000`.
- **Entry: app reset @file `0x0006` = `jr 0x07808000` → BL runs on EVERY power-up.** 4-check gate
  @`0x8010-0x803F` (ID block, app code, BL descriptor `0x9060`=0x00200780, erased-sentinel @`0xA6000`)
  decides BL-mode vs app hand-off. **In programming mode the erased `0xA6000` keeps the BL resident**
  (the boot-induction mechanism). Dispatch: `mov 0x9060,r2; jmp [r2]` → 24-entry API table @`0x2000`.

## UDS services IN the bootloader (the boot-mode command set)
- **`0x35` RequestUpload — CONFIRMED, handler @file `0x7830` (in SBK), descriptor `[ptr=0x7830][SID=0x35]`.
  THIS is the read-out/dump command** absent from the app. ← the key finding.
- `0x34` RequestDownload (app `0x1FA92` → BL_DownloadHandler `0x4A6A`), `0x36` TransferData (BL state
  machine), `0x37` TransferExit (`0x4BB32`), `0x31` RoutineControl Erase (`0x5386`, FACI cmd 0x02) +
  CheckMemory/CRC (`0x82BC`), `0x23` ReadMemByAddr (app `0x4A5EC`).
- **BL has its OWN SecurityAccess** (state machine `0x5874E`; GetSeed via API `0x2044`, SendKey `0x2048`;
  subfuncs `0x01/0x02/0x07/0x08/0x41` = L1/L4..; session gate byte `0x0F` = sessions 0-3; max attempts
  `0x11`). SA_SendKey → BL_DownloadHandler — SA gates the download.
- `0x10`/`0x11`/`0x14` at app layer; `0x22`/`0x3E` not in BL.
- Dispatch model: no SID-keyed table in BL — the app UDS router calls into the SBK 24-entry API table
  `0x2000`; in-BL a download state machine `0x48CA` (handler table `0x4F80-0x5033`) drives states.

## Flash primitives (RH850 FACI)
FACI @`0xFF434000` (FSTATR/key/cmd/FMEPD/FMPFD/FMFIFO); erase cmd byte `0x02`; programming-window
offset **+0x2000000** added to flash addr. FENTRYR @`0xFF83A000`=0x80 enables code-flash program mode.
**SRAM-resident writer** `FUN_00008BF0` copied to SRAM `0xFEDF0000` and executed there (code flash
can't be read while written — standard RH850). Erase orchestrator `0x7A16` (vtable[0x2000]); multi-sector
erase FSM `0x875A`; block copy/program `0x851C`.

## Transfer to C120 (CONCEPTUAL — tagged, not byte)
The PATTERN transfers: Honda EPS bootloader = entered on power-up, kept resident by a programming/
erased-sentinel gate, hosts its own SA + `0x35` upload + the flash chain. So the **C120 boot-mode dump
via `0x35` is conceptually confirmed and live-confirmable** — NOT byte-verified on the C120 BL (SH-2A,
out-of-our-image; the region the operator reaches LIVE in boot mode, not statically). Do not port
Accord addresses/primitives to C120 byte-for-byte (V850E2 ≠ SH-2A).

## Residuals
Which of the two `0x36` handler candidates is primary; whether the BL `0x11` is separately callable;
the C120 BL's actual addresses (needs the C120 boot-mode dump or a C120 full image).

Cross-links: [[reference_eps_family_uds_sid_map]] [[reference_c120_uds_sid_coverage]]
[[reference_nefmoto_methodology]] (Pillar-1 bootmode/bootstrap) · Full: `.claude/tmp/.../tasks/wta84r7ra.output`.
