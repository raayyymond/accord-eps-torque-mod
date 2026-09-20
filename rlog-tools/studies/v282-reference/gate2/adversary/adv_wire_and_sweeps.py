# -*- coding: utf-8 -*-
"""GATE #2 ADVERSARY, part 3.

B1. THE INDEPENDENT CHECK ON THE JERK TERM, measured on the wire: is `Kj*jerk` even DIFFERENT
    between r73 (positive) and r72 (its matched control)?  If it is common-mode, it cannot
    separate them, whatever it does to the phase.
B2. Does the relay saturate once the jerk is added?  (the gate leans on "linear region".)
B3. THE V282 PROBLEM: r71 flew 0.011, V282 flew 0.010, both relay-live, opposite labels.
B4. Every -180 crossing 0.5-12 Hz for every config -- can the model family reach 4.0-6.5 Hz AT ALL?
B5. b-sensitivity: over which b does each clause hold?
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)
CACHE = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref")
R1 = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/retrodict/repair/out/r1_ident.json")
import adv_jerk_mechanism as M  # reuse the re-derived loop (NOT imported from the repair stream)

P = print
KJ, THR = 0.22, 0.30
ROUTES = {"r71 POS": "00000071--f2c9d073a3", "r73 POS": "00000073--79fd149dd8",
          "r72 clean": "00000072--8001fc3048", "rev6.4 cln": "0000006e--6ca3e014fd",
          "V282 clean": "0000006c--2bc842dbac", "V282old cln": "00000039--f56039af87"}

P("=" * 112)
P("B1/B2.  THE RELAY ARGUMENT ON THE WIRE:  arg = pid_log.error + 0.22 * desiredLateralJerk")
P("        engaged, lateral active, hands off, v >= 15 m/s.  (cs_err is error_with_lsf as logged,")
P("        i.e. already notched where the notch flew; cs_la_jerk is desiredLateralJerk.)")
P("=" * 112)
P(f"  {'route':12s} {'secs':>6} {'rms err':>8} {'rms Kj*j':>9} {'rms arg':>8} {'A=v2*rms':>9} "
  f"{'|arg|>thr':>10} {'corr(e,j)':>10} {'jerk/err':>9}")
wire = {}
for nm, rt in ROUTES.items():
    f = CACHE / f"{rt}.npz"
    if not f.exists():
        P(f"  {nm:12s}  (no cache)")
        continue
    d = np.load(f, allow_pickle=True)
    err, jrk = np.asarray(d["cs_err"], float), np.asarray(d["cs_la_jerk"], float)
    act = np.asarray(d["cs_active"], float) > 0.5
    t = np.asarray(d["t_cs"], float)
    tcst = np.asarray(d["t_cst"], float)          # vego / spress live on the carState clock
    v = np.interp(t, tcst, np.asarray(d["vego"], float))
    press = np.interp(t, tcst, np.asarray(d["spress"], float)) > 0.5
    sel = act & (v >= 15.0) & (~press) & np.isfinite(err) & np.isfinite(jrk)
    if sel.sum() < 500:
        P(f"  {nm:12s}  (only {sel.sum()} samples)")
        continue
    e, j = err[sel], KJ * jrk[sel]
    arg = e + j
    A = np.sqrt(2) * arg.std()
    cc = float(np.corrcoef(e, j)[0, 1])
    wire[nm] = dict(route=rt, secs=float(sel.sum() * 0.01), rms_e=float(e.std()), rms_j=float(j.std()),
                    rms_arg=float(arg.std()), A=float(A), sat=float((np.abs(arg) > THR).mean()),
                    corr=cc, jerk_over_err=float(j.std() / max(e.std(), 1e-9)),
                    rms_e_only_A=float(np.sqrt(2) * e.std()))
    w = wire[nm]
    P(f"  {nm:12s} {w['secs']:6.0f} {w['rms_e']:8.4f} {w['rms_j']:9.4f} {w['rms_arg']:8.4f} {A:9.4f} "
      f"{w['sat'] * 100:9.1f}% {cc:10.3f} {w['jerk_over_err']:9.2f}")
    del d

if "r72 clean" in wire and "r73 POS" in wire:
    a, b = wire["r72 clean"], wire["r73 POS"]
    P(f"\n  r73 vs its MATCHED CONTROL r72 (same commit, same everything but SteerFriction):")
    P(f"    rms(Kj*jerk):  r72 {a['rms_j']:.4f}   r73 {b['rms_j']:.4f}   ratio {b['rms_j'] / a['rms_j']:.3f}x")
    P(f"    rms(error)  :  r72 {a['rms_e']:.4f}   r73 {b['rms_e']:.4f}   ratio {b['rms_e'] / a['rms_e']:.3f}x")
    P(f"    A = sqrt(2)*rms(arg): r72 {a['A']:.4f}  r73 {b['A']:.4f}   (relay threshold {THR})")
    P("    => the jerk term is a PLANNER/ROAD quantity.  If it is ~common-mode across the pair it")
    P("       carries no information that separates them, and the repair's ONE new term cannot be")
    P("       what distinguishes a positive from its own matched control.")

P("\n" + "=" * 112)
P("B3.  THE V282 PROBLEM -- r71 0.011 vs V282 0.010, both relay-live, opposite labels")
P("=" * 112)
S = json.load(open(R1))
plants = {}
for key, d in S["cells"].items():
    wu = np.array(d["wSwu_re"]) + 1j * np.array(d["wSwu_im"])
    wy = np.array(d["wSwy_re"]) + 1j * np.array(d["wSwy_im"])
    plants[key] = dict(route=d["route"], bin=d["bin"], v=d["v"], c=d["c"], secs=d["secs"],
                       alpha=abs(np.mean(wy.mean(0) / wu.mean(0))) * M.k_of(d["v"]))
F = M.F
USE = ["00000072--8001fc3048|22+", "0000006c--68c6e94b17|22+", "0000006e--6ca3e014fd|22+"]
P("  the relay's own contribution to the controller gain, fric/0.30, vs the linear term (kp+I)/LAF:")
for nm, p in M.CTRL.items():
    P(f"    {nm:12s} kp/LAF = {p['kp'] / p['laf']:.4f}   relay = fric/thr = {p['fric'] / THR:.4f}   "
      f"sum = {p['kp'] / p['laf'] + p['fric'] / THR:.4f}   relay share {100 * (p['fric'] / THR) / (p['kp'] / p['laf'] + p['fric'] / THR):5.1f}%")
P("\n  r71 (POSITIVE, 0.011) vs V282 (CLEAN, 0.010): the relay dose differs by 10%.  V282's LINEAR")
P("  gain kp/LAF = 0.150 is 2.5x r71's 0.061.  Any statistic monotone in total controller gain")
P("  therefore ranks V282 ABOVE r71 -- and V282old (0.379) far above both.  Score it:")
for pk in USE:
    pl = plants[pk]
    sc = {}
    for nm, p in M.CTRL.items():
        L = M.L_of(F, pl["v"], pl["alpha"], pl["c"], p, 0.065, 0.0006)
        cs = M.crossings(F, L)
        sc[nm] = (cs[0][1], cs[0][0]) if cs else (np.nan, np.nan)
    order = sorted(sc.items(), key=lambda kv: -kv[1][0])
    P(f"    plant {pl['route'][:8]} v={pl['v']:.1f}: " + "  >  ".join(f"{k.split()[0]} {vv[0]:.2f}" for k, vv in order))
    pos = [k for k in sc if "POS" in k]
    cln = [k for k in sc if "POS" not in k]
    ok = all(sc[p][0] > max(sc[c][0] for c in cln) for p in pos)
    P(f"      clause (b) both positives above ALL cleans: {'PASS' if ok else 'FAIL'}"
      f"   (worst clean = {max(cln, key=lambda c: sc[c][0])} at {max(sc[c][0] for c in cln):.2f})")

P("\n" + "=" * 112)
P("B4.  CAN THIS MODEL FAMILY REACH 4.0-6.5 Hz AT ALL?  every -180 crossing, 0.5-12 Hz")
P("=" * 112)
allx = []
for pk in USE:
    pl = plants[pk]
    for nm, p in M.CTRL.items():
        for jl in (False, True):
            L = M.L_of(F, pl["v"], pl["alpha"], pl["c"], p, 0.065, 0.0006, 1.0, jl)
            cs = M.crossings(F, L, 0.5, 12.0)
            allx += [c[0] for c in cs]
            if pk == USE[0]:
                P(f"    plant {pl['route'][:8]} {nm:12s} jerk_in_loop={int(jl)} -> "
                  + ("  ".join(f"{fx:.2f}Hz(|L|={m:.2f})" for fx, m in cs) or "none"))
allx = np.array(allx)
P(f"\n  {len(allx)} crossings over 3 plants x 6 controllers x 2 jerk readings.")
P(f"  range {allx.min():.2f} .. {allx.max():.2f} Hz;  fraction in [4.0,6.5] = {((allx >= 4.0) & (allx <= 6.5)).mean() * 100:.1f}%")
P(f"                                                 fraction in [3.0,8.125] = {((allx >= 3.0) & (allx <= 8.125)).mean() * 100:.1f}%")
P("  => under the NARROW reading of clause (a) ('place r73's object inside the observed 4.0-6.5 Hz")
P("     band') this model family cannot pass at any Kj.  It passes only on the WIDE reading, and")
P("     then only by selecting the SECOND crossing -- a selection that is already available at")
P("     gate #1's baseline with NO jerk term.")

P("\n" + "=" * 112)
P("B5.  b-SENSITIVITY.  b is open over ~70x; gate #1 fixed it at 6e-4 with no justification.")
P("=" * 112)
pl = plants[USE[0]]
P(f"  plant {pl['route'][:8]} v={pl['v']:.1f}, D=65 ms.   (first crossing, |L|)")
P(f"  {'b':>9} " + " ".join(f"{nm.split()[0]:>11s}" for nm in M.CTRL) + "   (b) both pos top?")
brows = []
for b in (7e-5, 1.5e-4, 3e-4, 6e-4, 1.2e-3, 1.8e-3, 3e-3, 4.9e-3):
    sc, fx = {}, {}
    for nm, p in M.CTRL.items():
        L = M.L_of(F, pl["v"], pl["alpha"], pl["c"], p, 0.065, b)
        cs = M.crossings(F, L)
        sc[nm], fx[nm] = (cs[0][1], cs[0][0]) if cs else (np.nan, np.nan)
    cln = [k for k in sc if "POS" not in k]
    ok = all(sc[p] > max(sc[c] for c in cln) for p in sc if "POS" in p)
    a71 = 1.755 <= fx["r71  POS"] <= 2.925
    a73 = 3.0 <= fx["r73  POS"] <= 8.125
    brows.append(dict(b=b, scores={k: float(v) for k, v in sc.items()}, fcross={k: float(v) for k, v in fx.items()},
                      clause_b=bool(ok), a71=bool(a71), a73=bool(a73)))
    P(f"  {b:9.5f} " + " ".join(f"{sc[nm]:11.3f}" for nm in M.CTRL)
      + f"   {'PASS' if ok else 'FAIL'}   a71={'Y' if a71 else 'N'} a73={'Y' if a73 else 'N'}")

json.dump(dict(wire=wire, b_rows=brows, cross_range=[float(allx.min()), float(allx.max())],
               frac_in_narrow=float(((allx >= 4.0) & (allx <= 6.5)).mean())),
          open(OUT / "wire_sweeps.json", "w"), indent=1)
P("\nwrote " + str(OUT / "wire_sweeps.json"))
