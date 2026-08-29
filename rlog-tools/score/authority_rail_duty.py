# -*- coding: utf-8 -*-
"""Is LKAS actually AUTHORITY-limited, or is it delivering what it asks for?

"LKAS authority" can mean two very different failures and they have opposite fixes:
  (a) the COMMAND rails -- openpilot asks for more than the protocol/firmware will accept,
      so the ceiling binds and raising it (if legal) is the lever;
  (b) the command never rails but the CAR does not follow it -- the ceiling is irrelevant
      and the problem is delivery: the torque is requested and not produced.

Memory records the previous answer: V54 measured authority as "0 BY DESIGN", the soft-EME
windup held at zero by V31's boost floor, and 0xC407E is a hard-fault interlock Honda ships
at 511, one count under its own 512 trip -- V73 raised it and V74/V75 faulted.  So (a)'s
obvious lever is closed.  This asks whether (a) is even the right diagnosis.

Measured per route on engaged frames: how often the command sits at or near its rail, how
often it is small, and how well the delivered bar torque tracks it.
"""
import os, sys
import numpy as np
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROUTES = [('r78', 'V91'), ('r7e', 'V96'), ('r96', 'V102'), ('ra6', 'V106'),
          ('r1e', 'V107'), ('r22', 'V112'), ('r24', 'V122')]


def load(tag):
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not os.path.exists(p):
        return None
    return np.load(p, allow_pickle=True)


print('%-6s %-6s %-8s %-11s %-11s %-11s %-11s %s'
      % ('route', 'build', 'eng n', 'cmd |max|', 'rail duty', '>=90% duty', '>=50% duty', 'p50 |cmd|'))
rows = []
for tag, bld in ROUTES:
    z = load(tag)
    if z is None or 'sc_tq' not in z.files:
        continue
    lat = np.asarray(z['cc_lat']).astype(float)
    cmd = np.asarray(z['sc_tq']).astype(float)
    n = min(len(lat), len(cmd))
    m = (lat[:n] > 0.5) & np.isfinite(cmd[:n])
    c = np.abs(cmd[:n][m])
    if c.size < 500:
        continue
    mx = c.max()
    rows.append((tag, bld, c, mx))
    print('%-6s %-6s %-8d %-11.0f %-11.4f %-11.4f %-11.4f %.0f'
          % (tag, bld, c.size, mx, (c >= mx * 0.999).mean(), (c >= mx * 0.9).mean(),
             (c >= mx * 0.5).mean(), np.percentile(c, 50)))

allmax = max(r[3] for r in rows) if rows else 0
print('\n  observed command ceiling across all routes: %.0f counts' % allmax)
print('  pooled duty at >=99.9%% of that ceiling: %.4f'
      % np.mean([(r[2] >= allmax * 0.999).mean() for r in rows]))
print('  pooled duty at >=90%%:  %.4f' % np.mean([(r[2] >= allmax * 0.9).mean() for r in rows]))
print('  pooled duty at >=50%%:  %.4f' % np.mean([(r[2] >= allmax * 0.5).mean() for r in rows]))

print('\nDELIVERY -- does the bar torque follow the command?  (engaged frames, |corr| and slope)')
print('%-6s %-6s %-12s %-12s %s' % ('route', 'build', 'corr(cmd,bar)', 'slope ct/ct', 'note'))
for tag, bld in ROUTES:
    z = load(tag)
    if z is None or 'sc_tq' not in z.files or 'cs_tq' not in z.files:
        continue
    lat = np.asarray(z['cc_lat']).astype(float)
    cmd = np.asarray(z['sc_tq']).astype(float)
    bar = np.asarray(z['cs_tq']).astype(float)
    n = min(len(lat), len(cmd), len(bar))
    m = (lat[:n] > 0.5) & np.isfinite(cmd[:n]) & np.isfinite(bar[:n])
    x, y = cmd[:n][m], bar[:n][m]
    if x.size < 500 or np.std(x) == 0:
        continue
    r = float(np.corrcoef(x, y)[0, 1])
    sl = float(np.polyfit(x, y, 1)[0])
    print('%-6s %-6s %-12.3f %-12.4f %s'
          % (tag, bld, r, sl, 'command and bar move together' if abs(r) > 0.3 else 'weakly coupled'))

print("""
READING
  If the rail duty is ~0, the command is NOT hitting its ceiling and "authority" is not the
  binding constraint -- raising a ceiling cannot add what was never requested.  In that case
  the symptom the operator calls authority is a DELIVERY or a PLANT problem, and the lever
  is whatever makes requested torque turn into wheel motion.""")
