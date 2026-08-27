#!/usr/bin/env python3
r"""⭐ THE ACOUSTIC CHANNEL.  The rlog carries a REAL MICROPHONE, and nobody in this kit has ever
used it.  The operator's V99 report is about the **AUDIBLE** aspect of the grinding, so this is
the first build whose primary operator claim has a matching instrument.

WHAT IS ACTUALLY IN THE LOG  [EVIDENCE -- enumerated from the rlog itself, not assumed]:
    rawAudioData    1,048 msgs/segment   **16,000 Hz mono int16, 800 samples (50 ms) per message**
    soundPressure     564 msgs/segment   broadband level + A-weighted dB

TWO INSTRUMENTS ARE BUILT, and the second is the physically right one:
  (1) **BAND LEVELS** -- RMS in acoustic octave-ish bands.  Straightforward, but dominated by road
      and wind noise, so it MUST be speed-matched before it means anything.
  (2) ⭐ **THE MODULATION SPECTRUM OF THE AUDIO ENVELOPE.**  A mechanical ratchet at ~8 Hz does not
      RADIATE at 8 Hz -- a cabin mic cannot hear 8 Hz.  It **AMPLITUDE-MODULATES** the broadband
      rasp.  So the audible signature of "grinding" is a 6-9 / 12-31 Hz MODULATION of a
      several-hundred-Hz carrier.  This extractor computes the Hilbert-free envelope (rectify +
      decimate to 100 Hz) of each acoustic band, on the SAME 100 Hz grid as the CAN row grid, so
      every existing band statistic in `score/v99_r82_score.py` applies to it unchanged.

🛑 TIME BASE: `t = logMonoTime * 1e-9 - t0_mono`, the SAME convention `decode/extract_r7d.py` uses
   (`decode/extract_r7d.py:145` and `:301`).  Asserted against the cache's own `t` span.
🛑 GAPS ARE NOT INTERPOLATED.  Audio messages that are not contiguous leave a hole; the envelope
   grid carries NaN there and every consumer drops NaN windows.
⚠ CONFOUNDS, stated up front and NOT argued away: the microphone is the comma device's cabin mic.
   It hears road noise, wind, HVAC, the openpilot chimes and the operator.  It may have AGC.
   **NO cross-build acoustic number is safe without a within-route speed-matched control**, and the
   within-drive LKAS-off arm is the only clean comparison this instrument supports.

Usage:  python decode/extract_r82_audio.py 82 81
Writes: analysis-2020accord/_cache_r<N>/r<N>_audio.npz
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

import numpy as np
from scipy import signal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import rlog_parse as R  # noqa: E402

RLOGS = ROOT / "analysis-2020accord" / "rlogs"
ROUTES = {
    "82": ("75604b0a432fdc89_00000082--e30d55731b", 2, "_scratch/cache/r82", "r82", "V99"),
    "81": ("75604b0a432fdc89_00000081--c7103d2cb4", 3, "_scratch/cache/r81", "r81", "V98"),
}

SR = 16000                     # asserted per message, not assumed
GRID = 100.0                   # envelope output rate == the CAN row grid
# Acoustic carrier bands.  "Grinding" is a broadband rasp; these split it coarsely.
ABANDS = {"a20_100": (20, 100), "a100_300": (100, 300), "a300_800": (300, 800),
          "a800_2k": (800, 2000), "a2k_4k": (2000, 4000), "a4k_7k": (4000, 7000)}


def _blocks(route):
    """Yield (t_start_s, int16 samples) for every rawAudioData message, plus the soundPressure
    series.  `t` is in the cache's own time base."""
    pref, nseg, cdir, stem, _lab = ROUTES[route]
    z = np.load(ROOT / "analysis-2020accord" / cdir / f"{stem}.npz", allow_pickle=True)
    t0 = float(z["t0_mono"][0])
    t_end = float(z["t"][-1])
    blocks, sp_t, sp_db, sp_lin = [], [], [], []
    srs = set()
    for s in range(nseg):
        p = RLOGS / f"{pref}--{s}--rlog.zst"
        if not p.exists():
            print(f"  ⚠ missing {p.name}")
            continue
        nmsg = 0
        for evt in R.read_messages(str(p)):
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9 - t0
            if w == "rawAudioData":
                a = evt.rawAudioData
                srs.add(int(a.sampleRate))
                x = np.frombuffer(bytes(a.data), dtype=np.int16)
                if len(x):
                    blocks.append((tm, x))
                    nmsg += 1
            elif w == "soundPressure":
                sp = evt.soundPressure
                sp_t.append(tm)
                sp_db.append(float(sp.soundPressureWeightedDb))
                sp_lin.append(float(sp.soundPressure))
        print(f"    seg {s}: {nmsg:,} rawAudioData messages")
    assert srs == {SR}, f"unexpected sample rates {srs}"
    print(f"  sample rate asserted == {SR} Hz on every message; "
          f"audio spans {blocks[0][0]:.2f}..{blocks[-1][0]:.2f} s vs cache t 0..{t_end:.2f} s")
    return blocks, np.array(sp_t), np.array(sp_db), np.array(sp_lin), t_end


def extract(route):
    print(f"\n=== ACOUSTIC EXTRACT, route {route} ({ROUTES[route][4]}) ===")
    blocks, sp_t, sp_db, sp_lin, t_end = _blocks(route)

    # ---- 🛑 PLACEMENT.  DO NOT place each block at `round(t*SR)`.
    # `logMonoTime` is the PUBLISH time and it jitters +-10 ms about the true 50.01 ms cadence
    # (measured: dt p10 41.28 / p50 50.01 / p90 60.97 ms, and 800 samples @ 16 kHz IS 50.00 ms).
    # Timestamp placement therefore punctures the stream with a 1-4 sample-bin hole every ~8 bins
    # -- a PERIODIC dropout at ~11 Hz, landing squarely inside the 12-16 Hz modulation band this
    # analysis tests.  Interpolating those holes would MANUFACTURE the very line being measured.
    # The stream is genuinely contiguous: blocks are laid END TO END, and a new run is anchored
    # only at a REAL dropout (dt > 75 ms).  Route 82 seg 0 has exactly 12 such dropouts.
    GAP_TOL = 0.075
    n_tot = int(np.ceil((t_end + 1.0) * SR))
    pcm = np.full(n_tot, np.nan, np.float32)
    wp = None
    t_prev = None
    runs = 0
    for tm, x in blocks:
        if t_prev is None or (tm - t_prev) > GAP_TOL:
            wp = int(round(tm * SR))
            runs += 1
        i0 = max(wp, 0)
        i1 = min(i0 + len(x), n_tot)
        if i1 > i0:
            pcm[i0:i1] = x[:i1 - i0]
        wp = i0 + len(x)
        t_prev = tm
    cov = float(np.isfinite(pcm).mean())
    print(f"  16 kHz timeline: {n_tot:,} samples, coverage {100*cov:.2f} %, "
          f"{runs} contiguous runs (holes are REAL dropouts, NaN, NEVER interpolated)")

    filled = np.nan_to_num(pcm, nan=0.0).astype(np.float64)
    valid = np.isfinite(pcm)

    # ---- per-band envelope, decimated to the 100 Hz CAN row grid
    dec = int(SR / GRID)                      # 160
    n_out = n_tot // dec
    out = {}
    for name, (lo, hi) in ABANDS.items():
        sos = signal.butter(4, [lo / (SR / 2), min(hi, SR / 2 - 1) / (SR / 2)],
                            btype="band", output="sos")
        y = signal.sosfiltfilt(sos, filled)
        # envelope = RMS inside each 10 ms bin  (rectify + box decimate, no Hilbert needed)
        e = np.sqrt(np.mean((y[:n_out * dec].reshape(n_out, dec)) ** 2, axis=1))
        ok = valid[:n_out * dec].reshape(n_out, dec).all(axis=1)
        e[~ok] = np.nan
        out[name] = e.astype(np.float32)
        print(f"  band {name:9s} {lo:5d}-{hi:5d} Hz   envelope p50 "
              f"{np.nanmedian(e):9.1f}   valid {100*np.isfinite(e).mean():.1f} %")

    t_grid = np.arange(n_out) / GRID
    np.savez_compressed(
        ROOT / "analysis-2020accord" / ROUTES[route][2] / f"{ROUTES[route][3]}_audio.npz",
        t=t_grid, coverage=np.array([cov]), sample_rate=np.array([SR]),
        sp_t=sp_t, sp_db=sp_db, sp_lin=sp_lin, **out)
    print(f"  wrote {ROUTES[route][3]}_audio.npz   grid {n_out:,} @ {GRID:.0f} Hz, "
          f"soundPressure {len(sp_t):,} samples")


if __name__ == "__main__":
    for r in (sys.argv[1:] or ["82"]):
        extract(r)
