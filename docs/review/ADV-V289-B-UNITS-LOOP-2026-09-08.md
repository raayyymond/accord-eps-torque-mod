# ADVERSARY B — V289 rev 1 — UNITS / LOOP / GATE 2 — 2026-09-08

Subagent `advB`. Everything below is re-derived from the **built image** (sha256 `f0c10c29…39a3ed`, verified) and from the
**wire** (r39, r5e_v288 caches), never from the build script's constants or the design's tables. Scripts:
`rlog-tools/studies/grind/adv_v289_b_cave.py` (an independent V850E2 decoder + register-level interpreter that EXECUTES
the cave bytes), `adv_v289_b_loop.py` (L(z) from the bytes on the four plant fits; byte-exact 1 kHz closed-loop mirror),
`adv_v289_b_wire.py` (the V289 chain on the logged setpoints). Outputs in `_scratch/adv_v289_b_{loop,wire,extra}.txt`.
Criteria: `docs/review/ADVERSARIAL-V289-PREREG-2026-09-08.md` §B.

## VERDICT: **FAIL against §B3 as pre-registered** (B1, B2, B4 PASS)

| criterion | pre-registered FAIL | measured (method) | result |
|---|---|---|---|
| B1 fb DC | drift > 0.5 % or widths wrong | 30.8911 → 30.8859 = **−0.017 %**; 0xC63EA loaded `ld.hu` (unsigned), 0xC63E8 `ld.h` (signed), decoded from the bytes at 0x28F86/0x28F8A; 875/2301 fit; r26 clamp 0xC62E6 = 46080 in both images | PASS |
| B2 \|L\| < 5 Hz | > 5 % | **2.03 %** max (plant-independent ratio of the return ratio) | PASS |
| B2 7 Hz gate | > 1.02 | **1.005** (as-built 1.003; notch alone 1.079 = FAIL; fb pole alone 0.925) | PASS |
| B2 phase 3.9 Hz | worse than −5° | **+0.56°** (notch −3.85°, fb pole +4.41°) | PASS |
| B3 capped-frame step | peak rate or accel < 0.95× | census plant, byte-exact mirror: **peak rate ×0.909, peak accel ×0.929**; fit (iii) ×0.903 / ×0.779; steady state ×0.99–1.00 | **FAIL** |
| B4 18–22 Hz of S | reduction < 6 dB | **−13.6 dB (r39), −13.3 dB (r5e_v288)**; at the bookmarks −11 … −17 dB | PASS |

**Why B3 fails, and what the operator is actually being told.** The design's headline for "the pair" — *capped-step peak
rate/accel ×1.00/×1.00* (§0.6, §7, §8.1) — is the score of a **different topology**: `lm_final.log`'s (f) row is *"notch **fb** Q3 +
fb pole 25 Hz"*, the notch on the feedback operand. V289 puts the notch on the **PID sum** (forward path). Reproducing the design's
own linear method on its census plant: fb-notch + fb pole → ×0.998/×1.000; **sum-notch + fb pole (the build) → ×0.890/×0.934**
(consistent with the design's own d-out row 0.92/0.93). The byte-exact mirror (integer controller, clamps, the cave executed by
the interpreter, plant ZOH-discretised) gives ×0.909/×0.929. What is lost is the ring's overshoot (18 % → 8 % on a 33-count step)
and ~7 ms of t90 (28 → 35 ms); the steady-state rate is unchanged (1.88 → 1.86 deg/s), and open-loop peak torque into the motor is
**identical** for every step size (below). Whether that is an "authority cut" is the operator's call — but §B3 was written against
the 1.00/1.00 figure, the built topology does not meet it, and the design text misattributes the figure. [EVIDENCE — scripts above]

---

## 1. The cave, decoded and executed from the image (units surface)

`adv_v289_b_cave.py` decodes 0xC4C00–0xC4C8B with its own opcode tables (Format I/II/III/V/VI/VII/IX–XII, incl. the `ld.bu`-vs-`jarl`
collision: bits 10..6 = 11110 are shared; `ld.bu` has an odd hw2, `jr/jarl` an even displacement) and runs it register by register.

- **Hook**: 0x2A174 `89 07 8c aa` = `jr 0xC4C00`; cave exit `jr 0x2A178` after replicating `ld.hu 29678[tp], r7` (tp+0x73EE = 0xC63EE = 507). **48 instructions/tick, no `jarl`.** The interpreter seeds r11, r14, r15, r16, r22, r24, r27, r29, lp with markers and asserts them unchanged on every tick — never tripped.
- **Coefficients** (the three `movea` immediates, code order): b0 = **16048** (0xC4C0E), a2 = **15712** (0xC4C26), b1 = a1 = **−31842** (0xC4C3C); a0 = 2¹⁴ from the single `sari 14`. Structure = TDF-II with first-order error feedback (`andi 0x3fff` on the remainder word), the removed component n = x − y formed at 0xC4C3A, the FLAG (b5 = n < 0, b7 = |n| ≥ |y|, both from full-precision registers) shifted `<<4` and stored as one halfword at gp−0x6C3A, the output clamp reading **tp+0x71BE = 0xC61BE** (the same cell as Honda's sum clamp) applied to r12 only (the recursion uses the linear y).
- **State**: gp−0x6C44 (s1), gp−0x6C40 (s2), gp−0x6C3C low half (e, masked), gp−0x6C3A high half (FLAG). Note: the `st.w` of e′ at 0xC4C22 writes the whole word, zeroing the FLAG half for ~30 instructions until the `st.h` at 0xC4C6E rewrites it — if the 100 Hz reader can preempt the 1 kHz task inside that window it reads 0 (residual for surfaces A/D, not a §B item).
- **Realised transfer** (from the integers): DC (b0+b1+b0)/(a0+a1+a2) = **254/254 = 1 exactly**; zero on the unit circle (b0 = b2) at **f0 = 20.036 Hz**; −3 dB band 16.98–23.64 Hz → **Q 3.007**; |H| 0.0018/0.0042/0.0132 at 20.03/20.05/20.08 Hz; 0.998 ∠−3.85° at 3.9 Hz; 0.990 ∠−7.96° at 7.3 Hz; 0.925 at 13.5 Hz; 0.928 at 30 Hz. Executed on the interpreter: constant inputs 0, ±1, ±7, ±100, ±12345, ±15360 all settle to **exactly X**; rail-then-zero decays to |y| = 136 at 100 ticks and 0 by 500; sines at 3.9/7.3 Hz reproduce the linear |H|/phase to 0.001/0.2°. Matches the docstring's claims — established here independently.
- **Same counts end to end**: r12 enters the cave as the 0xC61BE-clamped sum and leaves clamped to the same cell; the lag multiplies it by r7 = 507 (0x2A180) exactly as V282 did; after the lag `sari 5`, then `mul r14(ramp), r9 ; sar 15 ; sxh` (0x2A1E6) — max |(s+s′)>>5| = 15209 fits the `sxh`, so **no implicit rescale**. The ramp is Q15 = 1.0 engaged (tracer Q0, relayed).
- **Tick**: every frequency above assumes 1 kHz. The record's evidence for that is the 100.00 ms CAN dwell of the 0xC64DF debounce only (trace Q6); a 10 % tick error would move the notch 2 Hz. [BELIEF-grade as an absolute; EVIDENCE that nothing in this build depends on it differently from the fb/lag poles it already carries]

## 2. B1 — the feedback filter

| | a (0xC63E8, `ld.h`) | b (0xC63EA, `ld.hu`) | DC 2b/(1024−a) | pole | steady \|s\| at \|x\| = 12000 | a·s, b·x vs 2³¹ |
|---|---|---|---|---|---|---|
| V282 | 923 | 1560 | 30.8911 | 16.53 Hz | 185,347 | 1.7e8, 1.9e7 |
| V289 | 875 | 2301 | 30.8859 | 25.03 Hz | 185,315 | 1.6e8, 2.8e7 |

Exact-integer runs (two-sample sum, `sar` floors) at x = ±100/±1000/±12000 give fb within 0.1–0.7 % of the float DC for both builds
(the sub-1 % asymmetry is the `sar` floor, present in V282 too). E's bound is unchanged: r26 is clamped to ±46080 by 0xC62E6 in
both images. Other cells checked unchanged: 0xC6446/48/4A (r24 lane 5244/1024/1024), 0xC63EC/EE 992/507, 0xC61B4/B6/BC/BE,
0xC6CD0 = 5346, 0xC63E6 = 0. **PASS.**

## 3. B2 — GATE 2 rebuilt from the bytes

Return ratio R = F·C·(254/256)·N·Hlag·(5346/2¹⁵)·z⁻¹ (T counts per raw rate count), L = R·8·G_d, negative feedback.

**Plant-independent** (ratios of R): |L| below 5 Hz +2.0 % max (fb pole +2.4 %, notch −0.4 %); 3.9 Hz +0.56°; 13/14/15/16/17 Hz
|L| ×1.06/1.04/1.01/0.95/0.84 with −10/−13/−18/−25/−34° of phase; **25–50 Hz |L| ×1.03–1.41**; rms rate→D gain 30–500 Hz **×1.49**.

**7 Hz gate** |Ls·R73 + Lr| with the record's split (Ls 0.55∠96°, Lr 1.19∠−27°): notch |H| 0.990 ∠−7.96°, fb pole ∠−23.85° →
−16.30° (**+7.56°**, |·| ×1.049) ⇒ R73 = 1.039 ∠−0.41° ⇒ **gate 1.005** (as-built 1.003); at |L_tot| 0.944/0.976/0.990 →
0.946/0.978/0.992. Sweeping the split (|Ls| ×0.5–1.5, angle ±30°) the V289 gate stays within **±0.012 of as-built** everywhere —
the pair is neutral at 7 Hz irrespective of the split. Notch alone: 1.079 (FAIL, as the design said). **PASS.**

**On the four plant fits** (`loopshape20_plants.json`; ζ from the |S| half-power width, "TD" from the band-passed impulse response):

| plant | loop | Nyquist | Ms | min\|1+L\| @ f | ζ (S-peak / TD) | \|L\| 13–17 Hz | ref→rate peak |
|---|---|---|---|---|---|---|---|
| **weak-mode (census fit iv)** | V282 | stable | 3.77 | 0.265 @ 21.5 | 0.018 / 0.015 | 0.38–0.40 | 0.152 @ 21.6 |
| | **V289** | stable | **2.05** | **0.487 @ 22.5** | **0.023 / 0.020** | 0.32–0.42 | 0.047 @ 22.4 |
| | notch only | stable | 1.73 | 0.578 @ 22.3 | 0.032 / 0.023 | 0.27–0.37 | 0.040 |
| | fb pole only | stable | 36.0 | 0.028 @ 21.7 | 0.002 / 0.001 | 0.44–0.46 | — |
| smooth+mode (fit iii) | V282 | stable | 3.12 | 0.321 @ 21.5 | 0.026 / 0.022 | 0.23–0.28 | 0.120 @ 21.6 |
| | **V289** | stable | 2.67 | 0.374 @ 22.7 | **0.018 / 0.016** | 0.23–0.25 | 0.073 @ 22.7 |
| | notch only | stable | 1.97 | 0.507 @ 22.6 | 0.028 / 0.022 | 0.19–0.22 | 0.054 |
| resonant (fit ii) | V282 | **UNSTABLE** | — | — | — | — | — |
| smooth (census-REJECTED) | V282 | stable | 12.5 | 0.080 @ 19.9 | 0.034 / 0.034 | 1.1–1.5 | 0.59 @ 19.9 |
| | **V289** | **UNSTABLE** | (12.1 @ 16.3) | 0.083 @ 16.3 | — | 0.9–1.5 | 0.50 @ **16.3** |
| | notch only | **UNSTABLE** | (19.0 @ 15.4) | 0.053 @ 15.4 | — | — | 0.88 @ **15.4** |

Byte-exact closed-loop step ring on the census plant (the mirror, 33-count step, band 12–30 Hz): V282 f 21.5 Hz, ζ **0.0155**
(e-fold 479 ms) → V289 f 21.7 Hz, ζ **0.0379** (e-fold 193 ms) — a 2.4× faster decay, in the direction the design predicts.

Readings, EVIDENCE for the arithmetic, the plants' validity being the design's BELIEF:
1. **On the census plant V289 does what it claims**: Ms 3.8 → 2.1, vector margin 0.27 → 0.49, decay 1.3–2.4× faster, and the critical
   point moves **UP to 22.5 Hz** (the mode's upper skirt), not down to 13–17 Hz — |L| there stays 0.3–0.4. No relocation to 14–17 Hz.
2. **Not robust across the design's own mode fits**: on fit (iii) the pair's ζ falls 0.022 → 0.016 (the design's own `lm_final.log`
   line 208 shows the same, 0.021 → 0.015) while the notch alone holds 0.022. The fb pole's +41 % gain at 25–50 Hz is what costs
   damping there. The design's "robust across the three mode-plant fits" (§0.6) is not supported by its own log for fit (iii).
   ⇒ **The pre-registered revert signature (a new line at 14–17 Hz) is one-sided; a new or louder line at 22–24 Hz is the other
   failure mode and should be pre-registered too** (the 26–33 / 2–6 guard sits above it).
3. **Fit (ii) is not a witness**: on the current `plants.json` resonant fit even as-built V282 is Nyquist-unstable, i.e. that fit is
   falsified by the car; the design's bracketed "(ii)" numbers come from an earlier fit.
4. **If the census was wrong (smooth plant): V289 is linearly UNSTABLE.** Byte-exact mirror, 33-count step, last second: V282 rate
   p-p 0.2 deg/s at 20 Hz; **V289 p-p 89 deg/s at 16.0 Hz, T p-p 1184, S railing 14 % of ticks** — a clamp/friction-limited limit
   cycle at 16 Hz, larger than anything V282 rings at (notch alone: 97 deg/s p-p at 15 Hz). On that plant the design's 5a rows
   (GM 0.94–0.95) said "relocates, sharper"; the byte-exact answer is a bounded 15–16 Hz oscillation. The operator would feel a
   grind at a LOWER pitch than today, sustained rather than decaying. That is the sentence the 14–17 Hz revert condition licenses.

## 4. B3 — authority, byte-exact

Closed-loop mirror (integer controller with the D/P/sum/T clamps, the cave via the interpreter, plant ZOH at 1 kHz, integer-tick
delay), steps from rest at tick 5:

| plant | step | peak rate V282 → V289 | peak accel | steady state | peak \|T\| |
|---|---|---|---|---|---|
| weak-mode (census) | 33 (capped frame, E 1056) | 2.22 → 2.02 deg/s (**×0.909**) | 122 → 113 (**×0.929**) | 1.88 → 1.86 | 99 → 99 |
| weak-mode | 1032 (full scale) | 50.3 → 49.5 (×0.985) | 1081 → 870 (×0.805) | 49.2 → 49.2 | 2465 → 2463 |
| smooth+mode | 33 | 1.53 → 1.39 (×0.903) | 78 → 61 (×0.779) | 1.20 → 1.19 | 124 → 124 |
| smooth+mode | 1032 | 26.2 → 25.2 (×0.963) | 842 → 662 (×0.786) | 24.6 → 24.6 | 2465 → 2464 |

(The smooth and resonant rows are meaningless — one or both loops are unstable there.) Reconciliation: the design's method
(linear, no clamps) on the same plant gives the built topology ×0.890/×0.934 and the fb-notch topology ×0.998/×1.000; opening the
clamps ×100 in the mirror gives ×0.866/×0.832 — so the D clamp (which binds on this step: |dE·Kd>>3| = 16896 vs 10240) actually
softens the difference. **The loss is the ring's overshoot** (18 % → 8 %) and ~7 ms of t90; steady state and full-scale peak rate
are within 1.5 %; peak accel on full scale is −20 % because the 1-tick D kick's 20 Hz content is what the notch removes.

**Open loop (rate held 0), torque into the motor** — identical peaks for every step: sp 33 → 163/163, 100 → 496/496, 300 →
1490/1490, 1032 → 2461/2461 (the peak is set by the D kick through the lag, which the notch smooths but does not raise). The notch's
×1.155 overshoot appears only on a *sustained* S step: S = 10000 → y peaks 11549 at tick 36, back within 1 % by tick 166, but
**T peak 1615 → 1615**; S = 13000 → y 15013, T 2099 → 2100; S = 15360 → y clamped at 15360 (linear 17741), T 2481 → 2481. The 5 Hz
output lag absorbs the ~30 ms overshoot. **No EME/governor ceiling sees anything V282 could not deliver**: y ≤ 15360 always (the
output clamp binds on 0.02–0.04 % of engaged ticks on the wire), T cap 3072 and gain 5346 unchanged. On the wire the clamp is
inert: 2–4 ticks per 10 s.

## 5. B4 — on the wire (open loop on the measured rate, whole engaged route, mirror validated tick-for-tick against the interpreter on 20,000 ticks)

| | r39 (880 s engaged) | r5e_v288 (642 s) |
|---|---|---|
| 18–22 Hz rms of S: V282 / V289 pre-notch / post-notch | 796 / 908 / **190** | 895 / 1018 / **220** |
| reduction post/pre (post vs V282) | **−13.6 dB** (−12.4) | **−13.3 dB** (−12.2) |
| residual 17 Hz / 23 Hz (post/pre) | ×0.70 (−3.1 dB) / ×0.65 (−3.8 dB) | ×0.71 / ×0.65 |
| 13–17 Hz / 25–33 Hz (post vs V282) | ×0.96 / **×1.14** (fb pole +1.1 dB) | ×0.93 / ×1.14 |
| 2–6 Hz / 6–10 Hz (post vs V282) | ×0.98 / ×1.03 | ×0.93 / ×1.02 |
| T after lag/gain/cap, 18–22 Hz | 31.4 → 7.5 (×0.24) | 35.4 → 8.8 (×0.25) |
| pooled PSD ratio post/pre at 15/17/18/19/20/21/22/23/25 Hz (dB) | −1.2/−3.2/−5.6/−10.7/−29.2/−11.5/−6.3/−4.0/−2.0 | same to 0.1 dB |
| removed component n: rms, p50/p90/p99, share of rms S | 737, 234/1046/2920, 29 % | 796, 190/1080/3063, 31 % |
| at the bookmarks, S 18–22 Hz post/pre | 689.7 s −15.9 dB; 927.7 s −13.3 dB | 129.4 s −11.0; 331.6 s −16.7; 820.1 s −11.9 dB |
| D-clamp / sum-clamp bind duty V282 → V289 | 0.0063 → 0.0063 / 0.0007 → 0.0008 | 0.0095 → 0.0099 / 0.0011 → 0.0012 |
| rms D (fb pole's HF rise) | 1451 → 1543 (+6 %) | 1531 → 1617 (+6 %) |

**PASS.** The notch is not inert on the wire; 20–30 % of the rms of S is in-band on these routes.

**Predicted telemetry duties, so the first drive can be read** [EVIDENCE — the FLAG as the cave computes it]:
- **b4.5 = sign(n)**: **0.500 engaged on both routes** (0.003–0.008 disengaged, where n = 0). A zero-mean band component has no
  duty information; its only use is the cross-spectrum with the 0x18F rate, exactly as the design says. Duty strictly inside (0,1)
  engaged is the liveness check; 0.500 ± 0.01 is what "alive" looks like.
- **b4.7 = |n| ≥ |y|**: **0.17–0.19 at 1 kHz, 0.10–0.11 at the 100 Hz sample instants, engaged**; rises with the line (bookmark
  windows 0.12–0.37) and is 0.45 when |S| < 100 (comparator noise on a near-zero signal). 🛑 **Reading trap: b4.7 = 1.000 while
  DISENGAGED** — S = 0, y = 0, n = 0 and 0 ≥ 0 is true. Score it engaged-only or it reads as a stuck bit.

## 6. Residuals (not §B FAILs)

1. Design §0.6/§7/§8.1 "the pair ×1.00/×1.00" is the fb-notch topology's number; the built sum-notch is ×0.89–0.91 / ×0.93 on the
   census plant. The design text should be corrected before the operator is told authority is untouched.
2. Damping gain not robust on fit (iii) (pair 0.022 → 0.016; notch alone 0.022); pre-register the 22–24 Hz line as a second
   revert signature alongside 14–17 Hz.
3. `plants.json` resonant fit makes as-built V282 unstable — drop it from any future GATE 2 table.
4. FLAG halfword is transiently 0 for ~30 instructions per tick (preemption question for surface D).
5. b4.7 reads 1 when idle; b4.5 duty is 0.5 by construction.

## 7. Recommendation to `main`

B1, B2, B4 pass with margin; B3 fails the letter of the pre-registration because the criterion was written against a number
that belongs to a different topology. **The pass returns "do not flash" as written.** If the orchestrator amends B3 to exclude
the ring's own overshoot (steady state ×1.00, open-loop peak torque identical, t90 +7 ms), the amendment must be recorded as an
amendment and the operator told in plain words: *on a capped-frame step the transient peak is ~9 % lower and arrives ~7 ms later;
full-scale steady authority is unchanged.* The conditional finding stands regardless: if the census's plant verdict is wrong,
V289 rings at 15–16 Hz and does not decay.
