"""ADVERSARIAL CONFOUND CHECK for s4_texture finding 'lightly-damped-3hz-closed-loop-mode'.

Re-derives the AR(10) pole (f, zeta) estimate and the e4->sr coherence FROM SCRATCH via V.load (does not
reuse s4_texture's cached blocks, to be an independent re-derivation), but this time tags every 10 s piece
with a SPEED x ACTIVITY(amplitude) cell (same SPD/ACT edges s4_compare.py uses) so the group comparison can
be run matched, per-route, and leave-one-route-out -- the sibling wheel23hztex confound test did this for
mode_rms/hf_ratio; this does it for the AR zeta claim specifically.

One route at a time (RAM). Writes a compact per-piece table to pieces.npz.
"""
import sys, json
import numpy as np
from scipy import signal

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s4_texture__lightlydampe__confound'
SPD = [0, 8, 15, 22, 40]
ACT = [0, 1.0, 3.0, 10.0, 1e9]
NB = 1000  # 10 s pieces at 100 Hz, matches s4_events.py


def ar_poles(x, p=10, fs=25.0):
    x = x - x.mean()
    Y = x[p:]; X = np.column_stack([x[p - k - 1:len(x) - k - 1] for k in range(p)])
    a, *_ = np.linalg.lstsq(X, Y, rcond=None)
    z = np.roots(np.r_[1, -a])
    s = np.log(z.astype(complex)) * fs
    out = []
    for si in s:
        if si.imag > 0:
            wn = abs(si)
            out.append((wn / (2 * np.pi), -si.real / wn))
    return out


def route(rk):
    S = V.load(rk)
    meta = S['meta']
    u = V.usable(S); t = S['t']
    e4 = np.nan_to_num(S['e4']); sr = np.nan_to_num(S['sr']); v = np.nan_to_num(S['v'])
    rows = []
    for a, b in V.runs(u, t, min_s=NB / 100.0):
        for k0 in range(0, b - a - NB + 1, NB):
            g = slice(a + k0, a + k0 + NB)
            sr_p = sr[g]; e4_p = e4[g]; v_p = v[g]
            vv = float(np.median(v_p))
            act = float(np.mean(np.abs(V.lowpass(sr_p, 0.5))))
            # AR poles on this piece, decimated to 25 Hz (same as s4_events.py)
            ds = signal.decimate(sr_p, 4, zero_phase=True)
            poles = [(f, z) for f, z in ar_poles(ds) if 1.5 <= f <= 4.0]
            if poles:
                # least-damped (min zeta) pole in-band -- what rings
                fz = min(poles, key=lambda p: p[1])
                f_ld, z_ld = fz
            else:
                f_ld = z_ld = np.nan
            # coherence e4->sr and variance shares, this piece (nperseg=250 -> 4 Hz bins... use 200 for finer + more windows)
            f_c, Cxy = signal.coherence(e4_p - e4_p.mean(), sr_p - sr_p.mean(), fs=100.0, nperseg=250, noverlap=125)
            _, Pxx = signal.welch(e4_p - e4_p.mean(), fs=100.0, nperseg=250, noverlap=125)
            _, Pyy = signal.welch(sr_p - sr_p.mean(), fs=100.0, nperseg=250, noverlap=125)
            b183 = (f_c >= 1.8) & (f_c < 3.0)
            b1p5_5 = (f_c >= 1.5) & (f_c < 5.0)
            btot = (f_c >= 0.05) & (f_c < 20.0)
            coh183 = float(np.mean(Cxy[b183])) if b183.sum() else np.nan
            e4_share = float(Pxx[b1p5_5].sum() / max(Pxx[btot].sum(), 1e-12))
            sr_share = float(Pyy[b1p5_5].sum() / max(Pyy[btot].sum(), 1e-12))
            sband = int(np.digitize([vv], SPD)[0] - 1)
            aband = int(np.digitize([act], ACT)[0] - 1)
            cell = sband * 10 + aband
            rows.append((vv, act, sband, aband, cell, f_ld, z_ld, coh183, e4_share, sr_share, len(poles)))
    R = np.array(rows, dtype=np.float64) if rows else np.zeros((0, 11))
    np.savez_compressed(f'{HERE}/data_{rk.replace("--", "_")}.npz', R=R, group=meta['group'], route=rk)
    print(rk, meta['group'], 'pieces', len(rows), 'w/pole', int(np.sum(~np.isnan(R[:, 6]))) if len(rows) else 0, flush=True)
    del S


if __name__ == '__main__':
    import os
    os.makedirs(HERE, exist_ok=True)
    for rk in (sys.argv[1:] or list(V.ROUTES)):
        route(rk)
