# ADV "bytes+instrument" vs V295 candidate A (robust-joint): b at 0xC63EA, 567 → 1106

**Verdict: SURVIVES_WITH_CHANGES.**

Adversary subagent, 2026-09-30. Design phase only.
- Nothing was built, flashed or sent, and no CAN traffic was generated.
- No image or `.rwd` was written. The candidate image existed only in memory, to count its bytes and re-run the CRC chain.
- No fork, firmware-repo, STATE, memory, lineage or golden-model file was touched. Nothing was committed.

The FAIL criteria were written before any computation: `adv_bytes/ADV-bytes-robust-joint-CRITERIA.md`. Scripts and outputs
are in `adv_bytes/`.

Every decision-bearing claim is marked **[E]** EVIDENCE (with its method) or **[B]** BELIEF. Every number was
re-derived from the V294 **image** (sha256 `3143616d…dbdd85`, re-hashed) on **my own integer lane**
(`ab2_lane.py`, written from the Ghidra decompile of FUN_00028ea6 on the V294 program). That lane was then
checked against two other implementations:
- the golden model, with 0 mismatches in 80,000 random ticks including bails and restarts;
- plib's route march, bit-identical on 1,020,390 r71b ticks.

---

## 0. Bottom line

**Nothing in the bytes breaks the candidate.**
- The cell has exactly one reader, and it sits in the LKAS PID.
- The int32 margin is 2.081, the one b-dependent product.
- The delivered surface is bit-identical to V294's at 482 idx×sign cells × 5 wheel rates.
- The rail and the zero-command cap are unchanged.
- The edit changes 6 bytes: 2 cal bytes plus the 4-byte trailer of the CRC block that V294 already re-CRC'd and flew.
- The changed value is visible on the existing wire. On r71b's own excitation, **every** 15 s engaged window
  separates b 1106 from V294 (0/49 errors). So does every symptomatic ±10 s hard-turn window (0/15).

**Four things must change before this is offered for flashing. None of them is a reason to reject the cell value.**

1. **H-SAFE-3, the constraint the design calls binding, was checked at ONE operating point [E].**
   - The design reads 283 T at zero command, against a 288 cap (2 × V294's 144).
   - Over demand index × sign × rate sign, at 100 deg/s, A reaches **301 T** (idx 238). It exceeds 288 in **6 of 28** cells.
   - At the same operating point A reaches **2.04 ×** V294 (idx 180: 133 → 271 T).
   - Only the worst-case-vs-worst-case reading passes: 301 / 165 = 1.82.
   - **b ≤ 1050 passes all three readings** (287 T, 1.93×, 1.74×).
   - The orchestrator must either state which reading was pre-registered, or cut b to ≤ 1050.
   - This is fault path only: a filter bail on an implausible bar, an invalid polarity, or |x| > 12000.
2. **The null sentence's symptom clause is not licensed by one short drive [E].**
   - The 1.6–3 Hz hard-turn wheel-rate band has a no-change scatter of ×0.78–1.26 with 15 s of hard frames, and
     ×0.83–1.19 with 30 s (block bootstrap on r71b). Drive against drive the scatter is ×0.71–1.42.
   - Event to event, with no change, one event against another spreads ×0.28–3.6 (90 %).
   - The design's own prediction is ×0.83 nominal (×0.68–0.93 over the family). It sits inside that scatter.
   - The design's own identified world also puts the drive's 1–3 Hz hard-turn motion at about 94 % disturbance.
   - So an unchanged band, or an unchanged "jerky", is expected under **both** hypotheses. It cannot license
     "EPS-side damping at 1–5 Hz does not limit that symptom".
   - The clause "no further trim in the cal space will" is also false. b is cal-only up to 2301 (int32 margin
     1.0); the 2.0 cap is self-imposed.
3. **The sentence's literal acceptance bands leave a no-call gap on the CORRECT image [E].**
   - "c1 0.97–1.00 and c2 1.8–2.0" gives no call on 38 % of 15 s hands-off windows, 17 % of 30 s hands-off windows
     and 22–35 % of contiguous all-engaged windows. It never gives a wrong call.
   - A midpoint rule (c2 > 1.45 → b live) with c1 read against V294's own spread gives **0 errors** at ≥ 15 s.
4. **The stated risks leave out the driver-override resistance [E on r71b's recorded motion].**
   - On r71b's 92 s of hands-on engaged frames, the trim opposing the driver goes from p99 166 → **323 T** and max
     309 → **564 T**. The cap is 616 T, unchanged.
   - The design mentions only "slightly heavier" inertia below 2 Hz.

---

## 1. Pre-registered FAIL criteria, and what fired

| id | criterion (abridged) | result |
|---|---|---|
| A1 | cell ≠ 567 u16 at 0xC63EA, or wrong reader or width | **PASS**. `37 02` = 567. `ld.hu 0x73ea,tp,r16` @0x28F86 [E: Python read + V294 Ghidra listing, dry-run] |
| A2 | a second consumer of the cell | **PASS**. 1 reader (Python raw scan = Ghidra `search_instructions`, stock, 184,512 insns). Page-level readers are value-agnostic, §2.2 |
| A3 | int32 overflow or margin < 2.0 | **PASS**. Margin **2.081** (a·s). Every other product is b-independent |
| A4 | surface / rail / zero-command torque differs | **PASS**. 0 differences in 482 × 5; rail +2461/−2463; cap −616/+615 |
| A5 | restart pulse > 288 T at 100 deg/s, or mis-modelled | **FIRES on the literal reading**: 301 T worst case, 6/28 cells > 288, per-point ratio 2.04. The path is modelled correctly (fault path only) → required change 1 |
| A6 | DC bias from floors > 1 T | **PASS**. ≤ 0.13 T (telescoping: Σ r26 = s_end − s_start) |
| A7 / E1 | more than 2 cal bytes + CRC, or needs code | **PASS**. 6 bytes; bootloader walk 0 fails, full chain 0 fails |
| B1 / B2 | a new interlock reached, or a monitor reads what b scales | **PASS** [E topology; B semantics inherited, §4] |
| C1 / C2 | lineage mismatch, or the class already falsified | **PASS** on the values. Record gap: LEVER-INDEX row 33 stops at "V293 restores 923/1560". The "what is different" is dose only (§5) |
| D1 / D2 | b invisible, or needs more than one short drive | **PASS** at ≥ 15 s engaged; marginal at 5–10 s (§6) |
| D3 | c2 confounded | **PASS**, weak note. Only a pole or Kp change would move c2; c1 guards Kp |
| D4 | the null sentence licenses more than the instrument supports | **FIRES** → required changes 2 and 3 |

---

## 2. (a) Bytes

### 2.1 The cell and its reader

| check | result | method |
|---|---|---|
| image | sha256 `3143616d…dbdd85` **MATCH** | [E] Python (`ab1`) |
| the Ghidra V294 program is not stale | 0xC63E0–EF and 0x28F40–AF read back byte-equal to the file, incl. `89 d1` subr @0x28FA4 and `37 02` @0xC63EA | [E] `read_memory` vs Python |
| cells | a 1011, **b 567**, C 1024, lag 992/507, Ki 0, D clamp 0, Kd bank rec 7 all 0, Kp rec 7 [960]×5, P/sum clamps 15360, lane clamp 3072, gain 5346, shl imm 2, operand `subr` | [E] Python LE reads (`ab1`, `ab2`) |
| new value | 1106 = `52 04` LE, < 32768, so the u16/s16 question does not arise | [E] |
| structure | `ld.hu 0x73ea,tp,r16` @0x28F86 · `mul r16,r7,r0` @0x28F8E (low word of x·b) · `mul r26,r9,r0` @0x28F92 (low word of a·s) · `sar 0xa` ×2 · `add` · `subr r9,r26` @0x28FA4 · `st.w r9,-0x3d30` · clamp ±C @0x28FA6–0x28FBE | [E] decompile first (FUN_00028ea6 lines 69–99), then the dry-run listing |
| bails | skip unless \|bar gp-0x4f60\| ≤ 25600 AND pol ∈ {−1,0,1} AND \|x\| ≤ 12000 AND pol ≠ 0 (`0x2EE0 + x < 0x5DC1`) | [E] decompile line 69–71, listing 0x28F4C–0x28F62 |

### 2.2 Reader census: every byte of [0xC63EA, 0xC63EB] (`ab1`, `ab1b`, `ab1d`)

**Positive controls, 7/7 FOUND** before any null was read:
- b @0x28F86;
- a @0x28F8A;
- 6-byte gp-0x6752 @0x48E56;
- `mov imm32 0xCB994` @0x29DC6;
- C ×3;
- s @0x28F7C;
- gp-0x6a34 store @0x290CA.

The bit-op decoder found 20 gp bit-ops image-wide, and the branch scan found the control `jarl 0x22522 → FUN_00028ea6`.

Forms covered:
- 4-byte Format VII (incl. the ld.bu bit-5 parity and hw2 bit-0 discriminators);
- 6-byte Format XIV disp23;
- a word load at 0xC63E8 spanning a and b;
- LE32 absolutes in [0xC63E0, 0xC63EF];
- `mov imm32` in [0xC6000, 0xC63EB];
- movea/addi on tp;
- movhi 0xC + movea;
- ep/sld reach.

The image was scanned over [0x13000, 0x100000), which includes the 0xC4xxx caves.

| form | hits | adjudication |
|---|---|---|
| direct load/store of 0xC63EA/EB | **1**: 0x28F86 `ld.hu` | Ghidra `search_instructions "0x73ea"` on stock = **1** (0x28F86), and `"0x73e8"` = 1 — **Python = Ghidra** [E] |
| LE32 absolute 0xC63E0–EF | 0 | [E] |
| movea tp+0x7000 @0x140D2 | 1 | the tp set-up itself: tp = 0xB0000 + 0x7000 + 0x8000 = 0xBF000 [E: listing 0x140C0] |
| movea tp+0x7010 @0x3ADFC / 0x3AF1E | 2 | FUN_0003ad74 indexes tp+0x7010 by ≤ 3 halfwords → cannot reach 0x73EA [E: decompile] |
| `mov 0xC6000` @0x146DC | 1 | **boot copy of [0xC6000, 0xC7000) to RAM 0xFA800000**, then 0xFA001300 := 0xC6000. A calibration-RAM overlay set-up [E: listing 0x146C0–0x14772]. Value-agnostic |
| `mov 0xC6000` @0x59560 / 0x5963E / 0x59862 | 3 | address translation for [0xC6000, 0xC7FFF] into that overlay, plus page (0x1000) operations through the bootloader API table. Value-agnostic [E: decompile of FUN_00059560, listing] |
| ep values | 180 distinct `mov imm32 → ep` | none in [0xC62EC, 0xC63EA] (sld reach ≤ 254 B). The ep bases in the cal page are ≥ 0xC7008, above the cell [E] |

**Precedent for the page-level readers [E].** V293 → V294 changed 8 bytes of this same block: 0xC62E7, 0xC63E8,
0xC63EA–EB and the trailer 0xC6FFC–FF. V294 flew on r71b with no EPS fault. The boot overlay copy and the page
operations have therefore already carried a changed b.

### 2.3 What b scales, and who reads it

| quantity | cell | accesses (my scan = Ghidra) | consumer | risk |
|---|---|---|---|---|
| fb state s | gp-0x3d30 | 1 ld @0x28F7C, 1 st @0x28FA8 | private to the filter | int32, §2.4 |
| sentinel | gp-0x3d2c | 1 ld, 1 st | private | restart, §2.6 |
| \|r26>>5\| | gp-0x6a34 | st @0x290CA; ld @0x2A0CA, ld @0x2AFAE | 0x2A0CA is the damper mode gated by gp-0x680a == 1. **gp-0x680a has 2 readers and 0 writers**: no st, no set1/clr1/not1, no 6-byte form [E: `ab1b`]. 0x2AFAE is in FUN_0002a93a, inside the twin island [0x2A30E, 0x2B421]. It has **0 external branches**: the 3 "jarl" hits originate at 0xD96C6/F2/1E, which is cal data. The 4 in-code LE32 hits are mid-instruction or a peripheral constant (`mov 0x2b000` → `st.w` to 0xFF6C1044) [E: `ab1b` + listing 0x5A350]. Range unchanged at 0…32, since C is unchanged | none live |
| T = lane torque | gp-0x6b38 | st 0x2A23C / 0x2A934 (twin); ld 0x2B418 (forward → FUN_0002b422 → gp-0x6b3a → monitor FUN_0002b57a), ld 0x4E8D2 / 0x4E8E2, ld 0x55DF0 and 0xC4B40 (the 427 tap) | FUN_0004e82e is a **passive diagnostic packer**. It copies cmd, flags, bar, x and T into a 0x38-byte buffer [E: decompile]. The forward clamp and monitor bound at 3072, far above the unchanged rail 2461 | none new |

My T-reader list matches the sibling trim-ratio adversary's list exactly. I derived it independently.

### 2.4 int32 (`ab2` [2])

The only b-dependent products are x·b (≤ 1106 × 12000 = 1.33 × 10⁷) and a·s. Every other product (E·Kp ≤ 4.9 × 10⁶;
the output-lag, ramp and gain products ≤ 5 × 10⁸) is b-independent.

The bound on s is exact:
- s' = floor(a·s/1024) + floor(b·x/1024) is monotone non-decreasing in s and in x;
- the bail keeps |x| ≤ 12000;
- so from s = 0 (boot or restart), s stays inside [s*(−12000), s*(+12000)].

| b | s* at x = −12000 / +12000 | max \|a·s\| | margin |
|---|---|---|---|
| 567 (V294) | −523,422 / 523,265 | 5.29 × 10⁸ | 4.058 |
| **1106 (A)** | −1,020,928 / 1,020,771 | 1.032 × 10⁹ | **2.081** |
| 1150 | | | 2.001 (largest b with margin ≥ 2.0) |
| 2301 | | | 1.0 (largest b with margin ≥ 1.0) |

- 200,000 adversarial ticks (x at ±12000 and random): 0 escapes from the bound, 0 wraps [E].
- On r71b, A's max \|a·s\| is 2.35 × 10⁸, a margin of 9.1 [E].

### 2.5 The surface, the rail, the cap, the floors (`ab2` [3], [4], [6])

- **Surface.** Settled T(A) == T(V294) at all 241 idx × 2 signs, at constant x ∈ {0, ±800, ±12000}: **0 of 2,410
  differ**, and r26 settles to exactly 0 [E]. At constant x the s-map is monotone and converges to a fixed point,
  so the difference operand is 0.
  - The output-lag fixed-point interval did not split the two trajectories.
  - The surface is monotone in both signs.
  - T(0/60/120/180/240) = 0/617/1237/1860/2461 and −0/−619/−1239/−1862/−2463.
- **Rail and cap.** With r26 forced to ±C: rail +2461/−2463, zero-command T −616/+615, identical for V294 and A.
  b does not enter the surface-vs-r26 map at all [E].
- **DC bias from floors.** Under zero-mean x noise (σ 1, 4, 16 counts), A − V294 mean T is ≤ 0.13 T.
  Σ r26 telescopes to s_end − s_start [E].
- **HF controller gain** \|PID/x\| at 20 Hz: A **4.055** = V294 2.079 × 1.951 [E: exact 1 kHz transfer, `ab3`].
  The same code gives V282 44.90, which matches the harness. That is the second method.

### 2.6 The restart pulse (`ab2` [5], `ab2b`, `ab2c`)

**How the pulse arises [E: decompile lines 69–99 and 161–172].**
- A bail sets sentinel := 2, r26 := 0, and skips the PID for that tick (S := 0 into the output lag).
- On the next good tick, s_old := 0, so r26 = clamp(b·x ≫ 10, ±C). That pulse decays at a/1024 per tick (τ 79 ms).
- Boot also starts with sentinel 0, but the PID is not running then.
- The pulse is capped by C, so the absolute ceiling is the unchanged 616 T.

At zero command my numbers equal the design's: 100 deg/s → V294 145 T (160 ms > 50 T), A **283 T** (219 ms).
**Over the demand envelope (100 deg/s, idx {0…240} × sign × rate sign):**

| b | worst pulse | vs absolute 288 | worst per-point ratio A / V294 | worst / worst |
|---|---|---|---|---|
| 1000 | 274 | PASS | 1.835 | 1.66 |
| **1050** | **287** | **PASS** | **1.932** | 1.74 |
| 1080 | 295 | FAIL | 1.985 | 1.79 |
| **1106 (A)** | **301** (idx 238) | **FAIL (6/28 cells)** | **2.038** (idx 180) | 1.82 |

The pulse grows with |demand|. The one-tick S dropout at the bail tick adds to the restart pulse when the signs agree.
**The design's binding constraint was evaluated at zero command only.** [E for the numbers; B for how often bails
occur: they need an implausible bar (> 25600), an invalid polarity, or |x| > 12000, which the producer's saturation at
±12000 makes unreachable.]

---

## 3. (a) Arithmetic on the real route (`ab2` [7], `ab7`)

My A march on r71b's recorded motion (1 kHz, engaged ticks):

| | V294 | A |
|---|---|---|
| \|r26\| at C | 0.0000 % | 0.0111 % |
| P at clamp | 0.057 % | 0.053 % |
| \|T\| ≥ 2000 | 0 | 0 |
| max \|T\| | 1467 | 1255 |
| p99.9 \|r26\| | 368 | 718 |

- A − V294 delivered torque on the same motion: rms 17.7 T, p99 90, max 261 [E].
- Hands-on engaged (92 s): |trim| p50/p99/max V294 8/166/309 → A 17/323/564 T.
- Hands-off engaged (709 s): 1/72/202 → 2/141/394 T.
- These use the recorded motion, not A's closed-loop motion, which should be somewhat smaller [B].

---

## 4. (b) Interlocks

- **The lane's reachable peak is unchanged.** The rail is set by the P clamp at unchanged C and Kp. The trim cap is
  616 T. [E, §2.5.] On r71b the lane never exceeded 1467 (V294) or 1255 (A); the forward clamp is 3072 [E].
- **Soft-EME (gp-0x3570, the 5120–5325 band on the post-governor total).** The LKAS lane contributes ≤ 2461 either way.
  - The trim's extra authority is ≤ 616 T × taper (×0.30 at |bar>>5| ≥ 64). V294 has the same cap.
  - The trim opposes the torque that accelerates the wheel, so it mostly reduces the total.
  - Nothing newly reachable [E for the bound; B for dwell on other roads; the band semantics are inherited from
    ADV-V293-D].
- **FUN_0004595a** (decompiled): a sign/magnitude comparator between gp-0x6b94 (the demand into the governor) and
  gp-0x6ace (the governor output). It fires FUN_000462e6(0x3f8e) when |ace| > |b94| + 10 or when the two have
  opposite signs.
  - Its inputs are aggregator-level. A's extra 5–30 Hz lane content is ≤ 2.6 T rms (harness).
  - V282's lane, ×11 higher HF gain, flew through it [E: my ab3 20 Hz gains; B: governor snap semantics inherited
    from the archived trace].
- **FUN_0002b57a**: reads gp-0x6b3a, which is already clamped to ±3072 upstream. It cannot trip [E: structure].
- **x plausibility and lockstep** (gp-0x6a56 / gp-0x4ca6): b does not write x [E: the filter only reads x].
- **No monitor reads s, r26, gp-0x6a34 or the published PID cells** [E: §2.3 census].

---

## 5. (c) Lineage (`ab3`, grep)

**Images [E, 297 images read, `ab3`].**
- b 1560 at a 923 on the **sum** operand (`add`, shl 5) on every image except:
  - V289: 2301 at a 875;
  - V291c10 / V292: 958 at a 962;
  - V294: 567 at a 1011 on the **diff** operand (`subr`, shl 2).
- **Only V294 carries the diff operand.**
- The design's lineage statement is correct.
- Grep: 21 build scripts reference 0xC63EA [E].
- `BUILD-LINEAGE-PART1-LEVER-INDEX.md` row 33 exists but stops at "V293 restores 923/1560" and does not record
  V294's 567. That is a record gap; I did not edit it.

**HF precedent, as |PID/x| at 20 Hz for every flown class [E, exact transfer per image].**

| image | \|PID/x\| at 20 Hz | outcome |
|---|---|---|
| V294 | 2.08 | clean, "No grinding or stuttering!" |
| **A** | **4.06** | untested |
| V292 | 31.4 | REVERT, 7 Hz re-armed |
| V285 | 39.5 | |
| V282 class | 44.9 | ground at 20 Hz |
| V289 | 55.1 | ring moved to 16 Hz |

- No flown build lies between 2.08 and 31.4. A is ×7.7 below the nearest flown bad class.
- The operand classes differ, so this is a controller-gain comparison only [B].

**"What is different this time" is dose only.**
- The design says so honestly: "same lever pushed further in the direction it already flew".
- The prior step (V293 → V294) had a harness counterfactual of ×0.77 / ×0.93 on hard-turn 1.6–3 Hz (5–10 / 15–22 m/s,
  nominal). This step's prediction is ×0.83 / ×0.94–0.96. **The two are the same size.**
- After the first step the operator still reported "Jerky on hard turns at medium speed".
- These numbers are quoted from the harness and design reports, not re-derived by me. The inference is [B].
- Untested ≠ falsified. It is still a re-run of the same lever at a comparable effect size. The operator should be
  told that before he drives it.

---

## 6. (d) Observability (`ab4`, `ab5`, `ab6`, `ab8`)

**The instrument.** The design's per-window OLS, `T_tap = c0 + c1·FF_V294 + c2·TRIM_V294`, re-implemented on my own
marches. My FF and live marches equal plib's T1k_null / T1k_live bit-for-bit.
- NULL = the real r71b tap.
- POSITIVE = quant(my A march) + the real residual.
- STRESS = POSITIVE + 0.95 × a proxy for the part of the residual that scales with b.
  - The proxy is the trim with x reconstructed by ZOH minus the trim with the resample_poly x: 0.86 counts rms,
    against a TRIM of 14.3.
- Rule: c2 > 1.45 → "b live".

| window family | n | V294 c2 median [p5, p95] | A c2 median [p5, p95] | errors (false alarm / miss / miss-stress) |
|---|---|---|---|---|
| hands-off 5 s | 141 | 0.98 [0.67, 1.12] | 1.89 [1.10, 2.07] | 2 / 11 / 13 |
| hands-off 10 s | 70 | 0.98 [0.77, 1.09] | 1.90 [1.57, 2.01] | 1 / 3 / 3 |
| hands-off 15 s | 47 | 0.99 [0.88, 1.09] | 1.91 [1.68, 1.99] | 0 / 0 / 1 |
| hands-off 30 s | 23 | **0.986 [0.934, 1.043]** | **1.923 [1.828, 1.958]** | 0 / 0 / 0 |
| contiguous 15 s, all engaged (hands-on incl.) | 49 | 0.98 [0.80, 1.04] | 1.90 [1.68, 1.97] | 0 / 0 / 0 |
| **symptomatic: ±10 s around each 5–22 m/s hard turn** (15 events) | 15 | 1.00 [0.95, 1.02] | **1.95 [1.89, 1.97]** | **0 / 0 / 0** |

The 30 s hands-off row reproduces the design exactly.

**Changed value: VISIBLE from one short symptomatic drive [E].** Per-event c2 is:
- V294: 0.91–1.02;
- A: 1.86–1.97;
- A-stress: 1.85–1.97.

Hard turns excite the trim, with a median trim rms of 23 counts per window, which makes the symptomatic windows the
best read. **The minimum is about 15 s of engaged frames with wheel motion.** 5–10 s windows fail 4–8 % of the time.
c1 reads 0.98–0.99 for both.

**Inherited flight-attribution gates on the correct A image [E, `ab8`, the real `identity_block`].**
- FF identity R² is 0.9620, against V294's 0.9868 (positive control reproduced). The V294 flight-read F1 line
  (FAIL < 0.90) still passes.
- A later read that tightens that line to ≥ 0.98, as the trim-ratio design did, would misfire on A. The identity has
  no trim term.

**Literal acceptance bands of the design's null sentence [E, `ab5`].** "c2 ∈ [0.9, 1.1] → not live" and
"c1 ∈ [0.97, 1.00] and c2 ∈ [1.8, 2.0] → live as designed":

| windows | no call on V294 | no call on A | wrong calls |
|---|---|---|---|
| 15 s hands-off | 17 % | **38 %** | 0 |
| 30 s hands-off | 4 % | 17 % | 0 |
| contiguous 15 s all-engaged | 22 % | 35 % | 0 |
| contiguous 30 s all-engaged | 9 % | 22 % | 0 |

**The symptom band cannot adjudicate the effect [E, two methods].**
- *Per-event method (`ab4`)*: 15 medium-speed hard-turn events on r71b. 1.6–3 Hz wheel-rate rms per event is
  2.5–19.6 deg/s, with a log-sd of 0.55.
  - One event against one event, with no change: ×0.28–3.59 (90 %).
  - Normalising by the command or the tap does not rescue it (×0.39–2.60).
- *Block bootstrap (`ab6`)*: 54 s of 5–15 m/s hard frames.
  - 15 s against the pool: ×0.78–1.26. 30 s: ×0.83–1.19.
  - Drive against drive: ×0.71–1.42 at 15 s.
- The prediction is ×0.83 nominal (×0.68–0.93 over the family), which is at or inside the no-change scatter.

**The sentence a null actually licenses (my rewrite):**

> *"If c2 > 1.45 on ≥ 15 s of engaged frames (preferably a symptomatic hard-turn window), b 1106 is live.
> If c1 also lies inside V294's own r71b spread (15 s windows p5–p95 ≈ 0.94–1.00), nothing else in the FF moved.
> If c2 < 1.45, the image is not A: stop. If c2 < 0, the sign is inverted: revert.
> Given b live, an unchanged 1.6–3 Hz hard-turn band licenses NOTHING. The design predicts a change inside that
> band's one-drive noise.
> An unchanged 'jerky on hard turns' is expected under the design's own identified world, where about 94 % of the
> motion is disturbance. It cannot distinguish 'EPS damping does not limit the symptom' from 'this dose is below what
> he can feel'.
> A reported IMPROVEMENT is attributable to b, the only change.
> The loose complaints are not tested (c1 = 1)."*

---

## 7. (e) One build, cal-only

**[E, `ab1` §7]**
- The CRC chain holds 50 blocks. 0xC63EA sits in [0xC6000, 0xC6FFC), with its trailer at 0xC6FFC.
- The bootloader walk checks that block before the 0xC6000 → 0x13000 bridge.
- The in-memory candidate differs from V294 in **exactly 6 bytes**: 0xC63EA–EB and 0xC6FFC–FF.
  - The kit verifier reports bootloader walk 0 fails and full chain 0 fails.
  - In-memory sha256 `1daf040d…eb88330`. This is not a build artifact.
- No code byte, no opcode, no second cal cell. The code region [0x13000, 0xC0000) differs from stock only at V294's
  known 47 bytes / 13 runs, which confirms the stock-program Ghidra xrefs are valid.

---

## 8. Required changes (for the orchestrator; I changed nothing)

1. **H-SAFE-3.** Choose one:
   - cut b to **≤ 1050**, which passes every reading [E, `ab2c`: 287 T, 1.93×]; or
   - record explicitly that the pre-registered cap is worst-case vs worst-case, where A reads 1.82 and passes, and
     accept the per-point 2.04 on the fault path.

   Either way, the design's "283 vs 288, binding" line is incomplete. A reaches 301 T.
2. **Rewrite the null sentence** as in §6.
   - Drop "unchanged band or report ⇒ EPS damping does not limit the symptom".
   - Drop "no further trim in the cal space will". b is cal-only up to 2301 (int32 margin 1.0).
3. **Replace the interval bands with the midpoint rule** (c2 > 1.45).
   - Read c1 against V294's own window spread, not 0.97–1.00.
   - Name the minimum exposure: ≥ 15 s of engaged frames, hard-turn windows preferred.
   - If anyone reuses the V294 attribution script's identity R², keep its line at 0.90. A reads 0.962.
4. **Add to the stated risks**: resistance to the driver's hand motion under override roughly doubles. p99 is
   166 → 323 T and max 309 → 564 T on r71b, against the unchanged 616 T cap.
5. **Tell the operator before he drives it** that this is the same lever as V294 at a similarly sized predicted step,
   and that the first step left "jerky on hard turns" in place.

---

## 9. Not verified / BELIEF

- **How often bails happen.** Structurally they are fault or init paths; I did not measure bail occurrence on any
  route. Nothing on the wire flags a bail.
- **The semantics of the governor, soft-EME and FUN_0004595a.** I re-read the topology and the FUN_0004595a decompile.
  The thresholds and dwell semantics are inherited.
- **Register-indirect writers of gp-0x680a.** Excluded only by operand scans and the census's .data boot value. This is
  the kit's standing residual.
- **Closed-loop motion under A.** Every route number here uses r71b's recorded motion under V294.
- **The ×0.83 / ×0.77 effect sizes in §5** are quoted from the design and harness, not re-derived by me.

## 10. Files (`analysis-2020accord/studies/v295/design/robust-joint/adv_bytes/`)

| file | what |
|---|---|
| `ADV-bytes-robust-joint-CRITERIA.md` | FAIL criteria, written first |
| `ab1_bytes.py` / `_out.txt` | hash, cells, raw V850 scanner with 7 controls, reader census, address formers, ep, the gp cells b scales, stock-diff, CRC chain + in-memory candidate |
| `ab1b_twin_flags.py` / `_out.txt` | twin-island callers, gp-0x680a / gp-0x6809 writers incl. bit ops |
| `ab1c_T_readers.py` / `_out.txt` | gp-0x6b38 / 6b30 / 6b2e / 6b3c access census |
| `ab1d_ep_values.py` / `_out.txt` | every `mov imm32 → ep` value |
| `ab2_lane.py` | my integer lane, from the V294 decompile and listing |
| `ab2_arith.py` / `_out.txt` | vs golden (80k ticks), int32, surface 2,410, rail and cap, restart, floors, r71b census; `_scratch_ab2_route.npz` |
| `ab2b_restart_grid.py`, `ab2c_restart_b.py` / `_out.txt` | the restart pulse over the demand envelope; b for each reading |
| `ab3_lineage_matrix.py` / `_out.txt` | the fb-former cells and \|PID/x\| at 20 Hz down 297 images |
| `ab4_observe.py` / `_out.txt` | the wire read: null, positive, stress; W1/W2/W3 windows; symptom-band per-event floor |
| `ab5_bands.py` / `_out.txt` | the design's literal bands, right/wrong/no-call; FF-only identity |
| `ab6_symptom_floor.py` / `_out.txt` | block-bootstrap floor of the symptom band (second method) |
| `ab7_override.py` / `_out.txt` | the trim under driver torque on r71b |
| `ab8_identity_gate.py` / `_out.txt` | the real `identity_block` on the synthetic A tap |
