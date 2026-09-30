# -*- coding: utf-8 -*-
"""h5_baseline.py -- gate H5 (determinism, the V293 control, the census anchors) and THE BASELINE TABLE the designers
compare against: V294 and V293 (C = 0 -> trim off, the control) through score() on the whole family.

Outputs: h5_baseline_out.txt (print_score of both + the compact table), _scratch/h5_baseline.json."""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v295_harness as H  # noqa: E402

PLANTS = ("nominal", "b_lo", "F_hi", "J_lo", "J_hi", "light_b", "tau6", "nominal_kappa")


def main():
    t0 = time.time()
    v294, v293 = H.Cells.v294(), H.Cells.v293()
    print("H5  determinism, controls, anchors")
    # determinism: two identical quick calls and two identical small sims
    a = H.score(v294, quick=True, verbose=False)
    b = H.score(v294, quick=True, verbose=False)
    ha, hb = H.score_hash(a), H.score_hash(b)
    fam = H.family()
    ch = H.route_chunks()[:4]
    R1 = H.simulate([v294], [fam["nominal"]], ch, H.SimOpts(mode="B", dist="lp"))
    R2 = H.simulate([v294], [fam["nominal"]], ch, H.SimOpts(mode="B", dist="lp"))
    same_sim = all(np.array_equal(R1[k], R2[k]) for k in ("ang", "T", "cmd", "la_act", "i"))
    print("  quick score hash %s == %s : %s ; mode-B sim bit-identical on a re-run: %s" % (ha[:16], hb[:16], ha == hb, same_sim))
    # the V293 control: C = 0 -> the trim is identically zero (T == the null shadow on every frame) and |L| == 0
    R3 = H.simulate([v293], [fam["nominal"], fam["light_b"]], ch, H.SimOpts(mode="B", dist="lp"), record_1k=True)
    trim_max = float(np.max(np.abs(R3["T"] - R3["T_null"])))
    Lmax = max(float(np.max(np.abs(H.loop_frf(v293, fam[p].at(v), np.logspace(-1, 1.6, 200))))) for p in PLANTS for v in (5.0, 20.0))
    print("  V293 control: max |T - T_null| over every frame %.0f ; max |L| over the family %.3g" % (trim_max, Lmax))
    s = a["M_SAFE"]
    anchors = dict(rail_pos=s["rail_pos"] == 2461, b_max=abs(s["b_max"] - 2301) < 1, zero_cmd=s["T_at_zero_cmd_max"] <= 616)
    print("  V294 anchors: rail +%d (census 2461) ; b_max %.1f (census 2301) ; T at zero command %d (census <= 616)"
          % (s["rail_pos"], s["b_max"], s["T_at_zero_cmd_max"]))
    g5 = (ha == hb) and same_sim and trim_max == 0 and Lmax == 0 and all(anchors.values())
    print("H5 %s" % ("PASS" if g5 else "FAIL"))
    # ------------------------------------------------------------------ the baseline
    print("\nBASELINE: V294 (as built) and V293 (C = 0, trim off) in ONE batch, plants %s" % (PLANTS,))
    ts = time.time()
    r = H.score(v293, plants=PLANTS, base=v294)
    print("  score(V293, base=V294): %.0f s" % (time.time() - ts))
    with open(os.path.join(HERE, "h5_baseline_full_out.txt"), "w", encoding="utf-8") as fh:
        H.print_score(r, file=fh)
        H.print_score(H.score(v294, quick=True, plants=PLANTS, verbose=False), file=fh)
    meas = r["M_DRIVE"]["measured"]
    bands = [b for b, _, _ in H.BANDS]
    print("\n  M_DRIVE (mode B) by band -- measured r71b | V294 sim | V293 sim, plant NOMINAL (the other members in the full file)")
    for dist in ("lp", "full"):
        for k in ("track_gain", "turn_hold", "straight_delivery", "J_err", "i_share", "cmd_rms", "trim_ff", "r_lo", "r_mid", "r_hi",
                  "hard16", "dwell_per_min"):
            row = []
            for bnd in bands:
                m_ = meas.get(bnd, {}).get(k, np.nan)
                s4 = r["M_DRIVE"]["sim"][(dist, "V294", "nominal")].get(bnd, {}).get(k, np.nan)
                s3 = r["M_DRIVE"]["sim"][(dist, "V293", "nominal")].get(bnd, {}).get(k, np.nan)
                row.append("%7.3f %7.3f %7.3f" % (m_, s4, s3))
            print("   %-4s %-18s | %s" % (dist, k, " | ".join(row)))
    print("   (columns per band: measured, V294, V293; bands %s)" % bands)
    print("\n  M_DRIVE V294 vs V293 across the family (dist lp: tracking gain / hard-turn 1.6-3 Hz rate; dist full: same):")
    for p in PLANTS:
        for dist in ("lp", "full"):
            x4 = r["M_DRIVE"]["sim"][(dist, "V294", p)]
            x3 = r["M_DRIVE"]["sim"][(dist, "V293", p)]
            print("   %-14s %-4s track %s | V293 %s   hard16 %s | V293 %s   limit %.2f Hz %+.1f dB | V293 %.2f Hz %+.1f dB"
                  % (p, dist, " ".join("%.3f" % x4[b]["track_gain"] for b in bands), " ".join("%.3f" % x3[b]["track_gain"] for b in bands),
                     " ".join("%.2f" % x4[b]["hard16"] for b in bands), " ".join("%.2f" % x3[b]["hard16"] for b in bands),
                     x4["limit_cycle"]["f"], x4["limit_cycle"]["dB"], x3["limit_cycle"]["f"], x3["limit_cycle"]["dB"]))
    print("\n  M_LOOP V294 (V293's |L| is 0 by construction):")
    q = H.score(v294, quick=True, plants=PLANTS, verbose=False)
    for (p, v), x in q["M_LOOP"].items():
        print("   %-14s v %4.1f |L| 1-3 %.2f 3-8 %.2f Ms %.3f GM %.1f Ms(delay x1.5) %.3f stable %s modes %s"
              % (p, v, x["L13"], x["L38"], x["Ms"], x["GM_min"], x["Ms_delay15"], x["stable"], x["modes"][:3]))
    print("\n  M_HF: delivered-torque rms per band (T counts), 1 kHz, mode A (dist full) and mode B (dist lp) -- V294 | V293")
    for key in ("sim_A", "sim_B"):
        for k, x in r["M_HF"].get(key, {}).items():
            print("   %s %s %s" % (key, k, {kk: round(vv, 3) for kk, vv in x.items()}))
    print("   stress modes (zeta): V293 = open ; V294 from q:")
    for k, x in q["M_HF"]["stress_modes"].items():
        print("   %-10s v %4.1f f %.1f Hz zeta V294 %.3f open %.3f" % (k[0], k[1], x["f"], x["zeta_V294"], x["zeta_open"]))
    print("\n  M_TRACK mode A (V294 | V293), probe transfer per band (|G| deg/s^2 per count, phase, coherence):")
    for k, x in r["M_TRACK"]["modeA"].items():
        print("   %s %s" % (k, {kk: {a_: round(b_, 3) for a_, b_ in vv.items()} for kk, vv in x.items() if kk.startswith("probe")}))
    print("   flatness |alpha/cmd| 1-3 Hz at 30/100/300 counts rms: %s" % {str(k): round(v, 3) for k, v in r["M_TRACK"]["flatness"].items()})
    json.dump(H.to_jsonable(dict(V293_vs_V294=r, V294_quick=q)), open(os.path.join(HERE, "_scratch", "h5_baseline.json"), "w"),
              indent=1)
    print("\n  total %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
