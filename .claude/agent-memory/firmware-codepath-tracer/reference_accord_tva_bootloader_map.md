---
name: accord-tva-bootloader-map-2026-06-01
description: Honda 39990-TVA (2020 Accord) bootloader byte-verified inventory from 2026-06-01 session — DELTA on top of reference_tva_accord_bootloader_map which has the prior session's deeper BL analysis
metadata:
  type: reference
---

## NOTE: See [[tva-accord-bootloader-map]] for the main reference.
## This file records corrections and new findings from the 2026-06-01 session.

## Source binary
`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin` — 1MB V850E2/RH850 LE, Bosch AUTOSAR EPS firmware.
Flash base = 0x07800000 (file_offset = flash_addr - 0x07800000).

## Architecture (split-BL)

The Honda TVA uses a Bosch AUTOSAR **split-bootloader** architecture:

1. **SBK layer** (file 0x0-0x7FFF = flash 0x07800000-0x07807FFF, 32KB): Security Boot Code.
   - Contains: IVT, low-level flash primitives (erase/write/verify), CAN/ISO-TP driver layer, SA state machine support functions.
   - Entered via TRAP exception at IVT[0x6] = `jr 0x8000` → this actually jumps to APP init.
   - Reset vector at IVT[0x2] = `jr 0x14` → normal app startup.

2. **Bosch AUTOSAR programming shell** (file 0x8000+): UDS service dispatch + UDS handlers.
   - App init at 0x8000 (MCU setup: BSEL, gp/tp/sp init, SRAM clear).
   - Main BL communication loop: **0x875a** (uses function pointer vtable at 0x2000-0x20AC).
   - Flash programming entry: **0x896e** → **0x851c** (main flash block copy/program).
   - UDS handlers accessed via Bosch service config tables at 0xB0000-0xBD000.

## SBK Boundary markers

| Address | Content |
|---------|---------|
| file 0x0-0x7FFF | SBK / Security Boot Code (32KB) |
| file 0x7FC0-0x7FCF | 0xFF fill (end-of-useful-BL pad) |
| file 0x7FD0 | `'C30_801_D_03_00_T04'` — BL module component ID |
| file 0x7FE0 | `00 AF FE DE AD 00 00 BE EF` — magic/fill |
| file 0x7FF0 | `01 00 00 00` = block count = 1 |
| file 0x7FF4 | `00 00 09 00` = 0x90000 (possibly APP copy target) |
| file 0x7FF8 | `02 00 06 00` |
| file 0x7FFC | `0x08ACF7C9` — BL block CRC32 candidate |
| file 0xFD0 | `0x9BFC9224 / 0x9BFC9223` — SBK tamper-detect key pair |
| file 0xFD8 | `'SBK_E13B0100'` — Security Boot Code identifier |

## UDS services (byte-verified handler addresses)

All handlers live in the **APP region** (file > 0x7FFF), dispatched by Bosch AUTOSAR:

| SID | Service | Handler addr (file) | Notes |
|-----|---------|---------------------|-------|
| 0x10 | DiagnosticSessionControl | 0x52e32 | App |
| 0x11 | ECUReset | 0x534da | App |
| 0x14 | ClearDiagnosticInfo | 0x58002 | App |
| 0x27 | SecurityAccess | 0x20380 | App, Bosch style, 4-slot subfunc table |
| 0x34 | RequestDownload | 0x1fa92 | App |
| 0x35 | RequestUpload | 0x7830 | BL region (file < 0x8000) |
| 0x36 | TransferData | 0x4baf0 / 0x4bac4 | App, variant handlers |
| 0x37 | TransferExit | 0x4bb32 | App, calls CRC validator 0x49fc8 |
| 0x23 | ReadMemByAddr | 0x4a5ec | App |

No direct BL-layer implementation of 0x10/0x11/0x27/0x34/0x36/0x37. All route through APP.

## SecurityAccess (SID 0x27)

- **Dispatcher**: file 0x20380 (Bosch AUTOSAR style, loop over 4 entries)
- **Subfunc table**: file 0xB7584 → bytes `[01 02 03 4F 01 01 02 0A 01 02 07 08 41 42 ...]`
  - ep starts at 0xB7585, ep+8 comparison bytes: **0x02 / 0x07 / 0x08 / 0x41** (4 live subfuncs)
  - 0x02 = sendKey L1, 0x07 = reqSeed L4, 0x08 = sendKey L4, 0x41 = reqSeed L33
- **SA config table**: file 0xB75E4 = `01 11 FF 0F` (session_gate=0x0F, max_attempts=0x11)
- **SA service descriptor**: file 0xBC2B8 = `[ptr=0x20380][SID=0x27][b5=0x12][b6=0x13][0x00]`
- **SA key calc (BL side)**: 0x585ea — uses `divq [0x11], r12, r10` + `mulhi 12, r10` for CAN mailbox selection. The 0x11 appears to be CAN mailbox count, not the k0 SA constant.
- **SA state orchestrator**: 0x5874e (BL, called from APP SA path via 0x193ce)
- **SA state checks**: 0x58982 (CAN mailbox state), 0x589ca (SA config table lookup at 0x8AF0C)

**No standard Honda k0/k1/k2 DIVU constants found in SBK or APP (searched full image). The TVA-A030 Bosch SA uses a different verification path from Pilot/Clarity family.**

## Flash primitives (all in SBK, file 0x0-0x7FFF)

| Addr | Function |
|------|----------|
| 0x2000-0x20AC | Flash primitive vtable (pointers for APP use) |
| 0x7a16 | Flash **erase** (FEDF03A0 flash ctrl register) |
| 0x7af4 | Flash **write** stub (calls 0x51a4) |
| 0x51a4 | Flash write sequence (programs FF434000/08/00 = FSTATR/FSTATR2/FMFIFO) |
| 0x51ec | Flash write data setup (programs FF43400C/10/28 = FMEPD/FMPFD/FMFIFO) |
| 0x7b84 | Flash verify/read (variant 1) |
| 0x7b3c | Flash verify/read (variant 2) |
| 0x7acc | Flash reset/clear helper |
| 0x4974 | Flash busy guard (polls FEDF02A4+88, checks 0x55555555 magic) |
| 0x4dc4 | Flash state check 1 (expects sentinel 0x5555555A) |
| 0x4dfe | Flash state check 2 (expects sentinel 0x555555A5) |
| 0x851c | Main BL flash block copy/program (uses vtable [0x2000] erase + [0x2004] write) |
| 0x896e | Flash programming entry point (BL main loop -> here -> 0x851c) |

## Communication functions (SBK, file 0x0-0x7FFF)

| Addr | Function |
|------|----------|
| 0x571e | CAN/ISO-TP message handler (reads FEDF0000 session buffer) |
| 0x5716 | Message dispatcher (branches on ISO-TP frame type 1/2/3 = SF/FF/CF) |
| 0x4e4c | CAN receive/process (vtable[0x201c]) |
| 0x4e9a | CAN idle callback (vtable[0x2030]) |
| 0x559c | Session init/reset (clears FEDF0000 session state) |
| 0x2874 | UDS NRC sender |
| 0x4f5a | BL version string getter (returns ptr to 'EV850T05xxxxxV105' at 0x5034) |
| 0x875a | Main BL communication loop (APP region, > 0x8000) |

## Notable strings

| File addr | String |
|-----------|--------|
| 0xFD8 | `SBK_E13B0100` |
| 0x7FD0 | `C30_801_D_03_00_T04` (BL component) |
| 0x5034 | `EV850T05xxxxxV105` (programming SW v1.05) |
| 0x5AF8 | `DV850T05xxxxxV104` (programming SW v1.04) |
| 0x7C1C | `SV850T05xxxxxV103` (programming SW v1.03) |
| 0x8FD0 | `C30_803_B_00_00` (calibration module) |
| 0x9011 | `39990-TVA-A11039990-TVA-A160` (variant SW IDs) |
| 0x922D | `39990-TVA-X01039990-TVA-X020` (engineering variant IDs) |
| 0x13010 | `2018/01/30 13:04:35.00` (build timestamp A160 layer) |
| 0x13037 | `SGDW00608` |
| 0x13056 | `C30_802_D_08_00` (second SW module) |
| 0x13090 | `2017/05/04 07:36:25.85` (build timestamp A110 layer) |
| 0x130B7 | `SGDW00277` |
| 0x130C1 | `A1B_A00_E_08_01` |
| 0x130D5 | `Honda_TVAA_Limphome` (limp-home strategy name) |
| 0x130E9 | `HW1B foc1` (hardware/FOC variant) |
| 0x13100 | `39990-TVA-A16039990-TVA-A110C30802D0800` (full variant+module string) |
| 0xB9A8C | `KFC_TLC`, `KFC_PWD`, `KFC_ROM`, `KFC_RAM`, `KFC_SGA` (Bosch DTC category names) |
| 0xB9AC4 | `KFC_SLIP_CLUTCH`, `KFC_EAT_158_SNA`, `KFC_ENG_13X_SNA` |

## Open questions

1. **SA key algorithm**: No DIVU/k0/k1/k2 constants found matching Pilot/Clarity pattern. The Bosch TVA SA appears to use a CAN mailbox state machine path (0x5874e -> 0x585ea) rather than the classic seed-multiply-divide algo. Need Ghidra decompile of 0x5874e and its callers for the actual key verification.
2. **TransferData (0x36) exact handler**: 0x4baf0 and 0x4bac4 are candidates but SID byte is not byte-verified for 0x36. The handler may be the same function with different block-size parameters. UNRESOLVED.
3. **0x7FF4 = 0x90000**: Meaning unclear. Possibly APP region start copy destination, or unrelated version field.
4. **SA key constants**: If SA key formula needed for programming session entry, must trace 0x20380 -> key comparison path in Ghidra. The DIVU-based constants are NOT present in this image.

## Related
[[reference_accord_tva_sa_dispatch]] [[reference_tg7_pilot_sa_dispatch]]
