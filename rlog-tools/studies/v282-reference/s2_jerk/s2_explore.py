import numpy as np, sys
from s2_common import *
rows, tr = load_all()
G = lambda g: [r for r in rows if r['group'] in g]
keys = ['jerk','step','v','la_act.gain','la_pose.gain','act.slag','pose.slag','la_act.peak_ratio','la_pose.peak_ratio','la_act.jerk_rough','la_pose.jerk_rough','la_act.jerk_des_rms','act.d10','act.d50','act.d90','pose.d50','act.step_over','pose.step_over','act.settle','act.err_0_20','act.err_20_60','act.err_60_150','act.err_150_300','act.bias_0_20','act.bias_20_60','act.bias_60_150','act.bias_150_300','act.ring_pre','act.ring_post','sr_ring_pre','sr_ring_post','hf_2_10','sa_pk_rate','lat_delay']
for vb in range(4):
  print('=== vbin', VBINS[vb])
  for grp in (['V282'],['V282old'],['T64'],['T64B'],['T5'],['T4']):
    R=[r for r in G(grp) if r['vb']==vb]
    print(f"{grp[0]:8s} n={len(R):3d} ", ' '.join(f"{k[:14]}={np.nanmedian([r.get(k,np.nan) for r in R]) if R else np.nan:.3g}" for k in keys))
