"""Pool the torque routes: per bin D_opt, route-cluster bootstrap, block bootstrap, SSR depth; per-route summary table.
usage: python pooled.py [cfg] [routes...]"""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eqlib as E
cfg = sys.argv[1] if len(sys.argv) > 1 else "rate_lp4"
routes = sys.argv[2:] or ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd", "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]
out = {}
for bi in range(3):
    units = []
    for r in routes:
        B = np.load(f"blocks_{r}.npz")
        if f"{cfg}_{bi}_XX" not in B.files:
            continue
        XX, Xy, yy, n = B[f"{cfg}_{bi}_XX"], B[f"{cfg}_{bi}_Xy"], B[f"{cfg}_{bi}_yy"], B[f"{cfg}_{bi}_n"]
        units.append([dict(XX=XX[i], Xy=Xy[i], yy=yy[i], n=int(n[i]), route=r) for i in range(len(n))])
    allb = [b for u in units for b in u]
    ssr, th, n = E.solve(allb); d, k = E.argmin_sub(ssr)
    rc = E.bootstrap(units, nboot=1000, seed=1)
    bb = E.bootstrap([[b] for b in allb], nboot=1000, seed=2)
    out[bi] = dict(D=d, n=n, seconds=n / 100.0, route_cluster_ci=np.percentile(rc, [2.5, 97.5]).tolist(),
                   block_ci=np.percentile(bb, [2.5, 97.5]).tolist(), depth_pct=float(100 * (ssr.max() - ssr.min()) / ssr.min()),
                   depth_0_to_min_pct=float(100 * (ssr[0] - ssr.min()) / ssr.min()),
                   ssr_rel_every10=(ssr[::10] / ssr.min()).round(4).tolist(),
                   th=dict(zip(E.NAMES, th[k].tolist())), th_m10=dict(zip(E.NAMES, th[max(k-10,0)].tolist())),
                   th_p10=dict(zip(E.NAMES, th[min(k+10,120)].tolist())),
                   r2=float(1 - ssr[k] / sum(b["yy"][k] for b in allb)))
    print(cfg, "bin", E.BINS[bi], json.dumps({kk: (np.round(vv, 5).tolist() if isinstance(vv, (list, float)) else vv) for kk, vv in out[bi].items()}))
json.dump(out, open(f"pooled_{cfg}_{len(routes)}r.json", "w"), indent=1)
