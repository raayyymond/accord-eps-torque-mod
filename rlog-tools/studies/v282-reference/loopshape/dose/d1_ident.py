# -*- coding: utf-8 -*-
"""D1 -- identify the plant P_la(jw) and the loop L(jw) on every flown route.

MEASUREMENT: P_la = S_ry / S_ru with the model's desired lateral accel as the instrument
             (r -> the loop only through u, and the road disturbance is independent of r).
             Positive control in d0_ivtest.py: recovers a known plant to ~1 % / ~1 deg and a known
             Ms / band-|S| to ~1 % on the real reference, with disturbance and sensor noise present.
ALGEBRA:     K_tot = -dU/dM is built from the fork's own published constants at the flown commit and
             each route's own initData values.  Its PID part is EXACT (d0 T4: p/error == SteerKP and
             p+i+f == -output*LAF to 4e-7).  Its rate-loop and observer parts are BELIEF-grade model,
             and are reported separately so the reader can see how much they matter.

Output: out/d1_<band>.json  and a printed table.
"""
import json
import numpy as np
import dlib as D

FS = 100.0
NPS = 1024


def segs_for(S, vlo, vhi, min_s=30.0):
    m = D.V.usable(S, vlo, vhi)
    out = []
    for a, b in D.V.runs(m, S["t"], min_s=min_s):
        if b - a < NPS:
            continue
        r = np.nan_to_num(S["model"][a:b])
        U = np.nan_to_num(S["p"][a:b]) + np.nan_to_num(S["i"][a:b]) + np.nan_to_num(S["f"][a:b])
        M = np.nan_to_num(S["la_act"][a:b])
        out.append((r, U, M))
    return out, m


def k_tot(f, cfg, v, k_m, kp_mult=1.0, ki_mult=1.0, rl_mult=1.0, dob_mult=1.0,
          parts=False, kp_abs=None, ki_abs=None):
    lsf = D.low_speed_factor(v)
    kp = kp_abs if kp_abs is not None else cfg["kp"] * kp_mult
    ki = ki_abs if ki_abs is not None else cfg["ki"] * ki_mult
    if cfg["ki_hi"] > 0:
        ki = float(np.interp(v, [8.0, 18.0], [ki, cfg["ki_hi"] * ki / max(cfg["ki"], 1e-9)]))
    f_notch = mode_hz(v) if cfg["nq"] > 0 else 0.0
    Cp = D.C_pid(f, kp, ki, lsf, cfg["nq"], f_notch)
    Cr = D.C_rate(f, cfg["laf"], cfg["rl"] * rl_mult, v, k_m)
    num, den = D.dob_terms(f, cfg["laf"], cfg["dob"] * dob_mult, v, k_m,
                           hold_level=(cfg["g"] in ("T64",)))
    K = (Cp + Cr + num) / den
    if parts:
        return K, Cp, Cr, num, den
    return K


def mode_hz(v):
    k = float(np.interp(v, D.HOLD_V_BP, D.HOLD_K_V))
    return float(np.sqrt(k / D.EPS_INERTIA) / (2 * np.pi))


def run(vlo, vhi, tag):
    res = {}
    print(f"\n=== band {vlo}-{vhi} m/s ===")
    print(f"{'route':22s} {'grp':8s} {'sec':>5s} {'n':>3s} {'v':>5s} {'k_m':>6s} "
          f"{'|P|.2Hz':>8s} {'|P|.8Hz':>8s} {'ph.8Hz':>7s} {'|P|2Hz':>7s} | "
          f"{'fc':>6s} {'PM':>6s} {'Ms':>5s} {'S.15-.3':>8s} {'S.3-.6':>7s} {'S.6-1.2':>8s}")
    for rt, cfg in D.ROUTES.items():
        S = D.load(rt)
        sg, m = segs_for(S, vlo, vhi)
        if not sg:
            print(f"{rt:22s} {cfg['g']:8s}  (no runs)")
            del S
            continue
        v = float(np.median(S["v"][m]))
        km = D.k_m_measured(S, m)
        R = D.iv_transfer(sg, nperseg=NPS)
        f = R["f"]
        P = D.smooth_c(R["P"].real) + 1j * D.smooth_c(R["P"].imag)
        valid = (D.smooth_c(R["coh_ry"]) > 0.30) & (D.smooth_c(R["coh_ru"]) > 0.30)
        K, Cp, Cr, num, den = k_tot(f, cfg, v, km, parts=True)
        L = K * P
        met = D.loop_metrics(f, L, valid)
        metP = D.loop_metrics(f, Cp * P, valid)          # PID-only loop, for contrast
        g = lambda ff: float(np.interp(ff, f, np.abs(P)))
        ph = lambda ff: float(np.degrees(np.interp(ff, f, np.unwrap(np.angle(P)))))
        print(f"{rt:22s} {cfg['g']:8s} {R['sec']:5.0f} {R['n']:3d} {v:5.1f} {km:6.4f} "
              f"{g(0.2):8.3f} {g(0.8):8.3f} {ph(0.8):7.1f} {g(2.0):7.3f} | "
              f"{met['fc']:6.2f} {met['pm']:6.1f} {met['Ms']:5.2f} "
              f"{met['S0.15_0.3']:8.3f} {met['S0.3_0.6']:7.3f} {met['S0.6_1.2']:8.3f}")
        res[rt] = dict(cfg=cfg, sec=R["sec"], n=R["n"], v=v, k_m=km,
                       f=f.tolist(), P_re=P.real.tolist(), P_im=P.imag.tolist(),
                       valid=valid.tolist(), coh_ry=R["coh_ry"].tolist(),
                       coh_ru=R["coh_ru"].tolist(), Srr=R["Srr"].tolist(),
                       met=met, met_pid_only=metP)
        del S
    with open(D.OUT / f"d1_{tag}.json", "w") as fh:
        json.dump(res, fh)
    return res


def contrast(res, tag):
    """The hypothesis under test: did deleting the EPS's own 1 kHz rate servo change the PLANT?"""
    print(f"\n--- plant P_la(jw) by EPS firmware ({tag}) : the hypothesis' own claim ---")
    print(f"{'group':10s} {'n':>2s} " + " ".join(f"{x:>8s}" for x in
          ("|P|0.2", "|P|0.4", "|P|0.8", "|P|1.2", "|P|2.0", "ph0.4", "ph0.8", "ph1.2", "ph2.0")))
    for grp in ("V282old", "V282", "T-ident", "T2", "T3", "T3r", "T4", "T5", "T64", "T64B"):
        rows = [v for v in res.values() if v["cfg"]["g"] == grp]
        if not rows:
            continue
        mags, phs = [], []
        for v in rows:
            f = np.array(v["f"])
            P = np.array(v["P_re"]) + 1j * np.array(v["P_im"])
            mags.append([float(np.interp(x, f, np.abs(P))) for x in (0.2, 0.4, 0.8, 1.2, 2.0)])
            phs.append([float(np.degrees(np.interp(x, f, np.unwrap(np.angle(P)))))
                        for x in (0.4, 0.8, 1.2, 2.0)])
        mm = np.median(np.array(mags), axis=0)
        pp = np.median(np.array(phs), axis=0)
        print(f"{grp:10s} {len(rows):2d} " + " ".join(f"{x:8.3f}" for x in mm)
              + " " + " ".join(f"{x:8.1f}" for x in pp))


if __name__ == "__main__":
    for lo, hi, tag in ((15.0, 99.0, "hi"), (8.0, 15.0, "mid")):
        r = run(lo, hi, tag)
        contrast(r, tag)
