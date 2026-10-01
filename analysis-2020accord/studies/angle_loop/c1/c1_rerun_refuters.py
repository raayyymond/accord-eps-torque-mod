# -*- coding: utf-8 -*-
"""c1_rerun_refuters.py -- re-run the REFUTERS' OWN scripts, unmodified, on C1.  Each script is executed with runpy after
the minimum patch that swaps C0 for C1; the refuters' logic, members, scenarios, detectors and print formats are theirs.

  refute_friction/*.py   fric_lib.LaneC0 -> c1_lib.LaneC1F (the C1 listing: table walk, E' = (E*G)>>8, freeze to
                         0x29D7E when |tq| > 512 or ramp < 0x8000), fric_lib's KP_BASE/KI -> 225/100; the
                         harness-based ones (expA2, expB3, expH) get harness_time.LaneVec -> c1_lib.LaneC1 and
                         rec_time6.cands() -> [the C1 row].  Their JSON caches are redirected under
                         _scratch/angle_loop/c1/refute_rerun/ so the refuters' own C0 caches are NOT overwritten.
  refute_stability/*.py  stab_lin.G_of_v -> the C1 walk expressed in the refuter's C0 base (G_C1 / 2, so that
                         450*G/256 = 225*G_C1/256 = Kp_eff exactly; Ki_eff is 199/200 of C1's -- 0.5 %, stated);
                         stab_nl / stab_nl2 (integer lanes): KP 450 -> 225, KI 199 -> 100, G_of_v -> the integer C1 G.

usage: python c1_rerun_refuters.py <script.py> [script args...]   (output: c1/refute_rerun/<script>[_args].txt)
"""
from __future__ import annotations

import io
import os
import runpy
import sys
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402

RF = C.AL / "refute_friction"
RS = C.AL / "refute_stability"
OUTD = HERE / "refute_rerun"
OUTD.mkdir(exist_ok=True)
FAKE = C.OUT / "refute_rerun" / "a" / "b" / "c" / "d"        # F.HERE.parents[3] / "_scratch/angle_loop/refute-friction"
(C.OUT / "refute_rerun" / "_scratch" / "angle_loop" / "refute-friction").mkdir(parents=True, exist_ok=True)


def patch_friction():
    F = C.install_fric(tbl=C.c1_table(), thr=C.FRZ_THR, rampfrz=True, pol="freeze")
    F.HERE = FAKE
    # the harness-based scripts: rec_time patches LaneVec = LaneCave at import; re-patch to LaneC1 afterwards
    sys.path.insert(0, str(C.AL / "reconcile_c0"))
    import rec_time  # noqa: F401
    import rec_time6
    C.HT.LaneVec = C.LaneC1
    row = C.c1_row(C.c1_table(), "C1", kd=C.KD, thr=C.FRZ_THR, rampfrz=True, pol="freeze")
    rec_time6.cands = lambda: [row]
    return F


def patch_stability(script):
    import stab_lin as S
    if script in ("stab_nl.py", "stab_nl2.py"):
        S.G_of_v = lambda v: C.G_at(v, C.c1_table())
        import stab_nl as N
        N.KP, N.KI, N.KD = C.KP_BASE, C.KI_BASE, C.KD
    else:
        S.G_of_v = lambda v: C.G_at(v, C.c1_table()) / 2.0


def main():
    script = sys.argv[1]
    args = sys.argv[2:]
    if (RF / script).exists():
        path = RF / script
        sys.path.insert(0, str(RF))
        patch_friction()
    elif (RS / script).exists():
        path = RS / script
        sys.path.insert(0, str(RS))
        patch_stability(script)
    else:
        raise SystemExit("no such refuter script: " + script)
    sys.argv = [str(path)] + args
    buf = io.StringIO()
    with redirect_stdout(buf):
        print(f"# RE-RUN on C1 of {path.relative_to(C.KIT)} {' '.join(args)}  (C1 table {C.c1_table()}, "
              f"Kp_base {C.KP_BASE}, Ki_base {C.KI_BASE}, Kd {C.KD}, freeze |tq|>{C.FRZ_THR} + ramp)")
        if script == "stab_nl.py":
            # stab_nl.py has no main guard and re-defines its integer constants at top level when run as __main__, so
            # the module-attribute patch does not reach it: substitute exactly that one line (C0 450/199 -> C1 225/100).
            src = path.read_text(encoding="utf-8")
            old = "KP, KI, KD, ICL, DCL, DB = 450, 199, 16, 4096, 10240, 0"
            assert src.count(old) == 1
            src = src.replace(old, f"KP, KI, KD, ICL, DCL, DB = {C.KP_BASE}, {C.KI_BASE}, {C.KD}, 4096, 10240, 0")
            g = {"__name__": "__main__", "__file__": str(path)}
            exec(compile(src, str(path), "exec"), g)
        else:
            runpy.run_path(str(path), run_name="__main__")
    txt = buf.getvalue()
    tag = script.replace(".py", "") + ("_" + "_".join(a.replace(",", "-") for a in args) if args else "")
    (OUTD / f"{tag}.txt").write_text(txt, encoding="utf-8")
    sys.stdout.write(txt)


if __name__ == "__main__":
    main()
