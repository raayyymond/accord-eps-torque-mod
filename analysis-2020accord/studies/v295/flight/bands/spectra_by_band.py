# -*- coding: utf-8 -*-
"""spectra_by_band.py -- full wheel-rate (0x18F, 100 Hz) and delivered-torque tap (0x1AB, 50 Hz, native samples)
spectra by speed band, the line list, and the pre-registered "NEW line in 5-30 Hz" test (criterion P2 in
CRITERIA-BANDS-r71b.md) for r71b_v294 against the V293 and V282 references.

Subagent "bands", 2026-09-30.  ANALYSIS ONLY.  Every estimator is the record's own, unchanged:
  * loader         creep20_loop_id.load (dejittered 0x18F frame axis; T on its native 50 Hz clock)
  * PSD            grind1_census_v288_r5e.seg_psds (Hann, 50 % overlap, per-segment periodograms, Welch = mean)
                   nperseg 256 at 100 Hz for the rate (= v293_flight_read.spectra), 128 at 50 Hz for the tap (same
                   2.56 s window, 0.39 Hz bins)
  * line strength  grind1_census_v288_r5e.excess_db (log-PSD minus a +-2 Hz running median) -- the scorer's "lines"
  * band amplitude v293_flight_read.band_amp_of convention: sqrt(2 * sum P * df), rate in deg/s (wire / 8)
  * masks          engaged = 0xE4 STEER_REQUEST & 0x18F SCA (the kit's lateral-engaged); hands-off = |bar| < 400
                   (the scorer's own hands-off predicate)
The wheel-rate sign does not matter for a PSD.

P2 as written BEFORE computing: a V294 line FIRES as NEW if its excess >= 3 dB, it lies in 5-30 Hz (tap: 5-24 Hz), and
NO V293 reference route has a line within +-1 Hz of it whose excess is >= (V294 excess - 3 dB) in the same speed band
and stratum.  Only strata with >= 60 s (>= 40 Welch segments) on the V294 route AND >= 1 reference are scored.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, *[".."] * 5))
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "grind"))
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "osc-highangle"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20            # noqa: E402
import grind1_census_v288_r5e as C88     # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FST, CPD = 100.0, 50.0, 8.0
V294 = "r71b_v294"
REF293 = ["r70_v293", "r71_v293r2", "r72_v293r3", "r73_v293r3", "r75_v293r4", "r76_v293r5"]
REF282 = ["r6c", "r39", "r3a", "r3c", "r35"]
SPEED = [("0-5", 0, 5), ("5-10", 5, 10), ("10-15", 10, 15), ("15-22", 15, 22), ("22+", 22, 99)]
STRATA = [("hands-off", lambda g: g["eng"] & (np.abs(g["bar"]) < 400)), ("engaged", lambda g: g["eng"])]
BANDS = [("1.6-3", 1.6, 3.0), ("3-5", 3.0, 5.0), ("5-9", 5, 9), ("9-13", 9, 13), ("13-17", 13, 17),
         ("18-22", 18, 22), ("22-26", 22, 26), ("26-30", 26, 30), ("30-45", 30, 45)]
NPR, NPT = 256, 128
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def lines_of(f, ex, lo, hi, thr=3.0):
    """local maxima of the excess-dB curve in [lo, hi] with excess >= thr, strongest first."""
    out = []
    for i in range(1, len(f) - 1):
        if lo <= f[i] <= hi and ex[i] >= thr and ex[i] >= ex[i - 1] and ex[i] >= ex[i + 1]:
            out.append((float(f[i]), float(ex[i])))
    return sorted(out, key=lambda x: -x[1])


def route_spectra(tag):
    g = C20.load(tag)
    res = {}
    tT, T = g["T_t"], g["T"]
    for sname, sfn in STRATA:
        sm = sfn(g)
        for bname, lo, hi in SPEED:
            m = sm & (g["vego"] >= lo) & (g["vego"] < hi)
            runs = C20.runs(m, NPR)
            fr, Pr = C88.seg_psds([g["wire"][a:b] / CPD for a, b in runs], FS, NPR)
            # tap: map each 100 Hz run to native tap samples by time
            truns = []
            for a, b in runs:
                i0, i1 = np.searchsorted(tT, g["t"][a]), np.searchsorted(tT, g["t"][b - 1])
                if i1 - i0 >= NPT:
                    truns.append(T[i0:i1])
            ft, Pt = C88.seg_psds(truns, FST, NPT)
            cell = dict(t_s=float(m.sum() / FS), nseg_r=int(Pr.shape[0]), nseg_t=int(Pt.shape[0]))
            if Pr.shape[0] >= 5:
                Pm = Pr.mean(0); df = fr[1] - fr[0]
                cell["rate_amp"] = {n: float(np.sqrt(2.0 * Pm[(fr >= a) & (fr <= b)].sum() * df)) for n, a, b in BANDS}
                ex = C88.excess_db(fr, Pm, half_hz=2.0)
                cell["rate_lines"] = lines_of(fr, ex, 1.0, 45.0)[:8]
                cell["rate_ex"] = ex.tolist(); cell["f_r"] = fr.tolist()
            if Pt.shape[0] >= 5:
                Pm = Pt.mean(0); df = ft[1] - ft[0]
                cell["tap_amp"] = {n: float(np.sqrt(2.0 * Pm[(ft >= a) & (ft <= b)].sum() * df)) for n, a, b in BANDS if b <= 25}
                ex = C88.excess_db(ft, Pm, half_hz=2.0)
                cell["tap_lines"] = lines_of(ft, ex, 1.0, 24.0)[:8]
                cell["tap_ex"] = ex.tolist(); cell["f_t"] = ft.tolist()
            res[(sname, bname)] = cell
    return res


def near_ref(fq, db, refcells, key_f, key_ex):
    """max excess of any reference within +-1 Hz of fq (the reference's own excess curve, not only its listed peaks)"""
    best = -99.0
    for c in refcells:
        if key_ex not in c:
            continue
        f = np.asarray(c[key_f]); ex = np.asarray(c[key_ex])
        s = (f >= fq - 1.0) & (f <= fq + 1.0)
        if s.any():
            best = max(best, float(ex[s].max()))
    return best


def main():
    tags = [V294] + REF293 + REF282
    have = [t for t in tags if os.path.exists(os.path.join(C20.CACHE, t + ".npz"))]
    missing = [t for t in tags if t not in have]
    pr("=" * 130)
    pr("SPECTRA BY SPEED BAND -- wheel rate (0x18F) and 427 tap, r71b_v294 vs V293 and V282 references")
    pr("routes with a v280 cache: %s   missing: %s" % (have, missing))
    pr("=" * 130)
    S = {}
    for t in have:
        S[t] = route_spectra(t)
        print("   done", t, flush=True)
    # --- amplitudes table
    for sname, _ in STRATA:
        for sig, key in (("WHEEL RATE deg/s", "rate_amp"), ("TAP counts", "tap_amp")):
            pr("\n%s -- %s, band amplitude by speed band (exposure s in brackets)" % (sig, sname))
            nb = [b for b in BANDS if key == "rate_amp" or b[2] <= 25]
            pr("  %-6s %-12s %6s | " % ("band", "route", "s") + " ".join("%8s" % n for n, _, _ in nb))
            for bname, _, _ in SPEED:
                for t in have:
                    c = S[t].get((sname, bname), {})
                    if key not in c:
                        continue
                    pr("  %-6s %-12s %6.0f | " % (bname, t, c["t_s"]) + " ".join("%8.2f" % c[key][n] for n, _, _ in nb))
                pr("")
    # --- line lists
    for sname, _ in STRATA:
        pr("\nLINES (excess dB >= 3 over the +-2 Hz running median; strongest first) -- %s" % sname)
        for bname, _, _ in SPEED:
            for t in have:
                c = S[t].get((sname, bname), {})
                if "rate_lines" not in c:
                    continue
                pr("  %-6s %-12s rate: %s" % (bname, t, "  ".join("%.1f Hz %+.1f" % x for x in c["rate_lines"][:6])))
                if "tap_lines" in c:
                    pr("  %-6s %-12s tap : %s" % (bname, t, "  ".join("%.1f Hz %+.1f" % x for x in c["tap_lines"][:6])))
            pr("")
    # --- P2: the NEW-line test
    pr("\nP2 -- NEW LINE IN 5-30 Hz (tap 5-24 Hz) vs the V293 references, as pre-registered")
    fired = []
    refs293 = [t for t in REF293 if t in S]
    refs282 = [t for t in REF282 if t in S]
    for sname, _ in STRATA:
        for bname, _, _ in SPEED:
            c = S[V294].get((sname, bname), {})
            if c.get("t_s", 0) < 60:
                pr("  %-9s %-6s V294 exposure %.0f s < 60 s -- not scored" % (sname, bname, c.get("t_s", 0)))
                continue
            rc = [S[t][(sname, bname)] for t in refs293 if (sname, bname) in S[t]]
            rc282 = [S[t][(sname, bname)] for t in refs282 if (sname, bname) in S[t]]
            for sig, kl, kf, kex, hi in (("rate", "rate_lines", "f_r", "rate_ex", 30.0), ("tap", "tap_lines", "f_t", "tap_ex", 24.0)):
                for fq, db in c.get(kl, []):
                    if not (5.0 <= fq <= hi):
                        continue
                    best = near_ref(fq, db, rc, kf, kex)
                    best282 = near_ref(fq, db, rc282, kf, kex)
                    new = best < db - 3.0
                    tagx = "NEW vs V293" if new else "present on V293"
                    pr("  %-9s %-6s %-4s %5.1f Hz %+5.1f dB | best V293 ref within 1 Hz %+5.1f | best V282 ref %+5.1f | %s"
                       % (sname, bname, sig, fq, db, best, best282, tagx))
                    if new:
                        fired.append((sname, bname, sig, fq, db, best, best282))
    pr("\nP2 verdict: %s" % ("FIRED on %d line(s): %s" % (len(fired), fired) if fired else "did not fire (every >= 3 dB line in 5-30 Hz has a V293-reference counterpart within 1 Hz and 3 dB)"))
    js = {t: {"|".join(k): {kk: vv for kk, vv in v.items() if kk not in ("rate_ex", "f_r", "tap_ex", "f_t")}
              for k, v in S[t].items()} for t in S}
    json.dump(dict(cells=js, p2_fired=fired, missing=missing), open(os.path.join(HERE, "spectra_by_band_out.json"), "w"), indent=1)
    # keep the full excess curves for the page
    np.savez_compressed(os.path.join(HERE, "_scratch", "spectra_curves.npz"),
                        **{("%s|%s|%s|%s" % (t, s, b, k)): np.asarray(v[k]) for t in S for (s, b), v in S[t].items()
                           for k in ("f_r", "rate_ex", "f_t", "tap_ex") if k in v})
    open(os.path.join(HERE, "spectra_by_band_out.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
