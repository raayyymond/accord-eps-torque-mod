# ADV-V37A-ARITHMETIC (lens 1) - 2026-10-17 - subagent adv37a-arith

VERDICT: PASS_WITH_DEFECTS (no pre-written FAIL condition triggered). Defects are low/informational.
Images: built `_v37a_plain_image.bin` sha256 7cb6fd3a...; Ghidra program = stock code.bin. Code region 0x14121..0xC4FFB is
byte-identical stock vs V37A (diff run), so Ghidra on stock is valid for the lane. EVIDENCE = Ghidra decompile + dry_run disasm + raw LE byte reads of the BUILT image.

## Edits seen in the image (V37 -> V37A diff, 356 B)
326 B = Y cells of the 28 map records (n and X bytes identical to stock, checked); CRC words E4FFC/E5FFC/E6FFC/E7FFC/E8FFC and C6FFC;
0xC61B3/B5 (1024->512), 0xC62E6 (7680->42865), 0xC646C (1782->891). Nothing else. [EVIDENCE: python diff]

## (1) Stage-by-stage widths (all EVIDENCE: dry_run disasm of 0x28F4C-0x29032, 0x29CB0-0x29E00, 0x29E32-0x29F40, 0x2A090-0x2A260)
| stage | addr | widths / signedness | new-value hazard |
|---|---|---|---|
| fb clamp | 0x28F96 `ld.hu 0x72e6,tp`, 0x28F9C `ld.hu`, 0x28FB8 `ld.hu` | all three ld.hu (bytes e56f/e577/e5d7 + hw2 72e7); r26 is a 32-bit reg; compares `cmp/ble`, `cmp/bge` signed 32-bit on zero-extended limit; negate via `subr r0` | 42865 stays +42865 (not -22671). Raw scan of the whole code region for tp+0x72e4..7 finds exactly these 3 readers of 0xC62E6 (positive control = the 3 known sites; 0x29D6E.. are 0xC62E4; 0x61824/0x618D4 are base r0, not tp). No signed reader. |
| fb state | 0x28FA8 `st.w gp-0x3d30` | stores the unclamped increment, clamp only shapes r26 | none |
| map walk | 0x29D18-0x29D68 | every X/Y load is ld.hu, unsigned compares (bh/bnc), diff in 32 bit, `mul`, signed `divq r10,r13,r0` (dst != src, so the SLEIGH divq bug does not apply), `+Y[k-1]` | max dY*di = 960*240 fine |
| sp | 0x29D6C `mulh r13,r16` | low 16 bits of Y, SIGNED, times +-1 | 960 < 32768 OK. Y is read ld.hu but mulh re-sign-extends: any Y >= 32768 would flip. 960 safe. |
| sp publish | 0x29D72 `st.h gp-0x6a32` | 16-bit | +-960 fits; no 4-byte reader exists (6-byte forms not scanned: BELIEF) |
| E | 0x29D76 `shl 5`; 0x29D78 `sub r26` | 32-bit | max abs 30720+42865 = 73585 |
| P | 0x29E36 `mul r9,r8`; 0x29E3E `sar 8`; clamp ld.hu 0xC61BC (15360) | 32-bit product | max abs E*Kp = 73585*717 = 52.8e6 < 2^31 (Kp max over all 28 sel = 717; live sel7 696) |
| E_prev | 0x29E62-0x29E7E `mov 0x177001`, `0xFFF44800`, `cmovnc r16,r8,r27` | unsigned window prev in [-768000,768000] else dE = 0 | |E| <= 73585 is always inside the window; sentinel 0x7FFFFFFF wraps to 0x800BB7FF >= 0x177001 so it takes dE = 0. A 0 -> 960 step gives dE = 30720. |
| D | 0x29EE4 `mul r7,r8`; 0x29EEC `sar 3`; clamp ld.hu 0xC61B6 (10240) | 32-bit | max abs dE = 147170, Kd = 128 on every selector, product 18.8e6; the step (30720*128)>>3 = 491520 clamps to 10240, no overflow |
| sum | 0x29F18-0x29F24 | 32-bit; I = state>>7, Ki = 0 (0xC63E6 = 0 in all 3 images) so I = 0 | |S| <= 25600 fits the int16 publish at gp-0x6b34 |
| taper | 0x2A0B4-0x2A0C2 `mulu`, `andi 0xffff`, `sar 8`, `mul r2`, `sar 8` | A*B <= 255*255 = 65025 < 65536, so `&0xffff` never wraps; factor = 254 | S*254 <= 6.5e6 |
| sum clamp | 0x2A13E ld.hu 0xC61BE=15360, +branch `ld.h` 0x2A146 | sign-extends 15360 harmlessly | |
| lag | 0x2A174-0x2A1AC | two separate floors; poles 992/507 | state <= 243360, 32-bit |
| ramp x | 0x2A1E6 `mul r14,r9; sar 15; sxh` | | 0x7FFF and 0x8000 give the same T (checked) |
| gain/out | 0x2A1EE `ld.h 0x746c` (891), `ld.b gp-0x6752` (+-1), `mulh`, `mul r13,r11`, `sar 15`, clamp `ld.hu 0xC61B4` (512, + branch ld.h) | | 891*15088 fits; the 512 clamp never binds (max T 410) |
| store | 0x2A23C `st.h gp-0x6b38` | | readers 0x4E8D2/0x4E8E2 `ld.h`, +-512 fine |

## (2) Record layout from the instructions [EVIDENCE]
Pointer table 0xC9A88, index = selector*4 (`shl 2` at 0x29CCE), loaded `ld.w` at 0x29D0C. Record: X[0] = `sld.hu 2[ep]` (rec+2), X[9] = `sld.hu 0x12[ep]` with ep=rec+2 (rec+0x14), Y[0] = rec+0x16, Y[9] = `ld.hu 0x12[r6]` (rec+0x28). That is u16 n, X[10], Y[10] with Y[0] at rec+2+2n. n is NEVER read; 10 is hard-coded. All 28 records have n = 10 (python). Only readers of the pointer table: 0x29CFE (live) and 0x2ABF4 (uncalled twin island); positive control = 0x29CFE found.

## (3) Index path [EVIDENCE]
0x29CD6 `sar 6` of the demand product, signed clamp +-0xC64F0/0xC64F1 (ld.bu, both 240 in the built image), abs at 0x29CF6/FA, `zxb` at 0x29D12, sign from `cmovn` at 0x29CD8. idx is in [0,240] always. Even if it were larger, `bnc` at 0x29D30 returns Y[9] = 960 for any idx >= X[9]. LIM record 0xE51A8 is flat 15360 (read from image) = 240*64, so idx 240 is exactly reachable. Max sp = 960, max 32*sp = 30720.

## (4) Python mirror (scratchpad mirror.py, stress.py; annotated with the addresses above). Live selector 7, steady state, fb = 0 / fb = 32*sp
| idx | stock sp,P,S3,T | V37A sp,P,S3,T (fb=0) | V37A fb=32sp |
|---|---|---|---|
| 12 | 24, 882, 875, 23 | 48, 1764, 1750, 47 | E=0, all 0 |
| 32 | 62, 2883, 2860, 76 | 128, 5952, 5905, 158 | 0 |
| 62 | 97, 5917, 5870, 157 | 248, 15128, 15009, 404 | 0 |
| 63 | 98, 6027, 5979, 160 | 252, 15360, 15240, 410 | 0 |
| 240 | 172, 14964, 14847, 399 | 960, 15360, 15240, 410 | 0 |
The build script's claims CHECK OUT: P rails first at idx 63 (idx 62 is 15128), T = 410 at the rail (-411 negative side, floor asymmetry; the stock mechanism), output clamp 512 never binds, S3 = 15240 not 15360 because the taper is 254/256. Stress over fb in +-42865, both signs, all idx: no overflow, no sign flip. fb = +42865 with sp = -960 gives E = -73585, P and D rail negative, S3 = -15360 (bounded). The scale is consistent: 960/172 = 5.581 = 42865/7680.

## Defects
1. LOW - selectors 0,2,4,5 (reachable, selector <= 9) are NOT an exact straight line: Y1 = 32 or 22 gives non-integer slope 8/3 and 11/6; integer knots + LERP deviate from the ideal line by up to 1.00 / 1.17 setpoint counts (<=0.12 % of 960). Live selector 7 and selectors 1,3,6,8,9 are exact (slope 4 or 2). Selectors 10-27 also 1.17 but dead (selector max 9, memory). No safety effect.
2. INFO - negative-side `sar` floor makes T = -411 vs +410 at the rail; same mechanism as stock.
3. INFO / BELIEF inherited, not re-proven: the 0x2A1FC addend is zero (I re-read the gp-0x6b2c Y table 0xC673E-44 = 0,0,0,0 in the built image; path proof is from the older memory); integrator state boots 0; damper mode 0x2A0C6 unreachable (gp-0x680a no writers); gp-0x6a34 |fb|>>5 consumers (0x2A0CA, 0x2AFAE) are in that mode / the uncalled island.
4. FOR LENS 4 - 0xC646C has more `ld.hu`-form readers than the lane: 0x2B656, 0x2C488, 0x36686, 0x3684A (plus 0x2A904 in the twin). They see 891 = stock (V37 had 1782), so no delta vs stock; not traced. 0xC61B2 readers are only 0x2B42A-0x2B5B6 (value = stock).

Not verified here: CRC words (lens 3), EME/lockstep interlocks (lens 4), the telemetry instrument question (project rule 2).
