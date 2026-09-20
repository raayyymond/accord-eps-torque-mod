# -*- coding: utf-8 -*-
"""f6 -- the JOINT map over every reachable loop element, and the frontier.

Elements and where their bounds come from (all read from source, all EVIDENCE):
  SteerKP            [0.05, platform_kp*5.0 = 3.00]   starpilot_variables.py:458-459,811
  SteerLatAccel      [base*0.5 = 7.0, base*10]        starpilot_variables.py:446-447,812  (flown base 14)
  AccordTorqueKiHigh [0.0, 6.0]                       starpilot_variables.py:838
  AccordTorqueKi     [0.05, 1.0]                      starpilot_variables.py:826  (below 8 m/s; inert here)
  AccordErrorNotchQ  [0.0, 4.0]                       starpilot_variables.py:835, params_keys.h:401,
                                                      device_settings_layout.json (UI, step 0.1)
  AccordRateLoopGain [0.0, 0.003]                     starpilot_variables.py:834, params_keys.h:400
  AccordDobHz        [0.0, 3.0]                       starpilot_variables.py:840
The notch CENTRE and DEPTH are NOT toggles: the centre is get_honda_accord_mode_hz(v) from
HONDA_ACCORD_HOLD_K_V / HONDA_ACCORD_EPS_INERTIA, and the numerator has an exact zero there at
every Q.  Moving the centre or limiting the depth needs CODE.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
sys.path.insert(0, str(HERE.parents[1] / "loopshape" / "loopshape"))
import lp_lib as LP           # noqa: E402
from f5_frontier import Engine, FLOWN, C_of, SHAKE_F, SUB   # noqa: E402

RL_FLOWN = 0.001              # T64's flown AccordRateLoopGain (loopshape U8 config column)
RL_RC = 0.01                  # HONDA_ACCORD_RATE_LOOP_RC
RL_TAPER_V = 12.0             # HONDA_ACCORD_RATE_LOOP_TAPER_V


class Joint(Engine):
    def __init__(self):
        super().__init__()
        f, v = self.f, self.v
        # command -> steering rate, DIRECT (|L| ~ 0.1 in the shake band, so the bias is small there)
        self.Qsr = np.empty((len(v), len(f)), complex)
        for lo, hi in ((15.0, 22.0), (22.0, 99.0)):
            s = (v >= lo) & (v < hi)
            if not s.any():
                continue
            self.Qsr[s] = (np.mean(np.conj(self.U[s]) * self.SR[s], axis=0)
                           / np.maximum(np.mean(np.abs(self.U[s]) ** 2, axis=0), 1e-300))
        z = np.exp(-2j * np.pi * f * LP.DT)
        a = LP.DT / (RL_RC + LP.DT)
        self.Hlp = a / (1.0 - (1.0 - a) * z)                          # the rate-measurement filter
        self.rl_taper = np.minimum(1.0, RL_TAPER_V / np.maximum(v, 0.1))[:, None]
        self.dL_unit = -self.Hlp[None, :] * self.Qsr * self.rl_taper   # dL per unit AccordRateLoopGain

    def run2(self, kp, laf, ki, ki_hi, q, rl=RL_FLOWN):
        C1 = C_of(self.f, self.v, kp, laf, ki, ki_hi, q)
        K = C1 / self.C0
        L1 = self.L0 * K + (rl - RL_FLOWN) * self.dL_unit
        rho = (1.0 + self.L0) / (1.0 + L1)
        E1 = self.E + self.V * self.D * (rho - 1.0)
        U1 = self.UFF + self.UFB * K * rho
        m = float(np.sum(np.abs(E1[:, self.b]) ** 2)) / self.px
        bands = [float(np.sum(np.abs(E1[:, s]) ** 2)) / self.px for s in self.sb]
        shake_cmd = float(np.sqrt(np.sum(np.abs(U1[:, self.shk]) ** 2) / self.pu_shk))
        shake_L = float(np.mean(np.abs(L1[:, self.shj])))
        S1 = np.abs(1.0 / (1.0 + L1))
        ms_sel = (self.f >= 0.10) & (self.f <= 2.5)
        Ms = float(np.max(np.mean(S1[:, ms_sel], axis=0)))
        Smean = [float(np.mean(S1[:, s])) for s in self.sb]
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
        lowsp = {vv: (kp + LP.low_speed_factor(vv)) / laf / ((1.0 + LP.low_speed_factor(vv)) / 14.0)
                 for vv in (2.0, 4.0, 8.0, 12.0, 20.0, 28.0)}
        return dict(kp=kp, laf=laf, ki=ki, ki_hi=ki_hi, q=q, rl=rl, metric=m, bands=bands,
                    shake_cmd=shake_cmd, shake_L=shake_L, Ms=Ms, Smean=Smean, wc=wc, pm=pm,
                    kp_laf=kp / laf, lowsp=lowsp,
                    closure=(1.3512 - m) / (1.3512 - 0.442))


def load_sr():
    """SR spectra for the target routes, in the same window order as Engine."""
    cols = []
    for r in ("0000006c--68c6e94b17", "0000006d--05e83bb04f"):
        cols.append(np.load(OUT / f"f1_{r}.npz")["SR"])
    return np.concatenate(cols, axis=0)


if __name__ == "__main__":
    J = Joint()

    base = J.run2(FLOWN["kp"], FLOWN["laf"], FLOWN["ki"], FLOWN["ki_hi"], FLOWN["q"], RL_FLOWN)
    print(f"AS FLOWN positive control: metric {base['metric']:.4f} (1.3512) shake_cmd {base['shake_cmd']:.3f} "
          f"shake_L {base['shake_L']:.3f}")
    print()
    print("RATE LOOP as a lever, alone (AccordRateLoopGain, flown 0.0010, ceiling 0.0030):")
    print(f"{'rl':>8s} {'metric':>7s} {'clos%':>6s} {'shakeL':>7s} {'Ms':>5s}   dL at 1.95/2.54/3.03 Hz (complex mean)")
    for rl in (0.0, 0.0006, 0.0010, 0.0015, 0.0020, 0.0030):
        r = J.run2(FLOWN["kp"], FLOWN["laf"], FLOWN["ki"], FLOWN["ki_hi"], FLOWN["q"], rl)
        d = (rl - RL_FLOWN) * np.mean(J.dL_unit[:, J.shj], axis=0)
        print(f"{rl:8.4f} {r['metric']:7.3f} {r['closure']*100:6.1f} {r['shake_L']:7.3f} {r['Ms']:5.2f}   "
              + " ".join(f"{x.real:+.3f}{x.imag:+.3f}j" for x in d))
    print()

    KPS = [1.0, 1.5, 2.0, 2.5, 3.0]
    LAFS = [14.0, 12.0, 10.0, 8.0, 7.0]
    QS = [0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]
    KIH = [0.0, 1.0, 2.5]
    RLS = [0.0010, 0.0015]
    rows = []
    for kp, laf, q, kih, rl in itertools.product(KPS, LAFS, QS, KIH, RLS):
        rows.append(J.run2(kp, laf, FLOWN["ki"], kih, q, rl))
    json.dump(rows, open(OUT / "f6_grid.json", "w"))
    print(f"joint grid: {len(rows)} configs")
    print()
    print("THE FRONTIER: max closure at each shake-band |L| ceiling")
    print("  anchors -- as flown 0.085 | r72 0.19 flew clean | r71 0.46 LIMIT-CYCLED at 2.34 Hz")
    print(f"{'|L| ceil':>8s} {'metric':>7s} {'clos%':>6s} {'shakeCmd':>9s} {'|L|':>6s} {'Ms':>5s} "
          f"{'wc':>6s} {'PM':>4s} {'kp/LAF':>7s} | config")
    for ceil in (0.085, 0.10, 0.12, 0.15, 0.19, 0.25, 0.30, 0.46):
        ok = [r for r in rows if r["shake_L"] <= ceil]
        if not ok:
            continue
        b = min(ok, key=lambda r: r["metric"])
        print(f"{ceil:8.3f} {b['metric']:7.3f} {b['closure']*100:6.1f} {b['shake_cmd']:9.3f} {b['shake_L']:6.3f} "
              f"{b['Ms']:5.2f} {b['wc']:6.3f} {b['pm']:4.0f} {b['kp_laf']:7.4f} | "
              f"KP {b['kp']:.2f} LAF {b['laf']:.0f} Q {b['q']:.2f} KiHigh {b['ki_hi']:.1f} rl {b['rl']:.4f}")
    print()
    print("THE FRONTIER: max closure at each COMMAND-SHAKE ceiling (1.00 = as flown)")
    print(f"{'shake x':>8s} {'metric':>7s} {'clos%':>6s} {'|L|':>6s} {'Ms':>5s} {'wc':>6s} {'PM':>4s} {'kp/LAF':>7s} | config")
    for ceil in (0.95, 1.00, 1.05, 1.10, 1.20, 1.30, 1.50, 2.00):
        ok = [r for r in rows if r["shake_cmd"] <= ceil]
        if not ok:
            continue
        b = min(ok, key=lambda r: r["metric"])
        print(f"{ceil:8.2f} {b['metric']:7.3f} {b['closure']*100:6.1f} {b['shake_L']:6.3f} {b['Ms']:5.2f} "
              f"{b['wc']:6.3f} {b['pm']:4.0f} {b['kp_laf']:7.4f} | "
              f"KP {b['kp']:.2f} LAF {b['laf']:.0f} Q {b['q']:.2f} KiHigh {b['ki_hi']:.1f} rl {b['rl']:.4f}")
