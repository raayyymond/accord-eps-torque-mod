# -*- coding: utf-8 -*-
"""c2: is the delay canceller actually cancelling?  MEASUREMENT of the setpoint stage on both builds.

The stage, verbatim from latcontrol_torque.py (identical structure at every flown commit):

    n        = int(clip(lat_delay/dt, 1, 100))                       # delay_frames, TRUNCATED to a frame
    expected = curvature_request_buffer[-n] * v(t)^2                 # u(t - n*dt), current v^2
    raw      = clip((u(t) - expected) / max(lat_delay, dt), +-2.5)   # MAX_LAT_JERK_UP
    jerk     = clip(F_j(raw), +-2.5)                                 # one-pole, rc = 1/(2 pi fc)
    sp_pre   = expected + jerk * lat_delay
    setpoint = RF(RF(sp_pre))                                        # AccordRefFilter, two one-poles, rev 4+ only

  => with F_j == 1 and no clip, sp_pre == u(t) EXACTLY (the lat_delay divide/multiply cancel), for ANY n.
     So the canceller's whole deviation from unity comes from F_j and from the two clips, and D enters
     only as the LEVER ARM on that deviation -- it is NOT a compensator that can be "over-large".

Stage 1 (VALIDATION): reconstruct `setpoint` from the logged u, lat_delay and jerk and compare to the logged
setpoint frame by frame.  Nothing downstream is trusted until this closes.
Stage 2 (MEASUREMENT): realised |H| and phase of u -> setpoint, u -> sp_pre (the canceller alone) and
raw -> jerk (F_j alone), against the closed-form DISCRETE algebra at each route's own n and fc.

ANALYSIS ONLY.  usage: python c2_stage.py [route ...]
"""
import json, os, sys
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "v282-reference"))
import v282cmp as V  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DT = 0.01
LAT_SMOOTH = 0.1   # controlsd.py: lat_delay = liveDelay.lateralDelay + get_control_lateral_smooth_seconds(...)
                   # which for brand "honda" is LAT_SMOOTH_SECONDS = 0.1 at EVERY flown commit (git-confirmed).
                   # The cached `lat_delay` channel is liveDelay ONLY, so D = cached + 0.1.
MAX_LAT_JERK_UP = 2.5
BUF = 100                       # LAT_ACCEL_REQUEST_BUFFER_SECONDS / dt
BANDS = [(0.06, 0.15), (0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)]

# flown configuration per route, EVIDENCE: git (JERK_LP_HZ / accord_ref_filter present-or-absent at the
# flown GitCommit from each route's own initData) x initData AccordRefFilter.  c1_delayparams.json.
CFG = {
    "00000039--f56039af87": dict(g="V282old", fc=1.2, rf=0.0),
    "0000003a--283a39a1d6": dict(g="V282old", fc=1.2, rf=0.0),
    "0000003c--927965c2b4": dict(g="V282old", fc=1.2, rf=0.0),
    "00000064--ce6b0b0ebb": dict(g="V282", fc=1.2, rf=0.0),
    "00000065--b9f78988bd": dict(g="V282", fc=1.2, rf=0.0),
    "0000006c--2bc842dbac": dict(g="V282", fc=1.2, rf=0.0),
    "0000006c--68c6e94b17": dict(g="T64", fc=4.0, rf=0.06),
    "0000006d--05e83bb04f": dict(g="T64", fc=4.0, rf=0.06),
    "0000006e--6ca3e014fd": dict(g="T64B", fc=4.0, rf=0.06),
    "00000075--6c8687d5bd": dict(g="T4", fc=1.2, rf=0.12),
    "00000076--d0b7ea7e4d": dict(g="T5", fc=1.2, rf=0.12),
    "00000072--8001fc3048": dict(g="T6?", fc=1.2, rf=0.12),
    "00000073--79fd149dd8": dict(g="T6?", fc=1.2, rf=0.12),
    "00000070--717f5a7866": dict(g="V293a", fc=1.2, rf=0.0),
    "00000071--f2c9d073a3": dict(g="V293a", fc=1.2, rf=0.0),
}


def onepole(x, rc, reset_mask=None, x0=0.0):
    """FirstOrderFilter: alpha = dt/(rc+dt); x = (1-a)x + a*u.  reset_mask True -> state forced to x0."""
    a = DT / (rc + DT)
    y = np.empty_like(x)
    s = x0
    if reset_mask is None:
        for k in range(len(x)):
            s = (1.0 - a) * s + a * x[k]
            y[k] = s
    else:
        for k in range(len(x)):
            if reset_mask[k]:
                s = x0
            else:
                s = (1.0 - a) * s + a * x[k]
            y[k] = s
    return y


def onepole_track(x, rc, reset_mask):
    """As onepole but on reset the state is PRIMED with the current input (accord_ref_filter_{1,2}.x = u)."""
    a = DT / (rc + DT)
    y = np.empty_like(x)
    s = x[0]
    for k in range(len(x)):
        if reset_mask[k]:
            s = x[k]
        else:
            s = (1.0 - a) * s + a * x[k]
        y[k] = s
    return y


def Hz_onepole(f, rc):
    a = DT / (rc + DT)
    z = np.exp(-2j * np.pi * f * DT)
    return a / (1.0 - (1.0 - a) * z)


def H_stage(f, n, fc, rf):
    """Closed-form DISCRETE transfer of the whole stage: canceller x ref filter."""
    Dz = np.exp(-2j * np.pi * f * n * DT)
    Fj = Hz_onepole(f, 1.0 / (2.0 * np.pi * fc))
    Hc = Dz + Fj * (1.0 - Dz)
    if rf > 0:
        Hc = Hc * Hz_onepole(f, rf) ** 2
    return Hc


def H_canc(f, n, fc):
    Dz = np.exp(-2j * np.pi * f * n * DT)
    Fj = Hz_onepole(f, 1.0 / (2.0 * np.pi * fc))
    return Dz + Fj * (1.0 - Dz)


def reconstruct(S, cfg):
    """Rebuild the stage from logged signals.  Returns dict of channels + the validation residuals."""
    t, v = S["t"], np.nan_to_num(S["v"])
    curv = np.nan_to_num(S["model"]) / np.maximum(v * v, 1e-9)     # back out desiredCurvature
    ld = np.nan_to_num(S["lat_delay"], nan=0.2) + LAT_SMOOTH
    N = len(t)
    n = np.clip((ld / DT).astype(np.int64), 1, BUF)                 # int() truncates
    u = np.nan_to_num(S["model"])
    idx = np.maximum(np.arange(N) - n, 0)
    expected = curv[idx] * v * v
    raw = np.clip((u - expected) / np.maximum(ld, DT), -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP)
    inact = ~S["active"]
    jerk_rec = np.clip(onepole(raw, 1.0 / (2.0 * np.pi * cfg["fc"]), reset_mask=inact, x0=0.0),
                       -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP)
    jerk_log = np.nan_to_num(S["jerk_des"])
    sp_pre_log = expected + jerk_log * ld          # uses the LOGGED jerk: isolates the ref-filter leg
    sp_pre_rec = expected + jerk_rec * ld          # fully independent
    if cfg["rf"] > 0:
        sp_rec = onepole_track(onepole_track(sp_pre_log, cfg["rf"], inact), cfg["rf"], inact)
    else:
        sp_rec = sp_pre_log
    return dict(u=u, expected=expected, raw=raw, jerk_rec=jerk_rec, jerk_log=jerk_log,
                sp_pre_log=sp_pre_log, sp_pre_rec=sp_pre_rec, sp_rec=sp_rec,
                sp_log=np.nan_to_num(S["setpoint"]), n=n, ld=ld)


def segs_for(S, R, xk, yk, vmin=0.0, vmax=99.0, min_s=40.0, trim=2.0):
    m = V.usable(S, vmin, vmax) & np.isfinite(R[xk]) & np.isfinite(R[yk])
    out = []
    for a, b in V.runs(m, S["t"], min_s=min_s + trim):
        a2 = a + int(trim * V.FS)
        if (S["t"][b - 1] - S["t"][a2]) >= min_s:
            out.append((R[xk][a2:b], R[yk][a2:b]))
    return out


def band_stats(segs, f1, f2, nps):
    segs = [s for s in segs if len(s[0]) >= nps]
    if not segs:
        return None
    Pxx = Pyy = Pxy = None
    fr = None
    sec = 0.0
    for x, y in segs:
        xs, ys = x - x.mean(), y - y.mean()
        f, pxx = signal.welch(xs, V.FS, nperseg=nps, noverlap=nps // 2)
        _, pyy = signal.welch(ys, V.FS, nperseg=nps, noverlap=nps // 2)
        _, pxy = signal.csd(xs, ys, V.FS, nperseg=nps, noverlap=nps // 2)
        w = len(xs)
        Pxx = pxx * w if Pxx is None else Pxx + pxx * w
        Pyy = pyy * w if Pyy is None else Pyy + pyy * w
        Pxy = pxy * w if Pxy is None else Pxy + pxy * w
        fr = f
        sec += w / V.FS
    s = (fr >= f1) & (fr < f2) & (fr > 0)
    if s.sum() < 1:
        return None
    w = Pxx[s]
    H = np.abs(Pxy[s]) / np.maximum(Pxx[s], 1e-30)
    coh = np.abs(Pxy[s]) ** 2 / np.maximum(Pxx[s] * Pyy[s], 1e-30)
    ph = np.angle(Pxy[s])
    lag = -ph / (2 * np.pi * fr[s])
    return dict(H=float(np.average(H, weights=w)), coh=float(np.average(coh, weights=w)),
                lag_ms=float(np.average(lag, weights=w) * 1e3), sec=sec, n=len(segs),
                fbins=fr[s], w=w)


def pred_band(bs, n, fc, rf, canc_only=False):
    f = bs["fbins"]
    H = H_canc(f, n, fc) if canc_only else H_stage(f, n, fc, rf)
    lag = -np.angle(H) / (2 * np.pi * f)
    return (float(np.average(np.abs(H), weights=bs["w"])), float(np.average(lag, weights=bs["w"]) * 1e3))


def main():
    routes = sys.argv[1:] or list(CFG)
    res = {}
    print("=" * 136)
    print("A. STAGE-1 VALIDATION -- reconstruct the logged setpoint from the logged plan, lat_delay and jerk.")
    print("   `sp_rec` uses the LOGGED desiredLateralJerk (isolates the ref filter); `sp_pre_rec` re-runs F_j too.")
    print("   RMS residual is normalised by the RMS of the logged setpoint, on laterally-engaged frames only.")
    print("=" * 136)
    print("%-22s %-7s n_med fc   RF    | setpoint recon: rel_rms   max_abs  corr | jerk recon: rel_rms  corr | "
          "raw clip%%  jerk clip%%" % ("route", "group"))
    for r in routes:
        cfg = CFG[r]
        S = V.load(r)
        R = reconstruct(S, cfg)
        m = V.usable(S) & np.isfinite(R["sp_log"]) & np.isfinite(R["sp_rec"])
        # drop the first 1.5 s of every engaged run: the buffer/filters are priming
        keep = np.zeros(len(m), bool)
        for a, b in V.runs(m, S["t"], min_s=3.0):
            keep[a + 150:b] = True
        m = m & keep
        sl = m
        den = np.sqrt(np.mean(R["sp_log"][sl] ** 2)) + 1e-12
        e = R["sp_rec"][sl] - R["sp_log"][sl]
        ej = R["jerk_rec"][sl] - R["jerk_log"][sl]
        cj = float(np.corrcoef(R["jerk_rec"][sl], R["jerk_log"][sl])[0, 1])
        cs = float(np.corrcoef(R["sp_rec"][sl], R["sp_log"][sl])[0, 1])
        rawclip = float(np.mean(np.abs(R["raw"][sl]) >= MAX_LAT_JERK_UP - 1e-9) * 100)
        jclip = float(np.mean(np.abs(R["jerk_log"][sl]) >= MAX_LAT_JERK_UP - 1e-9) * 100)
        print("%-22s %-7s %5d %4.1f %5.2f | %20.5f %8.4f %6.4f | %18.4f %6.4f | %8.3f %10.3f" % (
            r, cfg["g"], int(np.median(R["n"][sl])), cfg["fc"], cfg["rf"],
            np.sqrt(np.mean(e ** 2)) / den, np.max(np.abs(e)), cs,
            np.sqrt(np.mean(ej ** 2)) / (np.sqrt(np.mean(R["jerk_log"][sl] ** 2)) + 1e-12), cj,
            rawclip, jclip))
        res[r] = dict(cfg=cfg, n_med=int(np.median(R["n"][sl])), sp_rel_rms=float(np.sqrt(np.mean(e ** 2)) / den),
                      sp_max_abs=float(np.max(np.abs(e))), sp_corr=cs, jerk_corr=cj,
                      raw_clip_pct=rawclip, jerk_clip_pct=jclip, bands={})
        del R, S, m
    print()
    print("=" * 136)
    print("B. REALISED vs ALGEBRA.  MEASURED = Welch |Pxy|/Pxx, magnitudes averaged per bin weighted by input")
    print("   power; lag = -phase/(2 pi f) per bin, same weights.  PRED = the closed-form discrete algebra at")
    print("   that route's own n and fc, band-averaged with the SAME weights.  Ideal canceller: |H| 1, lag 0.")
    print("=" * 136)
    for r in routes:
        cfg = CFG[r]
        S = V.load(r)
        R = reconstruct(S, cfg)
        print("-- %s  %s  n=%d (D=%.4f s)  fc=%.1f Hz  AccordRefFilter=%.2f" % (
            r, cfg["g"], res[r]["n_med"], res[r]["n_med"] * DT, cfg["fc"], cfg["rf"]))
        print("   band Hz    |   STAGE u->setpoint(log)        |   CANCELLER u->sp_pre(rec)      |   F_j raw->jerk(log)")
        print("              |  |H|meas |H|pred lag_ms  pred   coh |  |H|meas |H|pred lag_ms  pred   coh |  |H|meas |H|pred ph_ms  pred   coh")
        for (f1, f2) in BANDS:
            nps = 4096 if f2 <= 0.30 else (2048 if f2 <= 0.60 else 1024)
            row = ["%5.2f-%4.2f  |" % (f1, f2)]
            bres = {}
            for tag, xk, yk, conly in (("stage", "u", "sp_log", False),
                                       ("canc", "u", "sp_pre_rec", True),
                                       ("fj", "raw", "jerk_log", None)):
                sg = segs_for(S, R, xk, yk)
                bs = band_stats(sg, f1, f2, nps)
                if bs is None:
                    row.append("   --      --      --     --     -- |")
                    continue
                if conly is None:
                    f = bs["fbins"]
                    Hp = Hz_onepole(f, 1.0 / (2.0 * np.pi * cfg["fc"]))
                    hp = float(np.average(np.abs(Hp), weights=bs["w"]))
                    lp = float(np.average(-np.angle(Hp) / (2 * np.pi * f), weights=bs["w"]) * 1e3)
                else:
                    hp, lp = pred_band(bs, res[r]["n_med"], cfg["fc"], cfg["rf"], canc_only=conly)
                row.append(" %7.4f %7.4f %6.1f %6.1f %5.2f |" % (bs["H"], hp, bs["lag_ms"], lp, bs["coh"]))
                bres[tag] = dict(H=bs["H"], H_pred=hp, lag_ms=bs["lag_ms"], lag_pred_ms=lp,
                                 coh=bs["coh"], sec=bs["sec"], nseg=bs["n"])
            print("   " + "".join(row))
            res[r]["bands"]["%.2f-%.2f" % (f1, f2)] = bres
        print()
        del R, S
    with open(os.path.join(HERE, "c2_stage.json"), "w") as fh:
        json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()
