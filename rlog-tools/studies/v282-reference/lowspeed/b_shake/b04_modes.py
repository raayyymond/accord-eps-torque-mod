"""b04: is the 1.5-3.5 Hz wheel shake COMMANDED (planner content through the loop), EXCITED ringing, or a LIMIT CYCLE?
Per route (torque + V282 + V282old), per speed bin, usable frames, runs >= 4 s:
  * desired angle from the controller SETPOINT (d_v282low formula, roll ignored in band):
        sa_des = deg( (-sp / max(v^2,1)) * sR * L * (1 - SF v^2) )   (+left); adr = d/dt
    and from the MODEL desired curvature (cs_des_curv) the same way (curv_des, +left = -? checked by correlation below)
  * Welch windows (256, hop 128, label = mean v): Srr, Saa, Sra in 1.5-3.5 Hz -> coherence, |H| rate/adr, coherent/incoherent rate rms
  * rate spectrum 1-5 Hz accumulated -> peak frequency per bin
  * envelope (Hilbert of 1.8-3.5 Hz rate) and angle-band amplitude; QUIET = planner band env (1.2-4 Hz adr) < 1 deg/s
  * decay after envelope peaks >= 6 deg/s with quiet planner over the following 1 s: ratio env(+0.8 s)/env(peak)
  * sustained episodes: env >= 4 deg/s continuously >= 1.5 s (>= ~4 cycles): time share, quiet share, CV of env inside
Saves per-window rows to out/b04_rows_<route>.npz."""
import sys
import numpy as np
from scipy import signal
import bs
V = bs.V
L_, SF = 2.83, -7.0e-4
S1 = signal.butter(4, [1.5, 3.5], btype='band', fs=100, output='sos')
S2 = signal.butter(4, [1.8, 3.5], btype='band', fs=100, output='sos')
S3 = signal.butter(4, [1.2, 4.0], btype='band', fs=100, output='sos')
NPS, HOP = 256, 128
f = np.fft.rfftfreq(NPS, 0.01); BB = (f >= 1.5) & (f <= 3.55); SB = (f >= 0.9) & (f <= 5.1)
win = signal.get_window('hann', NPS)
routes = list(bs.TORQUE.items()) + list(bs.V282.items())
if len(sys.argv) > 1:
    routes = [(r, g) for r, g in routes if r in sys.argv[1:]]
for rk, g in routes:
    S = V.load(rk)
    v = S['v']; sp = np.nan_to_num(S['setpoint']); sR = np.nan_to_num(S['sR'], nan=16.5)
    sa_des = np.degrees((-sp / np.maximum(v * v, 1.0)) * sR * L_ * (1 - SF * v * v))
    D = np.load(V.CACHE / f'{rk}.npz'); curv = D['cs_des_curv']; del D
    sa_mdl = np.degrees(curv * sR * L_ * (1 - SF * v * v))
    sr = S['sr']
    m = V.usable(S, 0, 15) & np.isfinite(sr) & np.isfinite(v) & np.isfinite(sa_des) & np.isfinite(sa_mdl)
    W = dict(v=[], Prr=[], Paa=[], Sra=[], Pmm=[], Srm=[], spec=[], absang=[])
    E = dict(v=[], env=[], aenv=[], quiet=[], angamp=[])
    DEC = []; EP = []
    for a, b in V.runs(m, S['t'], min_s=4.0):
        x = sr[a:b]; adr = np.gradient(sa_des[a:b]) * 100; amr = np.gradient(sa_mdl[a:b]) * 100
        # windows
        for s in range(0, b - a - NPS + 1, HOP):
            R = np.fft.rfft(signal.detrend(x[s:s + NPS]) * win)
            A = np.fft.rfft(signal.detrend(adr[s:s + NPS]) * win)
            M = np.fft.rfft(signal.detrend(amr[s:s + NPS]) * win)
            W['v'].append(v[a + s:a + s + NPS].mean()); W['absang'].append(np.abs(S['sa'][a + s:a + s + NPS]).mean())
            W['Prr'].append(np.abs(R[BB]) ** 2); W['Paa'].append(np.abs(A[BB]) ** 2); W['Sra'].append(np.conj(A[BB]) * R[BB])
            W['Pmm'].append(np.abs(M[BB]) ** 2); W['Srm'].append(np.conj(M[BB]) * R[BB]); W['spec'].append(np.abs(R[SB]) ** 2)
        if b - a < 600:
            continue
        rb = signal.sosfiltfilt(S2, x); env = np.abs(signal.hilbert(rb))
        ab = signal.sosfiltfilt(S3, adr); aenv = np.abs(signal.hilbert(ab))
        angb = signal.sosfiltfilt(S2, S['sa'][a:b]); angamp = np.abs(signal.hilbert(angb))
        e = 100
        sl = slice(e, b - a - e)
        vq = v[a:b]
        quiet = aenv < 1.0
        E['v'].append(vq[sl]); E['env'].append(env[sl]); E['aenv'].append(aenv[sl]); E['quiet'].append(quiet[sl]); E['angamp'].append(angamp[sl])
        # decay after envelope peaks
        pk, _ = signal.find_peaks(env[sl], height=6.0, distance=50)
        for p in pk + e:
            if p + 90 >= b - a - e:
                continue
            q = bool(np.all(aenv[p:p + 100] < 1.0)) if p + 100 <= len(aenv) else False
            qin = float(np.max(aenv[p:p + 90]) / max(env[p], 1e-6))
            DEC.append((vq[p], env[p], env[p + 40] / env[p], env[p + 80] / env[p], float(q), qin, aenv[p]))
        # sustained episodes
        hi = env >= 4.0
        for i0, i1 in V.runs(hi[e:-e], np.arange(len(hi) - 2 * e) / 100.0, min_s=1.5):
            i0 += e; i1 += e
            EP.append((vq[i0:i1].mean(), (i1 - i0) / 100, env[i0:i1].mean(), env[i0:i1].std() / env[i0:i1].mean(),
                       float(np.mean(quiet[i0:i1])), angamp[i0:i1].mean(), aenv[i0:i1].mean()))
    out = {k: np.asarray(vv) for k, vv in W.items()}
    for k in E:
        out['E_' + k] = np.concatenate(E[k]).astype(np.float32) if E[k] else np.zeros(0)
    out['DEC'] = np.asarray(DEC); out['EP'] = np.asarray(EP); out['f'] = f
    np.savez_compressed(bs.OUT + f'b04_rows_{rk}.npz', **out)
    # sign check setpoint-desired vs model-desired
    Sra = out['Sra'].sum(); Srm = out['Srm'].sum() if len(out['Srm']) else 0
    print(rk, g, 'windows', len(W['v']), 'env frames', len(out['E_env']), 'dec', len(DEC), 'ep', len(EP),
          'phase(sr vs adr_sp) %.0f  (sr vs adr_model) %.0f' % (np.degrees(np.angle(Sra)), np.degrees(np.angle(Srm))), flush=True)
    del S, out, W, E
