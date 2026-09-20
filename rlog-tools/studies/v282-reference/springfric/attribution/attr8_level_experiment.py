"""STEP 8  THE NATURAL EXPERIMENT, run on the plant read instead of the 12-34 episodes.

Routes 6c and 6d flew AccordHoldLevel ON (x1.15 below 12.5 m/s, confirmed from initData AND from the
logged hold_ff channel: hold_ff / hold_unlev(angdes) = 1.1500 exactly on 6c+6d, 1.0000 on 6e).
Routes 6e, 75, 76 flew it OFF (6e explicitly '0'; 75 and 76 predate the key, so the code had no level).

The episode-level contrast has 12-34 episodes per arm.  The direction-averaged plant read has
360-1400 frames per route in the same |angle| window, and it measures the SAME quantity: the command
that holds the wheel, minus the fork's levelled map.  If the shortfall is MULTIPLICATIVE, x1.15 of
the map closes 15 % of it.  If it is ADDITIVE, x1.15 closes 0.15*map -- a few per cent.

Reported: the ABSOLUTE shortfall per route, what the level moved, and the level multiplier that
would be required to close the shortfall at 2-8 m/s.
"""
import numpy as np
from attr_lib import build

D = build(); W, ar = D['W'], D['ar']
LOW = D['LOW']; route = D['route']
aaW, srW, vW, cmdW = W['aa'], W['sr'], W['v'], W['cmd']
NF = aaW.shape[1]
rmask = np.isin(D['group'], ['T64', 'T64B', 'T5', 'T4'])
FM = np.repeat(rmask[:, None], NF, 1) & (vW >= 2) & (vW < 8)
Sf = np.sign(aaW); MOV = FM & (np.abs(srW) > 3.0)
LEVM = np.abs(D['hold_aa_lev']); UNL = np.abs(D['hold_aa_unlev'])

AW = (1.2, 6.0)      # the |angle| window where every route has frames on both legs
print("=" * 106)
print(f"(1) PER-ROUTE SHORTFALL, |angle| {AW[0]}-{AW[1]} deg, 2-8 m/s, |sr| > 3 deg/s")
print(f"    {'route':>22s} {'lev':>4s} {'n_aw':>6s} {'n_tw':>6s} {'hold_meas':>10s} {'map lev':>9s}"
      f" {'map unlev':>10s} {'SHORTFALL':>10s} {'ratio':>6s}")
rows = {}
for rk in sorted(set(route[LOW])):
    rm = np.repeat((route == rk)[:, None], NF, 1)
    base = MOV & rm & (np.abs(aaW) >= AW[0]) & (np.abs(aaW) < AW[1])
    mp = base & (np.sign(srW) == Sf); mn = base & (np.sign(srW) == -Sf)
    a_ = np.median((cmdW * Sf)[mp]); t_ = np.median((cmdW * Sf)[mn])
    hold = (a_ + t_) / 2
    ml = np.median(LEVM[base]); mu = np.median(UNL[base])
    rows[rk] = dict(lev=D['lev'][rk], hold=hold, ml=ml, mu=mu, sf=hold - ml,
                    n=(int(mp.sum()), int(mn.sum())), base=base)
    print(f"    {rk:>22s} {int(D['lev'][rk]):4d} {int(mp.sum()):6d} {int(mn.sum()):6d} {hold:+10.4f}"
          f" {ml:+9.4f} {mu:+10.4f} {hold-ml:+10.4f} {hold/ml:6.2f}")

on = [v for v in rows.values() if v['lev']]; off = [v for v in rows.values() if not v['lev']]
sf_on = np.mean([v['sf'] for v in on]); sf_off = np.mean([v['sf'] for v in off])
mu_all = np.mean([v['mu'] for v in rows.values()])
print(f"\n    level ON  ({len(on)} routes): mean shortfall {sf_on:+.4f}   (per-route "
      + ", ".join(f"{v['sf']:+.4f}" for v in on) + ")")
print(f"    level OFF ({len(off)} routes): mean shortfall {sf_off:+.4f}   (per-route "
      + ", ".join(f"{v['sf']:+.4f}" for v in off) + ")")
print(f"    the level moved the shortfall by {sf_on - sf_off:+.4f}")
print(f"    the MAP ARITHMETIC predicts       {-0.15*mu_all:+.4f}   (= -0.15 * mean unlevelled map {mu_all:.4f})")
print(f"    so the x1.15 level accounts for {100*abs(sf_on-sf_off)/max(sf_off,1e-9):.0f} % of the shortfall,")
print(f"    and {100*(1-abs(sf_on-sf_off)/max(sf_off,1e-9)):.0f} % of it survives the level.")
print(f"\n    LEVEL MULTIPLIER that would close the shortfall at 2-8 m/s:")
for v in rows.values():
    pass
need = 1.0 + sf_off / mu_all
print(f"      hold_meas / map_unlev = {np.mean([v['hold'] for v in rows.values()])/mu_all:.2f}"
      f"   -> level would have to be x{need:.2f}  (currently x1.15 on 6c/6d, x1.00 elsewhere)")
print("      the fork's record: x1.30 was chosen as 'deliberately short'; x1.50 failed on a 0.17 deg")
print("      ring at 26 m/s; a GLOBAL AccordEpsSpringScale 1.3 was falsified at 12 m/s (+0.91 step")
print("      overshoot) -- read from latcontrol_vehicle_tunes.py:248 and :266-272.")

print()
print("=" * 106)
print("(2) IS THE SHORTFALL THE SAME SHAPE ON EVERY ROUTE?  gap vs |angle|, per route")
ABINS = [(0.7, 1.2), (1.2, 2.0), (2.0, 3.2), (3.2, 5.0), (5.0, 8.0), (8.0, 40.0)]
print(f"    {'route':>22s} {'lev':>4s} " + " ".join(f"{a0:.1f}-{a1:.1f}".rjust(9) for a0, a1 in ABINS))
for rk in sorted(set(route[LOW])):
    rm = np.repeat((route == rk)[:, None], NF, 1)
    out = []
    for a0, a1 in ABINS:
        base = MOV & rm & (np.abs(aaW) >= a0) & (np.abs(aaW) < a1)
        mp = base & (np.sign(srW) == Sf); mn = base & (np.sign(srW) == -Sf)
        if mp.sum() < 40 or mn.sum() < 40:
            out.append('      ---'); continue
        a_ = np.median((cmdW * Sf)[mp]); t_ = np.median((cmdW * Sf)[mn])
        out.append(f"{(a_+t_)/2 - np.median(LEVM[base]):+9.4f}")
    print(f"    {rk:>22s} {int(D['lev'][rk]):4d} " + " ".join(out))
print("    (a MULTIPLICATIVE shortfall must grow with |angle| like the map; an ADDITIVE one must")
print("     rise to a plateau and stop)")

print()
print("=" * 106)
print("(3) ROUTE-CLUSTER CI on the shortfall in the 1.2-6 deg window (5 clusters)")
u = np.array(sorted(set(route[LOW]))); rng = np.random.default_rng(41); bs = []
for _ in range(4000):
    pick = rng.choice(u, len(u))
    vals = [rows[c]['sf'] for c in pick]
    bs.append(np.mean(vals))
print(f"    mean shortfall over routes {np.mean([rows[c]['sf'] for c in u]):+.4f}"
      f"  CI [{np.percentile(bs,2.5):+.4f},{np.percentile(bs,97.5):+.4f}]")
print(f"    mean fork levelled map in the same window {np.mean([rows[c]['ml'] for c in u]):+.4f}")
print(f"    => the fork's feedforward supplies "
      f"{100*np.mean([rows[c]['ml'] for c in u])/np.mean([rows[c]['hold'] for c in u]):.0f} % of the"
      f" command that actually holds the wheel there.")
