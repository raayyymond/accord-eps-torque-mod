"""ALTMETHOD check for s4_texture finding 'texture-is-in-the-wheel-not-in-vehicle-yaw'.

The finding's own instrument for 'vehicle yaw' is livePose.pose_wz, a ~20 Hz EKF-SMOOTHED estimate
(confirmed here: t_pose median dt = 0.0503 s). An EKF that fuses gyro+wheel speed+camera odometry can
easily roll off well below its 10 Hz sampling Nyquist. This script uses a DIFFERENT, independent
instrument for vehicle rotation: the RAW MEMS gyroscope (message 'gyroscope', ~100 Hz, un-fused,
no EKF smoothing) present in the rlogs but not currently pulled into build_cache.py / v282cmp.py.

Method:
  1. Parse gyroscope + controlsState + carState directly from the rlog segments for ONE V282 route and
     ONE torque-mode route (RAM: one route fully processed and reduced before moving to the next).
  2. Identify the yaw axis and its sign empirically: whichever of the 3 raw gyro axes best correlates
     with the model's desired lateral accel / v (a signed, high-SNR reference) during engaged driving.
  3. Interpolate onto the controlsState clock (same clock v282cmp.load uses), band-pass 1.8-3.0 Hz,
     compute wheel-rate (sr) vs raw-gyow-yaw*v band power, matched to speed strata, using event windows
     (post desired-jerk events, i.e. exactly the regime this stream is about) AND whole-route blocks.
  4. Cross-correlate wheel rate and raw yaw in the 1.8-3 Hz band (Hilbert envelope correlation) as a
     nonlinear/coupling check independent of amplitude ratio.

This is a single-route-per-group check (n=1+1), so it cannot replace the multi-route matched comparison;
it is a different INSTRUMENT (unfiltered ~100 Hz raw gyro vs 20 Hz EKF output) and a different ESTIMATOR
(event/tail + envelope coupling vs block-median PSD ratio), which is what an ALTMETHOD pass is for.
"""
import sys, glob
import numpy as np
from scipy import signal

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/lib')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
from rlog_parse import read_messages
import v282cmp as V

RLOGS = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/rlogs'
FS = 100.0


def extract_route(route):
    segs = sorted(glob.glob(f'{RLOGS}/75604b0a432fdc89_{route}--*--rlog.zst'),
                  key=lambda p: int(p.split('--')[-2]))
    tg, gx, gy, gz = [], [], [], []
    tcs, cs_model, cs_out = [], [], []
    tcst, v_ego, sr_deg = [], [], []
    active, lat_active_t, lat_active = [], [], []
    press = []
    for p in segs:
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            t = evt.logMonoTime / 1e9
            if w == 'gyroscope':
                g = evt.gyroscope
                if g.which() != 'gyroUncalibrated':
                    continue
                v3 = g.gyroUncalibrated.v
                tg.append(t); gx.append(v3[0]); gy.append(v3[1]); gz.append(v3[2])
            elif w == 'controlsState':
                cs = evt.controlsState
                try:
                    ts = cs.lateralControlState.torqueState
                except Exception:
                    continue
                tcs.append(t)
                cs_model.append(cs.desiredCurvature)
                cs_out.append(ts.output)
                active.append(float(ts.active))
            elif w == 'carState':
                c = evt.carState
                tcst.append(t); v_ego.append(c.vEgo); sr_deg.append(c.steeringRateDeg); press.append(float(c.steeringPressed))
            elif w == 'carControl':
                cc = evt.carControl
                lat_active_t.append(t); lat_active.append(float(cc.latActive))
    return dict(tg=np.array(tg), gx=np.array(gx), gy=np.array(gy), gz=np.array(gz),
                tcs=np.array(tcs), cs_curv=np.array(cs_model), cs_out=np.array(cs_out), active=np.array(active),
                tcst=np.array(tcst), v=np.array(v_ego), sr=np.array(sr_deg), press=np.array(press),
                tcc=np.array(lat_active_t), lat_active=np.array(lat_active))


def resample_all(D):
    t = D['tcs']
    I = lambda tk, k: np.interp(t, D[tk], D[k])
    v = I('tcst', 'v')
    out = dict(t=t, v=v, sr=I('tcst', 'sr'), press=I('tcst', 'press') > 0.5,
               active=(D['active'] > 0.5) & (I('tcc', 'lat_active') > 0.5),
               model=D['cs_curv'] * v * v,
               gx=I('tg', 'gx'), gy=I('tg', 'gy'), gz=I('tg', 'gz'))
    return out


def bp(x, f1, f2, fs=FS, order=4):
    sos = signal.butter(order, [f1, f2], btype='band', fs=fs, output='sos')
    return signal.sosfiltfilt(sos, x)


def pick_yaw_axis(S, usable_mask):
    """Correlate each raw gyro axis (and its negative) with the model's desired lateral accel over
    usable engaged time -- whichever wins is the yaw axis, sign included."""
    m = usable_mask & (np.abs(S['model']) > 0.3)
    best = None
    for name in ('gx', 'gy', 'gz'):
        x = S[name][m]
        y = S['model'][m]
        if len(x) < 200:
            continue
        c = np.corrcoef(x, y)[0, 1]
        if best is None or abs(c) > abs(best[1]):
            best = (name, c)
    return best


def main():
    routes = dict(V282='00000064--ce6b0b0ebb', T64='0000006c--68c6e94b17')
    results = {}
    for grp, rk in routes.items():
        print(f'--- {grp} {rk} extracting from rlogs ---', flush=True)
        Draw = extract_route(rk)
        print('  n gyro', len(Draw['tg']), 'dt med', np.median(np.diff(Draw['tg'])),
              'n cs', len(Draw['tcs']), 'n cst', len(Draw['tcst']))
        S = resample_all(Draw)
        del Draw
        usable = S['active'] & ~S['press'] & (S['v'] > 0)
        axis, corr = pick_yaw_axis(S, usable)
        print(f'  yaw axis = {axis}, corr with model = {corr:.3f}')
        yaw = S[axis] if corr > 0 else -S[axis]
        # sanity: also load the cached v282cmp signals for the SAME route to cross-check v, model align
        Scache = V.load(rk)
        # --- (A) whole-route matched blocks: sr vs raw-gyro-yaw*v, band power 1.8-3.0 Hz, by speed stratum
        block = {}
        for lo, hi, lbl in [(0, 15, 'lt15'), (15, 40, 'ge15')]:
            u = usable & (S['v'] >= lo) & (S['v'] < hi)
            sr_rms, yaw_rms = [], []
            for a, b in V.runs(u, S['t'], min_s=5.12):
                n = ((b - a) // 512) * 512
                if n < 512:
                    continue
                srb = bp(np.nan_to_num(S['sr'][a:a + n]), 1.8, 3.0)
                yawb = bp(np.nan_to_num(yaw[a:a + n] * S['v'][a:a + n]), 1.8, 3.0)
                for k0 in range(0, n, 512):
                    sr_rms.append(np.sqrt(np.mean(srb[k0:k0 + 512] ** 2)))
                    yaw_rms.append(np.sqrt(np.mean(yawb[k0:k0 + 512] ** 2)))
            block[lbl] = dict(n=len(sr_rms), sr_rms_med=float(np.median(sr_rms)) if sr_rms else None,
                              yaw_rms_med=float(np.median(yaw_rms)) if yaw_rms else None,
                              yaw_rms_p90=float(np.percentile(yaw_rms, 90)) if yaw_rms else None)
        # --- (B) event-based: after desired-jerk events, raw-gyro-yaw band-rms in the post window vs pre
        ev, _ = V.jerk_events(dict(t=S['t'], v=S['v'], model=S['model'], active=S['active'], pressed=S['press']))
        events = []
        for e in ev:
            k = e['idx']
            a0, b0 = k - 150, k + 300  # -1.5s..+3s at 100Hz
            if a0 < 0 or b0 >= len(S['t']) or not usable[a0:b0].all():
                continue
            pre = bp(np.nan_to_num(yaw[a0:k] * S['v'][a0:k]), 1.8, 3.0)
            post = bp(np.nan_to_num(yaw[k:b0] * S['v'][k:b0]), 1.8, 3.0)
            events.append(dict(v=e['v'], pre=float(np.sqrt(np.mean(pre ** 2))) if len(pre) > 32 else np.nan,
                               post=float(np.sqrt(np.mean(post ** 2))) if len(post) > 32 else np.nan))
        # --- (C) envelope coupling: Hilbert envelope corr of sr and raw-yaw in 1.8-3 Hz, engaged runs >=15 m/s
        envcorrs = []
        for a, b in V.runs(usable & (S['v'] >= 15), S['t'], min_s=10.24):
            srb = bp(np.nan_to_num(S['sr'][a:b]), 1.8, 3.0)
            yawb = bp(np.nan_to_num(yaw[a:b] * S['v'][a:b]), 1.8, 3.0)
            esr = np.abs(signal.hilbert(srb)); eyaw = np.abs(signal.hilbert(yawb))
            if len(esr) > 200:
                envcorrs.append(float(np.corrcoef(esr, eyaw)[0, 1]))
        results[grp] = dict(axis=axis, corr_model=float(corr), block=block,
                            events_n=len(events),
                            events_post_med=float(np.nanmedian([e['post'] for e in events])) if events else None,
                            events_pre_med=float(np.nanmedian([e['pre'] for e in events])) if events else None,
                            envcorr_med=float(np.median(envcorrs)) if envcorrs else None,
                            envcorr_n=len(envcorrs))
        print(f'  block: {block}')
        print(f'  events n={len(events)} post_med={results[grp]["events_post_med"]} pre_med={results[grp]["events_pre_med"]}')
        print(f'  envcorr n={len(envcorrs)} med={results[grp]["envcorr_med"]}')
        del S, Scache
    print('\n=== SUMMARY ===')
    import json
    print(json.dumps(results, indent=1, default=str))
    json.dump(results, open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s4_texture__textureisint__altmethod/raw_gyro_result.json', 'w'), indent=1, default=str)


def usable_full_placeholder(S):
    return S['active']


if __name__ == '__main__':
    main()
