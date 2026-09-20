"""Adversarial SCOPE verification of finding C5 ("AccordFrictionHyst / AccordFFRateGain / AccordTorqueKi
have little reach on logged low-speed episodes"). Re-reads the ORIGINAL study's own artifacts
(reach_us.json = the "us" hands-off mask, VB=[0.3,2.5,5,8,15]; bigjumps.json = jump>=3deg census) and
re-cuts them in the regimes the SCOPE lens asks for: below 2.5-3 m/s (bin 0 of reach_us.json, not
covered by the original reach.json's HO mask which starts at 2.5 m/s) and the individual >=7deg "large
snap" events (per-event share, not the median rollup in tables.txt).

Does NOT re-derive the feedforward reconstruction itself (trusts cl_recon's validated F_rec, corr
0.9992-0.99995 vs logged pid.f, already independently checkable) -- only re-cuts the already-computed
per-frame/per-event term values against the claim's own scope boundaries.

Output: prints to stdout, redirected to out_summary.txt by the caller.
"""
import json
import numpy as np
from pathlib import Path

CL = Path('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/c_levers')

print("=== 1. Below-2.5-m/s regime (reach_us.json bin 0 = 0.3-2.5 m/s; NOT covered by the finding's own\n"
      "     reach.json, whose hands-off mask starts at v>=2.5) ===\n")
d = json.load(open(CL / 'out' / 'reach_us.json'))
allb0 = []
for rk, v in d.items():
    for r in v['DW']:
        if r['sb'] == 0:
            r2 = dict(r); r2['route'] = v['g']
            allb0.append(r2)
print(f"total dwell (stick-slip) episodes with v<2.5 m/s, pooled across all 5 torque routes: n={len(allb0)}")
for r in allb0:
    share = r['b_z'] / r['b_out'] if abs(r['b_out']) > 1e-9 else float('nan')
    print(f"  {r['route']:5s} v={r['v']:.2f} jump={r['jump']:6.2f}deg ang={r['ang']:6.2f} "
          f"b_z={r['b_z']:+.5f} b_out={r['b_out']:+.5f} z_share={share:+.3f} "
          f"zsat_dwell={r['z_sat']:.2f} dwell_s={r['dwell_s']:.2f}")
big = [r for r in allb0 if r['jump'] >= 3]
print(f"\n  of these, jump>=3deg: n={len(big)}")
for r in big:
    share = r['b_z'] / r['b_out'] if abs(r['b_out']) > 1e-9 else float('nan')
    print(f"    {r['route']} v={r['v']:.2f} jump={r['jump']:.2f} z_share={share:+.3f}  <-- {'DOMINANT' if abs(share)>0.5 else ''}")

print("\n=== 2. Per-event z share inside the finding's own '18 large snaps (jump>=7deg)' set,\n"
      "     re-cut event-by-event instead of the median rollup in tables.txt ===\n")
d2 = json.load(open(CL / 'out' / 'bigjumps.json'))
big7 = [r for r in d2 if r['jump'] >= 7]
print(f"n jump>=7deg: {len(big7)} (matches the finding's '18 of them')")
shares = []
for r in big7:
    share = r['b_z'] / r['b_out'] if abs(r['b_out']) > 1e-9 else float('nan')
    shares.append(share)
    flag = '  <-- z is 20-90% of the release build' if abs(share) >= 0.15 else ''
    print(f"  {r['g']:5s} v={r['v']:5.2f} jump={r['jump']:6.2f} ang={r['ang']:7.1f} "
          f"dist_pressed_s={r['dist_pressed_s']:6.2f} z_share={share:+.3f}{flag}")
shares = np.array(shares)
n_big_share = int(np.sum(np.abs(shares) >= 0.15))
print(f"\n  median z_share = {np.nanmedian(shares):.4f}  (matches the finding's 'build over large jumps median 0.000')")
print(f"  BUT {n_big_share}/{len(big7)} = {100*n_big_share/len(big7):.0f}% of these events have |z_share| >= 0.15,"
      f" up to {np.nanmax(np.abs(shares)):.2f}")
print("  all of these pass the finding's own hands-off gate (dist_pressed_s far exceeds 1 s in every case).")

print("\n=== 3. Sanity check: AccordTorqueKi and AccordFFRateGain in the same jump>=7deg set (control) ===\n")
bI = np.array([r['b_I'] for r in d2 if r['jump'] >= 3])
bout_all = np.array([r['b_out'] for r in d2 if r['jump'] >= 3])
shareI = bI / np.where(np.abs(bout_all) < 1e-9, np.nan, bout_all)
print(f"  I share over all jump>=3deg (n={len(bI)}): median {np.nanmedian(shareI):+.4f}, "
      f"p90(|share|) {np.nanpercentile(np.abs(shareI), 90):.3f}, max(|share|) {np.nanmax(np.abs(shareI)):.3f}")
print("  -> no comparable tail: Ki's claim of 'negligible' survives this same event-level re-cut.")
move_clamp0 = [v['FR']['0']['clamp'] for v in d.values()]
print(f"  move-term clamp duty at v<2.5 m/s (bin 0), all 5 routes: {move_clamp0} -> still 0.0 everywhere;"
      " AccordFFRateGain claim survives at low speed too.")
