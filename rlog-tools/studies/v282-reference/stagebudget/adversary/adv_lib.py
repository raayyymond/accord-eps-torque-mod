# -*- coding: utf-8 -*-
"""ADVERSARY stream, independent measurement core.  Shares NO code with the surface/amplitude/attribution
streams: every spectral quantity below is written from scratch here so that agreement is corroboration and
disagreement is a finding.

What it measures (MEASUREMENT of a closed-loop transfer from a logged input and a logged output):
    X  model desired lateral accel   controlsState.desiredCurvature * v^2
    Y  achieved lateral accel        livePose.angularVelocityDevice.z * v
    Z  controller setpoint           controlsState...torqueState.desiredLateralAccel
    W  steering wheel angle (deg)    carState.steeringAngleDeg
    A  controller's own achieved     controlsState...torqueState.actualLateralAccel

FIVE gain estimators per frequency bin, because the whole regime-B question is estimator choice:
    H1    = Sxy / Sxx                  (standard; unbiased for noise on Y, biased DOWN by noise on X)
    H2    = Syy / conj(Sxy)            (biased UP by noise on Y, unbiased for noise on X)
    Htot  = sqrt(Syy / Sxx)            (power ratio; hard UPPER bound on any linear gain)
    Hcoh  = |H1| * gamma               (the part of the output the input provably explains -> LOWER-ish)
    Hreg  = time-domain band-passed regression of y on x at the best lag (no cross-spectrum at all)
Plus gamma^2 (coherence) and its own null floor, and the Rice/variance bias factor for |H1|.

Tapers: hann, blackman-harris (sidelobes -92 dB vs -31 dB: the leakage control), and 3-taper DPSS
multitaper.  Detrend: mean-only and linear.  Window length is a free parameter.
"""
import math
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.signal.windows import dpss

FS = 100.0
KIT = Path(__file__).resolve().parents[5]
CACHE = KIT / "analysis-2020accord" / "_scratch" / "cache" / "v282ref"
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

# route -> (my group label, eps mode, flown AccordRefFilter, flown AccordTorqueKi, flown SteerKP)
# read from hsurface/surface/params_all.json (each route's own initData), not from labels.
ROUTES = {
    "00000064--ce6b0b0ebb": dict(g="V282", eps="V282", rf=0.0, ki=0.3, kp=0.9, fam="V282"),
    "00000065--b9f78988bd": dict(g="V282", eps="V282", rf=0.0, ki=0.3, kp=0.9, fam="V282"),
    "0000006c--2bc842dbac": dict(g="V282", eps="V282", rf=0.0, ki=0.3, kp=0.9, fam="V282"),
    "00000039--f56039af87": dict(g="V282old", eps="V282", rf=0.0, ki=None, kp=0.8, fam="V282old"),
    "0000003a--283a39a1d6": dict(g="V282old", eps="V282", rf=0.0, ki=None, kp=0.8, fam="V282old"),
    "0000003c--927965c2b4": dict(g="V282old", eps="V282", rf=0.0, ki=None, kp=0.8, fam="V282old"),
    "0000006c--68c6e94b17": dict(g="T64", eps="V293", rf=0.06, ki=0.3, kp=1.0, fam="RF06"),
    "0000006d--05e83bb04f": dict(g="T64", eps="V293", rf=0.06, ki=0.3, kp=1.0, fam="RF06"),
    "0000006e--6ca3e014fd": dict(g="T64B", eps="V293", rf=0.06, ki=0.3, kp=1.0, fam="RF06"),
    "00000076--d0b7ea7e4d": dict(g="T5", eps="V293", rf=0.12, ki=0.3, kp=1.0, fam="RF12"),
    "00000075--6c8687d5bd": dict(g="T4", eps="V293", rf=0.12, ki=0.6, kp=0.85, fam="RF12"),
    "00000072--8001fc3048": dict(g="T3", eps="V293", rf=0.12, ki=0.6, kp=0.85, fam="RF12"),
    "00000073--79fd149dd8": dict(g="T3", eps="V293", rf=0.12, ki=0.6, kp=0.85, fam="RF12"),
    "00000070--717f5a7866": dict(g="T2", eps="V293", rf=0.0, ki=0.15, kp=0.3, fam="RF00T"),
    "00000071--f2c9d073a3": dict(g="T2", eps="V293", rf=0.0, ki=0.3, kp=0.85, fam="RF00T"),
}
TORQ = [r for r, d in ROUTES.items() if d["eps"] == "V293"]
V282 = [r for r, d in ROUTES.items() if d["g"] == "V282"]

SPD = [(0.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 40.0)]
SPDN = ["0-8", "8-15", "15-22", "22+"]
ACUT = [(0.0, 0.3), (0.3, 1.0), (1.0, 99.0)]
ACUTN = ["A1", "A2", "A3"]
CH = ["X", "Y", "Z", "W", "A"]


# ----------------------------------------------------------------------------- loading
def load(route):
    D = np.load(CACHE / f"{route}.npz", allow_pickle=True)
    t = D["t_cs"]

    def I(tk, k):
        return np.interp(t, D[tk], D[k])

    v = I("t_cst", "vego")
    S = dict(route=route, t=t, v=v,
             on=(D["cs_active"] > 0.5) & (np.interp(t, D["t_cc"], D["lat_active"]) > 0.5),
             pressed=I("t_cst", "spress") > 0.5,
             X=np.nan_to_num(D["cs_des_curv"] * v * v),
             Y=np.nan_to_num(I("t_pose", "pose_wz") * v),
             Z=np.nan_to_num(D["cs_la_des"]),
             W=np.nan_to_num(I("t_cst", "sa_deg")),
             A=np.nan_to_num(D["cs_la_act"]),
             out=np.nan_to_num(D["cs_out"]))
    return S


def windows(S, n, stride=None):
    """Non-overlapping (default) windows of n samples that are wholly inside one laterally-engaged,
    hands-off, gap-free stretch.  Returns list of start indices."""
    stride = stride or n
    m = S["on"] & ~S["pressed"] & np.isfinite(S["v"])
    t = S["t"]
    idx, i, N = [], 0, len(m)
    while i < N:
        if not m[i]:
            i += 1
            continue
        j = i
        while j + 1 < N and m[j + 1] and (t[j + 1] - t[j]) < 0.04:
            j += 1
        k = i
        while k + n <= j + 1:
            idx.append(k)
            k += stride
        i = j + 1
    return idx


# ----------------------------------------------------------------------------- spectra
def taper_set(n):
    """Returns {name: (K, n) array of tapers}.  Each taper is normalised to unit power sum so that
    |FFT|^2 is a consistent PSD estimate across tapers."""
    out = {}
    for nm, w in (("hann", signal.windows.hann(n, sym=False)),
                  ("bh", signal.windows.blackmanharris(n, sym=False))):
        out[nm] = (w / math.sqrt((w ** 2).sum()))[None, :]
    d = dpss(n, 2.0, Kmax=3, sym=False)
    out["mt3"] = d / np.sqrt((d ** 2).sum(1))[:, None]
    return out


def spec_route(S, n, nbmax=70, detrends=("lin",), tapers=("hann", "bh", "mt3")):
    """Per-window complex spectra.  Returns dict with meta arrays and F[(detrend,taper)] of shape
    (nwin, nch, K, nbmax) complex64."""
    T = taper_set(n)
    idx = windows(S, n)
    if not idx:
        return None
    nb = min(nbmax, n // 2)
    tt = np.arange(n) - (n - 1) / 2.0
    tt2 = float((tt ** 2).sum())
    F = {}
    for dn in detrends:
        for tn in tapers:
            F[(dn, tn)] = np.zeros((len(idx), len(CH), T[tn].shape[0], nb), np.complex64)
    meta = dict(v=[], ap95=[], sa50=[], sa95=[], xrms=[], yrms=[], i0=[])
    for wi, k in enumerate(idx):
        sl = slice(k, k + n)
        meta["v"].append(float(np.median(S["v"][sl])))
        meta["ap95"].append(float(np.percentile(np.abs(S["X"][sl]), 95)))
        meta["sa50"].append(float(np.median(np.abs(S["W"][sl]))))
        meta["sa95"].append(float(np.percentile(np.abs(S["W"][sl]), 95)))
        meta["xrms"].append(float(np.std(S["X"][sl])))
        meta["yrms"].append(float(np.std(S["Y"][sl])))
        meta["i0"].append(k)
        for ci, c in enumerate(CH):
            x = S[c][sl].astype(np.float64)
            xm = x - x.mean()
            xl = xm - tt * (float((tt * xm).sum()) / tt2)
            for dn in detrends:
                u = xl if dn == "lin" else xm
                for tn in tapers:
                    F[(dn, tn)][wi, ci, :, :] = np.fft.rfft(T[tn] * u[None, :], axis=1)[:, :nb]
    for kk in meta:
        meta[kk] = np.asarray(meta[kk], np.float64)
    meta["fr"] = np.arange(nb) * (FS / n)
    meta["n"] = n
    meta["route"] = S["route"]
    return dict(meta=meta, F=F)


# ----------------------------------------------------------------------------- estimators
def cell(Fsel, ix, iy, f1, f2, fr):
    """Fsel: (nwin, nch, K, nb) complex.  Accumulate over the selected windows and tapers, then form the
    five estimators per bin and power-weight them across the band."""
    if Fsel.shape[0] == 0:
        return None
    b = (fr >= f1) & (fr < f2)
    if b.sum() < 1:
        return None
    Xf = Fsel[:, ix][:, :, b]           # (nwin, K, nbb)
    Yf = Fsel[:, iy][:, :, b]
    nseg = Xf.shape[0] * Xf.shape[1]
    Sxx = (np.abs(Xf) ** 2).sum((0, 1))
    Syy = (np.abs(Yf) ** 2).sum((0, 1))
    Sxy = (np.conj(Xf) * Yf).sum((0, 1))
    H1 = Sxy / np.maximum(Sxx, 1e-300)
    g2 = np.clip(np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-300), 1e-9, 1.0)
    H2 = Syy / np.maximum(np.abs(Sxy), 1e-300)
    Ht = np.sqrt(Syy / np.maximum(Sxx, 1e-300))
    w = Sxx
    aw = lambda a: float(np.average(a, weights=w))
    # Rice/variance bias factor on |H1|: E|H1|^2 ~ |H|^2 (1 + (1-g2)/(2 nseg g2))
    bias = np.sqrt(1.0 + (1.0 - g2) / np.maximum(2.0 * nseg * g2, 1e-9))
    fc = aw(fr[b])
    ph = float(np.angle((Sxy * w).sum()))
    # phase-SLOPE lag: unbiased by the spectral tilt inside the band, unlike phase-at-band-centre.
    gd = float("nan")
    if b.sum() >= 3:
        fb = fr[b]
        phb = np.unwrap(np.angle(H1))
        ww = w * g2
        A = np.vstack([2 * np.pi * fb, np.ones_like(fb)]).T
        sol = np.linalg.lstsq(A * np.sqrt(ww)[:, None], phb * np.sqrt(ww), rcond=None)[0]
        gd = -sol[0] * 1000.0
    return dict(lag_gd_ms=gd,
                H1=aw(np.abs(H1)), H1_db=aw(np.abs(H1) / bias), H2=aw(H2), Htot=aw(Ht),
                Hcoh=aw(np.abs(H1) * np.sqrt(g2)), g2=aw(g2), nseg=int(nseg), nwin=int(Xf.shape[0]),
                nbin=int(b.sum()), bias=aw(bias), fc=fc, phase_deg=math.degrees(ph),
                lag_ms=-math.degrees(ph) / 360.0 / max(fc, 1e-9) * 1000.0,
                g2null=float(1.0 - 0.05 ** (1.0 / max(nseg - 1, 1))),
                inrms=float(np.sqrt(Sxx.sum() / max(nseg, 1)) * np.sqrt(2 * (FS / len(fr) / 2))),
                prat=float(np.sqrt(Syy.sum() / max(Sxx.sum(), 1e-300))))


def bp(x, f1, f2, order=4):
    sos = signal.butter(order, [f1, f2], btype="band", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x)


def reg_gain(x, y, f1, f2, maxlag=0.9, trim=1500, order=2):
    """Time-domain estimator, entirely outside the cross-spectrum family.  Band-pass both, DISCARD the
    filter's edge transient (a control showed an untrimmed 8th-order band-pass reads a known 0.800 as
    0.686), then for each lag fit y(t) = g * x(t-tau) by least squares; report g, tau and R^2."""
    xb, yb = bp(x, f1, f2, order), bp(y, f1, f2, order)
    if len(xb) <= 2 * trim + int(maxlag * FS) + 200:
        return None
    xb, yb = xb[trim:len(xb) - trim], yb[trim:len(yb) - trim]
    L = int(maxlag * FS)
    best = None
    for k in range(0, L + 1):
        a, b = xb[:len(xb) - k], yb[k:]
        den = float(a @ a)
        if den <= 0:
            continue
        g = float(a @ b) / den
        r2 = (float(a @ b) ** 2) / (den * max(float(b @ b), 1e-30))
        if best is None or r2 > best[2]:
            best = (g, k / FS, r2)
    return best


# ----------------------------------------------------------------------------- positive controls
def _self_test():
    rng = np.random.default_rng(3)
    n, N = 1024, 1024 * 40
    t = np.arange(N) / FS
    msg = []

    # (1) known gain 0.8, lag 0.25 s, broadband low-frequency input, clean.
    x = signal.sosfiltfilt(signal.butter(2, 0.8, fs=FS, output="sos"), rng.standard_normal(N)) * 3
    y = 0.8 * np.roll(x, 25)
    S = dict(route="syn", t=t, v=np.full(N, 20.0), on=np.ones(N, bool), pressed=np.zeros(N, bool),
             X=x, Y=y, Z=y, W=y, A=y, out=y)
    sp = spec_route(S, n, detrends=("lin",), tapers=("hann",))
    r = cell(sp["F"][("lin", "hann")], 0, 1, 0.1, 0.6, sp["meta"]["fr"])
    assert abs(r["H1"] - 0.8) < 0.02, r
    assert abs(r["lag_gd_ms"] - 250) < 10, r          # phase-SLOPE: must be tight
    assert abs(r["lag_ms"] - 250) < 35, r             # phase-at-band-centre: knowingly loose
    assert r["g2"] > 0.98, r
    msg.append(f"  (1) clean gain 0.8 lag 250 ms -> H1 {r['H1']:.3f}  lag(slope) {r['lag_gd_ms']:.0f} ms  "
               f"lag(band-centre) {r['lag_ms']:.0f} ms  g2 {r['g2']:.3f}\n"
               f"      NOTE: the band-centre construction (the one the surface stream reports) reads "
               f"{r['lag_ms'] - 250:+.0f} ms on a KNOWN 250 ms.")

    # (2) THE REGIME-B CONTROL.  Known in-band gain 1.10 with heavy INCOHERENT output motion, sized so the
    #     output/input in-band power ratio is ~3 and the coherence lands near 0.7 -- exactly regime B's cell.
    #     Any estimator that returns ~2.5 here is manufacturing the finding.
    xb = signal.sosfiltfilt(signal.butter(2, [0.3, 3.0], btype="band", fs=FS, output="sos"),
                            rng.standard_normal(N))
    xb *= 0.03 / xb.std()
    ycoh = 1.10 * np.roll(xb, 8)
    nz = signal.sosfiltfilt(signal.butter(2, [0.4, 2.5], btype="band", fs=FS, output="sos"),
                            rng.standard_normal(N))
    for a in (0.6, 1.0, 2.0):
        yy = ycoh + nz * (a * 0.03 / nz.std())
        S2 = dict(S); S2.update(X=xb, Y=yy, Z=yy, W=yy, A=yy)
        sp2 = spec_route(S2, n, detrends=("lin",), tapers=("hann", "bh", "mt3"))
        rr = {tn: cell(sp2["F"][("lin", tn)], 0, 1, 0.6, 1.2, sp2["meta"]["fr"])
              for tn in ("hann", "bh", "mt3")}
        h = rr["hann"]
        assert abs(h["H1"] - 1.10) < 0.12, (a, h)
        msg.append(f"  (2) noise x{a:.1f}: true 1.10 -> H1 {h['H1']:.3f} (bh {rr['bh']['H1']:.3f} "
                   f"mt3 {rr['mt3']['H1']:.3f}) H2 {h['H2']:.2f} Htot {h['Htot']:.2f} "
                   f"Hcoh {h['Hcoh']:.2f} g2 {h['g2']:.2f} prat {h['prat']:.2f}")

    # (3) LEAKAGE control.  Put a LARGE coherent gain (4.0) at 1.2-2.4 Hz and gain 1.0 at 0.6-1.2, and
    #     check how much of the 4.0 leaks into the 0.6-1.2 reading under each taper.
    lo = signal.sosfiltfilt(signal.butter(4, [0.6, 1.2], btype="band", fs=FS, output="sos"),
                            rng.standard_normal(N))
    hi = signal.sosfiltfilt(signal.butter(4, [1.3, 2.4], btype="band", fs=FS, output="sos"),
                            rng.standard_normal(N))
    lo *= 0.03 / lo.std(); hi *= 0.03 / hi.std()
    S3 = dict(S); S3.update(X=lo + hi, Y=1.0 * lo + 4.0 * hi)
    sp3 = spec_route(S3, n, detrends=("lin",), tapers=("hann", "bh", "mt3"))
    lk = {tn: cell(sp3["F"][("lin", tn)], 0, 1, 0.6, 1.2, sp3["meta"]["fr"])["H1"]
          for tn in ("hann", "bh", "mt3")}
    msg.append(f"  (3) leakage control (1.0 in band, 4.0 just above): hann {lk['hann']:.3f} "
               f"bh {lk['bh']:.3f} mt3 {lk['mt3']:.3f}  (true 1.0)")
    assert lk["hann"] < 1.35 and lk["bh"] < 1.35, lk

    # (4) time-domain regression control
    g, tau, r2 = reg_gain(x, y, 0.1, 0.6)
    assert abs(g - 0.8) < 0.03 and abs(tau - 0.25) < 0.02, (g, tau, r2)
    msg.append(f"  (4) reg_gain clean -> g {g:.3f} tau {tau:.3f} s r2 {r2:.3f} OK")
    return "\n".join(msg)


if __name__ == "__main__":
    print("ADVERSARY core positive controls")
    print(_self_test())
