# -*- coding: utf-8 -*-
"""studies/grind/b_iv_kappa.py -- TWO questions the V291 DO-NOT-FLASH turns on.

Q1  Is B(f) = bar/rate biased by closed-loop feedback, and can 10-14 Hz be identified with an
    INSTRUMENT?   B is a ratio of two logged CLOSED-LOOP signals.  Re-estimate it with the 0xE4
    command (and, as a deliberately-invalid contrast, the 427 T tap) as the instrument:
        H_iv(rate -> bar) = S_cmd,bar / S_cmd,rate
    on bof's own strata, r39 + r6c, with coherence gates on BOTH cross-spectra and a block
    bootstrap over Welch windows.

Q2  Which r24 arm scaling is right -- does the +-3 POST-GAIN deadband explain the 0.45 factor?
    Reconstruct the lane's post-gain magnitude distribution, and solve for the deadband threshold
    that would reproduce the measured bit-6 duty at the FLOWN arm.  Then test which
    parameterisation (arm / deadband / post-scale / T-scale) is stratum-INVARIANT.

Subagent `biv`, 2026-09-13.  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing on any bus.

Estimator conventions are bof_v282.py's, verbatim, and section 0 proves it: nperseg 128, Hann,
50 % overlap, detrend constant, nfft 512, band-average +-0.40 Hz, COH_MIN 0.40, Hv = H1/sqrt(coh).
scipy's csd(x,y) = conj(X)*Y, so tf(u,y) = S_uy/S_uu and IV = S_wy/S_wu with instrument w.

Run: python b_iv_kappa.py      (writes _scratch/b_iv_kappa.{txt,json})
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import bof_v282 as BF                                        # noqa: E402  strata, load(), Pool, D4
import creep20_loop_id as C20                                # noqa: E402
from v282_r24_tap_read import read_cells, r24_series         # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
NPS, NFFT, NOV = 128, 512, 64
HALF = 0.40
COH_MIN = 0.40
FREQS = [3.0, 3.9, 5.0, 6.0, 7.3, 8.0, 10.0, 11.0, 12.0, 13.0, 14.0, 16.0, 18.0, 20.3, 22.0, 25.0, 30.0]
KEYF = [7.3, 20.3]
NBOOT = 2000
BLK = 2                      # bootstrap block = 2 adjacent (50 %-overlapping) Welch windows
RNG = np.random.default_rng(20260913)
OUT, J = [], {}


def pr(s=""):
    print(s, flush=True); OUT.append(s)


# ============================================================== per-window spectra (bootstrappable)
WIN = signal.get_window("hann", NPS)          # periodic, exactly what scipy.signal.csd uses


def seg_fft(x):
    """FFT of every Welch segment of one signal.  Returns (nwin, nfreq) complex.
    Matches scipy.signal.csd(nperseg=128, noverlap=64, nfft=512, window='hann', detrend='constant')
    up to a real scale that cancels in every ratio and coherence used here."""
    x = np.asarray(x, float)
    n = len(x)
    nseg = (n - NOV) // (NPS - NOV)
    if nseg < 1:
        return None
    idx = np.arange(NPS)[None, :] + (np.arange(nseg) * (NPS - NOV))[:, None]
    S = x[idx]
    S = S - S.mean(axis=1, keepdims=True)          # detrend='constant'
    return np.fft.rfft(S * WIN[None, :], n=NFFT, axis=1)


FGRID = np.fft.rfftfreq(NFFT, 1.0 / FS)
FSEL = (FGRID >= 2.0) & (FGRID <= 32.0)
FB = FGRID[FSEL]


class WinPool:
    """per-window FFTs for a set of signals over a stratum, so cross-spectra can be bootstrapped."""

    def __init__(self, keys):
        self.keys = list(keys)
        self.Z = {k: [] for k in keys}
        self.secs = 0.0

    def add_runs(self, g, mask, keys=None):
        keys = keys or self.keys
        for a, b in C20.runs(mask, NPS):
            zs = {k: seg_fft(g[k][a:b]) for k in keys}
            if any(z is None for z in zs.values()):
                continue
            for k in keys:
                self.Z[k].append(zs[k][:, FSEL])
            self.secs += (b - a) / FS

    def finish(self):
        self.Zc = {k: (np.concatenate(v, axis=0) if v else np.zeros((0, FB.size), complex))
                   for k, v in self.Z.items()}
        self.n = self.Zc[self.keys[0]].shape[0]
        return self

    def _bandsel(self, f0, half=HALF):
        s = np.abs(FB - f0) <= half + 1e-9
        if not s.any():
            s = np.zeros(FB.size, bool); s[int(np.argmin(np.abs(FB - f0)))] = True
        return s

    def _band(self, a, f0, half):
        """window x bin block for one signal inside f0 +- half, cached (the band is tiny, the pool is not)."""
        k = (a, round(f0, 6), round(half, 6))
        if not hasattr(self, "_bc"):
            self._bc = {}
        if k not in self._bc:
            self._bc[k] = np.ascontiguousarray(self.Zc[a][:, self._bandsel(f0, half)])
        return self._bc[k]

    def cross(self, a, b, f0, half=HALF, w=None):
        """band-summed cross-spectrum conj(A)*B over the selected windows (w = window index array).
        The band restriction is applied BEFORE the window indexing, so a bootstrap resample copies
        ~5 bins per window, not the whole spectrum."""
        A, B = self._band(a, f0, half), self._band(b, f0, half)
        if w is not None:
            A, B = A[w], B[w]
        return (np.conj(A) * B).mean(axis=0).sum()

    def est(self, f0, w=None, half=HALF):
        """all the estimators at one frequency, from one (possibly resampled) window set."""
        C = lambda a, b: self.cross(a, b, f0, half, w)   # noqa: E731
        Srr, Sbb = C("wire", "wire").real, C("bar", "bar").real
        Srb = C("wire", "bar")
        out = {}
        out["H1"] = Srb / Srr
        out["coh_dir"] = abs(Srb) ** 2 / (Srr * Sbb)
        out["Hv"] = out["H1"] / np.sqrt(max(out["coh_dir"], 1e-9))
        for nm, iv in (("cmd", "cmd"), ("T", "T100"), ("echo", "cmdecho"), ("resid", "cmdres")):
            if iv not in self.keys:
                continue
            Sii = C(iv, iv).real
            Sib, Sir = C(iv, "bar"), C(iv, "wire")
            out["iv_%s" % nm] = Sib / Sir
            out["cohib_%s" % nm] = abs(Sib) ** 2 / (Sii * Sbb)
            out["cohir_%s" % nm] = abs(Sir) ** 2 / (Sii * Srr)
        return out

    def boot(self, f0, keys, nboot=NBOOT, blk=BLK):
        """block bootstrap over Welch windows -> percentile CIs for |.| and angle of each estimator."""
        n = self.n
        if n < 4 * blk:
            return {}
        nb = max(1, n // blk)
        starts = RNG.integers(0, n - blk + 1, size=(nboot, nb))
        idxs = (starts[:, :, None] + np.arange(blk)[None, None, :]).reshape(nboot, -1)
        acc = {k: [] for k in keys}
        for r in range(nboot):
            e = self.est(f0, w=idxs[r])
            for k in keys:
                acc[k].append(e.get(k, np.nan))
        res = {}
        for k in keys:
            v = np.array(acc[k])
            if np.iscomplexobj(v):
                mag = np.abs(v)
                ref = np.angle(np.nanmean(v))
                ang = np.degrees(np.angle(v * np.exp(-1j * ref))) + np.degrees(ref)
                res[k] = dict(mag_lo=float(np.nanpercentile(mag, 2.5)), mag_hi=float(np.nanpercentile(mag, 97.5)),
                              ang_lo=float(np.nanpercentile(ang, 2.5)), ang_hi=float(np.nanpercentile(ang, 97.5)))
            else:
                res[k] = dict(lo=float(np.nanpercentile(v, 2.5)), hi=float(np.nanpercentile(v, 97.5)))
        return res


def ang(z):
    return float(np.degrees(np.angle(z)))


def unwrap_to(x, ref):
    """put angle x on the branch nearest ref."""
    return x + 360.0 * round((ref - x) / 360.0)
