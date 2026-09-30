"""ADV-D step 6b: V295 vs V294 from d6_score.json, plus V294's own M_LOOP and outer-loop margins on the SAME members
(score() computes those for the candidate only), so every number is paired."""
import sys, json
import numpy as np
from dataclasses import replace
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import v295_harness as H
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
V295 = FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
c5 = H.Cells.from_image(V295, "V295", "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed")
c4 = H.Cells.v294()
r = json.load(open("d6_score.json"))
fam = H.family()
plants = list(H.DEFAULT_PLANTS) + [p for p in H.STRESS_PLANTS if p not in H.DEFAULT_PLANTS]
print("=== M_SAFE ===")
for nm, s in (("V295", r["M_SAFE"]), ("V294", r["M_SAFE_V294"])):
    print("  %s rail +%d/%d  subrail %.4f  cap %d  int32 min %.3f  restart %s" % (nm, s["rail_pos"], s["rail_neg"],
          s["subrail_T_per_wire"], s["trim_cap_T"], min(v["margin"] for v in s["int32"].values()),
          {k: (v["peak"], v["ms_above_50"]) for k, v in s["restart"].items()}))

print("\n=== M_LOOP inner: V295 vs V294 (same members/speeds); worst rows ===")
L4 = H.m_loop(c4, fam, tuple(plants))
rows = []
for key, x in r["M_LOOP"].items():
    nm, v = key.split("|"); v = float(v)
    y = L4[(nm, v)]
    rows.append((nm, v, x["Ms"], y["Ms"], x["Ms_delay15"], y["Ms_delay15"], x["GM_min"], y["GM_min"], x["stable"], y["stable"],
                 x["L13"], y["L13"]))
unstable = [r_ for r_ in rows if r_[8] is not True and r_[9] is True]
print("  rows %d; unstable-on-V295-only: %d; V295 max Ms %.3f (%s %.1f); max Ms at delay x1.5 %.3f (%s %.1f); min GM %.2f (%s %.1f)" % (
    len(rows), len(unstable), max(r_[2] for r_ in rows), *max(rows, key=lambda t: t[2])[:2],
    max(r_[4] for r_ in rows), *max(rows, key=lambda t: t[4])[:2], min(r_[6] for r_ in rows), *min(rows, key=lambda t: t[6])[:2]))
print("  %-13s %5s | Ms V295/V294 | Ms x1.5 V295/V294 | GMmin V295/V294 | |L|1-3 V295/V294" % ("plant", "v"))
for r_ in rows:
    if r_[0] in ("nominal", "light_b", "tau9", "b_lo", "J_hi2", "mode20_lo"):
        print("  %-13s %5.1f | %.3f / %.3f | %.3f / %.3f | %6.1f / %6.1f | %.2f / %.2f" % (r_[0], r_[1], r_[2], r_[3], r_[4], r_[5],
              r_[6], r_[7], r_[10], r_[11]))

print("\n=== M_DRIVE outer loop (unchanged fork law r1): V295 vs V294 ===")
worst = []
for key, x in r["M_DRIVE"]["outer"].items():
    nm, v, relay = key.split("|"); v = float(v); relay = relay == "True"
    p = fam[nm].at(v)
    ff = np.logspace(-2, np.log10(20.0), 800)
    mg = H.margins(ff, H.outer_frf(c4, p, v, ff, relay=relay))
    worst.append((nm, v, relay, x["GM_min"], mg["GM_min"], x["PM_min"], mg["PM_min"], x["Ms"], mg["Ms"]))
print("  %-8s %5s %-5s | GM V295/V294 (ratio) | PM V295/V294 (d) | Ms V295/V294" % ("plant", "v", "relay"))
for w in worst:
    print("  %-8s %5.1f %-5s | %6.2f / %6.2f (x%.3f) | %6.1f / %6.1f (%+.1f) | %.3f / %.3f" % (w[0], w[1], w[2], w[3], w[4], w[3] / w[4],
          w[5], w[6], w[5] - w[6], w[7], w[8]))
gmr = [w[3] / w[4] for w in worst]
dpm = [w[5] - w[6] for w in worst]
print("  GM ratio range %.3f .. %.3f ; PM change range %+.1f .. %+.1f deg" % (min(gmr), max(gmr), min(dpm), max(dpm)))

print("\n=== M_HF simulated delivered torque, V295 / V294 ===")
worstHF = (0, None)
for key in ("sim_A", "sim_B"):
    for k, x in r["M_HF"][key].items():
        parts = k.split("|")
        if "V295" not in parts:
            continue
        kb = "|".join(["V294" if p == "V295" else p for p in parts])
        y = r["M_HF"][key][kb]
        rat = {b: x[b] / y[b] for b in x}
        mx = max(rat.items(), key=lambda t: t[1])
        if mx[1] > worstHF[0]:
            worstHF = (mx[1], (key, k, mx[0]))
        print("  %s %-24s %s" % (key, k, "  ".join("%s x%.2f" % (b, v_) for b, v_ in rat.items())))
print("  WORST band ratio x%.3f at %s" % worstHF)
h = r["M_HF"]
print("  |P/x| 20 Hz: V295 %.3f  V294 %.3f  V282 %.3f -> x%.3f of V294, %.1f %% of V282" % (h["P_per_x"][4], h["P_per_x_V294"][4],
      h["P_per_x_V282"][4], h["P_per_x"][4] / h["P_per_x_V294"][4], 100 * h["P_per_x"][4] / h["P_per_x_V282"][4]))
for k, x in h["stress_modes"].items():
    print("  stress %-16s zeta V295 %.4f  V294 %.4f  open %.4f  (V295-open %+.4f, V294-open %+.4f)" % (k, x["zeta"], x["zeta_V294"],
          x["zeta_open"], x["zeta"] - x["zeta_open"], x["zeta_V294"] - x["zeta_open"]))

print("\n=== M_DRIVE sim (mode B, fork in loop): V295 vs V294, per dist x plant x band ===")
S = r["M_DRIVE"]["sim"]
keys = ("track_gain", "turn_hold", "straight_delivery", "J_err", "r_lo", "r_mid", "r_hi", "hard16", "i_share", "cmd_rms")
flags = []
for k, x in S.items():
    dist, cn, pl = k.split("|")
    if cn != "V295":
        continue
    y = S["%s|V294|%s" % (dist, pl)]
    print("  -- %s %s  limit-cycle V295 %.2f Hz %+.1f dB rms %.2f | V294 %.2f Hz %+.1f dB rms %.2f" % (dist, pl,
          x["limit_cycle"]["f"], x["limit_cycle"]["dB"], x["limit_cycle"]["rms"], y["limit_cycle"]["f"], y["limit_cycle"]["dB"],
          y["limit_cycle"]["rms"]))
    for band in ("0-5", "5-10", "10-15", "15-22", "22+"):
        if band not in x or band not in y:
            continue
        a, b = x[band], y[band]
        s = []
        for kk in keys:
            va, vb = a.get(kk, np.nan), b.get(kk, np.nan)
            if kk in ("track_gain", "turn_hold", "straight_delivery", "i_share"):
                s.append("%s %+.3f" % (kk[:6], va - vb) if np.isfinite(va) and np.isfinite(vb) else "%s n/t" % kk[:6])
                if kk in ("track_gain", "turn_hold") and np.isfinite(va) and np.isfinite(vb) and va - vb < -0.01:
                    flags.append((dist, pl, band, kk, va - vb))
            else:
                s.append("%s x%.3f" % (kk[:6], va / vb) if np.isfinite(va) and np.isfinite(vb) and vb else "%s n/t" % kk[:6])
        print("     %-6s %s" % (band, " ".join(s)))
print("\nFLAGS (tracking gain / turn-hold worse than V294 by > 0.01):", flags)
