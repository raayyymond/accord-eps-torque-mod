#!/usr/bin/env python3
r"""EXTRACT THE ACOUSTIC CHANNEL for routes 97 / 96 / 9e / a4 into `_cache_<tag>/<tag>_audio.npz`.

WHAT IS THERE  [EVIDENCE, decoded from the rlogs this session]
    rawAudioData   20 Hz, 800 int16 samples/block, sampleRate 16000  => CONTINUOUS 16 kHz PCM
    soundPressure  10 Hz, {soundPressure, soundPressureWeightedDb, soundPressureWeighted}
On one 60 s segment of route a4: 958,400 samples = 59.90 s against 59.96 s wall time
(coverage 0.9981), block interval median exactly 800/16000 s, 0 samples at the int16 rail.
=> NYQUIST 8000 Hz.  The ~50 Hz ceiling that binds `rate_f` does not apply to this channel.

WHAT THIS FILE STORES -- features, not raw PCM (15.3 M samples/route is not worth persisting)
    t          feature time, seconds relative to the cache's own `t0_mono`  [same base as `t`]
    tob        third-octave band POWERS, 100 Hz .. 8 kHz                    [the new territory]
    tob_f      the third-octave centre frequencies
    wide       a few wide bands incl. the sub-100 Hz region, for the cross-check against `rate_f`
    wide_lab   their labels
    rms        broadband RMS per frame
    sp_t, sp, sp_db, sp_w    the 10 Hz `soundPressure` stream, verbatim

FRAMING.  1024-sample windows (64 ms, 15.6 Hz resolution -- enough to resolve the 100 Hz
third-octave, which is 89-112 Hz) hopping 256 samples => a **62.5 Hz feature rate**, whose
Nyquist is 31 Hz.  That is deliberate: it must be able to see a 6-12 /s envelope structure,
which a 20 Hz per-block feature rate could not.

TIMEBASE.  Each block's samples are timestamped `logMonoTime + i/16000`; a frame takes the mean
of its samples' times.  Blocks arrive with +-11 % jitter, so a frame spanning a block boundary
carries <10 ms of timing error.  Stated, not hidden.

🛑 NO ANALYSIS HERE.  This file only decodes and stores.  Controls, speed-matching and the
manual arm live in the analysis script, per the standing rule that road noise scales hard with
speed and will manufacture any result if unmatched.
"""
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import rlog_parse  # noqa: E402

RLOGS = ROOT / "analysis-2020accord" / "rlogs"
ROUTES = {
    "r97": ("75604b0a432fdc89_00000097--489d7896b3", "STOCK 1x"),
    "r96": ("75604b0a432fdc89_00000096--57f5183b32", "V102 6x"),
    "r9e": ("75604b0a432fdc89_0000009e--54bb0788af", "V103 6x"),
    "ra4": ("75604b0a432fdc89_000000a4--bdd0c0aa4e", "V104 6x"),
}
SR = 16000
NFFT = 1024
HOP = 256

# third-octave centres, 100 Hz .. 8 kHz (ISO preferred)
TOB_F = np.array([100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600,
                  2000, 2500, 3150, 4000, 5000, 6300, 8000], float)
WIDE = [(5, 15), (15, 21), (21, 28), (28, 40), (40, 60), (60, 100),
        (100, 300), (300, 1000), (1000, 3000), (3000, 8000)]
WIDE_LAB = ["%g-%g" % w for w in WIDE]


def segments(prefix):
    out = []
    i = 0
    while True:
        p = RLOGS / ("%s--%d--rlog.zst" % (prefix, i))
        if not p.exists():
            break
        out.append(p)
        i += 1
    return out


def extract(tag):
    prefix, label = ROUTES[tag]
    segs = segments(prefix)
    cache = ROOT / "analysis-2020accord" / ("_cache_%s" % tag) / ("%s.npz" % tag)
    t0 = float(np.load(cache, allow_pickle=True)["t0_mono"][0])
    print("  %s (%s): %d segments, t0_mono %.3f" % (tag, label, len(segs), t0), flush=True)

    fr_t, fr_tob, fr_wide, fr_rms = [], [], [], []
    sp_t, sp_v, sp_db, sp_w = [], [], [], []
    n_blocks = n_samp = 0
    wall_lo, wall_hi = None, None
    n_clip = 0
    win = np.hanning(NFFT + 1)[:NFFT]
    ff = np.fft.rfftfreq(NFFT, 1 / SR)
    tob_sel = [(ff >= c / 2 ** (1 / 6)) & (ff < c * 2 ** (1 / 6)) for c in TOB_F]
    wide_sel = [(ff >= a) & (ff < b) for a, b in WIDE]

    for si, p in enumerate(segs):
        blocks, btimes = [], []
        for evt in rlog_parse.read_messages(str(p)):
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if w == "rawAudioData":
                a = evt.rawAudioData
                blocks.append(np.frombuffer(bytes(a.data), dtype="<i2"))
                btimes.append(tm)
            elif w == "soundPressure":
                s = evt.soundPressure
                sp_t.append(tm - t0)
                sp_v.append(float(s.soundPressure))
                sp_db.append(float(s.soundPressureWeightedDb))
                sp_w.append(float(s.soundPressureWeighted))
        if not blocks:
            print("     seg %2d: NO AUDIO" % si, flush=True)
            continue
        x = np.concatenate(blocks).astype(np.float64)
        ts = np.concatenate([bt + np.arange(len(b)) / SR for bt, b in zip(btimes, blocks)]) - t0
        n_blocks += len(blocks)
        n_samp += len(x)
        n_clip += int((np.abs(x) >= 32767).sum())
        wall_lo = btimes[0] if wall_lo is None else wall_lo
        wall_hi = btimes[-1] + len(blocks[-1]) / SR
        for s in range(0, len(x) - NFFT + 1, HOP):
            seg = x[s:s + NFFT]
            seg = seg - seg.mean()
            X = np.fft.rfft(seg * win)
            P = (X.conj() * X).real
            fr_t.append(ts[s:s + NFFT].mean())
            fr_tob.append([P[m].sum() for m in tob_sel])
            fr_wide.append([P[m].sum() for m in wide_sel])
            fr_rms.append(np.sqrt((seg ** 2).mean()))
        if si % 4 == 0:
            print("     seg %2d done, frames so far %d" % (si, len(fr_t)), flush=True)

    out = ROOT / "analysis-2020accord" / ("_cache_%s" % tag) / ("%s_audio.npz" % tag)
    np.savez_compressed(
        out, t=np.array(fr_t), tob=np.array(fr_tob, np.float32), tob_f=TOB_F,
        wide=np.array(fr_wide, np.float32), wide_lab=np.array(WIDE_LAB),
        rms=np.array(fr_rms), sp_t=np.array(sp_t), sp=np.array(sp_v),
        sp_db=np.array(sp_db), sp_w=np.array(sp_w),
        meta=np.array([SR, NFFT, HOP, n_blocks, n_samp, n_clip], float))
    dur = n_samp / SR
    wall = (wall_hi - wall_lo) if wall_hi else float("nan")
    print("  %s AUDIT: %d blocks · %d samples = %.1f s audio · wall %.1f s · COVERAGE %.4f · "
          "clipped %d · frames %d @ %.2f Hz · soundPressure %d"
          % (tag, n_blocks, n_samp, dur, wall, dur / wall if wall else float("nan"),
             n_clip, len(fr_t), SR / HOP, len(sp_t)), flush=True)
    return dict(tag=tag, blocks=n_blocks, samples=n_samp, dur=dur, wall=wall,
                cov=dur / wall if wall else float("nan"), clip=n_clip, frames=len(fr_t))


if __name__ == "__main__":
    tags = sys.argv[1:] or list(ROUTES)
    print("=" * 100)
    print("AUDIO EXTRACTION + COVERAGE AUDIT")
    print("=" * 100)
    rep = [extract(t) for t in tags]
    print()
    print("%6s %9s %12s %10s %10s %10s %9s %9s" %
          ('route', 'blocks', 'samples', 'audio s', 'wall s', 'COVERAGE', 'clipped', 'frames'))
    for r in rep:
        print("%6s %9d %12d %10.1f %10.1f %10.4f %9d %9d"
              % (r['tag'], r['blocks'], r['samples'], r['dur'], r['wall'], r['cov'],
                 r['clip'], r['frames']))
