# T1a — the LKAS rate-PID lane on A340 (`39990-TVA-A340`, sha 01a53539…)

Subagent T1a → `main`. Ghidra program `/A340_stock.bin` confirmed before every batch; never switched, never saved;
every `disassemble_bytes` was `dry_run:true`. Python = bin_decompile env. Scripts + extracted listings:
`scratchpad/t1a/` (`FUN_00029230.c/.asm`, `align.py`, `cells.py`, `tpscan.py`, `jarl.py`, `recs.py`, `pin.py`, `ramtab.py`).

**Note:** the task message reached me truncated after "E4 0x29D6A `mov/mul". I covered every V300 A-/B-/D4 row and every
V37A cell that lives in or is read by the lane. Items on the rest of the list that are outside the lane are marked "not traced".

## 🛑 HEADLINE — A340's lane is NOT a re-addressed A160 lane. Five structural differences change the port

1. **Kp, Kd, Ki, the rate-reference map and the two dir-0 hand-fade arms are RAM tables, SPEED-SCHEDULED.**
   `FUN_0002a740` (called from the slot-4 task `FUN_00022d96`) blends three per-variant flash records per table across
   three speed knots (speed gp-0x6a2e, knots 4160/5120/12800 = 65/80/200 km/h) into RAM. The lane LERPs the RAM copy.
   ⇒ a V37A map edit or a V300 Kp/Kd/Ki edit is **12 variants × 3 speed records = 36 records per table**, not 28.
   All 36 are byte-identical on stock (EVIDENCE: `recs.py`). The RAM tables boot to 0 (`.data` image).
2. **Gain Q-format differs: P = (E·Kp)>>3 on A340 vs >>8 on A160** (`0x2A390 mul r27,r10 ; 0x2A39C sar 0x3,r10`).
   The I increment has an extra `shl 0x2` (`0x2A372`), so A340 inc = (Ki·db·4)>>3. D is the same: (dE·Kd)>>3.
   **All three gains are truncated to 8 bits** (`zxb`/`andi 0xff` at 0x2A010/0x2A06C/0x29FB4). ⇒ V300 Kp 112 (A160) =
   0.4375 is **not representable** on A340 (Kp 3 = 0.375, Kp 4 = 0.5). Ki 40 (A160) ≡ **Ki 10** exactly. Kd 48 ≡ **Kd 48**.
3. **Stock A340 ICL `0xC61C8` = 0** (A160 `0xC61BA` = 10240). Ki is 0 on all 36 records anyway.
4. **The A160 hook link register r6 is LIVE on A340.** It holds engage state gp-0x6764, read at 0x2A658 `cmp 0x1,r6`,
   with no write between hook and use. DB (r8) is also live into the freeze return. **The V299/V300 cave cannot be
   relocated byte-for-byte; it must be re-registered** (map below).
5. **V300's private forward-gain cell `0xC6CD0` is OCCUPIED on A340** (bytes `28 57`, read by `ld.bu` at 0x6E5C0). A
   different free cal cell is needed for A6.

Also: an extra post-fade clamp `0xC61CA` = 20476 that A160 does not have. The dir-2 hand-fade arms are **flash byte
tables** `0xC6C10`/`0xC6C00` (6 knots, u8), not records. The low-speed lockout `0xC62FC` is **already 0 on stock**.

## gp / tp (EVIDENCE)
`gp = 0xFEDF8000`, `tp = 0xBF000` on A340. The startup sequence at 0x140C0–0x140DF is **byte-identical** to A160
(`ori 0x8000,r0,r1 ; movhi 0xfedf,r0,gp ; movea 0,gp,gp ; add r1,gp ; movhi 0xb,r0,tp ; movea 0x7000,tp,tp ; add r1,tp`;
Ghidra dry-run decode). Anchor: `tp+0x72f8` reads 7680 (A160's fb clamp value) and has 3 `ld.hu` readers in the lane,
the same pattern as A160 `0xC62E6`. `.data` image: flash `[0x87320,0x8BC6C)` → RAM `0xFEDF11C0…` (copy loop 0x147BC–0x147F4).

## 1. Function, caller, twin

| A160 | meaning | A340 | stock | method | conf |
|---|---|---|---|---|---|
| `FUN_00028ea6` 0x28EA6–0x2A30D | LKAS rate PID lane | **`FUN_00029230`** 0x29230–0x2A73F | — | 8-byte window match (delta clusters +0x3AE…+0x418); mnemonic alignment 1355/1874 matched (difflib); decompile structure identical through the fb filter, guard, setpoint, P/I/D, lag, gain, taper | high |
| call 0x22522 in slot-0 task 0x2214A | sole caller | **0x22618** `80 ff 18 6c` (`jarl 0x29230,lp`) in `FUN_00022240` | — | Ghidra callers (1) + raw Format-V scan (exactly 1 hit). Task-table pointer at 0xBB950 (A160 0xBB928); slot-4 is +0xC0 in both | high |
| `FUN_0002a30e` + island →0x2B421 | uncalled twin | **0x2AE74** (prologue `prepare {r20,r22,r24,r26,r28,lp}`, `FUN_00047a28(9)`, `tp+0x7532`); not a Ghidra function. Plus **`FUN_0002b4a0`** 0x2B4A0–0x2BBF1 (lane-tail duplicate: reads the RAM gain tables, 0x71C4/71CA/71CC/71CE) | — | raw jr/jarl scan into [0x2AE74,0x2BBF2): only intra-island `jr`. Three odd-register "jarl" hits (0x240DC, 0x33458, 0x56284) are mid-instruction, adjudicated by Ghidra dry-run decode. No even absolute pointer to an entry. Ghidra: no callers | high |
| — | gain/map table fill (NEW) | **`FUN_0002a740`** 0x2A740–0x2AE73, called by slot-4 `FUN_00022d96` (task ptr 0xBBA10) | — | decompile | high |
| 0x2B422 (live) | limit&pack (reads `0xC61B2`) | **`FUN_0002bfa4`** (reads `0xC61C0` ×5), caller `FUN_00022240` | — | tp scan: same 4+1 reader shape | high |

## 2. In-place code sites (V298/V300 A2 rows)
Encoder **positive control**: my encoder reproduces all six A160 V300 edits byte-for-byte (E1, B2, A2, E4, HOOK, OPH).
"A340 new" = the same edit encoded for A340's registers. These are DERIVED and unverified by any build.

| id | A160 addr: stock → V300 | meaning | A340 addr: **stock bytes** | A340 equivalent edit | method | conf |
|---|---|---|---|---|---|---|
| E1 | 0x28F4C `24 3f aa 95` → `24 3f 00 96` | x := θ (gp-0x6a56→gp-0x6a00) | **0x292EE** `24 47 da 95` `ld.h -0x6a26[gp],r8` | `24 47 38 96` (`ld.h -0x69c8[gp],r8`) | alignment + decompile (`gp-0x6a26 + 12000 < 0x5dc1` validity, fb-filter input) | high (site) |
| E2 | 0x28FA4 stock **`c9 d1` add r9,r26** (V295 had subr) | — | **0x29346** `ca d1` `add r10,r26` | **none: stock is already `add`** | bytes | high |
| B2 | 0x29A50 `e2 47 00 00` → `e0 df 34 43` (`cmovne r0,r27,r8`) | r8 = (req==1)?eligible:0 | **0x29E68** `e2 47 00 00` `setfe r8` (after `cmp 0x1,r10`, r10 = gp-0x67cb request) | **`e0 cf 34 43`** (`cmovne r0,r25,r8`): the eligibility flag is **r25** on A340 (r27 on A160) | full reference census of r25/r27/r29 in both: A160 `0x2913A mov r8,r27` ↔ A340 `0x2954C mov r13,r25`, no intervening writer | high |
| A2 | 0x29A56 `da 05` → `b2 05` | PID runs iff ramp≠0 ∧ r8≠0 | **0x29E6E** `da 05` `bne 0x29E78` | `b2 05` (`be 0x29E74`); skip target `jr 0x2A596` at 0x29E74 | identical 6-insn layout | high |
| E4 | 0x29D6A `08 80 ed 80` → `24 87 52 96` | sp := gp-0x69ae (demand) | **0x2A334** `08 48 eb 48` `mov r8,r9 ; mulh r11,r9` | `24 4f 8a 96` (`ld.h -0x6976[gp],r9`) | gp-0x6976 = clamp(−4·raw, ±0x4000) in 0xE4 RX `FUN_000533e4` (decompile) | high |
| HOOK | 0x29D76 `c2 82 ba 81` → `jarl 0xC4C00,r6` | E := 32·sp − fb → cave | **0x2A340** `c5 4a ba 49` `shl 0x5,r9 ; sub r26,r9` | `jarl <cave>,rL` with **rL ∈ {r7,r10,r16}**, **NOT r6** (live) | liveness: first post-hook access of r7/r10/r16 is a write on every path | high (site), design open |
| HOOK_RET | 0x29D7A `mov r16,r6` | normal return | **0x2A344** `mov r9,r13` | — | alignment | high |
| FRZ_RET | 0x29D7E `cmp r10,r6` | freeze/CAM return | **0x2A348** `cmp r8,r13` | cave's freeze value register r6 → **r13**; **r8 = DB must be preserved** | alignment + liveness | high |
| SKIP_TGT | 0x2A164 | Honda skip epilogue | **0x2A596** | — | alignment (`mov 0,lp…; mov 0x7fffffff,r9`) | high |
| OPH | 0x29EE0 `10 40 bb 41` → `1a 40 00 00` | D operand := r26 | D operand is `0x2A3D0` `e9 57 32 53` `cmovnc r9,r10,r10` + **0x2A3D4 `89 51` `subr r9,r10`** | **`1a 50` at 0x2A3D4** (`mov r26,r10`), a 2-byte edit; the cmovnc becomes dead | decompile + asm (A340's D path is restructured: prev = gp-0x6cc8, Kd = r21) | high (site) |
| A6 | 0x2A1EE `25 3f 6c 74` → `25 3f d0 7c` | forward gain → private cell | **0x2A620** `25 5f 8a 74` `ld.h 0x748a[tp],r11` (hw2 at 0x2A622) | repoint hw2 to a free cal cell. **0xC6CD0 is NOT free on A340** | tp scan: `0xC648A` has 6 readers (0x2A620, twin 0x2B46A, 0x2C1D8, 0x2D00A, 0x37208, 0x373CC); A160 `0xC646C` has the matching 6 | high (site), cell TBD |

**Cave register map (DESIGN PROPOSAL, BELIEF until rebuilt and adversarially verified).** A160 cave → A340:
E r16→**r9**; fb r26→r26 (dead after hook except the unreachable damper path); camera flag r25→**r25** (A340 `0x2A072
setfe r25` from gp-0x67c9==2, no writer until 0x2A45C); ramp r14→r14 (gp-0x6978-derived, same SM). Scratch r8/r9/r13
need new homes (r8 and r9 are live), e.g. r10/r16/r7/r11. Link r6→r7/r10/r16. Freeze output r6→r13.
**Live across the hook — the cave must not touch these:** r1, r6, r8, r12, r14, r15, r21, r24, r25, r27, r28, r29.
gp inputs: gp-0x6abe→**gp-0x6a8e** (raw rate; producer `FUN_000402f8` shows the same `+13000 > 0x6590` validity),
gp-0x6a5e→**gp-0x6a2e** (speed), gp-0x4f68→**gp-0x4ec0** (|τ|, 37 accesses + 1 writer in both), gp-0x6a00→**gp-0x69c8**
(θ: 15 accesses + 1 writer in both; `FUN_0003f25a` ≡ A160 `FUN_0003e6d8`), gp-0x6dd0→**gp-0x6da0** (I state).
Free flash: `[0xC4B2C,0xC4FF0)` = 1220 B of 0xFF, ending at a CRC node at 0xC4FF0 with the same trailer layout as A160.
The CRC-block membership is BELIEF (not walked).

## 3. Lane cal cells (V300 A4/B rows, V37A a/b/d)
Values are LE u16 read from the A340 image. Reader counts come from a raw tp scan; the A160 control finds 3 readers for `0xC62E6`, which is correct.

| A160 cell (stock) | meaning | A340 cell | A340 stock | readers (raw scan) | conf |
|---|---|---|---|---|---|
| 0xC63E8 (923) | fb lag a (`ld.h`) | **0xC63F8** | 953 | 1: 0x2932C | high |
| 0xC63EA (1560) | fb lag b | **0xC63FA** | 1554 | 1: 0x29328 | high |
| 0xC62E6 (7680) | fb clamp C | **0xC62F8** | 7680 | 3: 0x29338/0x2933E/0x2935A | high |
| 0xC62E4 (4) | I deadband DB | **0xC62F6** | 4 | 4 lane + 3 twin | high |
| 0xC63E6 (0) | Ki (flat cell) | **none: RAM table gp-0x6e20** (records below) | 0 ×36 | — | high |
| 0xC61BA (10240) | ICL (`shl 0xa`,`sar 3`) | **0xC61C8** | **0** | 0x2A36A + twin | high |
| 0xC61B6 (10240) | D clamp | **0xC61C4** | 10240 | 4 lane + 3 twin | high |
| 0xC61BC (15360) | P clamp | **0xC61CC** | 20480 | 3 + 3 | high |
| — | post-fade clamp (A340 only) | **0xC61CA** | 20476 | 4 + 3 | high |
| 0xC61BE (15360) | sum clamp | **0xC61CE** | 20480 | 4 + 4 | high |
| 0xC63EC (992) / 0xC63EE (507) | output-lag a / b | **0xC63FC / 0xC63FE** | 1005 / 324 | 2 each (lane + undefined 0x2B408/0x2B3F8) | high |
| 0xC61B8 (102) | lag-bypass threshold | **0xC61C6** | 102 | 2 | high |
| 0xC646C (891) | Q15 forward gain G | **0xC648A** | **888** | 6, shared | high |
| 0xC61B4 (512) | lane output clamp | **0xC61C2** | 512 | 4 lane + 4 twin (same shape as A160) | high |
| 0xC61B2 (512) | limit&pack clamp | **0xC61C0** | 512 | 5 in `FUN_0002bfa4` | high |
| 0xC62EA (320) | low-speed lockout (D4) | **0xC62FC** | **0 (already off)** | 1: 0x29240 | high |
| gp-0x6b38 | lane torque out | **gp-0x6b08** | — | `st.h r1,-0x6b08[gp]` 0x2A66E | high |

## 4. Records (Kp/Kd/Ki, map, fades). EVIDENCE = `FUN_0002a740` decompile + `recs.py` dump
Each record is `n` at +0, then X[n] at +2, then Y[n]. 12 variants (selector gp-0x6714, one writer at 0x432AC, boots 0).

| table | ptr tables (low/mid/high speed) | n | Y offset | RAM target | stock (all 36 identical) |
|---|---|---|---|---|---|
| Kp | 0xC77E4 / 0xC78D4 / 0xC79C4 | 5 | +0x0C | gp-0x6110/-0x6104 | X 0,68,112,136,208 · Y 10,15,19,21,21 |
| Kd | 0xC7784 / 0xC7874 / 0xC7964 | 4 | +0x0A | gp-0x6e30/-0x6e28 | X 0,40,80,112 · Y 32 ×4 |
| Ki | 0xC77B4 / 0xC78A4 / 0xC7994 | 4 | +0x0A | gp-0x6e20/-0x6e18 | X 0,8,40,72 · Y 0 ×4 |
| map (V37A c) | 0xC72A4 / 0xC72D4 / 0xC7304 | 10 | +0x16 | gp-0x635c/-0x6348 | X 0,6,16,35,53,77,102,127,160,240 · Y 0,17,41,69,91,119,142,165,187,187 |
| fadeB dir-0 | 0xC7844 / 0xC7934 / 0xC7A24 | 6 | +0x0E | gp-0x62d8/-0x62cc (idx gp-0x67f6) | X 0,3,6,8,10,20 · Y 255,255,212,185,154,51 |
| fadeA dir-0 | 0xC7814 / 0xC7904 / 0xC79F4 | 6 | +0x0E | gp-0x62f0/-0x62e4 (idx gp-0x67f5) | X 16,26,38,48,80,112 · Y 255,255,255,255,255,154 |

Speed knots (u16 ×3, all 4160/5120/12800): Ki `0xC64C0`, Kp `0xC64C8`, Kd `0xC64B8`, map `0xC64D0`, fadeB `0xC64E0`, fadeA `0xC64D8`.
Records live in two pages: **0xE4000–0xE4E6F** (variants 0–5) and **0xE5000–0xE5E6F** (variants 6–11).
Gain index = gp-0x6711, the demand index (A160 gp-0x674b), written in-lane at 0x2A2D6.
**dir-2 fade arms (V300 A5) = flash u8 tables:** fadeB2 `0xC6C10` = n 6 · X 0,3,6,8,10,20 · Y 255,251,241,233,227,205;
fadeA2 `0xC6C00` = n 6 · X 16,26,38,48,64,96 · Y 255,237,196,145,99,77. Selected when r25 (gp-0x67c9 == 2) at 0x2A468/0x2A4C2.
The A5 equivalent is to rewrite these u8 tables to the dir-0 values (fadeB2 Y 255,255,212,185,154,51; fadeA2 X and Y). The
format is u8, so values ≤255 fit.

## 5. V37A lane-adjacent cells (A160 → A340, stock)
STEER_STATUS debounce u16: 0xC61C0/C2/C4 (1600/896/1280) → **0xC61D0/D2/D4 (12800/8960/11520)**. The A340 values are
~8–10× A160's, so the units probably differ (BELIEF). Bytes 0xC64B4..B7 (112,96,54,64) → **0xC6504..07** (same values).
DTC-0x49 gate 0xC64B8 (112) → **0xC6508** (112). Counters 0xC64E0/E1 → 0xC6530/31. EME step 0xC64DE (17) → **0xC652E**
(17, read at 0x29B7E). Method: lane alignment plus decompile. ⚠ On A340, `0xC64B8` is the **Kd speed-knot array**, not the
DTC gate. Never carry an A160 address across.

## 6. Not traced / open
- EME corridor ints/floats (V37A g), 0x14A/427 packers, the F181 string, D6's full cell set beyond §5, the D8k/D5k DampAxis cells: **not traced** (outside the lane).
- A free cal cell for A6, and the CRC-block membership of the A340 cave region: **open**.
- Variant selector's live value on the A340 car: unknown. It does not matter on stock, because all 12 variants are identical.
- The damper mode gp-0x67d0 has 2 `ld.bu`, 0 writers (raw scan) and boots 0, so it is unreachable as on A160 (register-indirect residual).
