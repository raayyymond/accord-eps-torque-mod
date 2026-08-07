---
name: accord-damper-evaluator-fun34350-ceiling-clamp
description: FUN_00034350 is the damper evaluator — pointer-array records, a count field the code never reads, and a hard output clamp that is the real limit on damper dose.
metadata:
  type: reference
---

**`FUN_00034350` is the EPS damper evaluator. Sole caller `FUN_00022ca0`.** [EVIDENCE — orchestrator
decompiled it directly, then confirmed every address with raw little-endian Python byte reads of
`stock_fw_dump/code.bin` and the V38/V75/V76 plain images.]

## Records come from a POINTER ARRAY per factor
```
mode = *(u8 *)(gp + 0x63fd)
rec  = *(u32 *)(PTR_ARRAY + mode*4)          # 34 modes, 4 bytes per entry
```
`FactorB 0xC9CCC · FactorC 0xC9E9C · FactorD 0xC9DB4 · FactorE 0xC9F84 · ceiling 0xC77A0 ·
friction 0xCBE74`. **34 distinct records over 34 modes for every factor — zero sharing**, so editing
mode 26 touches nothing else. Records sit on a page grid, three modes per 0x1000 page
(`0xCE000`, `0xCF000`, `0xD0000`…`0xD9000`). The car is `TVCA4` — see [[reference-accord-car-is-tvca4-mode-24-26]].

## Record layout
```
base+0      u16    n            breakpoint count
base+2      n*i16  X[]          index, strictly increasing
base+2+2n   n*i16  Y[]          output, Q10 (1024 = unity)
base+2+4n   u16    terminator   0x0000 in every record read
total = 4 + 4n
```
🛑 **X starts at `base+2`, NOT `base+4`.** Reading at +4 silently yields `[X1,X2,X3,Y0]` and looks
plausible. The orchestrator made exactly this error on the first pass.
Shipped counts: ceiling **n=2** · friction **n=3** · FactorB/C/E **n=4** · FactorD **n=5**.

## 🛑 THE COUNT FIELD IS NEVER READ — more points is a CODE edit
Each factor's lookup is a genuine `while (X[i] <= idx) i++` search loop, but `n` is pinned per factor by
three hardcoded immediates:

| factor | &Y[0] | X_last | Y_last | n |
|---|---|---|---|---|
| B / C / E | rec+10 | rec+8 | rec+0x10 | 4 |
| D | rec+0xc | rec+10 | rec+0x14 | 5 |
| ceiling | rec+6 | rec+4 | rec+8 | 2 |

⇒ **"just make a bigger table" is impossible as a data-only edit** — it needs instruction edits to the
always-on base-assist damper, i.e. the class that bricked V24/V27/V48B.
⊕ **Relocating a SAME-SIZE record is cal-only** — one u32 into the pointer array. See
[[accord-damper-table-relocation-is-cal-only]].
⚠ A subagent described these five LERPs as separately *unrolled* compare chains. They are **loops**. The
conclusion was right, the mechanism wasn't — cf. [[feedback-decompile-first-then-assembly]].

## Clamps and the product
Below `X[0]` → hard clamp to `Y[0]` (**strict** compare, so `idx == X[0]` clamps too); above `X[n-1]` →
clamp to `Y[n-1]`; linear between, integer division truncating toward zero.
```c
uVar7 = ((((base*(base<0x401) + (base>=0x401)*0x400)   // gp-0x698a, CLAMPED to <= 1024
            * FB >> 10) * FC >> 10) * FD >> 10) * FE >> 10;
if (0 < *(short *)(gp - 0x6abe)) uVar7 = -uVar7;        // SIGN from gp-0x6abe, NOT the index
```
Purely multiplicative, four `>>10` Q10 steps, zero `add`/`or` ⇒ any factor at 0 forces the damper to 0,
with no additive rescue path.

## ★★ THE OUTPUT IS HARD-CLAMPED — this is the real limit on damper dose
```c
uVar10 = ceiling_LERP(gp-0x6ac2);        // ptr 0xC77A0, n=2, X=[300,800] Y=[512,1024]
                                          // if gp-0x6ac2 >= 0x32c9 -> *(u16*)0xC6158 = 512
gp-0x6bd0 = clamp(uVar7, -uVar10, +uVar10);              // SYMMETRIC
```
**`|gp-0x6bd0|` can never exceed 1024, and is capped at 512 at low ceiling index.** Both mode-24 and
mode-26 ceiling records are byte-stock on stock and V76. This is why the point count was never the
obstacle to a ReLU — see [[accord-relu-plan-inverts-at-the-ceiling]].

## Gates and the shadow
- `FactorC → unity (0x400)` if `(gp-0x6a5e > 0x7d00) || (gp-0x67f4 != 1)`.
  🛑 **`gp-0x67f4` has never been probed** and disables the whole speed shaping. OPEN.
- `damper term → 0` unless `(gp-0x6ac0 < 0x32c9) && (gp-0x6abe + 13000 <= 0x6590)`.
- **`gp-0x6bd0` is lockstep-shadowed at `gp-0x4cf2`**: `if (cur == shadow) {store both} else FUN_0006b9fa(gp-0x4cf2)`.
- **FactorB (n=4) and FactorD (n=5) are byte-read flat `Y=1024` — inert unity in BOTH modes** on this
  car. FactorD's axis is `gp-0x6a10` (angle-tracking error), gated `gp-0x67fe ∈ {1,2}`; it appears in
  `build_v43/v72–v77_tva.py` only in assert-untouched checks ⇒ **UNTESTED, not falsified**, and it is a
  free 5-point lane on the same multiply chain.

## Dose arithmetic
`dose(v,r) = min((C(v) * E(r)) >> 10, ceiling)`, reference rate **`R_OP = 99 counts = 21.0 °/s**` (the
measured in-burst p50 for grind #1). `SPEED_CTS_PER_KMH = 64.0625` (`FUN_000522fe`, `x*41>>6`; 5 mph =
515 counts). `RATE_CTS_PER_DEGS = 4.7121`. Ramp gain `k = ((C_Y0 * E_Y1) >> 10) / (E_X1 - E_X0)`, and
`dose(r) = k*(r - E_X0)` exactly. Flown creep doses at r=99: stock/V38 **0** · V74 **50** (k 0.5799) ·
V75 **137** (k 1.5798) · V76 **137** (k 1.3866).
