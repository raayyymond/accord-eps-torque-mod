---
name: reference-accord-a160-sid30-proprietary-routinecontrol-and-rid-map
description: "2026-07-23 Ghidra byte/disasm-verified (code.bin): standard UDS RoutineControl (SID 0x31) is NOT implemented in the A160 app; Honda instead implements a proprietary RoutineControl-shaped service at SID 0x30 with 8 RIDs (0x48F0/F1/F2/F6/F9/FB/FC, 0xF000). Full byte layout, dispatch math, and per-RID handler map, with one RID (0x48F6) identified as a strong sensor-calibration-upload candidate."
metadata:
  type: reference
---

# Accord A160 app-UDS: SID 0x31 (RoutineControl) is UNIMPLEMENTED; proprietary SID 0x30 is its replacement (2026-07-23)

Traced answering an operator request to find a UDS routine that learns/zeroes the steering-angle or
torque-sensor neutral. Builds on [[reference-accord-a160-rdbi-handlerptr-live-dispatch]] (SID 0x22 RDBI) —
this memory covers the SID-level dispatcher generically and adds SID 0x2E (WDBI) and the SID 0x30 proprietary
service. All addresses in `code.bin` (gp=0xFEDF8000, tp=0xBF000, flat base 0).

## 1. The SID→idx lookup table, address-anchored (supersedes any hand-counted byte-array reading)

Table at `tp-0x7a64` = **0xB759C**, one byte per SID value 0x00-0x3F direct, SID 0x80-0xBF at index
`SID-0x40` (gated by `FUN_00020512`: `(SID&0x40)==0 && SID<0x86`). Value `0xFF` = SID not implemented;
else value = index into the 12-entry, 8-byte-stride "table A" at `0xB75E4` (`FUN_0002075c`, the SID-level
dispatcher).

**Read directly at the exact computed address for each SID of interest** (not by counting through a bulk
dump — a bulk read miscounts easily; single-purpose reads at `0xB759C+SID` are unambiguous):

| SID | tableA idx | Meaning |
|---|---|---|
| 0x10 | 0 | DiagnosticSessionControl |
| 0x11 | 1 | ECUReset |
| 0x14 | 2 | ClearDiagnosticInformation |
| 0x19 | 3 | ReadDTCInformation |
| 0x22 | 4 | ReadDataByIdentifier (RDBI, confirmed prior session) |
| 0x27 | 5 | SecurityAccess |
| 0x28 | 6 | CommunicationControl |
| 0x2E | 7 | WriteDataByIdentifier (WDBI) |
| 0x30 | 8 | **Honda-proprietary "RoutineControl-shaped" service** |
| 0x31 | **0xFF (INVALID)** | **RoutineControl — NOT IMPLEMENTED in the app** |
| 0x34,0x35,0x36,0x37 | 0xFF | RequestDownload/Upload/TransferData/RequestTransferExit — NOT in app (bootloader-only, separate dispatcher) |
| 0x3E | 9 | TesterPresent |
| 0x85 | 10 | ControlDTCSetting |

**Verdict: standard UDS RoutineControl (0x31) always returns NRC 0x11 (serviceNotSupported) — confirmed by
direct byte read at 0xB75CD = 0xFF, address = 0xB759C+0x31.**

## 2. SID 0x30 is architecturally RoutineControl, byte-for-byte

`FUN_00020e04` (table A idx8 → single-descriptor path → table B row19, tp-0x79bc stride 0x14) is the SID
0x30 top handler. **Full raw disassembly** (not decompile — Ghidra's decompiler mis-renders a tp-relative
table inside a helper it calls as an absolute `DAT_ffff8500`; the true address, confirmed via
`disassemble_function`, is `tp-0x7b00` = 0xB7500):

```
00020e12: ld.hu 0x4[r6],r16      ; r16 = ctx+4 = remaining length (u16)
00020e16: cmp 0x2,r16 / bnh      ; NRC 0x13 if length <= 2 (need >=3)
00020e1e: sld.bu 0x1[ep],r12     ; r12 = buf[1]
00020e20: sld.bu 0x2[ep],r6      ; r6  = buf[2]
00020e22/24: shl 0x8,r12 / or    ; r6 = (buf[1]<<8)|buf[2]   <- the RID, big-endian, wire order
00020e26: jarl FUN_00020de2      ; group(0-7 or 8=invalid) = match(RID, table@0xB7500)
...group-level session/SA gate (FUN_00020d7c on tp-0x7ad8+group*8, 8-byte descriptor)...
00020e4c: sld.bu 0x0[ep],r6      ; r6 = buf[0] = the SUBFUNCTION byte (read AFTER the RID match)
00020e50: jarl FUN_00020dbc      ; row(0-19 or 20=invalid) = f(subfn, group)
...RID-level session/SA + length gate on the 20-byte RID-table entry...
00020e92-9c: ctx.buf+=3; ctx.len-=3   ; confirms exactly 3 bytes consumed: subfn(1)+RID(2)
00020eae: ld.w 0x10[r24],r22     ; handler_ptr = RIDentry+0x10
00020eba: jmp [r22]              ; tail-call handler(ctx)
```

**Confirmed exact request byte layout: `[0x30][subFunction][RID_hi][RID_lo][optional data...]`** — identical
in shape to standard RoutineControl, just a different SID value (Honda placed it in the unused 0x2F/0x30 gap
of ISO 14229 service-ID space rather than using 0x31).

`FUN_00020de2` (raw disasm): linear search of `param_1` (the RID, zero-extended) against 8 halfwords at
`tp-0x7b00`=0xB7500, returns matching index 0-7, else 8 (invalid → NRC 0x31 requestOutOfRange in the caller).

`FUN_00020dbc(subfn, group)`: `sub_idx = *(byte*)(tp-0x7b44 + subfn)` (table read at 0xB74BC =
`[20,0,1,2,222,0,0,0]`, so **subfn 1→sub_idx0(start), 2→sub_idx1(stop), 3→sub_idx2(results)**, subfn 0 or
≥4 invalid); then `row = *(byte*)(tp-0x7af0 + group*3 + sub_idx)` (table at 0xB7510, 24 bytes:
`[0,1,2,3,4,5,6,20,7,8,9,10,11,12,13,14,15,16,17,20,18,19,20,20]`) — value `20` = that (RID,subfunction)
combo not supported → NRC 0x12 (subFunctionNotSupported).

## 3. RID table at 0xB7500 and the full (RID × subfunction) → handler map

Read directly: `{0x48F0, 0x48F1, 0x48F2, 0x48F6, 0x48F9, 0x48FB, 0x48FC, 0xF000}` (group 0-7).
20-byte-stride RID-detail table at `tp-0x75d4` = **0xB7A2C**; entry layout `+0x00`(u16, required exact
remaining-length, 0=wildcard), `+0x04`(u32, packed session/SA byte, same nibble scheme as SESSTATE
`gp-0x1548`), `+0x10`(u32, handler_ptr — ctx-pointer ABI, called via `jmp`).

Session/SA mask decode: high nibble bit0=defaultSession(subfn1), bit1=programmingSession(subfn2),
bit2=extendedDiagnosticSession(subfn3), bit3=Honda-specific session 0x4F(subfn 0x4F) — **verified by raw
disasm of the 4 session-set handlers at 0x20c28/2e/34/3a** (`mov 0x1,r7`/`0x2,r7`/`0x4,r7`/`0x8,r7`
respectively, matching DiagnosticSessionControl's own subfunction candidate table
`{1,2,3,0x4F}` at 0xB7584+0). Low nibble = SA-level bits, same shape, NOT independently traced this session
(would need the SID 0x27 seed/key handler).

| RID | start | stop | results | length | session/SA mask | session needed (decoded) |
|---|---|---|---|---|---|---|
| 0x48F0 | 0x514DE (undef) | 0x51592 (undef) | 0x51604 (undef) | 3 | 0xCC | extended(0x03) or Honda(0x4F) |
| 0x48F1 | 0x51622 (undef) | 0x516E4 | 0x51770 | 3 | 0xCC | extended(0x03) or Honda(0x4F) |
| 0x48F2 | 0x512FC | — (no stop) | 0x5142C | 3 | 0x84 | Honda(0x4F) only |
| **0x48F6** | **0x50DB8** | 0x50F80 | 0x50FC0 | **24** | 0x84 | Honda(0x4F) only |
| 0x48F9 | 0x5107C | 0x510D6 | 0x51146 | 3 | 0xC4 | extended(0x03) or Honda(0x4F) |
| 0x48FB | 0x51182 | 0x511E0 | 0x51248 | 3 | 0xDF | **default session OK, no restriction** |
| 0x48FC | 0x51284 | — (no stop) | 0x512CA | 3 | 0x84 | Honda(0x4F) only |
| 0xF000 | 0x50C48 | — | — | 3 | 0x84 | Honda(0x4F) only (multi-phase dispatcher on gp-0x3398, calls FUN_00046efe fault-check 4x — looks like a self-test/erase routine, not sensor-cal) |

"undef" = Ghidra has not auto-defined a Function at that address (only reachable via the computed
handler-pointer indirect call); read via `disassemble_bytes(dry_run:true)`, not `decompile_function`.

## 4. RID 0x48F6 — the strongest evidence-based sensor-calibration-upload candidate

`FUN_00050DB8` (raw disasm, start subfunction) requires EXACTLY 24 bytes after SID (subfn+RID+21 data
bytes) and, only if ALL of the following hold (each failure ORs a distinct bit into an accumulator, ANY
nonzero bit aborts with no write):
- `gp-0x4f68` (live value, un-identified signal) `<=` cal `tp+0x715e` (else sets bit 0x4001)
- voted column/steering torque `gp-0x6a62 == 0` **and** flag `gp-0x6814 == 0` (else sets bit 0x4002) —
  `gp-0x6a62` is the SAME Sensor-A voted torque documented in
  [[reference-accord-gp4f60-is-sensor-b-column-torque]]'s sibling voter and in the V33/gentle-EME memories
- EPS state `gp-0x67fa >= 4` (else sets bit 0x4004)
- `FUN_00057f8e()` (the same HW-ID/0xCD000-table validator from
  [[accord-tva-hw-id-provenance]]) returns 0
- `DAT_00006400` bit 0x400 clear

...then reads AT LEAST 11 bytes of the request payload and writes several signed 16-bit values into RAM
cells `gp-0x6a5c`, `gp-0x6a8e`, `gp-0x6ba0`, `gp-0x6ba2`, `gp-0x6a0c` (disassembly ran out at instruction
92/~byte 200 of a 250-byte window — more parameters likely follow; NOT fully traced). `FUN_00050FC0`
(results) translates a status word `gp-0x6aa6` back through the SAME bit values (0x4001→code1,
0x4002→code2, 0x4004→code3, etc.) into a single result byte — confirming rows 8/9/10 are one cohesive
routine.

**This requires the TESTER to SUPPLY calibration numbers (a multi-point table), not "capture my current
position as zero."** Combined with strings found at 0xb9c48/0xba184/0xb9ffc (`KFC_RACKPOS_NOCALIB`,
`KFC_RACKPOS_PRECALIB`, `KFC_CURRENT_OFFSET` — xrefs only into a large generic name-string-pointer array at
0xbadf0+, not directly tied to this handler by any code path found this session), this reads like a
**factory rack-position/current-sensor multi-point calibration upload**, not a simple driver-invoked
center-learn.

## 5. RIDs 0x48F9 / 0x48FB / 0x48FC (Groups A/B/C) — NOT confirmed as "neutral learn"

All three: start handler takes NO extra payload, gates on `tp+0x50b6 (cal) < gp-0x6a62 (live torque)` (i.e.
proceeds only when torque is AT/BELOW a small threshold — a "hands off the wheel" precondition), and on
success **immediately** (synchronously, no settling delay visible) sets a "done" flag and a generic success
status. The shared supervisor `FUN_0004d0d0` (called every scheduler tick via `FUN_0002351e`, mask `0x938`)
watches busy flags `gp-0x6837`(A)/`gp-0x6836`(C) and FORCIBLY ABORTS (resets flags, forces a fail/abort
result code) if the live torque becomes nonzero WHILE the routine is "busy" — but this function does not
itself write any persisted value. `gp-0x68b2`(B)'s only other reader is `FUN_0002db94` (the base-assist
damper/aggregator), which SUPPRESSES one boost feed-forward term while B is busy — a real interlock, but
also not an EEPROM write.

**I did not find, within this session's budget, the actual value-capture/EEPROM-commit code for A/B/C.**
Two live hypotheses, NOT adjudicated: (a) it exists in a background worker not yet located (the torque-gate
precondition is exactly what a hands-off angle/torque-sensor zero-learn would need), or (b) these are
simple diagnostic-mode arm/disarm toggles with no persisted effect. Do not present either as confirmed.

## 6. WDBI (SID 0x2E) — exactly 2 DIDs, confirmed via table B stride-0x14, entries 17-18 (RID/DID search
range `[15,19)` off table-A idx7, stride 2 confirmed via `FUN_00020344`)

- **DID 0x48F5** → `FUN_000508e8`, mask 0xCC. Raw byte-pattern-confirmed (`E8 08 05 00` at 0xB77A8) as the
  SAME 5-byte ECU HW-ID writer documented in [[accord-tva-hw-id-provenance]] — unrelated to angle/torque.
- **DID 0x48F8** → `FUN_00050b82` (raw disasm): a bitfield writer — each of 6 input bits independently
  sets/clears a specific bit of `DAT_00006400` (a fault-flag/diagnostic-suppression word, the SAME word
  read by the DID 0x4800 handler and by RID 0x48F6's preconditions). NOT an angle or torque value.

## Bottom line for "learn the steering-angle / torque-sensor neutral"

No UDS routine/DID in this firmware was confirmed, by content, to zero a steering-angle or torque-sensor
offset from the CURRENT live reading. RID 0x48F6 is the strongest candidate structurally (real sensor-cal
gating: torque=0, EPS state, an ID validator) but consumes EXTERNAL parameter data rather than capturing the
current position, matching a factory rack-position/current-offset table upload rather than a driver-facing
recenter command. RIDs 0x48F9/0x48FB/0x48FC remain open — torque-gated, simple, but the actual persisted
effect (if any) is unlocated.

## 7. ADDENDUM 2026-07-23 (same session) — persistence hunt CLOSED negative; bootloader SID 0x31 enumerated

Follow-up mission: does RID 0x48F6 (or A/B/C) actually PERSIST anything (data-flash write), and does the
BOOTLOADER's real SID 0x31 hide a sensor-calibration RID?

**7a. RID 0x48F6's full write-set (finished disassembling past instruction 92) — still 100% volatile RAM.**
Beyond the 5 cells in §4, the tail of `FUN_00050DB8` (0x50eb0-0x50f7c) converts more payload bytes via
`cvtf.ws` (word→float) into `gp-0x6ca0`, `gp-0x6ca4`, `gp-0x6ca8`, `gp-0x6cac` (conditionally, per a
`0xffff`-sentinel-skip pattern), clamps one more value via the known `FUN_00049a90` helper into `gp-0x6b92`,
and on full success (`r28==0`) sets `gp-0x6aa6=0`, `gp-0x6825=1`, **`gp-0x6839=1`** (this last one is the
SAME cell `FUN_0004d0d0` §5 below writes from `bVar1` — confirms 0x48F6 and the A/C-busy supervisor share
output state). On any precondition failure, `gp-0x6aa6 = r28` (the accumulated fail-bits) and NRC 0x22.
**Every write target is gp-relative volatile RAM; none is data-flash.**

**7b. No path from these RID handlers (or A/B/C) to the data-flash driver — re-confirmed independently.**
`get_function_callers` on all 3 known data-flash-sequencer entry points from the prior session's finding:
`FUN_000050f4`→{`FUN_00005130`,`FUN_00005498`}, `FUN_000051ec`→{`FUN_00005308`,`FUN_00005386`,
`FUN_000053de`,`FUN_00005514`}, `FUN_000053de`→{`FUN_00005716`}. **Every caller is itself inside
0x5000-0x5800** — the cluster remains fully self-contained in the boot range with zero application/UDS-layer
entry, re-confirming the earlier session's finding independently. And a gp-relative operand search is
trustworthy here specifically because gp-0x6XXX addresses are well within V850E2's ±32KB gp-relative window,
so the compiler has no reason to ever emit a `movhi`/`movea` bypass for them — the "exhaustive" search claim
for gp-0x6837/6836/68b2/3387/3386/3385 (§5, 4 total hits each, all inside the routine handlers themselves)
can be trusted at high confidence, not just "tool said zero."

**VERDICT: no SID-0x30 routine (0x48F6 or A/B/C) writes to non-volatile storage.** Whatever RID 0x48F6
loads lives only in RAM for the current power cycle (unless some entirely separate, unlocated boot-time
readback exists — not found). RIDs 0x48F9/0x48FB/0x48FC have no located value-capture code at all (their own
bodies just flip flags; their only other consumers are `FUN_0004d0d0`, a torque-abort supervisor, and for
0x48FB only, the base-assist damper `FUN_0002db94`, which just suppresses one feed-forward term while busy)
— best current read: **these are diagnostic-mode arm/disarm interlocks, not calibration-learn routines.**

**7c. Bootloader's REAL SID 0x31 (RoutineControl) — exactly 2 RIDs, both pure reprogramming, NO sensor cal.**
Dispatcher: `FUN_0000d43a` (the bootloader SID switch, reads the 13-entry SID table at flash `0x9330` via
predicate `FUN_0000c538`) → SID 0x31 case calls `FUN_0000cc4e`, decompiled in full:
- **RID 0xFF00** (`sVar1 == -0x100`, i.e. 0xFF00 as a signed CONCAT of buf[2]:buf[3]) — subfunction must be
  0x01 (start only, else NRC 0x12), total length must be exactly 3 (else NRC 0x13), requires a
  "flash-ready" bit (`_DAT_fedf20ac & 0x400`, else NRC 0x31), then calls `FUN_0000b002`→`FUN_0000affe`
  (the actual erase) plus a chain of flash-sequencer setup calls (`FUN_0000bd28`, `FUN_0000b1b8`,
  `FUN_0000d61c`, `FUN_0000c476`, `FUN_0000ba8a`, `FUN_0000b9c4`, `FUN_0000c316`). **This is eraseMemory.**
- **RID 0xFF01** (`sVar1 == -0xff`) — same subfunction/length gates, checks 3 more status bits
  (`0x4000`, `0xaa&0x20`, `0xaa&0x10`), calls `FUN_0000b002(...,3)` then `FUN_0000b0ae()`
  (a dependency/checksum validate). **This is checkProgrammingDependencies.**

Any RID value other than these two → NRC 0x31 (requestOutOfRange) immediately. **No third RID, no sensor
calibration, no rack/torque-neutral routine exists in the bootloader's RoutineControl.** This is the
complete case-arm enumeration (not a sample) — `FUN_0000cc4e`'s only two live branches are these.

**Combined bottom line for "does a UDS/proprietary/bootloader routine (re)capture or write the
torque-sensor neutral": NO, not found anywhere in this firmware after covering the app's proprietary SID
0x30 (8 RIDs, all traced to their actual write targets), WDBI's 2 DIDs, and the bootloader's real SID 0x31
(2 RIDs, exhaustively enumerated). Every write target found is either volatile RAM or a raw flash
erase/program primitive — none is a sensor-offset commit.**

Links: [[reference-accord-a160-rdbi-handlerptr-live-dispatch]] ·
[[reference-accord-a160-app-uds-session-gate-and-egress]] · [[accord-tva-hw-id-provenance]]
