# JUDGE: OPERABILITY AND FAIL-SAFE — angle-loop design panel, round 2 (2026-10-01)

**Status: ANALYSIS ONLY.** Nothing was built, flashed or sent; the fork was not touched; nothing was committed. Ghidra was
not opened (no decision on this lens needed a new decode; every byte claim I use is either a tracer's EVIDENCE, the
scorers' H1 interpreter result, or my own Python byte read of the V295 image, sha `5c044d65…`). The common scorers'
caches were not rewritten: my runs import `panel2/score_time.py` by path and write only to
`_scratch/angle_loop/judge-operability/` and `panel2/judge-operability/`.

**Author:** the OPERABILITY judge, a subagent of the orchestrator `main`. **My lens:** behaviour on the 0xE4 timeout and
fault sentinel, `gp-0x67fe ≠ 2`, mode ≠ 3, a wrong-payload source, light and firm driver override, engage and co-steer;
the authority character per speed band; fork prerequisites (fewer is better); and whether one short drive reads the edit
live and sizes the next step. **The common scorers outrank a designer's page**; where I contradict either, I re-ran it
(§1, §2). Every decision-bearing claim is marked **EVIDENCE** (with method) or **BELIEF**. Code is cited by address or
grep string, documents by heading.

---

## 0. Verdict in one table

Scores out of 100 = **Goal 20** (the goal's decidable time criteria on the common time scorer) · **Fail-safe 20** ·
**Override / engage / co-steer 20** · **Authority character per band 15** (incl. the frequency scorer's R2-box ring risk
and straight-line disturbance rejection) · **Fork prerequisites 10** · **One-drive readability 15**. Subscores in §8.

| # | id | score | one-line reason |
|---|---|---|---|
| 1 | **E2-A3** | **76** | The only submitted family that passes every decidable goal criterion in every band ≥ 8 m/s **with r71b's own torque word replayed** (0.985 / 0.991 / 1.005) and keeps both release lurches under 8° (light 5.8°, firm 4.7°); A3's low-speed cap returns < 8 m/s to P2's level. No RAM write, no new fork bit. Costs: P2's refuted small-signal loop (R2 box 690 fails), a straight-line hold bounded to ~200 T (crown/crosswind drift, §2.2), and an un-bounded cross-centre override (§2.1). |
| 2 | E2-A3-12k | 75 | A3 at ICL 12288: turn-hold margin to 0.99 past r71b's curves for 0 bytes; the bound binds first, so no lurch cost. More I authority on a wrong-payload setpoint (phantom 30° step: 34° vs 32° at 1 s, §2.3). |
| 3 | E2-A2 | 74 | A3 without the low-speed cap: light lurch < 8 m/s regresses to 15.5° (P2 11.9°). |
| 4 | E2-A2-X | 71 | A2 + the fork sends `gp-0x6803 == 2`: engage droop −33 % (6.3° → 4.3°), but the `0xCBAE4` fade arm makes the lane push **×1.8 harder against a firm hand** (my sim and my byte read, §1 V5) and adds a fork bit. Fixable by a cal copy (graft G2). |
| 5 | E1-freeze | 68 | Common scorer contradicts its designer's "dominated": light lurch 4.5° at 10–12.5 m/s (11.8° only at 8–10), firm 4.1°, co-steer droop **halved** (1.3°), replay tracking 0.982 / 0.984. Writes `gp-0x6dd0` on firm ticks; cross-centre light 22°. |
| 5 | E2-S | 68 | Sign-aware freeze (300 words): light 11.1° only at 8–10 m/s, co-steer 1.3°, replay 0.980 / 0.984; firm 8.2°, cross-centre 21.8°. No RAM write. |
| 7 | E1-cal | 64 | Fixes F1 at 0 code bytes and no new RAM claim — but light-hand release lurch **24.3°** (b_lo×J_hi, 10.25 m/s), 3× the 8° bar, under-declared by its designer (17°). |
| 7 | E1-reset | 64 | E1-cal + firm reset: firm lurch 4.2°, light still 24.3°; first cave RAM write. |
| 7 | E2-R1 | 64 | Reference column (= E1-cal); not offered by E2. |
| 10 | G-P48 | 62 | 0 R2-box fails, firm lurch 6.2°, hard-turn 1.17 — **but keeps ICL 4096, so F1 stands**: turn-hold 0.69 and tracking 0.835 at 15–22 m/s. |
| 10 | G-P48d | 62 | As G-P48 with a declared b_q×ms_free ring (1.28 Hz, ζ 0.06, R3\*) and better small-signal at 12.5–22; F1 stands (0.860). |
| 12 | G-P44 / G-P44d | 61 | As G-P48(d) with a 10 % 20 Hz margin; F1 stands. |
| 14 | G-P48k40 | 59 | Ki 40: lowest lurch of the ICL-4096 set but the worst F1 tracking pattern. |
| 15 | G-F24 / G-F24d | 58 | Pol-free held D; F1 stands; 13 Hz anti-damping ~2× V295; in-phase gain 0.56 at the dip. |
| 17 | P2 / D2a / F2 / B0r | 56 | Round-1 references: fail-safe identical to the panel's (A2/B2, A16A, guarded or held D) but fail F1 in every band 8–22 m/s and fail the R2 box (690–706 fails). |
| 17 | G-P48L | 56 | Deeper dip: in-phase gain 0.11 at 10–12.5 m/s, timeout excursion 2.9°. |
| 22 | G-A22 / G-A22d | 52 / 51 | Angle-own D: 2 RAM words + an untraced first-tick sentinel accessor; texture 2.3×; F1 stands. |
| 24 | E1-sched | 51 | Fails the tracking metric in every band (0.885–0.941). |
| — | E1-bleed | 55 | **DISQUALIFIED** (§9): hands-off tracking collapses on the real torque word (0.74–0.83). |
| — | E2-L | 52 | **DISQUALIFIED** (§9): fails the replayed-word tracking (0.938). |
| — | H-B | 47 | **DISQUALIFIED AS WRITTEN** (§9): no V1 fwVersion, undeclared replay-tracking fail, 20.8° lurch it claimed < 4°, no listing. |
| — | E1-splitP | 46 | **DISQUALIFIED** (§9): ρ = 1.0000 on b_q×ms_free, 5052 R2-box fails incl. nominal. |
| — | H-A | 40 | **DISQUALIFIED AS WRITTEN** (§9): as H-B, plus a fork SR/VGR fold the wire may not support and an engage-frame mismatch. |
| — | E2-K0 | 32 | **DISQUALIFIED** (§9): fork-code integral, light-hand lurch 36–52° unbounded by any firmware structure. |

**Not a submitted candidate, scored here as the graft the two scorers point to (G1, §10):** G's table + Kd 48 carrying
E2-A3's bound at ICL 8192. On the common time scorer (my run, reduced speed grid, references reproduce): **M-P48d-A3**
tracking 0.981 / 0.991 / 1.001 (replayed word), turn-hold ≥ 0.98, light lurch **4.1°**, firm **3.2°**, < 8 m/s light 7.7°
(P2 11.9°), hard-turn 1.08 (P2 1.53) — **≈ 81 on this rubric**; **M-P48-A3** ≈ 81 (0 R2-box fails, weaker small-signal at
12.5–22 m/s). Frequency verdict = G-P48(d)'s by construction (BELIEF until scored on a built table); bytes BELIEF
(unassembled).

---

## 1. What I verified myself (the crux of every decision-bearing claim on this page)

| # | claim | method | result |
|---|---|---|---|
| V1 | My harness IS the common time scorer for the scenarios it shares | `op_probe.py` / `op_merge.py` import `panel2/score_time.py` by path; positive controls re-run the scorer's own `ov_lt400` / `ov_fm2400` / `rr` / `rrq` / `th` | **EVIDENCE.** Reproduced at the matching speeds: P2 light 10.9° / firm 7.9° (scorer 10.9 / 7.9); E1-reset 24.3 / 4.2 (24.3 / 4.2); E2-A2 5.8 / 4.7 (5.8 / 4.7); H-A 22.2 / 2.8 (22.2 / 2.8); tracking P2 0.892 / 0.856, E2-A3 0.986 / 0.993 and replayed 0.985 / 0.991, G-P48d 0.892 / 0.860, G-P48 0.892 / 0.835 (all = the scorer). Not an independent engine — a reproduction plus new scenarios. |
| V2 | The ARB does not bound the I when the hand holds the wheel **past centre** | new scenario `xc_*`: the scorer's stiff hand takes the wheel Ah → −Ah, holds 1 s (and 3 s), releases | **EVIDENCE (sim):** E2-A2/A3 light lurch 12.2° (8–12.5 m/s) and **8.9° at 12.5–22 m/s, worse than P2's 8.0°**; I at release 4452 S (~713 T). Table §2.1. |
| V3 | The ARB caps straight-line disturbance rejection | new scenario `crown_d`: θ_sp = 0, a constant road torque d from 1 s, 16 s, steady error over the last 4 s | **EVIDENCE (sim):** E2-A2/A3 drift 1.1° (300 T) / 2.9° (450 T) at 8–12.5 m/s and 0.47° / 1.05° at 12.5–22; every non-ARB candidate ≤ 0.15°. Table §2.2. BELIEF: the real crown/crosswind load in T counts (E2 shows every r71b steady hold ≥ 43 T under the bound). |
| V4 | A signed bound would fix V2 but worsen V3 | `op_signed_arb.py`: one-line monkeypatch, bound = (max(0, sgn(E′)·θ) << sh) + B on 's' columns | **EVIDENCE (sim):** cross-centre 8.9° → **1.7°** at 12.5–22 m/s, but crown drift 1.14° → **2.37°** (300 T) and 2.85° → **5.54°** (450 T). The bound cannot tell a road load from a hand. **Rejected as a graft.** |
| V5 | `gp-0x6803 == 2` makes the lane push harder against a firm hand | (a) my LE read of V295 records `0xCBBC4[7] → 0xE564C` and `0xCBAE4[7] → 0xE54FC` + the integer LERP; (b) sim: mean lane \|T\| during a 1 s firm hold | **EVIDENCE.** (a) fade at 2048 raw: 77 vs **164** (×2.13); at 2400 raw: 77 vs **137** (×1.78); identical ≤ 1024 raw. (b) at 2400 words: P2/E2-A3 385 / 105 / 138 / 62 T vs E2-A2-X **690 / 189 / 248 / 107 T** at 8 / 11.9 / 17 / 26.9 m/s (×1.79–1.81). |
| V6 | A wrong-payload setpoint (the stock camera's 0xE4 on a relay close) is driven by every candidate | new scenario `cam30`: θ_sp steps 0 → 30° with request held 1 (the camera sends request 1 with torque up to \|702\| while its LKAS runs — SPEC-angle-setpoint-interface §0 finding 3, bus-2 census) | **EVIDENCE (sim):** every candidate puts the wheel at 20–32° within 0.5 s and 22–35° within 1 s at 12.5–27 m/s; raised-ICL candidates go further (E1-cal 35.1° vs P2 27.9° at 12.5 m/s, 1 s). **No submitted candidate is fail-safe here in firmware.** |
| V7 | H omits the V1 fwVersion edit | grep of H's byte tables (§2.1, §3.1 of H's page) and its fork prerequisite 4 ("Accept the `39990-TVA,A160` fwVersion") vs rev2-A/rev2-B/G (`V1 0x1310D 30 → 41`, F181 `…,A16A`) | **EVIDENCE.** H-A and H-B ship with the same F181 string as V295/V294, so the fork's C8 interlock cannot tell the angle image from the torque images. |
| V8 | H's F5 claim ("camera 0xE4 has request 0 ⇒ A2 skips") | SPEC-angle-setpoint-interface §0 finding 3 (bus-2 census: camera request 1, torque up to \|702\|, while its LKAS runs); TRACE-dominance §3.2 ("request 0 **with stock LKAS off**") | **EVIDENCE (record).** True only under the camera-LKAS-off procedure that every other candidate also relies on. |
| V9 | `gp-0x6802` has one live lane reader and it only acts at value 2 | Python LE scan (`sg_scan.py`, the sentinel tracer's controlled scanner) of V295 + the tracer's lane decompile `dec_28ea6_v294.c` | **EVIDENCE:** readers `0x291EE` (lane: `if 6802 == 2 && …` in the STEER_STATUS/`gp-0x6758` counter branch), `0x2A3D0` (after the lane body, BELIEF dead twin), `0x4E86C` (UDS DID record). Used only for graft G2's alternative. |
| V10 | The merged graft passes the goal's time criteria | `op_merge.py`: G's rows + Kd + `ARB_A3` + ICL 8192 as ordinary scorer columns; 13 scenarios × 4 members × 19 speeds | **EVIDENCE (sim):** §2.4. BELIEF: bytes (no hex), GATE 2 (by construction = G's; not re-scored). |

---

## 2. Operability findings new in this judgment

### 2.1 Cross-centre override — the scenario no scorer ran (EVIDENCE: sim, `op_probe.py xc_*`)

The scorer's override takes the wheel from the held angle **toward** centre. An evasive move **against** the planned
curve takes it **past** centre. Release lurch past the setpoint (deg), worst over nominal and b_lo×J_hi:

| cand | < 8 | 8–12.5 | 12.5–22 | > 22 | firm 2400, 8–12.5 / 12.5–22 |
|---|---|---|---|---|---|
| P2 (and F2/D2a/B0r) | 15.0 | 13.5 | 8.0 | 3.5 | 12.5 / 3.0 |
| E1-cal / E1-reset / E2-R1 / E2-L | 26.4 | **26.6** | 18.9 | 6.3 | 16.7 / 3.0 (reset 12.2 / 0.9) |
| E1-freeze / E2-S | 26.4 | 22.0 / 21.8 | 4.4 / 4.1 | 0.9 | 12.0 / 0.9 (S 16.2 / 2.9) |
| E2-A2 / A2-X | 26.4 | 12.2 | **8.9** | 1.5 | 10.7 / 2.7 |
| E2-A3 / A3-12k | 15.2 | 12.2 | **8.9** | 1.5 | 10.7 / 2.7 |
| G-P48d (ICL 4096, Kd 48) | 10.2 | 10.0 | 6.9 | 3.3 | 9.1 / 2.4 |
| H-A / H-B | 22.2 / 21.8 | 24.6 / 22.7 | 17.3 / 16.3 | 7.8 | 9.4 / 2.1 |
| **M-P48d-A3 (graft)** | **10.3** | **8.8** | **7.8** | **1.4** | **7.5 / 2.1** |

**Reading.** The ARB's bound is `(|θ| << sh) + B`: when a hand holds the wheel on the far side of centre, |θ| grows again
and so does the bound, so the I winds (to 4452 S ≈ 713 T at 12.5–15 m/s). The ARB is still far better than any
unbounded raised ICL, but on this geometry it is **no better than P2 at 12.5–22 m/s**. A 3 s hold changes nothing
(`xc3_lt400` = `xc_lt400` to 0.1°): the bound, not the time, sets the I. **Not declared by E2** (its hand family never
crosses centre). The stiff-hand, constant-word convention is BELIEF (E2 §2.2 argues a real hand reads more than 512 words
when it holds the wheel past centre against the spring, which would trip the hard freeze instead).

### 2.2 Straight-line disturbance rejection — the ARB's price (EVIDENCE: sim, `op_probe.py crown_*`)

θ_sp = 0, a constant road torque d (crown, crosswind) from 1 s, no hand; steady |θ| error (deg), worst of nominal / b_lo×J_hi:

| d | cand | 8–12.5 m/s | 12.5–22 | > 22 |
|---|---|---|---|---|
| 300 T | every non-ARB candidate (P2, E1, E2-R1/S, G, H) | ≤ 0.11 | ≤ 0.05 | ≤ 0.05 |
| 300 T | E2-A2 / A3 / A3-12k / A2-X, M-*-A3 | **1.1–1.25** | **0.45–0.47** | 0.25–0.30 |
| 450 T | every non-ARB candidate | ≤ 0.15 | ≤ 0.06 | ≤ 0.05 |
| 450 T | E2-A2 / A3 / M-*-A3 | **2.85–3.0** | **1.05–1.14** | 0.75–0.79 |

**Reading.** At θ ≈ 0 the bound is B = 1250 S ≈ 200 T, so the I cannot carry a constant load above it; the error grows
until `slope·|θ|` makes up the rest (26 T/deg ≤ 12.5 m/s, 102 T/deg above). This is E2's declared M-E2-4 ("never seen on
r71b"), now quantified. **E2's own on-car revert ("a steady hands-off error > 1° on a straight at ≥ 12.5 m/s") is
reachable at ~450 T.** EVIDENCE for the mechanism and the numbers in the model; **BELIEF** for how large real crown and
crosswind loads are in T counts (E2's r71b check: every steady hands-off hold ≥ 43 T under the bound). The fork's outer
loop sees the resulting lane drift and corrects the setpoint (BELIEF: slowly, τ_o ≥ 1 s).

V4 closes the obvious fix: a **signed** bound fixes §2.1 (8.9° → 1.7°) and **doubles** this drift (1.14° → 2.37°). A road
load and a hand are the same geometry to an angle-referenced bound; only a torque word separates them, and the torque
word cannot separate a light hand from the resting-hand / reaction torque (E1 §2.2, E2 §2.2, scorer finding 3). **This is
the design's irreducible trade; it must be a declared miss with the E2 revert, not engineered away.**

### 2.3 Wrong payload: the stock camera's command read as an angle (EVIDENCE: sim `cam30`; record for the camera)

Every candidate drives a phantom 30° setpoint (request held 1) to 20–32° within 0.5 s at 12.5–27 m/s (P2 19.5–23.2°,
E1-cal 24.6–27.3°, E2-A3 24.4–27.3°, G-P48d 19.7–23.0°, H-B 23.3–26.4°). At 19–27 m/s that is a violent swerve. Raised
I authority makes it slightly worse at 1 s (E2-A3 28.6–31.9° vs P2 21.6–26.4°). **H-cam is not fail-safe in firmware for
any submitted candidate**; the camera-LKAS-off procedure is a hard flight prerequisite for all of them, and graft G2 is the
only firmware closure on the table.

### 2.4 The merge both scorers point to (EVIDENCE: sim `op_merge.py`; BELIEF: bytes, GATE 2 on a built table)

The frequency scorer passes only G's skeletons on the R2 box (finding 2) and shows that no integral policy moves GATE 2
(finding 1: every freeze / bound state runs the I-frozen PD loop, which passes for every skeleton). The time scorer passes
only the E2-A family. So G's table + Kd 48 with E2-A3's block at ICL 8192 should inherit both. Measured on the common
time scorer (worst over the four members; vgr frame; speeds 3.1–30 incl. 9, 10.25, 11, 11.9, 12.5, 13.5):

| metric | P2 | E2-A3 | G-P48d | **M-P48d-A3** | **M-P48-A3** | M-F24-A3 (pol-free) |
|---|---|---|---|---|---|---|
| tracking r71b, replayed word 8–15 / 15–22 / > 22 | 0.892 / 0.855 / 1.000 | 0.985 / 0.991 / 1.000 | 0.891 / 0.859 / 1.000 | **0.981 / 0.991 / 1.001** | 0.980 / 0.987 / 1.001 | 0.981 / 0.983 / 1.000 |
| turn-hold a ≤ 2.0, min ≥ 8 / a 2.5 | 0.73 / 0.69 | 0.99 / 0.98 | 0.74 / 0.70 | **0.99 / 0.98** | 0.99 / 0.98 | 0.99 / 0.98 |
| in-phase ±1° 0.2 Hz: 10–12.5 / 12.5–15 / 15–22 | 0.88 / 0.88 / 0.86 | 0.88 / 0.88 / 0.86 | 0.70 / 0.88 / 0.89 | 0.70 / 0.88 / 0.89 | 0.69 / 0.76 / 0.73 | 0.62 / 0.65 / 0.66 |
| light lurch (400) ≥ 8 / < 8 | 10.9 / 11.9 | 5.8 / 12.0 | 9.9 / 7.7 | **4.1 / 7.7** | 4.1 / 7.7 | 4.1 / 8.1 |
| firm lurch ≥ 8 / < 8 | 7.9 / 11.5 | 4.7 / 10.8 | 6.2 / 7.4 | **3.2 / 7.0** | 3.2 / 7.0 | 3.1 / 7.2 |
| cross-centre light ≥ 8 (§2.1) | 13.5 | 12.2 | 10.0 | **8.8** | 8.8 | 8.9 |
| crown 300 T, 8–12.5 (§2.2) | 0.04 | 1.13 | 0.10 | 1.19 | 1.21 | 1.25 |
| engage droop ≥ 8 / co-steer ≥ 8 | 6.3 / 2.4 | 6.3 / 2.4 | 6.0 / 2.3 | 6.0 / 2.3 | 6.0 / 2.3 | 6.6 / 2.5 |
| timeout mid-motion 10–12.5 | 2.29 | 2.29 | 2.43 | 2.42 | 2.43 | 2.57 |
| hard turn 1.6–3 Hz ratio, 8–10 | 1.53 | 1.43 | 1.17 | **1.08** | 1.07 | 0.99 |
| R2-box fails (SCORE-FREQ T0, by construction) | 690 | 690 | 166 (declared) | 166 (declared) | **0** | 0 |

Dwell-then-jump on ±1° at 0.2 Hz is 0 at ≥ 8 m/s for all of these and 40–44 below 8 m/s (the shared M1 class). **Reading:**
the merge is the first column on the panel that passes every decidable time criterion **and** whose small-signal loop
passes the R2 box (M-P48-A3) or fails only a declared product (M-P48d-A3). G's D and table also cut the release lurch
the ARB leaves (5.8° → 4.1°) and the cross-centre case (12.2° → 8.8°). It inherits the ARB's crown drift (§2.2) and G's
weaker small-signal gain at the 10–12.5 m/s dip.

---

## 3. Fail-safe matrix (rows = fault; EVIDENCE unless marked)

| fault | shared structure | who differs | source |
|---|---|---|---|
| 0xE4 fault sentinel (`gp-0x69ae` 0x7FFF, request 0xFF) | A2 `0x29A56 da05 → b205` skips the PID; \|T\| ≤ 78 counts from 50 ms, peak ≤ 430 | none (all 30 columns) | TRACE-sentinel §3.3; SCORE-TIME §5.4 |
| 0xE4 timeout (510–514 ms hold, then sentinel) | last θ_sp held; mid-motion excursion 2.1–2.6° at 8–12.5 m/s, ≤ 0.6° in a held turn | G-P48L 2.9°, H-A 2.6°; ICL-raised columns hold a turn better (E2 T5: 1.01° → 0.58°) | TRACE-dominance §3; SCORE-TIME §5.4 |
| request drop | \|T\| = 0 by +150 ms | none | SCORE-TIME §5.4 |
| `gp-0x67fe ≠ 2` (θ forced to 0) | B2 `0x29A50 → e0df3443` skips the PID on the same tick | none (all carry B2; H lists it) | TRACE-sentinel §4.2; TRACE-dominance §1 |
| mode ≠ 3 / baseline `0x7FFF` (`gp-0x679c ≠ 3`, angle relative, in range) | **no firmware gate in any candidate**; fork B3 (drop request unless 0x14A b4 bit 1) | none | TRACE-sentinel §4.3 |
| baseline −0x8000 wrap | ±12000 bail → PID skip, STEER_STATUS 7 latched to key cycle | none | TRACE-sentinel §4.1 |
| **wrong payload: stock camera 0xE4** (relay close, camera LKAS on) | **not fail-safe in firmware** (§2.3); procedure only | E2-A2S-C (+20 B, needs 6803 = 2) is the only firmware gate offered — not common-scored | rev2-A H-cam; E2 §4.4 |
| **wrong payload: a torque-mode fork on the angle image** | V1 F181 `…,A16A` + the fork's C8 interlock | **H-A / H-B omit V1** (§1 V7) | TRACE-dominance §4; rev2-A H-fork-tq |
| motor rate invalid (`gp-0x6abe` = 0x7FFF) | fresh-D caves carry Honda's ±13000 form (H1 incl. 0x7FFF, 0 mismatches); held D reads the zeroed cell | **H-A: no listing** — the guard is described, not assembled (BELIEF) | JUDGE-bytes-risk §2.1; SCORE-TIME §1 H1 |
| pol ≠ −1 (image on another car) | pol = −1 boot-static on this car (record) | **fresh-D columns depend on it** (P2, D2a, E1-\*, E2-\*, G-P\*, H-A, M-P\*); pol-free: F2, B0r, G-F24\*, G-A22\*, H-B, M-F24-A3 | REFUTE-C2-r2-stability F8 |
| new RAM writes | none (P2 skeleton, E2, G fresh/held) | `gp-0x6dd0` (the lane's own I8) by E1-reset/freeze/bleed/sched/splitP and H's bleed; G-A22: `gp-0x6c44/-0x6c40` + an untraced `gp-0x6cf8` accessor | E1 §4; G §9 |
| bytes not assembled (BELIEF until a built-image decode) | — | E1-bleed, E1-sched, H-A, H-B, the merge graft | SCORE-TIME §1 |

---

## 4. Override, engage, co-steer (common time scorer, worst over four members, deg; vgr)

| family | light (400/511/1000) ≥ 8 | light < 8 | firm 2400 ≥ 8 | firm < 8 | cross-centre light ≥ 8 (§2.1) | engage droop ≥ 8 | co-steer ≥ 8 | hand-effort against a firm hand |
|---|---|---|---|---|---|---|---|---|
| P2 / F2 / D2a / B0r | 10.9 | 11.7–11.9 | 7.6–7.9 | 11.4–11.5 | 13.0–13.5 | 6.3–6.4 | 2.4–2.5 | stock arm (0.30 at 2048 raw) |
| E1-cal / E2-R1 / E2-L | **24.3** | 23.1 | 8.4 (L 4.2) | 22.2 | 26.6 | 6.3 | 2.4 | stock |
| E1-reset | **24.3** | 23.1 | 4.2 | 18.7 | 26.6 | 6.3 | 2.4 | stock |
| E1-freeze | 11.8 (8–10 only; ≤ 4.5 above) | 23.1 | 4.1 | 18.4 | 22.0 | 6.3 | **1.3** | stock |
| E2-S | 11.1 (8–10 only) | 23.1 | 8.2 | 22.0 | 21.8 | 6.3 | **1.3** | stock |
| E2-A2 | **5.8** | 15.5 | 4.7 | 14.1 | 12.2 | 6.3 | 2.4 | stock |
| E2-A3 / A3-12k | **5.8** | 12.0 | 4.7 | 10.9 | 12.2 | 6.3 | 2.4 | stock |
| E2-A2-X | 5.8 | 15.5 | 4.7 | 14.1 | 12.2 | **4.3** | 2.4 | **×1.8–2.1 harder** (V5) |
| G (ICL 4096) | 9.6–11.9 | 7.7–9.9 | 6.0–6.9 | 7.4–9.6 | 10.0–12.0 | 5.8–6.9 | 2.2–2.7 | stock |
| H-A / H-B | 22.2 / 20.8 | 19.5 / 19.3 | 2.8 / 3.3 | 15.4 / 16.8 | 24.6 / 22.7 | 6.5 / 6.3 | 2.5 / 2.4 | stock |
| E2-K0 | 20.0 | **51.7** | 5.1 | 13.9 | — | 6.3 | 2.2 | stock |

The 8° light/firm bar is rev2-B's pre-registered gate (a time gate of the brief, not one of the goal's own criteria). Only
the E2-A family and E1-bleed clear it at ≥ 8 m/s on the scorer's geometry; E1-bleed fails the goal (§9).

---

## 5. Authority character per band

| quantity | P2 skeleton (P2, D2a, E1, E2) | G tables | H | source |
|---|---|---|---|---|
| Kp_eff by band (dip at 10–12.5 m/s) | 523–578 / 579–666 / 285–668 / **234–283** / 286–454 / 458–772 / 774–932 (0–5 … 22–35 m/s) | dip deepened (G 438–474 vs 537 at the dip; G-P48 1015 vs 1359 at 17 m/s) | D2a's / B0r's tables | rev2-A §7.1; G §7.2c |
| I ceiling (T, through fade 254/256, lag 0.990, fwd 5346/32768) | 657 (ICL 4096) / 1313 (8192) / 1969 (12288) — the ARB caps it at 200 T + 26 T/deg (≤ 12.5 m/s) or 102 T/deg | 657 | 1202 (7500) | E1 §1.1; E2 §3.6 |
| rail / P clamp / fade floor | 2461 / 15360 S / 0.297 (stock arm) | same | same | TRACE-hook; SPEC §4.5 |
| R2-box small-signal (ring risk in the credible set) | 690 fails; b_q×ms_free 8.2°, **1.27 Hz ζ 0.028**; b_lo×ms_free 13.3°, 0.81 Hz ζ 0.049 | G-P48/P44/F24/A22/P48L/k40: **0**; G-d: 117–169, all b_q×ms_free (1.26–1.35 Hz ζ 0.058–0.064, declared) | H-A 352 (incl. an **undeclared 0.84 Hz** b_lo ring); H-B 359+ | SCORE-FREQ T0, T9 |
| 5 Hz Re(T/ω) (V295 +2.46 damps) | −0.57 | −0.03 (P48d) … −0.94 (A22) | −0.40 / −0.69 | SCORE-FREQ T4 |
| hard turn 1.6–3 Hz ratio (8–10 m/s) | 1.43–1.53 | 0.99–1.23 | 1.13 / 1.26 | SCORE-TIME §5.4 |
| straight-line load (§2.2) | ≤ 0.05° (ARB: 0.45–1.25° at 300 T) | ≤ 0.15° | ≤ 0.05° | this page |

Every ring the R2 box predicts for the P2 skeleton lies inside rev2-A's R3\* stop band (0.5–5.5 Hz, ζ < 0.10 → REVERT),
so it is catchable on the car; it was not declared as a prediction by rev2-A, and E1/E2 declare it only as "inherited".
On operability, a 1.27 Hz wheel oscillation at ζ 0.03 in a credible corner is the worst symptom on the table after H-cam.

---

## 6. Fork prerequisites (fewer is better)

**Common to every candidate** (SPEC-angle-setpoint-interface §0, C1–C11): raw = −10·θ_sp in carState's frame, clipped;
the measured angle with request 0 while allowed-but-inactive (C3), 0 when not allowed (C4); slew from the measured angle
(C5); |θ_sp|, slew and **Δmax** bounds — the panda bounds none of them (C6); override O1 (C7); engage only on the A16A
fwVersion **and** 0x14A b4 bits 0–2 = 7 (C8) plus B3; SR map at θ_des (C9); the inner loop's delay (C10); other 0xE4 fields
0 (C11); **camera LKAS off** (procedure); re-header every revert `.rwd` to list A16A.

| candidate | extra | score /10 |
|---|---|---|
| P2/F2/D2a/B0r, E1-\*, E2-R1/S/L/A2/A3/A3-12k, G-\*, merge | none | 8 |
| E2-A2-X | byte 2 bits 3:2 = 2 on **every** frame (C11 changes; under A2 the ramp-out on a request drop no longer matters, TRACE-dominance §5.1) | 6 |
| H-B | none extra, **but** no distinct fwVersion, so C8 cannot be implemented (a manual toggle replaces the interlock) | 6 |
| H-A | as H-B **plus** the VGR/SR fold: the fork must convert both the setpoint and the measured angle it sends when inactive into the `gp-0x69ca` frame. `gp-0x6a00 = gp-0x3608 + pol·C(d) + gp-0x69ca` (TRACE-angle §2.1): the wire carries only gp-0x6a00, and gp-0x3608 depends on the stored baseline the fork does not see (BELIEF that an exact fold is not possible from the wire; SCORE-TIME modelled a perfect fold). An unconverted measured angle at engage is a 0–15 % setpoint step (EVIDENCE: the 1.155 slope; magnitude BELIEF). | 3 |
| E2-K0 | a fork angle integral (τ_o ≥ 1 s, freeze above the pressed threshold): fork code beyond the interface | 2 |

---

## 7. One short drive: is the edit LIVE, and does it size the next step?

| candidate | LIVE on the wire without a deliberate act | needs a deliberate episode | sizes the next step? | /15 |
|---|---|---|---|---|
| raised ICL (E1-cal/reset, E2-R1) | **yes:** a 1.5–2 m/s² curve at 15–22 m/s held within ~2° hands-off (P2 lags ~5°); rev2-A §7.1 c_I/c_P | the lurch shows on any let-go | yes: the hold error vs ICL | 12–13 |
| ARB (E2-A2/A3/A3-12k) | the raised hold, as above | **one 15 s light-hand hold at 10–15 m/s** (E2 §8: I component flat vs ramping); its null sentence is written | yes; and §2.2's straight-line drift is directly the E2 revert (> 1° on a straight ≥ 12.5 m/s) | 12 |
| E2-A2-X | as A2, plus the 0.10 s ramp-in at every engage edge on the 427 tap | — | yes | 12 |
| E1-freeze / E2-S | raised hold | a hands-on episode above 320 / 300 words | partly | 11 |
| G-\* | **c_D 0.57 vs P2's 0.40** (window 0.45–0.70, G §8.2); the frame by angle-window regression (needs \|θ\| > 85° below 8 m/s) | the frame test needs a parking-speed manoeuvre | yes for the D; the drive would also re-show F1 | 12–13 |
| round-1 four | rev2-A §7.1's full LIVE table | — | yes, but F1 is a foreseeable FAIL | 12 |
| H-A | the loop variable (gp-0x69ca) is not on the wire; the regression on 0x14A is in the wrong frame unless the analyst applies C⁻¹ (and gp-0x3608); the I-bleed tap bit is proposed but undesigned | — | weakly | 7 |
| H-B | as round-1, but the bleed tap is undesigned | — | partly | 9 |
| E2-K0 | fork-side integral readable in fork logs | — | partly | 8 |

---

## 8. Subscores

| id | Goal /20 | Fail-safe /20 | Override /20 | Authority /15 | Fork /10 | Read /15 | **total** |
|---|---|---|---|---|---|---|---|
| E2-A3 | 20 | 15 | 16 | 5 | 8 | 12 | **76** |
| E2-A3-12k | 20 | 14 | 16 | 5 | 8 | 12 | **75** |
| E2-A2 | 20 | 15 | 14 | 5 | 8 | 12 | **74** |
| E2-A2-X | 20 | 15 | 13 | 5 | 6 | 12 | **71** |
| E1-freeze | 19 | 14 | 10 | 6 | 8 | 11 | **68** |
| E2-S | 19 | 15 | 9 | 6 | 8 | 11 | **68** |
| E1-reset | 19 | 14 | 5 | 6 | 8 | 12 | **64** |
| E1-cal | 19 | 15 | 3 | 6 | 8 | 13 | **64** |
| E2-R1 | 19 | 15 | 3 | 6 | 8 | 13 | **64** |
| G-P48 | 4 | 15 | 12 | 10 | 8 | 13 | **62** |
| G-P48d | 5 | 15 | 12 | 9 | 8 | 13 | **62** |
| G-P44 | 4 | 15 | 11 | 10 | 8 | 13 | **61** |
| G-P44d | 5 | 15 | 11 | 9 | 8 | 13 | **61** |
| G-P48k40 | 4 | 15 | 12 | 8 | 8 | 12 | **59** |
| G-F24 | 3 | 16 | 11 | 7 | 8 | 13 | **58** |
| G-F24d | 4 | 16 | 11 | 6 | 8 | 13 | **58** |
| P2 | 5 | 15 | 10 | 6 | 8 | 12 | **56** |
| D2a | 5 | 15 | 10 | 6 | 8 | 12 | **56** |
| F2 | 5 | 16 | 10 | 5 | 8 | 12 | **56** |
| B0r | 5 | 16 | 10 | 5 | 8 | 12 | **56** |
| G-P48L | 3 | 15 | 11 | 7 | 8 | 12 | **56** |
| E1-bleed (DQ) | 3 | 13 | 15 | 6 | 8 | 10 | 55 |
| E2-L (DQ) | 9 | 15 | 3 | 6 | 8 | 11 | 52 |
| G-A22 | 3 | 13 | 10 | 6 | 8 | 12 | **52** |
| E1-sched | 6 | 13 | 9 | 5 | 8 | 10 | **51** |
| G-A22d | 3 | 13 | 10 | 5 | 8 | 12 | **51** |
| H-B (DQ) | 11 | 11 | 5 | 5 | 6 | 9 | 47 |
| E1-splitP (DQ) | 3 | 14 | 11 | 0 | 8 | 10 | 46 |
| H-A (DQ) | 10 | 9 | 5 | 6 | 3 | 7 | 40 |
| E2-K0 (DQ) | 4 | 12 | 2 | 4 | 2 | 8 | 32 |
| *graft M-P48d-A3* | *20* | *15* | *17* | *8* | *8* | *13* | *≈ 81* |
| *graft M-P48-A3* | *19* | *15* | *17* | *9* | *8* | *13* | *≈ 81* |
| *graft M-F24-A3* | *19* | *16* | *17* | *6* | *8* | *13* | *≈ 79* |

Goal points: 20 = passes every decidable criterion in every band ≥ 8 m/s with the replayed word; 18–19 = passes with a
small cost; ≤ 6 = fails tracking/turn-hold (F1) in a band. The lurch bar is scored under Override, not Goal.

Not ranked (not on the common time scorer): E2-A (one slope), E2-A2S, E2-A2-NR, E2-A2S-C. By E2's own T3/T5, A2S equals A2
plus the co-steer benefit of E2-S (1.0° vs 2.2°) for −0.006 of replayed tracking; A2-NR is dominated by A2-X's droop.

---

## 9. Disqualifications (with cause)

| id | cause on this lens | re-admissible? |
|---|---|---|
| **E1-bleed** | The 256–512-word bleed drains the hold whenever the driver's resting hand reads in that band: replayed-word tracking **0.752 / 0.739 / 0.829** (SCORE-TIME). The hold evaporates in normal hands-off driving. Its designer rejected it; confirmed. | No (the band is the resting-hand band). |
| **E2-L** | Leak above 512 words: replayed tracking **0.938** at 8–15 m/s, and the light-hand lurch is unbounded (24.3°). Designer rejected; confirmed. | No. |
| **E1-splitP** | ρ = 1.0000 (ζ ≈ 0) on b_q×ms_free+h10 at 19 m/s; 5052 R2-box fails including nominal; turn-hold 0.75. | No. |
| **E2-K0** | The hold depends on fork code beyond the interface; a light hand winds the fork integral without any firmware bound: release lurch **51.7° below 8 m/s, 20° at 8–10**; real-curve hold 0.65. Designer withdrew it. | No. |
| **H-A, as written** | (1) No V1: the angle image carries V295's F181, so C8 cannot exclude a torque fork (§1 V7). (2) Its coupled F1↔F4 claim fails on the common scorer: light lurch **22.2°** (claimed < 4°; the 512 threshold never sees a ≤ 511-word hand) and replayed tracking **0.925 / 0.947** (undeclared). (3) Its published GATE-2 numbers belong to a different loop (SCORE-FREQ disagreement 1). (4) A fork fold the wire may not support (§6) and an engage-frame step. (5) No listing (the validity guard on gp-0x6abe is described, not assembled). (6) An undeclared 0.84 Hz ring (SCORE-FREQ T0). | As a new design only: its fresh `gp-0x69ca` operand is a graft (G7). |
| **H-B, as written** | (1), (2) (light **20.8°**, replay **0.933**), (5); plus undeclared R2-box fails (b_q×J1.0+h10 29.9°, J_hi+h10 41.4° strict) and 13 Hz anti-damping ×1.9 V295 (declared). | As a new design only. |

**Written before scoring, as a FAIL for this judge:** (a) a torque path without a valid current setpoint that A2/B2 or a
validity guard does not cover; (b) an integral policy whose goal metric fails in normal hands-off driving because it reads
the resting-hand torque word; (c) an override release with no firmware bound at all; (d) a fork prerequisite the fork
cannot satisfy from wire data or a missing fwVersion interlock; (e) a decision-bearing published claim the common scorers
refute. (b) fired on E1-bleed, E2-L, H-A, H-B; (c) on E2-K0; (d) on H-A, H-B; (e) on H-A, H-B. (a) fired on no submitted
candidate; H-cam is shared by all and is scored, not disqualifying.

---

## 10. Grafts

| # | graft | why (this lens) | evidence / what it still needs |
|---|---|---|---|
| **G1** | **Carry E2-A3's policy block (ARB + low-speed cap) and ICL 8192 onto G's skeleton (G-P48 or G-P48d table + Kd 48).** | The only combination that passes every decidable time criterion **and** a clean or declared R2 box; lowest release lurches on the panel (light 4.1°, firm 3.2°, < 8 m/s 7.7°), cross-centre 8.8°, hard-turn 1.08. Choose **M-P48-A3** if the orchestrator rules b_q×ms_free credible (0 fails; in-phase 0.76 / 0.73 at 12.5–22), **M-P48d-A3** if not (166 declared, 1.28 Hz ζ 0.06 under R3\*; in-phase 0.88 / 0.89). | EVIDENCE: §2.4 (common time scorer, references reproduce). BELIEF until done: assemble (E2-A3's 222-B code with G's rows; the bound reads `gp-0x6a00`/`gp-0x6dd0`/`gp-0x6a5e` as in E2's H1), H1 on the bytes, `g_gate.py` on the built table (SCORE-FREQ finding 1 says the policy cannot move it), full 0.25 m/s time grid. |
| **G2** | **A firmware camera interlock without the fade-arm cost:** E2-A2S-C's per-tick gate (`cmp r0,r25 ; be CAM`, +20 B) **plus** copying the stock fade-B values (`0xE564C`: X 16/26/38/48/64/96, Y 255/243/218/179/77/77) into the 6803 = 2 record (`0xCBAE4[7] → 0xE54FC`, 12 halfwords; the SPEC's own F3 note), with the fork packing byte 2 bits 3:2 = 2 every frame. Optional belt-and-braces: SPEC F3's one-byte engage gate `0x2937C fa 1d → f5 1d`. | Closes H-cam — the only fault on the table that is not fail-safe in firmware (§2.3) — keeps A2-X's −33 % engage droop, and removes its ×1.8–2.1 heavier override (§1 V5). | BELIEF: the camera never sends 2 on the operator's current routes (12-route census EVIDENCE; re-measure bus 2); a reader census of `0xE54FC`; whether r25 = 0 mid-drive while engaged through the 2-arm drops the ramp (E2's CAM path zeroes P/D/I regardless). Alternative to trace: a cave gate on `gp-0x6802 == 0` (openpilot packs 0; the camera's byte 2 & 0x7F = 1 per the kit record) needs no fork change; `gp-0x6802`'s only live lane reader acts at value 2 (§1 V9). BELIEF on the camera's bits 1:0. |
| G3 | **V1 (`0x1310D 30 → 41`, F181 `…,A16A`) is mandatory** on any angle image (H omits it). | The C8 interlock against a torque fork on the angle image. | EVIDENCE (TRACE-dominance §4). |
| G4 | **Keep the ARB unsigned; declare its straight-line cost.** Add §2.2's numbers to E2's M-E2-4 and keep its revert (> 1° on a straight ≥ 12.5 m/s). If on-car straights show drift, raise B or schedule it by speed — do **not** sign the bound. | §1 V4: signing fixes the cross-centre lurch but doubles crosswind/crown drift. | EVIDENCE (sim) for the trade; BELIEF for real load magnitudes. |
| G5 | Declare §2.1's cross-centre lurch for the ARB family (12.2° at 8–12.5, 8.9° at 12.5–22 m/s; merge 8.8° / 7.8°) with R9. | Undeclared on E2's page. | EVIDENCE (sim). |
| G6 | Drop E1's firm reset from any ARB design. | The ARB already gives a firm lurch of 4.7° (merge 3.2°) without a RAM write; the reset's 4.2° buys nothing measurable and adds the first cave write to `gp-0x6dd0`. | EVIDENCE: SCORE-TIME. |
| G7 | H-A's fresh 1 kHz `gp-0x69ca` feedback — the only loop whose margins do not depend on slot-4 timing (SCORE-FREQ finding 3) — as a later-round structure. | Removes the 100 Hz hold from the feedback. | Needs a fork fold the wire supports (gp-0x3608), a table refit under the ms_free products, a listing, and a 69ca tap for the drive. |
| G8 | E2-S's opposing-hand freeze (E2-A2S, +16 B) if co-steer release droop matters. | Co-steer droop halves (2.4° → 1.3°) at −0.006 of replayed tracking. | EVIDENCE: E2 T5 / SCORE-TIME. |
| G9 | Instrument for any fresh-D merge: G's c_D window (0.45–0.70 vs P2's 0.40) and the angle-window frame test, plus E2's light-hand episode; carFw A16A. | One drive reads the D size, the frame, the bound and the goal. | G §8.2; E2 §8. |

---

## 11. Disagreements (with cause)

1. **E1 vs the common scorer — E1-freeze is not "dominated".** E1: light lurch "stays 11–13° at 10–12.5 m/s". Scorer and my
   probe: **4.5°** at 10–12.5 m/s, 11.8° only at 8–10 m/s; co-steer droop halves. Cause unidentified (E1's speed grid and
   hand differ); the scorer wins.
2. **E1 — M6-E1 is under-quantified** (declared ~17°, scorer 24.3° at 10.25 m/s; E1's grid skips 10.25–12.25 m/s). A
   declared miss that its number does not cover is not covered (brief's rule); scored down, not disqualified, because
   R9 still catches it.
3. **H — "A2 closes the camera hole"** holds only with the camera's LKAS off (§1 V8). H's F5 resolution is the same
   procedure everyone relies on.
4. **H — "ICL 7500 + bleed makes a raised ICL safe"**: refuted by the scorer (22.2 / 20.8°) and its bleed fails the replayed
   tracking (undeclared). H's "THR → 256" suggestion would be worse (E1-bleed: 0.74–0.83).
5. **H — no V1** (§1 V7); H's fork prerequisite 4 removes the C8 interlock.
6. **E2 — M-E2-4 "never seen on r71b"**: true of r71b's holds; §2.2 quantifies the drift a modest constant load produces and
   shows E2's own revert is reachable at ~450 T. BELIEF on real loads.
7. **E2 — the hand family never crosses centre** (§2.1); the ARB's advantage over P2 vanishes at 12.5–22 m/s there.
8. **E2-A2-X** — E2's "×1.8 harder against a 2400-word hand" is confirmed by my byte read (×1.78; ×2.13 at 2048 raw) and by
   simulation (×1.79–1.81).
9. **G — "every implementation passes every pre-registered bar"**: true of rev2-A's bars; on the goal, F1 stands on every G
   column (SCORE-TIME finding 5), so G alone cannot fly toward the goal.
10. **The round-1 bytes-risk judge** ranked D2a 82 / B0r 81. On this round's scorers both fail F1 (tracking 0.856 / 0.852 at
    15–22 m/s) and the R2 box (702 / 706). Not a contradiction of that judge's lens; new evidence.
11. **SCORE-TIME's lurch scenario** takes the wheel toward centre only, and it has no straight-line load or wrong-payload
    case; §2 adds them. Its numbers on the cases it ran are reproduced exactly (V1).

---

## 12. Limits (what this judgment cannot see)

- **My scenarios reuse the common engine** (Karnopp plant on the r71b family, the scorer's sensors and lane). They are new
  scenarios, not an independent check of the engine; the engine's own controls (SCORE-TIME §1) are what make them credible.
- **The hand is the scorer's stiff-hand, constant-word convention** (κ → ∞). E2 §2.2 shows a consistent sensor would trip
  the 512 freeze earlier and shrink the light-hand lurches of every unbounded policy; the ranking between policies holds in
  both conventions (E2 T3), the absolute numbers are BELIEF.
- **Road-load magnitudes** for §2.2 and the camera's command shape for §2.3 are BELIEF; the mechanisms are EVIDENCE in the
  model.
- **The merge (G1) has no bytes and no frequency re-score** on a built table. Its GATE 2 is G-P48(d)'s by SCORE-FREQ finding 1.
  Its time grid here is reduced (19 speeds, not 94).
- **"Feel"** (override effort in Nm, how a 1.27 Hz ζ 0.03 ring feels) is not modelled; the operator scores symptoms.
- Everything above ~8 Hz is model (BELIEF on the plant); no 13–20 Hz claim on this page is decision-bearing.

---

## 13. Files (all `python`, the bin_decompile env; fixed seeds)

| file | what | output |
|---|---|---|
| `panel2/judge-operability/op_probe.py` | the scorer's lane/engine imported by path; positive controls + cross-centre override, crown, camera step | `_scratch/angle_loop/judge-operability/op_probe.json` |
| `panel2/judge-operability/op_signed_arb.py` | signed vs unsigned ARB (one-line monkeypatch) on cross-centre and crown | `…/op_signed_arb.json` |
| `panel2/judge-operability/op_merge.py` | graft G1: G rows/Kd + E2-A3 block + ICL 8192 through the scorer's own scenarios and metrics, references in-batch | `panel2/judge-operability/op_merge_out.txt`, `…/merge.json` |
| `panel2/judge-operability/op_merge_probe.py` | the §2.1–2.3 scenarios on the merged columns | `…/op_merge_probe.json` |
| `panel2/judge-operability/op_report.py` | writes every probe table from the JSON caches | `panel2/judge-operability/op_probe_out.txt` |
| (inline, §1 V5) | V295 fade records read LE; firm-hold lane torque A2 vs A2-X | quoted in §1 |
| `_scratch/angle_loop/sentinel_gates/sg_scan.py` (the tracer's, unchanged) | `gp-0x6802/-0x6803/-0x6805` access census on V295 | quoted in §1 V9 |
