# How to Build a Flashable `.rwd` for the 2020 Honda Accord Touring (TVA EPS)

**Vehicle:** 2020 Honda Accord Touring — EPS ECU `39990-TVA-A160` (siblings `A110`, `A340`)
**MCU:** Renesas µPD70F3508, V850E2/Px4 core, **little-endian**, 1 MB code flash (`0x0–0xFFFFF`)
**Container:** `x31` (`1\r\n` magic) — the V850 family format
**Status:** **The V9b build process below is CONFIRMED CORRECT.** `../accord-firmware/flashing-2020accord/rwd/39990-TVA-A160-RECONSTRUCTED-v9b-0x13000-0x100000.rwd` flashed successfully on the operator's car (2026-05-24). Every step here is validated against that working flash — this is the recipe of record, not a hypothesis.

> This document supersedes the old `STOCK_RECONSTRUCTION_REPORT.md`, `CIPHER_KEY_ORDER_BUG.md`, `BOOTLOADER_CRC_SOLVED.md`, `ENCODER_REPORT.md`, the SA-key report chain, and the `ACCORD_TVA_ARCHITECTURE_MAP.md` build sections. It is the single source for producing a `.rwd` — **stock recovery or modified firmware**.

---

## 0. TL;DR — the seven things that make a `.rwd` the ECU accepts

A V9-series build succeeds because **all** of these are right at once. The long v3→v8 failure history was a sweep through getting each one wrong in turn:

1. **Container = x31**, headers copied from the genuine V850 template `../accord-firmware/iHDS_rwds/CalibFiles/39990-T2F-A210.rwd.gz`, with `/`, `!`, `%` substituted for TVA. (§3)
2. **Cipher = `((c ^ 0xBF) ^ 0x10) - 0x9E`** — xor, xor, sub with key bytes `0xBF, 0x10, 0x9E`. This is the literal on-ECU decryptor. **CONFIRMED by the V9b flash.** (§2)
3. **Window = single contiguous block `[0x13000, 0x100000)`** (length `0xED000`). This is the exact window the ECU's bootloader advertises as programmable. (§4)
4. **Written cipher key = raw `BF 10 9E`** to DID `0x2E F101` (FLASH_DECRYPTION_KEY). (§2, §6)
5. **Per-4 KB-block CRC-32 trailers intact** for every protected block in the window — passed through verbatim for stock, **recomputed** for any patch. (§5)
6. **SA handshake** via the firmware-embedded Group C constants `(0x0211, 0x0212, 0x1220)`, not the `!` header. (§6)
7. **Pre-flash self-validation:** decode your own payload with the on-ECU cipher, splice into a 1 MB image at `0x13000`, and run the bootloader CRC-32 walk → **49/49 blocks must PASS** before you flash. (§5, §7)

If you change firmware bytes (a torque table, a clamp, anything), only steps 5 and 7 require extra work beyond stock: recompute the CRC trailer of any block you touched, then re-run the CRC walk. Everything else is identical to the stock build.

---

## 1. Artifact location and build script

The build scripts remain in this repository, but firmware inputs and outputs are
external. From the repository root, the default artifact root is
`../accord-firmware`; Python tools honor `ACCORD_FIRMWARE_ROOT` when it is set.
The stock input is `../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin`
and generated containers go to
`../accord-firmware/flashing-2020accord/rwd/`.

`analysis-2020accord/old_tools/build_stock_tva_v9.py` is the builder of record. It:

- reads `../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin` (the decrypted 1 MB image),
- builds the on-ECU **decode** table, inverts it to an **encode** table,
- enciphers the window `../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin[0x13000:0x100000]`,
- wraps it in an x31 container with TVA headers,
- **self-verifies**: re-decodes its own payload as the ECU would and replays the bootloader CRC-32 walk, refusing to write the file unless `ECU-decode == code.bin` AND 49/49 CRC blocks pass.

Run it:

```
python analysis-2020accord/old_tools/build_stock_tva_v9.py
```

Supporting modules (all in `analysis-2020accord/`, do not delete):
- `encode_eps.py` — x31/x5a parse + encode, cipher table builder/inverter (`build_decode_table`, `invert_table`, `encode_x31`, `parse_x31`, `OPS`).
- `verify_bootloader_crc.py` — `walk(img)` replays the ECU's `checkProgrammingDependencies` CRC chain. The pre-flash gate.
- `analysis-2020accord/old_tools/decode_eps.py` — the `.rwd` → `code.bin` decoder + cipher cracker (for inspecting other files).

> **Historical note on V9a:** the build originally emitted two cipher candidates — V9b (resident-decryptor cipher) and V9a (a fallback derived from the genuine T2F file, `((c-0x9E)+0xBF)^0x10`). The successful V9b flash proves the resident-decryptor cipher is the ECU's real decoder, so **V9a is retired.** Only the V9b cipher arrangement is correct. If you re-run the builder, use the V9b variant; ignore/remove the V9a path.

---

## 2. The cipher — CONFIRMED

The `.rwd` payload is a per-byte substitution. The ECU's resident decryptor (`FUN_0xB35E` in `code.bin`, invoked by the TransferData handler) does, for each ciphertext byte `c`:

```
plaintext = ((c ^ 0xBF) ^ 0x10) - 0x9E      # == (c ^ 0xAF) - 0x9E   (mod 256)
```

i.e. **ops = (xor, xor, sub)** with key bytes **`k0=0xBF, k1=0x10, k2=0x9E`**. These key bytes are loaded fresh per byte from RAM `0xFEDF20BB/BC/BD`, written there by the `0x2E F101` key-write handler; decryption is gated on bit 2 of `0xFEDF20AA` (set by that same write).

The **encode** table (host side) is simply the inverse permutation of that decode table — `encode_eps.invert_table(build_decode_table((0xBF,0x10,0x9E), (OPS.xor, OPS.xor, OPS.sub)))`.

### The cipher trap that cost v3–v8 (don't repeat it)

Builds v3–v8 used `((c - 0xBF) + 0x10) ^ 0x9E` [sub, add, xor]. That arrangement is bijective, so `decode(encode(x)) == x` passed trivially — **and that round-trip is exactly why the bug hid for six builds.** The ECU decrypted v8's payload to garbage, the CRC chain failed, and `checkProgrammingDependencies` returned NRC `0x72`.

**Rule: never validate a cipher with a `decode(encode(x)) == x` round-trip.** Validate it one of two ways:
1. Decode a *genuine encrypted file* to known plaintext (`encode_eps.crack_cipher` against the part-number string), or
2. Decode with the disassembled on-ECU decryptor and CRC-check the result (what the V9 builder does).

The `&` header always carries the **raw** key bytes `BF109E` (ASCII hex) regardless of the host encode arithmetic — the ECU reads those raw bytes into k0/k1/k2.

---

## 3. The x31 container & TVA headers

```
0x00   31 0D 0A                          magic '1\r\n'
0x03   6 tag-delimited ASCII headers, each: [tag 0D 0A] val 0D 0A ... [tag 0D 0A]
         #  -> [\x00]                     sentinel        (copy from template)
         ?  -> [b'A1']                    container marker (copy from template)
         /  -> [b'39990-TVA-A110', b'39990-TVA-A160']   supported part numbers
         !  -> [b'001100121020', b'001100121020']       Group A family marker (mirrored)
         &  -> [b'BF109E']                cipher key, ASCII hex (copy from template)
         %  -> [b'30']                    CAN sig byte -> 0x18DA30F1 (comma/red-panda)
varies <ciphered payload chunks>          N x 130 bytes: [addr_hi:u8][addr_mid:u8][data:128B]
                                          addr = (hi<<12)|(mid<<4); chunks ascending
+chunks file_checksum:u32 LE              sum(all preceding bytes) & 0xFFFFFFFF
```

`make_tva_headers()` copies `#`, `?`, `&` verbatim from the T2F template and substitutes `/`, `!`, `%`. Header facts established and confirmed:

- **`/` (part numbers):** two entries `A110` + `A160` (both strings exist in `code.bin` at `0x9011`/`0x9020`); matches the V850-family two-version convention.
- **`!` (`001100121020`, "Group A"):** a **vestigial family marker — NOT the SA secret on V850.** The ECU ignores it during SecurityAccess (see §6). Mirrored to two entries to match `/` arity.
- **`%` (CAN sig byte):** `30` → `0x18DA30F1`. **This is the comma/red-panda target** (`opendbc` `Ecu.eps, 0x18da30f1`, bus 1). The stock dealer/HDS tool uses `80` → `0x18DA80F1`; the ECU's RX filter is the broad `0x18DAxxF1` family so both reach it. **For the comma flash path, build with `%`=30.**
- **Chunks are 128 B-aligned;** block lengths are always multiples of 128. The MCU's 4 KB *erase* unit is separate from the `.rwd`'s 128 B chunk granularity.
- **File checksum:** last 4 bytes = `sum(everything before) & 0xFFFFFFFF`, little-endian. (Verified across siblings; identical for x31 and x5a.)

---

## 4. The flash window — `[0x13000, 0x100000)`

The bootloader hard-codes the **expected programmable window** in a table at `0x937C`: `start = 0x13000, length = 0xED000` (→ end `0x100000`). `checkProgrammingDependencies` (`0x937C` verdict worker) rejects any other start.

- The whole window is sent as **one contiguous block**, erased gaps carried verbatim as `0xFF` — the firmware erases 4 KB pages across the window then writes. A wrong start (v7 tried `0x14000`, `0x10000`, etc.) gets NRC `0x31` at `request_download`. `0x13000` is the only accepted start.
- `0x13000` begins **just after** the A110/A160 identity block at `0x12FF0..0x13000`, so this window does **not** rewrite the identity strings. The region below `0x13000` (reset vectors, early code, SA-key constants at `0x92C0`, sw-version, part numbers) is **never transmitted** and stays stock on the ECU — which is correct, because those are not part of the application reflash.

| Below the floor (NOT flashed) | Address | Stays stock |
|---|---|---|
| Reset vectors + early code | `0x0`+ | yes |
| `0x8000` boot-invoked routine | `0x08000` | yes |
| sw-version `DV850T05xxxxxV104` | `0x05AF8` | yes |
| SA-key Group C constants | `0x092C0` | yes — SA handshake unaffected |
| Part numbers `A110`/`A160` | `0x9011`/`0x9020` | yes |

---

## 5. Integrity: the CRC-32 scheme you must satisfy

`checkProgrammingDependencies` (UDS RoutineControl `0x31 01 FF01`) verifies a **backward linked list of CRC-32 blocks** over the programmed window, plus one big "main" block. CRC = standard CRC-32 (`zlib.crc32`; the MCU's DCRA "Ethernet CRC" unit, polynomial `0x04C11DB7`, init/xorout `0xFFFFFFFF`). **Any single block mismatch → NRC `0x72`.**

### The walk (replayed exactly by `verify_bootloader_crc.walk`)

- Region end `E = 0x13000 + 0xED000 = 0x100000`.
- Each block's trailer is `{start_page:u16, num_pages:u16}` at `[E-8]/[E-6]`; page `p` → byte addr `p<<12`; block length = `(num_pages<<12) - 4`; stored CRC at `block_start + length`.
- The next (lower) block's page fields live 8/6 bytes below the current block's start (a `[next_page:u16 LE][own_page:u16 LE]` chain pointer also lives at each protected block's `+0xFF6`).
- **Bridge:** when a block start hits `0xC6000`, jump to the **main block** `[0x13000, 0xC4FFC)` (length `0xB1FFC`, CRC at `0xC4FFC`).
- Terminate when a block start == region start `0x13000`.

For stock `code.bin` this is **49 blocks** (calibration band `0xFD000`→`0xC6000` as ~4 KB blocks, then the bridge to the one main block). All 49 verify.

The long-mysterious top word `0xFCB8212C @ 0xFFFFC` is just `zlib.crc32(code.bin[0xFD000:0xFFFFC])` (a non-4 KB, `0x2FFC`-byte block). It IS runtime-checked, contrary to an earlier "offline tool metadata" guess.

### Per-block trailers (the patch rule)

48 individual 4 KB blocks store `crc32(block[0:0xFFC])` at offset `+0xFFC`:

```
Protected:   0x00000, 0x08000, 0xC5000, 0xC6000, 0xCD000..0xF8000 (44 blocks)
Unprotected: 0xC4000, 0xC7000..0xCC000, 0xF9000..0xFD000 (where programmed)
```

**To patch a value inside a protected block, recompute its trailer:**

```python
import zlib
block[0xFFC:0x1000] = zlib.crc32(block[:0xFFC]).to_bytes(4, "little")
```

For stock recovery the trailers are already correct in `code.bin` — just pass them through.

---

## 6. SecurityAccess (the flash gate — distinct from the payload cipher)

Two different crypto primitives exist; don't confuse them:
- The **payload cipher** (§2) unwraps the `.rwd` into bytes.
- The **SA seed→key** handshake gates whether the ECU enters programming mode. It never touches the payload.

**Verified V850 SA algorithm** (handler `0x00AAB4`; the universal Honda formula, only the constants differ):

```
seed16 = received_seed & 0xFFFF
key16  = ((seed16 + 0x0211) & 0xFFFF) XOR ((seed16 * 0x0212) mod 0x1220)
```

- Constants are **firmware-embedded at `0x92C0..0x92C5`** (`k0=0x0211, k1=0x0212, k2=0x1220` — "Group C"), **not** in the `!` header.
- Wire format: 2-byte big-endian seed in (`0x27 01`), 2-byte big-endian key out (`0x27 02`).
- Implementation: `flashing-2020accord/tva_sa_key.py` (`calculate_tva_session_key`), with hand-checkable test vectors in `_selfcheck()`.
- The `0x2E F101` (FLASH_DECRYPTION_KEY) write sends the raw `&` bytes `BF 10 9E`, which arm the on-ECU decryptor (§2).

---

## 7. End-to-end: building a MODIFIED firmware `.rwd`

The stock build is the special case where you change nothing. For a real modification (torque table, clamp, gain — see `TORQUE_PATH_AND_TABLE.md` for what lives where):

1. **Start from the decrypted `../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin`** (the plaintext 1 MB image).
2. **Edit the bytes you want** in your target address(es). Confirm the address is inside the flashed window `[0x13000, 0x100000)` — anything below `0x13000` is not transmitted and cannot be changed this way.
3. **Recompute the CRC-32 trailer** (§5) of every 4 KB protected block you touched.
   - Caveat — the `+0xFF6` chain pointer: many calibration blocks have near-clone neighbors linked through the 48-block CRC chain. Its runtime role is **not fully traced.** Safer default until it is: **patch only your target block(s)** and observe behavior, rather than blanket-mirroring across chain neighbors.
4. **Hard ceiling — control params are NOT in this dump.** The values the live steering/motor loop actually reads (`0xFD8C8–0xFE189` control thresholds/gains/limits, `0xFE000+` motor params) are `0xFF` in `code.bin` — they live in the `0xF8000+` partition our dump doesn't capture, so you cannot change them from `code.bin` alone. (⚠ 2026-05-25: an earlier version said "`0xFF` in both `code.bin` and `data.bin`" — the `data.bin` half is invalid: `data.bin` is 32 KB at `0x02000000` and never covered `0xFxxxx`. See the CORRECTION at the top of `TORQUE_PATH_AND_TABLE.md` §0. The ceiling still holds on `code.bin` alone.) The calibration tables you *can* edit are the `0xC4000–0xFD0B8` band (§ `TORQUE_PATH_AND_TABLE.md`). To touch the live control params you'd need a raw dump of `0xF8000–0xFFFFF` or a stock TVA `.rwd` covering them.
5. **Re-encipher and wrap** using the V9b cipher + TVA headers — point `analysis-2020accord/old_tools/build_stock_tva_v9.py` at the modified image under `../accord-firmware/analysis-2020accord/` (it carves the `[0x13000,0x100000)` window automatically) and keeps output under `../accord-firmware/flashing-2020accord/rwd/`.
6. **Self-validate (mandatory gate):** decode the built payload with the on-ECU cipher, splice into a 1 MB image at `0x13000`, run `verify_bootloader_crc.walk`. **Require 49/49 PASS.** The builder does this and refuses to write on failure. A pass means the image will satisfy `0xFF01` *provided the ECU decrypts it correctly* — and the V9b cipher is now confirmed, so a pass is a true green light.

---

## 8. Flashing (operator-gated)

Flasher: `flashing-2020accord/eps-update-tva.py` (V850/x31-aware fork of sunnypilot's `eps-update.py`).

```
# Dry run (default — no mutation; runs through the SA handshake and stops):
python flashing-2020accord/eps-update-tva.py --bus 1 ../accord-firmware/flashing-2020accord/rwd/39990-TVA-A160-...-v9b-0x13000-0x100000.rwd

# Real flash (DANGEROUS; prints a banner, requires typing FLASH):
python flashing-2020accord/eps-update-tva.py --bus 1 --danger ../accord-firmware/flashing-2020accord/rwd/...-v9b-0x13000-0x100000.rwd
```

The script auto-detects x31, routes SA through `tva_sa_key.py`, resolves the CAN address from the `%` header, and issues one `request_download` per block.

**Non-negotiable safety preamble (kit `CLAUDE.md`):**
1. **Never send any CAN message — including UDS reads — without explicit operator confirmation of the exact payload.**
2. **Never run the flasher without the operator naming the firmware file AND the bus**; repeat the name back before proceeding.
3. **Kill openpilot/pandad before any flash** (`tmux kill-server` on a comma device). Otherwise every dash error light illuminates (recoverable but alarming).
4. **Firmware is car/year/revision specific.** Confirm the part number. Never cross-flash.
5. **Do not interrupt a flash once started** — a partial write can brick the EPS ECU.

A clean dry-run prints `SA handshake succeeded` — that alone validates the SA algorithm/constants against the real ECU with zero flash risk.

---

## 9. Quick reference

| Item | Value |
|---|---|
| Part number | `39990-TVA-A160` (siblings `A110`, `A340`) |
| MCU | µPD70F3508, V850E2/Px4, little-endian, 1 MB flash |
| Container | x31 (`31 0D 0A`) |
| Cipher (decode) | `((c ^ 0xBF) ^ 0x10) - 0x9E` — keys `BF 10 9E`, ops xor,xor,sub **[CONFIRMED by V9b flash]** |
| `&` header (raw key) | `BF109E` |
| Flash window | `[0x13000, 0x100000)`, length `0xED000`, single contiguous block |
| CRC | standard CRC-32 (`zlib.crc32`); per-block trailer at `+0xFFC`; linked-list walk via `0xFF01`; 49 blocks for stock |
| SA algorithm | `((seed&0xFFFF)+0x0211) XOR ((seed&0xFFFF)*0x0212 mod 0x1220)` |
| SA constants | `0x92C0..0x92C5` (Group C `0211 0212 1220`); NOT the `!` header |
| CAN address | `0x18DA30F1` (comma, `%`=30); `0x18DA80F1` (HDS, `%`=80) |
| Builder / validator / flasher | `analysis-2020accord/old_tools/build_stock_tva_v9.py` / `analysis-2020accord/verify_bootloader_crc.py` / `flashing-2020accord/eps-update-tva.py` |
| Working artifact | `../accord-firmware/flashing-2020accord/rwd/39990-TVA-A160-RECONSTRUCTED-v9b-0x13000-0x100000.rwd` |
