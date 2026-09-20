"""Diagnostic: print the MEASURED phase of H = S_uy/S_uu (command -> steering rate, sign-corrected) bin by bin,
next to the fitted model's phase, for one route and speed bin. Purpose: adjudicate the disagreement between the
parametric D (positive 6-19 ms) and the model-free phase slope (negative) on real data.

usage: python ph_diag.py <spectra.npz|innov_rows.npz> vlo vhi
"""
import sys
import numpy as np
import common as C, estimate as E

fn, lo, hi = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
Z = np.load(fn)
f = Z["f"]; v = Z["v"]
ks = [k for k in Z.files if k.startswith("S")]
rows = [dict(v=float(v[i]), **{k: Z[k][i] for k in ks}) for i in range(len(v)) if lo <= v[i] < hi]
print(fn, f"v{lo}-{hi}", "chunks", len(rows))
S = E.combine(rows)
for out in ("rate", "angle"):
    H, coh = E.H_of(S, "direct", out)
    H = -H
    nave = len(rows) * 7
    ft = C.fit_tf(f, H, coh, nave, fband=(1.5, 8.0), cmin=0.5, out=out)
    print(f"\n-- {out}: fit D {ft['D']*1e3:.1f} ms J {ft['J']:.2e} b {ft['b']:.1e} k {ft['k']:.1e} nb {ft['nbins']}")
    w = 2 * np.pi * f
    mod = C.model_H(np.maximum(w, 1e-9), ft["D"], ft["J"], ft["b"], ft["k"], out)
    sel = (f >= 1.0) & (f <= 9.0)
    print("   f    coh   |H|meas   |H|mod    ph_meas  ph_mod  d(ph)  used")
    pm = np.unwrap(np.angle(H[sel])); pmo = np.unwrap(np.angle(mod[sel]))
    # align the two unwraps at the first used bin
    for i, (ff, cc, hm, hmo, p1, p2) in enumerate(zip(f[sel], coh[sel], np.abs(H[sel]), np.abs(mod[sel]), pm, pmo)):
        use = "*" if (cc > 0.5 and 1.5 <= ff <= 8.0) else " "
        print(f" {ff:5.2f} {cc:5.2f} {hm:9.3e} {hmo:9.3e} {np.degrees(p1):8.1f} {np.degrees(p2):7.1f} {np.degrees(p1-p2):6.1f}  {use}")
    # weighted phase slope on the used bins, of the measured phase and of the model phase
    u = (coh > 0.5) & (f >= 1.5) & (f <= 8.0)
    for name, ph in (("meas", np.unwrap(np.angle(H[u]))), ("model", np.unwrap(np.angle(mod[u])))):
        ww = 2 * np.pi * f[u]; wt = coh[u] / np.maximum(1 - coh[u], 1e-3)
        A = np.vstack([ww, np.ones_like(ww)]).T; W = np.sqrt(wt)
        sol, *_ = np.linalg.lstsq(A * W[:, None], ph * W, rcond=None)
        print(f"   phase-slope {name}: tau = {-sol[0]*1e3:+.1f} ms  (intercept {np.degrees(sol[1]):.0f} deg)")
