# ADVERSARIAL PASS — V292, SURFACE A: ARITHMETIC

**Agent `advA2`, subagent of `main`, 2026-09-13. Adversarial: the job was to make V292 FAIL.**

**TOP-LINE VERDICT: PASS.** No arithmetic defect found that would justify withholding the flash.
One **reported defect in the pre-registered telemetry READ** (§5.1) — it changes what the operator
should be told to expect, not whether the image is safe to flash.

**Image under attack:** `_v292_…_plain_image.bin`, sha256
`d1128232993d3a1dcfa4afecb279976f014e6c940f36d88b87db9f2aee3aef33`.
Base V291 `a66f9c54b21031d3948cf1f60fbcadc6ac44d422c01d5a357b19aa0d23144657`;
V282 `0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe`.

**Method.** Every number below is re-derived from the image bytes. I built my own V850E2 decoder from
the ISA field layout (`scratchpad/advA2/dec.py`) and my own integer mirror from the decoded semantics
(`scratchpad/advA2/mirror.py`); neither reads `build_v292_tva.py`, the design's constants, or the
design's Python. Ghidra was used as an independent second method on a fresh import
(`/advA2/…v292…`, `auto_analyze:false`, `dry_run:true` only, nothing saved). Every scan was
positively controlled before its null was trusted; one of mine **failed** its control and is reported
as unverified rather than as a null (§4.2).

---

## 1. Scorecard against the pre-registration, surface A

| | criterion | verdict |
|---|---|---|
| **A1** | mean gain `b/1024`, mean decay `a/1024`, remainders bounded, realised DC | ✅ **PASS** (one scope defect in the criterion itself — §2.4) |
| **A2** | int32 overflow, narrowing stores, register/flag restoration | ✅ **PASS** |
| **A3** | describing-function gain at 20.3 Hz within 1.00 ± 0.03 | ✅ **PASS**, worst error **0.0009** |
| **A4** | r24 lane + b3 rung byte-identical to V291 and still correct | ✅ **PASS** |
| **A5** | displaced instructions replicated, return point, cycle cost ≤ 2× V289 | ✅ **PASS** |

---

## 2. A1 — exactness

Cal constants **read from the image**, at the tp-relative addresses the decoded loads name
(`tp = 0xBF000`): `a = [0xC63E8] = 962` (`ld.h`, sign-extended), `b = [0xC63EA] = 958` (`ld.hu`,
zero-extended), clamp `= [0xC62E6] = 46080`. Linear DC `2b/(1024−a) = 958/31 = 30.903225806`.

### 2.1 The residue identity — **EVIDENCE**

`andi 0x3ff` is exactly the residue of `sar 0xa` for two's-complement `t` of either sign:
`t == ((t >> 10) << 10) + (t & 0x3FF)` and `0 ≤ (t & 0x3FF) ≤ 1023`.
**160,001 values tested, including both int32 extremes and the reachable product bounds: 0 violations.**

### 2.2 The per-tick telescoping identity — **EVIDENCE**

The claim reduces to an exact local identity:

```
1024*s[n] = a*s[n-1] + b*x[n] + (ra[n-1]-ra[n]) + (rb[n-1]-rb[n])
```

Hold that at every tick and the sum telescopes, so `mean(s) → b*x/(1024-a)` and
`mean(out) = 2*mean(s)` exactly; over a periodic orbit the boundary terms cancel identically.

**Every constant `x` in −12000…−1 and 1…12000 (24,000 amplitudes) × 400 ticks = 9,600,000 ticks:
0 identity violations, 0 int32 excursions, max remainder 1022.**

### 2.3 Exact rational mean over the detected periodic orbit — **EVIDENCE**

Orbits found by state-tuple `(s, rb, ra)` cycle detection; the mean over one full cycle taken as an
exact `Fraction`, not a float.

| x | period | mean(out)/x, exact | = 958/31? |
|---|---|---|---|
| 1 | 15872 | 30.903225806 | **yes** |
| −1 | 15872 | 30.903225806 | **yes** |
| 3 | 15872 | 30.903225806 | **yes** |
| 24 | 1984 | 30.903225806 | **yes** |
| 1491 | 15872 | 30.903225806 | **yes** |
| 12000 | 496 | 30.903225806 | **yes** |
| −12000 | 496 | 30.903225806 | **yes** |

**Zero exactness failures at every x tested, both signs.**

### 2.4 The realised DC above |x| = 1491 — a **scope defect in A1 as written**

A1 says "the realised DC differs from 30.903 by more than 0.1 % at any amplitude from 1 count up."
The **state** is exact at every x. The **output** is not, above `|x| = C(1024−a)/(2b) = 1491.1`,
because the pre-existing `±46080` clamp binds. Measured mean(out)/x:

| x | V292 | V291 | V282 |
|---|---|---|---|
| 1400 | 30.903 | 30.863 | 30.866 |
| 1600 | 28.800 | 28.800 | 28.800 |
| 12000 | 3.840 | 3.840 | 3.840 |

**The three builds sit on the rail identically.** This is Honda's clamp, not the cave, and
`st.w r9,-0x3d30[gp]` @`0x28FA8` executes **before** the clamp code at `0x28FAC`, so the state is
never clamped. **Scored PASS on the cave's own contribution.** The criterion should have said
"up to the output clamp".

### 2.5 The design's headline mechanism, reproduced independently — **EVIDENCE**

Zero-mean 20.3 Hz input, mean of `out` over 300 s:

| A | V292 | V291 | V282 |
|---|---|---|---|
| 1 | **0.000** | −32.667 | −16.174 |
| 3 | **0.000** | −31.210 | −19.062 |
| 8 | **0.000** | −32.241 | −20.249 |
| 64 | **0.000** | −32.933 | −20.202 |
| 512 | **0.000** | −32.437 | −19.902 |

My numbers match the design's quoted −32.67 / −31.21 / −32.24 / −32.93 / −32.44 to three decimals,
from an independent mirror. **V291's −32-count constant feedback offset is real and V292 removes it
exactly.**

---

## 3. A2 — overflow, width, registers, flags

### 3.1 `|x| ≤ 12000` is enforced, not assumed — **EVIDENCE**

Decoded from the image at `0x28F50`: `addi 0x2ee0,r7,r11` (`r11 = x + 12000`);
`addi 0xa23f,r11,r0` (adds −24001, result discarded, sets CY); `bnc 0x28F5E`; else `jr 0x290B0`.
Carry is set iff `(x+12000)` exceeds 24000 unsigned, so the filter runs **only** for
`−12000 ≤ x ≤ 12000`. The hook at `0x28F8E` is downstream of this bail.

### 3.2 Reachable bounds — **EVIDENCE**

| quantity | worst measured | int32 margin |
|---|---|---|
| `\|s\|` | 185,420 (constant ±12000; analytic fixed point 185,419.4) | — |
| `a·s + rem_a` | 178,374,424 | **×12.04** |
| `b·x + rem_b` | 11,496,960 | **×186.8** |
| `s_old + s_new` | 123,619 | **×17,372** |

Swept over constant ±12000, square waves at periods 2/20/200, random ±12000 and random uniform,
40,000 ticks each. **Zero 32-bit wraps across every run in this report.**

**The cave's added exposure is exactly +1023 per product.** The `|s|` at which `a·s` overflows moves
from 2,232,311 (V291) to 2,232,310 (V292) — the safe window narrows by **1.00 count of s out of
2.23 million**, i.e. 0.000045 %.

### 3.3 No narrowing store — **EVIDENCE**

`st.h` at `0xC4C12`/`0xC4C22` stores `r13` **after** `andi 0x3ff`, so `r13 ∈ [0,1023] ⊂ [0,65535]`.
**Lossless by construction, not by bound.** `st.w r9,-0x3d30` stores a 32-bit state into a 32-bit
cell. Both remainder cells are halfword-aligned (`0xFEDF128C`, `0xFEDF128E`).

The design's choice of `ld.hu` over `ld.h` is the safer one and it matters only for garbage: `ld.hu`
caps a garbage cell at +65535, `ld.h` would admit −32768. Neither overflows; `ld.hu` never admits a
negative remainder. **Not a defect either way.**

### 3.4 Registers — the cave's write set is **identical** to the span it replaces — **EVIDENCE**

| | set |
|---|---|
| stock `0x28F8E…0x28FA1` writes | `{r7, r9, r13, r14}` |
| V292 cave writes | `{r7, r9, r13, r14}` |
| **new clobbers** | **EMPTY** |
| stock upward-exposed reads | `{gp, tp, r7, r9, r16, r26}` |
| cave upward-exposed reads | `{gp, tp, r7, r9, r16, r26}` |
| **new liveness claims** | **EMPTY** |

`r13` is **not** upward-exposed: `0xC4C08`/`0xC4C18` write it before `0xC4C0C`/`0xC4C1C` read it.
The cave restores `r13` and `r14` to the clamp value with the two replicated `ld.hu` before
returning; both are read downstream (`cmp r13,r26` @`0x28FA6`; `mov r14,r26` @`0x28FAE`,
`subr r0,r14` @`0x28FB2`, `cmp r14,r26` @`0x28FB4`). `r26` is read-only to the cave's second `mul`,
so the two-sample sum `add r9,r26` @`0x28FA4` is undisturbed.

**The r13/r14 reload ordering differs from Honda's** (Honda interleaves them with the `sar`s; the
cave does both `sar`s first). No instruction between them reads `r13`/`r14`, so the reorder is inert.

### 3.5 Flags — **EVIDENCE**

Last flag-setting instruction before the return is `sar 0xa,r9` in **both** the stock path
(`0x28FA0`) and the cave (`0xC4C26`); the two `ld.hu` after it set none. The values differ (the cave's
operand carries `rem_a`), but the first consumer is `ble` @`0x28FAC`, armed by `cmp r13,r26`
@`0x28FA6`, with `add`/`add`/`cmp` overwriting the flags in between. **Dead.**

### 3.6 Boot / stale garbage in the remainders — **EVIDENCE**

`.data` initialiser maps `0xFEDF11B0 →` flash `0x86260`. `rem_b`'s source is flash `0x8633C = 00 00`,
`rem_a`'s `0x8633E = 00 00`; the **whole 72-byte free run's source is 72 zero bytes**.
Anchor control: `gp−0x6AB0`'s source at flash `0x86600` reads `88 02 88 02`, the known non-zero cell —
so the mapping is right. **Both cells boot to exactly 0.**

Even if they did not: `andi 0x3ff` forces `[0,1023]` on the **first** tick unconditionally.

| rb₀, ra₀ | ticks to heal | worst \|out − clean\| |
|---|---|---|
| 65535, 65535 | **1** | 248 counts of a ±46,080 range |
| 40000, 12345 | **1** | 99 |
| 1024, 1024 | **1** | 4 |

**One tick, bounded, self-healing by construction.**

### 3.7 The bail path — **EVIDENCE**

On a bail the cave does not execute, so the remainders are frozen. The sentinel path
(`ld.bu -0x3d2c,gp,r9` @`0x28F66`; `cmp 1,r9`; `bnz 0x28F82`; `mov 0,r26` @`0x28F84`) makes the next
tick read `s_old = 0`, so `t_a = 0·a + rem_a = rem_a`. For `rem_a ∈ [0,1023]` — the only reachable
range after one cave tick — `step_a = 0` and `rem_a` is unchanged: **inert**.

Swept `rb₀` over `[0,1023]` and `x` over ±12000: **max |V292 out − V291 out| on the first post-bail
tick = 1 count.** No stale remainder can produce a wrong first tick.

---

## 4. A5 — displacement, return, timing; and the span

### 4.1 Replication and return — **EVIDENCE, my decoder and Ghidra agreeing instruction-for-instruction**

Hook `0x28F8E`: `89 07 72 bc` = `jr 0xC4C00`, disp22 `+0x9BC72`. 4 bytes replacing the 4-byte
`mul r16,r7,r0` — the instruction boundary at `0x28F92` is preserved.

All **six** displaced instructions are replicated **byte-identically** (a permutation, not a rewrite):

| displaced | bytes | cave |
|---|---|---|
| `0x28F8E mul r16,r7,r0` | `f03f2002` | `0xC4C00` |
| `0x28F92 mul r26,r9,r0` | `fa4f2002` | `0xC4C04` |
| `0x28F96 ld.hu 0x72e6,tp,r13` | `e56fe772` | `0xC4C28` |
| `0x28F9A sar 0xa,r7` | `aa3a` | `0xC4C16` |
| `0x28F9C ld.hu 0x72e6,tp,r14` | `e577e772` | `0xC4C2C` |
| `0x28FA0 sar 0xa,r9` | `aa4a` | `0xC4C26` |

Return `0xC4C30`: `b6 07 72 43` = `jr 0x28FA2`, disp22 `−0x9BC8E` — **exactly the instruction after
the last displaced one**, Honda's own `add r7,r9`. Both displacements are well inside the ±2 MB
disp22 range.

The eight non-replica instructions are the error feedback: `ld.hu −0x6d74/−0x6d72`, `add r13,r7/r9`,
`andi 0x3ff`, `st.h`.

### 4.2 Nothing branches into the orphaned span `[0x28F92, 0x28FA2)` — **EVIDENCE, both methods**

- **My raw-Python scan** over `[0x13000, 0xC5000)`: Format-V (`hw1[10:6] == 0x1E`, `hw2` bit 0 = 0 to
  exclude the 6-byte load) and Format-III `Bcond` — 2,732 + 23,085 distinct targets, 25,519 combined.
  **Positive controls 17/17 PASS**, including all four bails into `0x290B0`, the `jarl 0x28EA6` from
  `0x22522`, nine `Bcond` targets inside the filter block, two engagement skips, **and both of V292's
  own new jumps**. Result: **0 targets inside the span**; `0x28FA2` is targeted **only** from
  `0xC4C30`.
- **Ghidra** `get_bulk_xrefs` on all 11 half-word addresses of the span (analysed `code.bin`):
  **empty for every one.** Controlled: the same call returns all four jumps into `0x290B0`, the
  conditional into `0x28F4C`, both into `0x28FBE`, and the call into `0x28EA6`.
- **Absolute LE32 pointers** into `[0x28F80, 0x28FB0]` at any byte alignment, whole file: **NONE.**
  Controlled — the same scanner finds the `imm32 0xCB844` at `0x28FCE`.

The 16 orphaned bytes are byte-identical to stock and unreachable. Wasted space, no hazard.

⚠ **Residual, stated as such:** a computed jump through a table of *offsets* (rather than absolute
pointers) cannot be excluded by any of these three methods. The span is mid-block in an ordinary
straight-line function and the property is inherited unchanged from stock, so I judge this negligible —
but it is **BELIEF**, not evidence.

### 4.3 Timing — **EVIDENCE (counts) + BELIEF (cycles)**

| | instructions | net delta | duty |
|---|---|---|---|
| V289 notch cave (entry `0xC4C00`, `jr 0x2A178` @`0xC4C88`) | **52** (140 B) | **+52** | engaged path only |
| V292 EF cave | **15** (52 B) | **+10** | every tick |

**V292's net is 0.19× of the V289 cave that already flew on r62/r63.** A5's "≤ 2×" is met with a
×10 margin even before duty is considered.

Conservative cycle estimate (loads 3, `mul` 2, branches 4, ALU 1): cave ≈ 32 cycles vs 12 for the
displaced span, **net ≈ +20 cycles per 1 ms tick** — under 0.03 % of the tick at any plausible core
clock. **BELIEF:** I did not verify the core clock or the flash wait states, so treat the cycle
figure as an estimate and the instruction count as the evidence.

### 4.4 Flash region and CRC

`0xC4C00…0xC4C33` was **0xFF on both V282 and V291** (verified). 40 bytes of `0xFF` separate it from
the 0x14A cave's end at `0xC4BD8`; 956 bytes of `0xFF` remain above it. The pre-existing 12-byte
structure at `0xC4FF0` is untouched.

| block | trailer | V292 stored | computed | |
|---|---|---|---|---|
| `[0x13000, 0xC4FFC)` | `0xC4FFC` | `2c434e58` | `2c434e58` | ✔ owns both the hook and the cave |
| `[0xC6000, 0xC6FFC)` | `0xC6FFC` | `ed9b12bb` | `ed9b12bb` | ✔ **byte-identical to V291** — no cal edit |

### 4.5 The remainder cells are unowned — **EVIDENCE, both methods, both encoding forms**

Free run `gp−0x6D74 … gp−0x6D2D` = `0xFEDF128C…0xFEDF12D3`.

- **Python, 4-byte forms** (all eight load/store widths, with the `ld.bu` hw1-bit-5 parity rule and
  the `hw2` bit-0 load/branch discriminator): 10,691 sites and 2,601 distinct gp displacements
  image-wide. Inside the run, **with the cave excluded: ZERO**. Self-control: with the cave
  *included* it finds exactly the cave's own two accesses.
- **Ghidra `search_instructions`**, 184,512 instructions scanned, `truncated:false`, prefixes
  `-0x6d3`/`-0x6d4`/`-0x6d5`/`-0x6d6`: **0 matches each**. `-0x6d7` returns 17, all at `-0x6d78`
  /`-0x6d7c` (below the run); `-0x6d2` returns 21, lowest at `-0x6d2c` (above it).
  **Control for the 6-byte extended-displacement form: PASS** — `-0x4c2d` returns four length-6
  instances at `0x48E5C…0x48E8E` alongside the 4-byte ones, so this scanner does see that form.
- **Absolute LE32 pointers** into the run, any alignment: **NONE** (scanner controlled on `0xCB844`).
- **The region is live, writable RAM, not a hole**: `st.w` sites exist immediately below
  (`gp−0x6d78` @`0x197CA`, `gp−0x6d7c` @`0x21D40`) and immediately above (`gp−0x6d2c` @`0x400AC`,
  `st.h gp−0x6d24` @`0x54478`). Both methods agree on every neighbour.

🛑 **One scan of mine FAILED its positive control and its null is NOT reported.** My hand-rolled
6-byte extended-displacement decoder read `0x48E56` as disp `−13,548,827` when Ghidra reads
`ld.b -0x6752, gp, r8`. I discarded it and substituted the Ghidra sweep above, which is controlled on
that exact form. Recording it because the alternative was a confident empty answer.

---

## 5. Findings the pre-registration did not anticipate

### 5.1 🛑 **The pre-registered b3 telemetry read does not transfer from V291 to V292**

**REPORTED DEFECT — in the READ handed to the operator, not in the image. Not a DO-NOT-FLASH.**

The rung, decoded from the V292 image at `0xC4BA8`:
`ld.w -0x3d30,gp,r6 ; cmp 0x0,r6 ; bge +4 ; add 0x8,r7` ⇒ **b3 = 1 iff the fb filter state `s` < 0**.
It reads `gp−0x3d30` — **the exact state the cave changes**.

The pre-registration's PASS-license hands the operator *"b3 transition rate ×0.785 of the V282-pole
mirror"*. That number was computed on **V291**, whose filter has an **absorbing negative zone**: once
`s` goes negative it sticks in `[−16,−1]` forever. V292 removes that zone — which is the point of the
build — and the b3 statistics move with it.

Measured, b3 sampled at 100 Hz, 200 s per case, transition rate as a ratio to the V282-pole mirror:

| excitation | V291 / V282-pole | **V292 / V282-pole** |
|---|---|---|
| 20.3 Hz sine, A = 1 | 0.00 (frozen) | **1.00** |
| 20.3 Hz sine, A = 3 | 0.99 | **1.00** |
| LP noise sd ≈ 3 | **0.05** | **1.15** |
| LP noise sd ≈ 9 | 0.64 | **0.86** |
| LP noise sd ≈ 24 | **0.78** ← the quoted ×0.785 | **0.83** |

The ×0.785 reproduces only at the **largest** excitation. One step down it is wrong by 35 %, and at
1–3 count amplitudes — the regime this whole build targets — V291 reads ×0.05 and V292 ×1.15, a
factor of **23**. Handing the operator ×0.785 invites him to read a correct V292 as a failed one.

⭐ **The fix is free and makes the build *more* readable: hand over the b3 DUTY, not the transition
rate.** Measured duty (fraction of samples with `s < 0`):

| A (20.3 Hz) | V292 | V291 | V282-pole |
|---|---|---|---|
| 1 | **0.469** | 1.000 | 0.699 |
| 2 | **0.487** | 1.000 | 0.615 |
| 3 | **0.493** | 0.800 | 0.594 |
| 5 | **0.497** | 0.651 | 0.560 |
| 8 | **0.499** | 0.594 | 0.540 |

**V292 sits at 0.47–0.50 at every amplitude** — sign-symmetric, exactly as the linear model says it
must be — while V291 is pinned at 1.000 below A = 3 and V282-pole runs 0.54–0.70. That is a clean,
amplitude-independent, one-drive positive control that **only V292 can produce**, and it is what
design §6 was reaching for. Recommend amending the handed read before the drive.

### 5.2 The negative absorbing zone is `[−16, −1]`, not `{−1}`

The design's headline says "the `s = −1` absorbing state". Measured on V291 from several starting
states with zero input for 400 ticks: `s₀ = −1 → −1`, `−2 → −2`, `−16 → −16`, `−31 → −16`,
`−62 → −16`, `−500 → −16`, `−5000 → −16`. The design's own `s₀ = −500` row says `−16`, so the
substance is right; the headline understates the zone's width. V292 reaches exactly 0 from every one
of them (17 ticks from −1, 110 from −500, 145 from −5000).

### 5.3 V292's decay tail is longer than V291's — correct, but worth saying out loud

Ticks to reach `s = 0` from a positive state with zero input: `s₀ = 16` → V291 16, **V292 53**;
`s₀ = 500` → V291 64, **V292 109**. V292's figure is the **linear** answer
(`ln(500)/−ln(962/1024) = 99.5` ticks); V291's floor was eating the tail. Not a defect — it is the
edit doing what it claims — but the feedback signal now decays *more slowly*, and anyone reading a
decay-time statistic off the wire should expect that direction.

### 5.4 V282's own integer bias is −16 to −20 counts, not a flat −20

§2.5 measures −16.17 at A = 1 rising to −20.37 at A = 16. The design quotes −20. The difference is
immaterial to V292 but it means V282's byte-exact reference is itself amplitude-dependent, which is
the same effect adversary B amended clause B4 for.

---

## 6. What a FAIL would have looked like, and why none of them fired

Written before the numbers were in: a single identity violation at any of 9.6 M ticks; a single
int32 wrap under `|x| ≤ 12000`; a describing-function gain outside ±0.03 at any tested amplitude; a
register in the cave's write set that the stock span did not already clobber; a return landing
anywhere but `0x28FA2`; a branch target inside the orphaned span; a remainder cell with a second
accessor; a cave cycle cost above 2× V289's. **Each was tested and each came back clean.** The pass
was structurally able to return DO-NOT-FLASH and did not.

**Scripts:** `scratchpad/advA2/{dec,mirror,scan_targets,a1_exact,a2_overflow,a3_df,a5_b3}.py`.
