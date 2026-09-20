"""classifier stage 5: (i) how many episode labels flip between the two angdes reconstructions, and
(ii) a TIME-WEIGHTED census over every engaged hands-off frame at 2-15 m/s -- 145 episode release samples
are a thin base for a sign question, so the same three tests are also counted per frame.

Per frame, hands-off + engaged:
  fires      = gate > 1e-3                                   (the term's own test)
  outward_w  = sign(aa)*z > 0                                 pushes the WHEEL away from its own centre-side
  inward_w   = sign(aa)*z < 0                                 pushes the WHEEL toward / through centre
  moving_out = sign(steering rate 5 Hz lp) == sign(aa)        the wheel is actually travelling outward
  D-test     = sign(angdes) == sign(aa)
Also the sensitivity of |angdes| to the reconstruction (the tanh(angdes/1.0) argument), and how much of the
low-speed hands-off time sits inside |angdes| < 1 deg where the gate's own sign is set by a ~0.4 deg bias.
"""
import os, json, glob
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + '/out'
LEVEL = 0.020
rows = json.load(open(f'{OUT}/c1_rows.json'))
col = lambda k: np.array([r[k] for r in rows])
colf = lambda k: col(k).astype(float)
v = colf('v'); LOW = (v >= 2) & (v < 8); MID = (v >= 8) & (v < 15)
gA = colf('gate_bk_A') > 1e-3; gB = colf('gate_bk_B') > 1e-3
dA = colf('dose_bk_A'); dB = colf('dose_bk_B')
sgA = np.sign(colf('angdes_bk_A')); sgB = np.sign(colf('angdes_bk_B'))
aa_bk = colf('aa_bk')
R = {}
for bn, m in (('2-8', LOW), ('8-15', MID)):
    R[f'AB_flip|{bn}'] = dict(
        n=int(m.sum()), fires_A=int(gA[m].sum()), fires_B=int(gB[m].sum()),
        label_flips=int((gA[m] != gB[m]).sum()), frac_flip=float(np.mean(gA[m] != gB[m])),
        angdes_sign_flips=int((sgA[m] != sgB[m]).sum()), frac_sign_flip=float(np.mean(sgA[m] != sgB[m])),
        dose_disagree_ge_25pct=int((np.abs(dA[m] - dB[m]) >= 0.25 * LEVEL).sum()),
        med_abs_dose_diff=float(np.median(np.abs(dA[m] - dB[m]))))
print('=== (i) EPISODE LABEL FLIPS between the incumbent angdes (A) and the fork-faithful one (B) ===')
print(json.dumps({k: R[k] for k in R if k.startswith('AB_flip')}, indent=1))

# ---------------- (ii) time-weighted census ----------------
SOS = signal.butter(2, 5.0, btype='low', fs=100.0, output='sos')
ROUTES = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd',
          '00000076--d0b7ea7e4d', '00000075--6c8687d5bd']
BINS = [('2-5', 2.0, 5.0), ('5-8', 5.0, 8.0), ('2-8', 2.0, 8.0), ('8-12', 8.0, 12.0), ('12-15', 12.0, 15.0)]
ACC = {}
for rk in ROUTES:
    D = np.load(f'{OUT}/{rk}_cls.npz')
    C = np.load(f'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref/{rk}.npz', allow_pickle=True)
    v_ = D['v']; act = D['act']; aa = D['aa']; sr = D['sr']
    # hands-off, dilated 0.5 s, as the extractor does
    from scipy import ndimage
    t = C['t_cs']
    press = np.interp(t, C['t_cst'], C['spress']) > 0.5
    HO = act & ~ndimage.binary_dilation(press, iterations=50)
    srl = signal.sosfiltfilt(SOS, np.nan_to_num(sr))
    for tag in ('A', 'B'):
        ang = D[f'angdes_{tag}']; z = D[f'z_{tag}']; gate = D[f'gate_{tag}']
        fires = gate > 1e-3
        do = np.sign(aa) * z
        for bn, v0, v1 in BINS:
            m = HO & (v_ >= v0) & (v_ < v1)
            if m.sum() < 100:
                continue
            e = ACC.setdefault(f'{bn}|{tag}', dict(sec=0.0, fires=0, out=0, inw=0, mo_out=0, dtest=0,
                                                   near1=0, near04=0, absz=[], absz_f=[], zout=[], nf=0))
            e['sec'] += m.sum() / 100.0
            e['fires'] += int(fires[m].sum()); e['nf'] += int(m.sum())
            e['out'] += int((do[m] > 1e-5).sum()); e['inw'] += int((do[m] < -1e-5).sum())
            e['mo_out'] += int(((np.sign(srl[m]) == np.sign(aa[m])) & (np.abs(srl[m]) >= 1.0)).sum())
            e['dtest'] += int((np.sign(ang[m]) == np.sign(aa[m])).sum())
            e['near1'] += int((np.abs(ang[m]) < 1.0).sum()); e['near04'] += int((np.abs(ang[m]) < 0.4).sum())
            e['absz'].append(float(np.mean(np.abs(z[m])))); e['zout'].append(float(np.mean(do[m])))
    del D, C

print('\n=== (ii) TIME-WEIGHTED CENSUS, engaged hands-off frames ===')
hdr = 'sec %fires %push_OUT %push_IN %IN_of_fires %wheel_moving_out %D_test %|angdes|<1 %|angdes|<0.4 mean_z mean_z_out'
print(f'{"bin|tag":12s}' + ''.join(f'{h:>19s}' for h in hdr.split()))
CEN = {}
for k, e in ACC.items():
    n = e['nf']
    row = dict(sec=e['sec'], frac_fires=e['fires'] / n, frac_push_out=e['out'] / n, frac_push_in=e['inw'] / n,
               frac_in_of_fires=e['inw'] / max(e['fires'], 1), frac_wheel_moving_out=e['mo_out'] / n,
               frac_D_test=e['dtest'] / n, frac_angdes_lt1=e['near1'] / n, frac_angdes_lt04=e['near04'] / n,
               mean_abs_z=float(np.mean(e['absz'])), mean_z_out=float(np.mean(e['zout'])))
    CEN[k] = row
    print(f'{k:12s}' + ''.join(f'{x:19.4f}' for x in row.values()))
R['census'] = CEN
json.dump(R, open(f'{OUT}/c5_census.json', 'w'), indent=1)
