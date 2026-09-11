# HANDOFF 2026-09-10 — The excitation census: the grinding is an EXCITED RESONANCE, there is nothing to de-excite, and V288's null was never a null

**Read `docs/STATE.md`'s decision box first.** This is the narrative of a root-cause session that cut no
build, sent nothing on any bus, and overturned the verdict the last three builds were designed against.

## 0. One paragraph

The operator reopened his colleagues' hypothesis — *"what excites the ring is high openpilot slew into
quantizer steps"* — and said he was not convinced the prior work had disposed of it. He was right that it
had not. Six agents on disjoint surfaces then bounded or killed **every** excitation candidate, including
two nobody had tested, and the session ended with a different answer than either the operator or the
orchestrator expected: **the grinding is (C) an excited resonance, rung by ordinary broadband noise, with
no identifiable source to remove.** The decisive measurement is that the line's **phase coherence time
equals its ring-down time** (6.5–17.4 cycles, implied ζ matching the free-decay ζ on every build) —
*there is no persistent phase, therefore no persistent source.* Along the way the session found a **real,
large, previously-unknown 20 Hz forcing comb** on the command (modeld's staircase, never smoothed because
`clip_curvature` **never binds**), proved it is **not** the grinding, and discovered that **V288 rev 2 —
the build whose null closed the "reference-side class" — never applied a filter in the ring's band at
all.** The single most operator-legible result: the grinding is **engagement-gated**, ×33 to ×72 rarer
with lateral disengaged *at matched or higher load*, across 17 routes including stock.

## 1. How the session ran

Orchestrated; eight subagents, all analysis-only. Nothing was built, flashed or sent.

| agent | surface | outcome |
|---|---|---|
| `fwpath` | EPS intersample ZOH; then the `0x14A` angle producer | Confirmed the command is genuinely ZOH'd for ~10 ticks. **Then withdrew its own headline**: V288's cave is amplitude-dependent, not LTI — the finding that voided the kit's standing verdict. Confirmed the **EPS builds `0x14A`** (catching its own DBC false alarm first) and that the broadcast angle is **floor-truncated 5 bits, undithered**. Closed the lockstep safety gate: bit-exact dual-copy, nothing recomputed |
| `slewburst` | burst-onset triggers | **NO triggering event class.** 514 onsets, 5 routes: cap binds ≤ 8.2 %, best of any class ≤ 13.3 %, Δ² spikes 0 % [0, 2.0]. Road/IMU **null** in 30 tests. Corrected the orchestrator's Q≈17 impulse premise. **Retracted its own pre/post asymmetry result** as confounded by construction. Threshold sweep drove cap-bind RR *below* 1 |
| `modelrate` | modeld cadence vs the ring | Found the **comb** (Δ²cmd at 41–69× background, camera-locked 10–90× its null) and the **`clip_curvature` 0.000 binding fraction**. **Its first phase detector failed its own positive control**; diagnosed why and replaced it with the square law. **Retracted a V288 falsification after I had relayed it**, on a sample-size confound it found itself |
| `echoloop` | outer-loop identification | **\|L\| = 0.026–0.165**, bound ≤ 0.189. Named the trap it avoided (naive estimator *manufactures* \|L\| ≈ 1). Found a **second feedback path inside the feedforward**. **The engagement-gating experiment at real power (17 routes).** Corrected its own sign convention: critical point **L = +1**, metric \|1 − L\| |
| `cyclekind` | forced vs limit cycle vs resonance | **The verdict.** Coherence-time-equals-ring-down-time, plus Rice K = 0.00, no preferred amplitude, no plateau, no hysteresis, no harmonics. Independently re-derived V288's transparency. **Corrected the orchestrator's "f0 pinned" claim.** Camera-lock on the ring channel — ⚠ **later superseded: its `R2 − floor` estimator is biased low; the debiased figure is ≈0.50** |
| `combsize` | comb vs echo sizing (replaced `slewburst`) | **Designed a better experiment than briefed**: ablate the whole ring band from the command and measure what the mirror stops delivering — bounding both mechanisms at once. Command leg **20.2 %** (r39) / **4.1 %** (r63). Partial coherence 0.388 → **0.022** (matched control rises to 0.598). **Quarantined its own failed control**, then — on the last pass — **adjudicated the three-way lock-fraction dispute against ground truth and WITHDREW two of its own headline results** |
| `oplpf` | the colleagues' fix, as a diagnostic | Their LPF is **~1 Hz, not 20 Hz**, aimed at a low-speed near-centre *"hunting and escalating sway"*. **Three commit attributions in the 09-07 trace corrected.** Found `measurement` = steering angle and `k_d = 0`. **Flagged the standing no-fork-changes instruction rather than working around it** — which is what prompted the operator to amend it |

## 2. What changed our mind, and in what order

1. **The operator's challenge was correct on the merits.** H1 was falsified on *amplitude* and H2 on
   *first differences*; neither touched a **sustained forcing** whose signature lives in the **second**
   difference. Nobody had computed it. `modeld`, `modelV2` and `MODEL_FREQ` appeared in **zero** grind
   study, review or design doc in the repo.
2. **The orchestrator proposed the comb, over-claimed it, and then had to retract twice.** First on a
   frequency gap that turned out to be within the CI; then on a "zero-lag ⇒ common driver" argument built
   on a wrapped phase; then on relaying `modelrate`'s V288 phase result before its error bars were
   checked. Each retraction is in `STATE.md`.
3. 🛑 **`fwpath` re-derived a claim it had already reported and found V288's cave was amplitude-dependent.**
   That voided *"the reference-side class is exhausted"* — the premise behind V289, the whole V290 design
   round, and the "the lever is in-loop damping" framing. **The caveat had been written in the kit's own
   adversarial pass three days before V288 flew and was not applied when the drive was read.**
4. **`slewburst` closed the trigger question** and corrected the orchestrator's impulse arithmetic —
   which had been the argument used to reopen H1 in the first place.
5. **`echoloop` and `combsize` converged on the command-side budget by different methods** — an exact
   algebraic identity and a whole-band ablation through the byte-exact mirror — at ~20 %.
6. **`cyclekind`'s coherence-time test settled the mechanism** — a rung mode, not forced and not a limit
   cycle. Its camera-lock *price* for the comb (3–8 %) was later superseded; the mechanism verdict was not.
7. 🛑 **`combsize` then adjudicated the three-way lock-fraction dispute and it changed the price.** It
   reproduced all three agents' published numbers on one loader, decomposed the gap (**estimator ×4.09 ·
   windowing ×3.02 · total-vs-excess ×0.98 — the orchestrator's total-vs-excess hypothesis was WRONG**),
   and settled the estimator **against a synthetic signal with a known locked fraction**: `R2 − maxfloor`
   is biased low by 0.12–0.22, `R2_deb` recovers truth to ±0.04, because **noise adds in POWER and
   subtracting a floor in AMPLITUDE over-subtracts.** ⇒ **The lock fraction is ≈0.50 and perfect removal
   of the comb is worth ≈29 % amplitude (~3 dB), not 3–8 %.** All three agents reconcile once each
   estimator's bias is restored; **nobody's data was wrong.**
8. 🛑 **And it withdrew two of its own results, which the orchestrator had already banked and relayed** —
   *"the comb does not grow when the car grinds"* (its quiet strata were 5–7× longer, and the bias scales
   with N_eff, so quiet was penalised less; debiased the comb **grows**, r39's CI excluding 1 in the
   *opposite* direction) and *"bar is 34 % camera-locked while the angle is 2 %, so a torque comb barely
   moves the column's inertia"* (**the angle is ~40 % locked**; the column-inertia explanation goes with
   it). ⇒ **The crux-3 synthesis loses one of six premises; five survive.**
9. ⚠ **What keeps the 29 % from being a recommendation:** **V289 is already the flown version of "remove
   the coherent 20 Hz forcing" and the symptom got WORSE** — its relocated ring carries **0.000** camera
   lock and is **1.71×** r39's on **0.30–0.45×** the command drive. It is **confounded** (the notch also
   spent 30° of margin at 15–17 Hz), so not decisive — but it is the only configuration ever flown with no
   coherent forcing, and it went the wrong way. The 29 % also assumes the locked energy **vanishes**
   rather than being replaced by the broadband excitation that remains at unchanged loop gain.

## 3. Process lessons

- 🛑🛑 **Before reading any null, convert the SYMPTOM into the LEVER'S OWN UNITS and check the lever was
  actually active there.** *An experiment that did not move the independent variable cannot test the
  dependent one.* Corollary to *a null from the wrong image is not a null*.
- 🛑 **Every one of the four false premises was caught by an agent re-deriving a claim it had ALREADY
  REPORTED — never by review, never by an adversarial pass aimed at it afterwards.** Five self-corrections
  in one session. **Brief agents to re-derive their own load-bearing claim before reporting, and to
  report the failed controls, not only the successful ones.**
- **Demand the positive control pass before any null is quoted.** Two agents said outright that without
  it their null would just be a bug. `modelrate`'s first detector *did* fail its own control.
- ⚠ **A low coherence/lock statistic on a SHORT stratum is a NON-DETECTION, not a zero** (R2's floor
  scales 1/√N_eff). And **a detuned-frequency null does not decorrelate unless |Δf|·T ≫ 1** — at 3 s
  windows the "null" sat at 84 % of signal.
- **Agents saturate.** Three (`slewburst`, `oplpf`, `modelrate`) began re-sending their prior report
  instead of ingesting corrections. `slewburst` was stopped and replaced by `combsize`, which inherited
  its scripts and produced a better experiment. **Replace a looping agent rather than re-prompting it.**
- **A sister agent's number is not evidence.** `combsize` and `cyclekind` disagreed on one lock fraction
  (0.357 vs 0.035–0.145); `combsize` diagnosed its own as upper-biased and deferred. Flagged, not smoothed.

## 4. On disk

- **On the car:** V289 rev 1 — image `f0c10c29…`, rwd `20fa1757…`. **Operator's chosen revert target:
  V282**, rwd sha256 `618365154e3ffdbb073c00a60173508291f0a18340d6a4f7d39cdd4b2a5b7e22`. **Unchanged.**
- **Reports:** `rlog-tools/studies/grind/{FORCED-VS-LIMIT-CYCLE, COMB-VS-ECHO-SIZING, OUTER-LOOP-ID,
  BURST-ONSET-TRIGGERS, MODELD-CADENCE-VS-RING}-2026-09-10.md` ·
  `docs/traces/TRACE-2026-09-10-command-intersample-zoh.md` (four addenda) ·
  `docs/research/OPENPILOT-EXCITATION-SOURCES-2026-09-10.md`.
- **Scripts:** `rlog-tools/studies/grind/` — `fvlc_*.py` (band-aware detector, camera lock, V288 gain),
  `comb_*.py`, `outerloop_*.py`, `burst_*.py`, `modeld_*.py`. Verifier
  `analysis-2020accord/verify/verify_2026_09_10_zoh_census.py`.
- **Memories:** `accord/mechanism/accord-grinding-is-an-excited-resonance-no-excitation-to-remove.md` ·
  `accord/signals/accord-the-20hz-forcing-comb-is-real-and-half-the-rings-energy-is-locked-to-it.md` ·
  `accord/builds/accord-v288-null-is-void-filter-was-transparent-at-the-ring.md` ·
  `accord/instruments/accord-episodes-of-hardcodes-the-18-22hz-gate.md` ·
  `feedback/measurement/feedback-convert-the-symptom-into-the-levers-own-units-before-reading-a-null.md` ·
  `feedback/builds/feedback-no-openpilot-side-modifications.md` (**AMENDED**).
- **Golden model:** untouched. Contract re-verified — **90 symbols**, `_self_check()` + `_demo()` stdout
  2,512 B sha256 `740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d`.
- 🛑 **NO image, rwd or build script was created.** Nothing was flashed or sent on any bus.
- ⚠ `docs/STATE.md` is **206 KB** — under the 256 KB cap but above the ~150 KB target. **Archive the
  superseded blockquote blocks at the next close-out.**

## 5. The operator's standing instruction, amended

**2026-09-10, verbatim:** *"I am fine with openpilot-side changes. That memory was only relevant to that
specific section. But in general, I think the EPS should act faithfully on the openpilot commands. Only
for the grinding issue… I'm willing to accept openpilot changes if the model's connection / steering
authority is not limited (like by a LPF for example)."*
⇒ Fork-side fixes are **in scope for grinding only**, gated on **authority and lag, not location**. A
command LPF is **forbidden by name**. Everywhere else the EPS acts faithfully on openpilot's commands.

## 6. Open items

1. ⭐ **The IMU is the top open item and it is an INSTRUMENT, not a lever.** Every proxy used to date is a
   CAN channel from inside the steering system, so none can say whether the residual excitation is
   **road, rack or motor**. Cached for one route. **Extract corpus-wide before designing anything.**
2. 🛑 **Re-score option C on max Ms over 12–26 Hz before cutting it** — it was designed against the
   single-frequency framing V289 falsified.
3. **The reference-side class is UNTESTED and reopened** — but a reference filter still cannot separate
   (B) from (C), and any retry needs a **fractional accumulator**, not a `>>k` integer IIR.
4. **What the free (non-clock-locked) command content actually is** — `combsize` showed it is *not* an
   angle echo; what it *is* was not established.
5. **The `0x14A` truncation fix**: safe in principle (lockstep passes a consistently-dithered value) but
   **no clean hook and no free flash in that region**, and the confirmed-fault consequence is untraced.
6. **Retroactively re-census every V289 rate number** computed with `episodes_of`'s hard-coded gate.
7. **Amend** `accord-honda-kp-ki-scale-never-acted-kp-is-0600-on-all-60-routes` with the measured
   per-route kp (0.8/0.9/0.6) and live latAccelFactor (2.11/6.00), dated.
8. **`0xC61C0/C2/C4` still has NO lineage entry** despite 12 live readers across 249 images.
