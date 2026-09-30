# -*- coding: utf-8 -*-
"""h2_plant_gate.py -- gates H2a/H2b (CRITERIA-HARNESS.md).

H2a  PlantBatch (the harness's per-tick stepper) == v294_plant.simulate to <= 1e-9 on every tick, open loop (a random
     torque) and closed through the byte-exact lane (Lane294 inside simulate vs the harness Lane outside), on rigid,
     two-mass, delayed and noisy members at several speeds.
H2b  the kappa(angle) map reproduces the metric agent's measured d(angle)/d(integrated x/8): 1.16 +- 0.03 within 20 deg of
     centre and 0.965 +- 0.02 beyond 160 deg.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v295_harness as H  # noqa: E402
import v294_plant as VP  # noqa: E402


def run_harness(member, n, v100, th0, om0, T_open=None, cells=None, sp=None, m=None, c0=None, x_noise=0.0, seed=0):
    B = len(th0)
    P = H.PlantBatch([member] * B, th0, om0, c0=c0, x_noise=x_noise, seed=seed)
    L = H.Lane([cells] * B) if cells is not None else None
    if L is not None:
        L.set_state(s=np.zeros(B), o=np.zeros(B))
    out = {k: np.zeros((B, n)) for k in ("th", "om", "x", "T")}
    for i in range(n):
        fr = min(i // 10, v100.shape[1] - 1)
        if i % 10 == 0:
            P.set_speed(v100[:, fr])
        x = P.sense()
        if T_open is not None:
            T = T_open[:, i]
        else:
            T, _ = L.tick(-x, sp[:, fr].astype(np.int64), np.abs(sp[:, fr]).astype(np.int64) * 0 + idx_of_sp[:, fr],
                          m[:, fr].astype(np.int64))
            T = T.astype(float)
        P.step(T)
        out["th"][:, i] = P.wheel_angle()
        out["om"][:, i] = P.om
        out["x"][:, i] = x
        out["T"][:, i] = T
    return out


idx_of_sp = None


def main():
    global idx_of_sp
    fam = H.family()
    rng = np.random.default_rng(2)
    worst = 0.0
    print("H2 PLANT GATE")
    cases = [("nominal", fam["nominal"]), ("tau6", fam["tau6"]), ("mode20", fam["mode20"]), ("mode13", fam["mode13"]),
             ("light_b", fam["light_b"]), ("F_hi", fam["F_hi"])]
    for nm, mem in cases:
        for v in (3.0, 12.0, 26.0):
            n = 6000
            B = 3
            v100 = np.full((B, n // 10), v)
            th0 = rng.normal(0, 20, B)
            om0 = rng.normal(0, 30, B)
            T_open = np.cumsum(rng.normal(0, 25, (B, n)), axis=1)
            T_open = np.clip(T_open, -2400, 2400)
            ref = VP.simulate(mem, n, v100, th0, om0, T_open=T_open, c0=np.array([5.0, -12.0, 0.0]))
            got = run_harness(mem, n, v100, th0, om0, T_open=T_open, c0=np.array([5.0, -12.0, 0.0]))
            e = max(np.max(np.abs(ref["th"] - got["th"])), np.max(np.abs(ref["om"] - got["om"])),
                    np.max(np.abs(ref["x"] - got["x"])))
            worst = max(worst, e)
            print("  H2a open   %-8s v %4.1f: max |d| th/om/x = %.3g" % (nm, v, e))
    # closed loop through the lane: v294_plant.simulate(lane=Lane294) vs harness PlantBatch + Lane
    c = VP.v294_cells()
    base = H.Cells.v294()
    for nm, mem in (("nominal", fam["nominal"]), ("mode20", fam["mode20"]), ("tau6", fam["tau6"])):
        n = 8000
        B = 2
        v100 = np.full((B, n // 10), 10.0)
        idx = rng.integers(0, 200, (B, n // 10))
        sgn = rng.choice([-1, 1], (B, n // 10))
        lane294 = VP.Lane294(c, B)
        sp = sgn * lane294.LERP[idx]
        m = np.full((B, n // 10), 254)
        th0 = np.zeros(B)
        om0 = np.zeros(B)
        ref = VP.simulate(mem, n, v100, th0, om0, lane=lane294, sp=sp, m=m, x_noise=1.93, seed=5)
        idx_of_sp = idx
        got = run_harness(mem, n, v100, th0, om0, cells=base, sp=sp, m=m, x_noise=1.93, seed=5)
        e = max(np.max(np.abs(ref["th"] - got["th"])), np.max(np.abs(ref["om"] - got["om"])),
                np.max(np.abs(ref["T"] - got["T"])))
        worst = max(worst, e)
        print("  H2a closed %-8s (lane + x noise 1.93, seeded): max |d| th/om/T = %.3g   |T| max %.0f" % (nm, e, np.abs(got["T"]).max()))
    g2a = worst <= 1e-9
    print("H2a %s (worst %.3g)" % ("PASS" if g2a else "FAIL", worst))
    # H2b kappa
    th = np.linspace(0, 400, 40001)
    W = H.wheel_from_rack(th)
    dW = np.gradient(W, th)
    k_c = float(np.mean(dW[(W > 0.5) & (W < 20)]))
    k_l = float(np.mean(dW[W > 160]))
    back = np.max(np.abs(H.rack_from_wheel(W) - th))
    g2b = abs(k_c - 1.16) <= 0.03 and abs(k_l - 0.965) <= 0.02 and back < 1e-6
    print("  H2b kappa: dW/dtheta = %.3f on centre (want 1.16 +- 0.03), %.3f beyond 160 deg (want 0.965 +- 0.02); "
          "round trip %.1e deg" % (k_c, k_l, back))
    print("H2b %s" % ("PASS" if g2b else "FAIL"))
    print("H2", "PASS" if (g2a and g2b) else "FAIL")


if __name__ == "__main__":
    main()
