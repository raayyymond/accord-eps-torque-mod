# -*- coding: utf-8 -*-
r"""gate2_rescore_stock_terms.py -- GATE 2 (closed-loop magnitude AND phase, 0.3-30 Hz) for the V299 angle loop
(cave + tuning as built) when the RELEASE reverts plant-side firmware terms to STOCK:

  D3  r24 driver-torque-derivative lane: engaged gain flat 2048 (V299, 0xC6446 via the 0x3AA96 gate repoint)
      -> Honda's mode-26 speed LERP (0xD7A88/AC4/B00/B3C plateau Y0 = 3072/2560/2303/2150 at 0/10/50/100 km/h)
  D8' DampAxis lane gp-0x6b26 (FUN_00041464 -> FUN_00036c12): speed Y 0xD7A5C (-29490,-17202,-16000) -> stock
      (-9830,-5734,-1966), and its EMA #2 alpha2 = 0xC40DC/64: 14 -> 22 (the census filed 0xC40DC under D5)
  D5  Coulomb relay 0xC40BC / K1 0xC40D2: inside FUN_0003b8f6, the plant-model OBSERVER (gp-0x6bfc -> plausibility
      latch FUN_0003bc20).  It writes no motor command (TRACE-2026-08-10-lkas-command-visibility.md section 3/5):
      EXCLUDED from the linear loop here; listed for the interlock lens.
  D8  r24 rate-axis roll-off flatten + damper/boost families: zero below ~85 deg/s in BOTH images (plateau Y0=Y1 and
      the stock damper dead zone) -> no small-signal term; large-signal direction discussed in the report only.

METHOD.  The identified plant family (v294_plant, r71b = V294 image, which CARRIED the V299-level terms) absorbs the
firmware lanes.  The release plant is therefore P' = P / (1 - P * F_delta) with F_delta = F_stock - F_v299 the change of
the lanes' torque-per-angle transfer, each lane mirrored from its decompiled integer arithmetic as an LTI filter at
1 kHz (clamps and the 3-count r24 deadband OFF = small-signal, the conservative reading for a linear gate).  Signs
are ANCHORED to on-car measurements the record holds (sigma_r: r24 anti-damps at 7 Hz; sigma_d: the DampAxis x3 of
V106 extinguished the 21-27 Hz mode => damping there) because the firmware-internal sign conventions of the summed
lanes are not pinned by the decompile alone -- BELIEF-anchored, stated in the report.
The r24 lane needs the hands-off torsion-bar twist per degree of wheel motion, H_tb(f) = T_raw / theta: MEASURED on
route 79 (V298 flight) from the 100 Hz wire (0x18F torque sensor / 0x14 angle) in engaged hands-off windows, Welch
CSD, cached once; a two-mass fit extrapolates above the coherent band.
Runs in a few seconds.  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.
"""
from __future__ import annotations
import glob
import json
import math
import os
import struct
import sys
import time
from pathlib import Path
import numpy as np

KIT = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
AL = KIT / "analysis-2020accord/studies/angle_loop"
for p in (AL, KIT / "analysis-2020accord/studies/v295/plant", KIT / "analysis-2020accord/studies/v295/lib",
          KIT / "analysis-2020accord/model", KIT / "rlog-tools/studies/grind"):
    sys.path.insert(0, str(p))
import harness_freq as HF                      # noqa: E402
from scipy import signal                       # noqa: E402

OUT = KIT / "analysis-2020accord/_scratch/out/release"; OUT.mkdir(parents=True, exist_ok=True)
FIG = KIT / "analysis-2020accord/figures/release"; FIG.mkdir(parents=True, exist_ok=True)
TS = 1e-3
F = np.unique(np.concatenate([np.logspace(-1, math.log10(60.0), 420),
                              [0.3, 1.0, 5.0, 7.0, 13.0, 15.0, 17.0, 20.0, 24.0, 30.0]]))

# ---------------------------------------------------------------- image reads (EVIDENCE: LE bytes, both images)
FWR = Path(os.environ["ACCORD_FIRMWARE_ROOT"]) / "analysis-2020accord"
STOCK = (FWR / "stock_fw_dump/code.bin").read_bytes()
V299 = Path(glob.glob(str(FWR / "_v299_*plain_image.bin"))[0]).read_bytes()


def h(b, a): return struct.unpack_from("<h", b, a)[0]


def H(b, a): return struct.unpack_from("<H", b, a)[0]


assert H(STOCK, 0xC6446) == 512 and H(V299, 0xC6446) == 2048 and STOCK[0x3AA96] == 0xC5 and V299[0x3AA96] == 0xFB
R24_REC = (0xD7A88, 0xD7AC4, 0xD7B00, 0xD7B3C)                     # mode-26 r24 records, 0/10/50/100 km/h
R24_PLATEAU_STOCK = [h(STOCK, a + 0xA) for a in R24_REC]          # Y0 (count@+0, X[4]@+2, Y[4]@+0xA)
assert R24_PLATEAU_STOCK == [3072, 2560, 2303, 2150], R24_PLATEAU_STOCK
assert [h(V299, a + 0xA) for a in R24_REC] == R24_PLATEAU_STOCK    # plateau untouched by V268 (only Y2/Y3 flattened)
R24_SPEED_KMH = [0, 10, 50, 100]                                  # 0xC6010 = 0,640,3200,6400 (64 ct/km/h)
assert [H(STOCK, 0xC6010 + 2 * i) for i in range(4)] == [0, 640, 3200, 6400]
DA_X = [h(STOCK, 0xD7A56 + 2 * i) for i in range(3)]
DA_Y_S = [h(STOCK, 0xD7A5C + 2 * i) for i in range(3)]
DA_Y_V = [h(V299, 0xD7A5C + 2 * i) for i in range(3)]
assert DA_X == [0, 1280, 5760] and DA_Y_S == [-9830, -5734, -1966] and DA_Y_V == [-29490, -17202, -16000]
K0 = STOCK[0xC643C]; K2_S, K2_V = STOCK[0xC40DC], V299[0xC40DC]
assert (K0, K2_S, K2_V) == (37, 22, 14) and V299[0xC643C] == 37
GBP = [(H(V299, 0xC4CDA + 6 * i), H(V299, 0xC4CDA + 6 * i + 2)) for i in range(6)]   # (X speed counts, G Q8)
assert GBP[0] == (714, 1178) and GBP[-1] == (6198, 2188), GBP
KP = h(V299, 0xE5378 + 12); KD = h(V299, 0xE511C + 10); KI = H(V299, 0xC63E6)
assert (KP, KD, KI) == (112, 48, 40), (KP, KD, KI)
assert H(V299, 0xC63E8) == 0 and H(V299, 0xC63EA) == 8192


def G_of_v(v_ms):
    x = v_ms * 3.6 * 64.0
    return float(np.interp(x, [k[0] for k in GBP], [k[1] for k in GBP]))


def r24_gain_stock(v_ms):
    return float(np.interp(v_ms * 3.6, R24_SPEED_KMH, R24_PLATEAU_STOCK)) / 1024.0


def da_Y(v_ms, which):
    return float(np.interp(v_ms * 3.6 * 64.0, DA_X, DA_Y_S if which == "stock" else DA_Y_V))


# ---------------------------------------------------------------- H_tb from route 79 (hands-off, engaged)
def measure_htb():
    cache = OUT / "htb_r79.npz"
    if cache.exists():
        z = np.load(cache)
        return z["f"], z["Hre"] + 1j * z["Him"], z["coh"], float(z["nwin"]), float(z["sec"])
    z = np.load(KIT / "analysis-2020accord/_scratch/cache/v280/r79_a1f5d2_al.npz")
    t0 = max(z["t18"][0], z["t14"][0], z["te4"][0], z["tcs"][0])
    t1 = min(z["t18"][-1], z["t14"][-1], z["te4"][-1], z["tcs"][-1])
    t = np.arange(t0, t1, 0.01)
    tq = np.interp(t, z["t18"], z["tq"]) / 1.024          # wire = raw x 1.024 (record) -> raw torque-sensor counts
    ang = np.interp(t, z["t14"], z["ang"])
    req = np.interp(t, z["te4"], z["req"]) > 0.5
    press = np.interp(t, z["tcs"], z["cs_press"].astype(float)) > 0.5
    ok = req & ~press & (np.abs(tq) < 400)
    edges = np.flatnonzero(np.diff(np.r_[0, ok.astype(int), 0]))
    segs = [(a, b) for a, b in zip(edges[::2], edges[1::2]) if b - a >= 600]       # >= 6 s windows
    nper = 256; fs = 100.0
    Pxx = Pxy = Pyy = 0; n = 0
    for a, b in segs:
        x = signal.detrend(ang[a:b]); y = signal.detrend(tq[a:b])
        f, pxx = signal.welch(x, fs, nperseg=nper); _, pyy = signal.welch(y, fs, nperseg=nper)
        _, pxy = signal.csd(x, y, fs, nperseg=nper)
        w = (b - a); Pxx = Pxx + pxx * w; Pyy = Pyy + pyy * w; Pxy = Pxy + pxy * w; n += w
    Hm = Pxy / Pxx; coh = np.abs(Pxy) ** 2 / (Pxx * Pyy)
    np.savez(cache, f=f, Hre=Hm.real, Him=Hm.imag, coh=coh, nwin=len(segs), sec=n / 100.0)
    return f, Hm, coh, len(segs), n / 100.0


def fit_two_mass(fm, Hm, coh):
    """H_tb ~ Jw * s^2 * w2^2/(s^2 + 2 z w2 s + w2^2): twist = rim inertia x rim accel, rim follows the motor below f2."""
    sel = (fm >= 0.5) & (fm <= 30) & (coh >= 0.25)
    w = 2 * np.pi * fm[sel]; y = Hm[sel]
    best = None
    for f2 in np.linspace(8, 45, 75):
        w2 = 2 * np.pi * f2
        for zeta in (0.03, 0.06, 0.1, 0.2):
            basis = (-(w ** 2)) * (w2 ** 2) / (w2 ** 2 - w ** 2 + 2j * zeta * w2 * w)
            Jw = np.vdot(basis, y).real / np.vdot(basis, basis).real
            err = float(np.sum(np.abs(y - Jw * basis) ** 2))
            if best is None or err < best[0]:
                best = (err, float(f2), zeta, float(Jw))
    return best


def htb_model(f, fit):
    _, f2, zeta, Jw = fit
    w = 2 * np.pi * np.asarray(f, float); w2 = 2 * np.pi * f2
    return Jw * (-(w ** 2)) * (w2 ** 2) / (w2 ** 2 - w ** 2 + 2j * zeta * w2 * w)


# ---------------------------------------------------------------- the lane transfers (T counts per deg of theta)
def zi(f): return np.exp(-2j * np.pi * np.asarray(f, float) * TS)


def ema(f, alpha):
    z = zi(f); return alpha / (1 - (1 - alpha) * z)


KAPPA_M = 1.155 * 4.7121        # motor-rate counts per deg/s of gp-0x6a00 (BELIEF: 4.7121 ct/(deg/s) motor frame x1.155)
DA_SCALE = 0x111 / 2.0 ** 24    # ((g*Y)>>6)*0x111>>18


def F_dampaxis(f, v, which, sigma):
    """gp-0x6b26 per deg of theta: x = KAPPA_M * dtheta/dt, then the FUN_00041464 integer cascade and the FUN_00036c12 scale."""
    w = 2j * np.pi * np.asarray(f, float)
    K2 = K2_S if which == "stock" else K2_V
    chain = 1024.0 * ema(f, K0 / 128.0) * (1 - zi(f)) * 32.0 * ema(f, K2 / 64.0) / 512.0      # gp-0x6c2c per count of x
    return sigma * da_Y(v, which) * DA_SCALE * chain * KAPPA_M * w


def F_r24(f, v, G, sigma, Htb):
    """r24 per deg of theta: G * gp-0x4f62, gp-0x4f62 = 0.5*(T[n]-T[n-4]) raw torque-sensor counts (N = 4, 0xC6C42)."""
    return sigma * G * 0.5 * (1 - zi(f) ** 4) * Htb


def damping_part(Fd, f):
    """b_add = -Re(F / (j w)) in T per deg/s: F is torque ADDED on the motor side (same sense as u), a damper is F = -b*jw,
    so > 0 = the term opposes motion (adds damping), < 0 = anti-damping (pumps)."""
    return -(np.asarray(Fd) / (2j * np.pi * np.asarray(f, float))).real


# ---------------------------------------------------------------- controller = C3-rev2-P / V299 at speed v
def ctl_v299(v):
    G = G_of_v(v)
    return HF.Ctl("V299", op="angle", hold="hold", a=0, b=8192, fb_op="sum",
                  kp=KP * G / 256.0, ki=KI * G / 256.0, kd=KD, d_src="none")   # the fresh D is added in C_fb_v299


def C_fb_v299(f, c, kappa_d=1.0):
    """harness C_fb plus the FRESH motor-frame D (gp-0x6abe = EMA 37/128 of the motor rate; KAPPA_M counts per deg/s)."""
    w = 2j * np.pi * np.asarray(f, float)
    s = HF.PI_(f, c) * HF.R_fb(f, c) * HF.OP(f, c) + c.kd / 8.0 * kappa_d * KAPPA_M * ema(f, 37 / 128.0) * w
    return HF.FADE * HF.H_out(f, c.oa, c.ob) * HF.FWD * zi(f) ** c.d * s


def loop_metrics(c, P, f=F):
    L = C_fb_v299(f, c) * P
    mag = np.abs(L); ph = np.unwrap(np.angle(L))
    idx = np.where((mag[:-1] >= 1.0) & (mag[1:] < 1.0))[0]
    fc = pm = float("nan")
    if len(idx):
        i = idx[0]; t = (0 - math.log(mag[i])) / (math.log(mag[i + 1]) - math.log(mag[i]))
        fc = math.exp(math.log(f[i]) + t * (math.log(f[i + 1]) - math.log(f[i])))
        phc = ph[i] + t * (ph[i + 1] - ph[i])
        pm = 180.0 - abs((math.degrees(phc) + 180.0) % 360.0 - 180.0)
    im = L.imag
    jx = np.where((np.sign(im[:-1]) != np.sign(im[1:])) & (L.real[:-1] < 0))[0]
    Lneg = [abs(L[j]) for j in jx]
    below = [x for x in Lneg if x < 1.0]
    gm_up = 20 * math.log10(1.0 / max(below)) if below else float("inf")
    S = 1 / (1 + L); T = L * S

    def band(lo, hi): return (f >= lo) & (f <= hi)
    iT = int(np.argmax(np.where(band(5, 30), np.abs(T), 0)))
    return dict(fc=fc, pm=pm, gm_db=gm_up, fTpk=float(f[iT]), L20=float(mag[np.argmin(abs(f - 20))]), L1317=float(mag[band(13, 17)].max()),
                T530_db=20 * math.log10(float(np.abs(T[band(5, 30)]).max())), Ms=float(np.abs(S).max()),
                S530_db=20 * math.log10(float(np.abs(S[band(5, 30)]).max())),
                encircle=bool(any(x >= 1.0 for x in Lneg)))


def main():
    t0 = time.time()
    fm, Hm, coh, nwin, sec = measure_htb()
    fit = fit_two_mass(fm, Hm, coh)
    Htb = htb_model(F, fit)
    f7, f20, f24 = np.array([7.0]), np.array([20.0]), np.array([24.0])
    # anchors (record): r24 PUMPS (anti-damps) at 7 Hz; the DampAxis x3 (V106) DAMPED 21-27 Hz
    sig_r = -1.0 if damping_part(F_r24(f7, 3.0, 1.0, +1.0, htb_model(f7, fit)), f7)[0] > 0 else +1.0
    sig_d = +1.0 if damping_part(F_dampaxis(f24, 3.0, "stock", +1.0), f24)[0] > 0 else -1.0
    chk = {
        "r24_damp_7Hz_per_unit_G": float(damping_part(F_r24(f7, 3.0, 1.0, sig_r, htb_model(f7, fit)), f7)[0]),
        "r24_damp_20Hz_per_unit_G": float(damping_part(F_r24(f20, 3.0, 1.0, sig_r, htb_model(f20, fit)), f20)[0]),
        "da_stock_damp_7Hz": float(damping_part(F_dampaxis(f7, 3.0, "stock", sig_d), f7)[0]),
        "da_stock_damp_24Hz": float(damping_part(F_dampaxis(f24, 3.0, "stock", sig_d), f24)[0]),
        "da_v299_damp_24Hz": float(damping_part(F_dampaxis(f24, 3.0, "v299", sig_d), f24)[0]),
        "da_v299_J_add_T_per_deg_s2_3ms_(>0 adds inertia)": float(-(F_dampaxis(np.array([0.5]), 3.0, "v299", sig_d)[0] / (-(2 * np.pi * 0.5) ** 2)).real),
        "da_stock_J_add_T_per_deg_s2_3ms": float(-(F_dampaxis(np.array([0.5]), 3.0, "stock", sig_d)[0] / (-(2 * np.pi * 0.5) ** 2)).real),
        "r24_dG1_J_add_3ms": float(-(F_r24(np.array([0.5]), 3.0, 1.0, sig_r, htb_model(np.array([0.5]), fit))[0] / (-(2 * np.pi * 0.5) ** 2)).real),
        "da_stock_inertia_eq_T_per_deg_s2_3ms": float(abs(F_dampaxis(np.array([0.5]), 3.0, "stock", sig_d)[0]) / (2 * np.pi * 0.5) ** 2),
        "da_v299_inertia_eq_T_per_deg_s2_3ms": float(abs(F_dampaxis(np.array([0.5]), 3.0, "v299", sig_d)[0]) / (2 * np.pi * 0.5) ** 2),
    }
    members = [m for m in ("nominal", "J_lo", "J_hi", "J_hi2", "b_lo", "b_hi", "tau0", "tau6", "ms_free") if m in HF.FAM]
    tierA = {"nominal", "J_lo", "J_hi", "b_hi", "tau0", "tau6"}
    rows = []; bode = {}
    for v in HF.SPEEDS:
        c = ctl_v299(v)
        dG = r24_gain_stock(v) - 2.0
        Fd_da = F_dampaxis(F, v, "stock", sig_d) - F_dampaxis(F, v, "v299", sig_d)
        Fd_r24 = F_r24(F, v, dG, sig_r, Htb)
        Fd = Fd_da + Fd_r24
        for m in members:
            p = HF.plant_at(m, v)
            P = p.frf(F)
            variants = {"V299plant": P, "stock_terms": P / (1 - P * Fd), "only_r24": P / (1 - P * Fd_r24),
                        "only_dampaxis": P / (1 - P * Fd_da)}
            r = {k: loop_metrics(c, Pk) for k, Pk in variants.items()}
            r295 = HF.metrics(HF.V295, p, exact=False, f=F)
            row = dict(v=v, member=m, tier="A" if m in tierA else ("MSF" if m == "ms_free" else "B"), dG_r24=dG,
                       J=p.J, b=p.b, k=p.k, Y_da_stock=da_Y(v, "stock"), Y_da_v299=da_Y(v, "v299"), L20_v295=r295["L20"])
            for k, rr in r.items():
                for kk, vv in rr.items():
                    row[f"{k}_{kk}"] = vv
            rows.append(row)
            if m == "nominal" and v in (3.0, 12.5, 26.0):
                bode[v] = {k: (np.abs(C_fb_v299(F, c) * Pk), np.degrees(np.unwrap(np.angle(C_fb_v299(F, c) * Pk))))
                           for k, Pk in variants.items()}
    # ---- extra boxes: aged hold (ages 11-20), curve operating point (k * sech^2(theta_op/sat)), ms_free x b_lo, sign flips
    import v294_plant as VP
    extra = []
    for v in HF.SPEEDS:
        c = ctl_v299(v); dG = r24_gain_stock(v) - 2.0
        Fd = (F_dampaxis(F, v, "stock", sig_d) - F_dampaxis(F, v, "v299", sig_d)) + F_r24(F, v, dG, sig_r, Htb)
        th_op = math.degrees(math.atan(2.5 * 2.83 / max(v, 1.0) ** 2)) * 16.84          # 2.5 m/s^2 curve, SR 16.84 (BELIEF)
        sech2 = 1.0 / math.cosh(th_op / float(VP.sat_prior(v))) ** 2
        cases = []
        for m in ("nominal", "J_lo", "b_lo", "ms_free"):
            p0 = HF.plant_at(m, v)
            cases.append((f"{m} aged11-20", p0, HF.Ctl(**{**c.__dict__, "hold": "hold"}), range(11, 21)))
            cases.append((f"{m} curve k*{sech2:.2f}", HF.Plant(J=p0.J, b=p0.b, k=p0.k * sech2, tau=p0.tau, name=m), c, None))
        pm = HF.plant_at("ms_free", v)
        cases.append(("ms_free x b_lo", HF.Plant(J=pm.J, b=pm.b / (1.8 if v >= 10 else 1 / 0.7), k=pm.k, tau=pm.tau), c, None))
        for name, p, cc, ages in cases:
            if ages is not None:
                cc = HF.Ctl(**{**cc.__dict__, "hold": "hold"}); cc.__class__.ages.fget  # noqa
                ccA = cc; ages_obj = ages
                class _C(HF.Ctl):  # ages override
                    @property
                    def ages(self): return ages_obj
                cc = _C(**{k: getattr(ccA, k) for k in ccA.__dataclass_fields__})
            P = p.frf(F)
            r0 = loop_metrics(cc, P); r1 = loop_metrics(cc, P / (1 - P * Fd))
            extra.append(dict(v=v, case=name, pm0=r0["pm"], pm1=r1["pm"], L20_0=r0["L20"], L20_1=r1["L20"], T0=r0["T530_db"], T1=r1["T530_db"], enc=r1["encircle"]))
    signs = []
    for sr in (+1.0, -1.0):
        for sd in (+1.0, -1.0):
            worst = []
            for v in HF.SPEEDS:
                c = ctl_v299(v); dG = r24_gain_stock(v) - 2.0
                Fd = (F_dampaxis(F, v, "stock", sd) - F_dampaxis(F, v, "v299", sd)) + F_r24(F, v, dG, sr, Htb)
                for m in ("nominal", "J_lo", "b_lo", "ms_free"):
                    P = HF.plant_at(m, v).frf(F)
                    r0 = loop_metrics(c, P); r1 = loop_metrics(c, P / (1 - P * Fd))
                    worst.append((r1["pm"] - r0["pm"], r1["pm"], r1["L20"] / max(r0["L20"], 1e-9), r1["T530_db"], r1["encircle"], v, m))
            wT = max(worst, key=lambda w: w[3])
            signs.append(dict(sig_r=sr, sig_d=sd, anchored=(sr == sig_r and sd == sig_d), min_dpm=min(w[0] for w in worst), min_pm=min(w[1] for w in worst),
                              max_L20_ratio=max(w[2] for w in worst), max_T530=max(w[3] for w in worst), encircle=any(w[4] for w in worst),
                              at_min_dpm=min(worst)[5:], at_max_T=wT[5:]))
    json.dump(dict(fit=dict(err=fit[0], f2=fit[1], zeta=fit[2], Jw=fit[3]), nwin=nwin, sec=sec, sig_r=sig_r, sig_d=sig_d,
                   chk=chk, rows=rows, extra=extra, signs=signs), open(OUT / "gate2_rescore.json", "w"), indent=1, default=float)
    # ---------------- report
    L = []
    L.append(f"H_tb(r79): {nwin:.0f} hands-off engaged windows, {sec:.0f} s; two-mass fit f2 {fit[1]:.1f} Hz zeta {fit[2]} "
             f"Jw {fit[3]:.4f} raw counts per deg/s^2 (sign incl.), LS err {fit[0]:.3g}")
    L.append(f"sign anchors: sigma_r {sig_r:+.0f} (r24 anti-damps at 7 Hz), sigma_d {sig_d:+.0f} (DampAxis damps at 24 Hz)")
    L.append("checks: " + json.dumps({k: round(v, 5) for k, v in chk.items()}))
    L.append("")
    L.append("| v m/s | member | tier | J | PM V299-plant | PM stock-terms | dPM | PM only r24 | PM only DampAxis | GM up dB V299/stock | "
             "L20 V299/stock | L13-17 V299/stock | T5-30 dB V299/stock (f_pk) | T5-30 only r24 / only DampAxis | Ms V299/stock |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        L.append(f"| {r['v']:g} | {r['member']} | {r['tier']} | {r['J']:.2f} | {r['V299plant_pm']:.1f} | {r['stock_terms_pm']:.1f} | "
                 f"{r['stock_terms_pm'] - r['V299plant_pm']:+.1f} | {r['only_r24_pm']:.1f} | {r['only_dampaxis_pm']:.1f} | "
                 f"{r['V299plant_gm_db']:.1f}/{r['stock_terms_gm_db']:.1f} | {r['V299plant_L20']:.3f}/{r['stock_terms_L20']:.3f} | "
                 f"{r['V299plant_L1317']:.3f}/{r['stock_terms_L1317']:.3f} | {r['V299plant_T530_db']:+.1f}/{r['stock_terms_T530_db']:+.1f} | "
                 f"{r['V299plant_Ms']:.2f}/{r['stock_terms_Ms']:.2f} |")
    L.append("")
    for tier, bar in (("A", 45.0), ("B", 30.0), ("MSF", 30.0)):
        rs = [r for r in rows if r["tier"] == tier]
        if not rs:
            continue
        L.append(f"tier {tier}: min PM {min(r['V299plant_pm'] for r in rs):.1f} -> {min(r['stock_terms_pm'] for r in rs):.1f} (bar {bar:.0f}); "
                 f"points below bar {sum(r['V299plant_pm'] < bar for r in rs)} -> {sum(r['stock_terms_pm'] < bar for r in rs)} of {len(rs)}; "
                 f"max L20 {max(r['V299plant_L20'] for r in rs):.3f} -> {max(r['stock_terms_L20'] for r in rs):.3f}; "
                 f"max T5-30 {max(r['V299plant_T530_db'] for r in rs):+.1f} -> {max(r['stock_terms_T530_db'] for r in rs):+.1f} dB (only r24 {max(r['only_r24_T530_db'] for r in rs):+.1f}, only DampAxis {max(r['only_dampaxis_T530_db'] for r in rs):+.1f}); "
                 f"GM<6 dB points {sum(r['V299plant_gm_db'] < 6 for r in rs)} -> {sum(r['stock_terms_gm_db'] < 6 for r in rs)}; "
                 f"encirclements {sum(r['V299plant_encircle'] for r in rs)} -> {sum(r['stock_terms_encircle'] for r in rs)}")
    L.append("L20 / V295's L20 (nominal, stock terms): " + ", ".join(f"{r['v']:g} m/s {r['stock_terms_L20'] / r['L20_v295']:.2f}x"
                                                                     for r in rows if r["member"] == "nominal"))
    txt = "\n".join(L); print(txt); (OUT / "gate2_rescore.md").write_text(txt, encoding="utf-8")
    # ---------------- figures
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt   # noqa: E702
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    sel = coh > 0.25
    ax[0].loglog(fm[sel], np.abs(Hm[sel]), ".", label="measured r79 (coh>0.25)"); ax[0].loglog(F, np.abs(Htb), label="two-mass fit")
    ax[0].set_xlabel("Hz"); ax[0].set_ylabel("|T_tb/theta| raw counts/deg"); ax[0].legend(); ax[0].set_title("hands-off torsion-bar twist per deg (route 79)")
    ax[1].semilogx(fm[sel], np.degrees(np.angle(Hm[sel])), "."); ax[1].semilogx(F, np.degrees(np.angle(Htb)))
    ax[1].set_ylabel("phase deg"); ax[1].set_xlabel("Hz")
    fig.tight_layout(); fig.savefig(FIG / "htb_r79.png", dpi=110); plt.close(fig)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for v in (3.0, 8.0, 12.5, 19.0, 26.0):
        dG = r24_gain_stock(v) - 2.0
        ax[0].semilogx(F, damping_part(F_r24(F, v, dG, sig_r, Htb), F), label=f"r24 delta {v:g} m/s (dG {dG:+.2f})")
        ax[1].semilogx(F, damping_part(F_dampaxis(F, v, "stock", sig_d) - F_dampaxis(F, v, "v299", sig_d), F), label=f"DampAxis delta {v:g} m/s")
    for a in ax:
        a.axhline(0, color="k", lw=0.5); a.set_xlabel("Hz"); a.set_ylabel("Re(dF/jw)  T per deg/s  (>0 adds damping)"); a.legend(fontsize=7)
    ax[0].set_title("r24: stock - V299, damping part"); ax[1].set_title("DampAxis: stock - V299, damping part")
    fig.tight_layout(); fig.savefig(FIG / "delta_terms_damping.png", dpi=110); plt.close(fig)
    fig, axs = plt.subplots(2, 3, figsize=(14, 7), sharex=True)
    for j, v in enumerate((3.0, 12.5, 26.0)):
        for k, (mag, ph) in bode[v].items():
            axs[0, j].loglog(F, mag, label=k); axs[1, j].semilogx(F, ph, label=k)
        axs[0, j].axhline(1, color="k", lw=0.5); axs[0, j].set_title(f"L, nominal member, {v:g} m/s"); axs[1, j].axhline(-180, color="k", lw=0.5)
        axs[1, j].set_xlabel("Hz")
    axs[0, 0].set_ylabel("|L|"); axs[1, 0].set_ylabel("deg"); axs[0, 0].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "bode_L_v299_vs_stock_terms.png", dpi=110); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4))
    for m in members:
        rs = [r for r in rows if r["member"] == m]
        ax.plot([r["v"] for r in rs], [r["V299plant_pm"] for r in rs], "o--", ms=3, alpha=0.5)
        ax.plot([r["v"] for r in rs], [r["stock_terms_pm"] for r in rs], "s-", ms=3, label=m)
    ax.axhline(45, color="k", lw=0.5); ax.axhline(30, color="r", lw=0.5); ax.set_xlabel("m/s")
    ax.set_ylabel("PM deg (dashed: V299 plant, solid: stock terms)"); ax.legend(fontsize=7, ncol=3)
    fig.tight_layout(); fig.savefig(FIG / "pm_vs_speed.png", dpi=110); plt.close(fig)
    print(f"\nwall {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
