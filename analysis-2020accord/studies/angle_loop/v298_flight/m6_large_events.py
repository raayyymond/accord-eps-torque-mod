# -*- coding: utf-8 -*-
r"""m6_large_events.py -- M6 part 2: LARGE manoeuvres (note 2) event by event, the setpoint limiter's share, the
hard-turn 1.6-3 Hz normalisation, and the >22 m/s band split.

    python analysis-2020accord/studies/angle_loop/v298_flight/m6_large_events.py

ANALYSIS ONLY, cache only (r79_a1f5d2_al + r79_fork.npz).  Writes _scratch/out/r79/m6/m6_large_events.{txt,json}.

EVENT = an engaged stretch where |desired| (carControl.actuators.steeringAngleDeg) >= 10 deg, >= 0.5 s, whose peak
|desired| >= 20 deg.  Per event: speed, peak |desired| / |wire sp| / |theta|, peak rates (2 Hz LPF derivative) of
each, peak |tap| (LSB = T/8; the rail 2461 T = 307.6 LSB), max |theta - sp| (the FIRMWARE loop's error) and
max |theta - desired| (end to end), fraction of frames the fork limited the setpoint (|des - wire sp| > 0.5 deg)
and of those at the fork's 1.2 deg/frame rate cap, pressed fraction.
LIMITER attribution on carOutput frames (100 Hz, latActive): |co - des| > 0.5 deg split into (a) error clip active
(|co - carState angle| within 0.15 deg of ANGLE_ERROR_MAX(vEgoRaw) -- formula verified exactly, max excess 7e-6 deg),
(b) rate cap (|co[k] - co[k-1]| >= 1.19 deg), (c) the rest (VM lateral-accel / lateral-jerk limits, override O1).
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
from scipy import signal

T0 = time.time()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m6_common as C                                                   # noqa: E402
from m6_common import runs, FS                                         # noqa: E402

OUT = C.REPO / "_scratch" / "out" / "r79" / "m6"
OUT.mkdir(parents=True, exist_ok=True)
LINES = []
SB = (("<3", 0, 3), ("3-8", 3, 8), ("8-12", 8, 12), ("12-18", 12, 18), ("18-25", 18, 25), (">25", 25, 99))
SOS2 = signal.butter(2, 2.0, "lowpass", fs=FS, output="sos")
SOS05 = signal.butter(4, 0.5, "lowpass", fs=FS, output="sos")


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


def lpf_rate(x, rr):
    y = np.zeros(len(x))
    for a, b in rr:
        if b - a > 30:
            y[a:b] = np.gradient(signal.sosfiltfilt(SOS2, np.nan_to_num(x[a:b]))) * FS
    return y


def main():
    F = C.load_fork()
    W = C.load("r79_a1f5d2_al")
    t = W["t"]
    des = C._zoh(F["t_cc"], F["cc_ang"], t)
    co_rate_cap = np.r_[False, np.abs(np.diff(F["co_ang"])) >= 1.19]
    cap = C._zoh(F["t_co"], co_rate_cap.astype(float), t) > 0.5
    rr = runs(W["eng"], 30)
    r_des, r_sp, r_th = lpf_rate(des, rr), lpf_rate(W["theta_sp"], rr), lpf_rate(W["theta"], rr)
    J = {}

    # ---------------------------------------------------------------- limiter attribution (carOutput frames)
    co, tco = F["co_ang"], F["t_co"]
    j = np.clip(np.searchsorted(F["t_cs"], tco, side="right") - 1, 0, len(F["t_cs"]) - 1)
    jc = np.clip(np.searchsorted(F["t_cc"], tco, side="right") - 1, 0, len(F["t_cc"]) - 1)
    lat = F["cc_latActive"][jc].astype(bool)
    dco = F["cc_ang"][jc] - co
    v = F["cs_vegoraw"][j]
    bnd = np.interp(v, [3.1, 8, 10, 11.75, 17.5, 26.9], [17, 15.5, 19.5, 17, 8.5, 4.5])
    clipa = np.abs(co - F["cs_ang"][j]) >= bnd - 0.15
    press = F["cs_press"][j].astype(bool)
    pr("L. LIMITER attribution, carOutput frames with latActive, per band (vEgoRaw): share of frames with |des - co| > 0.5 deg,"
       " and of those: error clip / 1.2 deg-frame rate cap / other (VM accel-jerk, O1 override); pressed share of 'other'")
    J["limiter"] = {}
    for nm, lo, hi in SB:
        m = lat & (v >= lo) & (v < hi)
        lim = m & (np.abs(dco) > 0.5)
        n = max(lim.sum(), 1)
        a = (lim & clipa).sum() / n
        b = (lim & ~clipa & co_rate_cap).sum() / n
        oth = lim & ~clipa & ~co_rate_cap
        J["limiter"][nm] = dict(s=float(m.sum() / FS), lim=float(lim.mean() if m.any() else np.nan) if False else float(lim.sum() / max(m.sum(), 1)),
                                clip=float(a), rate=float(b), other=float(oth.sum() / n),
                                other_pressed=float((oth & press).sum() / max(oth.sum(), 1)),
                                dco_p95=float(np.percentile(np.abs(dco[m]), 95)) if m.any() else np.nan)
        L = J["limiter"][nm]
        pr("   %-6s latActive %6.1f s  limited %5.1f %%  -> clip %5.1f %%  rate-cap %5.1f %%  other %5.1f %% (pressed %4.1f %%)  |des-co| p95 %5.1f deg"
           % (nm, L["s"], 100 * L["lim"], 100 * L["clip"], 100 * L["rate"], 100 * L["other"], 100 * L["other_pressed"], L["dco_p95"]))

    # ---------------------------------------------------------------- large-manoeuvre events
    m10 = W["eng"] & (np.abs(des) >= 10)
    ev = []
    for a, b in runs(m10, 50):
        if np.abs(des[a:b]).max() < 20:
            continue
        sl = slice(a, b)
        ev.append(dict(t=float(t[a] - t[0]), dur=(b - a) / FS, v=float(W["vego"][sl].mean()),
                       des=float(np.abs(des[sl]).max()), sp=float(np.abs(W["theta_sp"][sl]).max()),
                       th=float(np.abs(W["theta"][sl]).max()),
                       rdes=float(np.abs(r_des[sl]).max()), rsp=float(np.abs(r_sp[sl]).max()), rth=float(np.abs(r_th[sl]).max()),
                       tap=float(np.nanmax(np.abs(W["T100"][sl]))) if np.isfinite(W["T100"][sl]).any() else np.nan,
                       err_fw=float(np.abs(W["theta"][sl] - W["theta_sp"][sl]).max()),
                       err_e2e=float(np.abs(W["theta"][sl] - des[sl]).max()),
                       lim=float((np.abs(des[sl] - W["theta_sp"][sl]) > 0.5).mean()), cap=float(cap[sl].mean()),
                       press=float(np.nan_to_num(W["pressed"][sl]).mean()),
                       bar=float(np.abs(W["bar"][sl]).max())))
    J["events"] = ev
    pr("\nE. LARGE-MANOEUVRE EVENTS (peak |desired| >= 20 deg; %d events).  Medians per speed band [p90 in brackets]" % len(ev))
    pr("   band   n  dur  |des| |sp| |th| | rate deg/s: des   sp   theta | tap LSB (rail 308) | err fw  err e2e | limited cap | pressed")
    J["event_bands"] = {}
    keys = ("dur", "des", "sp", "th", "rdes", "rsp", "rth", "tap", "err_fw", "err_e2e", "lim", "cap", "press")
    for nm, lo, hi in SB + (("ALL", 0, 99),):
        E = [e for e in ev if lo <= e["v"] < hi]
        if not E:
            continue
        A = {k: np.array([e[k] for e in E]) for k in keys}
        md = {k: float(np.nanmedian(A[k])) for k in keys}
        p9 = {k: float(np.nanpercentile(A[k], 90)) for k in keys}
        J["event_bands"][nm] = dict(n=len(E), med=md, p90=p9)
        pr("   %-5s %3d %4.1f %5.0f %4.0f %4.0f |        %5.0f %4.0f %5.0f   | %4.0f [%4.0f]         | %5.1f [%4.1f] %5.1f [%5.1f] | %4.2f %4.2f | %4.2f"
           % (nm, len(E), md["dur"], md["des"], md["sp"], md["th"], md["rdes"], md["rsp"], md["rth"], md["tap"], p9["tap"],
              md["err_fw"], p9["err_fw"], md["err_e2e"], p9["err_e2e"], md["lim"], md["cap"], md["press"]))
    # hands-free events only
    Ef = [e for e in ev if e["press"] < 0.05]
    if Ef:
        A = {k: np.array([e[k] for e in Ef]) for k in keys}
        pr("   hands-free events only (pressed < 5 %%): n %d  |des| %.0f |sp| %.0f |th| %.0f  rates %.0f/%.0f/%.0f  tap %.0f [p90 %.0f, max %.0f]  err fw %.1f  e2e %.1f  limited %.2f cap %.2f"
           % (len(Ef), *(np.median(A[k]) for k in ("des", "sp", "th", "rdes", "rsp", "rth", "tap")), np.percentile(A["tap"], 90),
              np.nanmax(A["tap"]), np.median(A["err_fw"]), np.median(A["err_e2e"]), np.median(A["lim"]), np.median(A["cap"])))
        J["events_free"] = dict(n=len(Ef), tap_max=float(np.nanmax(A["tap"])))
    # theta reach vs sp reach: ratio of peaks; theta rate vs sp rate
    A = {k: np.array([e[k] for e in ev]) for k in keys}
    pr("   ALL events: peak|theta|/peak|sp| median %.3f [p10 %.3f]; peak theta-rate / peak sp-rate median %.2f; peak sp-rate / peak des-rate median %.2f"
       % (np.median(A["th"] / A["sp"]), np.percentile(A["th"] / A["sp"], 10), np.median(A["rth"] / A["rsp"]), np.median(A["rsp"] / A["rdes"])))

    # ---------------------------------------------------------------- tap vs firmware error, all engaged-free (authority used)
    pr("\nT. AUTHORITY USED: |tap| (LSB) by |theta - sp| class, engaged & free (rail = 307.6 LSB)")
    e = np.abs(W["theta"] - W["theta_sp"])
    m = W["eng"] & W["free"] & np.isfinite(W["T100"])
    J["tap_by_err"] = {}
    for lo, hi in ((0, 1), (1, 3), (3, 6), (6, 10), (10, 99)):
        k = m & (e >= lo) & (e < hi)
        if k.sum() < 20:
            continue
        tp = np.abs(W["T100"][k])
        J["tap_by_err"]["%g-%g" % (lo, hi)] = dict(s=float(k.sum() / FS), p50=float(np.median(tp)), p90=float(np.percentile(tp, 90)),
                                                   max=float(tp.max()), rail=float((tp >= 300).mean()))
        pr("   |err| %4g-%-3g deg  %6.1f s  |tap| p50 %5.0f  p90 %5.0f  max %5.0f  at rail %.2f %%"
           % (lo, hi, k.sum() / FS, np.median(tp), np.percentile(tp, 90), tp.max(), 100 * (tp >= 300).mean()))

    # ---------------------------------------------------------------- hard-turn 1.6-3 Hz: wheel vs setpoint content
    pr("\nH. HARD-TURN (engaged, free, |theta| >= 20) 1.6-3 Hz rms: wheel rate w18 vs the wire setpoint's own rate content")
    sos_h = signal.butter(2, (1.6, 3.0), btype="bandpass", fs=FS, output="sos")
    J["hard"] = {}
    for nm, lo, hi in SB + (("ALL", 0, 99),):
        nw = ns = ne = 0.0
        cnt = 0
        for a, b in runs(W["eng"] & (W["vego"] >= lo) & (W["vego"] < hi), 200):
            sp_r = np.gradient(W["theta_sp"][a:b]) * FS
            yw = signal.sosfiltfilt(sos_h, W["w18"][a:b] - W["w18"][a:b].mean())
            ys = signal.sosfiltfilt(sos_h, sp_r - sp_r.mean())
            s_ = W["free"][a:b] & (np.abs(W["theta"][a:b]) >= 20)
            nw += (yw[s_] ** 2).sum(); ns += (ys[s_] ** 2).sum(); cnt += int(s_.sum())
        if cnt > 100:
            J["hard"][nm] = dict(s=cnt / FS, wheel=float(np.sqrt(nw / cnt)), sp=float(np.sqrt(ns / cnt)))
            pr("   %-5s %5.1f s  wheel %5.2f deg/s  setpoint %5.2f deg/s  ratio %.2f" % (nm, cnt / FS, np.sqrt(nw / cnt), np.sqrt(ns / cnt), np.sqrt(nw / ns)))

    # ---------------------------------------------------------------- >22 band split within the drive-read run
    pr("\nX. THE >22 m/s RUN split by speed (drive-read form: 0.5 Hz LPF, first 4 s dropped)")
    m = W["eng"] & W["free"] & (W["vego"] >= 22)
    J["x22"] = {}
    for a, b in runs(m, 1500):
        x = signal.sosfiltfilt(SOS05, W["theta_sp"][a:b]); y = signal.sosfiltfilt(SOS05, W["theta"][a:b])
        vv = W["vego"][a:b]
        for nm, k in (("22-25", (vv < 25)), (">=25", vv >= 25), ("all", np.ones(len(vv), bool))):
            k = k & (np.arange(b - a) >= 400)
            if k.sum() < 300:
                continue
            A = np.vstack([x[k], np.ones(k.sum())]).T
            s = np.linalg.lstsq(A, y[k], rcond=None)[0][0]
            J["x22"][nm] = dict(s=float(k.sum() / FS), slope=float(s), sp_sd=float(x[k].std()))
            pr("   run t=%.0f s  %-6s %5.1f s  slope %.3f  sp sd %.2f deg  sp range %.2f..%.2f" % (t[a] - t[0], nm, k.sum() / FS, s, x[k].std(), x[k].min(), x[k].max()))
        # where is the residual: the shape over time (first vs second half)
        h = (b - a) // 2
        for nm, (p, q) in (("1st half", (400, h)), ("2nd half", (h, b - a))):
            A = np.vstack([x[p:q], np.ones(q - p)]).T
            s = np.linalg.lstsq(A, y[p:q], rcond=None)[0][0]
            pr("   run t=%.0f s  %-8s slope %.3f sp sd %.2f  v %.1f m/s" % (t[a] - t[0], nm, s, x[p:q].std(), vv[p:q].mean()))
    J["runtime_s"] = time.time() - T0
    pr("\nwall time %.1f s" % J["runtime_s"])
    (OUT / "m6_large_events.txt").write_text("\n".join(LINES), encoding="utf-8")
    (OUT / "m6_large_events.json").write_text(json.dumps(J, default=float, indent=0))


if __name__ == "__main__":
    main()
