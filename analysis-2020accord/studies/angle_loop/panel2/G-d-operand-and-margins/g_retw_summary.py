# -*- coding: utf-8 -*-
r"""g_retw_summary.py -- condenses g_retw's cache: per implementation, the worst ratio vs V295 at each frequency over
every condition (2 frames x 2 transports x 3 rate-former lags x 4 hold-age sets = 48), the conditions where the
candidate is MORE anti-damping than V295 at 13-25 Hz, and the 5-10 Hz values.  ANALYSIS ONLY.
usage: python g_retw_summary.py <json tag>   -> g_retw_summary.txt"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402

FR = [5, 7, 10, 13, 15, 17, 20, 25]


def main(tag):
    d = json.loads((X.OUT / f"retw_{tag}.json").read_text())
    impls = []
    for k in d:
        i = k.split("|")[0]
        if i not in impls:
            impls.append(i)
    L = []
    P = L.append
    P(f"Re(T/w) vs V295 over 48 conditions (frame s 1 / 1.155 x transport 2 / 6 ms x rate-former lag 0 / 0.5 / 1 tick x "
      f"hold ages 0-9 / 1-10 / 11-20 / 21-30); ratio = candidate / V295 where V295 anti-damps (> 1 = worse than V295)")
    for i in impls:
        rows = {k.split("|", 1)[1]: v for k, v in d.items() if k.split("|")[0] == i}
        P(f"=== {i}")
        worst = [max((r["ratio"][j] if np.isfinite(r["ratio"][j]) else -1) for r in rows.values()) for j in range(8)]
        wc = [max(rows, key=lambda c: (rows[c]["ratio"][j] if np.isfinite(rows[c]["ratio"][j]) else -1)) for j in range(8)]
        P("  worst ratio vs V295 (finite cases) " + " ".join(f"{f:>2d} Hz {w:5.2f}" for f, w in zip(FR, worst)))
        for j in (3, 4, 5, 6, 7):
            P(f"     {FR[j]:2d} Hz worst at [{wc[j]}]")
        over = sorted({c for c, r in rows.items() for j in (3, 4, 5, 6, 7) if np.isfinite(r["ratio"][j]) and r["ratio"][j] > 1.0})
        P(f"  conditions with ratio > 1 at 13-25 Hz: {len(over)} / {len(rows)}")
        for c in over:
            r = rows[c]
            P(f"     {c:40s} " + " ".join(f"{r['ratio'][j]:5.2f}" for j in (3, 4, 5, 6, 7)))
        damp5 = [rows[c]["W"][0] for c in rows]
        damp7 = [rows[c]["W"][1] for c in rows]
        damp10 = [rows[c]["W"][2] for c in rows]
        P(f"  5 / 7 / 10 Hz Re(T/w) worst over conditions: {min(damp5):+.2f} / {min(damp7):+.2f} / {min(damp10):+.2f} "
          f"(V295 worst {min(rows[c]['v295'][0] for c in rows):+.2f} / {min(rows[c]['v295'][1] for c in rows):+.2f} / "
          f"{min(rows[c]['v295'][2] for c in rows):+.2f})")
    (HERE / "g_retw_summary.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main(sys.argv[1])


def absolute(tag):
    """worst-case vs worst-case: the most negative Re(T/w) over all 48 conditions, candidate and V295 / V294."""
    d = json.loads((X.OUT / f"retw_{tag}.json").read_text())
    impls = []
    for k in d:
        i = k.split("|")[0]
        if i not in impls:
            impls.append(i)
    L = ["", "WORST-CASE vs WORST-CASE: min over all 48 conditions of Re(T/w) (T counts per deg/s), per frequency",
         "freq Hz            " + " ".join(f"{f:6d}" for f in FR)]
    any_rows = next(iter(d.values()))
    v295 = np.min([r["v295"] for r in d.values()], axis=0)
    v294 = np.min([r["v294"] for r in d.values()], axis=0)
    L.append("V294               " + " ".join(f"{x:+6.2f}" for x in v294))
    L.append("V295               " + " ".join(f"{x:+6.2f}" for x in v295))
    for i in impls:
        W = np.min([r["W"] for k, r in d.items() if k.split("|")[0] == i], axis=0)
        L.append(f"{i:18s} " + " ".join(f"{x:+6.2f}" for x in W) + "   / V295 worst: " +
                 " ".join(f"{(w / v if v < 0 else float('nan')):5.2f}" for w, v in zip(W, v295)))
    print("\n".join(L))
    with open(HERE / "g_retw_summary.txt", "a", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if len(sys.argv) > 2 and sys.argv[2] == "abs":
    absolute(sys.argv[1])
