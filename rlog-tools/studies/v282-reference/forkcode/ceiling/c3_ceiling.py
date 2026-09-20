# -*- coding: utf-8 -*-
"""c3 -- THE FRONTIER WITH THE TOGGLE CEILINGS LIFTED.

Extends shapedgain/frontier's Engine.  Everything the engine measures is unchanged (E, D, X, U,
UFB, UFF, V, P all from the logs); what I add is a GENERAL analytic C that covers the fork-code
candidates, and a COST AXIS that survives its own calibration (c2).

C(f, v) -- built to mirror latcontrol_torque.py exactly:
    lsf   = (interp(v, LOW_SPEED_X, LOW_SPEED_Y) / max(v, MIN_SPEED))^2         (torque.py:339)
    P-path  (kp + lsf)                                 <- kp cancels in error*(1+lsf/kp) (:342)
    I-path  (ki(v)*dt/(1-z)) * (1 + lsf/kp)            <- kp does NOT cancel  (the coupling)
              decouple_i=True replaces kp by KP_REF here: that is the two-line repair.
    D-path  kd * (1-z)/dt * a_d/(1-(1-a_d) z)          <- the k_d slot, HARD ZERO today
    notch   HondaAccordErrorNotch(f0(v), Q)            Q may be a SCHEDULE Q(v)
    lp      optional first/second-order roll-off on the error (a new term)
    C = -(P + I + D) * notch * lp / LAF

COST AXES
  * shake_cmd   -- ratio of re-synthesised 1.8-3.5 Hz COMMAND rms to as-flown.  c2 calibrated the
                   brief's common units against the LOGGED commands: rev 6.4 = 32.4 and the r71
                   limit cycle = 176.0 reproduce to 0.3 % as an RMS ratio (29.35x in power).
  * Kshake      -- mean |C_new / C_flown| over 1.8-3.5 Hz.  EXACT and PLANT-FREE: the plant cancels,
                   so this number carries none of the shake-band identification scatter.
  * K234_vs_r71 -- |C_new| at 2.34 Hz as a fraction of what r71 ran there.  r71 and rev 6.4 are the
                   same car and the same EPS build, so the C ratio is the whole story up to plant
                   scatter.  r71 LIMIT-CYCLED at exactly 2.34 Hz, so 1.0 here is the known-bad point.
  * shake_L     -- the inherited axis.  REPORTED BUT NOT TRUSTED: c2 shows it puts r72 (flew clean)
                   ABOVE r71 (limit-cycled) on both plant estimators.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
FRONT = STUDY / "shapedgain" / "frontier"
sys.path.insert(0, str(FRONT))
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import lp_lib as LP                                   # noqa: E402
from f5_frontier import Engine, FLOWN                 # noqa: E402

np.seterr(divide="ignore", invalid="ignore")
OUTD = HERE / "out"
OUTD.mkdir(exist_ok=True)
KP_REF = 0.6          # the platform Kp for the Accord (SteerKP default); the I path's own reference
SHAKE = (1.8, 3.5)
COMMON = 32.4         # rev 6.4's shake in the brief's common units
R71_COMMON = 176.0    # the limit cycle
R72_COMMON = 19.4


def lp1(f, hz):
    """First-order discrete low-pass exactly as the fork's FirstOrderFilter runs it."""
    a = LP.DT / (1.0 / (2.0 * np.pi * hz) + LP.DT)
    z = np.exp(-2j * np.pi * np.asarray(f) * LP.DT)
    return a / (1.0 - (1.0 - a) * z)


def C_gen(f, v, kp, laf, ki, ki_hi, q, decouple_i=False, kp_ref=KP_REF,
          lp_hz=None, lp_ord=1, kd=0.0, kd_lp_hz=4.0, notch_on=True):
    """(nwin, nf) feedback transfer.  q may be a scalar or an (nwin,) array (a speed schedule)."""
    v = np.atleast_1d(v)
    lsf = LP.low_speed_factor(v)[:, None]
    kie = LP.ki_of(v, ki, ki_hi)[:, None]
    z = np.exp(-2j * np.pi * f[None, :] * LP.DT)
    Ipath = kie * LP.DT / (1.0 - z)
    if decouple_i:
        num = (kp + lsf) + Ipath * (1.0 + lsf / max(kp_ref, 1e-3))
    else:
        num = (kp + Ipath) * (1.0 + lsf / max(kp, 1e-3))
    if kd:
        num = num + kd * (1.0 - z) / LP.DT * lp1(f, kd_lp_hz)[None, :]
    C = -num / laf
    if notch_on:
        qq = np.atleast_1d(np.asarray(q, float))
        qq = np.full(len(v), float(qq[0])) if qq.size == 1 else qq
        f0 = LP.mode_hz(v)
        k = np.tan(np.pi * np.minimum(f0, 0.45 / LP.DT) * LP.DT)[:, None]
        Q = qq[:, None]
        act = (Q > 0)
        norm = 1.0 / (1.0 + k / np.where(act, Q, 1.0) + k * k)
        b0 = (1.0 + k * k) * norm
        b1 = 2.0 * (k * k - 1.0) * norm
        a2 = (1.0 - k / np.where(act, Q, 1.0) + k * k) * norm
        N = (b0 + b1 * z + b0 * z ** 2) / (1.0 + b1 * z + a2 * z ** 2)
        C = C * np.where(act, N, 1.0)
    if lp_hz:
        C = C * lp1(f, lp_hz)[None, :] ** lp_ord
    return C


class Ceiling(Engine):
    def __init__(self):
        super().__init__()
        f = self.f
        self.shb = (f >= SHAKE[0]) & (f <= SHAKE[1])
        self.j234 = int(np.argmin(np.abs(f - 2.34)))
        # r71's feedback transfer at ITS speed, for the plant-free limit-cycle comparison
        p71 = LP.FLOWN["00000071--f2c9d073a3"]
        v71 = np.array([27.8])
        self.C71 = C_gen(f, v71, p71["kp"], p71["laf"], p71["ki"], p71["ki_hi"], 0.0, notch_on=False)[0]
        # the flown C, evaluated at r71's speed too, so the two are compared like for like
        self.C0_at71 = C_gen(f, v71, FLOWN["kp"], FLOWN["laf"], FLOWN["ki"], FLOWN["ki_hi"], 1.0)[0]
        # command re-synthesis positive control
        self.U0rms = float(np.sqrt(np.sum(np.abs(self.U[:, self.shk]) ** 2)))

    def score(self, **kw):
        q = kw.pop("q", 1.0)
        kp, laf = kw.pop("kp"), kw.pop("laf")
        ki, kih = kw.pop("ki", FLOWN["ki"]), kw.pop("ki_hi", FLOWN["ki_hi"])
        C1 = C_gen(self.f, self.v, kp, laf, ki, kih, q, **kw)
        K = C1 / self.C0
        L1 = self.L0 * K
        rho = (1.0 + self.L0) / (1.0 + L1)
        E1 = self.E + self.V * self.D * (rho - 1.0)
        U1 = self.UFF + self.UFB * K * rho
        m = float(np.sum(np.abs(E1[:, self.b]) ** 2)) / self.px
        shake_cmd = float(np.sqrt(np.sum(np.abs(U1[:, self.shk]) ** 2) / self.pu_shk))
        Kshake = float(np.mean(np.abs(K[:, self.shb])))
        # plant-free comparison against the limit cycle, at r71's own speed
        C1_at71 = C_gen(self.f, np.array([27.8]), kp, laf, ki, kih,
                        (q if np.isscalar(q) else float(np.atleast_1d(q)[-1])), **kw)[0]
        k234 = float(np.abs(C1_at71[self.j234]) / np.abs(self.C71[self.j234]))
        S1 = np.abs(1.0 / (1.0 + L1))
        ms_sel = (self.f >= 0.10) & (self.f <= 2.5)
        Ms = float(np.max(np.mean(S1[:, ms_sel], axis=0)))
        Lm = np.mean(L1, axis=0)
        sel = (self.f >= 0.10) & (self.f <= 3.5)
        ff, LL = self.f[sel], Lm[sel]
        mag = np.abs(LL)
        wc = pm = np.nan
        x = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
        if len(x):
            k0 = x[0]
            w = np.log(mag[k0]) / (np.log(mag[k0]) - np.log(mag[k0 + 1]))
            wc = float(ff[k0] + w * (ff[k0 + 1] - ff[k0]))
            ph = np.unwrap(np.angle(LL))
            pm = float(180.0 + np.degrees(np.angle(np.exp(1j * np.interp(wc, ff, ph)))))
        # command growth, for the LAF clamp: rms and peak of the reconstructed AC command
        Ua, Ub = U1.copy(), self.U.copy()
        Ua[:, 0] = Ub[:, 0] = 0.0          # the PI numerator is singular at z=1; DC carries no info
        u1t = np.fft.irfft(np.nan_to_num(Ua), n=1024, axis=1)
        u0t = np.fft.irfft(Ub, n=1024, axis=1)
        return dict(metric=m, closure=(1.3512 - m) / (1.3512 - 0.442),
                    bands=[float(np.sum(np.abs(E1[:, s]) ** 2)) / self.px for s in self.sb],
                    shake_cmd=shake_cmd, shake_common=shake_cmd * COMMON,
                    Kshake=Kshake, k234_vs_r71=k234,
                    shake_L=float(np.mean(np.abs(L1[:, self.shj]))),
                    Ms=Ms, wc=wc, pm=pm, maxL=float(np.max(np.abs(Lm))),
                    u_rms=float(np.std(u1t) / np.std(u0t)),
                    u_pk=float(np.percentile(np.abs(u1t), 99.9) / np.percentile(np.abs(u0t), 99.9)))


def fmt(tag, r, extra=""):
    wc = f"{r['wc']:.3f}" if not np.isnan(r["wc"]) else " <1  "
    pm = f"{r['pm']:4.0f}" if not np.isnan(r["pm"]) else "   -"
    return (f"{tag:38s} {r['metric']:6.3f} {r['closure']*100:6.1f} {r['shake_cmd']:6.3f} "
            f"{r['shake_common']:7.1f} {r['Kshake']:6.2f} {r['k234_vs_r71']:7.3f} {r['Ms']:5.2f} "
            f"{wc:>6s} {pm} {r['u_rms']:5.2f} {extra}")


HDR = (f"{'config':38s} {'J':>6s} {'clos%':>6s} {'shkx':>6s} {'common':>7s} {'Kshk':>6s} "
       f"{'/r71':>7s} {'Ms':>5s} {'wc':>6s} {'PM':>4s} {'urms':>5s}")

if __name__ == "__main__":
    E = Ceiling()
    print("POSITIVE CONTROLS")
    b = E.score(kp=1.0, laf=14.0, q=1.0)
    print(fmt("as flown (J 1.3512, shk 1.000)", b))
    a = E.score(kp=3.0, laf=14.0, q=0.60)
    print(fmt("ARM-KP2 (brief J 1.058, x1.148)", a))
    print(f"   plant-free check: rev 6.4's own |C| at 2.34 Hz is {E.score(kp=1.0,laf=14.0,q=1.0)['k234_vs_r71']:.3f} "
          f"of r71's -> the flown build already sits {1/b['k234_vs_r71']:.2f}x BELOW the limit-cycle gain there")
    print()

    print("=" * 140)
    print("1. SteerKP PAST THE 3.00 TOGGLE CEILING, notch Q co-optimised (SteerLatAccel held at 14)")
    print("   Q swept 0(off) .. 4.0; for each KP the row is the Q that MINIMISES J, and the Q that")
    print("   minimises J subject to the command shake staying at or below as-flown (x1.00).")
    QS = [0.0, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7, 0.8, 0.9, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]
    KPS = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 24.0]
    print(HDR + "   Qbest")
    grid = {}
    for kp in KPS:
        rows = [(q, E.score(kp=kp, laf=14.0, q=q)) for q in QS]
        grid[kp] = rows
        bq, br = min(rows, key=lambda t: t[1]["metric"])
        flag = "  <-- toggle ceiling" if kp == 3.0 else ""
        print(fmt(f"KP {kp:5.1f}  best-J", br, f"Q {bq:.2f}{flag}"))
    print()
    print("   the same sweep with the command shake held AT OR BELOW AS FLOWN (x1.00) -- free closure")
    print(HDR + "   Qbest")
    for kp in KPS:
        ok = [(q, r) for q, r in grid[kp] if r["shake_cmd"] <= 1.0]
        if not ok:
            print(f"KP {kp:5.1f}  (no Q holds shake <= 1.00)")
            continue
        bq, br = min(ok, key=lambda t: t[1]["metric"])
        print(fmt(f"KP {kp:5.1f}  shake<=1.00", br, f"Q {bq:.2f}"))
    print()
    print("   FULL Q RESPONSE at three KP values (where the notch spends and where it pays)")
    for kp in (3.0, 6.0, 12.0):
        print(f"   --- SteerKP {kp}")
        print("   " + HDR)
        for q, r in grid[kp]:
            if q in (0.0, 0.25, 0.4, 0.6, 0.8, 1.0, 1.5, 4.0):
                print("   " + fmt(f"Q {q:.2f}", r))
    json.dump({str(k): [(q, {kk: vv for kk, vv in r.items()}) for q, r in v] for k, v in grid.items()},
              open(OUTD / "c3_kpsweep.json", "w"))
    print()
    print("=" * 140)
    print("2. THE FRONTIER on the CALIBRATED cost axis (command shake, common units).")
    print("   anchors: r72 flew clean 19.4 | rev 6.4 as flown 32.4 | r71 LIMIT-CYCLED 176.0")
    allr = []
    for kp in KPS:
        for q, r in grid[kp]:
            r2 = dict(r); r2["kp"] = kp; r2["q"] = q; r2["laf"] = 14.0
            allr.append(r2)
    print(HDR + "   config")
    for ceil in (32.4, 36.0, 40.0, 45.0, 50.0, 60.0, 80.0, 120.0, 176.0):
        ok = [r for r in allr if r["shake_common"] <= ceil]
        if not ok:
            continue
        bb = min(ok, key=lambda r: r["metric"])
        print(fmt(f"shake <= {ceil:6.1f} common", bb, f"KP {bb['kp']:.1f} Q {bb['q']:.2f}"))
