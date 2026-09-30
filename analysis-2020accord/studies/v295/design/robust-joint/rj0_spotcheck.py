# -*- coding: utf-8 -*-
"""rj0_spotcheck.py -- lens robust-joint, pre-flight spot-check of the shared harness (CRITERIA F1).

(1) one lane tick-for-tick vs the golden model (lkas_fb_lag + lkas_rate_pid_tick) on cell sets INSIDE this lens's search
    space that the harness's H1a did not use verbatim (diff operand, raised b, moved pole, raised C, Kp schedule,
    moved output lag, e_shift 1 / 0, D live) -- my own random driver, my own seed.
(2) one retrodiction row: V294, member nominal, dist lp, mode B, 5-10 m/s tracking gain (report: 0.865) and the
    measured 0.871, via sweep_drive (the fast path this lens will use) AND via score()'s internal path is not re-run
    (too slow); instead the same number is recomputed from simulate() directly as a second method.
ANALYSIS ONLY.
"""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
HARN = os.path.join(os.path.dirname(HERE), "harness")
sys.path.insert(0, HARN)
import v295_harness as H  # noqa: E402
import eps_lkas_chain_model as M  # noqa: E402


def golden(cells, xs, sp1k, idx1k, m1k):
    cal = H.golden_cal(cells)
    st = M.EpsState()
    T = np.zeros(len(xs), np.int64)
    S = np.zeros(len(xs), np.int64)
    for n in range(len(xs)):
        fb = M.lkas_fb_lag(int(xs[n]), st, cal)
        r = M.lkas_rate_pid_tick(int(sp1k[n]), fb, int(idx1k[n]), st, cal, pol=1, taper=int(m1k[n]))
        T[n], S[n] = r["T"], r["S"]
    return T, S


def main():
    rng = np.random.default_rng(20260930)
    base = H.Cells.v294()
    print("V294 cells from image sha %s" % base.image_sha256)
    sets = [
        ("V294", base),
        ("b1500 a1005 C2048", base.replace(fb_b=1500, fb_a=1005, fb_clamp=2048)),
        ("b1134 Kp sched 1100..960", base.replace(fb_b=1134, kp_x=(0, 16, 40, 136, 208), kp_y=(1150, 1100, 1000, 960, 960))),
        ("lag 980/697 b1700", base.replace(lag_a=980, lag_b=697, fb_b=1700)),
        ("e_shift1 Kp1920 b567", base.replace(e_shift=1, kp_y=(1920,) * 5)),
        ("e_shift0 Kp3840 b300 a1015", base.replace(e_shift=0, kp_y=(3840,) * 5, fb_b=300, fb_a=1015, fb_clamp=1024)),
        ("Kd64 Dcl2048 b900", base.replace(kd_y=(64, 64, 32, 16), d_clamp=2048, fb_b=900)),
    ]
    tot, mis = 0, 0
    for nm, c in sets:
        N = 8000
        xs = np.clip(np.cumsum(rng.integers(-40, 41, N)) + rng.integers(-8, 9, N), -12000, 12000)
        idx100 = np.clip(np.cumsum(rng.integers(-6, 7, N // 10 + 1)), 0, 240)
        idx100 = np.abs(idx100)
        sg = np.where(rng.random(N // 10 + 1) < 0.5, -1, 1)
        L = H.Lane([c])
        sp100 = sg * L.map_tab[0, idx100]
        m100 = rng.choice([254, 254, 254, 218, 179, 77], N // 10 + 1)
        Tg, Sg = golden(c, xs, np.repeat(sp100, 10)[:N], np.repeat(idx100, 10)[:N], np.repeat(m100, 10)[:N])
        T, K = L.march(xs[None, :], sp100[None, :], idx100[None, :], m100[None, :], keep=("S",))
        mm = int(np.sum(T[0] != Tg)) + int(np.sum(K["S"][0] != Sg))
        tot += N
        mis += mm
        print("  %-30s %d ticks  mismatches(T,S) %d   |T|max %d  problems %s" % (nm, N, mm, np.abs(Tg).max(), c.problems()))
    print("SPOT (1): %d ticks, %d mismatches -> %s" % (tot, mis, "PASS" if mis == 0 else "FAIL"))

    # (2) retrodiction row
    t0 = time.time()
    S = H.sweep_drive([], plants=("nominal",), dists=("lp",))
    t1 = time.time() - t0
    row = S[("lp", "V294", "nominal")]["5-10"]
    meas = H.drive_metrics(H.drive_series_measured(H.route_chunks()))["5-10"]
    print("SPOT (2a) sweep_drive %.1f s: V294 nominal lp 5-10 m/s tracking gain %.3f (report 0.865), measured %.3f (report 0.871)"
          % (t1, row["track_gain"], meas["track_gain"]))
    # second method: simulate() directly and my own polyfit of la_act on la_plan over |plan| > 0.3 in 5-10 m/s
    fam = H.family()
    ch = H.route_chunks()
    R = H.simulate([base], [fam["nominal"]], ch, H.SimOpts(mode="B", dist="lp"))
    pl, ac = [], []
    for j in range(len(ch)):
        n = R["lens"][j]
        v = R["v"][j, :n]
        mk = (v >= 5) & (v < 10)
        if mk.sum() < 100:
            continue
        pl.append(R["la_plan"][j, :n][mk]); ac.append(R["la_act"][j, :n][mk])
    pl, ac = np.concatenate(pl), np.concatenate(ac)
    sel = np.abs(pl) > 0.3
    g2 = float(np.polyfit(pl[sel], ac[sel], 1)[0])
    print("SPOT (2b) simulate() + own polyfit: %.3f" % g2)
    ok2 = abs(row["track_gain"] - 0.865) <= 0.01 and abs(g2 - row["track_gain"]) < 1e-9
    print("SPOT (2): %s" % ("PASS" if ok2 else "FAIL"))


if __name__ == "__main__":
    main()
