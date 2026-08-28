# -*- coding: utf-8 -*-
"""AUDIO for the CURRENT build (r22/r23 = V112) -- the corpus's 50 Hz ceiling does not apply here.

Every CAN/IMU channel logs at 100 Hz, so nothing above ~49 Hz is visible. The operator reports
grind #1 moved to a HIGHER frequency, and that may be above the ceiling entirely. The rlogs carry
`rawAudioData` PCM, which is not subject to it.

Two questions, and they are different:
  A) SPECTRUM 0-8 kHz, engaged vs manual -- WHAT PITCH is added when LKAS engages?
  B) AM ENVELOPE 0-100 Hz within carrier bands -- at what RATE is that pitch modulated?

(B) matters because a 21 Hz mechanical mode cannot radiate a 21 Hz tone into a cabin (16 m
wavelength). A rough, sticking mechanism instead MODULATES broadband noise at the mode rate.
So "the pitch went up" and "the mode is still at 21 Hz" can BOTH be true -- the carrier moved,
the modulation did not. This separates them.
"""
import os, sys, glob
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # rlog-tools
ROOT = os.path.dirname(HERE)                                          # repo root
sys.path.insert(0, HERE)
RLOGS = os.path.join(ROOT, 'analysis-2020accord', 'rlogs')
SR = 16000
ROUTES = {'r22': '75604b0a432fdc89_00000022--00f57626e0',
          'r23': '75604b0a432fdc89_00000023--fc5f268959'}
CARRIER = [(100, 300), (300, 800), (800, 2000), (2000, 5000), (5000, 7800)]


def read_pcm(prefix, max_seg=None):
    import capnp, zstandard
    try:
        import log_capnp as log  # noqa
    except Exception:
        pass
    segs = sorted(glob.glob(os.path.join(RLOGS, '%s--*--rlog.zst' % prefix)),
                  key=lambda p: int(os.path.basename(p).split('--')[2]))
    if max_seg:
        segs = segs[:max_seg]
    from cereal import log as clog
    out = []
    for p in segs:
        with open(p, 'rb') as fh:
            data = zstandard.ZstdDecompressor().stream_reader(fh).read()
        n = 0
        for evt in clog.Event.read_multiple_bytes(data):
            try:
                if evt.which() != 'rawAudioData':
                    continue
            except Exception:
                continue
            out.append(np.frombuffer(bytes(evt.rawAudioData.data), dtype='<i2'))
            n += 1
        print('    %s  %d audio blocks' % (os.path.basename(p)[-18:], n), flush=True)
    return np.concatenate(out).astype(np.float64) if out else None


def analyse(tag):
    print('  %s:' % tag, flush=True)
    x = read_pcm(ROUTES[tag])
    if x is None or len(x) < SR * 20:
        print('    NO AUDIO / too short'); return
    print('    %d samples = %.1f s at %d Hz' % (len(x), len(x) / SR, SR), flush=True)

    f, P = signal.welch(x - x.mean(), SR, nperseg=16384, noverlap=8192)
    tot = P[(f >= 50) & (f <= 7800)].sum()
    print('\n    A) SPECTRUM -- share of 50-7800 Hz power')
    for lo, hi in CARRIER:
        print('       %5d-%5d Hz   %6.2f %%' % (lo, hi, 100 * P[(f >= lo) & (f <= hi)].sum() / tot))
    top = f[(f >= 50) & (f <= 7800)][np.argsort(P[(f >= 50) & (f <= 7800)])[::-1][:6]]
    print('       strongest lines: %s Hz' % ', '.join('%.0f' % v for v in top))

    print('\n    B) AM ENVELOPE within each carrier -- the MODULATION RATE')
    print('       carrier band        peak mod rate    21-26 Hz share of 5-60 Hz')
    for lo, hi in CARRIER:
        sos = signal.butter(4, [lo / (SR / 2), min(hi / (SR / 2), 0.99)], btype='band', output='sos')
        env = np.abs(signal.hilbert(signal.sosfilt(sos, x)[::4]))
        fe, Pe = signal.welch(env - env.mean(), SR / 4, nperseg=8192, noverlap=4096)
        w = (fe >= 5) & (fe <= 60)
        pk = fe[w][int(np.argmax(Pe[w]))]
        sh = Pe[(fe >= 21) & (fe <= 26)].sum() / Pe[w].sum()
        print('       %5d-%5d Hz      %6.2f Hz          %5.1f %%' % (lo, hi, pk, 100 * sh))


for t in sys.argv[1:] or ['r22']:
    analyse(t)
