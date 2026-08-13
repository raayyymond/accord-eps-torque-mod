#!/usr/bin/env python3
r"""⭐ THE CONTROL THAT DECIDES THE >120 deg DROOP.

The pre-registered positive control ("plateau flat beyond 120 deg") FAILED.  Two readings are
possible and they must be separated:
    (i)  the estimator is broken and invents a droop where the rack is flat, or
    (ii) the rack really keeps quickening and the control's PREMISE was wrong.

This is the direct test.  Three synthetic racks are built from the REAL theta and the REAL sample
noise, pushed through the IDENTICAL pipeline, and scored with the IDENTICAL statistics:

  NULL-1  CONSTANT ratio everywhere                -> pipeline must return swing 1.000, droop 1.000
  NULL-2  FIRMWARE-SHAPED rack: the measured notch over 0-120 deg, then EXACTLY FLAT beyond
          -> pipeline must return the measured swing but droop 1.000.  🛑 THIS IS THE ONE THAT
             MATTERS: if the pipeline returns droop ~1.24 here, the droop is an artefact.
  RECOVERY the MEASURED rack -> pipeline must return the measured swing AND the measured droop.

The noise is the real per-sample residual (delta_measured - delta_on_the_fitted-curve), resampled
WITHIN speed bins, so its magnitude, its speed dependence and its heavy tail are all preserved.
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure_steering_ratio as M  # noqa: E402
import ratio_final2 as F2  # noqa: E402
import ratio_lib as R  # noqa: E402

OUT = R.ROOT / "analysis-2020accord" / "_cache_ratio"


def main(nrep=250, seed=9):
    A = M.prep()
    M.qa(A)
    A["v_front"] = R.smooth_blocks(A, 0.5 * (A["ws_fl"] + A["ws_fr"]), 0.5)
    gam = F2.gamma_front_rear(A)
    th0 = M.fit_theta0(A, "A")
    prim = R.base_mask(A, vmin=1.0, vmax=5.0) & R.steady_mask(A)
    D = F2.deltas(A, gam)

    th_c = A["s_ang"][prim] - th0
    v = A["v_ref"][prim]
    dlt = D["A"][prim]
    ta, sec, loc, _ = M.curve_from(th_c, dlt, M.BINS)
    real = F2.stats(ta, loc)

    # ---- the MEASURED delta(theta), as a monotone interpolant through the signed bin medians
    s = np.sign(th_c); s[s == 0] = 1
    ok = np.isfinite(ta)
    kt = np.concatenate([[0.0], ta[ok]])
    kd = np.concatenate([[0.0], (ta / sec)[ok]])
    o = np.argsort(kt)
    kt, kd = kt[o], kd[o]
    d_meas = np.interp(np.abs(th_c), kt, kd) * s
    resid = dlt - d_meas

    # ---- NULL-1: one constant ratio everywhere
    d_flat = th_c / real["ref120"]

    # ---- NULL-2: the measured curve up to 120 deg, then EXACTLY the firmware's flat continuation
    ref_loc = real["ref120"]
    kt2, kd2 = kt.copy(), kd.copy()
    for i in range(1, len(kt2)):
        if kt2[i] > 120.0:                       # beyond 120 deg: constant local ratio
            kd2[i] = kd2[i - 1] + (kt2[i] - kt2[i - 1]) / ref_loc
    d_fw = np.interp(np.abs(th_c), kt2, kd2) * s

    rng = np.random.default_rng(seed)
    vb = np.digitize(v, [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5])
    acc = {k: {"swing_0_to_120": [], "droop_120_to_380": []}
           for k in ("NULL1_constant", "NULL2_firmware_shaped", "RECOVERY_measured")}
    srcs = {"NULL1_constant": d_flat, "NULL2_firmware_shaped": d_fw,
            "RECOVERY_measured": d_meas}
    for _ in range(nrep):
        rs = resid.copy()
        for b in np.unique(vb):
            q = np.flatnonzero(vb == b)
            rs[q] = resid[rng.choice(q, len(q), replace=True)]
        for k, src in srcs.items():
            c = M.curve_from(th_c, src + rs, M.BINS)
            st = F2.stats(c[0], c[2])
            for f in ("swing_0_to_120", "droop_120_to_380"):
                if np.isfinite(st[f]):
                    acc[k][f].append(st[f])

    out = {"measured": real, "n_rep": nrep, "results": {}}
    print("\n" + "=" * 92)
    print("  ⭐ SYNTHETIC-RACK CONTROLS -- real theta, real noise, identical pipeline")
    print("=" * 92)
    print(f"  MEASURED:  swing(0->120) = {real['swing_0_to_120']:.4f}   "
          f"droop(120->380) = {real['droop_120_to_380']:.4f}")
    print("\n  synthetic rack             swing(0->120)              droop(120->380)"
          "        truth")
    truths = {"NULL1_constant": (1.0, 1.0),
              "NULL2_firmware_shaped": (real["swing_0_to_120"], 1.0),
              "RECOVERY_measured": (real["swing_0_to_120"], real["droop_120_to_380"])}
    verdict = {}
    for k in srcs:
        sw = np.array(acc[k]["swing_0_to_120"]); dr = np.array(acc[k]["droop_120_to_380"])
        t = truths[k]
        row = {"swing": [float(np.median(sw)), float(np.percentile(sw, 2.5)),
                         float(np.percentile(sw, 97.5))],
               "droop": [float(np.median(dr)), float(np.percentile(dr, 2.5)),
                         float(np.percentile(dr, 97.5))],
               "truth_swing": t[0], "truth_droop": t[1]}
        row["swing_PASS"] = bool(abs(row["swing"][0] - t[0]) < 0.03)
        row["droop_PASS"] = bool(abs(row["droop"][0] - t[1]) < 0.03)
        out["results"][k] = row
        verdict[k] = row["swing_PASS"] and row["droop_PASS"]
        print(f"  {k:24s}  {row['swing'][0]:.4f} [{row['swing'][1]:.4f},{row['swing'][2]:.4f}]  "
              f"  {row['droop'][0]:.4f} [{row['droop'][1]:.4f},{row['droop'][2]:.4f}]   "
              f"({t[0]:.4f}, {t[1]:.4f})   "
              f"{'PASS' if verdict[k] else 'FAIL'}")

    n2 = out["results"]["NULL2_firmware_shaped"]
    print(f"\n  🛑 THE DECIDING LINE: a rack that is EXACTLY FLAT beyond 120 deg is read back by "
          f"this\n     pipeline as droop = {n2['droop'][0]:.4f} "
          f"[{n2['droop'][1]:.4f}, {n2['droop'][2]:.4f}].  The real data give "
          f"{real['droop_120_to_380']:.4f}.")
    print("     ⇒ the pipeline CANNOT manufacture the droop; the rack really keeps quickening."
          if real["droop_120_to_380"] > n2["droop"][2] else
          "     ⇒ the droop is INSIDE what the pipeline invents on a flat rack -- NOT REPORTABLE.")
    out["DROOP_IS_REAL"] = bool(real["droop_120_to_380"] > n2["droop"][2])
    (OUT / "null_droop.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"\nwrote {OUT / 'null_droop.json'}")


if __name__ == "__main__":
    main()
