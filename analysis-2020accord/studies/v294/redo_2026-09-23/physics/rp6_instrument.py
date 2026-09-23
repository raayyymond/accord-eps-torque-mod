"""
REDO-PHYSICS claim 6: can ONE 15-30 s engaged episode tell LIVE from NULL from INVERTED?

Closed-loop simulation:
  plant (BELIEF)  J th'' + b th' + k th + F tanh(th'/1 deg/s) = T_motor / 2625.4 + d(t)       (0.1 ms substeps)
  EPS 1 kHz       integer chain (fb lag diff 1011/567 clamp 1024 ; E = 4 sp - r26 ; Kp 960 ; taper 254 ;
                  output lag 992/507 ; gain 5346 ; clamp 3072) -- NULL = r26 forced 0 (V293), INVERTED = -r26
  sensor          x = round(8 (th[n] - th[n-3]) / 3 ms), clip +-12000 ; 0x18F = x at 100 Hz (optionally 1 frame stale)
  fork 100 Hz     StarPilot generic torque path, V294 config: kp 0.9, ki 0.3, LAF 14, friction 0.011/0.30, FF = setpoint/LAF,
                  measurement from 0x14A angle (0.1 deg LSB), controls->0xE4 13 ms, wire = u * 4096, idx = |wire| / 16.125736
  tap 50 Hz       T quantised sign * (|T| >> 3) << 3
Predictor (as the V293 flight read does): steady-state FF surface of idx x 254/256, ZOH onto the tap, best lag scan,
optionally with a FF GAIN ERROR eps (the fade/taper model error the record carries: V293 resid 22 counts, R2 0.986).
Estimators of the trim slope beta (T counts per deg/s^2):
  E1  as specified   OLS residual ~ 1 + R,  R = -d/dt LPF_2Hz(0x18F rate)
  E2  nuisance       OLS residual ~ 1 + R + FFpred + dFFpred/dt
  E3  matched        like E2 but R passed through the 5 Hz output-lag replica
"""
import math, sys, time
import numpy as np

T_PER_U = 2625.4
MAPX = (0, 12, 20, 24, 32, 64, 96, 128, 160, 240)
MAPY = (0, 52, 86, 103, 138, 275, 413, 550, 688, 1032)


def lerp(i):
    return int(np.interp(i, MAPX, MAPY)) if i < 240 else 1032   # (map LERP; floor semantics are fine here)


def ff_T(i):
    """steady-state delivered T at idx i, fb = 0 (march the integer output lag to its cold-start fixed point)."""
    sp = lerp(i)
    P = max(-15360, min(15360, ((sp << 2) * 960) >> 8))
    S = (254 * P) >> 8
    o = 0
    for _ in range(4000):
        o2 = ((992 * o) >> 10) + ((S * 507) >> 10)
        if o2 == o:
            break
        o = o2
    y = (o + o) >> 5
    return max(-3072, min(3072, (y * 5346) >> 15))


FF_TABLE = np.array([ff_T(i) for i in range(241)], float)


def G_la(v, sR=16.33, L=2.83, sF=-7.0e-4):
    return v ** 2 * math.radians(1.0) / sR / (1 - sF * v ** 2) / L


def lsf(v):
    return (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 0.3)) ** 2


def simulate(v, mode, seed, dur=25.0, J=8e-5, b=6e-4, k=0.011, F=0.0, ref_amp_deg=8.0, dist=0.004, stale=0, d_act=2):
    rng = np.random.default_rng(seed)
    n = int(dur * 1000)
    # reference: desired lateral accel from a random smooth angle path (sum of sines 0.05-0.8 Hz) + a filtered step train
    t = np.arange(n) * 1e-3
    ang = np.zeros(n)
    for _ in range(6):
        f = rng.uniform(0.05, 0.8); ph = rng.uniform(0, 2 * math.pi)
        ang += rng.uniform(0.3, 1.0) * np.sin(2 * math.pi * f * t + ph)
    ang *= ref_amp_deg / max(1e-9, np.abs(ang).max())
    ref = G_la(v) * ang
    # road disturbance torque (OU, 0.3 s)
    dseq = np.zeros(n); a = math.exp(-1e-3 / 0.3); z = 0.0
    wn = rng.standard_normal(n)
    for i in range(n):
        z = a * z + math.sqrt(1 - a * a) * wn[i]; dseq[i] = dist * z
    ls = lsf(v); kp, ki, laf, fric, thr = 0.9, 0.3, 14.0, 0.011, 0.30
    Ga = G_la(v)
    th = 0.0; w = 0.0
    hist = [0.0] * 4
    s_fb = 0; o = 0
    Tq = [0] * (d_act + 1)
    I = 0.0; wire = 0; wire_pending = []
    rec_T, rec_x, rec_th, rec_wire = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    for i in range(n):
        # ---- fork at 100 Hz (frame at i % 10 == 0; computes at +3 ms; wire reaches the EPS at +16 ms) ----
        if i % 10 == 3:
            th_meas = round(rec_th[i - 3] * 10) / 10.0
            meas = Ga * th_meas
            e = ref[i] - meas
            el = e * (1 + ls / kp)
            I += ki * el * 0.01
            fr = fric * max(-1.0, min(1.0, el / thr))
            u = (kp * el + I + ref[i]) / laf + fr
            u = max(-1.0, min(1.0, u))
            wire_pending.append((i + 13, int(round(u * 4096))))
        while wire_pending and wire_pending[0][0] <= i:
            wire = wire_pending.pop(0)[1]
        idx = min(240, int(abs(wire) / 16.125736))
        sp = lerp(idx) * (1 if wire >= 0 else -1)
        # ---- sensor + EPS integer chain ----
        hist.append(th); hist.pop(0)
        x = int(round(8 * (hist[-1] - hist[-4]) / 0.003))
        x = max(-12000, min(12000, x))
        s_new = ((1011 * s_fb) >> 10) + ((567 * x) >> 10)
        r26 = max(-1024, min(1024, s_new - s_fb)); s_fb = s_new
        if mode == "null":
            r26 = 0
        elif mode == "inv":
            r26 = -r26
        E = (sp << 2) - r26
        P = max(-15360, min(15360, (E * 960) >> 8))
        S = max(-15360, min(15360, (254 * P) >> 8))
        o2 = ((992 * o) >> 10) + ((S * 507) >> 10)
        y = (o + o2) >> 5; o = o2
        T = max(-3072, min(3072, (y * 5346) >> 15))
        Tq.append(T); Tm = Tq.pop(0)
        # ---- plant, 10 substeps ----
        uu = Tm / T_PER_U + dseq[i]
        for _ in range(10):
            acc = (uu - b * w - k * th - F * math.tanh(w / 1.0)) / J
            w += acc * 1e-4; th += w * 1e-4
        rec_T[i], rec_x[i], rec_th[i], rec_wire[i] = T, x, th, wire
    # ---- the wire, as logged ----
    fr100 = np.arange(0, n, 10)
    x18f = rec_x[np.maximum(fr100 - 10 * stale, 0)]
    wire100 = rec_wire[fr100]
    tap_i = np.arange(0, n, 20)
    Tt = rec_T[tap_i]
    tap = np.sign(Tt) * (np.abs(Tt).astype(int) >> 3) * 8.0
    return dict(x18f=x18f, wire100=wire100, tap=tap, tap_i=tap_i, fr100=fr100, T=rec_T, x=rec_x, th=rec_th)


def lp1(xs, fc, fs):
    a = math.exp(-2 * math.pi * fc / fs); y = np.zeros_like(xs); s = 0.0
    for i, v in enumerate(xs):
        s = a * s + (1 - a) * v; y[i] = s
    return y


def estimators(sim, eps=0.0, lag_scan=range(-4, 13), settle_s=3.0):
    fs = 100.0
    wire = sim["wire100"]
    idx = np.minimum(240, (np.abs(wire) / 16.125736).astype(int))
    ffp = np.sign(wire) * FF_TABLE[idx] * (1 + eps)            # predictor (with a gain error eps)
    rate = sim["x18f"] / 8.0                                     # deg/s
    lr = lp1(rate, -math.log(1011 / 1024) / (2 * math.pi * 1e-3), fs)   # 2.03 Hz
    R = -np.gradient(lr) * fs                                    # -alpha through the 2 Hz pole, deg/s^2
    Rm = lp1(R, 5.05, fs)                                        # + the output-lag replica
    dff = np.gradient(ffp) * fs
    tap = sim["tap"]; ti = sim["tap_i"] // 10                   # tap frame -> 100 Hz frame index
    best = None
    for lag in lag_scan:                                         # the flight read's best-lag alignment of the predictor
        j = np.clip(ti - lag, 0, len(ffp) - 1)
        res = tap - ffp[j]
        ok = ti > settle_s * fs
        v = np.var(res[ok])
        if best is None or v < best[0]:
            best = (v, lag, j, ok)
    _, lag, j, ok = best
    res = tap - ffp[j]
    out = {"lag_frames": lag, "resid_rms": float(np.sqrt(np.mean(res[ok] ** 2)))}
    jr = np.clip(ti, 0, len(R) - 1)
    def ols(cols):
        X = np.column_stack([np.ones(ok.sum())] + [c[ok] for c in cols])
        beta, *_ = np.linalg.lstsq(X, res[ok], rcond=None)
        e = res[ok] - X @ beta
        # HAC-free but conservative: SE with an effective-N from the regressor's lag-1 autocorrelation
        r1 = np.corrcoef(cols[0][ok][1:], cols[0][ok][:-1])[0, 1]
        neff = ok.sum() * (1 - r1) / (1 + r1)
        XtX = np.linalg.inv(X.T @ X)
        se = math.sqrt(np.var(e) * XtX[1, 1] * ok.sum() / max(neff, 5))
        return beta[1], se
    out["E1"] = ols([R[jr]])
    out["E2"] = ols([R[jr], ffp[j], dff[j]])
    out["E3"] = ols([Rm[jr], ffp[j], dff[j]])
    out["R_rms"] = float(np.std(R[jr][ok])); out["rate_rms"] = float(np.std(rate[jr][ok]))
    return out


if __name__ == "__main__":
    t0 = time.time()
    # quick self-check of the embedded chain against the golden model (trim part at idx 0)
    sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/model")
    import eps_lkas_chain_model as M
    from dataclasses import replace
    V294 = replace(M.Calibration(), fb_clamp=1024, fb_lag_a=1011, fb_lag_b=567, kp_y=(960,) * 5, kd_y=(0,) * 4,
                   pid_d_clamp=0, fb_op="diff", e_shift=2)
    st = M.EpsState(); s_fb = 0; o = 0; mism = 0
    rng = np.random.default_rng(0)
    for i in range(20000):
        x = int(rng.integers(-3000, 3000)) if i % 7 else int(500 * math.sin(i / 90))
        idx = int(rng.integers(0, 241)) if i % 500 == 0 else (idx if i else 0)
        sp = M.lkas_rate_lerp(V294.assist_map_x, V294.assist_map_y, idx)
        fb = M.lkas_fb_lag(x, st, V294); Tg = M.lkas_rate_pid_tick(sp, fb, idx, st, V294)["T"]
        s_new = ((1011 * s_fb) >> 10) + ((567 * x) >> 10); r26 = max(-1024, min(1024, s_new - s_fb)); s_fb = s_new
        P = max(-15360, min(15360, (((sp << 2) - r26) * 960) >> 8)); S = max(-15360, min(15360, (254 * P) >> 8))
        o2 = ((992 * o) >> 10) + ((S * 507) >> 10); y = (o + o2) >> 5; o = o2
        T = max(-3072, min(3072, (y * 5346) >> 15))
        mism += (T != Tg)
    print(f"embedded integer chain vs golden model, 20000 ticks: mismatches {mism}")
    print(f"FF table: idx 10 {FF_TABLE[10]:.0f}, 60 {FF_TABLE[60]:.0f}, 120 {FF_TABLE[120]:.0f}, 240 {FF_TABLE[240]:.0f}")

    N_EP = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    for (v, kk, amp, dur) in ((19.0, 0.0111, 8.0, 20.0), (8.0, 0.0052, 25.0, 20.0), (19.0, 0.0111, 3.0, 20.0)):
        print(f"\n=== v {v} m/s, k {kk}, reference amplitude {amp} deg, episode {dur} s, {N_EP} episodes per arm ===")
        sims = {(mode, ep): simulate(v, mode, seed=1000 * ep + 7, dur=dur, k=kk, ref_amp_deg=amp)
                for mode in ("live", "null", "inv") for ep in range(N_EP)}
        for eps in (0.0, +0.05, -0.05):
            summ = {}
            for mode in ("live", "null", "inv"):
                vals = {"E1": [], "E2": [], "E3": []}; rr = []; rs = []; lg = []
                for ep in range(N_EP):
                    sim = sims[(mode, ep)]
                    o_ = estimators(sim, eps=eps)
                    for e_ in vals: vals[e_].append(o_[e_])
                    rr.append(o_["rate_rms"]); rs.append(o_["resid_rms"]); lg.append(o_["lag_frames"])
                summ[mode] = vals
                line = "  ".join(f"{e_} {np.mean([a for a, _ in vals[e_]]):+.3f}+-{np.std([a for a, _ in vals[e_]]):.3f} (se~{np.mean([s for _, s in vals[e_]]):.3f})" for e_ in vals)
                print(f"  eps {eps:+.2f} {mode:4s}: {line} | rate rms {np.mean(rr):.1f} deg/s, resid rms {np.mean(rs):.1f}, lag {np.median(lg):.0f} fr")
            # separability: fraction of episodes classified correctly by a fixed rule: beta > +0.105 live, |beta| < 0.105 null, < -0.105 inverted
            for e_ in ("E1", "E2", "E3"):
                cl = lambda b_: "live" if b_ > 0.105 else ("inv" if b_ < -0.105 else "null")
                acc = {m: np.mean([cl(a) == m for a, _ in summ[m][e_]]) for m in summ}
                print(f"      {e_}: correct classification (half-slope thresholds +-0.105): live {acc['live']:.2f} null {acc['null']:.2f} inv {acc['inv']:.2f}")
    print(f"\n[{time.time()-t0:.0f} s]  expected live slope from the chain (below the pole): +0.2097 T counts per deg/s^2")
