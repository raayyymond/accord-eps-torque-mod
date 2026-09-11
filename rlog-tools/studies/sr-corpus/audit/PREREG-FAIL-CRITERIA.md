# Adversarial pass on the SR-vs-angle instrument — FAIL criteria, pre-registered
Written before any number was computed. Subagent `sr-audit`, 2026-09-10.

A **FAIL** (= "do not reshape the fork's SR map on this evidence") is declared if ANY of:

F1  CIRCULARITY. Refitting with a FREE INTERCEPT (or with angleOffsetAverageDeg instead of
    angleOffsetDeg, or with the offset perturbed over its plausible +/-1 sigma range) moves the
    near-centre sR by more than HALF the claimed 17.1 -> 14.4 span (i.e. > 1.35 units), or
    collapses the monotone trend to within its own CI.
F2  SIGN IMBALANCE. The small-|sa| bins are materially asymmetric in left/right population
    (|n+ - n-|/(n+ + n-) > 0.2) AND flipping to a sign-balanced resample moves near-centre sR
    by > 1.0 unit. (An angle-offset bias only survives pooling when signs are imbalanced.)
F3  BICYCLE MODEL. Replacing curvature_factor by the purely kinematic 1/L changes the SHAPE
    (not just the level) such that the high-angle depression shrinks by > 50%; or the
    stiffnessFactor needed to null the effect is inside [0.5, 2.0] (physically plausible).
F4  SPEED, NOT ANGLE. In an |angle| x speed cross-tab, sR varies more ACROSS SPEED at fixed
    angle than ACROSS ANGLE at fixed speed; or the angle bins have no overlapping speed
    support at all (confounded by construction, effect not separable).
F5  INSTRUMENT CHAIN. The gyro-free wheel-speed yaw rate (0x1D0, (v_rr - v_rl)/track)
    disagrees with yaw_cal by a scale > 5% or reverses the angle trend; or a lead/lag sweep
    of +/-200 ms moves near-centre sR by > 1.0 unit.
F6  NOT-QUASI-STATIC / SLIP. The depression at large |sa| disappears in genuinely
    steady-state windows (sustained constant angle+speed >= 1.5 s), i.e. it is a transient or
    slip artefact rather than a rack property.
F7  FIRMWARE / ENGAGEMENT DEPENDENCE. The curve differs between firmware arms (stock vs
    V282 vs V289r1) or between engaged and manual by more than the block-bootstrap CIs.
    The instrument claims to read the MECHANICAL rack; any such split falsifies that claim.
F8  ESTIMATOR ARTEFACT. A continuous (unbinned) fit does not reproduce the monotone shape,
    or OLS-x-on-y vs OLS-y-on-x vs TLS straddle the whole claimed span.

A **PASS** requires the monotone quickening to survive F1-F8 with the near-centre-to-high-angle
span still >= ~1.5 sR units and CIs that do not overlap between the extreme bins.

**Partial verdict allowed**: "not yet" if the effect survives the confounds I could test but a
listed test could not be run on the available data.
