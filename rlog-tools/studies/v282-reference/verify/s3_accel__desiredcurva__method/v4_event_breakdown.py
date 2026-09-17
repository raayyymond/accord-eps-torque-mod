import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
from scipy import signal
import s3turns as T
import v282cmp as V

rk = '0000006c--68c6e94b17'
R = T.prep(rk)
evs, rej = T.find_turns(R)
print("rejects", rej)
adr = V.deriv(R["ad"])
n = len(R["t"])
for e in evs:
    mask = np.zeros(n, bool); mask[e["w0"]:e["w1"]] = True; mask &= ~R["pressed"]
    print(f"\nevent t={e['t']:.1f} v={e['v']:.1f} P={e['P']:.1f} hold_s={e['hold_s']:.2f} press_frac={e['press_frac']:.2f}")
    for a, b in V.runs(mask, R["t"], min_s=2.56):
        x = adr[a:b] - adr[a:b].mean(); y = R["sr"][a:b] - R["sr"][a:b].mean()
        f, pxx = signal.welch(x, V.FS, nperseg=256, noverlap=128)
        _, pyy = signal.welch(y, V.FS, nperseg=256, noverlap=128)
        df = f[1]-f[0]
        m = (f>=1.5)&(f<3.5)
        des = float(np.sqrt(np.sum(pxx[m])*df)); meas = float(np.sqrt(np.sum(pyy[m])*df))
        dur = (b-a)/V.FS
        # also raw stats on the desired ANGLE (not rate) and rate itself in-window, to spot a glitch
        ad_win = R["ad"][a:b]; adr_win = adr[a:b]
        print(f"   window dur={dur:5.1f}s  des_rms(1.5-3.5)={des:7.2f} meas_rms={meas:6.2f}  "
              f"ad range=[{ad_win.min():.1f},{ad_win.max():.1f}]deg  adr max|.|={np.max(np.abs(adr_win)):.1f} deg/s  "
              f"adr p99={np.percentile(np.abs(adr_win),99):.1f}")
