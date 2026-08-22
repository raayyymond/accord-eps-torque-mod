r"""IS THE MICROPHONE SENSITIVE **IN THE AUDIBLE RANGE**?  Two independent positive controls.

WHY THIS IS NEEDED.  `acoustic_positive_control.py` showed the mic is blind to the 21-28 Hz mode:
wheel-rate in-burst level runs 0.88 -> 18.6 across the gain ladder (21x) while the acoustic
in-burst level sits flat at 380-510 on every build, and the two envelopes are uncorrelated
(r = -0.13..+0.05, all inside a phase-shuffled surrogate null).

But that is a 25 Hz result, and a phone-class MEMS mic is high-passed near there.  **It says
NOTHING about 1 kHz.**  Without a working control in the audible range, item 2's 100 Hz - 8 kHz
null is UNINTERPRETABLE rather than negative -- and this project's rule is that an uninterpretable
null is a design failure, not a verdict.  So: two controls with known ground truth.

  CONTROL A -- SPEED.  Tyre and wind noise are the loudest thing in a car and rise steeply with
     speed.  If the audible bands do not track speed, the channel is dead.  Ground truth: strong
     positive dB/(km/h) slopes, biggest in the mid bands.

  CONTROL B -- THE TURN SIGNAL.  A blinker is a discrete, repetitive, plainly AUDIBLE cabin click
     at ~1.5 Hz, and `cs_lblink` / `cs_rblink` put its exact timing on the CAN bus for free.  It is
     an almost perfect positive control: known time base, known audibility, modest level, and it
     has nothing to do with speed, LKAS or the firmware.  Event-triggered average of the band
     envelope against a RANDOM-TIME surrogate.
     ⇒ If the mic resolves blinker clicks, it demonstrably hears real cabin sounds of modest
       level, and the item-2 null becomes a genuine negative result about grinding.
     ⇒ If it cannot even resolve a blinker, the acoustic channel is not a usable instrument here
       and I will say the whole workstream is uninstrumented.
"""
import os
import sys
import json
import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acoustic_lib as A                                            # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TAGS = ['r97', 'r96', 'r9e', 'ra4']

print("=" * 120)
print("CONTROL A -- SPEED.  dB of band power per km/h, engaged+manual pooled, 0-100 km/h.")
print("            Tyre and wind noise are the loudest thing in a car.  If these are flat, the")
print("            channel is dead.")
print("=" * 120)
R = {t: A.load(t) for t in TAGS}
TOBF = R['r97']['tob_f']
NB = len(TOBF)
print("%9s" % 'band Hz' + "".join("%14s" % A.NAMES[t] for t in TAGS) + "%12s" % 'median')
SLOPES = {}
for i in range(0, NB, 2):
    row = []
    for t in TAGS:
        r = R[t]
        m = (r['v'] > 1) & (r['v'] < 100) & np.isfinite(r['tob'][:, i]) & (r['tob'][:, i] > 0)
        y = 10 * np.log10(r['tob'][m, i])
        x = r['v'][m]
        X = np.vstack([x, np.ones(len(x))]).T
        row.append(np.linalg.lstsq(X, y, rcond=None)[0][0])
    SLOPES[float(TOBF[i])] = row
    print("%9.0f" % TOBF[i] + "".join("%14.3f" % v for v in row) + "%12.3f" % np.median(row))
print("  dB per km/h.  A working microphone shows a clear positive slope through the mid bands.")

print()
print("=" * 120)
print("CONTROL B -- THE TURN SIGNAL.  A plainly audible cabin click with its timing free on CAN.")
print("=" * 120)
FSE = 125.0
PRE, POST = 0.30, 0.50
OUT = {}
for t in TAGS:
    r = R[t]
    c = np.load(os.path.join(A.HERE, '_cache_%s' % t, '%s.npz' % t), allow_pickle=True)
    e = np.load(os.path.join(A.HERE, '_cache_%s' % t, '%s_env.npz' % t))
    te, ev, sp = e['t'].astype(float), e['env'].astype(float), e['splice'].astype(bool)
    bf = e['env_f']
    ct = c['t'].astype(float)
    bl = (c['cs_lblink'].astype(float) > 0.5) | (c['cs_rblink'].astype(float) > 0.5)
    # blinker ON transitions
    on = np.flatnonzero((~bl[:-1]) & bl[1:]) + 1
    ton = ct[on]
    # keep only isolated clicks with a clean window
    ton = ton[(ton > te[0] + PRE + 0.1) & (ton < te[-1] - POST - 0.1)]
    if len(ton) < 20:
        print("  %-5s only %d blinker onsets -- skipped" % (t, len(ton)))
        continue
    npre, npost = int(PRE * FSE), int(POST * FSE)
    idx = np.searchsorted(te, ton)
    idx = idx[(idx > npre) & (idx < len(te) - npost)]
    rng = np.random.default_rng(3)
    fake = rng.integers(npre, len(te) - npost, max(len(idx) * 8, 400))
    print("\n  ---- %s %s: %d blinker onsets ----" % (t, A.NAMES[t], len(idx)))
    print("%14s %12s %12s %20s %10s" %
          ('band Hz', 'pre level', 'post/pre', 'surrogate post/pre', 'z'))
    row = {}
    for j in range(len(bf)):
        if bf[j][0] < 100:
            continue
        E = ev[:, j]

        def eta(ii):
            a = np.array([E[k - npre:k].mean() for k in ii])
            b = np.array([E[k:k + npost].mean() for k in ii])
            return a, b

        a, b = eta(idx)
        ratio = float(b.mean() / a.mean())
        fa, fb = eta(fake)
        fr = fb / np.maximum(fa, 1e-12)
        lo, hi = np.percentile(fr, [2.5, 97.5])
        z = (ratio - fr.mean()) / (fr.std() / np.sqrt(len(idx)) * np.sqrt(len(fr) / len(idx)))
        z = (ratio - np.median(fr)) / (np.std(fr) / np.sqrt(len(idx)))
        row["%g-%g" % tuple(bf[j])] = dict(ratio=ratio, lo=float(lo), hi=float(hi), z=float(z))
        print("%14s %12.1f %12.4f %20s %10.2f"
              % ("%g-%g" % tuple(bf[j]), a.mean(), ratio, "[%.4f, %.4f]" % (lo, hi), z))
    OUT[t] = row
print()
print("  post/pre is the band envelope in the 0.5 s AFTER a blinker-on transition divided by the")
print("  0.3 s before.  The surrogate uses random times in the same route.  |z| > 3 = the mic")
print("  resolves the click in that band.")

json.dump({'speed_slopes': SLOPES, 'blinker': OUT},
          open(os.path.join(A.HERE, '_acoustic_audible_control.json'), 'w'), indent=1)
print("\n  wrote _acoustic_audible_control.json")
