# -*- coding: utf-8 -*-
r"""m1_loop_identity.py -- M1 (b) LOOP IDENTITY and (c) the D-SIGN DISPUTE, route 79 (V298 first flight).

ANALYSIS ONLY.  Reads the kit's wire cache and the BUILT V298 image (cells, Python LE reads); writes JSON + text under
_scratch/out/r79/m1/.  No rlog read, nothing sent, nothing flashed.  Independent of the drive-read's code: its own
loader (raw cache streams, ZOH by np.searchsorted, NO de-jitter grid), its own image reads, its own lane arithmetic.

THE LANE (design C3-rev2 §1.4 + lane_mirror_v295.lane_tick output path; every cell read from the V298 image):
  E   = (gp-0x69ae << 2) - r26,  gp-0x69ae = clamp(-4 raw),  r26 = 8 th[n] + 8 th[n-1],  th = gp-0x6a00 = 10*ang
      => E = -16 * e_w  with  e_w = raw + 10*ang = -10 (theta_sp - theta)          [wire counts, 0.1 deg]
  E'  = (E G(v)) >> 8 (cave GB-P walk, rows read at the relinked pointer 0xC4C1E)
  P   = (E' 112) >> 8 ; I += (((E' >> 5) 40) >> 3) unless frozen ; D = (48 abe) >> 3, abe = gp-0x6abe ~ -4.712 w18
  S   = (I >> 7) + P + D ; Sf = (S f) >> 8 ; clamp SCL ; output lag (oa, ob) ; x ramp >> 15 ; x (-fwd) >> 15 = T
  tap = 0x1AB field LSB = T/8 (sign +sign(T)).
  => tap ~= k [ 0.02734 G e_w + 28.27 w18 + I-term ]  with k = kout/8 > 0:  c_D > 0 = D OPPOSES motion (design).

THE D TEST THAT NEEDS NO LAG MODEL (method F, the two-input FRF ratio):
  inputs raw and th (= 10 ang), output tap.  tap = L(w) [ (c_P + c_I/jw)(raw + th) + (c_D/10) jw th ]
  R(w) = H_th / H_raw = 1 + jw tau / (1 - j kappa / w),   tau = c_D / (10 c_P) [s],  kappa = c_I / c_P [1/s]
  L (lag pole, transport, CAN/USB timing, the tap's 50 Hz hold) CANCELS.  A relative delay delta of the 0x14A stream
  vs the 0xE4 stream multiplies R by exp(-jw delta): it shifts arg R but NOT |R|.  So |R| measures |tau| free of
  any timing; arg R gives sign(tau) provided |delta| << |tau|.  Design tau = 103.4/G s (47-185 ms).
METHOD T (time domain): tap band-passed 2-5 Hz regressed on [e_w, w18, Sum e_w] each through the image's output-lag
  pole, common latency scanned; and the same at 0.3-3 Hz (the drive-read's literal band).
METHOD W (windowed replay): the lane above, vectorised at 1 kHz over hands-off settled runs, the I re-anchored by one
  free offset per 10 s window; D gain scanned {+1, 0, -1, free}.  Also the CONTINUOUS replay (I from 0 at engage,
  zero free parameters) = the drive-read's R2 claim, and an exact per-tick integer loop on one 10 s window to
  validate the vectorised chain.
"""
import json
import struct
import time
from pathlib import Path

import numpy as np
from scipy import signal

T0 = time.time()
KIT = Path(__file__).resolve().parents[4]
C = KIT / "analysis-2020accord" / "_scratch" / "cache" / "v280"
OUT = KIT / "_scratch" / "out" / "r79" / "m1"
OUT.mkdir(parents=True, exist_ok=True)
IMG = next((Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")).glob("_v298_*plain_image.bin"))
img = IMG.read_bytes()
LOG = []
RES = {}


def pr(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


u16 = lambda a: struct.unpack_from("<H", img, a)[0]      # noqa: E731
i16 = lambda a: struct.unpack_from("<h", img, a)[0]      # noqa: E731
u32 = lambda a: struct.unpack_from("<I", img, a)[0]      # noqa: E731
SEL = 7


def rec(bank, n):
    p = u32(bank + 4 * SEL)
    assert u16(p) == n, (hex(bank), u16(p), n)
    return (np.array([u16(p + 2 + 2 * i) for i in range(n)]), np.array([u16(p + 2 + 2 * n + 2 * i) for i in range(n)]))


CAL = dict(Ki=u16(0xC63E6), ICL=u16(0xC61BA), DCL=u16(0xC61B6), PCL=u16(0xC61BC), SCL=u16(0xC61BE), oa=i16(0xC63EC),
           ob=u16(0xC63EE), fwd=i16(0xC6CD0), OCL=u16(0xC61B4), a=i16(0xC63E8), b=u16(0xC63EA), C=u16(0xC62E6),
           DB=u16(0xC62E4), kp=[u16(0xE5384 + 2 * i) for i in range(5)], kd=[u16(0xE5126 + 2 * i) for i in range(4)],
           ramp=[u16(0xC63F6 + 2 * i) for i in range(4)], fver=img[0x13100:0x1310E].decode("latin1"))
FADE = dict(A=rec(0xCBC34, 6), B=rec(0xCBBC4, 6), A2=rec(0xCBB54, 6), B2=rec(0xCBAE4, 6))
tp_ = u32(0xC4C1E)
ROWS = []
while True:
    X_, G_, S_ = struct.unpack_from("<HHh", img, tp_)
    ROWS.append((X_, G_, S_))
    if X_ == 0xFFFF:
        break
    tp_ += 6
RX = np.array([r[0] for r in ROWS], np.int64)
RG = np.array([r[1] for r in ROWS], np.int64)
RS = np.array([r[2] for r in ROWS], np.int64)
pr("IMAGE", IMG.name[:60], "| F181", CAL["fver"], "| cells", {k: v for k, v in CAL.items() if k != "fver"})
pr("  fadeA2", FADE["A2"], "fadeB2", FADE["B2"], "(fadeB", FADE["B"], ")")
pr("  GB-P rows @0x%X" % u32(0xC4C1E), ROWS)
RES["image"] = dict(name=IMG.name, cal={k: (v if not isinstance(v, np.ndarray) else v.tolist()) for k, v in CAL.items()},
                    rows=ROWS, fadeB2_equals_fadeB=bool(np.all(FADE["B2"][0] == FADE["B"][0]) and np.all(FADE["B2"][1] == FADE["B"][1])))


def walkG(v):
    """the cave's G walk (nl_cave.walk_G semantics): v <= X0 -> G0 ; else segment i with X_i < v <= X_{i+1}."""
    v = np.asarray(v, np.int64) & 0xFFFF
    i = np.clip(np.searchsorted(RX, v, side="left") - 1, 0, len(RX) - 2)
    g = RG[i] + (((v - RX[i]) * RS[i]) >> 12)
    return np.where(v <= RX[0], RG[0], g)


def lerpv(XY, u):
    X, Y = (np.asarray(z, np.int64) for z in XY)
    u = np.asarray(u, np.int64)
    k = np.clip(np.searchsorted(X, u, side="right"), 1, len(X) - 1)
    num = (Y[k] - Y[k - 1]) * (u - X[k - 1])
    den = X[k] - X[k - 1]
    q = np.abs(num) // np.abs(den)
    mid = Y[k - 1] + np.where((num < 0) != (den < 0), -q, q)
    return np.where(u <= X[0], Y[0], np.where(u >= X[-1], Y[-1], mid))


# the linear chain's DC gain (T per S unit, f at rest) -- integer-marched on a constant input
fA0 = int(lerpv(FADE["A2"], [0])[0])
f0 = ((fA0 * int(lerpv(FADE["B2"], [0])[0])) & 0xFFFF) >> 8
o = 0
for _ in range(3000):
    on = ((10000 * CAL["ob"]) >> 10) + ((CAL["oa"] * o) >> 10)
    y = (o + on) >> 5
    o = on
LAGDC = y / 10000.0
KOUT = (f0 / 256.0) * LAGDC * CAL["fwd"] / 32768.0          # T per S unit
K = KOUT / 8.0                                               # tap LSB per S unit
CD_DESIGN = 6.0 * (32768.0 / (48 * 1159) * 8.0) * K          # (48 abe)>>3, abe = -(8 w18) 32768/(48*1159)
pr("chain: f0 %d lagDC %.4f kout %.5f T/S  => tap per S %.6f ; design c_D %.4f tap/(deg/s) ; c_P = %.3e x G per wire count"
   % (f0, LAGDC, KOUT, K, CD_DESIGN, 16 * 112 / 65536 * K))
RES["chain"] = dict(f0=f0, lagdc=LAGDC, kout=KOUT, k_tap_per_S=K, cD_design=CD_DESIGN, cP_per_G=16 * 112 / 65536 * K)

# ------------------------------------------------------------------------------------------------ LOAD (own loader)
W = dict(np.load(C / "r79_a1f5d2_al.npz"))
t14, ANG = W["t14"], W["ang"]
t18, RATE_RAW, BARR, SCA = W["t18"], W["rate"], W["tq"] * 1.024, W["sca"].astype(float)
te4, RAW, REQ = W["te4"], W["cmd"], W["req"].astype(float)
tcs, VEGO = W["tcs"], W["vego"]
t1ab = W["t1ab"]
fld = ((W["b0"].astype(int) & 3) << 8) | W["b1"].astype(int)
TAP = np.where(fld >= 512, -1.0, 1.0) * (fld & 511)


def zoh(ts, x, t):
    j = np.searchsorted(ts, t, side="right") - 1
    return np.asarray(x)[np.clip(j, 0, len(x) - 1)]


# sanity: the rate scale (raw/8 deg/s) and sign vs d(ang)/dt
tt = np.arange(200.0, 1200.0, 0.01)
w18 = -zoh(t18, RATE_RAW, tt) / 8.0
dang = np.gradient(zoh(t14, ANG, tt), 0.01)
bb, aa = signal.butter(2, 2.0 / 50.0)
cw = np.polyfit(signal.filtfilt(bb, aa, dang), signal.filtfilt(bb, aa, w18), 1)[0]
pr("rate check: slope of w18 (= -raw18/8) on d(ang)/dt (2 Hz LP) = %.3f (1.0 = same sign and scale)" % cw)
RES["rate_scale_check"] = float(cw)

# ------------------------------------------------------------------------------------------------ 100 Hz GRID
tg = np.arange(te4[0] + 1.0, te4[-1] - 1.0, 0.01)
g = dict(t=tg, ang=zoh(t14, ANG, tg), raw=zoh(te4, RAW, tg), req=zoh(te4, REQ, tg) > 0.5,
         sca=zoh(t18, SCA, tg) > 0.5, bar=zoh(t18, BARR, tg), w18=-zoh(t18, RATE_RAW, tg) / 8.0,
         v=zoh(tcs, VEGO, tg), tap=zoh(t1ab, TAP, tg))
eng = g["req"] & g["sca"]
rise_t = np.where(np.r_[eng[0], eng[1:] & ~eng[:-1]], tg, -np.inf)
tse = tg - np.maximum.accumulate(rise_t)
g["eng"] = eng
g["ew"] = g["raw"] + 10.0 * g["ang"]                         # = -10 (theta_sp - theta)
g["th"] = 10.0 * g["ang"]
HO = 500.0
base = eng & (tse >= 1.2) & (np.abs(g["bar"]) < HO) & (np.abs(g["tap"]) < 0.95 * 2461 / 8)
BANDS = (("<5", 0.0, 5.0), ("5-8", 5.0, 8.0), ("8-10", 8.0, 10.0), ("10-12.5", 10.0, 12.5), ("12.5-15", 12.5, 15.0),
         ("15-22", 15.0, 22.0), (">22", 22.0, 99.0))
Gband = {}
for nm, lo, hi in BANDS:
    m = base & (g["v"] >= lo) & (g["v"] < hi)
    Gband[nm] = float(np.mean(walkG(np.clip(np.round(g["v"][m] * 230.4), 0, 12000)))) if m.any() else np.nan


def runs(mask, minlen):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


# ================================================================================================ METHOD F
NSEG = 400                                                    # 4 s, df 0.25 Hz, Hann, 50 % overlap
win = np.hanning(NSEG)
fr = np.fft.rfftfreq(NSEG, 0.01)
segs = []                                                     # (band, X1, X2, Y) spectra per segment
for a, b in runs(base, NSEG):
    for s0 in range(a, b - NSEG + 1, NSEG // 2):
        sl = slice(s0, s0 + NSEG)
        vm = g["v"][sl].mean()
        band = next((nm for nm, lo, hi in BANDS if lo <= vm < hi), None)
        sp = []
        for key in ("raw", "th", "tap"):
            z = signal.detrend(g[key][sl], type="linear")
            sp.append(np.fft.rfft(z * win))
        segs.append((band, vm, sp[0], sp[1], sp[2]))
pr("METHOD F: %d hands-off settled 4 s segments" % len(segs))


def frf(sel):
    X1 = np.array([s[2] for s in sel])
    X2 = np.array([s[3] for s in sel])
    Y = np.array([s[4] for s in sel])
    S11 = np.mean(np.abs(X1) ** 2, 0)
    S22 = np.mean(np.abs(X2) ** 2, 0)
    S12 = np.mean(np.conj(X1) * X2, 0)
    S1y = np.mean(np.conj(X1) * Y, 0)
    S2y = np.mean(np.conj(X2) * Y, 0)
    det = S11 * S22 - np.abs(S12) ** 2
    H1 = (S22 * S1y - S12 * S2y) / det                         # H_raw
    H2 = (S11 * S2y - np.conj(S12) * S1y) / det                # H_th
    Syy = np.mean(np.abs(Y) ** 2, 0)
    coh = np.real(np.conj(H1) * S1y + np.conj(H2) * S2y) / Syy  # multiple coherence
    cond = np.abs(S12) ** 2 / (S11 * S22)
    return H1, H2, coh, cond


FB = (fr >= 0.5) & (fr <= 5.0)
TAUG = np.linspace(-0.40, 0.40, 161)
DELG = np.linspace(-0.04, 0.04, 41)
KAPG = np.linspace(0.0, 8.0, 17)


def fit_R(R, wts):
    """least squares of R(f) = (1 + jw tau/(1 - j kappa/w)) exp(-jw delta) over f in 0.5-5 Hz.  Returns the best
    (tau, delta, kappa), the profile min over (delta,kappa) for tau>0 and tau<0, the delta-free |tau| from |R| alone,
    and tau at delta fixed 0."""
    w = 2 * np.pi * fr[FB]
    Rm = R[FB]
    wt = wts[FB]
    tau = TAUG[:, None, None, None]
    dl = DELG[None, :, None, None]
    kp = KAPG[None, None, :, None]
    ww = w[None, None, None, :]
    model = (1 + 1j * ww * tau / (1 - 1j * kp / ww)) * np.exp(-1j * ww * dl)
    cost = np.sum(wt * np.abs(Rm - model) ** 2, -1)
    i = np.unravel_index(np.argmin(cost), cost.shape)
    prof = cost.min(axis=(1, 2))
    pos, neg = prof[TAUG > 0.005].min(), prof[TAUG < -0.005].min()
    mag = np.sum(wt * (np.abs(Rm) - np.abs(model)) ** 2, -1).min(axis=(1, 2))   # |R| only: delta-free
    taum = abs(TAUG[np.argmin(mag)])
    c0 = cost[:, int(np.argmin(np.abs(DELG))), :].min(axis=1)
    return dict(tau=float(TAUG[i[0]]), delta=float(DELG[i[1]]), kappa=float(KAPG[i[2]]), cost=float(cost[i]),
                cost_pos=float(pos), cost_neg=float(neg), tau_absR=float(taum), tau_delta0=float(TAUG[np.argmin(c0)]))


resF = {}
rng = np.random.default_rng(79)
for nm, lo, hi in BANDS + (("pooled>5", 5.0, 99.0),):
    sel = [s for s in segs if lo <= s[1] < hi]
    if len(sel) < 6:
        resF[nm] = dict(n=len(sel))
        continue
    H1, H2, coh, cond = frf(sel)
    R = H2 / H1
    wts = np.clip(coh, 0, 1) / (1 - np.clip(coh, 0, 0.98))
    ft = fit_R(R, wts)
    boot = []
    for _ in range(40):
        bs = [sel[j] for j in rng.integers(0, len(sel), len(sel))]
        b1, b2, bc, _ = frf(bs)
        bf = fit_R(b2 / b1, np.clip(bc, 0, 1) / (1 - np.clip(bc, 0, 0.98)))
        boot.append((bf["tau"], bf["tau_absR"], bf["delta"], bf["tau_delta0"]))
    boot = np.array(boot)
    Gm = Gband.get(nm, np.nan) if nm in Gband else float(np.nanmean([Gband[k] for k in Gband if k != "<5"]))
    taud = 103.4 / Gm if np.isfinite(Gm) else np.nan
    pick = {f_: int(np.argmin(np.abs(fr - f_))) for f_ in (1.0, 2.0, 3.0, 4.0)}
    cP_lo = np.abs(H1[(fr >= 0.25) & (fr <= 0.75)]).mean()
    resF[nm] = dict(n=len(sel), s=len(sel) * 2.0, G=Gm, tau_design=taud, fit=ft,
                    tau_ci=np.percentile(boot[:, 0], [2.5, 97.5]).tolist(),
                    tau_absR_ci=np.percentile(boot[:, 1], [2.5, 97.5]).tolist(),
                    tau_delta0_ci=np.percentile(boot[:, 3], [2.5, 97.5]).tolist(),
                    delta_ci=np.percentile(boot[:, 2], [2.5, 97.5]).tolist(),
                    frac_boot_tau_pos=float(np.mean(boot[:, 0] > 0)),
                    R={str(f_): (float(np.abs(R[k])), float(np.degrees(np.angle(R[k]))), float(coh[k]), float(cond[k]))
                       for f_, k in pick.items()},
                    Rpred={str(f_): (float(np.abs(1 + 1j * 2 * np.pi * f_ * taud)), float(np.degrees(np.arctan(2 * np.pi * f_ * taud))))
                           for f_ in pick} if np.isfinite(taud) else None,
                    H1_lowf_mag=float(cP_lo))
    r = resF[nm]
    pr("  F %-8s n %3d (%4.0f s) G %6.0f tau_design %+5.3f | fit tau %+6.3f [%+.3f,%+.3f] delta %+5.3f [%+.3f,%+.3f] kappa %.2f"
       " | P(tau>0) %.2f | |tau| from |R| %.3f [%.3f,%.3f] | tau@delta0 %+.3f [%+.3f,%+.3f] | cost+ %.3g cost- %.3g"
       % (nm, r["n"], r["s"], Gm, taud, ft["tau"], *r["tau_ci"], ft["delta"], *r["delta_ci"], ft["kappa"],
          r["frac_boot_tau_pos"], ft["tau_absR"], *r["tau_absR_ci"], ft["tau_delta0"], *r["tau_delta0_ci"], ft["cost_pos"],
          ft["cost_neg"]))
    pr("      R(f) |R| / arg deg / coh / cond:", {k: tuple(round(x, 2) for x in v) for k, v in r["R"].items()},
       " design (delta 0):", {k: tuple(round(x, 2) for x in v) for k, v in (r["Rpred"] or {}).items()})
RES["F"] = resF
pr("[stage F done %.1f s]" % (time.time() - T0))

# ================================================================================================ METHOD T
A100 = (CAL["oa"] / 1024.0) ** 10                             # the output-lag pole sampled at 100 Hz (BELIEF: ZOH input)


def lagp(x):
    return signal.lfilter([1 - A100], [1, -A100], x)


def bp_regress(f_lo, f_hi, lat_list=(0.00, 0.01, 0.02, 0.03, 0.04, 0.05), th_shift=0, nboot=80, use_dang=False):
    """per band: tap_bp ~ cP*L(e_w)_bp + cI*L(Sum e_w dt)_bp + cD*L(w18)_bp ; returns cP, cI/cP, cD and block-boot CI."""
    sos = signal.butter(3, [f_lo, f_hi], btype="band", fs=100.0, output="sos")
    out = {}
    rr = runs(base, 500)                                          # >= 5 s runs
    blocks = []
    for a, b in rr:
        sl = slice(a, b)
        ang_s = np.roll(g["ang"], th_shift)[sl]                   # relative 0x14A timing sensitivity (frames)
        ew = g["raw"][sl] + 10.0 * ang_s
        w_ = np.gradient(ang_s, 0.01) if use_dang else g["w18"][sl]
        Iw = np.cumsum(ew) * 0.01
        Xs = [signal.sosfiltfilt(sos, lagp(z - z.mean())) for z in (ew, Iw, w_)]
        n = b - a
        for s0 in range(0, n - 250 + 1, 250):                     # 2.5 s blocks for the bootstrap
            blocks.append((g["v"][a + s0:a + s0 + 250].mean(), a + s0, [x[s0:s0 + 250] for x in Xs], sl, s0))
    # the tap with a common latency: tap(t + lat) vs regressors(t)
    best = None
    for lat in lat_list:
        Y = signal.sosfiltfilt(sos, np.nan_to_num(zoh(t1ab, TAP, tg + lat)))
        res = {}
        for nm, lo, hi in BANDS + (("pooled>5", 5.0, 99.0),):
            bl = [x for x in blocks if lo <= x[0] < hi]
            if len(bl) < 8:
                res[nm] = None
                continue
            Xm = np.vstack([np.c_[tuple(x[2])] for x in bl])
            Ym = np.concatenate([Y[x[1]:x[1] + 250] for x in bl])
            coef, *_ = np.linalg.lstsq(Xm, Ym, rcond=None)
            r2 = 1 - np.sum((Ym - Xm @ coef) ** 2) / np.sum(Ym ** 2)
            res[nm] = dict(n=len(bl), coef=coef, r2=float(r2), bl=bl, Y=Y)
        sc = res["pooled>5"]["r2"] if res.get("pooled>5") else -9
        if best is None or sc > best[0]:
            best = (sc, lat, res)
    _, lat, res = best
    for nm, r in res.items():
        if r is None:
            out[nm] = None
            continue
        bl, Y = r["bl"], r["Y"]
        bc = []
        for _ in range(nboot):
            idx = rng.integers(0, len(bl), len(bl))
            Xm = np.vstack([np.c_[tuple(bl[j][2])] for j in idx])
            Ym = np.concatenate([Y[bl[j][1]:bl[j][1] + 250] for j in idx])
            bc.append(np.linalg.lstsq(Xm, Ym, rcond=None)[0])
        bc = np.array(bc)
        cP, cI, cD = r["coef"]
        Gm = Gband.get(nm, np.nan) if nm in Gband else np.nan
        out[nm] = dict(n_blocks=r["n"], s=r["n"] * 2.5, r2=r["r2"], cP=float(cP), cIcP=float(cI / cP), cD=float(cD),
                       cD_ci=np.percentile(bc[:, 2], [2.5, 97.5]).tolist(), cP_ci=np.percentile(bc[:, 0], [2.5, 97.5]).tolist(),
                       cP_pred=float(16 * 112 / 65536 * K * Gm) if np.isfinite(Gm) else None,
                       frac_boot_cD_pos=float(np.mean(bc[:, 2] > 0)))
    return dict(lat=lat, bands=out)


resT = {}
for lab, f_lo, f_hi in (("2-5Hz", 2.0, 5.0), ("0.3-3Hz", 0.3, 3.0), ("1-3Hz", 1.0, 3.0)):
    resT[lab] = bp_regress(f_lo, f_hi)
    pr("METHOD T %s (common latency %.2f s, best pooled R2):" % (lab, resT[lab]["lat"]))
    for nm, r in resT[lab]["bands"].items():
        if r:
            pr("  T %-8s %4.0f s R2 %.3f  cP %.3f [%.3f,%.3f] (pred %s)  cI/cP %+.2f /s  cD %+.3f [%+.3f,%+.3f] P(cD>0) %.2f"
               % (nm, r["s"], r["r2"], r["cP"], *r["cP_ci"], ("%.3f" % r["cP_pred"]) if r["cP_pred"] else "-", r["cIcP"],
                  r["cD"], *r["cD_ci"], r["frac_boot_cD_pos"]))
# sensitivity of the 2-5 Hz cD to the relative timing of the 0x14A stream (+-1 frame) with d(ang)/dt as the D regressor
sens = {}
for sh in (-1, 0, 1):
    rs = bp_regress(2.0, 5.0, lat_list=(resT["2-5Hz"]["lat"],), th_shift=sh, nboot=40, use_dang=True)
    sens[sh] = {k: (v["cD"] if v else None) for k, v in rs["bands"].items()}
pr("METHOD T 2-5 Hz cD vs a +-10 ms shift of the 0x14A stream (D regressor d(ang)/dt for the shifted rows):",
   {k: {b: (round(x, 3) if x is not None else None) for b, x in v.items()} for k, v in sens.items()})
resT["sens_th_shift"] = sens
pr("[stage T done %.1f s]" % (time.time() - T0))
RES["T"] = {k: (dict(lat=v["lat"], bands={b: ({kk: vv for kk, vv in r.items()} if r else None) for b, r in v["bands"].items()})
               if isinstance(v, dict) and "lat" in v else v) for k, v in resT.items()}

# ================================================================================================ METHOD W (replay)
RIN, ROUT = CAL["ramp"][3], CAL["ramp"][2]                   # dir-2 arm ramp-in 0xC63FC / ramp-out 0xC63FA (build doc)


def lane_inputs(tk):
    th = np.round(10.0 * zoh(t14, ANG, tk)).astype(np.int64)
    raw = np.round(zoh(te4, RAW, tk)).astype(np.int64)
    sp = np.clip(-4 * raw, -0x4000, 0x4000)
    x = np.round(-zoh(t18, RATE_RAW, tk)).astype(np.int64)                 # gp-0x6a56 = -raw18
    abe = np.round(-x * 32768.0 / (48 * 1159)).astype(np.int64)             # gp-0x6abe (held stand-in)
    vw = np.clip(np.round(zoh(tcs, VEGO, tk) * 230.4), 0, 12000).astype(np.int64)
    tqs = np.round(-zoh(t18, BARR, tk)).astype(np.int64)                   # gp-0x4f60 ~ -bar
    return th, sp, abe, vw, tqs


def lane_memoryless(th, thp, sp, abe, vw, tqs):
    r26 = 8 * th + 8 * thp
    E = (sp << 2) - r26
    Ep = (E * walkG(vw)) >> 8
    P = np.clip((Ep * 112) >> 8, -CAL["PCL"], CAL["PCL"])
    abv = ((abe + 13000) & 0xFFFFFFFF) <= 26000
    D = np.clip((48 * np.where(abv, abe, 0)) >> 3, -CAL["DCL"], CAL["DCL"])
    tqa = np.abs(tqs)
    frz = (tqa > 512) | ((tqa > 300) & ((tqs ^ Ep) < 0))
    inc = np.where(frz, 0, (((Ep >> 5) * CAL["Ki"]) >> 3))
    i682f = np.minimum(np.abs(tqs >> 5), 255)
    f = ((fA0 * lerpv(FADE["B2"], i682f)) & 0xFFFF) >> 8
    bound = (np.abs(th) << np.where(vw <= 2880, 4, 6)) + 1250
    bound = np.where(vw <= 1382, np.minimum(bound, 4096), bound)
    return Ep, P, D, inc, f, frz, bound


def chain(Sf_float, ramp):
    o = signal.lfilter([CAL["ob"] / 1024.0], [1.0, -CAL["oa"] / 1024.0], Sf_float)
    y = (np.r_[0.0, o[:-1]] + o) / 32.0
    return -(y * ramp / 32768.0) * CAL["fwd"] / 32768.0 / 8.0          # tap LSB (continuous)


# ---- exact per-tick integer loop on ONE 10 s window (validation of the vectorised chain)
def exact_window(tk, I0=0):
    th, sp, abe, vw, tqs = lane_inputs(tk)
    thp = np.r_[th[:1], th[:-1]]
    Ep, P, D, inc, f, frz, bound = lane_memoryless(th, thp, sp, abe, vw, tqs)
    I, olag = I0, 0
    icl = (CAL["ICL"] << 10) >> 3
    Tout = np.zeros(len(tk))
    for k in range(len(tk)):                                     # 10 000 ticks, pure Python ints
        ep, fz = int(Ep[k]), bool(frz[k])
        t_ = (I >> 7) if ep >= 0 else -(I >> 7)
        if not fz and t_ < int(bound[k]):
            I = max(-icl, min(icl, I + int(inc[k])))
        S = (I >> 7) + int(P[k]) + int(D[k])
        Sf = (S * int(f[k])) >> 8
        Sc = max(-CAL["SCL"], min(CAL["SCL"], Sf))
        on = ((Sc * CAL["ob"]) >> 10) + ((CAL["oa"] * olag) >> 10)
        y_ = (olag + on) >> 5
        olag = on
        T = (y_ * 0x8000) >> 15
        T = (T * -CAL["fwd"]) >> 15
        Tout[k] = max(-CAL["OCL"], min(CAL["OCL"], T))
    return Tout


def vec_window(tk, I0=0, dgain=1.0):
    th, sp, abe, vw, tqs = lane_inputs(tk)
    thp = np.r_[th[:1], th[:-1]]
    Ep, P, D, inc, f, frz, bound = lane_memoryless(th, thp, sp, abe, vw, tqs)
    I = I0 + np.cumsum(inc)
    viol = np.mean(np.where(Ep >= 0, I >> 7, -(I >> 7)) >= bound)
    Gv = walkG(vw).astype(float)
    Praw = (4.0 * sp * Gv / 256.0) * 112.0 / 256.0
    Pmeas = (-(8.0 * th + 8.0 * thp) * Gv / 256.0) * 112.0 / 256.0
    comps = {k: chain(z * f / 256.0, 0x8000) for k, z in (("P", P.astype(float)), ("D", D.astype(float)),
                                                            ("Praw", Praw), ("Pmeas", Pmeas),
                                                            ("I", (I >> 7).astype(float)), ("one", np.ones(len(tk)) / 128.0))}
    return comps, viol


# ---- windows: hands-off settled engaged runs >= 10 s, cut into 10 s windows; sample the tap at its native instants
W10 = []
WL = 500                                                      # 5 s windows (100 Hz samples)
for a, b in runs(base, WL):
    for s0 in range(a, b - WL + 1, WL):
        W10.append((tg[s0], g["v"][s0:s0 + WL].mean()))
pr("METHOD W: %d hands-off settled 5 s windows" % len(W10))
# validation: exact integer loop vs the vectorised chain on THREE 5 s windows (I0 = 0): mid-speed with the least
# A3-bound binding, the most-binding window, and the fastest window.  (3 x 5000 ticks; no route-length loop.)
def _viol(t0w):
    return vec_window(t0w + np.arange(WL * 10) / 1000.0)[1]
VV = [(t0w, vm, _viol(t0w)) for t0w, vm in W10]
cands = [min(VV, key=lambda z: (z[2] > 0.0, abs(z[1] - 13.0))), max(VV, key=lambda z: z[2]), max(VV, key=lambda z: z[1])]
RES["W_validation"] = []
for t0w, vm, vi in cands:
    tkv = t0w + np.arange(WL * 10) / 1000.0
    t_a = time.time()
    Tex = exact_window(tkv)
    t_ex = time.time() - t_a
    cv, _ = vec_window(tkv)
    Tvec = (cv["P"] + cv["D"] + cv["I"]) * 8.0
    dT = Tvec - Tex
    RES["W_validation"].append(dict(t0=float(t0w), v=float(vm), bound_viol=float(vi), max_abs_dT=float(np.max(np.abs(dT))),
                                    rms_dT=float(np.sqrt(np.mean(dT ** 2))), rms_T=float(np.sqrt(np.mean(Tex ** 2))), loop_s=t_ex))
    pr("  validation t0 %.1f v %.1f A3-viol %.3f: exact loop %.3f s; vectorised - exact T: max |d| %.1f T, rms %.2f T (rms T %.1f)"
       % (t0w, vm, vi, t_ex, np.max(np.abs(dT)), np.sqrt(np.mean(dT ** 2)), np.sqrt(np.mean(Tex ** 2))))

LATS = (0.0, 0.01, 0.02, 0.03, 0.04)
WIN = []
for t0w, vm in W10:
    tk = t0w + np.arange(WL * 10) / 1000.0
    comps, viol = vec_window(tk)
    m = (t1ab >= t0w + 0.1) & (t1ab < t0w + WL / 100.0 - 0.05)
    WIN.append(dict(t0=t0w, v=vm, tk=tk, comps=comps, viol=viol, ti=t1ab[m], y=TAP[m]))


def samp(win_, key, lat):
    return np.interp(win_["ti"] - lat, win_["tk"], win_["comps"][key])


def fit_windows(sel, lat, mode):
    """mode 'fixed': tap = P + d*D + I + I0_w*one (d in {1,0,-1}); 'free': tap = p P + d D + i I + I0_w one."""
    ys, cols, offs = [], [], []
    for j, w_ in enumerate(sel):
        ys.append(w_["y"])
        cols.append(np.c_[samp(w_, "P", lat), samp(w_, "D", lat), samp(w_, "I", lat), samp(w_, "Praw", lat),
                          samp(w_, "Pmeas", lat)])
        offs.append(samp(w_, "one", lat))
    y = np.concatenate(ys)
    Xc = np.vstack(cols)
    nW = len(sel)
    O = np.zeros((len(y), nW))
    r0 = 0
    for j, o_ in enumerate(offs):
        O[r0:r0 + len(o_), j] = o_
        r0 += len(o_)
    out = {}
    for d in (1.0, 0.0, -1.0):
        z = y - Xc[:, 0] - d * Xc[:, 1] - Xc[:, 2]
        c0, *_ = np.linalg.lstsq(O, z, rcond=None)
        out["d%+.0f" % d] = float(1 - np.sum((z - O @ c0) ** 2) / np.sum((y - y.mean()) ** 2))
    M = np.c_[Xc[:, :3], O]
    cf, *_ = np.linalg.lstsq(M, y, rcond=None)
    out["free"] = dict(p=float(cf[0]), d=float(cf[1]), i=float(cf[2]),
                       r2=float(1 - np.sum((y - M @ cf) ** 2) / np.sum((y - y.mean()) ** 2)))
    M2 = np.c_[Xc[:, 3:5], Xc[:, 1:3], O]
    c2, *_ = np.linalg.lstsq(M2, y, rcond=None)
    out["split"] = dict(a_raw=float(c2[0]), b_meas=float(c2[1]), ratio=float(-c2[1] / c2[0]) if c2[0] else None)
    return out


resW = {}
bestlat = None
for lat in LATS:
    fw = fit_windows(WIN, lat, "free")
    if bestlat is None or fw["free"]["r2"] > bestlat[0]:
        bestlat = (fw["free"]["r2"], lat)
LAT = bestlat[1]
for nm, lo, hi in BANDS + (("pooled>5", 5.0, 99.0), ("all", 0.0, 99.0)):
    sel = [w_ for w_ in WIN if lo <= w_["v"] < hi]
    if len(sel) < 2:
        continue
    fw = fit_windows(sel, LAT, "free")
    bs = []
    for _ in range(40):
        bsel = [sel[j] for j in rng.integers(0, len(sel), len(sel))]
        bf = fit_windows(bsel, LAT, "free")
        bs.append((bf["free"]["p"], bf["free"]["d"], bf["free"]["i"], bf["split"]["ratio"] or np.nan))
    bs = np.array(bs)
    fw["free"]["p_ci"] = np.percentile(bs[:, 0], [2.5, 97.5]).tolist()
    fw["free"]["d_ci"] = np.percentile(bs[:, 1], [2.5, 97.5]).tolist()
    fw["free"]["i_ci"] = np.percentile(bs[:, 2], [2.5, 97.5]).tolist()
    fw["split"]["ratio_ci"] = np.nanpercentile(bs[:, 3], [2.5, 97.5]).tolist()
    Gm = Gband.get(nm, np.nan)
    fw["dtap_dErr_per_deg"] = float(-10 * fw["free"]["p"] * 16 * 112 / 65536 * K * Gm) if np.isfinite(Gm) else None
    fw["n"] = len(sel)
    fw["viol_bound_mean"] = float(np.mean([w_["viol"] for w_ in sel]))
    resW[nm] = fw
    pr("  W %-8s %2d win  R2 (I re-anchored per 5 s): D=+1 %.3f  D=0 %.3f  D=-1 %.3f | free p %.2f [%.2f,%.2f] d %+.2f [%+.2f,%+.2f]"
       " i %.2f [%.2f,%.2f] R2 %.3f | c_meas/c_raw %+.2f [%+.2f,%+.2f] | dtap/d(sp-th) %s /deg | A3 viol(I0=0) %.3f"
       % (nm, len(sel), fw["d+1"], fw["d+0"], fw["d-1"], fw["free"]["p"], *fw["free"]["p_ci"], fw["free"]["d"],
          *fw["free"]["d_ci"], fw["free"]["i"], *fw["free"]["i_ci"], fw["free"]["r2"], fw["split"]["ratio"],
          *fw["split"]["ratio_ci"], ("%+.2f" % fw["dtap_dErr_per_deg"]) if fw["dtap_dErr_per_deg"] else "-",
          fw["viol_bound_mean"]))
pr("  (common latency %.2f s chosen by the pooled free-fit R2; d is the D gain relative to the image's (48 abe)>>3)" % LAT)
RES["W"] = dict(lat=LAT, bands=resW)
pr("[stage W done %.1f s]" % (time.time() - T0))

# ---- CONTINUOUS replay (zero free parameters): I from 0 at each request rising edge, ramp from the dir-2 cells
reqg = g["req"]
ep_runs = runs(eng, 200)
yT, yP, vv, hh, iR, bd = [], [], [], [], [], []
for a, b in ep_runs:
    t_a0, t_b0 = tg[a], tg[b - 1]
    tk = np.arange(t_a0, t_b0, 0.001)
    th, sp, abe, vw, tqs = lane_inputs(tk)
    thp = np.r_[th[:1], th[:-1]]
    Ep, P, D, inc, f, frz, bound = lane_memoryless(th, thp, sp, abe, vw, tqs)
    ramp = np.minimum(0x8000, RIN * np.arange(1, len(tk) + 1))
    inc = np.where(ramp >= 0x8000, inc, 0)
    I = np.cumsum(inc)
    I = np.clip(I, -(CAL["ICL"] << 7), CAL["ICL"] << 7)
    S = (I >> 7) + P + D
    Tt = chain(S * f / 256.0, ramp)
    m = (t1ab >= t_a0 + 1.2) & (t1ab < t_b0)
    ti = t1ab[m]
    hb = zoh(tg, np.abs(g["bar"]), ti) < HO
    yT.append(TAP[m])
    yP.append(np.interp(ti - LAT, tk, Tt))
    jj = np.clip(np.searchsorted(tk, ti - LAT) , 0, len(tk) - 1)
    iR.append((I >> 7)[jj].astype(float))
    bd.append(np.where(Ep[jj] >= 0, 1.0, -1.0) * bound[jj])
    vv.append(zoh(tcs, VEGO, ti))
    hh.append(hb)
yT, yP, vv, hh, iR, bd = (np.concatenate(z) for z in (yT, yP, vv, hh, iR, bd))
Iimp = iR - (yT - yP) / K               # chain(): tap = -K S, so S_real - S_rep = -(tap_real - tap_rep)/K (P, D shared)
resC = {}
for nm, lo, hi in BANDS + (("all", 0.0, 99.0),):
    m = hh & (vv >= lo) & (vv < hi)
    if m.sum() < 100:
        continue
    y_, p_ = yT[m], yP[m]
    gfit = float(np.sum(y_ * p_) / np.sum(p_ * p_))
    resC[nm] = dict(n=int(m.sum()), r2=float(1 - np.sum((y_ - p_) ** 2) / np.sum((y_ - y_.mean()) ** 2)), gain=gfit,
                    rms_tap=float(np.std(y_)), rms_err=float(np.std(y_ - p_)), mean_err=float(np.mean(y_ - p_)),
                    I_rep_med=float(np.median(iR[m])), I_implied_med=float(np.median(Iimp[m])),
                    bound_signed_med=float(np.median(bd[m])), I_implied_over_bound_med=float(np.median(Iimp[m] / bd[m])))
    pr("  C %-8s n %5d  R2 %.3f  LS gain %.2f  rms tap %.1f  rms resid %.1f  mean resid %+.1f | I>>7 replay med %+.0f,"
       " implied-real med %+.0f, A3 bound (signed to E') med %+.0f, implied/bound med %+.2f"
       % (nm, resC[nm]["n"], resC[nm]["r2"], gfit, resC[nm]["rms_tap"], resC[nm]["rms_err"], resC[nm]["mean_err"],
          resC[nm]["I_rep_med"], resC[nm]["I_implied_med"], resC[nm]["bound_signed_med"], resC[nm]["I_implied_over_bound_med"]))
RES["C"] = resC
RES["Gband"] = Gband
RES["wall_s"] = time.time() - T0
pr("wall %.1f s" % RES["wall_s"])


def js(z):
    if isinstance(z, (np.floating, np.integer)):
        return z.item()
    if isinstance(z, np.ndarray):
        return z.tolist()
    return str(z)


(OUT / "m1_loop_identity.json").write_text(json.dumps(RES, default=js, indent=1))
(OUT / "m1_loop_identity.txt").write_text("\n".join(LOG), encoding="utf-8")
