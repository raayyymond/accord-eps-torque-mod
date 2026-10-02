# -*- coding: utf-8 -*-
r"""d3_r79.py -- D3 (authority-first) ROUTE-79 COUNTERFACTUALS.  ANALYSIS ONLY: reads the kit's r79 caches and the V298
image; sends nothing; writes only _scratch/angle_loop/v299-D3/r79_*.{txt,json}.

  1. THE TWIST: the hands-off torque word |gp-0x4f68| (= |0x18F| x 1.024) by speed band and in hard hands-off frames,
     and its growth with wheel acceleration -- what any freeze / O1 threshold must clear.
  2. O1: the fork's override relay re-run on carState torque with V298's (600, 500) and the D3 thresholds; episodes,
     time, and how many never reach steeringPressed (1200) = the reaction-twist trips.
  3. THE INTEGRAL: freeze duty and discarded integration (hands-off, < 8 m/s) under each candidate's freeze rule, on the
     V298 lane replay (m3_lane's integer-exact terms + event-driven I recursion, generalised here to D3's cells).
  4. THE TAP each candidate's lane arithmetic would deliver on the RECORDED inputs (OPEN LOOP: the trajectory is held at
     what V298 produced; a stiffer loop would have closed the errors faster, so this over-states the tap of the stiffer
     candidates in slews -- an upper-bound-like read, BELIEF for the closed-loop value).
Vectorised; the only Python loops are over episodes / events (m3_lane.i_recursion).  Wall time printed.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "v298_flight"))
import d3_common as D  # noqa: E402
with contextlib.redirect_stdout(io.StringIO()):
    import m3_lane as M3  # noqa: E402

T0 = time.time()
LINES = []
RES = {}


def pr(s=""):
    LINES.append(s)
    print(s)


# =====================================================================================================================
# the lane terms, generalised (m3_lane.lane_terms with D3's cells as parameters; arithmetic identical otherwise)
# =====================================================================================================================
def lane_terms_p(C, th, cmd, tq, x, abe, vws, eng, R, r0, rows, thr=512, sgn=300, arb=(6, 4, 2880, 1250, 1382, 4096),
                 q_shift=10, rq=False):
    gl = M3.glut(rows)
    L = M3.lane_terms(C, th, cmd, tq, x, abe, vws, eng, R, r0, gl, q_shift=q_shift)
    FL = M3.FL
    # recompute the freeze terms and the bound with D3's immediates (the same expressions as m3_lane.lane_terms)
    atq, hs, Ep = L["atq"], L["hs"], L["Ep"]
    L["c1"] = atq > thr
    L["c2"] = (np.abs(hs) > sgn) & ((hs ^ Ep) < 0) & ~L["c1"]
    sh, sh_lo, vth, Bb, vcap, cap = arb
    m, n = L["m"], len(th)
    vw = np.broadcast_to(np.clip(vws[L["F"]], 0, 12000)[:, None], (m, 10)).ravel() & 0xFFFF
    shv = np.where(vw <= vth, sh_lo, sh)
    bound = FL.s32((np.abs(L["th6"]) << shv) + Bb)
    L["bound"] = np.where((vw <= vcap) & (bound > cap), cap, bound)
    L["vw"] = vw
    # the fresh rate per tick (lane_terms' own schedule: ticks 0..8 frame k, tick 9 frame k+1)
    F = L["F"]
    kn = np.minimum(F + 1, n - 1)
    ab = np.empty((m, 10), np.int64)
    ab[:, :9] = abe[F][:, None]
    ab[:, 9] = abe[kn]
    ab16 = FL.s16(ab.ravel())
    fast = (((ab16 >> 5) + 1) & 0xFFFFFFFF) > 1                # |gp-0x6abe| >= 32 (6.8 deg/s motor frame)
    toward = fast & ((ab16 ^ Ep) < 0)                          # abe = -4.712 w : the wheel moves toward the setpoint
    L["fast"], L["toward"] = fast, toward
    L["c1_v298"], L["c2_v298"] = L["c1"].copy(), L["c2"].copy()
    if rq:
        L["c1"] = L["c1"] & ~toward
        L["c2"] = L["c2"] & ~toward
    return L


def replay(C, ins, cand, R, r0):
    th, cmd, tq, x, abe, vws, eng = ins
    L = lane_terms_p(C, th, cmd, tq, x, abe, vws, eng, R, r0, cand["rows"], cand["thr"], cand["sgn"], cand["arb"],
                     rq=cand.get("rq", False))
    fr = L["c1"] | L["c2"] | L["c4"]
    Ia, a3s, clp, nev = M3.i_recursion(L, fr, a3=True, icl_s=cand["icl"])
    Cc = dict(C, SCL=cand["SCL"])
    T = M3.output_T(Cc, L, Ia, len(th))
    # S before the SCL clamp (to count clamp-active frames)
    Ssum = np.where(L["run"], ((Ia >> 7) + L["P"] + L["D"]) * L["f"] >> 8, 0)
    return dict(L=L, fr=fr, Ia=Ia, a3s=a3s, clp=clp, T=T, S=Ssum)


def hyst(x, on, off):
    """vectorised relay: 1 where x > on, 0 where x <= off, else the previous state (initial 0)."""
    dec = np.where(x > on, 1, np.where(x <= off, 0, -1))
    idx = np.where(dec >= 0, np.arange(len(x)), -1)
    last = np.maximum.accumulate(idx)
    return np.where(last >= 0, dec[np.maximum(last, 0)], 0).astype(bool)


def episodes(mask):
    e = np.flatnonzero(np.diff(np.r_[0, mask.astype(np.int8), 0]))
    return e[::2], e[1::2]


def main():
    C = M3.image_cells()
    D.assert_v298()
    W = M3.load_wire()
    th, cmd, tq, x, abe, vws = M3.wire_inputs(W)
    eng = W["eng"]
    n = len(th)
    v = W["vego"]
    bar = np.abs(W["bar"])                                    # = |gp-0x4f68| (wire x 1.024)
    pressed = W["pressed"]
    # pressed debounced +-0.5 s (a hand episode, not a twist)
    k = np.convolve(pressed.astype(float), np.ones(101), "same") > 0
    ho = eng & ~k
    w = np.nan_to_num(W["w18"])
    wl = np.convolve(w, np.ones(5) / 5, "same")
    alpha = np.gradient(wl) * 100.0                             # deg/s^2
    hard = eng & ((np.abs(W["theta"]) > 30) | (np.abs(w) > 60))
    pr(f"D3 route-79 counterfactuals; engaged {eng.sum() / 100:.1f} s, hands-off (pressed-debounced 0.5 s) "
       f"{ho.sum() / 100:.1f} s, hard hands-off {(ho & hard).sum() / 100:.1f} s")
    # ------------------------------------------------------------------------------------------------- 1. the twist
    pr("\n== 1. THE TWIST: hands-off |gp-0x4f68| percentiles (gp counts; 0x18F raw x 1.024) ==")
    bands = (("0-5", 0, 5), ("5-8", 5, 8), ("8-12.5", 8, 12.5), ("12.5-22", 12.5, 22), (">22", 22, 99))
    tw = {}
    for nm, lo, hi in bands:
        m = ho & (v >= lo) & (v < hi)
        if m.sum() < 200:
            continue
        q = np.percentile(bar[m], [50, 90, 99, 99.9])
        mh = m & hard
        qh = np.percentile(bar[mh], [90, 99, 99.9]) if mh.sum() > 100 else [np.nan] * 3
        frac = [float(np.mean(bar[m] > t)) for t in (512, 614, 800, 1000, 1229)]
        tw[nm] = dict(p50=q[0], p90=q[1], p99=q[2], p999=q[3], hard_p90=qh[0], hard_p99=qh[1], hard_p999=qh[2],
                      frac_gt=frac, secs=m.sum() / 100)
        pr(f"  {nm:8s} {m.sum() / 100:6.1f} s  p50 {q[0]:5.0f} p90 {q[1]:5.0f} p99 {q[2]:5.0f} p99.9 {q[3]:5.0f} | hard "
           f"p90/99/99.9 {qh[0]:5.0f}/{qh[1]:5.0f}/{qh[2]:5.0f} | >512 {frac[0]:.3f} >614 {frac[1]:.3f} >800 "
           f"{frac[2]:.3f} >1000 {frac[3]:.3f} >1229 {frac[4]:.4f}")
    RES["twist"] = tw
    # twist vs |alpha| (hands-off, < 8 m/s, moving)
    m = ho & (v < 8) & (np.abs(wl) > 5)
    edges = [0, 100, 200, 400, 700, 1000, 1500, 3000]
    pr("  hands-off < 8 m/s, |w| > 5 deg/s: |twist| p50/p90 by |alpha| bin (deg/s^2):")
    rows = []
    for a, b in zip(edges[:-1], edges[1:]):
        mm = m & (np.abs(alpha) >= a) & (np.abs(alpha) < b)
        if mm.sum() > 30:
            p = np.percentile(bar[mm], [50, 90])
            rows.append((a, b, int(mm.sum()), p[0], p[1]))
            pr(f"    [{a:4d},{b:4d}) n {mm.sum():5d}  p50 {p[0]:5.0f}  p90 {p[1]:5.0f}")
    X = np.c_[np.ones(m.sum()), np.abs(alpha[m]), np.abs(wl[m])]
    coef = np.linalg.lstsq(X, bar[m], rcond=None)[0]
    pr(f"  OLS |twist| = {coef[0]:.0f} + {coef[1]:.3f}|alpha| + {coef[2]:.2f}|w|   (hands-off < 8 m/s, moving)")
    RES["twist_alpha"] = dict(bins=rows, ols=coef.tolist())
    # threshold crossings per minute of hands-off TURNING (|0.5 s mean w18| >= 10 deg/s), < 10 m/s -- the refuter's
    # ratchet split keyed the r79 stall-surge excess to crossings of |bar| 300 / 512 (REFUTE-synthesis-inference 3)
    w05 = np.convolve(w, np.ones(50) / 50, "same")
    turn = ho & (v < 10) & (np.abs(w05) >= 10)
    cr = {}
    for thr_ in (300, 512, 800, 1229):
        up = (bar[1:] > thr_) & (bar[:-1] <= thr_) & turn[1:]
        cr[thr_] = float(up.sum() / max(turn.sum() / 6000.0, 1e-9))
    RES["crossings_per_min_turning_lt10"] = cr
    pr(f"  upward crossings of |bar| per minute of hands-off turning < 10 m/s ({turn.sum() / 100:.1f} s): "
       + "  ".join(f"{k}: {x:.1f}" for k, x in cr.items()))
    # -------------------------------------------------------------------------------------------------- 2. O1
    F = np.load(D.KIT / "analysis-2020accord" / "_scratch" / "cache" / "v280" / "r79_fork.npz")
    tcs, cst, csp = F["t_cs"], np.abs(F["cs_tq"]), F["cs_press"].astype(bool)
    la = np.interp(tcs, F["t_cc"], F["cc_latActive"].astype(float)) > 0.5
    vcs = F["cs_vego"]
    pr("\n== 2. O1 (fork override relay) re-run on carState torque, latActive frames ==")
    o1 = {}
    for on, off in ((600, 500), (900, 700), (1200, 1000), (1500, 1200)):
        s = hyst(np.where(la, cst, 0.0), on, off) & la
        a, b = episodes(s)
        never = sum(1 for i, j in zip(a, b) if not csp[i:j].any())
        never_t = sum((j - i) for i, j in zip(a, b) if not csp[i:j].any()) / 100.0
        tot = s.sum() / 100.0
        lo8 = (s & (vcs < 8)).sum() / max((la & (vcs < 8)).sum(), 1)
        o1[f"{on}/{off}"] = dict(n=len(a), secs=tot, never=never, never_secs=never_t, share_lo8=lo8)
        pr(f"  ON {on:4d} / OFF {off:4d}: {len(a):4d} episodes, {tot:6.1f} s; never-pressed {never:4d} ({never_t:5.1f} s);"
           f" share of latActive < 8 m/s {lo8:.3f}")
    # D3's O1: ON = |tq| > 1200 for MORE than 10 consecutive frames (100 ms) OR |tq| > 2500 at once; OFF <= 1000.
    # Vectorised: run length of (|tq| > 1200) via cumulative counts reset at each break.
    xo = np.where(la, cst, 0.0)
    over = xo > 1200
    idx = np.arange(len(xo))
    brk = np.maximum.accumulate(np.where(~over, idx, -1))
    runlen = np.where(over, idx - brk, 0)                         # frames (1-based) the excursion has lasted
    trig = (runlen > 10) | (xo > 2500)
    dec = np.where(trig, 1, np.where(xo <= 1000, 0, -1))
    li = np.maximum.accumulate(np.where(dec >= 0, idx, -1))
    sD3 = np.where(li >= 0, dec[np.maximum(li, 0)], 0).astype(bool) & la
    a, b = episodes(sD3)
    never = sum(1 for i, j in zip(a, b) if not csp[i:j].any())
    # recognition latency on the real-hand episodes: first frame > 1200 -> first O1 frame
    s12 = hyst(xo, 1200, 1000) & la
    a2, b2 = episodes(s12)
    lat = []
    for i, j in zip(a2, b2):
        kf = np.flatnonzero(sD3[i:j])
        lat.append((kf[0] if len(kf) else (j - i)) * 10.0)
    lat = np.array(lat)
    o1["D3"] = dict(n=len(a), secs=float(sD3.sum() / 100.0), never=never, lat_ms_p50=float(np.median(lat)),
                    lat_ms_p90=float(np.percentile(lat, 90)), lat_ms_max=float(lat.max()),
                    never_engaged=int(np.sum(lat >= np.array([(j - i) * 10.0 for i, j in zip(a2, b2)]))))
    pr(f"  D3 (1200 for > 100 ms, or > 2500; OFF 1000): {len(a):4d} episodes, {sD3.sum() / 100.0:6.1f} s; never-pressed "
       f"{never}; recognition latency vs the plain 1200 relay on its {len(a2)} episodes: p50 {np.median(lat):.0f} ms, "
       f"p90 {np.percentile(lat, 90):.0f} ms, max {lat.max():.0f} ms; episodes the D3 relay never enters "
       f"{o1['D3']['never_engaged']} (all shorter than 100 ms and below 2500)")
    RES["o1"] = o1
    # ------------------------------------------------------------------------------------------- 3/4. the lane replays
    r0, R = M3.ramp_ticks(eng, C["ramp_in2"], C["ramp_out2"])
    ins = (th, cmd, tq, x, abe, vws, eng)
    A3 = (6, 4, 2880, 1250, 1382, 4096)
    G12 = D.scaled_rows(1.2, mult_8=1.0)          # the D3 (a) table: x1.2 at 3.1 m/s tapering to x1.0 at 8.0 m/s
    CANDS = {
        "V298": dict(rows=D.GB_P, thr=512, sgn=300, arb=A3, icl=8192, SCL=15360),
        "V298+RQ": dict(rows=D.GB_P, thr=512, sgn=300, arb=A3, icl=8192, SCL=15360, rq=True),
        "V298+T1229/800": dict(rows=D.GB_P, thr=1229, sgn=800, arb=A3, icl=8192, SCL=15360),
        "D3a = (a)": dict(rows=G12, thr=1229, sgn=800, arb=A3, icl=8192, SCL=15360),
        "D3b = (a)+SCL19072": dict(rows=G12, thr=1229, sgn=800, arb=A3, icl=8192, SCL=19072),
        "RQ (rejected)": dict(rows=G12, thr=512, sgn=300, arb=A3, icl=8192, SCL=15360, rq=True),
        "RQ+T (rejected)": dict(rows=G12, thr=1229, sgn=800, arb=A3, icl=8192, SCL=15360, rq=True),
        "X8192 (rejected)": dict(rows=G12, thr=1229, sgn=800, arb=A3[:5] + (8192,), icl=8192, SCL=15360),
    }
    tapT = W["T"]                                             # measured tap, T counts at T_t (50 Hz)
    jj = np.clip(np.searchsorted(W["t"], W["T_t"], side="right") - 1, 0, n - 1)
    pr("\n== 3/4. LANE REPLAY on route 79's recorded inputs (dir-2 ramp, torque word +10 ticks = M3's best timing) ==")
    pr("  hands-off = engaged and not pressed (+-0.5 s); 'disc<8' = commanded integration discarded by the HAND freezes"
       " (|inc| weighted), hands-off, < 8 m/s; 'A3stop<8' = run ticks the A3 bound held I, < 8 m/s; 'real-hand frz' ="
       " share of run ticks with steeringPressed (> 1200) on which a hand freeze holds I (the N1 protection kept)")
    rep = {}
    for name, cd in CANDS.items():
        r = replay(C, ins, cd, R, r0)
        L = r["L"]
        Fi = L["F"]
        hoT = np.repeat(ho[Fi], 10)
        lo8 = np.repeat(v[Fi] < 8, 10)
        run = L["run"]
        hand = (L["c1"] | L["c2"]) & run
        incab = np.abs(L["inc"]).astype(float)
        sel = run & hoT & lo8
        disc = float((incab * hand)[sel].sum() / max(incab[sel].sum(), 1))
        duty = float(hand[run & hoT].mean())
        a3s = float(r["a3s"][run & lo8].mean())
        T = r["T"]
        tap = np.abs(T[eng]) / 8.0
        S_cl = np.abs(r["S"]) >= cd["SCL"]
        clamp_frac = float(S_cl[run].mean())
        Ih = M3.slot4(L, np.where(run, r["Ia"] >> 7, 0), n)
        hard_tap = np.abs(T[ho & hard]) / 8.0
        prT = np.repeat(pressed[Fi], 10)
        hand_real = float(hand[run & prT].mean()) if (run & prT).any() else float("nan")
        d = dict(peak=float(tap.max()), p99=float(np.percentile(tap, 99)), p999=float(np.percentile(tap, 99.9)),
                 hand_real=hand_real,
                 hard_p99=float(np.percentile(hard_tap, 99)), ge250=int((tap >= 250).sum()),
                 ge300=int((tap >= 300).sum()), disc_lo8=disc, hand_duty=duty, a3stop_lo8=a3s, scl_clamp=clamp_frac,
                 I_peak_S=float(np.abs(Ih[eng]).max()))
        if name == "V298":
            yh = T[jj] / 8.0
            mm = eng[jj] & np.isfinite(tapT) & ~k[jj]
            y = tapT[mm] / 8.0
            d["r2_vs_wire"] = float(1 - np.sum((y - yh[mm]) ** 2) / np.sum((y - y.mean()) ** 2))
        rep[name] = d
        if name == "V298":
            hf = ((L["c1_v298"] | L["c2_v298"]) & run & hoT)
            nh = max(int(hf.sum()), 1)
            sl = float((hf & ~L["fast"]).sum() / nh)
            tw_ = float((hf & L["toward"]).sum() / nh)
            aw = float((hf & L["fast"] & ~L["toward"]).sum() / nh)
            hf8 = hf & lo8
            nh8 = max(int(hf8.sum()), 1)
            RES["v298_handfrz_split"] = dict(slow=sl, toward=tw_, away=aw,
                                             slow_lo8=float((hf8 & ~L["fast"]).sum() / nh8),
                                             toward_lo8=float((hf8 & L["toward"]).sum() / nh8))
            pr(f"    V298 hands-off hand-frozen ticks: |rate| < 6.8 deg/s {sl:.3f} | moving TOWARD the setpoint {tw_:.3f} |"
               f" moving away {aw:.3f}   (< 8 m/s: slow {RES['v298_handfrz_split']['slow_lo8']:.3f}, toward "
               f"{RES['v298_handfrz_split']['toward_lo8']:.3f})")
        pr(f"  {name:18s} tap peak {d['peak']:6.1f} p99 {d['p99']:5.1f} p99.9 {d['p999']:5.1f} hard-ho p99 "
           f"{d['hard_p99']:5.1f} | >=250 {d['ge250']:4d} >=300 {d['ge300']:4d} frames | SCL-clamp {clamp_frac:.4f} |"
           f" disc<8 {disc:.3f} hand-frz duty {duty:.3f} A3stop<8 {a3s:.3f} | real-hand frz {hand_real:.3f} |"
           f" I peak {d['I_peak_S']:.0f} S"
           + (f" | R2 vs wire {d['r2_vs_wire']:.3f}" if "r2_vs_wire" in d else ""))
    RES["replay"] = rep
    pr(f"  measured tap: peak {np.nanmax(np.abs(tapT[eng[jj]])) / 8:.1f} LSB")
    RES["wall_s"] = time.time() - T0
    pr(f"\nwall time {RES['wall_s']:.1f} s")
    (D.OUT / "r79_counterfactuals.txt").write_text("\n".join(LINES), encoding="utf-8")
    (D.OUT / "r79_counterfactuals.json").write_text(json.dumps(RES, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
