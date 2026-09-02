# PRE-REGISTRATION — reading V278 rev 3's delivered-torque tap for the CLAMP question

Written **2026-09-02, BEFORE the drive.** Build: V278 rev 3 (map ×2, `0xC62E6` = 15360, CAN-427 carries
`(sign(T)<<9) | (|T|>>3)`, T = `gp-0x6b38`). Operator's question: *should the P/sum clamps be widened?*
Script: `rlog-tools/studies/osc-2to4/prereg_v278r3_saturation.py` (simulates the V276 rlog `r2e` through
the PID as decompiled, per K). **Do not move a threshold after the log lands; if one is wrong, say so.**

## 0. Three things the simulation contradicts in the build's premise — read first

1. 🛑 **The tap cannot read 313. The steady-state ceiling is |T| = 2481, tap reading 310.** EVIDENCE (cells +
   decompile): sum clamp 15360 → output lag `s_n = (992 s_o + 507 sum)>>10`, readout `(s_o+s_n)>>5` = 0.990 ×
   → 15208 → ×5346>>15 = 2481 < the 3072 cap. First-order lag, no overshoot. The brief's "P(|T| ≥ 2496)" is
   **structurally zero**. Saturation is re-defined here as **|T| ≥ 2472 (reading ≥ 309)**, one LSB under the ceiling.
2. 🛑 **The "narrow linear region" is 32× wider than stated.** EVIDENCE (decompile of `FUN_00028ea6`, line
   `iVar26 = iVar31 * Kp; >> 8`, `sar 0x8`): `P = (E·Kp)>>8` with `E = 32·sp − fb` — the 32 is *inside* E, there is
   no second 32. P rails at |E| = 15360·256/Kp = **15855 operand = 64 deg/s at Kp 248 (idx 0), 5650 = 22.9 deg/s
   at Kp 696 (idx ≥ 136)**, not 440 = 1.8 deg/s. Kp is indexed by the DEMAND index (`uVar33`, same as the map).
   On the V276 log, |E| < 440 holds on 4 % of oscillating ticks; |E| < the true rail holds on 96 % (K=2).
3. ⭐ **At K=2 the clamps essentially never bind on T.** P railed 3.5 % of oscillating ticks / 7.9 % normal; sum
   railed 7.5 % / 3.2 %; **T saturated 0.0 % / 0.4 %** — the 5 Hz output lag averages the brief rails away.
   ⇒ **The pre-registered prediction for the clamp question is a NULL: "leave clamps".** The drive can still
   refute it (§3) — that is why it is written down.

Also: `dose_e_sign_by_k.py` hard-codes LIMIT 15360; slot 7's is 16384. Effect: the demand index tops out at 237
instead of 240 for |cmd| ≥ 3840 — no frame on this log gets there (cmd p90 ≈ 1300). No number here changes.

## 1. Predicted duties, from the V276 log through the K-scaled chain  (EVIDENCE = simulation; chain = BELIEF where marked)

Osc = the 7 oscillation episodes (14.5 s); Normal = engaged, not oscillating (58.8 s). Duties are fractions of ticks.

| K | sat |T|≥2472 osc / norm | P railed osc / norm | sum railed osc / norm | D railed | \|E\|<440 osc / norm | \|E\| in true band osc / norm | damp_E osc | **damp_T osc / norm** |
|---|---|---|---|---|---|---|---|---|---|
| 1 (stock) | 0.000 / 0.002 | 0.000 / 0.023 | 0.004 / 0.008 | 0.001 | 0.040 / 0.299 | 1.000 / 0.977 | 0.937 | 0.758 / 0.682 |
| 1.5 | 0.000 / 0.003 | 0.000 / 0.050 | 0.024 / 0.019 | 0.002 | 0.042 / 0.279 | 1.000 / 0.950 | 0.902 | 0.717 / 0.643 |
| **2 (rev 3)** | **0.000 / 0.004** | 0.035 / 0.079 | 0.075 / 0.032 | 0.008 | 0.038 / 0.267 | 0.965 / 0.921 | 0.863 | **0.678 / 0.600** |
| 3 | 0.000 / 0.008 | 0.006 / 0.128 | 0.034 / 0.046 | 0.012 | 0.034 / 0.235 | 0.994 / 0.872 | 0.786 | 0.606 / 0.526 |
| 6 (V276) | 0.000 / 0.012 | 0.045 / 0.147 | 0.056 / 0.065 | 0.030 | 0.029 / 0.144 | 0.955 / 0.853 | 0.576 | **0.368 / 0.401** |

- `damp_E` = rev 2's comparator `sign(E) != sign(fb)` (0.86 at K=2 as in the lineage — reproduced).
- `damp_T` = **what rev 3's tap actually reads**: `sign(T) != sign(0x18F rate)` on frames with both nonzero
  (T = −lane; the lane opposes the wheel ⇔ sign(T) = sign(fb) = −sign(wire)). It is LOWER than damp_E because
  T lags E through the 5.05 Hz output lag (≈38° at 3.9 Hz). **Use the damp_T column, not 0.86, to score the drive.**
- Per-episode spread at K=2: damp_T 0.65–0.72 (sd 0.03), sat 0.00 in every episode; at K=6: damp_T 0.24–0.45 (sd 0.06).
- |T| in the oscillation, K=2: p50 798, p90 1550 — a third of the ceiling. Nothing in the episodes is near the rail.
- BELIEF in the chain: the post-sum multiplier (`0xCBB54/0xCBC34 × 0xCBAE4/0xCBBC4`, product>>8, applied BEFORE
  the sum clamp) is taken as 254/256 (all knots 255). If those tapers bite at speed, the sum rails *less* (at
  205/256: 0.5 %; at 164/256: 0.0 %) and damp_T does not move (0.677). The ramp `uVar18` is taken as 0x8000 once
  engaged. The zero-crossing gate before `LAB_0002a1ee` is dead: its enable byte `0xC74A3` = 0 (EVIDENCE, image).

## 2. The widening arithmetic, from the cells  (EVIDENCE: cells and read-site bytes)

`0xC61BC` (P clamp) and `0xC61BE` (sum clamp) → W. Delivered ceiling = `lag(W)·0xC6CD0>>15` until `0xC61B4` = 3072
binds: **W·5346>>15 ≥ 3072 ⇒ W ≥ 18830** (with the 0.990 lag readout, W ≥ 19017). To hold today's ceiling,
G = 0xC6CD0 = round(2505·32768/W):

| W | G = `0xC6CD0` | ceiling with G | ceiling if G left 5346 | P-rail \|E\| at Kp 248 | at Kp 696 |
|---|---|---|---|---|---|
| 15360 (now) | 5346 | 2481 | 2481 | 15855 op = 64 deg/s | 5650 = 22.9 deg/s |
| 18432 | 4453 | 2480 | 2977 | 19027 = 77 deg/s | 6780 = 27.4 |
| 20480 | 4008 | 2480 | 3072 (cap) | 21141 = 86 deg/s | 7533 = 30.5 |
| 24576 | 3340 | 2480 | 3072 (cap) | 25369 = 103 deg/s | 9039 = 36.6 |
| 30720 | 2672 | 2480 | 3072 (cap) | 31711 = 128 deg/s | 11299 = 45.7 |

deg/s = operand / 30.89 / 8. **All three cells are tp-relative cals — a cal-only change, outside the bricking class.**
Sign-extended reads (byte 0x25 = `ld.h`): `0xC61BE` @`0x2A146`, `0xC61B4` @`0x2A20C`, **and `0xC6CD0` @`0x2A1EE`**
(decompile: `*(short *)(tp+0x7cd0)`) — all three must stay < 32768; every W above is, and G only goes DOWN.
`0xC61BC`'s read widths were NOT checked here (BELIEF: `ld.hu`); keep W < 32768 regardless.
⚠ The D clamp `0xC61B6` = 10240 and I anti-windup `0xC61BA` are not in W; D rails on < 1 % of ticks and is left alone.

## 3. THE DECISION RULE — apply to the drive's 427 tap (engaged, in-taper, ramped frames)

Measure: **SAT** = P(|T| ≥ 2472) i.e. tap reading ≥ 309; **DAMP** = P(sign(T) ≠ sign(0x18F rate)), both nonzero.
Score over oscillating frames if the car oscillates (same episode detector), else over all engaged frames.

| | prediction K=2 | "high" | "low" | K=6 reference (V276 on the same instrument) |
|---|---|---|---|---|
| SAT, osc / normal | 0.000 / 0.004 | **≥ 0.05** | **< 0.02** | 0.000 / 0.012 |
| DAMP, osc / normal | 0.68 / 0.60 (episode sd 0.03) | **≥ 0.60 osc, ≥ 0.55 normal** | **≤ 0.50** | 0.37 / 0.40 |

| DAMP | SAT | verdict | note |
|---|---|---|---|
| high | high | **widen clamps** (W = 20480, G = 4008 keeps the ceiling) | NOT predicted. If seen, the chain model is wrong somewhere upstream of T (multiplier/ramp) — re-derive before cutting |
| high | low | **leave clamps; K=2 stands** | ⭐ THE PREDICTED CELL. The clamp question is closed by the null |
| low | low | **K = 1.5** (predicted DAMP 0.72 / 0.64) | the reference is still too high for the combined loop; clamps irrelevant |
| low | high | **clamps, not K** | the loop is railing AND not damping — the rail itself is what removes the damping |

Between "high" and "low" (SAT 0.02–0.05, DAMP 0.50–0.60): **undecided — report, do not act**; the tolerance is the
episode spread (DAMP sd 0.03) and the normal/osc difference (0.08). A 3.9 Hz symptom with DAMP ≥ 0.60 and
SAT < 0.02 is a symptom that neither lever addresses — that is the "clamps not K, and not this K either" outcome.

**What "do not act on the clamps" looks like, written now:** SAT < 0.02 in every regime — the prediction.
**What refutes this pre-registration:** a tap reading of 313 at any time (the ceiling arithmetic is wrong), or DAMP
on normal frames outside 0.50–0.70 while the car does not oscillate (the T-vs-wire phase model is wrong).
