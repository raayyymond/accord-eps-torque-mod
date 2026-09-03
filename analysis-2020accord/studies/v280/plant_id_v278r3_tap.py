# -*- coding: utf-8 -*-
"""PLANT IDENTIFICATION from V278 rev 3's own CAN-427 delivered-torque tap: G = wheel rate / T, on r31, r32, r33.

T      = gp-0x6b38 as tapped on 0x1AB: fld = ((b0&3)<<8)|b1, T = sign(fld>>9) * (fld&511)*8   (50 Hz, +-2481 rail reads 310)
rate   = 0x18F b2-3 (100 Hz), 8 counts/deg/s; the firmware's own operand is x = -wire (gp-0x6a56), so G is quoted for
         rate_x = -wire/8 in deg/s (the sign the PID sees).  cmd = 0xE4 b0-1 (src 129), tq = 0x18F b0-1 * 1.024 (raw).
Lateral engaged = 0x18F b4.3 (SCA) AND 0xE4 b2.7 (STEER_REQUEST).

T -> rate is INSIDE the closed rate loop (T is a function of rate through Kp/Kd), so the direct estimate
S_Tr/S_TT is biased toward -1/C wherever the loop's own noise dominates.  Two instrumental estimates are given:
   G_cmd = S_cr / S_cT   (cmd as the exogenous reference; cmd itself is closed through openpilot at ~1-2 Hz, weaker at 4-8 Hz)
   G_tq  = S_qr / S_qT   (driver torque as the reference; biased where the driver is reacting to the motion)
with the coherences that say where each is usable.  Welch, nperseg 256 @ 100 Hz (0.39 Hz bins), Hann, per contiguous
engaged stretch >= 4 s, cross-spectra pooled by window count.  Strata: speed <=10 / 10-20 / >=20 m/s x |angle| < 8 / >= 30 deg,
plus a hands-light sub-stratum (|tq| < 500 raw) at >= 20 m/s, < 8 deg -- the lane-change regime the operator reported.

Then the margins: INNER loop L_in = L_fw(f) * G(f) with L_fw from lowcmd_loopgain_v112_v278_v280.py (identical in V112 / rev 3 / V280);
OUTER loop L_out = K_op(f) * G_cr(f) * (1/jw) * (v^2/(L*SR)) * (pi/180) * K_map, with openpilot's torque controller as the
compensator (kp 0.6, ki 0.15, LAF 2.196 clip, friction 0.212 -> slope 0.707 per m/s^2 in the |e| < 0.3 linear band), G_cr = rate per
cmd count MEASURED on rev 3 (so K_map = 0.5 for V112, 1 for rev 3, 1.8 for V280 at idx 24-58).

Run:  python analysis-2020accord/studies/v280/plant_id_v278r3_tap.py
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402

CACHE = os.path.join(os.path.dirname(os.path.dirname(HERE)), "_scratch", "cache", "v280")
ROUTES = ("r31", "r32", "r33")          # r31 = V278 rev 3 ; r32, r33 = V280 rev 2 (tap-verified by the orchestrator, 2026-09-02)
FS = 100.0
NPERSEG = 256
FREQS_REPORT = (2.0, 4.0, 6.0, 8.0)
MIN_SEG_S = 4.0
# openpilot torque controller (kit record: accord-starpilot-torque-controller..., accord-honda-kp-ki-scale-never-acted...)
KP_OP, KI_OP, LAF, FRICTION, FRIC_THR = 0.6, 0.15, 2.196, 0.212, 0.3
CAN_PER_UNIT = 4096.0
WHEELBASE, STEER_RATIO = 2.83, 16.3            # BELIEF: comma's Accord values (steerRatio ~16.3); understeer gradient neglected
MEASURED_BUILD = "V280r2"                    # the build the highway G_cr was measured on (r32/r33); K_map is derived per stratum from the median idx
YAW_FN, YAW_Z = 1.2, 0.7                     # BELIEF: generic bicycle-model yaw response at ~24 m/s, a sensitivity only
YAW_WN = 2 * np.pi * YAW_FN


def load(tag):
    D = dict(np.load(os.path.join(CACHE, tag + ".npz")))
    t0 = D["t18"][0]
    T = D["t18"] - t0
    tg = np.arange(0.0, T[-1], 1 / FS)
    g = dict(tg=tg)
    g["wire"] = np.interp(tg, T, D["rate"])
    g["tq"] = np.interp(tg, T, D["tq"] * 1.024)
    g["ang"] = np.interp(tg, D["t14"] - t0, D["ang"])
    g["sca"] = np.interp(tg, T, D["sca"]) > 0.5
    g["req"] = np.interp(tg, D["te4"] - t0, D["req"]) > 0.5
    g["cmd"] = np.interp(tg, D["te4"] - t0, D["cmd"])
    g["vego"] = np.interp(tg, D["tcs"] - t0, D["vego"])
    fld = ((D["b0"].astype(int) & 3) << 8) | D["b1"].astype(int)
    Tm = np.where(fld >= 512, -1.0, 1.0) * (fld & 511) * 8
    g["T"] = np.interp(tg, D["t1ab"] - t0, Tm)
    # gaps in the 0x18F stream (torn segments): mark as invalid
    dt = np.diff(T)
    gaps = np.where(dt > 0.05)[0]
    bad = np.zeros_like(tg, bool)
    for i in gaps:
        bad |= (tg >= T[i]) & (tg <= T[i + 1])
    g["eng"] = g["sca"] & g["req"] & ~bad
    g["rate_x"] = -g["wire"] / 8.0                     # deg/s, the firmware's operand sign
    return g


def runs(mask, min_len):
    edges = np.diff(np.r_[0, mask.astype(int), 0])
    s, e = np.where(edges == 1)[0], np.where(edges == -1)[0]
    return [(a, b) for a, b in zip(s, e) if b - a >= min_len]


class Pool:
    """pooled cross-spectra over many stretches, weighted by the number of Welch windows."""

    def __init__(self):
        self.f = None
        self.S = {}
        self.n = 0

    def add(self, sigs):
        n = len(next(iter(sigs.values())))
        nw = max(1, (n - NPERSEG // 2) // (NPERSEG // 2))
        keys = list(sigs)
        for i, a in enumerate(keys):
            for b in keys[i:]:
                f, P = signal.csd(sigs[a], sigs[b], fs=FS, nperseg=NPERSEG, detrend="constant")
                self.f = f
                self.S[(a, b)] = self.S.get((a, b), 0) + nw * P
        self.n += nw

    def s(self, a, b):
        if (a, b) in self.S:
            return self.S[(a, b)] / self.n
        return np.conj(self.S[(b, a)]) / self.n

    def coh(self, a, b):
        return np.abs(self.s(a, b)) ** 2 / (np.real(self.s(a, a)) * np.real(self.s(b, b)))

    def tf(self, u, y, ref=None):
        """H = S_ref,y / S_ref,u  (ref = u gives the direct H1 estimate)."""
        ref = u if ref is None else ref
        return self.s(ref, y) / self.s(ref, u)


def at(f, X, f0):
    return np.interp(f0, f, X)


def strata_masks(g):
    v, a, tq = g["vego"], np.abs(g["ang"]), np.abs(g["tq"])
    out = {}
    for sn, sm in (("v<=10", v <= 10), ("10-20", (v > 10) & (v < 20)), ("v>=20", v >= 20)):
        for an, am in (("|ang|<8", a < 8), ("|ang|>=30", a >= 30)):
            out["%s %s" % (sn, an)] = g["eng"] & sm & am
    out["v>=20 |ang|<8 |tq|<500"] = g["eng"] & (v >= 20) & (a < 8) & (tq < 500)
    return out


def margins(fb_, mag, ph):
    """PM at the HIGHEST in-band unity crossing, GM at the first -180 crossing (both in 1-15 Hz)."""
    pm = gm = None
    for i in range(len(fb_) - 2, -1, -1):
        if (mag[i] - 1) * (mag[i + 1] - 1) < 0:
            pm = (fb_[i], 180 + ph[i]); break
    for i in range(len(fb_) - 1):
        if (ph[i] + 180) * (ph[i + 1] + 180) < 0:
            gm = (fb_[i], 1 / mag[i]); break
    return (("PM %.0f deg @ %.1f Hz" % (pm[1], pm[0])) if pm else "PM: no unity crossing in band",
            ("GM %.2fx @ %.1f Hz" % (gm[1], gm[0])) if gm else "GM: no -180 in band")


def main():
    G = {r: load(r) for r in ROUTES}
    pools = {}
    secs = {}
    for r, g in G.items():
        for name, m in strata_masks(g).items():
            key = (r, name)
            pools.setdefault(name, Pool())
            pools.setdefault(key, Pool())
            tot = 0
            for s, e in runs(m, int(MIN_SEG_S * FS)):
                sigs = {"T": g["T"][s:e], "r": g["rate_x"][s:e], "c": g["cmd"][s:e], "q": g["tq"][s:e]}
                pools[name].add(sigs)
                pools[key].add(sigs)
                tot += e - s
            secs[key] = tot / FS
            secs[name] = secs.get(name, 0) + tot / FS

    print("=" * 130)
    print("STRATA: engaged seconds in stretches >= %.0f s   (r31 / r32 / r33 / pooled)" % MIN_SEG_S)
    print("=" * 130)
    names = list(strata_masks(G["r31"]).keys())
    for name in names:
        print("  %-26s %7.1f %7.1f %7.1f | %8.1f s  (%d Welch windows pooled)" % (
            name, secs[("r31", name)], secs[("r32", name)], secs[("r33", name)], secs[name], pools[name].n))

    # ---- plant estimates per stratum (pooled over the three routes) ------------------------------------
    print("\n" + "=" * 130)
    print("PLANT G = rate_x / T  [deg/s per T count] at 2 / 4 / 6 / 8 Hz, pooled.  direct = S_Tr/S_TT ; IVc = S_cr/S_cT (cmd ref) ; IVq = S_qr/S_qT (tq ref)")
    print("  coh = coherence^2: Tr (direct), cT and cr (cmd instrument), qT and qr (tq instrument).  |G| x1e-3 ; phase deg (sign chosen so that the")
    print("  direct estimate's 1-2 Hz phase is nearest 0; the same sign applied to all three).  n = windows.")
    print("=" * 130)
    results = {}
    for name in names:
        P = pools[name]
        if P.n < 8:
            print("  %-26s  too little data (%d windows)" % (name, P.n))
            continue
        f = P.f
        Gd = P.tf("T", "r")
        Gc = P.tf("T", "r", ref="c")
        Gq = P.tf("T", "r", ref="q")
        lo = (f >= 1.0) & (f <= 2.0)
        sgn = 1.0 if abs(np.angle(np.mean(Gd[lo]))) <= np.pi / 2 else -1.0
        Gd, Gc, Gq = sgn * Gd, sgn * Gc, sgn * Gq
        results[name] = dict(f=f, Gd=Gd, Gc=Gc, Gq=Gq, sgn=sgn, n=P.n,
                             cTr=P.coh("T", "r"), ccT=P.coh("c", "T"), ccr=P.coh("c", "r"), cqT=P.coh("q", "T"), cqr=P.coh("q", "r"),
                             Gcr=P.tf("c", "r"), ccr_direct=P.coh("c", "r"))
        print("\n  %s   (n=%d, sign %+d)" % (name, P.n, sgn))
        print("    %4s | %8s %7s %5s | %8s %7s %5s %5s | %8s %7s %5s %5s" % ("f", "|Gdir|", "ph", "cohTr", "|G_IVc|", "ph", "cohcT", "cohcr", "|G_IVq|", "ph", "cohqT", "cohqr"))
        for f0 in FREQS_REPORT:
            print("    %4.0f | %8.3f %7.1f %5.2f | %8.3f %7.1f %5.2f %5.2f | %8.3f %7.1f %5.2f %5.2f" % (
                f0, 1e3 * abs(at(f, Gd, f0)), np.degrees(np.angle(at(f, Gd, f0))), at(f, results[name]["cTr"], f0),
                1e3 * abs(at(f, Gc, f0)), np.degrees(np.angle(at(f, Gc, f0))), at(f, results[name]["ccT"], f0), at(f, results[name]["ccr"], f0),
                1e3 * abs(at(f, Gq, f0)), np.degrees(np.angle(at(f, Gq, f0))), at(f, results[name]["cqT"], f0), at(f, results[name]["cqr"], f0)))

    # per-route check on the key stratum
    key = "v>=20 |ang|<8"
    print("\n  PER-ROUTE, %s, direct estimate |G| x1e-3 / phase / cohTr at 2,4,6,8 Hz:" % key)
    for r in ROUTES:
        P = pools[(r, key)]
        if P.n < 8:
            print("    %s: %d windows" % (r, P.n)); continue
        Gd = P.tf("T", "r"); f = P.f
        lo = (f >= 1.0) & (f <= 2.0)
        sgn = 1.0 if abs(np.angle(np.mean(Gd[lo]))) <= np.pi / 2 else -1.0
        print("    %s (n=%d): %s" % (r, P.n, "  ".join("%.0fHz %.3f/%.0f/%.2f" % (f0, 1e3 * abs(at(f, sgn * Gd, f0)), np.degrees(np.angle(at(f, sgn * Gd, f0))), at(f, P.coh("T", "r"), f0)) for f0 in FREQS_REPORT)))

    # ---- INNER-loop margins ----------------------------------------------------------------------------
    C = LG.read_build(LG.FW + LG.IMAGES["V278r3"])
    print("\n" + "=" * 130)
    print("INNER LOOP  L_in(f) = L_fw(f) * G(f)   [L_fw = firmware T per deg/s incl. Kp(idx), D, post-mult, lag, GAIN, fb filter, z^-1 -- IDENTICAL in V112 / rev 3 / V280]")
    print("  G = the direct estimate where cohTr >= 0.5, else the cmd-instrumented one (flagged 'IV').  idx 24 (Kp 341) unless noted.")
    print("  Reported: |L_in| and phase at 2/4/6/8 Hz, the in-band (1-15 Hz) phase minimum, and GM/PM where the crossings exist in band.")
    print("=" * 130)
    idx_op = 24
    for name, R in results.items():
        f = R["f"]
        band = (f >= 1.0) & (f <= 15.0)
        use_iv = at(f, R["cTr"], 4.0) < 0.5
        Gs = R["Gc"] if use_iv else R["Gd"]
        Lfw = np.array([LG.C_ctrl(C, idx_op, x, True) * LG.H_fb(C, x) * LG.CPD * np.exp(-1j * 2 * np.pi * x / LG.FS) for x in f])
        L = Lfw * Gs
        mag, ph = np.abs(L), np.degrees(np.unwrap(np.angle(L[band])))
        fb_ = f[band]
        pm, gm = margins(fb_, mag[band], ph)
        print("  %-26s %s  |L|@2/4/6/8: %s   phase: %s   min phase in band %.0f deg @ %.1f Hz   %s   %s" % (
            name, "IV " if use_iv else "dir", " ".join("%5.2f" % at(f, mag, x) for x in FREQS_REPORT),
            " ".join("%5.0f" % at(fb_, ph, x) for x in FREQS_REPORT), ph.min(), fb_[np.argmin(ph)], pm, gm))


    # ---- OUTER-loop margins ----------------------------------------------------------------------------
    print("\n" + "=" * 130)
    print("OUTER LOOP  L_out(f) = K_op(f) * G_cr(f) * 1/(jw) * v^2/(L*SR) * pi/180 * K_map     [BELIEF: compensator structure from the kit's StarPilot record]")
    print("  K_op = 4096 * [ (kp + ki/jw)/LAF + friction/0.3 ]  CAN counts per m/s^2  (kp %.2f ki %.2f LAF %.3f friction %.3f -> slope %.3f)" % (KP_OP, KI_OP, LAF, FRICTION, FRICTION / FRIC_THR))
    print("  G_cr = rate_x per cmd count MEASURED (direct S_cr/S_cc) on the stratum's routes (r31 = rev 3, r32/r33 = V280); K_map = each build's map slope at the stratum's median idx / V280's.  v = median speed.")
    print("  L = %.2f m, SR = %.1f (comma Accord), understeer neglected.  Phase includes the 1/s integrator (angle from rate) and one 10 ms openpilot frame." % (WHEELBASE, STEER_RATIO))
    print("=" * 130)
    for name, R in results.items():
        f = R["f"]
        P = pools[name]
        Gcr = P.tf("c", "r")
        # sign: cmd -> rate_x should be positive at low f (openpilot pushes the wheel the way it commands)
        lo = (f >= 1.0) & (f <= 2.0)
        sg = 1.0 if abs(np.angle(np.mean(Gcr[lo]))) <= np.pi / 2 else -1.0
        Gcr = sg * Gcr
        coh_cr = P.coh("c", "r")
        # median speed of the stratum
        vs = np.concatenate([G[r]["vego"][strata_masks(G[r])[name]] for r in ROUTES])
        v = float(np.median(vs)) if len(vs) else np.nan
        # per-stratum map ratio: small-signal slope of each build's map at the stratum's MEDIAN demand index, relative to the measured build
        idxs = np.concatenate([LG.idx_of_cmd(np.round(G[r]["cmd"][strata_masks(G[r])[name]])) for r in ROUTES])
        i50 = min(float(np.median(idxs)) if len(idxs) else 0.0, 239.0)
        CB = {k: LG.read_build(LG.FW + LG.IMAGES[k]) for k in ("V112", "V278r3", "V280r2")}
        sl = {k: LG.slope(CB[k]["map_X"], CB[k]["map_Y"], i50) for k in CB}
        K_MAP = {k: sl[k] / sl[MEASURED_BUILD] for k in CB}
        w = 2 * np.pi * f
        with np.errstate(divide="ignore", invalid="ignore"):
            Kop = CAN_PER_UNIT * ((KP_OP + KI_OP / (1j * w)) / LAF + FRICTION / FRIC_THR)
            plant = Gcr / (1j * w) * (v ** 2 / (WHEELBASE * STEER_RATIO)) * (np.pi / 180) * np.exp(-1j * w * 0.01)
        band = (f >= 1.0) & (f <= 15.0)
        print("  %-26s v=%4.1f m/s  coh_cr@2/4 %.2f/%.2f  |G_cr|@2/4 %.2e/%.2e deg/s per count   idx p50 %.0f -> K_map V112 %.2f rev3 %.2f V280 %.2f" % (
            name, v, at(f, coh_cr, 2), at(f, coh_cr, 4), abs(at(f, Gcr, 2)), abs(at(f, Gcr, 4)), i50, K_MAP["V112"], K_MAP["V278r3"], K_MAP["V280r2"]))
        yaw2 = YAW_WN ** 2 / ((1j * w) ** 2 + 2 * YAW_Z * YAW_WN * 1j * w + YAW_WN ** 2)
        for yaw_lab, yaw in (("kinematic", np.ones_like(w, complex)), ("+yaw wn %.1f Hz z %.2f" % (YAW_FN, YAW_Z), yaw2)):
            for b, km in K_MAP.items():
                Lo = Kop * plant * yaw * km
                mag = np.abs(Lo[band]); ph = np.degrees(np.unwrap(np.angle(Lo[band]))); fb_ = f[band]
                pm, gm = margins(fb_, mag, ph)
                print("      %-24s %-7s |L|@1/2/3/4 %5.2f %5.2f %5.2f %5.2f  phase@1/2/3/4 %5.0f %5.0f %5.0f %5.0f   %s   %s" % (
                    yaw_lab, b, at(fb_, mag, 1), at(fb_, mag, 2), at(fb_, mag, 3), at(fb_, mag, 4),
                    at(fb_, ph, 1), at(fb_, ph, 2), at(fb_, ph, 3), at(fb_, ph, 4), pm, gm))
    print("\n  NOTE: the outer-loop rows are only as good as (a) coh_cr, (b) the compensator structure taken from the kit's record, (c) the kinematic")
    print("        angle->lateral-accel model.  Read them as RATIOS between builds (exact: K_map) and as order-of-magnitude absolute margins.")

    # ---- direct spectral check: does the highway low-angle rate spectrum on V280 rev 2 carry a line that V112 does not? ----
    print("\n" + "=" * 130)
    print("HIGHWAY RATE SPECTRUM CHECK: PSD of the 0x18F rate, engaged, v >= 20 m/s, |ang| < 8 deg, stretches >= 4 s.  V280 rev 2 (r32, r33) vs V112 (r22, r23) vs stock (r97); rev 3 (r31) has no >= 20 m/s data")
    print("  peak frequency in 1-6 Hz, and the band-power ratio 1.5-3 Hz / (0.5-1 + 4-6 Hz shoulders)")
    print("=" * 130)
    for r, build in (("r32", "V280r2"), ("r33", "V280r2"), ("r22", "V112"), ("r23", "V112"), ("r97", "stock")):
        try:
            g = load(r)
        except Exception as e:
            print("  %s: %s" % (r, e)); continue
        m = g["eng"] & (g["vego"] >= 20) & (np.abs(g["ang"]) < 8)
        Pw = None; nw = 0
        for s_, e_ in runs(m, int(MIN_SEG_S * FS)):
            f, pp = signal.welch(g["rate_x"][s_:e_], fs=FS, nperseg=NPERSEG, detrend="constant")
            k = max(1, (e_ - s_ - NPERSEG // 2) // (NPERSEG // 2))
            Pw = pp * k if Pw is None else Pw + pp * k; nw += k
        if Pw is None:
            print("  %s %-7s: no data" % (r, build)); continue
        Pw /= nw
        b = (f >= 1.0) & (f <= 6.0)
        fpk = f[b][np.argmax(Pw[b])]
        core = np.trapezoid(Pw[(f >= 1.5) & (f <= 3.0)], f[(f >= 1.5) & (f <= 3.0)])
        sh = np.trapezoid(Pw[(f >= 0.5) & (f <= 1.0)], f[(f >= 0.5) & (f <= 1.0)]) + np.trapezoid(Pw[(f >= 4.0) & (f <= 6.0)], f[(f >= 4.0) & (f <= 6.0)])
        print("  %s %-7s: %4d windows (%5.0f s)  peak %.2f Hz  P(peak) %.3g  core/shoulders %.2f   PSD @1/2/3/4/6 Hz: %s" % (
            r, build, nw, nw * NPERSEG / 2 / FS, fpk, Pw[b].max(), core / sh, " ".join("%.2g" % at(f, Pw, x) for x in (1, 2, 3, 4, 6))))


if __name__ == "__main__":
    main()
