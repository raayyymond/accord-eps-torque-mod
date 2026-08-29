# -*- coding: utf-8 -*-
"""Is the command's 15-25 Hz peak DRIVEN by the car's resonance, or driving it?

The command channels clear their own slope-matched null in exactly ONE band, 15-25 Hz --
the grind's band -- at median 1.55-1.97x, and are BELOW their null in every other band
including the ratchet's.  Two readings:

  (a) openpilot RE-EMITS the car's resonance: the grind reaches openpilot through its own
      measurements, its 100 Hz lateral controller passes it, and the command inherits the
      peak.  Then command oscillation is a SYMPTOM of the grind and needs no separate
      lever -- damping the resonance fixes both.
  (b) openpilot GENERATES a 15-25 Hz command oscillation that drives the car.  Then it is
      an openpilot-side problem, which the standing instruction forbids changing, and the
      only firmware answer is to filter it on the way in.

Discriminator: if (a), the command peak must SCALE with the car's peak across builds.  If
(b), the command peak would be independent of how much the car is ringing.
"""
import sys
import numpy as np
from scipy import stats

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# 15-25 Hz excess / slope-matched-null ratios, transcribed from the sweep
ROUTES = ['r78', 'r7e', 'r96', 'ra6', 'r1e', 'r22', 'r24']
BUILD = [91, 96, 102, 106, 107, 112, 122]
CAR = [1.69, 6.87, 43.12, 5.40, 9.89, 3.34, 2.94]        # cs_tq -- the car's own resonance
CMD = {
    'co_tqcan': [1.22, 1.65, 3.16, 2.62, 1.28, 2.14, 1.44],
    'sc_tq':    [1.43, 1.49, 2.94, 3.00, 1.55, 2.45, 1.48],
}
# the ratchet band, as a NEGATIVE CONTROL: the car rings hard there and the command does not
CAR_R = [3.87, 3.76, 6.53, 21.77, 15.94, 12.31, 9.15]
CMD_R = {
    'co_tqcan': [0.48, 0.35, 0.23, 0.68, 0.69, 0.42, 0.78],
    'sc_tq':    [0.48, 0.35, 0.26, 0.69, 0.67, 0.50, 0.73],
}

car = np.array(CAR, float)
print('%-10s %-28s %-28s' % ('command', '15-25 Hz vs car 15-25 Hz', '5-12 Hz vs car 5-12 Hz (control)'))
for ch in CMD:
    c = np.array(CMD[ch], float)
    r1, p1 = stats.spearmanr(car, c)
    pr1, pp1 = stats.pearsonr(np.log(car), np.log(c))
    cr = np.array(CMD_R[ch], float)
    r2, p2 = stats.spearmanr(np.array(CAR_R, float), cr)
    print('%-10s rho %+.2f p %.3f  logr %+.2f    rho %+.2f p %.3f'
          % (ch, r1, p1, pr1, r2, p2))

print('\ninterpretation of the CONTROL band:')
print('  the car rings 3.9-21.8x above ITS null at 5-12 Hz while every command channel sits')
print('  at 0.23-0.78, i.e. BELOW its own null.  So the command does NOT simply inherit')
print('  whatever the car does -- it inherits 15-25 Hz and not 5-12 Hz.')

print('\nwhy that asymmetry is the expected one:')
print('  the LKAS lane is a ~1-5 Hz low-pass, so openpilot CANNOT command either resonance.')
print('  What it CAN do is re-emit content its own 100 Hz controller sees in feedback.')
print('  15-25 Hz aliases and passes differently through that path than 5-12 Hz does, and')
print('  the ratchet is a TORQUE mode with no matching ANGLE signature -- and openpilot')
print('  steers on ANGLE/curvature.  A torque-only mode is invisible to it; a mode that')
print('  moves the wheel is not.  That predicts exactly the observed pattern.')

print('\nbuild trend of the COMMAND peak (does it follow the car down?):')
for ch in CMD:
    c = np.array(CMD[ch], float)
    r, p = stats.spearmanr(BUILD, c)
    m = np.array(BUILD) >= 102
    r2, p2 = stats.spearmanr(np.array(BUILD)[m], c[m])
    print('  %-10s full-range rho %+.2f p %.3f   post-V102 rho %+.2f p %.3f'
          % (ch, r, p, r2, p2))
r, p = stats.spearmanr(np.array(BUILD)[np.array(BUILD) >= 102],
                       car[np.array(BUILD) >= 102])
print('  %-10s post-V102 rho %+.2f p %.3f   (for comparison)' % ('cs_tq CAR', r, p))
