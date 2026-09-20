"""MANDATORY PLANT POSITIVE CONTROL + the decisive check: why a signal-based D_act on the REAL V293 routes is void.

Plant (exactly the brief's):  J*acc = u(t-D) - b*rate - k(v)*angle - F*sign(rate),  1 kHz semi-implicit Euler,
driven by the route's ACTUAL logged 0xE4 command at its on-bus time, sampled at the ACTUAL 0x14A/0x18F frame
instants, quantised (angle 0.1 deg, rate 1 deg/s on 0x14A, 0.125 deg/s on 0x18F).

Estimator under test = PHASE SLOPE of rate w.r.t. the on-bus command over a high band (the plant's own phase
there is ~-180 deg and flat, so the slope is the delay).  Must recover true D = 30 and 60 ms within 5 ms.

Then the same estimator is run on:
  (a) OPEN LOOP synthetic  (the 0xE4 command is the logged one, independent of the simulated rate) -> recover D
  (b) CLOSED LOOP synthetic (the 0xE4 command is the logged one PLUS the fork's own rate loop acting on the
      SIMULATED rate: quantised to the sensor LSB, through a 0.01 s lag, applied D_ctl = 11 ms after its sample)
  (c) the REAL logged rate and the REAL logged command.
If (b) reproduces (c) and both are far from (a), a signal-based D_act on real closed-loop routes is unidentifiable.
Usage: python verify_cl_confound.py <counter--hash> [--sensor 14A|18F]
"""
import sys, json, math
from pathlib import Path
import numpy as np
from scipy import signal
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plant_delay as P

BANDS = ((6, 15), (8, 20), (10, 25))


def phase_slope(runs, ty, rate, tu, u, f1, f2, nper=256, fs=100.0):
    """D = -d(phase)/d(omega) of the command -> rate cross spectrum, coherence weighted."""
    Sxy = Sxx = Syy = None
    for a, b in runs:
        t = ty[a:b]
        if len(t) < nper + 8:
            continue
        uu = u[np.clip(np.searchsorted(tu, t, side="right") - 1, 0, None)].astype(float)
        rr = np.nan_to_num(rate[a:b]).astype(float)
        f, pxy = signal.csd(uu, rr, fs=fs, nperseg=nper, noverlap=nper // 2, detrend="linear")
        _, pxx = signal.welch(uu, fs=fs, nperseg=nper, noverlap=nper // 2, detrend="linear")
        _, pyy = signal.welch(rr, fs=fs, nperseg=nper, noverlap=nper // 2, detrend="linear")
        Sxy = pxy if Sxy is None else Sxy + pxy
        Sxx = pxx if Sxx is None else Sxx + pxx
        Syy = pyy if Syy is None else Syy + pyy
    s = (f >= f1) & (f <= f2)
    coh = np.abs(Sxy[s]) ** 2 / np.maximum(Sxx[s] * Syy[s], 1e-30)
    ph = np.unwrap(np.angle(Sxy[s]))
    w = np.sqrt(np.clip(coh, 0, .999) / np.maximum(1 - np.clip(coh, 0, .999), 1e-3))
    A = np.stack([2 * math.pi * f[s], np.ones(int(s.sum()))], 1)
    beta, *_ = np.linalg.lstsq(A * w[:, None], ph * w, rcond=None)
    return dict(D_ms=round(-beta[0] * 1e3, 2), icpt_deg=round(math.degrees(beta[1]) % 360 - 180, 1),
                coh=round(float(coh.mean()), 3))


def sim(R, D_true, J, b, Kfb=0.0, D_ctl_ms=11.0, F=0.02, ku=1.0 / 4089, tau=0.01, rate_lsb=1.0):
    """Kfb = 0 -> open loop.  Returns the quantised rate at the real frame instants AND the TOTAL command a
    0xE4 log would carry (logged part + the fork's rate loop on the simulated rate), on its own 1 kHz grid."""
    rate_q = np.full(len(R["ty"]), np.nan)
    gts, uts = [], []
    for a, b_ in P.runs_of(R["mask"], R["ty"]):
        t = R["ty"][a:b_]
        grid = np.arange(t[0] - 0.5, t[-1] + 0.01, 0.001)
        ul = R["u"][np.clip(np.searchsorted(R["tu"], grid, side="right") - 1, 0, None)].astype(float) * ku
        vg = np.interp(grid, t, R["v"][a:b_])
        k = np.interp(vg, P.K_V_BP, P.K_V)
        nD, nC = int(round(D_true)), int(round(D_ctl_ms))
        al = math.exp(-0.001 / tau)
        th = w = rf = 0.0
        n_ = len(grid)
        W = np.empty(n_); Ucmd = np.empty(n_); RF = np.empty(n_)
        for n in range(n_):
            rq = round(w / rate_lsb) * rate_lsb          # what the sensor reports
            rf = al * rf + (1 - al) * rq                 # the fork's 0.01 s rate filter
            RF[n] = rf
            Ucmd[n] = ul[n] - Kfb * RF[max(n - nC, 0)]   # the command SENT now (logged + feedback, D_ctl old)
            un = Ucmd[max(n - nD, 0)]                    # the command that ACTS now
            acc = (un - b * w - k[n] * th - F * math.tanh(w / 0.5)) / J
            w += acc * 0.001
            th += w * 0.001
            W[n] = w
        gi = np.clip(np.round((t - grid[0]) / 0.001).astype(int), 0, n_ - 1)
        rate_q[a:b_] = np.round(W[gi] / rate_lsb) * rate_lsb
        gts.append(grid); uts.append(Ucmd / ku)
    return rate_q, np.concatenate(gts), np.concatenate(uts)


def main(route, sensor="14A"):
    R = P.load_route(route, sensor)
    lsb = 1.0 if sensor == "14A" else 0.125
    runs = P.runs_of(R["mask"], R["ty"])
    out = {"route": route, "sensor": sensor, "n_runs": len(runs), "rate_lsb": lsb}
    out["real"] = {f"{a}-{b}Hz": phase_slope(runs, R["ty"], R["rate"], R["tu"], R["u"], a, b) for a, b in BANDS}
    print("REAL", json.dumps(out["real"]), flush=True)
    for J, b in ((8e-5, 0.003), (1e-3, 0.003)):
        for Dt in (30, 60):
            rq, gt, ut = sim(R, Dt, J, b, Kfb=0.0, rate_lsb=lsb)
            r = {f"{f1}-{f2}Hz": phase_slope(runs, R["ty"], rq, R["tu"], R["u"], f1, f2) for f1, f2 in BANDS}
            out[f"OL J={J:g} b={b:g} D={Dt}"] = r
            print(f"OL J={J:g} b={b:g} D={Dt}", json.dumps(r), flush=True)
            del rq, gt, ut
    for Kfb in (1e-3, 3e-3):
        rq, gt, ut = sim(R, 30, 8e-5, 0.003, Kfb=Kfb, rate_lsb=lsb)
        r = {f"{f1}-{f2}Hz": phase_slope(runs, R["ty"], rq, gt, ut, f1, f2) for f1, f2 in BANDS}
        out[f"CL J=8e-05 D=30 Kfb={Kfb:g}"] = r
        print(f"CL Kfb={Kfb:g} (true D=30)", json.dumps(r), flush=True)
        del rq, gt, ut
    json.dump(out, open(HERE / "out" / f"verify_cl_{route}_{sensor}.json", "w"), indent=1)


if __name__ == "__main__":
    s = "18F" if ("--sensor" in sys.argv and sys.argv[sys.argv.index("--sensor") + 1] == "18F") else "14A"
    main(sys.argv[1], s)
