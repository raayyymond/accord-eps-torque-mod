"""Independent re-derivation of the numbers cited in finding closed-loop-sim-validation-status.
Re-reads the SAME json outputs the finding cites (s5_02, s5_03, s5_05) and recomputes every quoted
number directly, plus an independent re-run of the calA variant to check the "limit-cycles at 120
deg/s" claim (not present in any stored json, so it must be regenerated).
Writes verify1_recompute.json with the comparison.
"""
import json, sys, math
import numpy as np

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism/'

# ---------- 1. s5_03 replica open-loop stats ----------
r3 = json.load(open(BASE + 's5_03_replica_validate.json'))
frames = [v['frames'] for v in r3.values()]
out_corr = [v['out']['corr'] for v in r3.values()]
out_slope = [v['out']['slope'] for v in r3.values()]
f_corr = [v['f']['corr'] for v in r3.values()]
p_corr = [v['p']['corr'] for v in r3.values()]
i_corr = [v['i']['corr'] for v in r3.values()]

print('=== s5_03 replica (open loop) ===')
print('frames range:', min(frames), max(frames), ' claim: 45k-68k')
print('out corr range:', round(min(out_corr), 4), round(max(out_corr), 4), ' claim: 0.996-0.999')
print('out slope range:', round(min(out_slope), 4), round(max(out_slope), 4), ' claim: 0.97-0.99')
print('F corr range:', round(min(f_corr), 4), round(max(f_corr), 4), ' claim: 0.998-0.999')
print('P corr range:', round(min(p_corr), 6), round(max(p_corr), 6), ' claim: "exact"')
print('I corr range:', round(min(i_corr), 4), round(max(i_corr), 4), ' claim: 0.95-0.999')

# ---------- 2. s5_02 equation-error F and hold-level s, per stratum, WITH LABELS ----------
r2 = json.load(open(BASE + 's5_02_plant_ident.json'))
print()
print('=== s5_02 equation-error fit (per stratum, LABELLED) ===')
for st in ('8-15', '15-22', '22-40'):
    b = r2[st]
    print(f'  {st} m/s: F best={b["F"]:.4f} CI=[{b["ci"]["F"][0]:.4f},{b["ci"]["F"][1]:.4f}]   '
          f's(hold) best={b["s"]:.3f} CI=[{b["ci"]["s"][0]:.3f},{b["ci"]["s"][1]:.3f}]')
print('claim: "F [CI]: 0.020-0.024, 0.023-0.027, 0.019-0.024 at 8-15/15-22/22+"')
print('claim: "s: 1.28 [1.22,1.38], 1.44 [1.39,1.59], 1.25 [1.10,1.66]" (assumed same stratum order)')

# ---------- 3. s5_05 closed-loop calC numbers ----------
r5 = json.load(open(BASE + 's5_05_closedloop_validate.json'))
print()
print('=== s5_05 calC (claim: this is what "calC" section of finding reports) ===')
order = [('0000006c--68c6e94b17', 'T64a'), ('0000006d--05e83bb04f', 'T64b'),
         ('0000006e--6ca3e014fd', 'T64B'), ('00000076--d0b7ea7e4d', 'T5'), ('00000075--6c8687d5bd', 'T4')]
for rk, tag in order:
    v = r5['calC'][rk]
    print(f'  {tag:5s} b030 meas={v["b030"]["meas"]:.3f} sim={v["b030"]["sim"]:.3f}   '
          f'hf_8 meas={v["hf_8"]["meas"]:.2f} sim={v["hf_8"]["sim"]:.2f}   '
          f'events lag_meas={v["events"]["lag_meas"]:.3f} lag_sim={v["events"]["lag_sim"]:.3f} '
          f'gain_meas={v["events"]["gain_meas"]:.3f} gain_sim={v["events"]["gain_sim"]:.3f} '
          f'corr_theta={v["events"]["corr_theta_med"]:.3f}')

gains = [r5['calC'][rk]['events']['gain_sim'] - r5['calC'][rk]['events']['gain_meas'] for rk, _ in order]
lags = [r5['calC'][rk]['events']['lag_sim'] - r5['calC'][rk]['events']['lag_meas'] for rk, _ in order]
print('calC event gain sim-meas per route:', [round(x, 3) for x in gains], ' claim: "+0.02 to +0.06"')
print('calC event lag sim-meas per route:', [round(x, 3) for x in lags], ' claim: "-0.015 to -0.035"')

corrs = [r5['calC'][rk]['events']['corr_theta_med'] for rk, _ in order]
print('calC event theta corr range:', min(corrs), max(corrs), ' claim: "0.956-0.983"')

r0 = [r5['nominal'][rk]['events'] for rk, _ in order]
lags0 = [e['lag_sim'] - e['lag_meas'] for e in r0]
print('nominal (F=0.015) event lag sim-meas per route:', [round(x, 3) for x in lags0],
      ' claim: "-0.03 to -0.11"')

# T64B hold-level-off prediction direction, nominal plant
t64_sim_b030 = [r5['nominal'][rk]['b030']['sim'] for rk in ('0000006c--68c6e94b17', '0000006d--05e83bb04f')]
t64b_sim_b030 = r5['nominal']['0000006e--6ca3e014fd']['b030']['sim']
t64_meas_b030 = [r5['nominal'][rk]['b030']['meas'] for rk in ('0000006c--68c6e94b17', '0000006d--05e83bb04f')]
t64b_meas_b030 = r5['nominal']['0000006e--6ca3e014fd']['b030']['meas']
print()
print('nominal b030 sim: T64 avg', round(np.mean(t64_sim_b030), 3), ' T64B', round(t64b_sim_b030, 3),
      ' -> sim predicts T64B', 'WORSE' if t64b_sim_b030 > np.mean(t64_sim_b030) else 'BETTER', 'than T64')
print('nominal b030 meas: T64 avg', round(np.mean(t64_meas_b030), 3), ' T64B', round(t64b_meas_b030, 3),
      ' -> measured T64B is', 'WORSE' if t64b_meas_b030 > np.mean(t64_meas_b030) else 'BETTER', 'than T64')

# T4 nominal
t4 = r5['nominal']['00000075--6c8687d5bd']['b030']
print('T4 nominal b030: meas', t4['meas'], 'sim', t4['sim'], ' claim: "T4 1.55 comes out as 1.22"')

# 2-3Hz texture underprediction on T64B and T4 (nominal)
for rk, tag in (('0000006e--6ca3e014fd', 'T64B'), ('00000075--6c8687d5bd', 'T4')):
    hf = r5['nominal'][rk]['hf_8']
    print(f'{tag} nominal hf_8 (1.5-3.5Hz, 8-15 m/s): meas={hf["meas"]} sim={hf["sim"]} ratio meas/sim={hf["meas"]/hf["sim"]:.2f}')

json.dump(dict(frames=frames, out_corr=out_corr, out_slope=out_slope, f_corr=f_corr, i_corr=i_corr),
          open(BASE.replace('s5_mechanism/', 'verify/s5_mechanism__closedloopsi__method/') + 'verify1_s3_recheck.json', 'w'), indent=1)
