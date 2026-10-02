# RE-REFUTE V299 rev 2: stability and nonlinear behaviour (2026-10-02)

**Target:** `docs/specs/design/v299/DESIGN-V299-SYNTHESIS-rev2-2026-10-02.md`. This is V298 + 67 B: a two-level A3 cap
(4096 S at v ≤ 1382, 6144 S at 1382 < v ≤ 2880), the hard freeze at 1229, no opposing clause, and the asymmetric bound. The fork
is config A with **no override** (ruling (i)).

**Role:** RE-REFUTER, stability and nonlinear, a SUBAGENT. This is ANALYSIS ONLY. Nothing was built, flashed or sent, and no fork,
firmware, golden-model, STATE, lineage or git file was touched.

**Method:**
- Python is `bin_decompile`.
- Ghidra was not needed. I executed the rev-2 cave bytes directly with the kit's V850E2 interpreter (control C1).
- The engines are my colleague's `rsn_engine.py`, imported **unchanged** (not the reviser's source-substituted copy), and S2 through
  the reviser's loader. I proved the S2 loader equal to my lane (C2).
- Scripts are in `refute/rev2sn/`, outputs in `_scratch/v299_RR2SN/`.

**Classifier interruptions:** 0.

## VERDICT: **FAIL — do not build/fly the brief as specified.**

**What fails is NOT the firmware.** The two-level cap and the 67 bytes survived every dynamics attack I made:
- The rev-2 bytes equal my lane (0/4000 mismatches).
- F4 holds at ≥ 45° in both engines and all three plan shapes.
- There is no relay, and nothing changes at the speed edges.
- Note 2 is carried.
- The 4–8 Hz readout and stall-surges are better than V298's.
- The ms_free ring is gone below 12.5 m/s.

**What fails is the brief's hand and release layer under the no-override fork.** Two pre-registered criteria fired (§0):

- **RC, the design's own revert criteria fire by construction on drive-card items.** Rev 2 carried rev 1's F3 and F5 text across
  the fork change, but rev 1's text assumed the O1 override made θsp follow the hand. With no override:
  - **F3 as written** ("\|θ − θsp\| > 8° within 1.5 s after a release at ≥ 8 m/s") reads the hand's own displacement at the release
    instant. It fires on every drag or hand-steer that moves the wheel more than 8° from the path at ≥ 8 m/s:
    - 8 m/s: 15.5°; 10 m/s: 14.9°; 12.5 m/s: 9.9° (deviation at release, R2);
    - this is card item 3's "one firm grab and a hand-steered turn".
  - **F5 as written** ("a light-hand episode … *ends* > 4° behind θsp toward centre") reads the hand's hold. It fires on a light
    centre-ward co-steer: R2 8.5–8.7° at 5 m/s and 5.6–5.8° at 8 m/s, for every word 300–1150, at a 1-s hold. This is card item 3's
    "light 1–2 s co-steer hold then release at ~5 m/s".
  - The page "predicts" both as not firing, but it predicts them with **different metrics**: S2's post-release swing and the droop
    1.5 s after release.
  - **F4's re-scope is self-contradictory.** The page's own range for 30° at ≤ 4 m/s (4.1–6.8°) crosses the 6° bar it keeps. My
    engines give 6.9–7.0° (b_lo×J_hi, linear plan, 3 m/s, RSN 2/12, S2 1/12 columns). The rewritten text ("> 15 % on a turn
    ≥ 45°") also deletes the % clause **everywhere**, because 15 % of 45° is 6.75° > 6°. That is not only at ≤ 4 m/s. Rev 1's
    clause would also fire at 5 m/s (4.6° on a 30° turn).
- **RE, light-hand outward release.** Both engines agree within 0.3°:
  - **> 8° at ≥ 8 m/s on the heavy member:** 9.9° at 8 m/s on a 20° hold, 9.7° at 10 m/s on a 15° hold.
  - **> 1.5° worse than the page's prediction at a card speed:** at 15 m/s on an 8° curve (a gentle highway curve,
    a_lat ≈ 0.65 m/s²), the 2-s hold gives 5.3° heavy / 3.3° r79F, and the 4-s hold 6.5° / 4.8°. The page says "≤ 2.0°".
  - The page computed its numbers at S2's small hold angles (0.5·A_turn: 4.3° at 15 m/s) and 1.5–2 s holds. The swing grows with
    the hold angle and the hold age, because the I unwinds from its holding value +X toward −B = −1250 S while the hand holds the
    wheel outward. The swing ≈ (X + 1250) S / stiffness.
  - This is the **N1 class at a new amplitude**, and it is inherent to "no freeze below 1229 + no override". My colleague's D8 was
    5.0–5.8° at 8 m/s under the G4 fork; it has **grown**, not been resolved.

**Path to PASS (BELIEF; nothing in the firmware needs to change for items 1–3):**

1. **Rewrite F3/F5 relative to the release state.**
   - F3 = the excursion *past the setpoint, away from the hand side*, in the 1.5 s after release (S2's `lurch`).
   - F5 = \|θ − θsp\| toward centre 1.5 s after release.
   - Define the release edge again (rev 1 had one; rev 2 dropped it).
2. **F4:** state that the 6° bar fires at 30°/≤ 4 m/s on the heavy member (predicted 7.0°) and give that cell its own bar, or fix
   the low-speed windup. Restore or delete the % clause explicitly.
3. **Re-size M5/M6 on the page at realistic holds.** Holds of 8 m/s 20°, 10 m/s 15° and 15 m/s 8°, at ages 1–4 s, and curve holds
   of 1.5–3.5 m/s² at 8–10 m/s (§3, §4).
4. **The operator decides (escalation 1) on the predicted heavy-member F3 firing** (9.7–10.0° at 8–10 m/s), before the drive, not
   after. The only firmware remedy is to freeze the I under an opposing light hand, which is the twist-relay class (D4b's LP +
   motion gate).

---

## 0. FAIL criteria, written BEFORE any script ran (`refute/rev2sn/PREREG-rev2-stability-nonlinear.txt`)

| id | criterion (abridged) | fired? |
|---|---|---|
| R0 | a HIGH defect of the first refutation (D1 F4, D2/D3 B relay) is not actually resolved in the DRIVE config on my engine | **no.** D1: 0 F4 columns at ≥ 45° ≤ 10 m/s in both engines and all plan shapes. B is gone and there is no O1: 0 O1, 0 stall-surges (§1, §2) |
| RA | a linear loop rev 2 operates in has PM < 30 / GM < 6 dB where V298 was at the bar | **no.** The inner bytes are identical (C1), the cap only switches PID → PD, and the O1 loop no longer exists |
| RB | a sustained self-excited cycle, including a v-word relay at the new 1382 / 2880 edges | **no** (§5) |
| RC | my engine or S2 predicts one of the design's OWN revert criteria firing on a card manoeuvre or inside the r79 envelope, where the page predicts it does not (or is > 1.5° / 25 % smaller) | **YES:** F3 and F5 as written, by construction; F4's 6° bar at 30°/3 m/s against the page's own range |
| RD | F4 at ≥ 45° ≤ 10 m/s in either engine, linear or raised-cosine | **no** (worst 5.2° at 45°/3 m/s) |
| RE | light-hand release lurch > 8° at ≥ 8 m/s, or > 1.5° worse than the page at a card speed, or F5 > 4° | **YES:** heavy member 9.7–10.0° at 8–10 m/s; 15 m/s 5.3° vs "≤ 2.0"; F5 literal |
| RF | config A alone does not carry note 2 (t90 not ≥ 25 % faster than V298 at 3–8 m/s on both members, both engines), or 4–8 Hz / stall-surges worse | **no.** t90 is ×0.28–0.63 of V298's (§2) |
| RG | ms_free ring at 10–12.5 m/s larger than V298's, or "no ring ≤ 12.5" false | **no** (§4). Shortfall replaces the ring, larger than the page sizes it (defect) |

---

## Controls — the engine is the bytes (EVIDENCE, `rsn2_control.py`, 13.6 s)

| control | result |
|---|---|
| C1: the rev-2 cave **bytes** (`V299R2_DISASM_ONLY_NOT_AN_ARTIFACT.bin`, sha `30ff05fa` asserted; the 260 B at 0xC4C00 = `rev2_cave.hex`), executed by `score_time.Cpu2` (via `rev_h1.run_bytes`), vs **my** `rsn_engine.Lane` with the two-level variant: freeze decision + E′ | **0/4000** freeze and 0/4000 E′ mismatches. Half the cases are targeted at 1382 < v ≤ 2880, the edges, and \|I\| 2000–9000 S. RAM/registers clean |
| N1: the same bytes vs my lane at rev-1 caps | 66/4000 (the check can fail) |
| C2: my lane R2 vs the S2 lane at `REV2_S2` (the reviser's substituted engine), 9000 ticks × 88 columns, I driven to ICL | **0** T/I mismatches |
| N2: my R2 vs S2 at rev-1 caps | 493,008 (the first attempt gave 0 because random sequences never reached I > 4096. I strengthened it; recorded so nobody reuses the weak form) |
| the scrap image vs V298 | 67 differing bytes (0x1310D, 0xC4C64…0xC4CAB, trailer), as §1.1 |

---

## 1. Prior defects — resolved, or re-worded?

| # (first refutation) | status in rev 2 | evidence (mine) |
|---|---|---|
| D1 F4 at 10 m/s | **RESOLVED** | RSN/S2 at 10 m/s, R2 45/60/90°: max 3.1 / 3.0 / 1.4° (RSN), 3.3 / 2.9 / 1.4° (S2), 0 F4 columns in either. The rev-1 firmware on the same fork (R1N) gives 7.5° [10/12] / 8.9° [12/12], so the cap is what fixes it. At 11.75 m/s 7.7° (V298 16.6 RSN / 11.1 S2); at 12.6–13 m/s 8.0–9.3° (= rev 1 = V298 rule; outside F4) |
| D2/D3/D7 config B relay, X3, A-vs-B | **RESOLVED by removal** | B is not built, and the no-override fork has no O1. 0 stall-surges on every R2 turn-in at 3–15 m/s (V298 0.25–7.1 per turn) |
| D4 ms_free ring | **RESOLVED ≤ 12.5 m/s, declared above** | §4: no F10 firing ≤ 12.4 m/s on any member at 1.5/2.5/3.5 m/s². F10 fires at 12.6–13 m/s on b_lo×ms_free (R2 2.69° first half-peak at 12.6/2.5 vs V298 0.06), as declared (M7). **The price is larger than the page states (new D-N4)** |
| D5 GATE-2 inherited shortfalls | declared (§3.1) | A3 duty 1.00 in ms_free holds ≥ 2.5 m/s² at 8–12.4 m/s confirms "PD there". At 1.5 m/s² the I is below the bound (duty 0.00 at 11–12.4 m/s): PID, but no ring (half-peaks ≤ 0.6°) |
| D6 unwind per member | **RESOLVED** (reported) | R2 unwind past centre ≤ 4.6° at 3–8 m/s on both members, both engines (V298 up to 7.1 / 9.2°) |
| **D8 light-hand outward swing at F3's edge** | **NOT RESOLVED — grew** | 5.0–5.8° (G4) → R2 no-override 8.1–10.3° heavy, 4.5–6.1° r79F at 5–10 m/s (§3) |
| D9 O1 GM at the bar | moot (no O1) | — |
| D10 process | ok | every script here < 30 s, walls in §6 |

---

## 2. Turn-ins over the whole grid (`rr_t1_turnin.py`; RSN 27.7 s, S2 15.8 + 20.6 s)

**Grid.**
- Speeds: 3, 4, 5, 5.9, 6.1, 6.5, 7, 8, 9, 10, 11, 11.75, 12.4, 12.6, 13, 15 m/s.
- Turns: 30 / 45 / 60 / 90°.
- Plans: linear at the planner rate, raised-cosine 1 s, raised-cosine 2 s.
- Members: r79F and b_lo×J_hi.
- Seeds: 2 per engine.
- Hold 4 s, then unwind.

**Systems.** V298 (V298 fork); **R2** = rev 2 + NoO1 = THE DRIVE; R1N = the rev-1 firmware on NoO1 (attribution).

**F4 (rev-2 text) at ≤ 10 m/s, R2:** 0 columns at 45/60/90°, in both engines and all plans. The worst cells:
- 45°: 5.2° at 3 m/s; 4.6–4.7° at 6.1 m/s (just above the 1382 edge: the 6144 cap starts here).
- 30°: **7.0° at 3 m/s (RSN 2/12, S2 1/12)** and 5.8° at 4 m/s, both b_lo×J_hi on the linear plan. That is F4's 6° bar, which the page's own
  range predicts (D-N3).

**Note 2 and stutter, linear plan, 60/90°, median [max] (RSN | S2):**

| v | sys | t90 60° | r4–8 deg/s | r1.6–3 deg/s | stall-surges/turn | hold err @4 s | tap LSB max |
|---|---|---|---|---|---|---|---|
| 3 | V298 | 1.44 \| 1.42 | 4.1 [8.4] \| 3.2 [9.6] | 5.3 \| 6.1 | 2.5 \| 1.75 | 0.5 [1.7] | 135 |
| 3 | **R2** | **0.67 \| 0.68** | **0.9 [1.4] \| 1.1 [1.8]** | **3.9 \| 4.7** | **0 \| 0** | 0.5 [1.6] | 132 |
| 5 | V298 | 1.48 \| 1.46 | 4.6 [10.4] \| 5.5 [10.0] | 5.5 \| 6.1 | 4.0 \| 4.4 | 4.3 [7.8] | 161 |
| 5 | **R2** | **0.71 \| 0.72** | **1.0 [1.5] \| 1.2 [1.9]** | **4.0 \| 4.8** | **0 \| 0** | 4.3 [7.1] | 156 |
| 8 | V298 | 1.61 \| 1.89 | 5.5 [8.6] \| 6.0 [13.9] | 5.5 \| 5.6 | 5.3 \| 6.1 | 0.0 [0.2] | 218 |
| 8 | **R2** | **0.67 \| 0.68** | **1.0 [1.6] \| 1.3 [2.0]** | **4.9 \| 5.9** | **0 \| 0** | 2.0 [4.1] | 193 |
| 10 | V298 | 1.25 \| 1.47 | 1.4 \| 1.3 | 3.7 \| 4.1 | 1.9 \| 0.9 | 0.6 [0.9] | 194 |
| 10 | **R2** | **0.96 \| 0.97** | 0.3 \| 0.4 | 2.5 \| 3.0 | 0 \| 0 | 0.1 [0.3] | 169 |

- **Config A alone carries the note-2 gain** (EVIDENCE in sim, both engines, both members). The t90 ratio R2/V298 at 3–8 m/s is
  0.28–0.55 on r79F and 0.46–0.63 on b_lo×J_hi.
- R1N ≈ R2 in t90 (0.64–0.71 s). **The gain comes from the fork and the 1229 freeze, not from the cap.** The cap's job is F4.
- **The 1.6–3 Hz readout**, which the page left as "—" for the DRIVE row: R2 is **lower** than V298 at every speed in both
  engines (3.9–5.9 vs 4.9–6.5 deg/s at 3–8 m/s). Ruling (ii) retired that criterion, and this is recorded so the omission is closed.
- **The cap's cost at 6.1–8 m/s.** Hold error at 90° is 3.5–4.7° (page 3.9–4.3), and the unwind past centre is ≤ 4.6°.
- **Tap.** The peak is 207 LSB (at 15 m/s, = V298), < 250. The page's "predicted peak ≈ 175–180" is low: the 6–8 m/s turn-ins
  reach 184–193 (D-N6).

---

## 3. Hands on the no-override fork (`rr_t2_hands.py` 9.7 s, `rr_t2b_s2hands.py` 9.3 s, `rr_t3_straight.py` 8.0 s)

**Setup.**
- Hold at the curve angle: 5 m/s 30°, 8 m/s 20°, 10 m/s 15°, 12.5 m/s 10°, 15 m/s 8°, 25 m/s 4°.
- The hand ramps on over 0.3 s, holds 1 or 4 s, and releases.
- Words 300–1150 raw (no freeze) and 1500 / 2500.
- Directions: centre-ward (c), outward (o), drag to centre (ov).
- Hand models: a stiff position hand (S2's) and a constant force at 0.29 T/word (BELIEF).
- Both members.

**Outward light co-steer, release swing past the setpoint (the page's lurch metric), max over words 550 and 1150, both engines.**
Engine agreement is within 0.3°.

| v / hold | member | V298 age 1 / 2 / 4 s | **R2 age 1 / 2 / 4 s** | page |
|---|---|---|---|---|
| 8 m/s / 15° (S2's own) | r79F · heavy | 0.5/1.4/2.4 · 3.0/3.8/5.1 | 4.5/4.5/4.5 · **8.1/8.1/8.1** | "8.0° at 8 m/s, r79F ≤ 4.4, heavy ≤ 9.6" ✔ |
| 8 m/s / 20° | r79F · heavy | 0.9/2.0/3.1 · 3.9/4.6/6.4 | 5.6/5.6/5.5 · **9.9/9.9/9.8** | — |
| 10 m/s / 15° | r79F · heavy | 0.4/0.8/1.8 · 2.1/2.9/4.0 | 4.4/**6.1/6.1** · 8.4/**9.8/9.7** | not run |
| 15 m/s / 4.3° (S2's) | r79F · heavy | ≤ 0.3 · ≤ 1.0 | 0.4/1.4/3.0 · 1.5/2.7/4.4 | "≤ 2.0" |
| 15 m/s / 8° | r79F · heavy | ≤ 0.8 · ≤ 1.9 | 1.4/3.3/4.8 · 3.0/**5.3/6.5** | "≤ 2.0" ✘ (card item 3 speed) |
| 25 m/s / 4° | r79F · heavy | ≤ 0.3 · ≤ 0.8 | 0.8/1.8/1.9 · 1.9/2.8/2.8 | "≤ 2.0" (heavy 2.8) |

**Mechanism (EVIDENCE from the bytes' rule, which C1 shows my engine executes).** Under an outward hand E′ is opposite to θ, so the
asymmetric bound is B = 1250 S. The I unwinds from its holding value +X down to −1250 S while the hand holds the wheel. On release,
self-alignment plus the negative I swing the wheel past the path toward centre.

V298 avoided this for words > 300 only through the opposing freeze, which is the twist relay ruled out. At ≤ 300 words V298 swings
16–20° (R2 ≤ 10.3°). **R2 is better than V298 for the weakest hands and worse for 550–1150 words.**

**On a straight (F3's straight clause)** R2 never fires (0/360; max 4.1° at 8 m/s, ≤ 2.0° at 15–25 m/s; V298 15/360, max 9.9°). The
asymmetric bound works exactly where it was designed to.

**Criteria as written vs their predictions (D-N1):**

| criterion (text) | what it reads with no override | R2 sim | page prediction (metric used) |
|---|---|---|---|
| F3 "\|θ − θsp\| > 8° within 1.5 s after release, ≥ 8 m/s" | the hand's displacement at the release instant | drag to centre: 15.5° (8 m/s), 14.9° (10), 9.9° (12.5); fires on every drag > 8° | "8.0° … at the bar" (post-release swing) |
| F5 "light-hand episode *ends* > 4° behind θsp toward centre" | the hand's hold | 8.5–8.7° at 5 m/s, 5.6–5.8° at 8 m/s, every word 300–1150, age 1 s | "back within 1° in ≤ 0.3 s" (post-release droop: ≤ 1.9° in my run) |

**Moderate band (F7b; declared, escalation 1).** On my larger holds: drag to centre at 5–8 m/s with 300–1150 words gives a tap
opposing the hand of 68–82 % max and 55–63 % residual (page 53–75 / 47–60). Hand force is 1329–1677 T (page 1128–1442). The longest
F7b run is **1540 ms** at 8 m/s, 800 words (page 820–840). Centre-ward 5 m/s 800 words: 833 ms. Same sign and class as the page,
somewhat larger. The F7b firing is declared, so it is not counted as a FAIL.

---

## 4. ms_free curve hold and the cap's hold cost (`rr_t4_msfree.py`, 17.5 s)

**Setup.** 8–14 m/s × a_lat 1.5 / 2.5 / 3.5 m/s² × {b_lo×ms_free, b_lo×ms_free_r79F, ms_free_r79F, r79F}; age 10 ms; twist
residual on; 1° step at 4 s; F10 computed as written (0.4–0.8 Hz band-pass).

- **F10 ≤ 12.4 m/s: R2 never fires** (V298 fires at 11.75–12.4 m/s on b_lo×ms_free 3.5 and b_lo×ms_free_r79F 2.5, and at 8 m/s r79F 3.5). The ring is
  gone because the I sits at the bound (A3 duty 1.00).
- **Above 12.5 m/s:** R2 fires at 12.6 m/s (2.5 and 3.5 m/s²) and 13 m/s (2.5) on b_lo×ms_free, where V298 fires only at 3.5. This is
  declared (M7/F10).
- **The price, steady hold shortfall (sp − θ), R2 vs V298:**

| member | 8 m/s 1.5 / 2.5 / 3.5 | 9 m/s | 10 m/s | 11 m/s | page |
|---|---|---|---|---|---|
| r79F (nominal) | **0.8 / 3.2 / 3.9** (V298 ≤ 0.1) | 0.1 / 0.9 / 1.7 | ≤ 0.1 | ≤ 0.3 | 90° at 6.5–8: 3.9–4.3 ✔ |
| ms_free_r79F | 3.2 / **6.4 / 7.4** | 2.0 / 5.8 / 7.3 | 0.6 / 5.1 / **7.3** | 0.4 / 2.8 / 5.4 | **not run** |
| b_lo×ms_free_r79F | 3.6 / 6.3 / 7.4 | 1.3 / 4.0 / 5.7 | 0.5 / 2.7 / 5.3 | 0.3 / 1.9 / 2.9 | "+1.4 to +2.8 at 10–12.5" (2.5 only) |
| b_lo×ms_free | 2.3 / 5.3 / 6.3 | 0.8 / 4.3 / 5.4 | 0.0 / 3.5 / 4.9 | 0.0 / 1.8 / 3.3 | "+3.4 / +1.8 / +0.4 / +2.7" ✔ at 2.5 |

The angles involved are large (8 m/s, 2.5 m/s² ≈ 108°), so the shortfall is 3–7 %.

The page's M6 ("ms_free holds 1.4–3.5°") is sized at 10–12.5 m/s and 2.5 m/s² only. At 8–10 m/s and 3.5 m/s² it is **×2**
(5–7.4°). The drive read's item 6 and the null sentence (> 3° → 7168) cover it, but the page should print the real size (D-N4).

---

## 5. The new speed edges — a relay? (`rr_t5_vedge.py`, 13.7 s)

**Setup.** A curve hold at 6.0 and 12.5 m/s (r79F, b_lo×J_hi, ms_free_r79F; 1.5 / 2.5 m/s²). The v-word is held at one side, jittered
±2 counts at 100 Hz, or ramped ±0.5 m/s through the edge.

- **1382:** R2 shows 0.0 freeze toggles/s and 1–10 Hz wheel rate 0.00 deg/s, at either side and under jitter. The I simply waits at
  4096 or 6144. A speed ramp moves the I 4100 → 6150 once (1–10 Hz 1.4–2.2 deg/s from that single move; V298 0.9–9.3).
- **2880:** jitter toggles the freeze at **33–45 /s** on ms_free_r79F, but the 1–10 Hz rate is 0.01–0.09 deg/s and the error is ≤ 0.5°.
  The cave only gates the I increment, and never writes I (EVIDENCE: §1.3's listing; FRZ returns r6 = 0 except on the camera path),
  so a toggle carries no torque step. V298 toggles 27 /s at the same point. **RB does not fire.**
- **Instrument note (LOW):** these A3-edge toggles are not 1229-freeze onsets. F6b's "freeze onsets" readout must count only
  \|w\| > 1229 freezes, or it will be inflated at 12.5 m/s.

**Also confirmed** at 6.0 m/s, v ≤ 1382: the inherited 4096 cap leaves a 9–27° shortfall on 115–190° low-speed curves on every
member, R2 ≈ V298 (V298 adds a 15 deg/s oscillation on b_lo×J_hi that R2 does not have). That is the page's M6 "inherited ≤ 6 m/s
ceiling", unchanged and recorded.

---

## New defects (most severe first)

| # | what | where | sev | fix |
|---|---|---|---|---|
| D-N1 | F3 and F5 as written fire **by construction** under the no-override fork on card item 3. F3 reads the drag distance at release (9.9–15.5° at 8–12.5 m/s); F5 reads the co-steer hold (5.6–8.7° at 5–8 m/s). The page predicts both with different metrics. Rev 1's F3 release-edge definition was dropped | rev 2 §7 F3, F5; §6 item 8 | **HIGH** | Redefine both relative to the release: F3 = the swing past θsp away from the hand side in 1.5 s; F5 = \|θ − θsp\| toward centre 1.5 s after release. Restore the release-edge definition (pressed falling edge or \|word\| > 300 for ≥ 0.5 s). Re-score with the same scripts |
| D-N2 | **The outward light co-steer release lurch is under-sized, and it grew from D8.** Heavy member 8.1–10.3° at 5–10 m/s (> F3's 8° at 8–10 m/s); r79F 4.5–6.1°. At card speed 15 m/s on an 8° curve with a 2–4 s hold: 3.3–4.8° (r79F) / 5.3–6.5° (heavy) vs the page's "≤ 2.0" | rev 2 §3.5, §7 F3 prediction, M5 | **HIGH** | Re-size at realistic holds (15 m/s 8°, 10 m/s 15°) and ages (1–4 s). The operator decides, before the drive, whether a predicted heavy-member F3 firing is acceptable. The firmware remedy (freeze I under a light opposing hand) is the twist-relay class: D4b's LP + motion gate |
| D-N3 | F4's re-scope contradicts itself. The page's own 30°/≤ 4 m/s range (4.1–6.8°) crosses the kept 6° bar (mine 7.0°). The "≥ 45°" wording deletes the % clause at every speed, not only ≤ 4 m/s (rev 1's clause also fires at 5 m/s, 30°: 4.6°) | rev 2 §7 F4, M4, escalation 5 | MED | State the predicted firing, or give 30°/≤ 4 m/s/heavy its own bar (e.g. 7.5°). Make the % clause's fate explicit |
| D-N4 | The cap's hold shortfall is under-sized. ms_free family 5.1–7.4° at 8–10 m/s, 2.5–3.5 m/s² (page "1.4–3.5"); nominal r79F 3.2–3.9° at 8 m/s, ≥ 2.5 m/s² | rev 2 §3.3–3.4, M6 | MED | Print the real size. The drive read's item 6 / null sentence already reads it |
| D-N5 | The A3-edge toggles at 2880 (33–45 /s under v-word jitter, harmless) could inflate a freeze-onset count | §6 item 4, F6b | LOW | Count only \|w\| > 1229 freezes in F6b |
| D-N6 | Tap peak predicted "≈ 175–180"; sim 184–193 at 6–8 m/s and 207 at 15 m/s (= V298). F9 (250) holds | rev 2 F9 | LOW | Correct the prediction |
| D-N7 | The DRIVE row omits r1.6–3. Mine: R2 < V298 in both engines (3.9–5.9 vs 4.9–6.5 deg/s at 3–8 m/s) | rev 2 §3.2 | LOW | Fill it in from §2 |

**Inherited and still declared (not new):**
- GATE 2: ms_free PM 6.1–6.3°, and r79's D-fraction PM 1.6° / 24.5°.
- The ≤ 6 m/s 4096 ceiling.
- F7b firing on a moderate drag (escalation 1).
- The ms_free ring above 12.5 m/s (F10/M7).

---

## 6. What I ran (all < 30 s; scripts in `refute/rev2sn/`, outputs in `_scratch/v299_RR2SN/`)

| script | does | wall |
|---|---|---|
| `rsn2.py` | setup: my engine unchanged + NoO1 fork + two-level variant; S2 via the reviser's loader | — |
| `rsn2_control.py` | C1 bytes vs my lane; C2 my lane vs S2-rev2; negatives | 13.6 s |
| `rr_t1_turnin.py RSN` / `S2 lin` / `S2 rc` + `rr_t1_report.py` | §2 grid | 27.7 / 15.8 / 20.6 s; < 1 s |
| `rr_t2_hands.py` + `rr_t2_report.py` | §3 hands, my engine | 9.7 s; < 1 s |
| `rr_t2b_s2hands.py` | §3 S2 cross-check at two hold angles and three ages | 9.3 s |
| `rr_t3_straight.py` | §3 straight-road nudges | 8.0 s |
| `rr_t4_msfree.py` | §4 | 17.5 s |
| `rr_t5_vedge.py` | §5 | 13.7 s |

**Not modelled (declared).**
- The hand models are BELIEF: S2's stiff hand and the force hand at 0.29 T/word.
- The plant family matches route 79 only at 10–13 m/s.
- The twist fit has R² 0.31.
- The v-word noise (±2 counts) is assumed.
- No 13–22 Hz plant mode exists in the family.
- The fork's path loop does not re-ask for missing angle in these sims (fixed plan). That could reduce the D-N4 shortfall on the car
  (BELIEF).
