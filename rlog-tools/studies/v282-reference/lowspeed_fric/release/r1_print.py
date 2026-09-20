import json, sys
R = json.load(open('out/r1_decomp.json'))
LAG = sys.argv[1] if len(sys.argv) > 1 else '+300ms'
print('=== MATCHED torque vs V282, delta over', LAG, 'from breakaway (sign-aligned, output torque) ===')
for key, d in R['matched'].items():
    print(f"\n-- {key}  n_pairs={d['n_pairs']} v={d['v_t']}/{d['v_r']} |aa|={d['aa_t']}/{d['aa_r']} dwell={d['dwell_t']}/{d['dwell_r']}")
    print(f"  {'term':<8}{'torque':>12}{'V282':>12}{'diff':>12}  {'diff CI':>22}")
    for k in ('cmd', 'P', 'I', 'F'):
        x = d[k][LAG]
        print(f"  {k:<8}{x['torque']['p50']:>12.5f}{x['v282']['p50']:>12.5f}{x['diff']['p50']:>12.5f}  [{x['diff']['ci'][0]:.5f},{x['diff']['ci'][1]:.5f}]")
    n = d['net'][LAG]
    print(f"  {'net':<8}{n['torque']['p50']:>12.5f}{n['v282']['p50']:>12.5f}")
    print(f"  net@bk  {d['net_at_bk']['torque']['p50']:>12.5f}{d['net_at_bk']['v282']['p50']:>12.5f}")
    for kk in ('excess_impulse_300ms', 'excess_impulse_500ms'):
        e = d[kk]
        print(f"  {kk:<22}{e['torque']['p50']:>10.5f} [{e['torque']['ci'][0]:.5f},{e['torque']['ci'][1]:.5f}]   V282 {e['v282']['p50']:>9.5f} [{e['v282']['ci'][0]:.5f},{e['v282']['ci'][1]:.5f}]   ratio {e['ratio']}")

print('\n=== PER-GROUP deltas (all episodes in band), sub-terms for torque ===')
for key, d in R['delta_by_group'].items():
    ks = [k for k in ('cmd', 'P', 'I', 'F', 'hold_ff', 'move', 'z', 'rl', 'dob') if k in d]
    print(f"\n-- {key}  n={d['cmd'][LAG]['n']}")
    print('  ' + ''.join(f'{k:>10}' for k in ks))
    print('  ' + ''.join(f"{d[k][LAG]['p50']:>10.5f}" for k in ks))
    print('  CI' + ''.join(f"[{d[k][LAG]['ci'][0]:.4f},{d[k][LAG]['ci'][1]:.4f}]" for k in ks))
    print('  level@bk ' + str({k: d['level_at_bk'][k] for k in ks}))
    print(f"  net delta {d['net_cmd_minus_hold_at_actual'][LAG]['p50']:.5f}  net@bk {d['net_level_at_bk']['p50']:.5f}"
          f"  excess300 {d['excess_impulse_300ms_F0.02']['p50']:.5f}  excess500 {d['excess_impulse_500ms_F0.02']['p50']:.5f}")
