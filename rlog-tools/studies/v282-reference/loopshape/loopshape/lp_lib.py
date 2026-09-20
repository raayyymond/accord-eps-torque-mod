# -*- coding: utf-8 -*-
"""loopshape: identify the L34 feedback loop (setpoint -> wheel angle) as an OPEN-LOOP transfer.

WHAT THE LOOP IS (EVIDENCE, read from the fork at each flown commit):

    latcontrol_torque.py (every flown commit, Accord branch):
        measured_curvature = -VM.calc_curvature(radians(steeringAngleDeg - angleOffsetDeg), vEgo, roll)
        measurement        = measured_curvature * vEgo**2          # == torqueState.actualLateralAccel
        error              = setpoint - measurement
        error_with_lsf     = error * (1 + low_speed_factor / max(kp, 1e-3))
        [rev 4/5/6.4 only]  error_with_lsf = accord_error_notch.update(error_with_lsf, mode_hz(v), Q=1.0)
        pid_log.error      = error_with_lsf
        p = kp*error ; i += ki*dt*error ; d = k_d*error_rate with k_d == 0
        output_lataccel    = clip(p + i + f, +/-LAF) ; output_torque = output_lataccel / LAF
        pid_log.output     = -output_torque

  => THE FEEDBACK VARIABLE IS THE STEERING ANGLE, mapped by a static (speed, roll) vehicle-model
     gain.  The vehicle's yaw dynamics are NOT inside this loop.  L34 (Z -> M) IS the closed loop.

ESTIMATOR (closed-loop identification, instrumental variable / joint input-output):
    y = P u + d ;  u = u_ff + u_fb ;  u_fb = C_fb (r - y)
    With an instrument w that is exogenous w.r.t. d:
        P_hat    = S_wy / S_wu
        C_fb_hat = S_w,ufb / S_w,e      with e = r - y exactly
        L_hat    = P_hat * C_fb_hat
    Instruments used: w = r (the shaped setpoint Z) and w = u_ff (the plant feedforward, a function
    of r and v alone -- it differentiates r, so it carries more power at 1 Hz than r itself).
    The naive direct estimator P_dir = S_uy/S_uu is biased toward -1/C_fb when d dominates; it is
    reported as the opposite-side bracket.  EVERY number is gated on the instrument coherence.

SIGNALS, all from ONE message (controlsState.lateralControlState.torqueState), so there is no
interpolation phase error between them: r = cs_la_des, y = cs_la_act, p, i, f, out.
    LAF   = -(p + i + f) / out            (exact when unsaturated; measured per route)
    u_fb  = -(p + i) / LAF ;  u_ff = -f / LAF ;  u = out
"""
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402

FS = 100.0
DT = 1.0 / FS
GROUPS = {
    "00000064--ce6b0b0ebb": "V282", "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
    "00000039--f56039af87": "V282old", "0000003a--283a39a1d6": "V282old", "0000003c--927965c2b4": "V282old",
    "0000006c--68c6e94b17": "T64", "0000006d--05e83bb04f": "T64", "0000006e--6ca3e014fd": "T64B",
    "00000076--d0b7ea7e4d": "T5", "00000075--6c8687d5bd": "T4",
    "00000070--717f5a7866": "RF00T", "00000071--f2c9d073a3": "T2",
    "00000072--8001fc3048": "T3", "00000073--79fd149dd8": "T3R",
}
# SteerKP / SteerLatAccel / AccordTorqueKi(+High) exactly as each route's own initData recorded them
# (hsurface/surface/params_all.json).  notch=True means the flown commit CONTAINS HondaAccordErrorNotch
# and AccordErrorNotchQ is unset, so starpilot_variables.get_value returns its default Q = 1.0.
FLOWN = {
    "00000064--ce6b0b0ebb": dict(kp=0.9, laf=6.0, ki=0.3, ki_hi=0.0, notch=False, eps="V282"),
    "00000065--b9f78988bd": dict(kp=0.9, laf=6.0, ki=0.3, ki_hi=0.0, notch=False, eps="V282"),
    "0000006c--2bc842dbac": dict(kp=0.9, laf=6.0, ki=0.3, ki_hi=0.0, notch=False, eps="V282"),
    "00000039--f56039af87": dict(kp=0.8, laf=2.11, ki=0.3, ki_hi=0.0, notch=False, eps="V282"),
    "0000003a--283a39a1d6": dict(kp=0.8, laf=4.0, ki=0.3, ki_hi=0.0, notch=False, eps="V282"),
    "0000003c--927965c2b4": dict(kp=0.8, laf=3.6, ki=0.3, ki_hi=0.0, notch=False, eps="V282"),
    "0000006c--68c6e94b17": dict(kp=1.0, laf=14.0, ki=0.3, ki_hi=0.0, notch=True, eps="V293"),
    "0000006d--05e83bb04f": dict(kp=1.0, laf=14.0, ki=0.3, ki_hi=0.0, notch=True, eps="V293"),
    "0000006e--6ca3e014fd": dict(kp=1.0, laf=14.0, ki=0.3, ki_hi=0.0, notch=True, eps="V293"),
    "00000076--d0b7ea7e4d": dict(kp=1.0, laf=14.0, ki=0.3, ki_hi=0.0, notch=True, eps="V293"),
    "00000075--6c8687d5bd": dict(kp=0.85, laf=14.0, ki=0.6, ki_hi=2.5, notch=True, eps="V293"),
    "00000070--717f5a7866": dict(kp=0.3, laf=6.0, ki=0.15, ki_hi=0.0, notch=False, eps="V293"),
    "00000071--f2c9d073a3": dict(kp=0.85, laf=14.0, ki=0.3, ki_hi=0.0, notch=False, eps="V293"),
    "00000072--8001fc3048": dict(kp=0.85, laf=14.0, ki=0.6, ki_hi=0.0, notch=False, eps="V293"),
    "00000073--79fd149dd8": dict(kp=0.85, laf=14.0, ki=0.6, ki_hi=0.0, notch=False, eps="V293"),
}
LOW_SPEED_X, LOW_SPEED_Y, MIN_SPEED = [0, 10, 20, 30], [12, 10.5, 8, 5], 1.0
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
EPS_INERTIA = 8e-5
KI_SCHED_BP = [8.0, 18.0]
# instrument-coherence gate: set by CONTROL 2 in _self_test (at 0.5 the L error there is <15%,
# at 0.15 it is >100% in the bins the gate would have admitted).
COH_GATE = 0.5
COH_SOFT = 0.2
BINS = [("8-15", 8.0, 15.0), ("15-22", 15.0, 22.0), ("22+", 22.0, 99.0), ("15+", 15.0, 99.0)]


def low_speed_factor(v):
    return (np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / np.maximum(v, MIN_SPEED)) ** 2


def mode_hz(v):
    return np.sqrt(np.interp(v, HOLD_V_BP, HOLD_K_V) / EPS_INERTIA) / (2.0 * np.pi)


def ki_of(v, ki, ki_hi):
    return np.full(np.shape(v), float(ki)) if ki_hi <= 0 else np.interp(v, KI_SCHED_BP, [float(ki), float(ki_hi)])


def notch_response(f, f0, q=1.0, dt=DT):
    """EXACT discrete response of HondaAccordErrorNotch at the coefficients it computes for f0."""
    k = np.tan(np.pi * min(float(f0), 0.45 / dt) * dt)
    norm = 1.0 / (1.0 + k / q + k * k)
    b0 = (1.0 + k * k) * norm
    b1 = 2.0 * (k * k - 1.0) * norm
    a2 = (1.0 - k / q + k * k) * norm
    z = np.exp(-2j * np.pi * np.asarray(f, float) * dt)
    return (b0 + b1 * z + b0 * z ** 2) / (1.0 + b1 * z + a2 * z ** 2)


def pi_response(f, kp, ki, dt=DT):
    """EXACT discrete p + i: i_k = i_{k-1} + ki*dt*e_k, and the control uses p_k + i_k."""
    z = np.exp(-2j * np.pi * np.asarray(f, float) * dt)
    with np.errstate(divide="ignore", invalid="ignore"):
        return kp + ki * dt / (1.0 - z)


def c_fb_analytic(f, kp, ki, laf, lsf, notch_f0=None, q=1.0):
    """The controller's feedback transfer from RAW error (setpoint - measurement) to logged output."""
    C = pi_response(f, kp, ki) * (1.0 + lsf / max(kp, 1e-3)) / laf
    if notch_f0:
        C = C * notch_response(f, notch_f0, q)
    return -C


# ----------------------------------------------------------------------------------------------
def load_loop(route):
    S = V.load(route)
    p, i, f, out = S["p"], S["i"], S["f"], S["out"]
    with np.errstate(divide="ignore", invalid="ignore"):
        laf_frame = np.where(np.abs(out) > 5e-3, -(p + i + f) / out, np.nan)
    act = S["active"]
    laf = float(np.nanmedian(laf_frame[act])) if act.any() else np.nan
    return dict(route=route, t=S["t"], v=S["v"], active=act, pressed=S["pressed"], sat=S["sat"],
                sa=S["sa"], sr=S["sr"], r=S["setpoint"], x=S["model"], y=S["la_act"],
                p=p, i=i, f=f, out=out,
                laf=laf, laf_frame=laf_frame, n=len(S["t"]))


def runs_mask(L):
    return L["active"] & ~L["pressed"] & np.isfinite(L["r"]) & np.isfinite(L["y"]) & np.isfinite(L["out"])


def windows(L, vlo, vhi, nps=1024, hop=512):
    """Contiguous, laterally-engaged, hands-off, unsaturated windows with MEDIAN speed in the bin."""
    m = runs_mask(L)
    out = []
    for a, b in V.runs(m, L["t"], min_s=nps / FS):
        for s in range(a, b - nps + 1, hop):
            e = s + nps
            vv = L["v"][s:e]
            if not np.isfinite(vv).all() or not (vlo <= float(np.median(vv)) < vhi):
                continue
            if float(np.mean(L["sat"][s:e])) > 0.02:
                continue
            out.append((s, e, len(out)))
    return out


_W = {}


def hann(n):
    if n not in _W:
        _W[n] = signal.get_window("hann", n)
    return _W[n]


def win_fft(L, wins, nps=1024):
    w = hann(nps)
    f = np.fft.rfftfreq(nps, DT)
    laf = L["laf"]
    sig = dict(r=np.nan_to_num(L["r"]), y=np.nan_to_num(L["y"]), u=np.nan_to_num(L["out"]),
               ufb=-(np.nan_to_num(L["p"]) + np.nan_to_num(L["i"])) / laf,
               uff=-np.nan_to_num(L["f"]) / laf, x=np.nan_to_num(L["x"]), sa=np.nan_to_num(L["sa"]))
    F = {k: np.empty((len(wins), len(f)), complex) for k in sig}
    vmed = np.empty(len(wins))
    for j, wn in enumerate(wins):
        s, e = wn[0], wn[1]
        for k, a in sig.items():
            F[k][j] = np.fft.rfft(signal.detrend(a[s:e]) * w)
        vmed[j] = float(np.median(L["v"][s:e]))
    return f, F, vmed


def xs(F, a, b, idx=None):
    A = F[a] if idx is None else F[a][idx]
    B = F[b] if idx is None else F[b][idx]
    return np.mean(np.conj(A) * B, axis=0)


def loop_from_F(F, idx=None, instr="r"):
    """L, P, C_fb, S, T from the IV estimator with instrument `instr`, plus brackets/coherences."""
    w = instr
    Sww = xs(F, w, w, idx).real
    Swy = xs(F, w, "y", idx)
    Swu = xs(F, w, "u", idx)
    Swb = xs(F, w, "ufb", idx)
    Swr = xs(F, w, "r", idx)
    Srr = xs(F, "r", "r", idx).real
    Syy = xs(F, "y", "y", idx).real
    Suu = xs(F, "u", "u", idx).real
    Sry = xs(F, "r", "y", idx)
    Swe = Swr - Swy                       # exact: e = r - y
    P = Swy / Swu
    Cfb = Swb / Swe
    L = P * Cfb
    return dict(P=P, Cfb=Cfb, L=L, S=1.0 / (1.0 + L), T=L / (1.0 + L),
                Try=Sry / Srr, P_dir=xs(F, "u", "y", idx) / Suu,
                coh_wu=np.abs(Swu) ** 2 / np.maximum(Sww * Suu, 1e-300),
                coh_wy=np.abs(Swy) ** 2 / np.maximum(Sww * Syy, 1e-300),
                coh_we=np.abs(Swe) ** 2 / np.maximum(Sww * np.maximum(Srr - 2 * Sry.real + Syy, 1e-300), 1e-300),
                Sww=Sww, Srr=Srr, Suu=Suu, Syy=Syy)


def total_loop(F, idx=None):
    """THE TOTAL feedback loop, including every path from the measured state back to the command.

    u_ff is NOT exogenous on the torque builds: it carries the 100 Hz rate loop (a function of the
    measured steering rate) and the disturbance observer (a function of the measured angle, rate and
    past output).  So L = P*C_fb is the PID's loop only.  To get the whole thing, note that the
    CONTROLLER IS NOISE-FREE -- u is an exact deterministic function of the measured signals -- so
    after projecting the exogenous reference out of both u and y at each frequency,
        u_perp = K_y(jw) y_perp    exactly (K_y lumps PID + rate loop + observer),
    and an H1 regression of u_perp on y_perp is unbiased because y_perp carries no independent
    equation noise.  Then  y = P u + d, u = K_r r + K_y y  =>  L_total = -P * K_y.
    POSITIVE CONTROL ON REAL DATA: on the V282 routes the PID is the only feedback path, so K_y
    must come back equal to -C_fb.  That check is printed by L2.
    """
    R = F if idx is None else {k: v[idx] for k, v in F.items()}
    Srr = np.mean(np.abs(R["r"]) ** 2, axis=0)
    bu = np.mean(np.conj(R["r"]) * R["u"], axis=0) / np.maximum(Srr, 1e-300)
    by = np.mean(np.conj(R["r"]) * R["y"], axis=0) / np.maximum(Srr, 1e-300)
    Up = R["u"] - bu * R["r"]
    Yp = R["y"] - by * R["r"]
    Syy = np.mean(np.abs(Yp) ** 2, axis=0)
    Suu = np.mean(np.abs(Up) ** 2, axis=0)
    Syu = np.mean(np.conj(Yp) * Up, axis=0)
    Ky = Syu / np.maximum(Syy, 1e-300)
    return dict(Ky=Ky, coh_yu=np.abs(Syu) ** 2 / np.maximum(Syy * Suu, 1e-300),
                Sypyp=Syy, Supup=Suu)


def margins(f, L, fmin=0.10, fmax=4.0):
    """Crossover (|L|=1), phase margin, gain margin, Ms = max|S| and the f where |S| first > 1."""
    s = (f >= fmin) & (f <= fmax)
    ff, LL = f[s], np.asarray(L)[s]
    mag = np.abs(LL)
    ph = np.unwrap(np.angle(LL))
    out = dict(wc=np.nan, pm=np.nan, gm=np.nan, gm_f=np.nan, Ms=np.nan, f_Ms=np.nan, f_S1=np.nan,
               magmax=float(mag.max()), f_magmax=float(ff[int(np.argmax(mag))]))
    k = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
    if len(k):
        k = k[-1]
        w = np.log(mag[k]) / (np.log(mag[k]) - np.log(mag[k + 1]))
        out["wc"] = float(ff[k] + w * (ff[k + 1] - ff[k]))
        pc = ph[k] + w * (ph[k + 1] - ph[k])
        out["pm"] = float(180.0 + np.degrees(np.angle(np.exp(1j * pc))))
    phw = np.degrees(np.angle(LL))
    for k in range(len(ff) - 1):
        a, b = phw[k], phw[k + 1]
        if a < -80 and b < -80 and a > -180 >= b:
            w = (a + 180.0) / (a - b)
            out["gm_f"] = float(ff[k] + w * (ff[k + 1] - ff[k]))
            out["gm"] = float(1.0 / np.exp(np.log(mag[k]) + w * (np.log(mag[k + 1]) - np.log(mag[k]))))
            break
    Sm = np.abs(1.0 / (1.0 + LL))
    k = int(np.argmax(Sm))
    out["Ms"], out["f_Ms"] = float(Sm[k]), float(ff[k])
    up = np.where(Sm > 1.0)[0]
    if len(up):
        out["f_S1"] = float(ff[up[0]])
    return out


# ----------------------------------------------------------------------------------------------
def _sim(n, rlp, dlp, g, fp, nd, kp, ki, laf, ffgain, ffrate, seed):
    """Closed loop with KNOWN P (gain g, pole fp, delay nd frames) and a KNOWN PI controller,
    an exogenous reference and an INDEPENDENT disturbance. The feedforward has a rate term, like
    the fork's plant FF, so the instrument carries power where the reference itself does not."""
    rng = np.random.default_rng(seed)
    a = DT / (1.0 / (2 * np.pi * fp) + DT)
    r = signal.sosfiltfilt(signal.butter(2, rlp, fs=FS, output="sos"), rng.standard_normal(n)) * 40
    d = signal.sosfiltfilt(signal.butter(2, dlp, fs=FS, output="sos"), rng.standard_normal(n)) * 20
    y = np.zeros(n); u = np.zeros(n); ufb = np.zeros(n); uff = np.zeros(n)
    ii = 0.0; st = 0.0; hist = [0.0] * (nd + 1); prev_r = r[0]
    for k in range(n):
        e = r[k] - y[k]
        ii += ki * DT * e
        ufb[k] = -(kp * e + ii) / laf
        uff[k] = -(ffgain * r[k] + ffrate * (r[k] - prev_r) / DT) / laf
        prev_r = r[k]
        u[k] = ufb[k] + uff[k]
        hist.append(u[k]); hist.pop(0)
        st += a * (g * hist[0] - st)
        if k + 1 < n:
            y[k + 1] = st + d[k + 1]
    z = np.exp(-2j * np.pi * np.fft.rfftfreq(1024, DT) * DT)
    Pt = g * (a / (1 - (1 - a) * z)) * z ** (nd + 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        Ct = -(kp + ki * DT / (1 - z)) / laf
    return r, y, u, ufb, uff, Pt, Ct


def _F_of(arrs, nps=1024, hop=512):
    n = len(arrs["r"])
    w = hann(nps)
    wins = [(s, s + nps) for s in range(0, n - nps + 1, hop)]
    F = {k: np.empty((len(wins), nps // 2 + 1), complex) for k in arrs}
    for j, (s, e) in enumerate(wins):
        for k, a in arrs.items():
            F[k][j] = np.fft.rfft(signal.detrend(a[s:e]) * w)
    return F, len(wins)


def _self_test():
    lines = []
    f = np.fft.rfftfreq(1024, DT)

    # ---- CONTROL 1: broadband reference. The estimator must recover P, C, L, wc, PM and Ms.
    r, y, u, ufb, uff, Pt, Ct = _sim(400 * 100, 5.0, 3.0, -9.0, 1.6, 6, 1.0, 0.3, 6.0, 0.4, 0.05, 7)
    F, nw = _F_of(dict(r=r, y=y, u=u, ufb=ufb, uff=uff, x=r, sa=y))
    R = loop_from_F(F, instr="r")
    Lt = Pt * Ct
    s = (f >= 0.2) & (f <= 3.0)
    eP = np.median(np.abs(R["P"][s] - Pt[s]) / np.abs(Pt[s]))
    eL = np.median(np.abs(R["L"][s] - Lt[s]) / np.abs(Lt[s]))
    eC = np.median(np.abs(R["Cfb"][s] - Ct[s]) / np.abs(Ct[s]))
    mt, mh = margins(f, Lt), margins(f, R["L"])
    eD = np.median(np.abs(R["P_dir"][s] - Pt[s]) / np.abs(Pt[s]))
    lines.append(f"  C1 broadband r, {nw} win: P err {eP*100:.2f}%  C err {eC*100:.3f}%  L err {eL*100:.2f}%"
                 f"  | direct-P err {eD*100:.1f}% (must be worse)")
    lines.append(f"     truth wc {mt['wc']:.3f} PM {mt['pm']:.1f} GM {mt['gm']:.2f} Ms {mt['Ms']:.3f}@{mt['f_Ms']:.2f}"
                 f"  |  est wc {mh['wc']:.3f} PM {mh['pm']:.1f} GM {mh['gm']:.2f} Ms {mh['Ms']:.3f}@{mh['f_Ms']:.2f}")
    assert eP < 0.05 and eL < 0.05 and eC < 0.01, lines[-2]
    # tolerances are ONE frequency bin (df = 0.0977 Hz) and the phase slope across it
    assert abs(mh["wc"] - mt["wc"]) < 0.10 and abs(mh["pm"] - mt["pm"]) < 6 and abs(mh["Ms"] - mt["Ms"]) < 0.08, lines[-1]
    assert eD > 1.8 * eP, lines[-2]

    # ---- CONTROL 2: narrow reference (0.45 Hz), heavy 3 Hz disturbance, FF with a rate term.
    #      The u_ff instrument must still work where the r instrument's coherence has collapsed,
    #      and the coherence gate must MARK the band where neither does.
    r, y, u, ufb, uff, Pt, Ct = _sim(400 * 100, 0.45, 3.0, -9.0, 1.6, 6, 1.0, 0.3, 6.0, 0.4, 0.05, 11)
    F, nw = _F_of(dict(r=r, y=y, u=u, ufb=ufb, uff=uff, x=r, sa=y))
    Rr, Rf = loop_from_F(F, instr="r"), loop_from_F(F, instr="uff")
    Lt = Pt * Ct
    for nm, RR in (("r", Rr), ("uff", Rf)):
        ok = RR["coh_wu"] > COH_GATE
        b = s & ok
        e1 = np.median(np.abs(RR["L"][b] - Lt[b]) / np.abs(Lt[b])) if b.sum() else np.nan
        bad = s & ~ok
        e2 = np.median(np.abs(RR["L"][bad] - Lt[bad]) / np.abs(Lt[bad])) if bad.sum() else np.nan
        lines.append(f"  C2 instrument {nm:3s}: coh>{COH_GATE} on {b.sum():3d}/{s.sum()} bins, L err there "
                     f"{e1*100:6.2f}%  | below the gate {bad.sum():3d} bins, L err {e2*100:8.1f}%")
        if b.sum() >= 5:
            assert e1 < 0.15, lines[-1]
    # the gate has to do real work: ungated, the narrow-r estimate must be visibly bad somewhere
    assert np.median(np.abs(Rr["L"][s] - Lt[s]) / np.abs(Lt[s])) > 0.15, "gate does nothing"
    # and with a narrow reference under a heavy disturbance the DIRECT estimator must blow up
    eD2 = np.median(np.abs(Rr["P_dir"][s] - Pt[s]) / np.abs(Pt[s]))
    lines.append(f"  C2 direct-P err (narrow r, heavy d) {eD2*100:.0f}% -- the bias this estimator is built to avoid")
    assert eD2 > 0.5, lines[-1]

    # ---- CONTROL 3: the notch and PI responses against a brute-force time-domain run.
    rng = np.random.default_rng(3)
    x = rng.standard_normal(60000)
    yn = np.empty_like(x)
    x1 = x2 = y1 = y2 = 0.0
    k = np.tan(np.pi * 1.9 * DT); q = 1.0
    nrm = 1.0 / (1.0 + k / q + k * k); b0 = (1 + k * k) * nrm; b1 = 2 * (k * k - 1) * nrm; a2 = (1 - k / q + k * k) * nrm
    for j, xv in enumerate(x):
        yv = b0 * xv + b1 * x1 + b0 * x2 - b1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, xv, y1, yv
        yn[j] = yv
    fw, pxx = signal.welch(x, FS, nperseg=4096)
    _, pxy = signal.csd(x, yn, FS, nperseg=4096)
    He = pxy / pxx
    Ha = notch_response(fw, 1.9, 1.0)
    m = (fw > 0.2) & (fw < 10)
    en = np.max(np.abs(He[m] - Ha[m]))
    lines.append(f"  C3 notch: max |empirical - analytic| over 0.2-10 Hz = {en:.2e}  "
                 f"(|N| at 1.9 Hz = {abs(notch_response(1.9,1.9,1.0)):.4f}, at 1.0 Hz = "
                 f"{abs(notch_response(1.0,1.9,1.0)):.3f} @ {np.degrees(np.angle(notch_response(1.0,1.9,1.0))):.1f} deg)")
    assert en < 2e-2, lines[-1]

    # ---- CONTROL 4: total_loop with a SECOND feedback path (a rate term inside u_ff), which is
    #      exactly the structure the torque builds have.  K_y must recover PID + rate, not PID alone.
    rng = np.random.default_rng(23)
    n = 400 * 100
    g, fp, nd, kp, ki, laf = -9.0, 1.6, 6, 1.0, 0.3, 6.0
    a = DT / (1.0 / (2 * np.pi * fp) + DT)
    krate = 0.004                      # command per (unit y)/s -- the inner rate feedback
    r = signal.sosfiltfilt(signal.butter(2, 2.0, fs=FS, output="sos"), rng.standard_normal(n)) * 40
    d = signal.sosfiltfilt(signal.butter(2, 3.0, fs=FS, output="sos"), rng.standard_normal(n)) * 20
    y = np.zeros(n); u = np.zeros(n); ufb = np.zeros(n); uff = np.zeros(n)
    ii = 0.0; st = 0.0; hist = [0.0] * (nd + 1); prev_r = r[0]; prev_y = 0.0
    for k in range(n):
        e = r[k] - y[k]
        ii += ki * DT * e
        ufb[k] = -(kp * e + ii) / laf
        uff[k] = -(0.4 * r[k] + 0.05 * (r[k] - prev_r) / DT) / laf + krate * (y[k] - prev_y) / DT
        prev_r = r[k]; prev_y = y[k]
        u[k] = ufb[k] + uff[k]
        hist.append(u[k]); hist.pop(0)
        st += a * (g * hist[0] - st)
        if k + 1 < n:
            y[k + 1] = st + d[k + 1]
    F, nw = _F_of(dict(r=r, y=y, u=u, ufb=ufb, uff=uff, x=r, sa=y))
    R = loop_from_F(F, instr="r")
    TT = total_loop(F)
    z = np.exp(-2j * np.pi * f * DT)
    with np.errstate(divide="ignore", invalid="ignore"):
        Ct = -(kp + ki * DT / (1 - z)) / laf
    Kyt = -Ct + krate * (1 - z) / DT               # PID + the discrete backward-difference rate term
    Pt = g * (a / (1 - (1 - a) * z)) * z ** (nd + 1)
    s2 = (f >= 0.2) & (f <= 4.0)
    eK = np.median(np.abs(TT["Ky"][s2] - Kyt[s2]) / np.abs(Kyt[s2]))
    ePID = np.median(np.abs(-R["Cfb"][s2] - Kyt[s2]) / np.abs(Kyt[s2]))
    mt = margins(f, -Pt * Kyt)
    mh = margins(f, -Pt * TT["Ky"])
    lines.append(f"  C4 total loop: K_y err {eK*100:.2f}% (the PID-only reading would be {ePID*100:.0f}% wrong), "
                 f"median coh(y_perp,u_perp) {np.median(TT['coh_yu'][s2]):.4f}")
    lines.append(f"     truth wc {mt['wc']:.3f} PM {mt['pm']:.1f} Ms {mt['Ms']:.3f}  |  est wc {mh['wc']:.3f} "
                 f"PM {mh['pm']:.1f} Ms {mh['Ms']:.3f}")
    assert eK < 0.03, lines[-2]
    assert ePID > 0.25, lines[-2]
    assert abs(mh["wc"] - mt["wc"]) < 0.10 and abs(mh["pm"] - mt["pm"]) < 6, lines[-1]
    return "SELF-TEST OK\n" + "\n".join(lines)


if __name__ == "__main__":
    print(_self_test())
