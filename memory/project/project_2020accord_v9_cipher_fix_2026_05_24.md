---
name: project-2020accord-v9-cipher-fix-2026-05-24
description: "2020 Accord TVA branch: SOLVED. V8 flash failed at checkProgrammingDependencies (NRC 0x72) due to wrong flash cipher; V9b (resident-decryptor cipher ((c^0xBF)^0x10)-0x9E) was rebuilt and FLASHED SUCCESSFULLY on the operator's car 2026-05-24. V9b cipher + window 0x13000-0x100000 + CRC walk = the confirmed recipe. V9a retired."
metadata:
  node_type: memory
  type: project
  source: claude
---

**Branch `2020accord`, state as of 2026-05-24 — RESOLVED.** A valid stock-recovery `.rwd` for the 2020 Accord Touring (`39990-TVA-A160`) has been reconstructed and flashed. Supersedes the "next step = rayy's dry-run" framing in [[project-2020accord-sa-key-solved-2026-05-23]] (done) and the "not yet flashed" framing of the earlier draft of this same memory.

## Outcome

**`39990-TVA-A160-RECONSTRUCTED-v9b-0x13000-0x100000.rwd` flashed successfully** (bus 1, comma EPS CAN `0x18DA30F1`, `--danger`). The full UDS sequence completed and `checkProgrammingDependencies` (`0x31 01 FF01`) returned positive. This **confirms** the V9b cipher hypothesis empirically and validates the whole V9b generation process as the recipe of record.

## The fix (now confirmed)

- **Cipher:** decode = `((c ^ 0xBF) ^ 0x10) - 0x9E` [xor,xor,sub], keys `BF 10 9E` — the literal resident decryptor `FUN_0xB35E`. See [[reference-tva-cipher-operand-order]].
- **Window:** single contiguous `[0x13000,0x100000)` (the bootloader's hard-coded programmable window at table `0x937C`).
- **Written `&`-key:** raw `BF109E` to DID `0x2E F101`.
- **Pre-flash gate:** decode-as-ECU == `code.bin` AND 49/49 CRC blocks PASS in `lib/verify_bootloader_crc.py`. See [[reference-tva-bootloader-crc-scheme]].

### What was wrong before
V8 (and all of v3–v7) enciphered with `((c-0xBF)+0x10)^0x9E` [sub,add,xor] → ECU decrypted to garbage → per-block CRC-32 chain failed → NRC `0x72`. The build's `decode(encode(x))==x` round-trip can't catch a wrong cipher (trivially true for any bijection); that hid the bug for six builds.

## State / artifacts

- Builder: `analysis-2020accord/archive/old_tools/build_stock_tva_v9.py` (now self-contained — the v3–v8 builders it used to import from were removed). Flasher: `flashing-2020accord/eps-update-tva.py`.
- **V9a is retired.** It was the fallback (genuine-T2F-file cipher); the successful V9b flash proves the resident decryptor is the ECU's real decoder, so the fallback is moot. All non-V9b `.rwd`s and the v3–v8 build scripts have been removed from `analysis-2020accord/` and `flashing-2020accord/`.
- Full recipe writeup (replaces the old per-finding docs): `analysis-2020accord/notes/HOW_TO_BUILD_ACCORD_TVA_RWD.md`. Torque path: `analysis-2020accord/notes/TORQUE_PATH_AND_TABLE.md`.
- NEXT for any *modified* firmware: edit `code.bin` inside `[0x13000,0x100000)`, recompute touched-block CRC trailers, re-run the CRC walk, re-encode with the V9b cipher. Note the hard ceiling: live control params (`0xFD8C8+`/`0xFE000+`) are absent from our dump.

## Cross-refs

- [[reference-tva-cipher-operand-order]] / [[reference-tva-bootloader-crc-scheme]] — the two durable findings, now flash-confirmed
- [[project-2020accord-sa-key-solved-2026-05-23]] — prior state (SA solved)
- [[feedback-operator-lived-experience-overrides-analyst-recs]] — operator's road feel is the final arbiter on any tune
