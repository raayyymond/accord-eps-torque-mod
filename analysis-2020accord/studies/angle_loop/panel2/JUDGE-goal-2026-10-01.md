# JUDGE: GOAL AND ROBUSTNESS. Angle-loop design panel, round 2, 2026-10-01

**Status: ANALYSIS ONLY.** Nothing was built, flashed or sent. No CAN traffic. The fork was not touched. Nothing was
committed. Ghidra was not opened: every byte-level claim below rests on executing cave bytes with the common time
scorer's own V850E2 interpreter (`score_time.h1`), not on new disassembly. No shared scorer file and no shared cache was
edited or rewritten: my runs import `panel2/score_time.py` unchanged and write to my own folders.

**Author:** JUDGE GOAL, a subagent of the orchestrator `main`.

**My lens: PRIORITY 1, the goal.** I rank by how many of the goal's criteria a candidate meets in each speed band, read
off the two common scorers' tables:

- **Must-haves:** tracking on route r71b's real angle paths ≥ 8 m/s, turn-hold, and no-grind.
- **Declared frontier:** low-speed stick-slip.
- **GATE 2:** an undeclared shortfall on a combined member costs more than a declared one. A miss whose pre-registered
  stop band covers the predicted ring is rewarded.

**Order of authority.** A common scorer's number beats a designer's claim, unless I re-ran the claim and showed
otherwise.

**Marking.** Every decision-bearing claim is marked **EVIDENCE** (with its method) or **BELIEF**. Code is cited by
heading or grep string.

---

## 0. Verdict

### 0.1 The headline

**No designer candidate meets the goal on both common scorers. The two scorers split the panel exactly in half.**

- **The time-goal side (EVIDENCE: SCORE-TIME §0 item 1 and its per-band fails table).**
  - E2-A2, E2-A3, E2-A3-12k and E2-A2-X are the only candidates that pass every decidable time criterion of the goal,
    in every band ≥ 8 m/s.
  - All four run **P2's small-signal loop**.
  - The frequency scorer refutes that loop on the R2 box: **690 fails** (SCORE-FREQ T0 and T2).
    - 197 of them sit on the brief's own members under the frame box: J_hi at 42.3°, b_lo×J_hi+h10 at 26.1°,
      b_q×J1.0+h10 at 27.1°.
    - 493 sit on the ms_free products, down to **8.2°**: a 1.27 Hz ring with ζ 0.028.
- **The frequency side (EVIDENCE: SCORE-FREQ F2 and T2).**
  - G-P48, G-P44, G-F24, G-A22, G-P48L and G-P48k40 are the only candidates with a firmware I that have **0 fails** on
    the R2 box.
  - All six keep **ICL 4096**, so the round-2 refuter's F1 stands on every one of them.
    - Tracking: 0.814–0.903.
    - Turn-hold: 0.66–0.78 at 12.5–22 m/s.
    - Release lurch: over the 8° bar at 8–12.5 m/s.
  - They fail the time goal in 4 of 5 bands.

**The way out is the composition the scorers point to.** SCORE-FREQ F1 says *"the policy block has to be carried onto a
skeleton that passes"*. I built and scored that composition.

**Graft J-G48-A3:**

- **The loop:** G-P48's fresh-rate D (Kd 48) and G-P48's 6-knot G(v) table.
- **The integral policy:** E2-A3's, with ICL 8192, the angle-referenced I bound with two slopes, and the
  low-speed cap.
- **The cave:** E2-A3's 222 B, carrying G-P48's table rows.

**What J-G48-A3 does on the scorers:**

- **Time scorer (EVIDENCE: §1 V2 and §4).**
  - It passes **every decidable time criterion of the goal in every band ≥ 8 m/s**, on all four members.
  - The run is the common time scorer, unchanged, in its primary `vgr` frame, with in-batch controls that reproduce
    SCORE-TIME.
  - Tracking with r71b's own torque word replayed: **0.980 / 0.987 / 1.006** (8–15 / 15–22 / > 22 m/s).
  - Turn-hold (a_lat ≤ 2.5): **≥ 0.98**.
  - Release lurch on b_lo×J_hi: **4.1° light / 3.2° firm**. Both are lower than E2-A3's 5.8° / 4.7°.
- **Frequency scorer (EVIDENCE by construction plus the scorer's own statement, §1 V3).** It inherits **G-P48's 0-fail
  verdict** on the R2 box, the strict reading and G's extra products.

**This is the judge's recommended primary.** Two alternates sit within the rubric's resolution, and the choice between
them is an orchestrator ruling (§4):

- **J-G44-A3:** more 20 Hz margin.
- **J-G48d-A3:** keeps P2-class small-correction behaviour at highway speed. It pays with a declared b_q×ms_free
  shortfall that R3\* covers.

### 0.2 Ranking of the designer candidates (rubric §2; scores out of 100)

Scores come from `JUDGE-goal/judge_score.py`, applied to the scorers' own summary files.

**Columns:**

- **A time** is out of 50.
- **B freq** is out of 30.
- **C decl/verify/hazard** is out of 20.
- **bands ≥ 8 failed** counts the goal-fail bands in SCORE-TIME's per-band fails table, out of 5.

**Row tags:**

- **DQ** = disqualified (§5).
- **(rej)** = withdrawn by its own designer.

| # | cand | score | A / B / C | bands ≥ 8 failed | one-line reason |
|---|---|---|---|---|---|
| 1 | **E2-A3-12k** | **80.5** | 48.9 / 15.2 / 16.5 | 0 | Every time criterion is met in every band, with the most tracking margin (replay 0.995 / 0.991 / 1.005). It runs P2's refuted small-signal loop: 690 R2-box fails, ms_free× at 8.2° / ζ 0.028. That was declared only as "inherited" (M-E2-6), with no covering stop band for the tier-B residual. |
| 2 | **E2-A3** | **80.5** | 48.8 / 15.2 / 16.5 | 0 | The same at ICL 8192. The < 8 m/s release is back to P2's (12.0 / 10.9°). Same frequency refutation. **The E2 policy block is the best integral policy on the panel.** |
| 3 | E2-A2 | 79.8 | 48.2 / 15.2 / 16.5 | 0 | Equals A3 at ≥ 8 m/s. Below 8 m/s the release regresses to 15.5° (declared as M-E2-1). |
| 4 | E2-A2-X | 79.1 | 48.4 / 15.2 / 15.5 | 0 | A2 with 6803 == 2. Engage droop falls from 6.3° to 4.3°. The fade arm pushes up to ×2.1 harder against a firm hand, and the fork must keep sending 2. Same frequency refutation. |
| 5 | E2-S | 78.0 | 44.9 / 15.2 / 18.0 | 1 | Fixes F1. The light lurch is 11.1° at 8–10 m/s, above the 8° bar. The opposing-hand freeze costs 0.006 of replay tracking. Frequency loop = P2. |
| 6 | E1-freeze | 73.0 | 44.4 / 15.2 / 13.5 | 1 | Fixes F1. The light lurch is 11.8° at 8–10 m/s, and its own designer calls it dominated. Frequency loop = P2. |
| 7 | E2-R1 | 71.4 | 38.2 / 15.2 / 18.0 | 4 | ICL 8192 alone. It fixes tracking and hold, but the light-hand lurch is 24.3° in 4 bands (the V283 class). It proves the brief's premise. |
| 8 | E2-L (rej) | 69.5 | 36.3 / 15.2 / 18.0 | 4 | The leak drains the hold on the real torque word: replay tracking 0.938 at 8–15 m/s. Light lurch 24.3°. |
| 9 | E1-cal | 67.4 | 38.2 / 15.2 / 14.0 | 4 | Zero code bytes for F1. The light lurch is 24.3°: the designer declared "~17°", under-quantified by ~7°. Its "inherits P2's GATE-2 PASS" claim holds only on the round-1 set. |
| 10 | E1-reset | 65.9 | 38.2 / 15.2 / 12.5 | 4 | E1-cal plus a firm-hand reset: the firm lurch falls from 8.4° to 4.2°. The light lurch stays 24.3°, and the reset is a new RAM write. |
| 11 | G-P48k40 | 64.2 | 22.2 / 24.9 / 17.0 | 4 | GATE 2 clean. ICL 4096 leaves tracking at 0.903 / 0.837 and hold at 0.70, and Ki 40 costs more tracking still. |
| 12 | **G-P48** | 63.0 | 20.4 / 25.6 / 17.0 | 4 | **The best frequency skeleton on the panel**: 0 fails including strict and G-strict, the least 5 Hz anti-damping (−0.05). It fails F1 (tracking 0.891 / 0.834, hold 0.69). **This is the primary graft's skeleton.** |
| 13 | G-P44 | 62.6 | 18.9 / 26.7 / 17.0 | 4 | As G-P48, with a 12 % M20 margin. More dwell-then-jump. Fails F1. |
| 14 | G-P48L | 61.6 | 19.2 / 25.4 / 17.0 | 4 | A deeper dip: ±1° in-phase gain 0.11 at 10–12.5 m/s. Fails F1. |
| 15 | G-P48d | 61.4 | 21.7 / 22.6 / 17.0 | 4 | b_q×ms_free is declared, and R3\* covers its 1.28 Hz / ζ 0.061 ring. Small corrections behave like P2's. Fails F1. |
| 16 | G-P44d | 61.2 | 20.4 / 23.8 / 17.0 | 4 | As G-P48d at Kd 44. Fails F1. |
| 17 | E2-K0 (rej, DQ) | 61.0 | 17.1 / 27.9 / 16.0 | 4 | GATE 2 clean, but no firmware I. Real-curve hold 0.652; tracking 0.915 at 15–22 m/s; light lurch 20° (51.7° below 8 m/s). It needs fork code beyond the angle interface. |
| 18 | E1-sched (rej, DQ) | 57.7 | 31.1 / 15.2 / 11.5 | 5 | Fails tracking in every band (0.886 / 0.928 / 0.941). No listing. |
| 19 | G-F24 | 57.3 | 17.9 / 21.4 / 18.0 | 4 | Held D, pol-free, 0 fails. Its 13 Hz anti-damping is −0.91 (1.9× V295) and its 5 Hz is −0.53. Fails F1. |
| 20 | H-A | 56.9 | 32.4 / 19.0 / 5.5 | 4 | The structurally cleanest operand (hold-age-free, ReTw −0.40 flat), and clean tracking. Its bleed fails replay tracking (0.925 / 0.947, undeclared). The light lurch is 22.2°. A 0.84 Hz ms_free ring lies outside its declared bands. The published numbers were a different loop. No listing. The fork SR fold is load-bearing. |
| 21 | G-F24d | 56.0 | 19.7 / 18.4 / 18.0 | 4 | As G-F24 with b_q×ms_free declared. Fails F1. |
| 22 | H-B | 55.8 | 35.6 / 11.2 / 9.0 | 3 | Replay tracking 0.933 at 8–15 m/s. Light lurch 20.8°. 13 Hz −0.91. More GATE-2 fails than it declared. No listing. |
| 23 | E1-bleed (rej, DQ) | 54.1 | 27.5 / 15.2 / 11.5 | 5 | Replay tracking 0.739–0.829 in every band. |
| 24 | G-A22 | 53.2 | 16.6 / 20.6 / 16.0 | 4 | Frame-exact and pol-free. Texture is 1.3–1.4 counts; anti-damping is −0.92 at 13 Hz and −0.94 at 5 Hz. Two RAM words plus an untraced sentinel accessor. Fails F1. |
| 25 | G-A22d | 51.7 | 18.1 / 17.6 / 16.0 | 4 | As G-A22. |
| 26 | P2 | 46.7 | 20.6 / 14.2 / 12.0 | 4 | Refuted: F1 in 4 bands, lurch 10.9°, 690 R2-box fails. |
| 27 | D2a | 46.6 | 20.5 / 14.2 / 12.0 | 4 | As P2 (702 fails). |
| 28 | F2 | 42.5 | 20.6 / 8.9 / 13.0 | 4 | As P2, plus held-D 13 Hz anti-damping of −0.84. |
| 29 | B0r | 42.4 | 20.4 / 8.9 / 13.0 | 4 | As F2 (706 fails). |
| 30 | E1-splitP (rej, DQ) | 41.9 | 19.4 / 7.9 / 14.5 | 4 | ρ = 1.0000 (ζ ≈ 0) on a gated member. 5052 fails, including nominal. Turn-hold 0.755. |

### 0.3 Grafts the judge built and scored on the common time scorer (§4)

Same rubric. Every graft has **0 goal-fail bands ≥ 8 m/s**.

| graft | score | what it is | why it is not the primary / why it is |
|---|---|---|---|
| **J-G48-A3 (PRIMARY)** | **88.7** | G-P48 loop + E2-A3 policy, ICL 8192 | Passes both scorers. GATE 2 has 0 fails on every reading. Costs: M20 0.965–0.976× V295, and more small-correction dwell at 12.5–22 m/s (§4.1). |
| J-G44-A3 | 88.8 | G-P44 loop + E2-A3 policy | Tied with the primary. Buys a 12 % M20 margin for **more** highway dwell-then-jump (305 vs 271 events) and a lower in-phase gain (§4.2). |
| J-G48-A3-12k | 88.7 | the primary at ICL 12288 | +0.012 tracking at 8–15 m/s. A higher worst-case I authority at 6–12.5 m/s large angles (§4.4). |
| J-G48d-A3 | 87.0 | G-P48d loop + E2-A3 policy | **Pick this one if the orchestrator rules the b_q×ms_free corner covered by R3\***. Highway small corrections stay P2-class: ±1° dwell 226 vs 271, ±0.3° in-phase gain 0.78 vs 0.31 at 15–22 m/s (§4.3). |
| J-F24-A3 | 80.8 | G-F24 held-D loop + A3 (no listing) | Pol-free, but 13 Hz anti-damping is 1.9× V295 and small corrections are the worst of the grafts. A mirror only. |

---

## 1. What I verified myself (the crux of every decision-bearing claim)

| # | claim | method | result |
|---|---|---|---|
| V1 | **The graft cave bytes equal the lane the grid runs.** The graft is E2's assembled A3 cave (`e2_cave_A3.hex`, 222 B), with G-P48's (or G-P44's, G-P48d's) 7 table rows written into the cave's own table. The cave's own `mov imm32` locates that table. | `score_time.h1` on the substituted bytes (`hexbytes` 'rows' path, the same path the scorer uses for G-P48L): 3 000 edge-heavy cases each, with the refuter's interpreter extended by `Cpu2`. **Negative control:** the lane runs P2's rows, the bytes carry G-P48's rows. | **EVIDENCE: 0 / 3000 mismatches** on J-G48-A3, J-G48-A3-12k, J-G44-A3 and J-G48d-A3 (and on the controls P2, E2-A3, G-P48, G-P44). **The negative control fails 1498 / 1500**, so the row substitution is real. J-F24-A3 has no hex (a held-D cave + A3 was never assembled): **BELIEF.** Output: `JUDGE-goal/h1_grafts_out.txt`. |
| V2 | **My grid is the common scorer's grid.** | `JUDGE-goal/judge_grafts.py run` imports `panel2/score_time.py` unchanged. It adds the grafts as `Cand` rows using the scorer's own switches (rows, D operand, Kd, ICL, `ARB_A3`). It runs the scorer's `run_grid` / `summarize` / `tables` in frame `vgr`: all 22 scenarios × 4 members × 94 speeds. P2, E2-A3, G-P48 and G-P44 ride in the same batches as **controls**. | **EVIDENCE: the controls reproduce SCORE-TIME's decision-bearing cells.** Tracking and real-curve hold to ≤ 0.002. Turn-hold to ≤ 0.003. Light and firm lurch to ≤ 0.02°. Droop to ≤ 0.007°. **Every per-band fail list is identical.** The 3 s-hold bridge reproduces SCORE-TIME §5.7 exactly: P2 7.2 / 7.9 / 7.0 / 10.9°; E2-A3 2.4 / 4.4 / 2.2 / 5.8°. Texture under road noise and the ±0.3° stick-slip gains differ by up to 0.11 (cause in §6 D1). |
| V3 | **A graft's frequency verdict is its skeleton's.** | The graft's Kp, Ki, Kd, G table and operands are byte-identical to G-P48's (V1), so its linear controller FRF is G-P48's. SCORE-FREQ F1 (EVIDENCE there): no integral policy moves GATE 2. Every freeze, bound or clamp-saturated state runs the I-frozen PD loop. The linear scorer models an unbounded integrator, so ICL does not enter. G-P48's I-frozen loop passes the R2 box (T0 "I-frozen B box" 50.1). | **EVIDENCE (construction plus the scorer's tables):** J-G48-A3 = G-P48's row of T0/T1/T2, so 0 R2-box fails, 0 strict, 0 G-strict. **BELIEF:** that switching between two stable loops (PID ↔ I-frozen PD, at the bound) cannot destabilise. Supporting EVIDENCE (sim): 0 hunting columns ≥ 8 m/s and 0 int32 wraps on every graft. |
| V4 | **E2-A3's bound still never binds on a normal hold when G-P48's lower highway table is underneath it.** | E2's own §2.3 measurement: the CAN-427 tap on V294 at every steady hands-off r71b hold sits ≥ 43 T under the bound. The tap is the WHOLE lane torque (I + P). Under any table, I's share ≤ the total. | **EVIDENCE (E2's measurement plus arithmetic), not re-run by me.** The graft's turn-hold of 0.976–0.997 and real-curve hold of 0.98 are consistent with the bound not binding. |
| V5 | **Where the graft's small-correction cost lives.** | My own per-member breakdown of the graft grid: ±1° and ±0.3° sinusoids, 12.5–22 m/s. | **EVIDENCE (sim):** see §4.1. The cost appears on the **nominal** member, not only on stress corners. Nominal ±1° 0.5 Hz dwell-then-jump: P2 2, E2-A3 3, J-G48d-A3 6, J-G48-A3 21, J-G44-A3 32. |
| V6 | **Scorer statements I relied on without re-running.** | Read SCORE-FREQ T0/T1/T2/F1–F9 and §3, and SCORE-TIME §0–§7. Checked their numbers against the summary JSONs that `judge_score.py` loads. | **EVIDENCE** that my tables quote them correctly (the script reads `score_time_summary.json`). The SCORE-FREQ constants in `judge_score.py` are copied from T0, with each row named. |

---

## 2. The rubric (fixed before scoring; the code is `JUDGE-goal/judge_score.py`)

### A. Goal time criteria, 50 points

Source: SCORE-TIME `vgr`, worst over the four members.

- **a1. Tracking (20).** 8 points each for the 8–15 and 15–22 m/s data bands, 4 for > 22 m/s.
  - Measure: the worse of clean and **r71b's own torque word replayed**.
  - Score: 0 at ≤ 0.90, full at ≥ 0.95. The bar is a must-have, so the ramp is short.
- **a2. Turn-hold (14).** The minimum of synthetic hold (a_lat ≤ 2.0) and real-curve hold, in three groups: 8–12.5,
  12.5–15, and ≥ 15 m/s.
  - Score: 0 at ≤ 0.80, full at ≥ 0.90.
- **a3. Release lurch ≥ 8 m/s (9).** The worst of the light and firm hand.
  - Score: full at ≤ 8°, 0 at ≥ 20°.
- **a4. Other (7):**
  - in-phase gain ±1° at 0.2 Hz (1);
  - engage droop (0.5);
  - hard-turn 1.6–3 Hz ratio (1);
  - **±1° dwell-then-jump events ≥ 8 m/s (2.5)**: the goal's first criterion, judged relative to the panel because
    V282 cannot be simulated;
  - **release lurch below 8 m/s (2)**: the declared low-speed frontier.

### B. Frequency and no-grind, 30 points

Source: SCORE-FREQ T0 and T2.

**b1. GATE 2 on the R2 box (15):**

| points | condition |
|---|---|
| 15 | 0 fails |
| 12 | fails only on b_q×ms_free, **declared, with R3\* covering the predicted ring (ζ < 0.10)** |
| 6 | fails only ms_free×, with an **undeclared** ring outside the declared bands (H-A) |
| 5 | H-B (fails beyond its declaration) |
| 3 | P2's loop, with the fails declared as "inherited" (E1, E2) |
| 2 | the round-1 four (undeclared, refuted) |
| 0 | ρ = 1 |

**b2. No-grind (15).** All candidates pass the goal's hard line "20 Hz gain ≤ V295's", so this term scores margin:

| points | measure | full marks | zero |
|---|---|---|---|
| 5 | M20 margin | ≤ 0.75× | 1.0× |
| 5 | 13 Hz anti-damping vs V295's −0.47 | no worse than V295 | −0.95 |
| 5 | 5 Hz anti-damping (V295 damps at +2.46; F7 = 0 is the stop) | 0 | −1.0 |

### C. Declaration, verification and hazards, 20 points (judge's rulings, reasons in §3)

- **Verification (6):**
  - hex-backed with H1 at 0 → 6;
  - assembled by the scorer or the judge → 5–5.5;
  - mirror only → 2.
- **Declaration accuracy (8):** deducted for every scorer-found failure the designer did not declare, or
  under-quantified.
- **Hazards (6):**
  - fresh-D pol = −1 dependence −1;
  - a new RAM write −0.5;
  - the ARB road-load cap (M-E2-4) −0.5;
  - the 6803 == 2 arm −1;
  - a load-bearing fork integral −3;
  - box10 RAM plus the untraced sentinel −2;
  - a load-bearing fork SR fold (H-A) −2.5.

**Sensitivity.** The top three grafts sit within **1.8 points**, which is inside the rubric's resolution. Their order is
decided by the rulings in §4, not by the decimals. Every designer candidate below the grafts is separated by its fail
bands, which no weight change in A reverses.

**Example:** E2-A3 against G-P48. E2-A3 has 0 fail bands and G-P48 has 4. G-P48 would need b1 + b2 to outweigh a 28-point
time deficit.

---

## 3. Findings by family (what decided each score)

### 3.1 E2 (the angle-referenced I bound): the best integral policy, on a refuted skeleton

- **The ARB family solves F1 and F4 together.** EVIDENCE (SCORE-TIME §0 item 1, §5.2, §5.7):
  - replay tracking ≥ 0.985;
  - turn-hold ≥ 0.98 to a_lat 2.5;
  - light and firm lurch 5.8° / 4.7° (b_lo×J_hi);
  - in both frames.
- **No other policy on the panel bounds the light-hand lurch without draining the hold on the real word.**
  - E1-bleed, E2-L, H-A and H-B all drain it, and all fail replay tracking.
  - E1-cal, E1-reset and E2-R1 do not bound it: 24.3°.
  - E1-freeze and E2-S bound it only above their threshold: 11–12° at 8–10 m/s.
- **E2's frequency inheritance is the whole deduction.**
  - E2 declared it as M-E2-6, but with the FA reading only (43.2° / 28.3°). On the R2 box it is 690 fails, including
    ms_free× at 8.2° (ring 1.27 Hz, ζ 0.028).
  - R3\* (ζ < 0.10) would catch that ring. It would **not** catch the tier-B residual on the brief's own members
    (26.1–27.1°, ζ about 0.2).
  - **Partly declared, partly uncovered.**
- **A3 against A2.** A3 is preferred: the low-speed release returns to P2's (12.0 / 10.9° vs A2's 15.5 / 14.1°). The
  price is the M-E2-1b low-speed turn-hold (0.90–0.95 below 6 m/s), declared.
- **A2-X.** The engage-droop gain is real: 6.3° → 4.3°, EVIDENCE. But it raises lane torque against a firm hand by up to
  ×2.1 (EVIDENCE: E2's LERP read of `0xCBAE4`), and the fork must keep sending 2. **A separate decision, not part of the
  primary.**

### 3.2 E1 (fewest bytes)

- **E1-cal is the honest floor: F1 at 0 code bytes.** Its light-hand lurch is 24.3° at 10.25 m/s (EVIDENCE: SCORE-TIME
  §6 item 4). E1's declared "~17°" skipped 10.25–12.25 m/s on its grid.
- **E1-reset's firm reset works** (firm lurch 8.4° → 4.2°), but it does nothing for the light hand.
- **E1's GATE-2 claim** ("inherits P2's PASS, 0 fails") holds only on the round-1 set (SCORE-FREQ §3, last E1 row).
- E1's analysis that **light override and hands-off reaction torque cannot be separated by magnitude** is correct, and
  it is the reason every torque-keyed drain fails. E2's angle-referenced bound is the answer, because it reads no
  torque word.

### 3.3 G (D operand and margins): the skeleton that passes, starved by ICL 4096

- **G's non-d tables are the only firmware-I loops with 0 fails** on the R2 box, the strict reading and G-strict
  (EVIDENCE: SCORE-FREQ F2).
- **Their time failure is entirely F1.** With ICL 8192 and the A3 bound underneath, the same tables pass every time band
  (§4). G declared F1 as another axis's problem. That is correct, and it is why the composition works.
- **G's real costs survive grafting (EVIDENCE, §4.1):**
  - small corrections at the dip and at highway;
  - G-M7;
  - M20 at 0.965–0.976× V295 for Kd 48.
- **G's PM-extractor finding** (leading crossings reported as negative margins) is confirmed by SCORE-FREQ F7. It
  affects no gated PID number, but **any I-frozen margin computed elsewhere with the shared routine must be re-read**.

### 3.4 H (whole loop): the right operand, the wrong policy, and published numbers for a different loop

- **H-A's operand is the panel's cleanest structure.** Fresh gp-0x69ca leaves no hold in the loop, and Re(T/ω) is −0.40
  flat over 5–25 Hz at every age (EVIDENCE: SCORE-FREQ F3).
- **But:**
  - its published frequency numbers are the held-operand D2a loop, double-aged (SCORE-FREQ §3 C9);
  - its bleed fails replay tracking (0.925 / 0.947), undeclared;
  - its light lurch is 22.2°: the withheld ICL-7500 rows are exactly where it fails;
  - its b_lo×ms_free ring at 0.84 Hz lies outside both bands it declared;
  - it has no listing;
  - the fork SR fold is load-bearing.
- **H-B** fails more than it declared (b_q×J1.0+h10 29.9°; J_hi+h10 41.4° strict).
- **H's F5 recommendation is sound, and I adopt it for every graft** (BELIEF, it is a procedure question): do not gate
  the firmware on 6803 == 2. Close the camera-relay hole with the A2 skip, the fork B3 gate, and the procedure.

### 3.5 Round 1 (P2, F2, D2a, B0r)

Refuted on both scorers (EVIDENCE: SCORE-TIME §6 item 14, SCORE-FREQ F1). They are superseded by the grafts, which keep
their in-place set (E1/E2/E4/A2/B2, hook `0x29D76`) unchanged.

---

## 4. The grafts

### 4.1 J-G48-A3: PRIMARY

#### What it is

| part | content | source |
|---|---|---|
| in-place set | P2 / rev2-A, unchanged: E1 `0x28F4C`, E2 `0x28FA4`, B2 `0x29A50`, A2 `0x29A56`, E4 `0x29D6A`, hook `0x29D76`; cals a 0 / b 8192 / C 65535, DB 0, DCL 10240, Kp 112, Ki 56 | as SCORE-TIME §3 |
| Kd record | **48**: the four cells `0xE5126..0xE512D` all equal (G-H3) | G's spec |
| cave | **E2-A3's 222 B at `0xC4C00`**: the fresh guarded D, the walk, the freeze, the ARB two-slope bound (26 / 102 T/deg + 1250 S, knee 2880) and the low-speed cap (4096 S below 1382 counts) | E2's spec |
| table | the cave's table carries **G-P48's rows**: (714, 1178, 1041) (1843, 1465, −6868) (2304, 692, −2328) (2707, 463, 1870) (4032, 1068, 2118) (6198, 2188, 0) (65535, 2188, 0) | G's `g_impls_frozen.json` |
| ICL | **8192** | E2's spec |
| RAM words | **0** | — |

**Bytes written:** ≈ 266 B by E2's counting convention (in-place 20 + cal 24 + cave 222). The Kd value changes but no
cell is added. **BELIEF until a built image is decoded.**

#### Scorer results

**Time** (EVIDENCE, sim, the common scorer in the `vgr` frame; `JUDGE-goal/judge_tables.md`):

| metric | J-G48-A3 | E2-A3 | G-P48 | P2 |
|---|---|---|---|---|
| tracking clean 8–15 / 15–22 / > 22 | 0.981 / 0.991 / 1.006 | 0.986 / 0.993 / 1.006 | 0.892 / 0.835 / 1.002 | 0.892 / 0.856 / 1.002 |
| tracking replay | **0.980 / 0.987 / 1.006** | 0.985 / 0.991 / 1.005 | 0.891 / 0.834 / 1.001 | 0.892 / 0.855 / 1.001 |
| turn-hold a ≤ 2.0 / a 2.5 (min ≥ 8) | **0.98 / 0.98** | 0.98 / 0.98 | 0.69 / 0.64 | 0.73 / 0.69 |
| real-curve hold min | 0.98 | 0.98 | 0.72 | 0.76 |
| light / firm lurch ≥ 8, b_lo×J_hi (1 s) | **4.1 / 3.2°** | 5.8 / 4.7° | 10.1 / 6.2° | 10.9 / 7.9° |
| the same, 3 s hold (bridge) | 4.1 / 3.2° | 5.8 / 4.7° | 10.1 / 6.2° | 10.9 / 7.9° |
| release < 8 m/s, light / firm (1 s) | **7.7 / 7.0°** | 12.0 / 10.9° | 7.7 / 7.4° | 11.9 / 11.5° |
| hard-turn 1.6–3 Hz ratio (max, 8–10 m/s) | **1.07** | 1.43 | 1.17 | 1.53 |
| step overshoot 8–10 m/s | 20.0 % | 29.5 % | 26.6 % | 37.1 % |
| engage droop (max ≥ 8) | 6.0° | 6.3° | 6.0° | 6.3° |
| 510 ms timeout mid-motion (max ≥ 8) | 2.41° | 2.27° | 2.41° | 2.27° |
| sentinel \|T\| @ 50 ms (max) | 70 counts | 75 | 70 | 75 |
| texture T 5–30 Hz under road noise (max ≥ 8) | 0.77 counts (bar 2.0) | 0.67 | 0.83 | 0.71 |
| hunt ≥ 8 m/s / below | 0 / 10 columns | 0 / 6 | 0 / 10 | 0 / 7 |

**Frequency** (EVIDENCE by construction plus SCORE-FREQ, §1 V3):

| metric | value |
|---|---|
| R2 box / strict / G-strict | **0 / 0 / 0** fails |
| tier A | 51.7° |
| tier B | 34.2° (b_q×J1.0+h10, FB κ0.83, 26.9 m/s; ring 1.89 Hz, ζ 0.18) |
| ms_free× | ≥ 35.4° |
| GM↑ | ≥ 13.9 dB |
| peak 5–30 Hz | −0.3 dB |
| M20 | **0.965** (ages 1–20) / 0.976 (21–30) × V295 |
| L20 | ≤ 0.97 |
| ReTw 5 / 13 / 20 Hz | −0.05 / −0.37 / −0.43; V295 is +2.46 / −0.47 / −0.82 |

#### Pre-declared misses

Each is quantified, with the stop band that covers it. This is the union of the two parents' declarations, plus what my
run measured.

| # | criterion | predicted | stop band |
|---|---|---|---|
| J-M1 | small corrections at 12.5–22 m/s (dwell-then-jump ≤ V282; G-M7) | **Nominal member:** ±1° 0.5 Hz dwell-then-jump 21 events over the grid (P2 2, E2-A3 3). ±1° 0.2 Hz in-phase gain 0.75 (P2 0.88). ±0.3° 0.2 Hz in-phase gain at 15–22 m/s 0.31 (P2 0.78). **All members, ≥ 8 m/s:** 271 dwell-then-jump events vs 228. EVIDENCE (sim, §1 V5). | rev2-A M2 / M4 (the operator's words; dwell rate vs r6c). If the operator reports highway micro-ratcheting on small corrections, switch to J-G48d-A3 (§4.3). |
| J-M2 | tracking on the b_q×ms_free member (G-M2) | linear 0.935 at 17 m/s (G's own metric; nominal 0.951). Not in the time scorer's member set. | on-car tracking < 0.95 in the 15–22 band = FAILED (rev2-A §8.2) |
| J-M3 | 20 Hz gain margin (G-M3) | M20 0.965–0.976× V295. M20 is controller-only and frame-exact (G §0.1 item 3), so the ratio is EVIDENCE from bytes. Whether the car's 20 Hz mode responds the same is BELIEF. | R4 (a new narrowband 5–30 Hz line → REVERT) |
| J-M4 | 5 Hz damping (G-M4, rev2-A M14) | −0.05 T per deg/s where V295 damps at +2.46: the least anti-damping on the panel | F7 > 0 → REVERT |
| J-M5 | low-speed turn-hold (M-E2-1b) | P2's below 6 m/s (0.90–0.95 at a 1.0–1.5) | operator words ("looser at low speed") |
| J-M6 | road load at θ ≈ 0 (M-E2-4) | the I is capped at 200 T + slope·\|θ\|; the excess becomes a P steady error. Never seen on r71b. | steady hands-off error > 1° on a straight ≥ 12.5 m/s → REVERT |
| J-M7 | engage droop (M-E2-7) | 6.0° at 8 m/s (b_lo×J_hi) | — (4.3° with the 6803 == 2 overlay, a separate decision) |
| J-M8 | low-speed stick-slip (the frontier, rev2-A M1) | unchanged from every candidate: hunting in 10 columns below 8 m/s (P2 7) | the operator's words |
| J-M9 | 510 ms timeout mid-motion (F4) | 2.41° at 10–12.5 m/s (P2 2.27°) | declared, as round 2 |
| inherited | F5: the stock camera on a relay close; pol = −1; FB frame in the time domain; aged hold and b_q / ms_free / J1.0 in the time domain | not simulable / not run (§7) | procedure + fork B3 gate; the R1 INVERTED check on the first drive |

#### Instrument

No new telemetry bit; both parents' reads apply:

- **The bound:** E2 §8's one deliberate light-hand episode. The I component stays flat in a 3 s light hold; a ramp means
  NOT LIVE.
- **The D re-size:** G §8.2, c_D on ω_18F in **0.45–0.70** (P2 0.40). The frame shows in the angle dependence of that
  coefficient.

#### What a FAIL looks like before any build ("do not flash")

- **E2's H-E2-1..4.** Note that H-E2-2 is re-based: GATE 2 on the built cells must equal **G-P48's** row (0 fails), not
  P2's.
- **G's G-H1..H5.**
- **Graft-specific:** the built cave's table must parse to G-P48's rows exactly (V1's negative control is the check).
- **Graft-specific:** `judge_grafts.py report` on the built constants must show 0 goal-fail bands ≥ 8 m/s.

### 4.2 J-G44-A3 (alternate: more 20 Hz margin)

**What it is:** the same cave with G-P44's rows and Kd 44.

**What it buys:**

- M20 0.884–0.895× (a 10–12 % margin);
- 5 Hz −0.14;
- 0 R2-box fails.

**What it costs** (EVIDENCE, sim):

- ±1° dwell-then-jump ≥ 8 m/s: 305 events vs 271. Nominal 0.5 Hz at 12.5–22 m/s: 32 vs 21.
- In-phase gain 0.66.
- Timeout excursion 2.54° (8–10 m/s; the primary's is 2.41°).

**Score:** tied with the primary (88.8 vs 88.7).

**Choose it only if** the orchestrator weighs the BELIEF-grade 20 Hz plant response above highway small-correction
precision. The controller's 20 Hz gain itself is under V295's in both, as EVIDENCE.

### 4.3 J-G48d-A3 (alternate: small corrections first; needs the b_q×ms_free ruling)

**What it is:** the same cave with G-P48d's rows.

**Frequency** (EVIDENCE: SCORE-FREQ T0/T1):

- 166 R2-box fails, **all on b_q×ms_free**: PM 17.0° (15.2° with tau6), ring 1.28 Hz, ζ 0.061.
- These are **declared, and covered by R3\*** (ζ < 0.10 → ≥ 4 visible cycles → REVERT).

**Time** (EVIDENCE, sim):

- **Small corrections stay P2-class:**
  - nominal ±1° 0.5 Hz dwell 6 events at 12.5–22 m/s (vs 21);
  - ±0.3° in-phase gain at 15–22 m/s 0.78 (vs 0.31);
  - dwell ≥ 8 m/s: 226 events.
- Linear tracking on b_q×ms_free 0.961 (G).

**The trade, which G framed and my run confirms in the time domain:** closing b_q×ms_free by the table costs highway
small-signal stiffness on the **nominal** plant. **This is the orchestrator's credibility ruling on a two-stress-corner
member.**

**My lean is the primary (GATE-2-clean), because:**

- the R3\* stop band detects the ring only after the car has shown it;
- GATE 2 is the kit's safety gate;
- J-M1 is a precision cost that one drive can read.

### 4.4 ICL 12288 (J-G48-A3-12k)

- **Gain:** +0.012 replay tracking at 8–15 m/s (0.992 vs 0.980), and E2's a_lat-3.5 hold margin (0.993 vs 0.905–0.928
  in E2's T1; I did not re-run a 3.5).
- **No lurch cost** in any scored case, because the bound binds first.
- **Cost:** the worst-case I authority rises from about 1313 T to about 1969 T where the bound is above the clamp.
  That is large wheel angles at 6–12.5 m/s, and any state in which the bound is defeated. **BELIEF** that this matters:
  no scenario exercised it.
- **Not recommended for the first flight. 0 bytes to add later.**

### 4.5 Overlays, not scored as part of the graft (each is a separate decision)

- **6803 == 2 (E2-A2-X).** Engage droop drops by a third, and it enables E2's +20 B firmware camera gate (A2S-C, F5).
  The `0xCBAE4` fade arm raises lane torque against a firm hand by up to ×2.1. **Not in the primary.** H's
  recommendation (A2 skip + fork B3 gate + camera-LKAS-off procedure) covers F5 without it.
- **E2's opposing-hand freeze (A2S, +16 B).** Halves co-steer release droop and the torque-source-hand lurch, for −0.006
  of tracking. **Not scored on the common scorer** (A2S is not a column there). Optional.

### 4.6 A round-3 design graft (BELIEF; not scorable now)

**What it would be:**

- H-A's **fresh gp-0x69ca** P/I operand: hold-age-free, Re(T/ω) −0.40 flat.
- A **G-style table refit** under ms_free×.
- **E2-A3's bound without H's bleed.**

**Why it is not a primary candidate:** it needs the fork SR fold, an assembled listing, and a refit nobody has run.

**Why it is worth keeping:** it is the only route on the panel to an angle loop whose margins do not depend on slot-4
timing.

### 4.7 Not grafted, and why

| candidate graft | why not |
|---|---|
| E1's firm reset onto A3 | The graft's firm lurch is already 3.2°. The reset adds a RAM write for < 1°. |
| H's bleed | Fails replay tracking wherever it is applied (SCORE-TIME §0 item 3). |
| G-F24's held D | Removes the pol dependence, but 13 Hz anti-damping is 1.9× V295 and small corrections are the worst of the grafts. Kept only as a pol-free fallback (J-F24-A3, mirror only). |

---

## 5. Disqualifications

| id | why (EVIDENCE) |
|---|---|
| **E1-splitP** | ρ = 1.0000, ζ ≈ 0, on b_q×ms_free+h10 at 19 m/s. 5052 R2-box fails including nominal (tier A 22.3°). Turn-hold 0.755. Its designer rejects it. (SCORE-FREQ F6, SCORE-TIME fails table.) |
| **E1-bleed** | Fails the goal's tracking in **every** band once r71b's own torque word is replayed (0.739–0.829). It drains the hold the raised ICL added. Its designer rejects it. No hex. (SCORE-TIME §5.1.) |
| **E2-K0** | No firmware I. The DC needs a fork angle integral, which is fork code beyond the angle interface. Real-curve hold 0.652; tracking 0.915 at 15–22 m/s; light lurch 20° at ≥ 8 m/s and 51.7° below; 42° with a 3 s hold. Its designer does not offer it. |
| **E1-sched** | Fails tracking in every band (0.886 / 0.928 / 0.941) and turn-hold in 3 bands. No hex. Its designer rejects it. |
| **E2-L** | Fails replay tracking at 8–15 m/s (0.938) and the lurch gate in 4 bands. Its designer rejects it. |

Not disqualified, but **superseded**:

- **The round-1 four.** Refuted on both scorers.
- **H-A and H-B.** No listing; published numbers do not describe the loop; undeclared failures.

---

## 6. Disagreements and notes (the judge's own)

| # | item | finding |
|---|---|---|
| D1 | **The common time scorer is not batch-invariant at the noise level.** SCORE-TIME says *"every column saw bit-identical inputs"*. | `run()` draws the 2.8-count sensor noise as `rng.normal(0, noise, B)` per tick, so each column's noise realisation depends on the batch width B and the column's position. EVIDENCE: my in-batch controls differ from SCORE-TIME by up to 0.11 in noise-dominated metrics (texture under road noise, the ±0.3° stick-slip gains) and by ≤ 0.002–0.02 in every decision-bearing metric. Every per-band fail list is identical. **Not decision-bearing here.** A future scorer should draw per-column noise from a per-column seed if cross-batch comparisons are to be exact. |
| D2 | E2's "the policy block carries over to any skeleton" | **Confirmed in the time domain on three skeletons** (G-P48, G-P44, G-P48d). The bytes check is 0 / 3000 on each. The lurch bound even improves (5.8 → 4.1°) because G's larger D damps the return. EVIDENCE. |
| D3 | G's "every implementation passes every pre-registered bar" | True of rev2-A's bars (SCORE-TIME §6 item 6). Against the goal, all fail F1. With E2's policy grafted, all of G-P48 / P44 / P48d pass the goal's time criteria. G's claim that F1 is "not this axis" is borne out. |
| D4 | E1's M6-E1 "~17°" | Under-quantified: SCORE-TIME measures 24.3° at 10.25 m/s. Deducted under C, not A. |
| D5 | H's published H-A margins and "fully stacked residual" | SCORE-FREQ §3 C9 is right: H scored a different loop and double-aged the +h10 members. Deducted under C. |
| D6 | The rubric weights are mine | The ranking of designer candidates is robust to them, because fail bands dominate. The order of the top three grafts is not robust (1.8 points apart). It is decided by the rulings in §4.2 and §4.3, stated as rulings. |

---

## 7. What no scorer decided (open before any build)

- **F5, the stock camera's 0xE4 on a relay close.** Not simulable. Procedure (camera LKAS off) plus the fork B3 gate;
  or E2's firmware camera gate with 6803 == 2 and its ×2.1 hand-authority cost. **An orchestrator decision.**
- **pol = −1.** The fresh-D sign rests on gp-0x6752 = −1 (record EVIDENCE, this car only). The image must not go to
  another car. R1 INVERTED catches it on the first drive.
- **The time domain has not run, for any candidate:**
  - the aged hold (+h10);
  - FB plant-frame reading;
  - κ 0.83;
  - the ms_free, b_q and J1.0 members;
  - a_lat 3.5.

  The grafts carry those only through the frequency scorer, where they pass (or are declared, for J-G48d-A3).
- **Not decidable without V282:** dwell-then-jump ≤ V282, and hard-turn energy ≤ V282's. Relative to the panel, the
  primary's hard-turn ratio is the lowest among the goal-passing designs (1.07 vs 1.43). Its dwell count is higher
  than P2-class (J-M1).
- **Low-speed stick-slip ("gone") is met by no candidate.** Every column hunts or sticks below 8 m/s. It is the declared
  frontier. The grafts do not change it.
- **κ (torque-word counts per T count) is unmeasured** (E2). The ARB bound is κ-independent by construction, which is
  why it is preferred.

---

## 8. Files and reproduction (all `python`, the bin_decompile env)

| file | what |
|---|---|
| `analysis-2020accord/studies/angle_loop/panel2/JUDGE-goal/judge_grafts.py` | Registers the grafts on the common time scorer (imported unchanged). `h1` runs the bytes check with its negative control. `run [procs]` runs the full 22-scenario grid in frame `vgr` (≈ 6 min on 13 processes; caches in `_scratch/angle_loop/judge-goal/grid`). `bridge` runs the 3 s-hold override bridge. `report` writes the tables plus `_scratch/angle_loop/judge-goal/judge_summary.json`. |
| `…/JUDGE-goal/judge_score.py` | The rubric of §2 applied to the scorers' summary JSON and the graft summary. Writes `judge_score_table.md` and `judge_score_out.json`. |
| `…/JUDGE-goal/judge_tables.md` | The common scorer's own tables for the four controls and five grafts. |
| `…/JUDGE-goal/judge_bridge_ov3.md` | The 3 s-hold bridge. |
| `…/JUDGE-goal/h1_grafts_out.txt` | The bytes-equal-lane check, with its negative control. |
| `…/JUDGE-goal/judge_score_table.md` | The full 35-row score table (designer candidates and grafts). |

**Order to reproduce:** `python judge_grafts.py h1`, then `run 13`, then `report`, then `bridge`, then
`python judge_score.py`.
