"""REFUTER (data) for the route-79 V298 synthesis (docs/scoring/DRIVE-READ-V298-r79-2026-10-02.md).
Cache only, vectorised (no per-sample Python loop), target < 30 s.  Independent of judge_verify*.py and M1-M6 code.

 A  D sign + c_I/c_P by a TWO-INPUT FRF (tap <- raw, theta).  Any LTI operation acting on the tap alone (output lag
    pole, transport delay, ZOH, packer age, fade) cancels in H_theta/H_raw, so the D sign does NOT depend on the
    tap's timing -- the weakness of every time-domain regression the synthesis cites.
 A2 time-domain regression, lag swept -100..+100 ms (both directions), three omega sources.
 B  camera 0xE4 counts.   C  O1 reconstruction VALIDATED against co_ang (setpoint = wheel + 0.06 w).
 D  rate-cap and error-clip binding, pairing tested, and the firmware error ON cap frames.
 E  tap peak / p99 / >=300.   G  torque bar pinned (unfiltered and with the UI's 0.1 s filter).
 H  hands-off torque word p90 by band.   J  >22 tracking slope.   K  in-turn 4-8 Hz rate rms vs references.
"""
import time, json
import numpy as np
from scipy import signal
from pathlib import Path

T0 = time.time()
C = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v280")
OUT = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/_scratch/out/r79/refute")
OUT.mkdir(parents=True, exist_ok=True)
R, L = {}, []


def pr(s=""):
    print(s, flush=True); L.append(s)


def zoh(ts, x, t):
    j = np.searchsorted(ts, t, side="right") - 1
    return np.asarray(x)[np.clip(j, 0, len(x) - 1)]


def tapdec(D):
    f = ((D["b0"].astype(int) & 3) << 8) | D["b1"].astype(int)
    return np.where(f >= 512, -1.0, 1.0) * (f & 511)          # LSB = T/8, sign +sign(T)


def runs(m):
    d = np.diff(np.r_[0, m.astype(np.int8), 0])
    return np.flatnonzero(d == 1), np.flatnonzero(d == -1)


def erode(m, k):
    return np.convolve((~m).astype(float), np.ones(2 * k + 1), "same") == 0


def grid(D, fs=100.0):
    t0 = max(D["te4"][0], D["t14"][0], D["t18"][0], D["t1ab"][0]) + 1.0
    t1 = min(D["te4"][-1], D["t14"][-1], D["t18"][-1], D["t1ab"][-1]) - 1.0
    tg = np.arange(t0, t1, 1.0 / fs)
    g = dict(t=tg, ang=zoh(D["t14"], D["ang"], tg), raw=zoh(D["te4"], D["cmd"], tg), req=zoh(D["te4"], D["req"], tg) > 0,
             sca=zoh(D["t18"], D["sca"], tg) > 0, bar=zoh(D["t18"], D["tq"] * 1.024, tg),
             w18=-zoh(D["t18"], D["rate"], tg) / 8.0, v=zoh(D["tcs"], D["vego"], tg), tap=zoh(D["t1ab"], tapdec(D), tg))
    if "cs_rate" in D:
        g["csr"] = zoh(D["tcs"], D["cs_rate"], tg)
        g["press"] = zoh(D["tcs"], D["cs_press"], tg) > 0
    g["eng"] = g["req"] & g["sca"]
    on = np.where(np.r_[g["eng"][0], g["eng"][1:] & ~g["eng"][:-1]], tg, -np.inf)
    g["tse"] = tg - np.maximum.accumulate(on)
    return g


W = dict(np.load(C / "r79_a1f5d2_al.npz"))
F = dict(np.load(C / "r79_fork.npz"))
g = grid(W)
t, ang, raw, bar, v, tap = g["t"], g["ang"], g["raw"], g["bar"], g["v"], g["tap"]
eng, tse = g["eng"], g["tse"]
GBv = np.array([714, 1843, 2304, 2707, 4032, 6198]) / 230.4          # cave GB-P knots (design §1.3), m/s
GBg = np.array([1178, 1465, 760, 560, 1068, 2188])
cPw = lambda vv: 5.477e-4 * np.interp(vv, GBv, GBg)                   # design c_P, tap LSB per wire count
CD_DES = 0.566
pr("REFUTER (data) route 79  grid %d frames, engaged %.1f s" % (len(t), eng.sum() / 100))

# sign sanity: 0x18F torque vs carState steeringTorque
tqw = zoh(W["t18"], W["tq"], F["t_cs"])
c0 = np.corrcoef(tqw, F["cs_tq"])[0, 1]
c1 = np.corrcoef(tqw[1:], F["cs_tq"][:-1])[0, 1]
pr("sign: corr(wire tq, cs_tq) lag0 %+.3f lag1 %+.3f ; corr(w18, csr) %+.3f ; corr(w18, dang/dt) %+.3f" % (
    c0, c1, np.corrcoef(g["w18"], g["csr"])[0, 1], np.corrcoef(g["w18"], np.gradient(ang, 0.01))[0, 1]))
R["sign"] = dict(tq_vs_cstq_lag0=c0, lag1=c1)

# ============================================================== A. two-input FRF
BANDS = ((0, 5, "<5"), (5, 8, "5-8"), (8, 12.5, "8-12.5"), (12.5, 22, "12.5-22"), (22, 99, ">22"), (5, 99, "pooled>5"))
base = eng & (tse >= 1.2) & (np.abs(bar) < 500)
mA = erode(base, 30)
NPS, STEP = 256, 128
a, b = runs(mA)
starts = np.concatenate([np.arange(s, e - NPS + 1, STEP) for s, e in zip(a, b) if e - s >= NPS] or [np.zeros(0, int)]).astype(int)
idx = starts[:, None] + np.arange(NPS)[None, :]
win = np.hanning(NPS)
fr = np.fft.rfftfreq(NPS, 0.01)
wj = 1j * 2 * np.pi * np.where(fr > 0, fr, np.nan)


def seg_fft(x, shift=0):
    xs = x[np.clip(idx + shift, 0, len(x) - 1)]
    xs = signal.detrend(xs, axis=1)
    return np.fft.rfft(xs * win, axis=1)


def frf(Xr, Xa, Y, sel):
    S11 = np.sum(np.conj(Xr[sel]) * Xr[sel], 0); S12 = np.sum(np.conj(Xr[sel]) * Xa[sel], 0)
    S22 = np.sum(np.conj(Xa[sel]) * Xa[sel], 0)
    S1y = np.sum(np.conj(Xr[sel]) * Y[sel], 0); S2y = np.sum(np.conj(Xa[sel]) * Y[sel], 0)
    Syy = np.sum(np.abs(Y[sel]) ** 2, 0)
    det = S11 * S22 - np.abs(S12) ** 2
    Hr = (S22 * S1y - S12 * S2y) / det                   # solve [[S11,S12],[S21,S22]] H = Sxy (S21 = conj S12)
    Ha = (S11 * S2y - np.conj(S12) * S1y) / det
    coh_in = np.abs(S12) ** 2 / (S11 * S22).real
    mcoh = (np.real(np.conj(Hr) * S1y + np.conj(Ha) * S2y) / Syy)
    return Hr, Ha, coh_in.real, mcoh


Yt = seg_fft(tap)
Xa = seg_fft(ang)
vseg = v[idx].mean(1)
pr("\nA. TWO-INPUT FRF tap <- (raw, theta): %d segments of 2.56 s (hands-off |bar|<500, >=1.2 s, eroded 0.3 s)" % len(starts))
pr("   Re(Ha/Hr) should be 10 (P sees raw + 10 theta).  D/P = Re[ (Ha-10Hr)/(jw Hr) * (1 + cIcP/jw) ], cIcP = 2.8 (design)")
pr("   design D/P = 0.566 / cP_w(v) s.  >0 = D OPPOSES motion.  Shift = raw moved +-1 frame vs theta (timing ambiguity).")
fsel = (fr >= 1.0) & (fr <= 5.0)
resA = {}
for shift in (0, -1, 1):
    Xr = seg_fft(raw, shift)
    for lo, hi, nm in BANDS:
        sel = (vseg >= lo) & (vseg < hi)
        if sel.sum() < 4:
            continue
        Hr, Ha, cin, mc = frf(Xr, Xa, Yt, sel)
        ratio = Ha / Hr
        Q = (Ha - 10 * Hr) / wj
        DP = Q / Hr * (1 + 2.8 / wj)
        DPn = Q / Hr                                           # no I correction
        des = CD_DES / cPw(vseg[sel].mean())
        rr = np.median(ratio[fsel].real)
        dpm = np.median(DP[fsel].real)
        dpn = np.median(DPn[fsel].real)
        pos = np.mean(DP[fsel].real > 0)
        cD_est = dpm * cPw(vseg[sel].mean())
        key = "%s|sh%+d" % (nm, shift)
        resA[key] = dict(nseg=int(sel.sum()), re_ratio=rr, DP=dpm, DP_noI=dpn, DP_design=des, frac_pos_bins=pos,
                         cD_est=cD_est, coh_in=float(np.median(cin[fsel])), mcoh=float(np.median(mc[fsel])))
        if shift == 0 or nm == "pooled>5":
            pr("   sh%+d %-9s nseg %4d  Re(Ha/Hr) %5.2f  D/P %+.3f s (noI %+.3f) design %.3f -> x%.2f ; bins>0 %.2f ; cD~%+.3f ; coh(raw,th) %.2f mcoh %.2f" % (
                shift, nm, sel.sum(), rr, dpm, dpn, des, dpm / des, pos, cD_est, np.median(cin[fsel]), np.median(mc[fsel])))
R["A_frf"] = resA

# per-bin table, pooled >5, shift 0
Xr = seg_fft(raw)
sel = vseg >= 5
Hr, Ha, cin, mc = frf(Xr, Xa, Yt, sel)
pr("   per-bin pooled>5: f Hz | Re(Ha/Hr) | D/P s | phase(Hr) deg | mcoh")
binrows = []
for k in np.flatnonzero((fr >= 0.39) & (fr <= 8.0)):
    DPk = ((Ha[k] - 10 * Hr[k]) / wj[k] / Hr[k] * (1 + 2.8 / wj[k])).real
    binrows.append((fr[k], (Ha[k] / Hr[k]).real, DPk, np.degrees(np.angle(Hr[k])), mc[k]))
for r_ in binrows[::2]:
    pr("     %5.2f | %6.2f | %+.3f | %+7.1f | %.2f" % r_)
R["A_bins"] = binrows

# c_I/c_P and delay from phase(Hr) = -atan(cIcP/w) - atan(w*tau_lag) - w*d ; tau_lag from the image pole (992/1024)^10
a100 = (992 / 1024.0) ** 10
tau_lag = -0.01 / np.log(a100)
kk = (fr >= 0.39) & (fr <= 6.0)
ph = np.unwrap(np.angle(Hr[kk])); wk = 2 * np.pi * fr[kk]
best = None
for ci in np.arange(0.0, 8.01, 0.05):
    for d in np.arange(-0.05, 0.151, 0.0025):
        res = ph - (-np.arctan(ci / wk) - np.arctan(wk * tau_lag) - wk * d)
        res = (res + np.pi) % (2 * np.pi) - np.pi
        s = np.sum(res ** 2 * mc[kk])
        if best is None or s < best[0]:
            best = (s, ci, d)
pr("   phase fit pooled>5: cI/cP %.2f /s, pure delay %.1f ms (on top of the %.1f ms image lag pole)" % (best[1], best[2] * 1e3, tau_lag * 1e3))
R["A_phasefit"] = dict(cIcP=best[1], delay_ms=best[2] * 1e3, tau_lag_ms=tau_lag * 1e3)
cirows = {}
for lo, hi, nm in BANDS[:5]:
    sel = (vseg >= lo) & (vseg < hi)
    if sel.sum() < 4:
        continue
    Hr_, Ha_, cin_, mc_ = frf(Xr, Xa, Yt, sel)
    ph = np.unwrap(np.angle(Hr_[kk]))
    bb = None
    for ci in np.arange(0.0, 8.01, 0.1):
        for d in np.arange(-0.05, 0.151, 0.005):
            res = ph - (-np.arctan(ci / wk) - np.arctan(wk * tau_lag) - wk * d)
            res = (res + np.pi) % (2 * np.pi) - np.pi
            s = np.sum(res ** 2 * mc_[kk])
            if bb is None or s < bb[0]:
                bb = (s, ci, d)
    cirows[nm] = (bb[1], bb[2] * 1e3)
pr("   per band cI/cP (/s), delay (ms): " + "  ".join("%s %.1f/%.0f" % (k_, *v_) for k_, v_ in cirows.items()))
R["A_cIcP_bands"] = cirows

# ============================================================== A2. time-domain lag sweep, both directions
pr("\nA2. TIME-DOMAIN: tap(t+L) = cP ew + cI Iw + cD w, band-pass 1-6 Hz, L in -100..+100 ms (L>0 = tap lags)")
sos = signal.butter(2, [1.0, 6.0], btype="band", fs=100.0, output="sos")
bp = lambda x: signal.sosfiltfilt(sos, x)
ew = raw + 10 * ang
Iw = np.cumsum(ew) * 0.01
fb = dict(ew=bp(ew), Iw=bp(Iw), tap=bp(tap), w18=bp(g["w18"]), csr=bp(g["csr"]), dang=bp(np.gradient(ang, 0.01)))
mT = erode(base, 50)
resA2 = {}
for wn in ("w18", "csr", "dang"):
    for lo, hi, nm in ((5, 12.5, "5-12.5"), (12.5, 99, ">12.5"), (5, 99, "pooled>5")):
        m = mT & (v >= lo) & (v < hi)
        row = []
        for Lf in range(-10, 11):
            y = np.roll(fb["tap"], -Lf)[m]
            X = np.c_[fb["ew"][m], fb["Iw"][m], fb[wn][m]]
            c, *_ = np.linalg.lstsq(X, y, rcond=None)
            r2 = 1 - np.var(y - X @ c) / np.var(y)
            row.append((Lf * 10, c[2], r2, c[0] / cPw(v[m].mean())))
        row = np.array(row)
        bi = int(np.argmax(row[:, 2]))
        zc = row[row[:, 1] > 0, 0]
        resA2["%s|%s" % (wn, nm)] = dict(best_L_ms=row[bi, 0], cD_best=row[bi, 1], r2=row[bi, 2], cP_ratio=row[bi, 3],
                                         cD_at={int(r_[0]): r_[1] for r_ in row},
                                         L_ms_where_cD_pos=[float(zc.min()) if len(zc) else None, float(zc.max()) if len(zc) else None])
        pr("   w=%-4s %-8s bestL %+4d ms R2 %.3f cP/des %.2f cD %+.3f | cD @-100 %+.2f -50 %+.2f -20 %+.2f 0 %+.2f +20 %+.2f +50 %+.2f +100 %+.2f | cD>0 for L in [%s..%s] ms" % (
            wn, nm, row[bi, 0], row[bi, 2], row[bi, 3], row[bi, 1], row[0, 1], row[5, 1], row[8, 1], row[10, 1], row[12, 1], row[15, 1], row[20, 1],
            zc.min() if len(zc) else None, zc.max() if len(zc) else None))
R["A2"] = resA2

# ============================================================== B. camera
B = dict(cam=int(len(F["t_e4cam"])), cam_req1=int((F["e4cam_req"] > 0).sum()),
         cam_req1_arm=sorted(set(F["e4cam_arm"][F["e4cam_req"] > 0].tolist())),
         tx0=int(len(F["t_e4tx0"])), tx0_req1=int((F["e4tx0_req"] > 0).sum()),
         rx1=int(len(F["t_e4rx1"])), rx1_last=float(F["t_e4rx1"].max()), rx1_after_39=int((F["t_e4rx1"] > 39.0).sum()),
         rx0_last=float(F["t_e4rx0"].max()) if len(F["t_e4rx0"]) else None,
         tx1_arm=sorted(set(F["e4tx1_arm"].tolist())), rej1=int(len(F["t_e4rej1"])))
cr = F["t_e4cam"][F["e4cam_req"] > 0]
d_ = np.diff(cr); B["cam_req_episodes"] = int(1 + (d_ > 1.0).sum()) if len(cr) else 0
B["cam_req_span"] = [float(cr.min()), float(cr.max())] if len(cr) else None
# was the fork laterally active while the camera requested?
latcs = zoh(F["t_cc"], F["cc_latActive"], cr) > 0
B["cam_req_during_fork_lat"] = float(latcs.mean()) if len(cr) else None
# does the tap react? EPS-side: tap during camera request vs not, while engaged
R["B"] = B
pr("\nB. CAMERA " + json.dumps(B))

# ============================================================== C/D. fork limiter on carOutput rows
tco, co, tcs = F["t_co"], F["co_ang"], F["t_cs"]
csa, csr_, cstq, press, vr = F["cs_ang"], F["cs_rate"], F["cs_tq"], F["cs_press"].astype(bool), F["cs_vegoraw"]
lat = zoh(F["t_cc"], F["cc_latActive"], tco) > 0
ccang = zoh(F["t_cc"], F["cc_ang"], tco)
BP, EV = [3.1, 8.0, 10.0, 11.75, 17.5, 26.9], [17.0, 15.5, 19.5, 17.0, 8.5, 4.5]
pair = {}
for p_ in (0, 1, 2):
    j = np.clip(np.arange(len(tco)) - p_, 0, None)
    ex = np.abs(co - csa[j]) - np.interp(vr[j], BP, EV)
    pair[p_] = float(np.max(ex[lat]))
pr("\nC. clip pairing: max(|co - cs_ang[i-p]| - emax) on latActive rows: p0 %+.4f  p1 %+.4f  p2 %+.4f deg" % (pair[0], pair[1], pair[2]))
P_ = 1
j = np.clip(np.arange(len(tco)) - P_, 0, None)
sj, rj, tj, vj, pj = csa[j], csr_[j], cstq[j], vr[j], press[j]
emax = np.interp(vj, BP, EV)
# O1 reconstruction (hysteresis 600 / 500 raw on |steeringTorque|, reset when not latActive), on the carState row used
s = np.where(~lat, 0.0, np.where(np.abs(tj) > 600, 1.0, np.where(np.abs(tj) <= 500, 0.0, np.nan)))
ii = np.where(~np.isnan(s), np.arange(len(s)), 0); ii = np.maximum.accumulate(ii)
o1 = (s[ii] > 0) & lat
o1_pred = np.clip(sj + rj * 0.06, sj - emax, sj + emax)
ok_on = np.abs(co - o1_pred) < 0.051
val = dict(o1_frames=int(o1.sum()), match_on_o1=float(ok_on[o1].mean()), match_on_nono1=float(ok_on[lat & ~o1].mean()))
# also the same-row pairing for O1 decision (judge used row i)
s0 = np.where(~lat, 0.0, np.where(np.abs(cstq) > 600, 1.0, np.where(np.abs(cstq) <= 500, 0.0, np.nan)))
i0 = np.where(~np.isnan(s0), np.arange(len(s0)), 0); i0 = np.maximum.accumulate(i0)
o1_same = (s0[i0] > 0) & lat
val["o1_frames_samerow"] = int(o1_same.sum())
val["match_on_o1_samerow"] = float(ok_on[o1_same].mean())
a, b = runs(o1)
dur = (b - a) / 100.0
val.update(episodes=int(len(a)), total_s=float(dur.sum()), share_lat=float(o1.sum() / lat.sum()),
           le50ms=float(np.mean(dur <= 0.05)), never_pressed=int(sum(1 for x, y in zip(a, b) if not pj[x:y].any())))
for lo, hi, nm in ((0, 5, "<5"), (5, 8, "5-8"), (8, 12.5, "8-12.5"), (12.5, 99, ">12.5")):
    m = lat & (vr >= lo) & (vr < hi)
    val["share_" + nm] = float(o1[m].mean())
R["O1"] = val
pr("C. O1 (pairing i-1): " + json.dumps({k_: (round(v_, 4) if isinstance(v_, float) else v_) for k_, v_ in val.items()}))

# rate cap: step of co from the previous applied value, excluding O1 on this or the previous row and first lat row
o1p = o1 | np.r_[False, o1[:-1]]
latp = lat & np.r_[False, lat[:-1]]
dco = np.r_[0.0, np.diff(co)]
cap = latp & ~o1p & (np.abs(np.abs(dco) - 1.2) < 1e-3)
gap = np.abs(ccang - co)
clipb = lat & (np.abs(co - sj) - emax >= -1e-3)
err_fw = co - sj                                         # fork-side tracking error (deg) on the row it used
ho = ~o1p & ~pj
hardJ = lat & ((np.abs(sj) > 30) | (np.abs(rj) > 60))   # the synthesis' "hard"
hardR = lat & (np.abs(rj) > 60)                           # dynamic only
hardG = latp & ~o1p & (gap > 5.0)                        # demand-limited: desired leads applied by > 5 deg
pr("D. RATE CAP / CLIP (carOutput rows, latActive, pairing i-1):")
pr("   band      | lat s | cap%%lat | clip%%lat | hardJ&HO s cap%% | hardR&HO s cap%% | gap>5 s: cap%% | on cap: |err| p50/p90 deg, |w| p50 deg/s, frac |err|<3")
Drows = []
for lo, hi, nm in ((0, 5, "<5"), (5, 8, "5-8"), (8, 12.5, "8-12.5"), (12.5, 22, "12.5-22"), (22, 99, ">22"), (0, 8, "<8"), (0, 99, "all")):
    m = lat & (vj >= lo) & (vj < hi)
    mJ, mR, mG = m & hardJ & ho, m & hardR & ho, m & hardG & ~pj
    mc_ = m & cap
    e_ = np.abs(err_fw[mc_])
    row = dict(band=nm, lat_s=m.sum() / 100, cap=100 * cap[m].mean(), clip=100 * clipb[m].mean(),
               hardJ_s=mJ.sum() / 100, hardJ_cap=100 * cap[mJ].mean() if mJ.any() else np.nan,
               hardR_s=mR.sum() / 100, hardR_cap=100 * cap[mR].mean() if mR.any() else np.nan,
               gap_s=mG.sum() / 100, gap_cap=100 * cap[mG].mean() if mG.any() else np.nan,
               cap_s=mc_.sum() / 100, err50=np.median(e_) if len(e_) else np.nan, err90=np.percentile(e_, 90) if len(e_) else np.nan,
               w50=np.median(np.abs(rj[mc_])) if mc_.any() else np.nan, err_lt3=float(np.mean(e_ < 3)) if len(e_) else np.nan)
    Drows.append(row)
    pr("   %-9s | %6.1f | %5.2f | %5.2f | %5.1f %5.1f | %5.1f %5.1f | %5.1f %5.1f | cap %5.1f s: %.1f/%.1f, %.0f, %.2f" % (
        nm, row["lat_s"], row["cap"], row["clip"], row["hardJ_s"], row["hardJ_cap"], row["hardR_s"], row["hardR_cap"], row["gap_s"],
        row["gap_cap"], row["cap_s"], row["err50"], row["err90"], row["w50"], row["err_lt3"]))
R["D"] = Drows
# wheel faster than the cap?
mm = lat & hardJ & ho
R["D_wheel"] = dict(rate_p99=float(np.percentile(np.abs(rj[mm]), 99)), frac_gt130=float(np.mean(np.abs(rj[mm]) > 130)),
                    setp_rate_p99=float(np.percentile(np.abs(dco[mm]) * 100, 99)))
pr("   hardJ&HO: |wheel rate| p99 %.0f deg/s, frac > 130 deg/s %.3f, |setpoint step| p99 %.0f deg/s" % (
    R["D_wheel"]["rate_p99"], R["D_wheel"]["frac_gt130"], R["D_wheel"]["setp_rate_p99"]))

# ============================================================== E. tap stats
def tapstats(D, nm):
    tt = D["t1ab"]
    e2 = (zoh(D["te4"], D["req"], tt) > 0) & (zoh(D["t18"], D["sca"], tt) > 0)
    tp = np.abs(tapdec(D))[e2]
    return dict(route=nm, eng_s=float(e2.sum() * 0.02), pk=float(tp.max()), p99=float(np.percentile(tp, 99)),
                p999=float(np.percentile(tp, 99.9)), ge300=int((tp >= 300).sum()), ge250=int((tp >= 250).sum()))


E = [tapstats(W, "r79")]
for nm in ("r6c", "r39", "r71b_v294"):
    E.append(tapstats(dict(np.load(C / (nm + ".npz"))), nm))
R["E"] = E
pr("\nE. TAP (native 50 Hz instants, engaged): " + " | ".join("%s pk %.0f p99 %.0f p99.9 %.0f >=250 %d >=300 %d (%.0f s)" % (
    e["route"], e["pk"], e["p99"], e["p999"], e["ge250"], e["ge300"], e["eng_s"]) for e in E))

# ============================================================== G. torque bar
tctl = F["t_ctl"]
vv = zoh(tcs, F["cs_vego"], tctl)
roll = zoh(F["t_lp"], F["lp_roll"], tctl)
latc = F["cc_latActive"] > 0                               # same row count & loop as controlsState
mla = json.loads(str(F["carparams_json"]))["maxLateralAccel"]
ades = F["ctl_dcurv"] * vv ** 2
rc_ = roll * 9.81 * np.interp(vv, [5, 15], [0, 1])
x = np.clip((ades - rc_) / mla, -1, 1)
x = np.where(latc, x, 0.0)
al = 0.01 / (0.1 + 0.01)
xf = signal.lfilter([al], [1, -(1 - al)], x)              # FirstOrderFilter(rc 0.1) at 100 Hz
ereq = (zoh(W["te4"], W["req"], tctl) > 0) & (zoh(W["t18"], W["sca"], tctl) > 0)
mG = latc & ereq & (vv > 3)
tpc = zoh(W["t1ab"], tapdec(W), tctl)
Gd = dict(eng_s=float(mG.sum() / 100), pinned_raw=float(np.mean(np.abs(x[mG]) >= 0.999)), pinned_filt95=float(np.mean(np.abs(xf[mG]) >= 0.95)),
          pinned_noroll=float(np.mean(np.abs(np.clip(ades / mla, -1, 1)[mG]) >= 0.999)),
          corr_abs=float(np.corrcoef(np.abs(xf[mG]), np.abs(tpc[mG]))[0, 1]),
          corr_signed=float(np.corrcoef(xf[mG], -tpc[mG])[0, 1]),
          p_full_given_tap_lt25=float(np.mean(np.abs(xf[mG & (np.abs(tpc) < 25)]) >= 0.9)),
          pinned_lat_all=float(np.mean(np.abs(x[latc & (vv > 3)]) >= 0.999)))
R["G"] = Gd
pr("\nG. BAR " + json.dumps({k_: round(v_, 3) for k_, v_ in Gd.items()}))

# ============================================================== H. hands-off torque word p90 by band
pr("H. |bar| (wire x1.024) engaged settled cs_press==0: band p50/p90/p99, %>512, %>614")
Hrows = {}
for lo, hi, nm in ((0, 5, "<5"), (5, 8, "5-8"), (8, 12.5, "8-12.5"), (12.5, 22, "12.5-22"), (22, 99, ">22")):
    m = eng & (tse >= 1.2) & ~g["press"] & (v >= lo) & (v < hi)
    bb = np.abs(bar[m])
    Hrows[nm] = (m.sum() / 100, *np.percentile(bb, [50, 90, 99]), 100 * np.mean(bb > 512), 100 * np.mean(bb > 614))
    pr("   %-8s %5.0f s  %4.0f / %4.0f / %4.0f  %4.1f %%  %4.1f %%" % ((nm,) + Hrows[nm]))
R["H"] = Hrows

# ============================================================== J. >22 tracking slope (0.5 Hz LPF, real paths)
sosl = signal.butter(2, 0.5, fs=100.0, output="sos")
thf, spf = signal.sosfiltfilt(sosl, ang), signal.sosfiltfilt(sosl, -raw / 10.0)
mJ = erode(eng & (tse >= 1.2) & (np.abs(bar) < 500), 25)
Jr = {}
for lo, hi, nm in ((8, 15, "8-15"), (15, 22, "15-22"), (22, 99, ">22"), (25, 99, ">=25")):
    m = mJ & (v >= lo) & (v < hi)
    X, Y = spf[m], thf[m]
    s0 = float(np.sum(X * Y) / np.sum(X * X))
    s1 = float(np.polyfit(X, Y, 1)[0]) if m.sum() > 10 else np.nan
    # drop the last 1 / 2 s of each run in band
    a_, b_ = runs(m)
    keep1, keep2 = m.copy(), m.copy()
    for x_, y_ in zip(a_, b_):
        keep1[max(x_, y_ - 100):y_] = False; keep2[max(x_, y_ - 200):y_] = False
    s_1 = float(np.sum(spf[keep1] * thf[keep1]) / np.sum(spf[keep1] ** 2)) if keep1.any() else np.nan
    s_2 = float(np.sum(spf[keep2] * thf[keep2]) / np.sum(spf[keep2] ** 2)) if keep2.any() else np.nan
    Jr[nm] = dict(s=m.sum() / 100, slope0=s0, slope_int=s1, slope_drop1=s_1, slope_drop2=s_2, nruns=int(len(a_)))
    pr("J. tracking %-5s %5.1f s (%d runs): through-0 %.3f, with intercept %.3f, drop last 1 s/run %.3f, 2 s %.3f" % (
        nm, m.sum() / 100, len(a_), s0, s1, s_1, s_2))
R["J"] = Jr

# ============================================================== K. in-turn 4-8 Hz rate rms, references
sos48 = signal.butter(2, [4.0, 8.0], btype="band", fs=100.0, output="sos")
Kr = {}
for nm, D in (("r79", W), ("r6c", None), ("r39", None), ("r71b_v294", None)):
    if D is None:
        D = dict(np.load(C / (nm + ".npz")))
    gg = g if nm == "r79" else grid(D)
    w = gg["w18"]
    mbar = np.convolve(w, np.ones(51) / 51, "same")
    wb = signal.sosfiltfilt(sos48, w)
    row = {}
    for lo, hi, bn in ((0, 5, "0-5"), (5, 10, "5-10"), (10, 20, "10-20")):
        m = gg["eng"] & (np.abs(mbar) >= 10) & (gg["v"] >= lo) & (gg["v"] < hi)
        mh = m & (np.abs(gg["bar"]) < 500)
        row[bn] = (m.sum() / 100, float(np.sqrt(np.mean(wb[m] ** 2))) if m.sum() > 50 else np.nan,
                   mh.sum() / 100, float(np.sqrt(np.mean(wb[mh] ** 2))) if mh.sum() > 50 else np.nan)
    Kr[nm] = row
    pr("K. %-10s in-turn 4-8 Hz w18 rms (deg/s) [all | hands-off |bar|<500]: " % nm + "  ".join(
        "%s: %.0fs %.2f | %.0fs %.2f" % (bn, *row[bn]) for bn in row))
R["K"] = Kr


# ============================================================== D2. cap runs: does the wheel follow the capped setpoint?
a_, b_ = runs(cap)
rows = []
tg_co = tco
for x_, y_ in zip(a_, b_):
    if y_ - x_ < 10:
        continue
    sp_tr = abs(co[y_ - 1] - co[x_ - 1])
    wh_tr = abs(csa[min(y_ - 1 + 10, len(csa) - 1)] - csa[x_ - 1])      # wheel travel incl. 100 ms of follow-through
    wh_tr0 = abs(csa[y_ - 1] - csa[x_ - 1])
    tpk = np.abs(zoh(W["t1ab"], tapdec(W), tco[x_:y_])).max()
    rows.append((y_ - x_, sp_tr, wh_tr0, wh_tr, tpk, vr[x_]))
rows = np.array(rows)
if len(rows):
    R["D2"] = dict(nruns=int(len(rows)), dur_p50=float(np.median(rows[:, 0]) / 100), sp_travel_p50=float(np.median(rows[:, 1])),
                   wheel_over_sp_in_run=float(np.median(rows[:, 2] / rows[:, 1])), wheel_over_sp_plus100ms=float(np.median(rows[:, 3] / rows[:, 1])),
                   tap_pk_p50=float(np.median(rows[:, 4])), tap_pk_p90=float(np.percentile(rows[:, 4], 90)), tap_pk_max=float(rows[:, 4].max()))
    pr("D2. cap runs >= 100 ms: n %d, dur p50 %.2f s, setpoint travel p50 %.1f deg; wheel/setpoint travel in-run p50 %.2f, +100 ms %.2f; run tap peak p50 %.0f p90 %.0f max %.0f LSB (rail 307.6)" % (
        len(rows), R["D2"]["dur_p50"], R["D2"]["sp_travel_p50"], R["D2"]["wheel_over_sp_in_run"], R["D2"]["wheel_over_sp_plus100ms"],
        R["D2"]["tap_pk_p50"], R["D2"]["tap_pk_p90"], R["D2"]["tap_pk_max"]))
tco_tap = np.abs(zoh(W["t1ab"], tapdec(W), tco))
pr("    tap on cap frames p50/p90/max %.0f / %.0f / %.0f LSB ; on hardJ&HO non-cap %.0f / %.0f" % (
    np.median(tco_tap[cap]), np.percentile(tco_tap[cap], 90), tco_tap[cap].max(),
    np.median(tco_tap[lat & hardJ & ho & ~cap]), np.percentile(tco_tap[lat & hardJ & ho & ~cap], 90)))

# ============================================================== K2. 4-8 Hz in-turn excess away from O1
o1g = zoh(tco, o1.astype(float), t) > 0
near = np.convolve(o1g.astype(float), np.ones(61), "same") > 0          # within +-0.3 s of an O1 frame
w = g["w18"]; mbar = np.convolve(w, np.ones(51) / 51, "same"); wb = signal.sosfiltfilt(sos48, w)
for lo, hi, bn in ((0, 5, "0-5"), (5, 10, "5-10")):
    m = eng & (np.abs(mbar) >= 10) & (v >= lo) & (v < hi)
    pr("K2. r79 %s in-turn 4-8 Hz rms: far from O1 (>0.3 s) %.0f s %.2f | near O1 %.0f s %.2f ; O1 within 0.3 s on %.0f %% of turning" % (
        bn, (m & ~near).sum() / 100, np.sqrt(np.mean(wb[m & ~near] ** 2)), (m & near).sum() / 100, np.sqrt(np.mean(wb[m & near] ** 2)),
        100 * near[m].mean()))
    R.setdefault("K2", {})[bn] = dict(far_s=(m & ~near).sum() / 100, far=float(np.sqrt(np.mean(wb[m & ~near] ** 2))),
                                     near=float(np.sqrt(np.mean(wb[m & near] ** 2))), near_share=float(near[m].mean()))

# ============================================================== M. hand-freeze duty and discarded integration (vectorised, hand rules only)
th, sp = ang, -raw / 10.0
E = 16 * np.round(10 * (sp - th))
G = np.interp(v, GBv, GBg)
Ep = np.floor(E * G / 256.0)
gp60 = -bar                                                   # gp-0x4f60 = -wire*1.024 (M3; sign checked above: wire = -cs_tq)
hard_f = np.abs(bar) > 512
opp_f = ~hard_f & (np.abs(bar) > 300) & (np.sign(gp60) * np.sign(Ep) < 0)
opp_flip = ~hard_f & (np.abs(bar) > 300) & (np.sign(gp60) * np.sign(Ep) > 0)
mM = eng & (tse >= 1.2) & ~g["press"]
fz = hard_f | opp_f
de = np.gradient(np.abs(sp - th), 0.01)
pr("M. hand-freeze (settled, cs_press==0): hard %.1f %%, opposing %.1f %% (flipped-sign rule would give %.1f %%); |Ep|-weighted discarded %.1f %% (<8 m/s %.1f %%)" % (
    100 * hard_f[mM].mean(), 100 * opp_f[mM].mean(), 100 * opp_flip[mM].mean(),
    100 * np.sum(np.abs(Ep[mM & fz])) / np.sum(np.abs(Ep[mM])), 100 * np.sum(np.abs(Ep[mM & fz & (v < 8)])) / np.sum(np.abs(Ep[mM & (v < 8)]))))
pr("   mean d|e|/dt frozen %+.2f deg/s, free %+.2f deg/s" % (np.mean(de[mM & fz]), np.mean(de[mM & ~fz])))
R["M"] = dict(hard=float(hard_f[mM].mean()), opp=float(opp_f[mM].mean()), opp_flip=float(opp_flip[mM].mean()),
              discarded=float(np.sum(np.abs(Ep[mM & fz])) / np.sum(np.abs(Ep[mM]))),
              discarded_lt8=float(np.sum(np.abs(Ep[mM & fz & (v < 8)])) / np.sum(np.abs(Ep[mM & (v < 8)]))),
              de_frozen=float(np.mean(de[mM & fz])), de_free=float(np.mean(de[mM & ~fz])))

# ============================================================== D3. is the cap binding a consequence of O1 release (re-slew)?
rel = np.r_[False, o1[:-1] & ~o1[1:]]                          # O1 falling edge rows
since_rel = np.arange(len(o1)) - np.maximum.accumulate(np.where(rel, np.arange(len(o1)), -10 ** 9))
post = since_rel <= 30                                          # within 0.3 s after an O1 release
pr("D3. cap frames within 0.3 s after an O1 release: %.1f %% (<8 m/s %.1f %%); base rate of that window on latActive %.1f %%" % (
    100 * post[cap].mean(), 100 * post[cap & (vj < 8)].mean(), 100 * post[lat].mean()))
mm = lat & hardJ & ho
pr("    hardJ&HO: desired leads applied by > 30 deg on %.1f %% ; > 5 deg on %.1f %%" % (100 * np.mean(gap[mm] > 30), 100 * np.mean(gap[mm] > 5)))
R["D3"] = dict(cap_post_release=float(post[cap].mean()), cap_post_release_lt8=float(post[cap & (vj < 8)].mean()),
               base=float(post[lat].mean()), gap30=float(np.mean(gap[mm] > 30)))

# ============================================================== A3. c_I/c_P, time domain, tap shifted +30 ms (best-R2 lag above)
cs_ = np.cumsum(np.where(eng, ew, 0.0)) * 0.01
isst = np.r_[eng[0], eng[1:] & ~eng[:-1]]
basev = np.where(isst, np.r_[0.0, cs_[:-1]], 0.0)
lastst = np.maximum.accumulate(np.where(isst, np.arange(len(ew)), 0))
Iwe = np.where(eng, cs_ - basev[lastst], 0.0)
for lo_f, hi_f in ((0.1, 3.0), (0.3, 3.0)):
    so = signal.butter(2, [lo_f, hi_f], btype="band", fs=100.0, output="sos")
    f2 = {k_: signal.sosfiltfilt(so, x_) for k_, x_ in (("ew", ew), ("I", Iwe), ("w", g["w18"]), ("tap", np.roll(tap, -3)))}
    row = []
    for lo, hi, nm in ((0, 8, "<8"), (8, 12.5, "8-12.5"), (12.5, 22, "12.5-22"), (22, 99, ">22"), (5, 99, "pooled>5")):
        m = mT & (v >= lo) & (v < hi)
        X = np.c_[f2["ew"][m], f2["I"][m], f2["w"][m]]
        c, *_ = np.linalg.lstsq(X, f2["tap"][m], rcond=None)
        row.append("%s %.2f (cD %+.2f)" % (nm, c[1] / c[0], c[2]))
        R.setdefault("A3", {})["%g-%g|%s" % (lo_f, hi_f, nm)] = dict(cIcP=float(c[1] / c[0]), cD=float(c[2]))
    pr("A3. cI/cP time-domain %.1f-%.0f Hz, tap +30 ms, per-episode integral: " % (lo_f, hi_f) + " | ".join(row))

beyond = lat & (np.abs(ccang - sj) > emax)
for lo, hi, nm in ((0, 8, "<8"), (0, 99, "all")):
    mm = lat & hardJ & ho & (vj >= lo) & (vj < hi)
    ml = lat & (vj >= lo) & (vj < hi)
    pr("D4. demand beyond the clip %s: hardJ&HO %.1f %% (of which post-O1-release %.1f %%), all latActive %.1f %%" % (
        nm, 100 * beyond[mm].mean(), 100 * post[mm & beyond].mean(), 100 * beyond[ml].mean()))
    R.setdefault("D4", {})[nm] = dict(hard=float(beyond[mm].mean()), post=float(post[mm & beyond].mean()), lat=float(beyond[ml].mean()))
pr("D4. cap frames on hardJ&HO that are post-O1-release: %.1f %%" % (100 * post[cap & lat & hardJ & ho].mean()))

R["wall_s"] = time.time() - T0
pr("\nwall %.1f s" % R["wall_s"])
(OUT / "refute_synth_data.json").write_text(json.dumps(R, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o)))
(OUT / "refute_synth_data.txt").write_text("\n".join(L), encoding="utf-8")
