#!/usr/bin/env python3
"""extract/extract_audio_cache.py -- per-route AUDIO spectrogram + aligned covariates.

The kit's microphone audit (`verify/audit_microphone_capability.py`) concluded the mic "can NEVER name a
frequency". That was correct FOR `soundPressure` -- a 10 Hz scalar RMS. It missed `rawAudioData`,
which carries 16 kHz mono int16 PCM in 50 ms blocks and is present from route 77 onward.

Measured on route a6 segment 10: gapless (60.00 s of samples in a 59.94 s span, no dt > 75 ms),
peak 11950/32767 (no clipping), and NO codec high-pass -- 5-80 Hz is the loudest region.
=> a genuine spectrometer, 5 Hz .. 8 kHz, on every route since 77.

Caches, per route: one row per audio window, holding the PSD over 0-500 Hz at ~1 Hz resolution plus
the covariates needed for speed-matched engaged/manual contrasts.
"""
import sys, glob, re
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
# repo reorg 2026-08-26 moved rlog_parse into rlog-tools/lib/ -- the old single-dir insert
# stopped resolving it. Put the kit root AND every code subfolder on the path.
for _p in [ROOT / "rlog-tools"] + [d for d in (ROOT / "rlog-tools").iterdir() if d.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from rlog_parse import read_messages                                    # noqa: E402

RLOG = ROOT / "analysis-2020accord" / "rlogs"
SR, NFFT, HOP = 16000, 16384, 8192          # 1.024 s window, 0.512 s hop, 0.977 Hz bins
FMAX = 500.0                                 # keep 0-500 Hz: fundamental + first harmonics
HIBANDS = [(500, 750), (750, 1000), (1000, 1500), (1500, 2000), (2000, 3000),
           (3000, 4000), (4000, 5500), (5500, 8000)]   # music-detection bands


def route_segments(rid):
    fs = glob.glob(str(RLOG / f"*_000000{rid}--*--rlog.zst"))
    key = lambda p: int(re.search(r"--(\d+)--rlog", p).group(1))
    return sorted(fs, key=key)


def extract(rid, out):
    rows_psd, rows_cov, rows_hi = [], [], []
    win = np.hanning(NFFT)
    for si, f in enumerate(route_segments(rid)):
        at, ablk = [], []
        ct, cv, ceng, cang, ctq = [], [], [], [], []
        for e in read_messages(f):
            try:
                w = e.which()
            except Exception:
                continue
            if w == "rawAudioData":
                at.append(e.logMonoTime)
                ablk.append(np.frombuffer(bytes(e.rawAudioData.data), "<i2"))
            elif w == "carState":
                cs = e.carState
                ct.append(e.logMonoTime); cv.append(cs.vEgo)
                cang.append(cs.steeringAngleDeg); ctq.append(cs.steeringTorque)
            elif w == "carControl":
                ceng.append((e.logMonoTime, bool(e.carControl.latActive)))
        if len(at) < 40 or len(ct) < 100:
            continue
        at = np.asarray(at, float) / 1e9
        x = np.concatenate(ablk).astype(np.float64)
        t0 = at[0]
        ts = t0 + np.arange(len(x)) / SR                      # blocks are gapless (verified)
        ct = np.asarray(ct, float) / 1e9
        cv, cang, ctq = map(lambda a: np.asarray(a, float), (cv, cang, ctq))
        et = np.asarray([p[0] for p in ceng], float) / 1e9
        ev = np.asarray([p[1] for p in ceng], float)
        # angle rate from the 100 Hz carState grid
        drate = np.gradient(cang, ct)
        for i in range(0, len(x) - NFFT, HOP):
            seg = x[i:i + NFFT]
            tc = ts[i + NFFT // 2]
            if tc < ct[0] or tc > ct[-1]:
                continue
            P = np.abs(np.fft.rfft((seg - seg.mean()) * win)) ** 2
            fr = np.fft.rfftfreq(NFFT, 1 / SR)
            rows_psd.append(P[fr <= FMAX].astype(np.float32))
            # -- MUSIC-DETECTION FEATURES ------------------------------------------------
            # Music lives where road/mechanical noise does not: harmonic structure and fast
            # temporal modulation in 200 Hz - 4 kHz.  Road noise is low-frequency and stationary.
            hb = [float(P[(fr >= a) & (fr < b)].mean()) for a, b in HIBANDS]
            lo = float(P[(fr >= 20) & (fr < 120)].mean())
            mid = float(P[(fr >= 300) & (fr < 4000)].mean())
            sub = P[(fr >= 100) & (fr < 4000)]
            flat = float(np.exp(np.log(sub + 1e-12).mean()) / (sub.mean() + 1e-12))  # 1=noise, 0=tonal
            rows_hi.append(hb + [np.log10(mid / lo + 1e-12), flat])
            m = (ct >= tc - 0.5) & (ct <= tc + 0.5)
            eg = ev[(et >= tc - 0.5) & (et <= tc + 0.5)]
            rows_cov.append((tc, si,
                             float(cv[m].mean()) if m.any() else np.nan,
                             float(eg.mean()) if len(eg) else np.nan,
                             float(np.abs(drate[m]).mean()) if m.any() else np.nan,
                             float(np.abs(ctq[m]).mean()) if m.any() else np.nan,
                             float(np.abs(cang[m]).mean()) if m.any() else np.nan))
        print(f"  {rid} seg {si:2d}: {len(rows_psd)} windows", flush=True)
    fr = np.fft.rfftfreq(NFFT, 1 / SR)
    np.savez_compressed(out, psd=np.array(rows_psd, np.float32),
                        hi=np.array(rows_hi, np.float32),
                        hicols=np.array([f"{a}-{b}" for a, b in HIBANDS] + ["logMidLo", "flatness"]),
                        cov=np.array(rows_cov, np.float64), freq=fr[fr <= FMAX].astype(np.float32),
                        cols=np.array(["t", "seg", "vEgo", "eng", "absRate", "absTq", "absAng"]))
    print(f"{rid}: wrote {out}  windows={len(rows_psd)}", flush=True)


if __name__ == "__main__":
    for rid in sys.argv[1:]:
        extract(rid, ROOT / "analysis-2020accord" / f"_audio_r{rid}.npz")
