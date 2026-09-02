# HANDOFF 2026-09-02 — V278 rev 3 FLEW; V280 (the knee at 96) BUILT

**Status: V278 rev 3 is ON THE CAR (flown 2026-09-02, route `75604b0a432fdc89_00000031--a680e9b2ac`, 11 segments, 581 s
engaged). V280 BUILT (`47bdfb0d…7411` / rwd `0357a025…84db`), written to `../accord-firmwares`, NOT flashed, three-agent
adversarial pass clean. Chain: ← `HANDOFF-2026-09-02-v278-rev3-the-torque-tap.md`.**

## The operator's report on rev 3, verbatim
"amazing authority in terms of maximum angular velocity and acceleration · no audible grinding, maybe felt a very very
attenuated version of it at some points, not sure · stuttering and oscillations at high angles far from center — this is the
firmware's largest issue · no more constant oscillations like in V276 · it still feels like we are not quite yet at 6x max
angular velocity relative to stock — confirm this first, then address it without introducing the V276 oscillations."
He also said the route "has given me confidence we do not need to pursue a V279 methodology which requires massive StarPilot
side changes."

## What the drive measured (EVIDENCE unless marked)

| question | answer | file |
|---|---|---|
| max rate vs stock | sustained full-demand hands-light rate p50/p90 **42.3 / 56.4 deg/s** vs rev 3's 44.5 reference; V112 (×1 map) 23.9/41.5 → rev 3 = 1.9× the ×1 builds = 32 % of the ×6 target. The REFERENCE limits, not torque: \|T\| p50 at full demand 539 (22 % of the rail), lane braking the wheel on 63 % of full-demand frames | `analysis-2020accord/studies/v280/V280-MAP-DESIGN-2026-09-02.md` |
| 3.9 Hz mode | GONE: MID-stratum band excess 0.76 (V276 4.58, corpus p50 0.82) | `rlog-tools/studies/osc-2to4/V278R3-READ-2026-09-02.md` |
| clamps | saturation duty 0.000, \|T\| max 1704 vs the rail → leave the clamps (pre-registered null confirmed) | same |
| damping statistic | 0.40 on normal frames; the prereg's 0.60 was V276-specific and its own refutation clause fired. The chain sim on rev 3's frames gives 0.399 — tap and model agree; the scalar is regime-dependent (0.33 near centre hands-off, 0.83 above 50 deg/s), not a discriminator | same |
| grinding | off-EPS metric NOT computable (23 s manual, needs ≥ 30 s speed-matched); engaged-only IMU 15–22 Hz shape stat 1.355 vs corpus max 1.280 — a flag, not a score | same |
| the high-angle stutter | a **7.0–7.6 Hz line** in the rate AND in T (coh 1.00), 10 of 13 episodes, all \|angle\| ≥ 30°, 3–9 m/s, cmd railed (idx 237–238), planner flat; absent on stock r97 / V112 r22 at comparable exposure (14–190× less 4–8 Hz rate power). Driver torque there is a 7 Hz RING (1470–1960 raw amplitude, near-zero mean, column twist), not a hand | `rlog-tools/studies/osc-highangle/HIGHANGLE-V278R3-2026-09-02.md` + `highangle_stutter.py` |
| its mechanism | in 7 of 10 episodes the wheel is STALLED by road/lock load at 10–20 deg/s against a 36–45 deg/s reference: E = +7k..+9k, P railed ~50 % of ticks; the ±25 deg/s (±6000 in E) 7 Hz rate ripple crosses P's 5650 linear window every cycle → T 100 % modulated. Counterfactual ×6 top on the same frames: E +25k..+34k, P never desaturates, T ripple/level 0.45 → 0.18 (uniform ×6 0.11). Open-loop. 3 of 10 episodes are the driver spinning ABOVE the reference (52–73 deg/s): fb clamp binds, the lane BRAKES | `rlog-tools/studies/osc-highangle/SERVO-AT-REFERENCE-2026-09-02.md` + `servo_at_reference.py` |

## Two instrument corrections
1. **The 427 tap field is `((b0&3)<<8)|b1`** (the kit's convention, which read V276's selector 35). The DBC-derived window in
   `decode_v278r3_torque_tap.py` ((b0&0x7F)<<3|b1>>5) was WRONG (max 21, sign never set); verified on raw bytes by the
   orchestrator (kit window: max 673, sign duty 0.54, corr(|T|,|cmd|) +0.67). Fixed in the decoder.
2. **Damping compares T to the RAW 0x18F rate**: damping ⇔ sign(E) ≠ sign(fb) ⇔ sign(T) ≠ sign(raw wire). The decoder had
   negated the wire once more. Fixed. Also: on the wire **sign(T) = +sign(cmd)** (80 % of frames, 100 % in steady corners) —
   the V279 docstring's "sign(T) == −sign(cmd)" is not what the wire shows (v = −4·cmd, then T = −lane: two negations).

## V280 — what it is and why
Map ×2 to idx 96 (byte-identical to rev 3, the region where V276 rang: its ringing frames were idx ≤ 58), rising linearly
to ×6 at 240 (f(128) = 26/9, f(160) = 34/9; slot 7 Y = 0,48,84,100,124,200,252,445,627,1032; top knot = V276's in all 28
records); `0xC62E6` = 46080 (V276's value; ratio 1.395 at the ceiling; all three readers `ld.hu`, decoded); tap unchanged.
Reference ceiling 44.5 → 133.6 deg/s. Damping fraction in V276's ringing frames stays 0.863 by construction. Predicted: less
7 Hz chatter at high-angle full demand (P pinned at its rail), rate p50 > 56, steadier ~1.3× harder push; the lane pushes
WITH a driver who spins the wheel above the old reference instead of braking (feel/risk, on the page).
**Pre-registration:** `rlog-tools/studies/osc-highangle/PREREG-V280-READ.md`. Build: `build_v280_tva.py`, 687/687.
Design: `analysis-2020accord/studies/v280/` (profile ranking: every knee ≥ 64 ties rev 3 at 0.863; the gate is blind above
idx 58, so ×6 at the top rests on V276's 73 s, not on the comparator).

## Adversarial pass (three agents, disjoint), all CLEAN
- `adv280a` build script: rebuild reproduces; 438 bytes vs V268 all attributed; own CRC walk 50/50 + 49/49; rwd == image;
  280 knots reproduced by independent round-half-up (denominators only 9 → no half products; floor would differ at 26 X=128
  knots and is caught); 33 mutations, 31 caught, 2 silent-benign (banker's rounding; LIVE_SLOT=6 is the same shape).
- `adv280b` arithmetic: LERP surfaces from all four images (V280 == rev 3 for idx ≤ 96 exactly; == V276 at 240); crossover
  133.6/44.5/22.3; fb clamp readers fully decoded ld.hu (op 0x3F, hw2 odd); P-desaturation margin at a 15 deg/s stall needs a
  96 deg/s ripple on V280 vs 6.7 on rev 3; D one-tick rails 0.71 → 1.06 % of ticks (4.0 % at idx ≥ 128) with a 100 Hz ZOH
  command; no width trap. Correction: a P-only rail delivers 2461 / reads 307 (post-sum 254/256, BELIEF); 2481/310 needs D.
- `adv280c` consumers: 0xC62E6 readers exactly three, all ld.hu; the 0xC9A88 family has two readers (the live LERP at
  0x29CFC and the dead twin at 0x2ABF2); `gp-0x6a32` has ZERO loads; no interlock consumes sp/E/fb; V280 vs V276 differs in
  code only by the tap window and in cal only by Y[1..8]. Untested: the X=128/160 knots and the ×2-low + 46080 pairing.

## Open items (not requested)
- Ghidra MCP was down all session; every census above is raw-scan only (the kit's required second method), not Ghidra+scan.
- `_scratch/cache/r31` (gitignored) was overwritten by the V278 route; a July route shared the tag.
- The engaged-only IMU 15–22 Hz flag on r31 and r2e (both above corpus max) needs a controlled route to become a score.
- V279's docstring/page still say sign(T) == −sign(cmd); correct when V279 is next touched.
- `dose_e_sign_by_k.py` LIMIT 15360 (slot 7: 16384) — unchanged, no frame affected on either log.
- Golden model: does not yet carry the map knee or the corrected P arithmetic.
