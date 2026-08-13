# TRACE 2026-08-13 — Does the 4× forward LKAS gain reach `gp-0x6b4a` (term 0 of `gp-0x6ad6`)?

**Agent:** `tracer-4x-to-term0` · **Tooling:** GhidraMCP only + raw Python LE byte scan (both methods,
set-differenced) · **Program:** `code.bin` (stock, `list_open_programs` → `is_current: true`), cross-read
against `_v99_..._plain_image.bin` for the modern cal state.
`gp = 0xFEDF8000`, `tp = 0xBF000`.

---

## VERDICT

> ## 🛑 **NO. The 4× does NOT reach `gp-0x6b4a`. It is EXONERATED.**
> The 4×-gained LKAS command is placed in **struct field +4**, which becomes `gp-0x62f8[1]` →
> `gp-0x62b0[1]` → **`gp-0x6b4c`** (the sibling). The field that becomes `gp-0x62e0[1]` → `gp-0x6298[1]`
> → **`gp-0x6b4a`** is written with a **hard-coded `r0` (zero)** at `0x2b52a`.
>
> ## ⭐ And the second answer is the good one: **the 4× IS buying what it is supposed to buy.**
> Every clamp on its own path was raised in lockstep with the gain, and the first *fixed* clamp
> downstream sits **5.0× above** the path's ceiling. **There is no saturation anywhere on the 4× path.**

**Scanner validation (mandatory harness, `memory/accord-v850-scan-traps-formatv-and-storezero.md`):**
`gp-0x4f60` → **64 `ld.h` + 5 `st.h`** disp16 and **7** six-byte extended sites (`0x4c784`, `0x59bfa`,
`0x59c02`, `0x59c44`, `0x59c4c`, `0x5a0bc`, `0x5a0c4`) — **exactly the expected counts. PASS.**
Every census below covers **both** encodings.

---

## 1. The entry point, pinned

`0x2a1ee` is the V57-migrated forward-gain read. **[EVIDENCE — byte-verified in both images]**

| image | bytes @ `0x2a1ee` | disp | resolves to | value |
|---|---|---|---|---|
| stock | `25 3f 6c 74` | `0x746c` | `0xC646C` | **891** (1.000×) |
| V99   | `25 3f d0 7c` | `0x7cd0` | `0xC6CD0` | **3564** (4.000×) |

Matches `build_v57`'s own docstring: *"`0x2A1F0` ld.h displacement `0x746C -> 0x7CD0`"*.

```
0x2a1ee  ld.h   0x746c,tp,r7     ; r7  = GAIN cal          <-- THE 4x
0x2a1f2  ld.b   -0x6752,gp,r13   ; r13 = polarity (-1, boot-static)
0x2a1f6  mulh   r7,r13           ; r13 = gain x polarity
0x2a1fc  add    r9,r11           ; r11 = raw LKAS command
0x2a1fe  mul    r13,r11,r0       ; r11 = cmd x gain x polarity
0x2a202  sar    0xf,r11          ; >>15
0x2a204..0x2a220                 ; clamp to +-cal(0xC61B4)
0x2a226  mov    r11,r1
0x2a23c  st.h   r1,-0x6b38,gp    ; ==> gp-0x6b38                     (unconditional)
0x2a2c2  cmove  0x0,r1,r16
0x2a2ea  st.h   r16,-0x6b3c,gp   ; ==> gp-0x6b3c  (gated copy)       <-- nearly missed; 2nd output
```
⚠ `gp-0x6b30` (`0x2a206 st.h r9`) holds the **pre-gain** accumulator ⇒ **invariant to `0xC6CD0`.**

## 2. Forward frontier — EXHAUSTIVE, and it closes

Census of the 4×'s outputs (raw scan, both encodings; `get_xrefs_to` on `0xFEDF14C8` returned a
**tool zero** — Ghidra defines no data at gp-relative RAM, so it is a silence, not a negative):

| cell | writers | readers |
|---|---|---|
| `gp-0x6b38` | `0x2a23c`, `0x2a934` | `0x2b418`, `0x4e8d2`, `0x4e8e2` |
| `gp-0x6b3c` | `0x2a2ea`, `0x2b41c` | `0x2b42e` |
| `gp-0x6b3a` | `0x2b45c` | `0x2b5b2` |

**Exactly five reader sites image-wide.** Adjudicated one by one:

| reader | function | disposition |
|---|---|---|
| `0x2b418` | unanalysed fn ending `jmp lp` @`0x2b420` | `gp-0x6b3c = (r16!=0) ? gp-0x6b38 : 0` — a re-gate copy |
| `0x2b42e` | `FUN_0002b422` | **THE ONLY CONTROL PATH** — see §3 |
| `0x2b5b2` | `FUN_0002b57a` | float plausibility monitor (`×1/1024`, ±0.003 band, ±3.0 bounds) → `FUN_00027802` |
| `0x4e8d2/e2` | `FUN_0004e82e` | CAN TX packer — writes `gp-0x6b38` to frame bytes 7–8. **Report only** |

`FUN_00027802` reads `gp-0x62e0[]`/`gp-0x62f8[]`/`gp-0x633c[]`/`gp-0x6230[]` and range-checks them,
calling fault reporters `FUN_000462e6`/`FUN_0004613e`. **[EVIDENCE]** `0x2783a` is `sld.h 0x0,ep,r8` —
a **LOAD**. It never stores to the arrays. ⇒ that branch cannot feed term 0.

## 3. The one control path — and where it actually lands

`FUN_0002b422` clamps `gp-0x6b3c` to ±cal(`0xC61B2`), stores it to `gp-0x6b3a`, then packs a 16-byte
request struct and calls the registration API `FUN_00025c32`. **[EVIDENCE — instruction level]**

```
0x2b42e  ld.h  -0x6b3c,gp,r12          ; the 4x-gained command
0x2b432..0x2b44a                       ; clamp to +-cal(0xC61B2)
0x2b45c  st.h  r12,-0x6b3a,gp
0x2b524  mov   sp,ep
0x2b526  sst.b r10,0x0[ep]   ; r10=1   -> SLOT 1
0x2b528  sst.b r14,0x1[ep]             -> mode selector
0x2b52a  sst.h r0, 0x2[ep]   bytes 8104   ***  LITERAL ZERO  ***
0x2b52c  sst.h r12,0x4[ep]   bytes 8264   ***  THE 4x COMMAND ***
0x2b53e  jarl  0x00025c32,lp
```

`FUN_00025c32(param_1)` — the request-registration API — maps the struct to the arrays:

| struct field | clamp | destination array | reaches |
|---|---|---|---|
| `param_1+2` | ±`0x4000` (16384) | **`gp-0x62e0[slot]`** | → `gp-0x6298[]` → **`gp-0x6b4a` (TERM 0)** |
| `param_1+4` | ±`0x2800` (10240) | **`gp-0x62f8[slot]`** | → `gp-0x62b0[]` → **`gp-0x6b4c`** |
| `param_1+6` | ±900 | `gp-0x6274[]` | |
| `param_1+8` | ±20000 | `gp-0x633c[]` | |

🛑 **This offset map is the crux, and it is the opposite of the natural guess.** The command sits at
**+4**, not +2.

In `FUN_00026c80`, slot 1 is **mode 0** (cal `0xC4124` = `[0,0,5,0,5,5,0,0,0,5,0]`, index 1 = 0), and
mode 0 does:
```
gp-0x6298[i] = gp-0x62e0[i]      # -> term 0   ... = 0 for slot 1
gp-0x62b0[i] = gp-0x62f8[i]      # -> gp-0x6b4c ... = the 4x command
gp-0x62c8[i] = 0                 # -> gp-0x6b4e
```

⇒ **`4× → gp-0x62f8[1] → gp-0x62b0[1] → gp-0x6b4c`. Term 0 gets a structural zero.**

## 4. What DOES feed term 0 — enumerated at the caller level

All **10** `jarl → FUN_00025c32` sites, decoding the register written to struct `+2`:

| jarl | slot field `+2` | verdict |
|---|---|---|
| `0x23bd6` `0x24176` `0x2b53e` `0x2c374` `0x2cbe6` `0x2e642` `0x33b5c` `0x3a972` `0x3b25c` | **`r0`** | hard zero — 9 of 10 |
| **`0x34212`** (`FUN_0003405a`) | **`r7`** | **the only live producer** |

`0x341fa mov 0x2,r16` → `0x341fc sst.b r16,0x0[ep]` ⇒ **SLOT 2** (mode 5 ⇒ `gp-0x6298[2] = gp-0x62e0[2]`).

⚠ **Variable-reuse trap.** Ghidra renders the `+2` field as `uStack_2a = (undefined2)iVar7`, and
`iVar7` is reused. Resolved at instruction level:
```
0x340a8  ld.h -0x6b76,gp,r7      ; gate PASSES -> r7 = gp-0x6b76
0x34114  mov  0x0,r7             ; gate FAILS  -> r7 = 0
0x341fe  sst.h r7,0x2[ep]
```
**[EVIDENCE]** No write to `r7` anywhere in `0x34118–0x341f6` (disassembled in full) ⇒
`gp-0x62e0[2] = gate ? gp-0x6b76 : 0`.

Gate (all must hold): `|gp-0x6b76| ≤ 0x5000` · `|gp-0x6b78| ≤ 0x2800` · `gp-0x699c ≤ 0x400` ·
`gp-0x67ea < 2` · plus `gp-0x6a62` (angle) and `gp-0x6a8c` conditions.

`gp-0x6b76`: **1 writer / 1 reader**, both outside the 1 kHz task.
```
0x3402c  st.h r8,-0x6b76,gp      ; r8 = (r1==0) ? 0x7FFF : ((r6==0) ? 0 : -r14)
```
`0x7FFF` is the kit's known invalid-sentinel — and 32767 > 20480 ⇒ **the sentinel FAILS the gate**,
forcing term 0 to zero. `FUN_0003405a`'s only caller is `FUN_00022ca0` (the **assist-shaping** task),
not the 1 kHz control task that hosts the 4×.

## 5. Order — a same-tick path WAS possible; the data says it does not exist

`FUN_0002214a` (1 kHz), decoded `jarl` order:
```
0x022522 FUN_00028ea6  <- the 4x
0x022530 FUN_0002b422  <- registers slot 1
0x022572 FUN_0002b57a
0x0225b4 FUN_00028d22  <- shadow-lockstep CHECKER (read-only on the arrays)
0x0225f6 FUN_00026c80  <- writes gp-0x6b4a / 6b4c / 6b4e
0x022676 FUN_00038148  <- reads gp-0x6b4c  @0x3816c
0x022696 FUN_00037fe6  <- reads gp-0x6b4a  @0x37fea -> gp-0x6ad6
0x0226a0 FUN_0003a382  <- the PID, +-8192 clamp (0xC6200)
```
The 4× runs **before** the term-0 writer in the same tick, so ordering did **not** rule the path out.
It is ruled out on **data**: the `sst.h r0, 0x2[ep]`.

## 6. The rail arithmetic — 4× vs 1×

```python
# gp-0x6b4a  (TERM 0) -- all slots except 2 write 0 into gp-0x62e0[]
# cal 0xC4118 (tp+0x5118) = [1]*11  => every slot is in the ON partition
#   => OFF-sum == 0  => the rate-limiter term and its residual are both driven by 0
iVar13   = gp_6298[2]                      # = clamp(gp_6b76, +-16384) when gated open
gp_6b4a  = clamp(iVar13, +-25600)          # 0x27784/0x2779c/0x277aa
#   reachable |term 0| = 16384  ->  2.000x the PID's 8192 threshold   [CAN rail it]
#   and it is INVARIANT to 0xC6CD0 at every value.

# gp-0x6b4c  (the 4x path)
scaled   = (raw_cmd * gain * polarity) >> 15      # gain 891 stock / 3564 ours
capped   = clamp(scaled, +-cal_0xC61B4)           # 512 stock / 2048 ours
capped   = clamp(capped, +-cal_0xC61B2)           # 512 stock / 2048 ours  (identical, no-op)
gp_62f8_1= clamp(capped, +-10240)                 # FIXED in FUN_00025c32 -- NOT binding
gp_6b4c  = clamp(sum_ON(gp_62b0), +-10240)        # FIXED
```

| | stock 1× | ours 4× | ratio |
|---|---|---|---|
| gain `0xC6CD0`/`0xC646C` | 891 | 3564 | **4.000×** |
| scale `gain/32768` | 0.027191 | 0.108765 | **4.000×** |
| path clamp `0xC61B4`/`0xC61B2` | 512 | 2048 | **4.000×** |
| ceiling into `gp-0x62b0[1]` | ±512 | **±2048** | **4.000×** |
| next *fixed* clamp | ±10240 | ±10240 | **5.0× of headroom** |

**[EVIDENCE, byte-read from both images]** `0xC61B2` and `0xC61B4` are 512 stock → **2048** on V99, and
`BUILD-LINEAGE` records them as *"LKAS forward-path clamps 512 → 2048, tracking the 4x gain"* (pre-V38).

## 7. Attenuators

- **On the 4× path (`gp-0x6b4c`):** the gain `0xC6CD0` itself, the `>>15`, the twin clamps
  `0xC61B2`/`0xC61B4`, and the polarity byte `gp-0x6752`. No hidden multiplier.
  The `iVar13 × cal(0xC63CC) >> 10` cross-term into `gp-0x6b4c` is **dead: `0xC63CC = 0`** in both
  stock and V99 ⇒ `gp-0x6b4c` is a clean sum of `gp-0x62b0[]` alone.
- **On the term-0 path (`gp-0x6b4a`):** **CONFIRMED — no calibration weight anywhere.** From
  `0x340a8` to the store at `0x27784`/`0x2779c`/`0x277aa` the value passes only through
  `clamp(±16384)` (registration), a plain copy (mode 5), an unweighted `add` accumulation, and
  `clamp(±25600)`. **No `mulh`, no cal multiply.** The prior record is upheld.

## 8. The sibling `gp-0x6b4c`, and a correction to the array map

`gp-0x6b4c` **is** on the 4×'s path — it is the *only* thing on it. It is **not** separately weighted
(`0xC63CC = 0`) and its gate `tp+0x5118[]` is all-1 ⇒ zero-reject. It is read at `0x3816c` inside
**`FUN_00038148`** (the Path-2 aggregator), whereas `gp-0x6b4a` is read at `0x37fea` inside
`FUN_00037fe6` (the reference model). **Two different destinations** — consistent with the recorded
"two LKAS routes; `gp-0x6b4c` bypasses AUTH".

🛑 **Correction to the brief's array map.** `gp-0x6b4c` and `gp-0x6b4e` are **not** two partition sums
of `gp-0x62c8[]`:
```
gp-0x6b4e = clamp( SUM  gp-0x62c8[i], +-10240 )                  # ungated
gp-0x6b4c = clamp( SUM_ON gp-0x62b0[i], +-10240 ) + polarity*((iVar13*cal_0xC63CC)>>10)
gp-0x6b4a = clamp( SUM_ON gp-0x6298[i] + rateLimited + residual, +-25600 )
```
The array actually **partitioned** by the `tp+0x5118[]` flags is **`gp-0x6298[]`** (ON-sum →
`gp-0x3d80`, OFF-sum → `gp-0x3d84`), and **both halves feed `gp-0x6b4a`**.
Source arrays: `gp-0x6298[] ← gp-0x62e0[]`, `gp-0x62b0[] ← gp-0x62f8[]`, `gp-0x62c8[] ← gp-0x62f8[]`
(mode-dependent). `gp-0x62c8` and `gp-0x62f8` are both real and distinct — the lockstep checker
`FUN_00028d22` validates both.

## 9. Open / not closed

1. **`gp-0x6b76`'s upstream is NOT closed.** I pinned its writer (`0x3402c`, `r8 = -r14` with
   `r14 = clamp(r2, ±cal tp+0x716c)`), but did not trace `r2` back to a physical source inside
   `FUN_00033ba8`. **To close:** `decompile_function` on `FUN_00033ba8` @`0x33ba8`.
2. **Term 0's duty cycle is UNMEASURED.** Whether the gate is usually open, and how big
   `gp-0x6b76` actually gets, has never been instrumented. `gp-0x6b76` is 1W/1R and
   `gp-0x62e0[2]` is array-indexed — a probe would need care.
3. `gp-0x6b4a` remains **shadow-lockstep protected** at `gp-0x4cd2` (`0x27784/88`, `0x2779c/a0`,
   `0x277aa/b0`, trap `FUN_0006b9fa` @`0x277ba`). **Reading is free; writing trips the monitor.**
