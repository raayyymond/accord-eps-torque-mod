# -*- coding: utf-8 -*-
r"""refute_inference.py -- REFUTER (inference) on the route-79 synthesis (DRIVE-READ-V298-r79-2026-10-02.md).
Cache only, vectorised, target < 30 s.  Writes _scratch/out/r79/refute/refute_inference.{txt,json}.

  A  D sign IDENTIFIABILITY: adds the setpoint RATE as a regressor, so a timing mismatch on the P term
     (cP*10*delta*(w - sp')) is separated from a true D on w.  cD_true = b_w + c_sp  (if the angle and the setpoint
     share their timing error), and the angle-only timing offset that would flip the sign is printed.
  B  hard-manoeuvre DENOMINATOR: O1 / steeringPressed / |cs_tq| tiers / hands-off share of ALL hard frames, and the
     120 deg/s cap's share of ALL hard frames (the synthesis quotes the cap on the hands-off subset only).
  C  is the cap DOWNSTREAM of O1?  time since the last O1 release on cap-binding hands-off hard frames; does the
     wheel keep up with the capped setpoint (rate ratio, error growth) inside cap runs.
  D  ratchet: M4's own stall-surge detector, per band, split by "bar spike > 614 (O1's level) within +-0.5 s"
     applied IDENTICALLY to r79 and the references (r79's O1 needs that spike; the refs have no O1).
  E  peak tap: what was true at the top-1 % |tap| engaged frames (err, v, O1, cap, pressed).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import signal

T0 = time.time()
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import m4_common as C          # noqa: E402
import m4_episodes as EP       # noqa: E402

CA = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v280")
OUT = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/_scratch/out/r79/refute")
OUT.mkdir(parents=True, exist_ok=True)
W = dict(np.load(CA / "r79_a1f5d2_al.npz"))
F = dict(np.load(CA / "r79_fork.npz"))
R, lines = {}, []


def pr(s):
    print(s)
    lines.append(s)


def zoh(ts, x, t):
    j = np.searchsorted(ts, t, side="right") - 1
    return np.asarray(x)[np.clip(j, 0, len(x) - 1)]


def tapdec(Wd):
    fld = ((Wd["b0"].astype(int) & 3) << 8) | Wd["b1"].astype(int)
    return np.where(fld >= 512, -1.0, 1.0) * (fld & 511)


def bp(x, lo, hi):
    sos = signal.butter(2, [lo, hi], btype="band", fs=100.0, output="sos")
    return signal.sosfiltfilt(sos, x)


# ================= A. D-sign identifiability (judge grid + setpoint rate)
te4 = W["te4"]
tg = np.arange(te4[0] + 1.0, te4[-1] - 1.0, 0.01)
ang = zoh(W["t14"], W["ang"], tg)
raw = zoh(te4, W["cmd"], tg).astype(float)
req = zoh(te4, W["req"], tg) > 0
sca = zoh(W["t18"], W["sca"], tg) > 0
bar = zoh(W["t18"], W["tq"] * 1.024, tg)
v = zoh(W["tcs"], W["vego"], tg)
csr = zoh(W["tcs"], W["cs_rate"], tg)
tap = zoh(W["t1ab"], tapdec(W), tg)
eng = req & sca
rise = np.where(np.r_[eng[0], eng[1:] & ~eng[:-1]], tg, -np.inf)
tse = tg - np.maximum.accumulate(rise)
ew = raw + 10.0 * ang
sp = -raw / 10.0
spd = np.gradient(sp, 0.01)
dang = np.gradient(ang, 0.01)
Iw = np.cumsum(ew) * 0.01
base = eng & (tse >= 1.2) & (np.abs(bar) < 500)
er = np.convolve((~base).astype(float), np.ones(101), "same") == 0
GBv = np.array([714, 1843, 2304, 2707, 4032, 6198]) / 230.4
GBg = np.array([1178, 1465, 760, 560, 1068, 2188])
pr("A. D IDENTIFIABILITY: tap_bp(t+L) = cP*ew + cI*Iw + b*w + c*sp' ; P-timing artefact = 10cP*delta*(w - sp')")
pr("   cD_true = b + c if angle and setpoint share the timing error; d_flip = angle-only lead (ms) of the WIRE angle")
pr("   behind the firmware's angle that would be needed to make cD_true <= 0")
resA = {}
for lo, hi, lab in ((2.0, 5.0, "2-5Hz"), (0.3, 3.0, "0.3-3Hz")):
    fb = {k: bp(x, lo, hi) for k, x in (("ew", ew), ("w", csr), ("dang", dang), ("Iw", Iw), ("tap", tap), ("spd", spd))}
    for wn in ("w", "dang"):
        for vlo, vhi, vb in ((5, 8, "5-8"), (8, 12.5, "8-12.5"), (12.5, 22, "12.5-22"), (22, 99, ">22"), (5, 99, "pooled")):
            m = er & (v >= vlo) & (v < vhi)
            best = None
            rows = []
            for L in range(-4, 9):
                y = np.roll(fb["tap"], -L)[m]
                X = np.c_[fb["ew"][m], fb["Iw"][m], fb[wn][m], fb["spd"][m]]
                c, *_ = np.linalg.lstsq(X, y, rcond=None)
                r2 = 1 - np.var(y - X @ c) / np.var(y)
                X3 = X[:, :3]
                c3, *_ = np.linalg.lstsq(X3, y, rcond=None)
                rows.append((L, r2, c, c3[2]))
                if best is None or r2 > best[1]:
                    best = (L, r2, c, c3[2])
            L, r2, c, b3 = best
            cP, b, cs = c[0], c[2], c[3]
            corr = np.corrcoef(fb[wn][m], fb["spd"][m])[0, 1]
            cdt = b + cs
            dflip = -cdt / (10 * cP) * 1000 if cP > 0 else np.nan
            delta_s = cs / (10 * cP) * 1000 if cP > 0 else np.nan
            allc = [r[2][2] + r[2][3] for r in rows]
            resA[f"{lab}|{wn}|{vb}"] = dict(n_s=float(m.sum() / 100), L_ms=L * 10, r2=float(r2), cP=float(cP), b_w=float(b),
                                             c_sp=float(cs), cD_true=float(cdt), cD_3reg=float(b3), corr_w_sp=float(corr),
                                             delta_sp_ms=float(delta_s), d_flip_ms=float(dflip),
                                             cD_true_over_L=[float(min(allc)), float(max(allc))])
            pr("   %-7s %-4s %-7s n %5.1f s L %3d ms R2 %.3f | b_w %+.3f c_sp %+.3f -> cD_true %+.3f (3-reg %+.3f) | corr(w,sp') %+.2f "
               "| delta_sp %+5.0f ms | d_flip %+5.0f ms | cD_true over L -40..80: %+.2f..%+.2f" % (
                   lab, wn, vb, m.sum() / 100, L * 10, r2, b, cs, cdt, b3, corr, delta_s, dflip, min(allc), max(allc)))
R["A"] = resA

# ---- A2. timing anchors: 0x18F rate vs d(0x14A angle)/dt and carState rate (xcorr lag), and tap step at request drops
w18 = zoh(W["t18"], W["rate"], tg)
mm = eng & (v > 3)


def xlag(a, b, maxlag=30):
    a = a - a.mean()
    b = b - b.mean()
    best = max(range(-maxlag, maxlag + 1), key=lambda k: np.dot(np.roll(a, -k), b))
    return best * 10


A2 = dict(lag_w18_vs_dang_ms=xlag(bp(w18, 0.5, 5)[mm], bp(dang, 0.5, 5)[mm]),
          lag_csr_vs_dang_ms=xlag(bp(csr, 0.5, 5)[mm], bp(dang, 0.5, 5)[mm]),
          sign_w18_vs_dang=float(np.sign(np.corrcoef(bp(w18, 0.5, 5)[mm], bp(dang, 0.5, 5)[mm])[0, 1])))
R["A2"] = A2
pr("A2. timing: positive = first signal LAGS d(ang)/dt by that many ms: %s" % json.dumps(A2))

# ================= B/C. fork axis (carOutput rows), the judge's definitions
tco, co = F["t_co"], F["co_ang"].astype(float)
csa, vr = F["cs_ang"].astype(float), F["cs_vegoraw"].astype(float)
cstq, press, ratecs = F["cs_tq"].astype(float), F["cs_press"] > 0, F["cs_rate"].astype(float)
tcc, ccang, cclat = F["t_cc"], F["cc_ang"].astype(float), F["cc_latActive"]
jcc = np.clip(np.searchsorted(tcc, tco, side="right") - 1, 0, len(tcc) - 1)
lat = cclat[jcc] > 0
s = np.where(np.abs(cstq) > 600, 1.0, np.where(np.abs(cstq) <= 500, 0.0, np.nan))
idx = np.maximum.accumulate(np.where(~np.isnan(s), np.arange(len(s)), 0))
o1 = (np.nan_to_num(s[idx]) > 0) & lat
o1p = o1 | np.r_[False, o1[:-1]]
dco = np.r_[0.0, np.abs(np.diff(co))]
cap = lat & ~o1p & (np.abs(dco - 1.2) <= 1e-3)
hard = lat & ((np.abs(csa) > 30) | (np.abs(ratecs) > 60))
ho = ~o1p & ~press
# O1 episodes: classify by whether |cs_tq| ever exceeded 1200 (steeringPressed's threshold) inside
d = np.diff(np.r_[0, o1.astype(int), 0])
on, off = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
cmax = np.array([np.abs(cstq[a:b]).max() for a, b in zip(on, off)])
pmax = np.array([press[a:b].any() for a, b in zip(on, off)])
dur = (off - on) / 100
o1_hand = np.zeros(len(o1), bool)
for a, b, hm in zip(on, off, cmax > 1200):
    if hm:
        o1_hand[a:b] = True
B = {}
pr("B. hard-manoeuvre DENOMINATOR (latActive & (|ang|>30 | |rate|>60)), fork rows, per band; shares of ALL hard frames")
pr("   band | hard s | O1 % | O1 with |tq|>1200 in-episode % | pressed % | hands-off % | cap(all hard) % | cap(HO hard) %")
for lo, hi, nm in ((0, 5, "<5"), (5, 8, "5-8"), (8, 12.5, "8-12.5"), (12.5, 99, ">12.5"), (0, 99, "all")):
    m = hard & (vr >= lo) & (vr < hi)
    if m.sum() == 0:
        continue
    row = dict(hard_s=m.sum() / 100, o1=100 * o1[m].mean(), o1_hand=100 * o1_hand[m].mean(), pressed=100 * press[m].mean(),
               ho=100 * ho[m].mean(), cap_all=100 * cap[m].mean(), cap_ho=100 * cap[m & ho].mean() if (m & ho).any() else np.nan)
    B[nm] = row
    pr("   %-7s %6.1f | %5.1f | %5.1f | %5.1f | %5.1f | %5.1f | %5.1f" % (nm, row["hard_s"], row["o1"], row["o1_hand"], row["pressed"],
                                                                     row["ho"], row["cap_all"], row["cap_ho"]))
B["o1_episodes"] = dict(n=int(len(on)), time_s=float(dur.sum()), hand_like_n=int((cmax > 1200).sum()),
                        hand_like_time_s=float(dur[cmax > 1200].sum()), pressed_n=int(pmax.sum()),
                        pressed_time_s=float(dur[pmax].sum()), short_le50_time_s=float(dur[dur <= 0.05].sum()),
                        o1_time_in_hard_s=float((o1 & hard).sum() / 100),
                        o1_hand_time_in_hard_s=float((o1_hand & hard).sum() / 100))
pr("   O1 episodes: %s" % json.dumps(B["o1_episodes"]))
R["B"] = B

# C. cap downstream of O1?
last_off = np.full(len(o1), -1e9)
rel = np.r_[False, o1[:-1] & ~o1[1:]]
tt = np.arange(len(o1)) / 100.0
last_off = np.maximum.accumulate(np.where(rel, tt, -1e9))
since = tt - last_off
mc = cap & hard & ho
Cc = dict(cap_ho_hard_s=float(mc.sum() / 100),
          frac_within_0p5s_of_O1_release=float(np.mean(since[mc] <= 0.5)),
          frac_within_1s=float(np.mean(since[mc] <= 1.0)),
          base_ho_hard_within_0p5=float(np.mean(since[hard & ho] <= 0.5)))
# wheel keeping up inside cap runs >= 0.3 s: wheel rate along the setpoint direction / 120, and |err| growth
rc = C.runs(cap & lat, 30)
csa_p = np.r_[csa[0], csa[:-1]]
err_fork = co - csa_p
ratios, growth, errs = [], [], []
for a, b in rc:
    dirn = np.sign(co[b - 1] - co[a])
    ratios.append(np.median(dirn * ratecs[a:b]) / 120.0)
    growth.append((abs(err_fork[b - 1]) - abs(err_fork[a])) / ((b - a) / 100))
    errs.append(np.median(np.abs(err_fork[a:b])))
Cc.update(n_cap_runs_ge0p3s=int(len(rc)), wheel_rate_over_120_p50=float(np.median(ratios)) if ratios else np.nan,
          wheel_rate_over_120_p10=float(np.percentile(ratios, 10)) if ratios else np.nan,
          err_growth_deg_per_s_p50=float(np.median(growth)) if growth else np.nan,
          err_median_in_run_p50=float(np.median(errs)) if errs else np.nan)
R["C"] = Cc
pr("C. cap vs O1 and wheel follow-up: %s" % json.dumps(Cc))

# ================= D. ratchet: stall-surge per band, split by a bar spike > 614 (wire) within +-0.5 s, ALL routes
D = {}
pr("D. STALL-SURGE /min of turning (M4 detector), split by |bar| > 614 within +-0.5 s (O1's trip level), same mask on every route")
pr("   route   band | spike-free: turn s, n, /min | spike-near: turn s, n, /min")
for tag in ("r79_a1f5d2_al", "r6c", "r39", "r71b_v294"):
    G = C.build_grid(tag)
    ss = EP.stall_surge(G, G["eng"])
    spike = np.abs(G["bar"]) > 614
    near = np.convolve(spike.astype(float), np.ones(101), "same") > 0
    Rs = ss["R"]
    vv = G["vego"]
    D[tag] = {}
    for nm, lo, hi in (("0-5", 0, 5), ("5-10", 5, 10), ("10-20", 10, 20)):
        res = {}
        for lab, msk in (("free", ~near), ("near", near)):
            tb = ss["turn"] & msk & (vv >= lo) & (vv < hi)
            sel = (vv[Rs[:, 0]] >= lo) & (vv[Rs[:, 0]] < hi) & msk[Rs[:, 0]] if len(Rs) else np.zeros(0, bool)
            secs = tb.sum() / 100
            res[lab] = (round(secs, 1), int(sel.sum()), round(60 * sel.sum() / secs, 1) if secs > 5 else None)
        D[tag][nm] = res
        pr("   %-12s %-6s | %s | %s" % (tag[:12], nm, res["free"], res["near"]))
R["D"] = D

# D2. the same split on r79 with the RECONSTRUCTED O1 (fork) instead of the wire spike
G = C.build_grid("r79_a1f5d2_al")
o1g = zoh(tco, o1.astype(float), G["t"]) > 0
capg = zoh(tco, cap.astype(float), G["t"]) > 0
ss = EP.stall_surge(G, G["eng"])
Rs, vv = ss["R"], G["vego"]
D2 = {}
for lab, near in (("O1+-0.5s", np.convolve(o1g.astype(float), np.ones(101), "same") > 0),
                  ("cap+-0.5s", np.convolve(capg.astype(float), np.ones(101), "same") > 0)):
    for nm, lo, hi in (("0-5", 0, 5), ("5-10", 5, 10)):
        out = {}
        for k, msk in (("free", ~near), ("near", near)):
            tb = ss["turn"] & msk & (vv >= lo) & (vv < hi)
            sel = (vv[Rs[:, 0]] >= lo) & (vv[Rs[:, 0]] < hi) & msk[Rs[:, 0]]
            secs = tb.sum() / 100
            out[k] = (round(secs, 1), int(sel.sum()), round(60 * sel.sum() / secs, 1) if secs > 5 else None)
        D2[f"{lab}|{nm}"] = out
        pr("D2. r79 split by %-9s %-5s | free %s | near %s" % (lab, nm, out["free"], out["near"]))
R["D2"] = D2

# ================= E. what was true at the peak-tap frames
me = eng & (v > 0.5)
thr = np.percentile(np.abs(tap[me]), 99)
pk = me & (np.abs(tap) >= thr)
o1w = zoh(tco, o1.astype(float), tg) > 0
capw = zoh(tco, cap.astype(float), tg) > 0
prs = zoh(F["t_cs"], press.astype(float), tg) > 0
errd = sp - ang
E = dict(tap_p99=float(thr), n_s=float(pk.sum() / 100), v_p50=float(np.median(v[pk])),
         abs_err_p50=float(np.median(np.abs(errd[pk]))), abs_err_p90=float(np.percentile(np.abs(errd[pk]), 90)),
         o1_frac=float(o1w[pk].mean()), cap_frac=float(capw[pk].mean()), pressed_frac=float(prs[pk].mean()),
         bar_gt512_frac=float(np.mean(np.abs(bar[pk]) > 512)),
         tap_pushes_same_way_as_bar=float(np.mean(np.sign(tap[pk]) == -np.sign(bar[pk]))))
R["E"] = E
pr("E. top-1%% |tap| engaged frames: %s" % json.dumps(E))

# ================= A3. R2 vs L (pooled, 2-5 Hz, csr) and a sign-aware timing xcorr of the 0x18F rate
fb = {k: bp(x, 2.0, 5.0) for k, x in (("ew", ew), ("w", csr), ("Iw", Iw), ("tap", tap), ("spd", spd))}
m = er & (v >= 5)
A3 = []
for L in range(-6, 11):
    y = np.roll(fb["tap"], -L)[m]
    X = np.c_[fb["ew"][m], fb["Iw"][m], fb["w"][m], fb["spd"][m]]
    c, *_ = np.linalg.lstsq(X, y, rcond=None)
    A3.append((L * 10, round(float(1 - np.var(y - X @ c) / np.var(y)), 3), round(float(c[2] + c[3]), 3)))
R["A3"] = A3
pr("A3. pooled 2-5 Hz, (L ms, R2, cD_true): %s" % A3)


def xlag_abs(a, b, maxlag=30):
    a = a - a.mean()
    b = b - b.mean()
    ks = list(range(-maxlag, maxlag + 1))
    vals = [np.dot(np.roll(a, -k), b) for k in ks]
    k = int(np.argmax(np.abs(vals)))
    return ks[k] * 10, float(np.sign(vals[k]))


mm2 = eng & (v > 3)
R["A2b"] = dict(w18_vs_dang=xlag_abs(bp(w18, 0.5, 5)[mm2], bp(dang, 0.5, 5)[mm2]),
                csr_vs_dang=xlag_abs(bp(csr, 0.5, 5)[mm2], bp(dang, 0.5, 5)[mm2]),
                tap_vs_ew_0p3_3=xlag_abs(bp(tap, 0.3, 3)[mm2 & (np.abs(bar) < 500)], bp(ew, 0.3, 3)[mm2 & (np.abs(bar) < 500)]))
pr("A2b. sign-aware xcorr (lag ms where first lags second if > 0 ... (lag, sign)): %s" % json.dumps(R["A2b"]))

# ================= F. what precedes the 70 hand (pressed) O1 episodes in hard manoeuvres
gap_des = np.abs(ccang[np.clip(jcc - 1, 0, len(ccang) - 1)] - co)       # desired (carControl before latest) - applied
Fh = []
for a, b, hm in zip(on, off, cmax > 1200):
    if not hm or not hard[a:b].any():
        continue
    pre = slice(max(a - 50, 0), a)
    Fh.append((float(np.max(gap_des[pre])), float(np.max(np.abs(err_fork[pre]))), float(cap[pre].mean()),
               float(np.sign(cstq[a]) == -np.sign(co[a] - csa_p[a])) if abs(co[a] - csa_p[a]) > 0.5 else np.nan,
               float((b - a) / 100)))
Fh = np.array(Fh)
Fr = dict(n=int(len(Fh)), pre_desired_minus_applied_p50=float(np.median(Fh[:, 0])), pre_gap_gt10deg=float(np.mean(Fh[:, 0] > 10)),
          pre_fw_err_p50=float(np.median(Fh[:, 1])), pre_cap_duty_p50=float(np.median(Fh[:, 2])),
          pre_cap_any=float(np.mean(Fh[:, 2] > 0)), dur_p50=float(np.median(Fh[:, 4])))
R["F"] = Fr
pr("F. 0.5 s BEFORE each hand-like O1 episode touching a hard manoeuvre: %s" % json.dumps(Fr))
# base: same stats on random hard latActive non-O1 frames
hb = np.flatnonzero(hard & ~o1p & lat)
rng = np.random.default_rng(3)
pick = rng.choice(hb, size=min(400, len(hb)), replace=False)
R["F_base"] = dict(desired_minus_applied_p50=float(np.median([gap_des[max(i - 50, 0):i + 1].max() for i in pick])),
                   gap_gt10=float(np.mean([gap_des[max(i - 50, 0):i + 1].max() > 10 for i in pick])),
                   cap_any=float(np.mean([cap[max(i - 50, 0):i + 1].any() for i in pick])))
pr("   base (random hard non-O1 frames, same 0.5 s window): %s" % json.dumps(R["F_base"]))

# ================= C2. tap and error inside cap runs (is the firmware the binder while the wheel falls behind?)
tapf = zoh(W["t1ab"], tapdec(W), tco)
C2 = [(float(np.median(np.abs(tapf[a:b]))), float(np.max(np.abs(tapf[a:b]))), float(np.median(np.abs(err_fork[a:b]))),
       float(np.median(vr[a:b]))) for a, b in rc]
R["C2"] = C2
pr("C2. cap runs >= 0.3 s: (|tap| p50, |tap| max, |err| p50, v): %s" % [tuple(round(x, 1) for x in r) for r in C2])

# ================= D3. stall-surge vs a FAST SETPOINT (|d sp/dt| >= 100 deg/s within +-0.5 s) on every route (no cap on refs)
pr("D3. stall-surge /min of turning, split by fast setpoint (|0.1 s mean d sp/dt| >= 100 deg/s within +-0.5 s)")
D3 = {}
for tag in ("r79_a1f5d2_al", "r6c", "r39", "r71b_v294"):
    G = C.build_grid(tag)
    ss = EP.stall_surge(G, G["eng"])
    spr = np.abs(np.convolve(np.gradient(G["theta_sp"], 0.01), np.ones(10) / 10, "same"))
    near = np.convolve((spr >= 100).astype(float), np.ones(101), "same") > 0
    Rs, vv = ss["R"], G["vego"]
    D3[tag] = {}
    for nm, lo, hi in (("0-5", 0, 5), ("5-10", 5, 10)):
        res = {}
        for lab, msk in (("slow", ~near), ("fast", near)):
            tb = ss["turn"] & msk & (vv >= lo) & (vv < hi)
            sel = (vv[Rs[:, 0]] >= lo) & (vv[Rs[:, 0]] < hi) & msk[Rs[:, 0]]
            secs = tb.sum() / 100
            res[lab] = (round(float(secs), 1), int(sel.sum()), round(float(60 * sel.sum() / secs), 1) if secs > 5 else None)
        D3[tag][nm] = res
        pr("   %-12s %-5s | slow %s | fast %s" % (tag[:12], nm, res["slow"], res["fast"]))
R["D3"] = D3

# ================= D4. r79 stall-surge split by an integrator-freeze toggle (V298 predicates on the wire) within +-0.25 s
G = C.build_grid("r79_a1f5d2_al")
ss = EP.stall_surge(G, G["eng"])
Rs, vv = ss["R"], G["vego"]
fz, fzh, fzo = EP.freeze_states(G)
tog = np.r_[False, fz[1:] != fz[:-1]] & G["eng"]
o1g = zoh(tco, o1.astype(float), G["t"]) > 0
o1near = np.convolve(o1g.astype(float), np.ones(101), "same") > 0
D4 = {}
for lab, near in (("toggle+-0.25s", np.convolve(tog.astype(float), np.ones(51), "same") > 0),
                  ("opp-only(300<|bar|<=512)+-0.25s", np.convolve((fzo & ~fzh).astype(float), np.ones(51), "same") > 0)):
    for nm, lo, hi in (("0-5", 0, 5), ("5-10", 5, 10)):
        out = {}
        for k, msk in (("free", ~near), ("near", near), ("near&O1free", near & ~o1near), ("free&O1free", ~near & ~o1near)):
            tb = ss["turn"] & msk & (vv >= lo) & (vv < hi)
            sel = (vv[Rs[:, 0]] >= lo) & (vv[Rs[:, 0]] < hi) & msk[Rs[:, 0]]
            secs = tb.sum() / 100
            out[k] = (round(float(secs), 1), int(sel.sum()), round(float(60 * sel.sum() / secs), 1) if secs > 3 else None)
        D4[f"{lab}|{nm}"] = out
        pr("D4. r79 %-32s %-5s %s" % (lab, nm, out))
R["D4"] = D4
# r79 vs refs at 5-10: the bar level during turning (is r79's turning more hands-on / twistier?)
for tag in ("r79_a1f5d2_al", "r6c", "r39", "r71b_v294"):
    Gx = C.build_grid(tag)
    ssx = EP.stall_surge(Gx, Gx["eng"])
    mt = ssx["turn"] & (Gx["vego"] >= 5) & (Gx["vego"] < 10)
    pr("D5. %-12s 5-10 turning %.1f s: |bar| p50/p90 %.0f/%.0f ; |w18| p50 %.0f ; frac |bar|>614 %.2f" % (
        tag[:12], mt.sum() / 100, np.percentile(np.abs(Gx["bar"][mt]), 50), np.percentile(np.abs(Gx["bar"][mt]), 90),
        np.percentile(np.abs(Gx["w18"][mt]), 50), np.mean(np.abs(Gx["bar"][mt]) > 614)))

# ================= D6. CONTROL for reverse causality: the same "freeze-like threshold crossing" split on the refs (no freeze there)
pr("D6. stall-surge /min of turning split by a crossing of |bar| 300 or 512 (wire) within +-0.25 s -- refs have no freeze: control")
D6 = {}
for tag in ("r79_a1f5d2_al", "r6c", "r39", "r71b_v294"):
    Gx = C.build_grid(tag)
    ssx = EP.stall_surge(Gx, Gx["eng"])
    b = np.abs(Gx["bar"])
    x300, x512 = b > 300, b > 512
    crs = (np.r_[False, x300[1:] != x300[:-1]] | np.r_[False, x512[1:] != x512[:-1]]) & Gx["eng"]
    near = np.convolve(crs.astype(float), np.ones(51), "same") > 0
    Rs, vv = ssx["R"], Gx["vego"]
    D6[tag] = {}
    for nm, lo, hi in (("0-5", 0, 5), ("5-10", 5, 10)):
        out = {}
        for k, msk in (("free", ~near), ("near", near)):
            tb = ssx["turn"] & msk & (vv >= lo) & (vv < hi)
            sel = (vv[Rs[:, 0]] >= lo) & (vv[Rs[:, 0]] < hi) & msk[Rs[:, 0]]
            secs = tb.sum() / 100
            out[k] = (round(float(secs), 1), int(sel.sum()), round(float(60 * sel.sum() / secs), 1) if secs > 3 else None)
        D6[tag][nm] = out
        pr("   %-12s %-5s %s" % (tag[:12], nm, out))
R["D6"] = D6

# ================= G. context of the hard manoeuvres: openpilot engaged vs always-on-lateral only; blinkers
tco_ = F["t_co"]
sde = zoh(F["t_sd"], F["sd_enabled"].astype(float), tco_) > 0
blk = (F["cs_lblink"] > 0) | (F["cs_rblink"] > 0)
Gc = {}
for nm, msk in (("hard", hard), ("hard&HO", hard & ho), ("hard&pressed", hard & press), ("hard&cap", hard & cap)):
    Gc[nm] = dict(s=float(msk.sum() / 100), sd_enabled=float(sde[msk].mean()), blinker=float(blk[msk].mean()),
                  pressed=float(press[msk].mean()))
Gc["latActive_all"] = dict(s=float(lat.sum() / 100), sd_enabled=float(sde[lat].mean()), blinker=float(blk[lat].mean()))
R["G"] = Gc
pr("G. context: %s" % json.dumps(Gc))

# ================= H. net lane drive along the motion during fast hands-off slews, split wind-up vs unwind
# tap sign convention: + tap = torque toward -theta (right); c_D > 0 = opposes; so drive along the motion = -tap*sign(w)
o1w2 = zoh(tco, o1p.astype(float), tg) > 0
prsw = zoh(F["t_cs"], press.astype(float), tg) > 0
H = {}
for lo_w, nm in ((60, "|w|>60"), (90, "|w|>90")):
    for vlo, vhi, vb in ((0, 5, "<5"), (5, 10, "5-10"), (10, 99, ">10")):
        for dirn in ("windup", "unwind"):
            wind = (np.sign(csr) == np.sign(ang)) if dirn == "windup" else (np.sign(csr) != np.sign(ang))
            m = eng & ~o1w2 & ~prsw & (np.abs(bar) < 500) & (np.abs(csr) > lo_w) & (v >= vlo) & (v < vhi) & wind & (np.abs(ang) > 5)
            if m.sum() < 20:
                continue
            sgn = np.sign(csr[m])
            drive = -tap[m] * sgn
            e_al = errd[m] * sgn
            row = dict(s=float(m.sum() / 100), w_p50=float(np.median(np.abs(csr[m]))), drive_tap_p50=float(np.median(drive)),
                       drive_pos_frac=float(np.mean(drive > 0)), err_along_p50=float(np.median(e_al)),
                       D_at_0p45=float(np.median(0.45 * np.abs(csr[m]))), D_at_0p566=float(np.median(0.566 * np.abs(csr[m]))))
            H[f"{nm}|{vb}|{dirn}"] = row
            pr("H. %-6s %-4s %-6s %s" % (nm, vb, dirn, json.dumps({k: round(x, 2) for k, x in row.items()})))
R["H"] = H

# ================= B2. what the judge's HO-hard and cap frames ARE: wind-up (turn-in), unwind (return), hold
wu = (np.abs(ratecs) > 10) & (np.sign(ratecs) == np.sign(csa))
uw = (np.abs(ratecs) > 10) & (np.sign(ratecs) != np.sign(csa))
hd = np.abs(ratecs) <= 10
B2 = {}
for nm, msk in (("hard", hard), ("hard&HO", hard & ho), ("hard&HO&cap", hard & ho & cap), ("hard&O1hand", hard & o1_hand),
                ("hard&HO&v<8", hard & ho & (vr < 8)), ("hard&HO&cap&v<8", hard & ho & cap & (vr < 8))):
    B2[nm] = dict(s=float(msk.sum() / 100), windup=float(wu[msk].mean()), unwind=float(uw[msk].mean()), hold=float(hd[msk].mean()))
    pr("B2. %-18s %s" % (nm, json.dumps({k: round(x, 3) for k, x in B2[nm].items()})))
R["B2"] = B2

R["wall_s"] = time.time() - T0
pr("wall %.1f s" % R["wall_s"])
(OUT / "refute_inference.json").write_text(json.dumps(R, indent=1, default=float))
(OUT / "refute_inference.txt").write_text("\n".join(lines))
