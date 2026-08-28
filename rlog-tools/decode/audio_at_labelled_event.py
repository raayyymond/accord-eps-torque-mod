# -*- coding: utf-8 -*-
"""Does the MICROPHONE see the operator's own LABELLED event?

He named route 23, segment 7, 21:46:48 as "an exact instance" of the peak-turn oscillation;
it sits at t = 445.6-448.2 s. That is the only acoustically-labelled moment in the corpus.

If the mic shows nothing there, the acoustic instrument cannot see symptoms this operator
reports, and every acoustic null in this session is uninformative. If it shows something,
that spectrum IS the signature to hunt on other drives.

Controls, because a 2.6 s window will show something by chance:
  - MATCHED controls from the same drive at similar speed and |angle|, engaged
  - the excess is reported against their MEDIAN, and against their SPREAD, so a line has to
    clear what ordinary moments already do
"""
import os, sys, glob
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
RLOGS = os.path.join(ROOT, 'analysis-2020accord', 'rlogs')
CACHE = os.path.join(ROOT, 'analysis-2020accord', '_scratch', 'cache')
SR = 16000
PREFIX = '75604b0a432fdc89_00000023--fc5f268959'
T0, T1 = 445.6, 448.2


def read_pcm_timed(prefix):
    import zstandard
    from cereal import log as clog
    segs = sorted(glob.glob(os.path.join(RLOGS, '%s--*--rlog.zst' % prefix)),
                  key=lambda p: int(os.path.basename(p).split('--')[2]))
    blocks, times = [], []
    for p in segs:
        with open(p, 'rb') as fh:
            data = zstandard.ZstdDecompressor().stream_reader(fh).read()
        for evt in clog.Event.read_multiple_bytes(data):
            try:
                if evt.which() != 'rawAudioData':
                    continue
            except Exception:
                continue
            blocks.append(np.frombuffer(bytes(evt.rawAudioData.data), dtype='<i2'))
            times.append(evt.logMonoTime * 1e-9)
    return blocks, np.array(times)


blocks, bt = read_pcm_timed(PREFIX)
z = np.load(os.path.join(CACHE, 'r23', 'r23.npz'), allow_pickle=True)
t = np.asarray(z['t']).astype(float)
lat = np.asarray(z['cc_lat']).astype(float)
v = np.asarray(z['cs_v']).astype(float)
ang = np.asarray(z['ang']).astype(float)
t0 = float(np.asarray(z['t0_mono']).ravel()[0])
at = bt - t0
x = np.concatenate([b.astype(float) for b in blocks])
start = np.concatenate([[0], np.cumsum([len(b) for b in blocks])[:-1]])
samp_t = np.interp(np.arange(len(x)), start, at)
print('  %d blocks, audio span %.1f-%.1f s' % (len(blocks), at.min(), at.max()))

NF = 8192
i0, i1 = int(np.searchsorted(samp_t, T0)), int(np.searchsorted(samp_t, T1))
print('  EVENT window: samples %d-%d = %.2f s of audio' % (i0, i1, (i1 - i0) / SR))
if i1 - i0 < NF:
    print('  event shorter than one FFT window -- using %d samples' % (i1 - i0))
nf = min(NF, i1 - i0)
f, PE = signal.welch(x[i0:i1] - x[i0:i1].mean(), SR, nperseg=nf)

# event's driving state
j = int(np.searchsorted(t, (T0 + T1) / 2))
ev_v, ev_a = v[j] * 3.6, abs(ang[j])
print('  event state: %.1f km/h, |ang| %.1f deg' % (ev_v, ev_a))

ctl = []
for a in range(0, len(x) - nf, nf // 2):
    tb = samp_t[a + nf // 2]
    if abs(tb - (T0 + T1) / 2) < 8:
        continue
    k = int(np.searchsorted(t, tb))
    if k <= 0 or k >= len(t) or lat[k] <= 0.5:
        continue
    if abs(v[k] * 3.6 - ev_v) > 15 or abs(abs(ang[k]) - ev_a) > 25:
        continue
    seg = x[a:a + nf]
    ctl.append(signal.welch(seg - seg.mean(), SR, nperseg=nf)[1])
print('  %d matched engaged controls (speed +-15 km/h, |ang| +-25 deg)' % len(ctl))
if len(ctl) < 10:
    print('  TOO FEW CONTROLS -- widening')
    ctl = []
    for a in range(0, len(x) - nf, nf // 2):
        tb = samp_t[a + nf // 2]
        if abs(tb - (T0 + T1) / 2) < 8:
            continue
        k = int(np.searchsorted(t, tb))
        if k <= 0 or k >= len(t) or lat[k] <= 0.5 or v[k] < 1.0:
            continue
        seg = x[a:a + nf]
        ctl.append(signal.welch(seg - seg.mean(), SR, nperseg=nf)[1])
    print('  %d engaged controls (speed/angle unmatched)' % len(ctl))
C = np.array(ctl)
med = np.median(C, axis=0)
p95 = np.percentile(C, 95, axis=0)
D = 10 * np.log10(np.maximum(PE, 1e-30) / np.maximum(med, 1e-30))
over = 10 * np.log10(np.maximum(PE, 1e-30) / np.maximum(p95, 1e-30))

print('\n  EVENT minus CONTROL-MEDIAN (dB), and minus CONTROL-p95 (the honest bar):')
print('     band            vs median   vs p95')
for lo, hi in ((20, 50), (50, 60), (60, 80), (80, 120), (120, 200), (200, 300),
               (300, 800), (800, 2000), (2000, 5000), (5000, 7800)):
    w = (f >= lo) & (f <= hi)
    print('     %5d-%5d Hz    %+6.2f     %+6.2f' % (lo, hi, np.median(D[w]), np.median(over[w])))
w = (f >= 20) & (f <= 7800)
ff, oo = f[w], over[w]
top = np.argsort(oo)[::-1][:10]
print('\n  lines that clear the control p95 by the most:')
for k2 in sorted(top, key=lambda k2: ff[k2]):
    print('     %7.0f Hz   %+5.1f dB over p95' % (ff[k2], oo[k2]))
print('\n  => %s' % ('THE MIC SEES THE EVENT -- this spectrum is the signature to hunt'
                     if np.max(oo) > 3 else
                     'THE MIC DOES NOT SEE IT -- acoustic nulls in this corpus are uninformative'))
