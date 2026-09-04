# ADV284-A — ADVERSARIAL PASS: ARITHMETIC (V284)

**Agent:** `adv284A` (subagent, adversary). **Date:** 2026-09-04.
**Target:** `_v284_V284-V282BASE-KI0-KP.M8.SLOT7.512.IDX32.88-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`
sha256 `1b46f24f3ea0988a7786d4dd4cfc4db84bba2f41d44f3a2176386727828b74ff` — **re-hashed from disk, matches the brief.**

## VERDICT: **FLASH WITH ONE NAMED CAVEAT** (finding A1)

On my surface — the arithmetic — I could not break this build. Every value the builder claims reproduces
exactly from the image's own bytes through an emulator written from the disassembly. The one thing I did
break is a **safety-envelope claim in the docstring and two build-script assertions that are weaker than
the prose they are made to support** (finding A1) — a V274-class pattern, not an ECU defect.

---

## FAIL criteria, written down BEFORE the work

I would have returned **DO NOT FLASH** on any of:

1. **F1** — the emulated gain curve, read from the built image, disagrees with any pre-registered value.
2. **F2** — a zero divisor at `divq 0x29E2C`, a discontinuity at a knot, a curve that drops below 248,
   exceeds 512, or falls below the base at any index.
3. **F3** — `E*Kp` overflows 32 bits at any reachable `|E|` (the `mul r9,r8,r0` at `0x29E36` keeps only
   the low word; an overflow there flips the sign of the P term — an assist reversal).
4. **F4** — the demand index can go negative or exceed the range tabulated offline, so the offline table
   is not the table the car uses.
5. **F5** — the twin `FUN_0002a93a` is reachable and consumes the reshaped record with different arithmetic.
6. **F6** — any cell the build declares FROZEN reads differently on the built image.
7. **F7** — the stated safety envelope is false. (CAVEAT or FAIL by magnitude.)

**Result: F1–F6 all PASS. F7 FAILS as stated — downgraded to a caveat, reasoning in A1.**

---

## Method note

The V284 image differs from V282 at **exactly 12 bytes**, all in `0xE537C–0xE5382`, `0xE5388–0xE538B`
and the page trailer `0xE5FFC–0xE5FFF` (verified by a full `[0x13000,0x100000)` Python diff). The code
region is therefore **byte-identical** to V282, and I verified `0x29DC6–0x29E40` byte-for-byte between
the two images before using the V282 Ghidra program for disassembly. All *values* are read from the
**V284** file. GhidraMCP only, `dry_run:true` throughout; no database mutation, nothing saved.

---

## The LERP, re-derived from the image (EVIDENCE)

Decompiled `FUN_00028ea6` first for structure, then pinned the instructions. The consumer at
`0x29DC6–0x29E32`:

| addr | insn | meaning |
|---|---|---|
| `0x29DD0` | `sld.w 0x0,ep,ep` | `ep = *(0xCB994 + slot*4)` — record base, reached by **pointer walk** |
| `0x29DE8` | `zxh r7` | **idx zero-extended to 16 bits — cannot be negative** |
| `0x29DEA` | `cmp r9,r7` / `bh` | **unsigned** `idx > X[0]`, else -> `Y[0]` (rec+0x0C) |
| `0x29DF6` | `cmp r6,r7` / `bnc` | **unsigned** `idx >= X[4]` (rec+0x0A) -> `Y[4]` (rec+0x14) |
| `0x29DFA–0x29E12` | walk | `i` = smallest `i>=1` with `X[i] > idx`; Y-pointer advances in lockstep |
| `0x29E20` | `sub r13,r9` | `Y[i]-Y[i-1]`, **32-bit, correctly signed on a falling leg** |
| `0x29E26` | `mul r7,r9,r0` | 32x32, **high word discarded into r0** |
| `0x29E2C` | **`divq r6,r9,r0`** | **SIGNED divide, truncates toward zero** (not `divqu`) |
| `0x29E32` | `zxh r9` | result truncated to 16 bits |
| `0x29E36`/`0x29E3E` | `mul r9,r8,r0` / **`sar 0x8,r8`** | `P = arithmetic-shift(E*Kp, 8)` |

I re-derived the pointer walk independently and it agrees with the builder's `i` convention exactly
(including the `br 0x29E14` pre-loop path, which yields `i=1`).

**The builder's `kp_lerp()` is a faithful mirror. I found no semantic error in it.**

---

## Findings

### A1 — **the "stays inside gain that has already been on the car" claim is FALSE pointwise** [SUBSTANTIVE]

Docstring line 170 and build assertions at lines 513–516:

```python
check(max(cc) < max(stock_curve), "...this build stays inside gain that has already been on the car")
check(all(cc[i] <= max(stock_curve) for i in range(256)), "no index exceeds the stock LERP's peak")
```

Both compare V284's curve against the stock curve's **scalar peak (696)**. Neither compares it against
the stock curve **at the same index** — and gain that "has been on the car" is a *function of index*,
not a scalar. Read from the V280 rev 2 image (the build that actually flew on r32/r33/r34):

| idx | V282 (on car) | **V284** | flown stock (V280r2) | V284 / flown stock |
|---|---|---|---|---|
| 34 | 248 | 380 | 380 | 1.000 |
| **36** | 248 | **512** | **387** | **1.323** |
| 40 | 248 | 512 | 403 | 1.270 |
| 44 | 248 | 512 | 418 | 1.225 |
| 45 | 248 | 506 | 422 | 1.199 |
| 50 | 248 | 476 | 442 | 1.077 |
| 54 | 248 | 452 | 457 | 0.989 |
| 68 | 248 | 368 | 512 | 0.719 |

**V284 exceeds the flown stock LERP on idx 35–53 (19 indices), worst +125 counts / +32.3 % at idx 36.**
That band is not incidental — it is the **low half of the stall band the build is aiming at**.

Exposure, measured on the wire (r35–r38 `.npz`, `req` = STEER_REQUEST engaged, index by the kit's
`demand_idx()`, whose `|clamp(v>>6,±240)|` I confirmed independently against the decompile):

| route | engaged frames | idx 33–87 (gain changed) | idx 35–53 (**exceeds anything flown**) |
|---|---|---|---|
| r35 | 91,556 | 8.54 % | 3.91 % |
| r36 | 63,162 | 5.58 % | 3.09 % |
| r37 | 25,958 | 13.46 % | 6.34 % |
| r38 | 70,489 | 6.54 % | 3.27 % |
| **all** | **251,165** | **7.75 %** | **3.78 %** |

**Why this is a CAVEAT and not a block.** The *absolute* value 512 has flown (stock delivers it at
idx 68), every clamp is unchanged and verified, and the build's real safety argument — the A11.4 ring
return ratio of 0.949 — is **index-aware**, computed on the measured index distributions, so it does not
rest on the peak-vs-peak assertion. What is defective is the *justification*, not the delivered surface:
the two assertions cannot fail on the thing the prose claims, which is exactly the V274 failure mode.

**Recommended caveat wording:** *"V284 delivers up to 1.32x the Kp that any flown build delivered at the
same demand index, on idx 35–53, covering ~3.8 % of engaged frames. The peak value (512) has flown; the
pairing of that value with that index has not."*

### A2 — docstring arithmetic errors [MINOR, no image impact]

- Line 90: *"The 32->36 leg is 4 wide — **99** Kp counts per index step."* The true slope is
  **(512-248)/(36-32) = 66.00/idx.** The orchestrator's brief repeats the 99.
- Line 90: *"Honda's narrowest is **48** wide."* Censused across all 28 records on the V280 rev 2 image,
  **Honda's narrowest segment is 24** (the 112->136 leg, present on most slots). The width-4 segment is
  therefore **6x** narrower than Honda's narrowest, and its 66.00/idx slope is **12.4x** steeper than
  Honda's steepest (5.33/idx, slot 10). The docstring's own "outside Honda's design envelope" caveat is
  correct in direction and understated in magnitude.

---

## Attacks that FAILED to break the build (all EVIDENCE)

**F1 — prereg curve.** Emulated from the image's own knots. All 13 checkpoints reproduce exactly:
idx 8/20/32 = 248, **34 = 380**, 36 = 512, 44 = 512, 45 = 506, 54 = 452, 60 = 416, 68 = 368, 80 = 296,
88 = 248, 100 = 248. Matches the builder and the A11.4 row.

**F2 — knots, continuity, divisor, truncation.** Image X = `(0,32,36,44,88)`, strictly increasing,
widths `32,4,8,44` — **no zero divisor**. Continuity checked at every knot from both sides:
`X=32` step +0 · `X=36` +66 (= exactly one slope step) · `X=44` +0 · `X=88` −6 (one slope step).
**No discontinuity anywhere.** Range over the full index domain is exactly `[248, 512]`; never above 512,
never below 248, never below V282 at any index.

**The truncation attack dies outright:** `264 = 66*4` and `264 = 6*44`, so **both legs divide EXACTLY**
— the `divq` quotient is never truncated at *any* index on *either* leg. Truncate-toward-zero on the
descending leg, the thing the builder was careful about, never actually fires. Verified by exhaustive
enumeration of all indices on all four legs.

**F3 — 32-bit overflow in `E*Kp`.** Re-derived the error from the image: `0x29D6C mulh r13,r16`
(setpoint x sign, so `|r16| <= 32767`), `0x29D76 shl 0x5,r16` (x32), `0x29D78 sub r26,r16` -> **E =
setpoint*32 − feedback.** Bounds read from the image: assist map slot 7 (`0xE502C`) max Y = **1032**;
feedback clamp `0xC62E6` = **46080** (two-sample sum -> 92,160).

```
|E|max = 1032*32 + 92160 = 125,184
Kp=512 : |E*Kp| = 64,094,208   vs 2^31 = 2,147,483,648   ->  33.5x margin
overflow needs |E| >= 4,194,304 ; absolute structural ceiling on |E| is 1,140,704  ->  UNREACHABLE
```

**Overflow is structurally impossible, by 3.7x even at the int16 ceiling.** Also holds at the stock
Kp 696 (24.6x margin). `(Pclamp<<8) = 15360<<8 = 3,932,160` — the builder's P-rail numerator is correct.

**P-rail thresholds** (P rails at `|E| >= 3,932,160/Kp`): idx 36–44 rails at **|E| >= 7,680** vs V282's
15,855 — exactly the 2.06x the build states. No index rails *differently in kind*; the sum clamp
(15360), D clamp (10240), anti-windup (10240) and output cap (3072) are all unchanged and all read
correct on the V284 image. **No intermediate changes sign anywhere.**

**F4 — index range.** `zxh r7` at `0x29DE8` forbids a negative index. Upstream, the demand is clamped
against the **byte** cals `0xC64F0`/`0xC64F1` = **240/240** and then absolute-valued, so
**idx in [0, 240]** — never above 240, never negative. The build's 0..255 tabulation covers the whole
reachable domain; I additionally emulated all **65,536** index values and found nothing outside [248,512].
Separately: the decompile shows the **same variable** feeds the assist-map lookup and the Kp lookup
(`uVar33` is not reassigned between them), which independently confirms the offline index definition.

**F5 — the twin `FUN_0002a93a` is UNREACHABLE on this image.** Four independent checks, **each
positive-controlled**:

- Raw LE `jarl` disp22 scan (opcode field `0x1E`, hw1 bits 6–10) over `[0x13000,0x100000)`: found
  **20,835 call sites / 13,679 targets**, and located all four known controls exactly
  (`0x28EA6`<-`0x22522`, `0x34350`<-`0x23276`, `0x3AA2C`<-`0x2291E`, `0xC4B34`<-`0x55C0E`).
  **Callers of `0x2A93A`: NONE.**
- 32-bit LE word scan for `0x0002A93A` anywhere in the image (indirect call / vector table): **NONE.**
  Control: the scan finds `0x000E5378` at `0xCB9B0` = `0xCB994 + 4*7`, the slot-7 pointer. Scanner sound.
- Short/conditional branch scan into `0x2A93A`: **NONE.** Control: finds both branches to `0x29E0A`
  (`0x29E00`, `0x29E12`).
- **Fall-through is impossible:** `0x2A938 jmp lp` returns immediately before it, and `0x2A93A` is
  `prepare {r20..r28}, 0x0` — a function prologue, i.e. a genuine entry point nothing enters.

It *does* reference the pointer bank (the `0xCB994` constant appears at `0x2ACBA` inside its body), so it
is indeed the twin — but **the reshaped record cannot reach it.** Its arithmetic is moot.

**F6 — frozen cells.** All 16 FROZEN cells re-read from the **V284** image: `0xC61B2`=3072,
`0xC61B4`=3072, `0xC61B6`=10240, `0xC61BA`=10240, `0xC61BC`=15360, `0xC61BE`=15360, `0xC62E6`=46080,
**`0xC63E6` (Ki) = 0**, `0xC63E8`=923, `0xC63EA`=1560, `0xC63EC`=992, `0xC63EE`=507, `0xC62E4`=4,
`0xC6CD0`=5346, `0xC6446`=5244. All correct. Kd slot 7 (`0xE511C`) = flat 128. **V284 is the memoryless
arm; it is not V283.**

---

## What I did NOT check (other agents' surfaces)

Build-script census and CRC recompute; slot/selector liveness and interlocks; the physical unit chain;
the closed-loop stability consequence of the raised Kp (I bounded the arithmetic, not the plant). My
A1 exposure figures use the kit's inherited `demand_idx()`; I confirmed its *form* against the decompile
but not its scaling constants — that is the unit-chain agent's surface.

## One residual, disclosed

The build's own null-sentence already names it: if the live index the LERP sees is not the
`0xE4`-derived index tabulated offline, the whole X-axis argument (mine included) moves. The tap site
`st.h r7, -0x697a, gp` at `0x29DDA` exists and is unread by this build. **This is a BELIEF-level
dependency for A1's exposure numbers, not for F1–F6, which are image-internal.**
