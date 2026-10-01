# -*- coding: utf-8 -*-
r"""h_freq.py -- FREQUENCY-DOMAIN GATE 2 for the two WHOLE-LOOP-RECONCILE implementations (designer H, 2026-10-01).

ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.  Ghidra not used here (bytes come from the traces;
cals from the V295 image via ds_model's LE reads).

It REUSES the orchestrator's engine unchanged -- ds_model (Des, loop_frf, metrics, re_tw, m20, V295) and ds_gate2
(member, GRID, TIER_A/B, PMBAR) -- so every number is produced by the SAME pipeline that scored the panel and that
the round-2 refuters validated byte-for-byte.  Nothing in ds_model/ds_gate2 is modified; this file only *builds Des
configs* and *drives the gate*, and it adds ONE thing the engine lacks: the measured P:D FRAME RATIO as a gated
uncertainty (refuter F2 / REFUTE-C2-r2-stability section 2).

THE TWO IMPLEMENTATIONS (decision-bearing difference = how F2, the P:D frame mismatch, is resolved):
  H-A  "motor-frame, fresh"  : P, I and D ALL close in the motor-linear frame (feedback gp-0x69ca, 1 kHz fresh;
                               D = fresh gp-0x6abe, guarded).  The intra-loop frame mismatch is ELIMINATED, so D is
                               scored in the SAME frame as P/I (no ratio spread on D).  The residual is the FORK's
                               SR map accuracy (a fork-side spec, not a GATE-2 member).  Cost: a fork SR correction.
  H-B  "corrected-frame, held": P and I close on gp-0x6a00 (corrected, = openpilot's own angle, NO fork change);
                               D = held gp-0x6a56 (motor frame).  The mismatch REMAINS, so the D operand per deg of
                               the corrected plant angle is Kd/slope with slope in [0.962, 1.155] -> Kd_eff in
                               [0.866, 1.040]*Kd.  BOTH ends are gated (refuter remedy section 5.1).

Both share: Kp 112 flat, raised ICL (frequency-invisible; a clamp), I FREEZE+BLEED on driver torque (cave; time
domain), the A2+B2 fail-safe guards, and a 7-knot speed-gain table fit under the full-factorial envelope.

usage:  python h_freq.py            # the gate, writes h_freq_out.txt
        python h_freq.py sweep       # Kd/Ki/table sensitivity
"""
from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]                                    # .../studies/angle_loop
for _p in (str(AL / "panel" / "D-structure"), str(AL / "c1"), str(AL.parent / "v295" / "plant"), str(AL)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ds_model as M          # noqa: E402  the shared engine (unmodified)
import ds_gate2 as G2         # noqa: E402  the brief's credible set + member()
import c1_lib as C            # noqa: E402  make_table / cave_G

OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(str(s))


# ---------------------------------------------------------------------------------------------------------------------
# the two tables (7-knot, fit under the full-factorial envelope).  H-A starts from the fresh-D env (D2a-class), H-B
# from the held-D env (B0r-class); both ALREADY carry 0 GATE-2 fails per SCORE-FREQ.  Designer H keeps them and layers
# the frame treatment + raised ICL + bleed on top (the F1/F2/F4 resolution), then re-gates.
# ---------------------------------------------------------------------------------------------------------------------
# verbatim from panel/score_freq.DS_ROWS (X u16 counts, G u16, S s16 Q12); the last row is the 0xFFFF sentinel.
TAB_FRESH = [(714, 1195, 1204), (1843, 1527, -7988), (2304, 628, -925), (2707, 537, 2773), (3571, 1122, 2941),
             (4032, 1453, 1278), (6198, 2129, 0), (0xFFFF, 2129, 0)]                      # D2a env (fresh D)
TAB_HELD = [(714, 1187, 896), (1843, 1434, -6388), (2304, 715, -1779), (2707, 540, 2489), (3571, 1065, 2781),
            (4032, 1378, 1297), (6198, 2064, 0), (0xFFFF, 2064, 0)]                        # B0r env (held D)


def G_of(tbl):
    def f(v):
        return float(C.cave_G(C.spd_counts(v), tbl))
    return f


def des_HA(kd=34, ki=56, kp=112, tbl=TAB_FRESH):
    """H-A: fresh gp-0x6abe D, motor-frame (scored single-frame: no D ratio spread)."""
    g = G_of(tbl)
    return lambda v: replace(M.Des(name="H-A"), kind="angle", dsrc="op", dop="fresh_rate",
                             kp=kp, ki=ki, kd=kd, G=g(v))


def des_HB(kd=23, ki=56, kp=112, tbl=TAB_HELD, dop_k=1.0):
    """H-B: held gp-0x6a56 D, corrected-frame.  dop_k applies the frame ratio to the held D (0.866 = near-centre
    worst, 1.040 = outward)."""
    g = G_of(tbl)
    # dsrc='rate_held' has no dop_k in the engine, so fold the ratio into kd (D is linear in kd): kd_eff = kd*dop_k.
    return lambda v: replace(M.Des(name="H-B"), kind="angle", dsrc="rate_held",
                             kp=kp, ki=ki, kd=kd * dop_k, G=g(v))


# ---------------------------------------------------------------------------------------------------------------------
# the gate (same bars as ds_gate2 / the brief)
# ---------------------------------------------------------------------------------------------------------------------
GRID = sorted(set([round(x, 2) for x in np.arange(2.0, 30.01, 0.5)] + [3.1, 8.0, 10.0, 11.75, 11.9, 12.5, 15.5, 17.0,
                                                                       26.9]))
AGES = (0, 10)


def gate(desf, members=G2.GATED, grid=GRID, ages=AGES, label="", convention="strict"):
    """Returns (fails, rows). fail = PM<bar (tier A 45, B 30) / GM<6 / 5-30 peak>+3 dB.  M20/ReTw20 are a separate
    member-independent controller rule (d=2).  convention='strict' = brief literal (aged singles stay tier A, ms_free
    gated tier A); 'panel' = the panel's reading (aged singles -> 30 deg, ms_free report-only, per refuter F6)."""
    fails = []
    worst = {}
    retw = {13: 9e9, 16: 9e9, 20: 9e9}
    for name in members:
        bar = G2.PMBAR.get(name, 30.0)
        if convention == "panel":
            if name.startswith("ms_free"):
                continue                                   # report-only (J 2.08 > 1.3 bound)
            if name.endswith("+h10") and name[:-4] in G2.TIER_A:
                bar = 30.0                                 # aged single -> stacked uncertainty -> tier B bar
        for v in grid:
            pl, d, ea0, (J, b, k) = G2.member(name, v)
            for age in ages:
                des = desf(v)
                des = replace(des, d=d, extra_age=ea0 + age)
                r = M.metrics(des, pl)
                pm = r["pm"]
                peak = max(r.get("Tc530", -99), r.get("Tr530", -99))
                bad = []
                if not (pm >= bar):
                    bad.append(f"PM {pm:.1f}<{bar:.0f}")
                if not (r["gm_lti"] >= 6.0):
                    bad.append(f"GM {r['gm_lti']:.1f}")
                if peak > 3.0:
                    bad.append(f"peak {peak:.1f}dB")
                if bad:
                    fails.append((name, v, age, "; ".join(bad), r["fc"]))
                key = G2.tier(name)
                if (key, age) not in worst or pm < worst[(key, age)][0]:
                    worst[(key, age)] = (pm, name, v, r["fc"])
    # controller-only 20 Hz rules (member-independent), at nominal transport d=2, ages 0 and 10, vs V295's reported
    rule_fail = []
    for v in grid:
        for age in ages:
            des = replace(desf(v), d=2, extra_age=age)
            ref = replace(M.V295, extra_age=age, rate_model=des.rate_model, d=2)
            if M.m20(des) > M.m20(ref) * (1 + 1e-9):
                rule_fail.append((v, age, f"M20 {M.m20(des):.2f}>{M.m20(ref):.2f}"))
            if M.re_tw(des, 20.0)[0] < M.re_tw(ref, 20.0)[0] - 1e-9:
                rule_fail.append((v, age, f"ReTw20 {M.re_tw(des,20.0)[0]:+.2f}<{M.re_tw(ref,20.0)[0]:+.2f}"))
    # controller-only HF numbers at nominal (member-independent) age 0
    d0 = desf(17.0)
    for f in (13, 16, 20):
        retw[f] = float(M.re_tw(replace(d0, extra_age=0), float(f))[0])
    pr(f"\n==== {label} ====")
    pr(f"  GATE-2 member fails: {len(fails)} ; controller-rule (M20/ReTw20 @d=2) fails: {len(rule_fail)}")
    for (nm, v, age, why, fc) in fails[:40]:
        pr(f"    {nm:14s} v={v:5.2f} age{age:2d}  {why}  (fc~{fc:.2f}Hz)")
    for (v, age, why) in rule_fail[:8]:
        pr(f"    RULE          v={v:5.2f} age{age:2d}  {why}")
    for (key, age), (pm, nm, v, fc) in sorted(worst.items()):
        pr(f"  worst tier-{key} age{age:2d}: PM {pm:5.1f} @ {nm} {v} (fc~{fc:.2f}Hz)")
    pr(f"  ReTw (ctrl, age0, v=17): 13Hz {retw[13]:+.2f}  16Hz {retw[16]:+.2f}  20Hz {retw[20]:+.2f}   "
       f"(V295 -0.47/-0.73/-0.82)")
    # turn-hold |T_ref(0.05 Hz)| worst >=8 m/s and tracking
    th = []
    for v in [x for x in grid if x >= 8.0]:
        pl, d, ea0, _ = G2.member("nominal", v)
        r = M.metrics(replace(desf(v), d=d, extra_age=0), pl)
        th.append(r.get("hold", float("nan")))
    pr(f"  turn-hold |Tref(0.05Hz)| worst>=8 m/s: {min(th):.3f} (goal>=0.90, FREQUENCY proxy; the CLAMP is time-domain)")
    return fails, worst


# low-speed-trimmed tables: pull the first knot's G down ~12% (raises PM / GM at 2-8 m/s; I carries the low-speed DC)
TAB_FRESH_LS = [(714, 1050, 1397), (1843, 1527, -7988), (2304, 628, -925), (2707, 537, 2773), (3571, 1122, 2941),
                (4032, 1453, 1278), (6198, 2129, 0), (0xFFFF, 2129, 0)]
TAB_HELD_LS = [(714, 1040, 1037), (1843, 1434, -6388), (2304, 715, -1779), (2707, 540, 2489), (3571, 1065, 2781),
               (4032, 1378, 1297), (6198, 2064, 0), (0xFFFF, 2064, 0)]


def main():
    pr("WHOLE-LOOP-RECONCILE (designer H) -- frequency GATE 2 on the brief's credible set")
    pr(f"members={len(G2.GATED)} speeds={len(GRID)} ages={AGES}")
    pr("\nReference (same engine): V295 M20 %.3f  ReTw13/16/20 %.2f/%.2f/%.2f" % (
        M.m20(M.V295), M.re_tw(M.V295, 13.0)[0], M.re_tw(M.V295, 16.0)[0], M.re_tw(M.V295, 20.0)[0]))

    for conv in ("strict", "panel"):
        pr(f"\n################ convention = {conv} ################")
        gate(des_HA(kd=34, ki=56), convention=conv, label="H-A fresh-D motor-frame, Kd34 Ki56 (single-frame)")
        gate(des_HA(kd=34, ki=56, tbl=TAB_FRESH_LS), convention=conv,
             label="H-A' fresh-D, Kd34 Ki56, LOW-SPEED-TRIMMED table")
        gate(des_HB(kd=23, ki=56, dop_k=0.866), convention=conv,
             label="H-B held-D corrected, Kd23 Ki56, FA near-centre (D x0.866)")
        gate(des_HB(kd=23, ki=56, dop_k=1.040), convention=conv,
             label="H-B held-D corrected, Kd23 Ki56, outward (D x1.040)")
        gate(des_HB(kd=23, ki=56, dop_k=0.866, tbl=TAB_HELD_LS), convention=conv,
             label="H-B' held-D corrected, Kd23 Ki56 FA, LOW-SPEED-TRIMMED table")

    (HERE / "h_freq_out.txt").write_text("\n".join(OUT), encoding="utf-8")
    pr("\nwrote h_freq_out.txt")


if __name__ == "__main__":
    main()
