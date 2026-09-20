# -*- coding: utf-8 -*-
"""ATTACK 1 -- is REGIME B (0.60-1.20 Hz, large demand, 8-22 m/s) real, or an estimator artefact?

Published claim under attack: |H| 1.20 -> 2.15 at 8-15 m/s (surface stream's own table reads
V282 1.097 -> TORQ 2.503 at 10.24 s), the top of the exposure-weighted ranking, with ~45% of the
excess error power incoherent.

Every reading below is re-derived from the route caches by this stream's own code (adv_lib), whose
positive controls include a synthetic cell with a KNOWN gain 1.10 buried in incoherent output motion
at coherence 0.20 -- the estimator returns 1.10, so incoherence alone cannot manufacture 2.5 -- and a
leakage control with |H| = 4.0 in the adjacent band, which moves the in-band reading by +1 to +3%.
"""
import sys
import numpy as np
import adv_lib as L

BANDS = dict(B=(0.60, 1.20), B_lo=(0.60, 0.80), B_mid=(0.80, 1.00), B_hi=(1.00, 1.20),
             A1530=(0.15, 0.30), A3060=(0.30, 0.60), HI=(1.20, 2.40))
CHI = {c: i for i, c in enumerate(["X", "Y", "Z", "W", "A", "C", "K"])}


def get(r, n):
    return np.load(L.OUT / f"spec_{r}_n{n}.npz")


def sel(D, sb, ab):
    v, ap = D["m_v"], D["m_ap95"]
    lo, hi = L.SPD[sb]
    a0, a1 = L.ACUT[ab]
    return (v >= lo) & (v < hi) & (ap >= a0) & (ap < a1)


def pool(routes, n, sb, ab, key="F_lin_hann", ix="X", iy="Y", band="B", extra=None):
    Fs, meta = [], {k: [] for k in ("v", "ap95", "sa50", "sa95", "vsd", "xrms", "yrms", "curv50")}
    fr = None
    for r in routes:
        D = get(r, n)
        m = sel(D, sb, ab)
        if extra is not None:
            m &= extra(D, r)
        if m.sum() == 0:
            continue
        Fs.append(D[key][m])
        for k in meta:
            meta[k].append(D["m_" + k][m])
        fr = D["m_fr"]
    if not Fs:
        return None, None
    F = np.concatenate(Fs, 0)
    meta = {k: np.concatenate(v) for k, v in meta.items()}
    f1, f2 = BANDS[band]
    c = L.cell(F, CHI[ix], CHI[iy], f1, f2, fr)
    if c:
        c.update({k + "_med": float(np.median(v)) for k, v in meta.items()})
    return c, meta


def line(tag, c):
    if c is None:
        return f"  {tag:34s}  --"
    return (f"  {tag:34s} n{c['nwin']:4d} H1 {c['H1']:6.3f} Hcoh {c['Hcoh']:6.3f} Htot {c['Htot']:6.3f} "
            f"H2 {c['H2']:7.3f} g2 {c['g2']:5.2f}/{c['g2null']:4.2f} bias {c['bias']:5.3f} "
            f"lag {c['lag_gd_ms']:7.0f} prat {c['prat']:5.2f}")


def main():
    print("=" * 150)
    print("1. THE REGIME-B CELL, every estimator x taper x detrend x window length.  X = curv*v^2 -> Y = wz*v")
    print("   H1 = Sxy/Sxx (what the surface stream uses, per bin).  Hcoh = |H1|*gamma.  Htot = sqrt(Syy/Sxx).")
    print("=" * 150)
    for sb, sn in ((1, "8-15"), (2, "15-22")):
        for ab in (2,):
            print(f"\n  speed {sn}  amp A3 (p95|model| >= 1.0 m/s2)   band 0.60-1.20 Hz")
            for n in (512, 1024, 2048):
                for key in ("F_lin_hann", "F_lin_bh", "F_lin_mt3", "F_mean_hann"):
                    cv, _ = pool(L.V282, n, sb, ab, key)
                    ct, _ = pool(L.TORQ, n, sb, ab, key)
                    if cv is None or ct is None:
                        continue
                    print(f"    n{n:5d} {key:12s} V282 " + line("", cv)[38:])
                    print(f"    {'':5s} {'':12s} TORQ " + line("", ct)[38:])
                    print(f"    {'':5s} {'':12s} ratio H1 {ct['H1']/cv['H1']:5.2f}  "
                          f"Hcoh {ct['Hcoh']/cv['Hcoh']:5.2f}  Htot {ct['Htot']/cv['Htot']:5.2f}")

    print("\n" + "=" * 150)
    print("2. SUB-BAND SPLIT.  Leakage from the 1.2-2.4 Hz band (where the two builds are the SAME) would")
    print("   pile the excess at the TOP edge.  A real in-band object would not.")
    print("=" * 150)
    for sb, sn in ((1, "8-15"), (2, "15-22")):
        print(f"\n  speed {sn} A3")
        for bd in ("B_lo", "B_mid", "B_hi", "HI"):
            cv, _ = pool(L.V282, 1024, sb, 2, band=bd)
            ct, _ = pool(L.TORQ, 1024, sb, 2, band=bd)
            if cv and ct:
                print(f"    {bd:6s} {BANDS[bd]}  V282 H1 {cv['H1']:6.3f} g2 {cv['g2']:.2f} | "
                      f"TORQ H1 {ct['H1']:6.3f} g2 {ct['g2']:.2f} | ratio {ct['H1']/cv['H1']:5.2f}")

    print("\n" + "=" * 150)
    print("3. CHANNEL SWAP: curvature -> curvature (C -> K) instead of curv*v^2 -> wz*v.")
    print("   X = curv*v^2 and Y = wz*v scale with DIFFERENT powers of v, so any window in which the speed")
    print("   changes puts a spurious gain into |H|.  8-15 m/s corner entries are where speed changes most.")
    print("=" * 150)
    for sb, sn in ((1, "8-15"), (2, "15-22"), (3, "22+")):
        for ab, an in ((2, "A3"), (1, "A2")):
            cv, mv = pool(L.V282, 1024, sb, ab, ix="X", iy="Y")
            ct, mt = pool(L.TORQ, 1024, sb, ab, ix="X", iy="Y")
            cv2, _ = pool(L.V282, 1024, sb, ab, ix="C", iy="K")
            ct2, _ = pool(L.TORQ, 1024, sb, ab, ix="C", iy="K")
            if not (cv and ct and cv2 and ct2):
                continue
            print(f"  {sn:6s} {an}  accel-frame  V282 {cv['H1']:6.3f} TORQ {ct['H1']:6.3f} ratio {ct['H1']/cv['H1']:5.2f}"
                  f"   |  curvature-frame V282 {cv2['H1']:6.3f} TORQ {ct2['H1']:6.3f} ratio {ct2['H1']/cv2['H1']:5.2f}"
                  f"   |  v-sd in window V282 {cv['vsd_med']:.2f} TORQ {ct['vsd_med']:.2f} m/s")

    print("\n" + "=" * 150)
    print("4. THE STRATUM IS NOT MATCHED.  Per-window census of the A3 cell at 8-15 and 15-22 m/s.")
    print("=" * 150)
    for sb, sn in ((1, "8-15"), (2, "15-22")):
        print(f"\n  speed {sn} A3, n=1024 windows")
        print(f"    {'route':24s} {'grp':6s} {'n':>3s} {'v50':>6s} {'|sa|50':>7s} {'|sa|95':>7s} "
              f"{'ap95':>6s} {'ax50':>6s} {'vsd':>5s} {'H1':>6s} {'g2':>5s}")
        for r in L.V282 + L.TORQ:
            D = get(r, 1024)
            m = sel(D, sb, 2)
            if m.sum() == 0:
                continue
            c = L.cell(D["F_lin_hann"][m], CHI["X"], CHI["Y"], 0.6, 1.2, D["m_fr"])
            print(f"    {r:24s} {L.ROUTES[r]['g']:6s} {m.sum():3d} {np.median(D['m_v'][m]):6.1f} "
                  f"{np.median(D['m_sa50'][m]):7.1f} {np.median(D['m_sa95'][m]):7.1f} "
                  f"{np.median(D['m_ap95'][m]):6.2f} {np.median(D['m_ax50'][m]):6.2f} "
                  f"{np.median(D['m_vsd'][m]):5.2f} {c['H1']:6.3f} {c['g2']:5.2f}")

    print("\n" + "=" * 150)
    print("5. TIME-DOMAIN CHECK, no cross-spectrum at all: band-passed regression on every run >= 60 s")
    print("   whose median speed is in the bin, weighted by run length.  Reported with its own R^2.")
    print("=" * 150)
    for sb, sn in ((1, "8-15"), (2, "15-22")):
        for grp, rts in (("V282", L.V282), ("TORQ", L.TORQ)):
            gs, ws, r2s = [], [], []
            for r in rts:
                S = L.load(r)
                m = S["on"] & ~S["pressed"]
                lo, hi = L.SPD[sb]
                t = S["t"]
                i, N = 0, len(m)
                while i < N:
                    if not m[i]:
                        i += 1
                        continue
                    j = i
                    while j + 1 < N and m[j + 1] and (t[j + 1] - t[j]) < 0.04:
                        j += 1
                    nn = j + 1 - i
                    if nn >= 60 * 100:
                        vv = np.median(S["v"][i:j + 1])
                        ap = np.percentile(np.abs(S["X"][i:j + 1]), 95)
                        if lo <= vv < hi and ap >= 1.0:
                            rr = L.reg_gain(S["X"][i:j + 1], S["Y"][i:j + 1], 0.6, 1.2)
                            if rr:
                                gs.append(rr[0]); ws.append(nn); r2s.append(rr[2])
                    i = j + 1
                del S
            if gs:
                gs, ws, r2s = np.array(gs), np.array(ws, float), np.array(r2s)
                print(f"  {sn:6s} {grp:5s} nruns {len(gs):3d} sec {ws.sum()/100:7.0f}  "
                      f"g(weighted) {np.average(gs, weights=ws):6.3f}  g median {np.median(gs):6.3f}  "
                      f"range {gs.min():.2f}..{gs.max():.2f}  R2 median {np.median(r2s):.2f}")
            else:
                print(f"  {sn:6s} {grp:5s} no run >=60 s with median speed in bin and p95|model| >= 1")


if __name__ == "__main__":
    main()
