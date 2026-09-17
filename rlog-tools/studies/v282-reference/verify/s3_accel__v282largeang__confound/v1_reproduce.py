"""Reproduce the exact numbers in the finding: candidates, full-window press overlap, fully-hands-off count,
per-event window press fraction. One route in RAM at a time (per RAM discipline)."""
import sys, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
import v282cmp as V
import s3turns as T

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s3_accel__v282largeang__confound/'

rows = []
tot_candidates = 0
tot_kept = 0
n_any_press_in_window = 0
n_fully_hands_off = 0
for rk in V.ROUTES:
    R = T.prep(rk)
    evs, rej = T.find_turns(R)
    tot_candidates += rej["candidates"]
    tot_kept += len(evs)
    for e in evs:
        w0, w1 = e["w0"], e["w1"]
        win_press = R["pressed"][w0:w1]
        any_press = bool(win_press.any())
        frac_win = float(win_press.mean())
        n_any_press_in_window += int(any_press)
        n_fully_hands_off += int(not any_press)
        rows.append(dict(rk=rk, group=R["group"], v=e["v"], P=e["P"], any_press_window=any_press,
                          frac_press_window=frac_win, press_frac_metric=e["press_frac"]))
    print(rk, R["group"], "candidates", rej["candidates"], "kept", len(evs), flush=True)
    del R

print()
print("total candidates (pre speed/edge/overlap/gap/disengaged filtering):", tot_candidates)
print("total kept events:", tot_kept)
print("events with >=1 pressed frame anywhere in [build_start-1s, return_end+1s]:", n_any_press_in_window, "/", tot_kept)
print("events fully hands-off in that window:", n_fully_hands_off, "/", tot_kept)

by_group = {}
for r in rows:
    by_group.setdefault(r["group"], []).append(r)
print()
print("fully-hands-off count by group:")
for g, rs in by_group.items():
    n_off = sum(1 for r in rs if not r["any_press_window"])
    print(f"  {g:8s} n={len(rs):3d} fully_hands_off={n_off}")

json.dump(dict(rows=rows, tot_candidates=tot_candidates, tot_kept=tot_kept,
               n_any_press=n_any_press_in_window, n_hands_off=n_fully_hands_off),
          open(OUT + 'v1_reproduce.json', 'w'), indent=1, default=float)
