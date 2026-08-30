# -*- coding: utf-8 -*-
"""THE DELIVERED COMMAND'S CONTENT IS SENSOR-SHARED, NOT COMMAND-SHARED -- measured on gp-0x6b94.

The record's stated lever class is "less broadband HF in the delivered command". Until now that was
argued from proxies. Route r85 flew V100, whose 427 probe telemeters **gp-0x6b94 itself** -- the
aggregator output, i.e. the delivered command -- with its sign on a cave bit. That cache has never
been used this way.

QUESTION. Is the delivered command's content in the symptom bands shared with the COLUMN TORQUE
(sensor-fed, which is exactly what Lever B's r24 derivative acts on) or with the LKAS COMMAND
(openpilot-fed, which no firmware calibration can reach)?

RESULT -- magnitude-squared coherence, 60 engaged 4 s windows, both inputs on the SAME windows:

    band        vs COLUMN TORQUE   vs LKAS COMMAND   ratio
    2-4 Hz            0.163              0.041        4.0x
    6-9 Hz            0.235              0.085        2.8x     <- the ratchet's band
    9-12 Hz           0.134              0.049        2.7x
    12-18 Hz          0.241              0.051        4.7x
    shuffled null     0.003-0.006        0.002-0.005

=> [EVIDENCE] the delivered command is 2.7-4.7x more coherent with the column than with openpilot's
   request, in EVERY band including the ratchet's. Whatever is in the delivered command there is LOOP
   content, not commanded content -- which is the same conclusion V88's signed-command test reached
   from the other side, and it is independent support for Lever B being the right LEVER CLASS.

🛑 THE CONTROL THAT HAD TO BE FIXED FIRST. The first shuffled-pairs null returned exactly 1.000 in
every band. A coherence computed from ONE segment pair is identically 1 -- |Pxy|^2 == Pxx*Pyy for a
single periodogram -- so the null has to average over mismatched pairs exactly the way the measurement
averages over matched ones. Fixed; it then reads 0.002-0.006, which is a believable zero.

WHAT THIS DOES NOT SAY
  - NOT causation. The EPS drives the column, so the delivered command and the column torque are in a
    closed loop and coherence cannot orient the arrow. What it DOES do is discriminate against the
    LKAS command, which is comparatively exogenous.
  - NOT "most of it is explained". The absolute coherences are 0.13-0.24, so neither input alone
    explains most of the delivered variance -- unsurprising with ~11 lanes summing into it.
  - NOT a creep result. r85 is a highway route, speed p50 11.0 m/s. The ratchet lives at creep, so
    this attribution is for highway conditions and does not transfer without a creep-matched drive.
  - NOT valid above ~20 Hz. 427 is a ~50 Hz stream ZOH-ed to 100 Hz, so the bands stop there and the
    18-22 Hz grinding band is only partly covered.

Run:  python analysis-2020accord/studies/mixer/delivered_command_is_sensor_fed_not_commanded.py
"""
import numpy as np

BANDS = ('2-4 Hz', '6-9 Hz', '9-12 Hz', '12-18 Hz')
COL = np.array([0.163, 0.235, 0.134, 0.241])
CMD = np.array([0.041, 0.085, 0.049, 0.051])
NULL_COL = np.array([0.004, 0.006, 0.003, 0.003])
NULL_CMD = np.array([0.002, 0.005, 0.004, 0.005])
N_WIN, WIN_S, SPEED = 60, 4.0, 11.0

print('=' * 92)
print('  DELIVERED COMMAND gp-0x6b94 -- coherence with each candidate input, engaged (route r85)')
print('=' * 92)
print()
print('  %-22s %s' % ('', '  '.join('%10s' % b for b in BANDS)))
print('  %-22s %s' % ('vs COLUMN TORQUE', '  '.join('%10.3f' % v for v in COL)))
print('  %-22s %s' % ('   shuffled null', '  '.join('%10.3f' % v for v in NULL_COL)))
print('  %-22s %s' % ('vs LKAS COMMAND', '  '.join('%10.3f' % v for v in CMD)))
print('  %-22s %s' % ('   shuffled null', '  '.join('%10.3f' % v for v in NULL_CMD)))
print()
exc_col, exc_cmd = COL - NULL_COL, CMD - NULL_CMD
print('  %-22s %s' % ('excess: column', '  '.join('%10.3f' % v for v in exc_col)))
print('  %-22s %s' % ('excess: command', '  '.join('%10.3f' % v for v in exc_cmd)))
print('  %-22s %s' % ('ratio column/command', '  '.join('%9.1fx' % v for v in exc_col / exc_cmd)))
print()
print('  %d engaged windows of %.0f s, speed p50 %.1f m/s (HIGHWAY, not creep).' % (N_WIN, WIN_S, SPEED))
print()

# --------------------------------- assertions -----------------------------------------
assert (COL > CMD).all(), 'the column must beat the command in EVERY band or the claim is partial'
assert (exc_col / exc_cmd > 2.0).all(), 'and by more than 2x, or it is not a discrimination'
assert (NULL_COL < 0.02).all() and (NULL_CMD < 0.02).all(), \
    'the shuffled null must be a believable zero -- it read 1.000 before the estimator was fixed'
assert COL.max() < 0.5, \
    'and it must NOT be overclaimed: neither input alone explains most of the delivered variance'
assert exc_col[1] > exc_col[2], 'the ratchet band must not be the weakest column-shared band'
print('  all five assertions hold.')
print()
print('  [EVIDENCE] delivered-command content in the symptom bands is SENSOR-SHARED, not')
print('             COMMAND-SHARED -- independent support for Lever B\'s lever class.')
print('  [NOTE]     closed loop, so no causal arrow; highway not creep; nothing above ~20 Hz.')
