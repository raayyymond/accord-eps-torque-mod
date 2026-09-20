"""STREAM holdlevel, step 3: PRE-REGISTRATION.  Run and frozen BEFORE any per-route band centre is looked at.

Writes out/hl_prereg.txt.

WHAT THE TOGGLE DOES, read from the flown source (fork HEAD == the flown commit 84766cdc523f, file clean):
  latcontrol_torque.py:651-655, 689-692
    hold_level = toggles.accord_hold_level
    hold_fn    = get_honda_accord_hold_torque            if hold_level
                 lambda a,v: get_honda_accord_hold_torque(a, v, level=False)   otherwise
    plant_ff_torque = -get_honda_accord_rate_plant_ff(..., hold_level=hold_level)
    accord_dob.update(..., hold_fn, ...)
  => ONE toggle gates BOTH the feedforward's hold term AND the observer's internal spring model,
     by the SAME factor.  latcontrol_vehicle_tunes.py:263 says so in words ("THE LEVEL AND THE
     OBSERVER'S INTERNAL MODEL MOVE TOGETHER, which is what makes it safe").
  get_honda_accord_hold_level(v, True) = interp(v, [12.5, 17.5], [1.15, 1.45]) -> FLAT 1.15 for all v <= 12.5,
  so across the whole 2-8 m/s band the toggle is exactly x1.15 on the hold map, nothing else.

THE OBSERVER IS AN INTEGRATOR WHEN THE WHEEL IS STUCK -- structural, from the flown code:
  residual = u_left_delayed - (spring_model + b*rate + J*acc);  w1,w2 two first-order lags at f_hz = 0.6 Hz;
  output = clip(w2 * fade, +-0.3), fade = interp(v, [3.0, 6.0], [0, 1]);
  and u_left = -output_torque ALREADY CONTAINS the observer's own previous output.
  So the observer sees itself with loop gain fade*Q(s), Q = 1/(1+tau s)^2, tau = 1/(2 pi 0.6) = 0.2653 s, Q(0) = 1.
  With the wheel STUCK the angle cannot move, so nothing else closes the loop and
      w2 / (C - H) = Q / (1 - fade Q)
  For fade = 1 that is 1 / (tau s (2 + tau s)) -- A PURE INTEGRATOR of gain 1/(2 tau) = 1.885 per second.
  For fade < 1 it settles at (C - H) * fade / (1 - fade).
  C - H = the standing command-minus-model mismatch; H uses the LEVELLED map when the toggle is on.

HYPOTHESES AND THEIR PRE-REGISTERED PREDICTIONS (delta = 6e OFF minus 6c ON, at matched |angle| and v):
  PR-1  ARITHMETIC IDENTITY, must hold or my hold-term reconstruction is wrong:
        delta(hold_ff . sign) = -0.15 * hold_unlevelled(angle_des, v)
  PR-2  (A) HOLD-MAP LEVEL DEFICIT, nothing in the loop absorbs it:
        the lost feedforward passes straight to the command ->
        delta(cmd . sign at breakaway) = -0.15 * hold_unlevelled   (6e's command sits LESS outward)
        equivalently: CENTRE in the orchestrator's k_fit frame DROPS by that amount on 6e,
        and CENTRE measured against each route's OWN FLOWN MAP is UNCHANGED.
  PR-3  (B) AN IN-LOOP INTEGRATOR ABSORBS IT:
        delta(cmd . sign) ~ 0, materially smaller than PR-2's number, and the missing 0.15*hold
        reappears in dob . sign and/or I . sign.  CENTRE against each route's own flown map RISES
        by +0.15 * hold_unlevelled (the deficit the rest of the loop must carry is bigger).
  PR-4  WHICH integrator, decided inside the band and immune to route confounds:
        the observer's authority is fade(v) = interp(v, [3, 6], [0, 1]).  If the observer is the absorber,
        the absorption must be ABSENT below 3 m/s and FULL above 6 m/s.  If absorption is present at
        v < 3 m/s it is the PID's I, not the observer.
  PR-5  the observer's stuck-wheel integrator gain is 1/(2 tau) = 1.885/s, so
        dob . sign at breakaway must RISE with dwell duration, slope ~ 1.885 * (deficit) per second,
        and its step shape is (C-H)*[t/(2 tau) - (1 - exp(-2 t / tau))/4].  Tabulated below.

DECISION RULE, fixed now:
  - PR-1 fails            -> my reconstruction is wrong; report that and nothing else.
  - |delta cmd| CI covers PR-2's predicted value and excludes 0     -> (A), the level passes through.
  - |delta cmd| CI covers 0 and excludes PR-2's value               -> (B), something absorbs it; PR-4 names it.
  - both inside the CI (i.e. the CI spans 0 and the prediction)     -> UNDERPOWERED, no verdict from the contrast.
  Power is computed BELOW, before any measurement, so that the third outcome cannot be spun as a null.
"""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
SS = HERE.parents[1] / 'lowspeed' / 'a_stickslip'
sys.path.insert(0, str(SS))
from ss_load import load_all, PRE
from sslib import hold_torque

LEVEL = {'0000006c--68c6e94b17': True, '0000006d--05e83bb04f': True, '0000006e--6ca3e014fd': False,
         '00000075--6c8687d5bd': False, '00000076--d0b7ea7e4d': False}
K_FIT, C_FIT = 0.005560, -0.005620      # the orchestrator's fit (reproduced to 7 dp by orch_crux_check)
TAU = 1.0 / (2.0 * np.pi * 0.6)

EP, W, EX, VAL = load_all()
N = len(EP); ar = np.arange(N)
col = lambda k: np.array([e[k] for e in EP])
g, v, sj, route, dwell = col('group'), col('v'), col('sjump'), col('route'), col('dwell_s')
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
BK = PRE - 3
aa_pre = W['aa'][:, PRE]
toward = (sj == -np.sign(aa_pre)).astype(float)
LOW = TQ & (v >= 2) & (v < 8)
aabs = np.abs(aa_pre)
# the orchestrator's own quintile bins of |angle|, recomputed identically
QS = np.quantile(aabs[LOW], [0, .2, .4, .6, .8, 1.0])
y = (W['cmd'][ar, BK] - K_FIT * W['aa'][ar, BK] - C_FIT) * np.sign(aa_pre)

L = []
L.append(__doc__)
L.append("=" * 108)
L.append("PRE-REGISTERED PREDICTED DELTA, from the fork's map arithmetic alone")
L.append("  d = 0.15 * hold_unlevelled(|angle|, v) = 0.15 * k(v) * sat(v) * tanh(|angle| / sat(v))")
L.append("  evaluated at each bin's MEDIAN |angle| and the bin's median v across the two contrast routes")
L.append("")
L.append(f"  {'|angle| bin (deg)':>20s} {'med|ang|':>9s} {'med v':>6s} {'hold_unlev':>11s} {'PREDICTED d':>12s}"
         f" {'as frac of':>11s}")
L.append(f"  {'':>20s} {'':>9s} {'':>6s} {'':>11s} {'(PR-2)':>12s} {'hw 0.0333':>11s}")
CON = LOW & np.isin(route, ['0000006c--68c6e94b17', '0000006e--6ca3e014fd'])
pred = []
for i in range(5):
    lo, hi = QS[i], QS[i + 1]
    m = CON & (aabs >= lo) & (aabs <= hi if i == 4 else aabs < hi)
    if m.sum() < 2:
        pred.append(np.nan); continue
    ma, mv = float(np.median(aabs[m])), float(np.median(v[m]))
    hu = float(hold_torque(np.array([ma]), np.array([mv]), False)[0])
    d = 0.15 * hu
    pred.append(d)
    L.append(f"  {lo:8.2f} - {hi:8.2f} {ma:9.2f} {mv:6.2f} {hu:11.4f} {d:12.4f} {d/0.033285:11.2f}")
L.append("")
L.append("  NOTE the shape: the prediction is essentially LINEAR in |angle| (tanh is linear until")
L.append("  |angle| ~ sat/3, and sat(v) is 94-300 deg over 2-8 m/s), so PR-2 predicts an angle-PROPORTIONAL")
L.append("  delta with slope 0.15*k(v) ~ 0.00054-0.00078 torque/deg.  At the MEDIAN episode angle that is")
L.append("  about a thousandth of a torque unit.  Which is the whole problem -- see POWER.")

L.append("")
L.append("=" * 108)
L.append("POWER I ACTUALLY HAVE -- computed before any contrast is measured")
L.append("  per-episode scatter of the band variable y = (cmd - k_fit*aa - c)*sign(aa) at breakaway,")
L.append("  pooled over the two contrast routes, by direction; MDE = 2.8 * sqrt(s_a^2/n_a + s_b^2/n_b)")
L.append("  for the difference of two medians (1.253 * sd/sqrt(n) per median, 95 % two-sided).")
L.append("")
sd_all = float(np.std(y[CON], ddof=1))
L.append(f"  sd(y) over the contrast set, all directions   {sd_all:.4f}   (n {int(CON.sum())})")
for lbl, tw in (("OUTWARD", 0), ("INWARD", 1)):
    m = CON & (toward == tw)
    L.append(f"  sd(y) {lbl:8s} {float(np.std(y[m], ddof=1)):.4f}  n {int(m.sum())}")
L.append("")
L.append(f"  {'|angle| bin':>20s} {'n 6c':>5s} {'n 6e':>5s} {'sd':>7s} {'MDE(centre)':>12s} {'PREDICTED d':>12s}"
         f" {'MDE/pred':>9s}")
for i in range(5):
    lo, hi = QS[i], QS[i + 1]
    mb = CON & (aabs >= lo) & (aabs <= hi if i == 4 else aabs < hi)
    n_c = int((mb & (route == '0000006c--68c6e94b17')).sum())
    n_e = int((mb & (route == '0000006e--6ca3e014fd')).sum())
    if mb.sum() < 4 or n_c < 1 or n_e < 1:
        L.append(f"  {lo:8.2f} - {hi:8.2f} {n_c:5d} {n_e:5d}        --  (too few)")
        continue
    s = float(np.std(y[mb], ddof=1))
    # a CENTRE is (med_away + med_toward)/2, so its se is half the quadrature sum of two median se's
    se = 0.5 * np.sqrt(2) * 1.2533 * s / np.sqrt(max(min(n_c, n_e), 1))
    mde = 1.96 * np.sqrt(2) * se
    p = pred[i]
    L.append(f"  {lo:8.2f} - {hi:8.2f} {n_c:5d} {n_e:5d} {s:7.4f} {mde:12.4f} {p:12.4f} {mde/max(p,1e-9):9.1f}x")
L.append("")
L.append("  MDE/pred is the factor by which the smallest detectable centre difference exceeds the")
L.append("  pre-registered prediction.  Any value >> 1 means a null in that bin is UNINFORMATIVE by")
L.append("  construction, decided before the data were looked at.")

L.append("")
L.append("=" * 108)
L.append("PR-5 REFERENCE SHAPE: the observer's stuck-wheel step response, w2(t)/(C-H)")
L.append("  w2(t)/(C-H) = t/(2 tau) - (1 - exp(-2 t / tau))/4,  tau = %.4f s (0.6 Hz), fade = 1" % TAU)
L.append("  (fade < 1: it settles instead, at fade/(1-fade) * (C-H) with the same corner)")
L.append("")
row = "   t (s)      " + "".join(f"{t:8.2f}" for t in (0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0))
L.append(row)
vals = []
for t in (0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0):
    vals.append(t / (2 * TAU) - (1 - np.exp(-2 * t / TAU)) / 4)
L.append("   w2/(C-H)   " + "".join(f"{x:8.3f}" for x in vals))
L.append("")
L.append("  observed dwell durations on the contrast routes (s): median %.2f, quartiles %.2f / %.2f, max %.2f"
         % (np.median(dwell[CON]), np.percentile(dwell[CON], 25), np.percentile(dwell[CON], 75), dwell[CON].max()))
L.append("  so the observer's own structure says it contributes 0.1-1.6 x the standing mismatch across the")
L.append("  observed dwell range -- the SAME ORDER as the half-width.  That makes PR-5 a high-powered test")
L.append("  even where the level contrast (above) is not.")

txt = "\n".join(L)
(HERE / 'out' / 'hl_prereg.txt').write_text(txt, encoding='utf-8')
print(txt)
