"""s5_mechanism helpers.  Built on v282cmp (do not edit that).  Adds what v282cmp does not have:
 - speed-stratum stretches (engaged, usable, contiguous, speed inside the band)
 - a COMPLEX per-bin FRF with an instrumental variable (closed-loop data: u and y are both driven by road noise through
   the loop, so S_uy/S_uu is biased; S_ry/S_ru with r = the model's demand is not, as long as r is uncorrelated with
   the road/driver noise).  v282cmp.band_H is magnitude-only and not IV, which is why this exists.
 - the +left plant torque u = cs_out (pid_log.output = -output_torque; the DOB uses u_left = -output_torque).
"""
import sys
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V  # noqa: E402

FS = V.FS
OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism/'
STRATA = [(3.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 40.0)]
GROUPS = {
    'V282': ['0000006c--2bc842dbac', '00000064--ce6b0b0ebb', '00000065--b9f78988bd'],
    'V282old': ['00000039--f56039af87', '0000003a--283a39a1d6', '0000003c--927965c2b4'],
    'T64': ['0000006c--68c6e94b17', '0000006d--05e83bb04f'],
    'T64B': ['0000006e--6ca3e014fd'],
    'T5': ['00000076--d0b7ea7e4d'],
    'T4': ['00000075--6c8687d5bd'],
}


def stretches(S, vlo, vhi, min_s):
    m = V.usable(S, vlo, vhi) & np.isfinite(S['sa']) & np.isfinite(S['sr']) & np.isfinite(S['model'])
    return V.runs(m, S['t'], min_s=min_s)


def frf_accumulate(acc, r, u, y_dict, nps):
    """Accumulate cross spectra for one contiguous stretch.  y_dict: name -> output array."""
    kw = dict(fs=FS, nperseg=nps, noverlap=nps // 2, detrend='linear')
    f, Srr = signal.welch(r, **kw)
    _, Sru = signal.csd(r, u, **kw)
    _, Suu = signal.welch(u, **kw)
    w = len(r)
    acc.setdefault('f', f)
    for k, v in (('Srr', Srr), ('Sru', Sru), ('Suu', Suu)):
        acc[k] = acc.get(k, 0) + v * w
    for name, y in y_dict.items():
        _, Sry = signal.csd(r, y, **kw)
        _, Suy = signal.csd(u, y, **kw)
        _, Syy = signal.welch(y, **kw)
        for k, v in (('Sry_' + name, Sry), ('Suy_' + name, Suy), ('Syy_' + name, Syy)):
            acc[k] = acc.get(k, 0) + v * w
    acc['sec'] = acc.get('sec', 0.0) + w / FS
    acc['n'] = acc.get('n', 0) + 1


def frf_result(acc, name):
    f = acc['f']
    H_iv = acc['Sry_' + name] / acc['Sru']                      # IV: u -> y
    H_dir = acc['Suy_' + name] / np.maximum(acc['Suu'], 1e-30)  # direct (biased in closed loop)
    coh_ru = np.abs(acc['Sru']) ** 2 / np.maximum(acc['Srr'] * acc['Suu'], 1e-30)
    coh_ry = np.abs(acc['Sry_' + name]) ** 2 / np.maximum(acc['Srr'] * acc['Syy_' + name], 1e-30)
    coh_uy = np.abs(acc['Suy_' + name]) ** 2 / np.maximum(acc['Suu'] * acc['Syy_' + name], 1e-30)
    return dict(f=f, H_iv=H_iv, H_dir=H_dir, coh_ru=coh_ru, coh_ry=coh_ry, coh_uy=coh_uy)
