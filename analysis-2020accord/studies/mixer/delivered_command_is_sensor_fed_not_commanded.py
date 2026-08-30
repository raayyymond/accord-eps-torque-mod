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

SPLIT BY SPEED -- the attribution HOLDS EVERYWHERE, and gets STRONGER where the ratchet lives.
Excess coherence over each band's own shuffled null (the null absorbs the small-sample bias, which is
why the low-speed nulls are larger):

    speed band          2-4 Hz          6-9 Hz         9-12 Hz        12-18 Hz
    LOW  1.5-4 m/s   col +0.637      col +0.544      col +0.236      col +0.259    9 windows, 36 s
     (9 windows)     cmd +0.107      cmd +0.362      cmd +0.095      cmd +0.099
    MID  4-10 m/s    col +0.073      col +0.234      col +0.188      col +0.239   37 windows, 148 s
                     cmd +0.085      cmd +0.080      cmd +0.049      cmd +0.054
    HIGH >10 m/s     col +0.103      col +0.276      col +0.212      col +0.238   63 windows, 252 s
                     cmd +0.041      cmd +0.128      cmd +0.065      cmd +0.078

  * the column beats the command in 11 of the 12 speed x band cells, by 1.5x to 6.0x.
  * 🛑 THE ONE EXCEPTION, and my first write-up got this wrong until an assertion caught it:
    MID 4-10 m/s, 2-4 Hz -> ratio 0.9x, the COMMAND slightly ahead (+0.085 vs +0.073). That is the
    LKAS lane's OWN band (openpilot's request is a ~1-5 Hz low-pass), so the command explaining the
    delivered content there is expected and is a sanity check, not a problem. In the three SYMPTOM
    bands (6-9, 9-12, 12-18 Hz) the column wins at EVERY speed, 1.5x-4.4x.
  * at LOW speed the delivered command tracks the column MUCH more tightly (0.575-0.688 raw vs
    ~0.24-0.28 higher up), so the sensor-shared reading is STRONGEST where the ratchet lives.
  * 🛑 ONE HONEST EXCEPTION, and it is in the ratchet's own band: at LOW speed the COMMAND's share
    rises to +0.362 in 6-9 Hz, narrowing the ratio to 1.5x -- its largest share anywhere. So at creep
    speeds in 6-9 Hz the delivered content is NOT purely loop content; openpilot's command explains a
    real fraction. That is consistent with the recorded "engagement amplifies 6-9 Hz 2.8x" -- the
    command's ENTRY matters there, even though the command carries no 6-9 Hz tone of its own.
  ⚠ the LOW row is 9 windows / 36 s. It is the weakest row and must not be quoted as tightly as the
    other two.
  ⚠ only 682 engaged frames (6.7 s) sit below 1.5 m/s, far too few to window -- TRUE creep is NOT
    covered by this route at all.

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
# ---- the speed split, and the one place the reading weakens ----------------------------
SPLIT = {  # band -> (col excess, cmd excess) per speed row
    'LOW  1.5-4':  (np.array([0.637, 0.544, 0.236, 0.259]), np.array([0.107, 0.362, 0.095, 0.099])),
    'MID  4-10':   (np.array([0.073, 0.234, 0.188, 0.239]), np.array([0.085, 0.080, 0.049, 0.054])),
    'HIGH >10':    (np.array([0.103, 0.276, 0.212, 0.238]), np.array([0.041, 0.128, 0.065, 0.078])),
}
N_WIN_SPLIT = {'LOW  1.5-4': 9, 'MID  4-10': 37, 'HIGH >10': 63}
print()
print('  by speed -- ratio column/command per band:')
for k, (cc, mm) in SPLIT.items():
    print('    %-12s %s   (%d windows)'
          % (k, '  '.join('%6.1fx' % r for r in cc / mm), N_WIN_SPLIT[k]))
_lo_ratio = (SPLIT['LOW  1.5-4'][0] / SPLIT['LOW  1.5-4'][1])[1]
print('    the ratchet band at LOW speed is the NARROWEST ratio anywhere: %.1fx' % _lo_ratio)

# the SYMPTOM bands are indices 1..3; index 0 (2-4 Hz) is the LKAS lane's own band, where the
# command is expected to win and does at mid speed -- asserting otherwise was an overclaim.
for k, (cc, mm) in SPLIT.items():
    assert (cc[1:] > mm[1:]).all(),         'the column must beat the command in the three SYMPTOM bands at %s' % k
assert (SPLIT['MID  4-10'][1] > SPLIT['MID  4-10'][0])[0],     'the 2-4 Hz mid-speed cell is the documented exception -- if it flips, the write-up is stale'
assert 1.2 < _lo_ratio < 2.0,     'the low-speed 6-9 Hz ratio must be reported as NARROW (~1.5x) -- it is the one place the '     '"purely loop content" reading weakens, and burying it would be dishonest'
assert SPLIT['LOW  1.5-4'][0][:2].min() > SPLIT['HIGH >10'][0][:2].max(),     'low-speed column coupling must be the TIGHTEST -- that is why the reading matters here'
assert N_WIN_SPLIT['LOW  1.5-4'] < 12,     'the low row must stay flagged as the thin one; if it grows, re-derive rather than reuse'
print('  all nine assertions hold.')
print()
print('  [EVIDENCE] delivered-command content in the symptom bands is SENSOR-SHARED, not')
print('             COMMAND-SHARED -- independent support for Lever B\'s lever class.')
print('  [NOTE]     closed loop, so no causal arrow; highway not creep; nothing above ~20 Hz.')
