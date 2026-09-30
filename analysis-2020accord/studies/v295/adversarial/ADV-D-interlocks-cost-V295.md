# ADV-D on the BUILT V295 image: interlocks, downstream consumers, and the closed-loop cost

Subagent ADV-D (adversary D), 2026-09-30.
- Nothing was flashed, no CAN traffic was sent, no build artifact or fork file was touched, nothing was committed.
- Not edited: STATE, CLAUDE.md, memory, BUILD-LINEAGE, the golden model, the harness.
- The FAIL criteria were written before any V295 number of mine existed: `ADV-D-CRITERIA.md` (12:30 PDT).
- Every script and output is in `advD/`.
- Each claim is marked **[E]** EVIDENCE (method named) or **[B]** BELIEF.
- Symptoms are the operator's to score. Nothing here says a symptom is fixed.

## 0. Verdict: **PASS_WITH_DEFECTS**. No DO_NOT_FLASH criterion fired.

**What I tried to break, and what held:**
- **b has one reader and nothing live downstream of it.** Every value b scales ends either in the lane itself, in an
  unreachable twin, in the forward path, in the 427 tap / 0x14A cave comparators, or in a diagnostic packer. No monitor,
  DTC, governor or lockstep reads any of them with a threshold the edit can newly cross.
- **The lane's reachable output set is unchanged**: rail +2461/−2463, trim cap 616, sub-rail slope 0.6409.
- **The inner loop stays stable on every member, speed and delay.** No inner Ms at delay ×1.5 exceeds 1.5.
- **The outer loop, with the fork law unchanged, gains gain margin on every row** (120 rows × 3 pipes, ×1.048 to
  ×1.66). Ms is never worse (at most ×1.002).
- **Tracking gain and turn-hold stay unchanged** (worst −0.009).
- **The hard-turn band falls on every member under both disturbance models.**
- **No new limit cycle or on-centre line appears.**

**Four statements must go on the page and to the operator before he drives it.** None of them is in the brief's cost list
as written.
- **D-1 Outer-loop phase margin at 5 m/s falls by up to 7.7°** (b_lo; 5.6° nominal) with the relay on, at every pipe
  22–62 ms. GM and Ms improve on the same rows. This is the inertia cost, now in the outer loop.
- **D-2 Delivered 13–17 Hz torque rises up to ×1.59 in the replayed-disturbance sim** (mode B full ×1.56–1.59, mode A
  ×1.52–1.56, over 6 members).
  - This crosses the trim-ratio lens's own pre-registered F5-HF line (×1.5), the clause that lens used to reject b 1134.
  - Under lp (the loop's own motion) the rise is ×0.97–1.08. The increase is the trim reacting to road HF motion.
  - In absolute terms it is small: 0.93 against 0.59 T rms, about 0.04 % of the rail.
  - The decision replaced that clause with "HF controller gain < ×3". Say that it was re-decided.
- **D-3 The soft-EME exposure grows even though its range does not.**
  - On the r71b replay, engaged |trim| > 300 T went from 1 run (42 ms) to 13 runs (longest 308 ms), 7 of them ≥ 75 ms,
    against the 75 ms SM2 residency.
  - All of them are at 0–5 m/s with the driver's hands on. One 49 ms run is at 9.5 m/s. None is at ≥ 10 m/s.
  - V282's flown 427 tap bounds it: |T| ≥ 946 for up to 5.6 s and ≥ 1277 for up to 2.3 s at 0–5 m/s, engaged.
- **D-4 The 20 Hz damping sign.**
  - It is anti-damping at ≥ 4–6 ms after the tap, and already at 2 ms on the prior's flexible modes.
  - Where the model reproduces V282's on-car ζ, the trim removes 0.0019–0.0045 of ζ: 3–6 % of what V282 removed, about 2×
    V294's share.
  - The worst row is 9.7 % within ≤ 9 ms and 11.8 % at 12 ms, both in worlds where V282 itself is unstable in the model.
  - The brief's "~10 %" is the upper end, not the typical value.

## 1. Identity (D0) [E: `advD/d1_identity.py`, hashlib + a whole-file compare]

| check | result |
|---|---|
| V295 image sha256 (re-hashed before and after my work) | `5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed` (1,048,576 B) |
| V294 base | `3143616d…89dbdd85` |
| rwd | `f42a06bd…aeae87` (986,042 B). I did not decode it: that is adversary C's surface |
| whole-file diff vs V294 | exactly 0xC63EA–EB (`37 02` → `1a 04`) and 0xC6FFC–FF |
| b | u16 LE at 0xC63EA = 1050. a = 1011, C = 1024, lag 992/507 |
| CRC trailer | = zlib.crc32([0xC6000, 0xC6FFC)) = 0x8D982BD9 |
| code bytes | code [0x13000, 0xC0000), the caves 0xC4000–0xC5000 and FUN_00028ea6 are byte-identical to V294 |

**Ghidra used the V294 program read-only** (advC's import).
- **Why that is valid:** its code bytes equal the V295 file. At 0x28F84 both read `00d2 e587eb73 …`. The program reads
  `3702` at 0xC63EA where the file has `1a04`, so it is not stale: it is V294, as expected (`d1b_ghidra_sync.txt`).
- **What I did in it:** decompile, `search_instructions`, dry-run disassembly and `read_memory` only. Nothing was saved,
  opened or closed.

## 2. Reader census (D1): the cell and everything its value scales

**Structure, decompiled first** [E: Ghidra `decompile_function 0x28ea6`, saved as
`advD/ghidra_v294_FUN_00028ea6_decompile.c`]:
- The fb filter runs at the top of the lane, **inside the input guard and NOT gated by engagement**:
  - s_new = (a·s_old>>10) + (b·x>>10), stored to gp-0x3d30;
  - r26 = clamp(s_new − s_old, ±C);
  - gp-0x6a34 = |r26>>5|.
- The PID arm runs only when `ramp gp-0x69b0 != 0 || gp-0x6805 == 1` and the guard passed. Otherwise S = 0 into the output
  lag.
- The caller gates the call by a scheduler task mask (`andi 0x930, r25` at 0x22518), not by engagement [E: listing].

**Raw scan** [E: `advD/d2_census.py`]:
- **Method:** my own decoder, sharing no code with the build or the census. It scans every even offset in
  [0x13000, 0x100000). It decodes the 4-byte Format VII forms (with ld.bu's parity and the ld.hu/ld.w `hw2 = disp|1`) and
  the 6-byte Format XIV form. It covers any base, absolute LE32, base materialisation (movea/addi/movhi/mov imm32 plus
  64-byte look-ahead) and ep/sld reach.
- **Positive controls:**
  - gp-0x4f60: **76** accesses, the record's corrected total exactly;
  - the 6-byte gp-0x6752 at **0x48E56**;
  - gp-0x674e: every decompile-visible read.
- **Second method:** Ghidra `search_instructions`.

| cell | readers / writers (raw scan, V295 image) | Ghidra agrees? | adjudication |
|---|---|---|---|
| **b 0xC63EA** (+ RAM alias 0xFA8003EA) | **1**: `ld.hu 0x73ea[tp]` @0x28F86. Alias: 0 hits. Any base: 1 hit @0xBC3BA | 1 = 1 | 0xBC3BA is data (no function; the build agent's halving table) [E] |
| s gp-0x3d30 | ld @0x28F7C, st @0x28FA8 | 2 = 2 | the lane only |
| sentinel gp-0x3d2c | ld @0x28F66, st @0x290D4 | 2 = 2 | the lane only |
| gp-0x6a34 \|r26>>5\| | st @0x290CA; ld @0x2A0CA, @0x2AFAE | 3 = 3 | 0x2A0CA is the damper-mode arm, gated by gp-0x680a == 1. gp-0x680a has **2 readers and 0 writers** (`d2b_all_out.txt`), and boots 0 per the census [B for the boot value]. 0x2AFAE is the dead twin (below). Range 0..32 either way (C unchanged) |
| E_prev gp-0x6cf8 | lane 0x29E5E/0x2A18C; twin 0x2AD4A/0x2B058 | 4 = 4 | D term only. D clamp 0xC61B6 = 0 on V295, so D ≡ 0 |
| P / sum / D / S gp-0x6b32/34/36/2e | lane stores; twin stores; **one read, 0x2A896** | Ghidra misses 0x2A896 | 0x2A896 is in the unreachable twin block |
| yr gp-0x6b30, out-lag gp-0x3d3c | lane plus twin copies (0x2A89A/8BA/8DE/900) | Ghidra misses the twin copies | twin, unreachable |
| **T gp-0x6b38** | writers 0x2A23C (lane), 0x2A934 (twin). Readers: 0x2B418, 0x4E8D2/E2, 0x55DF0, 0xC4B40 | Ghidra misses 0x2A934 and 0x2B418 | see the next list |
| gp-0x6b3c → gp-0x6b3a | lane st @0x2A2EA; FUN_0002b422 ld @0x2B42E, st gp-0x6b3a @0x2B45C; FUN_0002b57a ld @0x2B5B2 | = | the live forward path |

**The readers of T, one by one:**
- **0x55DF0** is the 427 tap.
- **0xC4B40** is the 0x14A cave comparator.
- **0x4E8D2/E2** is FUN_0004e82e, a diagnostic response packer. Decompiled [E], it copies cmd, flags, bar, x and T into a
  0x38-byte buffer and applies no threshold.
- **0x2B418 is DEAD CODE** (below).

**The twin chain 0x2A892–0x2B422 is unreachable** [E: `advD/d3_callers.py`, `d3b_callers.py`]. It is three pieces:
- the output lag plus a T writer using the *stock* gain cell 0x746C;
- FUN_0002a93a, the twin PID;
- the 0x2B070 routine whose tail copies T to gp-0x6b3c at 0x2B418.

The evidence:
- **Control transfers:** a raw scan finds none into any of the three from outside (disp22, disp32, bcond).
  - Its three positive controls are all found: 0x22522→0x28EA6, 0x22530→0x2B422 and 0x22514→0x1CBA6.
  - The only in-range bcond hits (0x2B094/0x2B0B8/0x2B0D2) are mid-instruction in Ghidra's listing.
- **Pointers:** there is no even LE32 pointer into the chain. The one even hit, 0x2B000 at 0x5A368, is an immediate stored
  to a peripheral register (`st.w r8, 0x1044[0xFF6C0000]`), not a call.
- **No fall-through:** each block is preceded by `jmp lp` or `dispose … lp`.
- **Ghidra:** no callers and no xrefs.

> **Correction to the design record:** ADV-bytes-trim-ratio §1 lists 0x2B418 as "the forward copy". It is in the dead
> twin. The live forward copy is the lane's own store at 0x2A2EA (`gp-0x6b3c = T·[gp-0x67a4 ∈ {2,3}]`), read at 0x2B42E.
> This is harmless to the verdict, because T's range is unchanged either way.

**Residual [B]:** a register-indirect call through an arithmetically built address, or a page-level indexed read of the
cal page. This is the kit's standing residual. V294 flew with b changed on the same page.

**D1-F1 did not fire and D1-F2 did not fire. Every null was positive-controlled.**

## 3. Interlocks and reachability (D2)

- **Range [E].** The rail, the cap and the slope are re-derived by the harness `m_safe` from the V295 image cells:
  +2461/−2463, 616, 0.6409. The lane clamp is 3072 and the forward clamp is 3072, and both are unchanged.
- **Forward-lane monitor FUN_0002b57a** [E: decompile]. Plausibility record 0x434E: gp-0x6b3a/1024, clamped to ±3072/1024,
  checked against ±3.0 ± 0.003. gp-0x6b3a is clamped to ±3072 at 0x2B42A–0x2B45C, so the monitor cannot trip. The V295
  peak is 2.40.
- **The >10 Hz reversal detector FUN_000428d4** [E: decompile + bytes].
  - **What it does:** it counts sign reversals of gp-0x6c2c beyond ±[0xC620A] = **12800** within [0xC64DD] = 50 ticks,
    then derates through a LERP (19661/32768 = 0.6 at ≥ 20 counts) and reports event 0x21.
  - **What feeds it:** gp-0x6c2c is written only by FUN_00041464 (0x4184E, 0x41AC2). That function reads gp-0x6b98, the
    shaped total the EME shaper writes (0x43B52, 0x43DFC).
  - **The LKAS lane's contribution** to that total is bounded by ±2463 (rail). Its motion-reactive part is bounded by
    ±616 (cap C). Both bounds are unchanged, and 12800 is 5.2× the rail. **Not newly reachable by range [E].**
  - The HF closed-loop behaviour is §4 [B].
- **Aggregator lockstep** [E: listing 0x3ACE0–0x3AD2A]. gp-0x6b94 and its shadow gp-0x4ce0 are compared (`cmp r15, r13`)
  and then both are stored from the same register. It is a RAM-integrity check and does not depend on the value. The rate
  producer's lockstep, gp-0x6a56 with gp-0x4ca6, is written only in FUN_0003f776 (4 writers, all in 0x3F776–0x3F883), and
  the lane writes neither.
- **DTC / plausibility on the fb operand.** The only checks are the |x| ≤ 12000 bail in the lane and the producer's own.
  No reader of s, r26, gp-0x6a34 or E exists outside the lane and the dead twin (§2) [E].
- **Governor ceilings** see the lane only through T, whose range is unchanged [E range; B for the inherited governor
  structure].
- **0x14A cave and 427 tap** [E]. Their code bytes are identical. The tap field (±511×8 = ±4088) holds the unchanged rail.
  - **But the cave's comparator bits change meaning**, as decompiled at 0xC4B34:
    - b4.6 is `|r24 gp-0x6ada| ≥ |T|`;
    - b4.7 is `sign(gp-0x6b4c)`, i.e. of T at the aggregator.
  - A larger trim moves both duties. **Do not compare b4.6/b4.7 duties across V294 and V295 as if they were b-invariant.**
    This is an instrument note, not a hazard.
- **Soft-EME dwell** [E replay, B consequence: `advD/d4_replay.py`, `d4b_v282_precedent.py`].
  - **Method:** a byte-exact open-loop replay of r71b. Its positive control is that the V294 march equals the cached
    `T1k_live` on 0 of 1,020,390 differing ticks.

  | engaged r71b | V294 | V295 |
  |---|---|---|
  | \|trim\| > 300 T ticks | 42 | **1362** |
  | runs / longest | 1 / 42 ms | **13 / 308 ms** |
  | runs ≥ 75 ms | 0 | **7, all 0–5 m/s** |
  | at 5–10 m/s | 0 | 1 run of 49 ms (9.5 m/s) |
  | at ≥ 10 m/s | 0 | **0** |
  | lane total \|T\| max | 1467 | 1277 (lower) |
  | \|bar\| in the long runs | – | 580–1310 (hands on) |
  | fb clamp C binding | 0 % | 0.0084 % |
  | P clamp binding | 0.058 % | 0.052 % |

  - **The flown bound, V282's 427 tap on 7 routes** (r36 r37 r38 r39 r3a r3c r6c, engaged, 0–5 m/s):
    - |T| ≥ 946: 266 runs, longest **5640 ms**, 110 of them ≥ 75 ms;
    - |T| ≥ 1277: 104 runs, longest **2280 ms**;
    - most of these are with |bar| ≥ 400.
  - **The same statistic on the V295 replay:** ≥ 946, 9 runs, longest 1472 ms; ≥ 1277, 1 run of 1 ms.
  - **So V295's lane stays well inside the flown V282 envelope** [E for the tap envelope].
  - Base assist is not modelled. The trim is co-signed with bar on 71 % of hands-on ticks where it matters (V294: 82 %), so
    it adds to base assist rather than opposing it [B: the sign chain]. D2-F2 did not fire. **Disclose it (D-3).**
- **Restart pulse reachability** [E: decompile + `advD/d9_bail_reach.py`].
  - **The fb state is zeroed only by the sentinel after a guard failure.** The guard fails on:
    - |gp-0x4f60| > 25600 raw (26214 wire);
    - gp-0x6752 ∉ {±1};
    - |x| > 12000.
  - **Engagement does not restart the filter,** because it runs whether engaged or not (§2). So there is no engage-time
    pulse.
  - **Over 29 cached routes (7.9 h) no bail condition was reached:**
    - max |0x18F rate| 5942 counts = 743 deg/s, **50 %** of the bail;
    - max |bar| 9105 wire, **35 %**;
    - on r71b alone, 25 % and 14 %.
  - **The pulse size** (harness, zero command): 268 T at 100 deg/s (V294: 144) and 554 at 300 deg/s (V294: 419), bounded by
    616. The build's envelope maximum is 287 T.
  - **Reachable only on a sensor fault or an extreme manoeuvre.** D2-F5 did not fire.
- **Driver override** [E lane arithmetic, B scenario: `advD/d5_override.py`].
  - **Method:** golden-exact Lanes (harness Lane = the golden model), with the wheel held to a prescribed swerve. The
    "trim" here is T minus T with the fb operand muted.
  - **Peak motion-reacting lane torque:**
    - V295 **30–611 T** against V294 17–590. The ratio is ×1.03 in the cap-bound 90°/0.3 s swerve and ×1.85 in the slow
      and evasive cases.
    - The impulse is ×1.3–1.86.
  - **V282, flown, gives 769–2480 T in the same manoeuvres, 4.0–26× V295 row for row.** The flown precedent bounds it, so
    D2-F6 did not fire. Heavy hands (bar 3600) cut all three by the taper: V295 30–185 T.

## 4. Closed-loop cost (D3). Harness `score()` of the V295 cells read from the image, with V294 in the same batch

Sources:
- `advD/d6_score.py` / `d6_score_out.txt` / `.json`, with runtime 99 s and hash `1f645218…`;
- `d6b_compare_out.txt`, which pairs V294's own M_LOOP and outer margins on the same members;
- `d6e_pipe_out.txt`, the 42 and 62 ms pipes;
- `d7_*` (stress modes), `d8_*` (low speed and on-centre).

**Trust:** the lane and the fork are [E]; plant-driven magnitudes are [B], and "full" is biased toward "no change"
(harness §0).

| quantity | V294 | **V295** | criterion |
|---|---|---|---|
| inner stability, 60 rows (6 default + 6 stress members × 5 speeds) | all stable | **all stable**; no row unstable on V295 only | D3-F1 PASS |
| inner Ms max / at delay ×1.5 | 1.136 / 1.135 | **1.240** (light_b 8 m/s) / **1.250** (tau9 3.1 m/s) | < 1.5, PASS |
| inner GM min | 16.3 | **8.78** (tau9 3.1 m/s). GM halves everywhere (linear dose) | – |
| wider set (light_b + a 20 Hz flexible mode, `lb_mode20_lo`), Ms at ×1 / ×1.5 / ×3 delay | 1.17 / 1.19 / 1.25 | **1.34 / 1.39 / 1.57**. GM 7.2 / 5.4 / 3.15 | ×3 exceeds 1.5 (outside my ×1.5 clause); disclosed |
| outer GM, r1 law, 6 members × 5 speeds × relay × pipes 22/42/62 | – | **×1.048 … ×1.66 on every row** | PASS |
| outer Ms | – | **≤ ×1.002 on every row** | PASS |
| outer PM, identified family | – | **−7.7° worst** (b_lo, 5 m/s, relay on, 97.9 → 90.2); nominal −5.6°; J_hi −3.9° | **5–10°: DEFECT D-1** |
| outer PM, light_b, 17 m/s, relay off | 134.2° | 98°, a *new* crossover pair at 0.71/0.93 Hz where \|L\| touches 1.03; Ms 1.54 → **1.39** | an artefact of the crossover count, not a margin loss [E `d6c_pm_out.txt`] |
| light_b 26.9 m/s, relay on, pipe 22 / 62 ms | GM 1.70, Ms 3.07 / GM **1.00**, Ms 261 | GM **2.67**, Ms 1.96 / GM **1.41**, Ms 4.43 | better |
| tracking gain Δ (all bands, members, dists) | – | −0.001 … +0.004 | PASS |
| turn-hold Δ | – | −0.009 … +0.012 | PASS (< 0.01) |
| straight delivery Δ | – | −0.009 … +0.015 | – |
| **0.5–1 Hz lateral-accel error**, 0–5 m/s (lp / full) | – | identified ×1.04–1.10 / ×1.01–1.05; **light_b ×1.23 / ×1.16** | ≤ ×1.4, PASS (inside the stated cost) |
| same, 5–10 m/s | – | identified ×1.03–1.06 / ×0.98–1.03; light_b ×1.16 / ×1.13 | PASS |
| J-style error 0.15–2.4 Hz, 0–5 m/s, lp | – | nominal ×1.05, b_lo ×1.08, light_b ×1.15 | – |
| **hard-turn 1.6–3 Hz, 5–10 m/s** (full / lp) | – | identified ×0.80–0.88 / ×0.77–0.89; **light_b ×0.72 / ×0.70** | falls, PASS |
| hard-turn 1.6–3 Hz, 15–22 m/s (full / lp) | – | identified ×0.90–0.94 / ×0.91–0.98; light_b ×0.69 / ×0.73 | falls |
| 1–5 Hz limit-cycle line, lp | −4.7 dB (nominal), +0.8 dB (light_b) | −5.5 / −0.9 dB. Prominence falls on all 6 members | D3-F6 PASS |
| same line, full, light_b | 1.27 Hz, +2.9 dB, rms 3.51 | 1.07 Hz, −2.2 dB, **rms 3.85** (+0.8 dB) as the line moves down | inertia shift, not a new cycle |
| on-centre (\|plan\| < 0.4, \|angle\| < 10°): wheel rate 1–5 Hz | – | ×0.79–0.99 everywhere | better |
| on-centre wheel rate 0.2–1 Hz | – | ×0.97–1.17, except light_b full at 0–5 m/s **×1.50** (25 s of data) | no new line: the PSD peak stays at 0.2 Hz (`d8b`, one 13 s chunk) [B] |
| low-frequency closed-loop modes (`d7c_modes_out.txt`) | light_b wheel mode 0.48–1.23 Hz, ζ 0.45–0.55 | 0.42–1.02 Hz, **ζ 0.42–0.48**. b_lo 0.64 Hz ζ 0.70 → 0.63. Lane-vs-J pair (nominal, b_lo, light_b, tau9) 3.3–4.5 → 4.6–5.9 Hz, ζ falls 0.06–0.12 (lowest 0.59, light_b 26.9) | the inertia cost [E model] |
| \|P/x\| at 20 Hz / \|T/x\| 5–30 Hz | 2.079 | **3.850** (×1.852, 8.6 % of V282's 44.90) / ×1.85 flat | < ×3, PASS |
| sim delivered torque 5–30 Hz, mode B **full** | – | 5–9 ×1.43–1.47, 9–13 ×1.40–1.45, **13–17 ×1.52–1.59**, 17–23 ×1.16–1.19, 23–30 ×1.20–1.28 | **> ×1.5: DEFECT D-2** |
| same, mode B **lp** | – | ×0.97–1.08 in every band on 6 members, stress members included (`d6d`) | – |
| staircase HF (command at the slew cap, x = 0) | 21.3 / 7.5 / 2.7 / 1.5 / 0.8 | identical | FF unchanged [E] |

**20 Hz stress modes against delay** [E model, B car: `d7_stress_out.txt`, `d7b_calibrated_rows.txt`]. Setup:
- dζ = ζ_lane − ζ_open;
- exact 1 kHz closed loop;
- V282 with its sum operand, shl 5, Kd 128. V282's r24 lane (5244) is not modelled.

At 2 ms (the harness setting) the trim **adds** damping on all 9 harness stress cells (+0.0016 … +0.023).

| delay / case | V294 dζ | **V295 dζ** | V282 dζ | V295 / V282 |
|---|---|---|---|---|
| mode20, 5 m/s, 6 ms (V282 → ζ 0.010 ≈ on-car 0.016) | −0.0010 | **−0.0021** | −0.065 | **3.2 %** |
| mode20, 12 m/s, 9 / 12 ms (V282 → 0.029 / 0.022) | −0.0009 / −0.0023 | **−0.0020 / −0.0045** | −0.069 / −0.075 | **2.9 % / 6.0 %** |
| prior flexible mode (lb_mode20), 4 ms (V282 → 0.005) | −0.0010 | **−0.0019** | −0.052 | **3.7 %** |
| worst at ≤ 9 ms (lb_mode20_lo, 9 ms; V282 **unstable** in the model) | −0.0108 | **−0.0200** (ζ 0.050 → 0.030) | – | 9.7 % |
| worst at 12 ms (mode20_lo, 5 m/s; V282 unstable) | −0.0150 | −0.0275 | – | 11.8 % |
| modes at 25 m/s, and mode13 / mode20_lo at 12 m/s | + | **+ (damps at every delay)** | – | – |

- V295 removes damping in 46 of 90 rows. No stress ζ falls below 0.05 where V294's was ≥ 0.05, and nothing is unstable on
  V295 only.
- **D3-F7 did not fire** (< 20 %; ≤ 9.7 % within the 2/6/9 ms clause).
- **The page must say "anti-damping above ~4 ms, about twice V294's, 3–6 % of V282's where calibrated" (D-4).**

## 5. The three complaints (his words), predicted

1. **"Jerky on hard turns at medium speed": predicted BETTER, modestly** [B: sim counterfactual; E: the lane arithmetic].
   - The hard-turn 1.6–3 Hz wheel rate at 5–10 m/s is ×0.77–0.89 on the identified family and ×0.70–0.72 on the prior,
     under both models. At 15–22 m/s it is ×0.90–0.98 and ×0.69–0.73.
   - The 1–3 Hz wheel rate is ×0.81–0.99 on the identified family and ×0.69–0.85 on the prior.
   - The mechanism sits at the trim's 2.03 Hz pole, where the recorded jerk mode is (2–2.7 Hz, V293 r75 read).
   - Caveat, already in the record: one short drive cannot separate ×0.87 from ×1.0 on the band (no-change scatter
     ×0.73–1.29 at 15 s). Only his report decides this.
2. **"Loose on straights and turns at low speed": predicted UNCHANGED to slightly WORSE** [B].
   - Tracking gain Δ ≤ +0.004 and straight delivery ±0.009: the static surface is byte-identical [E].
   - The 0.5–1 Hz lateral error at 0–5 m/s is ×1.01–1.10 on the identified family and ×1.16–1.23 on the prior.
   - On-centre 0.2–1 Hz wheel wander at parking speed is up to ×1.5 on the prior (full; ×1.07 lp).
   - The outer PM at 5 m/s falls by up to 7.7°, and the low wheel mode loses ζ (0.45 → 0.42 on the prior).
   - If he reports low speed looser, that is this predicted cost, not a surprise.
3. **"Loose / understeer at highway turns": predicted UNCHANGED** [E for the static surface; B for the sim].
   - Tracking gain Δ ≤ +0.003 and turn-hold Δ −0.007 … +0.012 at 15–22 and 22+ m/s, on every member.
   - The outer loop at highway speed gains margin, most on the prior: GM 1.70 → 2.67.
   - The lever does not reach this complaint. **D4-F1 did not fire.**

## 6. Pre-registered criteria: what fired

| criterion | result |
|---|---|
| D0-F1, D0-F2 identity / unchanged sources | no [E] |
| D1-F1 second reader of b | no. 1 reader; controls found [E] |
| D1-F2 live consumer of a b-scaled cell with a reachable threshold | no. Twins unreachable; T consumers carry no threshold, or it is unreachable [E] |
| D1-D1 uncontrolled null | none |
| D2-F1 range | no [E] |
| D2-F2 soft-EME | no (0 runs ≥ 75 ms at ≥ 10 m/s). **Disclosed: D-3** |
| D2-F3 detector / monitor / governor / lockstep newly reachable | no [E range] |
| D2-F4 DTC on the fb operand | no [E] |
| D2-F5 restart pulse routine | no. Bail-only; 0 bails in 7.9 h [E on the data, B beyond] |
| D2-F6 override beyond V282 | no. V282 is 4.0–26× larger, row for row |
| D3-F1 inner | no |
| D3-F2 outer | **PM 5–10° → DEFECT D-1**. GM and Ms never worse |
| D3-F3 tracking / hold | no |
| D3-F4 low-speed error | no (≤ ×1.23) |
| D3-F5 hard turns | no |
| D3-F6 limit cycle / hunting | no |
| D3-F7 20 Hz | no (≤ 9.7 %). **Wording: D-4** |
| D3-F8 HF | \|P/x\| no. **Sim HF > ×1.5 → DEFECT D-2** |
| D4-F1 highway claim | no |

## 7. Limits

- Nothing above ~8 Hz is identified. Every HF and stress statement is a stress-member model with one on-car calibration
  number, and V282's r24 lane is not modelled.
- The soft-EME consequence needs base assist, which is not modelled. The bound is the flown V282 envelope [B].
- The r71b replay is open loop (V294's recorded wheel motion).
- The harness's `full` counterfactuals are biased toward "no change". The low-speed on-centre ×1.50 rests on 25 s.
- I did not re-derive the build's arithmetic or units, the rwd or CRC walk, or the wire-read regression. Those are the
  other adversaries' surfaces.
