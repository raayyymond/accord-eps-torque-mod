---
name: reference-accord-lerp-envelope-gating
description: Accord EME LERP envelope tables are gated by DRIVER ASSIST (not LKAS cmd) — inactive during hands-off LKAS; explains zero stock 1x EMEs
metadata:
  type: reference
---

# Accord Envelope LERP Tables — Gating by Driver Assist

## Core finding (verified 0x43116–0x43134 in s_motor_torque_rate_shaper)

The T1/T2 LERP envelope tables are selected and zeroed based on **driver assist torque** (`gp-0x6bf0`), NOT the LKAS command (`gp-0x6acc`). Threshold = ±9216 (cal at `0xC6156`).

Selection logic at `0x43116–0x43134`:
- `driver_assist < -9216` → T1 active (T2 = 0)  [leftward driver override]
- `driver_assist > +9216` → T2 active (T1 = 0)  [rightward driver override]
- `|driver_assist| < 9216` → **BOTH outputs = 0** ← hands-off LKAS / normal operation

## Table layout (firmware-verified)

| Table | Cal address | X breakpoints | Y values |
|-------|-------------|---------------|----------|
| T1 upper | `tp+0x7748` = `0xC6748` | {-8192, -1024} | {1024, 1024, 0} |
| T2 lower | `tp+0x7754` = `0xC6754` | {1024, 8192} | {-1024, -1024, 0} |

X input = `gp-0x6af8` (gated `gp-0x4f60`, column angular velocity Q10; HW gate zeros when |v| ≥ 25600 = 25 deg/s).

T1 and T2 are **mutually exclusive** — they are alternative single bounds, not simultaneous upper+lower bounds.

## Consequence for EME analysis

During hands-off LKAS (`gp-0x6bf0 ≈ 0`), the entire LERP path is zeroed. The integrator `gp-0x3570` bounds in this mode come from **velocity-based rate-shaper bounds only**, not the ±1024 LERP plateau.

This resolves the apparent contradiction:
- **Stock 1× never causes EMEs**: cmd ≈ 418 LSB is below the rate-shaper bound at all velocities → integrator bleeds toward zero.
- **2× causes EMEs**: cmd ≈ 835 LSB exceeds the rate-shaper bound when the column stalls (bound collapses toward 0) → integrator winds → SM2/SM3 trip.

The LERP plateau of ±1024 is only relevant when the driver is actively fighting the wheel with ≥ ~9 Nm assist force — i.e., a driver-override event, not pure hands-off LKAS.

## Open question — velocity-breakpoint asymmetry

T1 releases from plateau at velocity = -1024 Q10 (-1 deg/s leftward).  
T2 releases from plateau at velocity = +8192 Q10 (+8 deg/s rightward).

T2's active zone extends 8× further into the rightward-velocity range before zeroing out. Whether this reflects a real left/right behavioral asymmetry or a calibration convention is **unresolved**. Operator is skeptical this represents real asymmetric behavior. Investigate in a future session.

**Why:** The plot (`_envelope_lerp_plot2.py`) previously overlaid both tables without encoding mutual exclusivity, creating an apparent "dead zone" annotation that was incorrect, and implied the ±1024 plateau was the binding constraint during hands-off LKAS.

**How to apply:** When reasoning about what limits the LKAS integrator at any given moment, first check the driver assist state. During normal openpilot operation (no hands), T1 = T2 = 0 and rate-shaper bounds are the only active envelope. The ±1024 LERP plateau is a driver-override feature, not a baseline LKAS constraint.

## ⊕ 2026-06-03 — this gate IS the corridor arm of the soft-EME bound; it's why V30 failed; V31 floors boost instead

This `|gp-0x6bf0| ≤ 9216` gate (T1/T2 = the DIRECTION CORRIDOR `tp+0x7748`/`tp+0x7754`) is **one arm of the
soft-EME integrator's 3-way max/min bound** `MAX/MIN(corridor, IIR gp-0x3574, boost)`. Confirmed this session
by walking `FUN_00042af8`. The corridor has a SECOND gate too: `0x43114` (`cmp r21,r13; bh`, `r21`=cal
`0xC641A`=0) zeroes it when authority `r13 ≠ 0` (`r13 = gp-0x6966 = (|integrator gp-0x3570>>15|×1092)>>10`).
So the corridor is live only when the driver fights (`|gp-0x6bf0|>9216`) AND authority ≈ 0.

V30 (corridor ×4 = 4096) was flashed and drove well but **still soft-EME'd on one hard SUSTAINED hands-off
turn** — exactly because this gate zeroes the corridor hands-off, so V30's widened corridor was inactive there
(bound = max(IIR, boost), both small on a held wheel → collapse → 2× cmd winds up → SM2/SM3). **V31 floors the
BOOST arm instead** (gated only by authority, ON at authority≈0), which holds the bound at 4096 at the
hands-off initiation instant the corridor can't. Full model: [[reference-accord-soft-eme-bound-arm-gating]].
(This memory's "bound collapses toward 0 when the column stalls → 2× EME" prediction was correct.)

See also: [[reference-accord-soft-eme-bound-arm-gating]], [[reference-accord-corridor-lockstep]], [[reference-accord-override-snap-state-machines]], [[reference-accord-eme-lever-semantics]]
