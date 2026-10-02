# -*- coding: utf-8 -*-
r"""rev_r79.py -- route-79 counterfactuals (D1's d1_r79.py, its arithmetic UNCHANGED) with the REV-2 rule added: D1c's hand
rule + asymmetric bound + the TWO-LEVEL A3 cap (4096 S at v-word <= 1382, 6144 S at 1382 < v <= 2880).  Loaded from
source with exact-once substitutions (asserted): the output folder moved to _scratch/v299_REV2/d1r79 (D1's out/ is not
touched), bound_with_cap() taught the two-level form, one RULES row and the window-discriminator row added.  Reports the
A3-bound share and the open-loop replay tap for rev 2 vs rev 1 (D1c), and the rule-identity power (F1's instrument) for
rev 2 vs V298 on route 79's own wire.  ANALYSIS ONLY.  usage: python rev_r79.py  (< 30 s)"""
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
V299 = HERE.parent
KIT = V299.parents[3]
SRC = V299 / "D1-firmware-minimal" / "d1_r79.py"
OUTD = KIT / "_scratch" / "v299_REV2" / "d1r79"
OUTD.mkdir(parents=True, exist_ok=True)


def sub(s, old, new):
    assert s.count(old) == 1, (old[:70], s.count(old))
    return s.replace(old, new)


s = SRC.read_text(encoding="utf-8")
s = sub(s, 'OUT = HERE / "out"', f'OUT = Path(r"{OUTD}")')
s = sub(s, "    return np.where((vwm <= 1382) & (b > cap), cap, b)",
        "    if isinstance(cap, tuple):                                          # REV 2: two-level cap\n"
        "        cv = np.where(vwm <= 1382, cap[0], cap[1])\n"
        "        return np.where((vwm <= 2880) & (b > cv), cv, b)\n"
        "    return np.where((vwm <= 1382) & (b > cap), cap, b)")
s = sub(s, '    "D1c: D1a hand rule + ASYM bound": (rule(1229), 4096, True),\n',
        '    "D1c: D1a hand rule + ASYM bound": (rule(1229), 4096, True),\n'
        '    "REV2: D1c + cap 6144 at 6-12.5 m/s": (rule(1229), (4096, 6144), True),\n')
s = sub(s, 'for alt in ("D1b: 1229 | opp300 & ~closing(A0 10)", "D1a: hard 1229, opp inert", "D1c: D1a hand rule + ASYM bound",',
        'for alt in ("D1b: 1229 | opp300 & ~closing(A0 10)", "D1a: hard 1229, opp inert", "D1c: D1a hand rule + ASYM bound",\n'
        '            "REV2: D1c + cap 6144 at 6-12.5 m/s",')
mod = types.ModuleType("d1_r79_rev2")
mod.__file__ = str(SRC)
sys.path.insert(0, str(SRC.parent))
exec(compile(s, str(SRC), "exec"), mod.__dict__)
