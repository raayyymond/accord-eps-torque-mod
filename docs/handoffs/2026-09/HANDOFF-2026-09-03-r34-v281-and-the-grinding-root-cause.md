# HANDOFF 2026-09-03 — r34 read, V281 rev 3, the tune, and the grinding root cause

Continues `HANDOFF-2026-09-02-two-loops.md` (§8 = the tune back-calculation). Operator directive in force: "Keep iterating to fix grinding, LKAS authority and
peak command oscillation." "openpilot" = StarPilot branch Dom. Seventeen subagents this session; every decision-bearing crux re-checked by the orchestrator
from the images, the wire or the source (noted per item). Nothing flashed by this session; two builds cut (V281 rev 2 → superseded → rev 3).

## 1. r34 (V280 rev 2, new tune) — `LANECHANGE-r34-NEWTUNE-2026-09-03.md`, `HIGHANGLE-r34-2026-09-03.md`
Tune decoded from `reference/toggle-backup_20260902.json`: ForceAutoTune OFF, LAF 2.11, friction 0.03, SR 16.1 explicit, KP 0.6, delay 0.2 (controller-used values
verified on the wire: identity −(p+i+d+f)/output = 2.110). **PASS on the pre-registered lane-change prediction:** 0 of 2 hands-light highway lane changes rang
(6 of 6 before); 4–8 Hz rate power ÷ 8–11 at matched speed/cmd; openpilot's block gain 0.36× (predicted 0.37). Cost: lane-keeping error RMS 2×; centring unchanged.
Strong-turn ripple unchanged (10 F7 at 7.3 Hz, wheel at reference, P linear) → EPS-internal. Prereg (i)–(viii) for V280: 7 of 8 pass, (v) borderline, (vii)
0.89 < 1.39. Flag: straight-road MID 2–4 Hz "excess" 1.41 because the command's 5–9 Hz content fell 6–14× (friction chatter gone) — watch. Oversteer: road-speed
regime +24 % (FF over-delivery at LAF 2.11 no longer masked by the 0.212 relay; entry not spiked, plateau 0.5–3 s), hairpin regime +16 % (ratio-shaped, output railed
at ±1.0 via the low-speed factor); highway curves fine. No FF-scale toggle exists for the Accord. Operator later set SteerRatio 12.5 (model over-reads lat accel 29 %
→ real ≈ 0.78 of request; outer gain +29 %, still below V112's).

## 2. V281 — the rate-PID Kp table
- Sizing `studies/v280/KPFLAT-SIZING-2026-09-03.md`: the 7 Hz ripple = inner-loop crossover limit cycle at Kp 512–696 (GM 0.5–0.86×), K_crit ≈ 425 two ways.
- Rev 1 (knot cap, lowered the highway band) → rev 2 (flat 341 from idx 24; A/B/C PASS; adversary B: the stall window moves to idx 80–111) → **rev 3 (operator:
  "completely flat at index 0's value" = 248 everywhere; 218 bytes; A and C PASS, B pending)**. Image 98a7a514…, rwd a3e330ff…, firmware repo 886355b.
  Prereg `PREREG-V281-READ.md`, page https://claude.ai/code/artifact/51c14843-7f5c-4792-ba8e-4eaf2e641054. Adversary A settled the record layout (n, X[5] with
  X[0]=0 implicit, Y[5], pad) and proved one live reader. StarPilot tune: leave for the first drive.

## 3. Grinding — root cause found, fix handed off
- `rlog-tools/studies/grind/CREEP-20HZ-LOOP-ID-2026-09-03.md`: the 20.3–21.0 Hz line (hands OFF, engaged-only) is the LKAS rate loop's own crossover resonance
  (17–21 Hz, PM 35–60°, Ms 2–2.9; D ~55 %), f pinned, presence follows Kp(idx) (13/42/83 % at idx 0/1–20/20–60), not the command, not cogging. Less D → ~8 Hz peak.
- `docs/research/GRINDING-ROOT-CAUSE-LEDGER-2026-09-03.md`: 98 hypotheses; the band scales with the ×6 gain; only motor-side rate/accel feedback ever reduced it;
  V280 carries every such lever at its ceiling; pump falsified on car; 26 contradictions listed.
- `docs/traces/TRACE-2026-09-03-engaged-only-loops-at-20hz.md`: since V104 the byte 0x3AA96 = fb repoints the base-assist rate-lane gate to STEER_CONTROL_ACTIVE
  → r24 flat 5244 (×10 stock) on the 4-tap derivative of the bar torque when engaged; r26 cut to 512. Verified from every image by the orchestrator.
- `TWIST-TAPER-LOOP-2026-09-03.md`: r24 ≈ 770 counts at 7 Hz, −18° from the rate (pump) — DISPUTED by the on-car 18–22 Hz history (gate ON reduced the band).
  The setpoint taper is inert under openpilot (arm field = 0); the live post-PID fade 0xCBBC4 explains the ~0.5 mirror slope; do not flatten it.
- Two Opus-5 max-thinking handoffs spawned: `HANDOFF-2026-09-03-GRINDING-for-deep-analysis.md`, `HANDOFF-2026-09-03-7HZ-STRONG-TURN-for-deep-analysis.md`.

## 4. Corrections of record (apply to memories with the operator's approval)
`accord-lever-b-is-unreachable` (true of c5 images only) · `accord-override-taper-is-a-cliff-not-a-taper` (unselected arm) · `reference-accord-second-driver-torque-gate-cbae4-cbbc4`
("inert" → live) · `accord-starpilot-torque-controller-the-033-multiplier-was-inert` ("raw LAF clipped to 2.196" → nothing was applied; torqued never valid) ·
"V106 reverted at V108" (bytes say the ×3 row is on the car) · `reference_accord_gp6b26_two_paths…` (α2 "virgin" → V109 lever, 14 on the car) · the highangle tables'
"cliff duty 2–11 %" (computed on the unselected knee).

## 5. Next
1. Fly V281 rev 3 (after adversary B) with the toggle backup recorded; read by `PREREG-V281-READ.md`; re-run `backcalc_extract.py`/`backcalc_laf_friction.py` on the route.
2. Act on the two deep-analysis reports: the loop shape for 20 Hz, the r24 verdict, the next build with its prereg.
3. StarPilot: if road-speed oversteer persists at SR 12.5, LAF 2.53; the true LAF 5–10 needs params.toml.
