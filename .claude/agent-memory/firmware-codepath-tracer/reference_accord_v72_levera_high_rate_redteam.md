---
name: reference_accord_v72_levera_high_rate_redteam
description: Red-team of proposed V72 Lever A (flattening r24/gain_B mode-10 rec0/rec1 ALL FOUR Y points to 5244, ungated) -- EVERY prior build (V66/68/69/70/71A) that touched these records edited ONLY Y[0]/Y[1], never Y[2]/Y[3]. V72 is the first to raise gain_B's HIGH-RATE response. r24-alone multiplier at high rate (3.41x) EXCEEDS V62's flat 2.0x that produced an 11.71x 40-49Hz regression. Also fully decoded FUN_0003aa2c's r24/r26/damping combine site and the gp-0x67ac reduced-sum branch at the instruction level.
metadata:
  type: reference
---

**Session: 2026-08-04, red-team assignment from team-lead on the V72 slate (rate-lane Lever A +
FactorC/E Lever B).** Full report sent via SendMessage; this captures what should outlive it.

## Headline: V72 Lever A touches a region NO prior build has ever touched

[EVIDENCE, grep of build_v66/68/69/70/71a_tva.py] Every prior build editing `0xD2A74`/`0xD2AB0` (r24/
gain_B mode-10 rec0/rec1, 0 and 10 km/h) touched **ONLY Y[0] and Y[1]** (rate breakpoints 0/400) —
`build_v69_tva.py:126-137` states this explicitly ("rec0 and rec1, Y[0] and Y[1], each EXACTLY
QUADRUPLED"), and V70/V71A reuse `V69.REC0`/`V69.REC1` with the same Y[0]/Y[1]-only pattern. **Y[2]/Y[3]
(rate 1400/1500-3000) are STOCK in every one of these builds.** V72's proposed edit (flatten ALL FOUR Y
points to 5244) is the FIRST proposal in this kit's history to raise `gain_B`'s HIGH-RATE response on the
ungated surface route. ⇒ **the established "r24 is near-inert, no grind#2 regression" result (V69/V70)
does not transfer** — it was measured on builds that never touched the region V72 touches.

## Full instruction-level decode of `FUN_0003aa2c` (`0x3aa2c-0x3ad74`) [EVIDENCE, fresh full disasm]

The aggregator combine site. Confirms exactly, at the instruction level:
- `dtorque = clamp(gp-0x4f62, ±0x1400)` computed ONCE at `0x3aa9c-0x3aac0`, shared by r24 and r26
  (register `r1`, reused unmodified at `0x3ab6c` for r26 and `0x3ac16` (`mov r1,r8`) for r24).
- r26: `0x3aac4-0x3ab2a` gain_A LERP-over-motor-rate; `0x3ab2a-0x3ab54` = 2-sample average of
  `gp-0x69a4` (the ADAPTIVE WEIGHT `w`, NOT dtorque or the output — this matters: it means neither r24
  nor r26 has ANY temporal filtering on the fast/dtorque path, both are purely memoryless instantaneous
  Q10 scalar multiplies). `0x3ab5c-6c` gate selection (`0xC6444`/`0xC643E`/LERP). `0x3ab6c-96`:
  `r26 = clamp(polarity * (((dtorque*w)>>10)*gainA)>>10, ±0x2000)`.
- r24: `0x3ab98-0x3ac16` gain_B LERP + gate selection (`0xC6442` mask-arm outranks all > `0xC6446` when
  `lp!=0` > `0xC6440` when state>=5 > else the LERP). `0x3ac16-58`: `r24 = clamp(polarity *
  deadzone((dtorque*gainB)>>10, cal 0xC61F6=3), ±0x2000)`.
- `0x3ac58-0x3ace2`: **the `gp-0x67ac` reduced-sum branch** (see below).
- `0x3ac78-0x3acda`: full-sum path — damping (`gp-0x6bd0`, clamp ±0x800), magnitude (`gp-0x6b86`, clamp
  ±0x1800), boost (`gp-0x6bbe`, clamp ±0x800... wait clamp derived from `addi 0x3000` = ±0x3000),
  friction (`gp-0x6b26`, clamp ±0x400), resonance (`gp-0x6ad4`, clamp ±0x2800), r26, r24, mixer/arb
  (`gp-0x6b4c`, clamp ±0x2800), return-centre (`gp-0x6b62`, clamp ±0x2000) — all summed by plain `add`
  at `0x3acc8-0x3acda`, THEN `jarl 0x36682` (Lane D, `FUN_00036682`, the 11th summand from my prior
  report) folds in, THEN the ±0x2800 output clamp with shadow-lockstep check.

## `gp-0x67ac==1` reduced-sum path — fully decoded [EVIDENCE]

`r20 = (gp-0x67ac clamped to max 1) == 1` (computed at function entry, `0x3aa34-4c`). If `r20==0`
(the normal case if `gp-0x67ac` is 0 in the field), full sum runs as above. **If `r20!=0`:**
`0x3ac5c-0x3ac76` runs instead — reduced sum = `(tp+0x74ab==0 ? clamp(gp-0x6ade,±0x400) : 0) +
(tp+0x74ac!=0 ? 0 : clamp(gp-0x6b62,±0x2000)) + clamp(gp-0x6b4c,±0x2800)`, **and the `jarl 0x36682` call
is skipped entirely** (it's only on the `r20==0` arm). Byte-read this session: `tp+0x74ab` (`0xC74AB`)
= **0x00**, `tp+0x74ac` (`0xC74AC`) = **0xEE=238** (stock). With those values, the reduced sum in stock
= `clamp(gp-0x6ade,±1024) + clamp(gp-0x6b4c,±0x2800)` ONLY — **r24, r26, damping, magnitude, boost,
friction, resonance AND Lane D (`FUN_00036682`) all drop out.** Corroborates FW-surface's/team-lead's
concern precisely; whether `gp-0x67ac` actually reads 1 in the field is FW-engagement's open item, not
resolved here.

## Saturation-onset shape change [EVIDENCE, arithmetic + cross-checked against build_v67_tva.py's own note]

r24's output clamp is ±8192. At `gainB=5244` (V72's flat target, = V67/V68's arm value), r24 saturates
at `|dtorque| >= 1024*8192/5244 = 1599.4` — **reproduces `build_v67_tva.py`'s own quoted figure
("lane saturates at |dtorque| >= 1599") exactly, independent derivation.** Stock's own high-rate gain
(1536-1947) needs `|dtorque| >= 4308-5461` to saturate — essentially unreachable (clamp ceiling on
dtorque itself is 5120). **V72 makes r24 saturate at the SAME low threshold uniformly across every
rate**, including the high-rate operating point where stock currently never saturates — turning r24 from
a linear derivative term into an effectively saturating/relay element over a much wider envelope than
stock, specifically where grind#2's extreme tail lives.

## Differentiator `H(z)=(1-z^-4)/2` at fs=1000Hz, gp-0x4f62 [EVIDENCE, exact z-domain, reproduces record's 1.93x]

| f | \|H\| | phase |
|---|---|---|
| 7.793 Hz | 0.098 (-20.2 dB) | +84.4 deg |
| 21.0 Hz | 0.261 (-11.7 dB) | +74.9 deg |
| 45.0 Hz | 0.536 (-5.4 dB) | +57.6 deg |

Always phase-LEADING; gain rises +14.8 dB from 7.8 to 45 Hz. Neither r24 nor r26 adds any phase of their
own (confirmed memoryless above) -- V72 changes GAIN only, not phase, in this lane.

## Gain ratio table, V72/stock, speed=0 km/h (worst case; exact 1.000x at >=50 km/h, strict 2-point)

| rate_key | r24 ratio | r26 ratio |
|---|---|---|
| 0-400 | 1.71x | 0.167x |
| 1400-1500 | 2.26-2.31x | 0.19-0.21x |
| 3000 | **3.41x** | 0.25x |

**r24-alone at high rate (3.41x) EXCEEDS V62's flat 2.000x combined multiplier that produced the
recorded 11.71x rise in 40-49Hz extreme-tail content** (creep AND |driver torque|>=1200 AND |angle|
>=100 deg, p=0.0003, cross-validated on the comma IMU). r26 moves favorably but its absolute weight
`w=avg(gp-0x69a4)` is UNMEASURED (sign-only probe throughout this kit's V67-V71 history) -- blocks a
combined number. grind#2 is essentially engagement-independent (1.33x, "weak" per the existing record)
so it is squarely inside V72's (ungated) exposure.

**Recommended fix if this thread is picked back up:** keep Y[2]/Y[3] at stock for r24 (deliver the
creep/grind#1 benefit via Y[0]/Y[1] only, matching every prior build AND the record's own finding that
grind#1 lives 97.8-100% inside the flat [0,400] rate segment); or if the high-rate flattening is kept,
cap it <=3072 (<=2.0x, matching V62's own flown ceiling) and fly with a dedicated 40-49Hz probe.
**V71B (route 54, apparently already flown/extracted per the task list) is the closest existing on-car
data point** -- it doubled ALL FOUR Y points of gain_A/r26 (opposite lane, opposite direction, but same
"touches the high-rate breakpoints" structure) -- pull its 40-49Hz band before green-lighting V72.

## Related
[[reference_accord_ratchet_time_constant_inventory_and_factorce_lever]] -- my prior session's report,
established the FactorC/E lever and the Lane D (`FUN_00036682`) phase finding this session's
`gp-0x67ac` decode shows is ALSO vacuous under the reduced-sum path.
