# REFUTE C3 rev2 — NONLINEAR lens (2026-10-01)

**Verdict: REFUTED. Do not flash the committed PRIMARY `C3-rev2-P` flight artifact as it stands.**

The refutation is specific and must be read precisely, because the two halves point opposite ways:

1. **The committed PRIMARY FLIGHT CAVE does not implement the loop the design scored.** The design's named
   primary flight cave — `c3b_cave_C3B-P.hex`, sha **`9a10cdc4ec75`**, the 240 B cave — carries its G-table pointer
   `mov 0xC4CC4,r9` while the +2 B op-skip pushed the actual 42 B GB-P table to **0xC4CC6**. The cave's G-walk reads
   the table from the stale pointer (2 bytes early), so the delivered gain schedule is **not GB-P**: it is a single
   rising ramp, **G ≈ 2129 → 3613 over 8 → 26 m/s, 1.5× (8 m/s) to 4.4× (11.75 m/s) the design's GB-P**, with the
   whole N2 dip (GB-P's 559 @ 11.75 m/s) **inverted into a peak**. This is undeclared, has no stop band, and the loop
   that would fly was never gated. (EVIDENCE: Python LE byte read, positive-controlled against the aligned 238 B
   score cave; the build-script root cause is isolated below.)

2. **The underlying CONTROL DESIGN survives this lens.** When I simulate the loop the design actually intends and
   scored (the aligned GB-P table, Ki 40, A3 θ-bound + opposing-hand freeze sgn 300, fresh D), I find **no undeclared
   nonlinear miss at ≥ 8 m/s**. Every nonlinear behaviour I can reproduce — the outward release lurch (N1), the
   small-signal dip (N2), reversal overshoot (N5), turn-hold, centre hunt — matches the design's own declared
   numbers. So the refutation is of the **artifact**, not the concept: fix the pointer (re-link to 0xC4CC6 and re-H1
   the FLIGHT cave against §1.4) and the primary would implement the design.

The one finding that decides the verdict is #1. It is a latent build-script defect that the design's own §8 FAIL
criterion ("H1 bytes ≠ the §1.4 arithmetic") would have caught **had the flight cave been H1'd** — but the design's
H1 was run on the *score* cave (§3 of rev2-B is explicit), which is correctly aligned, so the defect was never
exercised.

**Lens.** Coulomb friction + stiction (Karnopp), the 0.1° quantisers, the integer lane, the cave's EXACT committed-byte
arithmetic (including the misaligned G-walk read), fade, sign-hold, ramp-in, light/firm override in both directions,
co-steer, release, the 510 ms timeout, road-noise hunt. **Members:** nominal, bc, F_hi, b_lo×J_hi. **Speeds:** 3, 5,
8–26 m/s. Tracking on route r71b's real angle paths with the run's real speed trace. **Safety:** nothing built, flashed
or sent; Ghidra read-only (`list_open_programs`, byte reads), nothing saved.

---

## 1. The decider — the primary flight cave's G-table pointer is stale by 2 bytes (HIGH, CONFIRMED)

### 1.1 The byte fact (EVIDENCE, Python LE, positive-controlled)

The committed cave hex files parse as follows (my own LE read; the `mov imm32,r9` table pointer is the sole `29 06`
in each; the table is its 42 trailing bytes ending in the `FF FF … ` sentinel row):

| cave hex | sha | len | table pointer `mov …,r9` | actual table addr | aligned? |
|---|---|---|---|---|---|
| `c3b_cave_C3B-P.hex` (FLIGHT, named in the design) | **9a10cdc4ec75** | 240 | **0xC4CC4** | **0xC4CC6** | **MISALIGNED by 2** |
| `c3b_cave_C3B-P_score.hex` (scored) | b5a1d0ce1e0e | 238 | 0xC4CC4 | 0xC4CC4 | MATCH |
| `c3b_cave_C3B-F.hex` / `_score.hex` (fallback) | 9de9365fa952 | 220 | 0xC4CB2 | 0xC4CB2 | MATCH |

**Positive control:** the score cave (same table, same pointer bytes, no op-skip) is correctly aligned by the same
reader — so the reader is sound and the flight cave's misalignment is real, not a parser artifact. The fallback caves
are also aligned. **Only the primary FLIGHT cave is wrong, and it is the only cave carrying the op-skip (+2 B).**

### 1.2 Why — the build splices +2 B without re-linking (EVIDENCE, `rb_build.py`)

`rb_build.assemble()` links the listing and bakes the table pointer `mov labels["TBL"],r9` at the **score-cave**
layout (table at 0xC4CC4). `add_opskip()` then does a **raw byte splice** — `code[:i] + bnh;jr(6 B) + code[i+4:]` —
replacing the 4-byte validity `cmovh r0,r26,r26` at cave offset 18 with the 6-byte `bnh CONT ; jr 0x2A164`. That
inserts 2 bytes **before** both the table and the already-baked pointer immediate, but **does not re-link the
pointer**. Diff of the two committed caves confirms it exactly: first divergence at cave off 18
(score `e0 d7 36 d3` = cmovh → flight `b3 05 b6 07 50 55` = bnh;jr), the remaining 216 bytes byte-identical but
shifted +2. So the table moved 0xC4CC4 → 0xC4CC6 while the immediate stayed 0xC4CC4.

The cave's walk (EVIDENCE, `e2_asm.listing`) is `mov TBL,r9 ; bh L1 ; … addi 6,9,9 (next row) ; ld.hu 2(r9) (G) …` —
it uses r9 as the table base and advances by 6 B per row. With r9 = 0xC4CC4 it reads row 0 as
`(X=0x0066=102, G=714, S=1178)` and the real GB-P rows shifted one u16, so the X-knot column becomes
`102, 1041, 59272, …` (non-monotonic; the 0xFFFF sentinel lands in a G field, not an X field).

### 1.3 The delivered gain (EVIDENCE, my independent G-walk on the committed bytes)

| v (m/s) | word | **G flown (flight cave)** | G intended (GB-P) | ratio |
|---|---|---|---|---|
| 8.00 | 1843 | 2129 | 1464 | 1.45× |
| 10.00 | 2304 | 2294 | 759 | 3.02× |
| 11.75 | 2707 | **2438** | **559** | **4.36×** |
| 15.00 | 3456 | 2706 | 847 | 3.19× |
| 20.00 | 4608 | 3118 | 1365 | 2.28× |
| 26.00 | 5990 | 3613 | 2080 | 1.74× |

The flown G rises monotonically with speed; the intended GB-P dips to 559 at 11.75 m/s. **The N2 fix — the entire
reason GB-P exists — is not merely absent on the flight cave, it is inverted.** The loop that flies has 1.5–4.4× the
designed loop gain at every speed.

### 1.4 Why it is a refutation (and what it is not)

- **Undeclared, un-gated.** The design states (§0.1, §0.2, §2, §10) the primary "is C3B-P byte-for-byte, so it is
  re-scored by construction" and that the flight cave "diverges from the score cave **only on an invalid rate**"
  (rev2-B §3). Both are FALSE: the flight cave diverges on **every valid tick** through the G-walk. GATE 2 (PM/GM,
  5–30 Hz, M20) was computed on the aligned score cave; at 1.5–4.4× loop gain those margins do not hold, and that
  flown loop was never gated. No miss in §5/§6 and no stop band covers it.
- **Honest limit of THIS lens.** My nonlinear **time-domain** simulation does **not** exhibit a behavioural harm from
  the error: higher gain tracks DC curves *tighter* and settles reversals *faster*, so turn-hold, centre hunt and the
  r71b low-frequency slope all look fine or better (§3). The real hazard of a 1.5–4.4× loop gain is **frequency-domain
  stability** (crossover pushed up, phase margin eroded, a likely 5–30 Hz line / grinding) — that belongs to the
  STABILITY lens, which must re-run GATE 2 on the FLIGHT cave's G, not the score cave's. I flag it; I did not
  reproduce it here.
- **Fixable, and the fix is known.** Re-link the flight cave's table pointer to 0xC4CC6 (or rebuild so `add_opskip`
  re-links) and H1 the **flight** cave against §1.4. The fallback `C3-rev2-F` is unaffected (its caves are aligned).

---

## 2. Independence and controls

| # | what | method | result |
|---|---|---|---|
| K1 | the two gain schedules | my own LE parse of both committed hex files; pointer = the sole `29 06`; table = the 0xFFFF-terminated 42 B | EVIDENCE: score aligned, flight off by 2 |
| K2 | cave-diff | byte diff of flight vs score cave | EVIDENCE: single 4→6 B swap at off 18, tail shifted +2, pointer value unchanged |
| K3 | my lane vs the round-1 refuter mirror | `Lane2('theta',56)` == `c3nl_sim.Lane` on C3-P, bit-for-bit (dθ 0, dT 0) | EVIDENCE, PASS (the round-1 control, re-used) |
| K4 | the intended table | my parsed GB-P rows == `rb_table.GB_P` (asserted in-script) | EVIDENCE, PASS |

The plant is the round-1 Karnopp integrator with the r71b member parameters; the lane, the misaligned-G glut, the
freeze and every metric are my own code in `_scratch/angle_loop/` (scripts listed in §6). Every claim below is from
scenarios/directions the common scorer does not run, or from the committed bytes directly.

---

## 3. What passes this lens on the INTENDED (aligned, scored) loop — the design reproduces (EVIDENCE)

Simulated with the aligned GB-P table, Ki 40, A3 θ-bound + opposing-hand freeze sgn 300, fresh D (Kd 48), members
nominal/bc/F_hi/b_lo×J_hi.

- **N1 outward release lurch** (worst over members, deg past the setpoint): aggressive 2·Aₕ outward drag
  **14.4°** at 8–12.5 m/s (design declares **14.3°**, M-N1/R9) and 5.6° ≥ 12.5 m/s; 1.5·Aₕ **7.2°**; inward partial
  drag 0.5·Aₕ **7.2°**; straight 5° nudge **2.0°**. Every realistic case < 8°; the single > 8° residual is the
  declared aggressive-drag corner. **Reproduces the design's declared N1 numbers — honestly declared, not a new miss.**
- **N2 small-signal in the 11–12.5 dip** (in-phase wire gain, worst member): ±0.3° 0.1 Hz 0.57–0.69; ±0.5° 0.2 Hz
  −0.08 to −0.27; ±1° 0.3 Hz −0.06 to +0.02; dwell-then-jump ≤ 6 events/group. **Matches the declared M-N2/M-C3B-N4
  collapse** — declared, with R9 cover.
- **N5 reversal overshoot** (a_lat 1.5, frac of A): 0.00–0.13·A, worst at 11.75 m/s — the declared "jerk" class
  (M-N5, R9). No dwell-then-jump.
- **turn-hold** (a_lat 2.0, mean hold t6–7.5 s): 0.99–1.00 at every band ≥ 8 m/s — passes ≥ 0.90.
- **centre hunt** (sp 0, 15 T rms road noise, 30 s): p2p ≤ 0.2°, 0 dwell-then-jump — no limit cycle.
- **r71b real-path tracking slope** (real speed trace, concatenated runs per band, worst member):
  INTEND 8–15 0.949–0.962, 15–22 0.986–0.988, > 22 0.990–0.996 (worst member 0.949 ≈ the 0.95 tracking bar,
  consistent with the design's declared ≈ 0.94 real-curve hold and M-N4 S-bend ≈ 0.94).

I find **no undeclared nonlinear miss ≥ 8 m/s on the intended loop**. The opposing-hand freeze (the new term) does not
misfire on co-steer (aiding hands do not satisfy sign(hand) ≠ sign(E′)) and introduces no new dead-band or hunt in
these scenarios.

## 3a. The flight cave's gain error is time-domain-benign (EVIDENCE, the honest negative)

Same scenarios, FLIGHT vs INTEND:
- centre hunt: FLIGHT p2p ≤ 0.2°, reversals/dj identical to INTEND — **no limit cycle**.
- reversal overshoot: FLIGHT 0.01–0.08·A (≤ INTEND's) — **no worse**.
- r71b concatenated slope: FLIGHT 8–15 0.982–0.988, 15–22 0.997–0.998, > 22 0.996–1.000 — **passes** (higher gain
  tracks the low-frequency curve paths tighter). turn-hold FLIGHT 1.00 throughout.

So my time-domain lens cannot, by itself, tell the flight cave from the intended one on these metrics — which is
exactly why the misalignment is dangerous and was missed: it is invisible to DC/low-frequency tracking and shows only
in the frequency-domain margins (flagged to the stability lens, §1.4).

---

## 4. Pre-declared misses on the INTENDED loop — checked, each honestly bounded

The intended loop's declared misses (M-C3B-F1 ms_free curve-hold ring, N3 dwell 8–10/>22, N4 S-bend gated members,
N5 reversal, N6 road load at θ≈0, N7 accel-out-of-curve, N8 aged lurch, 6/7/8 low-speed, M-N1 aggressive outward drag
14.3°) each carry a quantified prediction and a stop band (R3*/R4/R5/R9 or an on-car threshold). The ones this lens
re-derived (N1, N2, N5, turn-hold, hunt) reproduce within rounding. **None is an undeclared miss.** The ms_free
curve-hold ring and the two-mass modal / 13 Hz items are frequency-domain and belong to the stability lens.

---

## 5. Not verified, and why

- **The frequency-domain consequence of the flight cave's 1.5–4.4× gain** (PM/GM, a 5–30 Hz line). Out of this lens;
  flagged to the stability lens, which must run GATE 2 on the FLIGHT cave's G, not the score cave's.
- **κ** (the D-operand frame ratio 0.83–1.155) — a frequency/phase quantity, not re-derived here; the A3 bound and the
  freeze are κ-independent / sign-only.
- **Dwell-then-jump and hard-turn energy vs V282** — V282 is not simulable.
- **The op-skip's `0x2A164` fail-safe** (F3) — a fault-path decode, not a valid-rate nonlinear quantity; accepted as
  the judge's Ghidra-verified EVIDENCE.
- **pol = −1, the camera relay close (bytes-lens F5), the FB frame** — not part of this lens.
- **No built image exists** — every byte claim is about the committed hex files and the V295 image.

---

## 6. Files and reproduction (all `python`, bin_decompile env, fixed seeds)

Scripts and outputs in `_scratch/angle_loop/refute-c3r2-nonlinear/` (this session); reused infra in
`analysis-2020accord/studies/angle_loop/refute_c3_nonlinear/` and `c3/rev2B/`:

| script | what | output |
|---|---|---|
| `refute-c3r2-nonlinear/c3r2nl.py` | parse both caves; FLIGHT vs INTEND G; turn-hold; r71b per-run; INTEND N1 lurch; INTEND small-signal | `c3r2nl_out.txt` |
| `refute-c3r2-nonlinear/c3r2nl_b.py` | centre-hunt; reversal overshoot; concatenated-run r71b, FLIGHT vs INTEND | `c3r2nl_b_out.txt` |
| (inline Python) | cave hex parse, pointer vs table alignment, cave diff, sha, G-walk | — |
| `refute_c3_nonlinear/c3nl_sim.py`, `c3nl_lens.py`, `c3nl_r71b.py` | the round-1 independent lane/plant/scenarios (controlled bit-exact against the common scorer) | — |
| `c3/rev2B/rb_n1.py` | `Lane2` (configurable bound + Ki + opposing-freeze), reused for the Ki-40 loop | — |

Nothing was flashed, sent or built. No design file, scorer, shared cache, image or fork file was modified.
