# -*- coding: utf-8 -*-
"""Is the 7-9 Hz energy COMMANDED, or MANUFACTURED downstream?

This is the missing link in V121's rationale. The LKAS lane is a ~1-5 Hz low-pass
(reference-accord-lkas-lane-is-a-lowpass), so openpilot's command should carry no 7.8 Hz
content. If the wheel oscillates at 7.8 Hz while the command is clean there, the energy is
GENERATED inside the loop -- and the harmonic result says the generator is a hard
nonlinearity, i.e. the Coulomb relay that V121 softens.

If instead the command DOES carry 7-9 Hz and it is coherent with the response, the energy
is commanded, V121 is aimed at the wrong thing, and the lever is upstream.

Measured on the OSCILLATING windows only, where the effect is largest, with a shuffled
control and the ROUTE as the bootstrap unit.
"""
import numpy as np, os
from scipy import signal

FS, NW = 100.0, 256
ROUTES = ['21', '22', '23', '77', '78', '79', '7e', '7f', '85', '95', '96', '9e', 'a4', 'a5', 'a6', '1e']


def route(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    need = ('cs_rate', 'cc_lat', 'cs_v')
    if any(k not in z.files for k in need):
        return None
    cmdk = 'cc_req' if 'cc_req' in z.files else ('co_tqcan' if 'co_tqcan' in z.files else None)
    if cmdk is None:
        return None
    rate, lat, v = [np.asarray(z[k]).astype(float) for k in need]
    cmd = np.asarray(z[cmdk]).astype(float)
    n = min(len(rate), len(cmd))
    rate, cmd, lat, v = rate[:n], cmd[:n], lat[:n], v[:n]
    m = (lat > 0.5) & (v > 1.0)
    W = []
    for a in range(0, n - NW, NW // 2):
        b = a + NW
        if m[a:b].mean() < 0.99:
            continue
        if np.std(cmd[a:b]) < 1e-9:
            continue
        f, Pr = signal.welch(rate[a:b] - rate[a:b].mean(), FS, nperseg=NW)
        _, Pc = signal.welch(cmd[a:b] - cmd[a:b].mean(), FS, nperseg=NW)
        W.append((f, Pr, Pc, cmd[a:b], rate[a:b]))
    if len(W) < 30:
        return None
    f = W[0][0]
    e = np.array([w[1][(f >= 6) & (f <= 9)].sum() for w in W])
    top = np.argsort(e)[-max(int(0.05 * len(e)), 5):]
    lo = (f >= 0.5) & (f <= 3)
    b69 = (f >= 6) & (f <= 9)
    # command spectral SHAPE: how much of the command's own power is at 6-9 vs 0.5-3 Hz
    cr = np.median([W[i][2][b69].sum() / max(W[i][2][lo].sum(), 1e-30) for i in top])
    rr = np.median([W[i][1][b69].sum() / max(W[i][1][lo].sum(), 1e-30) for i in top])
    # coherence at 6-9 Hz, real vs shuffled-pairing control
    coh, shuf = [], []
    rng = np.random.default_rng(0)
    for i in top:
        _, C = signal.coherence(W[i][3], W[i][4], FS, nperseg=NW // 2)
        fc = signal.coherence(W[i][3], W[i][4], FS, nperseg=NW // 2)[0]
        coh.append(np.mean(C[(fc >= 6) & (fc <= 9)]))
        j = top[rng.integers(0, len(top))]
        _, C2 = signal.coherence(W[i][3], W[j][4], FS, nperseg=NW // 2)
        shuf.append(np.mean(C2[(fc >= 6) & (fc <= 9)]))
    return cr, rr, np.median(coh), np.median(shuf), len(top)


rows = []
for r in ROUTES:
    s = route(r)
    if s:
        rows.append((r,) + s)
print("  on OSCILLATING windows only:  6-9 Hz power as a fraction of 0.5-3 Hz power\n")
print("  route   COMMAND 6-9/0.5-3   RESPONSE 6-9/0.5-3   coh(6-9)   shuffled   n_win")
for r, cr, rr, c, s, n in rows:
    print("   r%-4s      %10.5f          %10.5f       %6.3f     %6.3f    %4d" % (r, cr, rr, c, s, n))

cr = np.array([x[1] for x in rows])
rr = np.array([x[2] for x in rows])
co = np.array([x[3] for x in rows])
sh = np.array([x[4] for x in rows])
rng = np.random.default_rng(0)
print("\n  %d routes." % len(rows))
print("  median COMMAND  6-9/0.5-3 ratio : %.5f" % np.median(cr))
print("  median RESPONSE 6-9/0.5-3 ratio : %.5f" % np.median(rr))
print("  => the response carries %.1fx more relative 6-9 Hz content than the command"
      % (np.median(rr) / max(np.median(cr), 1e-30)))
bs = [np.median(rng.choice(co, len(co))) - np.median(rng.choice(sh, len(sh))) for _ in range(4000)]
print("\n  coherence(command, rate) at 6-9 Hz : %.3f   shuffled control %.3f   diff %.3f  CI [%.3f, %.3f]"
      % (np.median(co), np.median(sh), np.median(co) - np.median(sh),
         np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
print("\n  ⇒ %s" % ("COMMANDED -- the command carries the band and drives it"
                    if np.median(cr) > np.median(rr) * 0.5 else
                    "MANUFACTURED DOWNSTREAM -- the command is comparatively clean at 6-9 Hz,\n"
                    "     so the energy is generated inside the loop. V121's premise holds."))
