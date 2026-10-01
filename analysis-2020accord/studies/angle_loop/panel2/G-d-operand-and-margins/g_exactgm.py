# -*- coding: utf-8 -*-
r"""g_exactgm.py -- the EXACT gain margin (g_exact: the smallest loop-gain multiplier > 1 at which the 10-tick monodromy
reaches rho = 1) at the 12 lowest-LTI-GM gated points of each implementation's gate, beside the LTI GM g_gate used, and the
exact rho at the fade floor (x 0.297: a light hand) at the 12 lowest-PM points.  ANALYSIS ONLY.
usage: python g_exactgm.py <impl> ...   -> g_exactgm_out.txt (appends)"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402
import g_exact as GE  # noqa: E402
import g_gate as GG  # noqa: E402


def ex_for(im, name, v):
    pl, d, ea, jbk, kappa = X.plant_ext(name, v)
    return GE.Exact(im["dkind"], pl, d, ea, X.G_of(im["rows"], v), 112, im.get("ki", 56), im["kd"], kappa=kappa,
                    dop_k=2.0 ** im.get("sh", 6))


def main(iids):
    L = []
    for iid in iids:
        im = GG.impls()[iid]
        g = [r for r in json.loads((X.OUT / f"gate_{iid}.json").read_text()) if X.tier_of(r["member"]) != "report"]
        low = sorted(g, key=lambda r: r["gm"])[:12]
        L.append(f"== {iid}: exact GM at the 12 lowest-LTI-GM gated points")
        for r in low:
            egm = GE.exact_gm(ex_for(im, r["member"], r["v"]))
            L.append(f"   {r['member']:32s} @{r['v']:5.2f}: LTI GM {r['gm']:5.1f} dB   exact GM {egm:5.1f} dB")
        lowpm = sorted(g, key=lambda r: r["pm"] - X.bar_of(r["member"]))[:12]
        L.append(f"   fade floor (x 0.297, a light hand on the wheel) at the 12 lowest-PM-margin points: exact rho")
        for r in lowpm:
            rho = ex_for(im, r["member"], r["v"]).rho_pole(0.297)[0]
            L.append(f"   {r['member']:32s} @{r['v']:5.2f}: PM {r['pm']:5.1f}  rho(x0.297) {rho:.4f}")
        print("\n".join(L[-27:]), flush=True)
    with open(HERE / "g_exactgm_out.txt", "a", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
