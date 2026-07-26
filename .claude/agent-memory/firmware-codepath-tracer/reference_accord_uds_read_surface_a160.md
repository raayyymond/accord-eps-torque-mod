---
name: reference-accord-uds-read-surface-a160
description: 2020 Accord EPS (39990-TVA-A160, V850E2) diagnostic CAN read surface — dispatcher location, SIDs, session gating, and arbitrary RAM read framing
metadata:
  type: reference
---

> ⚠ **CORRECTED 2026-07-10** — key facts here are WRONG; see `reference_accord_a160_rdbi_handlerptr_live_dispatch.md`:
> the RDBI per-DID table TRUE base is **0xB77FC** (NOT 0xB7800), and the LIVE per-DID payload dispatch reads
> **handler_ptr at entry+0x10** and calls it with a ctx pointer (FUN_000209ea) — not a groupID jump-table for
> payload. Request addr is **0x18DA30F1** (resp 0x18DAF130), NOT 0x18DA80F1. Working telemetry = V31U
> (repoint DID 0x4801 handler_ptr @0xB7820 → cave). The three-stack / ABI / gateway facts below stand.

# 2020 Accord EPS — UDS/KWP Diagnostic Read Surface (A160)

Firmware: `39990-TVA-A160`, `code.bin`, V850E2Px4, Ghidra flat base 0. gp=0xFEDF8000, tp=0xBF000.

## Diagnostic CAN Channel

NOT ISO 15765-4 standard addresses (0x7DF/0x7E0). Uses Honda proprietary KWP2000-over-CAN:
- **RX CAN ID: 0x72A** (std 11-bit. Mbox 0x23, mbox ID reg `0x1CA80000`, stdID bits[28:18] = 0x72A)
- Mbox 0x23 → slot 22 (via mbox-to-slot table at `0xB70F4`)
- Slot 22 handler: `FUN_0001FA92` @ `0x0001FA92`

Also has extended-frame OBD functional address: mbox 0x20 = `0x98DBEFF1` (= 0x18DBEFF1 with ext-frame bit set).

## Response Transport — ALWAYS K-LINE (UART), NOT CAN

`DAT_fedf5d4a` = `gp-0x22B6` = `0xFEDF5D4A` — same byte serves dual purpose: transport latch AND pending flag.

**Transport select in `FUN_00014e9e` @ `0x00014e9e`:**
- `gp-0x22B6 & 0x70 != 0` → "CAN path" branch: `set1 0x0, 0x5d4a[r18]` = sets bit 0 (K-line pending flag). Does NOT write FCN0. Does NOT call `FUN_0001fafa`.
- `gp-0x22B6 & 0x70 == 0` → K-line path: `set1 0x4, 0x5d4a[r18]` + calls `FUN_0001fafa` (UART TX to K-line).

**Pending flag consumer — `FUN_00015f32` @ `0x00015f32`:**  
Called via tail-jump (`jr 0x00015f32` @ `0x0001FAF6`) immediately after every CAN 0x72A frame is processed by `FUN_0001FA92`.
Sequence:
1. `gp-0x22B6 &= 0x8F` (clears bits 4,5,6 — transport indicators) @ `0x00015f42`
2. If bit 0 was set: `clr1 0x0, 0x5d4a[r18]` @ `0x00015f56`, then calls `FUN_00014e9e`
3. `FUN_00014e9e` now sees `gp-0x22B6 & 0x70 == 0` → K-line path → `FUN_0001fafa` (UART TX)

**Result: diagnostic responses for CAN 0x72A requests always egress on K-line (UART). No FCN0 CAN frame is generated for any diagnostic response.** The ECU is a single-transport design: requests come in on CAN 0x72A, responses go out on K-line only.

## Bottom Line (Updated)

**0xF4 RAM read response for a CAN 0x72A request egresses on K-LINE (UART/ISO 9141/KWP physical layer), NOT on FCN0 CAN. Therefore comma-visible on CAN bus-1: NO.**

The comma cannot see the SID 0xF4 response on the CAN bus. RAM telemetry via UDS/KWP polling from the comma is not viable without a K-line adapter. **CAN-exfil alternative (enabling an internal TX frame via the 0xFEDF693C TX-enable bitfield and writing RAM values into it) remains the viable path for comma-visible RAM telemetry.**

Key addresses for response egress trace:
- `0x00014E9E` `FUN_00014e9e` — response router (transport select)
- `0x00014ECC` `set1 0x0, 0x5d4a[r18]` — "CAN path" sets K-line pending bit
- `0x00014EDE` `set1 0x4, 0x5d4a[r18]` — K-line path pending + immediate UART TX
- `0x00015F32` `FUN_00015f32` — diagnostic tick, consumes pending flag → K-line TX
- `0x0001FAF6` `jr 0x00015f32` — tail-jump from CAN handler to tick (immediate consumption)
- `0x0001FAFA` `FUN_0001fafa` — K-line UART TX (writes to `UARTH1_registers_t_ffffeb00`)

## Service Dispatcher

`FUN_000156fa` @ `0x000156fa` — KWP2000-style proprietary SID dispatcher (NOT ISO 14229 UDS).

Called from: `FUN_0001FA92` (CAN slot 22 handler).

SID space: **0xC0–0xFF** (Honda proprietary range). Standard UDS SIDs (0x10, 0x22, 0x23, 0x2C, 0x34, 0x35, 0x36, 0x37) are **NOT present**.

### Session / Security Gating (in `FUN_000156fa`)

1. State word gate: `gp-0x6A98 == 0` selects `*(gp-0x2588)`, else `*(gp-0x2584)`. If `(state & 0x80) != 0` → block all.
2. Diagnostic-enabled flag: `gp-0x24E4` must be non-zero.
3. Session-active gate: `gp-0x24D7 (DAT_fedf5b29) & 0x20` must be set (skips switch if 0).

### Session Open — SID 0xFF

A **single CAN frame** `[0xFF, ...]` on 0x72A opens the session:
- In `FUN_0001FA92`: SID==0xFF → `FUN_00014e92(8,8,0)` sets security byte at `gp-0x24C8` (0xFEDF5B38) = 0
- Security check passes → calls `FUN_000156fa` → 0xFF handler:
  - Sets `gp-0x24E0 = 0xFF` (response buffer SID echo)
  - Sets `gp-0x24D8 = 1` (response length)
  - Calls `FUN_00014fd8` (reset param buffers)
  - **Sets `DAT_fedf5b29 = 0x20`** → `gp-0x24D7 = 0x20` → bit 0x20 now set → dispatcher active
  - Sends response

No challenge-response SecurityAccess. Session open = **unauthenticated**.

## SID Table (Implemented)

All SIDs are proprietary KWP2000/Honda. No ISO 14229 UDS. Implemented SIDs include:

| SID | Function | Session/Security |
|-----|----------|-----------------|
| 0xC9 | Write N bytes to data buffer | default (after 0xFF open) |
| 0xCE | Short fixed response | default |
| 0xCF | Reset + flush | default |
| 0xD0 | Write ≤6 bytes to data buffer | default |
| 0xD1 | Read from data buffer address | default |
| 0xD2 | Flash unlock init | default (gates on flash state) |
| 0xD3 | Param set with 3 args | default |
| 0xD4 | Param set with 2 args | default |
| 0xD5 | Param set with 1 arg | default |
| 0xD6 | Reset (`FUN_00014fd8`) | default |
| 0xD7 | Read parameter record (TP-indexed) | default |
| 0xD9 | Set response format 0x107 | default |
| 0xDA | Set response format from cal | default |
| 0xDD | Snapshot/freeze-frame (gated on 3 conditions) | default |
| 0xDE | Set periodic flag | default |
| 0xDF | Read periodic flag | default |
| 0xE0 | Write periodic record | default |
| 0xE1 | Write to indexed RAM buffer | default |
| 0xE2 | Set buffer pointer | default |
| 0xE4 | Complex param write | default |
| 0xE5 | Read byte (range-gated < 0x2E) | default |
| 0xE6 | Write byte (session AND range gated, gp-0x67FA ∈ {3,4,8}) | extended |
| 0xE9 | Fixed response 0x2E | default |
| 0xEA | Read param byte | default |
| 0xEB | Read/write param with 3 args | default |
| 0xEE | **Write memory by address** (7 bytes) → `FUN_00014f68` → `FUN_0001ca52` | default |
| 0xF0 | **Write memory by address** (variable count ≤7) | default |
| 0xF3 | Set 16-bit address pointer (0x0000____ range only) | default |
| 0xF4 | **Read memory by address** (32-bit addr + count) | **default** |
| 0xF5 | **Read memory continuation** (count from byte[1]) | **default** |
| 0xF6 | Set address from translated pointer | default |
| 0xF9 | Set session state flags | default |
| 0xFB | Set response multi-frame format | default |
| 0xFC | Short NRC response | default |
| 0xFD | Fixed response with cal byte | default |
| 0xFE | Reset + `FUN_000156e4` | default |
| 0xFF | **Session open** (unauthenticated) | — |

Standard UDS SIDs **NOT PRESENT**: 0x10, 0x22, 0x23, 0x27, 0x2C, 0x34, 0x35, 0x36, 0x37.

## Arbitrary RAM Read Path — SID 0xF4

Handler in `FUN_000156fa` @ case 0xF4 (within switch at `~0x000158xx`):
- Calls `FUN_0001c726` (address translation — pass-through during normal op)
- Calls `FUN_00014fa0(count, response_buf)` → loops `count` times calling `FUN_0001ca0a(addr++)` for each byte
- `FUN_0001ca0a`: if addr < 0xFA800000 → direct `*addr`; else → aligned 32-bit peripheral read + byte extract. Handles 0xFEDF____ (V850 internal RAM/SFR) via the peripheral path.

**Request frame format (8 bytes, CAN 0x72A)**:
```
[0xF4, count, 0x00, addr_fmt, addr[31:24], addr[23:16], addr[15:8], addr[7:0]]
```
- byte[0] = 0xF4
- byte[1] = N (bytes to read, ≤ 7 for single CAN frame response — can chain with 0xF5)
- byte[2] = unused
- byte[3] = address format byte (ignored during normal op by `FUN_0001c726`)
- bytes[4..7] = 32-bit address, big-endian

**Response**: `[0xF4, byte0, byte1, ..., byteN]` (N+1 bytes) on TX CAN path.

**Address range of interest**: 0xFEDF____ (V850 internal RAM) — readable. gp=0xFEDF8000.

## Bottom Line

**YES — unauthenticated live RAM read is possible in default/normal session.**

Sequence (bus-1, physical, car drivable):
1. Send `[0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]` on CAN ID 0x72A → session opens, responds with echo
2. Send `[0xF4, N, 0x00, 0x00, MSB, ..., LSB]` on CAN ID 0x72A → responds with N bytes of RAM

No SecurityAccess (SID 0x27) required. No programming session required. No openpilot/pandad kill required (car drivable). 

**Caveat**: No standard ISO 14229 UDS (0x22/0x23/0x2C/0x34/0x35) is present. The entire surface is Honda proprietary KWP2000 SIDs 0xC9–0xFF.

## Key Addresses

| Address | Symbol | Notes |
|---------|--------|-------|
| 0x0001FA92 | `FUN_0001FA92` | CAN slot 22 handler; diagnostic frame entry point |
| 0x000156FA | `FUN_000156FA` | KWP SID dispatcher (switch on SID) |
| 0x00014FA0 | `FUN_00014FA0` | Read N bytes from address via `FUN_0001ca0a` |
| 0x0001CA0A | `FUN_0001CA0A` | Single-byte memory read (handles peripheral space) |
| 0x0001C726 | `FUN_0001C726` | Address translator (pass-through in normal op) |
| 0x00015FAC | `FUN_00015FAC` | Session-open (K-line path entry) |
| 0x000B733C | `s_can_mbox_id_table` | CAN mailbox ID table |
| 0x000B73FC | `s_can_slot_dispatch_handler_table` | Slot handler table |
| 0x000B70F4 | `s_can_mbox_to_slot_table` | Mbox→slot mapping |
| 0xFEDF5B29 | `DAT_fedf5b29` = `gp-0x24D7` | Session state flags (bit 0x20 = active) |
| 0xFEDF5B38 | `gp-0x24C8` | Security byte (0 = unlocked) |
| 0xFEDF5B1C | `gp-0x24E4` | Diagnostic-enabled flag |

[[reference-accord-tx-enable-bitfield]] — TX enable bitfield at 0xFEDF693C controls which CAN IDs go out
