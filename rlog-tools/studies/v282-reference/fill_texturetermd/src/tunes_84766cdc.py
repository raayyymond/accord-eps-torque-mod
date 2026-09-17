import ast
import json
import math
import numpy as np

from opendbc.car.chrysler.values import CAR as CHRYSLER_CAR
from opendbc.car.gm.values import CAR as GM_CAR
from opendbc.car.hyundai.values import CAR as HYUNDAI_CAR
from opendbc.car.subaru.values import CAR as SUBARU_CAR
from opendbc.car.toyota.values import CAR as TOYOTA_CAR
from openpilot.common.constants import CV
from openpilot.starpilot.common.testing_grounds import testing_ground

CIVIC_BOSCH_MODIFIED_B_FIXED_FRICTION_THRESHOLD = 0.30
STANDARD_FRICTION_THRESHOLD = 0.30
HKG_CANFD_BASE_FRICTION_THRESHOLD = 0.39
FLM_SCHEMA_VERSION = 1
FLM_FRICTION_SPEED_KNOTS = [0.0, 5.0, 10.0, 15.0, 25.0]
CIVIC_BOSCH_MODIFIED_B_LAT_ACCEL_FACTOR_MULT = 1.20
CIVIC_BOSCH_MODIFIED_A_VARIANT_LAT_ACCEL_FACTOR_MULT = 1.00
CIVIC_BOSCH_MODIFIED_B_VARIANT_LAT_ACCEL_FACTOR_MULT = 1.75
CIVIC_BOSCH_MODIFIED_B_TRANSITION_SPEED = 12.0
CIVIC_BOSCH_MODIFIED_B_PHASE_SCALE = 0.08
CIVIC_BOSCH_MODIFIED_B_FF_ONSET = 0.18
CIVIC_BOSCH_MODIFIED_B_FF_ONSET_WIDTH = 0.07
CIVIC_BOSCH_MODIFIED_B_FF_CUTOFF = 1.35
CIVIC_BOSCH_MODIFIED_B_FF_CUTOFF_WIDTH = 0.38
CIVIC_BOSCH_MODIFIED_B_FF_REDUCTION_LEFT = 0.14
CIVIC_BOSCH_MODIFIED_B_FF_REDUCTION_RIGHT = 0.24
CIVIC_BOSCH_MODIFIED_B_TURN_IN_BOOST_LEFT = 0.04
CIVIC_BOSCH_MODIFIED_B_TURN_IN_BOOST_RIGHT = 0.00
CIVIC_BOSCH_MODIFIED_B_UNWIND_TAPER_LEFT = 0.40
CIVIC_BOSCH_MODIFIED_B_UNWIND_TAPER_RIGHT = 0.60
CIVIC_BOSCH_MODIFIED_B_TURN_IN_FRICTION_BOOST_LEFT = 0.02
CIVIC_BOSCH_MODIFIED_B_TURN_IN_FRICTION_BOOST_RIGHT = 0.00
CIVIC_BOSCH_MODIFIED_B_UNWIND_FRICTION_REDUCTION_LEFT = 0.26
CIVIC_BOSCH_MODIFIED_B_UNWIND_FRICTION_REDUCTION_RIGHT = 0.40
CIVIC_BOSCH_MODIFIED_A_VARIANT_FF_RESTORE_LEFT = -0.10
CIVIC_BOSCH_MODIFIED_A_VARIANT_FF_RESTORE_RIGHT = 0.02
CIVIC_BOSCH_MODIFIED_A_VARIANT_TURN_IN_BOOST_LEFT = -0.05
CIVIC_BOSCH_MODIFIED_A_VARIANT_TURN_IN_BOOST_RIGHT = 0.02
CIVIC_BOSCH_MODIFIED_A_VARIANT_UNWIND_TAPER_LEFT = 0.24
CIVIC_BOSCH_MODIFIED_A_VARIANT_UNWIND_TAPER_RIGHT = 0.06
CIVIC_BOSCH_MODIFIED_A_VARIANT_TURN_IN_FRICTION_BOOST_LEFT = -0.02
CIVIC_BOSCH_MODIFIED_A_VARIANT_TURN_IN_FRICTION_BOOST_RIGHT = 0.01
CIVIC_BOSCH_MODIFIED_A_VARIANT_UNWIND_FRICTION_REDUCTION_LEFT = 0.22
CIVIC_BOSCH_MODIFIED_A_VARIANT_UNWIND_FRICTION_REDUCTION_RIGHT = 0.05
CIVIC_BOSCH_MODIFIED_A_VARIANT_CENTER_TAPER_MAX = 0.12
CIVIC_BOSCH_MODIFIED_A_VARIANT_CENTER_TAPER_LAT = 0.24
CIVIC_BOSCH_MODIFIED_A_VARIANT_CENTER_TAPER_LAT_WIDTH = 0.05
CIVIC_BOSCH_MODIFIED_A_VARIANT_CENTER_TAPER_SPEED = 18.0
CIVIC_BOSCH_MODIFIED_A_VARIANT_CENTER_TAPER_SPEED_WIDTH = 2.5
CIVIC_BOSCH_MODIFIED_B_VARIANT_FF_REDUCTION_LEFT = 0.50
CIVIC_BOSCH_MODIFIED_B_VARIANT_FF_REDUCTION_RIGHT = 0.82
CIVIC_BOSCH_MODIFIED_B_VARIANT_TURN_IN_BOOST_LEFT = 0.00
CIVIC_BOSCH_MODIFIED_B_VARIANT_TURN_IN_BOOST_RIGHT = 0.00
CIVIC_BOSCH_MODIFIED_B_VARIANT_UNWIND_TAPER_LEFT = 4.40
CIVIC_BOSCH_MODIFIED_B_VARIANT_UNWIND_TAPER_RIGHT = 6.20
CIVIC_BOSCH_MODIFIED_B_VARIANT_TURN_IN_FRICTION_BOOST_LEFT = 0.00
CIVIC_BOSCH_MODIFIED_B_VARIANT_TURN_IN_FRICTION_BOOST_RIGHT = 0.00
CIVIC_BOSCH_MODIFIED_B_VARIANT_UNWIND_FRICTION_REDUCTION_LEFT = 2.80
CIVIC_BOSCH_MODIFIED_B_VARIANT_UNWIND_FRICTION_REDUCTION_RIGHT = 4.20

BOLT_2022_2023_CARS = (
  GM_CAR.CHEVROLET_BOLT_ACC_2022_2023,
  GM_CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
  GM_CAR.CHEVROLET_BOLT_CC_2022_2023,
)
BOLT_2018_2021_CARS = (
  GM_CAR.CHEVROLET_BOLT_CC_2018_2021,
)
BOLT_2017_CARS = (
  GM_CAR.CHEVROLET_BOLT_CC_2017,
)
BOLT_CARS = BOLT_2022_2023_CARS + BOLT_2018_2021_CARS + BOLT_2017_CARS
# Re-measured 2026-09-11 over 82 routes / 894 segments / 14.2 h, on an instrument that contains no
# steering ratio at all:  sR = curvature_factor(v)*sa / (-yaw_cal/v - roll_comp), fitted with a
# PER-ROUTE FREE INTERCEPT and one common slope, so liveParameters.angleOffsetDeg never enters and
# no single route has to identify the slope alone.  Kinematic -- wheel angle to yaw rate -- so
# engaged and manual driving both count and the result is independent of the EPS firmware.  Checked:
# a stock-firmware 98%-manual route reads 15.82 at |sa| 35-400 deg where a V289r1 83%-engaged route
# reads 15.88.  Gates: calibrated, v > 4 m/s, |steeringRateDeg| < 20.
# Refit 2026-09-12 with route 0000006c--2bc842dbac added (83 routes; flown on this map at toggle 16.84,
# 62 segments, mostly motorway).  The fit never sees the served map or the toggle, so routes flown on
# unknown maps/settings count equally.  With 6c left out the fit reproduces every previous knot exactly;
# with it every bin moved <= 0.024 (inside every CI and the +/-0.12 shape band), shape 2.171 -> 2.154.
# 6c alone, where it has data: served-minus-measured -0.02 at 20-28, -0.01 at 45-55, -0.15/+0.08 at
# 130-210 deg.  The route CONFIRMS the reshape; the knots below are the 83-route values.
#
# The previous map was too FLAT.  The rack falls 2.16 :1 between 20-45 and 130-165 deg (95% CI
# [2.09, 2.22], systematic +/-0.12); the old curve fell 1.15 over the same span -- it quickened at
# 53% of the true rate.  Against the served curve it ran ~0.57 too LOW below 36 deg and up to +0.62
# (+4.3%) too HIGH at 165-210 deg.  Too high a served ratio makes calc_curvature UNDER-read, which
# the loop answers by OVER-delivering: the reported oversteer on roundabouts and 90 deg+ corners,
# absent on the motorway because the sign flips at ~50 deg.
#
# Values are ABSOLUTE served ratios (V[0] == NOMINAL), so the array reads as real ratios and the
# SteerRatio toggle means exactly "the on-centre ratio": set it to 16.88 for scale 1.0000.
# Three segments are NOT measurements:
#   0-23 deg    pinned by convention.  Below ~20 deg the estimator is NOT IDENTIFIED -- three-
#               estimator bracket width 1.55/0.55/0.25, denominator SNR 2.5 -- and every split that
#               disagreed anywhere (driver torque, engaged/manual, firmware arm) disagreed only
#               there.  The offset is identified at low angle, the slope at high angle, neither at both.
#   31-61 deg   interpolated across the 36-45 and 45-55 deg bins, which FAILED the lag-plateau test
#               (monotone, sweep variation 1.7 and 0.5 against a 0.30 pass threshold) and were dropped.
#   236+ deg    FROZEN at the old curve's served values (13.96/12.72/12.06 rescaled by 16.33/16.00;
#               unchanged to <=0.002 at 236/260/303/340/380/450).  1306 s of data exists above
#               303 deg but its median speed is 1.41 m/s -- parking -- and 0.1 s survives v > 4.  The
#               estimator divides yaw by speed, so that end is structurally out of reach.  The
#               227->236 step (14.09 -> 14.25, +0.16) is a deliberate discontinuity where measurement
#               meets extrapolation; smoothing it would mean silently editing a frozen knot.
# This is a COMPENSATION curve, not physical rack geometry: calc_curvature uses k = d/L rather than
# tan(d)/L, so a perfectly constant rack would read 1.4% low at 200 deg and 3.3% at 300 deg.  That
# cancels against the consumer (the map feeds the same function) so it is excluded from the band --
# but do not cite these numbers as the rack's true ratio.
# Bands: SHAPE +/-0.12, LEVEL +/-0.57.  The level term is the 4% gyro-vs-wheel-speed yaw-scale
# disagreement, which asymptotes flat from 50 deg up and is therefore multiplicative and constant:
# it moves both ends together and cancels in the shape.  A reshape consumes the shape.
HONDA_ACCORD_STEER_RATIO_ANGLE_BP = [0.0, 23.0, 31.0, 61.0, 76.0, 95.0, 116.0, 151.0,
                                     178.0, 227.0, 236.0, 303.0, 380.0]  # deg
HONDA_ACCORD_STEER_RATIO_V = [16.88, 16.88, 16.88, 16.25, 15.97, 15.45, 15.03, 14.68,
                              14.45, 14.09, 14.25, 12.98, 12.31]  # :1
# The map above is the rack SHAPE, normalised so that on-centre reads NOMINAL.  The SteerRatio
# toggle sets the LEVEL: sr = shape * (toggle / NOMINAL), so the whole curve slides together and
# the geometry is preserved.  Set the toggle to 16.88 to serve the measured curve unscaled.
HONDA_ACCORD_STEER_RATIO_NOMINAL = 16.88
HONDA_ACCORD_STEER_RATIO_LEVEL_MIN = 0.60   # toggle 10.13
HONDA_ACCORD_STEER_RATIO_LEVEL_MAX = 1.25   # toggle 21.10
# Kp for the Accord torque controller is NOT a constant here: controlsd overwrites
# LatControlTorque.pid._k_p every frame with the SteerKP toggle (a flat [[0], [SteerKP]]), so a
# construction-time override would be dead code.  Ki is applied at construction and then
# re-applied from the AccordTorqueKi toggle every frame (default below).
HONDA_ACCORD_TORQUE_KI = 0.30
HONDA_ACCORD_TURN_FF_REDUCTION_MAX = 0.30
HONDA_ACCORD_TURN_FF_ONSET = 0.45
HONDA_ACCORD_TURN_FF_WIDTH = 0.12
# Plant feedforward for the Accord's modified EPS.  The model is the same first-order balance
# under both EPS firmwares the fork has driven:
#     steering wheel rate [deg/s] = G(v) * torque - k(v) * angle        torque in [-1, 1]
# The torque that HOLDS an angle is k*angle/G and the torque that MOVES the wheel is rate/G.
# A lat-accel feedforward (setpoint / latAccelFactor) is the wrong SHAPE on this plant: it has no
# speed law and no friction term, so the P/I terms have to cancel it and the loop settles off
# command (measured on V293 route 70: 0.88x at 8-15 m/s, 1.12x above 22 m/s).
#
# TABLES = EPS firmware V293+ ("torque mode": the EPS LKAS lane is an open-loop torque map, its
# 1 kHz rate loop removed).  Identified on route 75604b0a432fdc89_00000070--717f5a7866
# (2026-09-13, 858 s laterally engaged, 27 clean hands-off stretches / 738 s), joint fit of
# u = a(v)*angle + b*angle_rate + F*sign(angle_rate) + u0 with a 2000-resample block bootstrap:
# G = 1/b, k = a/b, hold k/G = a.  Coulomb F = 0.010-0.012 (that is SteerFriction's own unit; set the
# toggle, it is NOT in these tables).  On V293 the plant is a SPRING: torque sets an angle, and the
# torque per degree is speed-flat above ~12 m/s (0.0079 / 0.0113 / 0.0154 per deg at 12.5 / 18.5 /
# 28.5 m/s) and much softer below 8 m/s (the 4-5 m/s knots are LOW CONFIDENCE: b's CI crosses zero
# there; the conservative, smaller hold was taken).  28.5 m/s is extrapolated (drive p95 25 m/s).
# The 4.0 m/s knot (0.30) is NOT the joint fit (0.93): route 70's own hands-off 0-5 m/s frames held 251 deg
# with |u| <= 0.163, which with Coulomb 0.012 bounds the hold at a <= 0.0007 torque/deg (OLS 0.00076) --
# 2.4x below the fit's knot; an over-holding FF over-steers low-speed entries (simulated +108 % peak on a
# planner-limited entry to 100 deg at 4.5 m/s), so the bound wins.  The 8.0 m/s knot (1.00, fit 1.64) is the
# compromise between that bound and the v^2 extrapolation of the solid 12.5 m/s cell: hold 0.00055 / 0.00086 /
# 0.0023 / 0.0041 torque per deg at <=4 / 5 / 8 / 10 m/s (about 25 % under the extrapolation at 8-10, 25 % over
# the bound at 5 -- both inside what one drive can say).  Adversarial pass:
# accord-eps-torque-mod/docs/review/ADV-REV2-FORK-PACKAGE-2026-09-13.md.
# KNOT PLACEMENT: the fit's bands are centred at 4.9 / 12.0 / 18.9 / 22.8 m/s, not at the knots.  The 28.5 m/s
# knot is EXTRAPOLATED (G 167, K 3.91) so that the interpolation reproduces the measurement at 22.8 m/s
# (hold 0.0154, viscous 0.0047 vs measured 0.0154 / 0.0049); writing the 22.8 values into the 28.5 knot, as a
# first cut did, under-held by 16 % at 22.8.  Likewise the 12.5 knot (K 2.30) reproduces the 12.0 m/s cell
# (0.0074 vs 0.0076).  Above 25 m/s (the drive's p95) the hold is a linear extrapolation -- BELIEF.
# Kit report: accord-eps-torque-mod/rlog-tools/studies/grind/V293-PLANT-IDENT-2026-09-13.md.
# The pole k these tables imply (0.2-0.5 Hz) is their weak part; the feedforward consumes only
# k/G (hold) and 1/G (move), never k alone.
# Previous tables, identified on the V280-V292 RATE-LOOP firmware (routes r34/r35/r39/r3a/r3c,
# 2026-09-02..04) -- restore these if the EPS goes back to a V282-class image:
#     G_V = [120.0, 95.0, 85.0, 70.0]   K_V = [0.17, 0.28, 0.35, 0.45, 0.50]
# (no single AccordEpsSpringScale maps one set onto the other: the ratio is 1.2x at 5 m/s and
# 2.1x from 12.5 m/s up).
HONDA_ACCORD_EPS_G_BP = [5.0, 12.5, 18.5, 28.5]        # m/s
HONDA_ACCORD_EPS_G_V = [550.0, 271.0, 246.0, 167.0]    # deg/s per unit torque (= 1/b)
HONDA_ACCORD_EPS_K_BP = [4.0, 8.0, 12.5, 18.5, 28.5]   # m/s
HONDA_ACCORD_EPS_K_V = [0.30, 1.00, 2.30, 2.77, 3.91]  # 1/s (= a/b; k/G is the hold torque per deg)
HONDA_ACCORD_FF_RATE_GAIN = 0.5    # fraction of the d(angle_des)/dt term (toggle AccordFFRateGain).  With the V293
                                   # tables 1/G IS the measured viscous term, but the term is fed the derivative of a
                                   # PLANNER-LIMITED reference (1098 deg/s allowed at 3 m/s = 2.0 torque through
                                   # G = 550): at 1.0 the feedforward alone exceeded full scale for 0.34 s below 8 m/s
                                   # on route 70's own demand (max 1.13); at 0.5 the max is 0.81.  Keep 0.5.
HONDA_ACCORD_FF_RATE_RC = 0.10     # s, first-order filter on d(angle_des)/dt
# rev 6 (2026-09-16): an ACCORD-SCOPED cutoff for latcontrol_torque's jerk_filter, replacing the generic
# LP_FILTER_CUTOFF_HZ = 1.2 for this car only.  The delay-compensation stage
#     setpoint = u(t-D) + F_j(s) * (u(t) - u(t-D))    =>    H(s) = e^{-sD} + F_j(s) * (1 - e^{-sD})
# is an EXACT delay canceller: H == 1 at EVERY frequency when F_j == 1.  So all of that stage's residual lag and
# its whole 0.4-1 Hz gain bump come from F_j alone -- and F_j is a 1.2 Hz smoother sized for a raw derivative,
# applied here to a quantity that is already a 38-frame difference and therefore already smooth.
# |F_j| and phase at 0.2/0.6/1.0 Hz: 0.999/0.989/0.970 and -2.9/-8.5/-14.0 deg at 4.0 Hz, against
# 0.986/0.894/0.768 and -9.5/-26.6/-39.8 deg at 1.2 Hz.
# Measured consequence on the whole setpoint chain at 19 m/s (group lag at 0.25 Hz | |H| at 0.5/0.6/0.7 Hz):
#     rev 5, AccordRefFilter 0.12, 1.2 Hz : 0.271 s | 1.112 / 1.088 / 1.039
#     AccordRefFilter 0.06, 4.0 Hz (rev 6): 0.128 s | 1.063 / 1.069 / 1.065   <- FLATTER than rev 5, half the lag
# i.e. this is not a new term and not a trade: it corrects a constant that was never measured on this path.
# Scoped to the Accord because LP_FILTER_CUTOFF_HZ is generic and no other car here has been measured on it.
HONDA_ACCORD_JERK_LP_HZ = 4.0      # Hz, cutoff of the lateral-jerk low-pass in the delay-compensation stage
HONDA_ACCORD_FF_ANGLE_LIMIT_DEG = 400.0
# Clamp on the MOVE term (rate_gain * d(angle_des)/dt / G) of the rate-plant feedforward.  The
# planner's jerk limit (clip_curvature, 5 m/s^3) becomes a steering-rate limit that scales as
# 1/v^2, so below ~8 m/s the move term alone exceeds full-scale torque, and the G/k tables are
# extrapolated flat below 5 m/s.  Sized as a strict no-op for the normal regime: simulated with
# the on-road settings (rate gain 0.5, gain/spring scale 1.0, sR 16.0) on a planner-limited
# 0 -> 2.5 m/s^2 ramp (jerk filter + 0.2 s look-ahead included, closed loop on the identified
# plant) the largest |move| torque seen was
#     10 m/s: 0.680   12.5: 0.489   15: 0.369   20: 0.250   25: 0.196   30: 0.165   35: 0.137
#      9 m/s: 0.804    8: 0.976     7: 1.226    6: 1.608    5: 2.236
# so the limit is 1.4 (2.06x the 10 m/s peak) at and above 10 m/s, tapering to 1.0 (the whole
# actuator range, i.e. the fastest rate the servo can produce anyway) at 8 m/s and below.  On
# that ramp it first bites at ~7.9 m/s.
HONDA_ACCORD_FF_MOVE_TORQUE_LIMIT_BP = [8.0, 10.0]  # m/s
HONDA_ACCORD_FF_MOVE_TORQUE_LIMIT_V = [1.0, 1.4]    # torque, units of the [-1, 1] output
# V293 TORQUE-MODE PLANT, SECOND PASS (2026-09-14, routes 70 + 71, ~1,650 s hands-off).  The linear
# k(v)/G(v) tables above are the FIRST-ORDER fit; the static hold torque the car actually needs is
#     hold(v, angle) = k(v) * sat(v) * tanh(angle / sat(v))        [+ static friction, applied separately]
# a SATURATING spring: measured hands-off with the wheel still (|rate| < 15 deg/s, 1 Hz LPF), median
# torque per (|angle|, speed) cell, both routes pooled, fitted jointly (weighted rms 0.0085 torque).
# Against the linear tables it is 3-5x LARGER below 10 m/s at 5-35 deg (route 71 tracking gain 0.83 /
# 0.93 at <8 / 8-15 m/s = under-turning, felt as "loose on slight bends") and 0.6-0.7x SMALLER above
# 17 m/s at 20-30 deg and above 25 m/s everywhere (tracking gain 1.12 above 22 m/s = over-turning).
# sat(v) = 19.3 + 546 * exp(-v / 3.01) deg: near-linear to 150 deg at 4 m/s, saturating past ~45 deg
# at 10 m/s (the tyre aligning torque peaks; 0.30 torque at 55-77 deg is measured) and past ~20 deg
# above 15 m/s -- angles a 3 m/s^2 planner never reaches there, so the saturated tail is unexercised
# BELIEF above 15 m/s.  k(v) knots are the fitted values smoothed monotone (the 12.5 / 15 m/s cells
# wobble from sparse data).  The map was fitted with a static-friction intercept of 0.020 torque,
# which is NOT in the table: the hysteresis feedforward (AccordFrictionHyst) supplies it in the
# direction of the last desired motion.  Kit: accord-eps-torque-mod/rlog-tools/studies/grind/
# _scratch/r70r71_hold_joint_fit.txt and v293r2_design.py.
HONDA_ACCORD_HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]   # m/s
# rev 4 (2026-09-14): the 28 m/s knot 0.0134 -> 0.0160.  The routes 70+71 fit was flat above 23 m/s because the >22 band's
# median speed was 22.8; routes 72/73 (medians 25.7 / 26.7 m/s) needed 1.3-1.7x the map at 4-12 deg, and the tyre's
# aligning torque grows ~v^2 for a given angle until it saturates, so a flat law above 23 is the one shape that cannot be
# right.  0.0160 is x1.20 (a v^1.0 rise 23 -> 28), deliberately short of v^2 (x1.48): the route-to-route scatter of the
# small-angle hold at speed is itself +/-30-40 % (crown, wind), which the integral gain -- not the map -- has to absorb.
HONDA_ACCORD_HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]  # torque/deg at 0 deg
# rev 6 (2026-09-16): a speed-scheduled LEVEL on the hold map.  Route 76's hands-off hold regression reads the map
# LOW at 15-25 m/s and CORRECT at 5-12 m/s (hand-free delivered/hold 0.99-1.00 at 5-8), and every route since 72 has
# read it low at speed.  It is a BIAS, not scatter, and a feedforward bias is not free: the disturbance observer's own
# loop gain IS its model mismatch, L_dob ~ Q(s) * (P/P_model - 1), so a low map makes the observer carry 45-64 % of the
# feedforward through its two 0.6 Hz poles -- 27 deg of lag and a x1.20 gain at the 0.24 Hz lane-centring mode, the
# largest single stage in the measured chain.  Correcting the model collapses that loop and returns the phase it cost
# (simulated L_dob 0.302 -> 0.074 at 19 m/s, torque-loop phase at 0.25 Hz -45.2 -> -35.4 deg).
# x1.30 is deliberately SHORT of the measured x1.2-1.65 and of the x1.45 the identification verdict allows at 15-22:
# the route-to-route scatter is +-30-40 % (crown, wind, camber) and the observer -- not the map -- must absorb scatter.
# Under-correcting is the safe side; the observer makes up the rest, slowly.  Over-correcting over-holds, and nothing
# takes that back.
# 12.5 m/s and below stay at 1.00: the map is right there, and a GLOBAL AccordEpsSpringScale 1.3 was already falsified
# at 12 m/s (+0.91 step overshoot).  That is also why this is a schedule and not that existing scalar.
# APPLIED IN get_honda_accord_hold_torque ONLY -- deliberately NOT by editing HONDA_ACCORD_HOLD_K_V, because
# get_honda_accord_mode_hz reads that same table and levelling k in place would move the P/I error notch by
# sqrt(level) (2.04 -> 2.33 Hz at 22.8 m/s); the record has a x1.35 notch move going unstable at 26 m/s.
# rev 6.4 (2026-09-16): 1.00 -> 1.15 and 1.30 -> 1.45, measured rather than reasoned.
# Rev 6 chose x1.30 deliberately short of the measured x1.4-1.65 on the argument quoted above -- "the observer,
# not the map, must absorb scatter".  ⭐ THAT ARGUMENT IS FALSIFIED BY THE BAND-PASSED TRACKING METRIC.  Under-
# correcting the map does not let the observer absorb scatter; it leaves a standing deficit the observer must
# carry, and carrying it is what makes the observer cancel the commanded fine correction as if it were a
# disturbance.  Measured on the stick-slip bench with a plant spring x1.50: delivered fraction of a 0.06 m/s^2
# rms lane-centring correction, band-passed to 0.25-0.60 Hz, against rev 6 AS FLOWN --
#     light damping  19 m/s  0.86 -> 0.95      identified  19 m/s  0.36 -> 0.45
#     light damping  26 m/s  0.88 -> 0.97      identified  26 m/s  0.43 -> 0.53
# i.e. +0.06 to +0.10 everywhere, and a near-perfect match in the light-damping world.
# THE LEVEL AND THE OBSERVER'S INTERNAL MODEL MOVE TOGETHER, which is what makes it safe: correcting only the
# observer rings the 2 m/s^2 hold-and-kick test 0.33 -> 3.89 deg at 8 m/s, because the feedforward's deficit
# then lands on P and I instead.  With both corrected there is no deficit for anyone to carry, and the same
# test is unchanged.  Swept 1.15/1.45 and 1.30/1.50: the first passes every safety test (T1 disturbance, T3
# ring, T8 chatter, break-out t50) against rev 6 as flown; the second fails on a 0.17 deg ring at 26 m/s.
# ⚠ x1.45 is inside the measured x1.4-1.6 but with less room for the +-30-40 % route-to-route scatter (crown,
# wind, camber) than x1.30 had.  AccordHoldLevel off restores the rev 3-5 unlevelled map, as before.
HONDA_ACCORD_HOLD_LEVEL_BP = [12.5, 17.5]          # m/s
HONDA_ACCORD_HOLD_LEVEL_V = [1.15, 1.45]           # multiplier on the hold map (NOT on the mode frequency)
HONDA_ACCORD_HOLD_SAT_DEG = (19.3, 546.0, 3.01)   # sat(v) = a + b * exp(-v / c), deg
HONDA_ACCORD_HOLD_STATIC_FRICTION = 0.020          # torque, the intercept the map was fitted WITHOUT (see above)
# The steering system's own mode on the V293 firmware: J * angle'' + b * angle' + hold(angle) = torque, with
# J = 8e-5 torque/(deg/s^2) (route 71 band-passed fit 7.2e-5..9.1e-5 by band; the limit-cycle point gives
# 9e-5..1e-4) and a light b ~ 0.0006 (damping ratio 0.2-0.35).  Its frequency sqrt(k(v)/J)/2pi runs 1.0 Hz
# at 4.5 m/s to 2.1 Hz above 20.  On route 71 the fork's delayed P + the SteerFriction relay drove it into a
# 2.34 Hz, +-6 deg limit cycle on hard curves above 20 m/s.  The notch (AccordErrorNotchQ) sits on it.
HONDA_ACCORD_EPS_INERTIA = 8e-5                    # torque per deg/s^2
# Rate loop (AccordRateLoopGain): torque per deg/s of (desired - measured wheel rate), measured rate through a
# first-order filter of HONDA_ACCORD_RATE_LOOP_RC; the gain is tapered by min(1, HONDA_ACCORD_RATE_LOOP_TAPER_V / v)
# above that speed because the ~60 ms loop delay turns rate feedback into negative stiffness at the 2 Hz mode.
# Loop-delay budget measured on route 71: CAN-in -> carState 3 ms, controlsState -> 0xE4 13 ms, 0xE4 -> delivered
# torque 30-45 ms; the rate-loop-alone gain must stay below 1 where its phase passes -180 deg (3.5-4 Hz):
# at 0.0006 it is 0.5 there, at 0.0012 it would cross.
HONDA_ACCORD_RATE_LOOP_RC = 0.01                   # s (rev 5, 2026-09-15: was 0.03.  The rate loop damps only where its
                                                   # phase -(w*Td + atan(w*RC)) is above -90 deg, i.e. below ~2.8 Hz with
                                                   # the 60 ms round trip; the 0.03 s filter cost a further 25 deg at
                                                   # 2.5 Hz.  0.01 s moves the damping/pumping boundary up ~0.5 Hz and
                                                   # cut the simulated hard-turn 1.6-3 Hz wheel-rate energy 15-20 %.
                                                   # The 0x18F rate is 0.125 deg/s per LSB, so the extra noise is
                                                   # 1e-3 * 0.125 = 1e-4 torque, far below the command LSB.)
HONDA_ACCORD_RATE_LOOP_TAPER_V = 12.0              # m/s
# Desired-angle travel that swings the hysteresis term end to end.  rev 6 (2026-09-16): speed-scheduled.
# WHAT THE TERM IS.  Below band/2 of demand it is an EXACT LINEAR SPRING of friction/band torque per degree at
# EXACTLY ZERO phase -- not friction compensation at all; only above band/2 does it become friction*sign(d angle_des)
# with the phase lead a Coulomb compensator needs (+11 deg at a 0.57 deg demand, +39 at 1.2, +73 at 10).  So the band
# sets THE DEMAND AT WHICH THE TERM STOPS BEING A SPRING AND STARTS BEING FRICTION COMPENSATION, and a fixed 3 deg is
# a different demand at every speed: 0.034 m/s^2 at 8 m/s but 0.158 at 19 and 0.251 at 26.
# WHY IT MATTERS.  Solving u = k*theta + b*theta' + F*sign(theta') for theta gives PLAY of half-width d = F/k: the
# plant is BACKLASH, and a play operator emits EXACTLY NOTHING below an input amplitude of d.  At F 0.012 that is
# 1.39 / 0.70 / 0.56 deg at 11.4 / 17.6 / 25.6 m/s against correction amplitudes of 0.69 / 0.32 / 0.18 deg, so
# openpilot's own 0.06-0.08 m/s^2 lane-centring corrections produce no motion at all above ~12 m/s -- which is what
# route 76 measured (0-6 % of them produced any gyro response).
# HOW IT IS SIZED, and why not smaller.  A demand-keyed term that actually reaches break-out MUST over-deliver: it
# needs a slope >= F/dtheta, and once the wheel is free the plant follows u/k, so it delivers (F/dtheta)/k = d/dtheta
# times the demand.  "Delivers the smallest correction" and "does not over-deliver it" are mutually exclusive below
# the half-width.  The table is therefore the LARGEST slope that does not over-deliver -- friction/band ~ the levelled
# hold stiffness: 0.0050 / 0.0071 / 0.0156 / 0.0250 torque/deg against k*level 0.0052 / 0.0088 / 0.0144 / 0.0194.
# That puts the spring/friction threshold at a flat ~0.05 m/s^2 of demand above 12 m/s, and leaves the last of the
# break-out to the disturbance observer -- the only term that can supply it without over-delivering.
# MEASURED on the fully stick-slip plant (kit scratchpad minlaw_sim8.txt, route-76 world, delays x1.5, 19 m/s):
# outer-loop phase margin +2.5 -> +8.6 deg, lag at 0.2 Hz 0.37 -> 0.26 s, lane residual 0.196 -> 0.138 m, and the
# 0.05 m/s^2 small-signal gain 1.45 -> 1.93.  Halving the table again reaches +12.8 deg but takes that gain to 2.68
# -- recorded, not shipped.  If the drive reads over-turning, AccordFrictionHyst 0.015 -> 0.010 moves it to 1.70 at
# no cost in margin, and it is a Galaxy toggle.
# It acts on the DESIRED angle only, so unlike the SteerFriction relay (falsified twice: route 71's 2.34 Hz limit
# cycle, route 73's 4-4.7 Hz chatter) it has no loop gain and cannot self-excite.
HONDA_ACCORD_FRICTION_HYST_BAND_BP = [8.0, 12.0, 19.0, 26.0]     # m/s
HONDA_ACCORD_FRICTION_HYST_BAND_V = [3.0, 2.10, 0.96, 0.60]      # deg of desired-angle travel
HONDA_ACCORD_FRICTION_HYST_BAND_DEG = 3.0          # deg, the fixed fallback = the rev 3-5 behaviour

# ---------------------------------------------------------------------------------------------------------------
# Friction-linearising command dither (AccordDither / AccordDitherGate, rev 6.3, 2026-09-16).
#
# WHY A DITHER AT ALL.  The V293 plant is a spring plus Coulomb friction, so in the (torque -> angle) map it is
# exactly BACKLASH of half-width F/k: 2F/k is 1.1 deg at 26 m/s, 1.3 at 19, 2.7 at 11, 4.7 at 5 (F 0.012, k
# measured on route 76).  A command increment smaller than that band moves the wheel by NOTHING -- which is why
# the smallest executable demand at 19-26 m/s (0.05-0.06 m/s^2) sits right on top of the size of the fork's own
# lane-centering corrections (0.06-0.08).  That is the resolution floor, and no amount of loop gain reaches it:
# the gain that breaks friction at 1 deg/s is 0.012 and the gain-margin ceiling through the 60 ms round trip is
# 0.0016-0.0059.  A dither well above the closed-loop bandwidth and well below the wheel's own mode replaces the
# Coulomb relay by its smoothed describing function for the slow signal.  It is the textbook lineariser, it adds
# NO loop gain and NO phase lag (it is open loop), and -- unlike a narrower hysteresis band -- it does not raise
# the small-signal slope, so it does not over-deliver.  Simulated at 19 m/s, 0.05 m/s^2 @ 0.2 Hz: the rev 6.1
# band schedule gives |H| 1.71 / THD 0.180, a flat band plus 0.012 of dither gives |H| 1.52 / THD 0.088 -- better
# on BOTH axes.  That is the whole case for preferring it to the band schedule rather than stacking them.
#
# FREQUENCY.  14 Hz has to clear three things measured on this car: the V281 7 Hz assist ripple and the 5-9 Hz
# wheel band (the record rejected a 7-10 Hz dither for sitting on them), the 1.0-2.3 Hz steering mode, and the
# 17.9 Hz ring seen on route 70.  14 Hz is the gap.
#
# AMPLITUDE is a toggle, not a constant, because it is the one number no log can settle: 0.012 torque is 49
# counts of 0xE4 and moves the rim about 0.001-0.002 deg -- a fiftieth of the 0.1 deg angle quantiser -- but how
# that FEELS through the column is not predictable from a simulation.  Swept 0.001-0.012 at 8/19/26 m/s: THD
# falls monotonically with amplitude and has no knee below 0.012, so there is no "free" small dose; the operator
# walks it down from the road.  Ceiling 0.02 = 82 counts, above which the 14 Hz slew starts to compete with the
# Honda +-0.03/frame limiter.
#
# THE GATE, and why it is gated on the COMMAND.  A dither earns its ripple only while the rack is STUCK; once
# the rack is sliding, friction is already broken and the dither is ripple with no benefit.  Two candidate
# envelopes were simulated.  The obvious one -- reuse the friction hysteresis state, envelope = 1 - |z|/friction
# -- FAILS: with the rev 6.1 band narrowed to 0.60-0.96 deg, z clips on the smallest demands too, so it reads
# ~0.4-0.5 in BOTH regimes and discriminates nothing.  The command-magnitude envelope works cleanly.  At 19 m/s
# with 0.008 of dither, 12-16 Hz rim rate rms (deg/s), small demand vs 2 m/s^2 corner:
#       ungated          <g> 1.00 -> 0.080  |  <g> 1.00 -> 0.108
#       1 - |z|/friction <g> 0.51 -> 0.076  |  <g> 0.42 -> 0.093      (closes on both: no good)
#       1 - |u|/REF      <g> 0.95 -> 0.081  |  <g> 0.00 -> 0.003      (= the no-dither floor)
# i.e. full dither where it is needed, off in a corner, for no measurable small-signal cost.
# REF 0.15 is where the taper reaches zero: out = lat_accel / LAF, so 0.15 is 2.1 m/s^2 -- a corner, not a
# correction.  Linear taper rather than a switch so the envelope cannot chatter at the threshold.
HONDA_ACCORD_DITHER_HZ = 14.0
HONDA_ACCORD_DITHER_CMD_REF = 0.15                 # unit torque at which the gate is fully closed


def get_honda_accord_dither_gate(output_torque: float, gate: bool = True) -> float:
  """Envelope on the dither amplitude: 1 where the command is small (the rack is stuck and the correction we
  cannot deliver lives here), tapering linearly to 0 by HONDA_ACCORD_DITHER_CMD_REF (a corner, where the rack
  is already sliding and the dither would be ripple for nothing)."""
  if not gate:
    return 1.0
  return float(np.clip(1.0 - abs(float(output_torque)) / HONDA_ACCORD_DITHER_CMD_REF, 0.0, 1.0))


def get_honda_accord_dither(amplitude: float, frame: int, dt: float, output_torque: float = 0.0,
                            gate: bool = True) -> float:
  """One sample of the friction-linearising command dither, in unit torque.  Pure feedforward: the caller adds
  it to the torque that LEAVES the controller, so the PID, the hysteresis, the rate loop and the disturbance
  observer never see it and it cannot enter any feedback state."""
  if amplitude <= 0.0:
    return 0.0
  g = get_honda_accord_dither_gate(output_torque, gate)
  if g <= 0.0:
    return 0.0
  return g * float(amplitude) * math.sin(2.0 * math.pi * HONDA_ACCORD_DITHER_HZ * frame * dt)

# Integral-gain speed schedule (AccordTorqueKi below the first knot, AccordTorqueKiHigh from the second, linear between).
# The live integral gain is Ki * (1 + lsf / Kp): the hard-coded low-speed factor already multiplies it ~7x at 5 m/s, so in
# angle terms the I loop's time constant is roughly speed-flat -- but the low-speed steering mode (1.0-1.5 Hz, zeta ~0.2)
# tolerates far less integral phase lag than the 2 Hz mode at speed.  Simulated on the identified plant (kit
# v293r4_design.py): Ki 2.5 at 5 m/s rings a curve-hold kick to 16-36 deg pk-pk (0.6: 0.7-0.8 deg); at 19-26 m/s the same
# 2.5 cuts the 2 s residual of a 0.03-torque disturbance from 0.11-0.12 to 0.005-0.013 m/s^2 with Ms unchanged (1.75).
HONDA_ACCORD_KI_SCHEDULE_V_BP = [8.0, 18.0]        # m/s
# Disturbance observer (AccordDobHz, rev 5, 2026-09-15).  A P loop through the ~60 ms round trip has a static stiffness of
# only 1 + Kp_torque/k (1.7 at the flown Kp; ~3 at the most Kp the margins allow), so a hold-map level error, a road crown
# or the friction the hysteresis term missed leaves 1/stiffness of it in the angle; the integrator takes it out at its own
# corner (Ki/Kp, 0.2-0.5 Hz) = the catch-up the operator feels.  The observer estimates the unmodelled torque directly,
#   w = hold(angle) + b(v) * rate + J * acc - u(t - HONDA_ACCORD_DOB_DELAY)        (+left frame, torque units)
# from the measured wheel state and the controller's own past output, low-passes it (two poles at AccordDobHz) and adds
# it to the feedforward.  Its loop closes only through the MODEL MISMATCH (|Q| * |P/P_model - 1| < 1), not through the
# plant's phase, so the corner can sit above the integrator's (kit v293r5_design*.py, five plant worlds: 0.03-torque
# step residual at 1 s 0.07 -> 0.03 m/s^2, planner-step overshoot 0.5 -> 0.2, hard-turn hold error -60 %, stable under
# b x0.15-8, hold x1.5, delays x1.5, J x1.5).  The model's b(v) = the fork's 1/G(v) is deliberately the HIGHER estimate:
# below the corner the observer installs the model's damping whatever the plant has; above it the mismatch de-damps the
# 2-2.7 Hz wheel mode, which is why the corner ships at 0.6 Hz (0.8 rang with delays x1.5).  Frozen while the
# output is safety-limited or the driver holds the wheel; reset on engage; faded in from HONDA_ACCORD_DOB_FADE_V_BP.
HONDA_ACCORD_DOB_DELAY = 0.06                      # s, openpilot -> EPS -> angle sensor round trip the model assumes
HONDA_ACCORD_DOB_ACC_RC = 0.05                     # s, filter on d(rate)/dt for the inertia term
HONDA_ACCORD_DOB_MAX_TORQUE = 0.3                  # clip on the estimate, units of the [-1, 1] output
HONDA_ACCORD_DOB_FADE_V_BP = [3.0, 6.0]            # m/s: 0 -> full authority (the plant is unidentified below 8 m/s)
VOLT_STANDARD_CARS = (
  GM_CAR.CHEVROLET_VOLT,
  GM_CAR.CHEVROLET_VOLT_2019,
  GM_CAR.CHEVROLET_VOLT_ASCM,
  GM_CAR.CHEVROLET_VOLT_CAMERA,
  GM_CAR.CHEVROLET_VOLT_CC,
)
SILVERADO_CARS = (
  GM_CAR.CHEVROLET_SILVERADO,
  GM_CAR.CHEVROLET_SILVERADO_CC,
)
GMC_YUKON_CC_CARS = (
  GM_CAR.GMC_YUKON_CC,
)
GENESIS_G90_CARS = (
  HYUNDAI_CAR.GENESIS_G90,
)
GENESIS_G70_CARS = (
  HYUNDAI_CAR.GENESIS_G70_2020,
)
GENESIS_GV70_CARS = (
  HYUNDAI_CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN,
)
PALISADE_CARS = (
  HYUNDAI_CAR.HYUNDAI_PALISADE,
  HYUNDAI_CAR.HYUNDAI_PALISADE_2023,
)
IONIQ_5_CARS = (
  HYUNDAI_CAR.HYUNDAI_IONIQ_5,
)
IONIQ_EV_OLD_CARS = (
  HYUNDAI_CAR.HYUNDAI_IONIQ_EV_LTD,
  HYUNDAI_CAR.HYUNDAI_IONIQ_EV_2020,
)
IONIQ_6_CARS = (
  HYUNDAI_CAR.HYUNDAI_IONIQ_6,
)


def is_ioniq_6_2025_model(CP) -> bool:
  """Identify the newer Ioniq 6 firmware without changing the legacy 2023 path."""
  if getattr(CP, "carFingerprint", None) not in IONIQ_6_CARS:
    return False

  versions = []
  try:
    for fw in CP.carFw:
      value = fw.fwVersion
      versions.append(value.decode("ascii", errors="ignore") if isinstance(value, bytes) else str(value))
  except (AttributeError, TypeError, ValueError):
    return False

  return any("230915" in version for version in versions) and any("240206" in version for version in versions)


SONATA_HYBRID_CARS = (
  HYUNDAI_CAR.HYUNDAI_SONATA_HYBRID,
)
SONATA_CARS = (
  HYUNDAI_CAR.HYUNDAI_SONATA,
)
ELANTRA_NON_SCC_CARS = (
  HYUNDAI_CAR.HYUNDAI_ELANTRA_2022_NON_SCC,
  HYUNDAI_CAR.HYUNDAI_ELANTRA_HEV_2022_NON_SCC,
)
KIA_EV6_CARS = (
  HYUNDAI_CAR.KIA_EV6,
)
KIA_CARNIVAL_CARS = (
  HYUNDAI_CAR.KIA_CARNIVAL_2025,
  HYUNDAI_CAR.KIA_CARNIVAL_HEV_4TH_GEN,
)
TUCSON_4TH_GEN_CARS = (
  HYUNDAI_CAR.HYUNDAI_TUCSON_4TH_GEN,
)
KIA_XCEED_CARS = (
  HYUNDAI_CAR.KIA_XCEED_PHEV,
)
KIA_NIRO_PHEV_2022_CARS = (
  HYUNDAI_CAR.KIA_NIRO_PHEV_2022,
)
KIA_STINGER_2022_CARS = (
  HYUNDAI_CAR.KIA_STINGER_2022,
)
KIA_FORTE_CARS = (
  HYUNDAI_CAR.KIA_FORTE,
  HYUNDAI_CAR.KIA_FORTE_2019_NON_SCC,
  HYUNDAI_CAR.KIA_FORTE_2021_NON_SCC,
)
KONA_NON_SCC_CARS = (
  HYUNDAI_CAR.HYUNDAI_KONA_NON_SCC,
)
KONA_EV_2022_CARS = (
  HYUNDAI_CAR.HYUNDAI_KONA_EV_2022,
)
PRIUS_CARS = (
  TOYOTA_CAR.TOYOTA_PRIUS,
  TOYOTA_CAR.TOYOTA_PRIUS_RETROFIT,
)

CAMRY_CARS = (
  TOYOTA_CAR.TOYOTA_CAMRY,
)

RAV4_PRIME_CARS = (
  TOYOTA_CAR.TOYOTA_RAV4_PRIME,
)

SIENNA_4TH_GEN_CARS = (
  TOYOTA_CAR.TOYOTA_SIENNA_4TH_GEN,
)

TOYOTA_HIGHLANDER_TSS2_CARS = (
  TOYOTA_CAR.TOYOTA_HIGHLANDER_TSS2,
)

TOYOTA_COROLLA_TSS2_CARS = (
  TOYOTA_CAR.TOYOTA_COROLLA_TSS2,
)

LEXUS_IS_CARS = (
  TOYOTA_CAR.LEXUS_IS,
)

SUBARU_IMPREZA_CARS = (
  SUBARU_CAR.SUBARU_IMPREZA,
)

RAM_1500_CARS = (
  CHRYSLER_CAR.RAM_1500_5TH_GEN,
)

RAM_1500_BASE_LAT_ACCEL_FACTOR_MULT = 1.0

GENESIS_GV70_FRICTION_THRESHOLD_GAIN = 0.12
GENESIS_GV70_FRICTION_SPEED_ONSET = 8.0 * CV.MPH_TO_MS
GENESIS_GV70_FRICTION_SPEED_ONSET_WIDTH = 4.0 * CV.MPH_TO_MS
GENESIS_GV70_FRICTION_SPEED_CUTOFF = 60.0 * CV.MPH_TO_MS
GENESIS_GV70_FRICTION_SPEED_CUTOFF_WIDTH = 10.0 * CV.MPH_TO_MS
GENESIS_GV70_FRICTION_CENTER_LAT = 0.28
GENESIS_GV70_FRICTION_CENTER_LAT_WIDTH = 0.12
GENESIS_GV70_FRICTION_CALM_JERK = 0.35
GENESIS_GV70_FRICTION_CALM_JERK_WIDTH = 0.10
GENESIS_GV70_FRICTION_JERK_DEADZONE_MAX = 0.55
GENESIS_GV70_FRICTION_JERK_DEADZONE_LAT = 0.30
GENESIS_GV70_FRICTION_JERK_DEADZONE_LAT_WIDTH = 0.08
GENESIS_GV70_FRICTION_JERK_DEADZONE_SPEED = 12.0 * CV.MPH_TO_MS
GENESIS_GV70_FRICTION_JERK_DEADZONE_SPEED_WIDTH = 3.5 * CV.MPH_TO_MS
GENESIS_GV70_CENTER_OUTPUT_TAPER_MAX = 0.20
GENESIS_GV70_CENTER_OUTPUT_TAPER_LAT = 0.30
GENESIS_GV70_CENTER_OUTPUT_TAPER_LAT_WIDTH = 0.10
GENESIS_GV70_CENTER_OUTPUT_TAPER_SPEED = 22.0 * CV.MPH_TO_MS
GENESIS_GV70_CENTER_OUTPUT_TAPER_SPEED_WIDTH = 3.0 * CV.MPH_TO_MS
GENESIS_GV70_UNWIND_FF_REDUCTION_MAX = 0.35
GENESIS_GV70_UNWIND_FF_OVERSHOOT = 0.15
GENESIS_GV70_UNWIND_FF_OVERSHOOT_WIDTH = 0.18
GENESIS_GV70_UNWIND_FF_JERK = 0.10
GENESIS_GV70_UNWIND_FF_JERK_WIDTH = 0.10
GENESIS_GV70_UNWIND_FF_SPEED = 10.0 * CV.MPH_TO_MS
GENESIS_GV70_UNWIND_FF_SPEED_WIDTH = 4.0 * CV.MPH_TO_MS
GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_MAX = 0.18
GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_SPEED = 50.0 * CV.MPH_TO_MS
GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_SPEED_WIDTH = 8.0 * CV.MPH_TO_MS
GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_ERROR = 0.18
GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_ERROR_WIDTH = 0.15
GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_JERK = 0.15
GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_JERK_WIDTH = 0.10
GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_MAX = 0.28
GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_SPEED = 25.0 * CV.MPH_TO_MS
GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_SPEED_WIDTH = 5.0 * CV.MPH_TO_MS
GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_ERROR = 0.30
GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_ERROR_WIDTH = 0.16
GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_JERK = 0.20
GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_JERK_WIDTH = 0.10
GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_MAX = 0.28
GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_SPEED = 18.0 * CV.MPH_TO_MS
GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_SPEED_WIDTH = 3.5 * CV.MPH_TO_MS
GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_SPEED_CUTOFF = 34.0 * CV.MPH_TO_MS
GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_SPEED_CUTOFF_WIDTH = 4.5 * CV.MPH_TO_MS
GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_CENTER_LAT = 0.22
GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_CENTER_LAT_WIDTH = 0.08
GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_MIN = 0.06
GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_LAT = 0.12
GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_LAT_WIDTH = 0.10
GENESIS_GV70_OUTPUT_SMOOTHING_SPEED = 38.0 * CV.MPH_TO_MS
GENESIS_GV70_OUTPUT_SMOOTHING_SPEED_WIDTH = 6.0 * CV.MPH_TO_MS
GENESIS_GV70_OUTPUT_SMOOTHING_CENTER_LAT = 0.48
GENESIS_GV70_OUTPUT_SMOOTHING_CENTER_LAT_WIDTH = 0.16
GENESIS_GV70_OUTPUT_SMOOTHING_CENTER_RC = 0.42
GENESIS_GV70_OUTPUT_SMOOTHING_CURVE_RC = 0.14
GENESIS_GV70_OUTPUT_SMOOTHING_UNWIND_RC = 0.12
GENESIS_GV70_OUTPUT_SMOOTHING_UNWIND_PHASE = 0.04
GENESIS_GV70_OUTPUT_SMOOTHING_UNWIND_PHASE_WIDTH = 0.08
GENESIS_GV70_OUTPUT_SMOOTHING_DIRECTION_CHANGE_LAT = 0.55
GENESIS_GV70_OUTPUT_SMOOTHING_DIRECTION_CHANGE_RC = 0.065

GENESIS_G70_FRICTION_THRESHOLD_GAIN = 0.10
GENESIS_G70_FRICTION_SPEED_ONSET = 10.0
GENESIS_G70_FRICTION_SPEED_ONSET_WIDTH = 3.0
GENESIS_G70_FRICTION_SPEED_CUTOFF = 35.0
GENESIS_G70_FRICTION_SPEED_CUTOFF_WIDTH = 6.0
GENESIS_G70_FRICTION_CENTER_LAT = 0.28
GENESIS_G70_FRICTION_CENTER_LAT_WIDTH = 0.10
GENESIS_G70_FRICTION_CALM_JERK = 0.35
GENESIS_G70_FRICTION_CALM_JERK_WIDTH = 0.10
GENESIS_G70_FRICTION_JERK_DEADZONE_MAX = 0.39
GENESIS_G70_FRICTION_JERK_DEADZONE_LAT = 0.30
GENESIS_G70_FRICTION_JERK_DEADZONE_LAT_WIDTH = 0.08
GENESIS_G70_FRICTION_JERK_DEADZONE_SPEED = 12.0
GENESIS_G70_FRICTION_JERK_DEADZONE_SPEED_WIDTH = 3.5
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_MAX = 0.26
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_SPEED = 35.0 * CV.MPH_TO_MS
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_SPEED_WIDTH = 8.0 * CV.MPH_TO_MS
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_LAT = 0.35
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_LAT_WIDTH = 0.15
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_LAT_CUTOFF = 1.75
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_LAT_CUTOFF_WIDTH = 0.30
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_JERK = 0.20
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_JERK_WIDTH = 0.12
GENESIS_G70_CENTER_OUTPUT_TAPER_MAX = 0.30
GENESIS_G70_CENTER_OUTPUT_TAPER_LAT = 0.30
GENESIS_G70_CENTER_OUTPUT_TAPER_LAT_WIDTH = 0.10
GENESIS_G70_CENTER_OUTPUT_TAPER_SPEED = 18.0
GENESIS_G70_CENTER_OUTPUT_TAPER_SPEED_WIDTH = 3.0
GENESIS_G70_HIGH_SPEED_TRANSITION_DAMPING_MAX = 0.18
GENESIS_G70_HIGH_SPEED_TRANSITION_DAMPING_SPEED = 45.0 * CV.MPH_TO_MS
GENESIS_G70_HIGH_SPEED_TRANSITION_DAMPING_SPEED_WIDTH = 8.0 * CV.MPH_TO_MS
GENESIS_G70_HIGH_SPEED_TRANSITION_DAMPING_LAT = 0.45
GENESIS_G70_HIGH_SPEED_TRANSITION_DAMPING_LAT_WIDTH = 0.15
GENESIS_G70_HIGH_SPEED_TRANSITION_DAMPING_JERK = 0.35
GENESIS_G70_HIGH_SPEED_TRANSITION_DAMPING_JERK_WIDTH = 0.15
GENESIS_G70_LOW_SPEED_CENTER_TAPER_MAX = 0.06
GENESIS_G70_LOW_SPEED_CENTER_TAPER_LAT = 0.14
GENESIS_G70_LOW_SPEED_CENTER_TAPER_LAT_WIDTH = 0.05
GENESIS_G70_LOW_SPEED_CENTER_TAPER_SPEED_MAX = 7.5
GENESIS_G70_LOW_SPEED_CENTER_TAPER_SPEED_WIDTH = 1.2
GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_MAX = 0.24
GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_SPEED = 6.0
GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_SPEED_WIDTH = 1.5
GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_ERROR = 7.0
GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_ERROR_WIDTH = 3.0
GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_ACTUAL = 8.0
GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_ACTUAL_WIDTH = 4.0
GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_BLEND = 0.50
GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_REDUCTION = 0.85
GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_LAT = 0.14
GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_LAT_WIDTH = 0.05
GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_SPEED = 6.0
GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_SPEED_WIDTH = 1.5
GENESIS_G70_CURVE_UNWIND_OUTPUT_REDUCTION_MAX = 0.10
GENESIS_G70_CURVE_UNWIND_SPEED = 18.0
GENESIS_G70_CURVE_UNWIND_SPEED_WIDTH = 3.0
GENESIS_G70_CURVE_UNWIND_LAT = 0.25
GENESIS_G70_CURVE_UNWIND_LAT_WIDTH = 0.12
GENESIS_G70_CURVE_UNWIND_JERK = 0.08
GENESIS_G70_CURVE_UNWIND_JERK_WIDTH = 0.08
GENESIS_G70_UNWIND_FF_REDUCTION_MAX = 0.34
GENESIS_G70_UNWIND_FF_OVERSHOOT = 0.13
GENESIS_G70_UNWIND_FF_OVERSHOOT_WIDTH = 0.17
GENESIS_G70_UNWIND_FF_JERK = 0.08
GENESIS_G70_UNWIND_FF_JERK_WIDTH = 0.11
GENESIS_G70_UNWIND_FF_SPEED = 18.0
GENESIS_G70_UNWIND_FF_SPEED_WIDTH = 3.0
GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_MAX = 0.15
GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_SPEED = 50.0 * CV.MPH_TO_MS
GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_SPEED_WIDTH = 8.0 * CV.MPH_TO_MS
GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_ERROR = 0.18
GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_ERROR_WIDTH = 0.15
GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_JERK = 0.15
GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_JERK_WIDTH = 0.10
GENESIS_G70_OUTPUT_SMOOTHING_SPEED = 40.0 * CV.MPH_TO_MS
GENESIS_G70_OUTPUT_SMOOTHING_SPEED_WIDTH = 6.0 * CV.MPH_TO_MS
GENESIS_G70_OUTPUT_SMOOTHING_CENTER_LAT = 0.42
GENESIS_G70_OUTPUT_SMOOTHING_CENTER_LAT_WIDTH = 0.14
GENESIS_G70_OUTPUT_SMOOTHING_CENTER_RC = 0.30
GENESIS_G70_OUTPUT_SMOOTHING_CURVE_RC = 0.10
GENESIS_G70_OUTPUT_SMOOTHING_UNWIND_RC = 0.10
GENESIS_G70_OUTPUT_SMOOTHING_UNWIND_PHASE = 0.04
GENESIS_G70_OUTPUT_SMOOTHING_UNWIND_PHASE_WIDTH = 0.08
GENESIS_G70_OUTPUT_SMOOTHING_DIRECTION_CHANGE_LAT = 0.45
GENESIS_G70_OUTPUT_SMOOTHING_DIRECTION_CHANGE_RC = 0.16
GENESIS_G70_ANGLE_OUTPUT_TAPER_MIN = 0.45
GENESIS_G70_ANGLE_OUTPUT_TAPER_START = 70.0
GENESIS_G70_ANGLE_OUTPUT_TAPER_WIDTH = 6.0

BOLT_2017_LATERAL_TESTING_GROUND_ID = testing_ground.id_3
BOLT_2017_STEER_RATIO_TEST_SCALE = 1.045
BOLT_2017_STEER_RATIO_ONSET_SPEED = 20.0 * CV.MPH_TO_MS
BOLT_2017_STEER_RATIO_ONSET_WIDTH = 4.0 * CV.MPH_TO_MS
BOLT_2017_CENTER_TAPER_LAT = 0.10
BOLT_2017_CENTER_TAPER_WIDTH = 0.03
BOLT_2017_CENTER_TAPER_GAIN = 0.055
BOLT_2017_TORQUE_SCALE_BP = [0.0, 0.2, 0.5, 1.0, 1.5, 2.5]
BOLT_2017_TORQUE_SCALE_LEFT = [1.0, 1.0, 1.065, 1.060, 1.055, 1.045]
BOLT_2017_TORQUE_SCALE_RIGHT = [1.0, 1.0, 1.035, 1.020, 0.995, 0.985]
BOLT_2017_TRANSITION_SPEED = 10.0
BOLT_2017_PHASE_SCALE = 0.12
BOLT_2017_TURN_IN_BOOST_LEFT = 0.28
BOLT_2017_TURN_IN_BOOST_RIGHT = 0.18
BOLT_2017_UNWIND_TAPER_LEFT = 0.08
BOLT_2017_UNWIND_TAPER_RIGHT = 0.28

BOLT_2018_2021_LATERAL_TESTING_GROUND_ID = testing_ground.id_4
BOLT_2018_2021_STEER_RATIO_TEST_SCALE = 1.01
BOLT_2018_2021_TORQUE_GAIN_LEFT = 0.090
BOLT_2018_2021_TORQUE_GAIN_RIGHT = 0.050
BOLT_2018_2021_TORQUE_ONSET = 0.18
BOLT_2018_2021_TORQUE_ONSET_WIDTH = 0.08
BOLT_2018_2021_TORQUE_CUTOFF = 1.05
BOLT_2018_2021_TORQUE_CUTOFF_WIDTH = 0.24
BOLT_2018_2021_JERK_TAPER_CUTOFF = 0.42
BOLT_2018_2021_CENTER_TAPER_LAT = 0.12
BOLT_2018_2021_CENTER_TAPER_WIDTH = 0.04
BOLT_2018_2021_CENTER_TAPER_GAIN = 0.35
BOLT_2018_2021_TRANSITION_SPEED = 8.5
BOLT_2018_2021_PHASE_SCALE = 0.10
BOLT_2018_2021_TURN_IN_BOOST_LEFT = 0.22
BOLT_2018_2021_TURN_IN_BOOST_RIGHT = 0.12
BOLT_2018_2021_UNWIND_TAPER_GAIN_LEFT = 0.80
BOLT_2018_2021_UNWIND_TAPER_GAIN_RIGHT = 1.04
BOLT_2018_2021_FRICTION_MULT = 1.01
BOLT_2018_2021_FRICTION_LAT_RISE = 0.24
BOLT_2018_2021_FRICTION_JERK_RISE = 0.28
BOLT_2018_2021_TURN_IN_THRESHOLD_REDUCTION_LEFT = 0.16
BOLT_2018_2021_TURN_IN_THRESHOLD_REDUCTION_RIGHT = 0.16
BOLT_2018_2021_UNWIND_THRESHOLD_INCREASE_LEFT = 0.15
BOLT_2018_2021_UNWIND_THRESHOLD_INCREASE_RIGHT = 0.25
BOLT_2018_2021_TURN_IN_FRICTION_BOOST_LEFT = 0.08
BOLT_2018_2021_TURN_IN_FRICTION_BOOST_RIGHT = 0.08
BOLT_2018_2021_UNWIND_FRICTION_REDUCTION_LEFT = 0.17
BOLT_2018_2021_UNWIND_FRICTION_REDUCTION_RIGHT = 0.27

BOLT_2022_2023_LATERAL_TESTING_GROUND_ID = testing_ground.id_5
BOLT_2022_2023_FF_GAIN_LEFT = 0.11
BOLT_2022_2023_FF_GAIN_RIGHT = 0.06
BOLT_2022_2023_FF_ONSET = 0.12
BOLT_2022_2023_FF_ONSET_WIDTH = 0.07
BOLT_2022_2023_FF_CUTOFF = 1.35
BOLT_2022_2023_FF_CUTOFF_WIDTH = 0.28
BOLT_2022_2023_TRANSITION_SPEED = 9.0
BOLT_2022_2023_PHASE_SCALE = 0.12
BOLT_2022_2023_TURN_IN_BOOST_LEFT = 0.18
BOLT_2022_2023_TURN_IN_BOOST_RIGHT = 0.13
BOLT_2022_2023_UNWIND_TAPER_LEFT = 0.38
BOLT_2022_2023_UNWIND_TAPER_RIGHT = 0.40
BOLT_2022_2023_FRICTION_MULT = 1.09
BOLT_2022_2023_FRICTION_LAT_RISE = 0.22
BOLT_2022_2023_FRICTION_JERK_RISE = 0.26
BOLT_2022_2023_CENTER_TAPER_MAX = 0.11
BOLT_2022_2023_CENTER_TAPER_LAT = 0.18
BOLT_2022_2023_CENTER_TAPER_LAT_WIDTH = 0.03
BOLT_2022_2023_CENTER_TAPER_SPEED = 25.0
BOLT_2022_2023_CENTER_TAPER_SPEED_WIDTH = 2.5
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_MAX = 0.12
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_LAT = 0.14
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_LAT_WIDTH = 0.04
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_SPEED = 4.0
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_SPEED_WIDTH = 1.5
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_FLOOR = 2.0
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_FLOOR_WIDTH = 0.7
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_SPEED_MAX = 16.5
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_SPEED_MAX_WIDTH = 2.0
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_LIMIT = 0.38
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_LAT = 0.17
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_LAT_WIDTH = 0.04
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED = 2.5
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_WIDTH = 0.7
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_MAX = 8.2
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_MAX_WIDTH = 0.6
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SCALE_MIN = 0.62
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_ALPHA_MIN = 0.28
BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_BUMP = 0.080
BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_LAT = 0.18
BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_LAT_WIDTH = 0.06
BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_SPEED = 6.7
BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_SPEED_WIDTH = 1.5
BOLT_2022_2023_TURN_IN_THRESHOLD_REDUCTION_LEFT = 0.16
BOLT_2022_2023_TURN_IN_THRESHOLD_REDUCTION_RIGHT = 0.12
BOLT_2022_2023_UNWIND_THRESHOLD_INCREASE_LEFT = 0.26
BOLT_2022_2023_UNWIND_THRESHOLD_INCREASE_RIGHT = 0.28
BOLT_2022_2023_TURN_IN_FRICTION_BOOST_LEFT = 0.10
BOLT_2022_2023_TURN_IN_FRICTION_BOOST_RIGHT = 0.07
BOLT_2022_2023_UNWIND_FRICTION_REDUCTION_LEFT = 0.27
BOLT_2022_2023_UNWIND_FRICTION_REDUCTION_RIGHT = 0.28

VOLT_STANDARD_LATERAL_TESTING_GROUND_ID = testing_ground.id_3
VOLT_STANDARD_FF_GAIN_LEFT = 0.13
VOLT_STANDARD_FF_GAIN_RIGHT = 0.06
VOLT_STANDARD_FF_ONSET = 0.10
VOLT_STANDARD_FF_ONSET_WIDTH = 0.05
VOLT_STANDARD_FF_CUTOFF = 1.38
VOLT_STANDARD_FF_CUTOFF_WIDTH = 0.28
VOLT_STANDARD_TRANSITION_SPEED = 10.0
VOLT_STANDARD_PHASE_SCALE = 0.10
VOLT_STANDARD_TURN_IN_BOOST_LEFT = 0.20
VOLT_STANDARD_TURN_IN_BOOST_RIGHT = 0.20
VOLT_STANDARD_UNWIND_TAPER_LEFT = 0.20
VOLT_STANDARD_UNWIND_TAPER_RIGHT = 0.20
VOLT_STANDARD_FRICTION_MULT = 1.00
VOLT_STANDARD_FRICTION_LAT_RISE = 0.20
VOLT_STANDARD_FRICTION_JERK_RISE = 0.20
VOLT_STANDARD_TURN_IN_THRESHOLD_REDUCTION_LEFT = 0.05
VOLT_STANDARD_TURN_IN_THRESHOLD_REDUCTION_RIGHT = 0.05
VOLT_STANDARD_UNWIND_THRESHOLD_INCREASE_LEFT = 0.05
VOLT_STANDARD_UNWIND_THRESHOLD_INCREASE_RIGHT = 0.05
VOLT_STANDARD_TURN_IN_FRICTION_BOOST_LEFT = 0.00
VOLT_STANDARD_TURN_IN_FRICTION_BOOST_RIGHT = 0.00
VOLT_STANDARD_UNWIND_FRICTION_REDUCTION_LEFT = 0.05
VOLT_STANDARD_UNWIND_FRICTION_REDUCTION_RIGHT = 0.05
VOLT_STANDARD_CENTER_TAPER_MAX = 0.12
VOLT_STANDARD_CENTER_TAPER_LAT = 0.10
VOLT_STANDARD_CENTER_TAPER_LAT_WIDTH = 0.018
VOLT_STANDARD_CENTER_TAPER_SPEED = 20.0
VOLT_STANDARD_CENTER_TAPER_SPEED_WIDTH = 2.5

SILVERADO_CENTER_TAPER_MAX = 0.22
SILVERADO_CENTER_TAPER_LAT = 0.18
SILVERADO_CENTER_TAPER_LAT_WIDTH = 0.05
SILVERADO_CENTER_TAPER_SPEED = 12.0
SILVERADO_CENTER_TAPER_SPEED_WIDTH = 2.5

GMC_YUKON_CC_PHASE_SCALE = 0.14
GMC_YUKON_CC_PHASE_SPEED_ONSET = 12.0
GMC_YUKON_CC_PHASE_SPEED_FULL = 30.0
GMC_YUKON_CC_PHASE_LAT_ONSET = 0.35
GMC_YUKON_CC_PHASE_LAT_WIDTH = 0.18
GMC_YUKON_CC_TURN_IN_FF_BOOST = 0.08
GMC_YUKON_CC_UNWIND_FF_REDUCTION = 0.12

SONATA_HYBRID_BASE_LAT_ACCEL_FACTOR_MULT = 1.05
SONATA_HYBRID_FF_REDUCTION_LEFT = 0.09
SONATA_HYBRID_FF_REDUCTION_RIGHT = 0.26
SONATA_HYBRID_FF_ONSET = 0.18
SONATA_HYBRID_FF_ONSET_WIDTH = 0.08
SONATA_HYBRID_FF_CUTOFF = 1.35
SONATA_HYBRID_FF_CUTOFF_WIDTH = 0.40
SONATA_HYBRID_TRANSITION_SPEED = 8.0
SONATA_HYBRID_PHASE_SCALE = 0.12
SONATA_HYBRID_TURN_IN_BOOST_LEFT = 0.12
SONATA_HYBRID_TURN_IN_BOOST_RIGHT = 0.02
SONATA_HYBRID_UNWIND_TAPER_LEFT = 0.18
SONATA_HYBRID_UNWIND_TAPER_RIGHT = 0.10
SONATA_HYBRID_CENTER_TAPER_MAX = 0.10
SONATA_HYBRID_CENTER_TAPER_LAT = 0.16
SONATA_HYBRID_CENTER_TAPER_LAT_WIDTH = 0.025
SONATA_HYBRID_CENTER_TAPER_SPEED = 22.0
SONATA_HYBRID_CENTER_TAPER_SPEED_WIDTH = 2.5
SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_MAX = 0.14
SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_LAT = 0.10
SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_LAT_WIDTH = 0.02
SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_SPEED_MAX = 7.5
SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_SPEED_WIDTH = 1.0
SONATA_HYBRID_CENTER_OUTPUT_TAPER_MAX = 0.14
SONATA_HYBRID_CENTER_OUTPUT_TAPER_LAT = 0.18
SONATA_HYBRID_CENTER_OUTPUT_TAPER_LAT_WIDTH = 0.05
SONATA_HYBRID_CENTER_OUTPUT_TAPER_SPEED = 12.5
SONATA_HYBRID_CENTER_OUTPUT_TAPER_SPEED_WIDTH = 2.5
SONATA_HYBRID_CHATTER_THRESHOLD_SPEED_BP = [0.0, 4.5, 7.5, 11.0, 20.0]
SONATA_HYBRID_CHATTER_THRESHOLD_BUMP = [0.02, 0.04, 0.04, 0.02, 0.0]
SONATA_HYBRID_CHATTER_THRESHOLD_CENTER = 0.20
SONATA_HYBRID_CHATTER_THRESHOLD_CENTER_WIDTH = 0.05

SONATA_FF_REDUCTION_LEFT = 0.04
SONATA_FF_REDUCTION_RIGHT = 0.26
SONATA_FF_ONSET = 0.18
SONATA_FF_ONSET_WIDTH = 0.08
SONATA_FF_CUTOFF = 1.40
SONATA_FF_CUTOFF_WIDTH = 0.42
SONATA_TRANSITION_SPEED = 8.5
SONATA_PHASE_SCALE = 0.12
SONATA_TURN_IN_BOOST_LEFT = 0.18
SONATA_TURN_IN_BOOST_RIGHT = 0.00
SONATA_UNWIND_TAPER_LEFT = 0.28
SONATA_UNWIND_TAPER_RIGHT = 0.00
SONATA_CENTER_TAPER_MAX = 0.04
SONATA_CENTER_TAPER_LAT = 0.15
SONATA_CENTER_TAPER_LAT_WIDTH = 0.025
SONATA_CENTER_TAPER_SPEED = 22.0
SONATA_CENTER_TAPER_SPEED_WIDTH = 2.5
SONATA_LOW_SPEED_CENTER_TAPER_MAX = 0.08
SONATA_LOW_SPEED_CENTER_TAPER_LAT = 0.10
SONATA_LOW_SPEED_CENTER_TAPER_LAT_WIDTH = 0.02
SONATA_LOW_SPEED_CENTER_TAPER_SPEED_MAX = 7.0
SONATA_LOW_SPEED_CENTER_TAPER_SPEED_WIDTH = 1.0

ELANTRA_NON_SCC_FF_ADJUST_LEFT = 0.02
ELANTRA_NON_SCC_FF_ADJUST_RIGHT = -0.02
ELANTRA_NON_SCC_FF_ONSET = 0.14
ELANTRA_NON_SCC_FF_ONSET_WIDTH = 0.06
ELANTRA_NON_SCC_FF_CUTOFF = 1.10
ELANTRA_NON_SCC_FF_CUTOFF_WIDTH = 0.34
ELANTRA_NON_SCC_TRANSITION_SPEED = 8.0
ELANTRA_NON_SCC_PHASE_SCALE = 0.10
ELANTRA_NON_SCC_TURN_IN_BOOST_LEFT = 0.10
ELANTRA_NON_SCC_TURN_IN_BOOST_RIGHT = 0.12
ELANTRA_NON_SCC_UNWIND_TAPER_LEFT = 0.22
ELANTRA_NON_SCC_UNWIND_TAPER_RIGHT = 0.12

KIA_XCEED_FF_REDUCTION_LEFT = 0.04
KIA_XCEED_FF_REDUCTION_RIGHT = 0.10
KIA_XCEED_FF_ONSET = 0.16
KIA_XCEED_FF_ONSET_WIDTH = 0.06
KIA_XCEED_FF_CUTOFF = 1.30
KIA_XCEED_FF_CUTOFF_WIDTH = 0.36
KIA_XCEED_TRANSITION_SPEED = 11.5
KIA_XCEED_PHASE_SCALE = 0.10
KIA_XCEED_TURN_IN_BOOST_LEFT = 0.26
KIA_XCEED_TURN_IN_BOOST_RIGHT = 0.06
KIA_XCEED_UNWIND_TAPER_LEFT = 0.20
KIA_XCEED_UNWIND_TAPER_RIGHT = 0.14
KIA_XCEED_CENTER_TAPER_MAX = 0.06
KIA_XCEED_CENTER_TAPER_LAT = 0.12
KIA_XCEED_CENTER_TAPER_LAT_WIDTH = 0.03
KIA_XCEED_CENTER_TAPER_SPEED = 17.5
KIA_XCEED_CENTER_TAPER_SPEED_WIDTH = 2.5

KIA_NIRO_PHEV_2022_CENTER_TAPER_MAX = 0.06
KIA_NIRO_PHEV_2022_CENTER_TAPER_LAT = 0.12
KIA_NIRO_PHEV_2022_CENTER_TAPER_LAT_WIDTH = 0.03
KIA_NIRO_PHEV_2022_CENTER_TAPER_SPEED = 23.0
KIA_NIRO_PHEV_2022_CENTER_TAPER_SPEED_WIDTH = 2.5
KIA_NIRO_PHEV_2022_FRICTION_CENTER_LAT = 0.12
KIA_NIRO_PHEV_2022_FRICTION_CENTER_LAT_WIDTH = 0.03
KIA_NIRO_PHEV_2022_FRICTION_SPEED = 23.0
KIA_NIRO_PHEV_2022_FRICTION_SPEED_WIDTH = 2.5
KIA_NIRO_PHEV_2022_FRICTION_CALM_JERK = 0.22
KIA_NIRO_PHEV_2022_FRICTION_CALM_JERK_WIDTH = 0.06
KIA_NIRO_PHEV_2022_FRICTION_THRESHOLD_GAIN = 0.12

KIA_STINGER_2022_CENTER_TAPER_MAX = 0.12
KIA_STINGER_2022_CENTER_TAPER_LAT = 0.30
KIA_STINGER_2022_CENTER_TAPER_LAT_WIDTH = 0.05
KIA_STINGER_2022_CENTER_TAPER_SPEED = 10.0
KIA_STINGER_2022_CENTER_TAPER_SPEED_WIDTH = 2.5
KIA_STINGER_2022_FRICTION_THRESHOLD_GAIN = 0.10

KIA_CARNIVAL_CENTER_TAPER_MAX = 0.20
KIA_CARNIVAL_CENTER_TAPER_LAT = 0.20
KIA_CARNIVAL_CENTER_TAPER_LAT_WIDTH = 0.055
KIA_CARNIVAL_CENTER_TAPER_SPEED = 3.5
KIA_CARNIVAL_CENTER_TAPER_SPEED_WIDTH = 1.8
KIA_CARNIVAL_CENTER_TAPER_SPEED_MAX = 14.5
KIA_CARNIVAL_CENTER_TAPER_SPEED_MAX_WIDTH = 2.0
KIA_CARNIVAL_FRICTION_THRESHOLD_GAIN = 0.24
KIA_CARNIVAL_FRICTION_CENTER_FADE_MAX = 0.34
KIA_CARNIVAL_HIGHWAY_CENTER_TAPER_MAX = 0.14
KIA_CARNIVAL_HIGHWAY_CENTER_TAPER_LAT = 0.24
KIA_CARNIVAL_HIGHWAY_CENTER_TAPER_LAT_WIDTH = 0.06
KIA_CARNIVAL_HIGHWAY_CENTER_TAPER_SPEED = 28.0
KIA_CARNIVAL_HIGHWAY_CENTER_TAPER_SPEED_WIDTH = 2.0
KIA_CARNIVAL_HIGHWAY_FRICTION_THRESHOLD_GAIN = 0.14
KIA_CARNIVAL_HIGHWAY_FRICTION_CENTER_FADE_MAX = 0.20
KIA_CARNIVAL_HIGHWAY_TRANSITION_TAPER_MAX = 0.28
KIA_CARNIVAL_HIGHWAY_TRANSITION_JERK = 0.45
KIA_CARNIVAL_HIGHWAY_TRANSITION_JERK_WIDTH = 0.15
KIA_CARNIVAL_HIGHWAY_TRANSITION_LAT_CUTOFF = 1.20
KIA_CARNIVAL_HIGHWAY_TRANSITION_LAT_WIDTH = 0.20
KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_MAX = 0.34
KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_SPEED = 15.0
KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_SPEED_WIDTH = 2.0
KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_SPEED_CUTOFF = 23.0
KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_SPEED_CUTOFF_WIDTH = 2.0
KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_LAT = 0.35
KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_LAT_WIDTH = 0.18
KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_JERK = 0.65
KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_JERK_WIDTH = 0.25
KIA_CARNIVAL_UNWIND_FF_REDUCTION_MAX = 0.45
KIA_CARNIVAL_UNWIND_FF_SPEED = 9.0
KIA_CARNIVAL_UNWIND_FF_SPEED_WIDTH = 2.0
KIA_CARNIVAL_UNWIND_FF_SPEED_CUTOFF = 23.0
KIA_CARNIVAL_UNWIND_FF_SPEED_CUTOFF_WIDTH = 2.0
KIA_CARNIVAL_UNWIND_FF_OVERSHOOT = 0.08
KIA_CARNIVAL_UNWIND_FF_OVERSHOOT_WIDTH = 0.06
KIA_CARNIVAL_UNWIND_FF_JERK = 0.45
KIA_CARNIVAL_UNWIND_FF_JERK_WIDTH = 0.20
KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_MAX = 0.28
KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_SPEED = 8.0
KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_SPEED_WIDTH = 2.0
KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_SPEED_CUTOFF = 16.0
KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_SPEED_CUTOFF_WIDTH = 2.5
KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_OVERSHOOT = 0.25
KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_OVERSHOOT_WIDTH = 0.15
KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_JERK = 0.45
KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_JERK_WIDTH = 0.20

TUCSON_4TH_GEN_CENTER_TAPER_MAX = 0.44
TUCSON_4TH_GEN_CENTER_TAPER_LAT = 0.28
TUCSON_4TH_GEN_CENTER_TAPER_LAT_WIDTH = 0.055
TUCSON_4TH_GEN_CENTER_TAPER_SPEED_MAX = 14.0
TUCSON_4TH_GEN_CENTER_TAPER_SPEED_WIDTH = 1.5
TUCSON_4TH_GEN_FRICTION_THRESHOLD_GAIN = 0.28

KIA_FORTE_BASE_LAT_ACCEL_FACTOR_MULT = 1.05
KIA_FORTE_FF_REDUCTION_LEFT = 0.05
KIA_FORTE_FF_REDUCTION_RIGHT = 0.10
KIA_FORTE_FF_ONSET = 0.16
KIA_FORTE_FF_ONSET_WIDTH = 0.06
KIA_FORTE_FF_CUTOFF = 1.20
KIA_FORTE_FF_CUTOFF_WIDTH = 0.36
KIA_FORTE_TRANSITION_SPEED = 9.0
KIA_FORTE_PHASE_SCALE = 0.10
KIA_FORTE_TURN_IN_BOOST_LEFT = 0.10
KIA_FORTE_TURN_IN_BOOST_RIGHT = 0.05
KIA_FORTE_UNWIND_TAPER_LEFT = 0.18
KIA_FORTE_UNWIND_TAPER_RIGHT = 0.02
KIA_FORTE_CRAWL_TURN_IN_FF_BOOST_LEFT = 0.10
KIA_FORTE_CRAWL_TURN_IN_FF_BOOST_RIGHT = 0.14
KIA_FORTE_CRAWL_TURN_IN_FF_SPEED = 4.5
KIA_FORTE_CRAWL_TURN_IN_FF_SPEED_WIDTH = 0.8
KIA_FORTE_CRAWL_TURN_IN_FF_LAT = 0.10
KIA_FORTE_CRAWL_TURN_IN_FF_LAT_WIDTH = 0.05
KIA_FORTE_CENTER_TAPER_MAX = 0.12
KIA_FORTE_CENTER_TAPER_LAT = 0.18
KIA_FORTE_CENTER_TAPER_LAT_WIDTH = 0.04
KIA_FORTE_CENTER_TAPER_SPEED = 22.5
KIA_FORTE_CENTER_TAPER_SPEED_WIDTH = 3.0
KIA_FORTE_FRICTION_CENTER_LAT = 0.18
KIA_FORTE_FRICTION_CENTER_LAT_WIDTH = 0.04
KIA_FORTE_FRICTION_SPEED = 24.0
KIA_FORTE_FRICTION_SPEED_WIDTH = 3.0
KIA_FORTE_FRICTION_CALM_JERK = 0.24
KIA_FORTE_FRICTION_CALM_JERK_WIDTH = 0.08
KIA_FORTE_FRICTION_THRESHOLD_GAIN = 0.10

PALISADE_BASE_LAT_ACCEL_FACTOR_MULT = 0.98
PALISADE_FF_GAIN_LEFT = 0.14
PALISADE_FF_GAIN_RIGHT = 0.12
PALISADE_FF_ONSET = 0.08
PALISADE_FF_ONSET_WIDTH = 0.04
PALISADE_FF_CUTOFF = 1.25
PALISADE_FF_CUTOFF_WIDTH = 0.36
PALISADE_TRANSITION_SPEED = 9.0
PALISADE_PHASE_SCALE = 0.11
PALISADE_TURN_IN_BOOST_LEFT = 0.44
PALISADE_TURN_IN_BOOST_RIGHT = 0.34
PALISADE_UNWIND_TAPER_LEFT = 0.18
PALISADE_UNWIND_TAPER_RIGHT = 0.30
PALISADE_FRICTION_MULT = 1.02
PALISADE_FRICTION_LAT_RISE = 0.20
PALISADE_FRICTION_JERK_RISE = 0.24
PALISADE_TURN_IN_THRESHOLD_REDUCTION_LEFT = 0.18
PALISADE_TURN_IN_THRESHOLD_REDUCTION_RIGHT = 0.14
PALISADE_UNWIND_THRESHOLD_INCREASE_LEFT = 0.14
PALISADE_UNWIND_THRESHOLD_INCREASE_RIGHT = 0.22
PALISADE_TURN_IN_FRICTION_BOOST_LEFT = 0.08
PALISADE_TURN_IN_FRICTION_BOOST_RIGHT = 0.06
PALISADE_UNWIND_FRICTION_REDUCTION_LEFT = 0.12
PALISADE_UNWIND_FRICTION_REDUCTION_RIGHT = 0.20
PALISADE_CENTER_TAPER_MAX = 0.12
PALISADE_CENTER_TAPER_LAT = 0.28
PALISADE_CENTER_TAPER_LAT_WIDTH = 0.055
PALISADE_CENTER_TAPER_SPEED = 12.0
PALISADE_CENTER_TAPER_SPEED_WIDTH = 2.5
PALISADE_CENTER_OUTPUT_TAPER_MAX = 0.18
PALISADE_CENTER_OUTPUT_TAPER_LAT = 0.28
PALISADE_CENTER_OUTPUT_TAPER_LAT_WIDTH = 0.055
PALISADE_CENTER_OUTPUT_TAPER_SPEED = 15.0
PALISADE_CENTER_OUTPUT_TAPER_SPEED_WIDTH = 3.0

GENESIS_G90_LATERAL_TESTING_GROUND_ID = testing_ground.id_4
GENESIS_G90_FF_GAIN_LEFT = 0.32
GENESIS_G90_FF_GAIN_RIGHT = 0.16
GENESIS_G90_FF_ONSET = 0.10
GENESIS_G90_FF_ONSET_WIDTH = 0.05
GENESIS_G90_FF_CUTOFF = 2.35
GENESIS_G90_FF_CUTOFF_WIDTH = 0.48
GENESIS_G90_TRANSITION_SPEED = 10.0
GENESIS_G90_PHASE_SCALE = 0.12
GENESIS_G90_TURN_IN_BOOST_LEFT = 0.66
GENESIS_G90_TURN_IN_BOOST_RIGHT = 0.50
GENESIS_G90_UNWIND_TAPER_LEFT = 0.10
GENESIS_G90_UNWIND_TAPER_RIGHT = 0.55
GENESIS_G90_FRICTION_MULT = 1.02
GENESIS_G90_FRICTION_LAT_RISE = 0.22
GENESIS_G90_FRICTION_JERK_RISE = 0.24
GENESIS_G90_TURN_IN_THRESHOLD_REDUCTION_LEFT = 0.28
GENESIS_G90_TURN_IN_THRESHOLD_REDUCTION_RIGHT = 0.22
GENESIS_G90_UNWIND_THRESHOLD_INCREASE_LEFT = 0.06
GENESIS_G90_UNWIND_THRESHOLD_INCREASE_RIGHT = 0.32
GENESIS_G90_TURN_IN_FRICTION_BOOST_LEFT = 0.16
GENESIS_G90_TURN_IN_FRICTION_BOOST_RIGHT = 0.14
GENESIS_G90_UNWIND_FRICTION_REDUCTION_LEFT = 0.04
GENESIS_G90_UNWIND_FRICTION_REDUCTION_RIGHT = 0.30

IONIQ_5_BASE_LAT_ACCEL_FACTOR_MULT = 1.22
IONIQ_5_FF_ONSET = 0.10
IONIQ_5_FF_ONSET_WIDTH = 0.05
IONIQ_5_FF_CUTOFF = 1.20
IONIQ_5_FF_CUTOFF_WIDTH = 0.30
IONIQ_5_TRANSITION_SPEED = 12.5
IONIQ_5_PHASE_SCALE = 0.10
IONIQ_5_FF_REDUCTION_LEFT = 0.15
IONIQ_5_FF_REDUCTION_RIGHT = 0.25
IONIQ_5_TURN_IN_BOOST_LEFT = 0.10
IONIQ_5_TURN_IN_BOOST_RIGHT = 0.04
IONIQ_5_UNWIND_TAPER_LEFT = 0.92
IONIQ_5_UNWIND_TAPER_RIGHT = 1.04
IONIQ_5_TURN_IN_THRESHOLD_REDUCTION_LEFT = 0.05
IONIQ_5_TURN_IN_THRESHOLD_REDUCTION_RIGHT = 0.03
IONIQ_5_UNWIND_THRESHOLD_INCREASE_LEFT = 0.46
IONIQ_5_UNWIND_THRESHOLD_INCREASE_RIGHT = 0.50
IONIQ_5_TURN_IN_FRICTION_BOOST_LEFT = 0.02
IONIQ_5_TURN_IN_FRICTION_BOOST_RIGHT = 0.01
IONIQ_5_UNWIND_FRICTION_REDUCTION_LEFT = 0.42
IONIQ_5_UNWIND_FRICTION_REDUCTION_RIGHT = 0.44
IONIQ_5_CENTER_TAPER_MAX = 0.18
IONIQ_5_CENTER_TAPER_LAT = 0.16
IONIQ_5_CENTER_TAPER_LAT_WIDTH = 0.04
IONIQ_5_CENTER_TAPER_SPEED = 15.0
IONIQ_5_CENTER_TAPER_SPEED_WIDTH = 2.2
IONIQ_5_SUSTAINED_TURN_IN_FF_BOOST_LEFT = 0.10
IONIQ_5_SUSTAINED_TURN_IN_FF_BOOST_RIGHT = 0.16
IONIQ_5_SUSTAINED_TURN_IN_FF_SPEED = 13.5
IONIQ_5_SUSTAINED_TURN_IN_FF_SPEED_WIDTH = 1.8
IONIQ_5_SUSTAINED_TURN_IN_FF_LAT_START = 1.10
IONIQ_5_SUSTAINED_TURN_IN_FF_LAT_END = 3.60
IONIQ_5_SUSTAINED_TURN_IN_FF_LAT_WIDTH = 0.30
IONIQ_5_LOW_SPEED_OUTPUT_LIMIT_BASE = 0.05
IONIQ_5_LOW_SPEED_OUTPUT_LIMIT_TURN_RELIEF = 0.95
IONIQ_5_LOW_SPEED_OUTPUT_LIMIT_SPEED = 8.0
IONIQ_5_LOW_SPEED_OUTPUT_LIMIT_SPEED_WIDTH = 0.8
IONIQ_5_LOW_SPEED_CENTER_LAT = 0.40
IONIQ_5_LOW_SPEED_CENTER_LAT_WIDTH = 0.10
IONIQ_5_LOW_SPEED_CENTER_JERK = 0.40
IONIQ_5_LOW_SPEED_CENTER_JERK_WIDTH = 0.12
IONIQ_5_FRICTION_JERK_DEADZONE_MAX = 0.36
IONIQ_5_FRICTION_JERK_DEADZONE_LAT = 1.25
IONIQ_5_FRICTION_JERK_DEADZONE_LAT_WIDTH = 0.35
IONIQ_5_FRICTION_JERK_DEADZONE_SPEED = 18.0
IONIQ_5_FRICTION_JERK_DEADZONE_SPEED_WIDTH = 3.0

IONIQ_EV_OLD_BASE_LAT_ACCEL_FACTOR_MULT = 1.16
IONIQ_EV_OLD_FF_REDUCTION_LEFT = 0.16
IONIQ_EV_OLD_FF_REDUCTION_RIGHT = 0.30
IONIQ_EV_OLD_FF_ONSET = 0.14
IONIQ_EV_OLD_FF_ONSET_WIDTH = 0.05
IONIQ_EV_OLD_FF_CUTOFF = 1.10
IONIQ_EV_OLD_FF_CUTOFF_WIDTH = 0.30
IONIQ_EV_OLD_TRANSITION_SPEED = 10.0
IONIQ_EV_OLD_PHASE_SCALE = 0.10
IONIQ_EV_OLD_TURN_IN_BOOST_LEFT = 0.01
IONIQ_EV_OLD_TURN_IN_BOOST_RIGHT = 0.00
IONIQ_EV_OLD_UNWIND_TAPER_LEFT = 0.26
IONIQ_EV_OLD_UNWIND_TAPER_RIGHT = 0.06
IONIQ_EV_OLD_CENTER_TAPER_MAX = 0.14
IONIQ_EV_OLD_CENTER_TAPER_LAT = 0.12
IONIQ_EV_OLD_CENTER_TAPER_LAT_WIDTH = 0.03
IONIQ_EV_OLD_CENTER_TAPER_SPEED = 22.0
IONIQ_EV_OLD_CENTER_TAPER_SPEED_WIDTH = 2.2

IONIQ_6_FF_GAIN_LEFT = 0.045
IONIQ_6_FF_GAIN_RIGHT = 0.015
IONIQ_6_BASE_LAT_ACCEL_FACTOR_MULT = 1.22
IONIQ_6_BASE_FRICTION_THRESHOLD = HKG_CANFD_BASE_FRICTION_THRESHOLD
IONIQ_6_FF_ONSET = 0.10
IONIQ_6_FF_ONSET_WIDTH = 0.04
IONIQ_6_FF_CUTOFF = 0.48
IONIQ_6_FF_CUTOFF_WIDTH = 0.12
IONIQ_6_TRANSITION_SPEED = 10.0
IONIQ_6_PHASE_SCALE = 0.10
IONIQ_6_TURN_IN_BOOST_LEFT = 1.64
IONIQ_6_TURN_IN_BOOST_RIGHT = 2.10
IONIQ_6_UNWIND_TAPER_LEFT = 3.18
IONIQ_6_UNWIND_TAPER_RIGHT = 8.20
IONIQ_6_FRICTION_MULT = 0.928
IONIQ_6_FRICTION_LAT_RISE = 0.20
IONIQ_6_FRICTION_JERK_RISE = 0.24
IONIQ_6_TURN_IN_THRESHOLD_REDUCTION_LEFT = 0.78
IONIQ_6_TURN_IN_THRESHOLD_REDUCTION_RIGHT = 1.42
IONIQ_6_UNWIND_THRESHOLD_INCREASE_LEFT = 3.90
IONIQ_6_UNWIND_THRESHOLD_INCREASE_RIGHT = 10.20
IONIQ_6_TURN_IN_FRICTION_BOOST_LEFT = 0.44
IONIQ_6_TURN_IN_FRICTION_BOOST_RIGHT = 0.94
IONIQ_6_UNWIND_FRICTION_REDUCTION_LEFT = 3.55
IONIQ_6_UNWIND_FRICTION_REDUCTION_RIGHT = 9.10
IONIQ_6_CENTER_TAPER_MAX = 0.082
IONIQ_6_CENTER_TAPER_LAT = 0.24
IONIQ_6_CENTER_TAPER_LAT_WIDTH = 0.025
IONIQ_6_CENTER_TAPER_SPEED = 18.0
IONIQ_6_CENTER_TAPER_SPEED_WIDTH = 2.5
IONIQ_6_HIGHWAY_CENTER_TAPER_MAX = 0.046
IONIQ_6_HIGHWAY_CENTER_TAPER_LAT = 0.10
IONIQ_6_HIGHWAY_CENTER_TAPER_LAT_WIDTH = 0.035
IONIQ_6_HIGHWAY_CENTER_TAPER_SPEED = 24.5
IONIQ_6_HIGHWAY_CENTER_TAPER_SPEED_WIDTH = 1.8
IONIQ_6_HIGHWAY_OUTPUT_TAPER_MAX = 0.10
IONIQ_6_HIGHWAY_OUTPUT_TAPER_LAT = 0.14
IONIQ_6_HIGHWAY_OUTPUT_TAPER_LAT_WIDTH = 0.04
IONIQ_6_HIGHWAY_OUTPUT_TAPER_SPEED = 23.5
IONIQ_6_HIGHWAY_OUTPUT_TAPER_SPEED_WIDTH = 2.0
IONIQ_6_HIGHWAY_TRANSITION_OUTPUT_TAPER_MAX = 0.18
IONIQ_6_HIGHWAY_TRANSITION_OUTPUT_TAPER_LAT = 1.05
IONIQ_6_HIGHWAY_TRANSITION_OUTPUT_TAPER_LAT_WIDTH = 0.22
IONIQ_6_HIGHWAY_TRANSITION_OUTPUT_TAPER_JERK = 0.24
IONIQ_6_HIGHWAY_TRANSITION_OUTPUT_TAPER_JERK_WIDTH = 0.14
IONIQ_6_LOW_MID_CENTER_TAPER_MAX = 0.088
IONIQ_6_LOW_MID_CENTER_TAPER_LAT = 0.28
IONIQ_6_LOW_MID_CENTER_TAPER_LAT_WIDTH = 0.06
IONIQ_6_LOW_MID_CENTER_TAPER_SPEED_MIN = 8.5
IONIQ_6_LOW_MID_CENTER_TAPER_SPEED_MAX = 16.5
IONIQ_6_LOW_MID_CENTER_TAPER_SPEED_WIDTH = 1.5
IONIQ_6_DIRECTIONAL_TAPER_LAT_START = 0.19
IONIQ_6_DIRECTIONAL_TAPER_LAT_END = 0.90
IONIQ_6_DIRECTIONAL_TAPER_LAT_WIDTH = 0.06
IONIQ_6_DIRECTIONAL_TAPER_BASE_LEFT = 0.11
IONIQ_6_DIRECTIONAL_TAPER_BASE_RIGHT = 0.45
IONIQ_6_DIRECTIONAL_TAPER_UNWIND_LEFT = 1.10
IONIQ_6_DIRECTIONAL_TAPER_UNWIND_RIGHT = 2.10
IONIQ_6_DIRECTIONAL_TAPER_FLOOR_LEFT = 0.48
IONIQ_6_DIRECTIONAL_TAPER_FLOOR_RIGHT = 0.52
IONIQ_6_DIRECTIONAL_TAPER_UNWIND_FLOOR_LEFT = 0.20
IONIQ_6_DIRECTIONAL_TAPER_UNWIND_FLOOR_RIGHT = 0.10
IONIQ_6_DIRECTIONAL_TAPER_JERK_ONSET = 1.00
IONIQ_6_DIRECTIONAL_TAPER_JERK_WIDTH = 0.30
# Unwind detection needs a softer phase transition and time smoothing than the shared
# PHASE_SCALE: desired lateral jerk noise in a sustained curve (~+/-1-2 m/s^3) otherwise
# chatters the taper between its base value and its floor at ~0.5 Hz (felt as notchy
# steering in highway sweepers).
IONIQ_6_DIRECTIONAL_TAPER_PHASE_SCALE = 0.45
IONIQ_6_DIRECTIONAL_TAPER_FILTER_RC = 0.4
IONIQ_6_DIRECTIONAL_TAPER_LOW_SPEED_RELIEF = 0.98
IONIQ_6_DIRECTIONAL_TAPER_LOW_SPEED_RELIEF_SPEED = 11.2
IONIQ_6_DIRECTIONAL_TAPER_LOW_SPEED_RELIEF_SPEED_WIDTH = 1.5
IONIQ_6_DIRECTIONAL_TAPER_LOW_SPEED_RELIEF_LAT = 0.10
IONIQ_6_DIRECTIONAL_TAPER_LOW_SPEED_RELIEF_LAT_WIDTH = 0.06
IONIQ_6_UNWIND_HIGH_SPEED_SPEED = 23.2
IONIQ_6_UNWIND_HIGH_SPEED_SPEED_WIDTH = 1.7
IONIQ_6_CRAWL_TURN_IN_FF_BOOST_LEFT = 0.18
IONIQ_6_CRAWL_TURN_IN_FF_BOOST_RIGHT = 0.24
IONIQ_6_CRAWL_TURN_IN_FF_SPEED = 5.3
IONIQ_6_CRAWL_TURN_IN_FF_SPEED_WIDTH = 1.0
IONIQ_6_CRAWL_TURN_IN_FF_LAT = 0.06
IONIQ_6_CRAWL_TURN_IN_FF_LAT_WIDTH = 0.035
IONIQ_6_LOW_SPEED_ANGLE_ASSIST_MAX_TORQUE = 0.46
IONIQ_6_LOW_SPEED_ANGLE_ASSIST_SPEED = 3.25
IONIQ_6_LOW_SPEED_ANGLE_ASSIST_SPEED_WIDTH = 0.45
IONIQ_6_LOW_SPEED_ANGLE_ASSIST_ERROR = 1.9
IONIQ_6_LOW_SPEED_ANGLE_ASSIST_ERROR_WIDTH = 1.20
IONIQ_6_LOW_SPEED_ANGLE_ASSIST_DESIRED_ANGLE = 5.5
IONIQ_6_LOW_SPEED_ANGLE_ASSIST_DESIRED_ANGLE_WIDTH = 2.4
IONIQ_6_LOW_SPEED_ANGLE_ASSIST_TRACK_RATIO_START = 0.66
IONIQ_6_LOW_SPEED_ANGLE_ASSIST_TRACK_RATIO_WIDTH = 0.12
IONIQ_6_LOW_SPEED_ANGLE_ASSIST_TRACK_RATIO_FLOOR = 0.26
IONIQ_6_LOW_SPEED_ANGLE_ASSIST_ADD_BP = [0.0, 0.35, 0.65, 1.0]
IONIQ_6_LOW_SPEED_ANGLE_ASSIST_ADD_V = [1.0, 1.0, 0.88, 0.08]
IONIQ_6_LOW_SPEED_UNWIND_ASSIST_MAX_TORQUE = 0.30
IONIQ_6_LOW_SPEED_UNWIND_ASSIST_SPEED = 3.35
IONIQ_6_LOW_SPEED_UNWIND_ASSIST_SPEED_WIDTH = 0.50
IONIQ_6_LOW_SPEED_UNWIND_ASSIST_ERROR = 1.6
IONIQ_6_LOW_SPEED_UNWIND_ASSIST_ERROR_WIDTH = 0.95
IONIQ_6_LOW_SPEED_UNWIND_ASSIST_ACTUAL_ANGLE = 10.5
IONIQ_6_LOW_SPEED_UNWIND_ASSIST_ACTUAL_ANGLE_WIDTH = 4.0
IONIQ_6_LOW_SPEED_UNWIND_ASSIST_BLEND = 0.52
IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_BOOST = 0.10
IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_SPEED = 18.0
IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_SPEED_WIDTH = 2.5
IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_LAT_START = 0.06
IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_LAT_END = 0.22
IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_LAT_WIDTH = 0.035
IONIQ_6_CURVY_SPEED_MIN = 7.2
IONIQ_6_CURVY_SPEED_MAX = 21.5
IONIQ_6_CURVY_SPEED_MIN_WIDTH = 1.1
IONIQ_6_CURVY_SPEED_MAX_WIDTH = 1.8
IONIQ_6_CURVY_UNWIND_EXTRA_REDUCTION_LEFT = 0.26
IONIQ_6_CURVY_UNWIND_EXTRA_REDUCTION_RIGHT = 0.30
IONIQ_6_CURVY_UNWIND_FLOOR_RELIEF_LEFT = 0.22
IONIQ_6_CURVY_UNWIND_FLOOR_RELIEF_RIGHT = 0.28
IONIQ_6_CURVY_UNWIND_LAT_START = 0.45
IONIQ_6_CURVY_UNWIND_LAT_END = 3.6
IONIQ_6_CURVY_UNWIND_LAT_ONSET_WIDTH = 0.14
IONIQ_6_CURVY_UNWIND_LAT_CUTOFF_WIDTH = 0.55
IONIQ_6_CURVY_RIGHT_UNWIND_JERK_ONSET = 0.40
IONIQ_6_CURVY_RIGHT_UNWIND_JERK_WIDTH = 0.22
IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_MIN = 11.5
IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_MAX = 20.5
IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_WIDTH = 1.2
IONIQ_6_CURVY_TURN_IN_TRIM_LEFT = 0.08
IONIQ_6_CURVY_TURN_IN_TRIM_RIGHT = 0.09
IONIQ_6_CURVY_TURN_IN_TRIM_LAT_START = 1.0
IONIQ_6_CURVY_TURN_IN_TRIM_LAT_END = 2.5
IONIQ_6_CURVY_TURN_IN_TRIM_LAT_ONSET_WIDTH = 0.18
IONIQ_6_CURVY_TURN_IN_TRIM_LAT_CUTOFF_WIDTH = 0.30
IONIQ_6_2023_UNWIND_FF_REDUCTION_MAX = 0.24
IONIQ_6_2023_UNWIND_FF_OVERSHOOT = 0.15
IONIQ_6_2023_UNWIND_FF_OVERSHOOT_WIDTH = 0.18
IONIQ_6_2023_UNWIND_FF_JERK = 0.10
IONIQ_6_2023_UNWIND_FF_JERK_WIDTH = 0.10
IONIQ_6_2023_UNWIND_FF_SPEED_ONSET = 8.0
IONIQ_6_2023_UNWIND_FF_SPEED_ONSET_WIDTH = 2.5
IONIQ_6_2023_UNWIND_FF_SPEED_CUTOFF = 23.5
IONIQ_6_2023_UNWIND_FF_SPEED_CUTOFF_WIDTH = 2.0
IONIQ_6_LOW_SPEED_PID_RESET_SPEED = 0.1 * CV.MPH_TO_MS
# Friction compensation near zero lateral accel amplifies planner jerk noise into a slow
# (~0.5 Hz) weave on straights: the 0.09/0.39 small-signal slope plus the jerk feed acts as
# extra P/D gain right where there is no breakaway torque to overcome. Deadzone the jerk
# feed below straight-line noise levels and fade friction near center at highway speed.
IONIQ_6_FRICTION_JERK_DEADZONE = 0.30
IONIQ_6_FRICTION_CENTER_FADE_MAX = 0.50
IONIQ_6_FRICTION_CENTER_FADE_LAT = 0.15
IONIQ_6_FRICTION_CENTER_FADE_LAT_WIDTH = 0.06
IONIQ_6_FRICTION_CENTER_FADE_SPEED = 18.0
IONIQ_6_FRICTION_CENTER_FADE_SPEED_WIDTH = 2.5
# Newer Ioniq 6 highway center-chatter correction; activation is firmware-gated.
IONIQ_6_2025_FRICTION_SCALE_MULT = 0.80
IONIQ_6_2025_FRICTION_JERK_DEADZONE = 0.45
IONIQ_6_2025_CENTER_OUTPUT_TAPER_MAX = 0.32
IONIQ_6_2025_CENTER_OUTPUT_TAPER_LAT = 0.35
IONIQ_6_2025_CENTER_OUTPUT_TAPER_LAT_WIDTH = 0.10
IONIQ_6_2025_CENTER_OUTPUT_TAPER_SPEED = 22.0
IONIQ_6_2025_CENTER_OUTPUT_TAPER_SPEED_WIDTH = 2.5
IONIQ_6_2025_LOW_SPEED_CENTER_ERROR_SCALE = 0.68
IONIQ_6_2025_LOW_SPEED_CENTER_FRICTION_SCALE = 0.72
IONIQ_6_2025_LOW_SPEED_CENTER_SPEED = 5.0
IONIQ_6_2025_LOW_SPEED_CENTER_SPEED_WIDTH = 1.3
IONIQ_6_2025_LOW_SPEED_CENTER_LAT = 0.22
IONIQ_6_2025_LOW_SPEED_CENTER_LAT_WIDTH = 0.10
IONIQ_6_2025_LOW_SPEED_CENTER_JERK = 0.30
IONIQ_6_2025_LOW_SPEED_CENTER_JERK_WIDTH = 0.13
IONIQ_6_2025_LOW_SPEED_OUTPUT_LIMIT_BASE = 0.22
IONIQ_6_2025_LOW_SPEED_OUTPUT_LIMIT_TURN_RELIEF = 0.50
IONIQ_6_2025_LOW_SPEED_OUTPUT_LIMIT_SPEED_RELIEF = 0.20
IONIQ_6_2025_LOW_SPEED_OUTPUT_LIMIT_SPEED = 6.5
IONIQ_6_2025_LOW_SPEED_OUTPUT_LIMIT_SPEED_WIDTH = 1.5
IONIQ_6_HEAVY_DIRECTIONAL_TAPER_LAT_START = 0.90
IONIQ_6_HEAVY_DIRECTIONAL_TAPER_LAT_WIDTH = 0.18
IONIQ_6_HEAVY_DIRECTIONAL_TAPER_BASE_LEFT = 0.03
IONIQ_6_HEAVY_DIRECTIONAL_TAPER_BASE_RIGHT = 0.11
IONIQ_6_HEAVY_DIRECTIONAL_TAPER_UNWIND_LEFT = 0.40
IONIQ_6_HEAVY_DIRECTIONAL_TAPER_UNWIND_RIGHT = 0.55
IONIQ_6_OUTPUT_TAPER_SPEED = 8.5
IONIQ_6_OUTPUT_TAPER_SPEED_WIDTH = 2.5
IONIQ_6_OUTPUT_CENTER_TAPER_BLEND = 0.90
IONIQ_6_OUTPUT_DIRECTIONAL_TAPER_BLEND = 0.97

KIA_EV6_LATERAL_TESTING_GROUND_ID = testing_ground.id_6
KIA_EV6_LATERAL_TESTING_GROUND_VARIANT = "C"
KIA_EV6_FF_GAIN_LEFT = 0.12
KIA_EV6_FF_GAIN_RIGHT = 0.17
KIA_EV6_FF_ONSET = 0.08
KIA_EV6_FF_ONSET_WIDTH = 0.04
KIA_EV6_FF_CUTOFF = 1.90
KIA_EV6_FF_CUTOFF_WIDTH = 0.40
KIA_EV6_TRANSITION_SPEED = 14.5
KIA_EV6_PHASE_SCALE = 0.09
KIA_EV6_TURN_IN_BOOST_LEFT = 0.54
KIA_EV6_TURN_IN_BOOST_RIGHT = 0.60
KIA_EV6_UNWIND_TAPER_LEFT = 0.56
KIA_EV6_UNWIND_TAPER_RIGHT = 0.54
KIA_EV6_BASE_UNWIND_TAPER_LEFT = 0.10
KIA_EV6_BASE_UNWIND_TAPER_RIGHT = 0.13
KIA_EV6_JWARM_BASE_TURN_IN_BOOST_LEFT = 0.12
KIA_EV6_JWARM_BASE_TURN_IN_BOOST_RIGHT = 0.14
KIA_EV6_JWARM_BASE_UNWIND_TAPER_LEFT = 0.15
KIA_EV6_JWARM_BASE_UNWIND_TAPER_RIGHT = 0.16
KIA_EV6_JWARM_PHASE_STABILITY_MAX_REDUCTION = 0.25
KIA_EV6_JWARM_PHASE_STABILITY_SPEED = 10.0
KIA_EV6_JWARM_PHASE_STABILITY_SPEED_WIDTH = 1.8
KIA_EV6_JWARM_PHASE_STABILITY_JERK = 0.70
KIA_EV6_JWARM_PHASE_STABILITY_JERK_WIDTH = 0.18
KIA_EV6_FRICTION_MULT = 1.01
KIA_EV6_FRICTION_LAT_RISE = 0.18
KIA_EV6_FRICTION_JERK_RISE = 0.22
KIA_EV6_TURN_IN_THRESHOLD_REDUCTION_LEFT = 0.34
KIA_EV6_TURN_IN_THRESHOLD_REDUCTION_RIGHT = 0.40
KIA_EV6_UNWIND_THRESHOLD_INCREASE_LEFT = 0.28
KIA_EV6_UNWIND_THRESHOLD_INCREASE_RIGHT = 0.24
KIA_EV6_TURN_IN_FRICTION_BOOST_LEFT = 0.18
KIA_EV6_TURN_IN_FRICTION_BOOST_RIGHT = 0.24
KIA_EV6_UNWIND_FRICTION_REDUCTION_LEFT = 0.28
KIA_EV6_UNWIND_FRICTION_REDUCTION_RIGHT = 0.22
KIA_EV6_CENTER_TAPER_MAX = 0.12
KIA_EV6_CENTER_TAPER_LAT = 0.16
KIA_EV6_CENTER_TAPER_LAT_WIDTH = 0.04
KIA_EV6_CENTER_TAPER_SPEED = 17.0
KIA_EV6_CENTER_TAPER_SPEED_WIDTH = 2.8
KIA_EV6_CENTER_FRICTION_THRESHOLD_GAIN = 0.14
KIA_EV6_CENTER_FRICTION_THRESHOLD_LAT = 0.30
KIA_EV6_CENTER_FRICTION_THRESHOLD_LAT_WIDTH = 0.07
KIA_EV6_CENTER_FRICTION_THRESHOLD_SPEED = 18.0
KIA_EV6_CENTER_FRICTION_THRESHOLD_SPEED_WIDTH = 2.5
KIA_EV6_LOW_SPEED_CENTER_TAPER_MAX = 0.19
KIA_EV6_LOW_SPEED_CENTER_TAPER_LAT = 0.08
KIA_EV6_LOW_SPEED_CENTER_TAPER_LAT_WIDTH = 0.02
KIA_EV6_LOW_SPEED_CENTER_TAPER_SPEED_MAX = 8.5
KIA_EV6_LOW_SPEED_CENTER_TAPER_SPEED_WIDTH = 1.4
KIA_EV6_CENTER_OUTPUT_TAPER_MAX = 0.14
KIA_EV6_CENTER_OUTPUT_TAPER_LAT = 0.30
KIA_EV6_CENTER_OUTPUT_TAPER_LAT_WIDTH = 0.08
KIA_EV6_CENTER_OUTPUT_TAPER_SPEED = 12.0
KIA_EV6_CENTER_OUTPUT_TAPER_SPEED_WIDTH = 2.4

VOLT_PLEXY_LATERAL_TESTING_GROUND_ID = testing_ground.id_7
VOLT_PLEXY_FF_EXTRA_MULT_LEFT = 1.07
VOLT_PLEXY_FF_EXTRA_MULT_RIGHT = 1.12
VOLT_PLEXY_FRICTION_SCALE_MULT_LEFT = 1.04
VOLT_PLEXY_FRICTION_SCALE_MULT_RIGHT = 1.05
VOLT_PLEXY_FRICTION_THRESHOLD_MULT_LEFT = 0.97
VOLT_PLEXY_FRICTION_THRESHOLD_MULT_RIGHT = 0.96
VOLT_PLEXY_CENTER_TAPER_REDUCTION_MULT = 1.02
PRIUS_TRANSITION_SPEED = 11.0
PRIUS_PHASE_SCALE = 0.09
PRIUS_FF_GAIN_LEFT = 0.06
PRIUS_FF_GAIN_RIGHT = 0.07
PRIUS_FF_ONSET = 0.15
PRIUS_FF_ONSET_WIDTH = 0.08
PRIUS_FF_CUTOFF = 1.30
PRIUS_FF_CUTOFF_WIDTH = 0.32
PRIUS_FRICTION_LAT_RISE = 0.18
PRIUS_FRICTION_JERK_RISE = 0.22
PRIUS_TURN_IN_BOOST_LEFT = 0.24
PRIUS_TURN_IN_BOOST_RIGHT = 0.22
PRIUS_UNWIND_TAPER_LEFT = 0.42
PRIUS_UNWIND_TAPER_RIGHT = 0.62
PRIUS_TURN_IN_THRESHOLD_REDUCTION_LEFT = 0.14
PRIUS_TURN_IN_THRESHOLD_REDUCTION_RIGHT = 0.14
PRIUS_UNWIND_THRESHOLD_INCREASE_LEFT = 0.40
PRIUS_UNWIND_THRESHOLD_INCREASE_RIGHT = 0.56
PRIUS_TURN_IN_FRICTION_BOOST_LEFT = 0.06
PRIUS_TURN_IN_FRICTION_BOOST_RIGHT = 0.06
PRIUS_UNWIND_FRICTION_REDUCTION_LEFT = 0.22
PRIUS_UNWIND_FRICTION_REDUCTION_RIGHT = 0.30
PRIUS_CENTER_TAPER_MAX = 0.155
PRIUS_CENTER_TAPER_LAT = 0.24
PRIUS_CENTER_TAPER_LAT_WIDTH = 0.035
PRIUS_CENTER_TAPER_SPEED = 18.0
PRIUS_CENTER_TAPER_SPEED_WIDTH = 2.2
PRIUS_CENTER_FRICTION_THRESHOLD_GAIN = 0.08
PRIUS_CENTER_FRICTION_THRESHOLD_LAT = 0.30
PRIUS_CENTER_FRICTION_THRESHOLD_LAT_WIDTH = 0.07
PRIUS_CENTER_FRICTION_THRESHOLD_SPEED = 18.0
PRIUS_CENTER_FRICTION_THRESHOLD_SPEED_WIDTH = 2.2
PRIUS_FRICTION_JERK_DEADZONE_MAX = 0.24
PRIUS_STANDARD_FRICTION_JERK_DEADZONE_MAX = 0.30
PRIUS_FRICTION_JERK_DEADZONE_LAT = 0.30
PRIUS_FRICTION_JERK_DEADZONE_LAT_WIDTH = 0.07
PRIUS_FRICTION_JERK_DEADZONE_SPEED = 18.0
PRIUS_FRICTION_JERK_DEADZONE_SPEED_WIDTH = 2.2
PRIUS_HIGH_SPEED_OUTPUT_TAPER_MAX = 0.06
PRIUS_STANDARD_HIGH_SPEED_OUTPUT_TAPER_MAX = 0.10
PRIUS_HIGH_SPEED_OUTPUT_TAPER_LAT = 0.30
PRIUS_HIGH_SPEED_OUTPUT_TAPER_LAT_WIDTH = 0.35
PRIUS_HIGH_SPEED_OUTPUT_TAPER_SPEED = 22.0
PRIUS_HIGH_SPEED_OUTPUT_TAPER_SPEED_WIDTH = 2.5

CAMRY_CENTER_FRICTION_THRESHOLD_GAIN = 0.09
CAMRY_CENTER_FRICTION_THRESHOLD_LAT = 0.22
CAMRY_CENTER_FRICTION_THRESHOLD_LAT_WIDTH = 0.06
CAMRY_CENTER_FRICTION_THRESHOLD_SPEED = 18.0
CAMRY_CENTER_FRICTION_THRESHOLD_SPEED_WIDTH = 3.0
CAMRY_UNWIND_FF_REDUCTION = 0.08
CAMRY_UNWIND_LAT_ONSET = 0.18
CAMRY_UNWIND_LAT_WIDTH = 0.07
CAMRY_UNWIND_SPEED_ONSET = 15.0
CAMRY_UNWIND_SPEED_WIDTH = 3.0

RAV4_PRIME_PHASE_SCALE = 0.12
RAV4_PRIME_TURN_IN_FF_BOOST_LEFT = 0.055
RAV4_PRIME_TURN_IN_FF_BOOST_RIGHT = 0.040
RAV4_PRIME_UNWIND_FF_REDUCTION_LEFT = 0.18
RAV4_PRIME_UNWIND_FF_REDUCTION_RIGHT = 0.19
RAV4_PRIME_UNWIND_FRICTION_REDUCTION_LEFT = 0.19
RAV4_PRIME_UNWIND_FRICTION_REDUCTION_RIGHT = 0.20
RAV4_PRIME_UNWIND_OUTPUT_REDUCTION_LEFT = 0.185
RAV4_PRIME_UNWIND_OUTPUT_REDUCTION_RIGHT = 0.225
RAV4_PRIME_HARD_UNWIND_OUTPUT_REDUCTION_LEFT = 0.04
RAV4_PRIME_HARD_UNWIND_OUTPUT_REDUCTION_RIGHT = 0.025
RAV4_PRIME_HARD_UNWIND_LAT = 1.25
RAV4_PRIME_HARD_UNWIND_LAT_WIDTH = 0.20
RAV4_PRIME_FRICTION_THRESHOLD_GAIN = 0.30
RAV4_PRIME_FRICTION_CENTER_LAT = 0.30
RAV4_PRIME_FRICTION_CENTER_LAT_WIDTH = 0.07
RAV4_PRIME_SPEED_ONSET = 5.0
RAV4_PRIME_SPEED_ONSET_WIDTH = 1.5
RAV4_PRIME_SPEED_MAX = 20.0
RAV4_PRIME_SPEED_MAX_WIDTH = 2.5

SIENNA_4TH_GEN_PHASE_SCALE = 0.12
SIENNA_4TH_GEN_TURN_IN_FF_BOOST = 0.06
SIENNA_4TH_GEN_TURN_IN_LAT = 0.24
SIENNA_4TH_GEN_TURN_IN_LAT_WIDTH = 0.08
SIENNA_4TH_GEN_TURN_IN_SPEED_ONSET = 3.0
SIENNA_4TH_GEN_TURN_IN_SPEED_WIDTH = 1.5
SIENNA_4TH_GEN_TURN_IN_SPEED_MAX = 20.0
SIENNA_4TH_GEN_TURN_IN_SPEED_MAX_WIDTH = 2.0
SIENNA_4TH_GEN_FRICTION_THRESHOLD_GAIN = 0.30
SIENNA_4TH_GEN_FRICTION_CENTER_LAT = 0.30
SIENNA_4TH_GEN_FRICTION_CENTER_LAT_WIDTH = 0.07
SIENNA_4TH_GEN_FRICTION_SPEED_ONSET = 3.0
SIENNA_4TH_GEN_FRICTION_SPEED_WIDTH = 1.5
SIENNA_4TH_GEN_FRICTION_SPEED_MAX = 14.0
SIENNA_4TH_GEN_FRICTION_SPEED_MAX_WIDTH = 2.0
SIENNA_4TH_GEN_HIGH_SPEED_FRICTION_THRESHOLD_GAIN = 0.14
SIENNA_4TH_GEN_HIGH_SPEED_FRICTION_SPEED_ONSET = 18.0
SIENNA_4TH_GEN_HIGH_SPEED_FRICTION_SPEED_WIDTH = 2.5
SIENNA_4TH_GEN_CENTER_TAPER_MAX = 0.12
SIENNA_4TH_GEN_CENTER_TAPER_LAT = 0.20
SIENNA_4TH_GEN_CENTER_TAPER_LAT_WIDTH = 0.06
SIENNA_4TH_GEN_CENTER_TAPER_SPEED_MAX = 13.0
SIENNA_4TH_GEN_CENTER_TAPER_SPEED_WIDTH = 2.0
SIENNA_4TH_GEN_HIGH_SPEED_CENTER_TAPER_MAX = 0.16
SIENNA_4TH_GEN_HIGH_SPEED_CENTER_TAPER_ONSET = 15.0
SIENNA_4TH_GEN_HIGH_SPEED_CENTER_TAPER_ONSET_WIDTH = 2.0
SIENNA_4TH_GEN_HIGH_SPEED_CENTER_TAPER_MAX_SPEED = 27.0
SIENNA_4TH_GEN_HIGH_SPEED_CENTER_TAPER_MAX_SPEED_WIDTH = 3.0
SIENNA_4TH_GEN_HIGH_SPEED_OUTPUT_TAPER_MAX = 0.10
SIENNA_4TH_GEN_HIGH_SPEED_OUTPUT_TAPER_ONSET = 18.0
SIENNA_4TH_GEN_HIGH_SPEED_OUTPUT_TAPER_ONSET_WIDTH = 2.0
SIENNA_4TH_GEN_HIGH_SPEED_OUTPUT_TAPER_MAX_SPEED = 27.0
SIENNA_4TH_GEN_HIGH_SPEED_OUTPUT_TAPER_MAX_SPEED_WIDTH = 3.0

TOYOTA_COROLLA_TSS2_PHASE_SCALE = 0.12
TOYOTA_COROLLA_TSS2_TURN_IN_FF_BOOST = 0.035
TOYOTA_COROLLA_TSS2_UNWIND_FF_REDUCTION = 0.06
TOYOTA_COROLLA_TSS2_CURVE_LAT_ONSET = 0.24
TOYOTA_COROLLA_TSS2_CURVE_LAT_WIDTH = 0.10
TOYOTA_COROLLA_TSS2_SPEED_ONSET = 4.0
TOYOTA_COROLLA_TSS2_SPEED_ONSET_WIDTH = 1.5
TOYOTA_COROLLA_TSS2_SPEED_CUTOFF = 24.0
TOYOTA_COROLLA_TSS2_SPEED_CUTOFF_WIDTH = 3.0
TOYOTA_COROLLA_TSS2_CENTER_OUTPUT_TAPER_MAX = 0.30
TOYOTA_COROLLA_TSS2_CENTER_OUTPUT_TAPER_LAT = 0.18
TOYOTA_COROLLA_TSS2_CENTER_OUTPUT_TAPER_LAT_WIDTH = 0.08
TOYOTA_COROLLA_TSS2_CENTER_OUTPUT_TAPER_SPEED = 4.5
TOYOTA_COROLLA_TSS2_CENTER_OUTPUT_TAPER_SPEED_WIDTH = 1.5
TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_GAIN = 0.12
TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_SPEED_ONSET = 12.0
TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_SPEED_WIDTH = 2.0
TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_SPEED_CUTOFF = 25.0
TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_SPEED_CUTOFF_WIDTH = 3.0
TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_LAT = 0.24
TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_LAT_WIDTH = 0.10
TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_JERK = 0.25
TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_JERK_WIDTH = 0.10

TOYOTA_HIGHLANDER_TSS2_PHASE_SCALE = 0.12
TOYOTA_HIGHLANDER_TSS2_UNWIND_FF_REDUCTION = 0.10
TOYOTA_HIGHLANDER_TSS2_UNWIND_FRICTION_THRESHOLD_GAIN = 0.16
TOYOTA_HIGHLANDER_TSS2_UNWIND_FRICTION_SCALE_REDUCTION = 0.10
TOYOTA_HIGHLANDER_TSS2_UNWIND_OUTPUT_REDUCTION = 0.15
TOYOTA_HIGHLANDER_TSS2_UNWIND_LAT_ONSET = 0.20
TOYOTA_HIGHLANDER_TSS2_UNWIND_LAT_WIDTH = 0.08
TOYOTA_HIGHLANDER_TSS2_UNWIND_SPEED_ONSET = 3.0
TOYOTA_HIGHLANDER_TSS2_UNWIND_SPEED_WIDTH = 1.5
TOYOTA_HIGHLANDER_TSS2_UNWIND_SPEED_MAX = 15.0
TOYOTA_HIGHLANDER_TSS2_UNWIND_SPEED_MAX_WIDTH = 2.0

LEXUS_IS_PHASE_SCALE = 0.10
LEXUS_IS_TURN_IN_FF_BOOST_LEFT = 0.06
LEXUS_IS_TURN_IN_FF_BOOST_RIGHT = 0.06
LEXUS_IS_UNWIND_FF_REDUCTION_LEFT = 0.13
LEXUS_IS_UNWIND_FF_REDUCTION_RIGHT = 0.20
LEXUS_IS_UNWIND_LAT_ONSET = 0.18
LEXUS_IS_UNWIND_LAT_WIDTH = 0.07
LEXUS_IS_UNWIND_SPEED_ONSET = 9.0
LEXUS_IS_UNWIND_SPEED_WIDTH = 2.0

SUBARU_IMPREZA_PID_TAPER_START_DEG = 0.75
SUBARU_IMPREZA_PID_TAPER_FULL_DEG = 4.0
SUBARU_IMPREZA_PID_TAPER_MIN = 0.58

RAV4_TSS2_CARS = (
  TOYOTA_CAR.TOYOTA_RAV4_TSS2,
)
RAV4_TSS2_PID_LOW_SPEED = 12.0 * CV.MPH_TO_MS
RAV4_TSS2_PID_LOW_SPEED_WIDTH = 2.0 * CV.MPH_TO_MS
RAV4_TSS2_PID_CENTER_ANGLE = 14.0
RAV4_TSS2_PID_CENTER_ANGLE_WIDTH = 3.0
RAV4_TSS2_PID_OUTPUT_SCALE_MIN = 0.62
RAV4_TSS2_PID_OUTPUT_ALPHA_MIN = 0.28

HONDA_CRV_5G_PID_LOW_SPEED = 18.0 * CV.MPH_TO_MS
HONDA_CRV_5G_PID_LOW_SPEED_WIDTH = 3.0 * CV.MPH_TO_MS
HONDA_CRV_5G_PID_CENTER_ANGLE = 14.0
HONDA_CRV_5G_PID_CENTER_ANGLE_WIDTH = 3.0
HONDA_CRV_5G_PID_OUTPUT_SCALE_MIN = 0.62
HONDA_CRV_5G_PID_OUTPUT_ALPHA_MIN = 0.28

RAV4_TSS2_CENTER_FRICTION_THRESHOLD_GAIN = 0.14
RAV4_TSS2_CENTER_FRICTION_LAT = 0.30
RAV4_TSS2_CENTER_FRICTION_LAT_WIDTH = 0.08
RAV4_TSS2_CENTER_SPEED = 13.0
RAV4_TSS2_CENTER_SPEED_WIDTH = 3.0
RAV4_TSS2_CENTER_OUTPUT_TAPER_MAX = 0.12
RAV4_TSS2_CENTER_OUTPUT_LAT = 0.30
RAV4_TSS2_CENTER_OUTPUT_LAT_WIDTH = 0.08

RAM_1500_TRANSITION_TAPER_MAX = 0.34
RAM_1500_TRANSITION_SPEED_ONSET = 10.0
RAM_1500_TRANSITION_SPEED_FULL = 15.0
RAM_1500_TRANSITION_JERK_ONSET = 0.35
RAM_1500_TRANSITION_JERK_FULL = 1.10
RAM_1500_TRANSITION_LAT_FADE_START = 0.65
RAM_1500_TRANSITION_LAT_FADE_END = 1.85
RAM_1500_MAX_LAT_JERK_UP = 2.10
RAM_1500_PHASE_SCALE = 0.12
RAM_1500_PHASE_SPEED_ONSET = 8.0
RAM_1500_PHASE_SPEED_FULL = 15.0
RAM_1500_PHASE_LAT_ONSET = 0.25
RAM_1500_PHASE_LAT_WIDTH = 0.12
RAM_1500_TURN_IN_FF_BOOST = 0.06
RAM_1500_UNWIND_FF_REDUCTION = 0.05
RAM_1500_CENTER_OUTPUT_TAPER_MAX = 0.12
RAM_1500_CENTER_OUTPUT_TAPER_LAT = 0.24
RAM_1500_CENTER_OUTPUT_TAPER_LAT_WIDTH = 0.08
RAM_1500_CENTER_OUTPUT_TAPER_SPEED_ONSET = 5.5
RAM_1500_CENTER_OUTPUT_TAPER_SPEED_ONSET_WIDTH = 1.5
RAM_1500_CENTER_OUTPUT_TAPER_SPEED_MAX = 16.0
RAM_1500_CENTER_OUTPUT_TAPER_SPEED_MAX_WIDTH = 2.0
RAM_1500_UNWIND_OUTPUT_TAPER_MAX = 0.18
RAM_1500_UNWIND_OUTPUT_SPEED_ONSET = 20.0
RAM_1500_UNWIND_OUTPUT_SPEED_FULL = 29.0
RAM_1500_UNWIND_OUTPUT_JERK_ONSET = 0.50
RAM_1500_UNWIND_OUTPUT_JERK_FULL = 1.80
RAM_1500_UNWIND_OUTPUT_LAT_ONSET = 0.65
RAM_1500_UNWIND_OUTPUT_LAT_WIDTH = 0.30

# The Kona route is exceptionally accurate below highway speed, but Pop V2
# reverses the requested lateral acceleration roughly once per second at
# 29-30 m/s. Fade only rapid, high-speed turn-building torque so the EPS has
# less stored torque to unwind while leaving steady curves and counter-torque.
KONA_NON_SCC_TRANSITION_TURN_IN_TAPER_MAX = 0.24
KONA_NON_SCC_TRANSITION_UNWIND_TAPER_MAX = 0.42
KONA_NON_SCC_TRANSITION_SPEED_ONSET = 22.0
KONA_NON_SCC_TRANSITION_SPEED_FULL = 29.0
KONA_NON_SCC_TRANSITION_JERK_ONSET = 0.35
KONA_NON_SCC_TRANSITION_JERK_FULL = 1.20
KONA_NON_SCC_TRANSITION_LAT_FADE_START = 0.45
KONA_NON_SCC_TRANSITION_LAT_FADE_END = 1.60
KONA_NON_SCC_CENTER_TAPER_MAX = 0.14
KONA_NON_SCC_CENTER_TAPER_LAT = 0.28
KONA_NON_SCC_CENTER_TAPER_SPEED_ONSET = 12.0
KONA_NON_SCC_CENTER_TAPER_SPEED_FULL = 24.0
KONA_NON_SCC_CENTER_FRICTION_THRESHOLD_GAIN = 0.14
KONA_NON_SCC_CENTER_FRICTION_THRESHOLD_LAT = 0.28
KONA_NON_SCC_CENTER_FRICTION_THRESHOLD_LAT_WIDTH = 0.07
KONA_NON_SCC_CENTER_FRICTION_THRESHOLD_SPEED_ONSET = 11.0
KONA_NON_SCC_CENTER_FRICTION_THRESHOLD_SPEED_WIDTH = 2.5
KONA_EV_2022_CENTER_FRICTION_THRESHOLD_GAIN = 0.08
KONA_EV_2022_CENTER_FRICTION_THRESHOLD_LAT = 0.20
KONA_EV_2022_CENTER_FRICTION_THRESHOLD_LAT_WIDTH = 0.05
KONA_EV_2022_CENTER_FRICTION_THRESHOLD_SPEED = 18.0
KONA_EV_2022_CENTER_FRICTION_THRESHOLD_SPEED_WIDTH = 2.5
KONA_EV_2022_CENTER_OUTPUT_TAPER_MAX = 0.045
KONA_EV_2022_CENTER_OUTPUT_TAPER_LAT = 0.20
KONA_EV_2022_CENTER_OUTPUT_TAPER_LAT_WIDTH = 0.05
KONA_EV_2022_CENTER_OUTPUT_TAPER_SPEED = 18.0
KONA_EV_2022_CENTER_OUTPUT_TAPER_SPEED_WIDTH = 2.5

TRAILER_LOAD_FULL_ASSIST_KG = 15000.0 * CV.LB_TO_KG
TRAILER_LATERAL_MIN_SPEED = 15.0 * CV.MPH_TO_MS
TRAILER_LATERAL_FULL_SPEED = 35.0 * CV.MPH_TO_MS
TRAILER_LATERAL_LAT_RISE = 0.30
TRAILER_LATERAL_FF_GAIN = 0.05
TRAILER_LATERAL_FRICTION_GAIN = 0.03

_FLM_ACTIVE_OVERRIDES_TEXT = ""
_FLM_ACTIVE_OVERRIDES = {}


def _sigmoid(x: float) -> float:
  if x >= 0.0:
    z = math.exp(-x)
    return 1.0 / (1.0 + z)

  z = math.exp(x)
  return z / (1.0 + z)


def _gm_base_friction_threshold_default(v_ego: float) -> float:
  return float(np.interp(v_ego, [1 * CV.MPH_TO_MS, 20 * CV.MPH_TO_MS, 75 * CV.MPH_TO_MS], [0.16, 0.19, 0.27]))


def _standard_friction_threshold_default(v_ego: float) -> float:
  return max(_gm_base_friction_threshold_default(v_ego), STANDARD_FRICTION_THRESHOLD)


def _hkg_canfd_base_friction_threshold_default(v_ego: float) -> float:
  return max(_gm_base_friction_threshold_default(v_ego), HKG_CANFD_BASE_FRICTION_THRESHOLD)


def _flm_copy_json(value):
  return json.loads(json.dumps(value))


def normalize_flm_overrides(overrides) -> dict:
  if overrides in (None, "", b""):
    return {}

  if isinstance(overrides, bytes):
    overrides = overrides.decode("utf-8", errors="replace")

  if isinstance(overrides, str):
    stripped = overrides.strip()
    if not stripped:
      return {}
    try:
      overrides = json.loads(stripped)
    except Exception:
      try:
        overrides = ast.literal_eval(stripped)
      except (SyntaxError, ValueError):
        return {}

  if not isinstance(overrides, dict):
    return {}

  normalized = {
    "schemaVersion": FLM_SCHEMA_VERSION,
    "baseFrictionThresholds": {},
    "vehicleKnobs": {},
  }

  for family in ("gm", "standard", "hkg_canfd"):
    payload = overrides.get("baseFrictionThresholds", {}).get(family, {})
    values = payload.get("values", payload if isinstance(payload, list) else [])
    if not isinstance(values, (list, tuple)) or len(values) != len(FLM_FRICTION_SPEED_KNOTS):
      continue
    try:
      normalized["baseFrictionThresholds"][family] = {
        "speedKnots": list(FLM_FRICTION_SPEED_KNOTS),
        "values": [float(v) for v in values],
      }
    except Exception:
      continue

  vehicle_knobs = overrides.get("vehicleKnobs", {})
  if isinstance(vehicle_knobs, dict):
    for key, value in vehicle_knobs.items():
      try:
        normalized["vehicleKnobs"][str(key)] = float(value)
      except Exception:
        continue

  if not normalized["baseFrictionThresholds"] and not normalized["vehicleKnobs"]:
    return {}

  return normalized


def set_flm_runtime_overrides(overrides) -> None:
  global _FLM_ACTIVE_OVERRIDES, _FLM_ACTIVE_OVERRIDES_TEXT

  normalized = normalize_flm_overrides(overrides)
  text = json.dumps(normalized, sort_keys=True, separators=(",", ":")) if normalized else ""
  if text == _FLM_ACTIVE_OVERRIDES_TEXT:
    return

  _FLM_ACTIVE_OVERRIDES_TEXT = text
  _FLM_ACTIVE_OVERRIDES = normalized


def clear_flm_runtime_overrides() -> None:
  set_flm_runtime_overrides({})


def get_flm_runtime_overrides() -> dict:
  return _flm_copy_json(_FLM_ACTIVE_OVERRIDES) if _FLM_ACTIVE_OVERRIDES else {}


def flm_runtime_overrides_active() -> bool:
  return bool(_FLM_ACTIVE_OVERRIDES)


def _flm_base_friction_threshold(family: str, v_ego: float, default_fn) -> float:
  payload = _FLM_ACTIVE_OVERRIDES.get("baseFrictionThresholds", {}).get(family, {})
  values = payload.get("values", [])
  if isinstance(values, list) and len(values) == len(FLM_FRICTION_SPEED_KNOTS):
    return float(np.interp(v_ego, FLM_FRICTION_SPEED_KNOTS, values))
  return float(default_fn(v_ego))


def _flm_vehicle_knob(name: str, default_value: float) -> float:
  try:
    return float(_FLM_ACTIVE_OVERRIDES.get("vehicleKnobs", {}).get(name, default_value))
  except Exception:
    return float(default_value)


def get_gm_base_friction_threshold(v_ego: float) -> float:
  return _flm_base_friction_threshold("gm", v_ego, _gm_base_friction_threshold_default)


def get_standard_friction_threshold(v_ego: float) -> float:
  return _flm_base_friction_threshold("standard", v_ego, _standard_friction_threshold_default)


def get_hkg_canfd_base_friction_threshold(v_ego: float) -> float:
  return _flm_base_friction_threshold("hkg_canfd", v_ego, _hkg_canfd_base_friction_threshold_default)


def get_trailer_lateral_assist_factor(trailer_load_kg: float, v_ego: float, desired_lateral_accel: float) -> float:
  load_factor = np.clip(trailer_load_kg / TRAILER_LOAD_FULL_ASSIST_KG, 0.0, 1.0)
  speed_factor = np.interp(v_ego, [TRAILER_LATERAL_MIN_SPEED, TRAILER_LATERAL_FULL_SPEED], [0.0, 1.0])
  lat_factor = 1.0 - math.exp(-abs(desired_lateral_accel) / TRAILER_LATERAL_LAT_RISE)
  return float(load_factor * speed_factor * lat_factor)


def get_trailer_lateral_ff_scale(trailer_load_kg: float, v_ego: float, desired_lateral_accel: float) -> float:
  return 1.0 + TRAILER_LATERAL_FF_GAIN * get_trailer_lateral_assist_factor(trailer_load_kg, v_ego, desired_lateral_accel)


def get_trailer_lateral_friction_scale(trailer_load_kg: float, v_ego: float, desired_lateral_accel: float) -> float:
  return 1.0 + TRAILER_LATERAL_FRICTION_GAIN * get_trailer_lateral_assist_factor(trailer_load_kg, v_ego, desired_lateral_accel)


def _prius_sigmoid(x: float) -> float:
  return _sigmoid(x)


def _prius_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / PRIUS_TRANSITION_SPEED) ** 2)


def _prius_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / PRIUS_PHASE_SCALE)


def _prius_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def _prius_transition_envelope(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  lat_factor = 1.0 - math.exp(-abs(desired_lateral_accel) / PRIUS_FRICTION_LAT_RISE)
  jerk_factor = 1.0 - math.exp(-abs(desired_lateral_jerk) / PRIUS_FRICTION_JERK_RISE)
  return _prius_low_speed_factor(v_ego) * lat_factor * jerk_factor


def get_prius_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  gain = _prius_side_value(
    desired_lateral_accel,
    _flm_vehicle_knob("toyota_prius.ff_gain_left", PRIUS_FF_GAIN_LEFT),
    _flm_vehicle_knob("toyota_prius.ff_gain_right", PRIUS_FF_GAIN_RIGHT),
  )
  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _prius_sigmoid((abs_lateral_accel - PRIUS_FF_ONSET) / PRIUS_FF_ONSET_WIDTH)
  cutoff = _prius_sigmoid((PRIUS_FF_CUTOFF - abs_lateral_accel) / PRIUS_FF_CUTOFF_WIDTH)
  extra_scale = gain * onset * cutoff
  phase = _prius_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  low_speed_factor = _prius_low_speed_factor(v_ego)
  turn_in_boost = 1.0 + (_prius_side_value(
                          desired_lateral_accel,
                          _flm_vehicle_knob("toyota_prius.turn_in_boost_left", PRIUS_TURN_IN_BOOST_LEFT),
                          _flm_vehicle_knob("toyota_prius.turn_in_boost_right", PRIUS_TURN_IN_BOOST_RIGHT),
                        ) *
                          turn_in_weight * (0.35 + 0.65 * low_speed_factor))
  unwind_taper = 1.0 - (_prius_side_value(
                         desired_lateral_accel,
                         _flm_vehicle_knob("toyota_prius.unwind_taper_left", PRIUS_UNWIND_TAPER_LEFT),
                         _flm_vehicle_knob("toyota_prius.unwind_taper_right", PRIUS_UNWIND_TAPER_RIGHT),
                       ) *
                         unwind_weight * (0.35 + 0.65 * low_speed_factor))
  return 1.0 + (extra_scale * turn_in_boost * max(unwind_taper, 0.0))


def get_prius_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0, desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = get_gm_base_friction_threshold(v_ego)
  transition_envelope = _prius_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _prius_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  threshold_scale = 1.0 - (_prius_side_value(
                           desired_lateral_accel,
                           _flm_vehicle_knob("toyota_prius.turn_in_threshold_reduction_left", PRIUS_TURN_IN_THRESHOLD_REDUCTION_LEFT),
                           _flm_vehicle_knob("toyota_prius.turn_in_threshold_reduction_right", PRIUS_TURN_IN_THRESHOLD_REDUCTION_RIGHT),
                         ) *
                           transition_envelope * turn_in_weight)
  threshold_scale += (_prius_side_value(
                      desired_lateral_accel,
                      _flm_vehicle_knob("toyota_prius.unwind_threshold_increase_left", PRIUS_UNWIND_THRESHOLD_INCREASE_LEFT),
                      _flm_vehicle_knob("toyota_prius.unwind_threshold_increase_right", PRIUS_UNWIND_THRESHOLD_INCREASE_RIGHT),
                    ) *
                      transition_envelope * unwind_weight)
  center_speed_weight = _prius_sigmoid((v_ego - PRIUS_CENTER_FRICTION_THRESHOLD_SPEED) /
                                       PRIUS_CENTER_FRICTION_THRESHOLD_SPEED_WIDTH)
  center_lat_weight = _prius_sigmoid((PRIUS_CENTER_FRICTION_THRESHOLD_LAT - abs(desired_lateral_accel)) /
                                     PRIUS_CENTER_FRICTION_THRESHOLD_LAT_WIDTH)
  threshold_scale += (_flm_vehicle_knob("toyota_prius.center_friction_threshold_gain",
                                        PRIUS_CENTER_FRICTION_THRESHOLD_GAIN) *
                      center_speed_weight * center_lat_weight)
  return base_threshold * min(max(threshold_scale, 0.86), 1.16)


def get_prius_friction_scale(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  transition_envelope = _prius_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _prius_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  friction_scale = 1.0
  friction_scale += (_prius_side_value(desired_lateral_accel, PRIUS_TURN_IN_FRICTION_BOOST_LEFT, PRIUS_TURN_IN_FRICTION_BOOST_RIGHT) *
                     transition_envelope * turn_in_weight)
  friction_scale -= (_prius_side_value(desired_lateral_accel, PRIUS_UNWIND_FRICTION_REDUCTION_LEFT, PRIUS_UNWIND_FRICTION_REDUCTION_RIGHT) *
                     transition_envelope * unwind_weight)
  return min(max(friction_scale, 0.90), 1.14)


def get_prius_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _prius_sigmoid((v_ego - PRIUS_CENTER_TAPER_SPEED) / PRIUS_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _prius_sigmoid((PRIUS_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / PRIUS_CENTER_TAPER_LAT_WIDTH)
  reduction = _flm_vehicle_knob("toyota_prius.center_taper_max", PRIUS_CENTER_TAPER_MAX) * speed_weight * center_weight
  return 1.0 - reduction


def get_prius_friction_jerk_deadzone(v_ego: float, desired_lateral_accel: float,
                                     deadzone_max: float = PRIUS_FRICTION_JERK_DEADZONE_MAX) -> float:
  speed_weight = _prius_sigmoid((v_ego - PRIUS_FRICTION_JERK_DEADZONE_SPEED) /
                                PRIUS_FRICTION_JERK_DEADZONE_SPEED_WIDTH)
  center_weight = _prius_sigmoid((PRIUS_FRICTION_JERK_DEADZONE_LAT - abs(desired_lateral_accel)) /
                                 PRIUS_FRICTION_JERK_DEADZONE_LAT_WIDTH)
  return deadzone_max * speed_weight * center_weight


def get_prius_high_speed_output_taper_scale(desired_lateral_accel: float, v_ego: float,
                                            taper_max: float = PRIUS_HIGH_SPEED_OUTPUT_TAPER_MAX) -> float:
  speed_weight = _prius_sigmoid((v_ego - PRIUS_HIGH_SPEED_OUTPUT_TAPER_SPEED) /
                                PRIUS_HIGH_SPEED_OUTPUT_TAPER_SPEED_WIDTH)
  curve_weight = _prius_sigmoid((abs(desired_lateral_accel) - PRIUS_HIGH_SPEED_OUTPUT_TAPER_LAT) /
                                 PRIUS_HIGH_SPEED_OUTPUT_TAPER_LAT_WIDTH)
  return 1.0 - taper_max * speed_weight * curve_weight


def get_camry_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0,
                                 desired_lateral_jerk: float = 0.0) -> float:
  del desired_lateral_jerk
  speed_weight = _sigmoid((v_ego - CAMRY_CENTER_FRICTION_THRESHOLD_SPEED) /
                          CAMRY_CENTER_FRICTION_THRESHOLD_SPEED_WIDTH)
  center_weight = _sigmoid((CAMRY_CENTER_FRICTION_THRESHOLD_LAT - abs(desired_lateral_accel)) /
                           CAMRY_CENTER_FRICTION_THRESHOLD_LAT_WIDTH)
  gain = _flm_vehicle_knob("toyota_camry.center_friction_threshold_gain",
                           CAMRY_CENTER_FRICTION_THRESHOLD_GAIN)
  return get_standard_friction_threshold(v_ego) * (1.0 + gain * speed_weight * center_weight)


def get_camry_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  phase = math.tanh((desired_lateral_accel * desired_lateral_jerk) / 0.10)
  unwind_weight = max(-phase, 0.0)
  lat_weight = _sigmoid((abs(desired_lateral_accel) - CAMRY_UNWIND_LAT_ONSET) / CAMRY_UNWIND_LAT_WIDTH)
  speed_weight = _sigmoid((v_ego - CAMRY_UNWIND_SPEED_ONSET) / CAMRY_UNWIND_SPEED_WIDTH)
  reduction = _flm_vehicle_knob("toyota_camry.unwind_ff_reduction", CAMRY_UNWIND_FF_REDUCTION)
  return 1.0 - reduction * unwind_weight * lat_weight * speed_weight


def _rav4_prime_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def _rav4_prime_speed_weight(v_ego: float) -> float:
  onset = _sigmoid((v_ego - RAV4_PRIME_SPEED_ONSET) / RAV4_PRIME_SPEED_ONSET_WIDTH)
  cutoff = _sigmoid((RAV4_PRIME_SPEED_MAX - v_ego) / RAV4_PRIME_SPEED_MAX_WIDTH)
  return onset * cutoff


def _rav4_prime_unwind_weight(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  phase = math.tanh((desired_lateral_accel * desired_lateral_jerk) / RAV4_PRIME_PHASE_SCALE)
  lat_weight = _sigmoid((abs(desired_lateral_accel) - 0.20) / 0.07)
  return max(-phase, 0.0) * lat_weight


def _rav4_prime_turn_in_weight(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  phase = math.tanh((desired_lateral_accel * desired_lateral_jerk) / RAV4_PRIME_PHASE_SCALE)
  lat_weight = _sigmoid((abs(desired_lateral_accel) - 0.20) / 0.07)
  return max(phase, 0.0) * lat_weight


def get_rav4_prime_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  turn_in_boost = _rav4_prime_side_value(desired_lateral_accel,
                                         RAV4_PRIME_TURN_IN_FF_BOOST_LEFT,
                                         RAV4_PRIME_TURN_IN_FF_BOOST_RIGHT)
  reduction = _rav4_prime_side_value(desired_lateral_accel,
                                     RAV4_PRIME_UNWIND_FF_REDUCTION_LEFT,
                                     RAV4_PRIME_UNWIND_FF_REDUCTION_RIGHT)
  speed_weight = _rav4_prime_speed_weight(v_ego)
  return (1.0 + (turn_in_boost * _rav4_prime_turn_in_weight(desired_lateral_accel, desired_lateral_jerk) * speed_weight) -
          (reduction * _rav4_prime_unwind_weight(desired_lateral_accel, desired_lateral_jerk) * speed_weight))


def get_rav4_prime_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0,
                                      desired_lateral_jerk: float = 0.0) -> float:
  del desired_lateral_jerk
  center_weight = _sigmoid((RAV4_PRIME_FRICTION_CENTER_LAT - abs(desired_lateral_accel)) /
                           RAV4_PRIME_FRICTION_CENTER_LAT_WIDTH)
  scale = 1.0 + (RAV4_PRIME_FRICTION_THRESHOLD_GAIN * center_weight * _rav4_prime_speed_weight(v_ego))
  return get_standard_friction_threshold(v_ego) * scale


def get_rav4_prime_friction_scale(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  reduction = _rav4_prime_side_value(desired_lateral_accel,
                                     RAV4_PRIME_UNWIND_FRICTION_REDUCTION_LEFT,
                                     RAV4_PRIME_UNWIND_FRICTION_REDUCTION_RIGHT)
  return 1.0 - (reduction * _rav4_prime_unwind_weight(desired_lateral_accel, desired_lateral_jerk) *
                _rav4_prime_speed_weight(v_ego))


def get_rav4_prime_output_taper_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  reduction = _rav4_prime_side_value(desired_lateral_accel,
                                     RAV4_PRIME_UNWIND_OUTPUT_REDUCTION_LEFT,
                                     RAV4_PRIME_UNWIND_OUTPUT_REDUCTION_RIGHT)
  hard_reduction = _rav4_prime_side_value(desired_lateral_accel,
                                          RAV4_PRIME_HARD_UNWIND_OUTPUT_REDUCTION_LEFT,
                                          RAV4_PRIME_HARD_UNWIND_OUTPUT_REDUCTION_RIGHT)
  hard_curve_weight = _sigmoid((abs(desired_lateral_accel) - RAV4_PRIME_HARD_UNWIND_LAT) /
                               RAV4_PRIME_HARD_UNWIND_LAT_WIDTH)
  reduction += hard_reduction * hard_curve_weight
  return 1.0 - (reduction * _rav4_prime_unwind_weight(desired_lateral_accel, desired_lateral_jerk) *
                _rav4_prime_speed_weight(v_ego))


def _sienna_4th_gen_turn_in_speed_weight(v_ego: float) -> float:
  onset = _sigmoid((v_ego - SIENNA_4TH_GEN_TURN_IN_SPEED_ONSET) / SIENNA_4TH_GEN_TURN_IN_SPEED_WIDTH)
  cutoff = _sigmoid((SIENNA_4TH_GEN_TURN_IN_SPEED_MAX - v_ego) / SIENNA_4TH_GEN_TURN_IN_SPEED_MAX_WIDTH)
  return onset * cutoff


def _sienna_4th_gen_friction_speed_weight(v_ego: float) -> float:
  onset = _sigmoid((v_ego - SIENNA_4TH_GEN_FRICTION_SPEED_ONSET) / SIENNA_4TH_GEN_FRICTION_SPEED_WIDTH)
  cutoff = _sigmoid((SIENNA_4TH_GEN_FRICTION_SPEED_MAX - v_ego) / SIENNA_4TH_GEN_FRICTION_SPEED_MAX_WIDTH)
  return onset * cutoff


def _sienna_4th_gen_turn_in_weight(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  phase = math.tanh((desired_lateral_accel * desired_lateral_jerk) / SIENNA_4TH_GEN_PHASE_SCALE)
  lat_weight = _sigmoid((abs(desired_lateral_accel) - SIENNA_4TH_GEN_TURN_IN_LAT) /
                        SIENNA_4TH_GEN_TURN_IN_LAT_WIDTH)
  return max(phase, 0.0) * lat_weight


def get_sienna_4th_gen_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0
  return 1.0 + (SIENNA_4TH_GEN_TURN_IN_FF_BOOST *
                _sienna_4th_gen_turn_in_weight(desired_lateral_accel, desired_lateral_jerk) *
                _sienna_4th_gen_turn_in_speed_weight(v_ego))


def get_sienna_4th_gen_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0,
                                          desired_lateral_jerk: float = 0.0) -> float:
  del desired_lateral_jerk
  center_weight = _sigmoid((SIENNA_4TH_GEN_FRICTION_CENTER_LAT - abs(desired_lateral_accel)) /
                           SIENNA_4TH_GEN_FRICTION_CENTER_LAT_WIDTH)
  high_speed_weight = _sigmoid((v_ego - SIENNA_4TH_GEN_HIGH_SPEED_FRICTION_SPEED_ONSET) /
                               SIENNA_4TH_GEN_HIGH_SPEED_FRICTION_SPEED_WIDTH)
  return get_standard_friction_threshold(v_ego) * (
    1.0 + center_weight * (
      SIENNA_4TH_GEN_FRICTION_THRESHOLD_GAIN * _sienna_4th_gen_friction_speed_weight(v_ego) +
      SIENNA_4TH_GEN_HIGH_SPEED_FRICTION_THRESHOLD_GAIN * high_speed_weight
    )
  )


def get_sienna_4th_gen_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  center_weight = _sigmoid((SIENNA_4TH_GEN_CENTER_TAPER_LAT - abs(desired_lateral_accel)) /
                           SIENNA_4TH_GEN_CENTER_TAPER_LAT_WIDTH)
  low_speed_weight = _sigmoid((SIENNA_4TH_GEN_CENTER_TAPER_SPEED_MAX - v_ego) /
                              SIENNA_4TH_GEN_CENTER_TAPER_SPEED_WIDTH)
  high_speed_onset = _sigmoid((v_ego - SIENNA_4TH_GEN_HIGH_SPEED_CENTER_TAPER_ONSET) /
                              SIENNA_4TH_GEN_HIGH_SPEED_CENTER_TAPER_ONSET_WIDTH)
  high_speed_cutoff = _sigmoid((SIENNA_4TH_GEN_HIGH_SPEED_CENTER_TAPER_MAX_SPEED - v_ego) /
                               SIENNA_4TH_GEN_HIGH_SPEED_CENTER_TAPER_MAX_SPEED_WIDTH)
  reduction = (SIENNA_4TH_GEN_CENTER_TAPER_MAX * low_speed_weight +
               SIENNA_4TH_GEN_HIGH_SPEED_CENTER_TAPER_MAX * high_speed_onset * high_speed_cutoff)
  return 1.0 - (reduction * center_weight)


def get_sienna_4th_gen_high_speed_output_taper_scale(v_ego: float) -> float:
  onset = _sigmoid((v_ego - SIENNA_4TH_GEN_HIGH_SPEED_OUTPUT_TAPER_ONSET) /
                   SIENNA_4TH_GEN_HIGH_SPEED_OUTPUT_TAPER_ONSET_WIDTH)
  cutoff = _sigmoid((SIENNA_4TH_GEN_HIGH_SPEED_OUTPUT_TAPER_MAX_SPEED - v_ego) /
                    SIENNA_4TH_GEN_HIGH_SPEED_OUTPUT_TAPER_MAX_SPEED_WIDTH)
  return 1.0 - SIENNA_4TH_GEN_HIGH_SPEED_OUTPUT_TAPER_MAX * onset * cutoff


def get_toyota_corolla_tss2_ff_scale(desired_lateral_accel: float,
                                     desired_lateral_jerk: float,
                                     v_ego: float) -> float:
  """Add a small, transition-only turn-in correction for Corolla TSS2 torque EPS."""
  if desired_lateral_accel == 0.0:
    return 1.0

  phase = math.tanh((desired_lateral_accel * desired_lateral_jerk) /
                    TOYOTA_COROLLA_TSS2_PHASE_SCALE)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  curve_weight = _sigmoid((abs(desired_lateral_accel) - TOYOTA_COROLLA_TSS2_CURVE_LAT_ONSET) /
                          TOYOTA_COROLLA_TSS2_CURVE_LAT_WIDTH)
  speed_weight = (_sigmoid((v_ego - TOYOTA_COROLLA_TSS2_SPEED_ONSET) /
                           TOYOTA_COROLLA_TSS2_SPEED_ONSET_WIDTH) *
                  _sigmoid((TOYOTA_COROLLA_TSS2_SPEED_CUTOFF - v_ego) /
                           TOYOTA_COROLLA_TSS2_SPEED_CUTOFF_WIDTH))
  boost = _flm_vehicle_knob("toyota_corolla_tss2.turn_in_ff_boost",
                            TOYOTA_COROLLA_TSS2_TURN_IN_FF_BOOST)
  unwind_reduction = _flm_vehicle_knob("toyota_corolla_tss2.unwind_ff_reduction",
                                       TOYOTA_COROLLA_TSS2_UNWIND_FF_REDUCTION)
  return 1.0 + curve_weight * speed_weight * (boost * turn_in_weight - unwind_reduction * unwind_weight)


def get_toyota_corolla_tss2_friction_threshold(v_ego: float,
                                               desired_lateral_accel: float = 0.0,
                                               desired_lateral_jerk: float = 0.0) -> float:
  """Reduce center-only friction chasing on highway-sized model corrections."""
  speed_weight = (_sigmoid((v_ego - TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_SPEED_ONSET) /
                           TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_SPEED_WIDTH) *
                  _sigmoid((TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_SPEED_CUTOFF - v_ego) /
                           TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_SPEED_CUTOFF_WIDTH))
  center_weight = _sigmoid((TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_LAT - abs(desired_lateral_accel)) /
                           TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_LAT_WIDTH)
  calm_weight = _sigmoid((TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_JERK - abs(desired_lateral_jerk)) /
                         TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_JERK_WIDTH)
  gain = _flm_vehicle_knob("toyota_corolla_tss2.center_friction_threshold_gain",
                           TOYOTA_COROLLA_TSS2_CENTER_FRICTION_THRESHOLD_GAIN)
  return get_standard_friction_threshold(v_ego) * (1.0 + gain * speed_weight * center_weight * calm_weight)


def get_toyota_corolla_tss2_center_output_scale(desired_lateral_accel: float, v_ego: float) -> float:
  """Taper only near-center crawl-speed torque during manual handoff."""
  center_weight = _sigmoid((TOYOTA_COROLLA_TSS2_CENTER_OUTPUT_TAPER_LAT - abs(desired_lateral_accel)) /
                           TOYOTA_COROLLA_TSS2_CENTER_OUTPUT_TAPER_LAT_WIDTH)
  low_speed_weight = _sigmoid((TOYOTA_COROLLA_TSS2_CENTER_OUTPUT_TAPER_SPEED - v_ego) /
                              TOYOTA_COROLLA_TSS2_CENTER_OUTPUT_TAPER_SPEED_WIDTH)
  reduction = _flm_vehicle_knob("toyota_corolla_tss2.center_output_taper_max",
                                TOYOTA_COROLLA_TSS2_CENTER_OUTPUT_TAPER_MAX) * center_weight * low_speed_weight
  return max(1.0 - reduction, 0.65)


def _toyota_highlander_tss2_unwind_weight(desired_lateral_accel: float,
                                           desired_lateral_jerk: float,
                                           v_ego: float) -> float:
  phase = math.tanh((desired_lateral_accel * desired_lateral_jerk) /
                    TOYOTA_HIGHLANDER_TSS2_PHASE_SCALE)
  curve_weight = _sigmoid((abs(desired_lateral_accel) - TOYOTA_HIGHLANDER_TSS2_UNWIND_LAT_ONSET) /
                          TOYOTA_HIGHLANDER_TSS2_UNWIND_LAT_WIDTH)
  speed_weight = (_sigmoid((v_ego - TOYOTA_HIGHLANDER_TSS2_UNWIND_SPEED_ONSET) /
                           TOYOTA_HIGHLANDER_TSS2_UNWIND_SPEED_WIDTH) *
                  _sigmoid((TOYOTA_HIGHLANDER_TSS2_UNWIND_SPEED_MAX - v_ego) /
                           TOYOTA_HIGHLANDER_TSS2_UNWIND_SPEED_MAX_WIDTH))
  return max(-phase, 0.0) * curve_weight * speed_weight


def get_toyota_highlander_tss2_ff_scale(desired_lateral_accel: float,
                                         desired_lateral_jerk: float,
                                         v_ego: float) -> float:
  reduction = _flm_vehicle_knob("toyota_highlander_tss2.unwind_ff_reduction",
                                TOYOTA_HIGHLANDER_TSS2_UNWIND_FF_REDUCTION)
  return 1.0 - reduction * _toyota_highlander_tss2_unwind_weight(
    desired_lateral_accel, desired_lateral_jerk, v_ego,
  )


def get_toyota_highlander_tss2_friction_threshold(v_ego: float,
                                                  desired_lateral_accel: float = 0.0,
                                                  desired_lateral_jerk: float = 0.0) -> float:
  gain = _flm_vehicle_knob("toyota_highlander_tss2.unwind_friction_threshold_gain",
                           TOYOTA_HIGHLANDER_TSS2_UNWIND_FRICTION_THRESHOLD_GAIN)
  return get_standard_friction_threshold(v_ego) * (
    1.0 + gain * _toyota_highlander_tss2_unwind_weight(
      desired_lateral_accel, desired_lateral_jerk, v_ego,
    )
  )


def get_toyota_highlander_tss2_friction_scale(v_ego: float,
                                              desired_lateral_accel: float,
                                              desired_lateral_jerk: float) -> float:
  reduction = _flm_vehicle_knob("toyota_highlander_tss2.unwind_friction_scale_reduction",
                                TOYOTA_HIGHLANDER_TSS2_UNWIND_FRICTION_SCALE_REDUCTION)
  return 1.0 - reduction * _toyota_highlander_tss2_unwind_weight(
    desired_lateral_accel, desired_lateral_jerk, v_ego,
  )


def get_toyota_highlander_tss2_output_taper_scale(desired_lateral_accel: float,
                                                  desired_lateral_jerk: float,
                                                  v_ego: float) -> float:
  """Slow low-speed unwind reversals without reducing turn-in authority."""
  reduction = _flm_vehicle_knob("toyota_highlander_tss2.unwind_output_reduction",
                                TOYOTA_HIGHLANDER_TSS2_UNWIND_OUTPUT_REDUCTION)
  return 1.0 - reduction * _toyota_highlander_tss2_unwind_weight(
    desired_lateral_accel, desired_lateral_jerk, v_ego,
  )


def get_lexus_is_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  phase = math.tanh((desired_lateral_accel * desired_lateral_jerk) / LEXUS_IS_PHASE_SCALE)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  lat_weight = _sigmoid((abs(desired_lateral_accel) - LEXUS_IS_UNWIND_LAT_ONSET) / LEXUS_IS_UNWIND_LAT_WIDTH)
  speed_weight = _sigmoid((v_ego - LEXUS_IS_UNWIND_SPEED_ONSET) / LEXUS_IS_UNWIND_SPEED_WIDTH)
  turn_in_boost = LEXUS_IS_TURN_IN_FF_BOOST_LEFT if desired_lateral_accel >= 0.0 else LEXUS_IS_TURN_IN_FF_BOOST_RIGHT
  reduction = LEXUS_IS_UNWIND_FF_REDUCTION_LEFT if desired_lateral_accel >= 0.0 else LEXUS_IS_UNWIND_FF_REDUCTION_RIGHT
  return (1.0 + (turn_in_boost * turn_in_weight * lat_weight * speed_weight) -
          (reduction * unwind_weight * lat_weight * speed_weight))


def get_subaru_impreza_pid_output_scale(angle_error_deg: float) -> float:
  error_weight = min(max((abs(angle_error_deg) - SUBARU_IMPREZA_PID_TAPER_START_DEG) /
                         (SUBARU_IMPREZA_PID_TAPER_FULL_DEG - SUBARU_IMPREZA_PID_TAPER_START_DEG), 0.0), 1.0)
  return 1.0 - ((1.0 - SUBARU_IMPREZA_PID_TAPER_MIN) * error_weight)


def get_rav4_tss2_pid_output(output_torque: float, prev_output_torque: float,
                             desired_angle_deg: float, v_ego: float) -> float:
  """Damp low-speed RAV4 center reversals without blunting real turns."""
  speed_weight = _sigmoid((RAV4_TSS2_PID_LOW_SPEED - max(v_ego, 0.0)) /
                          RAV4_TSS2_PID_LOW_SPEED_WIDTH)
  center_weight = _sigmoid((RAV4_TSS2_PID_CENTER_ANGLE - abs(desired_angle_deg)) /
                           RAV4_TSS2_PID_CENTER_ANGLE_WIDTH)
  envelope = speed_weight * center_weight

  output_scale = 1.0 - ((1.0 - RAV4_TSS2_PID_OUTPUT_SCALE_MIN) * envelope)
  output_alpha = 1.0 - ((1.0 - RAV4_TSS2_PID_OUTPUT_ALPHA_MIN) * envelope)
  limited_output = output_torque * output_scale
  return float(prev_output_torque + output_alpha * (limited_output - prev_output_torque))


def get_honda_crv_5g_pid_output(output_torque: float, prev_output_torque: float,
                                desired_angle_deg: float, v_ego: float) -> float:
  """Damp low-speed CR-V 5G center reversals without blunting real turns."""
  speed_weight = _sigmoid((HONDA_CRV_5G_PID_LOW_SPEED - max(v_ego, 0.0)) /
                          HONDA_CRV_5G_PID_LOW_SPEED_WIDTH)
  center_weight = _sigmoid((HONDA_CRV_5G_PID_CENTER_ANGLE - abs(desired_angle_deg)) /
                           HONDA_CRV_5G_PID_CENTER_ANGLE_WIDTH)
  envelope = speed_weight * center_weight

  output_scale = 1.0 - ((1.0 - HONDA_CRV_5G_PID_OUTPUT_SCALE_MIN) * envelope)
  output_alpha = 1.0 - ((1.0 - HONDA_CRV_5G_PID_OUTPUT_ALPHA_MIN) * envelope)
  limited_output = output_torque * output_scale
  return float(prev_output_torque + output_alpha * (limited_output - prev_output_torque))


def _rav4_tss2_center_envelope(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _sigmoid((RAV4_TSS2_CENTER_SPEED - max(v_ego, 0.0)) /
                          RAV4_TSS2_CENTER_SPEED_WIDTH)
  center_weight = _sigmoid((RAV4_TSS2_CENTER_FRICTION_LAT - abs(desired_lateral_accel)) /
                           RAV4_TSS2_CENTER_FRICTION_LAT_WIDTH)
  return speed_weight * center_weight


def get_rav4_tss2_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0,
                                     desired_lateral_jerk: float = 0.0) -> float:
  del desired_lateral_jerk
  gain = _flm_vehicle_knob("toyota_rav4_tss2.center_friction_threshold_gain",
                           RAV4_TSS2_CENTER_FRICTION_THRESHOLD_GAIN)
  return get_standard_friction_threshold(v_ego) * (
    1.0 + gain * _rav4_tss2_center_envelope(desired_lateral_accel, v_ego)
  )


def get_rav4_tss2_center_output_scale(desired_lateral_accel: float, v_ego: float) -> float:
  reduction = _flm_vehicle_knob("toyota_rav4_tss2.center_output_taper_max",
                                RAV4_TSS2_CENTER_OUTPUT_TAPER_MAX)
  return 1.0 - reduction * _rav4_tss2_center_envelope(desired_lateral_accel, v_ego)


def get_ram_1500_transition_output_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  speed_weight = float(np.interp(v_ego, [RAM_1500_TRANSITION_SPEED_ONSET, RAM_1500_TRANSITION_SPEED_FULL], [0.0, 1.0]))
  jerk_weight = float(np.interp(abs(desired_lateral_jerk),
                                [RAM_1500_TRANSITION_JERK_ONSET, RAM_1500_TRANSITION_JERK_FULL], [0.0, 1.0]))
  lat_weight = 1.0 - float(np.interp(abs(desired_lateral_accel),
                                     [RAM_1500_TRANSITION_LAT_FADE_START, RAM_1500_TRANSITION_LAT_FADE_END], [0.0, 1.0]))
  return 1.0 - (RAM_1500_TRANSITION_TAPER_MAX * speed_weight * jerk_weight * lat_weight)


def get_ram_1500_unwind_output_scale(desired_lateral_accel: float, desired_lateral_jerk: float,
                                     v_ego: float) -> float:
  """Soften only rapid high-speed unwind reversals on the RAM 1500."""
  if desired_lateral_accel * desired_lateral_jerk >= 0.0:
    return 1.0

  speed_weight = float(np.interp(v_ego,
                                 [RAM_1500_UNWIND_OUTPUT_SPEED_ONSET, RAM_1500_UNWIND_OUTPUT_SPEED_FULL],
                                 [0.0, 1.0]))
  jerk_weight = float(np.interp(abs(desired_lateral_jerk),
                                [RAM_1500_UNWIND_OUTPUT_JERK_ONSET, RAM_1500_UNWIND_OUTPUT_JERK_FULL],
                                [0.0, 1.0]))
  curve_weight = _sigmoid((abs(desired_lateral_accel) - RAM_1500_UNWIND_OUTPUT_LAT_ONSET) /
                           RAM_1500_UNWIND_OUTPUT_LAT_WIDTH)
  return 1.0 - (RAM_1500_UNWIND_OUTPUT_TAPER_MAX * speed_weight * jerk_weight * curve_weight)


def get_ram_1500_center_output_scale(desired_lateral_accel: float, v_ego: float) -> float:
  """Damp only center corrections at low/mid speed, not turn authority."""
  center_weight = _sigmoid((RAM_1500_CENTER_OUTPUT_TAPER_LAT - abs(desired_lateral_accel)) /
                           RAM_1500_CENTER_OUTPUT_TAPER_LAT_WIDTH)
  speed_onset = _sigmoid((v_ego - RAM_1500_CENTER_OUTPUT_TAPER_SPEED_ONSET) /
                         RAM_1500_CENTER_OUTPUT_TAPER_SPEED_ONSET_WIDTH)
  speed_cutoff = _sigmoid((RAM_1500_CENTER_OUTPUT_TAPER_SPEED_MAX - v_ego) /
                          RAM_1500_CENTER_OUTPUT_TAPER_SPEED_MAX_WIDTH)
  return 1.0 - (RAM_1500_CENTER_OUTPUT_TAPER_MAX * center_weight * speed_onset * speed_cutoff)


def get_ram_1500_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  phase = math.tanh((desired_lateral_accel * desired_lateral_jerk) / RAM_1500_PHASE_SCALE)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  speed_weight = float(np.interp(v_ego, [RAM_1500_PHASE_SPEED_ONSET, RAM_1500_PHASE_SPEED_FULL], [0.0, 1.0]))
  lat_weight = _sigmoid((abs(desired_lateral_accel) - RAM_1500_PHASE_LAT_ONSET) / RAM_1500_PHASE_LAT_WIDTH)
  return 1.0 + ((RAM_1500_TURN_IN_FF_BOOST * turn_in_weight -
                 RAM_1500_UNWIND_FF_REDUCTION * unwind_weight) * speed_weight * lat_weight)


def get_gmc_yukon_cc_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  """Add turn-in authority and soften the high-speed unwind transient on Yukon CC."""
  phase = math.tanh((desired_lateral_accel * desired_lateral_jerk) / GMC_YUKON_CC_PHASE_SCALE)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  speed_weight = float(np.interp(v_ego,
                                 [GMC_YUKON_CC_PHASE_SPEED_ONSET, GMC_YUKON_CC_PHASE_SPEED_FULL],
                                 [0.0, 1.0]))
  lat_weight = _sigmoid((abs(desired_lateral_accel) - GMC_YUKON_CC_PHASE_LAT_ONSET) /
                        GMC_YUKON_CC_PHASE_LAT_WIDTH)
  return 1.0 + ((GMC_YUKON_CC_TURN_IN_FF_BOOST * turn_in_weight -
                 GMC_YUKON_CC_UNWIND_FF_REDUCTION * unwind_weight) * speed_weight * lat_weight)


def get_kona_non_scc_highway_transition_output_scale(desired_lateral_accel: float, desired_lateral_jerk: float,
                                                       v_ego: float) -> float:
  speed_weight = float(np.interp(v_ego, [KONA_NON_SCC_TRANSITION_SPEED_ONSET, KONA_NON_SCC_TRANSITION_SPEED_FULL], [0.0, 1.0]))
  jerk_weight = float(np.interp(abs(desired_lateral_jerk),
                                [KONA_NON_SCC_TRANSITION_JERK_ONSET, KONA_NON_SCC_TRANSITION_JERK_FULL], [0.0, 1.0]))
  lat_weight = 1.0 - float(np.interp(abs(desired_lateral_accel),
                                     [KONA_NON_SCC_TRANSITION_LAT_FADE_START, KONA_NON_SCC_TRANSITION_LAT_FADE_END], [0.0, 1.0]))
  taper_max = (KONA_NON_SCC_TRANSITION_UNWIND_TAPER_MAX
               if desired_lateral_accel * desired_lateral_jerk < 0.0
               else KONA_NON_SCC_TRANSITION_TURN_IN_TAPER_MAX)
  return 1.0 - (taper_max * speed_weight * jerk_weight * lat_weight)


def get_kona_non_scc_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0,
                                        desired_lateral_jerk: float = 0.0) -> float:
  del desired_lateral_jerk
  speed_weight = _sigmoid((v_ego - KONA_NON_SCC_CENTER_FRICTION_THRESHOLD_SPEED_ONSET) /
                          KONA_NON_SCC_CENTER_FRICTION_THRESHOLD_SPEED_WIDTH)
  center_weight = _sigmoid((KONA_NON_SCC_CENTER_FRICTION_THRESHOLD_LAT - abs(desired_lateral_accel)) /
                           KONA_NON_SCC_CENTER_FRICTION_THRESHOLD_LAT_WIDTH)
  return get_standard_friction_threshold(v_ego) * (
    1.0 + KONA_NON_SCC_CENTER_FRICTION_THRESHOLD_GAIN * speed_weight * center_weight
  )


def get_kona_non_scc_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = float(np.interp(v_ego, [KONA_NON_SCC_CENTER_TAPER_SPEED_ONSET, KONA_NON_SCC_CENTER_TAPER_SPEED_FULL], [0.0, 1.0]))
  center_weight = float(np.interp(abs(desired_lateral_accel), [0.0, KONA_NON_SCC_CENTER_TAPER_LAT], [1.0, 0.0]))
  return 1.0 - (KONA_NON_SCC_CENTER_TAPER_MAX * speed_weight * center_weight)


def _kona_ev_2022_center_weights(desired_lateral_accel: float, v_ego: float) -> tuple[float, float]:
  speed_weight = _sigmoid((v_ego - KONA_EV_2022_CENTER_FRICTION_THRESHOLD_SPEED) /
                          KONA_EV_2022_CENTER_FRICTION_THRESHOLD_SPEED_WIDTH)
  center_weight = _sigmoid((KONA_EV_2022_CENTER_FRICTION_THRESHOLD_LAT - abs(desired_lateral_accel)) /
                           KONA_EV_2022_CENTER_FRICTION_THRESHOLD_LAT_WIDTH)
  return speed_weight, center_weight


def get_kona_ev_2022_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0) -> float:
  speed_weight, center_weight = _kona_ev_2022_center_weights(desired_lateral_accel, v_ego)
  return get_standard_friction_threshold(v_ego) * (
    1.0 + KONA_EV_2022_CENTER_FRICTION_THRESHOLD_GAIN * speed_weight * center_weight
  )


def get_kona_ev_2022_center_output_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _sigmoid((v_ego - KONA_EV_2022_CENTER_OUTPUT_TAPER_SPEED) /
                          KONA_EV_2022_CENTER_OUTPUT_TAPER_SPEED_WIDTH)
  center_weight = _sigmoid((KONA_EV_2022_CENTER_OUTPUT_TAPER_LAT - abs(desired_lateral_accel)) /
                           KONA_EV_2022_CENTER_OUTPUT_TAPER_LAT_WIDTH)
  return 1.0 - (KONA_EV_2022_CENTER_OUTPUT_TAPER_MAX * speed_weight * center_weight)


def civic_bosch_modified_lateral_testing_ground_active() -> bool:
  return testing_ground.use("8", "B")


def civic_bosch_modified_a_lateral_testing_ground_active() -> bool:
  return testing_ground.use("8", "A")


def get_civic_bosch_modified_a_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _sigmoid((v_ego - CIVIC_BOSCH_MODIFIED_A_VARIANT_CENTER_TAPER_SPEED) /
                          CIVIC_BOSCH_MODIFIED_A_VARIANT_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _sigmoid((CIVIC_BOSCH_MODIFIED_A_VARIANT_CENTER_TAPER_LAT - abs(desired_lateral_accel)) /
                           CIVIC_BOSCH_MODIFIED_A_VARIANT_CENTER_TAPER_LAT_WIDTH)
  reduction = CIVIC_BOSCH_MODIFIED_A_VARIANT_CENTER_TAPER_MAX * speed_weight * center_weight
  return 1.0 - reduction


def _civic_bosch_modified_b_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / CIVIC_BOSCH_MODIFIED_B_TRANSITION_SPEED) ** 2)


def _civic_bosch_modified_b_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / CIVIC_BOSCH_MODIFIED_B_PHASE_SCALE)


def _civic_bosch_modified_b_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def get_civic_bosch_modified_b_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _sigmoid((abs_lateral_accel - CIVIC_BOSCH_MODIFIED_B_FF_ONSET) / CIVIC_BOSCH_MODIFIED_B_FF_ONSET_WIDTH)
  cutoff = _sigmoid((CIVIC_BOSCH_MODIFIED_B_FF_CUTOFF - abs_lateral_accel) / CIVIC_BOSCH_MODIFIED_B_FF_CUTOFF_WIDTH)
  base_reduction = _civic_bosch_modified_b_side_value(desired_lateral_accel,
                                                       CIVIC_BOSCH_MODIFIED_B_FF_REDUCTION_LEFT,
                                                       CIVIC_BOSCH_MODIFIED_B_FF_REDUCTION_RIGHT) * onset * cutoff

  phase = _civic_bosch_modified_b_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  low_speed_factor = _civic_bosch_modified_b_low_speed_factor(v_ego)
  a_variant_active = civic_bosch_modified_a_lateral_testing_ground_active()
  variant_active = civic_bosch_modified_lateral_testing_ground_active()
  if a_variant_active:
    base_reduction -= (_civic_bosch_modified_b_side_value(desired_lateral_accel,
                                                           CIVIC_BOSCH_MODIFIED_A_VARIANT_FF_RESTORE_LEFT,
                                                           CIVIC_BOSCH_MODIFIED_A_VARIANT_FF_RESTORE_RIGHT) * onset * cutoff)
  if variant_active:
    base_reduction += (_civic_bosch_modified_b_side_value(desired_lateral_accel,
                                                           CIVIC_BOSCH_MODIFIED_B_VARIANT_FF_REDUCTION_LEFT,
                                                           CIVIC_BOSCH_MODIFIED_B_VARIANT_FF_REDUCTION_RIGHT) * onset * cutoff)

  turn_in_boost = 1.0 + (_civic_bosch_modified_b_side_value(desired_lateral_accel,
                                                             CIVIC_BOSCH_MODIFIED_B_TURN_IN_BOOST_LEFT,
                                                             CIVIC_BOSCH_MODIFIED_B_TURN_IN_BOOST_RIGHT) *
                          turn_in_weight * (0.40 + 0.60 * low_speed_factor))
  if a_variant_active:
    turn_in_boost *= 1.0 + (_civic_bosch_modified_b_side_value(desired_lateral_accel,
                                                                CIVIC_BOSCH_MODIFIED_A_VARIANT_TURN_IN_BOOST_LEFT,
                                                                CIVIC_BOSCH_MODIFIED_A_VARIANT_TURN_IN_BOOST_RIGHT) *
                             turn_in_weight * (0.40 + 0.60 * low_speed_factor))
  if variant_active:
    turn_in_boost *= 1.0 + (_civic_bosch_modified_b_side_value(desired_lateral_accel,
                                                                CIVIC_BOSCH_MODIFIED_B_VARIANT_TURN_IN_BOOST_LEFT,
                                                                CIVIC_BOSCH_MODIFIED_B_VARIANT_TURN_IN_BOOST_RIGHT) *
                             turn_in_weight * (0.40 + 0.60 * low_speed_factor))
  unwind_taper = 1.0 - (_civic_bosch_modified_b_side_value(desired_lateral_accel,
                                                            CIVIC_BOSCH_MODIFIED_B_UNWIND_TAPER_LEFT,
                                                            CIVIC_BOSCH_MODIFIED_B_UNWIND_TAPER_RIGHT) *
                         unwind_weight * (0.35 + 0.65 * low_speed_factor))
  if a_variant_active:
    unwind_taper *= 1.0 - (_civic_bosch_modified_b_side_value(desired_lateral_accel,
                                                               CIVIC_BOSCH_MODIFIED_A_VARIANT_UNWIND_TAPER_LEFT,
                                                               CIVIC_BOSCH_MODIFIED_A_VARIANT_UNWIND_TAPER_RIGHT) *
                            unwind_weight * (0.35 + 0.65 * low_speed_factor))
  if variant_active:
    unwind_taper *= 1.0 - (_civic_bosch_modified_b_side_value(desired_lateral_accel,
                                                               CIVIC_BOSCH_MODIFIED_B_VARIANT_UNWIND_TAPER_LEFT,
                                                               CIVIC_BOSCH_MODIFIED_B_VARIANT_UNWIND_TAPER_RIGHT) *
                            unwind_weight * (0.35 + 0.65 * low_speed_factor))
  return (1.0 - base_reduction) * turn_in_boost * max(unwind_taper, 0.0)


def get_civic_bosch_modified_b_friction_scale(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  if desired_lateral_accel == 0.0 or desired_lateral_jerk == 0.0:
    return 1.0

  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _sigmoid((abs_lateral_accel - CIVIC_BOSCH_MODIFIED_B_FF_ONSET) / CIVIC_BOSCH_MODIFIED_B_FF_ONSET_WIDTH)
  cutoff = _sigmoid((CIVIC_BOSCH_MODIFIED_B_FF_CUTOFF - abs_lateral_accel) / CIVIC_BOSCH_MODIFIED_B_FF_CUTOFF_WIDTH)
  envelope = onset * cutoff * _civic_bosch_modified_b_low_speed_factor(v_ego)
  phase = _civic_bosch_modified_b_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  a_variant_active = civic_bosch_modified_a_lateral_testing_ground_active()
  variant_active = civic_bosch_modified_lateral_testing_ground_active()

  friction_scale = 1.0
  friction_scale += (_civic_bosch_modified_b_side_value(desired_lateral_accel,
                                                         CIVIC_BOSCH_MODIFIED_B_TURN_IN_FRICTION_BOOST_LEFT,
                                                         CIVIC_BOSCH_MODIFIED_B_TURN_IN_FRICTION_BOOST_RIGHT) *
                     envelope * turn_in_weight)
  if a_variant_active:
    friction_scale += (_civic_bosch_modified_b_side_value(desired_lateral_accel,
                                                           CIVIC_BOSCH_MODIFIED_A_VARIANT_TURN_IN_FRICTION_BOOST_LEFT,
                                                           CIVIC_BOSCH_MODIFIED_A_VARIANT_TURN_IN_FRICTION_BOOST_RIGHT) *
                       envelope * turn_in_weight)
  if variant_active:
    friction_scale += (_civic_bosch_modified_b_side_value(desired_lateral_accel,
                                                           CIVIC_BOSCH_MODIFIED_B_VARIANT_TURN_IN_FRICTION_BOOST_LEFT,
                                                           CIVIC_BOSCH_MODIFIED_B_VARIANT_TURN_IN_FRICTION_BOOST_RIGHT) *
                       envelope * turn_in_weight)
  friction_scale -= (_civic_bosch_modified_b_side_value(desired_lateral_accel,
                                                         CIVIC_BOSCH_MODIFIED_B_UNWIND_FRICTION_REDUCTION_LEFT,
                                                         CIVIC_BOSCH_MODIFIED_B_UNWIND_FRICTION_REDUCTION_RIGHT) *
                     envelope * unwind_weight)
  if a_variant_active:
    friction_scale -= (_civic_bosch_modified_b_side_value(desired_lateral_accel,
                                                           CIVIC_BOSCH_MODIFIED_A_VARIANT_UNWIND_FRICTION_REDUCTION_LEFT,
                                                           CIVIC_BOSCH_MODIFIED_A_VARIANT_UNWIND_FRICTION_REDUCTION_RIGHT) *
                       envelope * unwind_weight)
  if variant_active:
    friction_scale -= (_civic_bosch_modified_b_side_value(desired_lateral_accel,
                                                           CIVIC_BOSCH_MODIFIED_B_VARIANT_UNWIND_FRICTION_REDUCTION_LEFT,
                                                           CIVIC_BOSCH_MODIFIED_B_VARIANT_UNWIND_FRICTION_REDUCTION_RIGHT) *
                       envelope * unwind_weight)
  return min(max(friction_scale, 0.82), 1.06)


def bolt_2017_lateral_testing_ground_active() -> bool:
  return testing_ground.use(BOLT_2017_LATERAL_TESTING_GROUND_ID)


def _bolt_2017_sigmoid(x: float) -> float:
  return _sigmoid(x)


def _bolt_2017_high_speed_factor(v_ego: float) -> float:
  return _bolt_2017_sigmoid((max(v_ego, 0.0) - BOLT_2017_STEER_RATIO_ONSET_SPEED) / BOLT_2017_STEER_RATIO_ONSET_WIDTH)


def get_bolt_2017_steer_ratio_scale(v_ego: float) -> float:
  return 1.0 + ((BOLT_2017_STEER_RATIO_TEST_SCALE - 1.0) * _bolt_2017_high_speed_factor(v_ego))


def get_honda_accord_steer_ratio(steer_angle_deg: float, level: float | None = None) -> float:
  """Local ratio of the Accord's variable-ratio rack at the current wheel angle.

  `level` is the desired ON-CENTRE ratio (the SteerRatio toggle).  It scales the whole
  curve by level / NOMINAL, so the rack geometry measured off the car is preserved and
  only the calibration level moves.  None (or NOMINAL) leaves the map untouched.

  sR sits in the MEASUREMENT path -- VehicleModel.calc_curvature -- so a HIGHER level makes the
  controller read LESS curvature than it has, and the closed loop settles ABOVE its command.
  Unlike a feedforward trim this is not undone by the integrator, because the integrator drives
  the (biased) error to zero: the loop converges perfectly onto the wrong road curvature while
  pid_log.error still reads 0.  On this fork sR enters a SECOND time -- the rate-plant feedforward
  builds angle_des through it -- so a high level asks for more angle AND reads back less curvature.
  Both push the same way, and neither produces an error the controller can see.

  🛑 SUPERSEDED 2026-09-11: the old "a FLAT defect wants a FLAT fix, neutral is 16.00/1.116 = 14.3"
  derivation is WITHDRAWN.  It rested on r39/r3a/r3c (n=38 curves) and on the claim that the
  over-delivery was angle-independent (p=0.71).  Re-measured over 82 routes with a per-route free
  intercept, the defect is NOT flat: the served curve ran ~0.57 too LOW below 36 deg and up to
  +0.62 too HIGH at 165-210 deg, with the sign flipping at ~50 deg.  A flat level change would have
  traded the corner for the straight.  The fix was a RESHAPE of the knots above, not a level move;
  see the comment on HONDA_ACCORD_STEER_RATIO_V for the measurement, the bands and the three
  segments that are conventions rather than data.  The level lever remains available and is now
  honestly bounded: LEVEL +/-0.57 (the gyro-vs-wheel-speed yaw-scale term, multiplicative and
  constant), against SHAPE +/-0.12.
  """
  ratio = float(np.interp(abs(steer_angle_deg), HONDA_ACCORD_STEER_RATIO_ANGLE_BP, HONDA_ACCORD_STEER_RATIO_V))
  if level is not None:
    scale = float(level) / HONDA_ACCORD_STEER_RATIO_NOMINAL
    ratio *= min(max(scale, HONDA_ACCORD_STEER_RATIO_LEVEL_MIN), HONDA_ACCORD_STEER_RATIO_LEVEL_MAX)
  return ratio


def get_honda_accord_ff_scale(desired_lateral_accel: float) -> float:
  """Taper only sharp-turn feedforward where the Accord carries excess curvature."""
  turn_weight = _sigmoid((abs(desired_lateral_accel) - HONDA_ACCORD_TURN_FF_ONSET) /
                         HONDA_ACCORD_TURN_FF_WIDTH)
  return 1.0 - (HONDA_ACCORD_TURN_FF_REDUCTION_MAX * turn_weight)


def get_honda_accord_rate_plant_ff(angle_des_deg: float, angle_des_rate_dps: float, v_ego: float,
                                   rate_gain: float = HONDA_ACCORD_FF_RATE_GAIN,
                                   gain_scale: float = 1.0, spring_scale: float = 1.0,
                                   hold_map: bool = False, hold_level: bool = True) -> float:
  """Feedforward TORQUE (units of the [-1, 1] output) for the Accord's rate-servo EPS.

  hold term  k(v) * angle / G(v)   -- the torque that balances the return spring at angle_des
             (hold_map=True: the measured saturating V293 map, get_honda_accord_hold_torque)
  move term  gain * d(angle)/dt / G(v) -- the torque that drives the wheel toward angle_des
  Both are in the steering-angle sign frame (positive = left); the caller converts to the
  controller's internal frame.  The P/I terms stay in lateral-acceleration space and are
  unchanged, so the SteerLatAccel toggle scales only P/I once this feedforward is in use.
  """
  angle_des_deg = float(np.clip(angle_des_deg, -HONDA_ACCORD_FF_ANGLE_LIMIT_DEG, HONDA_ACCORD_FF_ANGLE_LIMIT_DEG))
  # gain_scale / spring_scale (AccordEpsGainScale / AccordEpsSpringScale) let the tables be corrected
  # from Galaxy after an EPS firmware change, until the plant is re-identified and the tables updated.
  gain = float(np.interp(v_ego, HONDA_ACCORD_EPS_G_BP, HONDA_ACCORD_EPS_G_V)) * max(float(gain_scale), 0.1)
  if hold_map:
    # the measured saturating hold map (AccordHoldMap); spring_scale still scales it, gain_scale does not
    hold_torque = get_honda_accord_hold_torque(angle_des_deg, v_ego, level=hold_level) * float(spring_scale)
  else:
    spring = float(np.interp(v_ego, HONDA_ACCORD_EPS_K_BP, HONDA_ACCORD_EPS_K_V)) * float(spring_scale)
    hold_torque = spring * angle_des_deg / gain
  move_limit = get_honda_accord_ff_move_torque_limit(v_ego)
  move_torque = float(np.clip(rate_gain * angle_des_rate_dps / gain, -move_limit, move_limit))
  return hold_torque + move_torque


def get_honda_accord_ff_move_torque_limit(v_ego: float) -> float:
  """Magnitude limit on the move term of get_honda_accord_rate_plant_ff (see the constants)."""
  return float(np.interp(v_ego, HONDA_ACCORD_FF_MOVE_TORQUE_LIMIT_BP, HONDA_ACCORD_FF_MOVE_TORQUE_LIMIT_V))


def get_honda_accord_hold_sat_deg(v_ego: float) -> float:
  a, b, c = HONDA_ACCORD_HOLD_SAT_DEG
  return a + b * math.exp(-max(float(v_ego), 0.0) / c)


def get_honda_accord_hold_level(v_ego: float, level: bool = True) -> float:
  """Speed-scheduled level correction on the hold map (see the HONDA_ACCORD_HOLD_LEVEL_* constants).
  Read ONLY by get_honda_accord_hold_torque -- never by get_honda_accord_mode_hz, which shares the k table.
  level=False is the rev 3-5 map (AccordHoldLevel off)."""
  if not level:
    return 1.0
  return float(np.interp(v_ego, HONDA_ACCORD_HOLD_LEVEL_BP, HONDA_ACCORD_HOLD_LEVEL_V))


def get_honda_accord_hold_torque(angle_deg: float, v_ego: float, level: bool = True) -> float:
  """Static hold torque (spring part, +left frame) from the measured V293 hold map: k(v) * sat(v) * tanh(angle / sat(v)).
  Odd in the angle; the static friction is NOT included (see HONDA_ACCORD_HOLD_STATIC_FRICTION).
  level=True (AccordHoldLevel) multiplies k(v) by HONDA_ACCORD_HOLD_LEVEL_V(v); level=False is the rev 3-5 map."""
  angle_deg = float(np.clip(angle_deg, -HONDA_ACCORD_FF_ANGLE_LIMIT_DEG, HONDA_ACCORD_FF_ANGLE_LIMIT_DEG))
  k = float(np.interp(v_ego, HONDA_ACCORD_HOLD_V_BP, HONDA_ACCORD_HOLD_K_V)) * get_honda_accord_hold_level(v_ego, level)
  sat = get_honda_accord_hold_sat_deg(v_ego)
  return k * sat * math.tanh(angle_deg / sat)


def get_honda_accord_mode_hz(v_ego: float) -> float:
  """Frequency of the steering system's own mode on the V293 firmware, sqrt(k(v) / J) / 2pi."""
  k = float(np.interp(v_ego, HONDA_ACCORD_HOLD_V_BP, HONDA_ACCORD_HOLD_K_V))
  return math.sqrt(k / HONDA_ACCORD_EPS_INERTIA) / (2.0 * math.pi)


def get_honda_accord_torque_ki(v_ego: float, ki_low: float, ki_high: float) -> float:
  """Speed-scheduled integral gain: ki_low below HONDA_ACCORD_KI_SCHEDULE_V_BP[0], ki_high from [1], linear between.
  ki_high <= 0 disables the schedule (flat ki_low, the rev-3 behaviour)."""
  if ki_high <= 0.0:
    return float(ki_low)
  return float(np.interp(v_ego, HONDA_ACCORD_KI_SCHEDULE_V_BP, [float(ki_low), float(ki_high)]))


def get_honda_accord_rate_loop_gain(v_ego: float, gain: float) -> float:
  """AccordRateLoopGain tapered above HONDA_ACCORD_RATE_LOOP_TAPER_V (torque per deg/s)."""
  return float(gain) * min(1.0, HONDA_ACCORD_RATE_LOOP_TAPER_V / max(float(v_ego), 0.1))


def get_honda_accord_friction_hyst_band(v_ego: float, scheduled: bool = True) -> float:
  """Desired-angle travel (deg) that swings the static-friction hysteresis term end to end, at this speed.
  See the HONDA_ACCORD_FRICTION_HYST_BAND_* constants.  scheduled=False is the rev 3-5 flat band."""
  if not scheduled:
    return HONDA_ACCORD_FRICTION_HYST_BAND_DEG
  return float(np.interp(v_ego, HONDA_ACCORD_FRICTION_HYST_BAND_BP, HONDA_ACCORD_FRICTION_HYST_BAND_V))


def honda_accord_friction_hysteresis(z: float, d_angle_des_deg: float, friction: float,
                                     band_deg: float = HONDA_ACCORD_FRICTION_HYST_BAND_DEG) -> float:
  """One step of the static-friction hysteresis operator: z follows the desired angle's motion at
  friction / band_deg torque per degree and is clipped to +/- friction, so it reads +friction after the
  wheel was asked to move left, -friction after right, and swings between them over band_deg of travel."""
  if friction <= 0.0:
    return 0.0
  z = float(z) + float(d_angle_des_deg) * float(friction) / max(float(band_deg), 1e-3)
  return float(np.clip(z, -friction, friction))


class HondaAccordErrorNotch:
  """Second-order notch (bilinear, coefficients recomputed every frame so it tracks the mode with speed)
  on the lateral-accel error before P and I.  Q <= 0 passes the input through and keeps the state primed."""

  def __init__(self, dt: float):
    self.dt = dt
    self.reset()

  def reset(self, x0: float = 0.0):
    self.x1 = self.x2 = self.y1 = self.y2 = float(x0)

  def update(self, x: float, f_hz: float, q: float) -> float:
    x = float(x)
    if q <= 0.0 or f_hz <= 0.0:
      self.x1 = self.x2 = self.y1 = self.y2 = x
      return x
    k = math.tan(math.pi * min(float(f_hz), 0.45 / self.dt) * self.dt)
    norm = 1.0 / (1.0 + k / q + k * k)
    b0 = (1.0 + k * k) * norm
    b1 = 2.0 * (k * k - 1.0) * norm
    a2 = (1.0 - k / q + k * k) * norm
    y = b0 * x + b1 * self.x1 + b0 * self.x2 - b1 * self.y1 - a2 * self.y2
    self.x2, self.x1, self.y2, self.y1 = self.x1, x, self.y1, y
    return y


class HondaAccordDisturbanceObserver:
  """Model-based disturbance observer for the V293 torque-map EPS (see the HONDA_ACCORD_DOB_* constants).
  update() takes the +left-frame measured angle / rate, the speed and the controller's own output torque of THIS
  frame (torque frame; it is delayed internally by HONDA_ACCORD_DOB_DELAY), and returns the unmodelled torque estimate
  in the +left frame, faded by speed and clipped.  f_hz <= 0 disables it (returns 0, keeps the state at rest)."""

  def __init__(self, dt: float):
    self.dt = dt
    self.n_delay = max(int(round(HONDA_ACCORD_DOB_DELAY / dt)), 1)
    self.reset()

  def reset(self, rate_deg_s: float = 0.0):
    self.u_hist = [0.0] * self.n_delay        # +left-frame torque, oldest first
    self.w1 = 0.0                             # first pole state
    self.w2 = 0.0                             # second pole state = the estimate before fade/clip
    self.prev_rate = float(rate_deg_s)
    self.acc = 0.0
    self.residual = 0.0

  def update(self, angle_deg: float, rate_deg_s: float, v_ego: float, output_torque: float, f_hz: float,
             hold_torque_fn, hold_map: bool = True, gain_scale: float = 1.0, spring_scale: float = 1.0,
             freeze: bool = False) -> float:
    rate_deg_s = float(rate_deg_s)
    if f_hz <= 0.0:
      self.reset(rate_deg_s)
      return 0.0
    # controller torque frame -> +left plant frame (plant_ff_torque = -get_honda_accord_rate_plant_ff(...))
    u_left_now = -float(output_torque)
    u_left_delayed = self.u_hist[0]
    self.u_hist.append(u_left_now); self.u_hist.pop(0)
    # the model: hold(angle) + b(v) rate + J acc, b = 1/G(v) (the fork's own viscous term)
    if hold_map:
      spring = float(hold_torque_fn(angle_deg, v_ego)) * float(spring_scale)
    else:
      spring = get_honda_accord_rate_plant_ff(angle_deg, 0.0, v_ego, 0.0, gain_scale, spring_scale, hold_map=False)
    b_model = 1.0 / (float(np.interp(v_ego, HONDA_ACCORD_EPS_G_BP, HONDA_ACCORD_EPS_G_V)) * max(float(gain_scale), 0.1))
    alpha_acc = self.dt / (HONDA_ACCORD_DOB_ACC_RC + self.dt)
    self.acc += alpha_acc * ((rate_deg_s - self.prev_rate) / self.dt - self.acc)
    self.prev_rate = rate_deg_s
    self.residual = u_left_delayed - (spring + b_model * rate_deg_s + HONDA_ACCORD_EPS_INERTIA * self.acc)
    if not freeze:
      alpha = self.dt / (1.0 / (2.0 * math.pi * float(f_hz)) + self.dt)
      self.w1 += alpha * (self.residual - self.w1)
      self.w2 += alpha * (self.w1 - self.w2)
    fade = float(np.interp(v_ego, HONDA_ACCORD_DOB_FADE_V_BP, [0.0, 1.0]))
    return float(np.clip(self.w2 * fade, -HONDA_ACCORD_DOB_MAX_TORQUE, HONDA_ACCORD_DOB_MAX_TORQUE))


def get_bolt_2017_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  center_window = _bolt_2017_sigmoid((BOLT_2017_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / BOLT_2017_CENTER_TAPER_WIDTH)
  return 1.0 - (BOLT_2017_CENTER_TAPER_GAIN * _bolt_2017_high_speed_factor(v_ego) * center_window)


def _bolt_2017_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / BOLT_2017_TRANSITION_SPEED) ** 2)


def _bolt_2017_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / BOLT_2017_PHASE_SCALE)


def _bolt_2017_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def get_bolt_2017_base_torque_scale(desired_lateral_accel: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  scale_values = BOLT_2017_TORQUE_SCALE_LEFT if desired_lateral_accel > 0.0 else BOLT_2017_TORQUE_SCALE_RIGHT
  return float(np.interp(abs(desired_lateral_accel), BOLT_2017_TORQUE_SCALE_BP, scale_values))


def get_bolt_2017_torque_scale(desired_lateral_accel: float, desired_lateral_jerk: float = 0.0, v_ego: float = 30.0) -> float:
  base_scale = get_bolt_2017_base_torque_scale(desired_lateral_accel)
  scale = base_scale
  if base_scale > 1.0 and desired_lateral_jerk != 0.0:
    low_speed_factor = _bolt_2017_low_speed_factor(v_ego)
    phase = _bolt_2017_transition_phase(desired_lateral_accel, desired_lateral_jerk)
    turn_in_weight = max(phase, 0.0)
    unwind_weight = max(-phase, 0.0)
    turn_in_boost = 1.0 + (_bolt_2017_side_value(desired_lateral_accel, BOLT_2017_TURN_IN_BOOST_LEFT, BOLT_2017_TURN_IN_BOOST_RIGHT) *
                            turn_in_weight * (0.35 + 0.65 * low_speed_factor))
    unwind_taper = 1.0 - (_bolt_2017_side_value(desired_lateral_accel, BOLT_2017_UNWIND_TAPER_LEFT, BOLT_2017_UNWIND_TAPER_RIGHT) *
                           unwind_weight * (0.45 + 0.55 * low_speed_factor))
    scale = 1.0 + ((base_scale - 1.0) * turn_in_boost * max(unwind_taper, 0.0))

  return scale * get_bolt_2017_center_taper_scale(desired_lateral_accel, v_ego)


def bolt_2018_2021_lateral_testing_ground_active() -> bool:
  return testing_ground.use(BOLT_2018_2021_LATERAL_TESTING_GROUND_ID)


def _bolt_2018_2021_sigmoid(x: float) -> float:
  return _sigmoid(x)


def _bolt_2018_2021_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / BOLT_2018_2021_TRANSITION_SPEED) ** 2)


def _bolt_2018_2021_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / BOLT_2018_2021_PHASE_SCALE)


def _bolt_2018_2021_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def _bolt_2018_2021_transition_envelope(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  lat_factor = 1.0 - math.exp(-abs(desired_lateral_accel) / BOLT_2018_2021_FRICTION_LAT_RISE)
  jerk_factor = 1.0 - math.exp(-abs(desired_lateral_jerk) / BOLT_2018_2021_FRICTION_JERK_RISE)
  return _bolt_2018_2021_low_speed_factor(v_ego) * lat_factor * jerk_factor


def get_bolt_2018_2021_torque_scale(desired_lateral_accel: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  gain = BOLT_2018_2021_TORQUE_GAIN_LEFT if desired_lateral_accel > 0.0 else BOLT_2018_2021_TORQUE_GAIN_RIGHT
  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _bolt_2018_2021_sigmoid((abs_lateral_accel - BOLT_2018_2021_TORQUE_ONSET) / BOLT_2018_2021_TORQUE_ONSET_WIDTH)
  cutoff = _bolt_2018_2021_sigmoid((BOLT_2018_2021_TORQUE_CUTOFF - abs_lateral_accel) / BOLT_2018_2021_TORQUE_CUTOFF_WIDTH)
  return 1.0 + gain * onset * cutoff


def get_bolt_2018_2021_dynamic_torque_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  base_scale = get_bolt_2018_2021_torque_scale(desired_lateral_accel)
  extra_scale = max(base_scale - 1.0, 0.0)
  abs_lateral_accel = abs(desired_lateral_accel)
  low_speed_factor = _bolt_2018_2021_low_speed_factor(v_ego)
  high_speed_factor = 1.0 - low_speed_factor
  center_window = _bolt_2018_2021_sigmoid((BOLT_2018_2021_CENTER_TAPER_LAT - abs_lateral_accel) / BOLT_2018_2021_CENTER_TAPER_WIDTH)
  center_taper = 1.0 - (BOLT_2018_2021_CENTER_TAPER_GAIN * high_speed_factor * center_window)
  phase = _bolt_2018_2021_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  jerk_taper = 1.0 / (1.0 + (abs(desired_lateral_jerk) / BOLT_2018_2021_JERK_TAPER_CUTOFF) ** 2)
  turn_in_boost = 1.0 + (_bolt_2018_2021_side_value(desired_lateral_accel, BOLT_2018_2021_TURN_IN_BOOST_LEFT, BOLT_2018_2021_TURN_IN_BOOST_RIGHT) *
                          turn_in_weight * low_speed_factor)
  unwind_weight = max(-phase, 0.0)
  unwind_taper = 1.0 - (_bolt_2018_2021_side_value(desired_lateral_accel, BOLT_2018_2021_UNWIND_TAPER_GAIN_LEFT, BOLT_2018_2021_UNWIND_TAPER_GAIN_RIGHT) *
                         unwind_weight * (0.55 + 0.45 * low_speed_factor))
  return 1.0 + (extra_scale * center_taper * jerk_taper * turn_in_boost * max(unwind_taper, 0.0))


def get_bolt_2018_2021_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0, desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = get_gm_base_friction_threshold(v_ego)
  transition_envelope = _bolt_2018_2021_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _bolt_2018_2021_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  threshold_scale = 1.0 - (_bolt_2018_2021_side_value(desired_lateral_accel, BOLT_2018_2021_TURN_IN_THRESHOLD_REDUCTION_LEFT, BOLT_2018_2021_TURN_IN_THRESHOLD_REDUCTION_RIGHT) *
                           transition_envelope * turn_in_weight)
  threshold_scale += (_bolt_2018_2021_side_value(desired_lateral_accel, BOLT_2018_2021_UNWIND_THRESHOLD_INCREASE_LEFT, BOLT_2018_2021_UNWIND_THRESHOLD_INCREASE_RIGHT) *
                      transition_envelope * unwind_weight)
  return base_threshold * min(max(threshold_scale, 0.82), 1.12)


def get_bolt_2018_2021_friction_scale(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  transition_envelope = _bolt_2018_2021_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _bolt_2018_2021_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  friction_scale = BOLT_2018_2021_FRICTION_MULT
  friction_scale += (_bolt_2018_2021_side_value(desired_lateral_accel, BOLT_2018_2021_TURN_IN_FRICTION_BOOST_LEFT, BOLT_2018_2021_TURN_IN_FRICTION_BOOST_RIGHT) *
                     transition_envelope * turn_in_weight)
  friction_scale -= (_bolt_2018_2021_side_value(desired_lateral_accel, BOLT_2018_2021_UNWIND_FRICTION_REDUCTION_LEFT, BOLT_2018_2021_UNWIND_FRICTION_REDUCTION_RIGHT) *
                     transition_envelope * unwind_weight)
  return min(max(friction_scale, 0.88), 1.10)


def bolt_2022_2023_lateral_testing_ground_active() -> bool:
  return testing_ground.use(BOLT_2022_2023_LATERAL_TESTING_GROUND_ID)


def _bolt_2022_2023_sigmoid(x: float) -> float:
  return _sigmoid(x)


def _bolt_2022_2023_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / BOLT_2022_2023_TRANSITION_SPEED) ** 2)


def _bolt_2022_2023_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / BOLT_2022_2023_PHASE_SCALE)


def _bolt_2022_2023_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def _bolt_2022_2023_transition_envelope(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  lat_factor = 1.0 - math.exp(-abs(desired_lateral_accel) / BOLT_2022_2023_FRICTION_LAT_RISE)
  jerk_factor = 1.0 - math.exp(-abs(desired_lateral_jerk) / BOLT_2022_2023_FRICTION_JERK_RISE)
  return _bolt_2022_2023_low_speed_factor(v_ego) * lat_factor * jerk_factor


def get_bolt_2022_2023_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  gain = _bolt_2022_2023_side_value(
    desired_lateral_accel,
    _flm_vehicle_knob("gm_bolt_2022_2023.ff_gain_left", BOLT_2022_2023_FF_GAIN_LEFT),
    _flm_vehicle_knob("gm_bolt_2022_2023.ff_gain_right", BOLT_2022_2023_FF_GAIN_RIGHT),
  )
  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _bolt_2022_2023_sigmoid((abs_lateral_accel - BOLT_2022_2023_FF_ONSET) / BOLT_2022_2023_FF_ONSET_WIDTH)
  cutoff = _bolt_2022_2023_sigmoid((BOLT_2022_2023_FF_CUTOFF - abs_lateral_accel) / BOLT_2022_2023_FF_CUTOFF_WIDTH)
  extra_scale = gain * onset * cutoff
  speed_weight = _bolt_2022_2023_sigmoid((v_ego - BOLT_2022_2023_CENTER_TAPER_SPEED) / BOLT_2022_2023_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _bolt_2022_2023_sigmoid((BOLT_2022_2023_CENTER_TAPER_LAT - abs_lateral_accel) / BOLT_2022_2023_CENTER_TAPER_LAT_WIDTH)
  center_taper = 1.0 - (_flm_vehicle_knob("gm_bolt_2022_2023.center_taper_max", BOLT_2022_2023_CENTER_TAPER_MAX) * speed_weight * center_weight)
  low_speed_factor = _bolt_2022_2023_low_speed_factor(v_ego)
  transition_envelope = _bolt_2022_2023_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _bolt_2022_2023_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  turn_in_boost = 1.0 + (_bolt_2022_2023_side_value(
                          desired_lateral_accel,
                          _flm_vehicle_knob("gm_bolt_2022_2023.turn_in_boost_left", BOLT_2022_2023_TURN_IN_BOOST_LEFT),
                          _flm_vehicle_knob("gm_bolt_2022_2023.turn_in_boost_right", BOLT_2022_2023_TURN_IN_BOOST_RIGHT),
                        ) *
                          turn_in_weight * low_speed_factor)
  unwind_envelope = (0.25 + 0.75 * low_speed_factor) * (1.0 + 0.45 * transition_envelope)
  unwind_taper = 1.0 - (_bolt_2022_2023_side_value(
                         desired_lateral_accel,
                         _flm_vehicle_knob("gm_bolt_2022_2023.unwind_taper_left", BOLT_2022_2023_UNWIND_TAPER_LEFT),
                         _flm_vehicle_knob("gm_bolt_2022_2023.unwind_taper_right", BOLT_2022_2023_UNWIND_TAPER_RIGHT),
                       ) *
                         unwind_weight * unwind_envelope)
  return 1.0 + (extra_scale * center_taper * turn_in_boost * max(unwind_taper, 0.0))


def get_bolt_2022_2023_center_output_scale(desired_lateral_accel: float, v_ego: float) -> float:
  highway_speed_weight = _bolt_2022_2023_sigmoid((v_ego - BOLT_2022_2023_CENTER_TAPER_SPEED) /
                                                  BOLT_2022_2023_CENTER_TAPER_SPEED_WIDTH)
  highway_center_weight = _bolt_2022_2023_sigmoid((BOLT_2022_2023_CENTER_TAPER_LAT - abs(desired_lateral_accel)) /
                                                   BOLT_2022_2023_CENTER_TAPER_LAT_WIDTH)
  low_speed_onset = _bolt_2022_2023_sigmoid((v_ego - BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_SPEED) /
                                             BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_SPEED_WIDTH)
  low_speed_cutoff = _bolt_2022_2023_sigmoid((BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_SPEED_MAX - v_ego) /
                                              BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_SPEED_MAX_WIDTH)
  low_speed_center_weight = _bolt_2022_2023_sigmoid((BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_LAT - abs(desired_lateral_accel)) /
                                                     BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_LAT_WIDTH)
  low_speed_floor = _bolt_2022_2023_sigmoid(
    (v_ego - BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_FLOOR) /
    BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_FLOOR_WIDTH
  )
  highway_reduction = (_flm_vehicle_knob("gm_bolt_2022_2023.center_taper_max", BOLT_2022_2023_CENTER_TAPER_MAX) *
                       highway_speed_weight * highway_center_weight)
  low_speed_reduction = (BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_MAX * low_speed_onset * low_speed_cutoff *
                         low_speed_center_weight * low_speed_floor)
  return 1.0 - min(highway_reduction + low_speed_reduction, 0.95)


def get_bolt_2022_2023_low_speed_center_output_limit(desired_lateral_accel: float, v_ego: float) -> float:
  """Limit small-signal output while the Bolt is in its low-speed chatter band."""
  speed_onset = _bolt_2022_2023_sigmoid(
    (v_ego - BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED) /
    BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_WIDTH
  )
  speed_cutoff = _bolt_2022_2023_sigmoid(
    (BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_MAX - v_ego) /
    BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_MAX_WIDTH
  )
  center_weight = _bolt_2022_2023_sigmoid(
    (BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_LAT - abs(desired_lateral_accel)) /
    BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_LAT_WIDTH
  )
  speed_weight = speed_onset * speed_cutoff
  reduction = (1.0 - BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_LIMIT) * speed_weight * center_weight
  return 1.0 - reduction


def get_bolt_2022_2023_low_speed_center_output(output_torque: float, prev_output_torque: float,
                                               desired_lateral_accel: float, v_ego: float) -> float:
  """Damp low-speed center reversals without reducing real turn authority."""
  speed_weight = _bolt_2022_2023_sigmoid(
    (v_ego - BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED) /
    BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_WIDTH
  ) * _bolt_2022_2023_sigmoid(
    (BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_MAX - v_ego) /
    BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_MAX_WIDTH
  )
  center_weight = _bolt_2022_2023_sigmoid(
    (BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_LAT - abs(desired_lateral_accel)) /
    BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_LAT_WIDTH
  )
  envelope = speed_weight * center_weight
  output_scale = 1.0 - ((1.0 - BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SCALE_MIN) * envelope)
  output_alpha = 1.0 - ((1.0 - BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_ALPHA_MIN) * envelope)
  limited_output = output_torque * output_scale
  return float(prev_output_torque + output_alpha * (limited_output - prev_output_torque))


def get_bolt_2022_2023_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0, desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = get_gm_base_friction_threshold(v_ego)
  center_weight = _bolt_2022_2023_sigmoid(
    (BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_LAT - abs(desired_lateral_accel)) /
    BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_LAT_WIDTH
  )
  low_speed_weight = _bolt_2022_2023_sigmoid(
    (BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_SPEED - v_ego) /
    BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_SPEED_WIDTH
  )
  base_threshold += (BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_BUMP * center_weight * low_speed_weight)
  transition_envelope = _bolt_2022_2023_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _bolt_2022_2023_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  threshold_scale = 1.0 - (_bolt_2022_2023_side_value(
                           desired_lateral_accel,
                           _flm_vehicle_knob("gm_bolt_2022_2023.turn_in_threshold_reduction_left", BOLT_2022_2023_TURN_IN_THRESHOLD_REDUCTION_LEFT),
                           _flm_vehicle_knob("gm_bolt_2022_2023.turn_in_threshold_reduction_right", BOLT_2022_2023_TURN_IN_THRESHOLD_REDUCTION_RIGHT),
                         ) *
                           transition_envelope * turn_in_weight)
  threshold_scale += (_bolt_2022_2023_side_value(
                      desired_lateral_accel,
                      _flm_vehicle_knob("gm_bolt_2022_2023.unwind_threshold_increase_left", BOLT_2022_2023_UNWIND_THRESHOLD_INCREASE_LEFT),
                      _flm_vehicle_knob("gm_bolt_2022_2023.unwind_threshold_increase_right", BOLT_2022_2023_UNWIND_THRESHOLD_INCREASE_RIGHT),
                    ) *
                      transition_envelope * unwind_weight)
  return base_threshold * min(max(threshold_scale, 0.84), 1.14)


def get_bolt_2022_2023_friction_scale(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  transition_envelope = _bolt_2022_2023_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _bolt_2022_2023_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  friction_scale = BOLT_2022_2023_FRICTION_MULT
  friction_scale += (_bolt_2022_2023_side_value(desired_lateral_accel, BOLT_2022_2023_TURN_IN_FRICTION_BOOST_LEFT, BOLT_2022_2023_TURN_IN_FRICTION_BOOST_RIGHT) *
                     transition_envelope * turn_in_weight)
  friction_scale -= (_bolt_2022_2023_side_value(desired_lateral_accel, BOLT_2022_2023_UNWIND_FRICTION_REDUCTION_LEFT, BOLT_2022_2023_UNWIND_FRICTION_REDUCTION_RIGHT) *
                     transition_envelope * unwind_weight)
  return min(max(friction_scale, 0.92), 1.22)


def volt_standard_lateral_testing_ground_active() -> bool:
  return testing_ground.use(VOLT_STANDARD_LATERAL_TESTING_GROUND_ID)


def _volt_standard_sigmoid(x: float) -> float:
  return _sigmoid(x)


def _volt_standard_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / VOLT_STANDARD_TRANSITION_SPEED) ** 2)


def _volt_standard_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / VOLT_STANDARD_PHASE_SCALE)


def _volt_standard_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def _volt_standard_transition_envelope(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  lat_factor = 1.0 - math.exp(-abs(desired_lateral_accel) / VOLT_STANDARD_FRICTION_LAT_RISE)
  jerk_factor = 1.0 - math.exp(-abs(desired_lateral_jerk) / VOLT_STANDARD_FRICTION_JERK_RISE)
  return _volt_standard_low_speed_factor(v_ego) * lat_factor * jerk_factor


def get_volt_standard_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  gain = _volt_standard_side_value(desired_lateral_accel, VOLT_STANDARD_FF_GAIN_LEFT, VOLT_STANDARD_FF_GAIN_RIGHT)
  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _volt_standard_sigmoid((abs_lateral_accel - VOLT_STANDARD_FF_ONSET) / VOLT_STANDARD_FF_ONSET_WIDTH)
  cutoff = _volt_standard_sigmoid((VOLT_STANDARD_FF_CUTOFF - abs_lateral_accel) / VOLT_STANDARD_FF_CUTOFF_WIDTH)
  extra_scale = gain * onset * cutoff
  phase = _volt_standard_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  low_speed_factor = _volt_standard_low_speed_factor(v_ego)
  turn_in_boost = 1.0 + (_volt_standard_side_value(desired_lateral_accel, VOLT_STANDARD_TURN_IN_BOOST_LEFT, VOLT_STANDARD_TURN_IN_BOOST_RIGHT) *
                          turn_in_weight * low_speed_factor)
  unwind_taper = 1.0 - (_volt_standard_side_value(desired_lateral_accel, VOLT_STANDARD_UNWIND_TAPER_LEFT, VOLT_STANDARD_UNWIND_TAPER_RIGHT) *
                         unwind_weight * (0.30 + 0.70 * low_speed_factor))
  return 1.0 + (extra_scale * turn_in_boost * max(unwind_taper, 0.0))


def get_volt_standard_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0, desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = get_gm_base_friction_threshold(v_ego)
  transition_envelope = _volt_standard_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _volt_standard_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  threshold_scale = 1.0 - (_volt_standard_side_value(desired_lateral_accel, VOLT_STANDARD_TURN_IN_THRESHOLD_REDUCTION_LEFT, VOLT_STANDARD_TURN_IN_THRESHOLD_REDUCTION_RIGHT) *
                           transition_envelope * turn_in_weight)
  threshold_scale += (_volt_standard_side_value(desired_lateral_accel, VOLT_STANDARD_UNWIND_THRESHOLD_INCREASE_LEFT, VOLT_STANDARD_UNWIND_THRESHOLD_INCREASE_RIGHT) *
                      transition_envelope * unwind_weight)
  return base_threshold * min(max(threshold_scale, 0.84), 1.12)


def get_volt_standard_friction_scale(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  transition_envelope = _volt_standard_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _volt_standard_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  friction_scale = VOLT_STANDARD_FRICTION_MULT
  friction_scale += (_volt_standard_side_value(desired_lateral_accel, VOLT_STANDARD_TURN_IN_FRICTION_BOOST_LEFT, VOLT_STANDARD_TURN_IN_FRICTION_BOOST_RIGHT) *
                     transition_envelope * turn_in_weight)
  friction_scale -= (_volt_standard_side_value(desired_lateral_accel, VOLT_STANDARD_UNWIND_FRICTION_REDUCTION_LEFT, VOLT_STANDARD_UNWIND_FRICTION_REDUCTION_RIGHT) *
                     transition_envelope * unwind_weight)
  return min(max(friction_scale, 0.90), 1.14)


def get_volt_standard_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _volt_standard_sigmoid((v_ego - VOLT_STANDARD_CENTER_TAPER_SPEED) / VOLT_STANDARD_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _volt_standard_sigmoid((VOLT_STANDARD_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / VOLT_STANDARD_CENTER_TAPER_LAT_WIDTH)
  reduction = VOLT_STANDARD_CENTER_TAPER_MAX * speed_weight * center_weight
  return 1.0 - reduction


def get_silverado_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _sigmoid((v_ego - SILVERADO_CENTER_TAPER_SPEED) / SILVERADO_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _sigmoid((SILVERADO_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / SILVERADO_CENTER_TAPER_LAT_WIDTH)
  reduction = SILVERADO_CENTER_TAPER_MAX * speed_weight * center_weight
  return 1.0 - reduction


def _sonata_hybrid_sigmoid(x: float) -> float:
  return _sigmoid(x)


def _sonata_hybrid_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / SONATA_HYBRID_TRANSITION_SPEED) ** 2)


def _sonata_hybrid_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / SONATA_HYBRID_PHASE_SCALE)


def _sonata_hybrid_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def get_sonata_hybrid_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _sonata_hybrid_sigmoid((abs_lateral_accel - SONATA_HYBRID_FF_ONSET) / SONATA_HYBRID_FF_ONSET_WIDTH)
  cutoff = _sonata_hybrid_sigmoid((SONATA_HYBRID_FF_CUTOFF - abs_lateral_accel) / SONATA_HYBRID_FF_CUTOFF_WIDTH)
  base_reduction = _sonata_hybrid_side_value(desired_lateral_accel,
                                             SONATA_HYBRID_FF_REDUCTION_LEFT,
                                             SONATA_HYBRID_FF_REDUCTION_RIGHT) * onset * cutoff
  phase = _sonata_hybrid_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  low_speed_factor = _sonata_hybrid_low_speed_factor(v_ego)
  turn_in_boost = 1.0 + (_sonata_hybrid_side_value(desired_lateral_accel,
                                                    SONATA_HYBRID_TURN_IN_BOOST_LEFT,
                                                    SONATA_HYBRID_TURN_IN_BOOST_RIGHT) *
                         turn_in_weight * low_speed_factor)
  unwind_taper = 1.0 - (_sonata_hybrid_side_value(desired_lateral_accel,
                                                   SONATA_HYBRID_UNWIND_TAPER_LEFT,
                                                   SONATA_HYBRID_UNWIND_TAPER_RIGHT) *
                        unwind_weight * (0.35 + 0.65 * low_speed_factor))
  return (1.0 - base_reduction) * turn_in_boost * max(unwind_taper, 0.0)


def get_sonata_hybrid_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _sonata_hybrid_sigmoid((v_ego - SONATA_HYBRID_CENTER_TAPER_SPEED) / SONATA_HYBRID_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _sonata_hybrid_sigmoid((SONATA_HYBRID_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / SONATA_HYBRID_CENTER_TAPER_LAT_WIDTH)
  reduction = SONATA_HYBRID_CENTER_TAPER_MAX * speed_weight * center_weight
  low_speed_weight = _sonata_hybrid_sigmoid((SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_SPEED_MAX - v_ego) /
                                            SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_SPEED_WIDTH)
  low_speed_center_weight = _sonata_hybrid_sigmoid((SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_LAT - abs(desired_lateral_accel)) /
                                                   SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_LAT_WIDTH)
  reduction += SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_MAX * low_speed_weight * low_speed_center_weight
  return 1.0 - reduction


def get_sonata_hybrid_center_output_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _sonata_hybrid_sigmoid((v_ego - SONATA_HYBRID_CENTER_OUTPUT_TAPER_SPEED) /
                                        SONATA_HYBRID_CENTER_OUTPUT_TAPER_SPEED_WIDTH)
  center_weight = _sonata_hybrid_sigmoid((SONATA_HYBRID_CENTER_OUTPUT_TAPER_LAT - abs(desired_lateral_accel)) /
                                         SONATA_HYBRID_CENTER_OUTPUT_TAPER_LAT_WIDTH)
  return 1.0 - SONATA_HYBRID_CENTER_OUTPUT_TAPER_MAX * speed_weight * center_weight


def get_sonata_hybrid_friction_threshold(v_ego: float, desired_lateral_accel: float) -> float:
  base_threshold = get_standard_friction_threshold(v_ego)
  speed_bump = np.interp(max(v_ego, 0.0), SONATA_HYBRID_CHATTER_THRESHOLD_SPEED_BP,
                         SONATA_HYBRID_CHATTER_THRESHOLD_BUMP)
  center_weight = _sonata_hybrid_sigmoid(
    (SONATA_HYBRID_CHATTER_THRESHOLD_CENTER - abs(desired_lateral_accel)) /
    SONATA_HYBRID_CHATTER_THRESHOLD_CENTER_WIDTH
  )
  return float(base_threshold + speed_bump * center_weight)


def _sonata_sigmoid(x: float) -> float:
  return _sigmoid(x)


def _sonata_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / SONATA_TRANSITION_SPEED) ** 2)


def _sonata_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / SONATA_PHASE_SCALE)


def _sonata_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def get_sonata_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _sonata_sigmoid((abs_lateral_accel - SONATA_FF_ONSET) / SONATA_FF_ONSET_WIDTH)
  cutoff = _sonata_sigmoid((SONATA_FF_CUTOFF - abs_lateral_accel) / SONATA_FF_CUTOFF_WIDTH)
  base_reduction = _sonata_side_value(desired_lateral_accel, SONATA_FF_REDUCTION_LEFT, SONATA_FF_REDUCTION_RIGHT) * onset * cutoff
  phase = _sonata_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  low_speed_factor = _sonata_low_speed_factor(v_ego)
  turn_in_boost = 1.0 + (_sonata_side_value(desired_lateral_accel, SONATA_TURN_IN_BOOST_LEFT, SONATA_TURN_IN_BOOST_RIGHT) *
                         turn_in_weight * low_speed_factor)
  unwind_taper = 1.0 - (_sonata_side_value(desired_lateral_accel, SONATA_UNWIND_TAPER_LEFT, SONATA_UNWIND_TAPER_RIGHT) *
                        unwind_weight * (0.35 + 0.65 * low_speed_factor))
  return (1.0 - base_reduction) * turn_in_boost * max(unwind_taper, 0.0)


def get_sonata_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _sonata_sigmoid((v_ego - SONATA_CENTER_TAPER_SPEED) / SONATA_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _sonata_sigmoid((SONATA_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / SONATA_CENTER_TAPER_LAT_WIDTH)
  reduction = SONATA_CENTER_TAPER_MAX * speed_weight * center_weight
  low_speed_weight = _sonata_sigmoid((SONATA_LOW_SPEED_CENTER_TAPER_SPEED_MAX - v_ego) /
                                     SONATA_LOW_SPEED_CENTER_TAPER_SPEED_WIDTH)
  low_speed_center_weight = _sonata_sigmoid((SONATA_LOW_SPEED_CENTER_TAPER_LAT - abs(desired_lateral_accel)) /
                                            SONATA_LOW_SPEED_CENTER_TAPER_LAT_WIDTH)
  reduction += SONATA_LOW_SPEED_CENTER_TAPER_MAX * low_speed_weight * low_speed_center_weight
  return 1.0 - reduction


def _elantra_non_scc_sigmoid(x: float) -> float:
  return _sigmoid(x)


def _elantra_non_scc_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / ELANTRA_NON_SCC_TRANSITION_SPEED) ** 2)


def _elantra_non_scc_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / ELANTRA_NON_SCC_PHASE_SCALE)


def _elantra_non_scc_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def get_elantra_non_scc_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _elantra_non_scc_sigmoid((abs_lateral_accel - ELANTRA_NON_SCC_FF_ONSET) / ELANTRA_NON_SCC_FF_ONSET_WIDTH)
  cutoff = _elantra_non_scc_sigmoid((ELANTRA_NON_SCC_FF_CUTOFF - abs_lateral_accel) / ELANTRA_NON_SCC_FF_CUTOFF_WIDTH)
  low_speed_factor = _elantra_non_scc_low_speed_factor(v_ego)
  envelope = onset * cutoff * low_speed_factor
  base_scale = 1.0 - (_elantra_non_scc_side_value(desired_lateral_accel,
                                                   ELANTRA_NON_SCC_FF_ADJUST_LEFT,
                                                   ELANTRA_NON_SCC_FF_ADJUST_RIGHT) * envelope)
  phase = _elantra_non_scc_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  turn_in_boost = 1.0 + (_elantra_non_scc_side_value(desired_lateral_accel,
                                                      ELANTRA_NON_SCC_TURN_IN_BOOST_LEFT,
                                                      ELANTRA_NON_SCC_TURN_IN_BOOST_RIGHT) *
                          turn_in_weight * (0.35 + 0.65 * low_speed_factor))
  unwind_taper = 1.0 - (_elantra_non_scc_side_value(desired_lateral_accel,
                                                     ELANTRA_NON_SCC_UNWIND_TAPER_LEFT,
                                                     ELANTRA_NON_SCC_UNWIND_TAPER_RIGHT) *
                         unwind_weight * (0.35 + 0.65 * low_speed_factor))
  return base_scale * turn_in_boost * max(unwind_taper, 0.0)


def _kia_xceed_sigmoid(x: float) -> float:
  return _sigmoid(x)


def _kia_xceed_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / KIA_XCEED_TRANSITION_SPEED) ** 2)


def _kia_xceed_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / KIA_XCEED_PHASE_SCALE)


def _kia_xceed_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def get_kia_xceed_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _kia_xceed_sigmoid((abs_lateral_accel - KIA_XCEED_FF_ONSET) / KIA_XCEED_FF_ONSET_WIDTH)
  cutoff = _kia_xceed_sigmoid((KIA_XCEED_FF_CUTOFF - abs_lateral_accel) / KIA_XCEED_FF_CUTOFF_WIDTH)
  base_reduction = _kia_xceed_side_value(desired_lateral_accel,
                                         KIA_XCEED_FF_REDUCTION_LEFT,
                                         KIA_XCEED_FF_REDUCTION_RIGHT) * onset * cutoff
  phase = _kia_xceed_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  low_speed_factor = _kia_xceed_low_speed_factor(v_ego)
  turn_in_boost = 1.0 + (_kia_xceed_side_value(desired_lateral_accel,
                                                KIA_XCEED_TURN_IN_BOOST_LEFT,
                                                KIA_XCEED_TURN_IN_BOOST_RIGHT) *
                         turn_in_weight * low_speed_factor)
  unwind_taper = 1.0 - (_kia_xceed_side_value(desired_lateral_accel,
                                               KIA_XCEED_UNWIND_TAPER_LEFT,
                                               KIA_XCEED_UNWIND_TAPER_RIGHT) *
                        unwind_weight * (0.35 + 0.65 * low_speed_factor))
  return (1.0 - base_reduction) * turn_in_boost * max(unwind_taper, 0.0)


def get_kia_xceed_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _kia_xceed_sigmoid((v_ego - KIA_XCEED_CENTER_TAPER_SPEED) / KIA_XCEED_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _kia_xceed_sigmoid((KIA_XCEED_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / KIA_XCEED_CENTER_TAPER_LAT_WIDTH)
  reduction = KIA_XCEED_CENTER_TAPER_MAX * speed_weight * center_weight
  return 1.0 - reduction


def get_kia_niro_phev_2022_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _sigmoid((v_ego - KIA_NIRO_PHEV_2022_CENTER_TAPER_SPEED) / KIA_NIRO_PHEV_2022_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _sigmoid((KIA_NIRO_PHEV_2022_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / KIA_NIRO_PHEV_2022_CENTER_TAPER_LAT_WIDTH)
  reduction = KIA_NIRO_PHEV_2022_CENTER_TAPER_MAX * speed_weight * center_weight
  return 1.0 - reduction


def get_kia_niro_phev_2022_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0, desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = get_gm_base_friction_threshold(v_ego)
  speed_weight = _sigmoid((v_ego - KIA_NIRO_PHEV_2022_FRICTION_SPEED) / KIA_NIRO_PHEV_2022_FRICTION_SPEED_WIDTH)
  center_weight = _sigmoid((KIA_NIRO_PHEV_2022_FRICTION_CENTER_LAT - abs(desired_lateral_accel)) / KIA_NIRO_PHEV_2022_FRICTION_CENTER_LAT_WIDTH)
  calm_jerk_weight = _sigmoid((KIA_NIRO_PHEV_2022_FRICTION_CALM_JERK - abs(desired_lateral_jerk)) / KIA_NIRO_PHEV_2022_FRICTION_CALM_JERK_WIDTH)
  threshold_scale = 1.0 + (KIA_NIRO_PHEV_2022_FRICTION_THRESHOLD_GAIN * speed_weight * center_weight * calm_jerk_weight)
  return base_threshold * min(max(threshold_scale, 1.0), 1.18)


def _kia_stinger_2022_center_weights(desired_lateral_accel: float, v_ego: float) -> tuple[float, float]:
  speed_weight = _sigmoid((v_ego - KIA_STINGER_2022_CENTER_TAPER_SPEED) / KIA_STINGER_2022_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _sigmoid((KIA_STINGER_2022_CENTER_TAPER_LAT - abs(desired_lateral_accel)) /
                           KIA_STINGER_2022_CENTER_TAPER_LAT_WIDTH)
  return speed_weight, center_weight


def get_kia_stinger_2022_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight, center_weight = _kia_stinger_2022_center_weights(desired_lateral_accel, v_ego)
  return 1.0 - (KIA_STINGER_2022_CENTER_TAPER_MAX * speed_weight * center_weight)


def get_kia_stinger_2022_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0,
                                            desired_lateral_jerk: float = 0.0) -> float:
  del desired_lateral_jerk
  speed_weight, center_weight = _kia_stinger_2022_center_weights(desired_lateral_accel, v_ego)
  return get_standard_friction_threshold(v_ego) * (1.0 + KIA_STINGER_2022_FRICTION_THRESHOLD_GAIN * speed_weight * center_weight)


def _kia_carnival_center_weights(desired_lateral_accel: float, v_ego: float) -> tuple[float, float]:
  speed_onset = _sigmoid((v_ego - KIA_CARNIVAL_CENTER_TAPER_SPEED) / KIA_CARNIVAL_CENTER_TAPER_SPEED_WIDTH)
  speed_cutoff = _sigmoid((KIA_CARNIVAL_CENTER_TAPER_SPEED_MAX - v_ego) / KIA_CARNIVAL_CENTER_TAPER_SPEED_MAX_WIDTH)
  speed_weight = speed_onset * speed_cutoff
  center_weight = _sigmoid((KIA_CARNIVAL_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / KIA_CARNIVAL_CENTER_TAPER_LAT_WIDTH)
  return speed_weight, center_weight


def _kia_carnival_highway_center_weights(desired_lateral_accel: float, v_ego: float) -> tuple[float, float]:
  speed_weight = _sigmoid((v_ego - KIA_CARNIVAL_HIGHWAY_CENTER_TAPER_SPEED) /
                          KIA_CARNIVAL_HIGHWAY_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _sigmoid((KIA_CARNIVAL_HIGHWAY_CENTER_TAPER_LAT - abs(desired_lateral_accel)) /
                           KIA_CARNIVAL_HIGHWAY_CENTER_TAPER_LAT_WIDTH)
  return speed_weight, center_weight


def get_kia_carnival_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight, center_weight = _kia_carnival_center_weights(desired_lateral_accel, v_ego)
  highway_speed_weight, highway_center_weight = _kia_carnival_highway_center_weights(desired_lateral_accel, v_ego)
  reduction = KIA_CARNIVAL_CENTER_TAPER_MAX * speed_weight * center_weight
  reduction += KIA_CARNIVAL_HIGHWAY_CENTER_TAPER_MAX * highway_speed_weight * highway_center_weight
  return 1.0 - min(reduction, 0.95)


def get_kia_carnival_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0, desired_lateral_jerk: float = 0.0) -> float:
  del desired_lateral_jerk
  speed_weight, center_weight = _kia_carnival_center_weights(desired_lateral_accel, v_ego)
  highway_speed_weight, highway_center_weight = _kia_carnival_highway_center_weights(desired_lateral_accel, v_ego)
  gain = KIA_CARNIVAL_FRICTION_THRESHOLD_GAIN * speed_weight * center_weight
  gain += KIA_CARNIVAL_HIGHWAY_FRICTION_THRESHOLD_GAIN * highway_speed_weight * highway_center_weight
  return get_hkg_canfd_base_friction_threshold(v_ego) * (1.0 + gain)


def get_kia_carnival_friction_center_fade_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight, center_weight = _kia_carnival_center_weights(desired_lateral_accel, v_ego)
  highway_speed_weight, highway_center_weight = _kia_carnival_highway_center_weights(desired_lateral_accel, v_ego)
  reduction = KIA_CARNIVAL_FRICTION_CENTER_FADE_MAX * speed_weight * center_weight
  reduction += KIA_CARNIVAL_HIGHWAY_FRICTION_CENTER_FADE_MAX * highway_speed_weight * highway_center_weight
  return 1.0 - min(reduction, 0.95)


def get_kia_carnival_highway_transition_output_scale(desired_lateral_accel: float, desired_lateral_jerk: float,
                                                      v_ego: float) -> float:
  speed_weight = _sigmoid((v_ego - KIA_CARNIVAL_HIGHWAY_CENTER_TAPER_SPEED) /
                          KIA_CARNIVAL_HIGHWAY_CENTER_TAPER_SPEED_WIDTH)
  jerk_weight = _sigmoid((abs(desired_lateral_jerk) - KIA_CARNIVAL_HIGHWAY_TRANSITION_JERK) /
                         KIA_CARNIVAL_HIGHWAY_TRANSITION_JERK_WIDTH)
  lat_weight = _sigmoid((KIA_CARNIVAL_HIGHWAY_TRANSITION_LAT_CUTOFF - abs(desired_lateral_accel)) /
                        KIA_CARNIVAL_HIGHWAY_TRANSITION_LAT_WIDTH)
  return 1.0 - (KIA_CARNIVAL_HIGHWAY_TRANSITION_TAPER_MAX * speed_weight * jerk_weight * lat_weight)


def get_kia_carnival_friction_jerk_deadzone(v_ego: float, desired_lateral_accel: float,
                                            desired_lateral_jerk: float) -> float:
  """Reduce abrupt friction reversals during mid-speed curve exits only."""
  speed_weight = _sigmoid((v_ego - KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_SPEED) /
                          KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_SPEED_WIDTH)
  speed_cutoff = _sigmoid((KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_SPEED_CUTOFF - v_ego) /
                          KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_SPEED_CUTOFF_WIDTH)
  center_weight = _sigmoid((KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_LAT - abs(desired_lateral_accel)) /
                           KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_LAT_WIDTH)
  jerk_weight = _sigmoid((abs(desired_lateral_jerk) - KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_JERK) /
                         KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_JERK_WIDTH)
  return KIA_CARNIVAL_UNWIND_FRICTION_JERK_DEADZONE_MAX * speed_weight * speed_cutoff * center_weight * jerk_weight


def get_kia_carnival_unwind_ff_scale(setpoint: float, measured_lateral_accel: float,
                                     desired_lateral_jerk: float, v_ego: float) -> float:
  """Remove stale turn feedforward when the measured response carries through an unwind."""
  if setpoint * desired_lateral_jerk >= 0.0:
    return 1.0

  overshoot = max(abs(measured_lateral_accel) - abs(setpoint), 0.0)
  if overshoot <= 0.0:
    return 1.0

  speed_weight = (_sigmoid((v_ego - KIA_CARNIVAL_UNWIND_FF_SPEED) /
                           KIA_CARNIVAL_UNWIND_FF_SPEED_WIDTH) *
                  _sigmoid((KIA_CARNIVAL_UNWIND_FF_SPEED_CUTOFF - v_ego) /
                           KIA_CARNIVAL_UNWIND_FF_SPEED_CUTOFF_WIDTH))
  overshoot_weight = _sigmoid((overshoot - KIA_CARNIVAL_UNWIND_FF_OVERSHOOT) /
                              KIA_CARNIVAL_UNWIND_FF_OVERSHOOT_WIDTH)
  jerk_weight = _sigmoid((abs(desired_lateral_jerk) - KIA_CARNIVAL_UNWIND_FF_JERK) /
                         KIA_CARNIVAL_UNWIND_FF_JERK_WIDTH)
  return 1.0 - (KIA_CARNIVAL_UNWIND_FF_REDUCTION_MAX * speed_weight * overshoot_weight * jerk_weight)


def get_kia_carnival_unwind_output_scale(setpoint: float, measured_lateral_accel: float,
                                         desired_lateral_jerk: float, v_ego: float) -> float:
  if (setpoint * desired_lateral_jerk >= 0.0 or
      setpoint * measured_lateral_accel <= 0.0):
    return 1.0

  overshoot = max(abs(measured_lateral_accel) - abs(setpoint), 0.0)
  if overshoot <= 0.0:
    return 1.0

  speed_weight = (_sigmoid((v_ego - KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_SPEED) /
                           KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_SPEED_WIDTH) *
                  _sigmoid((KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_SPEED_CUTOFF - v_ego) /
                           KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_SPEED_CUTOFF_WIDTH))
  overshoot_weight = _sigmoid((overshoot - KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_OVERSHOOT) /
                              KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_OVERSHOOT_WIDTH)
  jerk_weight = _sigmoid((abs(desired_lateral_jerk) - KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_JERK) /
                         KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_JERK_WIDTH)
  return 1.0 - (KIA_CARNIVAL_UNWIND_OUTPUT_DAMPING_MAX * speed_weight * overshoot_weight * jerk_weight)


def _tucson_4th_gen_center_weights(desired_lateral_accel: float, v_ego: float) -> tuple[float, float]:
  speed_weight = _sigmoid((TUCSON_4TH_GEN_CENTER_TAPER_SPEED_MAX - v_ego) / TUCSON_4TH_GEN_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _sigmoid((TUCSON_4TH_GEN_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / TUCSON_4TH_GEN_CENTER_TAPER_LAT_WIDTH)
  return speed_weight, center_weight


def get_tucson_4th_gen_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight, center_weight = _tucson_4th_gen_center_weights(desired_lateral_accel, v_ego)
  return 1.0 - (TUCSON_4TH_GEN_CENTER_TAPER_MAX * speed_weight * center_weight)


def get_tucson_4th_gen_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0,
                                          desired_lateral_jerk: float = 0.0) -> float:
  del desired_lateral_jerk
  speed_weight, center_weight = _tucson_4th_gen_center_weights(desired_lateral_accel, v_ego)
  return get_hkg_canfd_base_friction_threshold(v_ego) * (1.0 + TUCSON_4TH_GEN_FRICTION_THRESHOLD_GAIN * speed_weight * center_weight)


def _kia_forte_sigmoid(x: float) -> float:
  return _sigmoid(x)


def _kia_forte_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / KIA_FORTE_TRANSITION_SPEED) ** 2)


def _kia_forte_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / KIA_FORTE_PHASE_SCALE)


def _kia_forte_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def get_kia_forte_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _kia_forte_sigmoid((abs_lateral_accel - KIA_FORTE_FF_ONSET) / KIA_FORTE_FF_ONSET_WIDTH)
  cutoff = _kia_forte_sigmoid((KIA_FORTE_FF_CUTOFF - abs_lateral_accel) / KIA_FORTE_FF_CUTOFF_WIDTH)
  base_reduction = _kia_forte_side_value(desired_lateral_accel, KIA_FORTE_FF_REDUCTION_LEFT, KIA_FORTE_FF_REDUCTION_RIGHT) * onset * cutoff
  phase = _kia_forte_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  low_speed_factor = _kia_forte_low_speed_factor(v_ego)
  turn_in_boost = 1.0 + (_kia_forte_side_value(desired_lateral_accel, KIA_FORTE_TURN_IN_BOOST_LEFT, KIA_FORTE_TURN_IN_BOOST_RIGHT) *
                         turn_in_weight * (0.35 + 0.65 * low_speed_factor))
  unwind_taper = 1.0 - (_kia_forte_side_value(desired_lateral_accel, KIA_FORTE_UNWIND_TAPER_LEFT, KIA_FORTE_UNWIND_TAPER_RIGHT) *
                        unwind_weight * (0.35 + 0.65 * low_speed_factor))
  crawl_turn_in_scale = 0.0
  if desired_lateral_accel * desired_lateral_jerk > 0.0:
    crawl_speed_weight = _kia_forte_sigmoid((KIA_FORTE_CRAWL_TURN_IN_FF_SPEED - max(v_ego, 0.0)) /
                                            KIA_FORTE_CRAWL_TURN_IN_FF_SPEED_WIDTH)
    crawl_lat_weight = _kia_forte_sigmoid((abs_lateral_accel - KIA_FORTE_CRAWL_TURN_IN_FF_LAT) /
                                          KIA_FORTE_CRAWL_TURN_IN_FF_LAT_WIDTH)
    crawl_turn_in_scale = _kia_forte_side_value(desired_lateral_accel, KIA_FORTE_CRAWL_TURN_IN_FF_BOOST_LEFT,
                                                KIA_FORTE_CRAWL_TURN_IN_FF_BOOST_RIGHT) * crawl_speed_weight * crawl_lat_weight
  return ((1.0 - base_reduction) * turn_in_boost * max(unwind_taper, 0.0)) + crawl_turn_in_scale


def get_kia_forte_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _kia_forte_sigmoid((v_ego - KIA_FORTE_CENTER_TAPER_SPEED) / KIA_FORTE_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _kia_forte_sigmoid((KIA_FORTE_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / KIA_FORTE_CENTER_TAPER_LAT_WIDTH)
  reduction = KIA_FORTE_CENTER_TAPER_MAX * speed_weight * center_weight
  return 1.0 - reduction


def get_kia_forte_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0, desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = get_gm_base_friction_threshold(v_ego)
  speed_weight = _kia_forte_sigmoid((v_ego - KIA_FORTE_FRICTION_SPEED) / KIA_FORTE_FRICTION_SPEED_WIDTH)
  center_weight = _kia_forte_sigmoid((KIA_FORTE_FRICTION_CENTER_LAT - abs(desired_lateral_accel)) / KIA_FORTE_FRICTION_CENTER_LAT_WIDTH)
  calm_jerk_weight = _kia_forte_sigmoid((KIA_FORTE_FRICTION_CALM_JERK - abs(desired_lateral_jerk)) / KIA_FORTE_FRICTION_CALM_JERK_WIDTH)
  threshold_scale = 1.0 + (KIA_FORTE_FRICTION_THRESHOLD_GAIN * speed_weight * center_weight * calm_jerk_weight)
  return base_threshold * min(max(threshold_scale, 1.0), 1.18)


def _palisade_sigmoid(x: float) -> float:
  return _sigmoid(x)


def _palisade_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / PALISADE_TRANSITION_SPEED) ** 2)


def _palisade_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / PALISADE_PHASE_SCALE)


def _palisade_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def _palisade_transition_envelope(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  lat_factor = 1.0 - math.exp(-abs(desired_lateral_accel) / PALISADE_FRICTION_LAT_RISE)
  jerk_factor = 1.0 - math.exp(-abs(desired_lateral_jerk) / PALISADE_FRICTION_JERK_RISE)
  return _palisade_low_speed_factor(v_ego) * lat_factor * jerk_factor


def get_palisade_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  gain = _palisade_side_value(desired_lateral_accel, PALISADE_FF_GAIN_LEFT, PALISADE_FF_GAIN_RIGHT)
  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _palisade_sigmoid((abs_lateral_accel - PALISADE_FF_ONSET) / PALISADE_FF_ONSET_WIDTH)
  cutoff = _palisade_sigmoid((PALISADE_FF_CUTOFF - abs_lateral_accel) / PALISADE_FF_CUTOFF_WIDTH)
  extra_scale = gain * onset * cutoff
  phase = _palisade_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  low_speed_factor = _palisade_low_speed_factor(v_ego)
  turn_in_boost = 1.0 + (_palisade_side_value(desired_lateral_accel, PALISADE_TURN_IN_BOOST_LEFT, PALISADE_TURN_IN_BOOST_RIGHT) *
                          turn_in_weight * (0.35 + 0.65 * low_speed_factor))
  unwind_taper = 1.0 - (_palisade_side_value(desired_lateral_accel, PALISADE_UNWIND_TAPER_LEFT, PALISADE_UNWIND_TAPER_RIGHT) *
                         unwind_weight * (0.35 + 0.65 * low_speed_factor))
  return 1.0 + (extra_scale * turn_in_boost * max(unwind_taper, 0.0))


def get_palisade_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0, desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = get_gm_base_friction_threshold(v_ego)
  transition_envelope = _palisade_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _palisade_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  threshold_scale = 1.0 - (_palisade_side_value(desired_lateral_accel, PALISADE_TURN_IN_THRESHOLD_REDUCTION_LEFT, PALISADE_TURN_IN_THRESHOLD_REDUCTION_RIGHT) *
                           transition_envelope * turn_in_weight)
  threshold_scale += (_palisade_side_value(desired_lateral_accel, PALISADE_UNWIND_THRESHOLD_INCREASE_LEFT, PALISADE_UNWIND_THRESHOLD_INCREASE_RIGHT) *
                      transition_envelope * unwind_weight)
  return base_threshold * min(max(threshold_scale, 0.84), 1.14)


def get_palisade_friction_scale(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  transition_envelope = _palisade_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _palisade_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  friction_scale = PALISADE_FRICTION_MULT
  friction_scale += (_palisade_side_value(desired_lateral_accel, PALISADE_TURN_IN_FRICTION_BOOST_LEFT, PALISADE_TURN_IN_FRICTION_BOOST_RIGHT) *
                     transition_envelope * turn_in_weight)
  friction_scale -= (_palisade_side_value(desired_lateral_accel, PALISADE_UNWIND_FRICTION_REDUCTION_LEFT, PALISADE_UNWIND_FRICTION_REDUCTION_RIGHT) *
                     transition_envelope * unwind_weight)
  return min(max(friction_scale, 0.92), 1.12)


def get_palisade_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _palisade_sigmoid((v_ego - PALISADE_CENTER_TAPER_SPEED) / PALISADE_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _palisade_sigmoid((PALISADE_CENTER_TAPER_LAT - abs(desired_lateral_accel)) /
                                    PALISADE_CENTER_TAPER_LAT_WIDTH)
  return 1.0 - (PALISADE_CENTER_TAPER_MAX * speed_weight * center_weight)


def get_palisade_center_output_scale(desired_lateral_accel: float, v_ego: float) -> float:
  """Reduce high-speed center corrections without reducing normal turn authority."""
  speed_weight = _palisade_sigmoid((v_ego - PALISADE_CENTER_OUTPUT_TAPER_SPEED) /
                                    PALISADE_CENTER_OUTPUT_TAPER_SPEED_WIDTH)
  center_weight = _palisade_sigmoid((PALISADE_CENTER_OUTPUT_TAPER_LAT - abs(desired_lateral_accel)) /
                                    PALISADE_CENTER_OUTPUT_TAPER_LAT_WIDTH)
  return 1.0 - (PALISADE_CENTER_OUTPUT_TAPER_MAX * speed_weight * center_weight)


def genesis_g90_lateral_testing_ground_active() -> bool:
  return testing_ground.use(GENESIS_G90_LATERAL_TESTING_GROUND_ID)


def _genesis_g90_sigmoid(x: float) -> float:
  return _sigmoid(x)


def _genesis_g90_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / GENESIS_G90_TRANSITION_SPEED) ** 2)


def _genesis_g90_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / GENESIS_G90_PHASE_SCALE)


def _genesis_g90_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def _genesis_g90_transition_envelope(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  lat_factor = 1.0 - math.exp(-abs(desired_lateral_accel) / GENESIS_G90_FRICTION_LAT_RISE)
  jerk_factor = 1.0 - math.exp(-abs(desired_lateral_jerk) / GENESIS_G90_FRICTION_JERK_RISE)
  return _genesis_g90_low_speed_factor(v_ego) * lat_factor * jerk_factor


def get_genesis_g90_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  gain = _genesis_g90_side_value(desired_lateral_accel, GENESIS_G90_FF_GAIN_LEFT, GENESIS_G90_FF_GAIN_RIGHT)
  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _genesis_g90_sigmoid((abs_lateral_accel - GENESIS_G90_FF_ONSET) / GENESIS_G90_FF_ONSET_WIDTH)
  cutoff = _genesis_g90_sigmoid((GENESIS_G90_FF_CUTOFF - abs_lateral_accel) / GENESIS_G90_FF_CUTOFF_WIDTH)
  extra_scale = gain * onset * cutoff
  phase = _genesis_g90_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  low_speed_factor = _genesis_g90_low_speed_factor(v_ego)
  turn_in_boost = 1.0 + (_genesis_g90_side_value(desired_lateral_accel, GENESIS_G90_TURN_IN_BOOST_LEFT, GENESIS_G90_TURN_IN_BOOST_RIGHT) *
                          turn_in_weight * (0.35 + 0.65 * low_speed_factor))
  unwind_taper = 1.0 - (_genesis_g90_side_value(desired_lateral_accel, GENESIS_G90_UNWIND_TAPER_LEFT, GENESIS_G90_UNWIND_TAPER_RIGHT) *
                         unwind_weight * (0.30 + 0.70 * low_speed_factor))
  return 1.0 + (extra_scale * turn_in_boost * max(unwind_taper, 0.0))


def get_genesis_g90_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0, desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = get_gm_base_friction_threshold(v_ego)
  transition_envelope = _genesis_g90_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _genesis_g90_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  threshold_scale = 1.0 - (_genesis_g90_side_value(desired_lateral_accel, GENESIS_G90_TURN_IN_THRESHOLD_REDUCTION_LEFT, GENESIS_G90_TURN_IN_THRESHOLD_REDUCTION_RIGHT) *
                           transition_envelope * turn_in_weight)
  threshold_scale += (_genesis_g90_side_value(desired_lateral_accel, GENESIS_G90_UNWIND_THRESHOLD_INCREASE_LEFT, GENESIS_G90_UNWIND_THRESHOLD_INCREASE_RIGHT) *
                      transition_envelope * unwind_weight)
  return base_threshold * min(max(threshold_scale, 0.86), 1.12)


def get_genesis_g90_friction_scale(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  transition_envelope = _genesis_g90_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _genesis_g90_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  friction_scale = GENESIS_G90_FRICTION_MULT
  friction_scale += (_genesis_g90_side_value(desired_lateral_accel, GENESIS_G90_TURN_IN_FRICTION_BOOST_LEFT, GENESIS_G90_TURN_IN_FRICTION_BOOST_RIGHT) *
                     transition_envelope * turn_in_weight)
  friction_scale -= (_genesis_g90_side_value(desired_lateral_accel, GENESIS_G90_UNWIND_FRICTION_REDUCTION_LEFT, GENESIS_G90_UNWIND_FRICTION_REDUCTION_RIGHT) *
                     transition_envelope * unwind_weight)
  return min(max(friction_scale, 0.92), 1.12)


def get_genesis_gv70_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0,
                                        desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = get_hkg_canfd_base_friction_threshold(v_ego)
  speed_onset = _sigmoid((v_ego - GENESIS_GV70_FRICTION_SPEED_ONSET) / GENESIS_GV70_FRICTION_SPEED_ONSET_WIDTH)
  speed_cutoff = _sigmoid((GENESIS_GV70_FRICTION_SPEED_CUTOFF - v_ego) / GENESIS_GV70_FRICTION_SPEED_CUTOFF_WIDTH)
  center_weight = _sigmoid((GENESIS_GV70_FRICTION_CENTER_LAT - abs(desired_lateral_accel)) /
                           GENESIS_GV70_FRICTION_CENTER_LAT_WIDTH)
  calm_jerk_weight = _sigmoid((GENESIS_GV70_FRICTION_CALM_JERK - abs(desired_lateral_jerk)) /
                              GENESIS_GV70_FRICTION_CALM_JERK_WIDTH)
  gain = (GENESIS_GV70_FRICTION_THRESHOLD_GAIN * speed_onset * speed_cutoff *
          center_weight * calm_jerk_weight)
  return base_threshold * (1.0 + gain)


def get_genesis_gv70_friction_jerk_deadzone(v_ego: float, desired_lateral_accel: float) -> float:
  """Suppress small jerk-driven friction flips around the GV70 lane center."""
  speed_weight = _sigmoid((v_ego - GENESIS_GV70_FRICTION_JERK_DEADZONE_SPEED) /
                          GENESIS_GV70_FRICTION_JERK_DEADZONE_SPEED_WIDTH)
  center_weight = _sigmoid((GENESIS_GV70_FRICTION_JERK_DEADZONE_LAT - abs(desired_lateral_accel)) /
                           GENESIS_GV70_FRICTION_JERK_DEADZONE_LAT_WIDTH)
  return GENESIS_GV70_FRICTION_JERK_DEADZONE_MAX * speed_weight * center_weight


def get_genesis_gv70_center_output_scale(desired_lateral_accel: float, v_ego: float) -> float:
  """Dampen high-speed center corrections without reducing turn authority."""
  speed_weight = _sigmoid((v_ego - GENESIS_GV70_CENTER_OUTPUT_TAPER_SPEED) /
                          GENESIS_GV70_CENTER_OUTPUT_TAPER_SPEED_WIDTH)
  center_weight = _sigmoid((GENESIS_GV70_CENTER_OUTPUT_TAPER_LAT - abs(desired_lateral_accel)) /
                           GENESIS_GV70_CENTER_OUTPUT_TAPER_LAT_WIDTH)
  return 1.0 - (GENESIS_GV70_CENTER_OUTPUT_TAPER_MAX * speed_weight * center_weight)


def get_genesis_gv70_unwind_ff_scale(setpoint: float, measured_lateral_accel: float,
                                     desired_lateral_jerk: float, v_ego: float) -> float:
  """Remove old-turn feedforward when the GV70 has already over-rotated."""
  if setpoint * desired_lateral_jerk >= 0.0 or setpoint * measured_lateral_accel <= 0.0:
    return 1.0

  overshoot = max(abs(measured_lateral_accel) - abs(setpoint), 0.0)
  overshoot_weight = _sigmoid((overshoot - GENESIS_GV70_UNWIND_FF_OVERSHOOT) /
                              GENESIS_GV70_UNWIND_FF_OVERSHOOT_WIDTH)
  jerk_weight = _sigmoid((abs(desired_lateral_jerk) - GENESIS_GV70_UNWIND_FF_JERK) /
                         GENESIS_GV70_UNWIND_FF_JERK_WIDTH)
  speed_weight = _sigmoid((v_ego - GENESIS_GV70_UNWIND_FF_SPEED) /
                          GENESIS_GV70_UNWIND_FF_SPEED_WIDTH)
  return 1.0 - GENESIS_GV70_UNWIND_FF_REDUCTION_MAX * overshoot_weight * jerk_weight * speed_weight


def get_genesis_gv70_high_speed_error_scale(setpoint: float, measured_lateral_accel: float,
                                             desired_lateral_jerk: float, v_ego: float) -> float:
  tracking_error = abs(measured_lateral_accel - setpoint)
  if tracking_error <= 0.0:
    return 1.0
  speed_weight = _sigmoid((v_ego - GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_SPEED) /
                          GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_SPEED_WIDTH)
  error_weight = _sigmoid((tracking_error - GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_ERROR) /
                          GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_ERROR_WIDTH)
  jerk_weight = _sigmoid((abs(desired_lateral_jerk) - GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_JERK) /
                         GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_JERK_WIDTH)
  phase_weight = 1.0 if setpoint * desired_lateral_jerk < 0.0 else 0.45
  reduction = (GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_MAX * speed_weight * error_weight *
               (0.35 + (0.65 * jerk_weight)) * phase_weight)
  return 1.0 - reduction


def get_genesis_gv70_reversal_output_scale(setpoint: float, measured_lateral_accel: float,
                                           desired_lateral_jerk: float, v_ego: float) -> float:
  commanded_unwind = setpoint * desired_lateral_jerk < 0.0
  measured_reversal = setpoint * measured_lateral_accel < 0.0
  if not commanded_unwind and not measured_reversal:
    return 1.0

  tracking_error = abs(measured_lateral_accel - setpoint)
  speed_weight = _sigmoid((v_ego - GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_SPEED) /
                          GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_SPEED_WIDTH)
  error_weight = _sigmoid((tracking_error - GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_ERROR) /
                          GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_ERROR_WIDTH)
  jerk_weight = _sigmoid((abs(desired_lateral_jerk) - GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_JERK) /
                         GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_JERK_WIDTH)
  reduction = (GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_MAX * speed_weight * error_weight * jerk_weight)
  return 1.0 - reduction


def get_genesis_gv70_low_speed_center_overshoot_scale(setpoint: float, measured_lateral_accel: float,
                                                      v_ego: float) -> float:
  if abs(setpoint) > 0.08 and setpoint * measured_lateral_accel < 0.0:
    return 1.0
  overshoot = max(abs(measured_lateral_accel) - abs(setpoint), 0.0)
  if overshoot < GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_MIN:
    return 1.0
  overshoot_weight = _sigmoid((overshoot - GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_LAT) /
                              GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_LAT_WIDTH)
  center_weight = _sigmoid((GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_CENTER_LAT - abs(setpoint)) /
                           GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_CENTER_LAT_WIDTH)
  speed_weight = _sigmoid((v_ego - GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_SPEED) /
                          GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_SPEED_WIDTH)
  speed_cutoff = _sigmoid((GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_SPEED_CUTOFF - v_ego) /
                          GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_SPEED_CUTOFF_WIDTH)
  return 1.0 - (GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_MAX * overshoot_weight * center_weight *
                speed_weight * speed_cutoff)


def get_genesis_gv70_stabilized_output(output_torque: float, prev_output_torque: float,
                                        desired_lateral_accel: float, desired_lateral_jerk: float,
                                        v_ego: float, dt: float) -> float:
  speed_weight = _sigmoid((max(v_ego, 0.0) - GENESIS_GV70_OUTPUT_SMOOTHING_SPEED) /
                          GENESIS_GV70_OUTPUT_SMOOTHING_SPEED_WIDTH)
  center_weight = _sigmoid((GENESIS_GV70_OUTPUT_SMOOTHING_CENTER_LAT - abs(desired_lateral_accel)) /
                           GENESIS_GV70_OUTPUT_SMOOTHING_CENTER_LAT_WIDTH)
  curve_weight = 1.0 - center_weight
  response_time = (GENESIS_GV70_OUTPUT_SMOOTHING_CURVE_RC * curve_weight +
                   GENESIS_GV70_OUTPUT_SMOOTHING_CENTER_RC * center_weight)

  unwind_phase = -desired_lateral_accel * desired_lateral_jerk
  unwind_weight = _sigmoid((unwind_phase - GENESIS_GV70_OUTPUT_SMOOTHING_UNWIND_PHASE) /
                           GENESIS_GV70_OUTPUT_SMOOTHING_UNWIND_PHASE_WIDTH)
  response_time += GENESIS_GV70_OUTPUT_SMOOTHING_UNWIND_RC * curve_weight * unwind_weight

  changing_direction = (abs(desired_lateral_accel) >= GENESIS_GV70_OUTPUT_SMOOTHING_DIRECTION_CHANGE_LAT and
                        prev_output_torque * desired_lateral_accel <= 0.0)
  if changing_direction:
    response_time = min(response_time, GENESIS_GV70_OUTPUT_SMOOTHING_DIRECTION_CHANGE_RC)

  output_alpha = dt / (max(response_time, 0.0) + dt)
  smoothed_output = prev_output_torque + output_alpha * (output_torque - prev_output_torque)
  return float(output_torque + speed_weight * (smoothed_output - output_torque))


def get_genesis_g70_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0,
                                       desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = get_standard_friction_threshold(v_ego)
  speed_onset = _sigmoid((v_ego - GENESIS_G70_FRICTION_SPEED_ONSET) / GENESIS_G70_FRICTION_SPEED_ONSET_WIDTH)
  speed_cutoff = _sigmoid((GENESIS_G70_FRICTION_SPEED_CUTOFF - v_ego) / GENESIS_G70_FRICTION_SPEED_CUTOFF_WIDTH)
  center_weight = _sigmoid((GENESIS_G70_FRICTION_CENTER_LAT - abs(desired_lateral_accel)) /
                           GENESIS_G70_FRICTION_CENTER_LAT_WIDTH)
  calm_jerk_weight = _sigmoid((GENESIS_G70_FRICTION_CALM_JERK - abs(desired_lateral_jerk)) /
                              GENESIS_G70_FRICTION_CALM_JERK_WIDTH)
  gain = (GENESIS_G70_FRICTION_THRESHOLD_GAIN * speed_onset * speed_cutoff *
          center_weight * calm_jerk_weight)
  return base_threshold * (1.0 + gain)


def get_genesis_g70_friction_jerk_deadzone(v_ego: float, desired_lateral_accel: float,
                                           desired_lateral_jerk: float = 0.0,
                                           measured_lateral_accel: float = 0.0) -> float:
  speed_weight = _sigmoid((v_ego - GENESIS_G70_FRICTION_JERK_DEADZONE_SPEED) /
                          GENESIS_G70_FRICTION_JERK_DEADZONE_SPEED_WIDTH)
  center_weight = _sigmoid((GENESIS_G70_FRICTION_JERK_DEADZONE_LAT - abs(desired_lateral_accel)) /
                           GENESIS_G70_FRICTION_JERK_DEADZONE_LAT_WIDTH)
  deadzone = GENESIS_G70_FRICTION_JERK_DEADZONE_MAX * speed_weight * center_weight

  overshoot = max(abs(measured_lateral_accel) - abs(desired_lateral_accel), 0.0)
  if (desired_lateral_accel * desired_lateral_jerk < 0.0 and
      desired_lateral_accel * measured_lateral_accel > 0.0 and overshoot > 0.0):
    curve_speed_weight = _sigmoid(
      (max(v_ego, 0.0) - GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_SPEED) /
      GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_SPEED_WIDTH
    )
    curve_onset_weight = _sigmoid(
      (abs(desired_lateral_accel) - GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_LAT) /
      GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_LAT_WIDTH
    )
    curve_cutoff_weight = _sigmoid(
      (GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_LAT_CUTOFF - abs(desired_lateral_accel)) /
      GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_LAT_CUTOFF_WIDTH
    )
    jerk_weight = _sigmoid(
      (abs(desired_lateral_jerk) - GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_JERK) /
      GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_JERK_WIDTH
    )
    overshoot_weight = _sigmoid((overshoot - 0.08) / 0.10)
    deadzone += (GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_MAX * curve_speed_weight *
                 curve_onset_weight * curve_cutoff_weight * jerk_weight * overshoot_weight)
  return deadzone


def get_genesis_g70_center_output_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _sigmoid((v_ego - GENESIS_G70_CENTER_OUTPUT_TAPER_SPEED) /
                          GENESIS_G70_CENTER_OUTPUT_TAPER_SPEED_WIDTH)
  center_weight = _sigmoid((GENESIS_G70_CENTER_OUTPUT_TAPER_LAT - abs(desired_lateral_accel)) /
                           GENESIS_G70_CENTER_OUTPUT_TAPER_LAT_WIDTH)
  reduction = GENESIS_G70_CENTER_OUTPUT_TAPER_MAX * speed_weight * center_weight
  low_speed_weight = _sigmoid((GENESIS_G70_LOW_SPEED_CENTER_TAPER_SPEED_MAX - v_ego) /
                               GENESIS_G70_LOW_SPEED_CENTER_TAPER_SPEED_WIDTH)
  low_speed_center_weight = _sigmoid((GENESIS_G70_LOW_SPEED_CENTER_TAPER_LAT - abs(desired_lateral_accel)) /
                                     GENESIS_G70_LOW_SPEED_CENTER_TAPER_LAT_WIDTH)
  reduction += GENESIS_G70_LOW_SPEED_CENTER_TAPER_MAX * low_speed_weight * low_speed_center_weight
  return 1.0 - reduction


def get_genesis_g70_high_speed_transition_scale(desired_lateral_accel: float,
                                                desired_lateral_jerk: float, v_ego: float) -> float:
  speed_weight = _sigmoid((v_ego - GENESIS_G70_HIGH_SPEED_TRANSITION_DAMPING_SPEED) /
                          GENESIS_G70_HIGH_SPEED_TRANSITION_DAMPING_SPEED_WIDTH)
  center_weight = _sigmoid((GENESIS_G70_HIGH_SPEED_TRANSITION_DAMPING_LAT - abs(desired_lateral_accel)) /
                           GENESIS_G70_HIGH_SPEED_TRANSITION_DAMPING_LAT_WIDTH)
  jerk_weight = _sigmoid((abs(desired_lateral_jerk) - GENESIS_G70_HIGH_SPEED_TRANSITION_DAMPING_JERK) /
                          GENESIS_G70_HIGH_SPEED_TRANSITION_DAMPING_JERK_WIDTH)
  reduction = (GENESIS_G70_HIGH_SPEED_TRANSITION_DAMPING_MAX * speed_weight * center_weight * jerk_weight)
  return 1.0 - reduction


def get_genesis_g70_low_speed_angle_damping(desired_angle_deg: float, actual_angle_deg: float,
                                             current_output_torque: float, v_ego: float) -> float:
  angle_error = desired_angle_deg - actual_angle_deg
  speed_weight = _sigmoid((GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_SPEED - max(v_ego, 0.0)) /
                          GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_SPEED_WIDTH)
  error_weight = _sigmoid((abs(angle_error) - GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_ERROR) /
                          GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_ERROR_WIDTH)
  actual_angle_weight = _sigmoid((abs(actual_angle_deg) - GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_ACTUAL) /
                                 GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_ACTUAL_WIDTH)
  damping_torque = math.copysign(
    GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_MAX * speed_weight * error_weight * actual_angle_weight,
    -angle_error,
  )
  if abs(damping_torque) < 1e-4:
    return current_output_torque
  if current_output_torque * damping_torque >= 0.0:
    damping_torque *= GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_BLEND
  return float(np.clip(current_output_torque + damping_torque, -1.0, 1.0))


def get_genesis_g70_low_speed_output_limit(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _sigmoid((GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_SPEED - max(v_ego, 0.0)) /
                          GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_SPEED_WIDTH)
  center_weight = _sigmoid((GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_LAT - abs(desired_lateral_accel)) /
                           GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_LAT_WIDTH)
  return max(0.05, 1.0 - GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_REDUCTION * speed_weight * center_weight)


def get_genesis_g70_angle_output_scale(steering_angle_deg: float, output_torque: float) -> float:
  """Ease G70 torque as it approaches the EPS high-angle protection threshold."""
  if steering_angle_deg == 0.0 or output_torque * steering_angle_deg <= 0.0:
    return 1.0

  angle_weight = _sigmoid((abs(steering_angle_deg) - GENESIS_G70_ANGLE_OUTPUT_TAPER_START) /
                          GENESIS_G70_ANGLE_OUTPUT_TAPER_WIDTH)
  return 1.0 - ((1.0 - GENESIS_G70_ANGLE_OUTPUT_TAPER_MIN) * angle_weight)


def get_genesis_g70_curve_unwind_output_scale(desired_lateral_accel: float, desired_lateral_jerk: float,
                                               v_ego: float) -> float:
  if desired_lateral_accel * desired_lateral_jerk >= 0.0:
    return 1.0
  speed_weight = _sigmoid((max(v_ego, 0.0) - GENESIS_G70_CURVE_UNWIND_SPEED) /
                          GENESIS_G70_CURVE_UNWIND_SPEED_WIDTH)
  lateral_weight = _sigmoid((abs(desired_lateral_accel) - GENESIS_G70_CURVE_UNWIND_LAT) /
                            GENESIS_G70_CURVE_UNWIND_LAT_WIDTH)
  jerk_weight = _sigmoid((abs(desired_lateral_jerk) - GENESIS_G70_CURVE_UNWIND_JERK) /
                          GENESIS_G70_CURVE_UNWIND_JERK_WIDTH)
  reduction = (GENESIS_G70_CURVE_UNWIND_OUTPUT_REDUCTION_MAX * speed_weight * lateral_weight * jerk_weight)
  return 1.0 - reduction


def get_genesis_g70_unwind_ff_scale(setpoint: float, measured_lateral_accel: float,
                                    desired_lateral_jerk: float, v_ego: float) -> float:
  if setpoint * desired_lateral_jerk >= 0.0 or setpoint * measured_lateral_accel <= 0.0:
    return 1.0

  overshoot = max(abs(measured_lateral_accel) - abs(setpoint), 0.0)
  if overshoot <= 0.0:
    return 1.0
  overshoot_weight = _sigmoid((overshoot - GENESIS_G70_UNWIND_FF_OVERSHOOT) /
                              GENESIS_G70_UNWIND_FF_OVERSHOOT_WIDTH)
  jerk_weight = _sigmoid((abs(desired_lateral_jerk) - GENESIS_G70_UNWIND_FF_JERK) /
                         GENESIS_G70_UNWIND_FF_JERK_WIDTH)
  speed_weight = _sigmoid((v_ego - GENESIS_G70_UNWIND_FF_SPEED) /
                          GENESIS_G70_UNWIND_FF_SPEED_WIDTH)
  return 1.0 - GENESIS_G70_UNWIND_FF_REDUCTION_MAX * overshoot_weight * jerk_weight * speed_weight


def get_genesis_g70_high_speed_error_scale(setpoint: float, measured_lateral_accel: float,
                                            desired_lateral_jerk: float, v_ego: float) -> float:
  if (setpoint == 0.0 or setpoint * measured_lateral_accel <= 0.0 or
      abs(measured_lateral_accel) <= abs(setpoint)):
    return 1.0
  tracking_error = abs(measured_lateral_accel - setpoint)
  speed_weight = _sigmoid((v_ego - GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_SPEED) /
                          GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_SPEED_WIDTH)
  error_weight = _sigmoid((tracking_error - GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_ERROR) /
                          GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_ERROR_WIDTH)
  jerk_weight = _sigmoid((abs(desired_lateral_jerk) - GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_JERK) /
                         GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_JERK_WIDTH)
  phase_weight = 1.0 if setpoint * desired_lateral_jerk < 0.0 else 0.45
  reduction = (GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_MAX * speed_weight * error_weight *
               (0.35 + (0.65 * jerk_weight)) * phase_weight)
  return 1.0 - reduction


def get_genesis_g70_stabilized_output(output_torque: float, prev_output_torque: float,
                                      desired_lateral_accel: float, desired_lateral_jerk: float,
                                      v_ego: float, dt: float) -> float:
  speed_weight = _sigmoid((max(v_ego, 0.0) - GENESIS_G70_OUTPUT_SMOOTHING_SPEED) /
                          GENESIS_G70_OUTPUT_SMOOTHING_SPEED_WIDTH)
  center_weight = _sigmoid((GENESIS_G70_OUTPUT_SMOOTHING_CENTER_LAT - abs(desired_lateral_accel)) /
                           GENESIS_G70_OUTPUT_SMOOTHING_CENTER_LAT_WIDTH)
  curve_weight = 1.0 - center_weight
  response_time = (GENESIS_G70_OUTPUT_SMOOTHING_CURVE_RC * curve_weight +
                   GENESIS_G70_OUTPUT_SMOOTHING_CENTER_RC * center_weight)

  unwind_phase = -desired_lateral_accel * desired_lateral_jerk
  unwind_weight = _sigmoid((unwind_phase - GENESIS_G70_OUTPUT_SMOOTHING_UNWIND_PHASE) /
                           GENESIS_G70_OUTPUT_SMOOTHING_UNWIND_PHASE_WIDTH)
  response_time += GENESIS_G70_OUTPUT_SMOOTHING_UNWIND_RC * curve_weight * unwind_weight

  changing_direction = (abs(desired_lateral_accel) >= GENESIS_G70_OUTPUT_SMOOTHING_DIRECTION_CHANGE_LAT and
                        prev_output_torque * desired_lateral_accel <= 0.0)
  if changing_direction:
    response_time = max(response_time, GENESIS_G70_OUTPUT_SMOOTHING_DIRECTION_CHANGE_RC)

  output_alpha = dt / (max(response_time, 0.0) + dt)
  smoothed_output = prev_output_torque + output_alpha * (output_torque - prev_output_torque)
  return float(output_torque + speed_weight * (smoothed_output - output_torque))


def _ioniq_5_sigmoid(x: float) -> float:
  return _sigmoid(x)


def _ioniq_5_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / IONIQ_5_TRANSITION_SPEED) ** 2)


def _ioniq_5_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / IONIQ_5_PHASE_SCALE)


def _ioniq_5_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def _ioniq_5_transition_envelope(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _ioniq_5_sigmoid((abs_lateral_accel - IONIQ_5_FF_ONSET) / IONIQ_5_FF_ONSET_WIDTH)
  cutoff = _ioniq_5_sigmoid((IONIQ_5_FF_CUTOFF - abs_lateral_accel) / IONIQ_5_FF_CUTOFF_WIDTH)
  return onset * cutoff * _ioniq_5_low_speed_factor(v_ego)


def get_ioniq_5_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  envelope = _ioniq_5_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _ioniq_5_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  low_speed_factor = _ioniq_5_low_speed_factor(v_ego)
  abs_lateral_accel = abs(desired_lateral_accel)

  base_reduction = _ioniq_5_side_value(desired_lateral_accel, IONIQ_5_FF_REDUCTION_LEFT, IONIQ_5_FF_REDUCTION_RIGHT) * envelope
  turn_in_boost = 1.0 + (_ioniq_5_side_value(desired_lateral_accel, IONIQ_5_TURN_IN_BOOST_LEFT, IONIQ_5_TURN_IN_BOOST_RIGHT) *
                          turn_in_weight * (0.35 + 0.65 * low_speed_factor))
  unwind_taper = 1.0 - (_ioniq_5_side_value(desired_lateral_accel, IONIQ_5_UNWIND_TAPER_LEFT, IONIQ_5_UNWIND_TAPER_RIGHT) *
                         unwind_weight * (0.35 + 0.65 * low_speed_factor))
  sustained_turn_in_scale = 0.0
  if desired_lateral_accel * desired_lateral_jerk > 0.0:
    sustained_speed_weight = _ioniq_5_sigmoid((max(v_ego, 0.0) - IONIQ_5_SUSTAINED_TURN_IN_FF_SPEED) /
                                              IONIQ_5_SUSTAINED_TURN_IN_FF_SPEED_WIDTH)
    sustained_lat_onset = _ioniq_5_sigmoid((abs_lateral_accel - IONIQ_5_SUSTAINED_TURN_IN_FF_LAT_START) /
                                           IONIQ_5_SUSTAINED_TURN_IN_FF_LAT_WIDTH)
    sustained_lat_cutoff = _ioniq_5_sigmoid((IONIQ_5_SUSTAINED_TURN_IN_FF_LAT_END - abs_lateral_accel) /
                                            IONIQ_5_SUSTAINED_TURN_IN_FF_LAT_WIDTH)
    sustained_turn_in_scale = (_ioniq_5_side_value(desired_lateral_accel,
                                                   IONIQ_5_SUSTAINED_TURN_IN_FF_BOOST_LEFT,
                                                   IONIQ_5_SUSTAINED_TURN_IN_FF_BOOST_RIGHT) *
                               sustained_speed_weight * sustained_lat_onset * sustained_lat_cutoff)
  return (1.0 + sustained_turn_in_scale) * (1.0 - base_reduction) * turn_in_boost * max(unwind_taper, 0.0)


def get_ioniq_5_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0, desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = get_hkg_canfd_base_friction_threshold(v_ego)
  envelope = _ioniq_5_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _ioniq_5_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)

  threshold_scale = 1.0 - (_ioniq_5_side_value(desired_lateral_accel, IONIQ_5_TURN_IN_THRESHOLD_REDUCTION_LEFT, IONIQ_5_TURN_IN_THRESHOLD_REDUCTION_RIGHT) *
                           envelope * turn_in_weight)
  threshold_scale += (_ioniq_5_side_value(desired_lateral_accel, IONIQ_5_UNWIND_THRESHOLD_INCREASE_LEFT, IONIQ_5_UNWIND_THRESHOLD_INCREASE_RIGHT) *
                      envelope * unwind_weight)
  return base_threshold * min(max(threshold_scale, 0.86), 1.18)


def get_ioniq_5_friction_scale(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  if desired_lateral_accel == 0.0 or desired_lateral_jerk == 0.0:
    return 1.0

  envelope = _ioniq_5_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _ioniq_5_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)

  friction_scale = 1.0
  friction_scale += (_ioniq_5_side_value(desired_lateral_accel, IONIQ_5_TURN_IN_FRICTION_BOOST_LEFT, IONIQ_5_TURN_IN_FRICTION_BOOST_RIGHT) *
                     envelope * turn_in_weight)
  friction_scale -= (_ioniq_5_side_value(desired_lateral_accel, IONIQ_5_UNWIND_FRICTION_REDUCTION_LEFT, IONIQ_5_UNWIND_FRICTION_REDUCTION_RIGHT) *
                     envelope * unwind_weight)
  return min(max(friction_scale, 0.86), 1.04)


def get_ioniq_5_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _ioniq_5_sigmoid((v_ego - IONIQ_5_CENTER_TAPER_SPEED) / IONIQ_5_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _ioniq_5_sigmoid((IONIQ_5_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / IONIQ_5_CENTER_TAPER_LAT_WIDTH)
  reduction = IONIQ_5_CENTER_TAPER_MAX * speed_weight * center_weight
  return 1.0 - reduction


def get_ioniq_5_low_speed_output_limit(desired_lateral_accel: float,
                                       desired_lateral_jerk: float, v_ego: float) -> float:
  """Bound stop-transition center chatter without blunting actual turns."""
  speed_weight = _ioniq_5_sigmoid((IONIQ_5_LOW_SPEED_OUTPUT_LIMIT_SPEED - max(v_ego, 0.0)) /
                                  IONIQ_5_LOW_SPEED_OUTPUT_LIMIT_SPEED_WIDTH)
  center_weight = _ioniq_5_sigmoid((IONIQ_5_LOW_SPEED_CENTER_LAT - abs(desired_lateral_accel)) /
                                   IONIQ_5_LOW_SPEED_CENTER_LAT_WIDTH)
  calm_weight = _ioniq_5_sigmoid((IONIQ_5_LOW_SPEED_CENTER_JERK - abs(desired_lateral_jerk)) /
                                 IONIQ_5_LOW_SPEED_CENTER_JERK_WIDTH)
  center_weight *= calm_weight
  center_limit = (IONIQ_5_LOW_SPEED_OUTPUT_LIMIT_BASE +
                  IONIQ_5_LOW_SPEED_OUTPUT_LIMIT_TURN_RELIEF * (1.0 - center_weight))
  limit = 1.0 - speed_weight * (1.0 - center_limit)
  return float(np.clip(limit, IONIQ_5_LOW_SPEED_OUTPUT_LIMIT_BASE, 1.0))


def get_ioniq_5_friction_jerk_deadzone(v_ego: float, desired_lateral_accel: float) -> float:
  """Suppress high-speed friction reversals without reducing steady-turn torque."""
  speed_weight = _ioniq_5_sigmoid((max(v_ego, 0.0) - IONIQ_5_FRICTION_JERK_DEADZONE_SPEED) /
                                  IONIQ_5_FRICTION_JERK_DEADZONE_SPEED_WIDTH)
  curve_weight = _ioniq_5_sigmoid((IONIQ_5_FRICTION_JERK_DEADZONE_LAT - abs(desired_lateral_accel)) /
                                   IONIQ_5_FRICTION_JERK_DEADZONE_LAT_WIDTH)
  return IONIQ_5_FRICTION_JERK_DEADZONE_MAX * speed_weight * curve_weight


def _ioniq_ev_old_sigmoid(x: float) -> float:
  return _sigmoid(x)


def _ioniq_ev_old_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / IONIQ_EV_OLD_TRANSITION_SPEED) ** 2)


def _ioniq_ev_old_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / IONIQ_EV_OLD_PHASE_SCALE)


def _ioniq_ev_old_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def get_ioniq_ev_old_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _ioniq_ev_old_sigmoid((abs_lateral_accel - IONIQ_EV_OLD_FF_ONSET) / IONIQ_EV_OLD_FF_ONSET_WIDTH)
  cutoff = _ioniq_ev_old_sigmoid((IONIQ_EV_OLD_FF_CUTOFF - abs_lateral_accel) / IONIQ_EV_OLD_FF_CUTOFF_WIDTH)
  base_reduction = _ioniq_ev_old_side_value(desired_lateral_accel, IONIQ_EV_OLD_FF_REDUCTION_LEFT, IONIQ_EV_OLD_FF_REDUCTION_RIGHT) * onset * cutoff
  phase = _ioniq_ev_old_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  low_speed_factor = _ioniq_ev_old_low_speed_factor(v_ego)
  turn_in_boost = 1.0 + (_ioniq_ev_old_side_value(desired_lateral_accel, IONIQ_EV_OLD_TURN_IN_BOOST_LEFT, IONIQ_EV_OLD_TURN_IN_BOOST_RIGHT) *
                         turn_in_weight * (0.35 + 0.65 * low_speed_factor))
  unwind_taper = 1.0 - (_ioniq_ev_old_side_value(desired_lateral_accel, IONIQ_EV_OLD_UNWIND_TAPER_LEFT, IONIQ_EV_OLD_UNWIND_TAPER_RIGHT) *
                        unwind_weight * (0.35 + 0.65 * low_speed_factor))
  return (1.0 - base_reduction) * turn_in_boost * max(unwind_taper, 0.0)


def get_ioniq_ev_old_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _ioniq_ev_old_sigmoid((v_ego - IONIQ_EV_OLD_CENTER_TAPER_SPEED) / IONIQ_EV_OLD_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _ioniq_ev_old_sigmoid((IONIQ_EV_OLD_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / IONIQ_EV_OLD_CENTER_TAPER_LAT_WIDTH)
  reduction = IONIQ_EV_OLD_CENTER_TAPER_MAX * speed_weight * center_weight
  return 1.0 - reduction


def _ioniq_6_sigmoid(x: float) -> float:
  return _sigmoid(x)


def _ioniq_6_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / IONIQ_6_TRANSITION_SPEED) ** 2)


def _ioniq_6_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / IONIQ_6_PHASE_SCALE)


def _ioniq_6_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def _ioniq_6_transition_envelope(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  lat_factor = 1.0 - math.exp(-abs(desired_lateral_accel) / IONIQ_6_FRICTION_LAT_RISE)
  jerk_factor = 1.0 - math.exp(-abs(desired_lateral_jerk) / IONIQ_6_FRICTION_JERK_RISE)
  return _ioniq_6_low_speed_factor(v_ego) * lat_factor * jerk_factor


def _ioniq_6_curvy_speed_weight(v_ego: float) -> float:
  curvy_speed_min = _flm_vehicle_knob("hyundai_ioniq_6.curvy_speed_min", IONIQ_6_CURVY_SPEED_MIN)
  curvy_speed_max = _flm_vehicle_knob("hyundai_ioniq_6.curvy_speed_max", IONIQ_6_CURVY_SPEED_MAX)
  onset = _ioniq_6_sigmoid((max(v_ego, 0.0) - curvy_speed_min) / IONIQ_6_CURVY_SPEED_MIN_WIDTH)
  cutoff = _ioniq_6_sigmoid((curvy_speed_max - max(v_ego, 0.0)) / IONIQ_6_CURVY_SPEED_MAX_WIDTH)
  return onset * cutoff


def _ioniq_6_curvy_turn_in_trim_speed_weight(v_ego: float) -> float:
  curvy_turn_in_speed_min = _flm_vehicle_knob("hyundai_ioniq_6.curvy_turn_in_trim_speed_min", IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_MIN)
  curvy_turn_in_speed_max = _flm_vehicle_knob("hyundai_ioniq_6.curvy_turn_in_trim_speed_max", IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_MAX)
  onset = _ioniq_6_sigmoid((max(v_ego, 0.0) - curvy_turn_in_speed_min) / IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_WIDTH)
  cutoff = _ioniq_6_sigmoid((curvy_turn_in_speed_max - max(v_ego, 0.0)) / IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_WIDTH)
  return onset * cutoff


def get_ioniq_6_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float,
                         directional_taper_scale: float | None = None) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  gain = _ioniq_6_side_value(
    desired_lateral_accel,
    _flm_vehicle_knob("hyundai_ioniq_6.ff_gain_left", IONIQ_6_FF_GAIN_LEFT),
    _flm_vehicle_knob("hyundai_ioniq_6.ff_gain_right", IONIQ_6_FF_GAIN_RIGHT),
  )
  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _ioniq_6_sigmoid((abs_lateral_accel - IONIQ_6_FF_ONSET) / IONIQ_6_FF_ONSET_WIDTH)
  cutoff = _ioniq_6_sigmoid((IONIQ_6_FF_CUTOFF - abs_lateral_accel) / IONIQ_6_FF_CUTOFF_WIDTH)
  extra_scale = gain * onset * cutoff
  phase = _ioniq_6_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  low_speed_factor = _ioniq_6_low_speed_factor(v_ego)
  turn_in_boost = 1.0 + (_ioniq_6_side_value(
                          desired_lateral_accel,
                          _flm_vehicle_knob("hyundai_ioniq_6.turn_in_boost_left", IONIQ_6_TURN_IN_BOOST_LEFT),
                          _flm_vehicle_knob("hyundai_ioniq_6.turn_in_boost_right", IONIQ_6_TURN_IN_BOOST_RIGHT),
                        ) *
                          turn_in_weight * low_speed_factor)
  unwind_taper = 1.0 - (_ioniq_6_side_value(
                         desired_lateral_accel,
                         _flm_vehicle_knob("hyundai_ioniq_6.unwind_taper_left", IONIQ_6_UNWIND_TAPER_LEFT),
                         _flm_vehicle_knob("hyundai_ioniq_6.unwind_taper_right", IONIQ_6_UNWIND_TAPER_RIGHT),
                       ) *
                         unwind_weight * (0.30 + 0.70 * low_speed_factor))
  crawl_turn_in_scale = 0.0
  if desired_lateral_accel * desired_lateral_jerk > 0.0:
    crawl_speed_weight = _ioniq_6_sigmoid((IONIQ_6_CRAWL_TURN_IN_FF_SPEED - max(v_ego, 0.0)) /
                                          IONIQ_6_CRAWL_TURN_IN_FF_SPEED_WIDTH)
    crawl_lat_weight = _ioniq_6_sigmoid((abs_lateral_accel - IONIQ_6_CRAWL_TURN_IN_FF_LAT) /
                                        IONIQ_6_CRAWL_TURN_IN_FF_LAT_WIDTH)
    crawl_turn_in_scale = _ioniq_6_side_value(
      desired_lateral_accel,
      _flm_vehicle_knob("hyundai_ioniq_6.crawl_turn_in_ff_boost_left", IONIQ_6_CRAWL_TURN_IN_FF_BOOST_LEFT),
      _flm_vehicle_knob("hyundai_ioniq_6.crawl_turn_in_ff_boost_right", IONIQ_6_CRAWL_TURN_IN_FF_BOOST_RIGHT),
    ) * crawl_speed_weight * crawl_lat_weight
  high_speed_right_turn_in_scale = 0.0
  if desired_lateral_accel < 0.0 and desired_lateral_accel * desired_lateral_jerk > 0.0:
    high_speed_weight = _ioniq_6_sigmoid((max(v_ego, 0.0) - IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_SPEED) /
                                         IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_SPEED_WIDTH)
    high_speed_lat_onset = _ioniq_6_sigmoid((abs_lateral_accel - IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_LAT_START) /
                                            IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_LAT_WIDTH)
    high_speed_lat_cutoff = _ioniq_6_sigmoid((IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_LAT_END - abs_lateral_accel) /
                                             IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_LAT_WIDTH)
    high_speed_right_turn_in_scale = IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_BOOST * high_speed_weight * high_speed_lat_onset * high_speed_lat_cutoff
  if directional_taper_scale is None:
    directional_taper_scale = get_ioniq_6_directional_taper_scale(desired_lateral_accel, desired_lateral_jerk, v_ego)
  return (1.0 + crawl_turn_in_scale + high_speed_right_turn_in_scale +
          (extra_scale * turn_in_boost * max(unwind_taper, 0.0))) * directional_taper_scale


def get_ioniq_6_2023_unwind_ff_scale(setpoint: float, measured_lateral_accel: float,
                                     desired_lateral_jerk: float, v_ego: float) -> float:
  """Trim residual curve feedforward when the 2023 car is already over-rotated."""
  if setpoint * desired_lateral_jerk >= 0.0 or setpoint * measured_lateral_accel <= 0.0:
    return 1.0

  overshoot = max(abs(measured_lateral_accel) - abs(setpoint), 0.0)
  if overshoot <= 0.0:
    return 1.0

  overshoot_weight = _ioniq_6_sigmoid((overshoot - IONIQ_6_2023_UNWIND_FF_OVERSHOOT) /
                                      IONIQ_6_2023_UNWIND_FF_OVERSHOOT_WIDTH)
  jerk_weight = _ioniq_6_sigmoid((abs(desired_lateral_jerk) - IONIQ_6_2023_UNWIND_FF_JERK) /
                                 IONIQ_6_2023_UNWIND_FF_JERK_WIDTH)
  speed_onset = _ioniq_6_sigmoid((v_ego - IONIQ_6_2023_UNWIND_FF_SPEED_ONSET) /
                                 IONIQ_6_2023_UNWIND_FF_SPEED_ONSET_WIDTH)
  speed_cutoff = _ioniq_6_sigmoid((IONIQ_6_2023_UNWIND_FF_SPEED_CUTOFF - v_ego) /
                                  IONIQ_6_2023_UNWIND_FF_SPEED_CUTOFF_WIDTH)
  reduction = (IONIQ_6_2023_UNWIND_FF_REDUCTION_MAX * overshoot_weight * jerk_weight *
               speed_onset * speed_cutoff)
  return 1.0 - reduction


def get_ioniq_6_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0, desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = max(get_hkg_canfd_base_friction_threshold(v_ego), IONIQ_6_BASE_FRICTION_THRESHOLD)
  transition_envelope = _ioniq_6_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _ioniq_6_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  unwind_speed_weight = _ioniq_6_sigmoid((v_ego - IONIQ_6_UNWIND_HIGH_SPEED_SPEED) / IONIQ_6_UNWIND_HIGH_SPEED_SPEED_WIDTH)
  threshold_scale = 1.0 - (_ioniq_6_side_value(
                           desired_lateral_accel,
                           _flm_vehicle_knob("hyundai_ioniq_6.turn_in_threshold_reduction_left", IONIQ_6_TURN_IN_THRESHOLD_REDUCTION_LEFT),
                           _flm_vehicle_knob("hyundai_ioniq_6.turn_in_threshold_reduction_right", IONIQ_6_TURN_IN_THRESHOLD_REDUCTION_RIGHT),
                         ) *
                           transition_envelope * turn_in_weight)
  threshold_scale += (_ioniq_6_side_value(
                      desired_lateral_accel,
                      _flm_vehicle_knob("hyundai_ioniq_6.unwind_threshold_increase_left", IONIQ_6_UNWIND_THRESHOLD_INCREASE_LEFT),
                      _flm_vehicle_knob("hyundai_ioniq_6.unwind_threshold_increase_right", IONIQ_6_UNWIND_THRESHOLD_INCREASE_RIGHT),
                    ) *
                      transition_envelope * unwind_weight * unwind_speed_weight)
  return base_threshold * min(max(threshold_scale, 0.82), 1.18)


def get_ioniq_6_friction_scale(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  transition_envelope = _ioniq_6_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _ioniq_6_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  unwind_speed_weight = _ioniq_6_sigmoid((v_ego - IONIQ_6_UNWIND_HIGH_SPEED_SPEED) / IONIQ_6_UNWIND_HIGH_SPEED_SPEED_WIDTH)
  friction_scale = IONIQ_6_FRICTION_MULT
  friction_scale += (_ioniq_6_side_value(desired_lateral_accel, IONIQ_6_TURN_IN_FRICTION_BOOST_LEFT, IONIQ_6_TURN_IN_FRICTION_BOOST_RIGHT) *
                     transition_envelope * turn_in_weight)
  friction_scale -= (_ioniq_6_side_value(desired_lateral_accel, IONIQ_6_UNWIND_FRICTION_REDUCTION_LEFT, IONIQ_6_UNWIND_FRICTION_REDUCTION_RIGHT) *
                     transition_envelope * unwind_weight * unwind_speed_weight)
  return min(max(friction_scale, 0.82), 1.08)


def get_ioniq_6_friction_center_fade_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _ioniq_6_sigmoid((v_ego - IONIQ_6_FRICTION_CENTER_FADE_SPEED) / IONIQ_6_FRICTION_CENTER_FADE_SPEED_WIDTH)
  center_weight = _ioniq_6_sigmoid((IONIQ_6_FRICTION_CENTER_FADE_LAT - abs(desired_lateral_accel)) / IONIQ_6_FRICTION_CENTER_FADE_LAT_WIDTH)
  return 1.0 - IONIQ_6_FRICTION_CENTER_FADE_MAX * speed_weight * center_weight


def get_ioniq_6_2025_center_output_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _ioniq_6_sigmoid((v_ego - IONIQ_6_2025_CENTER_OUTPUT_TAPER_SPEED) /
                                  IONIQ_6_2025_CENTER_OUTPUT_TAPER_SPEED_WIDTH)
  center_weight = _ioniq_6_sigmoid((IONIQ_6_2025_CENTER_OUTPUT_TAPER_LAT - abs(desired_lateral_accel)) /
                                   IONIQ_6_2025_CENTER_OUTPUT_TAPER_LAT_WIDTH)
  return 1.0 - IONIQ_6_2025_CENTER_OUTPUT_TAPER_MAX * speed_weight * center_weight


def get_ioniq_6_2025_low_speed_output_limit(desired_lateral_accel: float,
                                              desired_lateral_jerk: float, v_ego: float) -> float:
  """Limit small-signal torque at crawl speed while leaving real turn commands open."""
  speed_weight = _ioniq_6_sigmoid((IONIQ_6_2025_LOW_SPEED_OUTPUT_LIMIT_SPEED - max(v_ego, 0.0)) /
                                  IONIQ_6_2025_LOW_SPEED_OUTPUT_LIMIT_SPEED_WIDTH)
  center_weight = _ioniq_6_sigmoid((IONIQ_6_2025_LOW_SPEED_CENTER_LAT - abs(desired_lateral_accel)) /
                                   IONIQ_6_2025_LOW_SPEED_CENTER_LAT_WIDTH)
  calm_weight = _ioniq_6_sigmoid((IONIQ_6_2025_LOW_SPEED_CENTER_JERK - abs(desired_lateral_jerk)) /
                                 IONIQ_6_2025_LOW_SPEED_CENTER_JERK_WIDTH)
  center_weight *= calm_weight
  limit = (IONIQ_6_2025_LOW_SPEED_OUTPUT_LIMIT_BASE +
           IONIQ_6_2025_LOW_SPEED_OUTPUT_LIMIT_TURN_RELIEF * (1.0 - center_weight) +
           IONIQ_6_2025_LOW_SPEED_OUTPUT_LIMIT_SPEED_RELIEF * (1.0 - speed_weight))
  return float(np.clip(limit, IONIQ_6_2025_LOW_SPEED_OUTPUT_LIMIT_BASE, 1.0))


def _ioniq_6_2025_low_speed_center_envelope(desired_lateral_accel: float,
                                             desired_lateral_jerk: float, v_ego: float) -> float:
  speed_weight = _ioniq_6_sigmoid((IONIQ_6_2025_LOW_SPEED_CENTER_SPEED - max(v_ego, 0.0)) /
                                  IONIQ_6_2025_LOW_SPEED_CENTER_SPEED_WIDTH)
  center_weight = _ioniq_6_sigmoid((IONIQ_6_2025_LOW_SPEED_CENTER_LAT - abs(desired_lateral_accel)) /
                                   IONIQ_6_2025_LOW_SPEED_CENTER_LAT_WIDTH)
  calm_weight = _ioniq_6_sigmoid((IONIQ_6_2025_LOW_SPEED_CENTER_JERK - abs(desired_lateral_jerk)) /
                                 IONIQ_6_2025_LOW_SPEED_CENTER_JERK_WIDTH)
  return speed_weight * center_weight * calm_weight


def get_ioniq_6_2025_low_speed_center_error_scale(desired_lateral_accel: float,
                                                   desired_lateral_jerk: float, v_ego: float) -> float:
  envelope = _ioniq_6_2025_low_speed_center_envelope(desired_lateral_accel, desired_lateral_jerk, v_ego)
  return 1.0 - (1.0 - IONIQ_6_2025_LOW_SPEED_CENTER_ERROR_SCALE) * envelope


def get_ioniq_6_2025_low_speed_center_friction_scale(desired_lateral_accel: float,
                                                      desired_lateral_jerk: float, v_ego: float) -> float:
  envelope = _ioniq_6_2025_low_speed_center_envelope(desired_lateral_accel, desired_lateral_jerk, v_ego)
  return 1.0 - (1.0 - IONIQ_6_2025_LOW_SPEED_CENTER_FRICTION_SCALE) * envelope


def get_ioniq_6_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _ioniq_6_sigmoid((v_ego - IONIQ_6_CENTER_TAPER_SPEED) / IONIQ_6_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _ioniq_6_sigmoid((IONIQ_6_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / IONIQ_6_CENTER_TAPER_LAT_WIDTH)
  high_speed_reduction = _flm_vehicle_knob("hyundai_ioniq_6.center_taper_max", IONIQ_6_CENTER_TAPER_MAX) * speed_weight * center_weight

  highway_speed_weight = _ioniq_6_sigmoid((v_ego - IONIQ_6_HIGHWAY_CENTER_TAPER_SPEED) / IONIQ_6_HIGHWAY_CENTER_TAPER_SPEED_WIDTH)
  highway_center_weight = _ioniq_6_sigmoid((IONIQ_6_HIGHWAY_CENTER_TAPER_LAT - abs(desired_lateral_accel)) /
                                           IONIQ_6_HIGHWAY_CENTER_TAPER_LAT_WIDTH)
  highway_center_reduction = _flm_vehicle_knob("hyundai_ioniq_6.highway_center_taper_max", IONIQ_6_HIGHWAY_CENTER_TAPER_MAX) * highway_speed_weight * highway_center_weight

  low_mid_onset = _ioniq_6_sigmoid((v_ego - IONIQ_6_LOW_MID_CENTER_TAPER_SPEED_MIN) / IONIQ_6_LOW_MID_CENTER_TAPER_SPEED_WIDTH)
  low_mid_cutoff = _ioniq_6_sigmoid((IONIQ_6_LOW_MID_CENTER_TAPER_SPEED_MAX - v_ego) / IONIQ_6_LOW_MID_CENTER_TAPER_SPEED_WIDTH)
  low_mid_speed_weight = low_mid_onset * low_mid_cutoff
  low_mid_center_weight = _ioniq_6_sigmoid((IONIQ_6_LOW_MID_CENTER_TAPER_LAT - abs(desired_lateral_accel)) /
                                           IONIQ_6_LOW_MID_CENTER_TAPER_LAT_WIDTH)
  low_mid_reduction = IONIQ_6_LOW_MID_CENTER_TAPER_MAX * low_mid_speed_weight * low_mid_center_weight

  return 1.0 - min(high_speed_reduction + highway_center_reduction + low_mid_reduction, 0.12)


def get_ioniq_6_directional_taper_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float | None = None) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _ioniq_6_sigmoid((abs_lateral_accel - IONIQ_6_DIRECTIONAL_TAPER_LAT_START) / IONIQ_6_DIRECTIONAL_TAPER_LAT_WIDTH)
  cutoff = _ioniq_6_sigmoid((IONIQ_6_DIRECTIONAL_TAPER_LAT_END - abs_lateral_accel) / IONIQ_6_DIRECTIONAL_TAPER_LAT_WIDTH)
  band_weight = onset * cutoff
  heavy_band_weight = _ioniq_6_sigmoid((abs_lateral_accel - IONIQ_6_HEAVY_DIRECTIONAL_TAPER_LAT_START) / IONIQ_6_HEAVY_DIRECTIONAL_TAPER_LAT_WIDTH)
  phase = math.tanh((desired_lateral_accel * desired_lateral_jerk) / IONIQ_6_DIRECTIONAL_TAPER_PHASE_SCALE)
  unwind_weight = max(-phase, 0.0) * _ioniq_6_sigmoid((abs(desired_lateral_jerk) - IONIQ_6_DIRECTIONAL_TAPER_JERK_ONSET) /
                                                       IONIQ_6_DIRECTIONAL_TAPER_JERK_WIDTH)
  low_speed_relief_weight = 0.0
  curvy_turn_in_trim_weight = 0.0
  if v_ego is not None:
    low_speed_weight = _ioniq_6_sigmoid((IONIQ_6_DIRECTIONAL_TAPER_LOW_SPEED_RELIEF_SPEED - max(v_ego, 0.0)) /
                                        IONIQ_6_DIRECTIONAL_TAPER_LOW_SPEED_RELIEF_SPEED_WIDTH)
    tight_turn_weight = _ioniq_6_sigmoid((abs_lateral_accel - IONIQ_6_DIRECTIONAL_TAPER_LOW_SPEED_RELIEF_LAT) /
                                         IONIQ_6_DIRECTIONAL_TAPER_LOW_SPEED_RELIEF_LAT_WIDTH)
    low_speed_relief_weight = IONIQ_6_DIRECTIONAL_TAPER_LOW_SPEED_RELIEF * low_speed_weight * tight_turn_weight * (1.0 - unwind_weight)
    turn_in_weight = max(phase, 0.0)
    curvy_turn_in_speed_weight = _ioniq_6_curvy_turn_in_trim_speed_weight(v_ego)
    curvy_turn_in_lat_onset = _ioniq_6_sigmoid((abs_lateral_accel - IONIQ_6_CURVY_TURN_IN_TRIM_LAT_START) /
                                               IONIQ_6_CURVY_TURN_IN_TRIM_LAT_ONSET_WIDTH)
    curvy_turn_in_lat_cutoff = _ioniq_6_sigmoid((IONIQ_6_CURVY_TURN_IN_TRIM_LAT_END - abs_lateral_accel) /
                                                IONIQ_6_CURVY_TURN_IN_TRIM_LAT_CUTOFF_WIDTH)
    curvy_turn_in_trim_weight = curvy_turn_in_speed_weight * curvy_turn_in_lat_onset * curvy_turn_in_lat_cutoff * turn_in_weight
  base_reduction = _ioniq_6_side_value(desired_lateral_accel, IONIQ_6_DIRECTIONAL_TAPER_BASE_LEFT, IONIQ_6_DIRECTIONAL_TAPER_BASE_RIGHT)
  unwind_reduction = _ioniq_6_side_value(desired_lateral_accel, IONIQ_6_DIRECTIONAL_TAPER_UNWIND_LEFT, IONIQ_6_DIRECTIONAL_TAPER_UNWIND_RIGHT)
  heavy_base_reduction = _ioniq_6_side_value(desired_lateral_accel, IONIQ_6_HEAVY_DIRECTIONAL_TAPER_BASE_LEFT, IONIQ_6_HEAVY_DIRECTIONAL_TAPER_BASE_RIGHT)
  heavy_unwind_reduction = _ioniq_6_side_value(desired_lateral_accel, IONIQ_6_HEAVY_DIRECTIONAL_TAPER_UNWIND_LEFT, IONIQ_6_HEAVY_DIRECTIONAL_TAPER_UNWIND_RIGHT)
  base_reduction *= 1.0 - low_speed_relief_weight
  heavy_base_reduction *= 1.0 - low_speed_relief_weight
  reduction = band_weight * (base_reduction + unwind_reduction * unwind_weight)
  reduction += heavy_band_weight * (heavy_base_reduction + heavy_unwind_reduction * unwind_weight)
  reduction += (_ioniq_6_side_value(desired_lateral_accel,
                                    _flm_vehicle_knob("hyundai_ioniq_6.curvy_turn_in_trim_left", IONIQ_6_CURVY_TURN_IN_TRIM_LEFT),
                                    _flm_vehicle_knob("hyundai_ioniq_6.curvy_turn_in_trim_right", IONIQ_6_CURVY_TURN_IN_TRIM_RIGHT)) *
                curvy_turn_in_trim_weight)
  curvy_unwind_weight = 0.0
  curvy_unwind_floor_relief = 0.0
  if v_ego is not None:
    curvy_unwind_phase_weight = unwind_weight
    if desired_lateral_accel < 0.0:
      curvy_unwind_phase_weight = max(-phase, 0.0) * _ioniq_6_sigmoid(
        (abs(desired_lateral_jerk) - IONIQ_6_CURVY_RIGHT_UNWIND_JERK_ONSET) / IONIQ_6_CURVY_RIGHT_UNWIND_JERK_WIDTH)
    curvy_unwind_speed_weight = _ioniq_6_curvy_speed_weight(v_ego)
    curvy_unwind_lat_onset = _ioniq_6_sigmoid((abs_lateral_accel - IONIQ_6_CURVY_UNWIND_LAT_START) /
                                              IONIQ_6_CURVY_UNWIND_LAT_ONSET_WIDTH)
    curvy_unwind_lat_cutoff = _ioniq_6_sigmoid((IONIQ_6_CURVY_UNWIND_LAT_END - abs_lateral_accel) /
                                               IONIQ_6_CURVY_UNWIND_LAT_CUTOFF_WIDTH)
    curvy_unwind_weight = curvy_unwind_speed_weight * curvy_unwind_lat_onset * curvy_unwind_lat_cutoff * curvy_unwind_phase_weight
    curvy_unwind_floor_relief = (_ioniq_6_side_value(desired_lateral_accel,
                                                     _flm_vehicle_knob("hyundai_ioniq_6.curvy_unwind_floor_relief_left", IONIQ_6_CURVY_UNWIND_FLOOR_RELIEF_LEFT),
                                                     _flm_vehicle_knob("hyundai_ioniq_6.curvy_unwind_floor_relief_right", IONIQ_6_CURVY_UNWIND_FLOOR_RELIEF_RIGHT)) *
                                 curvy_unwind_weight)
  reduction += (_ioniq_6_side_value(desired_lateral_accel,
                                    _flm_vehicle_knob("hyundai_ioniq_6.curvy_unwind_extra_reduction_left", IONIQ_6_CURVY_UNWIND_EXTRA_REDUCTION_LEFT),
                                    _flm_vehicle_knob("hyundai_ioniq_6.curvy_unwind_extra_reduction_right", IONIQ_6_CURVY_UNWIND_EXTRA_REDUCTION_RIGHT)) *
                curvy_unwind_weight)
  floor = _ioniq_6_side_value(desired_lateral_accel, IONIQ_6_DIRECTIONAL_TAPER_FLOOR_LEFT, IONIQ_6_DIRECTIONAL_TAPER_FLOOR_RIGHT)
  floor -= _ioniq_6_side_value(desired_lateral_accel, IONIQ_6_DIRECTIONAL_TAPER_UNWIND_FLOOR_LEFT, IONIQ_6_DIRECTIONAL_TAPER_UNWIND_FLOOR_RIGHT) * unwind_weight
  floor -= curvy_unwind_floor_relief
  return max(1.0 - reduction, floor)


def get_ioniq_6_output_taper_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  speed_weight = _ioniq_6_sigmoid((v_ego - IONIQ_6_OUTPUT_TAPER_SPEED) / IONIQ_6_OUTPUT_TAPER_SPEED_WIDTH)
  center_taper = get_ioniq_6_center_taper_scale(desired_lateral_accel, v_ego)
  directional_taper = get_ioniq_6_directional_taper_scale(desired_lateral_accel, desired_lateral_jerk, v_ego)
  center_scale = 1.0 - ((1.0 - center_taper) * IONIQ_6_OUTPUT_CENTER_TAPER_BLEND * speed_weight)
  directional_scale = 1.0 - ((1.0 - directional_taper) * IONIQ_6_OUTPUT_DIRECTIONAL_TAPER_BLEND * speed_weight)
  return center_scale * directional_scale


def get_ioniq_6_highway_output_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _ioniq_6_sigmoid((v_ego - IONIQ_6_HIGHWAY_OUTPUT_TAPER_SPEED) / IONIQ_6_HIGHWAY_OUTPUT_TAPER_SPEED_WIDTH)
  center_weight = _ioniq_6_sigmoid((IONIQ_6_HIGHWAY_OUTPUT_TAPER_LAT - abs(desired_lateral_accel)) /
                                   IONIQ_6_HIGHWAY_OUTPUT_TAPER_LAT_WIDTH)
  reduction = IONIQ_6_HIGHWAY_OUTPUT_TAPER_MAX * speed_weight * center_weight
  return 1.0 - reduction


def get_ioniq_6_highway_transition_output_taper_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  speed_weight = _ioniq_6_sigmoid((v_ego - IONIQ_6_HIGHWAY_OUTPUT_TAPER_SPEED) / IONIQ_6_HIGHWAY_OUTPUT_TAPER_SPEED_WIDTH)
  center_weight = _ioniq_6_sigmoid((IONIQ_6_HIGHWAY_TRANSITION_OUTPUT_TAPER_LAT - abs(desired_lateral_accel)) /
                                   IONIQ_6_HIGHWAY_TRANSITION_OUTPUT_TAPER_LAT_WIDTH)
  jerk_weight = _ioniq_6_sigmoid((abs(desired_lateral_jerk) - IONIQ_6_HIGHWAY_TRANSITION_OUTPUT_TAPER_JERK) /
                                 IONIQ_6_HIGHWAY_TRANSITION_OUTPUT_TAPER_JERK_WIDTH)
  reduction = IONIQ_6_HIGHWAY_TRANSITION_OUTPUT_TAPER_MAX * speed_weight * center_weight * jerk_weight
  return 1.0 - reduction


def get_ioniq_6_low_speed_angle_assist_torque(desired_angle_deg: float, actual_angle_deg: float,
                                              current_output_torque: float, v_ego: float) -> float:
  angle_error = desired_angle_deg - actual_angle_deg
  if desired_angle_deg * angle_error > 0.0:
    speed_weight = _ioniq_6_sigmoid((IONIQ_6_LOW_SPEED_ANGLE_ASSIST_SPEED - max(v_ego, 0.0)) /
                                    IONIQ_6_LOW_SPEED_ANGLE_ASSIST_SPEED_WIDTH)
    error_weight = _ioniq_6_sigmoid((abs(angle_error) - IONIQ_6_LOW_SPEED_ANGLE_ASSIST_ERROR) /
                                    IONIQ_6_LOW_SPEED_ANGLE_ASSIST_ERROR_WIDTH)
    desired_angle_weight = _ioniq_6_sigmoid((abs(desired_angle_deg) - IONIQ_6_LOW_SPEED_ANGLE_ASSIST_DESIRED_ANGLE) /
                                            IONIQ_6_LOW_SPEED_ANGLE_ASSIST_DESIRED_ANGLE_WIDTH)
    tracking_ratio = abs(actual_angle_deg) / max(abs(desired_angle_deg), 1e-3)
    tracking_taper = _ioniq_6_sigmoid((tracking_ratio - IONIQ_6_LOW_SPEED_ANGLE_ASSIST_TRACK_RATIO_START) /
                                      IONIQ_6_LOW_SPEED_ANGLE_ASSIST_TRACK_RATIO_WIDTH)
    tracking_scale = max(1.0 - tracking_taper, IONIQ_6_LOW_SPEED_ANGLE_ASSIST_TRACK_RATIO_FLOOR)
    assist_torque = math.copysign(
      _flm_vehicle_knob("hyundai_ioniq_6.low_speed_angle_assist_max_torque", IONIQ_6_LOW_SPEED_ANGLE_ASSIST_MAX_TORQUE) *
      speed_weight * error_weight * desired_angle_weight * tracking_scale,
      -angle_error,
    )
    if abs(assist_torque) < 1e-4:
      return current_output_torque

    if current_output_torque * assist_torque >= 0.0:
      add_scale = float(np.interp(abs(current_output_torque),
                                  IONIQ_6_LOW_SPEED_ANGLE_ASSIST_ADD_BP,
                                  IONIQ_6_LOW_SPEED_ANGLE_ASSIST_ADD_V))
      return float(np.clip(current_output_torque + (assist_torque * add_scale), -1.0, 1.0))

    return float(np.clip(current_output_torque + assist_torque, -1.0, 1.0))

  speed_weight = _ioniq_6_sigmoid((IONIQ_6_LOW_SPEED_UNWIND_ASSIST_SPEED - max(v_ego, 0.0)) /
                                  IONIQ_6_LOW_SPEED_UNWIND_ASSIST_SPEED_WIDTH)
  error_weight = _ioniq_6_sigmoid((abs(angle_error) - IONIQ_6_LOW_SPEED_UNWIND_ASSIST_ERROR) /
                                  IONIQ_6_LOW_SPEED_UNWIND_ASSIST_ERROR_WIDTH)
  actual_angle_weight = _ioniq_6_sigmoid((abs(actual_angle_deg) - IONIQ_6_LOW_SPEED_UNWIND_ASSIST_ACTUAL_ANGLE) /
                                         IONIQ_6_LOW_SPEED_UNWIND_ASSIST_ACTUAL_ANGLE_WIDTH)
  assist_torque = math.copysign(IONIQ_6_LOW_SPEED_UNWIND_ASSIST_MAX_TORQUE * speed_weight * error_weight * actual_angle_weight, -angle_error)
  if abs(assist_torque) < 1e-4:
    return current_output_torque

  if current_output_torque * assist_torque >= 0.0:
    assist_torque *= IONIQ_6_LOW_SPEED_UNWIND_ASSIST_BLEND

  return float(np.clip(current_output_torque + assist_torque, -1.0, 1.0))


def kia_ev6_lateral_testing_ground_active() -> bool:
  return testing_ground.use(KIA_EV6_LATERAL_TESTING_GROUND_ID, KIA_EV6_LATERAL_TESTING_GROUND_VARIANT)


def _kia_ev6_sigmoid(x: float) -> float:
  return _sigmoid(x)


def _kia_ev6_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / KIA_EV6_TRANSITION_SPEED) ** 2)


def _kia_ev6_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / KIA_EV6_PHASE_SCALE)


def _kia_ev6_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def _kia_ev6_transition_envelope(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  lat_factor = 1.0 - math.exp(-abs(desired_lateral_accel) / KIA_EV6_FRICTION_LAT_RISE)
  jerk_factor = 1.0 - math.exp(-abs(desired_lateral_jerk) / KIA_EV6_FRICTION_JERK_RISE)
  return _kia_ev6_low_speed_factor(v_ego) * lat_factor * jerk_factor


def get_kia_ev6_jwarm_phase_confidence(v_ego: float, desired_lateral_jerk: float) -> float:
  low_speed_weight = _kia_ev6_sigmoid(
    (KIA_EV6_JWARM_PHASE_STABILITY_SPEED - v_ego) / KIA_EV6_JWARM_PHASE_STABILITY_SPEED_WIDTH
  )
  abrupt_transition_weight = _kia_ev6_sigmoid(
    (abs(desired_lateral_jerk) - KIA_EV6_JWARM_PHASE_STABILITY_JERK) / KIA_EV6_JWARM_PHASE_STABILITY_JERK_WIDTH
  )
  return 1.0 - (KIA_EV6_JWARM_PHASE_STABILITY_MAX_REDUCTION * low_speed_weight * abrupt_transition_weight)


def get_kia_ev6_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  gain = _kia_ev6_side_value(
    desired_lateral_accel,
    _flm_vehicle_knob("hyundai_kia_ev6.ff_gain_left", KIA_EV6_FF_GAIN_LEFT),
    _flm_vehicle_knob("hyundai_kia_ev6.ff_gain_right", KIA_EV6_FF_GAIN_RIGHT),
  )
  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _kia_ev6_sigmoid((abs_lateral_accel - KIA_EV6_FF_ONSET) / KIA_EV6_FF_ONSET_WIDTH)
  cutoff = _kia_ev6_sigmoid((KIA_EV6_FF_CUTOFF - abs_lateral_accel) / KIA_EV6_FF_CUTOFF_WIDTH)
  extra_scale = gain * onset * cutoff
  phase = _kia_ev6_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  low_speed_factor = _kia_ev6_low_speed_factor(v_ego)
  turn_in_boost = 1.0 + (_kia_ev6_side_value(
                          desired_lateral_accel,
                          _flm_vehicle_knob("hyundai_kia_ev6.turn_in_boost_left", KIA_EV6_TURN_IN_BOOST_LEFT),
                          _flm_vehicle_knob("hyundai_kia_ev6.turn_in_boost_right", KIA_EV6_TURN_IN_BOOST_RIGHT),
                        ) *
                          turn_in_weight * (0.35 + 0.65 * low_speed_factor))
  unwind_taper = 1.0 - (_kia_ev6_side_value(
                         desired_lateral_accel,
                         _flm_vehicle_knob("hyundai_kia_ev6.unwind_taper_left", KIA_EV6_UNWIND_TAPER_LEFT),
                         _flm_vehicle_knob("hyundai_kia_ev6.unwind_taper_right", KIA_EV6_UNWIND_TAPER_RIGHT),
                       ) *
                         unwind_weight * (0.35 + 0.65 * low_speed_factor))
  jwarm_tune = kia_ev6_lateral_testing_ground_active()
  jwarm_phase_confidence = get_kia_ev6_jwarm_phase_confidence(v_ego, desired_lateral_jerk) if jwarm_tune else 0.0
  base_turn_in_boost = 1.0 + ((_kia_ev6_side_value(
                                desired_lateral_accel,
                                KIA_EV6_JWARM_BASE_TURN_IN_BOOST_LEFT,
                                KIA_EV6_JWARM_BASE_TURN_IN_BOOST_RIGHT,
                              ) if jwarm_tune else 0.0) *
                                jwarm_phase_confidence * turn_in_weight * onset * cutoff)
  base_unwind_taper_left = _flm_vehicle_knob("hyundai_kia_ev6.base_unwind_taper_left", KIA_EV6_BASE_UNWIND_TAPER_LEFT)
  base_unwind_taper_right = _flm_vehicle_knob("hyundai_kia_ev6.base_unwind_taper_right", KIA_EV6_BASE_UNWIND_TAPER_RIGHT)
  if jwarm_tune:
    base_unwind_taper_left += (KIA_EV6_JWARM_BASE_UNWIND_TAPER_LEFT - base_unwind_taper_left) * jwarm_phase_confidence
    base_unwind_taper_right += (KIA_EV6_JWARM_BASE_UNWIND_TAPER_RIGHT - base_unwind_taper_right) * jwarm_phase_confidence
  base_unwind_taper = 1.0 - (_kia_ev6_side_value(
                              desired_lateral_accel,
                              base_unwind_taper_left,
                              base_unwind_taper_right,
                            ) * unwind_weight * onset * cutoff)
  return (base_unwind_taper * base_turn_in_boost) + (extra_scale * turn_in_boost * max(unwind_taper, 0.0))


def get_kia_ev6_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0, desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = get_hkg_canfd_base_friction_threshold(v_ego)
  transition_envelope = _kia_ev6_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _kia_ev6_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  threshold_scale = 1.0 - (_kia_ev6_side_value(
                           desired_lateral_accel,
                           _flm_vehicle_knob("hyundai_kia_ev6.turn_in_threshold_reduction_left", KIA_EV6_TURN_IN_THRESHOLD_REDUCTION_LEFT),
                           _flm_vehicle_knob("hyundai_kia_ev6.turn_in_threshold_reduction_right", KIA_EV6_TURN_IN_THRESHOLD_REDUCTION_RIGHT),
                         ) *
                           transition_envelope * turn_in_weight)
  threshold_scale += (_kia_ev6_side_value(
                      desired_lateral_accel,
                      _flm_vehicle_knob("hyundai_kia_ev6.unwind_threshold_increase_left", KIA_EV6_UNWIND_THRESHOLD_INCREASE_LEFT),
                      _flm_vehicle_knob("hyundai_kia_ev6.unwind_threshold_increase_right", KIA_EV6_UNWIND_THRESHOLD_INCREASE_RIGHT),
                    ) *
                      transition_envelope * unwind_weight)
  center_speed_weight = _kia_ev6_sigmoid((v_ego - KIA_EV6_CENTER_FRICTION_THRESHOLD_SPEED) /
                                         KIA_EV6_CENTER_FRICTION_THRESHOLD_SPEED_WIDTH)
  center_lat_weight = _kia_ev6_sigmoid((KIA_EV6_CENTER_FRICTION_THRESHOLD_LAT - abs(desired_lateral_accel)) /
                                       KIA_EV6_CENTER_FRICTION_THRESHOLD_LAT_WIDTH)
  threshold_scale += (_flm_vehicle_knob("hyundai_kia_ev6.center_friction_threshold_gain",
                                        KIA_EV6_CENTER_FRICTION_THRESHOLD_GAIN) *
                      center_speed_weight * center_lat_weight)
  return base_threshold * min(max(threshold_scale, 0.82), 1.16)


def get_kia_ev6_friction_scale(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  transition_envelope = _kia_ev6_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _kia_ev6_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  friction_scale = KIA_EV6_FRICTION_MULT
  friction_scale += (_kia_ev6_side_value(desired_lateral_accel, KIA_EV6_TURN_IN_FRICTION_BOOST_LEFT, KIA_EV6_TURN_IN_FRICTION_BOOST_RIGHT) *
                     transition_envelope * turn_in_weight)
  friction_scale -= (_kia_ev6_side_value(desired_lateral_accel, KIA_EV6_UNWIND_FRICTION_REDUCTION_LEFT, KIA_EV6_UNWIND_FRICTION_REDUCTION_RIGHT) *
                     transition_envelope * unwind_weight)
  return min(max(friction_scale, 0.90), 1.10)


def get_kia_ev6_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _kia_ev6_sigmoid((v_ego - KIA_EV6_CENTER_TAPER_SPEED) / KIA_EV6_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _kia_ev6_sigmoid((KIA_EV6_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / KIA_EV6_CENTER_TAPER_LAT_WIDTH)
  reduction = _flm_vehicle_knob("hyundai_kia_ev6.center_taper_max", KIA_EV6_CENTER_TAPER_MAX) * speed_weight * center_weight
  return 1.0 - reduction


def get_kia_ev6_low_speed_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _kia_ev6_sigmoid((KIA_EV6_LOW_SPEED_CENTER_TAPER_SPEED_MAX - v_ego) / KIA_EV6_LOW_SPEED_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _kia_ev6_sigmoid((KIA_EV6_LOW_SPEED_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / KIA_EV6_LOW_SPEED_CENTER_TAPER_LAT_WIDTH)
  reduction = KIA_EV6_LOW_SPEED_CENTER_TAPER_MAX * speed_weight * center_weight
  return 1.0 - reduction


def get_kia_ev6_center_output_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _kia_ev6_sigmoid((v_ego - KIA_EV6_CENTER_OUTPUT_TAPER_SPEED) /
                                  KIA_EV6_CENTER_OUTPUT_TAPER_SPEED_WIDTH)
  center_weight = _kia_ev6_sigmoid((KIA_EV6_CENTER_OUTPUT_TAPER_LAT - abs(desired_lateral_accel)) /
                                   KIA_EV6_CENTER_OUTPUT_TAPER_LAT_WIDTH)
  reduction = _flm_vehicle_knob("hyundai_kia_ev6.center_output_taper_max", KIA_EV6_CENTER_OUTPUT_TAPER_MAX) * speed_weight * center_weight
  return 1.0 - reduction


def volt_plexy_lateral_testing_ground_active() -> bool:
  return testing_ground.use(VOLT_PLEXY_LATERAL_TESTING_GROUND_ID)


def _volt_plexy_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def get_volt_plexy_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  standard_scale = get_volt_standard_ff_scale(desired_lateral_accel, desired_lateral_jerk, v_ego)
  extra_scale = standard_scale - 1.0
  extra_mult = _volt_plexy_side_value(desired_lateral_accel, VOLT_PLEXY_FF_EXTRA_MULT_LEFT, VOLT_PLEXY_FF_EXTRA_MULT_RIGHT)
  return 1.0 + (extra_scale * extra_mult)


def get_volt_plexy_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0, desired_lateral_jerk: float = 0.0) -> float:
  standard_threshold = get_volt_standard_friction_threshold(v_ego, desired_lateral_accel, desired_lateral_jerk)
  threshold_mult = _volt_plexy_side_value(desired_lateral_accel, VOLT_PLEXY_FRICTION_THRESHOLD_MULT_LEFT, VOLT_PLEXY_FRICTION_THRESHOLD_MULT_RIGHT)
  return standard_threshold * threshold_mult


def get_volt_plexy_friction_scale(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  standard_scale = get_volt_standard_friction_scale(v_ego, desired_lateral_accel, desired_lateral_jerk)
  friction_extra = standard_scale - 1.0
  friction_mult = _volt_plexy_side_value(desired_lateral_accel, VOLT_PLEXY_FRICTION_SCALE_MULT_LEFT, VOLT_PLEXY_FRICTION_SCALE_MULT_RIGHT)
  return 1.0 + (friction_extra * friction_mult)


def get_volt_plexy_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  standard_scale = get_volt_standard_center_taper_scale(desired_lateral_accel, v_ego)
  standard_reduction = 1.0 - standard_scale
  return 1.0 - (standard_reduction * VOLT_PLEXY_CENTER_TAPER_REDUCTION_MULT)


FLM_UNIVERSAL_PROFILE_KEY = "torque_universal"

FLM_FULL_SURFACE_SUFFIX_METADATA = {
  "ff_gain_left": {"min": 0.0, "max": 0.60, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "ff_gain_right": {"min": 0.0, "max": 0.60, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "turn_in_boost_left": {"min": -0.10, "max": 2.80, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "turn_in_boost_right": {"min": -0.10, "max": 2.80, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "unwind_taper_left": {"min": 0.0, "max": 12.0, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "unwind_taper_right": {"min": 0.0, "max": 12.0, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "center_taper_max": {"min": 0.0, "max": 0.18, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "highway_center_taper_max": {"min": 0.0, "max": 0.18, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "center_deadband_crawl_deg": {"min": 0.0, "max": 0.30, "precision": 0.005, "deltaType": "absolute", "safeLiveTrial": True},
  "center_deadband_low_deg": {"min": 0.0, "max": 0.30, "precision": 0.005, "deltaType": "absolute", "safeLiveTrial": True},
  "center_deadband_mid_deg": {"min": 0.0, "max": 0.20, "precision": 0.005, "deltaType": "absolute", "safeLiveTrial": True},
  "center_deadband_fast_deg": {"min": 0.0, "max": 0.12, "precision": 0.005, "deltaType": "absolute", "safeLiveTrial": True},
  "center_deadband_highway_deg": {"min": 0.0, "max": 0.08, "precision": 0.005, "deltaType": "absolute", "safeLiveTrial": True},
  "turn_in_threshold_reduction_left": {"min": 0.0, "max": 2.00, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "turn_in_threshold_reduction_right": {"min": 0.0, "max": 2.00, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "unwind_threshold_increase_left": {"min": 0.0, "max": 12.0, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "unwind_threshold_increase_right": {"min": 0.0, "max": 12.0, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "crawl_turn_in_ff_boost_left": {"min": 0.0, "max": 0.50, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "crawl_turn_in_ff_boost_right": {"min": 0.0, "max": 0.50, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "low_speed_angle_assist_max_torque": {"min": 0.0, "max": 0.80, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "curvy_speed_min": {"min": 4.0, "max": 12.0, "precision": 0.1, "deltaType": "absolute", "safeLiveTrial": True},
  "curvy_speed_max": {"min": 14.0, "max": 25.0, "precision": 0.1, "deltaType": "absolute", "safeLiveTrial": True},
  "curvy_turn_in_trim_speed_min": {"min": 8.0, "max": 16.0, "precision": 0.1, "deltaType": "absolute", "safeLiveTrial": True},
  "curvy_turn_in_trim_speed_max": {"min": 14.0, "max": 25.0, "precision": 0.1, "deltaType": "absolute", "safeLiveTrial": True},
  "curvy_turn_in_trim_left": {"min": 0.0, "max": 0.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "curvy_turn_in_trim_right": {"min": 0.0, "max": 0.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "curvy_unwind_floor_relief_left": {"min": 0.0, "max": 0.45, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "curvy_unwind_floor_relief_right": {"min": 0.0, "max": 0.45, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "curvy_unwind_extra_reduction_left": {"min": 0.0, "max": 0.45, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "curvy_unwind_extra_reduction_right": {"min": 0.0, "max": 0.45, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
}

FLM_FULL_SURFACE_NEUTRAL_DEFAULTS = {
  "ff_gain_left": 0.0,
  "ff_gain_right": 0.0,
  "turn_in_boost_left": 0.0,
  "turn_in_boost_right": 0.0,
  "unwind_taper_left": 0.0,
  "unwind_taper_right": 0.0,
  "center_taper_max": 0.0,
  "highway_center_taper_max": 0.0,
  "center_deadband_crawl_deg": 0.0,
  "center_deadband_low_deg": 0.0,
  "center_deadband_mid_deg": 0.0,
  "center_deadband_fast_deg": 0.0,
  "center_deadband_highway_deg": 0.0,
  "turn_in_threshold_reduction_left": 0.0,
  "turn_in_threshold_reduction_right": 0.0,
  "unwind_threshold_increase_left": 0.0,
  "unwind_threshold_increase_right": 0.0,
  "crawl_turn_in_ff_boost_left": 0.0,
  "crawl_turn_in_ff_boost_right": 0.0,
  "low_speed_angle_assist_max_torque": 0.0,
  "curvy_speed_min": IONIQ_6_CURVY_SPEED_MIN,
  "curvy_speed_max": IONIQ_6_CURVY_SPEED_MAX,
  "curvy_turn_in_trim_speed_min": IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_MIN,
  "curvy_turn_in_trim_speed_max": IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_MAX,
  "curvy_turn_in_trim_left": 0.0,
  "curvy_turn_in_trim_right": 0.0,
  "curvy_unwind_floor_relief_left": 0.0,
  "curvy_unwind_floor_relief_right": 0.0,
  "curvy_unwind_extra_reduction_left": 0.0,
  "curvy_unwind_extra_reduction_right": 0.0,
}


def _flm_profile_symbol(profile_key: str, suffix: str) -> str:
  return f"{profile_key}.{suffix}"


def flm_profile_supports_knob(profile_key: str | None, suffix: str) -> bool:
  if not profile_key:
    return False
  return _flm_profile_symbol(profile_key, suffix) in FLM_SUPPORTED_VEHICLE_KNOBS


def _flm_full_surface_side_value(profile_key: str, desired_lateral_accel: float,
                                 suffix: str, left_default: float = 0.0, right_default: float = 0.0) -> float:
  if desired_lateral_accel >= 0.0:
    return _flm_vehicle_knob(_flm_profile_symbol(profile_key, f"{suffix}_left"), left_default)
  return _flm_vehicle_knob(_flm_profile_symbol(profile_key, f"{suffix}_right"), right_default)


def _flm_full_surface_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / IONIQ_6_TRANSITION_SPEED) ** 2)


def _flm_full_surface_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / IONIQ_6_PHASE_SCALE)


def _flm_full_surface_transition_envelope(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  lat_factor = 1.0 - math.exp(-abs(desired_lateral_accel) / IONIQ_6_FRICTION_LAT_RISE)
  jerk_factor = 1.0 - math.exp(-abs(desired_lateral_jerk) / IONIQ_6_FRICTION_JERK_RISE)
  return _flm_full_surface_low_speed_factor(v_ego) * lat_factor * jerk_factor


def _flm_full_surface_curvy_speed_weight(profile_key: str, v_ego: float) -> float:
  curvy_speed_min = _flm_vehicle_knob(_flm_profile_symbol(profile_key, "curvy_speed_min"), IONIQ_6_CURVY_SPEED_MIN)
  curvy_speed_max = _flm_vehicle_knob(_flm_profile_symbol(profile_key, "curvy_speed_max"), IONIQ_6_CURVY_SPEED_MAX)
  onset = _sigmoid((max(v_ego, 0.0) - curvy_speed_min) / IONIQ_6_CURVY_SPEED_MIN_WIDTH)
  cutoff = _sigmoid((curvy_speed_max - max(v_ego, 0.0)) / IONIQ_6_CURVY_SPEED_MAX_WIDTH)
  return onset * cutoff


def _flm_full_surface_curvy_turn_in_trim_speed_weight(profile_key: str, v_ego: float) -> float:
  curvy_turn_in_speed_min = _flm_vehicle_knob(_flm_profile_symbol(profile_key, "curvy_turn_in_trim_speed_min"), IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_MIN)
  curvy_turn_in_speed_max = _flm_vehicle_knob(_flm_profile_symbol(profile_key, "curvy_turn_in_trim_speed_max"), IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_MAX)
  onset = _sigmoid((max(v_ego, 0.0) - curvy_turn_in_speed_min) / IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_WIDTH)
  cutoff = _sigmoid((curvy_turn_in_speed_max - max(v_ego, 0.0)) / IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_WIDTH)
  return onset * cutoff


def get_flm_full_surface_center_taper_scale(profile_key: str | None, desired_lateral_accel: float, v_ego: float,
                                            include_base_center: bool = False) -> float:
  if not profile_key:
    return 1.0

  reduction = 0.0
  if include_base_center and flm_profile_supports_knob(profile_key, "center_taper_max"):
    speed_weight = _sigmoid((v_ego - IONIQ_6_CENTER_TAPER_SPEED) / IONIQ_6_CENTER_TAPER_SPEED_WIDTH)
    center_weight = _sigmoid((IONIQ_6_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / IONIQ_6_CENTER_TAPER_LAT_WIDTH)
    reduction += _flm_vehicle_knob(_flm_profile_symbol(profile_key, "center_taper_max"), 0.0) * speed_weight * center_weight

  if flm_profile_supports_knob(profile_key, "highway_center_taper_max"):
    speed_weight = _sigmoid((v_ego - IONIQ_6_HIGHWAY_CENTER_TAPER_SPEED) / IONIQ_6_HIGHWAY_CENTER_TAPER_SPEED_WIDTH)
    center_weight = _sigmoid((IONIQ_6_HIGHWAY_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / IONIQ_6_HIGHWAY_CENTER_TAPER_LAT_WIDTH)
    reduction += _flm_vehicle_knob(_flm_profile_symbol(profile_key, "highway_center_taper_max"), 0.0) * speed_weight * center_weight

  return 1.0 - min(reduction, 0.20)


def get_flm_full_surface_center_deadband_deg(profile_key: str | None, v_ego: float) -> float:
  if not profile_key:
    return 0.0

  suffixes = (
    "center_deadband_crawl_deg",
    "center_deadband_low_deg",
    "center_deadband_mid_deg",
    "center_deadband_fast_deg",
    "center_deadband_highway_deg",
  )
  values = [
    _flm_vehicle_knob(_flm_profile_symbol(profile_key, suffix), 0.0)
    for suffix in suffixes
  ]
  return float(np.interp(max(v_ego, 0.0), FLM_FRICTION_SPEED_KNOTS, values))


def get_flm_full_surface_ff_scale(profile_key: str | None, desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float,
                                  include_base_ff: bool = False) -> float:
  if not profile_key or desired_lateral_accel == 0.0:
    return 1.0

  abs_lateral_accel = abs(desired_lateral_accel)
  phase = _flm_full_surface_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  low_speed_factor = _flm_full_surface_low_speed_factor(v_ego)

  curvy_turn_in_speed_weight = _flm_full_surface_curvy_turn_in_trim_speed_weight(profile_key, v_ego)
  curvy_turn_in_lat_onset = _sigmoid((abs_lateral_accel - IONIQ_6_CURVY_TURN_IN_TRIM_LAT_START) / IONIQ_6_CURVY_TURN_IN_TRIM_LAT_ONSET_WIDTH)
  curvy_turn_in_lat_cutoff = _sigmoid((IONIQ_6_CURVY_TURN_IN_TRIM_LAT_END - abs_lateral_accel) / IONIQ_6_CURVY_TURN_IN_TRIM_LAT_CUTOFF_WIDTH)
  curvy_turn_in_trim_weight = curvy_turn_in_speed_weight * curvy_turn_in_lat_onset * curvy_turn_in_lat_cutoff * turn_in_weight

  curvy_unwind_speed_weight = _flm_full_surface_curvy_speed_weight(profile_key, v_ego)
  curvy_unwind_lat_onset = _sigmoid((abs_lateral_accel - IONIQ_6_CURVY_UNWIND_LAT_START) / IONIQ_6_CURVY_UNWIND_LAT_ONSET_WIDTH)
  curvy_unwind_lat_cutoff = _sigmoid((IONIQ_6_CURVY_UNWIND_LAT_END - abs_lateral_accel) / IONIQ_6_CURVY_UNWIND_LAT_CUTOFF_WIDTH)
  curvy_unwind_weight = curvy_unwind_speed_weight * curvy_unwind_lat_onset * curvy_unwind_lat_cutoff * unwind_weight

  scale = 1.0
  if include_base_ff and flm_profile_supports_knob(profile_key, "ff_gain_left"):
    gain = _flm_full_surface_side_value(profile_key, desired_lateral_accel, "ff_gain")
    onset = _sigmoid((abs_lateral_accel - IONIQ_6_FF_ONSET) / IONIQ_6_FF_ONSET_WIDTH)
    cutoff = _sigmoid((IONIQ_6_FF_CUTOFF - abs_lateral_accel) / IONIQ_6_FF_CUTOFF_WIDTH)
    extra_scale = gain * onset * cutoff
    turn_in_boost = 1.0 + (_flm_full_surface_side_value(profile_key, desired_lateral_accel, "turn_in_boost") * turn_in_weight * low_speed_factor)
    unwind_reduction = _flm_full_surface_side_value(profile_key, desired_lateral_accel, "unwind_taper") * unwind_weight * (0.30 + 0.70 * low_speed_factor)
    curvy_unwind_extra = _flm_full_surface_side_value(profile_key, desired_lateral_accel, "curvy_unwind_extra_reduction") * curvy_unwind_weight
    curvy_unwind_floor_relief = _flm_full_surface_side_value(profile_key, desired_lateral_accel, "curvy_unwind_floor_relief") * curvy_unwind_weight
    unwind_floor = 1.0 - (0.55 * unwind_reduction) - curvy_unwind_floor_relief
    unwind_scale = max(1.0 - unwind_reduction - curvy_unwind_extra, unwind_floor, 0.0)
    scale *= 1.0 + (extra_scale * turn_in_boost * unwind_scale)
  else:
    curvy_unwind_extra = _flm_full_surface_side_value(profile_key, desired_lateral_accel, "curvy_unwind_extra_reduction") * curvy_unwind_weight
    curvy_unwind_floor_relief = _flm_full_surface_side_value(profile_key, desired_lateral_accel, "curvy_unwind_floor_relief") * curvy_unwind_weight
    scale *= max(1.0 - curvy_unwind_extra - curvy_unwind_floor_relief, 0.55)

  if flm_profile_supports_knob(profile_key, "curvy_turn_in_trim_left"):
    curvy_trim = _flm_full_surface_side_value(profile_key, desired_lateral_accel, "curvy_turn_in_trim") * curvy_turn_in_trim_weight
    scale *= max(1.0 - curvy_trim, 0.55)

  if flm_profile_supports_knob(profile_key, "crawl_turn_in_ff_boost_left") and desired_lateral_accel * desired_lateral_jerk > 0.0:
    crawl_speed_weight = _sigmoid((IONIQ_6_CRAWL_TURN_IN_FF_SPEED - max(v_ego, 0.0)) / IONIQ_6_CRAWL_TURN_IN_FF_SPEED_WIDTH)
    crawl_lat_weight = _sigmoid((abs_lateral_accel - IONIQ_6_CRAWL_TURN_IN_FF_LAT) / IONIQ_6_CRAWL_TURN_IN_FF_LAT_WIDTH)
    scale += _flm_full_surface_side_value(profile_key, desired_lateral_accel, "crawl_turn_in_ff_boost") * crawl_speed_weight * crawl_lat_weight

  return scale


def get_flm_full_surface_friction_threshold(profile_key: str | None, base_threshold: float, v_ego: float,
                                            desired_lateral_accel: float = 0.0, desired_lateral_jerk: float = 0.0,
                                            include_base_threshold: bool = False) -> float:
  if not profile_key or not include_base_threshold:
    return base_threshold

  transition_envelope = _flm_full_surface_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _flm_full_surface_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  unwind_speed_weight = _sigmoid((v_ego - IONIQ_6_UNWIND_HIGH_SPEED_SPEED) / IONIQ_6_UNWIND_HIGH_SPEED_SPEED_WIDTH)
  threshold_scale = 1.0
  threshold_scale -= (_flm_full_surface_side_value(profile_key, desired_lateral_accel, "turn_in_threshold_reduction") *
                      transition_envelope * turn_in_weight)
  threshold_scale += (_flm_full_surface_side_value(profile_key, desired_lateral_accel, "unwind_threshold_increase") *
                      transition_envelope * unwind_weight * unwind_speed_weight)
  return base_threshold * min(max(threshold_scale, 0.82), 1.18)


def get_flm_full_surface_low_speed_angle_assist_torque(profile_key: str | None, desired_angle_deg: float, actual_angle_deg: float,
                                                       current_output_torque: float, v_ego: float) -> float:
  if not profile_key or not flm_profile_supports_knob(profile_key, "low_speed_angle_assist_max_torque"):
    return current_output_torque

  max_torque = _flm_vehicle_knob(_flm_profile_symbol(profile_key, "low_speed_angle_assist_max_torque"), 0.0)
  if max_torque <= 1e-4:
    return current_output_torque

  angle_error = desired_angle_deg - actual_angle_deg
  if desired_angle_deg * angle_error > 0.0:
    speed_weight = _sigmoid((IONIQ_6_LOW_SPEED_ANGLE_ASSIST_SPEED - max(v_ego, 0.0)) / IONIQ_6_LOW_SPEED_ANGLE_ASSIST_SPEED_WIDTH)
    error_weight = _sigmoid((abs(angle_error) - IONIQ_6_LOW_SPEED_ANGLE_ASSIST_ERROR) / IONIQ_6_LOW_SPEED_ANGLE_ASSIST_ERROR_WIDTH)
    desired_angle_weight = _sigmoid((abs(desired_angle_deg) - IONIQ_6_LOW_SPEED_ANGLE_ASSIST_DESIRED_ANGLE) / IONIQ_6_LOW_SPEED_ANGLE_ASSIST_DESIRED_ANGLE_WIDTH)
    tracking_ratio = abs(actual_angle_deg) / max(abs(desired_angle_deg), 1e-3)
    tracking_taper = _sigmoid((tracking_ratio - IONIQ_6_LOW_SPEED_ANGLE_ASSIST_TRACK_RATIO_START) / IONIQ_6_LOW_SPEED_ANGLE_ASSIST_TRACK_RATIO_WIDTH)
    tracking_scale = max(1.0 - tracking_taper, IONIQ_6_LOW_SPEED_ANGLE_ASSIST_TRACK_RATIO_FLOOR)
    assist_torque = math.copysign(max_torque * speed_weight * error_weight * desired_angle_weight * tracking_scale, -angle_error)
    if abs(assist_torque) < 1e-4:
      return current_output_torque
    if current_output_torque * assist_torque >= 0.0:
      add_scale = float(np.interp(abs(current_output_torque), IONIQ_6_LOW_SPEED_ANGLE_ASSIST_ADD_BP, IONIQ_6_LOW_SPEED_ANGLE_ASSIST_ADD_V))
      return float(np.clip(current_output_torque + (assist_torque * add_scale), -1.0, 1.0))
    return float(np.clip(current_output_torque + assist_torque, -1.0, 1.0))

  speed_weight = _sigmoid((IONIQ_6_LOW_SPEED_UNWIND_ASSIST_SPEED - max(v_ego, 0.0)) / IONIQ_6_LOW_SPEED_UNWIND_ASSIST_SPEED_WIDTH)
  error_weight = _sigmoid((abs(angle_error) - IONIQ_6_LOW_SPEED_UNWIND_ASSIST_ERROR) / IONIQ_6_LOW_SPEED_UNWIND_ASSIST_ERROR_WIDTH)
  actual_angle_weight = _sigmoid((abs(actual_angle_deg) - IONIQ_6_LOW_SPEED_UNWIND_ASSIST_ACTUAL_ANGLE) / IONIQ_6_LOW_SPEED_UNWIND_ASSIST_ACTUAL_ANGLE_WIDTH)
  assist_torque = math.copysign(IONIQ_6_LOW_SPEED_UNWIND_ASSIST_MAX_TORQUE * speed_weight * error_weight * actual_angle_weight, -angle_error)
  if abs(assist_torque) < 1e-4:
    return current_output_torque
  if current_output_torque * assist_torque >= 0.0:
    assist_torque *= IONIQ_6_LOW_SPEED_UNWIND_ASSIST_BLEND
  return float(np.clip(current_output_torque + assist_torque, -1.0, 1.0))


FLM_RICH_PROFILE_CARS = {
  "gm_bolt_2022_2023": set(BOLT_2022_2023_CARS),
  "hyundai_ioniq_6": set(IONIQ_6_CARS),
  "hyundai_kia_ev6": set(KIA_EV6_CARS),
  "toyota_prius": set(PRIUS_CARS),
  "toyota_camry": set(CAMRY_CARS),
}

FLM_RICH_PROFILE_LABELS = {
  "gm_bolt_2022_2023": "Bolt 2022-2023",
  "hyundai_ioniq_6": "Ioniq 6",
  "hyundai_kia_ev6": "EV6",
  "toyota_prius": "Prius",
  "toyota_camry": "Camry",
  FLM_UNIVERSAL_PROFILE_KEY: "Torque Controller",
}

FLM_SUPPORTED_VEHICLE_KNOBS = {
  "gm_bolt_2022_2023.ff_gain_left": {"profile": "gm_bolt_2022_2023", "min": 0.0, "max": 0.40, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": BOLT_2022_2023_FF_GAIN_LEFT},
  "gm_bolt_2022_2023.ff_gain_right": {"profile": "gm_bolt_2022_2023", "min": 0.0, "max": 0.40, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": BOLT_2022_2023_FF_GAIN_RIGHT},
  "gm_bolt_2022_2023.turn_in_boost_left": {"profile": "gm_bolt_2022_2023", "min": -0.10, "max": 0.50, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": BOLT_2022_2023_TURN_IN_BOOST_LEFT},
  "gm_bolt_2022_2023.turn_in_boost_right": {"profile": "gm_bolt_2022_2023", "min": -0.10, "max": 0.50, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": BOLT_2022_2023_TURN_IN_BOOST_RIGHT},
  "gm_bolt_2022_2023.unwind_taper_left": {"profile": "gm_bolt_2022_2023", "min": 0.0, "max": 0.80, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": BOLT_2022_2023_UNWIND_TAPER_LEFT},
  "gm_bolt_2022_2023.unwind_taper_right": {"profile": "gm_bolt_2022_2023", "min": 0.0, "max": 0.80, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": BOLT_2022_2023_UNWIND_TAPER_RIGHT},
  "gm_bolt_2022_2023.center_taper_max": {"profile": "gm_bolt_2022_2023", "min": 0.0, "max": 0.25, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": BOLT_2022_2023_CENTER_TAPER_MAX},
  "gm_bolt_2022_2023.turn_in_threshold_reduction_left": {"profile": "gm_bolt_2022_2023", "min": 0.0, "max": 0.40, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": BOLT_2022_2023_TURN_IN_THRESHOLD_REDUCTION_LEFT},
  "gm_bolt_2022_2023.turn_in_threshold_reduction_right": {"profile": "gm_bolt_2022_2023", "min": 0.0, "max": 0.40, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": BOLT_2022_2023_TURN_IN_THRESHOLD_REDUCTION_RIGHT},
  "gm_bolt_2022_2023.unwind_threshold_increase_left": {"profile": "gm_bolt_2022_2023", "min": 0.0, "max": 0.60, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": BOLT_2022_2023_UNWIND_THRESHOLD_INCREASE_LEFT},
  "gm_bolt_2022_2023.unwind_threshold_increase_right": {"profile": "gm_bolt_2022_2023", "min": 0.0, "max": 0.60, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": BOLT_2022_2023_UNWIND_THRESHOLD_INCREASE_RIGHT},
  "hyundai_ioniq_6.ff_gain_left": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 0.60, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_FF_GAIN_LEFT},
  "hyundai_ioniq_6.ff_gain_right": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 0.60, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_FF_GAIN_RIGHT},
  "hyundai_ioniq_6.turn_in_boost_left": {"profile": "hyundai_ioniq_6", "min": 0.40, "max": 2.80, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_TURN_IN_BOOST_LEFT},
  "hyundai_ioniq_6.turn_in_boost_right": {"profile": "hyundai_ioniq_6", "min": 0.40, "max": 2.80, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_TURN_IN_BOOST_RIGHT},
  "hyundai_ioniq_6.unwind_taper_left": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 12.0, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_UNWIND_TAPER_LEFT},
  "hyundai_ioniq_6.unwind_taper_right": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 12.0, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_UNWIND_TAPER_RIGHT},
  "hyundai_ioniq_6.center_taper_max": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 0.18, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_CENTER_TAPER_MAX},
  "hyundai_ioniq_6.highway_center_taper_max": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 0.18, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_HIGHWAY_CENTER_TAPER_MAX},
  "hyundai_ioniq_6.turn_in_threshold_reduction_left": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 2.00, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_TURN_IN_THRESHOLD_REDUCTION_LEFT},
  "hyundai_ioniq_6.turn_in_threshold_reduction_right": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 2.00, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_TURN_IN_THRESHOLD_REDUCTION_RIGHT},
  "hyundai_ioniq_6.unwind_threshold_increase_left": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 12.0, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_UNWIND_THRESHOLD_INCREASE_LEFT},
  "hyundai_ioniq_6.unwind_threshold_increase_right": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 12.0, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_UNWIND_THRESHOLD_INCREASE_RIGHT},
  "hyundai_ioniq_6.crawl_turn_in_ff_boost_left": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 0.50, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_CRAWL_TURN_IN_FF_BOOST_LEFT},
  "hyundai_ioniq_6.crawl_turn_in_ff_boost_right": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 0.50, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_CRAWL_TURN_IN_FF_BOOST_RIGHT},
  "hyundai_ioniq_6.low_speed_angle_assist_max_torque": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 0.80, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_LOW_SPEED_ANGLE_ASSIST_MAX_TORQUE},
  "hyundai_ioniq_6.curvy_speed_min": {"profile": "hyundai_ioniq_6", "min": 4.0, "max": 12.0, "precision": 0.1, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_CURVY_SPEED_MIN},
  "hyundai_ioniq_6.curvy_speed_max": {"profile": "hyundai_ioniq_6", "min": 14.0, "max": 25.0, "precision": 0.1, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_CURVY_SPEED_MAX},
  "hyundai_ioniq_6.curvy_turn_in_trim_speed_min": {"profile": "hyundai_ioniq_6", "min": 8.0, "max": 16.0, "precision": 0.1, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_MIN},
  "hyundai_ioniq_6.curvy_turn_in_trim_speed_max": {"profile": "hyundai_ioniq_6", "min": 14.0, "max": 25.0, "precision": 0.1, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_MAX},
  "hyundai_ioniq_6.curvy_turn_in_trim_left": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 0.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_CURVY_TURN_IN_TRIM_LEFT},
  "hyundai_ioniq_6.curvy_turn_in_trim_right": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 0.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_CURVY_TURN_IN_TRIM_RIGHT},
  "hyundai_ioniq_6.curvy_unwind_floor_relief_left": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 0.45, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_CURVY_UNWIND_FLOOR_RELIEF_LEFT},
  "hyundai_ioniq_6.curvy_unwind_floor_relief_right": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 0.45, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_CURVY_UNWIND_FLOOR_RELIEF_RIGHT},
  "hyundai_ioniq_6.curvy_unwind_extra_reduction_left": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 0.45, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_CURVY_UNWIND_EXTRA_REDUCTION_LEFT},
  "hyundai_ioniq_6.curvy_unwind_extra_reduction_right": {"profile": "hyundai_ioniq_6", "min": 0.0, "max": 0.45, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": IONIQ_6_CURVY_UNWIND_EXTRA_REDUCTION_RIGHT},
  "hyundai_kia_ev6.ff_gain_left": {"profile": "hyundai_kia_ev6", "min": 0.0, "max": 0.60, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": KIA_EV6_FF_GAIN_LEFT},
  "hyundai_kia_ev6.ff_gain_right": {"profile": "hyundai_kia_ev6", "min": 0.0, "max": 0.60, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": KIA_EV6_FF_GAIN_RIGHT},
  "hyundai_kia_ev6.turn_in_boost_left": {"profile": "hyundai_kia_ev6", "min": 0.0, "max": 1.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": KIA_EV6_TURN_IN_BOOST_LEFT},
  "hyundai_kia_ev6.turn_in_boost_right": {"profile": "hyundai_kia_ev6", "min": 0.0, "max": 1.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": KIA_EV6_TURN_IN_BOOST_RIGHT},
  "hyundai_kia_ev6.unwind_taper_left": {"profile": "hyundai_kia_ev6", "min": 0.0, "max": 1.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": KIA_EV6_UNWIND_TAPER_LEFT},
  "hyundai_kia_ev6.unwind_taper_right": {"profile": "hyundai_kia_ev6", "min": 0.0, "max": 1.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": KIA_EV6_UNWIND_TAPER_RIGHT},
  "hyundai_kia_ev6.base_unwind_taper_left": {"profile": "hyundai_kia_ev6", "min": 0.0, "max": 0.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": KIA_EV6_BASE_UNWIND_TAPER_LEFT},
  "hyundai_kia_ev6.base_unwind_taper_right": {"profile": "hyundai_kia_ev6", "min": 0.0, "max": 0.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": KIA_EV6_BASE_UNWIND_TAPER_RIGHT},
  "hyundai_kia_ev6.center_taper_max": {"profile": "hyundai_kia_ev6", "min": 0.0, "max": 0.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": KIA_EV6_CENTER_TAPER_MAX},
  "hyundai_kia_ev6.turn_in_threshold_reduction_left": {"profile": "hyundai_kia_ev6", "min": 0.0, "max": 0.40, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": KIA_EV6_TURN_IN_THRESHOLD_REDUCTION_LEFT},
  "hyundai_kia_ev6.turn_in_threshold_reduction_right": {"profile": "hyundai_kia_ev6", "min": 0.0, "max": 0.40, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": KIA_EV6_TURN_IN_THRESHOLD_REDUCTION_RIGHT},
  "hyundai_kia_ev6.unwind_threshold_increase_left": {"profile": "hyundai_kia_ev6", "min": 0.0, "max": 0.80, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": KIA_EV6_UNWIND_THRESHOLD_INCREASE_LEFT},
  "hyundai_kia_ev6.unwind_threshold_increase_right": {"profile": "hyundai_kia_ev6", "min": 0.0, "max": 0.80, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": KIA_EV6_UNWIND_THRESHOLD_INCREASE_RIGHT},
  "hyundai_kia_ev6.center_friction_threshold_gain": {"profile": "hyundai_kia_ev6", "min": 0.0, "max": 0.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": KIA_EV6_CENTER_FRICTION_THRESHOLD_GAIN},
  "hyundai_kia_ev6.center_output_taper_max": {"profile": "hyundai_kia_ev6", "min": 0.0, "max": 0.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": KIA_EV6_CENTER_OUTPUT_TAPER_MAX},
  "toyota_prius.ff_gain_left": {"profile": "toyota_prius", "min": 0.0, "max": 0.25, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": PRIUS_FF_GAIN_LEFT},
  "toyota_prius.ff_gain_right": {"profile": "toyota_prius", "min": 0.0, "max": 0.25, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": PRIUS_FF_GAIN_RIGHT},
  "toyota_prius.turn_in_boost_left": {"profile": "toyota_prius", "min": -0.10, "max": 0.60, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": PRIUS_TURN_IN_BOOST_LEFT},
  "toyota_prius.turn_in_boost_right": {"profile": "toyota_prius", "min": -0.10, "max": 0.60, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": PRIUS_TURN_IN_BOOST_RIGHT},
  "toyota_prius.unwind_taper_left": {"profile": "toyota_prius", "min": 0.0, "max": 1.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": PRIUS_UNWIND_TAPER_LEFT},
  "toyota_prius.unwind_taper_right": {"profile": "toyota_prius", "min": 0.0, "max": 1.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": PRIUS_UNWIND_TAPER_RIGHT},
  "toyota_prius.center_taper_max": {"profile": "toyota_prius", "min": 0.0, "max": 0.25, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": PRIUS_CENTER_TAPER_MAX},
  "toyota_prius.turn_in_threshold_reduction_left": {"profile": "toyota_prius", "min": 0.0, "max": 0.50, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": PRIUS_TURN_IN_THRESHOLD_REDUCTION_LEFT},
  "toyota_prius.turn_in_threshold_reduction_right": {"profile": "toyota_prius", "min": 0.0, "max": 0.50, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": PRIUS_TURN_IN_THRESHOLD_REDUCTION_RIGHT},
  "toyota_prius.unwind_threshold_increase_left": {"profile": "toyota_prius", "min": 0.0, "max": 0.90, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": PRIUS_UNWIND_THRESHOLD_INCREASE_LEFT},
  "toyota_prius.unwind_threshold_increase_right": {"profile": "toyota_prius", "min": 0.0, "max": 0.90, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": PRIUS_UNWIND_THRESHOLD_INCREASE_RIGHT},
  "toyota_prius.center_friction_threshold_gain": {"profile": "toyota_prius", "min": 0.0, "max": 0.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": PRIUS_CENTER_FRICTION_THRESHOLD_GAIN},
  "toyota_camry.center_friction_threshold_gain": {"profile": "toyota_camry", "min": 0.0, "max": 0.15, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": CAMRY_CENTER_FRICTION_THRESHOLD_GAIN},
  "toyota_camry.unwind_ff_reduction": {"profile": "toyota_camry", "min": 0.0, "max": 0.20, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True, "defaultValue": CAMRY_UNWIND_FF_REDUCTION},
}


def _add_flm_full_surface_profile_knobs(profile_key: str, defaults: dict[str, float] | None = None) -> None:
  knob_defaults = dict(FLM_FULL_SURFACE_NEUTRAL_DEFAULTS)
  if defaults:
    knob_defaults.update(defaults)

  for suffix, meta in FLM_FULL_SURFACE_SUFFIX_METADATA.items():
    symbol = _flm_profile_symbol(profile_key, suffix)
    if symbol in FLM_SUPPORTED_VEHICLE_KNOBS:
      continue
    minimum = -0.40 if profile_key == FLM_UNIVERSAL_PROFILE_KEY and suffix in ("ff_gain_left", "ff_gain_right") else meta["min"]
    FLM_SUPPORTED_VEHICLE_KNOBS[symbol] = {
      "profile": profile_key,
      "min": minimum,
      "max": meta["max"],
      "precision": meta["precision"],
      "deltaType": meta["deltaType"],
      "safeLiveTrial": meta["safeLiveTrial"],
      "defaultValue": knob_defaults[suffix],
    }


for _flm_profile_key in ("gm_bolt_2022_2023", "hyundai_ioniq_6", "hyundai_kia_ev6", "toyota_prius", "toyota_camry", FLM_UNIVERSAL_PROFILE_KEY):
  _add_flm_full_surface_profile_knobs(_flm_profile_key)


def get_flm_supported_vehicle_knobs() -> dict:
  return _flm_copy_json(FLM_SUPPORTED_VEHICLE_KNOBS)


def get_flm_rich_profile_key(car_fingerprint) -> str | None:
  for profile_key, cars in FLM_RICH_PROFILE_CARS.items():
    if car_fingerprint in cars:
      return profile_key
  return None


def get_flm_surface_profile_key(car_fingerprint, torque_control: bool = True) -> str | None:
  profile_key = get_flm_rich_profile_key(car_fingerprint)
  if profile_key is not None or not torque_control:
    return profile_key
  return FLM_UNIVERSAL_PROFILE_KEY


def get_flm_capabilities(car_fingerprint, brand: str = "", hyundai_canfd: bool = False, torque_control: bool = True) -> dict:
  profile_key = get_flm_surface_profile_key(car_fingerprint, torque_control=torque_control)
  if hyundai_canfd:
    friction_family = "hkg_canfd"
  elif brand == "gm":
    friction_family = "gm"
  else:
    friction_family = "standard"

  dedicated_friction = car_fingerprint in (
    set(BOLT_2022_2023_CARS) | set(BOLT_2018_2021_CARS) | set(VOLT_STANDARD_CARS) | set(PALISADE_CARS) |
    set(PRIUS_CARS) | set(RAV4_PRIME_CARS) | set(SIENNA_4TH_GEN_CARS) | set(IONIQ_5_CARS) | set(IONIQ_6_CARS) | set(KIA_EV6_CARS) | set(KIA_FORTE_CARS) |
    set(KIA_NIRO_PHEV_2022_CARS) | set(KIA_CARNIVAL_CARS) | set(GENESIS_G90_CARS) | set(GENESIS_G70_CARS) | set(CAMRY_CARS)
  )
  dedicated_center_taper = car_fingerprint in (
    set(PRIUS_CARS) | set(SIENNA_4TH_GEN_CARS) | set(BOLT_CARS) | set(VOLT_STANDARD_CARS) | set(IONIQ_5_CARS) |
    set(IONIQ_EV_OLD_CARS) | set(IONIQ_6_CARS) | set(SONATA_CARS) | set(SONATA_HYBRID_CARS) |
    set(KIA_XCEED_CARS) | set(KIA_NIRO_PHEV_2022_CARS) | set(KIA_FORTE_CARS) | set(KIA_EV6_CARS) |
    set(KIA_CARNIVAL_CARS) | set(TUCSON_4TH_GEN_CARS) | set(GENESIS_G70_CARS) | set(SILVERADO_CARS)
  )
  rich_knobs = [name for name, meta in FLM_SUPPORTED_VEHICLE_KNOBS.items() if meta["profile"] == profile_key]
  return {
    "torqueControl": bool(torque_control),
    "frictionFamily": friction_family,
    "hasDedicatedFrictionThreshold": bool(dedicated_friction),
    "hasDedicatedCenterTaper": bool(dedicated_center_taper),
    "richProfileKey": profile_key,
    "richProfileLabel": FLM_RICH_PROFILE_LABELS.get(profile_key),
    "richKnobs": rich_knobs,
  }


__all__ = [name for name in globals() if not name.startswith("_") and name not in {
  "math", "np", "GM_CAR", "HYUNDAI_CAR", "TOYOTA_CAR", "CV", "testing_ground",
}]
