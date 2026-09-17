import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
R = json.load(open(HERE / "v_results.json"))

print("=== 1. la_yaw re-check ===")
for r in R["la_yaw_check"]:
    print(f"  {r['route']:24s} {r['group']:8s} std={r['std']:.6f} finite={r['finite_frac']:.3f}")

print("\n=== 2. band |H| act vs pose, by speed bin (grouped, sec-weighted) ===")
by = {}
for c in R["band_cells"]:
    k = (c["group"], c["vbin"], c["band"])
    by.setdefault(k, []).append(c)
groups = sorted(set(c["group"] for c in R["band_cells"]))
vbins = ["0-8", "8-15", "15-22", ">22"]
bands = ["0.05-0.15", "0.15-0.3", "0.3-0.6", "0.6-1.2", "1.2-2.5"]
for vb in vbins:
    print(f"\n -- speed {vb} m/s --")
    for band in bands:
        row = []
        for g in groups:
            k = (g, vb, band)
            if k not in by:
                continue
            cells = by[k]
            sec = sum(c["sec"] for c in cells)
            Ha = sum(c["H_act"] * c["sec"] for c in cells) / sec
            Hp = sum(c["H_pose"] * c["sec"] for c in cells) / sec
            coha = sum(c["coh_act"] * c["sec"] for c in cells) / sec
            cohp = sum(c["coh_pose"] * c["sec"] for c in cells) / sec
            row.append(f"{g}:Ha={Ha:.2f}(coh{coha:.2f}) Hp={Hp:.2f}(coh{cohp:.2f}) d={Hp-Ha:+.2f} n={sec:.0f}s")
        if row:
            print(f"   {band:10s} " + " | ".join(row))

print("\n=== 3. low-speed (<15) amplitude-stratified secant gain, act vs pose ===")
for r in sorted(R["amp_strat"], key=lambda r: (r["group"], r["lo"])):
    print(f"  {r['group']:8s} {r['route']:24s} |model| {r['lo']:.1f}-{r['hi']:.1f}  sec={r['sec']:6.0f}  "
          f"secant_act={r['secant_act']:.2f} secant_pose={r['secant_pose']:.2f} "
          f"d={r['secant_pose']-r['secant_act']:+.2f}  rms(a-p)={r['rms_act_minus_pose']:.3f}")

print("\n=== 4. event-window act vs pose disagreement, by group ===")
ev = R["events"]
for g in groups:
    for kind in ("jerk", "accel"):
        sub = [e for e in ev if e["group"] == g and e["kind"] == kind]
        if not sub:
            continue
        rel = np.array([e["rel_disagree"] for e in sub])
        corr = np.array([e["corr_act_pose"] for e in sub if np.isfinite(e["corr_act_pose"])])
        lo_v = np.array([e["v"] for e in sub]) < 15
        print(f"  {g:8s} {kind:6s} n={len(sub):4d}  rel_disagree median={np.nanmedian(rel):.2f} "
              f"p90={np.nanpercentile(rel,90):.2f}  corr median={np.nanmedian(corr) if len(corr) else float('nan'):.2f}  "
              f"  n<15m/s={lo_v.sum()}  rel_disagree<15 median={np.nanmedian(rel[lo_v]) if lo_v.sum() else float('nan'):.2f}"
              f"  rel_disagree>=15 median={np.nanmedian(rel[~lo_v]) if (~lo_v).sum() else float('nan'):.2f}")

print("\n=== 4b. worst-disagreement events (top 15 by rel_disagree) ===")
worst = sorted(ev, key=lambda e: -e["rel_disagree"])[:15]
for e in worst:
    print(f"  {e['group']:8s} {e['route']:24s} {e['kind']:6s} v={e['v']:.1f} la_peak={e['la_peak']:.2f} "
          f"rel_disagree={e['rel_disagree']:.2f} corr={e['corr_act_pose']:.2f}")
