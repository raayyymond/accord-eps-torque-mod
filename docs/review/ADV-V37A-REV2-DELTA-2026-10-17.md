# ADV-V37A-REV2-DELTA (adv37a-rev2) - 2026-10-17

VERDICT: PASS_WITH_DEFECTS. No pre-written FAIL condition fired. Defects are LOW or INFO. Images/rwd exactly as briefed (image sha256 6b457089..., rwd sha256 71652fa8...).
EVIDENCE = Python full-file diff / CRC walk / raw LE scans (positive-controlled) / Ghidra decompile of FUN_00028ea6, FUN_0002b422, FUN_00025c32, FUN_00041d56 + dry_run disasm. Ghidra program = stock code.bin (valid for code: code bytes differ from rev2 only at PN bytes 0x13109/0x14120 and the V37 cal edits).

## 1. Byte/CRC [EVIDENCE]
- rev2 vs rev1 over [0x13000,0x100000): 8 bytes: 0xC61B3 (04 vs 02), 0xC61B5 (04 vs 02), 0xC646C-D (0x06F6 vs 0x037B), trailer 0xC6FFC-F. Nothing else. (Brief said "6 bytes"; it is 4 payload bytes in 3 cells + 4 trailer bytes. Same content.)
- rev2 vs V37: 352 bytes. Everything outside the E4000-E8FFF map pages is 0xC62E6-7 (7680->42865 = 0xA771) and trailer 0xC6FFC. In the map pages only Y cells + the five trailers 0xE4FFC..0xE8FFC (map = rev1 map: rev1/rev2 identical there).
- Cells in rev2: 0xC646C=1782, 0xC61B2=0xC61B4=1024, 0xC62E6=42865 (V37: 1782/1024/1024/7680).
- All six trailers recomputed with zlib.crc32: match (0xC6FFC 9c2a2ce6, E4FFC 5b7f38f7, E5FFC fd71516f, E6FFC 262d7649, E7FFC 55cdc289, E8FFC bba529d4).
- Kit walk on the image: BL walk 49/49 PASS, walk_all_blocks 50/50 PASS. Same on the rwd payload decoded (parse_x31, cipher (0xBF,0x10,0x9E) ops xor,xor,sub), placed in a 0xFF 1 MB image: single block 0x13000 len 0xED000, 0 bytes differ from the image, BL walk 49/49 and full 50/50 PASS.
- Exactly ONE non-superseded V37A rwd on disk (REV2); the REV1 file carries the SUPERSEDED-DO-NOT-FLASH- prefix (sha c9bd3446...).
- Scripts: _scratch/v37a/rev2/{diff,rwd,lane,obs}.py

## 2. Lane tail at gain 1782 [EVIDENCE: decompile 0x28ea6 tail + dry-run disasm 0x2A174-0x2A23C + image bytes]
Path: x (clamped +-0xC61BE=15360 at 0x2A13E, all branches join 0x2A174) -> st.h gp-0x6b2e;
 new = (x*507>>10) + (992*state>>10) (0x2A180..0x2A1A8, 32-bit mul, two separate sar 10 floors); st.w state; out = (old+new)>>5 (0x2A1AC);
 gate test (0x2A1B4-0x2A1E2, only forces 0); r9 = sxh(out*ramp>>15) (0x2A1E6/EA/EC), ramp gp-0x69b0 is ushort and every write in the decompile is <= 0x8000;
 0x2A1EE ld.h 0xC646C (SIGNED, 1782 < 32768) ; mulh with polarity +-1 ; (r9 + r11)*gain*pol (32-bit mul) >>15 ; clamp +-ld.hu 0xC61B4 (1024; positive-branch re-load is ld.h, 1024 harmless) ; st.h gp-0x6b38 @0x2A23C.
- r11 addend (gp-0x6b2c): Y table 0xC673E..44 = 0,0,0,0 in rev2 (read); path proof inherited from older memory (BELIEF as to every path, EVIDENCE as to the table).
- Python mirror (lane.py, byte-read cells): x=15240 (P railed, taper 254/256) -> out 15088, T = +820 (matches the build's claim). x=15360 held (sum clamp, D on top) -> out 15208-15210, T = +827 / -828 (floor asymmetry). Random +-15360 sequences max |T| 723.
- 1024 clamp CANNOT bind: it needs x >= 19020 but x <= 15360 by the 0xC61BE clamp. Max |T| = 828.
- 16-bit truncation/overflow: none. out <= 15210 (fits int16 for sxh), 15210*32768 = 5.0e8 and 32767*1782 = 5.8e7 (< 2^31), store st.h of |T| <= 828. Sentinel/first-tick and ramp 0x8000 vs 0x7FFF give the same T.

## 3. Downstream with |T| up to 820-828 reached from idx 63 [EVIDENCE for cells and readers; BELIEF where marked]
- Reach/dwell difference vs V37 (arithmetic lens table x2): idx 63 -> 820 (V37 ~320), idx 32 -> ~316, idx 12 -> ~94. Rev2 sits at the rail for all idx >= 63 (91% of engaged time is idx <= 58 per memory, so most driving stays BELOW the rail; the rail is the high-demand regime). Ceiling is only +3.5% above V37's 799 (827 vs 799); the change is how EARLY and LONG it is reached.
- gp-0x682f thresholds: image 0xC64B4-B8 = 0xFF x5 and 0xC61C0/C2/C4 = 0xFFFF in both V37 and rev2 (read). gp-0x682f is min(|gp-0x4f60>>5|,255), from the torque sensor, not the lane output. Cannot be crossed by T. (Reads equal V37; stock differs - V37 inherited.)
- Lane consumers: gp-0x6b3c -> FUN_0002b422 clamps to +-0xC61B2 (=1024, signed ld.h at 0x2B436, same cell as the float twin FUN_0002b57a, so int and float agree) -> gp-0x6b3a -> FUN_00025c32 request slot (+-0x2800 clamp, decompile read). 828 < 1024 < 10240: no clamp binds.
- Soft-EME floors in rev2 = V37: 0xC6768/6A/6C, 0xC674E/50 all 4096 (read). Lane 828 << 4096 IF the aggregator passes it unscaled; I did NOT re-trace the aggregator scale (BELIEF, from the interlock lens plus the lineage: 6x builds held this lane at ~2461-2505 with raised 0xC61B2/B4 and flew).
- Cal constants in the 795-830 window checked for readers (raw tp scan, control = the 0xC61B4 and 0xC62E6 sites found): 0xC6306=800 read at 0x3FAF6 (FUN_0003f884, compared with gp-0x6a60 ushort; the other raw hit 0x1F4D4 has hw2[0]=0, not a load); 0xC630C=800 read at 0x44B64/0x44BBC (FUN_00044a8c, compared with a register and gp-0x6ba4); 0xC6764=800 and the 0xC54CE.. table values have no tp reader. None of these compares anything I can derive from gp-0x6b38/6b3a/6b3c (whose reader census is closed by the interlock lens). BELIEF that no threshold in (799,828] on a T-derived signal exists; EVIDENCE only for the direct readers of the lane cells.
- DTC 0x5E observer FUN_00041d56 (re-read): 3x3 state-space, DC gain from the u2 input (gp-0x501c) to the tested output is exactly 1.0 (x1024), from the angle input 0 (solved from the image floats, obs.py). Arm: |out| >= 0xC61FA=5530 (rising edge), release <1024 (0xC61F8), fault when the edge counter >= 0xC6500=3, latch cleared only by FUN_0003bcb2. So it needs ~5.4 units of SUSTAINED unexplained u2 (measured current) three times. Whether 820 counts at a stall produces that is NOT provable from the firmware alone (unit of u2 and motor constant unknown): OPEN, BELIEF = more reachable than V37 at idx 63..240 in a stall regime, because T there is up to 2.56x V37's; the ceiling only +3.5%.

## 4. 0xE4 sentinel [EVIDENCE: decompile 0x28ea6 ramp block + cells]
- 0x7FFF -> idx 240 -> sp 960 -> P rail -> T = +820 (steady value, 827 with D). The ramp gp-0x69b0 is decremented by ld.hu 0xC63F6 per tick (tp+0x73F6; value 16, read) in the block that sets gp-0x69b0 -= 0x73F6 (decompile lines at 0x29734 region); 0x8000/16 = 2048 ticks = 2.048 s at 1 kHz, and T falls linearly with the ramp (T = r9*ramp). Other fade cells for other states: 0xC63F4 = 328, 0xC63FA = 66, 0xC63F8 = 33 (unchanged vs V37).
- Pulse in rev2 therefore 820 -> 0 over 2.048 s toward a 123 deg/s reference (V37: ~794 toward 22 deg/s); stock ~399. Nothing changed in the fade; the same ramp-down, but the P stays railed longer because the wheel must reach the larger rate before E falls (BELIEF). Inherited V37 behaviour at ~2x stock peak; flag as the biggest dynamic exposure.

## Defects
1. LOW: brief/build docs say "three cells (6 bytes)"; actual 4 payload bytes. No effect.
2. LOW (BELIEF-open): DTC 0x5E arm reachability under a sustained railed lane at stall (see 3). Watch DTC 0x5E / latch gp-0x671d on the first drive.
3. INFO: negative rail -828 vs +827 (sar floor), same mechanism as stock.
4. INFO: rev1-lens statements "lane <= 417", "0xC646C readers return to stock", "0xC61B2 = stock" are STALE for rev2 (now 828, V37 values). Their conclusions that no clamp binds still hold (828 < 1024).
5. INFO: dwell exposure. Rail from idx >= 63 (V37: only near idx 240). Lane torque is a full 2x stock peak as the operator ruled; the extra exposure is time at 320-828 counts.

## Not verified
Aggregator scale from gp-0x6b3a to the EME compare; u2 units for the 0x5E observer; FUN_0004e82e invocation; any T-derived threshold reached through a register-indirect path.
