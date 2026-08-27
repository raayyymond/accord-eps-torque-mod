#!/usr/bin/env python3
"""extract/extract_audio_flux.py -- LEVEL-BLIND music features, second pass over the raw PCM.

Why a second pass: a level-based detector (2-3 kHz energy vs a per-speed floor) works at standstill
but FAILS at highway speed -- wind noise at 2-3 kHz masks music, and the detector degenerates into a
speed filter (route a6: "music" class p50 29.7 km/h vs "clean" 94.9, with the 2-3 kHz medians only
0.4 dB apart).  The speed-blind control (partial-centroid movement) showed no separation either.

SPECTRAL FLUX is blind to absolute level: it measures how fast the spectrum CHANGES.  Music has
note onsets and beats; road noise, wind and a mechanical resonance are stationary.  Computed on
LOG magnitudes so a loud passage and a quiet one give the same flux.

  frame 512 samples (32 ms), hop 256 (16 ms), band 300-4000 Hz
  flux      = mean over frames of the positive half-wave rectified frame-to-frame log-mag change
  modpeak   = fraction of the mid-band envelope's modulation power in 1-8 Hz (the beat/onset band)

GROUND TRUTH for calibration: standstill windows (vEgo < 2 km/h) have no wind and no tyre noise, so
their 2-3 kHz level cleanly labels music (>=75 dB) vs silence (<=50 dB).  Both features are scored
against that label before being used at speed.
"""
import sys, glob, re
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "rlog-tools"))
from rlog_parse import read_messages                                    # noqa: E402

RLOG = ROOT / "analysis-2020accord" / "rlogs"
SR, NFFT, HOP = 16000, 16384, 8192
FR, FH = 512, 256


def flux_features(x):
    n = 1 + (len(x) - FR) // FH
    w = np.hanning(FR)
    S = np.stack([np.abs(np.fft.rfft((x[i*FH:i*FH+FR] - x[i*FH:i*FH+FR].mean()) * w)) for i in range(n)])
    f = np.fft.rfftfreq(FR, 1 / SR)
    m = (f >= 300) & (f <= 4000)
    L = 20 * np.log10(S[:, m] + 1e-6)
    d = np.diff(L, axis=0)
    flux = float(np.maximum(d, 0).mean())                      # level-blind onset strength
    env = L.mean(axis=1)
    env = env - env.mean()
    P = np.abs(np.fft.rfft(env * np.hanning(len(env)))) ** 2
    mf = np.fft.rfftfreq(len(env), FH / SR)
    band = (mf >= 1.0) & (mf <= 8.0)
    modpeak = float(P[band].sum() / (P[mf >= 0.3].sum() + 1e-12))
    return flux, modpeak


def run(rid):
    fs = sorted(glob.glob(str(RLOG / f"*_000000{rid}--*--rlog.zst")),
                key=lambda p: int(re.search(r"--(\d+)--rlog", p).group(1)))
    rows = []
    for si, f in enumerate(fs):
        at, ablk = [], []
        for e in read_messages(f):
            try:
                if e.which() != "rawAudioData":
                    continue
            except Exception:
                continue
            at.append(e.logMonoTime)
            ablk.append(np.frombuffer(bytes(e.rawAudioData.data), "<i2"))
        if len(at) < 40:
            continue
        x = np.concatenate(ablk).astype(np.float64)
        t0 = np.asarray(at, float)[0] / 1e9
        ts = t0 + np.arange(len(x)) / SR
        for i in range(0, len(x) - NFFT, HOP):
            fl, mp = flux_features(x[i:i + NFFT])
            rows.append((ts[i + NFFT // 2], si, fl, mp))
        print(f"  {rid} seg {si}: {len(rows)}", flush=True)
    np.savez_compressed(ROOT / "analysis-2020accord" / f"_audioflux_r{rid}.npz",
                        rows=np.array(rows, np.float64),
                        cols=np.array(["t", "seg", "flux", "modpeak"]))
    print(f"{rid}: done {len(rows)}", flush=True)


if __name__ == "__main__":
    for r in sys.argv[1:]:
        run(r)
