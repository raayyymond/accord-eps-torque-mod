# -*- coding: utf-8 -*-
"""Extract 0x14A byte 4 (V282 cave probe byte) for r36/r37/r38 into
analysis-2020accord/_scratch/cache/v280/<tag>_b4.npz  (t14b, b4).
V282 decode: bit7=sign(gp-0x6b4c) bit6=|r24|>=|T| bit5=|r24|>=|agg| bit4=sign(r24) bit3=sign(gp-0x3680).
Subagent grind283, 2026-09-03.  Mirrors ../osc-highangle/extract_14a_b4.py exactly."""
import glob, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
from cereal import log as clog  # noqa
import zstandard

def run(tag, prefix):
    segs = sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % prefix)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    print(tag, len(segs), "segments", flush=True)
    t, b4 = [], []
    for p in segs:
        with open(p, "rb") as fh:
            data = zstandard.ZstdDecompressor().stream_reader(fh).read()
        it = clog.Event.read_multiple_bytes(data)
        while True:
            try: evt = next(it)
            except StopIteration: break
            except Exception as e: print("  truncated", str(e)[:50]); break
            try: w = evt.which()
            except Exception: continue
            if w == "can":
                for m in evt.can:
                    if m.src == 1 and m.address == 0x14A and len(m.dat) >= 5:
                        t.append(evt.logMonoTime * 1e-9); b4.append(m.dat[4])
        print("  read", os.path.basename(p), flush=True)
    np.savez(os.path.join(CACHE, tag + "_b4.npz"), t14b=np.asarray(t), b4=np.asarray(b4, int))
    u, c = np.unique(np.asarray(b4), return_counts=True)
    print(tag, len(t), "frames; b4 census", list(zip(u.tolist(), c.tolist())), flush=True)

if __name__ == "__main__":
    for tag, prefix in (("r36", "75604b0a432fdc89_00000036--f4be1a18e9"),
                        ("r37", "75604b0a432fdc89_00000037--4a79da5d18"),
                        ("r38", "75604b0a432fdc89_00000038--f77bddf4bd")):
        if not os.path.exists(os.path.join(CACHE, tag + "_b4.npz")):
            run(tag, prefix)
        else:
            print(tag, "already cached", flush=True)
