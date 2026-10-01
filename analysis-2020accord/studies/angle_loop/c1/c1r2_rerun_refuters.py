# -*- coding: utf-8 -*-
"""c1r2_rerun_refuters.py -- re-run the REFUTERS' OWN scripts, unmodified in logic, on C1 rev 2 (Kd 20, Ki_base 112,
the rev-2 table).  Wraps c1_rerun_refuters (rev 1) with two corrections that rev 2 needs:

  1. stab_lin.Ctl binds kp/ki/kd as DEFAULT ARGUMENTS at import (450 / 199 / 16).  Rev 1 kept Kd 16 and rescaled G by
     1/2 so 450*G/2 = 225*G (Ki_eff then 199/200 of C1's, 0.5 %).  Rev 2 has Kd 20 and Ki 112, so here the defaults
     themselves are replaced: Ctl(v, kp=225, ki=112, kd=20, ...) and stab_lin.G_of_v = the rev-2 integer walk (no 1/2).
     xcheck_hf.py hard-codes kd=16 in two HF.Ctl calls: substituted to kd=C.KD (source substitution, asserted count).
  2. Outputs go to c1/refute_rerun_r2/ so rev 1's c1/refute_rerun/ stays as the record of rev 1.
The round-2 stability refuter's own scripts (refute_stability/refute_c1_run.py, refute_c1_stage2.py) read c1_lib
directly (table, KP_BASE, KI_BASE, KD), so they need no patch and are run as they are.
usage: python c1r2_rerun_refuters.py <script.py> [args...]"""
from __future__ import annotations

import io
import runpy
import sys
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402
import c1_rerun_refuters as R1  # noqa: E402

OUTD = HERE / "refute_rerun_r2"
OUTD.mkdir(exist_ok=True)
R1.OUTD = OUTD


def patch_stability(script):
    import stab_lin as S
    d = list(S.Ctl.__init__.__defaults__)          # (kp, ki, kd, d, extra_age, rate_pole_hz, G, fade)
    d[0], d[1], d[2] = C.KP_BASE, C.KI_BASE, C.KD
    S.Ctl.__init__.__defaults__ = tuple(d)
    S.KP_BASE, S.KI, S.KD = C.KP_BASE, C.KI_BASE, C.KD
    S.G_of_v = lambda v: C.G_at(v, C.c1_table())
    if script in ("stab_nl.py", "stab_nl2.py"):
        import stab_nl as N
        N.KP, N.KI, N.KD = C.KP_BASE, C.KI_BASE, C.KD


R1.patch_stability = patch_stability


def main():
    script = sys.argv[1]
    if script in ("xcheck_hf.py", "stab_fix.py"):
        # these two hard-code the C0 base (450 / 199 / kd 16) in their own arithmetic: substitute exactly those literals
        # (counts asserted) so that Kp_eff = Kp_base*G/256 and Ki_eff = Ki_base*G/256 are C1 rev 2's, with no rescale.
        path = R1.RS / script
        sys.path.insert(0, str(R1.RS))
        patch_stability(script)
        src = path.read_text(encoding="utf-8")
        subs = {"xcheck_hf.py": [("kd=16", f"kd={C.KD}", 2), ("450*G/256", f"{C.KP_BASE}*G/256", 2),
                                 ("199*G/256", f"{C.KI_BASE}*G/256", 2)],
                "stab_fix.py": [("kd=16", f"kd={C.KD}", 1), ("450*S.G_of_v(v)/256", f"{C.KP_BASE}*S.G_of_v(v)/256", 1),
                                ("450*best/256", f"{C.KP_BASE}*best/256", 1), ("Kpe*256/450", f"Kpe*256/{C.KP_BASE}", 1),
                                ("range(120, 1200, 4)", f"range({120 * 450 // C.KP_BASE}, {1200 * 450 // C.KP_BASE}, 8)", 1)]}
        for a, b, n in subs[script]:
            assert src.count(a) == n, (script, a, src.count(a))
            src = src.replace(a, b)
        buf = io.StringIO()
        with redirect_stdout(buf):
            print(f"# RE-RUN on C1 rev 2 of {path.relative_to(C.KIT)} (C0-base literals substituted: {subs[script]}; table "
                  f"{C.c1_table()}, Kp_base {C.KP_BASE}, Ki_base {C.KI_BASE})")
            g = {"__name__": "__main__", "__file__": str(path)}
            exec(compile(src, str(path), "exec"), g)
        (OUTD / script.replace(".py", ".txt")).write_text(buf.getvalue(), encoding="utf-8")
        sys.stdout.write(buf.getvalue())
        return
    if script in ("refute_c1_run.py", "refute_c1_stage2.py"):
        path = R1.RS / script
        sys.path.insert(0, str(R1.RS))
        buf = io.StringIO()
        with redirect_stdout(buf):
            print(f"# RE-RUN on C1 rev 2 of {path.relative_to(C.KIT)} (unpatched; it reads c1_lib: table "
                  f"{C.c1_table()}, Kp_base {C.KP_BASE}, Ki_base {C.KI_BASE}, Kd {C.KD})")
            runpy.run_path(str(path), run_name="__main__")
        (OUTD / script.replace(".py", ".txt")).write_text(buf.getvalue(), encoding="utf-8")
        sys.stdout.write(buf.getvalue())
        return
    R1.main()


if __name__ == "__main__":
    main()
