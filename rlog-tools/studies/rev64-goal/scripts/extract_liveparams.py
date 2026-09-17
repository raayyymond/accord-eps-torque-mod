import sys, os, glob
sys.path.insert(0,'/home/user/accord-eps-torque-mod/rlog-tools/lib')
import numpy as np
from rlog_parse import read_messages
OUT='/home/user/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/tau'
for tag in sys.argv[1:]:
    segs=sorted(glob.glob(f'/home/user/accord-eps-torque-mod/analysis-2020accord/rlogs/'
                          f'75604b0a432fdc89_{tag}--*--rlog.zst'), key=lambda p:int(os.path.basename(p).split('--')[2]))
    A={k:[] for k in ('t_lp','roll','sR','stiff','aoff','t_lt','laf_f','lao_f','fric_f','lt_valid')}
    for p in segs:
        for evt in read_messages(p):
            try: w=evt.which()
            except Exception: continue
            t=evt.logMonoTime/1e9
            if w=='liveParameters':
                d=evt.liveParameters
                A['t_lp'].append(t); A['roll'].append(d.roll); A['sR'].append(d.steerRatio)
                A['stiff'].append(d.stiffnessFactor); A['aoff'].append(d.angleOffsetDeg)
            elif w=='liveTorqueParameters':
                d=evt.liveTorqueParameters
                A['t_lt'].append(t); A['laf_f'].append(d.latAccelFactorFiltered)
                A['lao_f'].append(d.latAccelOffsetFiltered); A['fric_f'].append(d.frictionCoefficientFiltered)
                A['lt_valid'].append(float(d.liveValid))
    D={k:np.array(v,dtype=np.float64) for k,v in A.items() if len(v)}
    f=os.path.join(OUT,f'r{tag[-2:]}_rev64_live.npz'); np.savez_compressed(f,**D)
    print(f'{tag}: liveParameters {len(D.get("t_lp",[]))}, liveTorqueParameters {len(D.get("t_lt",[]))} -> {os.path.basename(f)}')
    if 'roll' in D:
        print(f'   roll: p5={np.percentile(D["roll"],5):+.4f} p50={np.percentile(D["roll"],50):+.4f} '
              f'p95={np.percentile(D["roll"],95):+.4f} rad   (x g = {np.std(D["roll"])*9.81:.3f} m/s2 rms)')
        print(f'   steerRatio {np.median(D["sR"]):.3f}   stiffness {np.median(D["stiff"]):.3f}   '
              f'angleOffset {np.median(D["aoff"]):+.3f} deg')
    if 'lao_f' in D:
        print(f'   latAccelOffsetFiltered: median {np.median(D["lao_f"]):+.4f}  latAccelFactorFiltered {np.median(D["laf_f"]):.3f}')
