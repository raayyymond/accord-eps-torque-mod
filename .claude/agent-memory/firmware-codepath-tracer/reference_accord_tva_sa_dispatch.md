---
name: accord-tva-sa-dispatch
description: Accord TVA-A030 (Bosch AUTOSAR) SA 0x27 subfunc dispatch — 4-slot lookup, subfuncs 0x02/0x07/0x08/0x41, session-gated, different from Pilot Denso framework
metadata:
  type: reference
---

## Source binary
`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin` — 1MB V850E2/Px4 LE, Bosch AUTOSAR firmware (NOT Denso/Jtekt like Pilot TG7). German debug strings (KFC_TLC etc.) confirm Bosch origin.

## ISA and framework
- V850E2 LE (same MCU family as Pilot TG7)
- Bosch AUTOSAR BSW (completely different UDS framework from Pilot's Denso/Jtekt stack)
- gp = 0xFFFF8000, tp = 0x000BF000 (set at startup 0x140C4-0x140D6)
- Code: 0x0-0x83FFF; Data: 0x84000+ 

## SA 0x27 service dispatch path
- Service descriptor at file 0xBC2B8: [ptr=0x00020380][desc=0x27 0x12 0x13 0x00]
- SID=0x27 also confirmed in UDS service SID list at file 0xB9A54 (LE u16 = 0x0027)
- SA dispatcher function: **0x20380** (Bosch AUTOSAR style, NOT a Pilot-format table)

## SA subfunc dispatch mechanism at 0x20380
The function:
1. Takes subfunc byte in r6 (zxb → r24)
2. Loads table config from tp+0x85E4 (V850 addr 0xB75E4, file 0xB75E4)
3. Loads subfunc comparison array base from tp+0x8584 (file 0xB7584)
4. Calls 0x20344: returns stride=1 (from byte1 & 0xF = 0x11 & 0xF = 0x01)
5. Calls 0x2035E: computes initial ep = 0xB7585 (table_base + 1)
6. **LOOP (max 4 iterations)**: compares ep+8 against input subfunc, stride=1

## The 4 subfunc bytes checked (ep+8 window at ep=0xB7585-0xB7588):
| Iteration | ep | compare byte (at ep+8) | Handler bitmask | Standard UDS meaning |
|-----------|-----|------------------------|-----------------|----------------------|
| 0 | 0xB7585 | file[0xB758D] = **0x02** | 1 | sendKey L1 |
| 1 | 0xB7586 | file[0xB758E] = **0x07** | 2 | requestSeed L4 |
| 2 | 0xB7587 | file[0xB758F] = **0x08** | 4 | sendKey L4 |
| 3 | 0xB7588 | file[0xB7590] = **0x41** | 8 | requestSeed L33 (Clarity-style) |

Note: 0x42 (sendKey L33) is in the byte array at position [13] but the loop exits at 4 iterations, so it is NOT checked.

## Handler dispatch (after match)
- Table 3 at file 0xB7644 (tp+0x8644 signed), stride=20, 4 entries
- All 4 entries jump via 0x20C1A to main handler at **0x4D276**
- 0x4D276 branches on bitmask: cmp 2, r6 (requestSeed path) and cmp 1, r6 (sendKey path)
- Bitmasks 4 and 8 (subfuncs 0x08 and 0x41) fall through to state machine at 0x2073A

## Session gate
- Table header at file 0xB75E4 byte[3] = **0x0F** = 0b00001111
- Sessions 0-3 allowed; sessions 4+ NOT allowed
- This IS a session gate (not all sessions can invoke SA 0x27)
- Flag set location: the byte at 0xB75E4+3 = 0x0F is a FLASH constant

## What is MISSING vs. standard UDS SA
- **0x01 (requestSeed L1)**: NOT in the 4-slot comparison table -> L1 is incomplete/absent
- **0x42 (sendKey L33)**: In the byte array but outside the 4-slot search window

## wwhrlrcr5 claim (Accord = L1-only)
**DISPROVEN WITH EVIDENCE**: The binary contains subFuncs 0x07/0x08 (L4) and 0x41 (L33 requestSeed), not just L1. The claim that only 0x01/0x02 (L1) are supported is not consistent with the binary. If 0x01 is absent, it's L4+partial-L33, not L1-only.

**CAVEAT**: Moderate confidence. The ep+8 comparison offset derivation assumes stride=1 from function 0x20344 and initial ep=0xB7585 from function 0x2035E. These derived from register traces. The Bosch framework may have preprocessing I haven't traced. A live probe of subFuncs 0x01, 0x02, 0x07, 0x08, 0x41 would definitively confirm.

## Key algorithm constants
The Accord TVA SA key constants were NOT found in the binary (searched exhaustively for k0=0x0011, k1=0x0012, k2=0x1020 and all variants). The key algorithm may be in bootloader or use a different formula than the Pilot/Clarity family.

## Related
[[reference_tg7_pilot_sa_dispatch]] [[reference_clarity_sa_level_dispatch]]
