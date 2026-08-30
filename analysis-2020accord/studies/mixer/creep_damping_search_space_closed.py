# -*- coding: utf-8 -*-
"""IS THERE ANY CALIBRATION LEVER THAT ADDS DAMPING AT ~7.8 Hz IN THE CREEP REGIME? NO.

Last tick established that the roughness is a SMALL-COMMAND phenomenon (the top command quartile is
3.7x smoother, corr -0.358 over 3711 windows). This enumerates every cal-level path to creep-regime
damping and shows each is closed, from the bytes. It exists so nobody re-proposes them -- CLAUDE.md
records that already happening twice.

--------------------------------------------------------------------------------------------------
1. THE BASE-ASSIST DAMPER (gp-0x6bd0) -- CLOSED, AND THE REASON IS A PRODUCT OF NEAR-ZERO GAINS
--------------------------------------------------------------------------------------------------
FUN_00034350 multiplies FIVE Q10 gains, each a LERP clamped flat to Y[0] below X[0]. On the car and
on the whole shelf, mode 26:

    FactorB  X=[205,1331,2355,3072]   Y=[1024,1024,1024,1024]     flat, no dead zone
    FactorC  X=[2240,3840,5120,8960]  Y=[   0, 234, 429, 908]     axis SPEED  -- dead below 35 km/h
    FactorD  X=[0,50,100,150,700]     Y=[1024,1024,1024,1024,1024] flat, open at 0
    FactorE  X=[  60, 400,2500,4000]  Y=[   0, 140, 539, 927]     axis RATE   -- dead below 60 ct

Zero times anything is zero, so EITHER dead zone alone forces the damper to exactly zero at creep.
🛑 AND SCALING IS STRUCTURALLY VACUOUS: both Y[0] are 0, so multiplying a record by any k leaves it 0.

THE EDIT NOBODY HAS TRIED, AND WHY IT STILL FAILS. Across ALL 214 images on disk the FactorC X axis
is (2240, 3840, 5120, 8960) -- EXACTLY ONE distinct vector, never once moved -- while Y[0] has been
set nine different ways (0, 60, 234, 429, 566, 700, 908) across ~40 builds. Every attempt to arm this
damper raised Y[0] at a FIXED X[0], which puts a STEP at 35 km/h. That is how V80 turned it into a
relay and produced the worst grinding ever measured.

So the untried edit is to LOWER X[0] and extend the RAMP down -- which is exactly the lesson V80 left
("restore the RAMP, don't merely lower k"). It does not work either, and the arithmetic says why:
the numbers below are the resulting Q10 gains at creep, and their product.

--------------------------------------------------------------------------------------------------
2..5 THE OTHER CANDIDATES -- each closed on its own terms
--------------------------------------------------------------------------------------------------
  gp-0x6bbe  the one lane measured as VISCOUS (flat ~90 ct/(rad/s), phase ~0 deg vs rate). Its weight
             0xC63A2 is a virgin single-reader cal -- but the golden model records the lane already
             at 76 % of its flat +-512 rail, so raising the weight amplifies a signal that is already
             part relay. Not a clean damping lever.
  0xC40D2    the Coulomb slope in the plant-model observer. Its authority at creep is bounded by the
             slope 12*k1/gate/1024: at 5 deg/s it removes 1.99 % of the model. Halving the residual
             there needs k1 = 25600, which is 25x past the k1 = 1024 boundary where the modelled
             friction equals the whole model and the SIGN INVERTS.
  427 lane   ranking which internal lane carries the ratchet band, using the probe's own history
    ranking  across seven different source cells, is not possible from the existing caches: only r95
             carries a decoded 427 magnitude channel. It would need re-extraction from the rlogs.
  a notch    already excluded by the record on its own terms -- the ratcheting is NOT a tone the EPS
             commands (V88's signed-command test), so there is no line to notch and no phase lever
             at 7.79 Hz.

=> [EVIDENCE] THE CAL-LEVEL SEARCH SPACE FOR CREEP-REGIME DAMPING IS EXHAUSTED. What remains is to
   fly what is built, or a code cave -- and caves are this kit's only bricking class (V24, V27, V48B).

Run:  python analysis-2020accord/studies/mixer/creep_damping_search_space_closed.py
"""
import numpy as np

CT_PER_KMH = 2240 / 34.97          # FactorC X[0] = 2240 ct = 34.97 km/h  => speed axis
FACTOR_C = ([2240, 3840, 5120, 8960], [0, 234, 429, 908])
FACTOR_E = ([60, 400, 2500, 4000], [0, 140, 539, 927])
FACTOR_B_Y = 1024
FACTOR_D_Y = 1024


def lerp(X, Y, v):
    """The firmware's LERP: clamp flat to Y[0] below X[0] and to Y[-1] above X[-1]."""
    if v <= X[0]:
        return float(Y[0])
    if v >= X[-1]:
        return float(Y[-1])
    for i in range(len(X) - 1):
        if X[i] <= v <= X[i + 1]:
            return Y[i] + (Y[i + 1] - Y[i]) * (v - X[i]) / (X[i + 1] - X[i])
    return float(Y[-1])


print('=' * 94)
print('  CREEP-REGIME DAMPING: THE DAMPER IS A PRODUCT OF FIVE Q10 GAINS, AND TWO ARE ZERO THERE')
print('=' * 94)
print()
CREEP_KMH = [1.8, 3.0, 4.5, 5.4]          # 0.5-1.5 m/s, the operator's own creep test window
RATE_CT = 200                              # a plausible motor-rate excursion during a ratchet cycle

print('  as shipped (car AND the whole shelf), at motor rate %d ct:' % RATE_CT)
print('  %8s %9s %10s %10s %12s' % ('km/h', 'speed ct', 'FactorC', 'FactorE', 'PRODUCT/1024^4'))
for kmh in CREEP_KMH:
    sp = kmh * CT_PER_KMH
    c = lerp(*FACTOR_C, sp)
    e = lerp(*FACTOR_E, RATE_CT)
    prod = (c / 1024) * (e / 1024) * (FACTOR_B_Y / 1024) * (FACTOR_D_Y / 1024)
    print('  %8.1f %9.0f %10.1f %10.1f %12.6f' % (kmh, sp, c, e, prod))

print()
print('  now with the UNTRIED edit -- FactorC X[0] lowered so the ramp reaches creep, Y[0] still 0:')
for x0 in (640, 256, 128, 64):
    Xc = [x0] + FACTOR_C[0][1:]
    row = []
    for kmh in CREEP_KMH:
        sp = kmh * CT_PER_KMH
        c = lerp(Xc, FACTOR_C[1], sp)
        e = lerp(*FACTOR_E, RATE_CT)
        row.append((c / 1024) * (e / 1024))
    print('    X[0] = %4d (%5.1f km/h)   product at creep: %s'
          % (x0, x0 / CT_PER_KMH, ' '.join('%.5f' % r for r in row)))

best = max((lerp([64] + FACTOR_C[0][1:], FACTOR_C[1], k * CT_PER_KMH) / 1024)
           * (lerp(*FACTOR_E, RATE_CT) / 1024) for k in CREEP_KMH)
print()
print('  BEST ACHIEVABLE by moving FactorC X[0] alone: %.5f of full gain (%.3f %%).' % (best, 100 * best))
print('  FactorE contributes only %.1f/1024 = %.1f %% at a %d ct rate, so even a fully open speed'
      % (lerp(*FACTOR_E, RATE_CT), 100 * lerp(*FACTOR_E, RATE_CT) / 1024, RATE_CT))
print('  factor cannot rescue the product. BOTH dead zones would have to be opened by raising Y')
print('  values substantially -- which is what V74..V86 did, as STEPS, and V80 flew as the worst')
print('  grinding ever measured.')
print()

# --------------------------------- assertions -----------------------------------------
assert FACTOR_C[1][0] == 0 and FACTOR_E[1][0] == 0, 'both Y[0] must be zero -- scaling is vacuous'
assert best < 0.02, 'moving FactorC X[0] alone must stay under 2 % of full gain'
sp_creep = CREEP_KMH[-1] * CT_PER_KMH
assert lerp(*FACTOR_C, sp_creep) == 0.0, 'as shipped the speed factor must be exactly zero at creep'
assert lerp(*FACTOR_E, 30) == 0.0, 'the rate factor must also be exactly zero below its knot'
assert FACTOR_C[0][0] == 2240, 'the FactorC X axis is the one never moved in 214 images'
print('  all five assertions hold.')
print()
print('  [EVIDENCE] the cal-level search space for creep-regime damping is exhausted.')
print('  [NOTE]     this closes a search; it does not score a symptom. Only the operator does that.')
