# -*- coding: utf-8 -*-
"""studies/osc-highangle/grind_r34_operator.py -- the operator's two r34 timestamps for "very very attenuated grind #1 still present
at 3-6 mph" (his words; "grind #1" is the kit's 18-22 Hz torsion-bar band, `_grind2_lib.BANDS["18-22"]`, strict presence band 18-26).

Anchor: unix = logMonoTime + off_gps, off_gps = median(gpsLocationExternal.unixTimestampMillis/1e3 - logMonoTime) over fix-valid
samples (`_scratch/_lc_r34.npz`, built by the lanechange study), exactly as lanechange_windows.anchor(). Local = PDT (UTC-7).

Per window (+-15 s, frames at 1.3-2.7 m/s = 3-6 mph): engaged/manual state, angle, cmd/idx, driver torque; band amplitudes of the 0x18F
rate, the torsion bar (0x18F signed driver torque, raw), the tap T, and the IMU vertical/lateral accel (house cache imu_vert/imu_lat) in
18-22 / 18-26 / 24-28 (negative control) / 30-49 (grind #2) / 6-9 (ratchet) Hz; the most prominent line 12-30 Hz (prominence = P over its
local median floor, _grind2_lib.locate); chain rails (V280 rev 2 line, open loop). Baselines: the same speed band engaged and manual on
r32, r33 and the rest of r34.  Run: python grind_r34_operator.py
"""
import datetime
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import strongturn_r34 as T  # noqa: E402
V, ST = T.V, T.ST
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
import _grind2_lib as G2  # noqa: E402

FS = 100.0
TZ_H = -7
DATE = "2026-09-02"
OPERATOR = [("20:48:55", "operator wrote 20:48:55"), ("20:50:28", "operator wrote 2:50:28; read as 20:50:28")]
HALF = 15.0
VLO, VHI = 1.3, 2.7          # 3-6 mph
BANDS = [("6-9", 6, 9), ("18-22", 18, 22), ("18-26", 18, 26), ("24-28", 24, 28), ("30-49", 30, 49)]


def bamp(x, lo, hi):
    if len(x) < 64:
        return np.nan
    hi = min(hi, 49.0)
    sos = signal.butter(4, (lo, hi), btype="bandpass", fs=FS, output="sos")
    y = signal.sosfiltfilt(sos, x - np.mean(x))
    return float(np.sqrt(2) * y.std())


def welch_runs(x, m, nps=256):
    d = np.diff(np.r_[0, m.astype(int), 0]); acc = None; tot = 0
    for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
        if b - a < nps:
            continue
        f, P = signal.welch(x[a:b] - x[a:b].mean(), fs=FS, nperseg=nps)
        acc = P * (b - a) if acc is None else acc + P * (b - a); tot += b - a
    return (f, acc / tot) if tot else (None, None)


def stats(r, H, m, R):
    """m = 100 Hz mask on the route grid."""
    o = dict(n=int(m.sum()), secs=m.sum() / FS)
    if o["n"] < 100:
        return o
    o["eng"] = float(r.eng[m].mean()); o["v"] = float(np.median(r.vego[m])); o["ang"] = float(np.median(np.abs(r.ang[m])))
    o["cmd"] = float(np.median(np.abs(r.cmd[m]))); o["idx"] = float(np.median(r.idx[m])); o["idx90"] = float(np.percentile(r.idx[m], 90))
    o["tq"] = float(np.median(np.abs(r.tq_raw[m]))); o["tq90"] = float(np.percentile(np.abs(r.tq_raw[m]), 90))
    o["cliff"] = float(np.mean(np.abs(r.tq_raw[m]) >= 2240))
    o["T"] = float(np.median(np.abs(r.T_meas[m]))); o["Tsat"] = float(np.mean(np.abs(r.T_meas[m]) >= V.SAT_THR))
    i = r.i100[m]
    o["Prail"] = float(np.mean(np.abs(R["P_raw"][i]) >= V.P_CLAMP)); o["Drail"] = float(np.mean(np.abs(R["D_raw"][i]) > V.D_CLAMP))
    o["fbclp"] = float(np.mean(np.abs(r.fb_un[i]) >= T.V280R2[1])); o["ocap"] = float(np.mean(np.abs(R["T"][i]) >= ST.CAP))
    # band amps over contiguous runs >= 1 s (concatenating runs would create edges)
    runs = V.runs(m, 100)
    for nm, lo, hi in BANDS:
        o["rate_" + nm] = bamp(r.wire[runs], lo, hi) / V.CPD if runs.sum() > 100 else np.nan
        o["bar_" + nm] = bamp(r.tq_raw[runs], lo, hi) if runs.sum() > 100 else np.nan
        o["T_" + nm] = bamp(r.T_meas[runs], lo, hi) if runs.sum() > 100 else np.nan
        o["ivert_" + nm] = bamp(H["imu_vert"][runs], lo, hi) if runs.sum() > 100 else np.nan
        o["ilat_" + nm] = bamp(H["imu_lat"][runs], lo, hi) if runs.sum() > 100 else np.nan
    for ch, x in (("bar", r.tq_raw), ("rate", r.wire), ("T", r.T_meas), ("ilat", H["imu_lat"])):
        f, P = welch_runs(x, m)
        if f is None:
            o[ch + "_f0"] = o[ch + "_prom"] = np.nan; continue
        f0, pr_ = G2.locate(f, P, 12, 30)
        o[ch + "_f0"], o[ch + "_prom"] = f0, pr_
    # bar-to-rate coherence at the bar's line
    if o["n"] >= 512:
        d = np.diff(np.r_[0, m.astype(int), 0]); a = np.flatnonzero(d == 1); b = np.flatnonzero(d == -1)
        k = int(np.argmax(b - a)); s = slice(a[k], b[k])
        if b[k] - a[k] >= 512:
            fc, C = signal.coherence(r.tq_raw[s], r.wire[s], fs=FS, nperseg=256)
            j = int(np.argmin(np.abs(fc - (o["bar_f0"] if np.isfinite(o["bar_f0"]) else 20)))); o["coh_bar_rate"] = float(C[j])
            fc, C = signal.coherence(r.tq_raw[s], r.T_meas[s], fs=FS, nperseg=256)
            o["coh_bar_T"] = float(C[j])
    return o


def fmt(nm, o):
    if o.get("n", 0) < 100:
        return "  %-34s n=%d (<1 s)" % (nm, o.get("n", 0))
    return ("  %-34s %5.1f s eng %.2f v %.1f |ang| %4.0f |cmd| %4.0f idx %3.0f/%3.0f |tq| %4.0f/%4.0f cliff %.2f |T| %4.0f sat %.3f | rails P %.2f D %.2f fb %.2f cap %.2f\n"
            "      bar 6-9 %4.0f 18-22 %4.0f 18-26 %4.0f 24-28 %4.0f 30-49 %4.0f raw | rate 6-9 %4.2f 18-22 %4.2f 18-26 %4.2f 24-28 %4.2f 30-49 %4.2f deg/s | T 18-22 %3.0f 24-28 %3.0f 30-49 %3.0f\n"
            "      IMU vert 18-22 %.4f 24-28 %.4f 30-49 %.4f ; lat 18-22 %.4f 24-28 %.4f 30-49 %.4f m/s2 | lines 12-30 Hz: bar %.1f Hz x%.1f  rate %.1f x%.1f  T %.1f x%.1f  ilat %.1f x%.1f | coh bar-rate %.2f bar-T %.2f"
            % (nm, o["secs"], o["eng"], o["v"], o["ang"], o["cmd"], o["idx"], o["idx90"], o["tq"], o["tq90"], o["cliff"], o["T"], o["Tsat"], o["Prail"], o["Drail"], o["fbclp"], o["ocap"],
               o["bar_6-9"], o["bar_18-22"], o["bar_18-26"], o["bar_24-28"], o["bar_30-49"], o["rate_6-9"], o["rate_18-22"], o["rate_18-26"], o["rate_24-28"], o["rate_30-49"],
               o["T_18-22"], o["T_24-28"], o["T_30-49"], o["ivert_18-22"], o["ivert_24-28"], o["ivert_30-49"], o["ilat_18-22"], o["ilat_24-28"], o["ilat_30-49"],
               o["bar_f0"], o["bar_prom"], o["rate_f0"], o["rate_prom"], o["T_f0"], o["T_prom"], o["ilat_f0"], o["ilat_prom"], o.get("coh_bar_rate", np.nan), o.get("coh_bar_T", np.nan)))


def main():
    L = []
    pr = lambda s="": (print(s), L.append(s))  # noqa: E731
    routes, house, chains = {}, {}, {}
    for tag in ("r32", "r33", "r34"):
        routes[tag] = V.Route(tag)
        z = np.load(os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", tag, tag + ".npz"), allow_pickle=True)
        th = np.asarray(z["t"], float) + float(z["t0_mono"][0]) - float(np.load(os.path.join(V.CACHE, tag + ".npz"))["t18"][0])
        house[tag] = {k: np.interp(routes[tag].tg, th, np.nan_to_num(np.asarray(z[k], float))) for k in ("imu_vert", "imu_lat")}
        chains[tag] = T.sim(routes[tag], *T.V280R2)
    r, H, R = routes["r34"], house["r34"], chains["r34"]
    lc = dict(np.load(os.path.join(HERE, "_scratch", "_lc_r34.npz")))
    ok = lc["unixms"] > 1.6e12
    off = float(np.median(lc["unixms"][ok] * 1e-3 - lc["tgps"][ok]))
    wall = lc["wall"] * 1e-9 - lc["tclk"]; off_clk = wall[wall > 1.6e9].max() if (wall > 1.6e9).any() else np.nan
    t0 = float(np.load(os.path.join(V.CACHE, "r34.npz"))["t18"][0])
    start = datetime.datetime.fromtimestamp(t0 + off, datetime.timezone.utc)
    pr("ANCHOR r34: unix = logMonoTime + %.3f s (GPS fix-valid n=%d; post-sync clocks offset %.3f, diff %.3f s)" % (off, ok.sum(), off_clk, off_clk - off))
    pr("  route t=0 (first 0x18F) = %s UTC = %s PDT ; route ends t=%.1f s = %s PDT" % (
        start.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], (start + datetime.timedelta(hours=TZ_H)).strftime("%H:%M:%S"), r.tg[-1],
        (start + datetime.timedelta(hours=TZ_H, seconds=float(r.tg[-1]))).strftime("%H:%M:%S")))
    wins = []
    for hhmmss, note in OPERATOR:
        local = datetime.datetime.strptime(DATE + " " + hhmmss, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone(datetime.timedelta(hours=TZ_H)))
        tr = local.timestamp() - off - t0
        pr("  OPERATOR %s PDT (%s) -> route t = %.1f s (segment %d)" % (hhmmss, note, tr, int(tr // 60)))
        wins.append((hhmmss, tr))

    speed = (r.vego >= VLO) & (r.vego < VHI)
    pr("\n" + "=" * 150)
    pr("THE TWO WINDOWS, +-%.0f s, restricted to 3-6 mph (%.1f-%.1f m/s) -- and the same window unrestricted" % (HALF, VLO, VHI))
    pr("=" * 150)
    inwin = np.zeros_like(r.eng)
    for hhmmss, tr in wins:
        w = (r.tg >= tr - HALF) & (r.tg <= tr + HALF)
        inwin |= w
        pr("\n-- %s (t %.1f s): speed profile in the window: v p10/p50/p90 %.1f/%.1f/%.1f m/s ; engaged %.2f ; 3-6 mph frames %.1f s (engaged %.1f s, manual %.1f s)" % (
            hhmmss, tr, *np.percentile(r.vego[w], (10, 50, 90)), r.eng[w].mean(), (w & speed).sum() / FS, (w & speed & r.eng).sum() / FS, (w & speed & ~r.eng).sum() / FS))
        pr(fmt("window all speeds, engaged", stats(r, H, w & r.eng, R)))
        pr(fmt("window 3-6 mph, engaged", stats(r, H, w & speed & r.eng, R)))
        pr(fmt("window 3-6 mph, manual", stats(r, H, w & speed & ~r.eng, R)))
        # 1 s trace
        pr("   1 s trace: t | v | eng | ang | cmd | idx | |tq| | T | bar18-22 | rate18-22 | bar 12-30 line | rails P/fb/cliff")
        for s in np.arange(tr - HALF, tr + HALF, 1.0):
            m = (r.tg >= s) & (r.tg < s + 1.0)
            if m.sum() < 90:
                continue
            i = r.i100[m]
            f, P = signal.welch(r.tq_raw[m] - r.tq_raw[m].mean(), fs=FS, nperseg=100); f0, pm = G2.locate(f, P, 12, 30, halfwin=8, exclude=2)
            pr("   %6.1f | %4.1f | %.1f | %+5.0f | %+5.0f | %3.0f | %4.0f | %+5.0f | %4.0f | %4.1f | %4.1f x%4.1f | %.2f/%.2f/%.2f%s" % (
                s, r.vego[m].mean(), r.eng[m].mean(), np.median(r.ang[m]), np.median(r.cmd[m]), np.median(r.idx[m]), np.median(np.abs(r.tq_raw[m])), np.median(r.T_meas[m]),
                bamp(r.tq_raw[m], 18, 22), bamp(r.wire[m], 18, 22) / V.CPD, f0, pm, np.mean(np.abs(R["P_raw"][i]) >= V.P_CLAMP), np.mean(np.abs(r.fb_un[i]) >= T.V280R2[1]),
                np.mean(np.abs(r.tq_raw[m]) >= 2240), "  <-- 3-6 mph" if VLO <= r.vego[m].mean() < VHI else ""))

    pr("\n" + "=" * 150)
    pr("BASELINES at 3-6 mph: r34 outside the windows, r32, r33 -- engaged and manual; and the whole-route 3-6 mph engaged set with the windows")
    pr("=" * 150)
    for tag in ("r34", "r32", "r33"):
        rr, HH, RR = routes[tag], house[tag], chains[tag]
        sp = (rr.vego >= VLO) & (rr.vego < VHI)
        excl = ~inwin if tag == "r34" else np.ones_like(rr.eng)
        pr(fmt("%s 3-6 mph engaged%s" % (tag, " (outside windows)" if tag == "r34" else ""), stats(rr, HH, sp & rr.eng & excl, RR)))
        pr(fmt("%s 3-6 mph manual" % tag, stats(rr, HH, sp & ~rr.eng, RR)))
        pr(fmt("%s 3-6 mph engaged, |ang| < 30" % tag, stats(rr, HH, sp & rr.eng & excl & (np.abs(rr.ang) < 30), RR)))
        pr(fmt("%s 3-6 mph engaged, |ang| >= 30" % tag, stats(rr, HH, sp & rr.eng & excl & (np.abs(rr.ang) >= 30), RR)))
    # distribution of 1 s bar 18-22 amps at 3-6 mph engaged: where do the windows sit?
    pr("\nPER-SECOND bar 18-22 Hz amplitude at 3-6 mph engaged -- percentile of each window's seconds inside the route's own distribution")
    for tag in ("r34", "r32", "r33"):
        rr = routes[tag]; sp = (rr.vego >= VLO) & (rr.vego < VHI)
        vals, tt = [], []
        for s in np.arange(0, rr.tg[-1], 1.0):
            m = (rr.tg >= s) & (rr.tg < s + 1.0) & sp & rr.eng
            if m.sum() >= 90:
                vals.append(bamp(rr.tq_raw[m], 18, 22)); tt.append(s)
        vals, tt = np.array(vals), np.array(tt)
        if not len(vals):
            pr("  %s: no 3-6 mph engaged seconds" % tag); continue
        line = "  %s: n=%d s ; bar 18-22 p50/p90/p99/max %.0f/%.0f/%.0f/%.0f raw" % (tag, len(vals), *np.percentile(vals, (50, 90, 99)), vals.max())
        if tag == "r34":
            for hhmmss, tr in wins:
                sel = (tt >= tr - HALF) & (tt <= tr + HALF)
                if sel.any():
                    line += " | window %s: n=%d, p50 %.0f max %.0f = route pct %.0f/%.0f" % (hhmmss, sel.sum(), np.median(vals[sel]), vals[sel].max(),
                                                                                         100 * np.mean(vals < np.median(vals[sel])), 100 * np.mean(vals < vals[sel].max()))
            top = np.argsort(vals)[::-1][:8]
            line += "\n     top-8 seconds route-wide: " + " ".join("t%.0f(%.0f)" % (tt[k], vals[k]) for k in top)
        pr(line)

    out = os.path.join(HERE, "_scratch", "grind_r34_operator.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
