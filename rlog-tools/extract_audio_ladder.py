r"""Extract the ACOUSTIC channel for the two LADDER routes the first pass could not reach.

`extract_audio.py`'s `segments()` walks 0,1,2,... and STOPS at the first absent index.
Route `85` on disk is segments **15,16,18,19,20** -- index 0 is absent, so that scan returns
ZERO segments and route 85 was silently skipped.  Route 95 (0..4) is contiguous but was not in
the first pass's ROUTES table at all.

This file changes NOTHING about the feature extraction -- it imports `extract_audio` and only
replaces the segment discovery with a glob, so the ladder routes are processed by the same code
that wrote the four caches already on disk.

    r85  V100  4x   (5 of ~21 segments on disk -- the cache is a SUBSET of the drive, stated)
    r95  V101  8x   CONFOUNDED (a second lever differs; zero engaged seconds above 80 km/h)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import extract_audio as E  # noqa: E402

E.ROUTES.update({
    "r85": ("75604b0a432fdc89_00000085--cad692c3d3", "V100 4x  (segments 15,16,18,19,20 only)"),
    "r95": ("75604b0a432fdc89_00000095--6d7c6deef5", "V101 8x  CONFOUNDED"),
})


def segments(prefix):
    """Glob, so a hole in the segment numbering does not truncate the route."""
    out = sorted(E.RLOGS.glob("%s--*--rlog.zst" % prefix),
                 key=lambda p: int(p.name.split("--")[2]))
    return out


E.segments = segments

if __name__ == "__main__":
    tags = sys.argv[1:] or ["r85", "r95"]
    print("=" * 100)
    print("LADDER AUDIO EXTRACTION + COVERAGE AUDIT  (glob segment discovery)")
    print("=" * 100)
    for t in tags:
        print("  segments found for %s: %s" % (t, [p.name.split('--')[2] for p in segments(E.ROUTES[t][0])]))
    rep = [E.extract(t) for t in tags]
    print()
    print("%6s %9s %12s %10s %10s %10s %9s %9s" %
          ('route', 'blocks', 'samples', 'audio s', 'wall s', 'COVERAGE', 'clipped', 'frames'))
    for r in rep:
        print("%6s %9d %12d %10.1f %10.1f %10.4f %9d %9d"
              % (r['tag'], r['blocks'], r['samples'], r['dur'], r['wall'], r['cov'],
                 r['clip'], r['frames']))
