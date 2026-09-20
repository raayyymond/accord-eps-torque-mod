"""A2b - identify the relay's amplitude from the log by its SHAPE, not by a plateau difference.

The relay contributes  F*LAF * clip((err + 0.22*jerk)/0.30, -1, 1)  to the logged feedforward.
Everything else in ff is driven by the desired angle / rate and is smooth in err over a small
window.  So regress
        cs_f  ~  a0 + a1*e + a2*e^2 + a3*e^3 + C * clip(u/0.30,-1,1)
over |e| < 1.5, where u = e + 0.22 * cs_la_jerk.  C identifies F*LAF: the saturating kink at
|u| = 0.30 is not reproducible by a low-order polynomial in e.

Control: routes flown with SteerFriction = 0 must return C ~ 0.
"""
import json
import os
import numpy as np

CACHE = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref"
PARAMS = json.load(open(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/hsurface/surface/params_all.json"))

ROUTES = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac",
          "00000070--717f5a7866", "00000071--f2c9d073a3", "00000072--8001fc3048",
          "00000073--79fd149dd8", "00000075--6c8687d5bd", "0000006d--05e83bb04f",
          "0000006c--68c6e94b17", "00000076--d0b7ea7e4d"]


def boot_ci(X, y, nb=200, seed=0):
    rng = np.random.default_rng(seed)
    n = len(y)
    out = []
    # block bootstrap, 10 s blocks at 100 Hz, to respect autocorrelation
    bl = 1000
    nblk = max(n // bl, 1)
    for _ in range(nb):
        idx = np.concatenate([np.arange(s, min(s + bl, n)) for s in rng.integers(0, max(n - bl, 1), nblk)])
        try:
            c = np.linalg.lstsq(X[idx], y[idx], rcond=None)[0]
            out.append(c[-1])
        except Exception:
            pass
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


print(f"{'route':22} {'F_param':>9} {'LAF':>5} {'F*LAF pred':>11} {'C fitted':>9} {'95% CI':>22} {'F_implied':>10} {'n':>7}")
print("-" * 105)
res = {}
for key in ROUTES:
    z = np.load(os.path.join(CACHE, key + ".npz"))
    t = z["t_cs"]
    act = z["cs_active"] > 0.5
    e_all, f_all, j_all = z["cs_err"], z["cs_f"], z["cs_la_jerk"]
    v = np.interp(t, z["t_cst"], z["vego"])
    sp = np.interp(t, z["t_cst"], z["spress"]) > 0.5
    sel = act & ~sp & (v >= 15.0) & np.isfinite(e_all) & np.isfinite(f_all) & (np.abs(e_all) < 1.5)
    del z
    e, f, j = e_all[sel], f_all[sel], j_all[sel]
    if e.size < 500:
        print(f"{key:22}  too few samples ({e.size})")
        continue
    u = e + 0.22 * j
    g = np.clip(u / 0.30, -1.0, 1.0)
    X = np.column_stack([np.ones_like(e), e, e ** 2, e ** 3, g])
    c = np.linalg.lstsq(X, f, rcond=None)[0]
    lo, hi = boot_ci(X, f)
    pa = PARAMS[key]
    F = float(pa["SteerFriction"])
    LAF = float(pa["SteerLatAccel"])
    res[key] = dict(C=float(c[-1]), lo=lo, hi=hi, F_param=F, LAF=LAF, n=int(e.size))
    print(f"{key:22} {F:9.5f} {LAF:5.1f} {F*LAF:11.3f} {c[-1]:9.3f} [{lo:9.3f},{hi:9.3f}] "
          f"{c[-1]/LAF:10.4f} {e.size:7d}")

json.dump(res, open(os.path.join(os.path.dirname(__file__), "a2b_relay_fit.json"), "w"), indent=1)
