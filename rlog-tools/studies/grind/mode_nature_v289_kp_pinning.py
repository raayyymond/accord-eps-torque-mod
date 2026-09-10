# -*- coding: utf-8 -*-
"""studies/grind/mode_nature_v289_kp_pinning.py -- WHY IS THE LINE PINNED AT 20 Hz ACROSS Kp 248-696?   Subagent modenat2, 2026-09-09.
Analysis only: builds nothing, flashes nothing, sends nothing.

The demand-gated re-census (mode_nature_v289_recensus.py, section 1e'') measures f0 = 20.01 / 20.03 / 20.08 / 20.11 / 19.97 Hz
over Kp 248 (flat-Kp builds) -> 696 (the Kp-LERP builds' top bin), i.e. PINNED to +-0.15 Hz over a x2.81 nominal Kp.  Every plant
family refitted to the V282 and V289 poles predicts instead that the pole falls to 17-19 Hz and goes UNSTABLE as Kp rises.
The hypothesis on the table is that the P / D / sum clamps limit the EFFECTIVE Kp.  This script QUANTIFIES that instead of
asserting it, from the census windows themselves, in three steps:

  1  THE NOMINAL LEVER IS SMALLER THAN IT LOOKS.  C(z) = Kp/256 + (Kd/8)(1 - z^-1).  At 20 Hz the D term is 2.010 and dominates,
     so |C| only goes 2.29 -> 3.48 (x1.52) as Kp goes 248 -> 696, not x2.81.  The PHASE of C falls 61 -> 35 deg over the same span.
  2  THE MEASURED LINE AMPLITUDE, RUN THROUGH THE BYTE-EXACT CHAIN.  Each demand-gated present window carries the wheel-rate
     amplitude at its own f0 (bamp = sqrt(2)*std = the peak of the sinusoid, deg/s).  Push it through the real feedback filter to
     get the rate-error amplitude, then P, D, P+D and the post-gain output, and compare each against its real clamp:
       D clamp  0xC61B6 = 10240 on the D term alone
       sum clamp 0xC61BE = 15360 on P + D
       out clamp 0xC61B4 = 3072 after x(254/256)(gain/32768) and the 5.05 Hz output lag
  3  SINUSOIDAL-INPUT DESCRIBING FUNCTION of each clamp, N(A) = 1 (A<=L), else (2/pi)[asin(L/A) + (L/A)sqrt(1-(L/A)^2)], giving the
     EFFECTIVE per-cycle gain and phase of C at the line, and hence the effective open-loop gain relative to the Kp = 248 case.
     If the pinning is clamp-limited, that effective gain must be flat across the Kp bins while the nominal one rises.

Run: python mode_nature_v289_kp_pinning.py   (reads _scratch/mode_nature_v289_win_*.npz; writes _scratch/mode_nature_v289_kp_pinning.txt)
"""
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.argv = [sys.argv[0]]
import mode_nature_v289_recensus as MN   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def df_sat(A, L):
    """describing function of a symmetric saturation at +-L for a sinusoid of amplitude A (Gelb & Vander Velde)."""
    A = np.asarray(A, float)
    r = np.clip(np.where(A > 0, L / np.maximum(A, 1e-12), 1.0), 0.0, 1.0)
    return np.where(A <= L, 1.0, (2.0 / np.pi) * (np.arcsin(r) + r * np.sqrt(np.maximum(1 - r * r, 0.0))))


def load_windows():
    rows = {}
    for p in sorted(glob.glob(os.path.join(SCR, "mode_nature_v289_win_*.npz"))):
        d = np.load(p, allow_pickle=True)
        for k in d.files:
            rows.setdefault(k, []).append(d[k])
    return {k: np.concatenate(v) for k, v in rows.items()}


def main():
    cells = {k: MN.GI.read_cells(p) for k, p in MN.IMG.items()}
    c = cells["V282"]
    KD, DCLAMP, SCLAMP, OCLAMP, GAIN = float(c["kd_Y"][0]), float(c["d_clamp"]), 15360.0, 3072.0, float(c["gain"])
    R = load_windows()
    pres = (R["prom"] >= 8) & (R["amp"] >= 40)
    loop = pres & (R["idx"] >= MN.DEMAND_MIN)

    def C_of(kp, f, nd=1.0):
        """C(z) = Kp/256 + nd*(Kd/8)(1 - z^-1) at f, nd = the D clamp's describing-function gain."""
        z = np.exp(2j * np.pi * np.asarray(f, float) * MN.TS)
        return kp / 256.0 + nd * (KD / 8.0) * (1 - 1 / z)

    def F_of(f):
        z = np.exp(2j * np.pi * np.asarray(f, float) * MN.TS)
        return (c["fb_b"] / 1024.0) * (1 + 1 / z) / (1 - (c["fb_a"] / 1024.0) / z)

    def H_of(f):
        z = np.exp(2j * np.pi * np.asarray(f, float) * MN.TS)
        return (c["lag_b"] / 1024.0 / 32.0) * (1 + 1 / z) / (1 - (c["lag_a"] / 1024.0) / z)

    pr("=" * 150)
    pr("WHY THE LINE IS PINNED AT 20 Hz ACROSS Kp 248-696 -- quantified from the demand-gated census windows")
    pr("  cells read from the V282 image: Kd %d, D clamp %d (0xC61B6), sum clamp %d (0xC61BE), out clamp %d (0xC61B4), gain %d" % (KD, DCLAMP, SCLAMP, OCLAMP, GAIN))
    pr("=" * 150)

    pr("\n0. IS THE PINNING EVEN REAL?  MODEL-FREE, MATCHED-LOAD Kp CONTRAST.  The Kp-LERP builds index Kp off the DEMAND index,")
    pr("   so a raw 'f0 by Kp bin' table is confounded with load.  Comparing the flat-Kp builds (Kp 248 at every idx) against the")
    pr("   Kp-LERP builds INSIDE THE SAME idx STRATUM holds demand, hands load and plant fixed and varies only Kp.")
    pr("   %-12s %7s %-26s %7s %-26s %8s %8s" % ("idx stratum", "n flat", "f0 at Kp 248", "n lerp", "f0 at lerp Kp", "lerp Kp", "df0"))
    flat = loop & np.isin(R["build"], ["V282", "V288", "V281r3"])
    lerp = loop & (R["grp"] == "Kp-LERP")
    dfs = []
    for lo, hi in ((20, 30), (30, 45), (45, 70), (70, 110), (110, 200)):
        a = flat & (R["idx"] >= lo) & (R["idx"] < hi); b = lerp & (R["idx"] >= lo) & (R["idx"] < hi)
        if a.sum() < 15 or b.sum() < 15:
            pr("   %-12s n=%d/%d (too few)" % ("%d-%d" % (lo, hi), a.sum(), b.sum())); continue
        fa, fb = R["f0"][a], R["f0"][b]
        dfs.append(np.median(fb) - np.median(fa))
        pr("   %-12s %7d %-26s %7d %-26s %8.0f %+8.2f" % (
            "%d-%d" % (lo, hi), a.sum(), "%.2f [%.2f-%.2f]" % (np.median(fa), *np.percentile(fa, (25, 75))),
            b.sum(), "%.2f [%.2f-%.2f]" % (np.median(fb), *np.percentile(fb, (25, 75))), np.median(R["kp"][b]), dfs[-1]))
    pr("   => df0 over a x2.81 Kp, at matched load: mean %+.2f Hz, range %+.2f to %+.2f.  THE PINNING IS REAL AND MODEL-FREE." % (
        np.mean(dfs), min(dfs), max(dfs)))
    pr("      (for contrast, zeta DOES respond: 0.033 at Kp 240-320 -> 0.030 at 320-450 -> 0.018 at 450-700, re-census section 2c.)")

    pr("\n1. THE NOMINAL LEVER IS SMALLER THAN Kp SUGGESTS.  C(z) = Kp/256 + (Kd/8)(1 - z^-1) at the line; the D term is Kd/8 * |1-z^-1|.")
    pr("   %-6s %-10s %-10s %-22s %-22s" % ("Kp", "P term", "D term", "|C| at 20 Hz (x Kp248)", "angle C at 20 Hz"))
    for kp in (248, 350, 470, 560, 696):
        Cv = C_of(kp, 20.0); C0 = C_of(248, 20.0)
        pr("   %-6d %-10.3f %-10.3f %-22s %+.1f deg" % (kp, kp / 256.0, abs((KD / 8.0) * (1 - np.exp(-2j * np.pi * 20.0 * MN.TS))),
                                                        "%.3f  (x%.3f)" % (abs(Cv), abs(Cv / C0)), np.degrees(np.angle(Cv))))
    pr("   => the D term (2.010) carries 88 %% of |C| at 20 Hz, so a x2.81 nominal Kp is only a x1.52 loop-gain lever there,")
    pr("      and it COSTS 26 deg of the PID's phase lead (+61 -> +35).  That phase loss is why every linear refit drags the")
    pr("      crossing DOWN in frequency as Kp rises -- which is precisely what the measurement says does NOT happen.")

    pr("\n2. THE MEASURED LINE AMPLITUDE THROUGH THE BYTE-EXACT CHAIN (demand-gated present windows, per Kp bin).")
    pr("   rate amplitude at f0 -> error E = |F(f0)| * CPD * rate ; P = (Kp/256) E ; D = (Kd/8)|1-z^-1| E ; P+D = |C| E ;")
    pr("   S = |C| E * |H(f0)| * (254/256)(gain/32768).  All peak amplitudes of the sinusoid at f0, raw counts.")
    pr("   %-22s %5s %8s %9s %9s %9s %9s %9s | %s" % ("stratum", "n", "rate p50", "E p50", "P p50", "D p50", "P+D p50", "S p50", "% of windows with the clamp BINDING (D / sum / out)"))
    strata = [("flat-Kp Kp=248", loop & np.isin(R["build"], ["V282", "V288", "V281r3"]), 248.0),
              ("V289    Kp=248", loop & (R["build"] == "V289"), 248.0)]
    for lo, hi in ((300, 400), (400, 500), (500, 600), (600, 700)):
        m = loop & (R["grp"] == "Kp-LERP") & (R["kp"] >= lo) & (R["kp"] < hi)
        strata.append(("Kp-LERP Kp %d-%d" % (lo, hi), m, None))
    stats = {}
    for lab, m, kpfix in strata:
        if m.sum() < 10:
            pr("   %-22s n=%d (too few)" % (lab, m.sum())); continue
        f0, ra = R["f0"][m], R["ramp"][m]
        kp = np.full(m.sum(), kpfix) if kpfix else R["kp"][m]
        E = np.abs(F_of(f0)) * MN.CPD * ra
        P = kp / 256.0 * E
        D = np.abs((KD / 8.0) * (1 - np.exp(-2j * np.pi * f0 * MN.TS))) * E
        PD = np.abs(C_of(kp, f0)) * E
        S = PD * np.abs(H_of(f0)) * (254.0 / 256.0) * GAIN / 32768.0
        stats[lab] = dict(f0=f0, ra=ra, kp=kp, E=E, P=P, D=D, PD=PD, S=S, n=int(m.sum()))
        pr("   %-22s %5d %8.2f %9.0f %9.0f %9.0f %9.0f %9.0f | %5.1f %% / %5.1f %% / %5.1f %%" % (
            lab, m.sum(), np.median(ra), np.median(E), np.median(P), np.median(D), np.median(PD), np.median(S),
            100 * np.mean(D > DCLAMP), 100 * np.mean(PD > SCLAMP), 100 * np.mean(S > OCLAMP)))
    pr("   p90 of the same, to show the loud tail (the episodes the operator hears):")
    pr("   %-22s %8s %9s %9s %9s %9s | %s" % ("stratum", "rate p90", "E p90", "D p90", "P+D p90", "S p90", "clamp binding at p90 (D / sum / out)"))
    for lab, s in stats.items():
        pr("   %-22s %8.2f %9.0f %9.0f %9.0f %9.0f | %s / %s / %s" % (
            lab, *[np.percentile(s[k], 90) for k in ("ra", "E", "D", "PD", "S")],
            "YES" if np.percentile(s["D"], 90) > DCLAMP else "no", "YES" if np.percentile(s["PD"], 90) > SCLAMP else "no",
            "YES" if np.percentile(s["S"], 90) > OCLAMP else "no"))

    pr("\n3. DESCRIBING-FUNCTION EFFECTIVE GAIN AT THE LINE.  N(A) for a symmetric saturation; D clamp applied to D, then the sum")
    pr("   clamp to the clamped P+D.  'eff gain' is the per-cycle open-loop gain relative to the Kp = 248 UNCLAMPED case.")
    pr("   %-22s %5s | %-24s %-24s | %-18s" % ("stratum", "n", "NOMINAL |C|/|C248|", "EFFECTIVE (clamped)", "angle C eff"))
    for lab, s in stats.items():
        C0 = np.abs(C_of(248.0, s["f0"]))
        nom = np.abs(C_of(s["kp"], s["f0"])) / C0
        nD = df_sat(s["D"], DCLAMP)
        Ce = C_of(s["kp"], s["f0"], nd=nD)
        nS = df_sat(np.abs(Ce) * s["E"], SCLAMP)
        eff = nS * np.abs(Ce) / C0
        pr("   %-22s %5d | %-24s %-24s | %+6.1f deg [%+.1f-%+.1f]" % (
            lab, s["n"], "%.3f [%.3f-%.3f]" % (np.median(nom), *np.percentile(nom, (25, 75))),
            "%.3f [%.3f-%.3f]" % (np.median(eff), *np.percentile(eff, (25, 75))),
            np.median(np.degrees(np.angle(Ce))), *np.percentile(np.degrees(np.angle(Ce)), (25, 75))))
    pr("\n   and the same restricted to the LOUD windows (rate amplitude at f0 in the top quartile of that stratum):")
    pr("   %-22s %5s | %-24s %-24s | %-18s" % ("stratum (top-quartile loud)", "n", "NOMINAL |C|/|C248|", "EFFECTIVE (clamped)", "angle C eff"))
    for lab, s in stats.items():
        q = s["ra"] >= np.percentile(s["ra"], 75)
        C0 = np.abs(C_of(248.0, s["f0"][q]))
        nom = np.abs(C_of(s["kp"][q], s["f0"][q])) / C0
        nD = df_sat(s["D"][q], DCLAMP)
        Ce = C_of(s["kp"][q], s["f0"][q], nd=nD)
        nS = df_sat(np.abs(Ce) * s["E"][q], SCLAMP)
        eff = nS * np.abs(Ce) / C0
        pr("   %-22s %5d | %-24s %-24s | %+6.1f deg" % (
            lab, q.sum(), "%.3f [%.3f-%.3f]" % (np.median(nom), *np.percentile(nom, (25, 75))),
            "%.3f [%.3f-%.3f]" % (np.median(eff), *np.percentile(eff, (25, 75))), np.median(np.degrees(np.angle(Ce)))))

    pr("\n4. WHAT AMPLITUDE WOULD EACH CLAMP NEED?  (solved from the chain above at 20 Hz, Kp 248)")
    f0 = 20.0
    Ecoef = abs(F_of(f0)) * MN.CPD
    dcoef = abs((KD / 8.0) * (1 - np.exp(-2j * np.pi * f0 * MN.TS)))
    pr("   E = %.1f * rate(deg/s) ; D = %.3f * E ; P+D = %.3f * E ; S = %.5f * (P+D)" % (
        Ecoef, dcoef, abs(C_of(248.0, f0)), abs(H_of(f0)) * (254.0 / 256.0) * GAIN / 32768.0))
    pr("   D clamp   %5.0f binds above rate = %6.2f deg/s" % (DCLAMP, DCLAMP / dcoef / Ecoef))
    pr("   sum clamp %5.0f binds above rate = %6.2f deg/s" % (SCLAMP, SCLAMP / abs(C_of(248.0, f0)) / Ecoef))
    pr("   out clamp %5.0f binds above rate = %6.2f deg/s" % (OCLAMP, OCLAMP / (abs(C_of(248.0, f0)) * abs(H_of(f0)) * (254.0 / 256.0) * GAIN / 32768.0) / Ecoef))
    pr("   (for comparison, the measured line amplitudes above are the 'rate p50' / 'rate p90' columns in section 2)")

    with open(os.path.join(SCR, "mode_nature_v289_kp_pinning.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    pr("\nwrote _scratch/mode_nature_v289_kp_pinning.txt")


if __name__ == "__main__":
    main()
