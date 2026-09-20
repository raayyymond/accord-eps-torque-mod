"""b_shake helpers. Terms in +LEFT torque, output units (cs_out frame, same as steeringRateDeg +left).
Source of sub-terms: fill_texturetermd/out/red_<route>.npz (s5 replica, validated open loop; re-validated here <3 m/s).
Logged observer: out/obs_<route>.npz (raw logged sign; contribution to cs_out = -logged)."""
import sys
import numpy as np
from scipy import signal
BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/'
sys.path.insert(0, BASE)
import v282cmp as V  # noqa
HERE = BASE + 'lowspeed/b_shake/'
OUT = HERE + 'out/'
FS = 100.0
TORQUE = {'0000006c--68c6e94b17': 'T64', '0000006d--05e83bb04f': 'T64', '0000006e--6ca3e014fd': 'T64B',
          '00000076--d0b7ea7e4d': 'T5', '00000075--6c8687d5bd': 'T4'}
V282 = {'00000064--ce6b0b0ebb': 'V282', '00000065--b9f78988bd': 'V282', '0000006c--2bc842dbac': 'V282',
        '00000039--f56039af87': 'V282old', '0000003a--283a39a1d6': 'V282old', '0000003c--927965c2b4': 'V282old'}
BINS = [(0, 3, '<3'), (3, 6, '3-6'), (6, 8, '6-8'), (8, 15, '8-15')]
SOS = signal.butter(4, [1.5, 3.5], btype='band', fs=FS, output='sos')


def bp(x, sos=SOS):
    return signal.sosfiltfilt(sos, x)


def load_torque(rk):
    R = dict(np.load(V.CACHE.parent / 'v282ref' / 'x.npz')) if False else None
    D = dict(np.load(BASE + f'fill_texturetermd/out/red_{rk}.npz'))
    D = {k: np.asarray(v, dtype=np.float64) for k, v in D.items()}
    try:
        O = np.load(OUT + f'obs_{rk}.npz')
        if len(O['t']):
            D['dob_log'] = -np.interp(D['t'], O['t'], O['obs_logged'])
            D['dob_frz'] = np.interp(D['t'], O['t'], O['frozen']) > 0.5
    except FileNotFoundError:
        pass
    return D
