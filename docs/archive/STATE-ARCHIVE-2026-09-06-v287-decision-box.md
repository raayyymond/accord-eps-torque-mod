# ARCHIVED decision box (2026-09-06, V287 rev 2 era) — superseded 2026-09-07 by the V288 box in STATE.md. A record, not an instruction.

## ✈ THE DECISION, IN ONE PLACE  — updated 2026-09-06 (**grind #1 on V282: the CAL-ONLY SURFACE IS EXHAUSTED**; 🛑 the record's headline lever, the output-lag pole to 15 Hz, is **DO-NOT-FLASH** (GM 0.72×); the one new class, the **D-term clamp 0xC61B6**, FAILED the adversarial pass at 2560 and is built at **7680 as V287 rev 2 — a partial mitigant (~5 %), NOT a cure**; the real fix is a **setpoint-interpolation CODE edit**, identified, not built)

**ON THE CAR: V282**, unchanged (r39/r3a/r3c, confirmed on the wire — see the archived 2026-09-05 box in `docs/archive/STATE-ARCHIVE-2026-09-05-r3a-r3c-decision-box.md` for the openpilot-side SR-map / LAF results, which stand).

**BUILT, UNFLASHED: V287 rev 2 = V282 + ONE halfword, `0xC61B6` 10240 → 7680** (the LKAS rate PID's D-term clamp; D = 16·ΔE rails at |ΔE| = 480 instead of 640). Image `_v287r2_…DCLAMP.7680…_plain_image.bin` sha256 **e75ae7eb5c5bcba564f445a7223260b25c4b476b9df1d8c9ad8e171f79498f15**; rwd `…V287R2…rwd` sha256 **71648c0ebdc8ca63d7f974d32a735c0f3ef607d7b67c71efc883ceb79ba852a5**. Diff vs V282: 5 bytes (0xC61B7 + the cal-page CRC). Adversarial pass on rev 1 (2560): A arithmetic PASS · C build audit PASS · D interlocks PASS · **B units/strata FAIL** → re-sized to 7680, where B's own admissibility test holds in every stratum. Prereg: `rlog-tools/studies/grind/PREREG-V287-LOOP-SHAPE.md` §C5. 🛑 **V287 rev 1 (2560) is SUPERSEDED-DO-NOT-FLASH** (renamed on disk).

### 🛑🛑 THE RESULT — every cal-only grind #1 lever on V282, priced on one model anchored to the measured loop
Grind #1 = the 18–22 Hz rate-loop crossover resonance, lightly damped, rung by input. **On V282 it opens 130 times over r39+r3a+r3c** (48 burst / 51 sustained / 31 ride-along), at demand index, wheel rate and |angle| **3–6× the all-engaged median**; only 7 % of onsets are in strict steady creep [EVIDENCE, `GRIND1-CENSUS-V282-2026-09-06.md`]. The operator's "opens on large turn transients" is right in direction; the sharpest bursts open at somewhat lower demand than the sustained stretches. **Onsets within 0.5 s of a top-1 % command step (|Δcmd| ≥ 122 raw/frame or Δidx ≥ 9/frame) are enriched 2.80× [2.10, 3.57] over engaged baseline** (burst 2.1×, sustained 3.8×, ride-along 2.4×) — but **69 % of onsets have no such step nearby**, so the command kick is an enrichment, not a necessity: a second, structural reason the D clamp can only be partial.

| lever (cell) | Re@7 Hz | S@20 | GM | ring L_tot | verdict |
|---|---|---|---|---|---|
| as-built V282 | −0.23 | 1.61 | 1.77× | 0.980 [0.971–0.983] | — |
| **out-lag pole 15 Hz** 0xC63EC/EE 932/1458 | +1.84 | 0.63 | **0.72×** | — | 🛑 **DO-NOT-FLASH** (also ≥10 Hz: fires Honda's oscillation detector in 15/19 windows) |
| out-lag pole 8 Hz 974/792 | +0.69 | 1.21 | 1.19× | 0.822 | WATERBED: 18–22 ↓ ×0.76, 26–33 Hz ↑ ×2.3 into the blind band; a plant discriminator, not a cure |
| fb pole 0xC63E8/EA | — | — | — | — | gain lever only (rectified, multiplicative; no phase effect measured) — struck |
| Kd 64–96 | — | 1.67–1.71 | ↑ | — | drags the sensitivity peak from 26 Hz INTO 20.7 Hz — closed |
| Kp 160 | — | 1.38 | 1.91× | 0.912 | costs 35 % inner DC tracking; SteerKP headroom only 1.125× — unrecoverable |
| **0xC6446 → 2048** | **+0.62** | 1.61 | 1.77× | **0.479** | the largest FREE lever for the **7.3 Hz stutter**; halves 20 Hz damping (1.52 → 0.68) — a stutter build, not a grind build |
| **D clamp 0xC61B6 → 2560** | — | as-built hands-off | — | **1.038 (loaded)** | 🛑 FAILED adversary B: in hands-on bar>700 / loaded ang>60 / fast wheel >25 deg/s (20–28 % of engaged time) it clips the FEEDBACK derivative, Kd_eff 95 < the ~118 floor, ring re-armed |
| **D clamp 0xC61B6 → 7680** | −0.29 | as-built | 1.77× | **0.983 (= gate)** | admissible in every stratum; onset envelope ×0.947 (r39) / ×0.930 (r3c); steady control ×1.000; **needs ≥ 1,150 command-step onsets ≈ 38 min engaged to resolve at 2 SE** |

**The joint (pole, Kd) grid with today's margins held is EMPTY; the (Kd, 0xC6446, Kp) grid moves S@20 only through Kp.** V282's sensitivity peak already sits at **26.3 Hz** — every linear lever that helps 18–22 Hz feeds 26–33 Hz, where the 0x18F streams carry energy but not frequency (`TASK5`). [BELIEF for absolute margins — model (a), pessimistic ≥1.7× vs the measured GM 1.32× at Kp 470; EVIDENCE for every phase and for the rankings' direction]

### ⭐ THE MECHANISM BEHIND THE D CLAMP, and why the staircase cannot be softened by calibration
The openpilot command is a **100 Hz staircase**; the PID runs at 1 kHz on E = 32·sp − fb, so **32·Δsp is an impulse train** into D. At today's 10240, **93–100 % of the ticks on which D binds are setpoint-dominated and land on a command step** [EVIDENCE, 1 kHz mirror]. The clamp is already an excitation limiter. **But the setpoint path has NO memory anywhere from the 0xE4 byte to the error** — CAN decode store (0x526F2) → symmetric clamp → Q16 LERP scale → ›22 → clamp 240 (0xC64F0) → assist map → `shl 5` (an immediate) → `sub`. Structural test: a slew needs a RAM cell both written and read; the positive control finds the lag filter's state (gp-0x3d3c); the setpoint region has none [EVIDENCE, tracer addenda 5–6]. ⇒ **Softening the kick without touching feedback D is a CODE edit** (interpolate sp across the 10 ticks: ~10× less kick, zero DC cost) — the identified target, needs a new RAM state cell (GATE 1) and the cave discipline.

### 🛑 NEW: HONDA'S OSCILLATION DETECTOR IS LIVE (FUN_000428d4)
Ungated, every tick: watches **gp-0x6c2c = a 39 Hz-filtered derivative of motor ROTOR angle** (cal 0xC40DC = **14 on V282, stock 22**), counts alternate crossings past ±12800 (40 % of its 32000 full scale), resets after 50 ticks (so only >10 Hz counts), and after 15/20 reversals ramps **×0.600 into the governor's Q15 motor-demand scale** (slot 2, MIN-fold, by register — the RAM mirror gp-0x6994 has no readers). **Not observed firing on any V282 episode** (no ×0.6 step in motion per unit T; the duration histogram is confounded by the detector floor). No cave comparator can read it (no RAM reference). The golden model's `motor_torque_governor` treats the scale as exogenous — **a gap to close**.

### CORRECTIONS OF RECORD (2026-09-06)
1. **The D clamp is `0xC61B6`; `0xC61BA` is the integrator anti-windup** (both 10240; the build scripts always had it right; assert on the ADDRESS).
2. **The 102 deadband `0xC61B8` is gated OFF when engaged** (block at 0x2A1BC skipped when gp-0x6806 ≠ 0) → the "P-only deadband = 0xC61B8" attribution of r39's stall runs is **WITHDRAWN**.
3. The fb filter has **no ›5** (DC 30.89); the lag filter's DC formula does not apply to it. 963/986 is +2 % DC; 842/2814 is 31.1 Hz.
4. 0xC63EC/EE and 0xC61B6 each have extra readers inside a **duplicate, unreachable PID copy at 0x2A508** (entered only via a `dispose …, lp` return). GATE 1 passes for both. New scan trap: `prepare` collides with jr/jarl on the Format-V opcode test → odd "targets" are false positives.
5. The deep analysis's LKAS-lane phase at 20 Hz (−69°) was **modelled**; measured −86° (τ 3.9 ms) → the servo lane is near-pure quadrature at 20 Hz, **essentially all 20 Hz damping is r24's** (sum +2.06 → +1.52).
6. D and the PID sum (gp-0x6b36/34) are **write-only** — the clamp's binding is observable only through T; with Ki 0, on rising steps where P rails and sign(D)=sign(P) the sum clamp masks the edit exactly (Q1 is conditioned on it).
7. 0x14A bit-6 duty rises mechanically under any D-clamp dose (T's kick shrinks) — **score it differentially; V282's 0.22/0.10 thresholds do not transfer**.

### ✈ NEXT — in order
1. **Decide on V287 rev 2.** Adversary B on rev 2: PASS WITH CONDITIONS — admissible in every stratum on its own machinery, authority clean, BUT the ring gate |L_tot| = 0.983 has zero margin and the multiplier it turns on is measured at 0.990 (shape) vs 0.970–0.983 (B), i.e. not to gate precision. ⇒ the ring is judged by **Q10** (6–9 / 18–22 Hz at |ang|>60, FAIL > ×1.9/×2.3, margins ×1.75/×1.78) and the operator's stutter report, Q5 is REPORTED; **Q2 is read PAIRED against the 10240-mirror on the same drive** (a two-drive comparison never resolves: 2·SE floor 7.8 % vs a 5.3 % effect); Q6 > ×1.9 route-wide. Read Q1 liveness first. Paired Q2 (1.0 s onset windows, predicted ×0.957) has a measured paired SE of 3.2–5.0 %, so it resolves at 2 SE with ~650–810 onset events ≈ 22–27 min engaged ≈ 1.5 normal routes; the mirror under-predicts the tap's 18–22 Hz content by 18–28 % (cancels in the ratio if stable — recorded).
2. **Spec the setpoint-interpolation cave** (the real grind #1 fix): GATE 1 for a new state cell, hook site near 0x29D76, instrument = 427 tap vs mirror on step ticks, dose = interpolation depth.
3. **0xC6446 → 2048 as a labelled STUTTER build** if the 7.3 Hz ring is the next symptom to treat.
4. **Creep/onset exposure drive on V282** (hands-off 1–3 m/s, several minutes) — sizes every endpoint's n and SE.
5. Golden model: add the governor's 7-slot MIN-fold and the oscillation detector.
6. Open: r3c t 232 s burst (P rail active 73 %, a different mechanism); the 80/120 Hz alias (audio); Task 5's rate on a second method.

