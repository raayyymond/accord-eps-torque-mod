#!/usr/bin/env python3
"""selfint_lib -- the column-impedance instrument.

Measures the transfer  `theta_dot (column angular rate) -> torsion-bar torque`  on the existing
route caches, and decomposes it into inertial / damping / stiffness parts.  Written for the V85
session's test of the operator's self-interference thesis; kept general so any future route drops in.

CHANNEL CHOICES -- deliberately the SAME ones `studies/grind/compare_r67_v81_grind.py` /
`studies/grind/compare_v75_v76_v80_grind.py` use, so every number here is commensurable with the kit's record:

    bar torque   d["tq"]        0x18F bytes 0-1, i16be * -1.0, COUNTS  (LSB is 8 counts, see below)
    column rate  d["rate_c"]    0x14A bytes 2-3, i16be * -1.0, 1 deg/s LSB
    column angle d["ang"]       0x14A bytes 0-1, i16be * -0.1, 0.1 deg LSB
    command      d["sc_tq"]     0x0E4 bytes 0-1 on **sendcan src1** (NOT can src0)
    engagement   d["cc_lat"]    carControl.latActive
    fs           _r4f_lib.fs_lattice(d) -- (n-1)/(t[-1]-t[0]) over the longest gap-free run.
                 🛑 NEVER 1/median(dt).

WHY `rate_c` AND NOT A DOUBLE DIFFERENCE OF `ang`  [EVIDENCE, measured -- see `scale_check()`]
    `rate_c` is the EPS's own derivative, computed at its ~1 kHz tick BEFORE the 100 Hz CAN
    sampling.  Below 2 Hz, |rate_c| / (omega * |ang|) = 1.00 +/- 0.05 at gamma^2 = 0.99 across
    route 67, so the two DBC scales are mutually consistent and `rate_c` is genuinely d(ang)/dt.
    Above ~5 Hz they diverge, and the direction says which one is noisy: `ang` is 0.1 deg
    quantised and REPEATS on 73.8% of consecutive frames, so at 20 Hz its own LSB is worth
    0.1 deg * omega = 12.6 deg/s -- 12.6x COARSER than `rate_c`'s 1 deg/s LSB.  Differencing
    `ang` twice at 100 Hz would amplify that by a further omega^2.
    ⇒ the whole analysis is built on `rate_c`, and theta / theta_ddot are obtained from it by
    EXACT spectral integration / differentiation (divide / multiply the DFT bin by j*omega).
    That differentiator's own transfer is therefore exactly `j*omega` inside the analysis band and
    exactly zero outside it -- no roll-off, no group delay, nothing to correct for.

INSTRUMENT CORRECTIONS APPLIED
    * `0x18F` payload is ~9.9 ms stale vs `0x14A`'s  (memory/accord-0x18f-payload-one-frame-stale).
      Applied in the frequency domain as T(f) *= exp(+j*2*pi*f*TAU_18F).  `TAU_18F` is a module
      constant so any claim can be re-run at tau=0 to price its own sensitivity.
    * `rate_f` (the 0x18F rate copy) is NOT used anywhere -- it rides the stale message and its
      stored scale is 0.8x truth.
    * `tq`'s LSB is **8 counts**, not 1 (measured: min positive step in `np.unique(tq)` is 8.0).
      Quantisation floor is still ~0.8 counts rms in a 6 Hz band, i.e. >100x below every band
      level measured, so it is not a limitation -- but it is not 1, and a noise-floor claim that
      assumed 1 would be 8x optimistic.

SIGN CONVENTION AND WHAT THE FIT MEANS
    Fit, per frequency, the mechanical impedance seen by the column:

        Z(f) = T(f) / Theta_dot(f)
        T = A*(-theta_ddot) + B*(-theta_dot) + C*(theta) + residual
          =>  Z = -B  +  j*( -omega*A - C/omega )

    🛑 Real(Z) alone determines B.  A and C are **perfectly collinear at a single frequency** --
    -theta_ddot = +omega^2 * theta for a sinusoid -- so no single-frequency method can separate
    "inertial" from "stiffness".  Only the FREQUENCY DEPENDENCE of Imag(Z) separates them, which
    is why `fit_ABC` is a wideband fit and the per-frequency table reports the reactive part as
    ONE number with the model's split shown alongside.
    A > 0 means the bar torque OPPOSES angular acceleration, i.e. exactly the operator's
    "opposing torque under LKAS-driven angular acceleration due to the steering wheel inertia".
    A is in **counts / (rad/s^2)**;  J_eff [kg m^2] = A * S_T, with S_T the (UNKNOWN, carried
    symbolically) counts->N.m calibration of `STEER_TORQUE_SENSOR`.

EPISODES
    An EPISODE is a maximal run of frames meeting the condition mask, on an unbroken sample
    lattice (no dt > 15 ms), capped at `EP_MAX` samples so one 60 s engagement does not become a
    single unit.  Spectra are averaged WITHIN an episode over non-overlapping Hann blocks, then
    ACROSS episodes.  Every CI in this module bootstraps over EPISODES, never windows
    (memory/feedback-episodes-not-windows).  K is always reported.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import _r4f_lib as R4F  # noqa: E402

D2R = np.pi / 180.0
TAU_18F = 0.00999           # s -- 0x18F payload staleness vs 0x14A.  Set to 0.0 to price it.
NPERSEG = 512               # 5.12 s @100 Hz -> 0.195 Hz bins.  Resolves 7.79 vs 8.56 Hz.
EP_MAX = 2048               # 20.48 s -- the episode cap
LATTICE_GAP = 0.015         # s -- a frame gap above this breaks the lattice

# The kit's bands, verbatim from `compare_v75_v76_v80_grind.BANDS_EXT`.
BANDS = {"6-9": (6.0, 9.0), "17-23": (17.0, 23.0), "26-31": (26.0, 31.0),
         "32-38": (32.0, 38.0), "40-49": (40.0, 49.0)}
# The three symptom frequencies the V85 brief names.
FTARGETS = [("S2 micro-ratchet", 7.79), ("S1 grind #1", 20.5), ("the ring", 27.5)]

ROUTES = {
    "V84/r6d":  ("_scratch/cache/r6d",  "r6ds",  12),
    "V83a/r68": ("_scratch/cache/r68x", "r68xs",  8),
    "V81/r67":  ("_scratch/cache/r67x", "r67xs", 14),
    "V80/r66":  ("_scratch/cache/r66x", "r66xs", 15),
}


# ---------------------------------------------------------------------------- loading -----------
def segs(route):
    cache, pfx, n = ROUTES[route]
    for s in range(n):
        p = ROOT / cache / f"{pfx}{s}.npz"
        if p.exists():
            d = {k: v for k, v in np.load(p).items()}
            d["_fs"] = R4F.fs_lattice(d)
            d["_seg"] = s
            d["_route"] = route
            yield d


def lattice_ok(d):
    t = np.asarray(d["t"], float)
    ok = np.ones(len(t), bool)
    ok[1:] = np.diff(t) < LATTICE_GAP
    return ok


def sustained(x, fs, fc=2.0):
    """Low-passed |x| -- the kit's `_r31_common.sustained`, re-implemented locally to avoid the
    NaN guard's interp cost.  Used as the hands-off proxy on the bar."""
    x = np.asarray(x, float)
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[f > fc] = 0
    return np.abs(np.fft.irfft(X, n=len(x)) + x.mean())


# ---------------------------------------------------------------------------- masks -------------
def mask_engaged(d):
    return d["cc_lat"] > 0.5


def mask_manual(d):
    return (d["cc_lat"] < 0.5) & (np.abs(d["cs_v"]) > 1.0)


def mask_handsoff(d, thr=400.0):
    """`steeringPressed` == 0 AND the 0-2 Hz bar effort below `thr` counts.

    ⚠ `cs_press` is openpilot's |steeringTorque| > 1200-count threshold, so on its own it is a
    weak hands-off detector -- 268 s of route 66 is 'hands off' by that flag while the driver is
    steering manually.  The sustained-bar cut is the real gate; `thr` is swept in the report.
    """
    fs = d["_fs"]
    return (d["cs_press"] < 0.5) & (sustained(np.asarray(d["tq"], float), fs, 2.0) < thr)


# ---------------------------------------------------------------------------- episodes ----------
def episodes(d, mask, nperseg=NPERSEG, ep_max=EP_MAX):
    """Yield (i0, i1) half-open index ranges: maximal lattice-contiguous runs of `mask`, split at
    `ep_max`, each at least `nperseg` long and truncated to a whole number of blocks."""
    m = np.asarray(mask, bool) & lattice_ok(d)
    idx = np.flatnonzero(m)
    if not len(idx):
        return
    starts = [idx[0]]
    ends = []
    for a, b in zip(idx[:-1], idx[1:]):
        if b != a + 1:
            ends.append(a + 1)
            starts.append(b)
    ends.append(idx[-1] + 1)
    for s, e in zip(starts, ends):
        while e - s >= nperseg:
            n = min(ep_max, e - s)
            n -= n % nperseg
            yield (s, s + n)
            s += n


# ---------------------------------------------------------------------------- spectra -----------
def ep_spectra(d, i0, i1, nperseg=NPERSEG, tau=None, hop=None):
    """Within-episode averaged auto/cross spectra of (theta_dot [rad/s], T [counts]).

    Returns (f, Sxx, Syy, Sxy, nblk).  `Sxy = conj(X) * Y`, so H1 = Sxy/Sxx = Z = T/theta_dot.
    The 0x18F staleness is removed here, in the frequency domain: T_true = T_rec * exp(+j w tau).
    `hop` defaults to nperseg//2 (50% overlap, the Welch standard) -- overlapping blocks WITHIN an
    episode are not independent EPISODES and are never used as bootstrap units.
    """
    tau = TAU_18F if tau is None else tau
    hop = nperseg // 2 if hop is None else hop
    fs = d["_fs"]
    x_all = np.asarray(d["rate_c"], float) * D2R
    y_all = np.asarray(d["tq"], float)
    w = np.hanning(nperseg)
    f = np.fft.rfftfreq(nperseg, 1 / fs)
    rot = np.exp(1j * 2 * np.pi * f * tau)
    r = np.arange(nperseg, dtype=float)
    Sxx = np.zeros(len(f))
    Syy = np.zeros(len(f))
    Sxy = np.zeros(len(f), complex)
    n = 0
    for i in range(i0, i1 - nperseg + 1, hop):
        x = x_all[i:i + nperseg]
        y = y_all[i:i + nperseg]
        if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
            continue
        x = x - np.polyval(np.polyfit(r, x, 1), r)
        y = y - np.polyval(np.polyfit(r, y, 1), r)
        X = np.fft.rfft(x * w)
        Y = np.fft.rfft(y * w) * rot
        Sxx += np.abs(X) ** 2
        Syy += np.abs(Y) ** 2
        Sxy += np.conj(X) * Y
        n += 1
    if not n:
        return f, None, None, None, 0
    return f, Sxx / n, Syy / n, Sxy / n, n


def collect(route, mask_fn, nperseg=NPERSEG, extra=None, tau=None, ep_max=EP_MAX):
    """One record per episode.  `extra(d, i0, i1)` may add per-episode covariates."""
    out = []
    for d in segs(route):
        m = mask_fn(d)
        for i0, i1 in episodes(d, m, nperseg, ep_max):
            f, Sxx, Syy, Sxy, nb = ep_spectra(d, i0, i1, nperseg, tau)
            if nb < 2:
                continue
            v = np.abs(np.asarray(d["cs_v"], float)[i0:i1])
            rec = dict(f=f, Sxx=Sxx, Syy=Syy, Sxy=Sxy, nblk=nb, route=route, seg=d["_seg"],
                       i0=i0, i1=i1, sec=(i1 - i0) / d["_fs"], fs=d["_fs"],
                       v_mean=float(v.mean()), v_p5=float(np.percentile(v, 5)),
                       v_p95=float(np.percentile(v, 95)))
            if extra is not None:
                rec.update(extra(d, i0, i1))
            out.append(rec)
    return out


def stack(recs):
    """Average spectra ACROSS episodes (block-count weighted).  Returns f, Sxx, Syy, Sxy, K."""
    if not recs:
        return None, None, None, None, 0
    f = recs[0]["f"]
    wgt = np.array([r["nblk"] for r in recs], float)
    Sxx = np.tensordot(wgt, np.array([r["Sxx"] for r in recs]), 1) / wgt.sum()
    Syy = np.tensordot(wgt, np.array([r["Syy"] for r in recs]), 1) / wgt.sum()
    Sxy = np.tensordot(wgt, np.array([r["Sxy"] for r in recs]), 1) / wgt.sum()
    return f, Sxx, Syy, Sxy, len(recs)


def coh(Sxx, Syy, Sxy):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.abs(Sxy) ** 2 / (Sxx * Syy)


# ---------------------------------------------------------------------------- the fit -----------
def fit_ABC(f, Sxx, Sxy, band=(4.0, 32.0), weight="coh", Syy=None):
    """Weighted complex least squares of  Z(f) = -B + j*(-omega*A - C/omega)  to H1 = Sxy/Sxx.

    Real and imaginary parts decouple:
        Real(Z) = -B                      -> B from a weighted mean
        Imag(Z) = -omega*A - C/omega      -> A, C from a 2-parameter weighted LS in omega
    Weight = coherent input power  gamma^2 * Sxx  (the Bendat-Piersol optimum for H1), which is
    what stops one loud low-frequency episode from setting the high-frequency answer.
    Returns dict(A=counts/(rad/s^2), B=counts/(rad/s), C=counts/rad, f0=Hz or nan, n=bins).
    """
    sel = (f >= band[0]) & (f <= band[1]) & (f > 0)
    om = 2 * np.pi * f[sel]
    Z = Sxy[sel] / Sxx[sel]
    if weight == "coh" and Syy is not None:
        wgt = coh(Sxx, Syy, Sxy)[sel] * Sxx[sel]
    else:
        wgt = Sxx[sel]
    wgt = np.nan_to_num(wgt, nan=0.0, posinf=0.0, neginf=0.0)
    if wgt.sum() <= 0:
        return dict(A=np.nan, B=np.nan, C=np.nan, f0=np.nan, n=int(sel.sum()))
    B = -float(np.sum(wgt * Z.real) / np.sum(wgt))
    # Imag(Z) = -A*om - C*(1/om)
    M = np.stack([-om, -1.0 / om], axis=1)
    W = wgt
    lhs = M.T @ (W[:, None] * M)
    rhs = M.T @ (W * Z.imag)
    try:
        A, C = np.linalg.solve(lhs, rhs)
    except np.linalg.LinAlgError:
        return dict(A=np.nan, B=np.nan, C=np.nan, f0=np.nan, n=int(sel.sum()))
    f0 = np.sqrt(C / A) / (2 * np.pi) if (A > 0 and C > 0) else np.nan
    return dict(A=float(A), B=float(B), C=float(C), f0=float(f0), n=int(sel.sum()))


def boot_fit(recs, band=(4.0, 32.0), nboot=2000, seed=8585, tau=None):
    """Episode bootstrap of `fit_ABC`.  Returns (point, {key: (lo, hi)}, samples)."""
    rng = np.random.default_rng(seed)
    f, Sxx, Syy, Sxy, K = stack(recs)
    pt = fit_ABC(f, Sxx, Sxy, band, Syy=Syy)
    if K < 3:
        return pt, {k: (np.nan, np.nan) for k in ("A", "B", "C", "f0")}, None
    keys = ("A", "B", "C", "f0")
    smp = {k: [] for k in keys}
    n = len(recs)
    for _ in range(nboot):
        j = rng.integers(0, n, n)
        f2, sx, sy, sc, _ = stack([recs[i] for i in j])
        r = fit_ABC(f2, sx, sc, band, Syy=sy)
        for k in keys:
            smp[k].append(r[k])
    ci = {k: (float(np.nanpercentile(smp[k], 2.5)), float(np.nanpercentile(smp[k], 97.5)))
          for k in keys}
    return pt, ci, smp


# ---------------------------------------------------------------------------- decomposition -----
def decompose(f, Sxx, Syy, Sxy, ftar, halfwidth=1.0):
    """Fraction of BAR variance at `ftar` +/- halfwidth explained by each phase direction.

    quad  = in phase with -theta_dot   (damping / friction)   -> Real(Z)
    react = in phase with  theta       (== in phase with -theta_ddot; they are THE SAME direction
            at a single frequency and cannot be separated here) -> Imag(Z)
    resid = 1 - gamma^2   (everything not linearly explained by the column kinematics at all)
    quad + react == gamma^2 identically.
    """
    sel = (f >= ftar - halfwidth) & (f <= ftar + halfwidth)
    sxx, syy = Sxx[sel].sum(), Syy[sel].sum()
    sxy = Sxy[sel].sum()
    if syy <= 0 or sxx <= 0:
        return dict(f=ftar, g2=np.nan, quad=np.nan, react=np.nan, resid=np.nan)
    g2 = abs(sxy) ** 2 / (sxx * syy)
    Z = sxy / sxx
    quad = (Z.real ** 2) * sxx / syy
    react = (Z.imag ** 2) * sxx / syy
    # 🛑 THE SIGN OF Imag(Z) IS THE WHOLE POINT.  Z = -B + j(-omega*A - C/omega):
    #   Imag(Z) < 0  =>  A > 0  =>  T opposes theta_ddot   -- the operator's INERTIAL reaction
    #   Imag(Z) > 0  =>  C < 0  =>  T opposes theta        -- a STIFFNESS reaction
    # Both are "in phase with theta" and both land in `react`; only the sign separates them, and
    # a magnitude-only decomposition would report the two OPPOSITE mechanisms identically.
    return dict(f=ftar, g2=float(g2), quad=float(quad), react=float(react),
                react_sign=("inertial(-J.thddot)" if Z.imag < 0 else "stiffness(-k.theta)"),
                damp_sign=("dissipative" if Z.real < 0 else "ANTI-damping"),
                phase_deg=float(np.degrees(np.angle(Z))),
                resid=float(1 - g2), Zre=float(Z.real), Zim=float(Z.imag),
                Sxx=float(sxx), Syy=float(syy), nbin=int(sel.sum()))


# ------------------------------------------------------- the TWO-INERTIA (resonant) model -------
# The 3-parameter (A,B,C) impedance above is a LUMPED model and the data refute it (the measured
# phase of T/theta sweeps 0 -> -90 -> 180 across 5-45 Hz, which no single J,b,k can produce).  The
# physically correct minimal model, given that the CAN angle/rate is the sensor BELOW the torsion
# bar and the steering wheel hangs above it on that bar:
#
#     upper column:  J*thddot_w = T_d - T_bar - b*thdot_w        T_bar = k*(th_w - th_p)
#     eliminate th_w (hands off, T_d = 0):
#
#         T(s) / Theta_p(s) = -k * (J s^2 + b s) / (J s^2 + b s + k)
#         Z(s) = T/Theta_dot_p = -k * (J s + b) / (J s^2 + b s + k)
#              = -k * (s + 2*zeta*wn) / (s^2 + 2*zeta*wn*s + wn^2)          wn^2 = k/J
#
# Limits, and they are the whole diagnostic:
#     w << wn :  T -> +J*w^2*Theta = -J*thddot   ... the operator's INERTIAL REACTION
#     w >> wn :  T -> -k*Theta                   ... a pure STIFFNESS against a wheel that its own
#                                                    inertia has pinned.  NOT an inertial term.
# k is in counts/rad and J in counts*s^2/rad; wn is calibration-FREE.
def Zres(f, k, fn, zeta):
    s = 1j * 2 * np.pi * np.asarray(f, float)
    wn = 2 * np.pi * fn
    return -k * (s + 2 * zeta * wn) / (s ** 2 + 2 * zeta * wn * s + wn ** 2)


def frf(Sxx, Syy, Sxy, est="geo"):
    """H1 (input-noise biased LOW), H2 (output-noise biased HIGH) or their geometric mean.

    |H2| = |H1| / gamma^2 identically and the PHASES are identical, so the estimator choice moves
    MAGNITUDE only -- never a phase conclusion.  `geo` = H1/gamma is the total-least-squares-style
    compromise and is what every magnitude number in the report uses unless stated.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        H1 = Sxy / Sxx
        g2 = np.abs(Sxy) ** 2 / (Sxx * Syy)
        if est == "H1":
            return H1
        if est == "H2":
            return H1 / g2
        return H1 / np.sqrt(g2)


_BASIS = {}


def _basis(ff, fn_grid, z_grid):
    """Cached (len(fn)*len(zeta), len(ff)) matrix of unit-k model responses.

    It does not depend on the DATA, only on the frequency grid, so a 2000-draw episode bootstrap
    builds it once instead of 2000*G times.  This is a pure speed change -- `Zres` is unchanged
    and the returned fit is bit-identical to the loop it replaces.
    """
    key = (ff.tobytes(), fn_grid.tobytes(), z_grid.tobytes())
    U = _BASIS.get(key)
    if U is None:
        U = np.stack([Zres(ff, 1.0, fn, z) for fn in fn_grid for z in z_grid])
        if len(_BASIS) > 8:
            _BASIS.clear()
        _BASIS[key] = U
    return U


def fit_res(f, Sxx, Syy, Sxy, band=(4.0, 45.0), fn_grid=None, z_grid=None, est="geo"):
    """Weighted complex LS of `Zres` to H1 = Sxy/Sxx.  k is closed-form given (fn, zeta), so this
    is an exact 2-D grid search -- no local minima, no optimiser dependency.

    Weight = gamma^2 * Sxx = COHERENT OUTPUT POWER / |Z|^2, so the residual being minimised is in
    counts^2 of bar torque: the fit explains bar variance, which is the quantity the V85 question
    is actually about.
    """
    sel = (f >= band[0]) & (f <= band[1]) & (f > 0)
    ff = f[sel]
    Zm = frf(Sxx, Syy, Sxy, est)[sel]
    w = np.nan_to_num(coh(Sxx, Syy, Sxy)[sel] * Sxx[sel], nan=0.0, posinf=0.0, neginf=0.0)
    if w.sum() <= 0:
        return dict(k=np.nan, fn=np.nan, zeta=np.nan, J=np.nan, b=np.nan, vaf=np.nan)
    fn_grid = np.geomspace(3.0, 45.0, 180) if fn_grid is None else fn_grid
    z_grid = np.geomspace(0.02, 2.0, 120) if z_grid is None else z_grid
    U = _basis(ff, fn_grid, z_grid)           # (G, nbins);  Z = k * U  -- linear in k, cached
    den = (np.abs(U) ** 2) @ w                                     # (G,)
    num = np.real(np.conj(U) @ (w * Zm))                           # (G,)
    with np.errstate(divide="ignore", invalid="ignore"):
        kk = np.where(den > 0, num / np.where(den > 0, den, 1.0), np.nan)
    res = (np.abs(Zm) ** 2) @ w - np.where(np.isfinite(kk), kk, 0.0) * num
    res = np.where(np.isfinite(kk), res, np.inf)
    g = int(np.argmin(res))
    r, k = float(res[g]), float(kk[g])
    fn = float(fn_grid[g // len(z_grid)])
    z = float(z_grid[g % len(z_grid)])
    tot = float(np.sum(w * np.abs(Zm) ** 2))
    wn = 2 * np.pi * fn
    J = k / wn ** 2
    b = 2 * z * k / wn
    return dict(k=k, fn=fn, zeta=z, J=J, b=b, vaf=float(1 - r / tot) if tot > 0 else np.nan,
                n=int(sel.sum()))


def boot_res(recs, band=(4.0, 45.0), nboot=400, seed=8585, coarse=False):
    """Episode bootstrap of `fit_res`.  Returns (point, ci dict)."""
    rng = np.random.default_rng(seed)
    f, Sxx, Syy, Sxy, K = stack(recs)
    pt = fit_res(f, Sxx, Syy, Sxy, band)
    if K < 4:
        return pt, {kk: (np.nan, np.nan) for kk in ("k", "fn", "zeta", "J", "b")}
    fg = np.geomspace(3.0, 45.0, 90) if coarse else None
    zg = np.geomspace(0.02, 2.0, 60) if coarse else None
    keys = ("k", "fn", "zeta", "J", "b")
    smp = {kk: [] for kk in keys}
    n = len(recs)
    for _ in range(nboot):
        j = rng.integers(0, n, n)
        f2, sx, sy, sc, _ = stack([recs[i] for i in j])
        r = fit_res(f2, sx, sy, sc, band, fg, zg)
        for kk in keys:
            smp[kk].append(r[kk])
    ci = {kk: (float(np.nanpercentile(smp[kk], 2.5)), float(np.nanpercentile(smp[kk], 97.5)))
          for kk in keys}
    return pt, ci


# ---------------------------------------------------------------------------- nulls -------------
def mismatch_null(recs, shift=1):
    """Coherence floor: pair each episode's INPUT spectrum with the NEXT episode's OUTPUT.

    Uses the real per-episode cross term  conj(X_i) * Y_{i+1}  reconstructed from magnitudes with
    a random phase, because the stored spectra are already block-averaged and the true per-block
    Fourier coefficients are gone.  ⇒ this is the coherence a set of K episodes with the SAME
    power distribution but NO phase relationship would produce.  Exactly 1/K in expectation.
    """
    K = len(recs)
    if K < 3:
        return None, 0
    rng = np.random.default_rng(4242)
    f = recs[0]["f"]
    Sxx = np.mean([r["Sxx"] for r in recs], axis=0)
    Syy = np.mean([r["Syy"] for r in recs], axis=0)
    acc = np.zeros(len(f), complex)
    for i, r in enumerate(recs):
        o = recs[(i + shift) % K]
        ph = rng.uniform(0, 2 * np.pi, len(f))
        acc += np.sqrt(r["Sxx"] * o["Syy"]) * np.exp(1j * ph)
    Sxy = acc / K
    return coh(Sxx, Syy, Sxy), K


def splithalf(recs, band=(4.0, 32.0)):
    a = fit_ABC(*(lambda s: (s[0], s[1], s[3]))(stack(recs[0::2])), band,
                Syy=stack(recs[0::2])[2])
    b = fit_ABC(*(lambda s: (s[0], s[1], s[3]))(stack(recs[1::2])), band,
                Syy=stack(recs[1::2])[2])
    return a, b


# ---------------------------------------------------------------------------- misc -------------
def band_rms_from_spec(f, S, lo, hi):
    """rms of a signal in [lo,hi] from its Hann periodogram accumulator (arbitrary but CONSISTENT
    normalisation -- only ratios of these are ever used)."""
    sel = (f >= lo) & (f <= hi)
    return float(np.sqrt(S[sel].sum()))


def fmt_ci(pt, ci, sf=3):
    lo, hi = ci
    return f"{pt:.{sf}g} [{lo:.{sf}g}, {hi:.{sf}g}]"
