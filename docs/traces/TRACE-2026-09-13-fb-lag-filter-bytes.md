# TRACE 2026-09-13 — the LKAS feedback-lag filter, byte-exact

**Agent:** `tracer` (firmware-codepath-tracer), subagent of `main`.
**Tooling:** GhidraMCP only for disassembly (`disassemble_bytes dry_run:true`, `disassemble_function`,
`search_instructions`, `get_function_callers`); Python for every byte-level census and for the integer
mirror. No mutating Ghidra call was made; nothing was saved to the shared project.
**Program:** `code.bin` (stock dump, 2086 functions) confirmed current via `list_open_programs`.
**Constants:** `gp = 0xFEDF8000`, `tp = 0xBF000`. Anchor check performed: `ld.h 0x73e8[tp]` at `0x28F8A`
reads the halfword whose bytes at file offset `0xC63E8` are `9b 03` = 923, the value the record ascribes
to the feedback pole `a`. `0xBF000 + 0x73E8 = 0xC63E8` ✔ — no off-by-0x1000.

Every claim below is marked **EVIDENCE** (with the address and the method) or **BELIEF**.

---

## 0. Image-identity check — the brief's premise is WRONG by two bytes

**EVIDENCE.** `0x28F00–0x2A260` is **not** identical between `stock_fw_dump/code.bin` and
`_v282_…_plain_image.bin`. Exactly two bytes differ:

| offset | stock | V282 | meaning |
|---|---|---|---|
| `0x2A1F0`–`0x2A1F1` | `6c 74` (disp `0x746C`) | `d0 7c` (disp `0x7CD0`) | displacement of the forward-LKAS gain load |

This is a **documented, intentional** V282 delta — row 2 of
`docs/review/V282-CUMULATIVE-NONSTOCK-DELTA-2026-09-09.md`: the V57 lever, lost in the V38 rebase and
restored in V81, which repoints the forward gain off the shared sensor-scale cal `0xC646C` onto the
private cell `0xC6CD0`. It sits at `0x2A1F0`, **downstream of every address in tasks 1–6**.

Everything this trace touches is byte-identical between the two images: the filter `0x28F4C–0x28FBE`,
the bail block `0x290B0–0x290D8`, the guard `0x29A48–0x29A70`, the error `0x29D72–0x29D78`, the D path
`0x29EE0–0x29F2E`, the sum clamp `0x2A13E–0x2A162` and the reset `0x2A164–0x2A19C`.

Full-image diff restricted to `[0x13000, 0x100000)` (never whole-file — the `0xFF` filler trap):
**1,984 differing bytes in 280 clusters**, consistent with the delta document. SHA256 of
`stock[0x28F00:0x2A260]` = `722f210f…9423`; V282 = `13a09267…a6c`.

⇒ Working on `code.bin` is correct for this trace. State it as "identical **except** `0x2A1F0`", not
"identical".

---

## 1. The filter, byte-exact

`disassemble_bytes(0x28F30, 160, dry_run:true)`. Inside `FUN_00028ea6` (body `0x28EA6–0x2A30D`).

```
;--- guards, all four BAIL to 0x290B0 -----------------------------------------
28F30  addi  0x6400,r15,r8        r15 = ld.h -0x4f60[gp]   (sensor)
28F38  cmp   r16,r8 ; bc 28F40    r16 = 0xC801
28F3C  jr    290B0                BAIL 1  (sensor implausible)
28F40  addi  0x1,r6,r12           r6 = ld.b -0x6752[gp]  (arm flag, signed byte)
28F44  cmp   0x3,r12 ; bc 28F4C
28F48  jr    290B0                BAIL 2  (arm flag not in {-1,0,+1})
28F4C  ld.h  -0x6a56,gp,r7        x  = SIGNED 16-bit steering rate
28F50  addi  0x2ee0,r7,r11        r11 = x + 12000
28F54  addi  -0x5dc1,r11,r0       flags only; CY iff r11 >= 24001 (unsigned)
28F58  bnc   28F5E                continue iff -12000 <= x <= 12000
28F5A  jr    290B0                BAIL 3  (rate implausible)   <-- a BAIL, NOT a clamp
28F5E  cmp   r0,r14 ; bne 28F66   r14 = (arm flag != 0)
28F62  jr    290B0                BAIL 4  (arm flag == 0)
;--- the filter ---------------------------------------------------------------
28F66  ld.bu -0x3d2c,gp,r9        SENTINEL
28F72  cmp   0x1,r9 ; mov 0x1,r1
28F76  bne   28F82                sentinel != 1  ->  cold start
28F78  ld.w  -0x3d34,gp,r6        (sibling state, the OTHER filter)
28F7C  ld.w  -0x3d30,gp,r26       s   <-- STATE CELL, 32-BIT ld.w
28F80  br    28F86
28F82  mov   0x0,r6
28F84  mov   0x0,r26              s := 0
28F86  ld.hu 0x73ea,tp,r16        b = [0xC63EA] = 1560   UNSIGNED halfword
28F8A  ld.h  0x73e8,tp,r9         a = [0xC63E8] =  923   ** SIGNED halfword (ld.h) **
28F8E  mul   r16,r7,r0            r7 = low32(x * b)      high word DISCARDED into r0
28F92  mul   r26,r9,r0            r9 = low32(s * a)      high word DISCARDED into r0
28F96  ld.hu 0x72e6,tp,r13        clamp = [0xC62E6]
28F9A  sar   0xa,r7               floor(x*b / 1024)      <-- SEPARATE floor
28F9C  ld.hu 0x72e6,tp,r14        clamp again
28FA0  sar   0xa,r9               floor(s*a / 1024)      <-- SEPARATE floor
28FA2  add   r7,r9                s_new
28FA4  add   r9,r26               out = s_old + s_new    <-- the two-sample sum
28FA6  cmp   r13,r26
28FA8  st.w  r9,-0x3d30,gp        s := s_new             <-- 32-BIT st.w
28FAC  ble   28FB2
28FAE  mov   r14,r26              out := +clamp
28FB0  br    28FBE
28FB2  subr  r0,r14               r14 = -clamp
28FB4  cmp   r14,r26
28FB6  bge   28FBE
28FB8  ld.hu 0x72e6,tp,r26
28FBC  subr  r0,r26               out := -clamp
28FBE  mov   r26,r16              (r26 now carries the clamped feedback)
```

### 1.1 The recurrence

```python
# tick n, exactly as 0x28F86..0x28FA8 executes
s_new = (a * s) >> 10  +  (b * x) >> 10     # two SEPARATE arithmetic shifts
out   = s + s_new                            # r26 before the clamp
s     = s_new                                # 0x28FA8 st.w
out   = max(-C, min(+C, out))                # C = [0xC62E6]
```

DC gain `= 2b / (1024 - a)`. At (923, 1560): `3120/101 = 30.8911` — **EVIDENCE** that the record's
"DC 30.89 per raw count" is exact.

### 1.2 Answers to the specific questions in task 1

| question | answer | evidence |
|---|---|---|
| which cell holds `s`, and its **width** | `gp-0x3d30` = `0xFEDF42D0`, **32-bit** | `ld.w` at `0x28F7C`, `st.w` at `0x28FA8` — both the `.w` form (`hw1` bit 0 set: `d1 c2` = `0xC2D1`, disp `0xC2D0`) |
| does 185,000 fit | yes, with ~11,600× headroom | 32-bit signed |
| multiply width | **32×32 → low 32**, high word discarded | `mul r16,r7,r0` / `mul r26,r9,r0` — `reg3 = r0`, so the high word of the 64-bit product is thrown away. No intermediate is narrowed to 16 bits anywhere in the chain |
| overflow headroom | worst case `a·s ≈ 1.9e8` vs `2^31 = 2.1e9`, **≈11×** | `|x| ≤ 12000` (§1.3), `|s|_DC = b·12000/(1024−a)`; at (1011,201) that is 185,538 and `a·s = 1.88e8` |
| `sar 0xa` semantics | arithmetic, floors toward −∞, applied to **each term separately** | `0x28F9A` and `0x28FA0` are on different registers, `add` is at `0x28FA2` |
| the two-sample sum | `out = s_old + s_new`, stored state is `s_new` only | `add r9,r26` at `0x28FA4` **before** `st.w r9` at `0x28FA8` |
| the clamp | `±[0xC62E6]`, loaded **`ld.hu`** so it is unsigned 0…65535 | `0x28F96 / 0x28F9C / 0x28FB8`; stock 7680, V282 **46080** |
| is `a` capped | **yes, at 32767** — `a` is read with `ld.h`, signed | `0x28F8A` opcode field `0x39`, `hw1` bit 0 clear ⇒ `ld.h`. A cal value ≥ 32768 would be read NEGATIVE |
| is `b` capped | at 65535 — `ld.hu`, unsigned | `0x28F86` |

### 1.3 Where `x` is produced, and whether it is clamped

> ⚠ **ERRATUM 2026-09-20 (V294 adversarial pass, verified by the orchestrator from the bytes):** the count is
> **29, not 30** — the alleged `ld.bu` at `0x14B1E` (`84 ff aa 95`) is `jarl 0x5E0C8,lp` (`hw2` bit 0 = 0, even
> target, reg2 = 31 = lp), the `ld.bu`/`jarl` opcode collision the `firmware-decompile` skill documents. The
> 25 `ld.h` + 4 `st.h` stand. Nothing downstream of this count changes.

**EVIDENCE.** `gp-0x6a56` has 30 accesses image-wide — **25 `ld.h`, 4 `st.h`, 1 `ld.bu`**. All four
writers are in one block at `0x3F7A0–0x3F822`, and they **saturate**:

```
3F7A0  mul   r16,r15,r0
3F7A4  sar   0xf,r15             Q15 scale
3F7A6  mul   r15,r6,r0
3F7AA  addi  0x2ee0,r6,r0 ; bgt 3F7C2       (r6 > -12000 ?)
3F7B4  movea -0x2ee0,r0,r6
3F7B8  st.h  r6,-0x6a56,gp       x := -12000        (saturate low)
3F7BC  st.h  r6,-0x4ca6,gp       ** LOCKSTEP MIRROR **
3F7C2  addi  -0x2ee0,r6,r0 ; blt 3F7DA       (r6 < +12000 ?)
3F7CC  movea 0x2ee0,r0,r6
3F7D0  st.h  r6,-0x6a56,gp       x := +12000        (saturate high)
3F7D4  st.h  r6,-0x4ca6,gp       mirror
3F7DC  sxh   r6
3F7E0  st.h  r6,-0x6a56,gp       x := r6            (in range)
3F7E4  st.h  r6,-0x4ca6,gp       mirror
3F81E  st.h  r0,-0x6a56,gp       x := 0             (fault/reset path)
3F822  st.h  r0,-0x4ca6,gp       mirror
```

⇒ **`x` is already saturated to ±12000 by its producer**, so the `0x28F50` test is a *redundant
plausibility bail*, not the operative clamp. In normal operation it never fires.

🛑 **GATE-1 finding for any cave that writes `gp-0x6a56`:** every writer pairs the store with a store to
**`gp-0x4ca6`**, and the pair is compared before use (`cmp r14,r12 ; bne 0x3F7EA` → `jarl 0x6B9FA`, a
fault handler). **EVIDENCE** for the mirror's existence and the compare; **BELIEF** that `0x6B9FA` is a
DTC/fault路 — I did not decompile it. A hook that writes `gp-0x6a56` without the mirror will desync the
lockstep pair.

---

## 2. Reader census of `tp+0x73E8` and `tp+0x73EA` — GATE 1 PASSES

### 2.1 Method

A two-encoding Python scanner over the whole 1 MiB image
(`scratchpad/census.py`), decoding **effective** displacements rather than matching raw halfwords:

* **4-byte form** — `hw0 = (reg2<<11) | (opcode<<5) | reg1`, `reg1 ∈ {4 = gp, 5 = tp}`,
  `opcode ∈ 0x38…0x3F`, with the per-opcode displacement rules derived empirically from this binary:
  `0x38 ld.b` / `0x3A st.b` → `disp = hw1`; `0x39`,`0x3B` → `.w` if `hw1` bit 0 else `.h`, `disp = hw1 & 0xFFFE`;
  `0x3C/0x3D ld.bu` → `disp = (hw1 & 0xFFFE) | (opcode & 1)` (the bit-5 parity trap);
  `0x3E/0x3F ld.hu` → `disp = hw1 & 0xFFFE`.
* **6-byte extended-displacement form** — `hw0 & 0xFFE0 ∈ {0x0780, 0x07A0}`,
  `disp = (sext16(hw2) << 7) | ((hw1 >> 4) & 0x7F)`, `reg2 = (hw1 >> 11) & 0x1F`
  (the 0-indexed formula from `memory/accord/firmware/accord-gp4f60-two-encodings-enumeration-trap.md`).
* **Absolute-pointer form** — every LE32 in the image equal to the target address.
* **`movhi`+`movea` pair** building the target address.

**Positive controls — the scanner is not self-controlled.** It independently reproduces:
* all **30** `gp-0x6a56` accesses, matching the prior record's 25 `ld.h` + 4 `st.h` + 1 `ld.bu` exactly;
* the output-lag pole pair — `0xC63EC` at `0x2A184` and `0x2A8A2`, `0xC63EE` at `0x2A174` and `0x2A892`
  — i.e. V289's notch hook *and* the known duplicate-orphan block, both found without being told about them;
* the 4 six-byte `gp-0x6752` accesses at `0x48E56`–`0x48E88`, proving the 6-byte path is live in the scanner
  (one hand-verified: `84 07 e5 42 31 ff` → `(sext16(0xff31)<<7) | ((0x42e5>>4)&0x7F) = −26496 + 46 = −0x6752` ✔,
  `reg2 = (0x42e5>>11)&0x1F = 8` ✔);
* `scan_abs` control — it finds `0xCB844` at file offset `0x28FCE`, the imm32 of the `mov 0xcb844,r8`
  at `0x28FCC`.

### 2.2 Result

| cell | 4-byte | 6-byte | abs ptr | movhi/movea | **total** |
|---|---|---|---|---|---|
| `tp+0x73E8` = `0xC63E8` (`a`) | 1 — `ld.h` @ **`0x28F8A`** | 0 | 0 | 0 | **1 reader, 0 writers** |
| `tp+0x73EA` = `0xC63EA` (`b`) | 1 — `ld.hu` @ **`0x28F86`** | 0 | 0 | 0 | **1 reader, 0 writers** |

**Ghidra, independently:** `search_instructions(operand_pattern="0x73e8")` →
`match_count: 1`, `0x28F8A`, `instructions_scanned: 183576`, `truncated: false`.

**Set-difference of the two methods is EMPTY.** No disagreement to adjudicate.

⇒ **EVIDENCE: a cal change to `0xC63E8` / `0xC63EA` is PRIVATE to this filter.** Nothing else in the
image reads them, by any encoding, by pointer, or by constructed address.

**Residual risk considered and closed:** a LERP/table walk striding *into* these cells would not appear
as a direct reference. The nearest constructed base in the image is `0xCB844` (`0x28FCC`) and
`0xCBB54` (`0x29F08`); `scan_abs` finds **no LE32 anywhere in `[0xC6300, 0xC6400)`**, so there is no
table base from which a stride could reach `0xC63E8`. The neighbours are themselves singly-read
(`0xC63E2` @ `0x28F6E`, `0xC63E4` @ `0x28F6A`, `0xC63E6` Ki @ `0x29D9C` + `0x2AC8E`), which is the
signature of scattered scalars, not of an array.

### 2.3 Flight precedent, read from the built images (not from a build script)

**EVIDENCE.** `_v289_…_plain_image.bin` carries `0xC63E8 = 875`, `0xC63EA = 2301`
(stock/V282: 923, 1560), and a page CRC at `0xC6FFC` of `fe780477` against V282's `75eadf72`.
DC held: `2·2301/(1024−875) = 30.886` vs `30.891`, −0.02 %. Corner moved `16.53 → 25.03 Hz`.
V289 rev 1 flew on routes r62/r63 with no fault. **That is the precedent; §2.2 is the proof.**

---

## 3. `s` and `r26` — readers, writers, liveness

### 3.1 The state cell is private

**EVIDENCE.** `gp-0x3d30` (`0xFEDF42D0`) has **exactly two accesses image-wide**:
`ld.w` at `0x28F7C` and `st.w` at `0x28FA8`. Both inside the filter. **No side lane, no UDS record
packer, no 427 packer, no diagnostic reader touches `s`.** Its neighbours are equally private —
sentinel `gp-0x3d2c`: `ld.bu` `0x28F66` + `st.b` `0x290D4`; sibling `gp-0x3d34`: `ld.w` `0x28F78` +
`st.w` `0x29080`.

⇒ Nothing outside this filter can observe a slower state. **No downstream consumer to worry about.**

### 3.2 `r26` liveness — a correction to the prior record

An exhaustive `r26` sweep over all **1,874** instructions of `FUN_00028ea6`:

```
28EA6  prepare { …,r26,r27,… },0x1     r26 is CALLEE-SAVED
28F7C  ld.w  -0x3d30[gp],r26
28F84  mov   0x0,r26
28F92  mul   r26,r9,r0
28FA4  add   r9,r26
28FA6  cmp   r13,r26
28FAE  mov   r14,r26
28FB4  cmp   r14,r26
28FB8  ld.hu 0x72e6[tp],r26
28FBC  subr  r0,r26
28FBE  mov   r26,r16              <-- filter output published into r16
290B6  mov   0x0,r26              <-- ** A WRITE, on the BAIL path **
29D78  sub   r26,r16              <-- E = 32*sp - r26
29F76  mov   r13,r26              <-- rewritten with LERP scratch  (record CONFIRMED)
29F96  zxh   r26
29FE8  cmovne r26,r9,r23
2A0C8  cmp   r0,r26
2A30A  dispose …
```

🛑 **The prior record's "zero intervening accesses over 3,514 bytes" is not exact.** There is one
intervening **write**, `0x290B6 mov 0x0,r26`. It lies on the BAIL path (`0x290B0–0x290C0`), which the
normal path jumps over via `br 0x290C2` at `0x290AE`, so:

* **zero intervening *readers*** — TRUE;
* **`r26` survives `0x28FBE → 0x29D78` on the path that reaches it** — TRUE;
* but `r26` at `0x29D78` is **either** the clamped filter output **or** literal `0` from the bail.
  A hook that assumes "r26 always carries the filter output at `0x29D78`" is wrong on the bail path.

`0x29F76 mov r13,r26` (the LERP scratch rewrite) is **CONFIRMED**, and `r26`'s scratch value is
genuinely consumed at `0x29FE8 cmovne r26,r9,r23`.

---

## 4. The D path

```
29E5E  ld.w   -0x6cf8,gp,r8       E_prev, ** 32-BIT ld.w **, cell gp-0x6cf8
29E62  mov    0x177001,r13        1,536,001
29E68  mov    0xfff44800,r10      -768,000
29E70  mov    r8,r7
29E72  sub    r10,r7              r7 = E_prev + 768000
29E74  cmp    r13,r7              CY iff r7 < 1536001 (unsigned)
29E7E  cmovnc r16,r8,r27          r27 = (E_prev OUT of +-768000) ? E_now : E_prev
...
29EDE  zxh    r7                  Kd from the LERP walk, ZERO-extended (unsigned 16)
29EE0  mov    r16,r8              r8 = E   (the FULL error)
29EE2  sub    r27,r8              dE = E - E_prev            <-- ON THE FULL ERROR
29EE4  mul    r7,r8,r0            r8 = dE * Kd   (low 32)
29EE8  ld.hu  0x71b6,tp,r10       D clamp = [0xC61B6] = 10240
29EEC  sar    0x3,r8              D = (dE*Kd) >> 3
29EEE..29F06  clamp D to +-[0xC61B6]
29F2E  mov    r8,r27              r27 := D  (r27 is REUSED; E_prev is gone)
...
29F18  sar    0x7,r2              P = (Kp product) >> 7
29F1E  add    r9,r2               + I            (r9 = Ki * deadband-excess; Ki = 0 ⇒ inert)
29F24  add    r8,r2               + D            <-- D ADDED TO P
29F2A  mov    r2,r22              publish copy -> gp-0x6b34 at 0x2A1A2
...
2A0B4  mulu   r9,r23,r0
2A0B8  andi   0xffff,r23,r12
2A0BC  sar    0x8,r12
2A0BE  mul    r2,r12,r0           post-gain product of the PID SUM
2A0C2  sar    0x8,r12
2A0C4  br     2A13E
2A13E  ld.hu  0x71be,tp,r9        sum clamp = [0xC61BE] = 15360
2A142  cmp    r9,r12 ; ble 2A14C
2A146  ld.h   0x71be,tp,r12       +clamp   (** ld.h, SIGNED — see the latent defect below **)
2A14C..2A15C  -clamp branch  (ld.hu + subr + sxh)
2A160  sxh    r12                 in-range branch
```

**Confirmations (all EVIDENCE):**

* `0x29EE2 sub r27,r8` computes `dE = E − E_prev` on the **FULL** error `E = 32·sp − r26` — both the
  setpoint and the feedback parts. `r16` is written by `0x29D78 sub r26,r16` and is not rewritten
  before `0x29EE0`.
* **`E_prev` lives in `gp-0x6cf8`, 32-bit** (`ld.w` `0x29E5E` / `st.w` `0x2A18C`), guarded by a
  plausibility window `±768,000`. Image-wide the cell has 4 accesses: the two above plus `ld.w`
  `0x2AD4A` and `st.w` `0x2B058`, both inside **`FUN_0002a93a`** (body `0x2A93A–0x2B06F`), which
  `get_function_callers` reports as having **no callers** — the known dead twin.
* `×Kd` then **`sar 3`**, then clamp `±[0xC61B6] = 10240` (identical stock and V282).
* **D is added to P (and to the inert I) at `0x29F24`, before the `0xC61BE` sum clamp.** `r2` has only
  five mentions between `0x29F24` and `0x2A0BE` and none of them writes it, so the sum reaches the
  clamp intact. ✔ the brief's claim holds.
* ⚠ **Latent sign defect at the sum clamp, re-confirmed:** the *comparison* at `0x2A142` reads
  `0xC61BE` with **`ld.hu`** (unsigned) but the *positive saturation assignment* at `0x2A146` reads the
  same cell with **`ld.h`** (signed). At 15360 the two agree, so it is inert today; a cal value ≥ 32768
  would compare as positive and assign as negative. **Do not raise `0xC61BE` above 32767.**
* `r27` is reused: it holds `E_prev` at `0x29EE2` and becomes `D` at `0x29F2E` (then published to
  `gp-0x6b36` at `0x2A19C`).

### 4.1 The exact first-tick sequences the brief asked for

Tick period **`Ts = 1 ms`**. This is **EVIDENCE-by-consistency, not a direct scheduler measurement**:
`f_c = −ln(a/1024)/(2π·Ts)` gives 16.53 Hz at the stock `a = 923` (the record's "16.5 Hz") and
**25.03 Hz at V289's byte-read `a = 875`** (V289's own build tag `FBPOLE.25HZ`). Two independent
label↔byte agreements.

**The brief's candidate pairs are not all DC-held.** `DC = 2b/(1024−a)`; target `3120/101 = 30.8911`:

| pair | DC | error | `f_c` | verdict |
|---|---|---|---|---|
| (923, 1560) | 30.8911 | 0.00 % | 16.53 Hz | stock |
| (1005, **293**) | 30.8421 | −0.16 % | 2.98 Hz | ✔ DC-held |
| (1013, **167**) | 30.3636 | **−1.71 %** | 1.72 Hz | ✘ — use **170** (30.9091, +0.06 %) |
| (1020, **60**) | 30.0000 | **−2.88 %** | 0.62 Hz | ✘ — use **62** (31.0000, +0.35 %) |

And (1013, ·) / (1020, ·) are **below** the brief's own 2–8 Hz band. The DC-held pairs that actually
span it:

| target | `a` | `b` | actual DC | actual `f_c` |
|---|---|---|---|---|
| 8 Hz | 974 | 772 | 30.880 (−0.04 %) | 7.97 Hz |
| 6 Hz | 986 | 587 | 30.895 (+0.01 %) | 6.02 Hz |
| 5 Hz | 992 | 494 | 30.875 (−0.05 %) | 5.05 Hz |
| 4 Hz | 999 | 386 | 30.880 (−0.04 %) | 3.93 Hz |
| 3 Hz | 1005 | 293 | 30.842 (−0.16 %) | 2.98 Hz |
| 2.5 Hz | 1008 | 247 | 30.875 (−0.05 %) | 2.51 Hz |
| 2 Hz | 1011 | 201 | 30.923 (+0.10 %) | 2.03 Hz |

**Exact integer sequence of `r26` for a unit step `x = 1` from `s = 0`:**

| pair | `r26[1..8]` |
|---|---|
| (923, 1560) | 1, 2, 2, 2, 2, 2, 2, 2 |
| (1005, 293) | **0, 0, 0, 0, 0, 0, 0, 0** |
| (1013, 170) | **0, 0, 0, 0, 0, 0, 0, 0** |
| (1020, 62) | **0, 0, 0, 0, 0, 0, 0, 0** |

and the resulting `dE` / `D` (Kd = 128, `sar 3`, clamp ±10240, setpoint constant, so `dE = −Δr26`):

| pair | (dE, D) for ticks 1…6 |
|---|---|
| (923, 1560) | (−1, −16), (−1, −16), (0,0), (0,0), (0,0), (0,0) |
| (1005, 293) | all (0, 0) |
| (1013, 170) | all (0, 0) |
| (1020, 62) | all (0, 0) |

### 4.2 🛑 The finding that most matters to the design: lowering `b` opens a quantiser dead zone

**EVIDENCE (from the arithmetic at `0x28F9A`).** The input term is `floor(b·x / 1024)`. It is
**identically zero** for `0 ≤ x < 1024/b`, and for a *constant* small `x` the state never leaves 0, so
the filter output is identically zero — not merely attenuated.

| `b` | `f_c` | dead zone in raw counts | in deg/s (8 counts / deg·s⁻¹) |
|---|---|---|---|
| 1560 (stock) | 16.5 Hz | \|x\| < 0.66 | 0.08 |
| 772 | 8.0 Hz | \|x\| < 1.33 | 0.17 |
| 494 | 5.1 Hz | \|x\| < 2.07 | 0.26 |
| 293 | 3.0 Hz | \|x\| < 3.49 | 0.44 |
| 201 | 2.0 Hz | \|x\| < 5.09 | 0.64 |
| 62 | 0.6 Hz | \|x\| < 16.5 | 2.07 |

Because `sar` floors toward −∞ the dead zone is **asymmetric**: `x = +3` with `b = 293` gives 0, but
`x = −3` gives −1. Over a symmetric small oscillation the mean output is **negative**, not zero.

**Pre-existing, not a regression:** `s = −1` is an absorbing state at *every* `a` in 923…1023
(`floor(−a/1024) = −1` for all `a < 1024`), so `r26` rests at **−2** rather than 0 with `x = 0`. That is
already true on stock. What the edit changes is the **width** of the dead zone, by up to 7.7× at 2 Hz.

**BELIEF:** at the grinding amplitudes the loop actually sees this is probably benign (a few counts),
but it is the first thing to check against the measured `x` distribution before choosing `b`. It has
not been measured here.

---

## 5. Init and reset

### 5.1 The reset mechanism is the sentinel, not the disengage route

**EVIDENCE.** `gp-0x3d2c` is written at exactly one site, `0x290D4 st.b r1,-0x3d2c[gp]`, and `r1` is:

* **`1`** on the normal path (`0x28F74 mov 0x1,r1`);
* **`2`** on the bail path (`0x290B0 mov 0x2,r1`).

The filter loads `s` only when the sentinel reads **exactly 1** (`0x28F72 cmp 0x1,r9` / `bne 0x28F82`).
⇒ **any tick that bails zeroes `s` on the next tick that runs.** There are exactly four bail sources:
`0x28F3C`, `0x28F48`, `0x28F5A`, `0x28F62`.

### 5.2 The disengage reset at `0x2A164` does **NOT** touch `s`

**EVIDENCE.**

```
2A164  mov 0x0,r24 ; mov 0x0,r29 ; mov 0x0,r27 ; mov 0x0,r22
2A16C  mov 0x7fffffff,r16
2A172  mov 0x0,r12
2A174  … 2A17C st.h r12,-0x6b2e[gp] ; 2A188 st.h r29,-0x6b32[gp]
2A18C  st.w r16,-0x6cf8[gp]        <-- E_prev := 0x7FFFFFFF, the sentinel
2A190  st.w r24,-0x6dd0[gp]
2A19C  st.h r27,-0x6b36[gp] ; 2A1A2 st.h r22,-0x6b34[gp]
```

It zeroes **registers** and the **published** cells, and poisons `E_prev`. It never writes `gp-0x3d30`
or `gp-0x3d2c` — consistent with §3.1, where those cells have only two accesses each, both in the
filter. The same is true of the `0x2A0C6` route (`0x2A0E4`/`0x2A0E6`/`0x2A0EA`/`0x2A0F0`).

🛑 **Correction to the prior record.** "The three hook-skipping routes reset **every** PID cell" is too
strong. They reset the PID registers, the four published `gp-0x6b2e/32/34/36` cells and `E_prev`. They
do **not** reset the feedback state `gp-0x3d30` or the output-lag state `gp-0x3d3c`.

### 5.3 Does the filter run when disengaged? **Yes — every tick.**

**EVIDENCE.** The filter is at `0x28F4C–0x28FBE`; the engagement guard is at `0x29A48–0x29A70`, i.e.
**2,812 bytes later in the same straight-line flow**. The four pre-filter bails test only:

* `gp-0x4f60` sensor plausibility (`0x28F38`),
* the arm flag `gp-0x6752` (`0x28F44`, `0x28F5E`),
* `|x| ≤ 12000` (`0x28F58`),

**none of which is an engagement condition.** `gp-0x6752` is a **±1 flag**: its three writers are
`0x490C0` (writes `+1`), `0x49838` (writes `+1`) and `0x49844` (writes `−1`), selected by a record byte
compared against `0x2C`; each is mirrored into `gp-0x4c2d`. **It is never written 0.** So after
initialisation the filter runs unconditionally.

⇒ **`s` tracks the wheel continuously while disengaged.** On re-engage `s` is **current, not stale** —
which is the answer that makes a 54 ms pole safe where it would otherwise be the main hazard.

### 5.4 Cold-boot value

**BELIEF, with the honest caveat.** `gp-0x3d30` and `gp-0x3d2c` have **no writer anywhere in the image
other than the filter itself** (§3.1) — so the *only* possible initialiser is a generic BSS/RAM clear,
which by construction leaves no gp-relative reference. I did **not** locate that clear loop; a scan for
LE32 section bounds in the `0xFEDFxxxx` window found 242 distinct constants but none bracketing
`0xFEDF42CC–0xFEDF42D4` (nearest below `0xFEDF41AC`, nearest above `0xFEDF4640`).

Two branches, both bounded:

1. **BSS is cleared** (the standard case) → sentinel = 0 ≠ 1 → `s := 0` on the first tick. Safe.
2. **BSS is not cleared** → there is a 1-in-256 chance the sentinel powers up as exactly 1 and `s` loads
   RAM garbage. The output is **clamped to ±[0xC62E6]** throughout, and the state decays at `a/1024`
   per tick: from `2^31` to below 1 count takes **207 ticks (0.21 s) at `a = 923`** but
   **1,682 ticks (1.68 s) at `a = 1011`**. This happens at boot, before engagement, where the PID is
   skipped and `E_prev` is re-poisoned every tick — so it is bounded, but it is **8× longer** with the
   lowered pole.

**Exact next step to convert this to EVIDENCE:** find the startup RAM-clear loop (a `st.w r0, 0[rX]`
loop with a base built by `movhi`/`movea` or `mov imm32` into the `0xFEDFxxxx` range) and confirm its
extent covers `0xFEDF42CC–0xFEDF42D4`. `search_instructions(mnemonic="st.w", operand_pattern="r0")`
near the reset vector, or `get_entry_points` then decompile the startup function.

---

## 6. The engagement guard and the three skip jumps — CONFIRMED

```
29A48  cmp    r0,r14 ; setfne r20        r20 = (r14 != 0)
29A4E  cmp    0x1,r8 ; setfe  r8         r8  = (r8 == 1)
29A54  cmp    r0,r20 ; bne 29A60
29A58  cmp    r0,r8  ; bne 29A60
29A5C  jr     0x2A164                    SKIP 1
29A60  cmp    r0,r25 ; bne 29A68
29A64  jr     0x2A164                    SKIP 2
29A68  ld.bu  -0x680a,gp,r13
29A6C  cmp    0x1,r13 ; bne 29A74
29A70  jr     0x2A0C6                    SKIP 3
```

**EVIDENCE.** An exhaustive branch sweep of `FUN_00028ea6` finds **exactly** these three jumps to
`0x2A164`/`0x2A0C6` and **exactly four** to `0x290B0`. There is no fourth skip route.

All three skips originate at `0x29A5C+`, which is **after** `0x28F4C` and **before** `0x29D72`. ⇒ the
V290 trace's claim is **confirmed**: the skips bypass `0x29D72` (and therefore the `0x29D78` error
formation and everything downstream) but **cannot** bypass `0x28F4C`.

🛑 **One coupling the V290 trace did not state.** `r25` — tested at `0x29A60` — is set by the *filter
block itself*: `0x290AC mov 0x1,r25` on the normal path, `0x290C0 mov 0x0,r25` on the bail path. So a
filter bail **forces** skip 2. The filter running and the PID running are not independent: **the PID
cannot run on a tick where the filter bailed.** A cave at `0x28F4C` must not disturb `r25`.

---

## 7. Integer mirror (exact, for the golden model)

```python
# LKAS feedback lag filter, FUN_00028ea6 @ 0x28F4C..0x28FBE.  Ts = 1 ms.
# a = [0xC63E8]  ld.h   SIGNED   (cap 32767)
# b = [0xC63EA]  ld.hu  UNSIGNED (cap 65535)
# C = [0xC62E6]  ld.hu  UNSIGNED (V282: 46080; stock: 7680)
def lkas_fb_lag(x, s, sentinel_ok, a=923, b=1560, C=46080):
    if not (-12000 <= x <= 12000):        # 0x28F50..0x28F58  -> BAIL (r25=0, r26=0, sentinel:=2)
        return 0, s, False
    if not sentinel_ok:                   # 0x28F72 cmp 0x1 / bne 0x28F82
        s = 0
    s_new = (a * s) >> 10                 # 0x28F92 mul + 0x28FA0 sar 0xa   (floor toward -inf)
    s_new += (b * x) >> 10                # 0x28F8E mul + 0x28F9A sar 0xa   (SEPARATE floor)
    out = s + s_new                       # 0x28FA4  two-sample sum
    s = s_new                             # 0x28FA8  st.w  (32-bit state)
    out = C if out > C else (-C if out < -C else out)   # 0x28FA6..0x28FBC
    return out, s, True                   # out -> r26;  sentinel := 1
```

`DC = 2b / (1024 − a)`; `f_c = −ln(a/1024) / (2π · 0.001)` Hz.

---

## 8. What a build script must assert

1. **Edit exactly 4 bytes.** `0xC63E8` (LE u16 `a`) and `0xC63EA` (LE u16 `b`). Read back and assert.
2. **`a ≤ 32767`** — it is loaded with **`ld.h` (signed)** at `0x28F8A`. Above that it reads negative
   and the filter becomes an unstable alternating recurrence. **`b ≤ 65535`** (`ld.hu`, `0x28F86`).
3. **`a ≤ 1023`.** At `a = 1024` the pole is exactly 1 (pure integrator); above it the filter diverges
   until the `±[0xC62E6]` clamp catches it. Assert strictly.
4. **Assert the DC gain** `2b/(1024−a)` against `3120/101 = 30.8911` to within a stated tolerance —
   and use the *corrected* pairs in §4.1, not (1013,167) or (1020,60), which are off by 1.7 % and 2.9 %.
5. **Assert the overflow margin** `a · b · 12000 / (1024 − a) < 2^31`, i.e. `a · s_max < 2^31`. At
   `(1011, 201)` the margin is 11.4×.
6. **Assert the dead zone** `1024/b` in raw counts and record it in the docstring (§4.2). At
   `b = 201` it is 5.09 counts = 0.64 deg/s, 7.7× the stock 0.66.
7. **Recompute the page CRC at `0xC6FFC`.** `0xC63E8` is inside the `0xC6000` 4 KiB page; every image in
   `accord-firmwares` that touches a `0xC6xxx` cal also carries a changed `0xC6FFC`
   (V282 `75eadf72`, V283 `40c4d60c`, V287r2 `dc56db20`, V289 `fe780477`, stock `ef3c9e0c`).
8. **Assert the CODE is untouched.** `stock[0x28F00:0x2A260] == built[0x28F00:0x2A260]` **except**
   `0x2A1F0–0x2A1F1`, which must equal `d0 7c` on any V282-based build.
9. **Assert the privacy census still holds on the BUILT image** — re-run the two-encoding scan for
   `tp+0x73E8` and `tp+0x73EA` and assert exactly one reader each, at `0x28F8A` and `0x28F86`.
   *A null from the stock image is not a null for a modded one.*
10. **Reset behaviour to document, not to assert:** `s` lives in `gp-0x3d30` (32-bit, private, 2
    accesses image-wide); it is zeroed **only** by the `gp-0x3d2c` sentinel after a bail; the
    `0x2A164` / `0x2A0C6` disengage routes do **not** clear it; the filter runs every tick including
    while disengaged, so `s` is never stale on re-engage.
11. **Do not raise `0xC61BE` above 32767** (the `ld.hu`/`ld.h` mismatch at `0x2A142`/`0x2A146`).
12. **Anything writing `gp-0x6a56` must also write the lockstep mirror `gp-0x4ca6`** (§1.3).

---

## 9. Corrections to the prior record

| claim | status | evidence |
|---|---|---|
| "`0x28F00–0x2A260` identical in code.bin and V282" (this brief) | **WRONG by 2 bytes** — `0x2A1F0–0x2A1F1` is the V57/V81 gain repoint | Python byte diff |
| "`r26` dormant `0x28FBE→0x29D78` with zero intervening **accesses**" | **imprecise** — one WRITE at `0x290B6` on the bail path; zero intervening *readers* is correct | full 1,874-instruction `r26` sweep |
| "the three hook-skipping routes reset **every** PID cell" | **too strong** — they do not reset `gp-0x3d30` (fb state) or `gp-0x3d3c` (lag state) | `0x2A164–0x2A1A2` dump; §3.1 census |
| "(1013, 167) and (1020, 60) are DC-held pairs" (this brief) | **WRONG** — −1.71 % and −2.88 %; correct values 170 and 62 | arithmetic on `2b/(1024−a)` |
| "`x` is clamped ±12000 before `0x28F4C`" | **true, but at the producer** — `0x28F50` is a *bail*, the saturation is at `0x3F7B8/D0/E0` | `disassemble_bytes(0x3F7A0)` |
| "`a` and `b` poles are private" (V289's premise) | **CONFIRMED, both methods, empty set-difference** | §2.2 |

---

## 10. Open questions / verification still needed

1. **The cold-boot RAM clear (§5.4).** BELIEF only. Next step: `get_entry_points`, then decompile the
   startup function and confirm a clear loop covering `0xFEDF42CC–0xFEDF42D4`.
2. **The dead-zone impact (§4.2).** The widened quantiser dead zone is arithmetically certain; whether
   it matters depends on the measured distribution of `x` during a grinding episode, which is an
   rlog question, not a firmware one. **This should be checked before choosing `b`.** It is the one
   thing in this trace that could turn a 2 Hz pole into a new nonlinearity at small amplitude.
3. **`0x6B9FA`** — the fault handler called when the `gp-0x6a56` / `gp-0x4ca6` lockstep pair disagrees.
   Not decompiled. Only relevant if a future cave writes `gp-0x6a56`.
4. **`Ts = 1 ms`** is EVIDENCE-by-consistency (two label↔byte agreements), not a scheduler read. If it
   matters to a decision, confirm from the timer ISR period.
