# -*- coding: utf-8 -*-
"""h4_retrodict.py -- gate H4 (CRITERIA-HARNESS.md): does the closed-loop harness retrodict route r71b (V294 + r1)?

Mode B (recorded planner demand -> the fork port -> 0xE4 -> byte-exact lane -> plant) on every hands-off laterally-engaged
chunk of r71b, for every plant member and three disturbance models:
  c0    one constant torque per chunk (the plant study's per-window offset) -- the PLANT ALONE is tested
  lp    the drive's own equation residual low-passed at 0.1 Hz (road bank/crown + slow model error) -- the plant above 0.1 Hz
  full  the drive's residual at full bandwidth (DISTURBANCE REPLAY) -- a CONSISTENCY check of the loop assembly (fork,
        pipeline, lane, plant inversion); it is NOT independent evidence for the plant
The drive's own values come from the SAME metric code on the same frames.  Verdicts per the pre-registered tolerances.
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v295_harness as H  # noqa: E402

MEMBERS = ("nominal", "b_lo", "b_hi", "F_hi", "F_lo", "J_lo", "J_hi", "ms_free", "tau6", "light_b", "nominal_kappa")
DISTS = ("c0", "lp", "full")
METRICS = ("track_gain", "turn_hold", "i_share", "cmd_rms", "trim_ff", "r_lo", "r_mid", "r_hi", "hard16", "dwell_per_min")


def grade(k, meas, sim, dm_meas):
    """pre-registered tolerance of one metric -> 'FIT' / 'DIR' / 'NOT' / 'n/t' (not testable)."""
    if not (np.isfinite(meas) and np.isfinite(sim)):
        return "n/t"
    if k == "hard16" and dm_meas.get("hard_sec", 0) < 5:
        return "n/t"
    if k == "track_gain":
        d = abs(sim - meas)
        return "FIT" if d <= 0.05 else ("DIR" if (sim < 0.97 and d <= 0.12) else "NOT")
    if k == "turn_hold":
        d = abs(sim - meas)
        return "FIT" if d <= 0.06 else ("DIR" if d <= 0.15 else "NOT")
    if k == "i_share":
        d = abs(sim - meas)
        return "FIT" if d <= 0.08 else ("DIR" if d <= 0.15 else "NOT")
    tol = dict(cmd_rms=(1.15, 1.5), trim_ff=(1.25, 2.0), r_lo=(1.3, 2.0), r_mid=(1.3, 2.0), r_hi=(1.3, 2.0),
               hard16=(1.5, 2.5), dwell_per_min=(3.0, 10.0))[k]
    r = sim / meas if meas else np.inf
    if 1 / tol[0] <= r <= tol[0]:
        return "FIT"
    if 1 / tol[1] <= r <= tol[1]:
        return "DIR"
    return "NOT"


def band_verdict(g, sec):
    if sec < 30:
        return "NOT TESTABLE"
    if g["track_gain"] == "NOT" or g["turn_hold"] == "NOT" or sum(v == "NOT" for v in g.values()) >= 3:
        return "NOT FIT"
    core = [g[k] for k in ("track_gain", "turn_hold", "cmd_rms", "r_mid") if g[k] != "n/t"]
    if all(v == "FIT" for v in core) and not any(v == "NOT" for v in g.values()):
        return "FIT"
    return "DIRECTIONAL ONLY"


def main():
    t0 = time.time()
    fam = H.family()
    ch = H.route_chunks()
    d = H.route()
    tot = sum(b - a for a, b in ch) / 100.0
    print("H4 RETRODICTION  r71b, %d hands-off engaged chunks, %.0f s; V294 cells from the image; fork port (== real)" % (len(ch), tot))
    meas = H.drive_metrics(H.drive_series_measured(ch))
    # second method on the measured side: the bands report's own band edges (S2: 1-8 / 8-15 / 15-22 / >22)
    S2B = (("1-8", 1.0, 8.0), ("8-15", 8.0, 15.0), ("15-22", 15.0, 22.0), (">22", 22.0, 99.0))
    m2 = H.drive_metrics(H.drive_series_measured(ch), S2B)
    print("\n  MEASURED on the chunks, S2 band edges, S2's own form (all-frame slope) -- vs the bands report (S2 row):")
    quoted = {"1-8": 0.836, "8-15": 0.800, "15-22": 0.831, ">22": 0.934}
    quoted_hold = {"1-8": 0.81, "8-15": 0.69, "15-22": 0.67, ">22": 0.94}
    quoted_ish = {"1-8": 0.353, "8-15": 0.343, "15-22": 0.411, ">22": 0.251}
    for b, x in m2.items():
        print("     %-6s %4.0f s  track(all) %.3f [report %.3f]  track(|plan|>0.3) %.3f  hold %.3f [report %.2f]  i-share %.3f [report %.3f]"
              % (b, x["sec"], x["track_gain_all"], quoted[b], x["track_gain"], x["turn_hold"], quoted_hold[b], x["i_share"], quoted_ish[b]))
    out = dict(chunks=ch, measured=meas, measured_S2=m2, sims={})
    diverged = []
    for dist in DISTS:
        ts = time.time()
        R = H.simulate([H.Cells.v294()], [fam[m] for m in MEMBERS], ch, H.SimOpts(mode="B", dist=dist))
        nK = len(ch)
        print("\n  mode B dist=%s: %d lanes, %.1f s" % (dist, len(R["lens"]), time.time() - ts))
        for mi, nm in enumerate(MEMBERS):
            rows = list(range(mi * nK, (mi + 1) * nK))
            bad = [j for j in rows if not np.all(np.isfinite(R["ang"][j])) or np.max(np.abs(R["ang"][j])) > 1500]
            if bad:
                diverged.append((dist, nm, len(bad)))
            sm = H.drive_metrics(H.drive_series_sim(R, rows))
            # per-chunk angle/rate R2 against the drive
            ra, rr = [], []
            for jj, j in enumerate(rows):
                a, b = ch[jj]
                n = b - a
                y, yh = d["th"][a:b], R["ang"][j, :n]
                ra.append(1 - np.sum((y - yh) ** 2) / np.sum((y - y.mean()) ** 2))
                y, yh = d["x18_f"][a:b] / 8.0, R["rate18"][j, :n]
                rr.append(1 - np.sum((y - yh) ** 2) / np.sum((y - y.mean()) ** 2))
            ver = {}
            for b in meas:
                if b not in sm:
                    continue
                g = {k: grade(k, meas[b].get(k, np.nan), sm[b].get(k, np.nan), meas[b]) for k in METRICS}
                ver[b] = dict(grades=g, verdict=band_verdict(g, meas[b]["sec"]))
            out["sims"][(dist, nm)] = dict(metrics=sm, verdicts=ver, angle_R2_med=float(np.median(ra)),
                                          rate_R2_med=float(np.median(rr)), diverged=len(bad))
    # ---- print: the full table for the nominal member, then the verdict matrix
    for dist in DISTS:
        s = out["sims"][(dist, "nominal")]
        print("\n  ===== nominal, dist=%s   (per-chunk median angle R2 %.3f, rate R2 %.3f)" % (dist, s["angle_R2_med"], s["rate_R2_med"]))
        print("     %-6s %-22s " % ("band", "metric") + "  meas      sim     grade")
        for b in meas:
            if b not in s["verdicts"]:
                continue
            for k in METRICS:
                print("     %-6s %-22s %8.3f %8.3f   %s" % (b, k, meas[b].get(k, np.nan), s["metrics"][b].get(k, np.nan),
                                                          s["verdicts"][b]["grades"][k]))
            print("     %-6s VERDICT: %s" % (b, s["verdicts"][b]["verdict"]))
    print("\n  VERDICT MATRIX (band verdict per member x disturbance model):")
    print("     %-14s %-5s " % ("member", "dist") + "".join("%-18s" % b for b in meas) + " angleR2 rateR2")
    for dist in DISTS:
        for nm in MEMBERS:
            s = out["sims"][(dist, nm)]
            print("     %-14s %-5s " % (nm, dist) + "".join("%-18s" % s["verdicts"].get(b, {}).get("verdict", "-") for b in meas)
                  + " %6.3f %6.3f" % (s["angle_R2_med"], s["rate_R2_med"]))
    print("\n  TRACKING GAIN (|plan| > 0.3) by member, dist=c0 / lp:   measured %s"
          % " ".join("%.3f" % meas[b]["track_gain"] for b in meas))
    for nm in MEMBERS:
        print("     %-14s c0 %s   lp %s" % (nm, " ".join("%.3f" % out["sims"][("c0", nm)]["metrics"][b]["track_gain"] for b in meas),
                                           " ".join("%.3f" % out["sims"][("lp", nm)]["metrics"][b]["track_gain"] for b in meas)))
    # ---- the pre-registered FAIL sentence
    fail_bits = []
    for dist in ("c0", "lp"):
        s = out["sims"][(dist, "nominal")]["metrics"]
        hi = [b for b in ("10-15", "15-22") if b in s and s[b]["track_gain"] >= 0.95]
        if hi:
            fail_bits.append("%s: sim tracking gain >= 0.95 at %s" % (dist, hi))
        cm = [b for b in meas if b in s and not (1 / 1.5 <= s[b]["cmd_rms"] / meas[b]["cmd_rms"] <= 1.5)]
        if len(cm) >= 2:
            fail_bits.append("%s: command rms off by > x1.5 in %s" % (dist, cm))
    if diverged:
        fail_bits.append("diverged: %s" % diverged)
    print("\n  PRE-REGISTERED HARNESS-FAIL SENTENCE fires: %s" % ("; ".join(fail_bits) if fail_bits else "NO"))
    # mode A literal metric vs the metric agent
    RA = H.simulate([H.Cells.v294()], [fam["nominal"]], ch, H.SimOpts(mode="A", dist="full"))
    mt, _ = H.m_track_from_sim(RA)
    lit_meas = {}
    for (bn, lo, hi) in (("0.3-1", 0.3, 1.0), ("1-3", 1.0, 3.0), ("3-8", 3.0, 8.0)):
        fits = []
        for a, b in ch:
            if b - a < 1000:
                continue
            fits.append(H.gain_phase_fit(d["e4_f"][a:b], -np.gradient(d["x18_f"][a:b] / 8.0) * 100.0, lo, hi))
        lit_meas[bn] = dict(R2=float(np.median([f["R2"] for f in fits])), G=float(np.median([f["G"] for f in fits])),
                            ph=float(np.median([f["ph"] for f in fits])))
    print("\n  MODE A (recorded command, dist=full) literal cmd->alpha gain-phase fit, per-chunk medians (+ right frame):")
    for bn in lit_meas:
        print("     %-6s drive R2 %.2f |G| %.2f ph %+.0f   |  sim R2 %.2f |G| %.2f ph %+.0f   (metric agent, all speeds, pooled: "
              "0.3-1 0.37/0.44/+51, 1-3 0.55/1.88/+25, 3-8 0.16/2.48/+18)"
              % (bn, lit_meas[bn]["R2"], lit_meas[bn]["G"], lit_meas[bn]["ph"], mt["lit_" + bn]["R2"], mt["lit_" + bn]["G"],
                 mt["lit_" + bn]["ph"]))
    out["modeA_literal"] = dict(drive=lit_meas, sim=mt)
    out["runtime_s"] = time.time() - t0
    print("\n  runtime %.0f s" % out["runtime_s"])
    json.dump({str(k): v for k, v in out.items() if k != "sims"} | {"sims": {str(k): v for k, v in out["sims"].items()}},
              open(os.path.join(HERE, "_scratch", "h4_retrodict.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
