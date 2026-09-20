# -*- coding: utf-8 -*-
"""ADV1: re-derive the goal metric from the logs, per route, with no code shared with the other streams.

Asks three things the programme's headline numbers depend on:
  1. Does J = sum|X-Y|^2 / sum|X|^2 over 0.15-2.4 Hz reproduce 1.350 (rev 6.4) and 0.442 (V282)?
  2. What is the ROUTE-TO-ROUTE scatter of J inside a family?  (If it is large, every closure
     percentage quoted to 0.1 % is quoted past its own resolution.)
  3. What is the flown kp/LAF envelope ON THE TORQUE EPS, as opposed to pooled over both EPS builds?
"""
import json
import sys

import numpy as np

import advlib as A


def per_route():
    rows = []
    for rk, meta in A.FLOWN.items():
        try:
            N = A.load_nodes(rk)
        except Exception as e:  # noqa: BLE001
            print(f"  {rk}: {e}"); continue
        fr, sp, vs = A.windows(N)
        if len(vs) == 0:
            print(f"  {rk:22s} {meta['fam']:8s}  no >=30 s engaged hands-off run above {A.VMIN} m/s")
            continue
        sel = A.bandsel(fr)
        X, Y = sp["X"], sp["Y"]
        # sign of Y relative to X, measured (livePose device frame); report it, never assume it
        c = float(np.real(np.sum(np.conj(X[:, sel]) * Y[:, sel])) /
                  np.sqrt(np.sum(np.abs(X[:, sel]) ** 2) * np.sum(np.abs(Y[:, sel]) ** 2)))
        J, num, den = A.metric(X, X - Y, sel)
        # per-window J, for the scatter
        jw = np.sum(np.abs((X - Y)[:, sel]) ** 2, 1) / np.sum(np.abs(X[:, sel]) ** 2, 1)
        rows.append(dict(rk=rk, fam=meta["fam"], eps=meta["eps"], kp=meta["kp"], laf=meta["laf"],
                         kpl=meta["kp"] / meta["laf"], ki=meta["ki"], ki_hi=meta["ki_hi"],
                         nwin=int(len(vs)), v=float(np.median(vs)), sec=float(len(vs) * A.NPERSEG / A.FS / 2),
                         corrXY=c, J=J, num=num, den=den,
                         Jw_med=float(np.median(jw)), Jw_p25=float(np.percentile(jw, 25)),
                         Jw_p75=float(np.percentile(jw, 75))))
        print(f"  {rk:22s} {meta['fam']:8s} nwin {len(vs):4d} v {np.median(vs):5.1f}  corr(X,Y) {c:+.3f}  J {J:6.3f}",
              flush=True)
        del N, sp, X, Y
    return rows


def main():
    print(A._self_test())
    print("\nPER ROUTE: J over 0.15-2.4 Hz, >=15 m/s, engaged hands-off runs >=30 s, 20.48 s Hann windows, 50% overlap")
    rows = per_route()
    json.dump(rows, open(A.OUT / "adv1_metric.json", "w"), indent=1)

    print("\nPOOLED BY FAMILY (one denominator across every window of the family):")
    fams = {}
    for r in rows:
        fams.setdefault(r["fam"], []).append(r)
    for f, rs in fams.items():
        num = sum(r["num"] for r in rs); den = sum(r["den"] for r in rs)
        js = [r["J"] for r in rs]
        print(f"  {f:8s} n_routes {len(rs)}  J_pooled {num/den:6.3f}   per-route J {['%.3f'%j for j in js]}"
              f"   spread {max(js)/min(js):.2f}x" if len(rs) > 1 else
              f"  {f:8s} n_routes {len(rs)}  J_pooled {num/den:6.3f}   per-route J {['%.3f'%j for j in js]}")

    print("\nTHE HEADLINE PAIR, as the brief states it (rev 6.4 = T64 = 6c/68c6 + 6d; V282 = 64 + 65 + 6c/2bc8):")
    for label, keys in [("rev 6.4 (T64)", ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]),
                        ("V282 reference", ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"])]:
        rs = [r for r in rows if r["rk"] in keys]
        if not rs:
            continue
        num = sum(r["num"] for r in rs); den = sum(r["den"] for r in rs)
        print(f"  {label:16s} J = {num/den:6.3f}   (per route {['%.3f'%r['J'] for r in rs]})")

    print("\nWITHIN-FAMILY SCATTER of J, per 20.48 s window (the resolution any closure % is quoted against):")
    for r in rows:
        print(f"  {r['rk'][:8]} {r['fam']:8s} J {r['J']:6.3f}  window median {r['Jw_med']:6.3f}"
              f"  IQR [{r['Jw_p25']:.3f}, {r['Jw_p75']:.3f}]  n {r['nwin']}")

    print("\nFLOWN kp/LAF ENVELOPE, split by EPS BUILD (the brief pools them as '0.050-0.379'):")
    for eps in ("V282", "V293"):
        rs = sorted([r for r in rows if r["eps"] == eps], key=lambda r: r["kpl"])
        if not rs:
            continue
        print(f"  EPS {eps}: " + "  ".join(f"{r['rk'][:8]}={r['kpl']:.4f}" for r in rs))
        print(f"    -> envelope {min(r['kpl'] for r in rs):.4f} .. {max(r['kpl'] for r in rs):.4f}"
              f"  (span {max(r['kpl'] for r in rs)/min(r['kpl'] for r in rs):.2f}x)")
    tor = [r["kpl"] for r in rows if r["eps"] == "V293"]
    if tor:
        for kp in (2.0, 2.5, 3.0):
            print(f"    SteerKP {kp} -> kp/LAF {kp/14:.4f} = {kp/14/max(tor):.2f}x the TOP of the torque-EPS envelope")
    return 0


if __name__ == "__main__":
    sys.exit(main())
