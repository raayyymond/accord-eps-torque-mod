# -*- coding: utf-8 -*-
"""line156_localise.py -- where does the P2 line (engaged 0-5 m/s, 15.6 Hz, tap +6.1 dB / rate +4.7 dB) live?

P2 FIRED on it as written (spectra_by_band.py).  This does NOT re-score P2; it localises the line so the orchestrator
can ask the operator the right question.  Same loader, same PSD code (seg_psds nperseg 128 @ 50 Hz tap,
256 @ 100 Hz rate, excess_db +-2 Hz).
  1. split engaged 0-5 m/s into hands-off (|bar| < 400) / hands-on (|bar| >= 400) and by |cmd| (< 2000, >= 2000),
     and re-run the spectrum on each piece (is the line a hands-on / override object?);
  2. slide 2.56 s windows (hop 0.64 s) over engaged 0-5 m/s and list the windows carrying the most 14.5-16.8 Hz tap
     amplitude with their context (time, v, |bar|, |cmd|, angle, rate);
  3. the same split on the V293 references that carry an engaged 0-5 line (r72 19.5 Hz, r73 22.7 Hz, r75 20.7 Hz)
     so the family can be compared.
EVIDENCE for the numbers.  What the line physically is stays BELIEF.
"""
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
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def tap_runs(g, runs, npt=128):
    tT, T = g["T_t"], g["T"]
    out = []
    for a, b in runs:
        i0, i1 = np.searchsorted(tT, g["t"][a]), np.searchsorted(tT, g["t"][b - 1])
        if i1 - i0 >= npt:
            out.append(T[i0:i1])
    return out


def spec_line(g, m, fq, label):
    runs = C20.runs(m, 256)
    fr, Pr = C88.seg_psds([g["wire"][a:b] / CPD for a, b in runs], FS, 256)
    ft, Pt = C88.seg_psds(tap_runs(g, runs), FST, 128)
    row = "    %-34s %6.1f s | " % (label, m.sum() / FS)
    for nm, f, P in (("rate", fr, Pr), ("tap", ft, Pt)):
        if P.shape[0] < 5:
            row += "%s: n/a (%d seg)   " % (nm, P.shape[0]); continue
        ex = C88.excess_db(f, P.mean(0), 2.0)
        s = (f >= fq - 1.0) & (f <= fq + 1.0)
        k = int(np.argmax(ex[s]))
        df = f[1] - f[0]
        amp = np.sqrt(2 * P.mean(0)[(f >= fq - 1.2) & (f <= fq + 1.2)].sum() * df)
        row += "%s: peak %.1f Hz %+5.1f dB, amp %.2f %s (%d seg)   " % (nm, f[s][k], ex[s][k], amp, "deg/s" if nm == "rate" else "cnt", P.shape[0])
    pr(row)


def main():
    for tag, fq in (("r71b_v294", 15.6), ("r72_v293r3", 19.5), ("r73_v293r3", 22.7), ("r75_v293r4", 20.7)):
        g = C20.load(tag)
        base = g["eng"] & (g["vego"] < 5)
        pr("\n%s -- engaged 0-5 m/s, the line near %.1f Hz by stratum" % (tag, fq))
        spec_line(g, base, fq, "engaged 0-5 (all)")
        spec_line(g, base & (np.abs(g["bar"]) < 400), fq, "  hands-off |bar|<400")
        spec_line(g, base & (np.abs(g["bar"]) >= 400), fq, "  hands-on |bar|>=400")
        spec_line(g, base & (np.abs(g["cmd"]) < 2000), fq, "  |cmd| < 2000")
        spec_line(g, base & (np.abs(g["cmd"]) >= 2000), fq, "  |cmd| >= 2000")
        spec_line(g, base & (g["vego"] < 1.0), fq, "  v < 1 m/s")
        spec_line(g, base & (g["vego"] >= 1.0), fq, "  1-5 m/s")
        if tag != "r71b_v294":
            continue
        # sliding windows on the tap
        tT, T = g["T_t"], g["T"]
        m50 = np.interp(tT, g["t"], base.astype(float)) > 0.99
        W, H = 128, 32
        rows = []
        from scipy import signal as sg
        sos = sg.butter(4, [14.5, 16.8], btype="bandpass", fs=FST, output="sos")
        for s in range(0, len(T) - W, H):
            if not m50[s:s + W].all():
                continue
            x = T[s:s + W] - T[s:s + W].mean()
            a = float(np.sqrt(2.0) * sg.sosfiltfilt(sos, x).std())
            t0, t1 = tT[s], tT[s + W - 1]
            k0, k1 = np.searchsorted(g["t"], t0), np.searchsorted(g["t"], t1)
            rows.append((a, t0 - g["t"][0], float(np.median(g["vego"][k0:k1])), float(np.median(np.abs(g["bar"][k0:k1]))),
                         float(np.median(np.abs(g["cmd"][k0:k1]))), float(np.median(g["ang"][k0:k1])),
                         float(np.percentile(np.abs(g["wire"][k0:k1] / CPD), 90)),
                         float(np.median(np.abs(T[s:s + W])))))
        rows.sort(key=lambda r: -r[0])
        amps = np.array([r[0] for r in rows])
        pr("    sliding 2.56 s windows on engaged 0-5 m/s: n %d, 14.5-16.8 Hz tap amp p50 %.2f p90 %.2f max %.2f counts"
           % (len(rows), np.median(amps), np.percentile(amps, 90), amps.max()))
        tot = np.sum(amps ** 2)
        pr("    share of the 14.5-16.8 Hz tap energy in the top 5 / 10 windows (overlapping x4): %.0f %% / %.0f %%"
           % (100 * np.sum(amps[:5] ** 2) / tot, 100 * np.sum(amps[:10] ** 2) / tot))
        pr("      amp    t_route   v     |bar|   |cmd|   angle  |rate|p90  |T|med")
        for r in rows[:12]:
            pr("    %6.2f  %8.1f  %4.1f  %6.0f  %6.0f  %6.1f  %7.1f  %6.0f" % r)
    open(os.path.join(HERE, "line156_localise_out.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
