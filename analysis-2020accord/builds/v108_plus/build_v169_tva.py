#!/usr/bin/env python3
r"""
V169 -- BASE-ASSIST SLOPE CAP at 1792 (2.2x).  Base = V158.  DOSE LADDER member.

Same single edit as V168 (`0xC6384`), at a different dose, through V168's own verified builder --
one builder, four build numbers, so the assertions and the CRC/readback path cannot drift apart.

WHEN TO FLY THIS ONE
--------------------
the SMALLER step, if V168 reads clean on the ratchet but too heavy on FEEL

PREDICTED EFFECT, on the GATE 2 anchoring in build_v168_tva.py:
    cap 1792 => s = 1.750 => |L| = 2.575 => |1-P.L| = 0.1523 => Q ratio 6.57
    = 2.2x more damped than stock (cap 2048, Q ratio 14.29)

The feel cost rises monotonically with the dose: the cap binds on the LOW-torque segments, so a
lower cap means heavier steering near centre.  Peak authority and max rates are untouched at every
dose (the curve is uncapped above X ~ 450), and no dose touches the LKAS lane (`0xC616C`=0 forces
`gp-0x6b4a` identically zero).

Read `build_v168_tva.py` for the full derivation, the measurement it rests on, and the
pre-registered three-way outcome.  BUILT, UNFLASHED.
"""
import sys
from pathlib import Path

# --- PATH BOOTSTRAP ---------------------------------------------------------------------------
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
for _sub in ("builds", "lib", "model", "verify", "extract"):
    _q = _d / _sub
    if _q.is_dir():
        for _r in [_q] + [p for p in _q.iterdir() if p.is_dir()]:
            if str(_r) not in sys.path:
                sys.path.insert(0, str(_r))

import build_v168_tva as V168                                                     # noqa: E402

CAP_NEW = 1792


def build():
    return V168.build(cap_new=CAP_NEW, vnum=169, write_env="ACCORD_V169_WRITE")


if __name__ == "__main__":
    build()
