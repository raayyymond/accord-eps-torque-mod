# -*- coding: utf-8 -*-
"""studies/grind/mode_nature_v289_addenda.py -- two cross-checks asked for by the orchestrator after the re-census started.
Subagent modenat, 2026-09-09.  Analysis only.  Imports the loop build of mode_nature_v289_recensus.py (same electronics, same solver).

A  SIGN CROSS-CHECK of another agent's claim.  On every plant fit (the four 2026-09-08 fits and the four joint refits), the
   closed-loop pole 8-30 Hz under V289 with an ADDED post-lag term  S' = y_post -/+ (S - y) >> 3, where y = the V289 notch output
   (N*S), S - y = (1 - N) S the notched-out component, y_post = the 5.05 Hz output-lag output at 0x2A1AC.  Forward path becomes
   N*Hlag -/+ (1/8)(1 - N) in place of N*Hlag.  zeta before / after for both signs.  Claim under test: the MINUS sign LOWERS zeta and
   the PLUS sign RAISES it on 8/8 fits; and that proportional rate feedback acts as a spring, zeta' = zeta / sqrt(1 + k).
B  FAMILY WIDTH.  Each family's grid re-searched against BOTH measured poles jointly (V282 and V289, medians from the re-census
   episodes) + the off-line tap |G|/angle at 10/15 Hz; every grid plant within delta chi2 <= 4 of the family's best is kept and the
   envelope of its phase (and |G|) at 10-25 Hz reported, per family and pooled.
Run: python mode_nature_v289_addenda.py   (after mode_nature_v289_recensus.py; writes _scratch/mode_nature_v289_addenda.txt)
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.argv = [sys.argv[0]]
import mode_nature_v289_recensus as MN   # noqa: E402

OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def measured():
    E = dict(np.load(os.path.join(MN.SCR, "mode_nature_v289_episodes.npz"), allow_pickle=True))
    okd = np.isfinite(E["gd"]) & (E["gd"] < 0)
    M = {}
    for b in ("V282", "V288", "V289"):
        m = okd & (E["build"] == b)
        M[b] = dict(f=float(np.median(E["f0"][m])), z=float(np.median(E["zeta"][m])), n=int(m.sum()),
                    f_iqr=(float(np.percentile(E["f0"][m], 25)), float(np.percentile(E["f0"][m], 75))))
    return M


def zt_add(a, b, sign=+1.0):
    num = np.polyadd(np.polymul(a.num, b.den), sign * np.polymul(b.num, a.den))
    return MN.ZT(num, np.polymul(a.den, b.den))


def elec_v289_with_term(c, sign):
    """R = F * C * fade * [N*Hlag + sign*(1/8)(1-N)] * K6/32768 * z^-1 ; sign = -1 for S' = y_post - n>>3, +1 for y_post + n>>3."""
    F = MN.ZT([c["fb_b"] / 1024.0, c["fb_b"] / 1024.0], [1.0, -c["fb_a"] / 1024.0])
    kp, kd = float(c["kp_Y"][0]), float(c["kd_Y"][0])
    C = MN.ZT([kp / 256.0 + kd / 8.0, -kd / 8.0], [1.0, 0.0])
    H = MN.ZT([c["lag_b"] / 1024.0 / 32.0, c["lag_b"] / 1024.0 / 32.0], [1.0, -c["lag_a"] / 1024.0])
    N = MN.ZT(MN.NOTCH_B, MN.NOTCH_A)
    one_minus_N = MN.ZT(np.polysub(MN.NOTCH_A, MN.NOTCH_B), MN.NOTCH_A)
    fwd = zt_add(N * H, one_minus_N * (1.0 / 8.0), sign)
    return F * C * fwd * MN.ZT([1.0], [1.0, 0.0]) * (254.0 / 256.0 * c["gain"] / 32768.0)


def main():
    cells = {k: MN.GI.read_cells(p) for k, p in MN.IMG.items()}
    c282, c289 = cells["V282"], cells["V289"]
    M = measured()
    pr("measured (re-census episodes, medians): " + " ; ".join("%s f %.2f z %.3f n %d" % (b, M[b]["f"], M[b]["z"], M[b]["n"]) for b in M))
    R282, R289 = MN.elec(c282), MN.elec(c289, notch=True)
    Rm, Rp = elec_v289_with_term(c289, -1.0), elec_v289_with_term(c289, +1.0)
    zf = lambda f: np.exp(2j * np.pi * f * MN.TS)  # noqa: E731
    for f0 in (7.3, 10.0, 16.5, 20.0, 24.0):
        pr("  forward-path check at %.1f Hz: V289 |R| %.3f %+.0f deg | minus-term |R| %.3f %+.0f | plus-term |R| %.3f %+.0f | (1-N)/8 = %.3f %+.0f deg, N*Hlag = %.4f %+.0f deg" % (
            f0, abs(R289(f0)), np.degrees(np.angle(R289(f0))), abs(Rm(f0)), np.degrees(np.angle(Rm(f0))), abs(Rp(f0)), np.degrees(np.angle(Rp(f0))),
            abs((1 - np.polyval(MN.NOTCH_B, zf(f0)) / np.polyval(MN.NOTCH_A, zf(f0))) / 8), np.degrees(np.angle((1 - np.polyval(MN.NOTCH_B, zf(f0)) / np.polyval(MN.NOTCH_A, zf(f0))) / 8)),
            abs(np.polyval(MN.NOTCH_B, zf(f0)) / np.polyval(MN.NOTCH_A, zf(f0)) * (c289["lag_b"] / 1024 / 32) * (1 + 1 / zf(f0)) / (1 - c289["lag_a"] / 1024 / zf(f0))),
            np.degrees(np.angle(np.polyval(MN.NOTCH_B, zf(f0)) / np.polyval(MN.NOTCH_A, zf(f0)) * (c289["lag_b"] / 1024 / 32) * (1 + 1 / zf(f0)) / (1 - c289["lag_a"] / 1024 / zf(f0))))))

    fits = {}
    for nm, fn in (("2026-09-08", "loopshape20_plants.json"), ("joint-refit", "mode_nature_v289_refits.json")):
        p = os.path.join(MN.SCR, fn)
        if not os.path.exists(p):
            pr("  (%s missing: %s)" % (nm, fn)); continue
        for fam, d in json.load(open(p)).items():
            fits["%s %s" % (nm, fam)] = MN.PlantH(d["g0"], d["tau"], d["f1"], d.get("fp"), d.get("zp"), d.get("kappa"), label=fam)

    pr("\n" + "=" * 150)
    pr("A. SIGN CROSS-CHECK: closed-loop pole 8-30 Hz (least-damped) under V282, V289, V289 + [y_post - n>>3], V289 + [y_post + n>>3]; n = S - y")
    pr("=" * 150)
    pr("  %-28s | %-14s | %-18s | %-18s | %-18s | %s" % ("fit", "V282 f/zeta", "V289 f/zeta", "MINUS f/zeta", "PLUS f/zeta", "verdict on 'minus lowers, plus raises'"))
    for nm, pl in fits.items():
        r = {}
        for lab, R in (("V282", R282), ("V289", R289), ("MINUS", Rm), ("PLUS", Rp)):
            L = MN.loop(R, pl); f, z, _ = MN.dominant(L, 8.0, 30.0); r[lab] = (f, z, MN.unstable_any(L))
        v = "minus %s, plus %s" % ("LOWERS" if r["MINUS"][1] < r["V289"][1] else "RAISES", "RAISES" if r["PLUS"][1] > r["V289"][1] else "LOWERS")
        pr("  %-28s | %5.2f/%7.4f | %5.2f/%7.4f %s | %5.2f/%7.4f %s | %5.2f/%7.4f %s | %s" % (
            nm, r["V282"][0], r["V282"][1], r["V289"][0], r["V289"][1], "UNS" if r["V289"][2] else "   ", r["MINUS"][0], r["MINUS"][1], "UNS" if r["MINUS"][2] else "   ",
            r["PLUS"][0], r["PLUS"][1], "UNS" if r["PLUS"][2] else "   ", v))
    pr("  the 'spring' formula zeta' = zeta/sqrt(1+k): test on a scalar loop-gain multiplier k applied to the WHOLE V289 loop (what a proportional rate-feedback dose does), each fit:")
    for nm, pl in fits.items():
        s = []
        for k in (0.0, 0.25, 0.5, 1.0):
            L = MN.loop(R289 * (1 + k), pl); f, z, _ = MN.dominant(L, 8.0, 30.0); s.append("k %.2f: %.2f/%.4f" % (k, f, z))
        pr("    %-28s %s" % (nm, " ; ".join(s)))

    pr("\n" + "=" * 150)
    pr("B. FAMILY WIDTH: all grid plants within delta chi2 <= 4 of each family's best JOINT fit (V282 + V289 poles + tap |G| 10/15 Hz); phase / |G| envelope 10-25 Hz")
    pr("=" * 150)
    G_OFF = {10: (42.9, -35.0), 15: (41.4, -42.0)}
    FF = np.array([10.0, 12.5, 15.0, 16.5, 18.0, 20.0, 22.0, 25.0])

    def jerr(pl):
        e = 0.0
        for b, R in (("V282", R282), ("V289", R289)):
            L = MN.loop(R, pl); f, z, _ = MN.dominant(L); e += MN.chi2(f, z, M[b]["f"], M[b]["z"], MN.unstable_any(L))
        for f0, (mag, phr) in G_OFF.items():
            g = pl.Gs(f0) * 1e3; phc = phr - 360 * f0 * MN.TAU_STREAM
            e += 0.3 * ((np.log(abs(g)) - np.log(mag)) / 0.4) ** 2 + 0.3 * ((np.degrees(np.angle(g)) - phc) / 20.0) ** 2
        return e

    grids = {
        "smooth": [MN.PlantH(g0, tau * 1e-3, f1, label="smooth") for tau in range(1, 16) for f1 in (1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 30.0) for g0 in np.exp(np.linspace(np.log(0.005), np.log(0.4), 36))],
        "resonant": [MN.PlantH(g0, tau * 1e-3, f1, fp, zp, label="resonant") for fp in np.arange(14.0, 24.01, 0.5) for zp in (0.01, 0.02, 0.03, 0.05, 0.08, 0.12) for tau in (1, 2, 4, 6, 8) for f1 in (2.0, 5.0, 12.0) for g0 in np.exp(np.linspace(np.log(0.003), np.log(0.3), 14))],
        "smooth+mode": [MN.PlantH(g0, tau * 1e-3, f1, fp, zp, label="smooth+mode") for fp in np.arange(14.0, 25.01, 0.5) for zp in (0.05, 0.08, 0.12, 0.18, 0.25, 0.35, 0.5) for tau in (2, 4, 6, 8, 10, 13) for f1 in (3.0, 8.0, 20.0) for g0 in np.exp(np.linspace(np.log(0.01), np.log(0.3), 12))],
        "weak-mode": [MN.PlantH(g0, tau * 1e-3, f1, fp, zp, kappa, label="weak-mode") for fp in np.arange(14.0, 23.01, 0.5) for zp in (0.02, 0.03, 0.05, 0.07, 0.10) for kappa in (0.3, 0.5, 0.8, 1.2) for tau in (4, 7, 10, 13) for f1 in (5.0, 12.0, 30.0) for g0 in np.exp(np.linspace(np.log(0.02), np.log(0.12), 8))],
    }
    pooled = []
    for fam, pls in grids.items():
        errs = np.array([jerr(pl) for pl in pls])
        k = int(np.argmin(errs)); keep = np.flatnonzero(errs <= errs[k] + 4.0)
        pr("\n  %-12s grid %6d, best chi2 %.1f (%s: g0 %.4f tau %.0f ms f1 %g%s), kept %d within +4" % (
            fam, len(pls), errs[k], fam, pls[k].g0, 1e3 * pls[k].tau, pls[k].f1, (" fp %.1f zp %.3f%s" % (pls[k].fp, pls[k].zp, (" k %.1f" % pls[k].kappa) if pls[k].kappa else "")) if pls[k].fp else "", len(keep)))
        if errs[k] > 30:
            pr("    (best chi2 > 30: this family does not fit both poles; its envelope is shown for the record only)")
        PH = np.array([np.degrees(np.angle(pls[i].Gs(FF))) for i in keep]); MG = np.array([1e3 * np.abs(pls[i].Gs(FF)) for i in keep])
        PH = np.where(PH > 60, PH - 360, PH)
        pr("    f Hz      " + " ".join("%7.1f" % f for f in FF))
        pr("    phase min " + " ".join("%+7.0f" % v for v in PH.min(0)))
        pr("    phase best" + " ".join("%+7.0f" % v for v in np.degrees(np.angle(pls[k].Gs(FF)))))
        pr("    phase max " + " ".join("%+7.0f" % v for v in PH.max(0)))
        pr("    |G|e-3 min" + " ".join("%7.1f" % v for v in MG.min(0)))
        pr("    |G|e-3 max" + " ".join("%7.1f" % v for v in MG.max(0)))
        pr("    kept: tau %s ms, f1 %s%s" % (sorted(set(int(round(1e3 * pls[i].tau)) for i in keep)), sorted(set(pls[i].f1 for i in keep)),
                                            ("" if pls[k].fp is None else ", fp %s, zp %s" % (sorted(set(pls[i].fp for i in keep)), sorted(set(pls[i].zp for i in keep))))))
        if errs[k] <= 30:
            pooled += [(PH[j], MG[j]) for j in range(len(keep))]
    if pooled:
        PH = np.array([p[0] for p in pooled]); MG = np.array([p[1] for p in pooled])
        pr("\n  POOLED over the families that fit both poles (%d plants): phase envelope at 10-25 Hz" % len(pooled))
        pr("    f Hz      " + " ".join("%7.1f" % f for f in FF))
        pr("    phase min " + " ".join("%+7.0f" % v for v in PH.min(0)))
        pr("    phase max " + " ".join("%+7.0f" % v for v in PH.max(0)))
        pr("    |G|e-3    " + " ".join("%3.0f-%-3.0f" % (a, b) for a, b in zip(MG.min(0), MG.max(0))))
    with open(os.path.join(MN.SCR, "mode_nature_v289_addenda.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    pr("\nwrote _scratch/mode_nature_v289_addenda.txt")


if __name__ == "__main__":
    main()
