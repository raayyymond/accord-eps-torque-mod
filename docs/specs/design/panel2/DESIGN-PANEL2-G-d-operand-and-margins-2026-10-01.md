# DESIGN PANEL 2, designer G: the D operand and the margin findings (F2, F3), 2026-10-01

**Status: DESIGN ONLY.** Nothing was built, flashed or sent, and the fork was not touched. No image or `.rwd` was written:
every patched image exists only in memory inside `g_bytes.py`. Ghidra was used read-only (`get_function_by_address`,
`get_function_callers` on stock `code.bin`); nothing was saved. Python is the `bin_decompile` env.

**Author:** designer G, a subagent working for the orchestrator `main`. Three other designers work other axes; I have not
seen their work. **I do not pick a winner** (the brief); §0.4 says what each implementation buys and costs.

**My axis (the brief):** the D term's frame (round-2 finding F2) and the margin findings (F3): ms_free × damping-corner
products at PM 13.5°, aged single corners below 45° under the strict reading, and the phase-fragile "13–25 Hz anti-damping
≤ 0.79× V295" claim. Implementations asked for: (i) P2's fresh-rate D with Kd re-sized and the frame ratio gated;
(ii) F2's held-rate D, the same; (iii) a D from the angle operand's own 10-tick-aware difference (no rate read);
(iv) optional, a lower G(v) at 10–13 m/s with its tracking price.

**Scripts** — `analysis-2020accord/studies/angle_loop/panel2/G-d-operand-and-margins/` (run with `python <script>`;
caches in `_scratch/angle_loop/G-dop/`, gitignored, regenerable):

| script | what it does | output |
|---|---|---|
| `g_ext.py` | **the extension of `panel/score_freq.py`** (imported, not forked): corrected PM, the extended member set, the frame variants, the angle-own D FRF, the kd-linear loop split | — |
| `g_selftest.py` | controls: P2/F2 rows == rev2-A's hex; `metrics_ext` == `score_freq.score` (1.4e-15); the PM correction shown point by point | `g_selftest_out.txt` |
| `g_env.py` | speed-gain envelope over Kd × the extended set × frames, plus the 20 Hz rules in both frames | `_scratch/.../env_*.json` |
| `g_fit.py` | the integer G(v) tables (ds_gate2's own LP fitter; deterministic — a re-run reproduces every table) | `g_fit_out.txt`, `g_impls_frozen.json` |
| `g_gate.py` | GATE 2 on 48 020 points per implementation: common extractor + pm_fixed + exact ρ (own periodic model) | `g_gate_<id>.txt` |
| `g_exact.py` | my own exact periodic model (== ds_model.Lifted to 1.7e-14 on fresh/held; adds box10) | — |
| `g_exactgm.py` | exact GM at the lowest-GM points; ρ at the fade floor | `g_exactgm_out.txt` |
| `g_retw.py`, `g_retw_summary.py` | Re(T/ω) 5–25 Hz over 48 conditions (frame × transport × rate-former lag × 4 hold-age sets) vs V294/V295 | `g_retw_*.txt`, `g_retw_summary.txt` |
| `g_stress.py` | two-mass stress 13–20 Hz, ζ₂ 0.02/0.05, r₂ 0.2/0.4, incl. κ 1.155 | `g_stress_out.txt` |
| `g_track.py` | the goal's own tracking metric (linear, `c1r2_trackmetric.slope`), turn-hold, \|T_ref\| 1.6–3 Hz | `g_track_*.txt` |
| `g_nl.py` | the round-2 NONLINEAR refuter's instruments (`nl_realref`, the turn-hold and small-correction experiments) on these implementations | `g_nl_realref.txt`, `g_nl_turnhold.txt`, `g_nl_small.txt` |
| `g_time.py` | **the common time scorer `c2/rev2A/score_time.py`, extended** (one subclass for the box10 operand) | `score_time_out.md`, `score_time_late_out.md`, `g_time_selftest.txt` |
| `g_cave.py`, `g_lane.py` | the caves → bytes, H1 (60 000 inputs, the D designer's V850 interpreter); the integer lane for box10 | `g_cave_out.txt`, `g_cave_<id>.hex` |
| `g_bytes.py` | every byte, applied in memory to V295, full diff | `g_bytes_out.txt` |
| `g_xcheck.py` | crux numbers re-derived on the stability refuter's independent engine (`c2r2_model`) | `g_xcheck_out.txt` |
| `g_pmfix_panel.py` | does the PM finding change any published SCORE-FREQ number? (no: 0 / 80 920) | `g_pmfix_panel_out.txt` |
| `g_explore1.py` | first exploration: PM at the round-2 binding members vs Kd, G scale and Ki (refuter's engine) | `g_explore1_out.txt` |
| `g_sfrow.py` | each implementation as a row of `score_freq`'s own table, nothing changed | `g_sfrow_out.md` |

Every decision-bearing claim is marked **EVIDENCE** (with its method) or **BELIEF**. Code is cited by address or grep string.

---

## 0. The answer on one page

### 0.1 Four findings that move the design space

1. **The shared phase-margin extractor mis-reports LEADING crossings, and rev2-A's Kd ceiling was that artefact.**
   **EVIDENCE.** Every PM routine in the kit (`score_freq._pm_all`, `ds_model.pm_all`, `ds_gate2._pm_gm_rows`,
   `c2r2_model.pm_all` and seven more; grep `% 360 - 180`) computes `((phase + 180) + 180) % 360 − 180`. For a crossing
   whose phase is in (0°, 180°) that returns `phase − 180°`, a NEGATIVE number, where the margin is `180° − phase`.
   Leading crossings appear exactly when the D term's own loop exceeds unity below the plant resonance — the low-G rows of
   an envelope search at higher Kd. rev2-A rejected P3 (Kd 41) and P4 (Kd 48) because "the envelope collapses to 0"
   (`r2a_common.REJECTED`). On the **refuter's own engine** (`g_xcheck_out.txt`, X1):

   | structure, point | shared formula | crossings (Hz, phase) | exact ρ | exact delay margin |
   |---|---|---|---|---|
   | Kd 41, b_q×J1.0 @ 14 m/s, G 40 | **−179.5°** | 0.02 −88.8°; **1.01 +0.5°**; 1.19 −37.5° | 0.9986 | **∞** |
   | Kd 48, b_q×J_hi @ 13 m/s, G 40 | **−160.5°** | 0.03 −88.6°; **0.99 +19.5°**; 1.77 −59.4° | 0.9980 | 189 ms |
   | Kd 48, b_lo @ 5 m/s, G 40 | **−164.0°** | 0.08 −91.0°; **0.65 +16.0°**; 2.29 −60.1° | 0.9917 | 146 ms |
   | Kd 48, b_q×J1.0 @ 15 m/s, G 60 | **−164.0°** | 0.03 −88.4°; **1.03 +16.0°**; 1.42 −57.3° | 0.9982 | ∞ |

   Stable, with delay margins of 146 ms to infinity: these points have 160–180° of margin, not −160°. **Every number on
   this page uses `pm_fixed = 180 − |wrap(phase)|`.** On every gated point of every implementation below, and on the
   published P2/F2 tables, `pm_fixed == pm_raw` (`g_gate_*.txt`, first line) — so **the published P2/F2/D2a/B0r margins
   are unaffected; only envelope searches at Kd > ~40 were.** Decision-bearing for my axis: it re-opens Kd 41–48.

2. **The D operand's frame, measured, and the range it can take at each speed.** **EVIDENCE, two methods, reproduced
   this session.** (a) The bytes: the gp-0x6a00 correction knots `0xC6892`/`0xC68A2` give d(gp-0x6a00)/d(lin) = **1.1551**
   for |θ_lin| < 27.7°, 1.120 / 1.083 / 1.032 / 0.993 further out, **0.962** beyond 80.8° (my LE read of the V295 image,
   sha `5c044d65…`). (b) The wire: `c2r2_frame_wire.py` re-run, r71b 0x14A: slope of dθ/dt on x/8 = 1.155 / 1.162 / 1.158 /
   1.154 in the 0–30° bins, 0.964 beyond 90°, correlation 0.9975. (c) **New: what angles are actually driven at each speed**
   (r71b, engaged, `t_cst`/`sa_deg` of `r71b_v294_ident.npz`):

   | speed | \|θ\| p95 | max | frames > 27.7° | frames > 80.8° | ⇒ D operand per deg/s of gp-0x6a00, relative to the model |
   |---|---|---|---|---|---|
   | 0–5 m/s | 280° | 374° | 29 % | 24 % | 0.866–1.04 |
   | 5–8 | 162° | 273° | 26 % | 18 % | 0.866–1.04 |
   | 8–10 | 60.5° | 99.6° | 16 % | 0.8 % | 0.866–1.04 |
   | 10–13 | 25.0° | 96.3° | 4.3 % | 0.5 % | 0.866–1.04 |
   | **13–15** | 8.0° | 22.5° | **0** | 0 | **0.866 exactly** |
   | **15–22** | 18.7° | 27.0° | **0** | 0 | **0.866 exactly** |
   | **22+** | 12.2° | 15.3° | **0** | 0 | **0.866 exactly** |

   The common scorer and every round-2 design read the rate operand as if it measured gp-0x6a00's own rate (κ = 1). **At
   13 m/s and above the true κ is 1/1.155 = 0.866 on every r71b frame**; below, 0.866–1.04. So P2's "Kd 34 = 3.21 T per
   deg/s" delivered **2.78 T per deg/s of gp-0x6a00** at highway (EVIDENCE: arithmetic on the two facts above). This page
   sizes Kd in the operand's own frame and gates the **whole box κ ∈ [0.83, 1.155]** (the brief's range, which contains the
   physical 0.866–1.04 with margin both sides) **× both readings of the identified plant's frame** (FA: J, b, k per degree of
   gp-0x6a00; FB: J, b per degree of the motor-linear angle — `|fb` divides J and b by 1.155, which is the refuter's FB
   reading rewritten in θ). For the angle-own D (iii) κ ≡ 1 by construction; only the FB reading applies.

3. **The real ceiling on a fresh-rate D is the goal's own 20 Hz criterion, at Kd 48.** **EVIDENCE (model arithmetic,
   frame-exact).** M20 (the controller's 20 Hz gain per count of x) is D-dominated: Kd 48 gives **0.981× V295** at G → 0,
   **0.976×** over the whole grid; Kd 50 exceeds it (`env_fresh_*_coarse.json`: Kd 50/52 → envelope 0, rule M20). Because
   the fresh operand gp-0x6abe and V295's gp-0x6a56 are the **same lin-frame motor rate** (gp-0x6a56 = −1.698·gp-0x6abe,
   `FUN_0003f776`), the frame ratio cancels in this comparison: the M20 rule is frame-exact for the rate D. For the held
   D the binding 20 Hz rule is Re(T/ω)₂₀ in the s = 1.155 frame (Kd 24 caps G at 2030; Kd 26 at 1136); for box10 the same
   rule binds at Kd 22. These ceilings, not the D-loop "collapse", are what limit the D.

4. **The b_q × ms_free products cannot be closed by the D at its 20 Hz ceiling without spending the goal's tracking
   metric at 15–19 m/s.** **EVIDENCE (model).** At Kd 48 (the M20 cap), closing b_q×ms_free(×tau6)(+h10) at PM ≥ 30° under
   κ 0.83 needs G at 15–19 m/s about **25 % below P2's** (G-P48 table 1015 vs P2 1359 at 17 m/s), and the linear goal metric
   then reads **0.935** on b_q×ms_free and **0.951** on nominal at 17 m/s (bar 0.95). Lowering Ki instead (the I's phase lag
   is the largest anti-damper at the 1.2–1.3 Hz crossover) lets G rise but costs MORE tracking (Ki 40: 0.903; Ki 32: 0.873),
   because the metric's 0.05–0.3 Hz content rides on the I. Deepening the 10–13 m/s dip (iv) costs 0.921. **So F3's
   b_q × ms_free item is a choice between a declared stability miss (stop band R3\*) and a declared tracking miss; this page
   delivers both, labelled, and the judges choose.** Every other F2/F3 item closes by design (§0.3).

### 0.2 The implementations (every number from a script on this page; strict = the brief + aged single corners at 45° + the refuters' ms_free products at 30°, every point at κ 0.83 / 1 / 1.155 and both plant frames)

Bytes: **diff** = bytes that differ from V295 over [0x13000, 0x100000) (rev2-A's "differ" count: P2 198, F2 183 reproduce);
**written** = instruction bytes rewritten + the whole cave + the changed 2-byte cal cells. Every row: 1 cave at `0xC4C00`.

| id | what | diff / written / RAM | GATE 2 strict: fails | tier-A min (member, v) | tier-B min (member, v) | M20 × V295 | linear goal metric ≥ 8 m/s | verdict on its own terms |
|---|---|---|---|---|---|---|---|---|
| rev2A-P2 (ref) | fresh D Kd 34, published | 198 / 213 / 0 | **1 496** (197 even on the brief's literal set: the frame) | 37.7 (J_hi+h10 κ0.83, 1) | **6.4** (b_q×ms_free×tau6+h10 κ0.83, 15.75) | 0.69 | 0.957 | refuted by F2/F3 (reproduced) |
| rev2A-F2 (ref) | held D Kd 20, published | 183 / 197 / 0 | **1 562** | 38.1 | 9.6 | 0.71 | 0.957 | refuted by F2/F3 |
| **G-P48** | (i) fresh D **Kd 48**, table under the FULL strict set | 198 / 213 / 0 | **0** | 47.1 (J_hi+h10 κ0.83, 1) | 33.6 (b_lo×ms_free×tau6+h10 κ0.83, 9) | 0.976 | **0.935 FAIL** (b_q×ms_free, 17); nominal 0.951 | closes F2 + all F3 margins; **declared tracking miss 13.5–19 m/s** |
| **G-P48d** | (i) fresh D Kd 48, b_q×ms_free products **declared** | 198 / 213 / 0 | 381, **all b_q×ms_free** (min 15.2°, ring 1.28 Hz ζ 0.055) | 47.1 | 33.6 (b_lo×ms_free×tau6+h10) | 0.976 | **0.961 PASS** | closes F2 + aged + b_lo×ms_free; **declared b_q×ms_free, stop band R3\*** |
| G-P44 | (i) fresh D Kd 44, full set | 198 / 213 / 0 | **0** | 46.6 (J_hi+h10 κ0.83, 1) | 33.3 (b_lo×ms_free×tau6+h10 fb κ0.83, 8.5) | 0.895 | 0.930 FAIL | M20 margin 10 %, lower envelope |
| **G-P44d** | (i) fresh D Kd 44, b_q×ms_free declared | 198 / 213 / 0 | 386, all b_q×ms_free (min 14.9°, ring 1.27 Hz ζ 0.052) | 46.6 | 33.3 | 0.895 | **0.954 PASS** | as G-P48d with 10 % more 20 Hz margin, 0.007 less tracking margin |
| G-P48L | (iv) G-P48 with the 9.5–13.5 m/s dip −20 % | 198 / 213 / 0 | **0** | 47.1 | 34.2 (b_lo×ms_free×tau6+h10, 8.25; ring ζ 0.189) | 0.978 | 0.921 FAIL | the dip's price: −0.014 to −0.037 |
| G-P48k40 / k32 | (i) Kd 48 + Ki 40 / 32 | 198 / 213 / 0 | 0 (k40) / not gated | — | — | — | 0.903 / 0.873 FAIL | Ki costs more tracking than G — rejected |
| **G-F24** | (ii) held D **Kd 24**, full set | 183 / 197 / 0 | **0** | 46.9 (J_hi+h10 κ0.83, 1) | 33.7 (b_lo×ms_free×tau6+h10 fb κ0.83, 8.75) | 0.83 | **0.918 FAIL** | closes F2/F3 margins at a 9–36 % stiffness cost vs P2; 13 Hz anti-damping 2.4× V295 |
| G-F24d | (ii) held D Kd 24, b_q×ms_free declared | 183 / 197 / 0 | 356, all b_q×ms_free | 46.9 | 33.7 | 0.83 | 0.947 FAIL | misses the goal metric by 0.003 |
| **G-A22** | (iii) **angle-own D**, box10 Kd 22 (k_op 64), full set | 247 / 267 / **2** (gp-0x6c44, -0x6c40) | **0** | 46.5 (J_hi+h10, 1) | 33.7 (b_lo×ms_free×tau6+h10 fb, 8.75) | 0.75 (vs V295 at κ 0.866) | 0.909 FAIL | frame-exact; lowest envelope; texture §7 |
| G-A22d | (iii) box10, b_q×ms_free declared | 247 / 267 / 2 | 250, all b_q×ms_free (min 16.1°) | 46.5 | 33.7 | 0.75 | 0.937 FAIL | — |

**Time domain (rev2-A's common time scorer, 18 scenarios × 12 speeds × 5 members): every implementation passes every
pre-registered bar** (§7.3). The re-sized D halves P2's firm-hand release lurch on b_lo×J_hi (10.2° → 5.9°) and pulls the
hard-turn 1.6–3 Hz ratio 1.40 → 1.07; the tables cost small-signal tracking at the 10–12.5 m/s dip (§7.2c).

### 0.3 The F2 / F3 findings and how each is resolved

| finding (round 2) | resolution on this page | evidence |
|---|---|---|
| **F2** D operand frame 1.155 near centre; P2/F2/D2a/B0r fail GATE 2 on gated members once it is applied (tier A 43.2–44.1°, tier B 24.6–28.3°) | **Kd re-sized in the operand's frame and the ratio gated, not assumed.** Every implementation is gated at κ 0.83, 1, 1.155 on every member and speed, under both plant-frame readings. G-P48/P48d: tier A ≥ 47.1°, tier B ≥ 33.6° on that box (P2 on the same box: 37.7° / 6.4°). Reproduced the refuter's F1 rows first (§4.3). | `g_gate_*.txt`, `g_xcheck_*.txt` |
| **F3a** ms_free × {b_lo, b_q} products reach PM 13.5° (ζ 0.047) | **b_lo × ms_free (the bias-corrected damping): closed by design** in every implementation (≥ 33.6°, ring 0.77 Hz ζ ≥ 0.117). **b_q × ms_free: closed by design in G-P48 / G-F24 / G-A22 (≥ 34.9°) at a declared tracking cost; declared in the "d" variants (min 15.2° at κ 0.83, 22.2° at κ 1; ring 1.28 Hz ζ 0.055), with stop band R3\*.** Credibility of b_q × ms_free is a ruling for the orchestrator: two stress corners at once (b/4 with J 1.66–2.08, "J unidentified above 10 m/s"). | §4, §8 |
| **F3b** aged single corners below 45° under the strict reading (J_hi+h10 42.2°, ms_free+h10 43.5°) | **Closed by design**: the strict reading is this page's GATE. G-P48/P48d: J_hi+h10 **47.1°**, ms_free+h10 **49.3°**, at κ 0.83 (the worst frame). | `g_gate_G-P48.txt` |
| **F3c** "13–25 Hz anti-damping ≤ 0.79× V295" is phase-fragile (1.12× at ages 0–9; ≥ 1× in the tau6-aged corner with a rate-former lag) | **The ratio claim is withdrawn for every structure, P2 included** — it fails in 15–31 of 48 conditions for the fresh D, 24 of 48 for held and box10 (§5). **Replaced by a worst-case-vs-worst-case statement that holds:** over all 48 conditions the fresh-D implementations anti-damp 13–25 Hz at **0.57–1.00× V295's own worst** (G-P48), **0.54–0.92×** (G-P44); the held / box10 ones 0.64–0.86×. The goal's actual 20 Hz criterion (M20/L20 ≤ V295) passes in every frame. Any new 5–30 Hz line is R4's job on the car. | `g_retw_summary.txt` |
| refuter F2 (P2's claim fragile) / F8 (fresh-D sign rests on pol) | (ii) and (iii) remove the pol dependence: the held operand carries pol like θ does; the angle-own D IS θ. (i) keeps H10 (pol = −1, record EVIDENCE) and the R1 INVERTED check. | §9 |

### 0.4 What each implementation buys (no winner — the judges pick)

- **G-P48d** is the only implementation here that closes F2 and every F3 item except b_q × ms_free **and** passes the
  goal's linear tracking metric (0.961). Same instruction bytes as P2; vs P2 only the Kd record (34→48) and the six table rows
  (data in the cave) change. It spends the
  20 Hz gain margin almost entirely (M20 0.976×) and moves P2's 20–25 Hz anti-damping from 0.62–0.71× to 0.85–1.00× of
  V295's worst case, while removing 28 % of P2's 5 Hz anti-damping (§5). **Its cost lands at the 10–12.5 m/s dip:** small
  corrections with friction track worse than P2's (±0.5° bc in-phase gain −0.07 vs 0.60; ±1° bc 9 dwell-then-jump events vs 1,
  §7.2c) — the margin closure deepens the dip (G 474 vs 537) and adds D there. On the real r71b paths it is neutral (+0.004 at
  15–22 m/s, −0.003 at 8–15, §7.2).
- **G-P44d** trades 0.007 of tracking margin and some low-speed stiffness for a 10 % M20 margin and 0.78–0.92× at 20–25 Hz.
- **G-P48** closes everything in F3 by design and pre-declares a tracking miss at 13.5–19 m/s (linear metric 0.951 on
  nominal at 17 m/s, −0.021 vs P2; 0.935 on b_q × ms_free; −0.021 on the real r71b paths at 15–22 m/s) — in the very band
  where the integrator clamp (F1) already costs 0.15 on the real paths.
- **G-F24 / G-F24d** (held D) close the margins but cost 9–36 % / 5–24 % of P2's stiffness and keep F2's 13–15 Hz
  anti-damping at 1.5–2.4× V295 (condition-matched). **G-A22 / A22d** (angle-own D) are frame-exact and pol-free but have the lowest envelope (box10's 10.5 ms of
  operand lag), need two RAM words and 54 more cave bytes, and quantise the D at 10 deg/s per count (§7).

---

## 1. F2: the D operand's frame, and how the D is sized

### 1.1 The facts (each EVIDENCE, method in §0.1 item 2)

- gp-0x6a00 (P and I) = the motor-linear angle **plus** Honda's correction C(lin); slope 1.155 for |θ_lin| < 27.7°,
  0.962 beyond 80.8°.
- gp-0x6abe (fresh D, i) and gp-0x6a56 (held D, ii) are the **motor-linear rate**: x = 8 counts per deg/s of lin,
  gp-0x6abe = −4.712 per deg/s of lin (`FUN_0003f776`, `FUN_00041464`; the D designer's and the refuter's decompiles, and
  **my own decompile of `FUN_0003f776` on stock `code.bin` this session**: gp-0x6a56 = gp-0x6752 ·
  ((gp-0x6abe · 0x30 · u16 tp+0x713a) >> 15), clamped ±12000, zeroed when gp-0x6abe + 13000 > 0x6590 unsigned — the cave's
  guard is that same form).
- So per deg/s of gp-0x6a00 the rate operand reads **×1/s(θ)**: 0.866 near centre, 1.04 outward.
- On r71b the wheel never left the 1.155 band at ≥ 13 m/s (§0.1 table).

### 1.2 What the identified plant's frame changes (BELIEF which reading is right; both are gated)

The r71b fit (`plib.py`, `oe_lib.py`) is `J·al + b·om + k·th + F·sgn(om) = u + d` with **th from 0x14A (gp-0x6a00) and om
= x/8 (lin)**, scored output-error on both θ and ω. Near centre θ = 1.155·r, so the same ODE can be read two ways:

| reading | in the θ frame of this page | what changes vs the model's default |
|---|---|---|
| FA: J, b were fitted per degree of gp-0x6a00 | J θ̈ + b θ̇ + k θ = T; rate operand reads θ̇/s | κ = 1/s on the D only |
| FB: J, b were fitted per degree of lin (= om) | (J/s) θ̈ + (b/s) θ̇ + k θ = T; rate operand reads θ̇/s | κ = 1/s **and** J, b ÷ s (`|fb`) |

(FB here is algebraically the refuter's FB — G and k × 1.155 in the lin frame — divided through by s.) The page gates
**both**, at κ ∈ {0.83, 1, 1.155} × {FA, FB}, on every member and speed: the brief's ratio range as a gated uncertainty,
containing the physical 0.866–1.04.

### 1.3 The D, sized in the operand's own frame

| implementation | D operand | cal Kd | D per deg/s of the operand's own rate | per deg/s of gp-0x6a00 at ≥ 13 m/s (κ 0.866) | gated κ |
|---|---|---|---|---|---|
| P2 (ref) | gp-0x6abe | 34 | 20.0 S = 3.21 T | **17.3 S = 2.78 T** | (assumed 1) |
| **G-P48(d)** | gp-0x6abe | **48** | 28.3 S = 4.53 T | **24.5 S = 3.92 T** (1.41× P2's true) | 0.83–1.155 |
| G-P44(d) | gp-0x6abe | 44 | 25.9 S = 4.15 T | 22.4 S = 3.60 T | 0.83–1.155 |
| **G-F24(d)** | gp-0x6a56 (held, E5) | **24** | 24.0 S = 3.85 T | 20.8 S = 3.33 T | 0.83–1.155 |
| **G-A22(d)** | box10 of gp-0x6a00 | **22** (k_op 64) | 17.6 S = 2.82 T per deg/s of gp-0x6a00 | the same (frame-exact) | 1 |

(T = S × FADE 254/256 × output-lag DC 0.990 × FWD 5346/32768: EVIDENCE arithmetic on the image cals.)

**Why these Kd and not more** (§0.1 item 3, `g_env.py` rules in both frames): fresh — M20 (Kd 50 fails at every G);
held — Re(T/ω)₂₀ at s = 1.155 (Kd 24 caps G at 2030 ≥ the highway knot; Kd 26 caps it at 1136); box10 — Re(T/ω)₂₀
(Kd 22 caps G at 1953; Kd 24 at 1276). **Why not less:** the strict set at κ 0.83 needs the D — at Kd 34 the envelope
is 867 at 1–3 m/s (J_hi+h10 κ0.83 binds) against 1228 at Kd 48 (`env_fresh_*_coarse.json`).

---

## 2. The PM extractor (finding 1) — what was changed and where it matters

- `g_ext.crossings` returns every |L| = 1 crossing with its phase; `pm_fixed` = min over crossings of `180 − |wrap(φ)|`,
  wrap to [−180°, 180°). `pm_gm_rows_fixed` is ds_gate2's row routine with that one line changed.
- **Where it matters:** only when a crossing leads (φ > 0): the D-loop crossing of a low-G row at Kd > ~40 (envelope
  searches). On the 48 020 points of every gate on this page, and on P2/F2's published tables, the two agree to 1e-9
  (`g_gate_*.txt`: "points where pm_fixed != the shared formula: 0"). **Every published SCORE-FREQ number is unaffected:**
  `g_pmfix_panel.py` re-scores every angle-kind `score_freq` candidate (incl. B2 at Kd 41 and CGF-1 at Kd 48) on the brief's
  gated set and grid — 0 of 80 920 points differ (`g_pmfix_panel_out.txt`). What the bug did corrupt is the **envelope
  search** (`ds_gate2.env_point` scans G upward from 40 and stops at the first failing row), which is how rev2-A rejected
  P3/P4. The orchestrator may want the shared routines fixed; this page did not edit any shared file.
- **Second method:** exact ρ (my periodic model and the refuter's) and the refuter's exact delay margin (§0.1 table).

---

## 3. The implementations, every byte

All share C1/rev2-A's in-place set, decoded and controlled by the D designer and rev2-A (`ds_bytes.py` records, reused):
E1 `0x28F4C` `24 3f aa 95`→`24 3f 00 96` (x := θ) · E2 `0x28FA4` `89 d1`→`c9 d1` (sum) · B2 `0x29A50` `e2 47 00 00`→`e0 df 34 43` ·
A2 `0x29A56` `da 05`→`b2 05` · E4 `0x29D6A` `08 80 ed 80`→`24 87 52 96` (sp := gp-0x69ae) · H `0x29D76` `c2 82 ba 81`→`89 37 8a ae`
(jarl 0xC4C00, r6) · V1 `0x1310D` `30`→`41` (F181 A16A interlock) · and **either** OPH `0x29EE0` `10 40 bb 41`→`1a 40 00 00`
(D on r26: (i), (iii)) **or** E5 `0x29EDE` `c7 00`→`80 39` + `0x29EE0`→`24 47 aa 95` (D on the held rate: (ii)).
Cals: a `0xC63E8` 0 · b `0xC63EA` 8192 · C `0xC62E6` 65535 · DB `0xC62E4` 0 · **Ki `0xC63E6` 56** · ICL `0xC61BA` 4096 · DCL
`0xC61B6` 10240 · Kp record Y `0xE5384` ×5 = 112 · **Kd record Y `0xE5126` ×4 = Kd** (48 / 44 / 24 / 22). Every pre-edit byte is
asserted against V295 by `g_bytes.py`; full diff UNLISTED: none, for every implementation (`g_bytes_out.txt`).

### 3.1 (i) fresh-rate D — G-P48, G-P48d, G-P44, G-P44d, G-P48L

**The cave code is rev2-A P2's 114 bytes byte for byte** (`ds_asm.listing('D2a')`; my assembly of P2's table reproduces
`c2_cave_P2.hex` sha `75e8755743e14d93` exactly — positive control). Only the 42-byte table differs. **Relative to P2 no
instruction byte changes: the four Kd record cells (`0xE5126..`) and the six table rows (data inside the cave block) do.**

| id | table rows (X, G, S) — X in gp-0x6a5e counts (230.4 per m/s) | G at 3.1 / 8 / 10 / 11.75 / 17.5 / 26.9 m/s | T per deg at those speeds |
|---|---|---|---|
| P2 (ref) | (714,1195,1204) (1843,1527,−7988) (2304,628,−925) (2707,537,2785) (4032,1438,1309) (6198,2130,0) | 1195 1527 628 537 1438 2130 | 52 67 28 24 63 93 |
| **G-P48** | (714,1178,1041) (1843,1465,−6868) (2304,692,−2328) (2707,463,1870) (4032,1068,2118) (6198,2188,0) | 1178 1465 692 463 1068 2188 | 52 64 30 20 47 96 |
| **G-P48d** | (714,1178,1052) (1843,1468,−6948) (2304,686,−2155) (2707,474,3230) (4032,1519,1227) (6198,2168,0) | 1178 1468 686 474 1519 2168 | 52 64 30 21 67 95 |
| G-P44 | (714,1090,1230) (1843,1429,−7437) (2304,592,−1423) (2707,452,1580) (3456,741,2039) (6198,2106,0) — knot at 15.0 m/s | 1090 1429 592 452 (741 @15) 2106 | 48 63 26 20 — 92 |
| **G-P44d** | (714,1090,1230) (1843,1429,−7437) (2304,592,−1565) (2707,438,3138) (4032,1453,1197) (6198,2086,0) | 1090 1429 592 438 1453 2086 | 48 63 26 19 64 91 |
| G-P48L | (714,1178,1292) (1843,1534,−9320) (2304,485,−1677) (2707,320,2312) (4032,1068,2118) (6198,2188,0) | 1178 1534 485 320 1068 2188 | 52 67 21 14 47 96 |

Each row set ends with the `0xFFFF` sentinel row (G = the last knot's). Overflow budget (EVIDENCE, `g_bytes.py`): |E·G| ≤
196 603 × 2188 = 4.3·10⁸ < 2³¹; Kd·|op| ≤ 48 × 13 000 = 6.2·10⁵ → >> 3 → DCL 10 240.

### 3.2 (ii) held-rate D — G-F24, G-F24d

**The cave code is C1 rev 2 / rev2-A F2's 96 bytes byte for byte** (`ds_asm.listing('B0')`; reproduces `c2_cave_F2.hex` sha
`482de8587ce23cbc`). D is Honda's multiply on the held gp-0x6a56 through E5. Tables:

| id | rows | G at 3.1 / 8 / 10 / 11.75 / 17.5 / 26.9 |
|---|---|---|
| **G-F24** | (714,1009,892) (1843,1255,−5882) (2304,593,−1789) (2707,417,1539) (4032,915,1953) (6198,1948,0) | 1009 1255 593 417 915 1948 |
| G-F24d | (714,1009,889) (1843,1254,−5837) (2304,597,−1931) (2707,407,2779) (4032,1306,1214) (6198,1948,0) | 1009 1254 597 407 1306 1948 |

### 3.3 (iii) the angle-own D, "box10" — G-A22, G-A22d

**What it is.** The D operand is the held angle's difference across exactly one slot-4 refresh, held for ten ticks:
`op = −(th_h[n] − th_h[n−10]) << 6`. It reads **no rate cell** and is in gp-0x6a00's own frame by construction (κ ≡ 1;
no pol factor). It differs from the D designer's D1c (a 21 Hz IIR low-pass on the one-tick difference, which turned the
100 Hz impulse train into 5–30 Hz texture) by being an exact 10-tap box-car: its frequency response has nulls at 100 Hz and
every multiple, so the refresh carrier is removed exactly, at the cost of 10.5 ms of operand lag.

**Why the box-car needs a countdown.** A refresh that does not change θ_h is invisible to a change detector, so without
one the last difference would be held forever after the wheel stops. The cave keeps `W = (−Δ << 8) + countdown`: a
refresh that changes θ_h loads 10 ticks; each tick without a change counts down; at 0 the difference expires.

```python
# integer-exact (g_lane.GLane.box_op == g_cave.box10_ref == the assembled bytes, H1)
first = (gp-0x6cf8 == 0x7FFFFFFF)                 # Honda's E_prev sentinel, written 0x7FFFFFFF on every skip tick
C, W  = (th, 0) if first else (RAM_A, RAM_B)       # RAM_A = gp-0x6c44 (last seen th_h), RAM_B = gp-0x6c40
if th != C:      W = ((C - th) << 8) + 10           # a refresh moved th_h: hold -Delta for ten ticks
elif W & 0xFF:   W -= 1;  W = 0 if (W & 0xFF) == 0 else W
RAM_A, RAM_B = th, W                                # PID ticks only (the cave is not on the skip path)
op = (W >> 8) << 6                                  # left in r26 for 0x29EE0 mov r26,r8 ; Honda: D = (Kd op) >> 3
```

**Cave: 210 bytes = 168 code (55 instructions) + 42 table** (`g_cave_out.txt`; listing per instruction with its loop term).
H1: 0 / 60 000 (see §6). Every encoding form is one of `ds_asm.CONTROLS` (ld.w/ld.h/st.w disp[gp], mov imm32, cmov z,
andi, add imm5 (control `0x29E8E add 0xa,r8`), shl/sar imm5, sub, mov, be/bne/br).

**Its cost, measured** (§7): the D quantum is one 0.1° count per 10 ms = **10 deg/s**, i.e. a 176 S step held 10 ms per
count (≈ 28 T if it were held; ≈ 8 T peak after the 5.05 Hz output lag). Rates below 10 deg/s — most lane keeping — produce a pulse train. The fresh operand's quantum is
0.21 deg/s.

**Hazard (UNTRACED, BELIEF).** gp-0x6cf8 has a second load/store pair at `0x2AD4A` / `0x2B058` (the D designer's GATE-1
census, `ds_gate1_out.txt`), inside `FUN_0002a93a` (`get_function_by_address`, stock `code.bin`). Ghidra lists no
callers; my raw Format-V jarl scan (controlled: it finds `0x22522 → FUN_00028ea6`) finds none, and no LE32 pointer
literal exists. Whether it runs (a 6-byte `jarl disp32`, a table jump) is not traced. If it does, the first-tick sentinel is
not the lane's alone. D1c relied on the same sentinel. **Not resolved here; a tracer item if (iii) is chosen.**

---

## 4. GATE 2 on the extended set (`g_gate.py`; 48 020 points per implementation)

**Set.** Tier A (45°, GM 6 dB, |T| 5–30 Hz ≤ +3 dB, M20 and L20 ≤ V295's in the same frame): the brief's ten single
corners **and, strict, their +h10**. Tier B (30°, GM 6 dB): the brief's combined members and their +h10, **plus**
b_lo×ms_free, b_q×ms_free, each ×tau6, each +h10, and b_lo×J_hi×tau6 (+h10). **Every gated member at κ 0.83, 1, 1.155 and
under |fb (×0.83 and ×1.155)** for rate-operand D; κ 1 and |fb for box10. Grid 1–35 m/s at 0.25 + knots. Report members
(the c1r2 factorial remainder, J1.3, light_b, +h20) at κ 1 and 0.83. Every point carries the exact ρ; the 12 lowest-GM
points the exact GM.

### 4.1 Results

| | G-P48 | G-P48d | G-F24 | G-F24d | rev2A-P2 (same set) |
|---|---|---|---|---|---|
| fails, strict | **0** | 381 (all b_q×ms_free) | **0** | 356 (all b_q×ms_free) | 1 496 |
| fails, brief literal (+ frame box) | **0** | **0** | **0** | **0** | 197 |
| unstable points (all, incl. report) | 0 (max ρ 0.9939) | 0 (0.9956) | 0 (0.9943) | 0 (0.9955) | 0 (0.9983) |
| min exact GM, gated | **13.9 dB** (b_lo×tau6 fb κ1.155, 8) | 13.9 dB | **6.7 dB** (b_lo×tau6+h10 fb κ1.155, 8) | — | — |
| J_hi / J_hi+h10 | 51.7 / **47.1** | 51.7 / 47.1 | 50.7 / 46.9 | — | 42.3 / 37.7 |
| ms_free / ms_free+h10 | 52.6 / **49.3** | 52.7 / 49.4 | 55.5 / 51.6 | — | 42.6 / 38.4 |
| b_lo×J_hi×tau6+h10 | 36.8 | 36.8 | 35.9 | — | 23.3 |
| b_q×J1.0+h10 | 34.2 (fb κ0.83, 26.9) | 34.7 | 34.8 | — | 27.1 |
| b_lo×ms_free×tau6+h10 | **33.6** (ring 0.77 Hz ζ 0.126) | 33.6 | 33.7 | — | 12.2 |
| b_q×ms_free×tau6+h10 | **34.9** (ring 1.21 Hz ζ 0.105) | **15.2** (1.28 Hz ζ 0.055) | 35.1 | declared | **6.4** |
| b_q×ms_free+h10 | 36.6 | 17.0 (ζ 0.061) | 36.9 | declared | 8.2 |
| max L20 / V295 (same frame) | 0.976 | 0.976 | 0.83 | 0.83 | 0.69 |
| max \|T\| 5–30 Hz, gated | −1.2 dB (b_lo fb κ0.83) | — | −0.8 dB | — | — |
| report: light_b (prior, contradicted by r71b) | 15.3° (3.85 Hz ζ 0.104) | — | — | — | (refuter: 4.9° aged) |
| report: lowest other | b_lo×J1.0×tau6+h10 28.8° | — | b_lo×J_hi2×tau6+h10 31.1° | — | — |

All PMs in degrees, worst over speed and frame; the frame that binds is κ 0.83 on almost every member (the weakest D).
**EVIDENCE (model).** BELIEF: the plant above 8 Hz (never identified), the credibility of the stress products.

### 4.2 The remaining implementations (`g_gate_<id>.txt`)

| | G-P44 | G-P44d | G-P48L (iv) | G-A22 (iii) | G-A22d |
|---|---|---|---|---|---|
| fails, strict | **0** | 386 (all b_q×ms_free) | **0** | **0** | 250 (all b_q×ms_free) |
| fails, brief literal (+ frame box) | 0 | 0 | 0 | 0 | 0 |
| unstable points (all) | 0 (max ρ 0.9944) | 0 (0.9959) | 0 (0.9915) | 0 (0.9946) | 0 (0.9958) |
| min exact GM, gated | — | **14.6 dB** | — | **8.1 dB** (b_lo×tau6+h10 fb, 7.25) | — |
| J_hi / J_hi+h10 | 50.9 / 46.6 | 50.9 / 46.6 | 51.7 / 47.1 | 50.1 / 46.5 | 50.1 / 46.5 |
| ms_free / ms_free+h10 | 52.9 / 49.4 | 52.9 / 49.4 | 54.1 / 50.3 | 56.1 / 52.3 | 56.0 / 52.2 |
| b_lo×J_hi×tau6+h10 | 35.4 | 35.4 | 34.5 | 36.1 | 36.2 |
| b_q×J1.0+h10 | 34.3 | 34.9 | 34.2 | 34.3 | 34.7 |
| b_lo×ms_free×tau6+h10 | 33.3 | 33.3 | **34.2** (ζ 0.189) | 33.7 | 33.7 |
| b_q×ms_free×tau6+h10 | 35.3 | **14.9** (1.27 Hz ζ 0.052) | 35.3 | 35.5 | **16.1** (1.35 Hz ζ 0.053) |
| max L20 / V295 | 0.885 | 0.886 | 0.971 | 0.65 | 0.65 |
| M20 / V295 (same frame) | 0.895 | 0.895 | 0.978 | 0.75 (V295 at κ 0.866) / 0.65 (κ 1) | 0.75 |
| report light_b (prior world) | 14.4° (3.76 Hz ζ 0.095) | 14.8° | 15.3° | **5.9° (3.99 Hz ζ 0.037)** | 6.0° |

The angle-own D has the thinnest light_b margin of any implementation (its 10.5 ms operand lag at the 4 Hz light_b
crossover); light_b is report-only and contradicted by r71b (refuter F7), and its ring is inside R3\*.

### 4.3 Positive control: the round-2 refuter's rows reproduced

`rev2A-P2` on this gate, at the refuter's own frame readings, reproduces its published F1/F4/F6 numbers: b_q×ms_free+h10 at
κ 1 **13.5°** (refuter 13.5°); J_hi+h10 42.2° (refuter 42.2°, F6). On its own engine (`g_xcheck.py` X3) — see §6.

### 4.4 The same implementations as rows of the common scorer's own table (`g_sfrow_out.md`)

`score_freq.score / summarize / write_report`, unchanged: the brief's gated set at κ 1 (no frame variants, no new products),
0.25 m/s grid, ages 1–10 and 11–20 — directly comparable with SCORE-FREQ-2026-10-01.md (D2a there: minPMsingle 46.7,
minPMcomb 32.6, M20 0.67×).

| cand | minPMnom | minPMsingle | minPMcomb | binding | peak 5–30 dB | M20 (× V295) | L20× | ReTw13/16/20 @12.5 | ReTw20 age 10 (× V295) | Tr1.6–3 | turnhold ≥ 8 | GATE2 fails |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G-P48 | 69.2 | 58.1 | 41.2 | b_q×J1.0+h10 @ 26.9 | −3.0 | 3.26 (0.96) | 0.96 | −0.08 / −0.23 / −0.34 | −0.72 (0.80) | 0.83 | 0.99 | 0 |
| G-P48d | 69.2 | 58.1 | 41.8 | b_q×J1.0+h10 @ 27.0 | −3.0 | 3.25 (0.96) | 0.96 | −0.09 / −0.24 / −0.34 | −0.72 (0.80) | 0.83 | 1.00 | 0 |
| G-P44d | 68.7 | 56.9 | 41.9 | b_q×J1.0+h10 @ 27.0 | −3.8 | 2.98 (0.88) | 0.88 | −0.09 / −0.22 / −0.31 | −0.66 (0.74) | 0.85 | 1.00 | 0 |
| G-F24 | 68.6 | 56.3 | 41.8 | b_q×J1.0+h10 @ 27.0 | −2.5 | 2.66 (0.79) | 0.82 | −0.65 / −0.73 / −0.72 | −0.75 (0.84) | 0.77 | 0.99 | 0 |
| G-F24d | 68.6 | 56.3 | 41.8 | b_q×J1.0+h10 @ 27.0 | −2.2 | 2.67 (0.79) | 0.82 | −0.65 / −0.73 / −0.72 | −0.75 (0.84) | 0.77 | 1.00 | 0 |
| G-A22 (†) | 67.3 | 50.1 | 37.4 | b_q×J1.0+h10 @ 26.9 | −4.8 | 1.99 (0.59) | 0.65 | −0.67 / −0.68 / −0.61 | −0.43 (0.48) | 0.81 | 0.99 | 0 |
| G-A22d (†) | 67.3 | 50.1 | 37.7 | b_q×J1.0+h10 @ 26.9 | −4.9 | 1.99 (0.59) | 0.65 | −0.67 / −0.69 / −0.61 | −0.43 (0.48) | 0.81 | 0.99 | 0 |

(†) box10 is not a score_freq Cand kind: its rows use g_ext.metrics_ext (score_freq's extractor + the box10 FRF), and its
M20 is against V295 at κ 1 (0.75× against V295 at the physical κ 0.866, §4.2).

---

## 5. Re(T/ω) 5–25 Hz, at hold ages 0–9 / 1–10 / 11–20 / 21–30, vs V294 / V295

`g_retw.py`: worst over 1–35 m/s at 0.25, T counts per deg/s, > 0 damps; 48 conditions = frame (s 1 / 1.155) × transport
(2 / 6 ms) × rate-former lag (0 / 0.5 / 1 tick on every rate operand, the candidate's and V295's) × hold ages
(0–9 / 1–10 / 11–20 / 21–30). Positive control: P2 at s 1, 2 ms, ages 1–10 reproduces rev2-A's §3.3 (13 Hz 0.79×,
20 Hz 0.41×); ages 0–9 reproduces the refuter's 1.12–1.13×.

### 5.1 The designs' own convention (s 1, 2 ms, no lag)

| Hz | 5 | 7 | 10 | 13 | 15 | 17 | 20 | 25 |
|---|---|---|---|---|---|---|---|---|
| V294, ages 1–10 | +1.33 | +0.67 | +0.05 | −0.25 | −0.36 | −0.42 | −0.44 | −0.41 |
| V295, ages 1–10 | +2.46 | +1.24 | +0.09 | −0.47 | −0.66 | −0.77 | −0.82 | −0.76 |
| P2, ages 1–10 | −0.57 | −0.44 | −0.39 | −0.37 | −0.36 | −0.35 | −0.34 | −0.31 |
| **G-P48, ages 1–10** | **−0.05** | **−0.16** | −0.30 | −0.37 | −0.40 | −0.42 | −0.43 | −0.42 |
| G-P48d, ages 1–10 | −0.03 | −0.14 | −0.29 | −0.37 | −0.40 | −0.42 | −0.43 | −0.42 |
| G-P44, ages 1–10 | −0.14 | −0.20 | −0.30 | −0.36 | −0.38 | −0.39 | −0.40 | −0.39 |
| G-F24, ages 1–10 | −0.53 | −0.70 | −0.86 | −0.91 | −0.90 | −0.87 | −0.80 | −0.65 |
| G-A22, ages 1–10 | −0.94 | −0.95 | −0.96 | −0.92 | −0.87 | −0.80 | −0.69 | −0.49 |
| V295, ages 0–9 | +2.53 | +1.35 | +0.23 | −0.34 | −0.54 | −0.66 | −0.73 | −0.71 |
| P2, ages 0–9 | −0.54 | −0.43 | −0.39 | −0.38 | −0.37 | −0.36 | −0.35 | −0.33 |
| G-P48, ages 0–9 | −0.02 | −0.14 | −0.30 | −0.38 | −0.42 | −0.43 | −0.44 | −0.44 |
| G-A22, ages 0–9 | −0.86 | −0.87 | −0.89 | −0.86 | −0.82 | −0.77 | −0.68 | −0.51 |
| V295, ages 11–20 | +1.69 | +0.08 | −1.17 | −1.50 | −1.44 | −1.26 | −0.89 | −0.25 |
| P2, ages 11–20 | −0.74 | −0.42 | −0.23 | −0.15 | −0.14 | −0.15 | −0.20 | −0.24 |
| G-P48, ages 11–20 | −0.23 | −0.14 | −0.13 | −0.15 | −0.17 | −0.21 | −0.29 | −0.35 |
| G-F24, ages 11–20 | −1.49 | −1.65 | −1.64 | −1.40 | −1.18 | −0.96 | −0.63 | −0.13 |
| V295, ages 21–30 | +0.76 | −1.09 | −1.99 | −1.58 | −1.03 | −0.45 | +0.27 | +0.76 |
| P2, ages 21–30 | −0.70 | −0.18 | +0.13 | +0.05 | −0.03 | −0.10 | −0.17 | −0.25 |
| G-P48, ages 21–30 | −0.19 | +0.12 | +0.23 | +0.05 | −0.08 | −0.17 | −0.27 | −0.36 |
| G-A22, ages 21–30 | −2.28 | −2.01 | −1.36 | −0.70 | −0.29 | +0.07 | +0.42 | +0.45 |

**What the D re-size does to the band** (EVIDENCE, model): raising the fresh D 34 → 48 **removes most of P2's 5–7 Hz
anti-damping** (−0.57 → −0.05 at 5 Hz, −0.44 → −0.16 at 7 Hz: rev2-A's declared M14, the F7 / 7 Hz class) and **adds
0.04–0.11 of anti-damping at 17–25 Hz** (the D through the 5.05 Hz output lag and 2 ms transport is past −90° above about
12 Hz). The held and angle-own D carry the hold's lag and anti-damp 5–15 Hz at 2–3× the fresh D.

### 5.2 The ratio claim (F3c), over all 48 conditions — withdrawn for every structure

`g_retw_summary.txt`: conditions in which the candidate anti-damps MORE than V295 under the same condition, at any of
13–25 Hz: **P2 15/48** (13 Hz at ages 0–9: 1.00–1.31×; 25 Hz aged: up to 2.5×), **G-P48 31/48** (13 Hz ages 0–9 up to
1.33×; 20–25 Hz aged/tau6 where V295 itself turns damping), **G-P44 22/48**, **G-F24 24/48** (13 Hz up to 2.59×),
**G-A22 24/48** (13 Hz up to 2.97×). **No structure satisfies "≤ V295 at 13–25 Hz under every condition" — the
condition-matched ratio is a fragile proxy because V295's own Re(T/ω) changes sign with hold age.**

### 5.3 The statement that does hold: worst case vs worst case

| Hz | 7 | 10 | 13 | 15 | 17 | 20 | 25 |
|---|---|---|---|---|---|---|---|
| V295 worst over 48 conditions | −1.61 | −2.12 | −1.68 | −1.46 | −1.26 | −1.06 | −0.79 |
| V294 worst | −0.87 | −1.14 | −0.91 | −0.79 | −0.68 | −0.57 | −0.43 |
| P2 | −0.90 (0.56×) | −0.81 (0.38×) | −0.78 (0.46×) | −0.75 (0.51×) | −0.71 (0.56×) | −0.66 (0.62×) | −0.56 (0.71×) |
| **G-P48 / G-P48d** | −0.80 (0.49×) | −0.90 (0.43×) | −0.97 (0.58×) | −0.97 (0.67×) | −0.95 (0.75×) | −0.90 (**0.85×**) | −0.79 (**1.00×**) |
| **G-P44 / G-P44d** | −0.79 (0.49×) | −0.86 (0.40×) | −0.90 (0.54×) | −0.90 (0.62×) | −0.88 (0.70×) | −0.83 (0.78×) | −0.73 (0.92×) |
| G-F24 / G-F24d | −2.48 (1.54×) | −1.83 (0.86×) | −1.43 (0.86×) | −1.19 (0.82×) | −1.07 (0.85×) | −0.89 (0.84×) | −0.67 (0.84×) |
| G-A22 / G-A22d | −2.05 (1.27×) | −1.47 (0.69×) | −1.11 (0.66×) | −0.97 (0.66×) | −0.84 (0.67×) | −0.69 (0.65×) | −0.51 (0.64×) |

At 5 Hz V295 damps under every condition (+0.22 worst) and no angle-loop structure does (G-P48 −0.86, P2 −1.19, G-F24 −2.65,
G-A22 −2.46): the 5 Hz anti-damping is a property of an angle loop's P/I through the hold and output lag, smallest for G-P48.
For scale: the identified plant damping b is 5–26 T per deg/s at 1–2 Hz (BELIEF above 8 Hz).

---

## 6. Stress, independent re-derivation, H1

### 6.1 Two-mass stress (`g_stress.py`; 4 200 points per implementation)

Collocated mode at 13 / 15 / 16.5 / 17 / 20 Hz, ζ₂ 0.02 / 0.05, r₂ 0.2 / 0.4, on nominal, b_lo, b_q, nominal+h10 and (rate D)
nominal at κ 1.155 aged and not, 1–35 m/s.

| | unstable | least-damped 5–50 Hz pole | max 5–30 Hz closed-loop peak |
|---|---|---|---|
| P2 (ref) | 0 | 20.02 Hz ζ 0.036 (open 0.02) | −6.1 dB |
| G-P48 / G-P48d | 0 / 0 | 20.05 Hz ζ 0.036 | −3.8 dB |
| G-P44d | 0 | 20.04 Hz ζ 0.036 | −4.5 dB |
| G-F24d | 0 | 20.00 Hz ζ 0.033 | −3.8 dB (nominal+h10 κ1.155) |
| G-A22d | 0 | 19.97 Hz ζ 0.034 | −6.3 dB |

The loop adds damping to every stress mode for every implementation (closed ζ ≥ open ζ); the higher D raises the closed-loop
peak at the 20 Hz mode by 2.3 dB but keeps it under 0 dB. **EVIDENCE (model).**

### 6.2 Exact GM and the fade floor

`g_exactgm_out.txt`: exact GM = LTI GM to 0.1 dB at the 12 lowest-GM points of each implementation (G-P48 / G-P48d
13.9 dB, G-P44d 14.6 dB, G-F24 **6.7 dB** at b_lo×tau6+h10 |fb κ1.155, 8 m/s — the held D's thin corner, G-A22 8.1 dB);
ρ at the fade floor (×0.297, a light hand) < 1 at the 12 lowest-margin points of each (e.g. G-P44d: 0.9923–0.9929 on the
declared b_q×ms_free points).

### 6.3 The refuter's own engine (`g_xcheck.py`)

X1 is §0.1's table. **X2** — every implementation's eight worst gated points (by margin to the bar), re-derived on the
stability refuter's engine `c2r2_model` (its own image read, sensor chain, member builder, exact periodic model): PM agrees
to ≤ 0.1° and exact ρ to 4 decimals on all 88 points (e.g. G-P48d b_q×ms_free×tau6+h10 κ0.83 @ 15.75: 15.2° / ρ 0.9956
both engines; G-P48 b_lo×ms_free×tau6+h10 κ0.83 @ 9: 33.6° vs 33.5°). **X3** — the refuter's own F1 / F4 / F6 rows on its
own engine; positive control first, its published P2/F2 numbers reproduce exactly:

| member (refuter's reading) | bar | P2 (published) | F2 | **G-P48** | **G-P48d** | G-P44d | G-F24 | G-F24d |
|---|---|---|---|---|---|---|---|---|
| J_hi (FA) | 45 | 43.2 (43.2) | 43.4 | **53.0** | 53.0 | 52.2 | 51.9 | 51.9 |
| ms_free (FA) | 45 | 43.8 (43.8) | 43.8 | **53.9** | 54.0 | 54.2 | 56.7 | 56.6 |
| b_lo×J_hi+h10 (FA) | 30 | 28.3 (28.3) | 28.0 | **40.4** | 40.4 | 40.1 | 39.7 | 39.7 |
| b_q×J1.0+h10 (FB) | 30 | 28.5 (28.5) | 27.5 | **35.3** | 35.9 | 36.1 | 35.8 | 35.6 |
| b_lo×J_hi×tau6+h10 (FB) | 30 | 24.6 (24.6) | 24.8 | **38.7** | 38.6 | 36.9 | 37.1 | 37.1 |
| b_q×ms_free+h10 (κ 1) | 30 | 13.5 (13.5) | 14.9 | **44.4** | 24.0 (declared) | 23.5 (declared) | 44.0 | 24.4 (declared) |
| b_q×ms_free (κ 1) | 30 | 17.3 | 19.5 | **45.7** | 27.2 (declared) | 26.7 (declared) | 48.3 | 28.9 (declared) |

(remaining rows in `g_xcheck_out.txt`.) The angle-own D is not expressible in `c2r2_model`; its exact ρ comes from my own
periodic model, which matches `ds_model.Lifted` to 1.7e-14 on the structures both can express.

### 6.4 H1 on the assembled caves

`g_cave_out.txt`: each cave assembled by the D designer's two-pass assembler and executed by its V850E2 interpreter
(`ds_asm.run_bytes`) against the lane's cave arithmetic, 60 000 random inputs (sentinels, validity edges, table knots ±1,
first-tick, random register file, every non-scratch register checked): (i) and (ii) re-use `ds_asm.h1_test`; (iii)
`g_cave.h1_box10`, which also checks the two RAM words and that no other RAM changes. **Result: 0 / 60 000 for each of
G-P48, G-P48d, G-P44, G-P44d, G-F24, G-F24d, G-A22, G-A22d** (cave sha256 prefixes in `g_cave_out.txt`; G-P48d
`0679edaa64ea75af`, G-P44d `ac2268c9f9be19bd`, G-F24 `1b08aa6400e1e980`, G-A22 `f9e6f3f1bf76ef69`). Positive control: the
same assembly path reproduces rev2-A's `c2_cave_P2.hex` and `c2_cave_F2.hex` byte for byte. **BELIEF until a built image is
decoded by Ghidra (rev2-A H5).**

---

## 7. Tracking price and the time domain

### 7.1 The goal's linear tracking metric (`g_track.py`; 18 members incl. |fb, |k0.83, b_q×ms_free, b_lo×ms_free)

| | 8–12.5 m/s min | 13.5 | 15 | 17 | 19 | ≥ 22 | worst (member, v) | \|T_ref\| 1.6–3 Hz max |
|---|---|---|---|---|---|---|---|---|
| P2 | 0.964 | 0.961 | 0.959 | 0.957 | 0.969 | 0.986 | 0.957 (b_q×ms_free, 17) | 2.44 |
| G-P48 | 0.953 | 0.946 | 0.940 | **0.935** | 0.958 | 0.985 | **0.935** | **1.65** |
| **G-P48d** | 0.961 | 0.961 | 0.961 | 0.961 | 0.972 | 0.988 | **0.961** | 1.92 |
| G-P44 | 0.948 | 0.939 | 0.932 | 0.930 | 0.955 | 0.984 | 0.930 | 1.66 |
| **G-P44d** | **0.954** (11.9) | 0.957 | 0.958 | 0.958 | 0.970 | 0.987 | **0.954** (b_lo×ms_free, 11.9) | 1.91 |
| G-P48L (iv) | 0.921 | 0.928 | 0.932 | 0.934 | 0.958 | 0.985 | 0.921 (b_lo×ms_free, 11.9) | 1.65 |
| G-P48k40 | 0.934 | 0.922 | 0.913 | **0.903** | 0.933 | 0.973 | 0.903 | 1.54 |
| G-F24 | 0.941 | 0.932 | 0.925 | **0.918** | 0.947 | 0.981 | 0.918 | 1.54 |
| G-F24d | **0.947** | 0.949 | 0.950 | 0.951 | 0.965 | 0.985 | 0.947 | 1.67 |
| G-A22 | 0.930 | 0.921 | 0.916 | **0.909** | 0.941 | 0.979 | 0.909 | 1.77 |
| G-A22d | **0.937** | 0.941 | 0.943 | 0.945 | 0.960 | 0.983 | 0.937 | 1.82 |

Turn-hold |T_ref(0.02 Hz)| ≥ 0.992 everywhere (linear; blind to the clamp). The hard-turn band: the extra D cuts P2's worst
|T_ref| 1.6–3 Hz from 2.44 to 1.65 (G-P48) — the M9 / hard-turn criterion moves the right way.

### 7.2 With the clamp: the nonlinear refuter's instruments (`g_nl.py`)

**The goal's tracking metric on route r71b's own engaged angle paths** (`nl_realref`, the refuter's lane / plant / friction /
integrator clamp; 0.5 Hz LPF, OLS slope; P2 re-run in the same batch as the positive control — the refuter published 0.900–0.904
at 8–15 and 0.851–0.856 at 15–22: reproduced, 0.900 / 0.856):

| band / member | P2 | G-P48 | **G-P48d** | G-P44 | **G-P44d** | G-F24 | G-F24d |
|---|---|---|---|---|---|---|---|
| 8–15 nominal | 0.900 | 0.897 | 0.897 | 0.891 | 0.891 | 0.889 | 0.889 |
| 8–15 bc / F_hi / b_lo×J_hi | 0.910 / 0.899 / 0.892 | 0.906 / 0.896 / 0.891 | 0.907 / 0.897 / 0.891 | 0.901 / 0.890 / 0.884 | 0.901 / 0.890 / 0.884 | 0.899 / 0.888 / 0.882 | 0.900 / 0.889 / 0.882 |
| **15–22 nominal** | 0.856 | **0.835** | **0.860** | 0.831 | 0.856 | 0.821 | 0.847 |
| 15–22 bc / F_hi / b_lo×J_hi | 0.857 / 0.856 / 0.864 | 0.837 / 0.835 / 0.845 | 0.862 / 0.860 / 0.868 | 0.833 / 0.831 / 0.841 | 0.858 / 0.856 / 0.865 | 0.823 / 0.821 / 0.831 | 0.849 / 0.847 / 0.856 |
| > 22, every member | 1.000–1.002 | 1.000–1.002 | 1.000–1.002 | 1.000–1.002 | 1.000–1.002 | 1.000–1.002 | 1.000–1.002 |

**Reading (EVIDENCE: simulation, the refuter's instrument):** every implementation misses 0.95 at 8–22 m/s on the real
paths **for the reason round-2 F1 gave — the integrator clamp ICL 4096** (the friction-free twins read the same to 0.001).
That is the integral designers' axis. What this axis adds to it: **G-P48d is +0.004 over P2 at 15–22 m/s and −0.003 at
8–15 m/s; closing b_q × ms_free by G (G-P48) costs −0.021 at 15–22 m/s**, on top of F1's −0.15. The D re-size itself is
neutral on the real paths; the table is what moves it.

**Turn-hold at a curve sized by lateral acceleration** (the refuter's experiment, `g_nl_turnhold.txt`; hold ratio over the
last 2 s of an 8 s hold; positive control P2 at 17 m/s, 2.0 m/s² = 0.73, the refuter's 0.73):

| a_lat, nominal | P2 | G-P48 | **G-P48d** | **G-P44d** | G-F24d |
|---|---|---|---|---|---|
| 1.0 m/s², worst ≥ 8 m/s | 0.98 | 0.97 | 0.98 | 0.98 | 0.98 |
| 1.5 m/s², 15 / 17 / 19 m/s | 0.86 / 0.81 / 0.93 | 0.84 / 0.78 / 0.93 | 0.86 / 0.81 / 0.94 | 0.85 / 0.81 / 0.93 | 0.85 / 0.80 / 0.93 |
| 2.0 m/s², 15 / 17 / 19 m/s | 0.78 / 0.73 / 0.84 | 0.75 / 0.69 / 0.82 | 0.79 / 0.74 / 0.84 | 0.78 / 0.74 / 0.84 | 0.77 / 0.72 / 0.83 |

The integrator sits at its clamp ('*' in the file) in every sub-0.90 cell, for every implementation and for the friction-free
twin: **F1 is the integral policy's, not this axis's.** This axis's tables move it by +0.01 (the "d" variants) to −0.04
(G-P48).

### 7.2c Small corrections at the dip — **a cost of this axis, measured** (`g_nl_small.txt`, the refuter's F2/F4 experiment)

±0.3° at 0.1 Hz, ±0.5° at 0.2 Hz, ±1° at 0.3 Hz; dwell-then-jump events summed over the band's speeds (largest jump), and the
in-phase wire gain (min over the band). The friction-free twins show 0 events everywhere (the linear control).

| scenario, member, band 10.25–12.5 m/s | P2 | G-P48 | **G-P48d** | **G-P44d** | G-F24d |
|---|---|---|---|---|---|
| ±0.3° 0.1 Hz, nominal: events / gain | 13 / 1.03 | 15 / 0.85 | 15 / 0.85 | 15 / 0.81 | 18 / 0.72 |
| ±0.5° 0.2 Hz, bc: events (max jump) / gain | 18 (0.68°) / **0.60** | 16 (0.66°) / −0.07 | 16 (0.65°) / **−0.07** | 17 (0.62°) / −0.16 | 18 (0.61°) / −0.29 |
| ±1° 0.3 Hz, bc: events (max jump) / gain | **1 (1.26°)** / 0.42 | 14 (1.22°) / 0.05 | **9 (1.22°)** / 0.08 | 18 (1.11°) / −0.04 | 18 (1.13°) / −0.12 |
| ±1° 0.3 Hz, nominal friction-free: gain | 0.86 | 0.75 | 0.75 | 0.68 | 0.65 |
| 12.75–15 m/s, ±0.5° bc: events / gain | 6 / 0.72 | 12 / 0.40 | **5 / 0.67** | 9 / 0.50 | 11 / 0.44 |

**Reading (EVIDENCE: simulation; BELIEF: transfer to the car, V282 not simulable).** At the 10–12.5 m/s dip every
implementation of this axis **tracks small corrections worse than P2**: the strict set at κ 0.83 (ms_free+h10 at 45°,
b_lo×ms_free products at 30°) puts the dip at G 438–474 against P2's 537, and the larger D adds viscous resistance that the
dip's low P (19–21 T per degree) must overcome after a stick. Outside the dip the "d" variants are at P2's level (12.75–15 m/s:
G-P48d 5 events vs P2 6). **This is the price of closing F2/F3 at the dip; it lands on round-2 F4 (the integral/dip axis).**
A variant that declares BOTH ms_free products (G-P48dd, table only, not gated: dip G 567–587, linear metric 0.961) recovers
P2's dip stiffness; it is listed in §11, not offered, because b_lo × ms_free is the bias-corrected damping, the more
credible of the two products.

### 7.3 The common time scorer (`g_time.py` → `score_time_out.md`)

rev2-A's `score_time.py` (18 scenarios × 12 speeds incl. the plant knots × 5 members: nominal, bc, F_hi, b_lo×J_hi,
nominal+h10), every column in ONE batch per (scenario, speed, member), rev2-A's P2 and F2 as same-batch references.

**Pre-registered bars (hold ≥ 0.90 at ≥ 8 m/s; T 5–30 Hz in holds ≤ 2.0 counts and 0 detector reversals; sentinel push
≤ 0.1°; tmo |T| < 50 by sentinel + 0.25 s; 0 int32 wraps): every column PASSES** — G-P48, G-P48d, G-P44, G-P48L, G-F24,
G-F24d, G-A22, G-A22d, G-P48k40, G-P48k32 and both references. **EVIDENCE (simulation).**

What moves (worst over speeds; P2 in the same batch; full tables in `score_time_out.md`):

| member | quantity | P2 | **G-P48d** | G-P48 | G-F24 | G-A22 |
|---|---|---|---|---|---|---|
| b_lo×J_hi | firm-hand release lurch | 10.21° | **5.92°** | 5.93° | 6.30° | 8.59° |
| b_lo×J_hi | light-hand (400) lurch | 10.54° | **9.50°** | 9.64° | 10.47° | 11.87° |
| b_lo×J_hi | step overshoot | 33.6 % | **23.0 %** | 22.9 % | 23.4 % | 28.9 % |
| b_lo×J_hi | engage droop | 6.85° | **6.50°** | 6.50° | 7.14° | 7.83° |
| b_lo×J_hi | hard-turn 1.6–3 Hz wheel rate / command's own | 1.40 | **1.07** | 1.06 | 0.99 | 1.06 |
| nominal | hard-turn ratio | 0.92 | 0.77 | 0.77 | 0.72 | 0.76 |
| bc | firm-hand release lurch | 5.84° | 4.04° | 4.05° | 4.57° | 5.37° |
| nominal | s02 (±, 0.2 Hz) wire gain min ≥ 8 m/s | 0.85 | **0.87** | 0.73 | 0.67 | 0.64 |
| nominal | s05 (0.5 Hz) gain min ≥ 8 m/s | 0.22 | 0.05 | 0.02 | −0.01 | −0.01 |
| bc / F_hi | dwell-then-jump events 8–12.5 m/s | 2 / 0 | 4 / 4 | 6 / 4 | 8 / — | 8 / 8 |
| F_hi | timeout (510 ms) hold deviation | 1.01° | 2.16° | 2.15° | — | 2.92° |
| nominal | T 5–30 Hz in holds (bar 2.0) | 0.68 | 0.64 | 0.65 | 0.63 | **1.48** |
| nominal | T 40–200 Hz | 0.76 | 0.73 | 0.73 | 0.66 | 0.88 |
| all | Honda's oscillation detector | ≤ 0.23 of threshold, 0 reversals | same | same | same | same |

**Dense pass** (3–30 m/s every 0.5 m/s, s02 + rh, nominal and bc — reduced from score_time's 0.25 m/s / s02+rh+ssm for
compute): turn-hold ≥ 0.976 for every column; s02 wire-gain minimum (at 16.5–17 m/s) **P2 0.852 / G-P48d 0.869 / G-P44d
— / G-P48 0.731 / G-F24 0.666 / G-A22 0.636**; dwell-then-jump in s02: 0 for every column; **highway hold slips (≥ 0.1°
creep after a stick, 13.25–30 m/s, nominal) P2 25 / G-P48d 52 / G-P48 40 / G-P44 35 / G-F24d 47 / G-A22 23** (bc: 0–1 for
all) — the rev2-A M11 class, roughly doubled by the "d" tables' higher highway gain with the re-sized D.

**G-P44d** (fitted after the main suite's column snapshot) ran the identical suite afterwards with P2 again in the same
batch (`score_time_late_out.md`; P2's numbers reproduce the main batch exactly): **every pre-registered bar PASSES**
(hold ≥ 0.987, T 5–30 Hz 0.84, 0 reversals, sentinel 0.00°, tmo 0, 0 wraps); b_lo×J_hi firm-hand lurch 6.32° (P2 10.21°),
light 10.05° (10.55°), step overshoot 24.1 % (33.6 %), hard-turn ratio 1.09 (1.40); nominal s05 gain min 0.01 (P2 0.21);
F_hi timeout-hold deviation 2.45° (1.01°).

**Reading.** The re-sized D is what moves the override and hard-turn rows — it **halves P2's firm-hand release lurch on
b_lo × J_hi (rev2-A's declared M6 class)**, cuts the step overshoot by a third and pulls the hard-turn 1.6–3 Hz ratio from
1.40 to 1.07 (rev2-A's M9). The table is what moves the dip rows: small-signal gain at 0.5 Hz, dwell-then-jump at 8–12.5 m/s
and the F_hi timeout hold are worse than P2's, as §7.2c found with the refuter's instrument. The angle-own D carries 2.3×
the 5–30 Hz torque texture of the fresh D (its 10 deg/s quantum), under the 2.0 bar.

---

## 8. Declared misses and stop bands (written before any build)

Stop bands are rev2-A's, which these implementations inherit unchanged: **R3\*** (any speed: a 0.5–5.5 Hz oscillation in
0x14A or the 0x18F rate that grows, or ≥ 4 visible cycles above 2× the pre-event rms, i.e. ζ < 0.10 → REVERT), **R4** (a
narrowband 5–30 Hz line absent on V282/V295 → REVERT), R5 (ring > 0.5 %, F7 > 0).

| # | implementation | criterion | quantified prediction | stop band that catches it |
|---|---|---|---|---|
| G-M1 | **the "d" variants** | GATE 2 on b_q×ms_free (two stress corners) | PM 15.2–27.1° at 12.75–22.75 m/s (κ 0.83 → 1); ring **1.27–1.30 Hz, ζ 0.055–0.078** (G-P48d) | **R3\*** (ζ < 0.10 → ≥ 4 visible cycles) |
| G-M2 | **G-P48, G-F24, G-A22** (b_q×ms_free gated) | the goal's tracking metric at 13.5–19 m/s | linear 0.935–0.958 (b_q×ms_free), nominal 0.951 at 17 m/s; on the real paths see §7.2 | on-car tracking < 0.95 in the 15–22 band = FAILED (§8.2 of rev2-A) |
| G-M3 | fresh-D (i) | 20 Hz gain margin | M20 0.976× (Kd 48) / 0.90× (Kd 44); 20–25 Hz anti-damping 0.85–1.00× / 0.78–0.92× of V295's worst case | **R4** |
| G-M4 | all | 5 Hz damping | −0.86 (G-P48) … −2.65 (G-F24) T per deg/s where V295 damps | R4 (5–8 Hz), F7 > 0 |
| G-M5 | held (ii) | 13–15 Hz anti-damping (F2's M13) | 1.5–2.6× V295 condition-matched; 0.82–0.86× worst-vs-worst | R4 with a 10–17 Hz watch |
| G-M6 | box10 (iii) | 5–30 Hz texture | T 5–30 Hz in holds 1.39–1.51 counts (bar 2.0; the fresh D 0.64), the 10 deg/s operand quantum | R4 / the "line" bar |
| G-M7 | every implementation | small corrections at the 10–12.5 m/s dip (round-2 F4) | worse than P2: ±0.5° bc in-phase gain −0.07…−0.29 vs 0.60; ±1° bc 9–18 dwell-then-jump events vs 1; F_hi timeout-hold deviation 2.16° vs 1.01° (§7.2c, §7.3) | rev2-A M2/M4 (operator's words; dwell rate vs r6c) |
| G-M8 | the "d" fresh variants | highway hold creep (rev2-A M11) | 52 hold slips over the dense nominal grid vs P2's 25 (bc: 0) | rev2-A M11 (not a revert; operator's words) |
| inherited | all | rev2-A M1–M12, M15 (low-speed stick-slip, light-hand lurch, timeout hold, stock camera) and round-2 F1/F4 (integrator clamp, dwell-then-jump at the dip) | not this axis; §7.2 quantifies how my tables move F1 | rev2-A §6 / §7.2 |

### 8.1 What a FAIL looks like for these implementations (any one means **do not flash**; written before any build)

| id | failure |
|---|---|
| G-H1 | The built image's cave bytes, executed by `ds_asm.run_bytes`, differ from the lane arithmetic on any of 60 000 inputs (design time: 0 / 60 000 for every implementation, `g_cave_out.txt`), or (iii) writes any RAM other than gp-0x6c44 / gp-0x6c40. |
| G-H2 | `g_gate.py` on the BUILT image's table and Kd cells: any strict-set fail outside the declared set (the "d" variants: b_q×ms_free only), any unstable point, M20 or L20 above V295's in the same frame. |
| G-H3 | The four Kd record cells `0xE5126..0xE512D` are not all equal to the implementation's Kd (a non-flat Kd LERP would make the D depend on the demand index the angle loop bypasses). |
| G-H4 | `g_xcheck.py` X2 on the built table: any binding point where `c2r2_model` and `g_gate` disagree by more than 0.5° or on stability. |
| G-H5 | `g_time.py` on the built table: any of score_time's pre-registered bars failing outside the declared misses. |
| G-H6 | (iii) only: the gp-0x6cf8 accessor at `0x2AD4A`/`0x2B058` (`FUN_0002a93a`) is reachable while the lane runs (H-sentinel) — not traced here. |
| inherited | rev2-A §8.1 H1–H10 (hook decode, A2/B2, integrity regions, F181, pol) apply unchanged to (i)/(ii), whose code is P2's / F2's byte for byte. |

### 8.2 One short drive: LIVE / INVERTED for the D re-size, and the frame (no new telemetry bit)

rev2-A §7's regression `tap = c_P·(raw − 10θ) + c_I·Σ(raw − 10θ)·dt + c_D·ω_18F + c0` on hands-off windows, run twice:

| verdict | condition |
|---|---|
| **LIVE: the re-sized D** | c_D ∈ [0.45, 0.70] tap per deg/s of ω_18F for G-P48(d) (predicted 0.57), [0.41, 0.64] for G-P44(d) (0.52), [0.38, 0.58] for G-F24(d) (0.48), flat in speed. P2 predicted 0.40 — **the Kd 34 → 48 step is resolvable in one drive** (windows overlap only in 0.45–0.50). |
| **LIVE: the frame** | one regressor cannot tell the frames apart (ω_18F and dθ_14A/dt differ by the slope s, so any coefficient just rescales). The discriminator is the slope's **angle dependence**: run the regression in two windows, \|θ\| < 25° (s 1.155) and \|θ\| > 85° (s 0.962; 18–24 % of frames below 8 m/s on r71b). A lin-frame D ((i), (ii)) gives the **same c_D on ω_18F** in both windows (and c_D on dθ_14A/dt changes by 1.155/0.962 = 1.20); the angle-own D (iii) gives the same c_D on dθ_14A/dt in both. This measures F2 on this car's own data, in the drive. |
| **INVERTED → abort (R1)** | c_D aiding (same sign as ω). For (i) this is the pol check (H-pol); (ii)/(iii) cannot invert it. |
| declared b_q × ms_free world (the "d" variants) | a 1.2–1.4 Hz ring at 13–22 m/s with ζ 0.05–0.08 (≥ 4 visible cycles) → **R3\* REVERT**: the drive identifies that the plant is in the declared corner. |

---

## 9. Hazards specific to this axis

- **H-pol (i).** The fresh D's sign rests on pol = gp-0x6752 = −1 (record EVIDENCE). Inherited from P2; R1 INVERTED catches
  it on the first drive (c_D aiding). **(ii) and (iii) remove it:** the held x carries pol exactly as θ does; the angle-own
  D is θ itself.
- **H-frame.** The design does not depend on which frame the identified plant lives in: both readings are gated (§1.2).
  It does depend on the correction table being the one in the image (bytes read) and the wire ratio holding on other roads
  (BELIEF: one route).
- **H-sentinel (iii only).** §3.3: gp-0x6cf8's second accessor `FUN_0002a93a` — UNTRACED.
- **H-RAM (iii only).** gp-0x6c44 / gp-0x6c40: 0 accesses of any form in V295 (the D designer's controlled GATE-1 census,
  `ds_gate1_out.txt`: 4-byte and 6-byte gp forms, bit ops, LE32 literal, address-taken); both flown (V289, V292 era cave RAM;
  record). Not re-scanned on a built image (the builder's H4).
- **Instrument (no new bit).** The D's size is observable on the wire as rev2-A §7's c_D (the regression coefficient on
  the 0x18F rate, which IS the lin-frame operand): **G-P48(d) c_D = 4.53 / 8 = 0.57 tap per deg/s (window 0.45–0.70)**
  against P2's 0.40 (0.30–0.50); G-P44(d) 0.52; G-F24(d) 0.48; G-A22(d) 0.35 per deg/s of the 0x14A angle rate. **The frame
  itself is observable on the same drive** by the angle dependence of the D coefficient (§8.2): constant on ω_18F across
  |θ| < 25° and |θ| > 85° for (i)/(ii), constant on dθ_14A/dt for (iii).

---

## 10. What was changed in the common scorers, and nothing else

- **`panel/score_freq.py`: not edited.** `g_ext.py` imports it and adds, beside it: `pm_fixed` (one line); the extended
  members (ms_free products, +h20, +h0, the |k and |fb frames); the box10 FRF; the kd-linear split. Control C2:
  `metrics_ext` == `score_freq.score` to 1.4e-15 on 12 members × 6 speeds × 10 keys for P2 and F2 (`g_selftest_out.txt`).
  `g_sfrow.py` scores every rate-D implementation through `score_freq.score/summarize/write_report` unchanged.
- **`c2/rev2A/score_time.py`: not edited.** `g_time.py` rebinds `ds_lane.DSLane` (in its own process) to `g_lane.GLane`, a
  subclass that adds only the box10 operand through DSLane's own 'fine' path. CONTROL A: GLane == DSLane through
  `score_time.run`, max |ΔT| 0 on 8 columns × 3 scenarios; CONTROL B: GLane's box10 operand == `g_cave.box10_ref` over
  4 000 ticks with a skip, 0 mismatches (`g_time_selftest.txt`). The column set is frozen per suite (a snapshot), so a
  later fit cannot change a running suite's columns. Tables by rev2-A's own `r2a_time_report.main`, paths pointed here.
- **The nonlinear refuter's `nl_sim` / `nl_realref`: not edited.** `g_nl.py` adds entries to `nl_sim`'s IMPL / ROWS / GLUT
  registries and points `nl_realref.OUT` at my scratch.

---

## 11. Not adopted, so nobody re-proposes them blind

| alternative | result | why not |
|---|---|---|
| fresh D Kd 50–52 | M20 > V295 at every G | the goal's 20 Hz criterion |
| held D Kd 26 | Re(T/ω)₂₀ rule caps G at 1136 at every speed | highway stiffness |
| box10 Kd 24 | Re(T/ω)₂₀ caps G at 1276 | highway stiffness |
| Ki 56 → 40 / 32 at Kd 48 (G-P48k40/k32) | envelope +8–30 %, but the linear goal metric 0.903 / 0.873 | the I carries the metric's 0.05–0.3 Hz content; a slower I costs more than the G it buys |
| a deeper 10–13 m/s dip (iv, G-P48L) | ms_free margins up; metric 0.921 at 11.9 m/s | the dip is already the binding tracking band after F1; lowering it further is the wrong direction |
| D1c-style IIR on the one-tick angle difference | the D designer's D1c: texture 5.4 counts | box10 replaces it with an exact box-car (100 Hz nulls); the 10 deg/s quantum is the same |
| G-P48dd: Kd 48 with BOTH ms_free products declared | table (714,1178,…) dip G 567 / 564 / 587 at 10 / 11 / 11.9 m/s (P2 627 / 576 / 560); linear metric 0.961 | not gated; it buys back P2's dip stiffness (§7.2c) by declaring b_lo × ms_free, the bias-corrected product — a ruling, not a design result |
| a speed-scheduled Kd (less D at the dip) | not built | the Kd record is indexed by the demand index the angle loop bypasses; scheduling D by speed needs a second cave table (≈ +20 B). It would trade the dip's ms_free margin for small-signal tracking, the same trade as G-P48dd. |

---

## 12. What this page did not do (so nobody reads it as done)

- **No image was built**, so nothing here is decoded from a built image (rev2-A H5). The cave listings and H1 are on the
  assembled bytes in memory; the in-place edits are P2's / F2's records, re-asserted against V295 byte by byte.
- **The time domain cannot carry κ.** score_time's sensors model every rate operand at κ 1; the frame box is gated in the
  frequency domain only (where it binds) and in the refuter's engine.
- **The dense time pass was reduced** (0.5 m/s, s02 + rh) for compute; score_time's own dense is 0.25 m/s with ssm.
- **G-P44d's time-domain run** was a separate batch (the same suite, P2 re-run beside it as the control): §7.3,
  `score_time_late_out.md`.
- **box10's first-tick sentinel second accessor** (`FUN_0002a93a`) is untraced; a 6-byte `jarl disp32` caller scan was not
  run.
- **G-P48dd** (both ms_free products declared) is a fitted table only — not gated, not time-scored.
- **The integral policy (ICL, Ki) is held at P2's** (4096, 56). Round-2 F1 dominates real-path tracking at 15–22 m/s; any
  change the integral designers make to Ki or ICL moves the margins on this page (Ki 56 → 40 adds 5–11° on the round-2
  binding members at P2's table, `g_explore1_out.txt`, and costs the tracking metric, §7.1) — the gates here must be re-run
  on the merged design.
