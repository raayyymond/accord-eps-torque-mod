# -*- coding: utf-8 -*-
"""KPFLAT SIZING -- "flatten Kp(idx) to its low-demand value" as a lever against the 6.5-7.4 Hz strong-turn ripple
on V280 rev 2 (r32/r33 F7 episodes: idx 26-173, wheel at 0.6-1.2x the reference, |angle| >= 30, v 2-9 m/s, P linear
62-79 % of ticks).  Subagent kpflat, 2026-09-03.  SIZING ONLY -- builds nothing.

Parts
  1  the Kp / Kd LERP tables of ALL 28 slots, read from the V280 rev 2 image (pointer banks 0xCB994 / 0xCB7D4),
     cross-checked by a raw little-endian byte scan.
  2  inner-loop L_in(f) = L_fw(Kp, Kd, lag, fb) * G(f), G identified from the CAN-427 tap in the high-angle low-speed
     stratum (plant_id_v278r3_tap.py's pools, extended to 1-30 Hz), for Kp as-is per idx and Kp flattened; GM / PM /
     crossover / sensitivity peak / K_crit = the Kp at which the linear loop reaches |L| = 1 at -180 deg.
  3  describing function on the F7 episode frames: N = fundamental gain of the P clamp on the chain's own P, so
     K_eff = N * Kp(idx) is the loop gain the limit cycle self-regulates to (a MEASUREMENT of K_crit that needs no
     plant); open-loop chain with Kp x 1.0/0.8/0.62/0.5 and the flats: P-linear fraction, T ripple/level, and the
     steady tracking / authority cost.
  4  alternatives: Kd, the output-lag pole (0xC63EC/EE), the two-sample feedback sum (0xC63E8/EA) -- same margins.

Arithmetic mirrors the FUN_00028ea6 decompile as in lowcmd_loopgain_v112_v278_v280.py / v280_map_profiles.py.
Run:  python analysis-2020accord/studies/v280/kpflat_sizing.py
"""
import os
import struct
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "rlog-tools", "studies", "osc-highangle"))
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import plant_id_v278r3_tap as PI              # noqa: E402
import v280_map_profiles as V                 # noqa: E402
import servo_at_reference as S                # noqa: E402
import strongturn_r32_r33 as ST               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IMG = LG.FW + LG.IMAGES["V280r2"]
FS1K, FS = 1000.0, 100.0
OUT = os.path.join(HERE, "_scratch", "kpflat_sizing.txt")
L = []


def pr(s=""):
    print(s)
    L.append(s)


# ======================================================================================================
# PART 1 -- the tables, all 28 slots, from the V280 image + raw scan
# ======================================================================================================
def part1():
    b = open(IMG, "rb").read()
    u16 = lambda a: struct.unpack_from("<H", b, a)[0]      # noqa: E731
    u32 = lambda a: struct.unpack_from("<I", b, a)[0]      # noqa: E731

    def rec(base, n):
        return u16(base), [u16(base + 2 + 2 * i) for i in range(n)], [u16(base + 2 + 2 * n + 2 * i) for i in range(n)]

    pr("=" * 120)
    pr("PART 1 -- Kp bank 0xCB994 (28 ptrs -> 5-knot LERP records: hdr, X[5], Y[5]) and Kd bank 0xCB7D4 (4-knot), V280 rev 2 image")
    pr("=" * 120)
    kp, kd = {}, {}
    for s in range(28):
        p = u32(0xCB994 + 4 * s); h, X, Y = rec(p, 5); kp[s] = (p, X, Y)
        q = u32(0xCB7D4 + 4 * s); h2, X2, Y2 = rec(q, 4); kd[s] = (q, X2, Y2)
        pr("  slot %2d  Kp @0x%05X hdr %d X %-24s Y %-26s | Kd @0x%05X hdr %d X %-16s Y %s%s" % (
            s, p, h, X, Y, q, h2, X2, Y2, "   <-- LIVE (selector 7)" if s == 7 else ""))
    # distinct shapes
    shapes = {}
    for s, (p, X, Y) in kp.items():
        shapes.setdefault((tuple(X), tuple(Y)), []).append(s)
    pr("  distinct Kp shapes: %d" % len(shapes))
    for (X, Y), ss in shapes.items():
        pr("     X %-24s Y %-26s slots %s" % (list(X), list(Y), ss))
    # raw LE scan: the slot-7 X pattern, and the count of 4-knot Kd X patterns
    pat = struct.pack("<5H", *kp[7][1])
    hits = [i for i in range(0x13000, len(b) - 10) if b[i:i + 10] == pat]
    pat2 = struct.pack("<4H", *kd[7][1])
    hits2 = [i for i in range(0x13000, len(b) - 8) if b[i:i + 8] == pat2]
    pr("  raw LE scan: Kp X pattern %s at %s (= the X fields of the slot 0/1/3/4/6/7 records, +2 from each ptr)" % (kp[7][1], [hex(h) for h in hits]))
    pr("  raw LE scan: Kd X pattern %s: %d hits; the 28 bank pointers +2 are %s of them" % (
        kd[7][1], len(hits2), "all" if all((kd[s][0] + 2) in hits2 for s in range(28)) else "NOT all"))
    pr("  reachable slots are 0-9 (selector max 9, kit record); slot 7 = X 0 68 112 136 208 / Y 248 512 645 696 696 (Kp/256 = 0.97 .. 2.72);")
    pr("  Kd is 128 on slots 0,1,3,4,6,7,8,9 and 64 on 2,5,10+; Kd X ends at 32 so Kd is FLAT over the whole idx range that matters.")
    pr("  Kp at idx: " + "  ".join("%d:%.0f" % (i, np.interp(i, kp[7][1], kp[7][2])) for i in (0, 12, 26, 40, 58, 68, 90, 112, 136, 173, 208, 240)))
    return kp, kd


# ======================================================================================================
# PART 2 -- inner-loop margins vs Kp with the identified plant
# ======================================================================================================
def L_fw(c, f, kp, kd=128, lag=None, fb=None, post=254):
    """T counts per deg/s of wheel rate, open loop, one 1 kHz tick of transport; kp = Kp table value (P = E*kp>>8)."""
    z = np.exp(1j * 2 * np.pi * f / FS1K)
    la, lb = lag if lag else (c["lag_a"], c["lag_b"])
    fa, fbb = fb if fb else (c["fb_a"], c["fb_b"])
    Hlag = (lb / 1024.0) * (1 + 1 / z) / (1 - (la / 1024.0) / z) / 32.0
    Hfb = (fbb / 1024.0) * (1 + 1 / z) / (1 - (fa / 1024.0) / z)
    C = (kp / 256.0 + kd / 8.0 * (1 - 1 / z)) * (post / 256.0) * Hlag * (c["gain"] / 32768.0)
    return C * Hfb * LG.CPD / z


def margins(f, Lc, lo=1.0, hi=30.0):
    band = (f >= lo) & (f <= hi)
    fb_, mag = f[band], np.abs(Lc[band])
    ph = np.degrees(np.unwrap(np.angle(Lc[band])))
    out = dict(pm=None, gm=None, fc=None, f180=None, sens=None, fsens=None)
    # highest unity crossing
    for i in range(len(fb_) - 2, -1, -1):
        if (mag[i] - 1) * (mag[i + 1] - 1) <= 0 and mag[i] != mag[i + 1]:
            t = (1 - mag[i]) / (mag[i + 1] - mag[i])
            out["fc"] = fb_[i] + t * (fb_[i + 1] - fb_[i]); out["pm"] = 180 + ph[i] + t * (ph[i + 1] - ph[i]); break
    for i in range(len(fb_) - 1):
        if (ph[i] + 180) * (ph[i + 1] + 180) <= 0 and ph[i] != ph[i + 1]:
            t = (-180 - ph[i]) / (ph[i + 1] - ph[i])
            out["f180"] = fb_[i] + t * (fb_[i + 1] - fb_[i]); out["gm"] = 1 / (mag[i] + t * (mag[i + 1] - mag[i])); break
    sens = 1 / np.abs(1 + Lc[band])
    out["sens"] = float(sens.max()); out["fsens"] = float(fb_[np.argmax(sens)])
    return out


def fmt_m(m):
    return "%s  %s  Ms %.2f @ %4.1f Hz" % (
        ("PM %4.0f deg @ %4.1f Hz" % (m["pm"], m["fc"])) if m["pm"] is not None else "PM  --- (no unity crossing)  ",
        ("GM %5.2fx @ %4.1f Hz" % (m["gm"], m["f180"])) if m["gm"] is not None else "GM  --- (no -180 in band) ",
        m["sens"], m["fsens"])


def part2(c, kp7):
    pr("\n" + "=" * 120)
    pr("PART 2 -- plant G = rate/T from the tap (plant_id pools, r31+r32+r33), the high-angle low-speed strata, 1-30 Hz")
    pr("=" * 120)
    G = {r: PI.load(r) for r in PI.ROUTES}
    pools, secs = {}, {}

    def masks(g):
        v, a, tq, idx = g["vego"], np.abs(g["ang"]), np.abs(g["tq"]), LG.idx_of_cmd(np.round(g["cmd"]))
        return {"v<=10 |ang|>=30 (A2/A3 stratum)": g["eng"] & (v <= 10) & (a >= 30),
                "v>=20 |ang|<8 |tq|<500 (highway ref)": g["eng"] & (v >= 20) & (a < 8) & (tq < 500)}
    for r, g in G.items():
        for name, m in masks(g).items():
            pools.setdefault(name, PI.Pool())
            minseg = 4.0 if "F7" not in name else 2.56
            for s, e in PI.runs(m, int(minseg * FS)):
                if e - s < PI.NPERSEG:
                    continue
                pools[name].add({"T": g["T"][s:e], "r": g["rate_x"][s:e], "c": g["cmd"][s:e], "q": g["tq"][s:e]})
                secs[name] = secs.get(name, 0) + (e - s) / FS
    plants = {}
    for name, P in pools.items():
        f = P.f
        Gd, Gc, Gq = P.tf("T", "r"), P.tf("T", "r", ref="c"), P.tf("T", "r", ref="q")
        lo = (f >= 1) & (f <= 2)
        sgn = 1.0 if abs(np.angle(np.mean(Gd[lo]))) <= np.pi / 2 else -1.0
        plants[name] = dict(f=f, direct=sgn * Gd, cmdIV=sgn * Gc, tqIV=sgn * Gq, n=P.n, cTr=P.coh("T", "r"), cqr=P.coh("q", "r"), ccr=P.coh("c", "r"))
        pr("  %-42s %6.0f s, %4d windows | |G| x1e-3 / phase / coh at 2,4,6,8,10,12 Hz" % (name, secs[name], P.n))
        for est, coh in (("direct", "cTr"), ("tqIV", "cqr"), ("cmdIV", "ccr")):
            pr("     %-7s " % est + "  ".join("%2.0fHz %5.1f/%5.0f/%.2f" % (x, 1e3 * abs(PI.at(f, plants[name][est], x)), np.degrees(np.angle(PI.at(f, plants[name][est], x))), PI.at(f, plants[name][coh], x)) for x in (2, 4, 6, 8, 10, 12)))

    # ---- parametric plant fits on the coherent 3-9.5 Hz band of the A2/A3 stratum ------------------------
    from scipy.optimize import least_squares
    A3 = plants["v<=10 |ang|>=30 (A2/A3 stratum)"]
    f = A3["f"]; sel = (f >= 3.0) & (f <= 9.5)
    w = 2 * np.pi * f[sel]

    def m_pd(p, w):
        K, fp, tau = p; return K * np.exp(-1j * w * tau) / (1 + 1j * w / (2 * np.pi * fp))

    def m_2o(p, w):
        K, fn, z, tau = p; wn = 2 * np.pi * fn
        return K * wn ** 2 * np.exp(-1j * w * tau) / ((1j * w) ** 2 + 2 * z * wn * 1j * w + wn ** 2)

    def fit(model, p0, lo, hi, Gm, wt):
        res_ = lambda p: np.r_[wt * np.log(np.abs(model(p, w)) / np.abs(Gm)), wt * np.angle(model(p, w) / Gm)]   # noqa: E731
        return least_squares(res_, p0, bounds=(lo, hi))
    fits = {}
    fits["pole+delay, tqIV"] = (m_pd, fit(m_pd, [0.08, 5, 0.02], [0, 0.5, 0], [1, 50, 0.2], A3["tqIV"][sel], np.sqrt(A3["cqr"][sel])).x)
    fits["pole+delay, direct"] = (m_pd, fit(m_pd, [0.08, 5, 0.02], [0, 0.5, 0], [1, 50, 0.2], A3["direct"][sel], np.sqrt(A3["cTr"][sel])).x)
    fits["2nd-order+delay, tqIV"] = (m_2o, fit(m_2o, [0.08, 6, 0.5, 0.01], [0, 1, 0.05, 0], [1, 50, 3, 0.2], A3["tqIV"][sel], np.sqrt(A3["cqr"][sel])).x)
    pr("\n  PARAMETRIC PLANT FITS (weighted by sqrt coherence, 3-9.5 Hz of the A2/A3 stratum; the raw grid is too coarse/noisy above 8.6 Hz for margins):")
    for k, (mod, p) in fits.items():
        pr("    %-24s params %s ; model |G|x1e-3 / phase at 4/6/7/8/10 Hz: %s" % (k, np.round(p, 4).tolist(), "  ".join(
            "%.1f/%.0f" % (1e3 * abs(mod(p, 2 * np.pi * x)), np.degrees(np.angle(mod(p, 2 * np.pi * x)))) for x in (4, 6, 7, 8, 10))))
    pr("    raw tqIV at the same f: " + "  ".join("%.1f/%.0f" % (1e3 * abs(PI.at(f, A3["tqIV"], x)), np.degrees(np.angle(PI.at(f, A3["tqIV"], x)))) for x in (4, 6, 7, 8, 10)))

    ff = np.linspace(0.5, 40, 4000)
    res = {}
    variants = [("as-is idx 26", float(np.interp(26, *kp7))), ("as-is idx 68", 512), ("as-is idx 112", 645), ("as-is idx 173", 696),
                ("FLAT 473 (Kp58)", 473), ("FLAT 400", 400), ("FLAT 341 (Kp24)", 341), ("FLAT 295 (Kp12)", 295), ("FLAT 248 (Kp0)", 248), ("FLAT 200", 200)]
    pr("\n  INNER LOOP L_in = L_fw(Kp, Kd 128, stock lag/fb) * G_fit, margins on a fine grid 0.5-40 Hz.  Ms = peak |1/(1+L)|.")
    pr("  K_crit(linear) = the flat Kp at which GM = 1 (D fixed at Kd 128, so it is found by bisection, not Kp/GM).")
    for k, (mod, p) in fits.items():
        Gf = mod(p, 2 * np.pi * ff)
        pr("\n  plant %s" % k)
        pr("    %-18s %5s | |L| @ 4 / 6 / 7 / 8 / 10 Hz | ph@7 | margins" % ("Kp", "Kp"))
        for lab, kpv in variants:
            Lc = np.array([L_fw(c, x, kpv) for x in ff]) * Gf; m = margins(ff, Lc, 0.5, 40)
            res[(k, lab)] = m
            pr("    %-18s %5.0f | %s | %+5.0f | %s" % (lab, kpv, " ".join("%5.2f" % abs(PI.at(ff, Lc, x)) for x in (4, 6, 7, 8, 10)),
                                                     np.degrees(np.angle(PI.at(ff, Lc, 7.0))), fmt_m(m)))
        lo_, hi_ = 150.0, 900.0
        for _ in range(30):
            mid = 0.5 * (lo_ + hi_)
            m = margins(ff, np.array([L_fw(c, x, mid) for x in ff]) * Gf, 0.5, 40)
            if m["gm"] is None or m["gm"] > 1: lo_ = mid
            else: hi_ = mid
        res[(k, "Kcrit")] = 0.5 * (lo_ + hi_)
        pr("    K_crit(linear, Kd 128) = %.0f" % res[(k, "Kcrit")])
    plants["fits"] = fits; plants["ff"] = ff
    return plants, res


# ======================================================================================================
# PART 3 -- describing function on the F7 episode frames (open-loop chain on the measured rate)
# ======================================================================================================
def part3(c, kp7):
    pr("\n" + "=" * 120)
    pr("PART 3 -- F7 episodes r32/r33 through the V280 rev 2 chain (line map, clamp 46080): the P clamp's describing function and Kp variants")
    pr("=" * 120)
    ST.V.GAIN, ST.V.OUT_CAP = ST.GAIN, ST.CAP
    routes = {t: V.Route(t) for t in ("r32", "r33")}
    Y280, clamp = ST.V280R2
    chain = (254 / 256.0) * (2 * c["lag_b"] / (1024 - c["lag_a"]) / 32) * (c["gain"] / 32768.0)      # T per unit of (P+D) at DC
    pr("  chain (post 254/256 * lag DC * GAIN/32768) = %.4f T per count of P ; 1 deg/s of rate error = %.1f counts of E" % (chain, V.FB_DC * V.CPD))
    kp_scales = [("x1.00", 1.0, None), ("x0.80", 0.8, None), ("x0.62", 0.62, None), ("x0.50", 0.5, None),
                 ("FLAT 473", None, 473), ("FLAT 341", None, 341), ("FLAT 295", None, 295), ("FLAT 248", None, 248)]
    pr("  per episode: idx50, Kp(idx50), N = amp7(clip P)/amp7(P raw) [the clamp's fundamental gain on the chain's own P], K_eff = N*Kp,")
    pr("  P-linear fraction and sim T ripple/level (6-8.5 Hz amp / |T| p50) under each Kp variant (open loop on the RECORDED rate),")
    pr("  steady tracking cost = |T_meas| p50 / (Kp/256 * chain) in deg/s of rate error, and as a fraction of the episode's reference.")
    hdr = "  %-3s %6s %4s %4s %5s | %5s %5s %5s | " % ("rte", "t0", "idx", "Kp", "N", "K_eff", "Plin", "rip/L")
    hdr += " ".join("%9s" % k for k, _, _ in kp_scales) + " | " + " ".join("%9s" % k for k, _, _ in kp_scales) + " | err deg/s @ 1.0 .62 F295 (ref)"
    pr(hdr)
    pr("  %49s %s | %s |" % ("", "P-linear fraction".center(len(kp_scales) * 10 - 1), "sim T ripple/level".center(len(kp_scales) * 10 - 1)))
    rows = []
    for tag, r in routes.items():
        sims = {}
        for lab, sc, flat in kp_scales:
            kpY = V.KP_Y * sc if sc else np.full(5, float(flat))
            R = r.simulate(Y280, kpY=kpY, fb_clamp=clamp)
            R["ref_deg"] = 32 * np.abs(R["sp"]) / V.FB_DC / V.CPD
            sims[lab] = R
        for (t0, dur, fd) in ST.EPIS[tag]:
            if fd < 6:
                continue
            s, e = int(round(t0 * FS)), int(round((t0 + dur) * FS))
            m100 = np.zeros_like(r.eng); m100[s:e] = True; m100 &= r.eng
            m1k = np.zeros_like(r.eng1k); m1k[int(t0 * FS1K):int((t0 + dur) * FS1K)] = True; m1k &= r.eng1k
            if np.abs(r.ang[m100]).mean() < 30:
                continue
            i = r.i100[m100]
            R0 = sims["x1.00"]
            idx50 = float(np.median(r.idx[m100])); kpv = float(np.interp(idx50, *kp7))
            Praw = R0["P_raw"][i]; Pcl = np.clip(Praw, -V.P_CLAMP, V.P_CLAMP)
            N = S.band_amp(Pcl) / max(S.band_amp(Praw), 1e-9)
            plin, ripl = [], []
            for lab, _, _ in kp_scales:
                R = sims[lab]
                plin.append(float(np.mean(np.abs(R["P_raw"][m1k]) < V.P_CLAMP)))
                Ts = R["T"][i]
                ripl.append(S.band_amp(Ts) / max(np.median(np.abs(Ts)), 1))
            Tm = np.median(np.abs(r.T_meas[m100]))
            ref = float(np.median(R0["ref_deg"][i]))
            err = lambda k: Tm / (k / 256.0 * chain) / (V.FB_DC * V.CPD)   # noqa: E731
            rows.append(dict(tag=tag, t0=t0, idx=idx50, kp=kpv, N=N, keff=N * kpv, plin=plin, ripl=ripl, Tm=Tm, ref=ref,
                             err=(err(kpv), err(0.62 * kpv), err(295)), rate=float(np.median(np.abs(r.wire[m100])) / V.CPD)))
            pr("  %-3s %6.1f %4.0f %4.0f %5.2f | %5.0f %5.2f %5.2f | %s | %s | %5.1f %5.1f %5.1f (%4.1f; rate %4.1f)" % (
                tag, t0, idx50, kpv, N, N * kpv, plin[0], ripl[0], " ".join("%9.2f" % x for x in plin), " ".join("%9.2f" % x for x in ripl),
                *rows[-1]["err"], ref, rows[-1]["rate"]))
    ke = np.array([x["keff"] for x in rows]); kk = np.array([x["kp"] for x in rows])
    pr("  K_eff = N*Kp(idx): median %.0f, range %.0f-%.0f ; N median %.2f (range %.2f-%.2f) ; K_eff/Kp median %.2f" % (
        np.median(ke), ke.min(), ke.max(), np.median([x["N"] for x in rows]), min(x["N"] for x in rows), max(x["N"] for x in rows), np.median(ke / kk)))
    pr("  Reading: a limit cycle self-regulates its effective gain to the loop's critical gain. K_eff is therefore a per-episode MEASUREMENT of")
    pr("  K_crit at that episode's operating point (plant included, no ID needed).  A flat Kp BELOW min(K_eff) leaves no amplitude at which the")
    pr("  loop can sustain the cycle; a flat Kp between min and max kills some episodes and leaves others (with LESS clamping = closer to sinusoidal).")
    return rows


def part3b(c, kp7):
    pr("\n  AUTHORITY / TRACKING COST at full demand (idx 240, reference 133.6 deg/s on the line map), P-only steady state, Kp variants:")
    pr("  P rails at |E| = 15360*256/Kp -> the rate error at which the lane delivers its full push; steady rate under a load needing T_load = ref - T_load/(Kp/256*chain*247)")
    chain = (254 / 256.0) * (2 * c["lag_b"] / (1024 - c["lag_a"]) / 32) * (c["gain"] / 32768.0)
    ref = 32 * 1032 / (V.FB_DC * V.CPD)
    pr("  %-16s %5s | rail err deg/s | full push below deg/s | rate at T_load 600 / 1000 / 1500 / 2472 (deg/s)  | mid-demand idx 100 (ref %.1f): rail err, rate @ T 600 / 1000" % (
        "Kp", "Kp", 32 * np.interp(100, V.MAP_X, ST.V280R2[0]) / (V.FB_DC * V.CPD)))
    ref100 = 32 * np.interp(100, V.MAP_X, ST.V280R2[0]) / (V.FB_DC * V.CPD)
    for lab, kpv in (("as-is (696)", 696), ("FLAT 473", 473), ("FLAT 400", 400), ("FLAT 341", 341), ("FLAT 295", 295), ("FLAT 248", 248)):
        g = kpv / 256.0 * chain * V.FB_DC * V.CPD          # T per deg/s of rate error
        rail = V.P_CLAMP * 256 / kpv / (V.FB_DC * V.CPD)
        rates = [max(ref - T / g, ref - rail) if T / g <= rail else ref - rail for T in (600, 1000, 1500, 2472)]
        k100 = kpv if "FLAT" in lab else float(np.interp(100, *kp7))
        g100 = k100 / 256.0 * chain * V.FB_DC * V.CPD; rail100 = V.P_CLAMP * 256 / k100 / (V.FB_DC * V.CPD)
        pr("  %-16s %5.0f | %14.1f | %21.1f | %s  | Kp %.0f: %.1f, %s" % (
            lab, kpv, rail, ref - rail, " / ".join("%5.1f" % x for x in rates), k100, rail100,
            " / ".join("%5.1f" % max(ref100 - T / g100, ref100 - rail100) for T in (600, 1000))))
    pr("  (T_load 2472 = the tap rail = full delivered torque; 'full push below' = the wheel rate under which the lane is already at its P rail.)")


# ======================================================================================================
# PART 4 -- alternatives: Kd, output-lag pole, feedback sum
# ======================================================================================================
def part4(c, plants, kp7):
    pr("\n" + "=" * 120)
    pr("PART 4 -- alternative levers, same margins, Kp as-is at idx 112 (645) and idx 26 (%.0f), flats 341/295, on the parametric plant fits" % np.interp(26, *kp7))
    pr("=" * 120)
    alts = [("stock (Kd 128, lag 992/507, fb 923/1560)", dict()),
            ("Kd 0", dict(kd=0)), ("Kd 64", dict(kd=64)), ("Kd 192", dict(kd=192)), ("Kd 256", dict(kd=256)), ("Kd 384", dict(kd=384)),
            ("lag pole 5.05 -> 10 Hz (a 960, b 1014, DC held)", dict(lag=(960, 1014))),
            ("lag pole -> 20 Hz (a 896, b 2027)", dict(lag=(896, 2027))),
            ("lag pole -> 40 Hz (a 790, b 3706)", dict(lag=(790, 3706))),
            ("fb pole 16.5 -> 33 Hz (a 832, b 2965, DC held)", dict(fb=(832, 2965))),
            ("fb pole -> 66 Hz (a 676, b 5374)", dict(fb=(676, 5374))),
            ("fb single-sample x2 (no z^-1 sum; a 923, b 3120)", "single")]
    ff = plants["ff"]
    for k, (mod, p) in plants["fits"].items():
        Gf = mod(p, 2 * np.pi * ff)
        for kpv in (645, float(np.interp(26, *kp7)), 341, 295):
            pr("\n  plant %s, Kp %.0f" % (k, kpv))
            pr("    %-50s | |L|@7  ph@7 | %s" % ("lever", "margins"))
            for lab, kw in alts:
                if kw == "single":
                    def Lf(x):
                        z = np.exp(1j * 2 * np.pi * x / FS1K)
                        Hfb = 2 * (c["fb_b"] / 1024.0) / (1 - (c["fb_a"] / 1024.0) / z)
                        Hlag = (c["lag_b"] / 1024.0) * (1 + 1 / z) / (1 - (c["lag_a"] / 1024.0) / z) / 32.0
                        C = (kpv / 256.0 + 128 / 8.0 * (1 - 1 / z)) * (254 / 256.0) * Hlag * (c["gain"] / 32768.0)
                        return C * Hfb * LG.CPD / z
                    Lc = np.array([Lf(x) for x in ff]) * Gf
                else:
                    Lc = np.array([L_fw(c, x, kpv, **kw) for x in ff]) * Gf
                m = margins(ff, Lc, 0.5, 40)
                pr("    %-50s | %5.2f %+5.0f | %s" % (lab, abs(PI.at(ff, Lc, 7.0)), np.degrees(np.angle(PI.at(ff, Lc, 7.0))), fmt_m(m)))
        pr("\n  COMBINED grid, plant %s: Kp flat x Kd x fb pole" % k)
        for kpv in (400, 341, 295, 248):
            for kd in (128, 192, 256):
                for fbl, fbv in (("fb stock", None), ("fb 33 Hz", (832, 2965))):
                    Lc = np.array([L_fw(c, x, kpv, kd=kd, fb=fbv) for x in ff]) * Gf; m = margins(ff, Lc, 0.5, 40)
                    pr("    Kp %3d Kd %3d %-9s | %s" % (kpv, kd, fbl, fmt_m(m)))
    # highway: the lane-change regime runs at idx 2-12 where Kp is already 256-295 -> a flat at 295 is inert there
    H = plants["v>=20 |ang|<8 |tq|<500 (highway ref)"]; f = H["f"]
    pr("\n  HIGHWAY (idx 2-12, Kp as-is 256-295): inner closed-loop |rate/sp| at 1/2/3 Hz (direct G) for Kp 268 (idx 5) vs flat 295 vs 645:")
    for kpv in (268, 295, 645):
        Lc = np.array([L_fw(c, x, kpv) for x in f]) * H["direct"]
        CL = Lc / (1 + Lc)
        pr("    Kp %3d: |L| @1/2/3 Hz %s ; |L/(1+L)| %s" % (kpv, " ".join("%.2f" % abs(PI.at(f, Lc, x)) for x in (1, 2, 3)), " ".join("%.2f" % abs(PI.at(f, CL, x)) for x in (1, 2, 3))))
    # firmware-side phase budget at 7 Hz
    pr("\n  firmware phase budget at 7 Hz (Kp 645, Kd 128): " + ", ".join("%s %+.0f deg" % (k, v) for k, v in (
        ("P+D controller", np.degrees(np.angle(645 / 256.0 + 16 * (1 - np.exp(-1j * 2 * np.pi * 7 / FS1K))))),
        ("output lag", np.degrees(np.angle(LG.H_lag(c, 7.0)))), ("fb sum", np.degrees(np.angle(LG.H_fb(c, 7.0)))), ("tick", -360 * 7 / FS1K))))
    for kpv in (248, 295, 400, 645):
        pr("  D lead at 7 Hz vs Kp %3d: Kd 128 %+.0f deg, Kd 256 %+.0f deg, Kd 384 %+.0f deg ; |D|/|P| at 7 Hz: %.2f / %.2f / %.2f" % (
            kpv, *[np.degrees(np.angle(kpv / 256.0 + kd / 8.0 * (1 - np.exp(-1j * 2 * np.pi * 7 / FS1K)))) for kd in (128, 256, 384)],
            *[abs(kd / 8.0 * (1 - np.exp(-1j * 2 * np.pi * 7 / FS1K))) / (kpv / 256.0) for kd in (128, 256, 384)]))


def main():
    kp, kd = part1()
    kp7 = (np.array(kp[7][1], float), np.array(kp[7][2], float))
    c = LG.read_build(IMG)
    plants, res = part2(c, kp7)
    rows = part3(c, kp7)
    part3b(c, kp7)
    part4(c, plants, kp7)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
