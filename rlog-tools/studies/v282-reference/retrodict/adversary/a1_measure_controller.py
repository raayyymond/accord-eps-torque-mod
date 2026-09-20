"""A1 - measure, from each route's OWN log, the controller constants the retrodiction needs.

kp   = cs_p / cs_err                       (pid_log.p = kp * error_with_lsf)
LAF  = (cs_p + cs_i + cs_f) / cs_out       (output_torque = output_lataccel / latAccelFactor)

Both are read from the wire, not from params_all.json or from source, so they are an
independent check on the attribution the retrodiction rests on.
One route at a time; only the needed arrays are held.
"""
import json
import os
import numpy as np

CACHE = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref"
PARAMS = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/hsurface/surface/params_all.json"

params = json.load(open(PARAMS))


def robust_slope(x, y):
    """median of y/x on |x| above its own 60th pct - immune to the clipped/saturated tail."""
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if x.size < 200:
        return np.nan, 0
    thr = np.percentile(np.abs(x), 60)
    k = np.abs(x) > max(thr, 1e-6)
    if k.sum() < 100:
        return np.nan, 0
    r = y[k] / x[k]
    return float(np.median(r)), int(k.sum())


rows = []
for f in sorted(os.listdir(CACHE)):
    if not f.endswith(".npz"):
        continue
    key = f[:-4]
    z = np.load(os.path.join(CACHE, f))
    need = {"cs_p", "cs_i", "cs_f", "cs_err", "cs_out", "cs_active", "t_cs", "t_cst", "vego", "spress"}
    if not need.issubset(set(z.files)):
        print(key, "MISSING FIELDS")
        continue
    t = z["t_cs"]
    act = z["cs_active"] > 0.5
    p, i, ff, err, out = z["cs_p"], z["cs_i"], z["cs_f"], z["cs_err"], z["cs_out"]
    v = np.interp(t, z["t_cst"], z["vego"])
    sp = np.interp(t, z["t_cst"], z["spress"]) > 0.5
    sel = act & ~sp & (v >= 15.0) & np.isfinite(err)
    selall = act & ~sp
    kp, nkp = robust_slope(err[sel], p[sel])
    lat = p + i + ff
    unsat = np.abs(out) < 0.98
    laf, nlaf = robust_slope(out[sel & unsat], lat[sel & unsat])
    pa = params.get(key, {})
    rows.append(dict(route=key, kp_meas=kp, n_kp=nkp, laf_meas=laf, n_laf=nlaf,
                     SteerKP=pa.get("SteerKP"), SteerLatAccel=pa.get("SteerLatAccel"),
                     SteerFriction=pa.get("SteerFriction"), FrictionHyst=pa.get("AccordFrictionHyst"),
                     commit=str(pa.get("GitCommit"))[:9],
                     n_eng_s=float(selall.sum()) / 100.0, n_fast_s=float(sel.sum()) / 100.0))
    del z

hdr = f"{'route':22} {'commit':10} {'kp_meas':>8} {'SteerKP':>8} {'LAF_meas':>9} {'SteerLA':>8} {'SteerFric':>10} {'Hyst':>7} {'eng_s':>8} {'fast_s':>8}"
print(hdr)
print("-" * len(hdr))
for r in rows:
    print(f"{r['route']:22} {r['commit']:10} {r['kp_meas']:8.4f} {str(r['SteerKP']):>8} "
          f"{r['laf_meas']:9.4f} {str(r['SteerLatAccel']):>8} {str(r['SteerFriction'])[:10]:>10} "
          f"{str(r['FrictionHyst']):>7} {r['n_eng_s']:8.1f} {r['n_fast_s']:8.1f}")

json.dump(rows, open(os.path.join(os.path.dirname(__file__), "a1_controller_measured.json"), "w"), indent=1)
