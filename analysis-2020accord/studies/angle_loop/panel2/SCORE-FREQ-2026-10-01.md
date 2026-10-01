# SCORE-FREQ, panel round 2: common frequency-domain scoring of every candidate (2026-10-01)

**Status: ANALYSIS ONLY.** Nothing was built, flashed or sent. The fork was not touched, and nothing was committed.
Ghidra was not used: every G(v) table was parsed in Python from the cave hex each designer published (table address
taken from the cave's own `mov imm32, r9`). The image cals come from `lane_mirror_v295.load_cal`, which reads the V295
image little-endian and asserts its sha256 `5c044d65…`.

**Author:** the orchestrator's **common frequency-domain scorer**, a subagent of `main`. Designers do not grade their own
work here. Every candidate is re-derived from its bytes and cals and run through ONE pipeline: the same controller
FRF, plant family, member set, frame box, speed grid, hold ages and metric extractor.

**Script:** `analysis-2020accord/studies/angle_loop/panel2/score_freq.py`. Its outputs go to `_scratch/angle_loop/panel2-score/`
(gitignored, regenerable): `arr.npz` (every point), `score_freq_summary.json`, `score_freq_tables.md` (= the appendix
below) and `claims_out.txt` (§3).

**How claims are marked:** every decision-bearing claim is **EVIDENCE**, with its method, or **BELIEF**. Code is cited by
grep string. Frequency-domain results are linear: the integrator clamp (ICL), friction, the hands-on policies and
tracking on real paths belong to the time scorer.

---

## 0. The answer on one page

### 0.1 The gate this round

**R2 box** is the brief's credible set, extended as follows:

- **Added members:** ms_free × {b_lo, b_q}.
- **Hold ages:** every member at both 1–10 and 11–20.
- **Speed grid:** 1–35 m/s in 0.25 m/s steps, plus the knots 3.1 / 8.0 / 11.9 / 17.0 / 26.9.
- **Frame box:** the D-operand ratio is a gated uncertainty. κ = 0.83 / 1 / 1.155 under reading FA, and κ = 0.83 /
  1.155 under reading FB (J and b × 1/1.155 in θ coordinates; this is the stability refuter's second reading).
- **Bars:** tier A PM ≥ 45° and tier B PM ≥ 30°. Both tiers also need GM↑ ≥ 6 dB, |T_c|/|T_ref| 5–30 Hz ≤ +3 dB, and
  L20 ≤ V295's L20 on the same member and frame.
- **Aged single corners:** tier B by the panel convention. The strict reading (bar 45°) is reported alongside.

Other columns report:

- the round-1 set (R1);
- the brief's literal extension (R2 lit: FA only);
- G's extra × tau6 products;
- the physical frame points (κ = 1/1.155 near centre and 1/0.962 outward, under FA and FB).

### 0.2 The result in one table

Full detail is in T0–T9 in the appendix.

| class | candidates | small-signal loop | R2 box fails | what binds | frequency-domain verdict |
|---|---|---|---|---|---|
| **round-1 four** | P2, D2a / F2, B0r | own | **690 / 702 / 691 / 706** | brief's own members: tier A 42.3° (J_hi κ0.83); tier B 26.1° (b_lo×J_hi+h10). ms_free×: 8.2° (b_q, 1.27 Hz, ζ 0.028) | refuted by the frame box and by ms_free×. Refuter F1 and F4 reproduced to 0.1° (§3 C5) |
| **integral policy, E1** | E1-reset, E1-cal, E1-bleed, E1-freeze, E1-sched | **= P2** | **690** (each) | as P2 | **inherits P2's refutation unchanged.** ICL is a clamp, and the reset, bleed and freeze act only hands-on. None changes Kp, Ki, Kd or G |
| | E1-splitP | own (Kp 200) | **5052** | nominal fails; tier A 22.3°; ring at b_q×ms_free+h10 19 m/s with ρ 1.0000 (ζ ≈ 0) | **rejected** (its designer agrees) |
| **integral policy, E2** | E2-R1, E2-S, E2-A2, E2-A3, E2-A2-X, E2-L | **= P2** | **690** (each) | as P2 | **inherits P2's refutation unchanged.** E2 says the same (M-E2-6), and its policy block carries over to any skeleton |
| | E2-K0 | own (Ki 0) | **0** | — | GATE 2 clean, and the fork-integral loop has PM ≥ 77.4° and GM ≥ 14.9 dB. **But its linear turn-hold is 0.878 even with the fork integral (goal ≥ 0.90)**, and its DC stiffness is finite. Not a goal design (its designer agrees) |
| **D operand, G** | **G-P48, G-P44, G-F24, G-A22, G-P48L, G-P48k40** | own | **0** (strict 0, G-strict 0) | tier B 34.2–34.8° (b_q×J1.0+h10, FB κ0.83, 26.9 m/s); ms_free× ≥ 34.8° | **the only candidates with a firmware I that pass the R2 box, the strict reading and G's own extra products.** Costs are in §2 F4 |
| | G-P48d, G-P44d, G-F24d, G-A22d | own | **166 / 169 / 151 / 117** | **only b_q×ms_free**: 16.7–18.3°, ring 1.26–1.35 Hz, ζ 0.058–0.064, 13–22.25 m/s | fail only the declared product. The ring sits inside G's declared R3\* band |
| **whole loop, H** | **H-A** | own (fresh gp-0x69ca) | **352** | **only ms_free×**. b_q: 17.0° (1.34 Hz, ζ 0.069, 12.5–22 m/s). b_lo: 22.3° (**0.84 Hz**, ζ 0.093, 11–12.75 m/s) | passes every brief member across the full frame box. **Hold-age-free by structure.** **The b_lo×ms_free ring lies outside every stop band H declared** |
| | H-B | own | **359** (strict 440) | ms_free× (13.5° / 17.8°), plus b_q×J1.0+h10 at 29.9° (FB κ0.83, 2 pts), plus J_hi+h10 at 41.4° (strict) | fails on more than the declared product |

### 0.3 Decision-bearing findings (detail in §2)

1. **No integral policy moves GATE 2, in either direction.** **EVIDENCE.**
   - Method: every E2 cave carries P2's table byte for byte (hex parse, asserted). E1's byte account changes only ICL
     and hands-on blocks. Every freeze, reset, bleed, leak, angle-bound or clamp-saturated state turns the loop into
     the **I-frozen PD loop**.
   - That PD loop passes the R2 box for every skeleton (0 fails; tier B ≥ 30.9°) and keeps PM ≥ 89.6° at the fade floors
     0.297 and 0.195 (every candidate except E1-splitP).
   - So the E1/E2 policies inherit their skeleton's frequency verdict exactly. **Their skeleton (P2) is refuted.** The
     policy block has to be carried onto a skeleton that passes.
2. **Six G implementations pass the R2 box, the strict reading and G's extra products: G-P48, G-P44, G-F24, G-A22,
   G-P48L and G-P48k40.** **EVIDENCE** (model).
   - Binding point: b_q×J1.0+h10 at FB κ0.83, 26.9 m/s, PM 34.2–34.8°, exact ring 1.86–1.98 Hz, ζ 0.18–0.19.
   - G's own counts reproduce exactly once a duplicate block in G's P2 reference is removed (§3 C6).
3. **H-A's fresh 1 kHz operand removes the hold from the feedback loop.** **EVIDENCE.**
   - The analytic L equals the exact periodic harmonic to 6e-14 (V5).
   - PM is identical at ages 1–10, 11–20 and 21–30. Re(T/ω) is −0.40 flat over 5–25 Hz at every age.
   - It is the only candidate whose margins and anti-damping do not depend on slot-4 timing.
   - It fails only the ms_free products, because it borrows D2a's table, which was never fitted under them.
   - **H's published H-A numbers are a different loop** (§3 C9): H scored the held-operand D2a loop, and double-aged
     every `+h10` member.
4. **The 20 Hz criterion holds for every candidate** (M20 and L20 ≤ V295 at every κ and age 0–30). **EVIDENCE.**
   - G-P48, G-P48d and G-P48L spend almost all of the margin: M20 0.965 at ages 1–10 and 0.976 at ages 21–30.
5. **No candidate damps at 5–10 Hz the way V294/V295 do.** **EVIDENCE.**
   - V295 is +2.46 at 5 Hz. Every angle loop is negative at 5 Hz: G-P48 −0.05 (least), H-A −0.40, P2 −0.57,
     G-F24 −0.53, G-A22 −0.94.
   - This is the rev2-A M14 class; F7 = 0 is the on-car stop.
   - At 13 Hz the held-rate and box10 D are about 2× V295's anti-damping at ages 1–10 (−0.91 / −0.92 vs −0.47). The
     fresh-rate D and H-A sit at −0.36 to −0.40.

---

## 1. The pipeline

### 1.1 Inherited from round 1 (imported unchanged by path from `panel/score_freq.py`)

- The frequency grid: 2600 log points plus pinned lines.
- The 100 Hz hold H.
- The gp-0x6abe EMA (37/128).
- The output lag × fwd × fade, `K_out`.
- `ds_model`'s ZOH plant FRF.
- `ds_gate2`'s two-mass modes.
- `c1r2_members`' factorial.
- `c1_lib`'s integer G walk.

### 1.2 New this round, each validated (T0 appendix "Validation block")

1. **The controller split by frame** (grep `def ctl_split`).
   - Each channel is either:
     - θ-frame: the held gp-0x6a00 and the box10 D; or
     - motor-frame: gp-0x6abe, gp-0x6a56 and gp-0x69ca.
   - L = L_θ + κ·L_motor.
   - **V1:** it equals round 1's `SF.ctl_angle` on the P2, F2 and fresh-operand structures to 2.9e-11 (absolute, on
     values ~1e3).
2. **The frame box** (grep `VARIANTS =`). The two readings follow the refuter (`c2r2_frame.py`) and designer G
   (`g_ext._split`):
   - FA: κ on the motor channels only.
   - FB: the same, plus J and b × 1/1.155.
   - The physical points (FAc, FBc, FAo, FBo) are reported, not gated.
   - A candidate with no motor channel (box10) sees κ not at all. Its κ-only variants are counted once (`frame_free`).
3. **Members.** ms_free × {b_lo, b_q} is built from `M2.FAM["ms_free"]` and `M2._dscale`.
   - **V6:** it is identical (0.0e0) to the stability refuter's independent builder `c2r2_model.member`.
4. **The corrected PM** (grep `def pm_gm`): 180 − |wrap(φ)| at every |L| = 1 crossing.
   - **V3** shows the shared formula's sign error on a leading crossing.
   - The count of points where the two differ is a column in T2.
5. **Two operands round 1 lacked:**
   - **The fresh P/I operand gp-0x69ca (H-A).** EVIDENCE that it is fresh in the same tick: `TRACE-2026-09-30-angle-signal-gp6a00`
     §1.2. It is written by `FUN_0003bd7c` at `0x2224a` and read by the PID at `0x22522` in the same slot-0 pass.
   - **The box10 D (G-A22).** op = 64·10·(θ_h,prev − θ_h) per degree.
   - **V5:** the analytic L equals the exact same-frequency harmonic of the extended periodic model to 6.2e-14 (H-A),
     6.8e-14 (G-A22) and 6.4e-14 (P2) over 0.1–3 Hz. That is an independent confirmation of G's box10 FRF.
6. **GM split into GM↑ and GM↓.** GM↑ (upward) is gated. GM↓ (gain-reduction) is reported.
   - No gated point of any candidate has a −180° crossing with |L| ≥ 1, except E1-splitP.
7. **The I-frozen loop and the fade floors.**
   - Ki 0 on the same set.
   - Hands-on fade floors: 76/254 for the stock arm `0xCBBC4` (min LERP value 77), and 50/254 for the 6803 == 2 arm
     `0xCBAE4` (min 51).
   - Both arms read 255 at hands-off, so the hands-off fade is identical for E2-A2-X. **EVIDENCE:** LE read of both
     records (`fadeB` = `(16,26,38,48,64,96)` → `(255,243,218,179,77,77)`; `fadeB2` = `(24,…,112)` →
     `(255,205,164,125,90,51)`).
8. **The exact periodic model** `Lifted2` (`ds_model.Lifted` plus the fresh operand plus box10) gives ρ and the
   least-damped closed-loop pole at every binding point.
   - **V4:** it equals `ds_model.Lifted` to 1e-12 on the structures both can express.
   - Exact GM at P2's worst point (4.91 dB) matches the LTI GM↑ (4.83 dB).

**Positive controls.**

- **V2:** round 1's D2a and B0r nominal/J_hi PMs reproduce exactly (64.9/46.7, 64.8/47.0).
- **§3 C1–C5** reproduce E2's and the stability refuter's published rows exactly.

### 1.3 Candidate → loop (EVIDENCE, hex parse, unless marked)

| cand | table source (bytes, sha16) | Kp / Ki / Kd | operand |
|---|---|---|---|
| P2 | `c2_cave_P2.hex` 156 B `75e8755743e14d93` | 112 / 56 / 34 | θ held, fresh-rate D |
| F2 | `c2_cave_F2.hex` 138 B `482de8587ce23cbc` | 112 / 56 / 20 | θ held, held-rate D |
| D2a / B0r | `ds_cave_D2a.hex` 162 B / `ds_cave_B0r.hex` 144 B | 34 / 20 | as P2 / F2, 7 knots |
| E1-* | **no E1 hex exists.** E1's byte account (`out/bytes_out.txt`) changes only ICL and hands-on blocks → P2's table (**BELIEF** from E1's account, not from bytes) | P2's (splitP: Kp 200) | as P2 |
| E2-* | `e2_cave_{P2,S300,A2,A3,L13,K0}.hex`: **every one carries P2's rows byte for byte** (asserted in `build_cands`) | P2's (K0: Ki 0) | as P2 |
| G-* | `g_cave_G-*.hex` (8 files). P48L and P48k40 have no hex; their rows come from `g_impls_frozen.json` | 112 / 56 (k40: 40) / 48, 44, 24, 22 | fresh, held, box10 |
| H-A / H-B | `h_freq.py` `TAB_FRESH` / `TAB_HELD` (AST-parsed). **These equal D2a's / B0r's rows** (asserted) | 112 / 56 / 34 / 23 | H-A: **fresh gp-0x69ca, motor frame**. H-B: θ held, held-rate D |

---

## 2. Findings (EVIDENCE / BELIEF)

**F1. Every integral-policy candidate is P2's loop in the frequency domain, and P2 is refuted on the R2 box.**
EVIDENCE: T0, T2, T2b.

- P2 fails 690 points:
  - 197 on the brief's own members under the frame box: J_hi 42.3° and ms_free 42.6° (tier A, κ0.83 / FB κ0.83);
    b_lo×J_hi+h10 26.1°; b_q×J1.0+h10 27.1°.
  - 493 on ms_free×: b_q×ms_free+h10 8.2° at 15.75 m/s, exact ring 1.27 Hz ζ 0.028, ρ 0.9977. GM↑ 4.8 dB there
    (exact GM 4.91 dB).
- E1's "inherits P2's GATE-2 PASS exactly (0 fails, tier A 46.7°)" holds on the **round-1** set only (R1 = 0 fails).
- E2 states the inherited frame failure itself (its M-E2-6, reproduced here exactly, §3 C2).
- **What the policies do change** is which loop runs:
  - Freeze, reset, bleed, leak, angle-bound and saturated-clamp states all run the I-frozen loop.
  - That loop passes the R2 box for P2 (tier A 55.4°, tier B 31.6°, 0 fails).
  - So none of the policies can make P2's frequency verdict worse. None can make it better either.
- **BELIEF:** the "leak" states (E1-bleed I −= I>>3 per tick; E2-L τ 146 ms; H's bleed bsh 7) sit between the PID and
  PD loops. They were not scored separately, because both ends pass for the same skeleton.

**F2. G's "non-d" implementations are the only firmware-I candidates that clear every frequency gate in this file.**
EVIDENCE: T0, T2.

- G-P48, G-P44, G-F24, G-A22, G-P48L and G-P48k40 each have 0 fails on R2 lit, the R2 box, strict and G-strict.
- Binding: b_q×J1.0+h10 at 26.9–27 m/s under FB κ0.83, 34.2–34.8°, exact ring 1.86–1.98 Hz, ζ 0.18–0.19.
- **Costs, frequency side:**
  - (a) **I-frozen turn-hold** (the hold any freeze, bleed or clamp state falls back to) drops from P2's 0.427 to
    0.358 / 0.347 / 0.323 / 0.308 (P48 / P44 / F24 / A22). Their tables are lower where the products bind.
  - (b) **G-P48's M20 is 0.965–0.976 × V295.** It nearly spends the goal's 20 Hz margin; P44 is at 0.88–0.90.
  - (c) **G-F24 and G-A22 anti-damp 13 Hz at −0.91 / −0.92** at ages 1–10, about 1.9× V295's −0.47. At ages 0–9,
    T4b gives a worst condition-matched 2.6× / 3.0×.
- **Tracking cost:** linear |T_ref| is unchanged (hold ≥ 0.983). The goal's tracking metric and the ICL clamp are
  time-domain items (G declares 0.935 at 17 m/s for G-P48).

**F3. H-A is hold-age-free and passes every brief member over the whole frame box, but fails ms_free× with an
undeclared 0.84 Hz ring.**
EVIDENCE: T1, T9, V5, §3 C9.

- On the brief's own members:
  - tier A min 45.5° (ms_free at FA κ1.155, 11.9 m/s; ring 0.79 Hz, ζ 0.204);
  - tier B 33.9°;
  - R2 box without ms_free×: 0 fails.
- **The structural gain.** The gp-0x69ca operand and the fresh D leave no 100 Hz hold in the feedback loop. So:
  - the aged members equal the unaged ones;
  - Re(T/ω) is −0.40 at 5–25 Hz at every age, where P2 moves from −0.37 to −0.15 to +0.05 at 13 Hz across ages
    1–10 / 11–20 / 21–30, and V295 from −0.47 to −1.50 to −1.58.
- **The failure.** It uses D2a's table unchanged, which was fitted without ms_free×:
  - b_q×ms_free: 17.0° at 15.75 m/s, ring 1.34 Hz, ζ 0.069, below 30° over 12.5–22 m/s. This is inside H's stated
    "1.2–1.4 Hz" stop band.
  - **b_lo×ms_free: 22.3° at 11.9 m/s, ring 0.84 Hz, ζ 0.093, below 30° over 11–12.75 m/s.** This is outside both
    bands H declared (1.2–1.4 Hz for ms_free, 1.3–2.1 Hz shared).
- Its 20 Hz gain is M20 0.748, up from D2a's 0.676 because the fresh operand removes the hold's attenuation (the
  round-1 CGF-1b effect). It stays well under V295.
- **BELIEF:** a table refit under ms_free× (as G did for its "non-d" set) would close it. That was not run; it is a
  design step, not a score.
- The hazards H names are unscored here: the fork SR fold, and gp-0x69ca validity.

**F4. H-B fails more than its declared items.**
EVIDENCE: T2b.

- Besides the ms_free products (13.5° b_q, ring 1.28 Hz; 17.8° b_lo, ring **0.82 Hz**), it has:
  - b_q×J1.0+h10 at 29.9° under FB κ0.83 (2 points, 17.5–17.75 m/s);
  - under the strict reading, J_hi+h10 at 41.4° (FA κ0.83, 1 m/s).
- Its 13 Hz anti-damping is −0.91 at ages 1–10, 1.9× V295. It is declared.

**F5. E2-K0 (no firmware I) is the most robust loop and the weakest at holding.**
EVIDENCE: T0, T5, T8.

- R2 box 0 fails. Tier B min 31.6° (b_q×ms_free+h10).
- With its fork integral (τ_o 1 s, 60 ms, 100 Hz; E2's `e2_k0` model), the outer loop has PM ≥ 77.4° and GM ≥ 14.9 dB.
- The linear turn-hold |T_ref(0.05 Hz)| is still **0.878** (goal ≥ 0.90), and 0.1–1 Hz tracking is 0.29–0.96.
- Consistent with E2's own "fails the goal".

**F6. E1-splitP is not a loop the credible set allows.**
EVIDENCE.

- Kp 200 on P2's table gives nominal 45.9° and tier A 29.7°.
- At b_q×ms_free+h10 FA κ0.83, 19 m/s, the exact pole is at the unit circle (ρ 1.0000, ζ −0.000).
- 212 of its points need the corrected PM, because they are leading crossings.

**F7. The PM-formula finding (designer G) is confirmed, and it does not touch any gated PID number here.**
EVIDENCE: T2 last column, §3 C8.

- On every gated PID-loop point of every candidate, except E1-splitP (212) and E2-K0 (1, which is a Ki 0 loop), the
  corrected and shared formulas agree.
- The leading crossings live in the I-frozen loops: up to 862 points (G-P48L).
- **Any I-frozen or Ki 0 margin computed with the shared routines elsewhere in the kit must be re-read with the fix.**

**F8. Stability.**
EVIDENCE (Nyquist plus exact spot checks).

- No gated point of any candidate except E1-splitP has a −180° crossing with |L| ≥ 1 (GM↓ = none). With an
  open-loop-stable plant and the integrator pole indented, that means no encirclement, so every gated point is stable.
- Exact ρ at every binding point is < 1 (max 0.9977, P2 b_q×ms_free+h10), except E1-splitP.

**F9. Re(T/ω), the phase-fragility check (round-2 F3c).**
EVIDENCE: T4b.

- Across 16 conditions (κ 1 / 0.866 × transport 2 / 6 ms × ages 0–9 / 1–10 / 11–20 / 21–30), every fresh-rate-D
  skeleton exceeds V295's condition-matched 13 Hz anti-damping in 2–5 conditions. Those are the ages-0–9 cells,
  where V295 itself is least negative.
- Held D and box10 exceed it in 8.
- At 20 Hz the "∞" entries are the ages-21–30 cells where V295 damps (+0.27) and the candidate does not. The
  condition-matched ratio is a fragile proxy, as G said.
- Worst-vs-worst (each loop's worst condition against V295's worst):
  - 13 Hz: 0.41 (P2), 0.46 (H-A), 0.51 (G-P48), 0.84 (G-F24);
  - 20 Hz: 0.57–0.84.
- The rate-former lag (G's third axis) is not included here.

---

## 3. Disagreements with the designers: re-run, cause recorded

These come from `python score_freq.py claims` (→ `claims_out.txt`) and a slice of H's own `h_freq.gate`.

| # | designer claim | this scorer | cause |
|---|---|---|---|
| C1–C4 | E2 `e2_freq_out.txt`: P2 46.7/32.6/0; P2-FA 43.2/28.3/50; P2-I0 62.6/48.4/0; P2-I0-FA 60.3/45.4/0 | **identical** (all eight numbers and both counts) | none. Positive control |
| C5 | stability refuter F1/F4 (P2): J_hi 43.2/44.0; ms_free 43.8/43.6; b_lo×J_hi+h10 28.3/27.3; b_q×J1.0+h10 29.5/28.5; b_q×ms_free+h10 13.5; b_q×ms_free 17.3; b_lo×ms_free 18.5–22.8 | **identical** (b_lo×ms_free 22.8 at κ1, 17.5 FAc, 19.9 FBc) | none. Positive control |
| C6 | G: rev2A-P2 strict 1496 fails; rev2A-F2 1562 | 1465 / 1522 | **G's listing counts `b_lo*J_hi*tau6+h10\|k0.83` as 62 points over a 31-speed range** (mine 31). 1496 − 31 = 1465. G's counts for its own implementations match exactly (G-P48d 381, G-P44d 386, G-F24d 356, G-A22d 250; P48/P44/F24/A22 0). A bookkeeping duplicate in G's reference rows, not decision-bearing |
| C7 | G: M20 0.976 (G-P48), 0.895 (G-P44d) | 0.965 / 0.884 at ages 1–20; **0.976 / 0.895 at ages 21–30** | G quotes the ages 21–30 value. Both ≤ 1 |
| C8 | G: "pm_fixed == shared on every gated point" | confirmed for every gated PID point (splitP / K0 aside) | — (F7) |
| C9 | **H: H-A tier A 46.7/42.2, tier B 32.6/27.8 (ages 0/10), ReTw13/16/20 −0.23/−0.27/−0.29, 35/33 fails** | with H's operand: **identical**. With the bytes' operand: b_lo×J_hi+h10 40.0° at every age; J_hi 49.2°; ReTw v17 −0.25/−0.30/−0.33 (worst over speed −0.40) | **Two causes, both re-run on H's own code.** (a) `h_freq.des_HA` builds a `ds_model.Des` with no fresh-operand option, so it scores **the held gp-0x6a00 operand, i.e. D2a's loop**, not the gp-0x69ca operand its bytes load (`0x28F4C` → `ld.h -0x69ca`). (b) `h_freq.gate` sets `extra_age = ea0 + age`, where `ea0` from `ds_gate2.member` already includes +10 for `+h10` names. So its "age 10" column scores `+h10` members at **ages 21–30**. A slice of `h_freq.gate` printed "worst tier-B age10 27.8 @ b_lo*J_hi+h10" after `ds_gate2.member("b_lo*J_hi+h10")` returned extra_age 10. H's "fully-stacked residual" (§4 of its page) is therefore an ages 21–30 artefact for H-A |
| C10 | H: H-B ReTw −0.70/−0.70/−0.65 (×0.866), −0.79/−0.81/−0.76 (×1.040) | **identical at v17**. Worst over speed: −0.91 at 13 Hz | H reads one speed. H-B's tier-B 26.8° "age 10" is double-aged, as in C9 |
| C11 | E1: splitP Kp 160 → 40.0/19.6; Kp 200 → 29.7/11.0 | 38.8 (ms_free) / 18.5; 29.7 / 9.8 (b_q×J1.0+h10, 17.5 m/s) | **no E1 script or output for these figures exists on disk** (`out/` has none). Tier A at Kp 200 reproduces; the rest differ by 1.1–1.2°. The cause is not identified (possibly ms_free excluded, or a coarser grid; 9.9° on an integer grid). Not decision-bearing: every figure is far below its bar |
| — | E1: "E1-cal/reset/bleed inherit P2's GATE-2 PASS exactly (0 fails, tier A 46.7°, tier B 30.5°)" | R1: 0 fails, 46.7° ✓. R2 box: **690 fails** | E1 scored the round-1 set. Its 30.5° is rev2-A's b_lo×J_hi×tau6+h10, which is outside R1. E1 does state that F2/F3 are inherited |
| — | G: tier-B min 33.6° (b_lo×ms_free×tau6+h10) for G-P48 | 33.6° in the G's-products column (T1). R2-box min 34.2° (b_q×J1.0+h10) | different member sets: the × tau6 products are report-only here and gated in G's strict. Both pass 30° |

---

## 4. Limits (what this file cannot say)

- **Linear only.** The ICL clamp (F1 of round 2), friction, dwell-then-jump, the release lurch and tracking on real
  r71b paths are the time scorer's. The "hold" columns are |T_ref(0.05 Hz)| with an unbounded integrator.
- **The plant above about 8 Hz is model** (BELIEF), as every page says. The rate-former lag sensitivity (G's 48-condition
  axis) is not in T4b.
- **Credibility rulings are not mine:**
  - whether ms_free × {b_lo, b_q} belongs in the gate (the brief says gate it; this file does);
  - whether aged single corners take the 45° bar (reported as "strict").
- **H-A's operand facts are taken from the trace and the bytes H lists:** gp-0x69ca is 0.1° of the linear angle and
  fresh in the same tick. The fork SR fold and gp-0x69ca validity are unscored.
- **E1's rows rest on E1's byte account,** since no E1 cave hex exists.

---

## 5. Reproduce

```
cd analysis-2020accord/studies/angle_loop/panel2
python score_freq.py validate    # prints V1-V6 and VALIDATE PASS
python score_freq.py             # full run, about 5 min on 12 processes -> _scratch/angle_loop/panel2-score/
python score_freq.py report      # tables again from the cached arr.npz (about 1 min)
python score_freq.py claims      # the §3 cross-checks -> claims_out.txt
```

---

## Appendix: the generated tables (`score_freq_tables.md`, verbatim)

### T0 — one row per candidate (PID loop unless marked; PM deg; κ box = κ 0.83/1/1.155 under FA + 0.83/1.155 under FB; every member at ages 1–10 and 11–20)

| cand | loop | PM nom | A box | A aged (strict) | B box excl. ms_free× | ms_free× b_lo / b_q | fails R1 / R2 lit / **R2 box** / strict | M20 ×V295 | ReTw 5 / 13 / 20 Hz, ages 1–10 (11–20) | \|Tref\| 1.6–3 | hold / hold I-frozen | I-frozen B box |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P2 | own | 64.9 | 42.3 | 37.7 | 26.1 | 13.3 / 8.2 | 0 / 356 / **690** / 824 | 0.68 | -0.57 / -0.37 / -0.34 (-0.74 / -0.15 / -0.20) | 0.99 | 0.997 / 0.427 | 31.6 |
| F2 | own | 64.8 | 42.5 | 38.1 | 26.2 | 13.0 / 9.6 | 0 / 354 / **691** / 868 | 0.70 | -0.84 / -0.84 / -0.69 (-1.68 / -1.20 / -0.52) | 0.93 | 0.996 / 0.413 | 31.1 |
| D2a | own | 64.9 | 42.3 | 37.7 | 26.1 | 13.3 / 8.2 | 0 / 367 / **702** / 836 | 0.68 | -0.57 / -0.37 / -0.34 (-0.74 / -0.15 / -0.20) | 0.99 | 0.997 / 0.429 | 31.3 |
| B0r | own | 64.8 | 42.5 | 38.1 | 26.2 | 13.0 / 9.6 | 0 / 368 / **706** / 883 | 0.70 | -0.84 / -0.84 / -0.69 (-1.68 / -1.20 / -0.52) | 0.93 | 0.997 / 0.416 | 30.9 |
| E1-reset | = P2 | 64.9 | 42.3 | 37.7 | 26.1 | 13.3 / 8.2 | 0 / 356 / **690** / 824 | 0.68 | -0.57 / -0.37 / -0.34 (-0.74 / -0.15 / -0.20) | 0.99 | 0.997 / 0.427 | 31.6 |
| E1-cal | = P2 | 64.9 | 42.3 | 37.7 | 26.1 | 13.3 / 8.2 | 0 / 356 / **690** / 824 | 0.68 | -0.57 / -0.37 / -0.34 (-0.74 / -0.15 / -0.20) | 0.99 | 0.997 / 0.427 | 31.6 |
| E1-bleed | = P2 | 64.9 | 42.3 | 37.7 | 26.1 | 13.3 / 8.2 | 0 / 356 / **690** / 824 | 0.68 | -0.57 / -0.37 / -0.34 (-0.74 / -0.15 / -0.20) | 0.99 | 0.997 / 0.427 | 31.6 |
| E1-freeze | = P2 | 64.9 | 42.3 | 37.7 | 26.1 | 13.3 / 8.2 | 0 / 356 / **690** / 824 | 0.68 | -0.57 / -0.37 / -0.34 (-0.74 / -0.15 / -0.20) | 0.99 | 0.997 / 0.427 | 31.6 |
| E1-sched | = P2 | 64.9 | 42.3 | 37.7 | 26.1 | 13.3 / 8.2 | 0 / 356 / **690** / 824 | 0.68 | -0.57 / -0.37 / -0.34 (-0.74 / -0.15 / -0.20) | 0.99 | 0.997 / 0.427 | 31.6 |
| E1-splitP | own | 45.9 | 22.3 | 13.9 | 3.6 | 5.7 / 0.0 | 624 / 2770 / **5052** / 5967 | 0.66 | -1.98 / -0.67 / -0.43 (-2.35 / -0.30 / -0.18) | 1.24 | 0.991 / 0.571 | 7.4 |
| E2-R1 | = P2 | 64.9 | 42.3 | 37.7 | 26.1 | 13.3 / 8.2 | 0 / 356 / **690** / 824 | 0.68 | -0.57 / -0.37 / -0.34 (-0.74 / -0.15 / -0.20) | 0.99 | 0.997 / 0.427 | 31.6 |
| E2-S | = P2 | 64.9 | 42.3 | 37.7 | 26.1 | 13.3 / 8.2 | 0 / 356 / **690** / 824 | 0.68 | -0.57 / -0.37 / -0.34 (-0.74 / -0.15 / -0.20) | 0.99 | 0.997 / 0.427 | 31.6 |
| E2-A2 | = P2 | 64.9 | 42.3 | 37.7 | 26.1 | 13.3 / 8.2 | 0 / 356 / **690** / 824 | 0.68 | -0.57 / -0.37 / -0.34 (-0.74 / -0.15 / -0.20) | 0.99 | 0.997 / 0.427 | 31.6 |
| E2-A3 | = P2 | 64.9 | 42.3 | 37.7 | 26.1 | 13.3 / 8.2 | 0 / 356 / **690** / 824 | 0.68 | -0.57 / -0.37 / -0.34 (-0.74 / -0.15 / -0.20) | 0.99 | 0.997 / 0.427 | 31.6 |
| E2-A2-X | = P2 | 64.9 | 42.3 | 37.7 | 26.1 | 13.3 / 8.2 | 0 / 356 / **690** / 824 | 0.68 | -0.57 / -0.37 / -0.34 (-0.74 / -0.15 / -0.20) | 0.99 | 0.997 / 0.427 | 31.6 |
| E2-L | = P2 | 64.9 | 42.3 | 37.7 | 26.1 | 13.3 / 8.2 | 0 / 356 / **690** / 824 | 0.68 | -0.57 / -0.37 / -0.34 (-0.74 / -0.15 / -0.20) | 0.99 | 0.997 / 0.427 | 31.6 |
| E2-K0 | own | 81.5 | 55.4 | 52.0 | 40.9 | 41.3 / 31.6 | 0 / 0 / **0** / 0 | 0.68 | -0.43 / -0.37 / -0.34 (-0.67 / -0.17 / -0.20) | 0.77 | 0.878 / 0.427 | 31.6 |
| G-P48d | own | 69.2 | 51.7 | 47.1 | 34.7 | 34.7 / 17.0 | 0 / 101 / **166** / 166 | 0.96 | -0.03 / -0.37 / -0.43 (-0.21 / -0.15 / -0.29) | 0.83 | 0.998 / 0.439 | 36.2 |
| G-P44d | own | 68.7 | 50.9 | 46.6 | 34.9 | 35.2 / 16.7 | 0 / 103 / **169** / 169 | 0.88 | -0.12 / -0.36 / -0.40 (-0.29 / -0.15 / -0.26) | 0.85 | 0.997 / 0.428 | 36.5 |
| G-P48 | own | 69.2 | 51.7 | 47.1 | 34.2 | 35.4 / 36.6 | 0 / 0 / **0** / 0 | 0.96 | -0.05 / -0.37 / -0.43 (-0.23 / -0.15 / -0.29) | 0.83 | 0.994 / 0.358 | 50.1 |
| G-P44 | own | 68.7 | 50.9 | 46.6 | 34.3 | 35.2 / 37.6 | 0 / 0 / **0** / 0 | 0.88 | -0.14 / -0.36 / -0.40 (-0.31 / -0.15 / -0.26) | 0.85 | 0.993 / 0.347 | 50.1 |
| G-F24 | own | 68.6 | 50.7 | 46.9 | 34.8 | 35.8 / 36.9 | 0 / 0 / **0** / 0 | 0.82 | -0.53 / -0.91 / -0.80 (-1.49 / -1.40 / -0.63) | 0.77 | 0.991 / 0.323 | 44.0 |
| G-F24d | own | 68.6 | 50.7 | 46.9 | 34.5 | 35.7 / 18.3 | 0 / 83 / **151** / 151 | 0.82 | -0.53 / -0.91 / -0.80 (-1.49 / -1.40 / -0.63) | 0.77 | 0.996 / 0.402 | 36.4 |
| G-A22 | own | 67.3 | 50.1 | 46.5 | 34.3 | 35.7 / 37.3 | 0 / 0 / **0** / 0 | 0.65 | -0.94 / -0.92 / -0.69 (-1.69 / -1.11 / -0.31) | 0.81 | 0.988 / 0.308 | 50.0 |
| G-A22d | own | 67.3 | 50.1 | 46.5 | 34.7 | 35.7 / 18.0 | 0 / 56 / **117** / 117 | 0.65 | -0.93 / -0.92 / -0.69 (-1.68 / -1.11 / -0.31) | 0.81 | 0.995 / 0.386 | 37.1 |
| G-P48L | own | 69.2 | 51.7 | 47.1 | 34.2 | 36.5 / 37.6 | 0 / 0 / **0** / 0 | 0.97 | -0.05 / -0.37 / -0.43 (-0.23 / -0.15 / -0.29) | 0.87 | 0.994 / 0.355 | 48.4 |
| G-P48k40 | own | 74.4 | 52.4 | 48.0 | 34.8 | 34.8 / 36.2 | 0 / 0 / **0** / 0 | 0.96 | -0.17 / -0.41 / -0.44 (-0.38 / -0.17 / -0.28) | 0.82 | 0.983 / 0.377 | 44.9 |
| H-A | own | 67.9 | 45.5 | 45.5 | 33.9 | 22.3 / 17.0 | 0 / 218 / **352** / 352 | 0.75 | -0.40 / -0.40 / -0.40 (-0.40 / -0.40 / -0.40) | 0.94 | 0.997 / 0.429 | 36.7 |
| H-B | own | 68.2 | 45.7 | 41.4 | 29.9 | 17.8 / 13.5 | 0 / 213 / **359** / 440 | 0.79 | -0.69 / -0.91 / -0.78 (-1.62 / -1.36 / -0.60) | 0.88 | 0.997 / 0.416 | 33.1 |
| V294 (ref) | rate | — | — | — | — | — | — | 0.54 | +1.33 / -0.25 / -0.44 (+0.91 / -0.81 / -0.48) | — | — | — |
| V295 (ref) | rate | — | — | — | — | — | — | 1.00 | +2.46 / -0.47 / -0.82 (+1.69 / -1.50 / -0.89) | — | — | — |

#### Validation block (printed by the script)

- V1 ctl_split == round-1 SF.ctl_angle (P2): max|diff| 2.9e-11
- V1 ctl_split == round-1 SF.ctl_angle (F2): max|diff| 2.9e-11
- V1 ctl_split == round-1 SF.ctl_angle (H-A): max|diff| 2.9e-11
- V2 D2a min PM nominal / J_hi = 64.9 / 46.7 (SCORE-FREQ round 1: 64.9 / 46.7)
- V2 B0r min PM nominal / J_hi = 64.8 / 47.0 (SCORE-FREQ round 1: 64.8 / 47.0)
- V3 PM: lagging -120 deg crossing -> fixed 60.0 / shared 60.0 ; leading +16 deg -> fixed 164.0 / shared -164.0
- V4 Lifted2 == ds_model.Lifted (P2 b_lo*J_hi+h10 @8): rho 0.971842825367 vs 0.971842825367
- V4 Lifted2 == ds_model.Lifted (F2 b_lo*J_hi+h10 @8): rho 0.967561201275 vs 0.967561201275
- V5 analytic L vs exact harmonic (H-A nominal@17.0, 0.1-3 Hz): max rel diff 6.18e-14 (tol 1e-08)
- V5 analytic L vs exact harmonic (G-A22 nominal@17.0, 0.1-3 Hz): max rel diff 6.82e-14 (tol 0.05)
- V5 analytic L vs exact harmonic (P2 nominal@17.0, 0.1-3 Hz): max rel diff 6.37e-14 (tol 0.05)
- V6 members == refuter c2r2_model.member (ms_free products, b_q*J1.0, b_lo*J_hi): max|diff| 0.0e+00

### T1 — GATE 2 margins (PID loop, PM corrected; PM in deg)

`A k1` = single corners at κ 1 (round-1 comparable). `A box` / `B box` = over the gated frame box (κ 0.83/1/1.155 under FA + κ 0.83/1.155 under FB). `A aged` = single corners at ages 11–20 (strict reading, bar 45). `B box` includes every aged member and ms_free × {b_lo, b_q}. Binding: member@speed variant, crossover fc (Hz); ring = the exact least-damped closed-loop pole (f Hz, ζ) at that point.

| cand | = loop of | PM nom / GM nom | A k1 | B k1 (R1 set) | A box (binding; ring) | A aged (binding; ring) | B box (binding; ring) | ms_free×{b_lo,b_q} (binding; ring) | G's ×tau6 products (report) |
|---|---|---|---|---|---|---|---|---|---|
| P2 | — | 64.9 / 24.6 | 46.7 | 32.6 (b_lo*J_hi+h10@1.00 nom, fc 1.38) | 42.3 (J_hi@1.00 FA.83, fc 1.20); ring 1.05 Hz ζ 0.495, ρ 0.9631 | 37.7 (J_hi+h10@1.00 FA.83, fc 1.18); ring 1.11 Hz ζ 0.422, ρ 0.9681 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 6.4 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.36) |
| F2 | — | 64.8 / 17.8 | 47.0 | 32.1 (b_lo*J_hi+h10@1.00 nom, fc 1.44) | 42.5 (J_hi@1.00 FA.83, fc 1.21); ring 1.03 Hz ζ 0.515, ρ 0.9618 | 38.1 (J_hi+h10@1.00 FA.83, fc 1.21); ring 1.10 Hz ζ 0.470, ρ 0.9639 | 9.6 (b_q*ms_free+h10@15.75 FB.83, fc 1.36); ring 1.38 Hz ζ 0.034, ρ 0.9971 | 9.6 (b_q*ms_free+h10@15.75 FB.83, fc 1.36); ring 1.38 Hz ζ 0.034, ρ 0.9971 | 7.7 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.36) |
| D2a | — | 64.9 / 24.6 | 46.7 | 32.6 (b_lo*J_hi+h10@1.00 nom, fc 1.38) | 42.3 (J_hi@1.00 FA.83, fc 1.20); ring 1.05 Hz ζ 0.495, ρ 0.9631 | 37.7 (J_hi+h10@1.00 FA.83, fc 1.18); ring 1.11 Hz ζ 0.422, ρ 0.9681 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 6.4 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.36) |
| B0r | — | 64.8 / 17.8 | 47.0 | 32.1 (b_lo*J_hi+h10@1.00 nom, fc 1.44) | 42.5 (J_hi@1.00 FA.83, fc 1.21); ring 1.03 Hz ζ 0.515, ρ 0.9618 | 38.1 (J_hi+h10@1.00 FA.83, fc 1.21); ring 1.10 Hz ζ 0.470, ρ 0.9639 | 9.6 (b_q*ms_free+h10@15.75 FB.83, fc 1.36); ring 1.38 Hz ζ 0.034, ρ 0.9971 | 9.6 (b_q*ms_free+h10@15.75 FB.83, fc 1.36); ring 1.38 Hz ζ 0.034, ρ 0.9971 | 7.7 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.36) |
| E1-reset | P2 | 64.9 / 24.6 | 46.7 | 32.6 (b_lo*J_hi+h10@1.00 nom, fc 1.38) | 42.3 (J_hi@1.00 FA.83, fc 1.20); ring 1.05 Hz ζ 0.495, ρ 0.9631 | 37.7 (J_hi+h10@1.00 FA.83, fc 1.18); ring 1.11 Hz ζ 0.422, ρ 0.9681 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 6.4 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.36) |
| E1-cal | P2 | 64.9 / 24.6 | 46.7 | 32.6 (b_lo*J_hi+h10@1.00 nom, fc 1.38) | 42.3 (J_hi@1.00 FA.83, fc 1.20); ring 1.05 Hz ζ 0.495, ρ 0.9631 | 37.7 (J_hi+h10@1.00 FA.83, fc 1.18); ring 1.11 Hz ζ 0.422, ρ 0.9681 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 6.4 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.36) |
| E1-bleed | P2 | 64.9 / 24.6 | 46.7 | 32.6 (b_lo*J_hi+h10@1.00 nom, fc 1.38) | 42.3 (J_hi@1.00 FA.83, fc 1.20); ring 1.05 Hz ζ 0.495, ρ 0.9631 | 37.7 (J_hi+h10@1.00 FA.83, fc 1.18); ring 1.11 Hz ζ 0.422, ρ 0.9681 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 6.4 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.36) |
| E1-freeze | P2 | 64.9 / 24.6 | 46.7 | 32.6 (b_lo*J_hi+h10@1.00 nom, fc 1.38) | 42.3 (J_hi@1.00 FA.83, fc 1.20); ring 1.05 Hz ζ 0.495, ρ 0.9631 | 37.7 (J_hi+h10@1.00 FA.83, fc 1.18); ring 1.11 Hz ζ 0.422, ρ 0.9681 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 6.4 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.36) |
| E1-sched | P2 | 64.9 / 24.6 | 46.7 | 32.6 (b_lo*J_hi+h10@1.00 nom, fc 1.38) | 42.3 (J_hi@1.00 FA.83, fc 1.20); ring 1.05 Hz ζ 0.495, ρ 0.9631 | 37.7 (J_hi+h10@1.00 FA.83, fc 1.18); ring 1.11 Hz ζ 0.422, ρ 0.9681 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 6.4 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.36) |
| E1-splitP | — | 45.9 / 18.2 | 29.7 | 9.8 (b_q*J1.0+h10@17.50 nom, fc 2.02) | 22.3 (b_lo@8.00 FB.83, fc 3.64); ring 3.86 Hz ζ 0.158, ρ 0.9797 | 13.9 (b_lo+h10@8.00 FB.83, fc 3.45); ring 3.59 Hz ζ 0.089, ρ 0.9800 | 0.0 (b_q*ms_free+h10@19.00 FA.83, fc 1.77); ring 1.77 Hz ζ -0.000, ρ 1.0000 | 0.0 (b_q*ms_free+h10@19.00 FA.83, fc 1.77); ring 1.77 Hz ζ -0.000, ρ 1.0000 | 0.0 (b_q*ms_free*tau6+h10@15.50 nom, fc 1.44) |
| E2-R1 | P2 | 64.9 / 24.6 | 46.7 | 32.6 (b_lo*J_hi+h10@1.00 nom, fc 1.38) | 42.3 (J_hi@1.00 FA.83, fc 1.20); ring 1.05 Hz ζ 0.495, ρ 0.9631 | 37.7 (J_hi+h10@1.00 FA.83, fc 1.18); ring 1.11 Hz ζ 0.422, ρ 0.9681 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 6.4 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.36) |
| E2-S | P2 | 64.9 / 24.6 | 46.7 | 32.6 (b_lo*J_hi+h10@1.00 nom, fc 1.38) | 42.3 (J_hi@1.00 FA.83, fc 1.20); ring 1.05 Hz ζ 0.495, ρ 0.9631 | 37.7 (J_hi+h10@1.00 FA.83, fc 1.18); ring 1.11 Hz ζ 0.422, ρ 0.9681 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 6.4 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.36) |
| E2-A2 | P2 | 64.9 / 24.6 | 46.7 | 32.6 (b_lo*J_hi+h10@1.00 nom, fc 1.38) | 42.3 (J_hi@1.00 FA.83, fc 1.20); ring 1.05 Hz ζ 0.495, ρ 0.9631 | 37.7 (J_hi+h10@1.00 FA.83, fc 1.18); ring 1.11 Hz ζ 0.422, ρ 0.9681 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 6.4 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.36) |
| E2-A3 | P2 | 64.9 / 24.6 | 46.7 | 32.6 (b_lo*J_hi+h10@1.00 nom, fc 1.38) | 42.3 (J_hi@1.00 FA.83, fc 1.20); ring 1.05 Hz ζ 0.495, ρ 0.9631 | 37.7 (J_hi+h10@1.00 FA.83, fc 1.18); ring 1.11 Hz ζ 0.422, ρ 0.9681 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 6.4 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.36) |
| E2-A2-X | P2 | 64.9 / 24.6 | 46.7 | 32.6 (b_lo*J_hi+h10@1.00 nom, fc 1.38) | 42.3 (J_hi@1.00 FA.83, fc 1.20); ring 1.05 Hz ζ 0.495, ρ 0.9631 | 37.7 (J_hi+h10@1.00 FA.83, fc 1.18); ring 1.11 Hz ζ 0.422, ρ 0.9681 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 6.4 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.36) |
| E2-L | P2 | 64.9 / 24.6 | 46.7 | 32.6 (b_lo*J_hi+h10@1.00 nom, fc 1.38) | 42.3 (J_hi@1.00 FA.83, fc 1.20); ring 1.05 Hz ζ 0.495, ρ 0.9631 | 37.7 (J_hi+h10@1.00 FA.83, fc 1.18); ring 1.11 Hz ζ 0.422, ρ 0.9681 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 8.2 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.27 Hz ζ 0.028, ρ 0.9977 | 6.4 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.36) |
| E2-K0 | — | 81.5 / 24.4 | 62.6 | 48.4 (b_lo*J_hi+h10@8.00 nom, fc 1.85) | 55.4 (b_lo@8.00 FB.83, fc 2.91); ring 3.39 Hz ζ 0.394, ρ 0.9128 | 52.0 (b_lo+h10@8.00 FB.83, fc 2.74); ring 3.18 Hz ζ 0.341, ρ 0.9302 | 31.6 (b_q*ms_free+h10@15.75 FB.83, fc 1.39); ring 1.42 Hz ζ 0.113, ρ 0.9898 | 31.6 (b_q*ms_free+h10@15.75 FB.83, fc 1.39); ring 1.42 Hz ζ 0.113, ρ 0.9898 | 29.6 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.39) |
| G-P48d | — | 69.2 / 23.1 | 58.1 | 41.8 (b_q*J1.0+h10@27.00 nom, fc 1.57) | 51.7 (J_hi@1.00 FA.83, fc 1.18); ring 0.82 Hz ζ 0.564, ρ 0.9655 | 47.1 (J_hi+h10@1.00 FA.83, fc 1.14); ring 0.89 Hz ζ 0.516, ρ 0.9670 | 17.0 (b_q*ms_free+h10@15.75 FA.83, fc 1.27); ring 1.28 Hz ζ 0.061, ρ 0.9951 | 17.0 (b_q*ms_free+h10@15.75 FA.83, fc 1.27); ring 1.28 Hz ζ 0.061, ρ 0.9951 | 15.2 (b_q*ms_free*tau6+h10@15.75 FA.83, fc 1.27) |
| G-P44d | — | 68.7 / 23.6 | 56.9 | 41.9 (b_q*J1.0+h10@27.00 nom, fc 1.54) | 50.9 (J_hi@1.00 FA.83, fc 1.11); ring 0.80 Hz ζ 0.548, ρ 0.9676 | 46.6 (J_hi+h10@1.00 FA.83, fc 1.08); ring 0.86 Hz ζ 0.502, ρ 0.9691 | 16.7 (b_q*ms_free+h10@15.75 FA.83, fc 1.25); ring 1.27 Hz ζ 0.058, ρ 0.9954 | 16.7 (b_q*ms_free+h10@15.75 FA.83, fc 1.25); ring 1.27 Hz ζ 0.058, ρ 0.9954 | 14.9 (b_q*ms_free*tau6+h10@15.75 FA.83, fc 1.25) |
| G-P48 | — | 69.2 / 23.1 | 58.1 | 41.2 (b_q*J1.0+h10@26.90 nom, fc 1.58) | 51.7 (J_hi@1.00 FA.83, fc 1.18); ring 0.82 Hz ζ 0.564, ρ 0.9655 | 47.1 (J_hi+h10@1.00 FA.83, fc 1.14); ring 0.89 Hz ζ 0.516, ρ 0.9670 | 34.2 (b_q*J1.0+h10@26.90 FB.83, fc 1.74); ring 1.89 Hz ζ 0.184, ρ 0.9780 | 35.4 (b_lo*ms_free+h10@9.00 FA.83, fc 1.24); ring 1.26 Hz ζ 0.227, ρ 0.9817 | 33.6 (b_lo*ms_free*tau6+h10@9.00 FA.83, fc 1.24) |
| G-P44 | — | 68.7 / 23.6 | 56.9 | 41.2 (b_q*J1.0+h10@27.00 nom, fc 1.55) | 50.9 (J_hi@1.00 FA.83, fc 1.11); ring 0.80 Hz ζ 0.548, ρ 0.9676 | 46.6 (J_hi+h10@1.00 FA.83, fc 1.08); ring 0.86 Hz ζ 0.502, ρ 0.9691 | 34.3 (b_q*J1.0+h10@27.00 FB.83, fc 1.71); ring 1.87 Hz ζ 0.180, ρ 0.9787 | 35.2 (b_lo*ms_free+h10@8.75 FA.83, fc 1.31); ring 1.34 Hz ζ 0.231, ρ 0.9802 | 33.3 (b_lo*ms_free*tau6+h10@8.50 FB.83, fc 1.56) |
| G-F24 | — | 68.6 / 17.5 | 56.3 | 41.8 (b_q*J1.0+h10@27.00 nom, fc 1.54) | 50.7 (J_hi@1.00 FA.83, fc 1.07); ring 0.76 Hz ζ 0.545, ρ 0.9692 | 46.9 (J_hi+h10@1.00 FA.83, fc 1.07); ring 0.80 Hz ζ 0.530, ρ 0.9693 | 34.8 (b_q*J1.0+h10@27.00 FB.83, fc 1.70); ring 1.88 Hz ζ 0.187, ρ 0.9777 | 35.8 (b_lo*ms_free+h10@8.75 FB.83, fc 1.42); ring 1.47 Hz ζ 0.248, ρ 0.9766 | 33.7 (b_lo*ms_free*tau6+h10@8.75 FB.83, fc 1.42) |
| G-F24d | — | 68.6 / 17.5 | 56.3 | 41.8 (b_q*J1.0+h10@27.00 nom, fc 1.54) | 50.7 (J_hi@1.00 FA.83, fc 1.07); ring 0.76 Hz ζ 0.545, ρ 0.9692 | 46.9 (J_hi+h10@1.00 FA.83, fc 1.07); ring 0.80 Hz ζ 0.530, ρ 0.9693 | 18.3 (b_q*ms_free+h10@15.75 FA.83, fc 1.24); ring 1.26 Hz ζ 0.064, ρ 0.9949 | 18.3 (b_q*ms_free+h10@15.75 FA.83, fc 1.24); ring 1.26 Hz ζ 0.064, ρ 0.9949 | 16.4 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.34) |
| G-A22 | — | 67.3 / 17.4 | 50.1 | 37.4 (b_q*J1.0+h10@26.90 nom, fc 1.52) | 50.1 (J_hi@1.00 nom, fc 0.98); ring 0.73 Hz ζ 0.528, ρ 0.9718 | 46.5 (J_hi+h10@1.00 nom, fc 0.98); ring 0.76 Hz ζ 0.512, ρ 0.9720 | 34.3 (b_q*J1.0+h10@26.90 FB.83, fc 1.68); ring 1.86 Hz ζ 0.179, ρ 0.9789 | 35.7 (b_lo*ms_free+h10@8.75 FB.83, fc 1.38); ring 1.44 Hz ζ 0.238, ρ 0.9781 | 33.7 (b_lo*ms_free*tau6+h10@8.75 FB.83, fc 1.38) |
| G-A22d | — | 67.3 / 17.4 | 50.1 | 37.7 (b_q*J1.0+h10@26.90 nom, fc 1.51) | 50.1 (J_hi@1.00 nom, fc 0.98); ring 0.73 Hz ζ 0.528, ρ 0.9718 | 46.5 (J_hi+h10@1.00 nom, fc 0.98); ring 0.76 Hz ζ 0.512, ρ 0.9720 | 18.0 (b_q*ms_free+h10@15.75 FB.83, fc 1.33); ring 1.35 Hz ζ 0.060, ρ 0.9949 | 18.0 (b_q*ms_free+h10@15.75 FB.83, fc 1.33); ring 1.35 Hz ζ 0.060, ρ 0.9949 | 16.1 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.33) |
| G-P48L | — | 69.2 / 22.9 | 58.1 | 41.2 (b_q*J1.0+h10@26.90 nom, fc 1.58) | 51.7 (J_hi@1.00 FA.83, fc 1.18); ring 0.82 Hz ζ 0.564, ρ 0.9655 | 47.1 (J_hi+h10@1.00 FA.83, fc 1.14); ring 0.89 Hz ζ 0.516, ρ 0.9670 | 34.2 (b_q*J1.0+h10@26.90 FB.83, fc 1.74); ring 1.89 Hz ζ 0.184, ρ 0.9780 | 36.5 (b_lo*ms_free+h10@8.50 FB.83, fc 1.59); ring 1.62 Hz ζ 0.257, ρ 0.9734 | 34.2 (b_lo*ms_free*tau6+h10@8.25 FB.83, fc 1.75) |
| G-P48k40 | — | 74.4 / 22.7 | 58.5 | 42.2 (b_q*J1.0+h10@26.90 nom, fc 1.66) | 52.4 (J_hi@1.00 FB.83, fc 1.57); ring 1.41 Hz ζ 0.643, ρ 0.9601 | 48.0 (J_hi+h10@1.00 FB.83, fc 1.51); ring 1.46 Hz ζ 0.541, ρ 0.9613 | 34.8 (b_q*J1.0+h10@26.90 FB.83, fc 1.82); ring 1.98 Hz ζ 0.186, ρ 0.9800 | 34.8 (b_lo*ms_free+h10@11.90 FA.83, fc 0.81); ring 0.82 Hz ζ 0.138, ρ 0.9928 | 33.2 (b_lo*J_hi*tau6+h10@1.00 FB.83, fc 1.74) |
| H-A | — | 67.9 / 23.7 | 49.2 | 39.2 (b_q*J1.0@15.50 nom, fc 1.58) | 45.5 (ms_free@11.90 FA1.155, fc 0.75); ring 0.79 Hz ζ 0.204, ρ 0.9897 | 45.5 (ms_free+h10@11.90 FA1.155, fc 0.75); ring 0.79 Hz ζ 0.204, ρ 0.9897 | 17.0 (b_q*ms_free@15.75 FA1.155, fc 1.32); ring 1.34 Hz ζ 0.069, ρ 0.9942 | 17.0 (b_q*ms_free@15.75 FA1.155, fc 1.32); ring 1.34 Hz ζ 0.069, ρ 0.9942 | 15.1 (b_q*ms_free*tau6@15.75 FA1.155, fc 1.32) |
| H-B | — | 68.2 / 17.2 | 50.9 | 36.6 (b_lo*J_hi+h10@1.00 nom, fc 1.46) | 45.7 (J_hi@1.00 FA.83, fc 1.20); ring 0.94 Hz ζ 0.555, ρ 0.9615 | 41.4 (J_hi+h10@1.00 FA.83, fc 1.20); ring 1.00 Hz ζ 0.524, ρ 0.9621 | 13.5 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.28 Hz ζ 0.048, ρ 0.9961 | 13.5 (b_q*ms_free+h10@15.75 FA.83, fc 1.26); ring 1.28 Hz ζ 0.048, ρ 0.9961 | 11.6 (b_q*ms_free*tau6+h10@15.75 FB.83, fc 1.36) |

### T2 — GATE 2 fail counts (points = member × speed × frame variant; PID loop)

`R1` = round-1 brief set at κ 1 (comparable with SCORE-FREQ round 1). `R2 lit` = + ms_free × {b_lo, b_q} and κ 0.83/1.155 under FA (the brief's literal extension). **`R2 box` = + reading FB (THE gate this round).** `strict` = R2 box with aged single corners at 45°. `G-strict` = strict + designer G's × tau6 products. `R2 box w/o ms_free×` = the same gate without the two new products. Fail = PM < bar, GM↑ < 6 dB, max(|Tc|,|Tref|) 5–30 Hz > +3 dB, or L20 > V295's L20 (same member, speed, frame).

| cand | R1 | R2 lit | **R2 box** | R2 box w/o L20 | R2 box w/o ms_free× | strict | G-strict | min GM↑ dB | min GM↓ dB | peak 5–30 dB | max L20 / V295 | PM fixed≠shared |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P2 | 0 | 356 | **690** | 690 | 197 | 824 | 1465 | 4.8 | — | -2.6 | 0.68 | 1 |
| F2 | 0 | 354 | **691** | 691 | 188 | 868 | 1522 | 6.1 | — | +0.1 | 0.71 | 1 |
| D2a | 0 | 367 | **702** | 702 | 207 | 836 | 1480 | 4.8 | — | -2.6 | 0.68 | 1 |
| B0r | 0 | 368 | **706** | 706 | 197 | 883 | 1539 | 5.6 | — | +0.1 | 0.71 | 1 |
| E1-reset | 0 | 356 | **690** | 690 | 197 | 824 | 1465 | 4.8 | — | -2.6 | 0.68 | 1 |
| E1-cal | 0 | 356 | **690** | 690 | 197 | 824 | 1465 | 4.8 | — | -2.6 | 0.68 | 1 |
| E1-bleed | 0 | 356 | **690** | 690 | 197 | 824 | 1465 | 4.8 | — | -2.6 | 0.68 | 1 |
| E1-freeze | 0 | 356 | **690** | 690 | 197 | 824 | 1465 | 4.8 | — | -2.6 | 0.68 | 1 |
| E1-sched | 0 | 356 | **690** | 690 | 197 | 824 | 1465 | 4.8 | — | -2.6 | 0.68 | 1 |
| E1-splitP | 624 | 2770 | **5052** | 5052 | 3536 | 5967 | 8014 | 0.0 | 0.0 | +2.7 | 0.67 | 212 |
| E2-R1 | 0 | 356 | **690** | 690 | 197 | 824 | 1465 | 4.8 | — | -2.6 | 0.68 | 1 |
| E2-S | 0 | 356 | **690** | 690 | 197 | 824 | 1465 | 4.8 | — | -2.6 | 0.68 | 1 |
| E2-A2 | 0 | 356 | **690** | 690 | 197 | 824 | 1465 | 4.8 | — | -2.6 | 0.68 | 1 |
| E2-A3 | 0 | 356 | **690** | 690 | 197 | 824 | 1465 | 4.8 | — | -2.6 | 0.68 | 1 |
| E2-A2-X | 0 | 356 | **690** | 690 | 197 | 824 | 1465 | 4.8 | — | -2.6 | 0.68 | 1 |
| E2-L | 0 | 356 | **690** | 690 | 197 | 824 | 1465 | 4.8 | — | -2.6 | 0.68 | 1 |
| E2-K0 | 0 | 0 | **0** | 0 | 0 | 0 | 5 | 14.4 | — | -2.0 | 0.68 | 2 |
| G-P48d | 0 | 101 | **166** | 166 | 0 | 166 | 381 | 13.9 | — | -0.3 | 0.97 | 448 |
| G-P44d | 0 | 103 | **169** | 169 | 0 | 169 | 386 | 14.4 | — | -0.9 | 0.89 | 275 |
| G-P48 | 0 | 0 | **0** | 0 | 0 | 0 | 0 | 13.9 | — | -0.3 | 0.97 | 573 |
| G-P44 | 0 | 0 | **0** | 0 | 0 | 0 | 0 | 14.4 | — | -0.9 | 0.89 | 356 |
| G-F24 | 0 | 0 | **0** | 0 | 0 | 0 | 0 | 6.7 | — | +2.0 | 0.83 | 184 |
| G-F24d | 0 | 83 | **151** | 151 | 0 | 151 | 356 | 6.7 | — | +2.0 | 0.83 | 142 |
| G-A22 | 0 | 0 | **0** | 0 | 0 | 0 | 0 | 7.9 | — | -3.2 | 0.79 | 0 |
| G-A22d | 0 | 56 | **117** | 117 | 0 | 117 | 250 | 7.9 | — | -3.0 | 0.79 | 0 |
| G-P48L | 0 | 0 | **0** | 0 | 0 | 0 | 0 | 13.7 | — | -0.1 | 0.97 | 862 |
| G-P48k40 | 0 | 0 | **0** | 0 | 0 | 0 | 0 | 13.5 | — | +0.3 | 0.96 | 372 |
| H-A | 0 | 218 | **352** | 352 | 0 | 352 | 758 | 13.8 | — | -0.8 | 0.75 | 4 |
| H-B | 0 | 213 | **359** | 359 | 2 | 440 | 928 | 6.4 | — | +1.9 | 0.81 | 45 |

### T2b — which members fail the R2 box gate (member: variant/points/min PM)

- **P2**: J_hi 34 pts min 42.3 [FA.83,FB.83]; ms_free 10 pts min 42.6 [FA.83,FB.83]; b_lo*ms_free 44 pts min 16.1 [FA.83,FA1.155,FB.83,nom]; b_q*ms_free 174 pts min 12.3 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_lo*J_hi+h10 60 pts min 26.1 [FA.83,FB.83]; b_q*J1.0+h10 93 pts min 27.1 [FA.83,FB.83]; b_lo*ms_free+h10 72 pts min 13.3 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_q*ms_free+h10 203 pts min 8.2 [FA.83,FA1.155,FB.83,FB1.155,nom]
- **F2**: J_hi 29 pts min 42.5 [FA.83,FB.83]; ms_free 11 pts min 42.7 [FA.83,FB.83]; b_lo*ms_free 51 pts min 15.9 [FA.83,FA1.155,FB.83,nom]; b_q*ms_free 160 pts min 14.4 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_lo*J_hi+h10 60 pts min 26.2 [FA.83,FB.83]; b_q*J1.0+h10 88 pts min 26.4 [FA.83,FB.83]; b_lo*ms_free+h10 84 pts min 13.0 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_q*ms_free+h10 208 pts min 9.6 [FA.83,FA1.155,FB.83,FB1.155,nom]
- **D2a**: J_hi 34 pts min 42.3 [FA.83,FB.83]; ms_free 10 pts min 42.6 [FA.83,FB.83]; b_lo*ms_free 44 pts min 16.1 [FA.83,FA1.155,FB.83,nom]; b_q*ms_free 175 pts min 12.3 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_lo*J_hi+h10 60 pts min 26.1 [FA.83,FB.83]; b_q*J1.0+h10 103 pts min 26.9 [FA.83,FB.83]; b_lo*ms_free+h10 71 pts min 13.3 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_q*ms_free+h10 205 pts min 8.2 [FA.83,FA1.155,FB.83,FB1.155,nom]
- **B0r**: J_hi 29 pts min 42.5 [FA.83,FB.83]; ms_free 11 pts min 42.7 [FA.83,FB.83]; b_lo*ms_free 51 pts min 15.9 [FA.83,FA1.155,FB.83,nom]; b_q*ms_free 164 pts min 14.4 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_lo*J_hi+h10 60 pts min 26.2 [FA.83,FB.83]; b_q*J1.0+h10 97 pts min 26.4 [FA.83,FB.83]; b_lo*ms_free+h10 84 pts min 13.0 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_q*ms_free+h10 210 pts min 9.6 [FA.83,FA1.155,FB.83,FB1.155,nom]
- **E1-splitP**: nominal 48 pts min 38.7 [FA.83,FB.83]; J_hi 162 pts min 26.7 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_lo 162 pts min 22.3 [FA.83,FA1.155,FB.83,FB1.155,nom]; tau0 36 pts min 40.9 [FA.83,FB.83]; tau6 94 pts min 34.1 [FA.83,FA1.155,FB.83,FB1.155,nom]; mode13 50 pts min 38.3 [FA.83,FB.83]; mode20 49 pts min 38.5 [FA.83,FB.83]; ms_free 221 pts min 25.9 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_lo*J_hi 163 pts min 13.0 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_lo*tau6 103 pts min 17.1 [FA.83,FA1.155,FB.83,FB1.155,nom]; J1.0 9 pts min 27.3 [FB.83]; b_q*J_hi 271 pts min 21.7 [FA.83,FB.83,FB1.155,nom]; b_q*J1.0 459 pts min 10.3 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_lo*ms_free 257 pts min 11.8 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_q*ms_free 406 pts min 2.3 [FA.83,FA1.155,FB.83,FB1.155,nom]; J_hi+h10 81 pts min 19.8 [FA.83,FB.83,FB1.155,nom]; b_lo+h10 123 pts min 13.9 [FA.83,FA1.155,FB.83,FB1.155,nom]; tau6+h10 13 pts min 26.7 [FB.83]; ms_free+h10 68 pts min 19.7 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_lo*J_hi+h10 168 pts min 5.4 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_lo*tau6+h10 158 pts min 9.0 [FA.83,FA1.155,FB.83,FB1.155,nom]; J1.0+h10 61 pts min 21.7 [FA.83,FB.83,FB1.155,nom]; b_q*J_hi+h10 470 pts min 13.3 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_q*J1.0+h10 517 pts min 3.6 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_q*tau6+h10 50 pts min 26.7 [FB.83]; b_lo*ms_free+h10 325 pts min 5.7 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_q*ms_free+h10 528 pts min 0.0 [FA.83,FA1.155,FB.83,FB1.155,nom]
- **G-P48d**: b_q*ms_free 71 pts min 20.7 [FA.83,FB.83,nom]; b_q*ms_free+h10 95 pts min 17.0 [FA.83,FA1.155,FB.83,nom]
- **G-P44d**: b_q*ms_free 71 pts min 20.3 [FA.83,FB.83,nom]; b_q*ms_free+h10 98 pts min 16.7 [FA.83,FA1.155,FB.83,FB1.155,nom]
- **G-F24d**: b_q*ms_free 51 pts min 22.8 [FA.83,FB.83,nom]; b_q*ms_free+h10 100 pts min 18.3 [FA.83,FA1.155,FB.83,FB1.155,nom]
- **G-A22d**: b_q*ms_free 48 pts min 22.7 [FB.83,nom]; b_q*ms_free+h10 69 pts min 18.0 [FB.83,nom]
- **H-A**: b_lo*ms_free 22 pts min 22.3 [FA.83,FA1.155,FB1.155,nom]; b_q*ms_free 154 pts min 17.0 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_lo*ms_free+h10 22 pts min 22.3 [FA.83,FA1.155,FB1.155,nom]; b_q*ms_free+h10 154 pts min 17.0 [FA.83,FA1.155,FB.83,FB1.155,nom]
- **H-B**: b_lo*ms_free 26 pts min 20.7 [FA.83,FB.83,nom]; b_q*ms_free 107 pts min 18.1 [FA.83,FA1.155,FB.83,FB1.155,nom]; b_q*J1.0+h10 2 pts min 29.9 [FB.83]; b_lo*ms_free+h10 47 pts min 17.8 [FA.83,FB.83,nom]; b_q*ms_free+h10 177 pts min 13.5 [FA.83,FA1.155,FB.83,FB1.155,nom]

### T3 — 20 Hz gain vs V295 (worst over speed, ages 1–10 and 11–20, same frame κ)

| cand | M20/V295 κ1 | κ0.83 | κ1.155 | κ0.866 (phys) | κ1, ages 0–30 | L20/V295 max (R2 box) |
|---|---|---|---|---|---|---|
| P2 | 0.676 | 0.673 | 0.679 | 0.674 | 0.691 | 0.679 |
| F2 | 0.697 | 0.711 | 0.689 | 0.707 | 0.697 | 0.711 |
| D2a | 0.676 | 0.673 | 0.679 | 0.674 | 0.691 | 0.679 |
| B0r | 0.697 | 0.711 | 0.689 | 0.707 | 0.697 | 0.711 |
| E1-reset | 0.676 | 0.673 | 0.679 | 0.674 | 0.691 | 0.679 |
| E1-cal | 0.676 | 0.673 | 0.679 | 0.674 | 0.691 | 0.679 |
| E1-bleed | 0.676 | 0.673 | 0.679 | 0.674 | 0.691 | 0.679 |
| E1-freeze | 0.676 | 0.673 | 0.679 | 0.674 | 0.691 | 0.679 |
| E1-sched | 0.676 | 0.673 | 0.679 | 0.674 | 0.691 | 0.679 |
| E1-splitP | 0.665 | 0.659 | 0.668 | 0.661 | 0.710 | 0.668 |
| E2-R1 | 0.676 | 0.673 | 0.679 | 0.674 | 0.691 | 0.679 |
| E2-S | 0.676 | 0.673 | 0.679 | 0.674 | 0.691 | 0.679 |
| E2-A2 | 0.676 | 0.673 | 0.679 | 0.674 | 0.691 | 0.679 |
| E2-A3 | 0.676 | 0.673 | 0.679 | 0.674 | 0.691 | 0.679 |
| E2-A2-X | 0.676 | 0.673 | 0.679 | 0.674 | 0.691 | 0.679 |
| E2-L | 0.676 | 0.673 | 0.679 | 0.674 | 0.691 | 0.679 |
| E2-K0 | 0.678 | 0.674 | 0.680 | 0.675 | 0.689 | 0.680 |
| G-P48d | 0.964 | 0.961 | 0.966 | 0.962 | 0.976 | 0.966 |
| G-P44d | 0.884 | 0.881 | 0.886 | 0.882 | 0.895 | 0.886 |
| G-P48 | 0.965 | 0.962 | 0.967 | 0.962 | 0.976 | 0.967 |
| G-P44 | 0.883 | 0.880 | 0.885 | 0.881 | 0.895 | 0.885 |
| G-F24 | 0.821 | 0.832 | 0.814 | 0.830 | 0.821 | 0.833 |
| G-F24d | 0.821 | 0.832 | 0.814 | 0.830 | 0.821 | 0.833 |
| G-A22 | 0.653 | 0.786 | 0.565 | 0.754 | 0.653 | 0.786 |
| G-A22d | 0.652 | 0.786 | 0.565 | 0.753 | 0.652 | 0.786 |
| G-P48L | 0.969 | 0.967 | 0.971 | 0.968 | 0.978 | 0.971 |
| G-P48k40 | 0.961 | 0.957 | 0.963 | 0.958 | 0.975 | 0.963 |
| H-A | 0.748 | 0.748 | 0.748 | 0.748 | 0.748 | 0.748 |
| H-B | 0.792 | 0.805 | 0.785 | 0.802 | 0.792 | 0.806 |

### T4 — Re(T/ω) worst over 1–35 m/s (T counts per deg/s, > 0 damps), κ 1, 2 ms transport


**ages 1–10 (age 0)**

| loop | 5 Hz | 7 Hz | 10 Hz | 13 Hz | 16 Hz | 20 Hz | 25 Hz |
|---|---|---|---|---|---|---|---|
| V294 | +1.33 | +0.67 | +0.05 | -0.25 | -0.39 | -0.44 | -0.41 |
| V295 | +2.46 | +1.24 | +0.09 | -0.47 | -0.73 | -0.82 | -0.76 |
| V282 | +17.98 | +10.06 | +1.82 | -3.50 | -6.78 | -8.87 | -9.05 |
| P2 | -0.57 | -0.44 | -0.39 | -0.37 | -0.35 | -0.34 | -0.31 |
| F2 | -0.84 | -0.84 | -0.86 | -0.84 | -0.79 | -0.69 | -0.55 |
| D2a | -0.57 | -0.44 | -0.39 | -0.37 | -0.35 | -0.34 | -0.31 |
| B0r | -0.84 | -0.84 | -0.86 | -0.84 | -0.79 | -0.69 | -0.55 |
| E1-splitP | -1.98 | -1.37 | -0.91 | -0.67 | -0.54 | -0.43 | -0.35 |
| E2-K0 | -0.43 | -0.41 | -0.39 | -0.37 | -0.36 | -0.34 | -0.31 |
| G-P48d | -0.03 | -0.14 | -0.29 | -0.37 | -0.41 | -0.43 | -0.42 |
| G-P44d | -0.12 | -0.19 | -0.30 | -0.36 | -0.39 | -0.40 | -0.39 |
| G-P48 | -0.05 | -0.16 | -0.30 | -0.37 | -0.41 | -0.43 | -0.42 |
| G-P44 | -0.14 | -0.20 | -0.30 | -0.36 | -0.39 | -0.40 | -0.39 |
| G-F24 | -0.53 | -0.70 | -0.86 | -0.91 | -0.89 | -0.80 | -0.65 |
| G-F24d | -0.53 | -0.70 | -0.86 | -0.91 | -0.89 | -0.80 | -0.65 |
| G-A22 | -0.94 | -0.95 | -0.96 | -0.92 | -0.84 | -0.69 | -0.49 |
| G-A22d | -0.93 | -0.94 | -0.96 | -0.92 | -0.84 | -0.69 | -0.49 |
| G-P48L | -0.05 | -0.16 | -0.30 | -0.37 | -0.41 | -0.43 | -0.42 |
| G-P48k40 | -0.17 | -0.25 | -0.35 | -0.41 | -0.43 | -0.44 | -0.43 |
| H-A | -0.40 | -0.36 | -0.38 | -0.40 | -0.40 | -0.40 | -0.38 |
| H-B | -0.69 | -0.78 | -0.89 | -0.91 | -0.87 | -0.78 | -0.63 |

**ages 11–20 (age 10)**

| loop | 5 Hz | 7 Hz | 10 Hz | 13 Hz | 16 Hz | 20 Hz | 25 Hz |
|---|---|---|---|---|---|---|---|
| V294 | +0.91 | +0.05 | -0.63 | -0.81 | -0.74 | -0.48 | -0.13 |
| V295 | +1.69 | +0.08 | -1.17 | -1.50 | -1.36 | -0.89 | -0.25 |
| V282 | +9.93 | -0.83 | -10.80 | -15.03 | -15.03 | -10.95 | -3.63 |
| P2 | -0.74 | -0.42 | -0.23 | -0.15 | -0.13 | -0.20 | -0.24 |
| F2 | -1.68 | -1.62 | -1.47 | -1.20 | -0.89 | -0.52 | -0.10 |
| D2a | -0.74 | -0.42 | -0.23 | -0.15 | -0.13 | -0.20 | -0.24 |
| B0r | -1.68 | -1.62 | -1.47 | -1.20 | -0.89 | -0.52 | -0.10 |
| E1-splitP | -2.35 | -1.38 | -0.63 | -0.30 | -0.15 | -0.18 | -0.22 |
| E2-K0 | -0.67 | -0.44 | -0.25 | -0.17 | -0.14 | -0.20 | -0.24 |
| G-P48d | -0.21 | -0.12 | -0.13 | -0.15 | -0.18 | -0.29 | -0.35 |
| G-P44d | -0.29 | -0.17 | -0.14 | -0.15 | -0.17 | -0.26 | -0.32 |
| G-P48 | -0.23 | -0.14 | -0.13 | -0.15 | -0.18 | -0.29 | -0.35 |
| G-P44 | -0.31 | -0.18 | -0.14 | -0.15 | -0.17 | -0.26 | -0.32 |
| G-F24 | -1.49 | -1.65 | -1.64 | -1.40 | -1.06 | -0.63 | -0.13 |
| G-F24d | -1.49 | -1.65 | -1.64 | -1.40 | -1.06 | -0.63 | -0.13 |
| G-A22 | -1.69 | -1.63 | -1.43 | -1.11 | -0.73 | -0.31 | +0.10 |
| G-A22d | -1.68 | -1.63 | -1.43 | -1.11 | -0.73 | -0.31 | +0.10 |
| G-P48L | -0.23 | -0.14 | -0.13 | -0.15 | -0.18 | -0.29 | -0.36 |
| G-P48k40 | -0.38 | -0.24 | -0.18 | -0.17 | -0.19 | -0.28 | -0.34 |
| H-A | -0.40 | -0.36 | -0.38 | -0.40 | -0.40 | -0.40 | -0.38 |
| H-B | -1.62 | -1.69 | -1.62 | -1.36 | -1.02 | -0.60 | -0.12 |

**ages 21–30 (age 20)**

| loop | 5 Hz | 7 Hz | 10 Hz | 13 Hz | 16 Hz | 20 Hz | 25 Hz |
|---|---|---|---|---|---|---|---|
| V294 | +0.41 | -0.59 | -1.07 | -0.85 | -0.40 | +0.15 | +0.41 |
| V295 | +0.76 | -1.09 | -1.99 | -1.58 | -0.74 | +0.27 | +0.76 |
| V282 | +0.91 | -11.56 | -19.29 | -17.07 | -9.32 | +2.11 | +9.05 |
| P2 | -0.70 | -0.18 | +0.13 | +0.05 | -0.07 | -0.17 | -0.25 |
| F2 | -2.35 | -2.10 | -1.52 | -0.92 | -0.32 | +0.29 | +0.52 |
| D2a | -0.70 | -0.18 | +0.13 | +0.05 | -0.07 | -0.17 | -0.25 |
| B0r | -2.35 | -2.10 | -1.52 | -0.92 | -0.32 | +0.29 | +0.52 |
| E1-splitP | -2.35 | -0.97 | -0.02 | +0.08 | -0.03 | -0.14 | -0.24 |
| E2-K0 | -0.72 | -0.24 | +0.09 | +0.05 | -0.07 | -0.17 | -0.25 |
| G-P48d | -0.17 | +0.13 | +0.23 | +0.05 | -0.13 | -0.27 | -0.36 |
| G-P44d | -0.25 | +0.07 | +0.21 | +0.05 | -0.12 | -0.25 | -0.33 |
| G-P48 | -0.19 | +0.12 | +0.23 | +0.05 | -0.13 | -0.27 | -0.36 |
| G-P44 | -0.27 | +0.06 | +0.21 | +0.05 | -0.11 | -0.24 | -0.33 |
| G-F24 | -2.30 | -2.28 | -1.79 | -1.13 | -0.41 | +0.32 | +0.62 |
| G-F24d | -2.30 | -2.28 | -1.79 | -1.13 | -0.41 | +0.32 | +0.62 |
| G-A22 | -2.28 | -2.01 | -1.36 | -0.70 | -0.10 | +0.42 | +0.45 |
| G-A22d | -2.27 | -2.00 | -1.36 | -0.70 | -0.10 | +0.42 | +0.45 |
| G-P48L | -0.19 | +0.12 | +0.23 | +0.04 | -0.14 | -0.28 | -0.36 |
| G-P48k40 | -0.37 | +0.02 | +0.21 | +0.06 | -0.11 | -0.26 | -0.36 |
| H-A | -0.40 | -0.36 | -0.38 | -0.40 | -0.40 | -0.40 | -0.38 |
| H-B | -2.40 | -2.28 | -1.73 | -1.07 | -0.38 | +0.32 | +0.59 |

### T4b — phase fragility (round-2 F3c): Re(T/ω) at 13 and 20 Hz over 16 conditions (κ 1/0.866 × transport 2/6 ms × ages 0–9/1–10/11–20/21–30), candidate worst ÷ V295 worst in the SAME condition (>1 = more anti-damping than V295 there; only negative candidate values count)

| cand | 13 Hz: conds >1× V295 | worst ratio (cond) | 20 Hz: conds >1× | worst ratio (cond) | 13 Hz worst-vs-worst | 20 Hz worst-vs-worst |
|---|---|---|---|---|---|---|
| P2 | 2/16 | 1.31 (κ0.866 d2 e-1) | 4/16 | inf (κ1 d2 e20) | 0.41 | 0.57 |
| F2 | 8/16 | 2.44 (κ0.866 d2 e-1) | 0/16 | 0.92 (κ0.866 d2 e-1) | 0.72 | 0.71 |
| D2a | 2/16 | 1.30 (κ0.866 d2 e-1) | 4/16 | inf (κ1 d2 e20) | 0.41 | 0.57 |
| B0r | 8/16 | 2.44 (κ0.866 d2 e-1) | 0/16 | 0.92 (κ0.866 d2 e-1) | 0.72 | 0.71 |
| E1-splitP | 7/16 | 2.37 (κ0.866 d2 e-1) | 4/16 | inf (κ1 d2 e20) | 0.58 | 0.62 |
| E2-K0 | 2/16 | 1.32 (κ0.866 d2 e-1) | 4/16 | inf (κ1 d2 e20) | 0.42 | 0.58 |
| G-P48d | 3/16 | 1.31 (κ0.866 d2 e-1) | 6/16 | inf (κ1 d2 e20) | 0.51 | 0.78 |
| G-P44d | 2/16 | 1.27 (κ0.866 d2 e-1) | 6/16 | inf (κ1 d2 e20) | 0.47 | 0.72 |
| G-P48 | 3/16 | 1.33 (κ0.866 d2 e-1) | 6/16 | inf (κ1 d2 e20) | 0.51 | 0.78 |
| G-P44 | 2/16 | 1.28 (κ0.866 d2 e-1) | 6/16 | inf (κ1 d2 e20) | 0.47 | 0.72 |
| G-F24 | 8/16 | 2.59 (κ0.866 d2 e-1) | 2/16 | 1.05 (κ0.866 d2 e-1) | 0.84 | 0.83 |
| G-F24d | 8/16 | 2.59 (κ0.866 d2 e-1) | 2/16 | 1.05 (κ0.866 d2 e-1) | 0.84 | 0.83 |
| G-A22 | 8/16 | 2.97 (κ0.866 d2 e-1) | 1/16 | 1.07 (κ0.866 d2 e-1) | 0.67 | 0.66 |
| G-A22d | 8/16 | 2.96 (κ0.866 d2 e-1) | 1/16 | 1.07 (κ0.866 d2 e-1) | 0.67 | 0.66 |
| G-P48L | 3/16 | 1.33 (κ0.866 d2 e-1) | 6/16 | inf (κ1 d2 e20) | 0.51 | 0.78 |
| G-P48k40 | 5/16 | 1.44 (κ0.866 d2 e-1) | 6/16 | inf (κ1 d2 e20) | 0.53 | 0.79 |
| H-A | 2/16 | 1.19 (κ1 d2 e-1) | 6/16 | inf (κ1 d2 e20) | 0.46 | 0.65 |
| H-B | 8/16 | 2.61 (κ0.866 d2 e-1) | 1/16 | 1.03 (κ0.866 d2 e-1) | 0.82 | 0.81 |

### T5 — tracking proxies, crossover, stiffness (nominal member, κ 1, ages 1–10)

`hold` = |T_ref(0.05 Hz)| min over ≥ 8 m/s (linear turn-hold proxy; the integrator CLAMP is not in a linear model). `hold I-frozen` = the same with Ki 0 (every freeze / reset / bleed / bound / saturated state). `trk` = |T_ref| over 0.1–1 Hz, min–max over ≥ 8 m/s. `|T_ref| 1.6–3` = max over ≥ 8 m/s (all speeds in brackets). Stiffness = DC T per deg (inf = integrator).

| cand | fc range nominal (Hz) | \|T_ref\| 1.6–3 Hz | hold | hold I-frozen | trk 0.1–1 Hz | Ms | DC stiffness |
|---|---|---|---|---|---|---|---|
| P2 | 0.43–1.90 | 0.99 (1.00) | 0.997 | 0.427 | 0.38–1.11 | 1.27 | inf (I) |
| F2 | 0.41–1.86 | 0.93 (0.96) | 0.996 | 0.413 | 0.38–1.11 | 1.33 | inf (I) |
| D2a | 0.43–1.90 | 0.99 (1.00) | 0.997 | 0.429 | 0.38–1.11 | 1.27 | inf (I) |
| B0r | 0.42–1.86 | 0.93 (0.96) | 0.997 | 0.416 | 0.38–1.11 | 1.33 | inf (I) |
| E1-reset | 0.43–1.90 | 0.99 (1.00) | 0.997 | 0.427 | 0.38–1.11 | 1.27 | inf (I) |
| E1-cal | 0.43–1.90 | 0.99 (1.00) | 0.997 | 0.427 | 0.38–1.11 | 1.27 | inf (I) |
| E1-bleed | 0.43–1.90 | 0.99 (1.00) | 0.997 | 0.427 | 0.38–1.11 | 1.27 | inf (I) |
| E1-freeze | 0.43–1.90 | 0.99 (1.00) | 0.997 | 0.427 | 0.38–1.11 | 1.27 | inf (I) |
| E1-sched | 0.43–1.90 | 0.99 (1.00) | 0.997 | 0.427 | 0.38–1.11 | 1.27 | inf (I) |
| E1-splitP | 0.62–2.92 | 1.24 (1.24) | 0.991 | 0.571 | 0.55–1.02 | 1.71 | inf (I) |
| E2-R1 | 0.43–1.90 | 0.99 (1.00) | 0.997 | 0.427 | 0.38–1.11 | 1.27 | inf (I) |
| E2-S | 0.43–1.90 | 0.99 (1.00) | 0.997 | 0.427 | 0.38–1.11 | 1.27 | inf (I) |
| E2-A2 | 0.43–1.90 | 0.99 (1.00) | 0.997 | 0.427 | 0.38–1.11 | 1.27 | inf (I) |
| E2-A3 | 0.43–1.90 | 0.99 (1.00) | 0.997 | 0.427 | 0.38–1.11 | 1.27 | inf (I) |
| E2-A2-X | 0.43–1.90 | 0.99 (1.00) | 0.997 | 0.427 | 0.38–1.11 | 1.27 | inf (I) |
| E2-L | 0.43–1.90 | 0.99 (1.00) | 0.997 | 0.427 | 0.38–1.11 | 1.27 | inf (I) |
| E2-K0 | 0.01–2.12 | 0.77 (0.77) | 0.878 | 0.427 | 0.29–0.96 | 1.26 | 48 (min ≥8 m/s) + fork integral |
| G-P48d | 0.37–2.01 | 0.83 (0.83) | 0.998 | 0.439 | 0.30–1.12 | 1.25 | inf (I) |
| G-P44d | 0.35–1.89 | 0.85 (0.85) | 0.997 | 0.428 | 0.28–1.12 | 1.24 | inf (I) |
| G-P48 | 0.32–2.00 | 0.83 (0.83) | 0.994 | 0.358 | 0.29–1.12 | 1.25 | inf (I) |
| G-P44 | 0.31–1.89 | 0.85 (0.85) | 0.993 | 0.347 | 0.29–1.12 | 1.24 | inf (I) |
| G-F24 | 0.28–1.72 | 0.77 (0.77) | 0.991 | 0.323 | 0.27–1.11 | 1.30 | inf (I) |
| G-F24d | 0.33–1.72 | 0.77 (0.77) | 0.996 | 0.402 | 0.27–1.11 | 1.30 | inf (I) |
| G-A22 | 0.26–1.53 | 0.81 (0.81) | 0.988 | 0.308 | 0.26–1.10 | 1.30 | inf (I) |
| G-A22d | 0.33–1.52 | 0.81 (0.81) | 0.995 | 0.386 | 0.26–1.10 | 1.30 | inf (I) |
| G-P48L | 0.27–2.08 | 0.87 (0.87) | 0.994 | 0.355 | 0.20–1.12 | 1.26 | inf (I) |
| G-P48k40 | 0.27–2.27 | 0.82 (0.87) | 0.983 | 0.377 | 0.30–1.03 | 1.27 | inf (I) |
| H-A | 0.43–1.97 | 0.94 (0.95) | 0.997 | 0.429 | 0.37–1.10 | 1.27 | inf (I) |
| H-B | 0.41–1.92 | 0.88 (0.90) | 0.997 | 0.416 | 0.37–1.11 | 1.33 | inf (I) |

### T6 — the I-frozen loop (Ki 0) and hands-on fade floors

The small-signal loop of every freeze / reset / bleed / leak / angle-bound / clamp-saturated state. R2 box gate (bars 45/30). Fade floors: PM over every member at κ 1 (bar shown only for reference — the hand's own impedance is not modelled).

| cand | PD tier A (binding) | PD tier B (binding; ring) | PD fails R2 box | fade 0.297 min PM | fade 0.195 min PM | fade 0.297 min GM↑ / GM↓ |
|---|---|---|---|---|---|---|
| P2 | 55.4 (b_lo@8.00 FB.83, fc 2.91) | 31.6 (b_q*ms_free+h10@15.75 FB.83, fc 1.39); ring 1.42 Hz ζ 0.113 | 0 | 97.7 | 120.5 | 27.2 / — |
| F2 | 54.7 (b_lo@8.00 FB.83, fc 2.93) | 31.1 (b_q*ms_free+h10@15.75 FB.83, fc 1.39); ring 1.43 Hz ζ 0.115 | 0 | 97.0 | 120.5 | 18.8 / — |
| D2a | 55.4 (b_lo@8.00 FB.83, fc 2.91) | 31.3 (b_q*ms_free+h10@17.50 FB.83, fc 1.57); ring 1.62 Hz ζ 0.113 | 0 | 97.7 | 120.5 | 27.2 / — |
| B0r | 54.7 (b_lo@8.00 FB.83, fc 2.93) | 30.9 (b_q*ms_free+h10@17.50 FB.83, fc 1.57); ring 1.63 Hz ζ 0.115 | 0 | 97.0 | 120.5 | 18.8 / — |
| E1-splitP | 25.9 (b_lo@8.00 FB.83, fc 3.71) | 7.4 (b_q*ms_free+h10@17.50 FB.83, fc 1.81); ring 1.83 Hz ζ 0.033 | 3185 | 56.2 | 84.0 | 14.8 / — |
| E2-K0 | 55.4 (b_lo@8.00 FB.83, fc 2.91) | 31.6 (b_q*ms_free+h10@15.75 FB.83, fc 1.39); ring 1.42 Hz ζ 0.113 | 0 | 97.7 | 120.5 | 27.2 / — |
| G-P48d | 62.0 (b_lo@8.00 FB.83, fc 3.19) | 36.2 (b_q*ms_free+h10@17.50 FB.83, fc 1.60); ring 1.65 Hz ζ 0.143 | 0 | 103.3 | 124.5 | 26.3 / — |
| G-P44d | 62.5 (b_lo@8.00 FB.83, fc 3.06) | 36.5 (b_q*ms_free+h10@17.50 FB.83, fc 1.58); ring 1.63 Hz ζ 0.138 | 0 | 106.5 | 129.0 | 26.7 / — |
| G-P48 | 62.1 (b_lo@8.00 FB.83, fc 3.19) | 50.1 (b_q*J1.0+h10@26.90 FB.83, fc 1.82); ring 2.04 Hz ζ 0.250 | 0 | 103.3 | 124.5 | 26.3 / — |
| G-P44 | 62.5 (b_lo@8.00 FB.83, fc 3.06) | 50.1 (b_lo*J_hi+h10@8.00 FB.83, fc 2.00); ring 2.17 Hz ζ 0.334 | 0 | 106.5 | 129.0 | 26.7 / — |
| G-F24 | 61.5 (b_lo@8.00 FB1.155, fc 3.47) | 44.0 (b_lo*tau6+h10@8.00 FB1.155, fc 3.47); ring 4.46 Hz ζ 0.251 | 0 | 108.9 | 133.8 | 19.0 / — |
| G-F24d | 61.5 (b_lo@8.00 FB1.155, fc 3.47) | 36.4 (b_q*ms_free+h10@17.50 FB.83, fc 1.57); ring 1.62 Hz ζ 0.138 | 0 | 108.9 | 133.8 | 19.0 / — |
| G-A22 | 64.1 (b_lo@8.00 FB.83, fc 2.78) | 50.0 (b_lo*J_hi+h10@8.00 FB.83, fc 1.89); ring 2.17 Hz ζ 0.331 | 0 | 112.9 | 142.0 | 19.6 / — |
| G-A22d | 64.2 (b_lo@8.00 FB.83, fc 2.78) | 37.1 (b_q*ms_free+h10@17.50 FB.83, fc 1.54); ring 1.60 Hz ζ 0.133 | 0 | 112.9 | 142.0 | 19.6 / — |
| G-P48L | 60.0 (b_lo@8.00 FB.83, fc 3.24) | 48.4 (b_lo*J_hi+h10@8.00 FB.83, fc 2.08); ring 2.24 Hz ζ 0.331 | 0 | 103.3 | 124.5 | 26.1 / — |
| G-P48k40 | 55.6 (b_lo@1.00 FB.83, fc 3.01) | 44.9 (b_lo*ms_free+h10@8.25 FB.83, fc 1.96); ring 2.08 Hz ζ 0.302 | 0 | 89.6 | 109.8 | 25.8 / — |
| H-A | 54.5 (b_lo@8.00 FB1.155, fc 3.49) | 36.7 (b_q*ms_free@17.50 FB1.155, fc 1.67); ring 1.70 Hz ζ 0.162 | 0 | 100.6 | 122.3 | 26.8 / — |
| H-B | 56.1 (b_lo@8.00 FB.83, fc 3.05) | 33.1 (b_q*ms_free+h10@17.50 FB.83, fc 1.58); ring 1.64 Hz ζ 0.127 | 0 | 98.7 | 121.6 | 18.5 / — |

### T7 — the physical frame points (report): PM over tier A / tier B at κ = 1/1.155 and 1/0.962 under FA and FB

| cand | tier A min (binding) | tier B min (binding) |
|---|---|---|
| P2 | 43.2 (J_hi@1.00 FAc, fc 1.20) | 9.3 (b_q*ms_free+h10@15.75 FAc, fc 1.26) |
| F2 | 43.4 (J_hi@1.00 FAc, fc 1.21) | 10.8 (b_q*ms_free+h10@15.75 FBc, fc 1.36) |
| D2a | 43.2 (J_hi@1.00 FAc, fc 1.20) | 9.3 (b_q*ms_free+h10@15.75 FAc, fc 1.26) |
| B0r | 43.4 (J_hi@1.00 FAc, fc 1.21) | 10.8 (b_q*ms_free+h10@15.75 FBc, fc 1.36) |
| E1-splitP | 23.3 (b_lo@8.00 FBc, fc 3.65) | 0.0 (b_q*ms_free+h10@20.50 FBc, fc 2.03) |
| E2-K0 | 56.1 (b_lo@8.00 FBc, fc 2.94) | 32.4 (b_q*ms_free+h10@15.75 FBc, fc 1.39) |
| G-P48d | 53.0 (J_hi@1.00 FAc, fc 1.18) | 18.5 (b_q*ms_free+h10@15.75 FAc, fc 1.27) |
| G-P44d | 52.2 (J_hi@1.00 FAc, fc 1.11) | 18.1 (b_q*ms_free+h10@15.75 FAc, fc 1.25) |
| G-P48 | 53.0 (J_hi@1.00 FAc, fc 1.18) | 35.3 (b_q*J1.0+h10@26.90 FBc, fc 1.74) |
| G-P44 | 52.2 (J_hi@1.00 FAc, fc 1.11) | 35.4 (b_q*J1.0+h10@27.00 FBc, fc 1.71) |
| G-F24 | 51.9 (J_hi@1.00 FAc, fc 1.06) | 35.8 (b_q*J1.0+h10@27.00 FBc, fc 1.70) |
| G-F24d | 51.9 (J_hi@1.00 FAc, fc 1.06) | 19.6 (b_q*ms_free+h10@15.75 FAc, fc 1.24) |
| G-A22 | 49.4 (J_hi@1.00 FBo, fc 0.96) | 34.3 (b_q*J1.0+h10@26.90 FBc, fc 1.68) |
| G-A22d | 49.4 (J_hi@1.00 FBo, fc 0.96) | 18.0 (b_q*ms_free+h10@15.75 FBc, fc 1.33) |
| G-P48L | 53.0 (J_hi@1.00 FAc, fc 1.18) | 35.3 (b_q*J1.0+h10@26.90 FBc, fc 1.74) |
| G-P48k40 | 53.6 (J_hi@1.00 FBc, fc 1.58) | 35.8 (b_q*J1.0+h10@26.90 FBc, fc 1.82) |
| H-A | 48.7 (ms_free@8.75 FBo, fc 1.21) | 18.5 (b_q*ms_free@15.75 FBo, fc 1.26) |
| H-B | 46.8 (J_hi@1.00 FAc, fc 1.20) | 14.7 (b_q*ms_free+h10@15.75 FAc, fc 1.26) |

### T8 — E2-K0's fork angle integral (τ_o 1 s, 60 ms, 100 Hz) as its own loop, every R2 member, κ 1, every other speed

- outer-loop min PM 77.4° (b_hi@26.90, fc 0.10 Hz); min GM↑ 14.9 dB (b_lo*ms_free+h10@12.00)

### T9 — the ms_free products one by one: worst PM over the gated frame box and both hold ages, the exact ring there, and the speed span where any frame/age sits below 30°

| cand | b_lo×ms_free min (point; ring) | span < 30° | b_q×ms_free min (point; ring) | span < 30° |
|---|---|---|---|---|
| P2 | 13.3 (b_lo*ms_free+h10@11.90 FA.83; ring 0.81 Hz ζ 0.049) | 6.50–13.50 m/s | 8.2 (b_q*ms_free+h10@15.75 FA.83; ring 1.27 Hz ζ 0.028) | 12.50–24.00 m/s |
| F2 | 13.0 (b_lo*ms_free+h10@11.90 FA.83; ring 0.82 Hz ζ 0.050) | 6.00–13.25 m/s | 9.6 (b_q*ms_free+h10@15.75 FB.83; ring 1.38 Hz ζ 0.034) | 12.50–24.25 m/s |
| D2a | 13.3 (b_lo*ms_free+h10@11.90 FA.83; ring 0.81 Hz ζ 0.049) | 6.50–13.50 m/s | 8.2 (b_q*ms_free+h10@15.75 FA.83; ring 1.27 Hz ζ 0.028) | 12.50–24.00 m/s |
| B0r | 13.0 (b_lo*ms_free+h10@11.90 FA.83; ring 0.82 Hz ζ 0.050) | 6.00–13.25 m/s | 9.6 (b_q*ms_free+h10@15.75 FB.83; ring 1.38 Hz ζ 0.034) | 12.50–24.25 m/s |
| E1-splitP | 5.7 (b_lo*ms_free+h10@8.00 FB.83; ring 2.56 Hz ζ 0.037) | 1.00–18.50 m/s | 0.0 (b_q*ms_free+h10@19.00 FA.83; ring 1.77 Hz ζ -0.000) | 3.75–35.00 m/s |
| E2-K0 | 41.3 (b_lo*ms_free+h10@8.25 FB.83; ring 1.99 Hz ζ 0.253) | none | 31.6 (b_q*ms_free+h10@15.75 FB.83; ring 1.42 Hz ζ 0.113) | none |
| G-P48d | 34.7 (b_lo*ms_free+h10@11.90 FA.83; ring 0.78 Hz ζ 0.120) | none | 17.0 (b_q*ms_free+h10@15.75 FA.83; ring 1.28 Hz ζ 0.061) | 13.00–22.00 m/s |
| G-P44d | 35.2 (b_lo*ms_free+h10@8.75 FA.83; ring 1.34 Hz ζ 0.231) | none | 16.7 (b_q*ms_free+h10@15.75 FA.83; ring 1.27 Hz ζ 0.058) | 13.00–22.00 m/s |
| G-P48 | 35.4 (b_lo*ms_free+h10@9.00 FA.83; ring 1.26 Hz ζ 0.227) | none | 36.6 (b_q*ms_free+h10@15.75 FA.83; ring 1.21 Hz ζ 0.110) | none |
| G-P44 | 35.2 (b_lo*ms_free+h10@8.75 FA.83; ring 1.34 Hz ζ 0.231) | none | 37.6 (b_q*ms_free+h10@20.75 FB.83; ring 1.69 Hz ζ 0.143) | none |
| G-F24 | 35.8 (b_lo*ms_free+h10@8.75 FB.83; ring 1.47 Hz ζ 0.248) | none | 36.9 (b_q*ms_free+h10@15.75 FB.83; ring 1.30 Hz ζ 0.109) | none |
| G-F24d | 35.7 (b_lo*ms_free+h10@8.75 FB.83; ring 1.47 Hz ζ 0.248) | none | 18.3 (b_q*ms_free+h10@15.75 FA.83; ring 1.26 Hz ζ 0.064) | 13.25–22.25 m/s |
| G-A22 | 35.7 (b_lo*ms_free+h10@8.75 FB.83; ring 1.44 Hz ζ 0.238) | none | 37.3 (b_q*ms_free+h10@15.75 FB.83; ring 1.29 Hz ζ 0.103) | none |
| G-A22d | 35.7 (b_lo*ms_free+h10@8.75 FB.83; ring 1.44 Hz ζ 0.237) | none | 18.0 (b_q*ms_free+h10@15.75 FB.83; ring 1.35 Hz ζ 0.060) | 13.25–22.25 m/s |
| G-P48L | 36.5 (b_lo*ms_free+h10@8.50 FB.83; ring 1.62 Hz ζ 0.257) | none | 37.6 (b_q*ms_free+h10@20.75 FB.83; ring 1.70 Hz ζ 0.149) | none |
| G-P48k40 | 34.8 (b_lo*ms_free+h10@11.90 FA.83; ring 0.82 Hz ζ 0.138) | none | 36.2 (b_q*ms_free+h10@15.75 FB.83; ring 1.35 Hz ζ 0.121) | none |
| H-A | 22.3 (b_lo*ms_free@11.90 FA1.155; ring 0.84 Hz ζ 0.093) | 11.00–12.75 m/s | 17.0 (b_q*ms_free@15.75 FA1.155; ring 1.34 Hz ζ 0.069) | 12.50–22.00 m/s |
| H-B | 17.8 (b_lo*ms_free+h10@11.90 FA.83; ring 0.82 Hz ζ 0.069) | 8.25–13.00 m/s | 13.5 (b_q*ms_free+h10@15.75 FA.83; ring 1.28 Hz ζ 0.048) | 12.50–23.50 m/s |
