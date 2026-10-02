# -*- coding: utf-8 -*-
r"""cf_fork_r79.py -- D2 (FORK-FIRST) route-79 COUNTERFACTUALS for the V299 design round.

ANALYSIS ONLY: reads the route-79 caches (r79_fork.npz, r79_a1f5d2_al.npz, _scratch/v299_D2/x1ab_r79.npz); writes
_scratch/v299_D2/cf_fork_r79.{txt,json}.  Vectorised; the only time recursion (the fork's rate limiter) runs over the
hard-manoeuvre WINDOWS (dilated 1.5 s), never over the 20-minute route.

A. O1 GATE: how many of the 415 recorded O1 episodes survive each candidate gate, how much time, and whether every
   steeringPressed (hand > 1200) episode is still caught, and how late (EVIDENCE: recorded |carState torque|).
B. LIMITER RE-RUN on the recorded desired angle and the recorded wheel (OPEN LOOP: the wheel is NOT re-simulated):
   cap / clip / O1 / re-slew shares and the P tap the V298 stiffness would deliver on the counterfactual error.
   The baseline config is first proved equal to the published carOutput angle (validation).
C. BAR: the current angle-mode bar vs the proposed bar = signed 0x1AB lane torque / 2461.

Timing / pairing conventions are m4_common.limiter_reconstruct's (EVIDENCE there: 100 % / 99.994 % reproduction):
carOutput row i is computed from carState row i-1 and the carControl BEFORE the latest one.
"""
from __future__ import annotations

import json
import math
import time

import numpy as np

import d2_common as C

T0 = time.perf_counter()
L = []
R = {}


def pr(s=""):
    L.append(s)
    print(s, flush=True)


F = dict(np.load(C.CACHE / "r79_fork.npz"))
W = dict(np.load(C.CACHE / "r79_a1f5d2_al.npz"))
t = F["t_co"]
n = len(t)
jc = np.clip(np.searchsorted(F["t_cc"], t, side="right") - 2, 0, len(F["t_cc"]) - 1)
lat = F["cc_latActive"][jc].astype(bool)
des = F["cc_ang"][jc].astype(float)
sh = lambda x: np.r_[x[:1], x[:-1]].astype(float)  # noqa: E731
th, rate, tqs = sh(F["cs_ang"]), sh(F["cs_rate"]), sh(F["cs_tq"])
tq = np.abs(tqs)
vraw = sh(F["cs_vegoraw"])
press = F["cs_press"].astype(bool)
co = F["co_ang"].astype(float)
hard = lat & ((np.abs(F["cs_ang"]) > 30) | (np.abs(F["cs_rate"]) > 60))


def hyst(set_, reset, lat_):
    ev = np.full(n, -1, np.int8)
    ev[reset] = 0
    ev[set_] = 1
    ev[~lat_] = 0
    idx = np.where(ev >= 0, np.arange(n), -1)
    last = np.maximum.accumulate(idx)
    return np.where(last >= 0, ev[np.maximum(last, 0)], 0).astype(bool) & lat_


def runlen(mask):
    """length of the current run of True ending at each frame (vectorised)."""
    m = mask.astype(np.int64)
    c = np.cumsum(m)
    z = np.where(m == 0, c, 0)
    return c - np.maximum.accumulate(z)


def episodes(mask):
    d = np.diff(np.r_[0, mask.astype(np.int8), 0])
    return np.flatnonzero(d == 1), np.flatnonzero(d == -1)


# =====================================================================================================================
# A. O1 GATES
# =====================================================================================================================
pr("A. O1 GATE COUNTERFACTUAL (recorded |carState torque| at i-1, latActive; 100 Hz fork frames)")
# the hands-off reaction residual (alpha/omega-compensated word), fitted here on settled hands-off frames
from scipy import signal  # noqa: E402
b8, a8 = signal.butter(2, 8.0 / 50.0)
w_lp = signal.filtfilt(b8, a8, F["cs_rate"].astype(float))
alpha = np.gradient(w_lp) * 100.0
gp60 = 1.024 * F["cs_tq"].astype(float)                    # gp-0x4f60 = +1.024 cs_tq (M3 sign check)
m_fit = lat & ~press & (tq < 500) & (F["cs_vegoraw"] > 1.0)
X = np.c_[alpha, w_lp, np.tanh(w_lp / 2.0), np.ones(n)]
bR, *_ = np.linalg.lstsq(X[m_fit], gp60[m_fit], rcond=None)
res_word = gp60 - X @ bR
res_raw = sh(np.abs(res_word) / 1.024)
pr("  reaction refit on %.0f s (lat, no press, |tq|<500): gp60 = %.3f a %+.3f w %+.1f tanh(w/2) %+.1f ; resid sd %.0f gp"
   % (m_fit.sum() / 100, *bR, np.std(res_word[m_fit])))
GATES = {
    "G0 cur 600/500": hyst(tq > 600, tq <= 500, lat),
    "G1 Honda 1200/900": hyst(tq > 1200, tq <= 900, lat),
    "G2 deb40 600 | 1200": hyst((runlen(tq > 600) >= 4) | (tq > 1200), tq <= 500, lat),
    "G3 deb60 600 | 1200": hyst((runlen(tq > 600) >= 6) | (tq > 1200), tq <= 500, lat),
    "G4 deb80 600 | 1200": hyst((runlen(tq > 600) >= 8) | (tq > 1200), tq <= 500, lat),
    "G5 deb80 600 | 1500": hyst((runlen(tq > 600) >= 8) | (tq > 1500), tq <= 500, lat),
    "G6 deb100 600 | 1500": hyst((runlen(tq > 600) >= 10) | (tq > 1500), tq <= 500, lat),
    "G7 a-comp 600/500": hyst(res_raw > 600, res_raw <= 500, lat),
    "G8 deb80 600 | deb30 1200": hyst((runlen(tq > 600) >= 8) | (runlen(tq > 1200) >= 3), tq <= 500, lat),
    "G9 deb80 600 | deb20 1200": hyst((runlen(tq > 600) >= 8) | (runlen(tq > 1200) >= 2), tq <= 500, lat),
}


def confirmed_hold(g, hold=20, conf_hard=10, conf_len=30):
    """(b): an O1 episode CONFIRMED as a hand (>= conf_hard frames above 1200, or >= conf_len frames long) releases
    only after |tq| <= 500 for `hold` frames.  Vectorised per frame; one loop over EPISODES (not samples)."""
    le = runlen(tq <= 500)
    ok_rel = le >= hold
    nxt = np.full(n + 1, n, np.int64)                     # next index where the hold condition is met
    idx = np.flatnonzero(ok_rel)
    nxt[:n] = np.searchsorted(idx, np.arange(n)) 
    nxt[:n] = np.where(nxt[:n] < len(idx), idx[np.minimum(nxt[:n], len(idx) - 1)], n)
    out = g.copy()
    a, b = episodes(g)
    for x, y in zip(a, b):
        if (tq[x:y] > 1200).sum() >= conf_hard or (y - x) >= conf_len:
            e = min(nxt[y], n)
            out[y:e] = True
    return out & lat


GATES["G10 G4 + confirmed-hand hold 200 ms"] = confirmed_hold(GATES["G4 deb80 600 | 1200"])
pa, pb = episodes(press & lat)                               # the hand episodes (steeringPressed, Honda 1200)
pr("  hand (steeringPressed & latActive) episodes: %d, %.1f s" % (len(pa), (press & lat).sum() / 100))
o1_0 = GATES["G0 cur 600/500"]
RA = {}
pr("  gate | episodes | s | eps w/o press | s w/o press | hand eps caught | yield latency vs |tq|>600 onset p50/p90/max ms "
   "| vs press onset p50/max ms | releases | O1 % of hard no-press time")
for k, g in GATES.items():
    a, b = episodes(g)
    hasp = np.array([press[x:y].any() for x, y in zip(a, b)], bool) if len(a) else np.zeros(0, bool)
    caught, lat600, latp = 0, [], []
    for x, y in zip(pa, pb):
        lo = max(x - 50, 0)
        on600 = lo + int(np.argmax(tq[lo:y] > 600)) if (tq[lo:y] > 600).any() else x
        gi = np.flatnonzero(g[lo:y + 1])
        if len(gi):
            caught += 1
            gon = lo + gi[0]
            lat600.append(max(gon - on600, 0) * 10)
            latp.append((gon - x) * 10)
    lat600 = np.array(lat600) if lat600 else np.array([np.nan])
    latp = np.array(latp) if latp else np.array([np.nan])
    rel = int((g[:-1] & ~g[1:] & lat[1:]).sum())
    sh_hard = float((g & hard & ~press).sum() / max((hard & ~press).sum(), 1))
    RA[k] = dict(n=len(a), s=float(g.sum() / 100), n_nopress=int((~hasp).sum()),
                 s_nopress=float(sum((y - x) for x, y, h in zip(a, b, hasp) if not h) / 100),
                 caught=caught, n_hand=len(pa), lat600_p50=float(np.nanmedian(lat600)),
                 lat600_p90=float(np.nanpercentile(lat600, 90)), lat600_max=float(np.nanmax(lat600)),
                 latp_p50=float(np.nanmedian(latp)), latp_max=float(np.nanmax(latp)), releases=rel,
                 o1_share_hard_nopress=sh_hard)
    r = RA[k]
    pr("  %-22s | %4d | %5.1f | %4d | %5.1f | %d/%d | %3.0f / %3.0f / %3.0f | %+4.0f / %+4.0f | %4d | %4.1f %%"
       % (k, r["n"], r["s"], r["n_nopress"], r["s_nopress"], r["caught"], r["n_hand"], r["lat600_p50"],
          r["lat600_p90"], r["lat600_max"], r["latp_p50"], r["latp_max"], r["releases"], 100 * sh_hard))
R["A"] = dict(gates=RA, reaction_refit=list(map(float, bR)), resid_sd=float(np.std(res_word[m_fit])))
# peak |tq| of the no-press episodes of the current gate (what a threshold must clear)
a0, b0 = episodes(o1_0)
pk = np.array([tq[x:y].max() for x, y in zip(a0, b0)])
du = (b0 - a0) * 10
hp = np.array([press[x:y].any() for x, y in zip(a0, b0)])
pr("  current-gate episodes WITHOUT press: n %d, duration p50/p90/max %d/%d/%d ms, peak |tq| p50/p90/max %d/%d/%d"
   % ((~hp).sum(), np.median(du[~hp]), np.percentile(du[~hp], 90), du[~hp].max(), np.median(pk[~hp]),
      np.percentile(pk[~hp], 90), pk[~hp].max()))
pr("  ... WITH press: n %d, duration p50/p10 %d/%d ms" % (hp.sum(), np.median(du[hp]), np.percentile(du[hp], 10)))
# how long |tq| stays > 600 continuously inside the hand episodes (does an 80 ms debounce delay a real hand?)
R["A"]["nopress_dur_ms"] = [float(np.median(du[~hp])), float(np.percentile(du[~hp], 90)), float(du[~hp].max())]
R["A"]["nopress_peak"] = [float(np.median(pk[~hp])), float(np.percentile(pk[~hp], 90)), float(pk[~hp].max())]

# =====================================================================================================================
# B. LIMITER RE-RUN over the hard windows (open loop on the recorded wheel)
# =====================================================================================================================
pr("\nB. LIMITER RE-RUN on the hard windows (recorded desired angle + recorded wheel; OPEN LOOP)")
dil = np.convolve(hard.astype(np.int8), np.ones(301, np.int8), mode="same") > 0
win_a, win_b = episodes(dil & lat)
pr("  windows %d, %.1f s (hard %.1f s)" % (len(win_a), (dil & lat).sum() / 100, hard.sum() / 100))
v = np.maximum(vraw, 1.0)
djerk = C.vm_dmax_jerk(v)
amax = C.vm_amax(v)
s_tap = C.s_tap_per_deg(vraw)


def run_limiter(cfg, gate):
    """the fork's _update_angle, frame by frame on each window; cfg = dict(cap, err_bp, err_v, lead_o1, take, acc)."""
    y = np.full(n, np.nan)
    stage = np.zeros(n, np.int8)            # 1 rate/jerk, 2 accel clip, 3 O1, 4 error clip
    emax = np.interp(vraw, cfg["err_bp"], cfg["err_v"])
    dmax = np.minimum(djerk, cfg["cap"])
    acc = cfg.get("acc", 0.0) * 1e-4        # deg/frame^2
    take = cfg.get("take", 0.0)
    for a, b in zip(win_a, win_b):
        prev = co[a - 1] if a > 0 else th[a]
        prev_rate = 0.0
        since = 1e9
        g_prev = gate[a - 1] if a > 0 else False
        for i in range(a, b):
            g = gate[i]
            if g_prev and not g:
                prev, since, prev_rate = th[i], 0.0, 0.0
            dm = dmax[i]
            if take > 0.0 and since < take:
                dm = dm * since / take
            if acc > 0.0:                    # (b) second-order limiter with the braking curve sqrt(2 acc |d|)
                dd = des[i] - prev
                rb = math.copysign(math.sqrt(2.0 * acc * abs(dd)), dd)
                rc = min(max(rb, -dm), dm)
                r1 = prev + min(max(rc, prev_rate - acc), prev_rate + acc)
            else:
                r1 = min(max(des[i], prev - dm), prev + dm)
            r2 = min(max(r1, -amax[i]), amax[i])
            r3 = th[i] + rate[i] * cfg["lead_o1"] if g else r2
            r4 = min(max(r3, th[i] - emax[i]), th[i] + emax[i])
            r4 = min(max(r4, -400.0), 400.0)
            st = 0
            if abs(r1 - des[i]) > 1e-3:
                st = 1
            if abs(r2 - r1) > 1e-3:
                st = 2
            if g:
                st = 3
            if abs(r4 - r3) > 1e-3:
                st = 4
            stage[i] = st
            prev_rate = r4 - prev
            prev, y[i] = r4, r4
            since += 0.01
            g_prev = g
    return y, stage


tB = time.perf_counter()
base_cfg = dict(cap=C.CUR["cap"], err_bp=C.CUR["err_bp"], err_v=C.CUR["err_v"], lead_o1=0.06, take=0.0)
y0, st0 = run_limiter(base_cfg, o1_0)
mw = dil & lat
ok = np.abs(y0[mw] - co[mw]) <= 1e-3
pr("  VALIDATION baseline re-run == published co_ang on %.3f %% of window frames (max |diff| %.4f deg); %.1f s"
   % (100 * ok.mean(), np.nanmax(np.abs(y0[mw] - co[mw])), time.perf_counter() - tB))
R["B_valid"] = float(ok.mean())

ERR_A = (29.0, 24.0, 32.0, 25.0, 8.5, 4.5)                  # D2 proposal: P-cap ~60 % rail at <= 12 m/s, highway unchanged
CFGS = {
    "C0 V298 (current)": (base_cfg, "G0 cur 600/500"),
    "C1 gate G4 only": (dict(base_cfg, lead_o1=0.0), "G4 deb80 600 | 1200"),
    "C2 G4 + takeover 0.4 s": (dict(base_cfg, lead_o1=0.0, take=0.4), "G4 deb80 600 | 1200"),
    "C3 C2 + cap 300": (dict(base_cfg, cap=3.0, lead_o1=0.0, take=0.4), "G4 deb80 600 | 1200"),
    "C4 C3 + clip D2 (impl a)": (dict(base_cfg, cap=3.0, lead_o1=0.0, take=0.4, err_v=ERR_A), "G4 deb80 600 | 1200"),
    "C5 C4 + accel 1500 (impl b)": (dict(base_cfg, cap=3.0, lead_o1=0.0, take=0.4, err_v=ERR_A, acc=1500.0),
                                    "G4 deb80 600 | 1200"),
    "C6 cap 300 + clip only (no gate)": (dict(base_cfg, cap=3.0, err_v=ERR_A), "G0 cur 600/500"),
}
# the recorded tap on the fork axis (signed, LSB): 0x1AB field, ZOH to t_co
fld = ((W["b0"].astype(int) & 3) << 8) | W["b1"].astype(int)
tap_w = np.where(fld >= 512, -1.0, 1.0) * (fld & 511)
j1 = np.clip(np.searchsorted(W["t1ab"], t, side="right") - 1, 0, len(tap_w) - 1)
tap_rec = tap_w[j1]
RB = {}
pr("  config | gate | ON frames: hard&~press share O1 / rate-jerk / error-clip | |sp-th| p50/p90 (deg) | P tap p50/p90/max "
   "(LSB) | P+D drive p90/max | P-cap frames | cap-bound frames after a release (<=0.3 s) share")
for k, (cfg, gk) in CFGS.items():
    g = GATES[gk]
    y, st = run_limiter(cfg, g)
    m = mw & hard & ~press
    e = (y - th)
    P = s_tap * e                                            # tap LSB, sign = left
    Dd = -0.5 * rate                                         # measured c_D ~0.5 tap per deg/s (synthesis C7), opposes
    drive = np.abs(P + Dd)
    rel = np.r_[False, g[:-1] & ~g[1:]] & lat
    since_rel = np.full(n, 1e9)
    ri = np.flatnonzero(rel)
    if len(ri):
        last = np.maximum.accumulate(np.where(rel, np.arange(n), -1))
        since_rel = np.where(last >= 0, (np.arange(n) - last) * 0.01, 1e9)
    capb = m & (st == 1)
    # the setpoint's 1.6-3 Hz rate content on the hard no-press frames (the hard-turn goal criterion's band; the wheel
    # attenuates it 0.42-0.86, M6) -- counterfactual setpoint inside the windows, the published one outside
    spc = np.where(np.isnan(y), co, y)
    sos_b = signal.butter(2, [1.6, 3.0], btype="band", fs=100.0, output="sos")
    r163 = float(np.sqrt(np.mean(signal.sosfiltfilt(sos_b, np.gradient(spc) * 100.0)[m] ** 2)))
    emax = np.interp(vraw, cfg["err_bp"], cfg["err_v"])
    pcap = np.abs(s_tap * emax)
    RB[k] = dict(o1=float(np.mean(st[m] == 3)), rate=float(np.mean(st[m] == 1)), clip=float(np.mean(st[m] == 4)),
                 err_p50=float(np.nanmedian(np.abs(e[m]))), err_p90=float(np.nanpercentile(np.abs(e[m]), 90)),
                 P_p50=float(np.nanmedian(np.abs(P[m]))), P_p90=float(np.nanpercentile(np.abs(P[m]), 90)),
                 P_max=float(np.nanmax(np.abs(P[m]))), drive_p90=float(np.nanpercentile(drive[m], 90)),
                 drive_max=float(np.nanmax(drive[m])), pcap_frames=float(np.mean(np.abs(P[m]) >= 0.999 * pcap[m])),
                 cap_after_release=float(np.mean(since_rel[capb] <= 0.3)) if capb.any() else 0.0, sp_rate_163=r163,
                 low8=dict(rate=float(np.mean(st[m & (vraw < 8)] == 1)), clip=float(np.mean(st[m & (vraw < 8)] == 4)),
                           P_p90=float(np.nanpercentile(np.abs(P[m & (vraw < 8)]), 90))))
    r = RB[k]
    pr("  %-32s | %s | %4.1f / %4.1f / %4.1f %% | %4.1f / %4.1f | %5.1f / %5.1f / %5.1f | %5.1f / %5.1f | %4.1f %% | %4.1f %%"
       % (k, gk.split()[0], 100 * r["o1"], 100 * r["rate"], 100 * r["clip"], r["err_p50"], r["err_p90"], r["P_p50"],
          r["P_p90"], r["P_max"], r["drive_p90"], r["drive_max"], 100 * r["pcap_frames"], 100 * r["cap_after_release"])
       + "  | sp 1.6-3 Hz rate rms %.1f deg/s" % r["sp_rate_163"])
m = mw & hard & ~press
pr("  recorded tap on the same frames: |tap| p50/p90/max %.1f / %.1f / %.1f LSB (rail %.1f)"
   % (np.median(np.abs(tap_rec[m])), np.percentile(np.abs(tap_rec[m]), 90), np.abs(tap_rec[m]).max(), C.RAIL_TAP))
R["B"] = RB
R["B_tap_rec"] = [float(np.median(np.abs(tap_rec[m]))), float(np.percentile(np.abs(tap_rec[m]), 90)),
                  float(np.abs(tap_rec[m]).max())]

# =====================================================================================================================
# C. THE BAR
# =====================================================================================================================
pr("\nC. BAR: current angle-mode formula vs the proposed signed 0x1AB lane torque / 2461")
# the tap's sign convention: correlate with the error (theta_sp - theta, + left) on the wire grid
te4, cmd = W["te4"], W["cmd"]
jt = np.clip(np.searchsorted(W["t1ab"], te4, side="right") - 1, 0, len(tap_w) - 1)
j14 = np.clip(np.searchsorted(W["t14"], te4, side="right") - 1, 0, len(W["ang"]) - 1)
err_w = -cmd / 10.0 - W["ang"][j14]
eng = W["req"] > 0
c_sign = float(np.corrcoef(tap_w[jt][eng], err_w[eng])[0, 1])
pr("  corr(signed tap, theta_sp - theta) engaged = %+.3f  => tap + = torque toward %s" % (c_sign, "LEFT" if c_sign > 0 else "RIGHT"))
x1 = np.load(C.OUT / "x1ab_r79.npz") if (C.OUT / "x1ab_r79.npz").exists() else None
if x1 is not None:
    pr("  0x1AB frames in the rlog: %d on src %s (checksum/counter: see x1ab_r79.txt)" % (len(x1["t"]), sorted(set(x1["src"].tolist()))))
bar_new = np.clip(np.sign(c_sign) * tap_rec / C.RAIL_TAP, -1, 1)
mlat = lat
pr("  proposed bar: |bar| >= 0.95 on %.2f %% of latActive frames (current 59.7 %%); |bar| p50/p99/max %.2f/%.2f/%.2f; "
   "corr with the delivered lane torque = 1 by construction" % (100 * np.mean(np.abs(bar_new[mlat]) >= 0.95),
                                                                np.median(np.abs(bar_new[mlat])),
                                                                np.percentile(np.abs(bar_new[mlat]), 99),
                                                                np.abs(bar_new[mlat]).max()))
R["C"] = dict(tap_sign_corr=c_sign, pinned_new=float(np.mean(np.abs(bar_new[mlat]) >= 0.95)),
              p99=float(np.percentile(np.abs(bar_new[mlat]), 99)))
R["wall_s"] = time.perf_counter() - T0
pr("\nwall %.1f s" % R["wall_s"])
(C.OUT / "cf_fork_r79.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
(C.OUT / "cf_fork_r79.json").write_text(json.dumps(R, indent=1, default=float), encoding="utf-8")
