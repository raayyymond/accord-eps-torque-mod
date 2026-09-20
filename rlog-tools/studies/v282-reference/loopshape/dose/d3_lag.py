# -*- coding: utf-8 -*-
"""D3 -- resolve corr(kp/LAF, loop lag) = +0.808: does more P really give MORE lag on this car?

The study's L34 leg is the group lag of the LOOP STAGE Z -> M (shaped setpoint -> wheel angle in
lat-accel units).  That stage is NOT the sensitivity.  With a feedforward present,

    M/Z  =  P * (F_z + C) / (1 + P*C)  =  [P*(F_z + C)] * S

so its group lag splits into a FEEDFORWARD part (P*(F_z+C), which more P makes FASTER too, but
whose size is set by F_z) and a LOOP part (S = 1/(1+PC), which is a phase LEAD -- more P can only
REDUCE lag through it).  Every quantity here is measured:

  F_z(jw) = S_{Z,f} / S_{Z,Z}      -- logged pid.f IS the feedforward, so this needs no model
  M/Z     = S_{Z,M} / S_{Z,Z}
  P, S    -- from d1's IV identification and the fork's own controller arithmetic

If the +0.808 is real, the loop part must carry it.  If the loop part goes the other way, the
correlation lives in F_z (which covaries with fork version, not with kp) and the dose is not void.
"""
import json
import numpy as np
from scipy import signal
import dlib as D
from d1_ident import k_tot, segs_for

FS = 100.0
NPS = 2048
BAND = (0.15, 0.30)     # the band the study reports the lag in


def gdelay(f, H, f1, f2):
    """Group delay of H over [f1,f2], s, from a straight-line fit to the phase unwrapped INSIDE
    the band only (a nan anywhere else must not propagate through np.unwrap)."""
    m = (f >= f1) & (f <= f2) & np.isfinite(H)
    if m.sum() < 3:
        return float("nan")
    ph = np.unwrap(np.angle(H[m]))
    a = np.polyfit(f[m], ph, 1)[0]
    return float(-a / (2 * np.pi))


def main():
    res = json.load(open(D.OUT / "d1_hi.json"))
    print("Measured stage lags at 0.15-0.30 Hz, >=15 m/s (positive = the car lags), and the split\n")
    print(f"{'route':22s} {'grp':8s} {'kp/LAF':>7s} {'|F_z|':>6s} {'ph(F_z)':>8s} | "
          f"{'lag M/Z':>8s} {'lag FFpart':>10s} {'lag S':>7s} {'sum':>7s} | {'|S|':>5s} {'|L|':>5s}")
    rows = []
    for rt, cfg in D.ROUTES.items():
        S = D.load(rt)
        m = D.V.usable(S, 15.0)
        sg = []
        for a, b in D.V.runs(m, S["t"], min_s=30.0):
            if b - a < NPS:
                continue
            Z = np.nan_to_num(S["setpoint"][a:b])
            F = np.nan_to_num(S["f"][a:b])
            M = np.nan_to_num(S["la_act"][a:b])
            sg.append((Z, F, M))
        del S
        if not sg or rt not in res:
            print(f"{rt:22s} {cfg['g']:8s}  (no runs)")
            continue
        acc = dict(zz=None, zf=None, zm=None)
        fr = None
        for Z, F, M in sg:
            Z, F, M = Z - Z.mean(), F - F.mean(), M - M.mean()
            kw = dict(fs=FS, nperseg=NPS, noverlap=NPS // 2)
            f, zz = signal.welch(Z, **kw)
            _, zf = signal.csd(Z, F, **kw)
            _, zm = signal.csd(Z, M, **kw)
            w = len(Z)
            for k, vv in (("zz", zz), ("zf", zf), ("zm", zm)):
                acc[k] = vv * w if acc[k] is None else acc[k] + vv * w
            fr = f
        Fz = acc["zf"] / acc["zz"]
        MZ = acc["zm"] / acc["zz"]
        v = res[rt]
        f1 = np.array(v["f"])                      # d1 ran at nperseg 1024; re-grid onto fr
        P = (np.interp(fr, f1, np.array(v["P_re"]))
             + 1j * np.interp(fr, f1, np.array(v["P_im"])))
        K = k_tot(fr, cfg, v["v"], v["k_m"])
        Ssens = 1.0 / (1.0 + K * P)
        FFpart = P * (Fz + K)          # the reference path, with the measured F_z
        lag_mz = gdelay(fr, MZ, *BAND)
        lag_ff = gdelay(fr, FFpart, *BAND)
        lag_s = gdelay(fr, Ssens, *BAND)
        b = (fr >= BAND[0]) & (fr <= BAND[1])
        print(f"{rt:22s} {cfg['g']:8s} {cfg['kp']/cfg['laf']:7.4f} "
              f"{np.abs(Fz[b]).mean():6.3f} {np.degrees(np.angle(Fz[b].sum())):8.1f} | "
              f"{lag_mz:8.3f} {lag_ff:10.3f} {lag_s:7.3f} {lag_ff+lag_s:7.3f} | "
              f"{np.abs(Ssens[b]).mean():5.3f} {np.abs((K*P)[b]).mean():5.3f}")
        rows.append(dict(rt=rt, g=cfg["g"], kpl=cfg["kp"] / cfg["laf"], Fz=float(np.abs(Fz[b]).mean()),
                         lag_mz=lag_mz, lag_ff=lag_ff, lag_s=lag_s))

    def corr(sel, key, lab):
        r = [x for x in rows if sel(x)]
        if len(r) < 3:
            return
        x = np.array([q["kpl"] for q in r]); y = np.array([q[key] for q in r])
        c = float(np.corrcoef(x, y)[0, 1])
        print(f"   corr(kp/LAF, {lab:12s}) = {c:+.3f}   over {len(r)} routes: {[q['g'] for q in r]}")

    print("\nCORRELATIONS")
    print(" all six V282-EPS routes (the study's own dose set):")
    for k, l in (("lag_mz", "lag M/Z"), ("lag_ff", "lag FF part"), ("lag_s", "lag S (loop)"),
                 ("Fz", "|F_z|")):
        corr(lambda x: x["g"].startswith("V282"), k, l)
    print(" the THREE V282 routes alone (same fork, same feedforward structure, kp/LAF identical):")
    for k, l in (("lag_mz", "lag M/Z"), ("Fz", "|F_z|")):
        corr(lambda x: x["g"] == "V282", k, l)
    print(" the THREE V282old routes alone (same fork family, kp/LAF 0.200-0.379):")
    for k, l in (("lag_mz", "lag M/Z"), ("lag_ff", "lag FF part"), ("lag_s", "lag S (loop)")):
        corr(lambda x: x["g"] == "V282old", k, l)
    print(" the nine torque routes:")
    for k, l in (("lag_mz", "lag M/Z"), ("lag_s", "lag S (loop)"), ("Fz", "|F_z|")):
        corr(lambda x: x["g"].startswith("T"), k, l)

    print("\nGROUP MEANS (the correlation's real content)")
    for g in ("V282old", "V282"):
        r = [x for x in rows if x["g"] == g]
        print(f"  {g:8s} n={len(r)}  kp/LAF {np.mean([q['kpl'] for q in r]):.3f}"
              f"  |F_z| {np.mean([q['Fz'] for q in r]):.3f}"
              f"  lag M/Z {np.mean([q['lag_mz'] for q in r]):+.3f} s"
              f"  lag FF {np.mean([q['lag_ff'] for q in r]):+.3f}"
              f"  lag S {np.mean([q['lag_s'] for q in r]):+.3f}")
    r = [x for x in rows if x["g"].startswith("T")]
    print(f"  {'TORQUE':8s} n={len(r)}  kp/LAF {np.mean([q['kpl'] for q in r]):.3f}"
          f"  |F_z| {np.mean([q['Fz'] for q in r]):.3f}"
          f"  lag M/Z {np.mean([q['lag_mz'] for q in r]):+.3f} s"
          f"  lag FF {np.mean([q['lag_ff'] for q in r]):+.3f}"
          f"  lag S {np.mean([q['lag_s'] for q in r]):+.3f}")

    print("\nWHAT RAISING SteerKP DOES TO THE SAME LAG, on the identified loop (algebra, same routes)")
    print(f"{'route':22s} " + " ".join(f"{'kp x'+str(k):>9s}" for k in (1, 2, 3))
          + "   group lag of S at 0.15-0.30 Hz, s  (negative = the loop LEADS)")
    for rt, v in res.items():
        if not v["cfg"]["g"] in ("T5", "T64", "T64B"):
            continue
        f1 = np.array(v["f"])
        f = np.arange(0.02, 3.0, 0.01)
        P = np.interp(f, f1, np.array(v["P_re"])) + 1j * np.interp(f, f1, np.array(v["P_im"]))
        out = []
        for kmul in (1.0, 2.0, 3.0):
            K = k_tot(f, v["cfg"], v["v"], v["k_m"], kp_mult=kmul)
            out.append(gdelay(f, 1.0 / (1.0 + K * P), *BAND))
        print(f"{rt:22s} " + " ".join(f"{x:9.3f}" for x in out) + "   <- the LOOP part only (S)")


if __name__ == "__main__":
    main()
