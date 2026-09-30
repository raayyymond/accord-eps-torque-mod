# V295 design, lens "trim-ratio": raise the acceleration trim, hold the feedforward byte-identical

Subagent `trim-ratio`, 2026-09-30. **Design only.**
- Nothing was built, flashed or sent.
- No fork, firmware artifact, STATE, memory, lineage or golden-model file was touched, and nothing was committed.
- Pre-registered FAIL criteria are in `CRITERIA-trim-ratio.md`, written before any candidate number existed.
- Every decision-bearing claim is marked **[E]** EVIDENCE (with its method) or **[B]** BELIEF.
- The operator scores symptoms; this page scores bands, transfer functions and simulations.

---

## 0. Bottom line

**The one candidate: V294 + ONE calibration cell.** `0xC63EA` (fb-lag gain b) goes **567 → 964**.

| property | value |
|---|---|
| trim gain | ×1.70 at every frequency |
| pole a (0xC63E8) | 1011 (2.03 Hz), unchanged |
| cap C (0xC62E6) | 1024, unchanged |
| Kp, shl, map, clamps, output lag | unchanged |
| code bytes | none |
| edit class | cal-only, one u16, plus page CRCs |

**What it is.** The same lever V294 flew, pushed ×1.7 in the same direction. b = 964 has never been on any image [E, s9: 252 images byte-read].

**What it buys** (all relative to V294, same batch):
- **"Jerky on hard turns at medium speed" is the only complaint this lens can reach.** Hard-turn 1.6–3 Hz wheel rate at 5–10 m/s moves by these factors (a sim counterfactual, [B], biased toward "no change"):
  - ×0.87 on the identified nominal plant;
  - ×0.75–0.92 across all 12 members;
  - ×0.75 on the lightly damped prior.
- At 15–22 m/s the change is only ×0.95 on nominal (×0.74 on the prior).
- The 1–5 Hz limit-cycle line drops 0.3–4.8 dB.

**What it cannot reach:**
- **"Loose at low speed" and "loose / understeer at highway turns" are out of reach.** Tracking gain, turn-hold, straight delivery and integrator share move by ≤ 0.010 in every band on every member [E for the sim]. The trim has no DC by construction: the difference operand settles to exactly 0 at any constant rate.
- **Low-speed side effect [B].** It may make low-speed looseness slightly *worse*. At 0–5 m/s:
  - the J-style lateral-accel error rises ×1.02–1.12 (nominal ×1.04, prior ×1.12, dist lp);
  - the 0.3–1 Hz wheel rate rises up to ×1.19.

  The trim's inertia below its 2 Hz pole lowers and de-damps the soft low-speed wheel mode. This is the redo audit's 2026-09-23 finding, scaled ×1.7.
- **The goal metric (cmd vs wheel angular acceleration) barely moves:**
  - |α/cmd| flatness over 0.5–3 Hz goes 5.2 → 4.7 on nominal and 7.5 → 5.6 on the prior;
  - the literal 1–3 Hz regression R² goes 0.316 → 0.328;
  - the friction deficit is unchanged.

  The ceiling is physics, not the value (§8). On the identified plant, making α track the command would need **×9–73 V294's controller gain at 1 Hz** (×7–48 at 2 Hz). That is the V282 grinding class (V282 = ×21.6).

**The binding constraint.** It is my own pre-registered HF-content clause (F5-HF): no band of simulated delivered 5–30 Hz torque may exceed ×1.5 V294.
- b 964 reads ×1.45 in its worst band. G 1.8 fails it, and so does b 1134 (G 2.0, ×1.65).
- Without that clause, the linear stress-member analysis and the on-car record would allow about G 3 (§6).

**The wire read (existing instruments, one short drive):**
- The flown E3 trim regression on the 427 tap: predicted **β +0.361**, against V294's +0.21.
  - The per-20 s-window 5–95 % range [+0.283, +0.346] is **disjoint** from V294's [+0.152, +0.222].
  - One hands-off 20 s window attributes the edit.
  - Model selection names b 964 in 6/6 windows [E on r71b's own excitation].
- The FF identity must still hold, since the surface is byte-identical.

**Lens verdict.** Not a "no change": the pick improves the medium-speed jerk band ≥ 10 % on both worlds, as pre-registered. But the margin is thin:
- the gain is ×1.7, just above my ×1.5 lens-FAIL line;
- under the identified plant the operator may not feel it.

The null sentence (§9) is written so that such a drive still decides something.

---

## 1. Pre-registered criteria: what fired

The criteria live in `CRITERIA-trim-ratio.md`. The candidate is b 964.

| clause | result for b 964 | notes |
|---|---|---|
| **F1** FF identity | **PASS** [E] | Golden surface equal at 723/723 (idx × 3 tapers). The Lane march at x = 0 equals V294 on 30,000/30,000 ticks. This holds for every candidate in the lens (s3a) |
| **F2** HF guard | **PASS** [E, model] | \|T/x\| 10–25 Hz ×1.70 (≤ 3). Stress ζ ≥ V294 on 9/9 member/speed cells (+0.001 … +0.009). Every member stable. Worst Ms at delay ×1.5 is **1.23** (`tau9`, 3.1 m/s; V294's worst is 1.13) |
| **F3** outer loop | **PASS** [B, prior world] | `light_b` outer GM_min 1.68 → **2.51** (rises everywhere). Identified outer Ms max 1.275 (V294 1.275) |
| **F4** safety | **PASS** [E] | Rail +2461/−2463 and sub-rail 0.6409 T/wire unchanged. b 964 ≤ b_max 2301. int32 min margin **2.39** (a·s). Trim cap 616 T unchanged. Restart peak ≤ 542 ≤ 615. `problems()` empty |
| **F5** closed loop, nominal + light_b, full + lp | **PASS** | Tracking Δ ≥ −0.001. Turn-hold Δ ≥ −0.008. hard16 ≤ ×1.02 (nominal lp 22+). Limit cycle −0.7 / −4.8 dB. **HF mode A max ×1.45** (13–17 Hz nominal); mode B lp max ×1.07 |
| **F6** attribution | **PASS** [E] | E3 / SCALE / SEL separate b 964 from V294 by more than 100 CI half-widths pooled, and in every single 20 s window. No other cell changes. C is unchanged, and binds on 0.003 % of engaged ticks, so nothing unreadable is shipped |
| lens-level ≥ 10 % on hard16 (full, nominal AND light_b) | **met at 5–10 m/s** (×0.87 / ×0.75) | At 15–22 m/s nominal only ×0.95 |

**Clauses that fired on OTHER candidates (not waived):**
- **F5-HF fired on b 1134 (G 2.0)**: ×1.65 at 13–17 Hz, mode A, dist full.
  - It also fires on every G ≥ 1.8 and on a1005/b1134 [E, `s7_hf_scan_out.txt`].
  - I believe the clause is conservative. Under dist lp (the loop's own motion) the same candidates read ×1.04–1.09. The extra content under full is the damper reacting to replayed wheel motion above 8 Hz, which is not identified, and r_hi falls ×0.83–0.98.
  - I wrote the clause, it fired, and I **do not waive it**. b 1134 is runner-up 2.
- **F2 (Ms at delay ×1.5 ≤ 1.5)** is violated by a1017 G ≥ 3 (1.53) and approached by a1011 G3 (1.46).
- **F5 turn-hold** fired on a1017 G3: light_b full 5–10 m/s, −0.022.

---

## 2. Harness spot-check (before any use): PASS

Script and output: `s0_spotcheck.py` / `s0_spotcheck_out.txt`.
- **Lane vs golden model [E].** 40,000 ticks, 0 mismatches (T, E, P, S, y), on V294 and on this lens's own class. That class includes shl 1 with Kp 1920, shl 0 with Kp 3840, a 1017/1020, b up to 1700 and C 256/512. The harness's H1a covered none of it exactly.
- **Retrodiction row [E].** V294, mode B, dist lp, nominal, tracking gain by band: 0.8397 / 0.8649 / 0.5862 / 0.7636 / 0.9167. The report gives 0.840 / 0.865 / 0.586 / 0.764 / 0.917. Full 5–10 m/s hard16 is 14.885 (report 14.89).

---

## 3. The lens, in the firmware's own arithmetic

What changes, as an integer Python mirror. Addresses are from the V294 image. The Ghidra listing (dry run) was confirmed at 0x28F7C–0x28FBE this session.

```python
# 0x28F86  ld.hu 0x73ea[tp], r16      b  = [0xC63EA] u16 -> 964 (was 567)   ONLY reader of the cell [E: Ghidra + raw scan]
# 0x28F8A  ld.h  0x73e8[tp], r9       a  = [0xC63E8] s16 = 1011 (2.03 Hz)   unchanged
# 0x28F8E  mul r16, r7                b*x                 (x = 8 counts per deg/s, |x| <= 12000 else bail)
# 0x28F92  mul r26, r9                a*s_old
s_new = ((a * s_old) >> 10) + ((b * x) >> 10)            # 0x28F9A / 0x28FA0 sar 10 ; 0x28FA2 add
r26   = clamp(s_new - s_old, -C, +C)                     # 0x28FA4 subr (V294) ; C = [0xC62E6] = 1024 ld.hu x3
E     = (sp << 2) - r26                                  # 0x29D76 shl 2 ; 0x29D78 sub          unchanged
P     = clamp((E * 960) >> 8, +-15360)                   # = 15*sp  -  floor(3.75*r26)   (FF bit-identical)
```

- **Static FF [E].** P at r26 = 0 is `15·sp`, independent of b. The golden surface and the Lane march are identical (F1). The sub-rail slope stays 0.6409 T per wire count and the rail stays 2461. **The fork's DC plant gain is untouched.**
- **Trim [E, s3 two methods].** T_trim ∝ (Kp/256)·r26, and r26 ∝ b.
  - The HF gain (above the pole) is |T/x| ×1.70 at 10–25 Hz. Analytic `lane_ctf` equals a time-domain sinusoid march to 4 digits.
  - The inertia below the pole is K_α 0.210 → **0.356 T per deg/s²**. The closed form agrees with a constant-α ramp march within 1–3 % (floor bias).
  - At 2.5 Hz the trim is 1.82 → **3.09 T per deg/s of damping**, plus 0.025 → 0.042 T per deg/s² of inertia.
- **Why not the shl / Kp pair [E].**
  - Kp·2^shift = 3840 keeps the FF exact: 3840·sp/256 = 15·sp for any shift. The trim then scales with Kp·b, so the shift buys nothing that b does not, **until b hits the overflow bound**.
  - That bound is b/(1024 − a) ≤ 2³¹/(12000·a), about 175 per x count. It caps K_α at 0.85·(Kp/960) at margin 1, and at half that for my pre-registered margin 2.
  - So shl 2 reaches G 2.03 at a 1011 with margin 2 (G 4.06 at margin 1). The opcode is needed only for G > 2 with margin 2, or for a lower pole at G ≥ 1.1.
  - The pick needs neither.
- **The pole [E, linear].**
  - At fixed K_α (the overflow-bound case), the damping at frequency ω, K_α·ω_p·ω²/(ω² + ω_p²), is maximised at ω_p = ω. So a 2 Hz pole is optimal for the 1.95–2.7 Hz jerk line.
  - At fixed HF gain, a lower pole gives more 2 Hz damping and more low-speed inertia.
  - V294's 2.03 Hz is kept, which also keeps the flown E3 regressor exactly valid.

---

## 4. The (gain, pole) plane on the whole family (linear, exact 1 kHz)

Source: `s1_plane.py`, `s1_plane.json`, `s1_plane_out.txt` and `s1b_detail.py`. [E for the model, B for the car.] 66 points were evaluated: a ∈ {993…1020} (4.9…0.62 Hz), G ∈ {1…4}, each realised with the least code change at int32 margin ≥ 2.

**Column key:**
- **K_α**: T per deg/s².
- **d2.5**: damping at 2.5 Hz, T per deg/s.
- **Ms15**: worst inner Ms at delay ×1.5 over 8 members × 5 speeds.
- **stress Δζ**: worst of ζ_cand − min(ζ_V294, ζ_open) over mode13 / 20 / 20_lo × 5 / 12 / 25 m/s.
- **lb27 GM**: outer GM on `light_b` at 26.9 m/s with the relay.
- **flatness**: max/min of |α/cmd| over 0.5–3 Hz.

| point | pole Hz | b / shl / Kp / C | K_α | d2.5 | HF ×V294 | \|P/x\|20 | Ms15 | stress Δζ | lb27 GM | flatness nom@12 | flatness lb@12 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| V294 | 2.03 | 567/2/960/1024 | 0.210 | 1.83 | 1.00 | 2.08 | 1.13 | +0.001 | 1.68 | 5.24 | 7.46 |
| **pick b964** | 2.03 | **964**/2/960/1024 | 0.356 | 3.09 | 1.70 | 3.54 | 1.23 | +0.001 | 2.51 | ≈4.7 | ≈5.6 |
| a1011 G2 | 2.03 | 1134/2/960/1024 | 0.419 | 3.65 | 2.00 | 4.16 | 1.27 | +0.002 | 2.87 | 4.49 | 5.04 |
| a1011 G3 | 2.03 | 850/1/1920/512 | 0.628 | 5.47 | 3.00 | 6.23 | 1.46 | +0.002 | 4.19 | 3.93 | 3.59 |
| a1011 G4 | 2.03 | 1134/1/1920/512 | 0.838 | 7.30 | 4.00 | 8.32 | 1.69 | +0.003 | 5.66 | 3.49 | 2.68 |
| a1017 G1 | 1.09 | 567/2/960/1024 | 0.388 | 2.19 | 1.01 | 2.08 | 1.15 | +0.001 | 1.87 | 5.25 | 7.45 |
| a1017 G2 | 1.09 | 567/1/1920/512 | 0.777 | 4.38 | 2.02 | 4.16 | 1.31 | +0.001 | 3.14 | 4.53 | 4.78 |
| a1014 G1.5 | 1.56 | 850/2/960/1024 | 0.408 | 3.04 | 1.51 | 3.12 | 1.21 | +0.001 | 2.41 | 4.81 | 5.97 |
| a1005 G2 | 2.98 | 1134/2/960/1024 | 0.287 | 2.86 | 2.00 | 4.15 | 1.24 | +0.001 | 2.33 | 4.65 | 5.43 |
| a993 G1 | 4.89 | 567/2/960/1024 | 0.088 | 0.90 | 0.99 | 2.05 | 1.10 | +0.000 | 1.13 | 5.57 | 9.46 |

What the plane shows:
- **Stress members [B: stress cases, nothing above 8 Hz is identified].** The trim never reduces the 13 or 20 Hz flexible-mode ζ, up to G 4. At 13–20 Hz the trim is still −60° to −70° from pure damping.
- **Inner loop.** The margin that erodes is delay. The worst case is always `tau9` (9 ms) at ×1.5, i.e. 13.5 ms; the measured transport delay is about 2 ms. Ms15 crosses 1.5 at about G 3.1 at 2 Hz and at G 3 at 1.1 Hz.
- **Outer loop, the pessimistic prior.** At highway speed it gets *better* with trim, because the trim damps the prior's lightly damped wheel. GM 1.68 → 2.5 (pick) → 4.2 (G3).
- **The inner ~1 Hz wheel mode in `light_b` loses damping** as K_α rises: ζ 0.45 (V294) → 0.42–0.49 (pick) → 0.38 (G3). The trim's inertia below its pole lowers that mode. This is the low-speed cost seen in §5.

---

## 5. Closed loop: fork in the loop, mode B, V294 in the same batch

Sources:
- `s2_sweep*` (10 candidates × 4 members);
- `s8_family*` (the pick ±1 dose step × **12 members**, the whole identified family plus the prior);
- `s5_score_b964_out.txt` (the full harness `score()`).

Every number is candidate / V294 or candidate − V294 [B: sim counterfactual]. The harness warns that `full` is biased toward "no change" and that `lp` is the plant alone, which is NOT FIT for 1–8 Hz motion. I quote directions and ranges, not magnitudes.

**b 964, range over the 12 members, with `light_b` in brackets:**

| metric | dist | 0–5 | 5–10 | 10–15 | 15–22 | 22+ |
|---|---|---|---|---|---|---|
| **hard-turn 1.6–3 Hz rate** ×, *the jerk complaint* | full | n/t | **0.75–0.92** [0.75] | n/t | **0.74–0.97** [0.74] | 0.77–0.98 |
| | lp | n/t | 0.73–0.95 [0.73] | n/t | 0.73–1.05 [0.73] | 0.87–1.06 |
| 1–3 Hz wheel rate × | full | 0.80–0.93 | 0.73–0.92 | 0.83–0.94 | 0.80–0.97 | 0.88–0.98 |
| 3–8 Hz wheel rate × | full | 0.90–0.98 | 0.87–0.98 | 0.91–1.00 | 0.87–0.99 | 0.92–0.98 |
| **0.3–1 Hz wheel rate** × | full | 1.00–**1.19** | 0.98–1.04 | 0.98–0.99 | 0.99–1.02 | 0.99–1.02 |
| | lp | 1.01–**1.19** | 1.01–1.07 | 1.01–1.03 | 1.00–1.03 | 0.99–1.02 |
| **J-style lat-accel error (0.15–2.4 Hz)** × | full | 0.97–1.09 | 0.98–1.06 | 0.99–1.00 | 1.00–1.01 | 1.00–1.01 |
| | lp | 1.02–**1.12** | 1.01–1.08 | 1.00–1.01 | 1.00–1.02 | 1.00–1.01 |
| tracking gain Δ | full / lp | +0.001…+0.004 | ≤ +0.002 | ≤ ±0.001 | ≤ ±0.001 | ≤ +0.003 |
| turn-hold Δ | full / lp | n/t | −0.008…+0.010 | −0.005…+0.007 | −0.002…+0.006 | −0.001…+0.010 |
| straight delivery Δ | full / lp | −0.003…+0.005 | −0.005…+0.002 | −0.005…+0.002 | −0.004…+0.001 | +0.001…+0.004 |
| 1–5 Hz limit-cycle line | full / lp | −0.4 to −4.8 dB / −0.3 to −1.5 dB | | | | |

Notes on the table:
- The three lp hard16 readings above 1.00 are J_hi2 ×1.05 at 15–22, and F_lo ×1.05 and ms_free ×1.06 at 22+. They sit at an absolute level of about 0.17 deg/s: the plant alone makes 2–9 % of the drive's level there (harness H4), so they are noise-level.
- **The physical reading [B]:**
  - The trim is a heavier wheel below 2 Hz and a damper above it.
  - It moves wheel motion out of 1.6–3 Hz, which is the jerk band.
  - It lets a little more through a slower, less damped 0.3–1 Hz mode, and only where the spring is soft (0–5 m/s, k about 6.5 T/deg).

Dose ladder at the 2.03 Hz pole (full, 5–10 m/s hard16, nominal / light_b):

| b | G | hard16, nominal / light_b | HF max (mode A full) | 0–5 J_err lp, nominal / light_b |
|---|---|---|---|---|
| 850 | 1.5 | 0.90 / 0.81 | ×1.31 | 1.03 / 1.08 |
| **964** | **1.7** | **0.87 / 0.75** | **×1.45** | **1.04 / 1.12** |
| 1134 | 2.0 | 0.82 / 0.69 | ×1.65 FAIL | 1.06 / 1.18 |

At G 3 (shl 1): 0.69 / 0.52, HF ×2.40 (13–17 Hz, `s5_score_g3sh1.json`; FAIL), J_err 1.12 / 1.37.

**Snap / breakaway** (`s6b_step_out.txt`; open loop, zero noise, wheel stuck, command stepped past breakaway) [B]:
- G 2.0 (b 1134) gives a peak wheel rate after breakaway of ×0.80–0.96 V294; b 964 lies between V294 and it, and every row is monotone in G.
- **Peak acceleration at the breakaway instant is unchanged** (×0.93–1.00). The first ~50–100 ms of a snap is beyond this term's reach: the 2 Hz pole, the 5.05 Hz output lag and the ~2 ms delay all come first.
- The settled angle and the overshoot are identical (the plant is overdamped, and the trim has no DC).
- ⚠ The first snap probe (`s6_snap.py`, a slow ramp) produced continuous slides, not stick-slip. **It is non-informative and not cited.**

---

## 6. HF / grinding margin, against the stress members AND the on-car record

| quantity | V294 (flies clean, r71b) | **b 964** | V282 (ground at 20 Hz) | source |
|---|---|---|---|---|
| \|P/x\| at 20 Hz, P-counts per x-count | 2.079 | **3.535** | 44.90 | [E] harness `lane_ctf` = time-domain march (s3b) |
| \|T/x\| 10–25 Hz | 1 | ×1.70 | not given | [E] |
| mode20 ζ at 5 / 12 / 25 m/s | 0.076 / 0.099 / 0.115 | 0.077 / 0.101 / 0.116 | (0.016 on-car, de-damped) | [B] stress member; two pole codes agree (s3d) |
| mode13 ζ | 0.145 / 0.171 / 0.146 | 0.150 / 0.178 / 0.147 | – | [B] |
| mode20_lo ζ | 0.126 / 0.226 / 0.191 | 0.128 / 0.235 / 0.193 | – | [B] |
| simulated delivered HF torque, 5–9 / 9–13 / 13–17 / 17–23 / 23–30 Hz, mode A full (nominal) | 1.74 / 1.11 / 0.65 / 0.53 / 0.23 T | ×1.34 / 1.32 / **1.45** / 1.15 / 1.22 | – | [B] replayed disturbance, unidentified above 8 Hz |
| same, mode B lp | 1.36 / 0.81 / 0.40 / 0.52 / 0.20 | ×0.93–1.07 | – | [B] |
| staircase HF (command at the slew cap, x = 0) | 21.3 / 7.5 / 2.7 / 1.5 / 0.8 | identical | – | [E] the FF is unchanged |

**The margin argument:**
1. **It is the same term V294 flies clean, scaled ×1.7.** The controller's 20 Hz gain stays **12.7× below V282's**.
2. **It is still a damper at 13–20 Hz.** Its phase is −60° to −70°, so it adds ζ to every stress mode instead of removing it.
3. **The 5–30 Hz torque it adds is its reaction to wheel motion**, not a new excitation. The FF staircase is byte-identical, and in lp (no replayed HF road motion) the delivered HF moves by ≤ ×1.07.

This is a margin argument, not evidence. **Nothing between 2.08 and 44.9 has ever flown on this operand.** The step from 2.08 to 3.54 is the kit's next data point, and the revert signature below watches it.

---

## 7. The three complaints and the goal metric, separately

**1. "Jerky on hard turns at medium speed": REACHABLE, modestly.**
- Hard16 at 5–10 m/s: ×0.87 on nominal, ×0.75–0.92 across the family, ×0.75 on the prior. At 15–22 m/s: ×0.95 / ×0.74.
- The 1.95 Hz hard-curve line sits right at the trim's pole, where damping per unit gain is maximal (§3).
- Whether the operator feels it depends on which world is real:
  - **identified world**: the jerk band is road/tyre-driven, and 5–13 % is below what he is likely to feel [B];
  - **prior world**: loop-generated, 25 %.

**2. "Loose on straights and turns at low speed": NOT REACHABLE, and slightly at risk.**
- Tracking gain Δ ≤ +0.004 and straight delivery Δ within ±0.005.
- At 0–5 m/s the lat-accel error is ×1.02–1.12 and the 0.3–1 Hz wheel rate up to ×1.19 [B].
- If he reports low speed looser, that is the predicted side effect, not a surprise.
- The firmware lever that is neutral at low speed is the pole-only a 1017 (runner-up 4). The actual "loose" is the fork's slow outer loop (Ki 0.3 / LAF 14): out of this session's scope.

**3. "Loose / understeer at highway turns": NOT REACHABLE.**
- Turn-hold and tracking gain move by ≤ 0.010 at 15–22 and 22+ m/s on every member.
- The static FF, which is what holds a curve, is byte-identical by construction, and the trim has no DC.

**Goal metric: cmd vs wheel angular acceleration. It moves, but only a little.**

| quantity | V294 | b 964 |
|---|---|---|
| closed-form \|α/cmd\| flatness 0.5–3 Hz (nominal, 12 m/s) | 5.24 | 4.70 |
| same, `light_b` | 7.47 | 5.63 |
| \|α/cmd\| at 0.3 Hz | 0.075 | 0.076 (spring-dominated, untouched) |
| mode A literal fit 1–3 Hz: R² / \|G\| / phase | 0.316 / 1.44 / +29° | 0.328 / 1.31 / +28° |
| friction deficit (small/large amplitude ratio, 1–3 Hz) | 0.351 | 0.358 (unchanged) |

The flatness gains come from *lowering* the 2–3 Hz response, not from raising the low side.

---

## 8. Physics honesty: the ceiling

Source: `s10_ceiling_out.txt`. [E for the linear model, B for the car.]

**The spring.** The trim is an *acceleration* term only between the spring corner f_s = √(k/K_α)/2π and its own 2.03 Hz pole. Below f_s the spring k·θ out-pulls it.

| speed knot, m/s | 3.1 | 8 | 12 | 17 | 27 |
|---|---|---|---|---|---|
| nominal k, T/deg | 6.5 | 20 | 24 | 80 | 56 |
| f_s, V294 (Hz) | 0.88 | 1.56 | 1.71 | **3.10** | **2.60** |
| f_s, pick (Hz) | 0.68 | 1.20 | 1.31 | **2.38** | 1.99 |
| f_s, rigorous cal-only max b 2301 (margin 1) | 0.44 | 0.78 | 0.85 | 1.54 | 1.29 |

At 15–22 m/s there is **no** frequency where even the pick is an acceleration servo: f_s is above the pole.

**Loop gain needed to "track".** An |L| of 3 (acceleration error about 25 %) needs this multiple of V294's HF gain:

| world | at 1 Hz | at 2 Hz |
|---|---|---|
| identified family | ×9–73 | ×7–48 |
| `light_b` | ×4–12 | ×2.7–4.5 |

A 4.9 Hz pole makes it about twice as bad. V282's rate loop was ×21.6. **On the identified plant, an EPS acceleration servo that tracks at 1 Hz is the grinding class.** It cannot be had with values under the no-grinding constraint.

**The other limits:**
- **Friction.** The trim is zero at rest and lags the breakaway (§5), so the small-signal deficit is untouched.
- **The 5.05 Hz output lag.** It sits after the sum: −22° at 2 Hz, −45° at 5 Hz, and it lags the FF too.
- **The overflow bound.** It caps K_α at 0.85 at shl 2.

**What would be needed beyond values:**
- **(i)** A **filter cave** that keeps 1–3 Hz gain while cutting 10–25 Hz. This is V289's hook class, and it is a bricking-class risk.
- **(ii)** A **command whose semantics are acceleration**, with the spring handled by the fork's FF: a fork change, out of scope.
- **(iii)** An **integrator on the α-error**. That is Ki on this operand, the class the operator rejected on V283.

---

## 9. The wire read: one short drive, existing instruments only

| changed value | instrument | predicted (r71b excitation, b 964) | V294 | method |
|---|---|---|---|---|
| static FF (unchanged) | FF identity, `v293_flight_read.identity_block`, V293 cells | R² ≥ 0.98 all engaged, ≥ 0.997 at \|acc\| < 20 deg/s² | 0.9868 / 0.998 | [E] surface identical |
| **b 567 → 964** | **E3**: tap − null march ~ 1 + Rm + pred + dFF/dt; Rm = lp1(−d/dt lp1(wire/8, **2.03 Hz**), 5.05 Hz). The *flown* regressor, unchanged | **pooled +0.361 [0.358, 0.363]**; per 20 s window median +0.326, 5–95 % **[+0.283, +0.346]** | +0.213 [0.211, 0.214]; window [+0.152, +0.222] | [E] fake-tap = real tap − quant(V294 march) + quant(b964 march), byte-exact 1 kHz Lane, 709 s hands-off (`s4_attrib_out.txt`) |
| same | **SCALE**: residual on V294's modelled trim | pooled **1.654** [1.630, 1.664] | 0.989 | [E]. Per-window SCALE is biased low by nuisance collinearity: **read it pooled only** |
| same | **SEL**: rms(tap − quant(march(cells))) over {V294, null, b850, b964, b1134, …} | b964 minimal in **6/6** windows (3.64 counts vs 5.00 for b850, 5.92 for b1134, 11.1 for V294) | V294 minimal in 4/6 of its own windows | [E] |
| C (unchanged, not readable) | – | binds on 0.003 % of engaged ticks | 0 % | [E] clamp census |

**Sentences each read licenses, written before the drive:**
- **β ≥ +0.28 on any 20 s hands-off window (pooled ≥ +0.30), SCALE ≈ 1.6, SEL names b964: the edit is live.** It is ×1.7 V294's trim, right sign.
- **β within +0.15 … +0.25 (pooled ≈ 0.21): the car is running V294's trim gain.** The b edit did not reach the ECU (wrong image or flash). The drive says nothing about ×1.7; stop and check the image.
- **|β| < 0.04: no trim at all.** This is a V293-class image. **Stop.**
- **β < −0.10: sign inverted.** Impossible for a b-only edit unless the image is wrong. **Stop and revert to V294.**
- **FF identity R² < 0.95: the static surface is not V294's.** Wrong image. **Stop.**
- **Outcome, if the edit is live:**
  - **(a)** If he reports hard medium-speed turns *less jerky*, and the hard-turn 1.6–3 Hz wheel rate in matched cells drops ≥ 20 % against r71b, the jerk is loop-sensitive (the prior's world). The next dose, G 2.5–3 via shl 1, is licensed; it needs the F5-HF clause re-decided.
  - **(b)** If he reports **no change**, and the band moves ≤ 10 %, **the medium-speed jerk is not governed by 2 Hz damping at any HF-safe dose.** That is the identified world: road/tyre-driven. This lens's remaining headroom is ×1.7 → ×3 and would buy at most another ×0.8. **Stop turning this knob.**
  - **(c)** If he reports **low speed looser**, that is the predicted inertia side effect. **Revert b.** The pole-only a 1017 is the low-speed-neutral alternative.
- **Revert signature.** Any *new* line in 5–30 Hz on the 0x18F rate, or the operator reporting grinding or stutter, means revert to V294. This is the first dose above 2.08 P-counts per x-count on this operand.

---

## 10. Checks demanded by design rule 7

| check | result |
|---|---|
| int32 | a·s at \|x\| = 12000 is 2³¹ / 2.39. b·x ≤ 964·12000 = 1.16e7 [E] |
| b_max | 2301; b / b_max = 0.42 [E] |
| clamps | P clamp 15360 binds only near idx ≥ 179–236, where the trim is one-sided as on V294, now ×1.7 larger (max tap on r71b was 1464 = 60 % rail). The sum clamp and the lane clamp are unchanged [E] |
| zero-command torque | Trim cap C·Kp/256 = 3840 S = **616 T (25 % rail), unchanged**. It is now reached at 1/1.7 the acceleration: ~1726 deg/s² below the pole, ~136 deg/s above it. On r71b that means 0.003 % of ticks [E] |
| restart pulse | After a filter bail, peak 24 / 73 / 246 / 542 T at 10 / 30 / 100 / 300 deg/s (V294 14 / 43 / 144 / 419). Above 50 T for 0 / 89 / 206 / 293 ms. Bounded by 616 [E]. Bails need \|x\| > 12000 (1500 deg/s), an implausible bar, or polarity 0, which the census says never happens, so in practice they do not occur [B] |
| soft-EME | The lane alone cannot reach 5120–5325 (\|T\| ≤ rail 2461). The zero-command excursion V294's adversary B bounded (616 T) is unchanged in size, and is now reached at lower wheel acceleration. Base assist is not modelled [B] |
| reader census of 0xC63EA | **exactly one reader**: `ld.hu 0x73ea[tp]` @0x28F86. Ghidra dry-run listing this session, and an independent raw LE scan (`s11`, 4-byte and 6-byte forms, absolute LE32) with positive controls a@0x28F8A and C@0x28F96/9C/B8 found. The 6-byte control gp-0x6752 was found at 0x48E56. **Zero writers**; the cell is in flash. The value in V294 is 567 [E] |

---

## 11. Runner-ups, with numbers

All from `s2`, `s7`, `s8` and `s5`, relative to V294.

**1. a 1011 → 1014 plus b 567 → 850 (G 1.5 at 1.56 Hz), cal-only, 2 cells.**
- Same jerk-band effect as the pick: hard16 nominal ×0.87 / 0.95, `light_b` ×0.78 / 0.74.
- **Lower HF content** (mode A max ×1.31 vs ×1.45) and 2.5 Hz damping 3.04.
- The same low-speed cost (J_err lp 0–5 m/s ×1.045 / 1.117).
- int32 margin 2.08.
- Costs a second changed cell, and the E3 regressor pole must become 1.56 Hz. SEL reads it.
- Pick it instead if the orchestrator weights the HF clause more than one-cell attribution.

**2. b 1134 (G 2.0), cal-only, 1 cell.**
- hard16 ×0.82 / 0.93 nominal and ×0.69 / 0.66 prior; 1–3 Hz ×0.84–0.95.
- **FAILS my pre-registered F5-HF** (13–17 Hz ×1.65, mode A full; ×1.07 in lp).
- Low-speed J_err lp 0–5 m/s ×1.06 / 1.18. int32 margin 2.03.
- E3 +0.424, SCALE 1.94.

**3. The largest loop gain that is safe against every stress member.** G 3.0 at 2.03 Hz: shl 1 (0x29D76 imm 2→1), Kp bank 960→1920 ×28 records, b 850, C 512 to hold the 616 T cap.
- \|P/x\|20 is 6.23, **exactly rule 3's ×3 line**. Ms at delay ×1.5 is 1.46, just under F2's 1.5. Stress ζ is up.
- hard16 ×0.69 / 0.87 nominal and ×0.52 / 0.48 prior.
- At 0–5 m/s, low-speed J_err lp ×1.12 / 1.37 and 0.3–1 Hz wheel rate lp ×1.10 / 1.43 (full ×1.10 / 1.53).
- F5-HF fails.
- There is a cal-only twin, b 1701 at shl 2, int32 margin 1.35: overflow-safe by construction, but below my margin-2 rule. It reads identically (E3 +0.636).
- Licensed only by outcome (a) in §9.

**4. a 1011 → 1017, pole only (1.09 Hz), b 567, cal-only, 1 cell.**
- Low-speed neutral: J_err full nominal 0–5 ×0.95, lp ×1.03; 0.3–1 Hz ×0.98–1.04.
- HF content ×1.03.
- But the jerk effect is small (hard16 ×0.95 / 0.98 nominal, ×0.94 / 0.89 prior). It fails my lens-level ≥ 10 % bar on nominal.

---

## 12. The lever's record

The byte-read census is `s9_cell_history_out.txt`: 252 images. BUILD-LINEAGE-PART1 and PART6 were grepped as well.

**0xC63EA (b):**
- stock / V100–V288 / V293: **1560**, on the sum operand (the rate loop);
- V289: 2301 (sum), flown, ring moved to 16 Hz;
- V291 / V292: 958 with a 962 (sum); V292 flown, REVERT;
- **V294: 567 on the difference operand. FLOWN r71b.** The trim was LIVE (β +0.210, scale 0.964). The operator reported "No grinding or stuttering!" and hard medium-speed turns are still jerky.

**b 964 has never been on any image.** Class: **the same lever as V294, pushed further in the same direction** (×1.7 dose). It is not a new lever and not a re-run of a falsified one. The sum-operand history is a different loop.

**What makes a different result likely.** None: it is a dose step on a lever whose sign and liveness are EVIDENCE. The question it answers is whether the jerk band is dose-responsive, which is exactly the one thing r71b could not decide (harness §0.7).

**Other cells:**
- 0xC63E8 a, 0xC62E6 C, 0x29D76 shl, the 0xCB994 Kp bank: all unchanged from V294 in the pick.
- The shl immediate has only ever been 5 (271 images) or 2 (V294).

---

## 13. Surprises, defects, reports

1. **The binding constraint was my own HF-content clause, not stability.** Under dist full it scales linearly with G, because the trim reacts to replayed wheel motion above 8 Hz, which is not identified. Under lp it barely moves. I did not waive it; the orchestrator may re-decide it.
2. **More trim de-damps the low-speed wheel mode** (§5). It is the redo audit's quasi-static warning, now quantified in closed loop with the real fork. It is the lens's real cost.
3. **The first 6-byte predicate in my raw scan was wrong** (0x07E0 instead of opcode field 0x3C/0x3D). Its positive control at 0x48E56 caught it, it was fixed, and the scan was re-run with a scanning control. The first draft's 6-byte null was void.
4. **`s6_snap.py` was a failed probe design** (continuous slides, no stick-slip). It is kept on disk and not cited. `s6b_step.py` replaces it.
5. **Per-20 s-window SCALE is biased low** (V294 reads a 0.74 median against 0.989 pooled): the nuisance regressors are collinear in short windows. Use E3 and SEL per window, and SCALE only pooled.
6. **r71b has only six 20 s hands-off windows**, so the per-window "5–95 %" is close to min/max of six values.
7. **The harness's `M_TRACK` 0.3–1 Hz probe coherence is < 0.13.** I did not read it.

## 14. Files (all in `analysis-2020accord/studies/v295/design/trim-ratio/`)

| file | contents |
|---|---|
| `CRITERIA-trim-ratio.md` | pre-registered |
| `s0_spotcheck.py` / `_out.txt` | harness spot-check |
| `s1_plane.py` / `.json` / `_out.txt`, `s1b_detail.py` | the linear plane |
| `s2_sweep.py` / `.json` / `_out.txt`, `s2b_lowspeed.py` / `_out.txt` | mode B shortlist |
| `s3_second_methods.py` / `_out.txt` | FF identity, HF gain, K_α, poles, cap |
| `s4_attrib.py` / `_out.txt` | the wire read |
| `s5_score.py`; `s5_score_{b964,b1134,g3sh1}.json` / `_out.txt` | harness `score()` |
| `s6_snap.py` / `_out.txt` (non-informative), `s6b_step.py` / `_out.txt` | snap probes |
| `s7_hf_scan.py` / `_out.txt` | the F5-HF dose ladder |
| `s8_family.py` / `.json` / `_out.txt` | 12-member robustness |
| `s9_cell_history.py` / `_out.txt` | the cell across 252 images |
| `s10_ceiling.py` / `_out.txt`, **`s10_curves.json`** | before/after curves for the close-out page: trim T/ω damping and inertia 0.1–30 Hz, \|T/x\| 1–40 Hz, \|α/cmd\| on nominal and `light_b` at 8 / 17 m/s, the delivered surface, for V293 / V294 / pick |
| `s11_reader_scan.py` / `_out.txt` | controlled raw reader scan |
