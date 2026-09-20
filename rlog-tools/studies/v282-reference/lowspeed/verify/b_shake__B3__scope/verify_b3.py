"""B3 SCOPE verify: re-test dwell-jump energy/time share and episode incidence in the regimes
where a stick-slip-linked shake would most likely show up: <3 m/s, large angle, and re-check the
'<8' claim's per-route arithmetic (the finding cites '4 of 5 torque routes' with 6d 0.21 vs 0.19)."""
import sys, json
import numpy as np
from scipy import signal
BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/'
sys.path.insert(0, BASE)
import v282cmp as V

S2 = signal.butter(4, [1.8, 3.5], btype='band', fs=100, output='sos')
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0]; HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095]
TORQUE = {'0000006c--68c6e94b17': 'T64', '0000006d--05e83bb04f': 'T64', '0000006e--6ca3e014fd': 'T64B',
          '00000076--d0b7ea7e4d': 'T5', '00000075--6c8687d5bd': 'T4'}
V282 = {'00000064--ce6b0b0ebb': 'V282', '00000065--b9f78988bd': 'V282', '0000006c--2bc842dbac': 'V282'}


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


def analyze(rk, g, vlo, vhi, ang_split=None):
    """ang_split: if given (deg threshold), also split energy/time share by |sa| at dwell index vs threshold."""
    S = V.load(rk)
    m = V.usable(S, 0, 15) & np.isfinite(S['sr']) & np.isfinite(S['sa'])
    E_in = E_all = 0.0; N_in = N_all = 0; jumps = []; iv = []; angs_at_event = []
    E_in_hi = E_all_hi = 0.0; N_in_hi = N_all_hi = 0
    n_dj = 0
    for a, b in V.runs(m, S['t'], min_s=6.0):
        sr = S['sr'][a:b]; sa = S['sa'][a:b]; v = S['v'][a:b]
        rb = signal.sosfiltfilt(S2, sr)
        e = 100; n = len(sr)
        inwin = np.zeros(n, bool)
        dj = dwell_jumps(sr, sa)
        last = None
        for j, jump, dw in dj:
            if not (vlo <= v[j] < vhi):
                continue
            n_dj += 1
            jumps.append((jump, dw, v[j]))
            angs_at_event.append(abs(sa[j]))
            if last is not None:
                iv.append((j - last) / 100)
            last = j
            if j - 100 >= e and j + 200 < n - e:
                pass
            inwin[max(j - 20, 0):min(j + 150, n)] = True
        sel = np.zeros(n, bool); sel[e:n - e] = True; sel &= (v >= vlo) & (v < vhi)
        E_all += float(np.sum(rb[sel] ** 2)); E_in += float(np.sum(rb[sel & inwin] ** 2))
        N_all += int(sel.sum()); N_in += int((sel & inwin).sum())
        if ang_split is not None:
            hi_ang = sel & (np.abs(sa) >= ang_split)
            E_all_hi += float(np.sum(rb[hi_ang] ** 2)); E_in_hi += float(np.sum(rb[hi_ang & inwin] ** 2))
            N_all_hi += int(hi_ang.sum()); N_in_hi += int((hi_ang & inwin).sum())
    del S
    r = dict(route=rk, group=g, n_dj=n_dj, secs=N_all / 100,
             energy_share=E_in / max(E_all, 1e-9), time_share=N_in / max(N_all, 1))
    if iv:
        r['iv_p50'] = float(np.median(iv)); r['iv_n'] = len(iv)
    if jumps:
        J = np.array(jumps)
        r['jump_p50'] = float(np.median(J[:, 0]))
        r['twoF_over_k_p50'] = float(np.median(2 * 0.020 / np.interp(J[:, 2], HOLD_V_BP, HOLD_K_V)))
    if angs_at_event:
        r['ang_at_event_p50'] = float(np.median(angs_at_event))
    if ang_split is not None and N_all_hi > 200:
        r['ang_ge_%g_energy_share' % ang_split] = E_in_hi / max(E_all_hi, 1e-9)
        r['ang_ge_%g_time_share' % ang_split] = N_in_hi / max(N_all_hi, 1)
        r['ang_ge_%g_secs' % ang_split] = N_all_hi / 100
    return r


if __name__ == '__main__':
    out = {}
    print('=== <3 m/s, dwell-jump energy vs time share ===')
    for rk, g in {**TORQUE, **V282}.items():
        r = analyze(rk, g, 0, 3)
        out[rk + '|<3'] = r
        print(rk, g, r)

    print()
    print('=== <8 m/s recheck: reproduce the finding\'s per-route energy vs time share ===')
    for rk, g in {**TORQUE, **V282}.items():
        r = analyze(rk, g, 0, 8)
        out[rk + '|<8_recheck'] = r
        flag = 'LESS' if r['energy_share'] < r['time_share'] else 'GREATER/EQUAL'
        print(rk, g, 'energy=%.3f time=%.3f -> %s' % (r['energy_share'], r['time_share'], flag))

    print()
    print('=== 3-8 m/s, dwell-jump energy vs time share (fill the gap between <3 and <8) ===')
    for rk, g in {**TORQUE, **V282}.items():
        r = analyze(rk, g, 3, 8)
        out[rk + '|3-8'] = r
        print(rk, g, r)

    print()
    print('=== large-angle sub-regime: |sa| >= 10 deg, <15 m/s, energy vs time share in dwell windows ===')
    for rk, g in {**TORQUE, **V282}.items():
        r = analyze(rk, g, 0, 15, ang_split=10.0)
        out[rk + '|largeang10'] = r
        print(rk, g, r)

    json.dump(out, open(BASE + 'lowspeed/verify/b_shake__B3__scope/out/verify_b3.json', 'w'), indent=1, default=float)
