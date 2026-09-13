# ADVERSARIAL PASS — V293, SURFACE A: ARITHMETIC

**Agent:** `advA3`, a SUBAGENT of the orchestrator (`main`). **Study/analysis only.** Nothing flashed,
nothing sent on any bus, no build script edited, no commit, no artifact touched.

**Charter:** the FAIL criteria in `docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md` §"A — ARITHMETIC"
(A1–A4), fixed before the image existed. My explicit job was to make V293 **fail**.

**Independence.** Every number below is re-derived from the **built image**. I wrote my own V850E2
little-endian decoder, my own gp/tp two-encoding scanner, my own LERP-record reader and my own integer
mirror of the PID. I did **not** read `build_v293_tva.py`'s constants, the design doc's numbers, or the
orchestrator's brief for any value. Ghidra (`code.bin`, the stock dump — the only open program) was used
for **structure** only: the decompile of `FUN_00028ea6` and three byte-level arbitrations, each named.

Claims are marked **[E]** EVIDENCE (with method) or **[B]** BELIEF.

---

## 0. VERDICT

| clause | verdict | the decisive number |
|---|---|---|
| **A1** fb operand identically 0; no other rate path; D ≡ 0 two ways; Ki = 0 | **PASS** | clamp block simulated from its own decoded bytes over **4,023 int32 states** including ±2³¹ and ±0x7FFFFFFF: **0 states with a non-zero operand**. D ≡ 0 by **each cell alone**. `gp-0x680a` = **0 writers, 3 methods**. |
| **A2** surface linear to the rail; rail = V282's; P does not rail below idx 238 | **PASS** | rail **2461 on both**, difference **0 counts**, ratio **1.000000**. P first rails at **idx 239**. Max linear residual **2.19 counts** on a 0→2459 span, fully explained by the map lerp's own quantisation. |
| **A3** widths, narrowing stores, all 28 Kp/Kd records | **PASS** | worst `E·Kp` = 32·1128·120 = **4,331,520**, **495× inside** int32. All **28/28** Kp records `[120]×5`, all **28/28** Kd records `[0]×4`, **no pointer aliasing**. `&0xFFFF` provably inert. |
| **A4** cave rungs b3–b7, decoders, 0x1AB tap byte-identical to V282 | **PASS** | cave `0xC4B34..0xC4C00` sha8 **`b55bbaf5` = b55bbaf5**; packer `0x55DF0..0x55E12` **`48343ead` = 48343ead**; **0 bytes changed in the whole code region** `[0x13000,0xC0000)`. b3 reads `ld.w gp-0x3680` — the aliased bit, **not** V292's fb-state rung. |

**SURFACE A RETURNS: NO DO-NOT-FLASH.**

**But the pass is not clean.** Three things the pre-registration states as fact are **wrong or
incomplete**, and one consequence of the build is understated. None of them trips an A clause; all four
change what the close-out page and the operator brief may say. They are §7 and they are not optional.

---

## 1. PROVENANCE

| artifact | sha256 |
|---|---|
| `_v293_V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin` | `f75e77cf0ba9d93b5302196877e59c6a41deae4983afc09ade99c5b766e1db17` |
| `39990-TVA,A160-V293-…-0x13000-0x100000.rwd` | `ac4723865378ff376086174bbb82fcabf07c435fae5bf5706a6ef83caa6e71ba` (986,042 B) |
| base `_v282_…_plain_image.bin` | `0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe` |

Both V293 hashes **re-read and unchanged** across two reads > 60 s apart (mtime 14:57:40, re-read
15:06:51). **Exactly one** `*v293*` image and **exactly one** `*V293*` rwd on disk. **[E]**

### 1.1 Tool validation — every scan positively controlled before any null was trusted

My decoder independently reproduces the record's `0x28F86–0x28FBE` listing **instruction for
instruction**, including the two traps that have cost this kit wrong answers: `gp = r4` / `tp = r5`
(not r30), and `0x3F` with `hw2[0] = 0` being **`mul`** (Format XI), not a load.

My scanner's 10 positive controls, run **on the V293 image itself**, all PASS:

| control | result |
|---|---|
| `ld.h gp-0x6a56` @`0x28F4C` | PASS — **30** accesses (the count `search_instructions` undercounts as 25) |
| `ld.w` / `st.w gp-0x3d30` @`0x28F7C` / `0x28FA8` | PASS |
| `ld.bu gp-0x3d2c` @`0x28F66` — **odd displacement**, the hw1-bit-5 parity trap | PASS |
| `ld.h tp+0x73e8`, `ld.hu tp+0x73ea`, `ld.hu tp+0x72e6` | PASS |
| `st.h gp-0x6b38` @`0x2A23C` | PASS |
| **6-byte disp23** `gp-0x4f60` @`0x4C784` | PASS — **76** accesses, the kit's recorded true total |
| `st.h gp-0x6a34` @`0x290CA` | PASS |

⭐ **A decoder trap I hit and had to fix, worth adding to `firmware-decompile`.** My first decoder read
`bf ff 64 3c` (inside the 0x1AB packer) as `ld.bu 0x3C65[lp],lp`. Ghidra says **`jarl 0x49A5A,lp`**.
The opcode fields genuinely collide: `ld.bu` is bits[10:5] = `0b11110x`, `jarl`/`jr` is bits[10:6] =
`0b11110`, so **bits[10:6] cannot distinguish them**. The disambiguator is **`hw2` bit 0: `ld.bu`
requires `hw2[0] = 1`; `hw2[0] = 0` with that opcode field is `jarl`/`jr`.** With the fix I re-checked
every 4-byte word in the `0x14A` cave: **none is a `jarl`**, so my cave decode in §5 stands. This is the
same family as the recorded `jarl disp22 is 0x1E not 0x1B` trap, and it bites in the other direction.

---

## 2. A1 — THE FEEDBACK OPERAND, D, AND EVERY OTHER RATE PATH

### 2.1 The cells, read from the image

`0xC62E6` (fb output clamp) **46080 → 0** · `0xC61B6` (D clamp) **10240 → 0** · Kd bank, all 28
records **→ 0** · `0xC63E6` (Ki) **0, unchanged**. **[E]**, Python LE byte reads.

### 2.2 The clamp block, decoded from the V293 image itself — byte-identical to V282

```
28F96  ld.hu  0x72E6[tp],r13     C = [0xC62E6]   (ZERO-EXTENDED: 0 reads as 0, no sign trap)
28F9C  ld.hu  0x72E6[tp],r14     C again
28FA2  add    r7,r9              s_new
28FA4  add    r9,r26             out = s_old + s_new      <- the two-sample sum
28FA6  cmp    r13,r26            flags of (r26 - C)
28FA8  st.w   r9,-0x3D30[gp]     ** THE STATE STORE — unconditional, before any branch **
28FAC  ble    28FB2              taken iff r26 <= C  (signed)
28FAE  mov    r14,r26            out := +C
28FB0  br     28FBE
28FB2  subr   r0,r14             r14 := -C
28FB4  cmp    r14,r26
28FB6  bge    28FBE              taken iff r26 >= -C -> unchanged
28FB8  ld.hu  0x72E6[tp],r26
28FBC  subr   r0,r26             out := -C
28FBE  mov    r26,r16            the clamped feedback
```

**Proof that `r26 ≡ 0` for every int32 state, with `C = 0` — exhaustive by case, not by sampling:**
`r13 = r14 = 0`. The three exits are
1. `r26 > 0` → `mov r14,r26` → **0**;
2. `r26 < 0` → `ld.hu`+`subr` → `−0` = **0**;
3. **unchanged** — but that exit requires *both* `r26 ≤ 0` (the `ble`) *and* `r26 ≥ −0` (the `bge`),
   i.e. `r26 = 0`. **The only state that survives unchanged is already zero.**

**Check [E]:** I simulated the block from its own decoded branch semantics over **4,023 states** —
`−2³¹`, `−2³¹+1`, `±0x7FFFFFFF`, `±10⁶`, `±46079/±46080/±46081`, `±1024`, `±3/±2/±1`, `0`, and the full
contiguous run `−2000…+2000`. **Non-zero results: 0.** The same harness on **V282** (`C = 46080`)
returns **4,012 non-zero** — so the check is *capable of failing* and its null is real, not vacuous.

**`0x80000000` specifically:** `cmp` gives S=1, OV=0 ⇒ `ble` taken ⇒ `bge` not taken ⇒ falls to
`ld.hu`/`subr` ⇒ **0**. No overflow arm exists, because `subr r0,r14` with `r14 = 0` is `0`.

**The state store still runs. [E], two ways.** (i) `st.w` sits at `0x28FA8`, *between* the `cmp` and the
`ble`, and V850 stores do not write PSW, so the compare's flags survive it. (ii) I scanned every
Format-III branch and `jr`/`jarl` in `[0x28E00,0x2A300)` for a target landing inside
`0x28F88..0x28FA8`: **none** (positive control — the scanner finds `0x28FAC → 0x28FB2`). The head of the
filter is straight-line; **`0x28FA8` cannot be skipped.** The store writes `r9` = `s_new`, computed
*before* the clamp, so zeroing `C` does not feed back into the state. State bound: `a = 923`, pole
`0.901`, `|s| ≤ 1560·12000/101 = 185,346`, `|a·s| ≤ 1.71e8` — **12.6× inside int32.**

### 2.3 D ≡ 0, two independent ways — each cell **alone**

| configuration | cells tested | non-zero D |
|---|---|---|
| **Kd = 0 (image) with V282's D clamp 10240** | 595 (17 ΔE × 35 idx) | **0** |
| **D clamp = 0 (image) with V282's Kd = 128** | 17 ΔE | **0** |
| both as built | 595 | **0** |

ΔE grid spans `±2³¹`, `±10⁸`, `±768000` (the `E_prev` plausibility window edge), `±33024` (the largest
`32·sp`), `±1046` (the measured command-slew step), `±3`, `±1`, `0`. Kd walked over **every** idx 0–240:
the record returns **`{0}`** — one value. **[E]**

The D clamp uses the **same three-arm idiom** as the fb clamp, so `clamp(v, 0) = 0` for all int32 by the
identical case argument; verified at `±2³¹`, `±1`, `0`.

### 2.4 Ki, the deadband and the I clamp

`Ki = [0xC63E6] = 0` **[E]**. The accumulator update is `I = clamp((I_state>>3) + ((exc·Ki)>>3), ICL)`;
with `Ki = 0` the increment is identically 0 and `I_state` boots to 0 (`.data` source flash — see §2.5),
so **`I ≡ 0` for the life of the ECU**. The deadband `0xC62E4 = 4` and the I clamp `0xC61BA = 10240`
therefore **cannot matter**: they act only on a term that is already zero. Both are byte-identical to
V282 anyway.

### 2.5 Every OTHER path from the wheel rate — censused on the V293 image

| cell | accesses | readers | writers |
|---|---|---|---|
| `gp-0x6a56` (the PID's rate operand) | **30** | 26, of which **exactly one — `0x28F4C` — lies inside the LKAS PID** `[0x28EA6,0x2A300)` | 4, all in the producer `FUN_0003f776` |
| `gp-0x4ca6` (lockstep mirror) | 5 | `0x3F78E` | 4, all in the producer |
| `gp-0x6a34` (`\|fb>>5\|`) | 3 | `0x2A0CA` (the damper mode), `0x2AFAE` (dead twin) | `0x290CA` |
| `gp-0x3d30` (fb filter state) | 2 | `0x28F7C` | `0x28FA8` |
| **`gp-0x680a`** (damper-mode key) | **2 — both `ld.bu` READS** (`0x29A68` live, `0x2A96A` dead twin) | — | **ZERO** |
| `gp-0x6b38` (delivered lane torque) | 7 | `0x2B418` (dead twin), `0x4E8D2`, `0x4E8E2`, `0x55DF0` (the 427 tap), `0xC4B40` (the cave) | `0x2A23C` (live), `0x2A934` (dead twin) |

**[E]** — my two-encoding scan (disp16 + 6-byte disp23), 10/10 controls PASS, **on the V293 image**.

🛑 **The dead viscous-damper mode at `0x2A0C6` is unreachable on the BUILT V293 image — three
independent methods:**
1. `gp-0x680a`: **zero writers** in any encoding, disp16 or disp23.
2. **LE32 literal scan** of the whole image for its absolute address `0xFEDF17F6`: **zero hits** — so no
   `mov imm32,reg` + register-indirect store can reach it either. (This closes the residual the tracer
   left open as BELIEF.) Same scan on `gp-0x6a34` (`0xFEDF15CC`) and `gp-0x6a56` (`0xFEDF15AA`): zero.
3. **`.data` boot value:** the copy loop `0x1476C–0x14794` walks flash `[0x86260,0x8AB18)` into RAM from
   `0xFEDF11B0`; `gp-0x680a` ← flash **`0x868A6` = `00`**. Positive control on the same mapping:
   `gp-0x6AB0` ← flash `0x86600` = **`88 02 88 02`**, the known non-zero cell — so the mapping is
   verified, not assumed.

⇒ `gp-0x680a ≡ 0`; the `== 1` branch never executes; `gp-0x6a34`'s only live consumer is dead in
practice. **The wheel rate reaches the delivered lane torque by NO path on V293.**

Also boot-verified on this image: `gp-0x3d30` ← `0x89380` = `00 00 00 00`; `gp-0x3d2c` ← `0x89384` =
`00`; `gp-0x6b2c` (the `T` addend `r11`) ← `0x86584` = `00 00`.

**A1 → PASS.**

---

## 3. A2 — THE DELIVERED SURFACE

### 3.1 The integer mirror, re-derived from the decompile of `FUN_00028ea6`

```python
sp     = sign(cmd) * LERP_map(idx)                      # 0xC9A88[7] -> 0xE502C
E      = 32*sp - fb                                     # 0x29D78 sub r26,r16 ;  fb == 0
I      = 0                                              # Ki == 0
P      = clamp((E*Kp) >> 8, [0xC61BC]=15360)            # 0x29E36 mul, 0x29E3E sar 0x8
D      = clamp((dE*Kd) >> 3, [0xC61B6]=0)               # == 0
S      = (I >> 7) + P + D                               # 0x29F18/1E/24
factor = ((tapAB * tapCD) & 0xFFFF) >> 8                # ONE stage - see 7.1
S      = (factor * S) >> 8
S      = clamp(S, [0xC61BE]=15360)                      # 0x2A13E..0x2A160
ln     = ((992*L) >> 10) + ((S*507) >> 10);  y = (L + ln) >> 5;  L = ln     # 0x2A174/0x2A184
yr     = sxh((y * ramp) >> 15)                          # 0x2A1E6 mul, 0x2A1EA sar 0xf, 0x2A1EC sxh r9
T      = clamp(((0 + yr) * pol * gain) >> 15, [0xC61B4]=3072)   # gain = [0xC6CD0] = 5346
```

The LERP record layout (`u16 N | N×X | N×Y | pad`, Y start = `base+2+2N`) was re-derived from the
**decompiler's own pointer arithmetic**, not taken from any kit document. The interior interpolation is
`(Y[j]−Y[j−1])·(x−X[j−1]) / (X[j]−X[j−1]) + Y[j−1]` with **C truncation toward zero**, guarded by a
**strict** `X[0] < x` on the low side.

Two byte-level arbitrations by Ghidra, both confirming my decode:
- `0x2A1EE` is **`ld.h 0x7CD0[tp],r7`** — a **signed** halfword load of `0xC6CD0 = 5346` (V282's
  repoint; stock reads `tp+0x746c`). Read from the image's own displacement field, not assumed.
- `0x2A1EC` is **`sxh r9`** (`e9 00`), the `(int)(short)` narrowing Ghidra renders at the ramp stage.
  My first decoder called it `mulh r9,r0`; `0x00E0|reg` is `sxh`.

### 3.2 The result

| | V282 (fb = 0) | V293 |
|---|---|---|
| **rail T** | **2461** | **2461** |
| **difference** | — | **0 counts, ratio 1.000000** |
| **P first rails at idx** | 116 | **239** |
| linear fit over the sub-rail span | `T = 21.351·idx − 2.03`, max resid 3.79 | **`T = 10.336·idx − 1.89`, max resid 2.19** |

**Is 2.19 counts "within the integer floor"? [E], yes, and it is accounted for, not asserted.** The map
record's own lerp deviates from its best-fit line by up to **0.828 counts of `sp`**, and the chain gain
is `dT/dsp = 15 × 254/256 × 0.99003 × 5346/32768 = 2.404 counts of T per count of sp`. That predicts
**1.99 counts** of T residual from the map alone; the remaining ~0.2 is the three downstream floors
(`>>8` taper, `>>5` lag, `sar 15` gain). The surface is linear to the rail to within its own
quantisation.

| idx | V282 T | V293 T | ratio |
|---|---|---|---|
| 1 | 19 | 9 | 0.474 |
| 10 | 213 | 102 | 0.479 |
| 32 | 685 | 331 | 0.483 |
| **58** (measured p90 demand) | **1236** | **598** | **0.484** |
| 96 | 2051 | 992 | 0.484 |
| 116 | 2461 | 1196 | 0.486 |
| 160 | 2461 | 1653 | 0.672 |
| 200 | 2461 | 2067 | 0.840 |
| 238 | 2461 | 2459 | 0.999 |
| **239 / 240** | **2461** | **2461** | **1.000** |

**P rails at idx 239, not below 238 → PASS.** At `sp = 1027` (idx 239) `P = 15·1027 = 15405 ≥ 15360`;
at `sp = 1023` (idx 238) `P = 15345 < 15360`. `Kp = 120` makes `P = 15·sp` **exactly** (3840 = 15·256,
no floor loss).

**A2 → PASS.** See §7.2 and §7.4 for what this table does **not** say.

---

## 4. A3 — WIDTHS, NARROWING STORES, ALL 28 SLOTS

| check | result |
|---|---|
| worst `E·Kp` over every reachable slot | `32 × 1128 × 120` = **4,331,520**; int32 limit 2,147,483,647 ⇒ **495× margin**. (Note: the max map ceiling is **1128** on slots 8/9, not the 1032 of slot 7 — the brief's `32·1032·120` understates it, harmlessly.) |
| `(E·Kp)>>8` worst | 16,920 vs the P clamp 15,360 — the clamp binds on slots 8/9 too; no wrap |
| taper `&0xFFFF` | max product `255 × 255 = 65,025 < 65,536` ⇒ the mask is **provably inert** |
| `0xC62E6` read width | **`ld.hu`** at all three sites ⇒ 0 zero-extends to 0; **no sign trap** |
| `0xC61B6` read width | **`ld.hu`** at all four live sites, same |
| narrowing store `sxh r9` @`0x2A1EC` | `y` at `S = 15360` is **15,208**; `(y·0x8000)>>15 = 15,208` — **inside int16 by 2.15×**; no wrap |
| `T` pre-clamp at that `y` | `(15208 × 5346) >> 15` = **2481** vs the output clamp **3072** — the clamp does **not** bind; the rail is set by the **P clamp**, not `0xC61B4` |
| **Kp, all 28 records** | **`[120,120,120,120,120]` on every one of slots 0…27** — no slot left at 205/248/266/307 |
| **Kd, all 28 records** | **`[0,0,0,0]` on every one of slots 0…27** — including the **20 slots that carried 64, not 128** (slots 2, 5, 10–27). The pre-registration's "Kd bank (all records) 128 → 0" describes only 8 of the 28; the build nevertheless zeroed all of them. |
| pointer aliasing | **none** — 28 distinct Kp pointers, 28 distinct Kd pointers, 28 distinct map pointers |
| pointer families | all **8** families (map, Kp, Kd, tapA, tapB, tapC, tapD, LIM) **byte-identical to V282** |
| map / taper / LIM **records** | `0xE502C`, `0xE55A4`, `0xE56F4`, `0xE54FC`, `0xE564C`, `0xE51A8` all **byte-identical to V282** |

⚠ **A genuine, small sign defect — present, bounded, and also present on V282.** `sar` floors toward
−∞, so the negative side is **not** the mirror of the positive side:

```
T(+240) = +2461      T(-240) = -2463        asymmetry = 2 counts
  of which:  output-lag floor  y = -15092 vs +15088   -> 1 count of T
             gain  sar 15      (-15088*5346)>>15 = -2462 vs -((15088*5346)>>15) = -2461  -> 1 count
```

**2 counts out of 2461 = 0.08 %.** It is inherent to `sar`, unchanged in kind by V293, and it is **not**
the "one-count" figure — it is **two**, because the output lag contributes one as well as the gain.
Anyone quoting a closed form for the negative side should use the floor, and should say **two**.

**A3 → PASS.**

---

## 5. A4 — THE CAVE, ITS RUNGS, AND THE 0x1AB TAP

### 5.1 Byte identity — sha8 over each region, V293 vs V282

| region | V293 | V282 | |
|---|---|---|---|
| `0x14A` cave `0xC4B34..0xC4C00` | `b55bbaf5` | `b55bbaf5` | **IDENTICAL** |
| cave + surround `0xC4B00..0xC4C40` | `f91b4f88` | `f91b4f88` | **IDENTICAL** |
| `0x1AB` packer `0x55DF0..0x55E12` | `48343ead` | `48343ead` | **IDENTICAL** |
| `0x1AB` hook region `0x55C00..0x55E40` | `113aa0a4` | `113aa0a4` | **IDENTICAL** |
| the whole PID body `0x28E00..0x2A300` | `662732ee` | `662732ee` | **IDENTICAL** |
| fb clamp block `0x28F86..0x28FC0` | `a21ee434` | `a21ee434` | **IDENTICAL** |
| gain load `0x2A1EE..0x2A1F2` | `f4926354` | `f4926354` | **IDENTICAL** |

🛑 **Stronger, and this is the one that settles it: `0` bytes differ anywhere in the code region
`[0x13000, 0xC0000)`.** V293 is **cal-only**. All 378 changed bytes lie in `[0xC0000, 0x100000)` and
every one is attributed:

| group | bytes |
|---|---|
| named cells (`0xC61B7`, `0xC62E7`, `0xC6446–47`) | 4 |
| Kp records, 28 slots × 5 knots (1 B where 205/248, 2 B where 266/307) | 240 |
| Kd records, 28 slots × 4 knots (1 B each) | 112 |
| block CRC trailers `0xC6FFC`, `0xE4FFC`, `0xE5FFC`, `0xE6FFC`, `0xE7FFC`, `0xE8FFC` | 22 |
| **total** | **378 — zero unattributed** |

### 5.2 The rungs, decoded from the V293 image

```
C4B34  |gp-0x6ADA| -> r7 ;  C4B40  |gp-0x6B38| -> r6 ;  cmp ; mov 0x4,r7 ; bge ; shl 0x4
       andi 0xBF  ->  ** b6 = ( |gp-0x6ADA| >= |T| ) **                      reads gp-0x6b38
C4B62  |gp-0x6ADA| -> r7 ;  C4B6E  |gp-0x6B94| -> r6 ;  cmp ; mov 0x2,r7 ; bge ; shl 0x4
       andi 0xDF  ->  ** b5 = ( |gp-0x6ADA| >= |gp-0x6B94| ) **
C4B92  ld.h gp-0x6B4C  -> +8   ;  C4B9C  ld.h gp-0x6ADA -> +1  ;  shl 0x4
C4BA8  ld.w gp-0x3680  -> +8   ;  andi 0x67
       ->  ** b7 = sign(gp-0x6B4C) ·  b4 = sign(gp-0x6ADA) ·  b3 = sign(gp-0x3680) **
C4BC0  mov 0x3 ; shl 0x6 ; andi 0x3F on gp-0x1511  ->  the version marker, bits 6-7 = 3
```

🛑 **b3 reads `ld.w gp-0x3680`** (bytes `24 37 81 c9`) — **V282's aliased bit.** V292's edit was
`0xC4BAA: 81 c9 → d1 c2`, repointing it to `ld.w gp-0x3d30` (the fb state). V293 carries **`81 c9`**.
**b3 is NOT the V292 fb-state rung. [E]**, byte read plus the region hash.

### 5.3 The tap source, and the identity's residual

The stock-vs-V293 diff over `0x55C00..0x55E60` is **35 bytes in 3 clusters**, and it pins the alignment
beyond argument: stock has `ld.h -0x6c18,gp,r6` at `0x55DF0`; the kit patched **only its displacement
halfword at `0x55DF2`** (`e8 93 → c8 94`). So the instruction is

```
55DF0  ld.h  -0x6B38[gp],r6        ** THE TAP SOURCE IS gp-0x6b38 = T **   [E]
55DF4  mov   r6,r9
55DF6  jarl  0x49A5A,lp            -> r10 = |r6|   (Ghidra: cmp/cmovge/subr, an abs helper with an
                                       INT_MIN guard)
55DFA  mov   r10,r6 ;  55DFC  sar 0x3,r6           r6 = |T| >> 3
55DFE  shr   0x1F,r9 ; 55E00  shl 0x9,r9 ; 55E02  or r9,r6      bit 9 = sign(T)
55E04  movea 0x3FF,r0,r8                            the 10-bit field mask
```

⇒ **the wire field is `(|T|>>3) & 0x1FF` in bits 0–8 and `sign(T)` in bit 9.**

**The identity's expected residual. [E]** `|T| = 8·field + r`, `r ∈ [0,7]`, so **`|tap·8|` under-reads
`|T|` by 0 to 7 counts, mean 3.5** — a **one-sided negative bias**, never an over-read. Measured on the
V293 surface: idx 1 → −1, idx 10 → −6, idx 58 → −6, idx 116 → −4, idx 240 → −5. At the rail that is
**0.20 %**. **No saturation**: `|T| ≤ 3072` (the output clamp) ⇒ `|T|>>3 ≤ 384 < 512`, so the 9-bit
magnitude field has **25 % headroom** and cannot clip.

**A4 → PASS.**

---

## 6. WHAT A FAIL WOULD HAVE LOOKED LIKE

Written so this pass cannot be called theatre. Each of these was a live possibility and each was
checked, not assumed:

- the fb clamp read as **`ld.h` (signed)** anywhere — then `C = 0` would still be 0, but a *negative* C
  would invert the arms. **Checked: all three reads are `ld.hu`.**
- a branch landing **inside** `0x28F88..0x28FA8`, letting the state store be skipped — the filter would
  freeze and the b3 liveness control would go dead. **Checked: none.**
- **any** writer of `gp-0x680a`, in any of three encodings, or its address appearing as an LE32 literal
  — the viscous damper would deliver `−sign(fb)·LERP` with the loop nominally open. **Checked: none.**
- a Kp or Kd record **left unflattened** on a reachable slot, or two slots **aliasing** one pointer — a
  selector that is ever not 7 would land on a 307-gain surface with zero feedback. **Checked: 28/28
  flattened, no aliasing.**
- the rail moving by ≥ 1 count, or P railing below idx 238. **Checked: 0 counts, idx 239.**
- one code byte anywhere. **Checked: zero in `[0x13000,0xC0000)`.**

---

## 7. FINDINGS THAT DO NOT TRIP AN A CLAUSE BUT MUST NOT BE DROPPED

### 7.1 🛑 The taper is ONE stage, not two — the pre-registration's A2 premise is wrong as written

A2 says *"the always-on `((255·255)&0xFFFF)>>8 = 254/256` taper **and** the live speed taper"*, as if
these are two stages in series. **The bytes say one.** The decompile of `FUN_00028ea6` (Ghidra, the
lines feeding the `0xC61BE` clamp) gives exactly:

```c
factor = ((  (A_lerp * bVar1 + B_lerp * !bVar1)
           * (C_lerp * bVar1 + D_lerp * !bVar1)  ) & 0xFFFF) >> 8;
S      = (factor * S) >> 8;
```

`A`/`B` walk the bar-derivative axis, `C`/`D` walk the speed axis, **one selector picks both halves**,
and the product is taken **once**. The famous 254/256 is simply that single stage's value **at rest**,
where both halves return 255. There is **no separate always-on stage on top of the speed taper**.

**Consequence:** the number 2461 is the **zero-speed** rail and nothing else. Every "delivered rail"
sentence on the close-out page must say at what speed.

### 7.2 🛑 The live speed taper is **D** (`0xCBBC4`), not C — the kit memory is right, the tracer is not

The selector is `bVar1 = (*(char*)(gp − 0x6803) == 2)`, assigned on the LKAS command path and dominating
the earlier speed-plausibility assignment. `gp-0x6803` is the `0x0E4` `SET_ME_X00` field, which
openpilot sends as **0** ⇒ `bVar1 = false` ⇒ the taper picks **B × D**. `A ≡ B` byte-identically, so
only the speed half matters. **[E]** for the selector expression and the byte reads;
**[B]** for "openpilot sends 0", which rests on the kit's own `0x0E4` handler record and on
`accord-the-override-taper-arm-is-selected-by-a-0xe4-field-openpilot-sends-0`, both of which I did not
re-derive from the wire this session.

**Both tables, and the delivered rail under each** (V293, idx 240; C and D are byte-identical to V282,
so this is a **pre-existing** property, not something V293 changes):

| speed | C (`0xCBAE4`) rail | **D (`0xCBBC4`) rail — LIVE** |
|---|---|---|
| 0 | 2461 | **2461** |
| 10 m/s (36 km/h) | 2190 | **2151** |
| 20 m/s (72 km/h) | 1395 | **736** |
| 30 m/s (108 km/h) | 581 | **736** |

**[B]** on the axis unit being km/h — the knots (C `[24,45,64,80,96,112]`, D `[16,26,38,48,64,96]`) are
read from the bytes **[E]**, but I did not derive `gp-0x6a5e`'s scale this session. If the unit were
something else the rows shift; the **C-vs-D difference does not**, and at 20 m/s the two tables differ
by **1.90×**. If anyone is going to quote a delivered torque at highway speed, this choice has to be
right, and the tracer's open item §7.4 is now closed in the other direction.

### 7.3 The rail read from the bytes is **2461**, not the record's 2462

The output lag is a floor-based IIR, so it has a **continuum of fixed points** — at `S = 15240` any
`L ∈ [241409, 241471]` is stationary. From a cold start the trajectory settles on the **smallest**,
`L = 241409`, giving `y = 15088` and `T = 2461`. The record's 2462 corresponds to `L ≥ 241440`, which a
cold start does not reach. **The rail is therefore trajectory-dependent by 1 count**, which is exactly
why the A2 clause must be — and was — scored under a **matched trajectory** for both images. Under that
matching the difference is **0**.

### 7.4 ⭐ The rails match; the **operational** authority does not. V293 delivers ~48 % of V282 below idx 238.

This is the finding I most want on the page, because the pre-registration's own wording invites the
wrong reading. A2 says *"the same P-clamp rail as V282, linear below it"* — both clauses are **true**,
and together they are easy to hear as *"same authority"*. They are not.

**V293's slope is 10.34 counts of T per idx; V282's is 21.35. For every idx from 1 to 237, V293
delivers less — and for idx ≤ 116 it delivers 0.474–0.486 of V282.** They meet only at idx 239–240,
which requires demand at the very top of the map. At the record's own **measured p90 demand, idx 58**,
V293 delivers **598** where V282 delivers **1236** — **×0.484**.

That is the arithmetic consequence of `Kp 248 → 120` at a fixed P clamp: the knee moves from idx 116 to
idx 239, and the price is half the gain everywhere below it. Whether that is the intended trade is a
design question, not mine. **But it is not "authority unchanged", and a page that shows only the rail
will mislead the operator about what he is about to drive.** The honest sentence is: *"the peak is
identical and now needs 2× the demand to reach; everywhere short of peak the lane is roughly half as
strong as V282."*

It is also worth stating plainly that this is **compounded** by §7.1/§7.2: at 20 m/s the live taper puts
the rail at **736**, and V293 reaches it only at idx 239.

### 7.5 Smaller corrections to the record

- The pre-registration's `32·1032·120` understates the worst case: the reachable map ceiling is **1128**
  (slots 8, 9), so the true worst product is **4,331,520**. Still 495× inside int32.
- "Kd bank (all records) 128 → 0" describes 8 of the 28 records; **20 carried 64**. The build zeroed all
  28 regardless, so nothing is wrong with the image — only with the description.
- The negative-side floor defect is **two** counts, not one (§4).

---

## 8. WHAT I DID **NOT** VERIFY — and the next step for each

1. **That `gp-0x6803` is zero on the wire.** §7.2's conclusion (taper = D) rests on it. It is inherited
   **[E]** from the kit's `0x0E4` handler record, not re-derived here. **Next:** decode `0x6803` on one
   engaged V292 rlog frame — it is already on the bus, no build needed.
2. **The speed axis unit of `gp-0x6a5e`.** Every m/s row in §7.2 inherits km/h as **[B]**. **Next:**
   read the four writers of `gp-0x6a5e` and their scale, or regress it against a logged wheel speed.
3. **Register-indirect writers** of `gp-0x680a`. I closed the LE32-literal hole, which is the route the
   kit's own record names as the one a gp-scan misses, but a pointer computed arithmetically at runtime
   would still evade all four methods. I consider the claim **strong**; it is not a proof.
4. **Anything outside arithmetic.** I priced no loop, no plant, no interlock, no CRC, no rebuild. B, C
   and D own those. In particular I did **not** check whether the sustained-effort / EME question (D1)
   is affected by the halved sub-rail surface — it plausibly cuts the dwell risk, but that is **[B]**
   and it is D's call.
5. **Ghidra held the STOCK dump, not V293.** I used it only for structure and for three byte
   arbitrations, and I verified V293 is **cal-only with zero code bytes changed** before relying on any
   of it. No mutating Ghidra call was made; nothing was saved.
