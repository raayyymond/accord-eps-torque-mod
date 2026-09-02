# -*- coding: utf-8 -*-
"""V280 LINEAR map candidates: Y(X) = s*X through the origin (no knee), through the exact LKAS rate-PID chain
(FUN_00028ea6) on the V276 (r2e) and V278 rev 3 (r31) logs.  Companion to v280_map_profiles.py, whose Route /
simulate / metrics / profile machinery is imported unchanged (same chain, same cache, same comparators).

Operator instruction (2026-09-02): "change the setpoint curve to be LINEAR instead of having a knee at 96 --
linearize this response as much as possible for openpilot to control torque."

For every candidate:  damp_E in V276's ringing frames (whole, and by idx band <=12 / 12-32 / 32-58), damp_T,
damp_E in normal driving on r2e and r31, D-rail / P-rail / sat duties on r31, ceiling crossover, the fb-clamp
margin, the stall margin at idx 240 (servo_at_reference.py's method), and the small-signal loop-gain proxy
slope(idx) * Kp(idx).

Run:  python analysis-2020accord/studies/v280/v280_linear_profiles.py [--clamp 46080|ratio]
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v280_map_profiles as M   # noqa: E402

MAP_X, MAP_Y, KP_X, KP_Y = M.MAP_X, M.MAP_Y, M.KP_X, M.KP_Y
lerp, map_knots, profile, ceiling_degs = M.lerp, M.map_knots, M.profile, M.ceiling_degs
FB_DC, CPD, P_CLAMP = M.FB_DC, M.CPD, M.P_CLAMP
FB_PER_DEGS = FB_DC * CPD                  # 247.1 fb counts per deg/s of wheel rate
STALL_DEGS = 15.0                          # the F7 stalls: rate p50 10-20 deg/s against the reference
KP_TOP = float(KP_Y[-1])                   # 696
P_WINDOW = np.floor(P_CLAMP * 256 / KP_TOP)   # 5650: |E| above which P rails at idx >= 136


# ----------------------------------------------------------------------------------------------------
# the candidate family
# ----------------------------------------------------------------------------------------------------
def linear_knots(s):
    """Y = s*X at the ten slot-7 X knots (rounded)."""
    return np.round(s * MAP_X)


def two_seg_knots(s1, x_mid, y_top=1032.0):
    """Linear s1 to idx x_mid, then linear to y_top at 240."""
    y_mid = s1 * x_mid
    return np.round(np.where(MAP_X <= x_mid, s1 * MAP_X, y_mid + (y_top - y_mid) * (MAP_X - x_mid) / (240 - x_mid)))


CANDIDATES = [
    # name, knots, family
    ("U1 stock", map_knots(profile(1, 240, 1)), "ref"),
    ("U2 rev3 x2", map_knots(profile(2, 240, 2)), "ref"),
    ("2@96->6 knee", map_knots(profile(2, 96, 6)), "ref"),
    ("U6 V276", map_knots(profile(6, 240, 6)), "ref"),
] + [("lin s=%.1f" % s, linear_knots(s), "lin") for s in (2.0, 2.5, 3.0, 3.5, 4.0, 4.3, 4.5, 4.7)]


def clamp_for(Y, mode):
    if mode == "ratio":
        return float(np.round(32 * Y[-1] * 1.395))
    return float(mode)


def stall_margin_degs(Y):
    """E at idx 240 with the wheel stalled at STALL_DEGS, minus P's rail window, in deg/s of rate ripple needed
    to pull P off its rail (servo_at_reference.py's method; rev 3 = 6.7, V276 ~ 96)."""
    E0 = 32 * Y[-1] - STALL_DEGS * FB_PER_DEGS
    return (E0 - P_WINDOW) / FB_PER_DEGS


def band_damp(r, R, lo, hi):
    """damp_E on the V276 ringing ticks whose demand idx is in (lo, hi]."""
    m = r.osc1k & (r.idx1k > lo) & (r.idx1k <= hi) & (R["fb"] != 0)
    return (np.mean(np.sign(R["E"][m]) != np.sign(R["fb"][m])), int(m.sum())) if m.any() else (np.nan, 0)


def evaluate(r2e, r31, Y, clamp):
    R2 = r2e.simulate(Y, fb_clamp=clamp)
    R3 = r31.simulate(Y, fb_clamp=clamp)
    o = r2e.metrics(R2, r2e.osc1k, r2e.osc)
    n = r2e.metrics(R2, r2e.nor1k, r2e.normal)
    m3 = r31.metrics(R3, r31.eng1k, r31.eng)
    bands = [band_damp(r2e, R2, lo, hi) for lo, hi in ((-1, 12), (12, 32), (32, 58))]
    return o, n, m3, bands


def local_slope(Y, x):
    g = np.gradient(lerp(MAP_X, Y, np.arange(241.0)))
    return g[int(x)]


# ----------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clamp", default="46080", help="fb clamp 0xC62E6 for every candidate: a number, or 'ratio' (= 1.395 x 32*Y240)")
    a = ap.parse_args()
    r2e, r31 = M.Route("r2e"), M.Route("r31")
    for r in (r2e, r31):
        print("  %s: %d episodes (%.1f s ringing), engaged %.1f s" % (r.tag, len(r.eps), r.osc.sum() / M.FS, r.eng.sum() / M.FS))
    print("  V276 ringing ticks by idx band (<=12 / 12-32 / 32-58 / >58): %s" % [
        int((r2e.osc1k & (r2e.idx1k > lo) & (r2e.idx1k <= hi)).sum()) for lo, hi in ((-1, 12), (12, 32), (32, 58), (58, 999))])

    print("\n" + "=" * 120)
    print("PART A -- LINEAR CANDIDATES through the chain, fb clamp = %s.  dE = damp_E (E-comparator), dT = damp_T (what the rev-3 tap reads)" % a.clamp)
    print("          osc = V276 ringing frames; b1/b2/b3 = osc frames with idx <=12 / 12-32 / 32-58; nrm = r2e normal; r31 = rev-3 route engaged")
    print("          stall = deg/s of rate ripple needed to desaturate P at idx 240 with the wheel stalled at 15 deg/s (rev 3: 6.7)")
    print("=" * 120)
    print("%-13s %5s %6s %6s %6s | %6s %6s %6s %6s | %6s %6s %6s %6s | %6s %6s %6s %6s | %6s" % (
        "candidate", "s", "Y240", "ceil", "stall", "dE_osc", "dE_b1", "dE_b2", "dE_b3", "dT_osc", "dE_nrm", "dE_r31", "dT_r31",
        "Drl31", "Prl31", "sat31", "Prl_o", "clmp/32Y"))
    rows = []
    for name, Y, fam in CANDIDATES:
        clamp = clamp_for(Y, a.clamp if fam == "lin" else "ratio")     # reference rows carry their own 7680 x K_top clamp
        o, n, m3, b = evaluate(r2e, r31, Y, clamp)
        s = Y[-1] / 240.0
        rows.append((name, Y, s, o, n, m3, b, clamp))
        print("%-13s %5.2f %6d %6.1f %6.1f | %6.3f %6.3f %6.3f %6.3f | %6.3f %6.3f %6.3f %6.3f | %6.4f %6.3f %6.3f %6.3f | %6.2f" % (
            name, s, Y[-1], ceiling_degs(Y), stall_margin_degs(Y), o["damp_E"], b[0][0], b[1][0], b[2][0], o["damp_T"],
            n["damp_E"], m3["damp_E"], m3["damp_T"], m3["d_rail"], m3["p_rail"], m3["sat"], o["p_rail"], clamp / (32 * Y[-1])))
    print("\n  knots (Y at X = %s):" % ", ".join("%d" % x for x in MAP_X))
    for name, Y, s, o, n, m3, b, clamp in rows:
        print("   %-13s %s   | vs rev3 at X=12/20/32/58: %s" % (name, " ".join("%4d" % y for y in Y),
              " ".join("%.2f" % (lerp(MAP_X, Y, x) / lerp(MAP_X, 2 * MAP_Y, x)) for x in (12, 20, 32, 58))))

    # ---- fine s sweep for the gate
    print("\n  s SWEEP (linear, clamp %s): damp_E osc / by band / ceiling / stall" % a.clamp)
    sweep = []
    for s in np.arange(2.0, 4.71, 0.1):
        Y = linear_knots(s)
        o, n, m3, b = evaluate(r2e, r31, Y, clamp_for(Y, a.clamp))
        sweep.append((s, o["damp_E"], b, ceiling_degs(Y), stall_margin_degs(Y), m3["p_rail"], m3["sat"]))
        print("   s %.1f  Y240 %4d  dE_osc %.3f  bands %.3f/%.3f/%.3f  dT_osc %.3f  dE_nrm %.3f  ceil %6.1f  stall %5.1f  Prl31 %.3f  sat31 %.3f" % (
            s, Y[-1], o["damp_E"], b[0][0], b[1][0], b[2][0], o["damp_T"], n["damp_E"], ceiling_degs(Y), stall_margin_degs(Y), m3["p_rail"], m3["sat"]))
    for gate in (0.86, 0.82):
        ok = [t for t in sweep if t[1] >= gate - 1e-9]
        if ok:
            s, dE, b, c, st, pr, sat = max(ok, key=lambda t: t[0])
            print("  GATE damp_E osc >= %.2f: largest linear s = %.1f (Y240 %d, ceiling %.1f deg/s, stall %.1f, damp_E %.3f)" % (gate, s, 240 * s, c, st, dE))
        else:
            print("  GATE damp_E osc >= %.2f: NO linear s in [2.0, 4.7] passes" % gate)

    # ---- clamp sensitivity: 46080 vs ratio-preserving vs 15360
    print("\n  CLAMP SENSITIVITY (damp_E osc / dE_r31 / fb-clamp-railed r31): 46080 | ratio 1.395 | 15360")
    for name, Y, fam in CANDIDATES:
        if fam != "lin":
            continue
        cells = []
        for cm in ("46080", "ratio", "15360"):
            clamp = clamp_for(Y, cm)
            R3 = r31.simulate(Y, fb_clamp=clamp); R2 = r2e.simulate(Y, fb_clamp=clamp)
            o = r2e.metrics(R2, r2e.osc1k, r2e.osc); m3 = r31.metrics(R3, r31.eng1k, r31.eng)
            cells.append("%5d: %.3f / %.3f / %.4f" % (clamp, o["damp_E"], m3["damp_E"], np.mean(np.abs(R3["fb"][r31.eng1k]) >= clamp)))
        print("   %-11s 32*Y240 %5d  need >= %5d | %s" % (name, 32 * Y[-1], 32 * Y[-1], " | ".join(cells)))

    # ---- two-segment alternative
    print("\n  TWO-SEGMENT 'as linear as possible': s1 to idx 64, then linear to 1032 at 240 (clamp %s)" % a.clamp)
    for s1 in (2.0, 2.5, 3.0, 3.5, 3.8, 4.0):
        Y = two_seg_knots(s1, 64)
        s2 = (1032 - s1 * 64) / (240 - 64)
        o, n, m3, b = evaluate(r2e, r31, Y, clamp_for(Y, a.clamp))
        print("   s1 %.1f -> Y64 %4d, s2 %.2f: dE_osc %.3f bands %.3f/%.3f/%.3f  dT_osc %.3f  dE_nrm %.3f  dE_r31 %.3f  Drl31 %.4f Prl31 %.3f sat31 %.3f  knots %s" % (
            s1, s1 * 64, s2, o["damp_E"], b[0][0], b[1][0], b[2][0], o["damp_T"], n["damp_E"], m3["damp_E"], m3["d_rail"], m3["p_rail"], m3["sat"],
            " ".join("%d" % y for y in Y)))

    # ---- Kp interaction: small-signal loop-gain proxy = local map slope x Kp(idx)
    print("\n" + "=" * 120)
    print("PART B -- small-signal loop-gain proxy  slope(idx) x Kp(idx)   [Kp 248 at 0, 512 at 68, 645 at 112, 696 from 136]")
    print("          slope = dY/didx of the map at that idx (stock is concave: slopes 2.0 2.25 2.0 1.5 1.19 0.81 0.88 0.38 0.075 per segment)")
    print("=" * 120)
    pts = (12, 32, 58, 96, 136, 240)
    print("%-13s | " % "map" + " ".join("%14s" % ("idx %d" % x) for x in pts) + "   (slope x Kp, and ratio to rev 3)")
    ref = {x: local_slope(map_knots(profile(2, 240, 2)), x) * lerp(KP_X, KP_Y, x) for x in pts}
    for name, Y, fam in CANDIDATES:
        if name.startswith("U6"):
            continue
        cells = []
        for x in pts:
            g = local_slope(Y, x) * lerp(KP_X, KP_Y, x)
            cells.append("%6.0f (%4.2fx)" % (g, g / ref[x]))
        print("%-13s | %s" % (name, " ".join(cells)))
    print("   Kp(idx): " + "  ".join("%d:%.0f" % (x, lerp(KP_X, KP_Y, x)) for x in pts))
    print("   NOTE: at idx <= 20 the stock map's slope (2.0-2.25) x2 = 4.0-4.5 >= a straight 4.3, so the linear map is NOT steeper than rev 3 there;")
    print("         it is steeper from idx ~24 up (rev 3 slope 3.0 at 24-32, 2.4 at 32-64, 1.6 at 64-96 ... 0.15 at 160-240).")


if __name__ == "__main__":
    main()
