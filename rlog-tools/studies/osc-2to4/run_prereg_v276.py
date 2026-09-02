#!/usr/bin/env python3
"""Run the V276 PRE-REGISTRATION (`PREREG-V276-2to4Hz-READ.md`) on route r2e, EXACTLY as written.

Route  : 75604b0a432fdc89_0000002e--855ecfcf30  (16 segments)  -> cache r2e, probe_build V276
Tests  : the 8 numbered rows of the pre-reg's section 3, each printed against its own
         CONFIRMS / REFUTES threshold.  No thresholds are moved here; if one is unavailable the
         script says "UNAVAILABLE", never "negative".
Extra  : the waveform-shape read the orchestrator asked for (crest factor / kurtosis / clip duty
         of the 2-4 Hz band-passed command and rate inside the oscillation episodes).

Every statistic is computed by the SAME functions as the primary instrument
(`band_excess_2to4_speed_matched.py`), imported, not re-typed.

Usage:  python rlog-tools/studies/osc-2to4/run_prereg_v276.py [--route r2e] [--json OUT]
"""
import os, sys, json, argparse
import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import band_excess_2to4_speed_matched as B          # the primary instrument

FS, NPS = B.FS, B.NPS
BAND = B.BAND
STRATA = B.SPEED_BINS
CACHE_ROOTS = ("analysis-2020accord/_scratch/cache", "_scratch/cache")


def find_cache(tag):
    for r in CACHE_ROOTS:
        p = os.path.join(r, tag, tag + ".npz")
        if os.path.exists(p):
            return p
    raise SystemExit("no cache for %s" % tag)


def rolling_median_abs(x, w):
    pad = np.pad(np.abs(x), (w // 2, w - 1 - w // 2), mode="edge")
    return np.median(sliding_window_view(pad, w), axis=-1)[: len(x)]


def cell_stats(d, segs):
    """excess24 / peak / coh / gain on a given set of contiguous runs -- same math as B.score."""
    out = {"secs": sum(b - a for a, b in segs) / FS, "n_runs": len(segs)}
    if out["secs"] < 2 * NPS / FS:
        return out
    for ch in ("rate_f", "ang", "tq", "co_req", "e4tq"):
        if d.get(ch) is None:
            continue
        f, P = B.welch_runs(d[ch], segs)
        E = B.excess_curve(f, P)
        c = {"pow24": B.bandmean(f, P, BAND)}
        if E is not None:
            c["excess24"] = B.bandmean(f, E, BAND)
            pf, pe, pq = B.interior_peak(f, E)
            c.update(peak_f=pf, peak_excess=pe, peak_Q=pq)
            c["_E"] = E; c["_f"] = f
        out[ch] = c
    if d.get("e4tq") is not None:
        r = B.csd_runs(d["e4tq"], d["rate_f"], segs)
        if r:
            f, Pxy, Pxx, Pyy = r
            bm = (f >= BAND[0]) & (f < BAND[1])
            coh = np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30)
            out["coh24"] = float(np.mean(coh[bm]))
            wgt = np.abs(Pxy[bm])
            out["ph24"] = float(np.degrees(np.angle(np.sum(Pxy[bm] * wgt))))
            out["gain24"] = float(np.sqrt(np.mean(Pyy[bm]) / max(np.mean(Pxx[bm]), 1e-30)))
    return out


def bandpass(x, lo=2.0, hi=4.0, order=4):
    sos = signal.butter(order, [lo, hi], btype="band", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, np.nan_to_num(np.asarray(x, float)))


def envelope(x):
    return np.abs(signal.hilbert(x))


def fmt(v, p=3):
    return ("%%.%df" % p) % v if isinstance(v, (int, float)) and np.isfinite(v) else "  n/a"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", default="r2e")
    ap.add_argument("--json")
    args = ap.parse_args()
    fp = find_cache(args.route)
    d = B.load(fp)
    assert d is not None, "cache lacks a needed channel"
    z = np.load(fp, allow_pickle=True)
    d["ct_dcurv"] = np.nan_to_num(np.asarray(z["ct_dcurv"], float)) if "ct_dcurv" in z.files else None
    n = len(d["cs_v"]); T = n / FS
    v, lat = d["cs_v"], d["cc_lat"]
    eng = lat > 0.5
    print("=" * 110)
    print("V276 PRE-REGISTRATION READ  route %s  build(npz)=%s  cache=%s" % (d["_tag"], d["_build"], fp))
    print("  %d rows = %.1f min;  engaged %.1f min;  manual %.1f min" % (n, T / 60, eng.sum() / FS / 60,
                                                                        (~eng).sum() / FS / 60))
    for nm, lo, hi in STRATA:
        inb = (v >= lo) & (v < hi)
        print("  stratum %-4s  engaged %6.1f s   manual %6.1f s" % (nm, (inb & eng).sum() / FS,
                                                                   (inb & ~eng).sum() / FS))
    print("=" * 110)

    R = {"route": d["_tag"], "build": d["_build"]}
    cells = {}
    for nm, lo, hi in STRATA:
        inb = (v >= lo) & (v < hi)
        for arm, am in (("ENG", eng), ("MAN", ~eng)):
            segs = B.runs_of(inb & am, NPS)
            cells["%s.%s" % (nm, arm)] = cell_stats(d, segs)
    R["cells"] = {k: {kk: vv for kk, vv in c.items() if not isinstance(vv, dict)} |
                  {ch: {kk: vv for kk, vv in c[ch].items() if not kk.startswith("_")}
                   for ch in ("rate_f", "ang", "tq", "co_req", "e4tq") if ch in c}
                  for k, c in cells.items()}

    def g(k, ch, f_):
        x = cells.get(k, {}).get(ch)
        return x.get(f_, np.nan) if isinstance(x, dict) else np.nan

    # ------------------------------------------------------------------ TEST 1 + 8
    print("\nTEST 1 -- is there a real 2-4 Hz oscillation?   CONFIRMS: excess24(rate_f) >= 2.5 engaged in >=2 strata "
          "with >=120 s each.   REFUTES: excess24 <= 1.4 (corpus p95).")
    print("TEST 8 -- ALL speeds?   CONFIRMS: excess24 >= 2.5 in all three strata.")
    conf1 = 0; conf8 = 0; avail8 = 0
    for nm, _, _ in STRATA:
        k = "%s.ENG" % nm
        s = cells[k]["secs"]; e = g(k, "rate_f", "excess24")
        tag = "CONFIRMS" if (e >= 2.5 and s >= 120) else ("REFUTES(<=1.4)" if e <= 1.4 else "between")
        if s < 2 * NPS / FS:
            tag = "UNAVAILABLE (<10.24 s)"
        print("   %-4s  engaged %7.1f s  runs %3d   excess24(rate_f)=%s   excess24(ang)=%s   -> %s"
              % (nm, s, cells[k]["n_runs"], fmt(e), fmt(g(k, "ang", "excess24")), tag))
        conf1 += int(e >= 2.5 and s >= 120)
        if s >= 2 * NPS / FS:
            avail8 += 1; conf8 += int(e >= 2.5)
    print("   TEST 1 verdict: %s  (%d strata >= 2.5 with >= 120 s)" % ("CONFIRMS" if conf1 >= 2 else "NOT confirmed", conf1))
    print("   TEST 8 verdict: %s  (%d of %d available strata >= 2.5)" % ("CONFIRMS" if (conf8 == 3) else "NOT confirmed", conf8, avail8))
    R["test1"] = {"n_strata_confirm": conf1}; R["test8"] = {"n_confirm": conf8, "n_avail": avail8}

    # ------------------------------------------------------------------ TEST 2
    print("\nTEST 2 -- PEAK not broadband?   CONFIRMS: strict interior max in 1.6-5.0 Hz, peak excess >= 3, Q >= 3, "
          "same fc (+-0.4 Hz) in every stratum.   REFUTES: no interior max, or fc moving > 1 Hz.")
    pks = {}
    for nm, _, _ in STRATA:
        k = "%s.ENG" % nm
        if cells[k]["secs"] < 2 * NPS / FS:
            continue
        pf, pe, pq = g(k, "rate_f", "peak_f"), g(k, "rate_f", "peak_excess"), g(k, "rate_f", "peak_Q")
        cf, ce, cq = g(k, "e4tq", "peak_f"), g(k, "e4tq", "peak_excess"), g(k, "e4tq", "peak_Q")
        pks[nm] = pf
        print("   %-4s  rate_f: fc=%s Hz  peak_excess=%s  Q=%s   |  e4tq: fc=%s  peak_excess=%s  Q=%s"
              % (nm, fmt(pf, 2), fmt(pe, 2), fmt(pq, 2), fmt(cf, 2), fmt(ce, 2), fmt(cq, 2)))
    fcs = [x for x in pks.values() if np.isfinite(x)]
    spread = (max(fcs) - min(fcs)) if fcs else np.nan
    ok2 = (len(fcs) == len(pks) and len(fcs) > 0 and spread <= 0.8 and
           all(g("%s.ENG" % nm, "rate_f", "peak_excess") >= 3 and g("%s.ENG" % nm, "rate_f", "peak_Q") >= 3 for nm in pks))
    print("   fc spread across strata = %s Hz   TEST 2 verdict: %s" % (fmt(spread, 2), "CONFIRMS" if ok2 else
          ("REFUTES (fc spread > 1 Hz or no interior max)" if (not fcs or len(fcs) < len(pks) or spread > 1.0) else "NOT confirmed (peak/Q below threshold)")))
    R["test2"] = {"peak_f": pks, "spread": spread}
    # print the excess curve itself for the operator
    for nm in pks:
        c = cells["%s.ENG" % nm]["rate_f"]
        f, E = c["_f"], c["_E"]
        m = (f >= 1.0) & (f <= 6.0)
        print("   %-4s excess curve 1-6 Hz (rate_f): " % nm + " ".join("%.1f:%.2f" % (ff, ee) for ff, ee in zip(f[m][::2], E[m][::2])))

    # ------------------------------------------------------------------ TEST 3
    print("\nTEST 3 -- ENGAGED-ONLY?   CONFIRMS: engaged/manual excess24 >= 3 in a matched stratum with >= 60 s both arms.  "
          "REFUTES: ratio <= 1.5.   No manual frames at speed => UNAVAILABLE.")
    R["test3"] = {}
    for nm, _, _ in STRATA:
        kE, kM = "%s.ENG" % nm, "%s.MAN" % nm
        sE, sM = cells[kE]["secs"], cells[kM]["secs"]
        eE, eM = g(kE, "rate_f", "excess24"), g(kM, "rate_f", "excess24")
        if sE < 60 or sM < 60:
            tag = "UNAVAILABLE (eng %.0f s, man %.0f s in contiguous >=5.12 s runs)" % (sE, sM)
            ratio = np.nan
        else:
            ratio = eE / eM
            tag = "CONFIRMS" if ratio >= 3 else ("REFUTES" if ratio <= 1.5 else "between")
        print("   %-4s  eng excess24=%s (%.0f s)  man excess24=%s (%.0f s)  ratio=%s  -> %s"
              % (nm, fmt(eE), sE, fmt(eM), sM, fmt(ratio, 2), tag))
        R["test3"][nm] = {"ratio": ratio, "secE": sE, "secM": sM, "excE": eE, "excM": eM}

    # ------------------------------------------------------------------ TEST 4 + 7
    print("\nTEST 4 -- THE DISCRIMINATOR (command vs response), per stratum, engaged:")
    print("   OUTER (comma):   cmd_excess24 >= 2.5 AND coh24 >= 0.8, rate follows")
    print("   INNER (firmware): cmd_excess24 <= 1.3 while rate_excess24 >= 2.5")
    print("   AMBIGUOUS:       both >= 2.5 with coh24 <= 0.5")
    print("TEST 7 -- plant more responsive?  CONFIRMS: gain24 >= 0.10.  REFUTES: gain24 in [0.009, 0.048].")
    print("   %-4s | %8s %8s %8s %8s | %6s %7s %8s | %s" % ("spd", "secs", "rateExc", "e4Exc", "coreqExc", "coh24", "ph24", "gain24", "row"))
    R["test4"] = {}
    for nm, _, _ in STRATA:
        k = "%s.ENG" % nm
        if cells[k]["secs"] < 2 * NPS / FS:
            print("   %-4s   UNAVAILABLE" % nm); continue
        re_, ce_, co_ = g(k, "rate_f", "excess24"), g(k, "e4tq", "excess24"), g(k, "co_req", "excess24")
        coh, ph, gn = cells[k].get("coh24", np.nan), cells[k].get("ph24", np.nan), cells[k].get("gain24", np.nan)
        if ce_ >= 2.5 and coh >= 0.8:
            row = "OUTER-loop row (openpilot ringing; comma-side fix)"
        elif ce_ <= 1.3 and re_ >= 2.5:
            row = "INNER-loop row (EPS ringing on a smooth command; V278 exists)"
        elif ce_ >= 2.5 and re_ >= 2.5 and coh <= 0.5:
            row = "AMBIGUOUS row (common drive / two effects)"
        else:
            row = "NO ROW MATCHES (outside all three pre-registered cells)"
        t7 = "CONFIRMS" if gn >= 0.10 else ("REFUTES" if 0.009 <= gn <= 0.048 else "between")
        print("   %-4s | %8.0f %8.3f %8.3f %8.3f | %6.3f %7.1f %8.4f | %s ; gain24 -> TEST 7 %s"
              % (nm, cells[k]["secs"], re_, ce_, co_, coh, ph, gn, row, t7))
        R["test4"][nm] = dict(secs=cells[k]["secs"], rate_excess24=re_, cmd_excess24=ce_, coreq_excess24=co_,
                              coh24=coh, ph24=ph, gain24=gn, row=row, test7=t7)

    # ------------------------------------------------------------------ TEST 5 -- self-exciting
    print("\nTEST 5 -- SELF-EXCITING?   CONFIRMS: 2-4 Hz analytic envelope of rate_f shows episodes rising >= 3x over "
          ">= 3 s with no matching rise in ct_dcurv.   REFUTES: envelope tracks ct_dcurv.")
    bp_rate = bandpass(d["rate_f"]); env_r = envelope(bp_rate)
    bp_cmd = bandpass(d["e4tq"]); env_c = envelope(bp_cmd)
    w1 = int(1.0 * FS)
    env_r_s = np.convolve(env_r, np.ones(w1) / w1, mode="same")
    have_dc = d["ct_dcurv"] is not None and np.any(d["ct_dcurv"] != 0)
    if have_dc:
        dc = d["ct_dcurv"]
        env_dc = np.convolve(np.abs(dc), np.ones(w1) / w1, mode="same")       # magnitude of the road/curvature input
        bp_dc = bandpass(dc); env_dc24 = np.convolve(envelope(bp_dc), np.ones(w1) / w1, mode="same")
    episodes = []
    # Scan engaged contiguous runs for rises: from a local trough to >= 3x within a window of >= 3 s.
    for a, b in B.runs_of(eng, int(8 * FS)):
        e = env_r_s[a:b]
        i = 0; L = len(e)
        while i < L - int(3 * FS):
            # trough at i; look ahead up to 12 s for a 3x rise
            j_end = min(L, i + int(12 * FS))
            seg = e[i:j_end]
            k = int(np.argmax(seg))
            if seg[k] >= 3 * e[i] and k >= int(3 * FS) and e[i] > 0:
                t0, t1 = a + i, a + i + k
                ep = {"t0": t0 / FS, "t1": t1 / FS, "dur": (t1 - t0) / FS, "rise": float(seg[k] / e[i]),
                      "env_peak": float(seg[k]), "v": float(np.mean(v[t0:t1]))}
                if have_dc:
                    ep["dcurv_rise"] = float((np.max(env_dc[t0:t1 + 1]) + 1e-12) / (env_dc[t0] + 1e-12))
                    ep["dcurv24_rise"] = float((np.max(env_dc24[t0:t1 + 1]) + 1e-12) / (env_dc24[t0] + 1e-12))
                    ep["dcurv_peak"] = float(np.max(np.abs(dc[t0:t1 + 1])))
                ep["cmd_env_peak"] = float(np.max(env_c[t0:t1 + 1]))
                episodes.append(ep)
                i = i + k + int(2 * FS)
            else:
                i += int(0.5 * FS)
    # keep only material episodes: peak envelope in the top decile of engaged envelope
    thr = np.percentile(env_r_s[eng], 90) if eng.any() else 0
    big = [ep for ep in episodes if ep["env_peak"] >= thr]
    print("   rise-episodes found (>=3x over >=3 s, engaged): %d ; of which reaching the top-decile engaged envelope (%.2f deg/s): %d"
          % (len(episodes), thr, len(big)))
    if have_dc:
        # correlation between the rate envelope and the road input envelope, engaged frames, 1 s smoothing
        m = eng
        r_all = np.corrcoef(env_r_s[m], env_dc[m])[0, 1] if m.sum() > 100 else np.nan
        r_24 = np.corrcoef(env_r_s[m], env_dc24[m])[0, 1] if m.sum() > 100 else np.nan
        print("   corr(env24 rate_f, |ct_dcurv| 1 s) engaged = %.3f ;  corr(env24 rate_f, env24 ct_dcurv) = %.3f" % (r_all, r_24))
        nm_ = sum(1 for ep in big if ep["dcurv_rise"] < 1.5)
        print("   big episodes with NO matching ct_dcurv rise (<1.5x): %d of %d" % (nm_, len(big)))
    else:
        print("   ct_dcurv absent or all-zero in cache -> road-input control UNAVAILABLE; envelope rises reported alone")
    for ep in sorted(big, key=lambda e: -e["env_peak"])[:12]:
        print("     t=%7.1f-%7.1f s (%4.1f s)  v=%4.1f m/s  rate env %5.2f -> x%4.1f  cmd env %6.1f  %s"
              % (ep["t0"], ep["t1"], ep["dur"], ep["v"], ep["env_peak"] / ep["rise"], ep["rise"], ep["cmd_env_peak"],
                 ("dcurv rise x%.1f (24Hz-band x%.1f)" % (ep["dcurv_rise"], ep["dcurv24_rise"])) if have_dc else ""))
    R["test5"] = {"n_episodes": len(episodes), "n_big": len(big), "episodes": big[:40]}

    # ------------------------------------------------------------------ TEST 6 -- hands on / off
    print("\nTEST 6 -- gripping kills it?   CONFIRMS: excess24 on hands-ON frames (5 s median |tq| >= 1200) <= 1/3 of hands-OFF.")
    ton = rolling_median_abs(d["tq"], int(5 * FS)) >= 1200
    R["test6"] = {}
    for nm, lo, hi in STRATA:
        inb = (v >= lo) & (v < hi) & eng
        sOn = B.runs_of(inb & ton, NPS); sOff = B.runs_of(inb & ~ton, NPS)
        cOn, cOff = cell_stats(d, sOn), cell_stats(d, sOff)
        eOn, eOff = cOn.get("rate_f", {}).get("excess24", np.nan), cOff.get("rate_f", {}).get("excess24", np.nan)
        if cOn["secs"] < 2 * NPS / FS or cOff["secs"] < 2 * NPS / FS:
            tag = "UNAVAILABLE (on %.0f s / off %.0f s)" % (cOn["secs"], cOff["secs"])
        else:
            tag = "CONFIRMS" if eOn <= eOff / 3 else "REFUTES/not confirmed"
        print("   %-4s  hands-ON  %6.1f s excess24=%s   hands-OFF %6.1f s excess24=%s   ratio on/off=%s  -> %s"
              % (nm, cOn["secs"], fmt(eOn), cOff["secs"], fmt(eOff), fmt(eOn / eOff if eOff else np.nan, 2), tag))
        R["test6"][nm] = dict(secOn=cOn["secs"], secOff=cOff["secs"], excOn=eOn, excOff=eOff)
    print("   (tq distribution engaged: p50 |tq| = %.0f, p90 = %.0f, frac hands-on = %.3f)"
          % (np.percentile(np.abs(d["tq"][eng]), 50), np.percentile(np.abs(d["tq"][eng]), 90), ton[eng].mean()))

    # ------------------------------------------------------------------ WAVEFORM SHAPE
    print("\nWAVEFORM SHAPE inside oscillation episodes (top-decile 2-4 Hz rate envelope, engaged):")
    print("   crest = peak/rms of the 2-4 Hz band-passed signal (sine 1.41, square 1.00, growing sinusoid > 1.41);")
    print("   kurtosis of band-passed signal (sine -1.5 excess, square -2.0, gaussian 0);  clip = fraction of RAW e4tq at >= 95%% of its route max |e4tq|.")
    thr = 2.0 * np.median(env_r_s[eng])
    hi_mask = eng & (env_r_s >= thr)
    segs_hi = B.runs_of(hi_mask, int(1 * FS))
    print("   NOTE: the excess PEAK sits at 3.9-4.5 Hz, at the 2-4 Hz band EDGE; a 2-4 Hz band-pass attenuates it. "
          "Rows tagged [2-6] use a 2-6 Hz band-pass (supplementary, NOT pre-registered).")
    bp_rate6, bp_cmd6 = bandpass(d["rate_f"], 2.0, 6.0), bandpass(d["e4tq"], 2.0, 6.0)
    e4 = d["e4tq"]; e4max = np.max(np.abs(e4[eng])) if eng.any() else np.nan
    rows = []
    for a, b in segs_hi:
        for nm_sig, x in (("rate", bp_rate), ("cmd", bp_cmd), ("rate[2-6]", bp_rate6), ("cmd[2-6]", bp_cmd6)):
            s = x[a:b]; rms = np.sqrt(np.mean(s ** 2)); pk = np.max(np.abs(s))
            k = float(np.mean(((s - s.mean()) / (s.std() + 1e-12)) ** 4) - 3)
            rows.append((a, b, nm_sig, pk / (rms + 1e-12), k))
    def agg(sig, idx):
        vals = [r[idx] for r in rows if r[2] == sig]
        return (np.median(vals), np.percentile(vals, 10), np.percentile(vals, 90)) if vals else (np.nan,) * 3
    print("   episode threshold: 1-s 2-4 Hz rate envelope >= 2x engaged median = %.2f deg/s; episodes >= 1 s: %d, total %.1f s"
          % (thr, len(segs_hi), sum(b - a for a, b in segs_hi) / FS))
    for a, b in segs_hi:
        print("     episode t=%7.1f-%7.1f s (%4.1f s) v=%4.1f  rate env %5.1f  cmd env %6.0f  p50|tq| %5.0f"
              % (a / FS, b / FS, (b - a) / FS, np.mean(v[a:b]), np.mean(env_r_s[a:b]), np.mean(env_c[a:b]),
                 np.median(np.abs(d["tq"][a:b]))))
    for sig in ("rate", "cmd", "rate[2-6]", "cmd[2-6]"):
        c = agg(sig, 3); k = agg(sig, 4)
        print("   %-9s crest median %.2f (p10 %.2f, p90 %.2f)   excess kurtosis median %.2f (p10 %.2f, p90 %.2f)"
              % (sig, *c, *k))
    if segs_hi:
        m_hi = np.zeros(n, bool)
        for a, b in segs_hi: m_hi[a:b] = True
        clip = np.mean(np.abs(e4[m_hi]) >= 0.95 * e4max)
        print("   raw e4tq during episodes: route max |e4tq| = %.0f ; fraction of episode samples >= 95%% of max = %.3f ; "
              "p50 |e4tq| in episodes = %.0f vs engaged overall p50 = %.0f"
              % (e4max, clip, np.percentile(np.abs(e4[m_hi]), 50), np.percentile(np.abs(e4[eng]), 50)))
        # amplitude trajectory inside the longest episode: growth or plateau?
        a, b = max(segs_hi, key=lambda s: s[1] - s[0])
        e = env_r_s[a:b]; t = np.arange(len(e)) / FS
        q = max(1, len(e) // 5)
        print("   longest episode t=%.1f-%.1f s (%.1f s): rate env by fifths = %s ; cmd env by fifths = %s"
              % (a / FS, b / FS, (b - a) / FS,
                 " ".join("%.2f" % np.mean(e[i:i + q]) for i in range(0, len(e), q)),
                 " ".join("%.0f" % np.mean(env_c[a:b][i:i + q]) for i in range(0, len(e), q))))
        # dominant frequency inside episodes, from the PSD of the raw rate on these runs
        long_ = [s for s in segs_hi if s[1] - s[0] >= NPS]
        if long_:
            f, P = B.welch_runs(d["rate_f"], long_)
        else:
            # no episode reaches 5.12 s: welch each episode at its own length (coarser bins), length-weighted
            P = None; W = 0.0
            for a, b in segs_hi:
                s_ = d["rate_f"][a:b] - d["rate_f"][a:b].mean()
                f, p_ = signal.welch(s_, FS, nperseg=len(s_), noverlap=0, nfft=NPS)
                P = p_ * (b - a) if P is None else P + p_ * (b - a); W += (b - a)
            P = P / W
            print("   (no episode >= 5.12 s: per-episode periodograms zero-padded to %d bins)" % NPS)
        if f is not None:
            E = B.excess_curve(f, P)
            m = (f >= 1.0) & (f <= 8.0)
            fd = f[m][np.argmax(P[m])]
            pf, pe, pq = B.interior_peak(f, E) if E is not None else (np.nan,) * 3
            print("   dominant PSD frequency in episodes (1-8 Hz) = %.2f Hz ; interior excess peak fc=%s excess=%s Q=%s"
                  % (fd, fmt(pf, 2), fmt(pe, 2), fmt(pq, 2)))
            R["waveform"] = dict(n_ep=len(segs_hi), f_dom=float(fd), peak_f=pf, peak_excess=pe, peak_Q=pq,
                                 crest_rate=agg("rate", 3)[0], crest_cmd=agg("cmd", 3)[0],
                                 kurt_rate=agg("rate", 4)[0], kurt_cmd=agg("cmd", 4)[0], clip=float(clip))
    if args.json:
        json.dump(R, open(args.json, "w"), indent=1, default=float)
        print("\nwrote %s" % args.json)


if __name__ == "__main__":
    main()
