# -*- coding: utf-8 -*-
"""studies/grind/loopshape20_mode_nature.py -- IS THE 20 Hz GRIND LINE A CLOSED-LOOP CROSSOVER RESONANCE
OR A LIGHTLY DAMPED PLANT (column/torsion) MODE THE LOOP MERELY EXCITES?   Subagent loopshape, 2026-09-08.
Analysis only: builds nothing, flashes nothing, sends nothing.

Routes (caches analysis-2020accord/_scratch/cache/v280/*.npz, loaded through creep20_loop_id.load):
  V282   r39 r3a r3c        Kp FLAT 248, Kd 128, linear map (loop gain idx-INDEPENDENT)
  V288r2 r5e_v288           = V282 + setpoint pre-filter cave (feedback loop byte-identical to V282)
  V281r3 r35                Kp flat 248 (first flat-Kp build)
  V280r2 r32 r33 r34        Kp LERP 248..696 on idx  <-- the only routes where LOOP GAIN varies within a route
  V278r3 r31                Kp LERP, map x2

Method (all instruments already on disk, census recipe copied from grind1_census_v282.py so the yardstick is
the same: 2 s windows / 0.5 s step / present = 15-26 Hz prominence >= 8 AND bar 18-22 >= 40 raw):
  1  line frequency vs hands (|bar| median <400 / 400-700 / >700), vs idx, vs Kp(idx) (V280 routes only),
     vs speed, vs |rate|, vs the command's own 20 Hz echo (cmd line prominence at f0).  Spearman + OLS.
     THE DISCRIMINATOR: on r31-r34 Kp rises 248->696 with idx.  A crossover/-180deg-limited loop on a SMOOTH
     plant moves its pole DOWN by several Hz when Kp rises (less D lead); a plant resonance pins f.
  2  free-decay fits: per episode, log-envelope slope after the peak -> zeta = -gd/(2 pi f0); instantaneous
     frequency during the decay; command 18-22 content during the decay (is it free?).
  3  closed-loop transfer command -> wheel rate and command -> bar, 100 Hz frame axis, pooled Welch, 15-26 Hz;
     resonance fit (fn, zeta) to |H| and the phase step across the peak.  The command is exogenous.
  4  plant tap -> rate at the tap's own instants (creep20.native_tap_segment), pooled over engaged low-speed
     hands-off runs, |G| / angle / coherence 8-24 Hz; the -180 deg crossing of L = L_fw(Kp 248) * G with and
     without the 3.9 ms inter-stream offset removed (the offset creep20 measured end to end).
Run: python loopshape20_mode_nature.py   (writes _scratch/loopshape20_mode_nature.txt beside it)
"""
import os
import sys

import numpy as np
from scipy import signal, stats

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

FS, FST = 100.0, 50.0
W, STEP = 200, 50
TAU_STREAM = 0.0039          # creep20 §1.0: the tap reads ~3.9 ms after the 0x18F rate snapshot it responds to
IMG = {
    "V282": LG.FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "V288": LG.FW + "_v288r2_V288R2-V282BASE-SPFILT.K4.EINIT-KP.FLAT.Y0-CAVE.R24CMP.B6-SPSIGN.B5-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "V281r3": LG.FW + "_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "V280r2": LG.FW + LG.IMAGES["V280r2"],
    "V278r3": LG.FW + LG.IMAGES["V278r3"],
}
ROUTES = ("r39", "r3a", "r3c", "r5e_v288", "r35", "r32", "r33", "r34", "r31")
BUILD = {"r39": "V282", "r3a": "V282", "r3c": "V282", "r5e_v288": "V288", "r35": "V281r3",
         "r32": "V280r2", "r33": "V280r2", "r34": "V280r2", "r31": "V278r3"}
GROUP = {"V282": "flat-Kp", "V288": "flat-Kp", "V281r3": "flat-Kp", "V280r2": "Kp-LERP", "V278r3": "Kp-LERP"}
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def kp_of(c, idx):
    return np.interp(idx, c["kp_X"], c["kp_Y"])


def load_route(tag, cells):
    g = C20.load(tag)
    g["tr"] = g["t"] - g["t"][0]
    c = cells[BUILD[tag]]
    g["idx"], _ = GI.demand_live(np.round(g["cmd"]), g["bar"], c)
    g["kp"] = kp_of(c, g["idx"])
    g["rate"] = np.abs(g["wire"]) / V.CPD
    return g


def line_prom_at(x, fs, f0, half=0.6):
    """prominence of x's spectrum at f0 (+-half Hz) against the local floor -- same estimator as line_of."""
    f, P = signal.periodogram(np.asarray(x, float) - np.mean(x), fs=fs, window="hann", nfft=4096)
    import _grind2_lib as G2
    Rp = G2.prom_spectrum(f, P, 6.0, 1.5)
    m = (f >= f0 - half) & (f <= f0 + half)
    return float(np.max(Rp[m])) if m.any() else np.nan


def inst_freq(x, f0, fs, bw=3.0):
    y = C20.bandpass(x, max(f0 - bw, 1.0), f0 + bw, fs)
    ph = np.unwrap(np.angle(signal.hilbert(y)))
    return np.gradient(ph) * fs / (2 * np.pi)


def resonance_fit(f, H, flo=15.0, fhi=26.0):
    """|H|(f) ~ A / |1 - (f/fn)^2 + 2 j zeta f/fn| over [flo, fhi]; grid search on (fn, zeta), A by LS.
    returns fn, zeta, rms log residual."""
    m = (f >= flo) & (f <= fhi) & np.isfinite(H)
    ff, hh = f[m], np.abs(H[m])
    best = (np.nan, np.nan, np.inf)
    for fn in np.arange(17.0, 24.01, 0.1):
        for ze in np.r_[0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05, 0.07, 0.10, 0.15, 0.2, 0.3, 0.5]:
            r = 1.0 / np.abs(1 - (ff / fn) ** 2 + 2j * ze * ff / fn)
            A = np.exp(np.mean(np.log(hh) - np.log(r)))
            res = np.sqrt(np.mean((np.log(hh) - np.log(A * r)) ** 2))
            if res < best[2]:
                best = (fn, ze, res)
    return best


def main():
    cells = {k: GI.read_cells(p) for k, p in IMG.items()}
    pr("cells per build (Kp knots / Kd / lag / fb / gain):")
    for k, c in cells.items():
        pr("  %-7s Kp %s  Kd %s  lag %d/%d  fb %d/%d  gain %d  Dclamp %d" % (
            k, c["kp_Y"].astype(int).tolist(), c["kd_Y"].astype(int).tolist(), c["lag_a"], c["lag_b"], c["fb_a"], c["fb_b"], c["gain"], c["d_clamp"]))
    G = {}
    for tag in ROUTES:
        try:
            G[tag] = load_route(tag, cells)
            pr("loaded %-9s %-7s %.0f s, %.0f s engaged" % (tag, BUILD[tag], G[tag]["tr"][-1], G[tag]["eng"].sum() / FS))
        except Exception as e:  # noqa: BLE001
            pr("FAILED %s: %r" % (tag, e))
    tags = [t for t in ROUTES if t in G]

    # ================================================================================================ 1. census windows
    pr("\n" + "=" * 150)
    pr("1. LINE FREQUENCY vs STATE  (2 s windows, 0.5 s step, engaged lateral; present = 15-26 Hz prom >= 8 AND bar 18-22 >= 40)")
    pr("=" * 150)
    rows = []
    for tag in tags:
        g = G[tag]
        for aa, bb in C20.runs(g["eng"], W):
            for s in range(aa, bb - W + 1, STEP):
                e = s + W
                f0w, promw, _, _ = GI.line_of(g["bar"][s:e], FS)
                if not np.isfinite(f0w):
                    continue
                fr, pr_, _, _ = GI.line_of(g["wire"][s:e], FS)
                rows.append(dict(
                    tag=tag, build=BUILD[tag], grp=GROUP[BUILD[tag]], t=g["tr"][s], f0=f0w, prom=promw, fr=fr, promr=pr_,
                    amp=GI.band(g["bar"][s:e], 18, 22), ramp=GI.band(g["wire"][s:e], 18, 22) / V.CPD,
                    camp=GI.band(g["cmd"][s:e], 18, 22), cprom=line_prom_at(g["cmd"][s:e], FS, f0w),
                    tq=float(np.median(np.abs(g["bar"][s:e]))), idx=float(np.median(g["idx"][s:e])),
                    kp=float(np.median(g["kp"][s:e])), v=float(g["vego"][s:e].mean()),
                    rate=float(np.mean(g["rate"][s:e])), ang=float(np.median(np.abs(g["ang"][s:e]))),
                    T=float(np.median(np.abs(g["T100"][s:e])))))
    R = {k: np.array([r[k] for r in rows]) for k in rows[0]}
    pres = (R["prom"] >= 8) & (R["amp"] >= 40)
    np.savez(os.path.join(SCR, "loopshape20_windows.npz"), **R, pres=pres)
    pr("  windows %d, present %d" % (len(rows), pres.sum()))

    def med_iqr(x):
        return "%.2f [%.2f-%.2f] n=%d" % (np.median(x), np.percentile(x, 25), np.percentile(x, 75), len(x)) if len(x) >= 5 else "(n=%d)" % len(x)

    pr("\n1a. f0 (bar line) by build:")
    for b in ("V278r3", "V280r2", "V281r3", "V282", "V288"):
        m = pres & (R["build"] == b)
        if m.any():
            pr("  %-7s f0 %s   rate-line f %s   presence %.1f %%" % (b, med_iqr(R["f0"][m]), med_iqr(R["fr"][m]), 100 * m.sum() / max(1, (R["build"] == b).sum())))
    pr("\n1b. f0 by HANDS (|bar| median raw), pooled per group:")
    for grp in ("flat-Kp", "Kp-LERP"):
        for lab, lo, hi in (("hands-off <400", 0, 400), ("mid 400-700", 400, 700), ("hands-on >700", 700, 1e9), ("hard >1500", 1500, 1e9)):
            m = pres & (R["grp"] == grp) & (R["tq"] >= lo) & (R["tq"] < hi)
            pr("  %-8s %-16s f0 %s" % (grp, lab, med_iqr(R["f0"][m])))
    pr("\n1c. f0 vs state, Spearman rho (p) and OLS slope over p10-p90, present windows:")
    for grp in ("flat-Kp", "Kp-LERP"):
        m = pres & (R["grp"] == grp)
        pr("  group %s (n=%d):" % (grp, m.sum()))
        for key, lab in (("tq", "|bar| raw"), ("idx", "idx"), ("kp", "Kp(idx)"), ("v", "v m/s"), ("rate", "|rate| deg/s"),
                         ("ang", "|angle|"), ("T", "|T| tap"), ("cprom", "cmd line prom at f0"), ("camp", "cmd 18-22 amp")):
            x, y = R[key][m], R["f0"][m]
            ok = np.isfinite(x) & np.isfinite(y)
            if ok.sum() < 10 or np.std(x[ok]) == 0:
                pr("    %-22s (flat or n<10)" % lab); continue
            rho, p = stats.spearmanr(x[ok], y[ok])
            sl, ic, r, pp, se = stats.linregress(x[ok], y[ok])
            p10, p90 = np.percentile(x[ok], (10, 90))
            pr("    %-22s rho %+.2f (p %.3f)  slope %+.4f +- %.4f Hz/unit  -> %+.2f Hz over p10-p90 [%.1f, %.1f]" % (
                lab, rho, p, sl, se, sl * (p90 - p10), p10, p90))
    pr("\n1d. THE Kp DISCRIMINATOR -- f0 by Kp(idx) bins on the Kp-LERP routes (r31-r34), and idx bins on flat-Kp routes as the control:")
    m0 = pres & (R["grp"] == "Kp-LERP")
    for lo, hi in ((240, 300), (300, 400), (400, 500), (500, 600), (600, 700)):
        m = m0 & (R["kp"] >= lo) & (R["kp"] < hi)
        pr("  Kp-LERP  Kp %3d-%3d : f0 %s   amp p50 %.0f" % (lo, hi, med_iqr(R["f0"][m]), np.median(R["amp"][m]) if m.any() else np.nan))
    m0 = pres & (R["grp"] == "flat-Kp")
    for lo, hi in ((0, 20), (20, 60), (60, 120), (120, 250)):
        m = m0 & (R["idx"] >= lo) & (R["idx"] < hi)
        pr("  flat-Kp  idx %3d-%3d : f0 %s   amp p50 %.0f" % (lo, hi, med_iqr(R["f0"][m]), np.median(R["amp"][m]) if m.any() else np.nan))
    pr("\n1e. f0 by the command's own echo (cmd line prominence at f0 >= 8 = echo present), pooled flat-Kp:")
    m0 = pres & (R["grp"] == "flat-Kp")
    for lab, m in (("echo present", m0 & (R["cprom"] >= 8)), ("echo absent", m0 & (R["cprom"] < 8))):
        pr("  %-13s f0 %s  amp p50 %.0f" % (lab, med_iqr(R["f0"][m]), np.median(R["amp"][m]) if m.any() else np.nan))
    pr("\n1f. speed bins, pooled flat-Kp:")
    for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 6), (6, 12), (12, 40)):
        m = m0 & (R["v"] >= lo) & (R["v"] < hi)
        pr("  v %2d-%2d m/s : f0 %s" % (lo, hi, med_iqr(R["f0"][m])))

    # ================================================================================================ 2. free decays
    pr("\n" + "=" * 150)
    pr("2. FREE-DECAY FITS per episode (>= 0.5 s present run): zeta = -gd/(2 pi f0); f_inst during the decay; cmd 18-22 in the decay window")
    pr("=" * 150)
    eps = []
    for tag in tags:
        g = G[tag]
        sel = np.flatnonzero(R["tag"] == tag)
        wt, wp = R["t"][sel], pres[sel]
        if len(wt) == 0:
            continue
        j = np.clip(np.searchsorted(wt, g["tr"] - 1.0), 0, len(wt) - 1)
        near = np.abs(wt[j] + 1.0 - g["tr"]) < 1.5
        hot = g["eng"] & near & wp[j]
        for a, b in C20.runs(hot, int(0.5 * FS)):
            f0, prom, _, _ = GI.line_of(g["bar"][a:b], FS)
            if not np.isfinite(f0):
                continue
            lo, hi = max(0, a - 100), min(len(g["tr"]), b + 100)
            env = GI.envelope(g["bar"][lo:hi], f0, FS)
            envr = GI.envelope(g["wire"][lo:hi], f0, FS)
            tloc = g["tr"][lo:hi]
            gu, _, gd, dur_d = GI.growth_fit(tloc, env)
            gur, _, gdr, _ = GI.growth_fit(tloc, envr)
            k = int(np.argmax(env))
            # decay window: peak -> 10 % (or end); instantaneous frequency there; command band content there
            k2 = k + (np.flatnonzero(env[k:] <= 0.1 * env[k])[0] if (env[k:] <= 0.1 * env[k]).any() else len(env) - k - 1)
            fi = inst_freq(g["bar"][lo:hi], f0, FS)
            fdec = float(np.median(fi[k:k2])) if k2 - k >= 5 else np.nan
            cdec = GI.band(g["cmd"][lo + k:lo + max(k2, k + 32)], 18, 22) if hi - (lo + k) >= 32 else np.nan
            ccore = GI.band(g["cmd"][a:b], 18, 22)
            eps.append(dict(tag=tag, build=BUILD[tag], t0=g["tr"][a], dur=(b - a) / FS, f0=f0, env=float(env[k]),
                            gu=gu, gd=gd, gdr=gdr, ddur=dur_d, zeta=(-gd / (2 * np.pi * f0)) if np.isfinite(gd) else np.nan,
                            zetar=(-gdr / (2 * np.pi * f0)) if np.isfinite(gdr) else np.nan,
                            fdec=fdec, cdec=cdec, ccore=ccore, tq=float(np.median(np.abs(g["bar"][a:b]))),
                            v=float(g["vego"][a:b].mean()), kp=float(np.median(g["kp"][a:b]))))
    E = {k: np.array([e[k] for e in eps]) for k in eps[0]}
    np.savez(os.path.join(SCR, "loopshape20_episodes.npz"), **E)
    pr("  episodes: %d  (%s)" % (len(eps), ", ".join("%s=%d" % (t, (E["tag"] == t).sum()) for t in tags)))
    okd = np.isfinite(E["gd"]) & (E["gd"] < 0)
    pr("\n2a. decay-rate distribution (bar envelope), episodes with a measurable decay (gd < 0): n=%d of %d" % (okd.sum(), len(eps)))
    for b in ("V278r3", "V280r2", "V281r3", "V282", "V288"):
        m = okd & (E["build"] == b)
        if m.sum() >= 3:
            pr("  %-7s gd /s p10/p50/p90 %6.2f/%6.2f/%6.2f  -> zeta p10/p50/p90 %.3f/%.3f/%.3f   (rate env zeta p50 %.3f)   f_dec p50 %.2f Hz  f0 p50 %.2f" % (
                b, *np.percentile(E["gd"][m], (10, 50, 90)), *np.percentile(E["zeta"][m], (10, 50, 90)),
                np.nanmedian(E["zetar"][m]), np.nanmedian(E["fdec"][m]), np.median(E["f0"][m])))
    pr("\n2b. are the decays FREE?  cmd 18-22 amplitude in the decay window vs in the core (raw), and zeta split by it (pooled):")
    m = okd & np.isfinite(E["cdec"])
    q = np.nanmedian(E["cdec"][m])
    for lab, mm in (("cmd 18-22 in decay <= median (%.1f raw)" % q, m & (E["cdec"] <= q)), ("cmd 18-22 in decay > median", m & (E["cdec"] > q))):
        pr("  %-40s n=%d  zeta p25/p50/p75 %.3f/%.3f/%.3f  f_dec p50 %.2f" % (lab, mm.sum(), *np.percentile(E["zeta"][mm], (25, 50, 75)), np.nanmedian(E["fdec"][mm])))
    pr("\n2c. zeta vs Kp on the Kp-LERP routes (does the pole's damping follow loop gain?):")
    m = okd & np.isin(E["build"], ["V280r2", "V278r3"])
    for lo, hi in ((240, 320), (320, 450), (450, 700)):
        mm = m & (E["kp"] >= lo) & (E["kp"] < hi)
        if mm.sum() >= 3:
            pr("  Kp %3d-%3d n=%2d  zeta p25/p50/p75 %.3f/%.3f/%.3f  env pk p50 %.0f  f0 p50 %.2f" % (lo, hi, mm.sum(), *np.percentile(E["zeta"][mm], (25, 50, 75)), np.median(E["env"][mm]), np.median(E["f0"][mm])))
    pr("\n2d. zeta by hands (pooled flat-Kp):")
    m = okd & np.isin(E["build"], ["V282", "V288", "V281r3"])
    for lab, lo, hi in (("hands-off <400", 0, 400), ("on >700", 700, 1e9)):
        mm = m & (E["tq"] >= lo) & (E["tq"] < hi)
        if mm.sum() >= 3:
            pr("  %-15s n=%2d  zeta p25/p50/p75 %.3f/%.3f/%.3f  f0 p50 %.2f" % (lab, mm.sum(), *np.percentile(E["zeta"][mm], (25, 50, 75)), np.median(E["f0"][mm])))

    # ================================================================================================ 3. closed-loop transfer
    pr("\n" + "=" * 150)
    pr("3. CLOSED-LOOP TRANSFER command -> wheel rate / bar (exogenous input), 100 Hz frame axis, Welch nperseg 256 (0.39 Hz), 15-26 Hz")
    pr("   stratum: engaged lateral, v < 8 m/s, |bar| < 400 (hands-off), runs >= 2.56 s;  resonance fit |H| ~ A/|1-(f/fn)^2+2j zeta f/fn|")
    pr("=" * 150)
    for grp, tl in (("V282 (r39+r3a+r3c)", ["r39", "r3a", "r3c"]), ("V288 (r5e)", ["r5e_v288"]), ("V280r2 (r32-r34)", ["r32", "r33", "r34"]), ("V281r3 (r35)", ["r35"])):
        P = C20.Pool(FS, 256)
        secs = 0.0
        for tag in tl:
            if tag not in G:
                continue
            g = G[tag]
            msk = g["eng"] & (g["vego"] < 8.0) & (np.abs(g["bar"]) < 400)
            for a, b in C20.runs(msk, 256):
                P.add({"c": g["cmd"][a:b] - g["cmd"][a:b].mean(), "r": g["rate_x"][a:b] - g["rate_x"][a:b].mean(), "q": g["bar"][a:b] - g["bar"][a:b].mean()})
                secs += (b - a) / FS
        if P.n == 0:
            pr("  %s: no data" % grp); continue
        f = P.f
        Hcr, Hcq = P.tf("c", "r"), P.tf("c", "q")
        ccr, ccq = P.coh("c", "r"), P.coh("c", "q")
        pr("\n  %s: %.0f s, %d windows" % (grp, secs, P.n))
        pr("   f Hz   |H c->r| ang coh   |   |H c->q| ang coh   |  |S_qq| / |S_cc| ")
        for f0 in (10, 14, 16, 18, 19, 20, 20.5, 21, 22, 23, 24, 26, 30):
            i = np.argmin(np.abs(f - f0))
            pr("   %4.1f   %7.4f %+5.0f %.2f   |   %7.3f %+5.0f %.2f   |  %.3g" % (
                f[i], abs(Hcr[i]), np.degrees(np.angle(Hcr[i])), ccr[i], abs(Hcq[i]), np.degrees(np.angle(Hcq[i])), ccq[i],
                np.real(P.s("q", "q")[i]) / max(np.real(P.s("c", "c")[i]), 1e-12)))
        for nm, H in (("cmd->rate", Hcr), ("cmd->bar", Hcq)):
            fn, ze, res = resonance_fit(f, H)
            pr("   resonance fit %-9s : fn %.1f Hz  zeta %.3f  (rms log resid %.2f)" % (nm, fn, ze, res))
        # bar / rate at the line (same frame, no timing risk) and its phase
        Hqr = P.tf("r", "q"); cqr = P.coh("r", "q")
        i = np.argmin(np.abs(f - 20.3))
        pr("   bar/rate at 20.3 Hz: |H| %.1f raw per deg/s, angle %+.0f deg, coh %.2f" % (abs(Hqr[i]), np.degrees(np.angle(Hqr[i])), cqr[i]))
        # phase slope of bar/rate through 15-26 Hz (a plant mode between the two sensors would show a step)
        m = (f >= 15) & (f <= 26)
        ph = np.degrees(np.unwrap(np.angle(Hqr[m])))
        pr("   bar/rate phase 15 -> 26 Hz: %s" % " ".join("%+.0f" % p for p in ph[::3]))

    # ================================================================================================ 4. plant from the tap
    pr("\n" + "=" * 150)
    pr("4. PLANT rate/T from the 427 tap at its own instants (50 Hz), pooled engaged v<8 hands-off runs, nperseg 64 (0.78 Hz)")
    pr("   L = L_fw(Kp 248, Kd 128, lag 992/507, fb 923/1560, one tick) * G ; angle(G) shown RAW and with the 3.9 ms stream offset removed")
    pr("=" * 150)
    for grp, tl in (("V282 (r39+r3a+r3c)", ["r39", "r3a", "r3c"]), ("V288 (r5e)", ["r5e_v288"]), ("V280r2+V278r3 (r31-r34)", ["r31", "r32", "r33", "r34"])):
        P = C20.Pool(FST, 64)
        secs = 0.0
        for tag in tl:
            if tag not in G:
                continue
            g = G[tag]
            msk = g["eng"] & (g["vego"] < 8.0) & (np.abs(g["bar"]) < 400)
            for a, b in C20.runs(msk, 128):
                seg = C20.native_tap_segment(g, a, b)
                if seg is None or len(seg["T"]) < 64:
                    continue
                P.add({k: v - v.mean() for k, v in seg.items()})
                secs += (b - a) / FS
        if P.n == 0:
            pr("  %s: no data" % grp); continue
        f = P.f
        Gd = -P.tf("T", "r")            # sign -1 as in creep20 §1.1 / plant_id_v278r3_tap
        Gc = -P.tf("T", "r", ref="c")   # command-IV
        coh_Tr, coh_cr, coh_cT = P.coh("T", "r"), P.coh("c", "r"), P.coh("c", "T")
        c282 = cells["V282"]
        pr("\n  %s: %.0f s, %d windows" % (grp, secs, P.n))
        pr("   f Hz   |G|e-3 angG_raw angG_corr coh_Tr | cmdIV |G| ang_corr coh_cr | L=Lfw*G (corr): |L|  angL  | raw angL")
        Lc, Lr = [], []
        fr = []
        for f0 in (8, 10, 12, 14, 16, 18, 19, 20, 20.5, 21, 22, 23, 24):
            i = np.argmin(np.abs(f - f0))
            corr = np.exp(-2j * np.pi * f[i] * TAU_STREAM)   # T lags the rate snapshot by tau -> G measured has +tau lead: remove it
            Lfw = C20.L_fw(c282, f[i], 248.0)
            L1 = Lfw * Gd[i] * corr / 1000.0 * 1000.0
            # units: L_fw is T counts per deg/s ; G is deg/s per T count (x1e-3 shown) -> dimensionless
            L1 = Lfw * (Gd[i] * corr)
            L0 = Lfw * Gd[i]
            Lc.append(L1); Lr.append(L0); fr.append(f[i])
            pr("   %4.1f  %6.1f  %+6.0f   %+6.0f    %.2f  | %6.1f  %+6.0f  %.2f  |  %.2f %+6.0f  |  %+6.0f" % (
                f[i], 1e3 * abs(Gd[i]), np.degrees(np.angle(Gd[i])), np.degrees(np.angle(Gd[i] * corr)), coh_Tr[i],
                1e3 * abs(Gc[i]), np.degrees(np.angle(Gc[i] * corr)), coh_cr[i], abs(L1), np.degrees(np.angle(L1)), np.degrees(np.angle(L0))))
        # -180 crossing of the corrected L over 12-24 Hz on the full grid
        m = (f >= 12) & (f <= 24.5)
        Lg = np.array([C20.L_fw(c282, ff, 248.0) * Gd[i] * np.exp(-2j * np.pi * ff * TAU_STREAM) for i, ff in zip(np.flatnonzero(m), f[m])])
        mg = C20.margins(f[m], Lg, 12, 24.5)
        pr("   corrected L, 12-24.5 Hz: %s" % C20.fmt_m(mg))
        Lg0 = np.array([C20.L_fw(c282, ff, 248.0) * Gd[i] for i, ff in zip(np.flatnonzero(m), f[m])])
        pr("   raw L,       12-24.5 Hz: %s" % C20.fmt_m(C20.margins(f[m], Lg0, 12, 24.5)))
        # is there a resonant bump in |G| off the line?  ratio of |G| at 18-21 to 10-15
        i1 = (f >= 18) & (f <= 21); i0 = (f >= 10) & (f <= 15)
        pr("   |G| 18-21 / |G| 10-15 = %.2f ; coherence 10-15 p50 %.2f, 18-21 p50 %.2f" % (
            np.median(abs(Gd[i1])) / np.median(abs(Gd[i0])), np.median(coh_Tr[i0]), np.median(coh_Tr[i1])))

    with open(os.path.join(SCR, "loopshape20_mode_nature.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    pr("\nwrote _scratch/loopshape20_mode_nature.txt")


if __name__ == "__main__":
    main()
