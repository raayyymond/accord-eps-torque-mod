# SPEC — UDS-over-CAN RAM telemetry for the gentle-EME (39990-TVA-A160)

> ## ⚠ CORRECTED + SUPERSEDED (2026-07-10) — this channel is now BUILT, FLASHED, and WORKING as V31U.
> Two facts in the original design below are WRONG; use these instead (see
> `docs/HANDOFF-2026-07-10-v31u-uds-telemetry-working.md` and
> `.claude/agent-memory/firmware-codepath-tracer/reference_accord_a160_rdbi_handlerptr_live_dispatch.md`):
> 1. **Request address is `0x18DA30F1` (resp `0x18DAF130`), NOT `0x18DA80F1`.** The A160 `%` header = `30`.
> 2. **RDBI per-DID table TRUE base is `0xB77FC` (NOT `0xB7800`), stride 0x14**, struct
>    `u16 did; u16 declared_len; u32 gate; u32 session; u32 group; u32 handler_ptr`. The **live per-DID
>    dispatch reads `handler_ptr` at entry+0x10 and calls it with a ctx pointer in r6** (`FUN_000209ea`).
>    DID `0x4801` = **idx1** (entry base `0xB7810`): declared_len `@0xB7812`, handler_ptr `@0xB7820`.
>    The §3 patch below targeted `0xB780C`/`0xB7800` = DID **0x4800**'s fields (off-by-one entry) → the cave
>    was never reached. The CORRECT patch: `0xB7820` handler_ptr → cave `0x000C4E00`; `0xB7812` len → 10;
>    leave `0xB780C` (0x4800) stock. Built + flashed by `analysis-2020accord/build_v31u_uds_telem_tva.py`.
> The cave handler, ABI, cipher/CRC machinery, gateway-crossing rationale, and RAM signal set below are all
> still correct — only the table base + address were wrong.

**Status (original 2026-07-08):** design-complete, byte-level, **UNBUILT / UNFLASHED**. Study artifact.
**Platform:** 2020 Honda Accord EPS, `39990-TVA-A160`, Renesas uPD70F3508 / V850E2.
**Analysis program:** `code.bin` (stock full dump) in Ghidra project `accord2020_ghidra` — `V850:LE:32`,
flat base 0, offset==addr. gp(r4)=0xFEDF8000, tp(r5)=0xBF000.
**Date:** 2026-07-08. Supersedes the "next best option" question in
`docs/HANDOFF-2026-07-08-tier1-telemetry-and-visibility-correction.md`.

⚠ Ghidra has TWO programs open — always target **`code.bin`** (the other, `_tier1_plain_image.bin`,
is a build output with no analysis; querying it silently returns nothing).

---

## 0. Why this exists (one paragraph)

Broadcast-CAN telemetry is dead: the EPS uses a **single** CAN controller (FCN0, mailbox 6) for *all*
frames, so 0x660 and 399 leave on the same wire — the car's external gateway forwards only
`{399, 427, 0x14A}` + diagnostics and drops the rest (proven on-car: TIER1 rearmed 0x660 to 100 Hz, still
absent — see `analysis-2020accord/can-scans/2026-07-08-*`). The **diagnostic** channel, however, crosses
the gateway (that's how `eps-update-tva.py` flashes over OBD). So telemetry must ride UDS-over-CAN. Stock
firmware exposes **no** arbitrary-RAM read on the CAN-native diagnostic stack (SID 0x23 absent; no
RAM-backed DID). This spec adds one, minimally, in the **application** region.

---

## 1. Diagnostic architecture (verified this session in Ghidra)

Three diagnostic stacks:

| Stack | Where | Services | Egress | Use |
|---|---|---|---|---|
| Bootloader UDS | file `0x0–0xFFFF` (OFF-LIMITS) | 0x34/0x36/0x37/0x35/0x31 erase+CRC, own SA | CAN, PROGRAMMING session | flashing |
| **App ISO-TP UDS** | app region | 0x10/0x22/0x27/0x2E/0x31/0x3E | **CAN (FCN0), native** | **← we patch here** |
| Legacy KWP on 0x72A | app region | 0xF4 RAM read, 0x34 bridge | K-line | (dead end for comma) |

Request/response IDs (flasher-proven): **request `0x18DA80F1`, response `0x18DAF180`** (29-bit ISO-TP).

### The RDBI (SID 0x22) read path — call chain (all in `code.bin`)
```
CAN RX → ISO-TP reassembly → FUN_0002075c  (app UDS SID dispatcher)
  SID→service-index table @0xB759C[SID]      (0x22 → index 4)      [FUN_00020512]
  service-entry table @0xB75E4 (stride 8)     (entry 4 = 01 00 2F 0D 01 09 08 00)
    byte[1]&0xF == 0  →  fixed descriptor index = byte[5] = 9   (NO per-DID gate here)
  service-descriptor @0xB7644 (stride 0x14), index 9 → handler FUN_00021036
FUN_00021036  (RDBI top: accepts 1–5 DIDs, length must be even ≥2) → FUN_00020f0a
FUN_00020f0a  (per-DID loop):
    FUN_00020d76  raw 2-byte DID → DID-index (0..0x1B) via key table @0xB7584
    if index < 0x1C:  dispatch DID-descriptor @ (0xB7800 + index*0x14)   [FUN_00020ce2]
Response: framework turns SID 0x22 → 0x62 and echoes the DID bytes; handler appends data;
          TX on FCN0 with response ID from gp-0x1700 (= 0x18DAF180), multi-frame ISO-TP.
```

### The RDBI DID descriptor table @ `0xB7800` (this is the insertion layer)
Stride **0x14 (20) bytes**, indices 0..27 (`FUN_00020f0a` gate: `index < 0x1C`). Entry layout
(little-endian, byte-verified from ROM):

| off | size | field | typical |
|---|---|---|---|
| +0x00 | u32 | gate/SA flags | `0xDF` (readable, no SA) |
| +0x04 | u32 | session mask | `0x0F` (all sessions) |
| +0x08 | u32 | flags | `0` |
| +0x0C | u32 | **handler pointer** | e.g. `0x0004F6D6` |
| +0x10 | u16 | **DID** (LE) | e.g. `0xF181` |
| +0x12 | u16 | **declared length** | e.g. `0x0010` |

Decoded DID list (index : DID : handler : len): 0:`0x4801`/`4D5C2`/56 · 1:`0x480A`/`4D8DC`/56 ·
2:`0x480B`/`4DDFC` · 3:`0x48A0` · 4:`0x48A2` · 5:`0x48AC` · 6:`0x48AF` · 7:`0x48B9` · 8:`0x48BD` ·
9:`0x48BE` · 10:`0x48E0` · 11:`0x48E1` · 12:`0x48E2` · 13:`0x48F5` · 14:`0x48F8` · 15:`0x48FD` ·
16:`0x48FE` · 17:`0x48FF` · 18:`0xE600` · 19:`0xE602` · 20:`0xF100` · 21:`0xF110` · 22:`0xF112` ·
23:`0xF116` · 24:`0xF180` · 25:**`0xF181`**/`4F6D6`/16 (app-SW-id, the part string the flasher reads —
DO NOT touch) · 26:`0xF186`/`4F6FA`/2 · 27:`0x0003`/`4F72C` (looks like a sentinel).

### DID-handler ABI (template = stock `0xF181` handler `FUN_0004f6d6`)
```c
void handler(int ctx) {              // ctx in r6
    *(u16*)(ctx + 0xC) = declared_len; // = data_len + 2 (the +2 = the echoed DID)
    FUN_000211ba();                    // response-SM step (0x000211BA)
    FUN_0002114e(src_ptr, n);          // append n bytes from src_ptr (0x0002114E); multi-frame-safe
    ... more appends ...
    FUN_0002073a();                    // finalize/commit (0x0002073A)
}
```
`FUN_0002114e(int src, u16 n)`: appends `n` bytes from absolute pointer `src` to the response payload
(handles the 62-byte ISO-TP segmentation internally). Confirmed by the `0xF181` handler:
`declared_len=0x10` (16), then appends `0xE` (14) data bytes → **declared = data + 2**.

---

## 2. Telemetry target (gentle-EME signals in RAM)

| signal | RAM addr | gp offset | width |
|---|---|---|---|
| voter-MAX torque (`gp-0x6a62`) | `0xFEDF159E` | −0x6A62 | u16 |
| voter-AVG torque (`gp-0x6a5e`) | `0xFEDF15A2` | −0x6A5E | u16 |
| \|column torque\| (`gp-0x4f68`) | `0xFEDF3098` | −0x4F68 | u16 |
| angle suspect (`gp-0x6cc4`) | `0xFEDF133C` | −0x6CC4 | u16 |

⚠ Correction to an earlier note: voter-MAX and voter-AVG are **4 bytes apart** (0x159E vs 0x15A2), NOT
adjacent — a 4-byte read from 0x159E would grab an unrelated word at 0x15A0. Use **four explicit 2-byte
appends**. Total payload = 8 bytes. RAM is little-endian → response bytes are LE → decode as LE u16.

---

## 3. THE PATCH (recommended: repurpose one expendable DID)

**Approach A — repurpose (RECOMMENDED, minimal): 2 field edits in one existing DID entry + one cave
handler.** Pick an expendable `0x48xx` DID (openpilot never reads UDS DIDs; the only stock consumer of a
`0x48xx` is Honda's dealer tool during a specific diagnostic — acceptable to sacrifice for a temporary
study/telemetry flash). Example below uses **index 0 = DID `0x4801`** (`0xB7800`); substitute any other
`0x48xx` by changing only the entry base address.

### 3.1 Table edit (at `0xB7800` + index*0x14; index 0 shown → base `0xB7800`)
| field | offset | stock | new |
|---|---|---|---|
| handler ptr | `0xB7800 + 0x0C` = **`0xB780C`** | `C2 D5 04 00` (0x0004D5C2) | **`00 4E 0C 00`** (0x000C4E00, the cave) |
| declared len | `0xB7800 + 0x12` = **`0xB7812`** | `38 00` (56) | **`0A 00`** (10 = 8 data + 2 DID echo) |

Leave +0x00 (`0xDF`), +0x04 (`0x0F`), +0x10 (DID `01 48`) unchanged → stays default-session, no-SA,
DID `0x4801`.

### 3.2 Cave handler (place at `0xC4E00`; 492 bytes of erased 0xFF available, app-region, CRC-covered)
V850E2 assembly, mirrors `FUN_0004f6d6`:
```asm
; entry: r6 = ctx
prepare {lp}, 0                 ; save return addr (calls clobber lp)
mov     0x0A, r1
st.h    r1, 0x0C[r6]            ; *(u16*)(ctx+0xC) = 10  (= 8 data + 2 DID echo)
jarl    0x000211BA, lp          ; FUN_000211ba (response-SM step)
movhi   0xFEDF, r0, r6          ; \
movea   0x159E, r6, r6          ;  } src = 0xFEDF159E  (voter-MAX)
mov     2, r7                   ; /
jarl    0x0002114E, lp          ; append 2 bytes
movhi   0xFEDF, r0, r6
movea   0x15A2, r6, r6          ; voter-AVG
mov     2, r7
jarl    0x0002114E, lp
movhi   0xFEDF, r0, r6
movea   0x3098, r6, r6          ; |column torque|
mov     2, r7
jarl    0x0002114E, lp
movhi   0xFEDF, r0, r6
movea   0x133C, r6, r6          ; angle
mov     2, r7
jarl    0x0002114E, lp
jarl    0x0002073A, lp          ; FUN_0002073a (finalize)
dispose 0, {lp}
jmp     [lp]                    ; return
```
All four `movea` immediates (< 0x8000) sign-extend positively → correct 0xFEDF____ addresses. ~80 bytes.

### 3.3 CRC
Both edits (`0xB7800` table, `0xC4E00` cave) lie in the flashed window `[0x13000, 0x100000)` and inside
CRC-protected blocks. Recompute the covering block CRC(s) using the existing machinery in
`analysis-2020accord/build_tier1_telem_tva.py` (`TOUCHED_BLOCKS` + `recompute_crc`). Emit the `.rwd` via
`encode_x31` exactly as TIER1 does; self-check 49/49 + ECU-decode==patched image.

**Approach B — add a new DID (zero sacrifice), if preferred:** add a descriptor at index 27/28 + a
key-table entry at `0xB7584` (used by `FUN_00020d76`) + (if index ≥ 0x1C) bump the `< 0x1C` limit in
`FUN_00020f0a`/`FUN_00020d76`. More edits and requires reversing the `0xB7584` key-table insert format
(FUN_00020d3a) — heavier. Only pursue if sacrificing a `0x48xx` DID is unacceptable.

---

## 4. Region confirmation (app only — NOT bootloader)

Flash window = `[0x13000, 0x100000)` (bootloader `0x0–0xFFFF` is NOT in the `.rwd`). All touched
addresses are inside it: table `0xB7800`/`0xB780C`/`0xB7812`, cave `0xC4E00`, and every called helper
(`0x211BA`, `0x2114E`, `0x2073A`) — all app-region. Independently corroborated: TIER1 already patched
code `0x561B0` + data `0xB7CA0`/`0xB7264` in this same window and produced a valid 49/49 `.rwd`.

---

## 5. Capture & decode (on-car)

Because the gentle-EME needs openpilot actively steering to reproduce, run the UDS poll on a **second red
panda on the OBD port** (operator's red-panda+laptop workflow) while the comma drives — sidesteps
openpilot's TX safety restrictions.

- **Request** (ISO-TP, 29-bit): to `0x18DA80F1`, payload `22 48 01` (SID 0x22, DID 0x4801 big-endian on wire).
- **Response**: from `0x18DAF180`, `62 48 01 <b0..b7>` (multi-frame; panda UDS client handles flow control).
- **Decode** (`b0..b7`, all little-endian u16): `[0:2]`=voter-MAX, `[2:4]`=voter-AVG, `[4:6]`=|column
  torque|, `[6:8]`=angle. Poll rate: CAN request/response supports tens–hundreds of reads/sec — ample
  for the ~90 ms cut (vs K-line's 2–4 samples). **Per the iron rule, the operator names the exact
  payload + bus and I repeat it back before any request is sent.**

---

## 6. Confidence & final pre-build checks

**Evidence (decompiled this session):** dispatcher `FUN_0002075c`, RDBI top `FUN_00021036`, per-DID loop
`FUN_00020f0a`, handler template `FUN_0004f6d6`, append primitive `FUN_0002114e`, SM steps
`FUN_000211ba`/`FUN_0002073a`; tables `0xB759C`/`0xB75E4`/`0xB7644`/`0xB7800` read raw from ROM; cave
`0xC4E00` (492×0xFF) confirmed.

**Belief / to confirm at build (each trivial, none change the design):**
1. Declared-length convention: I use `+0xC = data+2 = 10`, mirroring `0xF181` (16 = 14+2). If a bench read
   comes back 2 bytes short/long, adjust this one constant — immediately visible.
2. If choosing a *specific* expendable DID matters, decompile that entry's stock handler once to confirm
   its function is non-critical (or just pick any `0x48xx` for a study flash).
3. Assemble the handler and byte-verify the emitted (encrypted→decoded) image disassembles to the intended
   instructions before flashing (same discipline as TIER1).

**Safety:** read-only DID; no SecurityAccess; default session; touches only the diagnostic read surface —
no command/torque/motor/soft-EME/engage-SM/fault path. Study artifact until the operator explicitly
authorizes a build + flash by file name + bus.
