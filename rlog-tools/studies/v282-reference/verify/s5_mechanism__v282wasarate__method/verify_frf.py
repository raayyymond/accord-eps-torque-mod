"""Independent re-derivation of s5_01_actuator_frf's V282 rate/cmd numbers.
Recomputes the IV FRF for the RATE channel specifically (the original json only
stored theta's coh_ry/coh_ru/coh_uy columns for both th and rate rows -- we need
the rate channel's own coherence to check the claim 'IV coherence r->rate 0.38-0.89').
Also re-derives the servo-model fit params for each stratum to cross-check
G 107-139, leak(a) 1.7-2.2/s, pole(fc) 11-16 Hz, delay 0.
"""
import json, sys
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism')
import s5lib as L  # noqa: E402
from scipy import optimize

NPS = 256
STRATA = L.STRATA
routes = L.GROUPS['V282']

accs = {st: {} for st in STRATA}
for rk in routes:
    S = L.V.load(rk)
    for st in STRATA:
        for a, b in L.stretches(S, st[0], st[1], min_s=2 * NPS / L.FS):
            r = np.nan_to_num(S['model'][a:b]); u = S['out'][a:b]
            L.frf_accumulate(accs[st], r, u, dict(rate=S['sr'][a:b]), NPS)
    del S

out = {}
allrate = []
allph = []
allcoh_ry_rate = []
allcoh_ru = []

for st, acc in accs.items():
    key = f'{st[0]:.0f}-{st[1]:.0f}'
    Rr = L.frf_result(acc, 'rate')
    f = Rr['f']
    # match s5_01's own bin-selection method: nearest welch bin to each named target,
    # not a naive range filter (the welch grid is 0.390625 Hz apart, so a naive
    # f<=1.95 cutoff silently drops the 1.953125 Hz bin that s5_01's argmin picks
    # for its "1.95" row -- reproduce EXACTLY what s5_01 did).
    targets = [0.39, 0.78, 1.17, 1.56, 1.95]
    idxs = [int(np.argmin(np.abs(f - t))) for t in targets]
    fs = f[idxs]
    mag = np.abs(Rr['H_iv'][idxs])
    ph = np.degrees(np.angle(Rr['H_iv'][idxs]))
    coh_ry_rate = Rr['coh_ry'][idxs]   # rate channel's OWN coherence -- not theta's
    coh_ru = Rr['coh_ru'][idxs]        # same for both channels (only depends on r,u)
    for i in range(len(fs)):
        allrate.append((key, float(fs[i]), float(mag[i])))
        allph.append((key, float(fs[i]), float(ph[i])))
        allcoh_ry_rate.append((key, float(fs[i]), float(coh_ry_rate[i])))
        allcoh_ru.append((key, float(fs[i]), float(coh_ru[i])))
    out[key] = dict(sec=round(acc['sec']))

    # servo fit on the FULL 0.3-4.0 Hz band (same window s5_01 used), weight = coh_ry*coh_ru
    sel_fit = (f >= 0.3) & (f <= 4.0)
    w = (Rr['coh_ry'] * Rr['coh_ru'])[sel_fit]
    Hfit = Rr['H_iv'][sel_fit]
    ffit = f[sel_fit]
    s = 1j * 2 * np.pi * ffit

    def model(p):
        G, a, fc, d = p
        return G * np.exp(-s * d) / ((s + a) * (1 + s / (2 * np.pi * fc)))

    def resid(p):
        e = (model(p) - Hfit) / np.maximum(np.abs(Hfit), 1e-9)
        return np.concatenate([np.sqrt(w) * e.real, np.sqrt(w) * e.imag])

    best = None
    for G0 in (30, 100, 300):
        for fc0 in (1.0, 3.0, 8.0):
            r = optimize.least_squares(resid, [G0, 1.0, fc0, 0.05],
                                        bounds=([0.1, -5.0, 0.05, 0.0], [5000, 50.0, 50.0, 0.4]))
            if best is None or r.cost < best.cost:
                best = r
    out[key]['servo_fit_on_rate'] = dict(p=[float(x) for x in best.x], cost=float(best.cost))

print("=== recomputed rate-channel IV FRF, V282, 0.39-1.95 Hz, all 4 strata ===")
print("total sec:", sum(round(acc['sec']) for acc in accs.values()))
print("gain (|H_iv| rate) min/max:", min(allrate, key=lambda x: x[2]), max(allrate, key=lambda x: x[2]))
print("phase min/max:", min(allph, key=lambda x: x[2]), max(allph, key=lambda x: x[2]))
print("coh_ry (RATE channel, own) min/max:", min(allcoh_ry_rate, key=lambda x: x[2]), max(allcoh_ry_rate, key=lambda x: x[2]))
print("coh_ru min/max:", min(allcoh_ru, key=lambda x: x[2]), max(allcoh_ru, key=lambda x: x[2]))
print()
for k, v in out.items():
    print(k, v)

json.dump(dict(bins=dict(rate=allrate, ph=allph, coh_ry_rate=allcoh_ry_rate, coh_ru=allcoh_ru), fits=out),
          open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s5_mechanism__v282wasarate__method/verify_frf_out.json', 'w'),
          indent=1)
