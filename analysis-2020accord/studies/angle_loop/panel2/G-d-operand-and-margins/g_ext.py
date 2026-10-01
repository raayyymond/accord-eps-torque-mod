# -*- coding: utf-8 -*-
r"""g_ext.py -- PANEL 2 designer G (the D operand and the margin findings F2/F3), 2026-10-01.
EXTENSION of the common frequency scorer (panel/score_freq.py) -- imported, NOT forked.  ANALYSIS ONLY: builds no image,
flashes nothing, sends nothing; writes only under this folder and _scratch/angle_loop/G-dop/.

WHAT THIS ADDS TO score_freq (and nothing else; every controller FRF primitive, the plant FRF, the member factorial and
the metric extractor are score_freq's / ds_model's own, called unchanged):

  (1) pm_fixed -- the PM of a crossing is 180 - |wrap(phase)|, wrap to (-180, 180].  The shared extractor (score_freq
      _pm_all, ds_model.pm_all, ds_gate2._pm_gm_rows, c2r2_model.pm_all and 7 more copies) computes
      ((phase + 180) + 180) % 360 - 180, which is correct for a lagging crossing (phase in (-180, 0]) and returns
      phase - 180 (NEGATIVE) for a LEADING crossing (phase in (0, 180)).  A leading crossing appears when the D term's own
      loop exceeds unity below the plant's resonance (D_T > b) -- exactly the low-G rows of an envelope search at higher
      Kd.  EVIDENCE: explore2 (this folder's g_pmfix.py reproduces it): Kd 41, b_q*J1.0 @ 14 m/s, G 40: crossing at
      1.01 Hz, phase +0.5 deg -> the shared formula says PM -179.5, exact periodic rho 0.9986 (stable).  Every margin this
      page reports uses pm_fixed; the raw formula is printed beside it wherever the two differ.
  (2) params_ext / plant_ext -- the brief's credible set PLUS the members the round-2 refuters named:
        ms_free x {b_lo, b_q} (each with tau6 and +h10), aged single corners at the STRICT tier (PM >= 45 at ages 11-20),
        '+h20' (ages 21-30) and '+h0' (ages 0-9, slot 4 before the lane) for Re(T/w) and the sensitivity tables,
      and the FRAME variants of finding F2:  name + '|k<kappa>' scales the D operand's gain per degree/s of the plant's
      angle (kappa x the model's), name + '|fb' divides J and b by s_c = 1.155 (the plant identified in the motor frame:
      J r'' + b r' + k theta = T with theta = s r near centre is, in theta, (J/s) theta'' + (b/s) theta' + k theta = T).
  (3) the angle-own D operand 'box10' (implementation iii): op = k_op (th_h[n-10] - th_h[n]) -- the held angle's
      difference across exactly one refresh, held for the 10 ticks (FRF: -10 k_op H(q) (1 - q^10) per degree).
  (4) a G-affine, kd-linear loop decomposition (L = kd kappa L_D1 + g L_PI1) so an envelope over Kd and kappa costs one
      pair of loop FRFs per (member, speed).

Units / conventions are score_freq's: theta deg (+ left), omega deg/s, lane S counts, L = -K (C_th Pt + C_w Pw).
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

HERE = Path(__file__).resolve().parent                    # .../angle_loop/panel2/G-d-operand-and-margins
AL = HERE.parents[1]                                      # .../studies/angle_loop
KIT = AL.parents[2]
for _p in (str(AL / "panel"), str(AL / "panel" / "D-structure"), str(AL / "c1"), str(AL / "refute_stability"),
           str(AL.parent / "v295" / "plant"), str(AL), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import score_freq as SF        # noqa: E402  the common frequency scorer (imported, not forked)
import ds_model as DM          # noqa: E402
import ds_gate2 as G2          # noqa: E402
import c1r2_members as M2      # noqa: E402
import c1_lib as C             # noqa: E402

OUT = KIT / "_scratch" / "angle_loop" / "G-dop"
OUT.mkdir(parents=True, exist_ok=True)

S_C = 1.155                     # d(gp-0x6a00)/d(lin) near centre (|theta| < 27.7 deg): image knots 0xC6892/0xC68A2 + r71b wire
S_O = 0.962                     # ... beyond 81 deg (EVIDENCE: c2r2_frame_wire_out, bytes and wire agree)
F = SF.FGRID


# ======================================================================================================================
# (1) the corrected phase margin
# ======================================================================================================================
def crossings(f, L):
    """every |L| = 1 crossing: (fc, phase_unwrapped_deg, pm_fixed, pm_raw)."""
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L)) * 180 / np.pi
    out = []
    for i in np.where((mag[:-1] - 1) * (mag[1:] - 1) <= 0)[0]:
        if mag[i] == mag[i + 1]:
            continue
        t = (1 - mag[i]) / (mag[i + 1] - mag[i])
        p = ph[i] + t * (ph[i + 1] - ph[i])
        fc = f[i] + t * (f[i + 1] - f[i])
        w = ((p + 180.0) % 360.0) - 180.0                       # wrap to [-180, 180)
        out.append((fc, p, 180.0 - abs(w), ((p + 180) + 180) % 360 - 180))
    return out


def pm_fixed(f, L):
    cr = crossings(f, L)
    if not cr:
        return float("nan"), float("nan"), float("nan")
    j = int(np.argmin([c[2] for c in cr]))
    return cr[j][2], cr[j][0], min(c[3] for c in cr)            # (pm_fixed, fc at it, pm_raw = the shared formula)


def pm_gm_rows_fixed(L):
    """ds_gate2._pm_gm_rows with the corrected PM (rows = G values)."""
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L), axis=1) * 180 / np.pi
    nG = L.shape[0]
    pm = np.full(nG, np.inf)
    gm = np.full(nG, np.inf)
    for i in range(nG):
        m, p = mag[i], ph[i]
        idx = np.where((m[:-1] - 1) * (m[1:] - 1) <= 0)[0]
        for j in idx:
            if m[j] == m[j + 1]:
                continue
            t = (1 - m[j]) / (m[j + 1] - m[j])
            q = p[j] + t * (p[j + 1] - p[j])
            w = ((q + 180.0) % 360.0) - 180.0
            pm[i] = min(pm[i], 180.0 - abs(w))
        wv = np.floor((p + 180) / 360)
        jx = np.where(wv[:-1] != wv[1:])[0]
        for j in jx:
            gm[i] = min(gm[i], -20 * math.log10(max(m[j], 1e-12)))
    return pm, gm


# ======================================================================================================================
# (2) members: the brief's set + the refuters' products + aged tiers + frame variants
# ======================================================================================================================
MSF_PRODUCTS = ("b_lo*ms_free", "b_q*ms_free", "b_lo*ms_free*tau6", "b_q*ms_free*tau6")


def _split(name):
    """name -> (base, ea_extra, kappa, jb_scale).  Suffix order: base[+h10|+h20|+h0][|k<x>][|fb]"""
    kappa, jb = 1.0, 1.0
    parts = name.split("|")
    base = parts[0]
    for p in parts[1:]:
        if p.startswith("k"):
            kappa = float(p[1:])
        elif p == "fb":
            jb = 1.0 / S_C
        elif p == "fbo":
            jb = 1.0 / S_O
        else:
            raise KeyError(name)
    ea = 0
    for suf, e in (("+h10", 10), ("+h20", 20), ("+h0", -1)):
        if base.endswith(suf):
            base, ea = base[:-len(suf)], e
            break
    return base, ea, kappa, jb


def params_ext(base, v):
    """(J, b, k, d, ea0) for a base name (no age / frame suffix)."""
    if base in ("mode13", "mode20"):
        return M2.params("nominal", v)
    if "ms_free" in base:
        parts = base.split("*")
        p = M2.FAM["ms_free"].at(v)
        J, b, k = p.J, p.b, p.k
        d = 2
        for q in parts:
            if q == "ms_free":
                continue
            if q in ("b_lo", "b_q"):
                b = M2._dscale(q, b, v)
            elif q == "tau6":
                d = 6
            else:
                raise KeyError(base)
        return J, b, k, d, 0
    return M2.params(base, v)


def plant_ext(name, v):
    """(plant tuple, d, ea, (J, b, k), kappa).  Plant = rigid (or the brief's two-mass for mode13/mode20)."""
    base, ea, kappa, jb = _split(name)
    J, b, k, d, ea0 = params_ext(base, v)
    J, b = J * jb, b * jb
    if base in ("mode13", "mode20"):
        f2, z2 = (13.0, 0.1) if base == "mode13" else (20.0, 0.05)
        pl = G2.two_mass_mu(J, b, k, f2, z2, 0.2)
    else:
        pl = DM.rigid(J, b, k)
    return pl, int(d), int(ea0 + ea), (J, b, k), kappa


_PC = {}


def plant_frf_ext(name, v):
    key = (name, round(v, 4))
    if key not in _PC:
        pl, d, ea, jbk, kappa = plant_ext(name, v)
        Pt, Pw = DM.plant_frf(pl, F)
        if len(_PC) > 400:
            _PC.clear()
        _PC[key] = (Pt, Pw, d, ea, jbk, kappa)
    return _PC[key]


# the gated sets ---------------------------------------------------------------------------------------------------------
SINGLE = G2.SINGLE                                    # nominal J_lo J_hi b_lo b_hi tau0 tau6 mode13 mode20 ms_free
COMBINED = G2.COMBINED                                # b_lo*J_hi b_lo*tau6 J1.0 b_q b_q*J_hi b_q*J1.0 b_q*tau6
BRIEF_A = SINGLE
BRIEF_B = COMBINED + tuple(m + "+h10" for m in SINGLE + COMBINED)
NEW_B = MSF_PRODUCTS + tuple(m + "+h10" for m in MSF_PRODUCTS) + ("b_lo*J_hi*tau6", "b_lo*J_hi*tau6+h10")
STRICT_A = tuple(m + "+h10" for m in SINGLE)          # the strict reading: aged single corners at 45 deg
FRAMES_RATE = ("", "|k0.83", "|k1.155", "|fb|k0.83", "|fb|k1.155")     # gated on every member (rate-operand D)
FRAMES_ANGLE = ("", "|fb")                                              # the angle-own D is frame-exact (kappa = 1)


def tier_of(name, strict=True):
    """strict: the brief + aged single corners at tier A + the refuters' products at tier B (this page's gate);
    not strict: the brief's literal set (aged single corners tier B, the refuters' new products report-only)."""
    base = name.split("|")[0]
    if base in BRIEF_A:
        return "A"
    if strict and base in STRICT_A:
        return "A"
    if base in BRIEF_B or (strict and base in NEW_B):
        return "B"
    return "report"


def bar_of(name, strict=True):
    return {"A": 45.0, "B": 30.0}.get(tier_of(name, strict), 0.0)


def gated_members(dkind, strict=True, new=True):
    frames = FRAMES_ANGLE if dkind == "box10" else FRAMES_RATE
    bases = list(BRIEF_A) + list(BRIEF_B) + (list(NEW_B) if new else [])
    return [b + fr for b in bases for fr in frames]


# ======================================================================================================================
# (3) the controller FRF with the D operand separated (kd-linear) and the angle-own D 'box10'
# ======================================================================================================================
def ctl_parts(cand: SF.Cand, pr, ea, f=None):
    """(Cth_PI, Cref_PI, Cth_D1, Cw_D1) on frequency grid f (default FGRID): the P/I part at pr's G and the D part PER
    UNIT kd (score_freq's own ctl_angle with kd = 0 and kd = 1, differenced -- except box10, built here)."""
    f = F if f is None else np.asarray(f, float)
    pr0 = dict(pr, kd=0.0)
    base = cand if cand.dop != "box10" else replace(cand, dsrc="none", dop="")
    Cth0, Cw0, Cref0 = SF.ctl_angle(f, base, pr0, ea)
    if cand.dop == "box10":
        q = SF._z(f)
        H = SF._H(f, ea)
        Cth_D1 = -(1.0 / 8.0) * cand.dop_k * 10.0 * H * (1 - q ** 10)
        Cw_D1 = np.zeros_like(q)
    else:
        Cth1, Cw1, _ = SF.ctl_angle(f, cand, dict(pr, kd=1.0), ea)
        Cth_D1, Cw_D1 = Cth1 - Cth0, Cw1 - Cw0
    return Cth0, Cref0, Cth_D1, Cw_D1


def loop_parts(cand, name, v, G=None):
    """L_PI (at G), L_D1 (per unit kd, kappa applied), K, Pt, Pw, Cref for member `name` at speed v."""
    Pt, Pw, d, ea, jbk, kappa = plant_frf_ext(name, v)
    pr = cand.cont(v)
    if G is not None:
        pr = dict(pr, G=float(G))
    Cth0, Cref0, CthD, CwD = ctl_parts(cand, pr, ea)
    K = SF.K_out(F, d)
    L_PI = -K * Cth0 * Pt
    L_D1 = -K * kappa * (CthD * Pt + CwD * Pw)
    return dict(L_PI=L_PI, L_D1=L_D1, K=K, Pt=Pt, Pw=Pw, Cth0=Cth0, Cref0=Cref0, CthD=CthD * kappa, CwD=CwD * kappa,
                d=d, ea=ea, jbk=jbk, kappa=kappa, pr=pr)


def metrics_ext(cand, name, v, G=None, kd=None):
    """score_freq.metrics_from on the extended member, plus pm_fixed / pm_raw / every crossing."""
    lp = loop_parts(cand, name, v, G)
    kdv = lp["pr"]["kd"] if kd is None else kd
    Cth = lp["Cth0"] + kdv * lp["CthD"]
    Cw = kdv * lp["CwD"]
    r = SF.metrics_from(Cth, Cw, lp["Cref0"], lp["K"], lp["Pt"], lp["Pw"])
    L = lp["L_PI"] + kdv * lp["L_D1"]
    pmf, fcf, pmr = pm_fixed(F, L)
    r["pm_raw"] = r["pm"]
    r["pm"] = pmf
    r["fc"] = fcf
    r["ncross"] = len(crossings(F, L))
    r["G"] = lp["pr"]["G"]
    r["kd"] = kdv
    r["kappa"] = lp["kappa"]
    r["jbk"] = lp["jbk"]
    return r


# ======================================================================================================================
# (4) envelope over Kd and kappa (G affine, kd linear)
# ======================================================================================================================
GSCAN = np.unique(np.round(np.geomspace(60, 6000, 120)))
FE = np.unique(np.concatenate([np.logspace(-2.3, math.log10(499.0), 1400), [0.02, 0.05, 1.0, 2.0, 20.0]]))


def env_point(args):
    """largest G on GSCAN with every G' <= G passing pm_fixed >= bar and LTI GM >= 6 dB, for every kd in kds.
    Returns (name, v, {kd: Gmax}).  Loop evaluated on the coarse grid FE (1400 pts) -- envelope only; the final gate
    uses FGRID."""
    cand, name, v, kds, bar = args
    pl, d, ea, jbk, kappa = plant_ext(name, v)
    Pt, Pw = DM.plant_frf(pl, FE)
    pr1 = dict(cand.cont(v), G=256.0, kd=0.0)
    Cth0, Cref0, CthD, CwD = ctl_parts(cand, pr1, ea, FE)
    K = SF.K_out(FE, d)
    L_PI1 = -K * Cth0 * Pt
    L_D1 = -K * kappa * (CthD * Pt + CwD * Pw)
    g = GSCAN / 256.0
    out = {}
    for kd in kds:
        Lr = kd * L_D1[None, :] + g[:, None] * L_PI1[None, :]
        pm, gm = pm_gm_rows_fixed(Lr)
        ok = (pm >= bar) & (gm >= 6.0)
        if not ok[0]:
            out[kd] = 0.0
        else:
            k = int(np.argmin(ok)) if not ok.all() else len(ok)
            out[kd] = float(GSCAN[k - 1])
    return name, v, out


# ======================================================================================================================
# the 20 Hz rules (controller-only M20 and Re(T/w)20 vs V295 at ages 0 / 10; L20 on tier-A members) at a given kd/kappa
# ======================================================================================================================
def ctl_at(cand, v, G, kd, kappa, ea, f):
    pr = dict(cand.cont(v), G=float(G), kd=0.0)
    Cth0, Cref0, CthD, CwD = ctl_parts(cand, pr, ea, f)
    return Cth0 + kd * kappa * CthD, kd * kappa * CwD


def m20(cand, v, G, kd, kappa=1.0, ea=0):
    Cth, Cw = ctl_at(cand, v, G, kd, kappa, ea, np.array([20.0]))
    w = 2 * np.pi * 20.0
    return float(abs(Cth[0] + 1j * w * Cw[0]) / (8 * w))


def re_tw(cand, v, G, kd, f, ea=0, d=2, kappa=1.0):
    f = np.atleast_1d(np.asarray(f, float))
    Cth, Cw = ctl_at(cand, v, G, kd, kappa, ea, f)
    K = SF.K_out(f, d)
    w = 2 * np.pi * f
    return (-K * (Cth + 1j * w * Cw) / (1j * w)).real


def ref_re_tw(nm, f, ea=0, d=2, kappa=1.0):
    """V294 / V295 / V282 controller-output impedance (rate operand x kappa: the reference reads the lin-frame rate)."""
    f = np.atleast_1d(np.asarray(f, float))
    des = replace(SF.des_for_ref(nm), d=d, extra_age=ea)
    Cth, Cw, _ = DM.ctl_frf(f, des)
    K = DM.K_out(f, des)
    w = 2 * np.pi * f
    return (-K * (Cth + 1j * w * kappa * Cw) / (1j * w)).real


def ref_m20(nm, kappa=1.0, ea=0):
    des = replace(SF.des_for_ref(nm), extra_age=ea)
    Cth, Cw, _ = DM.ctl_frf(np.array([20.0]), des)
    w = 2 * np.pi * 20.0
    return float(abs(Cth[0] + 1j * w * kappa * Cw[0]) / (8 * w))


def ref_L20(nm, name, v):
    """V295's |L(20 Hz)| on the same member (its rate operand scaled by the member's kappa)."""
    pl, d, ea, jbk, kappa = plant_ext(name, v)
    f = np.array([20.0])
    des = replace(SF.des_for_ref(nm), d=d, extra_age=ea)
    Cth, Cw, _ = DM.ctl_frf(f, des)
    K = DM.K_out(f, des)
    Pt, Pw = DM.plant_frf(pl, f)
    return float(abs(-K * (Cth * Pt + kappa * Cw * Pw))[0])


def cand_L20(cand, name, v, G, kd):
    pl, d, ea, jbk, kappa = plant_ext(name, v)
    f = np.array([20.0])
    Cth, Cw = ctl_at(cand, v, G, kd, kappa, ea, f)
    K = SF.K_out(f, d)
    Pt, Pw = DM.plant_frf(pl, f)
    return float(abs(-K * (Cth * Pt + Cw * Pw))[0])


# ======================================================================================================================
# candidates
# ======================================================================================================================
def cand(cid, dkind, rows, kd, kp=112, ki=56, note="", dop_k=1.0):
    """dkind: 'fresh' (gp-0x6abe in the cave, P2's code), 'held' (gp-0x6a56 via E5, F2's code), 'box10' (angle-own)."""
    if dkind == "fresh":
        return SF.Cand(cid, "G", kind="angle", dsrc="op", dop="fresh_rate", cont=SF.cave_cont_rows(rows, kp, ki, kd),
                       note=note)
    if dkind == "held":
        return SF.Cand(cid, "G", kind="angle", dsrc="rate_held", cont=SF.cave_cont_rows(rows, kp, ki, kd), note=note)
    if dkind == "box10":
        return SF.Cand(cid, "G", kind="angle", dsrc="op", dop="box10", dop_k=dop_k,
                       cont=SF.cave_cont_rows(rows, kp, ki, kd), note=note)
    raise ValueError(dkind)


def flat_cand(dkind, kd, G=256.0, ki=56, dop_k=1.0):
    """a structure at a fixed G (for envelopes: cont returns G=256 placeholder; env_point overrides G)."""
    def cont(v):
        return dict(G=G, kp=112.0, ki=float(ki), kd=float(kd))
    if dkind == "fresh":
        return SF.Cand(f"fresh{kd}", "G", dsrc="op", dop="fresh_rate", cont=cont)
    if dkind == "held":
        return SF.Cand(f"held{kd}", "G", dsrc="rate_held", cont=cont)
    return SF.Cand(f"box{kd}", "G", dsrc="op", dop="box10", dop_k=dop_k, cont=cont)


def G_of(rows, v):
    return float(C.cave_G(C.spd_counts(v), [tuple(r) for r in rows]))


P2_ROWS = [(714, 1195, 1204), (1843, 1527, -7988), (2304, 628, -925), (2707, 537, 2785), (4032, 1438, 1309),
           (6198, 2130, 0), (0xFFFF, 2130, 0)]          # rev2-A P2, parsed from c2_cave_P2.hex (asserted in g_selftest)
F2_ROWS = [(714, 1187, 896), (1843, 1434, -6388), (2304, 715, -1779), (2707, 540, 2507), (4032, 1351, 1348),
           (6198, 2064, 0), (0xFFFF, 2064, 0)]          # rev2-A F2, parsed from c2_cave_F2.hex
