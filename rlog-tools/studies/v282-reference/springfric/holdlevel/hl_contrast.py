"""STREAM holdlevel, step 4: the AccordHoldLevel contrast, and the observer tests it turns into.

Everything here recomputes the hold term MYSELF from the stored aa / angdes / v channels, honouring each
route's own flown AccordHoldLevel (read from initData by hl_params.py).  The stored hold_aa channel is
the UNLEVELLED map on every route (ss_extract.py:64 was level=False until 2026-09-19) -- verified in
hl_diag.py, rms|stored - unlevelled| = 1e-9 on 6c and 6d, which flew it ON.
Route-cluster CIs use ss_load.boot_ci (concatenates indices), never ss_centring_fit's OR-of-masks.

Sections
  A  PR-1  the stored hold_ff channel really does carry the flown level, and the predicted delta
  B        the observer's recursion reproduced from logged cmd/aa/sr/v -> the mechanism is real
  C  PR-2/3 the CENTRE contrast, per route, in the orchestrator's frame and against each route's own map
  D        the pooled level-interaction regression (the best-powered form of the contrast)
  E  PR-4/5 the observer's contribution at breakaway vs dwell duration and vs its own fade schedule
  F        the substitution accounting: what supplies cmd at breakaway, ON vs OFF
"""
import sys, json
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
SS = HERE.parents[1] / 'lowspeed' / 'a_stickslip'
sys.path.insert(0, str(SS))
from ss_load import load_all, boot_ci, PRE
from sslib import hold_torque, G_BP, G_V

LEVEL = {'0000006c--68c6e94b17': True, '0000006d--05e83bb04f': True, '0000006e--6ca3e014fd': False,
         '00000075--6c8687d5bd': False, '00000076--d0b7ea7e4d': False}
ON, OFF = '0000006c--68c6e94b17', '0000006e--6ca3e014fd'
K_FIT, C_FIT = 0.005560, -0.005620
DOB_FADE_BP = [3.0, 6.0]
DOB_HZ = 0.6; DOB_DELAY = 0.06; DOB_ACC_RC = 0.05; DOB_MAX = 0.3; J = 8e-5
DT = 0.01
TAU = 1.0 / (2.0 * np.pi * DOB_HZ)

EP, W, EX, VAL = load_all()
N = len(EP); ar = np.arange(N)
col = lambda k: np.array([e[k] for e in EP])
g, v, sj, route, dwell, kind = col('group'), col('v'), col('sjump'), col('route'), col('dwell_s'), col('kind')
d0 = np.maximum(col('w_d0'), 0); d1 = np.maximum(col('w_d1'), 0)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
BK = PRE - 3
aa_pre = W['aa'][:, PRE]
sgn = np.sign(aa_pre)
toward = (sj == -np.sign(aa_pre)).astype(float)
LOW = TQ & (v >= 2) & (v < 8)
aabs = np.abs(aa_pre)
QS = np.quantile(aabs[LOW], [0, .2, .4, .6, .8, 1.0])
lvl = np.array([LEVEL.get(r, False) for r in route])

# ---- recompute the hold term MYSELF, per route's flown level ----------------------------------
hold_flown_aa = np.zeros_like(W['aa'])
hold_unlev_aa = hold_torque(W['aa'], W['v'], False)
for rk, L in LEVEL.items():
    m = route == rk
    if m.any():
        hold_flown_aa[m] = hold_torque(W['aa'][m], W['v'][m], L)
OUT = []
P = OUT.append


def bins(mask):
    for i in range(5):
        lo, hi = QS[i], QS[i + 1]
        yield i, lo, hi, mask & (aabs >= lo) & (aabs <= hi if i == 4 else aabs < hi)


P("=" * 112)
P("A.  PR-1 -- does the STORED hold_ff channel carry each route's FLOWN level?  (it is hold(angdes,v,level))")
P("    rms|stored hold_ff - hold(angdes, v, L)| for L = flown and L = False, whole window")
for rk in sorted(LEVEL):
    m = route == rk
    if not m.any():
        continue
    ad_, vv, st = W['angdes'][m].ravel(), W['v'][m].ravel(), W['hold_ff'][m].ravel()
    ok = np.isfinite(ad_) & np.isfinite(vv) & np.isfinite(st)
    ad_, vv, st = ad_[ok], vv[ok], st[ok]
    hf = hold_torque(ad_, vv, LEVEL[rk]); hF = hold_torque(ad_, vv, False)
    P(f"    {rk}  flown {str(LEVEL[rk]):5s}  vs flown {np.sqrt(np.mean((st-hf)**2)):.3e}"
      f"   vs False {np.sqrt(np.mean((st-hF)**2)):.3e}")
P("    => the feedforward channel IS levelled per route (hold_aa was not); the level really ran.")

P("")
P("=" * 112)
P("B.  THE OBSERVER'S RECURSION, reproduced from the logged cmd / aa / sr / v with each route's flown level")
P("    residual = cmd(t-60ms) - [hold_flown(aa,v) + rate/G(v) + J*acc];  w1,w2 two 0.6 Hz lags;")
P("    out = clip(w2 * fade(v), +-0.3), fade = interp(v,[3,6],[0,1]).  Warm-started from the logged dob.")
P("    Compared over the 2.3 s window of every 2-8 m/s episode.")


def sim_dob(i):
    """re-run the observer over episode i's window; returns the simulated +left estimate"""
    cmd = W['cmd'][i].astype(float); aa = W['aa'][i].astype(float)
    sr = W['sr'][i].astype(float); vv = W['v'][i].astype(float)
    L = LEVEL.get(route[i], False)
    n = len(cmd); nd = max(int(round(DOB_DELAY / DT)), 1)
    fade = np.interp(vv, DOB_FADE_BP, [0.0, 1.0])
    alpha = DT / (TAU + DT); aacc = DT / (DOB_ACC_RC + DT)
    w0 = W['dob'][i][0] / max(fade[0], 1e-3)                       # warm start from the log
    w1 = w2 = float(np.clip(w0, -1.0, 1.0)); acc = 0.0; prev = sr[0]
    hist = [float(cmd[0])] * nd
    out = np.zeros(n)
    spring = hold_torque(aa, vv, L)
    b = 1.0 / np.interp(vv, G_BP, G_V)
    for t in range(n):
        ud = hist[0]; hist.append(float(cmd[t])); hist.pop(0)
        acc += aacc * ((sr[t] - prev) / DT - acc); prev = sr[t]
        res = ud - (spring[t] + b[t] * sr[t] + J * acc)
        w1 += alpha * (res - w1); w2 += alpha * (w1 - w2)
        out[t] = np.clip(w2 * fade[t], -DOB_MAX, DOB_MAX)
    return out


idx = np.where(LOW)[0]
sim = {i: sim_dob(i) for i in idx}
P(f"    {'route':22s} {'lvl':5s} {'n':>3s} {'rms(dob)':>9s} {'rms(sim-dob)':>13s} {'ratio':>7s} {'corr':>6s}")
for rk in sorted(set(route[LOW])):
    ii = [i for i in idx if route[i] == rk]
    a_ = np.concatenate([W['dob'][i] for i in ii]); b_ = np.concatenate([sim[i] for i in ii])
    P(f"    {rk:22s} {str(LEVEL[rk]):5s} {len(ii):3d} {np.sqrt(np.mean(a_**2)):9.4f}"
      f" {np.sqrt(np.mean((a_-b_)**2)):13.4f} {np.sqrt(np.mean((a_-b_)**2))/max(np.sqrt(np.mean(a_**2)),1e-9):7.2f}"
      f" {np.corrcoef(a_, b_)[0,1]:6.3f}")
P("    (a small ratio + high corr = the observer's own arithmetic, driven by logged signals, IS the logged")
P("     channel; this is structural arithmetic on logged data, not a closed-loop prediction.)")

# ---- the band variable, three regressor specifications ----------------------------------------
y_fit = (W['cmd'][ar, BK] - K_FIT * W['aa'][ar, BK] - C_FIT) * sgn          # the orchestrator's frame
y_map = (W['cmd'][ar, BK] - hold_flown_aa[ar, BK]) * sgn                    # vs each route's OWN flown map
pred_d = 0.15 * hold_unlev_aa[ar, BK] * 1.0                                 # PR-2's predicted |delta|

P("")
P("=" * 112)
P("C.  PR-2/PR-3 -- CENTRE and HALF-WIDTH per route, same |angle| quintiles as the orchestrator's")
P("    CENTRE = (med_away + med_toward)/2, HALF-WIDTH = (med_away - med_toward)/2")
for name, yy in (("y_fit  (orchestrator's single k=0.00556, c=-0.00562)", y_fit),
                 ("y_map  (each route's OWN FLOWN hold map, no constant)", y_map)):
    P("")
    P(f"  -- {name} --")
    P(f"  {'|angle| bin':>19s} " + "".join(f"{'  ' + r[4:8] + ' ' + ('ON ' if LEVEL[r] else 'OFF'):>16s}"
                                           for r in (ON, '0000006d--05e83bb04f', OFF, '00000076--d0b7ea7e4d')))
    P(f"  {'':>19s} " + "".join(f"{'ctr / hw  n':>16s}" for _ in range(4)))
    for i, lo, hi, mb in bins(LOW):
        row = f"  {lo:8.2f}-{hi:8.2f} "
        for rk in (ON, '0000006d--05e83bb04f', OFF, '00000076--d0b7ea7e4d'):
            m = mb & (route == rk)
            ma, mt = m & (toward == 0), m & (toward == 1)
            if ma.sum() < 1 or mt.sum() < 1:
                row += f"{'  --':>16s}"
            else:
                a_, t_ = np.median(yy[ma]), np.median(yy[mt])
                row += f"{(a_+t_)/2:+7.4f}/{(a_-t_)/2:+6.4f} {int(ma.sum())}+{int(mt.sum())}"
        P(row)
    P(f"  {'PRED |delta| (PR-2)':>19s} " + "  ".join(
        f"{0.15*np.median(hold_unlev_aa[mb & np.isin(route,[ON,OFF]), BK]):.4f}" if (mb & np.isin(route, [ON, OFF])).sum() else " --"
        for i, lo, hi, mb in bins(LOW)))

P("")
P("  POOLED over bins, ON group (6c[,6d]) vs OFF group (6e[,76]), route-cluster bootstrap on the CENTRE proxy")
P("  (centre proxy per episode: y with the toward episodes sign-flipped about the pooled half-width is not")
P("   defined per-episode, so the pooled comparison below is on the DIRECTIONAL medians separately.)")
for name, yy in (("y_fit", y_fit), ("y_map", y_map)):
    P(f"  -- {name} --")
    for grp, rks in (("ON  6c+6d", [ON, '0000006d--05e83bb04f']), ("OFF 6e", [OFF]),
                     ("OFF 6e+76", [OFF, '00000076--d0b7ea7e4d']), ("ON  6c only", [ON])):
        m = LOW & np.isin(route, rks)
        ma, mt = m & (toward == 0), m & (toward == 1)
        ea, ca = boot_ci(yy[ma], route[ma]); et, ct = boot_ci(yy[mt], route[mt])
        P(f"    {grp:12s} n {int(ma.sum()):3d}/{int(mt.sum()):3d}  away {ea:+.4f} [{ca[0]:+.4f},{ca[1]:+.4f}]"
          f"   toward {et:+.4f} [{ct[0]:+.4f},{ct[1]:+.4f}]   centre {(ea+et)/2:+.4f}  hw {(ea-et)/2:+.4f}")

P("")
P("=" * 112)
P("D.  THE POOLED LEVEL-INTERACTION REGRESSION -- the best-powered form of the contrast")
P("    cmd[bk-3] = a*hold_unlev(aa,v) + b*hold_unlev(aa,v)*OFF + Fa*sj + d*sj*toward + c")
P("    hold_unlev is already ODD in the angle, so a is the plant-spring / map ratio and")
P("    PR-2 (level passes straight through, nothing absorbs) => b = -0.15")
P("    PR-3 (an in-loop integrator absorbs it)               => b = 0")
for lbl, rks in (("6c ON  vs 6e OFF            ", [ON, OFF]),
                 ("6c+6d ON vs 6e OFF          ", [ON, '0000006d--05e83bb04f', OFF]),
                 ("6c+6d ON vs 6e+76 OFF       ", [ON, '0000006d--05e83bb04f', OFF, '00000076--d0b7ea7e4d'])):
    m = LOW & np.isin(route, rks)
    off = (~lvl).astype(float)
    X = np.vstack([hold_unlev_aa[ar, BK], hold_unlev_aa[ar, BK] * off, sj, sj * toward, np.ones(N)]).T[m]
    yv = W['cmd'][ar, BK][m]
    c_, *_ = np.linalg.lstsq(X, yv, rcond=None)
    resid = yv - X @ c_
    s2 = resid @ resid / max(len(yv) - X.shape[1], 1)
    try:
        cov = s2 * np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(cov))
    except np.linalg.LinAlgError:
        se = np.full(5, np.nan)
    P(f"    {lbl} n {int(m.sum()):3d}  a {c_[0]:+.3f}+-{se[0]:.3f}   b {c_[1]:+.3f}+-{se[1]:.3f}"
      f"  (95% CI {c_[1]-1.96*se[1]:+.3f}..{c_[1]+1.96*se[1]:+.3f})   Fa {c_[2]:+.4f}  d {c_[3]:+.4f}  c {c_[4]:+.4f}")
    P(f"      resid rms {np.sqrt(s2):.4f};  PR-2 wants b = -0.150, PR-3 wants b = 0."
      f"  {'BOTH inside CI -> UNDERPOWERED' if (c_[1]-1.96*se[1] < -0.15 < c_[1]+1.96*se[1]) and (c_[1]-1.96*se[1] < 0 < c_[1]+1.96*se[1]) else 'DISCRIMINATES'}")

P("")
P("=" * 112)
P("E.  PR-4 / PR-5 -- THE OBSERVER AT BREAKAWAY.  dob . sign(angle) at bk-3, all 5 routes, n=%d" % int(LOW.sum()))
dob_s = W['dob'][ar, BK] * sgn
dob_d0 = W['dob'][ar, d0] * sgn
I_s = W['I'][ar, BK] * sgn
P_s = W['P'][ar, BK] * sgn
cmd_s = W['cmd'][ar, BK] * sgn
hff_s = hold_flown_aa[ar, BK] * sgn
fade = np.interp(v, DOB_FADE_BP, [0.0, 1.0])
mis = (W['cmd'][ar, d0] - hold_flown_aa[ar, d0]) * sgn      # the standing mismatch at dwell start
P("")
P("  PR-5  dob . sign at breakaway, and its GROWTH through the dwell, by dwell duration quartile")
P(f"  {'dwell (s)':>14s} {'n':>4s} {'dob@d0':>9s} {'dob@bk':>9s} {'growth':>9s} {'growth CI':>20s}"
  f" {'per s':>8s} {'PR-5 shape':>11s}")
qd = np.quantile(dwell[LOW], [0, .25, .5, .75, 1.0])
for i in range(4):
    lo, hi = qd[i], qd[i + 1]
    m = LOW & (dwell >= lo) & (dwell <= hi if i == 3 else dwell < hi)
    if m.sum() < 4:
        continue
    gr = dob_s - dob_d0
    e, c = boot_ci(gr[m], route[m])
    td = float(np.median(dwell[m]))
    shape = td / (2 * TAU) - (1 - np.exp(-2 * td / TAU)) / 4
    P(f"  {lo:6.2f}-{hi:6.2f} {int(m.sum()):4d} {np.median(dob_d0[m]):+9.4f} {np.median(dob_s[m]):+9.4f}"
      f" {e:+9.4f} [{c[0]:+.4f},{c[1]:+.4f}] {e/max(td,1e-3):+8.4f} {shape:11.3f}")
e, c = boot_ci((dob_s - dob_d0)[LOW], route[LOW])
P(f"  POOLED growth {e:+.4f} [{c[0]:+.4f},{c[1]:+.4f}]   (route-cluster, 5 clusters)")
sl = np.polyfit(dwell[LOW], (dob_s - dob_d0)[LOW], 1)
P(f"  OLS growth vs dwell: slope {sl[0]:+.4f} /s  intercept {sl[1]:+.4f}"
  f"   corr {np.corrcoef(dwell[LOW], (dob_s-dob_d0)[LOW])[0,1]:+.3f}")
P(f"  standing mismatch at dwell start (cmd - hold_flown).sign: median {np.median(mis[LOW]):+.4f}"
  f"  -> PR-5 predicts growth/s = {np.median(mis[LOW])/(2*TAU):+.4f}")

P("")
P("  PR-4  the observer's authority schedule fade(v) = interp(v,[3,6],[0,1]) -- is the absorber the observer?")
P(f"  {'v band':>12s} {'fade':>5s} {'n':>4s} {'dob@bk . sgn':>13s} {'CI':>20s} {'I@bk . sgn':>11s} {'growth':>9s}")
for lo, hi in ((2.0, 3.0), (3.0, 4.5), (4.5, 6.0), (6.0, 8.0)):
    m = LOW & (v >= lo) & (v < hi)
    if m.sum() < 3:
        P(f"  {lo:5.1f}-{hi:5.1f} {np.interp((lo+hi)/2,DOB_FADE_BP,[0,1]):5.2f} {int(m.sum()):4d}   (too few)")
        continue
    e, c = boot_ci(dob_s[m], route[m])
    eI, _ = boot_ci(I_s[m], route[m])
    eg, _ = boot_ci((dob_s - dob_d0)[m], route[m])
    P(f"  {lo:5.1f}-{hi:5.1f} {np.interp((lo+hi)/2,DOB_FADE_BP,[0,1]):5.2f} {int(m.sum()):4d}"
      f" {e:+13.4f} [{c[0]:+.4f},{c[1]:+.4f}] {eI:+11.4f} {eg:+9.4f}")

P("")
P("=" * 112)
P("F.  THE SUBSTITUTION ACCOUNTING -- who supplies cmd at breakaway, and does it change with the level?")
P("    all in the OUTWARD frame (x sign(angle at dwell start)), medians with route-cluster CIs where >1 route")
terms = [('cmd', cmd_s), ('hold_ff(flown)', hff_s), ('move', W['move'][ar, BK] * sgn),
         ('z (hyst)', W['z'][ar, BK] * sgn), ('rate loop', W['rl'][ar, BK] * sgn),
         ('dob', dob_s), ('P', P_s), ('I', I_s)]
for lbl, rks in (("6c ON ", [ON]), ("6d ON ", ['0000006d--05e83bb04f']), ("6e OFF", [OFF]),
                 ("76 OFF", ['00000076--d0b7ea7e4d']), ("75 OFF", ['00000075--6c8687d5bd'])):
    m = LOW & np.isin(route, rks)
    P(f"  {lbl} n {int(m.sum()):3d}  " + "  ".join(f"{nm} {np.median(x[m]):+.4f}" for nm, x in terms))
P("")
P("  the same, split by direction (outward-breaking vs inward-breaking episodes):")
for lbl, rks in (("6c ON ", [ON]), ("6e OFF", [OFF])):
    for dlbl, tw in (("out", 0), ("in ", 1)):
        m = LOW & np.isin(route, rks) & (toward == tw)
        if m.sum() < 3:
            continue
        P(f"  {lbl} {dlbl} n {int(m.sum()):3d}  " + "  ".join(f"{nm} {np.median(x[m]):+.4f}" for nm, x in terms))
P("")
P("  ON-group minus OFF-group, matched by |angle| quintile then averaged (reduces the angle-mix confound):")
for nm, x in terms:
    ds = []
    for i, lo, hi, mb in bins(LOW):
        a_ = mb & (route == ON); b_ = mb & (route == OFF)
        if a_.sum() >= 2 and b_.sum() >= 2:
            ds.append(np.median(x[b_]) - np.median(x[a_]))
    if ds:
        P(f"    {nm:15s} mean over {len(ds)} matched bins  {np.mean(ds):+.4f}   per-bin {['%+.4f' % q for q in ds]}")
pb = []
for i, lo, hi, mb in bins(LOW):
    a_ = mb & (route == ON); b_ = mb & (route == OFF)
    if a_.sum() >= 2 and b_.sum() >= 2:
        pb.append(0.15 * np.median(hold_unlev_aa[mb & np.isin(route, [ON, OFF]), BK]))
P(f"    {'PR-2 predicted':15s} mean over {len(pb)} matched bins  {-np.mean(pb):+.4f}   per-bin {['%+.4f' % -q for q in pb]}")

txt = "\n".join(OUT)
(HERE / 'out' / 'hl_contrast.txt').write_text(txt, encoding='utf-8')
print(txt)
