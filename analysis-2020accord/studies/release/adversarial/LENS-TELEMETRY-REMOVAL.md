# LENS: telemetry removal (C1-C3) for release V300 -- 2026-10-15

**VERDICT: PASS_WITH_DEFECTS** (no do-not-flash finding; 3 defects to close in the release builder and notes).

**What a FAIL would have looked like (written before running):** (a) the angle cave or a lane edit branches into, reads, or depends on the telemetry cave or its cells; (b) the telemetry cave clobbers a register that is live at the hook's return; (c) a stock reader or writer expects a value the cave supplied; (d) the stock bytes at the three windows are not the original control flow; (e) the CRC/trailer story is unsatisfiable. None occurred.

Images: stock `stock_fw_dump/code.bin` (the open Ghidra program; `list_open_programs` -> code.bin, V850:LE, 1,048,576 B); `_v299_...A16B_plain_image.bin` (Python only). No V300 image exists yet, so I verified the inputs of the removal (stock bytes, V299 bytes), not a built release. Re-run section 3 against the built image.
Hand decoder: `_scratch/lens_tel/dec850_tel.py` (a Python-fed listing of V299 bytes, since Ghidra cannot disassemble bytes that are not in its program). Validated against Ghidra on stock at 0x55BE8-0x55C20 and fixed twice (register names; ld.bu vs jarl collision on hw2 bit 0).

## 1. The telemetry, fully decoded (EVIDENCE: V299 bytes via decoder; stock side via Ghidra decompile of FUN_00055a98 and FUN_00055d80)

**C1 hook** `0x55C0E`: V299 `86ff26ef` = `jarl 0xC4B34, lp`; stock `2436e8ea` = `movea -0x1518, gp, r6` (r6 = &0x14A buffer, arg 1 of the checksum call). Next stock instructions: `0x55C12 mov 8,r7`, `0x55C14 movea 0x14a,r0,r8`, `0x55C18 jarl 0x57B24,lp` (FUN_00057b24 = Honda counter/checksum nibble; decompiled, read-only on the buffer). The hook sits between `FUN_0001fa42()` and `FUN_0001fa72()` (critical section) inside FUN_00055a98, the 0x14A builder.

**C2 cave** `0xC4B34..0xC4BD7` (164 B), full listing:

| addr | effect |
|---|---|
| 4B34-4B5E | r7 = [abs(gp-0x6ada) > abs(gp-0x6b38)] << 4; gp-0x1514 = (gp-0x1514 & 0xBF) or r7 : **b4 bit 6** |
| 4B62-4B8C | r7 = 2*[abs(gp-0x6ada) > abs(gp-0x6b94)] << 4; mask 0xDF : **b4 bit 5** |
| 4B90-4BBC | r7 = 8*[gp-0x6b4c<0] + [gp-0x6ada<0], << 4, +8 if (s32)gp-0x3680<0; mask 0x67 : **b4 bits 3,4,7** |
| 4BC0-4BCE | r7 = 3<<6; gp-0x1511 = (gp-0x1511 & 0x3F) or 0xC0 : **b7 bits 6,7 = constant 11** |
| 4BD2-4BD6 | `movea -0x1518,gp,r6` (the displaced stock instruction, replayed); `jmp [lp]` |

- **RAM read (5):** gp-0x6ada, gp-0x6b38 (lane torque), gp-0x6b94, gp-0x6b4c, gp-0x3680 (ld.w). The cave changes none of them.
- **RAM written (2 bytes, no others):** gp-0x1514 (0x14A byte 4) and gp-0x1511 (0x14A byte 7). `gp-0x1518` is **not written** by the cave. It appears only as the address operand of the replayed movea. No persistent cave state exists.
- **Registers clobbered:** r6, r7, lp. All dead at the return: `0x55C12` overwrites r7, `0x55C14` overwrites r8, `0x55C18` is a `jarl ...,lp`, and r6 is re-set by the replayed movea.
- **CAN bytes altered:** 0x14A byte 4 bits 3-7 (as briefed) **and byte 7 bits 6-7 forced to 11. The census names only byte 4.** Stock never writes any of these seven bits: byte 4 masks are `0xFB/0xFD/0xFE` plus fault `clr1 1/0` at 0x55B20/0x55B30; byte 7 masks are `0xCF` and `0xF0`; the word RMW at 0x2193E uses `0xFF0000FF`, preserving bytes 4 and 7. The opendbc STEERING_SENSORS definition (`honda_bosch_radarless_generated.dbc`) uses only byte 4 bits 0-2 and byte 7 counter (61|2) and checksum (59|4). The checksum is computed after the hook, so it always covers whatever the bits hold.
- **C3 tap** `0x55DF2..0x55E11` is in FUN_00055d80, the **0x1AB / 427 MOTOR_TORQUE** builder (call `FUN_00057b24(gp-0x13cc,3,0x1ab)`). Stock `ld.h -0x6c18[gp],r6` at 0x55DF0 (its displacement halfword `e893` sits at 0x55DF2) becomes `c894` = `ld.h -0x6b38[gp]` (lane torque), followed by `mov r6,r9` and a sign-magnitude repack. V299 clobbers r9 and replaces stock's `ori 0xFFFF,r0,r7 / jarl 0x49A78 / andi 0xFFFF,r10,r6 / mul 5` sequence. The field is sign<<9 or abs(T)>>3, so 0x1AB carries the angle lane's torque. Stock content is Honda's motor torque: FUN_00049a5a/78/90 clamp of gp-0x6c18 times 5 >> 3 into 0..0x3FF.

## 2. The angle cave and in-place edits reference none of it (EVIDENCE: two methods)

| check | method | result |
|---|---|---|
| jarl/jr targets into 0xC4B34..0xC4BD7 in V299 (Format-V with ld.bu collision filter) | Python, all even offsets | **exactly one**: `0x55C0E`, the hook |
| 32-bit words pointing into the cave | Python | 0 |
| low-16 halfword 0x4B34-0x4BD7 | Python, ~270 raw hits | all adjudicated noise: immediates (`4b80` family), a `cmov` tail `4b36` at 0xC4CA2 inside the angle cave (`ed4f 364b`), ASCII; none behind a movhi 0x000C |
| angle cave 0xC4C00..0xC4D03 control transfers | decoder | `jr 0x2A164`, `jr 0x29D7E` (x2), `jmp [r6]` (link from `jarl 0xC4C00, r6` at 0x29D76), table at 0xC4CDA; nothing in 0xC4B34-BD7 |
| any gp-0x1518..gp-0x1511 access in V299 outside stock sites and the telemetry cave | Python, reg1==gp, all op forms | stock 15 hits; V299 23 = the same stock sites + 9 cave sites; none in the angle cave or lane edits (0x28F4E, 0x29A50-56, 0x29D6A-79, 0x29EE0-3, 0x2A1F0) |
| other address forms | Ghidra `get_xrefs_to(0xFEDF6AEC)`: 0x55B20 and 0x55B30 only, both stock FUN_00055a98; `get_xrefs_to(0xFEDF6AEF)`: none; Python halfword scan of stock | adjudicated: 0xB728C = CAN-TX buffer pointer table (data); 0xCC184/0xCC1E4 = flash pointer table (0x000D6AEC), not RAM; 0x93E8-93F0 = data |

The angle cave returns through r6, not lp, so the hook's lp use is independent. No stock reader or writer depends on a value the cave supplies. The only stock consumer of the written bits is the CAN transmit of the buffer.

**Residual, not closed:**
1. A register-indirect write to the buffer was not excluded by operand scans. The kit's earlier Segment D pointer-array census found the buffer belongs to table index 10 only (BELIEF, inherited).
2. Power-on value of the 7 bits. 0xFEDF6AE8 lies above the end of the `.data` copy (RAM 0xFEDF5A68), so it is not initialised from flash. I did not locate a zero-fill (boot code 0x146E0-0x14850 shows the `.data` copy and a 0xEBEBEBEB stack fill only). That they read 0 on a stock car is BELIEF, supported by the V31-era use of these bits as clean spares. Cheap close: one stock or pre-V31 route's 0x14A byte 4 and byte 7.

## 3. Stock bytes and restoration (EVIDENCE: Python equality, Ghidra decompile)

- Stock `0x55C0E..0x55C11` = `2436e8ea` = `movea -0x1518,gp,r6` (Ghidra disassemble_bytes dry_run over 0x55DD0 and the decompile of FUN_00055a98). Restoring it removes the detour and leaves r6 = &buffer for the checksum call.
- Stock `0x55DF2..0x55E11` (32 B) starts on the displacement halfword of the instruction at 0x55DF0. Restore it as raw bytes from the dump. The full stock sequence is in section 1; the owning function is the 0x1AB builder.
- Hypothetical release R = V299 with C1 and C3 from stock and `0xC4B34..0xC4BD7` = 0xFF: windows equal stock byte for byte (Python True); cave region equals stock (all 0xFF).
- V299 vs stock outside the C windows is owned by the D and B lenses; not examined here.
- **CRC:** main block `[0x13000,0xC4FFC)` covers all three windows. The trailer is zlib crc32, little-endian: V299's `953bdd70` reproduces (crc32 0x70DD3B95). The release must recompute it. For orientation only, V299 minus telemetry alone would carry `af9e346e`; the real release differs because of the D edits.

## 4. Consequence for the wire and the decoders

- **Still identifies the firmware:** UDS F181 (V299 `39990-TVA,A16B`, near 0x1310D). It is not visible passively. The fork keys the angle interface on the A16 family: a release F181 outside it gives `EPS_ANGLE_LOOP_FW_MISSING` and the fork refuses to steer (carstate.py, found by grep; not run).
- **0x14A:** bytes 0-3, 5-6, byte 4 bits 0-2 and the byte 7 counter and checksum stay Honda. Byte 4 bits 3-7 and byte 7 bits 6-7 return to stock (BELIEF: 0). No dbc signal or fork code reads them.
- **0x1AB:** reverts to Honda MOTOR_TORQUE. The fork's torque bar (`update_accord_eps_torque` -> `torque_bar.py`) reads 0x1AB only for the on-screen bar, so it will show Honda's stock value read as lane counts: wrong or near 0, cosmetic. The Honda checksum stays valid, so it is not flagged stale.

**Kit readers that go stock-blind on release routes:**

| reader | reads | status on release routes |
|---|---|---|
| `rlog-tools/studies/angle_loop/drive_read_v299.py` | 0x1AB tap in F1 (tap vs replays), F7/F7b/F9, F8 (bar == -8*tap), F6 via tap | blind; the 0x14A b4 bits 0-2 check (R8) stays valid |
| `angle_loop_drive_read.py`, `angle_loop_controls.py`, `high_angle_hunt.py`, `high_angle_probe.py`, `drive_read_fastlane.py` (same folder) | tap T from 0x1AB | blind |
| `rlog-tools/decode/extract_eps_telemetry.py` and about 35 `extract_r*.py`, `rlog-tools/probe/decode_v*_probe.py`, `rlog-tools/score/score_*.py` | 0x14A b4 bits 3-7, b7 bits 6-7 (older rung meanings, not V299's constant 11) | blind; they read 0 by design |

## Defects (all closable without redesign)
1. **Census gap:** C2 also writes 0x14A byte 7 bits 6-7 (constant 11, 0xC4BC0-0xC4BCE). Add it to the C table and the "wire returns to stock" claim.
2. **CRC trailer** must be recomputed over `[0x13000,0xC4FFC)`; add an assertion that trailer == crc32 of the final block.
3. **Boot value of the 7 freed bits is BELIEF.** One stock route closes it. Build notes must also state the release F181 stays A16-family.
