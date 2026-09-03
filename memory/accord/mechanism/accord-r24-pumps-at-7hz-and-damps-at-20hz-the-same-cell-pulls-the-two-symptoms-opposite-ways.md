---
name: accord-r24-pumps-at-7hz-and-damps-at-20hz-the-same-cell-pulls-the-two-symptoms-opposite-ways
description: 2026-09-03, the two Opus deep analyses (docs/research/7HZ-STRONG-TURN-DEEP-ANALYSIS-2026-09-03.md, GRINDING-DEEP-ANALYSIS-2026-09-03.md). MEASURED on r31-r34 from a bit nobody had read -- the V105+ cave publishes sign(gp-0x6ada) (= r24, the engaged-only base-assist rate lane at flat gain 0xC6446 = 5244) in 0x14A byte 4 bit 4 at 100 Hz: r24 PUMPS below ~10 Hz (+179 deg re the wheel rate at 7 Hz in the loaded stratum, coh 0.76 -- i.e. in phase with the rate under the kit's convention) and DAMPS at 13-23 Hz (-6 deg at the 20 Hz creep line, coh 0.80); the bar-to-rate phase swings 210 deg through the free-wheel torsion-bar mode at ~10-12 Hz. Plant-free share method (both lanes enter the same 1 kHz sum with unit coefficients, clamp +-0x2800 -> gp-0x6b94): at 7 Hz the LKAS servo's return-ratio share is 0.81 (never > 1 on 18 episodes), r24's 1.17 (> 1 on 17/18) -> r24 sustains the strong-turn ripple; at 20 Hz in creep r24 delivers 3.23 aggregator counts per rate count (+5 deg) vs the LKAS PID's 1.90 (-69 deg) -> r24 is ~83 % of the 20 Hz damping. So 0xC6446 5244 -> 512 would fix the 7 Hz and strip 74-90 % of the grind damper: DO NOT FLASH it. Honda's own arms (2048; the 2150-3072 LERP) sit near the 7 Hz neutral point; V280 flies 2.8x past it -- the whole account of "7 Hz stutter, very attenuated grind". A hidden gain arm (gp-0x671d != 0 -> 0xC6442 = 1024) would invert every ranking; r24 is not on the wire -> V282 = the inert r24 comparator tap (cave displacement re-point, keeps the 427 T tap).
metadata:
  type: reference
---

# r24 pumps at 7 Hz and damps at 20 Hz -- the same cell pulls the two symptoms opposite ways (2026-09-03)

| claim | status | method |
|---|---|---|
| sign(gp-0x6ada) is on 0x14A b4.4 since V105 | EVIDENCE | cave decode; re-extracted from r31-r34 |
| r24 re rate: +179 deg at 7 Hz (loaded), -6 deg at 20 Hz (creep) | EVIDENCE (coh 0.76 / 0.80; sign() preserves phase; residual flat 13-23 Hz) | deepgrind |
| bar re rate -95..-108 deg at 3.9-9 Hz, +111..+116 deg at 14.8-25 Hz (loaded stratum) | EVIDENCE (coh to 0.94) | deep7hz |
| creep20's "bar re rate -70 deg at 20 Hz" | WRONG by 180 deg (mixed convention); re-measured +114 deg, coh 0.94 | deepgrind |
| twistloop's "gp-0x4f60 = -(cache tq)" | sign error (builder negates, cache negates back); gp-0x6752 = -1 now MEASURED | deepgrind |
| L_servo 0.81 / L_r24 1.17 at 7 Hz | EVIDENCE (plant-free identity) | deep7hz, r24_deembed.py |
| V281 rev 3 (Kp flat 248) stops the 7 Hz cycle by 9-12 % margin; Q~2-3 mode remains | BELIEF | deep7hz |
| V281 rev 3 makes the 7 Hz NET damping slightly worse (-2.09 -> -2.42, aggregator budget) | BELIEF | deepgrind (registered) |
| ranked loop shapes (cal-only, never touched in 280 builds): output-lag pole 5->15 Hz (0xC63EC/EE 932/1457) + 0xC6446 -> 2048 (7 Hz +1.97, 20 Hz x0.87); pole 5->15 alone; pole 5->10; fb pole 16.5->33 (0xC63E8/EA 842/2814) | BELIEF; shared cost = HF gain x1.8-2.9 at 25-50 Hz, unobservable | deepgrind |
| Ki 100 at 0xC63E6 (corner 0.5 Hz at Kp 248) costs ~0 at 7-9/20 Hz, restores the low-demand deadband flat 248 creates; no accumulator tap needed | EVIDENCE arithmetic / BELIEF transient | deep7hz §10 |

Open: the plant above 25 Hz (no instrument); 20 Hz vs 80/120 Hz alias (audio could settle it); gp-0x671d's identity; the 1 kHz tick; gp-0x69a4 (r26); which r24 LERP bank is live.
Related: [[accord-grind-happens-hands-off-the-bar-signal-is-twist-and-the-engaged-rate-lane-gate-is-live]], [[accord-the-creep-grind-is-the-lkas-rate-loop-crossover-resonance-d-dominated]].
