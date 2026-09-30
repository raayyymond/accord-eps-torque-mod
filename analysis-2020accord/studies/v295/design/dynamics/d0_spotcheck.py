# -*- coding: utf-8 -*-
"""d0_spotcheck.py -- lens "dynamics": spot-check the shared harness before leaning on it (orchestrator's instruction).

(1) ONE lane vs the golden model, tick for tick (T, E, P, D, S, y), on the cell sets THIS lens will score:
    V294 as built; output lag 962/982 (10 Hz); Kd 512 flat + D clamp 10240 + sum clamp 15240; fb_a 1017 (b held).
    Golden model = analysis-2020accord/model eps_lkas_chain_model.lkas_fb_lag + lkas_rate_pid_tick (independent code).
(2) ONE retrodiction row: V294, nominal member, dist "lp", mode B -> tracking gain / turn-hold / cmd rms per band,
    to be compared with V295-HARNESS.md section 6 (lp nominal: 0.840/0.865/0.586/0.764/0.917 tracking gain).
(3) The census anchors this lens leans on: output-lag DC 507/512, pole 5.05 Hz; |P/x| at 20 Hz 2.079; K_alpha 0.210.
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
    keys = ("T", "E", "P", "D", "S", "y")
    out = {k: np.zeros(len(xs), np.int64) for k in keys}
    for n in range(len(xs)):
        fb = M.lkas_fb_lag(int(xs[n]), st, cal)
        r = M.lkas_rate_pid_tick(int(sps[n]), fb, int(idxs[n]), st, cal, pol=1, taper=int(ms[n]))
        for k in keys:
            out[k][n] = r[k]
    return out


def main():
    rng = np.random.default_rng(20260930)
    base = H.Cells.v294()
    print("V294 image sha256", base.image_sha256)
    sets = [("V294", base),
            ("lag 962/982", base.replace(lag_a=962, lag_b=982, name="L10")),
            ("Kd512 Dcl10240 Scl15240", base.replace(kd_y=(512,) * 4, d_clamp=10240, sum_clamp=15240, name="D512")),
            ("fb_a 1017 b567", base.replace(fb_a=1017, name="A1017"))]
    tot, mm_tot = 0, 0
    for nm, c in sets:
        N = 8000
        xs = np.clip(np.cumsum(rng.integers(-60, 61, N)) + rng.integers(-5, 6, N), -12000, 12000)
        idx100 = np.clip(np.cumsum(rng.integers(-8, 9, N // 10 + 1)) + 60, 0, 240)   # a slewing command, like the road
        sg = np.where(rng.random(N // 10 + 1) < 0.02, -1, 1)
        L = H.Lane([c])
        sp100 = sg * L.map_tab[0, idx100]
        m100 = np.full(N // 10 + 1, 254)
        g = golden_run(c, xs, np.repeat(sp100, 10)[:N], np.repeat(idx100, 10)[:N], np.repeat(m100, 10)[:N])
        T, K = L.march(xs[None, :], sp100[None, :], idx100[None, :], m100[None, :], keep=("E", "P", "D", "S", "y"))
        mm = int(np.sum(T[0] != g["T"])) + sum(int(np.sum(K[k][0] != g[k])) for k in ("E", "P", "D", "S", "y"))
        tot += N
        mm_tot += mm
        print("  (1) %-26s %d ticks: mismatches (T,E,P,D,S,y) %d   |T| max %d |D| max %d" % (nm, N, mm, np.abs(g["T"]).max(),
                                                                                           np.abs(g["D"]).max()))
    print("(1) lane == golden model: %s (%d ticks, %d mismatches)" % ("PASS" if mm_tot == 0 else "FAIL", tot, mm_tot))

    # (3) census anchors
    f = np.array([20.0])
    print("(3) |P/x| at 20 Hz V294 %.3f (census/harness 2.079)" % abs(H.lane_ctf(base, f, kind="P")[0]))
    print("    output-lag DC %.6f (507/512 = %.6f), pole %.3f Hz" % (base.lag_b / (16.0 * (1024 - base.lag_a)), 507 / 512.,
                                                                    -np.log(base.lag_a / 1024.) / (2 * np.pi * 1e-3)))
    ka = (960 / 256.) * 8 * 1e-3 * base.fb_b / (1024 - base.fb_a) * 0.1603
    print("    K_alpha (census formula) %.4f T per deg/s^2 (census 0.210)" % ka)

    # (2) one retrodiction row
    t0 = time.time()
    S = H.sweep_drive([], plants=("nominal",), dists=("lp",))
    r = S[("lp", "V294", "nominal")]
    print("(2) retrodiction V294 nominal lp (%.0f s):" % (time.time() - t0))
    ref = {"0-5": 0.840, "5-10": 0.865, "10-15": 0.586, "15-22": 0.764, "22+": 0.917}
    for b in ("0-5", "5-10", "10-15", "15-22", "22+"):
        x = r.get(b, {})
        print("    %-6s track %.3f (harness report %.3f)  turn-hold %.3f  cmd rms %.0f  i-share %.3f" %
              (b, x.get("track_gain", np.nan), ref[b], x.get("turn_hold", np.nan), x.get("cmd_rms", np.nan),
               x.get("i_share", np.nan)))
    ok = all(abs(r[b]["track_gain"] - ref[b]) < 0.0015 for b in ref)
    print("(2) retrodiction row reproduces the harness report: %s" % ("PASS" if ok else "FAIL"))


if __name__ == "__main__":
    main()
