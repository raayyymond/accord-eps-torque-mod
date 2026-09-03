# Adversary A — arithmetic — V281 rev 3

**Subagent `adv281r3a` (firmware-codepath-tracer role), 2026-09-03.** Job: make V281 rev 3 FAIL on
arithmetic. Independent of the builder's own assertions and of the rev 2 predecessor pass's printed
numbers — the record layout, the LERP walker, the P-multiply and the reader census below are all
re-derived from GhidraMCP disassembly/decompile of `code.bin` (the code region 0x13000–0xC0000 is
byte-identical between stock, V280 rev 2 and V281 rev 3 per the builder's own diff, independently
re-confirmed here for the specific record-address literal search in §4, so `code.bin`'s copy of
`FUN_00028ea6` is the live function on all three images) and independent Python byte scans of
`code.bin`.

**What a FAIL would look like (written before the analysis):**
1. The flattened-Y LERP takes a different code path than the sloped LERP — a division-by-zero guard,
   a `slope==0` special case, or an `x>=X[4]` bound that reads outside the 24-byte record.
2. Kp=248 is below some minimum the code assumes elsewhere (a shift needing Kp≥256, a `Kp−256` term,
   a table indexed by `Kp>>k`).
3. The P-rail derivation (`|E|≈15855`) or the underlying E/Kp multiply has a width/overflow problem
   that a lower Kp makes worse, not better.
4. The 0xCB994 pointer bank or the 28 record byte-ranges have an undisclosed reader.

**Verdict: PASS. No arithmetic defect found.** All four attack vectors traced to specific addresses;
none produced a FAIL condition. One predecessor-report disagreement resolved (§0): the builder's record
layout is correct, re-derived independently from the walker's own disassembly.

---

## §0 — Record layout, resolved from the walker's disassembly (not from either report)

`FUN_00028ea6` (decompiled + disassembled, GhidraMCP, code.bin — same bytes on all three images):
record pointer `p` loaded from `0xCB994 + 4*iVar23` (disasm `0x29dc6–0x29dd6`: `mov 0xcb994,r10` /
`add r10,ep` / `sld.w 0x0,ep,ep` gives `ep = p`; a second, redundant load into `r10` gives the same `p`
again — this is where the decompile's "iVar41 = iVar26 = ..." double-read comes from, both reads are
the SAME pointer, not two different cells).

Confirmed field offsets, read directly off the instruction operands:

| offset | field | evidence |
|---|---|---|
| p+0 | n (u16) | not directly re-checked here (builder's `bn==5` check, re-used) |
| p+2 | X[0] | `0x29dde sld.hu 0x2,ep,r9` (ep=p) — compared against idx at `0x29dea` |
| p+4 | X[1] | `0x29dfa sld.hu 0x2,ep,r9` (ep now p+2) |
| p+10 | X[4] | `0x29df4 sld.hu 0x8,ep,r6` (ep=p+2, +8=p+10) — the upper-bound test at `0x29df6/df8` |
| p+0xc = p+12 | Y[0] | `0x29de2 add 0xc,r10` (r10=p) then `0x29dee ld.hu 0x0,r10,r9` on the idx≤X[0] path |
| p+0x14 = p+20 | Y[4] | `0x29e04 ld.hu 0x8,r10,r9` (r10=p+12, +8=p+20) on the idx≥X[4] path |
| p+0x16 = p+22 | pad | not read by this walker (matches "not this build's business") |

**This is the builder's layout exactly** (n, 5×X, 5×Y, pad — 12 words, 24 bytes) — the walker uses the
SAME word at p+10 for the "is idx ≥ top knot" test and as X[4], the last interpolation knot; there is
no second, duplicated "hi_th" word anywhere in the 24-byte record. The predecessor pass's "duplicated
hi_th" framing (ADV281R2-A) describes the SAME cell doing double duty (bound test + last knot), not a
distinct memory location — **resolved: no duplication exists; the builder's naming is correct.**
Consequently the edit (Y[1..4] := Y[0] at p+14/16/18/20) touches exactly the four words the builder
claims, and only those — confirmed structurally by the offsets above, not by re-reading the builder's
own table.

## §1 — Flat-Y LERP: all three branches traced, no special-casing, no div-by-zero, no OOB read

Full disassembly `0x29dc0–0x29e32` (55 instructions, quoted in full in the tool trace; addresses below
are exact):

- **idx ≤ X[0]** (`0x29dec bh 0x29df4` not taken): `0x29dee ld.hu 0x0,r10,r9` reads **Y[0]** directly at
  `p+0xc`. In-bounds, unconditional, no dependency on the shape of Y[1..4]. **Unaffected by the edit.**
- **idx ≥ X[4]** (`0x29df8 bnc 0x29e04` taken): `0x29e04 ld.hu 0x8,r10,r9` reads **Y[4]** at `p+0x14` —
  the last word of the Y block, well inside the 24-byte record (record spans p+0..p+23). **No
  out-of-bounds read.** Post-edit this is 248 instead of 696; same code path, same offset.
- **X[0] < idx < X[4]** (the walk): loop `0x29e0a–0x29e12` (the exact address the brief named) advances
  the X and Y pointers together while `idx ≥ X[k]`; the earlier `bnc 0x29e04` guarantee (idx < X[4])
  structurally bounds the loop to exit at or before k=3, so it **never reads past X[4]/Y[4]** —
  independent of any Y value, because the bound is on X, which this build never touches. At `0x29e14`:
  ```
  ld.hu 0x2,r10,r9   ; r9 = Y[k+1]
  ld.hu 0x0,r10,r13  ; r13 = Y[k]
  ld.hu -0x2,ep,r8   ; r8 = X[k]
  sub r13,r9         ; r9 = Y[k+1]-Y[k]
  sld.hu 0x0,ep,r6   ; r6 = X[k+1]
  sub r8,r7          ; r7 = idx-X[k]
  mul r7,r9,r0       ; r9 = (Y[k+1]-Y[k])*(idx-X[k])   (32x32->32, low word — see §3)
  sub r8,r6          ; r6 = X[k+1]-X[k]
  divq r6,r9,r0      ; r9 = r9 / r6   (signed divide; dst=r0, src=r9 — DIFFERENT registers, so the
                       known Ghidra V850 "divq dst==src" SLEIGH decode bug does NOT apply here)
  add r13,r9         ; r9 = quotient + Y[k]
  ```
  With every Y equal post-edit, `Y[k+1]-Y[k] = 0` unconditionally for every k, every record (asserted
  by the builder and independently true by construction of the edit): the `mul` produces exactly 0
  regardless of `idx-X[k]`, and `divq 0, (X[k+1]-X[k])` = 0 exactly for ANY nonzero divisor — **no
  divide-by-zero risk**, because the divisor is `X[k+1]-X[k]`, which depends only on X (untouched,
  strictly increasing, so always ≥1) and was never at risk from this Y-only edit. `add r13,r9` then
  gives exactly `Y[k] = Y[0]`. **Every branch returns 248 (live slot) exactly, with zero rounding
  residue** — matches the builder's claim exactly, now confirmed from the raw instruction sequence
  rather than from the Python mirror.

No branch inspects whether `Y[k+1]==Y[k]`; the flat case is not a special path, it is the general path
with a numerator that happens to be zero. **PASS.**

## §2 — Kp minimum-value assumption: none found

After the walker converges (`0x29e32 zxh r9`), `r9` (Kp, zero-extended u16) is used exactly once:
```
0x29e34  mov r16,r8      ; r8 = E  (see §3)
0x29e36  mul r9,r8,r0     ; {r8(new)=low32, r0=high32} = r9(Kp) * r8(E)
0x29e3a  ld.hu 0x71bc,tp,r6   ; r6 = 0xC61BC = 15360 (P_CLAMP)
0x29e3e  sar 0x8,r8       ; r8 = P = (Kp*E) >> 8
0x29e40  cmp r6,r8 / 0x29e42 ble 0x29e4a   ; clamp branch
0x29e44/0x29e4a  ld.hu 0x71bc,tp,r9/r13    ; re-reads the SAME clamp cell for both branches (symmetric ±)
```
`r9` (Kp) is **dead after `0x29e36`** — it is never read again in this window; the two subsequent
`ld.hu ...,r9` at `0x29e44`/elsewhere OVERWRITE r9 with the clamp constant, they do not read the old
Kp value. I found no shift, no subtraction, no comparison, and no second table lookup anywhere that
treats Kp (or the LERP result register) as needing to be ≥256, or indexes anything by `Kp>>k`. The only
consumer of the LERP result is the one multiply above. **No minimum-value assumption exists for Kp in
this path — PASS.** (I did not trace every OTHER caller of the Kp LERP's output value across the whole
function for unrelated purposes, because the disassembly shows r9 is architecturally dead past the
multiply — there is no "other purpose" for this specific register value to be reused for.)

## §3 — P-rail re-derivation and overflow check

`E` is loaded into `r16` at `0x29d78 sub r26,r16` (`r16 = 32*sp − r26`, i.e. `r16 = 32·sp − fb`,
matching the established formula) and is **not re-clamped or truncated** between that point and
`0x29e34 mov r16,r8` (I traced every instruction in `0x29d78–0x29e34`; r16 is copied to r6 at `0x29d7a`
for the separate dE/D-term computation but r16 itself is never overwritten before the P-multiply reads
it) — **independently confirms, at the register level, the rev 2 report's claim that E is unclamped**
going into the P multiply.

Width: the `mul` at `0x29e36` is a 32×32→64 signed multiply (V850E2 `MUL reg2,reg3,reg1`: low 32 bits
overwrite `reg3`, high 32 bits go to `reg1`); `sar 0x8,r8` operates on the **low** word (matches
Ghidra's own decompile, which models this as a plain `iVar26 = iVar31 * (uVar13&0xffff); uVar33 =
iVar26>>8;` — i.e. Ghidra's semantic model and my register-level reading agree). For this to differ
from a true 64-bit product, `|E·Kp|` would need to exceed `2^31−1 ≈ 2.147e9`. Bounding `|E|`: `sp` is a
map-LERP output (established range ≈0–1032 on the live map, so `32·sp` ≤ ~33024) and `fb` is itself
clamped elsewhere to ±46080 (established, not re-verified in this window — outside the traced address
range), so a generous bound is `|E| ≲ 79104`. Even at the OLD, higher Kp (up to 4095, the general
`0<Y<4096` bound the builder asserts across all 28 records) the product is `79104×4095 ≈ 3.24e8`, ~15×
below the int32 ceiling. **Lowering Kp to 248 only shrinks this margin further — it cannot create an
overflow that a higher Kp wouldn't already risk more.** No overflow defect, before or after this edit.

P-rail: `P = clamp((E·Kp)>>8, ±15360)`, clamp cell `tp+0x71bc = 0xC61BC = 15360` (re-read directly at
`0x29e3a`/`0x29e44`/`0x29e4a` — matches `P_CLAMP` exactly, both branches use the SAME cell, symmetric).
Exact integer threshold at Kp=248 (arithmetic-shift-right floors toward −∞, but for the positive-E case
`>>8` is a plain floor divide by 256): `E=15856` gives `(15856·248)>>8 = 3932288>>8 = 15360` (exactly at
the bound, not yet clamped since the branch is `ble`, less-or-equal passes through unclamped); `E=15857`
gives `15361` → clamped. So the natural value first REACHES the clamp bound at `E=15856` and is first
actively railed at `E=15857`. The builder's `P_CLAMP*256/Kp = 15360*256/248 = 15854.7…→"15855"` is a
**continuous approximation** (explicitly labelled "recomputed from the chain arithmetic" in the build
script, sec. [3b]), off by 1–2 counts (≈0.01%) from the discrete floor-division boundary — not a defect,
just a rounding difference between a continuous model and the integer boundary. **PASS**, with the
correction noted: the exact discrete rail is `|E|=15857` (first clamped sample), not `15855`.

## §4 — Reader census: 0xCB994 pointer bank and the 28 record byte-ranges

**Ghidra xrefs to `0xCB994`:** exactly 2 code sites, both `mov 0xcb994,r10` (absolute-immediate load,
not tp/gp-relative — confirmed by instruction bytes `2a0694b90c00` at both sites):
- `0x00029dc6` in `FUN_00028ea6` — **the live PID** (called from `0x22522`, confirmed both by Ghidra
  `get_xrefs_to(0x28ea6)` and independently below).
- `0x0002acb8` in `FUN_0002a93a` — the "dead twin" the rev 2 report named.

**Independent liveness check on `FUN_0002a93a` (positive-controlled per the skill's rule):**
- Raw Python scan for `jarl` disp22 (opcode field `0x1E`, per the skill's documented trap — NOT `0x1B`)
  across the full 1 MB image found exactly **one** hit: `0x22522 → 0x28ea6` — matching the skill's own
  documented control (`FUN_00028ea6 is called from 0x22522`) exactly, so the scanner is validated.
  **Zero** hits target `0x2a93a`. Ghidra's own `get_xrefs_to(0x2a93a)` independently returns **no
  references found**. Two independent methods agree: `FUN_0002a93a` has no direct callers.
- Indirect-call check: scanned the whole image for the raw little-endian 4-byte pointer value
  `0x0002a93a` (a function-pointer-table entry would show up this way) — **zero hits** anywhere in the
  file. (Same scan for `0x00028ea6`, the live function, also returns zero — consistent with it being
  called directly via `jarl`, never through a pointer table, so the "zero hits" methodology is not
  itself biased toward finding nothing.) **`FUN_0002a93a` is confirmed unreachable by both direct and
  indirect call — the Kp bank's second reader is dead code, independently re-confirmed for this image.**

**Record-memory census (the actual 28×24-byte record spans, not just the pointer bank):** for every one
of the 28 record base addresses (`0xE4360`…`0xE8288`, read from the live pointer bank) I scanned the
**entire 1 MB image** for any 4-byte little-endian pointer literal landing on **any of the 24 bytes** of
that record (base address + every offset 0–23), excluding the pointer-bank slot itself. **Zero hits.**
No other pointer bank, no taper/gain/map table, and no hard-coded absolute reference anywhere in the
image points into any Kp record's byte range. Combined with the `0xCB994`-bank census above, this closes
the "a cell is not private because you did not find another reader — prove the census" requirement:
**the only path to any of the 224 edited bytes is `FUN_00028ea6`'s single walker at `0x29dc6`, and
nothing else in the 1 MB image reads them.** **PASS.**

## Summary

| item | verdict | address(es) |
|---|---|---|
| §0 record layout | builder correct, predecessor's "hi_th" is the same cell, not a duplicate | p+2..p+10 (X), p+0xc..p+0x14 (Y) |
| §1 flat-Y LERP branches | PASS — no div-by-zero, no OOB, no special case | 0x29dec, 0x29df8, 0x29e0a-0x29e12, 0x29e14-0x29e30 |
| §2 Kp minimum assumption | PASS — none found, Kp dead after the multiply | 0x29e32-0x29e36 |
| §3 P-rail / overflow | PASS — E unclamped but nowhere near int32 overflow; exact rail is \|E\|=15857, not 15855 (cosmetic, ~0.01%) | 0x29d78, 0x29e34-0x29e4a |
| §4 reader census | PASS — 2 xrefs to the bank (1 live, 1 provably dead 3 ways); 0 other readers of any record byte anywhere in the image | 0x29dc6, 0x2acb8, full-image scans |

**No FAIL condition found on arithmetic grounds. Recommend PASS to flash on this axis**, with one
correction for the record (§3: the discrete P-rail is 15857 counts, not 15855 — a ~0.01% continuous-vs-
discrete rounding difference, not a defect) and one disambiguation for the record (§0: the predecessor
pass's "duplicated hi_th word" names the same memory cell the builder calls "the last knot doing double
duty as the bound test," not a second word — no duplication exists in the 24-byte record).
