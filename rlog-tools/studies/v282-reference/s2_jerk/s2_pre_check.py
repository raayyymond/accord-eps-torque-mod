"""Is the pre-jerk-peak excursion wrong-way motion or a decaying prior over-delivery? Split by type; compare model and achieved
slopes over [-1.0,-0.4] s (normalised by step); fraction of events with achieved moving AGAINST the step while the model moves WITH it."""
import numpy as np, warnings
warnings.filterwarnings('ignore')
from scipy import signal
from s2_common import *
rows, tr = load_all(); sos = signal.butter(2, 3.0, fs=100, output='sos')
for sn, vbs in (('>=15', [2, 3]), ('<15', [0, 1])):
    for g in ['V282', 'T64', 'T64B', 'T5', 'T4']:
        for typ in ('onset', 'release'):
            R = [r for r in rows if r['group'] == g and r['vb'] in vbs and r['type'] == typ and abs(r['a1'] - r['a0']) >= 0.2]
            if len(R) < 4: continue
            ms, as_, wrong, lvl = [], [], 0, []
            for r in R:
                Dd = abs(r['a1'] - r['a0']); u = r['uid']
                m = tr['model'][u] / Dd; a = signal.sosfiltfilt(sos, tr['la_act'][u]) / Dd
                sm = np.polyfit(np.arange(60) / 100, m[0:60], 1)[0]; sa = np.polyfit(np.arange(60) / 100, a[0:60], 1)[0]
                ms.append(sm); as_.append(sa); wrong += (sa < -0.2 and sm > -0.05)
                lvl.append(np.mean(a[0:20] - m[0:20]))  # achieved - model at -1.0..-0.8 (baseline already removed, so ~0 by construction)
            print(f"{sn:5s} {g:5s} {typ:8s} n={len(R):3d} model slope {np.median(ms):+.2f}/s achieved slope {np.median(as_):+.2f}/s  wrong-way frac {wrong/len(R):.2f}")
