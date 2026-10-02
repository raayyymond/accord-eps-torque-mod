# -*- coding: utf-8 -*-
r"""rev_common.py -- V299 REVISION (rev 2) shared loaders.  ANALYSIS ONLY: builds no image, flashes nothing, sends nothing.

Two engines, both re-used UNCHANGED except for two per-column switches added by exact-once source substitution
(asserted), each a no-op at its default so the transformed engine reproduces the original bit for bit (rev_control.py):
  (1) the A3 low-speed cap: speed threshold `capv` (V298 1382) and cap value `capval` (V298 4096) per column -- the two
      cave immediates the rev-2 byte edit changes (0xC4C9C movea imm16, 0xC4CA4 movea imm16);
  (2) the fork takeover after an O1 release is skipped when the O1 episode lasted < `short_n` frames (default 0 = always
      ramp, = rev 1).
S2  = scores/S2-time-nonlinear/s2_time.py (the common time/nonlinear scorer)
RSN = refute/rsn_engine.py (the stability refuter's own engine; it already carries capv/capval as a lane variant)
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

HERE = Path(__file__).resolve().parent
V299 = HERE.parent
KIT = V299.parents[3]
OUT = KIT / "_scratch" / "v299_REV2"
OUT.mkdir(parents=True, exist_ok=True)


def _sub(src, old, new, n=1):
    k = src.count(old)
    assert k == n, (old[:60], k)
    return src.replace(old, new)


def _load_from_source(name, path, src):
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    sys.modules[name] = mod
    exec(compile(src, str(path), "exec"), mod.__dict__)
    return mod


def load_s2(name="s2_time_rev2"):
    if name in sys.modules:
        return sys.modules[name]
    p = V299 / "scores" / "S2-time-nonlinear" / "s2_time.py"
    s = p.read_text(encoding="utf-8")
    s = _sub(s, "FWD = dict(rows=GBP, thr=512, sgn=300, asym=False, d4=False, d5a=False, scl=15360, pcl=15360)",
             "FWD = dict(rows=GBP, thr=512, sgn=300, asym=False, d4=False, d5a=False, scl=15360, pcl=15360, capv=1382, capval=4096, caplo_v=1382, caplo=4096)")
    s = _sub(s, 'for k in ("asym", "d4", "d5a", "scl", "pcl"):', 'for k in ("asym", "d4", "d5a", "scl", "pcl", "capv", "capval", "caplo_v", "caplo"):')
    s = _sub(s, "self.capon = (self.vw & 0xFFFF) <= 1382",
             'self.capon = (self.vw & 0xFFFF) <= g("capv", 1382).astype(np.int64)\n'
             '        self.capval = np.where((self.vw & 0xFFFF) <= g("caplo_v", 1382).astype(np.int64), '
             'g("caplo", 4096).astype(np.int64), g("capval", 4096).astype(np.int64))')
    s = _sub(s, "bound = np.where(self.capon & (bound > 4096), 4096, bound)",
             "bound = np.where(self.capon & (bound > self.capval), self.capval, bound)")
    s = _sub(s, "o1lead=0.06, take=0.0, k4=False,", "o1lead=0.06, take=0.0, short_n=0.0, k4=False,")
    s = _sub(s, 'o1lead, take, acc = F("o1lead"), F("take"), F("acc") * 1e-4',
             'o1lead, take, acc = F("o1lead"), F("take"), F("acc") * 1e-4\n'
             '    shortn = F("short_n")\n    EPL = np.zeros(B)')
    s = _sub(s, "                since = np.where(rel, 0.0, since)\n",
             "                since = np.where(rel & (EPL >= shortn), 0.0, since)\n"
             "                EPL = np.where(o1, EPL + 1, 0)\n")
    return _load_from_source(name, p, s)


def load_s2_orig(name="s2_time_orig"):
    if name in sys.modules:
        return sys.modules[name]
    p = V299 / "scores" / "S2-time-nonlinear" / "s2_time.py"
    sp = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m
    sp.loader.exec_module(m)
    return m


def load_rsn(name="rsn_engine_rev2"):
    if name in sys.modules:
        return sys.modules[name]
    p = V299 / "refute" / "rsn_engine.py"
    s = p.read_text(encoding="utf-8")
    s = _sub(s, '    hard_n = np.array([f.get("hard_n", 1) for f in fk], float)\n',
             '    hard_n = np.array([f.get("hard_n", 1) for f in fk], float)\n'
             '    shortn = np.array([f.get("short_n", 0) for f in fk], float)\n'
             '    EPL = np.zeros(B)\n')
    s = _sub(s, "                since = np.where(rel, 0.0, since)\n",
             "                since = np.where(rel & (EPL >= shortn), 0.0, since)\n"
             "                EPL = np.where(o1, EPL + 1, 0)\n")
    m = _load_from_source(name, p, s)
    # rev-2 fork variants (config A + a takeover rule); V298 / A / B kept as the refuter defined them
    m.FORKS["A_s5"] = dict(m.FORKS["A"], short_n=5)          # no takeover after O1 episodes < 50 ms
    m.FORKS["A_T02"] = dict(m.FORKS["A"], take=0.2)          # takeover 0.2 s
    return m


def load_rsn_orig():
    sys.path.insert(0, str(V299 / "refute"))
    import rsn_engine as E  # noqa
    return E


# S2 two-level form: cap applies at v <= capv; value caplo at v <= caplo_v else capval (defaults = V298 single level)
REV2_S2 = dict(thr=1229, sgn=0, asym=True, capv=2880, capval=6144, caplo_v=1382, caplo=4096)
# the rev-2 firmware cap candidates (speed-word threshold, cap value in S units = I8 >> 10)
CAP_V298 = dict(capv=1382, capval=4096)
CAPS = {k: dict(capv=v, capval=c, caplo_v=v, caplo=c) for k, (v, c) in
        {"rev1": (1382, 4096), "c4096": (2880, 4096), "c5120": (2880, 5120), "c6144": (2880, 6144), "c7168": (2880, 7168)}.items()}
# (single-level forms: caplo = capval, caplo_v = capv, so the S2 two-level switch degenerates to one value)
