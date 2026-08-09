#!/usr/bin/env python3
"""CHARACTERISING THE ~21 Hz MODE.  Did `0xC40D4` change its DAMPING, or only its FREQUENCY?

🛑 S1 RUNS FIRST AND CAN INVALIDATE EVERYTHING ELSE.  `accord-vibration-moves-with-speed-and-
   dies-at-rail` records the engaged-only vibration MOVING WITH SPEED: 20.12 Hz @ 1.0 m/s ->
   21.68 Hz @ 4.0 m/s, a slope of ~+0.52 Hz/(m/s).  If the mode really is speed-dependent, then
   a difference in the WITHIN-BIN speed distribution between 6f and 6e could manufacture part of
   the +10.6% shift.  Measure the slope and the within-bin speed census BEFORE anything else.

S2  Q / damping ratio, two independent methods (Lorentzian fit + half-power bandwidth).
S3  ENERGY.  Is it conserved across the move?  Integrated over 18-27 Hz, wide enough to hold the
    mode in BOTH positions.  🛑 This is an AMPLITUDE question, and amplitude ratios have failed
    four builds against a [0.63, 1.50] null -- so the same-alpha pair (V86B vs V85) is computed
    as the floor FIRST, and no energy claim is read below it.
S4  Gain-set vs phase-set, from the joint (df, dQ, dE) pattern.
S5  The dose law and its honesty.
S6  Is this the recorded 21.09 Hz object?
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v86_freq_test as V           # noqa: E402

ROOT = V.ROOT
RNG = np.random.default_rng(86_2100)
VBINS = V.VBINS
HFLO, HFHI = 18.0, 27.0
O = {}
ALPHA = {"V85/r6e": 573 / 4096, "V86B/r70": 573 / 4096, "V86/r6f": 286 / 4096}


def lorentz(f, A, f0, Q, B):
    return A / (1.0 + 4.0 * Q * Q * ((f - f0) / f0) ** 2) + B


def fit_mode(fr, P, lo=HFLO, hi=HFHI):
    """Lorentzian + flat floor over [lo, hi].  Returns (f0, Q, A_peak, area, ok)."""
    m = (fr >= lo) & (fr <= hi) & np.isfinite(P)
    x, y = fr[m], P[m]
    if len(x) < 12 or not np.all(np.isfinite(y)) or np.ptp(y) <= 0:
        return (np.nan,) * 4 + (False,)
    j = int(np.argmax(y))
    p0 = [max(y[j] - np.median(y), 1e-9), x[j], 12.0, float(np.median(y))]
    try:
        pop, _ = curve_fit(lorentz, x, y, p0=p0, maxfev=20000,
                           bounds=([0, lo, 1.0, 0], [np.inf, hi, 200.0, np.inf]))
    except Exception:
        return (np.nan,) * 4 + (False,)
    A, f0, Q, B = pop
    if not (lo + 0.2 < f0 < hi - 0.2) or A <= 0:
        return (np.nan,) * 4 + (False,)
    area = np.pi * A * f0 / (2.0 * Q)          # analytic Lorentzian area
    return float(f0), float(Q), float(A), float(area), True


def halfpower(fr, R, lo=HFLO, hi=HFHI):
    """Q from the -3 dB width of the PROMINENCE peak (excess over the local floor)."""
    m = (fr >= lo) & (fr <= hi) & np.isfinite(R)
    x, y = fr[m], R[m] - 1.0
    if len(x) < 12 or np.nanmax(y) <= 0:
        return np.nan, np.nan
    j = int(np.nanargmax(y))
    half = y[j] / 2.0
    i = j
    while i > 0 and y[i] > half:
        i -= 1
    k = j
    while k < len(y) - 1 and y[k] > half:
        k += 1
    if i == j or k == j:
        return np.nan, np.nan
    bw = x[k] - x[i]
    return (float(x[j] / bw) if bw > 0 else np.nan), float(bw)


def band_energy(r, lo=HFLO, hi=HFHI):
    """Total power, floor power and EXCESS power over the local floor, in [lo, hi]."""
    f, P, R = r["f"], r["P"], r["R"]
    m = (f >= lo) & (f <= hi) & np.isfinite(R) & (R > 0)
    tot = float(np.sum(P[m]))
    floor = float(np.sum(P[m] / R[m]))
    return tot, floor, max(tot - floor, 0.0)


def main():
    E, M = {}, {}
    for name, (c, p, s) in V.ROUTES.items():
        E[name] = V.in_speed(V.spectra(V.windows(name, c, p, s, engaged=True)))
        M[name] = V.in_speed(V.spectra(V.windows(name, c, p, s, engaged=False)))
    ARMS = ("V86/r6f", "V85/r6e", "V86B/r70")
    for nm in E:
        for r in E[nm] + M[nm]:
            f0, Q, A, ar, ok = fit_mode(r["f"], r["P"])
            r["l_f0"], r["l_Q"], r["l_A"], r["l_area"], r["l_ok"] = f0, Q, A, ar, ok
            r["hp_Q"], r["hp_bw"] = halfpower(r["f"], r["R"])
            r["e_tot"], r["e_floor"], r["e_exc"] = band_energy(r)
            m = (r["f"] >= HFLO) & (r["f"] <= HFHI) & np.isfinite(r["R"])
            r["f_hf"] = float(r["f"][np.argmax(np.where(m, r["R"], -np.inf))])
            r["p_hf"] = float(np.nanmax(np.where(m, r["R"], np.nan)))

    # =========================================================================================
    V.hdr("S1  🛑 THE SPEED CONFOUND -- RUN FIRST.  The record has the engaged-only vibration\n"
          "    MOVING WITH SPEED (20.12 Hz @ 1.0 m/s -> 21.68 @ 4.0, ~+0.52 Hz per m/s).  If so,\n"
          "    a within-bin speed difference between 6f and 6e could manufacture the +10.6%.")
    O["s1"] = {}
    print("    %-10s %6s | %30s | %s" % ("build", "n", "d(f_hf)/dv Hz per m/s, block CI",
                                         "per-bin median f_hf"))
    for nm in ARMS:
        rs = E[nm]
        v = np.array([r["v"] for r in rs]); ff = np.array([r["f_hf"] for r in rs])
        ok = np.isfinite(ff)
        sl = float(np.polyfit(v[ok], ff[ok], 1)[0])
        g = {}
        for r in rs:
            g.setdefault(r["blk"], []).append(r)
        ks = list(g); d = []
        for _ in range(3000):
            rr = [x for i in RNG.integers(0, len(ks), len(ks)) for x in g[ks[i]]]
            vv = np.array([x["v"] for x in rr]); f2 = np.array([x["f_hf"] for x in rr])
            o = np.isfinite(f2)
            if len(set(np.round(vv[o], 3))) < 3:
                continue
            d.append(np.polyfit(vv[o], f2[o], 1)[0])
        lo, hi = np.percentile(d, [2.5, 97.5]) if len(d) > 50 else (np.nan, np.nan)
        per = "  ".join("%.2f-%.2f:%.2f(n=%d)"
                        % (a, b, np.median([r["f_hf"] for r in rs if a <= r["v"] < b]),
                           sum(1 for r in rs if a <= r["v"] < b))
                        for a, b in VBINS if sum(1 for r in rs if a <= r["v"] < b) >= 2)
        print("    %-10s %6d | %+8.4f [%+8.4f,%+8.4f]      | %s" % (nm, len(rs), sl, lo, hi, per))
        O["s1"][nm] = dict(slope=[sl, float(lo), float(hi)], n=len(rs))

    print("\n    WITHIN-BIN MEAN SPEED -- is the matching actually matched?")
    print("    %-10s %s" % ("build", "  ".join("%.2f-%.2f" % b for b in VBINS)))
    for nm in ARMS:
        rs = E[nm]
        cells = []
        for a, b in VBINS:
            m = [r["v"] for r in rs if a <= r["v"] < b]
            cells.append("%s" % ("%.3f (n=%d)" % (np.mean(m), len(m)) if m else "   --    "))
        print("    %-10s %s" % (nm, "  ".join(cells)))
        O["s1"].setdefault("within_bin_v", {})[nm] = cells
    d6f = [np.mean([r["v"] for r in E["V86/r6f"] if a <= r["v"] < b] or [np.nan])
           for a, b in VBINS]
    d6e = [np.mean([r["v"] for r in E["V85/r6e"] if a <= r["v"] < b] or [np.nan])
           for a, b in VBINS]
    dv = np.nanmean(np.array(d6f) - np.array(d6e))
    sl6e = O["s1"]["V85/r6e"]["slope"][0]
    print("\n    mean within-bin speed difference 6f - 6e = %+.3f m/s" % dv)
    print("    worst-case slope from the CIs = %+.3f Hz per m/s" %
          max(abs(O["s1"][nm]["slope"][2]) for nm in ARMS))
    worst = max(abs(O["s1"][nm]["slope"][2]) for nm in ARMS)
    print("    => speed can account for at most %+.3f Hz of the observed %+.3f Hz shift (%.1f%%)"
          % (worst * dv, 23.663 - 20.972, 100 * abs(worst * dv) / (23.663 - 20.972)))
    O["s1"]["confound"] = dict(dv=float(dv), worst_slope=float(worst),
                               max_attributable_Hz=float(worst * dv),
                               observed_Hz=23.663 - 20.972)

    # =========================================================================================
    V.hdr("S2  Q / DAMPING, two independent methods.  Lorentzian fit to the POWER spectrum\n"
          "    (A, f0, Q, flat floor) and the -3 dB width of the PROMINENCE peak.")
    O["s2"] = {}
    print("    %-10s %8s | %22s | %22s | %22s"
          % ("build", "n fit/n", "f0 (Lorentzian)", "Q (Lorentzian)", "Q (half-power)"))
    for nm in ARMS:
        rs = [r for r in E[nm] if r["l_ok"]]
        u = [r["blk"] for r in rs]
        f0 = V.block_boot([r["l_f0"] for r in rs], u)
        Ql = V.block_boot([r["l_Q"] for r in rs], u)
        Qh = V.block_boot([r["hp_Q"] for r in E[nm]], [r["blk"] for r in E[nm]])
        print("    %-10s %4d/%-3d | %7.3f [%6.3f,%6.3f] | %7.2f [%6.2f,%6.2f] | "
              "%7.2f [%6.2f,%6.2f]"
              % (nm, len(rs), len(E[nm]), f0[0], f0[1], f0[2], Ql[0], Ql[1], Ql[2],
                 Qh[0], Qh[1], Qh[2]))
        O["s2"][nm] = dict(f0=list(f0), Q_lorentz=list(Ql), Q_halfpower=list(Qh),
                           n_fit=len(rs), n=len(E[nm]), n_blk=len(set(u)))
    print("\n    RATIOS (alpha-DIFFERING pair first, then the same-alpha NULL):")
    for A, B, tag in (("V86/r6f", "V85/r6e", "alpha DIFFERS"),
                      ("V86/r6f", "V86B/r70", "alpha DIFFERS"),
                      ("V86B/r70", "V85/r6e", "alpha SAME <- NULL")):
        for key, lab in (("l_f0", "f0"), ("l_Q", "Q_lor"), ("hp_Q", "Q_hp")):
            src = ({k: [r for r in E[k] if r["l_ok"]] for k in (A, B)} if key != "hp_Q"
                   else {k: E[k] for k in (A, B)})
            r = V.strat_block_boot_ratio(src[A], src[B], key=key)
            ex = "YES" if (r["hi"] < 1.0 or r["lo"] > 1.0) else "no"
            print("      %-9s/%-9s %-18s %-6s %6.3f [%6.3f,%6.3f]  excl 1.00: %s"
                  % (A.split("/")[0], B.split("/")[0], tag, lab, r["ratio"], r["lo"],
                     r["hi"], ex))
            O.setdefault("s2_ratio", {})["%s|%s|%s" % (A, B, key)] = r

    # =========================================================================================
    V.hdr("S3  🛑 ENERGY -- IS IT CONSERVED ACROSS THE MOVE?  Integrated 18-27 Hz, wide enough\n"
          "    to hold the mode in BOTH positions.  This is an AMPLITUDE question, and amplitude\n"
          "    ratios have failed four builds against a [0.63, 1.50] null.  So the SAME-ALPHA\n"
          "    pair is computed as the floor and no energy claim is read below it.")
    O["s3"] = {}
    print("    %-10s %4s | %24s | %24s | %22s"
          % ("build", "n", "EXCESS power 18-27", "TOTAL power 18-27", "excess/floor"))
    for nm in ARMS:
        rs = E[nm]
        u = [r["blk"] for r in rs]
        for r in rs:
            r["e_ratio"] = r["e_exc"] / r["e_floor"] if r["e_floor"] > 0 else np.nan
        ex = V.block_boot([r["e_exc"] for r in rs], u)
        to = V.block_boot([r["e_tot"] for r in rs], u)
        rt = V.block_boot([r["e_ratio"] for r in rs], u)
        print("    %-10s %4d | %8.3e [%7.2e,%7.2e] | %8.3e [%7.2e,%7.2e] | %6.2f [%5.2f,%5.2f]"
              % (nm, len(rs), ex[0], ex[1], ex[2], to[0], to[1], to[2], rt[0], rt[1], rt[2]))
        O["s3"][nm] = dict(excess=list(ex), total=list(to), ratio=list(rt))
    print("\n    🛑 THE NULL FIRST -- same-alpha pair (V86B vs V85), then the alpha-differing one:")
    for A, B, tag in (("V86B/r70", "V85/r6e", "alpha SAME <- THE FLOOR"),
                      ("V86/r6f", "V85/r6e", "alpha DIFFERS"),
                      ("V86/r6f", "V86B/r70", "alpha DIFFERS")):
        for key, lab in (("e_exc", "excess"), ("e_tot", "total"), ("e_ratio", "exc/floor")):
            r = V.strat_block_boot_ratio(E[A], E[B], key=key)
            e2 = "YES" if (r["hi"] < 1.0 or r["lo"] > 1.0) else "no"
            print("      %-9s/%-9s %-24s %-9s %6.3f [%6.3f,%6.3f]  excl 1.00: %s"
                  % (A.split("/")[0], B.split("/")[0], tag, lab, r["ratio"], r["lo"],
                     r["hi"], e2))
            O.setdefault("s3_ratio", {})["%s|%s|%s" % (A, B, key)] = r

    # =========================================================================================
    V.hdr("S6  IS THIS THE RECORDED 21.09 Hz OBJECT?  Engaged-conditionality and the V81/V84 arms.")
    O["s6"] = {}
    print("    %-10s | %22s | %22s | %10s"
          % ("build", "excess power ENGAGED", "excess power MANUAL", "ENG/MAN"))
    for nm in ARMS:
        e = V.block_boot([r["e_exc"] for r in E[nm]], [r["blk"] for r in E[nm]])
        if len(M[nm]) >= 4:
            m = V.block_boot([r["e_exc"] for r in M[nm]], [r["blk"] for r in M[nm]])
            print("    %-10s | %8.3e [%7.2e,%7.2e] | %8.3e [%7.2e,%7.2e] | %10.2f"
                  % (nm, e[0], e[1], e[2], m[0], m[1], m[2], e[0] / m[0]))
            O["s6"][nm] = dict(eng=list(e), man=list(m), ratio=e[0] / m[0])
        else:
            print("    %-10s | %8.3e [%7.2e,%7.2e] | manual n=%d too few |"
                  % (nm, e[0], e[1], e[2], len(M[nm])))
            O["s6"][nm] = dict(eng=list(e), man=None)
    print("\n    The older arms at parking-lot speed (both thin -- reported, not scored):")
    for nm in ("V84/r6d", "V81/r67"):
        rs = E[nm]
        if len(rs) < 4:
            print("    %-10s n=%d -- too few to score --" % (nm, len(rs)))
            O["s6"][nm] = dict(n=len(rs), scoreable=False)
            continue
        f = V.block_boot([r["f_hf"] for r in rs], [r["blk"] for r in rs])
        p = V.block_boot([r["p_hf"] for r in rs], [r["blk"] for r in rs])
        print("    %-10s n=%3d/%2dblk  f_hf %7.3f [%6.3f,%6.3f]  prom %6.2f [%5.2f,%5.2f]"
              % (nm, f[3], f[4], f[0], f[1], f[2], p[0], p[1], p[2]))
        O["s6"][nm] = dict(f_hf=list(f), prom=list(p), n=len(rs), scoreable=True)

    # =========================================================================================
    V.hdr("S5  THE DOSE LAW AND ITS HONESTY.  TWO dose levels only (573, 286).")
    fA, fB = O["s2"]["V86/r6f"]["f0"][0], O["s2"]["V85/r6e"]["f0"][0]
    sens = np.log(fA / fB) / np.log(ALPHA["V86/r6f"] / ALPHA["V85/r6e"])
    print("    Lorentzian f0: V86 %.3f Hz, V85 %.3f Hz  =>  d(ln f)/d(ln alpha) = %.4f"
          % (fA, fB, sens))
    print("    alpha is a Q12 FRACTION: cell/4096, so the cell CAPS AT 4096 (alpha = 1.0).")
    print("    %8s %9s %10s %12s %s" % ("cell", "alpha", "alpha mult", "pred f (Hz)", "note"))
    O["s5"] = dict(sens=float(sens), cap=4096)
    for cell in (286, 573, 652, 1146, 1891, 4096):
        al = cell / 4096
        pf = fA * (al / ALPHA["V86/r6f"]) ** sens
        note = ("CURRENT (V86)" if cell == 286 else "STOCK" if cell == 573 else
                "extrapolation x%.1f in alpha" % (al / ALPHA["V86/r6f"]))
        print("    %8d %9.4f %10.2f %12.2f %s" % (cell, al, al / ALPHA["V86/r6f"], pf, note))
        O["s5"].setdefault("predictions", {})[str(cell)] = dict(alpha=al, pred_f=float(pf))
    print("\n    HF estimator gain, |H(f)| = alpha/|1-(1-alpha)e^-j2pi f T| at 1 kHz -- the COST:")
    print("    %8s %10s %10s %10s" % ("cell", "|H| 8 Hz", "|H| 21 Hz", "|H| 28 Hz"))
    for cell in (286, 573, 1146, 1891):
        al = cell / 4096
        row = [float(np.abs(al / (1 - (1 - al) * np.exp(-2j * np.pi * f * 1e-3))))
               for f in (8.0, 21.0, 28.0)]
        print("    %8d %10.4f %10.4f %10.4f" % (cell, row[0], row[1], row[2]))
        O["s5"].setdefault("hf_gain", {})[str(cell)] = row

    (ROOT / "_cache_r6f" / "v86_hf_mode.json").write_text(json.dumps(O, indent=1, default=float))
    print("\nwrote %s" % (ROOT / "_cache_r6f" / "v86_hf_mode.json"))


if __name__ == "__main__":
    main()
