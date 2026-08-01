---
name: reference_accord_r24_gainb_table_structure_and_priority_gate
description: FUN_0003ad74's four mode-indexed ROM-record pointer arrays fully enumerated (one array, not two, at 0xCC12C -- resolves the old 0xCC154/0xCC184 ambiguity); mode-10 records byte-read and blast-radius-confirmed private; r24's gain_B is a 4-way PRIORITY GATE (gp-0x671d / gp-0x683c / gp-0x671a-vs-cal5 / mode-table default), not unconditionally the mode table; CRC blocks identified; evaluation axis gp-0x6ac0 scale (4.7121 counts/deg/s) independently re-derived exact, plus the >=13001 fold-to-MAX-gain discontinuity confirmed via decompiler.
metadata:
  type: reference
---

# r24 gain_B table structure -- resolved 2026-08-01 for team-lead's mode-10 table question

Task: team-lead's own byte-read of pointer array bases `0xCC154`/`0xCC184` (index10/idx0 giving the
SAME value `0xD6AEC`) didn't reconcile -- looked like either two overlapping arrays or one array read at
two offsets. Also needed: exact mode-10 gain_B table content, blast radius, and whether curveA (the
ROM-record LERP) is unconditionally gain_B.

## 1. ONE array at 0xCC12C, not two -- CLOSED [EVIDENCE: FUN_0003ad74 disasm 0x3AD88-0x3ADC2]

`FUN_0003ad74` fetches FOUR pointer-array bases via literal immediates in the instruction stream:
`0xCBF5C` (array1, cross-axis pt X=640), `0xCC044` (array2, X=3200), `0xCC12C` (array3, X=6400), and
`tp+0xD214=0xCC214` (array0, X=0), each indexed by `mode*4` where `mode = *(byte*)(gp+0x63FD)` (a
POSITIVE gp displacement -- RAM, see #6). Each array is exactly **58 entries x 4 bytes = 0xE8**,
contiguous: `0xCBF5C -> 0xCC044 -> 0xCC12C -> 0xCC214 -> 0xCC2FC(end)`, confirmed by reading past the end
(byte content becomes an unrelated ascending run, not more pointers). `0xCC154 = 0xCC12C+4*10` (mode 10)
and `0xCC184 = 0xCC12C+4*22` (mode 22) are BOTH inside array3 -- not two arrays. The naive "0xCC154 as
array base, read 16 entries" reading was an artifact of reading past mode boundaries within array3, not a
real second table.

## 2. Mode-10's four records -- byte-read, EXACT match to the pre-existing golden-model numbers

Cross-axis breakpoints `tp+0x7010=0xC6010`: X=[0,640,3200,6400] (v65, confirmed). Cal `tp+0x713a=0xC613A=1159`.

| array (cross-axis pt) | pointer slot | record addr | X | Y |
|---|---|---|---|---|
| array0 (X=0) | `0xCC23C` | `0xD2B28` | [0,400,1500,3000] | [2151,2151,2049,1947] |
| array1 (X=640) | `0xCBF84` | `0xD2A74` | [0,400,1400,3000] | [3072,3072,2322,1536] |
| array2 (X=3200) | `0xCC06C` | `0xD2AB0` | [0,400,1500,3000] | [2561,2561,2247,1947] |
| array3 (X=6400) | `0xCC154` | `0xD2AEC` | [0,400,1500,3000] | [2305,2304,2149,1948] |

Record layout: 20-byte stride, `u16 count(=4); i16 X[4]; i16 Y[4]` (18 bytes payload + 2 pad).
**Blast radius**: whole-image LE32 scan, each of the 4 record addresses has EXACTLY 1 pointer reference
(its own array slot) -- private to mode 10, not shared with any other mode. **Float-mirror scan** (Y/1024
as float32, whole image): the 8 mode-10-distinctive non-round Y values (1947/1948/2049/2149/2151/2247/
2305/2322) -> ZERO hits. (1536/2304/3072 -> 2.25/2.25/3.0 DID hit elsewhere, but those are generic
round-number float constants unrelated to this table -- not a real mirror.)

## 3. gain_B is a 4-WAY PRIORITY GATE -- the mode table is the DEFAULT, not unconditional [EVIDENCE: FUN_0003aa2c 0x3ABFA-0x3AC20]

```
0x3ABFA  if (gp-0x671d != 0):        gain_B = cal 0xC6442 (=1024, r24-EXCLUSIVE, no r26 counterpart)
0x3AC04  elif (gp-0x683c != 0):      gain_B = cal 0xC6446 (=512)   -- DEAD, gp-0x683c has 0 writers image-wide
0x3AC0E  elif (cal(0xC64FA)=5 < gp-0x671a): gain_B = cal 0xC6440 (=2048)
0x3AC16  else (DEFAULT):             gain_B = mode-indexed ROM-record cross-interpolation (section 2)
0x3AC18  r8 = clamp(gp-0x4f62,+/-5120) * gain_B
0x3AC20  sar 0xa (stock) / 0x9 (V62-V65, the doubling patch)
0x3AC24-3C  deadband +/- cal(0xC61F6)=3
0x3AC3E  * polarity(gp-0x6752)
0x3AC42-54  clamp +/- 0x2000 -> r24
```
Curve-A (the mode-table LERP) is COMPUTED unconditionally every tick (the cross-interpolation runs at
`0x3AB98-0x3ABF8` regardless), but only KEPT as gain_B when all three override flags are clear. r26 has an
analogous but separate priority chain (own default = a FIXED, non-mode-indexed ROM-record cross-
interpolation at `tp+0x7A68` family; overrides `0xC6444`(gp-0x683c, dead)/`0xC643E`(same gp-0x671a-vs-cal5
test) -- r26 has NO gp-0x671d-equivalent private override).

**Gate-flag writer status:**
- `gp-0x671d`: **2 real `st.b` writers** -- `FUN_0003bcb2`@0x3BD2A (writes 0), `FUN_00041d56`@0x41EC6
  (writes r28; per [[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]], resolver/FOC-domain
  inputs, not LKAS). **LIVE**, structurally reachable, not proven to fire in any specific scenario this
  session.
- `gp-0x683c`: **ZERO `st.*` writers** image-wide (`search_instructions`, substring "st" catches st.b/h/w/
  sst.b/h/w, 183429 instrs, truncated:false). **DEAD, confirmed** -- matches prior record; both `0xC6446`
  (r24) and `0xC6444` (r26) are unreachable via this shared flag.
- `gp-0x671a`: 1 real writer `FUN_000428d4`@0x42A12 (`st.b r7,-0x671a,gp`), a debounce/hysteresis state
  machine whose output is clamped against `cal(0xC64FA)=5` on SOME but not all decompiled branches.
  **NOT resolved** whether it can exceed 5 in practice -- flagged open, don't assert `0xC6440` dead or live.

## 4. gp+0x63fd (mode selector) is RAM, not statically readable from flash

6 runtime `st.b`/extended-st writers found: `FUN_00042692`@0x426AE, `FUN_00042746`@0x4279E/27C4/27FC/
42822 (4 sites), `FUN_0004a798`@0x4A7FC (6-byte extended encoding). "mode=10 on this car" is inherited
from prior sessions (presumably telemetry or trace of these writers), NOT re-derivable from a static image
byte read -- the exact match of `0xD2AEC`'s content to previously-reported numbers is strong circumstantial
corroboration, not independent proof. If re-verification is ever needed, decompile `FUN_00042746`/
`FUN_0004a798`.

## 5. CRC blocks (v65, all currently PASS -- confirms boundaries)

| edit target | block | range | CRC word |
|---|---|---|---|
| mode-10 records (0xD2A74/AB0/AEC, 0xD2B28) | #41 | `[0xD2000,0xD2FFC)` | `0xD2FFC` |
| pointer arrays (0xCBF5C..0xCC2FC) | #47 | `[0xC7000,0xCCFFC)` | `0xCCFFC` |
| fixed gain cals (0xC6440/42/44/46, 0xC643E, 0xC61F6, 0xC613A, 0xC64FA) | #48 | `[0xC6000,0xC6FFC)` | `0xC6FFC` |

Block 48 = the documented bootloader-bridge block (`verify_bootloader_crc.py`) -- confirmed still
individually CRC-checked before the bridge kicks in for lower blocks. A pure Y-value edit to the mode-10
records only touches block #41; a fixed-cal-only edit only touches #48.

## Cal values (v65)
`0xC61F6`(r24 deadzone)=3, `0xC6440`=2048, `0xC6442`=1024, `0xC6444`=512, `0xC6446`=512, `0xC643E`=1536,
`0xC64FA`=5(byte), `0xC613A`=1159, cross-axis `0xC6010`=[0,640,3200,6400].

## 6. Evaluation axis gp-0x6ac0 -- exact scale (4.7121 counts/deg/s) and the >=13001 fold-to-MAX-gain discontinuity [EVIDENCE, 2026-08-01 session 2]

`gp-0x6ac0 = abs(EMA_state) >> 10` inside `FUN_00041464`, the SAME EMA state as `gp-0x6abe = EMA_state >> 10`
(per [[reference-accord-common-mode-rate-signal-6abe-6ac0-full-chain]]) -- rectified twin, IDENTICAL scale.

**Scale, independently re-derived (not just cited) via a fresh decompile of `FUN_00040a50`:**
```c
*(short *)(gp-0x69ea) = -*(short *)(gp-0x6a56);   // EXACT negation, both live branches, no extra scale
```
Combined with `FUN_0003f776`'s `gp-0x6a56=clamp(pol*(gp-0x6abe*48*1159)>>15,+/-12000)` and the CAN 0x14A
builder's `>>3` before packing (scale -1.0 deg/s): `gp-0x6abe = deg/s * 262144/55632 = deg/s * 16384/3477
= deg/s * 4.71210813920046...` -- **exact rational reproduction of the kit's "4.7121 counts/deg/s" figure**
to 4 decimal places. Applies unchanged to `gp-0x6ac0` (same signal, same scale). Breakpoints: 400->84.888,
1500->318.329, 3000->636.658, 1400(array1 only)->297.107 deg/s.
**Open loose end**: the CAN 0x18F(399) route (`raw=-gp-0x6a56` direct, no `>>3`, scale -0.1) gives a
DIFFERENT implied scale (~5.89 counts/deg/s) -- the two CAN messages' rate fields don't cross-check to a
clean multiplier despite "10x finer copy" framing. Not chased (needs `FUN_0002191e`'s exact packing).
Doesn't affect the 4.7121 answer, which is independently reproduced via the SAME chain it was originally
cited from.

**The >=13001 (0x32C9) fold -- CONFIRMED via decompiler ground truth (raw disasm `cmovc` operand-order
reading is a trap here, I mis-read it once and want to flag that for future sessions -- ALWAYS verify a
cmov's direction against the decompiled C, not the raw operand order):**
```c
sVar20 = *(ushort *)(gp-0x6ac0) * (ushort)(*(ushort *)(gp-0x6ac0) < 0x32c9);
```
`rateKey = gp-0x6ac0` if `<13001`, **else 0**. One shared value feeds BOTH r24's (`gp-0x6e40/38`) and r26's
(`gp-0x6e30/28`) LERP evaluations. `13001/4.71211 = 2759.06 deg/s`. Since every mode-10 record's own top
breakpoint (X[3]=3000 or 1400) sits at 636.7/297.1 deg/s -- far below 2759 -- the LERP is already pinned at
the record's low-gain endpoint Y[3] for the whole 637-2759 deg/s range (standard clamp-to-boundary). At
2759 deg/s exactly, rateKey snaps to 0 -> re-evaluates at X[0]=0 -> Y[0], **every record's HIGHEST gain**
(Y monotonic decreasing X0->X3 in all 4 mode-10 records). **A real step discontinuity** (e.g. array1:
1.5x->3.0x, a 2x jump) at fault/glitch-level rate (~7.7 wheel rev/s), not reachable in ordinary driving.

## Related
[[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]] -- established gp-0x671d's own resolver/
FOC-domain inputs; this session adds it to r24's priority-gate structure explicitly.
[[reference-accord-v61-taps-gain-priority-and-sign-apples-to-apples]] -- earlier "gain-arm priority
decoded" note this session makes address-exact and adds the pointer-array/record/CRC layer that memory
didn't have.
[[reference-accord-common-mode-rate-signal-6abe-6ac0-full-chain]] -- gp-0x6ac0 (rateKey axis) = |gp-0x6abe|,
same producer, same scale -- the evaluation axis for all 4 mode-10 records.
