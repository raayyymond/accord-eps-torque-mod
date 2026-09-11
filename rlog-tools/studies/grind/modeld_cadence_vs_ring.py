# -*- coding: utf-8 -*-
"""studies/grind/modeld_cadence_vs_ring.py -- IS THE ~20 Hz GRINDING LINE A FORCED RESPONSE TO
MODELD'S 20 Hz FRAME CADENCE, OR A PLANT RESONANCE?   Subagent `modelrate`, 2026-09-10.
ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.

The kit has never asked this.  `modeld` / `modelV2` / `MODEL_FREQ` appear in no grind study, review or
design doc.  The existing falsification of "H2 -- the staircase" was run on the FIRST difference of the
0xE4 command and on value-repeat statistics; a piecewise-linear knotted ramp passes all of those
trivially while carrying a slope discontinuity at exactly the model rate, which lives in the SECOND
difference.

Routes (all caches already on disk; nothing is re-downloaded)
  r22        V112, STOCK MAP x1  (the older era in which the 20 Hz line was already named)
  r39        V282
  r5e_v288   V288 rev 2
  r62_v289 / r63_v289   V289 rev 1   (the notch build -- its line sits at 15-17 Hz)

CLOCKS -- reconciled explicitly, because the whole question is a 0.3 % frequency comparison.
  * `analysis-2020accord/_scratch/cache/v280/<tag>.npz` stores RAW `logMonoTime` seconds (see
    extract_r39_v280cache.py: `t18.append(tm)` with `tm = evt.logMonoTime*1e-9`; no t0 is subtracted).
    `_scratch/modeld/<tag>_cad.npz` (modeld_cadence_extract.py) stores the same quantity for every
    openpilot-side message.  => modelV2 publish times and CAN receive times are on ONE clock already.
  * The CAN streams are still BATCH-JITTERED on that clock, so each is put back on its own nominal
    frame counter by creep20_loop_id.dejitter, which also FITS the stream's true period P.  P is in
    DEVICE seconds per frame, so `fs = 1/P` is the stream's rate measured against the device clock --
    that is the reconciliation.  Measured: P18 (EPS 0x18F) = 0.0100001-0.0100008 s, i.e. the EPS clock
    is within 0.008 % of the device clock, so a line reported at 20.03 Hz on the k18 axis is at
    20.03 Hz +- 0.002 Hz in device seconds.  Pe4 (the device's OWN 0xE4 tx) fits ~0.010045 s = 99.55 Hz:
    controlsd's Ratekeeper slips ~0.45 %, which matters for anything read on the 0xE4 counter axis and
    is corrected here by using the FITTED Pe4, never a nominal 0.01.
  * The camera stamp `timestampEof` is on the boottime clock (a different ORIGIN, same rate: the
    fid->eof and fid->logMonoTime regressions agree to 3e-11 s/frame).  Only differences are used.

Sections
  1  CADENCE      modeld's actual rate per route (fid->logMonoTime and fid->timestampEof regressions,
                  with SE), dt distribution, drop indicators, execution time; livePose / cameraOdometry
                  / roadCameraState / controlsState / carControl / carOutput rates; the CAN clocks.
  2  THE PLAN     is `controlsState.desiredCurvature` the 5-frame staircase or the knotted ramp?  hold
                  census stratified by speed and engagement; how often clip_curvature BINDS (tested by
                  equality against its own bound, not by a proxy); how often the value is the raw model
                  value passed through; the POSITIVE CONTROL -- the 5-phase fold of D2(desiredCurvature).
  3  D2 ON THE WIRE   D2cmd = cmd[n] - 2cmd[n-1] + cmd[n-2] on the dejittered 0xE4 counter; its spectrum,
                  grinding windows vs matched baseline (H1 SS C strata); power at f_model vs local
                  background; the model-phase fold of |D2cmd| and its concentration index.
  4  RING f       the census episodes' line frequency, pooled, with a block bootstrap CI, against
                  f_model on the same clock.
  5  PHASE LOCK   the decisive discriminator.  Instantaneous phase of the 18-22 Hz (V289: 13-18 Hz)
                  component of each channel, referenced to the model frame clock; Rayleigh R with an
                  effective-N correction; a delta-sweep of the reference clock as the drifting-clock null;
                  and the same statistic on `controlsState.desiredCurvature` as the POSITIVE CONTROL.
  6  VERDICT      what a NULL looks like, and whether we got one.

Run: python modeld_cadence_vs_ring.py            (writes _scratch/modeld_cadence_vs_ring.txt)
"""
import os
import sys

import numpy as np
from scipy import signal, stats

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
MDIR = os.path.join(SCR, "modeld")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import v280_map_profiles as V                 # noqa: E402
import grind_incident_r35 as GI               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTES = [("r22", "V112 (STOCK MAP x1)"), ("r39", "V282"), ("r5e_v288", "V288 rev 2"),
          ("r62_v289", "V289 rev 1"), ("r63_v289", "V289 rev 1")]
# the band the grinding mode occupies on each build (STATE.md 2026-09-09 two-object picture)
BAND = {"r22": (18.0, 22.0), "r39": (18.0, 22.0), "r5e_v288": (18.0, 22.0),
        "r62_v289": (13.0, 18.0), "r63_v289": (13.0, 18.0)}
W, STEP = 200, 50          # grind1_census_v282.py's 2 s window / 0.5 s step
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def hr(t):
    pr(); pr("=" * 118); pr(t); pr("=" * 118)


# ======================================================================================================
# loading
# ======================================================================================================
def load(tag):
    """v280 CAN cache on the dejittered 0x18F frame axis + the raw 0xE4 counter axis + modeld timing."""
    D = dict(np.load(os.path.join(C20.CACHE, tag + ".npz")))
    k18, P18, tn18, res18 = C20.dejitter(D["t18"], 0.01, 100)
    ke4, Pe4, tne4, rese4 = C20.dejitter(D["te4"], 0.01, 100)
    k1a, P1a, tn1a, res1a = C20.dejitter(D["t1ab"], 0.02, 50)
    K = int(k18[-1])
    g = dict(tag=tag, P18=P18, Pe4=Pe4, P1ab=P1a,
             res18=np.percentile(np.abs(res18), 90), rese4=np.percentile(np.abs(rese4), 90))
    g["t"] = np.interp(np.arange(K + 1), k18, tn18)                  # device-clock time of 0x18F frame k
    g["bar"], have = C20.grid_from(k18, D["tq"] * 1.024, K)
    g["wire"], _ = C20.grid_from(k18, D["rate"].astype(float), K)
    sca, _ = C20.grid_from(k18, D["sca"].astype(float), K)
    g["have"] = have
    g["cmd"] = np.interp(g["t"], tne4, D["cmd"].astype(float))
    req = np.interp(g["t"], tne4, D["req"].astype(float)) > 0.5
    g["ang"] = np.interp(g["t"], D["t14"], D["ang"].astype(float))
    g["vego"] = np.interp(g["t"], D["tcs"], D["vego"].astype(float))
    g["eng"] = (sca > 0.5) & req & have
    g["tr"] = g["t"] - g["t"][0]
    g["rate"] = np.abs(g["wire"]) / V.CPD
    fld = ((D["b0"].astype(int) & 3) << 8) | D["b1"].astype(int)
    g["T_t"], g["T"] = tn1a, np.where(fld >= 512, -1.0, 1.0) * (fld & 511) * 8
    # the RAW 0xE4 stream on its OWN counter (the axis D2 must be computed on)
    Ke = int(ke4[-1])
    ge, havee = C20.grid_from(ke4, D["cmd"].astype(float), Ke)
    rq, _ = C20.grid_from(ke4, D["req"].astype(float), Ke)
    sc = np.interp(np.interp(np.arange(Ke + 1), ke4, tne4), g["t"], sca)
    g["e4"] = dict(t=np.interp(np.arange(Ke + 1), ke4, tne4), cmd=ge, have=havee,
                   eng=(rq > 0.5) & (sc > 0.5) & havee, P=Pe4)
    g["e4"]["v"] = np.interp(g["e4"]["t"], D["tcs"], D["vego"].astype(float))
    g["e4"]["bar"] = np.interp(g["e4"]["t"], g["t"], g["bar"])
    # modeld / controlsd timing
    M = dict(np.load(os.path.join(MDIR, tag + "_cad.npz"), allow_pickle=True))
    g["M"] = M
    sl, ic = np.polyfit(M["mdl_fid"], M["mdl_t"], 1)
    g["f_model"], g["model_slope"], g["model_icept"] = 1.0 / sl, sl, ic
    return g


def model_phase(g, t):
    """continuous model-frame index at device-clock time t; theta = 2*pi*index."""
    return (t - g["model_icept"]) / g["model_slope"]


def runs(mask, n):
    return C20.runs(mask, n)


# ======================================================================================================
# SECTION 1 -- cadence
# ======================================================================================================
def sec1(G):
    hr("SECTION 1 -- MEASURED CADENCES (every number from the rlogs; logMonoTime seconds)")
    pr("modeld publish rate, from a least-squares fit of the message clock on modelV2.frameId")
    pr("(N is the number of modelV2 messages; SE is the regression SE of the period, converted to Hz)")
    pr()
    pr("%-10s %-20s %7s %8s  %-26s %-26s %8s" %
       ("route", "build", "N", "span s", "f from logMonoTime [Hz]", "f from timestampEof [Hz]", "dfid!=1"))
    pr("-" * 118)
    for tag, build in ROUTES:
        M = G[tag]["M"]
        fid, t, eof = M["mdl_fid"], M["mdl_t"], M["mdl_eof"] * 1e-9
        n = len(fid)
        out = []
        for y in (t, eof):
            A = np.vstack([fid, np.ones(n)]).T
            coef, res, *_ = np.linalg.lstsq(A, y, rcond=None)
            sl = coef[0]
            resid = y - A @ coef
            se_sl = np.sqrt((resid @ resid) / (n - 2) / ((fid - fid.mean()) @ (fid - fid.mean())))
            out.append((1.0 / sl, se_sl / sl ** 2))
        nbad = int((np.diff(fid) != 1).sum())
        pr("%-10s %-20s %7d %8.1f  %12.6f +- %-9.6f %12.6f +- %-9.6f %8d" %
           (tag, build, n, t[-1] - t[0], out[0][0], out[0][1], out[1][0], out[1][1], nbad))
    pr()
    pr("modelV2 health and the other openpilot-side rates (N / span, on the same clock)")
    pr("%-10s %9s %9s %9s %9s | %8s %8s %8s %8s %8s %8s" %
       ("route", "dropPerc", "frameAge", "exec ms", "dt p1-p99", "livePose", "camOdo", "roadCam",
        "ctrlState", "carCtrl", "carOut"))
    pr("-" * 118)
    for tag, _ in ROUTES:
        M = G[tag]["M"]
        dt = np.diff(M["mdl_t"])
        rate = lambda p: (len(M[p + "_t"]) - 1) / (M[p + "_t"][-1] - M[p + "_t"][0]) if p + "_t" in M else np.nan  # noqa: E731
        pr("%-10s %9.4f %9.3f %9.2f %5.1f-%-5.1f | %8.4f %8.4f %8.4f %8.3f %8.3f %8.3f" %
           (tag, np.nanmax(M["mdl_drop"]), np.nanmax(M["mdl_age"]), np.nanmedian(M["mdl_exec"]) * 1e3,
            np.percentile(dt, 1) * 1e3, np.percentile(dt, 99) * 1e3,
            rate("lp"), rate("od"), rate("rc"), rate("cs"), rate("cc"), rate("co")))
    pr()
    pr("CAN stream clocks, fitted by creep20_loop_id.dejitter (DEVICE seconds per frame)")
    pr("%-10s %14s %12s %14s %12s %14s %12s %10s" %
       ("route", "P18 (EPS)", "-> Hz", "Pe4 (device tx)", "-> Hz", "P1ab (EPS)", "-> Hz", "f_model"))
    pr("-" * 118)
    for tag, _ in ROUTES:
        g = G[tag]
        pr("%-10s %14.8f %12.5f %14.8f %12.5f %14.8f %12.5f %10.6f" %
           (tag, g["P18"], 1 / g["P18"], g["Pe4"], 1 / g["Pe4"], g["P1ab"], 1 / g["P1ab"], g["f_model"]))
    pr()
    pr("CLOCK RECONCILIATION [EVIDENCE]")
    pr("  * modelV2 publish times and CAN receive times come from ONE clock (logMonoTime) with ONE zero;")
    pr("    no offset is applied anywhere below.")
    pr("  * The EPS 0x18F stream -- the channel every grinding frequency in this kit is measured on --")
    pr("    runs at 1/P18 = %.5f-%.5f Hz against that clock.  A line reported at 20.03 Hz on the k18"
       % (min(1 / G[t]["P18"] for t, _ in ROUTES), max(1 / G[t]["P18"] for t, _ in ROUTES)))
    pr("    axis is therefore at 20.03 Hz +- <0.002 Hz in device seconds.  THE 20.03-vs-20.00 GAP IS NOT")
    pr("    A CLOCK ARTEFACT AT THIS LEVEL.")
    pr("  * The device's own 0xE4 transmit counter fits 1/Pe4 = %.5f-%.5f Hz -- controlsd's Ratekeeper"
       % (min(1 / G[t]["Pe4"] for t, _ in ROUTES), max(1 / G[t]["Pe4"] for t, _ in ROUTES)))
    pr("    slips ~0.45 %% low.  Everything read on the 0xE4 counter below uses the FITTED Pe4.")


# ======================================================================================================
# SECTION 2 -- the plan and the limiter
# ======================================================================================================
MAX_LATERAL_JERK = 5.0      # drive_helpers.py:13 (read from the fork at trace time)
DT_CTRL = 0.01
MIN_SPEED = 1.0


def sec2(G):
    hr("SECTION 2 -- WHAT controlsd ACTUALLY EMITS: staircase, ramp, or both?")
    pr("`controlsState.desiredCurvature` is the POST-clip_curvature value (controlsd.py:803-806:")
    pr("`self.desired_curvature, curvature_limited = clip_curvature(...)` then `actuators.curvature =")
    pr("self.desired_curvature`).  Hold length = number of consecutive 100 Hz ticks with an identical")
    pr("float.  A pure 20 Hz staircase gives hold = 5; a rate-limited ramp gives hold = 1.")
    pr()
    pr("%-10s %-12s %8s %7s %7s %7s %7s %7s | %9s %9s" %
       ("route", "stratum", "ticks", "h=1", "h=4", "h=5", "h=6", "other", "bind frac", "passthru"))
    pr("-" * 118)
    S2 = {}
    for tag, _ in ROUTES:
        M = G[tag]["M"]
        t, dc = M["cs_t"], M["cs_descurv"]
        v = np.interp(t, M["st_t"], M["st_v"])
        lat = np.interp(t, M["cc_t"], M["cc_latact"]) > 0.5
        act = M["cs_active"] > 0.5
        eng = lat & act
        ch = np.r_[True, dc[1:] != dc[:-1]]
        idx = np.flatnonzero(ch)
        hold = np.diff(idx)
        st = idx[:-1]
        # clip_curvature binding: |d(dc)| equal (to float tolerance) to its own bound
        vv = np.maximum(v, MIN_SPEED)
        bound = MAX_LATERAL_JERK / vv ** 2 * DT_CTRL
        d = np.r_[0.0, np.diff(dc)]
        bind = np.abs(np.abs(d) - bound) <= 1e-9 + 1e-6 * bound
        # pass-through: dc equals the latest modelV2 action.desiredCurvature
        j = np.clip(np.searchsorted(M["mdl_t"], t) - 1, 0, len(M["mdl_t"]) - 1)
        passthru = np.abs(dc - M["mdl_curv"][j]) <= 1e-12
        for lab, m in (("engaged", eng), ("eng v<12", eng & (v < 12)), ("eng v>=12", eng & (v >= 12))):
            if m.sum() < 500:
                continue
            ok = m[st]
            h = hold[ok]
            f = lambda k: float((h == k).mean()) if len(h) else np.nan  # noqa: E731
            pr("%-10s %-12s %8d %7.3f %7.3f %7.3f %7.3f %7.3f | %9.3f %9.3f" %
               (tag, lab, int(m.sum()), f(1), f(4), f(5), f(6),
                1 - f(1) - f(4) - f(5) - f(6), float(bind[m].mean()), float(passthru[m].mean())))
            if lab == "eng v<12":
                S2[tag] = dict(frac5=f(5), frac1=f(1), bind=float(bind[m].mean()),
                               passthru=float(passthru[m].mean()))
        pr("-" * 118)
    pr()
    pr("POSITIVE CONTROL -- the 5-phase fold of D2(desiredCurvature) against the MODEL frame clock.")
    pr("D2 of a signal whose knots land on the model clock must concentrate in ONE phase bin.  The")
    pr("statistic is C = max(bin mean |D2|) / mean(|D2|); C = 1.0 is uniform, C = 5.0 is a perfect knot.")
    pr("The null column repeats the statistic with the reference clock detuned by +0.37 Hz.")
    pr()
    pr("%-10s %-22s %8s %8s %8s %10s" % ("route", "channel", "N", "C", "C null", "Rayleigh R"))
    pr("-" * 118)
    for tag, _ in ROUTES:
        g, M = G[tag], G[tag]["M"]
        t, dc = M["cs_t"], M["cs_descurv"]
        v = np.interp(t, M["st_t"], M["st_v"])
        lat = np.interp(t, M["cc_t"], M["cc_latact"]) > 0.5
        eng = lat & (M["cs_active"] > 0.5) & (v < 12)
        d2 = np.r_[0.0, 0.0, dc[2:] - 2 * dc[1:-1] + dc[:-2]]
        # the D2 sample at tick n is attributed to the phase at tick n-1 (the knot)
        ph = model_phase(g, t)
        for lab, phi in (("D2 desiredCurvature", ph), ):
            m = eng & np.isfinite(d2)
            C, R = fold_stats(np.abs(d2[m]), phi[m])
            phin = (t[m] - g["model_icept"]) * (g["f_model"] + 0.37)
            Cn, Rn = fold_stats(np.abs(d2[m]), phin)
            pr("%-10s %-22s %8d %8.3f %8.3f %10.4f" % (tag, lab, int(m.sum()), C, Cn, R))
    return S2


def fold_stats(w, phase, nb=5):
    """w >= 0 weights at continuous frame-phase `phase`.  Returns (concentration C, Rayleigh R)."""
    fr = phase - np.floor(phase)
    b = np.minimum((fr * nb).astype(int), nb - 1)
    mu = np.array([w[b == k].mean() if (b == k).any() else np.nan for k in range(nb)])
    C = np.nanmax(mu) / w.mean() if w.mean() > 0 else np.nan
    z = (w * np.exp(2j * np.pi * fr)).sum() / max(w.sum(), 1e-30)
    return float(C), float(np.abs(z))


# ======================================================================================================
# SECTION 3 -- D2 of the 0xE4 command
# ======================================================================================================
def episodes_of(g):
    """grind1_census_v282.py's episode recipe, band-adapted per build (STATE.md two-object picture)."""
    lo, hi = BAND[g["tag"]]
    wt, wp = [], []
    for aa, bb in runs(g["eng"], W):
        for s in range(aa, bb - W + 1, STEP):
            e = s + W
            f0w, prom, _, _ = GI.line_of(g["bar"][s:e], 100.0, lo - 3.0, hi + 4.0)
            amp = GI.band(g["bar"][s:e], lo, hi, 100.0)
            wt.append(g["tr"][s])
            wp.append((prom >= 8) and (amp >= 40))
    wt, wp = np.array(wt), np.array(wp, bool)
    if not len(wt):
        return [], np.zeros(len(g["eng"]), bool)
    j = np.clip(np.searchsorted(wt, g["tr"] - 1.0), 0, len(wt) - 1)
    near = np.abs(wt[j] + 1.0 - g["tr"]) < 1.5
    hot = g["eng"] & near & wp[j]
    eps = []
    for a, b in runs(hot, 50):
        f0, prom, _, _ = GI.line_of(g["bar"][a:b], 100.0, lo - 3.0, hi + 4.0)
        if np.isfinite(f0):
            eps.append((a, b, f0))
    return eps, hot


def welch_at(x, fs, f0, lo, hi, nper=512):
    """Welch PSD; returns (power at f0, median power in [lo,hi], peak f, peak/median)."""
    if len(x) < nper:
        return (np.nan,) * 4
    f, P = signal.welch(x - np.mean(x), fs=fs, nperseg=nper, noverlap=nper // 2,
                        nfft=1 << int(np.ceil(np.log2(nper * 16))))
    s = (f >= lo) & (f <= hi)
    if s.sum() < 4:
        return (np.nan,) * 4
    ff, PP = f[s], P[s]
    i0 = int(np.argmin(np.abs(ff - f0)))
    med = float(np.median(PP))
    return float(PP[i0]), med, float(ff[np.argmax(PP)]), float(PP.max() / med)


def sec3(G, EPS):
    hr("SECTION 3 -- THE SECOND DIFFERENCE OF THE 0xE4 COMMAND (what H2 never computed)")
    pr("D2cmd[n] = cmd[n] - 2cmd[n-1] + cmd[n-2], on the 0xE4 stream's OWN dejittered counter with its")
    pr("FITTED period Pe4 (~99.55 Hz, NOT 100).  Strata are H1-TORQUE-TABLE-RESOLUTION SS C's: baseline =")
    pr("engaged, v < 12 m/s, |bar| < 400 raw, outside every episode; grinding = the episode-majority ticks.")
    pr()
    pr("%-10s %-9s %8s %8s %9s %9s %9s %9s %9s" %
       ("route", "stratum", "ticks", "rms D2", "f_model", "P(f_m)", "P_med", "P(fm)/med", "peak f"))
    pr("-" * 118)
    for tag, _ in ROUTES:
        g = G[tag]
        e = g["e4"]
        fs = 1.0 / e["P"]
        fm = g["f_model"]
        d2 = np.r_[0.0, 0.0, e["cmd"][2:] - 2 * e["cmd"][1:-1] + e["cmd"][:-2]]
        hot100 = EPS[tag][1]
        hot = np.interp(e["t"], g["t"], hot100.astype(float)) > 0.5
        base = e["eng"] & (e["v"] < 12) & (np.abs(e["bar"]) < 400) & ~hot
        lo, hi = BAND[tag]
        for lab, m in (("baseline", base), ("grinding", e["eng"] & hot)):
            seg = [(a, b) for a, b in runs(m, 512)]
            if not seg:
                pr("%-10s %-9s %8d   (no run >= 512 ticks)" % (tag, lab, int(m.sum())))
                continue
            Pf, Pm, pk, pr_ = [], [], [], []
            for a, b in seg:
                r = welch_at(d2[a:b], fs, fm, lo - 4, hi + 4)
                if np.isfinite(r[0]):
                    Pf.append(r[0]); Pm.append(r[1]); pk.append(r[2]); pr_.append(r[3])
            if not Pf:
                continue
            pr("%-10s %-9s %8d %8.2f %9.5f %9.3g %9.3g %9.3f %9.4f" %
               (tag, lab, int(m.sum()), float(np.std(d2[m])), fm, float(np.mean(Pf)),
                float(np.mean(Pm)), float(np.mean(Pf) / np.mean(Pm)), float(np.median(pk))))
    pr()
    pr("MODEL-PHASE FOLD of |D2cmd| -- does the command's curvature knot land on the model clock?")
    pr("C = max(phase-bin mean) / overall mean over 5 bins (1.00 uniform, 5.00 perfect knot);")
    pr("R = amplitude-weighted Rayleigh concentration; NULL = the same with the clock detuned +0.37 Hz.")
    pr()
    pr("%-10s %-9s %8s %8s %8s %9s %9s" % ("route", "stratum", "ticks", "C", "C null", "R", "R null"))
    pr("-" * 118)
    for tag, _ in ROUTES:
        g = G[tag]
        e = g["e4"]
        d2 = np.r_[0.0, 0.0, e["cmd"][2:] - 2 * e["cmd"][1:-1] + e["cmd"][:-2]]
        ph = model_phase(g, e["t"])
        phn = (e["t"] - g["model_icept"]) * (g["f_model"] + 0.37)
        hot100 = EPS[tag][1]
        hot = np.interp(e["t"], g["t"], hot100.astype(float)) > 0.5
        base = e["eng"] & (e["v"] < 12) & (np.abs(e["bar"]) < 400) & ~hot
        for lab, m in (("baseline", base), ("grinding", e["eng"] & hot)):
            if m.sum() < 500:
                pr("%-10s %-9s %8d  (too few)" % (tag, lab, int(m.sum()))); continue
            C, R = fold_stats(np.abs(d2[m]), ph[m])
            Cn, Rn = fold_stats(np.abs(d2[m]), phn[m])
            pr("%-10s %-9s %8d %8.3f %8.3f %9.4f %9.4f" % (tag, lab, int(m.sum()), C, Cn, R, Rn))


# ======================================================================================================
# SECTION 4 -- the ring frequency against the model rate
# ======================================================================================================
def sec4(G, EPS):
    hr("SECTION 4 -- THE RING FREQUENCY vs MODELD'S RATE, ON THE SAME CLOCK")
    pr("Episodes are grind1_census_v282.py's recipe (2 s windows / 0.5 s step; present = peak prominence")
    pr(">= 8 AND in-band bar amplitude >= 40 raw; episode = contiguous >= 0.5 s present run inside an")
    pr("engaged run), with the search band widened per build per STATE.md's two-object picture.")
    pr("f0 is corrected from the k18 axis to device seconds by the factor 0.01/P18.")
    pr()
    pr("%-10s %-20s %7s %8s %9s %9s %9s %11s %11s" %
       ("route", "build", "n eps", "dur s", "f0 med", "f0 p25", "f0 p75", "CI lo-hi", "f_model"))
    pr("-" * 118)
    for tag, build in ROUTES:
        g = G[tag]
        eps, hot = EPS[tag]
        if not eps:
            pr("%-10s %-20s %7d" % (tag, build, 0)); continue
        corr = 0.01 / g["P18"]
        f0 = np.array([e[2] for e in eps]) * corr
        dur = np.array([(e[1] - e[0]) for e in eps]) * g["P18"]
        rng = np.random.default_rng(0xC0FFEE)
        bs = np.array([np.median(rng.choice(f0, size=len(f0))) for _ in range(4000)])
        pr("%-10s %-20s %7d %8.1f %9.4f %9.4f %9.4f %5.3f-%-5.3f %11.6f" %
           (tag, build, len(eps), dur.sum(), np.median(f0), np.percentile(f0, 25),
            np.percentile(f0, 75), np.percentile(bs, 2.5), np.percentile(bs, 97.5), g["f_model"]))
    pr()
    pr("Demand-gated high-demand subset (idx >= 20) -- STATE.md's separation of the grinding mode from")
    pr("the low-demand 12-14 Hz road line.")
    pr("%-10s %7s %9s %11s %11s %10s" % ("route", "n eps", "f0 med", "CI lo-hi", "f_model", "f0-f_model"))
    pr("-" * 118)
    for tag, _ in ROUTES:
        g = G[tag]
        eps, hot = EPS[tag]
        if not eps:
            continue
        idx, _ = GI.demand_live(np.round(g["cmd"]), g["bar"], None) if False else V.demand(np.round(g["cmd"]), g["bar"])
        corr = 0.01 / g["P18"]
        sel = [e for e in eps if np.median(idx[e[0]:e[1]]) >= 20]
        if len(sel) < 8:
            pr("%-10s %7d  (too few high-demand episodes)" % (tag, len(sel))); continue
        f0 = np.array([e[2] for e in sel]) * corr
        rng = np.random.default_rng(0xBEEF)
        bs = np.array([np.median(rng.choice(f0, size=len(f0))) for _ in range(4000)])
        pr("%-10s %7d %9.4f %5.3f-%-5.3f %11.6f %10.4f" %
           (tag, len(sel), np.median(f0), np.percentile(bs, 2.5), np.percentile(bs, 97.5),
            g["f_model"], np.median(f0) - g["f_model"]))


# ======================================================================================================
# SECTION 5 -- the phase-lock test
# ======================================================================================================
def bp_phase(x, fs, lo, hi):
    """instantaneous phase and envelope of the [lo,hi] component (zero-phase FIR + Hilbert)."""
    ntap = 257
    b = signal.firwin(ntap, [lo, hi], fs=fs, pass_zero=False)
    y = signal.filtfilt(b, [1.0], x - np.mean(x))
    z = signal.hilbert(y)
    return np.angle(z), np.abs(z)


def rayleigh(phi, w=None):
    if w is None:
        w = np.ones_like(phi)
    z = (w * np.exp(1j * phi)).sum() / max(w.sum(), 1e-30)
    return float(np.abs(z)), float(np.angle(z))


def block_null(phi, nblk):
    """R expected from nblk independent phasors = 1/sqrt(nblk) (Rayleigh distribution mean ~ .886/sqrt)."""
    return 1.0 / np.sqrt(max(nblk, 1))


def sec5(G, EPS):
    hr("SECTION 5 -- PHASE LOCK TO THE MODEL FRAME CLOCK  (THE DECISIVE DISCRIMINATOR)")
    pr("A FORCED line keeps a fixed phase against the clock that forces it, for as long as that clock")
    pr("runs.  A RESONANCE at a nearby frequency drifts: at |f_ring - f_model| = 0.03 Hz the phase turns")
    pr("through a full cycle every 33 s, so pooled over a route it averages to zero.")
    pr()
    pr("phi = (instantaneous phase of the band-passed channel) - 2*pi*(model frame index).  R is the")
    pr("amplitude-weighted circular concentration of phi.  The noise floor is 1/sqrt(n_blocks), with")
    pr("blocks of 1 s (longer than the mode's own coherence time 1/(2*zeta*f) ~ 0.3-0.8 s).")
    pr("dR = R(at f_model) - max R over the detuned reference clocks +-(0.15..0.60) Hz: a FORCED line")
    pr("makes dR strongly positive; anything else leaves R indistinguishable from its own detunings.")
    pr()
    pr("%-10s %-22s %-9s %7s %8s %8s %9s %9s %9s" %
       ("route", "channel", "stratum", "n s", "R", "floor", "R/floor", "max R det", "dR"))
    pr("-" * 118)
    DET = np.r_[np.arange(-0.60, -0.14, 0.05), np.arange(0.15, 0.61, 0.05)]
    for tag, _ in ROUTES:
        g = G[tag]
        eps, hot = EPS[tag]
        lo, hi = BAND[tag]
        fs18 = 1.0 / g["P18"]
        chans = [("0xE4 command", g["cmd"]), ("bar (driver torque)", g["bar"]),
                 ("wheel rate 0x18F", g["wire"].astype(float)), ("angle 0x14A", g["ang"])]
        # controlsState.desiredCurvature resampled onto the 0x18F axis -- the POSITIVE CONTROL
        M = g["M"]
        chans.insert(0, ("desiredCurvature*", np.interp(g["t"], M["cs_t"], M["cs_descurv"])))
        ph_model = 2 * np.pi * model_phase(g, g["t"])
        for name, x in chans:
            phx, amp = bp_phase(x, fs18, lo, hi)
            for lab, m in (("engaged", g["eng"]), ("grinding", g["eng"] & hot)):
                if m.sum() < 1000:
                    continue
                d = np.angle(np.exp(1j * (phx[m] - ph_model[m])))
                R, _ = rayleigh(d, amp[m])
                nblk = max(1, int(m.sum() * g["P18"]))
                fl = block_null(d, nblk)
                Rd = []
                for dd in DET:
                    phd = 2 * np.pi * (g["t"] - g["model_icept"]) * (g["f_model"] + dd)
                    Rd.append(rayleigh(np.angle(np.exp(1j * (phx[m] - phd[m]))), amp[m])[0])
                pr("%-10s %-22s %-9s %7.1f %8.4f %8.4f %9.2f %9.4f %+9.4f" %
                   (tag, name, lab, m.sum() * g["P18"], R, fl, R / fl, max(Rd), R - max(Rd)))
        pr("-" * 118)
    pr("* desiredCurvature is the POSITIVE CONTROL: it is generated ON the model clock, so if the method")
    pr("  can detect a lock anywhere it must detect it here.")


# ======================================================================================================
def main():
    G = {}
    for tag, build in ROUTES:
        pr("loading %s (%s) ..." % (tag, build))
        G[tag] = load(tag)
    EPS = {}
    for tag, _ in ROUTES:
        eps, hot = episodes_of(G[tag])
        EPS[tag] = (eps, hot)
        pr("  %s: %d episodes, %.1f s hot" % (tag, len(eps), hot.sum() * G[tag]["P18"]))
    sec1(G)
    sec2(G)
    sec3(G, EPS)
    sec4(G, EPS)
    sec5(G, EPS)
    with open(os.path.join(SCR, "modeld_cadence_vs_ring.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote", os.path.join(SCR, "modeld_cadence_vs_ring.txt"))


if __name__ == "__main__":
    main()
