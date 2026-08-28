# -*- coding: utf-8 -*-
"""CASE-CONTROL on the operator's own labelled event -- what PRECEDES the oscillation?

The operator named route 23, segment 7, 21:46:48 as "an exact instance" of the peak-turn
oscillation; it was located at t = 445.6-448.2 s, 7.42 Hz, 6-9 Hz rate rms 16.86 deg/s
against a corpus p99 of 3.98. That is ONE precisely labelled positive, and it has only
been used for characterisation.

Here it is used as a CASE, against CONTROLS drawn from the same drive: windows matched on
speed, |angle| and |rate| that did NOT oscillate. Everything is within r23, so route-level
variance -- the problem that has invalidated several results this session -- cannot apply.

The question is not "what does the oscillation look like" but "what is DIFFERENT in the
seconds BEFORE it", because that is what a fix has to act on.
"""
import numpy as np, os
from scipy import signal

FS = 100.0
z = np.load('analysis-2020accord/_scratch/cache/r23/r23.npz', allow_pickle=True)
G = lambda k: np.asarray(z[k]).astype(float) if k in z.files else None
t = G('t')
if t is None:
    t = np.arange(len(G('cs_rate'))) / FS
rate, ang, v, lat = G('cs_rate'), G('ang'), G('cs_v'), G('cc_lat')
tq, req = G('cs_tq'), (G('cc_req') if G('cc_req') is not None else G('co_tqcan'))

T0, T1 = 445.6, 448.2
NW = 256


def band(x, lo, hi):
    f, P = signal.welch(x - np.mean(x), FS, nperseg=min(NW, len(x)))
    return np.sqrt(np.sum(P[(f >= lo) & (f <= hi)]) * (f[1] - f[0]))


i0, i1 = int(np.searchsorted(t, T0)), int(np.searchsorted(t, T1))
print("EVENT  t = %.1f-%.1f s   n = %d samples" % (t[i0], t[i1], i1 - i0))
ev = dict(v=np.mean(v[i0:i1]) * 3.6, ang=np.mean(np.abs(ang[i0:i1])),
          rate=np.percentile(np.abs(rate[i0:i1]), 95), osc=band(rate[i0:i1], 6, 9))
print("  speed %.1f km/h   |ang| %.1f deg   p95|rate| %.1f deg/s   6-9 Hz rms %.2f\n"
      % (ev['v'], ev['ang'], ev['rate'], ev['osc']))

# controls: same drive, engaged, matched on speed/angle/rate, NOT oscillating
cands = []
m = (lat > 0.5) & (v > 1.0)
for a in range(0, len(rate) - NW, NW // 4):
    b = a + NW
    if not m[a:b].all():
        continue
    if abs(t[a] - T0) < 6:
        continue
    c = dict(i=a, v=np.mean(v[a:b]) * 3.6, ang=np.mean(np.abs(ang[a:b])),
             rate=np.percentile(np.abs(rate[a:b]), 95), osc=band(rate[a:b], 6, 9))
    cands.append(c)
print("  %d candidate windows in r23." % len(cands))
sel = [c for c in cands
       if abs(c['v'] - ev['v']) < 20 and abs(c['ang'] - ev['ang']) < 30
       and c['rate'] > 0.25 * ev['rate']]
sel = sorted(sel, key=lambda c: c['osc'])[:max(int(len(sel)*0.6), 10)]
print("  %d matched CONTROLS (speed +-12 km/h, |ang| +-12 deg, rate >= 40%% of the event)\n" % len(sel))


def lead(sig, i, secs):
    a = max(0, i - int(secs * FS))
    return sig[a:i]


print("  what is DIFFERENT in the %s s BEFORE?  (event value | control median | ratio)" % '2.0')
CH = [('|angle| mean', lambda i: np.mean(np.abs(lead(ang, i, 2.0)))),
      ('|angle| max', lambda i: np.max(np.abs(lead(ang, i, 2.0)))),
      ('d|angle|/dt', lambda i: np.mean(np.abs(np.diff(np.abs(lead(ang, i, 2.0)))) * FS)),
      ('|rate| p95', lambda i: np.percentile(np.abs(lead(rate, i, 2.0)), 95)),
      ('|accel| p95', lambda i: np.percentile(np.abs(np.diff(lead(rate, i, 2.0))) * FS, 95)),
      ('speed km/h', lambda i: np.mean(lead(v, i, 2.0)) * 3.6),
      ('d(speed)/dt', lambda i: np.mean(np.diff(lead(v, i, 2.0))) * FS),
      ('6-9 Hz rms', lambda i: band(lead(rate, i, 2.0), 6, 9)),
      ('18-22 Hz rms', lambda i: band(lead(rate, i, 2.0), 18, 22))]
if tq is not None:
    CH += [('|drv torque| p95', lambda i: np.percentile(np.abs(lead(tq, i, 2.0)), 95)),
           ('|drv torque| mean', lambda i: np.mean(np.abs(lead(tq, i, 2.0))))]
if req is not None:
    CH += [('|LKAS cmd| p95', lambda i: np.percentile(np.abs(lead(req, i, 2.0)), 95))]

for nm, fn in CH:
    try:
        e = fn(i0)
        cs = np.array([fn(c['i']) for c in sel])
        med = np.median(cs)
        pct = (cs < e).mean() * 100
        print("   %-20s %10.3f | %10.3f | %6.2fx   event is at the %5.1f th pct of controls"
              % (nm, e, med, e / med if med else np.nan, pct))
    except Exception as ex:
        print("   %-20s  <%s>" % (nm, ex))
