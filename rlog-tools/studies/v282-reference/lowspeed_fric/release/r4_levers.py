"""Stage 4: (a) the hysteresis term at release, (b) the rate loop at release, (c) what EXISTING
toggles reach on the release side -- structural reach only (how much of the measured command
fall-back each would have supplied on the real logged episodes).  NO closed-loop prediction.

Also the guard on raising AccordFFRateGain: how much 1.8-3.5 Hz (the shake band) the `move`
channel already carries, relative to the whole command.
-> out/r4_levers.json
"""
import numpy as np, json
import scipy.signal as ss
from rel_lib import *
from sslib import hyst_run, band

EP, W, P = load()
N = len(EP)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); rt = col('route'); aa_abs = col('abs_aa')
TQ = np.isin(g, TQG); V2 = g == 'V282'
S = {k: W[k] * sj[:, None] for k in ('cmd', 'P', 'I', 'F', 'hold_ff', 'move', 'z', 'rl', 'dob', 'aa', 'angdes', 'sr')}
R = {}
mean = lambda x: round(float(np.mean(x)), 5)


def D(k, L, m):   # mean sign-aligned delta of channel k over L frames from breakaway
    return float(np.mean((S[k][:, PRE + L] - S[k][:, PRE])[m]))


# ================= (a) the hysteresis term z at release =================
# z is driven by d(angle_DESIRED).  Counterfactual z_meas: the same operator driven by
# d(measured angle) instead -- "a hysteresis term that knows the wheel moved".
fric = np.array([float(P[e['route']].get('AccordFrictionHyst', 0.0)) for e in EP])
sch = np.array([P[e['route']].get('AccordFrictionHystBand', '0') == '1' for e in EP])
bw = np.array([band(v[i], bool(sch[i])) for i in range(N)])
d_aa = np.diff(W['aa'], axis=1, prepend=W['aa'][:, :1])
z_meas = np.zeros_like(d_aa)
for i in range(N):
    if fric[i] > 0:
        z_meas[i] = hyst_run(d_aa[i], fric[i], np.full(d_aa.shape[1], bw[i]), np.ones(d_aa.shape[1], bool))
Sz_meas = z_meas * sj[:, None]
R['a_hysteresis_at_release'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    m = TQ & (v >= lo) & (v < hi)
    row = dict(n=int(m.sum()), z_level_at_bk=mean(S['z'][m, PRE]), frac_clipped_at_bk=round(float(np.mean(np.abs(W['z'][m, PRE]) >= 0.999 * fric[m])), 3))
    for L in (30, 50):
        dz = (S['z'][:, PRE + L] - S['z'][:, PRE])[m]
        dzm = (Sz_meas[:, PRE + L] - Sz_meas[:, PRE])[m]
        row[f'+{L*10}ms'] = dict(dz_mean=mean(dz), dz_p50=round(float(np.median(dz)), 5),
                                 frac_dz_negative=round(float(np.mean(dz < -1e-6)), 3),
                                 dz_if_driven_by_measured_angle=mean(dzm),
                                 frac_dzmeas_negative=round(float(np.mean(dzm < -1e-6)), 3),
                                 demand_reverses=round(float(np.mean((S['angdes'][:, PRE + L] - S['angdes'][:, PRE])[m] < 0)), 3))
    R['a_hysteresis_at_release'][f'{lo}-{hi}'] = row

# ================= (b) the rate loop at release =================
b5, a5 = ss.butter(2, 5.0 / 50.0)
srl = ss.filtfilt(b5, a5, W['sr'], axis=1) * sj[:, None]
pk_t = np.argmax(np.abs(srl[:, PRE:PRE + 51]), 1) * 0.01
rlg = np.array([float(P[e['route']].get('AccordRateLoopGain', 0.0)) for e in EP])
R['b_rate_loop_at_release'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    m = TQ & (v >= lo) & (v < hi)
    row = dict(n=int(m.sum()), gain_flown=round(float(np.mean(rlg[m])), 5),
               rl_level_at_bk=mean(S['rl'][m, PRE]),
               taper=round(float(np.mean(np.minimum(1.0, RATE_LOOP_TAPER_V / np.maximum(v[m], 0.1)))), 3))
    for L in (30, 50):
        row[f'drl_+{L*10}ms'] = mean((S['rl'][:, PRE + L] - S['rl'][:, PRE])[m])
        row[f'dcmd_+{L*10}ms'] = mean((S['cmd'][:, PRE + L] - S['cmd'][:, PRE])[m])
    # is the rate loop's output still useful when it arrives?  D_loop 55-75 ms => 6-8 frames
    row['frac_peak_rate_after_65ms'] = round(float(np.mean(pk_t[m] > 0.065)), 3)
    row['frac_peak_rate_after_110ms'] = round(float(np.mean(pk_t[m] > 0.110)), 3)
    row['pk_rate_time_p50'] = round(float(np.median(pk_t[m])), 3)
    # the rate loop's own signal at release, in the frame the wheel feels it (shift 6 frames)
    for sh in (0, 6, 8):
        row[f'drl_+300ms_shift{sh}'] = mean((S['rl'][:, PRE + 30 - sh] - S['rl'][:, PRE - sh])[m])
    R['b_rate_loop_at_release'][f'{lo}-{hi}'] = row

# ================= (c) existing-toggle structural reach on the release side =================
# target = the matched torque-minus-V282 excess rise in the command over 300 ms (r1_decomp)
TARGET = {'2-8': 0.02176, '8-15': 0.02445}
R['c_reach'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    key = f'{lo}-{hi}'
    m = TQ & (v >= lo) & (v < hi); mT64 = (g == 'T64') & (v >= lo) & (v < hi)
    tgt = TARGET[key]
    rows = {}
    # 1. AccordDobHz 0.6 -> 0 (ARM-D, already queued): removes the observer's own rise
    rows['AccordDobHz 0.6->0 (ARM-D)'] = dict(delta_cmd_300ms=mean(-(S['dob'][:, PRE + 30] - S['dob'][:, PRE])[mT64]),
                                              basis='T64 only (the flown rev); T4/T5-style revs differ', n=int(mT64.sum()))
    # 2. AccordFFRateGain 0.5 -> s: the move term (the only demand-side LEAD term) scales linearly
    for s in (1.0, 2.0, 4.0):
        f_ = s / 0.5 - 1.0
        rows[f'AccordFFRateGain 0.5->{s}'] = dict(delta_cmd_300ms=mean(f_ * (S['move'][:, PRE + 30] - S['move'][:, PRE])[m]),
                                                 also_adds_at_breakaway=mean(f_ * S['move'][m, PRE]),
                                                 n=int(m.sum()))
    # 3. AccordRateLoopGain 0.001 -> s
    for s in (0.0015, 0.002):
        f_ = s / 0.001 - 1.0
        rows[f'AccordRateLoopGain 0.001->{s}'] = dict(delta_cmd_300ms=mean(f_ * (S['rl'][:, PRE + 30] - S['rl'][:, PRE])[m]),
                                                     note='REPORT: gain margin permits ~x1.5 from 0.0006; the flown 0.001 is already above that')
    # 4. AccordFrictionHyst 0.015 -> s : z scales linearly (level AND rise)
    for s in (0.010, 0.0):
        f_ = s / 0.015 - 1.0
        rows[f'AccordFrictionHyst 0.015->{s}'] = dict(delta_cmd_300ms=mean(f_ * (S['z'][:, PRE + 30] - S['z'][:, PRE])[m]),
                                                     also_removes_at_breakaway=mean(f_ * S['z'][m, PRE]))
    # 5. AccordHoldLevel 1->0 : the hold term / 1.15
    f_ = 1.0 / 1.15 - 1.0
    rows['AccordHoldLevel 1->0'] = dict(delta_cmd_300ms=mean(f_ * (S['hold_ff'][:, PRE + 30] - S['hold_ff'][:, PRE])[mT64]),
                                        note='already flown as T64B: worse in band and shakier')
    # 6. SteerKP / SteerLatAccel : P scales linearly -- P RISES after release, so raising it hurts
    for s in (0.5, 1.5):
        rows[f'P scale x{s} (SteerKP or 1/SteerLatAccel)'] = dict(delta_cmd_300ms=mean((s - 1.0) * (S['P'][:, PRE + 30] - S['P'][:, PRE])[m]))
    for k in rows:
        dc = rows[k]['delta_cmd_300ms']
        rows[k]['share_of_target'] = round(float(-dc / tgt), 3)     # + = closes the gap
    rows['_target_matched_excess_rise_300ms'] = tgt
    R['c_reach'][key] = rows

# ================= (d) guard: shake-band content of the move term =================
bb, aa_ = ss.butter(2, [1.8 / 50.0, 3.5 / 50.0], btype='band')
R['d_shake_band_content'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    for gname, gm in (('TORQUE', TQ), ('V282', V2)):
        m = gm & (v >= lo) & (v < hi)
        if m.sum() < 8:
            continue
        row = {'n': int(m.sum())}
        for k in ('cmd', 'move', 'hold_ff', 'z', 'rl', 'dob', 'P', 'F'):
            x = W[k][m]
            if np.allclose(x, 0):
                row[k] = 0.0; continue
            y = ss.filtfilt(bb, aa_, x, axis=1)
            row[k] = round(float(np.sqrt(np.mean(y[:, 40:-40] ** 2))), 6)
        row['move_over_cmd'] = round(row['move'] / max(row['cmd'], 1e-9), 3)
        R['d_shake_band_content'][f'{gname}|{lo}-{hi}'] = row

json.dump(R, open(OUT + '/r4_levers.json', 'w'), indent=1, default=float)
print(json.dumps(R, indent=1))
