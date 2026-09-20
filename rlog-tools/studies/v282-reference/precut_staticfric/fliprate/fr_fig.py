"""fliprate figure: what the term's own waveform is, where its energy lands, how often it flips, and the
reach/band trade-off.  Palette validated with the dataviz validator (light, categorical, all checks pass)."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from fr_lib import *

C = ['#3b5bdb', '#e8590c', '#0ca678', '#ae3ec9']
INK, INK2, MUT, SURF = '#1b1b1a', '#4a4a47', '#8a8a85', '#fcfcfb'
plt.rcParams.update({'font.size': 8.5, 'axes.edgecolor': MUT, 'axes.labelcolor': INK2, 'text.color': INK,
                     'xtick.color': INK2, 'ytick.color': INK2, 'axes.facecolor': SURF, 'figure.facecolor': SURF,
                     'axes.grid': True, 'grid.color': '#e6e6e2', 'grid.linewidth': 0.6, 'axes.axisbelow': True,
                     'legend.frameon': False, 'axes.spines.top': False, 'axes.spines.right': False})
RK = '0000006c--68c6e94b17'
TORQUE = [k for k, mv in V.ROUTES.items() if mv['eps'] == 'V293']
fig, ax = plt.subplots(2, 2, figsize=(11.5, 7.4))

# ---------------- P1: the waveform at a depart breakaway ----------------
R = prep(RK)
v = R['v']; t = R['t']
z = z_out_of(R['angdes'], R['rate_des'], v)
z10 = fo_filter(z, 0.10, reset=~R['act'])
z20 = fo_filter(z, 0.20, reset=~R['act'])
EP = list(np.load(f'{BASE}/lowspeed/a_stickslip/out/{RK}_ss.npz', allow_pickle=True)['EP'])
cand = [e for e in EP if 2 <= float(e['v']) < 8 and (np.sign(float(e['aa'])) == float(e['sdem']) or abs(float(e['aa'])) < 0.5)]
e = sorted(cand, key=lambda q: -float(q['dwell_s']))[len(cand) // 3]
bk = int(e['bk']); i0, i1 = int(e['i0']), int(e['i1'])
sl = slice(bk - 300, bk + 200)
tt = (t[sl] - t[bk])
a = ax[0, 0]
a.axvspan(t[i0] - t[bk], t[i1] - t[bk], color='#ecebe6', lw=0, zorder=0)
a.axhline(0, color=MUT, lw=0.8)
a.plot(tt, z[sl], color=C[0], lw=1.6, label='z_out, as designed')
a.plot(tt, z10[sl], color=C[1], lw=1.6, label='+ post-filter RC 0.10 s')
a.plot(tt, z20[sl], color=C[2], lw=1.6, label='+ post-filter RC 0.20 s')
a.axvline(0, color=INK2, lw=0.9, ls=(0, (4, 3)))
a.annotate('breakaway', (0, a.get_ylim()[1]), xytext=(4, -10), textcoords='offset points', color=INK2, fontsize=8)
a.annotate('dwell', ((t[i0] + t[i1]) / 2 - t[bk], a.get_ylim()[0]), xytext=(-12, 6), textcoords='offset points',
           color=INK2, fontsize=8)
a.set_xlabel('time from breakaway  [s]'); a.set_ylabel('added torque, +left  [output units]')
a.set_title(f'A. One depart dwell, {RK[:8]} at {e["v"]:.1f} m/s: the term slams on and off with sign(demand rate)',
            loc='left', fontsize=8.6, color=INK)
a.legend(loc='lower left', fontsize=8)

# ---------------- P2: where the energy lands (2-5 m/s, all torque routes) ----------------
segz, seg10, segc = [], [], []
for rk in TORQUE:
    Rr = prep(rk)
    vv = Rr['v']
    zz = z_out_of(Rr['angdes'], Rr['rate_des'], vv)
    z15 = fo_filter(zz, 0.15, reset=~Rr['act'])
    m = Rr['HO'] & (vv >= 2.0) & (vv < 5.0)
    for aa_, bb_ in V.runs(m, Rr['t'], min_s=2.56):
        segz.append(zz[aa_:bb_]); seg10.append(z15[aa_:bb_]); segc.append(Rr['cmd'][aa_:bb_])
    del Rr
fr, Pc, sec = psd_sum(segc, nps_max=512)
_, Pz, _ = psd_sum(segz, nps_max=512)
_, P15, _ = psd_sum(seg10, nps_max=512)
a = ax[0, 1]
for (f1, f2), nm in [((1.8, 3.5), 'shake 1.8-3.5'), ((4.0, 4.7), 'relay 4.0-4.7'), ((15.0, 22.0), 'plant 15-22')]:
    a.axvspan(f1, f2, color='#ecebe6', lw=0, zorder=0)
    a.annotate(nm, (np.sqrt(f1 * f2), 2e-3), rotation=90, ha='center', va='top', fontsize=7.2, color=MUT)
s = fr > 0.05
a.loglog(fr[s], Pc[s], color=INK2, lw=1.6, label='flown command (rev 6.4)')
a.loglog(fr[s], Pz[s], color=C[0], lw=1.6, label='z_out, as designed')
a.loglog(fr[s], P15[s], color=C[1], lw=1.6, label='z_out + post-filter RC 0.15 s')
a.set_xlim(0.1, 40); a.set_ylim(1e-11, 3e-3)
a.set_xlabel('frequency  [Hz]'); a.set_ylabel('PSD  [torque$^2$/Hz]')
a.set_title(f'B. Spectrum, 2-5 m/s hands-off, 5 torque routes ({sec:.0f} s): it lands in every band of record',
            loc='left', fontsize=8.6, color=INK)
a.legend(loc='lower left', fontsize=8)

# ---------------- P3: how long the term stays on ----------------
durs = []
for rk in TORQUE:
    Rr = prep(rk)
    vv = Rr['v']
    O = (np.tanh(Rr['angdes'] / A_SCALE) * np.tanh(Rr['rate_des'] / R_SCALE)) > 0
    zz = z_out_of(Rr['angdes'], Rr['rate_des'], vv)
    m = Rr['HO'] & (vv < 12.0)
    for aa_, bb_ in V.runs(m, Rr['t'], min_s=1.0):
        Or = O[aa_:bb_]
        ed = np.r_[0, np.flatnonzero(np.diff(Or.astype(int)) != 0) + 1, bb_ - aa_]
        for k in range(len(ed) - 1):
            if Or[ed[k]] and np.max(np.abs(zz[aa_ + ed[k]:aa_ + ed[k + 1]])) >= LEVEL / 4:
                durs.append((ed[k + 1] - ed[k]) / FS)
    del Rr
durs = np.array(durs)
a = ax[1, 0]
bins = np.logspace(np.log10(0.02), np.log10(8), 34)
a.hist(durs, bins=bins, color=C[0], edgecolor=SURF, linewidth=0.8)
a.set_xscale('log')
a.axvline(0.30, color=C[1], lw=2.0)
a.annotate(f'0.30 s: {100*np.mean(durs<0.3):.0f}% of on-intervals are shorter\n(the chatter class)',
           (0.30, a.get_ylim()[1] * 0.92), xytext=(6, 0), textcoords='offset points', color=C[1], fontsize=8, va='top')
a.axvline(np.median(durs), color=INK2, lw=1.4, ls=(0, (4, 3)))
a.annotate(f'median {np.median(durs):.2f} s', (np.median(durs), a.get_ylim()[1] * 0.55), xytext=(6, 0),
           textcoords='offset points', color=INK2, fontsize=8)
a.set_xlabel('duration the term stays ON  [s]'); a.set_ylabel(f'count  (n = {len(durs)})')
a.set_title('C. Dwell between flips, effective ON-intervals, v < 12 m/s, 5 torque routes',
            loc='left', fontsize=8.6, color=INK)

# ---------------- P4: reach vs band cost ----------------
SW = json.load(open(f'{OUT}/fr_sweep.json'))['pooled']
a = ax[1, 1]
gx, gy, gl = [], [], []
for A_ in (0.5, 1.0, 2.0, 4.0, 8.0):
    for Rq in (1.0, 2.0, 4.0, 8.0):
        k = f'A{A_}_R{Rq}'
        gx.append(SW[k]['reach_bk_2_8']); gy.append(SW[k]['z_shake']); gl.append(f'A{A_:g} R{Rq:g}')
px, py, pl = [], [], []
for rc in (0.05, 0.1, 0.2, 0.4):
    k = f'A1.0_R2.0_zout{rc}'
    px.append(SW[k]['reach_bk_2_8']); py.append(SW[k]['z_shake']); pl.append(f'RC {rc:g}')
a.plot(gx, gy, 'o', ms=8, mfc=C[0], mec=SURF, mew=1.6, label='stateless: the two tanh scales')
a.plot([SW['A1.0_R2.0']['reach_bk_2_8']] + px, [SW['A1.0_R2.0']['z_shake']] + py, '-o', color=C[1], lw=2.0,
       ms=8, mfc=C[1], mec=SURF, mew=1.6, label='A1 R2 + post-filter on z_out')
a.annotate('A1 R2\nas designed', (SW['A1.0_R2.0']['reach_bk_2_8'], SW['A1.0_R2.0']['z_shake']),
           xytext=(6, 4), textcoords='offset points', fontsize=8, color=INK2)
for x_, y_, l_ in zip(px, py, pl):
    a.annotate(l_, (x_, y_), xytext=(5, -9), textcoords='offset points', fontsize=7.6, color=C[1])
for x_, y_, l_ in zip(gx, gy, gl):
    if l_ in ('A8 R8', 'A0.5 R1', 'A4 R4'):
        a.annotate(l_, (x_, y_), xytext=(5, 4), textcoords='offset points', fontsize=7.6, color=C[0])
a.set_xlabel('reach at breakaway, median of route medians  [torque]')
a.set_ylabel('z_out 1.8-3.5 Hz RMS  [torque]')
a.set_title('D. Cost vs reach (down-right is better): the tanh scales trade 1:1, the post-filter does not',
            loc='left', fontsize=8.6, color=INK)
a.legend(loc='upper left', fontsize=8)
a.axvline(0.0133, color=MUT, lw=1.2, ls=(0, (2, 2)))
a.annotate('0.0133 = the measured\noutward shortfall', (0.0133, a.get_ylim()[0]), xytext=(4, 14),
           textcoords='offset points', fontsize=7.6, color=MUT)

fig.tight_layout(pad=1.4)
fig.savefig(f'{OUT}/fig_fliprate.png', dpi=140)
print('wrote', f'{OUT}/fig_fliprate.png', '| durs n', len(durs), 'p50', round(float(np.median(durs)), 3),
      'frac<0.3', round(float(np.mean(durs < 0.3)), 3), '| psd sec', round(sec, 1))
