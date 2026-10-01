# -*- coding: utf-8 -*-
"""c1r2_fit_table.py -- fit the cave's G(v) table UNDER the rev-2 envelope.  ANALYSIS ONLY.

Rule (written before the fit): the INTEGER walk the cave executes (c1_lib.cave_G over every gp-0x6a5e count from 0
to 35 m/s) must sit at or below (1 - MARGIN) x the envelope at every grid speed AND below the envelope linearly
interpolated between grid speeds; knots are placed on the 0.25 m/s grid; the fewest knots that achieve it
(greedy: each segment is extended as far right as the chord stays under the bound, then shortened by one grid
step at a time if the integer walk violates it).  The table ends flat at the last knot (the sentinel row).
usage: python c1r2_fit_table.py <kd> <ki> [margin]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402
import c1r2_members as M  # noqa: E402


def load_env(kd, ki):
    js = json.loads((C.OUT / ("design_G_r2_" + (f"kp{C.KP_BASE}_" if C.KP_BASE != 225 else "") + f"kd{kd}_ki{ki}.json")).read_text())
    vs = sorted(float(v) for v in js)
    env = np.array([min(js[str(v) if str(v) in js else repr(v)][n] for n in M.TIER_A + M.TIER_B) for v in vs], float)
    return np.array(vs), env


def walk_ok(knots, vs, bound):
    tbl = C.make_table(knots)
    counts = np.arange(0, C.spd_counts(35.0) + 1)
    g = np.array([C.cave_G(int(c), tbl) for c in counts])
    vv = counts / C.SPD_PER_MPS
    b = np.interp(vv, vs, bound)
    return bool(np.all(g <= b + 1e-9)), tbl, float(np.max(g - b))


def fit(vs, env, margin, K=6, w=None):
    """DP: the K-knot piecewise-linear G (flat outside the first/last knot) under the bound that maximises the sum of
    G over the grid speeds; knot values are the bound at the knot (floored).  Then the integer walk is checked and,
    where it pokes above the bound (sar 12 floors cannot raise G, so this only guards the knot rounding), every knot
    value is lowered by 1 count until it passes."""
    bound = np.floor(env * (1.0 - margin))
    n = len(vs)
    w = np.ones(n) if w is None else np.asarray(w, float)
    feas = np.zeros((n, n), bool)
    area = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            gi, gj = bound[i], bound[j]
            q = np.arange(i, j + 1)
            chord = gi + (gj - gi) * (vs[q] - vs[i]) / (vs[j] - vs[i])
            if np.all(chord <= bound[q] + 1e-9):
                feas[i, j] = True
                area[i, j] = (w[q[1:]] * chord[1:]).sum()          # points i+1..j (weighted)
    left_ok = np.array([np.all(bound[:i + 1] >= bound[i]) for i in range(n)])
    right_ok = np.array([np.all(bound[i:] >= bound[i]) for i in range(n)])
    NEG = -1e18
    best = np.full((K + 1, n), NEG)
    prev = np.full((K + 1, n), -1, int)
    for i in range(n):
        if left_ok[i]:
            best[1, i] = bound[i] * w[:i + 1].sum()          # flat from the grid start to knot i
    for k in range(2, K + 1):
        for j in range(n):
            cand = np.where(feas[:, j], best[k - 1] + area[:, j], NEG)
            i = int(np.argmax(cand))
            if cand[i] > NEG / 2:
                best[k, j] = cand[i]
                prev[k, j] = i
    tot = np.full((K + 1, n), NEG)
    for k in range(1, K + 1):
        for j in range(n):
            if best[k, j] > NEG / 2 and right_ok[j]:
                tot[k, j] = best[k, j] + bound[j] * w[j + 1:].sum()
    k, j = np.unravel_index(int(np.argmax(tot)), tot.shape)
    idx = []
    while j >= 0 and k >= 1:
        idx.append(j)
        j = prev[k, j]
        k -= 1
    idx = idx[::-1]
    knots = [(float(vs[i]), int(bound[i])) for i in idx]
    for _ in range(64):
        ok, _, _ = walk_ok(knots, vs, bound)
        if ok:
            break
        knots = [(v, g - 1) for v, g in knots]
    return knots, bound


def main():
    kd, ki = int(sys.argv[1]), int(sys.argv[2])
    margin = float(sys.argv[3]) if len(sys.argv) > 3 else 0.04
    K = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    vs, env = load_env(kd, ki)
    # optional "--weighted": weight x3 the speeds where the goal's criteria bind on rev 2 -- 5-12.5 m/s (dwell-then-jump,
    # stick-slip) and 15-22 m/s (the tracking band with the least margin); x1 elsewhere
    w = None
    if "--weighted" in sys.argv:
        w = np.where(((vs >= 5) & (vs <= 12.5)) | ((vs >= 15) & (vs <= 22)), 3.0, 1.0)
    knots, bound = fit(vs, env, margin, K, w)
    ok, tbl, worst = walk_ok(knots, vs, bound)
    print(f"kd {kd} ki {ki} margin {margin}: {len(knots)} knots, walk under bound: {ok} (max excess {worst:+.1f})")
    for v, g in knots:
        print(f"   ({v:5.2f} m/s, G {g:5d})  Kp_eff {C.KP_BASE * g / 256:6.0f}")
    print("   table rows:", tbl)
    # the margin actually achieved, per speed, on the grid
    counts = np.array([C.spd_counts(v) for v in vs])
    g = np.array([C.cave_G(int(c), tbl) for c in counts])
    m = 1 - g / env
    print(f"   achieved margin below the envelope: min {m.min() * 100:.1f} % (at {vs[np.argmin(m)]:.2f} m/s), "
          f"median {np.median(m) * 100:.1f} %")
    return knots


if __name__ == "__main__":
    main()
