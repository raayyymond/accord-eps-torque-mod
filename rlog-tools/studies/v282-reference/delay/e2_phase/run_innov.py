"""Real data, INNOVATION-instrument IV (and setpoint IV, direct for reference): per route and POOLED across routes,
per speed bin, rate fits at coherence gates 0.5 and 0.3; route-cluster bootstrap for the pooled estimate.
usage: python run_innov.py route [...]   (writes out/innov_rows_<route>.npz, then pools all present)"""
import sys, json, glob
from pathlib import Path
import numpy as np
import common as C, estimate as E
import os
OUT = Path(__file__).resolve().parent / ("out" if os.environ.get("INNOV_ULAGS","1") != "0" else "out_noulag")
OUT.mkdir(exist_ok=True)
BINS = [(0.0, 8.0), (8.0, 15.0), (15.0, 99.0), (0.0, 99.0)]
routes = sys.argv[1:]
for route in routes:
    R = C.load_route(route); mask = C.handsoff_mask(R)
    R["innov"] = C.innovation(R, mask)
    f, rows = E.chunk_stack(R, mask, zkey="innov")
    np.savez_compressed(OUT / f"innov_rows_{route}.npz", f=f, v=np.array([r["v"] for r in rows]),
                        **{k: np.array([r[k] for r in rows]) for k in rows[0] if k.startswith("S")})
    del R, rows


def load_rows(fn):
    Z = np.load(fn); ks = [k for k in Z.files if k.startswith("S")]
    return Z["f"], [dict(v=float(Z["v"][i]), **{k: Z[k][i] for k in ks}) for i in range(len(Z["v"]))]


res = {}
allrows = {}
for fn in sorted(glob.glob(str(OUT / "innov_rows_*.npz"))):
    rt = fn.split("innov_rows_")[1][:-4]
    if rt not in routes and routes and "--pool" not in sys.argv:
        pass
    f, rows = load_rows(fn); allrows[rt] = rows
torque = [r for r in C.TORQUE_ROUTES if r in allrows]
rng = np.random.default_rng(7)
for lo, hi in BINS:
    for cm in (0.5, 0.3):
        for est in ("iv", "direct"):
            for rt in list(allrows) + ["POOLED_TORQUE"]:
                rr = ([r for t in torque for r in allrows[t]] if rt == "POOLED_TORQUE" else allrows[rt])
                rr = [r for r in rr if lo <= r["v"] < hi]
                x = E.fit_bin(f, rr, est=est, out="rate", cmin=cm, nboot=(0 if rt == "POOLED_TORQUE" else 60))
                ft = x["fit"] if x else None
                ci = x.get("D_boot_ci95") if x else None
                if rt == "POOLED_TORQUE" and ft:
                    Ds = []
                    for _ in range(100):   # route-cluster bootstrap, chunks resampled within each drawn route
                        pick = rng.choice(torque, len(torque))
                        rb = []
                        for t in pick:
                            cand = [r for r in allrows[t] if lo <= r["v"] < hi]
                            if cand:
                                rb += [cand[i] for i in rng.integers(0, len(cand), len(cand))]
                        xb = E.fit_bin(f, rb, est=est, out="rate", cmin=cm, nboot=0) if rb else None
                        if xb and xb.get("fit"):
                            Ds.append(xb["fit"]["D"])
                    if len(Ds) >= 10:
                        ci = [float(np.percentile(Ds, 2.5)), float(np.percentile(Ds, 97.5))]
                        x["D_cluster_ci95"] = ci; x["n_boot_ok"] = len(Ds)
                key = f"{rt}|v{lo:.0f}-{hi:.0f}|coh>{cm}|{est}_innov"
                res[key] = x
                print(key, "n", len(rr), (f"D {ft['D']*1e3:.1f} CI {[round(c*1e3,1) for c in ci] if ci else None} J {ft['J']:.1e} b {ft['b']:.1e} k {ft['k']:.1e} corrDJ {ft['corr_D_J']:+.2f} bins {ft['nbins']} f {ft['fmin']:.1f}-{ft['fmax']:.1f}") if ft else "--", flush=True)
                if ft and rt == "POOLED_TORQUE":
                    print("    coh bins", x["coh_bins"], flush=True)
(OUT / "innov_results.json").write_text(json.dumps(res, indent=1, default=float))
