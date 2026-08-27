---
name: reference-accord-can-e4-intake-gates
description: 2020 Accord TVA-A160 — full CAN 0xE4 (STEERING_CONTROL) RX intake chain and every gate inside FUN_00052676 that can zero the LKAS command before arbitration. Byte-verified this session with r2 -a v850.gnu.
metadata:
  type: reference
---

2020 Accord 39990-TVA-A160, V850E2. STOCK code.bin. gp=0xFEDF8000, tp=0xBF000. r2 5.5.0 `-a v850.gnu`.
[V] = disasm-verified this session (2026-07-06). [I] = inferred/structural, not instruction-pinned.

## Scope
This is SEGMENT A of a 6-way mapping effort: CAN RX intake -> internal LKAS command variable,
stopping at the hand-off to `m_steer_torque_arbitration` (`FUN_00028ea6`, owned by another tracer).
Distinct from the driver COLUMN-TORQUE sensors (`gp-0x6a62`/`gp-0x4f60`, see
[[reference-accord-dual-torque-sensor-architecture]]) — this file is about the INBOUND
openpilot LKAS command, a separate signal.

## RX chain (re-verified this session, matches `notes/TORQUE_PATH_AND_TABLE.md` §0.5)
```
CAN 0xE4 STEERING_CONTROL (DLC 5, STEER_TORQUE = s16 BE bytes[0:1], opendbc _bosch_2018.dbc)
  mailbox-ID table 0xB733C[22] = 0x03900000 -> stdID = 0x0390>>2 = 0xE4          [V, byte-read 2026-07-06]
  mailbox->slot table 0xB7120 (=0xB70F4+22*2) = 17 (u16)                          [V, byte-read]
  route dest-ptr table 0xB73E0 (=0xB739C+17*4) = 0xFEDF6BD8                       [V, byte-read]
    -> routed buffer 0xFEDF6BD8: STEER_TORQUE s16 BE @+0/+1, byte2 @+2, byte3 @+3 (unread), byte4 @+4
 -> FUN_00021724 (getter): IRQ-critical-section read (jarl 0x1fa42 / 0x1fa72 = IRQ disable/enable),
    concatenates byte0<<8|byte1 -> BE16                                          [V, full disasm]
 -> FUN_00052676 (processor, ONE function 0x52676-0x527d6 — r2 af/pdf correctly bounds this one)
    normal path (param r6==0): sxh; shl 2; subr r0 (=x * -4); clamp(FUN_00049a90, -16384, +16384)
    -> stored to gp-0x69ae = 0xFEDF1652 (LKAS SETPOINT)                          [V, full disasm]
 -> FUN_00028ea6 m_steer_torque_arbitration (OUT OF SCOPE — owned by another tracer)
```

## Command variable
**`gp-0x69ae` = `0xFEDF1652`** — the LKAS torque setpoint, written only by `FUN_00052676`
(either the real scaled/clamped value, or sentinel `0x7FFF` on any gate trip below).

## Sub-fields also parsed by FUN_00052676 (from the SAME routed buffer, each cycle)
| Field | Source bit(s) | Dest | Notes |
|---|---|---|---|
| STEER_TORQUE_REQUEST (candidate) | byte2 (`0xFEDF6BDA`) bit7 | `gp-0x6805` = `0xFEDF17FB` | live, unlatched, no gate effect inside this fn [V mechanism / I label] |
| unknown flag | byte2 bit6 | `gp-0x6804` = `0xFEDF17FC` | stored only |
| candidate COUNTER | byte2 bits[3:2] | `gp-0x6803` = `0xFEDF17FD` | 2-bit field, NOT cross-cycle-checked in this fn |
| 2nd 2-bit field | byte2 bits[1:0] | `gp-0x6802` = `0xFEDF17FE` | forced `0xFF` if STATUS_WORD bit23 set |
| sticky "seen-valid" latch | byte4 (`0xFEDF6BDC`) bit6 | `gp-0x6876` = `0xFEDF178A` | ONCE set to 1, NEVER clears again (verified: `cmp 1,r7; be [skip recompute]`) |
| debounced flag | byte4 bit7 | `gp-0x67F3` = `0xFEDF180D` | gated by a 500-cycle tick counter, see GATE 3 |

byte3 (`0xFEDF6BDB`) is never read by this function — likely CHECKSUM raw byte, owned by an
external validator (see Open Questions). No opendbc `.dbc` was available in this repo to confirm
exact bit-name mapping beyond the byte7/STEER_TORQUE_REQUEST structural match — treat sub-field
NAMES as unconfirmed, the BIT POSITIONS AND ADDRESSES as verified.

## GATE TABLE (all gates found inside FUN_00052676; none reached arbitration in this trace)

| # | Gate | function@addr | branch @addr | input | condition | debounce | effect | confidence |
|---|---|---|---|---|---|---|---|---|
| 1 | CAN-health short-circuit | FUN_00052676@0x526bc | `andi 8,r11,r0`@0x526c0 / `bne 0x52722`@0x526c4 | STATUS_WORD `gp+0x6400`=`0xFEDFE400` bit3 (NOTE: **positive** gp offset, not negative) | bit3 set | none at this test | skips CAN read entirely; `gp-0x69ae`=0x7FFF, all sub-fields=0xFF | VERIFIED (mechanism); INFERRED (HW semantic = CAN ctrl error flag) |
| 2 | CAN-health soft-mark | FUN_00052676@0x52742 | `and r11,r9(0x800000)`@0x52742 / `bne 0x52788`@0x5275e | same STATUS_WORD bit23 | bit23 set | none direct | forces sub-fields `gp-0x6802`/`gp-0x67F3`=0xFF + logs via FUN_0005462c(7,r28)->DTC mgr FUN_00016de6; does **NOT** re-zero the setpoint already written this cycle | VERIFIED (mechanism); INFERRED (HW semantic) |
| 3 | 500-tick debounce | FUN_00052676@0x52768 | `bl 0x52788`@0x52774 | tick counter `gp-0xF4C`=`0xFEDF70B4` vs literal 500 (NOT a cal/tp value — hardcoded immediate) | only active when byte2 bits[1:0]==1; then counter<500 | YES, 500-cycle | `gp-0x67F3` forced 0xFF instead of live byte4-bit7 value; setpoint untouched | VERIFIED (mechanism); INFERRED (trigger semantics) |
| 4 | Validator fault codes 1/2/3 | FUN_00052676@0x5279a | `bnh 0x527a8`@0x527a0 | param r6 (case code) from an **unidentified external caller** | r6 ∈ {1,2,3} | NONE — instantaneous | full sentinel: `gp-0x69ae`=0x7FFF, ALL sub-fields=0xFF, logs FUN_0005462c(7,r6)->FUN_00016de6 (shared DTC/fault latch, see [[reference-accord-consistency-monitor-hardshutdown]]) | VERIFIED (mechanism/effect); UNRESOLVED (caller identity + which code = checksum/counter/DLC) |
| 5 | Rx-timeout/watchdog latch | FUN_00052676@0x5267a (fn entry) | `bne 0x526b4`@0x52682 (skips reset unless r15==1) / `bne 0x526b4`@0x52686 (unless r6==4) | `gp-0x3330`=`0xFEDF4CD0` (word) == 1, AND param r6==4 | both true | edge-consume: `gp-0x3330` reset to 0 at 0x526a0 after firing | full sentinel, same as gate 4, but returns WITHOUT calling FUN_0005462c (no DTC log for this path) | VERIFIED (mechanism/effect); UNRESOLVED (producer of `gp-0x3330`=1) |

**No gate in this segment tests the STEER_TORQUE VALUE itself for magnitude/rate** — all five gates
are CAN-message-validity / comms-health gates, not torque-magnitude gates. There is no raw-value
sanity clamp on the parsed setpoint beyond the fixed `±16384` scale-clamp (`FUN_00049a90`), which
is a UNIT clamp (matches the DBC ±4096 x4 scale), not a fault gate.

## STATUS_WORD (`gp+0x6400` = `0xFEDFE400`) producer [V]
Built by `FUN_000508e8` (called with a channel index in r10; `cmp 2,r10` suggests channel 2 is the
relevant CAN channel for this dispatch). Reads a per-channel diagnostic struct at
`0xCD000 + chan*0x24` (`mulhi 36,r10,r26; mov 0xcd000,r10; add r10,r26`) and translates hardware
bits at struct offset `+27` into software status bits via `tst1`/`ori`/`and` sequences:
```
tst1 0,27[r26] -> bit0   tst1 1,27[r26] -> bit6   tst1 2,27[r26] -> bit3 (GATE 1)
tst1 3,27[r26] -> bit7   tst1 4,27[r26] -> bit17  tst1 5,27[r26] -> bit23 (GATE 2)
```
Byte-verified instruction sequence at `0x50a2e-0x50a3e` (bit3) and `0x50a6e-0x50a7e` (bit23).
Exact hardware meaning of struct-offset-27 bits 2 and 5 (bus-off? error-passive? RX overrun?) is
NOT pinned — would need the `UPD70F3508GJA2-GBG-AX-1.pdf` CAN controller register chapter.

## The unresolved external validator — the most important open thread
`FUN_00052676`'s own address (`0x00052676`) appears as a raw pointer at **file offset `0xbb640`**,
inside a repeating 32-byte-stride table (confirmed entries at `0xbb600/620/640/660`, each:
`[fn_ptr:u32][u32][u32][u32][u16,u16][u32][u32]`). This means `FUN_00052676` is **NOT called by a
literal `jarl`** anywhere in the disassembled code (confirmed by a full linear disassembly of
`0x0-0xc4000`, zero hits) — it is invoked **indirectly through this table** by a shared, not-yet-
located generic CAN-message validator, one entry per RX message. This validator almost certainly
owns: (a) checksum computation (no checksum arithmetic exists inside `FUN_00052676` itself), (b)
rolling-counter cross-cycle consistency (the counter bits are extracted in `FUN_00052676` but never
compared to a remembered previous value there), and (c) the fault-code selection (1/2/3/4) tested
in GATE 4/5 above. **Locating this function would let us map fault codes 1/2/3 to specific failure
types (checksum/counter/DLC).**

### Why it wasn't found this session — tooling note
`r2 -a v850.gnu`'s `aa`/`aaa` analysis and `axt` are UNRELIABLE on this cluster: `axt 0x52676`
returned garbage (`(nofunc) 0xbb640 [UNKNOWN] satsubi 5,r22,gp`) — which in retrospect makes sense,
since `0xbb640` is the DATA table entry, and the plugin was trying to disassemble table bytes as
code. Similarly `FUN_0001cf30` (the HW mailbox filter setup, first hop, not re-verified this
session) hits `invalid`/`unaligned` opcodes almost immediately — the same known v850.gnu undecoded-
opcode issue documented in [[reference-accord-voter-0xffff-sentinel]] for a different function.
**Do not trust r2 aa-based xrefs/afl sizing anywhere in this cluster; hand-walk with linear `pD`,
and use raw byte search (`/x <LE-hex-of-target-address>`) to find data/table references instead of
`axt`.** This is how `0xbb640` was found (searching for bytes `76 26 05 00`).

## Confirmed NOT a magnitude gate
Consistent with [[reference-accord-dual-torque-sensor-architecture]]'s finding that the CAN command
and the physical torque sensors are separate signals: nothing in this intake path reads the parsed
STEER_TORQUE value and rejects it for being "too large" — the only numeric clamp is the fixed
scale-clamp (±16384), a unit-range clamp not a fault gate.

## Bump/hard-turn transient question (mandate item 4)
No gate here is torque-magnitude-triggered, so a hard-turn/bump cannot trip these gates through the
STEER_TORQUE value itself. The plausible INDIRECT path (MEDIUM-LOW confidence, reasoned by analogy
to [[reference-accord-voter-0xffff-sentinel]]'s Q4 finding for the DMA torque-sensor frame): a
mechanical shock coincident with electrical noise/connector chatter on the **openpilot CAN bus**
could trip the CAN-controller STATUS_WORD bits (GATE 1/2) or a checksum/counter mismatch in the
unresolved validator (GATE 4), momentarily forcing the sentinel. This is a DIFFERENT physical bus
than the internal DMA torque-sensor frame in that other memory — same failure CLASS (frame/bus
glitch coincident with mechanical event), different physical channel. Not measured, not proven.

## Open questions / next verification steps
1. **Find the caller of the `0xbb600+` table** (the generic CAN-message validator). Next step:
   Ghidra with the V850E2 processor module (better opcode coverage than r2's v850.gnu) — define the
   table as `struct{void* fn; u32; u32; u32; u16; u16; void*; u32}[]` at `0xbb5xx` (find the true
   table start by scanning backward/forward from `0xbb600` for the same stride) and let Ghidra's
   xref engine find who reads it. This resolves GATE 4/5's exact trigger semantics and the
   checksum/counter mechanism.
2. **Producer of `gp-0x3330`=1** (GATE 5's rx-timeout latch) — not located. Likely a periodic
   watchdog task; would need the same table/caller resolution, or a targeted search of the 1ms
   scheduler `FUN_0002214a`'s task list (mentioned in `notes/TORQUE_PATH_AND_TABLE.md` §0.3) for a
   "CAN message freshness" task.
3. **`FUN_0001cf30`** (HW mailbox/acceptance-filter programming, the very first hop) hits undecoded
   opcodes in r2 — not re-verified this session, carried over from prior memory only.
4. **Exact hardware meaning of STATUS_WORD bits 3/23** (struct-offset-27 bits 2/5 at `0xCD000+
   chan*0x24`) — would need the UPD70F3508 CAN controller register chapter.
5. No opendbc `.dbc` file was available in this repo to confirm the sub-byte-field DBC names
   (COUNTER/CHECKSUM/SET_ME_X) beyond the structural REQUEST-bit match — cross-check against
   `honda_bosch.dbc` (0xE4 STEERING_CONTROL) if/when available.

[[reference-accord-dual-torque-sensor-architecture]] [[reference-accord-consistency-monitor-hardshutdown]] [[reference-accord-voter-0xffff-sentinel]]
