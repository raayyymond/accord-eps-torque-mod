#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""studies/osc-highangle/lanechange_chain.py -- which path carries the 7 Hz ripple into the delivered torque on the
highway lane-change episodes?  Runs the full FUN_00028ea6 mirror of analysis-2020accord/studies/v280/v280_map_profiles.py
(fb IIR at 1 kHz, sp from the map, E, P, D, sum clamp, output lag, gain 5346 / cap 3072 -- rev 3's cells: map x2, fb clamp
15360) on each episode window (+-1 s) of r32/r33, open loop on the MEASURED rate and command, and compares T_sim with the
CAN-427 tap T_meas (corr, slope, phase at f0).  Then two counterfactuals on the same frames:
   (i)  COMMAND FROZEN  -- cmd replaced by its 1 Hz low-pass (openpilot's ripple removed, the wheel's ripple kept);
   (ii) RATE FROZEN     -- the rate's 2-12 Hz band removed before the fb IIR (the inner-loop ripple removed, cmd kept).
The 4-12 Hz amplitude of T_sim under each says how much of T's ripple comes through the setpoint (openpilot) versus
through the rate feedback (EPS-internal).  Open loop: the rate is what the closed loop produced; the split is a
statement about the PATH, not about closed-loop stability.  Also: the 0x18F driver-torque ripple (the torsion bar)
amplitude and phase re the rate, since servo_at_reference.py found it ringing at 7 Hz on r31's high-angle episodes.

Second pass with the V280 rev 2 LINE map (Y = 4.3 idx, clamp 46080), because the sibling strongturn study reads r32/r33's
tap as that map, not rev 3's.  At lane-change idx (5-50) the two maps differ by < 1.8x.

V112 control: the same on r22's largest command excursions with V112's cells (map x1, clamp 7680), T_meas absent.

Run:  python lanechange_chain.py   (writes LANECHANGE-chain.txt beside itself)
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
import v280_map_profiles as V  # noqa: E402
import lanechange_osc as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS, FS1K = 100.0, 1000.0


def chain_1k(wire100, cmd100, tq100, eng100, K, fb_clamp, mapY=None):
    """the v280 chain on a window: inputs on the 100 Hz grid, returns 100 Hz-sampled T_sim and the 1 kHz internals."""
    n = len(wire100)
    tg = np.arange(n) / FS
    t1k = np.arange(0, n / FS, 1 / FS1K)
    up = lambda a: np.interp(t1k, tg, a)  # noqa: E731
    idx, sgn = V.demand(cmd100, tq100)
    idx1k = np.round(up(idx)); s = np.sign(up(sgn)); s[s == 0] = 1
    fb_un = V.feedback_1khz(-up(wire100))
    y = V.lerp(V.MAP_X, V.MAP_Y * K if mapY is None else mapY, idx1k)
    kp = V.lerp(V.KP_X, V.KP_Y, idx1k)
    sp = s * y
    fb = np.clip(fb_un, -fb_clamp, fb_clamp)
    E = 32 * sp - fb
    P = np.clip(np.floor(E * kp / 256), -V.P_CLAMP, V.P_CLAMP)
    dE = np.r_[0.0, np.diff(E)]
    D = np.clip(np.floor(dE * V.KD / 8), -V.D_CLAMP, V.D_CLAMP)
    S = np.clip(np.floor(V.SUM_MULT * (P + D) / 256), -V.SUM_CLAMP, V.SUM_CLAMP)
    eng1k = up(eng100.astype(float)) > 0.5
    S[~eng1k] = 0.0
    lag = V.output_lag(S)
    T = np.clip(np.floor(-lag * V.GAIN / 32768), -V.OUT_CAP, V.OUT_CAP)
    i100 = np.clip(np.round(tg * FS1K).astype(int), 0, len(t1k) - 1)
    return dict(T=T[i100], E=E[i100], P=P[i100], D=D[i100], fb=fb[i100], sp32=32 * sp[i100], idx=idx,
                p_rail=float(np.mean(np.abs(E * kp / 256) >= V.P_CLAMP)), fb_cl=float(np.mean(np.abs(fb_un) >= fb_clamp)),
                d_rail=float(np.mean(np.abs(dE * V.KD / 8) > V.D_CLAMP)), s_rail=float(np.mean(np.abs(V.SUM_MULT * (P + D) / 256) >= V.SUM_CLAMP)))


def phase_at(x, y, f0):
    n = min(128, len(x))
    if n < 64 or np.std(x) == 0 or np.std(y) == 0:
        return np.nan, np.nan
    f, C = signal.coherence(x, y, fs=FS, nperseg=n)
    _, P = signal.csd(x, y, fs=FS, nperseg=n)
    j = int(np.argmin(np.abs(f - f0)))
    return float(np.degrees(np.angle(P[j]))), float(C[j])


def main():
    J = json.load(open(os.path.join(HERE, "lanechange_events.json")))
    lines = []
    pr = lambda s="": (print(s), lines.append(s))  # noqa: E731
    ba = lambda x: L.band_amp(x, 4, 12)  # noqa: E731
    out = {}
    MAP_LINE = L.MAP_Y_V280R2                     # V280 rev 2 slot-7 knots (orchestrator), clamp 46080
    for tag, K, clamp, kinds, mapY in (("r32", 6.0, 46080, ("OSC",), MAP_LINE), ("r33", 6.0, 46080, ("OSC",), MAP_LINE),
                                       ("r32", 2.0, 15360, ("OSC",), None), ("r33", 2.0, 15360, ("OSC",), None),
                                       ("r22", 1.0, 7680, ("EXC",), None)):
        G = L.load(tag)
        evs = [e for e in J["events"][tag] if e["kind"] in kinds]
        if tag == "r22":
            evs = sorted(evs, key=lambda e: -e["amp_rate_412"])[:8]
        pr("=" * 130)
        pr("ROUTE %s (%s)  cells: %s, fb clamp %d, gain %d, cap %d" % (tag, L.ROUTES[tag][1], "V280 rev 2 LINE (Y 0,52,...,1032)" if mapY is not None else "map x%.0f" % K, clamp, V.GAIN, V.OUT_CAP))
        pr("  t0    f0 | rails P fb D S | T_sim vs T_meas: corr slope ph(sim re meas) | ph re rate: T_meas T_sim E cmd tq | 4-12 amp: rate(deg/s) 32sp fb E P T_sim T_meas | "
           "T_sim amp: actual  cmd-frozen  rate-frozen  (frac of actual) | tq ripple amp (raw) | damp_meas damp_sim")
        out.setdefault(tag + ('_line' if mapY is not None else ''), [])
        for e in sorted(evs, key=lambda e: e["t0"]):
            a0 = int(round(e["t0"] * FS)); b0 = a0 + int(e["dur"] * FS)
            a, b = max(a0 - 100, 0), min(b0 + 100, len(G["t"]))       # +-1 s context for the IIR/lag to settle
            wi = slice(a0 - a, a0 - a + (b0 - a0))                      # the episode inside the window
            f0 = e["f_rate"] if np.isfinite(e["f_rate"]) and 3 < e["f_rate"] < 12 else 7.5
            wire, cmd, tq, eng = G["rate"][a:b], G["cmd"][a:b], G["tq"][a:b], G["eng"][a:b]
            R = chain_1k(wire, cmd, tq, eng, K, clamp, mapY)
            cmd_fz = L.lpf(cmd, 1.0)
            Rc = chain_1k(wire, cmd_fz, tq, eng, K, clamp, mapY)
            wire_fz = wire - L.bp(wire, 2, 12)
            Rr = chain_1k(wire_fz, cmd, tq, eng, K, clamp, mapY)
            Ts, Tm = R["T"][wi], G["T"][a:b][wi]
            w, E, P, c, q = wire[wi], R["E"][wi], R["P"][wi], cmd[wi], tq[wi]
            row = dict(t0=e["t0"], f0=f0, p_rail=R["p_rail"], fb_cl=R["fb_cl"], d_rail=R["d_rail"], s_rail=R["s_rail"],
                       amp_rate=ba(w) / 8, amp_sp32=ba(R["sp32"][wi]), amp_fb=ba(R["fb"][wi]), amp_E=ba(E), amp_P=ba(P),
                       amp_Tsim=ba(Ts), amp_Tsim_cmdfz=ba(Rc["T"][wi]), amp_Tsim_ratefz=ba(Rr["T"][wi]), amp_tq=ba(q))
            row["ph_Tsim_re_rate"], _ = phase_at(w, Ts, f0)
            row["ph_E_re_rate"], _ = phase_at(w, E, f0)
            row["ph_cmd_re_rate"], _ = phase_at(w, c, f0)
            row["ph_tq_re_rate"], row["coh_tq"] = phase_at(w, q, f0)
            mt = (Ts != 0) & (w != 0)
            row["damp_sim"] = float(np.mean(np.sign(Ts[mt]) != np.sign(w[mt]))) if mt.any() else np.nan
            if tag in L.HAS_TAP:
                row["amp_Tmeas"] = ba(Tm)
                row["corr"] = float(np.corrcoef(Ts, Tm)[0, 1]) if np.std(Ts) > 0 else np.nan
                row["slope"] = float(np.sum(Ts * Tm) / max(np.sum(Ts ** 2), 1))
                row["ph_sim_re_meas"], _ = phase_at(Tm, Ts, f0)
                row["ph_Tmeas_re_rate"], _ = phase_at(w, Tm, f0)
                mm = (Tm != 0) & (w != 0)
                row["damp_meas"] = float(np.mean(np.sign(Tm[mm]) != np.sign(w[mm]))) if mm.any() else np.nan
            else:
                for k in ("amp_Tmeas", "corr", "slope", "ph_sim_re_meas", "ph_Tmeas_re_rate", "damp_meas"):
                    row[k] = np.nan
            out[tag + ('_line' if mapY is not None else '')].append(row)
            pr("  %6.1f %5.2f | %4.2f %4.2f %4.2f %4.2f | %5.2f %5.2f %5.0f | %5.0f %5.0f %5.0f %5.0f %5.0f (coh %.2f) | %5.1f %5.0f %5.0f %5.0f %5.0f %5.0f %5.0f | %5.0f %5.0f (%.2f) %5.0f (%.2f) | %5.0f | %4.2f %4.2f" % (
                row["t0"], f0, row["p_rail"], row["fb_cl"], row["d_rail"], row["s_rail"], row["corr"], row["slope"], row["ph_sim_re_meas"],
                row["ph_Tmeas_re_rate"], row["ph_Tsim_re_rate"], row["ph_E_re_rate"], row["ph_cmd_re_rate"], row["ph_tq_re_rate"], row["coh_tq"],
                row["amp_rate"], row["amp_sp32"], row["amp_fb"], row["amp_E"], row["amp_P"], row["amp_Tsim"], row["amp_Tmeas"],
                row["amp_Tsim"], row["amp_Tsim_cmdfz"], row["amp_Tsim_cmdfz"] / max(row["amp_Tsim"], 1e-9),
                row["amp_Tsim_ratefz"], row["amp_Tsim_ratefz"] / max(row["amp_Tsim"], 1e-9), row["amp_tq"], row["damp_meas"], row["damp_sim"]))
    open(os.path.join(HERE, "LANECHANGE-chain.txt"), "w", encoding="utf-8").write("\n".join(lines))
    json.dump(out, open(os.path.join(HERE, "lanechange_chain.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
