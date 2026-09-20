# -*- coding: utf-8 -*-
"""Stage 0 of the budget: does the software replay reproduce the LOGGED setpoint?

If Zhat != Z the split of the software leg into (delay canceller + jerk filter) and (ref filter) is
not licensed and nothing downstream is reported for that route.  This is the gate.

Also censuses the two jerk clips (a nonlinearity that would put amplitude dependence in the SOFTWARE
leg) and each route's flown lat_delay and ref-filter rc.

ANALYSIS ONLY, read-only.  usage: python sb_validate.py > out/VALIDATE-OUT.txt
"""
import sys

import numpy as np

import sb_lib as L
import v282cmp as V


def main():
    print("=" * 130)
    print("SOFTWARE REPLAY VALIDATION -- logged desiredLateralAccel vs the replay of latcontrol_torque's")
    print("setpoint chain from the SAME route's logged desiredCurvature, vEgo and liveDelay.lateralDelay.")
    print("  corr / rms(Zhat-Z) as a fraction of rms(Z) / p99 |Zhat-Z|, over LATERALLY ENGAGED frames only.")
    print("  RF = flown AccordRefFilter (None = the code has no ref-filter stage at that commit).")
    print("  Jhz = the flown jerk-filter cutoff (git-checked per commit).")
    print("=" * 130)
    hdr = (f"{'route':24s} {'grp':8s} {'commit':10s} {'RF':>5s} {'Jhz':>4s} {'D_med':>6s} "
           f"{'engaged s':>9s} {'corr':>8s} {'rmsE/rmsZ':>10s} {'p99|E|':>8s} {'rmsZ':>7s} "
           f"{'clipRAW%':>8s} {'clipFLT%':>8s}  verdict")
    print(hdr)
    rows = []
    for rk, (grp, cm, rf) in sorted(L.ROUTES.items(), key=lambda kv: (kv[1][0], kv[0])):
        f = V.CACHE / f"{rk}.npz"
        if not f.exists():
            print(f"{rk:24s} {grp:8s} NO CACHE"); continue
        S = L.load_route(rk)
        cfg = L.COMMIT[cm]
        rc = rf if cfg["ref_block"] else None
        Z0, Zh, ok, cr, cf = L.replay_setpoint(S, cfg["jerk_hz"], rc)
        m = V.usable(S) & ok & np.isfinite(S["setpoint"])
        Z = S["setpoint"]
        if m.sum() < 1000:
            print(f"{rk:24s} {grp:8s} too few frames {m.sum()}"); del S; continue
        e = Zh[m] - Z[m]
        rmsZ = float(np.sqrt(np.mean(Z[m] ** 2)))
        rmsE = float(np.sqrt(np.mean(e ** 2)))
        cc = float(np.corrcoef(Zh[m], Z[m])[0, 1])
        p99 = float(np.percentile(np.abs(e), 99))
        Dm = float(np.median(S["lat_delay"][m]))
        pr = 100.0 * float(np.mean(cr[m]))
        pf = 100.0 * float(np.mean(cf[m]))
        good = (cc > 0.995) and (rmsE / rmsZ < 0.12)
        print(f"{rk:24s} {grp:8s} {cm:10s} {str(rc):>5s} {cfg['jerk_hz']:>4.1f} {Dm:>6.3f} "
              f"{m.sum()/L.FS:>9.0f} {cc:>8.5f} {rmsE/rmsZ:>10.4f} {p99:>8.4f} {rmsZ:>7.4f} "
              f"{pr:>8.3f} {pf:>8.3f}  {'PASS' if good else 'FAIL'}")
        rows.append((rk, grp, cc, rmsE / rmsZ, good))
        del S
    print()
    nb = [r for r in rows if not r[4]]
    print(f"{len(rows)} routes replayed, {len(rows)-len(nb)} PASS, {len(nb)} FAIL"
          + ("" if not nb else "  -> " + ", ".join(r[0] for r in nb)))

    # ---------------------------------------------------------------------------------------
    print()
    print("=" * 130)
    print("CONTROL: the analytic response of each software stage, as a check on the measured legs.")
    print("  canceller = e^{-sD} + F_j(s)(1-e^{-sD}) with the flown D and the flown jerk cutoff,")
    print("  ref filter = two cascaded FirstOrderFilters at the flown rc.  |H| and group lag (ms).")
    print("=" * 130)
    fg = np.concatenate([np.linspace(1e-4, 0.05, 40), np.linspace(0.05, 1.5, 400)])
    cases = [("V282   D 0.200 Jhz 1.2 RF none", 0.200, 1.2, None),
             ("T3/T4  D 0.276 Jhz 1.2 RF 0.12", 0.276, 1.2, 0.12),
             ("T5     D 0.286 Jhz 1.2 RF 0.12", 0.286, 1.2, 0.12),
             ("T64    D 0.299 Jhz 4.0 RF 0.06", 0.299, 4.0, 0.06),
             ("T2     D 0.200 Jhz 1.2 RF none", 0.200, 1.2, None)]
    print(f"{'case':32s} " + " ".join(f"{fc:>17s}" for fc in ["0.10 Hz", "0.22 Hz", "0.45 Hz", "0.85 Hz"]))
    print(f"{'':32s} " + " ".join(f"{'|H|   lag ms':>17s}" for _ in range(4)))
    for nm, Dv, jh, rc in cases:
        Hc = L.canceller_H(fg, Dv, jh)
        Hr = L.ref_filter_H(fg, rc)
        for tag, H in (("  canceller+jerk", Hc), ("  ref filter   ", Hr), ("  = whole X->Z ", Hc * Hr)):
            lg = L.group_lag_ms(H, fg)
            s = f"{nm if tag.strip()=='canceller+jerk' else '':32s}"
            cells = []
            for ft in (0.10, 0.22, 0.45, 0.85):
                k = int(np.argmin(np.abs(fg - ft)))
                cells.append(f"{abs(H[k]):6.3f} {lg[k]:+7.0f}  ")
            print(s[:32] + tag + " " + " ".join(f"{c:>17s}" for c in cells))
    return 0


if __name__ == "__main__":
    print(L._self_test())
    print(V._self_test())
    print()
    sys.exit(main())
