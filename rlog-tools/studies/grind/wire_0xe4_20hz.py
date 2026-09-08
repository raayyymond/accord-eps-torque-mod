# -*- coding: utf-8 -*-
"""studies/grind/wire_0xe4_20hz.py -- is the 18-22 Hz grind #1 line PRESENT IN the 0xE4 steer command
itself, or only RUNG BY it?  Subagent `wire`, 2026-09-07.  ANALYSIS ONLY: builds nothing, sends nothing.

Outside observer's claim under test: "openpilot's latcontrol has no low-pass; it emits a 20 Hz stairstep
command held for 4 frames and sent at 100 Hz; Honda's EPS does exactly what it is told."

Routes r39 / r3a / r3c (all V282), caches analysis-2020accord/_scratch/cache/v280/*.npz, loaded through
creep20_loop_id.load() (dejittered nominal frame clocks; "eng" = LATERAL engaged = 0x18F
STEER_CONTROL_ACTIVE AND 0xE4 STEER_REQUEST).  Episode detection is grind1_census_v282.py's recipe
verbatim (2 s windows / 0.5 s step, present = 15-26 Hz peak prominence >= 8 AND bar 18-22 >= 40 raw,
episode = contiguous >= 0.5 s present run inside an engaged run).

Sections
  1  CADENCE      raw 0xE4 value-change cadence, step-size distribution, rate limit, episodes vs baseline
  2  SPECTRUM     PSD of cmd on its OWN dejittered clock (no resampling) + bar/rate/ang/T; fine f0
  3  CAUSALITY    coherence & cross-phase cmd<->bar/rate/ang/T at the line; the openpilot angle->cmd
                  gain model; the 100 Hz update comb
  4  CONTRIBUTION the 1 kHz FUN_00028ea6 mirror re-run with cmd low-passed below 15 Hz -- how much of
                  T's 18-22 Hz content is the command's own 20 Hz, vs the feedback's
  5  DOSES        offline setpoint filters: first-order IIR at 1 kHz (fc 10/15/20/30 Hz) and the 10-tick
                  linear interpolation -- 18-22 Hz removal, per-tick D kick, group delay at 1-3 Hz
  6  ALIAS        what 100 Hz sampling of 0xE4 can and cannot exclude

Run: python wire_0xe4_20hz.py      (writes _scratch/wire_0xe4_20hz.txt beside it)
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
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import v280_map_profiles as V                 # noqa: E402
import grind_incident_r35 as GI               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K, FST = 100.0, 1000.0, 50.0
W, STEP = 200, 50
ROUTES = ("r39", "r3a", "r3c")
V282_IMG = (LG.FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-"
                    "MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
LO, HI = 18.0, 22.0
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


# ======================================================================================================
# loading
# ======================================================================================================
def load_route(tag, cells):
    """C20.load + the raw (unresampled) 0xE4 stream on its own dejittered clock + episode covariates."""
    g = C20.load(tag)
    g["tr"] = g["t"] - g["t"][0]
    g["idx"], _ = GI.demand_live(np.round(g["cmd"]), g["bar"], cells)
    g["rate"] = np.abs(g["wire"]) / V.CPD
    D = dict(np.load(os.path.join(C20.CACHE, tag + ".npz")))
    ke4, Pe4, tne4, rese4 = C20.dejitter(D["te4"], 0.01, 100)
    k18, P18, tn18, _ = C20.dejitter(D["t18"], 0.01, 100)
    e = dict(k=ke4, P=Pe4, t=tne4, cmd=D["cmd"].astype(float), req=D["req"].astype(int) > 0,
             resid=rese4)
    e["sca"] = np.interp(tne4, tn18, D["sca"].astype(float)) > 0.5
    e["eng"] = e["req"] & e["sca"]
    # uniform-in-k grid of the RAW command (gaps flagged, not interpolated over for cadence work)
    K = int(ke4[-1])
    grid = np.full(K + 1, np.nan)
    grid[ke4] = e["cmd"]
    have = ~np.isnan(grid)
    eg = np.zeros(K + 1, bool)
    eg[ke4] = e["eng"]
    filled = grid.copy()
    filled[~have] = np.interp(np.flatnonzero(~have), np.flatnonzero(have), grid[have])
    e["grid"], e["have"], e["egrid"], e["K"] = filled, have, eg & have, K
    e["tgrid"] = np.interp(np.arange(K + 1), ke4, tne4)
    g["e4"] = e
    g["ang14_t"] = D["t14"]
    g["ang14"] = D["ang"].astype(float)
    return g


def episodes_of(g):
    """grind1_census_v282.py's episode recipe, verbatim in substance."""
    wt, wp = [], []
    for aa, bb in C20.runs(g["eng"], W):
        for s in range(aa, bb - W + 1, STEP):
            e = s + W
            f0w, prom, _, _ = GI.line_of(g["bar"][s:e], FS, 15.0, 26.0)
            amp = GI.band(g["bar"][s:e], LO, HI, FS)
            wt.append(g["tr"][s])
            wp.append((prom >= 8) and (amp >= 40))
    wt, wp = np.array(wt), np.array(wp, bool)
    j = np.clip(np.searchsorted(wt, g["tr"] - 1.0), 0, len(wt) - 1)
    near = np.abs(wt[j] + 1.0 - g["tr"]) < 1.5
    hot = g["eng"] & near & wp[j]
    eps = []
    for a, b in C20.runs(hot, int(0.5 * FS)):
        f0, prom, _, _ = GI.line_of(g["bar"][a:b], FS, 15.0, 26.0)
        if np.isfinite(f0):
            eps.append((a, b, f0))
    return eps, hot


# ======================================================================================================
# helpers
# ======================================================================================================
def fine_line(x, fs, lo, hi, nfft=1 << 16):
    """peak frequency of a zero-padded periodogram in [lo,hi], with a 3-point parabolic refine."""
    x = np.asarray(x, float)
    x = x - x.mean()
    w = np.hanning(len(x))
    X = np.abs(np.fft.rfft(x * w, n=max(nfft, len(x)))) ** 2
    f = np.fft.rfftfreq(max(nfft, len(x)), 1.0 / fs)
    sel = (f >= lo) & (f <= hi)
    i = np.flatnonzero(sel)[np.argmax(X[sel])]
    if 0 < i < len(X) - 1:
        y0, y1, y2 = np.log(X[i - 1] + 1e-30), np.log(X[i] + 1e-30), np.log(X[i + 1] + 1e-30)
        d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2) if (y0 - 2 * y1 + y2) != 0 else 0.0
        return float(f[i] + d * (f[1] - f[0])), float(X[i])
    return float(f[i]), float(X[i])


def bandamp(x, fs, lo, hi):
    """rms-equivalent single-sided amplitude in [lo,hi] -- the kit's GI.band, generalised in fs."""
    return GI.band(np.asarray(x, float), lo, hi, fs)


def welch_pool(segs, fs, nperseg):
    """length-weighted pooled Welch PSD over a list of 1-D segments."""
    P, f, n = None, None, 0
    for x in segs:
        if len(x) < nperseg:
            continue
        f, p = signal.welch(x - np.mean(x), fs=fs, nperseg=nperseg, detrend="linear")
        P = p * len(x) if P is None else P + p * len(x)
        n += len(x)
    return (f, P / n, n) if n else (None, None, 0)


def csd_pool(segs_a, segs_b, fs, nperseg):
    """pooled auto/cross spectra -> (f, coherence, phase_deg of A relative to B, |Txy| gain A/B)."""
    Saa = Sbb = Sab = None
    n = 0
    for xa, xb in zip(segs_a, segs_b):
        if len(xa) < nperseg:
            continue
        xa = xa - np.mean(xa)
        xb = xb - np.mean(xb)
        f, paa = signal.csd(xa, xa, fs=fs, nperseg=nperseg, detrend="linear")
        _, pbb = signal.csd(xb, xb, fs=fs, nperseg=nperseg, detrend="linear")
        _, pab = signal.csd(xa, xb, fs=fs, nperseg=nperseg, detrend="linear")
        Saa = paa * len(xa) if Saa is None else Saa + paa * len(xa)
        Sbb = pbb * len(xa) if Sbb is None else Sbb + pbb * len(xa)
        Sab = pab * len(xa) if Sab is None else Sab + pab * len(xa)
        n += len(xa)
    if not n:
        return None, None, None, None, 0
    coh = np.abs(Sab) ** 2 / (np.real(Saa) * np.real(Sbb) + 1e-30)
    ph = np.degrees(np.angle(Sab))
    gain = np.abs(Sab) / (np.real(Sbb) + 1e-30)
    return f, np.real(coh), ph, gain, n


def at(f, y, f0):
    return float(np.interp(f0, f, y))


def circ_at(f, ph, f0):
    """phase interpolation on the unit circle."""
    z = np.exp(1j * np.radians(ph))
    return float(np.degrees(np.angle(np.interp(f0, f, z.real) + 1j * np.interp(f0, f, z.imag))))


# ======================================================================================================
def main():
    cells = GI.read_cells(V282_IMG)
    G = {t: load_route(t, cells) for t in ROUTES}
    EP = {}
    for t in ROUTES:
        eps, hot = episodes_of(G[t])
        EP[t] = eps
        G[t]["hot"] = hot
        print("loaded %s: %.0f s, %.0f s engaged, %d episodes" %
              (t, G[t]["tr"][-1], G[t]["eng"].sum() / FS, len(eps)), flush=True)

    pr("=" * 150)
    pr("IS THE 18-22 Hz GRIND #1 LINE IN THE 0xE4 STEER COMMAND?  --  V282 wire read (r39, r3a, r3c)")
    pr("script wire_0xe4_20hz.py, subagent `wire`, 2026-09-07.  Analysis only.")
    pr("=" * 150)

    # ==================================================================================== 1. CADENCE
    pr("\n" + "=" * 150)
    pr("1. COMMAND CADENCE -- raw 0xE4 STEER_TORQUE, its own dejittered frame clock, lateral-engaged only")
    pr("=" * 150)
    pr("\n1a. Frame period and value-change cadence")
    pr("  %-5s %10s %9s %9s %9s | %s" % ("route", "P_e4 ms", "n eng", "chg/frame", "eff Hz",
                                         "frames-between-changes: 1 / 2 / 3 / 4 / 5 / >=6"))
    CAD = {}
    for tag in ROUTES:
        e = G[tag]["e4"]
        m = e["egrid"]
        d = np.diff(e["grid"])
        ok = m[1:] & m[:-1] & e["have"][1:] & e["have"][:-1]
        dd = d[ok]
        chg = np.mean(dd != 0)
        ch = np.flatnonzero(dd != 0)
        gaps = np.diff(ch) if len(ch) > 2 else np.array([1])
        h = [np.mean(gaps == k) for k in (1, 2, 3, 4, 5)] + [np.mean(gaps >= 6)]
        CAD[tag] = dict(d=dd, gaps=gaps, ok=ok)
        pr("  %-5s %10.5f %9d %9.3f %9.1f | %s" % (
            tag, e["P"] * 1000, ok.sum(), chg, chg / e["P"],
            " / ".join("%.3f" % v for v in h)))
    pooled = np.concatenate([CAD[t]["d"] for t in ROUTES])
    pgaps = np.concatenate([CAD[t]["gaps"] for t in ROUTES])
    pr("  %-5s %10s %9d %9.3f %9s | %s" % (
        "POOL", "-", len(pooled), np.mean(pooled != 0), "-",
        " / ".join("%.3f" % np.mean(pgaps == k) for k in (1, 2, 3, 4, 5)) +
        " / %.3f" % np.mean(pgaps >= 6)))
    pr("\n  => The command changes value on %.1f %% of engaged 100 Hz frames.  A '20 Hz stairstep held for"
       % (100 * np.mean(pooled != 0)))
    pr("     4-5 frames' would show >= 0.8 of gaps at 4-5 frames and change on ~20 %% of frames.  It does not.")

    pr("\n1b. Step-size distribution, |delta cmd| per engaged frame (raw counts; 0xE4 command is signed, +-4096)")
    pr("  %-5s %8s %7s %7s %7s %7s %7s %7s %8s %10s" %
       ("route", "n", "p50", "p75", "p90", "p95", "p99", "max", "mean", "frac at max"))
    for tag in list(ROUTES) + ["POOL"]:
        d = pooled if tag == "POOL" else CAD[tag]["d"]
        a = np.abs(d)
        mx = a.max()
        pr("  %-5s %8d %7.0f %7.0f %7.0f %7.0f %7.0f %7.0f %8.2f %10.4f" % (
            tag, len(a), *np.percentile(a, (50, 75, 90, 95, 99)), mx, a.mean(), np.mean(a >= mx - 0.5)))
    pr("  |delta| never exceeds %.0f raw/frame on any route -- openpilot's own rate limit "
       "(the census's top-1%% threshold was 122)." % np.abs(pooled).max())

    pr("\n1c. Cadence INSIDE grind #1 episodes vs engaged baseline (same route, same clock)")
    pr("  %-5s %-12s %8s %9s %9s %9s %9s" %
       ("route", "stratum", "n frames", "chg/frame", "mean|d|", "p90|d|", "frac |d|>=122"))
    for tag in ROUTES:
        g, e = G[tag], G[tag]["e4"]
        # map the 0x18F-axis episode mask onto the e4 grid by nominal time
        hotf = np.interp(e["tgrid"], g["t"], g["hot"].astype(float)) > 0.5
        d = np.diff(e["grid"])
        base = e["egrid"][1:] & e["egrid"][:-1]
        for lab, sel in (("episode", base & hotf[1:]), ("baseline", base & ~hotf[1:])):
            dd = d[sel]
            if len(dd) < 100:
                pr("  %-5s %-12s %8d   (thin)" % (tag, lab, len(dd)))
                continue
            pr("  %-5s %-12s %8d %9.3f %9.2f %9.1f %9.4f" % (
                tag, lab, len(dd), np.mean(dd != 0), np.abs(dd).mean(),
                np.percentile(np.abs(dd), 90), np.mean(np.abs(dd) >= 122)))

    # ==================================================================================== 2. SPECTRUM
    pr("\n" + "=" * 150)
    pr("2. SPECTRUM OF THE COMMAND -- on the 0xE4 stream's OWN dejittered clock (fs = 1/P_e4, no resampling)")
    pr("=" * 150)
    SP = {}
    for tag in ROUTES:
        g, e = G[tag], G[tag]["e4"]
        fs = 1.0 / e["P"]
        hotf = np.interp(e["tgrid"], g["t"], g["hot"].astype(float)) > 0.5
        segs_all, segs_hot, segs_cold = [], [], []
        for a, b in C20.runs(e["egrid"], 512):
            segs_all.append(e["grid"][a:b])
        for a, b in C20.runs(e["egrid"] & hotf, 256):
            segs_hot.append(e["grid"][a:b])
        for a, b in C20.runs(e["egrid"] & ~hotf, 512):
            segs_cold.append(e["grid"][a:b])
        SP[tag] = dict(fs=fs,
                       all=welch_pool(segs_all, fs, 512),
                       hot=welch_pool(segs_hot, fs, 256),
                       cold=welch_pool(segs_cold, fs, 512))
    pr("\n2a. Pooled Welch PSD of cmd (raw counts^2/Hz), engaged; nperseg 512 (0.195 Hz bins)")
    pr("  %-5s %8s | %10s %10s %10s %10s %10s | %10s %8s" %
       ("route", "s engd", "1-5 Hz", "5-10", "12-18", "18-22", "26-40", "peak 18-22", "f peak"))
    for tag in ROUTES:
        f, P, n = SP[tag]["all"]
        row = []
        for lo, hi in ((1, 5), (5, 10), (12, 18), (18, 22), (26, 40)):
            s = (f >= lo) & (f < hi)
            row.append(P[s].mean())
        s = (f >= 18) & (f < 22)
        pr("  %-5s %8.0f | %10.3g %10.3g %10.3g %10.3g %10.3g | %10.3g %8.2f" %
           (tag, n / SP[tag]["fs"], *row, P[s].max(), f[s][P[s].argmax()]))
    pr("\n  Line-to-shoulder ratio (mean PSD 18-22 / mean of 12-18 and 26-40):")
    for tag in ROUTES:
        f, P, n = SP[tag]["all"]
        b18 = P[(f >= 18) & (f < 22)].mean()
        sh = 0.5 * (P[(f >= 12) & (f < 18)].mean() + P[(f >= 26) & (f < 40)].mean())
        pr("    %-5s  %.2f x" % (tag, b18 / sh))

    pr("\n2b. Fine line frequency, SAME estimator on every stream (zero-padded periodogram, parabolic refine)")
    pr("    cmd on its own clock; bar / wheel-rate / angle on the 0x18F clock; T on the 0x1AB clock.")
    pr("  %-5s | %-16s %-16s %-16s %-16s %-16s" %
       ("route", "cmd (0xE4)", "bar (0x18F)", "rate (0x18F)", "angle (0x14A)", "T (427 tap)"))
    F0 = {}
    for tag in ROUTES:
        g, e = G[tag], G[tag]["e4"]
        hotf = np.interp(e["tgrid"], g["t"], g["hot"].astype(float)) > 0.5
        outs = []
        # cmd, own clock, episode frames only
        segs = [e["grid"][a:b] for a, b in C20.runs(e["egrid"] & hotf, 256)]
        fc = [fine_line(s, 1.0 / e["P"], 15, 26)[0] for s in segs]
        outs.append((np.median(fc), len(fc)))
        for key, fsx in (("bar", FS), ("wire", FS), ("ang", FS)):
            segs = [g[key][a:b] for a, b in C20.runs(g["hot"], 256)]
            fv = [fine_line(s, fsx, 15, 26)[0] for s in segs]
            outs.append((np.median(fv), len(fv)))
        # T on its own 50 Hz clock: episode mask by time
        hotT = np.interp(g["T_t"], g["t"], g["hot"].astype(float)) > 0.5
        segs = [g["T"][a:b] for a, b in C20.runs(hotT, 128)]
        fv = [fine_line(s, FST, 15, 24)[0] for s in segs]
        outs.append((np.median(fv) if fv else np.nan, len(fv)))
        F0[tag] = outs
        pr("  %-5s | %s" % (tag, " ".join("%6.3f Hz (n%3d)" % (a, b) for a, b in outs)))
    pr("\n  If the command's line were a fixed openpilot clock artefact it would sit at a constant frequency")
    pr("  independent of the car; if it is the car's oscillation echoed back it sits on the bar/rate line.")

    pr("\n2c. Per-episode PAIRED line frequency, cmd vs bar (the tracking test)")
    pr("  %-5s %6s %12s %12s %12s %12s" % ("route", "n eps", "f cmd p50", "f bar p50",
                                           "median |df|", "corr(f_cmd,f_bar)"))
    allc, allb = [], []
    for tag in ROUTES:
        g, e = G[tag], G[tag]["e4"]
        fc, fb = [], []
        for a, b, _f in EP[tag]:
            if b - a < 100:
                continue
            t0, t1 = g["t"][a], g["t"][b - 1]
            i0, i1 = np.searchsorted(e["tgrid"], (t0, t1))
            if i1 - i0 < 100 or not e["egrid"][i0:i1].all():
                continue
            fc.append(fine_line(e["grid"][i0:i1], 1.0 / e["P"], 15, 26)[0])
            fb.append(fine_line(g["bar"][a:b], FS, 15, 26)[0])
        if len(fc) >= 5:
            r = float(np.corrcoef(fc, fb)[0, 1])
            pr("  %-5s %6d %12.3f %12.3f %12.3f %12.3f" %
               (tag, len(fc), np.median(fc), np.median(fb), np.median(np.abs(np.array(fc) - np.array(fb))), r))
            allc += fc
            allb += fb
        else:
            pr("  %-5s %6d   (thin)" % (tag, len(fc)))
    if len(allc) >= 5:
        pr("  %-5s %6d %12.3f %12.3f %12.3f %12.3f" %
           ("POOL", len(allc), np.median(allc), np.median(allb),
            np.median(np.abs(np.array(allc) - np.array(allb))), float(np.corrcoef(allc, allb)[0, 1])))

    pr("\n2d. Is the command's line PRESENT when the car is not grinding?  (cmd 18-22 Hz amplitude, raw counts)")
    pr("  %-5s %14s %14s %10s | %14s %14s %10s" %
       ("route", "cmd 18-22 epi", "cmd 18-22 base", "ratio", "bar 18-22 epi", "bar 18-22 base", "ratio"))
    for tag in ROUTES:
        g, e = G[tag], G[tag]["e4"]
        hotf = np.interp(e["tgrid"], g["t"], g["hot"].astype(float)) > 0.5
        ce = [bandamp(e["grid"][a:b], 1.0 / e["P"], LO, HI) for a, b in C20.runs(e["egrid"] & hotf, 128)]
        cb = [bandamp(e["grid"][a:b], 1.0 / e["P"], LO, HI) for a, b in C20.runs(e["egrid"] & ~hotf, 128)]
        be = [bandamp(g["bar"][a:b], FS, LO, HI) for a, b in C20.runs(g["hot"], 128)]
        bb = [bandamp(g["bar"][a:b], FS, LO, HI) for a, b in C20.runs(g["eng"] & ~g["hot"], 128)]
        pr("  %-5s %14.1f %14.1f %10.2f | %14.1f %14.1f %10.2f" %
           (tag, np.median(ce), np.median(cb), np.median(ce) / max(np.median(cb), 1e-9),
            np.median(be), np.median(bb), np.median(be) / max(np.median(bb), 1e-9)))

    pr("\n2e. The 100 Hz update comb -- is there a spectral comb at the command update rate?")
    pr("    A ZOH staircase updated every N frames puts lines at k/(N*P). N=1 (every frame) puts its first")
    pr("    image at 1/P ~ 100 Hz, i.e. ABOVE this instrument's 50 Hz Nyquist -- nothing in band.")
    for tag in ROUTES:
        f, P, n = SP[tag]["all"]
        pr("    %-5s  peaks in 30-49.5 Hz: %s" % (
            tag, " ".join("%.2f Hz (%.3g)" % (f[i], P[i]) for i in
                          (np.flatnonzero((f >= 30) & (f <= 49.5))[
                              np.argsort(P[(f >= 30) & (f <= 49.5)])[-4:]][::-1]))))
    pr("    Also: mean |delta cmd| folded by frame index mod N (a genuine every-Nth-frame update would")
    pr("    make one residue class systematically larger):")
    for tag in ROUTES:
        e = G[tag]["e4"]
        d = np.abs(np.diff(e["grid"]))
        ok = e["egrid"][1:] & e["egrid"][:-1]
        kk = np.arange(1, e["K"] + 1)[ok]
        dd = d[ok]
        line = []
        for M in (2, 3, 4, 5, 10):
            mus = np.array([dd[kk % M == j].mean() for j in range(M)])
            line.append("mod%d %.3f" % (M, (mus.max() - mus.min()) / mus.mean()))
        pr("      %-5s relative spread: %s" % (tag, "   ".join(line)))

    # ==================================================================================== 3. CAUSALITY
    pr("\n" + "=" * 150)
    pr("3. COHERENCE AND CROSS-PHASE AT THE LINE")
    pr("=" * 150)
    pr("\n3a. cmd vs bar / wheel-rate / angle, on the common 0x18F nominal clock, EPISODE frames only")
    pr("    (cmd is put on the 0x18F clock by interpolation here -- a mild low-pass; amplitudes read low by")
    pr("     a few %, coherence and phase unaffected.)  nperseg 256 (0.39 Hz bins).")
    pr("  %-5s %-10s %8s %10s %10s %10s" % ("route", "pair", "coh@f0", "phase deg", "gain", "n frames"))
    PH = {}
    for tag in ROUTES:
        g = G[tag]
        f0 = F0[tag][1][0]                    # the bar line
        segs = {k: [] for k in ("cmd", "bar", "wire", "ang")}
        for a, b in C20.runs(g["hot"], 256):
            for k in segs:
                segs[k].append(g[k][a:b])
        PH[tag] = {}
        for other in ("bar", "wire", "ang"):
            f, coh, ph, gain, n = csd_pool(segs["cmd"], segs[other], FS, 256)
            if not n:
                continue
            PH[tag][other] = (at(f, coh, f0), circ_at(f, ph, f0), at(f, gain, f0))
            pr("  %-5s %-10s %8.2f %10.1f %10.4g %10d" %
               (tag, "cmd/" + other, PH[tag][other][0], PH[tag][other][1], PH[tag][other][2], n))
        # cmd vs T on the 50 Hz tap clock
        hotT = np.interp(g["T_t"], g["t"], g["hot"].astype(float)) > 0.5
        cmdT = np.interp(g["T_t"], g["t"], g["cmd"])
        sa, sb = [], []
        for a, b in C20.runs(hotT, 128):
            sa.append(cmdT[a:b])
            sb.append(g["T"][a:b])
        f, coh, ph, gain, n = csd_pool(sa, sb, FST, 128)
        if n:
            PH[tag]["T"] = (at(f, coh, f0), circ_at(f, ph, f0), at(f, gain, f0))
            pr("  %-5s %-10s %8.2f %10.1f %10.4g %10d" % (tag, "cmd/T", *PH[tag]["T"], n))
    pr("\n  CAVEAT [EVIDENCE for the numbers, NOT for lead/lag]: each CAN stream carries its own unknown")
    pr("  receive latency.  The record already measures ~3.9 ms between 0x18F and 0x1AB (a constant +23..+33")
    pr("  deg at 20 Hz).  There is NO equivalent calibration for 0xE4, and 5 ms = 36 deg at 20 Hz, so an")
    pr("  absolute phase at 20 Hz CANNOT be read as 'the command leads'.  Sections 3b/4 do not use phase.")

    pr("\n3b. The openpilot angle->command path, evaluated (this is what would put the car's 20 Hz IN the command)")
    pr("    StarPilot latcontrol_torque.update() [EVIDENCE: source read, openpilots/StarPilot/selfdrive/controls/")
    pr("    lib/latcontrol_torque.py + latcontrol_vehicle_tunes.py + common/pid.py + controlsd.py + opendbc_repo/")
    pr("    opendbc/car/lateral.py]:")
    pr("      measurement    = -VM.calc_curvature(rad(CS.steeringAngleDeg - angleOffset), vEgo, roll) * vEgo^2")
    pr("      error          = setpoint - measurement          (setpoint is the 20 Hz model path: DC at 20 Hz)")
    pr("      error_with_lsf = error * (1 + lsf/current_kp),  lsf = (interp(v,[0,10,20,30],[12,10.5,8,5])/max(v,.3))^2")
    pr("      output_lataccel= pid.k_p*error_with_lsf + i + ff,  ff += friction*LAF*clip(error_with_lsf/thr,-1,1)")
    pr("      output_torque  = output_lataccel / LAF ;  apply_steer = round(output_torque * STEER_MAX)")
    pr("    KEY STRUCTURAL FACTS: (i) the measurement is CS.steeringAngleDeg at 100 Hz with NO low-pass anywhere;")
    pr("    (ii) PIDController k_d defaults to 0 and is never set, so the error_rate (2 Hz-filtered) D term is")
    pr("    INERT; (iii) controlsd overwrites pid._k_p with the SteerKP toggle (0.600, measured) every frame.")
    pr("    => predicted small-signal angle->command gain, live at EVERY frequency openpilot passes:")
    pr("       Gpred = STEER_MAX * (1 + lsf/current_kp) * (k_p/LAF + friction/thr) * (pi/180)*v^2/(SR*L)")
    SR, L, STEER_MAX, KP, FRIC, THR = 16.1, 2.83, 4096.0, 0.600, 0.212, 0.30
    LAF = {"r39": 2.11, "r3a": 4.00, "r3c": 3.60}
    pr("       SR %.1f, wheelbase %.2f m, STEER_MAX %.0f, k_p %.3f, SteerFriction %.3f, threshold %.2f, LAF per route."
       % (SR, L, STEER_MAX, KP, FRIC, THR))
    pr("       `current_kp` is AMBIGUOUS in the source (pid._k_p is replaced by the flat toggle, so the speed")
    pr("       interpolation it is read through may return either the flat 0.600 or the KP_INTERP ladder) --")
    pr("       both cases are priced. [BELIEF: the model; EVIDENCE: the measured gain and coherence]")
    pr("  %-5s %7s %7s %8s %11s %11s %11s %11s %11s %7s" %
       ("route", "v p50", "LAF", "lsf", "Gpred kp=.6", "Gpred ladder", "Gmeas c/deg", "meas/pred.6",
        "ang18-22 deg", "coh"))
    for tag in ROUTES:
        g = G[tag]
        v = float(np.median(g["vego"][g["hot"]])) if g["hot"].any() else np.nan
        lsf = (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 0.3)) ** 2
        kp_ladder = float(np.interp(v, [1, 1.5, 2.0, 3.0, 5, 7.5, 10, 15, 30],
                                    [250, 120, 65, 30, 11.5, 5.5, 3.5, 2.0, 0.6]))
        core = (KP / LAF[tag] + FRIC / THR) * (np.pi / 180) / (SR * L) * v ** 2 * STEER_MAX
        gpa = (1 + lsf / KP) * core
        gpb = (1 + lsf / kp_ladder) * core
        gm, coh = (PH[tag]["ang"][2], PH[tag]["ang"][0]) if "ang" in PH[tag] else (np.nan, np.nan)
        aamp = np.median([bandamp(g["ang"][a:b], FS, LO, HI) for a, b in C20.runs(g["hot"], 128)])
        pr("  %-5s %7.1f %7.2f %8.2f %11.0f %11.0f %11.0f %11.2f %11.4f %7.2f" %
           (tag, v, LAF[tag], lsf, gpa, gpb, gm, gm / gpa if gpa else np.nan, aamp, coh))
    pr("    Reading: the measured gain sits ~2x above the flat-k_p prediction and ~6x above the ladder one.")
    pr("    Both are order-of-magnitude agreements, not a validated model -- the 0x14A angle quantises at")
    pr("    0.1 deg, which is a large fraction of the 18-22 Hz angle ripple above, so the angle auto-spectrum")
    pr("    is inflated by quantisation noise and the H1 gain estimate is biased DOWN.  What the row supports")
    pr("    is only this: an UNFILTERED 100 Hz proportional path from steering angle to command exists in the")
    pr("    source and is of the right order to explain the command's 20 Hz line.  It is not a measurement of")
    pr("    that path's exact gain.")

    # ================================================================================ 4. CONTRIBUTION
    pr("\n" + "=" * 150)
    pr("4. HOW MUCH OF THE DELIVERED 18-22 Hz IS THE COMMAND'S OWN LINE?  (1 kHz FUN_00028ea6 mirror)")
    pr("=" * 150)
    pr("  Method: GI.simulate (the kit's 1 kHz mirror, V282 cells) run on each episode window three ways --")
    pr("    (a) as flown;  (b) cmd zero-phase low-passed at 15 Hz before the demand chain (its 18-22 Hz")
    pr("    content removed, everything else identical);  (c) wheel rate low-passed at 15 Hz (the record's")
    pr("    own comparator).  Delta in T's 18-22 Hz band amplitude attributes the ripple.")
    pr("  %-5s %-26s %6s %9s %9s %9s %9s %9s" %
       ("route", "episode t0-t1 (s)", "dur", "T18-22 a", "b:cmdLP", "b/a", "c:rateLP", "c/a"))
    sos15 = signal.butter(4, 15.0, btype="lowpass", fs=FS, output="sos")
    tot = {"ba": [], "ca": []}
    for tag in ROUTES:
        g = G[tag]
        eps = sorted(EP[tag], key=lambda z: -GI.band(g["bar"][z[0]:z[1]], LO, HI, FS))[:6]
        for a, b, f0 in eps:
            if b - a < 100:
                continue
            o = GI.simulate(g, a, b, cells)
            gl = dict(g)
            gl["cmd"] = signal.sosfiltfilt(sos15, g["cmd"])
            ol = GI.simulate(gl, a, b, cells)
            orl = GI.simulate(g, a, b, cells, rate_filter=15.0)
            n0 = (a - o["seg"].start) * 10
            n1 = n0 + (b - a) * 10
            Ta = GI.band(o["T"][n0:n1], LO, HI, FS1K)
            Tb = GI.band(ol["T"][n0:n1], LO, HI, FS1K)
            Tc = GI.band(orl["T"][n0:n1], LO, HI, FS1K)
            tot["ba"].append(Tb / Ta)
            tot["ca"].append(Tc / Ta)
            pr("  %-5s %-26s %6.2f %9.1f %9.1f %9.3f %9.1f %9.3f" %
               (tag, "%.1f - %.1f" % (g["tr"][a], g["tr"][b - 1]), (b - a) / FS, Ta, Tb, Tb / Ta, Tc, Tc / Ta))
    pr("  %-5s %-26s %6s %9s %9s %9.3f %9s %9.3f" %
       ("POOL", "median over %d episodes" % len(tot["ba"]), "", "", "",
        np.median(tot["ba"]), "", np.median(tot["ca"])))
    pr("\n  Read: (b/a) is what SURVIVES when the command's own 18-22 Hz is deleted -- 1.00 would mean the")
    pr("  command contributes nothing; 0.00 would mean the ripple IS the command.  (c/a) is the same test on")
    pr("  the feedback path.  The record's comparable numbers (creep20 headline 1): low-passing the RATE")
    pr("  removes 79 %% of the ripple, freezing the command removes 23 %%.")

    # ====================================================================================== 5. DOSES
    pr("\n" + "=" * 150)
    pr("5. CANDIDATE EPS-SIDE SETPOINT FILTERS, SIMULATED OFFLINE ON THE REAL STAIRCASE")
    pr("=" * 150)
    pr("  The EPS reads the decoded 0xE4 value from a store and runs the PID at 1 kHz: the setpoint path is a")
    pr("  zero-order hold, 10 ticks per command frame, with NO memory anywhere from the CAN byte to the error")
    pr("  (STATE 2026-09-06).  Two candidate code edits, both applied to the command BEFORE the demand chain:")
    pr("    IIR      sp <- sp + alpha*(cmd - sp) each 1 kHz tick, alpha = 1-exp(-2*pi*fc/1000)")
    pr("    LERP10   ramp linearly from the previous frame's value to the new one across the 10 ticks")
    pr("             (= a causal 10-tick moving average of the staircase; no extra frame of buffering)")
    pr("  Metrics, pooled over engaged 0xE4 frames of all three routes:")
    pr("    'cmd 18-22'  amplitude of the command's own line after the filter, relative to the staircase")
    pr("    'kick'       mean over binding-relevant ticks of |32*delta_sp| per 1 kHz tick = the impulse into D")
    pr("    'gd 1-3 Hz'  added group delay in the outer loop's band, and the phase it costs at 1/2/3 Hz")
    # build the 1 kHz staircase from the raw engaged command of every route
    stair, spstair = [], []
    for tag in ROUTES:
        g, e = G[tag], G[tag]["e4"]
        for a, b in C20.runs(e["egrid"], 512):
            stair.append(np.repeat(e["grid"][a:b], 10))
    pr("\n  %-10s %8s %10s %11s %11s %11s %11s %11s" %
       ("filter", "alpha", "cmd18-22", "vs stair", "kick raw", "vs stair", "gd (ms)", "ph@2Hz deg"))
    base_amp = np.median([bandamp(s, FS1K, LO, HI) for s in stair])
    base_kick = np.median([np.mean(np.abs(np.diff(s))[np.abs(np.diff(s)) > 0]) for s in stair])
    pr("  %-10s %8s %10.2f %11.3f %11.2f %11.3f %11.2f %11.1f" %
       ("staircase", "-", base_amp, 1.0, base_kick, 1.0, 0.0, 0.0))
    DOSE = {}
    for fc in (10.0, 15.0, 20.0, 30.0):
        al = 1.0 - np.exp(-2 * np.pi * fc / FS1K)
        amps, kicks = [], []
        for s in stair:
            y = signal.lfilter([al], [1.0, -(1.0 - al)], s - s[0]) + s[0]
            amps.append(bandamp(y, FS1K, LO, HI))
            dy = np.abs(np.diff(y))
            kicks.append(np.mean(dy[dy > 1e-9]))
        gd = 1.0 / (2 * np.pi * fc) * 1000.0
        ph2 = -np.degrees(np.arctan(2.0 / fc))
        DOSE["IIR %g Hz" % fc] = (np.median(amps) / base_amp, np.median(kicks) / base_kick)
        pr("  %-10s %8.4f %10.2f %11.3f %11.2f %11.3f %11.2f %11.1f" %
           ("IIR %g Hz" % fc, al, np.median(amps), np.median(amps) / base_amp,
            np.median(kicks), np.median(kicks) / base_kick, gd, ph2))
    amps, kicks = [], []
    for s in stair:
        y = signal.lfilter(np.ones(10) / 10.0, [1.0], s - s[0]) + s[0]
        amps.append(bandamp(y, FS1K, LO, HI))
        dy = np.abs(np.diff(y))
        kicks.append(np.mean(dy[dy > 1e-9]))
    DOSE["LERP10"] = (np.median(amps) / base_amp, np.median(kicks) / base_kick)
    pr("  %-10s %8s %10.2f %11.3f %11.2f %11.3f %11.2f %11.1f" %
       ("LERP10", "-", np.median(amps), np.median(amps) / base_amp,
        np.median(kicks), np.median(kicks) / base_kick, 4.5, -np.degrees(2 * np.pi * 2.0 * 0.0045)))

    pr("\n5b. The same doses carried through the WHOLE 1 kHz mirror on the loudest episodes")
    pr("    (setpoint path filtered; feedback, gains, clamps and the map untouched).")
    pr("    Two columns per dose: T's 18-22 Hz amplitude ratio, and the D-term rail duty (V282 clamp 10240).")
    pr("  %-5s %-22s %8s %7s | %s" % ("route", "episode", "T18-22", "drail", " ".join(
        "%13s" % k for k in ["IIR10", "IIR15", "IIR20", "IIR30", "LERP10"])))

    def filt_cmd_1k(cmd100, kind, fc=None):
        """apply a 1 kHz setpoint filter to a 100 Hz command, return the 100 Hz-decimated equivalent
        that GI.simulate's ZOH will re-expand.  (GI.simulate repeats each 100 Hz sample 10x, so we
        return the mean of each 10-tick block -- exact for LERP10, a close proxy for the IIRs.)"""
        s = np.repeat(cmd100, 10)
        if kind == "iir":
            al = 1.0 - np.exp(-2 * np.pi * fc / FS1K)
            y = signal.lfilter([al], [1.0, -(1.0 - al)], s - s[0]) + s[0]
        else:
            y = signal.lfilter(np.ones(10) / 10.0, [1.0], s - s[0]) + s[0]
        return y.reshape(-1, 10).mean(1)

    KEYS = ("IIR10", "IIR15", "IIR20", "IIR30", "LERP10")
    dose_tot = {k: [] for k in KEYS}
    dose_dr = {k: [] for k in KEYS}
    for tag in ROUTES:
        g = G[tag]
        eps = sorted(EP[tag], key=lambda z: -GI.band(g["bar"][z[0]:z[1]], LO, HI, FS))[:4]
        for a, b, f0 in eps:
            if b - a < 100:
                continue
            o = GI.simulate(g, a, b, cells)
            n0 = (a - o["seg"].start) * 10
            n1 = n0 + (b - a) * 10
            Ta = GI.band(o["T"][n0:n1], LO, HI, FS1K)
            cells_row = []
            for lab, kind, fc in (("IIR10", "iir", 10.0), ("IIR15", "iir", 15.0), ("IIR20", "iir", 20.0),
                                  ("IIR30", "iir", 30.0), ("LERP10", "lerp", None)):
                gl = dict(g)
                gl["cmd"] = filt_cmd_1k(g["cmd"], kind, fc)
                ol = GI.simulate(gl, a, b, cells)
                r = GI.band(ol["T"][n0:n1], LO, HI, FS1K) / Ta
                dose_tot[lab].append(r)
                dose_dr[lab].append(ol["drail"])
                cells_row.append((r, ol["drail"]))
            dose_tot.setdefault("_base", []).append(o["drail"])
            pr("  %-5s %-22s %8.1f %7.4f | %s" % (
                tag, "%.1f-%.1f" % (g["tr"][a], g["tr"][b - 1]), Ta, o["drail"],
                " ".join("%7.3f/%5.4f" % c for c in cells_row)))
    pr("  %-5s %-22s %8s %7.4f | %s" % (
        "POOL", "median", "", np.median(dose_tot["_base"]),
        " ".join("%7.3f/%5.4f" % (np.median(dose_tot[k]), np.median(dose_dr[k])) for k in KEYS)))

    # ====================================================================================== 6. ALIAS
    pr("\n" + "=" * 150)
    pr("6. ALIAS CHECK")
    pr("=" * 150)
    e = G["r39"]["e4"]
    pr("  The 0xE4 stream in the rlog is not a SAMPLING of a continuous signal: every transmitted frame is")
    pr("  logged, and the value logged IS the value the EPS receives.  Its own clock is %.5f ms (%.3f Hz)."
       % (e["P"] * 1000, 1.0 / e["P"]))
    pr("  CAN EXCLUDE: that the 20 Hz line is a logging/resampling artefact of the command -- the line is")
    pr("    measured on the raw per-frame values, on the stream's own dejittered frame counter, with no")
    pr("    resampling anywhere in the path (Section 2a/2b).")
    pr("  CANNOT EXCLUDE from this stream alone: content ABOVE %.1f Hz in the command." % (0.5 / e["P"]))
    pr("    openpilot emits one value per frame, so anything it computed above 49.8 Hz is already folded into")
    pr("    the emitted sequence by ITS OWN 100 Hz rate before transmission -- the EPS receives the aliased")
    pr("    version too.  There is therefore no 'true' 80/120 Hz command content the EPS could see and we")
    pr("    could not: the command IS the 100 Hz sequence.  This is DIFFERENT from the 0x18F rate/angle")
    pr("    streams, where the sensor is continuous and the 100 Hz CAN frame IS a sampling, so an 80 or 120 Hz")
    pr("    mechanical line would fold to 20 Hz there and cannot be excluded (TASK5, open).")
    pr("  What this means for attribution: a 20 Hz line in the COMMAND is real at 20 Hz by construction; a")
    pr("    20 Hz line on the 0x18F wheel streams still carries TASK5's unresolved 80/120 Hz alias risk.")

    with open(os.path.join(SCR, "wire_0xe4_20hz.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    pr("\n[written: _scratch/wire_0xe4_20hz.txt]")


if __name__ == "__main__":
    main()
