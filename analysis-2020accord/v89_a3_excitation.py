#!/usr/bin/env python3
"""v89_a3_excitation.py -- WHICH INPUT drives the 6-9 Hz ratchet?  And what is its Q?

Three candidate excitation paths, and they select different firmware levers:

  P1  THE DELIVERED COMMAND (gp-0x6b98)   -> a command-side lever (Lever B class) can work.
                                             V88 already halved 15-22 Hz command content and
                                             the ratchet did NOT move, so P1 is on the ropes.
  P2  ROAD INPUT (imu_vert / imu_lat / wheel-speed roughness)
                                          -> NO firmware lever can work; it is a plant problem.
  P3  DRIVER WHEEL MOTION (steering rate) -> the lever is whatever converts wheel motion into
                                             assist: the torque-sensor derivative lanes and the
                                             angle-rate boost arm.

v89_a1/a2 showed the 6-9 Hz column energy scales with |steer rate| (slope +0.49) and that the
ENGAGED/MANUAL excess at matched rate climbs 2.09x -> 21.17x with rate while a negative control
band stays ~1.3-3.8x. That points at P3, but points is not proves.

TESTS
  E1  multiple + PARTIAL coherence of the engaged column torque against (cmd, road, rate),
      each against a shuffled-pairs control computed on the SAME windows.
  E2  the same, MANUAL arm -- P2 must survive disengagement; P1 and P3-via-firmware must not.
  E3  the 4-15 Hz resonance: f0 and Q from the peak shape, engaged vs manual, rate-matched.
  E4  the envelope test done properly -- many short engaged runs, |rate| vs the 6-9 Hz envelope,
      with the negative-control envelope as the control.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, coherence, csd, hilbert, sosfiltfilt, welch

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "_cache_r73"
sys.path.insert(0, str(CACHE))
OUT = CACHE / "v89_a3_excitation.json"
RNG = np.random.default_rng(890303)

NPERSEG = 256
BAND = (6.0, 9.0)
NEG = (32.0, 38.0)
CIRC_LO, CIRC_HI = 2.073, 2.088


def order_hits(v, lo, hi, nmax=6):
    if v <= 0.05:
        return False
    for circ in (CIRC_LO, CIRC_HI):
        for n in range(1, nmax + 1):
            if lo <= n * v / circ < hi:
                return True
    return False


def runs_of(mask, minlen):
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i >= minlen:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def band_mean(f, y, lo, hi):
    m = (f >= lo) & (f < hi)
    return float(np.mean(y[m])) if m.any() else float("nan")


def coh_of(x, y, fs, lo, hi):
    f, c = coherence(x, y, fs=fs, nperseg=NPERSEG, noverlap=NPERSEG // 2)
    return band_mean(f, c, lo, hi)


def shuffled_control(x, y, fs, lo, hi, n=40):
    """Break the pairing by circularly rotating y by a random amount >= 2 s."""
    vals = []
    lo_shift = int(2 * fs)
    for _ in range(n):
        s = RNG.integers(lo_shift, max(lo_shift + 1, len(y) - lo_shift))
        vals.append(coh_of(x, np.roll(y, s), fs, lo, hi))
    return float(np.median(vals)), float(np.percentile(vals, 95))


def partial_coh(y, x_main, others, fs, lo, hi):
    """Coherence of y with x_main after linearly removing `others` from BOTH, in the band.

    Frequency-domain regression: for each Fourier bin, project out the others.
    """
    def F(a):
        w = np.hanning(NPERSEG)
        segs = []
        for s in range(0, len(a) - NPERSEG + 1, NPERSEG // 2):
            seg = a[s:s + NPERSEG]
            segs.append(np.fft.rfft((seg - seg.mean()) * w))
        return np.array(segs)

    f = np.fft.rfftfreq(NPERSEG, 1.0 / fs)
    Y, Xm = F(y), F(x_main)
    Os = [F(o) for o in others]
    m = (f >= lo) & (f < hi)
    if Y.shape[0] < 6 or not m.any():
        return float("nan")
    num, den_y, den_x = 0.0, 0.0, 0.0
    for k in np.where(m)[0]:
        yk, xk = Y[:, k].copy(), Xm[:, k].copy()
        if Os:
            A = np.column_stack([o[:, k] for o in Os])
            # complex least squares projection
            coef_y = np.linalg.lstsq(A, yk, rcond=None)[0]
            coef_x = np.linalg.lstsq(A, xk, rcond=None)[0]
            yk = yk - A @ coef_y
            xk = xk - A @ coef_x
        num += np.abs(np.vdot(xk, yk)) ** 2
        den_y += np.vdot(yk, yk).real ** 2 if False else np.sum(np.abs(yk) ** 2)
        den_x += np.sum(np.abs(xk) ** 2)
    return float(num / (den_x * den_y)) if den_x > 0 and den_y > 0 else float("nan")


def q_from_peak(f, p, lo=4.0, hi=15.0):
    """f0 and Q from the half-power width of the largest peak in [lo, hi] above a fitted floor."""
    m = (f >= lo) & (f <= hi)
    ff, pp = f[m], p[m].copy()
    if len(ff) < 8:
        return None
    # log-linear background over the window, refit excluding the peak
    for _ in range(3):
        A = np.column_stack([np.ones_like(ff), np.log(ff)])
        b = np.linalg.lstsq(A, np.log(pp + 1e-30), rcond=None)[0]
        bg = np.exp(A @ b)
        resid = pp / bg
        k = int(np.argmax(resid))
        keep = np.ones(len(ff), bool)
        keep[max(0, k - 2):k + 3] = False
        if keep.sum() > 4:
            A2, y2 = A[keep], np.log(pp[keep] + 1e-30)
            b = np.linalg.lstsq(A2, y2, rcond=None)[0]
            bg = np.exp(A @ b)
    excess = pp - bg
    k = int(np.argmax(excess))
    if excess[k] <= 0:
        return None
    half = excess[k] / 2.0
    i = k
    while i > 0 and excess[i] > half:
        i -= 1
    j = k
    while j < len(ff) - 1 and excess[j] > half:
        j += 1
    if j <= i:
        return None
    f0 = ff[k]
    bw = ff[j] - ff[i]
    return {"f0": float(f0), "bw": float(bw), "Q": float(f0 / bw) if bw > 0 else None,
            "prom": float(pp[k] / bg[k])}


def main():
    from v88_d3_fork import signed_grids            # reuse the validated reconstruction

    z = np.load(CACHE / "r73.npz", allow_pickle=True)
    g50, g100 = signed_grids(CACHE, "r73")
    fs = float(g100["fs"])
    rep = {"fs": fs}
    print(f"100 Hz grid: n={len(g100['t'])}, fs={fs:.3f}")

    t = np.asarray(g100["t"], float)
    cmd = np.asarray(g100["signed"], float)
    tq = np.asarray(g100["tq"], float)
    rate = np.asarray(g100["rate_c"], float)
    v = np.asarray(g100["v"], float)

    # bring the IMU + wheel speeds onto the 100 Hz probe grid
    tr = np.asarray(z["t"], float)
    imu_v = np.interp(t, tr, z["imu_vert"].astype(float))
    imu_l = np.interp(t, tr, z["imu_lat"].astype(float))
    eng = np.interp(t, tr, (z["cc_lat"].astype(float) > 0.5).astype(float)) > 0.5
    sst = np.interp(t, tr, z["sstat"].astype(float))
    ws = z["ws_kph"].astype(float)
    wst = z["ws_t"].astype(float)
    ws_rough = np.interp(t, wst, np.std(ws, axis=1))     # inter-wheel spread = road roughness

    good = np.isfinite(cmd) & np.isfinite(tq) & np.isfinite(rate) & (sst == 0)

    # ------------------------------------------------------------------ E1 / E2
    print("\n" + "=" * 80)
    print("E1/E2  WHICH INPUT CARRIES THE 6-9 Hz COLUMN ENERGY?  coherence vs its own control")
    print("=" * 80)
    rep["E1"] = []
    for arm, m_arm in (("ENGAGED", eng), ("MANUAL", ~eng)):
        m = good & m_arm & (v > 0.3) & (v < 8.0)
        rr = runs_of(m, int(12 * fs))
        if not rr:
            print(f"  {arm}: no runs")
            continue
        print(f"\n  {arm}  ({len(rr)} runs, {sum(b-a for a, b in rr)/fs:.0f} s, "
              f"|rate| med {np.median(np.abs(rate[m])):.1f} deg/s, v med {np.median(v[m]):.1f} m/s)")
        chans = {"cmd  (gp-0x6b98)": cmd, "rate (wheel motion)": np.abs(rate),
                 "imu_vert (road)": imu_v, "imu_lat  (road)": imu_l,
                 "ws_rough (road)": ws_rough}
        row = {"arm": arm, "runs": len(rr), "sec": sum(b - a for a, b in rr) / fs,
               "chan": {}}
        for nm, x in chans.items():
            cs, ctl, ctl95, csn = [], [], [], []
            for a, b in rr:
                xa, ya = x[a:b], tq[a:b]
                if not (np.isfinite(xa).all() and np.std(xa) > 0):
                    continue
                cs.append(coh_of(xa, ya, fs, *BAND))
                csn.append(coh_of(xa, ya, fs, *NEG))
                c_med, c95 = shuffled_control(xa, ya, fs, *BAND, n=20)
                ctl.append(c_med)
                ctl95.append(c95)
            if not cs:
                continue
            print(f"    {nm:22s} coh(6-9) {np.median(cs):.3f}  ctl {np.median(ctl):.3f} "
                  f"(p95 {np.median(ctl95):.3f})   coh(32-38) {np.median(csn):.3f}   "
                  f"{'ABOVE' if np.median(cs) > np.median(ctl95) else 'at control'}")
            row["chan"][nm] = {"coh": float(np.median(cs)), "ctl": float(np.median(ctl)),
                               "ctl95": float(np.median(ctl95)),
                               "coh_neg": float(np.median(csn))}
        rep["E1"].append(row)

    # partial: rate's coherence after removing cmd, and cmd's after removing rate
    print("\n  PARTIAL (engaged, 6-9 Hz) -- who survives conditioning on the other?")
    m = good & eng & (v > 0.3) & (v < 8.0)
    rr = runs_of(m, int(12 * fs))
    pr, pc = [], []
    for a, b in rr:
        pr.append(partial_coh(tq[a:b], np.abs(rate[a:b]), [cmd[a:b]], fs, *BAND))
        pc.append(partial_coh(tq[a:b], cmd[a:b], [np.abs(rate[a:b])], fs, *BAND))
    pr = np.array([x for x in pr if np.isfinite(x)])
    pc = np.array([x for x in pc if np.isfinite(x)])
    if len(pr) and len(pc):
        print(f"    rate | cmd  = {np.median(pr):.3f}      cmd | rate = {np.median(pc):.3f}")
        rep["partial"] = {"rate_given_cmd": float(np.median(pr)),
                          "cmd_given_rate": float(np.median(pc))}

    # ------------------------------------------------------------------ E3
    print("\n" + "=" * 80)
    print("E3  THE RESONANCE -- f0 and Q from the peak shape, engaged vs manual, rate-matched")
    print("=" * 80)
    rep["E3"] = []
    for arm, m_arm in (("ENGAGED", eng), ("MANUAL", ~eng)):
        for rlo, rhi in [(3, 20), (20, 60)]:
            m = good & m_arm & (v > 0.3) & (v < 8.0)
            idx = np.where(m)[0]
            if len(idx) < NPERSEG * 3:
                continue
            keep = []
            for s in range(0, len(tq) - NPERSEG + 1, NPERSEG // 2):
                sl = slice(s, s + NPERSEG)
                if not m[sl].all():
                    continue
                rm = np.median(np.abs(rate[sl]))
                if not (rlo <= rm < rhi):
                    continue
                if order_hits(float(np.median(v[sl])), 4.0, 15.0):
                    continue
                keep.append(s)
            if len(keep) < 4:
                print(f"  {arm:8s} |rate| {rlo:2d}-{rhi:2d} deg/s : n={len(keep)} -- insufficient")
                continue
            acc = None
            w = np.hanning(NPERSEG)
            for s in keep:
                seg = tq[s:s + NPERSEG]
                X = np.fft.rfft((seg - seg.mean()) * w)
                p = (np.abs(X) ** 2) / (np.sum(w ** 2) * fs)
                acc = p if acc is None else acc + p
            acc /= len(keep)
            f = np.fft.rfftfreq(NPERSEG, 1.0 / fs)
            q = q_from_peak(f, acc)
            if q:
                print(f"  {arm:8s} |rate| {rlo:2d}-{rhi:2d} deg/s : n={len(keep):3d}  "
                      f"f0={q['f0']:5.2f} Hz  bw={q['bw']:5.2f}  Q={q['Q']:6.2f}  "
                      f"prom={q['prom']:5.2f}")
                rep["E3"].append({"arm": arm, "rate_lo": rlo, "rate_hi": rhi,
                                  "n": len(keep), **q})
            else:
                print(f"  {arm:8s} |rate| {rlo:2d}-{rhi:2d} deg/s : n={len(keep):3d}  no peak")
    print("  NB Q from a periodogram half-power width is an UPPER bound on damping (a lower")
    print("     bound on Q) only if the line is resolved: 1 bin = "
          f"{fs/NPERSEG:.3f} Hz, so Q > ~{8.0/(2*fs/NPERSEG):.0f} is UNRESOLVED.")

    # ------------------------------------------------------------------ E4
    print("\n" + "=" * 80)
    print("E4  ENVELOPE TEST -- does |rate| LEAD the 6-9 Hz envelope?  (control: 32-38 Hz)")
    print("=" * 80)
    sos69 = butter(4, [6.0 / (fs / 2), 9.0 / (fs / 2)], btype="band", output="sos")
    sos32 = butter(4, [32.0 / (fs / 2), 38.0 / (fs / 2)], btype="band", output="sos")
    rep["E4"] = []
    for arm, m_arm in (("ENGAGED", eng), ("MANUAL", ~eng)):
        m = good & m_arm & (v > 0.3) & (v < 8.0)
        rr = runs_of(m, int(15 * fs))
        if not rr:
            continue
        lags = np.arange(-int(0.5 * fs), int(0.5 * fs) + 1)
        A69, A32, n = np.zeros(len(lags)), np.zeros(len(lags)), 0
        for a, b in rr:
            x = np.abs(rate[a:b])
            e69 = np.abs(hilbert(sosfiltfilt(sos69, tq[a:b] - tq[a:b].mean())))
            e32 = np.abs(hilbert(sosfiltfilt(sos32, tq[a:b] - tq[a:b].mean())))
            k = 15
            sm = lambda u: np.convolve(u, np.ones(k) / k, mode="same")
            zz = lambda u: (sm(u) - sm(u).mean()) / (sm(u).std() + 1e-12)
            x, e69, e32 = zz(x), zz(e69), zz(e32)
            for i, L in enumerate(lags):
                if L >= 0:
                    A69[i] += float(np.dot(x[:len(x) - L], e69[L:]) / (len(x) - L))
                    A32[i] += float(np.dot(x[:len(x) - L], e32[L:]) / (len(x) - L))
                else:
                    A69[i] += float(np.dot(x[-L:], e69[:len(x) + L]) / (len(x) + L))
                    A32[i] += float(np.dot(x[-L:], e32[:len(x) + L]) / (len(x) + L))
            n += 1
        A69 /= n
        A32 /= n
        k69, k32 = int(np.argmax(A69)), int(np.argmax(A32))
        print(f"  {arm:8s} {n} runs, {sum(b-a for a,b in rr)/fs:.0f} s")
        print(f"    6-9 Hz env : peak r={A69[k69]:+.3f} @ {lags[k69]/fs*1000:+.0f} ms   "
              f"r(0)={A69[len(lags)//2]:+.3f}")
        print(f"    32-38 ctrl : peak r={A32[k32]:+.3f} @ {lags[k32]/fs*1000:+.0f} ms   "
              f"r(0)={A32[len(lags)//2]:+.3f}")
        rep["E4"].append({"arm": arm, "runs": n,
                          "peak_r_69": float(A69[k69]), "lag_ms_69": float(lags[k69]/fs*1000),
                          "r0_69": float(A69[len(lags)//2]),
                          "peak_r_32": float(A32[k32]), "lag_ms_32": float(lags[k32]/fs*1000),
                          "r0_32": float(A32[len(lags)//2])})

    OUT.write_text(json.dumps(rep, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
