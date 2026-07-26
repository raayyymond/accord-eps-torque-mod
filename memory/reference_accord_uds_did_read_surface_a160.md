---
name: reference-accord-uds-did-read-surface-a160
description: "2020 Accord EPS (39990-TVA-A160) app UDS-over-CAN RAM telemetry — WORKING as V31U (flashed 2026-07-10). Request 0x18DA30F1 / resp 0x18DAF130 (NOT 0x18DA80F1; A160 % header=30), comma-visible/gateway-crossing. RDBI per-DID table TRUE base 0xB77FC (NOT 0xB7800), stride 0x14: u16 did; u16 declared_len; u32 gate; u32 session; u32 group; u32 handler_ptr(+0x10). LIVE per-DID dispatch = FUN_000209ea reads handler_ptr(entry+0x10), calls it with ctx ptr in r6 (drained per-tick by w_steer_control_task after FUN_00021036 arms a pending bit). DID 0x4801=idx1 @0xB7810. Working telemetry = repurpose 0x4801: handler_ptr @0xB7820 -> cave 0x0C4E00, declared_len @0xB7812 -> 10. Reads 4 gentle-EME globals (voter-MAX 0xFEDF159E, voter-AVG 0xFEDF15A2, |coltq| 0xFEDF3098, angle 0xFEDF133C) as 4x LE u16. Broadcast (0x660) is gateway-blocked; UDS is the only CAN telemetry path."
metadata:
  node_type: memory
  type: reference
---

# Accord EPS UDS-over-CAN DID read surface — WORKING RAM telemetry (V31U)

**STATUS: BUILT + FLASHED + LIVE-VALIDATED (2026-07-10).** `39990-TVA,A160-V31U-...rwd` reads 4 gentle-EME
RAM globals over CAN on DID `0x4801`; `|coltq|` + `angle` track the wheel live (voters read 0 without LKAS).
This corrects the two errors in the original 2026-07-08 mapping (address `0x18DA80F1`, table `0xB7800`).

## The channel (what to send/decode)
- **Request:** ISO-TP 29-bit → **`0x18DA30F1`**, `22 48 01`. **Resp** from **`0x18DAF130`**: `62 48 01 <b0..b7>`.
  (`0x18DA30F1` NOT `0x18DA80F1` — the A160 `%` header is `30`; the flasher dry-run TX proved it.)
- **Decode** (`b0..b7`, 4× LE u16): `[0:2]`=voter-MAX torque `gp-0x6a62`/`0xFEDF159E`; `[2:4]`=voter-AVG
  `gp-0x6a5e`/`0xFEDF15A2`; `[4:6]`=`|column torque|` `gp-0x4f68`/`0xFEDF3098`; `[6:8]`=angle
  `gp-0x6cc4`/`0xFEDF133C`. Reader: `tools/bench_uds_telem_read.py` (defaults correct).

## Three diagnostic stacks (only app-UDS is comma-visible + non-bootloader)
1. **Bootloader UDS** (file `0x0–0xFFFF`, OFF-LIMITS): flash chain, own SA, PROGRAMMING session.
2. **App ISO-TP UDS** (app region): req `0x18DA30F1`/resp `0x18DAF130`, native FCN0/CAN, **crosses the car
   gateway** (that's how OBD flashing works). ← the telemetry channel.
3. Legacy KWP on 11-bit `0x72A`: SID `0xF4` RAM read but egress is **K-line** → dead end for the comma.

## App UDS dispatch (CORRECTED — all in `code.bin`, gp=0xFEDF8000, tp=0xBF000)
- SID top: `FUN_0002075c` → SID 0x22 RDBI → `FUN_00021036` → validate/pass-1 `FUN_00020f0a` (binary-search
  DID→idx over the table, session/SA gate, writes idx to `gp-0x1574`, arms pending bit `gp-0x1552` bit0).
- **LIVE per-DID payload dispatch = `FUN_000209ea`**, drained **per-tick by `w_steer_control_task`**: reads
  `handler_ptr = *(u32*)(0xB77FC + idx*0x14 + 0x10)` and calls `handler_ptr(ctx = &gp-0x15f4)` — **ctx
  POINTER in r6**. Proven live because DID `0xF181` builds its app-id string this exact way (its own
  handler_ptr `0x4F6FA`).
- `groupID` byte (entry+0xC) → 7-slot jump table `0xB7568` is an **orthogonal** response-builder STATE
  dispatch that passes a **masked scalar** in r6 — NOT the per-DID payload path. Do NOT repoint it for a
  ctx-pointer cave (corruption risk).

## The RDBI DID descriptor table — TRUE base `0xB77FC` (NOT 0xB7800), stride 0x14
Struct (LE): `+0x00 u16 DID` · `+0x02 u16 declared_len` · `+0x04 u32 gate (0xDF)` · `+0x08 u32 session
(0x0F)` · `+0x0C u32 group (low byte=groupID)` · `+0x10 u32 handler_ptr`. 28 entries, DID-sorted (binary
search). idx0=`0x4800` (hp `0x4D5C2`), **idx1=`0x4801`** (hp stock `0x4D8DC`, entry base `0xB7810`),
idx26=`0xF181` (hp `0x4F6FA`). ⚠ The earlier "`0xB7800`, handler@+0x0C, idx0=0x4801" mapping was read 4
bytes late (one entry off) — that error wired the old build's cave to DID **0x4800**.

## DID-handler ABI (template = 0xF181 handler)
`handler(ctx /*r6 = pointer*/)`: `*(u16*)(ctx+0xc) = declared_len` (= data_len + 2) → `FUN_000211ba()` →
`FUN_0002114e(src_ptr /*r6*/, n /*r7*/)` appends n bytes from an absolute pointer (live read at call time,
multi-frame ISO-TP safe) → `FUN_0002073a()` finalize.

## Working telemetry build (V31U — FLASHED)
`analysis-2020accord/build_v31u_uds_telem_tva.py` = V31 cal + repurpose **idx1 / DID `0x4801`**: handler_ptr
`@0xB7820` `0x4D8DC → 0x000C4E00`; declared_len `@0xB7812` `56 → 10`; 72-byte cave `@0xC4E00` (clean
`0xF181`-class clone) appends the 4 signals. Leave `0xB780C` (DID 0x4800 hp) STOCK. Both handler+len must
match (a len-only or handler-only edit fails: len-mismatch hangs, handler-mismatch reads stale). 49/49 CRC,
byte-diff vs proven V31 = 74 bytes telemetry-only. Superseded builds: `build_uds_telem_tva.py` (off-by-one,
cave on 0x4800); `build_tier1_telem_tva.py` (0x660 broadcast, gateway-blocked).

## Gotchas
- **Two Ghidra programs open**: analyze `code.bin` (stock); `../accord-firmware/analysis-2020accord/_*_plain_image.bin` are build outputs.
- Repurposing DID 0x4801 needs BOTH handler_ptr (`0xB7820`) AND declared_len (`0xB7812`); the `0x4800`
  freeze on 2026-07-10 was a len-mismatch (cave emits 10, table said 56).
- **Next step is openpilot-side:** log this DID into rlogs during an LKAS drive (voters only move then) — see
  `docs/HANDOFF-2026-07-10-v31u-uds-telemetry-working.md` §5.

Links: [[reference-accord-can-single-fcn0-external-gateway]] · [[reference-accord-gp-base-fedf8000]]
