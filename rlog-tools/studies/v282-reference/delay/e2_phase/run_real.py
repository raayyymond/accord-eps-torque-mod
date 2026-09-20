"""Real data: per route, per speed bin, DIRECT and IV (setpoint instrument) fits of D_act, angle / rate / joint,
block-bootstrap CIs over 10.24 s chunks, J-profile. Stores the per-chunk spectra so pooling can be done later.

usage: python run_real.py route [route ...]
"""
import sys, json
from pathlib import Path
import numpy as np
import common as C, estimate as E

OUT = Path(__file__).resolve().parent / "out"; OUT.mkdir(exist_ok=True)
JGRID = [2e-5, 4e-5, 8e-5, 1.5e-4, 3e-4, 6e-4, 1e-3]


def joint_bin(f, rows, est, fband=(1.5, 8.0), cmin=0.5, nboot=100, rng=None):
    if len(rows) < 1:
        return None
    S = E.combine(rows)
    Ha, ca = E.H_of(S, est, "angle"); Hr, cr = E.H_of(S, est, "rate")
    nave = len(rows) * 7
    r = C.fit_joint(f, -Ha, ca, -Hr, cr, nave, fband=fband, cmin=cmin)
    if r is None:
        return None
    out = dict(fit=r)
    if nboot and len(rows) >= 3:
        rng = rng or np.random.default_rng(1)
        Ds = []
        for _ in range(nboot):
            Sb = E.combine(rows, rng.integers(0, len(rows), len(rows)))
            Ha_, ca_ = E.H_of(Sb, est, "angle"); Hr_, cr_ = E.H_of(Sb, est, "rate")
            rb = C.fit_joint(f, -Ha_, ca_, -Hr_, cr_, nave, fband=fband, cmin=cmin, Dstarts=(r["D"],))
            if rb:
                Ds.append(rb["D"])
        if len(Ds) >= 10:
            out["D_boot_ci95"] = [float(np.percentile(Ds, 2.5)), float(np.percentile(Ds, 97.5))]
            out["n_boot_ok"] = len(Ds)
    return out


if __name__ == "__main__":
    for route in sys.argv[1:]:
        R = C.load_route(route)
        mask = C.handsoff_mask(R)
        f, rows = E.chunk_stack(R, mask, zkey="sp")
        np.savez_compressed(OUT / f"spectra_{route}.npz", f=f, v=np.array([r["v"] for r in rows]),
                            **{k: np.array([r[k] for r in rows]) for k in rows[0] if k.startswith("S")})
        res = dict(route=route, handsoff_s=float(mask.sum() / C.FS), n_chunks=len(rows))
        for lo, hi in C.SPEED_BINS:
            rr = [r for r in rows if lo <= r["v"] < hi]
            key = f"v{lo:.0f}-{hi:.0f}"
            res[key] = dict(n_chunks=len(rr))
            for est in ("direct", "iv"):
                for out in ("angle", "rate"):
                    x = E.fit_bin(f, rr, est=est, out=out, nboot=100, jgrid=JGRID if out == "rate" else None)
                    res[key][f"{est}_{out}"] = x
                    ft = x["fit"] if x else None
                    ci = x.get("D_boot_ci95") if x else None
                    print(route, key, est, out, "n", len(rr),
                          (f"D {ft['D']*1e3:.1f} CI {[round(c*1e3,1) for c in ci] if ci else None} J {ft['J']:.1e} b {ft['b']:.1e} "
                           f"k {ft['k']:.1e} corrDJ {ft['corr_D_J']:+.2f} bins {ft['nbins']} gd_raw "
                           f"{x['group_delay_raw']['tau']*1e3 if x['group_delay_raw'] else float('nan'):.1f} gd_corr "
                           f"{x['group_delay_plant_removed']['tau']*1e3 if x['group_delay_plant_removed'] else float('nan'):.1f}") if ft else None,
                          flush=True)
                    if ft and x.get("J_profile"):
                        print("     J-profile:", [(p["J"], round(p["D"] * 1e3, 1), round(p["cost"], 1)) for p in x["J_profile"]], flush=True)
                j = joint_bin(f, rr, est)
                res[key][f"{est}_joint"] = j
                if j:
                    print(route, key, est, "JOINT D", round(j["fit"]["D"] * 1e3, 1), "CI",
                          [round(c * 1e3, 1) for c in j.get("D_boot_ci95", [np.nan, np.nan])], f"J {j['fit']['J']:.1e}", flush=True)
        (OUT / f"real_{route}.json").write_text(json.dumps(res, indent=1, default=float))
        del R, rows
