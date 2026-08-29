# -*- coding: utf-8 -*-
"""THE DECISIVE ACOUSTIC TEST: engaged-vs-manual spectrum, above the 50 Hz ceiling.

r22 audio showed its strongest lines at 51-56 Hz, just above the Nyquist of every CAN/IMU
channel -- exactly where the operator's "grind #1 moved higher" would have been invisible.
But that was the WHOLE drive, so it could equally be engine or road.

This aligns the PCM to the CAN timebase using each audio event's logMonoTime against the
cache's t0_mono, then splits on cc_lat. Engine and road noise appear in BOTH arms and
cancel; anything LKAS-specific does not.

Reports the engaged-minus-manual excess across 20-2000 Hz so the answer is not pre-committed
to a band, plus a speed-matched control -- because engaged driving is not a random sample of
speeds, and a speed difference alone would move engine and road noise.
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

# Route prefixes are RESOLVED FROM THE RLOG FILENAMES, not hardcoded.  The old
#   ROUTES = {'r22': ..., 'r23': ...}
# meant every new drive needed this file edited before its audio could be read, and a stale
# entry would silently analyse the wrong drive.  Verified: this resolver reproduces the two
# hardcoded values exactly (r22 -> 75604b0a432fdc89_00000022--00f57626e0).
_RE = __import__('re')


def route_prefix(tag):
    """'r24' or '24' -> the rlog prefix, or None if that route has no rlogs on disk."""
    key = tag[1:] if tag.startswith('r') else tag
    for p in sorted(glob.glob(os.path.join(RLOGS, '*rlog.zst'))):
        parts = os.path.basename(p).split('--')
        m = _RE.match(r'.*_0*([0-9a-f]+)$', parts[0])
        if m and (m.group(1).lstrip('0') or '0') == key.lstrip('0'):
            return '%s--%s' % (parts[0], parts[1])
    return None


def available():
    """Routes that have BOTH rlogs and a cache -- the ones this tool can actually run on."""
    out = []
    for d in sorted(glob.glob(os.path.join(CACHE, 'r*'))):
        if not os.path.isdir(d):
            continue
        tag = os.path.basename(d)
        if route_prefix(tag):
            out.append(tag)
    return out


class _Routes(dict):
    """Backwards-compatible mapping: ROUTES['r24'] resolves on demand."""

    def __missing__(self, k):
        p = route_prefix(k)
        if p is None:
            raise KeyError('%s: no rlogs found under %s' % (k, RLOGS))
        return p


ROUTES = _Routes()


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


def run(tag):
    print('\n=== %s ===' % tag, flush=True)
    blocks, bt = read_pcm_timed(ROUTES[tag])
    if not blocks:
        print('  no audio'); return
    z = np.load(os.path.join(CACHE, tag, '%s.npz' % tag), allow_pickle=True)
    t = np.asarray(z['t']).astype(float)
    lat = np.asarray(z['cc_lat']).astype(float)
    v = np.asarray(z['cs_v']).astype(float)
    t0 = float(np.asarray(z['t0_mono']).ravel()[0])
    at = bt - t0                                     # audio block start, cache timebase
    print('  %d audio blocks, span %.1f-%.1f s ; cache t span %.1f-%.1f s'
          % (len(blocks), at.min(), at.max(), t.min(), t.max()), flush=True)

    # blocks are ~800 samples (~50 ms); concatenate and window at 8192 for resolution
    NF = 8192
    x_all = np.concatenate([b.astype(float) for b in blocks])
    n_per = np.array([len(b) for b in blocks])
    start = np.concatenate([[0], np.cumsum(n_per)[:-1]])
    # sample index -> cache time, by interpolating block start times
    samp_t = np.interp(np.arange(len(x_all)), start, at)
    # ENGAGED-ONLY case-control: the engaged/manual split is hopelessly speed-confounded on
    # this route (52.8 vs 11.5 km/h median), which produces a uniform +10 dB across 20-2000 Hz.
    # Instead: within ENGAGED driving only, contrast windows with HIGH vs LOW 21-26 Hz
    # steering-rate content, matched on speed. Road and engine noise are then common to both arms.
    rate = np.asarray(z['cs_rate']).astype(float)
    FSC, NWC = 100.0, 256
    rows = []
    for a in range(0, len(x_all) - NF, NF // 2):
        tb = samp_t[a + NF // 2]
        i = int(np.searchsorted(t, tb))
        if i <= NWC or i >= len(t) - NWC or v[i] < 1.0 or lat[i] <= 0.5:
            continue
        seg_r = rate[i - NWC // 2:i + NWC // 2]
        if len(seg_r) < NWC or not np.isfinite(seg_r).all():
            continue
        fr, Pr = signal.welch(seg_r - seg_r.mean(), FSC, nperseg=NWC)
        g = Pr[(fr >= 21) & (fr <= 26)].sum() / max(Pr[(fr >= 1) & (fr <= 45)].sum(), 1e-30)
        seg = x_all[a:a + NF]
        f, P = signal.welch(seg - seg.mean(), SR, nperseg=NF)
        rows.append((g, v[i] * 3.6, P))
    if len(rows) < 100:
        print('  too few engaged windows: %d' % len(rows)); return
    g = np.array([r[0] for r in rows]); vv = np.array([r[1] for r in rows])
    hi_i = g >= np.percentile(g, 80)
    lo_i = g <= np.percentile(g, 40)
    # speed-match the two arms
    band = (np.percentile(vv[hi_i], 20), np.percentile(vv[hi_i], 80))
    H = [r[2] for r, m in zip(rows, hi_i) if m and band[0] <= r[1] <= band[1]]
    L = [r[2] for r, m in zip(rows, lo_i) if m and band[0] <= r[1] <= band[1]]
    print('  ENGAGED-ONLY, speed-matched %.0f-%.0f km/h: high-grind %d vs low-grind %d windows'
          % (band[0], band[1], len(H), len(L)))
    if len(H) < 30 or len(L) < 30:
        print('  too few after matching'); return
    D = 10 * np.log10(np.maximum(np.median(np.array(H), axis=0), 1e-30) /
                      np.maximum(np.median(np.array(L), axis=0), 1e-30))
    print('')
    print('  HIGH-GRIND minus LOW-GRIND audio excess (dB), engaged only, speed-matched:')
    for lo, hi in ((20, 50), (50, 60), (60, 80), (80, 120), (120, 200), (200, 300),
                   (300, 800), (800, 2000), (2000, 5000)):
        w = (f >= lo) & (f <= hi)
        print('     %5d-%5d Hz   %+6.2f dB' % (lo, hi, np.median(D[w])))
    w = (f >= 20) & (f <= 3000)
    ff, dd = f[w], D[w]
    top = np.argsort(dd)[::-1][:8]
    print('  strongest grind-specific lines: %s'
          % ', '.join('%.0f Hz %+.1f' % (ff[k2], dd[k2]) for k2 in sorted(top, key=lambda k2: ff[k2])))


_args = [a for a in sys.argv[1:] if not a.startswith('--')]
if '--list' in sys.argv[1:]:
    av = available()
    print('  routes with BOTH rlogs and a cache (%d): %s' % (len(av), ' '.join(av)))
    print('  usage: python rlog-tools/decode/audio_engaged_vs_manual.py <route> [<route> ...]')
else:
    for t_ in _args or ['r22']:
        try:
            run(t_)
        except KeyError as e:
            print('  %s' % e)
            print('  run with --list to see which routes are available.')
