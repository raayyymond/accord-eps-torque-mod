---
name: reference-tva-cipher-operand-order
description: "CONFIRMED: the V850 TVA on-ECU flash decryptor (FUN_0xB35E) is ((c^0xBF)^0x10)-0x9E for written key BF109E [xor,xor,sub] — V9b flashed successfully 2026-05-24. build_stock_tva v3-v8 used the wrong arrangement ((c-0xBF)+0x10)^0x9E [sub,add,xor] -> garbage -> CRC fail -> NRC 0x72. Round-trip self-checks can't catch a wrong cipher."
metadata:
  node_type: memory
  type: reference
  source: claude
---

**Root-caused 2026-05-24; CONFIRMED by successful V9b flash same day.** Full writeup now: `analysis-2020accord/notes/HOW_TO_BUILD_ACCORD_TVA_RWD.md` §2 (was `CIPHER_KEY_ORDER_BUG.md`, since distilled). This was the cause of the V8 `0xFF01` → NRC `0x72` failure (see [[reference-tva-bootloader-crc-scheme]] for the check it tripped).

## The ciphers (all use `&`-key bytes BF 10 9E)

| | decode = plaintext(`c`) | ops / key order | provenance | verdict |
|---|---|---|---|---|
| **wrong (v3–v8)** | `((c-0xBF)+0x10)^0x9E` | sub,add,xor / BF,10,9E | "family-invariant" assumption, never validated vs plaintext | DISPROVEN; flashed → 0x72 |
| **V9b — CONFIRMED** | `((c^0xBF)^0x10)-0x9E` = `(c^0xAF)-0x9E` | xor,xor,sub / BF,10,9E | **disassembled resident decryptor `FUN_0xB35E`**; **flashed successfully 2026-05-24** | CORRECT — this is the ECU's decoder |
| **V9a — retired** | `((c-0x9E)+0xBF)^0x10` = `(c+0x21)^0x10` | sub,add,xor / 9E,BF,10 | was the fallback (cracked from genuine `39990-T2F-A210.rwd`) | moot — V9b's success settled it |

They are genuinely different substitutions (`c=0`: wrong→…, V9b→0x11, V9a→0x31). V9b is the one the ECU uses — proven empirically, not just by strongest-evidence.

## Evidence

- `FUN_0xB35E` @`code.bin` 0xb3ac–0xb3c4 (radare2 v850): loads k0=`[0xFEDF20BB]`=0xBF, `xor` cipher; k1=`[0xFEDF20BC]`=0x10, `xor`; k2=`[0xFEDF20BD]`=0x9E, `sub`. Key bytes written there by the `0x2E F101` handler `FUN_0xCB20`; decrypt gated on bit 2 of `0xFEDF20AA` (set by that key write). Invoked by TransferData handler `FUN_0xD0C4`.
- `encode_eps.crack_cipher` on the genuine T2F file, anchored on `39990-T2F-A210`, returns `((i-0x9e)+0xbf)^0x10` and decodes coherent ASCII. V8's table does NOT reveal the T2F part number.
- Software repro: encode `code.bin[0x13000:0x100000]` with V8's table, decode with the real ECU decoder → bytes ≠ code.bin, trailer decodes to a bogus page pointer, CRC chain destroyed → guaranteed `0xFF01` fail.
- Caveat: `FUN_0xB35E` calls `FUN_0xB4C8` every 16 bytes; that's a `jr` into RAM (`0xFEDF4316`, absent kernel). If it mutates the key, the cipher isn't a static substitution — but the T2F file decodes with a static table, so static is overwhelmingly likely; V9a is kept as the fallback for the residual case.

## How to apply

- **NEVER trust a `decode(encode(x))==x` round-trip as cipher validation** — it's trivially true for any bijective table and is exactly what hid this bug for v3–v8. Validate by decoding a genuine encrypted file to known plaintext (`crack_cipher` on the part number), OR by decoding with the disassembled on-ECU decryptor and CRC-checking ([[reference-tva-bootloader-crc-scheme]]).
- The written `&`-key stays raw `BF109E` for all variants (the ECU reads those into k0/k1/k2); only the host *encode* arithmetic changes.
- Flash order if/when authorized: **V9b first** (it is the literal resident decryptor), V9a only if V9b fails `0xFF01` the same way.

## Cross-refs

- [[reference-tva-bootloader-crc-scheme]] — the CRC check this cipher must satisfy
- [[project-2020accord-v9-cipher-fix-2026-05-24]] — current branch state / candidates built
- [[feedback-three-senses-of-rebuilt]] — sibling "false-confidence from self-consistent round-trip" trap
- [[reference-eps-tool-canonical-cipher]] — the analogous SH-2A cipher-selection trap (rwd-xray non-canonical key)
