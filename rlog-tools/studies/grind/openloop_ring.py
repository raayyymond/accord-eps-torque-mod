# -*- coding: utf-8 -*-
"""openloop_ring.py -- WHAT IS THE 18-22 Hz OBJECT'S DAMPING WITH THE LKAS RATE LOOP OPEN?
Subagent `openloop`, 2026-09-13.  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.

THE QUESTION.  A build that opens the LKAS rate loop above ~8 Hz stops the loop de-damping the
18-22 Hz object.  Whether that CURES the grinding or only shortens it depends on the mode's damping
with the loop OPEN, zeta_p.  The record holds two incompatible numbers (a loopshape extrapolation
zeta_p ~ 0.05, and the V290B plant family's 0.07/0.20/0.50) and neither is measured from the wire.

THE NATURAL EXPERIMENT.  Lateral-DISENGAGED time (0xE4 STEER_REQUEST = 0 AND 0x18F
STEER_CONTROL_ACTIVE = 0) is the LKAS rate loop OPEN: the EPS receives no LKAS command at all.  It is
not a clean open-loop test of the plant -- base assist is still closed around the same mechanics --
but it IS the configuration the proposed build approximates, and the record already establishes that
the 20 Hz object is engagement-gated on it.

SECTIONS
  A  EXPOSURE + replication of the 2026-09-10 engagement-gating result on 35 routes (it had 17)
  B  SAME OBJECT?  where the disengaged 12-26 Hz content actually sits, against the engaged line
  C  ZETA with the loop OPEN, three estimators, against ZETA engaged at matched speed
  D  AMPLITUDE, not rate: the load-matched disengaged/engaged ratio at 18-22 Hz, with CIs
Run: python openloop_ring.py [A B C D]
"""
import os
import pickle
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import openloop_lib as L                       # noqa: E402
import openloop_zeta as Z                      # noqa: E402
import openloop_census as CEN                  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
BINS = ((0, 4), (4, 8), (8, 13), (13, 18), (18, 25), (25, 40))
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def save(name="openloop_ring.txt"):
    with open(os.path.join(L.SCR, name), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")


_ROWS = None


def rows():
    global _ROWS
    if _ROWS is None:
        with open(CEN.PKL, "rb") as fh:
            _ROWS = pickle.load(fh)
    return _ROWS


def segs(tag, want_eng, vlo=None, vhi=None, idxmin=None, minlen=1024, chan="bar",
         press=None):
    """contiguous sample segments of one route satisfying the stratum, at least minlen long."""
    g = L.load(tag)
    m = (g["eng"] if want_eng else g["off"]) & g["have"]
    if vlo is not None:
        m &= (g["vego"] >= vlo) & (g["vego"] < vhi)
    if idxmin is not None:
        m &= g["idx"] >= idxmin
    if press is not None:
        m &= (g["press"] > 0.5) if press else (g["press"] <= 0.5)
    x = {"bar": g["bar"], "rate": g["rate_dps"], "ang": g["ang"], "cmd": g["cmd"]}[chan]
    return [signal.detrend(x[a:b]) for a, b in L.runs(m, minlen)]


def pool_segs(tags, **kw):
    out = []
    for t in tags:
        out += segs(t, **kw)
    return out


# ==============================================================================================
def secA():
    R = rows()
    E = [r for r in R if r["eng"]]
    D = [r for r in R if not r["eng"]]
    pr("=" * 122)
    pr("SECTION A -- EXPOSURE, AND THE ENGAGEMENT GATING REPLICATED ON 35 ROUTES")
    pr("=" * 122)
    pr("2 s windows / 0.5 s step, ENTIRELY lateral-engaged or ENTIRELY lateral-OFF.  'Lateral engaged'")
    pr("= 0x18F STEER_CONTROL_ACTIVE AND 0xE4 STEER_REQUEST (the kit's canonical definition).")
    pr("LEVEL gate = prominence >= 8 in 12-26 Hz AND bar band amplitude (f0 +- 2 Hz) >= 40 raw.")
    pr("The 2026-09-10 run had 20,761 engaged / 5,905 OFF over 17 routes; this has:")
    pr("  %d engaged, %d lateral-OFF, %d routes" % (len(E), len(D), len(set(r["tag"] for r in R))))
    pr()
    lvl = lambda r: r["pw"] >= 8 and r["A"] >= 40                     # noqa: E731
    hi = lambda r: r["ph"] >= 8 and r["A_bar_hi"] >= 40               # noqa: E731  18-22 BAND-SPECIFIC
    pr("A1 -- speed-stratified, pooled.  'hi gate' is BAND-SPECIFIC: prominence >= 8 inside 17-23 Hz")
    pr("      AND >= 40 raw of 18-22 Hz bar amplitude -- the gate the 12-14 Hz road line cannot pass.")
    pr("  %-10s | %7s %8s %8s %7s | %7s %8s %8s %7s | %s"
       % ("speed m/s", "n_eng", "lvl", "hi gate", "f0 lvl", "n_OFF", "lvl", "hi gate", "f0 lvl", "hi ratio"))
    for lo, hiv in BINS:
        e = [r for r in E if lo <= r["v"] < hiv]
        d = [r for r in D if lo <= r["v"] < hiv]
        el, eh = [r for r in e if lvl(r)], [r for r in e if hi(r)]
        dl, dh = [r for r in d if lvl(r)], [r for r in d if hi(r)]
        re_, rd = len(eh) / max(1, len(e)), len(dh) / max(1, len(d))
        pr("  %4.0f-%-5.0f | %7d %8.4f %8.4f %7.1f | %7d %8.4f %8.4f %7.1f | %s"
           % (lo, hiv, len(e), len(el) / max(1, len(e)), re_,
              float(np.median([r["f0w"] for r in el])) if el else np.nan,
              len(d), len(dl) / max(1, len(d)), rd,
              float(np.median([r["f0w"] for r in dl])) if dl else np.nan,
              ("%.1fx" % (re_ / rd)) if rd > 0 else (">= %.0fx" % (re_ * len(d) / 3.0) if d and re_ else "-")))
    pr()
    pr("A2 -- LOAD-MATCHED (OFF windows restricted, inside each speed bin, to the ENGAGED interquartile")
    pr("      range of BOTH driver-torque rms and wheel-rate rms), on the 18-22 Hz gate")
    pr("  %-10s | %6s %7s %7s %7s | %6s %7s %7s %7s | %s"
       % ("speed m/s", "n_eng", "hi", "barRMS", "rateRMS", "n_OFF", "hi", "barRMS", "rateRMS", "ratio"))
    global MATCHED
    MATCHED = {}
    for lo, hiv in BINS:
        e = [r for r in E if lo <= r["v"] < hiv]
        d = [r for r in D if lo <= r["v"] < hiv]
        if not e or not d:
            pr("  %4.0f-%-5.0f | %6d %7s %7s %7s | %6d  no exposure" % (lo, hiv, len(e), "-", "-", "-", len(d)))
            continue
        bq = np.percentile([r["barrms"] for r in e], [25, 75])
        rq = np.percentile([r["raterms"] for r in e], [25, 75])
        dm = [r for r in d if bq[0] <= r["barrms"] <= bq[1] and rq[0] <= r["raterms"] <= rq[1]]
        MATCHED[(lo, hiv)] = (e, dm)
        eh = [r for r in e if hi(r)]
        dh = [r for r in dm if hi(r)]
        re_ = len(eh) / len(e)
        rd = len(dh) / max(1, len(dm))
        pr("  %4.0f-%-5.0f | %6d %7.4f %7.1f %7.1f | %6d %7s %7s %7s | %s"
           % (lo, hiv, len(e), re_, np.median([r["barrms"] for r in e]), np.median([r["raterms"] for r in e]),
              len(dm), ("%.4f" % rd) if dm else "-",
              ("%.1f" % np.median([r["barrms"] for r in dm])) if dm else "-",
              ("%.1f" % np.median([r["raterms"] for r in dm])) if dm else "-",
              ("%.1fx" % (re_ / rd)) if rd > 0 else (">= %.0fx" % (re_ * len(dm) / 3.0) if dm and re_ else "-")))
    pr()
    pr("A3 -- per route (18-22 Hz gate), so no single route carries the pooled result")
    pr("  %-10s %-9s | %6s %7s | %6s %7s %7s | %s"
       % ("route", "build", "n_eng", "hi eng", "n_OFF", "hi OFF", "OFF secs", "max OFF v"))
    for t in sorted(set(r["tag"] for r in R)):
        e = [r for r in E if r["tag"] == t]
        d = [r for r in D if r["tag"] == t]
        eh = [r for r in e if hi(r)]
        dh = [r for r in d if hi(r)]
        pr("  %-10s %-9s | %6d %7.4f | %6d %7.4f %7.0f | %.1f"
           % (t, L.BUILD.get(t, "?"), len(e), len(eh) / max(1, len(e)), len(d),
              len(dh) / max(1, len(d)), len(d) * 0.5,
              max([r["v"] for r in d]) if d else np.nan))


# ==============================================================================================
def secB():
    R = rows()
    E = [r for r in R if r["eng"]]
    D = [r for r in R if not r["eng"]]
    pr()
    pr("=" * 122)
    pr("SECTION B -- IS THE DISENGAGED 12-26 Hz CONTENT THE SAME OBJECT?")
    pr("=" * 122)
    pr("B1 -- where the most prominent 12-26 Hz line sits, by label and speed (median f0, and the")
    pr("      fraction of windows whose line falls in 18-22 vs 12-14.5 Hz).  No level gate: this is")
    pr("      a question about SHAPE, and a level gate would pre-select the engaged answer.")
    pr("  %-10s | %-38s | %-38s" % ("speed m/s", "LATERAL ENGAGED", "LATERAL OFF"))
    pr("  %-10s | %6s %7s %7s %7s | %6s %7s %7s %7s"
       % ("", "n", "med f0", "f0 in", "f0 in", "n", "med f0", "f0 in", "f0 in"))
    pr("  %-10s | %6s %7s %7s %7s | %6s %7s %7s %7s"
       % ("", "", "", "18-22", "12-14.5", "", "", "18-22", "12-14.5"))
    for lo, hiv in BINS:
        out = []
        for S in (E, D):
            s = [r for r in S if lo <= r["v"] < hiv and r["pw"] >= 8]
            if not s:
                out.append((0, np.nan, np.nan, np.nan))
                continue
            f0 = np.array([r["f0w"] for r in s])
            out.append((len(s), float(np.median(f0)), float(np.mean((f0 >= 18) & (f0 <= 22))),
                        float(np.mean((f0 >= 12) & (f0 <= 14.5)))))
        pr("  %4.0f-%-5.0f | %6d %7.2f %7.3f %7.3f | %6d %7.2f %7.3f %7.3f"
           % ((lo, hiv) + out[0] + out[1]))
    pr()
    pr("B2 -- POOLED SPECTRA.  Welch (nperseg 1024 = 10.24 s, Hann, 50 %% overlap) over every")
    pr("      contiguous run of the stratum, weighted by run length.  Amplitude density, arbitrary")
    pr("      units per channel; what matters is the SHAPE and where the peak sits.")
    tags = L.routes()
    for chan, unit in (("bar", "raw torque"), ("rate", "deg/s")):
        pr()
        pr("  channel = %s (%s)" % (chan, unit))
        pr("    %-22s %7s | %s" % ("stratum", "secs", "  ".join("%5.1f" % f for f in
                                                                (12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 26, 30))))
        for lab, kw in (("ENGAGED 0-8 m/s", dict(want_eng=True, vlo=0, vhi=8)),
                        ("ENGAGED 0-8 idx>=20", dict(want_eng=True, vlo=0, vhi=8, idxmin=20)),
                        ("OFF     0-8 m/s", dict(want_eng=False, vlo=0, vhi=8)),
                        ("ENGAGED 8-25 m/s", dict(want_eng=True, vlo=8, vhi=25)),
                        ("OFF     8-25 m/s", dict(want_eng=False, vlo=8, vhi=25))):
            ss = pool_segs(tags, chan=chan, **kw)
            f, P, W = Z.pooled_psd(ss, 1024)
            if f is None:
                pr("    %-22s %7s | no exposure" % (lab, "-"))
                continue
            A = np.sqrt(P)
            pr("    %-22s %7.0f | %s" % (lab, W / FS, "  ".join(
                "%5.3g" % np.interp(x, f, A) for x in (12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 26, 30))))


# ==============================================================================================
# SECTION C -- rebuilt around E3b.  See openloop_zeta2.py for the controls that forced the rebuild:
#   * a bare Lorentzian parks f0 on the window edge when there is no line -> E3b models the
#     background as a power law, confines f0 to the interior, and reports `bump` = max(model/bg).
#   * pooling a PSD across speeds inflates zeta x1.1 (0.25 Hz of f0 spread) to x3.8 (2 Hz)
#     -> every stratum below is 2 m/s wide, and the record measures df0/dv at 0.11-0.21 Hz per m/s,
#        so a 2 m/s bin carries <= 0.42 Hz of spread, i.e. <= x1.3 of inflation.
# ==============================================================================================
VB = ((0, 4), (4, 8), (8, 12), (12, 16), (16, 20), (20, 26))
# lateral-OFF is thin above 4 m/s (98 s at 4-8, 431 s at 8-26 in segments >= 10.24 s), so it also
# gets pooled rows.  A wider bin costs f0-spread inflation (controls: x1.05 at 0.25 Hz of spread,
# x1.20 at 0.5, x1.60 at 1.0), and the record measures df0/dv at 0.11-0.21 Hz per m/s, so a 4 m/s
# bin carries <= 0.84 Hz and <= ~x1.5.  Inflation biases zeta UP, i.e. AGAINST "the loop open is
# still lightly damped", so a LOW zeta on a wide bin is conservative and a HIGH one is not.
VB_OFF = ((0, 4), (4, 8), (8, 26), (0, 26))
NPER = 1024                     # 10.24 s -> Welch ENBW 0.146 Hz -> resolvable zeta floor ~0.0035
BUMP_MIN = 1.8                  # the no-mode controls top out at bump 1.48 / prom 1.39


def _zrow(lab, ss, flo, fhi, nboot=40, e2=True, nper=None):
    nper = nper or NPER
    if len(ss) < 3:
        pr("  %-34s | %6s %4d | %s" % (lab, "-", len(ss), "no exposure (< 3 segments)"))
        return None
    r = Z.zeta_line(ss, flo, fhi, nper, nboot=nboot, seed=7)
    f0 = r["f0"] if np.isfinite(r["f0"]) else 0.5 * (flo + fhi)
    e2r = Z.zeta_coh(ss, f0, HB=3.0, nboot=0) if (e2 and f0 > 4) else dict(z=np.nan)
    e1r = Z.zeta_decay(ss, f0) if f0 > 4 else dict(z=np.nan)
    line = (r["bump"] >= BUMP_MIN) and (r["prom_data"] >= BUMP_MIN) and (not r["edge"])
    flag = "LINE" if line else "NO LINE"
    if line and r.get("atfloor"):
        flag = "LINE<=res"
    pr("  %-34s | %6.0f %4d | %6.3f %7.4f [%6.4f %6.4f] %6.2f %6.2f %7.0f %8s | %7.4f %7.4f"
       % (lab, r["secs"], r["nseg"], r["f0"], r["z"], r["lo"], r["hi"],
          min(r["bump"], 9999.0), min(r["prom_data"], 9999.0), max(r["dAIC"], -99999.0), flag,
          e2r["z"], e1r["z"]))
    return r


def _hdr():
    pr("  %-34s | %6s %4s | %6s %7s %-15s %6s %6s %7s %8s | %7s %7s"
       % ("stratum", "secs", "nseg", "f0 fit", "E3b z", "[95% CI]", "bump", "prom", "dAIC",
          "verdict", "E2 z", "E1 z"))
    pr("-" * 140)


def secC():
    tags = L.routes()
    pr()
    pr("=" * 140)
    pr("SECTION C -- ZETA OF THE 18-22 Hz OBJECT WITH THE LKAS RATE LOOP OPEN")
    pr("=" * 140)
    pr("E3b = background-pinned Lorentzian fit to the pooled Welch PSD, nperseg %d (%.2f s), f0 confined"
       % (NPER, NPER / FS))
    pr("  to the window interior.  ESTIMATOR OF RECORD.  Controls: _scratch/openloop_zeta2_controls.txt.")
    pr("  Bias at 0 dB in-band SNR: x0.87-1.16 for true zeta 0.005-0.05, then it UNDER-reads (x0.75 at")
    pr("  0.10, x0.47 at 0.20, x0.33 at 0.30).  Under-reading is conservative for this question: a HIGH")
    pr("  measured zeta means the truth is higher still.")
    pr("  FALSIFIERS, both required for a LINE verdict: `bump` = fitted peak/background, and the")
    pr("  MODEL-FREE `prom` = max(P within +-1 Hz of f0) / median(P over the window).  On the no-mode")
    pr("  controls both sit at 1.26-1.48 and dAIC is only -4.4.  Threshold %.1f, plus f0 not on an edge." % BUMP_MIN)
    pr("E2 = the record's coherence time.  Usable 0.01-0.05; SATURATES above (no-mode control 0.0527).")
    pr("E1 = the record's free-decay estimator.  FAILED its control: 0.036-0.040 for NO MODE and for")
    pr("  every true zeta 0.05-0.30.  Printed only for comparability with DESIGN-V290B A.2.")
    pr()
    pr("-" * 140)
    pr("C1 -- FIT WINDOW 16-26 Hz, channel = driver torque `bar`, ALL 35 ROUTES")
    _hdr()
    for lab, we in (("ENGAGED", True), ("OFF *LOOP OPEN*", False)):
        for vlo, vhi in (VB if we else VB_OFF):
            _zrow("%-15s %2d-%-2d m/s" % (lab, vlo, vhi),
                  pool_segs(tags, chan="bar", want_eng=we, vlo=vlo, vhi=vhi, minlen=NPER), 16.0, 26.0)
        pr()
    pr("-" * 140)
    pr("C2 -- the same on the WHEEL RATE channel (0x18F STEER_ANGLE_RATE, 0.125 deg/s LSB)")
    _hdr()
    for lab, we in (("ENGAGED", True), ("OFF *LOOP OPEN*", False)):
        for vlo, vhi in (VB if we else VB_OFF):
            _zrow("%-15s %2d-%-2d m/s" % (lab, vlo, vhi),
                  pool_segs(tags, chan="rate", want_eng=we, vlo=vlo, vhi=vhi, minlen=NPER), 16.0, 26.0)
        pr()
    pr("-" * 140)
    pr("C3 -- POSITIVE CONTROL ON REAL DATA: the 10-16 Hz road/plant line.  The record says this line")
    pr("      is NOT engagement-gated.  If E3b finds it on BOTH labels, the machinery can see a plant")
    pr("      mode in lateral-disengaged data -- which is what C1/C2's nulls need before they mean")
    pr("      anything.  A null here would mean the instrument, not the car, is the reason.")
    _hdr()
    for lab, we in (("ENGAGED", True), ("OFF *LOOP OPEN*", False)):
        for vlo, vhi in ((0, 4), (4, 8), (8, 26), (0, 26)):
            _zrow("%-15s %2d-%-2d m/s road line" % (lab, vlo, vhi),
                  pool_segs(tags, chan="bar", want_eng=we, vlo=vlo, vhi=vhi, minlen=NPER), 10.0, 16.0)
        pr()
    pr("-" * 140)
    pr("C4 -- PER BUILD.  Engaged creep is the grinding stratum; the OFF row is the same car with the")
    pr("      LKAS rate loop open.  Cross-check of E3b against the record's coherence-time zeta")
    pr("      (0.0091-0.0224 per build) and against DESIGN-V290B A.2's free-decay anchors.")
    _hdr()
    for b, ts in (("stock", ["r97"]), ("V112", ["r22", "r23"]), ("V278r3", ["r31"]),
                  ("V280r2", ["r32", "r33", "r34"]), ("V281r3", ["r35"]),
                  ("V282", ["r39", "r3a", "r3c"]), ("V288r2", ["r5e_v288"]),
                  ("V289r1", ["r62_v289", "r63_v289"])):
        band = (12.0, 22.0) if b == "V289r1" else (16.0, 26.0)
        _zrow("%-8s ENGAGED 0-8 m/s" % b,
              pool_segs(ts, chan="bar", want_eng=True, vlo=0, vhi=8, minlen=NPER), band[0], band[1])
        _zrow("%-8s OFF     0-26 m/s loop open" % b,
              pool_segs(ts, chan="bar", want_eng=False, minlen=NPER), 16.0, 26.0)
        pr()
    pr("-" * 140)
    pr("C5 -- DETECTION POWER: what the disengaged null actually EXCLUDES.")
    pr("      A synthetic mode of KNOWN zeta at 20.0 Hz is ADDED to the REAL lateral-OFF segments at")
    pr("      0-4 m/s, scaled so its 18-22 Hz band amplitude is a stated fraction of the ENGAGED")
    pr("      18-22 Hz ring amplitude on the same channel.  Every Y row is a (zeta, amplitude) pair")
    pr("      that IS detectable in this data and is therefore EXCLUDED by the real null.")
    pr()
    for chan in ("bar", "rate"):
        off = pool_segs(tags, chan=chan, want_eng=False, vlo=0, vhi=4, minlen=NPER)
        eng = pool_segs(tags, chan=chan, want_eng=True, vlo=0, vhi=4, minlen=NPER)
        Aeng = float(np.median([np.sqrt(2) * np.std(L.bp(x, 18, 22)) for x in eng]))
        Aoff = float(np.median([np.sqrt(2) * np.std(L.bp(x, 18, 22)) for x in off]))
        r0 = Z.zeta_line(off, 16.0, 26.0, NPER)
        pr("  channel %-5s : ENGAGED 18-22 amplitude %.4f, lateral-OFF %.4f (ratio %.4f); %d OFF segs, %.0f s"
           % (chan, Aeng, Aoff, Aoff / Aeng, len(off), sum(len(x) for x in off) / FS))
        pr("    REAL lateral-OFF, nothing injected : z %7.4f  f0 %6.3f  bump %5.2f  prom %5.2f  -> %s"
           % (r0["z"], r0["f0"], r0["bump"], r0["prom_data"],
              "LINE" if (r0["bump"] >= BUMP_MIN and r0["prom_data"] >= BUMP_MIN and not r0["edge"]) else "NO LINE"))
        pr("    %-10s | %s" % ("injected z", "  ".join("%-24s" % ("amp %.2f x engaged" % fr)
                                                       for fr in (1.0, 0.5, 0.25, 0.10))))
        for zt in (0.010, 0.030, 0.050, 0.100, 0.200, 0.300, 0.500):
            cells = []
            for fr in (1.0, 0.5, 0.25, 0.10):
                rr = Z.zeta_line(Z.inject(off, zt, 20.0, Aeng * fr, seed=int(zt * 1e4)), 16.0, 26.0, NPER)
                det = (rr["bump"] >= BUMP_MIN) and (rr["prom_data"] >= BUMP_MIN) and (not rr["edge"])
                cells.append("z %6.4f bmp %5.2f %s" % (rr["z"], min(rr["bump"], 999.0), "Y" if det else "n"))
            pr("    %-10.3f | %s" % (zt, "  ".join("%-24s" % c for c in cells)))
        pr()
    pr("  Y = E3b would have called it a line in this exact data.  n = it would not.")


# ==============================================================================================
def secD():
    pr()
    pr("=" * 122)
    pr("SECTION D -- AMPLITUDE, NOT RATE: the load-matched 18-22 Hz amplitude disengaged vs engaged")
    pr("=" * 122)
    pr("The record's x33-x72 is a PRESENCE RATE.  This is the AMPLITUDE ratio: median 18-22 Hz band")
    pr("amplitude (sqrt(2)*std of a 4th-order zero-phase Butterworth) over the windows of each label,")
    pr("with the OFF windows load-matched to the engaged interquartile range of BOTH driver-torque rms")
    pr("and wheel-rate rms inside each speed bin.  Ratio CI is a 4000-sample bootstrap of the ratio of")
    pr("medians, resampling both labels independently.")
    pr()
    R = rows()
    E = [r for r in R if r["eng"]]
    D = [r for r in R if not r["eng"]]
    rng = np.random.default_rng(11)
    for ch, unit in (("bar", "raw driver torque"), ("rate", "deg/s wheel rate"), ("ang", "deg")):
        pr("  channel %s (%s)" % (ch, unit))
        pr("    %-10s | %6s %10s | %6s %10s | %-24s | %s"
           % ("speed m/s", "n_eng", "A eng", "n_OFF", "A OFF", "ratio OFF/eng [95% CI]", "neighbour 26-34 ratio"))
        for lo, hiv in BINS:
            e = [r for r in E if lo <= r["v"] < hiv]
            d = [r for r in D if lo <= r["v"] < hiv]
            if not e or not d:
                pr("    %4.0f-%-5.0f | %6d %10s | %6d  no exposure" % (lo, hiv, len(e), "-", len(d)))
                continue
            bq = np.percentile([r["barrms"] for r in e], [25, 75])
            rq = np.percentile([r["raterms"] for r in e], [25, 75])
            dm = [r for r in d if bq[0] <= r["barrms"] <= bq[1] and rq[0] <= r["raterms"] <= rq[1]]
            if len(dm) < 10:
                pr("    %4.0f-%-5.0f | %6d %10.3f | %6d  matched n < 10" % (lo, hiv, len(e),
                   np.median([r["A_%s_hi" % ch] for r in e]), len(dm)))
                continue
            a = np.array([r["A_%s_hi" % ch] for r in e])
            b = np.array([r["A_%s_hi" % ch] for r in dm])
            an = np.array([r["A_%s_nb" % ch] for r in e])
            bn = np.array([r["A_%s_nb" % ch] for r in dm])
            bs = np.array([np.median(b[rng.integers(0, len(b), len(b))])
                           / np.median(a[rng.integers(0, len(a), len(a))]) for _ in range(4000)])
            pr("    %4.0f-%-5.0f | %6d %10.4f | %6d %10.4f | %.4f [%.4f %.4f]%s | %.4f"
               % (lo, hiv, len(e), np.median(a), len(dm), np.median(b),
                  np.median(b) / np.median(a), np.percentile(bs, 2.5), np.percentile(bs, 97.5),
                  "    ", np.median(bn) / np.median(an)))
        pr()
    pr("  READ: the NEIGHBOUR-band (26-34 Hz) ratio is the control.  If the 18-22 ratio and the 26-34")
    pr("  ratio are the same, the two labels differ in BROADBAND level and nothing specific to the mode")
    pr("  has been shown.  A mode-specific effect is 18-22 ratio << 26-34 ratio.")


if __name__ == "__main__":
    for s in (sys.argv[1:] or ["A", "B", "C", "D"]):
        globals()["sec%s" % s]()
    save()
