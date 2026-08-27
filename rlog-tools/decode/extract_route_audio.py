#!/usr/bin/env python3
r"""Spectrogram cache for ANY route -- generalised from `extract_r1e_audio.py`.

WHY THIS EXISTS
---------------
`extract_r1e_audio.py` built the only real audio spectrogram in the kit and hard-coded
`ROUTE = "1e"` plus that route's filename hash.  The 83.5 Hz harmonic-series result
(`accord-the-lowspeed-grind-is-an-83hz-harmonic-series`) therefore rests on ONE build (V107) with
no way to ask the two questions that matter:

    * is the comb present on STOCK?          <- decides whether the series is OURS
    * does it scale with the LKAS gain?      <- decides whether the gain drives it

Both are answerable: the rlogs for the whole ladder are on disk -- r97 (STOCK, 18 seg),
r85 (V100, 4x), r95 (V101, 8x), r96 (V102, 6x), r9e (V103), ra4 (V104), ra5 (V105), ra6 (V106).

🛑 EVERYTHING IN THE 1e HEADER STILL APPLIES.  Absolute level does NOT travel between drives --
the parked-engine-on cabin differs 3-12x -- so no statistic may compare route to route.  Every
contrast lives INSIDE one drive: engaged vs manual at matched speed.  The comb SCORE is itself an
engaged-minus-manual quantity, which is exactly why it CAN be compared across drives.

TIME BASE.  Blocks are 800 samples = 50.0 ms at 16 kHz and carry `logMonoTime`.  Frames are stamped
from the FIRST block of each segment and indexed forward at 1/16000 s, so a dropped block inside a
segment cannot silently shift later frames; segment boundaries are never spanned.  Times are
relative to that route's cache `t0_mono`, i.e. the same axis as `r<ROUTE>.npz:t`.

Usage:
    python decode/extract_route_audio.py 97          # one route
    python decode/extract_route_audio.py 97 a6 96    # several
    python decode/extract_route_audio.py --list      # what is available and what is already built
"""
# --- PATH BOOTSTRAP -------------------------------------------------------
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
                  ("rlogs", "ghidra_project", "__pycache__")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_here", "_roots", "_c", "_n", "_top", "_e", "_cand", "_p",
           "_r", "_b", "_ds", "_fs", "_x", "_v"):
    globals().pop(_v, None)
# --------------------------------------------------------------------------
import re
import sys
from pathlib import Path

import numpy as np
import rlog_parse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
RLOGS = ROOT / "analysis-2020accord" / "rlogs"
CACHE_ROOT = ROOT / "analysis-2020accord" / "_scratch" / "cache"

SR = 16000
NFFT = 4096              # 3.906 Hz/bin -- fine enough to resolve an 83.5 Hz comb from its neighbours
HOP = 800                # 50 ms, one block
FMAX = 2000.0


def discover(route):
    """Find the filename prefix for a route.  🛑 GLOB and sort numerically -- never index-walk
    until absent, the loop that once silently dropped a whole route."""
    pat = re.compile(r"^(.*_0*%s)--([0-9a-f]+)--(\d+)--rlog\.zst$" % re.escape(route.lower()))
    pref = {}
    for p in RLOGS.iterdir():
        m = pat.match(p.name)
        if m:
            pref.setdefault(f"{m.group(1)}--{m.group(2)}", []).append(p)
    if not pref:
        return None, []
    # a route can have more than one capture prefix; take the one with the most segments
    best = max(pref, key=lambda k: len(pref[k]))
    segs = sorted(pref[best], key=lambda p: int(p.name.split("--")[2]))
    return best, segs


def build(route, force=False):
    cache = CACHE_ROOT / f"r{route}"
    out = cache / f"r{route}_spec.npz"
    if out.exists() and not force:
        print(f"  r{route}: spectrogram already built ({out.stat().st_size/1e6:.0f} MB) -- skipping")
        return None
    can = cache / f"r{route}.npz"
    if not can.exists():
        print(f"  r{route}: NO CAN CACHE -- cannot place audio on a common time axis, skipping")
        return None
    z = np.load(can, allow_pickle=True)
    if "t0_mono" not in z.files:
        print(f"  r{route}: CAN cache has no t0_mono -- skipping")
        return None
    t0 = float(np.asarray(z["t0_mono"]).ravel()[0])
    prefix, segs = discover(route)
    if not segs:
        print(f"  r{route}: NO RLOGS on disk")
        return None
    tag = str(np.asarray(z["probe_build"]).ravel()[0]) if "probe_build" in z.files else "?"
    print(f"  r{route} ({tag}): {len(segs)} segments, prefix {prefix}, t0_mono {t0:.3f}", flush=True)

    win = np.hanning(NFFT + 1)[:NFFT]
    ff = np.fft.rfftfreq(NFFT, 1 / SR)
    keep = ff <= FMAX
    fkeep = ff[keep]

    all_t, all_S, n_blocks, n_noaudio = [], [], 0, 0
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
            n_noaudio += 1
            continue
        n_blocks += len(blocks)
        x = np.concatenate(blocks).astype(np.float64)
        tseg0 = btimes[0] - t0
        nfr = 1 + (len(x) - NFFT) // HOP if len(x) >= NFFT else 0
        if nfr <= 0:
            continue
        idx = np.arange(nfr) * HOP
        frames = np.lib.stride_tricks.sliding_window_view(x, NFFT)[idx] * win
        all_S.append(np.abs(np.fft.rfft(frames, axis=1))[:, keep].astype(np.float32))
        all_t.append(tseg0 + (idx + NFFT / 2) / SR)
    if not all_S:
        print(f"    r{route}: ZERO audio blocks in {len(segs)} segments -- this route has no audio")
        return None
    t = np.concatenate(all_t)
    S = np.concatenate(all_S, axis=0)
    o = np.argsort(t)
    t, S = t[o], S[o]
    np.savez_compressed(out, t=t.astype(np.float32), f=fkeep.astype(np.float32), S=S)
    print(f"    {n_blocks} blocks ({n_noaudio}/{len(segs)} segments had none) -> {S.shape} "
          f"frames x bins, {fkeep[1]-fkeep[0]:.3f} Hz/bin, span {t[0]:.1f}..{t[-1]:.1f} s")
    print(f"    wrote {out}  ({out.stat().st_size/1e6:.0f} MB)")
    return t, fkeep, S


def available():
    seen = {}
    pat = re.compile(r"^.*_0*([0-9a-f]+)--[0-9a-f]+--\d+--rlog\.zst$")
    for p in RLOGS.iterdir():
        m = pat.match(p.name)
        if m:
            seen[m.group(1)] = seen.get(m.group(1), 0) + 1
    rows = []
    for r, n in sorted(seen.items()):
        cache = CACHE_ROOT / f"r{r}"
        rows.append((r, n, (cache / f"r{r}.npz").exists(), (cache / f"r{r}_spec.npz").exists()))
    return rows


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    if not args or args[0] == "--list":
        print("  %-6s %5s %6s %6s" % ("route", "segs", "CAN", "spec"))
        for r, n, hc, hs in available():
            if hc:
                print("  %-6s %5d %6s %6s" % (r, n, "yes" if hc else "-", "yes" if hs else "-"))
        sys.exit(0)
    force = "--force" in args
    for r in [a for a in args if not a.startswith("--")]:
        build(r, force=force)
