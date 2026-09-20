"""STEP 7  close the last leak (J*acc), then the final attribution with fractions and residual.
 (a) inertial leak census on the direction-averaged read.
 (b) the OUTWARD medians the orchestrator asked for: I, dob, hold_ff and the CENTRE on one axis.
 (c) final attribution: fraction of the centre / of the deficit each channel owns, and the residual.
 (d) the summary numbers for the report.
"""
import numpy as np
from attr_lib import build, fit_lin, fit_hold, quintiles, bins, BK, PRE, CHAN, boot_ci, boot_ci_ev
from sslib import G_BP, G_V, HOLD_SAT

D = build(); W, ar = D['W'], D['ar']
LOW = D['LOW']; route = D['route']; tw = D['toward']; sj = D['sjump']
aaW, srW, vW, cmdW = W['aa'], W['sr'], W['v'], W['cmd']
NF = aaW.shape[1]
rmask = np.isin(D['group'], ['T64', 'T64B', 'T5', 'T4'])
FM = np.repeat(rmask[:, None], NF, 1) & (vW >= 2) & (vW < 8)
Sf = np.sign(aaW); MOV = FM & (np.abs(srW) > 3.0)
MAPL = np.abs(D['hold_aa_lev'])
J = 8e-5
acc = np.zeros_like(srW); acc[:, 1:-1] = (srW[:, 2:] - srW[:, :-2]) / 0.02

print("=" * 108)
print("(a) INERTIAL LEAK.  J = 8e-5 torque/(deg/s^2).  J*acc cancels in the direction average only")
print("    if the two legs have the same median acceleration.  Census:")
print(f"    {'v':>7s} {'|aa|':>11s} {'acc_aw':>9s} {'acc_tw':>9s} {'J*asym/2':>10s} {'GAP':>9s} {'leak/GAP':>9s}")
ABINS = [(0.3, 0.7), (0.7, 1.2), (1.2, 2.0), (2.0, 3.2), (3.2, 5.0), (5.0, 8.0), (13.0, 40.0)]
for v0, v1 in ((4, 6), (6, 8)):
    for a0, a1 in ABINS:
        base = MOV & (vW >= v0) & (vW < v1) & (np.abs(aaW) >= a0) & (np.abs(aaW) < a1)
        mp = base & (np.sign(srW) == Sf); mn = base & (np.sign(srW) == -Sf)
        if mp.sum() < 120 or mn.sum() < 120:
            continue
        ap = np.median((acc * Sf)[mp]); an = np.median((acc * Sf)[mn])
        a_ = np.median((cmdW * Sf)[mp]); t_ = np.median((cmdW * Sf)[mn])
        gap = (a_ + t_) / 2 - np.median(MAPL[base])
        leak = J * (ap + an) / 2
        print(f"    {v0}-{v1:<4d} {a0:5.1f}-{a1:5.1f} {ap:+9.1f} {an:+9.1f} {leak:+10.4f} {gap:+9.4f}"
              f" {leak/gap:9.3f}")
print("    (acc is in the +away-from-centre sense; the leak column is what survives the average)")

print()
print("=" * 108)
print("(b) OUTWARD (away-leg) MEDIANS by |aa| quintile -- the three profiles on one axis")
f0 = fit_lin(D, LOW, np.full(D['N'], BK)); K, C = f0['k'], f0['const']
S = np.sign(D['aa_pre']); aabs = np.abs(D['aa_pre'])
Y = (W['cmd'][ar, BK] - K * W['aa'][ar, BK] - C) * S
qs, _ = quintiles(D)
Ych = dict(CENTRE=Y, I=W['I'][ar, BK] * S, dob=W['dob'][ar, BK] * S, P=W['P'][ar, BK] * S,
           hold_ff=W['hold_ff'][ar, BK] * S, z=W['z'][ar, BK] * S,
           hold_ff_net=(W['hold_ff'][ar, BK] - K * W['aa'][ar, BK] - C) * S,
           slow=(W['I'][ar, BK] + W['dob'][ar, BK]) * S)
rows = [(np.median(aabs[m]), m) for _, _, m in bins(D, LOW, qs, aabs)]
print("    quantity          " + "".join(f"{a:>11.2f}d" for a, _ in rows) + "    slope_wrt_|aa|  rise/CENTRE rise")
cr = None
for nm in ('CENTRE', 'I', 'dob', 'slow', 'P', 'hold_ff_net', 'z'):
    aw = [np.median(Ych[nm][m & (tw == 0)]) for _, m in rows]
    tws = [np.median(Ych[nm][m & (tw == 1)]) for _, m in rows]
    ctr = [(a + b) / 2 for a, b in zip(aw, tws)]
    rise = ctr[-1] - ctr[0]
    if nm == 'CENTRE':
        cr = rise
    sl = np.polyfit(np.log(np.array([a for a, _ in rows])), ctr, 1)[0]
    print(f"    {nm:12s} AWAY " + "".join(f"{x:+12.4f}" for x in aw))
    print(f"    {'':12s} ctr  " + "".join(f"{x:+12.4f}" for x in ctr) + f"   {sl:+14.4f} {rise/cr:17.2f}")
print("\n    'rise' = bin5 centre - bin1 centre.  An INTEGRATOR explanation requires I (or dob) to")
print("    carry the rise; a FEEDFORWARD explanation requires hold_ff_net to carry it.")

print()
print("=" * 108)
print("(c) FINAL ATTRIBUTION.  Two references, both reported.")
H = D['hold_aa_lev'][ar, BK]
DEF = (W['cmd'][ar, BK] - H) * S       # what the FF at the ACTUAL angle does not cover


def ctr_(y, m):
    ma, mt = m & (tw == 0), m & (tw == 1)
    if ma.sum() < 3 or mt.sum() < 3:
        return np.nan
    return (np.median(y[ma]) + np.median(y[mt])) / 2


for tag, TOT in (('CENTRE  (cmd - k*aa - c, the orchestrator quantity)', Y),
                 ("DEFICIT (cmd - fork's levelled hold map at the ACTUAL angle)", DEF)):
    print(f"\n    ---- {tag} ----")
    print(f"    {'|aa| band':>12s} {'n':>4s} {'TOTAL':>9s} " + " ".join(f"{c:>9s}" for c in
          ('hold_ff*', 'P', 'I', 'dob', 'slow', 'z', 'rl', 'move')) + "   resid")
    for a, m in rows:
        t = ctr_(TOT, m)
        hf = ctr_((W['hold_ff'][ar, BK] - (K * W['aa'][ar, BK] + C if tag[0] == 'C' else H)) * S, m)
        parts = [hf] + [ctr_(W[c][ar, BK] * S, m) for c in ('P', 'I', 'dob')]
        slow = ctr_((W['I'][ar, BK] + W['dob'][ar, BK]) * S, m)
        rest = [ctr_(W[c][ar, BK] * S, m) for c in ('z', 'rl', 'move')]
        s = hf + parts[1] + parts[2] + parts[3] + sum(rest)
        print(f"    {a:11.2f}d {int(m.sum()):4d} {t:+9.4f} " +
              " ".join(f"{x:+9.4f}" for x in parts + [slow] + rest) + f" {t-s:+9.4f}")
    print(f"    FRACTIONS above |aa| = 0.6 deg (pooled, n={int((LOW&(aabs>0.6)).sum())}):")
    m = LOW & (aabs > 0.6)
    t = ctr_(TOT, m)
    hf = ctr_((W['hold_ff'][ar, BK] - (K * W['aa'][ar, BK] + C if tag[0] == 'C' else H)) * S, m)
    for nm, y in (('hold_ff*', hf), ('P', ctr_(W['P'][ar, BK] * S, m)), ('I', ctr_(W['I'][ar, BK] * S, m)),
                  ('dob', ctr_(W['dob'][ar, BK] * S, m)),
                  ('I+dob (slow)', ctr_((W['I'][ar, BK] + W['dob'][ar, BK]) * S, m)),
                  ('z', ctr_(W['z'][ar, BK] * S, m)), ('rl', ctr_(W['rl'][ar, BK] * S, m)),
                  ('move', ctr_(W['move'][ar, BK] * S, m))):
        print(f"      {nm:14s} {y:+.4f}   {100*y/t:+6.1f} % of {t:+.4f}")
    e, ci = boot_ci(TOT[m & (tw == 0)], route[m & (tw == 0)])
    e2, ci2 = boot_ci(TOT[m & (tw == 1)], route[m & (tw == 1)])
    print(f"      TOTAL centre route-cluster CI: [{(ci[0]+ci2[0])/2:+.4f},{(ci[1]+ci2[1])/2:+.4f}]  point {t:+.4f}")
    sm = LOW & (aabs > 0.6)
    e3, ci3 = boot_ci_ev((W['I'][ar, BK] + W['dob'][ar, BK])[sm & (tw == 0)] * S[sm & (tw == 0)])
    e4, ci4 = boot_ci_ev((W['I'][ar, BK] + W['dob'][ar, BK])[sm & (tw == 1)] * S[sm & (tw == 1)])
    print(f"      slow (I+dob) episode-bootstrap CI: [{(ci3[0]+ci4[0])/2:+.4f},{(ci3[1]+ci4[1])/2:+.4f}]")

print()
print("=" * 108)
print("(d) SUMMARY NUMBERS")
print(f"    band fit, torque|2-8|breakaway: away {f0['away']:+.4f} toward {f0['toward']:+.4f}"
      f" halfwidth {f0['halfwidth']:+.4f} centring_offset {f0['centring_offset']:+.4f} k {f0['k']:.5f}")
fh = fit_hold(D, LOW, np.full(D['N'], BK), 'hold_aa_lev')
print(f"    free gain on the fork's levelled NONLINEAR hold map: G {fh['G']:+.4f}"
      f"  centring_offset after it {fh['centring_offset']:+.4f} (was {f0['centring_offset']:+.4f})"
      f"  halfwidth {fh['halfwidth']:+.4f}")
print(f"    the centre profile does NOT flatten under the nonlinear map -> hypothesis (C) falsified")
print(f"    independent plant read (no band fit): map gain G 1.145 [0.86,1.69], intercept A +0.0215 [+0.0173,+0.0309]")
print(f"    gain-only (pure stiffness) model: G 1.73 [1.27,2.75] with 1.9x the weighted residual")
print(f"    fork constants: HOLD_STATIC_FRICTION 0.020 (the intercept the map was fitted WITHOUT);"
      f" flown AccordFrictionHyst 0.015")
print(f"    Coulomb F: band half-width {f0['halfwidth']:.4f}; independent read median 0.0385")
zhw = []
for a, m in rows:
    ma, mt = m & (tw == 0), m & (tw == 1)
    zhw.append((np.median((W['z'][ar, BK] * S)[ma]) - np.median((W['z'][ar, BK] * S)[mt])) / 2)
print("      z's contribution to the half-width by bin: " + " ".join(f"{x:+.4f}" for x in zhw)
      + f"  (of a total {f0['halfwidth']:.4f})")
