# -*- coding: utf-8 -*-
"""outer_loop_reads.py -- the record's OWN outer-loop / hard-turn / limit-cycle readers, run unchanged on
r71b_v294 against r75_v293r4 (rev 4) and r76_v293r5 (rev 5).  Subagent "bands", 2026-09-30.  ANALYSIS ONLY.

Called as library functions so that nothing is written into rlog-tools/studies/grind (their main()s write report
files there).  Every section below is the named function, not a re-implementation, except where marked COPIED:
  A  v293r5_read   n0 (attribution), n1 (IV torque->angle and closed-loop planner->actual |H|), n2 (stiction /
                   breakaway + hard-turn roughness), n3 (integrator), n6 (tracking vs the planner: gain, lag, rms,
                   |H|(0.2), error energy <0.3 / 0.3-1 / >1 Hz)
  B  v293r5_observer_read.read  O2 (planner-error rms 0.05-0.3 / 0.3-1 / 1-3 Hz + integrator share), O3 (des->act |H|
                   at 0.2-2 Hz), O4 (hard turns v<10: 1.6-3 Hz share of 0.3-8 Hz wheel-rate energy, reversals)
  C  v293r3_read.analyse + compare  S2 tracking, S3 the 1.6-3 Hz mode on curves/straights, S4 hard-turn jerkiness,
                   S5 torque shares, S8 straight-line looseness, S9 cross-route table
  D  COPIED from v293r2_read.main S7 (the route-71-old 2.34 Hz limit-cycle instrument), verbatim, plus the same
                   computation restricted to v >= 19 m/s as pre-registered (criterion P4)
  E  saturation share: torqueState.saturated and |cmd| >= 4096 on engaged frames, by band (new, trivial counts)
  F  matched speed x demand 1.6-3 Hz wheel-rate rms (criterion P1 "matched speed/demand"): hands-off (0.5 s buffer),
     cells = speed band x |planner lat accel| bin, stretches >= 3 s, 4th-order band-pass 1.6-3 Hz (v293_ident_lib)
"""
import io
import os
import sys
from contextlib import redirect_stdout

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, *[".."] * 5))
G = os.path.join(KIT, "rlog-tools", "studies", "grind")
sys.path.insert(0, G)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import v293_ident_lib as L          # noqa: E402
import v293r3_read as R3            # noqa: E402
import v293r5_read as R5            # noqa: E402
import v293r5_observer_read as OB   # noqa: E402

FS, DT = 100.0, 0.01
TAGS = ["r71b_v294", "r75_v293r4", "r76_v293r5"]


def sec_D(tag):
    """COPIED verbatim from v293r2_read.main S7 (masks and prints), then again at v >= 19 (P4)."""
    g = R3.load_plus(tag)
    v, ang, rate = g["v"], g["ang"], g["rate_dps"]
    eng = g["eng"] & np.isfinite(v) & np.isfinite(-g["op_torque"])
    ok = np.isfinite(rate) & np.isfinite(ang)
    c = np.corrcoef(rate[ok], np.gradient(ang, DT)[ok])[0, 1]
    rate_s = rate if c > 0 else -rate
    out = {}
    for vmin, lab in ((15.0, "S7 as written: v>15"), (19.0, "S7 at v>=19 (P4)")):
        m = eng & (v > vmin if vmin == 15.0 else v >= vmin) & (np.abs(g["la_des"]) > 1.0)
        runs = L.stretches(m, int(5 * FS))
        print("  %s  %s, |Ddes|>1.0, engaged runs >= 5 s:" % (tag, lab))
        if not runs:
            print("    no runs -- NOT TESTABLE"); out[lab] = None; continue
        tot = sum(b - a for a, b in runs)
        E = np.concatenate([g["err"][a:b] for a, b in runs])
        zc = np.sum(np.diff(np.sign(E)) != 0) / (tot * DT)
        print("    %d runs, %.0f s; error rms %.3f m/s2, zero-crossings %.2f /s (=> ~%.2f Hz if a cycle)" % (len(runs), tot * DT, np.sqrt(np.mean(E ** 2)), zc, zc / 2))
        res = {}
        for cname, x in (("rate", rate_s), ("cmd", g["cmd"]), ("err", g["err"]), ("angle", ang)):
            X = np.concatenate([signal.detrend(x[a:b]) for a, b in runs])
            f, Pw = signal.welch(X, fs=FS, nperseg=512, noverlap=256, detrend="linear")
            sel = (f >= 0.3) & (f <= 3.0)
            fs_, Ps = f[sel], Pw[sel]
            k = int(np.argmax(Ps))
            sh = ((f >= 0.3 / 1.6) & (f < 0.3)) | ((f > 3.0) & (f <= 3.0 * 1.6))
            cc = np.polyfit(np.log(f[sh]), np.log(Pw[sh] + 1e-30), 1)
            prom = 10 * np.log10((Ps[k] + 1e-30) / (np.exp(np.polyval(cc, np.log(fs_[k]))) + 1e-30))
            rms = np.sqrt(np.mean(L.bandpass(X, 0.5, 3.0) ** 2))
            res[cname] = (float(fs_[k]), float(prom), float(rms))
            print("      %-6s peak 0.3-3 Hz at %.2f Hz, prominence %+.1f dB; rms 0.5-3 Hz %.3f" % (cname, fs_[k], prom, rms))
        fired = res["rate"][0] >= 2.0 and res["rate"][0] <= 2.7 and res["rate"][1] >= 10.0
        print("    P4 rule (rate peak in 2.0-2.7 Hz AND prominence >= +10 dB): %s" % ("FIRES" if fired else "does not fire"))
        out[lab] = dict(runs=len(runs), s=tot * DT, rate=res["rate"], cmd=res["cmd"], err=res["err"], angle=res["angle"], fired=fired)
    return out


def sec_E(tag):
    g = R3.load_plus(tag)
    v = g["v"]
    eng = g["eng"] & (g["cs_active"] > 0.5)
    print("  %s  saturation on engaged+active frames:" % tag)
    for lo, hi, nm in ((0, 5, "0-5"), (5, 10, "5-10"), (10, 15, "10-15"), (15, 22, "15-22"), (22, 99, "22+")):
        m = eng & (v >= lo) & (v < hi)
        if m.sum() < 100:
            continue
        print("    %-6s %6.0f s | torqueState.saturated %.2f %% | |cmd| >= 4096 %.2f %% | |op torque| >= 0.95 %.2f %% | hands-off: sat %.2f %%"
              % (nm, m.sum() * DT, 100 * np.nanmean(g["sat"][m] > 0.5), 100 * np.mean(np.abs(g["cmd"][m]) >= 4096),
                 100 * np.mean(np.abs(g["op_torque"][m]) >= 0.95),
                 100 * np.nanmean(g["sat"][m & (g["press"] < 0.5)] > 0.5) if (m & (g["press"] < 0.5)).any() else np.nan))


def sec_F(tag):
    g = R3.load_plus(tag)
    v = g["v"]; ang = g["ang"]; rate = g["rate_dps"]
    eng = g["eng"] & (g["cs_active"] > 0.5)
    w = int(0.5 * FS)
    pb = np.convolve((g["press"] > 0.5).astype(float), np.ones(2 * w + 1), mode="same") > 0
    ho = eng & ~pb
    lap = np.abs(g["des_curv"] * v ** 2)
    rows = {}
    for lo, hi, nm in ((0, 5, "0-5"), (5, 10, "5-10"), (10, 15, "10-15"), (15, 22, "15-22"), (22, 99, "22+")):
        for dlo, dhi, dn in ((0.0, 0.5, "|D|<0.5"), (0.5, 1.5, "0.5-1.5"), (1.5, 99, ">1.5")):
            m = ho & (v >= lo) & (v < hi) & (lap >= dlo) & (lap < dhi) & np.isfinite(rate)
            st = L.stretches(m, int(3 * FS))
            s = sum(b - a for a, b in st) * DT
            if s < 10:
                rows[(nm, dn)] = (s, np.nan, np.nan); continue
            r16 = np.concatenate([L.bandpass(rate[a:b], 1.6, 3.0) for a, b in st])
            r03 = np.concatenate([L.bandpass(rate[a:b], 0.3, 8.0) for a, b in st])
            rows[(nm, dn)] = (s, float(np.sqrt(np.mean(r16 ** 2))), float(100 * np.mean(r16 ** 2) / np.mean(r03 ** 2)))
    return rows


def main():
    buf = io.StringIO()

    class Tee:
        def write(self, s):
            sys.__stdout__.write(s); buf.write(s)

        def flush(self):
            sys.__stdout__.flush()
    with redirect_stdout(Tee()):
        print("=" * 120); print("A. v293r5_read  n0 / n1 / n2 / n3 / n6"); print("=" * 120)
        for t in TAGS:
            R = R5.load(t)
            R5.n0(R); R5.n1(R); R5.n2(R); R5.n3(R); R5.n6(R)
        print("\n" + "=" * 120); print("B. v293r5_observer_read.read  O1..O4"); print("=" * 120)
        for t in TAGS:
            OB.read(t)
        print("\n" + "=" * 120); print("C. v293r3_read.analyse + compare  (S6 = the rev-3 FF replay; on V294's generic path it is NOT the law that ran -- REPORT only)"); print("=" * 120)
        RS = []
        for t in TAGS:
            try:
                RS.append(R3.analyse(t))
            except Exception as e:
                print("    analyse(%s) raised %r" % (t, e))
        if len(RS) > 1:
            R3.compare(RS)
        print("\n" + "=" * 120); print("D. THE 2.34 Hz LIMIT-CYCLE CHECK (v293r2_read S7, copied) -- criterion P4"); print("=" * 120)
        for t in TAGS + ["r71_v293r2"]:
            sec_D(t)
        print("\n" + "=" * 120); print("E. SATURATION SHARE"); print("=" * 120)
        for t in TAGS:
            sec_E(t)
        print("\n" + "=" * 120); print("F. MATCHED SPEED x DEMAND: 1.6-3 Hz wheel-rate rms (deg/s) and its share of 0.3-8 Hz energy, hands-off"); print("=" * 120)
        F = {t: sec_F(t) for t in TAGS}
        keys = list(F[TAGS[0]].keys())
        print("  %-7s %-8s | " % ("band", "|D|") + " | ".join("%-26s" % t for t in TAGS))
        for k in keys:
            print("  %-7s %-8s | " % k + " | ".join("%5.0f s  %6.2f dps  %4.0f %%  " % F[t][k] if np.isfinite(F[t][k][1]) else "%5.0f s        -              " % F[t][k][0] for t in TAGS))
    open(os.path.join(HERE, "outer_loop_reads_out.txt"), "w", encoding="utf-8").write(buf.getvalue())


if __name__ == "__main__":
    main()
