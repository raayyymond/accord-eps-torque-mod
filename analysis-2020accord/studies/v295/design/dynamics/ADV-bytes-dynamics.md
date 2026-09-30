# ADV-bytes-dynamics — adversary "bytes + instrument" against the `dynamics` candidate A1017

Subagent, 2026-09-30. **Design-phase adversarial pass only.** Nothing was built, flashed or sent, and no CAN traffic was
generated. No image or rwd was written: the A1017 CRC check ran in memory only. Nothing was committed. The fork, STATE,
memory, lineage, the golden model and `../accord-firmwares` were read only.

- Every decision-bearing claim is marked **[E]** EVIDENCE (with its method) or **[B]** BELIEF.
- The FAIL criteria were written before any number was computed: `ADV-bytes-CRITERIA.md`.
- Default verdict for any claim I could not reproduce: REFUTED.

**Candidate.** A1017 moves the fb-lag pole `0xC63E8` from 1011 to 1017 (LE `F3 03` -> `F9 03`) and keeps b `0xC63EA` at 567.

## 0. Verdict: SURVIVES_WITH_CHANGES

**The bytes, the arithmetic, the interlocks, the lineage and the cal-only claim all hold.** I re-derived each one from the
V294 image with my own code, and none can be broken:
- The edit is one payload byte plus one CRC trailer: 5 bytes in total, and 0 code bytes.
- The cell has exactly one reader.
- Every intermediate stays inside int32, with a margin of 2.172.
- The delivered surface, the rail, the zero-command cap and the HF transfer are unchanged.
- The restart pulse and the replay internals reproduce the design's numbers to the count.

**What does not survive as written is the pre-registered wire read.**
- **The primary exact-model regression (beta) is sound.** On symptomatic 15 s and 30 s hard-turn windows it classifies 12/12
  correctly in both arms.
- **The trim-footprint |K| sentences misfire on a 15-30 s window.** Applied per window as written:
  - A correct A1017 flight would trigger **"the arithmetic is not what the report says — STOP"** in 18-20 % of contiguous
    windows.
  - A V294 flight would trigger it in 14-16 %.
  - At 15 s, V294 reads |K| >= 0.28 ("live") in 21 % of windows.
  - The |K| read becomes decisive only at 60-120 s or more of pooled hands-off driving.

The changes that fix the read are in section 6. None of them touches the image.

**One risk statement on the page is wrong.** It calls soft-EME exposure "unchanged".
- **The instantaneous range is unchanged [E].**
- **The dwell of large trim torque is not [E, replay].** It rises about 18-fold in ticks, and its longest run rises from 42 ms
  to 212 ms. That is longer than the 75 ms SM2 residency on record.
- All of it is below 5 m/s.

This is a rise in exposure, not a new mechanism, but it must be stated (section 3).

| pre-registered criterion | result |
|---|---|
| FB-1 base bytes / hash | **PASS** |
| FB-2 reader census | **PASS**; the bulk boot copy and the CRC readers are benign, proven on-car by V294's own edit of this page |
| FB-3 second consumers | **PASS** |
| FB-4 int32 | **PASS**, margin 2.172 against the 2.0 threshold (thin) |
| FB-5 delivered surface | **PASS**; 0 of 482 differ at 3 constant rates |
| FB-6 settling / dither | **PASS**; every x settles to exactly 0 |
| FB-7 restart pulse | **PASS**; matches the design exactly |
| FB-8 interlocks | **PASS** on range. The soft-EME dwell exposure rises (a stated risk, not "unchanged") |
| FB-9 lineage | **PASS**; 1017 is on none of 304 images. Three framing findings |
| FB-10 (i) beta separation | **PASS** |
| FB-10 (ii) null false alarm | **PASS** at 1 s blocks; **fires at 3 s blocks** (12-14 % of contiguous 30 s windows); fixed by a footprint gate |
| FB-10 (iii) \|K\| thresholds | **FIRES as written** (> 20 % misfire at 15 s). The re-worded read works |
| FB-11 instrument per changed value | **PASS** |
| FB-12 one build, cal-only | **PASS** |

---

## 1. Bytes, from the V294 image (`advb1_bytes.py`, `advb5_ram_mirror.py`, Ghidra)

**The image and the cell [E].**
- The image is `_v294_…plain_image.bin`, sha256 `3143616d…dbdd85`, asserted in code.
- `0xC63E8` holds `F3 03` = 1011, and `0xC63EA` holds `37 02` = 567. Its neighbours: C 1024, lag 992/507, Ki 0, P and sum
  clamps 15360, lane clamp 3072, gain 5346 (through the 0x2A1F0 displacement).
- **The edit changes exactly one byte**, 0xC63E8 F3 -> F9. That makes it one byte plus the trailer.

**Width and signedness [E].**
- The Ghidra listing (dry run, 0x28F4C-0x28FBE) shows `0x28F8A ld.h 0x73e8,tp,r9` (bytes `25 4f e8 73`). The load is signed
  16-bit, and 1017 is positive.
- `0x28F92 mul r26,r9,r0` keeps the **low 32 bits** of a·s_old. Then `0x28FA0 sar 0xa`, `0x28FA2 add r7,r9` (s_new), and
  `0x28FA4 subr r9,r26` (r26 = s_new − s_old).
- `0x28FA8 st.w r9,-0x3d30` stores the state before the clamp, and `0x28FA6..0x28FBC` clamps to ±C.
- The decompile of `V294_lkas_rate_pid` (FUN_00028ea6), lines 69-172, gives the same structure: the bail window
  `0x2EE0 + x < 0x5DC1` (|x| ≤ 12000), then sentinel → s_old = 0, then the product, then the clamp.
- I confirmed the Ghidra program is not stale: `read_memory` at 0xC63E0, 0x28FA0 and 0x29D74 equals the file.

**Reader census [E, raw little-endian scan, positive-controlled].**
- The controls 0x28F8A `ld.h tp+0x73E8` and 0x28F86 `ld.hu tp+0x73EA` are both found.
- `0xC63E8` has **one reader, 0x28F8A**, across every access form I scanned:
  - 4-byte disp16 on any base register, including the ld.bu parity and the `hw2|1` forms;
  - the 6-byte disp23 form (its decoder is controlled by the census's 0x48E56 gp-0x6752 read);
  - absolute LE32 anywhere in the image;
  - a movhi 0xC/0xD base plus disp or movea (7 + 7 sites, all resolving elsewhere: tp+0x63xx = 0xC53xx, or gp RAM);
  - disp16 0x03E8/0x03E9 on any base — this form would catch a register holding 0xC6000 or 0xFA800000;
  - ep-relative short loads cannot reach the cell. ep does take 174 cal-table addresses, but the lowest is 0xC7008: it is
    never loaded with an address in the 0xC6000 page, and never through movhi 0xC/0xD. An sld reaches only ≤ 0xFE past ep.
- **The uncalled twin island has no reader of 0xC63E8.** It has no fb former. The design's parenthetical "twin island only
  otherwise" is wrong, though conservative; the lag cells do have twin readers at 0x2A892 / 0x2A8A2.

**Bulk readers of the page [E].** Four `mov imm32 0xC6000` sites exist:
- `0x146DC` is a boot-time copy of `0xC6000..0xC6FFF` to RAM `0xFA800000`.
- `FUN_00059560` translates addresses in `[0xC6000, 0xC7FFF]` by −0x58C6000.
- `0x5963E` is a range check, and `0x59862` a flash routine over 0x1000 bytes.
- The kit already knew this (TRACE-2026-09-06, LOOPSHAPE-LAGPOLE-KD-2026-09-04).
- These read the byte in bulk, for copies and CRCs, not as a control value. **V294 edited three cells of this same page
  (0xC62E6, 0xC63E8, 0xC63EA) and its trim measured live at the design pole and gain on r71b**, so an edited flash value in
  this page reaches the code, and the page's CRC path works on-car. [E]

## 2. Integer arithmetic at a = 1017 (`advb4_arith.py`, `advb9_replay.py`, `advb11_trim_tf.py`)

**My own mirror matches both references [E].** I wrote a pure-Python integer mirror from the listing above. Tested on random
inputs with a wandering rate and 30 random slams to ±12000:
- against the harness `Lane`: **0 mismatches in T and r26** on 20,000 ticks, at both a = 1011 and a = 1017;
- against the golden `lkas_fb_lag`: 0 mismatches on 20,000 ticks at each a.

**int32 [E, exact integer fixed point + a monotonicity proof].**
- f_x(s) = ⌊a·s/1024⌋ + ⌊567·x/1024⌋ is non-decreasing in s and in x. So the interval [s*(−12000), s*(+12000)] is invariant
  from s = 0 (boot or a restart), and |s| can never exceed the fixed point.
- At a = 1017: s* = +971,777 / −972,069, max |a·s| = 9.886e8, **margin 2.172**. The design's figure is 2.17.
- At a = 1011 the margin is 4.058; at 1018 it is 1.860 and at 1020 it is 1.238.
- b_max(1017) = 1232, so b ≤ 616 at margin 2. That confirms the design's constraint on combining this with a b increase.
- Nothing downstream changes (the S clamp is unchanged): |E·Kp| ≤ 5152·960 = 4.9e6, the output-lag products carry margins
  ≥ 8.9, and the LERP is flat.
- On the r71b replay max |a·s| = 2.074e8, a margin of 10.4 (V294: 17.8), exactly the design's figure.

**Settling [E].** For every x in [−12000, 12000], starting from 0, from +s* and from −s*, r26 reaches exactly 0 and stays there.
- The worst case takes 1469 ticks (V294: 789).
- With x = 0 there is no bias: negative s sticks in [−146, −1], but r26 is a difference and reads 0.

**Delivered surface [E].** I marched T(idx) at x = 0, 800 and −2400, for all 241 idx and both signs:
- **0 of 482 differ** between 1011 and 1017;
- the rail is **+2461 / −2463**;
- the surface is monotone.

**Restart pulse after a bail, wheel held [E].** Both my mirror and the harness give **17 / 52 / 174 / 503 T** at 10 / 30 / 100 /
300 deg/s, and **433 ms above 50 T** at 300 deg/s (V294: 14 / 43 / 144 / 419 T, 252 ms). This matches the design exactly.

**HF [E, closed form of the integer filter's linear part].** The ratio |r26/x| A1017/V294 is:

| 5 Hz | 9 Hz | 13 Hz | 17 Hz | 20 Hz | 25 Hz | 30 Hz |
|---|---|---|---|---|---|---|
| 1.052 | 1.015 | 1.006 | 1.002 | 1.0007 | 0.999 | 0.999 |

- At 20 Hz the phase is −2.7 deg.
- |P/x| at 20 Hz = 2.079 × 1.0007 = 2.080, as the design says.

**Trim transfer, my own closed form [E].** With a 3 ms rate-former window:
- damping part at 2 Hz: **1.61 → 2.17 T per deg/s**;
- damping peak: **3.17 → 2.33 Hz**;
- K_α: **0.2097 → 0.3894 T per deg/s²**.

This reproduces the design's d1/d6. One non-decision-bearing difference: V294's 20 Hz angle comes out at −77 deg against the
design table's −81.

**r71b open-loop replay [E, plib.march, want=True].** Every number reproduces `d5_replay_internals.json`:

| | V294 | A1017 |
|---|---|---|
| max \|r26\| | 637 | 790 |
| fb-clamp binds | 0 | 0 |
| P-clamp binds | 461 | 345 |
| trim rms | 18.7 T | 28.0 T |
| trim p99 | 95 T | 140 T |
| trim max | 309 T | 429 T |
| max \|T\| | 1467 | 1358 |

## 3. Interlocks (`advb2_consumers.py`, `advb9b_hightrim.py`, record)

**Consumers of the changed signal [E, 4-byte + 6-byte + absolute LE32, 5/5 controls].**
- **gp-0x6a34 (\|r26>>5\|).** Written at 0x290CA. Read at 0x2A0CA, the damper lane, which is gated by gp-0x680a == 1. gp-0x680a
  has 2 readers and 0 writers and boots 0, so that lane is unreachable. The only other read is 0x2AFAE in the twin.
  (Register-indirect writes remain the standing residual.)
- **gp-0x3d30 / gp-0x3d2c.** One load and one store each, all inside the PID. No lockstep copy of the fb former exists: it would
  have to read 0xC63E8, and nothing else does.
- **Published S / P / sum / D** (gp-0x6b2e/32/34/36). Stores only, apart from one twin read.
- **T gp-0x6b38.** Its readers:
  - 0x55DF0, the 427 tap packer;
  - 0xC4B40, the telemetry cave;
  - 0x4E8D2 / 0x4E8E2 in **FUN_0004e82e**, a diagnostic record packer with no threshold. I decompiled it.
  - the twin.
- **gp-0x6b3c → FUN_0002b422 → gp-0x6b3a.** The value is clamped at 0x2B45C, and the monitor FUN_0002b57a reads it at 0x2B5B2.
  The forward clamp makes that monitor untrippable.

**Range argument [E].** The reachable T set is unchanged: the rail is unchanged and the zero-command cap is C·Kp/256 → 616 T,
also unchanged. The per-tick |ΔT| bound through the output lag is unchanged too. So nothing that thresholds T's instantaneous
value or slew can be newly reached.
- **Honda's oscillation detector** (FUN_000428d4, input gp-0x6c2c) needs 15 reversals faster than 10 Hz at ±12800. A1017
  changes the lane's gain there by ×1.00-1.015 [E, linear]. It cannot newly arm it.
- **Governor, energy budget and FUN_0004595a.** Their operands are downstream magnitudes whose range the lane cannot raise.
  V293-D §1.4's range identity carries over [E structure, inherited].

**Soft-EME dwell: a RISK the design mislabels "unchanged" [E replay, B consequence].** The soft-EME integrator gp-0x3570 is
dwell-sensitive: SM2 arms after about 75 ms of a 205-count excess (ADV-V293-D §1.5).

On the r71b replay:

| | V294 | A1017 |
|---|---|---|
| ticks with \|trim\| > 300 T | 42 | 776 |
| longest run | 42 ms | 212 ms |
| episodes | 1 | 8 |

A1017's episodes:
- all at **0.5-4.6 m/s**;
- 75 % with |bar| ≥ 400;
- 7 % steeringPressed;
- corr(trim, bar) = +0.58.

How to read that:
- **[B, sign chain]** Hands-off the bar reads +0.55·α_left (metric agent). That puts bar in the tap's + right convention, so a
  trim co-signed with bar is co-directional with the bar-keyed base assist.
- It is **not a new mechanism**. The range is unchanged, V294 reaches the same states at higher α, and V282 flew with its lane
  able to hold the full 2461 rail at any dwell. SM2/SM3 self-clear.
- But the exposure rises, it is concentrated at parking and creep speed where base assist is largest, and the lane-only harness
  cannot see it.
- **The page must state it.**

## 4. Lineage (`advb3_redo_ladder.py`, 304-image census, lineage docs)

**[E] 0xC63E8 / 0xC63EA / 0x28FA4 across all 304 images on disk:**

| cells | operand | images |
|---|---|---|
| 923 / 1560 | add | 294 |
| 875 / 2301 | add | V289 only |
| 962 / 958 | add | V291, V292 |
| 1011 / 567 | subr | V294 only |

**1017 has never been built.** The design's lineage table is right. On the difference operand only V294's 1011 has flown, and it
flew clean ("No grinding or stuttering!"). V289 and V292 were rate-servo builds (\|P/x\|(20) = 44.9) that also carried caves.
Their failures were HF phenomena (the 16 Hz ring, the 7 Hz re-arm), and A1017 leaves HF unchanged. So "what is different this
time" is real.

Framing findings:
1. **"Inside V294's build-script ladder bounds a ∈ [1000, 1018]" overstates the precedent.** That builder also asserts
   (a, b) ∈ LADDER = {(1015,392), (1011,567), (1005,831), (1000,1080), (1011,284), (1011,1134)} (`build_v294_tva.py`, the ladder
   check). (1017, 567) is not a rung, so A1017 needs its own builder. The ladder held K_α/J = 1, and A1017 is K_α ×1.86 at a
   1.09 Hz pole, a point V294's design never evaluated.
2. **The design does not cite the V294 redo audit's own pole-ladder result** (`studies/v294/redo_2026-09-23/physics` rp8b/rp8c,
   report claim 5). Moving to a = 1018 **with K/J held** costs light-world outer PM at 26 m/s, +34 → +18 deg. I ran A1017
   (b held, K ×13/7) in **that model** [E model, a second independent plant world]:

   | light world, 26 m/s | V294 | A1017, b held | a 1017, K held |
   |---|---|---|---|
   | PM | +34 | **+54** | +23 |
   | Ms | 2.99 | **2.40** | 4.94 |
   | GM | 1.70 | **1.88** | 1.32 |

   - The design's direction is confirmed in the redo's own model.
   - The benefit comes from the K_α rise, not from the pole alone.
   - The identified world moves by ≤ 3 deg PM.
3. **The PART1 lever index for 0xC63E8 is stale.** Its row ends at "V293 restores 923/1560" and carries no V294 1011/567 entry. This
   is a record defect. I report it and did not edit it.

## 5. One build, cal-only (`advb8_crc.py`, in memory only)

**[E] The edit is cal-only.**
- 0xC63E8 lies in block `[0xC6000, 0xC6FFC)`. The bootloader walk covers it (the 0xC6000 bridge block).
- Applying the edit and recomputing the trailer (0xC6FFC: `0xF3441165` → `0x5BF1D146`) gives a bootloader walk of **49/49** and
  a full chain of **50/50**.
- **The whole-range diff is 5 bytes**: 0xC63E8 plus the 4 trailer bytes. **0 bytes change in the code region.**
- V293 → V294 changed this same block and trailer, so the builder path is exercised.
- The rwd x31 checksum is the standard pipeline. I did not generate it.

## 6. Observability on the existing wire (`advb6_observe.py`, `advb7_joint_rule.py`, `advb12_K_duration.py`, `advb13_beta_only.py`, `advb10_band_noise.py`)

**Method [E].** This is independent of the design's d3:
- **The march uses plib.march**, a third implementation, not the harness Lane. Positive control: V294 equals the cached
  `T1k_live` on **0 of 1,020,390 mismatching ticks**.
- **The synthetic A1017 flight** is quant(T_A1017) plus the real tap residual.
  - The residual is 3.64 counts rms hands-off and 8.98 hands-on.
  - The footprint is 9.88 counts rms hands-off (p99 48) and 20.4 hands-on.
- **The |K| read uses the metric agent's own `build_grid`, `band_signals` and `trim_footprint`** on its own grid. The synthetic
  delta is mapped by time; alignment corr is 1.00000 at 0 frames.

**(a) Exact-model beta (read #1) [E sim on r71b].**
- **The design's windows (1500 hands-off frames):**
  - synthetic: beta median 1.01, z median 12.7, 96 % of windows with z > 3;
  - null: |z| > 3 in 4 %, **beta > 0.3 in 9 %, beta ≥ 0.5 ("A1017 flew") in 4 %**.
  - These windows span a median of 34 s of route time (up to 81 s).
- **Contiguous 30 s / 15 s windows:** synthetic z > 3 in 84-100 %. The null reads |z| > 3 in 4-8 % with a 1 s block bootstrap
  and **12-14 % with a 3 s block**, which fires FB-10(ii) as written.
  - The 1 s blocks understate the SE for 0.3-1 Hz content.
  - The median window footprint is only 2-3.5 counts rms: quiet highway windows carry almost no signal.
- **Symptomatic windows (5-15 m/s, the top 12 by 1.6-3 Hz wheel-rate energy):** z of 25-58, and null beta p95 of 0.05-0.14.
- **The re-worded rule is error-free.** Beta alone (LIVE ≥ 0.5 / NOT ≤ 0.3) on all engaged frames, with a footprint gate of
  Σr² ≥ 5·(3.64/0.1)², gives **0 misclassifications** in every window set:
  - contiguous 30 s: 20 + 20 correct, 9 gated out;
  - contiguous 15 s: 25 + 25 correct, 30 gated out;
  - **symptomatic 15 s and 30 s: 12/12 in both arms**.
  - Ungated, the null reads LIVE in 1-2 of 27-55 windows.
- The design's |bar| < 400 mask removes exactly the high-α frames (metric agent P1). Using all engaged frames raises z (30 s
  contiguous: median 15.9 against 11.8).

**(b) The trim-footprint |K| (read #2) [E sim, the metric's own code].**

| | pooled \|K\| [CI], phase | 30 s windows, p5-p95 | 15 s windows, p5-p95 |
|---|---|---|---|
| V294 real, 0.3-1 Hz | **0.193 [0.184, 0.200] at +157°** (reproduces the metric report) | 0.116-0.327 | 0.107-0.458 |
| A1017 synthetic, 0.3-1 Hz | **0.316 [0.307, 0.325] at +141°** | 0.173-0.399 | 0.211-0.502 |
| A1017 synthetic, 1-3 Hz | 0.155 [0.146, 0.162] at +96° | | |
| A1017 synthetic, 3-8 Hz | 0.067 at +56° | | |

- **The design's predictions sit outside the synthetic's own pooled CIs.** It predicts 0.33 / 0.17 / 0.064; the ratio method is
  4 % and 9 % high in the first two bands. They should be restated as 0.316 / 0.155 / 0.067.
- **The sentences as written, per window** (the joint rule: LIVE = beta ≥ 0.5 AND |K| ≥ 0.28; STOP-ARITH = |K| > 0.45 or
  dphase < −30):

  | window | A1017 synthetic | V294 null |
  |---|---|---|
  | contiguous 30 s | LIVE 19/28, AMBIGUOUS 4, **STOP-ARITH 5** | **STOP-ARITH 4/28** |
  | contiguous 15 s | LIVE 29/51, AMBIGUOUS 12, **STOP-ARITH 10** | **STOP-ARITH 8/51** |
  | symptomatic 15 s | LIVE 8/12, AMBIGUOUS 3, STOP-ARITH 1 | — |

- **Duration needed for |K|:** at ≥ 60 s of hands-off driving, A1017 reads ≥ 0.28 in 92 % of windows and the null in 0 %. At
  ≥ 120 s it is 100 % / 0 %, with 0 STOP-ARITH.

**(c) Symptom band [E].** The hard-turn 1.6-3 Hz wheel-rate rms, V294 against itself on r71b, has a null 5-95 % ratio of:

| hard-turn driving | null 5-95 % ratio |
|---|---|
| 15 s | [0.10, 9.5] |
| 60 s | [0.39, 2.6] |
| 120 s | [0.53, 1.90] |

The predicted ×0.89-0.98 is invisible there; the design rightly calls this read secondary. The symptom outcome therefore rests
on the operator's feel alone. "Jerky as V294" is the design's own predicted outcome in the identified world (×0.94-0.98). **The
null sentence therefore licenses only "the pole lever is exhausted at int32 margin 2 for this jerk"**, which the int32 ceiling
already implies. It licenses no statement about the jerk's physics beyond that.

**The sentences a result licenses, re-worded (what I require):**
1. **LIVE / NOT (primary).** Exact-model beta on **all engaged frames** of the symptomatic episode, or pooled over the drive,
   counting only windows with Σr² ≥ 5·(3.64/0.1)².
   - beta ≥ 0.5 → A1017 is on the car.
   - beta ≤ 0.3 → it is not: STOP.
   - Otherwise → pool more frames.
2. **Transfer check (secondary).** The metric's |K| is used **only pooled over ≥ 120 s** of hands-off engaged driving, with the
   60 s block bootstrap. Expect 0.316 at +141° (0.3-1 Hz).
   - STOP-ARITH only if the **pooled CI** excludes [0.25, 0.40], or the pooled phase shift is outside [−30°, 0°].
   - Never apply it to a single 15-30 s window.
3. **Risk statement.** Replace "soft-EME unchanged" with the replay's dwell numbers from section 3.
4. **Lineage.** Correct the three framing items in section 4.

## 7. Files (all in `analysis-2020accord/studies/v295/design/dynamics/`)

- `ADV-bytes-CRITERIA.md` — the pre-registered FAIL criteria.
- `advb1_bytes.py` — cells, reader scan, V293→V294 diff.
- `advb2_consumers.py` — consumers of the changed gp cells.
- `advb3_redo_ladder.py` — A1017 in the V294 redo audit's outer-loop model.
- `advb4_arith.py` — mirror spot-checks, int32, settling, restart pulse, surface, HF.
- `advb5_ram_mirror.py` — the 0xFA800000 cal mirror.
- `advb6_observe.py` / `.json`, `advb7_joint_rule.py`, `advb12_K_duration.py`, `advb13_beta_only.py` — observability.
- `advb8_crc.py` — CRC and cal-only check, in memory.
- `advb9_replay.py`, `advb9b_hightrim.py` — replay internals and the high-trim dwell.
- `advb10_band_noise.py` — the symptom-band null spread.
- `advb11_trim_tf.py` — the closed-form trim transfer.

Each script has an `*_out.txt` beside it. The march cache is `_scratch/advb6_march.npz`.

**Not done / residuals.**
- I did not use the harness `score()` and did not re-run a retrodiction row. No conclusion here rests on the plant family.
- Register-indirect writers of gp-0x680a are the standing residual.
- The base-assist magnitude at the low-speed high-trim episodes is unmodelled, so the soft-EME consequence is [B].
- If I find a defect after reporting, I will report it and not fix it.
