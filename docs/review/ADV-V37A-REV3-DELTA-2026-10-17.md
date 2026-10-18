# ADV-V37A-REV3-DELTA (adv37a-rev3) - 2026-10-17

VERDICT: PASS_WITH_DEFECTS. No pre-written FAIL condition fired. Image sha256 e33a97ee...805e and rwd sha256 af57a236...0ee8 exactly as briefed. Scripts: _scratch/v37a/rev3/{chk.py,lane.py}.
EVIDENCE = Python full-file diff / CRC walk / raw LE scans (positive-controlled) / Ghidra decompile of FUN_00028ea6 (stock code.bin program; code bytes identical to rev 3, see 1). BELIEF is marked.

## 1. Bytes / CRC [EVIDENCE]
- rev3 vs V37 over [0x13000,0x100000): 301 bytes, ZERO unexplained. Explained set = Y cells of the 28 records (pointer table 0xC9A88, 28 x u32, every header n=10), 0xC62E6-7, trailers 0xC6FFC, 0xE4FFC..0xE8FFC.
- rev3 vs rev2: 330 bytes, ZERO outside that same set (values differ only).
- Cells: 0xC62E6 = 15360 (V37/stock 7680, rev2 42865); 0xC646C = 1782; 0xC61B2 = 0xC61B4 = 1024.
- All six trailers recomputed with zlib.crc32 over [base, base+0xFFC): match (0xC6FFC 4689b948, E4FFC 57b9edbd, E5FFC 3f8c3c6d, E6FFC 5ea086e1, E7FFC 2d403221, E8FFC aa88e588).
- Kit walk() on the image: 49/49 PASS. walk_all_blocks(): 50/50 PASS.
- rwd decoded (parse_x31, cipher 0xBF,0x10,0x9E xor,xor,sub), one block 0x13000 len 0xED000, placed in 0xFF 1 MB: 0 bytes differ from the image; walk 49/49, all 50/50 PASS.
- Hashes: image e33a97ee2a9cd8be2e4a8080c121fec74776588c46d10f35a0ae34458487805e; rwd af57a2365a1781d58410039ed6acd7303d61989253be6f13bb44ce859c040ee8.
- Exactly ONE non-superseded V37A rwd on disk (REV3). REV1 and REV2 files carry the SUPERSEDED-DO-NOT-FLASH- prefix.

## 2. The map [EVIDENCE]
- All 28 records: X untouched, Y[0] = 0, monotone, and Y == floor(Fraction(2*Ytop*X,240)+1/2) from STOCK, byte for byte (two formulas agree). Stock tops are 172, 180, 188.
- Slot 7 (0xE502C): stock 0,24,42,50,62,100,126,154,166,172 -> rev3 0,17,29,34,46,92,138,183,229,344 (matches the brief).
- Integer LERP (truncating divide, flat above X[9]) idx 0..240: max deviation from 344*idx/240 = 1.367 at idx 137 (build claims <= 1.37, fail line 2.0). Values: idx 12 -> 17, 120 -> 171, 238 -> 341, 240 -> 344.
- DEFECT (LOW, doc): reference vs stock slot 7 is BELOW stock for idx 1..75, EQUAL at 0, 76, 77, ABOVE from idx 78. The brief's "crossing ~ idx 48" is wrong (at idx 48 the line is 69, stock 81). State the right crossing on the page.

## 3. Clamp 15360 [EVIDENCE]
- sp:fb ratio 15360/(32*344) = 1.39535 = 7680/(32*172) = 1.39535, identical.
- Stock clamp (7680) would bind when 32*sp > 7680, i.e. sp > 240; on the rev3 line first at idx 169 (sp 241).
- 15360 > 32*344 = 11008, so E = 32*sp - fb reaches 11008-15360 = -4352 at the top: E can change sign.
- 0xC62E6 readers: raw tp scan (control: 0xC646C found at 0x2A1EE) gives exactly 3 reads 0x28F96/0x28F9C/0x28FB8, all hw2 odd (ld.hu); identical bytes to stock. 15360 < 32767 anyway.

## 4. Arithmetic [EVIDENCE via the kit golden model lkas_rate_pid_surface fed from each image's own cells; BELIEF that it is faithful, it is not an independent mirror]
- E is 32-bit in the decompile (FUN_00028ea6: `iVar31*0x20 - uVar35`, then >>5 against 0xC62E4). Max |E| anywhere on the surface = 11008; absolute worst case (fb = -15360) 26368, no int16 or int32 overflow. P = E*Kp>>8 <= 26368*696 = 18.4e6 < 2^31. Bounds are smaller than rev 2's (32*960 + 42865).
- Rail: P first railed at idx 128 (E 5856, kp 679, P = 15360), T = 820. kp 681 at 129, 696 from 160. Max T on the surface 820 (golden-model T_ceil 835 is an upper bound; rev 2's measured max with D on top was 828; lane tail unchanged, BELIEF carries over).
- Torque table (stock / V37 / rev2 / rev3): idx 12: 23/46/94/33; 32: 76/153/317/114; 63: 160/321/820/295; 100: 261/523/820/580; 120: 324/649/820/755; 127: 345/690/820/816; 128+: 349../698../820/820; 240: 399/799/820/820.

## 5. Downstream [EVIDENCE for surface; BELIEF where marked]
- Lane vs V37: rev3 BELOW V37 for idx <= 75, equal-ish at 76-77, ABOVE from idx 78 (not ~48), rail 820 from 128 vs V37 799 only at 240. Lane vs stock: rev3 >= stock at every idx (gain 2x beats the lower reference). Lane vs rev2: rev3 <= rev2 everywhere (rev2 railed from idx 63).
- Ceiling 820 is identical to rev 2, so rev 2's downstream checks stand: lane cells 0xC61B2/B4 1024 never bind, soft-EME floors 4096 unchanged, gp-0x682f thresholds 0xFF/0xFFFF unchanged. Rev 2's (799,828] threshold search found none; nothing in that window changed (only the map and 0xC62E6 differ, both verified above). No newly crossed lane-derived threshold: BELIEF-level for register-indirect paths, same caveat as rev 2.
- Pointer-table consumers: raw scan of movea imm 0x9A88 finds 0x29CFC (inside FUN_00028ea6, live), 0x2ABF2 (in the 0x2A30E-0x2B421 uncalled twin island per memory, not re-verified here), 0x64C96 (a jarl displacement byte, not a movea, false positive). LIM record 0xE51A8 (flat 0x3C00 = 15360) is not among the 28 and is byte-unchanged.
- Dwell exposure: rev3 spends far less time at 820 than rev 2 (idx 128+ vs 63+), same ceiling.

## Defects
1. LOW (doc/page): crossing is idx 76-78, not ~48, for both the reference-vs-stock and the lane-vs-V37 statements.
2. INFO: the build script's module docstring (lines ~40-85 of build_v37a_tva.py) still describes rev 2 (4*idx to 960, 42865, gain back to stock). Stale text, not behaviour.
3. INFO: DTC 0x5E observer reachability at a stalled railed lane is still unproven from firmware alone (inherited from rev 2).

## Not verified
Aggregator scale 0x6b3a -> EME compare; 0x2ABF2 caller status; an independent (non-kit) mirror of the PID.
