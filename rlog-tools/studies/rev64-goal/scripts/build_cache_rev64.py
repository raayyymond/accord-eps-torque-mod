"""Extract the rev 6.4 routes (0000006c, 0000006d) into the SAME npz schema as the
existing r76_v293_ident cache, so every analysis script works unchanged.
"""
import sys, os, glob
sys.path.insert(0, '/home/user/accord-eps-torque-mod/rlog-tools/lib')
import numpy as np
from rlog_parse import read_messages

OUT = '/home/user/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/tau'
os.makedirs(OUT, exist_ok=True)

def seg_key(p):
    b = os.path.basename(p)
    return int(b.split('--')[2])

def extract(route_tag):
    segs = sorted(glob.glob(f'/home/user/accord-eps-torque-mod/analysis-2020accord/rlogs/'
                            f'75604b0a432fdc89_{route_tag}--*--rlog.zst'), key=seg_key)
    print(f'{route_tag}: {len(segs)} segments', flush=True)
    A = {k: [] for k in
         ['t_cs','cs_active','cs_err','cs_p','cs_i','cs_f','cs_out','cs_sat','cs_la_act','cs_la_des',
          'cs_la_jerk','cs_des_curv','cs_curv','cs_errrate',
          't_cst','vego','aego','sa_deg','sr_deg','spress','storque','storque_eps','cs_yaw','sa_off',
          't_cc','lat_active','cc_enabled','cc_curv_cmd','cc_torque','cc_tq_can','cc_curv_now',
          't_ld','ld_delay','ld_est','ld_std']}
    for p in segs:
        n = 0
        for evt in read_messages(p):
            try: w = evt.which()
            except Exception: continue
            t = evt.logMonoTime / 1e9
            if w == 'controlsState':
                cs = evt.controlsState
                try: ts = cs.lateralControlState.torqueState
                except Exception: continue
                A['t_cs'].append(t); A['cs_active'].append(float(ts.active))
                A['cs_err'].append(ts.error); A['cs_p'].append(ts.p); A['cs_i'].append(ts.i)
                A['cs_f'].append(ts.f); A['cs_out'].append(ts.output); A['cs_sat'].append(float(ts.saturated))
                A['cs_la_act'].append(ts.actualLateralAccel); A['cs_la_des'].append(ts.desiredLateralAccel)
                A['cs_la_jerk'].append(ts.desiredLateralJerk); A['cs_errrate'].append(ts.errorRate)
                A['cs_des_curv'].append(cs.desiredCurvature); A['cs_curv'].append(cs.curvature)
            elif w == 'carState':
                c = evt.carState
                A['t_cst'].append(t); A['vego'].append(c.vEgo); A['aego'].append(c.aEgo)
                A['sa_deg'].append(c.steeringAngleDeg); A['sr_deg'].append(c.steeringRateDeg)
                A['spress'].append(float(c.steeringPressed)); A['storque'].append(c.steeringTorque)
                A['storque_eps'].append(c.steeringTorqueEps); A['cs_yaw'].append(c.yawRate)
                A['sa_off'].append(c.steeringAngleOffsetDeg)
            elif w == 'carControl':
                cc = evt.carControl
                A['t_cc'].append(t); A['lat_active'].append(float(cc.latActive))
                A['cc_enabled'].append(float(cc.enabled)); A['cc_curv_now'].append(cc.currentCurvature)
                a = cc.actuators
                A['cc_curv_cmd'].append(a.curvature); A['cc_torque'].append(a.torque)
                A['cc_tq_can'].append(a.torqueOutputCan)
            elif w == 'liveDelay':
                try:
                    ld = evt.liveDelay
                    A['t_ld'].append(t); A['ld_delay'].append(ld.lateralDelay)
                    A['ld_est'].append(ld.lateralDelayEstimate); A['ld_std'].append(ld.lateralDelayEstimateStd)
                except Exception: pass
            n += 1
        print(f'   {os.path.basename(p)}  {n} msgs  cs={len(A["t_cs"])}', flush=True)
    D = {k: np.array(v, dtype=np.float64) for k, v in A.items() if len(v)}
    f = os.path.join(OUT, f'r{route_tag[-2:]}_rev64_ident.npz')
    np.savez_compressed(f, **D)
    print(f'   -> {f}  ({os.path.getsize(f)/1e6:.1f} MB)', flush=True)
    for k in ('t_cs','t_cst','t_cc'):
        if k in D: print(f'      {k}: {len(D[k])} samples, {D[k][-1]-D[k][0]:.0f} s span', flush=True)

for tag in sys.argv[1:]:
    extract(tag)
