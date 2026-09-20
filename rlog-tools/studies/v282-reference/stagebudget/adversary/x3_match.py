# -*- coding: utf-8 -*-
"""ATTACK 2 -- the A3 stratum is not matched, and ATTACK 5 -- wheel -> yaw must be build-independent.

A3 is an OPEN-ENDED stratum (p95 |model| >= 1.0 m/s2 with no ceiling) selected on a PERCENTILE, so a
window that is straight for 9 s with one 2.4 m/s2 spike qualifies alongside a window holding 1.3 m/s2
for 10 s.  If the two builds occupy different parts of it, |H| is comparing roads, not builds.

Tests:
  (a) common support of the two builds in (window steering p95, median |model|, speed, speed sd)
  (b) |H| restricted to the overlap box, and with nearest-neighbour 1:1 matching
  (c) within-BUILD dose-response of |H| against the same window descriptors -- if V282's own |H| climbs
      to ~2 on torque-like windows, the "build difference" is the window mix
  (d) an amplitude axis that is honest for a band-limited transfer: IN-BAND demand RMS, not p95
  (e) wheel -> yaw.  Pure vehicle.  It MUST be build-independent at matched speed and amplitude.
"""
import numpy as np
import adv_lib as L

CHI = {c: i for i, c in enumerate(["X", "Y", "Z", "W", "A", "C", "K"])}
N = 1024
F1, F2 = 0.60, 1.20


def load_all(n=N):
    R = {}
    for r in L.ROUTES:
        D = np.load(L.OUT / f"spec_{r}_n{n}.npz")
        fr = D["m_fr"]
        b = (fr >= F1) & (fr < F2)
        X = D["F_lin_hann"][:, CHI["X"], 0, :]
        R[r] = dict(F=D["F_lin_hann"], fr=fr,
                    v=D["m_v"], ap95=D["m_ap95"], sa50=D["m_sa50"], sa95=D["m_sa95"],
                    vsd=D["m_vsd"], ax50=D["m_ax50"], xrms=D["m_xrms"],
                    # in-band demand RMS: the amplitude the transfer measurement actually sees
                    inb=np.sqrt((np.abs(X[:, b]) ** 2).sum(1)))
    return R


def H(R, picks, ix="X", iy="Y", f1=F1, f2=F2):
    Fs = [R[r]["F"][m] for r, m in picks if m.sum()]
    if not Fs:
        return None
    return L.cell(np.concatenate(Fs, 0), CHI[ix], CHI[iy], f1, f2, R[picks[0][0]]["fr"])


def main():
    R = load_all()
    print("=" * 150)
    print("(a) COMMON SUPPORT.  A3 windows at 8-15 and 15-22 m/s, pooled per build.")
    print("=" * 150)
    for sb, sn in ((1, "8-15"), (2, "15-22")):
        lo, hi = L.SPD[sb]
        for grp, rts in (("V282", L.V282), ("TORQ", L.TORQ)):
            sa, ax, vv, vs, ib = [], [], [], [], []
            for r in rts:
                d = R[r]
                m = (d["v"] >= lo) & (d["v"] < hi) & (d["ap95"] >= 1.0)
                sa.append(d["sa95"][m]); ax.append(d["ax50"][m]); vv.append(d["v"][m])
                vs.append(d["vsd"][m]); ib.append(d["inb"][m])
            sa, ax, vv, vs, ib = map(np.concatenate, (sa, ax, vv, vs, ib))
            q = lambda a: f"{np.percentile(a,10):7.2f} {np.median(a):7.2f} {np.percentile(a,90):7.2f}"
            print(f"  {sn:6s} {grp}  n {len(sa):3d}   |sa|95 p10/50/90 {q(sa)}   med|model| {q(ax)}   "
                  f"v {q(vv)}   vsd {q(vs)}   inband {q(ib)}")

    print("\n" + "=" * 150)
    print("(b) |H| 0.60-1.20 Hz RESTRICTED TO THE OVERLAP BOX, and 1:1 nearest-neighbour matched.")
    print("    Box = [max of the two p10, min of the two p90] on |sa|95 AND median |model| AND speed.")
    print("=" * 150)
    for sb, sn in ((1, "8-15"), (2, "15-22")):
        lo, hi = L.SPD[sb]

        def grab(rts):
            out = []
            for r in rts:
                d = R[r]
                m = (d["v"] >= lo) & (d["v"] < hi) & (d["ap95"] >= 1.0)
                out.append((r, m))
            return out

        pv, pt = grab(L.V282), grab(L.TORQ)
        feats = lambda p: np.concatenate([np.stack([R[r]["sa95"][m], R[r]["ax50"][m], R[r]["v"][m]], 1)
                                          for r, m in p if m.sum()], 0)
        Av, At = feats(pv), feats(pt)
        box = [(max(np.percentile(Av[:, k], 10), np.percentile(At[:, k], 10)),
                min(np.percentile(Av[:, k], 90), np.percentile(At[:, k], 90))) for k in range(3)]
        print(f"  {sn}: overlap box  |sa|95 [{box[0][0]:.1f},{box[0][1]:.1f}] deg   "
              f"med|model| [{box[1][0]:.2f},{box[1][1]:.2f}]   v [{box[2][0]:.1f},{box[2][1]:.1f}]")
        res = {}
        for nm, p in (("V282", pv), ("TORQ", pt)):
            pp = []
            for r, m in p:
                d = R[r]
                mm = m.copy()
                for k, key in enumerate(("sa95", "ax50", "v")):
                    mm &= (d[key] >= box[k][0]) & (d[key] <= box[k][1])
                pp.append((r, mm))
            c = H(R, pp)
            res[nm] = c
            tot = sum(int(m.sum()) for _, m in pp)
            print(f"    {nm}  in-box n {tot:3d}  " + ("--" if c is None else
                  f"H1 {c['H1']:.3f} Hcoh {c['Hcoh']:.3f} Htot {c['Htot']:.3f} g2 {c['g2']:.2f}"))
        if res["V282"] and res["TORQ"]:
            print(f"    ratio in box  H1 {res['TORQ']['H1']/res['V282']['H1']:.2f}   "
                  f"Htot {res['TORQ']['Htot']/res['V282']['Htot']:.2f}")

        # 1:1 nearest neighbour on standardised (log sa95, log ax50, v), greedy, caliper 0.75 sd
        def flat(p):
            idx = []
            for r, m in p:
                for i in np.where(m)[0]:
                    idx.append((r, i))
            return idx
        iv, it = flat(pv), flat(pt)
        Z = lambda idx: np.stack([[np.log(max(R[r]["sa95"][i], .5)) for r, i in idx],
                                  [np.log(max(R[r]["ax50"][i], .02)) for r, i in idx],
                                  [R[r]["v"][i] for r, i in idx]], 1)
        Zv, Zt = Z(iv), Z(it)
        mu, sd = np.vstack([Zv, Zt]).mean(0), np.vstack([Zv, Zt]).std(0) + 1e-9
        Zv, Zt = (Zv - mu) / sd, (Zt - mu) / sd
        used, pairs = set(), []
        for j in range(len(it)):
            d = np.linalg.norm(Zv - Zt[j], axis=1)
            for k in np.argsort(d):
                if k not in used and d[k] < 0.75:
                    used.add(int(k)); pairs.append((int(k), j)); break
        if pairs:
            pm = {}
            for k, j in pairs:
                pm.setdefault(("V", iv[k][0]), []).append(iv[k][1])
                pm.setdefault(("T", it[j][0]), []).append(it[j][1])
            mk = lambda tag: [(r, np.isin(np.arange(len(R[r]["v"])), v))
                              for (t, r), v in pm.items() if t == tag]
            cv, ct = H(R, mk("V")), H(R, mk("T"))
            print(f"    1:1 matched pairs {len(pairs):3d}  V282 H1 {cv['H1']:.3f} (n{cv['nwin']})  "
                  f"TORQ H1 {ct['H1']:.3f} (n{ct['nwin']})  ratio {ct['H1']/cv['H1']:.2f}")
        else:
            print("    1:1 matched pairs   0  -- NO torque A3 window has a V282 counterpart inside the caliper")

    print("\n" + "=" * 150)
    print("(c) WITHIN-BUILD dose-response of |H| 0.6-1.2 Hz against the window descriptors, 8-22 m/s,")
    print("    all amplitude strata.  If |H| is a function of the window content, the build contrast in a")
    print("    mismatched stratum is that function, not the build.")
    print("=" * 150)
    for key, lab in (("sa95", "|sa|95 deg"), ("ax50", "median |model|"), ("inb", "in-band demand RMS"),
                     ("vsd", "speed sd m/s")):
        for grp, rts in (("V282", L.V282), ("TORQ", L.TORQ)):
            vals = np.concatenate([R[r][key][(R[r]["v"] >= 8) & (R[r]["v"] < 22)] for r in rts])
            ed = np.percentile(vals, [0, 25, 50, 75, 100])
            row = []
            for k in range(4):
                pp = [(r, (R[r]["v"] >= 8) & (R[r]["v"] < 22) & (R[r][key] >= ed[k]) &
                       (R[r][key] <= ed[k + 1] if k == 3 else R[r][key] < ed[k + 1])) for r in rts]
                c = H(R, pp)
                row.append(f"{c['H1']:5.2f}(n{c['nwin']:3d})" if c else "   --     ")
            print(f"  {lab:22s} {grp}  quartiles of {key}: {[round(float(e),2) for e in ed]}")
            print(f"  {'':22s} {'':5s}  |H| by quartile: " + "  ".join(row))

    print("\n" + "=" * 150)
    print("(d) AMPLITUDE AXIS REDEFINED to IN-BAND (0.6-1.2 Hz) demand RMS, common absolute cuts.")
    print("    This is the amplitude the transfer measurement actually operates on; p95 of the whole")
    print("    window's |model| is a different quantity and the two builds populate it differently.")
    print("=" * 150)
    allinb = np.concatenate([R[r]["inb"][(R[r]["v"] >= 8) & (R[r]["v"] < 22)] for r in L.ROUTES])
    cuts = np.percentile(allinb, [0, 50, 80, 95, 100])
    print(f"  cuts (pooled quantiles, both builds): {[round(float(c),4) for c in cuts]}")
    for sb, sn in ((1, "8-15"), (2, "15-22")):
        lo, hi = L.SPD[sb]
        for k in range(4):
            out = []
            for grp, rts in (("V282", L.V282), ("TORQ", L.TORQ)):
                pp = [(r, (R[r]["v"] >= lo) & (R[r]["v"] < hi) & (R[r]["inb"] >= cuts[k]) &
                       (R[r]["inb"] <= cuts[k + 1] if k == 3 else R[r]["inb"] < cuts[k + 1])) for r in rts]
                out.append(H(R, pp))
            cv, ct = out
            s = f"  {sn:6s} inband Q{k+1}  "
            s += f"V282 {cv['H1']:5.2f}(n{cv['nwin']:3d}) " if cv else "V282  --        "
            s += f"TORQ {ct['H1']:5.2f}(n{ct['nwin']:3d}) " if ct else "TORQ  --        "
            if cv and ct:
                s += f"ratio {ct['H1']/cv['H1']:5.2f}"
            print(s)

    print("\n" + "=" * 150)
    print("(e) SANITY ON THE CONTROL: wheel -> yaw (W deg -> Y m/s2).  Pure vehicle.  Must be")
    print("    build-independent at matched speed.  A difference here is a comparison error upstream.")
    print("=" * 150)
    for sb, sn in enumerate(L.SPDN):
        lo, hi = L.SPD[sb]
        for band, bn in (((0.15, 0.30), "0.15-0.30"), ((0.30, 0.60), "0.30-0.60"),
                         ((0.60, 1.20), "0.60-1.20"), ((1.20, 2.40), "1.20-2.40")):
            out = []
            for grp, rts in (("V282", L.V282), ("TORQ", L.TORQ)):
                pp = [(r, (R[r]["v"] >= lo) & (R[r]["v"] < hi)) for r in rts]
                out.append(H(R, pp, ix="W", iy="Y", f1=band[0], f2=band[1]))
            cv, ct = out
            if cv and ct:
                vm = np.median(np.concatenate([R[r]["v"][(R[r]["v"] >= lo) & (R[r]["v"] < hi)] for r in L.V282]))
                tm = np.median(np.concatenate([R[r]["v"][(R[r]["v"] >= lo) & (R[r]["v"] < hi)] for r in L.TORQ]))
                # expected bicycle scaling: a_lat/delta ~ v^2 / (L*SR*(1+K v^2)) -> compare after /v^2
                print(f"  {sn:6s} {bn}  V282 H {cv['H1']:7.4f} (v50 {vm:4.1f}, g2 {cv['g2']:.2f}, n{cv['nwin']:3d})  "
                      f"TORQ H {ct['H1']:7.4f} (v50 {tm:4.1f}, g2 {ct['g2']:.2f}, n{ct['nwin']:3d})  "
                      f"ratio {ct['H1']/cv['H1']:5.3f}   ratio/(vT/vV)^2 {ct['H1']/cv['H1']/(tm/vm)**2:5.3f}")


if __name__ == "__main__":
    main()
