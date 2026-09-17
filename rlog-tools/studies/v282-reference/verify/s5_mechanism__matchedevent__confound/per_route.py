"""Per-torque-route breakdown: does the lag/texture effect hold in EACH T64 route individually,
or is it driven by only one of the two (T64 has just 46 events total across 2 routes)?"""
import json
import numpy as np

SRC = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism/s5_04_events_rows.json'
rows = json.load(open(SRC))
V282_NO_6c = [r for r in rows if r['g'] == 'V282' and r['rk'] != '0000006c--2bc842dbac']

def match(ref_rows, target_rows):
    pairs = []
    for r in target_rows:
        best, bd = None, 1e9
        for q in ref_rows:
            if abs(q['v'] - r['v']) > 3 or not (0.67 <= r['ad_rate_pk'] / max(q['ad_rate_pk'], 1e-6) <= 1.5):
                continue
            dist = abs(np.log(r['ad_rate_pk'] / q['ad_rate_pk'])) + abs(q['v'] - r['v']) / 10
            if dist < bd:
                best, bd = q, dist
        if best is not None:
            pairs.append((r, best))
    return pairs

for rk in ('0000006c--68c6e94b17', '0000006d--05e83bb04f'):
    tgt = [r for r in rows if r['g'] == 'T64' and r['rk'] == rk and r['v'] >= 8]
    pairs = match(V282_NO_6c, tgt)
    if len(pairs) < 3:
        print(rk, 'too few pairs', len(pairs)); continue
    ang_lag = np.array([r['ang_lag'] - q['ang_lag'] for r, q in pairs if np.isfinite(r['ang_lag']) and np.isfinite(q['ang_lag'])])
    hf = np.array([r['hf'] - q['hf'] for r, q in pairs if np.isfinite(r['hf']) and np.isfinite(q['hf'])])
    print(rk, 'n_pairs', len(pairs), 'ang_lag median diff', round(float(np.median(ang_lag)), 3),
          'hf median diff', round(float(np.median(hf)), 3))
