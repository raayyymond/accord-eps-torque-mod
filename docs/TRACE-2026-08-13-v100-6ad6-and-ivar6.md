# TRACE 2026-08-13 — `gp-0x6ad6`'s clamp, and whether `iVar6` is cave-reachable

Agent: `tracer-6ad6` (subagent). Program: **`code.bin`** (stock dump) in GhidraMCP, cross-checked
against `_v98_…_plain_image.bin` (ON THE CAR) and `_v99_…_plain_image.bin` with raw Python.
`gp = 0xFEDF8000`, `tp = 0xBF000`. Anchor check for the off-by-0x1000 trap: `0xC5200 = 2000`,
`0xC6200 = 8192` — the tp-relative resolution is confirmed against a known value before use.

---

## 0. HEADLINE — the claim is CONFIRMED, and it is stronger than the brief stated

> **`0xC6200` = 8192 is read at `0x3a7a2` INSIDE `FUN_0003a382` and hard-clamps `gp-0x6ad6` itself,
> before it becomes the PID error. All three of P, I and D are driven from that single clamped
> difference. `gp-0x6ad6` is written with a ±25600 clamp. Term 0 (`−gp-0x6b4a`) alone spans ±25600.
> ⇒ whenever `|gp-0x6ad6| ≥ 8192`, `∂(gp-0x6ad4)/∂(gp-0x6b70) = 0` through P, I and D simultaneously.**

The kit's own record has never said this. `BUILD-LINEAGE.md:490` describes `0xC6200` as
*"gp-0x6b70's clamp"* with **"15 readers, 3 of them still unidentified"**. The three unidentified
readers are `0x3a7a2` / `0x3a7b2` / `0x3a7c4` — **the PID's clamp on `gp-0x6ad6`.** RULE 11's census
on this cell is now complete (see §5).

🛑 **Direct conflict with a result accepted this week.** `path2-authority` reported
`d(gp-0x6b94)/d(gp-0x6b70) = 0.2565` at 7.79 Hz with *"no dilution anywhere, every link unity."*
**That is the UNSATURATED derivative.** The `±8192` clamp sits inside that very chain. When it is
active the true derivative is **0**, not 0.2565. The 0.2565 figure is correct as a small-signal gain
about an unsaturated operating point and must never again be quoted without that condition.

---

## 1. ENTRY POINT AND GOAL

Entry: the writer of `gp-0x6ad6` (`FUN_00037fe6` @`0x37fe6`) and its readers.
Goal: (Q1) is there a rail, is `0xC6200` the cell, can term 0 alone reach it, is a cave rung
buildable and at what byte cost, and what does a null license. (Q2) is `iVar6` cave-reachable.

---

## 2. Q1 PATH — every hop, address by address

### 2.1 `gp-0x6ad6`'s FULL CENSUS — Ghidra ∖ Python set-difference is EMPTY [EVIDENCE]

| method | result |
|---|---|
| GhidraMCP `search_instructions(operand_pattern="6ad6")` | 3 hits, `instructions_scanned: 183570`, `truncated:false` |
| Python raw LE disp16 scan over `[0x13000,0x100000)`, both bit-0 aliases, `reg1==gp` | **5 hits** |
| Python raw **disp23** (6-byte) scan, `disp=(sext16(hw2)<<7)\|((hw1>>4)&0x7F)` | **0** |
| Byte-aligned search for the 32-bit literal `0xFEDF152A` (register-indirect base formation) | **0 occurrences image-wide** |
| `ep`-relative short-format aliasing (the V97-session trap class) | **0** — see §2.2 |

Adjudication of the two extra Python hits — **both EXCLUDED, with reason:**

- `0xBCC52` and `0xBDF92`, bytes `443f2b95`. hw1 `0x3f44` decodes `st.b r7, -0x6ad5[gp]` — that is
  **disp = −0x6ad5, not −0x6ad6**; my scanner's bit-0 alias rule (correct for `ld.w`/`st.w`/`ld.hu`)
  does **not** apply to `st.b`. Both sit inside a monotone data table
  (`…433f35f3 433fe01b 443f6c44 443fdb6c 443f2b95 443f5cbd 443f70e5 443f650d…`, stride ≈ 0x2840,
  byte-identical at both addresses), and `get_function_by_address(0xBCC52)` returns
  **"No function found"**. **Data, not instructions.**

⇒ **`gp-0x6ad6` has exactly ONE writer and TWO readers:**

| addr | instruction | role |
|---|---|---|
| `0x38142` | `st.h r6,-0x6ad6[gp]` | the sole writer, end of `FUN_00037fe6` |
| `0x3a6ba` | `ld.h -0x6ad6[gp],r15` | **plausibility gate only** — `\|gp-0x6ad6\| ≤ 25600` AND `\|gp-0x4f60\| ≤ 25600`, feeding `setfnc` → the PID enable `bVar1` |
| `0x3a798` | `ld.h -0x6ad6[gp],r7` | ⭐ **THE CONTROL PATH** |

No lockstep shadow: `FUN_00037fe6`'s disassembly contains exactly one `st.h`. (Contrast
`gp-0x6b4a`, which **does** have one — see §2.5.)

### 2.2 The `ep`-relative aliasing check — a VERIFIED zero, not a tool zero [EVIDENCE]

Deliberately over-inclusive Python scan: every byte-aligned pattern decoding as
`movea imm16, gp, ep` (`(hw1>>5)&0x3F == 0x31`, `reg2 == 30`, `reg1 == 4`) over
`[0x13000,0x100000)` — **1,295 candidates**, a superset that includes data false positives. For
each, the `sld`/`sst` reach window `[imm, imm+254]` was tested against the target displacement:

| cell | candidate `ep` bases in reach |
|---|---|
| `gp-0x6ad6` | **0** |
| `gp-0x6b4a` | **0** |
| `gp-0x6b70` | **0** |
| `gp-0x6bfa` | **0** |
| `gp-0x6bfe` | **0** |
| `gp-0x374c` | 5 (`0x35610`, `0x3566c`, `0x356a8`, `0x356cc`, `0x35708`) |

The five for `gp-0x374c` were **adjudicated individually**: `disassemble_bytes(dry_run:true)` at
`0x35604` shows `movea -0x37d4,gp,ep` followed by `sld.hu` at offsets `0x0, 0x2, 0x4, 0x6, 0x8, 0xa,
0xc, 0xe, 0x10` only — reaching `gp-0x37d4 … gp-0x37c4`. **`gp-0x374c` (offset 0x88) is never
touched.** No ep-relative access to any of the six cells.

### 2.3 THE WRITER — `FUN_00037fe6`, mirrored exactly [EVIDENCE, `disassemble_function(0x37fe6)`]

```python
# FUN_00037fe6  @0x37fe6 .. 0x38146   — called ONCE per 1 kHz pass from FUN_0002214a @0x22696
def gate(x, half):                      # the ZERO-REJECT window idiom, addi/addi/cmovc
    return x if -half <= x <= half else 0   # e.g. 0x37ff4 addi 0x6400 / 0x37ff8 ori 0xc801 / 0x38000 bnc

iVar4 = 0
if -25600 <= s16(gp_0x6b4a) <= 25600:                 # 0x37fea..0x38000  (ALWAYS true, writer-clamped)
    iVar4 = -s16(gp_0x6b4a)                           # 0x38002 sub r15,r10   <-- TERM 0, NEGATED

if not (u8(gp_0x67ab) == 1):                          # 0x37fee cmp/0x37ff0 cmovh/0x380b0 cmp/0x380b2 be
                                                      #   gp-0x67ab == 0 STRUCTURALLY  => ALWAYS taken
    iVar4 += gate(gp_0x6bc2, 10240) * cal8(0xC64AE)   # 0x380a8 cmovc / 0x380ac mulh
    iVar4 += gate(gp_0x6b60, 15360) * cal8(0xC64B2)   # 0x38090 / 0x38094   <-- WIDER window
    iVar4 += gate(gp_0x6b2a, 10240) * cal8(0xC64B3)   # 0x3807c / 0x38080
    iVar4 += gate(gp_0x6bce, 10240) * cal8(0xC64AD)   # 0x38064 / 0x38068
    iVar4 += s16( gate(gp_0x6b6e,10240)*cal8(0xC64B1)
                + gate(gp_0x6bbc,10240)*cal8(0xC64AF) )   # 0x3803e..0x3804c  (inner pair, sxh'd)
    iVar4 += gate(gp_0x6b70, 10240) * cal8(0xC64B0)   # 0x3801e / 0x38046   <-- ALL OF PATH 2

sp = speed_lerp(gp_0x69aa)                            # 0x380b6..0x38122
r10 = (iVar4 * sp) >> 10                              # 0x38124 mul r12,r10,r0 / 0x38128 sar 0xa,r10
gp_0x6ad6 = +25600 if r10 > 25600 else (-25600 if r10 < -25600 else r10)   # 0x3812a..0x3813e
                                                      # 0x38142 st.h r6,-0x6ad6[gp]
```

**Two facts that collapse this to an identity, both read from the image:**

1. **The seven weights `0xC64AD..0xC64B3` are ALL `1`.** Byte-read from `code.bin` and from the
   V98 (on-car) and V99 images: `[1,1,1,1,1,1,1]`. Loaded by `ld.bu` at
   `0x38054/0x3800a/0x38040/0x3801a/0x38074/0x38086/0x3809c` and applied with `mulh` — unity.
2. **The speed LERP is the IDENTITY at every speed.** Table header `0xC6AB8` = 8 knots,
   X `0xC6ABA..0xC6AC8` = `[0,6554,13107,19661,22938,26214,29491,32768]`,
   **Y `0xC6ACA..0xC6AD8` = `[1024]×8`**, below-first-knot value `0xC6ACA` = 1024, above-last
   `0xC6AD8` = 1024, and the `uVar3 > 0x8000` fallback `0xC6448` = **1024**.
   ⇒ `(iVar4 * 1024) >> 10 == iVar4` exactly, all speeds, no rounding.

⇒ **`gp-0x6ad6 = clamp( −gp-0x6b4a + Σ(seven zero-reject-gated terms), ±25600 )`.** Unweighted,
unscaled. All of the above is **byte-identical to stock on V98 (on the car) and V99** — verified:
`code[0x37FE6:0x38146]` matches the stock dump on both images.

### 2.4 ⭐ THE READER THAT MATTERS — the ±8192 clamp, and it is `0xC6200` [EVIDENCE]

`disassemble_bytes(0x3a778, dry_run:true)` and `(0x3a7c4, dry_run:true)`, corroborated by
`decompile_function(0x3a382)`:

```
0003a798: ld.h  -0x6ad6[gp],r7        ; r7 = the REFERENCE, as written (±25600)
0003a7a2: ld.h  0x7200[tp],r6         ; r6 = cal 0xC6200 = +8192          <-- THE CLAMP CONSTANT
0003a7b2: ld.hu 0x7200[tp],r11        ; r11 = 8192
0003a7b0: cmp   r6,r7
0003a7b6: ble   0x0003a7bc            ;   r7 <= +8192 ?
0003a7b8:   mov r11,r7                ;     NO  -> r7 = +8192             <-- HIGH RAIL
0003a7ba:   br  0x0003a7ca
0003a7bc: subr  r0,r11                ; r11 = -8192
0003a7be: sxh   r11
0003a7c0: cmp   r11,r7
0003a7c2: bge   0x0003a7ca            ;   r7 >= -8192 -> keep
0003a7c4:   ld.hu 0x7200[tp],r7
0003a7c8:   subr  r0,r7               ;     r7 = -8192                    <-- LOW RAIL
0003a7ca: ld.h  -0x4f60[gp],r8        ; r8 = the MEASURED DRIVER TORQUE
0003a7ce: sub   r7,r8                 ; r8 = torque − clamp(ref, ±8192)   <-- THE PID ERROR
0003a7d0..0x3a7e2:                    ; err = clamp(err, ±10240)   (0x2800, an IMMEDIATE not a cal)
0003a7e8: mul   lp,r8,r0              ; × Kp …
```

Mirrored in integer Python, with the decompile as the structural check:

```python
REF   = s16(gp_0x6ad6)                                   # 0x3a798
CLAMP = u16(cal 0xC6200)          # = 8192               # 0x3a7a2 / 0x3a7b2 / 0x3a7c4
ref_c = max(-CLAMP, min(CLAMP, REF))                     # 0x3a7b0..0x3a7c8
err   = s16(gp_0x4f60) - ref_c                           # 0x3a7ca / 0x3a7ce
err   = max(-10240, min(10240, err))                     # 0x3a7d0..0x3a7e2   (SECOND saturation)
# err then feeds ALL THREE terms — there is no other entry point for gp-0x6ad6:
I  = gp_0x367c + (((err*Kp_lerp)>>10)*32 - gp_0x367c) * cal(0xC7450) >> 10
P  = ((Kp2_lerp * err) >> 10) + gp_0x3688          # anti-windup bracketed
D  = ((err - gp_0x3684) * Kd_lerp) >> 10           # then slewed into gp-0x3680
gp_0x6ad4 = (((D + I_state + I) >> 5) * gainA >> 10) * sign(gp_0x6752)
```

⇒ **`∂err/∂REF = −1` iff `|REF| < 8192`, and `0` otherwise. Because P, I and D all derive from
`err` and from nothing else touching `gp-0x6ad6`, the whole PID's sensitivity to `gp-0x6ad6` — and
therefore to `gp-0x6b70`, which enters `gp-0x6ad6` at unit weight — is EXACTLY ZERO when the clamp
is active.** [EVIDENCE: the instruction stream above + the decompile + the unity weight `0xC64B0`=1
+ the identity speed LERP.]

⚠ **There is a SECOND saturation in series** — the `±10240` error clamp at `0x3a7d0`. It also zeroes
the derivative, and it is reachable independently (driver torque alone can push `err` past 10240
even with the reference clamped). **Marginal authority is zero if EITHER saturation is active.**
Any instrument that scores only the first will UNDER-count the zero-authority duty.

### 2.5 "TERM 0 ALONE CAN RAIL IT" — CONFIRMED, and the bar is far lower than stated [EVIDENCE]

`gp-0x6b4a`'s writer, `disassemble_bytes(0x2775c, dry_run:true)`:

```
00027772: addi -0x6400,r23,r0          ; r23 = the 11-lane sum + rate-limited accumulator
0002777a: ble  0x2778e
00027780: movea 0x6400,r0,r6           ;   -> +25600
00027784: st.h r6,-0x6b4a[gp]
00027788: st.h r6,-0x4cd2[gp]          ; 🛑 SHADOW-LOCKSTEP TWIN (new to the kit record)
00027798: movea -0x6400,r0,r6          ;   -> -25600
0002779c/0x277a0: st.h  ... -0x6b4a / -0x4cd2
000277aa: st.h r23,-0x6b4a[gp]         ; in-range pass-through
```

⇒ `gp-0x6b4a ∈ [−25600, +25600]`, and `term0 = −gp-0x6b4a` spans the same.

🛑 **The refinement that matters: term 0 does NOT need to rail `gp-0x6ad6` at ±25600. It only needs
to push `|gp-0x6ad6|` past 8192 — 32.0 % of its own clamp.** The brief's framing ("`gp-0x6ad6` runs
to ±25600, term 0 can rail it") understates the hypothesis by 3.125×.

Reachable ranges of every term into `gp-0x6ad6`, against the ±8192 PID clamp:

| term | cell | reject window / clamp | ratio to the 8192 clamp |
|---|---|---|---|
| **0** | `gp-0x6b4a` | **±25600** (writer clamp) | **3.125×** |
| 1 | `gp-0x6bc2` | ±10240 | 1.25× |
| 2 | `gp-0x6b60` | **±15360** | 1.875× |
| 3 | `gp-0x6b2a` | ±10240 | 1.25× |
| 4 | `gp-0x6bce` | ±10240 | 1.25× |
| 5 | `gp-0x6b6e` + `gp-0x6bbc` | ±10240 each, pair `sxh`'d | 1.25× each |
| **7** | **`gp-0x6b70` — ALL OF PATH 2** | gate ±10240, but the cell is **clamped ±8192** by the SAME cal `0xC6200` | **1.000×** |

⭐⭐ **`0xC6200` appears TWICE in one loop: at `0x382ac` it clamps `gp-0x6b70` (Path 2's entire
output), and at `0x3a7a2` it clamps `gp-0x6ad6` (the whole reference). The SAME number.**
⇒ **Path 2's full-scale output is EXACTLY the width of the window it has to fit inside.** Any
co-contribution from the other seven terms eats that headroom one-for-one. Structurally this is a
system designed so Path 2 can own the reference *only when nothing else is asking for it.*

### 2.6 The distribution of `gp-0x6ad6` is UNMEASURED — that is the whole point [EVIDENCE of absence]

`grep -rl "6ad6" analysis-2020accord/build_v*_tva.py` → `v43, v46, v52, v52c, v53, v96, vfourframe`
— all **references in prose/cal tables**, none a probe on the cell. **`gp-0x6ad6` has never been on
the wire.** No build has ever measured it; the 0.2565 authority figure was derived analytically.

---

## 3. Q1 — THE BUILDABILITY VERDICT

### 3.1 The rung is a COMPARATOR, not a threshold — and that is not a rhetorical dodge

The brief asks: *is `|gp-0x6ad6| ≥ 8192` a bare threshold on an unmeasured distribution?*

**No — provided you build it as `|gp-0x6ad6| ≥ cal(0xC6200)`, reading the constant at runtime from
the very cell the PID reads at `0x3a7a2`.** Then:

- there is **no LSB and no quantisation** — it compares at full 16-bit precision inside the cave;
- there is **no assumed scale** — the threshold is not a guess about the signal, it is the
  mechanism's own boundary, and the answer it gives is *"is the mechanism active"*, which is a
  binary structural fact, not a percentile;
- it is **immune to a future cal edit** of `0xC6200` (which is a live lever candidate: 15 readers).

This is materially different from V69's rungs (thresholds against guessed magnitudes) and from
V96's regressor (34× over-range). **Its duty IS the answer.**

### 3.2 THE BYTE COST — priced against V98's flown payload, idiom for idiom

The flown V98 cave is 154 B at `0xC4B34`, hook `0x55C0E = jarl 0xC4B34,lp` on the **100 Hz `0x14A`
builder** (`0x55C14 = movea 0x14A,r0,r8`), interrupts OFF across it, store set exactly
`{gp-0x1514, gp-0x1511}`, extent `0xC4B34..0xC4FF0` = 1212 B free (12.7 % used).

**RUNG A — `|gp-0x6ad6| ≥ cal(0xC6200)` — 24 BYTES:**

```
2437 2a95   ld.h  -0x6ad6[gp],r6      4 B   hw1 `2437` = flown cave +0x02 ; hw2 `2a95` = HONDA @0x3a79A
6032        cmp   0x0,r6              2 B   flown cave +0x06
ae05        bge   +4                  2 B   flown cave +0x08
8031        subr  r0,r6               2 B   flown cave +0x1C   (NOT satsubr 3080)   -> r6 = |ref|
0638        mov   r6,r7               2 B   HONDA @0x14EEE                          -> r7 = |ref|
e537 0172   ld.hu 0x7200[tp],r6       4 B   HONDA @0x382BC and @0x354E0, byte-verbatim -> r6 = 8192
e639        cmp   r6,r7               2 B   HONDA @0x1BD96     flags = |ref| − 8192
xx3a        mov   imm,r7              2 B   HONDA (V98 uses @0x1708C / @0x1A79C)  ASSUME SET
ae05        bge   +4                  2 B   flown cave +0x08   taken iff |ref| >= 8192 ⇒ KEEP
003a        mov   0x0,r7              2 B   flown cave +0x00   else CLEAR
                                     ====
                                     24 B
```

- **ZERO new registers** — `r6`/`r7` only, V96's proven discipline.
- **ZERO new branch conditions** — `{bge}` only; the cave's set stays `{bge, bnh}`.
- **ZERO new stores** — the store set stays exactly `{gp-0x1514, gp-0x1511}`, 3 stores, 2 cells.
- **ZERO new twin classes** — every 2/4-byte group already exists either in the flown cave or as a
  Ghidra-certified Honda instruction. The one genuinely new 4-byte group is `e5370172`
  (`ld.hu 0x7200,tp,r6`), which is **byte-verbatim Honda at `0x382BC`** — an instruction inside
  `FUN_00038148`, the function this whole trace is about.

**Net cost: −8 BYTES.** RUNG A (24 B) replaces V98's PASS-1 comparator (32 B, `+0x00..+0x1F`), whose
measurand — `|REQUEST| ≥ |ACTUAL|` — is the one V98 already answered and which §2 of the handoff
established licenses nothing. The PASS-1 merge (`+0x22..+0x2F`, 14 B) is reused unchanged.
**Cave 154 → 146 B, 12.0 % of the extent.** The rung is not merely affordable; it is free.

**RUNG B — `gp-0x6ad6 < 0` (the reference's SIGN) — 10 BYTES**, exactly V96's flown b7 idiom with
one hw2 changed:
```
2437 2a95   ld.h -0x6ad6[gp],r6   4 B
6032        cmp  0x0,r6           2 B
ae05        bge  +4               2 B
483a        add  0x8,r7           2 B      (accumulates into an already-seeded r7)
```
Drop-in for V98's b3 (`gp-0x6752` polarity), which is **SPENT** — `sign(gp-0x6752) = −1` constant,
0.0000 over 17,983 frames, and V99 already hard-wires that bit as an identity constant. **Net 0 B.**

**RUNG C — `|gp-0x6ad6| ≥ |gp-0x6b70|` (Path 2's SHARE of the reference) — 30 B + 14 B pass merge:**
V98's PASS-1 skeleton with both operands 16-bit. 🛑 **A comparator consumes BOTH free registers, so
it must SEED `r7` and therefore OWNS its pass.** Two comparators ⇒ two passes ⇒ +14 B of
`ld.bu`/`andi`/`or`/`st.b`. **Net +44 B** unless a third scratch register is proven dead at the hook
— a NEW liveness claim the brief rules out, and I do not propose it.

**Total for the recommended V100 instrument** (RUNG A + RUNG C + RUNG B + carry V98's b6
MODEL-vs-ACTUAL + carry b7 `gp-0x6b70` sign; drop b5, b4, b3):
**154 − 8 + 44 + 0 = 190 B, 15.7 % of the 1212 B extent.** Store set unchanged. Register set
unchanged. Branch-condition set unchanged.

**Minimum viable V100** (RUNG A + RUNG B only, everything else carried): **146 B, 12.0 %** — smaller
than what is on the car today.

### 3.3 GATES

- **GATE 1 (RAM ownership).** The cave only **READS** `gp-0x6ad6` and `0xC6200`. Store set unchanged
  at `{gp-0x1514, gp-0x1511}` — 3 stores, 2 cells, flown on 5 routes. `gp-0x6ad6` has **one writer,
  two readers, no shadow twin, no `ep` alias, no register-indirect base** (§2.1–2.2). **PASS.**
- **GATE 2 (closed-loop stability).** **Not applicable** — no control signal is altered. Zero
  calibration bytes. Zero code edits outside the cave. This is a pure instrument.
- **GATE 3 (size against the lane's own reachable output).** Satisfied by construction: there is no
  field to size. A comparator has no LSB and no ceiling.

---

## 4. ⭐ Q1 — THE PRE-REGISTERED SENTENCES, written BEFORE the cut

Let **`d_clamp`** = duty of `|gp-0x6ad6| ≥ cal(0xC6200)` over engaged frames;
**`d_share`** = duty of `|gp-0x6ad6| ≥ |gp-0x6b70|` (RUNG C, the positive control).

**A POSITIVE reading — `d_clamp` materially > 0, e.g. ≥ 0.30 — licenses EXACTLY:**
> *"On `d_clamp` of engaged frames the PID's reference was pinned at ±8192 by cal `0xC6200`, so on
> those frames `∂(gp-0x6ad4)/∂(gp-0x6b70)` was **exactly zero** and every gain upstream of it —
> `0xC40D2` (V89), `0xC63AC` (V97), `0xC63AE`, the six lane weights, `0xC6468` — had **no effect on
> the delivered command at all**. V89's flat dose-response and V97's felt-null are then explained by
> **one mechanism, requiring nothing unmeasured**: the levers were live, correctly aimed and
> correctly signed, and their output was thrown away by a saturation. The next lever must move
> `0xC6200` or move term 0 (`gp-0x6b4a`), not anything inside the observer."*

Additional strength if it **co-varies with the symptom**: the same partial-Spearman-vs-6–9 Hz-RMS
test that gave V98 its best result (`b6 r = −0.321, p = 0.0050`). A positive `d_clamp` that RISES
with the symptom is the strongest possible form of this result.

**A NULL — `d_clamp` = 0.0000 with `d_share` healthy (strictly between 0.05 and 0.95) — licenses EXACTLY:**
> *"`gp-0x6ad6` never reached the PID's ±8192 clamp in any engaged frame. Path 2's marginal
> authority was therefore NOT zeroed by this saturation, `d(gp-0x6b94)/d(gp-0x6b70) = 0.2565` stands
> unconditionally in the flown regime, and the `f′`-compression account in `STATE.md` remains the
> only surviving explanation for V89 and V97. **The saturation hypothesis is DEAD and must not be
> re-proposed.**"*

**An UNINTERPRETABLE outcome — `d_clamp` = 0.0000 AND `d_share` = 0.0000 (or 1.0000)** — means the
instrument failed, not that the hypothesis failed. **RUNG C exists solely so this case is
distinguishable.** This is the design law applied literally: a threshold rung paired with a
scale-free magnitude channel that has a *known* distribution (`gp-0x6b70` is already on CAN 427,
p50 320 / p90 2,534 / max 3,187 on route 80, nonzero on 98.29 % of frames) — so `d_share` has a
**predicted** value and a wildly-off `d_share` indicts the instrument, not the car.

🛑 **The honest residual, stated before the cut:** the rung scores only the FIRST saturation.
`d_clamp = 0` does **not** license *"Path 2 always had authority"* — the `±10240` error clamp at
`0x3a7d0` can zero it independently. If the budget stretches, a fourth rung
`|gp-0x4f60 − clamp(gp-0x6ad6,±8192)| ≥ 10240` (~34 B, its own pass) closes that. **If it is not
built, the null sentence above must be qualified with "by THIS saturation" — as it is.**

---

## 5. `0xC6200`'s READER CENSUS — RULE 11 now COMPLETE [EVIDENCE]

Raw Python LE scan for tp-relative disp16 `0x7200`/`0x7201`, `[0x13000,0x100000)`: **15 hits**,
matching `BUILD-LINEAGE.md:490`'s count exactly.

| addresses | function | role |
|---|---|---|
| `0x353de`, `0x353f0`, `0x354ce`, `0x354da`, `0x354e0`, `0x354f0` (6) | `FUN_000352b4` | the friction-magnitude lane (`gp-0x6b86`) |
| `0x382ac`, `0x382b6`, `0x382bc`, `0x382c6` (4) | `FUN_00038148` | **clamps `gp-0x6b70`** — Path 2's output |
| `0x38a94` (1) | `FUN_000389ec` | the Stage-2 LERP's `Y[9]` |
| `0x39ff6` (1) | `FUN_00039702` | *(not chased — outside this brief)* |
| **`0x3a7a2`, `0x3a7b2`, `0x3a7c4` (3)** | **`FUN_0003a382`** | 🛑 **clamps `gp-0x6ad6` — NEW TO THE RECORD** |

⇒ **The "3 still unidentified" readers were the PID's clamp on the reference.** `BUILD-LINEAGE.md`
should be updated. ⚠ **And a warning for any future lever on `0xC6200`: it is NOT "gp-0x6b70's
clamp". Raising it widens `gp-0x6b70`'s output AND widens the reference window AND raises the LERP's
`Y[9]` AND changes the friction lane — four effects, three of them in the same loop.**

---

## 6. Q2 — IS `iVar6` CAVE-REACHABLE?

### 6.1 `iVar6` is REGISTER-ONLY [EVIDENCE]

`disassemble_function(0x38148)` gives the complete instruction stream of `FUN_00038148`
(`0x38148..0x382d6`). It contains **exactly two stores**:

```
00038230: st.w r6,-0x374c[gp]      ; the Stage-1 IIR accumulator (32-bit)
000382d2: st.h r11,-0x6b70[gp]     ; the Stage-2 output
```

Cross-checked by a raw Python store scan over the same range (op `0x3A`/`0x3B`, `reg1==gp`): same
two, nothing else. `iVar6` lives in `r6` at `0x3823a` and is consumed in-register.
⇒ **`iVar6` is NEVER stored. It cannot be read directly by any cave. [EVIDENCE]**

### 6.2 The residual arithmetic, byte-exact

```
000381fe: ld.w  -0x374c[gp],r6      ; r6 = the OLD accumulator
00038208: ld.h  -0x6bfa[gp],r7      ; r7 = REQUEST
00038218: ld.h  -0x6bfe[gp],r15     ; r15 = MODEL
00038222: add   r14,r6              ; r6 = accumulator + IIR step   (0xC63AC is the pole)
00038230: st.w  r6,-0x374c[gp]      ; <-- the NEW accumulator is COMMITTED here
00038234: bnc   0x382ce             ; |gp-0x6bfe| > 20000 -> gp-0x6b70 = 0x7fff  (never fired, 96,414 frames)
00038236: sar   0x4,r6              ; r6 = ACTUAL = gp-0x374c_new >> 4
00038238: subr  r15,r6              ; r6 = MODEL − ACTUAL          (subr reg1,reg2 : reg2 = reg1 − reg2)
0003823a: add   r9,r6               ; r6 = iVar6                    (r9 = gated REQUEST)
```
⇒ `iVar6 = gp_0x6bfe − (gp_0x374c >> 4) + gp_0x6bfa`, coefficients exactly ±1.
🛑 **The `>>4` is applied to the NEWLY COMMITTED accumulator** — the cave reads the same committed
value, so the shift is reproducible bit-for-bit (and `sar 0x4,r6` = `a432` is available as a
byte-verbatim Honda twin at `0x38236`, which the flown V98 cave already uses).

### 6.3 ⭐ THE SAMPLING-SKEW RISK IS SMALLER THAN FEARED — the call ORDER closes it [EVIDENCE]

Raw Python decode of every `jarl disp22,lp` inside `FUN_0002214a` (the 1 kHz control task —
established single-rate, no phase dividers):

```
0x22416  -> FUN_0003bc20    writes gp-0x6bfe   (MODEL)
0x225f6  -> FUN_00026c80    writes gp-0x6bfa   (REQUEST)  and gp-0x6b4a
0x22676  -> FUN_00038148    READS all three; writes gp-0x374c and gp-0x6b70
0x22696  -> FUN_00037fe6    writes gp-0x6ad6
0x226a0  -> FUN_0003a382    READS gp-0x6ad6 -> the PID
```

⇒ **All five run in ONE pass, in that fixed order.** Between `0x226a0` returning and the next
pass reaching `0x22416`, the four cells `gp-0x6bfe`, `gp-0x6bfa`, `gp-0x374c`, `gp-0x6ad6` are
**mutually consistent** — a cave reading them gets *exactly* the triple `FUN_00038148` used and
*exactly* the reference `FUN_0003a382` used.

| | skew |
|---|---|
| **`gp-0x6ad6` (Q1)** | **ZERO by construction** — it is a committed cell, read one pass later. No recomputation, no skew term at all. |
| **recomputed `iVar6` (Q2)** | **ZERO** if the 100 Hz hook lands outside `[0x22416, 0x22676]`; **≤ one 1 kHz tick on ONE arm** if it lands inside. |

Worst-case magnitude of the inside-window error, at the symptom frequency:
`Δ ≈ A·2π·f·Δt = A·2π·7.79·0.001 = 0.049·A` per arm.
Against the measured `|iVar6|` **p50 = 2,829 ct hands-ON** (route 81, `steeringPressed`) with arms of
order 3,000 ct: **error ≈ 150 ct per arm, ≲ 10 % of the residual.** Acceptable for a comparator.
🛑 **Against `|iVar6|` p50 = 188 ct hands-OFF, the same 150 ct error is ~80 % — the recomputation is
VALID in the hands-ON (symptomatic) regime and INVALID hands-off.** That happens to be the right
way round, but it must be stated and the scoring must be masked on `steeringPressed`.

⚠ **One unresolved sub-question:** whether the 100 Hz `0x14A` builder can preempt a partially
completed 1 kHz pass at all. Interrupts are OFF *across* the cave (`0x55C0A jarl FUN_0001fa42`), which
prevents the cave being interrupted but does not by itself prove the cave cannot *start* mid-pass.
**To confirm zero skew outright, the next step is the interrupt-priority registers for the two
tasks** — the `UPD70F3508` SVD's INTC block plus the priority writes at boot. I did not run it.

### 6.4 `gp-0x6bfa`'s shadow lockstep — reading is free [EVIDENCE]

`disassemble_bytes(0x27390, dry_run:true)`:
```
00027396: ld.w  -0x3d90[gp],r15        ; the 11-slot aggregator output, 32-bit
0002739a: ld.h  -0x4cfa[gp],r6         ; the SHADOW
000273b0: st.h  r14,-0x6bfa[gp]        ; clamp(+20000)   } every write goes to BOTH
000273b4: st.h  r14,-0x4cfa[gp]        ;                 }
000273c8/0x273cc: (−20000) pair
000273d6/0x273dc: (pass-through) pair
0002739a + 0x273a8 `cmp r6,r14` + `bne 0x273e2` : the mismatch trap -> jarl 0x6b9fa
```
⇒ The lockstep is a **write-side consistency check between `gp-0x6bfa` and `gp-0x4cfa`**. A cave that
only **reads** `gp-0x6bfa` cannot perturb it. **Reading is free. CONFIRMED.**
🛑 **New to the record: `gp-0x6b4a` has the SAME protection**, shadow at **`gp-0x4cd2`**
(`0x27788`, `0x277a0`, and the `cmp r6,r15`/`bne 0x277b6` trap at `0x2777c`). Same conclusion:
reading is free; **writing either cell would trip a hard-shutdown monitor.**

### 6.5 THE BYTE COST OF `|iVar6| ≥ |gp-0x6bfa|`

```
2437 0294   ld.h  -0x6bfe[gp],r6      4 B   flown cave +0x30..+0x33, VERBATIM
0638        mov   r6,r7               2 B   flown cave +0x3A               r7 = MODEL
2437 b5c8   ld.w  -0x374c[gp],r6      4 B   flown cave +0x3C, VERBATIM (HONDA @0x381FE)
a432        sar   0x4,r6              2 B   flown cave +0x40  (HONDA @0x38236)
????        sub   r6,r7               2 B   🛑 NEW ENCODING — needs a Ghidra-certified twin
2437 0694   ld.h  -0x6bfa[gp],r6      4 B   flown cave +0x00..+0x03, VERBATIM   r6 = REQUEST
????        add   r6,r7               2 B   🛑 NEW ENCODING — needs a twin      r7 = iVar6
6032 ae05   cmp 0x0,r7 / bge +4       4 B   🛑 NEW — the cave only ever tests r6
????        subr  r0,r7               2 B   🛑 NEW — the cave only ever negates r6   r7 = |iVar6|
6032 ae05   cmp 0x0,r6 / bge +4       4 B   flown cave +0x04/+0x06
8031        subr  r0,r6               2 B   flown cave +0x08                     r6 = |REQUEST|
e639        cmp   r6,r7               2 B   HONDA @0x1BD96      flags = |iVar6| − |REQUEST|
xx3a        mov   imm,r7              2 B
ae05        bge   +4                  2 B                       taken iff |iVar6| >= |REQUEST|
003a        mov   0x0,r7              2 B
                                     ====
                                     40 B   + 14 B pass merge (it is a comparator ⇒ owns a pass)
```

- Replacing V98's b5 comparator + its pass (32 + 14 = 46 B) ⇒ **net +8 B**, cave 154 → **162 B (13.4 %)**.
- Added on top of everything ⇒ **+54 B**, cave 154 → **208 B (17.2 %)**.
- 🛑 **FIVE new instruction encodings** (`sub r6,r7`, `add r6,r7`, `cmp 0x0,r7`, `bge` after an r7
  test, `subr r0,r7`). The kit's own rule — *"a raw byte hit is NOT a twin; ~1 in 6 of the scan's
  candidates was not at an instruction boundary at all"* — means each needs a **Ghidra-certified
  address inside a defined function, byte-identical between stock and the base image.** That is real
  work, and it is the honest reason Q2 is more expensive than its 40-byte count suggests.
- ⚠ The polarity is the **converse** of the brief's (`|iVar6| ≥ |REQUEST|`, not `|REQUEST| ≥ |iVar6|`)
  — chosen so the flown `cmp r6,r7` twin is reused. The two are complements; relabel, do not re-encode.

### 6.6 🛑 THE CHEAPER ROUTE THAT MAY MAKE Q2 UNNECESSARY

`gp-0x6b70 = sign(iVar6) × LERP(|iVar6| × 0xC63AE / 1024)`, and the Stage-2 LERP is **100 %
flash-derived with a runtime rescale that is the IDENTITY** (`gp-0x6982`/`gp-0x6984` have zero
writers image-wide and boot to 1024), **monotone non-decreasing by code at three ungated sites**,
and therefore **invertible**. The kit has already inverted it once (route 80: `|gp-0x6b70|` p50 320
→ `|iVar6|` 126–136).

⇒ **`|iVar6|` is ALREADY MEASURED, at 100 Hz, on CAN 427, on every build since V96.** What is *not*
measured is `|gp-0x6bfa|` — the REQUEST arm. So the comparator's purpose can be served by a
**single-operand magnitude ladder on `gp-0x6bfa`** and an off-car inversion of 427, at a fraction of
the cost — **at the price of 427's `sar 0x6` quantisation (÷64) and the ~10 ms CAN join.** For a
*duty* statistic the in-cave comparator is strictly better; for a *distribution* the 427 inversion
is already free. **This is a genuine fork and I flag it rather than resolving it.**

---

## 7. RECOMMENDATION

**Q1 (`gp-0x6ad6`) over Q2 (`iVar6`), decisively.** Reasons, in order:

1. **Q1 costs −8 B; Q2 costs +8 B and five new instruction encodings.** Q1 makes the cave *smaller*
   than what is on the car.
2. **Q1 has ZERO sampling skew** (a committed cell); Q2 has a bounded but real skew that is only
   acceptable hands-ON.
3. **Q1's null is decisive in BOTH directions.** Q2's null (`|iVar6| ≥ |REQUEST|` always) tells you
   the ranking of two arms — informative, but it does not decide any lever.
4. **Q1 decides the meaning of every lever the kit has flown since V89**, including the two whose
   nulls are currently unexplained, and including `0xC63AE` — the *only* candidate that clears the
   perceptual floor and which `HANDOFF §8` already says **must FOLLOW this rung, not precede it,
   because raising `gp-0x6b70` pushes toward this very clamp.**
5. **`|iVar6|` is already on the wire** via the 427 inversion (§6.6); `gp-0x6ad6` never has been.

**The shape of V100:** RUNG A (`|gp-0x6ad6| ≥ cal 0xC6200`, PASS 1, seeds `r7`) + RUNG C
(`|gp-0x6ad6| ≥ |gp-0x6b70|`, PASS 2, seeds `r7`, the scale-free positive control) + RUNG B
(`gp-0x6ad6 < 0`, PASS 2, `add`) + carry V98's b6 and b7. Drop b5, b4, b3 — all three spent.
**190 B, 15.7 % of the extent, store set and register set and branch set all unchanged.**
Identity must come from a separate `0x18F` field, per `HANDOFF §8.3` — `0x14A` byte7[7:6] is burned.

---

## 8. OPEN — exactly what would close each

| # | open | exact next step |
|---|---|---|
| 1 | Can the 100 Hz `0x14A` builder preempt a partial 1 kHz pass? Decides whether Q2's skew is 0 or ≤1 tick. | Read the INTC priority registers for the two task vectors from the boot init, against `svd_for_ghidra/UPD70F3508_V850E2Px4.svd`. |
| 2 | 🛑 **BLOCKING FLAG — `0xC6200` MUST NOT BE EDITED BY ANY FUTURE BUILD UNTIL `0x39ff6` IS CHASED.** `0x39ff6` is the 15th reader of `0xC6200`, inside `FUN_00039702`, and it is the one reader of the fifteen whose role is unknown. **V100 is unaffected: it READS `0xC6200` and changes zero calibration bytes**, so an unchased reader cannot affect this build's correctness. The flag binds only a build that proposes *moving* the cell — and moving it is a live temptation, because the cell now has **four** known roles in the same loop (friction lane · `gp-0x6b70`'s clamp · LERP `Y[9]` · **the PID's reference clamp**), so an edit intended for one hits all four plus this unknown fifth. | `decompile_function(0x39702)`, then a reader-role write-up. Orchestrator-directed, 2026-08-13. |
| 3 | The `±10240` error clamp at `0x3a7d0` is a SECOND, independent zero-authority mechanism and is not instrumented by RUNG A. | A fourth rung, ~34 B + its own pass. Named, priced, not designed. |
| 4 | `gp-0x6b4a`'s actual reachable magnitude in the symptom regime. | It is 32 % of its clamp away from railing the reference. RUNG A measures the *consequence* directly, which is why I did not chase the cause. |

---

# ADDENDUM — the second saturation, and the identity field (follow-ups 1 and 2)

## A1. ⭐ THE SECOND CLAMP CAN BE MEASURED WITHOUT COMPUTING THE FIRST

Naively, detecting `|gp-0x4f60 − clamp(gp-0x6ad6, ±8192)| ≥ 10240` needs the clamp reproduced in the
cave — ~50 B in a 2-register cave. **It does not.** Define

```
C1  = ( |gp-0x6ad6| >= cal(0xC6200) )                 # RUNG A  — the reference clamp
C2  = ( |gp-0x4f60 − clamp(gp-0x6ad6,±8192)| >= 10240 )   # the TRUE error-clamp predicate
C2' = ( |gp-0x4f60 −       gp-0x6ad6       | >= 10240 )   # RUNG D' — no clamp computed
```

When `C1 = 0`, `clamp(REF,±8192) ≡ REF`, so **`C2' ≡ C2` identically**. When `C1 = 1`, marginal
authority is already zero from the reference clamp, so `C2` is not needed. Hence

> **`marginal authority is exactly zero` ⟺ `C1 ∨ C2'`, with NO approximation,**
> **and `C2' ≡ C2` on exactly the frames where the attribution matters.**

Verified exhaustively over the full reachable `(REF, T)` grid — **0 mismatches**.

**⇒ THE TWO DUTIES ARE SEPARABLE, and this is the answer to "can I tell them apart, not get their OR".**
Both bits are transmitted as **separate CAN bits**, so the per-frame 2×2 joint is observable exactly
as V98's `(b6,b5)` table was:

| read-out | meaning |
|---|---|
| `d(C1)` | the reference clamp's duty — **exact, unconditional** |
| **`d(C2' \| C1 = 0)`** | ⭐ the error clamp's TRUE duty — **exact** |
| `d(C1 ∨ C2')` | the composite "Path-2 authority is zero" duty — **exact** |
| `d(C2')` unconditioned | 🛑 **NOT the error clamp's duty** — on `C1=1` frames `C2'` is uninterpreted. **Never quote it.** |

## A2. RUNG D' — 30 BYTES, in the r6/r7 orientation that reuses the flown idioms

```
2437 a0b0   ld.h  -0x4f60[gp],r6     4 B   VERBATIM Honda @0x4E452/@0x55624/@0x69C12/@0x815C2
243f 2a95   ld.h  -0x6ad6[gp],r7     4 B   VERBATIM Honda @0x3A798  (the PID's OWN read)
a731        sub   r7,r6              2 B   Ghidra-certified @0x4333E (FUN_00042af8, the shaper), +9 more
6032 / ae05 / 8031  abs into r6      6 B   flown cave +0x04/+0x06/+0x08, byte-identical
0638        mov   r6,r7              2 B   Honda @0x14EEE                     r7 = |err_pre|
2036 0028   movea 0x2800,r0,r6       4 B   hw1 Honda @0x27798 · hw2 Honda @0x3A7D6   r6 = 10240
e639        cmp   r6,r7              2 B   Honda @0x1BD96      flags = |err_pre| − 10240
043a / ae05 / 003a  materialise      6 B   flown cave
                                    ====
                                     30 B
```
⚠ **Boundary footnote, from the assembly not the decompile:** `0x3a7d0 addi -0x2800,r8,r0` + `bgt`
rails high iff `err_pre > 10240`; `0x3a7da addi 0x2800,r8,r0` + `cmovle` rails low iff
`err_pre ≤ −10240`. RUNG D' fires on `≥ 10240` both ways, so it over-counts by the **single value
`err_pre = +10240`**. Negligible for a duty; recorded so nobody rediscovers it as a bug.

## A3. THE IDENTITY PROBLEM DISSOLVES — a 4-bit SINGLE-FRAME field for 4 BYTES, no new hook

`0x14A` byte 4 bits **7:3 = 5 bits** are ours (`andi` masks preserve Honda's 2:0); byte 7 bits
**7:6 = 2 bits** (mask `0x3F`). **Seven bits total.** Dropping V98's spent `b5`/`b4`/`b3` frees three.

**The trick: an identity bit costs nothing structurally — it is an EXISTING rung with its guard
DELETED.** V98's `b4` rung is `ld.w`/`sar`/`cmp`/`bge`/`add 0x1,r7` (12 B); delete the first four
instructions and keep `add 0x1,r7` (2 B) — the bit becomes an unconditional constant. Same for `b3`
(`add 0x8,r7`). **No new encoding, no new store, no new hook — it is a REMOVAL.** And it drops `bnh`
from the cave's branch set, making V100's branch set a strict **subset** of what has flown.

⇒ **IDENTITY = byte7[7:6] ⊕ byte4 b4 ⊕ byte4 b3 = 4 bits = 16 codes, SINGLE-FRAME**, for **4 bytes**.
That is 4× the generations of `0x18F`'s proposal at ~1/40th the risk, and it retires V99's
duty-based identity regression.

**🛑 AND `0x18F` IS THE WRONG HOME EVEN IF A HOOK WERE FREE.** `memory/accord-0x18f-payload-one-frame-stale`
is a **measured permanent instrument calibration** (route 67, V81): `0x18F`'s payload is **≈9.9 ms —
exactly one 100 Hz frame — stale relative to `0x14A`'s**. An identity field on `0x18F` would be one
frame out of step with the measurands it identifies. **That is verbatim the `raw14` off-by-one
pairing-bug class** (`accord-raw14-offbyone-in-every-cache`) which this kit has already shipped in
all 13 caches. Separately, `0x18F` has its own TX buffer — the proven hook writes `gp-0x1514` /
`gp-0x1511` inside the 8-byte `0x14A` buffer at `gp-0x1518` (the checksum call at `0x55C18` is
`FUN_00057b24(gp-0x1518, 8, 0x14a)`), so reaching `0x18F` means **a new store to a new cell = a new
GATE 1 claim + a grown store set**, on the only class of change that has ever bricked this ECU.
**RECOMMENDATION: do not open `0x18F`. Ever, for identity.**

## A4. THE RECOMMENDED V100 PAYLOAD — 124 B, SMALLER THAN WHAT IS ON THE CAR

| `0x14A` bit | measurand | rung | bytes |
|---|---|---|---|
| byte4 **b5** | ⭐ `\|gp-0x6ad6\| ≥ cal(0xC6200)` — **reference clamp active** | comparator, PASS 1 seed | 24 |
| byte4 **b7** | `gp-0x6ad6 < 0` — sign / **positive control** | single-operand, PASS 1 | 10 |
| byte4 **b6** | ⭐ `\|gp-0x4f60 − gp-0x6ad6\| ≥ 10240` — **error clamp active** (exact given b5) | comparator, PASS 2 seed | 30 |
| byte4 **b4** | IDENTITY bit 0 | unconditional `add 0x1,r7` | 2 |
| byte4 **b3** | IDENTITY bit 1 | unconditional `add 0x8,r7` | 2 |
| byte7 **[7:6]** | IDENTITY bits 3:2 | V98's constant block, unchanged | 18 |

```
PASS1   50 B     (RUNG A 24 + sign 10 + shl/merge 16)   andi 0x5f -> clears b7,b5
PASS2   50 B     (RUNG D' 30 + 2 ID bits 4 + shl/merge 16)  andi 0xa7 -> clears b6,b4,b3
BYTE7   18 B     unchanged from V98
RET      6 B
TOTAL  124 B     vs V98's 154 B  =  −30 B  =  10.2 % of the 1212 B extent
```
- **STORE SET IDENTICAL TO THE FLOWN ONE: 3 stores, 2 cells (`gp-0x1514` ×2, `gp-0x1511` ×1).** No growth.
- **Registers r6/r7 only. Branch set `{bge}` — a strict subset of V98's `{bge, bnh}`.**
- **Six new byte groups, four of them VERBATIM Honda instructions Ghidra certifies inside defined
  functions**; the other two assembled hw1+hw2 from certified halves, which is V98's own method.
- **Zero calibration bytes. Zero code edits outside the cave. GATE 2 not applicable.**

**Bits dropped and why:** `b6` MODEL-vs-ACTUAL — **answered by V98** (0.4235, r = −0.321, p = 0.0050);
re-measuring costs a whole extra pass (+46 B, +1 store) and buys replication this decision does not
need. `b7` `gp-0x6b70 < 0` — **redundant with CAN 427**, which carries `gp-0x6b70` sign and magnitude
at 100 Hz on every build since V96. `b3` polarity — **spent** (`sign(gp-0x6752) = −1` constant over
17,983 frames).

**Why the SIGN rung is the right positive control** (cheaper than the `|6ad6| ≥ |6b70|` share rung and
strictly better as a control): it is the only channel that can be validated **against an external
signal we already have** — `gp-0x6ad6` is dominated by `−gp-0x6b4a`, the LKAS demand path, so its
sign duty must track openpilot's own commanded sign. 🛑 It also catches the one failure the other two
rungs cannot: **if `gp-0x6ad6 ≡ 0`, RUNG A reads 0.0000 and the sign rung reads 0.0000, while RUNG D'
degenerates into a pure driver-torque statistic that would still look "live".** Without the sign
rung, that failure mode is invisible.

## A5. 🛑 ZERO SPARE BITS — the arbitration the orchestrator has to make

The 124 B design uses **all five** byte4 bits (3 measurands + 2 identity). **Any additional rung —
including any φ / Path-share rung `tracer-c63ae` proposes — collides immediately.** The trade, priced:

| option | identity | measurands | bytes | stores |
|---|---|---|---|---|
| **A (recommended)** | **4 bits, 16 codes** | 3 | **124** | **3 (flown set)** |
| B — add ONE single-operand rung | 3 bits, 8 codes | 4 | ~134 | 3 (flown set) |
| C — add ONE comparator (e.g. `\|gp-0x6ad6\| ≥ \|gp-0x6b70\|`, the Path-2 share) | 3 bits, 8 codes | 4 | **~168** | 🛑 **4 — GROWS THE STORE COUNT** |
| D — identity on byte7 only | **2 bits, all 4 codes BURNED** | 5 | — | — **not acceptable** |

⇒ **A φ rung costs either an identity bit or a measurand, and if it is a comparator it also costs a
fourth store.** Byte-space is not the constraint (10 % of the extent used); **bits are.** My
recommendation is **A**, with **B** as the fallback if a single-operand φ rung exists — a *comparator*
φ rung (option C) should be weighed against growing a store set that has flown five routes clean.

---

## 9. RECORD CORRECTIONS PROPOSED (reports, not edits)

1. `BUILD-LINEAGE.md:490` — `0xC6200`'s "3 still unidentified readers" are `0x3a7a2`/`0x3a7b2`/
   `0x3a7c4`, the PID's clamp on `gp-0x6ad6`. **RULE 11 census complete.** And the cell's
   description should stop saying "gp-0x6b70's clamp" — it is **four** things.
2. `path2-authority`'s `d(gp-0x6b94)/d(gp-0x6b70) = 0.2565` is the **UNSATURATED** derivative and must
   carry the condition `|gp-0x6ad6| < 8192`.
3. `gp-0x6b4a` is **shadow-lockstep protected at `gp-0x4cd2`** — new to the record, same class as
   `gp-0x6bfa`/`gp-0x4cfa`.
