"""Synthesis-judge crux checks on route 79 (V298). Cache only, vectorised; target < 30 s.
Re-derives, independently of the M1-M6 code, the decision-bearing numbers the reports disagree on:
 A. D sign (2-5 Hz band-pass regression; omega from carState steeringRateDeg = 0x14A STEER_ANGLE_RATE, and d(ang)/dt)
 B. camera 0xE4: forwarded to bus 0? reached bus 1?
 C. fork error clip: binding vs 'demand beyond the clip'
 D. fork 120 deg/s rate cap binding
 E. tap peak vs rail, and the references
 F. O1 override share by band
 G. torque-bar pinned fraction (source formula)
"""
import time, json
import numpy as np
from scipy import signal
from pathlib import Path
T0 = time.time()
C = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v280")
OUT = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/_scratch/out/r79/judge")
OUT.mkdir(parents=True, exist_ok=True)
W = dict(np.load(C / "r79_a1f5d2_al.npz"))
F = dict(np.load(C / "r79_fork.npz"))
R = {}


def zoh(ts, x, t):
    j = np.searchsorted(ts, t, side="right") - 1
    return np.asarray(x)[np.clip(j, 0, len(x) - 1)]


def tapdec(Wd):
    fld = ((Wd["b0"].astype(int) & 3) << 8) | Wd["b1"].astype(int)
    return np.where(fld >= 512, -1.0, 1.0) * (fld & 511)


lines = []


def pr(s):
    print(s)
    lines.append(s)


# ---------------- grid
te4 = W["te4"]
tg = np.arange(te4[0] + 1.0, te4[-1] - 1.0, 0.01)
ang = zoh(W["t14"], W["ang"], tg)
raw = zoh(te4, W["cmd"], tg)
req = zoh(te4, W["req"], tg) > 0
sca = zoh(W["t18"], W["sca"], tg) > 0
bar = zoh(W["t18"], W["tq"] * 1.024, tg)
v = zoh(W["tcs"], W["vego"], tg)
csr = zoh(W["tcs"], W["cs_rate"], tg)              # carState steeringRateDeg (0x14A rate), + left
tap = zoh(W["t1ab"], tapdec(W), tg)
eng = req & sca
rise = np.where(np.r_[eng[0], eng[1:] & ~eng[:-1]], tg, -np.inf)
tse = tg - np.maximum.accumulate(rise)
ew = raw + 10.0 * ang                              # = -10 (theta_sp - theta), wire counts
dang = np.gradient(ang, 0.01)


# ---------------- A. D sign
def bp(x, lo, hi):
    sos = signal.butter(2, [lo, hi], btype="band", fs=100.0, output="sos")
    return signal.sosfiltfilt(sos, x)


base = eng & (tse >= 1.2) & (np.abs(bar) < 500)
er = np.convolve((~base).astype(float), np.ones(101), "same") == 0     # eroded 0.5 s each side
GBv = np.array([714, 1843, 2304, 2707, 4032, 6198]) / 230.4
GBg = np.array([1178, 1465, 760, 560, 1068, 2188])
pr("A. D SIGN: tap_bp(t+L) = cP*ew_bp + cI*Iw_bp + cD*omega_bp, hands-off engaged settled (|bar|<500, >=1.2 s, eroded 0.5 s)")
pr("   design c_D = 0.566 tap/(deg/s), > 0 = OPPOSES motion; design c_P = 5.477e-4*G tap per wire count")
Iw = np.cumsum(ew) * 0.01
resA = {}
for band_lo, band_hi, lab in ((2.0, 5.0, "2-5Hz"), (0.3, 3.0, "0.3-3Hz")):
    fbp = {k: bp(x, band_lo, band_hi) for k, x in (("ew", ew), ("csr", csr), ("dang", dang), ("Iw", Iw), ("tap", tap))}
    for wname in ("csr", "dang"):
        for vlo, vhi, vb in ((5, 8, "5-8"), (8, 12.5, "8-12.5"), (12.5, 22, "12.5-22"), (22, 99, ">22"), (5, 99, "pooled>5")):
            m = er & (v >= vlo) & (v < vhi)
            best = None
            cds = []
            for L in range(0, 9):                          # 0..80 ms, tap lags the regressors
                y = np.roll(fbp["tap"], -L)[m]
                X = np.c_[fbp["ew"][m], fbp["Iw"][m], fbp[wname][m]]
                c, *_ = np.linalg.lstsq(X, y, rcond=None)
                r2 = 1 - np.var(y - X @ c) / np.var(y)
                cds.append(c[2])
                if best is None or r2 > best[0]:
                    best = (r2, L, c)
            Gm = float(np.mean(np.interp(v[m], GBv, GBg)))
            resA[f"{lab}|{wname}|{vb}"] = dict(n_s=int(m.sum()) / 100, L_ms=best[1] * 10, r2=best[0],
                                               cP_ratio=best[2][0] / (5.477e-4 * Gm),
                                               cI_over_cP=best[2][1] / best[2][0], cD=best[2][2], cD_all_L=[min(cds), max(cds)])
            pr("   %-7s w=%-4s %-9s n %6.1f s  bestL %2d ms R2 %.3f  cP/design %.2f  cI/cP %5.2f  cD %+.3f  (cD over L 0-80 ms: %+.3f..%+.3f)" % (
                lab, wname, vb, m.sum() / 100, best[1] * 10, best[0], best[2][0] / (5.477e-4 * Gm), best[2][1] / best[2][0],
                best[2][2], min(cds), max(cds)))
R["A"] = resA

# ---------------- B. camera
t_cam, cam_req, cam_arm = F["t_e4cam"], F["e4cam_req"], F["e4cam_arm"]
tx0 = F["t_e4tx0"]
tx0_req = F["e4tx0_req"]
rx1 = F["t_e4rx1"]
B = dict(cam_frames=int(len(t_cam)), cam_req1=int(cam_req.sum()), cam_req1_arm_vals=sorted(set(cam_arm[cam_req > 0].tolist())),
         tx0_frames=int(len(tx0)), tx0_req1=int(tx0_req.sum()), rx1_frames=int(len(rx1)),
         rx1_last_t=float(rx1.max()) if len(rx1) else None, tx1_arm_vals=sorted(set(F["e4tx1_arm"].tolist())))
cr = t_cam[cam_req > 0]
B["cam_req1_span"] = [float(cr.min()), float(cr.max())] if len(cr) else None
R["B"] = B
pr("B. CAMERA: %s" % json.dumps(B))

# ---------------- C/D/F. fork limiter census (carOutput rows)
tco, co = F["t_co"], F["co_ang"]
tcs, csa = F["t_cs"], F["cs_ang"]
vr = F["cs_vegoraw"]
cstq = F["cs_tq"]
press = F["cs_press"]
tcc = F["t_cc"]
ccang = F["cc_ang"]
cclat = F["cc_latActive"]
assert len(tco) == len(tcs)
BP = [3.1, 8.0, 10.0, 11.75, 17.5, 26.9]
EV = [17.0, 15.5, 19.5, 17.0, 8.5, 4.5]
jcc = np.clip(np.searchsorted(tcc, tco, side="right") - 1, 0, len(tcc) - 1)
lat = cclat[jcc] > 0
cc_now = ccang[jcc]
emax_i = np.interp(vr, BP, EV)
ex_i = np.abs(co - csa) - emax_i
ex_im1 = np.abs(co[1:] - csa[:-1]) - emax_i[:-1]
pr("C. pairing: max(|co-cs|-emax) pair i: %.4f ; pair i-1: %.4f  (latActive)" % (ex_i[lat].max(), ex_im1[lat[1:]].max()))
s = np.where(np.abs(cstq) > 600, 1.0, np.where(np.abs(cstq) <= 500, 0.0, np.nan))
idx = np.where(~np.isnan(s), np.arange(len(s)), 0)
idx = np.maximum.accumulate(idx)
o1 = (np.nan_to_num(s[idx]) > 0) & lat
# the real pairing is carOutput i <- carState i-1 (pair i never touches the bound; pair i-1 does, max excess 0.0000)
csa_p = np.r_[csa[0], csa[:-1]]
emax_p = np.r_[emax_i[0], emax_i[:-1]]
bind_clip = lat & (np.abs(co - csa_p) - emax_p >= -1e-3)
beyond = lat & (np.abs(cc_now - csa_p) > emax_p)
dco = np.r_[0.0, np.abs(np.diff(co))]
o1p = o1 | np.r_[False, o1[:-1]]
cap = lat & ~o1p & (dco >= 1.2 - 1e-3) & (dco <= 1.2 + 1e-3)
ratecs = F["cs_rate"]
hard = lat & ((np.abs(csa) > 30) | (np.abs(ratecs) > 60))
ho = ~o1p & (press == 0)
rows = []
pr("C/D/F. per band (latActive carOutput rows): s | clip binding % | demand beyond clip % | 120-cap step % (no O1) | O1 % | hard&HO s | hard&HO: cap % clip % beyond %")
for lo, hi, nm in ((0, 5, "<5"), (5, 8, "5-8"), (8, 12.5, "8-12.5"), (12.5, 22, "12.5-22"), (22, 99, ">22"), (0, 99, "all")):
    m = lat & (vr >= lo) & (vr < hi)
    mh = m & hard & ho
    row = dict(band=nm, s=m.sum() / 100, clip=100 * bind_clip[m].mean(), beyond=100 * beyond[m].mean(), cap=100 * cap[m].mean(),
               o1=100 * o1[m].mean(), hard_ho_s=mh.sum() / 100,
               hard_ho_cap=100 * cap[mh].mean() if mh.any() else np.nan,
               hard_ho_clip=100 * bind_clip[mh].mean() if mh.any() else np.nan,
               hard_ho_beyond=100 * beyond[mh].mean() if mh.any() else np.nan)
    rows.append(row)
    pr("   %-8s %6.1f s | %5.2f | %5.1f | %5.1f | %5.1f | %5.1f s | %5.1f %5.2f %5.1f" % (
        nm, row["s"], row["clip"], row["beyond"], row["cap"], row["o1"], row["hard_ho_s"], row["hard_ho_cap"], row["hard_ho_clip"], row["hard_ho_beyond"]))
R["CDF"] = rows
d = np.diff(np.r_[0, o1.astype(int), 0])
on, off = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
dur = (off - on) / 100
R["O1"] = dict(episodes=int(len(on)), total_s=float(dur.sum()), p50=float(np.median(dur)), le50ms=float(np.mean(dur <= 0.05)),
               not_pressed=int(sum(1 for a, b in zip(on, off) if press[a:b].max() == 0)))
pr("F. O1 episodes %d, total %.1f s, dur p50 %.2f s, <=50 ms %.2f, never steeringPressed %d" % (
    len(on), dur.sum(), np.median(dur), np.mean(dur <= 0.05), R["O1"]["not_pressed"]))


# ---------------- E. tap peak
def tap_stats(Wd, name):
    tg2 = np.arange(Wd["te4"][0] + 1, Wd["te4"][-1] - 1, 0.02)
    e2 = (zoh(Wd["te4"], Wd["req"], tg2) > 0) & (zoh(Wd["t18"], Wd["sca"], tg2) > 0)
    tp = np.abs(zoh(Wd["t1ab"], tapdec(Wd), tg2))[e2]
    return dict(route=name, eng_s=float(e2.sum() * 0.02), pk=float(tp.max()), p99=float(np.percentile(tp, 99)), ge300=int((tp >= 300).sum()))


E = [tap_stats(W, "r79 V298")]
for nm in ("r6c", "r39", "r71b_v294"):
    try:
        E.append(tap_stats(dict(np.load(C / f"{nm}.npz")), nm))
    except Exception as ex:
        E.append(dict(route=nm, err=str(ex)))
R["E"] = E
for e in E:
    pr("E. tap " + json.dumps(e))

# ---------------- G. torque bar (source formula, torque_bar.py TorqueBar._update_state; unfiltered x)
tctl = F["t_ctl"]
kap, kd = F["ctl_curv"], F["ctl_dcurv"]
vv = zoh(tcs, F["cs_vego"], tctl)
roll = zoh(F["t_lp"], F["lp_roll"], tctl)
lat_c = F["cc_latActive"][np.clip(np.searchsorted(tcc, tctl, side="right") - 1, 0, len(tcc) - 1)] > 0
aact, ades = kap * vv ** 2, kd * vv ** 2
rollc = roll * 9.81 * np.interp(vv, [5, 15], [0, 1])
x = np.clip(((aact - rollc) + (ades - aact)) / 0.32467, -1, 1)
ereq = (zoh(te4, W["req"], tctl) > 0) & (zoh(W["t18"], W["sca"], tctl) > 0)
mm = lat_c & ereq & (vv > 3)
tpc = zoh(W["t1ab"], tapdec(W), tctl)
G = dict(eng_s=float(mm.sum() / 100), pinned=float(np.mean(np.abs(x[mm]) >= 0.999)),
         pinned_no_roll=float(np.mean(np.abs(np.clip(ades / 0.32467, -1, 1)[mm]) >= 0.999)),
         corr_abs=float(np.corrcoef(np.abs(x[mm]), np.abs(tpc[mm]))[0, 1]),
         corr_abs_at3_noroll=float(np.corrcoef(np.abs(np.clip(ades / 3.0, -1, 1)[mm]), np.abs(tpc[mm]))[0, 1]),
         p_bar09_given_tap_lt25=float(np.mean(np.abs(x[mm & (np.abs(tpc) < 25)]) >= 0.9)))
R["G"] = G
pr("G. bar " + json.dumps(G))
ps = F["ps_txblocked"]
tps = F["t_ps"]
st = np.flatnonzero(np.diff(ps) != 0)
R["ps_steps"] = [(float(tps[i + 1]), int(ps[i]), int(ps[i + 1])) for i in st]
pr("ps_txblocked steps: %s" % R["ps_steps"])
R["wall_s"] = time.time() - T0
pr("wall %.1f s" % R["wall_s"])
(OUT / "judge_verify.json").write_text(json.dumps(R, indent=1, default=float))
(OUT / "judge_verify.txt").write_text("\n".join(lines))
