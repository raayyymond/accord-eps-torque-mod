# -*- coding: utf-8 -*-
r"""score_freq.py -- THE COMMON FREQUENCY-DOMAIN SCORER for the angle-loop design panel (2026-10-01).

ANALYSIS ONLY.  Builds nothing, flashes nothing, sends nothing.  The orchestrator's independent scorer: every candidate
(A1, A2, B1, B2, B3, CGF-1, CGF-2, CGF-1b, B0r, D1a-D3b) is driven through ONE identical pipeline -- the same controller
FRF construction primitives, the same plant family (c1r2_members via ds_gate2.member), the same credible member set and
0.25 m/s speed grid (incl. the plant knots), the same hold ages {0, 10} (= holds 1-10 and 11-20), and the SAME metrics
extractor (PM = min over every |L|=1 crossing, LTI GM at -180, Ms, |Tc|/|Tr| 5-30 dB, M20, L20, Re(T/w), |Tref| 1.6-3,
turn-hold, DC stiffness).  Designers graded their own work; this file does not -- it re-derives each loop from the spec.

Engine provenance (EVIDENCE): the controller FRF is built here from the lane bytes/cals, reusing ds_model's image-read
cals (OA 992, OB 507, FWD 5346/32768, FADE 254/256) and sensor scales (gp-0x6abe EMA alpha 37/128 = 54.3 Hz, EVIDENCE
cal 0xC643C=37 and FUN_00041464; gp-0x6abe -4.712 counts/deg-s; gp-0x6cc4 -278.5 counts/deg).  The angle-kind
controller FRF is a re-implementation here (with an op_hold flag the shared base lacked) VALIDATED == ds_model._ctl_frf
to < 1e-9 on a held sample; cascade/rate kinds route through ds_model.ctl_frf; plant_frf and the member set come from the
D-structure gate module (= the brief's full factorial).  V295/V294/V282 are scored with the identical extractor.

usage:  python score_freq.py            (full run: writes the JSON caches + prints the table)
        python score_freq.py quick      (headline members only, faster smoke test)
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

HERE = Path(__file__).resolve().parent                        # .../studies/angle_loop/panel
AL = HERE.parent                                              # .../studies/angle_loop
for _p in (str(HERE / "D-structure"), str(AL / "c1"), str(AL / "refute_stability"),
           str(AL.parent / "v295" / "plant"), str(AL)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ds_model as DM            # noqa: E402  the shared structural engine (image cals, plant frf, cascade/rate kinds)
import ds_gate2 as G2            # noqa: E402  the brief's full-factorial credible set + member() + GRID
import c1_lib as C              # noqa: E402  make_table / cave_G (the integer speed-gain walk)

TS = 1e-3
ALPHA = DM.ALPHA                 # 37/128, gp-0x6abe EMA (54.3 Hz)
ABE_PER = DM.ABE_PER             # -4.712 counts per deg/s
D_PER = DM.D_PER                 # -278.5 counts per deg (gp-0x6cc4 near centre)
OA, OB, FWD, FADE = DM.OA, DM.OB, DM.FWD, DM.FADE

OUT = AL.parent.parent / "_scratch" / "angle_loop" / "panel"   # repo-root scratch (AL.parent = analysis-2020accord)
OUT.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------------------------------------------------
# FREQUENCY GRID (dense; the 20/13/16 Hz and 1.6-3 Hz lines pinned so the band maxima land on a sample)
# ----------------------------------------------------------------------------------------------------------------------
FGRID = np.unique(np.concatenate([
    np.logspace(-2.3, math.log10(499.0), 2600),
    [0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 1.6, 2.0, 2.5, 3.0, 5.0, 7.0, 10.0, 13.0, 15.0, 16.0, 17.0, 20.0, 25.0, 30.0]]))
_I20 = int(np.argmin(abs(FGRID - 20.0)))


def _z(f):
    return np.exp(-2j * np.pi * np.asarray(f, float) * TS)


def _H(f, ea):
    z = _z(f)
    return np.mean([z ** (a + ea) for a in range(1, 11)], axis=0)


def _ema(f):
    z = _z(f)
    return ALPHA / (1 - (1 - ALPHA) * z)


def _Hout(f):
    z = _z(f)
    return (OB / 1024.0) * (1 + z) / (32.0 * (1 - (OA / 1024.0) * z))


def K_out(f, d):
    return FADE * FWD * _Hout(f) * _z(f) ** d


# ----------------------------------------------------------------------------------------------------------------------
# CANDIDATE DESCRIPTION.  cont(v) -> dict(G, kp, ki, kd) at that speed (controller params; member independent).
# struct fields fix the loop STRUCTURE (identical across speeds).  rate_model='ema' (firmware-evidenced) for every D.
# ----------------------------------------------------------------------------------------------------------------------
@dataclass
class Cand:
    cid: str
    designer: str
    kind: str = "angle"              # 'angle' | 'cascade' | 'rate'
    dsrc: str = "rate_held"          # angle: 'none'|'rate_held'|'E'|'op'
    dop: str = ""                    # 'fine'|'held_lp'|'fresh_rate'
    dop_k: float = 1.0
    lp_beta: float = 0.0
    lead: str = ""                   # ''|'fwd'|'fb'
    lead_beta: float = 1.0 / 16.0
    lead_kh: float = 1.0
    op_hold: str = "held"            # angle P/I operand: 'held' (100 Hz) | 'fresh' (1 kHz rebuilt)
    # cascade:
    casc_kp: float = 24.0
    casc_ki: float = 12.0
    casc_fa: float = 923.0
    casc_fb: float = 1560.0
    casc_ka: float = 4.0
    casc_cop: str = "held"
    cont: callable = None            # v -> dict(G, kp, ki, kd)
    note: str = ""


# ------------------------- speed-gain tables (the cave walks) and re-key schedules -------------------------
def cave_cont(knots, kp_base, ki_base, kd):
    tbl = C.make_table(knots)

    def f(v):
        G = float(C.cave_G(C.spd_counts(v), tbl))
        return dict(G=G, kp=kp_base, ki=ki_base, kd=kd)
    return f


def cave_cont_rows(rows, kp_base, ki_base, kd):
    """rows = explicit (X,G,S) table rows incl. the 0xFFFF sentinel (the D-structure candidates give these directly)."""
    tbl = [tuple(r) for r in rows]

    def f(v):
        G = float(C.cave_G(C.spd_counts(v), tbl))
        return dict(G=G, kp=kp_base, ki=ki_base, kd=kd)
    return f


def rekey_cont(kpX, kpY, kiflat, kiX, kiY, kdX, kdY):
    """A1/A2: no cave (G=256); Kp_eff/Ki_eff/Kd scheduled on key = speed>>8 (= v * 230.4 / 256 counts)."""
    def f(v):
        key = v * 3.6 * 64 / 256.0
        kp = float(np.interp(key, kpX, kpY))
        ki = kiflat if kiflat is not None else float(np.interp(key, kiX, kiY))
        kd = float(np.interp(key, kdX, kdY))
        return dict(G=256.0, kp=kp, ki=ki, kd=kd)
    return f


# D-structure candidate tables (X,G,S rows), read verbatim from the task spec's cals (same make_table format)
DS_ROWS = {
    "B0r": [(714, 1187, 896), (1843, 1434, -6388), (2304, 715, -1779), (2707, 540, 2489), (3571, 1065, 2781),
            (4032, 1378, 1297), (6198, 2064, 0), (0xFFFF, 2064, 0)],
    "D1a": [(714, 1326, 0), (1843, 1326, -6042), (2304, 646, -2510), (2707, 399, 3921), (3571, 1226, 889),
            (4032, 1326, 0), (6198, 1326, 0), (0xFFFF, 1326, 0)],
    "D1b": [(714, 1217, 1121), (1843, 1526, -7970), (2304, 629, -935), (2707, 537, 2830), (3571, 1134, 2932),
            (4032, 1464, 1293), (6198, 2148, 0), (0xFFFF, 2148, 0)],
    "D1c": [(714, 1164, 889), (1843, 1409, -6388), (2304, 690, -1514), (2707, 541, 2361), (3571, 1039, 2674),
            (4032, 1340, 1326), (6198, 2041, 0), (0xFFFF, 2041, 0)],
    "D2a": [(714, 1195, 1204), (1843, 1527, -7988), (2304, 628, -925), (2707, 537, 2773), (3571, 1122, 2941),
            (4032, 1453, 1278), (6198, 2129, 0), (0xFFFF, 2129, 0)],
    "D2b": [(714, 1501, 1070), (1843, 1796, -10307), (2304, 636, -589), (2707, 578, 3162), (3571, 1245, 3323),
            (4032, 1619, 1615), (6198, 2473, 0), (0xFFFF, 2473, 0)],
    "D2c": [(714, 1426, 954), (1843, 1689, -8761), (2304, 703, -1403), (2707, 565, 2987), (3571, 1195, 2959),
            (4032, 1528, 1551), (6198, 2348, 0), (0xFFFF, 2348, 0)],
    "D3a": [(714, 993, 203), (1843, 1049, -2372), (2304, 782, -2571), (2707, 529, 2067), (3571, 965, 2994),
            (4032, 1302, 1677), (6198, 2189, 0), (0xFFFF, 2189, 0)],
    "D3b": [(714, 851, 453), (1843, 976, -2888), (2304, 651, -2002), (2707, 454, 1555), (3571, 782, 1821),
            (4032, 987, 1095), (6198, 1566, 0), (0xFFFF, 1566, 0)],
}

# B-designer knots (b_gate.py IMPL)
B1_KNOTS = [(3.1, 952), (8.0, 1321), (10.0, 855), (11.9, 699), (15.5, 1044), (26.9, 2041)]
B2_KNOTS = [(3.1, 1106), (8.0, 1475), (10.0, 989), (11.9, 826), (15.5, 1213), (26.9, 2241)]
B3_KNOTS = [(3.1, 1690), (8.0, 1805), (10.0, 1357), (11.9, 1162), (15.5, 1366), (26.9, 2765)]
# CGF knots (cgf_design.py)
CGF_KNOTS = [(3.1, 1268), (8.0, 1576), (10.0, 1211), (12.0, 1131), (15.5, 1486), (19.0, 1908), (26.9, 2468)]

# A1/A2 re-key schedules (task spec cals; key = speed>>8)
A1_KPX, A1_KPY = (2, 7, 10, 15, 24), (411, 561, 330, 536, 883)
A1_KDX, A1_KDY = (2, 7, 15, 24), (20, 18, 14, 10)
A2_KPY = (296, 404, 238, 386, 636)
A2_KIX, A2_KIY = (2, 7, 10, 15, 24), (148, 202, 119, 193, 318)


CANDS = [
    Cand("A1-zero-cave", "fewest bytes", kind="angle", dsrc="rate_held",
         cont=rekey_cont(A1_KPX, A1_KPY, 80, None, None, A1_KDX, A1_KDY),
         note="zero cave; re-key Kp(speed), flat Ki 80, held-rate D"),
    Cand("A2-ki-cave", "fewest bytes", kind="angle", dsrc="rate_held",
         cont=rekey_cont(A1_KPX, A2_KPY, None, A2_KIX, A2_KIY, A1_KDX, A1_KDY),
         note="A1 + Ki cave (Ki=0.5 Kp), 0.72x Kp envelope, held-rate D"),
    Cand("B1-robust-gaincut", "robust margins", kind="angle", dsrc="rate_held",
         cont=cave_cont(B1_KNOTS, 112, 56, 20), note="held-rate D Kd20, I-freeze, 6-knot gaincut"),
    Cand("B2-freshD-lead", "robust margins", kind="angle", dsrc="op", dop="fresh_rate",
         cont=cave_cont(B2_KNOTS, 112, 56, 41),
         note="FRESH gp-0x6abe D, cal 41 (Kd_eff 24); designer used 40 Hz EMA, scorer uses firmware 37/128 (54.3 Hz)"),
    Cand("B3-noI-forkDC", "robust margins", kind="angle", dsrc="rate_held",
         cont=cave_cont(B3_KNOTS, 112, 0, 20), note="Ki=0 (no firmware I), held-rate D Kd20, highest Kp"),
    Cand("CGF-1", "goal first", kind="angle", dsrc="op", dop="fresh_rate",
         cont=cave_cont(CGF_KNOTS, 112, 56, 48),
         note="FRESH gp-0x6abe D, cal 48 (Kd_eff 28), higher highway Kp"),
    Cand("CGF-2", "goal first", kind="angle", dsrc="op", dop="fresh_rate",
         cont=cave_cont(CGF_KNOTS, 112, 56, 48),
         note="= CGF-1 in the freq domain; the friction FF is a time-domain dead-zone break (not a freq lever)"),
    Cand("CGF-1b", "goal first", kind="angle", dsrc="op", dop="fresh_rate", op_hold="fresh",
         cont=cave_cont(CGF_KNOTS, 112, 56, 48),
         note="CGF-1 + FRESH 1 kHz operand (no 100 Hz P/I hold); scored on CGF-1's table (designer notes gain can rise)"),
    Cand("B0r", "D-structure", kind="angle", dsrc="rate_held",
         cont=cave_cont_rows(DS_ROWS["B0r"], 112, 56, 20), note="C1r2 structure refit (baseline, held-rate D Kd20)"),
    Cand("D1a", "D-structure", kind="angle", dsrc="E",
         cont=cave_cont_rows(DS_ROWS["D1a"], 112, 56, 256), note="stock D on E' (cal-only), Kd_E 256"),
    Cand("D1b", "D-structure", kind="angle", dsrc="op", dop="fine", dop_k=8,
         cont=cave_cont_rows(DS_ROWS["D1b"], 112, 56, 72), note="D on gp-0x6cc4 1 kHz accumulator diff, Kd 72"),
    Cand("D1c", "D-structure", kind="angle", dsrc="op", dop="held_lp", dop_k=8, lp_beta=1.0 / 8,
         cont=cave_cont_rows(DS_ROWS["D1c"], 112, 56, 250), note="D on held-angle diff via 21 Hz LP, Kd 250"),
    Cand("D2a", "D-structure", kind="angle", dsrc="op", dop="fresh_rate",
         cont=cave_cont_rows(DS_ROWS["D2a"], 112, 56, 34), note="D on fresh gp-0x6abe EMA, Kd 34"),
    Cand("D2b", "D-structure", kind="angle", dsrc="op", dop="fresh_rate", lead="fwd", lead_beta=1.0 / 16, lead_kh=1,
         cont=cave_cont_rows(DS_ROWS["D2b"], 112, 56, 34), note="D2a + forward-path output-lag lead on E' (P only)"),
    Cand("D2c", "D-structure", kind="angle", dsrc="op", dop="fresh_rate", lead="fb", lead_beta=1.0 / 16, lead_kh=1,
         cont=cave_cont_rows(DS_ROWS["D2c"], 112, 56, 34), note="D2a + feedback-path lead on r26 (P and I)"),
    Cand("D3a", "D-structure", kind="cascade", casc_kp=24, casc_ki=12, casc_fa=923, casc_fb=1560, casc_ka=4.0,
         casc_cop="held", cont=cave_cont_rows(DS_ROWS["D3a"], 24, 12, 0), note="cascade, HELD inner rate loop"),
    Cand("D3b", "D-structure", kind="cascade", casc_kp=46, casc_ki=12, casc_fa=923, casc_fb=1560, casc_ka=4.0,
         casc_cop="fresh", cont=cave_cont_rows(DS_ROWS["D3b"], 46, 12, 0), note="cascade, FRESH inner rate loop"),
]
PLACEHOLDERS = ["E-none-1", "E-none-2"]      # E-integral-and-handover halted; no design produced


# ----------------------------------------------------------------------------------------------------------------------
# CONTROLLER FRF (angle kind re-implemented here with op_hold; cascade/rate via ds_model).  Returns Cth, Cw, Cref.
# ----------------------------------------------------------------------------------------------------------------------
def ctl_angle(f, cand: Cand, pr, ea):
    """pr = dict(G, kp, ki, kd) at this speed.  Mirrors ds_model._ctl_frf (angle) + op_hold; validated == ds_model."""
    z = _z(f)
    H = _H(f, ea)
    ema = _ema(f)
    g = pr["G"] / 256.0
    Hop = H if cand.op_hold == "held" else np.ones_like(z)
    r26_th = 80 * (1 + z) * Hop
    if cand.lead:
        Lf = 1 + cand.lead_kh * (1 - cand.lead_beta / (1 - (1 - cand.lead_beta) * z))
    else:
        Lf = np.ones_like(z)
    if cand.lead == "fb":
        r26_th = Lf * r26_th
    E_th, E_ref = -r26_th, 160.0 * np.ones_like(z)
    Ep_th, Ep_ref = g * E_th, g * E_ref
    LP = Lf if cand.lead == "fwd" else np.ones_like(z)
    kp, ki, kd = pr["kp"], pr["ki"], pr["kd"]
    Cth = (kp / 256.0) * LP * Ep_th + (ki / 32768.0) / (1 - z) * Ep_th
    Cref = (kp / 256.0) * LP * Ep_ref + (ki / 32768.0) / (1 - z) * Ep_ref
    Cw = np.zeros_like(z)
    kd8 = kd / 8.0
    if cand.dsrc == "rate_held":                       # D = -Kd * H * omega (rate_model ema: Rth=0, Rw=ema)
        Cw = Cw - kd * H * ema
    elif cand.dsrc == "E":                             # D = Kd/8 (E'[n]-E'[n-1])
        Cth = Cth + kd8 * (1 - z) * LP * Ep_th
        Cref = Cref + kd8 * (1 - z) * LP * Ep_ref
    elif cand.dsrc == "op":
        if cand.dop == "fresh_rate":                   # op = gp-0x6abe (-4.712/deg/s) EMA
            Cw = Cw + kd8 * cand.dop_k * ABE_PER * ema
        elif cand.dop == "fine":                       # op = d[n]-d[n-1] = D_PER (1-z) theta
            Cth = Cth + kd8 * cand.dop_k * D_PER * (1 - z)
        elif cand.dop == "held_lp":
            lp = cand.lp_beta / (1 - (1 - cand.lp_beta) * z)
            Cth = Cth - kd8 * cand.dop_k * lp * 80 * (1 - z) * H
        else:
            raise ValueError(cand.dop)
    elif cand.dsrc != "none":
        raise ValueError(cand.dsrc)
    # the 0xE4 setpoint is a 100 Hz hold (sp_hold): age 1..10 on the reference path
    Cref = Cref * np.mean([z ** a for a in range(1, 11)], axis=0)
    return Cth, Cw, Cref


def controller_frf(cand: Cand, f, pr, d, ea):
    if cand.kind == "angle":
        Cth, Cw, Cref = ctl_angle(f, cand, pr, ea)
        K = K_out(f, d)
        return Cth, Cw, Cref, K
    if cand.kind == "cascade":
        des = DM.Des(kind="cascade", kp=cand.casc_kp, ki=cand.casc_ki, fa=cand.casc_fa, fb=cand.casc_fb,
                     ka=cand.casc_ka, cop=cand.casc_cop, G=pr["G"], d=d, extra_age=ea, dsrc="none")
        Cth, Cw, Cref = DM.ctl_frf(f, des)
        K = DM.K_out(f, des)
        return Cth, Cw, Cref, K
    raise ValueError(cand.kind)


def des_for_ref(name):
    return {"V295": DM.V295, "V294": DM.V294, "V282": DM.V282}[name]


def ref_ctl_frf(name, f, d, ea):
    des = replace(des_for_ref(name), d=d, extra_age=ea)
    Cth, Cw, Cref = DM.ctl_frf(f, des)
    K = DM.K_out(f, des)
    return Cth, Cw, Cref, K


# ----------------------------------------------------------------------------------------------------------------------
# THE SINGLE METRICS EXTRACTOR (identical for every candidate AND the references)
# ----------------------------------------------------------------------------------------------------------------------
def _pm_all(f, L):
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L)) * 180 / np.pi
    pms, fcs = [], []
    for i in np.where((mag[:-1] - 1) * (mag[1:] - 1) <= 0)[0]:
        if mag[i] == mag[i + 1]:
            continue
        t = (1 - mag[i]) / (mag[i + 1] - mag[i])
        pms.append(((ph[i] + t * (ph[i + 1] - ph[i])) + 180 + 180) % 360 - 180)
        fcs.append(f[i] + t * (f[i + 1] - f[i]))
    return pms, fcs


def _gm_lti(f, L):
    ph = np.unwrap(np.angle(L)) * 180 / np.pi
    mag = np.abs(L)
    gms = []
    for i in range(len(f) - 1):
        if math.floor((ph[i] + 180) / 360) != math.floor((ph[i + 1] + 180) / 360):
            gms.append(-20 * math.log10(max(mag[i], 1e-12)))
    pos = [g for g in gms if g > 0]
    return min(pos) if pos else float("inf")


def metrics_from(Cth, Cw, Cref, K, Pt, Pw, f=FGRID, want_ref=True):
    L = -K * (Cth * Pt + Cw * Pw)
    S = 1.0 / (1.0 + L)
    Tc = L * S
    pms, fcs = _pm_all(f, L)
    band = lambda lo, hi: (f >= lo) & (f <= hi)  # noqa: E731
    w20 = 2 * np.pi * 20.0
    out = dict(pm=(min(pms) if pms else float("nan")),
               fc=(fcs[int(np.argmin(pms))] if pms else float("nan")),
               n_cross=len(pms), gm=_gm_lti(f, L), Ms=float(np.abs(S).max()),
               L20=float(abs(L[_I20])), Tc530=20 * math.log10(max(float(np.abs(Tc[band(5, 30)]).max()), 1e-12)),
               M20=float(abs(Cth[_I20] + 1j * w20 * Cw[_I20]) / (8 * w20)))
    # Re(T/w): controller-output impedance, member independent, T counts per deg/s (>0 damps)
    for ff in (7, 10, 13, 16, 20):
        wf = 2 * np.pi * ff
        iff = int(np.argmin(abs(f - ff)))
        out[f"ReTw{ff}"] = float((-K[iff] * (Cth[iff] + 1j * wf * Cw[iff]) / (1j * wf)).real)
    if want_ref and Cref is not None:
        Tr = K * Cref * Pt * S
        out.update(Tr530=20 * math.log10(max(float(np.abs(Tr[band(5, 30)]).max()), 1e-12)),
                   Tr163=float(np.abs(Tr[band(1.6, 3)]).max()),
                   hold=float(abs(Tr[int(np.argmin(abs(f - 0.05)))])),
                   Tr0=float(abs(Tr[0])),
                   trk_min=float(np.abs(Tr[band(0.1, 1.0)]).min()),
                   trk_max=float(np.abs(Tr[band(0.1, 1.0)]).max()))
    return out


# plant frf cache keyed on (member, v)
_PCACHE = {}


def plant_frf(member, v):
    key = (member, round(v, 4))
    if key not in _PCACHE:
        plant, d, ea, jbk = G2.member(member, v)
        Pt, Pw = DM.plant_frf(plant, FGRID)
        _PCACHE[key] = (Pt, Pw, int(d), int(ea), jbk)
    return _PCACHE[key]


def score(cand, member, v, want_ref=True):
    Pt, Pw, d, ea0, _ = plant_frf(member, v)
    ea = ea0
    pr = cand.cont(v)
    Cth, Cw, Cref, K = controller_frf(cand, FGRID, pr, d, ea)
    r = metrics_from(Cth, Cw, Cref, K, Pt, Pw, want_ref=want_ref)
    r["G"] = pr["G"]
    r["kp_eff"] = pr["kp"] * pr["G"] / 256.0
    r["ki_eff"] = pr["ki"] * pr["G"] / 256.0
    r["has_I"] = pr["ki"] > 0
    return r


def score_ref(name, member, v):
    Pt, Pw, d, ea, _ = plant_frf(member, v)
    Cth, Cw, Cref, K = ref_ctl_frf(name, FGRID, d, ea)
    return metrics_from(Cth, Cw, Cref, K, Pt, Pw, want_ref=False)


# ----------------------------------------------------------------------------------------------------------------------
# VALIDATION: my angle FRF == ds_model on a held sample; the extractor reproduces ds_model margins on V295
# ----------------------------------------------------------------------------------------------------------------------
def validate():
    import c1r2_members as M2
    ok = True
    # 1. angle held: B1 at nominal 12.5
    tbl = C.make_table(B1_KNOTS)
    G = float(C.cave_G(C.spd_counts(12.5), tbl))
    plant, d, ea, _ = G2.member("nominal", 12.5)
    des = DM.Des(kind="angle", dsrc="rate_held", kp=112, ki=56, kd=20, G=G, d=d)
    Cth0, Cw0, Cref0 = DM.ctl_frf(FGRID, des)
    b1 = [c for c in CANDS if c.cid == "B1-robust-gaincut"][0]
    Cth, Cw, Cref = ctl_angle(FGRID, b1, dict(G=G, kp=112, ki=56, kd=20), ea)
    e = max(np.max(np.abs(Cth - Cth0)), np.max(np.abs(Cw - Cw0)), np.max(np.abs(Cref - Cref0)))
    print(f"validate 1 (angle held FRF == ds_model): max|diff| = {e:.2e}  {'OK' if e < 1e-9 else 'FAIL'}")
    ok &= e < 1e-9
    # 2. extractor on V295 nominal vs ds_model.metrics
    for v in (8.0, 26.9):
        Pt, Pw, d2, ea2, _ = plant_frf("nominal", v)
        mine = score_ref("V295", "nominal", v)
        dm = DM.metrics(replace(DM.V295, d=d2), (G2.member("nominal", v)[0]))
        dpm = abs(mine["pm"] - dm["pm"]) if np.isfinite(mine["pm"]) and np.isfinite(dm["pm"]) else 0.0
        print(f"validate 2 V295@{v}: PM mine {mine['pm']:.2f} ds_model {dm['pm']:.2f}  dM20 "
              f"{abs(mine['M20'] - dm['M20']):.3f}  dPM {dpm:.3f}")
        ok &= dpm < 0.2
    # 3. B1 nominal 26.9 PM should match gate_B1.txt (67.5)
    r = score(b1, "nominal", 26.9)
    print(f"validate 3 B1 nominal@26.9 PM {r['pm']:.1f} (designer gate_B1 67.5)")
    print("VALIDATE", "PASS" if ok else "FAIL")
    return ok


# ----------------------------------------------------------------------------------------------------------------------
# THE RUN
# ----------------------------------------------------------------------------------------------------------------------
GRID = G2.GRID
TIER_A = G2.TIER_A
TIER_B = G2.TIER_B
GATED = G2.GATED
PMBAR = G2.PMBAR
HEADLINE = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau6", "mode13", "mode20")
COMBINED_NAMES = tuple(n for n in GATED if n not in TIER_A)   # tier-B + aged members


def run(quick=False):
    t0 = time.time()
    if not validate():
        print("validation failed; aborting")
        return
    members = GATED if not quick else ("nominal", "J_hi", "b_lo", "b_q", "b_q*J1.0", "b_q*J1.0+h10")
    speeds = GRID if not quick else [3.0, 8.0, 12.5, 17.0, 26.9]
    # V295 reference L20 per (member,v) for the L20 gate, and V295 M20 (member independent)
    v295M20 = score_ref("V295", "nominal", 12.5)["M20"]
    v294M20 = score_ref("V294", "nominal", 12.5)["M20"]
    refRe = {nm: {ff: None for ff in (7, 10, 13, 16, 20)} for nm in ("V294", "V295", "V282")}
    for nm in refRe:
        rr = score_ref(nm, "nominal", 12.5)
        for ff in (7, 10, 13, 16, 20):
            refRe[nm][ff] = rr[f"ReTw{ff}"]
    # V295 Re(T/w)20 worst over speed, age 0 and 10 (the gate reference)
    v295Re20 = {0: 1e9, 10: 1e9}
    for v in speeds:
        for ea, nm in ((0, "nominal"), (10, "nominal+h10")):
            Pt, Pw, d, ea2, _ = plant_frf(nm, v)
            Cth, Cw, Cref, K = ref_ctl_frf("V295", FGRID, d, ea2)
            wf = 2 * np.pi * 20.0
            iff = int(np.argmin(abs(FGRID - 20.0)))
            re20 = float((-K[iff] * (Cth[iff] + 1j * wf * Cw[iff]) / (1j * wf)).real)
            v295Re20[ea] = min(v295Re20[ea], re20)
    v295L20 = {}
    for m in members:
        for v in speeds:
            v295L20[(m, v)] = score_ref("V295", m, v)["L20"]

    allres = {}
    summary = {}
    for cand in CANDS:
        rows = {}
        for m in members:
            for v in speeds:
                r = score(cand, m, v)
                rows[(m, v)] = r
        allres[cand.cid] = rows
        summary[cand.cid] = summarize(cand, rows, members, speeds, v295M20, v294M20, v295L20, v295Re20, refRe)
        s = summary[cand.cid]
        print(f"[{cand.cid:16s}] minPMnom {s['minPM_nom']:.1f} minPMsingle {s['minPM_single']:.1f} "
              f"minPMcomb {s['minPM_comb']:.1f} ({s['bind']}) fails {s['n_fail']} "
              f"M20 {s['M20']:.2f} ({s['M20_ratio']:.2f}x) [{time.time() - t0:.0f}s]")
    # persist
    (OUT / "score_freq_summary.json").write_text(json.dumps(summary, default=float, indent=1))
    refpack = dict(v295M20=v295M20, v294M20=v294M20, v295Re20=v295Re20, refRe=refRe)
    (OUT / "score_freq_refs.json").write_text(json.dumps(refpack, default=float, indent=1))
    write_report(summary, refpack, quick)
    print(f"done [{time.time() - t0:.0f}s]  ->  {OUT/'score_freq_summary.json'}")
    return summary, refpack


def summarize(cand, rows, members, speeds, v295M20, v294M20, v295L20, v295Re20, refRe):
    def finite(xs):
        return [x for x in xs if np.isfinite(x)]
    nomrows = [(v, rows[("nominal", v)]) for v in speeds]
    minPM_nom = min((r["pm"] for _, r in nomrows if np.isfinite(r["pm"])), default=float("nan"))
    single = [n for n in members if n in TIER_A]
    comb = [n for n in members if n in TIER_B]
    minPM_single = min((rows[(n, v)]["pm"] for n in single for v in speeds if np.isfinite(rows[(n, v)]["pm"])),
                       default=float("nan"))
    # binding combined member
    cbind = None
    minPM_comb = float("inf")
    for n in comb:
        for v in speeds:
            pm = rows[(n, v)]["pm"]
            if np.isfinite(pm) and pm < minPM_comb:
                minPM_comb = pm
                cbind = (n, v, rows[(n, v)]["fc"])
    if not np.isfinite(minPM_comb):
        minPM_comb = float("nan")
    bind = f"{cbind[0]}@{cbind[1]:.2f} fc~{cbind[2]:.2f}Hz" if cbind else "-"
    # crossover range on nominal (finite fc)
    fcs = finite([r["fc"] for _, r in nomrows])
    fcr = (min(fcs), max(fcs)) if fcs else (float("nan"), float("nan"))
    # M20 (member independent, read off nominal 12.5)
    M20 = rows[("nominal", 12.5)]["M20"] if ("nominal", 12.5) in rows else rows[("nominal", speeds[0])]["M20"]
    # 5-30 Hz closed-loop peak over gated members/speeds (max of Tc530, Tr530)
    peak530 = max((max(rows[(n, v)]["Tc530"], rows[(n, v)].get("Tr530", -99)) for n in members for v in speeds))
    # L20 ratio vs V295 (same member), worst
    l20r = max((rows[(n, v)]["L20"] / v295L20[(n, v)] for n in members for v in speeds if v295L20[(n, v)] > 0))
    # Re(T/w) controller-only at the design speeds (read at nominal 12.5; member independent) + 20 Hz age-10 worst
    re = {ff: rows[("nominal", 12.5)][f"ReTw{ff}"] for ff in (7, 10, 13, 16, 20)}
    # Re(T/w)20 worst over speed, age 0 and age 10
    re20w = {0: 1e9, 10: 1e9}
    for n in members:
        base = n[:-4] if n.endswith("+h10") else n
        ea_tag = 10 if n.endswith("+h10") else 0
        for v in speeds:
            re20w[ea_tag] = min(re20w[ea_tag], rows[(n, v)]["ReTw20"])
    # Tr163 (nominal worst over speed)
    tr163 = max((rows[("nominal", v)].get("Tr163", float("nan")) for v in speeds))
    # turn-hold & tracking (nominal, >=8 m/s)
    th = [rows[("nominal", v)].get("hold", float("nan")) for v in speeds if v >= 8.0]
    th = min([x for x in th if np.isfinite(x)], default=float("nan"))
    trk = [(rows[("nominal", v)].get("trk_min", float("nan")), rows[("nominal", v)].get("trk_max", float("nan")))
           for v in speeds if v >= 8.0]
    trk = [t for t in trk if np.isfinite(t[0])]
    trkrange = (min(t[0] for t in trk), max(t[1] for t in trk)) if trk else (float("nan"), float("nan"))
    # DC stiffness
    hasI = rows[("nominal", speeds[0])]["has_I"]
    if hasI:
        stiff = float("inf")
    else:
        # k + static loop gain: Kp_eff/256 * 160 * FADE*FWD*Hout(0); Hout(0) = OB/1024 *2/32 /(1-OA/1024)
        kpeff = rows[("nominal", 26.9)]["kp_eff"]
        g0 = FADE * FWD * (OB / 1024 * 2 / 32 / (1 - OA / 1024))
        _, _, _, _, jbk = plant_frf("nominal", 26.9)
        stiff = jbk[2] + g0 * (kpeff / 256.0) * 160.0
    # hold-age sensitivity: min PM over combined at age0 vs the same at age10 (ΔPM)
    comb0 = [n for n in comb if not n.endswith("+h10")]
    comb10 = [n for n in comb if n.endswith("+h10")]
    pm0 = min((rows[(n, v)]["pm"] for n in comb0 for v in speeds if np.isfinite(rows[(n, v)]["pm"])),
              default=float("nan"))
    pm10 = min((rows[(n, v)]["pm"] for n in comb10 for v in speeds if np.isfinite(rows[(n, v)]["pm"])),
               default=float("nan"))
    holdage = pm0 - pm10 if np.isfinite(pm0) and np.isfinite(pm10) else float("nan")
    # GATE 2 fails (PM<thr | gm<6 | Tc/Tr 5-30>+3 | M20>V295 | L20>V295 ; stability via PM>0/finite proxy)
    fails = []
    for n in members:
        thr = PMBAR.get(n, 45.0 if n in TIER_A else 30.0)
        for v in speeds:
            r = rows[(n, v)]
            bad = []
            if np.isfinite(r["pm"]) and r["pm"] < thr:
                bad.append(f"PM{thr:.0f}")
            if r["gm"] < 6.0:
                bad.append("GM6")
            if max(r["Tc530"], r.get("Tr530", -99)) > 3.0:
                bad.append("T530")
            if r["M20"] > v295M20 * (1 + 1e-9):
                bad.append("M20")
            if v295L20[(n, v)] > 0 and r["L20"] > v295L20[(n, v)] * (1 + 1e-9):
                bad.append("L20")
            if bad:
                fails.append((n, round(v, 2), bad, round(r["pm"], 1)))
    return dict(cid=cand.cid, designer=cand.designer, note=cand.note, has_I=bool(hasI),
                minPM_nom=minPM_nom, minPM_single=minPM_single, minPM_comb=minPM_comb, bind=bind,
                fc_range=fcr, M20=M20, M20_ratio=M20 / v295M20, M20_ratio_v294=M20 / v294M20,
                peak530=peak530, L20_ratio=l20r, Re=re, Re20_worst=re20w, Tr163=tr163,
                turnhold=th, trk_range=trkrange, dc_stiff=stiff, holdage_dPM=holdage,
                n_fail=len(fails), fails=fails[:40],
                kp_eff_lo=min(rows[("nominal", v)]["kp_eff"] for v in speeds),
                kp_eff_hi=max(rows[("nominal", v)]["kp_eff"] for v in speeds))


def write_report(summary, refpack, quick):
    """emit the machine-readable table block the SCORE-FREQ markdown embeds (also printed)."""
    cols = ["cand", "minPMnom", "minPMsingle", "minPMcomb", "binding(member@v fc)", "fcRange(nom,Hz)",
            "peak5-30dB", "M20(x V295)", "L20x", "ReTw13", "ReTw16", "ReTw20", "ReTw20@age10(x V295)",
            "Tr1.6-3", "turnhold>=8", "trk0.1-1", "DCstiff", "dPM(age)", "GATE2 fails"]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    v295Re20 = refpack["v295Re20"]
    for cid, s in summary.items():
        rw = s["Re20_worst"]
        re20a10 = rw[10] if 10 in rw else rw["10"]
        v295a10 = v295Re20[10] if 10 in v295Re20 else v295Re20["10"]
        ratio_a10 = (re20a10 / v295a10) if v295a10 else float("nan")
        dcs = "inf(I)" if s["dc_stiff"] == float("inf") else f"{s['dc_stiff']:.0f}"
        row = [cid, f"{s['minPM_nom']:.1f}", f"{s['minPM_single']:.1f}", f"{s['minPM_comb']:.1f}", s["bind"],
               f"{s['fc_range'][0]:.2f}-{s['fc_range'][1]:.2f}", f"{s['peak530']:+.1f}",
               f"{s['M20']:.2f} ({s['M20_ratio']:.2f})", f"{s['L20_ratio']:.2f}",
               f"{s['Re'][13]:+.2f}", f"{s['Re'][16]:+.2f}", f"{s['Re'][20]:+.2f}",
               f"{re20a10:+.2f} ({ratio_a10:.2f})", f"{s['Tr163']:.2f}",
               f"{s['turnhold']:.2f}", f"{s['trk_range'][0]:.2f}-{s['trk_range'][1]:.2f}", dcs,
               f"{s['holdage_dPM']:.1f}", str(s["n_fail"])]
        lines.append("| " + " | ".join(row) + " |")
    table = "\n".join(lines)
    (OUT / "score_freq_table.md").write_text(table, encoding="utf-8")
    print("\n" + table + "\n")
    return table


if __name__ == "__main__":
    run(quick=("quick" in sys.argv))
