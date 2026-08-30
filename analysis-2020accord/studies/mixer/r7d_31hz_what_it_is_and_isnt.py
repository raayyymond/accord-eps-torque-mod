# -*- coding: utf-8 -*-
"""What the ~31 Hz line on r7d IS, what it is NOT, and the limit that stops us naming it.

r7d is the drive the operator aborted -- "it vibrated the entire car, and I decided it was not safe
to drive".  It flew V94, the only build in the corpus at a low apparent-inertia dose (0.250x).
inertia_dose_vs_peak_frequency.py refuted the 1/sqrt(J) reading and left the line UNEXPLAINED.
This file narrows it, and is explicit about the one thing that still cannot be excluded.

--------------------------------------------------------------------------------------------------
WHAT IT IS  [EVIDENCE, r7d cache, cc_lat mask, 2 s Welch, engaged vs manual on the same route]
--------------------------------------------------------------------------------------------------
  IN THE LOOP, NOT COMMANDED.  The line is 63x background in cs_rate engaged and absent in manual,
  and it is present in `probe`, the cave byte -- the firmware's OWN internal state -- at 11x.
  But the LKAS request carries NO 30 Hz content at all: sc_req's engaged peaks are 3.0 / 5.0 / 7.0 /
  9.0 Hz, a clean roll-off.  So the EPS is generating it, not tracking it.

      channel     engaged top peaks (x background)      manual
      cs_rate     30.1:63x  7.0:34x  32.1:21x           3.0:196x  5.5:20x  8.0:8x   (no 30)
      tq          7.0:218x  30.1:46x 5.0:42x            3.0:95x   5.0:12x  8.5:5x   (no 30)
      probe       30.1:11x  27.0:4x  25.0:4x            24.0:3x   29.1:2x           (firmware-side)
      sc_req      3.0  5.0  7.0  9.0                    --                          (NO 30 Hz)

--------------------------------------------------------------------------------------------------
WHAT IT IS NOT
--------------------------------------------------------------------------------------------------
  (1) NOT a harmonic of the ~7.8 Hz ratchet.  A cascade must show 2f.  It does not:
      the 2f rung (15.6 Hz) sits at 0.47x background in cs_rate and 0.67x in tq -- BELOW background,
      while 4f sits at 69.7x.  You cannot reach a 4th harmonic without a 2nd.

  (2) NOT the apparent-inertia mode moving, and now refuted under the RIGHT functional form.
      The prior study fit a power law.  The stated mechanism is not a power law -- it saturates:
          f(dose) = A / sqrt(1 + B*dose)
      Calibrating A and B on the 0.250x and 1.000x points and predicting the high-dose end:
          dose 3.576  predicted 13.30 Hz   observed 20.90 Hz
          dose 3.964  predicted 12.71 Hz   observed 17.19 Hz
      The mechanism fails its own arithmetic under the model that is most favourable to it.

  (3) NOT band-specific, which is the finding that reframes it.  Testing fixed-band engaged/manual
      power instead of argmax frequency, EVERY band tracks the dose at once and by similar amounts:
          HIGH 28-34  corr -0.853      LOW  5-12  corr -0.747
          ctlA 12-18  corr -0.574      ctlB 40-46 corr -0.790
      Bands that move together are a LOOP-GAIN change, not a resonance being repositioned.
      => [BELIEF] cutting apparent inertia raised engaged closed-loop gain broadband; ~31 Hz is
         merely where this plant peaks.  Consistent with the operator's own words: the whole car
         vibrated, not a tone.

--------------------------------------------------------------------------------------------------
WHY IT IS STILL NOT PROVEN -- TWO LIMITS, BOTH REAL
--------------------------------------------------------------------------------------------------
  (a) NOT IDENTIFIED.  Inertia dose correlates with build number at +0.750 across the corpus, build
      number alone predicts the broadband lift at p=0.087, and the whole association dies when the
      single low-dose route is dropped (p=0.0087 -> 0.2486).  One drive carries all of it.

  (b) ALIASING CANNOT BE EXCLUDED, AND THIS AFFECTS EVERY HIGH-BAND CLAIM IN THE KIT.
      Every route caches at fs = 101.01-101.26 Hz, so Nyquist is ~50.5 Hz and anything real in
      52-71 Hz FOLDS INTO THE 30-49 Hz BAND THE KIT SCORES.  A real 70.1 Hz line lands on 31 Hz.
      No channel here escapes it: probe, raw14 and raw18 share the 101 Hz frame rate, and the ~50 Hz
      channels (raw1ab, ws) fold 30 Hz and 70 Hz to the SAME ~20 Hz.  The spread in fs across routes
      is 0.25 Hz, far too small to separate the alias by its shift.
      => the 30-49 Hz control band added to score_drive.py inherits this caveat.  A line in it is
         "30-49 Hz OR its 52-71 Hz alias", never 30-49 Hz alone.

  THE WAY OUT IS A CAVE RUNG, NOT MORE ANALYSIS.  A zero-crossing COUNTER on the internal signal,
  incremented in the 1000 Hz control task and reported once per CAN frame, measures the true
  oscillation rate independently of the 100 Hz transmit rate and is immune to folding by
  construction.  Spec: docs/specs/design/PROBE-zero-crossing-rate-counter.md.  Its positive control
  is free -- the established ~7.8 Hz ratchet must read ~15-16 crossings/s.

Run:  python analysis-2020accord/studies/mixer/r7d_31hz_what_it_is_and_isnt.py
"""
import numpy as np

# ---- (2) the saturating model, calibrated on the low end, predicting the high end ----------
DOSE = np.array([0.250, 1.000, 1.500, 1.500, 1.500, 1.500, 3.576, 3.576, 3.964])
HIGH = np.array([30.86, 21.88, 19.92, 19.53, 22.27, 22.66, 19.92, 21.88, 17.19])

r2 = (HIGH[0] / HIGH[1]) ** 2                      # f(0.25)^2 / f(1.0)^2 = (1+B) / (1+0.25B)
B = (r2 - 1.0) / (1.0 - 0.25 * r2)
A = HIGH[1] * np.sqrt(1.0 + B)
pred = lambda d: A / np.sqrt(1.0 + B * d)

# ---- (3) the bands move together --------------------------------------------------------
CORR = {'HIGH 28-34': -0.853, 'LOW 5-12': -0.747, 'ctlA 12-18': -0.574, 'ctlB 40-46': -0.790}

# ---- (a) identification ------------------------------------------------------------------
P_ALL, P_NO_R7D, CORR_DOSE_BUILD, P_BUILD = 0.0087, 0.2486, 0.750, 0.0873

# ---- (b) aliasing ------------------------------------------------------------------------
FS_LO, FS_HI, F_OBS = 101.010, 101.260, 30.06

print('=' * 92)
print('  r7d ~31 Hz -- IN THE LOOP, BROADBAND, AND NOT SEPARABLE FROM ITS ALIAS')
print('=' * 92)
print()
print('  (2) saturating apparent-inertia model  f = A/sqrt(1+B*dose),  A=%.2f Hz  B=%.3f' % (A, B))
print('      %-8s %10s %10s %8s' % ('dose', 'predicted', 'observed', 'error'))
for d, h in ((3.576, 20.90), (3.964, 17.19)):
    print('      %-8.3f %10.2f %10.2f %+8.1f%%' % (d, pred(d), h, 100 * (pred(d) / h - 1)))
print('      => refuted under the functional form most favourable to the mechanism')
print()
print('  (3) every band tracks the dose, and by similar amounts:')
for k, v in CORR.items():
    print('      %-12s corr %+.3f' % (k, v))
print('      spread across bands %.3f -- a MODE would put the HIGH band far clear of the controls'
      % (max(CORR.values()) - min(CORR.values())))
print()
print('  (a) dose vs build number corr %+.3f; perm p %.4f -> %.4f when r7d is dropped'
      % (CORR_DOSE_BUILD, P_ALL, P_NO_R7D))
print()
print('  (b) fs %.3f-%.3f Hz  =>  Nyquist ~%.2f Hz;  a real line at %.1f-%.1f Hz folds onto %.2f'
      % (FS_LO, FS_HI, FS_LO / 2, FS_LO - F_OBS, FS_HI - F_OBS, F_OBS))
print('      the kit scores 30-49 Hz; that band is contaminated by anything real in %.0f-%.0f Hz'
      % (FS_LO - 49, FS_HI - 30))
print()

# ---------------------------------- assertions -------------------------------------------
assert pred(3.576) < 0.75 * 20.90 and pred(3.964) < 0.80 * 17.19, \
    'the saturating model must UNDER-predict the high-dose end by a wide margin'
assert max(CORR.values()) - min(CORR.values()) < 0.30, \
    'the bands must move together; if they separate, re-open the mode reading'
assert CORR['HIGH 28-34'] < 0 and CORR['ctlB 40-46'] < 0, 'both must share the sign'
assert P_NO_R7D > 0.05 > P_ALL, 'the association must die when the single low-dose route is dropped'
assert CORR_DOSE_BUILD > 0.7, 'dose and build number must be flagged as confounded'
assert FS_LO - 49.0 > FS_LO / 2, \
    'the 52-71 Hz fold source must sit entirely ABOVE Nyquist -- that is what makes it invisible ' \
    'and unremovable: we can neither see it nor filter it out after the fact'
assert abs((FS_LO - F_OBS) - 70.95) < 1.0, 'the fold frequency must land where the docstring says'
print('  all seven assertions hold.')
print('  VERDICT: [EVIDENCE] in-loop and not commanded; NOT a harmonic; NOT the inertia mode moving.')
print('           [BELIEF]   a broadband engaged loop-gain rise, carried by one drive.')
print('           [OPEN]     30-49 Hz cannot be separated from 52-71 Hz without a cave counter.')
