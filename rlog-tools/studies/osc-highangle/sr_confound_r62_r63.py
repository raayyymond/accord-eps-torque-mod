# -*- coding: utf-8 -*-
"""sr_confound_r62_r63.py -- is the SR-free ratio defect driven by ANGLE or by SPEED?

sR_true measured small-angle and measured large-angle are confounded, because small angles happen
at high speed and large angles at low speed, and the bicycle model's slip factor sf*v^2 (which is
inside curvature_factor) is the one term that is speed-dependent and could be mis-parameterised.
Cross-tabulate to separate them, pooling r62+r63 for n.

Also: corner events with a looser gate than oversteer_r62_r63.py section C, and the lead/lag of
achieved vs asked through the entry.
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "analysis-2020accord", "studies", "optune"))
sys.path.insert(0, os.path.join(ROOT, "rlog-tools"))
import backcalc_laf_friction as B  # noqa: E402

G = 9.81
FS = B.FS
MAP_BP = [0.0, 48.0, 60.0, 76.0, 95.0, 121.0, 191.0, 236.0, 303.0, 380.0]
MAP_V = [16.00, 16.00, 16.00, 15.83, 15.23, 14.99, 14.72, 13.96, 12.72, 12.06]
L = []


def pr(s=""):
    print(s, flush=True)
    L.append(s)


def tls(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 100:
        return np.nan, len(x)
    _, _, V = np.linalg.svd(np.stack([x, y], 1), full_matrices=False)
    n = V[-1]
    return float(-n[0] / n[1]), len(x)


def prep(tag, level):
    D = B.load(tag)
    g = B.grid(D)
    cp = D["cp"]
    m_, l_, aF = cp["mass"], cp["wheelbase"], cp["centerToFront"]
    cF, cR = cp["tireStiffnessFront"], cp["tireStiffnessRear"]
    aR = l_ - aF
    sf = m_ * (cF * aF - cR * aR) / (l_ ** 2 * cF * cR)
    v = g["v"]
    g["cfac"] = 1.0 / (1.0 - sf * v ** 2) / l_
    g["cfac_kin"] = np.full_like(v, 1.0 / l_)          # kinematic: no slip term at all
    g["rollc"] = (G * g["proll"]) / ((1.0 / sf) - v ** 2)
    g["sa_deg"] = g["ang"] - g["aoff"]
    g["sa"] = np.radians(g["sa_deg"])
    g["denom"] = (-g["yaw_cal"] / np.maximum(v, 1e-3)) - g["rollc"]
    j = np.clip(np.searchsorted(g["lp_t"], g["t"]) - 1, 0, len(g["lp_t"]) - 1)
    g["eng"] = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & g["lp_calok"][j]
    g["srv"] = np.interp(np.abs(g["sa_deg"]), MAP_BP, MAP_V) * (level / 16.00)
    g["tag"] = tag
    return g


def cat(gs, key):
    return np.concatenate([g[key] for g in gs])


def main():
    gs = [prep("r62", 16.33), prep("r63", 16.33)]
    keys = ["cfac", "cfac_kin", "denom", "sa", "sa_deg", "v", "rate", "eng", "srv", "descurv", "yaw_cal", "t"]
    P = {k: cat(gs, k) for k in keys}
    base = P["eng"] & (np.abs(P["rate"]) < 20.0) & np.isfinite(P["denom"]) & (np.abs(P["sa_deg"]) > 2.0)

    pr("=" * 118)
    pr("A  sR_true CROSS-TAB: |wheel angle| (rows) x speed (cols).  pooled r62+r63.  cell = sR_true / n seconds")
    pr("   If the defect is ANGLE-driven the rows move and the columns do not; if it is a bicycle-model")
    pr("   speed artefact the columns move and the rows do not.")
    pr("=" * 118)
    ABINS = [(2, 6), (6, 12), (12, 25), (25, 60), (60, 400)]
    VBINS = [(4, 9), (9, 14), (14, 20), (20, 40)]
    pr("   %-10s %s" % ("|sa| deg", "".join("%18s" % ("v %d-%d" % vb) for vb in VBINS)))
    for lo, hi in ABINS:
        cells = []
        for vlo, vhi in VBINS:
            ok = base & (np.abs(P["sa_deg"]) >= lo) & (np.abs(P["sa_deg"]) < hi) & (P["v"] >= vlo) & (P["v"] < vhi)
            s, n = tls(P["denom"][ok], P["cfac"][ok] * P["sa"][ok])
            cells.append("%18s" % ("%.2f / %.0fs" % (s, n / FS) if np.isfinite(s) else "--"))
        pr("   %-10s %s" % ("%d-%d" % (lo, hi), "".join(cells)))

    pr("")
    pr("   Same cross-tab with the KINEMATIC curvature factor (1/wheelbase, slip term removed entirely):")
    pr("   %-10s %s" % ("|sa| deg", "".join("%18s" % ("v %d-%d" % vb) for vb in VBINS)))
    for lo, hi in ABINS:
        cells = []
        for vlo, vhi in VBINS:
            ok = base & (np.abs(P["sa_deg"]) >= lo) & (np.abs(P["sa_deg"]) < hi) & (P["v"] >= vlo) & (P["v"] < vhi)
            s, n = tls(P["denom"][ok], P["cfac_kin"][ok] * P["sa"][ok])
            cells.append("%18s" % ("%.2f / %.0fs" % (s, n / FS) if np.isfinite(s) else "--"))
        pr("   %-10s %s" % ("%d-%d" % (lo, hi), "".join(cells)))

    pr("")
    pr("=" * 118)
    pr("B  CORNER EVENTS, loose gate: engaged run of >= 4 s with peak |asked| > 2.0 m/s2 (any speed).")
    pr("   overshoot = peak achieved / peak asked;  lead = seconds achieved LEADS asked (xcorr, +ve = car early)")
    pr("=" * 118)
    for g in gs:
        v = g["v"]
        asked = g["descurv"] * v ** 2
        ach = v * g["yaw_cal"]
        eng = g["eng"] & np.isfinite(ach)
        # engaged runs
        d = np.diff(eng.astype(int))
        starts = np.flatnonzero(d == 1) + 1
        ends = np.flatnonzero(d == -1) + 1
        if eng[0]:
            starts = np.r_[0, starts]
        if eng[-1]:
            ends = np.r_[ends, len(eng)]
        evs = []
        for s0, e0 in zip(starts, ends):
            if e0 - s0 < int(4 * FS):
                continue
            a = asked[s0:e0]
            c = ach[s0:e0]
            # segment into sign-consistent excursions above 2.0
            hot = np.abs(a) > 2.0
            dd = np.diff(hot.astype(int))
            hs = np.flatnonzero(dd == 1) + 1
            he = np.flatnonzero(dd == -1) + 1
            if hot[0]:
                hs = np.r_[0, hs]
            if hot[-1]:
                he = np.r_[he, len(hot)]
            for h0, h1 in zip(hs, he):
                w0 = max(h0 - int(1.5 * FS), 0)
                w1 = min(h1 + int(1.5 * FS), len(a))
                if w1 - w0 < int(2.5 * FS):
                    continue
                aw, cw = a[w0:w1], c[w0:w1]
                sg = np.sign(np.median(aw[h0 - w0:h1 - w0]))
                pk_a = float(sg * np.max(sg * aw))
                pk_c = float(sg * np.max(sg * cw))
                if abs(pk_a) < 2.0:
                    continue
                aa, cc = aw - aw.mean(), cw - cw.mean()
                lags = np.arange(-int(1.0 * FS), int(1.0 * FS) + 1)
                xc = [float(np.dot(aa[:len(aa) - lg], cc[lg:])) if lg >= 0 else float(np.dot(aa[-lg:], cc[:len(cc) + lg])) for lg in lags]
                lead = -lags[int(np.argmax(xc))] / FS
                evs.append((float(g["t"][s0 + h0]), float(np.median(v[s0 + h0:s0 + h1])), pk_a, pk_c, pk_c / pk_a, float(lead),
                            float(np.max(np.abs(g["sa_deg"][s0 + w0:s0 + w1])))))
        pr("   %s: %d corner excursions" % (g["tag"], len(evs)))
        if not evs:
            continue
        E = np.array([[e[1], e[2], e[4], e[5], e[6]] for e in evs], float)
        for lbl, mm in (("all", np.ones(len(E), bool)),
                        ("v < 11 m/s (roundabout)", E[:, 0] < 11),
                        ("v 11-18", (E[:, 0] >= 11) & (E[:, 0] < 18)),
                        ("v >= 18", E[:, 0] >= 18),
                        ("peak |sa| > 45 deg", E[:, 4] > 45)):
            if mm.sum() < 3:
                continue
            pr("     %-24s n=%3d  overshoot med %.3f  [p25 %.3f p75 %.3f]   lead med %+.2f s   med |ask| %.2f" % (
                lbl, int(mm.sum()), float(np.median(E[mm, 2])), float(np.percentile(E[mm, 2], 25)),
                float(np.percentile(E[mm, 2], 75)), float(np.median(E[mm, 3])), float(np.median(np.abs(E[mm, 1])))))
        pr("")

    with open(os.path.join(HERE, "_scratch", "sr_confound_r62_r63.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
