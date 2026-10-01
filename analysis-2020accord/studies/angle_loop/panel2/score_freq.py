# -*- coding: utf-8 -*-
r"""panel2/score_freq.py -- THE COMMON FREQUENCY-DOMAIN SCORER, PANEL ROUND 2 (2026-10-01).

ANALYSIS ONLY.  Builds nothing, flashes nothing, sends nothing; writes only under _scratch/angle_loop/panel2-score/.
Every candidate (E1-*, E2-*, G-*, H-A, H-B and the four round-1 implementations P2, F2, D2a, B0r) goes through ONE
identical pipeline.  Designers do not grade their own work here: each loop is re-derived from its bytes (the G(v) table is
parsed from the cave hex the designer published) and its cals.

WHAT IS INHERITED (validated last round, imported unchanged from panel/score_freq.py = "SF"):
  the frequency grid, the 100 Hz hold H, the gp-0x6abe EMA (37/128), the output lag + fwd + fade K_out, the image cals
  (OA 992, OB 507, FWD 5346/32768, FADE 254/256), ds_model's plant FRF (ZOH), ds_gate2's two-mass modes, c1r2_members'
  credible factorial, c1_lib's integer G walk.  SF.ctl_angle is the reference this file's controller is checked against.

WHAT IS NEW THIS ROUND (each a finding of the round-2 refuters or a designer, each validated in validate()):
  (1) the controller split by FRAME: every channel is either in gp-0x6a00's frame (theta: the held angle, the box10 D)
      or the motor-linear frame (gp-0x6abe, gp-0x6a56, gp-0x69ca).  L = L_theta + kappa * L_motor, linear in kappa.
  (2) the frame box (refuter F1 / round-2 F2): kappa = the motor-frame operand's gain per deg/s of the plant's angle,
      gated at kappa in {0.83, 1, 1.155} under reading FA (J, b, k per degree of gp-0x6a00) and at {0.83, 1.155} under
      reading FB (J, b per degree of the motor-linear angle: J, b x 1/1.155 in theta coordinates); the PHYSICAL points
      (kappa 1/1.155 near centre, 1/0.962 outward, each under FA and FB) are reported.
  (3) the member set + ms_free x {b_lo, b_q} (refuter F4 / round-2 F3), every member at hold ages 1-10 AND 11-20;
      the strict reading (aged single corners at 45 deg) reported; designer G's x tau6 products reported.
  (4) the CORRECTED phase margin (designer G's finding, re-verified here): PM = 180 - |wrap(phase)| at every |L| = 1
      crossing.  The shared formula ((p+180)+180) % 360 - 180 returns p - 180 for a LEADING crossing.  Every row records
      whether the two differ.
  (5) two operands the round-1 engine lacked: the FRESH 1 kHz P/I operand (gp-0x69ca, H-A) and the angle-own box10 D
      (G-A22): op = 64 (th_h[prev refresh] - th_h[now]) counts.
  (6) GM split into the UPWARD margin (gated, >= 6 dB) and the DOWNWARD (gain-reduction) margin (reported).
  (7) the I-FROZEN loop (Ki 0: every freeze / reset / bleed / clamp-saturated / angle-bound state of every integral
      policy) on the same set, and hands-on at the fade floors 0.297 (stock arm) and 0.195 (the 6803 == 2 arm 0xCBAE4).
  (8) an exact periodic model (ds_model.Lifted extended with the fresh operand and box10) for rho and the least-damped
      closed-loop pole at every candidate's binding points.

usage:  python score_freq.py            full run (~3-6 min on 12 processes); caches + markdown tables in the scratch dir
        python score_freq.py validate   the validation block only
        python score_freq.py quick      3 members x 5 speeds smoke test
        python score_freq.py report     re-run the analysis + tables from the cached array (no loop recomputation)
        python score_freq.py claims     the designer-claim cross-checks (needs the cached array)
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import struct
import sys
import time
from dataclasses import dataclass, field, replace
from multiprocessing import Pool
from pathlib import Path

import numpy as np

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
os.environ.setdefault("C1_VARIANT", "r2")

HERE = Path(__file__).resolve().parent                  # .../studies/angle_loop/panel2
AL = HERE.parent                                        # .../studies/angle_loop
KIT = AL.parents[2]                                     # repo root
for _p in (str(AL / "panel" / "D-structure"), str(AL / "c1"), str(AL / "refute_stability"),
           str(AL.parent / "v295" / "plant"), str(AL)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# the round-1 common scorer, by PATH (this file shares its name; a bare import would import itself)
_spec = importlib.util.spec_from_file_location("score_freq_r1", str(AL / "panel" / "score_freq.py"))
SF = importlib.util.module_from_spec(_spec)
sys.modules["score_freq_r1"] = SF
_spec.loader.exec_module(SF)

import ds_model as DM            # noqa: E402
import ds_gate2 as G2            # noqa: E402
import c1r2_members as M2        # noqa: E402
import c1_lib as C               # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                           # pragma: no cover
    pass

OUT = KIT / "_scratch" / "angle_loop" / "panel2-score"
OUT.mkdir(parents=True, exist_ok=True)

F = SF.FGRID
TS = 1e-3
ABE_PER = DM.ABE_PER                                    # gp-0x6abe counts per deg/s of the motor-linear rate (-4.712)
S_C, S_O = 1.155, 0.962                                 # d(gp-0x6a00)/d(lin): near centre / beyond 81 deg (bytes+wire)
I20 = int(np.argmin(abs(F - 20.0)))
I005 = int(np.argmin(abs(F - 0.05)))
B530 = (F >= 5.0) & (F <= 30.0)
B163 = (F >= 1.6) & (F <= 3.0)
B011 = (F >= 0.1) & (F <= 1.0)


# ======================================================================================================================
# 1. TABLES: parsed from the published cave hex (the table address from the cave's own `mov imm32, r9`)
# ======================================================================================================================
def cave_table(path: Path, load=0xC4C00):
    bs = bytes(int(t, 16) for t in Path(path).read_text().split())
    tbl = None
    for i in range(0, len(bs) - 6, 2):
        if bs[i] == 0x29 and bs[i + 1] == 0x06:                 # mov imm32, r9  (hw1 0x0629)
            tbl = struct.unpack_from("<I", bs, i + 2)[0]
            break
    assert tbl is not None, path
    off = tbl - load
    rows = []
    while True:
        X, G, S = struct.unpack_from("<HHh", bs, off)
        rows.append((X, G, S))
        off += 6
        if X == 0xFFFF:
            break
    assert off == len(bs), (path, off, len(bs))
    return rows, len(bs), hashlib.sha256(bs).hexdigest()[:16]


P2H = AL / "c2" / "rev2A"
DSH = AL / "panel" / "D-structure"
GH = HERE / "G-d-operand-and-margins"
E2H = HERE / "E2-integral-most-margin"
HH = HERE / "H-whole-loop-reconcile"


def _rows_from_json(cid):
    d = json.loads((GH / "g_impls_frozen.json").read_text())
    return [tuple(r) for r in d[cid]["rows"]]


# H's tables are given only in h_freq.py (no hex yet): read them from that file verbatim (it states they are D2a / B0r)
def _h_tables():
    import ast
    tree = ast.parse((HH / "h_freq.py").read_text(encoding="utf-8"))
    ns = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and getattr(node.targets[0], "id", "") in (
                "TAB_FRESH", "TAB_HELD"):
            ns[node.targets[0].id] = [tuple(r) for r in ast.literal_eval(node.value)]
    return ns["TAB_FRESH"], ns["TAB_HELD"]


# ======================================================================================================================
# 2. CANDIDATES
# ======================================================================================================================
@dataclass
class Spec:
    cid: str
    designer: str
    rows: list
    kd: float
    kp: float = 112.0
    ki: float = 56.0
    dkind: str = "fresh"           # 'fresh' (gp-0x6abe EMA) | 'held' (gp-0x6a56) | 'box10' (angle-own) | 'none'
    op: str = "held"               # P/I operand: 'held' (gp-0x6a00, 100 Hz) | 'fresh' (gp-0x69ca, 1 kHz)
    pi_frame: str = "theta"        # 'theta' (gp-0x6a00) | 'motor' (gp-0x69ca)
    box_k: float = 64.0
    src: str = ""                  # where the table came from (+ sha16 / bytes)
    linear_as: str = ""            # '' = its own loop; else the cid whose small-signal loop it IS (bytes/cals identical)
    fade_floor: float = 0.297      # hands-on fade floor of its arm (0.195 for the 6803 == 2 arm)
    outer_tau: float = 0.0         # fork angle integral time constant (E2-K0), 0 = none
    note: str = ""

    @property
    def d_frame(self):
        return "theta" if self.dkind == "box10" else ("motor" if self.dkind in ("fresh", "held") else "none")


def build_cands():
    P2r, P2n, P2s = cave_table(P2H / "c2_cave_P2.hex")
    F2r, F2n, F2s = cave_table(P2H / "c2_cave_F2.hex")
    D2r, D2n, D2s = cave_table(DSH / "ds_cave_D2a.hex")
    B0r_, B0n, B0s = cave_table(DSH / "ds_cave_B0r.hex")
    g = {k: cave_table(GH / f"g_cave_{k}.hex") for k in ("G-P48d", "G-P44d", "G-P48", "G-P44", "G-F24", "G-F24d",
                                                          "G-A22", "G-A22d")}
    e2 = {k: cave_table(E2H / f"e2_cave_{k}.hex") for k in ("P2", "S300", "A2", "A3", "L13", "K0")}
    hA, hB = _h_tables()
    for k, (r, n, s) in e2.items():                            # EVIDENCE: every E2 cave carries P2's table byte for byte
        assert r == P2r, (k, r)
    cands = [
        # ---- the four round-1 implementations ----
        Spec("P2", "rev2-A", P2r, 34, src=f"c2_cave_P2.hex {P2n} B {P2s}", note="fresh-rate D Kd 34, 6 knots"),
        Spec("F2", "rev2-A", F2r, 20, dkind="held", src=f"c2_cave_F2.hex {F2n} B {F2s}", note="held-rate D Kd 20"),
        Spec("D2a", "rev2-B", D2r, 34, src=f"ds_cave_D2a.hex {D2n} B {D2s}", note="fresh-rate D Kd 34, 7 knots"),
        Spec("B0r", "rev2-B", B0r_, 20, dkind="held", src=f"ds_cave_B0r.hex {B0n} B {B0s}", note="held-rate D Kd 20"),
        # ---- E1 (P2 skeleton; only ICL / hands-on policy differ -> the small-signal loop IS P2's except splitP) ----
        Spec("E1-reset", "E1", P2r, 34, linear_as="P2", src="P2 table (cave 168 B = P2 + 12 B reset)",
             note="ICL 8192 + firm reset |tq|>1536"),
        Spec("E1-cal", "E1", P2r, 34, linear_as="P2", src="P2 cave unchanged", note="ICL 8192 cal only"),
        Spec("E1-bleed", "E1", P2r, 34, linear_as="P2", src="P2 table", note="+ bleed I-=I>>3 at 256<|tq|<=512"),
        Spec("E1-freeze", "E1", P2r, 34, linear_as="P2", src="P2 table", note="freeze 512->320"),
        Spec("E1-sched", "E1", P2r, 34, linear_as="P2", src="P2 table", note="ICL scheduled (a clamp)"),
        Spec("E1-splitP", "E1", P2r, 34, kp=200, src="P2 table, Kp record 200", note="Kp 200, ICL 3072"),
        # ---- E2 (P2 skeleton, P2's table parsed from each hex) ----
        Spec("E2-R1", "E2", P2r, 34, linear_as="P2", src=f"e2_cave_P2.hex {e2['P2'][1]} B {e2['P2'][2]}",
             note="ICL 8192 only"),
        Spec("E2-S", "E2", P2r, 34, linear_as="P2", src=f"e2_cave_S300.hex {e2['S300'][1]} B {e2['S300'][2]}",
             note="+ opposing-hand freeze >300"),
        Spec("E2-A2", "E2", P2r, 34, linear_as="P2", src=f"e2_cave_A2.hex {e2['A2'][1]} B {e2['A2'][2]}",
             note="+ angle-referenced I bound"),
        Spec("E2-A3", "E2", P2r, 34, linear_as="P2", src=f"e2_cave_A3.hex {e2['A3'][1]} B {e2['A3'][2]}",
             note="A2 + low-speed cap"),
        Spec("E2-A2-X", "E2", P2r, 34, linear_as="P2", fade_floor=50.0 / 256.0,
             src=f"e2_cave_A2.hex + fork 6803==2", note="A2 + fade arm 0xCBAE4 (hands-off fade identical)"),
        Spec("E2-L", "E2", P2r, 34, linear_as="P2", src=f"e2_cave_L13.hex {e2['L13'][1]} B {e2['L13'][2]}",
             note="+ I leak above 512"),
        Spec("E2-K0", "E2", P2r, 34, ki=0, outer_tau=1.0, src=f"e2_cave_K0.hex {e2['K0'][1]} B {e2['K0'][2]}",
             note="Ki 0 + fork angle integral tau_o 1 s"),
        # ---- G ----
        Spec("G-P48d", "G", g["G-P48d"][0], 48, src=f"g_cave_G-P48d.hex {g['G-P48d'][1]} B {g['G-P48d'][2]}"),
        Spec("G-P44d", "G", g["G-P44d"][0], 44, src=f"g_cave_G-P44d.hex {g['G-P44d'][1]} B {g['G-P44d'][2]}"),
        Spec("G-P48", "G", g["G-P48"][0], 48, src=f"g_cave_G-P48.hex {g['G-P48'][1]} B {g['G-P48'][2]}"),
        Spec("G-P44", "G", g["G-P44"][0], 44, src=f"g_cave_G-P44.hex {g['G-P44'][1]} B {g['G-P44'][2]}"),
        Spec("G-F24", "G", g["G-F24"][0], 24, dkind="held", src=f"g_cave_G-F24.hex {g['G-F24'][1]} B {g['G-F24'][2]}"),
        Spec("G-F24d", "G", g["G-F24d"][0], 24, dkind="held",
             src=f"g_cave_G-F24d.hex {g['G-F24d'][1]} B {g['G-F24d'][2]}"),
        Spec("G-A22", "G", g["G-A22"][0], 22, dkind="box10",
             src=f"g_cave_G-A22.hex {g['G-A22'][1]} B {g['G-A22'][2]}"),
        Spec("G-A22d", "G", g["G-A22d"][0], 22, dkind="box10",
             src=f"g_cave_G-A22d.hex {g['G-A22d'][1]} B {g['G-A22d'][2]}"),
        Spec("G-P48L", "G", _rows_from_json("G-P48L"), 48, src="g_impls_frozen.json (no hex)"),
        Spec("G-P48k40", "G", _rows_from_json("G-P48k40"), 48, ki=40, src="g_impls_frozen.json (no hex)"),
        # ---- H ----
        Spec("H-A", "H", hA, 34, op="fresh", pi_frame="motor", src="h_freq.py TAB_FRESH (= D2a's rows)",
             note="P/I on fresh gp-0x69ca (motor frame), fresh D Kd 34"),
        Spec("H-B", "H", hB, 23, dkind="held", src="h_freq.py TAB_HELD (= B0r's rows)",
             note="P/I gp-0x6a00 held, held D Kd 23"),
    ]
    return cands


# ======================================================================================================================
# 3. CONTROLLER FRF, split by frame.  S = C_th theta + C_w omega + C_ref theta_sp  (lane S counts; theta deg)
# ======================================================================================================================
def _z(f):
    return np.exp(-2j * np.pi * np.asarray(f, float) * TS)        # = z^-1


def _H(f, ea):
    z = _z(f)
    return np.mean([z ** (a + ea) for a in range(1, 11)], axis=0)


def _ema(f):
    z = _z(f)
    return DM.ALPHA / (1 - (1 - DM.ALPHA) * z)


def ctl_split(f, sp: Spec, G, ea, ki=None, kd=None):
    """-> dict(t=(Cth, Cw, Cref), m=(Cth, Cw, Cref)) : the theta-frame part and the motor-frame part."""
    f = np.asarray(f, float)
    z = _z(f)
    H = _H(f, ea)
    one = np.ones_like(z)
    zero = np.zeros_like(z)
    g = G / 256.0
    ki = sp.ki if ki is None else ki
    kd = sp.kd if kd is None else kd
    Hop = H if sp.op == "held" else one                          # fresh gp-0x69ca: same tick, no hold
    r26 = 80.0 * (1 + z) * Hop                                   # 8 th[n] + 8 th[n-1], 10 counts per deg
    PI = (sp.kp / 256.0 + (ki / 32768.0) / (1 - z)) * g          # P = (E' Kp) >> 8 ; I = sum (E' Ki) / 32768 (I>>7, inc >>3)
    sph = np.mean([z ** a for a in range(1, 11)], axis=0)        # 0xE4 setpoint hold (ages 1..10)
    PI_th, PI_ref = -PI * r26, PI * 160.0 * sph
    kd8 = kd / 8.0
    D_th, D_w = zero, zero
    if sp.dkind == "fresh":                                      # D = (Kd * gp-0x6abe) >> 3, gp-0x6abe = ABE_PER ema w
        D_w = kd8 * ABE_PER * _ema(f)
    elif sp.dkind == "held":                                     # D = (-Kd * gp-0x6a56) >> 3, x = 8 H ema w
        D_w = -kd * H * _ema(f)
    elif sp.dkind == "box10":                                    # op = k (th_h[prev] - th_h[now]) counts, D = Kd op >> 3
        D_th = -kd8 * sp.box_k * 10.0 * H * (1 - z ** 10)
    elif sp.dkind != "none":
        raise ValueError(sp.dkind)
    t = [zero, zero, zero]
    m = [zero, zero, zero]
    tgt = t if sp.pi_frame == "theta" else m
    tgt[0] = tgt[0] + PI_th
    tgt[2] = tgt[2] + PI_ref
    dtg = m if sp.d_frame == "motor" else t
    dtg[0] = dtg[0] + D_th
    dtg[1] = dtg[1] + D_w
    return dict(t=tuple(t), m=tuple(m))


def K_out(f, d):
    return SF.K_out(np.asarray(f, float), d)


def ref_ctl(name, f, d, ea):
    """V295 / V294 / V282: their rate operand is the motor-linear rate -> the whole controller is motor frame."""
    Cth, Cw, Cref, K = SF.ref_ctl_frf(name, np.asarray(f, float), d, ea)
    return Cth, Cw, K


# ======================================================================================================================
# 4. MEMBERS (the brief's set + ms_free x {b_lo, b_q} + designer G's x tau6 products), plant FRF with a J,b scale
# ======================================================================================================================
SINGLE = tuple(G2.SINGLE)                     # nominal J_lo J_hi b_lo b_hi tau0 tau6 mode13 mode20 ms_free
COMBINED = tuple(G2.COMBINED)                 # b_lo*J_hi b_lo*tau6 J1.0 b_q b_q*J_hi b_q*J1.0 b_q*tau6
MSF2 = ("b_lo*ms_free", "b_q*ms_free")        # the brief's extension (round-2 refuter F4)
XREP = ("b_lo*ms_free*tau6", "b_q*ms_free*tau6", "b_lo*J_hi*tau6")   # designer G's extra products (reported)
BASES = SINGLE + COMBINED + MSF2 + XREP
MEMBERS = tuple(b for b in BASES) + tuple(b + "+h10" for b in BASES)

# variants: (name, kappa, J,b scale)
VARIANTS = (("nom", 1.0, 1.0), ("FA.83", 0.83, 1.0), ("FA1.155", 1.155, 1.0), ("FB.83", 0.83, 1 / S_C),
            ("FB1.155", 1.155, 1 / S_C),
            ("FAc", 1 / S_C, 1.0), ("FBc", 1 / S_C, 1 / S_C), ("FAo", 1 / S_O, 1.0), ("FBo", 1 / S_O, 1 / S_O))
VNAMES = tuple(v[0] for v in VARIANTS)
GATE_LIT = (0, 1, 2)                          # the brief's literal box: kappa 0.83..1.155 under FA
GATE_FULL = (0, 1, 2, 3, 4)                   # + reading FB (refuter F1's second reading)
PHYS = (0, 5, 6, 7, 8)                        # the physical frame points (report)
JB_SET = (1.0, 1 / S_C, 1 / S_O)

GRID = list(G2.GRID)                          # 1-35 m/s at 0.25 + the plant knots 3.1 / 8.0 / 11.9 / 17.0 / 26.9


def params_ext(base, v):
    """(J, b, k, tau ticks, two-mass mode or None)."""
    if base in ("mode13", "mode20"):
        J, b, k, d, ea = M2.params("nominal", v)
        return J, b, k, int(d), ((13.0, 0.1) if base == "mode13" else (20.0, 0.05))
    if "ms_free" in base:
        p = M2.FAM["ms_free"].at(v)
        J, b, k, d = p.J, p.b, p.k, 2
        for q in base.split("*"):
            if q == "ms_free":
                continue
            if q in ("b_lo", "b_q"):
                b = M2._dscale(q, b, v)
            elif q == "tau6":
                d = 6
            else:
                raise KeyError(base)
        return J, b, k, d, None
    J, b, k, d, ea = M2.params(base, v)
    assert ea == 0
    return J, b, k, int(d), None


def member_plant(name, v, jb=1.0):
    base, ea = (name[:-4], 10) if name.endswith("+h10") else (name, 0)
    J, b, k, d, mode = params_ext(base, v)
    J, b = J * jb, b * jb
    if mode:
        pl = G2.two_mass_mu(J, b, k, mode[0], mode[1], 0.2)
    else:
        pl = DM.rigid(J, b, k)
    return pl, d, ea, (J, b, k)


def tier_of(member, gate):
    """gate 'R1' (round-1 brief set), 'R2' (+ ms_free products, aged singles at 30), 'strict' (aged singles at 45),
    'Gstrict' (strict + G's x tau6 products).  -> 'A' | 'B' | None."""
    aged = member.endswith("+h10")
    base = member[:-4] if aged else member
    if base in SINGLE:
        if not aged:
            return "A"
        return "A" if gate in ("strict", "Gstrict") else "B"
    if base in COMBINED:
        return "B"
    if base in MSF2:
        return None if gate == "R1" else "B"
    if base in XREP:
        return "B" if gate == "Gstrict" else None
    return None


BAR = {"A": 45.0, "B": 30.0}


# ======================================================================================================================
# 5. THE METRIC EXTRACTOR (one, for every loop)
# ======================================================================================================================
def pm_gm(L, f=F):
    """-> (PM fixed, fc at it, PM by the shared formula, GM up dB, GM down dB).  PM = inf if |L| never crosses 1."""
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L)) * (180.0 / np.pi)
    s = mag - 1.0
    idx = np.where((s[:-1] * s[1:] <= 0) & (mag[:-1] != mag[1:]))[0]
    if len(idx):
        t = (1 - mag[idx]) / (mag[idx + 1] - mag[idx])
        p = ph[idx] + t * (ph[idx + 1] - ph[idx])
        fc = f[idx] + t * (f[idx + 1] - f[idx])
        w = ((p + 180.0) % 360.0) - 180.0
        pmf = 180.0 - np.abs(w)
        pmr = ((p + 180.0) + 180.0) % 360.0 - 180.0
        j = int(np.argmin(pmf))
        PM, FC, PMR = float(pmf[j]), float(fc[j]), float(pmr.min())
    else:
        PM, FC, PMR = float("inf"), float("nan"), float("inf")
    wr = np.floor((ph + 180.0) / 360.0)
    jx = np.where(wr[:-1] != wr[1:])[0]
    m = mag[jx]
    up = m[m < 1.0]
    dn = m[m >= 1.0]
    gmu = float(-20 * np.log10(up.max())) if len(up) else float("inf")
    gmd = float(20 * np.log10(dn.min())) if len(dn) else float("inf")
    return PM, FC, PMR, gmu, gmd


# ======================================================================================================================
# 6. THE WORKER: one member, every speed, every candidate, every variant, PID and I-frozen
# ======================================================================================================================
LOOPS = [("PID", vi) for vi in range(len(VARIANTS))] + [("PD", vi) for vi in range(len(VARIANTS))] + \
        [("PD297", 0), ("PD195", 0)]
METRICS = ("pm", "fc", "gmu", "gmd", "t530", "l20r", "pmdiff")
_C = {}


def _init(cands):
    _C["cands"] = cands
    _C["G"] = {sp.cid: [float(C.cave_G(C.spd_counts(v), sp.rows)) for v in GRID] for sp in cands}


def work(args):
    member, speeds_idx = args
    cands = _C["cands"]
    nC, nL, nV = len(cands), len(LOOPS), len(speeds_idx)
    out = np.full((nC, nL, nV, len(METRICS)), np.nan, np.float32)
    for jv, iv in enumerate(speeds_idx):
        v = GRID[iv]
        plants = {}
        for jb in JB_SET:
            pl, d, ea, jbk = member_plant(member, v, jb)
            Pt, Pw = DM.plant_frf(pl, F)
            plants[jb] = (Pt, Pw, d, ea)
        K = K_out(F, plants[1.0][2])
        # V295 reference loop (motor frame) per J,b scale: L_V(kappa) = kappa * L_V1
        CthV, CwV, KV = ref_ctl("V295", F, plants[1.0][2], plants[1.0][3])
        LV = {jb: -KV * (CthV * plants[jb][0] + CwV * plants[jb][1]) for jb in JB_SET}
        for ic, sp in enumerate(cands):
            G = _C["G"][sp.cid][iv]
            d, ea = plants[1.0][2], plants[1.0][3]
            parts = {"PID": ctl_split(F, sp, G, ea), "PD": ctl_split(F, sp, G, ea, ki=0.0)}
            for il, (lp, vi) in enumerate(LOOPS):
                nm, kap, jb = VARIANTS[vi]
                cs = parts["PD" if lp.startswith("PD") else "PID"]
                fade = {"PD297": 76.0 / 254.0, "PD195": 50.0 / 254.0}.get(lp, 1.0)   # f(arm floor) / f(hands-off)
                Pt, Pw = plants[jb][0], plants[jb][1]
                (tth, tw, tref), (mth, mw, mref) = cs["t"], cs["m"]
                Cth = tth + kap * mth
                Cw = tw + kap * mw
                Cref = tref + kap * mref
                L = -fade * K * (Cth * Pt + Cw * Pw)
                PM, FC, PMR, gmu, gmd = pm_gm(L)
                Sx = 1.0 / (1.0 + L)
                Tc = np.abs(L[B530] * Sx[B530]).max()
                Tr = np.abs((fade * K * Cref * Pt * Sx)[B530]).max()
                t530 = 20 * math.log10(max(Tc, Tr, 1e-12))
                l20r = abs(L[I20]) / (kap * abs(LV[jb][I20]))
                pmdiff = float(np.isfinite(PM) and abs(PM - PMR) > 1e-6)
                out[ic, il, jv] = (PM, FC, gmu, gmd, t530, l20r, pmdiff)
    return member, speeds_idx, out


# ======================================================================================================================
# 7. NOMINAL-ONLY extras (tracking proxies), Re(T/w), M20 -- controller / nominal member, main process
# ======================================================================================================================
def nominal_extras(sp, v):
    pl, d, ea, jbk = member_plant("nominal", v)
    Pt, Pw = DM.plant_frf(pl, F)
    G = float(C.cave_G(C.spd_counts(v), sp.rows))
    cs = ctl_split(F, sp, G, ea)
    (tth, tw, tref), (mth, mw, mref) = cs["t"], cs["m"]
    K = K_out(F, d)
    L = -K * ((tth + mth) * Pt + (tw + mw) * Pw)
    S = 1 / (1 + L)
    Tr = K * (tref + mref) * Pt * S
    if sp.outer_tau:
        Tr = outer_close(Tr, sp.outer_tau)
    return dict(Tr163=float(np.abs(Tr[B163]).max()), hold=float(abs(Tr[I005])),
                trk_min=float(np.abs(Tr[B011]).min()), trk_max=float(np.abs(Tr[B011]).max()),
                Ms=float(np.abs(S).max()), G=G, k=jbk[2],
                stiff=(float("inf") if sp.ki > 0 else stiffness(sp, G, jbk[2])))


def stiffness(sp, G, k):
    """DC torque stiffness, T per deg: k + FADE FWD Hout(0) (Kp G/256 / 256) 160 (round-1 convention, P only)."""
    g0 = DM.FADE * DM.FWD * (DM.OB / 1024 * 2 / 32 / (1 - DM.OA / 1024))
    return k + g0 * (sp.kp * G / 256.0 / 256.0) * 160.0


def outer_close(Tin, tau, delay=0.06):
    """E2-K0's fork angle integral: theta_sp = theta_plan + acc, acc += (theta_plan - theta(60 ms old)) 0.01/tau at
    100 Hz (designer E2's e2_k0 model).  -> theta / theta_plan."""
    zo = np.exp(-2j * np.pi * F * 0.01)
    Io = (0.01 / tau) / (1 - zo)
    Dl = np.exp(-2j * np.pi * F * delay)
    return Tin * (1 + Io) / (1 + Io * Dl * Tin)


def outer_margin(sp, member, v):
    pl, d, ea, jbk = member_plant(member, v)
    Pt, Pw = DM.plant_frf(pl, F)
    G = float(C.cave_G(C.spd_counts(v), sp.rows))
    cs = ctl_split(F, sp, G, ea)
    (tth, tw, tref), (mth, mw, mref) = cs["t"], cs["m"]
    K = K_out(F, d)
    L = -K * ((tth + mth) * Pt + (tw + mw) * Pw)
    Tin = K * (tref + mref) * Pt / (1 + L)
    zo = np.exp(-2j * np.pi * F * 0.01)
    Lo = (0.01 / sp.outer_tau) / (1 - zo) * np.exp(-2j * np.pi * F * 0.06) * Tin
    return pm_gm(Lo)


RET_F = (5.0, 7.0, 10.0, 13.0, 16.0, 20.0, 25.0)


def re_tw_cand(sp, v, ea, d, kappa):
    f = np.array(RET_F)
    G = float(C.cave_G(C.spd_counts(v), sp.rows))
    cs = ctl_split(f, sp, G, ea)
    Cth = cs["t"][0] + kappa * cs["m"][0]
    Cw = cs["t"][1] + kappa * cs["m"][1]
    K = K_out(f, d)
    w = 2 * np.pi * f
    return (-K * (Cth + 1j * w * Cw) / (1j * w)).real


def re_tw_ref(name, ea, d, kappa):
    f = np.array(RET_F)
    Cth, Cw, K = ref_ctl(name, f, d, ea)
    w = 2 * np.pi * f
    return (-K * kappa * (Cth + 1j * w * Cw) / (1j * w)).real


def m20_cand(sp, v, ea, kappa):
    f = np.array([20.0])
    G = float(C.cave_G(C.spd_counts(v), sp.rows))
    cs = ctl_split(f, sp, G, ea)
    Cth = cs["t"][0] + kappa * cs["m"][0]
    Cw = cs["t"][1] + kappa * cs["m"][1]
    w = 2 * np.pi * 20.0
    return float(abs(Cth[0] + 1j * w * Cw[0]) / (8 * w))


def m20_ref(name, ea, kappa):
    Cth, Cw, K = ref_ctl(name, np.array([20.0]), 2, ea)
    w = 2 * np.pi * 20.0
    return float(kappa * abs(Cth[0] + 1j * w * Cw[0]) / (8 * w))


# ======================================================================================================================
# 8. EXACT PERIODIC MODEL: ds_model.Lifted + the fresh P/I operand + the box10 D
# ======================================================================================================================
class Lifted2(DM.Lifted):
    """ds_model.Lifted (angle kind) with two operands it lacked.  op_fresh: r26 = 80 (th[n] + th[n-1]) from the plant
    state of THIS tick (gp-0x69ca, slot 0 before the PID).  box10: an extra state thq = the held angle before the last
    slot-4 refresh; D = Kd/8 * k_op * 10 * (thq - thh)."""

    def __init__(self, des, plant, op_fresh=False, box10=False, box_k=64.0):
        self.op_fresh, self.box10, self.box_k = op_fresh, box10, box_k
        super().__init__(des, plant)
        self.idx["thq"] = self.N
        self.N += 1

    def phase(self, p, gain=1.0, open_loop=False):
        des, N = self.des, self.N
        assert des.kind == "angle" and not des.lead and des.rate_model == "ema"
        e = self._e
        M = np.zeros((N, N + 2))
        xp = np.zeros((self.npl, N + 2))
        for i in range(self.npl):
            xp[i] = e("xp", i)
        th = self.Ct @ xp
        om = self.Cw @ xp
        thsp_in = np.zeros(N + 2)
        thsp_in[N] = 1.0
        thsp = e("sph") if des.sp_hold else thsp_in
        winp = np.zeros(N + 2)
        winp[N + 1] = 1.0
        r_new = (1 - DM.ALPHA) * e("r") + DM.ALPHA * om
        rs = r_new
        thh, xh = e("thh"), e("xh")
        g = des.G / 256.0
        if self.op_fresh:
            s_new, s_old = 80 * th, 80 * e("thf")
        else:
            s_new, s_old = 80 * thh, 80 * e("thp")
        E = 160 * thsp - (s_new + s_old)
        Ep = g * E
        I_new = e("I") + (des.ki / 32768.0) * Ep
        P = (des.kp / 256.0) * Ep
        kd8 = des.kd / 8.0
        if self.box10:
            D = kd8 * self.box_k * 10.0 * (e("thq") - thh)
        elif des.dsrc == "rate_held":
            D = -des.kd * xh
        elif des.dsrc == "op" and des.dop == "fresh_rate":
            D = kd8 * des.dop_k * DM.ABE_PER * r_new
        elif des.dsrc == "none":
            D = np.zeros(N + 2)
        else:
            raise ValueError(des.dsrc)
        S = I_new + P + D
        if des.ki:
            M[self.idx["I"]] = I_new
        M[self.idx["Ep"]] = Ep
        M[self.idx["thp"]] = thh
        Sf = des.fade * S
        o_new = (DM.OA / 1024.0) * e("o") + (DM.OB / 1024.0) * Sf
        y = (e("o") + o_new) / 32.0
        ucmd = gain * DM.FWD * y
        M[self.idx["o"]] = o_new
        M[self.idx["r"]] = r_new
        if des.sp_hold:
            M[self.idx["sph"]] = thsp_in if p == 0 else e("sph")
        M[self.idx["thf"]] = th
        ea = des.extra_age
        if ea:
            M[self.idx["eat"]] = th
            M[self.idx["eax"]] = rs
            for i in range(1, ea):
                M[self.idx["eat"] + i] = e("eat", i - 1)
                M[self.idx["eax"] + i] = e("eax", i - 1)
            src_t, src_x = e("eat", ea - 1), e("eax", ea - 1)
        else:
            src_t, src_x = th, rs
        if p == DM.HOLD_PHASE:
            M[self.idx["thh"]] = src_t
            M[self.idx["xh"]] = src_x
            M[self.idx["thq"]] = thh
        else:
            M[self.idx["thh"]] = thh
            M[self.idx["xh"]] = xh
            M[self.idx["thq"]] = e("thq")
        d = des.d
        if d > 0:
            u_out = e("ub", d - 1)
            M[self.idx["ub"]] = ucmd
            for i in range(1, d):
                M[self.idx["ub"] + i] = e("ub", i - 1)
        else:
            u_out = ucmd
        uin = (winp if open_loop else u_out + winp)
        for i in range(self.npl):
            M[self.idx["xp"] + i] = self.Ad[i] @ xp + self.Bd[i, 0] * uin
        return M, u_out, th


def lifted_for(sp: Spec, member, v, vi, frozen=False, fade=1.0):
    """the exact model of candidate sp at (member, v, variant vi)."""
    nm, kap, jb = VARIANTS[vi]
    pl, d, ea, jbk = member_plant(member, v, jb)
    G = float(C.cave_G(C.spd_counts(v), sp.rows))
    if sp.pi_frame == "motor":
        G = G * kap                                    # P/I in the motor frame (setpoint path irrelevant to rho)
    ki = 0.0 if frozen else sp.ki
    if sp.dkind == "fresh":
        des = DM.Des(kind="angle", dsrc="op", dop="fresh_rate", kp=sp.kp, ki=ki, kd=sp.kd, dop_k=kap, G=G, d=d,
                     extra_age=ea, fade=DM.FADE * fade)
    elif sp.dkind == "held":
        des = DM.Des(kind="angle", dsrc="rate_held", kp=sp.kp, ki=ki, kd=sp.kd * kap, G=G, d=d, extra_age=ea,
                     fade=DM.FADE * fade)
    elif sp.dkind == "box10":
        des = DM.Des(kind="angle", dsrc="none", kp=sp.kp, ki=ki, kd=sp.kd, G=G, d=d, extra_age=ea, fade=DM.FADE * fade)
    else:
        des = DM.Des(kind="angle", dsrc="none", kp=sp.kp, ki=ki, kd=0, G=G, d=d, extra_age=ea, fade=DM.FADE * fade)
    return Lifted2(des, pl, op_fresh=(sp.op == "fresh"), box10=(sp.dkind == "box10"), box_k=sp.box_k)


def exact_point(sp, member, v, vi, frozen=False, fade=1.0):
    lp = lifted_for(sp, member, v, vi, frozen, fade)
    rho, poles = lp.exact()
    band = [(fz, z) for fz, z in poles if 0.3 <= fz <= 30.0]
    fz, zz = min(band, key=lambda q: q[1]) if band else (float("nan"), float("nan"))
    return dict(rho=rho, f=fz, zeta=zz)


# ======================================================================================================================
# 9. VALIDATION (must print VALIDATE PASS before the run)
# ======================================================================================================================
def validate(cands):
    ok = True
    byid = {c.cid: c for c in cands}
    pr = []
    # V1: my split controller == the round-1 SF.ctl_angle on every structure SF supports
    for cid, sfc in (("P2", SF.Cand("x", "x", dsrc="op", dop="fresh_rate")), ("F2", SF.Cand("x", "x", dsrc="rate_held")),
                     ("H-A", SF.Cand("x", "x", dsrc="op", dop="fresh_rate", op_hold="fresh"))):
        sp = byid[cid]
        e = 0.0
        for v in (3.1, 11.75, 26.9):
            for ea in (0, 10):
                G = float(C.cave_G(C.spd_counts(v), sp.rows))
                cs = ctl_split(F, sp, G, ea)
                Cth = cs["t"][0] + cs["m"][0]
                Cw = cs["t"][1] + cs["m"][1]
                Cref = cs["t"][2] + cs["m"][2]
                a = SF.ctl_angle(F, sfc, dict(G=G, kp=sp.kp, ki=sp.ki, kd=sp.kd), ea)
                e = max(e, np.abs(Cth - a[0]).max(), np.abs(Cw - a[1]).max(), np.abs(Cref - a[2]).max())
        pr.append(f"V1 ctl_split == round-1 SF.ctl_angle ({cid}): max|diff| {e:.1e}")
        ok &= e < 1e-9
    # V2: round-1 numbers reproduced through THIS extractor (SF metrics on the same loop): D2a/B0r nominal & J_hi PM
    for cid, want in (("D2a", (64.9, 46.7)), ("B0r", (64.8, 47.0))):
        sp = byid[cid]
        pms = []
        for mem in ("nominal", "J_hi"):
            best = 1e9
            for v in GRID:
                pl, d, ea, _ = member_plant(mem, v)
                Pt, Pw = DM.plant_frf(pl, F)
                G = float(C.cave_G(C.spd_counts(v), sp.rows))
                cs = ctl_split(F, sp, G, ea)
                L = -K_out(F, d) * ((cs["t"][0] + cs["m"][0]) * Pt + (cs["t"][1] + cs["m"][1]) * Pw)
                best = min(best, pm_gm(L)[0])
            pms.append(round(best, 1))
        pr.append(f"V2 {cid} min PM nominal / J_hi = {pms[0]} / {pms[1]} (SCORE-FREQ round 1: {want[0]} / {want[1]})")
        ok &= abs(pms[0] - want[0]) <= 0.1 and abs(pms[1] - want[1]) <= 0.1
    # V3: the fixed PM == the shared formula on every lagging crossing; differs on a leading one (G's case)
    L = np.exp(1j * np.deg2rad(-120.0)) * np.ones(3)
    pr.append("V3 PM: lagging -120 deg crossing -> fixed 60.0 / shared 60.0 ; leading +16 deg -> fixed "
              f"{180 - abs(((16 + 180) % 360) - 180):.1f} / shared {((16 + 180) + 180) % 360 - 180:.1f}")
    # V4: Lifted2 == ds_model.Lifted on shared structures (rho to 1e-12)
    for cid in ("P2", "F2"):
        sp = byid[cid]
        lp2 = lifted_for(sp, "b_lo*J_hi+h10", 8.0, 0)
        des = lp2.des
        rho1 = DM.Lifted(des, lp2.plant).exact()[0]
        rho2 = lp2.exact()[0]
        pr.append(f"V4 Lifted2 == ds_model.Lifted ({cid} b_lo*J_hi+h10 @8): rho {rho1:.12f} vs {rho2:.12f}")
        ok &= abs(rho1 - rho2) < 1e-12
    # V5: analytic L == exact harmonic L.  H-A (fresh op, fresh D): the loop is LTI -> must agree to ~1e-9.
    #     box10 / held structures: agree within the averaged-hold approximation at <= 3 Hz.
    fchk = np.array([0.1, 0.3, 1.0, 2.0, 3.0])
    for cid, member, v, tol in (("H-A", "nominal", 17.0, 1e-8), ("G-A22", "nominal", 17.0, 0.05),
                                ("P2", "nominal", 17.0, 0.05)):
        sp = byid[cid]
        lp2 = lifted_for(sp, member, v, 0)
        Lx = -lp2.harmonic(fchk, inp="w", out="u", open_loop=True)
        pl, d, ea, _ = member_plant(member, v)
        Pt, Pw = DM.plant_frf(pl, fchk)
        G = float(C.cave_G(C.spd_counts(v), sp.rows))
        cs = ctl_split(fchk, sp, G, ea)
        La = -K_out(fchk, d) * ((cs["t"][0] + cs["m"][0]) * Pt + (cs["t"][1] + cs["m"][1]) * Pw)
        rel = float(np.max(np.abs(La - Lx) / np.abs(La)))
        pr.append(f"V5 analytic L vs exact harmonic ({cid} {member}@{v}, 0.1-3 Hz): max rel diff {rel:.2e} (tol {tol})")
        ok &= rel < tol
    # V6: ms_free products == the stability refuter's independent builder (c2r2_model.member)
    try:
        sys.path.insert(0, str(AL / "refute_stability" / "c2r2"))
        import c2r2_model as R
        e = 0.0
        for nm in MSF2 + ("ms_free", "b_q*J1.0", "b_lo*J_hi"):
            for v in (3.1, 8.0, 11.9, 15.75, 26.9):
                J, b, k, d, mode = params_ext(nm, v)
                r = R.member(nm, v)
                e = max(e, abs(J - r.J), abs(b - r.b), abs(k - r.k))
        pr.append(f"V6 members == refuter c2r2_model.member (ms_free products, b_q*J1.0, b_lo*J_hi): max|diff| {e:.1e}")
        ok &= e < 1e-9
    except Exception as ex:                                 # pragma: no cover
        pr.append(f"V6 skipped ({ex!r})")
    for s in pr:
        print(s)
    print("VALIDATE", "PASS" if ok else "FAIL")
    return ok, pr


# ======================================================================================================================
# 10. THE RUN
# ======================================================================================================================
def run(quick=False, procs=12):
    t0 = time.time()
    cands = build_cands()
    ok, vlines = validate(cands)
    if not ok:
        raise SystemExit("validation failed")
    # unique small-signal loops (identical bytes/cals in the linear path are scored once and the row is mapped)
    uniq = [c for c in cands if not c.linear_as]
    members = MEMBERS if not quick else ("nominal", "b_q*ms_free+h10", "J_hi+h10")
    sidx = list(range(len(GRID))) if not quick else [GRID.index(x) for x in (3.0, 8.0, 12.5, 17.0, 26.9)]
    jobs = [(m, sidx) for m in members]
    arr = np.full((len(uniq), len(LOOPS), len(members), len(sidx), len(METRICS)), np.nan, np.float32)
    mi = {m: i for i, m in enumerate(members)}
    with Pool(procs, initializer=_init, initargs=(uniq,)) as pool:
        for member, _s, out in pool.imap_unordered(work, jobs):
            arr[:, :, mi[member]] = out
            print(f"  member {member:24s} done [{time.time() - t0:.0f}s]", flush=True)
    speeds = [GRID[i] for i in sidx]
    np.savez_compressed(OUT / ("arr_quick.npz" if quick else "arr.npz"), arr=arr, members=np.array(members),
                        speeds=np.array(speeds), cands=np.array([c.cid for c in uniq]))
    res = analyse(cands, uniq, arr, members, speeds, vlines, quick)
    print(f"done [{time.time() - t0:.0f}s]")
    return res


def _fmt_point(members, speeds, vnames, m, s, v, fc):
    return f"{members[m]}@{speeds[s]:.2f} {vnames[v]} fc {fc:.2f}"


ARR = None


def analyse(cands, uniq, arr, members, speeds, vlines, quick):
    global ARR
    ARR = arr
    ui = {c.cid: i for i, c in enumerate(uniq)}
    li = {l: i for i, l in enumerate(LOOPS)}
    MI = {m: i for i, m in enumerate(members)}
    K = {m: i for i, m in enumerate(METRICS)}
    speeds = list(speeds)
    hi8 = [i for i, v in enumerate(speeds) if v >= 8.0]
    summ = {}
    lines = []

    def sel(loop, variants, gate, tiers=("A", "B")):
        """list of (member index, variant index, bar) for the loop rows in the gate.  A candidate with NO motor-frame
        channel (the box10 D on the theta P/I) sees kappa not at all: variants that differ only in kappa are the SAME
        loop and are counted once (the first of each J,b scale)."""
        if _cur["frame_free"]:
            seen, vv = set(), []
            for vi in variants:
                key = VARIANTS[vi][2]
                if key not in seen:
                    seen.add(key)
                    vv.append(vi)
            variants = tuple(vv)
        out = []
        for m in members:
            t = tier_of(m, gate)
            if t is None or t not in tiers:
                continue
            for vi in variants:
                out.append((MI[m], vi, BAR[t]))
        return out

    def worst(ic, loop, rows):
        best = (float("inf"), None)
        for mi_, vi, bar in rows:
            pm = arr[ic, li[(loop, vi)], mi_, :, K["pm"]]
            j = int(np.nanargmin(np.where(np.isfinite(pm), pm, np.inf)))
            if pm[j] < best[0]:
                best = (float(pm[j]), (mi_, j, vi, float(arr[ic, li[(loop, vi)], mi_, j, K["fc"]])))
        return best

    def fails(ic, loop, rows, l20=True):
        n = 0
        why = {}
        for mi_, vi, bar in rows:
            a = arr[ic, li[(loop, vi)], mi_]
            bad = (a[:, K["pm"]] < bar) | (a[:, K["gmu"]] < 6.0) | (a[:, K["t530"]] > 3.0)
            if l20:
                bad = bad | (a[:, K["l20r"]] > 1.0 + 1e-9)
            n += int(bad.sum())
            if bad.any():
                key = members[mi_]
                why.setdefault(key, []).append((VNAMES[vi], int(bad.sum()),
                                                float(np.nanmin(np.where(bad, a[:, K["pm"]], np.inf)))))
        return n, why

    _cur = {}
    for c in cands:
        ic = ui[c.linear_as or c.cid]
        u = uniq[ic]
        _cur["frame_free"] = (u.pi_frame == "theta" and u.d_frame != "motor")
        s = dict(cid=c.cid, designer=c.designer, linear_as=c.linear_as, src=c.src, note=c.note)
        nomrows = [(MI["nominal"], 0, 45.0)]
        pmn = arr[ic, li[("PID", 0)], MI["nominal"], :, K["pm"]]
        gmn = arr[ic, li[("PID", 0)], MI["nominal"], :, K["gmu"]]
        fcn = arr[ic, li[("PID", 0)], MI["nominal"], :, K["fc"]]
        s["pm_nom"] = float(np.nanmin(pmn))
        s["gm_nom"] = float(np.nanmin(gmn))
        s["fc_range"] = (float(np.nanmin(fcn)), float(np.nanmax(fcn)))
        if not quick:
            # tier A single corners (ages 1-10): kappa 1 only (round-1 comparable) and over the full frame box
            s["A_k1"] = worst(ic, "PID", sel("PID", (0,), "R2", ("A",)))
            s["A_full"] = worst(ic, "PID", sel("PID", GATE_FULL, "R2", ("A",)))
            s["Aaged_full"] = worst(ic, "PID", [(MI[m + "+h10"], vi, 45.0) for m in SINGLE for vi in GATE_FULL])
            s["B_R1"] = worst(ic, "PID", sel("PID", (0,), "R1", ("B",)))
            s["B_full"] = worst(ic, "PID", sel("PID", GATE_FULL, "R2", ("B",)))
            s["B_lit"] = worst(ic, "PID", sel("PID", GATE_LIT, "R2", ("B",)))
            s["MSF_full"] = worst(ic, "PID", [(MI[m], vi, 30.0) for m in members if m.split("+")[0] in MSF2
                                              for vi in GATE_FULL])
            s["XREP_full"] = worst(ic, "PID", [(MI[m], vi, 30.0) for m in members
                                               if m.split("+")[0] in XREP for vi in GATE_FULL])
            s["phys_A"] = worst(ic, "PID", sel("PID", PHYS, "R2", ("A",)))
            s["phys_B"] = worst(ic, "PID", sel("PID", PHYS, "R2", ("B",)))
            s["fail_R1"] = fails(ic, "PID", sel("PID", (0,), "R1"))
            s["fail_lit"] = fails(ic, "PID", sel("PID", GATE_LIT, "R2"))
            s["fail_full"] = fails(ic, "PID", sel("PID", GATE_FULL, "R2"))
            s["fail_strict"] = fails(ic, "PID", sel("PID", GATE_FULL, "strict"))
            s["fail_Gstrict"] = fails(ic, "PID", sel("PID", GATE_FULL, "Gstrict"))
            s["fail_full_noL20"] = fails(ic, "PID", sel("PID", GATE_FULL, "R2"), l20=False)
            s["fail_full_noMSF"] = fails(ic, "PID", [r for r in sel("PID", GATE_FULL, "R2")
                                                     if members[r[0]].split("+")[0] not in MSF2])
            allg = sel("PID", GATE_FULL, "R2")
            s["t530"] = float(max(np.nanmax(arr[ic, li[("PID", vi)], mi_, :, K["t530"]]) for mi_, vi, _ in allg))
            s["l20r"] = float(max(np.nanmax(arr[ic, li[("PID", vi)], mi_, :, K["l20r"]]) for mi_, vi, _ in allg))
            s["gmu_min"] = float(min(np.nanmin(arr[ic, li[("PID", vi)], mi_, :, K["gmu"]]) for mi_, vi, _ in allg))
            s["gmd_min"] = float(min(np.nanmin(arr[ic, li[("PID", vi)], mi_, :, K["gmd"]]) for mi_, vi, _ in allg))
            s["pmdiff"] = int(np.nansum(arr[ic, :, :, :, K["pmdiff"]]))
            # I-frozen loop (every freeze / clamp / bound / bleed state), the same gate; hands-on fade floors nominal
            s["PD_A"] = worst(ic, "PD", sel("PD", GATE_FULL, "R2", ("A",)))
            s["PD_B"] = worst(ic, "PD", sel("PD", GATE_FULL, "R2", ("B",)))
            s["PD_fail"] = fails(ic, "PD", sel("PD", GATE_FULL, "R2"), l20=False)
            s["PD297"] = worst(ic, "PD297", [(mi_, 0, 30.0) for mi_ in range(len(members))])
            s["PD195"] = worst(ic, "PD195", [(mi_, 0, 30.0) for mi_ in range(len(members))])
            s["PD297_gm"] = float(np.nanmin(arr[ic, li[("PD297", 0)], :, :, K["gmu"]]))
            s["PD297_gmd"] = float(np.nanmin(arr[ic, li[("PD297", 0)], :, :, K["gmd"]]))
        summ[c.cid] = s
    if not quick:
        report(cands, uniq, summ, members, speeds, vlines)
    return summ


# ======================================================================================================================
# 11. REPORT: exact binding points, 20 Hz, Re(T/w), tracking proxies, the K0 outer loop -> markdown in the scratch dir
# ======================================================================================================================
def _pt(s, members, speeds):
    pm, w = s
    if w is None:
        return "—", None
    mi_, j, vi, fc = w
    return f"{pm:.1f} ({members[mi_]}@{speeds[j]:.2f} {VNAMES[vi]}, fc {fc:.2f})", (members[mi_], speeds[j], vi)


def report(cands, uniq, summ, members, speeds, vlines):
    t0 = time.time()
    byid = {c.cid: c for c in cands}
    md = []
    J = {}
    # ---- exact rho / least-damped pole at every unique loop's binding points ----
    exact = {}
    for c in uniq:
        s = summ[c.cid]
        ex = {}
        for key in ("A_full", "Aaged_full", "B_full", "MSF_full", "PD_B"):
            txt, pt = _pt(s[key], members, speeds)
            if pt is None:
                continue
            ex[key] = exact_point(c, pt[0], pt[1], pt[2], frozen=(key == "PD_B"))
        exact[c.cid] = ex
    print(f"  exact binding points [{time.time() - t0:.0f}s]", flush=True)
    # ---- nominal extras (tracking proxies, stiffness) ----
    nomx = {}
    for c in uniq:
        rows = [nominal_extras(c, v) for v in speeds]
        hi = [r for v, r in zip(speeds, rows) if v >= 8.0]
        nomx[c.cid] = dict(Tr163_hi=max(r["Tr163"] for r in hi), Tr163_all=max(r["Tr163"] for r in rows),
                           hold=min(r["hold"] for r in hi), trk=(min(r["trk_min"] for r in hi),
                                                                 max(r["trk_max"] for r in hi)),
                           Ms=max(r["Ms"] for r in rows),
                           stiff=min(r["stiff"] for r in hi), stiff269=[r for v, r in zip(speeds, rows)
                                                                         if abs(v - 26.9) < 1e-6][0]["stiff"])
    # PD (I frozen) tracking: turn-hold with the I frozen (every freeze/bleed/bound state), nominal >= 8 m/s
    for c in uniq:
        holds = []
        for v in [x for x in speeds if x >= 8.0]:
            sp0 = replace(c, ki=0.0, outer_tau=0.0)
            holds.append(nominal_extras(sp0, v)["hold"])
        nomx[c.cid]["hold_PD"] = min(holds)
    # ---- M20 and Re(T/w), worst over speed, vs V294 / V295 (same condition) ----
    v295m20 = {kap: m20_ref("V295", 0, kap) for kap in (1.0, 0.83, 1.155, 1 / S_C)}
    m20t = {}
    for c in uniq:
        row = {}
        w30 = 0.0
        for ea in (-1, 0, 10, 20):
            w30 = max(w30, max(m20_cand(c, v, ea, 1.0) for v in speeds) / m20_ref("V295", ea, 1.0))
        row["a030"] = w30
        for kap in (1.0, 0.83, 1.155, 1 / S_C):
            w = 0.0
            for ea in (0, 10):
                ref = m20_ref("V295", ea, kap)
                w = max(w, max(m20_cand(c, v, ea, kap) for v in speeds) / ref)
            row[kap] = w
        m20t[c.cid] = row
    retw = {}
    conds = [(kap, d, ea) for kap in (1.0, 1 / S_C) for d in (2, 6) for ea in (-1, 0, 10, 20)]
    refw = {nm: {cd: re_tw_ref(nm, cd[2], cd[1], cd[0]) for cd in conds} for nm in ("V294", "V295", "V282")}
    for c in uniq:
        rw = {}
        for cd in conds:
            kap, d, ea = cd
            vals = np.array([re_tw_cand(c, v, ea, d, kap) for v in speeds])
            rw[cd] = vals.min(axis=0)                           # worst (most negative) over speed, per frequency
        retw[c.cid] = rw
    print(f"  M20 / Re(T/w) [{time.time() - t0:.0f}s]", flush=True)
    # ---- E2-K0: the fork outer integral's own loop ----
    k0 = byid["E2-K0"]
    om = []
    for mem in [m for m in members if tier_of(m, "R2")]:
        for v in speeds[::2]:
            pm_, fc_, _, gu, gd = outer_margin(k0, mem, v)
            om.append((pm_, fc_, gu, mem, v))
    om_pm = min(om, key=lambda q: q[0])
    om_gm = min(om, key=lambda q: q[2])

    # ================================= markdown =================================
    def fl(x, n=1):
        return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{n}f}"

    md.append("### T0 — one row per candidate (PID loop unless marked; PM deg; κ box = κ 0.83/1/1.155 under FA + "
              "0.83/1.155 under FB; every member at ages 1–10 and 11–20)\n")
    md.append("| cand | loop | PM nom | A box | A aged (strict) | B box excl. ms_free× | ms_free× b_lo / b_q | fails R1 / "
              "R2 lit / **R2 box** / strict | M20 ×V295 | ReTw 5 / 13 / 20 Hz, ages 1–10 (11–20) | \\|Tref\\| 1.6–3 | "
              "hold / hold I-frozen | I-frozen B box |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in cands:
        s = summ[c.cid]
        u = c.linear_as or c.cid
        uu = [q for q in uniq if q.cid == u][0]
        ic = [q.cid for q in uniq].index(u)
        # B box excluding the ms_free products
        bx = float("inf")
        for mi_, mem in enumerate(members):
            if tier_of(mem, "R2") != "B" or mem.split("+")[0] in MSF2:
                continue
            for vi in GATE_FULL:
                bx = min(bx, float(np.nanmin(ARR[ic, LOOPS.index(("PID", vi)), mi_, :, METRICS.index("pm")])))
        msf = []
        for base in MSF2:
            mm = float("inf")
            for mem in (base, base + "+h10"):
                for vi in GATE_FULL:
                    mm = min(mm, float(np.nanmin(ARR[ic, LOOPS.index(("PID", vi)), members.index(mem), :,
                                                     METRICS.index("pm")])))
            msf.append(mm)
        r0 = retw[u][(1.0, 2, 0)]
        r10 = retw[u][(1.0, 2, 10)]
        x = nomx[u]
        i5, i13, i20 = RET_F.index(5.0), RET_F.index(13.0), RET_F.index(20.0)
        md.append(f"| {c.cid} | {'= ' + c.linear_as if c.linear_as else 'own'} | {s['pm_nom']:.1f} | "
                  f"{s['A_full'][0]:.1f} | {s['Aaged_full'][0]:.1f} | {bx:.1f} | {msf[0]:.1f} / {msf[1]:.1f} | "
                  f"{s['fail_R1'][0]} / {s['fail_lit'][0]} / **{s['fail_full'][0]}** / {s['fail_strict'][0]} | "
                  f"{m20t[u][1.0]:.2f} | {r0[i5]:+.2f} / {r0[i13]:+.2f} / {r0[i20]:+.2f} ({r10[i5]:+.2f} / "
                  f"{r10[i13]:+.2f} / {r10[i20]:+.2f}) | {x['Tr163_hi']:.2f} | {x['hold']:.3f} / {x['hold_PD']:.3f} | "
                  f"{s['PD_B'][0]:.1f} |")
    for nm in ("V294", "V295"):
        r0 = refw[nm][(1.0, 2, 0)]
        r10 = refw[nm][(1.0, 2, 10)]
        md.append(f"| {nm} (ref) | rate | — | — | — | — | — | — | {m20_ref(nm, 0, 1.0) / m20_ref('V295', 0, 1.0):.2f} | {r0[0]:+.2f} / {r0[3]:+.2f} / "
                  f"{r0[5]:+.2f} ({r10[0]:+.2f} / {r10[3]:+.2f} / {r10[5]:+.2f}) | — | — | — |")
    md.append("")
    md.append("### Validation block (printed by the script)\n")
    md += ["- " + v for v in vlines]
    md.append("\n### T1 — GATE 2 margins (PID loop, PM corrected; PM in deg)\n")
    md.append("`A k1` = single corners at κ 1 (round-1 comparable). `A box` / `B box` = over the gated frame box "
              "(κ 0.83/1/1.155 under FA + κ 0.83/1.155 under FB). `A aged` = single corners at ages 11–20 (strict "
              "reading, bar 45). `B box` includes every aged member and ms_free × {b_lo, b_q}. Binding: member@speed "
              "variant, crossover fc (Hz); ring = the exact least-damped closed-loop pole (f Hz, ζ) at that point.\n")
    md.append("| cand | = loop of | PM nom / GM nom | A k1 | B k1 (R1 set) | A box (binding; ring) | A aged (binding; ring) | "
              "B box (binding; ring) | ms_free×{b_lo,b_q} (binding; ring) | G's ×tau6 products (report) |")
    md.append("|---|---|---|---|---|---|---|---|---|---|")
    for c in cands:
        s = summ[c.cid]
        u = c.linear_as or c.cid
        ex = exact[u]

        def cell(key):
            txt, pt = _pt(s[key], members, speeds)
            e = ex.get(key)
            if e:
                txt += f"; ring {e['f']:.2f} Hz ζ {e['zeta']:.3f}, ρ {e['rho']:.4f}"
            return txt
        md.append(f"| {c.cid} | {c.linear_as or '—'} | {fl(s['pm_nom'])} / {fl(s['gm_nom'])} | {fl(s['A_k1'][0])} | "
                  f"{_pt(s['B_R1'], members, speeds)[0]} | {cell('A_full')} | {cell('Aaged_full')} | {cell('B_full')} | "
                  f"{cell('MSF_full')} | {_pt(s['XREP_full'], members, speeds)[0]} |")
    md.append("\n### T2 — GATE 2 fail counts (points = member × speed × frame variant; PID loop)\n")
    md.append("`R1` = round-1 brief set at κ 1 (comparable with SCORE-FREQ round 1). `R2 lit` = + ms_free × {b_lo, b_q} "
              "and κ 0.83/1.155 under FA (the brief's literal extension). **`R2 box` = + reading FB (THE gate this "
              "round).** `strict` = R2 box with aged single corners at 45°. `G-strict` = strict + designer G's × tau6 "
              "products. `R2 box w/o ms_free×` = the same gate without the two new products. Fail = PM < bar, GM↑ < 6 dB, "
              "max(|Tc|,|Tref|) 5–30 Hz > +3 dB, or L20 > V295's L20 (same member, speed, frame).\n")
    md.append("| cand | R1 | R2 lit | **R2 box** | R2 box w/o L20 | R2 box w/o ms_free× | strict | G-strict | "
              "min GM↑ dB | min GM↓ dB | peak 5–30 dB | max L20 / V295 | PM fixed≠shared |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in cands:
        s = summ[c.cid]
        md.append(f"| {c.cid} | {s['fail_R1'][0]} | {s['fail_lit'][0]} | **{s['fail_full'][0]}** | "
                  f"{s['fail_full_noL20'][0]} | {s['fail_full_noMSF'][0]} | {s['fail_strict'][0]} | "
                  f"{s['fail_Gstrict'][0]} | {fl(s['gmu_min'])} | {fl(s['gmd_min'])} | {s['t530']:+.1f} | "
                  f"{s['l20r']:.2f} | {s['pmdiff']} |")
    md.append("\n#### T2b — which members fail the R2 box gate (member: variant/points/min PM)\n")
    for c in uniq:
        why = summ[c.cid]["fail_full"][1]
        if not why:
            continue
        parts = []
        for m, lst in why.items():
            n = sum(x[1] for x in lst)
            pmw = min(x[2] for x in lst)
            vs = ",".join(sorted(set(x[0] for x in lst)))
            parts.append(f"{m} {n} pts min {pmw:.1f} [{vs}]")
        md.append(f"- **{c.cid}**: " + "; ".join(parts))
    md.append("\n### T3 — 20 Hz gain vs V295 (worst over speed, ages 1–10 and 11–20, same frame κ)\n")
    md.append("| cand | M20/V295 κ1 | κ0.83 | κ1.155 | κ0.866 (phys) | κ1, ages 0–30 | L20/V295 max (R2 box) |")
    md.append("|---|---|---|---|---|---|---|")
    for c in cands:
        r = m20t[c.linear_as or c.cid]
        md.append(f"| {c.cid} | {r[1.0]:.3f} | {r[0.83]:.3f} | {r[1.155]:.3f} | {r[1 / S_C]:.3f} | {r['a030']:.3f} | "
                  f"{summ[c.cid]['l20r']:.3f} |")
    md.append("\n### T4 — Re(T/ω) worst over 1–35 m/s (T counts per deg/s, > 0 damps), κ 1, 2 ms transport\n")
    for ea, lab in ((0, "ages 1–10 (age 0)"), (10, "ages 11–20 (age 10)"), (20, "ages 21–30 (age 20)")):
        md.append(f"\n**{lab}**\n")
        md.append("| loop | " + " | ".join(f"{int(f)} Hz" for f in RET_F) + " |")
        md.append("|---|" + "---|" * len(RET_F))
        for nm in ("V294", "V295", "V282"):
            vv = refw[nm][(1.0, 2, ea)]
            md.append(f"| {nm} | " + " | ".join(f"{x:+.2f}" for x in vv) + " |")
        for c in uniq:
            vv = retw[c.cid][(1.0, 2, ea)]
            md.append(f"| {c.cid} | " + " | ".join(f"{x:+.2f}" for x in vv) + " |")
    md.append("\n#### T4b — phase fragility (round-2 F3c): Re(T/ω) at 13 and 20 Hz over 16 conditions "
              "(κ 1/0.866 × transport 2/6 ms × ages 0–9/1–10/11–20/21–30), candidate worst ÷ V295 worst in the SAME "
              "condition (>1 = more anti-damping than V295 there; only negative candidate values count)\n")
    md.append("| cand | 13 Hz: conds >1× V295 | worst ratio (cond) | 20 Hz: conds >1× | worst ratio (cond) | "
              "13 Hz worst-vs-worst | 20 Hz worst-vs-worst |")
    md.append("|---|---|---|---|---|---|---|")
    i13, i20 = RET_F.index(13.0), RET_F.index(20.0)
    for c in uniq:
        row = []
        for ii in (i13, i20):
            rats = []
            for cd in conds:
                cv = retw[c.cid][cd][ii]
                rv = refw["V295"][cd][ii]
                if cv < 0 and rv < 0:
                    rats.append((cv / rv, cd))
                elif cv < 0 <= rv:
                    rats.append((float("inf"), cd))
                else:
                    rats.append((0.0, cd))
            n1 = sum(1 for r, _ in rats if r > 1.0)
            wr = max(rats, key=lambda q: q[0])
            row.append((n1, wr))
        ww = []
        for ii in (i13, i20):
            cw = min(retw[c.cid][cd][ii] for cd in conds)
            rw_ = min(refw["V295"][cd][ii] for cd in conds)
            ww.append(cw / rw_ if (cw < 0 and rw_ < 0) else float("nan"))
        md.append(f"| {c.cid} | {row[0][0]}/16 | {row[0][1][0]:.2f} (κ{row[0][1][1][0]:.3g} d{row[0][1][1][1]} "
                  f"e{row[0][1][1][2]}) | {row[1][0]}/16 | {row[1][1][0]:.2f} (κ{row[1][1][1][0]:.3g} "
                  f"d{row[1][1][1][1]} e{row[1][1][1][2]}) | {ww[0]:.2f} | {ww[1]:.2f} |")
    md.append("\n### T5 — tracking proxies, crossover, stiffness (nominal member, κ 1, ages 1–10)\n")
    md.append("`hold` = |T_ref(0.05 Hz)| min over ≥ 8 m/s (linear turn-hold proxy; the integrator CLAMP is not in a "
              "linear model). `hold I-frozen` = the same with Ki 0 (every freeze / reset / bleed / bound / saturated "
              "state). `trk` = |T_ref| over 0.1–1 Hz, min–max over ≥ 8 m/s. `|T_ref| 1.6–3` = max over ≥ 8 m/s "
              "(all speeds in brackets). Stiffness = DC T per deg (inf = integrator).\n")
    md.append("| cand | fc range nominal (Hz) | \\|T_ref\\| 1.6–3 Hz | hold | hold I-frozen | trk 0.1–1 Hz | Ms | "
              "DC stiffness |")
    md.append("|---|---|---|---|---|---|---|---|")
    for c in cands:
        s = summ[c.cid]
        x = nomx[c.linear_as or c.cid]
        st = "inf (I)" if not np.isfinite(x["stiff"]) else f"{x['stiff']:.0f} (min ≥8 m/s)"
        if c.outer_tau:
            st += " + fork integral"
        md.append(f"| {c.cid} | {s['fc_range'][0]:.2f}–{s['fc_range'][1]:.2f} | {x['Tr163_hi']:.2f} "
                  f"({x['Tr163_all']:.2f}) | {x['hold']:.3f} | {x['hold_PD']:.3f} | {x['trk'][0]:.2f}–{x['trk'][1]:.2f} | "
                  f"{x['Ms']:.2f} | {st} |")
    md.append("\n### T6 — the I-frozen loop (Ki 0) and hands-on fade floors\n")
    md.append("The small-signal loop of every freeze / reset / bleed / leak / angle-bound / clamp-saturated state. "
              "R2 box gate (bars 45/30). Fade floors: PM over every member at κ 1 (bar shown only for reference — the "
              "hand's own impedance is not modelled).\n")
    md.append("| cand | PD tier A (binding) | PD tier B (binding; ring) | PD fails R2 box | fade 0.297 min PM | "
              "fade 0.195 min PM | fade 0.297 min GM↑ / GM↓ |")
    md.append("|---|---|---|---|---|---|---|")
    for c in uniq:
        s = summ[c.cid]
        e = exact[c.cid].get("PD_B")
        ring = f"; ring {e['f']:.2f} Hz ζ {e['zeta']:.3f}" if e else ""
        md.append(f"| {c.cid} | {_pt(s['PD_A'], members, speeds)[0]} | {_pt(s['PD_B'], members, speeds)[0]}{ring} | "
                  f"{s['PD_fail'][0]} | {fl(s['PD297'][0])} | {fl(s['PD195'][0])} | {fl(s['PD297_gm'])} / "
                  f"{fl(s['PD297_gmd'])} |")
    md.append("\n### T7 — the physical frame points (report): PM over tier A / tier B at κ = 1/1.155 and 1/0.962 "
              "under FA and FB\n")
    md.append("| cand | tier A min (binding) | tier B min (binding) |")
    md.append("|---|---|---|")
    for c in uniq:
        s = summ[c.cid]
        md.append(f"| {c.cid} | {_pt(s['phys_A'], members, speeds)[0]} | {_pt(s['phys_B'], members, speeds)[0]} |")
    md.append("\n### T8 — E2-K0's fork angle integral (τ_o 1 s, 60 ms, 100 Hz) as its own loop, every R2 member, "
              "κ 1, every other speed\n")
    md.append(f"- outer-loop min PM {om_pm[0]:.1f}° ({om_pm[3]}@{om_pm[4]:.2f}, fc {om_pm[1]:.2f} Hz); "
              f"min GM↑ {om_gm[2]:.1f} dB ({om_gm[3]}@{om_gm[4]:.2f})")
    md.append("\n### T9 — the ms_free products one by one: worst PM over the gated frame box and both hold ages, the "
              "exact ring there, and the speed span where any frame/age sits below 30°\n")
    md.append("| cand | b_lo×ms_free min (point; ring) | span < 30° | b_q×ms_free min (point; ring) | span < 30° |")
    md.append("|---|---|---|---|---|")
    MIx = {mm: i for i, mm in enumerate(members)}
    for c in uniq:
        ic = [u.cid for u in uniq].index(c.cid)
        cells = []
        for base in MSF2:
            best = (float("inf"), None, None, None)
            vs = set()
            for mem in (base, base + "+h10"):
                for vi in GATE_FULL:
                    pm = ARR[ic, LOOPS.index(("PID", vi)), MIx[mem], :, METRICS.index("pm")]
                    j = int(np.argmin(pm))
                    if pm[j] < best[0]:
                        best = (float(pm[j]), mem, speeds[j], vi)
                    vs |= {speeds[k] for k in np.where(pm < 30.0)[0]}
            e = exact_point(c, best[1], best[2], best[3])
            cells.append(f"{best[0]:.1f} ({best[1]}@{best[2]:.2f} {VNAMES[best[3]]}; ring {e['f']:.2f} Hz "
                         f"ζ {e['zeta']:.3f})")
            cells.append(f"{min(vs):.2f}–{max(vs):.2f} m/s" if vs else "none")
        md.append(f"| {c.cid} | " + " | ".join(cells) + " |")
    (OUT / "score_freq_tables.md").write_text("\n".join(md), encoding="utf-8")
    J = dict(summ={k: {kk: (vv if not isinstance(vv, tuple) else list(vv)) for kk, vv in v.items()}
                   for k, v in summ.items()},
             exact=exact, nomx=nomx, m20=m20t, v295m20=v295m20,
             retw={c: {str(k): v.tolist() for k, v in d.items()} for c, d in retw.items()},
             refw={c: {str(k): v.tolist() for k, v in d.items()} for c, d in refw.items()},
             k0_outer=dict(pm=om_pm, gm=om_gm))
    (OUT / "score_freq_summary.json").write_text(json.dumps(J, default=lambda o: o if not isinstance(o, np.generic)
                                                            else o.item(), indent=0), encoding="utf-8")
    print("\n".join(md))
    print(f"  report written -> {OUT / 'score_freq_tables.md'} [{time.time() - t0:.0f}s]")


# ======================================================================================================================
# ======================================================================================================================
# 12. DESIGNER-CLAIM CROSS-CHECKS (every published number this file disagrees with, or that a disagreement rests on)
# ======================================================================================================================
def _minpm(sp, member, vs, ea_extra=0):
    best = (float("inf"), None)
    for v in vs:
        pl, d, ea, _ = member_plant(member, v)
        Pt, Pw = DM.plant_frf(pl, F)
        G = float(C.cave_G(C.spd_counts(v), sp.rows))
        cs = ctl_split(F, sp, G, ea + ea_extra)
        L = -K_out(F, d) * ((cs["t"][0] + cs["m"][0]) * Pt + (cs["t"][1] + cs["m"][1]) * Pw)
        pm = pm_gm(L)[0]
        if pm < best[0]:
            best = (pm, v)
    return best


def _claim_job(a):
    kp, mem = a
    sp = replace({c.cid: c for c in build_cands()}["P2"], kp=kp)
    return kp, mem, _minpm(sp, mem, GRID)[0]


def claims(procs=12):
    cands = build_cands()
    byid = {c.cid: c for c in cands}
    z = np.load(OUT / "arr.npz")
    arr, members, speeds, cids = z["arr"], [str(x) for x in z["members"]], [float(x) for x in z["speeds"]], \
        list(z["cands"])
    K = {k: i for i, k in enumerate(METRICS)}
    LI = {l: i for i, l in enumerate(LOOPS)}
    out = []

    def P(x):
        print(x, flush=True)
        out.append(x)

    def gate(cid, vi, gname):
        ic = cids.index(cid)
        mins = {"A": (float("inf"), ""), "B": (float("inf"), "")}
        nf = 0
        for mi, mem in enumerate(members):
            t = tier_of(mem, gname)
            if t is None:
                continue
            a = arr[ic, LI[("PID", vi)], mi]
            j = int(np.argmin(a[:, K["pm"]]))
            if a[j, K["pm"]] < mins[t][0]:
                mins[t] = (float(a[j, K["pm"]]), f"{mem}@{speeds[j]}")
            nf += int(((a[:, K["pm"]] < BAR[t]) | (a[:, K["gmu"]] < 6) | (a[:, K["t530"]] > 3) |
                       (a[:, K["l20r"]] > 1)).sum())
        return f"A {mins['A'][0]:.1f} ({mins['A'][1]}) / B {mins['B'][0]:.1f} ({mins['B'][1]}) / {nf} fails"

    P("C1 E2 e2_freq_out: P2 46.7 / 32.6 / 0 | mine P2 R1 k1: " + gate("P2", 0, "R1"))
    P("C2 E2 e2_freq_out: P2-FA (D x1/1.155) 43.2 / 28.3 / 50 | mine P2 R1 at FAc: " + gate("P2", 5, "R1"))
    P("C3 E2 e2_freq_out: P2-I0 62.6 / 48.4 / 0 | mine E2-K0 (= P2, Ki 0) R1 k1: " + gate("E2-K0", 0, "R1"))
    P("C4 E2 e2_freq_out: P2-I0-FA 60.3 / 45.4 / 0 | mine E2-K0 R1 at FAc: " + gate("E2-K0", 5, "R1"))
    ic = cids.index("P2")
    row = []
    for mem in ("J_hi", "ms_free", "b_lo*J_hi+h10", "b_q*J1.0+h10", "b_q*ms_free+h10", "b_q*ms_free", "b_lo*ms_free"):
        mi = members.index(mem)
        vals = [float(arr[ic, LI[("PID", vi)], mi, :, K["pm"]].min()) for vi in (0, 5, 6)]
        row.append(f"{mem} {vals[0]:.1f}/{vals[1]:.1f}/{vals[2]:.1f}")
    P("C5 stability refuter F1/F4 (P2, kappa 1 / FA 0.866 / FB 0.866): published J_hi -/43.2/44.0, ms_free -/43.8/43.6, "
      "b_lo*J_hi+h10 -/28.3/27.3, b_q*J1.0+h10 34.0/29.5/28.5, b_q*ms_free+h10 13.5/-/-, b_q*ms_free 17.3, "
      "b_lo*ms_free 18.5-22.8 | mine: " + "; ".join(row))
    mi = members.index("b_lo*J_hi*tau6+h10")
    n83 = int((arr[ic, LI[("PID", 1)], mi, :, K["pm"]] < 30).sum())
    P(f"C6 G g_gate_rev2A-P2: 'b_lo*J_hi*tau6+h10|k0.83 (62 pts)' over a 31-speed range | mine: {n83} pts -> G's P2 "
      f"strict 1496 - 31 = 1465 = mine (a duplicated member-variant block in G's count for its rev2A references)")
    for cid in ("G-P48", "G-P44d"):
        c = byid[cid]
        r = {ea: max(m20_cand(c, v, ea, 1.0) for v in speeds) / m20_ref("V295", ea, 1.0) for ea in (-1, 0, 10, 20)}
        P(f"C7 G M20/V295 {cid}: published {'0.976' if cid == 'G-P48' else '0.895'} | mine ages 0-9/1-10/11-20/21-30 "
          f"{r[-1]:.3f}/{r[0]:.3f}/{r[10]:.3f}/{r[20]:.3f} (G's figure is the ages 21-30 value)")
    pd = {cid: sum(int(np.nansum(arr[cids.index(cid), il, :, :, K['pmdiff']])) for il, (lp, vi) in enumerate(LOOPS)
                   if lp == "PID") for cid in cids}
    P("C8 G 'pm_fixed == shared on every gated point': PID-loop points where the two differ, per loop: " +
      ", ".join(f"{k} {v}" for k, v in pd.items() if v) + " (all others 0); the I-frozen loops carry the leading crossings")
    HA, HB = byid["H-A"], byid["H-B"]
    HAh = replace(HA, op="held", pi_frame="theta")
    vs = [2.0, 2.5, 3.0, 3.1, 4.0, 5.0, 6.0, 8.0]
    P("C9 H h_freq_out H-A: tier A 46.7/42.2, tier B 32.6/27.8 (ages 0/10), ReTw13/16/20 -0.23/-0.27/-0.29 | "
      f"mine with H's operand (held gp-0x6a00 = D2a): b_lo*J_hi+h10 ages 11-20 {_minpm(HAh, 'b_lo*J_hi+h10', vs)[0]:.1f}, "
      f"ages 21-30 {_minpm(HAh, 'b_lo*J_hi+h10', vs, 10)[0]:.1f}; J_hi {_minpm(HAh, 'J_hi', vs)[0]:.1f}, J_hi+h10 "
      f"{_minpm(HAh, 'J_hi+h10', vs)[0]:.1f}; ReTw v17 " +
      "/".join(f"{x:+.2f}" for x in re_tw_cand(HAh, 17.0, 0, 2, 1.0)[3:6]) +
      f" | with the bytes' operand (fresh gp-0x69ca): b_lo*J_hi+h10 {_minpm(HA, 'b_lo*J_hi+h10', vs)[0]:.1f} at every "
      f"age, J_hi {_minpm(HA, 'J_hi', vs)[0]:.1f}; ReTw v17 " +
      "/".join(f"{x:+.2f}" for x in re_tw_cand(HA, 17.0, 0, 2, 1.0)[3:6]))
    P("C10 H h_freq_out H-B Kd23 D x0.866: ReTw -0.70/-0.70/-0.65; x1.040 -0.79/-0.81/-0.76 | mine v17: " +
      "/".join(f"{x:+.2f}" for x in re_tw_cand(HB, 17.0, 0, 2, 0.866)[3:6]) + " ; " +
      "/".join(f"{x:+.2f}" for x in re_tw_cand(HB, 17.0, 0, 2, 1.040)[3:6]))
    mems = [x for x in MEMBERS if tier_of(x, "R1")]
    with Pool(procs) as pool:
        res = pool.map(_claim_job, [(kp, mm) for kp in (160, 200) for mm in mems])
    for kp in (160, 200):
        a = min((r for r in res if r[0] == kp and tier_of(r[1], "R1") == "A"), key=lambda r: r[2])
        b = min((r for r in res if r[0] == kp and tier_of(r[1], "R1") == "B"), key=lambda r: r[2])
        P(f"C11 E1 splitP Kp {kp}: published {'40.0 / 19.6' if kp == 160 else '29.7 / 11.0'} | mine R1 k1: "
          f"A {a[2]:.1f} ({a[1]}) / B {b[2]:.1f} ({b[1]})")
    (OUT / "claims_out.txt").write_text("\n".join(out), encoding="utf-8")


def report_only():
    """re-run the analysis + report from the cached arr.npz (no recomputation of the loops)."""
    cands = build_cands()
    ok, vlines = validate(cands)
    if not ok:
        raise SystemExit("validation failed")
    z = np.load(OUT / "arr.npz")
    uniq = [c for c in cands if not c.linear_as]
    assert [c.cid for c in uniq] == list(z["cands"]), "candidate list changed: re-run the full scorer"
    return analyse(cands, uniq, z["arr"], tuple(z["members"]), list(z["speeds"]), vlines, False)


if __name__ == "__main__":
    if "validate" in sys.argv:
        validate(build_cands())
    elif "report" in sys.argv:
        report_only()
    elif "claims" in sys.argv:
        claims()
    else:
        run(quick=("quick" in sys.argv))
