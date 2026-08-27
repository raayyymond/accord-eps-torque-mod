#!/usr/bin/env python3
r"""Spectrogram cache for route `1e` (**V107**) -- the ONLY instrument that can see the grind.

🛑 WHY THIS EXISTS.  The operator hears grinding at "several hundred Hz, possibly ~100 Hz".  Every
CAN channel in this kit is structurally blind to it:
    0x18F staleness 12.5 ms  => Nyquist 50.6 Hz
    0x1AB (427)     20.1 ms  => Nyquist 24.9 Hz   (MEASURED on this route, n=66,896)
Only `rawAudioData` (16 kHz PCM) reaches the band.  Route `1e` carries 26,753 blocks over 23/23
segments = 1337.7 s = 100 % coverage.  🛑 **Route `1b` carries ZERO audio blocks** -- every audio
result in this kit's V107 work is necessarily 1e-only.

🛑 ABSOLUTE LEVEL DOES NOT TRAVEL BETWEEN DRIVES.  The parked-engine-on cabin differs 3-12x across
drives, so no statistic here compares 1e to another route.  Every contrast lives INSIDE this drive:
engaged vs manual at matched speed, speed bin vs speed bin, before vs after a disengagement.

TIME BASE.  Blocks are 800 samples = 50.0 ms at 16 kHz and carry `logMonoTime`.  Frames are stamped
from the FIRST block of each segment and indexed forward at 1/16000 s, so a dropped block inside a
segment cannot silently shift later frames; segment boundaries are never spanned by a window.
Times are relative to the cache's `t0_mono`, i.e. the same axis as `r1e.npz:t`.

Usage:
    python decode/extract_r1e_audio.py            # build the spectrogram cache
"""
# --- PATH BOOTSTRAP -------------------------------------------------------
# Walks BOTH `.pkgroot` roots: the reorg left `analysis-2020accord/lib/` off the path, which breaks
# the `_grind2_lib` import the shared extractors need.  See `extract_ra7.py` for the full note.
import os as _os, sys as _sys
_here = _os.path.dirname(_os.path.abspath(__file__))
_roots, _c = [], _here
while True:
    if _os.path.isfile(_os.path.join(_c, ".pkgroot")):
        _roots.append(_c)
    _n = _os.path.dirname(_c)
    if _n == _c:
        break
    _c = _n
_top = _os.path.dirname(_roots[0])
for _e in sorted(_os.listdir(_top)):
    _cand = _os.path.join(_top, _e)
    if _os.path.isfile(_os.path.join(_cand, ".pkgroot")) and _cand not in _roots:
        _roots.append(_cand)
_p = []
for _r in _roots:
    _p.append(_r)
    for _b, _ds, _fs in _os.walk(_r):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _here, _roots, _c, _n, _top, _e, _cand, _p, _r, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

import numpy as np

import rlog_parse  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
RLOGS = ROOT / "analysis-2020accord" / "rlogs"

ROUTE = "1e"
PREFIX = "75604b0a432fdc89_0000001e--28ef595061"
CACHE = ROOT / "analysis-2020accord" / "_scratch" / "cache" / f"r{ROUTE}"

SR = 16000
NFFT = 4096              # 3.906 Hz resolution -- fine enough to separate a line from its neighbours
HOP = 800                # 50 ms, one block: matches the CAN cache's usable time resolution
FMAX = 2000.0            # the operator's "several hundred Hz" lives well inside this


def segments():
    """🛑 GLOBS and sorts numerically.  Never index-walk-until-absent: that is the loop that
    silently dropped a whole route (`extract_audio.py:segments()`)."""
    return sorted(RLOGS.glob(f"{PREFIX}--*--rlog.zst"),
                  key=lambda p: int(p.name.split("--")[2]))


def build():
    segs = segments()
    t0 = float(np.load(CACHE / f"r{ROUTE}.npz", allow_pickle=True)["t0_mono"][0])
    print(f"  route {ROUTE} (V107): {len(segs)} segments, t0_mono {t0:.3f}", flush=True)

    win = np.hanning(NFFT + 1)[:NFFT]
    ff = np.fft.rfftfreq(NFFT, 1 / SR)
    keep = ff <= FMAX
    fkeep = ff[keep]

    all_t, all_S = [], []
    n_blocks = 0
    for si, p in enumerate(segs):
        blocks, btimes = [], []
        for evt in rlog_parse.read_messages(str(p)):
            try:
                if evt.which() != "rawAudioData":
                    continue
            except Exception:
                continue
            blocks.append(np.frombuffer(bytes(evt.rawAudioData.data), dtype="<i2"))
            btimes.append(evt.logMonoTime * 1e-9)
        if not blocks:
            print(f"    seg{si:02d}: NO AUDIO", flush=True)
            continue
        n_blocks += len(blocks)
        x = np.concatenate(blocks).astype(np.float64)
        # anchor on the first block of THIS segment; never span a segment boundary
        tseg0 = btimes[0] - t0
        nfr = 1 + (len(x) - NFFT) // HOP if len(x) >= NFFT else 0
        if nfr <= 0:
            continue
        idx = np.arange(nfr) * HOP
        frames = np.lib.stride_tricks.sliding_window_view(x, NFFT)[idx] * win
        S = np.abs(np.fft.rfft(frames, axis=1))[:, keep].astype(np.float32)
        all_S.append(S)
        all_t.append(tseg0 + (idx + NFFT / 2) / SR)
        print(f"    seg{si:02d}: {len(blocks):4d} blocks  {len(x)/SR:6.1f} s  {nfr:5d} frames  "
              f"t {tseg0:7.1f}..{tseg0 + len(x)/SR:7.1f}", flush=True)

    t = np.concatenate(all_t)
    S = np.concatenate(all_S, axis=0)
    o = np.argsort(t)
    t, S = t[o], S[o]
    out = CACHE / f"r{ROUTE}_spec.npz"
    np.savez_compressed(out, t=t.astype(np.float32), f=fkeep.astype(np.float32), S=S)
    print(f"\n  {n_blocks} blocks -> spectrogram {S.shape} (frames x bins), "
          f"{fkeep[1]-fkeep[0]:.3f} Hz/bin, {HOP/SR*1e3:.0f} ms/frame")
    print(f"  span {t[0]:.1f}..{t[-1]:.1f} s on the SAME axis as r{ROUTE}.npz:t")
    print(f"  wrote {out}  ({out.stat().st_size/1e6:.0f} MB)")
    return t, fkeep, S


if __name__ == "__main__":
    build()
