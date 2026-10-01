# -*- coding: utf-8 -*-
r"""r2a_fit.py -- the integer G(v) tables for this reviser's NEW implementations (P2, P3, P4, F2), fitted exactly as the
panel fitted P1 (= D2a) and F1 (= B0r): ds_gate2.fit_table, an LP maximising the area under the walk with the EXACT
integer walk (c1_lib.cave_G) held >= 4 % under the structure's own envelope at every grid speed (1-35 m/s at 0.25 +
the plant knots).  Also: a CONTROL that the panel's own tables P1 / F1 are re-produced by the same fit from the same
envelope and knots (so a 6-knot refit differs from the panel's 7-knot table only by the knot it drops), and a table of
the angle stiffness each implementation delivers.  ANALYSIS ONLY.   usage: python r2a_fit.py"""
from __future__ import annotations

import json

import numpy as np

import r2a_common as R

import ds_gate2 as G2  # noqa: E402

VS = (1.0, 3.1, 5.0, 8.0, 9.0, 10.0, 11.0, 11.75, 12.5, 13.0, 15.0, 15.5, 17.0, 19.0, 22.0, 26.9, 30.0)


def main():
    lines = []

    def P(s=""):
        print(s, flush=True)
        lines.append(s)

    fitted = {}
    # control: the panel tables re-fit from the cached envelopes at the 7 knots
    for impl, struct in (("P1", "fresh34"), ("F1", "held20")):
        env, _ = R.env_of(struct)
        tbl, _ = G2.fit_table(env, R.KNOTS7)
        same = [tuple(r) for r in tbl] == [tuple(r) for r in R.PANEL_ROWS[R.IMPLS[impl]["table"].split(":")[1]]]
        P(f"CONTROL {impl}: the 7-knot fit of the {struct} envelope reproduces the panel table byte for byte: {same}")
    for impl, im in R.IMPLS.items():
        if not im["table"].startswith("fit:"):
            continue
        _, struct, nk = im["table"].split(":")
        env, bind = R.env_of(struct)
        knots = {"5": R.KNOTS5, "6": R.KNOTS6, "7": R.KNOTS7}[nk]
        tbl, Gk = G2.fit_table(env, knots)
        fitted[impl] = [list(r) for r in tbl]
        worst = min(env[v] / max(G2.G_at(v, tbl), 1) for v in G2.GRID)
        P(f"{impl} ({im['note']}): knots {knots}")
        P(f"   rows {tbl}")
        P(f"   min envelope / G over the grid {worst:.3f}")
    (R.OUT / "r2a_tables.json").write_text(json.dumps(fitted))
    # the rejected Kd raises: where their own envelope collapses (no table can sit under a zero envelope)
    P("")
    P("REJECTED at the envelope stage -- the D term's own loop against the lowest credible damping:")
    k_T = (5346 / 32768) * (254 / 256) * (507 / 1024) * 2 / (32 * (1 - 992 / 1024))
    for impl, im in R.REJECTED.items():
        struct = im["struct"]
        env, bind = R.env_of(struct)
        kd = R.STRUCT[struct].kd
        zero = [v for v in sorted(env) if env[v] <= 0]
        P(f"  {impl} ({im['note']}): D_T = (Kd/8)*4.712*{k_T:.4f} = {kd / 8 * 4.712 * k_T:.2f} T per deg/s "
          f"(Kd 34: {34 / 8 * 4.712 * k_T:.2f}; b_lo below 10 m/s and the b_q floor: 3.46); envelope = 0 at "
          f"{len(zero)} grid speeds {zero[0] if zero else '-'}..{zero[-1] if zero else '-'} m/s, binding "
          f"{sorted(set(bind[v] for v in zero))}")
    tabs = R.tables()
    P("")
    P("ANGLE STIFFNESS of each implementation, T counts per degree of error at DC on the P path "
      "(= 0.1002 * Kp_eff, Kp_eff = 112 G / 256), and the envelope binding member of its structure")
    P("impl | " + " | ".join(f"{v:g}" for v in VS))
    for impl in R.IMPLS:
        tbl = tabs[impl]
        P(f"{impl} | " + " | ".join(f"{0.1002 * 112 * G2.G_at(v, tbl) / 256:.0f}" for v in VS))
    for struct in ("fresh34", "fresh41", "fresh48", "held20"):
        env, bind = R.env_of(struct)
        P(f"env {struct} | " + " | ".join(f"{0.1002 * 112 * env[min(env, key=lambda q: abs(q - v))] / 256:.0f}" for v in VS))
        P(f"bind {struct} | " + " | ".join(bind[min(bind, key=lambda q: abs(q - v))] for v in VS))
    P("")
    P("TABLE BYTES per implementation (6-byte rows incl. the 0xFFFF row): " +
      ", ".join(f"{k} {len(R.table_bytes(tabs[k]))}" for k in R.IMPLS))
    (R.HERE / "r2a_fit_out.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
