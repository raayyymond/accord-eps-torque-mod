#!/usr/bin/env python3
r"""Time-ordered trace of the packed 5-bit gp-0x1500 value across all 7 rlog-5 segments,
to see the transition pattern (zero at start -> nonzero later?) and whether it looks like
structured behavior (ramp/oscillation/counter) vs single-sample glitches.
"""
import sys, glob, os
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE.parent / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

RLOG5_GLOB = str(HERE / "rlogs" / "75604b0a432fdc89_00000005--2ae04b9ba2--*--rlog.zst")


def main():
    paths = sorted(glob.glob(RLOG5_GLOB))
    for path in paths:
        vals = []
        for evt in read_messages(path):
            try:
                if evt.which() != "can":
                    continue
            except Exception:
                continue
            for fr in evt.can:
                if fr.address != 330 or fr.src != 1:
                    continue
                d = bytes(fr.dat)
                if len(d) != 8:
                    continue
                p1 = (d[4] >> 3) & 0x1F
                vals.append(p1)
        seg = os.path.basename(path)
        n = len(vals)
        # find first index where value goes nonzero
        first_nz = next((i for i, v in enumerate(vals) if v != 0), None)
        zero_run_frac = sum(1 for v in vals if v == 0) / n if n else 0
        print(f"\n{seg}: {n} frames, first-nonzero-idx={first_nz}, zero-fraction={zero_run_frac:.3f}")
        # downsample: print every ~50th value across the segment (~2 samples/sec at 100Hz)
        step = max(1, n // 80)
        print("  downsampled trace:", vals[::step])


if __name__ == "__main__":
    main()
