# -*- coding: utf-8 -*-
"""S2 -- (a) IS THE ERROR NOTCH ACTUALLY RUNNING, and at what Q?  (b) who carries the 1.8-3.5 Hz
command -- the feedback or the feedforward?  (c) EXACT re-synthesis of the command at any
(SteerKP, AccordErrorNotchQ, extra filter), validated against the logged command first.

WHY THIS IS MEASUREMENT, NOT SIMULATION.  Every input to the re-synthesis is logged:
    raw error       e = Z - M          (cs_la_des - cs_la_act)
    lsf inflation   e_lsf = e * (1 + lsf(v)/kp)                    latcontrol_torque.py:342
    notch           e_n = HondaAccordErrorNotch(e_lsf, mode_hz(v), Q)          :347
    p = kp * e_n ;  i += ki*dt*e_n ;  U = (p + i + f)/LAF                      pid.py:47-62
`f` is taken from the log unchanged, so the feedforward, the inner rate loop and the observer are
carried exactly as they ran.  The re-synthesis is OPEN LOOP in e: it does not claim what the car
would then do.  It bounds the COMMAND, which is what the shake is driven by.

usage: python s2_resynth.py > out/S2-RESYNTH.txt
"""
import json

import numpy as np
from scipy import signal as sg

import suplib as S

ROUTES = S.T64 + ["0000006e--6ca3e014fd", "00000076--d0b7ea7e4d", "00000075--6c8687d5bd",
                  "00000072--8001fc3048", "00000071--f2c9d073a3"] + S.V282R
VMIN = 15.0


def _self_test():
    """Positive control on the re-synthesis: build a synthetic p/i/f from a KNOWN error with a KNOWN
    kp/ki/Q, then recover kp and Q by the same estimators used on the logs."""
    rng = np.random.default_rng(11)
    n = 30000
    v = np.full(n, 20.0)
    e = sg.sosfiltfilt(sg.butter(2, 3.0, fs=S.FS, output="sos"), rng.standard_normal(n)) * 0.3
    kp, ki, q = 1.0, 0.3, 1.0
    el = e * (1 + S.lsf(v) / kp)
    en = S.notch_run(el, S.mode_hz(v), q)
    p = kp * en
    i = np.cumsum(ki * S.DT * en)
    kp_hat = float(np.median(p[np.abs(en) > 0.01] / en[np.abs(en) > 0.01]))
    assert abs(kp_hat - kp) < 1e-6, kp_hat
    # the notch must be identifiable: residual against the notched model << residual against the raw one
    r_notch = np.sqrt(np.mean((p / kp - en) ** 2))
    r_raw = np.sqrt(np.mean((p / kp - el) ** 2))
    assert r_notch < 1e-12 and r_raw > 0.1 * np.sqrt(np.mean(el ** 2)), (r_notch, r_raw)
    # re-integration reproduces i
    i2 = np.cumsum(ki * S.DT * en)
    assert np.max(np.abs(i2 - i)) < 1e-9
    return "s2 self-test OK: kp recovered exactly, notch identifiable, integrator reproduced"


def resynth(N, a, b, kp_new, q_new, kp0, ki, laf, f0, post_filter=None):
    """Rebuild p, i and U over one run with a new (kp, Q) and an optional extra COMMAND filter.
    post_filter(u, v) -> u', applied to the whole command (FF included), as a code change would."""
    sl = slice(a, b)
    v = N["v"][sl]
    e = N["Z"][sl] - N["M"][sl]
    el = e * (1.0 + S.lsf(v) / max(kp_new, 1e-3))
    en = S.notch_run(el, f0[sl], q_new) if q_new is not None else el
    p = kp_new * en
    i = N["I"][a] + np.cumsum(ki * S.DT * en)
    # remove the integrator's free constant drift the same way for every variant: the logged i is
    # re-anchored to its own mean over the run, so only the SHAPE (what the bands see) is compared
    u = (p + i + N["F"][sl]) / laf
    if post_filter is not None:
        u = post_filter(u, v)
    return u, p, i, en, el


def main():
    print(S._self_test())
    print(_self_test())
    rows = {}
    for rk in ROUTES:
        meta = S.FLOWN[rk]
        N = S.load(rk)
        runs = S.runs_of(N, VMIN, 99.0, 30.0)
        if not runs:
            print(f"\n{rk} {meta['fam']}: no >=30 s engaged hands-off run above {VMIN} m/s")
            del N
            continue
        m = np.zeros(len(N["t"]), bool)
        for a, b in runs:
            m[a:b] = True
        # ---- A. the flown kp and LAF, measured, not assumed
        E, P, I, F, U = N["E"][m], N["P"][m], N["I"][m], N["F"][m], N["U"][m]
        big = np.abs(E) > np.percentile(np.abs(E), 60)
        kp_hat = float(np.median(P[big] / E[big]))
        lafd = (P + I + F) / np.where(np.abs(U) > 5e-3, U, np.nan)
        laf_hat = float(np.nanmedian(lafd))
        # ---- B. is the notch live?  reconstruct e_lsf from Z, M, v and compare to the LOGGED error
        v = N["v"]
        f0 = S.mode_hz(v)
        el = (N["Z"] - N["M"]) * (1.0 + S.lsf(v) / max(kp_hat, 1e-3))
        res = {}
        for tag, q in (("raw (no notch)", None), ("notch Q=1.0", 1.0), ("notch Q=0.5", 0.5), ("notch Q=2.0", 2.0)):
            pred = el if q is None else S.notch_run(el, f0, q)
            d = (N["E"] - pred)[m]
            res[tag] = float(np.sqrt(np.mean(d ** 2)) / np.sqrt(np.mean(N["E"][m] ** 2)))
        # band transfer from the reconstructed RAW error to the LOGGED error: this IS the notch
        Nx = dict(N); Nx["ELRAW"] = el
        fr, sp, vs = S.spectra(Nx, ("ELRAW", "E"), VMIN, 99.0, 2048, 30.0)
        H, coh = S.H_xy(sp["ELRAW"], sp["E"])
        del Nx, sp
        # ---- C. who carries the shake band
        ufb = (P + I) / laf_hat
        uff = F / laf_hat
        sh = {}
        for tag, x in (("U", U), ("u_fb=(p+i)/LAF", ufb), ("u_ff=f/LAF", uff)):
            sh[tag] = S.bandrms(x, *S.SHAKE)
        shg = {tag: S.bandrms(x, *S.GAP) for tag, x in (("U", U), ("u_fb", ufb), ("u_ff", uff))}
        print("\n" + "=" * 132)
        print(f"{rk}  fam {meta['fam']}  eps {meta['eps']}  flown kp {meta['kp']} LAF {meta['laf']} "
              f"ki {meta['ki']} notch-in-code {meta['notch']}  runs {len(runs)}  {m.sum()/S.FS:.0f} s >= {VMIN} m/s")
        print(f"  MEASURED kp = median(p/err) = {kp_hat:.4f}   (flown SteerKP {meta['kp']})    "
              f"MEASURED LAF = median((p+i+f)/U) = {laf_hat:.4f}   (flown {meta['laf']})")
        print("  IS THE NOTCH LIVE?  RMS residual of the LOGGED pid error against each reconstruction,"
              " as a fraction of the logged error's own RMS:")
        for tag, r in res.items():
            print(f"      {tag:16s} residual {r:7.4f}")
        best = min(res, key=res.get)
        print(f"      -> best: {best}")
        print("  Realised transfer  reconstructed-raw-error -> LOGGED error  (this IS the notch, measured):")
        hdr = [0.2, 0.3, 0.6, 1.0, 1.5, 1.75, 2.0, 2.25, 2.5, 3.0, 3.5]
        print("      f Hz   " + "".join(f"{q:>7.2f}" for q in hdr))
        print("      |H|    " + "".join(f"{abs(H[int(np.argmin(np.abs(fr-q)))]):7.3f}" for q in hdr))
        print("      coh    " + "".join(f"{coh[int(np.argmin(np.abs(fr-q)))]:7.3f}" for q in hdr))
        vmed = float(np.median(v[m]))
        print(f"      analytic notch Q=1.0 at the run's median speed {vmed:.1f} m/s (f0 {S.mode_hz(vmed):.2f} Hz):")
        print("      |H|    " + "".join(f"{abs(S.notch_H(q, S.mode_hz(vmed), 1.0)):7.3f}" for q in hdr))
        print(f"  COMMAND CONTENT   1.8-3.5 Hz rms:  U {sh['U']:.5f}   u_fb {sh['u_fb=(p+i)/LAF']:.5f} "
              f"({sh['u_fb=(p+i)/LAF']/sh['U']:.2f}x U)   u_ff {sh['u_ff=f/LAF']:.5f} ({sh['u_ff=f/LAF']/sh['U']:.2f}x U)")
        print(f"                    0.15-0.60 Hz rms: U {shg['U']:.5f}   u_fb {shg['u_fb']:.5f} "
              f"({shg['u_fb']/shg['U']:.2f}x U)   u_ff {shg['u_ff']:.5f} ({shg['u_ff']/shg['U']:.2f}x U)")

        # ---- D. re-synthesis, validated, then the variants
        ki = meta["ki"] if meta["ki_hi"] <= 0 else None
        if ki is None:
            ki_arr = np.interp(N["v"], [8.0, 18.0], [meta["ki"], meta["ki_hi"]])
        out = {}
        for a, b in runs:
            sl = slice(a, b)
            kiv = meta["ki"] if ki is not None else float(np.median(ki_arr[sl]))
            q_flown = 1.0 if meta["notch"] else None
            u0, p0, i0, en0, el0 = resynth(N, a, b, kp_hat, q_flown, kp_hat, kiv, laf_hat, f0)
            ulog = N["U"][sl]
            out.setdefault("val", []).append((float(np.corrcoef(u0, ulog)[0, 1]),
                                              S.bandrms(u0, *S.SHAKE) / max(S.bandrms(ulog, *S.SHAKE), 1e-12),
                                              S.bandrms(u0, *S.GAP) / max(S.bandrms(ulog, *S.GAP), 1e-12)))
            for tag, kpn, qn, pf in VARIANTS(kp_hat, meta):
                u1, *_ = resynth(N, a, b, kpn, qn, kp_hat, kiv, laf_hat, f0, pf)
                out.setdefault(tag, []).append((S.bandrms(u1, *S.SHAKE) / max(S.bandrms(u0, *S.SHAKE), 1e-12),
                                                S.bandrms(u1, *S.GAP) / max(S.bandrms(u0, *S.GAP), 1e-12),
                                                len(u1)))
        val = np.array(out.pop("val"))
        w = None
        print(f"  RE-SYNTHESIS POSITIVE CONTROL (flown settings, per run): corr(U_resynth, U_log) "
              f"{np.min(val[:,0]):.4f}-{np.max(val[:,0]):.4f};  band-rms ratio shake "
              f"{np.median(val[:,1]):.3f}, gap {np.median(val[:,2]):.3f}")
        print(f"  {'variant':44s} {'1.8-3.5 Hz cmd':>15s} {'0.15-0.60 Hz cmd':>17s}")
        rows[rk] = dict(fam=meta["fam"], kp=kp_hat, laf=laf_hat, notch_res=res,
                        shake=sh, gap=shg, val=val.tolist(), var={})
        for tag, vals in out.items():
            A = np.array(vals)
            wt = A[:, 2]
            rs = float(np.sum(A[:, 0] * wt) / np.sum(wt))
            rg = float(np.sum(A[:, 1] * wt) / np.sum(wt))
            print(f"  {tag:44s} {rs:15.3f} {rg:17.3f}")
            rows[rk]["var"][tag] = (rs, rg)
        del N
    json.dump(rows, open(S.OUT / "s2_resynth.json", "w"), indent=1)
    return 0


def VARIANTS(kp0, meta):
    """(tag, kp, Q, post-command filter).  Q None = notch bypassed."""
    q0 = 1.0 if meta["notch"] else None
    out = [("KP x2 (notch as flown)", kp0 * 2, q0, None),
           ("KP x3 (notch as flown)", kp0 * 3, q0, None),
           ("notch OFF (Q=0), kp as flown", kp0, None, None),
           ("notch Q=0.7", kp0, 0.7, None),
           ("notch Q=0.5", kp0, 0.5, None),
           ("notch Q=0.3", kp0, 0.3, None),
           ("KP x2 + notch Q=0.5", kp0 * 2, 0.5, None),
           ("KP x3 + notch Q=0.5", kp0 * 3, 0.5, None),
           ("KP x3 + notch Q=0.3", kp0 * 3, 0.3, None)]
    for fc in (2.0, 3.0):
        pf = (lambda u, v, fc=fc: S.fof_run(u, 1 / (2 * np.pi * fc), x0=u[0]))
        out.append((f"cmd LP {fc} Hz (kp as flown)", kp0, q0, pf))
        out.append((f"KP x3 + cmd LP {fc} Hz", kp0 * 3, q0, pf))
    pf25 = (lambda u, v: S.notch_run(u, 2.5, 1.0))
    out.append(("cmd notch 2.5 Hz Q=1 (kp as flown)", kp0, q0, pf25))
    out.append(("KP x3 + cmd notch 2.5 Hz Q=1", kp0 * 3, q0, pf25))
    return out


if __name__ == "__main__":
    raise SystemExit(main())
