"""Pooled curvature (profile) 95% CI for rate_lp4 using the n-weighted mean N_eff/N from the per-route residual autocorrelation."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eqlib as E
routes = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd", "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]
for bi in range(3):
    allb = []; nf_num = 0; nf_den = 0
    for r in routes:
        B = np.load(f"blocks_{r}.npz"); R = json.load(open(f"real_{r}.json"))["rate_lp4"][str(bi)]
        allb += [dict(XX=B[f"rate_lp4_{bi}_XX"][i], Xy=B[f"rate_lp4_{bi}_Xy"][i], yy=B[f"rate_lp4_{bi}_yy"][i], n=int(B[f"rate_lp4_{bi}_n"][i])) for i in range(len(B[f"rate_lp4_{bi}_n"]))]
        nf_num += R["neff_frac"] * R["n"]; nf_den += R["n"]
    ssr, th, n = E.solve(allb)
    lo, hi, neff = E.curvature_ci(ssr, nf_num / nf_den, n)
    print(E.BINS[bi], "D %.1f" % E.argmin_sub(ssr)[0], "curv CI", (lo, hi), "Neff %.0f" % neff)
