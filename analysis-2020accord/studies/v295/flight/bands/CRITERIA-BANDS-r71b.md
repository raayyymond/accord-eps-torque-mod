# Bands read of route `75604b0a432fdc89_00000071--a7b8ba5d9d` (r71b_v294): criteria written BEFORE any band was computed

Subagent "bands", 2026-09-30 06:58 PDT. This file was written before any scorer ran on r71b; only caches were being
extracted when it was written. Each threshold comes from the record, which is cited. Where the record has no threshold,
the row is marked REPORT and says so. **The operator scores symptoms. These are bands.**

## What was pre-registered for V294 (STATE box 2026-09-20, HANDOFF-2026-09-20 / -09-23, PART6 V294)
- P1: **1.6–3 Hz wheel-rate energy, and hard-turn behaviour vs r75 (rev 4) / r76 (rev 5)**, at matched speed and
  demand. Predicted DOWN. This row FIRES (the prediction fails) if the V294 value is ≥ the reference value in the
  matched stratum.
  - Instruments are the record's own: v293r5_observer_read O4 (hard turns v < 10: the 1.6–3 Hz share of 0.3–8 Hz
    wheel-rate energy, and rate sign reversals), v293r3_read S4 (hard-turn bursts/min, 0.5–5 Hz rate rms), and the
    absolute 1.6–3 Hz rate rms on matched strata.
  - ⚠ Caveat carried from the redo audit (09-23): exact poles give ζ× 0.89 at 5 m/s and 1.00 at 8 m/s, so below
    about 8 m/s the design itself predicted slightly LESS damping. A v < 10 rise is therefore not a surprise against
    the corrected physics. It is a FAIL only against the original "predicted down".
- P2: **any NEW line in 5–30 Hz = the revert signature.** FIRES if the excess-dB peak in any of the scorer's
  search bands (5–9.5, 10–17, 17–24, 22–30 Hz, engaged hands-off strata) exceeds the maximum over the V293 references
  (r70, r71-old, r72, r73, r75, r76 where cached) by ≥ 3 dB, at a frequency outside those references' ±1 Hz.
  The scorer's own REVERT gates also fire P2:
  - F7 ≥ 2 per 100 s
  - tap rip/L ≥ 0.25
  - absolute 6–8.5 Hz tap ripple ≥ 1.5 × r6c
  - 13–17 Hz ≥ 1.5 × V282
  - the 1–4 Hz outer-loop row (V276 signature)
- P3: **the 18–22 Hz ring** (drive-controlled engaged ÷ disengaged, and presence). V294's 20 Hz controller gain is
  −26.7 dB vs V282, so V293-like values are expected (r70 presence 1.1 %, amp ×0.43). The pre-registered clause is
  present-window amplitude ≤ 0.40 × V282. SURPRISE if presence exceeds the V293 references' maximum ×2, or
  engaged ÷ disengaged exceeds the V293 range.
- P4: **the 2.34 Hz limit cycle at ≥ 19 m/s** (route 71-old's signature, the expected symptom if the trim were NOT
  live). Instrument: v293r2_read S7, on hard curves v > 15, |Ddes| > 1.0, runs ≥ 5 s, peak 0.3–3 Hz in rate/cmd/err.
  It also runs restricted to v ≥ 19. FIRES if the rate peak falls in 2.0–2.7 Hz with prominence ≥ +10 dB (r71-old:
  +22.5 dB at 2.34 Hz). If there are no qualifying runs, the result is "NOT TESTABLE", which is not a pass.
- P5: **1–4 Hz prominence** in command AND angle (the V276 signature). Pre-registered (HOWTO §7.5): < 3 dB
  everywhere. FIRES if ≥ 3 dB in any populated band.
- P6: **ratchet dwells** (th 0.25 deg/s): PASS if ≤ 3 × r6c in every band with ≥ 60 s. The ratchet REVERT (toggle
  class) fires if dwells exceed r70_v293 in ≥ 2 exposed bands. p90 dwell and snap are REPORT.
- P7: **F7** (6–9 Hz strong-turn ripple, per 100 s). REVERT at ≥ 2. Tap rip/L REVERT at ≥ 0.25.
- P8: **0x14A cave duties.** r24 is unchanged (2048) V293 → V294, so b4 = sign(r24) is the NEGATIVE CONTROL.
  SURPRISE if b4 differs from the V293 references' range by > 0.05. The remaining bits are REPORT.

## The outer loop (no V294-specific pre-registration exists, so every row here is REPORT against the targets the record carries)
- Tracking gain (HOWTO §7.3): target 0.95–1.05 per band with ≥ 60 s (bracketed by r6c).
- |H|(0.2 Hz) ≥ 0.9 (rev-4 success sentence).
- Turn-hold at > 20 m/s ≤ 1.04.
- Integrator share < 0.20 (a target; no route passes).
- Planner-error rms by band < 0.3 / 0.3–1 / 1–3 Hz: REPORT vs r75/r76.
- des → act |H| at 2 Hz: REPORT vs r75 (2.28 at 10–20 m/s, coherence 0.99).
- **J** (0.15–2.4 Hz, ≥ 15 m/s, hands-off runs ≥ 30 s): V282 0.442, rev 6.4 1.3512. No V294 pre-registration. The
  exposure gate is at least 5 windows of 10.24 s (the smallest route in f2_metric.json has 17); below that J is not
  reported as a number.

## What a FAIL here licenses
Only "band X moved by Y against reference Z". None of it licenses "fixed", and none of it is a symptom verdict. The
operator's complaints for this drive, from OPERATOR-REPORT-r71b.md, were recorded by the orchestrator and not
verified by me:
- "No grinding or stuttering!"
- "Jerky on hard turns at medium speed"
- "Loose on straights and turns at low speed."
- "Loose/understeer at highway turns."
