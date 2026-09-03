#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""studies/osc-highangle/lanechange_loop.py -- is openpilot in the highway lane-change loop?  Companion to
lanechange_osc.py (same caches, same conventions).  For each route's highway frames (engaged, v >= 20, |ang| < 8)
and for each oscillation episode:

  1. The three H1 cross-spectral blocks around the outer loop, pooled Welch (1.28 s) on contiguous runs:
       H_op  = angle -> cmd   (openpilot's block: 0x14A angle in, 0xE4 command out)
       H_eps = cmd -> rate    (EPS + car: command in, 0x18F rate out)
       H_int = rate -> angle  (kinematics; should be ~1/(j*omega) up to the wire's sign/scale)
     and their product L = H_op * H_eps * H_int.  🛑 L is NOT the loop gain: the product of H1 estimates around a
     closed cycle is identically 1 when every block is coherent, so |L| only reports the coherence product.  It is
     kept as a sanity column.  The informative numbers are the individual blocks: H_op (does openpilot react at the
     line, with what gain and phase -- the same on every route?) and H_eps (rate per command count at the line,
     rev 3 vs V112 vs stock).  Coherence at each block is printed so a biased H1 is visible.
  2. Per episode: phase and gain of cmd re angle at f0; the openpilot block's low-frequency (0.3-2 Hz) gain for
     comparison; the delay of cmd behind angle from the phase slope over 1-6 Hz.
  3. The chain's two E contributions at 4-12 Hz on rev 3 episodes: amp(32*sp) [the setpoint ripple openpilot's
     command puts in] vs amp(fb) [the rate feedback ripple], and E's correlation with each.
  4. A 10 ms time-series dump of the largest r32 episode (rate, angle, cmd, T, E, P) for the report.

Run:  python lanechange_loop.py   (writes LANECHANGE-loop.txt beside itself)
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import highangle_stutter as H  # noqa: E402
import lanechange_osc as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS = 100.0
NPS = 128


def pooled_xspec(G, m, keys):
    """pooled auto/cross spectra over contiguous runs of m; returns f, dict of Pxy for the key pairs."""
    runs = H.runs_of(m, NPS)
    if not runs:
        return None, None
    acc = {}
    n = 0
    f = None
    for a, b in runs:
        X = {k: G[k][a:b] - G[k][a:b].mean() for k in keys}
        for i in keys:
            for j in keys:
                f, P = signal.csd(X[i], X[j], fs=FS, nperseg=NPS)
                acc[(i, j)] = acc.get((i, j), 0) + P * (b - a)
        n += b - a
    return f, {k: v / n for k, v in acc.items()}


def h1(S, x, y):
    return S[(x, y)] / np.real(S[(x, x)])


def coh(S, x, y):
    return np.abs(S[(x, y)]) ** 2 / (np.real(S[(x, x)]) * np.real(S[(y, y)]))


def loop_table(G, m, label, f_line, pr):
    f, S = pooled_xspec(G, m, ("ang", "cmd", "rate"))
    if f is None:
        pr("  %s: no runs" % label); return None
    Hop, Heps, Hint = h1(S, "ang", "cmd"), h1(S, "cmd", "rate"), h1(S, "rate", "ang")
    Lg = Hop * Heps * Hint
    Cop, Ceps, Cint = coh(S, "ang", "cmd"), coh(S, "cmd", "rate"), coh(S, "rate", "ang")
    pr("  %s  (%.0f s in Welch runs)" % (label, sum(b - a for a, b in H.runs_of(m, NPS)) / FS))
    pr("     f Hz | H_op=cmd/ang  |gain| ph coh | H_eps=rate/cmd |gain| ph coh | H_int=ang/rate |gain| ph coh |  coh-product |L| arg (NOT loop gain)")
    rows = {}
    for f0 in (1.56, 2.34, 3.13, 3.91, 4.69, 5.47, 6.25, 7.03, 7.81, 8.59, 9.38, 10.16, 10.94, 11.72, 12.5):
        j = int(np.argmin(np.abs(f - f0)))
        rows[float(f[j])] = dict(Lmag=float(np.abs(Lg[j])), Larg=float(np.degrees(np.angle(Lg[j]))),
                                 Hop=float(np.abs(Hop[j])), Heps=float(np.abs(Heps[j])), Cop=float(Cop[j]), Ceps=float(Ceps[j]))
        pr("    %5.2f |              %7.1f %5.0f %4.2f |               %6.3f %5.0f %4.2f |               %7.4f %5.0f %4.2f |  %8.3f %6.0f%s" % (
            f[j], np.abs(Hop[j]), np.degrees(np.angle(Hop[j])), Cop[j], np.abs(Heps[j]), np.degrees(np.angle(Heps[j])), Ceps[j],
            np.abs(Hint[j]), np.degrees(np.angle(Hint[j])), Cint[j], np.abs(Lg[j]), np.degrees(np.angle(Lg[j])),
            "   <- line" if abs(f[j] - f_line) < 0.5 else ""))
    return rows


def main():
    lines = []
    pr = lambda s="": (print(s), lines.append(s))  # noqa: E731
    J = json.load(open(os.path.join(HERE, "lanechange_events.json")))
    out = {}
    for tag in ("r32", "r33", "r22", "r97"):
        G = L.load(tag)
        hw = G["hw"]
        if hw.sum() < 500:
            continue
        C = L.chain(G)
        pr("=" * 120)
        pr("ROUTE %s (%s)" % (tag, L.ROUTES[tag][1]))
        # sign conventions at low frequency: does the command restore the angle?
        m = G["eng"] & (np.abs(G["ang"]) > 5) & (np.abs(G["cmd"]) > 200) & (G["v"] > 10)
        if m.any():
            pr("  steady sign check (engaged, |ang|>5, |cmd|>200, v>10, n=%d): sign(cmd) == -sign(ang) %.2f ; sign(rate) == sign(d ang/dt) %.2f" % (
                m.sum(), np.mean(np.sign(G["cmd"][m]) == -np.sign(G["ang"][m])),
                np.mean(np.sign(G["rate"][m]) == np.sign(np.gradient(L.lpf(G["ang"], 3.0), 1 / FS)[m]))))
        line = 7.5 if tag in L.HAS_TAP else 7.5
        out[tag] = {}
        out[tag]["hw_all"] = loop_table(G, hw, "HIGHWAY all frames", line, pr)
        mc = hw & (np.abs(G["cmd_lp"]) >= 100) & (np.abs(G["cmd_lp"]) < 300)
        out[tag]["hw_cmd100_300"] = loop_table(G, mc, "HIGHWAY |cmd| 100-300", line, pr)
        eps = [e for e in J["events"][tag] if e["kind"] == "OSC"]
        excs = [e for e in J["events"][tag] if e["kind"] == "EXC"]
        if eps:
            mo = np.zeros_like(hw)
            for e in eps:
                a = int(round(e["t0"] * FS)); mo[a:a + int(e["dur"] * FS)] = True
            out[tag]["episodes"] = loop_table(G, mo, "OSC EPISODES pooled", line, pr)
        me = np.zeros_like(hw)
        for e in excs:
            a = int(round(e["t0"] * FS)); me[a:a + int(e["dur"] * FS)] = True
        out[tag]["excursions"] = loop_table(G, me & hw, "COMMAND EXCURSIONS pooled", line, pr)

        # per-episode openpilot block and chain contributions
        pr("  per event: kind t0 f0 | cmd/ang gain@f0 (cnt/deg) phase coh | cmd/ang gain 0.3-2 Hz | delay from phase slope 1-6 Hz (ms) | "
           "chain 4-12 Hz amp: 32sp  fb  E  P | corr(E,32sp) corr(E,-fb) | amp T_meas | rate amp (deg/s)")
        for e in sorted(eps + excs, key=lambda e: e["t0"]):
            a = int(round(e["t0"] * FS)); b = a + int(e["dur"] * FS)
            f0 = e["f_rate"] if np.isfinite(e["f_rate"]) and 3 < e["f_rate"] < 12 else (e["f_inst"] if np.isfinite(e["f_inst"]) else 7.5)
            w = slice(a, b)
            ang, cmd = G["ang"][w], G["cmd"][w]
            n = min(NPS, b - a)
            if n < 64:
                continue
            f, Pac = signal.csd(ang - ang.mean(), cmd - cmd.mean(), fs=FS, nperseg=n)
            _, Paa = signal.welch(ang - ang.mean(), fs=FS, nperseg=n)
            _, Ccc = signal.coherence(ang, cmd, fs=FS, nperseg=n)
            Hoc = Pac / Paa
            j = int(np.argmin(np.abs(f - f0)))
            lo = (f >= 0.3) & (f <= 2.0)
            g_lo = float(np.abs(Hoc[lo]).mean()) if lo.any() else np.nan
            # delay: unwrap phase 1-6 Hz where coherence > 0.8, slope -> delay
            sel = (f >= 1) & (f <= 6) & (Ccc > 0.8)
            if sel.sum() >= 3:
                ph = np.unwrap(np.angle(Hoc[sel]))
                slope = np.polyfit(f[sel], ph, 1)[0]
                delay_ms = -slope / (2 * np.pi) * 1000
            else:
                delay_ms = np.nan
            sp32 = 32 * C["sp"][w]; fb = C["fb"][w]; E = C["E"][w]; P = np.clip(C["P_raw"][w], -L.P_CLAMP, L.P_CLAMP)
            ba = lambda x: L.band_amp(x, 4, 12)  # noqa: E731
            bs, bf, bE, bP = ba(sp32), ba(fb), ba(E), ba(P)
            cE1 = float(np.corrcoef(L.bp(E, 4, 12), L.bp(sp32, 4, 12))[0, 1]) if np.std(sp32) > 0 else np.nan
            cE2 = float(np.corrcoef(L.bp(E, 4, 12), -L.bp(fb, 4, 12))[0, 1]) if np.std(fb) > 0 else np.nan
            pr("   %-3s %6.1f %5.2f | %7.1f %5.0f %4.2f | %7.1f | %6.0f | %6.0f %6.0f %6.0f %6.0f | %5.2f %5.2f | %6.0f | %5.1f" % (
                e["kind"], e["t0"], f0, np.abs(Hoc[j]), np.degrees(np.angle(Hoc[j])), Ccc[j], g_lo, delay_ms,
                bs, bf, bE, bP, cE1, cE2, e["amp_T"] if e["amp_T"] is not None else np.nan, e["amp_rate_412"] / 8))
        # time-series dump of the largest episode on r32
        if tag == "r32" and eps:
            e = max(eps, key=lambda e: e["amp_rate_412"])
            a = int(round(e["t0"] * FS)); b = a + int(e["dur"] * FS)
            pr("  TIME SERIES r32 episode t0=%.1f (every 10 ms): t  rate(wire)  rate(deg/s)  ang(deg)  cmd  T_meas  idx  32sp  fb  E  P" % e["t0"])
            for i in range(a, b, 1):
                pr("   %7.2f %6.0f %6.1f %6.2f %6.0f %6.0f %4.0f %6.0f %6.0f %6.0f %6.0f" % (
                    G["t"][i], G["rate"][i], G["rate"][i] / 8, G["ang"][i], G["cmd"][i], G["T"][i], C["idx"][i],
                    32 * C["sp"][i], C["fb"][i], C["E"][i], np.clip(C["P_raw"][i], -L.P_CLAMP, L.P_CLAMP)))
    open(os.path.join(HERE, "LANECHANGE-loop.txt"), "w", encoding="utf-8").write("\n".join(lines))
    json.dump(out, open(os.path.join(HERE, "lanechange_loop.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
