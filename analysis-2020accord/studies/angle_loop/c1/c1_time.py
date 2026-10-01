# -*- coding: utf-8 -*-
"""c1_time.py -- the TIME harness (harness_time.run / metrics / per_speed_score, unmodified) on the C1 candidates, with
the cave emulated by c1_lib.LaneC1 exactly as the C1 listing computes it (the table walk, E' = (E*G)>>8, the freeze
return to 0x29D7E).  Members: the r71b family + 'bc' (b_lo's b, friction x2 at >= 10 m/s, x1.3 at 8 m/s: the
friction refuter's bias-corrected world, expH_biascorrected.py's definition) + 'J1.0' (the interpolated refit) +
the two-mass stress members.  ANALYSIS ONLY.

usage:  python c1_time.py run <suite>      (suites: nominal, robust, pi)
        python c1_time.py score <suite> [--detail]"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402
HT = C.install_ht()                       # top level: spawned workers re-import this module and get the patch too
VP = HT.VP
EXTRA_A = {4.0: 70.0, 5.5: 45.0, 6.0: 40.0, 6.5: 36.0, 7.0: 33.0, 10.0: 20.0, 11.9: 13.0, 15.0: 8.0, 17.0: 6.0,
           22.0: 4.0}
EXTRA_R = {4.0: 2.5, 5.5: 2.0, 6.0: 1.5, 6.5: 1.5, 7.0: 1.0, 10.0: 1.0, 11.9: 1.0, 15.0: 1.0, 17.0: 1.0, 22.0: 1.0}
HT.A_TURN.update(EXTRA_A)
HT.RAMP_S.update(EXTRA_R)
SPEEDS = (3.0, 5.0, 5.5, 6.0, 7.0, 8.0, 10.0, 11.9, 12.5, 15.0, 17.0, 19.0, 22.0, 26.0, 30.0)

# ---------------------------------------------------------------------------------------------------------------------
# the candidate rows
# ---------------------------------------------------------------------------------------------------------------------
def rows():
    t1 = C.c1_table()                                      # THE C1 TABLE (c1_lib.VARIANTS['kd16'])
    t0x2 = C.make_table(C.C0_KNOTS_X2)
    r = []
    r.append(C.c1_row(t1, "C1 (freeze |tq|>512 + ramp<0x8000)", kd=16, thr=512, rampfrz=True, pol="freeze"))
    r.append(C.c1_row(t1, "C1 freeze |tq|>512 only (no ramp freeze)", kd=16, thr=512, rampfrz=False, pol="freeze"))
    r.append(C.c1_row(t1, "C1 freeze |tq|>1024 + ramp", kd=16, thr=1024, rampfrz=True, pol="freeze"))
    r.append(C.c1_row(t1, "C1 gains + C0 bleed (1024, tau 64 ms)", kd=16, pol="bleed", bleed_thr=1024, bleed_sh=6,
                      rampfrz=False, thr=0))
    r.append(C.c1_row(t1, "C1 gains, no I policy (control)", kd=16, pol="none", rampfrz=False, thr=0))
    r.append(C.c1_row(C.C0_TABLE, "C0 as listed (450/199, bleed 1024)", kp_base=450, ki_base=199, kd=16, pol="bleed",
                      bleed_thr=1024, bleed_sh=6, rampfrz=False, thr=0))
    r.append(C.c1_row(t0x2, "C0 rebased x2 (225/100, bleed 1024)", kp_base=225, ki_base=100, kd=16, pol="bleed",
                      bleed_thr=1024, bleed_sh=6, rampfrz=False, thr=0))
    return r


# ---------------------------------------------------------------------------------------------------------------------
# members
# ---------------------------------------------------------------------------------------------------------------------
def member(name):
    fam = VP.family()
    if name.startswith("nominal+mode"):
        f2 = float(name.split("mode")[1].split("Hz")[0])
        return fam["nominal"].with_mode20(f2=f2, zeta2=0.1 if f2 < 15 else 0.05, r2=0.2)
    if name == "bc":
        nom, blo = fam["nominal"], fam["b_lo"]
        fx = np.where(VP.V_CENTRES >= 10.0, 2.0, np.where(VP.V_CENTRES >= 5.0, 1.3, 1.0))
        return replace(blo, name="bc", Fc=nom.Fc * fx, Fs=nom.Fs * fx)
    if name == "J1.0":
        import c1_members as M
        return replace(M.REFIT[1.0], use_sat=True)
    return fam[name]


def job(args):
    scn_name, v, rws, mem, outer, opts = args
    scn = HT.scenario(scn_name, v)
    cfg = HT.Cfg(rws)
    t0 = time.time()
    r = HT.run(scn, cfg, member(mem), v, outer=outer, **opts)
    m = HT.metrics(scn_name, scn, r, v)
    return dict(name=scn_name, v=v, member=mem, outer=outer, metrics={k: np.asarray(x).tolist() for k, x in m.items()},
                sec=time.time() - t0, opts=json.dumps(opts, sort_keys=True), extra=0)


SUITES = {
    "nominal": dict(members=("nominal",), scen=HT.SCENARIOS, outer="ff"),
    "robust": dict(members=("J_lo", "J_hi", "b_lo", "b_hi", "F_lo", "F_hi", "tau0", "tau6", "bc", "J1.0", "J_hi2",
                            "nominal+mode13Hz", "nominal+mode20Hz"), scen=HT.SC_TRACK, outer="ff"),
    "pi": dict(members=("nominal",), scen=HT.SC_TRACK, outer="pi"),
}


def run_suite(suite):
    s = SUITES[suite]
    rw = rows()
    jobs = [(nm, v, rw, m, s["outer"], {}) for m in s["members"] for v in SPEEDS for nm in s["scen"]]
    t0 = time.time()
    out = []
    with Pool(14) as pool:
        for i, res in enumerate(pool.imap_unordered(job, jobs)):
            out.append(res)
            if (i + 1) % 25 == 0 or i + 1 == len(jobs):
                print("  %s %d/%d, %.0f s" % (suite, i + 1, len(jobs), time.time() - t0), flush=True)
    (C.OUT / f"time_{suite}.json").write_text(json.dumps(dict(rows=rw, results=out)))


def kpkd(r, v):
    c = r["c1"]
    G = C.cave_G(C.spd_counts(v), c["tbl"]) if c.get("cave", True) else 256
    return r["kpY"][0] * G / 256.0, r["kdY"][0]


def score(suite, detail=False):
    d = json.loads((C.OUT / f"time_{suite}.json").read_text())
    rw, res = d["rows"], d["results"]
    by_mem = {}
    for r in res:
        by_mem.setdefault(r["member"], []).append(r)
    lines = []
    P = lines.append
    for mem, rr in by_mem.items():
        T = HT.table(rr, rw)
        P(f"\n===== member {mem}  (suite {suite})")
        for strict in (False, True):
            P("  -- " + ("STRICT (texture gated)" if strict else "LINE-ONLY"))
            for i, r in enumerate(rw):
                cells = []
                for v in SPEEDS:
                    if ("rh", v) not in T:
                        continue
                    gates, allpass, cost = HT.per_speed_score(T, v, [kpkd(x, v)[0] for x in rw], [kpkd(x, v)[1] for x in rw],
                                                              strict=strict)
                    fails = [k for k in HT.GATES if not gates[k][i]]
                    cells.append(f"{v:g}:{'PASS' if not fails else '/'.join(fails)}")
                npass = sum(1 for c in cells if c.endswith("PASS"))
                P(f"    {npass:2d}/{len(cells)} {r['label'][:46]:46s} " + " ".join(cells))
        if detail or mem != "nominal":
            for i, r in enumerate(rw):
                P(f"\n  **{r['label']}** ({mem})")
                P("  | m/s | Kp_eff | ess | hold | tg0.2 | tg0.5 | +-1 fit | dj ev | stick% | T_hf hold | T_hf sin | hunt p2p | step ov% | hard16 / ref | wraps |")
                for v in SPEEDS:
                    if ("rh", v) not in T:
                        continue
                    rh, st, s02, s05, ssm = (T[(n, v)] for n in ("rh", "st", "s02", "s05", "ssm"))
                    dj = s02["dj_events"][i] + s05["dj_events"][i] + ssm["dj_events"][i] + rh["hold_slips"][i] + st["hold_slips"][i]
                    stick = max(s02["stick_pct"][i], s05["stick_pct"][i], ssm["stick_pct"][i])
                    wr = max(rh["wraps"][i], st["wraps"][i], s02["wraps"][i], s05["wraps"][i], ssm["wraps"][i])
                    P(f"  | {v:g} | {kpkd(r, v)[0]:.0f} | {rh['ess_turn'][i]:.2f} | {rh['hold_ratio'][i]:.3f} | "
                      f"{s02['track_gain'][i]:.3f} | {s05['track_gain'][i]:.3f} | {ssm['fit_gain'][i]:.2f} | {dj:.0f} | "
                      f"{stick:.0f} | {max(rh['T_hf'][i], st['T_hf'][i]):.1f} | "
                      f"{max(s02['T_hf'][i], s05['T_hf'][i], ssm['T_hf'][i]):.1f} | "
                      f"{max(rh['hunt_p2p'][i], st['hunt_p2p'][i]):.2f} | {st['overshoot_pct'][i]:.0f} | "
                      f"{rh['hard16'][i]:.2f} / {rh['hard16_ref'][i]:.2f} | {wr:.0f} |")
                if ("ov_fade", SPEEDS[0]) in T:
                    P("  | m/s | override overshoot deg / peak T | latch overshoot | sentinel L16 peakT / s>50 / exc | R16 exc | dis meas / zero exc |")
                    for v in SPEEDS:
                        ov, la, se, sr, dm, dz = (T[(n, v)] for n in ("ov_fade", "ov_latch", "sen_L16", "sen_R16", "dis_meas", "dis_zero"))
                        P(f"  | {v:g} | {ov['lurch_overshoot'][i]:.2f} / {ov['lurch_peakT'][i]:.0f} | {la['lurch_overshoot'][i]:.2f} |"
                          f" {se['sen_peakT'][i]:.0f} / {se['sen_dur_s'][i]:.2f} / {se['sen_excursion'][i]:.1f} | {sr['sen_excursion'][i]:.1f} |"
                          f" {dm['dis_excursion'][i]:.2f} / {dz['dis_excursion'][i]:.2f} |")
    txt = "\n".join(lines)
    (HERE / f"time_{suite}_score.txt").write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run_suite(sys.argv[2])
    else:
        score(sys.argv[2], detail="--detail" in sys.argv)
