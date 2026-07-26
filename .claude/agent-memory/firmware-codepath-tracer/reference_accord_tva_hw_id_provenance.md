---
name: accord-tva-hw-id-provenance
description: Provenance of the 5-byte ECU hardware ID at gp+0x6408..0x640C in Honda Accord EPS 39990-TVA-A160 (V850 code.bin). Writer function, dispatch table entry, UDS service identification.
metadata:
  type: reference
---

## Finding: 5-byte ECU HW-ID at gp+0x6408..0x640C — Accord TVA A160 V850

Verified via GhidraMCP disasm/decompile, 2026-05-26.

### RAM address
- gp = 0xFEDF8000, so gp+0x6408 = 0xFEDFE408 through 0xFEDFE40C (5 bytes)

### Sole writer: FUN_000508e8 (UDS diagnostic handler)
- Only function that stores to gp+0x6408..0x640C (confirmed by exhaustive st.b search across all 185K instructions)
- Store instructions: 0x000509D4 (byte 0), 0x000509DA (byte 1), 0x000509E0 (byte 2), 0x000509E6 (byte 3), 0x000509F0 (byte 4)

### Two code paths in FUN_000508e8:
1. **`*pcVar11 == '\0'` (init/blank path):** Sets all 5 bytes to 0x30 ('0' ASCII) explicitly in code. Also calls memcpy(gp+0x6400, 0x14500, 4) for adjacent 4-byte region. The 5 ID bytes are NOT read from flash here — they are hardcoded to '0'.
2. **`*pcVar11 == '\x01'` (write path):** Copies pcVar11[1..5] → gp+0x6408..0x640C. This is a diagnostic write from a received message buffer. Calls FUN_00057f8e() to validate the new ID against the 0xCD000 table; if invalid (returns 0), reverts and sends NRC 0x31 (requestOutOfRange).

### Protocol identification: Honda proprietary diagnostic (UDS-adjacent)
- FUN_000508e8 is reached via function pointer table at 0xB77A8 (entry: handler=0x508E8, f1=0x3B, f2=0x05, f3=0x84, f4=0x08)
- Error codes: 0x22 = conditionsNotCorrect, 0x31 = requestOutOfRange — standard UDS NRC values
- FUN_00020436 is the NRC setter; FUN_0002073a sends the negative response
- Service byte in dispatch table: 0x84 (Honda proprietary, not standard UDS)

### Boot default
- At first run (blank/uninit flag): bytes are set to `30 30 30 30 30` ("00000" ASCII) in code
- Flash at 0x14508 also contains `30 30 30 30 30` (coincidence with code default, or flash-default mirror — NOT directly read by any discovered code path)
- No ld.b from gp+0x6408 found outside FUN_00057f8e (the reader/matcher)

### No hardware register source found
- No peripheral MMIO address discovered as source
- No OTP/unique-ID hardware register path found
- Source is purely the diagnostic write path (service 0x84, sub-cmd 0x01)

### Dispatch table location
- Table base extends from ~0xB7600 to ~0xB7C00 (stride varies by section)
- FUN_000508e8 entry at 0xB77A8 confirmed by byte-pattern search for E8 08 05 00

### UDS obtainability assessment
- The 5 bytes ARE writable via Honda proprietary service 0x84 sub-function 0x01
- Readable via FUN_00057f8e (the matcher) — the reader reads them from RAM, implying they survive across sessions only if NVRAM-backed (not confirmed)
- Standard UDS 0x22 ReadDataByIdentifier with DIDs F18C/F18x: NOT confirmed to expose this specific 5-byte field — those standard DIDs likely map to a different handler
- Operator would need to identify which standard DID (if any) maps to service 0x84 reads; the adjacent 0xCC-handler (FUN_00020CB8) at 0xB7794 may be the read counterpart to the 0x84 write handler
