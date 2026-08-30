# -*- coding: utf-8 -*-
"""V227 IS UNLIKELY TO BE INERT -- it binds through the INTEGRATOR, not the output clamp.

V227 raises `iVar10`, which does two jobs: the symmetric output clamp on gp-0x6ad4, and the
anti-windup window on the integrator (iVar10*32 -+ P). Either only matters where it BINDS, so "no
change at all" was listed as a real third outcome. This prices both, from the cals.

THE PID, read from V222 with the layouts the decompile actually walks:

    Kp   on motor rate   X=[0,300,2000,4000]   Y=[256,256,225,153]
    Ki   on motor rate   X=[0,400,1500,3000]   Y=[ 98, 98, 98, 98]     FLAT
    Kd   on motor rate   X=[50,400,1500,3000]  Y=[2048,2048,2048,2048] FLAT
    Kout on gp-0x671a    X=[5,10,15]           Y=[1024,1024,1024]      FLAT = unity
    BOUND on voted speed X=[128,1280,3200]     Y=[0,1024,1024]
    P EMA cal(0xC6450) = 1024 and D EMA cal(0xC644A) = 1024  =>  alpha = 1.0, NO filtering at all

Collecting the shifts: P_state = 8*err, D_state = 64*d(err), and out = (D+I+P)>>5 * Kout>>10, so

    out = 0.25*err + 2*d(err) + I/32

--------------------------------------------------------------------------------------------------
1. THE OUTPUT CLAMP PROBABLY DOES NOT BIND
--------------------------------------------------------------------------------------------------
At 7.79 Hz and 1 kHz, d(err) per sample = err * 2*pi*7.79/1000 = 0.0489*err, so the D term
contributes 0.098*err against P's 0.250*err, 90 deg apart => |gain| = 0.268.

    speed    bound    |err| needed to reach it
     3 km/h     57            212
     6 km/h    228            850
    10 km/h    455           1699

|err| = |gp-0x4f60 - gp-0x6ad6| is a TRACKING error, not the torque itself, and both of its own
clamps were measured never to saturate. Errors of 850+ counts at 6 km/h are not obviously reached.

--------------------------------------------------------------------------------------------------
2. THE ANTI-WINDUP WINDOW ALMOST CERTAINLY DOES  <- the actual answer
--------------------------------------------------------------------------------------------------
The integrator gains (err * Ki) >> 10 = 0.0957*err EVERY MILLISECOND, and its window is +-bound*32:

    speed    window      time to saturate from zero at a sustained |err| of
                          50 ct      100 ct     200 ct
     3 km/h   +- 1824     381 ms     190 ms      95 ms
     6 km/h   +- 7296    1525 ms     762 ms     381 ms

=> at creep the integrator reaches its window in a FRACTION OF A SECOND on any sustained error. It is
   not a rare excursion; it is the normal operating condition.

V227 raises the window 3x at creep (bound 57 -> 171 at 3 km/h, 228 -> 683 at 6), which TRIPLES the
time the integrator may accumulate before it is pinned.

=> [EVIDENCE, from the cals] THE "INERT" OUTCOME IS UNLIKELY. V227 will change something, and the
   mechanism is specifically the integrator's dwell before saturation -- not the output clamp.
=> [STILL OPEN] whether that helps. An integrator allowed to run longer contributes more low-frequency
   phase lag, which is the classic way to make a lightly-damped mode WORSE. So the sharpened
   prediction is "this will do something, and the something has a plausible route to harm".
🛑 That is a reason to fly it AFTER V222 and alone, not to fold it in.

Run:  python analysis-2020accord/studies/mixer/v227_binds_through_the_integrator.py
"""
import numpy as np

KP, KI, KD, KOUT = 256, 98, 2048, 1024
BOUND = {3: 57, 6: 228, 10: 455}
BOUND_V227 = {3: 171, 6: 683, 10: 1024}
F, FS = 7.79, 1000.0

p_gain = (KP / 1024.0) * 32 / 32 * (KOUT / 1024.0)          # 0.25
d_gain = (KD / 1024.0) * 32 / 32 * (KOUT / 1024.0) * (2 * np.pi * F / FS)
mag = float(np.hypot(p_gain, d_gain))
i_step = KI / 1024.0

print('=' * 88)
print('  V227 -- does the bound BIND? Priced from the cals.')
print('=' * 88)
print()
d_coeff = (KD / 1024.0) * 32 / 32 * (KOUT / 1024.0)      # = 2: D_state = 64*d(err), out = D/32
print('  out = %.3f*err + %.0f*d(err) + I/32   =>  |gain| at %.2f Hz = %.3f'
      % (p_gain, d_coeff, F, mag))
assert abs(d_coeff - 2.0) < 1e-9, 'the d(err) coefficient must be 2, matching the docstring'
assert abs(d_gain - d_coeff * 2 * np.pi * F / FS) < 1e-9, 'the printed coefficient must be the one used'
print()
print('  1. OUTPUT CLAMP -- |err| needed to reach it:')
for k, bd in BOUND.items():
    print('     %2d km/h  bound %5d   |err| = %7.0f' % (k, bd, bd / mag))
print()
print('  2. ANTI-WINDUP WINDOW -- integrator gains %.4f*err per ms, window = +-bound*32:' % i_step)
print('     %-9s %10s %s' % ('speed', 'window', '  '.join('%9s' % ('err=%d' % e) for e in (50, 100, 200))))
for k, bd in BOUND.items():
    w = bd * 32
    print('     %2d km/h   %10d %s'
          % (k, w, '  '.join('%7.0f ms' % (w / (i_step * e)) for e in (50, 100, 200))))
print()
print('  V227 raises the window 3x at creep: %s' % ', '.join(
    '%d km/h %d -> %d' % (k, BOUND[k] * 32, BOUND_V227[k] * 32) for k in (3, 6)))

# --------------------------------- assertions -----------------------------------------
assert BOUND[6] / mag > 500, 'the OUTPUT clamp must need a large err -- that is why it likely misses'
t100 = (BOUND[3] * 32) / (i_step * 100)
assert t100 < 400, 'the integrator must saturate in well under half a second at creep on err=100'
assert BOUND_V227[3] / BOUND[3] > 2.5, 'V227 must roughly triple the window at creep'
assert abs(mag - 0.268) < 0.02, 'the 7.79 Hz gain must be dominated by P, not D'
assert KOUT == 1024 and KI == 98, 'Kout unity and Ki flat -- both are what make this arithmetic simple'
print()
print('  all five assertions hold.')
print('  [EVIDENCE] V227 binds through the INTEGRATOR, not the output clamp -- "inert" is unlikely.')
print('  [OPEN]     whether a longer-running integrator helps. More low-frequency phase lag is the')
print('             classic way to make a lightly-damped mode WORSE, so harm has a plausible route.')
