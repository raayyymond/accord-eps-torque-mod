"""s4_texture -- per-block and per-event TEXTURE metrics, one route at a time, reduced to small npz files.

Blocks: non-overlapping 5.12 s (512-frame) stretches of V.usable(S) inside V.runs() (never across a gap).
Per block: stratum (median v, p90 |angle|, activity = mean |0.5 Hz-lowpassed rate|), Hann periodograms of the
steering rate, achieved lateral accel (la_act and livePose) and the 0xE4 word, and scalar texture metrics.

Texture metrics (all defined here, identical for every route):
  hf_ratio     rms(sr bandpassed 1.5-8 Hz) / (rms(sr lowpassed 1 Hz) + 2 deg/s)   -- rate texture per unit motion
  mode_rms     rms(sr bandpassed 1.8-3.0 Hz)                                         -- the 2-2.7 Hz wheel mode band
  conc         share of |d angle| travel done by the fastest 10 % of frames (smoothed 0.1 s rate)  [V293 ratchet stat]
  stall        fraction of frames with |smoothed rate| < 0.5 deg/s while |0.5 Hz rate| >= 3 deg/s (wheel should move)
  dj_*         dwell-then-jump: a dwell (0.1 s mean |rate| < 0.75 deg/s for >= 0.12 s) with >= 0.5 deg of same-sign
               travel both in the 0.5 s before and the 0.5 s after it; jump = |angle change| over 0.3 s after dwell end
  slew_hit     fraction of frames with |d e4| >= 120 counts (Honda STEER_DELTA 3/s x DT 0.01 x 4096 = 122.9)
  sat          fraction of frames with |e4| >= 4000
  jerk_rough   rms(d/dt la_pose, 1-5 Hz band)   (livePose is 20 Hz: nothing above ~8 Hz is real)
  jerk_act     rms(d/dt la_act, 1-8 Hz band)    (la_act is the controller's own measurement, angle-derived)
  mjerk        rms(d/dt model, lowpass 2 Hz)    -- the DEMAND's jerk, used for matching
"""
import sys, json
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
from scipy import signal
import v282cmp as V

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture/data'
FS = V.FS
NB = 512
SLEW_LIM = 120.0


def bp(x, f1, f2, order=4):
    sos = signal.butter(order, [f1, f2], btype='band', fs=FS, output='sos')
    return signal.sosfiltfilt(sos, x)


def smooth(x, n=10):
    return np.convolve(x, np.ones(n) / n, 'same')


def dwell_jumps(sr, sa):
    """Dwell-then-jump on one contiguous run. Returns list of (dwell_s, jump_deg, pre_deg, rate_after_peak)."""
    rs = smooth(np.abs(sr), 10)
    low = rs < 0.75
    out = []
    n = len(sr); i = 0
    while i < n:
        if not low[i]:
            i += 1; continue
        j = i
        while j + 1 < n and low[j + 1]:
            j += 1
        L = j - i + 1
        if L >= 12 and i - 50 >= 0 and j + 50 < n:
            pre = sa[i] - sa[i - 50]
            post = sa[j + 50] - sa[j]
            if abs(pre) >= 0.5 and abs(post) >= 0.5 and np.sign(pre) == np.sign(post):
                jump = abs(sa[j + 30] - sa[j])
                out.append((L / FS, jump, abs(pre), float(np.max(np.abs(sr[j:j + 30])))))
        i = j + 1
    return out


def route(rk):
    S = V.load(rk)
    t = S['t']; u = V.usable(S)
    sr = np.nan_to_num(S['sr']); sa = np.nan_to_num(S['sa']); v = np.nan_to_num(S['v'])
    e4 = np.nan_to_num(S['e4']); model = np.nan_to_num(S['model'])
    la_act = np.nan_to_num(S['la_act']); la_pose = np.nan_to_num(S['la_pose'])
    rows, P_sr, P_pose, P_e4, P_act, P_sa = [], [], [], [], [], []
    DJ = []   # per dwell-jump: v, |sa|, dwell_s, jump, pre, rate_after
    travel_by = []   # per run: travel deg binned later -> keep per-block travel instead
    f = np.fft.rfftfreq(NB, 1 / FS)
    win = np.hanning(NB); wn = (win ** 2).sum() * FS
    for a, b in V.runs(u, t, min_s=NB / FS):
        if b - a < NB:
            continue
        # run-level filtering (filters run on the whole contiguous run, then blocks are cut)
        s_sr = sr[a:b]; s_sa = sa[a:b]
        sr_lp1 = V.lowpass(s_sr, 1.0); sr_lp05 = V.lowpass(s_sr, 0.5)
        sr_hf = bp(s_sr, 1.5, 8.0) if b - a > 60 else np.zeros(b - a)
        sr_md = bp(s_sr, 1.8, 3.0)
        rsm = smooth(np.abs(s_sr), 10)
        de4 = np.abs(np.diff(e4[a:b], prepend=e4[a]))
        jp = V.deriv(bp(la_pose[a:b], 0.05, 5.0, 2)); jp = bp(jp, 1.0, 5.0)
        ja = bp(V.deriv(la_act[a:b]), 1.0, 8.0)
        mj = V.deriv(V.lowpass(model[a:b], 2.0))
        sa_rate = V.deriv(s_sa)
        sa_hf = bp(sa_rate, 1.5, 5.0); sa_lp1 = V.lowpass(sa_rate, 1.0)
        # dwell-then-jump (same definition as dwell_jumps(), with position for stratum assignment)
        # locate dwell positions too, for stratum assignment
        rs = rsm; low = rs < 0.75; n = b - a; i = 0
        while i < n:
            if not low[i]:
                i += 1; continue
            j = i
            while j + 1 < n and low[j + 1]:
                j += 1
            L = j - i + 1
            if L >= 12 and i - 50 >= 0 and j + 50 < n:
                pre = s_sa[i] - s_sa[i - 50]; post = s_sa[j + 50] - s_sa[j]
                if abs(pre) >= 0.5 and abs(post) >= 0.5 and np.sign(pre) == np.sign(post):
                    DJ.append((v[a + j], abs(s_sa[j]), L / FS, abs(s_sa[j + 30] - s_sa[j]), abs(pre),
                               float(np.max(np.abs(s_sr[j:j + 30]))), float(np.mean(np.abs(sr_lp05[i - 50:j + 50])))))
            i = j + 1
        for k0 in range(0, b - a - NB + 1, NB):
            k1 = k0 + NB; g = slice(a + k0, a + k1); l = slice(k0, k1)
            x = s_sr[l]
            vv = float(np.median(v[g])); ang90 = float(np.percentile(np.abs(sa[g]), 90))
            act = float(np.mean(np.abs(sr_lp05[l])))
            # travel concentration
            dth = np.abs(np.diff(s_sa[l]))
            rsl = rsm[l][1:]
            if dth.sum() > 0.5:
                thr = np.percentile(rsl, 90)
                conc = float(dth[rsl >= thr].sum() / dth.sum())
            else:
                conc = np.nan
            mv = np.abs(sr_lp05[l]) >= 3.0
            stall = float(np.mean(rsm[l][mv] < 0.5)) if mv.sum() >= 50 else np.nan
            rows.append(dict(v=vv, ang90=ang90, angmed=float(np.median(np.abs(sa[g]))), act=act,
                             travel=float(dth.sum()), mv_frames=int(mv.sum()),
                             hf_ratio=float(np.sqrt(np.mean(sr_hf[l] ** 2)) / (np.sqrt(np.mean(sr_lp1[l] ** 2)) + 2.0)),
                             hf_rms=float(np.sqrt(np.mean(sr_hf[l] ** 2))), lf_rms=float(np.sqrt(np.mean(sr_lp1[l] ** 2))),
                             hf_sa_ratio=float(np.sqrt(np.mean(sa_hf[l] ** 2)) / (np.sqrt(np.mean(sa_lp1[l] ** 2)) + 2.0)),
                             hf_sa_rms=float(np.sqrt(np.mean(sa_hf[l] ** 2))),
                             mode_rms=float(np.sqrt(np.mean(sr_md[l] ** 2))),
                             conc=conc, stall=stall,
                             slew_hit=float(np.mean(de4[l] >= SLEW_LIM)), sat=float(np.mean(np.abs(e4[g]) >= 4000)),
                             e4_rms=float(np.sqrt(np.mean(e4[g] ** 2))),
                             jerk_rough=float(np.sqrt(np.mean(jp[l] ** 2))), jerk_act=float(np.sqrt(np.mean(ja[l] ** 2))),
                             mjerk=float(np.sqrt(np.mean(mj[l] ** 2))), mla=float(np.sqrt(np.mean(model[g] ** 2))),
                             t0=float(t[a + k0])))
            def pg(y):
                y = y - np.mean(y); y = signal.detrend(y)
                return (np.abs(np.fft.rfft(y * win)) ** 2 / wn * 2).astype(np.float32)
            P_sr.append(pg(x)); P_sa.append(pg(sa_rate[l])); P_pose.append(pg(la_pose[g])); P_e4.append(pg(e4[g])); P_act.append(pg(la_act[g]))
    # events
    EV = []
    for thr, kind in [(0.4, 'jerk04'), (0.8, 'jerk08')]:
        ev, _ = V.jerk_events(S, jerk_thr=thr)
        for e in ev:
            k = e['idx']; i0, i1 = k - 150, k + 300
            x = sr[i0:i1]
            hf = bp(x, 1.5, 8.0); md = bp(x, 1.8, 3.0)
            de4 = np.abs(np.diff(e4[i0:i1]))
            em = V.event_metrics(S, i0, i1)
            emp = V.event_metrics(S, i0, i1, ach_key='la_pose')
            rs = smooth(np.abs(x), 10); lp = V.lowpass(x, 0.5); mv = np.abs(lp) >= 3
            EV.append(dict(kind=kind, v=e['v'], jerk=abs(e['jerk_peak']), la_peak=e['la_peak'],
                           ang_max=float(np.max(np.abs(sa[i0:i1]))), rate_max=float(np.max(np.abs(V.lowpass(x, 2.0)))),
                           hf_pre=float(np.sqrt(np.mean(hf[:150] ** 2))), hf_post=float(np.sqrt(np.mean(hf[150:] ** 2))),
                           md_pre=float(np.sqrt(np.mean(md[:150] ** 2))), md_post=float(np.sqrt(np.mean(md[150:] ** 2))),
                           hf_ratio=float(np.sqrt(np.mean(hf ** 2)) / (np.sqrt(np.mean(V.lowpass(x, 1.0) ** 2)) + 2)),
                           slew_hit=float(np.mean(de4 >= SLEW_LIM)), sat=float(np.mean(np.abs(e4[i0:i1]) >= 4000)),
                           stall=float(np.mean(rs[mv] < 0.5)) if mv.sum() >= 30 else np.nan,
                           jerk_rough=em['jerk_rough'], jerk_rough_pose=emp['jerk_rough'], gain=em['gain'], lag=em['lag'],
                           gain_pose=emp['gain'], overshoot=em['overshoot']))
    for e in V.accel_events(S, la_thr=1.0):
        i0, i1 = e['i0'], e['i1']
        x = sr[i0:i1]
        if len(x) < 64:
            continue
        hf = bp(x, 1.5, 8.0); md = bp(x, 1.8, 3.0); de4 = np.abs(np.diff(e4[i0:i1]))
        rs = smooth(np.abs(x), 10); lp = V.lowpass(x, 0.5); mv = np.abs(lp) >= 3
        em = V.event_metrics(S, i0, i1); emp = V.event_metrics(S, i0, i1, ach_key='la_pose')
        EV.append(dict(kind='acc10', v=e['v'], jerk=np.nan, la_peak=e['la_peak'],
                       ang_max=float(np.max(np.abs(sa[i0:i1]))), rate_max=float(np.max(np.abs(V.lowpass(x, 2.0)))),
                       hf_pre=np.nan, hf_post=float(np.sqrt(np.mean(hf ** 2))), md_pre=np.nan,
                       md_post=float(np.sqrt(np.mean(md ** 2))),
                       hf_ratio=float(np.sqrt(np.mean(hf ** 2)) / (np.sqrt(np.mean(V.lowpass(x, 1.0) ** 2)) + 2)),
                       slew_hit=float(np.mean(de4 >= SLEW_LIM)), sat=float(np.mean(np.abs(e4[i0:i1]) >= 4000)),
                       stall=float(np.mean(rs[mv] < 0.5)) if mv.sum() >= 30 else np.nan,
                       jerk_rough=em['jerk_rough'], jerk_rough_pose=emp['jerk_rough'], gain=em['gain'], lag=em['lag'],
                       gain_pose=emp['gain'], overshoot=em['overshoot']))
    # frame-level slew table (usable frames): v, |sa|, |de4|, |e4|, |rate|
    de4_all = np.abs(np.diff(e4, prepend=e4[0]))
    okf = u & np.concatenate([[False], np.diff(t) < 4 / FS]) & np.concatenate([[False], u[:-1]])
    FR = np.stack([v[okf], np.abs(sa[okf]), de4_all[okf], np.abs(e4[okf]), np.abs(sr[okf])]).astype(np.float32)
    keys = list(rows[0].keys())
    np.savez_compressed(f'{OUT}/{rk}.npz', f=f, keys=np.array(keys),
                        rows=np.array([[r[k] for k in keys] for r in rows], dtype=np.float64),
                        P_sr=np.array(P_sr), P_pose=np.array(P_pose), P_e4=np.array(P_e4), P_act=np.array(P_act), P_sa=np.array(P_sa),
                        DJ=np.array(DJ, dtype=np.float64).reshape(-1, 7), FR=FR,
                        EV=json.dumps(EV))
    print(rk, S['meta'].get('group'), 'blocks', len(rows), 'dj', len(DJ), 'events', len(EV), 'frames', FR.shape[1], flush=True)
    del S


if __name__ == '__main__':
    import os
    os.makedirs(OUT, exist_ok=True)
    for rk in (sys.argv[1:] or list(V.ROUTES)):
        route(rk)
