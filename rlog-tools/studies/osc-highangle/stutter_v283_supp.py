# -*- coding: utf-8 -*-
"""studies/osc-highangle/stutter_v283_supp.py -- the supplements to stutter_v283.py.

S1  THE Ki VALIDATION ON THE WIRE.  stutter_v283.py's A2 scored Ki by raw rms residual, which is biased
    toward whichever sim is SMALLEST.  The clean test is a DIFFERENCE regression: regress
    (T_meas - T_sim[Ki=0]) on (T_sim[Ki] - T_sim[Ki=0]).  If that Ki is live, the slope is ~1 and the
    correlation is high; if Ki is 0 on the car, the slope is ~0.  r35 (Ki 0) is the negative control.
S2  the STALL runs with GAP MERGING (r35's 7-run table bridges short gaps; stutter_v283.py's D1 does not)
S3  prereg (d) STALL-RELEASE OVERSHOOT with a command-stability guard (the raw statistic reads a command
    that simply stopped as a huge "overshoot")
S4  a mechanism-free proxy for the felt STUTTER in strong turns: wheel-rate sign reversals per second,
    p95 |d(rate)/dt|, and the tap's own reversal rate -- r35 vs r36/r37/r38
S5  the tap's saturation / near-cap behaviour in strong turns (the sum clamp and the 2462 output cap on
    the WIRE, not in the model)

Run: python stutter_v283_supp.py     Subagent stutter283, 2026-09-03.
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stutter_v283 as SV  # noqa: E402

V = SV.V
FS = SV.FS
CPD = SV.CPD
ROUTES = SV.ROUTES
KI_ONCAR = SV.KI_ONCAR


def merge_runs(mask, gap, nmin):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    rr = list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))
    out = []
    for a, b in rr:
        if out and a - out[-1][1] <= gap:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return [(a, b) for a, b in out if b - a >= nmin]


def main():
    L = []

    def pr(s=""):
        print(s, flush=True)
        L.append(s)

    routes, SIM = {}, {}
    for tag in ROUTES:
        print("loading %s ..." % tag, flush=True)
        routes[tag] = V.Route(tag)
    KIS = (0, 5, 20, 50, 100, 200)
    for tag in ROUTES:
        SIM[tag] = {ki: SV.sim_ki(routes[tag], *SV.V280R2, kpY=SV.KP_FLAT["flat 248"], ki=ki) for ki in KIS}
        print("  simulated %s" % tag, flush=True)

    pr("=" * 175)
    pr("stutter_v283_supp -- Ki validation on the wire, and the refined pre-registered counts.  Subagent stutter283, 2026-09-03")
    pr("=" * 175)

    # ------------------------------------------------------------------------------------------- S1
    pr("\nS1 -- DID Ki ACT ON THE WIRE?  Difference regression: y = T_meas - T_sim[Ki=0]  vs  x = T_sim[Ki] - T_sim[Ki=0].")
    pr("   If that Ki is the flown value the slope is ~1 with a high corr.  r35 (Ki 0 on the car) is the NEGATIVE CONTROL -- it must read ~0.")
    pr("   Frames: engaged, idx > 0 (all), and the I-authority stratum (idx 20-120, |angle| > 10) where the integrator carries load.")
    for tag in ROUTES:
        r = routes[tag]
        Tm = r.T_meas
        T0 = SIM[tag][0]["T"][r.i100]
        for lab, m in (("ALL ENGAGED  ", r.eng & (r.idx > 0)),
                       ("I-AUTHORITY  ", r.eng & (r.idx >= 20) & (r.idx <= 120) & (np.abs(r.ang) > 10)),
                       ("STRONG TURNS ", r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx <= 200) & (np.abs(r.tq_raw) < 1216))):
            y = Tm[m] - T0[m]
            cells = []
            for ki in KIS[1:]:
                x = SIM[tag][ki]["T"][r.i100][m] - T0[m]
                if np.sum(x * x) < 1e-6:
                    cells.append("Ki%3d --" % ki)
                    continue
                sl = float(np.sum(x * y) / np.sum(x * x))
                cc = float(np.corrcoef(x, y)[0, 1])
                cells.append("Ki%3d slope %+.2f corr %+.2f" % (ki, sl, cc))
            pr("  %s %s n %6d: %s" % (tag, lab, m.sum(), "  ".join(cells)))
        pr("")

    # ------------------------------------------------------------------------------------------- S2
    pr("S2 -- prereg (a) STALL RUNS with gap merging (bridge gaps <= 0.3 s), the framing behind r35's '7 runs / 14.8 s'.")
    pr("   Mask: engaged, |angle| >= 30, idx 40-200, |tq| < 1216, rate/ref < 0.5 through the ON-CAR chain.  Prediction: <= 2 runs, none > 1.5 s.")
    for tag in ROUTES:
        r = routes[tag]
        R = SIM[tag][KI_ONCAR[tag]]
        ref = R["ref_deg"][r.i100]
        w = np.abs(r.wire) / CPD
        elig = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx <= 200) & (np.abs(r.tq_raw) < 1216)
        st = elig & (ref > 5) & (w < 0.5 * ref)
        for gap, nmin, lab in ((30, 100, "gap 0.3 s, runs >= 1.0 s"), (30, 50, "gap 0.3 s, runs >= 0.5 s"), (50, 100, "gap 0.5 s, runs >= 1.0 s")):
            rr = merge_runs(st, gap, nmin)
            pr("  %s %-26s: %2d runs (%5.1f s); longest %.1f s | eligible %.1f s; stalled frames %.1f s = %.3f of eligible"
               % (tag, lab, len(rr), sum(b - a for a, b in rr) / FS, max([(b - a) / FS for a, b in rr] or [0]), elig.sum() / FS, st.sum() / FS, st.sum() / max(elig.sum(), 1)))
        for a, b in merge_runs(st, 30, 100):
            i = r.i100[a:b]
            pr("       t0 %6.1f dur %3.1f ang %4.0f v %4.1f idx %3.0f | rate %4.1f ref %5.1f (%.2f) | |T| %4.0f | mod |I| %5.0f |P| %5.0f | tq %4.0f | 6-8.5 Hz %.1f deg/s"
               % (a / FS, (b - a) / FS, np.median(np.abs(r.ang[a:b])), r.vego[a:b].mean(), np.median(r.idx[a:b]), np.median(w[a:b]), np.median(ref[a:b]),
                  np.median(w[a:b]) / max(np.median(ref[a:b]), 1e-9), np.median(np.abs(r.T_meas[a:b])), np.median(np.abs(R["I"][i])), np.median(np.abs(R["P_raw"][i])),
                  np.median(np.abs(r.tq_raw[a:b])), SV.ST.band_amp(r.wire[a:b]) / CPD if b - a >= 40 else np.nan))

    # ------------------------------------------------------------------------------------------- S3
    pr("\nS3 -- prereg (d) STALL-RELEASE OVERSHOOT with a COMMAND-STABILITY GUARD: the 2.5 s after a stall ends only counts if the")
    pr("   demand index stays within 50 %% of its in-stall median and the car stays engaged (otherwise a command that simply STOPPED reads as an 'overshoot').")
    for tag in ROUTES:
        r = routes[tag]
        R = SIM[tag][KI_ONCAR[tag]]
        ref = R["ref_deg"][r.i100]
        w = np.abs(r.wire) / CPD
        st = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx <= 200) & (np.abs(r.tq_raw) < 1216) & (ref > 5) & (w < 0.5 * ref)
        rows, rej = [], 0
        for a, b in merge_runs(st, 30, 50):
            e2 = min(b + 250, len(w))
            if e2 - b < 50 or not r.eng[b:e2].all():
                rej += 1
                continue
            i0 = np.median(r.idx[a:b])
            if np.median(r.idx[b:e2]) < 0.5 * i0:
                rej += 1
                continue
            over = w[b:e2] - ref[b:e2]
            rows.append((a / FS, (b - a) / FS, float(over.max()), float(np.sum(over > 0) / FS), float(np.median(r.idx[b:e2])), i0))
        if rows:
            pr("  %s: %d qualifying releases (%d rejected: disengaged or command dropped) | peak over-reference p50 %+.1f p90 %+.1f max %+.1f deg/s | time above ref p50 %.2f p90 %.2f s"
               % (tag, len(rows), rej, np.median([x[2] for x in rows]), np.percentile([x[2] for x in rows], 90), max(x[2] for x in rows),
                  np.median([x[3] for x in rows]), np.percentile([x[3] for x in rows], 90)))
            for x in sorted(rows, key=lambda z: -z[2])[:4]:
                pr("       t0 %6.1f stall %3.1f s -> peak +%.1f deg/s over ref for %.2f s (idx %3.0f in stall -> %3.0f after)" % (x[0], x[1], x[2], x[3], x[5], x[4]))
        else:
            pr("  %s: no qualifying stall releases (%d rejected)" % (tag, rej))

    # ------------------------------------------------------------------------------------------- S4
    pr("\nS4 -- a MECHANISM-FREE proxy for the felt STUTTER in strong turns (engaged, |angle| >= 30, v <= 10, runs >= 1 s).")
    pr("   'reversals' = wheel-rate sign changes per second on the 2-15 Hz band-passed rate; 'jerk p95' = 95th pct |d(rate)/dt| deg/s^2;")
    pr("   'tap rev' = the same on the 427 tap.  A stutter the driver feels is a repeated stop/go, so it shows up as reversals + jerk, not as a band alone.")
    for tag in ROUTES:
        r = routes[tag]
        for lab, m in (("strong ALL", r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10)),
                       ("strong hands-light idx>=40", r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10) & (np.abs(r.tq_raw) < 1216) & (r.idx >= 40)),
                       ("strong hands-on >=1216", r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10) & (np.abs(r.tq_raw) >= 1216))):
            runs = V.runs(m, 100)
            if runs.sum() < 200:
                pr("  %s %-28s: %.1f s -- too short" % (tag, lab, runs.sum() / FS))
                continue
            sos = signal.butter(4, [2.0, 15.0], btype="bandpass", fs=FS, output="sos")
            rb = signal.sosfiltfilt(sos, r.wire)[runs] / CPD
            tb = signal.sosfiltfilt(sos, r.T_meas)[runs]
            jerk = np.abs(np.diff(r.wire[runs] / CPD)) * FS
            pr("  %s %-28s %6.1f s | reversals %5.2f /s | jerk p95 %6.0f deg/s^2 p99 %6.0f | tap rev %5.2f /s | rate |x| p50 %5.1f deg/s | band rms %.2f deg/s"
               % (tag, lab, runs.sum() / FS, float(np.mean(np.diff(np.sign(rb)) != 0) * FS), float(np.percentile(jerk, 95)), float(np.percentile(jerk, 99)),
                  float(np.mean(np.diff(np.sign(tb)) != 0) * FS), float(np.median(np.abs(r.wire[runs]) / CPD)), float(rb.std())))

    # ------------------------------------------------------------------------------------------- S5
    pr("\nS5 -- the TAP's own saturation behaviour in strong turns (WIRE, not model).  |T| >= 2400 is within one LSB of the 2462/2472 cap region.")
    for tag in ROUTES:
        r = routes[tag]
        for lab, m in (("strong hands-light", r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx <= 200) & (np.abs(r.tq_raw) < 1216)),
                       ("strong hands-on", r.eng & (np.abs(r.ang) >= 30) & (np.abs(r.tq_raw) >= 2240)),
                       ("all engaged", r.eng)):
            if m.sum() < 100:
                continue
            T = np.abs(r.T_meas[m])
            pr("  %s %-20s n %6d: |T| p50 %4.0f p90 %4.0f p99 %4.0f max %4.0f | P(|T|>=1600) %.4f P(>=2000) %.4f P(>=2400) %.4f"
               % (tag, lab, m.sum(), np.median(T), np.percentile(T, 90), np.percentile(T, 99), T.max(),
                  float(np.mean(T >= 1600)), float(np.mean(T >= 2000)), float(np.mean(T >= 2400))))
        pr("")

    out = os.path.join(HERE, "_scratch", "stutter_v283_supp.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
