---
name: accord-v292-built-loop-opening-dose-byte-exact-error-feedback-cave-cleared-over-one-dissent
description: "🛑🛑⭐⭐⭐⭐⭐ V292 BUILT 2026-09-13, NOT FLOWN — THE FLIGHT CANDIDATE: V291's loop-opening dose (fb lag pole 16.5 → 9.94 Hz DC-held, r24 arm 5244 → 4725, 0x14A b3 = sign(fb state)) plus a 52-byte cave at 0xC4C00 (hook 0x28F8E) that carries error-feedback remainders through the filter's two `sar` floors, so the integer filter's mean equals the linear one at every amplitude; 69 bytes vs V282. Adversarial A/C/D PASS; B FAIL on the sp = 3 steady-state clause only (vs the LINEAR V282 chain — a surface no integer build can sit on; vs byte-exact V282 ×1.000); CLEARED by the orchestrator under the broken-check rule, dissent recorded. rwd 6d2784b5…, image d1128232…. V291 SUPERSEDED-DO-NOT-FLASH."
metadata:
  node_type: memory
  type: project
---

**What it is.** V282 + V291's three cells (`0xC63E8/EA` 962/958, `0xC6446` 4725, `0xC4BAA` b3 rung) + the
cave: hook `0x28F8E` `mul r16,r7,r0` → `jr 0xC4C00`; 52 bytes / 15 instructions (`mul, mul, ld.hu rem_b,
add, andi 0x3ff, st.h, sar 0xa, ld.hu rem_a, add, andi 0x3ff, st.h, sar 0xa, ld.hu clamp ×2, jr 0x28FA2`);
halfword remainders at `gp-0x6D74`/`gp-0x6D72` (boot 0 via the .data copy loop at 0x1476C); +10 instructions
per 1 ms tick. Design `docs/specs/design/DESIGN-V292-FBLP-CAVE-2026-09-13.md` (+ errata), mirror
`rlog-tools/studies/grind/v292_cave_mirror.py`, script `build_v292_tva.py` (refuses a second write; tag derived
from the integers; renamed V291 `SUPERSEDED-DO-NOT-FLASH-`), prereg + verdicts
`docs/review/ADVERSARIAL-V292-PREREG-2026-09-13.md`, reports `ADV-V292-{A,B,C,D}-2026-09-13.md`.

**Why the cave [EVIDENCE].** Each `sar 0xa` floor in the fb filter leaks half an LSB per tick, the state
integrates it and the two-sample sum doubles it: a constant **−32 count feedback bias** on the 9.94 Hz pole
(V282's own −16…−20) = one permanent phantom setpoint count; plus the input quantum 0.66 → 1.07 raw counts.
V291 read ×1.34–1.80 of V282's rate at sp = 3 counts. With `t & 0x3FF` carried as the residue (exact for
either sign), the mean gain is exactly b/1024 and the decay a/1024 at every x (2,982 amplitudes, error zero),
the DF gain at 20.3 Hz is 0.9994–1.0009 with ≤ 0.16° phase at A = 1…24 (V282's own: 0.11 / 5°), the
negative absorbing state [−16, −1] is released (s rests at exactly 0), and the linear loop is V291's unchanged.

**The pass [EVIDENCE].** A PASS · C PASS (independent rebuild, 17/17 mutations) · D PASS (remainders have
exactly the cave's accessors + the boot loop; interlocks byte-identical; r7/r9 are LIVE-IN and replicated —
the memo's "writes before reading" wording was wrong for two of four) · **B: every clause PASS except the
byte-exact steady state at sp = ±3 vs the LINEAR V282 chain (×0.78–1.16, 20–21/21 fits)** — the loop has FIVE
floors (P >>8, D >>3, fade >>8, output lag >>10/>>10/>>5, motor >>15) and the cave repairs one; V282 itself
reads ×0.96/×0.72 against its linear chain there. Vs byte-exact V282: ×1.0000 at +3 (median), sign asymmetry
×0.89 (V282 ×1.33, V291 ×1.41), ≤ 2 % at ±33, 0/21 fits outside ±1 % at ±330. B2: *"I would not defend a
do-not-flash on physics here."* **Orchestrator: CLEARED under the kit's rule that a check condemning the flown
build is broken; dissent recorded; the flight is the operator's decision.** Also from B2: the record's r24
fold omitted the motor gain K = 5346/32768 and over-weighted r24 ×6.13 (pessimistic; corrected Ms reduction
×5.2, folded f0 18.4 Hz); the ±102 deadband on y with gp-0x6806 = 0 would zero sp = 3 on every build —
which state is live while engaged is BELIEF (the record's V103/V104 evidence says 1); B5 is fragile in phase
(1.0 at −5.9° vs V282's −31.6°); the loop closes ~6× sooner after engage at near-zero rate.

**The read:** half-peak decay ≈545 → ≈183 ms on hands-off creep; −14° ± 4° at 10 Hz (T vs 0x18F rate);
**b3 DUTY 0.47–0.50 at every amplitude** (V282-pole 0.54–0.70; idle 0.000 with the wheel still = cave live) —
NOT the transition rate (that figure was V291's); b5/b6 the r24 control. **Revert if:** 6–9 Hz strong-turn
ripple; new roughness/line at 10–18 Hz (byte-exact worst-fit sensitivity ×1.3–1.7 of V282's, peak near 13 Hz);
22–30 Hz line; grinding unchanged; darty feel; one-sided pull at rest. `AccordCurvatureLead` OFF.

Related: [[accord-v291-c10-built-fb-pole-10hz-plus-r24-cut-loop-opening-class]] ·
[[accord-with-the-loop-open-there-is-no-18-22hz-object-zeta-open-ge-0-05]] ·
[[feedback-a-check-that-condemns-the-flown-build-is-broken]]

**Replay prediction on the operator's own recorded grinding episodes (byte-exact closed loop, `V292-REPLAY-PREDICTION-2026-09-13.md`):** ring amplitude ×0.55 [0.54, 0.57] of V282's (×0.71 on r6c), ring-down ×0.29–0.36, strong-turn ripple ×1.03/×0.94 (worst fit ×1.10), torque outside the bands ×1.00, 9–18 Hz ×1.09–1.17 (worst ×1.36). A model prediction, not a drive.
