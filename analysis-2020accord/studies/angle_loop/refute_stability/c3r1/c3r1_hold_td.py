# -*- coding: utf-8 -*-
"""c3r1_hold_td.py -- TIME-DOMAIN check of the operating-point finding on MY integer lane with the identified
SATURATING spring k*sat*tanh(theta/sat): ramp theta_sp to theta_op(v, a) over 1.5 s, hold; a 60 ms torque pulse (the
road / a hand brush) at t = 7 s; measure the entry overshoot, the ring after the pulse (frequency, log-decrement zeta,
number of cycles above 10 % of the first), and the settled residual.  Batched over members x a at one speed.
python c3r1_hold_td.py [fric 0|1] -> _scratch/.../hold_td_fric<k>.txt"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r1_model as M  # noqa: E402
import c3r1_intlane as IL  # noqa: E402
import c3r1_kop as K  # noqa: E402

D = M.designs()
MEMS = ("nominal", "J_hi", "ms_free", "J1.0", "b_lo*ms_free", "b_q*ms_free", "b_q*J1.0")
AS = (1.5, 2.0, 2.5)
FR = {"nom": (1.0, 1.0), "FA.83": (0.83, 1.0)}
FRIC_MS = {"ms_free": "msf"}


def fric_of(mem, v):
    if "ms_free" in mem:
        return float(np.interp(v, M.VC, [73.55, 14.44, 19.81, 11.61, 3.26])), 1.2
    Fc = float(np.interp(v, M.VC, [76.2, 13.49, 15.79, 7.86, 4.36]))
    Fs = float(np.interp(v, M.VC, [94.7, 18.9, 18.6, 10.0, 5.6]))
    return Fc, Fs / Fc


def ring_stats(e):
    """e: error after the pulse (ms ticks).  peaks of e (positive and negative alternately) -> f, zeta, n cycles > 10 %."""
    a = np.abs(e)
    pk = [i for i in range(1, len(e) - 1) if a[i] >= a[i - 1] and a[i] > a[i + 1] and a[i] > 1e-3]
    # keep alternating-sign extrema only
    ext = []
    for i in pk:
        if not ext or np.sign(e[i]) != np.sign(e[ext[-1]]):
            ext.append(i)
        elif a[i] > a[ext[-1]]:
            ext[-1] = i
    if len(ext) < 3:
        return math.nan, math.nan, len(ext)
    T = 2 * np.mean(np.diff(ext[:4])) * 1e-3
    r = a[ext[2]] / a[ext[0]]
    d = -math.log(max(r, 1e-9))
    n10 = sum(1 for i in ext if a[i] > 0.1 * a[ext[0]]) / 2
    return 1 / T, d / math.sqrt(4 * math.pi ** 2 + d * d), n10


def main(fric=0):
    out = []
    for dn in ("C3-P", "C3-F"):
        for v in (10.0, 12.0, 13.5, 15.0, 17.0):
            for fr in ("nom", "FA.83"):
                kap, jb = FR[fr]
                cases = [(m, a) for m in MEMS for a in AS]
                B = len(cases)
                pls = [M.member(m, v) for m, _ in cases]
                pl = M.Plant(np.array([p.J for p in pls]), np.array([p.b for p in pls]), np.array([p.k for p in pls]), 2.0)
                th_op = np.array([K.theta_op(v, a) for _, a in cases])
                sat = K.sat(v)
                if fric:
                    fc = np.array([fric_of(m, v)[0] for m, _ in cases])
                    rs = np.array([fric_of(m, v)[1] for m, _ in cases])
                else:
                    fc, rs = 0.0, 1.25
                n = 14000
                sp = lambda k: th_op * min(max((k - 200) / 1500.0, 0.0), 1.0)  # noqa: E731
                d_ext = lambda k: (np.full(B, 120.0) if 7000 <= k * 1 < 7060 else 0.0)  # noqa: E731
                r = IL.simulate(D[dn], pl, v, n, sp, B=B, kappa=kap, jb=jb, sat=sat, fric=fc, Fs_ratio=rs,
                                d_ext=lambda kk: d_ext(kk // 10 if False else kk))
                for b, (m, a) in enumerate(cases):
                    th = r["th"][b]
                    hold = th[6000:7000].mean()
                    ov = (th[1700:6000].max() - th_op[b]) / th_op[b] * 100
                    f, z, nc = ring_stats(th[7060:12000] - hold)
                    res = np.ptp(th[12000:14000])
                    out.append(f"{dn} v{v} {fr} {m:13s} a{a} th_op {th_op[b]:5.1f}: hold/target {hold / th_op[b]:.3f}, entry"
                               f" overshoot {ov:5.1f}%, after pulse ring {f:.2f} Hz zeta {z:.3f} cycles>10% {nc:.1f};"
                               f" settled pk-pk {res:.3f} deg")
                print("\n".join(out[-B:]), flush=True)
    (Path(M.OUT) / f"hold_td_fric{fric}.txt").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
