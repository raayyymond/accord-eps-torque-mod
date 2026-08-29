# -*- coding: utf-8 -*-
"""Can openpilot's lateral loop AFFORD the +16.4 deg of engaged-only lag V184 adds at 1 Hz?

V184 retunes an ENGAGED-GATED section on the torque-fed assist path.  That path is part of the
plant openpilot controls, so its phase enters openpilot's loop -- the open question is by how
much, and whether there is margin to spare.

A closed-loop resonant peak gives the margin without needing the open-loop transfer:
    Mp = peak of |closed loop|        PM ~= 2 * arcsin( 1 / (2 * Mp) )
Estimate the closed loop from openpilot's own command to the resulting steering angle, on
ENGAGED segments, and read the peak.

CONTROLS, because a bare spectral peak proves nothing:
  * the same estimate on MANUAL segments -- openpilot is not closing the loop there, so any
    "peak" found in manual is an artifact of the estimator or of the road, not of the loop;
  * a phase-shuffled surrogate of the command, which destroys the causal relationship while
    keeping both spectra.
"""
import os, sys, math
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, NPS = 100.0, 512
ROUTES = ['r77', 'r21', 'ra6', 'r1e', 'ra4', 'r7e', 'r7f', 'r95', 'r81', 'r82',
          'r78', 'r79', 'r85', 'r96', 'r9e', 'ra5', 'r22', 'r24', 'r97']


def segs(tag, engaged):
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not os.path.exists(p):
        return []
    z = np.load(p, allow_pickle=True)
    need = ('cc_lat', 'cs_ang')
    if any(k not in z.files for k in need):
        return []
    cmd_key = 'cc_req' if 'cc_req' in z.files else ('sc_tq' if 'sc_tq' in z.files else None)
    if cmd_key is None:
        return []
    lat = np.asarray(z['cc_lat']).astype(float)
    ang = np.asarray(z['cs_ang']).astype(float)
    cmd = np.asarray(z[cmd_key]).astype(float)
    n = min(len(lat), len(ang), len(cmd))
    lat, ang, cmd = lat[:n], ang[:n], cmd[:n]
    ok = ((lat > 0.5) if engaged else (lat <= 0.5)) & np.isfinite(ang) & np.isfinite(cmd)
    d = np.diff(np.concatenate(([0], ok.view(np.int8), [0])))
    out = []
    for i, j in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
        if (j - i) >= 2 * NPS and np.std(ang[i:j]) > 0 and np.std(cmd[i:j]) > 0:
            out.append((cmd[i:j], ang[i:j]))
    return out


def closed_loop(pairs, shuffle=False, seed=0):
    """|Ang/Cmd| averaged over segments -- the closed-loop magnitude estimate."""
    rng = np.random.default_rng(seed)
    acc, f = [], None
    for cmd, ang in pairs:
        c = cmd - cmd.mean()
        a = ang - ang.mean()
        if shuffle:
            C = np.fft.rfft(c)
            C = np.abs(C) * np.exp(1j * rng.uniform(0, 2 * np.pi, len(C)))
            c = np.fft.irfft(C, n=len(c))
        f, Pcc = signal.welch(c, FS, nperseg=NPS, noverlap=NPS // 2)
        _, Pca = signal.csd(c, a, FS, nperseg=NPS, noverlap=NPS // 2)
        m = Pcc > 0
        h = np.zeros_like(Pcc)
        h[m] = np.abs(Pca[m]) / Pcc[m]
        acc.append(h)
    return f, np.median(np.asarray(acc), 0)


eng = [s for t in ROUTES for s in segs(t, True)]
man = [s for t in ROUTES for s in segs(t, False)]
print('segments: engaged %d   manual %d' % (len(eng), len(man)))
if len(eng) < 6:
    print('too few engaged segments'); sys.exit(0)

BAND = (0.3, 4.0)          # where a lateral controller closes
f, He = closed_loop(eng)
_, Hm = closed_loop(man) if len(man) >= 6 else (None, None)
_, Hs = closed_loop(eng, shuffle=True, seed=3)
sel = (f >= BAND[0]) & (f <= BAND[1])
lo = (f >= 0.15) & (f <= 0.4)      # low-frequency reference (DC-ish gain)


def peak(H):
    if H is None:
        return None
    ref = np.median(H[lo])
    if ref <= 0:
        return None
    k = np.argmax(H[sel] / ref)
    return float((H[sel] / ref)[k]), float(f[sel][k])


for nm, H in (('ENGAGED (loop closed)', He), ('manual  (loop OPEN)', Hm),
              ('phase-shuffled cmd  ', Hs)):
    r = peak(H)
    print('  %-22s %s' % (nm, 'n/a' if r is None else
                          'Mp = %.3f at %.2f Hz' % r))

r = peak(He)
rm = peak(Hm)
rs = peak(Hs)
print('')
if r is None:
    print('no usable engaged estimate'); sys.exit(0)
Mp = r[0]
ctrl_ok = ((rm is None or Mp > rm[0] * 1.15) and (rs is None or Mp > rs[0] * 1.15))
print('CONTROLS: engaged peak must EXCEED both the manual and the shuffled peak to mean anything.')
print('  -> %s' % ('controls PASS, the peak is a property of the closed loop'
                   if ctrl_ok else
                   '** CONTROLS FAIL -- the peak is not distinguishable from the estimator/road. **'))
print('')
if not ctrl_ok:
    print('=> No usable phase-margin estimate. The question of whether openpilot can afford')
    print('   +16.4 deg stays OPEN, and V184 keeps it as a pre-registered risk.')
else:
    if Mp <= 0.5:
        print('peak below 0.5 -- formula not applicable')
    else:
        pm = math.degrees(2 * math.asin(min(1.0, 1.0 / (2 * Mp))))
        print('Mp = %.3f  =>  phase margin ~ %.1f deg' % (Mp, pm))
        print('V184 spends +16.4 deg of that at 1 Hz.')
        print('  remaining ~ %.1f deg  ->  %s' % (pm - 16.4,
              'COMFORTABLE' if pm - 16.4 > 30 else
              'THIN -- command oscillation is a real risk' if pm - 16.4 > 0 else
              'NEGATIVE -- V184 would be expected to destabilise openpilot'))
