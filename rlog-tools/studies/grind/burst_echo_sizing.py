# -*- coding: utf-8 -*-
"""studies/grind/burst_echo_sizing.py -- SIZE THE PHASE-LOCKED ECHO.  Subagent `slewburst`, 2026-09-10.
ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing on any bus.

Follow-up to BURST-ONSET-TRIGGERS-2026-09-10.md.  That report closed the TRIGGER question (no discrete
command event class accounts for more than ~13 % of burst onsets) and showed that a Q ~ 17 resonance
buys ring LENGTH, not amplitude -- a single capped command frame delivers 4.4-6.8 counts in the ring
band against 57-128 measured.  It also identified the one regime that is NOT closed by that argument:
a SUSTAINED, PHASE-LOCKED echo at f0, whose analytic accumulation ceiling is 1/(1-exp(-2*pi*zeta)) = 6.0.

`oplpf` supplies the candidate mechanism [its EVIDENCE, latcontrol_torque.py:236-237 <- carstate.py:187]:
openpilot's lateral measurement is the CAN 0x14A steering angle, 100 Hz, 0.1 deg/LSB, UNFILTERED,
reaching the command through P only (k_d = 0, k_p = 0.6).  One 0.1 deg LSB propagates to 13.2 raw 0xE4
counts at 5 m/s, 20.6 at 15, 52.8 at 30.  The measured 20 Hz command line is 15-40 counts.

Sections
  E1  DELIVERY   byte-exact 1 kHz mirror driven by a sustained sinusoidal command at the route's own f0,
                 amplitude swept over the realistic echo range -- how many counts land IN THE RING BAND?
  E2  PHASE      is the delivered in-band amplitude phase-dependent (it should not be -- the setpoint
                 path is open loop in the mirror); what phase actually decides; and the MEASURED
                 0x14A-angle -> 0xE4-command cross-phase at f0 on the wire.
  E3  WIRE GAIN  the measured 0xE4 counts per degree of steering angle AT f0, in the same episode
                 windows, per speed bin, against oplpf's predicted 132 / 206 / 528 counts/deg.
  E4  THRESHOLD  the detector threshold sweep I did not run -- does the trigger null survive a detector
                 that also catches half-amplitude episodes, and do the two r39 bookmarks come in?

Run: python rlog-tools/studies/grind/burst_echo_sizing.py
Writes _scratch/burst_echo_sizing.txt beside it.
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import burst_onset_triggers as B              # noqa: E402  (loader, detector, hazard, all reused verbatim)
import creep20_loop_id as C20                 # noqa: E402
import grind_incident_r35 as GI               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K = 100.0, 1000.0
RNG = np.random.default_rng(20260910)
OUT = []

# oplpf's predicted P-path gain: raw 0xE4 counts per 0.1 deg LSB, by speed
OPLPF = {5.0: 13.2, 15.0: 20.6, 30.0: 52.8}
AMPS = [13.2, 15.0, 20.0, 20.6, 25.0, 30.0, 40.0, 52.8]


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def band_amp(x, lo, hi, fs):
    """steady-state amplitude of the in-band content = sqrt(2) x rms of the band-passed signal."""
    sos = signal.butter(4, [lo, hi], btype="bandpass", fs=fs, output="sos")
    y = signal.sosfiltfilt(sos, x)
    return float(np.sqrt(2.0) * np.sqrt(np.mean(y ** 2)))


def loud_windows(g, n=10, half=150):
    """the loudest engaged 3 s windows, centred on the biggest burst peaks."""
    out = []
    for p0 in g["pk"][np.argsort(g["amp"])[::-1]]:
        a0, b0 = p0 - half, p0 + half
        if a0 < 60 or b0 > len(g["t"]) - 20 or not g["eng"][a0:b0].all():
            continue
        out.append((a0, b0, p0))
        if len(out) >= n:
            break
    return out


# ======================================================================================================
# E1  DELIVERY -- what a sustained phase-locked echo actually lands on the plant
# ======================================================================================================
def sectionE1(G):
    pr("=" * 118)
    pr("E1  DELIVERY -- byte-exact 1 kHz mirror, sustained sinusoidal command at f0, amplitude swept")
    pr("=" * 118)
    pr("The command is replaced by cmd(t) + A*sin(2*pi*f0*t); every other input -- the measured wire")
    pr("rate, the driver-torque bar, the engagement, every calibration cell -- is exactly as measured,")
    pr("read from that build's own image.  dT = T(with echo) - T(as measured); the number reported is")
    pr("the STEADY-STATE in-band amplitude sqrt(2)*rms of dT band-passed to the route's ring band, the")
    pr("SAME measure used for the capped-step row (4.4-6.8) and for T_band (57-128) in the first report.")
    pr("10 loudest 3 s engaged windows per route; median across windows, with the inter-window spread.")
    pr("")
    res = {}
    for tag in ("r39", "r5e_v288", "r63_v289"):
        g = G[tag]
        lo, hi = B.BAND[tag]
        f0 = g["f0"]
        wins = loud_windows(g)
        pr("--- %s (%s), f0 %.2f Hz, band %.0f-%.0f Hz, %d windows ---" % (tag, B.BUILD[tag], f0, lo, hi, len(wins)))
        pr("  %8s %10s %10s %12s %12s %14s" %
           ("A (raw)", "dT_band", "p25-p75", "T_band(meas)", "ratio", "speed p50 (m/s)"))
        base, vmed = [], []
        for a0, b0, p0 in wins:
            S0 = GI.simulate(g, a0, b0, g["cells"])
            base.append(band_amp(S0["T"], lo, hi, FS1K))
            vmed.append(float(np.median(g["vego"][a0:b0])))
        T0 = float(np.median(base))
        res[tag] = dict(T0=T0, rows=[], f0=f0, v=float(np.median(vmed)))
        for A in AMPS:
            vals = []
            for a0, b0, p0 in wins:
                g2 = dict(g)
                t = g["t"][:len(g["cmd"])]
                g2["cmd"] = g["cmd"] + A * np.sin(2 * np.pi * f0 * (t - t[a0]))
                S0 = GI.simulate(g, a0, b0, g["cells"])
                S1 = GI.simulate(g2, a0, b0, g["cells"])
                vals.append(band_amp(S1["T"] - S0["T"], lo, hi, FS1K))
            v = np.array(vals)
            res[tag]["rows"].append((A, float(np.median(v)), float(np.percentile(v, 25)),
                                     float(np.percentile(v, 75))))
            pr("  %8.1f %10.2f %10s %12.1f %12.3f %14.1f" %
               (A, np.median(v), "%.1f-%.1f" % (np.percentile(v, 25), np.percentile(v, 75)),
                T0, np.median(v) / T0, np.median(vmed)))
        pr("")
    pr("READING THE RATIO COLUMN: it is the fraction of the MEASURED ring that a sustained echo of that")
    pr("amplitude delivers DIRECTLY, before any resonant accumulation.  The accumulation ceiling for a")
    pr("perfectly phase-locked drive at f0 is 1/(1-exp(-2*pi*zeta)) = 6.00 at zeta = 0.029, so the")
    pr("largest ring such an echo could sustain is 6.00 x the ratio.  A ratio x 6.00 >= 1 means the")
    pr("echo CAN account for the measured ring; < 1 means it cannot, and by how much it falls short.")
    pr("")
    pr("%-10s %8s %10s %12s %12s %14s %s" %
       ("route", "A", "dT_band", "T_band", "ratio", "x6.0 ceiling", "verdict"))
    pr("-" * 118)
    for tag, d in res.items():
        for A, m, q1, q3 in d["rows"]:
            if A not in (13.2, 20.6, 40.0, 52.8):
                continue
            r = m / d["T0"]
            pr("%-10s %8.1f %10.2f %12.1f %12.3f %14.2f %s" %
               (tag, A, m, d["T0"], r, 6.0 * r,
                "SUFFICIENT" if 6.0 * r >= 1.0 else "short by x%.1f" % (1.0 / (6.0 * r))))
    pr("")
    return res


# ======================================================================================================
# E2  PHASE
# ======================================================================================================
def sectionE2(G, res):
    pr("=" * 118)
    pr("E2  PHASE -- what it does and does not control, and what the wire says the real phase is")
    pr("=" * 118)
    pr("E2a  Is the DELIVERED in-band amplitude phase-dependent?  It should not be: in the mirror the")
    pr("     setpoint path cmd -> idx -> map -> E -> P/D -> T is driven open loop (the feedback is the")
    pr("     MEASURED wire rate, which the injection cannot move).  Any phase dependence would be the")
    pr("     quantiser and the map LERP knots, i.e. a genuine nonlinearity, and is worth knowing.")
    pr("     A = 20.6 raw (oplpf's 15 m/s LSB), phase swept over one cycle.")
    pr("")
    pr("%-10s %s" % ("route", "  ".join("%6.0f deg" % p for p in range(0, 360, 45))))
    pr("-" * 118)
    for tag in ("r39", "r63_v289"):
        g = G[tag]
        lo, hi = B.BAND[tag]
        f0 = g["f0"]
        wins = loud_windows(g, n=6)
        row = []
        for ph in range(0, 360, 45):
            vals = []
            for a0, b0, p0 in wins:
                g2 = dict(g)
                t = g["t"][:len(g["cmd"])]
                g2["cmd"] = g["cmd"] + 20.6 * np.sin(2 * np.pi * f0 * (t - t[a0]) + np.radians(ph))
                S0 = GI.simulate(g, a0, b0, g["cells"])
                S1 = GI.simulate(g2, a0, b0, g["cells"])
                vals.append(band_amp(S1["T"] - S0["T"], lo, hi, FS1K))
            row.append(np.median(vals))
        pr("%-10s %s   (spread %.1f %% of mean)" %
           (tag, "  ".join("%10.2f" % v for v in row), 100 * (max(row) - min(row)) / np.mean(row)))
    pr("")
    pr("E2b  WHAT PHASE ACTUALLY DECIDES.  Phase does not change how much in-band torque the echo")
    pr("     DELIVERS; it decides whether that torque DE-DAMPS the mode, damps it, or only shifts its")
    pr("     frequency.  For a modal coordinate driven by a feedback torque of return-ratio magnitude")
    pr("     |L| at f0 and phase psi measured against the RING VELOCITY:")
    pr("        d(zeta) = -(|L|/2) * cos(psi)      psi = 0   -> pure de-damping (worst case)")
    pr("                                           psi = 90  -> pure frequency shift, no damping change")
    pr("                                           psi = 180 -> pure damping")
    pr("     The 6.00 accumulation ceiling in E1 assumes psi = 0 exactly.  At psi it is 6.00*|cos(psi)|,")
    pr("     to first order, so the ceiling is generous everywhere except psi ~ 0.")
    pr("     Ceiling vs psi:  " + "  ".join("%d deg: %.2f" % (p, 6.0 * abs(np.cos(np.radians(p))))
                                            for p in (0, 30, 45, 60, 90)))
    pr("")
    pr("E2c  THE MEASURED PHASE ON THE WIRE -- 0x14A steering angle -> 0xE4 command, at f0, inside the")
    pr("     loud grinding windows.  This is openpilot's OWN round trip (sensor -> P -> command); it is")
    pr("     NOT the full return ratio, because the command->torque->plant->angle leg is not included.")
    pr("     Reported with the coherence, so a low-coherence phase can be discarded rather than believed.")
    pr("")
    pr("%-10s %10s %12s %12s %12s" % ("route", "f0", "coherence", "phase deg", "implied lag ms"))
    pr("-" * 118)
    for tag, g in G.items():
        lo, hi = B.BAND[tag]
        f0 = g["f0"]
        wins = loud_windows(g, n=10)
        num = den1 = den2 = 0.0
        for a0, b0, p0 in wins:
            a = g["ang"][a0:b0] - np.mean(g["ang"][a0:b0])
            c = g["cmd"][a0:b0] - np.mean(g["cmd"][a0:b0])
            f, P = signal.csd(a, c, fs=FS, nperseg=128, detrend="constant")
            _, Pa = signal.welch(a, fs=FS, nperseg=128, detrend="constant")
            _, Pc = signal.welch(c, fs=FS, nperseg=128, detrend="constant")
            j = int(np.argmin(np.abs(f - f0)))
            num += P[j]; den1 += Pa[j]; den2 += Pc[j]
        coh = np.abs(num) ** 2 / (np.real(den1) * np.real(den2))
        ph = np.degrees(np.angle(num))
        pr("%-10s %10.2f %12.3f %12.1f %12.1f" % (tag, f0, coh, ph, -ph / 360.0 / f0 * 1000.0))
    pr("")


# ======================================================================================================
# E3  WIRE GAIN -- measured counts per degree at f0
# ======================================================================================================
def sectionE3(G):
    pr("=" * 118)
    pr("E3  WIRE GAIN -- measured 0xE4 counts per DEGREE of steering angle at f0, vs oplpf's prediction")
    pr("=" * 118)
    pr("0x14A carries the angle at 0.1 deg/LSB (extractor: ang = i16be(d,0) * -0.1, so `ang` is DEGREES).")
    pr("oplpf's predicted P-path gain, converted to counts per DEGREE (x10 its per-LSB figure):")
    pr("     5 m/s -> 132 counts/deg     15 m/s -> 206 counts/deg     30 m/s -> 528 counts/deg")
    pr("Measured here as |CMD(f0)| / |ANG(f0)| in 2 s engaged windows, using the cross-spectrum so a")
    pr("window with no coherent line contributes nothing; windows gated on coherence >= 0.3 at f0.")
    pr("")
    pr("%-10s %-12s %7s %10s %12s %12s %12s %10s" %
       ("route", "speed bin", "n_win", "coh p50", "meas c/deg", "IQR", "predicted", "meas/pred"))
    pr("-" * 118)
    VB = [(0, 8, 5.0), (8, 22, 15.0), (22, 100, 30.0)]
    for tag, g in G.items():
        lo, hi = B.BAND[tag]
        f0 = g["f0"]
        W = 200
        rows = {k: [] for k in range(3)}
        for a, b in g["runs"]:
            for s in range(a, b - W + 1, W // 2):
                e = s + W
                v = float(np.median(g["vego"][s:e]))
                k = next((i for i, (v0, v1, _) in enumerate(VB) if v0 <= v < v1), None)
                if k is None:
                    continue
                aa = g["ang"][s:e] - np.mean(g["ang"][s:e])
                cc = g["cmd"][s:e] - np.mean(g["cmd"][s:e])
                f, P = signal.csd(aa, cc, fs=FS, nperseg=128, detrend="constant")
                _, Pa = signal.welch(aa, fs=FS, nperseg=128, detrend="constant")
                _, Pc = signal.welch(cc, fs=FS, nperseg=128, detrend="constant")
                j = int(np.argmin(np.abs(f - f0)))
                coh = np.abs(P[j]) ** 2 / (np.real(Pa[j]) * np.real(Pc[j]) + 1e-30)
                if coh < 0.3 or np.real(Pa[j]) <= 0:
                    continue
                rows[k].append((np.sqrt(np.real(Pc[j]) / np.real(Pa[j])), coh))
        for k, (v0, v1, vn) in enumerate(VB):
            r = rows[k]
            if len(r) < 5:
                pr("%-10s %-12s %7d  (too few windows)" % (tag, "%d-%d m/s" % (v0, v1), len(r)))
                continue
            gains = np.array([x[0] for x in r]); cohs = np.array([x[1] for x in r])
            pred = OPLPF[vn] * 10.0
            pr("%-10s %-12s %7d %10.2f %12.1f %12s %12.0f %10.2f" %
               (tag, "%d-%d m/s" % (v0, v1), len(r), np.median(cohs), np.median(gains),
                "%.0f-%.0f" % (np.percentile(gains, 25), np.percentile(gains, 75)), pred,
                np.median(gains) / pred))
    pr("")


# ======================================================================================================
# E4  THRESHOLD SWEEP -- does the trigger null survive a detector that catches quiet episodes?
# ======================================================================================================
def sectionE4(G):
    pr("=" * 118)
    pr("E4  DETECTOR THRESHOLD SWEEP -- the one I did not run, and the r39 bookmarks")
    pr("=" * 118)
    pr("The first report's detector required a peak above max(50 raw, p90 of the engaged envelope).  On")
    pr("r39 that resolved to 95 raw, and the operator's TWO r39 bookmarks (envelope p90 62 and 36 there)")
    pr("produced no onset.  If his percept extends to half-amplitude episodes, the onset set is biased")
    pr("toward loud bursts and the trigger bounds may be tighter than the symptom.  Swept below.")
    pr("")
    pr("%-10s %8s %8s %8s %8s %10s %14s" %
       ("route", "hi_abs", "hi_q", "thr", "N_ons", "ons/min", "r39 marks hit"))
    pr("-" * 118)
    SW = [(50.0, 0.90), (40.0, 0.85), (30.0, 0.80), (25.0, 0.75), (20.0, 0.70)]
    sets = {}
    for tag, g in G.items():
        for ha, hq in SW:
            on, pk, amp, thi, tlo = B.find_onsets(g["env"], g["eng"], hi_q=hq, hi_abs=ha)
            sets[(tag, ha, hq)] = on
            hit = ""
            if tag == "r39":
                ot = g["tr"][on]
                hit = " ".join("%+.2f" % (ot[np.argmin(np.abs(ot - m))] - m) if len(ot) else "none"
                               for m in B.marks_of("r39"))
            pr("%-10s %8.0f %8.2f %8.0f %8d %10.2f %14s" %
               (tag, ha, hq, thi, len(on), 60 * len(on) / g["eng_s"], hit))
        pr("")
    pr("POOLED cap-bind hazard and attributable fraction at each threshold -- does the null hold?")
    pr("%-10s %8s %8s %8s %9s %8s %-17s %s" %
       ("hi_abs", "hi_q", "n_on", "n_in", "expected", "RR", "  95% CI", "f_trig [95% CI]"))
    pr("-" * 118)
    for ha, hq in SW:
        tot_in = tot_exp = tot_on = 0
        parts = []
        for tag, g in G.items():
            on = sets[(tag, ha, hq)]
            if len(on) == 0:
                continue
            m = B._window_mask(len(g["t"]), g["ev"]["cap_bind"], 0, 12) & g["eng"]
            cov = m.sum() / max(1, g["eng"].sum())
            tot_in += int(m[on].sum()); tot_exp += cov * len(on); tot_on += len(on)
            parts.append((m, on, cov))
        rr = tot_in / tot_exp
        bs = np.empty(3000)
        for s in range(3000):
            a = e = 0.0
            for m, on, cov in parts:
                j = RNG.integers(0, len(on), len(on))
                a += m[on[j]].sum(); e += cov * len(on)
            bs[s] = a / e
        c = tot_exp / tot_on
        f = lambda R: max(0.0, c * (R - 1.0) / (1.0 - c))            # noqa: E731
        q1, q3 = np.percentile(bs, 2.5), np.percentile(bs, 97.5)
        pr("%10.0f %8.2f %8d %8d %9.1f %8.2f  [%5.2f,%5.2f] %.3f [%.3f,%.3f]" %
           (ha, hq, tot_on, tot_in, tot_exp, rr, q1, q3, f(rr), f(q1), f(q3)))
    pr("")


# ======================================================================================================
# E5  THE ON-CAR TEST THAT ALREADY EXISTS -- V288 rev 2 flew this exact lever
# ======================================================================================================
def sectionE5(G, res):
    pr("=" * 118)
    pr("E5  🛑 THE ECHO LEVER HAS ALREADY BEEN FLOWN, AND IT RETURNED A NULL -- V288 rev 2")
    pr("=" * 118)
    pr("docs/BUILD-LINEAGE.md:341-348: V288 rev 2 is a *reference pre-filter*, 'the first build V38->V288")
    pr("to touch the reference the LKAS rate PID compares against'.  First-order, corner 10.3 Hz at")
    pr("1 kHz, DC gain exactly 1 (y += (x-y)>>4).  A command echo enters exactly there: cmd -> idx ->")
    pr("map -> setpoint, and the pre-filter is on that setpoint.  So V288 IS a direct on-car test of")
    pr("the echo lever, flown, on route r5e_v288.")
    pr("")
    a = 1.0 / 16.0
    for f0 in (20.0, 16.5):
        w = 2 * np.pi * f0 / FS1K
        H = a / abs(1 - (1 - a) * np.exp(-1j * w))
        pr("  |H(%.1f Hz)| of y += (x-y)>>4 at 1 kHz = %.4f  => the echo's drive is cut x%.2f (%.1f dB)"
           % (f0, H, 1 / H, 20 * np.log10(H)))
    H20 = a / abs(1 - (1 - a) * np.exp(-1j * 2 * np.pi * 20.0 / FS1K))
    pr("")
    pr("  What that predicts, read off the E1 sweep by re-running the mirror at the ATTENUATED amplitude")
    pr("  (exact for this purpose: the perturbation is what the pre-filter scales):")
    pr("")
    pr("  %-10s %8s %10s %10s %12s %14s %14s" %
       ("route", "A", "A x |H|", "dT_band", "ratio", "x6.0 ceiling", "vs unfiltered"))
    pr("  " + "-" * 112)
    for tag in ("r39",):
        g = G[tag]
        lo, hi = B.BAND[tag]
        f0 = g["f0"]
        wins = loud_windows(g)
        T0 = res[tag]["T0"]
        for A in (20.6, 40.0):
            Ae = A * H20
            vals = []
            for a0, b0, p0 in wins:
                g2 = dict(g)
                t = g["t"][:len(g["cmd"])]
                g2["cmd"] = g["cmd"] + Ae * np.sin(2 * np.pi * f0 * (t - t[a0]))
                S0 = GI.simulate(g, a0, b0, g["cells"])
                S1 = GI.simulate(g2, a0, b0, g["cells"])
                vals.append(band_amp(S1["T"] - S0["T"], lo, hi, FS1K))
            m = float(np.median(vals))
            base = [r for r in res[tag]["rows"] if r[0] == A][0][1]
            pr("  %-10s %8.1f %10.1f %10.2f %12.3f %14.2f %14s" %
               (tag, A, Ae, m, m / T0, 6.0 * m / T0, "x%.2f" % (m / base)))
    pr("")
    pr("  PREDICTION UNDER THE ECHO HYPOTHESIS: V288 should have taken the echo's sustaining capacity")
    pr("  from just-above-unity to well below it, i.e. the 20 Hz ring should have collapsed or dropped")
    pr("  markedly.  WHAT V288 rev 2 ACTUALLY DID ON THE CAR (r5e_v288, the census reproduced exactly")
    pr("  from the V282 pipeline -- GRIND1-CENSUS-V288-R5E-2026-09-08.md, quoted in STATE):")
    pr("     same 20.0-20.4 Hz line at all three operator bookmarks (mark 3 LOUDER than any V282 episode)")
    pr("     258 vs 239 episodes/h · envelope p50 126 vs 127 · f 20.06 vs 20.03 Hz")
    pr("     rung-bell ratio 2.41 vs 2.25 · no new line above 22 Hz · D-clamp bind duty x0.03")
    pr("  => EVERY ring statistic unchanged, while the cave demonstrably ran (b4.5 live on 99.5 % of")
    pr("     engaged frames).  The echo cannot be the DOMINANT sustaining leg.  [EVIDENCE, on-car]")
    pr("")
    pr("  🛑 THIS ON-CAR NULL OUTRANKS MY OFFLINE SIZING.  E1 says a sustained echo of the measured")
    pr("  amplitude is ARITHMETICALLY capable of sustaining the ring; E5 says that when the capability")
    pr("  was actually removed on the car, nothing happened.  A contributing leg of a few tens of")
    pr("  percent is not excluded -- V288 would have predicted only a modest change, inside the noise")
    pr("  of that comparison -- but the dominant-cause reading is falsified by a flown build.")
    pr("")
    pr("  ⚠ AND THE LIMITATION THAT CUTS THE OTHER WAY, stated plainly: GI.simulate is the V282-era")
    pr("  chain mirror.  It reads each build's own calibration cells from that build's image, but it")
    pr("  does NOT implement V288's pre-filter cave or V289's notch cave.  So the r5e_v288 and")
    pr("  r63_v289 rows in E1 are 'the V282 chain arithmetic carrying those builds' cal bytes', and")
    pr("  they OVERSTATE delivery for both -- by x%.2f for V288 at 20 Hz, and by an unquantified amount"
       % (1 / H20))
    pr("  for V289 (its notch is centred 20.04 Hz where |N| = 0.011, but r63's ring sits at 16.5 Hz,")
    pr("  off the notch centre, so the attenuation there is much smaller and I did not compute it).")
    pr("  ⇒ ONLY THE r39 (V282) ROW IS A CLEAN MIRROR RESULT.  V282's cave is the read-only r24")
    pr("  comparator telemetry; it adds no filter to the rate path.")
    pr("")


def main():
    G = {}
    for tag in B.ROUTES:
        pr("loading %s ..." % tag)
        g = B.load_route(tag)
        lo, hi = B.BAND[tag]
        g["f0"] = B.ring_f0(g, lo, hi)
        g["env"] = B.demod_env(g["bar"], g["f0"], FS)
        on, pk, amp, thi, tlo = B.find_onsets(g["env"], g["eng"])
        g["on"], g["pk"], g["amp"] = on, pk, amp
        g["on_t"], g["pk_t"] = g["tr"][on], g["tr"][pk]
        g["runs"] = B.eng_runs(g)
        g["eng_s"] = float(g["eng"].sum()) / FS
        g["ev"], g["E"] = B.event_series(g)
        sf = np.zeros(len(g["t"]))
        kk = np.clip(np.searchsorted(g["t"], g["e4"]["step_t"]), 0, len(g["t"]) - 1)
        np.maximum.at(sf, kk, np.abs(g["e4"]["step"]))
        g["step_f"] = sf
        G[tag] = g
    OUT.clear()
    pr("=" * 118)
    pr("SIZING THE PHASE-LOCKED ECHO -- follow-up to BURST-ONSET-TRIGGERS-2026-09-10.  2026-09-10")
    pr("=" * 118)
    pr("")
    res = sectionE1(G)
    sectionE2(G, res)
    sectionE3(G)
    sectionE4(G)
    sectionE5(G, res)
    with open(os.path.join(B.SCR, "burst_echo_sizing.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/burst_echo_sizing.txt")


if __name__ == "__main__":
    main()
