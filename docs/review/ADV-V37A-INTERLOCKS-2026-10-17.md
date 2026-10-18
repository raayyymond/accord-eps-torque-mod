# ADV V37A - lens 4: INTERLOCKS AND DOWNSTREAM CONSUMERS (2026-10-17, adv37a-interlocks)

Image: `_v37a_plain_image.bin` sha256 7cb6fd3a...9930 (verified). Ghidra program `code.bin` is stock. It is valid for code because V37A code bytes in [0x13000,0xBF000) differ from stock only at 0x13109 and 0x14120 (PN bytes, same as V37). All scans are raw little-endian Python on the V37A image, positive-controlled (the jarl scan finds 28ea6 from 0x22522, 2b422 from 0x22530, 2b62c from 0x22eda; the gp scan finds the known st.h at 0x29d72). Where noted they are cross-checked with Ghidra search_instructions or get_xrefs_to.

## VERDICT: PASS_WITH_DEFECTS. No pre-written FAIL condition is met. Every defect is LOW or INFO.

## 1. Consumers of the setpoint gp-0x6a32 and of E/P/S/lane torque [EVIDENCE]
- gp-0x6a32 has exactly 2 accesses, both STORES: 0x29d72 (live FUN_00028ea6) and 0x2ac68 (FUN_0002a93a, uncalled twin). ZERO loads. Raw scan and Ghidra search_instructions("-0x6a32") agree. The setpoint is consumed only as register r16 by the error former at 0x29D76.
- Other uses of sp inside FUN_00028ea6: P = clamp(32*E*Kp(idx)>>8, +-0xC61BC), a setpoint-derivative term clamp(+-0xC61B6), and I (Ki 0xC63E6 = 0, inert). Each term keeps its own unchanged clamp, then the sum clamp 0xC61BE = 15360 (unchanged). At idx >= 240 Kp = 696, so P = 87*E and the rail is reached at E >= 177. Stock sp 172 gives 14964 (the stock peak). V37A gives 15360. Same ceiling, +2.6 %.
- Published cells gp-0x6b2e/32/34/36, gp-0x697a: ZERO readers (stores only, lane plus dead island). gp-0x6b30 is read only at 0x2a1d4 (lane, sign test next tick) and 0x2a8de (dead island). gp-0x6cf8 (previous sp, first-tick sentinel) is read only at 0x29e5e. gp-0x6dd0 (I) is read only at 0x29da4. No plausibility, rate-of-change, lockstep twin, EME or DTC reads any of them.
- Lane torque gp-0x6b38: readers 0x2b418 (dead FUN_0002b35a, no callers) and 0x4e8d2/0x4e8e2 (FUN_0004e82e, a CAN frame builder writing it to bytes 7-8; no direct caller, probably table-dispatched, BELIEF). gp-0x6b3c has one live reader, 0x2b42e (FUN_0002b422). It clamps to +-0xC61B2, writes gp-0x6b3a and calls FUN_00025c32 (request slot, clamp +-0x2800). Its float twin FUN_0002b57a (live, jarl 0x22572) re-clamps gp-0x6b3a to +-0xC61B2 as float and passes a +-0.003 window to FUN_00027802. Both read the SAME cell 0xC61B2, and V37A sets it to 512 = stock, so int and float stay identical. The lane output is at most 15360*891>>15 = 417 counts, below 512, so neither clamp binds. 417 is stock's documented ceiling.
- gp-0x682f = min(|gp-0x4f60>>5|, 255) is built from the torque-sensor signal gp-0x4f60, not from sp/E/P. Unaffected.
- Dwell precedent: 6x-gain builds V101-V112 held the lane at 2505-3072 (rail 81.5 % of engaged time) and flew fault-free with the EME audit passing (BUILD-LINEAGE V101/V102/V103 rows). V37A's lane is at most 417.

## 2. Readers of map pointer table 0xC9A88 and the 28 records [EVIDENCE]
- Absolute-address scan of 0xC9A88: 0x29cfe (FUN_00028ea6, live) and 0x2abf4 (FUN_0002a93a, dead twin). Ghidra get_xrefs_to agrees (29d06/29d0c and 2abfc/2ac02).
- Record addresses are referenced only by the pointer table and by the CRC page list at 0x8ae38 and 0x8ae8c-0x8ae98 (page bases). All other 32-bit hits in code were odd-offset false hits. A movhi/movea pair scan into 0xE4000-0xE8200 returned 0 (its positive control is weaker, BELIEF).
- FUN_0002a93a has zero callers by Ghidra and by raw jarl/jr scan. No branch enters 0x2a30e-0x2b422 from outside. Dead.
- Y is read as ushort and interpolated in int; Y max 960. The X axis is untouched, so the index statistics and the gp-0x674b tap field are unchanged.
- CRC pages 0xC6 and 0xE4-0xE8 recomputed with zlib.crc32 over [page, page+0xFFC): all match the stored trailers on V37A.

## 3. Readers of 0xC646C [EVIDENCE]
Raw scan of tp+0x746C: 0x2a1ee (lane, live), 0x2a904 (dead island), 0x2b656 (FUN_0002b62c, caller 0x22eda), 0x2c488 (FUN_0002c478, caller 0x2242e), 0x36686 (FUN_00036682, caller 0x3acdc), 0x3684a (FUN_00036828, caller 0x23256). The four non-lane live readers use one idiom: (gp-0x4f60 torque signal * gain >> 15) * polarity gp-0x6752, then a clamp (+-0x4800, +-0xC00 or +-0x2800). On V37 they ran at 1782. V37A returns all four to stock 891 = stock behaviour. I found no int-versus-float twin keeping a fixed gain (not exhaustively proven, BELIEF). The V57 repoint to 0xC6CD0 does not exist here.

## 4. Readers of 0xC61B2, 0xC61B4, 0xC62E6 [EVIDENCE]
- 0xC61B2: 0x2b42a, 0x2b436, 0x2b43c, 0x2b446 (FUN_0002b422) and 0x2b5b6 (float twin FUN_0002b57a). 0x2b436 is ld.h, the rest ld.hu. 512 is positive, so identical.
- 0xC61B4: 0x2a1f8 (lane clamp), plus dead island 0x2a910.
- 0xC62E6 (42865 = 0xA771): exactly 3 reads, 0x28f96, 0x28f9c, 0x28fb8, all ld.hu, all in FUN_00028ea6. No second reader, no width or sign mismatch, no twin.

## 5. Engage, disengage, bail [EVIDENCE for code/bytes, BELIEF for behaviour]
- The lane entry guard (raw rate gp-0x6a56 within +-12000, gp-0x4f60 range, polarity) does not read sp or E. The disengage skips (0x29A5C/64 to 0x2A164, 0x29A70 to 0x2A0C6) and the epilogue writing 0x7fffffff to gp-0x6cf8 are untouched (code identical). The first-tick test treats |previous sp| > 768000 as first tick. sp <= 960 never does; the sentinel does.
- The STEER_STATUS machine (0x29068-0x29330) reads gp-0x682f, a filtered torque derivative, gp-0x69aa, |gp-0x69ae| <= 0x4000, gp-0x67fe and gp-0x6400 bit 3. None reads sp, E, P or the lane output. States 4 and 7 are structurally dead on the V37 base: 0xC64B4-B8 = 0xFF (gp-0x682f saturates at 255) and 0xC61C0/C2/C4 = 0xFFFF (derivative clamp 0x3200). Unchanged by V37A.
- Re-engage ramp (0xC64DE = 0x1B) and output gate (0xC61B8 = 102, arm 0xC64A3 = 1) are identical to V37. The gate acts only when gp-0x6806 = 0, which is status-driven and not sp-dependent.
- 0xE4 fault sentinel (idx 240): stock sp 172 gives P 14964, V37A sp 960 gives 15360. Same fade, +2.6 % amplitude.

## 6. Commanded-versus-achieved protections [census EVIDENCE, stall behaviour BELIEF]
- Lane internals: Ki = 0, so no wind-up and no timer.
- FUN_0004595a is an instantaneous comparator. FUN_0004503c is slew plus MIN. The energy budget FUN_0007b022 is unreachable (gp-0x4f64 <= 5325).
- Soft-EME integrator gp-0x3570 trips only when |gp-0x6acc| exceeds the bound. V37 bound floors are 4096 (0xC6768/6A/6C, corridor 0xC674E/50), against a lane of at most 417. The lane cannot wind it up alone.
- FUN_00041d56 (DTC 0x5E, latch gp-0x671d, SET at |x| >= 0xC61FA = 5530) is an observer over MEASURED motor current (gp-0x501c, from FUN_00070a98) and motor angle gp-0x4fd8. It is the one monitor on a command-versus-response mismatch. It does not read the lane or sp. See D1.
- No stall or overload timer on the lane's consumers was found.

## 7. Untouched gates [EVIDENCE]
Code is identical to stock apart from the PN bytes. The 0xE4 |cmd| <= 0x4000 check, the 0x7FFF sentinel and the LIM record 0xE51A8..0xE51C7 are byte-identical to stock.

## Defects (none FAIL)
- D1 LOW: the DTC 0x5E latch observer (FUN_00041d56) could arm if a held wheel opposes a railed lane. BELIEF that it needs a stall regime. Exposure is below every flown 6x build. Watch DTC 0x5E and the r24 arm on the first drive.
- D2 LOW: V37's STEER_STATUS 4/7 override paths are structurally off, and the lane now reaches its rail at E >= 177 over a much wider range, so a driver holding the wheel gets no firmware override. Inherited from V37; only the exposure grows.
- D3 INFO: restoring 0xC646C halves four non-lane assist paths (0x2b656, 0x2c488, 0x36686, 0x3684a) versus V37.
- D4 INFO: FUN_0004e82e puts lane torque in a transmitted frame; range at most 417, same as stock.

## Not verified
Body of FUN_00027802; how FUN_0004e82e is invoked; whether FUN_00041d56's x reaches 5530 under a stalled railed lane; the movhi/movea pair scan has a weak positive control; CRC of block 0xC4 (different range, unchanged versus V37).
