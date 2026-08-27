#!/usr/bin/env python3
r"""Two things the orchestrator asked for, both cheap and both decision-bearing.

(1) THE `427 == 1023` FLAG.  At `0x38234` a `bnc 0x382ce` routes to `movea 0x7fff,r0,r11` ->
    `st.h r11,-0x6b70[gp]`, i.e. when `|gp-0x6bfe| > 20000` (the observer's plausibility check
    FAILS) `gp-0x6b70` is forced to 32767 and the +-8192 clamp is BYPASSED.  On the V96/V97 packer
    `clamp(|gp-0x6b70| * 5 >> 6, 0, 0x3FF)` that lands at 32767*5>>6 = 2559 -> clamped to **1023**.

    🛑 I verified the CEILING claim independently, from `builds/v80_v107/build_v96_tva.py:128` (its own no-clip
    proof): the plausible branch's maximum wire is `8192*5>>6 = 640`.  So the flag is stronger than
    "== 1023": **ANY wire > 640 is arithmetically unreachable through the plausible branch.**  Both
    are reported.  I did NOT re-verify the `bnc` at `0x38234` in Ghidra -- that is carried as the
    TelemetryDesign agent's EVIDENCE, and the duty measured here is correct either way.

(2) THE REGIME SPLIT.  `STATE.md` §A2: the kit's hands-off mask is `steeringPressed` ==
    `|STEER_TORQUE_SENSOR| > 1200`, and **override is `steeringPressed == True` by definition**.
    Exposure across the corpus is 7121.6 s engaged hands-off vs 994.9 s engaged hands-on.  Route 80
    is scored against exactly that mask, plus openpilot's own `carState.steeringPressed`.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2].parent
AN = ROOT / "analysis-2020accord"
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from v97_r80_vs_v96 import ROUTES, load  # noqa: E402

TQ_HANDS_ON = 1200.0          # STATE.md A2 -- the kit's own mask, on 0x18F STEER_TORQUE_SENSOR
PLAUSIBLE_CEIL = 640          # builds/v80_v107/build_v96_tva.py:128, 8192*5>>6
IMPLAUSIBLE_CODE = 1023       # 32767*5>>6 = 2559, clamped to the 10-bit field


def runs(mask):
    """Contiguous True runs -> list of (i0, i1)."""
    m = np.asarray(mask, bool)
    if not m.any():
        return []
    d = np.diff(m.astype(int))
    s = list(np.where(d == 1)[0] + 1)
    e = list(np.where(d == -1)[0] + 1)
    if m[0]:
        s = [0] + s
    if m[-1]:
        e = e + [len(m)]
    return list(zip(s, e))


def main():
    D = {r: load(r) for r in ROUTES}
    out = {"tq_hands_on_threshold": TQ_HANDS_ON,
           "plausible_branch_max_wire": PLAUSIBLE_CEIL,
           "implausible_code": IMPLAUSIBLE_CODE}

    # ================= (1) THE 1023 FLAG =================
    print("=== THE 427 == 1023 FLAG (observer plausibility branch failed) ===")
    print(f"    plausible branch can only reach wire <= {PLAUSIBLE_CEIL} (8192*5>>6).")
    print(f"    wire == {IMPLAUSIBLE_CODE} <=> gp-0x6b70 forced to 32767.  wire > {PLAUSIBLE_CEIL} "
          f"is unreachable through the clamp AT ALL.")
    out["flag_1023"] = {}
    for r, d in D.items():
        mt = d["ab_mt"].astype(int)
        eng = d["ab_eng"]
        # hands-on, on the 427 grid, via the 0x18F column
        tq_ab = np.interp(d["ab_t"], d["t"], d["tq"])
        on = np.abs(tq_ab) > TQ_HANDS_ON
        rec = dict(build=d["build"], frames=int(len(mt)), wire_max=int(mt.max()),
                   n_eq_1023=int((mt == IMPLAUSIBLE_CODE).sum()),
                   duty_eq_1023=float((mt == IMPLAUSIBLE_CODE).mean()),
                   n_gt_640=int((mt > PLAUSIBLE_CEIL).sum()),
                   duty_gt_640=float((mt > PLAUSIBLE_CEIL).mean()),
                   n_eq_1023_engaged=int((mt == IMPLAUSIBLE_CODE)[eng].sum()),
                   n_eq_1023_manual=int((mt == IMPLAUSIBLE_CODE)[~eng].sum()),
                   n_gt_640_engaged=int((mt > PLAUSIBLE_CEIL)[eng].sum()),
                   n_gt_640_manual=int((mt > PLAUSIBLE_CEIL)[~eng].sum()),
                   n_gt_640_eng_handson=int((mt > PLAUSIBLE_CEIL)[eng & on].sum()),
                   n_gt_640_eng_handsoff=int((mt > PLAUSIBLE_CEIL)[eng & ~on].sum()),
                   wire_p999=float(np.percentile(mt, 99.9)),
                   wire_top5=sorted(np.unique(mt))[-5:])
        out["flag_1023"][r] = rec
        print(f"  r{r} ({d['build']:3s}): {len(mt):6,} frames  wire max {rec['wire_max']:4d}  "
              f"p99.9 {rec['wire_p999']:6.1f}  top-5 codes {rec['wire_top5']}")
        print(f"          wire == 1023: {rec['n_eq_1023']:5d} frames  duty "
              f"{rec['duty_eq_1023']:.6f}   (eng {rec['n_eq_1023_engaged']} / man "
              f"{rec['n_eq_1023_manual']})")
        print(f"          wire >  640 : {rec['n_gt_640']:5d} frames  duty "
              f"{rec['duty_gt_640']:.6f}   (eng-handsON {rec['n_gt_640_eng_handson']} / "
              f"eng-handsOFF {rec['n_gt_640_eng_handsoff']})")

    # ================= (2) THE REGIME SPLIT =================
    print(f"\n=== REGIME SPLIT: hands-on == |0x18F STEER_TORQUE_SENSOR| > {TQ_HANDS_ON:.0f} ===")
    print("    (STATE.md A2: engaged + hands-on == OVERRIDE, by definition)")
    out["regime"] = {}
    for r, d in D.items():
        on = np.abs(d["tq"]) > TQ_HANDS_ON
        eng = d["eng"]
        op = d["press"]                            # openpilot's own carState.steeringPressed
        rec = dict(build=d["build"],
                   engaged_s=float(eng.sum() * 0.01),
                   eng_handson_s=float((eng & on).sum() * 0.01),
                   eng_handsoff_s=float((eng & ~on).sum() * 0.01),
                   eng_handson_frac=float((eng & on).sum() / max(eng.sum(), 1)),
                   man_handson_s=float((~eng & on).sum() * 0.01),
                   op_press_eng_duty=float(op[eng].mean()) if eng.any() else float("nan"),
                   agree_op_vs_tq=float(np.mean(op[eng] == on[eng])) if eng.any() else float("nan"),
                   eng_handson_episodes=len([1 for a, b in runs(eng & on)
                                             if d["t"][b - 1] - d["t"][a] >= 1.0]),
                   eng_handsoff_episodes=len([1 for a, b in runs(eng & ~on)
                                              if d["t"][b - 1] - d["t"][a] >= 1.0]),
                   eng_handsoff_longest_s=max([d["t"][b - 1] - d["t"][a]
                                               for a, b in runs(eng & ~on)] or [0.0]))
        out["regime"][r] = rec
        print(f"  r{r} ({d['build']:3s}): engaged {rec['engaged_s']:7.1f} s  ->  "
              f"OVERRIDE (hands-ON) {rec['eng_handson_s']:6.1f} s "
              f"({100*rec['eng_handson_frac']:5.1f} %)   hands-OFF "
              f"{rec['eng_handsoff_s']:7.1f} s")
        print(f"          hands-OFF engaged episodes >=1 s: {rec['eng_handsoff_episodes']:3d}  "
              f"longest {rec['eng_handsoff_longest_s']:6.2f} s   || "
              f"openpilot steeringPressed duty (engaged) {rec['op_press_eng_duty']:.4f}, "
              f"agrees with the |tq|>1200 mask on {100*rec['agree_op_vs_tq']:.1f} % of frames")

    # ---- is the hands-off return-episode population the Q estimator needs present at all?
    print("\n=== CAN THE `Q` / RETURN ESTIMATOR RUN ON ROUTE 80? ===")
    print("    It needs ENGAGED + HANDS-OFF returns.  Counting them, per route:")
    out["handsoff_returns"] = {}
    for r, d in D.items():
        sel = d["eng"] & (np.abs(d["tq"]) <= TQ_HANDS_ON)
        eps = [(a, b) for a, b in runs(sel) if d["t"][b - 1] - d["t"][a] >= 2.0]
        # a "return" also needs the angle to be decaying toward zero over the episode
        rets = []
        for a, b in eps:
            a0, a1 = d["ang"][a], d["ang"][b - 1]
            if abs(a0) > 5.0 and abs(a1) < abs(a0) * 0.7:
                rets.append((float(d["t"][a]), float(d["t"][b - 1] - d["t"][a]),
                             float(a0), float(a1)))
        out["handsoff_returns"][r] = dict(build=d["build"], episodes_ge_2s=len(eps),
                                          returns=len(rets), detail=rets[:20])
        print(f"  r{r} ({d['build']:3s}): engaged+hands-off episodes >=2 s: {len(eps):3d}   "
              f"of which DECAYING-ANGLE returns: {len(rets):3d}")

    (AN / "_scratch/cache/r80" / "r80_override_and_1023.json").write_text(
        json.dumps(out, indent=1, default=float))
    print(f"\nwrote {AN/'_scratch/cache/r80'/'r80_override_and_1023.json'}")


if __name__ == "__main__":
    main()
