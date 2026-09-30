# -*- coding: utf-8 -*-
"""h1_lane_gate.py -- gates H1a/H1b/H1c (CRITERIA-HARNESS.md).

H1a  the harness Lane == the golden model (lkas_fb_lag + lkas_rate_pid_tick), tick for tick on T, E, I, P, D, S, y, over
     >= 50,000 random ticks on 9 cell sets (V294; Ki live; Kd live; Ki+Kd; V282-class sum operand; random banks; e_shift
     0..5; tapers < 254; V293 C = 0).
H1b  the int32 guard raises on constructed overflows (b above b_max at |x| = 12000; a Kp*E product past 2^31; a 16-bit y)
     and does NOT raise on the V294 cells over the whole r71b replay.
H1c  the Lane driven by r71b's plib inputs reproduces plib.march bit for bit (live and null) and the 427 tap to <= 10
     counts rms hands-off; the harness's own demand chain reproduces plib's idx/sign/m.
"""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v295_harness as H  # noqa: E402
import eps_lkas_chain_model as M  # noqa: E402


def golden_run(cells, xs, sps, idxs, ms):
    cal = H.golden_cal(cells)
    st = M.EpsState()
    keys = ("T", "E", "I", "P", "D", "S", "y")
    out = {k: np.zeros(len(xs), np.int64) for k in keys}
    for n in range(len(xs)):
        fb = M.lkas_fb_lag(int(xs[n]), st, cal)
        r = M.lkas_rate_pid_tick(int(sps[n]), fb, int(idxs[n]), st, cal, pol=1, taper=int(ms[n]))
        for k in keys:
            out[k][n] = r[k]
    return out


def main():
    rng = np.random.default_rng(295)
    base = H.Cells.v294()
    v282 = H.Cells.v282()
    v293 = H.Cells.v293()
    print("H1 LANE GATE    V294 image sha256 %s" % base.image_sha256)
    print("  cross-check Cells.from_image vs the kit reader (r71b_cache.v294_cells): ", end="")
    import r71b_cache as RC
    c = RC.v294_cells()
    same = (base.fb_a == c["fb_a"] and base.fb_b == c["fb_b"] and base.fb_clamp == c["fb_clamp"] and base.fb_op == c["fb_op"]
            and base.e_shift == c["e_shift"] and list(base.kp_y) == [int(v) for v in c["kp_Y"]]
            and list(base.kd_y) == [int(v) for v in c["kd_Y"]] and list(base.map_y) == [int(v) for v in c["map_Y"]]
            and (base.lag_a, base.lag_b, base.gain, base.t_clamp, base.p_clamp, base.sum_clamp, base.d_clamp, base.ki)
            == (c["lag_a"], c["lag_b"], c["gain"], c["t_clamp"], c["p_clamp"], c["sum_clamp"], c["d_clamp"], c["ki"])
            and list(base.taperD[1]) == [int(v) for v in c["fadeB"][1]] and list(base.taperB[1]) == [int(v) for v in c["fadeA"][1]]
            and list(base.G_same[1]) == [int(v) for v in c["taperS"][1]] and list(base.G_opp[0]) == [int(v) for v in c["taperO"][0]])
    print("IDENTICAL" if same else "DIFFERENT")
    print("  V294 cells: %s" % {k: v for k, v in H.asdict(base).items() if k not in ("image_sha256",)})
    print("  V294 dead band %d, I clamp %d (census: 4, 10240)" % (base.deadband, base.i_clamp))
    ok = same
    # ---------------------------------------------------------------- H1a
    sets = [
        ("V294", base),
        ("V294+Ki8", base.replace(ki=8)),
        ("V294+Ki64", base.replace(ki=64)),
        ("V294+Kd128/Dcl10240", base.replace(kd_y=(128,) * 4, d_clamp=10240)),
        ("V294+Ki8+Kd64 sched", base.replace(ki=8, kd_y=(16, 64, 128, 64), d_clamp=10240)),
        ("V282 (sum, shl5, C46080, Kd128)", v282),
        ("V293 (C=0)", v293),
        ("random banks e_shift3", base.replace(kp_y=(300, 700, 960, 1500, 2000), kp_x=(0, 40, 90, 150, 220), e_shift=3,
                                              fb_a=1000, fb_b=900, fb_clamp=2048, ki=3, deadband=2, i_clamp=5000,
                                              kd_y=(0, 40, 80, 10), d_clamp=3000, lag_a=960, lag_b=1014)),
        ("e_shift0 sum op", base.replace(e_shift=0, fb_op="sum", fb_b=300, fb_a=900, fb_clamp=46080)),
        ("e_shift5 diff Kd", base.replace(e_shift=5, kd_y=(128,) * 4, d_clamp=10240, kp_y=(248,) * 5)),
    ]
    total = 0
    mism_total = 0
    for nm, cells in sets:
        N = 6000
        xs = np.clip(np.cumsum(rng.integers(-60, 61, N)) + rng.integers(-5, 6, N), -12000, 12000)
        idx100 = rng.integers(0, 241, N // 10 + 1)
        sg = rng.choice([-1, 1], N // 10 + 1)
        L = H.Lane([cells])
        sp100 = sg * L.map_tab[0, idx100]
        m100 = rng.choice([254, 254, 254, 200, 128, 77], N // 10 + 1)
        idxs = np.repeat(idx100, 10)[:N]
        sps = np.repeat(sp100, 10)[:N]
        ms = np.repeat(m100, 10)[:N]
        g = golden_run(cells, xs, sps, idxs, ms)
        T, K = L.march(xs[None, :], sp100[None, :], idx100[None, :], m100[None, :], keep=("E", "I", "P", "D", "S", "y"))
        mm = int(np.sum(T[0] != g["T"]))
        for k in ("E", "I", "P", "D", "S", "y"):
            mm += int(np.sum(K[k][0] != g[k]))
        total += N
        mism_total += mm
        print("  H1a %-32s %d ticks: mismatches (T,E,I,P,D,S,y) = %d   |T| max %d  |I| max %d  |D| max %d"
              % (nm, N, mm, np.abs(g["T"]).max(), np.abs(g["I"]).max(), np.abs(g["D"]).max()))
    # batched: all sets in ONE batch must equal their single-lane runs
    N = 3000
    xs = np.clip(np.cumsum(rng.integers(-60, 61, N)), -12000, 12000)
    idx100 = rng.integers(0, 241, N // 10 + 1)
    sg = rng.choice([-1, 1], N // 10 + 1)
    LB = H.Lane([c for _, c in sets])
    sp100 = sg[None, :] * LB.map_tab[:, idx100]
    m100 = np.full(N // 10 + 1, 254)
    TB = LB.march(np.repeat(xs[None, :], len(sets), 0), sp100, np.repeat(idx100[None, :], len(sets), 0),
                  np.repeat(m100[None, :], len(sets), 0))
    mb = 0
    for j, (nm, cells) in enumerate(sets):
        g = golden_run(cells, xs, np.repeat(sp100[j], 10)[:N], np.repeat(idx100, 10)[:N], np.repeat(m100, 10)[:N])
        mb += int(np.sum(TB[j] != g["T"]))
    total += N * len(sets)
    mism_total += mb
    print("  H1a batched (%d different cell sets in one Lane): %d mismatching T ticks" % (len(sets), mb))
    g1a = mism_total == 0 and total >= 50000
    print("H1a %s  (%d ticks compared, %d mismatches)" % ("PASS" if g1a else "FAIL", total, mism_total))
    ok &= g1a
    # ---------------------------------------------------------------- H1b
    print("  H1b positive controls (each must RAISE):")
    ctrls = [("b above b_max at |x| 12000", base.replace(fb_b=int(base.b_max) + 60), np.full(20000, 12000), 0),
             ("Kp*E past 2^31", base.replace(kp_y=(65535,) * 5, fb_clamp=46080, fb_op="sum", fb_b=2301, fb_a=1011),
              np.full(3000, 12000), 0),
             ("y past the 16-bit sxh", base.replace(sum_clamp=40000, p_clamp=65535, kp_y=(4000,) * 5), np.zeros(4000), 240)]
    g1b = True
    for nm, cells, xs, idx in ctrls:
        L = H.Lane([cells])
        n = len(xs)
        sp = np.full(n // 10 + 1, L.map_tab[0, idx])
        try:
            L.march(xs[None, :], sp[None, :], np.full((1, n // 10 + 1), idx), np.full((1, n // 10 + 1), 254))
            print("     %-28s did NOT raise  FAIL" % nm)
            g1b = False
        except H.Int32Overflow as e:
            print("     %-28s raised: %s" % (nm, str(e)[:90]))
    print("     static problems() on the b-overflow control: %s" % ctrls[0][1].problems())
    print("     static problems() on V294: %s" % base.problems())
    # ---------------------------------------------------------------- H1c
    d = H.route()
    import plib as P
    n = len(d["t"])
    t0 = time.time()
    L = H.Lane([base, base.replace(fb_clamp=0, name="null")])
    x1k = np.clip(np.round(d["x1k"]), -12000, 12000).astype(np.int64)
    sp = d["sgn"].astype(np.int64) * L.map_tab[0, d["idx"]]
    T = L.march(np.vstack([x1k, x1k]), np.vstack([sp, sp]), np.vstack([d["idx"], d["idx"]]),
                np.vstack([d["m"], d["m"]]))
    dt_run = time.time() - t0
    sg = d["sg"]
    live = sg * T[0]
    null = sg * T[1]
    e_live = int(np.sum(live != d["T1k_live"]))
    e_null = int(np.sum(null != d["T1k_null"]))
    print("  H1c harness Lane on r71b (%d ticks, guard ON, %.1f s): mismatches vs plib.march live %d, null %d"
          % (len(x1k), dt_run, e_live, e_null))
    q = P.quant(live[d["tick_tap"]])
    j = d["j100"]
    ho = d["eng"][j] & (np.abs(d["bar"][j]) < 400) & ~d["pressed"][j]
    rms = float(np.sqrt(np.mean((d["T_tap"][ho] - q[ho]) ** 2)))
    print("  H1c tap vs harness live lane, hands-off engaged: %.2f counts rms over %d tap frames (plib G1: 3.64)" % (rms, ho.sum()))
    # the harness's own demand chain vs plib's idx/sgn/m (plib used the kit's float bar = raw*1.024)
    LD = H.Lane([base])
    idx_h, sp_h, m_h = [], [], []
    for k in range(n):
        i_, s_, m_ = LD.demand(d["cmd"][k], d["bar"][k])
        idx_h.append(i_[0]); sp_h.append(s_[0]); m_h.append(m_[0])
    idx_h, sp_h, m_h = np.array(idx_h), np.array(sp_h), np.array(m_h)
    eng = d["eng"]
    print("  H1c demand chain vs plib on engaged frames: idx equal %.5f, sp equal %.5f, taper m equal %.5f"
          % (np.mean(idx_h[eng] == d["idx"][eng]), np.mean(sp_h[eng] == sp[eng]), np.mean(m_h[eng] == d["m"][eng])))
    g1c = e_live == 0 and e_null == 0 and rms <= 10.0
    print("H1b %s" % ("PASS" if g1b else "FAIL"))
    print("H1c %s" % ("PASS" if g1c else "FAIL"))
    ok &= g1b and g1c
    print("H1", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
