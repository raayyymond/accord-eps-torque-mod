# -*- coding: utf-8 -*-
"""studies/osc-highangle/servo_at_reference.py -- is the 7 Hz high-angle stutter on V278 rev 3 the rate servo
CHATTERING AT ITS REFERENCE (wheel at the map ceiling, E small and sign-flipping, lane alternately braking and
pushing) or a level-driven ratchet firing while E is large and the lane pushes hard?  Subagent r3servo, 2026-09-02.

Method: re-run the frame-by-frame chain of analysis-2020accord/studies/v280/v280_map_profiles.py (mirrors the
FUN_00028ea6 decompile) on the MEASURED 0x18F rate of the F7 episodes found by highangle_stutter.py, with rev 3's
cells, and read per tick sp, fb, E, P, fb-clamp state and T_sim against the CAN-427 tap T_meas.  Then the same
frames through counterfactual maps/clamps.  Open loop: the rate is what rev 3's closed loop produced; a different
map would have produced a different rate.  Section 3 does the same on stock (r97) and V112 (r22) high-angle frames.

Delivery cells per build (read from the images, EVIDENCE):  stock gain 0xC646C=891 / cap 0xC61B4=512  ((15360*891)>>15 = 417);
V112 and rev 3: 0xC6CD0=5346 / 0xC61B4=3072.  Map Y (slot 7 @0xE5042): rev 3 = 2x stock, V276 = 6x stock.

Run:  python servo_at_reference.py   (uses analysis-2020accord/_scratch/cache/v280/<tag>.npz; writes <scratch>/servo_*.txt)
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
import v280_map_profiles as V  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K = 100.0, 1000.0
SCRATCH = os.environ.get("R3SERVO_SCRATCH", os.path.join(
    r"C:\Users\dudei\AppData\Local\Temp\claude\C--Users-dudei-Desktop-Projects-accord-eps-torque-mod",
    "1129e2c5-0c63-4cae-b75a-e528b96d16ef", "scratchpad", "r3servo"))
R3STUTTER_JSON = os.path.join(os.path.dirname(SCRATCH), "r3stutter", "r31.json")
BAND7 = (6.0, 8.5)

# episodes of highangle_stutter.py on r31 (HIGHANGLE-r31-episodes.txt), fallback if the JSON is absent: (t0, dur, fdom)
EPIS_FALLBACK = [(144.1, 2.0, 2.93), (158.1, 1.5, 6.54), (217.1, 2.4, 7.44), (221.5, 1.7, 7.47), (266.2, 2.8, 7.03),
                 (303.7, 1.4, 7.14), (312.7, 2.3, 7.05), (381.9, 3.2, 7.03), (411.3, 3.0, 7.42), (434.0, 1.3, 2.27),
                 (474.0, 1.1, 2.83), (537.0, 2.1, 7.58), (546.6, 2.0, 7.46)]

MAPS = {
    "rev3 x2 / clamp 15360": (V.map_knots(V.profile(2, 240, 2)), 15360),
    "(a) V276 x6 / clamp 46080": (V.map_knots(V.profile(6, 240, 6)), 46080),
    "(b) x6 / clamp KEPT 15360": (V.map_knots(V.profile(6, 240, 6)), 15360),
    "(c) stock x1 / clamp 7680": (V.map_knots(V.profile(1, 240, 1)), 7680),
    "(d) V280 2@96->6 / 46080": (V.map_knots(V.profile(2, 96, 6)), 46080),
}
DELIVERY = {"r97": (891, 512), "r22": (5346, 3072), "r31": (5346, 3072)}


def load_episodes():
    if os.path.exists(R3STUTTER_JSON):
        J = json.load(open(R3STUTTER_JSON))
        return [(e["t0"], e["dur"], e["fdom"]) for e in J["episodes"]], "r3stutter/r31.json"
    return EPIS_FALLBACK, "fallback list"


def band_amp(x, lo=BAND7[0], hi=BAND7[1]):
    if len(x) < 40:
        return np.nan
    sos = signal.butter(4, [lo, hi], btype="bandpass", fs=FS, output="sos")
    return float(np.sqrt(2) * signal.sosfiltfilt(sos, x - x.mean()).std())


def flips_per_s(x, fs):
    s = np.sign(x); s = s[s != 0]
    return float((np.diff(s) != 0).sum() / (len(x) / fs)) if len(x) else np.nan


def phase_at(x, y, f0):
    """phase of y relative to x at f0 (deg) and coherence, on the 100 Hz grid."""
    n = min(256, len(x))
    f, C = signal.coherence(x, y, fs=FS, nperseg=n)
    _, P = signal.csd(x, y, fs=FS, nperseg=n)
    j = int(np.argmin(np.abs(f - f0)))
    return float(np.degrees(np.angle(P[j]))), float(C[j])


def simulate(route, mapY, clamp, gain, cap):
    V.GAIN, V.OUT_CAP = gain, cap
    R = route.simulate(mapY, fb_clamp=clamp)
    R["clamped"] = np.abs(route.fb_un) >= clamp
    R["ref_deg"] = 32 * np.abs(R["sp"]) / V.FB_DC / V.CPD          # the reference rate the map asks for, per tick
    return R


def tick_metrics(route, R, m1k, m100, fdom=7.0):
    """m1k / m100: masks on the 1 kHz / 100 Hz grids."""
    sg = route.sgn1k[m1k]
    E = R["E"][m1k]; En = E * sg                          # E in the setpoint's direction: <0 = feedback past the reference = BRAKING
    fb = R["fb"][m1k]
    P = R["P_raw"][m1k]
    out = dict(n=int(m1k.sum()))
    out["absE_p50"] = float(np.median(np.abs(E))); out["absE_p90"] = float(np.percentile(np.abs(E), 90))
    out["E_brake"] = float(np.mean(En < 0))
    out["E_flips"] = flips_per_s(E, FS1K)
    ok = fb != 0
    out["dampE"] = float(np.mean(np.sign(E[ok]) != np.sign(fb[ok]))) if ok.any() else np.nan
    out["clamped"] = float(np.mean(R["clamped"][m1k]))
    out["P_rail"] = float(np.mean(np.abs(P) >= V.P_CLAMP))
    w = np.abs(route.wire[m100]) / V.CPD
    ref = R["ref_deg"][route.i100][m100]
    okr = ref > 0
    out["rate_p50"] = float(np.median(w)); out["ref_p50"] = float(np.median(ref[okr])) if okr.any() else np.nan
    out["rate_over_ref"] = float(np.median(w[okr] / ref[okr])) if okr.any() else np.nan
    out["sp32_p50"] = float(np.median(32 * np.abs(R["sp"][m1k])))
    # 7 Hz content on the 100 Hz grid (contiguous episode only -- meaningful when m100 is one run)
    i = route.i100[m100]
    E100, fb100, P100 = R["E"][i], R["fb"][i], np.clip(R["P_raw"][i], -V.P_CLAMP, V.P_CLAMP)
    Ts = R["T"][i]
    out["amp7_fb"] = band_amp(fb100); out["amp7_E"] = band_amp(E100); out["amp7_P"] = band_amp(P100)
    out["amp7_Tsim"] = band_amp(Ts); out["absT_sim_p50"] = float(np.median(np.abs(Ts)))
    out["Tsim_flips"] = flips_per_s(Ts, FS)
    out["Tsim_brake"] = float(np.mean(np.sign(Ts) != np.sign(-route.sgn[m100])))  # T sign on the wire = +sign(cmd) = -sgn? see below
    if hasattr(route, "T_meas"):
        Tm = route.T_meas[m100]
        out["amp7_Tmeas"] = band_amp(Tm); out["absT_meas_p50"] = float(np.median(np.abs(Tm)))
        out["Tmeas_flips"] = flips_per_s(Tm, FS)
        if len(Tm) > 40 and np.std(Ts) > 0:
            out["corr_T"] = float(np.corrcoef(Ts, Tm)[0, 1]); out["slope_T"] = float(np.sum(Ts * Tm) / np.sum(Ts ** 2))
            out["ph_Tsim_re_Tmeas"], out["coh_TT"] = phase_at(Tm, Ts, fdom)
        wr = route.wire[m100]
        out["ph_Tmeas_re_rate"], _ = phase_at(wr, Tm, fdom)
        out["ph_Tsim_re_rate"], _ = phase_at(wr, Ts, fdom)
        out["ph_E_re_rate"], _ = phase_at(wr, E100, fdom)
    return out


def sec1_2(r31, epis, src):
    lines = []
    pr = lambda s="": (print(s), lines.append(s))  # noqa: E731
    pr("=" * 120)
    pr("SECTION 1 -- r31 F7 episodes through the chain with rev 3's cells (map x2, fb clamp 15360, gain 5346, cap 3072); episodes from %s" % src)
    pr("  E in setpoint direction; 'brake' = P(E<0) = feedback past the reference; rate/ref = |0x18F|/8 over the map's reference at that tick")
    pr("=" * 120)
    R = simulate(r31, *MAPS["rev3 x2 / clamp 15360"], *DELIVERY["r31"])
    hdr = "%2s %6s %4s %5s | %6s %6s %5s %6s %5s %5s %5s | %5s %5s %5s | %6s %6s %6s %6s %6s | %5s %5s %5s %5s | %5s %5s %5s %5s %5s"
    pr(hdr % ("#", "t0", "dur", "fdom", "|E|50", "|E|90", "brake", "Eflp/s", "dampE", "clamp", "Prail", "rate", "ref", "r/ref",
              "a7fb", "a7E", "a7P", "a7Tsim", "a7Tms", "Ts50", "Tm50", "Tsflp", "Tmflp", "corr", "slope", "phTmr", "phTsr", "phEr"))
    f7 = []
    for k, (t0, dur, fdom) in enumerate(epis):
        s, e = int(round(t0 * FS)), int(round((t0 + dur) * FS))
        m100 = np.zeros_like(r31.eng); m100[s:e] = True; m100 &= r31.eng
        m1k = np.zeros_like(r31.eng1k); m1k[int(t0 * FS1K):int((t0 + dur) * FS1K)] = True; m1k &= r31.eng1k
        M = tick_metrics(r31, R, m1k, m100, fdom)
        tag = "F7" if fdom > 5 else "F2"
        pr("%2d %6.1f %4.1f %5.2f | %6.0f %6.0f %5.2f %6.1f %5.2f %5.2f %5.2f | %5.1f %5.1f %5.2f | %6.0f %6.0f %6.0f %6.0f %6.0f | %5.0f %5.0f %5.1f %5.1f | %5.2f %5.2f %5.0f %5.0f %5.0f  %s" % (
            k, t0, dur, fdom, M["absE_p50"], M["absE_p90"], M["E_brake"], M["E_flips"], M["dampE"], M["clamped"], M["P_rail"],
            M["rate_p50"], M["ref_p50"], M["rate_over_ref"], M["amp7_fb"], M["amp7_E"], M["amp7_P"], M["amp7_Tsim"], M["amp7_Tmeas"],
            M["absT_sim_p50"], M["absT_meas_p50"], M["Tsim_flips"], M["Tmeas_flips"], M.get("corr_T", np.nan), M.get("slope_T", np.nan),
            M["ph_Tmeas_re_rate"], M["ph_Tsim_re_rate"], M["ph_E_re_rate"], tag))
        if tag == "F7":
            f7.append((k, t0, dur, fdom, m1k, m100))
    # pooled F7
    m1k = np.zeros_like(r31.eng1k); m100 = np.zeros_like(r31.eng)
    for _, _, _, _, a, b in f7:
        m1k |= a; m100 |= b
    pr("\n  a7x = 6-8.5 Hz band amplitude (sqrt2*std) of fb, E, P (clamped), T_sim, T_meas; Ts50/Tm50 = |T| median; flp = sign flips/s;")
    pr("  phXr = phase of X relative to the RAW 0x18F rate at fdom (deg; the stutter note measured T_meas at +70..+88).")
    pr("\n" + "=" * 120)
    pr("SECTION 2 -- COUNTERFACTUALS on the SAME measured rate, pooled F7 ticks (n1k=%d, %.1f s), open loop" % (m1k.sum(), m100.sum() / FS))
    pr("=" * 120)
    pr("%-28s | %6s %6s %5s %6s %5s %5s %5s | %5s %5s | %6s %6s %6s %5s %5s | %s" % (
        "map / clamp", "|E|50", "|E|90", "brake", "Eflp/s", "dampE", "clamp", "Prail", "ref", "r/ref", "a7E", "a7P", "a7Tsim", "Ts50", "Tsflp", "T ripple/level"))
    for name, (Y, clamp) in MAPS.items():
        Rc = simulate(r31, Y, clamp, *DELIVERY["r31"])
        M = tick_metrics(r31, Rc, m1k, m100)
        # 7 Hz amplitude per episode, pooled as the median over episodes (the pooled band-pass would smear episode edges)
        a7E, a7P, a7T, tfl = [], [], [], []
        for _, _, _, fd, a, b in f7:
            Me = tick_metrics(r31, Rc, a, b, fd)
            a7E.append(Me["amp7_E"]); a7P.append(Me["amp7_P"]); a7T.append(Me["amp7_Tsim"]); tfl.append(Me["Tsim_flips"])
        pr("%-28s | %6.0f %6.0f %5.2f %6.1f %5.2f %5.2f %5.2f | %5.1f %5.2f | %6.0f %6.0f %6.0f %5.0f %5.1f | %.2f" % (
            name, M["absE_p50"], M["absE_p90"], M["E_brake"], M["E_flips"], M["dampE"], M["clamped"], M["P_rail"], M["ref_p50"], M["rate_over_ref"],
            np.median(a7E), np.median(a7P), np.median(a7T), M["absT_sim_p50"], np.median(tfl), np.median(a7T) / max(M["absT_sim_p50"], 1)))
    pr("  T ripple/level = 7 Hz T_sim amplitude over |T_sim| median: > 1 means the lane's output crosses zero at 7 Hz (reversing), << 1 a steady push with ripple.")
    return lines, R


def sec3(routes):
    lines = []
    pr = lambda s="": (print(s), lines.append(s))  # noqa: E731
    pr("\n" + "=" * 120)
    pr("SECTION 3 -- high-angle engaged frames (|0x14A| >= 30 deg) by demand, each route through ITS OWN build's cells")
    pr("=" * 120)
    pr("%-4s %-8s %-14s %5s | %6s %6s %5s %6s %5s %5s %5s | %5s %5s %5s | %6s %6s %6s %5s | %5s %6s" % (
        "rte", "build", "frames", "secs", "|E|50", "|E|90", "brake", "Eflp/s", "dampE", "clamp", "Prail", "rate", "ref", "r/ref", "a7fb", "a7E", "a7Tsim", "Ts50", "sat", "v50"))
    for tag, r in routes.items():
        Y, clamp = {"r97": MAPS["(c) stock x1 / clamp 7680"], "r22": MAPS["(c) stock x1 / clamp 7680"], "r31": MAPS["rev3 x2 / clamp 15360"]}[tag]
        R = simulate(r, Y, clamp, *DELIVERY[tag])
        hi = r.eng & (np.abs(r.ang) >= 30)
        for fname, fm in (("idx>=200", hi & (r.idx >= 200)), ("idx 128-200", hi & (r.idx >= 128) & (r.idx < 200)), ("idx<128", hi & (r.idx < 128)), ("all", hi)):
            m100 = fm
            m1k = r.up(m100.astype(float)) > 0.5
            if m100.sum() < 50:
                pr("%-4s %-8s %-14s %5.1f  (too few)" % (tag, V.ROUTE_BUILD[tag][:8], fname, m100.sum() / FS)); continue
            M = tick_metrics(r, R, m1k, m100)
            # band amplitude over contiguous runs only (>= 0.64 s)
            runs = V.runs(m100, 64)
            i = r.i100[runs]
            a7fb = band_amp(R["fb"][i]) if runs.sum() > 64 else np.nan
            a7E = band_amp(R["E"][i]) if runs.sum() > 64 else np.nan
            a7T = band_amp(R["T"][i]) if runs.sum() > 64 else np.nan
            sat = float(np.mean(np.abs(R["T"][r.i100][m100]) >= DELIVERY[tag][1] * 0.8))
            pr("%-4s %-8s %-14s %5.1f | %6.0f %6.0f %5.2f %6.1f %5.2f %5.2f %5.2f | %5.1f %5.1f %5.2f | %6.0f %6.0f %6.0f %5.0f | %5.2f %6.1f" % (
                tag, V.ROUTE_BUILD[tag][:8], fname, m100.sum() / FS, M["absE_p50"], M["absE_p90"], M["E_brake"], M["E_flips"], M["dampE"], M["clamped"], M["P_rail"],
                M["rate_p50"], M["ref_p50"], M["rate_over_ref"], a7fb, a7E, a7T, M["absT_sim_p50"], sat, float(np.median(r.vego[m100]))))
    pr("  a7* over contiguous >= 0.64 s runs of the mask (band-pass smears across gaps); sat = P(|T_sim| >= 0.8 cap); r97 T through gain 891 / cap 512.")
    return lines


def main():
    os.makedirs(SCRATCH, exist_ok=True)
    epis, src = load_episodes()
    routes = {}
    for tag in ("r31", "r97", "r22"):
        print("loading %s ..." % tag, flush=True)
        r = V.Route(tag)
        D = dict(np.load(os.path.join(V.CACHE, tag + ".npz")))
        t0 = D["t18"][0]
        r.ang = np.interp(r.tg, D["t14"] - t0, D["ang"])
        routes[tag] = r
    L1, _ = sec1_2(routes["r31"], epis, src)
    L3 = sec3(routes)
    with open(os.path.join(SCRATCH, "servo_at_reference.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L1 + L3) + "\n")
    print("wrote", os.path.join(SCRATCH, "servo_at_reference.txt"))


if __name__ == "__main__":
    main()
