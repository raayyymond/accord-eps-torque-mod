# HANDOFF 2026-09-09 — V289 flew: the notch WORKED and the ring RELOCATED to 15–17 Hz; H1 and H2 falsified; V290 designed, scored — and NOT CUT

**Read `docs/STATE.md`'s decision box first.** This is the narrative of the session that read V289 rev 1's
first two drives, tested the operator's two colleagues' hypotheses, designed and scored V290 — and ended
with the operator declining every candidate.

## 0. One paragraph
The operator drove V289 rev 1 on two routes (`…00000062--1c7daa54e8`, 975 s / 619 s engaged;
`…00000063--1d4b188022`, 707 s / 588 s engaged) and reported: ***"Grinding is still an issue."*** From the
wire — not the label — the notch cave was confirmed live on both. **The notch achieved its target
completely: the 18–22 Hz band is EMPTY on V289, 0 of 1414 present windows**, against 501 windows in
19–21 Hz alone on V282. What it did not do is quieten the car: **a different, pre-existing pole at
15–17 Hz became dominant** — one V282 already carried at |L| 1.13 with 30° of phase margin, which the
notch skirt (−41.6°) and the new feedback pole (+11.5°) spent. **Measured ζ is 0.029 on both builds: the
frequency moved, the damping did not.** V289 therefore hit its own pre-registered revert signature while
proving its own mechanism. Both colleague hypotheses were tested and both are false — H1's quantiser is
map-independent and its residual is 12–32× too small; H2's staircase is not on the wire. A design round
then produced two survivors: **C**, a notch on the feedback operand (×2.7 damping, ×1.41 ring, but
worst-case transient authority 0.928 against the operator's 0.95 floor) and **S′**, a legal Kd schedule
whose deliverable effect is ×1.22 and which cannot be read from one drive. Shown that table, the
operator chose ***"Neither — revert to V282 and stop here."*** **No V290 image, rwd or build script
exists.** The largest transferable finding of the session is not about this car's plant at all: **a
filter's PLACEMENT decides its authority cost and nothing else** — forward and feedback placement of the
same filter are algebraically identical in poles, ζ, Ms, margins and the 7 Hz gate to machine precision,
and differ only in transient authority (pkR 0.78 → 0.98). **V289's own design scored the feedback row and
the build shipped the loop-output one, with no blocker ever recorded.** The ×0.91 authority price V289
paid was a price for the topology, not for the damping.

## 1. How the session ran

The session was **restarted mid-flight by the operator's PC rebooting**, which killed every agent of the
first wave; files on disk survived, running processes did not. The second wave was briefed to check what
already existed and resume from it rather than re-run expensive stages, and to verify any half-written
file reproduces before building on it. `design290d` and `modenat2` both did exactly that.

| agent | surface | outcome |
|---|---|---|
| `qlive62` | extraction + build identity for r62/r63 | both routes verified **V289 from the wire** (b5 duty 0.500 engaged, b7 signature on SCA = 0 > 3 s post-disengage); caches delivered with `DONE` markers, no missing or truncated segments |
| `census62` | V282-yardstick census on r62/r63, re-derived against r39 / r5e_v288 / r3a / r3c | reproduction exact on the prior builds; V289 presence 2.1–2.2 % — **flagged in its own output as a gate artefact, not a result** |
| `census63` | the census write-up (`GRIND1-CENSUS-V289-R62-R63-2026-09-09.md`) | completed the markdown for the expensive stages that had already finished on disk before the restart |
| `marks62` | the two operator bookmarks + six unmarked loudest episodes, like-for-like vs V288/V282 | 15–17 Hz dominant line, not quieter, decaying-burst-in-trains shape, trigger class unchanged; an independent pooled-PSD crux check confirmed the band-power flip |
| `hyptable` | **H1** (torque-table resolution) | **FALSE** — assist-map LERP and index quantiser mirrored from the disassembly; openpilot's command table read from the operator's own fork; wire quantisation-residual vs tap comparison on r39 / r5e_v288 |
| `h1fig`, `h1fig2` | figure data for H1 + two corrections | index LSB corrected **16.19 → 16.126** (live taper arm 255, not the superseded 254); residual re-derived cleaner (still 12–32× too small); a new sign-asymmetry note on the quantiser (cosmetic, too small and too static to tone) |
| `advphys` | adversarial pass on the FIRST V290 design | **REFUTED it.** The added post-lag term class is closed on the surviving plant either sign: minus drives the 16.4 Hz pole to ζ −0.082; plus removes it but the crossover reappears at 26.9 Hz ζ +0.006, because (1−N)/8 bypasses the 5 Hz output lag and re-injects exactly the 20 Hz content the notch removed |
| `modenat`, `modenat2` | mode-nature re-census with the V289 routes (`modenat2` resumed `modenat` after the restart) | 🛑 **the correction that reframed the whole session** — the 12–26 Hz band holds **two lines separable on DEMAND, not speed**; the plant-mode verdict **survives and is stronger** (Kp-pinning confirmed model-free at matched load; the clamp explanation for it **falsified**); the notch **removed** the 20 Hz object rather than moving it; no single LTI plant carries both facts (best joint χ² 25.8) |
| `design290`, `design290d` | V290 candidate ranking; `design290d` re-ran the plant family from scratch after the restart | reproduced `_scratch/design290b_family.json` **character-for-character** (304 fits, 121 linear-stable, 87 burst-consistent) and re-derived both measured pole anchors by an independent method before building on them; returned a **null** — no candidate improves damping while holding the authority floor |
| its tracer (`design290`'s subagent) | RAM census, post-lag hook `0x2A1B0`, register liveness | **`r26` is REWRITTEN with LERP scratch at `0x29F76` on the main path** — corrects an implicit gap in an earlier trace; a V290 cave wanting filtered feedback must read `gp-0x3d30`, not `r26`. 72-byte free RAM run `gp-0x6D74..gp-0x6D2D` certified; 868 bytes free flash after V289's cave |
| `advnull` | adversarial pass **on the null itself** | 🛑 **overturned it.** The 92-row table contained **no feedback-path row**, and `pkR` — the one gate that killed every row — is a function of the forward path alone. Same filter, feedback placement: identical poles to 0.000e+00, `gate73` identical to six decimals, `pkR` 0.66 → 0.93. 41 of 735 grid combinations pass all three gates in that placement. What the null got *right* and advnull did **not** overturn: nothing reaches worst-case ζ ≥ 0.08 |
| `fbhook` | the feedback-operand hook: site, headroom, RAM, flash, and the historical question | hook `0x29D72` characterised (`r26`, zero intervening accesses over 3,514 bytes), then an **addendum moved the hook to `0x28F4C`** (the rate operand `x`, bounded ±12000) at advnull's argument — and found `0x28F4C`'s decisive advantage: it sits **below** the engagement guard, so the three skip jumps that bypass `0x29D72` do not bypass it ⇒ **runs every tick, no sentinel seeding needed**. **Q6: no blocker was ever recorded against the feedback placement** |
| `reconcile` | the one decision table; reconciling advnull vs design290d | **the two rankings were never in conflict** — they answer different questions and both answers are correct. Applied the operator's ×1.00 steady-state requirement and knocked 32 of 35 apparent wins over; design290d's hardest claim (PM_worst ≥ 40° does not exist in this space) **survives in both placements, 0 rows** |
| `reqaxis` | the Kp/Kd schedule X axis | named the axis in physical units and placed its knots on the wire: **16.125736 wire counts per LSB**; record layout read **from the instructions**, not inferred from the byte pattern (the naive split also fits and gives a *different, wrong* answer); Kd record `0xE511C` = X 0/11/22/32, Y 128×4, **never edited on a flown build** |
| `scalecheck` | independent verification of `reqaxis`'s scale | reproduced the axis scale; its VERIFICATION section is the second method behind the 16.125736 figure |
| `paramod` | the parametric-modulation hazard for a scheduled gain | **row S is safe** — the modulation it can produce is 15–50× too slow and 50–500× too shallow, and the *measured* `Kd(t)` trace through the byte-exact clamped mirror never pumped (9 of 9). 🛑 And the methodological finding: **a Floquet analysis of the UNCLAMPED electronics is not a sufficient parametric-safety argument for this loop** (linear ~2 % vs the clamped mirror's 0.42×) |
| `powerS` | is row S readable from one short drive? | **NO — and the estimator, not the control, is why.** The within-drive contrast is unbiased but **2.6× too imprecise**, and the two operator-facing channels are confounded **in the flattering direction**: low-demand rings are already 41 % quieter (×0.585) and half as long (×0.500) on the base builds. Also killed "cal-only, no cave" as an advantage — row S needs a cave for its own readability |
| `instr290` | V290 live telemetry design | bit table `b5 = sign(n)` · `b7 = \|n\| ≥ 16` · `b3 = \|d2\| > \|d\|`, b4/b6/b0–2 held as the "must not move" cross-build control. **Three rungs that looked obvious were measured and discarded** before cutting rather than after |
| `basepick` | which base, at the delivered dose | 🛑 **the schedule class is capped at ×2.1 at infinite dose**, because half of grinding seconds sit above the knot; **moving the knot X is dominated everywhere** by deepening Y; only S′ (Y0 = 112) is legal, at ×1.22. Stated the decision that had to go to the operator plainly, and stated its own §10 "what I did not verify" |
| `memories2`, `memfix` | memory files + index repair | two new memories written and the index pointers corrected |
| `pageqa2`, `pagefix`, `artifact1` | close-out page QA and the artifact | `PAGEQA-V290-CLOSEOUT-2026-09-09.md`; page regenerated from `analysis-2020accord/studies/closeout/gen_v290_closeout_page.py` |
| `collat1` | first collaterals pass | the first version of this handoff, the first V289 decision box, the V289 lineage entry, two memories |
| `closeout` (this agent) | second collaterals pass | rewrote the decision box around the operator's decision and the corrected V289 reading; the V290 lineage entry; the lever-index staleness block; `docs/review/V282-CUMULATIVE-NONSTOCK-DELTA-2026-09-09.md`; completed this handoff |

## 2. What changed our mind, and in what order

1. **The first reading of the drive was "the notch failed and the line moved." That was wrong, and the
   demand-gated re-census corrected it within the session.** The 12–26 Hz band holds two lines — a
   low-demand road/plant line at 12.4–13.8 Hz that is identical on every build, and the high-demand
   grinding mode. Any pooled median that ignores the demand gate drags to a spurious ~14.8 Hz. Once
   gated, the picture inverts: the notch **removed** the 20 Hz object (band empty, 0/1414) and a
   *different* pole took over. **The plant-mode verdict survives; what broke is the one-plant-one-pole
   model.**
2. **The V282-yardstick census's "fewer episodes" reading was nearly taken at face value.** Its gate
   (18–22 Hz ≥ 40 raw) is blind to a relocated line; without the independent, gate-free pooled-PSD read,
   V289 would have looked like a large win. `census62` flagged it in its own output.
3. **H1's original residual used the superseded taper cliff-arm (254) rather than the live arm (255).**
   Caught by a second figure-data agent re-deriving the same numbers independently. The correction
   (16.19 → 16.126 counts/LSB) strengthens the falsification.
4. **A tracer corrected its own predecessor's implicit assumption about `r26`** — it is not the filtered
   feedback at the candidate hook on the main engaged path. Caught by tracing *past* the point the
   earlier trace stopped, not by re-deriving from scratch.
5. **The first V290 design memo's own postscript overturned its own ranking** after the drive reads
   landed mid-session; `advphys` then refuted the whole added-post-lag-term class independently.
6. **The second design round returned a null — and `advnull` overturned that too.** The null was a
   statement about **one topology**. Every filter it scored sat on the loop output, in the command path
   as well as the loop, and the single gate that killed all of them (`pkR`) reads the forward path alone.
7. **`reconcile` then showed the two rankings were never in conflict**, and that applying the operator's
   ×1.00 steady-state requirement knocks over 32 of the 35 apparent feedback-placement wins.
8. **`basepick` and `powerS` together closed the schedule class** — capped at ×1.22 under the operator's
   own gate, read through a contrast whose error bar is 2.6× the effect.
9. **The operator closed the session**: shown C (relax the worst-case authority floor) versus S′ (keep
   every constraint, accept ×1.22), he chose **neither**.

## 3. Process lessons

- 🛑 **A machine restart is not a checkpoint.** Every first-wave agent died; every file survived. The
  second wave's standing instruction — *check what exists, resume from it, and verify a half-written file
  reproduces before building on it* — is what let `design290d` reproduce the 304-fit family
  character-for-character instead of re-running an 85 s stage on trust. Write that instruction into any
  brief issued after an interruption.
- 🛑 **An agent wrote a memory from a report that was still being written.** The census `.md` was in
  progress while the first collaterals pass quoted it; the `.txt` output was citable and the `.md` was
  not. **Cite the artefact that exists, and re-check it at close-out.** (`memfix` repaired the index.)
- 🛑🛑 **A design that tabulates two placements and ships the other one is a defect the build's own
  assertions cannot catch.** V289's design carried both rows on the same axes, preferred the sum node on
  one physics argument, left the feedback hook **explicitly open** — and the build's pre-registration was
  then written against the *feedback* row's authority number while the build shipped the *sum* row. The
  adversarial pass caught it only after the fact (`ADV-V289-B` §B3). ⇒ **when a design scores two
  variants, the build must name which row it is, and the pre-registration must be re-read against that
  row.**
- **An adversarial pass whose job is to break a NULL is as valuable as one aimed at a build.** `advnull`
  overturned a "nothing works" verdict by attacking its *search space*, not its arithmetic. The null had
  been correct about everything it actually scored.
- **The reason the physics argument that lost the feedback placement no longer had force was an
  experiment we had already flown**: V288 rev 2 put a filter on the reference side and the grinding did
  not move. Paying ×0.92 of authority to scrub a setpoint kick that has been measured not to matter is
  the wrong trade — and it is the trade V289 made.

## 4. On disk

- **On the car:** V289 rev 1 — image sha256 `f0c10c29752d2b9bc4ec510800cd4de58166ebbb87f05613b5ee8e7af339a3ed`,
  rwd `20fa175721eb9712cd9aada27c6ecc84e43108fcdd0c21d387b80db4a105625c`.
- **The operator's chosen revert target:**
  `../accord-firmwares/flashing-2020accord/rwd/39990-TVA,A160-V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP-0x13000-0x100000.rwd`
  **sha256 `618365154e3ffdbb073c00a60173508291f0a18340d6a4f7d39cdd4b2a5b7e22`** (verified from the file at
  close-out); plain image `0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe`.
  **Exactly one V282 `.rwd` on disk.** Full cumulative non-stock delta:
  `docs/review/V282-CUMULATIVE-NONSTOCK-DELTA-2026-09-09.md` (+ its reader
  `analysis-2020accord/studies/closeout/v282_cumulative_delta_from_images.py`).
- **Drive reads:** `rlog-tools/studies/grind/V289-QLIVE-R62-R63-2026-09-09.md`,
  `V289-MARKS-R62-R63-2026-09-09.md`, `GRIND1-CENSUS-V289-R62-R63-2026-09-09.md`,
  `MODE-NATURE-V289-RECENSUS-2026-09-09.md`.
- **H1 / H2:** `docs/review/H1-TORQUE-TABLE-RESOLUTION-2026-09-09.md`,
  `docs/review/H1-FIGURES-README-2026-09-09.md`, figure data
  `analysis-2020accord/_scratch/out/h1_figdata_2026-09-09.json`.
- **V290 design and adjudication:** `docs/specs/design/DESIGN-V290-2026-09-09.md` (the FIRST, **refuted**
  memo — do not build from it), `DESIGN-V290B-2026-09-09.md`, `DESIGN-V290-TELEMETRY-2026-09-09.md`;
  `docs/review/ADV-V290-PHYSICS-2026-09-09.md`, `ADV-V290-NULL-2026-09-09.md`,
  `V290-DECISION-TABLE-2026-09-09.md`, `V290-BASE-DECISION-2026-09-09.md` (**read its ADDENDUM — it
  supersedes the body's ranking**), `V290-ROWS-READABILITY-2026-09-09.md`,
  `V290-PARAMETRIC-HAZARD-2026-09-09.md`, `PAGEQA-V290-CLOSEOUT-2026-09-09.md`.
- **Traces:** `docs/traces/TRACE-2026-09-09-v290-feedback-operand-hook.md` (+ its ADDENDUM moving the
  hook to `0x28F4C`), `TRACE-2026-09-09-v290-postlag-hook-rate-operand-ram.md`,
  `TRACE-2026-09-09-kp-kd-schedule-axis.md`; verifier
  `analysis-2020accord/verify/v290_q1q3_rateop_and_ram_census.py`, `v290_fbhook_*.py`.
- 🛑 **NO V290 image, rwd or build script exists.** Nothing was built, flashed, or sent on the wire this
  session.
- **Golden model:** untouched. Contract re-verified at close-out — **90 symbols**, `_self_check()` +
  `_demo()` stdout 2,512 B, sha256 `740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d`.

## 5. Decoder note

V289's decoder is unchanged and was reconfirmed on r62/r63: `0x14A` byte 4 **b5 = sign(S − y)** (the
notched-out component; duty ≈ 0.50 engaged = the cave is alive), **b7 = |S − y| ≥ |y|**, b4/b6 = V282's
r24 comparators, b3 as V282, b0–2 stock Honda. 🛑 **Score b5/b7 ENGAGED-ONLY** — the cave, and Honda's
rate PID it sits in, keep executing 1–3 s after SCA falls with a decaying nonzero state (Honda's
disengage fade), so b7 reads ~1 on raw `SCA = 0` frames. **After a revert to V282, b5/b7 mean something
different** — attribute the build from the tap, not from the label.

## 6. Open items

1. **The operator flashes V282 when he chooses to.** Nothing else is pending on the car.
2. **Option C is ready to cut if he later relaxes the worst-case transient-authority floor** (0.928 vs
   0.95). Hook `0x28F4C`, cave `0xC4C90`, notch 21.5 Hz Q1.5 (`b0 = b2 = 15680`, `b1 = a1 = −31074`,
   `a2 = 14976`, ±12000 clamp), fb pole `0xC63E8/EA` → 796/3522. **Its revert signature is
   pre-registered** — and 🛑 **if C's 16.5 Hz pole is audible, the entire loop-shaping class is closed
   (both placements, both bases, and the Kd schedule) and V291 must come from outside it.**
3. **Retroactively re-census r39 and r5e_v288 demand-gated at 13–18 Hz** so V282 / V288 / V289 read on
   one instrument. The 18–22 Hz gate is blind to V289 and its numbers are not comparable.
4. **Fork-side echo lever, standing** (`docs/research/STARPILOT-FORK-COMMAND-PIPELINE-2026-09-07.md`):
   openpilot's unfiltered 100 Hz angle measurement is what makes the command's own 20 Hz line an echo of
   the wheel ring.
5. **The golden model still lacks the LKAS rate-PID stage** — untouched this session, deliberately. What
   would have to land: the E-former (`E = 32·setpoint − feedback`, two-sample sum DC 30.89 through the
   `0xC63E8/EA` lag pole), P and D (`P = E·Kp>>8` with the `0xE5378` schedule at 16.126 wire counts/LSB;
   D on the *error*, clamp `0xC61B6`), the sum clamp `0xC61BE`, the per-variant gain LERPs, and the
   5.05 Hz output lag `0xC63EC/EE` — plus a hook point where a cave filter can be inserted at **either**
   placement, since placement is now known to be the decision-bearing axis. **Do not add it piecemeal**;
   re-run the 90-symbol + sha256 contract on any edit.
6. **`docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md` is stale past V108** and now carries a block at its top
   naming the five post-V108 addresses (`0xC63E8/EA`, `0x2A174`, `0x28F4C`, `0xE511C`, `0xC4C90`) that a
   grep by address would otherwise miss. **Absence from that index is not evidence of untested.**
7. **`0xC61C0/C2/C4` still has NO lineage entry** despite 12 live readers across 249 images — a tracer
   task owed before the next authority change. (`docs/review/V282-CUMULATIVE-NONSTOCK-DELTA-2026-09-09.md`
   row 19.)
8. **The quantiser's sign-asymmetry note** (index 1 reached at command +1 one direction, −17 the other —
   a fixed offset, not a dither) is new and cosmetic; worth drawing on a future signal-path diagram, not
   a lever.
