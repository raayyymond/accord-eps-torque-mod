# TRACE 2026-08-13 — `0xC63AE` 1024 → 2048: PROVE OR KILL

Agent: `tracer-c63ae` (firmware-codepath-tracer), subagent of `main`. Study-only — no build, no flash,
no shared-state edits, no `save_program`. GhidraMCP for all decompilation/disassembly; Python for all
byte-level work and as the required second method on every load-bearing count. Program `code.bin`
(stock, confirmed `is_current` in `list_open_programs`). `gp = 0xFEDF8000`, `tp = 0xBF000`.

**Anchors verified from the image BEFORE any address arithmetic** (the off-by-0x1000 trap did not fire):
`0xC63AE`=1024 · `0xC6200`=8192 · `0xC63AC`=102 · `0xC6468`=2639 · `0xC40D2`=102 · `0xC613C`=14490 ·
`0xC64DF`(byte)=100. All match the record.

---

## VERDICT — **NO-GO on `0xC63AE` 1024 → 2048 as V100's calibration lever**

Three independent reasons, each sufficient on its own. The cell itself is clean; the **aim** is what fails.

1. **The "+28 % clears the perceptual floor" claim is a CHANNEL MISMATCH.** The +28 % / +177 ct is a
   median **LEVEL** shift. The bracket (V88 0.549, V85 1.088, V89 0.947) is calibrated in **in-band AC
   delivered ratios**. This lever's in-band figure is **1.242 on Path-2's own output**, and **1.021–1.135
   delivered** once V97's own Path-1 dilution is applied to the BENEFIT as well as the cost.
   **V85's 1.088 was NOT felt.**
2. **The closed-loop sign is UNRESOLVED**, with a live prior in each direction and a V94-class downside.
3. **It is not engagement-gated, and its LARGEST effect is on the hands-OFF / manual arm** (+81 % level
   vs +29 % hands-on). It will be felt mainly as changed steering weight in ordinary driving — a cost
   with no diagnostic value.

**If the direction is ever settled, the right value is 1536, not 2048** (corner margin 1.53× vs 1.14×),
and **1280 is disqualified — it is arithmetically WORSE than stock.**

---

## 1. RULE 7 — **PROVEN, AND IT DOES NOT BITE** [EVIDENCE]

### 1a. The cell itself is NOT mode-indexed

`decompile_function(0x38148)` — the read is a bare `tp` scalar, unconditional:

```c
uVar7 = iVar4 * (uint)*(ushort *)(unaff_tp + 0x73ae) >> 10 & 0xffff;   // tp+0x73ae = 0xC63AE
```
```
search_instructions operand_pattern="0x73ae"  ->  1 match, 183,570 instructions scanned
  00038242  ld.hu  0x73ae, tp, r10     bytes e557af73     FUN_00038148
```

No mode index, no per-mode row, no speed gate, no engagement gate. The only guards are the
`|gp-0x6bfe| ≤ 20000` sentinel (else `gp-0x6b70 = 0x7FFF`) and the caller's `andi 0x830` state gate —
which, per `BUILD-LINEAGE.md`'s V97 entry, is byte-identical to the assist-channel mixer's guard, so a
shut gate means **no power assist at all**.

⇒ **The V69/V70 wrong-mode-record failure mode CANNOT recur for this cell.**

### 1b. The KNOTS are mode-indexed — and the mode is settled

`decompile_function(0x382d8)` (`FUN_000382d8`, the sole writer of the LERP tables):

```c
uVar9   = (uint)(byte)(&DAT_000063fd)[unaff_gp];      // gp+0x63fd = the MODE byte
piVar22 = (int *)(&LAB_000cc9fc + uVar9 * 4);         // breakpoints  0xCC9FC + mode*4
puVar23 = (&PTR_DAT_000c7b40)[uVar9];                 // record[0]    0xC7B40 + mode*4
local_30[6] = *(short **)(&DAT_000090b0 + uVar9*4 + unaff_tp);   // tp+0x90b0 = 0xC80B0 + mode*4
```

Seven record-pointer arrays (`0xC7B40 / 0xC7C28 / 0xC7D10 / 0xC7DF8 / 0xC7EE0 / 0xC7FC8 / 0xC80B0`,
stride `0xE8`), record layout `+0x00 count(=9) · +0x02..0x12 nine X · +0x14..0x24 nine Y`.

**Mode = 24 manual / 26 engaged.** Prior EVIDENCE, re-read not re-measured
(`reference-accord-car-is-tvca4-mode-24-26`): V73's probe reports `gp+0x63fd` in a **4-bit** field, so
observed 8/10 ⇒ true ∈ {8,24}/{10,26}; **raw 8 appears in NO row** of the `0xCD000` config table ⇒
manual = 24 forced; **only row 11 `TVCA4` contains 24** ⇒ engaged = 26 forced. 104,061 frames, 18
transitions, all on engagement edges.

### 1c. ⭐ AND THE DOSE IS NEARLY MODE-INVARIANT — read from the image

```
m24 rec0 @0xd6158  X=[0,200,400,800,1200,1800,3000,5000,12000]  Y=[0,471,880,1408,1689,1953,2376,2844,4181]
m26 rec0 @0xd7130  X=[0,200,400,800,1200,1800,3000,5000,12000]  Y=[0,471,880,1408,1689,1953,2376,2844,4114]
```

Built tables, modes 24 vs 26 at creep: **X knots IDENTICAL, Y differs ONLY at `Y[8]`** (4114 vs 4181 at
0 km/h, 4245 vs 4280 at 6.6 km/h = **0.8–1.6 %**). ⇒ **even if the mode inference were wrong, the dose
moves under 2 %.**

⚠ **CORRECTION TO THE BRIEF.** It states *"recs 0/3/4/5 **and the breakpoints** differ."* The recs do;
**the breakpoints do NOT** — both modes read `[0,960,2560,5120,7680,10240,12800]` counts
(= 0/15/40/80/120/160/200 km/h), from `0xD6BA8` (m24) and `0xD7B98` (m26).

> ### ⇒ **RULE 7 VERDICT: PROVEN AND PASSED.** The cell is a non-indexed scalar with one unconditional
> reader; the mode-indexed tables it indexes into are resolved to mode 26, and the dose is <2 %
> sensitive to that resolution anyway.

---

## 2. WHAT IT MULTIPLIES, AND THE "TWICE" CLAIM — **VERIFIED, WITH A CORRECTION**

### 2a. The arithmetic, from the decompile

```python
idx = ((abs(iVar6) * cal(0xC63AE)) >> 10) & 0xFFFF    # 0x3824a mulu / 0x38256 shr 0xa / 0x3825c zxh
out = sign(iVar6) * LERP(idx, X[0..9], Y[0..9])       # sign re-applied at 0x3824e cmovlt
out = clamp(out, -cal(0xC6200), +cal(0xC6200))        # +-8192
```
⇒ `d(out)/d(iVar6) = (scale/1024) × f′((|iVar6|·scale)>>10)` — **the scale IS in the chain twice.
CONFIRMED.** I reproduce the handoff's "512 is 0.71× WORSE" exactly: AC gain ratio at 512 = **0.706**.

### 2b. 🛑 BUT THE CONSEQUENCE WAS UNDER-STATED — the AC gain is NON-MONOTONE in scale

At the hands-on p50 operating point, the effective small-signal gain relative to stock:

| `0xC63AE` | 512 | 768 | **1024** | **1280** | 1536 | 1792 | **2048** | 2560 | 3072 |
|---|---|---|---|---|---|---|---|---|---|
| AC gain ratio | 0.706 | 0.754 | **1.000** | **0.902** | 1.076 | 1.245 | **1.242** | 1.541 | 2.138 |

🛑 **1280 is WORSE THAN STOCK (0.902).** Each step first pushes the operating point into a flatter LERP
segment, and the multiplier only catches up on the next segment. **A "dose ladder" on this cell is a
sawtooth, not a ladder** — a smaller step does NOT buy proportionally less; it can buy negative.

### 2c. Census — 1 reader / 0 writers, two methods, set-difference EMPTY [EVIDENCE]

| method | result |
|---|---|
| GhidraMCP `search_instructions operand_pattern="0x73ae"` | **1 hit** — `ld.hu 0x73ae,tp,r10` @`0x38242`, 183,570 scanned |
| raw Python LE scan, base=r5(tp), **both parities** | **1 hit**, same address, `hw1=57e5 hw2=73af` — the **`hw2 = disp\|1`** form, `op6=0x3F` = `ld.hu` = a READ |
| 6-byte extended-displacement form | **0** |
| absolute literal `0x000C63AE` / `0x63AE` anywhere in the 1 MB image | **0 / 0** ⇒ no register-indirect base can be synthesised |
| stores (`op6=0x3B` `st.h`) at this displacement | **0** |

No `ep`-aliasing exposure: the cell is read directly through `tp` in one instruction. (The `ep`-based
array in this function is the LERP table at `gp-0x64b8`, a different object.)

### 2d. The `zxh` wrap — **UNREACHABLE at every dose considered**

`zxh r8` @`0x3825c` is a real 16-bit truncation, but:

| scale | wraps when `\|iVar6\|` > | margin over route-81 measured max (4,743) | measured WRAP duty |
|---|---|---|---|
| 1024 | 65,535 | 13.8× | 0.0000 |
| 1536 | 43,690 | 9.2× | 0.0000 |
| **2048** | **32,767** | **6.9×** | **0.0000** |
| 4096 | 16,383 | 3.5× | 0.0000 |

⇒ **the wrap concern recorded in `reference_accord_c63ae_arm_agnostic_residual_gain_and_zxh_wrap` does
not bind at ≤ 2048 on measured data.** (That memory's *structural* reach of 82,224 remains true and
unmeasured; it rests on all six lane windows co-pegging, which has never been observed.)

### 2e. ⭐ NEW STRUCTURAL FACT — `Y[9]` and the clamp are the SAME CELL

`FUN_000389ec` stores `*(gp-0x3702) = *(ushort *)(tp+0x7200)` ⇒ **`Y[9] = 0xC6200 = 8192`, the same cal
the output is then clamped to.** ⇒ the LERP can never exceed the clamp, so **the ±8192 clamp is never
the binding constraint.** The saturation is the *table* pinning at `Y[9]` for `idx ≥ X[9]`.

---

## 3. THE DOSE, ON THE OPERATOR'S OWN MEASURED DISTRIBUTION

### 3a. My own inversion, and its positive control

Rebuilt `FUN_000382d8` + `FUN_000389ec` line-by-line in integer Python from stock bytes, then inverted
route 81's measured `|gp-0x6b70|` (`427 = clamp(|gp-0x6b70|·5>>6, 0, 0x3FF)` ⇒ `×12.8`, ZOH'd onto the
row grid exactly as `rlog-tools/score/v98_r81_score.py:98-99`), **per frame at that frame's own speed**.

**Positive control — my rebuild reproduces `docs/traces/TRACE-2026-08-12-stage2-lerp-knots.md` §5 BIT-EXACTLY**
at 0.0 / 3.0 / 6.6 km/h (X, Y and the X-cap all MATCH), and `LERP(X[k]) == Y[k]` at all ten knots.
Identity gate `0x14A` byte7[7:6]==2 duty **1.000000** on 17,982 frames.

| mask | n | p10 | **p50** | p90 | p99 | max | censored |
|---|---|---|---|---|---|---|---|
| ENGAGED all | 6,591 | 36 | **389** | 3,339 | 4,330 | 4,744 | 0.0000 |
| **ENG hands-ON (press)** | **2,198** | **851** | **2,712** | **3,915** | 4,479 | 4,744 | 0.0000 |
| ENG hands-OFF (press) | 4,393 | 20 | **184** | 611 | 1,026 | 1,975 | 0.0000 |
| ENG hands-ON (D3) | 2,271 | 415 | 2,576 | 3,903 | 4,479 | 4,744 | 0.0000 |

Engaged speed p50 **5.58 km/h**, p90 11.15 km/h. Reproduces the record: engaged-all p50 **389 ✓**,
hands-off **184 vs 188 ✓**, speed **5.58 ✓**. My hands-on p50 **2,712** vs the handoff's **2,829** —
4 % apart (I use each frame's own speed; the handoff used a fixed creep table). Zero frames censored,
so the inversion is well-posed everywhere.

### 3b. The ladder — hands-ON engaged, at its own measured speeds

| `0xC63AE` | LEVEL p10 | **LEVEL p50** | LEVEL p90 | **AC (6–9 Hz) ratio** | Δ ct into `gp-0x6b94` |
|---|---|---|---|---|---|
| 512 | 0.627 | 0.779 | 0.788 | 0.706 | −142 |
| **1024 (stock)** | 1.000 | **1.000** | 1.000 | **1.000** | 0 |
| **1280** | 1.075 | **1.084** | 1.134 | **0.902** 🛑 | +49 |
| **1536** | 1.147 | **1.159** | 1.242 | **1.076** | +92 |
| 1792 | 1.215 | 1.225 | 1.314 | 1.245 | +134 |
| **2048** | **1.271** | **1.291** | **1.381** | **1.242** | **+173** |
| 3072 | 1.476 | 1.548 | 1.923 | 2.138 | +322 |

Hands-OFF at 2048 for contrast: LEVEL p50 **1.806** (+81 %), AC 1.420.

### 3c. 🛑 THE CATEGORY ERROR, AND IT IS THE FINDING

The **+28 % / +177 ct** that made this "the only lever above the floor" is a **median LEVEL shift** — a
quasi-static offset in the PID reference `gp-0x6ad6`. The perceptual bracket is calibrated in
**in-band AC delivered ratios** (V88 15–22 Hz command 0.549; V85 6–9 Hz 1.088; V89 0.947). **These are
different channels.** The in-band figure for this lever is **1.242**, not 1.291.

### 3d. 🛑 AND THE DILUTION — applied to the BENEFIT, which V97 never did

`builds/v80_v107/build_v97_tva.py:65-67`: a **1.234× LANE** change diluted to **"+2 % .. +13 % on the TOTAL command"**
⇒ Path-1 dilution factor **φ ∈ [0.085, 0.556]**. Applying the identical φ here:

| quantity | lane figure | **delivered TOTAL** |
|---|---|---|
| **AC 6–9 Hz @ 2048** | 1.242 | **1.021 .. 1.135** |
| AC 6–9 Hz @ 1536 | 1.076 | 1.006 .. 1.042 |
| LEVEL @ 2048 | 1.291 | 1.025 .. 1.162 |

> ### ⇒ **AGAINST THE FLOOR: V85's 1.088 was NOT felt. V89's 0.947 was NOT felt. This lever delivers 1.02–1.14 in-band. IT STRADDLES THE NOT-FELT LINE AND ITS MIDPOINT IS BELOW IT.**

⚠ V97's own script flags that dilution as **"a MODEL, not a measurement"**, and it was computed at
21 Hz. It is the best number the kit has; it is not an EVIDENCE-grade one. **[BELIEF, resting on an
EVIDENCE-grade lane figure and a modelled φ.]**

---

## 4. CLAMP RISK — THE NUMBERS, AND THE HAZARD IS NOT THE ONE NAMED

### 4a. The pin fraction the brief asked for — it is ZERO

Fraction of hands-on engaged frames (n = 2,198) at or beyond each boundary:

| `0xC63AE` | **PIN (`idx ≥ X[9]`, output ≡ 8192, marginal gain exactly 0)** | last segment (`idx ≥ X[8]`) | WRAP |
|---|---|---|---|
| 1024 | 0.0000 | 0.0000 | 0.0000 |
| **1280** | **0.0000** | **0.0000** | 0.0000 |
| **1536** | **0.0000** | **0.0000** | 0.0000 |
| **2048** | **0.0000** | **0.0000** | 0.0000 |
| 2560 | 0.0000 | 0.0332 | 0.0000 |
| 3072 | 0.0000 | 0.1965 | 0.0000 |
| 4096 | 0.1870 | 0.4959 | 0.0000 |

⇒ **The relay hazard as posed does not materialise at 1280, 1536 or 2048. It is zero, not small.**

### 4b. 🛑 THE REAL HAZARD IS THE `X[8]` CORNER — A GAIN **EXPANSION**, AND NOBODY HAS NAMED IT

The last segment `[X[8], X[9]] → [Y[8], 8192]` does not saturate — **it steepens**:

| km/h | X[8] | X[9] | f′ on `[X[7],X[8]]` | **f′ on the last segment** | **jump** |
|---|---|---|---|---|---|
| 0.0 | 12,000 | 14,490 | 0.181 | **1.638** | **9.0×** |
| 6.6 | 10,681 | 14,490 | 0.212 | **1.036** | **4.9×** |
| 30 | 9,400 | 14,490 | 0.305 | 0.612 | 2.0× |
| 50 | 7,000 | 14,490 | 0.348 | 0.452 | 1.3× |
| 80 | 6,000 | 14,490 | 0.431 | 0.380 | 0.9× |

**A slope that rises with amplitude is the classic limit-cycle setup — the V80 mechanism** (*"worst
grinding ever"*, 27.4 Hz limit cycle, zero DTCs, invisible to the fault system).

**Margin of that corner over the measured max `|iVar6|` = 4,743:**

| `0xC63AE` | corner at `\|iVar6\|` = | **margin** | frac ≥ corner | **frac ≥ 0.8 × corner** |
|---|---|---|---|---|
| 1024 | 10,853 | 2.29× | 0.0000 | 0.0000 |
| 1280 | 8,682 | 1.83× | 0.0000 | 0.0000 |
| **1536** | **7,235** | **1.53×** | 0.0000 | **0.0000** |
| **2048** | **5,426** | **1.14×** | 0.0000 | **0.0332** |
| 2560 | 4,341 | 0.92× | 0.0332 | 0.2520 |

🛑 **At 2048 the margin is 1.14× and 3.3 % of hands-on frames sit within 20 % of a 4.9× slope
discontinuity.** One excursion 14 % larger than anything on route 81 crosses it.
**At 1536 the margin is 1.53× and the within-20 % fraction is 0.0000.**

### 4c. Highway coverage hole — priced, and it is benign

Route 81 is creep-only (engaged p90 11.15 km/h), and `0xC669A`/`0xC66A8` truncate the X axis to 7,000
above 50 km/h. Replaying the **same** `|iVar6|` distribution at 50 / 80 km/h [WHAT-IF, a stated
assumption — the highway `|iVar6|` distribution has never been measured]:

| replay speed | last-segment frac @2048 | PIN @2048 | but the jump there is |
|---|---|---|---|
| 50 km/h | **0.2398** | 0.0000 | only **1.3×** |
| 80 km/h | **0.4117** | 0.0000 | only **0.9×** (no corner at all) |

⇒ **The dangerous combination — a large corner AND reachable — does not occur in any scenario I can
build from measured data.** At creep the corner is 4.9–9.0× but unreachable; at highway it is reachable
but essentially flat.

> ### ⇒ **RECOMMENDED VALUE IF THIS EVER FLIES: 1536.** Corner margin 1.53× vs 2048's 1.14×; zero
> frames within 20 % of the corner; AC 1.076 instead of 1.242.
> 🛑 **NOT 1280 — it is AC 0.902, arithmetically worse than stock.**

---

## 5. THE COST, STATED BEFORE THE UPSIDE

1. **Steering weight.** LEVEL **+29 %** at 2048 / **+16 %** at 1536 on `gp-0x6ad6`, the driver-feel
   reference. This is the **V86B *"extra dampening at slow speed"*** class, which he **felt**.
2. 🛑 **IT IS NOT ENGAGEMENT-GATED, AND ITS LARGEST EFFECT IS ON THE WRONG ARM.** `FUN_00038148`'s only
   guards are the `0x7FFF` sentinel and the caller's `andi 0x830` state gate. **It acts in MANUAL.** And
   the **hands-OFF** arm gets a **+81 %** level change at 2048 versus **+29 %** hands-on — because
   hands-off sits on the steep part of the curve. ⇒ **the most visible consequence will be in ordinary
   driving, not in the symptom regime.** That is the opposite of what a symptom-targeted lever should
   look like, and it is a strong confound for any operator report.
3. **21 Hz.** `0xC63AE` is a pure GAIN with no dynamics, so — unlike V97's pole — its effect at 21 Hz is
   the **same** factor as at 7.79 Hz: **+24 % at 2048**, landing on the band V62 and V88 bought the
   grinding fix in. Worst case on V88's Lever B (15–22 Hz command 0.549): undiluted
   `1.242 × 0.549 = 0.682`, diluted `1.135 × 0.549 = 0.623` — **both still inside V88's CI
   [0.407, 0.844]**, so it does not undo V88, but it eats into it.
4. ⭐ **The dilution is applied SYMMETRICALLY here** (§3d): the same φ multiplies cost and benefit, so
   the trade ratio is unchanged and both shrink together. **This is the asymmetry `builds/v80_v107/build_v97_tva.py`
   committed and this trace does not repeat.**

---

## 6. 🛑 THE BLOCKING UNCERTAINTY — THE CLOSED-LOOP SIGN

**OPEN-LOOP, closed by construction [EVIDENCE]:** raising the scale strictly increases `|gp-0x6b70|`,
sign-preserving. `f′ ≥ 0` is enforced in code at three ungated sites (`0x388c4`'s eight
`max(Y[i],Y[i-1])` rungs, the float-path monotone guard, `0x38de2`/`0x38e48`) ⇒ monotone
non-decreasing for any cal, any mode, any build; and `mulu` on `|iVar6|` cannot touch the sign, which
is re-applied separately at `0x3824e`.

🛑 **CLOSED-LOOP, NOT CLOSED.** `gp-0x6b70` is a PID **reference that gets SUBTRACTED**, and Path 2
enters as `B = 1 + Q`, **not in series**
(`reference_accord_path2_bracket_criterion_closes_openloop_not_closedloop`). Whether raising this
lane's gain **reduces or increases** 6–9 Hz grinding is unresolved, and the record carries a live prior
in **each** direction:

| direction | the argument | strength |
|---|---|---|
| **FOR raising** | the `f′`-compression story — the observer is desensitised 6.3× exactly when the driver pushes; restoring `f′` restores the correction | **BELIEF** (handoff §3b: *"fits all the data, not a tested prediction"*) |
| **AGAINST** | `Re(Z) < 0` at 6–9 Hz **replicated on three drives**; raising a loop gain in an anti-damped band makes it worse. Precedents: **V94** motor accel 3–7× up ⇒ *"worse by a lot… not safe to drive"* (aborted); **V85** de-relaying `0xC40BC` made the ratchet **worse**, 2.89× → 6.58× | **EVIDENCE** for the premises, BELIEF for the inference |

⇒ **This is a ~50/50 direction bet whose wrong-way outcome is +24 % of 6–9 Hz loop gain and +29 %
steering weight, in a loop with a recorded V80/V94 precedent for exactly that failure.**

---

## 7. ORDERING DEPENDENCY ON `gp-0x6ad6` — BOTH BRANCHES

`FUN_0003a382` takes `feedback = clamp(gp-0x6ad6, ±0xC6200 = 8192)` while `gp-0x6ad6` itself is clamped
at ±25,600. `tracer-6ad6` is measuring `|gp-0x6ad6| ≥ 8192`'s duty. My answer depends on theirs in a
simple, monotone way:

- **HIGH duty ⇒ every number in this trace scales toward zero, roughly by `(1 − duty)`.** Both the AC
  *and* the LEVEL effect are killed, because `gp-0x6ad6` **is** the clamped signal — the PID never sees
  the increase. `0xC63AE` becomes null-by-construction and must not fly as a fix. **Worse: raising
  `gp-0x6b70` pushes `gp-0x6ad6` further into the clamp**, so the lever partly disables itself.
- **LOW duty ⇒ the numbers above stand as computed**, and the verdict rests on §3d (dose below the
  floor) and §6 (sign unresolved) — **which are independent of their result.**

⇒ **My NO-GO does not depend on `tracer-6ad6`.** A low duty does not rescue the lever; a high duty
kills it a second way.

---

## 8. WHAT SURVIVES, AND WHAT WOULD CHANGE MY ANSWER

**Survives — the cell is genuinely clean:** RULE 7 passed · 1 reader / 0 writers by two methods,
set-difference EMPTY · VIRGIN on every build script (`build_v90/91/92/96/97/98/99` all list it as
stock 1024; never written) · no wrap at ≤2048 (6.9× margin) · no pin at ≤2048 (duty 0.0000) · dose
<2 % sensitive to the mode inference.

**What would change my answer, in priority order:**
1. **The closed-loop sign.** The cheap route is already specified in `TRACE-2026-08-13-path2-authority`
   §7: two sign rungs (`gp-0x6bfe < 0` and `(gp-0x374c>>4) < 0`) give the arm-to-arm phase from the
   cross-correlation of two 100 Hz sign sequences, with no scale assumption. **Until the sign is
   settled, no gain on this lane should fly as a fix.**
2. **A measured Path-1 vs Path-2 share at 6–9 Hz**, to replace V97's modelled φ ∈ [0.085, 0.556]. If
   φ turned out near 1, the delivered figure would be 1.242 and the verdict on §3d would flip.
3. **A highway `|iVar6|` distribution.** The 50/80 km/h rows in §4c are a WHAT-IF on a creep-measured
   distribution.

---

## 9. EVIDENCE / BELIEF LEDGER

| claim | grade | method |
|---|---|---|
| `0xC63AE` read once, unconditionally, `0x38242 ld.hu 0x73ae,tp,r10` | **EVIDENCE** | decompile `0x38148` + `search_instructions` (1/183,570) + raw LE both-parity scan (1 hit, same addr) |
| 1 reader / 0 writers; 6-byte form 0; no absolute literal | **EVIDENCE** | Ghidra ∖ Python set-difference EMPTY; `0x000C63AE`/`0x63AE` absent from the 1 MB image |
| RULE 7 does not apply to the cell; knots are mode-indexed; mode = 24/26 | **EVIDENCE** (structure) / **EVIDENCE, prior** (mode) | decompile `0x382d8`; `reference-accord-car-is-tvca4-mode-24-26` re-read, not re-measured |
| m24 vs m26 differ only at `Y[8]` (0.8–1.6 %); **breakpoints identical** | **EVIDENCE** | records read LE from `code.bin` at `0xD6158`/`0xD7130`, `0xD6BA8`/`0xD7B98` |
| `Y[9]` and the ±clamp are the same cell `0xC6200` | **EVIDENCE** | `FUN_000389ec`: `*(gp-0x3702) = *(ushort*)(tp+0x7200)` |
| LERP rebuild is faithful | **EVIDENCE** | reproduces `TRACE-2026-08-12` §5 bit-exactly at three speeds; `LERP(X[k])==Y[k]` at all ten knots |
| `\|iVar6\|` hands-on p50 2,712, max 4,743 | **EVIDENCE** | own inversion; reproduces the record's engaged p50 389 / hands-off 184 / speed 5.58 |
| AC gain **non-monotone**, 1280 = 0.902 < stock | **EVIDENCE** | `(scale/1024)·f′` evaluated per frame on the measured distribution |
| PIN / WRAP duty 0.0000 at 1280/1536/2048 | **EVIDENCE** | per-frame forward evaluation, n = 2,198 |
| last segment is a 4.9–9.0× gain **expansion**; margin 1.14× at 2048 | **EVIDENCE** | knot arithmetic from the built tables |
| delivered in-band 1.021–1.135 ⇒ at/below the not-felt line | **BELIEF** | EVIDENCE-grade lane figure 1.242 × a **modelled** φ from `builds/v80_v107/build_v97_tva.py:65-67`, which its own author flags as a model |
| raising the scale increases `\|gp-0x6b70\|`, sign-preserving | **EVIDENCE** | code-enforced `f′ ≥ 0` at 3 ungated sites + sign re-applied at `0x3824e` |
| whether that helps or hurts 6–9 Hz grinding | **UNRESOLVED** | `B = 1 + Q`; live priors both ways (§6) |
| 50/80 km/h rows | **WHAT-IF** | creep-measured `\|iVar6\|` replayed on the highway tables |

**Scripts** (session scratchpad, reproducible): `lerp.py` (the table rebuild, every line annotated with
its decompile site), `dose.py` (the inversion + positive control), `ladder2.py` (the dose ladder,
corner margins and clamp fractions).

---
---

# PART 2 — MAKING **φ** MEASURABLE (follow-up task, same agent)

φ = Path-2's share of the delivered command at 6–9 Hz. It priced V97's cost, it is the soft link in
Part 1's NO-GO, and it will price every future Path-2 lever. **It has never been measured** and is
quoted as `[0.085, 0.556]` — a 6.5× range, which is not a constraint.

## 1. WHAT PATH 1 ACTUALLY IS — **an unweighted 11-term sum, and Path 2 is one term** [EVIDENCE]

`decompile_function(0x3aa2c)`. With `gp-0x67ac ≡ 0` (proven open, `TRACE-2026-08-13-path2-authority`):

```c
sum = gp-0x6ade·[|·|<=1024]   + gp-0x6b4c·[|·|<=10240] + gp-0x6ad4·[|·|<=10240]  // <-- PATH 2
    + gp-0x6b62·[|·|<=8192]   + gp-0x6b26·[|·|<=1024]  + gp-0x6bbe·[|·|<=2048]
    + gp-0x6bd0·[|·|<=2048]   + gp-0x6b86·[|·|<=24576] + r24_lane(±8192) + r26_lane(±8192)
    + FUN_00036682();
gp-0x6b94 = clamp(sum, ±0x2800 = 10240);          // 0x3acec..0x3ad20
```
The `[·]` are **zero-reject booleans (0/1), not gains.**

**Assembly confirms "unweighted" — `0x3acc8`–`0x3ace6` is `mov` + TEN `add` + one `jarl` + one `add`,
and ZERO multiplies:**
```
0x3acc8 301a mov      0x3acd8 39cd add
0x3acca 31d8 add      0x3acda e1c7 add
0x3accc 41c6 add      0x3acdc ffbf jarl  -> FUN_00036682
0x3acce 61c8 add      0x3ace0 701c mov
0x3acd0 51cc add      0x3ace2 7f24 ld.w
0x3acd2 79ca add      0x3ace6 51ce add
0x3acd4 81cf add      16-bit opcode census over the junction: {add: 10, mov: 2}
0x3acd6 69d0 add
```
⇒ **`builds/v80_v107/build_v97_tva.py:65-67`'s "Path 1 is unweighted" — CONFIRMED.**

⇒ ⭐ **φ is therefore NOT a share of a weighted mix. It is literally `Path2 / total` at one summing
junction where every coefficient is exactly +1.** That is the cleanest possible definition, and it
means φ needs no modelling — only two numbers at the same node in the same units.

## 2. "UNAFFECTED BY A" — **SURVIVES** [EVIDENCE, two methods]

`A` = `0xC63AC` acts only on `gp-0x374c`. Census of `gp-0x374c`:

| method | result |
|---|---|
| Ghidra `search_instructions "-0x374c"` | **2 hits, BOTH in `FUN_00038148`** — `ld.w` @`0x381fe`, `st.w` @`0x38230` |
| raw Python LE scan, base=gp, both parities | **same 2**, `op6=0x39` (ld) / `0x3b` (st) |
| absolute literal `0xFEDFC8B4` anywhere in the image | **0** |

⇒ **the ACTUAL-arm accumulator never leaves `FUN_00038148`.** `A` cannot reach any of the other ten
summands. ✅

⊕ `gp-0x6ad4` census: **1 writer** (`0x3a8a0`, `FUN_0003a382`) / **1 reader** (`0x3aca8`,
`FUN_0003aa2c`). Python offered a third hit @`0x767b2` — **adjudicated OUT**: `op6=0x23`, not a
gp-relative `ld`(0x39)/`st`(0x3b); a byte coincidence in a dense 16-bit stream (its neighbour
`0x767a8` carries the identical `op6=0x23` pattern). Set-difference EMPTY after adjudication.

## 3. IS φ RECOVERABLE FROM EXISTING WIRE? — **NO, AND EXACTLY ONE NUMBER IS MISSING**

```
phi(6-9 Hz) = 0.2565 * RMS_6-9(gp-0x6b70)  /  RMS_6-9(gp-0x6b94)
              \________ numerator: HAVE ________/    \___ denominator: NEVER ON THE WIRE ___/
```

### 3a. ⭐ THE NUMERATOR IS CONFIRMED — and I nearly found it wrong

I reproduced it from `_scratch/cache/r81` and it lands on the record's figure to 4 s.f.:

| reconstruction of `gp-0x6b70` from 427 | **6–9 Hz RMS, engaged** | 6–9 Hz manual | 20–24 Hz control |
|---|---|---|---|
| **SIGNED** (b7 reconstructed) | **548.28** ✅ record says 548.3 | 29.62 | 104.46 |
| RECTIFIED `\|·\|` only | 112.73 | 28.66 | 82.45 |

⇒ **`TRACE-2026-08-13-path2-authority`'s 140.6 ct is CORRECT** (0.2565 × 548.28 = 140.63).

🛑 **BUT THE MARGIN IS 4.86×, AND ONE SHIPPED SCRIPT IS ON THE WRONG SIDE OF IT.**
`rlog-tools/score/v98_r81_score.py:541` feeds D4b the **rectified** lane:
```python
"mt427_gp6b70": d["mt_row"].astype(float) * (64.0 / 5.0)      # no sign applied
```
The sign bit toggles **5.06 times per second** (918 transitions in 181.5 s), so `|x|` is not `±x`. Any
band claim from D4b's `mt427_gp6b70` row **understates 6–9 Hz by ~4.9×** and distorts its eng/manual
ratio (3.93 rectified vs 18.51 signed). **Reported, not fixed** — it is outside the work already
accepted, and it does not touch the path2 trace, which used the signed reconstruction correctly.

⭐ **This is a MEASURED justification for the design law's "sign bit paired with a magnitude channel",
on this exact lane: omitting it costs 4.9×.** It makes the sign rung below mandatory, not stylistic.

### 3b. The denominator is genuinely missing, and cannot be bounded structurally

`gp-0x6b94`'s structural range is ±10240, and Path 2 alone can reach ±10240 ⇒ **φ ∈ [0,1]
structurally. Useless.** Several sibling lanes are measured ~0 (`gp-0x6bd0` on 87,940 frames;
`gp-0x6b62` on 75,227 engaged frames) but that bounds the *broadband* sum, not the 6–9 Hz share.
**⇒ It needs a measurement. One magnitude time series. [EVIDENCE that it is not derivable; the
alternative — inverting the plant from column torque — needs a plant model and is not offered.]**

## 4. THE INSTRUMENT — **cheapest is a 427 REPOINT, and it needs NO cave growth**

### 4a. The magnitude channel: repoint 427 to `gp-0x6b94`. **Zero packer change, zero saturation.**

```
existing packer (V96/V97/V98, unchanged since V96):  clamp(|X| * 5 >> 6, 0, 0x3FF)
gp-0x6b94 clamp = +-10240   ->   max code = (10240*5)>>6 = 800  of 1023
```
⇒ **NO SATURATION IS POSSIBLE**, structurally, from the aggregator's own clamp read at `0x3acec`.
LSB **12.8 ct**; quantisation noise 3.7 ct against an expected 6–9 Hz RMS in the hundreds.
**Edit = the hw2 of `ld.h ..[gp],r6` at `0x55DF2` only** (`R427_ADDR` in `builds/v80_v107/build_v98_tva.py:544`, the
same site used for every prior repoint). `0x55E10`'s `sar 0x6` carries unchanged.
⇒ **~2 bytes. NO CAVE GROWTH. GATE 1 RAM ownership UNCHANGED — no new store, no new load target.**

🛑 **GATE 3 note:** ±10240 is the aggregator's **own output clamp**, i.e. the lane's own reachable
output — not a downstream gate. This is the sizing the design law asks for, and it is read from the
decompile, not assumed.

### 4b. The 5 bits at `0x14A` byte4 b7:b3 — comparator form throughout

| bit | rung | why |
|---|---|---|
| **b7** | **`gp-0x6b94 < 0`** | 🛑 **MANDATORY** — §3a measures the cost of omitting it at **4.9×**. Without it 427 is rectified and the RMS is not the RMS. |
| b6 | `\|gp-0x6ad4\| >= \|gp-0x6b94\|` | instantaneous ratio >= 1.00 |
| b5 | `2·\|gp-0x6ad4\| >= \|gp-0x6b94\|` | ratio >= 0.50 |
| b4 | `4·\|gp-0x6ad4\| >= \|gp-0x6b94\|` | ratio >= 0.25 |
| b3 | **`\|gp-0x6b70\| >= 1024`** | ⭐ **POSITIVE CONTROL with a PRE-MEASURED duty** (below) — it re-anchors the cross-route numerator inside the new drive |

The ladder is **comparator form — no LSB, no ceiling, no assumed distribution**; the ×2 and ×4 are
exact shifts. Three duties = a 3-point CDF of the instantaneous ratio.
⚠ **Stated plainly: the ladder measures the BROADBAND ratio, not the 6–9 Hz ratio.** It is a
consistency check and a regime anchor, **not** φ. φ comes from 427 + b7.

**Buildability — this is proven machinery, not a new claim.** V98's flown cave was already a
two-operand comparator cave (`builds/v80_v107/build_v98_tva.py:302`: *"each comparator rung and pay one extra
read-modify-write of `gp-0x1514`"*), flown on route 81 with duty 1.000000. The store set stays
**exactly `{gp-0x1514, gp-0x1511}`**. Cost estimate **~60–75 B** of added payload at ~20 B/rung using
the recompute-per-rung discipline CLAUDE.md prefers. ⚠ I have **not** verified the cave's remaining
byte extent against its proven envelope — **that is a builder check I did not run.**

### 4c. Pre-registered duties, from route 81 — these must reproduce or the build is not trusted

```
|gp-0x6b70| >= 512   engaged 0.6519   manual 0.6825
|gp-0x6b70| >= 1024  engaged 0.4559   manual 0.5913     <- b3, the positive control
|gp-0x6b70| >= 2048  engaged 0.2414   manual 0.3701
```

## 5. 🛑 THE PRE-REGISTERED NULL SENTENCE

> **There is no null.** φ = 140.6 / R, where R is the engaged 6–9 Hz RMS of a signed, unsaturated,
> known-LSB channel. **The measurement returns a number on every drive that flies at all.** This is
> the opposite of a threshold rung: there is no gate that can fail to arm.

**The decision boundary, pre-registered:**

| measured R (ct RMS) | φ | delivered ratio for Part 1's lane 1.242 | verdict on `0xC63AE` |
|---|---|---|---|
| 141 | 1.00 | 1.241 | **ABOVE the floor — Part 1's NO-GO would be OVERTURNED** |
| 300 | 0.469 | 1.113 | ABOVE |
| **387** | **0.373** | **1.088** | ⭐ **THE CROSSOVER — exactly V85's not-felt figure** |
| 500 | 0.281 | 1.068 | BELOW — NO-GO stands |
| 1200 | 0.117 | 1.028 | BELOW — NO-GO stands |

> ### ⇒ **`R < 387 ct` overturns Part 1's dose argument. `R > 387 ct` confirms it.** One number, one
> drive, and it also replaces V97's `[0.085, 0.556]` (which corresponds to R ∈ [253, 1654]) for every
> future Path-2 lever.

**The four ways this instrument could still fail, and how each is caught:**
1. Build doesn't fly / identity fails → `0x14A` byte7[7:6] is exhausted; **V100 needs its own identity
   scheme, which is the orchestrator's item 3 and I have not designed it.**
2. 427 saturates → **structurally excluded** (max code 800 of 1023).
3. Sign bit stuck or inverted → caught by b3's pre-measured duty and by the manual/engaged contrast.
4. Too little exposure → 15 s engaged gives ~90 independent samples in a 3 Hz band ⇒ RMS relative
   s.e. **≈ 7.5 %**; 30 s gives ≈ 5.3 %. **Route 81 gave 65.1 s.** Comfortably inside the design law's
   one-episode budget.

## 6. COLLISION WITH `tracer-6ad6` — **and a merge that answers both**

I did **not** design any `gp-0x6ad6` or `iVar6` rung. But we collide on two scarce resources:

- **427.** If they need it for `gp-0x6ad6` or `iVar6`, only one of us gets it. **φ cannot be measured
  without a magnitude channel**, and 427 is the only one with the range and rate.
- **The 5 bits.** My spec uses all five; their `|gp-0x6ad6| >= 8192` needs at least one.

⭐ **MERGE, if the orchestrator wants both answers on one build** — drop my b4 (`ratio >= 0.25`):

| bit | rung |
|---|---|
| b7 | `gp-0x6b94 < 0` — mandatory for 427 |
| b6 | `\|gp-0x6ad4\| >= \|gp-0x6b94\|` |
| b5 | `2·\|gp-0x6ad4\| >= \|gp-0x6b94\|` |
| **b4** | **`\|gp-0x6ad6\| >= 8192` — `tracer-6ad6`'s rung** |
| b3 | `\|gp-0x6b70\| >= 1024` — positive control |

⊕ **These two questions are complements, not competitors:** if their duty is high, Path-2's marginal
authority is ~0 and my φ is the share of a lane that cannot be moved; if it is low, φ is the number
that prices every lever on that lane. **Both are answered by one drive on one 427 channel.**

## 7. EVIDENCE / BELIEF LEDGER — PART 2

| claim | grade | method |
|---|---|---|
| the aggregator is an unweighted 11-term sum; Path 2 is one term | **EVIDENCE** | decompile `0x3aa2c` + 16-bit opcode census of `0x3acc8`–`0x3ace6` = {add:10, mov:2}, zero multiplies |
| `gp-0x6b94` clamp = ±10240 ⇒ 427 cannot saturate on it | **EVIDENCE** | `0x3acec`–`0x3ad20`; `(10240·5)>>6 = 800 < 1023` |
| "Path 1 unweighted" (`builds/v80_v107/build_v97_tva.py:65-67`) survives | **EVIDENCE** | as above |
| "unaffected by A" survives — `gp-0x374c` never leaves `FUN_00038148` | **EVIDENCE** | Ghidra 2 hits ∖ Python 2 hits = EMPTY; absolute literal 0 |
| the record's 140.6 ct numerator is correct | **EVIDENCE** | independent reconstruction gives 548.28 vs its 548.3 |
| `score/v98_r81_score.py:541` D4b uses the lane rectified ⇒ ~4.9× understatement | **EVIDENCE** | signed vs rectified band RMS, 918 sign transitions in 181.5 s |
| φ is not derivable from existing wire | **EVIDENCE** (the denominator has never been transmitted) / **BELIEF** (that no proxy exists) | census + the structural bound being [0,1] |
| the crossover at R ≈ 387 ct | **EVIDENCE** for the arithmetic; **BELIEF** for the perceptual bracket it is scored against | `1 + 0.242·(140.6/R) = 1.088` |
| ~60–75 B cave cost | **BELIEF** | scaled from V98's flown two-operand rungs; **the remaining cave extent was NOT checked** |
