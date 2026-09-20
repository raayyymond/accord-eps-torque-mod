"""STEP 1  gate + channel census.
 (a) reproduce orch_crux_check GATE 0 through MY loader (nothing is trusted until this passes);
 (b) verify the command decomposition sums at the breakaway sample;
 (c) census the per-route FLOWN params that bear on this stream (level / observer / friction);
 (d) the CENTRE and HALF-WIDTH of the TOTAL and of EVERY CHANNEL, binned by |angle| exactly as
     the orchestrator did.  Means are used for the additive attribution (medians do not sum);
     medians are printed beside them as the robustness check.
"""
import numpy as np
from attr_lib import build, fit_lin, quintiles, bins, CHAN, BK, PRE, boot_ci

np.set_printoptions(linewidth=200)
D = build(); W, ar = D['W'], D['ar']
LOW = D['LOW']; sj = D['sjump']; tw = D['toward']; route = D['route']

print("=" * 100)
print("(a) GATE 0 -- reproduce ss_centring_fit / orch_crux_check through MY loader")
f0 = fit_lin(D, LOW, np.full(D['N'], BK))
exp = dict(away=0.052564, toward=0.014006, halfwidth=0.033285, centring_offset=0.019279, k=0.005560)
ok = True
for kk, want in exp.items():
    got = f0[kk]; good = abs(got - want) < 5e-5; ok &= good
    print(f"    {kk:16s} got {got:+.6f}  expected {want:+.6f}  d {got-want:+.2e}  {'OK' if good else '** MISMATCH **'}")
print(f"    n {int(LOW.sum())} (145)   n_toward {int(tw[LOW].sum())} (93)   k={f0['k']:.5f} c={f0['const']:+.5f}")
print(f"    GATE {'PASS' if ok else 'FAIL'}")
K, C = f0['k'], f0['const']

print()
print("=" * 100)
print("(b) DECOMPOSITION CHECK at the breakaway sample, LOW episodes")
tot = sum(W[c][ar, BK] for c in CHAN)
r = W['cmd'][ar, BK] - tot
print(f"    cmd - (hold_ff+move+z+rl+dob+P+I) : rms {np.sqrt(np.mean(r[LOW]**2)):.2e}  "
      f"max|.| {np.max(np.abs(r[LOW])):.2e}   (cmd rms {np.sqrt(np.mean(W['cmd'][ar,BK][LOW]**2)):.4f})")
rF = W['F'][ar, BK] - sum(W[c][ar, BK] for c in ('hold_ff', 'move', 'z', 'rl', 'dob'))
print(f"    F   - (hold_ff+move+z+rl+dob)     : rms {np.sqrt(np.mean(rF[LOW]**2)):.2e}  max {np.max(np.abs(rF[LOW])):.2e}")
print("    per-route z-model validation (from ss_extract): err_rms / err_p95 / corr")
for rk in sorted(set(route[LOW])):
    v = D['VAL'][rk]
    print(f"      {rk}  err_rms {v['err_rms']:.4f}  p95 {v['err_p95']:.4f}  corr {v['corr']:.3f}  z_rms {v['z_rms']:.4f}")
print(f"    n |sign(aa_pre)|==0 in LOW: {int((np.sign(D['aa_pre'])[LOW] == 0).sum())}")

print()
print("=" * 100)
print("(c) FLOWN PARAMS per LOW route, read from initData (stored by ss_extract into the npz)")
hdr = ('HoldLevel', 'HoldMap', 'DobHz', 'FrictionHyst', 'HystBand', 'SteerFriction', 'SteerKP',
       'TorqueKi', 'TorqueKiHigh', 'RateLoopGain', 'RefFilter', 'SpringScale', 'LatAccel')
key = ('AccordHoldLevel', 'AccordHoldMap', 'AccordDobHz', 'AccordFrictionHyst', 'AccordFrictionHystBand',
       'SteerFriction', 'SteerKP', 'AccordTorqueKi', 'AccordTorqueKiHigh', 'AccordRateLoopGain',
       'AccordRefFilter', 'AccordEpsSpringScale', 'SteerLatAccel')
print("    route                 grp  n  " + " ".join(f"{h:>13s}" for h in hdr))
for rk in sorted(set(route[LOW])):
    p = D['P'][rk]; g = D['group'][route == rk][0]; n = int((LOW & (route == rk)).sum())
    print(f"    {rk} {g:4s} {n:3d}  " + " ".join(f"{str(p.get(k,'--')):>13.13s}" for k in key))
print("    NOTE  AccordHoldLevel absent  => the fork commit predates the level (rev 4/5): level OFF.")
print("    NOTE  AccordDobHz absent/0    => observer returns 0 (f_hz<=0 resets it): observer OFF.")
print("    NOTE  the generic SteerFriction relay is gated OFF whenever AccordFrictionHyst>0")
print("          (latcontrol_torque.py: friction_torque = 0.0 if friction_hyst > 0.0), so the stock")
print("          0.212 on 6d/75 is INERT on these routes.  Verified by reading the branch.")
print(f"    level ON episodes {int(D['is_lev'][LOW].sum())} / OFF {int((~D['is_lev'])[LOW].sum())}"
      f"   |  observer ON {int(D['is_dob'][LOW].sum())} / OFF {int((~D['is_dob'])[LOW].sum())}")
print("    DOB fade = interp(v, [3,6], [0,1]) -> below 3 m/s the observer output is EXACTLY 0.")
vq = np.percentile(D['v'][LOW], [0, 10, 25, 50, 75, 90, 100])
print(f"    v in LOW, pct 0/10/25/50/75/90/100: " + " ".join(f"{x:.2f}" for x in vq))
fade = np.interp(D['v'][LOW], [3.0, 6.0], [0.0, 1.0])
print(f"    dob fade: median {np.median(fade):.2f}   frac at 0 {np.mean(fade==0):.2f}   frac at 1 {np.mean(fade==1):.2f}")

print()
print("=" * 100)
print("(d) CENTRE / HALF-WIDTH of the TOTAL and of EVERY CHANNEL, by |angle| quintile")
print("    y_X = X[bk-3]*sign(aa[bk]);  the linear spring+const reference is (k*aa+c)*sign(aa).")
print("    centre_X = (mean_away + mean_toward)/2 ;  halfwidth_X = (mean_away - mean_toward)/2")
print("    TOTAL row = cmd - k*aa - c  (identically the orchestrator's y).  Channels SUM to it.")
qs, aabs = quintiles(D)
S = np.sign(D['aa_pre'])
ych = {c: W[c][ar, BK] * S for c in CHAN}
ych['SPRINGREF'] = -(K * W['aa'][ar, BK] + C) * S      # the regressor that was removed
ych['TOTAL'] = (W['cmd'][ar, BK] - K * W['aa'][ar, BK] - C) * S
ref = dict(hold_aa_lev=D['hold_aa_lev'][ar, BK] * S, hold_ad_lev=D['hold_ad_lev'][ar, BK] * S,
           hold_aa_unlev=D['hold_aa_unlev'][ar, BK] * S)
order = ['TOTAL', 'SPRINGREF', 'hold_ff', 'P', 'I', 'dob', 'z', 'rl', 'move']

rows = []
for lo, hi, m in bins(D, LOW, qs, aabs):
    ma, mt = m & (tw == 0), m & (tw == 1)
    rows.append(dict(lo=lo, hi=hi, med_aa=np.median(aabs[m]), med_v=np.median(D['v'][m]),
                     na=int(ma.sum()), nt=int(mt.sum()), m=m, ma=ma, mt=mt))
print("\n    bin  |angle| range        med|aa|  med_v   n_aw n_tw")
for r_ in rows:
    print(f"    {r_['lo']:7.2f}-{r_['hi']:7.2f}  {r_['med_aa']:8.2f} {r_['med_v']:6.2f}  {r_['na']:4d} {r_['nt']:4d}")

for tag, agg in (('MEAN (additive)', np.mean), ('MEDIAN (robust)', np.median)):
    print(f"\n    ---- CENTRE by {tag} ----")
    print("    channel      " + "".join(f"{r_['med_aa']:>10.2f}d" for r_ in rows) + "     span   ratio")
    for c in order:
        vals = [(agg(ych[c][r_['ma']]) + agg(ych[c][r_['mt']])) / 2 for r_ in rows]
        sp = max(vals) - min(vals)
        print(f"    {c:12s} " + "".join(f"{x:+11.4f}" for x in vals) + f"  {sp:+8.4f}"
              f"  {max(vals)/max(min(vals),1e-9):7.1f}x")
    print("    -- reference curves (not channels): the fork's own map at this sample --")
    for c, x in ref.items():
        vals = [(agg(x[r_['ma']]) + agg(x[r_['mt']])) / 2 for r_ in rows]
        print(f"    {c:12s} " + "".join(f"{y:+11.4f}" for y in vals))
    print(f"\n    ---- HALF-WIDTH by {tag} ----")
    for c in order:
        vals = [(agg(ych[c][r_['ma']]) - agg(ych[c][r_['mt']])) / 2 for r_ in rows]
        sp = max(vals) - min(vals)
        print(f"    {c:12s} " + "".join(f"{x:+11.4f}" for x in vals) + f"  {sp:+8.4f}")

print()
print("=" * 100)
print("    CENTRE SUM CHECK (mean): channels must sum to TOTAL in every bin")
for r_ in rows:
    s = sum((np.mean(ych[c][r_['ma']]) + np.mean(ych[c][r_['mt']])) / 2 for c in list(CHAN) + ['SPRINGREF'])
    t = (np.mean(ych['TOTAL'][r_['ma']]) + np.mean(ych['TOTAL'][r_['mt']])) / 2
    print(f"      bin {r_['med_aa']:6.2f} deg   sum {s:+.6f}   TOTAL {t:+.6f}   d {s-t:+.1e}")

print()
print("=" * 100)
print("    PLANT READING.  At breakaway the wheel moves when |cmd - hold_plant(aa)| > F_static, so")
print("    (away+toward)/2 = hold_plant(aa) - (k*aa+c)  and (away-toward)/2 = F_static.  i.e. the")
print("    band CENTRE is a PLANT measurement of the static hold torque, read from the command.")
print("    hold_plant(aa) implied = centre + k*aa + c   vs the fork's levelled map at the same aa,v:")
print("\n      med|aa|  med_v   centre(med)   implied hold_plant    fork map lev   fork map unlev   ratio map/plant")
for r_ in rows:
    a_ = np.median(ych['TOTAL'][r_['ma']]); t_ = np.median(ych['TOTAL'][r_['mt']])
    ctr = (a_ + t_) / 2
    m = r_['m']
    kx = np.median((K * np.abs(W['aa'][ar, BK]) + C * S)[m])
    implied = ctr + kx
    fl = np.median(np.abs(D['hold_aa_lev'][ar, BK])[m]); fu = np.median(np.abs(D['hold_aa_unlev'][ar, BK])[m])
    print(f"      {r_['med_aa']:7.2f} {r_['med_v']:6.2f}   {ctr:+11.4f}   {implied:+17.4f}   {fl:+13.4f}   {fu:+14.4f}"
          f"   {fl/max(implied,1e-9):7.2f} / {fu/max(implied,1e-9):.2f}")
