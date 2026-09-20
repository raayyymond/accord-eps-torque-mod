"""d_v282low stage 1 -- per-route reduction of the LOW-SPEED (< 15 m/s) regime, angle domain.

Desired steering angle: model desired curvature through the car's MEASURED steering ratio vs |angle| (d_srfit.py) and
the VehicleModel slip term (sf = -7.0e-4 from opendbc scale_tire_stiffness), plus liveParameters angleOffset.
Common-lead variant: sa_des shifted LATER by (lat_delay - 0.20) s, so every build is scored at V282's 0.20 s lead.

Stored per route (one route in RAM at a time):
  RUNS : list of arrays for usable runs >= 6 s below 15 m/s (v, sa_des, sa_des_cl, sa, sr, out, f, p, i, e4)  float32
  BLK  : 1.28 s blocks (128 frames) inside runs >= 3 s -- columns in BLK_COLS
  EV   : rate-transient events (peak |d sa_des/dt| >= 15 deg/s, 2 Hz lp) -- columns in EV_COLS
  DJ   : dwell-then-jump (s4 definition) with (v, |sa|, dwell_s, jump_deg, |pre|)
"""
import sys, json
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low'
FS = 100.0
L, SF, G = 2.83, -7.0e-4, 9.81
VMIN, VMAX = 2.5, 15.0

BLK_COLS = ['v', 'abs_des', 'abs_rate_des', 'err_rms', 'err_rms_cl', 'err_mean_abs', 'sr_2_10', 'sr_18_35', 'sr_lt1',
            'out_2_10', 'out_lt1', 'f_2_10', 'p_2_10', 'i_2_10', 'out_mean_abs', 'rate_des_2_10', 'sat']
EV_COLS = ['v', 'sa0', 'dDes', 'peak_rate_des', 'peak_rate_meas', 'build', 't50_lag', 't50_lag_cl', 'rise_des', 'rise_meas',
           'overrun', 'overrun_cl', 'err_rms', 'err_rms_cl', 'sr_2_10', 'sr_18_35', 'out_2_10', 'out_step', 'n_dj',
           'max_jump', 'settle_err', 'ratio_mid']


def bp(x, f1, f2, order=4):
    return signal.sosfiltfilt(signal.butter(order, [f1, f2], btype='band', fs=FS, output='sos'), x)


def lp(x, fc, order=4):
    return signal.sosfiltfilt(signal.butter(order, fc, btype='low', fs=FS, output='sos'), x)


def fillnan(x):
    x = np.asarray(x, float).copy()
    ok = np.isfinite(x)
    if ok.sum() == 0:
        return np.zeros_like(x)
    idx = np.arange(len(x))
    x[~ok] = np.interp(idx[~ok], idx[ok], x[ok])
    return x


# pooled empirical steering ratio vs |angle| (d_srfit.py, all 11 routes, livePose yaw / v, steady frames)
SR_K = np.array([0, 8, 15, 27, 47, 75, 110, 155, 400.0])
SR_V = np.array([17.0, 16.8, 16.6, 16.2, 16.2, 15.8, 14.9, 14.7, 14.7])


def sa_des_of(S):
    """Model desired curvature -> steering angle through the CAR's measured ratio (not the fork's map, not liveParameters).
    Sign: model curvature is opposite to steeringAngleDeg on this car (verified, median sign -1). Roll not compensated."""
    v = fillnan(S['v']); aoff = fillnan(S['aoff'])
    curv = np.nan_to_num(S['model'] / np.maximum(v, 0.1) ** 2)
    base = np.degrees(-curv * L * (1 - SF * v ** 2))
    sa0 = base * 16.33
    for _ in range(3):
        sa0 = base * np.interp(np.abs(sa0), SR_K, SR_V)
    return sa0 + aoff


def dwell_jumps(sr, sa, v):
    rs = np.convolve(np.abs(sr), np.ones(10) / 10, 'same')
    low = rs < 0.75; out = []; n = len(sr); i = 0
    while i < n:
        if not low[i]:
            i += 1; continue
        j = i
        while j + 1 < n and low[j + 1]:
            j += 1
        Ln = j - i + 1
        if Ln >= 12 and i - 50 >= 0 and j + 50 < n:
            pre = sa[i] - sa[i - 50]; post = sa[j + 50] - sa[j]
            if abs(pre) >= 0.5 and abs(post) >= 0.5 and np.sign(pre) == np.sign(post):
                out.append((v[j], abs(sa[j]), Ln / FS, abs(sa[j + 30] - sa[j]), abs(pre), j))
        i = j + 1
    return out


def t_cross(x, frac):
    """first index where x (normalised 0->1) crosses frac, linear interp; nan if never."""
    k = np.nonzero(x >= frac)[0]
    if not len(k):
        return np.nan
    k = k[0]
    if k == 0:
        return 0.0
    return (k - 1) + (frac - x[k - 1]) / max(x[k] - x[k - 1], 1e-9)


def route(rk):
    S = V.load(rk)
    t = S['t']; v = fillnan(S['v'])
    u = V.usable(S, VMIN, VMAX)
    sad = sa_des_of(S)
    ld = float(np.nanmedian(S['lat_delay']))
    sh = int(round((ld - 0.20) * FS))
    sad_cl = np.concatenate([np.full(sh, sad[0]), sad[:-sh]]) if sh > 0 else sad.copy()
    sa = fillnan(S['sa']); sr = fillnan(S['sr'])
    out = np.nan_to_num(S['out']); f = np.nan_to_num(S['f']); p = np.nan_to_num(S['p']); i_ = np.nan_to_num(S['i'])
    e4 = fillnan(S['e4']); sat = S['sat'].astype(float)
    RUNS, BLK, EV, DJ = [], [], [], []
    for a, b in V.runs(u, t, min_s=3.0):
        n = b - a
        if n < 300:
            continue
        sl = slice(a, b)
        x = dict(v=v[sl], sad=sad[sl], sadc=sad_cl[sl], sa=sa[sl], sr=sr[sl], out=out[sl], f=f[sl], p=p[sl], i=i_[sl], e4=e4[sl])
        if n >= 600:
            RUNS.append(np.vstack([x[k] for k in ['v', 'sad', 'sadc', 'sa', 'sr', 'out', 'f', 'p', 'i', 'e4']]).astype(np.float32))
        rate_des = V.deriv(lp(x['sad'], 2.0, 2))
        sr_2_10 = bp(x['sr'], 2, 10); sr_18 = bp(x['sr'], 1.8, 3.5); sr_lt1 = lp(x['sr'], 1.0)
        out_2_10 = bp(x['out'], 2, 10); out_lt1 = lp(x['out'], 1.0)
        f_2_10 = bp(x['f'], 2, 10); p_2_10 = bp(x['p'], 2, 10); i_2_10 = bp(x['i'], 2, 10)
        rd_2_10 = bp(rate_des, 2, 10)
        err = x['sa'] - x['sad']; errc = x['sa'] - x['sadc']
        rms = lambda z, s: float(np.sqrt(np.mean(z[s] ** 2)))
        for k0 in range(50, n - 50 - 128 + 1, 128):   # 0.5 s edge trim for the filters
            s = slice(k0, k0 + 128)
            BLK.append([float(np.median(x['v'][s])), float(np.mean(np.abs(x['sad'][s]))), float(np.mean(np.abs(rate_des[s]))),
                        rms(err, s), rms(errc, s), float(abs(np.mean(err[s]))), rms(sr_2_10, s), rms(sr_18, s), rms(sr_lt1, s),
                        rms(out_2_10, s), rms(out_lt1, s), rms(f_2_10, s), rms(p_2_10, s), rms(i_2_10, s),
                        float(np.mean(np.abs(x['out'][s]))), rms(rd_2_10, s), float(np.mean(sat[a + k0:a + k0 + 128]))])
        for d in dwell_jumps(x['sr'], x['sa'], x['v']):
            DJ.append(d[:5])
        dj_idx = np.array([d[5] for d in dwell_jumps(x['sr'], x['sa'], x['v'])], dtype=int)
        # rate-transient events: peaks of |rate_des|
        pk, _ = signal.find_peaks(np.abs(rate_des), height=15.0, distance=200)
        sr5 = lp(x['sr'], 5.0, 2)
        for k in pk:
            k0, k1 = k - 150, k + 300
            if k0 < 50 or k1 > n - 50:
                continue
            w = slice(k0, k1)
            des = x['sad'][w]; desc = x['sadc'][w]; meas = x['sa'][w]
            d0, d1 = float(np.mean(des[:20])), float(np.mean(des[-30:]))
            dD = d1 - d0
            if abs(dD) < 5.0:
                continue
            sg = np.sign(dD)
            nd = (des - d0) / dD; ndc = (desc - float(np.mean(desc[:20]))) / dD; nm = (meas - float(np.mean(meas[:20]))) / dD
            t50d, t50m, t50c = t_cross(nd, 0.5), t_cross(nm, 0.5), t_cross(ndc, 0.5)
            rise_d = t_cross(nd, 0.9) - t_cross(nd, 0.1); rise_m = t_cross(nm, 0.9) - t_cross(nm, 0.1)
            k90 = t_cross(nd, 0.9)
            k90 = 0 if not np.isfinite(k90) else int(k90)
            over = float(np.max(sg * (meas[k90:] - des[k90:])))       # deg past the desired, after desired reached 90 %
            overc = float(np.max(sg * (meas[k90:] - desc[k90:])))
            ramp = slice(int(np.nan_to_num(t_cross(nd, 0.2))), max(int(np.nan_to_num(t_cross(nd, 0.8))) + 1, 1))
            ratio_mid = float(np.mean(nm[ramp]) / max(np.mean(nd[ramp]), 1e-3))
            ndj = dj_idx[(dj_idx >= k0) & (dj_idx < k1)] if len(dj_idx) else dj_idx
            jumps = [abs(x['sa'][j + 30] - x['sa'][j]) for j in ndj]
            o_lp = lp(x['out'], 1.0)[w]
            EV.append([float(np.median(x['v'][w])), float(x['sad'][k]), dD, float(np.max(sg * rate_des[w])), float(np.max(sg * sr5[w])),
                       float(abs(x['sad'][k1 - 1]) > abs(x['sad'][k0])),
                       (t50m - t50d) / FS, (t50m - t50c) / FS, rise_d / FS, rise_m / FS, over, overc,
                       float(np.sqrt(np.mean((meas - des) ** 2))), float(np.sqrt(np.mean((meas - desc) ** 2))),
                       rms(sr_2_10, w), rms(sr_18, w), rms(out_2_10, w), float(abs(np.mean(o_lp[-30:]) - np.mean(o_lp[:20]))),
                       float(len(ndj)), float(max(jumps) if jumps else 0.0), float(np.mean(np.abs(meas[-50:] - des[-50:]))), ratio_mid])
    np.savez_compressed(f'{HERE}/data/{rk}.npz', BLK=np.array(BLK, float), EV=np.array(EV, float), DJ=np.array(DJ, float),
                        RUNS=np.concatenate(RUNS, axis=1) if RUNS else np.zeros((10, 0), np.float32),
                        RUNLEN=np.array([r.shape[1] for r in RUNS], int), ld=ld)
    print(rk, S['meta']['group'], 'blocks', len(BLK), 'events', len(EV), 'dj', len(DJ), 'runs>=6s', len(RUNS),
          'run s', sum(r.shape[1] for r in RUNS) / FS, 'ld', ld, flush=True)
    del S


if __name__ == '__main__':
    import os
    os.makedirs(f'{HERE}/data', exist_ok=True)
    for rk in (sys.argv[1:] or list(V.ROUTES)):
        route(rk)
