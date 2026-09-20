"""e1_xcorr shared library: timestamp-true resampling, band-passed cross-correlation delay estimator with
sub-frame peak interpolation, and the synthetic torque-mode plant used for the positive control / bias correction.

Conventions
- u is the command in openpilot output-torque units, +u = the direction that increases steeringAngleDeg
  (u = -e4/4089 on the sendcan clock, or controlsState torqueState.output on the controlsState clock).
  The sign is checked on data (corr(u, acc) > 0), not assumed.
- Every signal is placed on a uniform 100 Hz grid by TRUE logMonoTime:
    command  -> zero-order hold from each message's time (the torque is held until the next frame)
    angle/rate -> linear interpolation between carState sample times
- A lag L > 0 means the response FOLLOWS the command by L.
"""
import math
from pathlib import Path
import numpy as np
from scipy import signal

KIT = Path(__file__).resolve().parents[5]
CACHE = KIT / "analysis-2020accord" / "_scratch" / "cache" / "v282ref"
HERE = Path(__file__).resolve().parent
FS = 100.0
DT = 1.0 / FS
E4_SCALE = 4089.0

HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
SPEED_BINS = [(0.0, 8.0), (8.0, 15.0), (15.0, 99.0)]
BIN_NAMES = ["<8", "8-15", ">=15"]

TORQUE_ROUTES = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
                 "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]
V282_ROUTES = ["0000006c--2bc842dbac", "00000064--ce6b0b0ebb"]


def zoh(t_msg, val, tg):
    """Value in force at each grid time: last message with t_msg <= tg (NaN before the first)."""
    idx = np.searchsorted(t_msg, tg, side="right") - 1
    out = np.where(idx >= 0, val[np.clip(idx, 0, None)], np.nan)
    return out


def load_route(route):
    D = np.load(CACHE / f"{route}.npz")
    R = {k: D[k] for k in ["t_cst", "sa_deg", "sr_deg", "vego", "spress", "t_e4", "e4_cmd", "t_cs", "cs_out",
                            "cs_active", "t_cc", "lat_active"]}
    del D
    return R


def grid_route(R):
    """Uniform 100 Hz grid spanning carState; returns dict of gridded signals + usable mask."""
    t0, t1 = R["t_cst"][0], R["t_cst"][-1]
    tg = np.arange(t0, t1, DT)
    G = dict(t=tg)
    G["sa"] = np.interp(tg, R["t_cst"], R["sa_deg"])
    G["sr"] = np.interp(tg, R["t_cst"], R["sr_deg"])
    G["v"] = np.interp(tg, R["t_cst"], R["vego"])
    G["pressed"] = zoh(R["t_cst"], R["spress"], tg) > 0.5
    G["u_e4"] = -zoh(R["t_e4"], R["e4_cmd"], tg) / E4_SCALE
    G["u_cs"] = zoh(R["t_cs"], R["cs_out"], tg)
    act = (zoh(R["t_cs"], R["cs_active"], tg) > 0.5) & (zoh(R["t_cc"], R["lat_active"], tg) > 0.5)
    # carState gap guard: no grid point more than 30 ms from a real carState sample
    j = np.searchsorted(R["t_cst"], tg)
    jl = np.clip(j - 1, 0, len(R["t_cst"]) - 1); jr = np.clip(j, 0, len(R["t_cst"]) - 1)
    gap = np.minimum(np.abs(tg - R["t_cst"][jl]), np.abs(R["t_cst"][jr] - tg))
    ok = act & ~G["pressed"] & (gap < 0.03) & np.isfinite(G["u_e4"]) & np.isfinite(G["u_cs"])
    G["ok"] = ok
    return G


def runs(mask, min_n):
    out = []; n = len(mask); i = 0
    d = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    st = np.where(d == 1)[0]; en = np.where(d == -1)[0]
    return [(a, b) for a, b in zip(st, en) if b - a >= min_n]


SOS = signal.butter(4, [1.0, 6.0], btype="band", fs=FS, output="sos")


def responses(sa, sr):
    """Candidate response signals (unfiltered): acc from the rate signal, acc from the angle signal, angle, rate."""
    return dict(acc_r=np.gradient(sr) * FS, acc_a=np.gradient(np.gradient(sa)) * FS * FS, ang=sa.copy(), rate=sr.copy())


LAGS = np.arange(-20, 41)          # samples: -200 .. +400 ms


class XC:
    """Accumulates normalised cross-correlation sums per block; one block = one contiguous 10 s stretch."""

    def __init__(self):
        self.blocks = []   # (bin, route, cxy[L], sxx, syy)

    def add(self, u, y, bin_i, tag, edge=100):
        """u, y unfiltered, contiguous. Band-pass both, drop filter edges, correlate on the SAME support per lag."""
        if len(u) < 2 * edge + 400:
            return
        uf = signal.sosfiltfilt(SOS, u - u.mean())[edge:-edge]
        yf = signal.sosfiltfilt(SOS, y - y.mean())[edge:-edge]
        n = len(uf)
        yc = yf[40:n - 20]           # identical response samples for every lag; command index = response index - L
        c = np.array([np.dot(uf[40 - L: n - 20 - L], yc) for L in LAGS])
        sxx = float(np.dot(uf[20:n - 40], uf[20:n - 40])); syy = float(np.dot(yc, yc))
        self.blocks.append((bin_i, tag, c, sxx, syy))

    def curve(self, sel=None, weights=None):
        bl = [b for b in self.blocks if sel is None or sel(b)]
        if not bl:
            return None
        C = sum(b[2] for b in bl); X = sum(b[3] for b in bl); Y = sum(b[4] for b in bl)
        return C / math.sqrt(X * Y + 1e-30)


def peak(curve, sign=+1, lo_ms=-50, hi_ms=250, up=20):
    """Sub-frame peak of sign*curve in [lo, hi]: (parabolic lag ms, FFT/sinc-upsampled lag ms, peak value).
    The 1-6 Hz band-passed xcorr is band-limited, so sinc (FFT) interpolation of the lag function is valid."""
    x = sign * curve
    lags_ms = LAGS * 10.0
    w = (lags_ms >= lo_ms) & (lags_ms <= hi_ms)
    idx = np.where(w)[0]
    i = idx[np.argmax(x[idx])]
    if 0 < i < len(x) - 1:
        a, b, c = x[i - 1], x[i], x[i + 1]
        den = a - 2 * b + c
        d = 0.5 * (a - c) / den if den != 0 else 0.0
    else:
        d = 0.0
    par = lags_ms[i] + 10.0 * d
    xs = signal.resample(x, len(x) * up)
    ls = lags_ms[0] + np.arange(len(xs)) * 10.0 / up
    ws = (ls >= lo_ms) & (ls <= hi_ms)
    j = np.where(ws)[0][np.argmax(xs[ws])]
    return float(par), float(ls[j]), float(sign * x[i])


def k_of_v(v):
    return np.interp(v, HOLD_V_BP, HOLD_K_V)


def sim_fine(t_u, u_val, t_s, v_s, D, J, b, F, k_scale=1.0, h=0.001, vstick=0.05, t_span=None,
             fb_gain=0.0, fb_delay=0.011, fb_rc=0.01, taper_v=12.0, dist_std=0.0, dist_seed=0):
    """Synthetic plant  J*acc = ucmd(t-D) - b*rate - k(v)*k_scale*angle - F*sign(rate)   (Karnopp stick-slip).

    ucmd(t) = the LOGGED command as a zero-order hold from its true send times t_u
              [- fb_gain*min(1, taper_v/v) * lp_RC(quantised rate)(t - fb_delay)   when fb_gain > 0: a closed-loop
               variant in which the command itself reacts to measured rate, so the estimator sees feedback too].
    The plant sees ucmd D later. Initial state: static equilibrium angle = ucmd/k, rate 0.
    Returns the fine time grid, angle, rate, ucmd (unquantised)."""
    ta, tb = t_span if t_span is not None else (t_s[0], t_s[-1])
    tt = np.arange(ta, tb, h)
    ulog = np.nan_to_num(zoh(t_u, u_val, tt))
    vv = np.interp(tt, t_s, v_s)
    kk = k_of_v(vv) * k_scale
    n = len(tt); nD = int(round(D / h)); nfd = int(round(fb_delay / h))
    ang = np.zeros(n); rate = np.zeros(n); ucmd = ulog.copy()
    taper = np.minimum(1.0, taper_v / np.maximum(vv, 0.1)) * fb_gain
    lpv = np.zeros(n); lp = 0.0; alpha = h / (fb_rc + h)
    a = ulog[0] / kk[0]; r = 0.0
    fb = fb_gain > 0.0
    dist = np.zeros(n)
    if dist_std > 0:   # unmeasured road/tyre torque disturbance: white noise low-passed at 4 Hz, std dist_std
        w = np.random.default_rng(dist_seed).standard_normal(n)
        w = signal.sosfilt(signal.butter(2, 4.0, fs=1.0 / h, output='sos'), w)
        dist = w * dist_std / max(w.std(), 1e-12)
    for i in range(n):
        if fb:
            ucmd[i] = ulog[i] - taper[i] * (lpv[i - nfd] if i >= nfd else 0.0)
        ui = ucmd[i - nD] if i >= nD else ucmd[0]
        net = ui + dist[i] - kk[i] * a
        if abs(r) < vstick and abs(net) <= F:
            r = 0.0
        else:
            fr = F * (math.copysign(1.0, r) if abs(r) >= vstick else math.copysign(1.0, net))
            r_new = r + (net - b * r - fr) / J * h
            if abs(r) >= vstick and r * r_new < 0:
                r_new = 0.0
            r = r_new
        a = a + r * h
        ang[i] = a; rate[i] = r
        if fb:
            lp = lp + alpha * (round(r) - lp); lpv[i] = lp
    return tt, ang, rate, ucmd


def simulate(t_u, u_val, t_s, v_s, D, J, b, F, k_scale=1.0, h=0.001, vstick=0.05, t_span=None, **kw):
    """sim_fine, sampled at the TRUE carState times and quantised to the logged LSBs (0.1 deg, 1 deg/s)."""
    tt, ang, rate, ucmd = sim_fine(t_u, u_val, t_s, v_s, D, J, b, F, k_scale, h, vstick, t_span, **kw)
    sa = np.round(np.interp(t_s, tt, ang) / 0.1) * 0.1
    sr = np.round(np.interp(t_s, tt, rate))
    return sa, sr, tt, ucmd
