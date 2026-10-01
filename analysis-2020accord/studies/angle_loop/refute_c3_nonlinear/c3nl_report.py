# -*- coding: utf-8 -*-
r"""c3nl_report.py -- per-band tables from the c3nl_lens grid (worst over the four members unless stated).
usage: python c3nl_report.py   -> out/lens_report.md"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c3nl_sim as S  # noqa: E402

LD = S.OUT / "lens"
BANDS = (("<8", 0, 8), ("8-10", 8, 10), ("10-12.5", 10, 12.5), ("12.5-15", 12.5, 15), ("15-22", 15, 22),
         (">=22", 22, 99))
IMPLS = ("C3-P", "C3-F", "P2", "E2-A3")


def load():
    D = {}
    for f in LD.glob("*.json"):
        d = json.loads(f.read_text())
        D[(d["scn"], d["member"], d["age"])] = d
    return D


def table(D, scn, key, agg="max", members=None, title=None, fmt="{:.2f}", impls=IMPLS):
    L = [f"### {title or scn + ' : ' + key}", "", "| impl | " + " | ".join(b[0] for b in BANDS) + " | worst >=8 (member, v) |",
         "|---|" + "---|" * (len(BANDS) + 1)]
    for im in impls:
        cells = []
        worst = (None, None, None)
        for bn, lo, hi in BANDS:
            vals = []
            for (s, mb, age), d in D.items():
                if s != scn or (members and mb not in members):
                    continue
                arr = np.array(d["m"][key])
                for j, k in enumerate(d["keys"]):
                    if k["impl"] == im and lo <= k["v"] < hi:
                        vals.append((arr[j], mb, k["v"]))
                        if lo >= 8:
                            if worst[0] is None or (arr[j] > worst[0] if agg == "max" else arr[j] < worst[0]):
                                worst = (arr[j], mb, k["v"])
            if not vals:
                cells.append("-")
                continue
            x = [a for a, _, _ in vals]
            val = max(x) if agg == "max" else (min(x) if agg == "min" else sum(x))
            cells.append(fmt.format(val))
        w = "-" if worst[0] is None else f"{fmt.format(worst[0])} ({worst[1]}, {worst[2]:.2f})"
        L.append(f"| {im} | " + " | ".join(cells) + f" | {w} |")
    return L + [""]


def main():
    D = load()
    L = ["# C3 nonlinear lens -- my independent loop (c3nl_sim), scenarios the common scorer does not run", ""]
    scns = sorted({k[0] for k in D})
    for s in scns:
        kind = s.split("_")[0]
        if kind in ("out", "kap", "part", "tsrc"):
            L += table(D, s, "under", title=f"{s}: release lurch TOWARD CENTRE past the setpoint (deg)")
            L += table(D, s, "over", title=f"{s}: max excursion past the setpoint into the turn after release (deg)")
            L += table(D, s, "I_rel", agg="min", title=f"{s}: I at release (S; min = most negative)", fmt="{:.0f}")
            L += table(D, s, "hf_rel", title=f"{s}: hand force at release (T counts)", fmt="{:.0f}")
        elif kind in ("nudge", "knudge", "tnudge"):
            L += table(D, s, "over", title=f"{s}: release lurch PAST CENTRE to the other side (deg)")
            L += table(D, s, "I_rel", agg="min", title=f"{s}: I at release (S)", fmt="{:.0f}")
            L += table(D, s, "hf_rel", title=f"{s}: hand force at release (T counts)", fmt="{:.0f}")
        elif kind in ("scurve", "rev"):
            L += table(D, s, "slope", agg="min", title=f"{s}: tracking slope (min)", fmt="{:.3f}")
            L += table(D, s, "e_max", title=f"{s}: max |error| (deg)")
            L += table(D, s, "dj", agg="sum", title=f"{s}: dwell-then-jump events (sum)", fmt="{:.0f}")
            L += table(D, s, "dj_max", title=f"{s}: largest dwell-then-jump (deg)")
            if kind == "rev":
                L += table(D, s, "hold2", agg="min", title=f"{s}: hold ratio after the reversal (min)", fmt="{:.3f}")
                L += table(D, s, "ovs2", title=f"{s}: overshoot after the reversal (fraction of A)", fmt="{:.3f}")
        elif kind == "small":
            L += table(D, s, "gain", agg="min", title=f"{s}: in-phase wire gain (min)", fmt="{:.2f}")
            L += table(D, s, "dj", agg="sum", title=f"{s}: dwell-then-jump events (sum over members/speeds)", fmt="{:.0f}")
            L += table(D, s, "dj_max", title=f"{s}: largest dwell-then-jump (deg)")
            L += table(D, s, "stick_pct", title=f"{s}: stuck while the setpoint moves (max %)", fmt="{:.0f}")
        elif kind == "zero":
            L += table(D, s, "e_mean", title=f"{s}: steady |error| at sp 0 (deg)", fmt="{:.2f}")
            L += table(D, s, "e_max", title=f"{s}: max |error| at sp 0 (deg)", fmt="{:.2f}")
            if "road" in s:
                L += table(D, s, "rev", title=f"{s}: rate reversals (max)", fmt="{:.0f}")
                L += table(D, s, "p2p", title=f"{s}: p2p wander (deg)", fmt="{:.2f}")
                L += table(D, s, "dj", agg="sum", title=f"{s}: dwell-then-jump events at centre (sum)", fmt="{:.0f}")
    wr = max((np.max(d["m"]["wraps"]) for d in D.values()), default=0)
    L.append(f"int32 wraps over the whole lens: {wr:.0f}")
    txt = "\n".join(L) + "\n"
    (HERE / "out" / "lens_report.md").write_text(txt, encoding="utf-8")
    print(f"{len(D)} job files; report {len(txt)} chars")


if __name__ == "__main__":
    main()
