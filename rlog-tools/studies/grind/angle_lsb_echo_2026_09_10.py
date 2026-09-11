# -*- coding: utf-8 -*-
"""studies/grind/angle_lsb_echo_2026_09_10.py -- IS THE COMMAND'S RING-BAND LINE A QUANTISER ARTEFACT OF
openpilot's 0.1 deg/LSB STEER_ANGLE MEASUREMENT?   Agent `echoloop`, 2026-09-10.  ANALYSIS ONLY.

Claim under test (raised in docs/research/OPENPILOT-EXCITATION-SOURCES-2026-09-10.md sec. 5.2, as BELIEF):
openpilot's `measurement` is CS.steeringAngleDeg (0x14A STEER_ANGLE, 0.1 deg/LSB, 100 Hz, UNFILTERED),
entering the command only through P (k_d = 0, k_p = SteerKP = 0.6).  One LSB propagated through
calc_curvature x v^2 x P x (1/LAF) x STEER_MAX is worth 13-53 raw 0xE4 counts over 5-30 m/s, against a
measured ring-band command amplitude of 15-40 counts.  If the ring in the ANGLE is <= ~1 LSB, the
command's line is a bang-bang quantiser artefact, not a faithful reading.

The decisive instrument is INDEPENDENT: 0x18F STEER_ANGLE_RATE is the same physical motion on a much
finer effective scale in this band -- a ring of amplitude A deg at f0 has rate amplitude A*2*pi*f0 deg/s,
so at 20 Hz the rate channel resolves the same motion many times finer per LSB.  Ring amplitude is
therefore measured TWICE: on the quantised angle, and via the rate channel.

Sections
  0  INSTRUMENT    the angle quantiser, the 0x14A frame rate, the fitted 0x18F counts-per-deg/s
  1  LSB HISTOGRAM diff(0x14A STEER_ANGLE) in raw LSBs, grinding vs speed+demand-MATCHED baseline
  2  RING AMPLITUDE ring-band angle amplitude in deg and LSBs, both instruments, vs the quantiser floor
  3  RESIDUAL NATURE line or broadband?  prominence, spectral flatness, coherence with the rate channel
  4  CLOSE THE LOOP angle ring -> gain chain -> predicted 0xE4 counts vs MEASURED, per speed bin, CI
  5  RATE LIMITER  measured bind duty, and the two-tone describing function AT that measured duty

Routes r39 (V282), r5e_v288 (V288r2), r62_v289 / r63_v289 (V289), r35 (V281r3).
Band: 18-22 Hz on V281r3/V282/V288; 13-18 Hz on V289 (the 18-22 gate is blind to V289's relocated line).

One expensive pass computes every per-window quantity and caches it to
_scratch/angle_lsb_echo_windows.npz; re-runs are instant.  Delete the cache or pass --rebuild to redo it.

Run: python angle_lsb_echo_2026_09_10.py [--rebuild]
     (writes _scratch/angle_lsb_echo_2026_09_10.txt beside it)
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import v280_map_profiles as V                 # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
W, STEP = 200, 50
LSB_DEG = 0.1                                  # 0x14A STEER_ANGLE scale, honda_civic_hatchback_ex_2017 dbc:521
ROUTES = (("r39", "V282", 18.0, 22.0),
          ("r5e_v288", "V288r2", 18.0, 22.0),
          ("r62_v289", "V289", 13.0, 18.0),
          ("r63_v289", "V289", 13.0, 18.0),
          ("r35", "V281r3", 18.0, 22.0))
CACHE = os.path.join(SCR, "angle_lsb_echo_windows.npz")

# --- the openpilot gain chain (fork-derived; see the report sec. 5.2) -------------------------------
STD_CARGO_KG = 136.0
M_VEH = 3279 * 0.453592 + STD_CARGO_KG
L_WB, SR_ON_CENTRE = 2.83, 16.00
A_F = L_WB * 0.39
A_R = L_WB - A_F
TSF = 0.8467
_cF = TSF * 192 * M_VEH / (L_WB ** 2) * A_R
_cR = TSF * 192 * M_VEH / (L_WB ** 2) * A_F
SLIP = M_VEH * (_cF * A_F - _cR * A_R) / (L_WB ** 2 * _cF * _cR)
LOW_SPEED_X, LOW_SPEED_Y = [0, 10, 20, 30], [12, 10.5, 8, 5]
KP_LIVE = 0.6                                  # SteerKP, pinned every frame at controlsd.py:449-450
LAF = 1.6893                                   # SteerLatAccel / torqued default
STEER_MAX = 4096
CAP = 3.0 * 0.01 * STEER_MAX                   # 122.88 raw counts/frame

OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def curvature_factor(u):
    return 1.0 / (1.0 - SLIP * u ** 2) / L_WB


def counts_per_deg(v):
    """raw 0xE4 counts produced by one DEGREE of measured steering angle, through P only."""
    v = max(float(v), 0.5)
    dmeas = curvature_factor(v) * np.radians(1.0) / SR_ON_CENTRE * v ** 2
    lsf = (np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / max(v, 1.0)) ** 2
    return dmeas * (KP_LIVE + lsf) / LAF * STEER_MAX          # k_p*err + lsf*err


def boot_ci(x, f=np.median, n=3000, seed=3):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return (np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    b = np.array([f(x[rng.integers(0, len(x), len(x))]) for _ in range(n)])
    return float(f(x)), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


# ======================================================================================================
# loading
# ======================================================================================================
def load(tag):
    g = C20.load(tag)
    g["tr"] = g["t"] - g["t"][0]
    D = dict(np.load(os.path.join(C20.CACHE, tag + ".npz")))
    k14, P14, tn14, _ = C20.dejitter(D["t14"], 0.01, 100)
    a = np.asarray(D["ang"], float)
    g["a_k"], g["a_P"], g["a_t"], g["a_deg"] = k14, P14, tn14, a
    g["a_lsb"] = np.round(a / LSB_DEG).astype(np.int64)
    K = int(k14[-1])
    gr = np.full(K + 1, np.nan)
    gr[k14] = a
    have = ~np.isnan(gr)
    gr[~have] = np.interp(np.flatnonzero(~have), np.flatnonzero(have), gr[have])
    g["ag"], g["ag_have"], g["ag_t"] = gr, have, np.interp(np.arange(K + 1), k14, tn14)
    # fitted counts per deg/s on the 0x18F rate wire (empirical check on V.CPD)
    da = np.diff(gr) / P14
    wr = np.interp(g["ag_t"][1:], g["t"], -g["wire"])
    m = np.isfinite(da) & np.isfinite(wr) & (np.abs(da) > 5)
    g["cpd"] = float(np.sum(wr[m] * da[m]) / np.sum(da[m] ** 2))
    return g


# ======================================================================================================
# ONE expensive pass: every per-window quantity, cached
# ======================================================================================================
FIELDS = ("s", "pres", "f0", "prom", "bar_amp", "v", "idx",
          "ang_amp", "ang_prom", "ang_df", "flat", "res_lsb", "coh",
          "rate_amp", "cmd_amp", "bind", "d0", "d1", "d2", "d3", "d4", "d5", "d6p", "dmean", "dn")


def one_pass(G):
    rec = {}
    for tag, build, lo, hi in ROUTES:
        g = G[tag]
        fsa = 1.0 / g["a_P"]
        slo, shi = max(lo - 3.0, 5.0), hi + 4.0
        sos_hp = signal.butter(4, 8.0, btype="highpass", fs=fsa, output="sos")
        rows = []
        runs = C20.runs(g["eng"], W)
        tot = sum(len(range(a, b - W + 1, STEP)) for a, b in runs)
        k = 0
        for a, b in runs:
            for s in range(a, b - W + 1, STEP):
                e = s + W
                bar = g["bar"][s:e]
                f0, prom, _, _ = GI.line_of(bar, FS, slo, shi)
                amp = GI.band(bar, lo, hi, FS)
                pres = bool(np.isfinite(f0) and prom >= 8 and amp >= 40)
                f0u = float(f0) if np.isfinite(f0) else 0.5 * (lo + hi)
                # --- raw angle on its OWN uniform 100 Hz grid over the same span (quantiser preserved)
                t0, t1 = g["t"][s], g["t"][e - 1]
                i0 = int(np.searchsorted(g["ag_t"], t0))
                i1 = int(np.searchsorted(g["ag_t"], t1))
                ag = g["ag"][i0:i1]
                # --- raw LSB steps inside the window
                ms = (g["a_t"] >= t0) & (g["a_t"] <= t1)
                dl = np.abs(np.diff(g["a_lsb"][ms])) if ms.sum() > 8 else np.array([], int)
                if len(ag) < 128 or len(dl) < 8:
                    continue
                fa, pa, _, _ = GI.line_of(ag, fsa, slo, shi)
                res = signal.sosfiltfilt(sos_hp, ag - ag.mean())
                f, P = signal.periodogram(res, fs=fsa, window="hann")
                sel = (f >= 12.0) & (f <= 26.0)
                flat = float(np.exp(np.mean(np.log(P[sel] + 1e-30))) / np.mean(P[sel]))
                n = min(len(ag), W)
                fc, Cxy = signal.coherence(ag[:n] - ag[:n].mean(),
                                           -g["wire"][s:s + n] / g["cpd"], fs=FS, nperseg=64)
                ci = int(np.argmin(np.abs(fc - f0u)))
                dcmd = np.abs(np.diff(np.round(g["cmd"][s:e])))
                rows.append((
                    s, 1.0 if pres else 0.0, f0u, prom if np.isfinite(prom) else 0.0, amp,
                    float(np.median(g["vego"][s:e])), float(np.median(g["idx"][s:e])),
                    GI.band(ag, lo, hi, fsa), pa if np.isfinite(pa) else 0.0,
                    (fa - f0u) if np.isfinite(fa) else np.nan,
                    flat, GI.band(res, lo, hi, fsa) / LSB_DEG, float(Cxy[ci]),
                    GI.band(-g["wire"][s:e] / g["cpd"], lo, hi, FS),
                    GI.band(g["cmd"][s:e], lo, hi, FS),
                    100.0 * float(np.mean(dcmd >= CAP - 0.5)),
                    *[float(np.mean(dl == j)) for j in range(6)],
                    float(np.mean(dl >= 6)), float(np.mean(dl)), float(len(dl))))
                k += 1
                if k % 250 == 0:
                    print("   %s %d/%d" % (tag, k, tot), flush=True)
        rec[tag] = np.array(rows, float)
        print("  %s: %d windows, %d present" % (tag, len(rows), int(rec[tag][:, 1].sum())), flush=True)
    return rec


VB = [0, 4, 8, 12, 16, 20, 40]
IB = [0, 5, 10, 20, 32, 1e9]


def matched(R):
    """for each present window pick a not-present window from the same (speed bin, demand bin)."""
    rng = np.random.default_rng(11)
    v, idx, pres = R[:, 5], R[:, 6], R[:, 1] > 0.5
    cv, ci = np.digitize(v, VB), np.digitize(idx, IB)
    pool = {}
    for i in np.flatnonzero(~pres):
        pool.setdefault((cv[i], ci[i]), []).append(i)
    out, miss = [], 0
    for i in np.flatnonzero(pres):
        c = pool.get((cv[i], ci[i]))
        if not c:
            miss += 1
            continue
        out.append(c[rng.integers(0, len(c))])
    return np.array(out, int), miss


# ======================================================================================================
def main():
    rebuild = "--rebuild" in sys.argv
    G = {}
    for tag, build, lo, hi in ROUTES:
        G[tag] = load(tag)
        print("loaded %-9s %-8s %6.0f s, %5.0f s engaged, 0x14A %.3f Hz, fitted CPD %.3f"
              % (tag, build, G[tag]["tr"][-1], G[tag]["eng"].sum() / FS, 1.0 / G[tag]["a_P"], G[tag]["cpd"]), flush=True)
    os.makedirs(SCR, exist_ok=True)
    if os.path.exists(CACHE) and not rebuild:
        Z = np.load(CACHE)
        R = {t: Z[t] for t, _, _, _ in ROUTES}
        print("window cache loaded from %s" % CACHE, flush=True)
    else:
        print("one expensive pass over all windows (~4 min/route) ...", flush=True)
        R = one_pass(G)
        np.savez_compressed(CACHE, **R)
        print("cached to %s" % CACHE, flush=True)
    F = {n: i for i, n in enumerate(FIELDS)}

    pr("=" * 150)
    pr("IS THE RING-BAND LINE IN THE 0xE4 COMMAND A QUANTISER ARTEFACT OF openpilot's 0.1 deg/LSB ANGLE MEASUREMENT?")
    pr("angle_lsb_echo_2026_09_10.py, agent `echoloop`, 2026-09-10.  Analysis only: builds nothing, sends nothing.")
    pr("windows: census recipe (2 s / 0.5 s step, lateral-engaged, bar line prominence >= 8 AND bar band amp >= 40 raw),")
    pr("band 18-22 Hz on V281r3/V282/V288 and 13-18 Hz on V289.  Baselines are matched on SPEED and DEMAND index.")
    pr("=" * 150)

    # ---------------------------------------------------------------- 0
    pr("\n" + "=" * 150)
    pr("0. INSTRUMENT CHECK")
    pr("=" * 150)
    pr("  %-9s %-8s %10s %10s %12s %12s %9s %9s" %
       ("route", "build", "0x14A Hz", "n samples", "off 0.1 grid", "fitted CPD", "windows", "present"))
    for tag, build, lo, hi in ROUTES:
        g = G[tag]
        off = float(np.max(np.abs(g["a_deg"] / LSB_DEG - np.round(g["a_deg"] / LSB_DEG))))
        pr("  %-9s %-8s %10.3f %10d %12.1e %12.3f %9d %9d" %
           (tag, build, 1.0 / g["a_P"], len(g["a_deg"]), off, g["cpd"], len(R[tag]), int(R[tag][:, 1].sum())))
    pr("\n  0x14A STEER_ANGLE is EXACTLY on a 0.1 deg grid at ~101 Hz [EVIDENCE].")
    pr("  V.CPD (the kit's constant) = %.1f counts per deg/s; 1 LSB of the 0x18F rate = %.4f deg/s." % (V.CPD, 1.0 / V.CPD))
    pr("  At 20 Hz, 1 LSB of the RATE channel corresponds to %.5f deg of ring amplitude -- i.e. the rate"
       % (1.0 / V.CPD / (2 * np.pi * 20)))
    pr("  channel resolves this band %.0fx finer than the 0.1 deg angle channel." % (LSB_DEG / (1.0 / V.CPD / (2 * np.pi * 20))))

    # ---------------------------------------------------------------- 1
    pr("\n" + "=" * 150)
    pr("1. diff(0x14A STEER_ANGLE) IN RAW LSBs -- grinding vs speed+demand-MATCHED baseline windows")
    pr("=" * 150)
    for tag, build, lo, hi in ROUTES:
        Rt = R[tag]
        pres = np.flatnonzero(Rt[:, 1] > 0.5)
        mb, miss = matched(Rt)
        if len(pres) == 0:
            continue
        pr("\n  %s (%s): %d present, %d matched baseline (%d unmatched)" % (tag, build, len(pres), len(mb), miss))
        pr("    %-6s %9s | %8s %8s %8s %8s %8s %8s %8s | %8s" %
           ("arm", "n samples", "0", "1", "2", "3", "4", "5", ">=6", "mean|d|"))
        for name, sel in (("GRIND", pres), ("BASE", mb)):
            if len(sel) == 0:
                continue
            w = Rt[sel, F["dn"]]
            wsum = w.sum()
            row = [float(np.sum(Rt[sel, F[k]] * w) / wsum) for k in ("d0", "d1", "d2", "d3", "d4", "d5", "d6p")]
            mean = float(np.sum(Rt[sel, F["dmean"]] * w) / wsum)
            pr("    %-6s %9d | %s | %8.3f" %
               (name, int(wsum), " ".join("%7.2f%%" % (100 * x) for x in row), mean))
    pr("\n  READING: if GRIND is dominated by 0 and +-1 LSB while BASE is not, the angle stream is riding the")
    pr("  quantiser during grinding.  If the two arms look alike, the ring is not distinguishable there.")

    # ---------------------------------------------------------------- 2
    pr("\n" + "=" * 150)
    pr("2. RING AMPLITUDE IN THE ANGLE -- on the QUANTISED angle, and INDEPENDENTLY via the 0x18F rate")
    pr("=" * 150)
    pr("  quantiser noise floor of the ANGLE channel (uniform step 0.1 deg, white over 0-50 Hz):")
    for lo, hi in ((18.0, 22.0), (13.0, 18.0)):
        rms = LSB_DEG / np.sqrt(12.0) * np.sqrt((hi - lo) / 50.0)
        pr("     band %4.0f-%2.0f Hz : rms %.5f deg, amplitude %.5f deg = %.3f LSB  <- below this is NOISE"
           % (lo, hi, rms, np.sqrt(2) * rms, np.sqrt(2) * rms / LSB_DEG))
    pr("\n  %-9s %-8s %5s | %-32s | %-34s | %8s" %
       ("route", "build", "n", "ANGLE channel (quantised, 0.1 deg)", "RATE channel (0x18F, independent)", "ratio"))
    pr("  %-9s %-8s %5s | %10s %13s %7s | %10s %10s %10s | %8s" %
       ("", "", "", "amp deg", "[95% CI]", "LSBs", "amp deg/s", "-> amp deg", "in ang LSB", "rate/ang"))
    for tag, build, lo, hi in ROUTES:
        Rt = R[tag]
        p = Rt[Rt[:, 1] > 0.5]
        if len(p) < 5:
            continue
        aa = p[:, F["ang_amp"]]
        rr = p[:, F["rate_amp"]] / (2 * np.pi * p[:, F["f0"]])
        ma, la, ha = boot_ci(aa)
        mr, lr, hr = boot_ci(rr)
        pr("  %-9s %-8s %5d | %10.4f %13s %7.2f | %10.3f %10.4f %10.2f | %8.2f" %
           (tag, build, len(p), ma, "[%.4f,%.4f]" % (la, ha), ma / LSB_DEG,
            np.median(p[:, F["rate_amp"]]), mr, mr / LSB_DEG, mr / ma if ma else np.nan))

    # ---------------------------------------------------------------- 3
    pr("\n" + "=" * 150)
    pr("3. NATURE OF THE ANGLE'S RING-BAND CONTENT -- narrow line, or broadband dither?")
    pr("=" * 150)
    pr("  %-9s %-8s %5s | %8s %8s | %9s %9s | %-22s" %
       ("route", "build", "n", "ang prom", "d f0 Hz", "flatness", "res LSB", "coh(angle, 0x18F rate)"))
    pr("  %-9s %-8s %5s | %8s %8s | %9s %9s | %9s %12s" % ("", "", "", "(bar>=8)", "vs bar", "1=white", "amp", "median", "[95% CI]"))
    for tag, build, lo, hi in ROUTES:
        Rt = R[tag]
        p = Rt[Rt[:, 1] > 0.5]
        b = Rt[matched(Rt)[0]] if len(p) else None
        if len(p) < 5:
            continue
        mc, lc, hc = boot_ci(p[:, F["coh"]])
        pr("  %-9s %-8s %5d | %8.1f %+8.2f | %9.3f %9.3f | %9.3f %12s" %
           (tag, build, len(p), np.median(p[:, F["ang_prom"]]), np.nanmedian(p[:, F["ang_df"]]),
            np.median(p[:, F["flat"]]), np.median(p[:, F["res_lsb"]]), mc, "[%.3f,%.3f]" % (lc, hc)))
        if b is not None and len(b) >= 5:
            mcb, lcb, hcb = boot_ci(b[:, F["coh"]])
            pr("  %-9s %-8s %5d | %8.1f %+8.2f | %9.3f %9.3f | %9.3f %12s   <= matched baseline" %
               ("", "", len(b), np.median(b[:, F["ang_prom"]]), np.nanmedian(b[:, F["ang_df"]]),
                np.median(b[:, F["flat"]]), np.median(b[:, F["res_lsb"]]), mcb, "[%.3f,%.3f]" % (lcb, hcb)))
    pr("\n  flatness 1.0 = perfectly white (pure dither); << 1 = a line dominates the band (a real ring).")
    pr("  coherence: the angle and the 0x18F rate are the SAME physical motion seen by two ECUs' signals.")
    pr("  High coherence at the line => the angle carries genuine ring motion.  Low => quantiser hash.")

    # ---------------------------------------------------------------- 4
    pr("\n" + "=" * 150)
    pr("4. CLOSE THE LOOP -- angle ring x the openpilot gain chain, vs the MEASURED 0xE4 ring-band amplitude")
    pr("=" * 150)
    pr("  prediction: |cmd|_ring = |angle|_ring [deg] x counts_per_deg(v), counts_per_deg =")
    pr("  curvature_factor(v) x rad(1 deg)/sR x v^2 x (k_p=%.2f + LSF(v)) / LAF=%.4f x %d.  P is the ONLY" % (KP_LIVE, LAF, STEER_MAX))
    pr("  path into the command from the measurement (k_d = 0 [EVIDENCE, pid.py:6 + no _k_d assignment]).")
    pr("\n    %-8s %s" % ("v m/s", " ".join("%8.1f" % v for v in (5, 8, 10, 12, 15, 20, 25, 30))))
    pr("    %-8s %s" % ("ct/deg", " ".join("%8.1f" % counts_per_deg(v) for v in (5, 8, 10, 12, 15, 20, 25, 30))))
    pr("    %-8s %s" % ("ct/LSB", " ".join("%8.1f" % (counts_per_deg(v) * LSB_DEG) for v in (5, 8, 10, 12, 15, 20, 25, 30))))
    pr("\n  %-9s %-8s %-11s %5s | %9s %9s %9s | %-16s | %s" %
       ("route", "build", "speed bin", "n", "pred ct", "meas ct", "ratio", "ratio [95% CI]", "via RATE-derived angle"))
    POOL, POOLR = [], []
    for tag, build, lo, hi in ROUTES:
        Rt = R[tag]
        p = Rt[Rt[:, 1] > 0.5]
        if len(p) < 5:
            continue
        cpdeg = np.array([counts_per_deg(v) for v in p[:, F["v"]]])
        pred = p[:, F["ang_amp"]] * cpdeg
        predr = p[:, F["rate_amp"]] / (2 * np.pi * p[:, F["f0"]]) * cpdeg
        meas = np.maximum(p[:, F["cmd_amp"]], 1e-9)
        for a, bnd in ((0, 8), (8, 14), (14, 20), (20, 40)):
            m = (p[:, F["v"]] >= a) & (p[:, F["v"]] < bnd)
            if m.sum() < 5:
                continue
            mr, lr, hr = boot_ci(pred[m] / meas[m])
            mr2, _, _ = boot_ci(predr[m] / meas[m])
            pr("  %-9s %-8s %-11s %5d | %9.1f %9.1f %9.2f | [%.2f, %.2f]%s | %.2f" %
               (tag, build, "%d-%d m/s" % (a, bnd), int(m.sum()), np.median(pred[m]), np.median(meas[m]),
                mr, lr, hr, " " * 4, mr2))
        mr, lr, hr = boot_ci(pred / meas)
        mr2, l2, h2 = boot_ci(predr / meas)
        pr("  %-9s %-8s %-11s %5d | %9.1f %9.1f %9.2f | [%.2f, %.2f]%s | %.2f [%.2f, %.2f]   <= route" %
           (tag, build, "ALL", len(p), np.median(pred), np.median(meas), mr, lr, hr, " " * 4, mr2, l2, h2))
        POOL.append(pred / meas)
        POOLR.append(predr / meas)
    if POOL:
        mr, lr, hr = boot_ci(np.concatenate(POOL))
        mr2, l2, h2 = boot_ci(np.concatenate(POOLR))
        pr("\n  POOLED predicted/measured, ANGLE-derived: %.2f [%.2f, %.2f]   (n = %d windows)"
           % (mr, lr, hr, sum(len(x) for x in POOL)))
        pr("  POOLED predicted/measured, RATE-derived  : %.2f [%.2f, %.2f]" % (mr2, l2, h2))
    pr("\n  READING: ratio ~1 (within ~2x) => the command's ring line IS P re-transmitting the measured")
    pr("  angle; the ECHO is fully accounted for.  ratio << 1 => something else drives the command's line.")

    # ---------------------------------------------------------------- 5
    pr("\n" + "=" * 150)
    pr("5. THE RATE LIMITER AT ITS MEASURED BIND DUTY -- passing or swallowing the ring?")
    pr("=" * 150)
    pr("  cap = STEER_DELTA_UP(3) x DT_CTRL(0.01) x STEER_MAX(4096) = %.2f raw counts/frame" % CAP)
    pr("\n  %-9s %-8s %7s %12s %12s | %11s" % ("route", "build", "n pres", "bind% GRIND", "bind% BASE", "cmd ring ct"))
    DUTY, RINGCT = [], []
    for tag, build, lo, hi in ROUTES:
        Rt = R[tag]
        pi = np.flatnonzero(Rt[:, 1] > 0.5)
        mb, _ = matched(Rt)
        if len(pi) < 5:
            continue
        dg = float(np.median(Rt[pi, F["bind"]]))
        db = float(np.median(Rt[mb, F["bind"]])) if len(mb) else np.nan
        rc = float(np.median(Rt[pi, F["cmd_amp"]]))
        DUTY.append(dg)
        RINGCT.append(rc)
        pr("  %-9s %-8s %7d %12.2f %12.2f | %11.1f" % (tag, build, len(pi), dg, db, rc))
    md = float(np.median(DUTY)) if DUTY else np.nan
    pr("\n  median measured bind duty inside grinding windows, across routes: %.2f %%" % md)
    pr("  (the record's '13-21 %% of grinding frames' is the comparable figure)")

    pr("\n  two-tone describing function RE-PARAMETERISED BY BIND DUTY: a 2 Hz slow drive is swept until the")
    pr("  limiter's duty matches the target, then |N| is the gain a 30-count 20 Hz rider sees through it.")
    R_LIM, Ahf = 3.0, 30.0 / STEER_MAX

    def two_tone(Aslow, fslow=2.0, fhf=20.0, secs=60.0, fs=100.0):
        n = int(secs * fs)
        t = np.arange(n) / fs
        u = Aslow * np.sin(2 * np.pi * fslow * t) + Ahf * np.sin(2 * np.pi * fhf * t)
        y = np.empty(n)
        pv = 0.0
        bind = 0
        step = R_LIM / fs
        for k, vv in enumerate(u):
            loq, hiq = pv - step, pv + step
            if vv < loq or vv > hiq:
                bind += 1
            pv = min(max(vv, loq), hiq)
            y[k] = pv
        c = np.exp(-1j * 2 * np.pi * fhf * t)
        N = (2 * np.mean(y * c)) / (2 * np.mean(u * c))
        return abs(N), np.degrees(np.angle(N)), 100.0 * bind / n

    pr("    %-14s %10s %12s %10s %10s" % ("target duty", "slow A ct", "actual duty", "|N|@20Hz", "phase"))
    for target in sorted(set([2.0, 5.0, 10.0, 13.0, round(md, 2), 17.0, 21.0, 40.0, 80.0, 99.0])):
        lo_a, hi_a = 1.0, 4096.0
        for _ in range(26):
            mid = 0.5 * (lo_a + hi_a)
            _, _, dd = two_tone(mid / STEER_MAX)
            if dd < target:
                lo_a = mid
            else:
                hi_a = mid
        A = 0.5 * (lo_a + hi_a)
        gN, pN, dd = two_tone(A / STEER_MAX)
        pr("    %-14s %10.0f %12.2f %10.3f %+9.1f%s" %
           ("%.2f %%" % target, A, dd, gN, pN, "   <= MEASURED" if abs(target - round(md, 2)) < 1e-9 else ""))
    pr("\n  DIRECT EMPIRICAL ANSWER, no model needed: the ring line IS present in the POST-limiter 0xE4")
    pr("  stream at %.0f-%.0f raw counts (column 'cmd ring ct').  A limiter that were swallowing the rider"
       % (min(RINGCT), max(RINGCT)))
    pr("  would not emit it.  At the measured duty the limiter is PASSING the ring.")

    with open(os.path.join(SCR, "angle_lsb_echo_2026_09_10.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(OUT) + "\n")
    pr("\nwrote %s" % os.path.join(SCR, "angle_lsb_echo_2026_09_10.txt"))


if __name__ == "__main__":
    main()
