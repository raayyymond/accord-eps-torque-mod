# -*- coding: utf-8 -*-
r"""high_angle_hunt.py -- WHO MOVES FIRST at high steering angle: the fork's setpoint or the firmware's wheel?

    python rlog-tools/studies/angle_loop/high_angle_hunt.py <route prefix> [<route prefix> ...] [--min-deg 60]
            [--plot DIR] [--json PATH]

ANALYSIS ONLY (2026-10-15, subagent routes-review).  Reads the kit's wire cache (angle_loop_drive_read.load_route) and
the fork-side cache (drive_read_v299.fork_cache: extracted once per route, ~10 s, then cached); sends nothing.

The operator's complaint (2026-10-15): "at very high steering angles (sharp turns), the wheel jumps back and forth a
bit rather than landing at a single hard turn angle."

RELEASE FIRMWARE (2026-10-15): no lane tap.  On an A16C route the tap columns (T, Trms, Tpk, Tflip, HOLD T flips) are NaN and
printed as "-" with a NOT AVAILABLE line; every stock-signal column (angle, 0xE4 setpoint, fork desired, bar, rate / clip
duty) is unchanged.  The rate cap and the error clip are the ones the fork ran (drive_read_v299.rate_cap / fork_constants),
not literals.  HANDS-OFF has two labels, both printed: |bar| < 300 (spec rev 3 §7.1) and the REACTION TEST
(drive_read_v299.reaction_label: the bar is the wheel's own inertial reaction, R2 >= 0.5 of bar vs angular acceleration).

EPISODE  latActive (the wire's req & SCA), >= 1.0 s after engage, |theta| >= MIN_DEG, runs >= 1.0 s.
HANDS-OFF frame  |bar| < 300 for this and the preceding 0.5 s, not steeringPressed (spec rev 3 §7.1).
SIGNALS (all on the 100 Hz wire grid):
  theta      0x14A angle (deg, +left)                    -- the WHEEL (what the operator feels)
  sp         0xE4 setpoint = -raw/10 (== carOutput angle) -- what the firmware is asked for (post fork limiter)
  cc         carControl.actuators.steeringAngleDeg        -- the fork's desired angle BEFORE its car-side limiter
  T          0x1AB tap, LSB (rail 2461/8 = 307 LSB)       -- the angle lane's torque
  bar        0x18F torque word x 1.024                    -- the hand / reaction twist
BAND  the 0.4-4 Hz band-pass (zero-phase) of each angle = the "back and forth".  Per episode:
  rms_th / rms_sp / rms_cc   band rms of wheel, setpoint, pre-limiter desire
  k_sp   = regression of band(theta) on band(sp) at the best lag 0..40 frames, and R2 -- share of wheel motion that is
           the setpoint's motion followed;   resid = rms of band(theta) - k band(sp_lagged)  (the firmware's own motion)
  f_th   dominant frequency of band(theta) (FFT peak over the episode)
  rev    wheel direction reversals per second with >= 0.5 deg swing between them; rev_sp likewise for the setpoint
  rate-cap duty  |d sp/dt| >= 115 deg/s (the fork's 120 deg/s cap)
  freeze duty / toggles   |bar| > 1229 (V299's hard freeze), > 512, > 300 (V298's levels)
  T: rms, peak, sign changes per second;  |sp - theta| p50 / p95
DECISION (pre-written before any new route was read):  FORK-SOURCED when R2 >= 0.5 and rms_sp >= 0.7 rms_th (the
wheel follows a moving setpoint); FIRMWARE-SOURCED when rms_sp < 0.4 rms_th (setpoint steady, wheel hunts); else MIXED.
Then: if fork-sourced, cc vs sp separates the planner (cc moves too) from the limiter (only sp moves).
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import signal

# ---- PATH BOOTSTRAP -- walk up to .pkgroot, then put the kit root and every code subfolder on the path
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
SOS = signal.butter(2, [0.4, 4.0], btype="band", fs=FS, output="sos")


def runs(mask, minlen=1):
    d = np.diff(np.r_[0, np.asarray(mask, np.int8), 0])
    a, b = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    k = (b - a) >= minlen
    return np.c_[a[k], b[k]]


def reversals(x, thr=0.5):
    """direction reversals with >= thr deg between successive extrema (hysteresis turning-point count)."""
    n, dirn = 0, 0
    hi = lo = float(x[0])
    for v in x[1:]:
        if dirn == 0:
            hi, lo = max(hi, v), min(lo, v)
            if hi - v >= thr:
                dirn, lo = -1, v
            elif v - lo >= thr:
                dirn, hi = 1, v
        elif dirn == 1:
            if v > hi:
                hi = v
            elif hi - v >= thr:
                n, dirn, lo = n + 1, -1, v
        else:
            if v < lo:
                lo = v
            elif v - lo >= thr:
                n, dirn, hi = n + 1, 1, v
    return n


def domfreq(x):
    if len(x) < 64:
        return np.nan
    f, p = signal.periodogram(x * np.hanning(len(x)), fs=FS, nfft=max(1024, len(x)))
    k = (f >= 0.4) & (f <= 4.0)
    return float(f[k][np.argmax(p[k])])


def best_lag_fit(y, x, maxlag=40):
    best = (-np.inf, 0, 0.0)
    for L in range(0, maxlag + 1):
        xs = x[:len(x) - L] if L else x
        ys = y[L:]
        den = float(np.dot(xs, xs))
        if den <= 0:
            continue
        k = float(np.dot(xs, ys)) / den
        r = ys - k * xs
        r2 = 1 - float(np.dot(r, r)) / max(float(np.dot(ys, ys)), 1e-12)
        if r2 > best[0]:
            best = (r2, L, k)
    return best


def load(route, synthetic=False):
    import angle_loop_drive_read as D
    import drive_read_v299 as V
    with contextlib.redirect_stdout(io.StringIO()):
        W = D.load_route(route)
    if synthetic:                                  # SELF-CHECK: the release path on a stripped V299 route
        D.strip_tap(W)
    FK, fm, _ = V.fork_cache(W, D._fr())
    t = W["t"]
    out = dict(W=W, fm=fm if isinstance(fm, dict) else {}, fork_err=None if FK is not None else fm,
               tap=D.tap_ok(W))
    if FK is not None:
        out["cc"] = np.interp(t, FK["t_cc"], FK["cc_ang"])
        out["co"] = np.interp(t, FK["t_co"], FK["co_ang"])
        out["press"] = np.interp(t, FK["t_cs"], FK["cs_press"]) > 0.5
        try:
            out["params"] = json.loads(str(FK["initdata_params_json"]))["params"]
        except Exception:
            out["params"] = {}
        try:
            out["carparams"] = json.loads(str(FK["carparams_json"]))
        except Exception:
            out["carparams"] = {}
    out["fw"] = sorted({str(f.get("fw", f) if isinstance(f, dict) else f).replace(chr(0), "").strip() for f in (W["meta"].get("carfw") or [])
                        if "39990" in str(f)})
    out["hand_off"] = V.handsoff_v3(W) if hasattr(V, "handsoff_v3") else (np.abs(W["bar"]) < 300)
    return out


def analyse(route, min_deg=60.0, plot_dir=None, synthetic=False):
    t0 = time.time()
    R = load(route, synthetic)
    W = R["W"]
    t, th, sp, T, bar, v, eng = W["t"], W["theta"], W["theta_sp"], W["T100"], W["bar"], W["vego"], W["eng"]
    import angle_loop_drive_read as D0
    import drive_read_v299 as V0
    tap = D0.tap_ok(W)
    if not tap:                                     # release firmware: 0x1AB is Honda's motor torque, never the lane
        T = np.full_like(np.asarray(th, float), np.nan)
    cc = R.get("cc", np.full_like(th, np.nan))
    ho = R["hand_off"]
    RL = V0.reaction_label(W)
    ho_r = V0.handsoff_v3_alt(W, RL)
    # band-passed per engaged run (zero-phase); NaN outside
    bth, bsp, bcc = (np.full_like(th, np.nan) for _ in range(3))
    for a, b in runs(eng, 200):
        for src, dst in ((th, bth), (sp, bsp), (cc, bcc)):
            seg = np.nan_to_num(src[a:b])
            dst[a:b] = signal.sosfiltfilt(SOS, seg)
    dsp = np.gradient(sp) * FS
    # the fork's limiter (Dom c6452361 carcontroller.py: rate cap MAX_ANGLE_RATE, then the ERROR CLIP
    # |apply - steeringAngleDeg| <= ANGLE_ERROR_MAX(v), knots <= 11.75 m/s scaled by AccordAngleClipScale)
    prm = R.get("params", {})
    def _pf(k, d):
        try:
            return float(prm.get(k)) if prm.get(k) not in (None, "") else d
        except ValueError:
            return d
    letter = (W["meta"].get("tap") or {}).get("letter")
    rate_deg_frame, rate_src = V0.rate_cap(prm, letter)       # the cap the fork ran, said where it came from
    mrate, cscale = rate_deg_frame * 100.0, _pf("AccordAngleClipScale", 1.0)
    KC = V0.fork_constants()                                   # error clip read from the fork's values.py
    bp = list(KC["err_bp"])
    ev = [x * (cscale if b <= 11.75 else 1.0) for b, x in zip(bp, KC["err_v"])]
    co = R.get("co", sp)
    cs_ang = W["ang"]
    emax = np.interp(v, bp, ev)
    clipb = np.abs(np.abs(co - cs_ang) - emax) < 0.15
    rateb = np.abs(np.abs(np.r_[0.0, np.diff(co)]) - mrate / 100.0) < 0.02
    # HOLD = the setpoint is (nearly) still: |d sp/dt| low-passed at 2 Hz < 8 deg/s for >= 0.5 s
    dspl = signal.sosfiltfilt(signal.butter(2, 2.0, fs=FS, output="sos"), np.nan_to_num(dsp))
    hold = eng & (np.abs(dspl) < 8.0)
    m = eng & (W["tse"] >= 1.0) & (np.abs(th) >= min_deg)
    eps = []
    for a, b in runs(m, 100):
        s = slice(a, b)
        dur = (b - a) / FS
        y, x, z = bth[s], bsp[s], bcc[s]
        r2, lag, k = best_lag_fit(y, x)
        xs = np.r_[np.zeros(lag), x[:len(x) - lag]] if lag else x
        resid = y - k * xs
        Tm = T[s]
        sgn = np.sign(Tm[np.abs(Tm) > 2]) if tap else np.zeros(0)
        e = dict(t=float(t[a] - t[0]), t_abs=float(t[a]), dur=dur, v=float(np.median(v[s])),
                 th=float(np.median(th[s])), th_max=float(np.max(np.abs(th[s]))),
                 handsoff=float(np.mean(ho[s])), press=float(np.mean(R.get("press", np.zeros_like(eng))[s])),
                 rms_th=float(np.std(y)), rms_sp=float(np.std(x)), rms_cc=float(np.nanstd(z)),
                 r2=float(r2), lag_ms=lag * 10, k=float(k), rms_resid=float(np.std(resid)),
                 pp_th=float(np.ptp(y)), pp_sp=float(np.ptp(x)),
                 f_th=domfreq(y), f_sp=domfreq(x), f_res=domfreq(resid),
                 rev_th=reversals(th[s]) / dur, rev_sp=reversals(sp[s]) / dur, rev_cc=reversals(np.nan_to_num(cc[s])) / dur,
                 capduty=float(np.mean(rateb[s])), clipduty=float(np.mean(clipb[s])),
                 clipflips=float(np.sum(np.diff(clipb[s].astype(np.int8)) == 1) / dur),
                 err50=float(np.median(np.abs(sp[s] - th[s]))), err95=float(np.percentile(np.abs(sp[s] - th[s]), 95)),
                 T_rms=float(np.sqrt(np.mean(Tm ** 2))) if tap else np.nan,
                 T_pk=float(np.max(np.abs(Tm))) if tap else np.nan,
                 T_flip=(float(np.sum(np.diff(sgn) != 0) / dur) if len(sgn) > 1 else 0.0) if tap else np.nan,
                 handsoff_r2=float(np.mean(ho_r[s])), react=float(np.mean(RL["mask"][s])),
                 react_r2_med=float(np.nanmedian(RL["r2"][s])) if np.isfinite(RL["r2"][s]).any() else np.nan,
                 bar_p90=float(np.percentile(np.abs(bar[s]), 90)))
        for L in (300, 512, 1229):
            f = np.abs(bar[s]) > L
            e["frz%d" % L] = float(np.mean(f))
            e["tog%d" % L] = float(np.sum(np.diff(f.astype(np.int8)) == 1) / dur)
            if L == 1229:                               # the same toggles, those that fall in a REACTION frame
                on_ = np.r_[False, f[1:] & ~f[:-1]]
                e["tog1229_react"] = float(np.sum(on_ & RL["mask"][s]) / dur)
        hs = runs(hold[a:b], 50)
        if len(hs):
            hy = np.concatenate([th[a + i:a + j] - np.mean(th[a + i:a + j]) for i, j in hs])
            hx = np.concatenate([sp[a + i:a + j] - np.mean(sp[a + i:a + j]) for i, j in hs])
            hd = float(sum(j - i for i, j in hs)) / FS
            e.update(hold_s=hd, hold_th_rms=float(np.std(hy)), hold_sp_rms=float(np.std(hx)),
                     hold_th_pp=float(max(np.ptp(th[a + i:a + j]) for i, j in hs)),
                     hold_rev=sum(reversals(th[a + i:a + j]) for i, j in hs) / hd,
                     hold_rev_sp=sum(reversals(sp[a + i:a + j]) for i, j in hs) / hd,
                     hold_f=domfreq(np.concatenate([signal.detrend(th[a + i:a + j]) for i, j in hs])),
                     hold_T_flip=(float(np.mean([np.sum(np.diff(np.sign(T[a + i:a + j][np.abs(T[a + i:a + j]) > 2])) != 0)
                                                 for i, j in hs])) / max(hd / len(hs), 1e-9)) if tap else np.nan,
                     hold_err=float(np.median(np.abs(sp[a:b][hold[a:b]] - th[a:b][hold[a:b]]))),
                     hold_frz1229=float(np.mean(np.abs(bar[a:b][hold[a:b]]) > 1229)),
                     hold_clip=float(np.mean(clipb[a:b][hold[a:b]])))
        else:
            e.update(hold_s=0.0, hold_th_rms=np.nan, hold_sp_rms=np.nan, hold_th_pp=np.nan, hold_rev=np.nan,
                     hold_rev_sp=np.nan, hold_f=np.nan, hold_T_flip=np.nan, hold_err=np.nan, hold_frz1229=np.nan, hold_clip=np.nan)
        e["_slice"] = (int(a), int(b))
        eps.append(e)
    # engaged-time context
    ctx = dict(eng_s=float(np.sum(eng) / FS), hi_s=float(np.sum(m) / FS), hi_ho_s=float(np.sum(m & ho) / FS),
               hi_ho_r2_s=float(np.sum(m & ho_r) / FS), hi_react_s=float(np.sum(m & RL["mask"]) / FS), tap=tap,
               rate_cap_deg_frame=rate_deg_frame, rate_cap_src=rate_src)
    if plot_dir:
        plot(route, R, eps, bth, bsp, plot_dir)
    for e in eps:
        e.pop("_slice")
    return dict(route=route, fw=R["fw"], params={k: R.get("params", {}).get(k) for k in (
        "AccordAngleMaxRate", "AccordAngleClipScale", "AccordAngleBarFromEps", "SteerRatio", "AccordEpsAngleLoop",
        "GitCommit")}, fork_commit=R["fm"].get("fork_commit_full"), fork_err=R["fork_err"],
        steerControlType=R.get("carparams", {}).get("steerControlType"), ctx=ctx, eps=eps, secs=time.time() - t0)


def plot(route, R, eps, bth, bsp, d):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    W = R["W"]
    t = W["t"]
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    top = sorted(eps, key=lambda e: -e["dur"] * e["handsoff"])[:6]
    if not top:
        return
    fig, axs = plt.subplots(len(top), 1, figsize=(11, 3.0 * len(top)), squeeze=False)
    for ax, e in zip(axs[:, 0], top):
        a, b = e["_slice"]
        a0, b0 = max(a - 150, 0), min(b + 150, len(t))
        s = slice(a0, b0)
        tt = t[s] - t[a]
        ax.plot(tt, W["theta"][s], color="#1f5fa8", lw=1.4, label="wheel 0x14A")
        ax.plot(tt, W["theta_sp"][s], color="#d1495b", lw=1.0, label="setpoint 0xE4")
        if "cc" in R:
            ax.plot(tt, R["cc"][s], color="#888888", lw=0.8, ls="--", label="fork desired (pre-limiter)")
        ax.axvspan(0, (b - a) / FS, color="#f3e9c6", alpha=0.5, lw=0)
        ax2 = ax.twinx()
        if R["tap"]:
            ax2.plot(tt, W["T100"][s], color="#2a9d8f", lw=0.7, alpha=0.8, label="tap T (LSB)")
        ax2.plot(tt, W["bar"][s] / 8.0, color="#9b5de5", lw=0.6, alpha=0.6, label="0x18F word/8")
        ax2.axhline(1229 / 8.0, color="#9b5de5", lw=0.5, ls=":")
        ax2.axhline(-1229 / 8.0, color="#9b5de5", lw=0.5, ls=":")
        ax.set_title("%s  t=%.1f s  %.1f m/s  |theta| %.0f deg  hands-off %.0f%%  band rms wheel %.2f / sp %.2f deg  R2 %.2f"
                     % (route.split("_")[1][:20], e["t"], e["v"], abs(e["th"]), 100 * e["handsoff"], e["rms_th"],
                        e["rms_sp"], e["r2"]), fontsize=8)
        ax.set_ylabel("deg")
        ax2.set_ylabel("LSB")
    axs[0, 0].legend(loc="upper left", fontsize=7)
    axs[-1, 0].set_xlabel("s from episode start (shaded = |theta| >= threshold, engaged)")
    fig.tight_layout()
    p = d / ("highangle_%s.png" % route.split("_")[1].replace("--", "_"))
    fig.savefig(p, dpi=90)
    plt.close(fig)
    print("  plot", p)


_TAP_COLS = [True]


def _c(x, fmt, w):
    """fmt % x; a tap column on release firmware (no tap) is '-' right-aligned to w."""
    return (fmt % x) if _TAP_COLS[0] else "-".rjust(w)


def report(res):
    _TAP_COLS[0] = bool(res["ctx"]["tap"])
    print("=" * 118)
    print("ROUTE %s   fw %s   fork %s   steerControlType %s   (%.1f s)" % (
        res["route"], res["fw"], (res["fork_commit"] or "")[:9], res["steerControlType"], res["secs"]))
    print("  params %s" % res["params"])
    c = res["ctx"]
    print("  engaged %.0f s ; |theta| >= thr engaged %.1f s, of it hands-off %.1f s by |bar| < 300, %.1f s with the reaction "
          "test (%.1f s of it are reaction frames)" % (c["eng_s"], c["hi_s"], c["hi_ho_s"], c["hi_ho_r2_s"], c["hi_react_s"]))
    print("  rate cap %.2f deg/frame (%s)" % (c["rate_cap_deg_frame"], c["rate_cap_src"]))
    if not c["tap"]:
        print("  LANE TAP: NOT AVAILABLE on release firmware (no tap) -- the Trms / Tpk / Tflip columns and HOLD T flips below "
              "are '-'")
    hdr = ("  t      dur   v    theta  HO%  rmsTh rmsSp rmsCc  R2  lag  k    resid  fTh  fRes  revTh revSp revCc cap%  "
           "e50  e95  Trms Tpk Tflip f1229 tg1229 f512 tg512 f300 bar90")
    print(hdr)
    for e in res["eps"]:
        print("  %6.1f %4.1f %4.1f %6.1f %4.0f %5.2f %5.2f %5.2f %4.2f %3d %4.2f %5.2f %4.2f %4.2f %5.2f %5.2f %5.2f %4.0f %4.1f %4.1f %s %s %s %5.2f %5.2f %5.2f %5.2f %5.2f %5.0f" % (
            e["t"], e["dur"], e["v"], e["th"], 100 * e["handsoff"], e["rms_th"], e["rms_sp"], e["rms_cc"], e["r2"],
            e["lag_ms"], e["k"], e["rms_resid"], e["f_th"], e["f_res"], e["rev_th"], e["rev_sp"], e["rev_cc"],
            100 * e["capduty"], e["err50"], e["err95"], _c(e["T_rms"], "%4.0f", 4), _c(e["T_pk"], "%3.0f", 3),
            _c(e["T_flip"], "%5.2f", 5), e["frz1229"], e["tog1229"],
            e["frz512"], e["tog512"], e["frz300"], e["bar_p90"]))
        print("         HOLD %.1f s: wheel rms %.2f pp %.2f deg, sp rms %.2f, wheel rev %.2f /s, sp rev %.2f /s, f %.2f Hz, "
              "T flips %s /s, |sp-th| %.1f, f1229 %.2f, clip %.2f ; episode clip-bound %.2f (onsets %.2f /s)" % (e["hold_s"], e["hold_th_rms"], e["hold_th_pp"],
              e["hold_sp_rms"], e["hold_rev"], e["hold_rev_sp"], e["hold_f"], _c(e["hold_T_flip"], "%.2f", 1), e["hold_err"],
              e["hold_frz1229"], e["hold_clip"], e["clipduty"], e["clipflips"]))
        print("         REACTION TEST: hands-off %.0f %% (vs %.0f %% by |bar| < 300), reaction frames %.0f %% (median window R2 %s); "
              "1229 freeze onsets %.2f /s, %.2f /s of them in a reaction frame" % (
                  100 * e["handsoff_r2"], 100 * e["handsoff"], 100 * e["react"], (("%.2f" % e["react_r2_med"]) if np.isfinite(e["react_r2_med"]) else "-"),
                  e["tog1229"], e["tog1229_react"]))
    E = [e for e in res["eps"] if e["handsoff"] >= 0.8]
    if E:
        w = np.array([e["dur"] for e in E])
        f = lambda k: float(np.average([e[k] for e in E], weights=w))
        ratio = f("rms_sp") / max(f("rms_th"), 1e-9)
        verdict = ("FORK-SOURCED" if (f("r2") >= 0.5 and ratio >= 0.7) else
                   "FIRMWARE-SOURCED" if ratio < 0.4 else "MIXED")
        print("  HANDS-OFF (>= 80 %%) episodes: %d, %.1f s; dur-weighted rms wheel %.2f sp %.2f cc %.2f deg, R2 %.2f, "
              "resid %.2f, rev wheel %.2f sp %.2f /s, f1229 %.3f, cap %.2f -> %s" % (
                  len(E), w.sum(), f("rms_th"), f("rms_sp"), f("rms_cc"), f("r2"), f("rms_resid"), f("rev_th"),
                  f("rev_sp"), f("frz1229"), f("capduty"), verdict))
        print("  clip-bound duty (dur-weighted) %.2f" % f("clipduty"))
        res["summary"] = dict(n=len(E), secs=float(w.sum()), rms_th=f("rms_th"), rms_sp=f("rms_sp"), rms_cc=f("rms_cc"),
                              r2=f("r2"), resid=f("rms_resid"), rev_th=f("rev_th"), rev_sp=f("rev_sp"),
                              frz1229=f("frz1229"), cap=f("capduty"), verdict=verdict)
    else:
        print("  no hands-off (>= 80 %) high-angle engaged episode")
    Er = [e for e in res["eps"] if e["handsoff_r2"] >= 0.8]
    if Er:
        w = np.array([e["dur"] for e in Er])
        print("  HANDS-OFF by the REACTION TEST (>= 80 %%) episodes: %d, %.1f s; dur-weighted 1229 freeze onsets %.2f /s "
              "(%.2f /s in reaction frames)" % (len(Er), w.sum(), np.average([e["tog1229"] for e in Er], weights=w),
                                                np.average([e["tog1229_react"] for e in Er], weights=w)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("routes", nargs="+")
    ap.add_argument("--min-deg", type=float, default=60.0)
    ap.add_argument("--plot", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--synthetic-release", action="store_true", help="SELF-CHECK: strip the tap from the cached route (see angle_loop_drive_read.strip_tap)")
    a = ap.parse_args()
    allr = []
    for r in a.routes:
        res = analyse(r, a.min_deg, a.plot, a.synthetic_release)
        report(res)
        allr.append(res)
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(allr, indent=1, default=float))


if __name__ == "__main__":
    main()
