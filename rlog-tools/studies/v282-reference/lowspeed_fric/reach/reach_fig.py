"""reach figures.  Palette: dataviz reference categorical slots 1-3 (validated all-pairs, light)."""
import os, sys, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
sys.path.insert(0, BASE + '/lowspeed/a_stickslip'); sys.path.insert(0, BASE)
from sslib import k_of_v  # noqa: E402
OUT = os.path.dirname(os.path.abspath(__file__)) + '/out'
S1, S2, S3 = '#2a78d6', '#eb6834', '#1baf7a'
INK, INK2, MUT, GRID, SURF = '#0b0b0b', '#52514e', '#8a8984', '#e4e3df', '#fcfcfb'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2,
                     'xtick.color': INK2, 'ytick.color': INK2, 'figure.facecolor': SURF,
                     'axes.facecolor': SURF, 'axes.titlecolor': INK, 'savefig.facecolor': SURF})


def style(ax):
    ax.grid(True, color=GRID, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)


RT = json.load(open(OUT + '/reach_table.json'))
RS = json.load(open(OUT + '/reach_slope.json'))
RI = json.load(open(OUT + '/reach_intercept.json'))
RA = json.load(open(OUT + '/reach_asym.json'))

# ---------------- FIG 1: reach is slope-bound ----------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.8, 4.5))
T = [r for r in RT['table'] if r['gate'] == 'g8_12']
sl = np.array([r['slope'] for r in T]); rc = np.array([r['reach_acc_2_8'] for r in T])
fc = np.array([r['f'] for r in T])
sc = a1.scatter(sl, rc, c=fc, cmap='Blues', vmin=0.008, vmax=0.048, s=46, lw=0.9,
                edgecolor=SURF, zorder=3)
xs = np.linspace(0, 0.031, 50)
L = RS['law']
a1.plot(xs, L['fit_slope'] * xs + L['fit_intercept'], color=INK2, lw=1.6, ls='--', zorder=2)
kmed = k_of_v(6.0)
for mult, lab in [(1.0, '1.0x'), (1.8, '1.8x'), (2.4, '2.4x')]:
    a1.axvline(mult * kmed, color=S2, lw=1.4, zorder=2)
    a1.text(mult * kmed, 1.47, lab, color=S2, ha='center', va='bottom', fontsize=8)
a1.text(0.0305, 1.55, 'slope / hold stiffness k(6 m/s)', color=S2, ha='right', va='bottom', fontsize=8)
a1.axhline(1.0, color=S3, lw=1.8, zorder=2)
a1.text(0.0155, 1.02, 'shortfall fully supplied', color=S3, ha='left', va='bottom', fontsize=8)
i_t = [i for i, r in enumerate(T) if r['f'] == 0.015 and r['band'] == 3.0][0]
a1.scatter([sl[i_t]], [rc[i_t]], s=150, facecolor='none', edgecolor=INK, lw=1.8, zorder=5)
a1.annotate('as flown\n0.015 / 3.0 deg\n27 %', (sl[i_t], rc[i_t]), xytext=(0.0068, 0.72),
            color=INK, fontsize=8.5, arrowprops=dict(arrowstyle='-', color=INK, lw=1))
a1.set_xlabel('slope = friction ceiling / band   (torque per deg of desired-angle travel)')
a1.set_ylabel('fraction of the measured 0.033 shortfall\nsupplied through the dwell  (median, 2-8 m/s)')
a1.set_title('Reach is set by the SLOPE, not the ceiling', loc='left', fontweight='bold')
a1.set_xlim(0, 0.0315); a1.set_ylim(0, 1.65); style(a1)
cb = fig.colorbar(sc, ax=a1, pad=0.015, fraction=0.045)
cb.set_label('ceiling (torque)', color=INK2, fontsize=8); cb.outline.set_visible(False)
cb.ax.tick_params(colors=INK2, labelsize=7.5)

ISO = RS['ceiling_inertness_at_constant_slope']
for q, (kk, colr) in enumerate(zip(['slope_0.005', 'slope_0.01', 'slope_0.015'], [S1, S2, S3])):
    L_ = ISO[kk]
    x = [e['f'] for e in L_]; y = [e['reach_acc'] for e in L_]
    a2.plot(x, y, '-o', color=colr, lw=2, ms=8, mec=SURF, mew=1.2, zorder=3)
    a2.annotate(f"slope {kk.split('_')[1]}", (x[-1], y[-1]), xytext=(4, 3), textcoords='offset points',
                color=colr, fontsize=8.5, fontweight='bold')
a2.set_xlabel('friction ceiling (torque)')
a2.set_ylabel('fraction of the 0.033 shortfall supplied')
a2.set_title('At constant slope the ceiling is nearly inert', loc='left', fontweight='bold')
a2.set_ylim(0, 1.0); a2.set_xlim(0.010, 0.050); style(a2)
a2.text(0.0125, 0.06, '2.7x ceiling at slope 0.005 buys\n27 % -> 29 % of the shortfall',
        color=INK2, fontsize=8.5)
fig.suptitle('Friction-hysteresis REACH on 145 logged low-speed dwells (2-8 m/s, 5 torque-mode routes)',
             fontsize=10.5, color=INK, x=0.012, ha='left', y=0.985)
fig.tight_layout(rect=[0, 0, 1, 0.945])
fig.savefig(OUT + '/fig1_reach_slope_bound.png', dpi=170)
plt.close(fig)

# ---------------- FIG 2: the asymmetry ----------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.8, 4.5))
M = RA['structure']['2-8']
m2 = M['M2 (cmd - hold_aa) ~ Fa*sj + d*sj*toward + c']
m3 = M['M3 (cmd - hold_aa - 0.020*sign(aa)) ~ Fa*sj + d*sj*toward + c']
rows = [('as logged\n(fork hold map only)', m2['away'], m2['toward'], S1),
        ('+ 0.020 x sign(angle)\n(the fork\'s own intercept)', m3['away'], m3['toward'], S3)]
for q, (lab, aw, tw, colr) in enumerate(rows):
    y = 1 - q
    a1.plot([tw, aw], [y, y], color=colr, lw=3.5, solid_capstyle='round', zorder=3)
    a1.scatter([tw, aw], [y, y], s=90, color=colr, zorder=4, ec=SURF, lw=1.4)
    a1.text(tw, y + 0.16, f'toward centre {tw:+.4f}', color=colr, fontsize=8.5, ha='left', va='bottom')
    a1.text(aw, y - 0.16, f'away from centre {aw:+.4f}', color=colr, fontsize=8.5, ha='right', va='top')
    a1.text(-0.012, y, lab, color=INK, fontsize=8.5, ha='right', va='center')
    a1.scatter([(aw + tw) / 2], [y], marker='|', s=260, color=INK, zorder=5, lw=1.6)
a1.axvline(0, color=MUT, lw=1.2, zorder=2)
a1.set_xlim(-0.055, 0.075); a1.set_ylim(-0.75, 1.75)
a1.set_yticks([])
a1.set_xlabel('command at breakaway minus the fork hold map, aligned with the jump (torque)')
a1.set_title('The release band is OFF-CENTRE by the intercept the hold map lacks',
             loc='left', fontweight='bold')
a1.text(0.073, 1.62, 'tick = band centre', color=INK, fontsize=8, ha='right')
style(a1); a1.grid(axis='y', visible=False)

LM = RI['last_motion']['2-8']['C: Fa*sj + A1*sign(aa) + A2*s_prev + c']
bars = [('half-width\nFa', LM['Fa'], MUT),
        ('angle-sign intercept\nA x sign(angle)', LM['A_aa'], S2),
        ('last-motion memory\nA x sign(prev motion)', LM['A_prev'], S1)]
for q, (lab, vc, colr) in enumerate(bars):
    est, ci = vc[0], vc[1]
    a2.barh(q, est, height=0.5, color=colr, zorder=3)
    a2.plot(ci, [q, q], color=INK, lw=1.4, zorder=4)
    a2.text(max(est, ci[1]) + 0.0018, q, f'{est:.4f}  [{ci[0]:.4f}, {ci[1]:.4f}]', va='center', color=INK, fontsize=8.5)
a2.axvline(0.015, color=S3, lw=2, ls='--', zorder=2)
a2.text(0.0152, 2.42, 'AccordFrictionHyst\nas flown = 0.015', color=S3, fontsize=8.5, va='top')
a2.set_yticks(range(3)); a2.set_yticklabels([b[0] for b in bars], fontsize=8.5)
a2.set_xlim(0, 0.068); a2.set_ylim(-0.5, 2.7)
a2.set_xlabel('torque, fitted on 145 low-speed dwells (route-cluster bootstrap 95 % CI)')
a2.set_title('A +/-friction operator carries only the last-motion half', loc='left', fontweight='bold')
style(a2); a2.grid(axis='y', visible=False)
fig.suptitle('The measured asymmetry: release needs 0.053 away from centre but 0.014 back toward it',
             fontsize=10.5, color=INK, x=0.012, ha='left', y=0.985)
fig.tight_layout(rect=[0, 0, 1, 0.945])
fig.savefig(OUT + '/fig2_asymmetry.png', dpi=170)
plt.close(fig)

# ---------------- FIG 3: what the finalists buy, by direction ----------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.8, 4.5))
CANDS = [('as flown\n0.015 / 3.0 flat', RS['kprop']['flat_today|f0.015'], 1.14),
         ('C1  f 0.027, band = f/(1.8k)\n7.1 / 5.4 / 3.4 / 2.9 deg', RS['kprop']['kprop_M1.8|f0.027'], 1.80),
         ('C2  f 0.027, band = f/(2.4k)\n5.4 / 4.0 / 2.6 / 2.2 deg', RS['kprop']['kprop_M2.4|f0.027'], 2.40),
         ('symmetric 0.033 / 2.0 deg', None, 0.0165 / k_of_v(6.0)),
         ('0.020 / 2.0 deg + 0.020 intercept', None, 0.010 / k_of_v(6.0))]
SYM = RI['variant_reach']["(0.033, 2.0, 'g8_12', 0.0, 1.0)"]
INT = RI['variant_reach']["(0.02, 2.0, 'g8_12', 0.02, 1.0)"]
dat = []
for q, (lab, d, ratio) in enumerate(CANDS):
    src = d if d is not None else (SYM if q == 3 else INT)
    dat.append((lab, src['2-8|away']['dt'], src['2-8|away']['dt_p90'],
                src['2-8|toward']['dt'], src['2-8|toward']['dt_p90'], ratio,
                src['2-8|all']['reach_acc']))
y = np.arange(len(dat))
a1.barh(y + 0.19, [d[1] for d in dat], height=0.34, color=S1, zorder=3, label='away from centre (n=52)')
a1.barh(y - 0.19, [d[3] for d in dat], height=0.34, color=S2, zorder=3, label='toward centre (n=93)')
for q, d in enumerate(dat):
    a1.plot([d[1], d[2]], [q + 0.19, q + 0.19], color=INK, lw=1.2, zorder=4)
    a1.plot([d[3], d[4]], [q - 0.19, q - 0.19], color=INK, lw=1.2, zorder=4)
    a1.text(d[2] + 0.015, q + 0.19, f'{d[1]:.2f} s', va='center', color=INK, fontsize=8)
    a1.text(d[4] + 0.015, q - 0.19, f'{d[3]:.2f} s' + ('  (later, not earlier)' if q == 4 else ''),
            va='center', color=INK, fontsize=8)
a1.set_yticks(y); a1.set_yticklabels([d[0] for d in dat], fontsize=8.5)
a1.set_xlabel('how much EARLIER the logged command reaches the level that released\nthis wheel (median, thin line to p90; seconds)')
a1.set_title('Earlier crossing, by direction', loc='left', fontweight='bold')
a1.legend(frameon=False, fontsize=8.5, loc='lower right')
a1.set_xlim(0, 1.25); style(a1); a1.grid(axis='y', visible=False)

a2.scatter([d[5] for d in dat], [d[6] for d in dat], s=0)
for q, d in enumerate(dat):
    colr = S1 if q == 0 else (S3 if q in (1, 2) else S2)
    a2.scatter([d[5]], [d[6]], s=130, color=colr, zorder=4, ec=SURF, lw=1.4)
    a2.annotate(d[0].split('\n')[0], (d[5], d[6]), xytext=(7, -4), textcoords='offset points',
                color=colr, fontsize=8.5, fontweight='bold')
a2.axvline(1.14, color=MUT, lw=1.2, ls=':', zorder=2)
a2.axvline(2.38, color=MUT, lw=1.2, ls=':', zorder=2)
a2.text(1.10, 0.03, "today's ratio at 6 m/s", color=MUT, fontsize=8, rotation=90, va='bottom', ha='right')
a2.text(2.34, 0.03, "today's worst ratio (2 m/s)", color=MUT, fontsize=8, rotation=90, va='bottom', ha='right')
a2.axhline(1.0, color=S3, lw=1.6, zorder=2)
a2.text(0.78, 1.01, 'shortfall fully supplied', color=S3, fontsize=8, va='bottom')
a2.set_xlabel('over-delivery: slope / k, at 6 m/s (median dwell speed)')
a2.set_ylabel('fraction of the 0.033 shortfall supplied')
a2.set_title('Reach bought against the over-delivery it costs', loc='left', fontweight='bold')
a2.set_xlim(0.7, 4.3); a2.set_ylim(0, 1.15); style(a2)
fig.suptitle('Finalists: every candidate is faded to today\'s values by 12 m/s, so the highway is untouched by construction',
             fontsize=10.5, color=INK, x=0.012, ha='left', y=0.985)
fig.tight_layout(rect=[0, 0, 1, 0.945])
fig.savefig(OUT + '/fig3_finalists.png', dpi=170)
plt.close(fig)
print('wrote 3 figures')
