"""b06: does the stick-slip cycle BECOME the 2-3 Hz shake, or excite it?
  * dwell-then-jump events (s4/d_v282low definition, verbatim logic): 10-frame |rate| mean < 0.75 deg/s for >= 12 frames,
    same-sign >= 0.5 deg travel in the 0.5 s before and after. Index = dwell end.
  * event-triggered median shake envelope (1.8-3.5 Hz rate, Hilbert) at -1.0..+2.0 s, v < 8 and 8-15
  * share of band rate ENERGY inside [end-0.2, end+1.5] s vs the share of TIME those windows occupy
  * intervals between consecutive dwell ends (a 2-3 Hz relay cycle would put them at 0.3-0.5 s)
  * spectral peak of the band rate: PSD nperseg 512 (df 0.195 Hz), local max in 1.5-4.5 Hz; zero-crossing frequency of the
    1.8-3.5 Hz rate inside envelope >= 4 deg/s
  * angle amplitude of the shake vs 2F/k (F 0.020 identified; k = fork HOLD_K_V(v) -- BELIEF about plant k)"""
import json
import numpy as np
from scipy import signal
import bs
V = bs.V
S2 = signal.butter(4, [1.8, 3.5], btype='band', fs=100, output='sos')
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0]; HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095]
GROUP = {**bs.TORQUE, **bs.V282}


def dwell_jumps(sr, sa):
    rs = np.convolve(np.abs(sr), np.ones(10) / 10, 'same')
    low = rs < 0.75; out = []; n = len(sr); i = 0
    while i < n:
        if not low[i]:
            i += 1; continue
        j = i
        while j + 1 < n and low[j + 1]:
            j += 1
        if j - i + 1 >= 12 and i - 50 >= 0 and j + 50 < n:
            pre = sa[i] - sa[i - 50]; post = sa[j + 50] - sa[j]
            if abs(pre) >= 0.5 and abs(post) >= 0.5 and np.sign(pre) == np.sign(post):
                out.append((j, abs(sa[j + 30] - sa[j]), (j - i + 1) / 100))
        i = j + 1
    return out


RES = {}
for rk, g in GROUP.items():
    S = V.load(rk)
    m = V.usable(S, 0, 15) & np.isfinite(S['sr']) & np.isfinite(S['sa'])
    acc = {lab: dict(trig=[], E_in=0.0, E_all=0.0, n_in=0, n_all=0, iv=[], jumps=[], psd=None, nps=0, zc=[], v=[]) for lab in ('<8', '8-15')}
    for a, b in V.runs(m, S['t'], min_s=6.0):
        sr = S['sr'][a:b]; sa = S['sa'][a:b]; v = S['v'][a:b]
        env = np.abs(signal.hilbert(signal.sosfiltfilt(S2, sr))); rb = signal.sosfiltfilt(S2, sr)
        e = 100; n = len(sr)
        inwin = np.zeros(n, bool)
        dj = dwell_jumps(sr, sa)
        last = {}
        for j, jump, dw in dj:
            lab = '<8' if v[j] < 8 else '8-15'
            A = acc[lab]; A['jumps'].append((jump, dw, v[j]))
            if lab in last:
                A['iv'].append((j - last[lab]) / 100)
            last[lab] = j
            if j - 100 >= e and j + 200 < n - e:
                A['trig'].append(env[j - 100:j + 200])
            inwin[max(j - 20, 0):min(j + 150, n)] = True
        for lab, lo, hi in (('<8', 0, 8), ('8-15', 8, 15)):
            sel = np.zeros(n, bool); sel[e:n - e] = True; sel &= (v >= lo) & (v < hi)
            A = acc[lab]
            A['E_all'] += float(np.sum(rb[sel] ** 2)); A['E_in'] += float(np.sum(rb[sel & inwin] ** 2))
            A['n_all'] += int(sel.sum()); A['n_in'] += int((sel & inwin).sum())
            if sel.sum() >= 512:
                # PSD on contiguous stretches of this bin
                for c0, c1 in V.runs(sel, np.arange(n) / 100.0, min_s=5.12):
                    fr, p = signal.welch(sr[c0:c1], 100, nperseg=512, noverlap=256)
                    A['psd'] = p * (c1 - c0) if A['psd'] is None else A['psd'] + p * (c1 - c0); A['nps'] += c1 - c0; A['f'] = fr
            hi_env = sel & (env >= 4.0)
            for c0, c1 in V.runs(hi_env, np.arange(n) / 100.0, min_s=0.8):
                zc = np.sum(np.diff(np.sign(rb[c0:c1])) != 0) / 2 / ((c1 - c0) / 100)
                A['zc'].append((zc, float(np.mean(v[c0:c1])), (c1 - c0) / 100, float(np.mean(np.abs(signal.hilbert(signal.sosfiltfilt(S2, sa[max(c0-100,0):c1+100])))[100 if c0>=100 else c0: (100 if c0>=100 else c0) + c1 - c0]))))
    out = {}
    for lab, A in acc.items():
        r = dict(n_dj=len(A['jumps']), secs=A['n_all'] / 100,
                 energy_share_in_dj_windows=A['E_in'] / max(A['E_all'], 1e-9), time_share_dj_windows=A['n_in'] / max(A['n_all'], 1))
        if A['trig']:
            T = np.array(A['trig']); r['trig_median'] = np.median(T, 0)[::10].round(2).tolist(); r['n_trig'] = len(T)
        if A['iv']:
            iv = np.array(A['iv']); r['iv_p10_p50'] = [float(np.percentile(iv, 10)), float(np.median(iv))]; r['iv_frac_lt_0p6s'] = float(np.mean(iv < 0.6))
        if A['jumps']:
            J = np.array(A['jumps']); r['jump_p50_p90'] = [float(np.median(J[:, 0])), float(np.percentile(J[:, 0], 90))]
            r['twoF_over_k_at_event_v_p50'] = float(np.median(2 * 0.020 / np.interp(J[:, 2], HOLD_V_BP, HOLD_K_V)))
        if A['psd'] is not None:
            fr = A['f']; p = A['psd'] / A['nps']; s = (fr >= 1.5) & (fr <= 4.5)
            k = np.argmax(p[s]); r['psd_peak_hz'] = float(fr[s][k]); r['psd_1p5_4p5'] = p[s].round(3).tolist()
            r['psd_peak_over_1p2hz'] = float(p[s][k] / p[(fr >= 1.1) & (fr <= 1.3)].mean())
        if A['zc']:
            Z = np.array(A['zc']); r['zc_hz_p50'] = float(np.median(Z[:, 0])); r['zc_n'] = len(Z)
            r['zc_by_v'] = {f'{lo}-{hi}': [float(np.median(Z[(Z[:, 1] >= lo) & (Z[:, 1] < hi), 0])) if ((Z[:, 1] >= lo) & (Z[:, 1] < hi)).sum() >= 3 else None,
                                           int(((Z[:, 1] >= lo) & (Z[:, 1] < hi)).sum())] for lo, hi in ((0, 4), (4, 6), (6, 8), (8, 11), (11, 15))}
            r['shake_angle_amp_p50_p90'] = [float(np.median(Z[:, 3])), float(np.percentile(Z[:, 3], 90))]
        out[lab] = r
    RES[rk] = dict(group=g, **out)
    print(rk, g, {lab: {k: v for k, v in r.items() if k not in ('trig_median', 'psd_1p5_4p5')} for lab, r in out.items()}, flush=True)
    del S
json.dump(RES, open(bs.OUT + 'b06_stickslip_link.json', 'w'), indent=1)
