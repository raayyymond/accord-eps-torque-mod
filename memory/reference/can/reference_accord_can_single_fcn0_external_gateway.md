---
name: reference-accord-can-single-fcn0-external-gateway
description: "2026-07-08 PROVEN: the 2020 Accord EPS (39990-TVA-A160) uses ONE CAN controller (FCN0 @0xFF480000, TX mailbox 6) for ALL frames — FCN1 (0xFF4A0000) is never initialized (zero xrefs). So 0x660 and 399 leave on the SAME physical wire; the visibility split (399/427/0x14A reach the comma, 0x660/0x19F/0x32E/0x64D don't) is 100% an EXTERNAL car gateway, NOT the EPS. No EPS-side broadcast edit can make a non-whitelisted ID comma-visible (TIER1's 0x660→100Hz rearm was invisible on-car). Telemetry must ride the diagnostic channel — see [[reference-accord-uds-did-read-surface-a160]]."
metadata:
  node_type: memory
  type: reference
---

# Accord EPS CAN broadcast visibility = external gateway (single FCN0)

**Question settled:** why do broadcast frames 399/427/0x14A reach the comma-tapped bus but 0x660/0x19F/0x32E/0x64D never do? **Answer: the EPS emits them all on one wire; the drop is downstream in the car's CAN gateway.** Ghidra-verified on stock `code.bin` (2026-07-08).

## Evidence (all in `code.bin`, gp=0xFEDF8000, tp=0xBF000)
- **One CAN controller: FCN0** (`0xFF480000`, mailbox area `0xFF481000`, mailbox 6 = `0xFF481180`). **FCN1 (`0xFF4A0000`) is never used** — `get_xrefs_to 0xFF4A0000` = zero; init only boot-zero-fills its range and never configures it. Init: `FUN_000005e6` → `FUN_00000c76` (zero-fill `0xFF480000`–`0xFF4A1FFF`) → `FUN_0000093a` (FCN0 bit-timing/mailbox config only).
- **All 11 broadcast slots route to FCN0 mailbox 6.** Routing fn `FUN_0001d82e` reads channel-byte from table **`0xB7208`** (all 11 slots = `6`); emitter **`FUN_0001d68e`** hardcodes `mov 0xff481000,r6` (FCN0). Slot→CAN-ID from table **`0xB721C`** (4-byte LE MID, `CAN_ID = MID>>18`): idx4=0x660, idx7=0x1AB/427, idx8=0x19F, idx9=0x18F/399, idx10=0x14A (+ inactive idx0-3=0x720-0x723). Active flags seed `0xB7D00` (slots4-10=1). Interval table `0xB7C9C` (tp-0x7364): `[1,1,1,1,20,100,10,2,1,1,1]` (1=100Hz…20=5Hz).
- **0x660 (idx4) and 399 (idx9) are byte-identical in the TX stack** — same channel-byte 6, same emitter call, same FCN0 mailbox 6; the only difference is the CAN ID (MID reg) and the payload-builder callback.
- **Diagnostic responses also use FCN0** (`FUN_0001d68e`, response ID from `gp-0x1700`=0xFEDF6900=0x18DAF180) — consistent: flashing over OBD works because FCN0 is the car-connected controller.

## Consequence
Since the EPS puts 0x660 and 399 on the same physical wire and only 399 reaches the comma, the filter is **entirely downstream of the EPS connector** — the car gateway bridges only the frames other modules consume (`{399, 427, 0x14A}` + diagnostics) and drops the EPS-internal ones. **On-car proof:** the TIER1 build rearmed 0x660 to 100 Hz and flashed it; the 2026-07-08 comma scan still shows 0x660 ABSENT on all buses (`analysis-2020accord/reference/can-scans/2026-07-08-*`), identical unique-ID counts to the pre-flash baseline.

⇒ **No EPS-side broadcast change (a new TX ID, a rearmed ID, a rate bump) can ever be made comma-visible** — the whitelist lives in a gateway ECU we can't reflash. The whitelisted broadcast frames (399/427/0x14A) are all full-DLC with a per-frame checksum → no spare-bit piggyback either. **The only surviving CAN telemetry path is the diagnostic (UDS) channel**, which the gateway *does* forward — see [[reference-accord-uds-did-read-surface-a160]].

Genuinely un-knowable from `code.bin`: the gateway's exact forwarding table (it's in a separate ECU) and the physical pin routing. Everything above is the EPS-side half, which is definitive.

Links: [[reference-accord-uds-did-read-surface-a160]] · [[reference-accord-gp-base-fedf8000]] · [[reference-accord-tva-bootloader-map]]
