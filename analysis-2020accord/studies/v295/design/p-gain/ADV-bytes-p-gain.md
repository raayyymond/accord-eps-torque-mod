# ADV-bytes-p-gain: adversary "bytes + instrument" against R1.3_8_100

Subagent, 2026-09-30. **Design review only.**
- Nothing was built, flashed or sent. The edit was applied **in memory** to count bytes and walk the CRC chain; no image and no `.rwd` was written.
- No fork file was touched, and neither was STATE, memory, lineage, the golden model or CLAUDE.md. Nothing was committed.
- FAIL criteria were written **before** any number was computed: `ADV-bytes-p-gain-CRITERIA.md` (PB-1 … PB-14).
- Default verdict for any claim I could not reproduce was REFUTED.
- Every decision-bearing claim is tagged **[E]** EVIDENCE (with method) or **[B]** BELIEF.

**Candidate.** Kp bank `0xCB994`, all 28 records rewritten.

| | X (knots) | Y (Kp) |
|---|---|---|
| V294 (live slot 7) | 0, 68, 112, 136, 208 | 960 at every knot |
| R1.3_8_100 | 0, 8, 54, 100, 208 | 1248, 1248, 1104, 960, 960 |

## Verdict: SURVIVES_WITH_CHANGES

**Byte and arithmetic claims.** Every one reproduces from the V294 image with my own code and a second method.
- No second consumer exists.
- No interlock is newly reachable.
- Each cell's lineage is as stated.
- The build is one cal-only build.

**The pre-registered edit-live read (R-PLATEAU) works**, and its baseline transfers across drives:
- It reads the same on six other routes: [E] 0.935–0.940 against r71b's 0.938.

**Three things in the wire plan are wrong or undecidable.** None of them makes the edit unsafe or invisible, so none is a FAIL:
1. **R-PLATEAU cannot see the taper.**
   - A flat-1248 image reads R-PLATEAU = 1.32, identical to the candidate. So does an image with Y written but X left unwritten. The flat-1248 image is exactly the family this lens pre-registered as a G6 FAIL.
   - The design's null sentence attributes the drive to R1.3_8_100 on the plateau read alone.
   - A taper read exists and is decidable in about 60 s of ordinary engaged driving, but it must be added as a gate.
2. **Null sentences 2 and 3 have thresholds inside r71b's own sampling spread**, so they cannot be decided from one drive.
3. **The local-slope minimum is 0.68 at idx 96–99, not 0.72.** This is a small correction to the stated hard-turn risk.

---

## 1. Criteria scorecard

| id | criterion (abridged) | result | evidence |
|---|---|---|---|
| PB-1 | base image, pointers, bytes, live record | **PASS** | §2.1 |
| PB-2 | record extent / aliasing | **PASS** | §2.2 |
| PB-3 | reader census of 0xCB994 + records | **PASS** | §2.3 |
| PB-4 | second consumers of the LERP output / P | **PASS** | §2.4 |
| PB-5 | LERP arithmetic (signed divide, knots, boundaries) | **PASS** | §3.1 |
| PB-6 | int32 | **PASS** | §3.2 |
| PB-7 | delivered surface (monotone, rail, +85 T, idx ≥ 100 unchanged) | **PASS**; local-slope minimum misreported (finding) | §3.3 |
| PB-8 | zero-command torque, restart pulse | **PASS** (exact) | §3.4 |
| PB-9 | interlocks | **PASS** [E structure; B soft-EME dwell] | §4 |
| PB-10 | lineage | **PASS** | §5 |
| PB-11 | R-PLATEAU on byte-exact model + measured noise | **PASS** (15 s windows marginal on the ±0.05 bands) | §6.1–6.2 |
| PB-12 | each changed value readable | **finding**: plateau blind to the taper; taper readable in ~60 s of ordinary driving; taper end over the whole drive; non-live records unobservable by construction | §6.3 |
| PB-13 | null sentences decidable | **finding**: sentences 2 and 3 are undecidable at their thresholds | §6.4 |
| PB-14 | one build, cal-only | **PASS** | §7 |

**What a FAIL would have looked like (from the criteria file), and why none fired:**
- A second reader of the records; a Kp outside [960, 1248]; a non-monotone step; a rail change; an interlock newly reachable; a Kp schedule that has already flown and been falsified.
- A plateau read that could not separate the candidate from V294 in one short window, or that collapses under pessimistic noise.
- A changed value with no read at any exposure.
- More than 252 payload bytes plus CRC trailers.
- None of these occurred.

---

## 2. Bytes: from the V294 image (`advp1_bytes.py`, `advp1b_twin.py`, `advp2_consumers.py`)

### 2.1 Base [E: Python LE read of the image]
- The image sha256 is `3143616d…dbdd85`.
- `u32(0xCB994 + 4k)` for k = 0..27 gives 28 distinct records at a 24-byte stride:
  - 0xE4360–0xE43D8, 0xE5360–0xE53D8, 0xE6360–0xE63D8 and 0xE7360–0xE73D8 (six records each);
  - 0xE8240–0xE8288 (four records).
- Every record has n = 5, with Y = 960 at all five knots. Pad bytes at rec+0x16 are `0000`.
- X differs by slot, exactly as the design's §3.3 table says.
- All 28 `bytes_v294` blocks in the spec JSON match the image byte for byte.
- Live slot 7 is `0xE5378`, with X [0,68,112,136,208] and Y 960 at all five knots. Ghidra `read_memory` on the open `/advC/_v294…` program gives the same 24 bytes, and 0x29D76 reads `c282` (shl 2): the program is V294, not a stale import.
- Globals read from the image:

  | cell | value |
  |---|---|
  | idx clamp | 240 / 240 |
  | P clamp | 15360 |
  | sum clamp | 15360 |
  | Ki | 0 |
  | D clamp | 0 |
  | C | 1024 |
  | a / b | 1011 / 567 |
  | output lag | 992 / 507 |
  | gain | 5346 |
  | lane clamp | 3072 |
  | forward clamp | 3072 |
  | ramp-down gate | 1 / 102 |

### 2.2 Aliasing [E: full-image LE32 scan at every alignment]
- **No LE32 anywhere in the image points into any Kp record** outside the 0xCB994 table. The table's own 28 entries were found: that is the control.
- The only pointers within one stride of a record are **neighbouring banks' records**, which are adjacent and do not overlap:
  - the G same-sign bank 0xCB924 slot 5 → 0xE434C (n = 4, ends 0xE435E, below the first changed byte 0xE4362);
  - the G-override bank 0xCBA04 → 0xE4404, after the last Kp record.
- No changed byte (rec+2 … rec+0x15) is shared with another bank.

### 2.3 Readers of the bank and the records [E: raw LE scans with positive controls, plus Ghidra]
- **`mov imm32 0xCB994`** appears at exactly two sites:
  - 0x29DC6, the live PID;
  - 0x2ACB8, the twin island 0x2A30E–0x2B421.
- **Controls found by the same scanner:**
  - the Kd bank 0xCB7D4 at 0x29E76 and 0x2AD64;
  - the map 0xC9A88 at 0x29CFC and 0x2ABF2.
- **No other form reads the bank:**
  - no movhi/movea pair forms 0xCB994 (the two `movhi 0xD` sites address 0xCEFF4 and 0xCD01B);
  - the tp offset is 0xC994, beyond disp16 reach;
  - no 6-byte disp23 access (r0 or tp base) reads the table or any record. The 6-byte control, gp-0x6752 at 0x48E56, was found.
- **The records are not read directly by any code.** No `mov imm32` into 0xE4000–0xE9000 exists except 0x2F5C0 `mov 0xe4c39`. Ghidra shows that is a trig constant feeding `mulu`, next to 0x3243F7 and 0x1921FB, which are π and π/2.
- **The twin island is uncalled** [E]:
  - No Format-V `jr`/`jarl` disp22 and no 6-byte disp32 jump from outside lands in it. The control, `jarl 0x28EA6` at 0x22522, was found.
  - No movhi+movea pair forms an address inside it. (This scan has no available positive control, because 0x28EA6 is reached by `jarl`.)
  - Three LE32/imm32 hits inside the island were adjudicated:
    - 0x1E4C8 → 0x2AE0B is odd, so it cannot be code;
    - 0x75B78 → 0x2A61E is inside code bytes;
    - 0x5A366 `mov 0x2b000, r8` is stored to peripheral register 0xFF6C1044 (`movhi -0x94, r17`; `st.w r8, 0x1044[r17]`). It is a constant, not a call.
  - **The island's status is not decision-bearing** [E]: if it were live, it reads the same 28 records through the same pointer table, so the two copies cannot disagree.

### 2.4 Second consumers of what Kp changes [E: decompile of FUN_00028ea6 on V294, then the raw scan, both encodings]

**The Kp LERP result goes only into the P multiply.** The listing is `zxh r9` → `mul r9, r8` at 0x29E36.

Stored products and who reads them:

| cell | what it holds | readers |
|---|---|---|
| gp-0x6b32 | P | **0** |
| gp-0x6b34 | raw sum | **0** |
| gp-0x6b36 | D | **0** |
| gp-0x697a | idx | **0** |
| gp-0x6b2e | S | the twin only (0x2A896) |
| gp-0x6b30 | the gate's previous yr | the PID (0x2A1D4) and the twin |
| gp-0x6b38 | T | see below |

Readers of **gp-0x6b38 (T)**:
- 0x2B418: the forward copy → gp-0x6b3c → FUN_0002b422 clamp → gp-0x6b3a → the monitor FUN_0002b57a;
- 0x55DF0: the 427 packer;
- 0x4E8D2 / 0x4E8E2: FUN_0004e82e, a **diagnostic response packer**. It byte-packs cmd, rate x, T and flags into a 0x38-byte buffer. It has no threshold and no compare.

**The damper lane (gp-0x680a == 1 → 0x2A0C6) is not a consumer:**
- It reads r26, which the Kp edit does not change.
- It is unreachable: 2 readers and **0 writers** in both encodings. The control, `st.b gp-0x674b` at 0x29D14, was found.

---

## 3. Arithmetic: my own lane, written from the listing (`advp_lane.py`, `advp3_arith.py`)

### 3.1 The Kp LERP [E: Ghidra decompile first, then the `dry_run` listing 0x29DC6–0x29E5E on the V294 program]

```python
# 0x29DC6 mov 0xcb994,r10 ; ep = r9 = sel*4 + 0xcb994 ; sld.w/ld.w -> rec
# 0x29DDE sld.hu 2[ep] = X0 ; 0x29DE2 add 0xc,r10 (-> Y0) ; 0x29DE8 zxh r7 (idx)
if not idx > X[0]: kp = Y[0]                 # 0x29DEA cmp r9,r7 ; bh   ; else 0x29DEE ld.hu 0[r10]
elif idx >= X[4]:  kp = Y[4]                 # 0x29DF4 sld.hu 8[ep] ; cmp ; bnc -> 0x29E04 ld.hu 8[r10]
else:
    k = first knot with X[k] > idx           # 0x29DFA..0x29E12 walk (bnc loops while idx >= X[k])
    num = (Y[k] - Y[k-1]) * (idx - X[k-1])   # 0x29E20 sub ; 0x29E24 sub ; 0x29E26 mul (low 32)
    kp = Y[k-1] + trunc0(num / (X[k] - X[k-1]))   # 0x29E2C divq r6,r9 (SIGNED) ; 0x29E30 add ; 0x29E32 zxh
P = clamp((E * kp) >> 8, +-[0xC61BC])        # 0x29E36 mul ; 0x29E3A ld.hu tp+0x71BC ; 0x29E3E sar 8
```

- **The knot count is fixed by code offsets**: X0 at rec+2, X4 at rec+0xA, Y0 at rec+0xC, Y4 at rec+0x14. The count word at rec+0 is **not read**.
- The divide is **`divq`**, which is signed. The same image carries `divqu` at 0x2F5BC, and Ghidra decodes the two differently.
- **My own listing-mirror LERP matches the golden `lkas_rate_lerp` on all 241 idx** (0 mismatches).
- **Kp over idx 0..255 is within [960, 1248] and non-increasing:**

  | idx | 0–8 | 9 | 18 | 34 | 50 | 54 | 75 | 92 | 99 | ≥ 100 |
  |---|---|---|---|---|---|---|---|---|---|---|
  | Kp | 1248 | 1245 | 1217 | 1167 | 1117 | 1104 | 1039 | 986 | 964 | 960 |

- idx is `|clamp(v, ±240)|`, so no idx beyond 240 and no negative idx reaches the LERP.

### 3.2 int32 [E]

| product | worst case | margin to 2³¹ |
|---|---|---|
| E·Kp, max over idx at \|r26\| = 1024 | 4.95·10⁶ (unchanged from V294, which reaches the same bound at idx 240 with Kp 960) | 434 |
| LERP numerator | ≤ 6624 | – |
| output-lag products (bounded by the sum clamp, which Kp does not move) | \|la·L\| ≤ 2.4·10⁸, y ≤ 15210 (< the sxh at 32767), y·gain ≤ 8.1·10⁷ | – |
| a·s, b·x | untouched by this edit | 4.06 (unchanged) |

The design quoted a margin of 335 from a looser bound. Both are safe.

### 3.3 Delivered surface [E: two methods, my own march and golden `lkas_rate_pid_surface`, 0 mismatches over 3 fb levels × 241 idx]
- **Monotone** in idx at every r26 from −1024 to +1024 in steps of 128 (17 levels).
- **Rail** 2461 / −2463, first reached at idx 239, the same as V294.
- **Largest increase +85 T at idx 51.**
- **No change at idx ≥ 100.**
- The static ratio is 1.333 / 1.311 / 1.266 / 1.217 / 1.163 / 1.083 / 1.026 at idx 3 / 6 / 18 / 34 / 50 / 75 / 92.

**Finding (minor).** The design's G3 row gives the minimum local-slope ratio as "0.72, idx 2–150". The true minimum is **0.68, at idx 96–99**:
- ±2-idx centred integer surface: 0.683 at idx 98;
- analytic `(map′·Kp + map·Kp′)/(map′·960)`: 0.728 / 0.701 / 0.683 at idx 92 / 96 / 99.

The fork's small-signal loop gain in the 5–10 m/s hard-turn region at idx 90–100 is therefore ×0.68–0.73, not ×0.72–0.9. This extends risk 3 ("slower response to a sudden demand change in those turns") slightly. It does not affect monotonicity.

### 3.4 Zero-command torque and restart pulse [E]

| | V294 | candidate | design |
|---|---|---|---|
| zero-command torque (idx 0, r26 = ∓1024) | 615 / −616 | **799 / −801** | 801 |
| restart pulse, peak \|ΔT\| at 10/30/100/300 deg/s | 14/43/145/419 | **18/56/188/545** | exact match |
| restart pulse, ms above 50 T | 0/0/160/253 | 0/46/184/275 | – |

The restart pulse was computed after a bail, with s restarting from 0 and x held constant, at idx 0. Every value is below the lane rail.

### 3.5 Harness tool check [E]
- The harness `Lane` marching the candidate on r71b equals my lane on the first 200,000 ticks: 0 mismatches.
- My V294 march equals plib's byte-exact march on all 1,020,390 ticks, both FF and live: 0 mismatches.

---

## 4. Interlocks [E structure; B where marked]

**The change is confined to idx < 100, and the lane's output range is unchanged.** Rail 2461 / −2463; the P clamp is not reached at idx ≤ 8 (max P ≈ 5674); the sum clamp is never binding with I = D = 0. Consequences:
- **Forward-lane monitor FUN_0002b57a.** Its operand gp-0x6b3a is clamped to ±[0xC61B2] before the compare (FUN_0002b422), so it is structurally unreachable by any lane value.
- **Soft-EME (gp-0x3570, band 5120–5325).** It sees the lane only through T, bounded by 3072 twice, and T's peak is unchanged.
  - The candidate adds at most +85 T of static torque (idx 51) and raises the zero-command trim cap by +185 T, only during wheel acceleration at idx < 100.
  - [B] The dwell change in the soft-EME band is negligible. The lane can still only reach it together with a large base assist, where the driver-torque taper D cuts LKAS.
- **Limiter comparator FUN_0004595a** (decompiled on code.bin). It compares |gp-0x6b94| with |gp-0x6ace| and their product.
  - gp-0x6ace is written at 0x454D2–0x455AE by code that reads gp-0x6b94 at 0x453E0, so it is a downstream representation of the same total command.
  - [B semantics] A scalar change of one lane, inside V294's existing range, cannot create a new disagreement.
  - Precedent [E, the record]: V282 flew a lane able to deliver 2463 T at zero command without a DTC. The candidate's worst case is 801.
- **Lockstep between the live PID and the twin.** Both read the same 28 records through the same table (§2.3), so they cannot diverge on Kp.
- **Ramp-down output gate (0xC64A3 = 1, 0xC61B8 = 102).** It acts only while ramping down. A larger |y| at small idx changes only when the gate releases; this is cosmetic.

---

## 5. Lineage [E: the Kp bank read from the BYTES of all 297 plain images on disk (`advp7_lineage.py`), plus the lineage docs]

| class | images | status |
|---|---|---|
| stock rising (slot 7 [248,512,645,696,696]; per-slot 248…717) | 263 images | flown |
| flat 248 (per-slot own Y[0]), rate operand | V281r3, V282, V283, V287r2, V288r2, V289, V291c10, V292 | flown where the lineage says so |
| V279 flat 256 | 1 | built, not flown |
| V281 rev 1 (248, 341×4) | 1 | superseded |
| **V281 rev 2 X (0,24,68,136,208)** | 1 | superseded, not flown |
| **V284 slot 7 only, X (0,32,36,44,88), Y (248,248,512,512,248): the ONLY falling Kp segment in any image** | 1 | **SHELVED, never driven** (`BUILD-LINEAGE.md` V284; TRACE-2026-09-09) |
| V285 Kp 0 | 1 | bench |
| V293 flat 120 × 28 | 1 | flown |
| V294 flat 960 × 28 (shl 2, subr) | 1 | flown r71b |

- **No non-flat Kp and no moved Kp X knot has ever flown. The regressive torque-mode schedule is untested, not falsified.** This matches the design's §10.
- **"What is different this time" is real** [E]:
  - V284 was shelved on V282's rate-loop 7.3 Hz margin (loop gain 0.976 at the ring). The shelving verdict read *"do not raise Kp anywhere without a fresh margin measurement"*.
  - That loop does not exist on V294: fb op `subr`, C 1024, 2 Hz fb pole, e_shift 2.
  - The fresh margins for the loops that do exist are the stability adversary's surface, not mine.
- Grep of `builds/**/build_v*_tva.py`: 22 scripts touch `0xCB994`. None writes a falling or moved-X table except V281 rev 2 and V284.
- The lever-index row `0xCB994` (PART1, line "bank 0xCB994") and PART6's V293/V294 rows agree with the bytes.

---

## 6. Observability: one short drive plus ordinary driving (`advp4_wire.py`, `advp5_crossroute.py`, `advp9_shape.py`, `advp6_nullsent.py`)

**Method.**
- My own lane marched r71b's recorded command and rate for six variants:
  - V294;
  - the candidate (CAND);
  - MB_flat1248, i.e. flat ×1.3: this is also "g1.3" and the pre-registered G6-FAIL family;
  - MB_Yonly: Y written, X left at V294's knots;
  - the runner-up R1.35_4_100;
  - flat g1.2.
- **Synthetic flight** = `quant(march at the tap tick) + r71b's own tap residual`, where the residual is real tap − quant(V294 march), rms 3.51.
- **Pessimistic variant:** residual × Kp(idx)/960. corr(|resid|, |dT|) is 0.155, so a torque-proportional part is plausible.
- **Windows** are consecutive blocks of **engaged** time: 15 s, 20 s and 30 s. Every window is counted, not only those pre-selected for exposure.
- **Regression:** `T_tap = a·F_V294 + b·R_V294 + c` on hands-off, off-rail tap frames at idx 0–8. Ratio = a / 0.9379.

### 6.1 R-PLATEAU per window [E: my own code; reproduces the design]

| window | qualifying (≥ 3 s idx 0–8 tap) | real V294 tap (null) | CAND | CAND, pessimistic noise | misfire of the ±0.05 bands | midpoint rule (> 1.15 = live) |
|---|---|---|---|---|---|---|
| 15 s | 41/53 (77 %) | 1.000 [0.939, 1.055] | 1.322 [1.249, 1.383] | 1.323 [1.230, 1.389] | null 10 %, CAND 10 % | 0 % / 0 % |
| 20 s | 38/40 (95 %) | 1.004 [0.962, 1.034] | 1.320 [1.280, 1.352] | 1.321 [1.267, 1.356] | null 5 %, CAND 3 % | 0 % / 0 % |
| 30 s | 25/26 (96 %) | 1.001 [0.964, 1.022] | 1.320 [1.286, 1.339] | 1.320 [1.274, 1.339] | 0 % / 0 % | 0 % / 0 % |

- **In symptomatic episodes:** 20 of the 21 30 s windows centred on a hard-turn run (idx ≥ 40, 5–22 m/s) qualify. The plateau read is available even in the episode the operator stops on.
- **The trim read** (b/b_base at idx 0–8) is CAND 1.31 [1.04, 1.47] against V294 0.99 [0.83, 1.19] per 20 s window. It overlaps per window and is a whole-drive confirmation only, as the design says. It is the same multiply as the FF, so it is not a separately changed value.

### 6.2 Is the baseline 0.938 transferable? [E: six V293 routes]
- V293's FF is bit-identical to V294's: `((sp<<5)·120)>>8 == ((sp<<2)·960)>>8` for every sp in ±1100 (asserted). V293's trim is 0.
- **The plateau slope on each route:**

  | route | plateau slope |
  |---|---|
  | r70 | 0.9356 |
  | r71 | 0.9369 |
  | r72 | 0.9399 |
  | r73 | 0.9394 |
  | r75 | 0.9352 |
  | r76 | 0.9364 |
  | mean (sd) | 0.9372 (0.0018) |
  | r71b | 0.9379 |

- The baseline is a property of the instrument, not of r71b. With a quantiser-aware regressor it reads 0.98–0.995. The sub-unity slope is the 427 tap's truncation toward zero at small |T|.
- **The candidate on each route's own residual** reads 1.29–1.32 against r71b's baseline.
- **Per-window null misfire rate** outside 1.00 ± 0.05 is 0–12 % (r70 12 %). The ±0.05 band is marginal; a midpoint threshold is not.

### 6.3 Each changed value [E]: finding PB-12

**The plateau read is blind to the taper.** MB_flat1248 and MB_Yonly read R-PLATEAU = **1.322**, the same as CAND, in every window at 15, 20 and 30 s. A flat-1248 image is the family this lens pre-registered as a G6 FAIL (hard-turn 1.6–3 Hz on light_b at 15–22 m/s, ×1.12). **The design's null sentence 1 would attribute a flat or X-unwritten image's drive to R1.3_8_100.**

**The taper can be read, with one statistic:**
- `TI = [a(idx 18–50)/a_V294(18–50)] / [a(idx 0–8)/a_V294(0–8)]`.
- Noiseless expectations: CAND **0.922**, flat and Y-only **0.985**, V294 0.997.
- **Decision midpoint: 0.953.**

| engaged chunk | chunks that read TI | CAND classified correctly | flat classified correctly |
|---|---|---|---|
| 20 s | 21/40 | 20/21 | 20/21 |
| 30 s | 19/26 | 18/19 | 19/19 |
| **60 s** | **13/13** | **13/13** (CAND 0.905–0.949) | **13/13** (flat 0.978–1.000) |
| 120 s | 6/6 | 6/6 | 6/6 |

⇒ **X1, X2 and Y2 are readable in about one minute of ordinary engaged driving.**

**The taper end (X3 = 100, the return to 960)** lives in idx 50–100, where r71b has only 29 s + 9 s of hands-off tap in the whole drive. It is readable **over the whole ordinary drive**:

| bin | CAND | flat | Y-only |
|---|---|---|---|
| 50–80 | 1.111 [1.105, 1.118] | 1.302 | 1.290 |
| 80–100 | 1.040 [0.997, 1.044] | 1.301 | 1.233 |

These are subsample block bootstraps over forty 20 s blocks, so the intervals are conservative. The taper end is not readable from one episode.

**Non-live records.** The 27 non-live records are unobservable on the wire by construction. They are inert while the selector is 7, which is measured on the wire (memory), and identical copies of the live record. Their correctness rests only on the build's byte census.

**No changed value is invisible at every exposure, so this is not a FAIL.** The null sentence must carry the taper gate.

### 6.4 Are the design's null sentences decidable? [E: r71b's own sampling spread, bootstrap]: finding PB-13

**Null 2**, part 1: "8–22 m/s turn-hold ≤ 0.72" (V294 0.67–0.69; predicted 0.75–0.78).
- My episode bootstrap (|la_des| 0.8–1.5 holds ≥ 1 s):

  | band | episodes | point | 95 % CI |
  |---|---|---|---|
  | 8–15 | 9 (17 s) | 0.734 | [0.593, 0.856] |
  | 15–22 | 5 (11 s) | 0.633 | [0.524, 0.737] |

- The half-width is 0.11–0.13, against a threshold 0.03 above baseline. **Undecidable.** A no-effect car can read 0.78 and an effective one can read 0.65.

**Null 2**, part 2: "22+ tracking ≤ 0.95" (V294 0.92; predicted ≈ 0.98).
- 22+ m/s had 4 blocks (74 s): gain 0.919, 95 % CI [0.763, 0.936]. **Undecidable.**
- **15–22 tracking is decidable:** 0.830 [0.800, 0.856], half-width 0.03 against a predicted +0.05 to +0.07. That band is DIRECTIONAL in the harness.

**Null 3:** "5–10 m/s matched hard-turn 1.6–3 Hz cell > ×1.10 vs r71b → revert".
- r71b's own cell, bootstrapped over its stretches:
  - hands-off: 3 stretches, 11.3 s, **×0.69–1.16** of the point;
  - engaged: 4 stretches, 13.7 s, **×0.62–1.17**;
  - 15–22 m/s: ×0.40–1.63.
- A second V294 drive would trip ×1.10 by sampling alone. **Undecidable. As written, it is a coin-flip revert.**

---

## 7. One build, cal-only [E: in-memory edit of the V294 image; `FF.crc_block_map` plus `walk` / `walk_all_blocks`]
- **Payload: 252 bytes**, 9 per record × 28, only inside rec+2 … rec+0x15.
- **The CRC chain moves exactly 5 trailers**, 20 bytes: blocks [0xE4000, 0xE4FFC) … [0xE8000, 0xE8FFC). The total diff is 272 bytes.
- Both chain walkers return 0 (clean) on the edited image.
- **All 5 blocks are ones V294's own builder already exercised** on these same records: its V293→V294 diff touched them, 280 bytes inside the Kp records.
- **Code region [0x13000, 0xC0000): 0 bytes changed.** No opcode is touched.
- The `.rwd` x31 checksum is the builder's standard step, the same as V294's.

---

## 8. Required changes (to reach "survives")

1. **Add a taper gate to null sentence 1.** R-PLATEAU = 1.30 means only that the plateau is live.
   - Pre-register TI (§6.3): live taper if **TI < 0.953** over ≥ 60 s of engaged ordinary driving. CAND reads 0.92; flat or X-unwritten reads 0.985.
   - Pre-register the whole-drive bins: 50–80 = 1.11 ± 0.03 and 80–100 ≈ 1.04 (V294 1.00; flat 1.30).
   - **Attribute nothing about hard turns or the highway outer loop to R1.3_8_100 unless the taper gate passes.** The taper is the design's whole safety argument against the flat ×1.3 G6 FAIL.
2. **Replace the "1.00 ± 0.05 / 1.30 ± 0.05" bands with a midpoint rule**: live > 1.15, not live < 1.08, ambiguous between. Alternatively, state the misfire rates: 10 % at 15 s windows, and 12 % null misfire on r70's residual.
3. **Rewrite null sentence 2** with CIs. Drop "turn-hold ≤ 0.72" and "22+ tracking ≤ 0.95" as single-drive decision rules.
   - Their r71b sampling half-widths are 0.11–0.13 and ±0.09.
   - Use 15–22 tracking (±0.03) as the decidable outcome read, or require pooled exposure.
4. **Rewrite null sentence 3.** ×1.10 lies inside r71b's own bootstrap (×0.62–1.17). Either:
   - revert only above the two-drive interval (≈ ×1.6 on r71b's exposure); or
   - state that this cell cannot decide a revert from one drive, and defer to the operator's symptom report, which is primary anyway.
5. **Correct G3 and risk 3.** The minimum local-slope ratio is **0.68 at idx 96–99**, not 0.72. The fork's loop gain in the 5–10 m/s hard-turn region at idx 90–100 is ×0.68–0.73.
6. **Builder requirement.** The V295 build script must assert a **full X + Y tuple census of all 28 records against the spec**, derived independently of the constants it writes. It must include a mutation test that moves one non-live X knot. The non-live records and every X knot are otherwise unverifiable on the wire, and R-PLATEAU does not see X at all. V294's adversary B found exactly this class: a missed non-live knot.
7. **Reporting.** §7's "R-OWN … 0/38" is the null side. The live side is **29/38** windows (76 %; `s10_attr_finalists_out.txt`). R-OWN is not a per-window live test.

## 9. Things I could not verify (said plainly)
- **Soft-EME dwell and FUN_0004595a's exact semantics.** [B] I traced the operands only. The argument rests on the unchanged output range and the V282 precedent.
- **The movhi+movea pair scan into the twin island** had no positive control available. The decision does not depend on it: both copies read the same records.
- **Whether the car is in the light_b world** at highway speed. This is the stability adversary's surface, and it is BELIEF in the design too.
- **All synthetic flights are open loop** on r71b's command. On the car the fork will command differently. The regressions condition on the command, so the attribution reads are unbiased, but exposure per idx bin will shift. [B] More small-idx exposure is likely, because less command is needed per torque.

## 10. Files (all in `analysis-2020accord/studies/v295/design/p-gain/`)
- `ADV-bytes-p-gain-CRITERIA.md`: pre-registered FAIL criteria.
- `advp1_bytes.py` / `out/advp1_bytes_out.txt`: bank, records, aliasing, reader census, twin callers, in-memory edit + CRC.
- `advp1b_twin.py`: adjudication of the twin-island LE32 hits and the movhi 0xD sites.
- `advp2_consumers.py` / `out/advp2_consumers_out.txt`: gp-cell reader and writer census with controls.
- `advp_lane.py`: the adversary's own byte-exact lane from the listing.
- `advp3_arith.py` / `out/advp3_arith_out.txt`, plus `out/advp3b_mono_out.txt`: surface, monotonicity, rail, int32, trim cap, restart pulse, local slope.
- `advp4_wire.py` / `out/advp4_wire_out.txt`: R-PLATEAU, R-SHAPE and knot reads on r71b. `out/_advp4_marches.npz` is a 3.6 MB regenerable cache.
- `advp5_crossroute.py` / `out/advp5_crossroute_out.txt`: baseline stability over six V293 routes.
- `advp6_nullsent.py` / `out/advp6_nullsent_out.txt`: sampling CIs for null sentences 2 and 3.
- `advp7_lineage.py` / `out/advp7_lineage_out.txt`: the Kp bank in all 297 images.
- `advp9_shape.py` / `out/advp9_shape_out.txt`: the TI taper read by exposure; per-bin CIs.
- `_advp8_harness_spot.py` / `out/advp8_harness_spot_out.txt`: harness Lane against my lane on the candidate.
- `_advp_probe_keys.py`: one-off cache key probe.
