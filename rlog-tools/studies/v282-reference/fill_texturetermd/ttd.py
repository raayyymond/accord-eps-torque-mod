"""fill_texturetermd helpers (own module; does not edit v282cmp.py or s5 code).

Why this exists: v282cmp.band_H is magnitude-only and stretch-based; this stream needs (a) the fork's lateral command
split into FEEDFORWARD (planner-only: hold, move, friction hysteresis, rate-loop reference part, P on the setpoint) and
FEEDBACK (P on the measurement, I, rate-loop measured-rate part, disturbance observer) sub-terms, and (b) cross-spectra
accumulated over short windows LABELLED by speed/|angle|/turn membership, so strata that never persist for a whole
stretch still get a coherence estimate.

Frames: every term is returned as +LEFT plant torque in units of the [-1,1] output (u = cs_out = -e4/4089), the same
frame as steeringAngleDeg / steeringRateDeg (+left).  The s5 replica stores torque-frame lateral-accel units (x laf).
"""
import math, sys
import numpy as np
from scipy import signal
BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/'
sys.path.insert(0, BASE)
sys.path.insert(0, BASE + 's5_mechanism')
import v282cmp as V  # noqa: E402

FS = V.FS
HERE = BASE + 'fill_texturetermd/'
OUT = HERE + 'out/'
TORQUE = {'0000006c--68c6e94b17': 'T64', '0000006d--05e83bb04f': 'T64', '0000006e--6ca3e014fd': 'T64B',
          '00000076--d0b7ea7e4d': 'T5', '00000075--6c8687d5bd': 'T4'}
GROUP_REV = {'T64': 'rev64', 'T64B': 'rev64B', 'T5': 'rev5', 'T4': 'rev4'}
TERMS_FF = ['hold', 'move', 'hyst', 'rl_ff', 'p_sp']
TERMS_FB = ['p_meas', 'i', 'rl_fb', 'dob']
TERMS = TERMS_FF + TERMS_FB
BAND = (1.5, 3.5)


def red(rk):
    return dict(np.load(OUT + f'red_{rk}.npz'))


def bp(x, f1=BAND[0], f2=BAND[1], order=4):
    sos = signal.butter(order, [f1, f2], btype='band', fs=FS, output='sos')
    return signal.sosfiltfilt(sos, x)


def windows(mask, t, nps=256, hop=64):
    """start indices of windows fully inside mask with no clock gap"""
    out = []
    for a, b in V.runs(mask, t, min_s=nps / FS):
        for s in range(a, b - nps + 1, hop):
            out.append(s)
    return np.array(out, dtype=int)


class XAcc:
    """Accumulate auto/cross spectra of named signals against a reference r over labelled windows.
    S[name] = sum_w conj(R) * X  (so angle = phase(X) - phase(R): + means X LEADS r)."""

    def __init__(self, names, nps=256):
        self.names = names; self.nps = nps
        self.win = signal.get_window('hann', nps)
        self.f = np.fft.rfftfreq(nps, 1 / FS)
        self.Srr = np.zeros(len(self.f)); self.Sxr = {n: np.zeros(len(self.f), complex) for n in names}
        self.Sxx = {n: np.zeros(len(self.f)) for n in names}
        self.Sxy = {}  # pairwise with 'total' for share
        self.nw = 0

    def add(self, r, X, s):
        e = s + self.nps
        w = self.win
        R = np.fft.rfft(signal.detrend(r[s:e]) * w)
        self.Srr += np.abs(R) ** 2
        for n in self.names:
            Xf = np.fft.rfft(signal.detrend(X[n][s:e]) * w)
            self.Sxr[n] += np.conj(R) * Xf
            self.Sxx[n] += np.abs(Xf) ** 2
            if 'total' in X and n != 'total':
                T = np.fft.rfft(signal.detrend(X['total'][s:e]) * w)
                self.Sxy[n] = self.Sxy.get(n, 0) + np.conj(T) * Xf
        self.nw += 1

    def summary(self, f1=BAND[0], f2=BAND[1], delay_s=0.06):
        b = (self.f >= f1) & (self.f <= f2)
        wr = self.Srr[b]
        res = dict(nw=self.nw, rate_rms=float(np.sqrt(self.Srr[b].sum() / max(self.nw, 1))) if self.nw else float('nan'))
        om = 2 * np.pi * self.f[b]
        for n in self.names:
            Sxr = self.Sxr[n][b]; Sxx = self.Sxx[n][b]
            coh = np.abs(Sxr) ** 2 / np.maximum(Sxx * wr, 1e-30)
            ph = np.unwrap(np.angle(Sxr))
            gd = float(-np.polyfit(om, ph, 1, w=np.sqrt(wr))[0]) if b.sum() >= 3 else float('nan')   # >0: X lags r
            # delayed-torque work on the wheel: Re sum conj(R) X e^{-i w d}, normalised by rate power -> equivalent
            # viscous coefficient b_eq (torque per deg/s).  b_eq > 0 = the term DAMPS, < 0 = it PUMPS.
            work = float(np.real(np.sum(Sxr * np.exp(-1j * om * delay_s))))
            r = dict(coh=float(np.average(coh, weights=wr)), phase_deg=float(np.degrees(np.angle(Sxr.sum()))),
                     gd_s=gd, b_eq=float(-work / max(wr.sum(), 1e-30)),
                     rms=float(np.sqrt(Sxx.sum() / max(self.nw, 1))))
            if n in self.Sxy:
                St = self.Sxx['total'][b]
                r['share'] = float(np.real(self.Sxy[n][b].sum()) / max(St.sum(), 1e-30))
            res[n] = r
        return res


def coh_floor(nw_eff):
    """expected coherence of independent signals ~ 1/N_eff"""
    return 1.0 / max(nw_eff, 1)
