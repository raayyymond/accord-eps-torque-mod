# -*- coding: utf-8 -*-
"""report_ad_b4.py -- pools out/read_ad_b4.json by firmware (V300 = ad..b4, V299 = 9c+9d, V298 = 79) and prints the
tables the drive-read report quotes.  < 1 s.  python rlog-tools/studies/angle_loop/release_ad_b4/report_ad_b4.py"""
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import read_ad_b4 as R  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
J = json.loads((HERE / "out" / "read_ad_b4.json").read_text())
GROUPS = {"V300": [k for k in J if J[k]["attrib"]["fw"].endswith("A16C")],
          "V299": [k for k in J if J[k]["attrib"]["fw"].endswith("A16B")],
          "V298": [k for k in J if J[k]["attrib"]["fw"].endswith("A16A")]}
nz = lambda x: float("nan") if x is None else x  # noqa: E731
f1 = lambda x: "-" if x is None or (isinstance(x, float) and not math.isfinite(x)) else "%.1f" % x  # noqa: E731
f2 = lambda x: "-" if x is None or (isinstance(x, float) and not math.isfinite(x)) else "%.2f" % x  # noqa: E731
pc = lambda x: "-" if x is None or (isinstance(x, float) and not math.isfinite(x)) else "%.1f %%" % (100 * x)  # noqa


def short(tag):
    return tag.split("_")[0][1:]


print("== 1. ATTRIBUTION")
print("route | EPS fw | fork commit | branch | steerControlType | CP.steerRatio | CP.maxLatAccel | route min | engaged min |"
      " engaged min by band 0-3/3-6/6-10/10-15/15-22/>22 | hands-on (>600) engaged min <6 / <10 | alerts")
for k, A in J.items():
    a = A["attrib"]
    e = a["exp_min"]
    print("%s | %s | %s | %s | %s | %.2f | %.3f | %.1f | %.1f | %s | %.2f / %.2f | %s" % (
        short(k), a["fw"], (a["commit"] or "?")[:10], a["branch"], a["steerControlType"], a["steerRatio"],
        a["maxLateralAccel"], a["route_min"], a["eng_min"], " / ".join("%.1f" % e[b] for b in e),
        a["handson_eng_min_lt6"], a["handson_eng_min_lt10"], "; ".join(x for x in a["alerts"] if "exceed" in x.lower())))

print("\n== bar sign (disengaged, |bar| > 600, |w| > 30: fraction with bar*w > 0)")
for k, A in J.items():
    print("  %s k %+d agree %.2f n %d" % (short(k), A["bar_sign"]["k"], A["bar_sign"]["agree"], A["bar_sign"]["n"]))

print("\n== 2a. GRIND BANDS, pooled by firmware: engaged/disengaged hands-on (|bar| > 600, |w| > 30), 1-s windows,"
      " ratio of medians per (speed 0-3/3-6/6-10, rate 30-60/60-120/>120) bin, engaged-weighted geometric mean")
KEYS = [("bar_V2", "bar 5-9 (V2)"), ("bar_C3", "bar 15-25 (C3)"), ("bar_V1", "bar 35-50 (V1)"),
        ("w_V2", "rate 5-9 (V2)"), ("w_C3", "rate 15-25 (C3)"), ("w_V1", "rate 35-50 (V1)"), ("w_C2", "rate 8-25 (C2)")]
POOL = {}
for g, tags in GROUPS.items():
    rows = [dict(r, route=short(t)) for t in tags for r in J[t]["rows"]]
    POOL[g] = rows
    for vmax in (6.0, 10.0):
        E, D = R.handson_sets(rows, vmax)
        line = []
        for key, nm in KEYS:
            rt, ne, nd, pb = R.compare(E, D, key, vmax)
            me = np.median([r[key] for r in E]) if E else float("nan")
            md = np.median([r[key] for r in D]) if D else float("nan")
            line.append("%s %s (eng p50 %s / dis p50 %s)" % (nm, f2(rt), f1(me), f1(md)))
        print("  %s v<%d  n eng %d dis %d (matched %d/%d):\n     %s" % (
            g, vmax, len(E), len(D), R.compare(E, D, "bar_V1", vmax)[1], R.compare(E, D, "bar_V1", vmax)[2],
            "\n     ".join(line)))

print("\n== 2a'. per route, v<10: n eng/dis hands-on windows; unmatched eng/dis median ratio bar 35-50 / bar 15-25 / rate 5-9")
for k, A in J.items():
    g = A["grind_v10"]
    me, md = g["med_eng"], g["med_dis"]
    rr = lambda q: (nz(me[q]) / nz(md[q])) if md[q] else float("nan")  # noqa: E731
    print("  %s n %d/%d  %s / %s / %s" % (short(k), g["n_eng"], g["n_dis"], f2(rr("bar_V1")), f2(rr("bar_C3")),
                                           f2(rr("w_V2"))))

print("\n== 2b. dwells/min (symptom instrument, engaged, @0.25 and @0.50 deg/s) 0-5 | 5-10 m/s")
for k, A in J.items():
    d = A["dwells"]
    print("  %s 0-5: %s / %s (%s s)   5-10: %s / %s (%s s)" % (
        short(k), f1(d["0-5"]["per_min_025"]), f1(d["0-5"]["per_min_050"]), f1(d["0-5"]["sec"]),
        f1(d["5-10"]["per_min_025"]), f1(d["5-10"]["per_min_050"]), f1(d["5-10"]["sec"])))
for g, tags in GROUPS.items():
    s = sum(J[t]["dwells"]["0-5"]["sec"] or 0 for t in tags)
    n25 = sum((J[t]["dwells"]["0-5"]["per_min_025"] or 0) * (J[t]["dwells"]["0-5"]["sec"] or 0) / 60 for t in tags)
    n50 = sum((J[t]["dwells"]["0-5"]["per_min_050"] or 0) * (J[t]["dwells"]["0-5"]["sec"] or 0) / 60 for t in tags)
    print("  POOLED %s 0-5 m/s: %.1f /min @0.25, %.1f /min @0.50 over %.0f s" % (g, 60 * n25 / max(s, 1), 60 * n50 / max(s, 1), s))

print("\n== 2c. C1 hand fight (frames: engaged, |bar| > 600)")
for vmax in (6, 10):
    print("  v<%d: route | hands-on s | opposing | aiding | opposing AND at the clip | at clip | |err| p50 | opposing |err| p50"
          " | P-only lane torque when opposing p50/p90 T (rail %%) | opposing with |bar| > 1200" % vmax)
    for k, A in J.items():
        c = A["c1_v%d" % vmax]
        if not c.get("n"):
            continue
        print("   %s | %.1f | %s | %s | %s | %s | %s | %s | %s/%s (%s) | %s" % (
            short(k), c["secs"], pc(c["opp"]), pc(c["aid"]), pc(c["opp_clip"]), pc(c["clip"]), f1(c["err_p50"]),
            f1(c["err_opp_p50"]), f1(c["TP_opp_p50"]), f1(c["TP_opp_p90"]), pc(c["TP_opp_rail_p50"]),
            pc(c["opp_pressed"])))
    for g, tags in GROUPS.items():
        w = [J[t]["c1_v%d" % vmax] for t in tags if J[t]["c1_v%d" % vmax].get("n")]
        n = sum(c["n"] for c in w)
        if n:
            print("   POOLED %s: %.0f s, opposing %s, opposing at clip %s" % (
                g, n / 100, pc(sum(c["opp"] * c["n"] for c in w) / n), pc(sum(c["opp_clip"] * c["n"] for c in w) / n)))
    print("  C1 vs band energy (hands-on engaged windows with > 50 %% opposing-at-clip vs < 10 %%), v<%d, pooled V300:" % vmax)
    E, _ = R.handson_sets(POOL["V300"], vmax)
    oc = [r for r in E if r.get("opp_clip", 0) > 0.5]
    no = [r for r in E if r.get("opp_clip", 0) < 0.1]
    for key, nm in KEYS:
        if oc and no:
            print("     %s: at-clip p50 %s (n %d) vs not p50 %s (n %d)" % (
                nm, f1(np.median([r[key] for r in oc])), len(oc), f1(np.median([r[key] for r in no])), len(no)))

print("\n== 2c'. C1 vs band energy CONTROLLED FOR HAND TORQUE: pooled V300 hands-on engaged windows v<10, binned by |bar|"
      " p50: band p50 at-clip (>50 %% opposing-at-clip) vs not (<10 %%)")
E, _ = R.handson_sets(POOL["V300"], 10.0)
for lo, hi in ((600, 1200), (1200, 2000), (2000, 1e9)):
    oc = [r for r in E if lo <= r["bar"] < hi and r.get("opp_clip", 0) > 0.5]
    no = [r for r in E if lo <= r["bar"] < hi and r.get("opp_clip", 0) < 0.1]
    print("  |bar| %d-%s: n %d / %d | " % (lo, "inf" if hi > 1e8 else "%d" % hi, len(oc), len(no)) + " | ".join(
        "%s %s vs %s" % (nm, f1(np.median([r[k] for r in oc]) if oc else float("nan")),
                         f1(np.median([r[k] for r in no]) if no else float("nan"))) for k, nm in KEYS[:3] + KEYS[6:]))

print("\n== 2a''. V1 at HIGH ANGLE (the record's grind #2 condition): hands-on windows v<10 with |angle| max > 150,"
      " engaged vs disengaged, by firmware")
for g in GROUPS:
    E, D = R.handson_sets(POOL[g], 10.0)
    E = [r for r in E if r["angmax"] > 150]
    D = [r for r in D if r["angmax"] > 150]
    md = lambda xs, k: f1(np.median([r[k] for r in xs])) if xs else "-"  # noqa: E731
    print("  %s n eng %d dis %d | bar 35-50 eng %s dis %s | bar 15-25 eng %s dis %s | bar 5-9 eng %s dis %s | |bar| p50 eng %s"
          " dis %s" % (g, len(E), len(D), md(E, "bar_V1"), md(D, "bar_V1"), md(E, "bar_C3"), md(D, "bar_C3"),
                       md(E, "bar_V2"), md(D, "bar_V2"), md(E, "bar"), md(D, "bar")))

print("\n== 2d. C2: setpoint vs measured wheel under a hand (xcorr of first differences; cross-spectrum 0.5-5 Hz)")
for k, A in J.items():
    for vmax in (10,):
        x = A["c2_v%d" % vmax]
        p = A["c2ph_v%d" % vmax]
        ho = A["c2ph_ho_v%d" % vmax]
        fk = A["c2fork_v%d" % vmax]
        if not x.get("n_runs"):
            continue
        print("  %s v<%d hands-on: xcorr lag %+d fr r %.2f gain %.2f | spectral tau %s ms gain %s coh %s | HANDS-OFF tau %s"
              " ms gain %s | FORK desired-vs-wheel tau %s ms gain %s coh %s ; sent-vs-wheel tau %s ms gain %s" % (
                  short(k), vmax, x["lag_frames"], x["r_peak"], x["gain"], f1(1e3 * p.get("tau_s", float("nan"))),
                  f2(p.get("gain")), f2(p.get("coh")), f1(1e3 * ho.get("tau_s", float("nan"))), f2(ho.get("gain")),
                  f1(1e3 * fk["des"].get("tau_s", float("nan"))), f2(fk["des"].get("gain")), f2(fk["des"].get("coh")),
                  f1(1e3 * fk["sent"].get("tau_s", float("nan"))), f2(fk["sent"].get("gain"))))

print("\n== 2e. TOP-10 candidate grind episodes (V300, engaged, |bar| > 600, |w| > 30, v < 10; score = max over bands of"
      " the window / the pooled V300 disengaged hands-on median in its speed x rate bin)")
E, D = R.handson_sets(POOL["V300"], 10.0)
base = {}
for key, _ in KEYS:
    for vb in range(3):
        for rb in range(3):
            xs = [r[key] for r in D if R.vbin(r["v"]) == vb and R.rbin(r["rate"]) == rb]
            base[(key, vb, rb)] = np.median(xs) if len(xs) >= 3 else np.median([r[key] for r in D])
SC = []
for r in E:
    sc = {key: r[key] / base[(key, R.vbin(r["v"]), R.rbin(r["rate"]))] for key, _ in KEYS}
    top = max(sc, key=sc.get)
    SC.append((sc[top], top, r, sc))
SC.sort(key=lambda z: -z[0])
print("route | t s (segment) | v m/s | angle deg | |bar| p50 | |rate| p50 deg/s | top band (x control) | bar 5-9/15-25/35-50"
      " | rate 5-9/15-25/35-50 | opposing-at-clip")
from scipy import signal as _sg
_DC = {}
for s, top, r, sc in SC[:10]:
    tg = [t for t in GROUPS["V300"] if short(t) == r["route"]][0]
    if tg not in _DC:
        _DC[tg] = R.load(tg)
    Dd = _DC[tg]
    a = r["i"] * 100
    pk = []
    for x in (Dd["bar"], Dd["w18"]):
        seg = _sg.sosfiltfilt(R._SOS_HP, np.nan_to_num(x[a - 200:a + 300]))[200:300]
        f, P = _sg.periodogram(seg, fs=100, window="hann")
        sel = f >= 5
        pk.append(f[sel][np.argmax(P[sel])])
    print("%s | %.0f (seg %d, +%.0f s) | %.1f | %+.0f | %.0f | %.0f | %s x%.1f | %.0f/%.0f/%.0f | %.2f/%.2f/%.2f | %s | peak bar %.0f Hz, rate %.0f Hz" % (
        r["route"], r["t"], int(r["t"] // 60), r["t"] % 60, r["v"], r["ang"], r["bar"], r["rate"], dict(KEYS)[top], s,
        r["bar_V2"], r["bar_C3"], r["bar_V1"], r["w_V2"], r["w_C3"], r["w_V1"], pc(r.get("opp_clip")), pk[0], pk[1]))
print("  scores of all %d V300 engaged hands-on windows: p50 %.2f p90 %.2f max %.2f ; same score on the disengaged"
      " control windows: p50 %.2f p90 %.2f max %.2f (n %d)" % (
          len(SC), np.median([z[0] for z in SC]), np.percentile([z[0] for z in SC], 90), SC[0][0],
          np.median([max(r[k] / base[(k, R.vbin(r["v"]), R.rbin(r["rate"]))] for k, _ in KEYS) for r in D]),
          np.percentile([max(r[k] / base[(k, R.vbin(r["v"]), R.rbin(r["rate"]))] for k, _ in KEYS) for r in D], 90),
          max(max(r[k] / base[(k, R.vbin(r["v"]), R.rbin(r["rate"]))] for k, _ in KEYS) for r in D), len(D)))

print("\n== 3. MAX ANGLE")
print("route | engaged setpoint peak (wire) | engaged wheel peak | wheel peak any | planner desired peak | sent peak |"
      " limiter replay agreement | frames |theta|>150 engaged: n, clip-bound, VM-bound, rate-bound")
for k, A in J.items():
    m = A["maxang"]
    print("%s | %.0f | %.0f | %.0f | %.0f | %.0f | %s | %d, %s, %s, %s" % (
        short(k), m["sp_peak"], m["th_peak_eng"], m["th_peak_all"], m["des_peak"], m["co_peak"], pc(m["agree"]),
        m["hi150_n"], pc(m["hi150_clip"]), pc(m["hi150_vm"]), pc(m["hi150_rate"])))
print("\n  WHEEL SHORT OF THE PLANNER (|desired| > 30, desired - wheel > 2 deg outward): which bound, by speed band, pooled V300")
for g, tags in GROUPS.items():
    print("  %s" % g)
    for nm, lo, hi in R.VBANDS:
        cells = [J[t]["maxang"]["short_by_band"][nm] for t in tags]
        n = sum(c.get("n", 0) for c in cells)
        if not n:
            continue
        w = lambda q: sum((c.get(q) or 0) * c.get("n", 0) for c in cells if c.get("n")) / n  # noqa: E731
        sp = [c["short_p50"] for c in cells if c.get("n")]
        th = [c["th_p50"] for c in cells if c.get("n")]
        print("    %-6s %6.1f s short | VM %s  clip %s  rate %s  none-of-the-fork-bounds %s | shortfall p50 (route"
              " medians) %s deg | |wheel| p50 %s" % (
                  nm, n / 100, pc(w("vm")), pc(w("clip")), pc(w("rate")), pc(w("none")),
                  "/".join("%.0f" % x for x in sp), "/".join("%.0f" % x for x in th)))
print("\n  HANDS-OFF (|bar| < 300 for 0.5 s) + QUASI-STATIC (|d desired/dt| < 10 deg/s for 0.5 s) short-of-planner, by firmware")
for g, tags in GROUPS.items():
    print("  %s  hands-off engaged peak |wheel| per route: %s ; hands-off s at |theta|>150: %s (clip duty %s)" % (
        g, "/".join(f1(J[t]["maxang"]["ho_peak_th"]) for t in tags),
        "/".join(f1(J[t]["maxang"]["ho_hi150_s"]) for t in tags),
        "/".join(pc(J[t]["maxang"]["ho_hi150_clip"]) for t in tags)))
    for nm, lo, hi in R.VBANDS:
        cells = [J[t]["maxang"]["short_ho_qs_by_band"][nm] for t in tags]
        n = sum(c.get("n", 0) for c in cells)
        if not n:
            continue
        w = lambda q: sum((c.get(q) or 0) * c.get("n", 0) for c in cells if c.get("n")) / n  # noqa: E731
        print("    %-6s %6.1f s | VM %s clip %s rate %s none %s | shortfall p50 %s | |wheel| p50 %s max %s | desired max %s"
              % (nm, n / 100, pc(w("vm")), pc(w("clip")), pc(w("rate")), pc(w("none")),
                 "/".join("%.0f" % c["short_p50"] for c in cells if c.get("n")),
                 "/".join("%.0f" % c["th_p50"] for c in cells if c.get("n")),
                 "/".join("%.0f" % c["th_max"] for c in cells if c.get("n")),
                 "/".join("%.0f" % c["des_max"] for c in cells if c.get("n"))))

print("\n  CLIP / VM duty on all latActive frames, pooled V300, by band (all angles | |theta| > 150)")
for nm, lo, hi in R.VBANDS:
    cells = [J[t]["maxang"]["duty_by_band"][nm] for t in GROUPS["V300"]]
    n = sum(c["n"] for c in cells)
    nh = sum(c["n_hi150"] for c in cells)
    if not n:
        continue
    cl = sum((c["clip"] or 0) * c["n"] for c in cells) / n
    vm = sum((c["vm"] or 0) * c["n"] for c in cells) / n
    ch = sum((c["clip_hi150"] or 0) * c["n_hi150"] for c in cells) / nh if nh else float("nan")
    print("    %-6s %7.0f s : clip %s  VM %s | |theta|>150: %5.1f s clip %s" % (nm, n / 100, pc(cl), pc(vm), nh / 100, pc(ch)))

print("\n== 3b. SATURATION ALERT duty (controlsState active rows; the timer rule of LatControl._check_saturation)")
for k, A in J.items():
    s = A["sat"]
    print("  %s logged %s (%d eps) | OLD rule replay %s (%d eps, agrees with logged %s) | NEW rule 9b7ef55826 replay %s"
          " (%d eps, agrees %s)" % (short(k), pc(s["logged"]), s["logged_eps"], pc(s["old"]), s["old_eps"],
                                    pc(s["agree_old"]), pc(s["new"]), s["new_eps"], pc(s["agree_new"])))
