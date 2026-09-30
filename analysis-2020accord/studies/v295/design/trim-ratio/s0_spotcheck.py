# -*- coding: utf-8 -*-
"""s0_spotcheck.py -- trim-ratio lens: spot-check the shared harness before using it (orchestrator's instruction).

(1) harness Lane == golden model (lkas_fb_lag + lkas_rate_pid_tick) tick for tick, on V294 and on this lens's own
    candidate class (shl 1 / shl 0 with Kp x2 / x4, a 1017-1020, b up to b_max, C scaled) -- a class H1a did not cover
    exactly (it covered e_shift 0/3/5 with other cells).
(2) one retrodiction row: V294 mode B, dist lp, nominal -> tracking gain by band vs the harness report's h5 table
    (0.840 / 0.865 / 0.586 / 0.764 / 0.917) and dist full 5-10 m/s hard16 14.89.
Analysis only.
"""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
import v295_harness as H  # noqa: E402
import eps_lkas_chain_model as M  # noqa: E402


def golden_run(cells, xs, sps, idxs, ms):
    cal = H.golden_cal(cells)
    st = M.EpsState()
    out = {k: np.zeros(len(xs), np.int64) for k in ("T", "E", "P", "S", "y")}
    for n in range(len(xs)):
        fb = M.lkas_fb_lag(int(xs[n]), st, cal)
        r = M.lkas_rate_pid_tick(int(sps[n]), fb, int(idxs[n]), st, cal, pol=1, taper=int(ms[n]))
        for k in out:
            out[k][n] = r[k]
    return out


def main():
    rng = np.random.default_rng(2951)
    base = H.Cells.v294()
    sets = [("V294", base),
            ("shl1 Kp1920 a1017 b600 C512", base.replace(e_shift=1, kp_y=(1920,) * 5, fb_a=1017, fb_b=600, fb_clamp=512)),
            ("shl0 Kp3840 a1020 b400 C256", base.replace(e_shift=0, kp_y=(3840,) * 5, fb_a=1020, fb_b=400, fb_clamp=256)),
            ("shl2 Kp960 a1011 b1700 C1024", base.replace(fb_b=1700)),
            ("shl2 Kp960 a1017 b1231 C1024", base.replace(fb_a=1017, fb_b=1231))]
    tot, mis = 0, 0
    for nm, c in sets:
        N = 8000
        xs = np.clip(np.cumsum(rng.integers(-80, 81, N)) + rng.integers(-5, 6, N), -12000, 12000)
        idx100 = rng.integers(0, 241, N // 10 + 1)
        sg = rng.choice([-1, 1], N // 10 + 1)
        L = H.Lane([c])
        sp100 = sg * L.map_tab[0, idx100]
        m100 = rng.choice([254, 254, 254, 200, 128, 77], N // 10 + 1)
        g = golden_run(c, xs, np.repeat(sp100, 10)[:N], np.repeat(idx100, 10)[:N], np.repeat(m100, 10)[:N])
        T, K = L.march(xs[None, :], sp100[None, :], idx100[None, :], m100[None, :], keep=("E", "P", "S", "y"))
        mm = int(np.sum(T[0] != g["T"])) + sum(int(np.sum(K[k][0] != g[k])) for k in ("E", "P", "S", "y"))
        tot += N
        mis += mm
        print("  (1) %-32s %d ticks: mismatches %d   max|T| %d" % (nm, N, mm, int(np.abs(g["T"]).max())))
    print("  (1) TOTAL %d ticks, %d mismatches -> %s" % (tot, mis, "PASS" if mis == 0 else "FAIL"))
    t0 = time.time()
    S = H.sweep_drive([], plants=("nominal",), dists=("lp", "full"))
    ref_lp = dict(zip(("0-5", "5-10", "10-15", "15-22", "22+"), (0.840, 0.865, 0.586, 0.764, 0.917)))
    ok = True
    for b, want in ref_lp.items():
        got = S[("lp", "V294", "nominal")][b]["track_gain"]
        ok &= abs(got - want) < 0.0015
        print("  (2) lp  %-6s track_gain %.4f  (report %.3f)" % (b, got, want))
    h = S[("full", "V294", "nominal")]["5-10"]["hard16"]
    ok &= abs(h - 14.89) < 0.02
    print("  (2) full 5-10 hard16 %.3f (report 14.89)   %.0f s  -> %s" % (h, time.time() - t0, "PASS" if ok else "FAIL"))


if __name__ == "__main__":
    main()
