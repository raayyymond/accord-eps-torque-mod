# -*- coding: utf-8 -*-
"""ROUTE-LEVEL INFERENCE.  Windows inside one drive are not independent draws of "a build"; the unit
that varies between the things being compared is the ROUTE.  Both headline claims are re-tested with
the route as the unit and an exact permutation test over the 3 + 9 route labels.

  claim B: |H| 0.60-1.20 Hz in the A3 stratum, 8-22 m/s     (regime B)
  claim A: the downstream Z->Y lag at 0.15-0.30 Hz          (regime A's unnamed residual)
  control: wheel -> yaw at 0.15-0.60 Hz, speed-matched      (must NOT separate)
"""
import itertools
import numpy as np
import adv_lib as L

CHI = {c: i for i, c in enumerate(["X", "Y", "Z", "W", "A", "C", "K"])}


def perm_p(vals, istorq, stat=np.mean):
    """Exact permutation test over route labels: how often does a random 3/9 split of the SAME routes
    give a group difference at least as large as the observed one?"""
    vals = np.asarray(vals, float)
    n, k = len(vals), int((~istorq).sum())
    obs = stat(vals[istorq]) - stat(vals[~istorq])
    cnt = tot = 0
    for c in itertools.combinations(range(n), k):
        m = np.zeros(n, bool); m[list(c)] = True
        d = stat(vals[~m]) - stat(vals[m])
        tot += 1
        if abs(d) >= abs(obs) - 1e-12:
            cnt += 1
    return obs, cnt / tot, tot


def main():
    R1 = {r: np.load(L.OUT / f"spec_{r}_n1024.npz") for r in L.ROUTES}
    R2 = {r: np.load(L.OUT / f"spec_{r}_n2048.npz") for r in L.ROUTES}
    fr1, fr2 = R1[L.V282[0]]["m_fr"], R2[L.V282[0]]["m_fr"]
    rts = list(L.V282) + list(L.TORQ)
    istorq = np.array([L.ROUTES[r]["eps"] == "V293" for r in rts])

    print("=" * 150)
    print("A. REGIME B at the route level.  |H1| 0.60-1.20 Hz, 8-22 m/s, A3 (p95|model| >= 1).")
    print("   Routes with fewer than 3 windows in the cell are printed and EXCLUDED from the test.")
    print("=" * 150)
    vals, keep, secs = [], [], []
    for r in rts:
        d = R1[r]
        m = (d["m_v"] >= 8) & (d["m_v"] < 22) & (d["m_ap95"] >= 1.0)
        if m.sum() < 3:
            print(f"  {r:24s} {L.ROUTES[r]['g']:6s} n {int(m.sum()):2d}  EXCLUDED (n<3)")
            keep.append(False); vals.append(np.nan); secs.append(m.sum() * 10.24)
            continue
        c = L.cell(d["F_lin_hann"][m], CHI["X"], CHI["Y"], 0.6, 1.2, fr1)
        print(f"  {r:24s} {L.ROUTES[r]['g']:6s} n {int(m.sum()):2d} ({m.sum()*10.24:5.0f} s)  "
              f"H1 {c['H1']:6.3f}  g2 {c['g2']:.2f}")
        keep.append(True); vals.append(c["H1"]); secs.append(m.sum() * 10.24)
    keep = np.array(keep); vals = np.array(vals); secs = np.array(secs)
    v, it = vals[keep], istorq[keep]
    obs, p, tot = perm_p(v, it)
    print(f"\n  V282 routes kept {int((~it).sum())} mean |H| {v[~it].mean():.3f} (range {v[~it].min():.2f}-{v[~it].max():.2f})")
    print(f"  TORQ routes kept {int(it.sum())} mean |H| {v[it].mean():.3f} (range {v[it].min():.2f}-{v[it].max():.2f})")
    print(f"  route-level difference {obs:+.3f}   exact permutation p = {p:.4f}  ({tot} splits)")
    print(f"  total seconds behind the cell: V282 {secs[keep][~it].sum():.0f} s, TORQ {secs[keep][it].sum():.0f} s")

    print("\n" + "=" * 150)
    print("B. REGIME A's downstream residual at the route level.  Z->Y phase-slope lag, 0.15-0.30 Hz, 8-22 m/s.")
    print("=" * 150)
    vals2, keep2 = [], []
    for r in rts:
        d = R2[r]
        m = (d["m_v"] >= 8) & (d["m_v"] < 22)
        if m.sum() < 4:
            keep2.append(False); vals2.append(np.nan); continue
        c = L.cell(d["F_lin_hann"][m], CHI["Z"], CHI["Y"], 0.15, 0.30, fr2)
        keep2.append(True); vals2.append(c["lag_gd_ms"])
    vals2 = np.array(vals2); keep2 = np.array(keep2)
    v2, i2 = vals2[keep2], istorq[keep2]
    obs2, p2, tot2 = perm_p(v2, i2)
    print(f"  V282 {np.round(v2[~i2]).astype(int)}  mean {v2[~i2].mean():.0f} ms")
    print(f"  TORQ {np.round(v2[i2]).astype(int)}  mean {v2[i2].mean():.0f} ms")
    print(f"  route-level difference {obs2:+.0f} ms   exact permutation p = {p2:.4f}  ({tot2} splits)")
    print(f"  torque routes at or below the V282 MAXIMUM ({v2[~i2].max():.0f} ms): "
          f"{int((v2[i2] <= v2[~i2].max()).sum())} of {int(i2.sum())}")
    print(f"  drop the single worst torque route: mean {np.sort(v2[i2])[:-1].mean():.0f} ms, "
          f"difference {np.sort(v2[i2])[:-1].mean()-v2[~i2].mean():+.0f} ms")
    # median-based version (robust)
    obs2m, p2m, _ = perm_p(v2, i2, stat=np.median)
    print(f"  median-based: difference {obs2m:+.0f} ms, exact permutation p = {p2m:.4f}")

    print("\n" + "=" * 150)
    print("C. CONTROL at the route level: wheel -> yaw, 0.15-0.60 Hz, speed-matched by restricting to")
    print("   16-22 m/s (both builds well populated).  A build separation here would invalidate everything.")
    print("=" * 150)
    vals3, keep3 = [], []
    for r in rts:
        d = R1[r]
        m = (d["m_v"] >= 16) & (d["m_v"] < 22)
        if m.sum() < 4:
            keep3.append(False); vals3.append(np.nan); continue
        c = L.cell(d["F_lin_hann"][m], CHI["W"], CHI["Y"], 0.15, 0.60, fr1)
        keep3.append(True); vals3.append(c["H1"])
    vals3 = np.array(vals3); keep3 = np.array(keep3)
    v3, i3 = vals3[keep3], istorq[keep3]
    obs3, p3, tot3 = perm_p(v3, i3)
    print(f"  V282 {np.round(v3[~i3], 4)}  mean {v3[~i3].mean():.4f}")
    print(f"  TORQ {np.round(v3[i3], 4)}  mean {v3[i3].mean():.4f}")
    print(f"  route-level difference {obs3:+.4f} ({100*obs3/v3[~i3].mean():+.1f}%)  exact permutation p = {p3:.4f}")

    print("\n" + "=" * 150)
    print("D. REGIME A's TOTAL gap at the route level, for comparison: X->Y phase-slope lag 0.15-0.30 Hz.")
    print("=" * 150)
    vals4, keep4 = [], []
    for r in rts:
        d = R2[r]
        m = (d["m_v"] >= 8) & (d["m_v"] < 22)
        if m.sum() < 4:
            keep4.append(False); vals4.append(np.nan); continue
        c = L.cell(d["F_lin_hann"][m], CHI["X"], CHI["Y"], 0.15, 0.30, fr2)
        keep4.append(True); vals4.append(c["lag_gd_ms"])
    vals4 = np.array(vals4); keep4 = np.array(keep4)
    v4, i4 = vals4[keep4], istorq[keep4]
    obs4, p4, _ = perm_p(v4, i4)
    print(f"  V282 {np.round(v4[~i4]).astype(int)}  mean {v4[~i4].mean():.0f} ms")
    print(f"  TORQ {np.round(v4[i4]).astype(int)}  mean {v4[i4].mean():.0f} ms")
    print(f"  route-level difference {obs4:+.0f} ms   exact permutation p = {p4:.4f}")
    med4, pm4, _ = perm_p(v4, i4, stat=np.median)
    print(f"  median-based: {med4:+.0f} ms, p = {pm4:.4f}")

    print("\n" + "=" * 150)
    print("E. EXPOSURE of the A3 stratum, from my own windows -- what regime B is actually worth.")
    print("=" * 150)
    for lo, hi, nm in ((8, 15, "8-15"), (15, 22, "15-22"), (8, 22, "8-22")):
        for gn, g in (("V282", L.V282), ("TORQ", L.TORQ)):
            tot = sum(int(((R1[r]["m_v"] >= 0)).sum()) for r in g)
            a3 = sum(int(((R1[r]["m_v"] >= lo) & (R1[r]["m_v"] < hi) & (R1[r]["m_ap95"] >= 1.0)).sum()) for r in g)
            a2 = sum(int(((R1[r]["m_v"] >= lo) & (R1[r]["m_v"] < hi) & (R1[r]["m_ap95"] >= 0.3)
                          & (R1[r]["m_ap95"] < 1.0)).sum()) for r in g)
            print(f"  {nm:6s} {gn}  all windows {tot:4d} ({tot*10.24:6.0f} s)  A3 {a3:3d} ({100*a3/tot:5.1f}%)  "
                  f"A2+A3 {a2+a3:3d} ({100*(a2+a3)/tot:5.1f}%)")


if __name__ == "__main__":
    main()
