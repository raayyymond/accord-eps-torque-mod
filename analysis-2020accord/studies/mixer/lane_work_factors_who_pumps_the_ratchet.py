# -*- coding: utf-8 -*-
"""WHICH AGGREGATOR LANE PUMPS THE RATCHET? Work factors from known transfers + measured input phase.

The r24 reconstruction validated a method: every aggregator lane is a KNOWN transfer acting on a
signal that is on the wire, so each lane's phase against RATE -- and therefore whether it adds or
removes energy at 6-9 Hz -- is computable without ever observing the lane itself.

    work factor = cos(phase of the lane's OUTPUT relative to RATE)
        +1  pure PUMP   (reinforces motion, an energy SOURCE)
        -1  pure DAMP   (opposes motion)
         0  quadrature  (stiffness/inertia-like, no net work)

This matters because the net is already known to be wrong: Re(Z) < 0 is replicated on three drives,
strongest in the micro regime. Something supplies that energy. r24 does not -- it measured -0.805,
i.e. damping. So the source is another lane, and this file ranks the candidates.

MEASURED INPUT PHASES (engaged, 6-9 Hz, 6 routes / 5 builds), with two controls that pass:
    rate vs itself      +0.0 deg     trivial control
    angle vs rate      -79.2 deg     physical control: an integrator of rate must be near -90
    TORQUE vs rate    -120.7 deg     the load-bearing number

THE FIXED TRANSFERS, from the cals:
    r24 / r26   -(cal/1024) * (1 - exp(-j*w*0.004))          arg = +84.4 deg, then +180 for gp-0x6752
    gp-0x6ad4   0.25 + 2*(jw) + (0.0957/(jw))/32, then *-1   the P/I/D combine, polarity applied after
    gp-0x6b46   alpha/(1-(1-alpha)*exp(-jw)), alpha=6/1024   arg = -81.8 deg at 7.79 Hz

WHAT IS SOLID AND WHAT IS NOT. The TRANSFERS are read from cals and are solid. The POLARITY with
which each lane enters the aggregator is documented only for r24/r26 and the PID (all three carry
gp-0x6752). For the rest the sign is not established here, so this file reports BOTH signs and says
which conclusion needs which. A lane is only called a pump when its polarity is documented.

Run:  python analysis-2020accord/studies/mixer/lane_work_factors_who_pumps_the_ratchet.py
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

F = 7.79
W = 2 * np.pi * F
PHI_T = -120.7                 # measured: torque relative to rate
PHI_A = -79.2                  # measured: angle relative to rate
DEG = u'\N{DEGREE SIGN}'
POL = 180.0                    # gp-0x6752 = -1, three-way verified


def wrap(a):
    return ((a + 180.0) % 360.0) - 180.0


def arg_deg(z):
    return float(np.degrees(np.angle(z)))


# ------------------------------- the transfers ------------------------------------------
H_DIFF = 1.0 - np.exp(-1j * W * 4e-3)                       # span-4 at 1 kHz
ALPHA = 6.0 / 1024.0
H_EMA = ALPHA / (1.0 - (1.0 - ALPHA) * np.exp(-1j * W / 1000.0))
KP, KI, KD, KOUT = 256.0, 98.0, 2048.0, 1024.0
P = (KP / 1024.0) * (KOUT / 1024.0)
D = (KD / 1024.0) * (KOUT / 1024.0) * (W / 1000.0)          # per-sample derivative at 1 kHz
I = ((KI / 1024.0) / (W / 1000.0)) / 32.0
H_PID = complex(P, D - I)

LANES = [
    # name,                input phase,  transfer arg,        polarity known?, note
    ('r24  (Lever B)',      PHI_T, arg_deg(H_DIFF) + POL, True,
     'span-4 diff, x gp-0x6752'),
    ('r26',                 PHI_T, arg_deg(H_DIFF) + POL, True,
     'same dtorque, odd parity too'),
    ('gp-0x6ad4 (res PID)', PHI_T, arg_deg(H_PID) + POL, True,
     'P+I+D then x gp-0x6752  <-- V227 raises THIS lane'),
    ('gp-0x6b46 (bias trk)', PHI_T, arg_deg(H_EMA), False,
     'first-order follower, alpha 6/1024'),
    ('gp-0x6bbe (viscous)',  0.0, 0.0, False,
     'rate-derived, phase ~0 vs rate'),
]

print('=' * 100)
print('  LANE WORK FACTORS AT %.2f Hz  --  who ADDS energy to the ratchet?' % F)
print('=' * 100)
print()
print('  measured inputs:  torque %+.1f%s vs rate   |   angle %+.1f%s (control, ideal -90)'
      % (PHI_T, DEG, PHI_A, DEG))
print('  fixed transfers:  diff %+.1f%s   PID %+.1f%s (|H| %.4f)   EMA %+.1f%s (|H| %.4f)'
      % (arg_deg(H_DIFF), DEG, arg_deg(H_PID), DEG, abs(H_PID),
         arg_deg(H_EMA), DEG, abs(H_EMA)))
print()
print('  %-22s %10s %11s %10s %9s   %s'
      % ('lane', 'in phase', 'out phase', 'work', 'polarity', 'verdict'))

rows = []
for name, pin, targ, known, note in LANES:
    out = wrap(pin + targ)
    w = float(np.cos(np.radians(out)))
    rows.append((name, out, w, known, note))
    if known:
        v = ('PUMPS' if w > 0.2 else 'DAMPS' if w < -0.2 else 'quadrature')
    else:
        v = 'sign UNKNOWN (|w| %.2f)' % abs(w)
    print('  %-22s %+9.1f%s %+10.1f%s %+9.3f %9s   %s'
          % (name, pin, DEG, out, DEG, w, 'known' if known else 'OPEN', v))

print()
for name, out, w, known, note in rows:
    print('    %-22s %s' % (name, note))

# ------------------------------- the finding --------------------------------------------
pid = [r for r in rows if 'res PID' in r[0]][0]
r24 = [r for r in rows if 'Lever B' in r[0]][0]
print()
print('  ' + '-' * 96)
print('  THE SPLIT: two lanes carry the SAME documented polarity and land on OPPOSITE sides.')
print('  ' + '-' * 96)
print('    r24        work %+.3f  -> removes energy' % r24[2])
print('    gp-0x6ad4  work %+.3f  -> ADDS energy' % pid[2])
print()
print('  Both multiply gp-0x6752, so this is NOT a polarity artefact between them: the difference is')
print('  the TRANSFER. The span-4 difference contributes +84.4%s of lead; the PID contributes only' % DEG)
print('  %+.1f%s because D and I are antiphase and nearly cancel, leaving it almost pure P.' % (arg_deg(H_PID), DEG))
print('  With torque already at %.1f%s, +84%s of lead reaches the anti-rate axis and %+.1f%s does not.'
      % (PHI_T, DEG, DEG, arg_deg(H_PID), DEG))

# ------------------------------- sensitivity --------------------------------------------
print()
print('  HOW ROBUST IS THE PID VERDICT? Its input is a torque RESIDUAL, not raw torque, so the input')
print('  phase carries real uncertainty. The sign flips where the output crosses +-90 deg:')
lo = wrap(90.0 - (arg_deg(H_PID) + POL))
hi = wrap(-90.0 - (arg_deg(H_PID) + POL))
print('    the lane PUMPS for input phase in the arc between %+.1f%s and %+.1f%s' % (hi, DEG, lo, DEG))
print('    measured torque sits at %+.1f%s, which is %.0f%s inside that arc.'
      % (PHI_T, DEG, abs(wrap(PHI_T - hi)), DEG))
margin = min(abs(wrap(PHI_T - lo)), abs(wrap(PHI_T - hi)))
print('    nearest sign-flip boundary is %.0f%s away.' % (margin, DEG))

assert r24[2] < -0.5, 'r24 must reproduce the damping result from the reconstruction'
assert pid[2] > 0.2, 'the PID lane must come out positive, or this file has no finding'
assert margin > 20, 'a verdict with <20 deg of margin is not reportable'
print()
print()
print('  ' + '=' * 96)
print('  RE-ANCHORED SO NO SIGN CONVENTION IS USED ANYWHERE')
print('  ' + '=' * 96)
print('  The kit records that its canonical Re(Z) tool maps T=+rate -> +1.0, which is the')
print('  OPPOSITE convention to the work factor above, and that reading one against the other')
print('  produced the wrong answer TWICE. So the absolute labels are NOT relied on here.')
print()
print('  What survives any global sign flip is the SEPARATION:')
print('     r24        %+.1f deg vs rate' % r24[1])
print('     gp-0x6ad4  %+.1f deg vs rate' % pid[1])
print('     separation %.1f deg -- they sit on OPPOSITE sides of the rate axis.' % abs(wrap(r24[1]-pid[1])))
print()
print('  And the GOOD side is fixed by an ON-CAR MEASUREMENT, not by a convention:')
print('     V88 raised r24 (512 -> 5244) and measured 6-9 Hz at 0.859x. r24 is beneficial.')
print('  => gp-0x6ad4, on the opposite side, is the HARMFUL side.')
print('  => CUTTING gp-0x6ad4 is predicted to help the ratchet, by the same argument that made')
print('     RAISING r24 help. No sign convention enters this chain at any point.')
print()
assert abs(wrap(r24[1] - pid[1])) > 45, 'the separation must be large or the argument is weak'
assert np.cos(np.radians(r24[1])) * np.cos(np.radians(pid[1])) < 0, \
    'the two lanes must fall on OPPOSITE sides of the rate axis -- that IS the finding'
print('  both separation assertions hold.')
print()
print('  [EVIDENCE] gp-0x6ad4 is the ONLY documented-polarity lane with a POSITIVE work factor at the')
print('             ratchet. It is a candidate ENERGY SOURCE, and margin to a sign flip is %.0f%s.'
      % (margin, DEG))
print('  \U0001f6d1 [CONSEQUENCE FOR V227] V227 RAISES this lane\'s authority (0xC67C4 1280->512, so the')
print('             ceiling reaches full at 8 km/h instead of 20). If this is right, V227 pushes the')
print('             ratchet the WRONG WAY at low speed -- exactly the creep regime it targets.')
print('             The opposite move -- CUTTING this lane -- becomes the candidate lever.')
print('  [LIMIT]    open-loop, and the PID input is a residual whose phase is assumed to track raw')
print('             torque. That assumption is what the margin above is quoted against.')
print('  [LIMIT]    the record classifies this lane as "net PID DAMPS at 6-9 Hz". That classification')
print('             is not reproduced here; see the handoff for the adjudication.')
