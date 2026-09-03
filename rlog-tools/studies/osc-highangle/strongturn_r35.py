# -*- coding: utf-8 -*-
"""studies/osc-highangle/strongturn_r35.py -- the STRONG-TURN / high-angle read on r35 (V281 rev 3: LKAS rate-PID
Kp FLAT 248 everywhere on the V280 rev 2 base: x6 line map, fb clamp 46080, CAN-427 delivered-torque tap), scored
EXACTLY as r34 was (strongturn_r34.py: fixed detector threshold 103 wire, same chain mirror, same edges), plus the
deep-analysis discriminators (7HZ-STRONG-TURN-DEEP-ANALYSIS-2026-09-03.md / r24_deembed.py): f0 per window, |bar|/|rate|
at f0, the plant-free L_servo / L_r24 split, and the 0x14A b4.4 sign(r24) bit's phase re the rate.
Subagent highangle35, 2026-09-03.

Sections
  A  build attribution from the tap: chain T_sim vs tap with Kp = stock LERP / flat 248 / flat 341 / flat 512 (corr,
     slope), and the LOW-FREQUENCY T-per-E slope in strong turns against the chain's DC gain at each Kp
  B  F7 census, FIXED threshold 103 (r34 vs r35) + highangle_stutter's own-threshold list; high-angle time by speed
  C  episodes through the Kp-248 chain (the on-car chain) -- the r34 columns; and the discriminators on every
     hands-light strong-turn window (f0, |bar|/|rate| at f0, L_servo/L_r24, r24 bit phase) r34 F7 episodes vs r35 windows
  D  what remains: rate + tap spectra 1-15 Hz in strong turns r34 vs r35; 2-4 Hz hunt census; 8-12 Hz; the
     stalled-wheel class (rate/ref < 0.5) count with idx and P duty; prereg (k) deadband fraction
  E  authority: hands-light full-demand rate p50/p90 (iv), tap |T| (v), stalled push at idx 40-80 vs r34; (vi) (viii)

Run: python strongturn_r35.py   (needs analysis-2020accord/_scratch/cache/v280/r34.npz, r35.npz, r3{4,5}_b4.npz)
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import strongturn_r32_r33 as ST  # noqa: E402
import r24_deembed as RD  # noqa: E402

V, S = ST.V, ST.S
FS, FS1K = ST.FS, ST.FS1K
CPD = V.CPD

V.ROUTE_PREFIX["r34"] = "75604b0a432fdc89_00000034--e2d2d5381f"
V.ROUTE_PREFIX["r35"] = "75604b0a432fdc89_00000035--580292087d"
V.ROUTE_BUILD["r34"] = "V280r2 line x6 (new tune)"
V.ROUTE_BUILD["r35"] = "V281r3 Kp flat 248 (new tune)"
V.ROUTE_K["r34"] = V.ROUTE_K["r35"] = 6.0
ST.TAP_TAGS.update({"r34", "r35"})
V280R2 = ST.V280R2
KP_FLAT = {"stock LERP": V.KP_Y, "flat 248": np.full(5, 248.0), "flat 341": np.full(5, 341.0), "flat 512": np.full(5, 512.0)}
KP_ONCAR = {"r34": "stock LERP", "r35": "flat 248"}

# highangle_stutter.py own-threshold lists (|angle| >= 30 only). r34 from HIGHANGLE-r34.txt (as strongturn_r34.py); r35 from HIGHANGLE-r35.txt
EPIS = {
    "r34": [(31.0, 3.3, 1.95), (35.5, 1.5, 7.43), (77.7, 1.2, 6.84), (133.1, 2.1, 7.28), (172.2, 1.3, 2.36), (182.4, 4.1, 7.81),
            (188.2, 1.1, 7.48), (227.9, 1.1, 2.78), (297.5, 2.0, 2.49), (343.7, 1.6, 7.41), (372.9, 1.6, 6.92), (475.7, 3.5, 7.03),
            (480.9, 3.8, 6.64), (664.8, 1.3, 3.76), (667.7, 1.7, 7.06), (747.8, 1.1, 2.75), (985.7, 2.0, 2.44), (1003.6, 1.0, 7.77)],
    "r35": [(275.9, 1.7, 4.65), (444.4, 1.2, 4.20)],       # #2 at 26.3 deg is below the 30 deg gate
}
HIGH_ANG_S = {"r34": 148.1, "r35": 79.8}
ROUTES = ("r34", "r35")


def sim(r, Y, clamp, kpY=V.KP_Y, kd=V.KD):
    V.GAIN, V.OUT_CAP = ST.GAIN, ST.CAP
    R = r.simulate(Y, kpY=kpY, fb_clamp=clamp, kd=kd)
    R["clamped"] = np.abs(r.fb_un) >= clamp
    R["ref_deg"] = 32 * np.abs(R["sp"]) / V.FB_DC / CPD
    return R


def lp(x, fc=2.0):
    return signal.sosfiltfilt(signal.butter(2, fc, fs=FS, output="sos"), x)


def welch_bands(x, fs=FS, nperseg=256):
    f, P = signal.welch(x - x.mean(), fs=fs, nperseg=min(nperseg, len(x)))
    return f, P


def band_amp_psd(f, P, lo, hi):
    m = (f >= lo) & (f < hi)
    return float(np.sqrt(2 * np.trapezoid(P[m], f[m]))) if m.sum() > 1 else np.nan


def load_b4(tag, r):
    f = os.path.join(V.CACHE, tag + "_b4.npz")
    if not os.path.exists(f):
        return None
    D = dict(np.load(os.path.join(V.CACHE, tag + ".npz"))); t0 = D["t18"][0]
    B = dict(np.load(f))
    tb = B["t14b"] - t0
    j = np.clip(np.searchsorted(tb, r.tg), 0, len(tb) - 1)
    return B["b4"][j]


def strong_windows(r, dur=1.0, vmax=10.0, tq_max=1216.0, idx_min=40, step=0.5):
    """hands-light strong-turn windows: engaged, |angle| >= 30, v <= vmax, |tq| < tq_max, idx >= idx_min, wheel moving with the setpoint"""
    m = r.eng & (np.abs(r.ang) >= 30) & (r.vego <= vmax) & (np.abs(r.tq_raw) < tq_max) & (r.idx >= idx_min)
    n = int(dur * FS); st = int(step * FS)
    out = []
    for a in range(0, len(m) - n, st):
        if m[a:a + n].mean() >= 0.95:
            out.append((a / FS, dur))
    return out


def disc_row(g, t0, dur, b4, r):
    """r24_deembed's per-window demodulation + the plant-free split + the r24 sign-bit phase re the rate at f0."""
    x = RD.episode_row(g, t0, dur)
    zT = x["AT"] * np.exp(1j * np.radians(x["ph_T"])); zr = x["Ar24"] * np.exp(1j * np.radians(x["ph_r24"]))
    tot = zT + zr
    x["Ls"], x["Lr"] = zT / tot, zr / tot
    x["bar_over_rate"] = x["Abar"] / max(x["Arate"] * CPD, 1e-9)
    s, e = int(round(t0 * FS)), int(round((t0 + dur) * FS))
    if b4 is not None:
        bit = np.where((b4[s:e] >> 4) & 1, 1.0, -1.0)
        t = g["t"][s:e]
        zb = RD.demod(bit, t, x["f0"]); zrate = RD.demod(g["rate"][s:e], t, x["f0"])
        x["bit_amp"] = abs(zb); x["ph_bit"] = float(np.degrees(np.angle(zb / zrate)))
        x["bit_duty"] = float(np.mean(bit > 0))
        x["bit_flips"] = float((np.diff(np.sign(bit)) != 0).sum() / dur)
    else:
        x["bit_amp"] = x["ph_bit"] = x["bit_duty"] = x["bit_flips"] = np.nan
    i100 = slice(s, e)
    x["tq_p50"] = float(np.median(np.abs(r.tq_raw[i100])))
    x["rate7"] = ST.band_amp(r.wire[i100]) / CPD
    x["rate_p50"] = float(np.median(np.abs(r.wire[i100])) / CPD)
    return x


def main():
    L = []
    pr = lambda s="": (print(s), L.append(s))  # noqa: E731
    routes, gs, b4s = {}, {}, {}
    for tag in ROUTES:
        print("loading %s ..." % tag, flush=True)
        routes[tag] = V.Route(tag)
        gs[tag] = RD.load(tag)
        b4s[tag] = load_b4(tag, routes[tag])
    SIMS = {tag: {k: sim(routes[tag], *V280R2, kpY=y) for k, y in KP_FLAT.items()} for tag in ROUTES}

    # ---------------------------------------------------------------------------------------------- A
    pr("=" * 170)
    pr("SECTION A -- BUILD ATTRIBUTION from the tap. Chain = V280 rev 2 line x6 / clamp 46080 / gain 5346 / cap 3072 with Kp = stock LERP (248..696) or FLAT; open loop on the measured rate")
    pr("  corr/slope = T_sim vs CAN-427 T_meas; 'strong' = |angle|>=30 & idx 40-200 & moving; DC slope = LP-2 Hz T_meas regressed on LP-2 Hz E (chain E is Kp-independent) on strong frames with |E| < 5650 (both Kp's linear window)")
    pr("=" * 170)
    for tag in ROUTES:
        r = routes[tag]; e = r.eng & (r.idx > 0); hi = e & (np.abs(r.ang) >= 30)
        strong = hi & (r.idx >= 40) & (r.idx <= 200) & (np.abs(r.wire) / CPD > 5)
        Tm = r.T_meas
        for k, R in SIMS[tag].items():
            Ts = R["T"][r.i100]
            c_all = np.corrcoef(Ts[e], Tm[e])[0, 1]; s_all = np.sum(Ts[e] * Tm[e]) / np.sum(Ts[e] ** 2)
            c_hi = np.corrcoef(Ts[hi], Tm[hi])[0, 1]; s_hi = np.sum(Ts[hi] * Tm[hi]) / np.sum(Ts[hi] ** 2)
            c_st = np.corrcoef(Ts[strong], Tm[strong])[0, 1] if strong.sum() > 100 else np.nan
            s_st = np.sum(Ts[strong] * Tm[strong]) / np.sum(Ts[strong] ** 2) if strong.sum() > 100 else np.nan
            rms = np.sqrt(np.mean((Ts[strong] - Tm[strong]) ** 2)) if strong.sum() > 100 else np.nan
            prail = np.mean(np.abs(R["P_raw"][r.i100][strong]) >= V.P_CLAMP) if strong.sum() else np.nan
            pr("  %s Kp %-10s | all eng (n %6d): corr %.3f slope %.2f | |ang|>=30 (n %5d): corr %.3f slope %.2f | strong (n %5d): corr %.3f slope %.2f rms-resid %5.0f | P-rail duty strong %.3f%s"
               % (tag, k, e.sum(), c_all, s_all, hi.sum(), c_hi, s_hi, strong.sum(), c_st, s_st, rms, prail, "   <-- ON CAR" if KP_ONCAR[tag] == k else ""))
        # DC T-per-E slope
        E100 = SIMS[tag]["flat 248"]["E"][r.i100]
        m = strong & (np.abs(E100) < 5650)
        if m.sum() > 200:
            Tl, El = lp(Tm), lp(E100)
            sl = np.sum(Tl[m] * El[m]) / np.sum(El[m] ** 2)
            cc = np.corrcoef(Tl[m], El[m])[0, 1]
            pred = {kk: np.sum(lp(SIMS[tag][kk]["T"][r.i100])[m] * El[m]) / np.sum(El[m] ** 2) for kk in KP_FLAT}
            pr("  %s DC slope T_meas/E on %d strong linear frames: %.4f (corr %.2f)  | chain predicts: %s  => nearest Kp: %s"
               % (tag, m.sum(), sl, cc, "  ".join("%s %.4f" % (kk, v) for kk, v in pred.items()), min(pred, key=lambda kk: abs(pred[kk] - sl))))
            # E-binned |T| ladder: P railing at 15855 (248) vs 5650 (696) would flatten T beyond that |E|
            cells = []
            for lo, hi_ in ((0, 2000), (2000, 4000), (4000, 6000), (6000, 9000), (9000, 13000), (13000, 17000), (17000, 30000)):
                mm = strong & (np.abs(E100) >= lo) & (np.abs(E100) < hi_)
                cells.append("%5d-%5d: |T| %4.0f (n%5d)" % (lo, hi_, np.median(np.abs(Tm[mm])), mm.sum()) if mm.sum() >= 50 else "%5d-%5d:   -- (n%5d)" % (lo, hi_, mm.sum()))
            pr("  %s |T_meas| p50 by |E| bin (strong frames; Kp 696 rails P at |E| 5650, Kp 248 at 15855): %s" % (tag, " | ".join(cells)))
        pr("  %s |E| on strong frames: p50 %.0f p90 %.0f p99 %.0f (deg/s of fb: /%.1f); frames with |E| >= 5650: %.3f, >= 15855: %.3f"
           % (tag, np.median(np.abs(E100[strong])), np.percentile(np.abs(E100[strong]), 90), np.percentile(np.abs(E100[strong]), 99), V.FB_DC * CPD,
              np.mean(np.abs(E100[strong]) >= 5650), np.mean(np.abs(E100[strong]) >= 15855)))

    # ---------------------------------------------------------------------------------------------- B
    pr("\n" + "=" * 170)
    pr("SECTION B -- F7 census. FIXED threshold 103 wire (the r32/r33/r34 census); own-threshold list from highangle_stutter.py (r34 thr 100, r35 thr 100)")
    pr("=" * 170)
    fixed = {}
    for tag in ROUTES:
        r = routes[tag]
        eps = ST.fixed_thr_episodes(r); fixed[tag] = eps
        hi = [e for e in eps if e["ang"] >= 30]; f7 = [e for e in hi if e["fdom"] >= 6]
        hs = float(np.sum(r.eng & (np.abs(r.ang) >= 30)) / FS)
        pr("%s: engaged %.0f s, high-angle %.1f s | FIXED-103: episodes %d (%.1f s); >=30 deg %d (%.1f s); F7 %d (%.1f s) = %.2f per 100 s high-angle; fdom list (>=30): %s"
           % (tag, r.eng.sum() / FS, hs, len(eps), sum(e["dur"] for e in eps), len(hi), sum(e["dur"] for e in hi), len(f7), sum(e["dur"] for e in f7),
              100 * len(f7) / hs, " ".join("%.1f" % e["fdom"] for e in hi) or "-"))
        for e in hi:
            pr("     fixed-103 episode t0 %6.1f dur %3.1f fdom %.2f ang %4.0f v %3.1f rate amp %4.0f wire" % (e["t0"], e["dur"], e["fdom"], e["ang"], e["v"], e["ramp"]))
        own = EPIS[tag]; f7o = [x for x in own if x[2] >= 6]
        pr("     own-threshold list: %d at >=30 deg, F7 %d (%.1f s) = %.2f per 100 s" % (len(own), len(f7o), sum(x[1] for x in f7o), 100 * len(f7o) / HIGH_ANG_S[tag]))
        m = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 200); runs = V.runs(m, 100)
        pr("     |angle|>=30 & idx>=200: %.1f s; rate 6-8.5 Hz amp over >=1 s runs %.1f deg/s; driver-torque ring %.0f raw; cmd 6-8.5 Hz amp %.0f"
           % (m.sum() / FS, ST.band_amp(r.wire[runs]) / CPD if runs.sum() > 100 else np.nan, ST.band_amp(r.tq_raw[runs]) if runs.sum() > 100 else np.nan, ST.band_amp(r.cmd[runs]) if runs.sum() > 100 else np.nan))
        for lo, hi_ in ((0, 3), (3, 6), (6, 10), (10, 99)):
            mm = r.eng & (np.abs(r.ang) >= 30) & (r.vego >= lo) & (r.vego < hi_)
            pr("       high-angle time at v %2d-%2d m/s: %5.1f s  (idx>=40 & hands-light <1216: %5.1f s)" % (lo, hi_, mm.sum() / FS, (mm & (r.idx >= 40) & (np.abs(r.tq_raw) < 1216)).sum() / FS))
        # lower thresholds: is the ripple just under the detector floor?
        for thr in (80, 60, 40):
            eps2 = ST.fixed_thr_episodes(r, thr=thr); hi2 = [e for e in eps2 if e["ang"] >= 30]; f72 = [e for e in hi2 if e["fdom"] >= 6]
            pr("     threshold %3d wire: >=30 deg %2d episodes, F7 %2d (%.1f s) = %.2f per 100 s; F7 fdom %s" % (thr, len(hi2), len(f72), sum(e["dur"] for e in f72), 100 * len(f72) / hs, " ".join("%.1f" % e["fdom"] for e in f72) or "-"))

    # ---------------------------------------------------------------------------------------------- C
    pr("\n" + "=" * 170)
    pr("SECTION C1 -- own-threshold episodes (|angle|>=30) through the ON-CAR chain (r34: Kp LERP; r35: Kp flat 248), open loop on the measured rate")
    pr("=" * 170)
    for tag in ROUTES:
        r = routes[tag]; Rb = SIMS[tag][KP_ONCAR[tag]]
        Rkd0 = sim(r, *V280R2, kpY=KP_FLAT[KP_ONCAR[tag]], kd=0)
        for (t0, dur, fd) in EPIS[tag]:
            M, a, b = ST.episode_row(r, Rb, t0, dur, fd, Rkd0)
            M["cmd_amp7"] = ST.band_amp(r.cmd[b]); M["cmd_ampf"] = ST.band_amp(r.cmd[b], max(fd - 1, 1), fd + 1)
            ph_c, coh_c = S.phase_at(r.wire[b], r.cmd[b], fd)
            pr("  %s t0 %6.1f dur %3.1f fdom %.2f %s ang %4.0f v %3.1f idx %3.0f | corr %.2f | rate %5.1f ref %5.1f r/ref %.2f %-5s | Prail %.2f Drail %.2f fbclp %.2f cliff %.2f | brake sim %.2f meas %.2f | rAmp(6-8.5) %4.1f | rip/L sim %.2f meas %.2f (|T| %4.0f) | tqRng %4.0f | cAmp7 %4.0f cAmp@f %4.0f coh(cmd,rate)@f %.2f ph %+.0f | T re rate %+.0f"
               % (tag, t0, dur, fd, "F7" if fd >= 6 else "F2", M["ang"], M["v"], M["idx50"], M.get("corr_T", np.nan), M["rate_p50"], M["ref_p50"], M["rate_over_ref"], M["cls"],
                  M["P_rail"], M["D_rail"], M["clamped"], M["cliff"], M["E_brake"], M["brake_meas"], M["rate_amp"], M["Tsim_ripple_level"], M["Tmeas_ripple_level"], M["absT_meas_p50"],
                  M["tq_ring"], M["cmd_amp7"], M["cmd_ampf"], coh_c, ph_c, M["ph_Tmeas_re_rate"]))

    pr("\n" + "=" * 170)
    pr("SECTION C2 -- the deep-analysis DISCRIMINATORS. r34: the 11 F7 episodes (as r24_deembed.py). r35: every hands-light strong-turn 1 s window")
    pr("  (engaged, |angle|>=30, v<=10, |tq|<2240 raw, idx>=40, 0.5 s step) -- there are no F7 episodes to score. f0 = rate peak in 5.5-9.5 Hz;")
    pr("  |bar|/|rate| at f0 (wire counts / wire counts; ~10 on r34's episodes); L_servo = T/(T+r24), L_r24 = r24/(T+r24) with r24 from the bar (0xC6446 = 5244, 4-tap);")
    pr("  ph(bit) = phase of the 0x14A b4.4 sign(r24) square wave re the wire rate at f0 (r34 loaded stratum read +179 at 7 Hz); bit duty/flips per s")
    pr("=" * 170)
    hd = ("  %-5s %6s %4s %5s %4s %4s %4s | %5s %6s %5s %5s %5s | %6s %6s %6s | %5s | %-12s %-12s | %6s %6s %5s %5s"
          % ("route", "t0", "dur", "f0", "idx", "v", "tq50", "rate", "bar", "T", "|T|50", "rip/L", "ph_bar", "ph_T", "ph_r24", "b/r", "L_servo", "L_r24", "bitAmp", "ph_bit", "duty", "flp/s"))
    pr(hd)
    disc = {}
    for tag in ROUTES:
        r = routes[tag]; g = gs[tag]
        RD.KP_Y = KP_FLAT[KP_ONCAR[tag]]
        wins = [(t0, dur) for (t0, dur, fd) in EPIS[tag] if fd >= 6] if tag == "r34" else strong_windows(r, tq_max=2240)
        rows = [disc_row(g, t0, dur, b4s[tag], r) for t0, dur in wins]
        disc[tag] = rows
        for x in rows:
            pr("  %-5s %6.1f %4.1f %5.2f %4.0f %4.1f %4.0f | %5.1f %6.0f %5.0f %5.0f %5.2f | %+6.0f %+6.0f %+6.0f | %5.1f | %5.2f@%+5.0f %5.2f@%+5.0f | %6.2f %+6.0f %5.2f %5.1f"
               % (tag, x["t0"], x["dur"], x["f0"], x["idx"], x["v"], x["tq_p50"], x["Arate"], x["Abar"], x["AT"], x["Tlev"], x["rl"], x["ph_bar"], x["ph_T"], x["ph_r24"],
                  x["bar_over_rate"], abs(x["Ls"]), np.degrees(np.angle(x["Ls"])), abs(x["Lr"]), np.degrees(np.angle(x["Lr"])),
                  x["bit_amp"], x["ph_bit"], x["bit_duty"], x["bit_flips"]))
        if rows:
            med = lambda k: float(np.median([x[k] for x in rows]))  # noqa: E731
            pr("  %s MEDIAN over %d windows: f0 %.2f (p10-p90 %.2f-%.2f) | rate@f0 %.1f deg/s (6-8.5 band %.1f) bar %.0f T %.0f |T| %.0f rip/L %.2f (p90 %.2f) | ph_bar %+.0f ph_T %+.0f ph_r24 %+.0f | |bar|/|rate| %.1f | |L_servo| %.2f @ %+.0f | |L_r24| %.2f @ %+.0f | bit amp %.2f ph %+.0f (circ. mean %+.0f, R %.2f)"
               % (tag, len(rows), med("f0"), np.percentile([x["f0"] for x in rows], 10), np.percentile([x["f0"] for x in rows], 90), med("Arate"), med("rate7"), med("Abar"), med("AT"), med("Tlev"), med("rl"),
                  np.percentile([x["rl"] for x in rows], 90), med("ph_bar"), med("ph_T"), med("ph_r24"), med("bar_over_rate"),
                  np.median([abs(x["Ls"]) for x in rows]), np.median([np.degrees(np.angle(x["Ls"])) for x in rows]),
                  np.median([abs(x["Lr"]) for x in rows]), np.median([np.degrees(np.angle(x["Lr"])) for x in rows]),
                  med("bit_amp"), med("ph_bit"),
                  np.degrees(np.angle(np.nanmean(np.exp(1j * np.radians([x["ph_bit"] for x in rows]))))), abs(np.nanmean(np.exp(1j * np.radians([x["ph_bit"] for x in rows]))))))
            pr("  %s |L_r24| > 1 on %d of %d; |L_servo| > 1 on %d of %d; |T+r24| median %.0f" % (tag, sum(abs(x["Lr"]) > 1 for x in rows), len(rows), sum(abs(x["Ls"]) > 1 for x in rows), len(rows), np.median([abs(x["AT"] * np.exp(1j * np.radians(x["ph_T"])) + x["Ar24"] * np.exp(1j * np.radians(x["ph_r24"]))) for x in rows])))
    # r34 scored the same WINDOW way for a like-for-like; both routes split by hands (<1216 light / 1216-2240 on)
    r = routes["r34"]; RD.KP_Y = V.KP_Y
    w34 = strong_windows(r, tq_max=2240); rows34w = [disc_row(gs["r34"], t0, dur, b4s["r34"], r) for t0, dur in w34]
    disc["r34w"] = rows34w
    pr("  WINDOW METHOD, both routes, hands split (tq50 < 1216 light / >= 1216 on); F7-class window = rate@f0 >= 15 deg/s and rip/L >= 0.4")
    for tag, rows in (("r34", rows34w), ("r35", disc["r35"])):
        for lab, sub in (("ALL <2240", rows), ("hands-light <1216", [x for x in rows if x["tq_p50"] < 1216]), ("hands-on 1216-2240", [x for x in rows if x["tq_p50"] >= 1216])):
            if not sub:
                pr("  %s %-20s: no windows" % (tag, lab)); continue
            pr("  %s %-20s n %3d: f0 med %.2f (p10-p90 %.2f-%.2f) | rate@f0 %.1f (p90 %.1f; 6-8.5 band %.1f) | bar %.0f T %.0f |T| %.0f | rip/L %.2f (p90 %.2f) | |bar|/|rate| %.1f | |L_servo| %.2f@%+.0f |L_r24| %.2f@%+.0f (>1 on %d) | bit ph circ.mean %+.0f R %.2f | F7-class windows %d (%.1f s)"
               % (tag, lab, len(sub), np.median([x["f0"] for x in sub]), np.percentile([x["f0"] for x in sub], 10), np.percentile([x["f0"] for x in sub], 90),
                  np.median([x["Arate"] for x in sub]), np.percentile([x["Arate"] for x in sub], 90), np.median([x["rate7"] for x in sub]),
                  np.median([x["Abar"] for x in sub]), np.median([x["AT"] for x in sub]), np.median([x["Tlev"] for x in sub]),
                  np.median([x["rl"] for x in sub]), np.percentile([x["rl"] for x in sub], 90), np.median([x["bar_over_rate"] for x in sub]),
                  np.median([abs(x["Ls"]) for x in sub]), np.median([np.degrees(np.angle(x["Ls"])) for x in sub]),
                  np.median([abs(x["Lr"]) for x in sub]), np.median([np.degrees(np.angle(x["Lr"])) for x in sub]), sum(abs(x["Lr"]) > 1 for x in sub),
                  np.degrees(np.angle(np.nanmean(np.exp(1j * np.radians([x["ph_bit"] for x in sub]))))), abs(np.nanmean(np.exp(1j * np.radians([x["ph_bit"] for x in sub])))),
                  sum(1 for x in sub if x["Arate"] >= 15 and x["rl"] >= 0.4), 0.5 * sum(1 for x in sub if x["Arate"] >= 15 and x["rl"] >= 0.4) + 0.5 * bool(sum(1 for x in sub if x["Arate"] >= 15 and x["rl"] >= 0.4))))
    # broadband bit-vs-rate phase in the high-angle stratum
    for tag in ROUTES:
        r = routes[tag]; b4 = b4s[tag]
        if b4 is None:
            pr("  %s: no 0x14A b4 cache" % tag); continue
        m = r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10); runs = V.runs(m, 256)
        if runs.sum() < 512:
            continue
        bit = np.where((b4 >> 4) & 1, 1.0, -1.0)
        f, C = signal.coherence(r.wire[runs], bit[runs], fs=FS, nperseg=256); _, P = signal.csd(r.wire[runs], bit[runs], fs=FS, nperseg=256)
        fb_, Cb = signal.coherence(r.wire[runs], r.tq_raw[runs], fs=FS, nperseg=256); _, Pb = signal.csd(r.wire[runs], r.tq_raw[runs], fs=FS, nperseg=256)
        cells = []
        for fq in (3.9, 5.1, 6.2, 7.0, 7.8, 9.0, 10.2, 12.1, 15.2, 20.3):
            j = int(np.argmin(np.abs(f - fq)))
            cells.append("%4.1f Hz: bit %+4.0f (coh %.2f) bar %+4.0f (%.2f)" % (f[j], np.degrees(np.angle(P[j])), C[j], np.degrees(np.angle(Pb[j])), Cb[j]))
        pr("  %s broadband phase RE THE RATE over %.0f s of high-angle (v<=10) runs, bit duty %.3f: %s" % (tag, runs.sum() / FS, np.mean(bit[runs] > 0), " | ".join(cells)))
        pr("       b4 byte census (engaged): %s" % ", ".join("0x%02x:%d" % (u, c) for u, c in zip(*np.unique(b4[r.eng], return_counts=True))))

    # ---------------------------------------------------------------------------------------------- D
    pr("\n" + "=" * 170)
    pr("SECTION D -- WHAT REMAINS. D1: rate and tap spectra in strong turns (engaged, |angle|>=30, v<=10, >=1 s runs; Welch 256) r34 vs r35, band amplitudes deg/s and tap counts")
    pr("=" * 170)
    bands = ((1, 2), (2, 4), (4, 6), (6, 8.5), (8.5, 10), (10, 12), (12, 15), (15, 22))
    spec = {}
    for tag in ROUTES:
        r = routes[tag]
        for lab, m in (("ALL strong", r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10)),
                       ("hands-light idx>=40", r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10) & (np.abs(r.tq_raw) < 1216) & (r.idx >= 40)),
                       ("hands-on >=1216", r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10) & (np.abs(r.tq_raw) >= 1216)),
                       ("manual high-angle", ~r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10) & (r.vego >= 1))):
            runs = V.runs(m, 100)
            if runs.sum() < 300:
                pr("  %s %-20s: %.1f s -- too short" % (tag, lab, runs.sum() / FS)); continue
            f, Pr = welch_bands(r.wire[runs]); _, Pt = welch_bands(r.T_meas[runs]); _, Pc = welch_bands(r.cmd[runs]); _, Pq = welch_bands(r.tq_raw[runs])
            spec[(tag, lab)] = (f, Pr, Pt)
            mm = (f >= 3) & (f <= 15)
            pk = f[mm][np.argmax(Pr[mm])]
            pr("  %s %-20s %6.1f s | RATE deg/s: %s | peak 3-15 Hz %.1f Hz | TAP: %s | CMD 2-4/4-8.5/8.5-12: %.0f/%.0f/%.0f | BAR 4-8.5/8.5-12: %.0f/%.0f"
               % (tag, lab, runs.sum() / FS, " ".join("%g-%g %.2f" % (lo, hi_, band_amp_psd(f, Pr, lo, hi_) / CPD) for lo, hi_ in bands), pk,
                  " ".join("%g-%g %.0f" % (lo, hi_, band_amp_psd(f, Pt, lo, hi_)) for lo, hi_ in bands),
                  band_amp_psd(f, Pc, 2, 4), band_amp_psd(f, Pc, 4, 8.5), band_amp_psd(f, Pc, 8.5, 12), band_amp_psd(f, Pq, 4, 8.5), band_amp_psd(f, Pq, 8.5, 12)))
    # spectrum table hands-light 1-15 Hz at 0.39 Hz bins for the md
    k34, k35 = ("r34", "ALL strong"), ("r35", "ALL strong")
    if k34 in spec and k35 in spec:
        f, P34, T34 = spec[k34]; _, P35, T35 = spec[k35]
        pr("  hands-light strong-turn PSD ratio r35/r34 by bin (rate | tap): " + " ".join("%.1f:%.2f|%.2f" % (fq, P35[j] / P34[j], T35[j] / T34[j]) for j, fq in enumerate(f) if 1 <= fq <= 15))
        pr("  rate ASD sqrt(P) deg/s/rtHz r34 : " + " ".join("%.1f:%.2f" % (fq, np.sqrt(P34[j]) / CPD) for j, fq in enumerate(f) if 1 <= fq <= 15))
        pr("  rate ASD sqrt(P) deg/s/rtHz r35 : " + " ".join("%.1f:%.2f" % (fq, np.sqrt(P35[j]) / CPD) for j, fq in enumerate(f) if 1 <= fq <= 15))

    # the residual 7 Hz ring: threshold-40 F7 episodes through the on-car chain + discriminators (what a lower detector floor finds)
    pr("\n  D1b -- RESIDUAL 7 Hz: fixed-threshold-40 F7 episodes (|angle|>=30, fdom>=6) through the on-car chain and the discriminators")
    for tag in ROUTES:
        r = routes[tag]; g = gs[tag]; RD.KP_Y = KP_FLAT[KP_ONCAR[tag]]; Rb = SIMS[tag][KP_ONCAR[tag]]
        eps2 = [e for e in ST.fixed_thr_episodes(r, thr=40) if e["ang"] >= 30 and e["fdom"] >= 6]
        for e in eps2:
            M, a, b = ST.episode_row(r, Rb, e["t0"], e["dur"], e["fdom"])
            x = disc_row(g, e["t0"], e["dur"], b4s[tag], r)
            pr("  %s thr40 t0 %6.1f dur %3.1f fdom %.2f f0 %.2f ang %4.0f v %3.1f idx %3.0f tq %4.0f | rate %5.1f ref %5.1f r/ref %.2f %-5s | Prail %.2f cliff %.2f | rAmp %4.1f rate@f0 %4.1f | rip/L meas %.2f (|T| %4.0f) | tqRng %4.0f | b/r %4.1f | L_servo %.2f@%+.0f L_r24 %.2f@%+.0f | bit ph %+.0f | cmd@f %4.0f coh %.2f"
               % (tag, e["t0"], e["dur"], e["fdom"], x["f0"], M["ang"], M["v"], M["idx50"], x["tq_p50"], M["rate_p50"], M["ref_p50"], M["rate_over_ref"], M["cls"], M["P_rail"], M["cliff"], M["rate_amp"], x["Arate"],
                  M["Tmeas_ripple_level"], M["absT_meas_p50"], M["tq_ring"], x["bar_over_rate"], abs(x["Ls"]), np.degrees(np.angle(x["Ls"])), abs(x["Lr"]), np.degrees(np.angle(x["Lr"])), x["ph_bit"],
                  x["Acmd"], S.phase_at(r.wire[b], r.cmd[b], x["f0"])[1]))

    pr("\n  D2 -- the 2-4 Hz HUNT and the outer loop: episode detector 2.5-6 Hz (v280_map_profiles.episodes, per-route threshold) count; cmd->rate coherence 2-5 Hz in strong turns")
    for tag in ROUTES:
        r = routes[tag]
        hi = [(s, e) for s, e in r.eps if np.median(np.abs(r.ang[s:e])) >= 30]
        pr("  %s: 2.5-6 Hz detector thr %.0f wire: %d episodes engaged, %d at |angle|>=30 (%.1f s): %s" % (tag, r.thr, len(r.eps), len(hi), sum(e - s for s, e in hi) / FS,
           "; ".join("t0 %.1f dur %.1f ang %.0f idx %.0f" % (s / FS, (e - s) / FS, np.median(np.abs(r.ang[s:e])), np.median(r.idx[s:e])) for s, e in hi)))
        m = r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10) & (np.abs(r.tq_raw) < 1216); runs = V.runs(m, 256)
        if runs.sum() > 512:
            f, C = signal.coherence(r.cmd[runs], r.wire[runs], fs=FS, nperseg=256); _, P = signal.csd(r.cmd[runs], r.wire[runs], fs=FS, nperseg=256)
            pr("     cmd->rate coherence/phase hands-light strong turns: " + " ".join("%.1f Hz %.2f/%+.0f" % (f[j], C[j], np.degrees(np.angle(P[j]))) for j in range(len(f)) if 1.5 <= f[j] <= 12.5))

    pr("\n  D3 -- the STALLED-WHEEL class: runs >= 0.5 s, engaged, |angle|>=30, idx 40-200, hands-light (<1216), rate/ref < 0.5 through the on-car chain; P duty at its rail")
    for tag in ROUTES:
        r = routes[tag]; R = SIMS[tag][KP_ONCAR[tag]]
        ref = R["ref_deg"][r.i100]; w = np.abs(r.wire) / CPD
        st = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx <= 200) & (np.abs(r.tq_raw) < 1216) & (ref > 5) & (w < 0.5 * ref)
        d = np.diff(np.r_[0, st.astype(int), 0]); runs = [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= 50]
        n60 = sum(1 for a, b in runs if 60 <= np.median(r.idx[a:b]) <= 120)
        pr("  %s: %d stall runs (%.1f s), %d with idx 60-120; total stalled frames %.1f s of %.1f s eligible" % (tag, len(runs), sum(b - a for a, b in runs) / FS, n60, st.sum() / FS,
           (r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx <= 200) & (np.abs(r.tq_raw) < 1216)).sum() / FS))
        for a, b in runs[:12]:
            i = r.i100[a:b]
            pr("     t0 %6.1f dur %3.1f ang %4.0f v %3.1f idx %3.0f | rate %4.1f ref %5.1f | |T| %4.0f | P-rail %.2f |P|/clamp p50 %.2f | tq %4.0f | rate 6-8.5 %.1f 2-4 %.1f deg/s"
               % (a / FS, (b - a) / FS, np.median(np.abs(r.ang[a:b])), r.vego[a:b].mean(), np.median(r.idx[a:b]), np.median(w[a:b]), np.median(ref[a:b]), np.median(np.abs(r.T_meas[a:b])),
                  np.mean(np.abs(R["P_raw"][i]) >= V.P_CLAMP), np.median(np.abs(R["P_raw"][i])) / V.P_CLAMP, np.median(np.abs(r.tq_raw[a:b])),
                  ST.band_amp(r.wire[a:b]) / CPD if b - a >= 40 else np.nan, ST.band_amp(r.wire[a:b], 2, 4) / CPD if b - a >= 40 else np.nan))
        # prereg (k): held unmoving command
        k = r.eng & (r.idx >= 20) & (r.idx <= 40) & (w < 1.0) & (np.abs(r.ang) > 10)
        base = r.eng & (r.idx >= 20) & (r.idx <= 40)
        pr("  %s prereg (k) deadband: idx 20-40 & |rate|<1 deg/s & |angle|>10: %.1f s = %.3f of engaged idx 20-40 frames (%.1f s); same at idx 40-80: %.3f; idx 80-120: %.3f"
           % (tag, k.sum() / FS, k.sum() / max(base.sum(), 1), base.sum() / FS,
              np.mean(w[r.eng & (r.idx > 40) & (r.idx <= 80) & (np.abs(r.ang) > 10)] < 1.0), np.mean(w[r.eng & (r.idx > 80) & (r.idx <= 120) & (np.abs(r.ang) > 10)] < 1.0)))

    # ---------------------------------------------------------------------------------------------- E
    pr("\n" + "=" * 170)
    pr("SECTION E -- AUTHORITY: (iv) hands-light sustained full demand (idx=240 >= 0.3 s, wheel with the setpoint), (v) tap |T|; stalled push by idx bin; (vi), (viii)")
    pr("=" * 170)
    for tag in ROUTES:
        r = routes[tag]
        o = ST.stat_iv(r)
        pr("%s (iv) ceil %.1f | " % (tag, V.ceiling_degs(V280R2[0])) + " | ".join("<%4d: n=%4d %5.1f/%5.1f" % (t, *o[t]) for t in (2240, 1000, 400, 200))
           + " | (v) tap |T| p50/p90 %.0f/%.0f (tq<400); v50 %.1f" % (o["tap"][0], o["tap"][1], o["v"]))
        pr("      tq<400 split: WINDING n=%4d rate %5.1f/%5.1f |ang| %3.0f v %4.1f |T| %4.0f | RETURNING n=%4d rate %5.1f/%5.1f |ang| %3.0f v %4.1f |T| %4.0f" % (*o["wind"], *o["return"]))
        w = np.abs(r.wire) / CPD; R = SIMS[tag][KP_ONCAR[tag]]; ref = R["ref_deg"][r.i100]
        cells = []
        for lo, hi_ in ((20, 40), (40, 60), (60, 80), (80, 120), (120, 200), (200, 241)):
            m = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= lo) & (r.idx < hi_) & (np.abs(r.tq_raw) < 1216)
            ms = m & (w < 0.5 * ref)
            cells.append("idx %3d-%3d: n %5d |T| %4.0f rate %5.1f/ref %5.1f (stalled n %4d |T| %4.0f)" % (lo, hi_, m.sum(), np.median(np.abs(r.T_meas[m])) if m.sum() else np.nan,
                         np.median(w[m]) if m.sum() else np.nan, np.median(ref[m]) if m.sum() else np.nan, ms.sum(), np.median(np.abs(r.T_meas[ms])) if ms.sum() else np.nan))
        pr("      strong-turn hands-light push by idx: " + " | ".join(cells))
        m = r.eng & (np.abs(r.cmd) < 1300) & (r.T_meas != 0) & (r.wire != 0)
        D = dict(np.load(os.path.join(V.CACHE, tag + ".npz"))); t0 = D["t18"][0]
        e1 = np.interp(D["t1ab"] - t0, r.tg, r.eng.astype(float)) > 0.5
        pr("%s (vi) %.3f (n=%d) | (viii) %.4f, max |field| %d, field==313 anywhere: %d | manual %.0f s (1-8 m/s %.1f s, >=8 %.1f s)" % (
            tag, np.mean(np.sign(r.T_meas[m]) != np.sign(r.wire[m])), m.sum(), np.mean((r.fld[e1] & 511) >= 309), (r.fld[e1] & 511).max(), int(np.sum(r.fld == 313)),
            (~r.eng).sum() / FS, (~r.eng & (r.vego >= 1) & (r.vego < 8)).sum() / FS, (~r.eng & (r.vego >= 8)).sum() / FS))
        st = r.eng & (np.abs(r.ang) < 5) & (r.vego >= 8); runs = V.runs(st, 512)
        if runs.sum() > 512:
            f, Pr = welch_bands(r.wire[runs], nperseg=512)
            pr("%s straight >=8 m/s engaged %.0f s: rate 2-4 Hz amp %.2f deg/s, 3.5-4.3 %.2f, 6-8.5 %.2f, 8.5-10 %.2f, 10-12 %.2f; cmd 2-4 %.0f" % (
                tag, st.sum() / FS, ST.band_amp(r.wire[runs], 2, 4) / CPD, ST.band_amp(r.wire[runs], 3.5, 4.3) / CPD, ST.band_amp(r.wire[runs]) / CPD,
                band_amp_psd(f, Pr, 8.5, 10) / CPD, band_amp_psd(f, Pr, 10, 12) / CPD, ST.band_amp(r.cmd[runs], 2, 4)))

    out = os.path.join(HERE, "_scratch", "strongturn_r35.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
