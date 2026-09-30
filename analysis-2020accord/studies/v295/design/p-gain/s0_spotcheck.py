# -*- coding: utf-8 -*-
"""s0_spotcheck.py -- p-gain lens: spot-check the shared harness before leaning on it.

(1) one lane vs the golden model, tick for tick, on THIS lens's knobs (flat Kp x1.5, a Kp(idx) schedule with moved X
    knots, a reshaped demand map) -- the golden model (lkas_fb_lag + lkas_rate_pid_tick) is the second method.
(2) one retrodiction row: V294 mode B, dist lp, nominal member -> tracking gain / turn-hold per band, against the
    harness report's h5 table (lp nominal: 0-5 .840, 5-10 .865/.780, 10-15 .586/.592, 15-22 .764/.636, 22+ .917/.940).
(3) the V294 surface T(idx) from the golden model's own surface routine vs an independent integer march written here.
ANALYSIS ONLY."""
import os
import sys
import time

import numpy as np

HARN = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness"
sys.path.insert(0, HARN)
import v295_harness as H  # noqa: E402
import eps_lkas_chain_model as M  # noqa: E402
from h1_lane_gate import golden_run  # noqa: E402


def main():
    rng = np.random.default_rng(2951)
    base = H.Cells.v294()
    print("V294 sha", base.image_sha256)
    sets = [("V294", base),
            ("Kp x1.5 flat", base.replace(kp_y=(1440,) * 5, name="g1.5")),
            ("Kp sched X moved", base.replace(kp_x=(0, 6, 20, 60, 208), kp_y=(1900, 1700, 1300, 1100, 960), name="sched")),
            ("map reshaped", base.replace(map_y=(0, 80, 110, 125, 150, 280, 413, 550, 688, 1032), name="map"))]
    tot = 0
    for nm, c in sets:
        N = 8000
        xs = np.clip(np.cumsum(rng.integers(-40, 41, N)) + rng.integers(-5, 6, N), -12000, 12000)
        idx100 = rng.integers(0, 241, N // 10 + 1)
        idx100[: N // 40] = rng.integers(0, 20, N // 40)        # force small-idx coverage (the schedule's busy zone)
        sg = rng.choice([-1, 1], N // 10 + 1)
        L = H.Lane([c])
        sp100 = sg * L.map_tab[0, idx100]
        m100 = rng.choice([254, 254, 254, 179, 77], N // 10 + 1)
        g = golden_run(c, xs, np.repeat(sp100, 10)[:N], np.repeat(idx100, 10)[:N], np.repeat(m100, 10)[:N])
        T, K = L.march(xs[None, :], sp100[None, :], idx100[None, :], m100[None, :], keep=("E", "P", "S", "y"))
        mm = int(np.sum(T[0] != g["T"])) + sum(int(np.sum(K[k][0] != g[k])) for k in ("E", "P", "S", "y"))
        tot += mm
        print("  lane vs golden  %-18s %d ticks  mismatches %d   |T|max %d" % (nm, N, mm, np.abs(g["T"]).max()))
    print("(1) lane == golden on this lens's knobs:", "PASS" if tot == 0 else "FAIL")

    # (3) surface: golden routine vs an independent closed-form-free integer march (fb = 0, taper 254, cold boot)
    def my_surface(c, idx):
        kp = int(H.lerp_table(c.kp_x, c.kp_y)[idx])
        sp = int(H.lerp_table(c.map_x, c.map_y)[idx])
        E = sp << c.e_shift
        P = max(-c.p_clamp, min(c.p_clamp, (E * kp) >> 8))
        S = max(-c.sum_clamp, min(c.sum_clamp, (254 * P) >> 8))
        o = 0
        seen = set()
        while o not in seen:
            seen.add(o)
            o2 = ((c.lag_a * o) >> 10) + ((S * c.lag_b) >> 10)
            y = (o + o2) >> 5
            o = o2
        return max(-c.t_clamp, min(c.t_clamp, (y * c.gain) >> 15))
    idxs = [0, 1, 2, 5, 10, 20, 40, 80, 120, 160, 200, 238, 240]
    for nm, c in sets:
        a = [int(v) for v in H.surface(c, idxs)]
        b = [my_surface(c, i) for i in idxs]
        print("  surface %-18s golden %s\n  %-27s mine   %s  %s" % (nm, a, "", b, "EQUAL" if a == b else "DIFFER"))

    # (2) one retrodiction row
    t0 = time.time()
    S = H.sweep_drive([], plants=("nominal",), dists=("lp",))
    r = S[("lp", "V294", "nominal")]
    print("(2) V294 lp nominal (%.0f s):" % (time.time() - t0))
    ref = {"0-5": (0.840, None), "5-10": (0.865, 0.780), "10-15": (0.586, 0.592), "15-22": (0.764, 0.636), "22+": (0.917, 0.940)}
    for b, (tg, th) in ref.items():
        x = r[b]
        print("   %-6s track %.3f (report %.3f)  hold %.3f (report %s)  ish %.3f  cmd %.0f" %
              (b, x["track_gain"], tg, x["turn_hold"], th, x["i_share"], x["cmd_rms"]))


if __name__ == "__main__":
    main()
