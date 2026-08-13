# TRACE 2026-08-13 — V99 lever set, pre-positioned on all three observer arms

Agent: `tracer-arms` (subagent; orchestrator = `main`). Tooling: **GhidraMCP only** for disassembly /
decompilation, **Python** for byte-level work, every load-bearing count adjudicated by **both**.

Programs open this session: `code.bin` (stock, current, 2,086 functions) plus four `_v9x` images.
**Every Ghidra call in this trace passed `program` explicitly.** Anchors: `gp = 0xFEDF8000`,
`tp = 0xBF000` ⇒ `tp+0x73AC = 0xC63AC`, `tp+0x5000 = 0xC4000` (**not** `0xC5000`).

---

## 0. The junction, re-read from scratch — and the exact instruction sequence

`decompile_function(0x38148)` then `get_assembly_context` to pin the encoding. The brief's diagram is
confirmed, with two refinements (§3.2, §3.3).

```
0x381ee  ld.b   -0x6752[gp],r8      ; polarity, signed byte
0x381f2  ld.hu  0x7468[tp],r16      ; 0xC6468 = 2639   (shared model gain)
0x381f6  mul    r8,r14,r0           ; sum6 * polarity
0x381fa  mul    r16,r14,r0          ; * 2639
0x381fe  ld.w   -0x374c[gp],r6      ; ACTUAL accumulator (32-bit)
0x38202  ld.hu  0x73ac[tp],r13      ; 0xC63AC = A       <-- ALL OF V97 (102 -> 150)
0x38206  sar    0xa,r14             ; >> 10
0x38208  ld.h   -0x6bfa[gp],r7      ; REQUEST
0x3820c  shl    0x4,r14             ; << 4              => target
0x3820e  sub    r6,r14              ; target - accum
0x38210  mul    r13,r14,r0          ; * A
0x38214  addi   0x4e20,r7,r11       ; REQUEST + 20000
0x38218  ld.h   -0x6bfe[gp],r15     ; MODEL
0x3821c  ori    0x9c41,r0,r8        ; 40001
0x38220  sar    0xa,r14             ; >> 10
0x38222  add    r14,r6              ; accum += delta
0x38224  cmp    r8,r11
0x38226  cmovnc 0x0,r7,r9           ; r9 = gated REQUEST  (zeroing conditional move)
0x3822a  addi   0x4e20,r15,r16      ; MODEL + 20000
0x3822e  cmp    r8,r16
0x38230  st.w   r6,-0x374c[gp]      ; store new accumulator
0x38234  bnc    0x382ce             ; MODEL out of range -> gp-0x6b70 = 0x7FFF (plausibility latch)
0x38236  sar    0x4,r6              ; ACTUAL = accum >> 4      (ARITHMETIC shift)
0x38238  subr   r15,r6              ; r6 = MODEL - ACTUAL      opcode 0x0C  => coefficient -1
0x3823a  add    r9,r6               ; r6 = ... + REQUEST       opcode 0x0E  => coefficient +1
0x3823c  mov    r6,r8
0x3823e  bp     0x38242
0x38240  subr   r0,r8               ; r8 = |iVar6|
0x38242  ld.hu  0x73ae[tp],r10      ; 0xC63AE = LERP index scale
0x38246  cmp    r0,r6
0x38248  mov    0x1,r11
0x3824a  mulu   r10,r8,r0           ; |iVar6| * scale   (UNSIGNED multiply)
0x3824e  cmovlt -0x1,r11,r11        ; r11 = sign(iVar6)
0x38252  ld.hu  -0x64b8[gp],r7      ; LERP X[0]
0x38256  shr    0xa,r8              ; >> 10  (LOGICAL)
0x38258  movea  -0x64b8,gp,ep       ; LERP table is ep-based
0x3825c  zxh    r8                  ; ****** 16-BIT TRUNCATION — REAL, see 4.1 ******
0x3825e  cmp    r7,r8
```

**±1 coefficients re-verified independently of the record** (`subr` = 0x0C, `add` = 0x0E). Integer
mirror of the whole junction, constants read little-endian:

```python
sum6   = sum(((x * gate(x, hw)) * W) >> 10 for x, hw, W in six_lanes)   # 0x38206
target = ((sum6 * polarity * 2639) >> 10) * 16                          # 0x381f6 .. 0x3820c
accum += ((target - accum) * A) >> 10                                   # 0x3820e .. 0x38222, A = 0xC63AC
iVar6  = MODEL - (accum >> 4) + (REQUEST if -20000 <= REQUEST <= 20000 else 0)   # 0x38236 .. 0x3823a
idx    = ((abs(iVar6) * SCALE) >> 10) & 0xFFFF                          # 0x3824a, 0x38256, 0x3825c
out    = sign(iVar6) * LERP(idx);  out = clamp(out, -8192, +8192)       # 0xC6200
```

---

## 1. D1 — CALIBRATION CENSUS BY ARM

### On-car ledger, read from the **image**, not the build scripts [EVIDENCE]
Car = `_v98_V97BASE-CAVE.CMP.6BFE.6BFA.374C-POL.6752-ID.BYTE7.2_plain_image.bin`.

| cell | stock | on car | role | introduced |
|---|---|---|---|---|
| `0xC63AC` | 102 | **150** | ACTUAL-arm IIR pole | **V97** |
| `0xC40D2` | 102 | **204** | MODEL-arm K1 (Coulomb) | **V89** |
| `0xC63A0..AA` | 1024 | 1024 | six lane weights | — |
| `0xC63AE` | 1024 | 1024 | LERP index scale | — |
| `0xC6468` | 2639 | 2639 | shared model gain | — |
| `0xC6200` | 8192 | 8192 | `gp-0x6b70` clamp | — |
| `0xC4080` `0xC40BC` `0xC40D0` `0xC40D4` `0xC40D6` `0xC40D8` | 0/600/408/573/246/3686 | identical | `FUN_0003b8f6` | — |

**Exactly two non-stock cells on the whole structure**, on opposite arms. Confirms the framing at byte
level.

### 1.1 REQUEST arm — `gp-0x6bfa` — **ZERO calibration cells** [EVIDENCE]

Writer `FUN_00026c80` @ `0x27396–0x273e6`, walked instruction by instruction:

```
0x27396  ld.w   -0x3d90[gp],r15   ; LKAS demand (32-bit), 1W @0x27336 / 1R @0x27396
0x2739e  addi   -0x4e20,r15,r0    ; flags vs +20000      0x4e20 = 20000
0x273a2  ld.h   -0x6bfa[gp],r14
0x273a6  ble    0x273ba
0x273a8  cmp    r6,r14 / bne 0x273e2      <-- shadow check, see 5.1
0x273ac  movea  0x4e20,r0,r14     ; HARDCODED IMMEDIATE — not a cal load
0x273b0  st.h   r14,-0x6bfa[gp]   ; clamp HIGH = +20000
0x273b4  st.h   r14,-0x4cfa[gp]   ; shadow
0x273c4  movea -0x4e20,r0,r14
0x273c8  st.h   r14,-0x6bfa[gp]   ; clamp LOW = -20000
0x273d6  st.h   r15,-0x6bfa[gp]   ; in-range pass-through
0x273e2  movea -0x4cfa,gp,r6 ; jarl 0x0006b9fa,lp   <-- MISMATCH handler
```

- **The ±20000 bound is a `movea` immediate, not a calibration cell.** There is no tunable cell
  anywhere between `gp-0x3d90` and `iVar6`, and REQUEST enters the sum with coefficient exactly **+1**
  and **no cal multiply**.
- ⇒ **If the comparator names REQUEST as the dominant arm, there is no cal-only lever on it.** Options
  are upstream of `gp-0x3d90` (the 11-slot aggregator) or a code edit — and a code edit here sits
  directly beside the lockstep monitor of §5.1.
- ⊕ **Proves "the ±20000 gate is DEAD" at instruction level**: the writer stores only values in
  `[-20000, +20000]`; the gate at `0x38224` admits exactly that closed interval. `cmovnc` can never fire.

### 1.2 MODEL arm — `gp-0x6bfe` — 10 cal cells, all in `FUN_0003b8f6` [EVIDENCE]

Sole writer `FUN_0003bc20` is twelve lines and contains **no calibration at all**:

```c
s = gp-0x6bfc;
if (s + 20000U < 0x9c41) { health = 0x400;  }                 // in range
else                     { health = 0xffff; s = 0x7fff; }     // FAULT sentinel
gp-0x6bfe = s;  gp-0x695c = health;
```

The tunable cells are one level up, in `FUN_0003b8f6` (the 1 kHz plant model). Types read from the
**opcode**, never the value (`ld.w` + `mulf.s` = float; `ld.hu` + `cvtf.uws` = u16):

| cell | tp+ | load @ | type | stock | car | role |
|---|---|---|---|---|---|---|
| `0xC4048` | 0x5048 | `0x3b9d2` | float | 1.0 | 1.0 | FIR tap b0 |
| `0xC404C` | 0x504C | `0x3b9de` | float | 0.0 | 0.0 | FIR tap b1 |
| `0xC4050` | 0x5050 | `0x3b9ee` | float | 0.0 | 0.0 | FIR tap b2 |
| `0xC4080` | 0x5080 | `0x3baf6` | u16 | 0 | 0 | K0 — **NEVER RAISE**, and dead at 0 |
| `0xC40BC` | 0x50BC | `0x3bab4` | u16 | 600 | 600 | Coulomb relay divisor |
| `0xC40D0` | 0x50D0 | `0x3bb22` | u16 | 408 | 408 | IIR α, friction, fc 16.7 Hz |
| `0xC40D2` | 0x50D2 | `0x3bafe` | u16 | 102 | **204** | K1, Q10 — **V89, on the car** |
| `0xC40D4` | 0x50D4 | `0x3b94e`,`0x3b96a` | u16 | 573 | 573 | IIR α ×2 cascade, fc 24.0 Hz |
| `0xC40D6` | 0x50D6 | `0x3bb60`,`0x3bb8a` | u16 | 246 | 246 | IIR α ×2, fc **9.86 Hz** — dominant phase |
| `0xC40D8` | 0x50D8 | `0x3b98e`,`0x3b9a2` | u16 | 3686 | 3686 | IIR α, fc 366 Hz — **NO-OP, −0.6°** |

**The float block is an IDENTITY** — `y[n] = 1.0·x[n] + 0.0·x[n−1] + 0.0·x[n−2]` ⇒ |H| = 1.000,
phase 0.000° at every frequency. The "3-tap FIR" is not a filter.

### 1.3 ACTUAL arm — `gp-0x374c` — 8 cal cells [EVIDENCE]

Six lane weights + the pole + the shared gain. Lane↔weight map and zero-reject windows re-read fresh
from the `0x38148` decompile (the gate is a **zero-reject window**, not a clamp — outside it the lane
*vanishes*; it tests the RAW pre-weight value, so raising a weight cannot trip its own gate):

| cell | weights lane | window | lane identity | on car |
|---|---|---|---|---|
| `0xC63A0` | `gp-0x6bd0` | ±2048 | seed / damper-presence — **measured ~0 on 87,940 frames** | 1024 |
| `0xC63A2` | `gp-0x6bbe` | ±2048 | **VISCOUS** + DC pedestal | 1024 |
| `0xC63A4` | `gp-0x6b46` | ±1024 | backlash-gated residual servo, own <1 Hz EMA | 1024 |
| `0xC63A6` | `gp-0x6b26` | ±1024 | **INERTIA** (`−K·α`) | 1024 |
| `0xC63A8` | `gp-0x6b4e` | ±10240 | **PROVABLY ≡ 0 — unfliable** | 1024 |
| `0xC63AA` | `gp-0x6b4c` | ±10240 | LKAS command lane | 1024 |
| `0xC63AC` | — | — | IIR pole A | **150** |
| `0xC6468` | — | — | shared gain 2639 | 2639 |

### 1.4 Downstream — LERP → `gp-0x6b70` → `gp-0x6ad6` → PID → aggregator

| cell | value | role | readers |
|---|---|---|---|
| `0xC63AE` | 1024 | **LERP index scale** — `idx = (|iVar6|·scale)>>10` | **1 reader, 0 writers** |
| `0xC6200` | 8192 | output clamp on `gp-0x6b70` | **≥3 functions** — see §4.2 |
| LERP knots | flash | mode- and speed-selected 2-D table | RULE 7 applies — §3 |

---

## 2. D2 — TRAP AUDIT. Every census tested; **one trap fired.**

### 2.1 Set-difference, Ghidra ∖ Python, every disagreement adjudicated

| cell | Ghidra | raw Python LE | disagreement | adjudication |
|---|---|---|---|---|
| `gp-0x6bfa` | 5 | 6 | `0x61576` | **EXCLUDED** — inside a stride-10 data table (`20 36 XX 00 \| 00 3a bf ff \| YY 94`). Decoded as an instruction its `reg1` field is **r0, not gp(r4)** ⇒ cannot be a gp-relative access |
| `gp-0x6bfe` | 2 | 2 | none | **EXACT MATCH** — 1W `0x3bc3e`, 1R `0x38218` |
| `gp-0x374c` | 2 | 3 | `0xc4606` | **EXCLUDED** — lies inside the cal DATA block; the two real ones are `\|1`-form `ld.w`@`0x381fe` / `st.w`@`0x38230` |
| `0xC63AE` | 1 | 1 | none | **EXACT MATCH** — `ld.hu`@`0x38242` only |

Both encodings covered: plain disp16 **and** the `|1` form, **and** the 6-byte extended form
`disp = (sext16(hw2)<<7) | ((hw1>>4)&0x7F)` — zero hits in the extended form for all three arms.

### 2.2 ⭐ The `ep`-relative aliasing trap — **it fired on the ACTUAL arm**

1,295 `movea imm,gp,ep` sites image-wide (raw scan for `24 f6 <imm16>`; the truncated Ghidra search
returned only 200 of them and would have hidden this).

- `gp-0x6bfa`, `gp-0x6bfe`: **0** bases within `sld` reach ⇒ clean.
- `gp-0x374c`: **5 bases in reach** — `0x35610`, `0x3566c`, `0x356a8`, `0x356cc`, `0x35708`, at offsets
  136 / 156 / 196, all ≤ 252 and word-aligned ⇒ all reachable by `sld.w`. One of them (`0x3566c`) uses
  **`add r22,ep`**, a genuine variable base. This is exactly the failure mode the brief warned about.
- **ADJUDICATED EXCLUDED by array extent** [EVIDENCE, `decompile_function(0x35610)` → `FUN_000352b4`]:
  the four `ep` arrays are **10 halfwords each** — the build loop is `do {...} while (bVar12 < 10)` and
  the copy loop is `iVar34 = 5` with two unrolled halfwords per iteration. They are based at
  `gp-0x3810`, `gp-0x37FC`, `gp-0x37E8`, `gp-0x37D4`, so the block spans `gp-0x3810 .. gp-0x37C2`, and
  the highest cell the function touches is `gp-0x37C4`. **`gp-0x374c` lies 118 bytes beyond the top of
  the highest array.** `r22` is the intra-array byte index and never leaves `[0,18]`.

🛑 Without the extent check this would have been reported clean for the wrong reason. The trap is real
on this arm and the exclusion is by **bound**, not by absence.

### 2.3 Traps that did **not** bite, recorded so the next session need not re-run them
- **Off-by-0x1000**: anchored — `tp+0x73AC` reads 102/150 exactly as the record says, and
  `tp+0x5000 = 0xC4000` was used throughout for `FUN_0003b8f6`'s cells.
- **`search_instructions` undercount**: every count above was confirmed by a raw LE scan. It *did*
  silently truncate on the `movea…ep` sweep (200 of 1,295) — the one place it mattered.
- **`ld.bu` parity**: no byte cals in this trace except `gp-0x6752` (polarity) and `0xC40BC`-family
  halfwords; both parities were scanned for every tp cal.

---

## 3. D4 — THE MODE QUESTION (RULE 7)

**Scalar cells are exempt.** `0xC63AE`, `0xC63AC`, `0xC63A0..AA`, `0xC6468`, `0xC6200` and all ten
`FUN_0003b8f6` cells are **single halfwords/floats with one load site each** — there is no mode record
and no per-mode row, so RULE 7 does not apply to them. That is a real advantage of every lever named in
§4 and it is the reason V69/V70's failure mode cannot recur for them.

**The LERP knots are the only table-valued item on this path, and RULE 7 does apply.** The car is
**TVCA4, modes 24/26**, and ⚠ **`mode 24 ≠ mode 26` in this family** — records 0/3/4/5 and the
breakpoints differ. The "stock ships 24 ≡ 26" memory is scoped to the **damper** families and does
**not** generalise here. **Any knot-valued V99 must prove which record the car reads or be marked a
BET.** I did not close that proof in this trace — see §6.

---

## 4. D3 — THE FOUR QUESTIONS, PER CANDIDATE

### 4.1 ⭐ `0xC63AE` — the LERP index scale. The one **arm-agnostic** lever.

This is the strongest candidate I found, and its distinguishing property is that **it does not care
which arm the comparator names**: it multiplies `|iVar6|` — the residual itself — after the difference
is formed. Whichever arm dominates, this lever acts on the result.

1. **SIGN — RESOLVED.** `idx = (|iVar6|·scale)>>10` feeds `LERP`, and **`f′ ≥ 0` is enforced in code at
   three ungated sites** (`0x388c4`'s eight `max(Y[i],Y[i−1])` rungs, the float-path monotone guard,
   `0x38de2`/`0x38e48`) ⇒ the transfer is monotone non-decreasing for **any cal, any mode, any build**.
   The output is re-signed by `sign(iVar6)` at `0x3824e`, which the scale cannot touch (`mulu` on
   `|iVar6|`). ⇒ **raising the scale strictly increases `|gp-0x6b70|`, sign-preserving.** This is the
   only lever in the set whose open-loop sign is closed by construction rather than by measurement.
   🛑 **Closed-loop sign is NOT thereby closed** — see §4.5.
2. **GAIN or POLE — it is a GAIN.** Unlike `0xC63AC` (DC gain 1.000000 at every value, which is exactly
   why V97 was uninterpretable) this cell **changes the DC transfer**. An amplitude statistic on
   `gp-0x6b70` — already a good instrument, 98.29 % nonzero, 250 codes, 0.000 % saturation — will see
   it. **A magnitude observable exists and is already flying.**
3. **BLAST RADIUS — the smallest possible: 1 reader, 0 writers**, agreeing exactly between Ghidra
   (`ld.hu 0x73ae[tp],r10` @ `0x38242`) and a raw both-parity LE scan (1 hit, same address). Touches
   nothing outside `FUN_00038148`'s Stage 2.
4. **HISTORY — VIRGIN across all 93 non-stock images.** Never written by any build script.

🛑 **THE COST — a real 16-bit wrap, and I must correct my own first pass on it.** `zxh r8` @ `0x3825c`
is a genuine zero-extend-halfword (confirmed at instruction level, **not** a decompiler artifact), so
the index truncates to 16 bits and **wraps** when `(|iVar6|·scale)>>10 > 65535`. A wrap sends a
saturating-large index to a small one ⇒ `gp-0x6b70` collapses discontinuously — a V80-class relay.

I initially bounded `|iVar6|` at 42,048 using a **measured** ACTUAL ceiling of 2,048 as though it were
structural. **That was wrong.** The structural steady state is `((sum6·2639)>>10)`, and with
`gp-0x6b4e ≡ 0` the six-lane window sum is 16,384 ⇒ ACTUAL can structurally reach **42,224** and
`|iVar6|` **82,224**:

| scale | ×  | wrap threshold | vs structural 82,224 | headroom over **measured** max 6,891 |
|---|---|---|---|---|
| 1024 | 1.00 | 65,535 | REACHABLE | 9.5× |
| 1229 | 1.20 | 54,603 | REACHABLE | 7.9× |
| 1434 | 1.40 | 46,797 | REACHABLE | 6.8× |
| 1536 | 1.50 | 43,690 | REACHABLE | 6.3× |
| 2048 | 2.00 | 32,767 | REACHABLE | 4.8× |

**The wrap is structurally reachable even at STOCK** ⇒ it is a pre-existing Honda condition that the
lane windows evidently never co-peg in practice, **not** something a dose would introduce. But the
margin scales inversely with the cell. ⇒ **Any dose here is bounded by the measured `|iVar6|`
distribution, and that distribution is creep-only** (route 80; it explicitly does not travel above
50 km/h, where `0xC669A`/`0xC66A8` truncate the LERP X axis). **[The safe-dose claim is BELIEF, resting
on a measured distribution with a known coverage hole — not a structural proof.]**

### 4.2 `0xC6200` — the ±8192 output clamp. **Rejected: inert upward, bad blast radius.**
Measured p99 on `gp-0x6b70` is 3,059 against a ±8192 rail with **0.000 % saturation** ⇒ **raising it does
nothing at all**, and lowering it below ~3,000 turns a clean lane into a clipper. And it is **not
private**: read by `FUN_00038148`, `FUN_0003a382` (bias clamp) **and** `FUN_000352b4`, where it clamps
an unrelated quantity — I found the third consumer in this trace. A raw scan cannot even cheaply bound
it (`0x7200`/`0x7201` are common byte patterns: 302 raw hits, each needing adjudication). **NO-GO.**

### 4.3 `0xC6468` = 2639 — **structurally cannot fix an imbalance.** Read at `0x381f2`
(`FUN_00038148`, the ACTUAL arm) **and at `0x3b94a` + `0x3bbba`, inside `FUN_0003b8f6` — the MODEL
producer.** ⇒ it scales **both arms together**, so it moves the residual's size but **cannot change the
arms' ratio**. If the comparator's answer is "the arms are wildly unequal", this cell is precisely the
wrong tool. ≥7 real readers across ≥4 functions. **NO-GO for the imbalance hypothesis.**

### 4.4 `0xC40D6` = 246 — the best MODEL-arm candidate if the comparator names MODEL.
VIRGIN 93/93, and the **dominant phase element of the entire plant model**: fc 9.86 Hz sits directly on
the 7.79 Hz ring (0.616 / **−73.9°** at 7.79 Hz), 2.2× `0xC40D4`'s contribution, and it acts on the
**acceleration** term. It is a **POLE**, so per the brief's own rule a phase/group-delay observable must
be named up front or it is unbuildable — the `gp-0x6b70` lane already carries the ring at coherence
0.95–0.97, which is where that observable would live. 🛑 **Its sign through the loop is NOT resolved**
(§4.5), and V86's `0xC40D4` precedent is a warning: a −32.1° phase move on the same function's dominant
term measured **1.001 [0.976, 1.060]** against a pre-registered [0.797, 0.875].

### 4.5 🛑 THE SIGN GATE THAT BINDS EVERY CANDIDATE HERE
`f′ ≥ 0` closes the **open-loop** sign only. `gp-0x6b70` is a **PID reference that gets SUBTRACTED**,
and Path 2 enters as `B = 1 + Q`, not in series ⇒ a Path-2 contribution's net sign depends on
`sign(iVar6)` **and** on the local LERP slope **and** on the unmeasured closed-loop `L`. The criterion
on record is *inversion iff `|Q| < 1` **and** `cos(arg Q) < −|Q|`*, and the measured `|Q| = 1.233` on
both routes **excludes inversion at any phase** — but that measurement was taken on hands-off engaged
returns at creep. **I did not re-derive it and I am not extending it to the symptom regime
(engaged + hands-on + override) on my own authority.** For `0xC63AE` specifically the open-loop sign is
closed by construction, which is strictly more than any of the six lane weights can claim, and it is the
reason I rank it first — **not** a claim that its closed-loop sign is proven.

### 4.6 The six lane weights — unchanged verdict, restated with this trace's evidence
`0xC63A8` **unfliable** (`gp-0x6b4e ≡ 0`; `0 × w = 0` for any `w`). `0xC63A0` **INERT by measurement**
(its lane read ~0 on 87,940 frames — its 8 flights tested nothing, and two of them, V74/V75, hard-faulted
on `0xC407E`). `0xC63A4` structurally <1 Hz. `0xC63A6` NO-GO on unresolved closed-loop sign.
`0xC63A2` (viscous) and `0xC63AA` (LKAS command) remain the only two with a coherent story, both
**VIRGIN 93/93**, both blocked on §4.5.

---

## 5. D5 — THE NEVER-RAISE LIST, confirmed from the on-car image

| cell | stock | car | status |
|---|---|---|---|
| `0xC4080` | 0 | **0** | K0 constant-Coulomb — **NEVER RAISE** (relay hazard). VIRGIN 93/93, and dead at 0. Confirmed untouched. |
| `0xC407E` | 511 | **511** | hard-fault interlock — Honda ships one count under its own 512 trip. V73 raised it ⇒ V74/V75 faulted. Confirmed at stock. |
| `0xC6CD0` | 65535 | **3564** | our own 4× LKAS gain. **Frozen on every build; scales EXCITATION, not loop gain — never recommend lowering it.** |
| `0xC40BC` | 600 | **600** | Coulomb relay. The standing "FREEZE at 6000" is **CONTRADICTED** — the car is at 600 and that is measurably better (2.89× vs 6.58×). Moved only on v85/v86/v86b. |

**Extension proposed — one new entry.** `gp-0x6bfa` (REQUEST) and its shadow `gp-0x4cfa` must be added
to the never-touch list for **cave/code work**, per §5.1.

### 5.1 🛑🛑 NEW SAFETY FINDING — the REQUEST arm is under an ACTIVE LOCKSTEP MONITOR [EVIDENCE]

`gp-0x6bfa` has a **shadow copy at `gp-0x4cfa`**. All three writers write **both**, and **every** write
path is guarded by `cmp r6,r14 / bne 0x273e2`, where a mismatch reaches
`movea -0x4cfa,gp,r6 ; jarl 0x0006b9fa,lp`.

`FUN_0006b9fa` is the **generic shadow-mismatch reporter**, taking the shadow cell's address in `r6`.
I found it invoked the same way on five further pairs inside `FUN_000352b4` alone:
`gp-0x69a4`/`gp-0x4c66`, `gp-0x6b7a`/`gp-0x4cdc`, `gp-0x6458`/`gp-0x4c0c`, `gp-0x6480`/`gp-0x4c20`,
`gp-0x6b86`/`gp-0x4cde`.

⇒ **Any cave or in-place patch that writes `gp-0x6bfa` without also writing `gp-0x4cfa` trips the
monitor.** This is a **GATE-1-class hazard not previously recorded for this cell**, and it is the kind
that produces an on-car fault rather than a quiet null.

⊕ **The asymmetry is useful in its own right:** `gp-0x6bfe` (MODEL) and `gp-0x374c` (ACTUAL) have **no
shadow** — consistent with V97 having moved the accumulator's pole with no fault, and with V89 having
moved the model's K1 with no fault. **The two arms that have been safely touched are exactly the two
that are not lockstep-protected.**

---

## 6. OPEN — what I did **not** close, and the exact next step

1. **RULE 7 for the LERP knots.** I did not prove which mode record the car reads for the Stage-2 knot
   table. **Next step:** `decompile_function(0x382d8)` (`FUN_000382d8`, the sole writer) to read the
   mode-byte selector, then confirm against `gp+0x63fd`. Required before **any** knot-valued V99.
2. **`0xC669A` / `0xC66A8`.** I read 0 and 12000 from the image, which does not match the "12,000 → 7,000
   above 50 km/h" shape in the record — that looks like a (lo, hi) pair rather than a speed-scheduled
   pair, but **I did not trace their readers and I am not asserting either reading.**
3. **The `|iVar6|` distribution above 50 km/h.** The safe-dose bound for `0xC63AE` (§4.1) rests on a
   creep-only measurement. The wrap margin at highway speed is **unmeasured**.
4. **Closed-loop sign in the symptom regime** (§4.5) — `|Q| = 1.233` was measured hands-off at creep;
   the symptom regime is engaged + hands-on + override.

---

## 7. SUMMARY — the pre-positioned lever set

| if the comparator names… | lever | class | sign | observable | blast radius | history |
|---|---|---|---|---|---|---|
| **any arm** (arm-agnostic) | **`0xC63AE`** | **GAIN** | open-loop **RESOLVED** by code-enforced `f′≥0` | amplitude on `gp-0x6b70`, already flying | **1R / 0W** | **VIRGIN 93/93** |
| **MODEL** | `0xC40D6` | POLE | unresolved | needs a phase/group-delay observable named up front | 2 loads, in-function | VIRGIN 93/93 |
| **ACTUAL** | `0xC63A2` / `0xC63AA` | GAIN | **unresolved — blocking** | lane amplitude | 1R each | VIRGIN 93/93 |
| **REQUEST** | **none exists** | — | — | — | — | **no cal cell on the arm at all** |

**The headline for V99 planning:** the REQUEST arm has no calibration lever and is lockstep-protected
against code edits, while `0xC63AE` is a virgin, single-reader, sign-resolved **gain** on the residual
that works whichever arm wins — with a real but quantified 16-bit wrap cliff that bounds the dose.

---
---

# ADDENDUM — after the V98 comparator result (route `0x81`)

The comparator retargeted this work: `b5` duty **0.0000** over 6,591 engaged frames ⇒ **REQUEST is the
smallest arm**; `b6` = **0.4235** ⇒ **MODEL and ACTUAL are comparable.** ⇒ `iVar6 ≈ MODEL − ACTUAL`, a
near-cancelling difference of two comparable estimates. §1.1's "REQUEST has no cal cells" therefore
closes that arm twice over. Everything below concerns the **mismatch** between the two live arms.

## 8. `0xC40BC` — the Coulomb relay normaliser. The measurement/theory conflict DISSOLVES.

### 8.1 What it is, assembly-exact [EVIDENCE]
```
0x3bab0  mul 0xc,r6,r0         ; x = polarity * gp-0x6abc * 12
0x3bab4  ld.hu 0x50bc[tp],r16  ; norm = 0xC40BC          (tp+0x50BC = 0xC40BC, NOT 0xC50BC)
0x3bab8  cvtf.ws  r6,r7        ; SIGNED convert of x
0x3babc  cvtf.uws r16,r9       ; UNSIGNED convert of norm
0x3bac4  movhi 0x3f00,r0,r14   ; 0.5f
0x3bac8  mulf.s r14,r7,r12     ; x * 0.5
0x3bacc  mulf.s r9,r14,r14     ; norm * 0.5
0x3bad0  divf.s r14,r12,r14    ; ramp = x / norm         <-- REAL FP DIVISION (the 0.5s cancel)
0x3bad8  cmp r10,r14 / ble     ; clamp to +1.0
0x3bae4  maxf.s r14,r7,r9      ; clamp to -1.0
0x3baf6  ld.hu 0x5080[tp],r12  ; K0 = 0xC4080 = 0
0x3bafe  ld.hu 0x50d2[tp],r12  ; K1 = 0xC40D2 = 204 (V89)
0x3bb0a  mulf.s r9,r14,r7      ; ramp * K0/1024
0x3bb0e  mulf.s r12,r9,r14     ; ramp * K1
0x3bb16  maddf.s r12,r10,r7,r14; friction = ramp*K1/1024*|model| + ramp*K0/1024
0x3bb22  ld.hu 0x50d0[tp],r14  ; then one-pole IIR, alpha = 0xC40D0/4096
```
```python
ramp     = clamp((polarity * gp_0x6abc * 12) / norm, -1.0, +1.0)   # 0x3bad0 .. 0x3bae4
friction = ramp * (K1/1024) * abs(model) + ramp * (K0/1024)        # 0x3bb16
```
**It is a saturating ramp on MOTOR RATE. It does NOT scale output magnitude** — the peak is
`K1·|model| + K0`, independent of `0xC40BC`. It sets **saturation duty and small-rate magnitude**, not
the ceiling.

### 8.2 🛑 THE RESOLUTION — V85 moved the KNEE out of the symptom band
Knee = `norm/12` counts = `(norm/12)/4.7121` column °/s:

| `0xC40BC` | knee | vs micro regime 1–13 °/s | small-signal gain |
|---|---|---|---|
| 150 | 2.65 °/s | inside | 4.0× |
| **300** | **5.31 °/s** | **inside, mid-band** | **2.0×** |
| **600 (stock, on car)** | **10.61 °/s** | inside, top edge | 1.0× |
| **6000 (V85)** | **106.1 °/s** | **far above ⇒ regime purely VISCOUS** | 0.1× |

**V85 neither hardened nor softened a relay — it removed modelled friction from the symptom regime**
(10× less there, and viscous rather than Coulomb). Per the kit's own observer logic — *under-modelled
friction is chased ⇒ stick-slip* — that predicts **worse**, which is what flew (2.89× → 6.58×).

⇒ **The desk theory and the flight are about different axes** — sharpness of the switch vs knee
position/magnitude in the regime. **`0xC40BC` moves both at once and they are not separable with this
cell.** No measurement is overturned; the code reconciles them.

### 8.3 The remaining four answers
- **Direction:** lowering ⇒ more modelled friction ⇒ (polarity chain) **LIGHTER wheel**.
- **K0:** the ramp is the **shared** normaliser (`0x3bb0a` K0, `0x3bb0e` K1, summed `0x3bb16`). **K0 = 0
  and `ramp × 0 = 0` for any ramp ⇒ lowering CANNOT numerically re-arm K0.** Lowering does reshape
  **K1's** term toward `sign(rate)·|model|·K1/1024`, but that stays **∝|model|** and **bounded by the
  ±10 clamp** — it is **not** K0's *pure, amplitude-independent, unbounded-index* hazard. Milder cousin.
- **Floor:** read **unsigned** (`cvtf.uws`) and used as a **divisor** (`divf.s`) ⇒ **value 0 gives
  ±Inf/NaN** into `gp-0x6bfc`/`gp-0x6bfe` and thence into float comparisons. **HARD FLOOR ≥ 1.**
  Usable range **300–600**.
- **Engagement gating — 🛑 NONE.** The entry guard is `|gp-0x6b98| ≤ 8192` ∧ `|gp-0x4f60| ≤ 25600` ∧
  `|gp-0x6abc| ≤ 13000` ∧ `polarity ∈ {−1,0,+1}` — **all plausibility/range guards.** It runs in MANUAL
  too ⇒ **fails the arc-map's engagement-gated-by-construction constraint**; V65 is the precedent.
- **`0xC40D4` interaction: NONE.** `0xC40D4` filters the command into `fVar18`; `0xC40BC` normalises the
  rate ramp. Different operands, meeting only at `maddf.s`. **Separable — the V86 confound does not
  weaken the direction argument.**

## 9. 🛑🛑 "MODEL IS UNFILTERED" IS REFUTED — seven EMA stages precede `gp-0x6bfe` [EVIDENCE]

| cal | val | stages | fc | phase @7.79 Hz | role |
|---|---|---|---|---|---|
| `0xC40D4` | 573 | **×2** | 24.0 Hz | **−33.25°** | command → `fVar18`, **the main path** |
| `0xC40D8` | 3686 | ×2 | 366 Hz | −0.62° | `gp-0x4f60` side term — **NO-OP** |
| `0xC40D0` | 408 | ×1 | 16.7 Hz | **−23.63°** | the friction term itself |
| `0xC40D6` | 246 | **×2** | 9.86 Hz | **−73.86°** | d/dt of rate → INERTIA, subtracted |

"MODEL UNFILTERED" holds only of `FUN_00038148`; `FUN_0003b8f6` filters it heavily upstream. **The
STATE.md diagram should be corrected.**

## 10. ⭐⭐ STOCK ENCODES AN **EXACT** PHASE MATCH BETWEEN THE ARMS — AND V97 BROKE IT

```
0xC40D0 = 408 / 4096 = 0.099609375    MODEL arm, friction-path EMA   @0x3bb22
0xC63AC = 102 / 1024 = 0.099609375    ACTUAL arm, accumulator pole   @0x38202
                       ^^^^^^^^^^^  BIT-IDENTICAL — both −23.63° @ 7.79 Hz
```
Two **differently-scaled** cal cells (÷4096 and ÷1024) chosen so the resulting α is bit-identical.
[**EVIDENCE** — read little-endian from `code.bin` and the V98 image.] [**BELIEF, strong** — a
deliberate matched-pole design for a difference of correlated estimates; an exact match across two
different scalings is hard to obtain by accident.]

**V97 set `0xC63AC` = 150 ⇒ α = 0.146484375 ⇒ the match is BROKEN.** The pole arithmetic confirms
**−23.63° at A=102** and **−15.81° at A=150**, i.e. **+7.82°** — so on a common basis V97 moved the two
stages from **9.62° apart to 17.45° apart**: **further out of alignment, not closer.**

⇒ If the mismatch story is right the corrective direction is **DOWN**. `A = 70` (−33.27°) would instead
align the accumulator with the MODEL's *main* path (`0xC40D4`×2, −33.25°).

🛑 **Scope limit:** this compares two *filter stages* on a common basis. It is **not** a total arm-to-arm
phase budget — the six lanes feeding the accumulator have their own upstream dynamics, not summed here,
nor is what feeds the command into `0xC40D4`. **"V97 went the wrong way" is EVIDENCE about the two poles
and BELIEF about the arms.**

## 11. RECOMMENDATION ORDER
1. **`0xC63AC` 150 → 102** — one byte, reverts to the value stock matches *exactly* to `0xC40D0`.
   Cheapest and best-grounded; undoes a change whose direction now looks wrong.
2. **`0xC40BC` 600 → 300** — well-aimed (knee mid-symptom-band), 2× small-signal gain. **Only if the
   ungated (manual-too) risk is accepted**, and GATE 2 remains unclosed (needs `L`; V80's failure mode
   is invisible to DTCs).
3. **`0xC63AE`** (§4.1) — the arm-agnostic magnitude lever, if a gain rather than a phase move is wanted.

⊕ **V89 re-read in the new light:** at 1 °/s the stock ramp delivers only **9.4 %** of full friction
(`4.7 ct × 12 / 600`), so V89 doubled a term that is mostly switched **off** at creep. That would explain
a flat result **and** argues `0xC40BC` (which moves the ramp) is better-aimed than `0xC40D2` (which moves
a magnitude the ramp is suppressing). ⚠ Rests on `|fVar18|`, which I have not measured.

Scripts: `analysis-2020accord/` equivalents of the scratchpad mirrors `c40bc_mirror.py`,
`model_arm_phase.py` (phase model reproduces `0xC63AC`'s known −23.63°/−15.81° to 0.01°).
