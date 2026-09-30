# -*- coding: utf-8 -*-
"""j_metric_ci.py -- sampling CI for J on the windows j_metric_r71b.py wrote (the record's f1 windows).

J = sum_w |E_w|^2 / sum_w |X_w|^2 over in-band bins.  The windows overlap 50 % (hop 512 of 1024), so the bootstrap
resamples BLOCKS of 3 consecutive windows (~20 s), never single windows.  2000 resamples, seed 0.
Also: the leave-one-block-out spread, and the share of V294's J carried by its single worst block (a J from 18
windows can be one bad curve).  EVIDENCE for the numbers; whether 18 windows suffice is judged by the CI width.
"""
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "_scratch" / "jmetric"
BAND = (0.15, 2.4)
SUB = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)]
ROUTES = {"00000064--ce6b0b0ebb": "V282", "00000075--6c8687d5bd": "T4 rev4", "00000076--d0b7ea7e4d": "T5 rev5",
          "00000071--a7b8ba5d9d": "V294"}


def per_window(route):
    D = np.load(OUT / f"f1_{route}.npz")
    f = D["f"]; b = (f >= BAND[0]) & (f <= BAND[1])
    E = D["X"] - D["Y"]
    pe = np.sum(np.abs(E[:, b]) ** 2, axis=1); px = np.sum(np.abs(D["X"][:, b]) ** 2, axis=1)
    pes = [np.sum(np.abs(E[:, (f >= lo) & (f < hi)]) ** 2, axis=1) for lo, hi in SUB]
    return pe, px, pes, D["vmed"]


def main():
    rng = np.random.default_rng(0)
    res = {}
    for r, lab in ROUTES.items():
        pe, px, pes, vm = per_window(r)
        n = len(pe); B = 3
        blocks = [np.arange(i, min(i + B, n)) for i in range(0, n, B)]
        J = pe.sum() / px.sum()
        bs = []
        for _ in range(2000):
            pick = rng.integers(0, len(blocks), len(blocks))
            idx = np.concatenate([blocks[k] for k in pick])
            bs.append(pe[idx].sum() / px[idx].sum())
        lo, hi = np.percentile(bs, [2.5, 97.5])
        loo = [np.delete(pe, blk).sum() / np.delete(px, blk).sum() for blk in blocks]
        wshare = pe / pe.sum()
        res[r] = dict(label=lab, n=n, J=float(J), ci=[float(lo), float(hi)], loo=[float(min(loo)), float(max(loo))],
                      top_window_share=float(wshare.max()), sub_ci=[])
        for k, (a, c) in enumerate(SUB):
            bsk = []
            for _ in range(500):
                pick = rng.integers(0, len(blocks), len(blocks))
                idx = np.concatenate([blocks[q] for q in pick])
                bsk.append(pes[k][idx].sum() / px[idx].sum())
            res[r]["sub_ci"].append([float(pes[k].sum() / px.sum()), *[float(x) for x in np.percentile(bsk, [2.5, 97.5])]])
        print(f"{lab:8s} {r}  n {n:3d}  J {J:.4f}  95% block-bootstrap [{lo:.4f}, {hi:.4f}]  leave-one-block-out "
              f"[{min(loo):.4f}, {max(loo):.4f}]  worst single window carries {100*wshare.max():.1f} % of the error")
        print("          sub-bands (value [CI]): " + "  ".join("%.2f-%.2f %.3f [%.3f, %.3f]" % (a, c, *res[r]["sub_ci"][k])
                                                        for k, (a, c) in enumerate(SUB)))
    json.dump(res, open(HERE / "j_metric_ci_out.json", "w"), indent=1)


if __name__ == "__main__":
    main()
