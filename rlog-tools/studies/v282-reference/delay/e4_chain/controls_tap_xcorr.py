"""Two positive controls that decide what the chain numbers and the orchestrator's 30 ms can be trusted for.

(a) TAP-FIT CONTROL.  Synthesise the 0x1AB tap from the route's own 0xE4 command with a KNOWN law
    (pure delay dd, first-order pole fc at 1 kHz, gain 0.63), sampled at the real tap arrival instants,
    quantised to 8 counts and clipped to the real tap's +-2461 rail; fit it with chain_timing.tap_fit (level and
    differenced) exactly as the real tap is fitted.  Pass: dd within 5 ms and fc recovered to the grid.
(b) THE ORCHESTRATOR'S ESTIMATOR on a synthetic plant with KNOWN D (30, 60 ms): sent-command vs d/dt(rate)
    on a 10 ms grid, both 1-6 Hz band-passed (4th-order Butterworth, zero phase), peak |normalised corr| over
    lags -50..250 ms -- as in orch_crux.py section 4 -- open loop, rate quantised 1 deg/s, angle 0.1 deg.
Usage: python controls_tap_xcorr.py <counter--hash>
"""
import sys, json, math
from pathlib import Path
import numpy as np
from scipy import signal
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain_timing as CT
import plant_delay as P


def tap_control(route):
    D = dict(np.load(HERE / "cache" / f"{route}.npz"))
    CH = dict(np.load(HERE / "cache" / f"{route}_chain.npz"))
    CL = dict(np.load(HERE / "cache" / f"{route}_clock.npz"))
    lam = float(CL["lam_mean"])
    tx = D["sc_t"] + lam * 1e-3
    cmd = D["sc_cmd"].astype(float)
    eab = CL["eab"]
    m = CH["mask"].astype(bool)
    out = {}
    fine = (2, 3, 4, 4.5, 5, 5.5, 6, 7, 8, 10, 15, np.inf)
    for fc, dd in ((5.05, 4), (np.inf, 30), (np.inf, 60), (3.0, 20)):
        # synthetic tap on a 1 kHz grid over the whole route, ZOH command at its on-bus time
        ok = np.isfinite(eab)
        T = np.full(len(eab), np.nan)
        # piecewise over contiguous send stretches to keep the grid small
        breaks = np.where(np.diff(tx) > 0.05)[0]
        starts = np.concatenate([[0], breaks + 1]); ends = np.concatenate([breaks + 1, [len(tx)]])
        for s_, e_ in zip(starts, ends):
            if e_ - s_ < 100:
                continue
            g0 = tx[s_]
            grid = np.arange(g0, tx[e_ - 1], 0.001)
            u = cmd[s_:e_][np.clip(np.searchsorted(tx[s_:e_], grid, side="right") - 1, 0, None)]
            y = CT.lpf_grid(u, fc)
            sel = ok & (eab > g0 + 0.2) & (eab < tx[e_ - 1])
            gi = np.clip(np.round((eab[sel] - dd * 1e-3 - g0) / 0.001).astype(int), 0, len(y) - 1)
            T[sel] = y[gi] * 0.63
        Tq = np.sign(T) * (np.floor(np.abs(np.nan_to_num(T)) / 8.0) * 8.0)
        Tq = np.clip(Tq, -2461, 2461)
        tab = np.where(np.isfinite(T), eab, np.nan)
        lev = CT.tap_fit(tx, cmd, m, tab, Tq, fcs=fine)
        dif = CT.tap_fit(tx, cmd, m, tab, Tq, fcs=fine, diff=True)
        key = f"true fc={fc} dd={dd}"
        out[key] = dict(level_best=lev["best"], diff_best=dif["best"],
                        diff_dd_at_true_fc=dif["best_dd_per_fc"].get("inf" if not np.isfinite(fc) else
                                                                     min(fine, key=lambda z: abs(z - fc))))
        print(key, "level", lev["best"][:3], "diff", dif["best"][:3], flush=True)
    return out


def orch_xcorr(ty, rate, tu, u, runs, v):
    """orch_crux.py section 4 on a regular 10 ms grid: u ZOH-sampled at the measurement instants."""
    sos = signal.butter(4, [1.0, 6.0], btype="band", fs=100.0, output="sos")
    num = {}; cnt = 0
    for a, b in runs:
        if np.median(v[a:b]) <= 3.0 or (ty[b - 1] - ty[a]) < 30.0:
            continue
        t = ty[a:b]
        uu = u[np.clip(np.searchsorted(tu, t, side="right") - 1, 0, None)]
        acc = np.gradient(rate[a:b]) * 100.0
        c = signal.sosfiltfilt(sos, uu); y = signal.sosfiltfilt(sos, acc)
        for L in range(-5, 26):
            ca, ya = (c[:len(c) - L], y[L:]) if L >= 0 else (c[-L:], y[:len(y) + L])
            num[L] = num.get(L, 0.0) + float(np.dot(ca, ya)) / math.sqrt(float(np.dot(ca, ca) * np.dot(ya, ya)) + 1e-12)
        cnt += 1
    if not cnt:
        return None
    Ls = sorted(num); vals = np.array([num[L] / cnt for L in Ls])
    ib = int(np.argmax(np.abs(vals)))
    # parabolic refinement on |corr|
    Lh = float(Ls[ib])
    if 0 < ib < len(vals) - 1:
        y0, y1, y2 = np.abs(vals[ib - 1:ib + 2])
        den = y0 - 2 * y1 + y2
        if den < 0:
            Lh += 0.5 * (y0 - y2) / den
    return dict(lag_ms=Ls[ib] * 10, lag_refined_ms=round(Lh * 10, 1), corr=float(vals[ib]), runs=cnt)


def xcorr_control(route):
    R = P.load_route(route, "14A")
    runs = P.runs_of(R["mask"], R["ty"])
    out = {"real_on_this_time_base": orch_xcorr(R["ty"], R["rate"], R["tu"], R["u"], runs, R["v"])}
    print("real", out["real_on_this_time_base"], flush=True)
    for J, b in ((8e-5, 0.003), (8e-5, 0.0006), (1e-3, 0.003)):
        for Dt in (30, 60):
            rq, aq = P.simulate(R, Dt, J, b=b, rate_lsb=1.0)
            r = orch_xcorr(R["ty"], rq, R["tu"], R["u"], runs, R["v"])
            out[f"J={J:g} b={b:g} D={Dt}"] = r
            print(J, b, Dt, r, flush=True)
    return out


if __name__ == "__main__":
    route = sys.argv[1]
    res = {"tap_control": tap_control(route), "orch_xcorr_control": xcorr_control(route)}
    json.dump(res, open(HERE / "out" / f"controls_{route}.json", "w"), indent=1, default=float)
