# -*- coding: utf-8 -*-
"""Shared helpers for the `unify` stream: loop identification from logged signals.

WHAT THIS IS.  Every transfer below is ESTIMATED FROM LOGGED INPUT AND LOGGED OUTPUT on real drives.
Nothing here simulates the car.  Closed-loop identification is done with the reference as an
instrument (an IV estimate), which is the standard unbiased construction when the disturbance is
uncorrelated with the reference; the direct (biased) estimate is computed alongside so the bias can
be seen rather than assumed.

SIGNS AND UNITS (read from the fork at latcontrol_torque.py:614-700 and confirmed on the log):
  pid_log.error  = error_with_lsf   [m/s^2]     (setpoint - measurement, inflated by the low-speed
                                                 factor, and notched on the torque builds)
  pid_log.p/i/f  = the three PID terms          [m/s^2]
  pid_log.output = -clip(p+i+f, +/-LAF)/LAF     [torque, full scale 1.0]
  => u_tot = -output = (p+i+f)/LAF, u_fb = (p+i)/LAF, u_ff = f/LAF     [torque]
  desiredLateralAccel = the SHAPED setpoint (post canceller / ref filter)   [m/s^2]
  actualLateralAccel  = the loop's own measurement = -calc_curvature(...)*v^2  [m/s^2]

LOOP ALGEBRA (2-DOF, exactly the fork's structure):
  u = K e + F r      (K = feedback PID, F = feedforward, both measurable from logs)
  y = P u + d        (P = torque -> measured lateral accel, the whole plant incl. EPS + delay)
  e = r - y
  => L = P K        S = 1/(1+L)        T = (PK+PF)/(1+PK)
Every one of K, F, P is estimated from logged pairs; L, S, the crossover and the margins are then
ALGEBRA on measured transfers.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
KIT = HERE.parents[4]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402

FS = 100.0
PARAMS = json.load(open(STUDY / "hsurface" / "surface" / "params_all.json"))

# Every cached route, with the family it belongs to.  EPS attribution follows v282cmp.py's
# documented rule; the five extra routes are torque-mode (V293 flew from route 70 onward).
FAMILY = {
    "00000064--ce6b0b0ebb": "V282",
    "00000065--b9f78988bd": "V282",
    "0000006c--2bc842dbac": "V282",
    "00000039--f56039af87": "V282old",
    "0000003a--283a39a1d6": "V282old",
    "0000003c--927965c2b4": "V282old",
    "0000006c--68c6e94b17": "TORQ",
    "0000006d--05e83bb04f": "TORQ",
    "0000006e--6ca3e014fd": "TORQ",
    "00000070--717f5a7866": "TORQ",
    "00000071--f2c9d073a3": "TORQ",
    "00000072--8001fc3048": "TORQ",
    "00000073--79fd149dd8": "TORQ",
    "00000075--6c8687d5bd": "TORQ",
    "00000076--d0b7ea7e4d": "TORQ",
}
SHORT = {k: k[6:8] + "/" + k[10:14] for k in FAMILY}


def laf(route):
    return float(PARAMS[route]["SteerLatAccel"])


def kp(route):
    return float(PARAMS[route]["SteerKP"])


def load(route):
    """v282cmp.load plus the loop signals in torque units and the raw engage flags."""
    D = np.load(V.CACHE / f"{route}.npz", allow_pickle=True)
    t = D["t_cs"]
    I = lambda tk, k: np.interp(t, D[tk], D[k])
    A = float(laf(route))
    v = I("t_cst", "vego")
    lat = I("t_cc", "lat_active") > 0.5
    S = dict(route=route, fam=FAMILY[route], t=t, v=v, laf=A, kp=kp(route),
             cs_active=D["cs_active"] > 0.5, lat_active=lat,
             cc_enabled=I("t_cc", "cc_enabled") > 0.5,
             active=(D["cs_active"] > 0.5) & lat,
             pressed=I("t_cst", "spress") > 0.5,
             sa=I("t_cst", "sa_deg"), sr=I("t_cst", "sr_deg"),
             r=D["cs_la_des"], y=D["cs_la_act"], e=D["cs_err"],
             p=D["cs_p"], i=D["cs_i"], f=D["cs_f"], out=D["cs_out"],
             sat=D["cs_sat"] > 0.5,
             model=D["cs_des_curv"] * v * v,
             la_pose=I("t_pose", "pose_wz") * v,
             storque=I("t_cst", "storque"))
    S["u"] = (S["p"] + S["i"] + S["f"]) / A          # total command, torque units
    S["ufb"] = (S["p"] + S["i"]) / A                 # feedback part
    S["uff"] = S["f"] / A                            # feedforward part
    S["u_log"] = -S["out"]                           # what actually went out (post-clip)
    return S


def usable(S, vmin=0.0, vmax=99.0, hands="off"):
    m = S["active"] & (S["v"] >= vmin) & (S["v"] < vmax)
    if hands == "off":
        m &= ~S["pressed"]
    elif hands == "on":
        m &= S["pressed"]
    return m


def segments(S, mask, min_s, nps_cap=8192):
    """Contiguous usable runs of at least min_s seconds, no clock gaps."""
    return [(a, b) for a, b in V.runs(mask, S["t"], min_s=min_s)]


class Spec:
    """Welch/CSD accumulator over a set of windows, input-power weighted.

    All cross- and auto-spectra are accumulated over the SAME windows with the SAME nperseg, so
    every ratio below is a consistent estimate on identical data.
    """

    def __init__(self, nperseg):
        self.n = int(nperseg)
        self.acc = {}
        self.sec = 0.0
        self.nwin = 0
        self.f = None

    def add(self, sigs):
        """sigs: dict name -> 1-D array, all the same length (one window)."""
        L = len(next(iter(sigs.values())))
        if L < self.n:
            return False
        xs = {k: np.nan_to_num(x) - np.nanmean(np.nan_to_num(x)) for k, x in sigs.items()}
        w = L
        names = list(xs)
        for a in names:
            f, p = signal.welch(xs[a], FS, nperseg=self.n, noverlap=self.n // 2)
            self.f = f
            self.acc[(a, a)] = self.acc.get((a, a), 0.0) + p * w
        for ii, a in enumerate(names):
            for b in names[ii + 1:]:
                _, c = signal.csd(xs[a], xs[b], FS, nperseg=self.n, noverlap=self.n // 2)
                self.acc[(a, b)] = self.acc.get((a, b), 0.0) + c * w
        self.sec += w / FS
        self.nwin += 1
        return True

    def P(self, a, b):
        if (a, b) in self.acc:
            return self.acc[(a, b)]
        if (b, a) in self.acc:
            return np.conj(self.acc[(b, a)])
        raise KeyError((a, b))

    def H(self, x, y):
        """Direct (least-squares) estimate y = H x.  Biased under feedback; reported for contrast."""
        return self.P(x, y) / np.maximum(np.abs(self.P(x, x)), 1e-30)

    def Hiv(self, x, y, z):
        """Instrumental-variable estimate of y = H x with instrument z: H = Pzy / Pzx.
        Unbiased when the disturbance is uncorrelated with z."""
        return self.P(z, y) / np.where(np.abs(self.P(z, x)) < 1e-30, 1e-30, self.P(z, x))

    def coh(self, a, b):
        return np.abs(self.P(a, b)) ** 2 / np.maximum(np.abs(self.P(a, a) * self.P(b, b)), 1e-30)


def band(f, f1, f2):
    return (f >= f1) & (f < f2)


def bandavg_mag(f, Hc, f1, f2, w=None):
    """Average |H| as MAGNITUDES over a band (never phasors), power-weighted if w given."""
    s = band(f, f1, f2)
    if s.sum() == 0:
        return float("nan")
    m = np.abs(Hc[s])
    return float(np.average(m, weights=(w[s] if w is not None else None)))


def bandavg_phase(f, Hc, f1, f2, w=None):
    """Power-weighted phasor average -> phase in degrees (phase IS a phasor quantity)."""
    s = band(f, f1, f2)
    if s.sum() == 0:
        return float("nan")
    ww = w[s] if w is not None else np.ones(s.sum())
    z = np.sum(Hc[s] / np.maximum(np.abs(Hc[s]), 1e-30) * ww)
    return float(np.degrees(np.angle(z)))


def crossover(f, L, fmin=0.05, fmax=5.0):
    """Lowest frequency in [fmin,fmax] where |L| crosses 1 from above, by log-log interpolation.
    Returns (f_c, phase_margin_deg) or (nan, nan)."""
    s = band(f, fmin, fmax)
    ff, mag = f[s], np.abs(L[s])
    ph = np.unwrap(np.angle(L[s]))
    g = 20 * np.log10(np.maximum(mag, 1e-12))
    for k in range(len(ff) - 1):
        if g[k] >= 0 > g[k + 1]:
            w = g[k] / (g[k] - g[k + 1])
            fc = ff[k] * (ff[k + 1] / ff[k]) ** w
            pc = ph[k] + w * (ph[k + 1] - ph[k])
            pm = np.degrees(pc) + 180.0
            pm = (pm + 180.0) % 360.0 - 180.0
            return float(fc), float(pm)
    return float("nan"), float("nan")


def smooth_c(H, k=5):
    """Odd-length moving average on a complex transfer (variance reduction in frequency)."""
    if k <= 1:
        return H
    ker = np.ones(k) / k
    return np.convolve(H, ker, mode="same")


def group_delay_ms(f, Hc, f1, f2):
    """Equivalent delay from the band-average phase: -phase/(2*pi*f_c), ms.  Reported at the band
    centre; this is a PHASE-to-DELAY conversion of a measured transfer, not a model."""
    s = band(f, f1, f2)
    if s.sum() == 0:
        return float("nan")
    fc = float(np.average(f[s]))
    ph = np.unwrap(np.angle(Hc))[s]
    phc = float(np.average(ph))
    return -phc / (2 * np.pi * fc) * 1000.0


def _self_test():
    """Positive controls: recover a KNOWN plant and a KNOWN loop from a synthetic closed loop with a
    disturbance, using the same estimators the real analysis uses."""
    rng = np.random.default_rng(3)
    n = 200000
    dt = 1 / FS
    # known plant: first order, gain 2.0, pole 1.5 Hz, delay 60 ms
    fp, gp, Dn = 1.5, 2.0, 6
    a = np.exp(-2 * np.pi * fp * dt)
    # reference: band-limited, exogenous by construction
    r = signal.sosfiltfilt(signal.butter(2, 3.0, "low", fs=FS, output="sos"), rng.standard_normal(n)) * 40
    d = signal.sosfiltfilt(signal.butter(2, 3.0, "low", fs=FS, output="sos"), rng.standard_normal(n)) * 20
    KP, KI = 0.6, 0.2
    y = np.zeros(n); u = np.zeros(n); e = np.zeros(n); ufb = np.zeros(n); x = 0.0; itg = 0.0
    ub = np.zeros(n + Dn)
    for k in range(n):
        e[k] = r[k] - y[k - 1] if k else r[k]
        itg += KI * e[k] * dt
        ufb[k] = KP * e[k] + itg
        u[k] = ufb[k]
        ub[k + Dn] = u[k]
        x = a * x + (1 - a) * gp * ub[k]
        y[k] = x + d[k]
    sp = Spec(4096)
    sp.add(dict(r=r, y=y, u=u, e=e))
    f = sp.f
    Piv = smooth_c(sp.Hiv("u", "y", "r"), 5)
    Pdir = smooth_c(sp.H("u", "y"), 5)
    fsafe = np.maximum(f, 1e-9)
    Ptrue = gp * (1 - a) / (1.0 - a * np.exp(-2j * np.pi * f * dt)) * np.exp(-2j * np.pi * f * Dn * dt)
    Ktrue = KP + KI / (2j * np.pi * fsafe)
    BB = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)]
    eiv = max(abs(bandavg_mag(f, Piv, b1, b2) / bandavg_mag(f, Ptrue, b1, b2) - 1) for b1, b2 in BB)
    piv = max(abs(bandavg_phase(f, Piv, b1, b2) - bandavg_phase(f, Ptrue, b1, b2)) for b1, b2 in BB)
    edir = max(abs(bandavg_mag(f, Pdir, b1, b2) / bandavg_mag(f, Ptrue, b1, b2) - 1) for b1, b2 in BB)
    Kc = smooth_c(sp.H("e", "u"), 5)
    ek = max(abs(bandavg_mag(f, Kc, b1, b2) / bandavg_mag(f, Ktrue, b1, b2) - 1) for b1, b2 in BB)
    L = smooth_c(Kc * Piv, 5)
    Lt = Ktrue * Ptrue
    fc, pm = crossover(f, L, 0.05, 5.0)
    fct, pmt = crossover(f, Lt, 0.05, 5.0)
    Ms = float(np.max(np.abs(1.0 / (1.0 + L))[band(f, 0.05, 5.0)]))
    Mst = float(np.max(np.abs(1.0 / (1.0 + Lt))[band(f, 0.05, 5.0)]))
    assert eiv < 0.10, f"IV plant band-mag error {eiv:.3f}"
    assert piv < 8.0, f"IV plant band-phase error {piv:.1f} deg"
    assert edir > 3 * eiv, f"direct estimate is NOT visibly biased ({edir:.3f} vs {eiv:.3f})"
    assert ek < 0.05, f"controller recovery error {ek:.3f}"
    assert abs(fc - fct) < 0.07 * fct, f"crossover {fc:.3f} vs true {fct:.3f}"
    assert abs(pm - pmt) < 6.0, f"PM {pm:.1f} vs true {pmt:.1f}"
    assert abs(Ms - Mst) < 0.15 * Mst, f"Ms {Ms:.2f} vs true {Mst:.2f}"
    return (f"self-test OK: IV plant band err {eiv*100:.1f}% mag / {piv:.1f} deg "
            f"(direct {edir*100:.0f}% = biased), K err {ek*100:.1f}%, "
            f"f_c {fc:.3f} vs true {fct:.3f} Hz, PM {pm:.1f} vs {pmt:.1f} deg, Ms {Ms:.2f} vs {Mst:.2f}")


if __name__ == "__main__":
    print(_self_test())
