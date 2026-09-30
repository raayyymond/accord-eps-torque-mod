# ADV "bytes+instrument" on V295 trim-ratio: b at 0xC63EA, 567 → 964

**Verdict: SURVIVES_WITH_CHANGES.**

Adversary subagent, 2026-09-30. Design phase only.
- Nothing was built, flashed or sent.
- No image or `.rwd` was written.
- No fork, firmware-repo, STATE, memory, lineage or golden-model file was touched.
- Nothing was committed.

The FAIL criteria were written before any computation: `adv_bytes/CRITERIA-ADV-bytes.md`. Scripts and outputs are in `adv_bytes/`.

Every decision-bearing claim below is marked **[E]** EVIDENCE (with its method) or **[B]** BELIEF. Every number was re-derived from the V294 **image** (sha256 `3143616d…dbdd85`, re-hashed), not from the designer's constants.

---

## 0. Bottom line

**Nothing in the bytes, the arithmetic, the interlocks, the lineage or the cal-only claim breaks.**
- The cell has exactly one reader, and it is private to the LKAS PID.
- Every int32 intermediate holds with margin 2.387.
- The delivered surface is bit-identical at 4,820 points.
- The edit lives in a CRC block that V294 already re-CRC'd and flew.
- The edit is observable. On r71b's own excitation, one 15–30 s window with ≥ 7.5 s of hands-off frames separates b 964 from V294 with d′ 8–14.

**Four defects in the design's *wire-read protocol* must be fixed before it flies.** None of them is a reason not to flash the cell value itself.

1. **Read (1) would misfire on the CORRECT image [E].**
   - The pre-registered line is "FF identity must stay R² ≥ 0.98 on all engaged frames".
   - The identity estimator has no trim term, so the ×1.7 trim lands in its residual.
   - The correct b 964 image reads **R² 0.9698** on r71b. V294 reads 0.9868. Method: the real `identity_block` on a fake-tap route.
   - The |acc| < 20 clause passes at 0.9977, but only 0.9970 against its 0.997 line if the residual is ×1.5.
2. **The E3 window rule is too strict for the drive the operator gives [E].**
   - The rule is "any contiguous 20 s hands-off window". r71b had only **6** such windows in 709 s of hands-off frames.
   - Sliding 15–30 s windows that need only ≥ 50 % hands-off frames separate cleanly (§4).
3. **The sentences leave gaps [E].** β in (0.25, 0.28), (0.04, 0.15) and (−0.10, −0.04), and identity R² in (0.95, 0.98), license nothing.
4. **The EFFECT sentences cannot be read from one short drive [E, ADDED-LATER criterion].**
   - The sentences are (a) "hard-turn 1.6–3 Hz rate down ≥ 20 %" and (b) "moved ≤ 10 % → stop turning this knob".
   - With nothing changed, a new drive with 15 s of 5–10 m/s hard frames reads r71b's value ×[0.73, 1.29] (5–95 %). With 30 s it reads ×[0.80, 1.21].
   - All of r71b had 34.6 s of such frames. The prediction (×0.87 nominal) sits inside that no-change scatter.
   - So a band null licenses nothing. The operator's report is the only decider of the effect.

---

## 1. (a) Bytes: the cell, its reader, and its consumers

| check | result | method |
|---|---|---|
| image | sha256 `3143616d5b79bdb7…89dbdd85` **MATCH** | [E] Python hash (`adv1`) |
| cell | `0xC63EA` = **567** (`37 02`), u16 LE. Neighbours: a 0xC63E8 = 1011, C 0xC62E6 = 1024, out-lag 992 / 507 | [E] Python byte read |
| reader width | `ld.hu 0x73ea[tp], r16` @0x28F86 (16-bit, zero-extended). 964 = 0x03C4 < 32768, so signedness is moot | [E] Ghidra dry-run listing 0x28F3C–0x28FBF (V294 program), Python decode |
| tp | tp = 0xB0000 + 0x7000 + r1 (0x8000) = **0xBF000**, set at 0x140CE–0x140D6 | [E] Ghidra dry-run of the reset code 0x140B0–0x140FF. The one "tp written" scan hit (0x140D2) is this setup |

**Reader census of every byte of [0xC63EA, 0xC63EC)**, scanned over the whole image [0, 0x100000), which includes the 0xC4xxx caves (`adv1`). Result: **exactly one**, 0x28F86.

- **Forms covered:**
  - 4-byte Format VII/VIII on any base, including the ld.bu bit-5 parity and hw2 bit-0 discriminators, and bit ops;
  - 6-byte Format XIV on any base, including r0-absolute disp23 = 0xC63EA;
  - a word access at 0xC63E8 that would span a and b;
  - absolute LE32 anywhere in [0xC62EC, 0xC63EB] (none);
  - register-built bases: 7,693 materialisations and 588 within disp16 reach, each with a 48-byte look-ahead for a load that hits the cell (none);
  - ep/sld reach (none).
- **Positive controls, all FOUND:**
  - a @0x28F8A;
  - C @0x28F96, 0x28F9C, 0x28FB8;
  - 6-byte gp-0x6752 @0x48E56;
  - LE32 0xCB994 @0x29DC8;
  - the jarl 0x22522 → FUN_00028ea6.
- **Second method: Ghidra `search_instructions`** for `0x73ea` finds exactly **1** in the stock `code.bin` (184,512 instructions) and **1** in the V294 program (171,309). For `0x73eb`, `0xc63e` and `0xc63ea`: 0. `get_xrefs_to(0xC63EA)` returns none; Ghidra does not resolve tp references.

**b's downstream consumers [E, decompile of FUN_00028ea6 plus scans].** b feeds s = gp-0x3d30. That cell has 1 ld and 1 st, both in the filter (Ghidra = Python, with control). From s it goes to r26, which is used in three places:

1. **E** (0x29D78) → P → S → output lag → **T = gp-0x6b38**. The readers of T in the V294 image (`adv6`) are:
   - 0x2B418, the forward copy → FUN_0002b422 clamp → gp-0x6b3a → the range monitor FUN_0002b57a;
   - 0x4E8D2 and 0x4E8E2, FUN_0004e82e, a diagnostic/data frame packer (decompiled: it only copies cmd, flags, bar, x and T into a buffer);
   - **0x55DF0 and 0xC4B40, the 427 tap.**

   Also: the dead twin's st @0x2A934, and the writer @0x2A23C.
2. **gp-0x6a34 = |r26>>5|** (st @0x290CA). Its readers are 0x2A0CA, the damper-mode path gated by gp-0x680a == 1, and 0x2AFAE in the twin FUN_0002a93a.
   - gp-0x680a has **2 readers and 0 writers** (`adv8`, control gp-0x3d2c found).
   - FUN_0002a93a and FUN_0002a892 have **0 callers** (jarl/jr disp22 and disp32, plus LE32 pointers; the control 0x22522 was found).
   - The value range of gp-0x6a34 is unchanged (0…32, since C is unchanged).
   - **No live consumer [E, with the census's standing residual: register-indirect writers of gp-0x680a are excluded only by operand scans plus the .data boot value].**
3. **The damper-mode sign** (the same unreachable path).

**The published gp-0x6b2e/32/34/36 cells** have **no live reader**. The twin writes them, and FUN_00028ea6 stores them (Ghidra `-0x6b3` search). **Nothing outside the LKAS lane reads any b-derived quantity except through T.**

---

## 2. (a) Integer arithmetic at b = 964, on my own mirror

The mirror is `adv_mirror.py`, written from this session's decompile and listing. It is not the harness Lane, not `plib`, and not the golden model.

**Two-method validation [E]:**
- the mirror equals the harness `Lane` on 6,000 random ticks (b 567 and b 964, all 241 idx, tapers 254/178/76/203): 0 mismatches;
- it equals the golden model (`lkas_fb_lag` + `lkas_rate_pid_tick`) at b 964 on 8,000 ticks: 0 mismatches (`adv9`);
- it equals `plib.T1k_live` **bit for bit on all 1,020,390 r71b ticks** (`adv2`).

| quantity | V294 | **b 964** | designer | verdict | method |
|---|---|---|---|---|---|
| bail window | x ∈ [−12000, 12000] (`addi 0x2ee0` ; `addi −0x5dc1,r0` ; `bnc`) | same | same | ✓ | [E] listing |
| fb fixed point at x = ±12000 | +523,265 / −523,422 | **+889,699 / −889,856** | – | – | [E] iterate the exact floors |
| int32 margin 2³¹/\|a·s\| | 4.059 | **2.387** | 2.39 | ✓ reproduces | [E] |
| adversarial x (square waves, half-periods 1–400 ticks, full swing, plus 200 k random ticks) | – | max \|a·s\| 893.8 M → margin **2.403**, no overflow | – | ✓ | [E] |
| b·x | – | ≤ 11.57 M | – | ≪ 2³¹ | [E] |
| overflow edge | – | b 2301 margin **1.000**; b 1134 margin 2.029 | b_max 2301 | ✓ | [E] |
| E, E·Kp, taper·S, output-lag products, y·ramp, yr·gain | unchanged (b does not enter). \|E\| ≤ 5152, y·ramp ≤ 5·10⁸ | same | – | ✓ | [E] mirror `chk()` on every product |
| surface T(idx) at x = 0, 241 idx × 10 taper states × both signs | – | **identical at 4,820 / 4,820 points**; non-monotone steps 0 / 0 | 723 / 723 | ✓ | [E] |
| rail | +2461 / −2463 | +2461 / −2463 | same | ✓ | [E] |
| constant-rate turn (49 x values) | – | steady r26 ≠ 0 in **0** cases, so the trim has no DC | – | ✓ | [E] |
| zero-command torque, r26 at ±C | +615 / −616 | +615 / −616 | 616 | ✓ | [E] |
| zero-command, 300 deg/s-amplitude chirp 0.2–20 Hz | max 563 | max **615** (reaches the cap) | – | cap unchanged, reached sooner | [E] |
| restart pulse (one bail tick), peak at 10 / 30 / 100 / 300 deg/s | 21 / 48 / 149 / 424 | **30 / 78 / 251 / 545** | 24 / 73 / 246 / 542 | ✓ ≤ 616. The difference is method: mine includes the ~10 T dip of the bail tick itself | [E] |
| restart > 50 T | 0 / 0 / 164 / 254 ms | 0 / 97 / 209 / 296 ms | 0 / 89 / 206 / 293 | ✓ | [E] |
| \|P/x\| at 20 Hz, small signal | 2.079 | **3.536** | 3.535 | ✓ | [E] sinusoid march, amplitude 25–125 deg/s (`adv2b`) |
| \|T/x\| ratio at 2.5 / 10 / 20 / 25 Hz | – | **×1.700–1.706** | ×1.70 | ✓ | [E] |
| K_α (200 deg/s² ramp) | 0.2100 | **0.3600** | 0.356 closed form | ✓ | [E] |
| C bind on r71b engaged ticks | 0 % | **0.00300 %** | 0.003 % | ✓ | [E] |
| r71b replay, max \|T\| | 1467 | **1311** (lower) | – | no new peak | [E] |
| r71b replay, max \|T964 − T567\| | – | 215 T | – | – | [E] |

**Caveat, not a FAIL [E].** The "×1.70 HF damping" is linear only below an HF wheel-rate amplitude of **136 deg/s**, where r26 = C. V294's limit was 231 deg/s. A 250 deg/s 20 Hz test saturates b 964's |P/x| at 2.32. Above that amplitude the damper is cap-limited at the same 616 T as V294. On r71b this is irrelevant (0.003 % of ticks).

**Floor and clamp ordering [E].**
- s stores the **unclamped** s_new (st.w @0x28FA8 comes before the clamp), so clipping r26 never winds up the state.
- The negative fixed point is 157 counts larger than the positive, which is harmless.

---

## 3. (b) Interlocks

- **The lane's reachable output set is unchanged [E].**
  - The rail is +2461/−2463, set by the P clamp as on V294.
  - The zero-command cap is 616.
  - The r71b replay max |T| falls.
  - So the lane clamp (3072), the forward clamp (3072) and the aggregator (±0x2800) cannot be newly reached. Neither can the soft-EME band 5120–5325 through the lane alone.
- **FUN_0002b57a [E, decompile].** It is a range check of gp-0x6b3a against ±[0xC61B2] ± 0.003, plus a sequence counter. gp-0x6b3a is already clamped to ±3072, and the rail is 2461. It cannot trip.
- **No monitor reads r26, s, gp-0x6a34 or the published PID cells [E, the §1 census].** T's only readers are the forward path, the tap and a diagnostic packer.
- **BELIEF residuals.**
  - Base assist is not modelled. The trim at ×1.7 opposes driver-driven wheel acceleration more strongly below 2 Hz: a "heavier wheel", up to 616 T, derated by taper D to ×0.30 at |bar>>5| ≥ 64.
  - I found no DTC reader of T that could see this.
  - The aggregator lockstep (gp-0x6b94/gp-0x4ce0) is value-independent (inherited).
- **P-clamp rectification at high idx [B].** P clips the assisting trim from idx ≈ 179, so an oscillating trim at very high demand would rectify into a small bias.
  - On r71b the lane never exceeded 60 % of the rail, so it did not occur there.
  - At ×1.7 it would start at a lower idx. It is not reached on r71b-like driving.

**B1 and B2 do not fire.**

---

## 4. (d) Observability: can one short drive see b = 964?

`adv4_observe.py`. The lane march is my own mirror; the E3 reader is re-implemented.

**Construction.** The designer's fake tap is: real r71b tap − quant(V294 march) + quant(b964 march). It is stressed by scaling the real residual **×1.5 and ×2**, i.e. up to all of it following the edit.
- The measured trim-proportional share of the residual variance is 3.8 %.
- The residual rms by |trim| quartile is 3.33 / 4.40 / 3.62 / 5.08 counts.

**Control [E]:** pooled hands-off β is V294 **+0.212** and b964 **+0.361**, against the designer's +0.213 / +0.361.

**E3 β per window** (5–95 %). "b964 misread as V294" is the fraction of b964 windows landing in the "V294 gain" band +0.15…+0.25.

| window rule | n | V294 | b964 | d′ | b964 < 0.28 | b964 misread as V294 |
|---|---|---|---|---|---|---|
| designer: contiguous 20 s hands-off, k 1 | **6** | [0.152, 0.222] | [0.282, 0.345] | 5.0 | 0 | 0 |
| same, k 2 | 6 | [0.132, 0.240] | [0.262, 0.361] | 3.4 | 0.33 | 0 |
| **sliding 15 s, ≥ 50 % hands-off, k 1** | 292 | [0.175, 0.221] | **[0.311, 0.365]** | 10.4 | 0.017 | 0.003 |
| same, k 2 | 292 | [0.166, 0.236] | [0.305, 0.373] | 8.2 | 0.031 | 0.014 |
| sliding 20 / 30 s, ≥ 50 % hands-off, k 1 | 288 / 283 | [0.183, 0.218] / [0.190, 0.215] | [0.317, 0.365] / [0.324, 0.364] | 11.9 / 13.7 | ≤ 0.003 | 0 |
| sliding 15 s, **all engaged, the flown plain Rm** | 298 | [0.115, 0.213] | [0.211, 0.351] | 3.5 | **0.275** | **0.128** |
| same, **Rm × taper m/254** | 298 | [0.165, 0.214] | [0.289, 0.357] | 9.4 | 0.023 | 0.003 |
| medium-speed hard turns (5–15 m/s, \|angle\| ≥ 45°), 15 s, all engaged, taper Rm | 11 | [0.202, 0.211] | [0.342, 0.356] | 31 | 0 | 0 |
| 2-minute drive chunks, pooled hands-off | 16 | [0.201, 0.215] | [0.341, 0.364] | 21 | 0 | 0 |

**Reading [E for the arithmetic; the next drive's excitation is B]:**
- b 964 is visible on the existing wire from a single 15 s window with ≥ 7.5 s of hands-off frames.
- On r71b the hard turns at 5–15 m/s were **82 % hands-off** (median), so the symptomatic episode itself supplies the read.
- **The designer's "contiguous 20 s hands-off" rule** is what r71b could satisfy only 6 times. Under a ×2 residual it drops a third of b964 windows below the 0.28 line, into the gap.
- **Dropping the hands-off filter while keeping the flown plain Rm** misreads 13 % of b964 windows as "V294 gain / the edit did not reach the ECU". The taper-scaled Rm fixes that.

**D4 [E].** The instrument is on the wire and would be byte-identical in V295. The 427 tap reads T (gp-0x6b38) at 0x55DF0 and 0xC4B40, and it reproduced the march at 3.64 counts rms on r71b.

**SEL is entailed by construction, not evidence of observability [E].**
- rms(fake964 − q964) equals rms(real tap − q567) = 3.6414 identically. So the true hypothesis always scores the real V294 residual.
- On the **real** V294 tap, SEL named the right image in only 4 of 6 windows. It named "null" once and b850 once.
- Use SEL as a read only. Its 6/6 on b 964 is not a result.

**Read (1), the FF identity, misfires on the correct image [E]** (`adv10`: the real `identity_block` on the r71b route object):

| tap | all engaged R² | \|acc\| < 20 R² |
|---|---|---|
| V294, real (control) | 0.9868 (resid 22.4) | 0.9981 |
| **b 964, fake** | **0.9698** (resid 33.8) | 0.9977 |
| b 964, residual ×1.5 | 0.9693 | **0.9970** |

The pre-registered "must stay ≥ 0.98 on all engaged frames" is **FALSE for the correct build**. The all-engaged clause is not an identity test once the trim changes, and the |acc| < 20 clause has no margin.

**The effect band from one short drive [E, measured side only]** (`adv7`, `adv7b`). This is the hard-turn 1.6–3 Hz wheel-rate rms, using the harness definition, resampled over r71b's own hard episodes. The ratio is what a no-change drive would read against r71b:

| band | hard frames on r71b | per-episode CV | 15 s of hard frames | 30 s |
|---|---|---|---|---|
| 5–10 m/s | 34.6 s in 12 episodes | 0.43 | **[0.73, 1.29]** | **[0.80, 1.21]** |
| 15–22 m/s | 13.6 s in **2** episodes | 0.59 | n/a | n/a |

- Normalising by the 1.6–3 Hz command does not help: [0.70, 1.40] at 15 s.
- The design's predicted ×0.87 (nominal) and ×0.75 (prior) sit inside or on the edge of the no-change scatter. Drive-to-drive road differences add to it.
- **Sentence (b), "band ≤ 10 % → the jerk is not governed by 2 Hz damping at any HF-safe dose; stop turning this knob", cannot be licensed by the band.**

**The null sentence I would license:**
- **If E3 reads ≥ +0.27 on a 15–30 s window with ≥ 7.5 s hands-off, or pooled over the drive:** b 964 is on the car. The trim is ×1.7 V294's, with the right sign.
- **If the operator feels no change:** "the ×1.7 dose is not felt". It is **not** "2 Hz damping cannot govern the jerk". The band cannot distinguish ×0.87 from ×1.0 at this exposure.

---

## 5. (c) Lineage

`adv3`: 297 distinct 1 MB images on disk. The designer's s9 says 252; the difference is not decision-bearing.

| (op @0x28FA4, shl, a, b, C) | images |
|---|---|
| add, 5, 923, **1560**, 7680 / 46080 / 0 / 15360 | 273 / 15 / 3 / 2 |
| add, 5, 962, **958**, 46080 | 2 (V291c10 superseded, **V292 flown → REVERT**) |
| add, 5, 875, **2301**, 46080 | 1 (**V289 flown**, ring moved to 16 Hz) |
| **subr, 2, 1011, 567, 1024** | **1: V294 only, flown on r71b** |

- The difference operand exists on exactly one image. b 964 exists on none.
- Grep of `builds/**/build_v*_tva.py` and `docs/BUILD-LINEAGE*.md` finds these other values:
  - 3522: V290-C, **unbuilt**, sum operand;
  - 958: V291/V292;
  - 2301: V289.
- **No same-operand value was ever flown and falsified. C1 does not fire.**
- **What is different this time [B, stated plainly].** Nothing but the dose. It is a dose step on a lever whose liveness and sign are EVIDENCE (r71b β +0.210). Its effect on the jerk band on-car is **unknown**: V294 vs V293 on r75/r76 is confounded by the fork config.
- **Record gap, reported and not edited:** `docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md`'s 0xC63E8/0xC63EA row stops at "V293 restores 923/1560". It has no V294 (1011/567, difference operand) entry.

---

## 6. (e) One build, cal-only

`adv5` [E]:
- 0xC63EA lies in CRC block **[0xC6000, 0xC6FFC), trailer @0xC6FFC**, inside both the bootloader walk (49 blocks) and the full chain (50).
- The V293 → V294 diff already moved that trailer (0xC6FFC–0xC7000) together with 0xC62E7, 0xC63E8 and 0xC63EA, and V294 flew with no faults.
- **V295 = 2 payload bytes (0237 → 03C4) + 4 CRC bytes in one already-exercised block.** No code byte changes. One build. **E1 does not fire.**

---

## 7. What fired, against my pre-registered criteria

| criterion | fired? |
|---|---|
| A1–A4 (image, width, second consumer, int32, surface) | **no** [E] |
| A5 numbers reproduce | yes, within method. Restart pulse at 10 deg/s is 30 vs 24 (bail-dip method, non-decision-bearing) |
| B1 / B2 | **no** |
| C1 | **no**. C2: record gap (PART1 index) |
| D1 | **partial**: separable from one window, but **not under the designer's contiguous-20 s-hands-off rule with a ×2 residual**, and not with the plain Rm on hands-on frames. The fix is to name the window rule |
| D2 | SEL circular (finding). E3 is honest, and survives ×2 residual inflation |
| D3 | **yes**: sentence gaps, **and read (1)'s R² ≥ 0.98 fails on the correct image** |
| D4 | no |
| E1 | no |
| ADDED-LATER: effect-band measurability | **yes**: the band arm of sentences (a)/(b) is not interpretable from one short drive |

**Decision: SURVIVES_WITH_CHANGES.** No REFUTE clause fired. The flash-relevant facts all hold (cell, arithmetic, interlocks, cal-only). The read protocol must be corrected before the drive, or a correct flash would be read as a failed identity check, and a null would be over-interpreted.

## Files

All in `analysis-2020accord/studies/v295/design/trim-ratio/adv_bytes/`:

| file | contents |
|---|---|
| `CRITERIA-ADV-bytes.md` | pre-registered FAIL criteria |
| `adv_mirror.py` | independent integer mirror |
| `adv1_reader_census.py` / `_out.txt` | reader census |
| `adv2_arith.py` / `_out.txt` | arithmetic |
| `adv2b_pgain.py` / `_out.txt` | linear gains |
| `adv3_lineage.py` / `_out.txt` | the cell across 297 images |
| `adv4_observe.py` / `_out.txt` | E3 observability |
| `adv5_crc_block.py` / `_out.txt` | CRC block |
| `adv6_T_readers.py` / `_out.txt` | readers of T |
| `adv7_band_scatter.py`, `adv7b_band_norm.py` / `_out.txt` | effect-band scatter |
| `adv8_damper_mode.py` / `_out.txt` | gp-0x680a census |
| `adv9_golden.py` / `_out.txt` | mirror vs golden model |
| `adv10_identity.py` / `_out.txt` | FF identity on the fake tap |
| `_adv_march_r71b.npz` | regenerable march cache |

Ghidra: read-only (decompile, `search_instructions`, `get_xrefs_to`, and `disassemble_bytes` with `dry_run: true` only). Nothing saved, no program opened or closed.
