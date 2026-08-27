# ADJUDICATION 2026-08-21 — "raise r24/r26" (model) vs V71c (road)

Subagent adjudication. Ghidra (`code.bin`, stock, read-only) + raw-Python byte work on the built
images under `ACCORD_FIRMWARE_ROOT=C:/Users/dudei/Desktop/Projects/accord-firmwares`.
Every decision-bearing line is marked **[EVIDENCE]** (with method) or **[BELIEF]** or **[RELAYED]**.

---

## 0. VERDICT — **(c), with one stated escape hatch**

> **The arm is LIVE on both V71c and V88. They differ in exactly ONE control-law cell. V71c is the
> HIGHER dose on the model's own axis at every value of the unknown lane weight `a`. The model says the
> higher dose should be BETTER; the road says it was WORSE (grind #1 excluded HIGHER, P = 0.0215;
> grind #2 returned; ratchet at the corpus record). ⇒ THE MODEL'S DIRECTION IS REFUTED BY THE ONLY
> ON-CAR SINGLE-VARIABLE TEST OF IT THAT EXISTS.**
>
> **The escape hatch:** the refutation inverts only if `a = gp-0x69a4/1024 > 5.57`, a quantity this kit
> has **never measured** (the tracer's own open item B). **One comparator rung closes it.**
>
> **Independently — and this alone is disqualifying — the identification behind the `m` table cannot
> be steered by.** `r85` has **2 episodes**. Dropping one swings `|A|` **0.183 ↔ 0.570 (3.1×)** and moves
> the model's own "worst dose" `m*` from **0.518 to 0.938** — a range that *contains both V88 and V71c*.
> **And the identification is CONFOUNDED**: route `0x85` = V100 carries Lever B **ARMED**, route `0x95`
> = V101 carries it **REMOVED**, so `κ` was solved from a two-point contrast in which the r24/r26 lane
> *itself* is one of the two things that changed.

**Recommendation: DO NOT RAISE.** Not because the road outranks the model by fiat, but because the
model fails its own robustness check, is confounded with the very lane it advises on, and its single
falsifiable on-car prediction has already been run and lost.

---

## 1. Task 1 — `gp-0x683c`: the writer/reader scan, and the SCOPE ERROR that voids the claim

### 1.1 The claim is TRUE — and IRRELEVANT to V71c and V88

**[EVIDENCE — four independent methods, stock `code.bin`]**

| method | result for `gp-0x683c` (`0xFEDF17C4`) |
|---|---|
| Ghidra `search_instructions("-0x683c")` | 1 hit — `0x3AA94 ld.bu -0x683c, gp, r15` |
| Ghidra `disassemble_bytes(0x3AA94, dry_run)` | `ld.bu -0x683c, gp, r15`, bytes `847fc597` |
| Python disp16 scan, **all 8 load/store opcodes, correct per-opcode displacement rule, byte-coverage width per width class** (so `st.h`/`st.w` overlap counts) | **1 candidate — the same read. ZERO writers of any width.** |
| Python disp23 (6-byte extended) scan | 1 raw candidate at `0x4CD9C`; **adjudicated FALSE** — `disassemble_bytes` shows no instruction starts there (next instruction begins `0x4CDA0`) |
| Python LE32 literal scan for `FEDF17C4` | **0 occurrences** ⇒ no `mov imm32` pointer construction |

The four `st.b` hits sharing `hw2 = 0x97C5` in the same block (`0x52E54`, `0x52FA8`, `0x5303A`,
`0x53196`) resolve to **`gp-0x683b`**, the adjacent cell — exactly the conflation class the brief warns
about. The decode rule was applied correctly: **`ld.b`/`ld.bu` take displacement bit 0 from `hw1`
bit 5** (equivalently the opcode-field LSB, `0x3C` = even, `0x3D` = odd) and `hw2` bit 0 is a
don't-care; **`st.b` takes `hw2` exactly**; **halfword/word ops** put a size selector in `hw2` bit 0.
The rule was validated in-place on `gp-0x671a`, whose 7 readers encode `hw2 = 0x98E7` (op `0x3C`,
even ⇒ `-0x671A`) while its sole writer encodes `hw2 = 0x98E6` (`st.b`, exact).

⇒ **`gp-0x683c`: 1 reader, 0 writers. CONFIRMED.**

### 1.2 🛑 BUT THAT IS A STATEMENT ABOUT **STOCK**, AND V71c AND V88 ARE NOT STOCK

**[EVIDENCE — read from the built images + Ghidra]**

Both V71c and V88 carry `0x3AA96 = 0xFB`, i.e. `0x3AA94..97 = 84 7f fb 97`. That exact 4-byte sequence
**already exists twice in stock** — at `0x42842` (`FUN_00042746`) and `0x55C76` (`FUN_00055c42`) — and
Ghidra decodes it, unprompted, as:

```
847ffb97  →  ld.bu -0x6806, gp, r15
```

Confirmed by both methods: `search_instructions("-0x6806")` returns those addresses with those bytes,
and the Python decoder gives `disp = (hw2 & 0xFFFE) | hw1_bit5 = 0x97FA | 0 = -0x6806`.

**`gp-0x6806` is the LKAS ENGAGEMENT FLAG** (`[RELAYED]` from `STATE.md` §3, where it is an on-car
measurement: 83.0 % vs 0.0 %, Fisher p = 3.8×10⁻⁴¹) and, structurally, **it is a heavily written live
cell — 15 `st.b` writers and 14 `ld.bu` readers [EVIDENCE, same scan]**, versus `gp-0x683c`'s zero.

⇒ **THE RELAYED "ZERO WRITERS ⇒ THE ARM IS DEAD" CLAIM IS SCOPED TO STOCK AND DOES NOT TRANSFER.**
Repointing that one byte is *the whole point of Lever B*: V67 replaced a permanently-zero selector with
the engagement flag. On V67/V68/**V71c**/V84/V85/V86/V86b/**V88**/V89…V100, engaged ⇒ `gp-0x6806 ≠ 0`
⇒ **both `0xC6444` (r26) and `0xC6446` (r24) are read.**

The source of the error is identifiable and benign: `docs/traces/TRACE-2026-08-21-r24-r26-as-active-damping.md`
§1.2 states *"`FUN_0003aa2c` contains ZERO references to `gp-0x6806`"* and §2.3 marks every override arm
"dead or starved". Both are correct **for stock**. Neither was qualified.

### 1.3 The decompile, confirming the gate structure

`decompile_function(0x3aa2c)` **[EVIDENCE]**:

```c
bVar1 = *(byte*)(gp-0x671a) < *(byte*)(tp+0x74fa);      // 0xC64FA = 5 ; always TRUE on-car
bVar4 = *(char*)(gp-0x683c) == '\0';                    // <-- V67+ : gp-0x6806 == 0  (== NOT ENGAGED)

/* r26 → gain_A */                        /* r24 → gain_B */
if (bVar4) {                              if (*(char*)(gp-0x671d) == '\0') {
  if (!bVar1) uVar12 = cal(0xC643E);        if (bVar4) { if (!bVar1) uVar11 = cal(0xC6440); }
} else {                                    else       { uVar11 = cal(0xC6446); }   // ARMED
  uVar12 = cal(0xC6444);   // ARMED       } else       { uVar11 = cal(0xC6442); }
}
```

Both arms hang off the **same** `bVar4`. `gp-0x671d` strictly outranks it on the r24 side.

### 1.4 `gp-0x671d` and `gp-0x671a` — rescanned with the corrected decode

**[EVIDENCE, same 4-method scan]**

| cell | readers | writers | note |
|---|---|---|---|
| `gp-0x671d` (`0xFEDF18E3`) | 14 (`ld.bu`, op `0x3D` odd, `hw2=0x98E3`) | **2** — `0x3BD2A st.b r0` (clear) and `0x41EC6 st.b r28` | matches the record; **not** zero-writer. Its on-car value 0/402,424 frames is an operating-point fact, not a structural one |
| `gp-0x671a` (`0xFEDF18E6`) | 7 (`ld.bu`, op `0x3C` even, `hw2=0x98E7`) | **1** — `0x42A12 st.b r7` (`hw2=0x98E6`) | exactly reproduces the record's "sole writer `0x42A12`" |
| `gp-0x6806` (`0xFEDF17FA`) | 14 | **15** | the live engagement flag |

disp23 hits: 0 for all three. LE32 literal hits: 0 for all four cells.

### 1.5 ⚠ Residual found in today's trace doc — reported, not fixed

`traces/TRACE-2026-08-21-r24-r26-as-active-damping.md` §2.2 says the r26 skip *"needs BOTH `gp-0x6b5e != 0`
AND the rare `gp-0x671a >= 5`"*. **The polarity of `bVar1` is inverted there.** From the decompile plus
the cal bytes (`0xC6136 = 0`, `0xC6138 = 1`, read from stock/V71c/V88 — identical in all three):

```
bVar1 = (gp-0x671a < 5)              -> TRUE in the flown regime (671a == 0 on 255,292 frames)
sVar7 = bVar1 ? cal(0xC6138)=1 : cal(0xC6136)=0
skip  = (gp-0x6b5e != 0) AND (sVar7 == 1)   ==>  in the flown regime, skip == (gp-0x6b5e != 0)
```

⇒ **r26 is zero-forced whenever `gp-0x6b5e != 0`, on its own** — the COMMON `gp-0x671a` state *arms*
the skip, it does not disarm it. This matters: it is the one remaining structural route by which
`0xC6444` could be inert. It is **not** closed by the images — but V70's probe read `gp-0x6adc`
(r26 post-clamp) strictly negative on **1,644 / 18,010** frames, which is an existence proof that
`gp-0x6b5e == 0` on ≥9.1 % of frames **[RELAYED]** ⇒ the lane fires.

---

## 2. Task 2 — the V71c ↔ V88 image diff

**[EVIDENCE — full byte diff over `[0x13000, 0x100000)`, strict contiguity]**

`_v71c_plain_image.bin` sha256 `30b63fdd…ff1607` (matches `BUILD-LINEAGE.md`'s recorded V71C SHA ⇒
**this is the flown artifact, not a re-cut**) vs
`_v88_…_plain_image.bin` sha256 `96b1e018…0ca47b8`.

**77 bytes, 7 runs:**

| run | bytes | what it is | control law? |
|---|---|---|---|
| `0x55DF2..3` | `e893` → `6894` | the **CAN-0x427 packer's source**: `ld.h -0x6C18[gp],r6` → `ld.h -0x6B98[gp],r6`. Introduced at **V87** ("PROBE.427.6B98") | **NO — telemetry** |
| `0xC4B34..0xC4B77` | 61 differing bytes | the **code cave payload**: V70's 4-bit sign probe vs V88's `gp-0x6b98` sign+mag256 probe | **NO — telemetry** |
| `0xC4FFC..F`, `0xC6FFC..F` | CRCs of blocks `0xC4000` / `0xC6000` | — | no |
| **`0xC6445`** | **`0c` → `02`** | **`0xC6444` (LE16) 3072 → 512 — r26's ENGAGED gain arm, Q10 ⇒ 3.000× → 0.500×, a factor of 6.00** | **YES — the only one** |

**Cave safety check [EVIDENCE]:** scanning `0xC4B30..0xC4B78` in both images for 4-byte store opcodes
with `reg1 = gp` returns **exactly one store in each, and it is the same store** —
`st.b r6, -0x1514[gp]` (`4437ecea`), the known write-only CAN-TX/diag tap. **Neither cave writes control
RAM.** ⚠ *Limit of method: 4-byte gp-relative stores only; a register-indirect store would be invisible.
Both caves are ~62 B of straight-line code with no visible pointer setup, and this payload family has
flown ≥7 times.*

**Frozen controls [EVIDENCE, read from the images]:** `0x3AA96 = fb` in **both** · `0xC6446 = 5244` in
**both** · `0xC6442 = 1024`, `0xC6440 = 2048`, `0xC643E = 1536`, `0xC64FA = 5`, `0xC61F6 = 3`,
`0xC6CD0 = 3564` (4× LKAS gain), `0x454FE = b5` (V42's ratchet fix present) — **all identical in both.**

⇒ **V71c ↔ V88 IS A CLEAN SINGLE-VARIABLE `0xC6444` CONTRAST IN THE CONTROL LAW.** There is no second
control-law cause to find. The corpus-extremes argument in `STATE.md` §5 survives the `gp-0x683c`
challenge intact — **for the wrong reason to the one STATE.md gives** (it is not that `a ≠ 0` makes two
identical builds differ; it is that the two builds were **never** arithmetically identical, because the
`a = 0` row is a *limit*, not the operating point, and the selector is live).

### 2.1 ⚠ BUT THEY WERE NOT FLOWN COMPARABLY — and a cleaner contrast already exists

**[EVIDENCE, from `BUILD-LINEAGE.md` / `archive/LEDGER-V38-TO-V84.md` / the handoff chain]**

- **V71c flew route `58`** (2026-08-04/05). Engaged creep-corner **23.0 s**, high-rate creep **6.4 s**.
- **V88 flew route `73`** (2026-08-09). 613.4 s, 72.7 % engaged, **119.6 s ≥50 km/h** — the kit's first
  real highway route.

These are not matched exposures, and **the record never scored V71c against V88 directly.** The chain is
transitive: V71c grind #1 `e_18-22` = **223** vs **V67/V68's 109, excluded HIGHER, P = 0.0215**; and
separately **V88/V67 = 1.101 [0.424, 2.206]** (V88 ≈ V67).

✅ **The cleaner contrast is V71c vs V67, and it is the one the record actually ran.** Byte-diffing
them **[EVIDENCE]**: V67 → V71c = **71 bytes / 9 runs** = `0x454FE` (`ba`→`b5`, V42 ratchet fix) +
61 cave bytes + `0xC6445` (`0xC6444` 512→3072) + 8 CRC. **V67 and V88 carry byte-identical rate-lane
cells** (`fb` / 512 / 5244), so V67 is a legitimate stand-in and it is same-era.
⚠ Not perfectly single-variable either — V71c also restored `0x454FE`, though **RULE 5** records that
lever as **null by construction on V71's drives** (`gp-0x67fa == 4` never occurred while driving), and
in any case it is a change that should have made the ratchet *better*.

### 2.2 🛑 REPORT THE OPERATOR IN HIS OWN WORDS — "worst build ever" is KIT JARGON

**[EVIDENCE, `archive/LEDGER-V38-TO-V84.md:236`]** the operator's V71c report is
***"attenuated but still present"***, and he **ranked V71c ABOVE V71b**.

"The worst build ever recorded on all three symptoms" is a **band-instrument** statement (grind #1 223;
grind #2 7 bursts at 44.31 Hz, p99 = 12.2× any non-bursting build; ratchet 8,521 ct p-p = corpus
record). `BUILD-LINEAGE.md:646` simultaneously lists **V71C among the builds that MEASURABLY MOVED grind
#1** (it beat *stock*, P = 0.0006; it lost to *V67*, P = 0.0215).
**Both statements are in the record and they are about different instruments.** The honest form is:

> *V71c raised the r26 arm 6× and the kit's grind-#1 instrument got ~2× worse than V67's, grind #2
> returned, and the ratchet p-p hit the corpus record; the operator called it "attenuated but still
> present". V88 held r26 at Honda's 512, and the operator said the grinding was fixed.*

---

## 3. Task 3 — the `m`-axis mapping, and the overshoot hypothesis

The brief's table is exactly reproduced by **`A(m) = A + (m−1)·κ·G_r24`** with
`A = 1 + 0.630∠163°`, `κ = c = 13.09∠145.3°`, `G_r24 = 0.1173∠−89.9°` ⇒ `Δ = κ·G_r24 = 1.5355∠55.40°`
(reproduces 0.449 / 0.223 / 0.438 / 1.016 / 1.926 / 3.455 to 3 decimals). Worst point
**`m* = 0.7542`, `|A| = 0.2226`, amplification 4.49×** **[EVIDENCE, arithmetic]**.

Using STATE.md's own net-dose formula, `m(a) = (5244 + C6444·a)/(3072 + 3072·a)`, `a = gp-0x69a4/1024`:

| `a` | m(V88) | model amp V88 | m(V71c) | model amp V71c | model's ordering |
|---|---|---|---|---|---|
| 0 | 1.707 | 0.68 | 1.707 | 0.68 | tie (limit only) |
| 0.25 | 1.399 | 0.99 | 1.566 | 0.79 | **V71c better** |
| 0.848 (parity) | 1.000 | 2.28 | 1.383 | 1.01 | **V71c better** |
| 1.0 | 0.937 | 2.79 | 1.354 | 1.06 | **V71c better** |
| 1.62 | **0.754 (= m\*)** | **4.49** | 1.270 | 1.22 | **V71c better** |
| 3.0 | 0.552 | 2.62 | 1.177 | 1.46 | **V71c better** |
| **5.57** | 0.402 | 1.73 | 1.106 | 1.73 | **crossover** |
| 10 | 0.307 | 1.38 | 1.064 | 1.90 | V88 better |

**Key structural facts [EVIDENCE, arithmetic]:**

1. **V71c's `m` ∈ (1.000, 1.707] for every `a` ≥ 0. It is NEVER outside the model's identified range
   and it NEVER exceeds 1.71.** ⇒ **the overshoot hypothesis is DEAD**: V71c cannot have "overshot past
   the favourable region", because the model has no unfavourable region above `m = 1` at all — `|A|` is
   strictly increasing (improving) for all `m > 0.754`.
2. **V71c's `m` ≥ V88's `m` for every `a` > 0.** V71c is unambiguously the *higher* dose on this axis.
3. `|A(m)|` is a parabola in `m` with its minimum at `m* = 0.754`. V71c sits on the increasing
   (improving) branch **always**; V88 crosses the minimum at `a = 1.62`. ⇒ for every `a < 5.57` the model
   predicts **V88 is the WORSE build**, by up to **3.4×** in closed-loop amplification (at `a ≈ 1`).
4. **The escape hatch:** at `a > 5.57` (i.e. `gp-0x69a4 > 5709` counts) the ordering flips.

⚠ **A second, independent limit on the mapping:** the net-dose formula is **small-signal only**. r24 and
r26 are each clamped at ±0x2000 **before** they are summed (`0x3AB78`-region and `0x3AC3E`-region
clamps, visible in the decompile). At `dtorque = ±5120` and `gain = 5244`, r24 pre-clamp is 26,220 ⇒
**railed**; gain changes do nothing there. The formula is valid only in the small-`dtorque` micro
regime — which is, fortunately, where 6–9 Hz lives.

**Is `a` ever > 5.57?** **UNMEASURED. [OPEN]** `gp-0x69a4` is a `ushort` fed by `FUN_000352b4`'s
`gp-0x37fc` table (tracer open item B). Its parity point `a = 0.848` is quoted throughout the kit as if
physical, which is weak evidence that the kit believes `a = O(1)`, not `a = O(6)`. **[BELIEF]** `a > 5.57`
is unlikely — at `a = 5.57` r26 would outweigh r24 by 5.6× at equal gains, and r26 would rail on almost
every frame — but **this is a belief, not a measurement, and it is the whole hinge.**

---

## 4. Task 5 — the identification's own foundation. **It cannot be steered by.**

Reproduced by running `analysis-2020accord/studies/grind2/_g2b_kappa_robust.py` **[EVIDENCE]**.

### 4.1 Episode counts: **r85 = 2, r95 = 3.**

`|ρ−1| = 0.291` at 6–9 Hz is the *best-conditioned* band the script flags as WELL-POSED, and it is built
from **two** episodes on the 4× arm.

### 4.2 Leave-one-episode-out at 6–9 Hz

| dropped | `\|P4\|` | `\|A\|` | `arg c` |
|---|---|---|---|
| none (full) | 0.630 | **0.440** | +145.3° |
| r85 ep0 | 0.855 | **0.183** | +159.3° |
| r85 ep1 | 0.591 | **0.570** | +131.2° |
| r95 ep0/1/2 | 0.644/0.563/0.734 | 0.413/0.505/0.371 | +147.5/+143.1/+145.1 |

**`|A|` swings 0.183 ↔ 0.570 — a 3.1× range — from dropping ONE of TWO episodes.** `arg c` spans
**34°** (+126.7° … +160.8°) over the 12 combinations. Speed-matched variants add `arg c = +173.0°` at
0–5 m/s.

### 4.3 What that does to the `m` table **[EVIDENCE, propagated]**

- **`m*` — the model's own "worst possible dose" — moves 0.518 → 0.938** across the LOO variants.
  On one variant `m*` = 0.938, and **V88's `m` at `a = 1` is 0.937.** The model cannot tell you whether
  V88 is sitting *on* its worst point or 0.4 away from it.
- **`|c|` moves 11.20 → 18.15** (1.6×), so `Δ` — the whole lever arm of the `m` axis — is uncertain by
  the same factor.
- **What IS robust:** `d|A|/dm > 0` at `m = 1` in **all 12 LOO variants and all 5 speed-matched
  variants** ⇒ *within this model*, "raise" is locally favourable, robustly. And **`amp(V71c)/amp(V88)`
  < 1 at `a ≤ 2` in every variant** ⇒ the model's V71c-vs-V88 prediction is robust too, and it is robustly
  wrong against the road.

⇒ **The FRAGILE parts are exactly the parts a build would need (where the optimum is, how big the win
is); the ROBUST part is the part the road has already falsified.** That is the worst possible split.

### 4.4 🛑 AND THE IDENTIFICATION IS CONFOUNDED WITH LEVER B ITSELF

**[EVIDENCE — `_scratch/cache/r85/r85_identity.json` = "build": "V100"; `_scratch/cache/r95/r95_identity.json` =
"build": "V101"; cells read from the images]**

| route | build | `0xC6CD0` | `0x3AA96` | `0xC6444` | `0xC6446` |
|---|---|---|---|---|---|
| `0x85` (the "4×" arm) | V100 | 3564 | **`fb` ARMED** | 512 | **5244** |
| `0x95` (the "8×" arm) | V101 | 7128 | **`c5` DEAD** | 512 | **512** |

`ρ = Z₄/Z₈` and then `c = (ρ−1)/(G₈ − ρG₄)` attribute the whole difference to a single scalar `κ` acting
through a measured `ΔG`. **But the two arms differ in THREE firmware cells, and two of them ARE the
r24/r26 lane the model then advises about.** V101's filename says it outright: `…-NOLEVERB-…`.

Whether that biases `κ` depends on whether the lane change is fully absorbed into the *measured* `G`
(in which case `κ` is still the invariant rest-of-loop) or partly into `κ` itself. I cannot settle that
from the data here. **[BELIEF]** it is at minimum a bad look for using this `κ` to price *that lane*,
and it is a checkable defect: the kit has never flown two builds differing **only** in `0xC6CD0`.

---

## 5. Reconciling with the kit's own "r24/r26 PUMPS" finding

The tracer's §6.2 flagged a **~131°** irreconcilable gap between `r24 = 0.1173∠−89.9°` (the model's
input) and the `139.1°` the `Re(Z)` route gives, and could not resolve it. **This adjudication does not
resolve it either** — but it changes which side has the burden:

- The `Re(Z)` route says r24/r26 **pumps** at 6–9 Hz ⇒ **cut it**. **V88 cut it (r26 ÷6) and the
  operator said the grinding was fixed.**
- The `P = κG` route says **raise it**. **V71c raised it (r26 ×6) and every instrument got worse.**

⇒ the two model routes disagree, and **the road agrees with the `Re(Z)` route.** That is a
tie-break, not a proof — but it points the same way the operator's experience does.

---

## 6. What I could NOT resolve

| # | open | what closes it | cost |
|---|---|---|---|
| **1** | **`a = gp-0x69a4/1024` is unmeasured.** The entire refutation inverts if `a > 5.57`. | **One comparator rung: `gp-0x69a4 ≥ 5709`.** A single cave bit, no scale assumption, duty *is* the answer. Or two rungs bracketing `a ∈ {1, 5.57}`. | 1–2 rungs |
| **2** | `gp-0x6b5e`'s engaged duty — the one remaining structural route to "`0xC6444` is inert". | A comparator rung `gp-0x6b5e == 0`, or decompile `FUN_000361c8` (its sole writer) to a mode condition. | 1 rung |
| **3** | Whether `κ` is biased by the Lever-B confound in the r85/r95 pair. | Fly two builds differing **only** in `0xC6CD0`; or re-solve with a third arm (route `71` = V87, 4×, Lever B dead) as the de-confounder. | 1 drive or 1 re-analysis |
| **4** | The `−89.9°` vs `139.1°` phase gap (tracer §6.2 / open item A). Not closed here. | The derivation/route behind `G_r24 = 0.1173∠−89.9°`. It is not in any file I could find. | ask the author |
| **5** | V71c-vs-V88 exposure mismatch (route `58` vs `73`). The clean same-era contrast is V71c-vs-V67 (P = 0.0215) and I used that; I did **not** re-run either score. | Re-score V71c vs V67 with the current estimator and an episode bootstrap. | 1 analysis |
| **6** | r26's own magnitude on-car. V70 proved *sign*; nothing has ever measured *size*. | A comparator `\|r26\| ≥ \|r24\|` (`gp-0x6adc` vs `gp-0x6ada`, both free RAM mirrors, both already proven readable). **This single rung measures `a` operationally and is immune to scale.** | 1 rung |

---

## 7. Record defects found (reported, not fixed — per standing instruction)

1. **`traces/TRACE-2026-08-21-r24-r26-as-active-damping.md` §1.2/§2.3** — "`FUN_0003aa2c` contains ZERO
   references to `gp-0x6806`" and "every override arm is dead or starved" are **STOCK-ONLY** and must be
   qualified. Unqualified they void every Lever-B build's mechanism.
2. **Same doc, §2.2** — the r26 skip condition has `bVar1`'s polarity inverted (see §1.5 above).
3. **`STATE.md` §5 / `BUILD-LINEAGE.md:55`** — *"At `a = 0`, V88 and V71c are ARITHMETICALLY IDENTICAL"*
   is a statement about a **limit that the car never occupies**, presented as if it were the operating
   point; the inference *"⇒ `a` is materially non-zero"* is therefore not needed and not established by
   it. The correct statement is simply: the two builds differ in `0xC6444` by 6.00× and nothing else in
   the control law.
4. **`memory/accord/builds/accord-v42-ratchet-fix-lost-since-v53.md`** — *"`0x454FE` byte-stock V53–V70, lost at a
   rebase, restored from V80 on"* is **wrong in the middle**. Read from all 70 images: `b5` on
   **V71a/V71b/V71c, V72, V73, V74, V75, V76_gate_fb, V77, V77b**, then `ba` again on
   V76_v38base, V78, V79, then `b5` from V80 on. It flip-flopped; it was not one contiguous outage.
5. **`STATE.md` §5 / `BUILD-LINEAGE.md`** call V71c *"the worst build ever recorded on all three
   symptoms"*, while `BUILD-LINEAGE.md:646` lists **V71C among the builds that measurably MOVED grind
   #1** and `archive/LEDGER-V38-TO-V84.md:236` records the operator's own words as **"attenuated but still
   present"**, ranking it **above V71b**. The band statement and the symptom statement need separating
   per the standing instruction.

---

## 8. Reproduction

```
# image diffs, cell reads, cross-build timeline
python  (inline, see §2)  — ACCORD_FIRMWARE_ROOT=C:/Users/dudei/Desktop/Projects/accord-firmwares
# identification robustness (reproduces the brief's numbers exactly)
cd analysis-2020accord && python studies/grind2/_g2b_kappa_robust.py
# m-axis propagation under leave-one-out  (temporary, deleted after use)
#   A(m) = A + (m-1)*c*G_r24 ; m(a) = (5244 + C6444*a)/(3072 + 3072*a)
```

Ghidra was used read-only (`dry_run:true` on every `disassemble_bytes`); no program was saved.
