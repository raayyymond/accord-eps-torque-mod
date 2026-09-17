"""t03b: regenerate out/t03_turns.json (s3turns.find_turns, default args) -- t03's first run crashed while writing it."""
import sys, json
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/fill_texturetermd')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
import ttd, s3turns
out = {}
for rk in ttd.TORQUE:
    P = s3turns.prep(rk); evs, _ = s3turns.find_turns(P); del P
    out[rk] = [(int(e['w0']), int(e['w1']), float(e['v']), float(e['P'])) for e in evs]
    print(rk, len(evs))
json.dump(out, open(ttd.OUT + 't03_turns.json', 'w'))
