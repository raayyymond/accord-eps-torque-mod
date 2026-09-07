# TRACE 2026-09-06 — hostile census of the LKAS rate-PID output-lag and feedback poles (V282)

**Agent**: `tracer` (subagent, reports to `main`). Study/analysis only — nothing built, flashed or sent.

**Programs used, stated explicitly (per the brief):**
- **Ghidra**: `code.bin` (stock dump), the ONLY program open (`list_open_programs` returned 1 program,
  `is_current: true`, 2086 functions). **All disassembly/decompile below is from stock.**
- **Python byte work**: `_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`
  (V282, 0x100000 bytes) with `code.bin` as the comparison.

**Why stock disassembly is admissible for V282 here [EVIDENCE]:** a full byte diff of the
`FUN_00028ea6` body `[0x28EA6, 0x2A2A0)` between V282 and stock returns **exactly 2 differing bytes,
`0x2A1F0` and `0x2A1F1`** — `ld.h 0x746c,tp,r7` (stock, to 0xC646C) became `ld.h 0x7cd0,tp,r7`
(V282, to 0xC6CD0), the V282 gain-source repoint. **Both filter blocks (`0x28F78`-`0x28FBE` and
`0x2A174`-`0x2A1B0`) are byte-identical.** Everything asserted about the filter arithmetic therefore
holds for V282.

**Anchor check (the off-by-0x1000 trap):** `tp = 0xBF000`, so `tp+0x73EC = 0xC63EC`. Verified **by
value**, not by arithmetic alone: 0xC63E8=923, 0xC63EA=1560, 0xC63EC=992, 0xC63EE=507, 0xC63E6=0 (Ki),
0xC61BC/BE=15360, 0xC646C=891. All match the record.

- **The trap DID fire once this session and was caught.** Ghidra renders the oscillation detector's
  LERP base as `DAT_0000794a + unaff_tp`; read at 0xC794A it gives nonsense knots (13/61464/13/61508).
  The correct anchor is **0xC694A**, which yields clean knots 0/15/20/25 and y 32768/32768/19661/19661.
  The same correction applies to `tp+0x72dc/0x72de/0x72e0`, which are **0xC62DC/DE/E0**, not 0xC72xx.

---

## TASK 1 — READER CENSUS, positive-controlled, two methods

### 1.1 Cal-cell values, V282 vs stock [EVIDENCE, Python LE read]

| addr | role | V282 | stock | raw |
|---|---|---|---|---|
| `0xC63E6` | Ki | 0 | 0 | `0000` |
| `0xC63E8` | feedback-EMA **a** | 923 | 923 | `9b03` |
| `0xC63EA` | feedback-EMA **b** | 1560 | 1560 | `1806` |
| `0xC63EC` | output-lag **a** | 992 | 992 | `e003` |
| `0xC63EE` | output-lag **b** | 507 | 507 | `fb01` |

**All four pole cells are byte-STOCK in V282.** Never edited in ~280 builds; confirmed here.

### 1.2 Raw Python census — the required second method

Scanner: every 2-byte-aligned offset in the whole 1 MiB image; decode `hw1`; keep sites where
`reg1 == 5` (tp) and the opcode field (hw1 bits 5-10) is a load/store (`0x38`-`0x3F`); resolve the
displacement with the **correct per-opcode rule** — `ld.h`/`ld.w`/`st.h`/`st.w` take `hw2 & 0xFFFE`,
`ld.hu` takes `hw2 & 0xFFFE` (encoded as `disp|1`), `ld.bu` carries displacement bit 0 in the opcode
field (`0x3C` even / `0x3D` odd). Target window `0x73E8`-`0x73EF`, plus controls.

**POSITIVE CONTROL — `0xC646C` (891), the record's known 5-reader cell: the scanner finds exactly 5
sites** — `0x2A944`, `0x2B656`, `0x2C448`, `0x36686`, `0x3684A`. Control **PASS**. (Stock has a 6th at
`0x2A1EE`; V282 repointed that one to 0xC6CD0, per the body diff above — an incidental second control
showing the scanner tracks a real edit.)

**Result for the four pole cells — exactly SIX sites image-wide, and ZERO stores:**

| addr | encoding | opcode | dest | cell |
|---|---|---|---|---|
| `0x28F86` | `e587eb73` | `0x3F` `ld.hu` | r16 | **0xC63EA** (fb b) |
| `0x28F8A` | `254fe873` | `0x39` `ld.h` | r9 | **0xC63E8** (fb a) |
| `0x2A174` | `e53fef73` | `0x3F` `ld.hu` | r7 | **0xC63EE** (lag b) |
| `0x2A184` | `253fec73` | `0x39` `ld.h` | r7 | **0xC63EC** (lag a) |
| `0x2A892` | `e5d7ef73` | `0x3F` `ld.hu` | r10 | **0xC63EE** (lag b) |
| `0x2A8A2` | `2557ec73` | `0x39` `ld.h` | r10 | **0xC63EC** (lag a) |

**No `ld.b`/`ld.bu`/`ld.w` and no `st.*` anywhere in `0x73E8`-`0x73EF`.**
Therefore **every one of the four cells is read as a HALFWORD only, never as a byte or a word, and
never written.** (This answers the brief's "is any cell also read as a byte or word somewhere" — no.)

**Unfiltered halfword sweep** (every occurrence of the raw value `0x73E8`-`0x73EF` anywhere in the
image, ignoring instruction context) returns 8 hits: the 6 above, plus two adjudicated **OUT**:
- `0x1F5D9` — **odd offset**, cannot be an instruction halfword boundary; data.
- `0x7FD5E` — preceding `hw1 = 0x7241`, low-5 bits = 1 (**r1**, not tp). Different base register.
  Exactly the false-positive class recorded in
  `reference_accord_operand_text_search_false_positive_wrong_base_register`.

**Extended / indirect forms, all negative with the method stated:**
- **48-bit extended-displacement tp loads** (opcode field `0x3E`, reg1 = tp): **0 hits** in the window.
- **Absolute dword pointers** into `0xC63E0`-`0xC63F8` anywhere in the image: **0 hits**.
- **`mov imm32, reg` (hw1 bits 5-15 == 0x31) with an immediate in `0xC6000`-`0xC6FFF`**: **4 hits**,
  all previously characterised and all in the **reprogramming/UDS** path, not the control loop —
  `0x146DC` (the wholesale `0xC6000`-`0xC6FFF` to `0xFA800000` block copy), `0x59560`, `0x5963E`,
  `0x59862` (the write-range validators / address mapper). **[BELIEF on "not live control readers"]**:
  their callers were not traced this session. The load-bearing point is only that the block **is**
  addressed through a base register, so "no other operand-text reader" was never by itself a census.

### 1.3 The Ghidra side, and the disagreement adjudicated

- `get_xrefs_to 0xC63E8` returns **"No references found."** This is the documented tp-displacement xref
  failure. **That null is worthless and is discarded, not reported as a finding.**
- `search_instructions operand_pattern="73e"` (prior session, same image) returned 58 matches with
  `truncated: false` and **did not contain `0x2A892` or `0x2A8A2`** — that region is unanalysed
  (`get_function_by_address 0x2a892` returns "No function found" in **both** programs), so the
  analysed-instruction scanner is structurally blind to it.
- **Adjudication: the Python scan wins**, because it is the method that found the control AND the extra
  sites, while the Ghidra scan found the control and missed real sites. Not averaged.

### 1.4 VERDICT per cell

| cell | readers | writers | GATE-1 verdict |
|---|---|---|---|
| `0xC63E8` fb a | **1** — `0x28F8A` (FUN_00028ea6) | none | **PRIVATE**, record CONFIRMED |
| `0xC63EA` fb b | **1** — `0x28F86` (FUN_00028ea6) | none | **PRIVATE**, record CONFIRMED |
| `0xC63EC` lag a | **2** — `0x2A184` (FUN_00028ea6) + `0x2A8A2` | none | SHARED-in-code, **PRIVATE-IN-EFFECT** |
| `0xC63EE` lag b | **2** — `0x2A174` (FUN_00028ea6) + `0x2A892` | none | SHARED-in-code, **PRIVATE-IN-EFFECT** |

**Why "private in effect" for the lag pair, and what is still open.** `0x2A30E`-`0x2B421` is a
**duplicate compiled copy** of the same LKAS computation (same cal set, same nine pointer banks, same
tail cells), differing from the live copy only in register allocation. Byte proof: the two dispatch
heads are `0x29322 ld.bu -0x3d38,gp,r10 = 8457c9c2` versus `0x2A508 ld.bu -0x3d38,gp,r6 = 8437c9c2`,
and `cmp 0x5,r10 = 6552` versus `cmp 0x5,r6 = 6532`. No entry path into it has ever been found, and the
halfword `0xA892` (the low half of `0x2A892`) **occurs nowhere in the image**, so no `movea`/`mov`
immediate can construct that address. Therefore the output-lag pole is applied **once per tick, not
twice**; there is no `H^2`.

**Residual caveat, carried forward unchanged:** `FUN_0002a30e` in the same range is a
live-with-no-discoverable-caller precedent in this kit (it writes STEER_STATUS=4, observed on CAN 399).
If its entry path is ever found it may enter this block too. **Cheapest definitive settle: a wire tap
on the shared RAM state `gp-0x3d3c` (0xFEDF42C4)** — exactly 4 accesses, 2 live (`ld.w 0x2A178` /
`st.w 0x2A1B0`) and 2 in the orphan (`ld.h 0x2A89A` / `st.h 0x2A8BA`). Written once per tick means the
orphan is dead; twice means it is live.

**RAM ownership:** feedback-EMA state `gp-0x3d30` (0xFEDF42D0) has **2 accesses, both inside
FUN_00028ea6** — **PRIVATE**. Output-lag state `gp-0x3d3c` has **4**, as above.

---

## TASK 2 — THE ARITHMETIC

### 2.1 The two filters, disassembled (`disassemble_bytes`, `dry_run: true`, stock)

**Output lag — `0x2A174` through `0x2A1B0`:**

```
0002a160  sxh    r12                      ; input S forced to signed 16-bit
0002a174  ld.hu  0x73ee, tp, r7           ; b = 0xC63EE = 507      (UNSIGNED load)
0002a178  ld.w   -0x3d3c, gp, r9          ; s = state              (32-bit)
0002a180  mul    r7, r12, r0              ; r12 = S * b            (low 32 kept, high discarded)
0002a184  ld.h   0x73ec, tp, r7           ; a = 0xC63EC = 992      (SIGNED load)
0002a194  mul    r9, r7, r0               ; r7  = a * s            (r9 preserved)
0002a1a0  sar    0xa, r12                 ; (b*S) >> 10
0002a1a6  sar    0xa, r7                  ; (a*s) >> 10
0002a1a8  add    r12, r7                  ; r7 = s_new
0002a1aa  add    r7, r9                   ; r9 = s_old + s_new
0002a1ac  sar    0x5, r9                  ; y = (s_old + s_new) >> 5
0002a1b0  st.w   r7, -0x3d3c, gp          ; state := s_new   (the INCREMENT, not y)
```

**Feedback EMA — `0x28F86` through `0x28FA8`:**

```
00028f4c  ld.h   -0x6a56, gp, r7          ; x = feedback input
00028f50  addi   0x2ee0, r7, r11          ; +12000
00028f54  addi   -0x5dc1, r11, r0         ; unsigned compare against 24001
00028f58  bnc    0x28f5e                  ; else jr 0x290b0 (bail)  => |x| <= 12000  [input guard]
00028f7c  ld.w   -0x3d30, gp, r26         ; s = state (32-bit); r6/r26 = 0 if not mode 1
00028f86  ld.hu  0x73ea, tp, r16          ; b = 0xC63EA = 1560     (UNSIGNED)
00028f8a  ld.h   0x73e8, tp, r9           ; a = 0xC63E8 = 923      (SIGNED)
00028f8e  mul    r16, r7, r0              ; r7 = x * b
00028f92  mul    r26, r9, r0              ; r9 = a * s   (r26 preserved)
00028f9a  sar    0xa, r7
00028fa0  sar    0xa, r9
00028fa2  add    r7, r9                   ; r9 = s_new
00028fa4  add    r9, r26                  ; r26 = s_old + s_new       <-- NO >>5 HERE
00028fa8  st.w   r9, -0x3d30, gp          ; state := s_new
00028fa6..0x28fbe                         ; symmetric clamp to +/- cal(0xC62E6)
```

### 2.2 The exact integer mirror, one line each

```python
# OUTPUT LAG  (state gp-0x3d3c, 32-bit; a=0xC63EC=992, b=0xC63EE=507; |x| <= 15360)
s_new = ((992*s) >> 10) + ((507*x) >> 10);  y = (s + s_new) >> 5;  s = s_new

# FEEDBACK EMA (state gp-0x3d30, 32-bit; a=0xC63E8=923, b=0xC63EA=1560; |x| <= 12000)
s_new = ((923*s) >> 10) + ((1560*x) >> 10); y = s + s_new;         s = s_new
# then y = clamp(y, -cal(0xC62E6), +cal(0xC62E6))   [V282: 46080; stock: 7680]
```

**So the form is neither of the brief's two candidates.** It is **not** `y += (b*x - a*y) >> 10` and
**not** `y = (a*y + b*x) >> 10`. It is a one-pole IIR **on an internal increment `s`**, whose output is
the **two-sample sum `s[n-1] + s[n]`**, optionally shifted. `a` is applied with a **positive** sign, so
the pole is `a/1024` directly.

- **Widths:** both states are **32-bit** (`ld.w`/`st.w`). Both `mul` are 32x32 keeping only the low 32
  bits (high half goes to `r0` and is discarded). Both shifts are **arithmetic** (`sar`), so negative
  products floor toward minus infinity — a small sign-asymmetric rounding, not a defect.
- **Clamp order:** output lag is filter, then `>>5`, then downstream. Feedback EMA is filter, then the
  `+/-0xC62E6` clamp. **In neither filter is the internal state `s` clamped**, so `s` is bounded only
  by the INPUT bound, not by any output clamp.
- **Sign extension:** `a` is loaded with **`ld.h` (sign-extending)**; `b` with **`ld.hu`
  (zero-extending)**. **Any future `a` >= 32768 would load NEGATIVE and produce a sign-flipping,
  unstable filter.** No candidate here is near that. `b` is safe up to 65535.

### 2.3 DC gain and pole frequency, derived from bytes

Steady state gives `s*(1 - a/1024) = b*x/1024`, so `s = b*x/(1024-a)` and `y = 2*s / 2^shift`.

**Therefore DC = 2b / ((1024-a) * 2^shift)**, with **shift = 5 for the output lag** and **shift = 0 for
the feedback EMA**.

- **Output lag today, 992/507: DC = 1014/(32*32) = 0.99023.** **The record's 0.990 is CONFIRMED.**
- **Feedback EMA today, 923/1560: DC = 2*1560/101 = 30.891.** **The brief's `/32` does NOT apply to
  this filter — there is no `>>5` in it.** Its DC is about 31x, not about 0.99. This is consistent with
  the kit memory `accord-feedback-operand-is-a-two-sample-sum-dc-30-89`, and it is why two earlier
  agents read 15.45.

Pole frequency uses the matched-z convention `f = -ln(a/1024)*fs/(2*pi)`, which is the convention that
reproduces the brief's own "923 is about 16.5 Hz" and "992 is about 5 Hz".

**Numeric mirror, run over the exact integer code above and self-checked by a 4000-tick step response
(output lag gives y = 15208 against closed-form 15210; EMA gives y = 30862 against 30891; the small
deficits are the `sar` floor):**

| a/b | f_pole | **DC** | abs H at 20 Hz | abs H at 40 Hz | max b*x | max s | **max a*s** | headroom to 2^31 |
|---|---|---|---|---|---|---|---|---|
| **992/507 TODAY** | 5.05 Hz | **0.9902** | 0.2422 | 0.1235 | 7,787,520 | 243,360 | 241,413,120 | **8.9x** |
| 963/986 (10 Hz) | 9.78 Hz | **1.0102** | 0.4430 | 0.2386 | 15,144,960 | 248,278 | 239,091,746 | **9.0x** |
| 932/1457 (15 Hz) | 14.98 Hz | **0.9898** | 0.5927 | 0.3454 | 22,379,520 | 243,256 | 226,714,268 | **9.5x** |
| 963/**966** (DC-fixed) | 9.78 Hz | **0.9898** | 0.4340 | 0.2337 | 14,837,760 | 243,242 | 234,242,014 | **9.2x** |

Feedback EMA (shift 0, `|x| <= 12000` from the input guard at `0x28F50`/`0x28F54`):

| a/b | f_pole | DC (2-sample sum) | max b*x | max s | max a*s | headroom |
|---|---|---|---|---|---|---|
| **923/1560 TODAY** | 16.53 Hz | 30.891 | 18,720,000 | 185,347 | 171,074,851 | **12.6x** |
| 842/2814 | **31.15 Hz** | 30.923 | 33,768,000 | 185,538 | 156,223,385 | **13.7x** |
| 832/**2966** (true 33 Hz) | 33.05 Hz | 30.896 | 35,592,000 | 185,375 | 154,232,000 | **13.9x** |

### 2.4 VERDICTS for task 2

1. **OVERFLOW: NONE, on every candidate pair.** The worst intermediate anywhere is `a*s` at **241 M**
   against the 32-bit signed limit **2,147 M** — **8.9x headroom minimum**. `b*x` peaks at 35.6 M. Both
   states are 32-bit and never truncated to 16. Both `mul` discard only the high half, which is zero at
   these magnitudes. **No candidate needs a width change.**
2. **`963/986` is NOT DC-neutral: DC = 1.0102, i.e. +2.0% delivered torque versus today's 0.9902.**
   That is a confound sitting on top of a pole move. **Use `963/966` (DC = 0.9898) if the intent is a
   pure pole move.** `932/1457` is already DC-neutral (0.9898 against 0.9902, a -0.04% change).
3. **`842/2814` is 31.1 Hz, not 33 Hz**, on the same convention the brief uses for 923 giving 16.5 Hz.
   Its DC is fine at 30.923 (+0.10%). For a true 33 Hz with DC held, use **`832/2966`** (33.05 Hz,
   DC 30.896, -0.02%).
4. **The "x2.5 to x2.9" in the brief is confirmed as the 20-40 Hz magnitude ratio of the 5 to 15 Hz lag
   move**: 0.5927/0.2422 = **2.45x at 20 Hz**, and 0.3454/0.1235 = **2.80x at 40 Hz**.
5. **The feedback EMA's +/-46080 clamp (`0xC62E6`, V282; stock 7680) saturates at |x| = 1492** of a
   possible 12000 input counts, because the DC gain is 30.89. All the fb candidates are DC-matched, so
   **the saturation point does not move** — but a faster pole passes more transient, so the clamp is
   reached on shorter events. This is the "FEEDBACK46080" edit, and it is the only non-stock cell in
   either filter's neighbourhood.

---

## TASK 3 — THE TICK

### 3.1 The task descriptor at 0xBB920 — decoded, and it carries NO period field [EVIDENCE]

`get_xrefs_to 0xBB920` returns two DATA referents, `0xBB7EC` and `0xBB858`. Reading `0xBB864` onward
gives a pointer array `0x000BB920, 0x000BB950, 0x000BB980, 0x000BB9B0, 0x000BB9E0, 0x000BBA10` —
**stride 0x30**, so each descriptor is 48 bytes and `0xBB920` is record 0.

```
0xBB920  c8 70 df fe   = 0xFEDF70C8   stack pointer
0xBB924  07 06 01 00   = 0x00010607   attribute/priority word
0xBB928  4a 21 02 00   = 0x0002214A   ENTRY -> FUN_0002214a          <-- the control task
0xBB92C  00 c0 de fe   = 0xFEDEC000   stack base
0xBB930  a4 07 00 01   = 0x010007A4
0xBB934..0xBB94F        zeros
--- next record ---
0xBB950  e0 70 df fe | 0xBB954 07 04 02 00 | 0xBB958 88 2a 02 00 = FUN_00022a88 (entry)
```

**There is no period field in the record.** It is an RTOS task/TCB initialiser (entry, stack,
priority), not a periodic-timer table. The two records differ only in bytes 1 and 2 of the attribute
word (`07 06 01` against `07 04 02`) — priority/id, not a divider. **The period cannot be read here.**

`get_function_callers FUN_0002214a` returns **"No callers found"**, consistent: it is dispatched by the
RTOS from this table, not reached by `jarl`. Its body ends in `FUN_000861f2`, which decompiles to a
**system-call table dispatch** through `SCBP`/`SCCFG` (the V850E2 system-call base-pointer registers) —
the "wait for next activation" primitive, which again carries no static period.

### 3.2 The 1 kHz claim [EVIDENCE, but BEHAVIOURAL, not static]

- **The static OSTM0 route is REFUTED in this kit's own record** (`TRACE-2026-08-20-loop-lag-map.md`
  line 27): the 79999-count reload was divided by an assumed 80 MHz PCLK; **PCLK is 40 MHz**, so that
  derivation gives 500 Hz, not 1000, and is discarded. Any memory still citing "OSTM0CMP=79999 over
  80 MHz" as a confirmation — including the `motor_torque_governor` docstring in the golden model
  (`analysis-2020accord/model/eps_chain_control.py`, "about 80 MHz") and
  `memory/misc/control-task-tick-confirmed-1khz.md` — is repeating the refuted half.
  **Flagged, not edited** (the operator asks to be consulted before a memory is changed).
- **The surviving evidence is a measurement**: the STEER_STATUS=4 debounce cal **`0xC64DF` = 100**
  (byte-verified in V282 this session, unchanged from stock) produced a **100.00 ms dwell measured on
  the CAN bus**. 100 ticks equals 100.00 ms, so **1 tick = 1.000 ms and the rate is 1000 Hz.** This is
  a real, independent, on-car measurement and it does not depend on any clock assumption.

**VERDICT: the 1 kHz tick is EVIDENCE**, resting on the dwell measurement alone. The static-timer
corroboration that the record calls a "second independent method" is **void** — it is one method, not
two.

### 3.3 The part that matters more, and is cleanly EVIDENCE

The `FUN_0002214a` decompile shows both functions called **in the same task body, in the same pass,
unconditionally under the same state mask**:

```c
if ((uVar2 & 0x930) != 0) { FUN_00028ea6(0x11); FUN_0002b422(0x12); FUN_0002b57a(0x13); }
...
if (uVar3 != 0)           { FUN_0003aa2c(0x20); }        // uVar3 = uVar2 & 0xc30
```

with `uVar2 = 1 << (gp-0x67fa & 0xf)`. The reachable state is `{11}`, and bit 11 (`0x800`) is set in
**both** `0x930` and `0xc30`. So **`FUN_00028ea6` and `FUN_0003aa2c` run once each, every tick, in that
order, synchronously.** Their relative phase is therefore exactly **one call-order gap, zero ticks of
skew**, whatever the absolute period turns out to be. **Every phase result that compares these two
functions is robust to the absolute-rate question**; only results quoted in absolute Hz depend on it.

**What would prove the period outright** (none of it done here, all read-only): read the OSTM0 or TAUA
compare register and its prescaler from the boot-init writes, resolve PCLK from the CKSC/PLL init, and
cross-check against the SVD `UPD70F3508_V850E2Px4.svd`. Alternatively, take a second on-car dwell
measurement against a different tick-denominated cal.

---

## TASK 4 — DOWNSTREAM CONSUMERS WITH A FREQUENCY-DEPENDENT GUARD

### 4.1 THE ONE AT RISK: Honda's oscillation-reversal detector, `FUN_000428d4`

**This is a live, genuinely frequency-selective assist cut, and 20-40 Hz sits inside its window.**

**Liveness [EVIDENCE, decompile of `FUN_0002214a`]:** called in the 1 kHz task under `if (uVar4 != 0)`
where `uVar4 = uVar2 & 0x830`; state 11 sets bit 11 = `0x800`, and `0x830 & 0x800` is non-zero, so it
**runs every tick.** Its own top gate is `iVar11 = FUN_00046ea6(5); if (iVar11 == 0) {...}` — the FSM
runs when DTC bit 5 is **clear**, that is, **in normal operation**; when the DTC is set the function
short-circuits to `uVar12 = 0x8000`, meaning no cut.

**Mechanism [EVIDENCE, decompile plus cal reads]:**

1. **Input**: `gp-0x6c2c`, the 1 kHz rate estimate produced by `FUN_00041464`. The kit record puts that
   producer's own EMA corner at about 67 Hz at fs = 1 kHz, so it passes the 20-40 Hz band essentially
   intact.
2. **Reversal test**: a 3-state FSM on `gp-0x67df` requires `gp-0x6c2c` to cross **alternately past
   `+cal(0xC620A)` and `-cal(0xC620A)`**, with `cal(0xC620A) = 12800` (V282 equals stock). This is an
   **amplitude threshold**.
3. **Dwell / timeout**: `gp-0x6759` counts ticks between crossings and the FSM **resets to state 0**
   once it reaches `cal(0xC64DD) = 50` (V282 equals stock). At 1 kHz that is **50 ms**.
   **So the detector only accepts oscillations whose HALF-period is under 50 ms, that is, frequency
   ABOVE 10 Hz. It is a high-pass acceptance window. 20-40 Hz is squarely inside it, while the 7-9 Hz
   ratchet band is squarely outside it.**
4. **Counter**: each accepted reversal increments the byte `gp-0x357c`; the latched level lands in
   `gp-0x671a`, floored and held against `cal(0xC64FA) = 5`.
5. **The cut**: `gp-0x671a` indexes a LERP at **`0xC694A`** (x knots) and **`0xC6952`** (y knots).
   Note this is **not** 0xC794A; see the anchor note at the top.

   | x (reversal level) | 0 | 15 | 20 | 25 |
   |---|---|---|---|---|
   | y (Q15) | 32768 | 32768 | **19661** | **19661** |

   So it is **flat at 1.000 up to level 15, then a linear ramp to a flat 0.600 at level 20 — a 40%
   assist cut.** The result goes to `gp-0x6994`, then through `FUN_00045608(2,...)` and
   `FUN_00045668(2)` to `FUN_00016de6(0x21,...)`, a monitor/DTC report on index 0x21.
6. **Speed gating**: the LERP runs only `if (gp-0x6a5e <= cal(0xC62E0) = 960)`; above that,
   `uVar12 = 0x8000` and there is no cut. `cal(0xC62DE) = 640` selects the hold/reload arm.
   `cal(0xC62DC) = 0` makes the second floor block unreachable, since `uVar8 < 0` is never true for a
   ushort. **All three are V282 equals stock.**

**Cost of the pole move against this monitor:**

- **The lag pole 5 to 15 Hz raises the loop's own 20-40 Hz output by 2.45x to 2.80x** (table in 2.3),
  directly on the signal that drives the rate this detector watches.
- **Reversals needed for any cut: 15. For the full 40% cut: 20.** At 20 Hz a reversal is a half-cycle,
  25 ms, so **15 reversals is 375 ms** and 20 is 500 ms of sustained oscillation. At 40 Hz those become
  **187 ms** and 250 ms. **The kit has measured the creep grind as a sustained 20.3-21 Hz line, and r35
  recorded a 0.9 s burst — long enough to reach level 20 several times over, IF the amplitude threshold
  is met.**
- **[BELIEF, and this is the crux I cannot close from bytes]** the detector is presumably not firing
  today, since a 40% assist drop during the grind is not in the symptom record. That implies today's
  `gp-0x6c2c` grind amplitude stays under +/-12800. **A 2.45x to 2.80x rise in exactly that band is a
  move toward that threshold, and it is the thing to price before flying the 15 Hz candidate.**
- **What would settle it**: the scale and the grind-band amplitude of `gp-0x6c2c`. That is a telemetry
  question, not a disassembly one — either an inert tap on `gp-0x6c2c` (0xFEDF13D4), or a
  reconstruction from existing route data if the r24 tap can be related to it. **I did not attempt
  either and will not guess a number.**

### 4.2 The other three, and why each is NOT at risk

**Governor slew, `FUN_0004503c`** — thresholds `0xC6206` = 512 (fast step, selected below 16.6 km/h)
and `0xC6208` = **205** (slow step, normal road speed); both V282 equals stock. It **is**
frequency-dependent: an asymmetric per-tick rate limit where motion away from zero is capped to
plus-or-minus STEP while motion toward zero and sign crossings are immediate. At 205 per tick it rate-
limits any component with `2*pi*f*A/1000 > 205`, so amplitude above 1631 at 20 Hz and above 816 at
40 Hz. **But it is a SHAPER, not a CUT.** It cannot latch a fault or kill assist, and `FUN_0004595a`,
its hard-fault monitor, checks only that the output magnitude does not exceed the target with matching
sign, which the asymmetric structure guarantees in every branch. **No DTC risk. It will, however, blunt
and rectify the extra high-frequency content the pole move creates, so expect less delivered HF than
the raw 2.45x to 2.80x figure, and expect the reduction to be asymmetric.**

**Soft-EME windup shaper, `FUN_00042af8`** — the `+/-8192` zero-reject on `gp-0x6acc`. Not
frequency-dependent; it is pure amplitude and persistence. **CANNOT FIRE.** The record's proven bound:
`gp-0x6ace <= cal(0xC6202) = 4762` (V282 equals stock, verified this session) plus compensation
`<= 2560` (the maximum Y of the 0xC67D8 LERP), giving **7322 against 8192, a margin of 870**. Both
terms are bounded by cals sitting downstream of the governor clamp, so PID-side high-frequency content
cannot push them.

**Hard-DTC lockstep monitor, `FUN_00043e44`** — the `+/-5` LSB integer-versus-float twin behind DTC
0xF00049. Not frequency-dependent. **Not at risk.** It cross-checks the recomputed shaper *bound* (the
corridor arm at `0xC6598` and the boost arm at `0xC65C4`), not the signal. A cal-only edit to
`0xC63E8/EA/EC/EE` touches neither arm, so the delta stays 0. The standing rule still applies to any
*other* edit: a soft-EME cal change must move the integer and the float together.

---

## SUMMARY OF CORRECTIONS TO THE BRIEF

1. **The filter form is neither candidate.** It is a one-pole IIR on an *increment*, with the output
   being the **two-sample sum** of that increment, and `a` **added**, not subtracted.
2. **`DC = 2b/(1024-a)/32 = 0.990` is right for the OUTPUT LAG only.** The feedback EMA has **no
   `>>5`**; its DC is **30.89**, not about 0.99.
3. **`963/986` moves DC by +2.0%** (to 1.0102). Use **`963/966`** for a DC-neutral 10 Hz.
4. **`842/2814` is 31.1 Hz, not 33 Hz.** Use **`832/2966`** for a DC-neutral true 33 Hz.
5. **`tp+0x794a` is `0xC694A`, not `0xC794A`** — the off-by-0x1000 trap fired once this session and was
   caught only because the knot values were nonsense.
6. **The 1 kHz tick rests on ONE method, not two** — the on-car dwell measurement. The OSTM0 static
   derivation still quoted in the golden model and in
   `memory/misc/control-task-tick-confirmed-1khz.md` is refuted by PCLK = 40 MHz.
   **Flagged for the operator; not edited.**

## OPEN, WITH THE EXACT NEXT STEP

| open item | next step |
|---|---|
| Is the `0x2A30E`-`0x2B421` duplicate ever entered? | Tap `gp-0x3d3c` (0xFEDF42C4): written once per tick means dead, twice means live. |
| Does the grind's `gp-0x6c2c` amplitude approach +/-12800? | Inert tap on `gp-0x6c2c` (0xFEDF13D4), or relate the existing r24 tap to it. **This is the gate on flying the 15 Hz lag pole.** |
| Absolute task period, statically | Read OSTM0/TAUA compare plus prescaler and the CKSC/PLL init against the SVD. |
| Callers of the 4 register-indirect `0xC6000` sites | `get_function_callers` on the enclosing functions of `0x146DC`, `0x59560`, `0x5963E`, `0x59862`. |


---

# ADDENDUM 2026-09-06 — follow-up (a) what gp-0x6c2c is, (b) the detector RAM and a cave rung

Same programs and rules. Positive control for every census below: **gp-0x3d3c returns exactly 4
accesses** (0x2A178 ld.h, 0x2A1B0 st.w, 0x2A89A ld.h, 0x2A8BA st.h). PASS.

## (a) gp-0x6c2c is a DERIVATIVE OF MOTOR ROTOR POSITION. It has NO firmware path from T.

**[EVIDENCE, decompile of FUN_00041464 plus a gp census]** The producer chain, in order:

1. `sVar15 = *(short *)(gp-0x4f50)` — the input. **gp-0x4f50 (0xFEDF30B0) has exactly ONE writer
   image-wide, `st.h` at `0x68FDE`**, inside `FUN_00068f52`, which the golden model identifies as the
   **resolver rotor-speed/position estimator in the 4 kHz FOC ISR chain**. 11 accesses total, 1 store.
2. **Validity gate**: `(sVar15 + 13000) > 26000` unsigned marks the sample INVALID. On invalid,
   `gp-0x6c2c` is forced to the sentinel **0x7FFF** (`st.h` at `0x4184E`).
3. Scale and inner EMA: `u = sVar15 * 0x400`, then `u += ((u - state) * cal(0xC643C)=37) >> 7`,
   state `gp-0x359c`. Corner **54.30 Hz**.
4. **Differentiate**: `iVar11 = u_new - u_prev`, then `* 0x20`, then clamp to `+/-0xFA0000`
   (16,384,000).
5. Outer EMA: `iVar17 += ((iVar14 - iVar17) * cal(0xC40DC)) >> 6`, state `gp-0x35a0`.
6. **`*(short *)(gp-0x6c2c) = (short)(iVar17 >> 9)`** — `st.h` at `0x41AC2`.

```python
# integer mirror, 1 kHz, annotated
u     = angle * 0x400                                  # angle = gp-0x4f50 (rotor position)
u    += ((u - s1) * 37) >> 7 ;  s1 = u                 # cal 0xC643C=37, corner 54.30 Hz
d     = u - u_prev                                     # THE DIFFERENCER
d     = max(-0xFA0000, min(0xFA0000, d * 0x20))        # x32 then clamp
s2   += ((d - s2) * 14) >> 6                           # cal 0xC40DC, V282=14 (stock 22)
gp_6c2c = s2 >> 9                                      # st.h @0x41AC2
```

**ANSWER TO THE SCALE QUESTION: it cannot be done, and that is structural, not a failure to find it.**
`gp-0x6c2c` is derived from the **motor rotor angle**, while the 427 tap `gp-0x6b38` is the
**delivered lane torque**. Between them lies the motor and the mechanical rack. **There is no firmware
arithmetic connecting T to gp-0x6c2c** — the transfer is the plant, which no disassembly can supply.
Any "12800 in tap counts" figure would have to come from measurement, not from the binary.

**What CAN be stated exactly, from the bytes:** the estimator saturates at `0xFA0000 >> 9 = 32000`, so
**the 12800 threshold is exactly 40.0% of gp-0x6c2c's own full scale.** That is the honest,
self-contained way to express it.

**`0xC40DC` IS NOT STOCK IN V282: 14, against stock's 22.** This is the detector's own input filter and
it was already moved (V109's lever, per the kit record). Corners: **V282 39.29 Hz, stock 67.04 Hz** —
so the record's oft-quoted "67 Hz for gp-0x6c2c" describes STOCK, not the image under test.

| filter | cal | corner | abs H @5 | @10 | @20 | @40 Hz |
|---|---|---|---|---|---|---|
| inner | 0xC643C = 37 (>>7) | 54.30 Hz | — | — | — | — |
| outer **V282** | 0xC40DC = **14** (>>6) | **39.29 Hz** | 0.9920 | 0.9693 | **0.8918** | **0.7026** |
| outer stock | 0xC40DC = 22 (>>6) | 67.04 Hz | 0.9973 | 0.9892 | 0.9589 | 0.8610 |
| sister gp-0x6c2e | 0xC40DA = 3 (>>7) | **3.77 Hz** | 0.6025 | 0.3532 | **0.1856** | **0.0942** |

So on V282 the detector still sees **89%** of any 20 Hz content and **70%** of 40 Hz. The band is not
filtered away.

**gp-0x6c2c is NOT private:** 8 accesses — writers `0x4184E` (fault sentinel) and `0x41AC2` (normal);
readers `0x36C1A`, `0x428FA`/`0x4292C`/`0x42968` (the detector), `0x71378`, `0x7B1A2`.

### Does it fire in MANUAL driving today? [EVIDENCE from the gating, not a guess]

**The FSM has NO engagement gate.** Its only gates are the DTC-bit-5 interlock (`FUN_00046ea6(5)`,
which permits the FSM when the DTC is CLEAR) and the speed gate on the LERP
(`gp-0x6a5e <= cal(0xC62E0) = 960`). **So it is armed in manual driving.**

**But it structurally cannot accumulate on a transient.** Reaching a cut needs 15 accepted reversals,
each an alternating crossing of `+/-12800` (40% of full scale) arriving within `cal(0xC64DD) = 50`
ticks of the last. On timeout the FSM drops to state 0, and the state-0 branch executes
`st.b r0, -0x357c, gp` at **`0x42906`** — **the accumulated reversal count is wiped to zero.** A bump
steer gives ONE crossing, then times out, then zeroes. So **only a genuinely SUSTAINED oscillation
above 10 Hz, at 80% or more peak-to-peak of full scale, for 375 ms or longer, can reach any cut.**
That is why it is not a routine manual-driving event, and it is also exactly why the 20 Hz creep grind
is the one regime that could satisfy it.

## (b) The detector's RAM, and what a cave rung can actually read

**Widths and addresses [EVIDENCE, gp census; the opcode gives the width directly]:**

| role | gp offset | address | width | accesses |
|---|---|---|---|---|
| watched rate | `gp-0x6c2c` | 0xFEDF13D4 | **halfword** `ld.h`/`st.h` | 8 (2 w / 6 r) |
| sister slow rate | `gp-0x6c2e` | 0xFEDF13D2 | **halfword** | 5 (2 w / 3 r) |
| **cut FACTOR (Q15)** | **`gp-0x6994`** | **0xFEDF166C** | **halfword `st.h`** | **1 — a single store at `0x42A86`, ZERO gp-relative readers** |
| cut LEVEL (LERP input, 0..25) | `gp-0x671a` | 0xFEDF18E6 | **BYTE** `st.b`/`ld.bu` | 7 — `st.b 0x42A12`; readers `0x35BEA`, `0x36C1E`, `0x3A4A6`, `0x3AA70`, `0x429C4`, `0x429D2` |
| reversal counter | `gp-0x357c` | 0xFEDF4A84 | **BYTE** | 4 — `st.b r0 0x42906` (the zeroing), `ld.bu` at `0x42942`/`0x4297C`/`0x42998` |
| inter-crossing tick counter | `gp-0x6759` | 0xFEDF18A7 | **BYTE**, **ODD displacement** | — |
| FSM state | `gp-0x67df` | 0xFEDF1821 | **BYTE**, **ODD displacement** | — |
| hold/decay counter | `gp-0x6a88` | 0xFEDF1578 | halfword | — |

**The rung form** (from `build_v282_tva.py`; it is a displacement-only edit at four `hw2` halfwords,
with `hw1 == 0x2437` = `ld.h <disp>[gp], r6` at every site):
`ld.h A[gp],r6 ; abs ; ld.h B[gp],r6 ; abs ; cmp ; bit = (|A| >= |B|)`.

### The three structural constraints, and what they rule out

1. **The rung is `ld.h` only, so both operands must be gp-relative HALFWORDS at EVEN displacements.**
   **The cut LEVEL, the reversal counter, the tick counter and the FSM state are ALL BYTES**, so none
   of them is a valid rung operand. `gp-0x6759` and `gp-0x67df` are additionally at **ODD**
   displacements and cannot be `ld.h`-addressed at all. For the two even-displacement bytes a `ld.h`
   would fetch the byte as the LOW half plus a neighbour as the HIGH half: `ld.h -0x671a,gp` yields
   `level | (gp-0x6719 << 8)`, and `ld.h -0x357c,gp` yields `count | (gp-0x357b << 8)`. **Both
   neighbours return ZERO gp-relative accesses** — but **"no gp-relative access" is NOT "always
   zero"**: operand-text census cannot see register-indirect writes, and it says nothing about
   power-on contents. **I will not certify either as a clean read.**
2. **A gp-relative disp16 spans only 0xFEDF0000-0xFEE00000 — RAM.** The threshold
   `cal(0xC620A) = 12800` is in **ROM** and is therefore **unreachable by any rung of this form.** A
   `|gp-0x6c2c| >= 12800` bit cannot be built unless some RAM halfword holds 12800 or a fixed fraction
   of it. **I did not find one, and I did not run the exhaustive search that would settle it.**
3. **`gp-0x6994` is the ideal tap source and is orphan-safe**: one store, zero gp-relative readers, a
   true halfword. It carries the answer directly — **32768 = idle, 19661 = full 40% cut**, with the
   ramp between. (Live consumption is via the register passed to `FUN_00045608`, so this cell is a
   mirror; register-indirect readers cannot be excluded by operand-text census.)

### Two rung designs, honestly ranked. READ-ONLY DESIGN ONLY — nothing built.

**Design 1 — the reference-free HF bit, BUILDABLE TODAY as a displacement-only edit:**
`bit = ( |gp-0x6c2c| >= |gp-0x6c2e| )`. Both halfwords, both even, both already `ld.h`-shaped. Fast
EMA (39.3 Hz) against slow EMA (3.77 Hz) **of the identical upstream signal**, so the ratio is a pure
high-frequency-content measure on exactly the quantity the detector watches. At 20 Hz the magnitude
ratio is 0.8918/0.1856 = **4.8**, so the bit pins near 1.0 during a grind.
**Baseline caveat**: at DC both EMAs converge to the same value, so in smooth driving the bit is a coin
flip near **duty 0.5**, not 0. The statistic is "duty rises from about 0.5 toward 1.0", not a clean
on/off. Size the discriminator against that baseline before flying it.

**Design 2 — the direct "detector fired" bit: `bit = ( |gp-0x6994| >= |B| )`, reading 1 = idle,
0 = cutting.** This is the bit worth having, and it is BLOCKED only on finding `B`: any gp-relative
halfword whose magnitude is stable in **(19661, 32768]**. **I have not found one.**
**Exact next step to settle it**: census every gp-relative `st.h` in the image whose stored register is
loaded from a `mov`/`movea` immediate in that window, keep only cells with a single writer, then
confirm the candidate is written once at init and never after. That is a bounded scan I can run on
request. Until it returns a cell, Design 2 is a design, not a proposal.

**Not recommended:** any rung on the LEVEL or the reversal COUNTER. Both are bytes, both would import
an unproven neighbour byte into the high half, and the counter is wiped to zero by `0x42906` on every
timeout, so a sampled bit on it would read zero almost always even during a real event.


---

# ADDENDUM 2 (2026-09-06) — the detector's action path, and the Design-2 reference scan

## 1. THE PREMISE IS WRONG: zero readers on gp-0x6994 does NOT make the cut inert.

**gp-0x6994 census CONFIRMED, and tighter than reported:** exactly **one** gp-relative access
image-wide, the `st.h` at `0x42A86`. **Zero readers.** Corroborated three ways — no absolute dword
pointer anywhere into 0xFEDF1660-78; no `mov imm32` RAM base equal to it; the full gp access map
returns an empty reader list.
⚠ **Residual I will not paper over**: 324 `mov imm32` sites carry a RAM base in 0xFEDF0000-8000, and
several (0xFEDF1194, 0xFEDF11AC, 0xFEDF1064) sit **below** 0xFEDF166C. I did **not** bound their copy
lengths, so a block copy reaching this cell is not excluded.

**But the cut factor never needed that cell. It is passed in a REGISTER:**

```c
*(short *)(gp-0x6994) = (short)uVar12;             // 0x42A86 -- a DIAGNOSTIC MIRROR, dead
FUN_00045608(2, uVar12 & 0xffff, uVar7, uVar10);   // <-- THE LIVE PATH
```

`FUN_00045608(slot, a, b, c)` with `slot < 7` writes three parallel 7-entry halfword arrays:
`gp-0x652c[slot]` (TARGET) `<- a`, plus `gp-0x64fc[slot]` and `gp-0x6514[slot]` (the slew bounds).
**Slot 2 puts the cut factor at `gp-0x6528`.**

**These arrays are addressed through a walking pointer, so a direct operand-text census of `gp-0x6528`
returns ZERO and that null is meaningless** — the classic register-indirect blind spot. Censusing the
**base displacements** instead is what finds them:

| base | role | sites |
|---|---|---|
| `gp-0x652c` TARGET[] | `movea` at `0x450C6`, `0x45610` | 2 |
| `gp-0x6544` CURRENT[] | `movea` at `0x1BF92`, `0x1BFA4`, `0x450BE` | 3 |
| `gp-0x64fc` bound A[] | `movea` at `0x450F0`, `0x45146`, `0x451AC`, `0x45618` | 4 |
| `gp-0x6514` bound B[] | `movea` at `0x450D6`, `0x4512C` | 2 |

**Every one of `0x450BE`-`0x451AC` is inside `FUN_0004503c` — the MOTOR TORQUE GOVERNOR.**

## 2. VERDICT: on V282, ENGAGED, the detector firing MULTIPLIES THE MOTOR DEMAND BY 0.600.

**[EVIDENCE, decompile of `FUN_0004503c`]** The governor opens with a slew loop over the slot arrays,
folds every slot into ONE Q15 aggregate, then multiplies the demand by it:

```c
puVar18 = (ushort *)(gp - 0x652c);        // TARGET[]  <- slot 2 is the detector's cut factor
puVar19 = (ushort *)(gp - 0x6544);        // CURRENT[]
uVar10  = 0x8000;                         // 32768 = unity
do {   /* slew CURRENT[i] toward TARGET[i] within the bounds arrays */
       uVar10 = FUN_00049a78(uVar10);     // fold slot i into the aggregate
       ...                                // 3 iterations x 2 slots, + a 7th at gp-0x6538
} while (bVar3);
uVar6 = FUN_00049a78(uVar10) & 0xffff;    // THE AGGREGATE Q15 SCALE
...
iVar7 = FUN_00049a90(gp-0x6b94, -((gp-0x4f64 * uVar17) >> 15));   // clamp the demand
iVar8 = (iVar7 * uVar6) >> 0xf;           // <<<<<< THE CUT MULTIPLIES THE DEMAND
```

`iVar8` then passes through the asymmetric 512/205 slew into **`gp-0x6ace`**, the governor output that
feeds the soft-EME shaper and then **`gp-0x6b98`, the FOC demand**.

**The fold is a MIN — now EVIDENCE, not belief.** `FUN_00049a78` decompiles to
`return param_2 * (param_2 <= param_1) + param_1 * (param_2 > param_1)`, i.e. **`min(a, b)`**. The
aggregate seeds at unity (0x8000) and every slot folds in, so **the most restrictive slot wins** and
slot 2 alone can pull the whole scale to 0.600.

**So X is not "nothing". X = the motor demand is scaled by 19661/32768 = 0.600 at full cut**, applied
multiplicatively inside the governor, on the same path this whole build arc has been tuning. Slot 2 is
slew-limited on the way in (the bounds arrays), so the cut ramps rather than steps.

**A GOLDEN-MODEL GAP THIS EXPOSES.** `motor_torque_governor()` in
`analysis-2020accord/model/eps_chain_control.py` models these two aggregates as **exogenous inputs** —
`sensors.governor_limit_scale_q15` and `sensors.governor_post_scale_q15`. They are not exogenous: they
are the MIN-fold of the 7-slot array, and **slot 2 is Honda's oscillation detector.** The model
therefore cannot represent this cut at all. Flagged, not edited.

## 3. The cut LEVEL byte gp-0x671a and its six readers

| site | function | what the level does |
|---|---|---|
| `0x429C4`, `0x429D2` | `FUN_000428d4` | the detector's own re-reads (hold/floor logic). Not an action. |
| `0x3AA70` | `FUN_0003aa2c` (aggregator, r24 arm) | **NIL when engaged on V282 — see below** |
| `0x3A4A6` | `FUN_0003a382` (the resonance PID) | RECORD (kit trace 2026-08-20): **no effect, flat table.** Function **byte-identical V282 vs stock** (0 diffs over 0x3A382-0x3A8A8). Not re-derived this session. |
| `0x35BEA` | `FUN_00035b20` | RECORD: switches the ceiling feeding the biquad's r18 from ~461-512 to a flat 307. Byte-identical V282 vs stock. Not re-derived. |
| `0x36C1E` | `FUN_00036c12` (friction) | RECORD: flips to a flat -8192 gain, but on cal **`0xC64FD`**, a different cell, **not gated by 0xC64FA**. Byte-identical. Not re-derived. |

**`0x3AA70`, freshly disassembled and V282-byte-checked:**

```
0003aa70  ld.bu -0x671a, gp, r12      ; r12 = LEVEL
0003aa78  ld.bu 0x74fa, tp, r14       ; r14 = cal(0xC64FA) byte = 5
0003aa7c  cmp   r14, r12
0003aa7e  bc    0x3aa88               ; level < 5 ?
0003aa80  mov   0x1, r2 ; ld.hu 0x7136,tp,r22   ; level >= 5 : r22 = cal(0xC6136) = 0
0003aa88  mov   0x0, r2 ; ld.hu 0x7138,tp,r22   ; level <  5 : r22 = cal(0xC6138) = 1
0003aa92  cmp   0x1, r22
0003aa94  ld.bu -0x6806, gp, r15      ; V282 ENGAGED GATE  (stock: -0x683c)
0003aa98  setfe r10                   ; r10 = (level < 5)
0003aaa6  cmp   r0, r15
0003aaa8  setfne lp                   ; lp  = (gate != 0) = ENGAGED
```

**V282 code delta CONFIRMED at the byte level: `0x3AA96` is `0xFB` in V282 against `0xC5` in stock**,
turning `ld.bu -0x683c,gp,r15` into `ld.bu -0x6806,gp,r15` — the V104 rate-lane gate repoint to
STEER_CONTROL_ACTIVE, exactly as the kit record has it.

⇒ **ENGAGED, `gp-0x6806 != 0`, so the gate arm is taken and the r24 arm is the flat `cal(0xC6446)` =
5244 in V282 (stock 512, byte-verified).** The level-derived boolean sits on the `gate == 0` path only.
**So on V282, engaged, gp-0x671a has NO influence on the r24 arm.**
[EVIDENCE for the gate repoint and the cal values; the "flat 5244 when gate != 0" structure is the
kit's existing record, whose entry conditions I confirmed but did not re-derive end to end.]

**NET VERDICT.** On V282, engaged, the detector firing does exactly one thing to motor torque: **the
Q15 cut factor through governor slot 2, MIN-folded, scaling the demand toward 0.600.** The LEVEL byte's
four non-detector readers contribute **nothing engaged** — one is gated off by the V282 repoint, one is
a flat table, one is on a different cal, one touches a biquad ceiling. **The cut is real, and it is the
FACTOR, not the level.**

**Incidental find:** `FUN_0004503c` carries **one** V282-vs-stock byte, at `0x454FE` (`ba65` -> `b565`,
`bne` -> `br`). That is the V42 state-4 ratchet fix, present and correct.

## 4. The Design-2 reference scan for B: a CLEAN NULL. Design 2 is NOT buildable today.

**Method + POSITIVE CONTROL.** Scanned every `movea`/`ori`/`mov imm32` materialising a value in
(19661, 32768] (316 sites) and every gp-relative `st.h` (2333 sites), paired them within 24 bytes on a
matching register (174 pairs), then filtered to destinations with **exactly one writer** in the full gp
access map. Separately scanned for cal-load-then-store sequences.
**Control, named before the run: the scanner must find the fault sentinel writing `0x7FFF` into
gp-0x6c2c. It did** — `0x41ABE movea 32767,r11`, then `0x41AC2 st.h r11,-0x6C2C` and
`0x41AC6 st.h r11,-0x6C2E`. **Control PASS**, so the null below is meaningful.

🛑 **THE CONTROL ALSO CORRECTS MY OWN ADDENDUM 1**: I wrote that `0x41AC2` was the normal store of
gp-0x6c2c and `0x4184E` the fault sentinel. **It is the other way round** — `0x41AC2`/`0x41AC6` are the
`0x7FFF` invalid-branch stores; `0x4184E`/`0x4185A` are the normal ones. Nothing else in that addendum
depends on it.

**Every candidate adjudicated OUT, each with its reason:**

| candidate | apparent value | why it is REJECTED |
|---|---|---|
| `gp-0x0F60` (0xFEDF70A0) | "21508" | **Disassembly kills it twice.** `0x51A04 add r13, r8` sits between the cal load and the store, so the cell holds **cal + a runtime value**, not a constant. AND my part-C scan had a **sign bug**: it read the tp displacement as unsigned, so `ld.hu -0x35e0,tp` was resolved to 0xCBA20 when the real address is **0xBBA20**. The "21508" was never the right cell. |
| `gp-0x6A9E` (0xFEDF1562) | "20480" = cal(0xC647A) | **Conditionally skipped.** `0x31C8E be 0x31C94` jumps **over** the cal load, so on that branch r13 holds something else entirely and that is what gets stored. Not a constant. |
| `gp-0x6950/694E/694C/6958/6956` | "32768" | **False positives.** The `ori 0x8000` sites at `0x4524A`-`0x453CC` are **inside `FUN_0004503c`**, and the decompile shows these destinations are the **CURRENT cells of other slew chains** — they take `FUN_00049a90(...)` results every tick and hold 32768 only transiently. My proximity heuristic cannot tell a clamp **argument** from a **stored value**. |
| the `movea 32767` group | "32767" | **False positives**, same shape as the gp-0x6c2c control: fault/init sentinels into cells that are otherwise computed every tick. |

🛑 **RESULT: NO gp-relative RAM halfword holding a stable constant in (19661, 32768] exists in this
image, by a positive-controlled scan with every candidate adjudicated.** Therefore
`bit = ( |gp-0x6994| >= |B| )` **cannot be built** — there is no B. **Design 2 is closed, not pending.**

**What survives.** **Design 1 is still buildable today** as a pure displacement edit:
`bit = ( |gp-0x6c2c| >= |gp-0x6c2e| )`, fast 39.3 Hz EMA against slow 3.77 Hz EMA of the same upstream
signal, magnitude ratio 4.8 at 20 Hz, baseline duty near 0.5 in smooth driving. It measures the HF
energy that DRIVES the detector rather than the detector's output, which — given section 2 — is
arguably the more useful quantity anyway, because it moves before any cut happens rather than at the
last level of the ramp.

**And one thing that no longer needs instrumenting.** Since the cut is a MIN-fold into the governor
scale, a 40% cut is a **40% drop in delivered assist** — a symptom the operator would feel directly and
unmistakably. If the grind is not accompanied by a large, sudden assist loss, the detector is not
firing. **That is a free observation requiring no build at all**, and it should be checked against the
existing drive record before any tap is cut for this purpose.


---

# ADDENDUM 3 (2026-09-06) — GATE 1 for 0xC63EC / 0xC63EE: is 0x2A892 / 0x2A8A2 reachable?

**VERDICT: UNREACHABLE. Every path into 0x2A892 begins inside the duplicate block, and NOTHING enters
that block from outside. GATE 1 PASSES for 0xC63EC and 0xC63EE — an edit changes ONE lag filter.**

🛑 **PROJECT HYGIENE, as instructed: I did NOT create a single function, label, or comment. Nothing was
imported, nothing was renamed, `save_program` was NOT called.** Every Ghidra call was
`disassemble_bytes` with `dry_run: true` or a read-only query. The shared analysed project is
byte-for-byte as I found it. The work was done with dry-run disassembly plus raw Python on the V282
image, which turned out to be sufficient — defining functions was not needed to answer the question.

## (i) The decisive instruction: 0x2A504 is a RETURN, not a fall-through

The whole "does FUN_0002a30e leak into the duplicate block" question is settled by one instruction.
`FUN_0002a30e` is bounded by Ghidra at 0x2A30E-0x2A507, and the four `jr` sites the brief names all
target 0x2A504:

```
0002a4e4  br       0x0002a504
0002a4f4  br       0x0002a504
0002a504  dispose  0x0, { r20,r22,r24,r26,r28,lp }, lp     <-- EPILOGUE + RETURN via lp
0002a508  ld.bu    -0x3d38, gp, r6                          <-- the duplicate's dispatch head
0002a50c  cmp      0x5, r6
0002a50e  bnc      0x0002a52a
```

**`dispose imm, list, lp` pops the frame AND jumps to `lp`.** So `0x2A34C`, `0x2A368`, `0x2A384`,
`0x2A3BA`, `0x2A4E4` and `0x2A4F4` all branch to the function's **RETURN**, and control **never falls
through** from 0x2A507 into 0x2A508. Ghidra's function bound is CORRECT here.
⇒ **FUN_0002a30e being live tells us nothing about the duplicate block.** The residual caveat that
`reference_accord_lkas_pid_pole_cell_gate1_census_2a508_second_reader` left open is now **CLOSED**.

(Incidentally this confirms FUN_0002a30e is the STEER_STATUS machine: `0x2A4EC` and `0x2A4FC` are
`st.b r1x, -0x6807, gp` with the register holding 4.)

## (ii) The convergent tail: where 0x2A892 is entered from

`0x2A892`/`0x2A8A2` sit in a block entered only at **`0x2A890`**. Every branch in the image targeting
`[0x2A880, 0x2A8D0)` — **19 of them** — lands on `0x2A890`, and **every single source is inside the
duplicate block**, spanning `0x2A54E` to `0x2A878`:

```
0x2A54E 0x2A56A 0x2A58C 0x2A594 0x2A5A8 0x2A5CC 0x2A5EC 0x2A664 0x2A672 0x2A6C4
0x2A748 0x2A75A 0x2A79C 0x2A7A4 0x2A7E2 0x2A820 0x2A846 0x2A858 0x2A878
```

That is the convergent-tail shape: the duplicate's dispatch ladder at 0x2A508 fans out to nine handler
ranges, all of which converge on the shared lag tail at 0x2A890. **So the question reduces entirely to:
is 0x2A508 ever entered?**

## (iii) The branch scan, positive-controlled — and a NEW decoder trap it exposed

**Method.** Raw Python over the whole code region, decoding two branch families:
- **Format III** (2-byte conditional / `br`): `(hw1 & 0x0780) == 0x0580`,
  `disp9 = sx(((hw1>>11)&0x1f)<<4 | ((hw1>>4)&0x7)<<1)`.
- **Format V** (4-byte `jr`/`jarl disp22`): `((hw1>>6) & 0x1f) == 0x1E`,
  `disp22 = sx(((hw1 & 0x3f)<<16) | hw2)`, `reg2 = (hw1>>11)&0x1f` (0 = `jr`).

**45,821 branches decoded. POSITIVE CONTROLS — 7 of 7 PASS**, named before the run:

| control | kind | result |
|---|---|---|
| `0x22522 -> 0x28EA6` | jarl | PASS |
| `0x22530 -> 0x2B422` | jarl | PASS |
| `0x22572 -> 0x2B57A` | jarl | PASS |
| `0x23276 -> 0x34350` | jarl | PASS |
| `0x2291E -> 0x3AA2C` | jarl | PASS |
| `0x2A1B4 -> 0x2A1E6` | Bcond | PASS |
| `0x28F3C -> 0x290B0` | jr | PASS |

**Raw result: 3 branches appear to enter `[0x2A508, 0x2B422)` from outside** — `0x1B36A -> 0x2B3E9`,
`0x20462 -> 0x2AC83`, `0x22CA0 -> 0x2AC41` (plus `0x20F0A -> 0x2B4AB` in the wider window).

🛑 **ALL FOUR ARE FALSE POSITIVES, and the reason is a NEW V850 SCAN TRAP worth recording:
`prepare` collides with `jr`/`jarl` on the Format-V opcode field.** Ghidra adjudicates them directly:

```
00022ca0  prepare  { r20,r21,r22,r23,r25,r26,r27,r28,lp }, 0x0    (bytes 8007a17f)
0001b36e  prepare  { r22,lp }, 0x4                                 (bytes 88072102)
```

`0x22CA0` is the entry of `FUN_00022ca0` — **the 100 Hz task** — and its prologue decodes as a bogus
`jr`. **The discriminator is that a real `jr`/`jarl` target must be HALFWORD-ALIGNED.** All four
produced ODD targets (`0x2B3E9`, `0x2AC83`, `0x2AC41`, `0x2B4AB`), which is structurally impossible on
V850. Filtering on target parity removes every one.
⊕ This is the mirror image of the documented `jarl` opcode-field trap: that one gave **false
negatives**, this one gives **false positives**. Both are caught by the same discipline — control the
scanner, then adjudicate every hit.

⇒ **After adjudication: ZERO real branches enter `[0x2A508, 0x2B422)` from outside it.**

**Backward branches from the live tail functions.** `FUN_0002b422` and `FUN_0002b57a` ARE live (jarl'd
from the 1 kHz task at 0x22530 and 0x22572), and they sit immediately above the duplicate block, so I
scanned every branch from `[0x2B422, 0x2C000)` targeting below 0x2B422. The real ones go to
`0x25C32`, `0x1CBA6` (twice) and `0x27802` — **all outside and below the duplicate block**. The rest
decoded to negative addresses, i.e. the same `prepare`/data artifacts. **No live tail function branches
back into the block.**

**Indirect / address-materialisation routes, all closed:**

| route | result |
|---|---|
| `mov imm32` with an immediate in `[0x2A508, 0x2B422)` | **1 hit**, `0x5A366 mov 0x2b000,r8` — immediately `st.w r8, 0x1044, r17`, a DATA field in a config struct; 0x2B000 is mid-body, not an entry. **OUT.** |
| 4-byte-aligned absolute dwords into the block | **3 hits, all OUT**: `0x1E4C8 = 0x2AE0B` is an **ODD** value, impossible as a code address; `0x5A368` is the immediate above; `0x75B78` is the byte pattern of the real instruction `addi 0x2, ep, r20` (`1ea60200`) read as a dword — Ghidra-confirmed, a coincidence. The other 18 dword hits are at unaligned offsets inside data/cal blocks. |
| `movhi 0x0002/0x0003` + `movea` pairs | **7 movhi sites image-wide; NONE is followed by a `movea 0xA508`.** Three of them (0xC563E, 0xFA23E, 0xFAE3E) are inside data blocks of repeating 0x0002. |
| halfword `0xA890` / `0xA892` anywhere in the image | **ZERO occurrences** — no immediate can construct the lag block's address at all. |

## VERDICT, and what it licenses

**"UNREACHABLE: every path into 0x2A892/0x2A8A2 starts at 0x2A890, which is reached only from 19 sites
all inside the duplicate block, whose sole entry 0x2A508 has no branch, no fall-through, and no
constructible address anywhere in the image."**

- **Fall-through**: blocked by the `dispose ..., lp` return at 0x2A504. [EVIDENCE]
- **Direct branch**: zero, after a 7/7-controlled scan with all 4 raw hits adjudicated. [EVIDENCE]
- **Indirect**: no immediate, pointer, or movhi/movea pair can build 0x2A508 or 0x2A890. [EVIDENCE]

⇒ **GATE 1 PASSES for `0xC63EC` and `0xC63EE`. Editing them changes exactly ONE output-lag filter, the
one in the live `FUN_00028ea6` at 0x2A174/0x2A184. There is no second application and no `H^2`.**
Together with Addendum 1 (the feedback poles `0xC63E8`/`0xC63EA` have a single reader each, and the
EMA state `gp-0x3d30` is private), **all four pole cells are cleared for a cal-only edit on GATE 1.**

**What the unreachable code computes**, for completeness: it is a **duplicate compiled copy of the same
LKAS assist/rate computation** — same cal set, same nine pointer banks, same convergent lag tail, and a
tail that writes the identical six cells `FUN_00028ea6`'s tail writes. It differs from the live copy
only in register allocation (`0x29322 ld.bu -0x3d38,gp,r10 = 8457c9c2` against
`0x2A508 ld.bu -0x3d38,gp,r6 = 8437c9c2`). **It is not a second lane and not a monitor**, and since it
never executes it **does not feed the motor.**

**The one thing this does NOT close**, stated plainly: `jarl [reg]` / `jmp [reg]` Format-XI dispatch
through a pointer computed at run time from something other than an immediate — for example a value
arriving over UDS or read from a table I have not identified as a pointer table. I have no positive
control for that encoding, so I did not attempt a census of it and I am not quoting a number for it.
**What makes that route implausible rather than merely unmeasured** is the halfword result: neither
`0xA890` nor `0xA892` occurs anywhere in the 1 MiB image, and `0x2A508` cannot be assembled by any
movhi/movea pair present. A run-time-computed entry would still have to get its constant from
somewhere. **If the operator wants this closed rather than bounded, the cheapest settle remains the
wire tap on `gp-0x3d3c` (0xFEDF42C4): written once per tick means dead, twice means live.**


---

# ADDENDUM 4 (2026-09-06) — GATE 1 census of the PID clamp bank 0xC61B4..0xC61BF

🛑 **HEADLINE: `0xC61BA` IS NOT THE D CLAMP. `0xC61B6` IS.** Both cells hold **10240**, which is why
they are easy to conflate. `0xC61BA` is the **integrator anti-windup ceiling** and sits one instruction
after the Ki load.

✅ **AND THE GOOD NEWS, because I audited it rather than assuming: THE KIT'S RECORD IS ALREADY CORRECT.
The mislabel is in the task brief for this session only, not in the repo.** A grep over every build
script and memory file finds the right assignment everywhere:

```
build_v274/275/276/277/278/278r3/279/280_tva.py:   0xC61B6: 10240,  0xC61BA: 10240,   # D clamp / I anti-windup
build_v270/271/272_tva.py:152:                     KI_CLAMP = 0xC61BA   # anti-windup, (v<<10)>>3
build_v275_tva.py:32:   0xC61B6  D clamp  10240 ... 4/4 ld.hu ... 65535  OK (not needed)
build_v275_tva.py:33:   0xC61BA  I clamp  10240 ... 1/1 ld.hu ... 65535  OK (Ki=0, inert)
```

⭐ `build_v275_tva.py` lines 32-33 are an **independent corroboration of this session's census**,
written by an earlier session: **4/4 `ld.hu` on the D clamp and 1/1 on the I clamp** — exactly the live
counts I re-derived below from bytes, by a different method. And `build_v270_tva.py` independently
states the `(cal(0xC61BA) << 10) >> 3` anti-windup arithmetic I recovered at `0x29DA0`-`0x29DAC`.

⇒ **No build was ever mis-dosed on this. Nothing needs retracting.** The only action is to fix the
brief's label so the next dose is written against `0xC61B6`.

## Cell values, V282 vs stock

| addr | tp disp | V282 | stock | role (this session) |
|---|---|---|---|---|
| `0xC61B2` | 0x71b2 | **3072** | 512 | non-stock in V282 |
| `0xC61B4` | 0x71b4 | **3072** | 512 | **T clamp** (non-stock in V282) |
| **`0xC61B6`** | 0x71b6 | **10240** | 10240 | 🛑 **THE D CLAMP** |
| `0xC61B8` | 0x71b8 | **102** | 102 | post-lag **DEADBAND**, not a clamp |
| `0xC61BA` | 0x71ba | **10240** | 10240 | 🛑 **INTEGRATOR anti-windup ceiling**, not D |
| `0xC61BC` | 0x71bc | 15360 | 15360 | P clamp |
| `0xC61BE` | 0x71be | 15360 | 15360 | post-gain **sum clamp** |
| `0xC61C0/C2/C4` | 0x71c0.. | **65535** | 1600 / 896 / 1280 | V36-blanked |

## Reader census — two methods, set-differenced, live vs unreachable split

**POSITIVE CONTROL: `0xC646C` returns exactly 5 sites** (`0x2A904`, `0x2B656`, `0x2C488`, `0x36686`,
`0x3684A`). PASS. Method as before: opcode-aware tp scan with the correct `ld.hu` (`disp|1`) and
`ld.bu` parity rules, cross-checked against an unfiltered halfword sweep with every extra hit
adjudicated by base register.

**Boundaries used:** `FUN_00028ea6` = 0x28EA6-0x2A2A0 (**LIVE**, 1 kHz) · `FUN_0002a30e` =
0x2A30E-0x2A507 (**LIVE** — behaviourally, it writes STEER_STATUS=4 seen on CAN 399; its caller is
still unidentified statically) · **0x2A508-0x2B421 = the duplicate block, proven UNREACHABLE in
Addendum 3.**

| cell | LIVE readers | unreachable-block readers | live count |
|---|---|---|---|
| `0xC61B4` T clamp | `0x2A1F8` hu, `0x2A20C` **h**, `0x2A212` hu, `0x2A21C` hu | 0x2A910, 0x2A91E, 0x2A924, 0x2A92E | **4** |
| **`0xC61B6` D clamp** | `0x29EE8` hu, `0x29EF2` hu, `0x29EF8` hu, `0x29F02` hu | 0x2ADD4, 0x2ADDC, 0x2ADEC | **4** |
| `0xC61B8` deadband | `0x2A1BE` **h**, `0x2A1CA` hu | 0x2A8C8, 0x2A8D4 | **2** |
| `0xC61BA` integrator | `0x29DA0` hu | 0x2ACA0 | **1** |
| `0xC61BC` P clamp | `0x29E3A`, `0x29E44`, `0x29E4A`, `0x29E58` all hu | 0x2AD2C, 0x2AD34, 0x2AD44 | **4** |
| `0xC61BE` sum clamp | `0x2A13E` hu, `0x2A146` **h**, `0x2A14C` hu, `0x2A156` hu | 0x2B024, 0x2B02C, 0x2B032, 0x2B03C | **4** |

**ZERO writers on any of them.** No 48-bit extended tp form reaches `0x71b4..0x71bf` (0 hits). No
absolute dword anywhere points into `0xC61B4..0xC61BF` (0 hits).

⇒ **`0xC61BA` has 2 raw readers, of which exactly ONE is live.** The record's "2 readers, not 5" is
CONFIRMED, and can now be sharpened to **1 live reader**.

**Unfiltered sweep on the D clamp specifically** (every occurrence of halfword `0x71B6`/`0x71B7`
anywhere): 10 raw hits. **7 are the tp sites above** (base register r5 = tp, confirmed on each). **3
adjudicated OUT with the base register stated**: `0x2C9B2` (prev hw1 `0x05D5`, base **r21**),
`0x4221A` (prev `0x05D3`, base **r19**), `0x5680E` (prev `0xFF80`, base **r0**). Set-difference between
the two methods is **empty**.

🛑 **CORRECTION TO A FRAMING IN MY OWN EARLIER WORK — `0xC61C0/C2/C4`.** Their 12 readers split
`0x2924A`, `0x2925E`, `0x2926E`, `0x292C4`, `0x292D8`, `0x292E8` (in `FUN_00028ea6`) and `0x2A42C`,
`0x2A440`, `0x2A450`, `0x2A4A6`, `0x2A4BA`, `0x2A4CA` — **and that second group is inside
`FUN_0002a30e` (0x2A30E-0x2A507), which is LIVE, NOT inside the unreachable block that starts at
0x2A508.** So these are **12 live readers across two live functions**, not 6 live plus 6 orphan.
The unreachable-block boundary begins at 0x2A508 and it is easy to mis-split these by eye.

## The D clamp, disassembled: `D = (ΔE · Kd) >> 3`, symmetric, and STRUCTURALLY SAFE to lower

```
00029ee0  mov   r16, r8            ; r8 = E
00029ee2  sub   r27, r8            ; r8 = E - E_prev  =  ΔE
00029ee4  mul   r7, r8, r0         ; r8 = ΔE * Kd     (r7 = the Kd LERP result, divq @0x29ED8)
00029ee8  ld.hu 0x71b6, tp, r10    ; L = 0xC61B6 = 10240        [UNSIGNED]
00029eec  sar   0x3, r8            ; D = (ΔE * Kd) >> 3          <<<< the >>3, CONFIRMED
00029eee  cmp   r10, r8
00029ef0  ble   0x00029ef8         ; D <= +L ? test the low side
00029ef2  ld.hu 0x71b6, tp, r8     ; D = +L                      [UNSIGNED]  clip high
00029ef6  br    0x00029f08
00029ef8  ld.hu 0x71b6, tp, r7     ; [UNSIGNED]
00029efc  subr  r0, r7             ; r7 = -L
00029efe  cmp   r7, r8
00029f00  bge   0x00029f08         ; D >= -L ? in range
00029f02  ld.hu 0x71b6, tp, r8     ; [UNSIGNED]
00029f06  subr  r0, r8             ; D = -L                      clip low
```

**Answers to the brief, point by point:**
- **Symmetric ±ONE cell.** There is no separate negative-limit cell. The negative limit is built as
  `0 - L` by `subr r0` at `0x29EFC` and `0x29F06`.
- **The `>>3` is confirmed** at `0x29EEC`, applied to the product, before the clamp.
- With the live Kd record `0xE511C` flat at **128**, `D = ΔE * 128 >> 3 = ΔE * 16`, so the clamp
  **rails at |ΔE| = 10240/16 = 640**. Lowering to **2560 rails at |ΔE| = 160**; **1280 rails at
  |ΔE| = 80**.
- 🛑 **NO ld.h/ld.hu MISMATCH HERE. All four loads are `ld.hu` (opcode 0x3F).** Lowering `0xC61B6` to
  2560 or 1280 **cannot install a wrong-sign limit**, for two independent reasons:
  1. **Structural** — both the compare limit and both clip values come from the *same cell* through the
     *same unsigned load*, with the negative built by `subr r0`. The clamp is symmetric by
     construction at **any** cell value, including 0xFFFF.
  2. **Numeric** — 2560 and 1280 are both far below 32768, so even the mismatched form would be safe.

## The latent ld.h/ld.hu mismatch: it is REAL, but on the T and SUM clamps, not on D

Two other clamps in the same bank load the **positive clip value with `ld.h` (SIGNED)** while every
other load in the same clamp uses `ld.hu`:

```
; SUM clamp 0xC61BE                        ; T clamp 0xC61B4
0002a13e  ld.hu 0x71be, tp, r9   compare   0002a1f8  ld.hu 0x71b4, tp, r16  compare
0002a146  ld.h  0x71be, tp, r12  CLIP+ <<  0002a20c  ld.h  0x71b4, tp, r11  CLIP+ <<
0002a14c  ld.hu 0x71be, tp, r6   limit-    0002a212  ld.hu 0x71b4, tp, r10  limit-
0002a156  ld.hu 0x71be, tp, r12  clip-     0002a21c  ld.hu 0x71b4, tp, r11  clip-
```

**The defect is dormant at every value ever shipped** (15360 and 3072, both < 32768) and the two loads
are numerically identical there. **It arms only if either cell is ever set to 32768 or above**, at
which point the comparison would still use the large positive value while the positive clip became
NEGATIVE — a wrong-sign limit that would drive the term hard negative on the high side.
⚠ **Standing note for any future build: `0xC61B4` and `0xC61BE` must never be set >= 32768.**
That constraint does **not** apply to `0xC61B6`, `0xC61BC` or `0xC61BA`, which are uniformly `ld.hu`.

## Engaged-only?

**No — the clamp sites execute every tick, but the terms they clamp are zero when disengaged.**
All six cells are read inside `FUN_00028ea6`, which the 1 kHz task calls unconditionally under the
state mask (reachable state 11 sets bit 0x800 in mask 0x930). The disengaged/reset branch sets the PID
terms to zero and rejoins the common path at 0x2A174, so D, P and the sum are all zero with the code
still running. ⇒ **A cal edit here has no effect disengaged, but not because the code is gated —
because its inputs are zero.** [EVIDENCE for the join at 0x2A174 from the earlier decompile; the
per-term zeroing is the same `else` branch documented in Addendum 1.]

## GATE 1 VERDICT for `0xC61B6`

**PASS.** Four live readers, all inside the live `FUN_00028ea6`, all implementing one symmetric clamp
on one term. Three further readers exist but all sit in `[0x2A508, 0x2B422)`, the block proven
unreachable in Addendum 3. **No other function anywhere reads it**, by two methods with an empty
set-difference and every raw hit adjudicated. **No writers.** Lowering it to 2560 or 1280 changes
exactly one clamp, on the D term of the live LKAS rate PID, and cannot flip a sign.

✅ **The naming collision is a brief-level slip only — AUDITED, not assumed.** A grep over every
`build_*.py` and every memory file shows the repo has always had `0xC61B6` = D clamp and `0xC61BA` = I
anti-windup, and one earlier build script even records the same 4/4 and 1/1 `ld.hu` reader counts this
session re-derived independently from bytes. **No build was mis-dosed, nothing needs retracting.**
Write the next dose against **`0xC61B6`** and the record stays consistent.

⚠ One genuine cross-check that DOES bear on a D-clamp dose, from the kit's own record and worth
re-stating here: **`0xC61BE` (the sum clamp, 15360) is the binding constraint on D, not D's own
clamp.** P alone already fills 0xC61BE at low override index, so D is discarded whenever it matters.
That cuts both ways for a *lowering* dose — reducing 0xC61B6 to 2560 or 1280 will bite only in frames
where D was not already being discarded downstream. **Size the dose against the sum clamp, not against
D's own headroom**, or the result risks being another uninterpretable null.


---

# ADDENDUM 5 (2026-09-06) — is there a cal-parameterised slew on the LKAS SETPOINT?

**ANSWER: (a) CLEAN NULL, positive-controlled. (b) The 32 is an IMMEDIATE, not a cal; no cal filters
dE; the setpoint and feedback halves of dE cannot be scaled separately. (c) The named upstream slew
cals are not on this path.**

## The setpoint path, freshly disassembled — map output to E is THREE instructions

```
00029d20..00029d6c   assist-map LERP: a memoryless knot walk (sld.hu over the x-knot array)
                     + divq linear interpolation.  NO state, NO previous-value blend.
00029d6c  mulh  r13, r16          ; r16 = sp          <- THE ASSIST-MAP OUTPUT
00029d6e  ld.hu 0x72e4, tp, r10   ; cal(0xC62E4) = 4  (used later, for the I path)
00029d72  st.h  r16, -0x6a32, gp  ; publish sp        <- DEAD: 0 readers, see below
00029d76  shl   0x5, r16          ; r16 = sp * 32     <<<< THE 32x -- AN IMMEDIATE (bytes c582)
00029d78  sub   r26, r16          ; r16 = E = 32*sp - fb
00029d7a  mov   r16, r6
00029d7c  sar   0x5, r6           ; E >> 5, back into sp units, for the 0xC62E4 test
```

**Between the map output and the error there is one publish, one shift and one subtract.** No filter,
no accumulator, no cal.

## (a) The structural test, positive-controlled: a slew NEEDS a state cell, and there is none

A slew limiter, first-order lag, hold or ramp is impossible without a RAM cell holding the previous
value. So the decisive test is: **is any gp cell BOTH written and read inside the setpoint region?**

| region | cells both written and read |
|---|---|
| **setpoint, `[0x29A48, 0x29DA0)`** (your join point to E) | **ZERO** |
| **POSITIVE CONTROL — the known output-lag filter, `[0x2A174, 0x2A1B4)`** | **`gp-0x3d3c`** — `ld` at `0x2A178`, `st` at `0x2A1B0`. Found, as it must be. |

**The control finds the one filter state that exists in this function; the same scan over the setpoint
region finds nothing.** ⇒ **There is no slew, lag, hold, interpolation or per-tick ramp on sp on the
engaged path, cal-parameterised or otherwise.** The question "what value would spread a step over ~10
ticks at DC gain 1" has no answer because **there is no cal in the path to give such a value to.**

Corroborating detail: `gp-0x6a32`, the published sp, has **2 writers** (`0x29D72` live, `0x2AC68` in
the unreachable duplicate) and **ZERO readers** — nothing reads sp back, so no feedback path exists
that could be turned into a filter either.

**The one historical candidate, and it is already dead.** `cal(0xC63CC) = 0` (V282 = stock) was pitched
in a prior session as "switching on a dormant LKAS slew limiter" and **killed by that same session**:
the rate-limited state is an **ADDITIVE term**, so enabling it ADDS command content rather than
filtering it — the opposite of the intent. Today's census adds a second, independent reason:
**`0xC63CC` has exactly ONE reader image-wide, at `0x276C2`, which is not inside `FUN_00028ea6` at
all.** It is not on this PID's setpoint path. [[feedback_audit_your_own_claims_before_others_act_on_them]]

## (b) The 32, the dE filter, and separating setpoint from feedback

- 🛑 **The 32 is an IMMEDIATE, not a cal**: `shl 0x5, r16` at **`0x29D76`**, 2 bytes, `c582`.
  Changing it is a **code edit**, and it would rescale E for **P, I and D simultaneously** — it is
  applied to sp *before* the subtraction, so it sets the whole error scale, not the setpoint's share.
- 🛑 **No cal filters dE.** The D chain is `sub r27,r8` (dE) at `0x29EE2` → `mul r7,r8` (Kd) at
  `0x29EE4` → `sar 0x3` at `0x29EEC` → clamp `0xC61B6`. **Nothing sits between the difference and the
  gain.** dE is a plain 1-tick backward difference.
- 🛑 **The setpoint and feedback halves of dE CANNOT be scaled separately, structurally.** dE is formed
  on the already-combined E (`E − E_prev`), so both halves inherit the same `shl 5` and the same
  subtraction. Separating them is not a cal question at all; it would need new code.
- **`0xC6C42` = 4 has NO analogue here.** That cell is the difference window `D` of the *torque-rate*
  producer `FUN_0007e74a` feeding `gp-0x4f62` (the r24 lane) — a different function and a different
  signal. The LKAS PID's D has no window cal.
- **One cal DOES sit on the error right after it is formed — but it is the INTEGRATOR's, and it is
  inert.** `0xC62E4` = 4 (V282 = stock), read 4x live (`0x29D6E`, `0x29D84`, `0x29D8C`, `0x29D96`) plus
  3 in the unreachable block, in the classic 4-read symmetric-clamp shape on `E >> 5`. Its result feeds
  the `mul r6, r9` at `0x29DA8` against **Ki**, i.e. the integrator — and **Ki = `0xC63E6` = 0**, so it
  does nothing today and it is not on the setpoint or on D.

## (c) The named upstream slew cals — not on this path

| cell | V282 | stock | verdict |
|---|---|---|---|
| `0xC693E` NORMAL slew curve | 358 | 358 | **NOT on the LKAS path.** Prior session re-confirmed it belongs to a different lane (`clamp(gp-0x4f60) + gp-0x6b4a`, with `0xC616C` = 0 forcing `gp-0x6b4a` = 0). Byte-stock. |
| `0xC6384` assist-map slope cap | 2048 | 2048 | Same lane, same verdict. **Not the LKAS setpoint.** |
| `0xC61D6` shaper slew step | **0** | 0 | On the **EME shaper output**, far downstream of the setpoint — and it is 0, i.e. no ramp. |
| `0xC6206` / `0xC6208` governor slew | 512 / 205 | 512 / 205 | Downstream of the entire PID (Addendum 2). Not a setpoint lever. |

⚠ **A BOUNDARY I DID NOT CROSS, stated rather than papered over.** I traced the LERP *index* only as
far back as `r22` at `0x29D20`. Inside `FUN_00028ea6` the index chain is memoryless — a multiply, a
`sar 0x10`, a `sar 0x6`, and a symmetric byte clamp against `cal(0xC64F0)` = 240 at
`0x29CD0`/`0x29CE0`/`0x29CE6` (note the `0x74f0`/`0x74f1` **ld.bu parity pair**, the documented trap) —
so **nothing inside this function can spread a step**. But I did **not** trace the index back through
the 100 Hz task to the 0xE4 decode, so **I cannot rule out a slew cal upstream of this function**, and
I am not claiming one way or the other.
**Exact next step to close it:** identify the producer of the value in `r22` at `0x29CBC` (it is set
before `0x29C00`), then census that gp cell's writers in the 100 Hz task. I stopped rather than
hand-trace registers backwards across ~350 bytes, which is the exact failure mode
[[reference_accord_c61be_sum_clamp_starves_d_term_v276_oscillation]] records for this function
("Ghidra's decompile reuses `r9`/`r27` across the P/D blocks and misreads easily") and which I caught
myself starting to do on `r27` this session.

## What this means for the lever you are looking for

**There is no cal-only setpoint-side lever of the shape you want.** The 100 Hz staircase reaches D
unfiltered because nothing in the setpoint path has memory, and the only memory in the whole PID is the
feedback EMA (`gp-0x3d30`) and the output lag (`gp-0x3d3c`) — **both on the feedback/output side, which
is precisely the side you are trying not to touch.**

That leaves, as cal-only options: the **output lag poles `0xC63EC`/`0xC63EE`** (GATE 1 passed in
Addendum 3, and they act after the sum clamp so they do not clip the feedback derivative), or **Kd
itself** via the flat record `0xE511C`. Both change the loop rather than the staircase. **Spreading the
staircase specifically would require a code edit**, which is outside what you asked me to report and
which I am not proposing.


---

# ADDENDUM 6 (2026-09-06) — closing the upstream boundary: CAN 0xE4 to the map index

**VERDICT: CLEAN NULL, extended all the way to the CAN byte. There is NO cal-parameterised slew, rate
limit, EMA or hold anywhere between the 0xE4 STEER_TORQUE byte and the assist-map LERP index. Every
stage is memoryless: one raw store, two symmetric clamps, one multiply, two shifts, one absolute
value.**

## 🛑 A correction to my own Addendum 5 reading, caught by continuing the trace

In Addendum 5 I wrote that the LERP index is `r22` = the clamped raw command. **That was wrong.**
`r22` is **REASSIGNED at `0x29D10` (`mov r7, r22`)** immediately before `0x29D20 mov r22, r9`. The
index is `r7`, the *scaled and clamped* value — not the raw command. The Addendum 5 conclusion (no
filter on the setpoint path) is unaffected, but the identity of the index was mis-stated and is
corrected here. This is the third time this session that hand-tracing registers in this function has
produced a wrong intermediate; the dataflow tool and a forward re-read caught it.

## The full chain, CAN byte to index — verified stage by stage

**Stage 1 — CAN decode. `FUN_00052676` (0x52676-0x527D9).**
```
000526f2  st.h  r10, -0x69ae, gp        ; gp-0x69ae = the raw 0xE4 STEER_TORQUE
```
`r10` is stored **unmodified**. The `FUN_00049a90(-0x4000, .., 0x4000)` clamp call at `0x526DA` acts on
a *different* register (`r6 = -(sxh(r10) << 2)`), not on what reaches `gp-0x69ae`.
**No filter, no slew, no rate limit at the decode.**
`gp-0x69ae` census (scanner control `gp-0x3d3c` → 2W/2R, PASS): **4 writers** — `0x5268C`, `0x526F2`,
`0x52726`, `0x527C6` — of which `0x5268C`, `0x52726`, `0x527C6` are fed by `movea 32767` (fault/invalid
sentinels, identified by the same immediate scan that found the `gp-0x6c2c` sentinel in Addendum 4), so
**`0x526F2` is the sole live decode store.** **3 readers**: `0x29032`, `0x29124` (both FUN_00028ea6),
`0x4E840`.
⚠ `get_function_callers` on `FUN_00052676` returns none — it is reached through the CAN-RX mailbox
dispatch table, not a `jarl`. I did not trace that table; it does not affect the filter question.

**Stages 2-8 — inside `FUN_00028ea6`.** Integer mirror, each line annotated with its address:

```python
CMD  = s16(gp_0x69ae)                      # 0x29032  ld.h  (SIGNED)
# L = a LERP-interpolated symmetric limit  # 0x2902C divq / 0x29030 add
r22  = max(-L, min(CMD, +L))               # 0x29036 andi / 0x2903A-0x29044 cmovle
r7   = (Q16 * r22) >> 16                   # 0x29CB8 andi 0xffff / 0x29CBC mul / 0x29CC0 sar 0x10
r7   = r7 >> 6                             # 0x29CD6  sar 0x6        -> total >> 22
r7   = max(-240, min(r7, +240))            # 0x29CD0 / 0x29CE0 / 0x29CE6, cal(0xC64F0) = 240
idx  = abs(r7)                             # 0x29CF6 cmp / 0x29CFA subr
gp_0x674b = idx & 0xFF                     # 0x29D12 zxb / 0x29D14 st.b   (published knot index)
# assist-map pointer table base 0xC9A88    # 0x29CFC  mov 0xc9a88, r16
r22  = r7                                  # 0x29D10  <<< THE REASSIGNMENT I MISSED IN ADDENDUM 5
r9   = r22                                 # 0x29D20  -> THE LERP INDEX
sp   = LERP_0xC9A88[selector](idx)         # 0x29D20-0x29D6C, memoryless knot walk + divq
```

**Not one stage has a state variable.** The structural test from Addendum 5 (is any gp cell both
written and read in the region?) covers `[0x29A48, 0x29DA0)` and returns **ZERO**, against a positive
control that finds `gp-0x3d3c` in the known lag-filter region. Stages 1-3 add only a store and two
clamps.

## Cal cells on the path — all clamps, none a filter

| cell | V282 | stock | what it does | reachable range |
|---|---|---|---|---|
| **`0xC64F0`** | **240** (byte) | 240 | symmetric clamp on the scaled index, `0x29CD0`/`0x29CE0`/`0x29CE6`. ⚠ uses the **`0x74f0`/`0x74f1` `ld.bu` parity pair** — the documented trap; a scanner that assumes one parity reads the neighbouring cell | 0-255 (byte); it sets the map X ceiling |
| the ±L limit | LERP | — | symmetric clamp on the raw command, `0x2902C`-`0x29044`; interpolated, not a single cell | — |
| `0xC9A88` | table | — | the assist-map pointer table base, `0x29CFC`. Record: **CONFIRMED LINEAR**, Y/X = 4.30 at selector 7 | per-slot records |

**A clamp is not a slew.** None of these has memory, so no value of any of them spreads a step over
multiple ticks. **The answer to "what cal value gives DC gain 1 and a ~10-tick spread" remains: no such
cal exists on this path.**

## The "1-5 Hz low-pass" on the LKAS command lane: NOT FIRMWARE

**[EVIDENCE]** Every stage from the CAN byte to the map index is memoryless — a raw store, two
symmetric clamps, a multiply, two shifts and an absolute value. **A first-order low-pass cannot exist
here; there is nowhere to keep the state.** So the "1-5 Hz low-pass" in the record is **either
openpilot-side command shaping or a mis-attribution to this lane.** It is not in the EPS firmware
between 0xE4 and the setpoint. ⚠ I am asserting this for **this path only** — I did not audit
openpilot, and the record's phrasing may refer to a different signal.

⭐ Related, and worth not losing: `gp-0x3d34` **is** a genuine one-writer/one-reader state cell in this
function (`st.w 0x29080`, `ld.w 0x28F78`) — but it sits in the **feedback / torque-sensor** block, not
on the command path. It is a third filter state alongside `gp-0x3d30` and `gp-0x3d3c`, and all three
are on the feedback/output side.

## Per-frame index step at turn onset

🛑 **I went to pin this and it killed my own draft answer. The scale is NOT a constant.** My first
write-up said idx = CMD/16, reproducing the record's figure from full-scale/240. Reading
`0x29C9C`-`0x29CB8` shows that is not derivable:

```
00029c9e  ld.hu -0x2, ep, r16      \
00029ca4  sld.hu 0x0, ep, r7        |  a SECOND knot walk + linear interpolation
00029ca8  mul   r13, r6, r0         |  (divq at 0x29CAE), output r6
00029cae  divq  r7, r6, r0          |
00029cb2  add   r8, r6             /
00029cb4  mulu  r6, r10, r0        ; r10 = r10 * r6        <- the "Q16 factor" is a LERP OUTPUT
00029cb8  andi  0xffff, r10, r7    ; r7 = low 16 bits = the Q16 fraction
```

**The CMD → idx scale is itself table-driven**, so the counts-per-index-step is **command-dependent,
not a fixed 1-per-16.** The record's "idx ~ cmd/16" is therefore a *local linearisation*, valid only
where that LERP is flat, and **I cannot confirm or refute it without reading that second LERP's knot
records** — which I did not do.

**What I CAN state as EVIDENCE:** the index saturates at `cal(0xC64F0) = 240`, the chain is linear in
CMD *for a fixed LERP output*, and the whole transform is memoryless. So at a turn onset the index step
per frame is `(dCMD * Q16_lerp) >> 22`, clamped at 240 — **and whatever its size, it arrives as a
single 1 kHz tick's discontinuity followed by 9 flat ticks**, which is the impulse train into D your
brief describes. **The staircase is real; its step size is command-dependent.**

**Exact next step for the number:** read the knot records of the LERP feeding `r6` at `0x29CB2` (walk
starts near `0x29C60`), then evaluate `(dCMD * Q16) >> 22` at the command amplitudes of a turn onset.
⭐ I am flagging this rather than shipping the 16, because the 16 was the kind of number that reads as
measured once it is in a report — and I had already written it down before I checked.

## Bottom line for the lever

**The staircase reaches D unattenuated, and the firmware offers no cal to soften it — confirmed from
the CAN byte forward, not just inside the PID.** Every cal on the path is a clamp. The only memory in
the whole chain lives on the feedback/output side (`gp-0x3d30`, `gp-0x3d34`, `gp-0x3d3c`), which is the
side the D-clamp adversarial pass told you not to touch. **Cal-only, there is nothing here.**
