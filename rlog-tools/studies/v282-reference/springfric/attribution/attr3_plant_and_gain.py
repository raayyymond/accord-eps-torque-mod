"""STEP 3  is the CENTRE a plant property at all, and does a free gain on the fork's NONLINEAR
hold map absorb it?

 (a) LEFT/RIGHT SPLIT of the band centre.  y = (...)*sign(aa), so a CONSTANT command bias b times an
     imbalanced left/right composition manufactures a centre out of nothing: it enters as (b-c)*sign(aa)
     and flips with the turn direction.  A genuine odd-in-angle plant term does NOT flip.
 (b) INDEPENDENT read of the plant's static hold torque, NOT through the band fit.  On frames where
     the wheel is MOVING steadily the Coulomb term is saturated at F*sign(rate), so
         (cmd | rate>0  +  cmd | rate<0) / 2  =  hold_plant(angle)     [F cancels]
         (cmd | rate>0  -  cmd | rate<0) / 2  =  F_coulomb
     computed per (|angle|, v) cell over EVERY window frame (all inside a hands-off run), against the
     fork's own levelled map.  This is the same experiment the map was fitted from and uses neither
     the fit's k nor its c.
 (c) FREE GAIN on the fork's nonlinear hold map in place of the linear k*aa regressor, at the
     breakaway sample, with route-cluster and episode bootstrap CIs -- and the CENTRE PROFILE under
     that regressor (hypothesis C: if it flattens, the centre was a regressor misfit).
 (d) the channel attribution re-referenced to hold_lev(aa) instead of k*aa.
"""
import numpy as np
from attr_lib import build, fit_lin, fit_hold, quintiles, bins, CHAN, BK, PRE, boot_ci, boot_ci_ev

D = build(); W, ar = D['W'], D['ar']
LOW = D['LOW']; sj = D['sjump']; tw = D['toward']; route = D['route']
f0 = fit_lin(D, LOW, np.full(D['N'], BK)); K, C = f0['k'], f0['const']
S = np.sign(D['aa_pre']); aabs = np.abs(D['aa_pre'])
Y = (W['cmd'][ar, BK] - K * W['aa'][ar, BK] - C) * S
cells = [(0.0, 0.6), (0.6, 1.5), (1.5, 3.0), (3.0, 1e9)]


def ch(y, m, agg=np.median):
    ma, mt = m & (tw == 0), m & (tw == 1)
    if ma.sum() < 3 or mt.sum() < 3:
        return None
    a_, t_ = agg(y[ma]), agg(y[mt])
    return (a_ + t_) / 2, (a_ - t_) / 2, int(ma.sum()), int(mt.sum())


print("=" * 104)
print("(a) LEFT vs RIGHT.  If the centre is a constant command bias x an imbalanced sign(aa)")
print("    composition it FLIPS between left and right; a real odd-in-angle term does not.")
print(f"\n    {'|aa| cell':>13s} {'nL':>4s} {'nR':>4s} {'ctr LEFT':>10s} {'ctr RIGHT':>10s} {'BOTH':>9s}"
      f" {'HW L':>8s} {'HW R':>8s}")
for lo, hi in cells:
    m = LOW & (aabs >= lo) & (aabs < hi)
    rl_, rr_ = ch(Y, m & (S > 0)), ch(Y, m & (S < 0)); rb = ch(Y, m)
    f = lambda r, i: f"{r[i]:+.4f}" if r else "   n/a"
    print(f"    {lo:5.2f}-{hi:6.2f} {int((m&(S>0)).sum()):4d} {int((m&(S<0)).sum()):4d}"
          f" {f(rl_,0):>10s} {f(rr_,0):>10s} {f(rb,0):>9s} {f(rl_,1):>8s} {f(rr_,1):>8s}")
print(f"\n    overall sign(aa) balance in LOW: left {int((S[LOW]>0).sum())}  right {int((S[LOW]<0).sum())}")
print("    raw-frame constant check: median(cmd - k*aa) by turn side, all LOW episodes --")
raw = W['cmd'][ar, BK] - K * W['aa'][ar, BK]
for nm, m in (('LEFT (aa>0)', LOW & (S > 0)), ('RIGHT (aa<0)', LOW & (S < 0))):
    e, ci = boot_ci_ev(raw[m])
    print(f"      {nm:14s} n={int(m.sum()):3d}  median {e:+.4f}  CI [{ci[0]:+.4f},{ci[1]:+.4f}]")

print()
print("=" * 104)
print("(b) INDEPENDENT PLANT-HOLD READ from MOVING window frames (no band fit, no k, no c)")
aaW, srW, vW, cmdW = W['aa'], W['sr'], W['v'], W['cmd']
# frame-level masks: torque routes, 2-8 m/s, moving steadily
rmask = np.isin(D['group'], ['T64', 'T64B', 'T5', 'T4'])
FM = np.repeat(rmask[:, None], aaW.shape[1], 1) & (vW >= 2) & (vW < 8)
print(f"    torque-route window frames at 2-8 m/s: {int(FM.sum()):,}")
# sign convention check: after breakaway the measured rate must agree with the jump direction
post = np.zeros_like(FM); post[:, PRE + 5:PRE + 40] = True
mm = post & FM & (np.abs(srW) > 2)
agree = np.mean(np.sign(srW[mm]) == np.repeat(sj[:, None], aaW.shape[1], 1)[mm])
print(f"    sign(sr) == sjump on post-breakaway moving frames: {agree:.3f}  (must be ~1: same frame)")
RTH = 3.0
lv = np.array([1.15 if D['lev'][r] else 1.0 for r in route])[:, None] * np.ones_like(aaW)
abins = [(0.3, 0.8), (0.8, 1.5), (1.5, 3.0), (3.0, 6.0), (6.0, 12.0), (12.0, 30.0)]
vbins = [(2, 4), (4, 6), (6, 8)]
print(f"\n    moving frames: |sr| > {RTH} deg/s.  cell = (|angle|, v).  hold = (m+ + m-)/2*sign(aa), F = (m+ - m-)/2*sign(aa)")
print(f"    {'v':>7s} {'|aa|':>11s} {'n+':>6s} {'n-':>6s} {'hold_meas':>10s} {'F_meas':>9s}"
      f" {'fork lev':>9s} {'fork unlev':>11s} {'meas/lev':>9s}")
tot = []
for v0, v1 in vbins:
    for a0, a1 in abins:
        base = FM & (vW >= v0) & (vW < v1) & (np.abs(aaW) >= a0) & (np.abs(aaW) < a1) & (np.abs(srW) > RTH)
        Sf = np.sign(aaW)
        mp = base & (np.sign(srW) == Sf)      # moving AWAY from centre
        mn = base & (np.sign(srW) == -Sf)     # moving TOWARD centre
        if mp.sum() < 200 or mn.sum() < 200:
            continue
        a_ = np.median((cmdW * Sf)[mp]); t_ = np.median((cmdW * Sf)[mn])
        hold = (a_ + t_) / 2; F = (a_ - t_) / 2
        kk = np.median((np.abs(D['hold_aa_lev']) )[base]); ku = np.median((np.abs(D['hold_aa_unlev']))[base])
        tot.append((v0, v1, a0, a1, hold, F, kk, ku, int(mp.sum()), int(mn.sum())))
        print(f"    {v0}-{v1:<4d} {a0:5.1f}-{a1:5.1f} {int(mp.sum()):6d} {int(mn.sum()):6d} {hold:+10.4f}"
              f" {F:+9.4f} {kk:+9.4f} {ku:+11.4f} {hold/max(kk,1e-9):9.2f}")
print("\n    NOTE this read is EVEN in sign(aa) by construction and averages over the same")
print("    populations on both legs, so it cannot be faked by a constant bias.")
# the same read restricted to NEAR-STILL frames, the condition the fork's map was fitted under
print(f"\n    same cells, NEAR-STILL frames (0.5 < |sr| <= 3 deg/s), which is closer to the map's own fit:")
print(f"    {'v':>7s} {'|aa|':>11s} {'n+':>6s} {'n-':>6s} {'hold_meas':>10s} {'F_meas':>9s} {'fork lev':>9s} {'meas/lev':>9s}")
for v0, v1 in vbins:
    for a0, a1 in abins:
        base = FM & (vW >= v0) & (vW < v1) & (np.abs(aaW) >= a0) & (np.abs(aaW) < a1) & (np.abs(srW) > 0.5) & (np.abs(srW) <= RTH)
        Sf = np.sign(aaW)
        mp = base & (np.sign(srW) == Sf); mn = base & (np.sign(srW) == -Sf)
        if mp.sum() < 200 or mn.sum() < 200:
            continue
        a_ = np.median((cmdW * Sf)[mp]); t_ = np.median((cmdW * Sf)[mn])
        kk = np.median(np.abs(D['hold_aa_lev'])[base])
        print(f"    {v0}-{v1:<4d} {a0:5.1f}-{a1:5.1f} {int(mp.sum()):6d} {int(mn.sum()):6d} {(a_+t_)/2:+10.4f}"
              f" {(a_-t_)/2:+9.4f} {kk:+9.4f} {((a_+t_)/2)/max(kk,1e-9):9.2f}")

print()
print("=" * 104)
print("(c) FREE GAIN on the fork's NONLINEAR hold map, band fit at breakaway")
idx = np.full(D['N'], BK)
for hch, nm in (('hold_aa_lev', 'hold(aa) LEVELLED per route'), ('hold_aa_unlev', 'hold(aa) unlevelled'),
                ('hold_ad_lev', 'hold(angdes) levelled')):
    f = fit_hold(D, LOW, idx, hch)
    # route-cluster bootstrap on G
    u = np.unique(route[LOW]); rng = np.random.default_rng(11); bs = []
    ii0 = {c: np.where(LOW & (route == c))[0] for c in u}
    X0 = np.vstack([D[hch][ar, BK], sj, sj * tw, np.ones(D['N'])]).T; y0 = W['cmd'][ar, BK]
    for _ in range(2000):
        ii = np.concatenate([ii0[c] for c in rng.choice(u, len(u))])
        bs.append(np.linalg.lstsq(X0[ii], y0[ii], rcond=None)[0])
    bs = np.array(bs)
    rng2 = np.random.default_rng(12); iiL = np.where(LOW)[0]; bs2 = []
    for _ in range(2000):
        ii = rng2.choice(iiL, len(iiL))
        bs2.append(np.linalg.lstsq(X0[ii], y0[ii], rcond=None)[0])
    bs2 = np.array(bs2)
    print(f"\n    regressor = {nm}")
    print(f"      G (free gain on the map) {f['G']:+.4f}   route-cluster CI [{np.percentile(bs[:,0],2.5):+.4f},"
          f"{np.percentile(bs[:,0],97.5):+.4f}]   episode CI [{np.percentile(bs2[:,0],2.5):+.4f},{np.percentile(bs2[:,0],97.5):+.4f}]")
    print(f"      away {f['away']:+.4f}  toward {f['toward']:+.4f}  HALFWIDTH {f['halfwidth']:+.4f}"
          f"  CENTRING_OFFSET {f['centring_offset']:+.4f}  const {f['const']:+.4f}")
    print(f"      centring_offset route-cluster CI [{np.percentile(-bs[:,2]/2,2.5):+.4f},{np.percentile(-bs[:,2]/2,97.5):+.4f}]")
    # the CENTRE PROFILE under this regressor
    Yh = (W['cmd'][ar, BK] - f['G'] * D[hch][ar, BK] - f['const']) * S
    qs, _ = quintiles(D)
    prof = []
    for lo, hi, m in bins(D, LOW, qs, aabs):
        r = ch(Yh, m)
        prof.append((np.median(aabs[m]), r[0] if r else np.nan, r[1] if r else np.nan))
    print("      CENTRE profile under this regressor:  " + "  ".join(f"{a:.2f}d {c:+.4f}" for a, c, _ in prof))
    print("      HALFWID profile under this regressor: " + "  ".join(f"{a:.2f}d {h:+.4f}" for a, _, h in prof))
    cs = np.array([c for _, c, _ in prof])
    print(f"      centre span {cs.max()-cs.min():+.4f}  (linear-k reference span +0.0340)")

print()
print("=" * 104)
print("(d) CHANNEL ATTRIBUTION re-referenced to the fork's levelled hold(aa) instead of k*aa.")
print("    DEFICIT(|aa|) = centre of [cmd - hold_lev(aa)] = what the FF at the ACTUAL angle does not cover.")
qs, _ = quintiles(D)
H = D['hold_aa_lev'][ar, BK]
ych = {c: W[c][ar, BK] * S for c in CHAN}
ych['DEFICIT'] = (W['cmd'][ar, BK] - H) * S
ych['hold_ff_minus_hold_aa'] = (W['hold_ff'][ar, BK] - H) * S
ych['slow'] = (W['I'][ar, BK] + W['dob'][ar, BK]) * S
order = ['DEFICIT', 'hold_ff_minus_hold_aa', 'P', 'I', 'dob', 'slow', 'z', 'rl', 'move']
rows = [(lo, hi, m) for lo, hi, m in bins(D, LOW, qs, aabs)]
print("\n    channel                      " + "".join(f"{np.median(aabs[m]):>10.2f}d" for _, _, m in rows))
for c in order:
    vals = [ch(ych[c], m)[0] for _, _, m in rows]
    print(f"    {c:28s} " + "".join(f"{x:+11.4f}" for x in vals))
print("\n    (DEFICIT = hold_ff_minus_hold_aa + P + I + dob + z + rl + move, by construction;")
print("     medians do not add exactly -- the mean version is in attr1)")
for _, _, m in rows:
    s = sum(np.mean(ych[c][m & (tw == 0)]) + np.mean(ych[c][m & (tw == 1)]) for c in
            ['hold_ff_minus_hold_aa', 'P', 'I', 'dob', 'z', 'rl', 'move']) / 2
    t = (np.mean(ych['DEFICIT'][m & (tw == 0)]) + np.mean(ych['DEFICIT'][m & (tw == 1)])) / 2
    print(f"      mean sum check  {s:+.5f} vs DEFICIT {t:+.5f}   d {s-t:+.1e}")
