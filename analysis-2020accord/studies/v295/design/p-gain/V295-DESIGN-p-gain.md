# V295 design, lens "p-gain": the P gain itself as the tuning value

Subagent `p-gain`, 2026-09-30. **Design only.**
- Nothing was built, flashed or sent. No CAN traffic, no image, no `.rwd`.
- The fork was not touched. STATE, memory, lineage, golden model and CLAUDE.md were not edited. Nothing was committed.
- Every decision-bearing claim is marked **[E]** EVIDENCE (with the method) or **[B]** BELIEF.
- The operator scores symptoms; everything below is a band, a transfer function or a simulation.
- Pre-registered gates, written at 10:36 before any candidate number existed: `CRITERIA-p-gain.md`.
- Scripts and outputs are beside this file: `s0`–`s16`, `pg_lib.py`, `out/`.

---

## 0. Bottom line

**Recommendation: a REGRESSIVE Kp schedule, `R1.3_8_100`. It is cal-only and touches only the Kp bank `0xCB994`, rewritten identically in all 28 records.**

| | X (demand index) | Y (Kp) |
|---|---|---|
| V294 (live slot 7) | 0, 68, 112, 136, 208 | 960, 960, 960, 960, 960 |
| **R1.3_8_100** | **0, 8, 54, 100, 208** | **1248, 1248, 1104, 960, 960** |

In words: Kp is ×1.30 up to idx 8 (|0xE4| ≤ 129 counts). It then falls linearly, in Kp, back to exactly V294's 960 at idx 100 (1613 counts), and stays at V294 from there to the rail.

**Why a schedule and not a flat multiple.**
- Kp does three jobs at once: `P = ((sp<<2) − r26)·Kp >> 8`. It sets:
  - the **static torque per command**, `Kp(idx)/960`, which closes the hold;
  - the **acceleration-feedback (trim) gain**, `Kp(idx)/960`;
  - the fork's **small-signal loop gain**, i.e. the local slope `d(map·Kp)/d idx`.
- A **flat** multiple raises all three by the same g.
- A **non-increasing** Kp raises the first two by `Kp/960` but raises the third by *less* (local slope = `Kp + idx·Kp′ < Kp`).
- That is the only asymmetry the P gain offers. The harness says it is the right one, in both plant worlds [E, model]:
  - It raises the delivered hold where the fork under-delivers (idx 0–55).
  - It holds, or lowers, the fork's loop gain where the hard-turn 1.6–3 Hz motion and the light_b outer-loop resonance live.

**What it does**, in the shared `score()`: same batch as V294, six plants, both disturbance models, differences only (`out/s13_compare_out.txt`).

| complaint (operator's words) | instrument | V294 → R1.3_8_100 | tag |
|---|---|---|---|
| "Loose/understeer at highway turns" | 22+ m/s tracking gain | +0.052 … +0.059 (drive 0.924 → ≈ 0.98) | [E model, FIT band]; [B] car |
| | 22+ m/s turn-hold | +0.055 … +0.066 (drive 0.943 → ≈ 1.00) | same |
| | 15–22 m/s tracking | +0.053 … +0.069 | 15–22 is **DIRECTIONAL** in the harness |
| | 15–22 m/s turn-hold | +0.071 … +0.109 (drive 0.673 → ≈ 0.75–0.78) | same |
| "Loose on straights and turns at low speed" | straight delivery, 0–10 m/s | +0.06 … +0.10 | [E model] |
| | 5–10 m/s tracking / hold | +0.026 … +0.032 / +0.020 … +0.050 | [E model] |
| | **0–5 m/s turns** | **+0.000 … +0.008: NOT REACHED** | [E model] |
| "Jerky on hard turns at medium speed" | hard-turn 1.6–3 Hz wheel rate, 5–10 m/s | ×0.80–0.90 (lp) / ×0.91–0.96 (full) | [B] for the car, below |
| | same, 15–22 m/s | ×0.99–1.12 (lp) / ×0.99 (full) | [B] |
| goal (cmd vs d²θ/dt²) | small/large amplitude \|α/cmd\| (friction deficit) | 0.35 → 0.50 (nominal, b_lo); 0.05 → 0.16 (F_hi) | [E model] |
| | mode-A literal R², 0.3–1 Hz | 0.20 → 0.29 (nominal); 0.15 → 0.28 (light_b) | [E model] |
| | mode-A literal R², 1–3 / 3–8 Hz | unchanged (0.32 → 0.33; 0.18 → 0.18) | [E model] |

On the hard-turn rows: the harness says 1–8 Hz wheel motion is NOT FIT from the plant alone. So read these as a *direction that holds across all six plants and both disturbance models*, not as a magnitude.

**Costs, stated before the drive:**
- **Outer loop on the light_b prior at 22+ m/s:** Ms 3.00 → 3.18 (holds, idx 18) and 3.04 → 3.43 (straights, idx 6). GM 1.71 → 1.60–1.66 [E model / B world].
- On the identified members, Ms ≤ 1.41 and GM ≥ 7.4 everywhere, including 3 m/s.
- **Plant-alone (lp) 1–3 Hz wheel motion:** +9–30 % at 0–5, 10–15, 15–22 and 22+ m/s (straights and holds carry the ×1.2–1.3 local slope).
  - Under `full` it is +0–9 %.
  - In absolute terms it is small: lp nominal 0.17–1.14 deg/s against the drive's 1.06–8.83 deg/s.
- **Delivered torque 5–30 Hz in the sim:** +14–24 %, at 0.6–2 T rms.
- **Zero-command trim cap:** 616 → 801 T (32.5 % of the rail).
- **Restart pulse:** ×1.3.
- **Unchanged:** the rail (2461 / −2463), the idx at which the rail is reached (239), the lane clamp, int32 margins, b/b_max, and every other cell.

**Wire read — one short drive, existing instruments:**
- Regress the 427 tap on V294's byte-exact FF+trim march, on idx 0–8 frames. Divide by V294's own r71b baseline.
- R1.3_8_100 reads **1.32 [1.29, 1.36]** in every 20 s window (33 of 33). V294 on the car reads **1.00 [0.98, 1.04]**. The two are disjoint [E: positive control built from r71b's own tap residual, plus the real-tap null].

**The null sentence:**
> If the plateau read is inside V294's band (1.00 ± 0.05), the new Kp records are not live, and nothing about the drive is attributed to them.
>
> If the plateau read is 1.30 ± 0.05 but the 8–22 m/s turn-hold does not rise above 0.72 (V294 0.67–0.69), then at this dose the under-delivery is not a firmware-slope problem. The remaining lever is the fork's integrator/LAF, which is out of this session's scope.

**The lens's FAIL sentence (CRITERIA-p-gain.md) does NOT fire.** R1.3_8_100 passes G1–G8 and wins ≥ +0.05 in three bands ≥ 8 m/s on both nominal and light_b.

**The flat family FAILS as pre-registered at g ≥ 1.3:** G6, hard-turn 1.6–3 Hz under `full` on light_b at 15–22 m/s is +12 %. g = 1.2 sits on the G6 line (+10 %).

**What the P gain cannot do (§9):**
- It cannot make α track the command below ~1 Hz. There the command holds an angle against the spring, which is the fork's torque semantics.
- It cannot give the speed-dependent gain the under-delivery needs: ×1.06 at 22+ against ×1.5–2 at 10–22 m/s. Kp has no speed axis.
- It cannot absorb road-to-road hold variation (20–70 %, r72/r73). That needs integral action.
- It reaches only the loop-generated part of the hard-turn jerk.
- It closes roughly **a quarter to a third** of the 15–22 m/s hold gap and **most** of the 22+ gap.

---

## 1. Pre-registered gates and what fired (`CRITERIA-p-gain.md`)

| gate | R1.3_8_100 | flat g1.3 | map ×1.3 |
|---|---|---|---|
| G1 rail 2461/−2463, lane clamp untouched | PASS (rail first at idx 239, same as V294) | PASS (P clamp from idx 184) | PASS |
| G2 int32 ≥ 2, b ≤ b_max, no static problem | PASS (min 4.06 at a·s, unchanged) | PASS | PASS |
| G3 monotone surface | PASS (min local-slope ratio 0.72, idx 2–150) | PASS | PASS |
| G4 \|P/x\|@20 Hz ≤ 6.24; stress ζ ≥ 0.9·V294's; all stable incl. delay ×1.5 | PASS (2.703; ζ ≥ V294's at all nine; Ms(×1.5 delay) ≤ 1.17) | PASS (2.703) | PASS (2.079) |
| G5 outer: identified Ms ≤ 1.6, GM ≥ 3; light_b GM ≥ 1.5, Ms ≤ max(1.25·V294's, 2) | PASS (light_b GM ≥ 1.60, Ms ≤ 3.43 against a 3.80 cap) | PASS (3.54, GM 1.57) | **FAIL** (Ms 5.49–5.77 at 22+, GM 1.29–1.31) |
| G6 no divergence; lc ≤ +3 dB; hard16 (full) ≤ ×1.10 at 5–10 / 15–22 | PASS (lc ≤ +0.33 dB; hard16 full 0.91–0.99) | **FAIL** (light_b 15–22 ×1.12) | **FAIL** (hard16 full light_b ×1.17 at 5–10 and ×1.29 at 15–22; lc +2.4 dB) |
| G7 wire-readable | PASS (§7) | PASS | PASS (FF identity) |
| G8 trim cap ≤ 924 T or argued | PASS (801) | PASS (800) | PASS (616) |
| win: ≥ +0.05 tracking/hold in a band ≥ 8 m/s, nominal **and** light_b | YES: 10–15, 15–22 [DIR], 22+ | YES | YES |

**Defects in my own process, reported rather than hidden:**
1. The first regressive grid (`s7`, rev 1) rejected every flat multiple for a "flat spot". That spot was the P-clamp top above idx 184, which is 0.3 % of r71b's engaged frames. Rev 2 (`s7b`) restricts the slope check to idx 2–150. The rev-1 table is kept in `out/s7_regress_grid_out.txt`.
2. The first run of rev 2 crashed on a name collision (`%.1f` rounding 1.25 → "1.2"). It was fixed and re-run.

---

## 2. Harness spot-check (`s0_spotcheck.py`, `out/s0_spotcheck_out.txt`) [E]

- **Lane equals the golden model tick for tick** on T, E, P, S and y, over 8,000 ticks each, on this lens's knobs:
  - V294;
  - flat Kp ×1.5;
  - a Kp schedule with moved X knots **and falling Y segments**;
  - a reshaped map.

  All four had 0 mismatches.
- **The surface T(idx)** from the golden `lkas_rate_pid_surface` equals my own integer march at 13 idx for all four sets.
- **For the recommendation, a third method** (`s16`): a listing-style re-implementation of the Kp LERP (`sub`, `mul`, **signed `divq`**, `add`, `zxh`) against the golden `lkas_rate_lerp` gives 0/241 mismatches. The hand-marched surface against the golden surface gives 0/241 mismatches.
- **One retrodiction row, V294 under lp on the nominal member:**

  | band | tracking gain | turn-hold | harness report |
  |---|---|---|---|
  | 0–5 | 0.840 | – | 0.840 |
  | 5–10 | 0.865 | 0.780 | .865 / .78 |
  | 10–15 | 0.586 | 0.592 | .586 / .592 |
  | 15–22 | 0.764 | 0.636 | .764 / .636 |
  | 22+ | 0.917 | 0.939 | .917 / .94 |

  This matches the harness report to the third decimal.

---

## 3. What Kp does on V294, in the firmware's own arithmetic

### 3.1 The Kp LERP [E]

Method: decompile of FUN_00028ea6 on `code.bin` first, then the listing 0x29DC6–0x29E36 (`dry_run`). The code region is byte-identical to V294 here (census c1).

```python
# per 1 ms tick, the Kp read (bank 0xCB994, 28 LE32 record pointers, live selector 7 -> record 0xE5378)
rec = u32(0xCB994 + 4*7)                  # 0x29DC6 mov 0xcb994,r10 ; 0x29DCE add ; 0x29DD6 ld.w
X = [u16(rec+2+2*k) for k in range(5)]    # count word at rec+0 is NOT read by the LERP
Y = [u16(rec+12+2*k) for k in range(5)]
if not X[0] < idx:   kp = Y[0]            # 0x29DEA cmp r9,r7 ; bh
elif not idx < X[4]: kp = Y[4]            # 0x29DF6 cmp ; bnc -> ld.hu 0x8(r10)
else:
    k = 1
    while X[k] <= idx: k += 1             # 0x29E0A..0x29E12 walk (X strictly increasing -> den > 0)
    num = (Y[k]-Y[k-1]) * (idx-X[k-1])    # 0x29E20 sub ; 0x29E24 sub ; 0x29E26 mul (32-bit low word)
    q = trunc(num / (X[k]-X[k-1]))        # 0x29E2C divq r6,r9  -- SIGNED (hw2 sub-opcode 0x2FC), truncates toward 0
    kp = (Y[k-1] + q) & 0xFFFF            # 0x29E30 add ; 0x29E32 zxh
P = clamp(((sp << 2) - r26) * kp >> 8, +-15360)   # 0x29E36 mul ; 0x29E3E sar 8 ; P clamp 0xC61BC
```

- **Falling Kp segments are arithmetically exact on this hardware** [E]:
  - The difference and the product are 32-bit two's-complement.
  - The divide is `divq` (signed), and Ghidra's decompile renders it `(int)/(int)`.
  - The golden model's `lkas_rate_lerp` (trunc toward zero) matches it on all 241 idx (`s16`).
- **Why this was checked:** every flown Kp record so far was flat or rising. V284's shelved record had one falling segment and never flew.

### 3.2 The three roles, at one operating point idx, with the wheel still and no driver [E, golden-model march]

- **static torque** `T(idx) ∝ map(idx)·Kp(idx)`: ratio to V294 = `Kp(idx)/960`.
- **trim** `−(Kp(idx)/256)·r26`: K_α = 0.210·Kp/960 T per deg/s² below the 2 Hz pole. Trim cap = C·Kp/256 through the chain.
- **local slope** `dT/dwire ∝ d(map·Kp)/d idx = map′·Kp + map·Kp′`. This is what the fork's loop sees.

For a flat Kp all three move together. For a falling Kp the local slope is below the static and trim ratios. See `out/fig3_ratios.png` and `out/s14_rec_table_out.txt`:

| idx (\|0xE4\|) | where r71b sat there (s2) | T V294 → rec | static ratio | local slope T/wire | ratio | Kp | K_α | trim cap T |
|---|---|---|---|---|---|---|---|---|
| 3 (48) | straights; the fork relay | 30 → 40 | 1.33 | 0.631 → 0.817 | 1.29 | 1248 | 0.273 | 800 |
| 6 (97) | straights ≥ 10 m/s | 61 → 80 | 1.31 | 0.633 → 0.815 | 1.29 | 1248 | 0.273 | 800 |
| 18 (290) | holds 22+ | 184 → 233 | 1.27 | 0.636 → 0.764 | 1.20 | 1217 | 0.266 | 780 |
| 34 (548) | holds 10–22 | 350 → 426 | 1.22 | 0.643 → 0.709 | 1.10 | 1167 | 0.255 | 748 |
| 50 (806) | holds 5–10; hard turns 15–22 | 516 → 600 | 1.16 | 0.643 → 0.647 | 1.01 | 1117 | 0.244 | 716 |
| 75 (1209) | hard turns 5–10 | 773 → 837 | 1.08 | 0.643 → 0.539 | 0.84 | 1039 | 0.227 | 666 |
| 92 (1484) | – | 949 → 974 | 1.03 | 0.643 → 0.465 | 0.72 | 986 | 0.216 | 632 |
| ≥ 100 (≥ 1613) | low-speed hard turns, rail | = V294 | 1.00 | = | 1.00 | 960 | 0.210 | 616 |

- The largest static increase is **+85 T at idx 51**.
- The rail is identical: 2461, first reached at idx 239.
- The fork's friction relay (45 counts → idx 3) grows from 30 T to 40 T.
- The fork's P, I and relay all act on the local slope at their operating point: ×1.3 on straights, ×1.2 on highway holds, ×1.0–1.1 on mid-speed holds, and ×0.7–0.9 in the 5–10 m/s hard turns.
- Because the fork is not retuned, this *is* its plant-gain change.

### 3.3 The Kp records on V294 [E, `s9_kp_records.py`]

- The 28 records are distinct: 24-byte stride, five 4 KB pages 0xE4000–0xE8000.
- Every Y is 960.
- **The X knots differ by record:**

  | slots | X |
  |---|---|
  | 0, 1, 3, 4, 6, 7 | [0, 68, 112, 136, 208] |
  | 2, 5 | [0, 48, 128, 160, 208] |
  | 8, 9 | [0, 64, 112, 136, 208] |
  | 10–27 | [0, 48, 112, 160, 208] |

- A flat Y made X irrelevant. Any schedule must rewrite **X and Y in all 28 records** to stay selector-invariant, as V293/V294 did for Y. That is **252 payload bytes over 5 pages** (`out/V295_p-gain_candidate_spec.json`, which gives the byte blocks per record).
- The census table's "X = [0,68,112,136,208]" is right for the live slot only. That is a report, not a defect in its conclusions.

---

## 4. Family (i): a flat Kp multiple g (`s1_flat_sweep.py`, `s7b`)

- **g raises tracking in every band on every member, monotonically.** EVIDENCE for the model, under lp and full, on nominal / light_b / b_lo / F_hi / J_hi.
- g1.3 gives tracking +0.05…+0.14 and turn-hold +0.05…+0.18 in every band. At 22+ it lands ≈ 1.00 (hold 1.01–1.04 at g1.5, the first sign of over-delivery).
- **The costs grow with g in the loop's own motion (lp):**

  | metric | g1.3 |
  |---|---|
  | 1–3 Hz wheel rate | +12 % to +58 % |
  | hard-turn 1.6–3 Hz | +17 % to +54 % |
  | lc on light_b | +1.0 dB |
  | light_b 22+ outer Ms | 3.00 → 3.49–3.54 |

- **Why the outer-loop cost is smaller than g** [E model, two methods]:
  - Kp's trim share is the reason: at 2–3 Hz on light_b the inner trim loop has |L| ≈ 0.8–1.4, so `P·g/(1+g·L0)` partly cancels g.
  - The diagnostic split in `s1` shows it:

    | variant | light_b 26.9 m/s Ms | GM |
    |---|---|---|
    | FF-only (Kp ×1.5 with b/1.5) | **11.5** | 1.13 |
    | trim-only (b ×1.5) | **2.21** | 2.25 |
    | flat g1.5 | 3.86 | 1.50 |

  - The closed-loop sim agrees: under full / light_b, lc is +7.3 dB FF-only against +3.4 dB for g1.5, and 5–10 m/s hard16 is 19.4 against 15.1 deg/s.
- **Best flat multiple:** g1.2 (Kp 1152) wins the pre-registered +0.05 in 10–15 and 15–22 [DIR], but sits on the G6 line (hard16 full light_b 15–22 ×1.10), with lc up to +0.67 dB. g1.1 does not reach +0.05 anywhere.
- **The flat family is dominated by the regressive schedules** (§5) at equal benefit ≥ 10 m/s.

## 5. Family (iii): the demand map's shape as the alternative place (`s3`, `s4`, `s5`)

**The map changes the FF only; the trim is untouched.**

| map variant | shape | outer loop, light_b | on-centre sim |
|---|---|---|---|
| **M-x1.3** | the same static gain as flat Kp ×1.3 | Ms **5.49–5.77** at 22+ against 3.49–3.54 for Kp ×1.3; GM 1.29–1.31 (**FAILS G5**) | – |
| **M-regress** | a small-idx boost, ×1.6 to idx 12, then the V294 slope | Ms 3.12 at 17 m/s straights (**12.0 at 22+ straights**) | **107–116 stick-slip breakaways/min** at 27 m/s (nominal, b_lo) against V294's 9, plus a +10 dB 3.4 Hz line on b_lo. This is the hunting signature. [E model; the magnitude is B] |

**Conclusion [E, model; two methods: linear margins + closed-loop sim]:** for a given static nonlinearity, the Kp bank is the better place than the map. The Kp bank brings its own acceleration feedback along; the map adds FF-only gain, and FF-only gain is what the light_b outer loop and the friction on-centre punish.

- **Fork friction interaction.** A step-like small-command boost is a relay in the loop, the route-73 class. There, SteerFriction 0.212 gave a 10×-Kp relay → 3.8–4.7 Hz chatter (memory, V293 rev 3).
- **Map on-car record:**
  - `0xC9A88` is linear ×6 since V282, flown on V282/V293/V294.
  - Its shape has never been changed in torque mode.
  - Nothing is recommended for it.

## 6. Family (ii): Kp(idx) schedules (`s3`, `s4`, `s7`, `s7b`, `s8`, `s12`, `s13`)

- **Rising or bumped schedules** (K-mid, K-1.3taper) have `Kp′ > 0` somewhere, so their local slope exceeds their trim ratio there. They behave like flat g or worse at those idx: K-mid light_b 22+ Ms 3.67 (`s4`).
- **Regressive schedules:** the grid (`s7b`) swept the plateau height k0 (1.25–1.45), the plateau end (idx 4, 8, 12) and the taper end (idx 100–180). What decides the result:

  | knob | effect |
  |---|---|
  | **taper end ≈ idx 100** | keeps hard16 under full ≤ 1.00, drops lc by 1.3–2.2 dB (lp light_b) and lowers 5–10 m/s hard-turn motion |
  | a later taper end (140–180) | buys the 0–5 m/s turns (+0.01–0.05) but gives back the hard-turn benefit (lp hard16 ×1.17–1.42) |
  | a higher plateau | +benefit and +cost roughly in proportion |

- **Four finalists through the SHARED `score()`** (`out/s8_score_*.txt/json`, compared in `out/s13_compare_out.txt`):

  | finalist | tracking ≥10 m/s (min over 6 plants, lp) | hard16 5–10 lp / full | hard16 15–22 lp / full | lc lp (max) | light_b 22+ Ms (hold / straight) | trim cap |
  |---|---|---|---|---|---|---|
  | **R1.3_8_100** | +0.052 … +0.097 | 0.80–0.90 / 0.91–0.96 | 0.99–1.12 / 0.99 | +0.33 dB | 3.18 / 3.43 | 801 |
  | R1.35_4_100 | +0.057 … +0.107 | 0.79–0.89 / 0.90–0.96 | 1.00–1.16 / 0.99 | +0.35 dB | 3.30 / 3.49 | 832 |
  | R-offset (×1.3 to idx 24, then +74 T) | +0.055 … +0.103 (0–5 m/s +0.017) | 0.96–1.04 / 0.96–0.98 | 1.01–1.14 / 0.96–0.99 | +0.72 dB | 3.49 / 3.54 | 801 |
  | g1.2 flat | +0.046 … +0.096 (0–10 m/s +0.04–0.05) | 1.09–1.21 / 1.00–1.01 | 1.22–1.34 / 1.00–1.10 | +0.45 dB (+0.67 full) | 3.33 / 3.38 | 739 |

- **R1.3_8_100 is chosen** because it has the smallest highway outer-loop penalty on light_b. Its taper already acts at idx 18, where the local slope ×1.20 is below the trim ×1.27. It also has the best hard-turn direction at 5–10 m/s, at a benefit within 0.01 of the strongest.

### 6.1 Full `score()` of R1.3_8_100 (`out/s8_score_R1.3_8_100.txt`), every number against V294 in the same batch

**M_SAFE**
- rail +2461 / −2463, unchanged;
- trim cap 801 T (32.5 %), against V294's 616;
- int32 minimum margin 4.06 (a·s, unchanged);
- restart pulse 18/56/188/545 T at 10/30/100/300 deg/s, against 14/43/144/419. This is the lane-only, wheel-held worst case after a |x| > 12000 (1500 deg/s) bail;
- b/b_max 0.246, unchanged;
- the soft-EME 5120–5325 band is unreachable by the lane (|T| ≤ rail). Base assist is not modelled [B].

**M_LOOP (inner, evaluated at Kp(0) = 1248, the strongest trim)**
- stable on all 12 members, including delay ×1.5;
- Ms ≤ 1.17 (light_b);
- GM ≥ 12.5 (tau9, 3.1 m/s);
- light_b |L| at 1–3 Hz is 0.88–1.04 against V294's 0.68–0.80. That is the trim damping the wheel mode. The crossover stays below 3 Hz, not in the unidentified > 8 Hz region.

**M_HF (rule 3)**
- |P/x| at 20 Hz is **2.703** at idx ≤ 8 and 2.079 at idx ≥ 100. That is ×1.30 of V294 at most, and 6.0 % of V282's 44.90, which ground at 20 Hz: a 16.6× margin to the flown grinding gain.
- Stress-mode damping is ≥ V294's at all nine (mode, speed) points: mode20 ζ 0.077/0.100/0.116 against 0.076/0.099/0.115, and open 0.076/0.097/0.113.
- Simulated delivered torque in 5–30 Hz is ×1.14–1.24 of V294, at 0.6–2.0 T rms.
- The staircase response is 5–9 Hz ×0.92 and 13–17 Hz ×1.34 (3.7 T rms).
- [B] for the car: nothing above 8 Hz is identified, and these are stress members.

**M_TRACK (the goal metric)** — see §8.

**M_DRIVE (lp and full, six plants)** — the §0 table. Integrator share −0.034 … +0.011. J error (0.15–2.4 Hz lat-accel) ×0.85–0.95 at ≥ 10 m/s.

**⚠ Harness limitation for schedules (a report).**
- The harness's own `M_DRIVE["outer"]` and `M_LOOP` use Kp at idx 0 for the trim.
- `ff_tf` uses `map′·Kp(idx_op)` and omits `map·Kp′`.
- For a scheduled Kp they therefore evaluate an operating point that does not exist. Its light_b 26.9 m/s Ms of 2.85 is optimistic.
- **Use `s12_outer_final.py`** (`pg_lib.outer_local`), which puts the true local slope and Kp(idx_op) into the same `outer_frf`.

### 6.2 Outer loop at every band's operating point, fork r1 unchanged (`out/s12_outer_final_out.txt`, `fig4_outer_lightb.png`) [E model]

Ms / GM (relay on). V294 → R1.3_8_100:

| op point (v, idx) | nominal | b_lo | J_hi | light_b [B world] |
|---|---|---|---|---|
| low-speed straight (3.1, 14) | 1.22/11.3 → 1.27/10.0 | 1.33/8.3 → 1.41/7.5 | 1.24/11.0 → 1.29/9.5 | 1.85/4.6 → 2.00/4.4 |
| low-speed turn (3.1, 62) | 1.22 → 1.21 | 1.33 → 1.31 | 1.24 → 1.22 | 1.85 → **1.76** |
| hold 5–10 (8, 50) | 1.18 → 1.18 | 1.26 → 1.25 | 1.22 → 1.21 | 1.74 → **1.69** |
| hard 5–10 (8, 75) | 1.18 → **1.15** | 1.26 → **1.21** | 1.22 → **1.18** | 1.74 → **1.57** |
| hold 15–22 (17, 34) | 1.06 → 1.07 | 1.10 → 1.11 | 1.08 → 1.09 | 2.00 → **1.97** |
| hard 15–22 (17, 50) | 1.06 → 1.06 | 1.10 → 1.10 | 1.08 → 1.08 | 2.00 → **1.88** |
| hold 22+ (26.9, 18) | 1.09/20.2 → 1.10/17.1 | 1.15 → 1.18 | 1.10 → 1.12 | **3.00/1.71 → 3.18/1.66** |
| straight 22+ (26.9, 6) | 1.09 → 1.11 | 1.15 → 1.19 | 1.10 → 1.12 | **3.04/1.70 → 3.43/1.60** |

- **Better than V294** in hard turns and mid-speed holds.
- **Worse** on straights and highway holds (small idx).
- **Flat ×1.3:** 3.49 / 3.54 at the two 22+ points.
- **Map ×1.3:** 5.49 / 5.77.

### 6.3 On-centre hunting with friction (`s5_oncentre.py`, `s8 oncentre`) [E model, magnitudes B]

- **Setup:** straight road, desired curvature 0, crown 15 or 60 T plus a 0.05 Hz drift, the real fork port, the byte-exact lane, Karnopp friction, 60 s per case, 4 plants × 5 speeds.
- **No sustained on-centre limit cycle** for any Kp candidate:
  - the rate spectra's strongest 0.1–5 Hz line stays within the noise (+5 to +9 dB, the same as V294's);
  - the 1–3 Hz rate is ≤ 0.05 deg/s, except light_b at d0 60, where it is 0.21 against V294's 0.28.
- **Stick-slip breakaways at 27 m/s rise** on nominal and b_lo (V294 9/min → R1.3_8_100 21–26/min at d0 15). Unchanged at d0 60, and unchanged below 20 m/s.
- **Only the map boost** (M-regress) showed the hunting signature.
- **Caveat:** the sim's absolute on-centre behaviour is noise-model dependent. The harness's h6 says the same about dwells.

---

## 7. How ONE short drive attributes the change (`s6`, `s10`, `s10b`) [E]

**Instruments:**
- the 427 tap (50 Hz, 8-count quantiser), 0x18F rate, and 0xE4 command, all already on the wire;
- r71b's own byte-exact march (`plib`) split into FF (fb forced 0) and trim.

**R-PLATEAU (the edit-live read; one number, readable in any 20 s engaged window)**
- Regress `T_tap = a·F_V294 + b·R_V294 + c` on hands-off, off-rail tap frames with idx 0–8. Report `a / a_baseline`, where `a_baseline` = 0.938 is V294's own r71b value for those frames.
- Positive control: R1.3_8_100 marched byte-exact on r71b, plus r71b's real tap residual, reads **1.321 [1.292, 1.356]**. That is 33/33 windows, needing ≥ 3 s of idx < 9 per window. Hands-off frames with idx < 6 are 18–42 % of every speed band (`s2`).
- Null, the real r71b tap: **1.002 [0.976, 1.035]** (max 1.081). The bands are disjoint.

**R-SHAPE (whole drive, by demand-index bin)** — tap ÷ V294's own:

| idx | tap ratio | Kp/960 |
|---|---|---|
| 0–5 | 1.322 | 1.300 |
| 5–9 | 1.318 | 1.300 |
| 9–18 | 1.290 | 1.286 |
| 18–30 | 1.253 | 1.253 |
| 30–50 | 1.202 | 1.206 |
| 50–80 | 1.111 | 1.120 |
| 80+ | 1.028 | 1.030 |

This reproduces the LERP's shape. It needs minutes of exposure above idx 50, which a single episode may not give; it is the whole-drive confirmation, not the gate.

**R-OWN (identity on the candidate's own march)**
- Synthetic flight: a 0.991, b 0.993, resid 4.88. V294's own is 0.991 / 0.988 / 4.13.
- The real V294 tap against the candidate's march: resid 21.0, and the candidate fits better in **0/38** windows. A V294 car cannot be mistaken for this build.

**The trim coefficient** is 0.210 × Kp(idx)/960 (0.273 at idx ≤ 8). It is read by the metric agent's trim-footprint regression. It is noisier per window (b: 20 s windows ±0.12) and is confirmed over the whole drive.

**The sentence a null licenses** (written before any drive):
- *"If R-PLATEAU reads 1.00 ± 0.05, the new Kp records are not live — wrong image, not flashed, or selector outside the rewritten bank (impossible if all 28 are written). Attribute nothing to V295 and stop."*
- *"If R-PLATEAU reads 1.30 ± 0.05 but the 8–22 m/s turn-hold (the bands report's S2/S3 instrument) is ≤ 0.72 and the 22+ tracking gain ≤ 0.95, the static firmware slope is not what limits the hold at this dose; the under-delivery is the fork's integrator/LAF problem (out of scope), and further Kp is not licensed."*
- *"If the 5–10 m/s matched hard-turn 1.6–3 Hz cell (bands §2.1b) is up by more than ×1.10 against r71b, the regressive taper has not protected the hard-turn band — revert to V294."*

**Symptoms remain the operator's to score.**

---

## 8. The goal metric (cmd vs d²θ/dt²), from the model, and the physics ceiling [E model; B car]

**Amplitude flatness (open loop, 1–3 Hz, |α/cmd| at 30 / 100 / 300 counts rms)**

| member | V294 | R1.3_8_100 |
|---|---|---|
| nominal | 0.206 / 0.496 / 0.587 (small/large 0.35) | 0.358 / 0.655 / 0.714 (**0.50**) |
| F_hi | 0.05 | **0.16** |

- This is the direction of the drive's measured friction deficit (0.37 vs 0.89 deg/s² per count, ratio 0.42). The schedule's small-idx plateau partly cancels it, and the goal metric's small-signal gain moves toward flat.

**Mode-A literal fit (recorded command, dist full)**

| member | band | R² V294 → cand | phase V294 → cand |
|---|---|---|---|
| nominal | 0.3–1 Hz | 0.198 → 0.294 | +78° → +85° |
| light_b | 0.3–1 Hz | 0.152 → 0.280 | – |
| any | 1–3 / 3–8 Hz | unchanged within 0.03 | unchanged within 7° |

- The closed-form |α/cmd| is ×1.10–1.16 at every frequency and on every member, with the shape unchanged.

**The ceiling, plainly**
1. **Below ~1 Hz the command holds an angle against the spring.** 55–95 % of command variance is k·θ (metric agent). A constant command demands a constant angle, not a constant acceleration.
   - No firmware value changes that. It is the fork's torque semantics.
   - Making "α tracks cmd" meaningful there needs a fork change to acceleration semantics, which is out of scope.
2. **Above ~1 Hz the literal metric is the fork reacting to the wheel** (the metric agent's M4). P gain scales that reaction and does not remove it. The 1–3 Hz R² does not move.
3. **An acceleration servo inside the EPS needs |L| ≫ 1 at 0.3–3 Hz.**
   - On the identified family, the plant's b of 5–26 T/(deg/s) dwarfs the trim's ~1.8. At V294 |L| is 0.05–0.41.
   - Via Kp that means ×10–30. The FF rides the same multiply, so the rail would be reached at idx ≤ 24.
   - Via b (the trim lens), b_max = 2301 caps it at ×4.
   - Via the `shl` opcode (e_shift 2→0 with Kp ×4, FF bit-identical), the trim is ×4 → |L| ≤ ~1.6.
   - None of these reaches "≫ 1". **The goal as literally stated is not reachable from the firmware values.** What they can do is move the small-signal gain toward flat and add damping, and the recommendation does a bounded amount of the first.
4. **The under-delivery needs a speed-dependent gain** (r71b turn-hold 0.94 at 22+ against 0.67 at 15–22 and 0.51 at 10–15). Kp's only axis is the demand index, which mixes speed and curvature (`s2`).
   - Highway holds sit at idx 18, mid-speed holds at idx 34–50, and low-speed turns at idx 60–135.
   - Road-to-road hold error of 20–70 % (r72/r73, memory) needs integral action.
   - Rev 4's fork Ki schedule (0.6→2.5 by 18 m/s) reached tracking 0.97–0.99 at speed on-car (r75). That is the lever this lens cannot pull.
5. **An on-car bracket for the dose** [B: confounded by Kp_eff, Ki and the build].
   - r70 (V293, the same generic fork path at LAF 6.0, i.e. FF ×2.33) read tracking 0.884 / 1.020 / **1.123** at 8–15 / 15–22 / >22 m/s. The operator reported oversteer above 20 m/s. r71b (LAF 14) read 0.800 / 0.831 / 0.934.
   - Interpolating linearly to R1.3_8_100's ratio 1.27–1.31 at small idx gives **0.97** at 22+, against the harness's 0.98. This second, on-car method agrees.
   - At 15–22 the interpolation gives 0.86 (at ratio ~1.2) against the harness's 0.88–0.90.
   - At 8–15 the interpolation (0.81) is well below the harness's 10–15 +0.09. The bands and the fork P differ; this is BELIEF.

---

## 9. The three complaints: what this lens can and cannot reach

| complaint | reachable from the P gain? | what R1.3_8_100 is predicted to do |
|---|---|---|
| **Loose/understeer at highway turns** | **Mostly**: the 22+ hold gap is ~6 %, and ratio ~1.27 at idx 18 closes it | 22+ tracking ≈ 0.98, hold ≈ 1.00. 15–22 hold 0.67 → ≈ 0.75–0.78 [DIR]; the rest there needs the fork's Ki |
| **Loose on straights and turns at low speed** | **Straights: partly. Turns at 0–5 m/s: NO.** Those turns sit at idx 60–135 (taper to V294), and the low-speed factor in the fork dominates (i-share 0.51) | straight delivery +0.06–0.10; 5–10 m/s hold +0.02–0.05; 0–5 m/s turns ≈ 0. **A later taper end (runner-up R1.3_8_150) buys +0.01–0.05 there at a hard-turn cost** |
| **Jerky on hard turns at medium speed** | **Only the loop-generated share.** Under the identified family most of the 1.6–3 Hz hard-turn motion is road/tyre disturbance (harness §0.1) [B] | 5–10 m/s ×0.80–0.96 (all plants, both models); 15–22 m/s ×0.99 (full) … ×1.12 (lp, light_b). Not worse at 15–22; better at 5–10. The operator scores it |

---

## 10. On-car record of every cell touched

Method: grep of `analysis-2020accord/builds/**/build_v*_tva.py` and `docs/BUILD-LINEAGE*.md`.

**Kp bank `0xCB994` (28 records, slot 7 `0xE5378`)**

*Flown:*
- stock [248, 512, 645, 696, 696] rising, on the RATE operand;
- V281 rev 3 / V282 flat 248 (per-slot own Y[0]), rate operand;
- V283 (V282 + Ki 50, rejected);
- V293 flat 120 × all 28, torque mode;
- V294 flat 960 × all 28, trim operand. No grinding (operator).

*Built, not flown:*
- V279 256 flat;
- V281 rev 2 (moved X knots, superseded);
- V284: the only prior *shaped* table (slot 7 only, X 0/32/36/44/88, Y 248/248/512/512/248). SHELVED on V282's rate-loop margin at 7.3 Hz (loop gain 0.976, headroom 2.5 %), with "do not raise Kp anywhere without a fresh margin measurement";
- V285 Kp 0 (bench).

*What that means here:*
- **No non-flat Kp and no moved Kp X knot has ever flown.**
- V284's verdict is about a loop that does not exist on V294: the rate operand is gone.
- The fresh margin measurement it demands is §6.1–6.2 for the loops that do exist (inner trim, outer fork loop). **That is EVIDENCE for the model and BELIEF for the car.**
- FALSIFIED ≠ untested: the regressive torque-mode schedule is untested.

**Not touched and not recommended:** the map `0xC9A88` (linear ×6 since V282, flown), the fb cells, C, Kd/Ki, the clamps, the output lag, and both opcodes.

---

## 11. Runner-ups (numbers from `s13`/`s7b`, all differences against V294)

1. **R1.35_4_100** (X 0/4/52/100/208, Y 1296/1296/1128/960/960): +0.005–0.01 more benefit everywhere. light_b 22+ Ms 3.30/3.49 and lp hard16 at 15–22 up to ×1.16. Pick it if the orchestrator weighs highway understeer over the light_b risk.
2. **R1.3_8_60** (taper ends at idx 60; `s7` rev 1): the hard-turn-first variant. hard16 ≤ ×0.99 lp and full; benefit only +0.03–0.05 (22+ hold +0.052).
3. **R1.3_8_150 / R1.25_4_140 / R1.25_12_180**: buy the 0–5 m/s turns (+0.014–0.027), with lp hard16 ×1.17–1.24 and full ×1.03–1.05.
4. **Flat g1.2 (Kp 1152 × 28)**: the simplest, and selector-invariant without rewriting X. It is on the G6 line (hard16 full light_b 15–22 ×1.10), and lc is up to +0.67 dB. **Flat ≥ 1.3 FAILS G6.**
5. **Map shapes**: not recommended (§5). They are dominated by Kp on the outer loop and are the hunting class.

---

## 12. Risks, stated before the drive

1. **The light_b world at highway** [B]. If the car is lightly damped at 27 m/s (the prior; the drive's +10.3 dB 1.95 Hz rate line on hard curves > 15 m/s is weak support), the outer-loop Ms rises 3.00 → 3.18 (holds) and 3.04 → 3.43 (straights).
   - The failure would feel like a 2.5 Hz weave on highway straights and holds.
   - The instrument is the bands report's S7 rule at ≥ 19 m/s, run as for r71b.
2. **More loop-generated 1–3 Hz motion on straights and holds** in the plant-alone model (+9–30 %). The operator's "jerky" is about hard turns, but a straight-line nervousness is the risk this recommendation takes on.
3. **Hard turns at 5–10 m/s get ×0.7–0.9 local slope.** The fork must move its command further for the same torque change, so a slower response to a sudden demand change in those turns is possible (not seen in the sim; hold +0.02–0.05).
4. **Zero-command torque up to 801 T** (V294 616; V282 flew 2463). This is adversary B's EME-band argument at 0.33× V282's exposure. Restart pulse ×1.3.
5. **Simulated delivered torque in 5–30 Hz is ×1.14–1.24** (0.6–2 T rms), and the controller gain at 20 Hz is ×1.30 of V294 = 6 % of V282's. Nothing above 8 Hz is identified. The stress members show no loss of damping.
6. **The build rewrites 252 bytes over five CRC pages**, the X knots included. That is more bytes than V294's Kp edit, though the same class (cal-only, Kp bank).
7. **The harness predicts the outer loop FIT in 4/5 bands only.** 15–22 m/s is DIRECTIONAL, and the planner is exogenous: a car that delivers more would get a different plan.

## 13. Files

- `CRITERIA-p-gain.md`: the pre-registered gates.
- `pg_lib.py`: surface, local slope, static ratio, and `outer_local` (scheduled-Kp linearisation).
- `s0_spotcheck.py`: harness spot-check (lane vs golden, surface, one retrodiction row).
- `s1_flat_sweep.py`: flat g plus the FF-only / trim-only diagnostics.
- `s2_idx_census.py`: where r71b sat on the idx axis by band and regime.
- `s3_shapes.py`, `s4_shape_sweep.py`: flat, Kp schedules and map shapes (surface; sim; outer loop at op points).
- `s5_oncentre.py`: the on-centre hunting sim.
- `s6_attribution.py`, `s10_attr_finalists.py`, `s10b_null_plateau.py`: the wire read (positive control + null).
- `s7_regress_grid.py`, `s7b_grid2.py`: the regressive grid.
- `s8_finalists.py`: the shared `score()` + on-centre for the four finalists.
- `s9_kp_records.py`: the 28 Kp records on V294.
- `s11_figures.py`: `out/fig1_kp_lerp.png`, `fig2_surface.png`, `fig3_ratios.png`, `fig4_outer_lightb.png`.
- `s12_outer_final.py`: outer loop at every op point, 6 members.
- `s13_compare.py`: the finalist comparison.
- `s14_rec_table.py`: the recommendation's surface table.
- `s15_candidate_spec.py`: `out/V295_p-gain_candidate_spec.json`, the byte-level spec per record. No image.
- `s16_surface_crosscheck.py`: the listing-style LERP and surface second method (`out/s16_surface_crosscheck_out.txt`).
- Every `*_out.txt` / `*.json` is in `out/`.
