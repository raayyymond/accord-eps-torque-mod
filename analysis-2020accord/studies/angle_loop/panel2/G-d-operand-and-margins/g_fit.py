# -*- coding: utf-8 -*-
r"""g_fit.py -- the integer G(v) tables of designer G's implementations, fitted under the full-grid envelopes of g_env.py
with the D designer's own LP fitter (ds_gate2.fit_table: knot values maximising the area under the walk, the EXACT
integer walk c1_lib.cave_G checked <= margin x envelope at every grid speed).  ANALYSIS ONLY.

Implementations (each a structure + a member policy + a table):
  G-P48   (i)   fresh-rate D (P2's code), Kd 48 = the largest Kd under the 20 Hz gain rule (M20 <= V295 at G -> 0:
                Kd 48 -> 0.98x), table under the FULL extended set (brief + ms_free x {b_lo, b_q} products + strict aged
                tier + the D-operand frame box kappa 0.83..1.155 and the motor-frame plant reading)
  G-P44   (i)   the same at Kd 44 (M20 0.90x: a 10 % margin on the 20 Hz gain instead of 2 %)
  G-P48d  (i)   Kd 48, table under the extended set EXCEPT the ms_free x b_q products (declared, with a stop band)
  G-P48L  (iv)  G-P48 with the 9.5-13.5 m/s dip cut a further 20 % (margin 0.77 there): the dip's tracking price
  G-F24   (ii)  held-rate D (F2's code), Kd 24 (the largest Kd the Re(T/w)20 rule allows at highway G), full set
  G-A22   (iii) angle-own D box10 (k_op 64), Kd 22 (the largest Kd the Re(T/w)20 rule allows at highway G), full set
usage: python g_fit.py     -> _scratch/angle_loop/G-dop/g_impls.json, g_fit_out.txt"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402

G2 = X.G2
KNOTS6 = [3.1, 8.0, 10.0, 11.75, 17.5, 26.9]
KNOTS6b = [3.1, 8.0, 10.0, 11.75, 15.0, 26.9]
KNOTS7 = [3.1, 8.0, 9.0, 10.0, 11.75, 17.5, 26.9]


def load_env(tag):
    """the g_env cache (tag = struct_kds_grid[_ki<Ki>])."""
    return json.loads((X.OUT / f"env_{tag}.json").read_text())


def envelope(d, kd, exclude=(), dip=None):
    """min over the members NOT matching any exclude substring, and the 20 Hz rules; dip=(v_lo, v_hi, factor)."""
    kd = str(float(kd))
    env, bind = {}, {}
    for name, v, gd in d["per_member"]:
        base = name.split("|")[0]
        if any(ex in base for ex in exclude):
            continue
        g = gd[kd]
        if v not in env or g < env[v]:
            env[v], bind[v] = g, name
    for v, g in d["rules"][kd].items():
        v = float(v)
        if g < env[v]:
            env[v], bind[v] = g, "RULE20"
    if dip:
        lo, hi, fac = dip
        env = {v: (g * fac if lo <= v <= hi else g) for v, g in env.items()}
    return env, bind


def fit(env, knots, margin=0.96):
    grid = sorted(env)
    tbl, Gk = G2.fit_table(env, knots, margin=margin, grid=grid)
    return [tuple(int(x) for x in r) for r in tbl], Gk


SPECS = {
    "G-P48": dict(dkind="fresh", kd=48, env="fresh_44.0-46.0-48.0_full", exclude=(), knots=KNOTS6,
                  note="(i) fresh-rate D Kd 48, full extended set"),
    "G-P44": dict(dkind="fresh", kd=44, env="fresh_44.0-46.0-48.0_full", exclude=(), knots=KNOTS6,
                  note="(i) fresh-rate D Kd 44 (10 % M20 margin), full extended set"),
    "G-P48d": dict(dkind="fresh", kd=48, env="fresh_44.0-46.0-48.0_full", exclude=("b_q*ms_free",), knots=KNOTS6,
                   note="(i) fresh-rate D Kd 48, ms_free x b_q products DECLARED (not gated)"),
    "G-P48dd": dict(dkind="fresh", kd=48, env="fresh_44.0-46.0-48.0_full", exclude=("b_q*ms_free", "b_lo*ms_free"),
                    knots=KNOTS6, note="(i) fresh-rate D Kd 48, BOTH ms_free products declared (b_lo and b_q)"),
    "G-P44d": dict(dkind="fresh", kd=44, env="fresh_44.0-46.0-48.0_full", exclude=("b_q*ms_free",), knots=KNOTS6,
                   note="(i) fresh-rate D Kd 44 (10 % M20 margin), ms_free x b_q products DECLARED (not gated)"),
    "G-P48L": dict(dkind="fresh", kd=48, env="fresh_44.0-46.0-48.0_full", exclude=(), knots=KNOTS6,
                   dip=(9.5, 13.5, 0.80), note="(iv) G-P48 with the 9.5-13.5 m/s dip a further 20 % lower"),
    "G-P48k40": dict(dkind="fresh", kd=48, ki=40, env="fresh_48.0_full_ki40", exclude=(), knots=KNOTS6,
                     note="(i)+Ki fresh-rate D Kd 48, Ki 56 -> 40 (PI corner 0.62 -> 0.44 Hz), full extended set"),
    "G-P48k32": dict(dkind="fresh", kd=48, ki=32, env="fresh_48.0_full_ki32", exclude=(), knots=KNOTS6,
                     note="(i)+Ki fresh-rate D Kd 48, Ki 56 -> 32 (PI corner 0.62 -> 0.36 Hz), full extended set"),
    "G-F24": dict(dkind="held", kd=24, env="held_23.0-24.0_full", exclude=(), knots=KNOTS6,
                  note="(ii) held-rate D Kd 24, full extended set"),
    "G-F24d": dict(dkind="held", kd=24, env="held_23.0-24.0_full", exclude=("b_q*ms_free",), knots=KNOTS6,
                   note="(ii) held-rate D Kd 24, ms_free x b_q products DECLARED (not gated)"),
    "G-A22": dict(dkind="box10", kd=22, sh=6, env="box10_20.0-22.0_full", exclude=(), knots=KNOTS6,
                  note="(iii) angle-own D box10 (k_op 64) Kd 22, full extended set"),
    "G-A22d": dict(dkind="box10", kd=22, sh=6, env="box10_20.0-22.0_full", exclude=("b_q*ms_free",), knots=KNOTS6,
                   note="(iii) angle-own D box10 Kd 22, ms_free x b_q products DECLARED (not gated)"),
}


def main(only=None):
    out, lines = {}, []

    def P(s=""):
        print(s, flush=True)
        lines.append(s)
    for iid, sp in SPECS.items():
        if only and iid not in only:
            continue
        try:
            d = load_env(sp["env"])
        except FileNotFoundError:
            P(f"{iid}: envelope {sp['env']} not yet computed")
            continue
        env, bind = envelope(d, sp["kd"], sp["exclude"], sp.get("dip"))
        best = None
        for kn in (sp["knots"], KNOTS6b, KNOTS7):
            tbl, Gk = fit(env, kn)
            area = sum(X.G_of(tbl, v) for v in sorted(env))
            if best is None or (len(kn) == len(sp["knots"]) and area > best[2] * 1.0) or \
                    (len(kn) > len(sp["knots"]) and area > best[2] * 1.03):
                best = (kn, tbl, area, Gk)
            P(f"{iid}: knots {kn} -> G {Gk}  area {area:.0f}")
        kn, tbl, area, Gk = best
        P(f"{iid}: CHOSEN knots {kn}, rows {tbl}")
        for v in (1.0, 3.1, 5.0, 8.0, 9.0, 10.0, 11.0, 11.9, 12.5, 13.5, 15.0, 17.0, 19.0, 22.0, 24.0, 26.9, 30.0):
            vv = min(env, key=lambda x: abs(x - v))
            P(f"    v {vv:5.2f}: env {env[vv]:6.0f} ({bind[vv]:32s}) table {X.G_of(tbl, vv):6.0f}  Kp_eff "
              f"{112 * X.G_of(tbl, vv) / 256:5.0f}  T/deg {0.1002 * 112 * X.G_of(tbl, vv) / 256:5.1f}")
        out[iid] = dict(dkind=sp["dkind"], kd=sp["kd"], ki=sp.get("ki", 56), sh=sp.get("sh", 6), rows=tbl, knots=kn,
                        note=sp["note"],
                        exclude=list(sp["exclude"]), dip=sp.get("dip"))
    prev = json.loads((X.OUT / "g_impls.json").read_text()) if (X.OUT / "g_impls.json").exists() else {}
    prev.update(out)
    (X.OUT / "g_impls.json").write_text(json.dumps(prev, indent=1))
    (HERE / "g_fit_out.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return prev


if __name__ == "__main__":
    main(sys.argv[1:] or None)
