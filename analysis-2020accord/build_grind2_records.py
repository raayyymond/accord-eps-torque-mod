#!/usr/bin/env python3
"""Materialise the grind-#2 window records for every cached build into one pickle.

Runs once; every analyze_grind2_*.py reads the pickle. Also prints the exposure inventory --
routes differ enormously in what they visited, and the matched-cell comparison is only as good as
the overlap, so the overlap is printed BEFORE any ratio is quoted.
"""
import pickle
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G  # noqa: E402

OUT = HERE.parent / "_cache_grind2_records.pkl"


def main():
    store = {}
    G.hdr("WINDOW RECORDS  (NFFT=256 -> 2.56 s / 0.392 Hz bins, hop=128)")
    print(f"{'build':10s} {'kd':>4s} {'nwin':>6s} {'runs':>5s} {'blk':>5s} {'eng%':>6s} "
          f"{'fs':>14s} {'v max':>6s} {'eff p90':>8s} {'rate p90':>8s}")
    for b in G.ORDER:
        rs = G.wrecs(b)
        store[b] = rs
        if not rs:
            print(f"{b:10s} (no data)")
            continue
        nrun = len({r["ep"] for r in rs})
        nblk = len({r["blk"] for r in rs})
        fsv = G.col(rs, "fs")
        print(f"{b:10s} {G.BUILDS[b]['kd']:4.0f} {len(rs):6d} {nrun:5d} {nblk:5d} "
              f"{100 * np.mean(G.col(rs, 'eng')):5.1f}% "
              f"{fsv.min():6.2f}-{fsv.max():6.2f} {G.col(rs, 'v').max():6.2f} "
              f"{np.percentile(G.col(rs, 'eff'), 90):8.0f} "
              f"{np.percentile(G.col(rs, 'rate'), 90):8.1f}")

    with open(OUT, "wb") as fh:
        pickle.dump(store, fh)
    print(f"\nwrote {OUT}  ({OUT.stat().st_size / 1e6:.1f} MB)")

    # ------------------------------------------------------------------ exposure overlap --------
    G.hdr("EXPOSURE BY CELL  (eng, v-bin, eff-bin, rate-bin) -> windows per build")
    print("v bins  " + " ".join(f"{i}:{lo:g}-{hi:g}" for i, (lo, hi) in enumerate(G.V_BINS)))
    print("eff bins" + " ".join(f"{i}:{lo:g}-{hi:g}" for i, (lo, hi) in enumerate(G.E_BINS)))
    print("rate bins" + " ".join(f"{i}:{lo:g}-{hi:g}" for i, (lo, hi) in enumerate(G.R_BINS)))
    cnt = {b: Counter(r["cell"] for r in store[b]) for b in G.ORDER if store.get(b)}
    cells = sorted(set().union(*[set(c) for c in cnt.values()]))
    print(f"\n{'cell (eng,v,eff,rate)':24s} " + " ".join(f"{b:>10s}" for b in cnt))
    for c in cells:
        row = [cnt[b].get(c, 0) for b in cnt]
        if sum(row) < 6:
            continue
        print(f"{str(c):24s} " + " ".join(f"{v:10d}" for v in row))

    # how many cells are shared between the two dose extremes?
    G.hdr("MATCHED-CELL OVERLAP between Kd doses (min 3 blocks and 8 windows per side)")
    for a, bb in ((0.0, 1.0), (1.0, 2.0), (0.0, 2.0)):
        ra = [r for b in G.DOSE[a] for r in store.get(b, [])]
        rb = [r for b in G.DOSE[bb] for r in store.get(b, [])]
        ca, cb = Counter(r["cell"] for r in ra), Counter(r["cell"] for r in rb)
        shared = [c for c in set(ca) & set(cb) if ca[c] >= 8 and cb[c] >= 8]
        nwa = sum(ca[c] for c in shared)
        nwb = sum(cb[c] for c in shared)
        print(f"  Kd {a:g} vs {bb:g}: {len(shared):3d} shared cells, "
              f"{nwa:5d} / {nwb:5d} windows inside them "
              f"({100 * nwa / max(len(ra), 1):.0f}% / {100 * nwb / max(len(rb), 1):.0f}% of each pool)")
        for c in sorted(shared):
            print(f"      {str(c):22s} {ca[c]:5d} {cb[c]:5d}")


if __name__ == "__main__":
    main()
