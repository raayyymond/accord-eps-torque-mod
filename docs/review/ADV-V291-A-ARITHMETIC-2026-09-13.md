# ADVERSARIAL PASS — V291 (C10), SURFACE A: ARITHMETIC

**Agent `advA`, subagent of `main`, 2026-09-13. Adversarial: the job was to make the build FAIL.**
**TOP-LINE VERDICT: PASS.** No arithmetic defect found that would justify withholding the flash.
Five findings are recorded below that the pre-registration did not anticipate; one of them
(**E1**) is a consumer-census item that belongs to surface D and is *not* closed here.

**Image under attack:** `_v291c10_…_plain_image.bin`
sha256 `a66f9c54b21031d3948cf1f60fbcadc6ac44d422c01d5a357b19aa0d23144657` (re-hashed from disk).
**Base:** `_v282_…_plain_image.bin` sha256 `0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe`.
**Stock:** `stock_fw_dump/code.bin` sha256 `3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822`.

**Method.** Every number below is re-derived from the image bytes or from GhidraMCP disassembly.
`build_v291_tva.py` was never read. Tooling: GhidraMCP `disassemble_bytes dry_run:true` on `code.bin`
(no mutating call, nothing saved), plus an **independently written V850E2 decoder** run directly on the
V291 image, plus integer mirrors in Python. Scratch:
`…/scratchpad/{v850dec,advA_arith,advA_part2,advA_part3,advA_part4,advA_part5,advA_census}.py`.

---

## 0. Premise check — the diff, and the right to use `code.bin` for the code

**EVIDENCE.** Full-byte diff V291 vs V282 over the whole 1 MiB: **15 bytes in 5 clusters, none below
`0x13000`.**

| offset | V282 | V291 | what |
|---|---|---|---|
| `0xC4BAA–AB` | `81 c9` | `d1 c2` | b3 rung displacement (hw2 only) |
| `0xC4FFC–FF` | `446bb04e` | `26c4ce34` | 0xC4000 page CRC trailer |
| `0xC63E8–EB` | `9b03 1806` | `c203 be03` | `a` 923→**962**, `b` 1560→**958** |
| `0xC6446–47` | `7c 14` | `75 12` | r24 engaged arm 5244→**4725** |
| `0xC6FFC–FF` | `72dfea75` | `bb129bed` | 0xC6000 page CRC trailer |

**EVIDENCE.** `0x28F30–0x28FC0` (the filter), `0x290B0–0x290E0` (the bail) and `0x3AA9C–0x3AC60` (the
r24 lane) are **byte-identical across V291, V282 and stock**. `FUN_00028ea6` as a whole differs from
stock only at `0x2A1F0–F1` (the documented V282 forward-gain re-point). ⇒ Ghidra's analysis of
`code.bin` is valid for every code claim below; the cave at `0xC4B34+` is fresh code in a stock-`0xFF`
region and was decoded from the V291 image only.

**Decoder positive control.** My decoder reproduces Ghidra's listing of `0x28F4C–0x28FC4`
**42 instructions out of 42, exact, with zero unknowns**, read from the V291 image.

---

## 1. The filter, re-derived from the image

```
28F4C  ld.h  -0x6a56[gp],r7      x  = steering rate, SIGNED 16-bit (producer already saturates +-12000)
28F50  addi  0x2ee0,r7,r11
28F54  addi  -0x5dc1,r11,r0
28F58  bnc   28F5E ; 28F5A jr 290B0     BAIL if |x| > 12000  (a BAIL, not a clamp)
28F66  ld.bu -0x3d2c[gp],r9      sentinel; != 1 -> cold start, s := 0
28F7C  ld.w  -0x3d30[gp],r26     s   <- 32-BIT load
28F86  ld.hu 0x73ea[tp],r16      b = [0xC63EA] = 958     UNSIGNED
28F8A  ld.h  0x73e8[tp],r9       a = [0xC63E8] = 962     ** SIGNED **
28F8E  mul   r16,r7,r0           r7 = low32(x*b)   high word discarded (reg3 = r0)
28F92  mul   r26,r9,r0           r9 = low32(s*a)   high word discarded
28F9A  sar   0xa,r7              floor(x*b/1024)   <- SEPARATE floor
28FA0  sar   0xa,r9              floor(s*a/1024)   <- SEPARATE floor
28FA2  add   r7,r9               s_new
28FA4  add   r9,r26              out = s_old + s_new
28FA8  st.w  r9,-0x3d30[gp]      s := s_new        <- 32-BIT store
28FA6/AC/AE/B2/B4/B6/B8/BC       clamp out to +-[0xC62E6] = 46080, all three loads ld.hu
```

```python
# byte-exact mirror
def tick(s, x, a=962, b=958, C=46080):        # a ld.h SIGNED, b ld.hu, C ld.hu
    assert -12000 <= x <= 12000               # 0x28F50/54/58  BAIL
    t1 = int32(x * b) >> 10                   # 0x28F8E, 0x28F9A
    t2 = int32(s * a) >> 10                   # 0x28F92, 0x28FA0
    snew = t2 + t1                            # 0x28FA2
    out  = s + snew                           # 0x28FA4   two-sample sum
    s    = snew                               # 0x28FA8
    return max(-C, min(C, out)), s
```

**On the bail path `r26 = 0`** (`0x290B6 mov 0x0,r26`) and the sentinel is written `2`
(`0x290B0 mov 0x2,r1` → `0x290D4 st.b`), so the next surviving tick restarts from `s = 0`. **EVIDENCE.**

---

## 2. SCORECARD against the pre-registration, surface A

### A1 — DC and corner ✅ **PASS**

| quantity | from the V291 bytes | FAIL threshold | margin |
|---|---|---|---|
| DC = 2b/(1024−a) = 2·958/62 | **30.903226** | ±0.5 % of 30.891 | **+0.0396 %** |
| corner = −ln(a/1024)/2πTs | **9.9404 Hz** | 9.94 ± 0.4 | **+0.0004 Hz** |

V282 for contrast: DC 30.891089, corner 16.5271 Hz. `Ts = 1 ms` is EVIDENCE-by-consistency
(the record's 16.53 Hz label ↔ `a = 923`), not a scheduler measurement. **PASS.**

**Simulated integer DC** (constant `x`, 20 000 ticks) reproduces the analytic value above ~5 deg/s and
falls away below it — see **E4**. That is the floor, not a defect in the cells.

### A2 — int32 overflow and width ✅ **PASS**

Swept `x` over `[−12000, +12000]`, state driven to steady state and then released from the opposite
rail, both builds, every tick audited:

| | V282 | V291 | int32 headroom (V291) |
|---|---|---|---|
| max \|s\| | 185,355 | **185,427** | ×11,581 |
| max \|x·b\| | 18,720,000 | **11,496,000** | **×186.8** |
| max \|s·a\| | 171,082,665 | **178,380,774** | **×12.04** |
| max \|pre-clamp out\| | 370,710 | **370,854** | ×5,790 |
| int32 overflows | 0 | **0** | — |

The state cell is 32-bit: `ld.w` at `0x28F7C` / `st.w` at `0x28FA8` (opcode field `0x39`/`0x3B` with
`hw2` bit 0 set — `d1 c2` = disp `0xC2D0` = −0x3D30, `.w` form). The recursion is monotone in `s`
(a first-order lag with `0 < a/1024 < 1`), so the swept steady states bound every transient.
**No narrowing anywhere on the error path.** The only narrowing found on *any* path is
`st.h r9,-0x6a34[gp]` at `0x290CA` (see **E1**), max value 1440, safe. **PASS.**

### A3 — dead zone and stick zone ✅ **PASS** (one clause with modest margin)

| | V282 | V291 | FAIL threshold |
|---|---|---|---|
| input dead zone 1024/b | 0.6564 cts = **0.0821 deg/s** | 1.0689 cts = **0.1336 deg/s** | > 0.15 deg/s |
| smallest \|x\| with `(b·x)>>10 ≠ 0` | 1 count | **2 counts** | — |
| widest negative absorbing \|s\| (x = 0) | 10 | **16** | ratio > 2.0 |
| stick-zone ratio | — | **1.600** | > 2.0 |
| resting `r26` after a negative release | −20 | **−32** | — |

Positive states have **no** absorbing point at either `a` — they all decay to 0; only the negative side
sticks, because `sar` floors toward −∞. The absorbing set is exactly `|s| < 1024/(1024−a)`:
1024/101 = 10.14 → 10 on V282, 1024/62 = 16.52 → 16 on V291. Verified by direct integer release from
`s = ±200,000` with `x ≡ 0`. The resting feedback offset is therefore −32 E-counts = **1.0 setpoint
count** of phantom demand at rest (V282: 0.625). **PASS on both clauses**, dead zone with 11 % margin.

### A4 — the r24 arm ✅ **PASS**, with one qualification that is *in the safe direction*

```
3AA9C  ld.h  -0x4f62[gp],r14              lane input
3AAAC..3AAC0                              r1 = clamp(r14, +-5120)
3AB98  ld.bu -0x671d[gp],r6  -> setfne    the LATCH arm
3ABFA  cmp r0,r6 ; be 3AC04
3ABFE  ld.hu 0x7442[tp],r10   [0xC6442] = 1024   <- OUTRANKS everything
3AC04  cmp r0,lp ; be 3AC0E
3AC08  ld.hu 0x7446[tp],r10   [0xC6446] = 4725   <- THE ENGAGED ARM  (ld.hu, unsigned)
3AC0E  cmp r0,r2 ; be 3AC16
3AC12  ld.hu 0x7440[tp],r10   [0xC6440] = 2048
       (else r10 keeps the LERP result from the 0x3AB9C..0x3ABF8 walk)
3AC16  mov r1,r8 ; 3AC18 mul r10,r8,r0 ; 3AC20 sar 0xa,r8     <- Q10
3AC1C..3AC3C                              deadband +-[0xC61F6] = 3, SUBTRACTIVE
3AC3E  mul r14,r6,r0                      x arm flag (ld.b gp-0x6752, in {-1,0,+1})
3AC42..3AC54                              clamp +-8192
```

- **Q10 and `ld.hu` — confirmed.** `ld.hu 0x7446[tp]` at `0x3AC08`, `sar 0xa` at `0x3AC20`.
  Raw halfword `0x1275` = 4725, far below 32768, so the unsigned read is unambiguous. ✅
- **No overflow.** max `|r1·gain|` = 5120 × 4725 = **24,192,000**, int32 headroom **×88.8**
  (V282: 26,849,280, ×80.0). ✅
- **Gain-select priority byte-identical.** `0x3AA9C–0x3AC60` is identical across V291, V282 and stock,
  so the priority chain above is unchanged by construction. ✅
- **Proportionality below the clamps.** Median realised ratio `out_V291/out_V282` = **0.9010**, exactly
  the cal ratio 4725/5244 = 0.901030. It departs by more than 1 % at only **8 of 1600** input values,
  all `|u| ≤ 13`, where the absolute error is ≤ 1 count — the subtractive ±3 deadband's granularity. ✅

🟡 **QUALIFICATION (finding E3).** The ±8192 output clamp is **not** proportional. Saturation is first
reached at `|u| = 1601` on V282 and `|u| = 1777` on V291 (**+11.0 %**), and **above that both builds
deliver an identical ±8192** — the −9.90 % cut is fully masked wherever the lane rails. This is the
ordinary consequence of a saturating lane, and it is strictly conservative: over `|u| ≤ 6000` there is
**no input at which V291's magnitude exceeds V282's and none at which the sign differs**; the largest
reduction is 811 counts at `|u| = 1600`. Scored **PASS**, but the effectiveness caveat is real — how
much of engaged time sits above `|u| = 1601` is a wire question for surfaces B/D.

### A5 — the sign and width of `a` ✅ **PASS**

`0xC63E8` raw halfword `0x03C2` = 962. `0x28F8A` is `ld.h` (opcode field `0x39`, `hw2 = 0x73E8`, bit 0
clear ⇒ `.h` form, **signed**). 962 ≤ 1023 ✅ and 962 ≪ 32768, so no sign-extension inversion.
`a/1024 = 0.939453 < 1` ⇒ pole strictly inside the unit circle. `b` raw `0x03BE` = 958 read `ld.hu`;
`b · 12000 = 11,496,000` fits int32. **PASS.**

---

## 3. The 0x14A cave b3 rung at `0xC4BA8` (brief item 3) ✅ **PASS on every claim**

Decoded from the V291 image by my own positive-controlled decoder:

```
0C4B90  003a       mov 0x0,r7
0C4B92  2437b494   ld.h  -0x6b4c[gp],r6   ; cmp 0,r6 ; bge +4 ; add 0x8,r7   -> becomes bit 7
0C4B9C  24372695   ld.h  -0x6ada[gp],r6   ; cmp 0,r6 ; bge +4 ; add 0x1,r7   -> becomes bit 4
0C4BA6  c43a       shl 0x4,r7
0C4BA8  2437d1c2   ld.w  -0x3d30[gp],r6   ** V291 EDIT (V282: 243781c9 = ld.w -0x3680[gp],r6) **
0C4BAC  6032       cmp 0x0,r6
0C4BAE  ae05       bge 0xC4BB2
0C4BB0  483a       add 0x8,r7             -> bit 3
0C4BB2  8437edea   ld.bu -0x1514[gp],r6
0C4BB6  c6366700   andi 0x67,r6,r6        ; 0x67 = 0110 0111
0C4BBA  0731       or  r7,r6
0C4BBC  4437ecea   st.b r6,-0x1514[gp]
```

1. **`24 37 d1 c2` is `ld.w -0x3d30[gp], r6` — proven by two independent methods.**
   (a) My decoder, controlled 42/42 against Ghidra on the filter range, read from the V291 image.
   (b) **Composition from two stock instances**: `hw1 = 0x3724` appears verbatim at `0x28F78`
   (`ld.w -0x3d34[gp], r6` — same reg2 = r6, reg1 = gp, opcode `0x39`), and `hw2 = 0xC2D1` appears
   verbatim at `0x28F7C` (`ld.w -0x3d30[gp], r26` — same odd `hw2`, therefore `.w`, disp `0xC2D0`
   sign-extended = −0x3D30). **EVIDENCE.**
2. **Displacement-only.** The byte diff shows exactly two changed bytes, `0xC4BAA–AB` (the `hw2`
   halfword). `hw1` is untouched, so width, base register and destination register are unchanged.
3. **The sign test is `s < 0` with zero reading CLEAR.** `cmp 0x0, r6` sets flags from `r6 − 0` (no
   overflow possible), `bge` branches when GE, i.e. when `s ≥ 0`, skipping the `add`. `s = 0` ⇒ branch
   taken ⇒ bit 3 stays clear. **EVIDENCE.**
4. **The rung shares nothing else.** `r6` is loaded fresh immediately before. `r7` is an accumulator
   initialised to 0 at `0xC4B90`; its maximum reachable value is `0x80 | 0x10 | 0x08 = 0x98`, so the
   three `add`s cannot carry into one another or out of the byte.
5. **Honda's bits 0–2 are preserved.** `andi 0x67` = `0110 0111` keeps bits 0, 1, 2 (stock Honda) and
   bits 5, 6 (this cave's own comparator rungs, written earlier at `0xC4B5E` and `0xC4B8C`), clearing
   only 3, 4, 7. **EVIDENCE.**
6. **`gp-0x3d30` is 4-byte aligned.** `0xFEDF8000 − 0x3D30 = 0xFEDF42D0`; `0x2D0 & 3 = 0`. An aligned
   32-bit read cannot tear against the filter's aligned 32-bit `st.w`. **EVIDENCE.**

⭐ **The pre-registration's own D4 premise is wrong, in the build's favour.** D4 says the rung reads
"gp-0x3d30 **low halfword**". It does not — it is a **32-bit `ld.w`**. That matters: `|s|` reaches
**185,427**, so a halfword read would have delivered an **inverted** sign bit whenever `|s| > 32767`,
i.e. whenever `|x| > 2120` counts (265 deg/s), which is inside the ±12000 range the producer allows.
**The build does the right thing; the brief describes a defect the build does not have.**

**Census on the built images (my two-encoding scanner, positive-controlled).**

| cell | V282 | V291 |
|---|---|---|
| `gp-0x3d30` (state `s`) | `ld.w 0x28F7C`, `st.w 0x28FA8` | same **+ `ld.w 0xC4BA8`** (the new rung) |
| `gp-0x3680` (V282's b3 source) | `ld.w 0x3A85C`, `st.w 0x3A87A`, **`ld.w 0xC4BA8`** | `ld.w 0x3A85C`, `st.w 0x3A87A` — **the cave read is gone** |

⇒ the re-point is exactly one read moved, nothing else. Note for the record: **V291 retires whatever
instrument bit 3 carried on V282** (`gp-0x3680`, written at `0x3A87A`). That is a telemetry-continuity
item, not an arithmetic one.

**Reader census of the three edited cells, on the BUILT V291 image**, four-byte + six-byte extended +
absolute-pointer forms, with positive controls (`gp-0x6a56` → 30 hits matching the record's
25 `ld.h` + 4 `st.h` + 1 `ld.bu`; `tp+0x72E6` → 3 `ld.hu`; `gp-0x6752` → 4 six-byte hits found):

| cell | readers | writers |
|---|---|---|
| `tp+0x73E8` (`a`) | **1** — `ld.h` `0x28F8A` | 0 |
| `tp+0x73EA` (`b`) | **1** — `ld.hu` `0x28F86` | 0 |
| `tp+0x7446` (r24 arm) | **1** — `ld.hu` `0x3AC08` | 0 |

---

## 4. Findings the pre-registration did not anticipate

### E1 🟡 A SECOND CONSUMER of the filter output, missed by the trace's census — **hand to surface D**

The trace censused the **state** `gp-0x3d30` and found it private. The **output** is not. **EVIDENCE:**

```
28FBE  mov  r26,r16        ; 28FC0 sar 0x5,r16 ; 28FC2 shl 0x5,r16   quantise to 32
28FC4  bp   28FC8          ; 28FC6 subr r0,r16                        ABS
28FDE  mov  r16,r9         r9 = |quantise(fb,32)|   (r9 is not written again on the normal path)
290AE  br   290C2          the normal path joins the shared epilogue
290C6  shr  0x5,r9         LOGICAL
290CA  st.h r9,-0x6a34,gp  gp-0x6a34 := |clamped filter output| >> 5      (16-bit store, max 1440)
```

Census of `gp-0x6a34`: one writer `0x290CA`, and **two readers — `0x2A0CA` (live, same function) and
`0x2AFAE` (inside `FUN_0002a93a`, the known caller-less dead twin).** The live reader is the index of a
LERP over `tp+0x7710`:

```
29A68  ld.bu -0x680a[gp],r13 ; cmp 0x1,r13 ; 29A70 jr 0x2A0C6      <- the guard
2A0C8  cmp   r0,r26                      r26 here is STILL the filter output (no write since 0x290B6)
2A0CA  ld.hu -0x6a34[gp],r8              index = |fb|>>5
2A0D4  cmovlt -0x1,r12,r12               r12 = sign(fb) in {+1,-1}
2A0D8..2A138                             LERP: X = {64,65,67,73,80,88,96,104} at 0xC6712..0xC6720
                                               Y = {608,704,704,832,832,832,832,832} at 0xC6722..0xC6730
2A13A  mulh r10,r12 ; 2A13C subr r0,r12  r12 = -sign(fb) * LERP(|fb|>>5)
2A13E                                    ... straight into the +-[0xC61BE] sum clamp
```

**On that path the PID output is replaced wholesale by a function of the edited filter's output.**
The table itself is byte-identical V282/V291. The edit is DC-neutral there (DC is held, so the index is
identical at every steady `x` — verified: index 37/37 at x = 40, 95/95 at 100, 192/192 at 200), and at
20 Hz it **reduces** the index swing ×0.699 (17.32 → 12.11 index counts at ring A = 28.2). During
hands-off creep the index sits at 0–7, far below the first knot at 64, so the table is pinned at 608 and
the signal is carried entirely by `sign(fb)` — whose 20 Hz phase the edit shifts by **−13.1°**.

**Bound on the exposure.** The guard `gp-0x680a == 1` has **two readers (`0x29A68` live, `0x2A96A` dead
twin) and NO writer visible** to a 4-byte, 6-byte or absolute-pointer scan. **BELIEF, not EVIDENCE:**
operand-text scanning cannot see register-indirect stores (CLAUDE.md), so I cannot assert the cell is
never set. If it is never set, this whole path is dead and the filter output reaches only the error at
`0x29D78`. **Surface D must close this**; I am not closing it. It is not a FAIL on surface A because
the DC behaviour is unchanged and the dynamic effect is a reduction.

### E2 🟡 The b3 rung is BLIND above a mean wheel rate the edit makes *lower*

`b3 = sign(s)` carries phase only while the ring's contribution to `s` exceeds the mean rate's DC
contribution, i.e. while `x_DC < |H_s(f)|·A·(1024−a)/b`:

| f | ring A | V282 pole: max mean rate | V291 pole: max mean rate | ratio |
|---|---|---|---|---|
| 7.3 Hz | 28.2 cts | 25.8 cts = 3.22 deg/s | 22.7 cts = **2.84 deg/s** | 0.881 |
| 10 Hz | 28.2 cts | 24.1 cts = 3.02 deg/s | 19.9 cts = **2.49 deg/s** | 0.824 |
| 10 Hz | 15.8 cts | 13.5 cts = 1.69 deg/s | 11.1 cts = **1.39 deg/s** | 0.824 |
| 20 Hz | 28.2 cts | 18.0 cts = 2.25 deg/s | 12.6 cts = **1.57 deg/s** | 0.699 |

Confirmed by direct integer simulation: at `x_DC = 40` counts the sign bit **never toggles** (duty
0.000) at either ring amplitude, on either build. ⇒ **On straight hands-off creep — the pre-registered
condition — the instrument works. In any sustained curve it pins to a constant and a reader must not
interpret that as "phase = 0".** The window is 12–30 % narrower than the V282 pole would have given.
**Warning, not a FAIL:** no surface-A FAIL condition covers instrument dynamic range, and the intended
condition is inside the window. Sampling is once per `0x14A` frame; I did not measure that frame rate,
so the aliasing margin is **BELIEF**.

### E3 🟡 The r24 cut is fully masked above `|u| = 1777` — see A4.

### E4 🟢 The rate-feedback resolution halves, exactly as the design predicted

Byte-exact, from a cold filter: the smallest `x` step producing a non-zero first-tick feedback move is
**1 count (0.125 deg/s) on V282 and 2 counts (0.250 deg/s) on V291**. Consequently the first-tick D
kick from one rate LSB is **zero** on V291. Integer DC at small constant rate:

| x (counts) | 1 | 2 | 4 | 8 | 20 | 40 | ≥ 80 |
|---|---|---|---|---|---|---|---|
| V282 out/x | 2.00 | 21.0 | 25.5 | 28.0 | 29.5 | 29.95 | ≥ 30.4 |
| V291 out/x | **0.00** | **1.00** | 17.0 | 25.0 | 28.1 | 29.75 | ≥ 30.2 |

This is the design's own §6.2 effect at the 9.94 Hz dose and is **already on the record** — recorded
here only because it is the sharpest byte-level consequence of the edit. Not a FAIL.

### E5 ⚪ Method note — a defect in MY OWN scanner, caught by control

My first branch decoder computed the Format-III displacement as `((r2<<4)|ddd)<<1` instead of
`((r2<<3)|ddd)<<1`. Every branch in the positive-control range had `r2 = 0`, where the two formulas
**agree**, so the control passed while the decoder was wrong for every long branch. It was caught only
because a second control against a Ghidra-confirmed long branch (`0x2A0C4 br 0x2A13E`) disagreed. Fixed
and re-controlled on 6 branches including 4 long ones. **No conclusion in this report depended on the
broken version**: the cave's branches are all `r2 = 0` (disp 4), the `jr` forms are Format V, and the
linear instruction-length walk is unaffected. Recording it because it is a textbook instance of the
skill's own rule — *a control that does not exercise the failing path is not a control.*

---

## 5. What a FAIL would have looked like, and why none was returned

Written so this pass is not theatre. I would have returned **DO-NOT-FLASH** on any of:
`b ≥ 1024·0.15·8 = 1229` (dead zone over 0.15 deg/s); `a ≥ 1024` (unstable pole) or `a ≥ 32768`
(sign inversion through the `ld.h`); any `|s·a|` or `|x·b|` reaching 2³¹; a 16-bit store on the state
or on the b3 rung's read; an `andi` mask that disturbed bits 0–2; a misaligned state cell; `4725`
read `ld.h` or at a shift other than 10; or an r24 input at which V291 delivers **more** than V282.
**Each was checked and none occurred.** The two cells whose margins are smallest are the dead zone
(0.1336 vs 0.15 deg/s, 11 % margin) and the stick-zone ratio (1.60 vs 2.0, 20 % margin).

## 6. VERDICT

| item | verdict | the number |
|---|---|---|
| A1 DC / corner | ✅ PASS | DC **30.903226** (+0.0396 %), corner **9.9404 Hz** |
| A2 overflow / width | ✅ PASS | max `\|s·a\|` **178,380,774**, headroom **×12.04**, 0 overflows |
| A3 dead zone / stick | ✅ PASS | **0.1336 deg/s** (< 0.15); stick ratio **1.600** (< 2.0) |
| A4 r24 arm | ✅ PASS | headroom **×88.8**; realised ratio **0.9010**; never larger than V282 |
| A5 `a` sign / width | ✅ PASS | `0x03C2` = 962 ≤ 1023, `ld.h`, `a/1024 = 0.939453` |
| b3 rung (brief item 3) | ✅ PASS | `ld.w`, 32-bit, aligned, `andi 0x67`, displacement-only |

**TOP-LINE: PASS.** Surface A finds no reason to withhold the flash. **E1 is open and belongs to
surface D** — the `gp-0x680a` guard's writer must be censused by a method that can see
register-indirect stores before anyone claims the filter output is consumed only by the error.
