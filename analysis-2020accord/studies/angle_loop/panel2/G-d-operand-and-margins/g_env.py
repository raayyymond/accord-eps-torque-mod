# -*- coding: utf-8 -*-
r"""g_env.py -- the speed-gain ENVELOPE of each D structure over a grid of Kd, on the EXTENDED credible set (designer G,
panel 2).  ANALYSIS ONLY.

For every structure (fresh-rate D / held-rate D / angle-own box10 D) and every Kd on its grid, at every grid speed:
  Gmax_pm(v)   = the largest G on g_ext.GSCAN such that every G' <= G passes pm_fixed >= bar and LTI GM >= 6 dB on EVERY
                 gated member x frame variant (g_ext.gated_members: the brief's tier A + tier B, the refuters' ms_free x
                 {b_lo, b_q} (+tau6, +h10), b_lo*J_hi*tau6(+h10), and -- strict reading -- aged single corners at 45 deg;
                 frames: kappa 0.83 / 1 / 1.155 on the D operand, and the motor-frame plant reading '|fb' (J, b / 1.155))
  Grule(v)     = the largest G with M20 <= V295's, Re(T/w)20 >= V295's at hold ages 0 AND 10, and L20 <= V295's on every
                 tier-A member -- evaluated with the candidate's D at kappa 1.155 against V295 at kappa 1 (rate D), or
                 the angle D (frame-exact) against V295 at kappa 1/1.155 (V295 reads the lin-frame rate): in both cases
                 the candidate's D 15.5 % stronger relative to V295's than the nominal model -- the conservative corner
  env(v)       = min(Gmax_pm, Grule) and the binding member.
usage:  python g_env.py <struct> <kd,kd,...> [coarse|full] [nostrict]      -> _scratch/angle_loop/G-dop/env_<tag>.json
        struct in fresh | held | box10 (box10 kd = Kd with k_op 64)"""
from __future__ import annotations

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402

GRID_FULL = X.G2.GRID
GRID_COARSE = sorted(set([float(x) for x in np.arange(1.0, 35.01, 1.0)] + [3.1, 8.0, 11.9, 17.0, 26.9, 9.5, 10.5,
                                                                           11.5, 12.5, 13.5]))
BOX_KOP = 64
KI = 56


def _struct(kind, kd0=1.0, ki=None):
    return X.flat_cand(kind, kd0, dop_k=BOX_KOP, ki=KI if ki is None else ki)


def env_job(args):
    kind, name, v, kds, bar, ki = args
    return X.env_point((_struct(kind, ki=ki), name, v, kds, bar))


def rule_point(args):
    """the 20 Hz rules at speed v for every kd: largest G on GSCAN (every smaller G passing too).
    FRAME HANDLING (arithmetic on EVIDENCE sensor facts): V295's operand gp-0x6a56 = -1.698 gp-0x6abe is the SAME
    lin-frame motor rate the fresh / held candidates read, so the frame ratio cancels between a rate-D candidate and V295
    and scales only the P/I part (theta = s r).  The rules are evaluated in BOTH frames and the smaller G kept:
        s = 1     : candidate D kappa 1,        V295 kappa 1           (the common scorer's convention)
        s = 1.155 : rate D kappa 1/1.155 = V295 kappa 1/1.155          (near centre, FA)
                    box10 (theta frame) kappa 1, V295 kappa 1/1.155    (the angle D is 15.5 % stronger relative to V295)"""
    kind, v, kds, a_mems, ki = args
    c = _struct(kind, ki=ki)
    frames = [(1.0, 1.0), ((1.0 if kind == "box10" else 1.0 / X.S_C), 1.0 / X.S_C)]
    refs = []
    for kc, kr in frames:
        m20ref = {ea: X.ref_m20("V295", kappa=kr, ea=ea) for ea in (0, 10)}
        re20ref = {ea: float(X.ref_re_tw("V295", 20.0, ea=ea, kappa=kr)[0]) for ea in (0, 10)}
        l20ref = {m: X.ref_L20("V295", m, v) * kr for m in a_mems}     # V295's L = -K Cw Pw: scales exactly by kr
        refs.append((kc, kr, m20ref, re20ref, l20ref))
    out = {}
    why = {}
    for kd in kds:
        Gok = 0.0
        bad = ""
        for G in X.GSCAN:
            ok = True
            for kc, kr, m20ref, re20ref, l20ref in refs:
                for ea in (0, 10):
                    if X.m20(c, v, G, kd, kappa=kc, ea=ea) > m20ref[ea] * (1 + 1e-9):
                        ok, bad = False, f"M20(s={1 / kr:.3f},ea{ea})"
                    elif X.re_tw(c, v, G, kd, 20.0, ea=ea, kappa=kc)[0] < re20ref[ea] - 1e-12:
                        ok, bad = False, f"Re20(s={1 / kr:.3f},ea{ea})"
                    if not ok:
                        break
                if ok:
                    for m in a_mems:
                        if X.cand_L20(c, m, v, G, kd * kc) > l20ref[m] * (1 + 1e-9):
                            ok, bad = False, f"L20:{m}(s={1 / kr:.3f})"
                            break
                if not ok:
                    break
            if not ok:
                break
            Gok = float(G)
        out[kd] = Gok
        why[kd] = bad
    return v, out, why


def run(kind, kds, grid, strict=True, procs=6, tag=None, ki=56):
    t0 = time.time()
    mems = X.gated_members(kind, strict=strict, new=True)
    jobs = [(kind, m, v, kds, X.bar_of(m, strict), ki) for m in mems for v in grid]
    a_mems = [m for m in X.BRIEF_A]                       # L20 rule on the brief's tier-A members (nominal frame)
    with Pool(procs) as pool:
        res = pool.map(env_job, jobs, chunksize=8)
        rr = pool.map(rule_point, [(kind, v, kds, a_mems, ki) for v in grid])
    env = {kd: {} for kd in kds}
    bind = {kd: {} for kd in kds}
    per = {}
    for name, v, d in res:
        for kd, g in d.items():
            per.setdefault(kd, {}).setdefault(v, []).append((g, name))
            if v not in env[kd] or g < env[kd][v]:
                env[kd][v] = g
                bind[kd][v] = name
    rules = {kd: {} for kd in kds}
    for v, d, why in rr:
        for kd, g in d.items():
            rules[kd][v] = g
            if g < env[kd][v]:
                env[kd][v] = g
                bind[kd][v] = "RULE20:" + why[kd]
    tag = tag or (f"{kind}_{'-'.join(str(k) for k in kds)}_{'full' if len(grid) > 60 else 'coarse'}"
                  f"{'' if strict else '_brief'}{'' if ki == 56 else f'_ki{ki}'}")
    # second-worst per (kd, v) for diagnostics
    second = {kd: {v: sorted(per[kd][v])[:4] for v in per[kd]} for kd in per}
    payload = dict(kind=kind, kds=kds, grid=list(grid), strict=strict, env={str(k): env[k] for k in kds},
                   bind={str(k): bind[k] for k in kds}, rules={str(k): rules[k] for k in kds},
                   worst4={str(k): {str(v): second[k][v] for v in second[k]} for k in second},
                   members=mems, sec=time.time() - t0,
                   per_member=[[name, v, {str(k): g for k, g in d.items()}] for name, v, d in res])
    (X.OUT / f"env_{tag}.json").write_text(json.dumps(payload, default=float))
    print(f"{tag}: {len(jobs)} member-speed points, {time.time() - t0:.0f} s")
    for kd in kds:
        row = " ".join(f"{env[kd][v]:5.0f}" for v in grid)
        print(f"  Kd {kd:5}: {row}")
    return payload


if __name__ == "__main__":
    kind = sys.argv[1]
    kds = [float(x) for x in sys.argv[2].split(",")]
    grid = GRID_FULL if (len(sys.argv) > 3 and sys.argv[3] == "full") else GRID_COARSE
    strict = "nostrict" not in sys.argv
    ki = next((int(a[3:]) for a in sys.argv if a.startswith("ki=")), 56)
    run(kind, kds, grid, strict=strict, ki=ki)
