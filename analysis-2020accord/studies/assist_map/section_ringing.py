# -*- coding: utf-8 -*-
"""Do the notch designs RING?  Pole radius says they might, and that would bite on-car.

Every candidate tuning reaches its 7-11 Hz attenuation by moving the section's poles close
to the unit circle: r ~ 0.984-0.988 against the FLYING build's 0.797.  A steady-state
frequency response can look flat while a lightly-damped pole pair rings badly on transients,
and the assist map sees transients constantly (kerbs, tramlines, the driver's own inputs).

Frequency response alone cannot see this.  Drive each design with a step and with a
realistic transient and look at the time domain, using the decompiled recursion itself so
the +/-12 clamp is included.
"""
import sys
import numpy as np

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

FS = 1000.0
D = {
    'FLYING':      dict(C_A8=-1.5372, C_AC=0.63462001, C_B0=-1.8808, C_B4=0.81730998),
    'A narrow':    dict(C_A8=-1.97369099, C_AC=0.974325001, C_B0=-1.99693692, C_B4=0.205796897),
    'B wide':      dict(C_A8=-1.97599733, C_AC=0.976558447, C_B0=-1.99728251, C_B4=0.204791307),
    'C protected': dict(C_A8=-1.96667385, C_AC=0.967945814, C_B0=-1.99430621, C_B4=0.217536256),
}


def run(x, c):
    s1 = s2 = 0.0
    y = np.empty_like(x)
    a8, ac, b0, b4 = c['C_A8'], c['C_AC'], c['C_B0'], c['C_B4']
    for i, xi in enumerate(x):
        w = -ac * s1 - a8 * s2 + b4 * xi
        yi = s1 + b0 * s2 + w
        s1, s2 = s2, w
        y[i] = min(max(yi, -12.0), 12.0)
    return y


def poles(c):
    return np.roots([1.0, c['C_A8'], c['C_AC']])


n = 4000
step = np.ones(n)
step[:200] = 0.0

print('%-13s %-9s %-11s %-11s %-12s %-11s %s'
      % ('design', 'pole r', 'ring f Hz', 'ring Q', 'overshoot', 'settle 2%', 'osc cycles'))
for nm, c in D.items():
    p = poles(c)
    r = float(np.max(np.abs(p)))
    fr = float(abs(np.angle(p[0]))) * FS / (2 * np.pi)
    q = 1.0 / (2.0 * max(1.0 - r, 1e-9))
    y = run(step, c)
    ss = float(np.mean(y[-300:]))
    ov = (y[200:].max() - ss) / max(abs(ss), 1e-9)
    # 2% settling time after the step
    idx = np.where(np.abs(y[200:] - ss) > 0.02 * max(abs(ss), 1e-9))[0]
    settle = (idx[-1] / FS) if len(idx) else 0.0
    # count zero-crossings of the error => oscillation cycles before settling
    e = y[200:] - ss
    zc = int(np.sum(np.diff(np.sign(e)) != 0))
    print('%-13s %-9.5f %-11.2f %-11.1f %-12s %-11s %d'
          % (nm, r, fr, q, '%.1f %%' % (100 * ov), '%.0f ms' % (1000 * settle), zc // 2))

print('\nresponse to a 40 ms transient (a kerb / tramline hit), peak and residual ringing:')
t = np.arange(n) / FS
pulse = np.zeros(n)
pulse[500:540] = 1.0
print('%-13s %-12s %-14s %s' % ('design', 'peak out', 'still ringing?', 'residual at +1 s'))
for nm, c in D.items():
    y = run(pulse, c)
    resid = float(np.max(np.abs(y[1540:1560])))
    print('%-13s %-12.4f %-14s %.5f'
          % (nm, float(np.max(np.abs(y))), 'YES' if resid > 0.02 else 'no', resid))

print("""
READING
  The FLYING section has r = 0.797: heavily damped, settles fast, no ringing.
  Every candidate needs r ~ 0.985 to reach 7-11 Hz, which is a Q of ~40 at ~3 Hz -- IN THE
  DRIVER'S OWN BAND.  If the step and pulse rows show sustained oscillation, the tuning is
  not flyable regardless of how good its frequency response looks, and the honest conclusion
  is that this second-order section cannot deliver the ratchet notch without introducing a
  worse low-frequency resonance.""")
