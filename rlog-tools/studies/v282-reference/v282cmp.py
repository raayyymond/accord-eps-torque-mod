"""Shared definitions for the V282 (rate-servo EPS) vs V293 (torque-mode EPS) comparison.

Every stream imports THIS, so route attribution, references, masks, events and estimators are identical.
Caches: analysis-2020accord/_scratch/cache/v282ref/<counter>--<hash>.npz  (build_cache.py)

Attribution (EVIDENCE): V293 first flew 2026-09-13 18:12 PDT on route 70 (BUILD-LINEAGE-PART6). V289 flew
2026-09-09 (r62/r63), the operator then reverted to V282; V292 flew 2026-09-13 (r6d/6e/6f --5e7b..).
r64/r65b/r6c(2bc842dbac) fall between the revert and V292, their 0x14A b4[3:7] code family matches the
documented V282 routes r39/r3a and differs from V288/V289/V292, and prior verdicts used r6c/r39 as V282.
"""
import math
from pathlib import Path
import numpy as np
from scipy import signal

KIT = Path(__file__).resolve().parents[3]
CACHE = KIT / "analysis-2020accord" / "_scratch" / "cache" / "v282ref"

# group, EPS firmware, fork commit, fork lateral config as flown (from initData)
ROUTES = {
    "00000064--ce6b0b0ebb": dict(group="V282", eps="V282", fork="0f98d8c7", note="LAF 6.0 Kp 0.9, rate-plant FF on"),
    "00000065--b9f78988bd": dict(group="V282", eps="V282", fork="0f98d8c7", note="LAF 6.0 Kp 0.9, rate-plant FF on"),
    "0000006c--2bc842dbac": dict(group="V282", eps="V282", fork="57410c3b", note="LAF 6.0 Kp 0.9, 62 segs"),
    "00000039--f56039af87": dict(group="V282old", eps="V282", fork="8a28dcef", note="LAF 2.11 Kp 0.8"),
    "0000003a--283a39a1d6": dict(group="V282old", eps="V282", fork="ffe28378", note="LAF 4.0 Kp 0.8, seg 10 missing"),
    "0000003c--927965c2b4": dict(group="V282old", eps="V282", fork="ffe28378", note="LAF 3.6 Kp 0.8"),
    "0000006c--68c6e94b17": dict(group="T64", eps="V293", fork="84766cdc", note="rev 6.4 as shipped"),
    "0000006d--05e83bb04f": dict(group="T64", eps="V293", fork="84766cdc", note="rev 6.4 as shipped"),
    "0000006e--6ca3e014fd": dict(group="T64B", eps="V293", fork="84766cdc", note="rev 6.4, AccordHoldLevel OFF (ARM-B)"),
    "00000076--d0b7ea7e4d": dict(group="T5", eps="V293", fork="e44b6cd3", note="rev 5"),
    "00000075--6c8687d5bd": dict(group="T4", eps="V293", fork="08a5a706", note="rev 4"),
}
FS = 100.0
G = 9.81


def load(route):
    """Everything on the controlsState clock. Lateral accels in m/s^2, angles deg, torque in [-1,1] output units."""
    D = np.load(CACHE / f"{route}.npz", allow_pickle=True)
    t = D["t_cs"]
    I = lambda tk, k: np.interp(t, D[tk], D[k]) if (tk in D.files and k in D.files and len(D[tk])) else np.full(len(t), np.nan)
    v = I("t_cst", "vego")
    S = dict(route=route, meta=ROUTES.get(route, {}), t=t, v=v,
             active=(D["cs_active"] > 0.5) & (I("t_cc", "lat_active") > 0.5),
             pressed=I("t_cst", "spress") > 0.5,
             sa=I("t_cst", "sa_deg"), sr=I("t_cst", "sr_deg"), aoff=I("t_lp", "aoff"),
             model=D["cs_des_curv"] * v * v,          # the MODEL's desired lateral accel (the goal's reference)
             setpoint=D["cs_la_des"],                  # the controller's shaped setpoint (post delay-comp / filters)
             la_act=D["cs_la_act"],                    # the controller's own achieved measurement
             la_yaw=I("t_cst", "cs_yaw") * v,          # independent: carState yaw rate x v
             la_pose=I("t_pose", "pose_wz") * v,       # independent: livePose yaw x v (device frame, check sign)
             jerk_des=D["cs_la_jerk"],
             out=D["cs_out"], p=D["cs_p"], i=D["cs_i"], f=D["cs_f"], sat=D["cs_sat"] > 0.5,
             e4=I("t_e4", "e4_cmd"), roll=I("t_lp", "roll"), sR=I("t_lp", "sR"),
             storque=I("t_cst", "storque"), storque_eps=I("t_cst", "storque_eps"),
             lat_delay=I("t_ld", "ld_delay"))
    return S


def usable(S, vmin=0.0, vmax=99.0):
    return S["active"] & ~S["pressed"] & (S["v"] >= vmin) & (S["v"] < vmax)


def runs(mask, t, min_s=0.0, max_gap=4.0 / FS):
    """Contiguous True stretches with no clock gap; never concatenate across a gap (every join is a step)."""
    out, n, i = [], len(mask), 0
    while i < n:
        if not mask[i]:
            i += 1; continue
        j = i
        while j + 1 < n and mask[j + 1] and (t[j + 1] - t[j]) < max_gap:
            j += 1
        if (t[j] - t[i]) >= min_s:
            out.append((i, j + 1))
        i = j + 1
    return out


def band_H(segs, f1, f2):
    """Per-bin |H| = |Pxy|/Pxx averaged over the band weighted by input power (no complex-phasor averaging, which
    biases |H| low where phase rotates), plus coherence and the phasor-averaged phase. segs = [(x, y), ...]."""
    segs = [s for s in segs if len(s[0]) >= 256]
    if not segs:
        return None
    nps = int(2 ** np.floor(np.log2(min(len(x) for x, _ in segs))))
    nps = min(nps, 8192)
    Pxx = Pyy = Pxy = None; fr = None; sec = 0.0
    for x, y in segs:
        xs, ys = x - x.mean(), y - y.mean()
        f, pxx = signal.welch(xs, FS, nperseg=nps, noverlap=nps // 2)
        _, pyy = signal.welch(ys, FS, nperseg=nps, noverlap=nps // 2)
        _, pxy = signal.csd(xs, ys, FS, nperseg=nps, noverlap=nps // 2)
        w = len(xs)
        Pxx = pxx * w if Pxx is None else Pxx + pxx * w
        Pyy = pyy * w if Pyy is None else Pyy + pyy * w
        Pxy = pxy * w if Pxy is None else Pxy + pxy * w
        fr = f; sec += w / FS
    s = (fr >= f1) & (fr < f2)
    if s.sum() < 1:
        return None
    w = Pxx[s]
    H = np.abs(Pxy[s]) / np.maximum(Pxx[s], 1e-30)
    coh = np.abs(Pxy[s]) ** 2 / np.maximum(Pxx[s] * Pyy[s], 1e-30)
    return dict(H=float(np.average(H, weights=w)), coh=float(np.average(coh, weights=w)),
                phase=float(np.degrees(np.angle(Pxy[s].sum()))), sec=sec, n=len(segs),
                df=float(fr[1] - fr[0]), in_rms=float(np.sqrt(np.sum(Pxx[s]) * (fr[1] - fr[0]) / max(sec, 1e-9))))


def lowpass(x, fc, order=2):
    sos = signal.butter(order, fc, btype="low", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x)


def deriv(x):
    return np.gradient(x) * FS


def jerk_events(S, jerk_thr=0.8, vmin=5.0, pre=1.5, post=3.0, min_sep=2.0, lp_hz=2.0):
    """High desired-lateral-JERK events from the MODEL reference (not the controller's own setpoint).
    jerk = d/dt of the 2 Hz-lowpassed model lateral accel. An event is a local peak of |jerk| >= jerk_thr m/s^3,
    at least min_sep s from the previous, with the whole [-pre, +post] window usable and contiguous."""
    m = usable(S, vmin)
    model = np.nan_to_num(S["model"])
    j = deriv(lowpass(model, lp_hz))
    aj = np.abs(j)
    pk, _ = signal.find_peaks(aj, height=jerk_thr, distance=int(min_sep * FS))
    ev = []
    a, b = int(pre * FS), int(post * FS)
    for k in pk:
        if k - a < 0 or k + b >= len(model):
            continue
        sl = slice(k - a, k + b)
        if not m[sl].all() or np.any(np.diff(S["t"][sl]) > 4.0 / FS):
            continue
        ev.append(dict(idx=int(k), t=float(S["t"][k]), v=float(np.median(S["v"][sl])),
                       jerk_peak=float(j[k]), la_peak=float(np.max(np.abs(model[sl]))),
                       la_step=float(model[k + b] - model[k - a])))
    return ev, j


def accel_events(S, la_thr=1.5, vmin=5.0, min_hold=1.0, pre=1.5, post=1.5):
    """Sustained high desired lateral ACCEL events (curves, turns): |model| >= la_thr for >= min_hold s."""
    m = usable(S, vmin)
    model = np.nan_to_num(S["model"])
    hi = (np.abs(lowpass(model, 1.0)) >= la_thr) & m
    ev = []
    for a, b in runs(hi, S["t"], min_s=min_hold):
        a0, b0 = a - int(pre * FS), b + int(post * FS)
        if a0 < 0 or b0 >= len(model) or not m[a0:b0].all():
            continue
        ev.append(dict(i0=int(a0), i1=int(b0), ia=int(a), ib=int(b), t=float(S["t"][a]),
                       v=float(np.median(S["v"][a:b])), la_peak=float(np.max(np.abs(model[a:b]))),
                       dur=float((b - a) / FS), sign=float(np.sign(np.mean(model[a:b])))))
    return ev


def event_metrics(S, i0, i1, ach_key="la_act", maxlag_s=0.8):
    """Tracking quality of one window. Returns gain (regression of achieved on lag-aligned desired), lag (s, +=car
    lags), rms and peak error before/after lag alignment, peak ratio, overshoot, and achieved-jerk roughness:
    RMS of the achieved jerk minus the desired jerk (lag aligned), both 5 Hz lowpassed."""
    x = np.nan_to_num(S["model"][i0:i1]); y = np.nan_to_num(S[ach_key][i0:i1])
    n = len(x); L = int(maxlag_s * FS)
    best, lag = -np.inf, 0
    for k in range(0, L + 1):
        xa, ya = x[: n - k], y[k:]
        if len(xa) < 20:
            break
        c = float(np.dot(xa - xa.mean(), ya - ya.mean()))
        if c > best:
            best, lag = c, k
    xa, ya = x[: n - lag], y[lag:]
    gain = float(np.dot(xa, ya) / max(np.dot(xa, xa), 1e-9))
    jx = deriv(lowpass(xa, 5.0)) if len(xa) > 30 else np.zeros_like(xa)
    jy = deriv(lowpass(ya, 5.0)) if len(ya) > 30 else np.zeros_like(ya)
    px, py = float(np.max(np.abs(x))), float(np.max(np.abs(y)))
    sgn = np.sign(x[np.argmax(np.abs(x))]) if px > 0 else 1.0
    over = float(max(0.0, np.max(sgn * y) - np.max(sgn * x)))
    return dict(gain=gain, lag=lag / FS, rms_err=float(np.sqrt(np.mean((y - x) ** 2))),
                rms_err_aligned=float(np.sqrt(np.mean((ya - gain * 0 - xa) ** 2))),
                peak_ratio=py / max(px, 1e-9), overshoot=over,
                jerk_rough=float(np.sqrt(np.mean((jy - jx) ** 2))), jerk_des_rms=float(np.sqrt(np.mean(jx ** 2))))


def steer_hf(S, i0, i1, f1=2.0, f2=10.0):
    """RMS of steering RATE in [f1, f2] Hz over a window: the texture the driver feels as jerk/ratchet/grind."""
    x = np.nan_to_num(S["sr"][i0:i1])
    if len(x) < 64:
        return float("nan")
    sos = signal.butter(4, [f1, f2], btype="band", fs=FS, output="sos")
    return float(np.sqrt(np.mean(signal.sosfiltfilt(sos, x) ** 2)))


def _self_test():
    """Positive controls for event_metrics and band_H on synthetic data with known answers."""
    t = np.arange(0, 60, 1 / FS)
    rng = np.random.default_rng(0)
    x = lowpass(rng.standard_normal(len(t)), 0.8) * 3
    lagN = 25
    y = 0.8 * np.concatenate([np.zeros(lagN), x[:-lagN]])
    S = dict(model=x, la_act=y)
    em = event_metrics(S, 500, 5500)
    assert abs(em["lag"] - 0.25) < 0.011, em
    assert abs(em["gain"] - 0.8) < 0.02, em
    r = band_H([(x, y)], 0.1, 0.6)
    assert abs(r["H"] - 0.8) < 0.02 and r["coh"] > 0.98, r
    return "self-test OK: lag 0.25 s and gain 0.8 recovered; band |H| 0.8 recovered"


if __name__ == "__main__":
    print(_self_test())
    for rk, meta in ROUTES.items():
        f = CACHE / f"{rk}.npz"
        if not f.exists():
            print(f"  {rk:24s} {meta['group']:8s} (no cache yet)")
            continue
        S = load(rk)
        u = usable(S)
        ev, _ = jerk_events(S)
        ae = accel_events(S)
        print(f"  {rk:24s} {meta['group']:8s} usable {u.sum()/FS:6.0f} s  (>15 m/s {usable(S,15).sum()/FS:5.0f} s, "
              f"<15 {usable(S,0,15).sum()/FS:5.0f} s)  jerk events {len(ev):4d}  accel events {len(ae):3d}")
