# -*- coding: utf-8 -*-
r"""r2a_refute_rerun.py -- the STABILITY REFUTER'S OWN independent model (refute_stability/refute_c1_ind.py: its own
ZOH discretisation, its own loop assembly, its own crossover finder, its own member re-implementation) and its own
attack lists (refute_c1_run.py ATTACK 1-4, refute_c1_stage2.py's ring / R3-coverage stage), re-run on this reviser's
implementations.  The MINIMUM patch, listed here and nowhere else:
  * table and immediates: KP_BASE 112, KI_BASE 56, the implementation's own G table (the refuter's model reads them from
    c1_lib; here they are passed per implementation);
  * design P only: the D term's operand.  The refuter's model has Comega = Kd * hold (held, ideal rate, S per deg/s).
    Design P's D is (Kd/8) * gp-0x6abe with gp-0x6abe = -4.712 counts per deg/s through the 37/128 EMA and NO hold:
    Comega_P = (Kd/8) * 4.712 * EMA(z).  Everything else in the refuter's model is untouched.
Also the refuter's own anchor() is run first: it must reproduce its published C0 / C1 anchors (a positive control that
the model in this process is the refuter's model).
ANALYSIS ONLY.   usage: python r2a_refute_rerun.py      (writes r2a_refute_rerun_out.txt)"""
from __future__ import annotations

import contextlib
import io
import math

import numpy as np

import os
os.environ["C1_VARIANT"] = "kd16"          # the refuter wrote its anchors against C1 rev 1 (c1_lib variant kd16)
import r2a_common as R

import refute_c1_ind as RI  # noqa: E402

ALPHA = 37.0 / 128.0


def loop_L_impl(impl, G, disc, f, d=2, age=0):
    """refute_c1_ind.loop_L verbatim, with Comega swapped for design P's fresh-EMA operand."""
    kd = R.des_of(impl).kd
    if R.des_of(impl).dsrc != "op":
        return RI.loop_L(G, 112, 56, kd, disc, f, d=d, age=age)
    z = np.exp(1j * 2 * np.pi * np.asarray(f, float) * RI.TS)
    zi = 1 / z
    hold = sum(zi ** (a + age) for a in range(1, 11)) / 10.0
    Hout = (RI.OB / 1024) * (1 + zi) / (32 * (1 - (RI.OA / 1024) * zi))
    K = RI.FADE * RI.FWD * Hout * zi ** d
    g = G / 256.0
    PI = 112 / 256.0 + (56 / 32768.0) / (1 - zi)
    Ctheta = g * PI * 80 * (1 + zi) * hold
    ema = ALPHA / (1 - (1 - ALPHA) * zi)
    Comega = (kd / 8.0) * 4.712 * ema
    Pt, Pw = RI.plant_frf(disc, f)
    return K * (Ctheta * Pt + Comega * Pw)


def margins_impl(impl, tbl, name, v, extra_age=0):
    J, b, k, d, age = RI.member_params(name, v)
    disc = RI.rigid_disc(J, b, k)
    G = R.G_at(v, tbl)
    f = np.logspace(math.log10(0.02), math.log10(120.0), 3200)
    L = loop_L_impl(impl, G, disc, f, d=d, age=age + extra_age)
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L)) * 180 / math.pi
    pms = []
    for i in range(len(f) - 1):
        if (mag[i] - 1) * (mag[i + 1] - 1) <= 0 and mag[i] != mag[i + 1]:
            t = (1 - mag[i]) / (mag[i + 1] - mag[i])
            p = ph[i] + t * (ph[i + 1] - ph[i])
            pms.append(((p + 180) + 180) % 360 - 180)
    gms = []
    for i in range(len(f) - 1):
        w0, w1 = (ph[i] + 180) / 360, (ph[i + 1] + 180) / 360
        if math.floor(w0) != math.floor(w1):
            t = (math.floor(max(w0, w1)) - w0) / (w1 - w0) if w1 != w0 else 0
            m = mag[i] + t * (mag[i + 1] - mag[i])
            gms.append(-20 * math.log10(max(m, 1e-12)))
    T = L / (1 + L)
    band = (f >= 0.5) & (f <= 30)
    S = 1 / (1 + L)
    return (min(pms) if pms else float("nan"), min([g for g in gms if g > 0], default=float("inf")),
            float(np.abs(T[band]).max()), float(f[band][np.argmax(np.abs(T[band]))]), float(f[np.argmax(np.abs(S))]))


def main():
    lines = []

    def P(s=""):
        print(s, flush=True)
        lines.append(s)

    buf = io.StringIO()
    import refute_c1_run as RR
    with contextlib.redirect_stdout(buf):
        RR.anchor()
    P("REFUTER'S OWN ANCHOR (positive control: the refuter's model in this process reproduces its published numbers):")
    for ln in buf.getvalue().splitlines():
        if ln.strip():
            P("  " + ln)
    vg = RR.fine_grid()
    tabs = R.tables()
    attacks = [
        ("ATTACK 1 tier A single corners (bar 45)", 45.0, ["nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6",
                                                          "F_hi", "F_lo", "ms_free"], 0),
        ("ATTACK 2 tier B combined, age 0 (bar 30)", 30.0, ["b_lo*J_hi", "b_lo*J_hi*tau6", "b_lo*tau6", "J_hi*tau6",
                                                           "b/1.9*J_hi", "b_lo*J0.3", "J_hi2", "J1.0", "b_q",
                                                           "nominal+h10", "b_lo+h10", "J_hi+h10"], 0),
        ("ATTACK 3 combined + 10-tick hold age (bar 30)", 30.0, ["b_lo*J_hi+hA", "b_lo*J_hi*tau6+hA", "J_hi2+hA",
                                                                 "J1.0+hA", "b_q+hA", "b/1.9*J_hi+hA"], 0),
        ("ATTACK 4 extra combined (bar 30)", 30.0, ["b_q*J_hi", "b_q*J1.0", "b_q*tau6", "J1.0*tau6", "b_q0*J_hi"], 0),
        ("ATTACK 4 aged (bar 30)", 30.0, ["b_q*J_hi", "b_q*J1.0", "b_q*tau6", "J1.0*tau6", "b_q0*J_hi"], 10),
    ]
    for impl in ("P1", "P2", "F1", "F2"):
        P("=" * 116)
        P(f"{impl}: {R.IMPLS[impl]['note']}")
        nsub = 0
        for title, bar, mems, ea in attacks:
            P(f"  --- {title}")
            for nm in mems:
                best = (1e9, None, None)
                nb = 0
                for v in vg:
                    try:
                        pm, gm, tpk, fpk, fS = margins_impl(impl, tabs[impl], nm, v, extra_age=ea)
                    except KeyError:
                        continue
                    if not math.isfinite(pm):
                        continue
                    if pm < bar:
                        nb += 1
                    if pm < best[0]:
                        best = (pm, v, (gm, tpk, fpk, fS))
                nsub += nb
                g = best[2]
                P(f"     {nm:22s} min PM {best[0]:6.1f} @ {best[1]:<6}  GM {g[0]:5.1f} dB  |T| 0.5-30 pk {g[1]:.2f} @ "
                  f"{g[2]:.2f} Hz  |S| pk @ {g[3]:.2f} Hz  sub-bar points {nb}" + ("   <<< BELOW BAR" if nb else ""))
        P(f"  => {impl}: sub-bar points over every attack {nsub}")
    (R.HERE / "r2a_refute_rerun_out.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
