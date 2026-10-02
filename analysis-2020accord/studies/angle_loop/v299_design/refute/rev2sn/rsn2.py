# -*- coding: utf-8 -*-
r"""rsn2.py -- RE-REFUTER (stability-nonlinear) of DESIGN-V299-SYNTHESIS-rev2: shared setup on MY engine (the stability
refuter's rsn_engine.py, imported UNCHANGED -- not the reviser's source-substituted copy) plus the S2 common scorer via
the reviser's loader (verified against my lane in rsn2_control.py).  ANALYSIS ONLY: nothing built/flashed/sent.
Systems:
  V298  = rule V298 (512/300 freeze, symmetric A3, cap 4096 <= 1382) + V298 fork (O1 600/500, lead 0.06)
  R2    = rule V299 (1229, no opposing clause, asym) + TWO-LEVEL cap (4096 <= 1382, 6144 1382 < v <= 2880)
          + fork NoO1 (config A: cap 120 deg/s, clip x1.0, NO override -- ruling (i))   <- THE DRIVE
  R1N   = rev-1 firmware (cap 4096 <= 1382 only) + NoO1 fork  (attribution of the cap edit)
  R2G   = rev 2 firmware + the G4 fork 'A' (record only)
"""
from __future__ import annotations
import os, sys
from pathlib import Path
import numpy as np
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
HERE = Path(__file__).resolve().parent
REF = HERE.parent
V299 = REF.parent
sys.path.insert(0, str(REF))
sys.path.insert(0, str(V299 / "revise"))
import rsn_engine as E  # noqa: E402
import rsn_common as C  # noqa: E402

KIT = V299.parents[3]
OUT = KIT / "_scratch" / "v299_RR2SN"
OUT.mkdir(parents=True, exist_ok=True)
E.FORKS["NoO1"] = dict(cap=120.0, clipx=1.0, on=1e9, hard=1e9, deb=0, off=500.0, lead=0.0, take=0.0)


def vword(v):
    return int(np.round(v * 3.6 * 64))          # the engine's own conversion (run())


def cap2(v):
    return dict(capv=2880, capval=4096 if vword(v) <= 1382 else 6144)


def sysd(name, v):
    return {"V298": ("V298", "V298", {}), "R2": ("V299", "NoO1", cap2(v)), "R1N": ("V299", "NoO1", {}),
            "R2G": ("V299", "A", cap2(v))}[name]


def col(name, member, v, **kw):
    r, f, var = sysd(name, v)
    d = dict(sys=name, rule=r, fork=f, variant=var, member=member, v=v)
    d.update(kw)
    return d


def load_s2():
    import rev_common as RC
    S2 = RC.load_s2()
    S2.FK["NoO1"] = dict(inst=1e9, d600=0, hi_n=0, o1lead=0.0, take=0.0)
    S2.FW["rev2"] = dict(RC.REV2_S2)
    S2.FW["rev1"] = dict(thr=1229, sgn=0, asym=True)
    S2.CANDS = {"V298": ("V298", "V298", ""), "R2": ("rev2", "NoO1", ""), "R1N": ("rev1", "NoO1", "")}
    S2.CIDS = tuple(S2.CANDS)
    return S2
