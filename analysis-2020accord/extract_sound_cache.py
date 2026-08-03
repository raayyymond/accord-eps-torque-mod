#!/usr/bin/env python3
"""extract_sound_cache.py -- the comma's MICROPHONE level, the only instrument with NO 50 Hz ceiling.

WHY THIS EXISTS. Both the EPS CAN grid (100.00 Hz) and the comma IMU (101.02 Hz) have a Nyquist of
~50 Hz. If the operator's felt highway vibration is genuinely ABOVE 50 Hz, every vibration
measurement in this kit is structurally blind to it and a null means nothing.

`soundPressure` is computed on the device from audio sampled at ~16-48 kHz and logged at 10 Hz as a
LEVEL. So it cannot give a spectrum, but it CAN answer "is there more acoustic energy during the
maneuver than during a speed-matched control" with no frequency ceiling at all. Grind #2 was
described as *"makes the entire car vibrate, almost like I have a subwoofer"* -- an audible event.

Fields (this fork's schema):
    soundPressure            linear, un-weighted   <- USE THIS for low-frequency content
    soundPressureWeighted    A-weighted linear
    soundPressureWeightedDb  A-weighted dB SPL

🛑 A-WEIGHTING IS THE TRAP. The A curve is -30 dB at 50 Hz and -19 dB at 100 Hz, so
`soundPressureWeightedDb` deliberately SUPPRESSES exactly the band in question. The un-weighted
`soundPressure` is the primary channel here and the weighted one is kept only as a contrast: a rise
in un-weighted with no rise in weighted is evidence the energy is LOW-frequency.

⚠ ROAD AND WIND NOISE SCALE STEEPLY WITH SPEED, so any comparison MUST be speed-matched. The route
atlas' maneuver/control pairs are matched to ~0.05 m/s, which is what makes this usable at all.

Usage:  python extract_sound_cache.py r47            # all segments
        python extract_sound_cache.py r47 5 6 7
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402
from extract_imu_cache import NSEG, ROUTES, recover_t0  # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"


def extract(tag, s):
    path = RLOGDIR / f"{ROUTES[tag]}--{s}--rlog.zst"
    if not path.exists():
        print(f"{tag}s{s}: no rlog -- skipped")
        return None
    out = ROOT / f"_cache_{tag}"
    z = np.load(out / f"{tag}s{s}.npz")
    t0 = float(z["t0_mono"][0]) if "t0_mono" in z.files else recover_t0(path)
    if t0 is None:
        print(f"{tag}s{s}: no t0 -- skipped")
        return None

    t, lin, wlin, wdb = [], [], [], []
    for evt in read_messages(path):
        try:
            if evt.which() != "soundPressure":
                continue
        except Exception:
            continue
        m = evt.soundPressure
        t.append(evt.logMonoTime * 1e-9)
        lin.append(float(m.soundPressure))
        try:
            wlin.append(float(m.soundPressureWeighted))
            wdb.append(float(m.soundPressureWeightedDb))
        except Exception:
            wlin.append(np.nan)
            wdb.append(np.nan)
    if len(t) < 10:
        print(f"{tag}s{s}: only {len(t)} soundPressure msgs -- skipped")
        return None
    t = np.array(t) - t0
    d = dict(t=t, sp=np.array(lin), spw=np.array(wlin), spwdb=np.array(wdb),
             t0_mono=np.array([t0]))
    np.savez_compressed(out / f"{tag}s{s}_snd.npz", **d)
    dt = np.diff(t)
    print(f"{tag}s{s}: n={len(t):5d}  {t[0]:7.2f}..{t[-1]:7.2f}s  "
          f"rate {1 / np.median(dt):6.3f} Hz  "
          f"sp med {np.median(d['sp']):.5f}  dB med {np.nanmedian(d['spwdb']):.2f}")
    return len(t)


if __name__ == "__main__":
    tag = sys.argv[1]
    segl = sys.argv[2:] or [str(i) for i in range(NSEG[tag])]
    n = sum(x for x in (extract(tag, s) for s in segl) if x)
    print(f"\n{tag}: {n} soundPressure samples cached")
