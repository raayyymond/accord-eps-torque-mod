# TRACE 2026-08-13 — PATH-2 AUTHORITY, bounded two ways; and the V97 "phantom" attacked

Answers the orchestrator's three questions. Scripts mirrored in the scratchpad
(`path2_static.py`, `path2_emp.py`, `zoh_trap.py`, `q3_phantom.py`).
GhidraMCP only (`code.bin`, stock). Decompile-first throughout; assembly used only to confirm
a claim already framed from the decompile. Every count/null confirmed with a raw Python LE scan.

---

## HEADLINE

1. ⭐ **PATH 2 HAS SUBSTANTIAL AUTHORITY. The low-authority hypothesis is REFUTED on the static
   side.** `d(gp-0x6b94)/d(gp-0x6b70)` = **0.253 / 0.257 / 0.262 at 6 / 7.79 / 9 Hz**, with
   essentially **zero net phase** (−0.9° / +8.2° / +13.3°). Every link is unity or a read cal;
   nothing in the chain is small. 🛑 **CONDITIONED 2026-08-13 (later), record-repair pass — this is
   the UNSATURATED derivative. See item 4 below: it is no longer a hypothetical risk, it is
   CONFIRMED — the condition is `|gp-0x6ad6| < 8192`, and clamp duty is unmeasured.**
2. ⭐ **TWO GATES COULD HAVE ZEROED PATH 2 ENTIRELY. BOTH ARE PROVEN OPEN — and one of them
   closes a multi-session OPEN item.** `gp-0x67ab` (which drops `gp-0x6b70` out of `gp-0x6ad6`)
   is a **sticky-OR that can only be set by role ∈ {2,3,4}**, and the static role table
   `0xC4124` = `00 00 05 00 05 05 00 00 00 05 00` **contains no 2, 3 or 4** ⇒ `gp-0x67ab ≡ 0`.
3. ⭐ **Empirically, Path 2 injects ~141 counts RMS at 6–9 Hz into `gp-0x6b94`** on route `0x81`
   (427's own 6–9 Hz engaged RMS is 548 counts). Against V87's `gp-0x6b98` engaged median of
   208 ct that is **the same order as the delivered command itself.**
4. 🛑 **ONE RESIDUAL COULD STILL KILL IT, AND IT HAS NEVER BEEN MEASURED**: the PID's
   `clamp(gp-0x6ad6, ±8192)`. If `gp-0x6ad6` rides outside that clamp, Path 2's *marginal*
   authority is **exactly zero** while every gain above stays as computed. **This is the single
   best comparator rung available.** ✅ **CONFIRMED 2026-08-13 (later) — `tracer-6ad6` traced this
   exact clamp** (`0xC6200` = 8192, read at `0x3a7a2` inside `FUN_0003a382`, all three of P/I/D
   driven from the clamped difference); crux verified by the team lead directly in Ghidra
   (`read_memory(0xC6200)` = 8192, `disassemble_bytes` reproduces the listing
   instruction-for-instruction). **The prediction in this item was exactly right — only the duty
   remains unmeasured; V100's RUNG A targets it.**
5. ⭐ **METHOD FINDING — the 427 lane's "35–45 Hz negative control" is STRUCTURALLY INVALID.**
   427 is transmitted at **49.8 Hz**; a ZOH onto the 101 Hz row grid images the 5–15 Hz baseband
   into 35–45 Hz. Demonstrated with a synthetic positive control. **`scorer-v98`'s "4.14× even in
   the negative control ⇒ no band-specific claim" should be revised**, not accepted.
6. 🛑 **QUESTION 3: THE PHANTOM IS AN IDEALISATION OF A CONFIGURATION THAT DOES NOT EXIST.** The
   arithmetic is right; the assumption fails four ways. Stock is **84.1° out of arm-to-arm
   alignment at 7.79 Hz**, not matched. V97's direction claim ("further apart") survives; the
   "V97 broke an exact match" framing does not.

---

# QUESTION 2 — BOUNDING PATH-2's AUTHORITY

## 2a. STATIC — the full chain, mirrored in integer Python

### The chain, link by link. Every factor is either 1, a read cal, or the PID.

```
gp-0x6b70  (the Stage-2 output, = sign(iVar6)*LERP(|iVar6|), clamp +-8192 @ 0xC6200)
   |
   | FUN_00037fe6 @0x37fe6 :  gp-0x6ad6 = clamp( ( -gp-0x6b4a + SUM(7 terms) ) * speedLERP >>10, +-25600 )
   |    gate      0x380b0 cmp 0x1,r14 / 0x380b2 be   -> the 7-term block runs iff gp-0x67ab != 1
   |    enable    0xC64B0 = 1                          (byte, tp+0x74b0)
   |    zero-rej  |gp-0x6b70| <= 10240                 (clamp is +-8192, so ALWAYS passes)
   |    speedLERP tp+0x7aca..0x7ad8 = [1024]*8         -> 1024/1024 = 1.000 AT EVERY SPEED
   v                                                                          FACTOR = +1.000
gp-0x6ad6  (the PID's driver-torque tracking REFERENCE)
   |
   | FUN_0003a382 @0x3a382 :  err = clamp( gp-0x4f60 - clamp(gp-0x6ad6, +-8192), +-10240 )
   v                                                                          FACTOR = -1
err
   |  P: gp-0x367c += ((err*Kp>>10)*32 - gp-0x367c)*aP>>10       Kp=256   aP=0xC6450=1024 (pass-thru)
   |  I: gp-0x3688 += (err*Ki)>>10                               Ki= 98
   |  D: d = ((err-err_1)*Kd)>>10 ; clamp +-10240
   |     gp-0x3680 += (d*32 - gp-0x3680)*aD>>10                  Kd=2048  aD=0xC644A=1024 (pass-thru)
   |  out = ((P + I + D) >> 5) * Kout>>10 * polarity             Kout=1024 (unity)
   v                                                                          FACTOR = H(f)
gp-0x6ad4
   |  polarity gp-0x6752 = -1   (V98 b3: constant, 0 transitions in 17,982 frames)   FACTOR = -1
   |  FUN_0003aa2c @0x3aa2c : a UNITY summand of the aggregator, zero-reject +-10240
   |     (present iff gp-0x67ac != 1 -- see the gate proof below)
   v                                                                          FACTOR = +1
gp-0x6b94  (clamp +-10240)  -> governor -> gp-0x6ace -> gp-0x6acc -> shaper -> gp-0x6b98 -> FOC
```

The two `-1`s cancel. **Net: `d(gp-0x6b94)/d(gp-0x6b70) = +H(f)`.**

### The PID transfer `H(f)`, and its positive control

Cals read little-endian from `code.bin`, anchored first (`0xC63AC`=102, `0xC6200`=8192,
`0xC6468`=2639 all confirmed, so the tp base is right and the off-by-0x1000 trap did not fire):

| gain | LERP X / Y | index | value at the flown operating point |
|---|---|---|---|
| `Kp` | `tp+0x7b1e` [0,300,2000,4000] / `tp+0x7b26` [256,256,225,153] | `gp-0x6ac0` | **256** (in-burst rate ≈ 99) |
| `Ki` | `tp+0x7b0a` [0,400,1500,3000] / `tp+0x7b12` [98,98,98,98] | `gp-0x6ac0` | **98**, flat |
| `Kd` | `tp+0x7ade` [50,400,1500,3000] / `tp+0x7ae6` [2048]*4 | `gp-0x6ac0` | **2048**, flat |
| `Kout` | `tp+0x77b2` [5,10,15] / `tp+0x77b8` [1024,1024,1024] | `gp-0x671a` | **1024** = unity |

```
H(f) = [ (Kp/1024)*32  +  (Ki/1024)/(1 - z^-1)  +  (Kd/1024)*32*(1 - z^-1) ] / 32 * (Kout/1024)
     = [ 8            +  0.0957/(1 - z^-1)      +  64*(1 - z^-1)           ] / 32
```

| f (Hz) | \|P\| | \|I\| | \|D\| | **\|H\|** | **arg H** |
|---|---|---|---|---|---|
| 1.00 | 8.000 | 15.232 | 0.402 | 0.5273 | −61.51° |
| 3.00 | 8.000 | 5.077 | 1.206 | 0.2794 | −25.65° |
| **6.00** | 8.000 | 2.539 | 2.413 | **0.2529** | **−0.89°** |
| **7.79** | 8.000 | 1.955 | 3.132 | **0.2565** | **+8.24°** |
| **9.00** | 8.000 | 1.693 | 3.619 | **0.2617** | **+13.29°** |
| 21.00 | 8.000 | 0.726 | 8.438 | 0.3607 | +41.81° |
| 28.00 | 8.000 | 0.545 | 11.245 | 0.4367 | +49.71° |

⭐ **POSITIVE CONTROL, RUN BEFORE THE MEASUREMENT AND IT PASSES.** The record
(`accord-fun3a382-is-a-torque-tracking-pid`) independently states *"+41.8°..+55.0° lead at 21 Hz,
\|D\| ≈ \|P\|"*. This reproduction gives **`|D|/|P|` = 1.055 and `arg H` = +41.81° at 21 Hz**, and
+49.71° at 28 Hz. Two numbers, three significant figures, from a completely separate derivation.
**[EVIDENCE]** that the mirrored arithmetic is faithful.

### ⭐ THE TWO GATES THAT COULD HAVE ZEROED PATH 2 — both proven OPEN

Two independent booleans, both written in `FUN_00026c80`, either of which removes Path 2 **entirely**
while leaving the car driveable. **Neither had ever been checked against V89 or V97.**

**GATE A — `gp-0x67ac`, the aggregator's reduced branch.** When it is 1, `FUN_0003aa2c` sums only
`gp-0x6ade + gp-0x6b4c + gp-0x6b62` and **drops `gp-0x6ad4` (all of Path 2) and `FUN_00036682`**.
Already recorded as *"PROVABLY always 0"*; **re-derived here independently** —
✅ **OPEN.**

**GATE B — `gp-0x67ab`, the `gp-0x6ad6` term gate. THIS IS THE ONE THE RECORD LEFT OPEN**
(`HANDOFF-2026-07-27:287`: *"OPEN: `gp-0x67ab`'s trigger … producer untraced"*). When it is 1,
`FUN_00037fe6` skips the whole 7-term block ⇒ **`gp-0x6b70` never reaches `gp-0x6ad6` at all**, and
the car still has full assist (term 0 `gp-0x6b4a` and `FUN_00036682` are outside the gate) ⇒ **it
would have been completely invisible.**

Census (Ghidra ∖ Python set-difference **EMPTY**, with the `ld.bu` parity trap decoded by hand:
`op6=0x3d` ⇒ odd disp `0x9855` = `-0x67ab`, `op6=0x3c` ⇒ even disp `0x9854` = `-0x67ac`):
**2 readers (`0x2774c`, `0x37fe6`) / 1 writer (`0x2775c`).**

The writer's producer, traced to the byte:

```
; FUN_00026c80, inside the 11-slot loop (i = r15 = 0..10 ; r9 walks tp+0x5124 = 0xC4124)
00027282  cmp   r0,r25                 ; r25 = the STICKY flag from the previous slot
00027286  bne   0x272ba                ;   once set, stays set
00027288  ld.bu 0x0,r9,r12             ; role = roleTable[0xC4124 + i]
0002728c  cmp   0x2,r12 / setfe r11    ; role == 2 ?
00027292  cmp   0x3,r12 / setfe r10    ; role == 3 ?
00027298  cmp   0x4,r12 / setfe r12    ; role == 4 ?
0002729e  cmp   r0,r11 / bne 0x272aa
000272a2  cmp   r0,r10 / bne 0x272aa
000272a6  cmp   r0,r12 / be  0x272be   ; role NOT in {2,3,4}  ->  r10 = 0
000272aa  ep = gp-0x6170 + i ; sld.bu -> r12 ; setfne r10     ; else: r10 = (gp-0x6170[i] != 0)
000272c0  cmp   r0,r10 / 000272c6 setfne r25                  ; new sticky value
000272ce  mov   r10,r11                ; -> 00027328 st.w r11,-0x3d94  -> 0002775c st.b -> gp-0x67ab
```

⇒ **`gp-0x67ab` = STICKY-OR over i∈[0,10] of ( `roleTable[i] ∈ {2,3,4}` AND `gp-0x6170[i] ≠ 0` ).**

```
0xC4124 (11 bytes, read LE from the stock image) = 00 00 05 00 05 05 00 00 00 05 00
                                                   ^^ no 2, no 3, no 4, anywhere
```
⇒ ✅ **`gp-0x67ab ≡ 0` STRUCTURALLY, on a static calibration byte that
`HANDOFF-2026-08-05` records as byte-identical across all 65 built images. THE GATE IS OPEN.**
**[EVIDENCE — decompile + hand-decoded disassembly + raw LE table read.]**

⊕ **This also retires V86's `b4` as evidence.** V86's rung was `gp-0x67ab < 2` and measured
**duty 1.0000**, reported in `BUILD-LINEAGE.md` as part of *"lever in force three ways."*
🛑 **`< 2` is satisfied by BOTH the open state (0) and the closed state (1) — the rung could not
have distinguished them.** It is the design law's own failure mode: a single threshold rung on a
quantity with no measured distribution. The gate is open, but **V86's probe is not why we know it.**

⚠ Discrepancy recorded, not resolved: `HANDOFF-2026-08-05` gives `gp-0x67ac`'s trigger role set as
**{6,7}**; my decode of the sibling block at `0x27248` reads **{2,3,4}**. Both conclusions are
`≡ 0` on this table, so nothing decision-bearing turns on it, but one of the two is wrong.

### ⇒ STATIC VERDICT

> **Path 2 controls ~0.25 counts of aggregator command per count of `gp-0x6b70`, at 6–9 Hz, with
> ~0° net phase, through a chain in which every single link is unity, an enable byte set to 1, a
> flat LERP, or the PID itself. There is no dilution anywhere.** [EVIDENCE]

Contrast with the record's *"Path 1: unity, 0°, unconditional."* Path 2 is **not** unity — it is
**0.25** — but 0.25 with 0° phase, on a signal running to thousands of counts, is not a lane that
can be dismissed. **The `≤ 9 %` retraction was right, and the correct replacement is not "small".**

---

## 2b. EMPIRICAL — route `0x81` (V98)

`427 = clamp(|gp-0x6b70| * 5 >> 6, 0, 0x3FF)` ⇒ `|gp-0x6b70| = code × 12.8`; sign from `0x14A`
byte4 b7. Engagement from `cc_lat` (`cs_eng` is dead in `_scratch/cache/r81`). Pairing asserted
elementwise (`raw14_b4[row2raw14] == probe`), so a mispairing kills the run.

```
427: 251 distinct codes, p50 98, p99 238, max 251, ==1023 duty 0.000000
|gp-0x6b70|: p50 1,254 ct   p99 3,046 ct        (clamp is +-8192 -> 0.000 % saturation)
```

### ⭐ FIRST, THE CONTROL — and it changed the answer

`scorer-v98` reports 427 is broadband-elevated engaged, **4.14× even in the 35–45 Hz negative
control**, and concluded that this blocks band-specific claims. **That control band is invalid.**

427 is transmitted at **49.835 Hz** (Nyquist 24.92 Hz) and ZOH'd onto the 101.26 Hz row grid.
A ZOH replicates the baseband at multiples of the transmit rate, so **5–15 Hz lands at
50−(5..15) = 35–45 Hz.** Synthetic positive control — a **pure 7.79 Hz tone**, tx-sampled then
ZOH'd exactly as the pipeline does:

| band | RMS of a signal containing ONLY 7.79 Hz |
|---|---|
| 6–9 Hz | 0.6795 |
| 20–24 Hz | 0.0135 |
| **35–45 Hz** | **0.1631** ← 24 % of the true band, out of nothing |

⇒ **the 35–45 Hz reading on the 427 lane is a MIRROR OF THE SYMPTOM BAND.** A valid negative
control for this lane must sit **inside 0–25 Hz**.

Re-run against the within-drive LKAS-off arm (seg 2, the operator's own demonstration):

| band | `gp-0x6b70` eng/off | column torque eng/off |
|---|---|---|
| **6–9 SYMPTOM** | **17.12×** | **12.67×** |
| 15–22 (grind #1) | 8.62× | 6.05× |
| **20–24 NEG CTL (valid)** | **7.45×** | 6.43× |
| 0.5–3 (authority null) | 1.14× | 1.15× |
| 35–45 (INVALID — ZOH image) | 9.24× | 1.25× |

⇒ 6–9 Hz excess over a **valid** control: **2.30×** on `gp-0x6b70`, **1.97×** on the column
torque. The two agree. The engaged elevation *is* partly broadband (6–24 Hz) in the column torque
too, so this supports a band contrast but not causation.

### The delivered-counts figure

```
gp-0x6b70, 6-9 Hz RMS, engaged                        =  548.3 counts
x d(gp-0x6b94)/d(gp-0x6b70) = 0.2565                  =  140.6 counts RMS into gp-0x6b94
   as a fraction of the aggregator clamp (+-10240)    =    1.37 %
   vs V87's gp-0x6b98 engaged median 208 ct           =   67.6 %   [cross-build, order-of-magnitude only]
```

🛑 **The 67.6 % is a SCALE COMPARISON, not a share.** V87's 208 ct is a broadband median of a
different cell on a different build. What it establishes is only that Path-2's 6–9 Hz injection is
**the same order as the delivered command**, not a rounding error. **[EVIDENCE for the 140.6;
BELIEF for the ratio.]**

### 🛑 A CONTROL THAT FAILED — reported, not buried

I attempted a within-engaged partial-Spearman between the 6–9 Hz log-envelopes of `gp-0x6b70` and
the column torque, controlling speed and |wheel rate|, block-permutation null. **It returns
ρ = 0.992 in the 6–9 Hz band — and ρ = 0.992 in the 0.5–3 Hz NULL band as well.** The test has no
band specificity: both envelopes track a common activity envelope. ⇒ **This route is dead. Do not
use envelope correlation on this pair.**

### ⇒ 🛑 THE ONE THING THAT COULD STILL MAKE PATH 2 INERT — and it is measurable

`FUN_0003a382` takes `feedback = clamp(gp-0x6ad6, ±tp+0x7200)` with **`0xC6200` = 8192**, while
`gp-0x6ad6` itself is clamped at **±25600**. **If `|gp-0x6ad6| > 8192`, the marginal gain from
`gp-0x6b70` is EXACTLY ZERO** — every factor above stays as computed and the lever still does
nothing. `gp-0x6ad6` is a **7-term sum**; `gp-0x6b70` (p99 3,046) is one term, and term 0
(`gp-0x6b4a`) alone has a ±25,600 window and *"can drive the reference to its rail"*
(`accord-gp6b4a-is-a-second-direct-lkas-term`).

**`gp-0x6ad6` HAS NEVER BEEN ON THE WIRE.** ⭐ **RECOMMENDED RUNG, and it is a comparator, so it
needs no scale assumption: `|gp-0x6ad6| ≥ 8192`.** Its duty *is* the answer. A companion
`|gp-0x6b70| ≥ |gp-0x6ad6|` ranks Path 2 against the reference it feeds, in one more rung.

---

# QUESTION 3 — IS THE PHANTOM REAL?

## The arithmetic: CORRECT [EVIDENCE, reproduced independently]

```
0xC40D0 = 408 / 4096 = 0.099609375        MODEL arm, friction-path pole    @0x3bb22
0xC63AC = 102 / 1024 = 0.099609375        ACTUAL arm, accumulator pole     @0x38202
408/4096 == 102/1024  ->  True            (408 = 4*102 ; 4096 = 4*1024)
|H(150/1024) - H(102/1024)| = 0.1109 / 0.1362 / 0.1506  at 6 / 7.79 / 9 Hz
```
All four numbers reproduce exactly.

## The assumption: **IT FAILS, THREE INDEPENDENT WAYS**
*(A fourth argument appeared here in the first draft and is **WITHDRAWN** — see the correction below.
Points 2–4 are each individually sufficient and are the ones that matter.)*

### 🛑 WITHDRAWN — my "it's just both being ≈0.1" argument. The bytes refute it.

First draft argued the bit-identity was uninformative because both cells are the same nominal 0.1
and *"any two cells set to ≈0.1 would look bit-identical to within 0.4 %."* **That is wrong, and my
own script's output contradicted the prose I wrote around it:**

```
round(0.1 * 1024) = 102     <- 0xC63AC stock IS 102.  Natural Q10 rounding.
round(0.1 * 4096) = 410     <- but 0xC40D0 is 408, NOT 410.  Off by 2 LSB.
4 * 102           = 408     <- exactly the Q12 image of the Q10 cell
410/4096 = 0.100097656  !=  102/1024      <- what INDEPENDENT "0.1 in Q12" would have produced
408/4096 = 0.099609375  ==  102/1024      <- what Honda actually shipped
```

⇒ **A designer independently targeting 0.1 in Q12 writes 410. Honda wrote 408.** The identity is
**not** explained by "both are ≈0.1"; it survives as *"one cell is exactly the other rescaled."*
**[EVIDENCE.]** ⇒ 🛑 **The bit-identity is probably DELIBERATE. What is refuted is its CONSEQUENCE,
by points 2–4 below — not the identity itself.**
⊕ Census, kept because it is a fact: `102` occurs **6×** in the `0xC4000` block and **12×** in
`0xC6000`; `408` occurs **once** in each. That `102` is common while `408` is unique is consistent
with 408 being derived from a 102, not typed independently.

**(2) THE ARMS DO NOT SHARE AN INPUT.** This is the decisive one. From `tracer-arms` §1.2/§1.3,
which I take as given and which my own reads are consistent with:
- **MODEL** (`gp-0x6bfe`) is the output of `FUN_0003b8f6`, a **plant model** — a float FIR
  identity, a Coulomb relay (`0xC40BC`), a friction magnitude (`0xC40D2` = V89), and a cascade of
  u16 IIRs.
- **ACTUAL** (`gp-0x374c`) is a **weighted sum of six physically distinct lanes** — `gp-0x6bd0`
  (damper seed), `gp-0x6bbe` (viscous + DC pedestal), `gp-0x6b46` (backlash servo), `gp-0x6b26`
  (inertia), `gp-0x6b4e` (≡ 0), `gp-0x6b4c` (LKAS command) — × polarity × 2639, then the pole.

**There is no common signal passing through both poles.** A "phantom disturbance appearing in the
difference when a common component fails to cancel" requires one; the structure does not provide
one. The phantom number is the answer to a question the firmware does not ask.

**(3) `0xC40D0` is not the MODEL arm's transfer — it is one stage on its FRICTION SUB-PATH**,
in series with `0xC40D4`×2, `0xC40D8`×2 and `0xC40D6`×2. The ACTUAL arm's transfer is `0xC63AC`
**alone**. Pairing them is pairing one stage of five against one of one.

**(4) With the rest of the chain included, STOCK IS NOT MATCHED — it is 84° apart.**

| f | MODEL main path | MODEL friction path | ACTUAL stock | ACTUAL V97 | **stock gap** | **V97 gap** |
|---|---|---|---|---|---|---|
| 6.00 | 0.687 ∠ −86.98° | 0.646 ∠ −105.68° | 0.941 ∠ −18.70° | 0.973 ∠ −12.34° | **−68.28°** | **−74.65°** |
| 7.79 | 0.557 ∠ −107.74° | 0.505 ∠ −131.37° | 0.906 ∠ −23.63° | 0.956 ∠ −15.81° | **−84.11°** | **−91.93°** |
| 9.00 | 0.478 ∠ −120.28° | 0.421 ∠ −147.01° | 0.880 ∠ −26.73° | 0.942 ∠ −18.07° | **−93.55°** | **−102.21°** |

The magnitudes are as mismatched as the phases (0.557 vs 0.906 at 7.79 Hz).

## ⇒ VERDICT ON Q3

🛑 **`§10`'s "STOCK ENCODES AN EXACT PHASE MATCH BETWEEN THE ARMS" is REFUTED — but not because the
match is accidental.** The match between the two **cells** is real and probably deliberate
(`408 = 4 × 102`, where an independent Q12 "0.1" would have been 410). What is refuted is that it
constitutes a match **between the ARMS**: it is an exact match between **two stages**, one of which
is one of five on a **sub-path**, on **two arms that are already 84° and 1.6× apart** and that
**do not share an input**.

✅ **What survives, and it is the part the V99 decision actually rests on:** V97 rotated the ACTUAL
arm **+7.82° at 7.79 Hz** and raised its magnitude **0.906 → 0.956 (+5.4 %)**, which moves the arms
**further apart, not closer**, on every one of the three frequencies. **The direction claim is
intact.** The *magnitude* of the claimed disturbance (0.111/0.136/0.151 "of a common signal") is
**not a real quantity** and should not be quoted.

## What would close it

The honest arm-to-arm transfer needs the **six lanes' own upstream dynamics** and **what feeds
`0xC40D4`**. Neither is in this trace. Two routes:

1. **Static** — trace each of the six lanes back to its source and price its transfer to
   `gp-0x374c`. Large; `gp-0x6bbe` and `gp-0x6b26` are already characterised in `memory/`, the
   other four are not.
2. ⭐ **Empirical, and far cheaper** — the arms are **already comparable per-frame on the wire**.
   V98's `b6` (`|gp-0x6bfe| ≥ |gp-0x374c>>4|`) gives their *ordering* at 0.4235 duty. **A cave
   that emits the SIGN of each arm separately** — `gp-0x6bfe < 0` and `(gp-0x374c>>4) < 0`, two
   rungs, both already proven buildable (`b4` is exactly the second one) — yields the **arm-to-arm
   phase directly from the cross-correlation of two sign sequences at 100 Hz**, with no scale
   assumption and no upstream trace. **That measurement would replace this entire section.**

---

# CONSEQUENCES FOR V99

- **"V99's `0xC63AC` revert would do nothing" is NOT supported.** Path 2 has ~0.25 authority at
  0° phase and carries 141 ct RMS at 6–9 Hz. Reverting the pole changes the ACTUAL arm's 7.79 Hz
  transfer by 5.4 % in magnitude and 7.8° in phase, on a residual that V98 shows is in the
  cancellation regime — where a small change in one arm is a **large fractional** change in the
  difference.
- **But its stated justification is refuted.** *"Restore the exact phase match stock designed"* is
  not a true description. The defensible justification is: **revert an unmeasured change on a lane
  that is now shown to be live and non-trivially authoritative, whose direction the phase budget
  says went the wrong way.** That is a good enough reason. It is a different reason.
- 🛑 **Before spending the build on the cal, consider spending the rungs on `|gp-0x6ad6| ≥ 8192`.**
  It is the one remaining structural way Path 2 could be inert, it is a comparator (no scale
  assumption), its duty *is* the answer, and it decides whether **every** Path-2 lever — V89's,
  V97's, and V99's — was ever able to reach the car.

---

## EVIDENCE / BELIEF ledger

| claim | grade | method |
|---|---|---|
| `d(gp-0x6b94)/d(gp-0x6b70)` = 0.253–0.262 at 6–9 Hz, ~0° | **EVIDENCE** | decompile of `0x37fe6`/`0x3a382`/`0x3aa2c` + LE cal reads + a positive control reproducing the record's independent 21 Hz figures to 3 s.f. |
| `gp-0x67ab ≡ 0` ⇒ the `gp-0x6ad6` gate is OPEN | **EVIDENCE** | hand-decoded sticky-OR at `0x27282`–`0x272ce` + role table `0xC4124` read LE |
| `gp-0x67ac ≡ 0` ⇒ `gp-0x6ad4` is in the aggregator sum | **EVIDENCE** | same table; independently recorded in `HANDOFF-2026-08-05` |
| V86's `b4` (`< 2`) cannot distinguish the two gate states | **EVIDENCE** | the rung's own threshold vs the gate's `== 1` condition |
| 427's 35–45 Hz control is a ZOH image | **EVIDENCE** | synthetic pure-tone positive control through the actual pipeline |
| 141 ct RMS into `gp-0x6b94` at 6–9 Hz engaged | **EVIDENCE** | route 81, asserted pairing, valid in-Nyquist control |
| "67.6 % of the delivered command" | **BELIEF** | cross-build, broadband denominator |
| `|gp-0x6ad6| > 8192` would zero Path 2 | **EVIDENCE** (mechanism) / **UNMEASURED** (whether it happens) | the clamp at `0x3a7f0`-ish, `tp+0x7200` = 8192 |
| The phantom's common-input assumption is false | **EVIDENCE** | the two arms' cal censuses are disjoint and describe different signals |
| `408/4096 == 102/1024` is deliberate, not accidental | **EVIDENCE** | an independent Q12 "0.1" is `round(0.1·4096)` = **410**; Honda shipped **408 = 4 × 102**. ⚠ **This CORRECTS a withdrawn first-draft claim of mine that it was "just both being ≈0.1"** |
| …but it is a match between two STAGES, not between the ARMS | **EVIDENCE** | `0xC40D0` is 1 of 5 poles on the MODEL arm's friction sub-path; `0xC63AC` is the ACTUAL arm's whole transfer |
| Stock arm-to-arm gap = 84.1° at 7.79 Hz | **EVIDENCE for the pole cascade; BELIEF for "arm-to-arm"** | it omits the six lanes' upstream dynamics — the same scope limit `tracer-arms` flagged |

---
---

# ADDENDUM — THE DOSE, IN COUNTS. AND ONE MECHANISM FOR BOTH NULLS.

Added after the orchestrator's redirect. This addendum **supersedes the parts of the sections above
that left the dose unpriced**, and it changes the conclusion — not about Path-2's *authority*, which
stands, but about V97's *lever* on it.

## 0. 🛑 ITEM D IS WITHDRAWN AS EVIDENCE — with a correction to the reconciliation itself

My Q1 report called `0xC63A0`'s four-flight null *"the strongest empirical prior"* on low Path-2
authority. **Withdrawn.** `arc-map`'s reconciliation is right and `STATE.md` §A6b's *"Unreconciled"*
is stale: the cell weights a lane that is arithmetically ~zero, so the null says nothing about
Path 2. **It must not be counted, and the stale line must not be re-cited a third time.**

⚠ **But the relayed reconciliation has the wrong lane, and that error is worth catching before it
enters the record.** Per `traces/TRACE-2026-08-13-v99-arm-levers.md` §1.3, read against the `0x38148`
decompile:

| cell | lane it weights | status |
|---|---|---|
| **`0xC63A0`** | **`gp-0x6bd0`** | *"seed / damper-presence — **measured ~0 on 87,940 frames**"*; V75's thermometer: L4 (≥448) = **0.000 %** of 28,317 engaged frames |
| `0xC63A6` | `gp-0x6b26` | INERTIA (−K·α) — this is the `gp-0x6b26` cell, and it is **not** the one that flew |

⇒ **The conclusion is unchanged and correct** (`0xC63A0` doubles a weight on a lane measured ~0);
**the mechanism is `gp-0x6bd0`, not `gp-0x6b26`, and not the FactorC×FactorE dead-zone product.**

⊕ Nothing in Q2's static bound ever rested on item D. That bound is independent.

## 1. ⭐⭐ THE MECHANISM — `f′` IS 6.3× SMALLER IN THE OPERATOR'S OWN REGIME

`gp-0x6b70 = sign(iVar6) · LERP(|iVar6|)`. **`f′ = dY/dX` is the exchange rate that converts a
residual perturbation into a delivered command change.** It is a *deterministic function of
`|iVar6|`* — no mask, no inference, no model. Read from the mode-26 knots (speed-interpolated):

| `|iVar6|` (ct) | **f′** | knot interval |
|---|---|---|
| 0 – 178 | **2.539** | [0,178] → [0,452] |
| 178 – 356 | **2.174** | [178,356] → [452,839] |
| 356 – 719 | 1.496 | |
| 719 – 1200 | 0.948 | |
| 1200 – 1800 | 0.488 | |
| **1800 – 3000** | **0.346** | [1800,3000] → [2131,2546] |
| 3000 – 5000 | 0.248 | |
| 5000 – 10681 | 0.212 | |

**`f′` falls 2.54 → 0.21 across the range — a 12× compression.**

Now, where does the car sit? Route `0x81`, engaged, **two masks, both reported**
(`memory/reference-accord-steeringpressed-mask-excludes-the-symptom-regime` warns `steeringPressed`
is a threshold on `|cs_tq|`, so its own D3 fix — window-median `|cs_tq| < 1200` — is run alongside):

| | `steeringPressed` mask | D3 mask (the memory's fix) |
|---|---|---|
| n on / off | 2,198 / 4,393 | 898 / 5,693 |
| **`|iVar6|` p50, hands-ON** | **2,829 ct** | **2,818 ct** |
| **`|iVar6|` p50, hands-OFF** | **188 ct** | **337 ct** |
| **`f′` p50, hands-ON** | **0.346** | **0.346** |
| **`f′` p50, hands-OFF** | **2.174** | **2.137** |
| **ratio** | **0.159×** | **0.162×** |

🛑 **THE TWO MASKS AGREE TO 2 %.** The result is not a mask artefact.

> ⭐ **LIVE-9(a) IS NOT A HYPOTHESIS ANY MORE. IT IS A MEASURED 6.3× COMPRESSION.**
> V97's direction and dose were argued on **hands-off engaged returns** (`|Q| = 1.233`, the LERP's
> steep region, `f′ ≈ 2.17`). The operator provokes the symptom **hands-on, overriding, at creep** —
> `|iVar6|` is **15× higher**, which puts him on the **flat** part of the same curve, `f′ = 0.346`.
> **The firmware desensitises this lane by 6.3× exactly when the driver pushes.** [EVIDENCE]

## 2. ⭐⭐ THE DOSE — "X ct of a Y ct signal", the figure the audit demanded

```
d(iVar6)     = |H(150) - H(102)| / |H(102)|  x  |ACTUAL_ac|   = 0.1502 x |ACTUAL_ac|
d(gp-0x6b70) = f'(regime) x d(iVar6)
d(gp-0x6b94) = 0.2565 x d(gp-0x6b70)                            [Q2a, this trace]
```
`|ACTUAL_ac|` (the 6–9 Hz AC of `gp-0x374c>>4`) is the one term still unmeasured; bracketed by the
regime's own `|iVar6_ac|` (arms roughly uncorrelated) and by **2048**, V96's hard measured ceiling
(`M ≡ 0` on 10,749/10,749 frames).

| regime | mask | `|ACTUAL_ac|` | **dose into `gp-0x6b94`, 6–9 Hz** |
|---|---|---|---|
| **hands-ON (THE SYMPTOM REGIME)** | press | own `iVar6_ac` = 267 ct | **3.55 ct RMS** |
| **hands-ON** | D3 | own `iVar6_ac` = 84 ct | **1.12 ct RMS** |
| **hands-ON** | either | **2048 ceiling** | **27.3 ct RMS** |
| hands-OFF (where the direction was argued) | press | own = 298 ct | 24.99 ct RMS |
| hands-OFF | either | 2048 ceiling | 171.6 ct RMS |

**Denominators**, both from this trace / the record:
- Path-2's **own** 6–9 Hz injection into `gp-0x6b94` = **140.6 ct RMS**
- V87's `gp-0x6b98` engaged median = 208 ct (broadband, cross-build — a scale, not a share)

> ### ⇒ **V97 CHANGED THE DELIVERED 6–9 Hz COMMAND BY 1.1–3.6 COUNTS RMS IN THE OPERATOR'S OWN REGIME — 0.8–2.5 % of Path-2's own output, ~1.7 % of the delivered command's scale.**
> Even at the 2048 ceiling — a bound so loose it assumes the ACTUAL arm's 6–9 Hz AC alone reaches
> the full measured envelope of the whole signal — it is **19 %**.

## 3. THE PERCEPTUAL CALIBRATION — the "underivable" step, turned into an interpolation

| build | delivered in-band change, **measured** | the operator's own words | felt? |
|---|---|---|---|
| V62 | 18–22 Hz down **8–42×** | *"Original grinding at 2–5 mph is gone!"* | ✅ |
| V88 | 15–22 Hz command **0.549 [0.407, 0.844]** | *"grinding fixed"* | ✅ |
| V86B | damper armed | *"extra dampening on LKAS and in general at slow speed"* | ✅ |
| V94 | motor accel **3–7× up** above 9 Hz | *"worse by a lot… not safe to drive"* | ✅ (aborted) |
| V85 | 6–9 Hz **1.088 [0.746, 1.451]** | *"barely, perceptibly better (somewhat unsure)"* | ~✗ |
| V86 | ~8 Hz ratio **1.001 [0.976, 1.060]** | *"maybe a smidge, if at all"* | ✗ |
| V89 | stratum contrast **0.947 [0.827, 0.979]** | *"fixed nothing"* | ✗ |

⇒ **THE BRACKET: an in-band delivered change of ~0.55× (−45 %) IS felt. ~1.09× (+9 %) IS NOT.**

**V97's 0.8–2.5 % sits an order of magnitude below the smallest change he has ever failed to
notice**, and ~20× below the smallest he has ever noticed. **The felt-null needs no further
mechanism.** [EVIDENCE for the dose and the bracket; **BELIEF** that a linear interpolation across
different symptoms and bands is the right perceptual model — it is a bracket, not a law.]

## 4. ⭐ LIVE-8 — THE ASYMMETRY, BOTH SIDES, AS THE ORCHESTRATOR ASKED

`builds/v80_v107/build_v97_tva.py:65-67`, verbatim:
> *"Path 1 is unweighted and unaffected by A, which **dilutes** the figure to **+2 % .. +13 % on the
> TOTAL command** at A=150 — worst case 1.13 × 0.549 = 0.620, still inside V88's measured CI."*

**That dilution was computed, and used, to argue the COST was acceptable.** The identical dilution
applies to the BENEFIT. **And it is worse than symmetric**, because the benefit takes a *second*
division the cost does not:

```
COST   side, as argued : 21 Hz throughput +23.4%  ->  diluted by Path-1 share  ->  +2%..+13%   [STATED]
BENEFIT side, unstated : same Path-1 dilution
                         x  f'(hands-off 2.17 -> hands-on 0.346) = a further 6.3x        [NEVER STATED]
                       ->  1.1-3.6 ct RMS = 0.8-2.5% of Path-2's own 6-9 Hz output
```
🛑 **The build priced its cost in the regime where the number is flattering and never priced its
benefit at all.** This is the T5 class that killed `0xC63A4` at 1.1 ct of 342 — and here the figure
is **1.1–3.6 ct of 141**. [EVIDENCE for both sides; the asymmetry is a fact about the document.]

## 5. ⭐⭐ ONE MECHANISM FOR BOTH NULLS — and this one survives V98

The arm-inequality story explained V89 and V97 together and **V98 killed it** (`b6` duty 0.4235 ⇒
the arms are comparable). Here is a replacement that **predicts V98's result rather than
contradicting it**:

> **Both V89 and V97 perturb `iVar6`. Every perturbation of `iVar6` reaches the car through `f′`.
> In the operator's symptom regime `f′` is 0.346 — 6.3× down from where both levers' directions
> were argued, and 7.3× down from the curve's steep region. The residual is not small (V98 is right
> — 288 ct RMS at 6–9 Hz); the *slope that carries changes in it* is.**

This is consistent with **every** measurement on the table: V98's comparable arms, V96/V97/V98's
lively 427 lane, V89's flat stratum contrast, and V97's felt-null. It requires nothing unmeasured.
[**BELIEF** — a mechanism that fits all the data, not a tested prediction. The test is §7.]

## 6. 🛑 WHAT THIS MEANS FOR V99 — **DO NOT FLY THE `0xC63AC` REVERT AS A FIX**

`|H(102) − H(150)|` is **the same number in both directions.** V99's revert therefore delivers
**the same 1.1–3.6 ct RMS**, in the same regime, on the same flat part of the same curve.

- ✅ **Path 2 has real authority (0.2565) — that stands, and the "Path 2 may have little authority"
  hypothesis is REFUTED as stated.**
- 🛑 **But the conclusion about V99 is CORRECT, for a different reason: the LEVER's dose is tiny in
  the regime that matters, because of `f′`, not because of the path.** *"Path 2 is weak"* is wrong;
  *"`0xC63AC` is a weak lever where he drives"* is right.
- ⇒ **Flying V99 as a fix spends a drive on a change ~20× below the perceptual bracket.** If it is
  flown, it must be flown as a **revert-to-stock hygiene step carried on a build whose real content
  is something else**, and pre-registered as *expected to be felt as nothing.*

## 7. ⇒ WHAT TO BUILD INSTEAD — the lever is `f′`, not the pole

🛑🛑 **CANDIDATE 1 BELOW IS NOW NO-GO — CORRECTED 2026-08-13 (later), record-repair pass. This
section used to recommend `0xC63AE` as the lead V100 candidate; do not build it.** `tracer-c63ae`
(crux verified by the team lead) found that **the AC gain through this cell is NON-MONOTONE in scale
and REVERSES SIGN across the operator's own amplitude distribution**: at scale 1536 the ratio is
0.773 at p10, 1.078 at p50, 1.277 at p90 — a gain that RISES with amplitude, the hardening
nonlinearity that sets up a limit cycle (V80 class). **1280 is arithmetically WORSE than stock.**
RULE 7 does pass (no mode-index failure mode here), but that is not sufficient. **This section's own
"+41% dose for one byte" framing at scale 512 is a LEVEL-shift argument only — it did not check the
AC-gain reversal, which is the actual gate.** See `docs/BUILD-LINEAGE.md`'s `0xC63AE` row for the
full correction. Candidate 2 is unaffected by this.

The 12× compression **is** the lever. Two candidates, in order:

1. ⭐ ~~`0xC63AE` = 1024, the LERP index scale~~ **NO-GO, see the correction above.** (`idx =
   (|iVar6|·scale)>>10`; **1 reader, 0 writers**; `tracer-arms` §4.1 already named it *"the one
   arm-agnostic lever"*). It moves **where on the curve the car sits.** Halving it to 512 maps
   `|iVar6|` p50 2,829 → index 1,415, i.e. `f′` 0.346 → 0.488 — **+41 % dose for one byte** — and
   unlike the pole it acts on **both** arms' contributions equally. 🛑 **`0xC63AE` must never go to
   0** (recorded flatten-into-a-relay hazard) and the LERP knots are **mode-indexed ⇒ RULE 7
   applies** (RULE 7 itself passes; the AC-gain reversal is the reason this is still NO-GO).
2. **The knots themselves** — raising `Y` in the 1800–3000 interval steepens `f′` exactly in the
   override regime. Bigger blast radius; mode-indexed; needs its own trace.

**And the instrument that decides all of it, still: `|gp-0x6ad6| ≥ 8192`** (§2b). If that clamp
saturates, `f′` is moot and the whole path is marginally dead. **Two comparator rungs — that one, and
`gp-0x6bfe < 0` / `(gp-0x374c>>4) < 0` for the arm phase — answer the three open questions in this
document with no scale assumption.**

## 8. ⚠ CARRIED FORWARD, AS THE ORCHESTRATOR ASKED

🛑 **`b5` = 0.0000 does NOT license "REQUEST is minor."** It licenses only `|REQUEST| < |ACTUAL|`.
The denominator for "minor" is the **RESIDUAL** — measured here at **288 ct RMS (6–9 Hz), `|iVar6|`
p50 389 ct engaged** — against which a REQUEST arm smaller than an ACTUAL arm bounded only by 2048
can still be several times larger. **The REQUEST arm is OPEN, it carries the LKAS + driver demand
path, and our own 4× gain `0xC6CD0` feeds it.** `tracer-arms`: zero calibration cells, and
shadow-lockstep protected against code edits. ⇒ **With Path-2 authority now established at 0.2565,
REQUEST is the most important unmeasured term in the chain.**

⚠ **Residual uncertainties in this addendum, stated:** `|ACTUAL_ac|` is bracketed, not measured; the
perceptual bracket interpolates across different symptoms and bands; the LERP knots are the mode-26
pair recorded in `STATE.md`, speed-interpolated linearly (the firmware's own schedule between
records was not re-derived); and every gain here is **linear small-signal** — the PID's anti-windup
and `FUN_00036682`'s hysteresis are not described-function analysed, exactly as `builds/v80_v107/build_v97_tva.py`
itself conceded.

---
---

# ADDENDUM 2 — V99's ACTUAL LEVER (`0xC40BC` 600 → 300), AND A CORRECTION TO MY OWN `0xC63AE` ADVICE

The first addendum priced `0xC63AC`. **That is V99's base hygiene, not its lever.** This one prices
`0xC40BC` on the identical machinery, and corrects an error in the recommendation I made at the end
of Addendum 1.

## 1. 🛑 THE DECISIVE NUMBER — 92.8 % OF HIS OWN REGIME IS ABOVE THE KNEE, WHERE THE LEVER IS ARITHMETICALLY IDENTICAL

```
ramp     = clamp(polarity * gp_0x6abc * 12 / norm, -1, +1)          @0x3bad0..0x3bae4
friction = ramp*(K1/1024)*|fVar18| + ramp*(K0/1024)                 @0x3bb16   K0 = 0xC4080 = 0
knee     = (norm/12) / 4.7121  column deg/s        [arc-map's own basis; its 9.4%-at-1 deg/s worked example]
           norm=600 -> 10.61 deg/s        norm=300 -> 5.31 deg/s
```
| `|rate|` | effect of 600 → 300 |
|---|---|
| **< 5.31 °/s** | ramp **exactly 2×** |
| 5.31 – 10.61 °/s | tapers 2× → 1× |
| **≥ 10.61 °/s** | both rails at ±1 ⇒ **ARITHMETICALLY IDENTICAL. INERT.** |

Route `0x81`, `|steeringRateDeg|`:

| stratum | n | p50 | p90 | **< 5.31** | 5.3–10.6 | **≥ 10.61 (INERT)** | **mean ramp ratio** |
|---|---|---|---|---|---|---|---|
| ENGAGED all | 6,591 | 25.0 | 125.0 | 15.2 % | 7.1 % | **77.6 %** | **1.150** |
| **ENGAGED hands-ON (press)** | 2,198 | **83.0** | 196.0 | **4.5 %** | 2.7 % | **92.8 %** | **1.048** |
| **ENGAGED hands-ON (D3)** | 898 | 42.0 | 203.0 | 10.4 % | 8.7 % | **81.0 %** | **1.117** |
| ENGAGED hands-OFF (press) | 4,393 | 19.0 | 38.0 | 20.6 % | 9.4 % | 70.0 % | 1.201 |

🛑 **The lever is not a 2×. In the operator's own hands-on regime it is a ×1.05 – ×1.12.**

⊕ **The scale caveat is ONE-DIRECTIONAL, so the verdict is robust.** `gp-0x6abc` is motor rate and
I used the kit's own **4.7121 ct/(column °/s)** basis (`arc-map` line 292; `tracer-arms` §8.2's knee
table uses it explicitly). **If the true motor-referred scale is larger, the knee in column °/s is
LOWER, so MORE frames sit above it and the lever is MORE inert — never less.** [EVIDENCE for the
distribution; the basis is inherited and flagged.]

## 2. THE DOSE, IN COUNTS — same chain, same denominators

**V89's own probe is the hard ceiling on `friction`** (`gp-0x6ae2` = friction × 1024, 782 engaged s):
`|friction| ≥ 0.0625` on **0.000** of frames below 1 °/s and **0.009** of the 1–13 °/s micro regime
⇒ **`friction` < 0.0625 on 99.1 % of the micro regime — with `K1` ALREADY AT 204** (V89, on the car).

`Δfriction = friction × (ramp_ratio − 1)` → `ΔMODEL = 2639 × Δfriction` → `Δ(iVar6)` (coefficient
+1) → `× f′ = 0.346` → `× 0.2565`:

| stratum | ramp ratio | `Δfriction` < | `ΔMODEL` < | `Δ(gp-0x6b94)` < | **% of Path-2's 140.6 ct** |
|---|---|---|---|---|---|
| **hands-ON (press)** | 1.048 | 0.0030 | 7.9 ct | **0.7 ct RMS** | **0.5 %** |
| **hands-ON (D3)** | 1.117 | 0.0073 | 19.2 ct | **1.7 ct RMS** | **1.2 %** |
| hands-OFF (press) | 1.201 | 0.0126 | 33.1 ct | 2.9 ct RMS | 2.1 % |

## 3. ⭐⭐ AND THE STRUCTURAL ARGUMENT THAT SETTLES IT WITHOUT ANY OF THE ABOVE

```
friction = |fVar18| * ramp * K1/1024
                      ^^^^      ^^
                   0xC40BC    0xC40D2  = V89
```
**`0xC40BC` and V89's `0xC40D2` are two factors of the SAME PRODUCT, in the same term, on the same
arm.** They are not different levers; they are the same lever reached from two sides.

| | multiplicative step on `friction` | where | result |
|---|---|---|---|
| **V89** | **×2.000** | **every rate, unconditionally** | 🛑 **MEASURED FLAT** — 0.947 [0.827, 0.979] inside a same-build placebo band [0.900, 1.111] = **0.92 σ**; operator: *"fixed nothing"* |
| **V99** | **×1.048** (press) / ×1.117 (D3) | **only below 10.61 °/s** | — |

> ### ⇒ **V99's ABSOLUTE PERTURBATION IS 0.096× V89's. It is a TEN-TIMES-WEAKER version of a lever that already measured flat against a well-powered placebo control, on the same product, in the same term.**

⚠ **The compounding you raised is real but it cuts the other way.** Yes, `0xC40BC` multiplies with
V89's `K1` = 204, so below 5.31 °/s the on-car dose is 4× Honda. **But only 4.5 % of his hands-on
frames are below 5.31 °/s**, and the friction ceiling that matters is the one measured **at K1 = 204
already** — 0.0625 — not a stock-referred one.

## 4. ⇒ VERDICT ON `0xC40BC`, IN THE FORM REQUESTED

> **0.7 – 1.7 ct RMS = 0.5 – 1.2 % of Path-2's own 6–9 Hz output, against a perceptual floor of +9 %.**
> **BELOW THE BRACKET BY 8–18×, and *lower* than `0xC63AC`'s 0.8–2.5 %.**

🛑 **Both of V99's cells are below the perceptual bracket. Neither is worth a drive as a fix.**
The honest pre-registration for V99, if it flies at all, is: **expected to be felt as nothing, on
both cells** — flown as revert-to-stock hygiene plus a rate-window nudge, carried on a build whose
real content is an instrument.

⊕ **What is NOT wrong with `0xC40BC`.** Its **direction** is well supported — V85's 600 → 6000 moved
the knee out of the symptom regime and the ratchet got **worse** (2.89× → 6.58×, contrast +0.682
[+0.213, +1.166]), and driver grip damps the same band. *More* modelled friction in the regime is
the right direction. **The problem is dose, not sign.** ⇒ If this lever is to be used, it needs a
value whose knee sits **above** his actual rate distribution — and at p50 83 °/s and p90 196 °/s,
that means `norm` of order **4,700–11,000**, not 300. 🛑 **That is V85's direction (6000), which flew
and was WORSE.** ⇒ **The two constraints are in direct conflict, and `0xC40BC` cannot satisfy both.**
[EVIDENCE for both legs; the conflict is the finding.]

## 5. 🛑 CORRECTION — MY OWN `0xC63AE` RECOMMENDATION WAS WRONG IN DIRECTION

At the end of Addendum 1 I wrote: *"1024 → 512 maps `|iVar6|` p50 2,829 → index 1,415, i.e. `f′`
0.346 → 0.488, +41 % dose for one byte."* **That is wrong. I priced the slope and forgot that the
same scale divides the input.**

```
idx = (|iVar6| * scale) >> 10
d(gp-0x6b70)/d(iVar6) = (scale/1024) * LERP'(idx)      <-- the scale is in the chain TWICE
```
Evaluated over route 81's engaged hands-on frames (n = 2,198, `|iVar6|` p50 2,829):

| `0xC63AE` | scale/1024 | median LERP′ | **effective gain** | vs stock |
|---|---|---|---|---|
| 512 | 0.500 | 0.488 | 0.2440 | **0.71× — WORSE** |
| 768 | 0.750 | 0.347 | 0.2603 | 0.75× |
| **1024 (stock)** | 1.000 | 0.346 | **0.3458** | — |
| 1536 | 1.500 | 0.247 | 0.3701 | 1.07× |
| **2048** | 2.000 | 0.212 | **0.4232** | **1.22×** |
| 3072 | 3.000 | 0.212 | 0.6347 | 1.84× |

⇒ **The direction is UP, not down**, and the gain is **+22 % at 2048**, not +41 % at 512.

⭐ **But the more interesting thing is what I also missed: `0xC63AE` is not a slope knob — it moves
the STANDING OUTPUT of the whole lane.** Median `|gp-0x6b70|` would go **2,470 → 3,162 ct** at
scale 2048 (+28 %). Through the measured 0.2565 authority that is **≈ +177 ct** in `gp-0x6b94` —
**above the perceptual bracket**, and the only candidate examined today that is. **`0xC63AE` is a
real lever with a real dose.** It is also therefore a real risk.

### 🛑 Its hazards, stated
- **NEVER 0** — recorded flatten-into-a-relay hazard (`accord-plant-model-residual-aggregator-chain`).
- 🛑 **NEVER far ABOVE ~2048 either, and this is a NEW hazard I am adding.** At 4096 the median
  frame's index (11,316) lands in the table's **final segment** `[10681, 14490] → [4245, 8192]`,
  which ramps straight into the **±8192 clamp**; `|iVar6|` max 5,560 → index 22,240 is **past
  `X[9]` and pins at 8,192**. **A clamped output IS a relay — the V80 class.** The apparent "12×"
  at 4096 is that saturation ramp, not usable gain. **Do not read it as a dose.**
- 🛑 **RULE 7 — the knots are MODE-INDEXED and the mode proof has NOT been done.**
  `decompile_function(0x382d8)` is the required step and nobody has run it. Every mode-indexed lever
  this kit ever flew was inert.
- ⚠ It raises the **driver-feel reference** `gp-0x6ad6`, so the predictable cost is **changed
  steering weight** — the V86B *"extra dampening… at slow speed"* class, which the operator **felt**.
  That cuts both ways: it is a real cost, and it is also evidence the dose is in a felt range.
- ⚠ And it is **still gated by the `|gp-0x6ad6| ≥ 8192` question** (§2b of the main trace). Raising
  `gp-0x6b70` pushes `gp-0x6ad6` *toward* that clamp. **If the clamp is already saturating, raising
  `0xC63AE` buys nothing and may buy less than nothing.** ⇒ **The comparator rung should precede
  this lever, not follow it.**
- 🛑🛑 **NEW, DECISIVE HAZARD — added 2026-08-13 (later), record-repair pass, from `tracer-c63ae`
  (crux verified by the team lead): RULE 7 actually PASSES here** (unconditional bare-`tp` scalar
  read at `0x38242`, no mode index — the concern above was misplaced) **but the AC gain through this
  cell is NON-MONOTONE IN SCALE and REVERSES SIGN across the operator's own amplitude distribution.**
  At scale 1536 (a milder dose than 2048): ratio 0.773 at p10, 1.078 at p50, 1.277 at p90 — the gain
  RISES with amplitude, the hardening nonlinearity that sets up a limit cycle, V80 class. **1280 is
  arithmetically WORSE than stock.** The table below's "median LERP′" analysis priced only the
  MEDIAN operating point and missed that the same scale's effect on the tails is not proportional and
  not even same-signed. **This supersedes the "real dose, above the floor" verdict — see the updated
  table below.**

## 6. WHERE THIS LEAVES THE SESSION

| lever | dose in his regime | vs +9 % floor | verdict |
|---|---|---|---|
| `0xC63AC` 150→102 (V99 hygiene) | 0.8–2.5 % | **below** | not a fix |
| `0xC40BC` 600→300 (V99 lever) | **0.5–1.2 %** | **below** | not a fix; and its direction conflicts with V85's flight |
| ~~`0xC63AE` 1024→2048~~ | ≈ +28 % on the lane (median only) | **above at median** | 🛑🛑 **NO-GO — CORRECTED 2026-08-13 (later): AC gain is non-monotone and reverses sign across the amplitude distribution (see the hazard above). Do not build. `docs/BUILD-LINEAGE.md`'s `0xC63AE` row carries the full correction.** |
| `\|gp-0x6ad6\| ≥ 8192` rung | n/a (instrument) | n/a | ⭐ decides all three |
