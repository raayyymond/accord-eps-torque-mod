"""STREAM holdlevel, step 5: WHICH TERM CARRIES THE ANGLE-PROPORTIONAL CENTRE.

Fixes two faults in my own step-4 run:
  - route 75 (00000075--6c8687d5bd) flew with NO disturbance observer (AccordDobHz absent -> dob_hz = 0.0 ->
    HondaAccordDisturbanceObserver.update returns 0; measured dob rms = 0.0000 over all 53 episodes).  Its 53
    exact zeros dragged every pooled median of the dob channel to exactly 0.  It is excluded from the observer
    tests and used instead as a FREE observer-off contrast.
  - the step-4 "ON minus OFF" table was computed OFF minus ON; sign fixed and it is noise either way.

Sections
  G  per-term outward-frame contribution vs |angle|: which term grows with the angle?
  H  the plant-spring / map ratio per route (no interaction term, so no collinearity)
  I  PR-5 on the observer routes only: does the observer wind through the dwell?
  J  the observer-on vs observer-off contrast (route 75), with its confounds named
  K  the centre profile where the observer has NO authority (v < 3, fade = 0) vs full (v > 6)
"""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
SS = HERE.parents[1] / 'lowspeed' / 'a_stickslip'
sys.path.insert(0, str(SS))
from ss_load import load_all, boot_ci, PRE
from sslib import hold_torque, G_BP, G_V

LEVEL = {'0000006c--68c6e94b17': True, '0000006d--05e83bb04f': True, '0000006e--6ca3e014fd': False,
         '00000075--6c8687d5bd': False, '00000076--d0b7ea7e4d': False}
NO_DOB = '00000075--6c8687d5bd'
OBS = [r for r in LEVEL if r != NO_DOB]
K_FIT, C_FIT = 0.005560, -0.005620
TAU = 1.0 / (2.0 * np.pi * 0.6)
J = 8e-5

EP, W, EX, VAL = load_all()
N = len(EP); ar = np.arange(N)
col = lambda k: np.array([e[k] for e in EP])
g, v, sj, route, dwell, kind = col('group'), col('v'), col('sjump'), col('route'), col('dwell_s'), col('kind')
d0 = np.maximum(col('w_d0'), 0)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
BK = PRE - 3
aa_pre = W['aa'][:, PRE]; sgn = np.sign(aa_pre); aabs = np.abs(aa_pre)
toward = (sj == -np.sign(aa_pre)).astype(float)
LOW = TQ & (v >= 2) & (v < 8)
QS = np.quantile(aabs[LOW], [0, .2, .4, .6, .8, 1.0])
fade = np.interp(v, [3.0, 6.0], [0.0, 1.0])

hold_flown = np.zeros_like(W['aa']); hold_unlev = hold_torque(W['aa'], W['v'], False)
for rk, L in LEVEL.items():
    m = route == rk
    if m.any():
        hold_flown[m] = hold_torque(W['aa'][m], W['v'][m], L)

TERMS = [('cmd', W['cmd'][ar, BK]), ('hold_ff', W['hold_ff'][ar, BK]), ('move', W['move'][ar, BK]),
         ('z_hyst', W['z'][ar, BK]), ('rate_lp', W['rl'][ar, BK]), ('dob', W['dob'][ar, BK]),
         ('P', W['P'][ar, BK]), ('I', W['I'][ar, BK]), ('dob+I', W['dob'][ar, BK] + W['I'][ar, BK]),
         ('hold@aa_flown', hold_flown[ar, BK]), ('hold@aa_unlev', hold_unlev[ar, BK])]
O = []; P_ = O.append


def bins(mask):
    for i in range(5):
        lo, hi = QS[i], QS[i + 1]
        yield i, lo, hi, mask & (aabs >= lo) & (aabs <= hi if i == 4 else aabs < hi)


P_("=" * 118)
P_("G.  PER-TERM OUTWARD-FRAME CONTRIBUTION vs |angle|, at breakaway (bk-3).  OBSERVER ROUTES ONLY (6c,6d,6e,76)")
P_("    every term x sign(angle at dwell start); medians; n = 92 episodes, 4 route clusters")
P_("    a term that CAUSES an angle-proportional centre must itself grow with |angle|")
M = LOW & np.isin(route, OBS)
P_("")
hdr = f"  {'term':15s}" + "".join(f"{f'{QS[i]:.2f}-{QS[i+1]:.2f}':>13s}" for i in range(5)) + f"{'slope/deg':>11s}{'CI':>22s}"
P_(hdr)
slopes = {}
for nm, x in TERMS:
    xs = x * sgn
    row = f"  {nm:15s}"
    for i, lo, hi, mb in bins(M):
        row += f"{np.median(xs[mb]):+13.4f}" if mb.sum() >= 3 else f"{'--':>13s}"
    # slope against |angle|, robust-ish: OLS on the 5 bin medians vs bin median |angle|, plus a per-episode OLS
    bm = [(np.median(aabs[mb]), np.median(xs[mb])) for i, lo, hi, mb in bins(M) if mb.sum() >= 3]
    sl = np.polyfit([q[0] for q in bm], [q[1] for q in bm], 1)[0] if len(bm) >= 3 else np.nan
    est, ci = boot_ci(xs[M], route[M])
    # per-episode slope with a route-cluster bootstrap
    def slope_fn(ii):
        return float(np.polyfit(aabs[M][ii], xs[M][ii], 1)[0])
    u = np.unique(route[M]); rng = np.random.default_rng(7)
    idxs = {c: np.where(route[M] == c)[0] for c in u}
    bs = []
    for _ in range(600):
        pick = rng.choice(u, len(u))
        ii = np.concatenate([idxs[c] for c in pick])
        try:
            bs.append(slope_fn(ii))
        except Exception:
            pass
    s_all = float(np.polyfit(aabs[M], xs[M], 1)[0])
    lo_, hi_ = np.percentile(bs, [2.5, 97.5])
    slopes[nm] = (s_all, lo_, hi_)
    P_(row + f"{s_all:+11.5f} [{lo_:+.5f},{hi_:+.5f}]")
P_("")
P_("  slope/deg is the per-episode OLS slope of (term x sign) against |angle| over 0.01-20 deg, with a")
P_("  4-route-cluster bootstrap CI.  The map's OWN slope is the hold@aa rows -- the benchmark.")

P_("")
P_("=" * 118)
P_("H.  THE PLANT-SPRING / MAP RATIO at breakaway, per route (no interaction term -> no collinearity)")
P_("    cmd[bk-3] = a * hold_unlev(aa,v) + Fa*sj + d*sj*toward + c    (hold_unlev is odd in the angle)")
P_("    a = how many times the UNLEVELLED map the plant actually demands.  The flown level supplies 1.15 of it")
P_("    on 6c/6d and 1.00 on 6e/76/75, so 'a - level' is the shortfall the rest of the loop must carry.")
P_("")
P_(f"  {'route':22s} {'lvl':5s} {'obs':4s} {'n':>4s} {'a':>8s} {'+-':>7s} {'a - level':>10s} {'Fa':>8s} {'d':>8s} {'c':>8s} {'resid':>7s}")
for rk in sorted(LEVEL):
    m = LOW & (route == rk)
    if m.sum() < 8:
        continue
    X = np.vstack([hold_unlev[ar, BK], sj, sj * toward, np.ones(N)]).T[m]
    yv = W['cmd'][ar, BK][m]
    c_, *_ = np.linalg.lstsq(X, yv, rcond=None)
    r = yv - X @ c_; s2 = r @ r / max(len(yv) - 4, 1)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    L = 1.15 if LEVEL[rk] else 1.0
    P_(f"  {rk:22s} {str(LEVEL[rk]):5s} {'no' if rk == NO_DOB else 'yes':4s} {int(m.sum()):4d}"
       f" {c_[0]:+8.3f} {se[0]:7.3f} {c_[0]-L:+10.3f} {c_[2*0+1]:+8.4f} {c_[2]:+8.4f} {c_[3]:+8.4f} {np.sqrt(s2):7.4f}")
m = LOW
X = np.vstack([hold_unlev[ar, BK], sj, sj * toward, np.ones(N)]).T[m]
yv = W['cmd'][ar, BK][m]
c_, *_ = np.linalg.lstsq(X, yv, rcond=None)
r = yv - X @ c_; s2 = r @ r / max(len(yv) - 4, 1)
se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
u = np.unique(route[m]); rng = np.random.default_rng(11); idxs = {c: np.where(route[m] == c)[0] for c in u}
bs = []
for _ in range(1000):
    pick = rng.choice(u, len(u)); ii = np.concatenate([idxs[c] for c in pick])
    XX, yy = X[ii], yv[ii]
    try:
        bs.append(np.linalg.lstsq(XX, yy, rcond=None)[0][0])
    except Exception:
        pass
P_(f"  {'ALL FIVE pooled':22s} {'-':5s} {'-':4s} {int(m.sum()):4d} {c_[0]:+8.3f} {se[0]:7.3f}"
   f"   route-cluster 95% CI [{np.percentile(bs,2.5):+.3f},{np.percentile(bs,97.5):+.3f}]")
P_("  (the fork's own comment at latcontrol_vehicle_tunes.py:244/268 cites a MEASURED x1.4-1.65 shortfall")
P_("   at speed, from a different method; this is the low-speed stick-slip band's own reading of it.)")

P_("")
P_("=" * 118)
P_("I.  PR-5 -- DOES THE OBSERVER WIND THROUGH THE DWELL?  observer routes, fade >= 0.9 only (full authority)")
P_("    structural prediction (flown code, wheel stuck): w2(t)/(C-H) = t/(2 tau) - (1-exp(-2t/tau))/4,")
P_("    tau = %.4f s, so growth per second -> 1/(2 tau) = %.3f x the standing mismatch" % (TAU, 1 / (2 * TAU)))
MO = LOW & np.isin(route, OBS) & (fade >= 0.9)
dob_bk = W['dob'][ar, BK] * sgn; dob_0 = W['dob'][ar, d0] * sgn
b_mod = 1.0 / np.interp(W['v'], G_BP, G_V)
mis0 = (W['cmd'][ar, d0] - hold_flown[ar, d0] - b_mod[ar, d0] * W['sr'][ar, d0]) * sgn
P_(f"    n = {int(MO.sum())}, routes {sorted(set(route[MO]))}")
P_("")
P_(f"  {'dwell (s)':>13s} {'n':>4s} {'dob@d0':>9s} {'dob@bk':>9s} {'growth':>9s} {'growth CI':>21s}"
   f" {'mis@d0':>8s} {'g/mis':>7s} {'PR-5':>7s}")
qd = np.quantile(dwell[MO], [0, .33, .66, 1.0])
for i in range(3):
    lo, hi = qd[i], qd[i + 1]
    mb = MO & (dwell >= lo) & (dwell <= hi if i == 2 else dwell < hi)
    if mb.sum() < 5:
        continue
    gr = dob_bk - dob_0
    e, c = boot_ci(gr[mb], route[mb])
    td = float(np.median(dwell[mb])); mm = float(np.median(mis0[mb]))
    shape = td / (2 * TAU) - (1 - np.exp(-2 * td / TAU)) / 4
    P_(f"  {lo:5.2f}-{hi:5.2f} {int(mb.sum()):4d} {np.median(dob_0[mb]):+9.4f} {np.median(dob_bk[mb]):+9.4f}"
       f" {e:+9.4f} [{c[0]:+.4f},{c[1]:+.4f}] {mm:+8.4f} {e/max(abs(mm),1e-6):+7.2f} {shape:7.2f}")
e, c = boot_ci((dob_bk - dob_0)[MO], route[MO])
P_(f"  POOLED growth {e:+.4f} [{c[0]:+.4f},{c[1]:+.4f}]   median mis@d0 {np.median(mis0[MO]):+.4f}")
sl = np.polyfit(dwell[MO], (dob_bk - dob_0)[MO], 1)
P_(f"  OLS growth vs dwell  slope {sl[0]:+.4f}/s  intercept {sl[1]:+.4f}  corr {np.corrcoef(dwell[MO], (dob_bk-dob_0)[MO])[0,1]:+.3f}")
P_(f"  OLS dob@bk vs dwell  slope {np.polyfit(dwell[MO], dob_bk[MO],1)[0]:+.4f}/s"
   f"  corr {np.corrcoef(dwell[MO], dob_bk[MO])[0,1]:+.3f}")
P_(f"  OLS dob@bk vs |angle| slope {np.polyfit(aabs[MO], dob_bk[MO],1)[0]:+.5f}/deg"
   f"  corr {np.corrcoef(aabs[MO], dob_bk[MO])[0,1]:+.3f}")
P_(f"  OLS dob@bk vs mis@d0 slope {np.polyfit(mis0[MO], dob_bk[MO],1)[0]:+.3f}"
   f"  corr {np.corrcoef(mis0[MO], dob_bk[MO])[0,1]:+.3f}")
P_("  NOTE: the observer is NOT reset at a dwell -- it has usually already settled onto the standing")
P_("  mismatch before the dwell begins, so a small GROWTH with a large LEVEL is the expected signature of")
P_("  an already-wound integrator, not of one that is not winding.  dob@d0 is the level it arrived with.")

P_("")
P_("=" * 118)
P_("J.  THE FREE OBSERVER-OFF CONTRAST: route 75 ran NO observer (AccordDobHz absent -> dob_hz 0 -> returns 0)")
P_("    CONFOUNDS, from initData: 75 is a DIFFERENT fork commit (08a5a7064 vs 84766cdc), AccordTorqueKi 0.6 not")
P_("    0.3 (x2 at v<8, since the KiHigh schedule starts at 8 m/s), SteerKP 0.85 not 1.0, AccordRateLoopGain")
P_("    0.0006 not 0.001, rate-loop RC 0.03 not 0.01, AccordRefFilter 0.12 not 0.06, and AccordHoldLevel absent.")
P_("    SteerFriction 0.212 on 75 and 6d is INERT: latcontrol_torque.py:675 zeroes the relay whenever")
P_("    AccordFrictionHyst > 0, and it was 0.015 on all five routes.")
P_("")
P_(f"  {'route':22s} {'obs':4s} {'Ki':>5s} {'n':>4s} {'cmd.sgn':>9s} {'hold_ff':>9s} {'dob':>9s} {'I':>9s}"
   f" {'dob+I':>9s} {'P':>9s} {'centre(y_fit)':>14s}")
y_fit = (W['cmd'][ar, BK] - K_FIT * W['aa'][ar, BK] - C_FIT) * sgn
KI = {'0000006c--68c6e94b17': 0.3, '0000006d--05e83bb04f': 0.3, '0000006e--6ca3e014fd': 0.3,
      '00000075--6c8687d5bd': 0.6, '00000076--d0b7ea7e4d': 0.3}
for rk in sorted(LEVEL):
    m = LOW & (route == rk)
    ma, mt = m & (toward == 0), m & (toward == 1)
    ctr = (np.median(y_fit[ma]) + np.median(y_fit[mt])) / 2 if ma.sum() and mt.sum() else np.nan
    P_(f"  {rk:22s} {'no' if rk == NO_DOB else 'yes':4s} {KI[rk]:5.1f} {int(m.sum()):4d}"
       f" {np.median(W['cmd'][ar,BK][m]*sgn[m]):+9.4f} {np.median(W['hold_ff'][ar,BK][m]*sgn[m]):+9.4f}"
       f" {np.median(W['dob'][ar,BK][m]*sgn[m]):+9.4f} {np.median(W['I'][ar,BK][m]*sgn[m]):+9.4f}"
       f" {np.median((W['dob'][ar,BK]+W['I'][ar,BK])[m]*sgn[m]):+9.4f}"
       f" {np.median(W['P'][ar,BK][m]*sgn[m]):+9.4f} {ctr:+14.4f}")
P_("")
for lbl, rks in (("observer ON  (6c,6d,6e,76)", OBS), ("observer OFF (75)", [NO_DOB])):
    m = LOW & np.isin(route, rks)
    for nm, x in (('dob', W['dob'][ar, BK]), ('I', W['I'][ar, BK]), ('dob+I', W['dob'][ar, BK] + W['I'][ar, BK]),
                  ('cmd', W['cmd'][ar, BK])):
        e, c = boot_ci((x * sgn)[m], route[m])
        P_(f"  {lbl:28s} {nm:6s} n {int(m.sum()):3d}  {e:+.4f} [{c[0]:+.4f},{c[1]:+.4f}]")

P_("")
P_("=" * 118)
P_("K.  WHERE THE OBSERVER HAS NO AUTHORITY.  fade(v) = interp(v,[3,6],[0,1]) is EXACTLY 0 below 3 m/s.")
P_("    If the observer manufactured the angle-proportional centre, the centre must collapse at v < 3 m/s.")
P_("")
P_(f"  {'v band':>11s} {'fade':>5s} {'n':>4s} {'n_aw/n_tw':>10s} {'med|ang|':>9s} {'centre':>8s} {'hw':>8s}"
   f" {'dob.sgn':>9s} {'I.sgn':>8s} {'hold_ff':>8s}")
for lo, hi in ((2.0, 3.0), (3.0, 4.5), (4.5, 6.0), (6.0, 8.0)):
    for grp, rks in (('obs', OBS), ('all', list(LEVEL))):
        m = LOW & (v >= lo) & (v < hi) & np.isin(route, rks)
        ma, mt = m & (toward == 0), m & (toward == 1)
        if ma.sum() < 2 or mt.sum() < 2:
            P_(f"  {lo:4.1f}-{hi:4.1f} {grp} {np.interp((lo+hi)/2,[3,6],[0,1]):5.2f} {int(m.sum()):4d}"
               f" {int(ma.sum()):4d}/{int(mt.sum()):<5d}  (too few)")
            continue
        a_, t_ = np.median(y_fit[ma]), np.median(y_fit[mt])
        P_(f"  {lo:4.1f}-{hi:4.1f} {grp} {np.interp((lo+hi)/2,[3,6],[0,1]):5.2f} {int(m.sum()):4d}"
           f" {int(ma.sum()):4d}/{int(mt.sum()):<5d} {np.median(aabs[m]):9.2f} {(a_+t_)/2:+8.4f} {(a_-t_)/2:+8.4f}"
           f" {np.median((W['dob'][ar,BK]*sgn)[m]):+9.4f} {np.median((W['I'][ar,BK]*sgn)[m]):+8.4f}"
           f" {np.median((W['hold_ff'][ar,BK]*sgn)[m]):+8.4f}")
P_("")
P_("  and the same split by |angle| inside the fade = 0 band, if n allows:")
m0 = LOW & (v < 3.0)
P_(f"  v < 3 m/s: n {int(m0.sum())}, routes {sorted(set(route[m0]))}, |angle| {np.sort(np.round(aabs[m0],2))}")
P_(f"    dob.sgn all exactly zero? {bool(np.all(W['dob'][ar,BK][m0] == 0))}"
   f"   max|dob| {np.max(np.abs(W['dob'][ar,BK][m0])):.2e}")

txt = "\n".join(O)
(HERE / 'out' / 'hl_terms.txt').write_text(txt, encoding='utf-8')
print(txt)
