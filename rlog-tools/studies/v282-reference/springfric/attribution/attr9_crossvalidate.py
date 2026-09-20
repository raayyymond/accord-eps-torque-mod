"""STEP 9  final crux check: do the TWO INDEPENDENT estimators of the plant hold agree?
  estimator 1 (episode band):  hold = CENTRE(|aa|) + k*|aa| + c-term,  from 145 breakaway episodes
  estimator 2 (frame read):    hold = (cmd|rate>0 + cmd|rate<0)/2 * sign(aa), from ~34k hands-off frames
They share no arithmetic: different samples, different direction variable (jump vs measured rate),
one uses the fit's k and c, the other uses neither.
"""
import numpy as np
from attr_lib import build, fit_lin, quintiles, bins, BK, PRE
D = build(); W, ar = D['W'], D['ar']; LOW = D['LOW']; tw = D['toward']; route = D['route']
f0 = fit_lin(D, LOW, np.full(D['N'], BK)); K, C = f0['k'], f0['const']
S = np.sign(D['aa_pre']); aabs = np.abs(D['aa_pre'])
Y = (W['cmd'][ar, BK] - K * W['aa'][ar, BK] - C) * S
aaW, srW, vW, cmdW = W['aa'], W['sr'], W['v'], W['cmd']; NF = aaW.shape[1]
rmask = np.isin(D['group'], ['T64','T64B','T5','T4'])
FM = np.repeat(rmask[:,None],NF,1) & (vW>=2) & (vW<8); Sf = np.sign(aaW); MOV = FM & (np.abs(srW)>3)
qs,_ = quintiles(D)
print(f"{'med|aa|':>8s} {'n_ep':>5s} {'band CENTRE':>12s} {'+k|aa|+c':>10s} {'= band hold':>12s} "
      f"{'frame hold':>11s} {'n_frames':>9s} {'diff':>9s}")
for lo,hi,m in bins(D, LOW, qs, aabs):
    ma,mt = m&(tw==0), m&(tw==1)
    ctr = (np.median(Y[ma])+np.median(Y[mt]))/2
    a_ = np.median(aabs[m])
    # add back exactly what the fit removed, in the S frame: (k*aa + c)*S = k|aa| + c*S
    back = np.median((K*np.abs(W['aa'][ar,BK]) + C*S)[m])
    b = MOV & (vW>=2)&(vW<8) & (np.abs(aaW)>=lo) & (np.abs(aaW)<(hi if hi<39 else 1e9))
    mp = b&(np.sign(srW)==Sf); mn = b&(np.sign(srW)==-Sf)
    fh = (np.median((cmdW*Sf)[mp])+np.median((cmdW*Sf)[mn]))/2 if (mp.sum()>80 and mn.sum()>80) else np.nan
    print(f"{a_:8.2f} {int(m.sum()):5d} {ctr:+12.4f} {back:+10.4f} {ctr+back:+12.4f} {fh:+11.4f} "
          f"{int(mp.sum()+mn.sum()):9d} {fh-(ctr+back):+9.4f}")
print("\nCoulomb cross-check (independent direction variables):")
print(f"  band half-width (jump direction)        {f0['halfwidth']:+.4f}")
fs=[]
for lo,hi,m in bins(D, LOW, qs, aabs):
    b = MOV & (np.abs(aaW)>=lo) & (np.abs(aaW)<(hi if hi<39 else 1e9))
    mp=b&(np.sign(srW)==Sf); mn=b&(np.sign(srW)==-Sf)
    if mp.sum()>80 and mn.sum()>80:
        fs.append((np.median((cmdW*Sf)[mp])-np.median((cmdW*Sf)[mn]))/2)
print(f"  frame read F (measured rate direction)  {np.median(fs):+.4f}   per bin " + " ".join(f"{x:+.4f}" for x in fs))
