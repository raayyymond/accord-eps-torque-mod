# -*- coding: utf-8 -*-
"""d8_lightb_rep -- are the light_b hunt / 2-2.7 Hz hits REPRODUCIBLE or per-point coin flips?  light_b only, v >= 12,
S1 (crown 0/0.6/1.0/1.5/2.5/3.5) and S2 (a 0.5/1/1.5/2/2.5) rows, several sensor-noise seeds and pipes, paired across
configs.  Adds a LINE test for S2: Welch PSD of the hold-window wheel rate, prominence of the 2.0-2.7 Hz max above the
median of the 1.0-5.0 Hz band (a line >= +6 dB; stick-slip jumps are broadband)."""
import os, sys, json, time
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import d2_engine as E
import d5_synth as S
import v295_harness as H

fam = H.family()


def rows_lb():
    rows = []
    for v in (12.0, 17.0, 19.0, 22.0, 26.9):
        Fs = float(fam["light_b"].at(v).Fs)
        for cr in (0.0, 0.6, 1.0, 1.5, 2.5, 3.5):
            rows.append(dict(kind="S1", member="light_b", v=v, crown=cr, c0=cr * Fs))
        for a in (0.5, 1.0, 1.5, 2.0, 2.5):
            rows.append(dict(kind="S2", member="light_b", v=v, a=a, des=S.ramp_profile(a)))
    return rows


def line_prom(x):
    f, p = signal.welch(x - np.mean(x), fs=100.0, nperseg=512)
    b = (f >= 2.0) & (f <= 2.7)
    ref = (f >= 1.0) & (f <= 5.0)
    return float(10 * np.log10(np.max(p[b]) / np.median(p[ref]))), float(f[b][np.argmax(p[b])])


def main():
    runs = [(22, 7), (22, 11), (42, 3), (62, 3)]
    rows = rows_lb()
    out = {}
    t0 = time.time()
    for pipe, seed in runs:
        for cfg in ("V294+r1", "V295+r1", "V295+r2alt"):
            R = E.run(cfg, rows, 60.0, pipe_ms=pipe, seed=seed)
            sc = S.score(R, rows)
            for j, r in enumerate(rows):
                if r["kind"] == "S2":
                    sc[j]["prom"], sc[j]["fline"] = line_prom(R["rate"][j, 1200:2700])
            out["%d|%d|%s" % (pipe, seed, cfg)] = sc
            print("pipe %d seed %d %s %.0f s" % (pipe, seed, cfg, time.time() - t0), flush=True)
    json.dump(out, open(os.path.join(HERE, "out", "d8_lightb_rep.json"), "w"), indent=0)
    L = []
    P = lambda s: (print(s), L.append(s))  # noqa: E731
    C = ("V294+r1", "V295+r1", "V295+r2alt")
    for pipe, seed in runs:
        P("\n== pipe %d ms, seed %d (light_b) ==" % (pipe, seed))
        sc = {c: out["%d|%d|%s" % (pipe, seed, c)] for c in C}
        # S1: worst straight-road p-p per speed, and count of points with p-p >= 0.4 deg
        for v in (12.0, 17.0, 19.0, 22.0, 26.9):
            js = [j for j, r in enumerate(rows) if r["kind"] == "S1" and r["v"] == v]
            P("  S1 v%5.1f  worst p-p / n(>=0.4 deg) over 6 crowns:  " % v + "  ".join(
                "%s %.2f/%d" % (c, max(sc[c][j]["pp"] for j in js), sum(sc[c][j]["pp"] >= 0.4 for j in js)) for c in C))
        # S2: pooled c24 rms over the a-grid per speed + max line prominence + max in-curve peak
        for v in (12.0, 17.0, 19.0, 22.0, 26.9):
            js = [j for j, r in enumerate(rows) if r["kind"] == "S2" and r["v"] == v]
            P("  S2 v%5.1f  pooled 2.0-2.7 Hz rms / max line prom dB (f) / max peak_in / max hold:  " % v + "  ".join(
                "%s %.3f/%+.1f(%.2f)/%.2f/%.2f" % (c, float(np.sqrt(np.mean([sc[c][j]["c24"] ** 2 for j in js]))),
                                            max(sc[c][j]["prom"] for j in js),
                                            sc[c][max(js, key=lambda jj: sc[c][jj]["prom"])]["fline"],
                                            max(sc[c][j]["peak_in"] for j in js), max(sc[c][j]["hold"] for j in js)) for c in C))
    open(os.path.join(HERE, "out", "d8_lightb_rep_out.txt"), "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
