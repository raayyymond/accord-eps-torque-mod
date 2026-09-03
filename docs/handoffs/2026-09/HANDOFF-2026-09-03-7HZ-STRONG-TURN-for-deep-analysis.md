# HANDOFF — THE 6–8 Hz STRONG-TURN OSCILLATION, for a deep-analysis agent (Opus 5, maximum thinking) — 2026-09-03

**Read this whole file, then the files it points to, before forming a view.** You are a SUBAGENT of the orchestrator `main`; report via
`SendMessage` (to: "main"). Never send CAN, never flash, never build an image; you may write studies and scripts. Python = `python` (never
`python3`); rlog readers run from `rlog-tools/`. Disassembly only via GhidraMCP (gp = 0xFEDF8000, tp = 0xBF000; decompile first). EVIDENCE (method) or
BELIEF on every claim. Kit rules: `CLAUDE.md`, `.claude/skills/firmware-iteration/SKILL.md`, `.claude/skills/firmware-decompile/SKILL.md`. A sibling agent
holds the GRINDING handoff (`HANDOFF-2026-09-03-GRINDING-for-deep-analysis.md`, same folder) — the two problems share the loop; read it, do not duplicate it,
and coordinate through `main` only.

## 0. The operator's words
Route r32/r33 (V280 rev 2): "while doing strong turns, there is still some slight oscillation of the wheel while its turning. its like a small signal riding on
top of a large one." Route r34: "biggest remaining thing is an small oscillation on top of large steering commands, perhaps we need to flatten the Kp curve to
its lower demand value? its like the feel oscillates at around 6-8 Hz very slightly while its turning strongly." His hypothesis: "could it be feedback from the
driver torque sensor temporarily limiting our torque demand setpoint input? Or driver torque sensor and the driver-side steering PID loop acting on the feedback?"
His decision: "I want Kp on the LKAS PID completely flat, flattened to demand index 0's value" → V281 rev 3, built.

## 1. Measured (EVIDENCE)
`rlog-tools/studies/osc-highangle/HIGHANGLE-r32-r33-2026-09-02.md`, `HIGHANGLE-r34-2026-09-03.md` (§2, §9 episode table), scripts `strongturn_r32_r33.py`,
`strongturn_r34.py`; caches `analysis-2020accord/_scratch/cache/v280/r3{2,3,4}.npz` (t1ab,b0,b1,t18,rate,tq,sca,t14,ang,te4,cmd,req,tcs,vego).
- 18 episodes at |angle| ≥ 30°, 2–9 m/s, 6.5–7.8 Hz, wheel MOVING at 0.6–1.2× the reference (not stalled: the r31 stalled class is gone on V280), demand idx
  median 109 (IQR 86–140; 4 of 18 above 200), P linear 60–80 % of ticks, D rail ≤ 0.06, fb clamp ≤ 0.02, no output cap, saturation 0.000, override cliff idle.
- Rate ripple 17–29 deg/s; tap T ripple/level 0.34–1.37 on |T| 500–1150; the torsion bar rings at 7 Hz with 1043–2223 raw amplitude around zero — column twist,
  hands light (bar↔T coherence 0.99, phase −152°: the wheel's inertial reaction to T; bar lags the wheel rate by 94°).
- The 0xE4 command carries only 3–20 % of the T ripple (65 counts median in-episode); the outer-loop tune change (friction 0.212 → 0.03, LAF 2.11) did not move
  the episodes (count 8.1 → 4.3 → 6.8 per 100 s, amplitude held) → EPS-internal.
- The chain mirror (FUN_00028ea6 on the measured rate, V280 map) reproduces the tap: P alone corr 0.78–0.93; with the LIVE post-PID driver-torque multiplier
  0xCBBC4 (fades from 512 raw, floor 0.30 at 2048; the arm selector gp-0x6803 is 0xE4 byte2 bits 3:2, which openpilot sends as 0 — the "cliff at 2240" arm is
  never selected) corr 0.955, slope 0.86–0.90. Decomposition of T's 7 Hz: P 0.53, D 0.26 (in quadrature), multiplier 0.10 (`TWIST-TAPER-LOOP-2026-09-03.md`).
- A 14 s hands-on stall on r34 (t 250–264, P railed 0.77–1.00) rippled 0.02–0.03: deep P saturation does not ripple.

## 2. The loop (EVIDENCE for gains, BELIEF for margins)
Plant G = rate/T identified from the tap in the loaded high-angle stratum (v ≤ 10, |angle| ≥ 30°): |L_in| 9.1/7.2/2.5/1.3 at 2/4/6/8 Hz, phase −86/−103/−135/−163°,
PM ~15° near 9 Hz at the base Kp; three parametric fits agree ±5 % (`analysis-2020accord/studies/v280/KPFLAT-SIZING-2026-09-03.md`, `kpflat_sizing.py`;
plant `LOWCMD-LOOPGAIN-V112-V278-V280-2026-09-02.md` A2–A3, `plant_id_v278r3_tap.py`). At Kp 512–696 (idx 68–208) GM 0.50–0.86×, PM −5…−25°: linearly unstable,
the P clamp regulates the cycle (describing function: K_eff = N·Kp, N 0.60–0.83, median 439 on the idx ≥ 106 episodes; 225 on the one idx-26 episode).
K_crit ≈ 425 by both methods. Flat 341: GM 1.36×, PM 11°. **Flat 248 (V281 rev 3): GM 2.0×, PM 27°, Ms 2.9 at 7.6 Hz.** Kd 0/64/192/384, the output-lag pole
and a single-sample fb do NOT stabilise the base Kp (Kd 0 is worse). Companion: fb filter pole 0xC63E8/EA 16.5 → 33 Hz (DC held) adds ~10° at 7–9 Hz (reader
census not done). Caveat (adversary B, `docs/review/ADV281R2-B-INTERLOCKS-2026-09-03.md`): the open-loop replay of the real episode frames shows ripple/level
RISING at lower Kp (the level falls faster than the ripple); only the closed-loop linear model says the cycle dies; the P-linear fraction → 0.86–1.0 says the clamp
stops regulating. The drive decides.
Firmware: E = 32·sp − fb; P = E·Kp>>8 clamp ±15360; D = 16·ΔE clamp ±10240; sum clamp 15360; × 0xCBBC4 multiplier; lag 992/507; ×5346>>15; clamp ±3072 → T = gp-0x6b38.
Kp(idx) slot 7 base: X 0,68,112,136,208 / Y 248,512,645,696,696; Kd 128 flat; fb = raw rate → two-sample sum (DC 30.89) → clamp 46080.

## 3. THE OPEN DISPUTE: is the engaged-only r24 twist-derivative lane the pump?
See the grinding handoff §4 for the byte-level facts (0x3AA96 = fb → r24 flat gain 5244 on the 4-tap derivative of the bar torque when engaged; r26 cut to 512).
twistloop (`TWIST-TAPER-LOOP-2026-09-03.md` §3b–3d): r24 = ~767 aggregator counts at 7 Hz (447–1028 across the 18 episodes; 72 at stock gain), **−18° from the
wheel rate = pumping**, 1.47× the LKAS lane's own ripple, ~3.5× the servo's damping component (T at +115° re rate, damping fraction 0.65). Measured-phase-only
derivation: bar lags rate 94°, derivative +90°, 4-tap −5° → −9°; decompile sign chain (gp-0x6752 = −1, frame builder sends −(gp-0x4f60·125>>7), 4-tap = +0.5·Δ)
agrees. The on-car history says the opposite for the 18–22 Hz band (gate ON reduced it), but those contrasts moved r26 too and the c5 arm runs Honda's LERP
(2305–3072), not 512. The tap-identified plant G already CONTAINS r24 closed, so every "servo at crossover" margin above is of the loop with this lane inside.
Only gp-0x6b38 is on the wire; r24 and the aggregator sum are not.

## 4. Builds on the table
- **V281 rev 3** (built 2026-09-03, cal-only, 218 bytes, three-attacker pass A/C done, B pending at hand-off time): Kp flat at Y[0] on all 28 records (live 248).
  Image `_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.…_plain_image.bin` sha256 98a7a514…; pre-registration `rlog-tools/studies/osc-highangle/PREREG-V281-READ.md`
  (F7 episodes ≤ 2 per 100 s, tap ripple/level ≤ 0.25, full-demand rate ≥ 105 deg/s; FAIL sentence: ≥ 4/100 s with ripple/level ≥ 0.4 → not the P-gain cycle,
  no further Kp cut licensed). Cost: hands-light full-demand rate ≈ −8 %; stalled push −29…−48 % at idx 26–80, full stalled push from idx ≈ 120; the r31 stall
  stutter may return at idx 60–120; highway inner Kp −3…−16 % (outer loop untouched).
- Candidate, NOT built: 0xC6446 5244 → 512 (cal-only, one u16, one live reader at 0x3ac08): r24 → 0.14× the T ripple, r26 and the servo untouched. FAIL sentence
  in `TWIST-TAPER-LOOP-2026-09-03.md` §3d. History both ways: V62 rate-lane ×2 was the one measured grinding fix; V255/V256 ×2 on the 6× base undriveable; V246 ×1.5
  never flew.
- Candidate, NOT built: an inert tap of r24 (or the aggregator sum) — the kit's doctrine prefers it to any dose, but the 427 tap window carries T and has no spare field.

## 5. Constraints
Authority (the ×6 map/gain) must stay; the 20 Hz creep grind is the same loop's higher-frequency mode and is D-dominated (less D moves it to ~8 Hz with a larger peak —
`rlog-tools/studies/grind/CREEP-20HZ-LOOP-ID-2026-09-03.md`); the highway outer loop is now at 0.35–0.45× its old gain (StarPilot 2.11 / 0.03 / SteerRatio 12.5) and
must not be pushed back toward the 7–8 Hz lane-change ring; cal-only edits preferred; every build interpretable from one short strong-turn drive.

## 6. Your deliverable
1. Settle §3 with the wire: at the 7 Hz episodes, using only measured phases (bar, rate, T, cmd) and the decompiled sign chain, is r24 pumping or damping; how much
   of the motor's 7 Hz content is r24 vs the servo P vs D vs the multiplier; reconcile with the on-car 18–22 Hz history (does the phase flip across the column
   resonance?). If it cannot be settled from the wire, specify the inert tap (cell, bits, comparator law) that settles it in one drive.
2. Predict V281 rev 3's drive on the loaded high-angle plant WITH r24 modelled explicitly (not folded into G): does Kp 248 kill the cycle if r24 is pumping at 767
   counts? What does 0xC6446 → 512 do alone, and combined with Kp 248 / 341? Give margins and the predicted ripple/level for each.
3. Recommend the ONE next build after V281 rev 3's read (or instead of it, if you can show V281 rev 3 cannot work), with its pre-registration in the kit's pattern.
4. List what you could not close and the measurement that would.
Write `docs/research/7HZ-STRONG-TURN-DEEP-ANALYSIS-2026-09-03.md` (+ scripts under `rlog-tools/studies/osc-highangle/`) and SendMessage `main` the headline.
Think as long as you need; verify the crux of every decision-bearing number yourself.
