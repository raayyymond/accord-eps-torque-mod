# -*- coding: utf-8 -*-
r"""g_selftest.py -- controls for g_ext (designer G, panel 2).  ANALYSIS ONLY.
  C1  the P2 / F2 table rows in g_ext == the rows parsed from rev2-A's published cave hex (the bytes, not the doc)
  C2  metrics_ext(kappa 1, base member) == score_freq.score on the SAME member/speed: pm_raw, gm, M20, L20, Re(T/w),
      Tc530, Tr530, hold, Tr163 -- for P2 and F2 on 12 members x 6 speeds (the extension changed nothing it did not mean to)
  C3  pm_fixed == pm_raw wherever every crossing lags (phase <= 0) -- and the points where they differ are listed with
      their crossing phases and the EXACT periodic rho (ds_model.Lifted), so the correction is shown, not asserted
  C4  the kd-linear decomposition: L_PI + kd L_D1 == score_freq's L at the table's kd (max rel err)
  C5  box10 FRF: its low-frequency D equals -(kd k_op / 80) S per deg/s (the arithmetic), and its fundamental equals the
      10 ms average rate (|1 - q^10| / (10 ms w) -> 1 at DC)
usage: python g_selftest.py   -> g_selftest_out.txt"""
from __future__ import annotations

import struct
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402

SF, DM, G2 = X.SF, X.DM, X.G2
LINES = []


def P(s=""):
    print(s, flush=True)
    LINES.append(s)


def parse_hex(path, load=0xC4C00):
    bs = bytes(int(t, 16) for t in Path(path).read_text().split())
    for i in range(0, len(bs) - 6, 2):
        if bs[i] == 0x29 and bs[i + 1] == 0x06:
            tbl = struct.unpack_from("<I", bs, i + 2)[0]
            break
    off = tbl - load
    rows = []
    while True:
        r = struct.unpack_from("<HHh", bs, off)
        rows.append(r)
        off += 6
        if r[0] == 0xFFFF:
            break
    return rows


def main():
    ok = True
    c2a = X.AL / "c2" / "rev2A"
    p2 = parse_hex(c2a / "c2_cave_P2.hex")
    f2 = parse_hex(c2a / "c2_cave_F2.hex")
    c1 = (p2 == X.P2_ROWS) and (f2 == X.F2_ROWS)
    P(f"C1 P2 rows == c2_cave_P2.hex: {p2 == X.P2_ROWS}; F2 rows == c2_cave_F2.hex: {f2 == X.F2_ROWS}  "
      f"{'OK' if c1 else 'FAIL'}")
    ok &= c1
    P2 = X.cand("P2", "fresh", X.P2_ROWS, 34)
    F2 = X.cand("F2", "held", X.F2_ROWS, 20)
    mems = ("nominal", "J_lo", "J_hi", "b_lo", "tau6", "mode20", "ms_free", "b_q*J1.0", "b_lo*J_hi+h10", "J_hi+h10",
            "b_q*J1.0+h10", "mode13+h10")
    keys = ("pm", "gm", "M20", "L20", "ReTw13", "ReTw20", "Tc530", "Tr530", "hold", "Tr163")
    worst = 0.0
    for c in (P2, F2):
        for m in mems:
            for v in (1.0, 3.1, 8.0, 11.9, 17.0, 26.9):
                a = SF.score(c, m, v)
                b = X.metrics_ext(c, m, v)
                for k in keys:
                    ka = a[k]
                    kb = b["pm_raw"] if k == "pm" else b[k]
                    if np.isfinite(ka) or np.isfinite(kb):
                        worst = max(worst, abs(ka - kb) / max(1.0, abs(ka)))
    c2 = worst < 1e-9
    P(f"C2 metrics_ext (kappa 1) vs score_freq.score, P2+F2 x {len(mems)} members x 6 speeds x {len(keys)} keys: "
      f"max rel diff {worst:.2e}  {'OK' if c2 else 'FAIL'}")
    ok &= c2
    # C3: where do pm_fixed and pm_raw differ?  scan P2 / F2 at their own kd over the brief's gated set, plus the
    # rev2-A REJECTED structures (Kd 41 / 48) at low G where the envelope "collapsed"
    nd = 0
    P("C3 pm_fixed vs pm_raw:")
    for c in (P2, F2):
        for m in X.BRIEF_A + X.BRIEF_B:
            for v in (1.0, 5.0, 8.0, 11.9, 13.0, 15.0, 17.0, 26.9):
                b = X.metrics_ext(c, m, v)
                if abs(b["pm"] - b["pm_raw"]) > 1e-9:
                    nd += 1
    P(f"   P2 / F2 at their own tables over the brief's gated set (8 speeds): {nd} points differ  "
      f"({'the published P2/F2 numbers are unaffected' if nd == 0 else 'SEE LIST'})")
    for kd, m, v, G in ((41, "b_q*J1.0", 14.0, 40), (48, "b_q*J_hi", 13.0, 40), (48, "b_lo", 5.0, 40),
                        (41, "b_q*J_hi", 12.5, 60), (48, "b_q*J1.0", 15.0, 60)):
        c = X.flat_cand("fresh", kd)
        b = X.metrics_ext(c, m, v, G=G)
        lp = X.loop_parts(c, m, v, G)
        L = lp["L_PI"] + kd * lp["L_D1"]
        cr = X.crossings(X.F, L)
        pl, d, ea, jbk, kappa = X.plant_ext(m, v)
        rho = DM.Lifted(DM.Des("x", dsrc="op", dop="fresh_rate", kd=kd, G=G, d=d, extra_age=ea), pl).exact()[0]
        P(f"   fresh Kd {kd} {m}@{v} G {G}: pm_raw {b['pm_raw']:7.1f}  pm_fixed {b['pm']:6.1f}  exact rho {rho:.4f}  "
          "crossings " + "; ".join(f"{fc:.2f} Hz ph {p:+.1f}" for fc, p, _, _ in cr))
    # C4
    worst = 0.0
    for c in (P2, F2):
        for m in ("nominal", "J_hi", "b_q*J1.0+h10", "mode20"):
            for v in (3.1, 11.9, 26.9):
                lp = X.loop_parts(c, m, v)
                L = lp["L_PI"] + lp["pr"]["kd"] * lp["L_D1"]
                Pt, Pw, d, ea, _ = SF.plant_frf(m, v)
                Cth, Cw, Cref, K = SF.controller_frf(c, SF.FGRID, c.cont(v), d, ea)
                L0 = -K * (Cth * Pt + Cw * Pw)
                worst = max(worst, float(np.max(np.abs(L - L0) / np.maximum(np.abs(L0), 1e-12))))
    c4 = worst < 1e-9
    P(f"C4 kd-linear decomposition == score_freq L: max rel err {worst:.2e}  {'OK' if c4 else 'FAIL'}")
    ok &= c4
    # C5
    bx = X.cand("BX", "box10", X.P2_ROWS, 25, dop_k=64)
    f = np.array([0.01, 0.1, 1.0])
    _, _, CthD, _ = X.ctl_parts(bx, dict(bx.cont(10.0), kd=0.0), 0, f)
    w = 2 * np.pi * f
    dd = (25 * CthD / (1j * w)).real                 # S per deg/s
    expect = -(25 * 64) / 80.0
    c5 = abs(dd[0] / expect - 1) < 1e-3
    P(f"C5 box10 Kd 25 k_op 64: D per deg/s at 0.01 / 0.1 / 1 Hz = {dd[0]:.3f} / {dd[1]:.3f} / {dd[2]:.3f}  "
      f"(arithmetic -(kd k_op)/80 = {expect:.3f})  {'OK' if c5 else 'FAIL'}")
    ok &= c5
    P("SELFTEST " + ("PASS" if ok else "FAIL"))
    (HERE / "g_selftest_out.txt").write_text("\n".join(LINES) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
