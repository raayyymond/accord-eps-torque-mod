# JUDGE — goal and operator notes (V299 judge panel, 2026-10-02)

**Role.** I am a JUDGE SUBAGENT, and my lens is the operator's goal and his four V298 notes. I read all five design pages
(`docs/specs/design/v299/DESIGN-V299-D1…D5`) and all three scorer reports (`scores/S1-frequency.md`,
`S2-time-nonlinear.md`, `S3-bytes-interlocks-fork.md`) in full. I also read, for grounding:
- the drive read §2–§5 (`docs/scoring/DRIVE-READ-V298-r79-2026-10-02.md`);
- the two refutations (`v298_flight/reports/REFUTE-synthesis-{data,inference}.md`);
- the `firmware-iteration` and `openpilot-iteration` skills.

**Status.** Nothing was built, flashed, sent or committed. I did not touch the fork, the firmware, the golden model, STATE
or the lineage. Ghidra was read-only (`disassemble_bytes dry_run` on `ADVIG_V298_177abf04.bin`). Two scripts are new,
both under `judges/` and both read-only; their wall times are in §7.

**Labels.** EVIDENCE = image bytes, route-79 (r79) caches, or an executed common scorer, with the method named.
BELIEF = a model or an inference. I score bands; **the operator scores the symptoms.** Nothing here is "fixed".

**Classifier interruptions:** 0.

---

## 0. Verdict on one page

**The lens.** For each candidate I asked:
- Does it move the mechanism behind each operator note, with a measured or scored number?
- Does it keep note 1 ("small-angle steering at all speeds seemed robust") intact?
- Does it respect the standing rules?
  - the driver can always override at the Honda-recognised hand level;
  - minimal firmware;
  - gate, don't delete;
  - one short drive can interpret the build.

**Headline (EVIDENCE from the scorers, unless marked).**
1. **No candidate, as designed, covers all four notes without a hand-safety cost.** Two came closest:
   - **D5b** covers all four on paper, but its firmware is byte-identical to D1a. On the N1 release lens D1a fails D1's test
     (15.9° against V298's 4.7°) and S2's (worst 18.6° against 13.9°, outward median 10.2° against 7.0°).
   - **D3a** delivers the most authority, but it has the weakest override:
     - the fork yields 370–400 ms after a 1500-word hand;
     - the lane reaches 75 % of the rail under the hand;
     - holding needs +21 % hand force;
     - the indicator is not fixed.
2. **D1c is the best base under this lens.**
   - It is the only candidate that removes the measured note-4 mechanism (the bar-keyed integrator-freeze relay) **and**
     improves N1 (worst release lurch 11.2° against 13.9°).
   - Its small-signal loop is byte-identical to V298's, so note 1 is unchanged.
   - It fixes note 3 with the **correct** bar sign.
   - It is the firmware half that every fork graft in S2 needed: under the D3, D5 and D2b forks it cuts N1 to 9.1–9.8°.
   - **Its weakness is note 2.** Turn-in t90 falls only 21–31 % (S2), and the wheel rate is unchanged, because the fork's
     120 deg/s cap still binds. Note 2 needs a fork graft.
3. **The composite I would put in front of the operator** (BELIEF until S2 scores it as one row; §6.1):
   - **Firmware:** D1c, built **in place** (§6.2: 21 bytes, no relink; my construction, BELIEF until H1), plus `A16B`.
   - **Fork:**
     - D1's bar formula, with `nan` frequency and its own param;
     - D2's O1 gate (instant above 1200 raw; 600–1200 held 80 ms) **with the O1 lead set to 0** (S1: O1-loop GM 6.0 → 9.4 dB);
     - a low-speed cap and clip raise (D3's K1 schedule or D2a's numbers), with D2's takeover ramp;
     - **no** post-clip lead.

**Ranking (all 13 implementations, my lens):**

| rank | candidate | one-line reason | status |
|---|---|---|---|
| 1 | **D1c** (D1 rec.) | Removes the freeze relay (r79 replay: 325 → 13 toggles/min). Best N1. Note 1 byte-identical. Note 2 weak alone. | **eligible: the winning base** |
| 2 | D1 fork bar | The only bar formula with today's sign (S3 0.942; my second method 0.854, corr +0.82). Pinned 59.7 % → 0 %. | eligible component (carry with rank 1) |
| 3 | D3-a (D3 rec.) | Most note-2 authority (t90 0.41/0.51 s, wheel 219/174 deg/s, tap 71 % of rail). Lowest 4–8 Hz in S2. But the weakest override, post-clip lead below the GM bar, no bar, N1 15.4°. | eligible with must-fixes |
| 4 | D2a (D2 rec.) | Zero firmware. Fork authority (t90 1.06/0.92 s). O1 lead 0 is the only change that adds O1-loop margin. Bar sign inverted (fixable). **Misses the freeze relay**, so integration kept falls to 0.46. | eligible with must-fix |
| 5 | D2b | As D2a, plus the best fork-only small-correction tracking. Largest fork diff; 1.6–3 Hz ×2.7. | eligible with must-fix |
| 6 | D4b (D4 rec.) | Halves the relay (79/min; sim 6 toggles/s). The best-designed instrument (b4.7 = sign(h)). The most firmware (222 B, +1 RAM word). N1 16.5°. Notes 2 and 3 barely moved. | eligible |
| 7 | D1-a2 G0-1400 | A separate later dose. S2 cannot tell it from D1c; S1 flags it (5 Hz edge). | eligible later |
| 8 | D4b+GBS13 | D4b's relay fix, plus a table that **fails the panel R2 box** (23 points, 25.1°) at exactly the 10–17.5 m/s regime note 1 praises | conditional on the ms_free ruling |
| 9 | D4a | Same R2-box fail. The freeze relay is untouched. Small-correction gain at 15 m/s 0.29 → 0.44. | conditional on the same ruling |
| 10 | D5 V299-b (D5 rec.) | Best note coverage on paper, but the firmware is D1a. N1 fails, the bar is inverted, and its 4–8 Hz wheel rate is the highest of all rows (14.4 / 12.0 deg/s against 8.5 / 9.1). | **DISQUALIFIED as designed**; the fork half survives |
| 11 | D1a | N1 release lurch 15.9° (D1) / 23.7° (S2). Its designer says not for flight. | DISQUALIFIED |
| 12 | D3-b | Soft-EME band 5120–~5900 not replayed. Dominated by D3a: the rail is reached on 0 ms. | DISQUALIFIED |
| 13 | D5 V299-a | GATE 2: the O1 loop has 1.5 dB at Trt 90 ms, with 17 sub-bar points on the R79 frames. Worst N1 (26.3°) and worst overshoot (9.9°). | DISQUALIFIED |

---

## 1. What each note asks, and the mechanism the record assigns it

These mechanisms are as corrected by the two refutations, which overrule the synthesis's own ranking.

| note (operator's words) | mechanism, strength (source) | what a candidate must move |
|---|---|---|
| 1 "small-angle steering at all speeds seemed robust" | The stable, damped loop. The I carries 91 % of hold torque, with no ring. **Caveat:** small corrections under-track (slope 0.64–0.82 at 12–25 m/s; 0.1 Hz lag 1188 ms). EVIDENCE, drive read §2. | **Keep it.** Leave the small-signal loop alone, or prove GATE 2 and the C2/hold cells unchanged. |
| 2 "high-angle / high-jerk / high-authority / high-torque … did not feel like 6×" | **(i)** The hard manoeuvres were **hand-steered**: always-on lateral, steeringPressed 53 %, blinker 57 %. O1, the ×0.30 fade and the freeze yield by design, strong (REFUTE-inference 2a). **(ii)** The O1 relay as one mechanism: a twist trip, a snap to the wheel, then a re-slew at the cap (73 % of cap binding), strong (REFUTE-data). **(iii)** Low-speed stiffness × the error the fork allows: D braking on unwinds, effective I 0.34–0.42× design, strong. **(iv)** The 120 deg/s cap on planner demand alone, weak. **The rail is ruled out:** peak 59 %. | Raise the hands-off wheel rate / t90 and the tap peak, with a predicted number against today's 183 / p99 135 LSB (C1). **Say honestly that a hand-steered turn will still yield.** |
| 3 "torque/demand indicator did not match the wheel" | The bar = (a_des − roll) / 0.3247. a_act cancels. Pinned 59.7 %, \|corr\| 0.135. Strong. | A bar driven by the delivered torque, keeping today's drawing direction. |
| 4 "stuttery / ratchety … instead of smooth, strongly and confidently controlled" | **(i)** The bar-keyed integrator freeze (300 opposing / 512 hard) firing on the reaction twist. Stall-surges 80.7 near vs 30.3 away /min at 5–10 m/s; no enrichment on V282/V294. Moderate-to-strong (REFUTE-inference §3). **(ii)** The small-correction stick (dwells 4.70/1.16/4.47/3.53 /min), moderate. **(iii)** 4–8 Hz modulation near O1 (6.99 vs 3.06 deg/s), cause undecided. | Remove the freeze relay without reopening N1. Do not raise 4–8 Hz. Reduce the stick if possible. |

**Binding constraints scored beside the notes:**
- **Hand override:** physical override at the Honda-recognised hand; the firmware fade is unchanged in every candidate.
- **N1 release lurch:** S2's LH lens and D1's `rb_n1` lens.
- **Firmware minimality:** bytes, caves, RAM (S3).
- **Toggle-config expressibility:** S3 §4.3.

---

## 2. The scoring matrix (numbers copied from the scorers; source per column)

### 2.1 Note 1: is the small-angle loop kept?

S2 C2 cells are the 2° correction at 15 / 25 m/s.

| cand | inner loop (S1) | GATE 2, R2 box (S1) | fork-loop margin (S1, Trt 60 / 90 ms) | C2 fast g@0.5 s | C2 slow e_rms (°) | note-1 verdict |
|---|---|---|---|---|---|---|
| V298 | — | 0 fails, worst 39.1° | O1 6.0 / 3.2 dB; clip 9.6 / 8.3 dB | 0.29 / 0.69 | 0.99 / 0.60 | baseline |
| D1c / D1a | = V298 (bytes) | = V298 | = V298 (I runs under O1: DC drift \|S\| 17, the declared droop) | 0.33 / 0.75 | 0.95 / 0.54 | **kept** |
| D2a | = V298 | = V298 | **O1 9.4 / 8.3 dB** (lead 0); path PM 64.3° | 0.35 / 0.73 | 0.92 / 0.51 | kept (SteerDelay over-leads at ≤ 5 m/s by ≤ 0.16 s, BELIEF) |
| D2b | = V298 | = V298 | as D2a; path PM 76.1°; 20 Hz not assessable (S1 †) | **0.47** / 0.73 | **0.76 / 0.44** | kept, and the "not crisp" caveat improves (sim; S2 cannot see the stick) |
| D3a | own table ≤ 8 m/s | 0 fails, worst 37.3°; low-speed −9.6°; +2 R79 sub-bar | **clip loop + K3: 6.4 / 4.5 dB, below the 6 dB bar at 90 ms** | 0.38 / 0.77 | 0.91 / 0.51 | kept at ≥ 10 m/s; margin halved ≤ 3 m/s |
| D4b | = V298 | = V298 | = V298 | 0.32 / 0.71 | 0.98 / 0.58 | kept |
| D4a / +GBS13 | GB-S13 | **23 fails, worst 25.1° (10–17.5 m/s)**; curve-hold ζ 0.040 → 0.010 | = V298 | 0.44 / 0.70 | 0.84 / 0.58 | **at risk exactly where note 1 praised the car.** S1 §2.9: the model under-states the real loop gain above 15 m/s (BELIEF) |
| D5b | = V298 | = V298 | O1 = V298 (lead 0.06 kept); path PM 61.3° | 0.38 / 0.77 | 0.91 / 0.51 | kept |
| D5a | own | worst 30.4° (+0.4); 17 R79 sub-bar | O1 1.5 dB at 90 ms | 0.40 / 0.79 | 0.89 / 0.49 | **broken** |

### 2.2 Note 2: hands-off authority

S2 columns are the 60° turn-in at 3 / 8 m/s on member r79F, median of seeds; worst in brackets.

| cand | t90 (s) | ω peak (deg/s) | tap peak, % of rail | designer's own headline (method) | honest about hand-steered turns? |
|---|---|---|---|---|---|
| V298 | 1.77 / 1.80 | 97 / 90 | 54 [62] | r79: 183 LSB = 59 %, wheel p99 140 (EVIDENCE) | — |
| D1c | 1.23 / 1.43 | 103 / 84 | 57 [67] | hard_ratio 0.60/0.64/0.73 → 0.78/0.90/1.00 (sim); open-loop tap p99 149 → 194 (r79 replay, an upper bound) | yes (M-D1-1) |
| D2a | 1.06 / 0.92 | 121 / 121 | 57 [64] | t90 0.93–1.11 → 0.54–0.65 s (own sim); X3 twist risk pre-registered | yes (§7) |
| D2b | 0.88 / 1.01 | 130 / 118 | 54 [62] | lane-change lag 515/275 → 135/135 ms (own sim) | yes |
| **D3a** | **0.41 / 0.51** | **219 / 174** | **71 [79]** | wheel 245–261 deg/s, tap 181–187 LSB (own sim); r79 open-loop tap peak 199 → 257 | partly: K2 makes a 600–1200 hand **not** yield (a feel change, declared) |
| D4b | 0.97 / 0.95 | 117 / 114 | 61 [68] | open-loop tap p99 120 → 162 | yes (M5) |
| D4a | 1.07 / 1.08 | 100 / 91 | 55 [68] | — | — |
| D5b | 0.71 / 0.89 | 167 / 127 | 65 [77] | t90 0.54–0.65 s, wheel 257–276 (own sim) | **yes, and the best framed** (§1, P4: asks the operator) |
| D5a | 0.72 / 0.74 | 158 / 167 | 71 [74] | — | — |

**No row reaches the rail** (S2 max 79 %; D3's (b) reaches it on 0 ms). EVIDENCE as computed. "6×" was never in V298's
design, and it cannot become a felt ×6 in rate or jerk (D3 §0, confirmed from bytes by S3).

### 2.3 Note 3: the indicator

| cand | bar formula | sign vs today's bar | r79 replay | parser |
|---|---|---|---|---|
| D1 | `clip(+8·s10 / 2461)` | **S3 0.942; mine 0.854, corr +0.822 (§7)** | p50 0.05 / p99 0.35 / max 0.60; pinned 0 % | `nan` (S3: the counter path can still drop canValid; the risk is low, 99.997 %) |
| D2 | eps = −8·s10; bar = +eps/2461 | **INVERTED**: S3 0.058; mine 0.146, corr −0.822 | pinned 0 % | freq 0: the same counter caveat |
| D5 | eps = −T; bar = +eps/2461 | **INVERTED** (same) | \|corr\| with \|tap\| 0.97 | **freq 50 makes 0x1AB non-optional** (must fix to `nan`) |
| D3, D4 | none | — | — | — |

**Under this lens the new bar does double duty.** It shows the delivered fraction of the 6× lane rail. So it answers note 2's
"was it 6×?" on the screen itself: r79 would have shown at most 0.60. BELIEF: the operator should be told that the bar is
the automation's effort, not Honda's base assist and not his hand.

### 2.4 Note 4: smoothness

| cand | freeze toggles, r79 replay (/min) | S2 freeze toggles (/s) 3/8 | S2 stall-surges | S2 4–8 Hz wheel rate, 3/8 (deg/s) | O1 twist trips, r79 / S2 | S2 I kept @8 | stick |
|---|---|---|---|---|---|---|---|
| V298 | 325 | 14.7 / 16.1 | 14 | 8.5 / 9.1 | 345 / 25 | 0.52 | baseline |
| **D1c** | **13** (duty 11.4 → 0.4 %) | **0 / 0** | **0** | 6.6 / 8.7 | 345 / 21 (unchanged fork) | **0.96** | unchanged |
| D1a | 13 | 0 / 0 | 0 | 6.6 / 8.6 | 345 / 21 | 1.00 | unchanged |
| D2a | 325 (relay untouched) | 9.8 / 13.5 | 4 | **5.7 / 5.8** | **30** / 4 | **0.47** | ≈ |
| D2b | 325 | 11.6 / 10.6 | 5 | 5.8 / 4.7 | 30 / 5 | 0.53 | best C2 (sim) |
| D3a | crossings 382/199 → 65/0 per min; duty 0.073 → 0.003 | 1.6 / 2.0 (hand-lost 0.41 at 3 m/s: its 1229 freeze fires on its own twist) | 0 | **4.3 / 2.9** (lowest) | **0 / 0** | 0.83 | unchanged |
| D4b | 79 | 6.1 / 5.9 | 4 | 5.8 / 6.2 | 63 / 7 | 0.82 | unchanged |
| D4a | 325 | 11.8 / 11.6 | 6 | 5.8 / 6.5 | 63 / 6 | 0.62 | −15 % stuck (sim) |
| D5b | 0 crossings (1108 → 0 /min) | 3.5 / 0.8 | 0 | **14.4 / 12.0 (highest of all rows)** | 18 / **15** | 0.96 | unchanged |
| D5a | 0 | 0.8 / 0 | 2 | 11.2 / 8.8 | 18 / 11 | 1.00 | inert Kf |

Two readings:
- **The firmware relay** (note-4 mechanism i) moves only with a firmware edit: D1c, D1a, D5b, D3a, and D4b (half).
  - EVIDENCE: the r79 replay (D1, D4, D5) and S2's integration kept.
  - D2 cannot reach it, and S2 shows the faster D2 slews **lower** integration kept (0.46 against 0.52).
- **The 4–8 Hz ratchet band is not monotone with the relay fix.**
  - D5b's fork drives it to the highest of any row, and the S2 graft shows the same under D1c firmware (14.7).
  - S2 attributes it to D5's boxcar lead (BELIEF). Mine is a second, untested candidate cause (BELIEF):
    - D5b keeps V298's 0.06 s O1 lead;
    - it has 15 instant-1200 twist trips at higher authority;
    - S1 finding 4 places the O1 loop's least-margin crossing at 5.2–5.6 Hz, with GM 6.0 dB at Trt 60 ms and 3.2 dB at 90.
  - D2 (lead 0, 2–4 trips) and D3 (0 trips) both sit **below** V298 in this band.
  - Under note 4, the fork's O1 rule therefore decides whether authority arrives smoothly.

### 2.5 Hand safety and the override rule (binding)

| cand | S2 N1 worst lurch (°) | S2 outward light hold, 5 m/s median (°) | D1's `rb_n1` out_2_511 @12.5–22 m/s (°) | fork O1 latency, 5 / 15 m/s (ms) | tap under the overriding hand (% rail) | hand force (T) |
|---|---|---|---|---|---|---|
| V298 | 13.9 | 7.0 | 4.71 | 30 / 160 | 47 | 372 |
| **D1c** | **11.2** | **4.1** | 5.05 | 30 / 160 | 48 | 366 |
| D1a | **23.7** | 10.2 | **15.90** | 30 / 160 | 48 | 366 |
| D2a / D2b | 14.9 / 14.8 | 6.8 | (V298 firmware) | 40 / 240 | 55 | 399 |
| D3a | 15.4 | 9.3 | not scored (opposing at 800) | **370 / 400** | **75** | **450 (+21 %)** |
| D4b | 16.5 | 7.5 | not scored | 70 / 210 | 56 | 403 |
| D5b | **18.6** | 10.2 | **= D1a firmware: 15.9** | 40 / 220 | 60 | 421 |
| D5a | **26.3** | 10.9 | — | 40 / 220 | 59 | 345 |

**Every candidate keeps physical override at Honda's level.**
- The firmware fade (×0.85 at 1216, ×0.30 at 2289) is unchanged in all of them.
- The I freezes at ≥ 1229, or ≥ 512 on D4b's LP word.

**D3a's "fork follows the hand only after 100 ms held above 1200"** meets the letter of the binding rule (EVIDENCE: the
fade acts at once). It has the worst feel numbers above, though. "Fights my hands" is a symptom the operator would
report. **This needs his ruling before D3's K2 flies.**

### 2.6 Firmware minimality (S3; my §6.2 for the in-place D1c)

| cand | changed bytes, pre-CRC / with CRC | cave | RAM | relink |
|---|---|---|---|---|
| D2a / D2b | 0 | — | 0 | — |
| D5b | 5 / 9 | 260 | 0 | no |
| D3a | 9 / 13 | 260 | 0 | no |
| D4a | 14 / 18 | 260 | 0 | no |
| **D1c in place (judge's construction, §6.2)** | **21 / 25 (+1 for A16B)** | **260** | **0** | **no** |
| D1c as designed | 152 / 156 | 252 | 0 | **yes** |
| D4b | 218 / 222 | 312 | **1** | yes |
| D5a | ≈ 110 | ≈ 330 | 1 | yes |

---

## 3. Per-candidate rationale (lens: goal and operator notes)

**D1c (rank 1).**
- **For it:**
  - Note 4's measured mechanism is removed, with EVIDENCE on r79's own wire: toggles 325 → 13 /min; discarded integration
    28.3 → 0.8 %; stall-surges near a toggle 22/27 → 9/27 at 0–5 m/s and 56/68 → 26/68 at 5–10 m/s.
  - S2 independently reproduces the removal: 0 toggles, 0 stall-surges, integration kept 0.96.
  - **The asymmetric A3 bound is a new mechanism for the same N1 hazard**, so the protection is replaced, not deleted.
    - S2 worst N1 is 11.2° against V298's 13.9°.
    - The unwind overshoot past centre is 0.6° against 4.2°, which the operator would feel as a cleaner return to centre.
  - Note 1 is untouched by construction: the loop is byte-identical and GATE 2 = V298 (S1).
  - Note 3 is fixed with the correct sign.
- **Against it:**
  - **Note 2 alone:** t90 1.23 / 1.43 s against 1.77 / 1.80, and ω unchanged (fork-limited).
  - The designed overshoot returns: 3.0 [5.0]°, settle 2.0 s at 8 m/s.
  - Light co-steer release droop ≤ 3.0° (V298 0.5–0.9°), declared with stop band F5.
  - The open-loop A3-stop toggling rises to 141 /min (M-D1-10). Closed loop shows 0.25 /s, but this is the relay to watch next.
  - The opposing freeze is replaced by firmware, which cannot be param-gated. Acceptable, because the N1 function is kept
    and scored.
  - Defects: A16B is left open (S3 recommends it), the bar has no own param, the parser needs `nan`.
- **Disqualifier:** none.

**D1 fork bar (rank 2, component).**
- It is the only bar formula with today's direction: S3 0.942, and my second method on a different frame set 0.854,
  corr +0.82.
- It is EVIDENCE-backed on r79: pinned 59.7 → 0 %.
- It must ship with any winner. Its own param should be `AccordAngleBarFromEps` (D5's name) so it can be reverted alone.

**D3-a (rank 3).**
- **For it:**
  - The strongest note-2 numbers in S2: t90 0.41 / 0.51 s; ω 219 / 174 deg/s, about ×2 V298's; tap 71 % of rail.
  - Its held-1200 O1 gives **0 twist trips**, and the lowest 4–8 Hz wheel rate of all rows.
  - Its design insight is right and decision-bearing: **"authority and the freeze/override thresholds must move together"**.
    S2 F3 confirms it.
- **Against it, under this lens:**
  - (a) **The weakest override:** 370–400 ms, 75 % of rail under the hand, +21 % hand force; 600–1200 hands never yield.
  - (b) **K3 is added after the clip,** so it is positive wheel-rate feedback while the clip binds. S1: GM 4.5 dB at Trt 90 ms,
    below the 6 dB bar, and the reference content at 13–22 Hz doubles.
  - (c) **No bar fix**, so note 3 is unaddressed.
  - (d) N1 worst 15.4° (> V298). Heavy-member unwind 15.4° at 3 m/s (own sim).
  - (e) **The 1229 freeze still fires on its own faster twist:** hand-lost 0.41 at 3 m/s (S2), so the relay re-arms one
    level up.
  - (f) Low-speed GATE-2 margin +15.3 → +7.3°; S1 5–30 Hz flag at the 5 Hz edge.
  - (g) K5 accepts A16B without K2: by D3's own sim the D3 firmware relays O1 on the default fork.
- **Must-fixes before eligibility:** K3 pre-clip with a boxcar, or dropped; an O1 instant path; K5 coupled to K2; the bar graft.

**D2a (rank 4).**
- **For it:**
  - Zero firmware: no GATE 1, no bricking class, toggle-expressible after one commit, param clamps specified.
  - It is the only candidate that **adds margin to a fork-coupled loop**: O1 lead 0 takes GM from 6.0 to 9.4 dB at 60 ms
    and from 3.2 to 8.3 dB at 90 ms (S1).
  - r79 twist O1 trips 347 → 30, while every hand episode is still caught no later than steeringPressed + 10 ms.
  - The best-formed override among the forks (S3).
  - The richest instrument: `co_tq` status bits, all free fields on r79.
- **Against it:**
  - **It misses note 4's measured mechanism** (declared). S2 shows the relay intact (9.8–13.5 toggles/s), and integration
    kept falls to 0.46–0.47.
  - Note-2 gain is moderate in S2: t90 1.06 / 0.92 s.
  - The bar sign is inverted (must-fix).
  - X3 (the twist crosses 1200) is a real risk in its own sim.
- It remains the best fork-only design, and its O1 gate is the graft the winner needs.

**D2b (rank 5).**
- **For it:** everything in D2a, plus the best small-correction tracking of any fork (C2 slow e_rms 0.76 / 0.44 against
  0.99 / 0.60). That speaks to the "robust but not crisp" caveat on note 1, though S2 cannot see the actual stick.
- **Against it:** the relay is untouched; 1.6–3 Hz ×2.7; the largest fork diff (~100–120 lines); the second-order limiter
  costs about 0.07 s of turn-in; too many new fork terms for one interpretable drive.

**D4b (rank 6).**
- **For it:**
  - It halves the relay with real-hand coverage intact (r79 79 /min, 0.999 pressed-frame freeze).
  - **It has the panel's best instrument design**: a sign bit paired with a comparator magnitude, which is the
    firmware-iteration design law.
- **Against it:**
  - Notes 2 and 3 barely move (t90 0.97 / 0.95; no bar).
  - N1 worst 16.5° (> V298).
  - The most firmware (222 B, cave +52 B, a new RAM word), against the minimality priority.
  - Code-constant fork terms, against the toggle preference.
  - No instant O1 path above 1200.

**D1-a2 G0-1400 (rank 7).**
- S2 cannot separate it from D1c at this resolution.
- S1 raises the 5 Hz-edge flag and a deeper O1 DC drift (\|S\| 28).
- **Correctly kept as a later, separate dose.**

**D4b+GBS13 (rank 8) and D4a (rank 9).**
- GB-S13 is the only stiffness edit that raises the small-correction gain at 15 m/s (g@0.5 0.29 → 0.44). Note 1's
  caveat wants that.
- But it **fails the panel R2 box** (23 points, 25.1°; two engines agree) and quarters the curve-hold ζ.
- Both happen at 10–17.5 m/s, the regime note 1 praised and where S1 says the model under-states the real gain.
- Under this lens, **raising highway stiffness risks the one thing the operator said works.** Conditional on the
  orchestrator's ms_free ruling; I would rule against it now.
- D4a also leaves the relay untouched.

**D5 V299-b (rank 10, DISQUALIFIED as designed).**
- **For it:**
  - The best-argued architecture: one hand detector, owned by the fork. Its "re-asked: is each V298 term still necessary?"
    table is the right practice (`openpilot-iteration`).
  - It covers all four notes nominally, with the best-framed note-2 honesty (P4).
- **Why it is disqualified:**
  - (a) Its firmware **is D1a byte for byte** (S3 §5). D1a fails N1 on D1's lens (15.9° against 4.7°). S2 then scored
    D5b on its own LH lens: worst 18.6° against 13.9°, outward median 10.2° against 7.0°. Two independent lenses agree, so
    S3's pending disqualifier is now confirmed.
  - (b) Its bar is inverted (S3, and my check).
  - (c) Its 0x1AB parser entry at 50 Hz adds a timeout to canValid.
  - (d) Its fork drives the 4–8 Hz ratchet band to the highest of any row (14.4 / 12.0 deg/s), the opposite of note 4.
- **Its fork half survives** as a graft source (with D1c firmware, N1 falls to 9.8°). Fly it only with the 4–8 Hz cause
  resolved first: the lead, or the 0.06 O1 lead with instant trips.

**D1a (rank 11, DISQUALIFIED):** N1 (above). Its value is as the negative control that proves the opposing clause needs a
replacement, not deletion.

**D3-b (rank 12, DISQUALIFIED):**
- The soft-EME band is not replayed, and override effort rises +24 %.
- It is dominated: the rail is reached on 0 ms, and in S2 its >2500 instant O1 trips on the twist, so t90 is 0.65 against
  0.41 at 3 m/s.

**D5 V299-a (rank 13, DISQUALIFIED):**
- GATE 2: O1 loop 17.4° / 1.5 dB at 90 ms; 17 R79 sub-bar points.
- Worst N1 (26.3°) and worst overshoot (9.9°).
- Its Kf is GATE-2-capped at an inert value.
- GATE 1 decode is owed.
- Its designer already rejects it.

---

## 4. Disqualifiers

| candidate | disqualifier | evidence |
|---|---|---|
| D1a | N1 release lurch: out_2_511 @12.5–22 m/s 15.9° against 4.71°; nudge 8.0° against 0.8°; S2 worst 23.7° against 13.9° | D1 `d1_n1` (Lane3 = V298 control bit for bit); S2 LH table |
| D5 V299-b (as designed) | Firmware = D1a, so the same N1 failure (S2 worst 18.6°; outward median 10.2° against 7.0°); bar inverted; parser freq 50 | S3 §5 + S2 LH + S3 §4.1, and my §7 check |
| D3-b | Soft-EME 5120–~5900 band unreplayed (do not fly); dominated by D3a | S3 §3; D3 §2.2; S2 F3 |
| D5 V299-a | GATE 2 fork-loop collapse (1.5 dB at 90 ms) and R79 sub-bar points; worst N1 and overshoot; GATE 1 decode owed | S1 §3.6; S2; S3 §2 |
| D4a, D4b+GBS13 | **Conditional:** they fail the panel R2 box at 10–17.5 m/s if the ms_free products stay gated. Under this lens I treat them as at risk to note 1. | S1 finding 2 (two engines) |

**Must-fix (not disqualifying):**

| candidate | must-fix |
|---|---|
| D2a / D2b | bar sign |
| D3a | K3 post-clip; override latency; K5 not coupled to K2; bar |
| D1c | A16B; bar param; `nan` parser entry |
| D4b | instant O1 path; param-gate the constants |

---

## 5. The single best graft from each losing candidate

| from | graft | why, under this lens (number and source) |
|---|---|---|
| D1 fork bar | (rank 2, carried with the winner) | note 3 fixed with the correct sign |
| **D3-a** | **K1, the low-speed authority envelope**: cap 300 deg/s ≤ 5 m/s → 200 at 8 → 120 at ≥ 10, clip 30 / 25° at 3.1 / 8 m/s; highway knots unchanged | Under D1c firmware it gives S2's fastest turn-in (G:D1c+D3fork t90 0.42 / 0.48 s, ω 222 / 178, tap 73 %) with N1 worst 9.1°. The rail is untouched and P stays below it. Its speed taper keeps the change below 10 m/s, where the hard manoeuvres were. **Take K1 without K2's 100 ms hold and without the post-clip K3.** |
| **D2a** | **The O1 gate G4 with the O1 lead at 0** (> 1200 instant; 600–1200 held 80 ms; off ≤ 500), behind `AccordAngleOvrHard / OvrDebounce / OvrLead` | S1: O1-loop GM 6.0 → 9.4 dB at Trt 60 ms and 3.2 → 8.3 dB at 90 ms, at the 5.2–5.6 Hz crossing where r79's 4–8 Hz excess sits. r79: no-press O1 347 → 30, every hand caught ≤ steeringPressed + 10 ms. It is the override form S3 rates best, and it is toggle-expressible. |
| D2b | The **plan-trajectory lead / interpolation** (b2/b3), as a later, separate fork experiment | The best fork-only small-correction tracking (C2 slow e_rms 0.76 / 0.44 against 0.99 / 0.60), which targets note 1's "robust but not crisp" caveat. It is not for the same drive as the authority terms. |
| D4b | **The LP hand word + motion gate (gp-0x6a32), with the b4.7 = sign(h) instrument, held in RESERVE** | It is the pre-designed next step if the authority graft makes D1c's 1229 freeze fire on the faster twist. That is S2's G:D1c+D3fork: hand-lost 0.22 at 3 m/s. It has H1 0/20000 and GATE 1 with V288 flight precedent already done. |
| D4a | **The 275 /min one-quantum setpoint-reversal census**, which makes a **fork hysteretic setpoint quantiser** the precondition for any stick fix | The only evidence-based route to note 4's second mechanism (the stick). Every friction-FF form was rejected because of this jitter (D4 §4; D5 s7). |
| D4b+GBS13 | none beyond D4b's and D4a's | — |
| D5 V299-b | **The drive-card item 1 and P4**: 2–3 hands-off ≥ 60° turns at ≤ 8 m/s with the hands hovering, plus the question "do you want the 6× in hand-steered turns?" | r79 had only **1.2 s** of hands-off fast wind-up (REFUTE-inference 2a/§5). Without this exposure, no build can be scored on note 2 at all. |
| D1-a2 | a later, separate dose of low-speed stiffness (±1° 0.2 Hz tracking at 3.1 m/s 0.18 → 0.50) | only after D1c's flight reads clean |
| D1a | none (negative control) | — |
| D3-b | none. Its finding that the rail is reached on 0 ms is the evidence to keep SCL/PCL at V282/V298's values | — |
| D5 V299-a | none. Its finding that friction comp is GATE-2-capped at an inert Kf 28 rules the firmware-feedback stick class out | — |

---

## 6. For the orchestrator: the composite, and the rulings this lens needs

### 6.1 The composite I would score next (BELIEF until scored as ONE S2 row)

| layer | element | source | note it serves |
|---|---|---|---|
| firmware | D1c's three edits, **in place** (§6.2), F181 A16B, main-block CRC | D1 + S3-7 | 4 (relay), N1, 1 kept |
| fork | bar = clip(+8·s10 / 2461), `AccordAngleBarFromEps`, 0x1AB listed with `nan` | D1 + S3-3 | 3 (and shows the 6× headroom) |
| fork | O1: > 1200 instant; 600–1200 held 80 ms; O1 lead 0; `co_tq` status bits | D2a | 2 (no twist relay or re-slew), 4 (4–8 Hz margin) |
| fork | K1 cap/clip schedule ≤ 8 m/s (or D2a's cap 300 / clip ×1.6), with D2's 0.4 s takeover ramp on release/engage | D3a / D2a | 2 |
| fork | **no** post-clip lead (D3 K3); no SteerDelay change in the same drive | S1 finding 5 | 1 kept |

**What S2 must show for this row** before it is offered:
- N1 worst ≤ 11.2°;
- 4–8 Hz wheel rate ≤ V298 (8.5 / 9.1);
- hand-lost at 3 m/s reported (the twist crossing 1229);
- O1 twist trips;
- t90 near G:D1c+D3fork's 0.42 / 0.48 s.

None of S2's three graft rows uses D2's O1 gate with lead 0, so this row is unscored.

**Interpretability on one short drive.**
- The firmware change is attributed by D1's zero-byte rule-identity replay against the 0x1AB tap (V298 won 18/18 r79
  windows, dR² +0.605) and by carFw A16B.
- Each fork term is param-gated and shows in `co_tq` bits.
- Fly the authority params (cap/clip) in the drive card's hands-off item only. Otherwise one symptom ("stutter")
  cannot be attributed between the D1c relay fix and the faster setpoint.

### 6.2 D1c without the relink (EVIDENCE for the bytes, BELIEF for equivalence until H1)

**What the Ghidra listing shows.** The dry-run of V298's cave `0xC4C00..0xC4CD9` (77 instructions) shows **only one branch
targeting the span 0xC4C6A..0xC4C7D**: the opposing block's own `bnh 0xC4C7A` at 0xC4C70, which D1c removes. Every other
cave target is outside the span (0xC4C18 / 30 / 3E / 54 / 84 / 94 / 96 / AC / B8 / C2 / C8 / D8, 0x2A164, 0x29D7E).

**The construction:**
- Replace the 20 bytes 0xC4C6A..0xC4C7D (V298's 16-B opposing block plus its 4-B θ load) with:
  - **D1c's own 12 bytes**: `24 4f 00 96` ld.h −0x6a00 ; `09 68` mov r9,r13 ; `30 69` xor r16,r13 ;
    `ae 05` bge +4 ; `00 4a` mov 0,r9. They are byte-identical to D1c's H1-tested relinked listing (checked by
    `jg_d1c_inplace_bytes.py`).
  - then 4 × `nop` (`00 00`).
- Set the hard threshold imm16 at 0xC4C64 to 1229.

**Result:**
- **21 changed bytes before the CRC** (against D1c's 152).
- The cave stays 260 B. The table pointer and every displacement are unchanged.
- The cost is 4 nops at 1 kHz.

**What the builder must still do:** prove that no transfer from outside the cave lands inside the span (the hook enters
at 0xC4C00), then re-run H1 and the Ghidra decode on the built image. This is the "in-place before a cave" rule applied
to D1c's own loop.

### 6.3 Rulings this lens cannot make (each one decides a note)

1. **Note 2 in hand-steered turns (D5's P4).**
   - Every candidate yields to a firm hand by design. The r79 hard manoeuvres were hand-steered.
   - If the operator wants co-steer authority in AOL turns, that is an unproposed design. D3's K2 is a partial step toward
     it, and it pays for that in override feel.
   - Ask him before scoring note 2 on the next drive.
2. **The goal's "hard-turn 1.6–3 Hz wheel rate ≤ V282" criterion conflicts with note 2.**
   - S2: D3a 21.9 against 5.1 deg/s; every authority row is worse. All five designers declared this.
   - For note 4's "stuttery/ratchety", the stutter-specific readouts are the 4–8 Hz wheel rate, stall-surges and ratchet
     trains (C10).
   - **It is his criterion: present the conflict, do not drop it silently.**
3. **The fork O1 timing at Honda's level: instant or held.**
   - Instant-1200 trips on the faster twist (S2: D5b 15 trips).
   - Held 100 ms costs 370–400 ms of setpoint yield with 75 % rail under the hand (D3a).
   - D2's G4 (instant > 1200, held only at 600–1200) is the middle form.
   - The firmware fade acts at once in every form. Whether "the hand torque the Honda stock threshold recognises" must also
     move the *setpoint* instantly is his call.
4. **The ms_free GATE-2 definition** (S1 finding 2). It decides D4a and D4b+GBS13. This lens says do not stiffen the highway
   loop the operator called robust.
5. **Authority re-arms the relay one level up** (D3 finding 3; S2 F3).
   - A faster setpoint raises the twist: S2 p99 1378–1559 at 3 m/s against flight p90 607–681.
   - **Pre-register for the composite:** stall-surges and freeze onsets within ±0.25 s of \|bar\| 1229 crossings. A
     ≥ 2× enrichment means D4b's LP + motion gate (§5) is the next build. D2's G-c, twist compensation from the 1 kHz motor
     rate, is the clean but larger alternative.
6. **The small-correction stick is unaddressed by every candidate** (S2 cannot reproduce it).
   - Note 4's second mechanism stays open.
   - The evidence points at the fork setpoint's 275 /min one-quantum reversals (D4), not at gain. Gain is GATE-2-capped
     (D1, D3, D5a).

---

## 7. Checks I ran myself (crux verification; read-only)

| check | method | result | wall |
|---|---|---|---|
| Bar sign: S3's "D2/D5 inverted", by a **second method** | `judges/jg_bar_sign_check.py`. A different frame set from S3: all latActive hands-off frames with \|tap\| ≥ 10 LSB and \|today's bar\| ≥ 0.1 (n 31,987). Angle from the wire 0x14A, not carState. Today's bar rebuilt from `ctl_dcurv`, `lp_roll`, 0.3247. | D1 formula: sign agreement **0.854**, corr **+0.822**. D2/D5 as written: **0.146**, corr **−0.822**. **S3 confirmed** (EVIDENCE). | 0.05 s |
| D5b's firmware is D1a | S3's byte census plus D5's own table (FZ1 = FZ2 = 1229) | confirmed by the two pages' bytes. The N1 consequence is scored by two independent lenses (D1 `d1_n1`, S2 LH). | — |
| D1c in place, no relink | Ghidra `disassemble_bytes dry_run` of V298 0xC4C00..0xC4CD9 for the branch-target census. `judges/jg_d1c_inplace_bytes.py` for the byte construction and diff count, with D1c's hex compared. | 1 internal branch into the span (removed); 21 changed bytes; D1c's 12-B sequence matches. BELIEF until H1. | 0.08 s |
| D3a override latency arithmetic | K2 = > 10 frames above 1200. S2's hand ramps to 1500 in 0.3 s, so it crosses 1200 at 0.24 s; plus 0.11–0.13 s gives ≈ 350–370 ms. | consistent with S2's 370 ms | — |

**Not re-run by me (inherited, BELIEF here):**
- every GATE 2 number (S1);
- every simulation cell (S2);
- the designers' H1 interpreter runs;
- the 0x1AB checksum/counter validity: measured independently by D1, D2 and D5;
- the r79 replay counterfactuals.
