# -*- coding: utf-8 -*-
"""s5_oncentre.py -- p-gain lens: ON-CENTRE HUNTING with friction, the fork UNCHANGED (r1 port, bit-identical to the
real code per the harness's H3b), the byte-exact lane, the plant family with Karnopp stick-slip.

A synthetic straight road: desired curvature 0, constant speed, a road-crown torque d0 on the plant (+ a 0.05 Hz
+-10 T drift), the measured x noise (1.93 counts), the 0x14A 0.1 deg angle quantiser, pipe 22 ms, the Honda limiter.
60 s per case after a 10 s settle.  Question: does a higher firmware slope (flat Kp g, or a small-idx boost) make the
fork + friction loop HUNT on centre (a sustained oscillation / stick-slip cycle) where V294 does not?
Metrics per case: wheel-rate rms 0.1-1 / 1-3 / 3-8 Hz, angle rms about its mean, the strongest rate line 0.1-5 Hz
(prominence dB over a log-log shoulder), stuck fraction (om == 0), command rms, stick-slip breakaways per minute.
The harness's mode-B engine is reproduced here with synthetic exogenous inputs (same classes, same order).
ANALYSIS ONLY."""
import json
import os
import sys
import time

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pg_lib as G  # noqa: E402
H = G.H
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def run(cells_list, members, speeds, d0s, secs=70.0, settle=10.0, pipe_ms=22, x_noise=1.93, seed=3):
    d = H.route()
    tg = d["toggles"]
    combos = [(ci, mi, vi, di) for ci in range(len(cells_list)) for mi in range(len(members))
              for vi in range(len(speeds)) for di in range(len(d0s))]
    B = len(combos)
    lane = Lane = H.Lane([cells_list[c] for c, _, _, _ in combos])
    plant = H.PlantBatch([members[m] for _, m, _, _ in combos], np.zeros(B), np.zeros(B), x_noise=x_noise, seed=seed)
    V = np.array([speeds[v] for _, _, v, _ in combos], float)
    D0 = np.array([d0s[k] for _, _, _, k in combos], float)
    fork = H.ForkPort(B, tg)
    laf_off = float(np.median(d["ltp_off_f"][d["eng"]]))
    NF = int(secs * 100)
    qcmd = np.zeros((B, NF + 4))
    last_tq = np.zeros(B)
    steer_lim = np.zeros(B, bool)
    wire_eff = np.zeros(B)
    idx, sp, m = lane.demand(wire_eff)
    rec = {k: np.zeros((B, NF)) for k in ("rate", "ang", "cmd", "om", "T")}
    t = np.arange(NF) * 0.01
    drift = 10.0 * np.sin(2 * np.pi * 0.05 * t)
    for n in range(NF * 10):
        k = n // 10
        if n % 10 == 0:
            plant.set_speed(V)
            ang = np.round(plant.wheel_angle() / 0.1) * 0.1
            r = fork.step(np.ones(B, bool), V, ang, np.zeros(B, bool), 0.0, 0.0, np.zeros(B), 0.426, laf_off, steer_lim)
            lim, can = H.honda_limiter(r["torque"], last_tq)
            steer_lim = np.abs(r["torque"] - lim) > 1e-2
            last_tq = lim
            qcmd[:, k] = can
            rec["ang"][:, k] = ang
            rec["om"][:, k] = plant.om
        if (n - pipe_ms) >= 0 and (n - pipe_ms) % 10 == 0:
            wire_eff = qcmd[:, (n - pipe_ms) // 10]
            idx, sp, m = lane.demand(wire_eff)
        x = plant.sense()
        T, _ = lane.tick(-x, sp, idx, m)
        plant.step(T.astype(float), D0 + drift[k])
        if n % 10 == 9:
            rec["rate"][:, k] = x / 8.0
            rec["cmd"][:, k] = wire_eff
            rec["T"][:, k] = T
    s0 = int(settle * 100)
    out = []
    for j, (ci, mi, vi, di) in enumerate(combos):
        rt = rec["rate"][j, s0:]
        a = rec["ang"][j, s0:]
        res = dict(cells=cells_list[ci].name, plant=members[mi].name, v=speeds[vi], d0=d0s[di])
        for key, (lo, hi) in (("r_01_1", (0.1, 1.0)), ("r_1_3", (1.0, 3.0)), ("r_3_8", (3.0, 8.0))):
            b, aa = signal.butter(2, [lo / 50, hi / 50], btype="band")
            res[key] = float(np.sqrt(np.mean(signal.filtfilt(b, aa, rt) ** 2)))
        res["ang_rms"] = float(np.std(a))
        f, P = signal.welch(rt - rt.mean(), fs=100.0, nperseg=2048)
        mm = (f >= 0.1) & (f <= 5.0)
        kk = np.flatnonzero(mm)[int(np.argmax(P[mm]))]
        sh = (f >= 0.05) & (f <= 8.0) & (np.abs(f - f[kk]) > 0.3)
        cf = np.polyfit(np.log(f[sh]), np.log(P[sh] + 1e-30), 1)
        res["line_f"] = float(f[kk])
        res["line_dB"] = float(10 * np.log10(P[kk] / np.exp(np.polyval(cf, np.log(f[kk])))))
        om = rec["om"][j, s0:]
        stuck = om == 0.0
        res["stuck_frac"] = float(np.mean(stuck))
        res["breakaways_per_min"] = float(np.sum(stuck[:-1] & ~stuck[1:]) / ((NF - s0) / 6000.0))
        res["cmd_rms"] = float(np.sqrt(np.mean(rec["cmd"][j, s0:] ** 2)))
        res["T_mean"] = float(np.mean(rec["T"][j, s0:]))
        out.append(res)
    return out


def main():
    base = H.Cells.v294()
    from s3_shapes import cands
    C = {c.name: c for c in cands()}
    cells = [base, C["g1.2"], C["g1.3"], C["g1.4"], C["K-regress"], C["M-regress"], C["K-mid"]]
    fam = H.family()
    mem = [fam[p] for p in ("nominal", "F_hi", "light_b", "b_lo")]
    speeds = [3.0, 6.0, 12.0, 20.0, 27.0]
    d0s = [15.0, 60.0]
    t0 = time.time()
    res = run(cells, mem, speeds, d0s)
    print("on-centre sim: %d cases, %.0f s" % (len(res), time.time() - t0))
    json.dump(res, open(os.path.join(OUT, "s5_oncentre.json"), "w"), indent=1)
    idx = {(r["cells"], r["plant"], r["v"], r["d0"]): r for r in res}
    for p in ("nominal", "F_hi", "light_b", "b_lo"):
        for d0 in d0s:
            print("\n== plant %s  crown d0 %g T:  per speed  r0.1-1 / r1-3 / r3-8 deg/s | line f dB | stuck | breakaways/min | cmd rms" % (p, d0))
            for c in cells:
                row = []
                for v in speeds:
                    r = idx[(c.name, p, v, d0)]
                    row.append("v%-4g %.2f/%.2f/%.2f %.2fHz%+.0fdB st%.2f bk%.0f c%.0f" % (v, r["r_01_1"], r["r_1_3"], r["r_3_8"], r["line_f"],
                                                                                   r["line_dB"], r["stuck_frac"], r["breakaways_per_min"], r["cmd_rms"]))
                print("  %-10s %s" % (c.name, " | ".join(row)))


if __name__ == "__main__":
    main()
