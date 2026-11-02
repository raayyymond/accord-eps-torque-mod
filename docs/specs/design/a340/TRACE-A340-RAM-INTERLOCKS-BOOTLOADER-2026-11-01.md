# T1b report (agent ram-a340, relayed by main). gp=0xFEDF8000, tp=0xBF000 on A340 (EVIDENCE 0x140c0-0x140d6).
A160 -> A340 RAM: angle 6a00->69c8 (writer FUN_0003f25a st.h 0x3f2da, 100 Hz slot 4, call 0x22f28); shadow 4c8a->4bea;
mode byte 67fe->67c4; setpoint 69ae->6976 (0xE4 RX FUN_000533e4, arithmetic IDENTICAL: sxh, shl2, subr, clamp +-0x4000, st.h 0x53460;
lane readers 0x2936a, 0x29536); field byte 6803->67c9 (bits 3:2); 6804->67ca; request 6805->67cb; 6802->67c8;
speed 6a5e->6a2e (writer 0x42ec4 FUN_00042a6e, 100 Hz); hand signed 4f60->4eb8; |hand| 4f68->4ec0; 1kHz EMA 6abe->6a8e (FUN_00041fe6);
100Hz rate fb 6a56->6a26 (FUN_000402f8, validity +13000>26000 identical); I state 6dd0->6da0 (lane st.w 0x2a5cc, ld.w 0x2a36e);
ramp 69b0->6978; sentinel 6cf8->6cc8; lane out 6b38->6b08 (0x2a66e); speed gate 67f4->67ba; state 67fa->67c0; tick flag 42fc->425c.
TRAP: A340 gp-0x69b0 is a 0x14A packer field. Lane = FUN_00029230 (slot-0 call 0x22618); uncalled twin FUN_0002ae74.
Cal deltas: motor scale 0xC6142=1157 (A160 1159); VGR LERP X 0xC68E2 last knot 12160 (A160 11513), Y 0xC68F2 = 0,44,60,70,75,74,49,-52.
0x14A packer FUN_000415d2 negates angle into 69b4/69b6.
NEW ON A340: FUN_0002a740 (100 Hz, slot-4 call 0x2332e) speed-LERPs records via ptr tables 0xC7784..0xC7A24 / 0xC72A4/0xC72D4,
selector gp-0x6714, into RAM arrays gp-0x6e20/6e18, 6e30/6e28, 6110/6104, 62d8/62cc, 62f0/62e4, 635c/6348; the lane reads them
(0x29e90-0x2a032, 0x2a2d0-0x2a306) -- absent on A160. => speed-scheduled lane terms; must be identified.
Cave home: free 0xFF 0xC4B2C-0xC4FF0; 0xC4C00..0xC4D04 unreferenced (tp/dword/mov32/jarl scans + xrefs, controlled); main CRC block
[0x13000,0xC4FFC). Cave writes no RAM; reads map to gp-0x6a8e, 6a2e, 4ec0, 69c8, 6da0. Scripts: scratchpad/t1b/.
# T1c report (agent interlocks-a340, relayed by main). gp=0xFEDF8000, tp=0xBF000 (EVIDENCE). Scripts scratchpad/t1c/.
Function pairs: lane 28ea6->29230; EME int shaper ->FUN_0004367a; float lockstep ->FUN_000449c6; DampAxis 41464->41fe6; 36c12->37794.
1. EME ladder, value-identical, shifted +0x50: int corridor-hi Y 0xC679E/0xC67A0 (1024), corridor-lo Y 0xC67AA/0xC67AC (-1024),
   boost floor Y 0xC67B8/BA/BC (0/1536/2048; X 700,800,1100 keyed gp-0x6a92<13001); floats corridor-hi 0xC65E8/0xC65EC (1.0f),
   corridor-lo 0xC65FC/0xC6600 (-1.0f), boost 0xC6614/18/1C (0/1.5/2.0). Lockstep compares float vs int/1024 -> code gp-0x68ce, fault >=128.
2. STEER_STATUS SM same structure (gp-0x67cd:=4 trip; DTC path FUN_00016ed0(0x49)). Cells: 0xC61D0/D2/D4 = 12800/8960/11520
   (A160 1600/896/1280); 0xC6504..07 = 112/96/54/64; DTC gate 0xC6508 = 112 (6 readers); 0xC652F=100, 0xC6530/31=50/50, 0xC6532=5.
   0xC61D0=12800 can never trip on stock (input clamped <=12800, test strictly greater) -- Honda already de-tuned it (BELIEF).
3. Low-speed lockout 0xC62FC = 0 already (reader 0x29240); upper bound 0xC62FA = 12800; new OR-term gp-0x687b untraced.
4. EME ramp step 0xC652E = 17 (8 live readers).
5. Hand fade: dir-2 = FIXED u8 cal tables 0xC6C10 (A-type, key gp-0x67f6: X 0,3,6,8,10,20 Y 255,251,241,233,227,205) and
   0xC6C00 (B-type, key gp-0x67f5: X 16,26,38,48,64,96 Y 255,237,196,145,99,77), selected by r25=(gp-0x67c9==2) at 0x2a072.
   dir-0 = RAM tables filled by FUN_0002a740 from 36 identical records: A: X 0,3,6,8,10,20 Y 255,255,212,185,154,51 (ptr tabs
   0xC7844/0xC7934/0xC7A24); B: X 16,26,38,48,80,112 Y 255x5,154 (0xC7814/0xC7904/0xC79F4). On A340 BOTH arms differ dir-2 vs dir-0.
   (Naming: V298's "fadeA2 0xE55A4" family = A-type = 0xC6C10; "fadeB2 0xE54FC" family = B-type = 0xC6C00.)
6. DampAxis: producer FUN_00041fe6 -> gp-0x6bfc; alpha2 0xC40D4 = 22 (>>6; reader 0x421a8), sibling 0xC40D2 = 3, alpha1 0xC645A = 37;
   consumer FUN_00037794 ptr table 0xCBE40 entries [26]/[27] -> 0xD7A54/0xD7A64 (SAME addresses), Y rows 0xD7A5C/0xD7A6C =
   -9830,-5734,-1966, X 0,1280,5760; clamp 0xC407E=511; output gp-0x6af6. Bank 0xCE000-0xD9FFF differs elsewhere (7487 B).
7. Engage ramp 0xC640C/0E/10/12 = 16/33/66/328 (unchanged values).
8. Angle constants: 0xC6450=900, 0xC6142=1157 (A160 1159), 0xC6542=128, 0xC636A=2, C-LERP X 0xC68E2 (last 12160) Y 0xC68F2
   (0,44,60,70,75,74,49,-52). 0.1 deg/count still BELIEF (check 0x14A packer passes gp-0x69c8 unscaled -- T1b: yes, negated only).
9. Strings 0x13100 '39990-TVA-A340' + '39990-TVA-A310C308'; 0x9011/0x901F, 0x14109/0x14117; 0x13109 and 0x14120 are '-'.
   SA key bytes 0x92C0..C5 identical.
# T3 report (agent rwd-a340, relayed by main; the agent could not write files)
1. Bootloader diff [0,0x13000): 139 runs / 2737 B. 0x1000-0x14D0 ID records (data); 0x2000-0x20C7 pointer table shifted +0x10;
   0x7314-0x7C50 recompiled code of the SECOND image [0x2000,0x7FFC) (role BELIEF); 0x7FFC and 0x12FFC CRC trailers;
   0x9000-0x12FFB only the 3 part-string bytes. SA handler 0xAAB4, decryptor 0xB35E, key-write handler, window worker 0x937C:
   byte-identical. SA constants 0x0211/0x0212/0x1220 at 0x92C0..C5 on both (positive control).
2. CRC layout identical to A160 (49/49 + 50/50; main block [0x13000,0xC4FFC)); build_v53_tva.owning_block works.
   build_vfourframe_tva baseline asserts are A160-specific -- do not call.
3. rwd: F181 string at 0x13100 '39990-TVA-A340', sibling A310 at 0x1310E, dead copies 0x14109/0x14117; same offsets as A160.
   '&'=BF109E is written by the flasher to DID 0xF101; decryptor identical -> same cipher. Proposed '/' headers:
   2x: 39990-TVA-A310, 39990-TVA-A340, 39990-TVA,A340 ; 6x: + 39990-TVA,A34C. '!' 001100121020 per entry. '%'=30 (BELIEF same).
4. Helper a340_paths.py in scratchpad.
# Free cal cell census, A340 (agent freecell-a340, relayed by main)
Only 0xFFFF run in [0xC6000,0xC6FFC): 0xC6D28..0xC6FEF (712 B). Scanner (all tp 4/6-byte forms, movea/addi off tp, mov imm32,
movhi+split, absolute words, pointer tables) positive-controlled: 6 readers of 0xC648A, 3 of 0xC62F8. 18 near-hits all false
(0x000C second halfwords, one mid-instruction, one region-table trailer word). Ghidra xrefs are blind on tp cells (returns none
even for 0xC648A) -- cannot prove a null. Recommended host: 0xC6E88 (8 B free around it); keep cells in 0xC6D48..0xC6FB0.
`ld.h 0x7e88[tp],r11` = 25 5f 88 7e (hw2 0x7E88). Block CRC trailer at 0xC6FFC must be recomputed. BELIEF: no register-indirect walk.
