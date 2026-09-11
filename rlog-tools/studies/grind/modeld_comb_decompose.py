# -*- coding: utf-8 -*-
"""studies/grind/modeld_comb_decompose.py -- the THREE-WAY decomposition of the in-band command and
torque energy (camera-locked comb / ring echo / free), the knot characterisation that would size a
LAG-FREE reconstruction, and the V289 pairing.  Subagent `modelrate`, 2026-09-10.  ANALYSIS ONLY.

Supersedes the locked-fraction numbers in MODELD-CADENCE-VS-RING-2026-09-10.md SS 5, which were NOT
bias-corrected.  R2's null floor scales as 1/sqrt(N_eff), so a short stratum (r5e grinding 98.9 s,
measured floor 0.455) is NOT comparable to a long one (r39 grinding 182.0 s, floor 0.161), and r5e's
raw R2 = 0.333 was a NON-DETECTION being read as a zero.  Everything here uses

    R2_deb = sqrt(max(R2^2 - mean(R2_detuned^2), 0))

the standard coherence debiasing, which removes the 1/N_eff bias and is comparable across strata.
Raw and debiased are printed side by side.

Two mechanisms are now on the table and they are cleanly separable [orchestrator, 2026-09-10]:
  * THE COMB      -- modeld's 20 Hz publish knot.  Phase reference: the CAMERA clock.
  * THE ECHO      -- the 0.1 deg/LSB steering-angle quantiser (latcontrol_torque.py:236-237 <-
                     carstate.py:187), entering the command through P only (k_p 0.6, k_d 0).
                     Phase reference: the WHEEL'S OWN RING.  No relation to the camera clock.
So the decomposition regresses each channel on the measured steering angle IN BAND (complex gain g,
which carries the loop delay in its phase), and asks the camera-lock question BOTH before and after
removing the angle-explained part.  The two orders bracket the shared component.

Sections
  A  KNOTS        hold-length and step-size distributions of the plan as it reaches the wire, in
                  curvature units AND in raw 0xE4 counts (the numerator `combsize` asked for);
                  the command's in-band and camera-locked rms in raw counts; intra-hold structure.
  B  3-WAY        camera-locked / angle-explained / free, debiased, per route x band x stratum, and
                  for the GRINDING EXCESS.  Plus the measured angle->command gain against the
                  quantiser prediction, per speed bin.
  C  V289         is the forcing unchanged while the response moved?
  D  RECONSTRUCT  what a slope-continuous reconstruction of desiredCurvature would remove from
                  12-26 Hz, for ZOH vs linear interpolation (costs 50 ms) vs slope extrapolation
                  (zero lag), measured offline on the real 20 Hz model series.

Run: python modeld_comb_decompose.py     (writes _scratch/modeld_comb_decompose.txt
                                          and _scratch/modeld_comb_for_combsize.npz)
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import modeld_cadence_vs_ring as MC     # noqa: E402
import modeld_phase_lock as PL          # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTES = [("r22", "V112 stock map"), ("r35", "V281 rev 3"), ("r39", "V282"),
          ("r5e_v288", "V288 rev 2"), ("r62_v289", "V289 rev 1"), ("r63_v289", "V289 rev 1")]
MC.BAND["r35"] = (18.0, 22.0)
OUT = []
HOTCACHE = os.path.join(SCR, "modeld_hotmask.npz")


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def hr(t):
    pr(); pr("=" * 126); pr(t); pr("=" * 126)


# ======================================================================================================
# the debiased statistic
# ======================================================================================================
def r2_deb(z, t, ic, fm, m):
    """returns (R2 raw, floor = max over detunings, R2 debiased, mean |z|^2, psi deg)."""
    zz = z[m] ** 2
    den = float((np.abs(z[m]) ** 2).sum())
    S = (zz * np.exp(-2j * 2 * np.pi * ((t[m] - ic) * fm))).sum()
    r0 = float(np.abs(S) / den)
    rd = np.array([float(np.abs((zz * np.exp(-2j * 2 * np.pi * ((t[m] - ic) * (fm + d)))).sum()) / den)
                   for d in PL.DET])
    deb = float(np.sqrt(max(r0 ** 2 - float(np.mean(rd ** 2)), 0.0)))
    return r0, float(rd.max()), deb, float(np.mean(np.abs(z[m]) ** 2)), float(np.degrees(0.5 * np.angle(S)))


def coh_deb(zx, za, m):
    """complex in-band regression of zx on za: (|g|, phase deg, gamma^2 raw, gamma^2 debiased, resid)."""
    a, x = za[m], zx[m]
    Saa = float((np.abs(a) ** 2).sum())
    Sxx = float((np.abs(x) ** 2).sum())
    Sxa = (x * np.conj(a)).sum()
    g = Sxa / max(Saa, 1e-300)
    g2 = float(np.abs(Sxa) ** 2 / max(Saa * Sxx, 1e-300))
    # bias of |gamma|^2 for N_eff independent samples is 1/N_eff; estimate N_eff from the
    # coherence of zx against a TIME-REVERSED, circularly-shifted angle (destroys the relation,
    # keeps the marginal statistics)
    nsh = 24
    rng = np.random.default_rng(7)
    sh = []
    ai = np.flatnonzero(m)
    for _ in range(nsh):
        k = int(rng.integers(len(ai) // 8, len(ai) - len(ai) // 8))
        ash = np.roll(za[m], k)
        sh.append(float(np.abs((x * np.conj(ash)).sum()) ** 2 /
                        max(float((np.abs(ash) ** 2).sum()) * Sxx, 1e-300)))
    bias = float(np.mean(sh))
    return float(np.abs(g)), float(np.degrees(np.angle(g))), g2, max(g2 - bias, 0.0), bias, g


# ======================================================================================================
def load_all():
    G, EPS = {}, {}
    cache = dict(np.load(HOTCACHE)) if os.path.exists(HOTCACHE) else {}
    dirty = False
    for tag, build in ROUTES:
        pr("loading %s (%s) ..." % (tag, build))
        G[tag] = MC.load(tag)
        if tag + "_hot" in cache and len(cache[tag + "_hot"]) == len(G[tag]["eng"]):
            hot = cache[tag + "_hot"].astype(bool)
            f0 = cache[tag + "_f0"]
            pr("  hot mask from cache (%.1f s)" % (hot.sum() * G[tag]["P18"]))
        else:
            eps, hot = MC.episodes_of(G[tag])
            f0 = np.array([e[2] for e in eps]) if eps else np.zeros(0)
            cache[tag + "_hot"] = hot
            cache[tag + "_f0"] = f0
            dirty = True
            pr("  %d episodes, %.1f s hot" % (len(eps), hot.sum() * G[tag]["P18"]))
        EPS[tag] = (f0, hot)
    if dirty:
        np.savez_compressed(HOTCACHE, **cache)
    return G, EPS


def strata(g, hot):
    base = g["eng"] & (g["vego"] < 12) & (np.abs(g["bar"]) < 400) & ~hot
    return base, g["eng"] & hot


# ======================================================================================================
# SECTION A -- the knots
# ======================================================================================================
def secA(G, EPS, dump):
    hr("SECTION A -- THE KNOT, MEASURED (what would size a lag-free reconstruction)")
    pr("The plan `modelV2.action.desiredCurvature` updates once per camera frame (19.9986-19.9997 Hz)")
    pr("and controlsd runs at 99.55 Hz, so a knot falls every 4.978 command frames on average.")
    pr("`clip_curvature` NEVER binds (0.000 everywhere, MODELD-CADENCE-VS-RING SS 2), so EVERY knot in")
    pr("this record is the staircase STEPPING, not the limiter engaging.")
    pr()
    pr("A.1  The command's sensitivity to the plan, measured (not assumed): OLS of the raw 0xE4")
    pr("     command on carControl.actuators.torque over engaged frames, and on desiredCurvature.")
    pr("%-10s %10s %10s %10s %12s" % ("route", "cnt/torque", "R^2", "n", "cnt per 1e-4 1/m"))
    pr("-" * 126)
    SENS = {}
    for tag, build in ROUTES:
        g = G[tag]
        M = g["M"]
        tq = np.interp(g["t"], M["cc_t"], M["cc_torque"])
        dc = np.interp(g["t"], M["cs_t"], M["cs_descurv"])
        m = g["eng"]
        A = np.vstack([tq[m], np.ones(m.sum())]).T
        c, *_ = np.linalg.lstsq(A, g["cmd"][m], rcond=None)
        res = g["cmd"][m] - A @ c
        r2 = 1 - res.var() / g["cmd"][m].var()
        # curvature -> counts, in band (the quantity a reconstruction changes), via the in-band
        # regression of cmd on desiredCurvature at 18-22 Hz
        fs = 1.0 / g["P18"]
        zc = PL.analytic(g["cmd"], fs, 18.0, 22.0)
        zd = PL.analytic(dc, fs, 18.0, 22.0)
        gg = (zc[m] * np.conj(zd[m])).sum() / max(float((np.abs(zd[m]) ** 2).sum()), 1e-300)
        SENS[tag] = (float(c[0]), float(np.abs(gg)))
        pr("%-10s %10.1f %10.4f %10d %12.1f" % (tag, c[0], r2, m.sum(), np.abs(gg) * 1e-4))
    pr()
    pr("A.2  HOLD LENGTH of desiredCurvature in 100 Hz controlsd ticks, and STEP SIZE at the knots.")
    pr("     Step size is the jump at a hold boundary; `cnt` converts it with the in-band")
    pr("     counts-per-curvature gain of A.1, i.e. it is the step the 0xE4 command would carry.")
    pr()
    pr("%-10s %-9s %8s %7s %7s %7s | %11s %11s %11s | %9s %9s" %
       ("route", "stratum", "n holds", "h=4", "h=5", "h=6",
        "|step| p25", "|step| p50", "|step| p75", "p50 cnt", "rms cnt"))
    pr("-" * 126)
    for tag, build in ROUTES:
        g = G[tag]
        M = g["M"]
        f0, hot = EPS[tag]
        t100, dc = M["cs_t"], M["cs_descurv"]
        v = np.interp(t100, M["st_t"], M["st_v"])
        lat = np.interp(t100, M["cc_t"], M["cc_latact"]) > 0.5
        eng = lat & (M["cs_active"] > 0.5)
        h100 = np.interp(t100, g["t"], hot.astype(float)) > 0.5
        ch = np.r_[True, dc[1:] != dc[:-1]]
        idx = np.flatnonzero(ch)
        hold = np.diff(idx)
        st = idx[:-1]
        step = np.abs(np.diff(dc[idx]))
        for slab, mm in (("quiet", eng & (v < 12) & ~h100), ("grinding", eng & h100)):
            ok = mm[st]
            h, s = hold[ok], step[ok]
            if len(h) < 50:
                pr("%-10s %-9s %8d  (too few)" % (tag, slab, len(h))); continue
            cpc = SENS[tag][1]
            pr("%-10s %-9s %8d %7.3f %7.3f %7.3f | %11.3e %11.3e %11.3e | %9.2f %9.2f" %
               (tag, slab, len(h), (h == 4).mean(), (h == 5).mean(), (h == 6).mean(),
                np.percentile(s, 25), np.percentile(s, 50), np.percentile(s, 75),
                np.percentile(s, 50) * cpc, np.sqrt(np.mean(s ** 2)) * cpc))
    pr()
    pr("A.3  INTRA-HOLD STRUCTURE: is the plan flat between knots?  (rms deviation of")
    pr("     desiredCurvature from its own hold mean, over holds of length >= 4)")
    pr("%-10s %-9s %12s %12s" % ("route", "stratum", "rms in-hold", "as frac of step p50"))
    pr("-" * 126)
    for tag, build in ROUTES:
        g = G[tag]
        M = g["M"]
        f0, hot = EPS[tag]
        t100, dc = M["cs_t"], M["cs_descurv"]
        v = np.interp(t100, M["st_t"], M["st_v"])
        lat = np.interp(t100, M["cc_t"], M["cc_latact"]) > 0.5
        eng = lat & (M["cs_active"] > 0.5)
        ch = np.r_[True, dc[1:] != dc[:-1]]
        idx = np.flatnonzero(ch)
        dev, stp = [], []
        for a, b in zip(idx[:-1], idx[1:]):
            if b - a < 4 or not eng[a] or v[a] >= 12:
                continue
            seg = dc[a:b]
            dev.append(np.sqrt(np.mean((seg - seg.mean()) ** 2)))
            stp.append(abs(dc[b] - dc[a]))
        if len(dev) < 50:
            pr("%-10s %-9s   (too few holds)" % (tag, "eng v<12")); continue
        pr("%-10s %-9s %12.3e %12.4f" % (tag, "eng v<12", np.mean(dev),
                                         np.mean(dev) / max(np.median(stp), 1e-300)))
    pr()
    pr("     (a value of 0.0000 means a PURE ZOH: the plan is bit-identical inside every hold, so the")
    pr("      knot is a pure slope discontinuity and there is nothing to remove but the discontinuity.)")
    pr()
    pr("A.4  THE NUMERATOR `combsize` ASKED FOR -- in-band (18-22 Hz) command content in RAW 0xE4")
    pr("     COUNTS, rms, and the camera-locked part of it (debiased).  rms = sqrt(mean|z|^2 / 2).")
    pr()
    pr("%-10s %-9s %7s %11s %11s %11s %9s" %
       ("route", "stratum", "n s", "cmd rms", "cmd locked", "bar rms", "bar locked"))
    pr("-" * 126)
    for tag, build in ROUTES:
        g = G[tag]
        f0, hot = EPS[tag]
        base, grind = strata(g, hot)
        fs = 1.0 / g["P18"]
        zc = PL.analytic(g["cmd"], fs, 18.0, 22.0)
        zb = PL.analytic(g["bar"], fs, 18.0, 22.0)
        for slab, m in (("quiet", base), ("grinding", grind)):
            if m.sum() < 800:
                pr("%-10s %-9s %7.1f  (too few)" % (tag, slab, m.sum() * g["P18"])); continue
            _, _, dc_, ec, _ = r2_deb(zc, g["t"], g["model_icept"], g["f_model"], m)
            _, _, db_, eb, _ = r2_deb(zb, g["t"], g["model_icept"], g["f_model"], m)
            pr("%-10s %-9s %7.1f %11.2f %11.2f %11.2f %9.2f" %
               (tag, slab, m.sum() * g["P18"], np.sqrt(ec / 2), np.sqrt(dc_ * ec / 2),
                np.sqrt(eb / 2), np.sqrt(db_ * eb / 2)))
        dump[tag + "_hold"] = np.array([0.0])
    return SENS


# ======================================================================================================
# SECTION B -- the three-way decomposition
# ======================================================================================================
def secB(G, EPS):
    hr("SECTION B -- THREE-WAY DECOMPOSITION: camera-locked comb / angle echo / free")
    pr("For each channel x and the measured steering angle a (0x14A, 0.1 deg/LSB), both band-passed and")
    pr("Hilberted:  g = <z_x, z_a>/<z_a, z_a>  (complex: |g| is the gain, arg g the loop delay);")
    pr("gamma^2 = the fraction of x's in-band energy linearly explained by a, debiased by 24 circular")
    pr("shifts of a.  R2_deb is the camera-locked fraction.  `R2 perp` repeats the camera test on the")
    pr("RESIDUAL x - g*a, i.e. the camera lock that SURVIVES removing the angle echo.  The pair")
    pr("(R2_deb, R2 perp) brackets the shared part: R2 perp is the lower bound on the comb.")
    pr()
    for tag, build in ROUTES:
        g = G[tag]
        f0, hot = EPS[tag]
        base, grind = strata(g, hot)
        fs = 1.0 / g["P18"]
        bands = [(18.0, 22.0)] + ([MC.BAND[tag]] if MC.BAND[tag] != (18.0, 22.0) else [])
        pr("-" * 126)
        pr("%s  %s   f_model %.6f" % (tag, build, g["f_model"]))
        for lo, hi in bands:
            za = PL.analytic(g["ang"], fs, lo, hi)
            pr("  band %g-%g Hz" % (lo, hi))
            pr("  %-14s %-9s %7s %9s %8s %8s %8s %9s %9s %9s" %
               ("channel", "stratum", "n s", "E", "R2 raw", "floor", "R2_deb", "gamma^2", "R2 perp", "|g| c/deg"))
            for nm, x in (("0xE4 cmd", g["cmd"]), ("bar", g["bar"]), ("wheel rate", g["wire"].astype(float))):
                zx = PL.analytic(x, fs, lo, hi)
                for slab, m in (("quiet", base), ("grinding", grind)):
                    if m.sum() < 800:
                        pr("  %-14s %-9s %7.1f  (too few)" % (nm, slab, m.sum() * g["P18"])); continue
                    r0, fl, deb, e, psi = r2_deb(zx, g["t"], g["model_icept"], g["f_model"], m)
                    ag, aph, g2, g2d, bias, gc = coh_deb(zx, za, m)
                    zr = zx - gc * za
                    _, _, debp, _, _ = r2_deb(zr, g["t"], g["model_icept"], g["f_model"], m)
                    pr("  %-14s %-9s %7.1f %9.4g %8.4f %8.4f %8.4f %9.4f %9.4f %9.1f" %
                       (nm, slab, m.sum() * g["P18"], e, r0, fl, deb, g2d, debp, ag))
            pr()
    pr("-" * 126)
    pr("THE GRINDING EXCESS, decomposed the same way (dE = E_grind - E_quiet; the excess is what we")
    pr("are trying to explain, not the total).  All fractions debiased.")
    pr()
    pr("%-10s %-16s %10s %10s %10s %10s %10s %10s" %
       ("route", "channel/band", "E quiet", "E grind", "dE", "dE cam", "dE echo", "dE free"))
    pr("-" * 126)
    for tag, build in ROUTES:
        g = G[tag]
        f0, hot = EPS[tag]
        base, grind = strata(g, hot)
        if base.sum() < 800 or grind.sum() < 800:
            pr("%-10s  (a stratum too small: quiet %.1f s, grinding %.1f s)"
               % (tag, base.sum() * g["P18"], grind.sum() * g["P18"])); continue
        fs = 1.0 / g["P18"]
        bands = [(18.0, 22.0)] + ([MC.BAND[tag]] if MC.BAND[tag] != (18.0, 22.0) else [])
        for lo, hi in bands:
            za = PL.analytic(g["ang"], fs, lo, hi)
            for nm, x in (("0xE4 cmd", g["cmd"]), ("bar", g["bar"])):
                zx = PL.analytic(x, fs, lo, hi)
                row = []
                for m in (base, grind):
                    _, _, deb, e, _ = r2_deb(zx, g["t"], g["model_icept"], g["f_model"], m)
                    _, _, _, g2d, _, _ = coh_deb(zx, za, m)
                    row.append((e, deb * e, g2d * e))
                (eq, cq, hq), (eg, cg, hgv) = row
                pr("%-10s %-16s %10.4g %10.4g %10.4g %10.4g %10.4g %10.4g" %
                   (tag, "%s %g-%g" % (nm, lo, hi), eq, eg, eg - eq, cg - cq, hgv - hq,
                    (eg - eq) - (cg - cq) - (hgv - hq)))
    pr()
    pr("(dE cam and dE echo can overlap -- the angle echo of a comb-driven ring is coherent with BOTH")
    pr(" references.  Read dE free as the part NEITHER explains; read `R2 perp` above for the comb's")
    pr(" lower bound after the echo is removed.)")
    pr()
    pr("B.2  THE ANGLE-QUANTISER GAIN CHECK, per speed bin.  `oplpf` predicts 1 LSB (0.1 deg) of")
    pr("     steering angle is worth 13.2 raw 0xE4 counts at 5 m/s, 20.6 at 15, 52.8 at 30 -- i.e.")
    pr("     132 / 206 / 528 counts per DEGREE, through P only (k_p 0.6, k_d 0).  Measured |g| is the")
    pr("     in-band regression of the 0xE4 command on the measured angle, in counts per degree.")
    pr()
    pr("%-10s %-10s %8s %11s %11s %10s" % ("route", "v bin m/s", "n s", "|g| c/deg", "arg g deg", "gamma^2"))
    pr("-" * 126)
    for tag, build in ROUTES:
        g = G[tag]
        fs = 1.0 / g["P18"]
        za = PL.analytic(g["ang"], fs, 18.0, 22.0)
        zc = PL.analytic(g["cmd"], fs, 18.0, 22.0)
        for vlo, vhi in ((0, 8), (8, 16), (16, 24), (24, 40)):
            m = g["eng"] & (g["vego"] >= vlo) & (g["vego"] < vhi)
            if m.sum() < 2000:
                continue
            ag, aph, g2, g2d, bias, _ = coh_deb(zc, za, m)
            pr("%-10s %-10s %8.1f %11.1f %11.1f %10.4f" %
               (tag, "%d-%d" % (vlo, vhi), m.sum() * g["P18"], ag, aph, g2d))


# ======================================================================================================
# SECTION C -- V289
# ======================================================================================================
def secC(G, EPS):
    hr("SECTION C -- V289: IS THE FORCING UNCHANGED WHILE THE RESPONSE MOVED?")
    pr("The orchestrator's reading to test: V289's 20.04 Hz Q3 notch removed the loop's RESPONSE at the")
    pr("comb frequency, leaving a different, non-comb-driven mode at 16.5 Hz.  If so, the FORCING")
    pr("(measured on the command, upstream of the EPS) must be UNCHANGED at 20 Hz while the bar's")
    pr("camera-locked fraction COLLAPSES.")
    pr()
    pr("%-10s %-16s %10s %10s %10s %10s %10s" %
       ("route", "build", "cmd d2 comb", "cmd R2_deb", "bar E 18-22", "bar R2_deb", "bar R2_deb 13-18"))
    pr("-" * 126)
    for tag, build in ROUTES:
        g = G[tag]
        f0, hot = EPS[tag]
        base, grind = strata(g, hot)
        fs = 1.0 / g["P18"]
        m = grind if grind.sum() >= 800 else g["eng"]
        # the forcing, measured on the command's |D2| model-phase fold (upstream of the EPS)
        e4 = g["e4"]
        d2 = np.r_[0.0, 0.0, e4["cmd"][2:] - 2 * e4["cmd"][1:-1] + e4["cmd"][:-2]]
        hm = np.interp(e4["t"], g["t"], hot.astype(float)) > 0.5
        me = e4["eng"] & (hm if hm.sum() > 3000 else (e4["v"] < 12))
        ph = MC.model_phase(g, e4["t"])
        C, R = MC.fold_stats(np.abs(d2[me]), ph[me])
        zc = PL.analytic(g["cmd"], fs, 18.0, 22.0)
        zb = PL.analytic(g["bar"], fs, 18.0, 22.0)
        _, _, dcm, _, _ = r2_deb(zc, g["t"], g["model_icept"], g["f_model"], m)
        _, _, dbm, eb, _ = r2_deb(zb, g["t"], g["model_icept"], g["f_model"], m)
        zl = PL.analytic(g["bar"], fs, 13.0, 18.0)
        _, _, dbl, _, _ = r2_deb(zl, g["t"], g["model_icept"], g["f_model"], m)
        pr("%-10s %-16s %10.4f %10.4f %10.4g %10.4f %10.4f" % (tag, build, R, dcm, eb, dbm, dbl))
    pr()
    pr("(cmd d2 comb = Rayleigh R of the |D2cmd| model-phase fold in the grinding stratum -- the")
    pr(" FORCING, measured on the wire upstream of the EPS.  Detuned null for that column is")
    pr(" 0.004-0.043 on every route.)")


# ======================================================================================================
# SECTION D -- the reconstruction
# ======================================================================================================
def secD(G, EPS):
    hr("SECTION D -- WHAT A SLOPE-CONTINUOUS RECONSTRUCTION WOULD REMOVE (sizing only, not a design)")
    pr("Applied OFFLINE to the real 20 Hz `modelV2.action.desiredCurvature` series of each route, then")
    pr("resampled to the 100 Hz controlsd tick grid by each rule, engaged & v<12 only:")
    pr("  ZOH     hold the last received value            -- what runs today")
    pr("  LERP    linear between the last two RECEIVED    -- slope-continuous, costs ONE model frame")
    pr("          values                                     (50 ms) of lag")
    pr("  EXTRAP  linear extrapolation from the last two  -- slope-continuous, ZERO added lag")
    pr("          received values                            (it leads the ZOH by ~half a frame)")
    pr("Energy is reported in the 12-26 Hz band and the 18-22 Hz sub-band, as a fraction of ZOH.")
    pr()
    pr("%-10s %9s %12s %12s %12s | %12s %12s %12s" %
       ("route", "n s", "ZOH 12-26", "LERP 12-26", "EXTRAP 12-26", "ZOH 18-22", "LERP 18-22", "EXTRAP 18-22"))
    pr("-" * 126)
    for tag, build in ROUTES:
        g = G[tag]
        M = g["M"]
        tm, cm = M["mdl_t"], M["mdl_curv"]
        t100 = M["cs_t"]
        v = np.interp(t100, M["st_t"], M["st_v"])
        lat = np.interp(t100, M["cc_t"], M["cc_latact"]) > 0.5
        m = lat & (M["cs_active"] > 0.5) & (v < 12)
        if m.sum() < 3000:
            continue
        j = np.clip(np.searchsorted(tm, t100) - 1, 1, len(tm) - 1)
        dtm = np.diff(tm, prepend=tm[0])
        zoh = cm[j]
        slope = np.where(dtm[j] > 0, (cm[j] - cm[j - 1]) / np.maximum(dtm[j], 1e-9), 0.0)
        age = t100 - tm[j]
        extrap = cm[j] + slope * age
        # LERP between the last two received values, i.e. one frame of lag
        lerp = cm[j - 1] + slope * age
        fs100 = 1.0 / np.median(np.diff(t100))
        row = []
        for lo, hi in ((12.0, 26.0), (18.0, 22.0)):
            es = []
            for y in (zoh, lerp, extrap):
                z = PL.analytic(y, fs100, lo, hi)
                es.append(float(np.mean(np.abs(z[m]) ** 2)))
            row.append(es)
        a, b = row
        pr("%-10s %9.1f %12.4g %12.4f %12.4f | %12.4g %12.4f %12.4f" %
           (tag, m.sum() / fs100, a[0], a[1] / a[0], a[2] / a[0], b[0], b[1] / b[0], b[2] / b[0]))
    pr()
    pr("NOTE the honest caveats: LERP is what a colleague's LPF is NOT (it does not attenuate the")
    pr("band, it removes the DISCONTINUITY) but it does cost 50 ms of lag.  EXTRAP costs none and")
    pr("can overshoot on a slope reversal -- its cost is overshoot, not delay.  `modeld` already")
    pr("applies smooth_value(..., LAT_SMOOTH_SECONDS = 0.1) at modeld.py:346,375 BEFORE publishing,")
    pr("so the residual measured here is what that smoothing LEAVES.")


# ======================================================================================================
def main():
    G, EPS = load_all()
    dump = {}
    SENS = secA(G, EPS, dump)
    secB(G, EPS)
    secC(G, EPS)
    secD(G, EPS)
    # dump for combsize
    for tag, build in ROUTES:
        g = G[tag]
        M = g["M"]
        f0, hot = EPS[tag]
        t100, dc = M["cs_t"], M["cs_descurv"]
        v = np.interp(t100, M["st_t"], M["st_v"])
        lat = np.interp(t100, M["cc_t"], M["cc_latact"]) > 0.5
        eng = lat & (M["cs_active"] > 0.5)
        h100 = np.interp(t100, g["t"], hot.astype(float)) > 0.5
        ch = np.r_[True, dc[1:] != dc[:-1]]
        idx = np.flatnonzero(ch)
        dump[tag + "_hold_len"] = np.diff(idx).astype(np.int32)
        dump[tag + "_step_curv"] = np.diff(dc[idx])
        dump[tag + "_hold_eng"] = eng[idx[:-1]]
        dump[tag + "_hold_v"] = v[idx[:-1]]
        dump[tag + "_hold_grind"] = h100[idx[:-1]]
        dump[tag + "_cnt_per_curv"] = np.array([SENS[tag][1]])
        dump[tag + "_cnt_per_torque"] = np.array([SENS[tag][0]])
        dump[tag + "_f_model"] = np.array([g["f_model"]])
        dump[tag + "_model_icept"] = np.array([g["model_icept"]])
        dump[tag + "_P18"] = np.array([g["P18"]])
        dump[tag + "_Pe4"] = np.array([g["e4"]["P"]])
    np.savez_compressed(os.path.join(SCR, "modeld_comb_for_combsize.npz"), **dump)
    with open(os.path.join(SCR, "modeld_comb_decompose.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/modeld_comb_decompose.txt and _scratch/modeld_comb_for_combsize.npz")


if __name__ == "__main__":
    main()
