"""Closed-loop identification of the forward delay (command on-bus -> steering acceleration), and its controls.

Why this exists: on the real routes the high-frequency phase-slope estimator (plant_delay.py --phase), which
passes its OPEN-loop positive control, returns a NEGATIVE delay with high coherence: above ~6 Hz the command is
dominated by the controller REACTING to measured wheel motion, so the cross-spectrum measures the feedback path.

Estimator 3 (direct ARX, closed-loop consistent when the noise is whitened and the feedback has >= 1 sample of delay):
   acc_n = beta_u * mean_{[t_{n-1}, t_n]} u_eff(t - D)
           + sum_{i=1..p} a_i acc_{n-i} + c0 rate_{n-1} + c1 angle_{n-1} + c2 angle*v + c3 angle*v^2 + c4 rate*v
           + c5 sign(rate_{n-1}) + 1
   acc_n = (rate_n - rate_{n-1}) / dt  (backward difference -> averages true acc over [t_{n-1}, t_n])
   u_eff = raw 0xE4 command (ZOH at its on-bus time)  or  the measured tap law (fc pole + dd) applied to it
   D scanned 0..120 ms at 1 ms; D_hat = argmax R^2 (+ parabolic refinement); run-cluster bootstrap CI.

Controls (synthetic plant on the route's own time base, rate quantised to the channel's LSB):
   OL : J*acc = u(t-D) - b*rate - k(v)*angle - F*sign(rate)
   CL : same + disturbance torque w (band 1-25 Hz) + FEEDBACK u_fb = -Kfb * LPF_10ms(rate_meas(t - 21 ms)),
        i.e. the fork's rate loop with the measured 21 ms arrival->TX latency, gain raised to make the feedback
        path dominate the high band as it does on the real routes.
Usage: python closedloop.py <counter--hash> [--sensor 18F|14A] [--control-only] [--real-only]
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.signal import lfilter
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plant_delay as P

D_GRID = np.arange(0, 121, 1)
AR = 4


def sim_cl(R, D_true, J, b=0.003, F=0.02, ku=1.0 / 4089, pole=None, rate_lsb=0.125, Kfb=0.0, A_ms=21.0,
           w_rms=0.0, seed=0):
    rng = np.random.default_rng(seed)
    rate_q = np.full(len(R["ty"]), np.nan); ang_q = np.full(len(R["ty"]), np.nan)
    u_tx = np.full(len(R["tu"]), np.nan)                 # the command actually "sent" (logged + feedback)
    tu = R["tu"]
    sos_w = signal.butter(2, [1.0, 25.0], btype="band", fs=1000, output="sos")
    a_rc = np.exp(-0.001 / 0.010)
    for a, b_ in P.runs_of(R["mask"], R["ty"]):
        t = R["ty"][a:b_]
        g0 = t[0] - 0.5
        grid = np.arange(g0, t[-1] + 0.01, 0.001)
        N = len(grid)
        ju0 = np.searchsorted(tu, g0); ju1 = np.searchsorted(tu, grid[-1])
        vg = np.interp(grid, t, R["v"][a:b_])
        k = np.interp(vg, P.K_V_BP, P.K_V)
        w = signal.sosfilt(sos_w, rng.standard_normal(N))
        w *= (w_rms / max(w.std(), 1e-12)) if w_rms > 0 else 0.0
        # delivered-torque pipeline state (for pole)
        if pole is not None:
            fc, dd = pole
            ap = np.exp(-2 * np.pi * fc * 0.001)
        else:
            ap, dd = 0.0, 0
        th = om = 0.0
        TH = np.zeros(N); W = np.zeros(N)
        cmd_grid = np.zeros(N)                             # command on bus (ZOH), filled as sends happen
        y_pole = 0.0
        meas_f = 0.0
        # sample indices where the EPS frame is taken (measurement), and sends
        gi_meas = np.clip(np.round((t - g0) / 0.001).astype(int), 0, N - 1)
        send_i = np.clip(np.round((tu[ju0:ju1] - g0) / 0.001).astype(int), 0, N - 1)
        send_ptr = 0
        cur_cmd = R["u"][max(ju0 - 1, 0)] * ku
        meas_ptr = 0
        last_meas_rate = 0.0
        meas_times = []                                    # (grid index, quantised rate)
        mq = []
        for n in range(N):
            # measurement frames
            while meas_ptr < len(gi_meas) and gi_meas[meas_ptr] <= n:
                rq = np.round(om / rate_lsb) * rate_lsb
                meas_times.append(n); mq.append(rq)
                meas_ptr += 1
            # sends: logged command + feedback on the rate measured A_ms earlier (through the 10 ms filter)
            while send_ptr < len(send_i) and send_i[send_ptr] <= n:
                if Kfb > 0 and meas_times:
                    target = n - int(A_ms)
                    kx = np.searchsorted(meas_times, target, side="right") - 1
                    r_old = mq[kx] if kx >= 0 else 0.0
                    meas_f = a_rc * meas_f + (1 - a_rc) * r_old   # coarse: one filter step per send (10 ms)
                    fb = -Kfb * meas_f
                else:
                    fb = 0.0
                cur_cmd = R["u"][ju0 + send_ptr] * ku + fb
                u_tx[ju0 + send_ptr] = cur_cmd / ku
                send_ptr += 1
            cmd_grid[n] = cur_cmd
            src = cmd_grid[n - int(D_true)] if n - int(D_true) >= 0 else cmd_grid[0]
            if pole is not None:
                src_d = cmd_grid[n - int(D_true) - int(dd)] if n - int(D_true) - int(dd) >= 0 else cmd_grid[0]
                y_pole = ap * y_pole + (1 - ap) * src_d
                src = y_pole
            acc = (src + w[n] - b * om - k[n] * th - F * np.tanh(om / 0.5)) / J
            om += acc * 0.001
            th += om * 0.001
            TH[n] = th; W[n] = om
        ang_q[a:b_] = np.round(TH[gi_meas] / 0.1) * 0.1
        rate_q[a:b_] = np.round(W[gi_meas] / rate_lsb) * rate_lsb
    u_out = np.where(np.isfinite(u_tx), u_tx, R["u"])
    return rate_q, ang_q, u_out


def arx_stats(runs, ty, rate, ang, v, tu, u, u_mode=("raw", None, None), D_grid=D_GRID, p=AR):
    ncol = 1 + p + 7
    blocks = []
    for a, b in runs:
        t = ty[a:b]; r = rate[a:b]; an = ang[a:b]; vv = v[a:b]
        if len(t) < 50:
            continue
        acc = np.empty(len(t)); acc[0] = np.nan
        acc[1:] = np.diff(r) / np.diff(t)
        g0 = t[0] - 0.2
        grid = np.arange(g0, t[-1] + 0.02, 0.001)
        iu = np.searchsorted(tu, grid, side="right") - 1
        if iu[0] < 0:
            continue
        ug = u[iu].astype(float)
        if u_mode[0] == "tap":
            ug = P.tap_law(ug, u_mode[1], u_mode[2])
        cs = np.concatenate([[0.0], np.cumsum(ug)])
        n0 = p + 1
        y = acc[n0:]
        lags = [acc[n0 - i:len(t) - i] for i in range(1, p + 1)]
        rp = r[n0 - 1:-1]; ap_ = an[n0 - 1:-1]; vp = vv[n0 - 1:-1]
        base = lags + [rp, ap_, ap_ * vp, ap_ * vp * vp, rp * vp, np.sign(rp), np.ones_like(rp)]
        tl = t[n0 - 1:-1]; tr = t[n0:]
        XtX = np.zeros((len(D_grid), ncol, ncol)); Xty = np.zeros((len(D_grid), ncol))
        for di, D in enumerate(D_grid):
            il = np.clip(np.round((tl - D * 1e-3 - g0) / 0.001).astype(int), 0, len(ug) - 1)
            ir = np.clip(np.round((tr - D * 1e-3 - g0) / 0.001).astype(int), 0, len(ug))
            um = (cs[np.maximum(ir, il + 1)] - cs[il]) / np.maximum(ir - il, 1)
            X = np.stack([um] + base, 1)
            XtX[di] = X.T @ X; Xty[di] = X.T @ y
        blocks.append(dict(XtX=XtX, Xty=Xty, yty=float(y @ y), ysum=float(y.sum()), n=len(y), v=float(np.median(vv))))
    if not blocks:
        return None
    return dict(XtX=np.array([b_["XtX"] for b_ in blocks]), Xty=np.array([b_["Xty"] for b_ in blocks]),
                yty=np.array([b_["yty"] for b_ in blocks]), n=np.array([b_["n"] for b_ in blocks]),
                v=np.array([b_["v"] for b_ in blocks]))


def est(S, sel=None, nboot=200):
    if S is None:
        return None
    r = P.estimate(S, sel=sel, nboot=nboot)
    return r


def main():
    route = sys.argv[1]
    sensor = "14A" if ("--sensor" in sys.argv and sys.argv[sys.argv.index("--sensor") + 1] == "14A") else "18F"
    R = P.load_route(route, sensor)
    runs = P.runs_of(R["mask"], R["ty"])
    tapj = json.load(open(HERE / "out" / f"timing_{route}.json"))
    bt = tapj.get("B_tap_fit_diff", {}).get("best")
    fc_tap, dd_tap = (bt[0], bt[1]) if bt else (5.05, 4)
    lsb = 0.125 if sensor == "18F" else 1.0
    fn = HERE / "out" / f"arx_{route}_{sensor}.json"
    out = json.load(open(fn)) if fn.exists() else {}
    out.update({"route": route, "sensor": sensor, "rate_lsb_control": lsb, "tap_law": [fc_tap, dd_tap], "n_runs": len(runs)})
    if "--real-only" not in sys.argv:
        ctrl = {}
        # real-data scale for the disturbance: torque ~ J * rms(HF acc) is unknown; use w_rms = 0.02 torque (1-25 Hz)
        cases = []
        for J, b in ((8e-5, 0.003), (1e-3, 0.003)):
            for Dt in (30, 60):
                cases.append((f"OL J={J:g} D={Dt}", dict(D_true=Dt, J=J, b=b)))
                cases.append((f"CL J={J:g} D={Dt} Kfb=3e-3 w=0.02", dict(D_true=Dt, J=J, b=b, Kfb=3e-3, w_rms=0.02)))
            cases.append((f"CL+pole J={J:g} Dres=10 Kfb=3e-3 w=0.02", dict(D_true=10, J=J, b=b, Kfb=3e-3, w_rms=0.02,
                                                                        pole=(fc_tap, dd_tap))))
        if "--quick" in sys.argv:
            cases = [c for c in cases if "J=8e-05" in c[0]]
        for name, kw in cases:
            rq, aq, uo = sim_cl(R, rate_lsb=lsb, **kw)
            mode = ("tap", fc_tap, dd_tap) if "pole" in kw else ("raw", None, None)
            S = arx_stats(runs, R["ty"], rq, aq, R["v"], R["tu"], uo, u_mode=mode)
            e = est(S, nboot=100)
            # the high-band phase estimator on the same closed-loop synthetic, for comparison
            ph = P.phase_boot(runs, R["ty"], rq, R["tu"], uo, mode, 10.0, 25.0, nboot=20)
            ctrl[name] = dict(arx=e, phase_10_25=ph)
            print(name, "ARX", e["D"] if e else None, e["ci95"] if e else None, "| phase", round(ph["D"], 1),
                  round(ph["coh_mean"], 3), flush=True)
        out["controls"] = ctrl
    if "--control-only" not in sys.argv:
        real = {}
        for mode in (("raw", None, None), ("tap", fc_tap, dd_tap)):
            S = arx_stats(runs, R["ty"], R["rate"], R["ang"], R["v"], R["tu"], R["u"], u_mode=mode)
            real[mode[0]] = {"all": est(S)}
            for nm, lo, hi in (("<8", 0, 8), ("8-15", 8, 15), (">=15", 15, 99)):
                sel = np.where((S["v"] >= lo) & (S["v"] < hi))[0]
                real[mode[0]][nm] = est(S, sel) if len(sel) >= 3 else None
            print("real", mode[0], {k: (v_["D"], v_["ci95"], round(v_["r2"], 3)) if v_ else None
                                    for k, v_ in real[mode[0]].items()}, flush=True)
        out["real"] = real
    json.dump(out, open(fn, "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
