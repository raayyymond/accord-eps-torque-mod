# HANDOFF 2026-08-30 — the notch was in the wrong place, and six of my own claims were wrong

**Nothing was flashed. No CAN or UDS message was sent.** Five builds were cut (V231–V235), two were
withdrawn, one live drive card exists. 1324 checks, 40/40 builders bit-exact.

---

## 1. WHAT TO DRIVE

**`docs/scoring/DRIVE-CARD-V235.md`** is the only live card. Everything else in `docs/scoring/` older
than it is a historical record.

```
  V235   39990-TVA,A160-V235-V234BASE-C63AE.BACK.TO.HONDA.1024-0x13000-0x100000.rwd
         rwd a6a58fa9ce11a0fa...   image ad6d485eefb2f6bc...

  = THE CAR + 3 cells, 15 payload bytes, verified by diffing the image against the car:
      0xC60A8/AC/B0/B4   the notch at the net-damping optimum      12 B
      0xC40DC            alpha2 8 -> 22, Honda's own value          1 B
      0x55DF2            the biquad-state probe on CAN 427          2 B   telemetry only

  paired arms, TWO BYTES each, for attribution:
      V234  isolates 0xC63AE (1024 vs 512)
      V233  isolates Lever B (5244 vs 13107)

  DO NOT FLY:  V228 (destroys 46.5 % of net damping), V230 (withdrawn, cuts a damper),
               V222 (8x gain + Lever B 2.5x above optimum)
```

---

## 2. THE FINDING THAT REFRAMES THE ARC

**There is exactly ONE biquad in this ECU, Honda uses it as a 55 Hz notch, and every build since V172
has been *relocating* it — moving it out of the band where its lane pumps and into the band where its
lane damps.**

Measured on `gp-0x6b86`, the notch's own lane, flown on CAN 427 in ra4/ra5/ra6, phase against wheel
rate, coherence-gated. Sign mapping fixed by the kit's own b26 result (`+137°`, `|cos| 0.73`, called
*"a REAL 6–9 Hz DAMPER"*), so **cos < 0 = damping, cos > 0 = pumping**:

```
  6-9    DAMPING  all 3 routes agree      22-30  PUMPING  all 3 agree
  9-12   DAMPING  all 3 routes agree      30-40  PUMPING  all 3 agree
  12-15  DAMPING  all 3 routes agree
  15-22  crossover, routes disagree
```

A notch belongs only where the lane pumps. **V228's 20.5 Hz placement sits at the crossover and its
skirt cuts the damping region** — which is why it measures as destroying 46.5 % of the net damping.

**This is the first mechanical explanation the 56-build null history has had.**

---

## 3. THE METRIC THAT WAS MISSING, AND WHICH REORDERED EVERYTHING

**A lane's damping contribution is `|H|·cos(φ)`, not `|H|`.** Every notch comparison in this kit,
mine included, had been made on magnitude alone. Adding the phase term inverts verdicts:

```
  build         6-9      9-12    12-15    22-30    30-40   damping  pumping
  car         1.000x   1.000x   1.000x   1.000x   1.000x   1.000x   1.000x
  V228        0.861x   0.799x  -0.055x  -0.088x  -0.498x   0.535x  -0.293x
  V232        0.985x   0.990x   0.858x   0.694x  -0.123x   0.944x  +0.285x
  V235        1.004x   1.000x   0.891x  -0.050x  -0.888x   0.965x  -0.469x
```

V228 **flips 12–15 Hz from damping into pumping**, which no magnitude table could show.
`rlog-tools/score/net_damping_by_build.py`. **Run it before proposing any filter or gain change.**

---

## 4. THE Re(Z) SIGN FRAME IS RESOLVED — ANALYTICALLY

`rez_spectrum.py` had flagged the absolute sign as unresolved, and that blocked three separate levers.
**The empirical anchor failed first and was abandoned** (the only directional pair, r95/V101 vs
r96/V102, differs by loop gain, which moves Re(Z) mechanically in the same direction as the observed
effect). It resolves without one:

`Re(Z)` is `carState.steeringTorque` over `carState.steeringRateDeg` — **both driver-frame**, and the
operator-confirmed convention puts +torque and +angle both toward LEFT. So `T·ω` is unambiguous:

> **`Re(Z) < 0` = the column does work on the driver's hands = ANTI-DAMPING.**

That immediately withdrew V230 (its α2 cut removes a *measured damper*) and closed `0xC40DC` in both
directions (Honda's 22 already sits at **99.3 %** of its theoretical ceiling at 7.79 Hz).

---

## 5. SIX CLAIMS OF MINE THAT WERE WRONG

Listed because the next session will read these notes the way this one read notes from months ago.

1. **"Audio is 2.3–7× more efficient than CAN"** — WITHDRAWN. Like-for-like, every CI spans 1.0;
   audio is *worse* on the point estimate in two of three bands. The original compared r24-gated audio
   against gated CAN using a factor measured on one route applied to a median from others.
2. **"V230's lever is probably inert"** — MISREADING. The record says the ×1.5 dose was
   *"UNMEASURABLE, not dead — do not file it FALSIFIED"*. `y = K·α` is invariant to K; the *motion*
   is not. V94's 6× cut of that cell ended a drive, which proves it reaches the car.
3. **Three V233 geometries** — each failed a gate: one **boosted** the band it was meant to cut and
   leaned on a 70° phase rotation; one rotated 10.5 Hz by −14.4° where the lane sits at cos −0.989;
   one was **deleted for amplifying 0.2 %** rather than granted a third documented exception.
4. **"V235 is the car plus exactly two things"** — wrong count; it is three. Caught by diffing the
   built image against the car instead of trusting the claim.
5. **My own de-embedding** — put 99.5 % of the power in one band. Division by near-zero at ra5/ra6's
   own notch. **You cannot recover a lane's response where the in-force filter removed the signal.**
6. **A script's verdict line** reading *"the advantage is fitted to the sample"* — the geometry is
   provably not fitted (every fold picks it) and 2-of-3 with a 10× margin asymmetry is a different
   thing. Corrected where it lives.

**Every one was caught by a control, a gate, or a check — none by inspection.** That is the pattern
worth carrying forward.

---

## 6. TWO DEFECTS IN BUILDS I WAS RECOMMENDING

Both found by checking cells against the record rather than trusting the carried ladder.

- **Lever B.** The record: *"THE LANE IS AN OPTIMUM AND V88 IS SITTING ON IT. BOTH FLANKS ARE NOW
  MEASURED … LEVER B IS OFF EVERY FUTURE SHORTLIST, IN BOTH DIRECTIONS."* V71c, above it, was **the
  worst build ever recorded on all three symptoms**. Read from the images: V88, the car and V217 carry
  **5244**; **V221 stepped it to 13107 and V228–V233 all inherited that**, unflown, toward the flank
  measured catastrophic. V234/V235 remove it.
- **`0xC63AE`.** Carried at 512 since V206 and **unpriced** — STATE.md's own word. The opposite
  direction is already NO-GO for an AC gain that *reverses* across the amplitude range. It halves the
  soft relay's **small-signal** gain, exactly where LKAS authority at small commands is decided.
  V235 returns it to Honda's 1024.

---

## 7. STANDING BLOCKS

- **No gain step on the strength of added damping.** The corpus has no clean gain contrast (V101 moved
  the clamps too, and the routes tap different signals), and Re(Z) is confounded by gain itself.
  Converting damping into headroom needs an open-loop transfer — GATE 2 — never measured here.
  A gain change is the class that produced V101's *"vibration at all speeds"* and V71c.
- **`0xC40DC` is spent in both directions.**
- **Lever B is off every shortlist in both directions.**
- **Score the MOTION, never a lever's own output** — in a stable loop that quantity is invariant by
  construction. Binary *liveness* tests are exempt.
- **When arms differ by build or route, the ROUTE is the bootstrap unit.** Episode-level CIs are too
  narrow and can flip the sign.

---

## 8. WHAT V235 DOES AND DOES NOT ADDRESS

| goal | V235 |
|---|---|
| grinding / ratcheting | **addressed** — cuts the band the lane *and* the aggregate pump in |
| LKAS authority | **nothing** — 0 of 15 command/authority cells differ from the car, verified |
| peak command oscillation | premise refuted on this bus; the roughness is a **small-command** phenomenon, where the notch acts |

---

## 9. OPEN ITEMS

1. **Does the biquad run at all?** Honda ships it dormant behind `gp-0x671a ≥ 5` (0 of 255,292 engaged
   frames); V103 armed it to the LKAS flag, and that arming is byte-intact on V103→V235. **V235's probe
   settles it**: the state floats boot to exactly `0.0f`, so identically zero across a drive means the
   filter never executed — and the whole notch axis retires.
2. **The 55 Hz cost measures to −0.05 %** of the lane's power, so it is mechanically negligible and the
   audible 50–72 Hz excess does **not** originate in the lane V235 touches. One route pair; worth
   re-checking if a future build has the tap for it.
3. **ra6 dissented in cross-validation** because its own notch erases 22–26 Hz — the band under test.
   Not a generalisation failure; a blind spot of the held-out route.
4. **LKAS authority has no EPS-side route** on present evidence.

---

## 10. TOOLS ADDED THIS SESSION

```
  rlog-tools/score/net_damping_by_build.py         |H|*cos(phi) per band per build -- run before any filter change
  rlog-tools/score/notch_lane_pump_damp.py         where the lane pumps vs damps
  rlog-tools/score/optimise_notch_net_damping.py   the constrained optimiser
  rlog-tools/score/notch_leave_one_route_out.py    cross-validation
  rlog-tools/score/lane_deembed_biquad.py          de-embedding, with the near-zero trap documented
  rlog-tools/score/aggregate_vs_lane_pumping.py    does the SUM pump where the lane does
  rlog-tools/score/alias_bound_55hz_cost.py        bounds 52-71 Hz via the CAN fold
  rlog-tools/score/biquad_liveness.py              armed-vs-dormant, and why audio cannot answer it
  rlog-tools/score/harmonic_lock_test.py           with the shuffled control that refuted it
  rlog-tools/lib/band_contrast.py                  now cluster-aware
  analysis-2020accord/verify/cell_audit_vs_stock.py  every cell vs stock, and which also differ from the car
```
