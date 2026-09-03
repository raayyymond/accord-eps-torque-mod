# -*- coding: utf-8 -*-
"""studies/grind/creep20_loop_id.py -- is the 20 Hz creep-regime line (the operator's "very very attenuated grind #1 at
3-6 mph, engaged, hands light" on V280 rev 2) the RATE LOOP'S OWN high-frequency mode, or something the loop merely transmits?
Subagent creep20, 2026-09-03.  Analysis only: builds nothing, sends nothing.

Routes: r31 (V278 rev 3), r32/r33 (V280 rev 2, old tune), r34 (V280 rev 2, new tune); caches analysis-2020accord/_scratch/cache/v280.
Streams: 0x18F (100 Hz: bar = signed driver torque b0-1 raw, rate = b2-3 raw 8 counts/deg/s, SCA b4.3), 0xE4 (100 Hz: cmd b0-1,
STEER_REQUEST b2.7), 0x1AB (50 Hz: the CAN-427 delivered-torque tap, fld = ((b0&3)<<8)|b1, T = +-(fld&0x1ff)<<3), 0x14 (angle), carState.

TIMING (the part the earlier readers did not do): the logged CAN receive times are BATCH-JITTERED -- 0x18F frames arrive in pairs
(dt 0 then 20 ms, 2.4 % of frames), 0x1AB dt spans 10-30 ms (p1/p99).  At 20 Hz a 10 ms error is HALF A CYCLE, so every stream is
first put back on its own nominal frame counter (period fitted per stream, drops detected as steps in the lower envelope of
t - k*P, the envelope itself = the transmit clock + minimum latency).  The residual of that fit is reported; the T_sim-vs-T_meas
phase at the line (Part 4) is the end-to-end check that the timing model is right.

Parts
  1  plant G = rate/T, CREEP stratum (engaged, v 1-3 m/s, |bar| < 400 raw), 50 Hz pools on the tap's native instants, 10-25 Hz
     (the tap is 50 Hz: nothing above 25 Hz is observable on it; bar/rate go to 40 Hz on the 100 Hz streams); direct, cmd-IV and
     bar-IV estimates with coherences; then L_in = L_fw(Kp(idx), Kd 128, lags, fb sum) * G at 20 Hz, GM/PM, and the -1/C identity
     test (T/rate measured vs the firmware's own controller); the bar-vs-rate phase (spring or inertia?).
  2  frequency-vs-state: f_line per 2 s window vs |rate|, v, |angle|, |T|, idx (Spearman, slope), per route.
  3  excitation: 20 Hz in the 0xE4 command (line, period-5 structure = the 20 Hz planner staircase), coherence cmd<->bar/T at the
     line; presence and amplitude vs |T| and idx; engaged idx = 0 vs pushing; manual creep.
  4  the FUN_00028ea6 mirror on the measured rate with the V280 map (ZOH command, 1 kHz): T_sim vs tap at 18-22 Hz (corr, amp,
     phase), P vs D share, then open-loop counterfactuals (Kd 0/64, Kp cap 341, lag pole, fb single-sample, rate<15 Hz only, cmd only).

Chain arithmetic mirrors v280_map_profiles.Route.simulate (FUN_00028ea6 decompile line refs in lowcmd_loopgain_v112_v278_v280.py):
  E = 32*sp - fb (L975) ; P = clamp(E*Kp>>8, +-15360) (L1013-1052) ; D = clamp(dE*Kd>>3, +-10240) (L1053-1092) ;
  sum = clamp(254*(P+D)>>8, +-15360) (L1094-1205) ; lag s' = (992 s + 507 u)>>10, y = (s+s')>>5 (L1224-1227) ;
  T = clamp(-y*5346>>15, +-3072) (L1244-1265).  fb = clamp(s_old + s_new, +-46080), s_new = (923 s + 1560 x)>>10, x = -rate raw.
Run: python creep20_loop_id.py     (writes _scratch/creep20_loop_id.txt beside it)
"""
import os
import sys

import numpy as np
from scipy import signal, stats

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402  (image reader, L_fw pieces)
import v280_map_profiles as V                 # noqa: E402  (chain constants, demand(), feedback_1khz())
import _grind2_lib as G2                      # noqa: E402  (prom_spectrum / locate)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
ROUTES = ("r31", "r32", "r33", "r34")
BUILD = {"r31": "V278r3 (map x2)", "r32": "V280r2 old tune", "r33": "V280r2 old tune", "r34": "V280r2 new tune"}
MAPY = {"r31": None, "r32": None, "r33": None, "r34": None}
FS, FS1K, FST = 100.0, 1000.0, 50.0
VLO, VHI, TQMAX = 1.0, 3.0, 400.0
FREQS = (10.0, 15.0, 18.0, 20.0, 22.0, 25.0)
OP_SECS = {"r34": [(336.0, 342.0), (419.0, 422.5), (437.0, 440.5)]}     # the operator's grind seconds (HIGHANGLE-r34 s8)
LINE_LO, LINE_HI = 15.0, 26.0
OUT = []


def pr(s=""):
    print(s); OUT.append(s)


# ======================================================================================================================
# timing: put each stream back on its nominal frame counter
# ======================================================================================================================
def rolling_low(x, half, q=2.0):
    """rolling q-th percentile over +-half samples, evaluated every `half` samples and interpolated."""
    n = len(x); cen = np.arange(0, n, max(1, half // 2))
    v = np.array([np.percentile(x[max(0, c - half):min(n, c + half + 1)], q) for c in cen])
    return np.interp(np.arange(n), cen, v)


def dejitter(t, P0, half):
    """returns (k, P, t_nom, resid): frame counter k, fitted period P, nominal times k*P + envelope, resid = t - t_nom >= ~0."""
    n = len(t); i = np.arange(n)
    r = t - i * P0
    env = rolling_low(r, half)
    # real drops = steps in the envelope of >= 0.6 P over one window; clock drift is gradual
    step = np.r_[0.0, np.diff(env)]
    drops = np.round(np.cumsum(np.where(np.abs(step) > 0.6 * P0, step, 0.0)) / P0).astype(int)
    k = i + drops
    # refine the period from the envelope end-points (drops removed), then re-envelope on the k axis
    r2 = t - k * P0
    env2 = rolling_low(r2, half)
    P = P0 + (env2[-1] - env2[0]) / max(1, (k[-1] - k[0]))
    r3 = t - k * P
    env3 = rolling_low(r3, half)
    t_nom = k * P + env3
    return k, P, t_nom, t - t_nom


def grid_from(k, x, kmax):
    """uniform-in-k array with gaps linearly filled; mask of real frames."""
    g = np.full(kmax + 1, np.nan); g[k] = x
    have = ~np.isnan(g)
    g[~have] = np.interp(np.flatnonzero(~have), np.flatnonzero(have), g[have])
    return g, have


def load(tag):
    D = dict(np.load(os.path.join(CACHE, tag + ".npz")))
    k18, P18, tn18, res18 = dejitter(D["t18"], 0.01, 100)
    k1ab, P1ab, tn1ab, res1ab = dejitter(D["t1ab"], 0.02, 50)
    ke4, Pe4, tne4, rese4 = dejitter(D["te4"], 0.01, 100)
    g = dict(tag=tag, P18=P18, P1ab=P1ab, Pe4=Pe4,
             res=dict(f18=(np.percentile(res18, 50), np.percentile(res18, 90), np.mean(np.abs(res18) > 0.003)),
                      f1ab=(np.percentile(res1ab, 50), np.percentile(res1ab, 90), np.mean(np.abs(res1ab) > 0.003)),
                      fe4=(np.percentile(rese4, 50), np.percentile(rese4, 90), np.mean(np.abs(rese4) > 0.003))))
    K = int(k18[-1])
    g["t"] = np.interp(np.arange(K + 1), k18, tn18 - k18 * P18) + np.arange(K + 1) * P18   # nominal time of frame k
    g["bar"], have = grid_from(k18, D["tq"] * 1.024, K)
    g["wire"], _ = grid_from(k18, D["rate"].astype(float), K)
    g["sca"], _ = grid_from(k18, D["sca"].astype(float), K)
    g["have18"] = have
    # other streams on the 18F frame axis, by nominal time
    g["cmd"] = np.interp(g["t"], tne4, D["cmd"].astype(float))
    g["req"] = np.interp(g["t"], tne4, D["req"].astype(float)) > 0.5
    g["ang"] = np.interp(g["t"], D["t14"], D["ang"].astype(float))
    g["vego"] = np.interp(g["t"], D["tcs"], D["vego"].astype(float))
    fld = ((D["b0"].astype(int) & 3) << 8) | D["b1"].astype(int)
    Tm = np.where(fld >= 512, -1.0, 1.0) * (fld & 511) * 8
    g["T_t"] = tn1ab; g["T"] = Tm
    g["T100"] = np.interp(g["t"], tn1ab, Tm)            # only for masks / coarse stats; spectra use the native samples
    # gap-marked engaged
    bad = ~have
    g["eng"] = (g["sca"] > 0.5) & g["req"] & ~bad
    g["idx"], g["sgn"] = V.demand(np.round(g["cmd"]), g["bar"])
    g["rate_x"] = -g["wire"] / V.CPD                     # deg/s, the sign the PID sees (x = gp-0x6a56 = -wire)
    return g


def runs(mask, min_len):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= min_len]


def creep_mask(g, vlo=VLO, vhi=VHI, tqmax=TQMAX):
    return g["eng"] & (g["vego"] >= vlo) & (g["vego"] < vhi) & (np.abs(g["bar"]) < tqmax)


def up1k(x):
    """100 Hz -> 1 kHz band-limited (FIR, zero phase); the frame axis is uniform in k so this is valid."""
    return signal.resample_poly(x - x[0], 10, 1) + x[0]


# ======================================================================================================================
# pooled cross-spectra
# ======================================================================================================================
class Pool:
    def __init__(self, fs, nperseg):
        self.fs, self.nps, self.f, self.S, self.n = fs, nperseg, None, {}, 0

    def add(self, sigs):
        n = len(next(iter(sigs.values())))
        if n < self.nps:
            return
        nw = max(1, (n - self.nps // 2) // (self.nps // 2))
        keys = list(sigs)
        for i, a in enumerate(keys):
            for b in keys[i:]:
                f, P = signal.csd(sigs[a], sigs[b], fs=self.fs, nperseg=self.nps, detrend="constant")
                self.f = f; self.S[(a, b)] = self.S.get((a, b), 0) + nw * P
        self.n += nw

    def s(self, a, b):
        return self.S[(a, b)] / self.n if (a, b) in self.S else np.conj(self.S[(b, a)]) / self.n

    def coh(self, a, b):
        return np.abs(self.s(a, b)) ** 2 / (np.real(self.s(a, a)) * np.real(self.s(b, b)))

    def tf(self, u, y, ref=None):
        ref = u if ref is None else ref
        return self.s(ref, y) / self.s(ref, u)


def at(f, X, f0):
    return np.interp(f0, f, X)


def native_tap_segment(g, a, b):
    """the tap samples inside 100 Hz frames [a, b) and the 100 Hz signals resampled at those instants (1 kHz FIR, nearest tick)."""
    t0, t1 = g["t"][a], g["t"][b - 1]
    sel = (g["T_t"] >= t0) & (g["T_t"] <= t1)
    if sel.sum() < 8:
        return None
    tt = g["T_t"][sel]
    # 1 kHz reconstruction of the frame-axis signals over [a, b)
    seg = slice(max(0, a - 20), min(len(g["t"]), b + 20))
    t1k = g["t"][seg.start] + np.arange((seg.stop - seg.start) * 10) * g["P18"] / 10
    out = {"T": g["T"][sel]}
    for nm, src in (("r", g["rate_x"]), ("q", g["bar"]), ("c", g["cmd"])):
        x1k = up1k(src[seg])
        j = np.clip(np.round((tt - t1k[0]) / (g["P18"] / 10)).astype(int), 0, len(x1k) - 1)
        out[nm] = x1k[j]
    return out


# ======================================================================================================================
# firmware side: L_fw (kpflat_sizing.L_fw, copied verbatim so this file does not import a module that runs on import)
# ======================================================================================================================
def L_fw(c, f, kp, kd=128, lag=None, fb=None, post=254):
    """T counts per deg/s of wheel rate, open loop, one 1 kHz tick of transport; kp = Kp table value (P = E*kp>>8)."""
    z = np.exp(1j * 2 * np.pi * f / FS1K)
    la, lb = lag if lag else (c["lag_a"], c["lag_b"])
    fa, fbb = fb if fb else (c["fb_a"], c["fb_b"])
    Hlag = (lb / 1024.0) * (1 + 1 / z) / (1 - (la / 1024.0) / z) / 32.0
    Hfb = (fbb / 1024.0) * (1 + 1 / z) / (1 - (fa / 1024.0) / z)
    C = (kp / 256.0 + kd / 8.0 * (1 - 1 / z)) * (post / 256.0) * Hlag * (c["gain"] / 32768.0)
    return C * Hfb * LG.CPD / z


def margins(f, Lc, lo, hi):
    band = (f >= lo) & (f <= hi)
    fb_, mag = f[band], np.abs(Lc[band])
    ph = np.degrees(np.unwrap(np.angle(Lc[band])))
    out = dict(pm=None, gm=None, fc=None, f180=None)
    for i in range(len(fb_) - 2, -1, -1):
        if (mag[i] - 1) * (mag[i + 1] - 1) <= 0 and mag[i] != mag[i + 1]:
            t = (1 - mag[i]) / (mag[i + 1] - mag[i])
            out["fc"] = fb_[i] + t * (fb_[i + 1] - fb_[i]); out["pm"] = 180 + ph[i] + t * (ph[i + 1] - ph[i]); break
    for i in range(len(fb_) - 1):
        if (ph[i] + 180) * (ph[i + 1] + 180) <= 0 and ph[i] != ph[i + 1]:
            t = (-180 - ph[i]) / (ph[i + 1] - ph[i])
            out["f180"] = fb_[i] + t * (fb_[i + 1] - fb_[i]); out["gm"] = 1 / (mag[i] + t * (mag[i + 1] - mag[i])); break
    sens = 1 / np.abs(1 + Lc[band]); out["sens"] = float(sens.max()); out["fsens"] = float(fb_[np.argmax(sens)])
    return out


def fmt_m(m):
    return "%s  %s  Ms %.2f @ %.1f Hz" % (
        ("PM %4.0f deg @ %4.1f Hz" % (m["pm"], m["fc"])) if m["pm"] is not None else "PM --- (no unity crossing)",
        ("GM %5.2fx @ %4.1f Hz" % (m["gm"], m["f180"])) if m["gm"] is not None else "GM --- (no -180 in band)", m["sens"], m["fsens"])


# ======================================================================================================================
# the chain mirror (1 kHz) with switches
# ======================================================================================================================
def simulate(g, a, b, mapY, kp_cap=None, kd=V.KD, lag=(V.OA, V.OB), fb_single=False, cmd_mode="zoh", rate_filter=None, freeze_cmd=False):
    """FUN_00028ea6 on frames [a, b): returns dict at 1 kHz (t1k, T, P-only T, D-only T, rails) -- open loop on the measured rate."""
    seg = slice(max(0, a - 50), min(len(g["t"]), b + 10))
    n1 = (seg.stop - seg.start) * 10
    t1k = g["t"][seg.start] + np.arange(n1) * g["P18"] / 10
    wire = up1k(g["wire"][seg])
    if rate_filter is not None:
        sos = signal.butter(4, rate_filter, btype="lowpass", fs=FS1K, output="sos"); wire = signal.sosfiltfilt(sos, wire)
    x = -wire                                                       # gp-0x6a56 = -0x18F rate
    # feedback: s_new = (923 s + 1560 x) >> 10 ; fb = s_old + s_new (two-sample sum, DC 30.89)  [single: fb = 2*s_new]
    s = 0.0; fb = np.empty(n1)
    for i in range(n1):
        s_new = np.floor((V.A_COEF * s + V.B_COEF * x[i]) / 1024.0)
        fb[i] = (2 * s_new) if fb_single else (s + s_new)
        s = s_new
    fb = np.clip(fb, -46080, 46080)
    cmd = g["cmd"][seg]; bar = g["bar"][seg]
    if freeze_cmd:
        cmd = np.full_like(cmd, np.median(cmd))
    if cmd_mode == "zoh":
        cmd1k = np.repeat(cmd, 10); bar1k = np.repeat(bar, 10)
    else:
        cmd1k = np.interp(t1k, g["t"][seg], cmd); bar1k = np.interp(t1k, g["t"][seg], bar)
    idx, sgn = V.demand(np.round(cmd1k), bar1k)
    idx = np.round(idx)
    kpY = V.KP_Y if kp_cap is None else np.minimum(V.KP_Y, kp_cap)
    sp = sgn * V.lerp(V.MAP_X, mapY, idx)                          # L951-974
    kp = V.lerp(V.KP_X, kpY, idx)
    E = 32 * sp - fb                                               # L975
    P = np.clip(np.floor(E * kp / 256), -V.P_CLAMP, V.P_CLAMP)      # L1013-1052
    dE = np.r_[0.0, np.diff(E)]
    D = np.clip(np.floor(dE * kd / 8), -V.D_CLAMP, V.D_CLAMP)        # L1053-1092
    eng1k = np.repeat(g["eng"][seg], 10)

    def post(u):
        S = np.clip(np.floor(V.SUM_MULT * u / 256), -V.SUM_CLAMP, V.SUM_CLAMP); S[~eng1k] = 0.0
        st = signal.lfilter([lag[1] / 1024.0], [1.0, -lag[0] / 1024.0], S); y = (np.r_[0.0, st[:-1]] + st) / 32.0
        return np.clip(np.floor(-y * V.GAIN / 32768), -V.OUT_CAP, V.OUT_CAP)
    T = post(P + D); TP = post(P); TD = post(D)
    return dict(t1k=t1k, T=T, TP=TP, TD=TD, P=P, D=D, E=E, fb=fb, idx=idx, kp=kp,
                prail=float(np.mean(np.abs(E * kp / 256) >= V.P_CLAMP)), drail=float(np.mean(np.abs(dE * kd / 8) > V.D_CLAMP)),
                srail=float(np.mean(np.abs(V.SUM_MULT * (P + D) / 256) >= V.SUM_CLAMP)), tcap=float(np.mean(np.abs(T) >= V.OUT_CAP)))


def bamp(x, lo, hi, fs):
    if len(x) < 32:
        return np.nan
    sos = signal.butter(4, (lo, min(hi, 0.98 * fs / 2)), btype="bandpass", fs=fs, output="sos")
    y = signal.sosfiltfilt(sos, x - np.mean(x))
    return float(np.sqrt(2) * y.std())


def bandpass(x, lo, hi, fs):
    sos = signal.butter(4, (lo, min(hi, 0.98 * fs / 2)), btype="bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x - np.mean(x))


# ======================================================================================================================
def main():
    C = LG.read_build(LG.FW + LG.IMAGES["V280r2"])
    C3 = LG.read_build(LG.FW + LG.IMAGES["V278r3"])
    MAPY["r31"] = C3["map_Y"]; MAPY["r32"] = MAPY["r33"] = MAPY["r34"] = C["map_Y"]
    pr("CELLS FROM THE V280r2 IMAGE (slot 7): map Y %s ; Kp X %s Y %s ; Kd %s ; lag %d/%d ; fb %d/%d ; gain %d @0x%X ; fb clamp %d" % (
        C["map_Y"].astype(int).tolist(), C["kp_X"].astype(int).tolist(), C["kp_Y"].astype(int).tolist(), C["kd_Y"].astype(int).tolist(),
        C["lag_a"], C["lag_b"], C["fb_a"], C["fb_b"], C["gain"], C["gain_addr"], C["fb_clamp"]))
    pr("  rev 3 map Y %s (r31)" % C3["map_Y"].astype(int).tolist())
    G = {}
    for tag in ROUTES:
        print("loading %s ..." % tag, flush=True)
        G[tag] = load(tag)
    pr("\n" + "=" * 150)
    pr("TIMING MODEL: per-stream fitted period and the residual t_logged - t_nominal (p50 / p90 / fraction > 3 ms).  Nominal = frame counter x period + lower envelope.")
    pr("=" * 150)
    for tag, g in G.items():
        pr("  %s  0x18F P %.5f ms res %.1f/%.1f ms >3ms %.2f | 0x1AB P %.5f ms res %.1f/%.1f ms >3ms %.2f | 0xE4 P %.5f ms res %.1f/%.1f ms >3ms %.2f" % (
            tag, 1e3 * g["P18"], 1e3 * g["res"]["f18"][0], 1e3 * g["res"]["f18"][1], g["res"]["f18"][2],
            1e3 * g["P1ab"], 1e3 * g["res"]["f1ab"][0], 1e3 * g["res"]["f1ab"][1], g["res"]["f1ab"][2],
            1e3 * g["Pe4"], 1e3 * g["res"]["fe4"][0], 1e3 * g["res"]["fe4"][1], g["res"]["fe4"][2]))
    pr("  (a 3 ms residual is 22 deg at 20 Hz; the raw logged dt had p1/p99 = 0/19.5 ms on 0x18F and 9.8/30 ms on 0x1AB)")

    # ---------------------------------------------------------------------------------------------------------- PART 1
    pr("\n" + "=" * 150)
    pr("PART 1 -- PLANT G = rate_x / T in the CREEP stratum (engaged, v %.0f-%.0f m/s, |bar| < %.0f raw), 50 Hz pools on the tap's own instants" % (VLO, VHI, TQMAX))
    pr("  nperseg 64 (0.78 Hz bins, runs >= 1.28 s) and 128 (0.39 Hz, runs >= 2.56 s).  |G| x1e-3 deg/s per T count, phase deg, sign chosen so the")
    pr("  1-3 Hz direct phase is nearest 0 (same rule as plant_id_v278r3_tap.py).  direct = S_Tr/S_TT (closed-loop biased toward -1/C where the")
    pr("  loop's disturbance dominates) ; IVc = S_cr/S_cT (0xE4 command as instrument) ; IVq = S_qr/S_qT (bar as instrument).")
    pr("=" * 150)
    pools = {}
    secs = {}
    for nps in (64, 128):
        for tag, g in G.items():
            m = creep_mask(g)
            for a, b in runs(m, int(nps / FST * FS)):
                seg = native_tap_segment(g, a, b)
                if seg is None or len(seg["T"]) < nps:
                    continue
                for key in (("all", nps), (tag, nps)):
                    pools.setdefault(key, Pool(FST, nps)).add(seg)
                    secs[key] = secs.get(key, 0) + (b - a) / FS
    pr("  creep seconds in usable runs: " + " ; ".join("%s nps%d %.1f s (%d w)" % (k[0], k[1], secs.get(k, 0), pools[k].n) for k in sorted(pools, key=str) if k in pools))
    plant = {}
    for key in (("all", 64), ("all", 128)):
        P = pools[key]; f = P.f
        Gd, Gc, Gq = P.tf("T", "r"), P.tf("T", "r", ref="c"), P.tf("T", "r", ref="q")
        lo = (f >= 1) & (f <= 3)
        sgn = 1.0 if abs(np.angle(np.mean(Gd[lo]))) <= np.pi / 2 else -1.0
        plant[key] = dict(f=f, Gd=sgn * Gd, Gc=sgn * Gc, Gq=sgn * Gq, sgn=sgn, cTr=P.coh("T", "r"), ccT=P.coh("c", "T"), ccr=P.coh("c", "r"),
                          cqT=P.coh("q", "T"), cqr=P.coh("q", "r"), HTr=P.tf("r", "T"), Hqr=P.tf("r", "q"), cqr_=P.coh("q", "r"), P=P)
        pr("\n  POOLED %s nperseg %d (%d windows, sign %+d)" % (key[0], key[1], P.n, sgn))
        pr("    %5s | %7s %6s %5s | %7s %6s %5s %5s | %7s %6s %5s %5s" % ("f", "|Gdir|", "ph", "cohTr", "|G_IVc|", "ph", "cohcT", "cohcr", "|G_IVq|", "ph", "cohqT", "cohqr"))
        for f0 in FREQS:
            pr("    %5.1f | %7.2f %6.0f %5.2f | %7.2f %6.0f %5.2f %5.2f | %7.2f %6.0f %5.2f %5.2f" % (
                f0, 1e3 * abs(at(f, plant[key]["Gd"], f0)), np.degrees(np.angle(at(f, plant[key]["Gd"], f0))), at(f, plant[key]["cTr"], f0),
                1e3 * abs(at(f, plant[key]["Gc"], f0)), np.degrees(np.angle(at(f, plant[key]["Gc"], f0))), at(f, plant[key]["ccT"], f0), at(f, plant[key]["ccr"], f0),
                1e3 * abs(at(f, plant[key]["Gq"], f0)), np.degrees(np.angle(at(f, plant[key]["Gq"], f0))), at(f, plant[key]["cqT"], f0), at(f, plant[key]["cqr"], f0)))
    pr("\n  PER ROUTE, nperseg 64, direct |G|x1e-3 / phase / cohTr at 15 / 20 / 22 Hz, and the T and rate line power at 20 Hz relative to 15 Hz:")
    for tag in ROUTES:
        key = (tag, 64)
        if key not in pools or pools[key].n < 4:
            pr("    %s: too little data" % tag); continue
        P = pools[key]; f = P.f; Gd = P.tf("T", "r"); lo = (f >= 1) & (f <= 3)
        sgn = 1.0 if abs(np.angle(np.mean(Gd[lo]))) <= np.pi / 2 else -1.0
        STT, Srr = np.real(P.s("T", "T")), np.real(P.s("r", "r"))
        pr("    %s %-16s (%3d w, %.0f s): %s | S_TT(20)/S_TT(15) %.1f  S_rr(20)/S_rr(15) %.1f" % (
            tag, BUILD[tag], P.n, secs[key], "  ".join("%.0fHz %.2f/%+.0f/%.2f" % (x, 1e3 * abs(at(f, sgn * Gd, x)), np.degrees(np.angle(at(f, sgn * Gd, x))), at(f, P.coh("T", "r"), x)) for x in (15, 20, 22)),
            at(f, STT, 20) / at(f, STT, 15), at(f, Srr, 20) / at(f, Srr, 15)))

    # ---- the -1/C identity: measured T per deg/s vs the firmware's controller ---------------------------------------
    key = ("all", 64); Pk = plant[key]; f = Pk["f"]
    # median idx / Kp over the creep line seconds
    idxs = np.concatenate([g["idx"][creep_mask(g)] for g in G.values()])
    idx50 = float(np.median(idxs)); kp50 = float(np.interp(idx50, C["kp_X"], C["kp_Y"]))
    pr("\n  CREEP idx p10/p50/p90 = %.0f/%.0f/%.0f -> Kp(idx p50) = %.0f (LERP X %s Y %s); Kp range over p10-p90 %.0f-%.0f" % (
        np.percentile(idxs, 10), idx50, np.percentile(idxs, 90), kp50, C["kp_X"].astype(int).tolist(), C["kp_Y"].astype(int).tolist(),
        np.interp(np.percentile(idxs, 10), C["kp_X"], C["kp_Y"]), np.interp(np.percentile(idxs, 90), C["kp_X"], C["kp_Y"])))
    pr("  D/P at 20 Hz, analytic: |D|/|P| = 16*2*sin(pi*20/1000) / (Kp/256): Kp 248 -> %.2f, Kp %.0f -> %.2f, Kp 470 -> %.2f  (D is on E at 1 kHz)" % (
        16 * 2 * np.sin(np.pi * 20 / 1000) / (248 / 256.), kp50, 16 * 2 * np.sin(np.pi * 20 / 1000) / (kp50 / 256.), 16 * 2 * np.sin(np.pi * 20 / 1000) / (470 / 256.)))
    pr("\n  THE CONTROLLER IDENTITY TEST: measured H_Tr = T per deg/s of rate_x (S_rT/S_rr) vs the firmware's L_fw(Kp %.0f, Kd 128) -- if T is the loop's" % kp50)
    pr("  own response to the rate, these agree in magnitude AND phase whether the line is a loop mode or a transmitted disturbance (T = C(rate) always).")
    pr("    %5s | %8s %6s | %8s %6s | %6s %6s" % ("f", "|H_Tr|", "ph", "|L_fw|", "ph", "ratio", "dph"))
    for f0 in FREQS:
        H = at(f, Pk["HTr"], f0); Lf = L_fw(C, f0, kp50)
        # sign: the tap and the wire share a convention where the lane's damping reads sign(T) != sign(wire); rate_x = -wire/8, so T/rate_x > 0 = damping
        pr("    %5.1f | %8.1f %6.0f | %8.1f %6.0f | %6.2f %6.0f" % (f0, abs(H), np.degrees(np.angle(H)), abs(Lf), np.degrees(np.angle(Lf)), abs(H) / abs(Lf),
                                                                  (np.degrees(np.angle(H / Lf)) + 180) % 360 - 180))
    pr("  (phase sign conventions: H_Tr uses the raw tap sign and rate_x = -wire/8; L_fw drops the firmware's (-1); a constant 0 or 180 offset is convention, a slope is timing)")

    # ---- L_in --------------------------------------------------------------------------------------------------------
    pr("\n  INNER LOOP L_in(f) = L_fw(Kp, Kd 128, stock lag/fb, one tick) * G(f), G = the creep estimates above (interpolated), 2-24 Hz band")
    pr("    %-34s | %-7s | |L| ph @ 15 / 18 / 20 / 22 Hz | margins" % ("G source", "Kp"))
    fine = np.linspace(2.0, 24.0, 2201)
    Lres = {}
    for gname, Gsrc in (("direct nps64", plant[("all", 64)]["Gd"]), ("direct nps128", plant[("all", 128)]["Gd"]), ("cmd-IV nps64", plant[("all", 64)]["Gc"]), ("bar-IV nps64", plant[("all", 64)]["Gq"])):
        fsrc = plant[("all", 64)]["f"] if "64" in gname else plant[("all", 128)]["f"]
        Gi = np.interp(fine, fsrc, np.real(Gsrc)) + 1j * np.interp(fine, fsrc, np.imag(Gsrc))
        for kplab, kpv in (("Kp(idx p50) %.0f" % kp50, kp50), ("Kp 248 (idx 0)", 248.0), ("Kp 341 (V281 cap)", 341.0), ("Kp 470 (idx 56)", 470.0)):
            Lc = np.array([L_fw(C, x, kpv) for x in fine]) * Gi
            m = margins(fine, Lc, 2.0, 24.0); Lres[(gname, kplab)] = (Lc, m)
            pr("    %-34s | %-7s | %s | %s" % (gname if kplab.startswith("Kp(idx") else "", kplab.split()[0] + " " + kplab.split()[1] if not kplab.startswith("Kp(") else "%.0f" % kpv,
                                             " ".join("%.2f/%+.0f" % (abs(at(fine, Lc, x)), np.degrees(np.angle(at(fine, Lc, x)))) for x in (15, 18, 20, 22)), fmt_m(m)))
    # Kd counterfactuals on the loop, direct G
    Gi = np.interp(fine, plant[("all", 64)]["f"], np.real(plant[("all", 64)]["Gd"])) + 1j * np.interp(fine, plant[("all", 64)]["f"], np.imag(plant[("all", 64)]["Gd"]))
    pr("    counterfactual loops on the direct-nps64 G, Kp %.0f:" % kp50)
    for lab, kw in (("Kd 0", dict(kd=0)), ("Kd 64", dict(kd=64)), ("lag 960/1014 (10 Hz pole, same DC)", dict(lag=(960, 1014))), ("lag 1008/253 (2.5 Hz pole)", dict(lag=(1008, 253))),
                    ("fb single-sample x2 (same DC)", dict(fb=(923, 1560)))):
        Lc = np.array([L_fw(C, x, kp50, **kw) for x in fine]) * Gi
        if lab.startswith("fb single"):
            z = np.exp(1j * 2 * np.pi * fine / FS1K); Lc = Lc * 2 / (1 + 1 / z)      # 2 s_new instead of s_old + s_new
        m = margins(fine, Lc, 2.0, 24.0)
        pr("      %-40s |L| ph @ 20 Hz %.2f/%+.0f | %s" % (lab, abs(at(fine, Lc, 20)), np.degrees(np.angle(at(fine, Lc, 20))), fmt_m(m)))

    # ---- bar vs rate mechanics ---------------------------------------------------------------------------------------
    pr("\n  BAR vs RATE at the line (100 Hz streams, same frame -> no inter-stream timing): H_qr = bar per deg/s of rate_x, from the creep pools.")
    pr("  spring against a still wheel: bar = -k*theta_c -> bar/rate = -k/(jw): phase -90, |H| = k/w falling 1/f ; wheel inertia dragged: bar = J*d(rate)/dt: +90, |H| rising with f")
    pr("    %5s | %8s %6s %5s" % ("f", "|H_qr|", "ph", "coh"))
    Pq = pools[("all", 64)]
    for f0 in (10.0, 15.0, 18.0, 20.0, 22.0):
        H = at(Pq.f, Pq.tf("r", "q"), f0)
        pr("    %5.1f | %8.1f %6.0f %5.2f" % (f0, abs(H), np.degrees(np.angle(H)), at(Pq.f, Pq.coh("q", "r"), f0)))
    # also the 100 Hz bar/rate to 40 Hz on all creep runs
    P100 = Pool(FS, 128)
    for g in G.values():
        for a, b in runs(creep_mask(g), 128):
            P100.add({"q": g["bar"][a:b], "r": g["rate_x"][a:b], "c": g["cmd"][a:b]})
    pr("    100 Hz streams, nperseg 128 (%d w): |H_qr| / ph / coh at 10/15/20/25/30/35/40 Hz: %s" % (P100.n, "  ".join(
        "%.0f: %.1f/%+.0f/%.2f" % (x, abs(at(P100.f, P100.tf("r", "q"), x)), np.degrees(np.angle(at(P100.f, P100.tf("r", "q"), x))), at(P100.f, P100.coh("q", "r"), x)) for x in (10, 15, 20, 25, 30, 35, 40))))
    Sqq, Srr = np.real(P100.s("q", "q")), np.real(P100.s("r", "r"))
    R = G2.prom_spectrum(P100.f, Sqq)
    f0q, pq = G2.locate(P100.f, Sqq, 12, 45, R=R)
    f0r, prr = G2.locate(P100.f, Srr, 12, 45)
    pr("    pooled creep PSD lines 12-45 Hz: bar %.2f Hz x%.1f ; rate %.2f Hz x%.1f ; bar PSD at 10/20/30/40 Hz %s" % (f0q, pq, f0r, prr, " ".join("%.3g" % at(P100.f, Sqq, x) for x in (10, 20, 30, 40))))

    # ---------------------------------------------------------------------------------------------------------- PART 2
    pr("\n" + "=" * 150)
    pr("PART 2 -- FREQUENCY vs STATE: 2 s windows (step 0.5 s), engaged, v < 6 m/s, all four routes; bar periodogram (Hann, nfft 4096), line = most")
    pr("  prominent 15-26 Hz (G2.locate, floor = local median +-6 Hz excl 1.5); 'line present' = prominence >= 8 and bar 18-22 amp >= 40 raw.")
    pr("=" * 150)
    rows = []
    W, STEP = 200, 50
    for tag, g in G.items():
        m = g["eng"] & (g["vego"] < 6.0)
        for a, b in runs(m, W):
            for s in range(a, b - W + 1, STEP):
                e = s + W
                x = g["bar"][s:e] - g["bar"][s:e].mean()
                f, Pxx = signal.periodogram(x, fs=FS, window="hann", nfft=4096)
                Rp = G2.prom_spectrum(f, Pxx, 6.0, 1.5)
                f0, prom = G2.locate(f, Pxx, LINE_LO, LINE_HI, R=Rp)
                xr = g["rate_x"][s:e]; fr, Prr_ = signal.periodogram(xr - xr.mean(), fs=FS, window="hann", nfft=4096)
                f0r_, promr = G2.locate(fr, Prr_, LINE_LO, LINE_HI)
                Tw = g["T100"][s:e]
                rows.append(dict(tag=tag, t=g["t"][s] - g["t"][0], f0=f0, prom=prom, f0r=f0r_, promr=promr, amp=bamp(g["bar"][s:e], 18, 22, FS),
                                 ramp=bamp(g["wire"][s:e], 18, 22, FS) / V.CPD, rate=float(np.mean(np.abs(g["wire"][s:e])) / V.CPD), v=float(g["vego"][s:e].mean()),
                                 ang=float(np.median(np.abs(g["ang"][s:e]))), T=float(np.median(np.abs(Tw))), Tmean=float(np.mean(Tw)), idx=float(np.median(g["idx"][s:e])),
                                 tq=float(np.median(np.abs(g["bar"][s:e]))), cmd=float(np.median(np.abs(g["cmd"][s:e]))), creep=bool(VLO <= g["vego"][s:e].mean() < VHI)))
    R = {k: np.array([r[k] for r in rows]) for k in rows[0]}
    present = (R["prom"] >= 8) & (R["amp"] >= 40)
    pr("  windows: %d engaged v<6 ; line present %d (%.0f %%) ; in creep (1-3 m/s) %d of %d" % (len(rows), present.sum(), 100 * present.mean(), (present & R["creep"]).sum(), R["creep"].sum()))
    pr("  f_line over present windows: mean %.2f sd %.2f p10/p50/p90 %.2f/%.2f/%.2f Hz ; rate-line agrees with bar-line within 0.5 Hz in %.0f %% of them" % (
        R["f0"][present].mean(), R["f0"][present].std(), *np.percentile(R["f0"][present], (10, 50, 90)), 100 * np.mean(np.abs(R["f0"][present] - R["f0r"][present]) < 0.5)))
    for tag in ROUTES:
        sel = present & (R["tag"] == tag)
        if sel.sum() < 3:
            pr("    %s: %d present windows" % (tag, sel.sum())); continue
        pr("    %s %-16s n=%3d  f mean %.2f sd %.2f p10/p90 %.2f/%.2f | |rate| p10/p90 %.1f/%.1f deg/s  v %.1f-%.1f  |T| p50 %.0f idx p50 %.0f amp p50 %.0f" % (
            tag, BUILD[tag], sel.sum(), R["f0"][sel].mean(), R["f0"][sel].std(), *np.percentile(R["f0"][sel], (10, 90)), *np.percentile(R["rate"][sel], (10, 90)),
            *np.percentile(R["v"][sel], (10, 90)), np.median(R["T"][sel]), np.median(R["idx"][sel]), np.median(R["amp"][sel])))
    pr("  f_line vs state over present windows (Spearman rho, p ; OLS slope per unit with 95 %% CI ; and what a proportional law would predict across p10-p90):")
    for k, unit, law in (("rate", "deg/s", "cogging/mesh: f prop. to |rate|"), ("v", "m/s", "tyre/road: f prop. to v"), ("ang", "deg", ""), ("T", "T counts", ""), ("idx", "idx", "loop mode: f rises with Kp(idx)"), ("tq", "raw", "")):
        x, y = R[k][present], R["f0"][present]
        rho, p = stats.spearmanr(x, y)
        sl, ic, rv, pv, se = stats.linregress(x, y)
        p10, p90 = np.percentile(x, (10, 90))
        pred = "f would go %.1f -> %.1f Hz" % (y.mean() * p10 / max(x.mean(), 1e-9), y.mean() * p90 / max(x.mean(), 1e-9)) if law else ""
        pr("    %-5s rho %+.2f p %.3f | slope %+.3f +- %.3f Hz/%s | over p10-p90 (%.1f-%.1f %s) measured f changes by %+.2f Hz | %s %s" % (
            k, rho, p, sl, 1.96 * se, unit, p10, p90, unit, sl * (p90 - p10), law, pred))
    # binned by |rate|
    pr("  f_line by |rate| tertile (present windows): " + " ; ".join("%.1f-%.1f deg/s: f %.2f (n %d)" % (lo, hi, R["f0"][present & (R["rate"] >= lo) & (R["rate"] <= hi)].mean(), (present & (R["rate"] >= lo) & (R["rate"] <= hi)).sum())
                                                              for lo, hi in zip(np.percentile(R["rate"][present], (0, 33, 67)), np.percentile(R["rate"][present], (33, 67, 100)))))
    pr("  f_line by idx bin: " + " ; ".join("idx %s: f %.2f sd %.2f (n %d)" % (lab, R["f0"][sel].mean(), R["f0"][sel].std(), sel.sum()) for lab, sel in (
        ("0", present & (R["idx"] == 0)), ("1-20", present & (R["idx"] > 0) & (R["idx"] <= 20)), ("20-60", present & (R["idx"] > 20) & (R["idx"] <= 60)), (">60", present & (R["idx"] > 60))) if sel.sum() >= 2))
    pr("  f_line by speed bin: " + " ; ".join("v %s: f %.2f sd %.2f (n %d)" % (lab, R["f0"][sel].mean(), R["f0"][sel].std(), sel.sum()) for lab, sel in (
        ("<1", present & (R["v"] < 1)), ("1-2", present & (R["v"] >= 1) & (R["v"] < 2)), ("2-3", present & (R["v"] >= 2) & (R["v"] < 3)), ("3-6", present & (R["v"] >= 3))) if sel.sum() >= 2))
    # manual creep presence
    pr("  MANUAL (disengaged) creep windows, same detector:")
    mrows = []
    for tag, g in G.items():
        m = (~g["eng"]) & g["have18"] & (g["vego"] >= VLO) & (g["vego"] < VHI)
        for a, b in runs(m, W):
            for s in range(a, b - W + 1, STEP):
                e = s + W; x = g["bar"][s:e] - g["bar"][s:e].mean()
                f, Pxx = signal.periodogram(x, fs=FS, window="hann", nfft=4096)
                f0, prom = G2.locate(f, Pxx, LINE_LO, LINE_HI)
                mrows.append((tag, f0, prom, bamp(g["bar"][s:e], 18, 22, FS), float(np.median(np.abs(g["bar"][s:e])))))
    if mrows:
        mp = np.array([r[2] for r in mrows]); ma = np.array([r[3] for r in mrows])
        pr("    n=%d windows, line present (prom>=8 & amp>=40) in %d (%.0f %%) ; bar 18-22 amp p50/p90 %.0f/%.0f raw ; |bar| p50 %.0f" % (
            len(mrows), ((mp >= 8) & (ma >= 40)).sum(), 100 * np.mean((mp >= 8) & (ma >= 40)), *np.percentile(ma, (50, 90)), np.median([r[4] for r in mrows])))

    # ---------------------------------------------------------------------------------------------------------- PART 3
    pr("\n" + "=" * 150)
    pr("PART 3 -- EXCITATION")
    pr("=" * 150)
    Pk64 = pools[("all", 64)]
    pr("  (a) 0xE4 command in the creep pools (native 50 Hz tap instants): coherence cmd<->T and cmd<->bar at 15/18/20/22 Hz: %s" % "  ".join(
        "%.0f: cT %.2f cq %.2f" % (x, at(Pk64.f, Pk64.coh("c", "T"), x), at(Pk64.f, Pk64.coh("c", "q"), x)) for x in (15, 18, 20, 22)))
    Scc = np.real(P100.s("c", "c"))
    f0c, pc = G2.locate(P100.f, Scc, 12, 45)
    pr("      cmd PSD (100 Hz creep pools, nperseg 128): line 12-45 Hz at %.2f Hz x%.1f ; PSD at 10/20/30/40 Hz %s ; coh cmd-bar at 20 Hz %.2f" % (
        f0c, pc, " ".join("%.3g" % at(P100.f, Scc, x) for x in (10, 20, 30, 40)), at(P100.f, P100.coh("c", "q"), 20)))
    # period-5 structure: does the command move every 5th frame?
    for tag, g in G.items():
        m = creep_mask(g)
        dc = np.diff(g["cmd"]); mm = m[1:] & m[:-1]
        d = np.abs(dc[mm])
        ac = [np.corrcoef(d[:-L], d[L:])[0, 1] for L in range(1, 11)]
        f, Pd = signal.welch(dc[mm] - dc[mm].mean(), fs=FS, nperseg=256)
        f0d, pd_ = G2.locate(f, Pd, 12, 45)
        pr("      %s: P(cmd changes frame to frame) %.2f ; |dcmd| autocorr lags 1..10: %s ; dcmd PSD line %.1f Hz x%.1f" % (
            tag, np.mean(d > 0), " ".join("%+.2f" % a for a in ac), f0d, pd_))
    # (b) presence vs T and idx
    pr("  (b) line amplitude vs the lane's output, creep windows (all engaged 1-3 m/s windows, not only 'present'):")
    cw = R["creep"]
    for k in ("T", "idx", "cmd", "rate", "tq"):
        rho, p = stats.spearmanr(R[k][cw], R["amp"][cw]); rho2, p2 = stats.spearmanr(R[k][cw], R["prom"][cw])
        pr("      bar 18-22 amp vs %-4s rho %+.2f (p %.3f) ; prominence vs %-4s rho %+.2f (p %.3f)" % (k, rho, p, k, rho2, p2))
    pr("      by |T| bin: " + " ; ".join("%s: n %d present %.0f %% amp p50 %.0f rate-amp %.2f" % (lab, sel.sum(), 100 * present[sel].mean(), np.median(R["amp"][sel]), np.median(R["ramp"][sel]))
                                        for lab, sel in (("T=0", cw & (R["T"] == 0)), ("1-100", cw & (R["T"] > 0) & (R["T"] <= 100)), ("100-300", cw & (R["T"] > 100) & (R["T"] <= 300)), (">300", cw & (R["T"] > 300))) if sel.sum() >= 2))
    pr("      by idx bin: " + " ; ".join("%s: n %d present %.0f %% amp p50 %.0f" % (lab, sel.sum(), 100 * present[sel].mean(), np.median(R["amp"][sel]))
                                        for lab, sel in (("idx 0", cw & (R["idx"] == 0)), ("1-20", cw & (R["idx"] > 0) & (R["idx"] <= 20)), ("20-60", cw & (R["idx"] > 20) & (R["idx"] <= 60)), (">60", cw & (R["idx"] > 60))) if sel.sum() >= 2))
    pr("      engaged idx = 0 AND |T| < 16 (lane silent): n %d, present %.0f %%, amp p50 %.0f ; engaged idx > 10 AND |T| > 100: n %d, present %.0f %%, amp p50 %.0f" % (
        (cw & (R["idx"] == 0) & (R["T"] < 16)).sum(), 100 * present[cw & (R["idx"] == 0) & (R["T"] < 16)].mean() if (cw & (R["idx"] == 0) & (R["T"] < 16)).any() else np.nan,
        np.median(R["amp"][cw & (R["idx"] == 0) & (R["T"] < 16)]) if (cw & (R["idx"] == 0) & (R["T"] < 16)).any() else np.nan,
        (cw & (R["idx"] > 10) & (R["T"] > 100)).sum(), 100 * present[cw & (R["idx"] > 10) & (R["T"] > 100)].mean(), np.median(R["amp"][cw & (R["idx"] > 10) & (R["T"] > 100)])))
    # T at the line vs T level: ripple / level
    sel = present & cw
    Tamp = np.array([np.nan] * len(rows))
    pr("      T 18-22 amp (from the 100 Hz-interpolated tap, attenuated ~0.6 at 20 Hz by the 50 Hz hold) vs |T| level in present creep windows: Spearman of amp_bar vs |T| %+.2f" % stats.spearmanr(R["T"][sel], R["amp"][sel])[0])

    # ---------------------------------------------------------------------------------------------------------- PART 4
    pr("\n" + "=" * 150)
    pr("PART 4 -- CHAIN MIRROR on the operator's seconds (r34) and on every creep line window: T_sim (V280 map, ZOH cmd, 1 kHz) vs the tap")
    pr("  18-22 Hz: amp_sim / amp_meas, corr of the band-passed pair at the tap instants, cross-phase at the line (0 = timing model right), P vs D share;")
    pr("  then open-loop counterfactuals -- what the 20 Hz T content would be with the loop's own arithmetic changed and the SAME measured rate.")
    pr("=" * 150)

    def eval_window(g, a, b, **kw):
        S = simulate(g, a, b, MAPY[g["tag"]], **kw)
        t0, t1 = g["t"][a], g["t"][b - 1]
        sel = (g["T_t"] >= t0) & (g["T_t"] <= t1)
        tt = g["T_t"][sel]; Tm = g["T"][sel]
        j = np.clip(np.round((tt - S["t1k"][0]) / (g["P18"] / 10)).astype(int), 0, len(S["T"]) - 1)
        Ts, TP, TD = S["T"][j], S["TP"][j], S["TD"][j]
        o = dict(n=len(tt), Tmeas_p50=float(np.median(np.abs(Tm))), Tsim_p50=float(np.median(np.abs(Ts))), corr_all=float(np.corrcoef(Tm, Ts)[0, 1]) if len(tt) > 4 else np.nan,
                 amp_meas=bamp(Tm, 18, 22, FST), amp_sim=bamp(Ts, 18, 22, FST), amp_P=bamp(TP, 18, 22, FST), amp_D=bamp(TD, 18, 22, FST),
                 amp_sim1k=bamp(S["T"], 18, 22, FS1K), amp_P1k=bamp(S["TP"], 18, 22, FS1K), amp_D1k=bamp(S["TD"], 18, 22, FS1K),
                 prail=S["prail"], drail=S["drail"], srail=S["srail"], tcap=S["tcap"], kp=float(np.median(S["kp"])), idx=float(np.median(S["idx"])))
        if len(tt) >= 64:
            bm, bs = bandpass(Tm, 18, 22, FST), bandpass(Ts, 18, 22, FST)
            o["corr_band"] = float(np.corrcoef(bm, bs)[0, 1])
            f, Sxy = signal.csd(bm, bs, fs=FST, nperseg=64); f, Sxx = signal.welch(bm, fs=FST, nperseg=64); f, Syy = signal.welch(bs, fs=FST, nperseg=64)
            j20 = int(np.argmin(np.abs(f - 20)))
            o["phase"] = float(np.degrees(np.angle(Sxy[j20]))); o["coh"] = float(abs(Sxy[j20]) ** 2 / (Sxx[j20] * Syy[j20]))
        else:
            o["corr_band"] = o["phase"] = o["coh"] = np.nan
        return o

    def fmt_e(lab, o):
        return "    %-44s n %3d |T| meas/sim %4.0f/%4.0f corr %.2f | 18-22 amp meas %5.1f sim %5.1f (P %5.1f D %5.1f; 1k: sim %5.1f P %5.1f D %5.1f) corr_band %.2f phase %+4.0f coh %.2f | rails P %.2f D %.2f S %.2f cap %.2f | idx %3.0f Kp %3.0f" % (
            lab, o["n"], o["Tmeas_p50"], o["Tsim_p50"], o["corr_all"], o["amp_meas"], o["amp_sim"], o["amp_P"], o["amp_D"], o["amp_sim1k"], o["amp_P1k"], o["amp_D1k"], o["corr_band"], o["phase"], o["coh"],
            o["prail"], o["drail"], o["srail"], o["tcap"], o["idx"], o["kp"])
    g34 = G["r34"]
    pr("  OPERATOR'S SECONDS (r34, route t from the first 0x18F frame):")
    for (t0, t1) in OP_SECS["r34"]:
        a = int(np.searchsorted(g34["t"] - g34["t"][0], t0)); b = int(np.searchsorted(g34["t"] - g34["t"][0], t1))
        pr("   t %.1f-%.1f s: v %.1f m/s eng %.2f idx p50 %.0f |bar| p50 %.0f |T| p50 %.0f | bar 18-22 %.0f raw, rate 18-22 %.2f deg/s" % (
            t0, t1, g34["vego"][a:b].mean(), g34["eng"][a:b].mean(), np.median(g34["idx"][a:b]), np.median(np.abs(g34["bar"][a:b])), np.median(np.abs(g34["T100"][a:b])),
            bamp(g34["bar"][a:b], 18, 22, FS), bamp(g34["wire"][a:b], 18, 22, FS) / V.CPD))
        pr(fmt_e("as built (V280 map, Kd 128, ZOH cmd)", eval_window(g34, a, b)))
        pr(fmt_e("  linear-interp cmd (kit chain style)", eval_window(g34, a, b, cmd_mode="lin")))
        for lab, kw in (("Kd 0", dict(kd=0)), ("Kd 64", dict(kd=64)), ("Kp cap 341 (V281)", dict(kp_cap=341)), ("lag 960/1014 (10 Hz pole)", dict(lag=(960, 1014))),
                        ("lag 1008/253 (2.5 Hz pole)", dict(lag=(1008, 253))), ("fb single-sample x2", dict(fb_single=True)),
                        ("rate low-passed < 15 Hz (no line in fb)", dict(rate_filter=15.0)), ("cmd frozen (no setpoint motion)", dict(freeze_cmd=True)),
                        ("cmd frozen AND rate < 15 Hz", dict(freeze_cmd=True, rate_filter=15.0))):
            pr(fmt_e("  " + lab, eval_window(g34, a, b, **kw)))
    # pooled over all present creep windows (2 s windows -> merge into runs)
    pr("\n  ALL CREEP LINE WINDOWS (present, 1-3 m/s), pooled per route: medians of the same per-window quantities")
    for tag in ROUTES:
        g = G[tag]
        wins = [(int(round((r["t"]) * FS)), int(round((r["t"]) * FS)) + W) for r in rows if r["tag"] == tag and r["creep"] and r["prom"] >= 8 and r["amp"] >= 40]
        if len(wins) < 2:
            pr("    %s: %d windows" % (tag, len(wins))); continue
        base = [eval_window(g, a, b) for a, b in wins]
        med = lambda k, L: float(np.nanmedian([o[k] for o in L]))  # noqa: E731
        pr("    %s %-16s n=%d | 18-22 amp meas %.1f sim %.1f (P %.1f D %.1f) corr_band %.2f phase %+.0f coh %.2f | |T| meas %.0f sim %.0f | idx %.0f Kp %.0f | rails P %.2f D %.2f" % (
            tag, BUILD[tag], len(wins), med("amp_meas", base), med("amp_sim", base), med("amp_P", base), med("amp_D", base), med("corr_band", base), med("phase", base), med("coh", base),
            med("Tmeas_p50", base), med("Tsim_p50", base), med("idx", base), med("kp", base), med("prail", base), med("drail", base)))
        if tag == "r34":
            for lab, kw in (("Kd 0", dict(kd=0)), ("Kd 64", dict(kd=64)), ("Kp cap 341", dict(kp_cap=341)), ("lag 960/1014", dict(lag=(960, 1014))), ("lag 1008/253", dict(lag=(1008, 253))),
                            ("fb single x2", dict(fb_single=True)), ("rate < 15 Hz", dict(rate_filter=15.0)), ("cmd frozen", dict(freeze_cmd=True))):
                L = [eval_window(g, a, b, **kw) for a, b in wins]
                pr("      %-16s 18-22 amp sim %.1f (P %.1f D %.1f) = %.2f x as-built" % (lab, med("amp_sim", L), med("amp_P", L), med("amp_D", L), med("amp_sim", L) / max(med("amp_sim", base), 1e-9)))

    out = os.path.join(HERE, "_scratch", "creep20_loop_id.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
