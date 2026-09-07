# HANDOFF 2026-09-06 — grind #1 on V282: the cal-only surface is exhausted; V287 rev 2 (D clamp 7680) is a partial mitigant, not a cure

**Read `docs/STATE.md`'s decision box first.** This is the narrative: what the operator asked, what the twelve agents found, which of their numbers died, and what the one build that survived the adversarial pass actually is.

## 0. The one-paragraph version
The operator: *"V282 is the latest and greatest … the only remaining big issue is the rare grinding (grind #1). Seems to generally open on large turn transients … fix this once and for all with V282 as the base."* Grind #1 is the LKAS rate loop's 18–22 Hz crossover resonance. On V282 (r39, r3a, r3c) it opens 130 times, at demand index, wheel rate and angle 3–6× the all-engaged median, only 7 % in strict steady creep — the operator's reading is right in direction. **Every calibration-only lever on the V282 base was priced on one model anchored to the measured loop, and none removes the mode without a trade**: the never-touched output-lag pole is a waterbed (the sensitivity peak already sits at ~26 Hz); the fb pole is gain-only; Kd is closed; Kp costs authority the outer loop cannot repay; the r24 gain is a stutter lever; and the D-term clamp — the one genuinely new class, an excitation limiter on the 100 Hz command staircase — **failed the adversarial pass at 2560** because in loaded, hands-on and fast-wheel driving (20–28 % of engaged time) it becomes a 0.6× Kd cut that re-arms the 7.3 Hz ring. The largest ring-safe dose, **7680, is built as V287 rev 2**: ~5 % on the grind-onset envelope, resolvable only over ~38 minutes of ordinary engaged driving. The staircase itself reaches the D term unfiltered because **no cell with memory exists anywhere on the setpoint path from the CAN byte to the error** — the real fix is a setpoint-interpolation code edit, identified and not built.

## 1. How the session was run
Orchestrator + subagents, all briefed as subagents reporting to `main`, GhidraMCP only, EVIDENCE/BELIEF on every claim, every decision-bearing crux re-verified by the orchestrator from the image or the wire (the 5-byte diff, the clamp cell and reader bytes, the doc corrections).

| agent | model | surface | outcome |
|---|---|---|---|
| `census` | Sonnet | grind #1 episode census, r39/r3a/r3c + comparators; detector-firing test | 130 episodes; onsets at 3–6× median demand/rate/angle; detector not seen firing |
| `shape` | Opus | loop shape on the measured r24 arm; the ONE build + prereg; Appendices A–C | lag pole = waterbed, 15 Hz DO-NOT-FLASH; D clamp found, then re-sized after adversary B; 7680 |
| `tracer` | Opus | pole-cell census, filter form, tick, downstream monitors, GATE 1, D clamp cell, setpoint path | Honda oscillation detector found LIVE; D clamp is 0xC61B6; GATE 1 passes; setpoint path has no state |
| `builder` | Opus | V287 rev 1 (2560), then rev 2 (7680) | 5-byte diff, address-asserted, one flashable rwd |
| `advA` … `advD` | Opus ×3, Sonnet | adversarial pass on the built image | A PASS, C PASS, D PASS, **B FAIL at 2560** |
| `lerps` | Sonnet | every LERP and cell for the artifact page, from three images | V282↔V287 differ in exactly one cell |

## 2. What changed my mind, in order
1. **I expected the output-lag pole to be the build.** The record ranked it first. The shape agent ran the Nyquist crossing the record never ran: V282's sensitivity peak is already at 26.3 Hz, and 932/1457 takes the gain margin to 0.72×. Every raise is a waterbed into the blind band.
2. **The D clamp looked like the clean lever** — memoryless, amplitude-selective, no gain-margin change, and its own negative control on the same drive. It was, in every hands-off stratum at every speed. Adversary B stratified the same mirror over hands-on, loaded and fast-wheel driving and found the feedback derivative binding there. The re-sizing (corrected for a double-counted Kd scaling that would have condemned the flown build) put the ring above unity at 2560 and exactly on its gate at 7680.
3. **I hoped a setpoint-side cal existed** to spread the 100 Hz staircase. The tracer's structural test (a slew needs a RAM cell both written and read; the positive control finds the lag filter's; the setpoint region has none) is a clean null from the CAN byte forward.
4. **Honda's oscillation detector** was unknown to the kit and is live: a ×0.6 multiplicative cut on motor demand after ~0.4 s of >10 Hz reversals on the rotor-rate derivative. It is not firing on today's grind; it is a ceiling on any lever that adds 20–40 Hz persistence.

## 3. Corrections of record produced
- The D clamp is **0xC61B6**; 0xC61BA is the integrator anti-windup (both 10240). The build scripts always had it right; this session's brief did not.
- The 0xC61B8 = 102 deadband is **gated off when engaged**; the "P-only deadband = 0xC61B8" attribution of r39's stall runs is **withdrawn**.
- The LKAS PID's feedback filter has **no ›5**: DC 30.89 (the "two-sample sum"); the record's DC formula applies to the output lag only. 963/986 is not DC-neutral (+2 %); 842/2814 is 31.1 Hz, not 33.
- The output-lag cells have a second reader inside a **duplicate, unreachable copy** of the PID at 0x2A508 (entered only via a `dispose …, lp` return); the D clamp likewise has 3 of 7 readers there. GATE 1 passes for both.
- The deep analysis's 20 Hz LKAS-lane phase (−69°) was a **modelled** phase on a measured magnitude; the corrected measurement (−86° after the 3.9 ms stream correction) makes the servo lane near-pure quadrature at 20 Hz — essentially all the 20 Hz damping is r24's.
- 0xC40DC = 14 on V282 is **not stock** (22); the "67 Hz" corner quoted for gp-0x6c2c is stock's.
- D and the PID sum are write-only cells: the clamp's binding is observable only through T.
- The kit's "LKAS command lane is a 1–5 Hz low-pass" is **not firmware** on this path.

## 4. Firmware state
- **V287 rev 1 = V282 + 0xC61B6 → 2560: SUPERSEDED-DO-NOT-FLASH** (renamed on disk in `accord-firmwares`). Failed adversary B.
- **V287 rev 2 = V282 + 0xC61B6 → 7680: built, unflashed, partial mitigant.** See STATE.md for hashes and the pre-registration (`rlog-tools/studies/grind/PREREG-V287-LOOP-SHAPE.md` §C5).
- DO-NOT-FLASH added: output-lag pole at ≥ 10 Hz (932/1457, 962/982, 950/1172).

## 5. Next
1. **Decide whether V287 rev 2 is worth a flash cycle.** It is ring-neutral at its gate and needs ≥ 1,150 command-step onsets (~38 min engaged, ordinary driving) to resolve a ×0.93–0.95 effect. If that exposure is not available, do not fly it.
2. **The real target: a setpoint-interpolation code edit** — first-order hold or linear interpolation of the assist-map output across the 10 PID ticks between 100 Hz command frames. Cuts the D kick ~10×, zero DC cost, zero feedback-D cost. Needs a new RAM state cell (GATE 1), a cave (the kit's only bricking class), and its own instrument (the 427 tap vs the mirror on step ticks, already adequate). Not built.
3. **0xC6446 → 2048 as a stutter build** — the largest free lever found for the 7.3 Hz ring (0.98 → 0.48, no margin or authority cost) at the price of half the 20 Hz damping. Label it as such if cut.
4. **Creep/onset exposure drive on V282** — still the cheapest measurement; it also sizes the onset endpoint's n and SE directly.
5. Golden model: `motor_torque_governor` must gain the 7-slot MIN-fold and Honda's detector as slot 2.
6. Open: the r3c t 232 s burst with the P rail active 73 % (a different mechanism from r35's); the 80/120 Hz alias question (audio); Task 5's true rate on a second method.

## 6. Artifacts
`docs/research/GRIND1-LOOP-SHAPE-V287-2026-09-06.md` (+ Appendices A–C) · `rlog-tools/studies/grind/PREREG-V287-LOOP-SHAPE.md` · `rlog-tools/studies/grind/GRIND1-CENSUS-V282-2026-09-06.md` · `docs/traces/TRACE-2026-09-06-lag-and-fb-pole-census-v282.md` (5 addenda) · `docs/review/ADV-V287-{A,B,C,D}-*.md` · `analysis-2020accord/builds/v108_plus/build_v287_tva.py` · scripts under `rlog-tools/studies/grind/` (`grind1_*.py`, `adv_v287_b_units_strata.py`) · `analysis-2020accord/_scratch/out/v287_lerps.json` · four memories under `memory/accord/{mechanism,firmware}/` and `memory/feedback/process/` · artifact page https://claude.ai/code/artifact/c27031d7-3166-4e31-83b8-2a5e9d2c8b73.
