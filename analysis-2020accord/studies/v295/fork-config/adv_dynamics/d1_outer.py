# -*- coding: utf-8 -*-
"""d1_outer -- ADV-dynamics (a) + (b-linear): the OUTER loop, re-derived independently.

Two methods for the EPS (wire count -> wheel angle) transfer:
  M1  the harness's analytic linearisation  G1 = plant_theta_frf/(1+loop_frf) * ff_tf * zoh100  (what the designer used)
  M2  TIME-DOMAIN identification: a periodic multisine 0xE4 command through the BYTE-EXACT integer H.Lane into the
      harness PlantBatch stepper with friction removed (linear member), theta sampled at the fork's 100 Hz frame instants.
The FORK side is MINE, from the source (latcontrol_torque.py @20d24ab79 + common/pid.py + opendbc lateral.get_friction):
      e_lsf = (sp - meas) * (1 + lsf/Kp) ;  P = Kp e_lsf ;  i[n] = i[n-1] + Ki(v) * 0.01 * e_lsf[n]  (pid.py line 53)
      fr = interp(e_lsf, [-0.30, 0.30], [-F*LAF, F*LAF])  -> small-signal slope F*LAF/0.30 (a SATURATION: DF <= slope)
      torque = (P + i + fr + ff) / LAF ;  wire = -4096 * torque ;  meas = kla(v) * theta  (VM.calc_curvature, the fork's VM)
      Ki(v) = interp(v, [8, 18], [Ki, KiHigh]) if KiHigh > 0 else Ki   (get_honda_accord_torque_ki)
Margins by my own code (all |L| = 1 crossings, all -180 deg crossings, Ms = max |1/(1+L)|).
ANALYSIS ONLY.
"""
import os, sys, json, time
from dataclasses import replace
import numpy as np
HARN = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness"
sys.path.insert(0, HARN)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import v295_harness as H
import fork_real as FK

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
V295_IMG = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR."
            "SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
CELLS = {"V294": H.Cells.v294(), "V295": H.Cells.from_image(V295_IMG, "V295",
                                                              "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed")}
FORKS = {"r1": dict(kp=0.9, ki=0.3, kih=0.0, laf=14.0, F=0.011),
         "r2alt": dict(kp=0.9, ki=0.3, kih=0.8, laf=14.0, F=0.011)}
CONFIGS = [("V294+r1", "V294", "r1"), ("V295+r1", "V295", "r1"), ("V295+r2alt", "V295", "r2alt")]
MEMBERS = ["nominal", "b_lo", "b_hi", "J_lo", "J_hi", "tau0", "tau6", "light_b"]   # F_lo/F_hi == nominal when linear
SPEEDS = [3.1, 4.0, 5.0, 8.0, 12.0, 17.0, 19.0, 22.0, 26.9]
PIPES = [22, 42, 62]

FK.setup()
from opendbc.car.vehicle_model import VehicleModel
_VM = VehicleModel(FK.make_CP())
_VM.update_params(1.0, 16.84)          # Accord SR map at angle 0 (16.88) x the level 16.84/16.88  (fork_real / controlsd)


def kla(v):
    """d(meas)/d(theta) in m/s^2 per deg at theta ~ 0 (the fork's own VehicleModel)."""
    return abs(float(_VM.calc_curvature(np.radians(1.0), v, 0.0))) * v * v


def lsf(v):
    return (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 0.001)) ** 2   # MIN_SPEED 0.001? checked below


def ki_at(fk, v):
    return fk["ki"] if fk["kih"] <= 0 else float(np.interp(v, [8.0, 18.0], [fk["ki"], fk["kih"]]))


def C_fork(fk, v, f, relay_mult=1.0):
    """torque (openpilot units) per m/s^2 of error, discrete 100 Hz (backward-rectangle integrator as pid.py)."""
    z = np.exp(2j * np.pi * f * 0.01)
    kp, laf, F = fk["kp"], float(np.float32(fk["laf"])), float(np.float32(fk["F"]))
    g = 1.0 + lsf(v) / max(kp, 1e-3)
    return g * (kp + ki_at(fk, v) * 0.01 / (1 - 1 / z) + relay_mult * F * laf / 0.30) / laf


def G1_eps(c, p, f):
    """harness analytic: wire count -> theta (deg), incl. the 100 Hz ZOH (continuous approx)."""
    Lin = H.loop_frf(c, p, f)
    Pcl = H.plant_theta_frf(p, f) / (1 + Lin)
    zoh100 = np.exp(-1j * np.pi * f * 0.01) * np.sinc(f * 0.01)
    return Pcl * H.ff_tf(c, f, 60) * zoh100


def margins(f, L):
    mag = np.abs(L)
    S = 1.0 / (1.0 + L)
    out = dict(Ms=float(np.max(np.abs(S))), f_Ms=float(f[int(np.argmax(np.abs(S)))]))
    xc = np.flatnonzero(np.diff(np.sign(mag - 1.0)) != 0)
    pms = []
    for i in xc:   # interpolate the crossing
        t = (1.0 - mag[i]) / (mag[i + 1] - mag[i])
        Lx = L[i] + t * (L[i + 1] - L[i])
        pms.append((float(f[i] + t * (f[i + 1] - f[i])), float(180.0 + np.degrees(np.angle(Lx)))))
    out["xover"] = [a for a, _ in pms]
    out["PM"] = min([b for _, b in pms], default=float("inf"))
    # phase crossings of -180 (Im L changes sign with Re L < 0)
    im = np.imag(L)
    pc = np.flatnonzero(np.diff(np.sign(im)) != 0)
    gms = []
    for i in pc:
        t = -im[i] / (im[i + 1] - im[i])
        Lx = L[i] + t * (L[i + 1] - L[i])
        if np.real(Lx) < 0:
            gms.append((float(f[i] + t * (f[i + 1] - f[i])), float(1.0 / abs(Lx))))
    out["GM"] = min([g for _, g in gms], default=float("inf"))
    out["f_GM"] = min(gms, key=lambda t: t[1])[0] if gms else float("nan")
    return out


# ---------------------------------------------------------------- M2: time-domain identification of the EPS
def identify(members, speeds, cells_names, amp=150.0, T0=40.0, periods=2, settle=10.0, seed=1):
    fam = H.family(include_stress=False)
    combos = [(cn, m, v) for cn in cells_names for m in members for v in speeds]
    B = len(combos)
    mem = []
    for _, m, _ in combos:
        mm = fam[m]
        mem.append(replace(mm, Fc=np.zeros_like(mm.Fc), Fs=np.zeros_like(mm.Fs), use_sat=False))
    lane = H.Lane([CELLS[cn] for cn, _, _ in combos])
    plant = H.PlantBatch(mem, np.zeros(B), np.zeros(B), x_noise=0.0)
    plant.set_speed(np.array([v for _, _, v in combos]))
    rng = np.random.default_rng(seed)
    nidx = np.unique(np.round(np.logspace(np.log10(2), np.log10(480), 45)).astype(int))   # x 1/T0 Hz: 0.05 .. 12 Hz
    fex = nidx / T0
    ph = rng.uniform(0, 2 * np.pi, len(nidx))
    NF = int((settle + periods * T0) * 100)
    k = np.arange(NF)
    u = np.sum(np.sin(2 * np.pi * fex[:, None] * k[None, :] * 0.01 + ph[:, None]), axis=0)
    u = amp * u / np.std(u)
    th = np.zeros((B, NF))
    r26max = np.zeros(B)
    Tmax = np.zeros(B)
    for kk in range(NF):
        th[:, kk] = plant.wheel_angle()
        idx, sp, mm = lane.demand(np.full(B, np.round(u[kk])))
        for t_ in range(10):
            x = plant.sense()
            T, r26 = lane.tick(-x, sp, idx, mm)
            r26max = np.maximum(r26max, np.abs(r26))
            Tmax = np.maximum(Tmax, np.abs(T))
            plant.step(T.astype(float))
    s0 = int(settle * 100)
    U = np.fft.rfft(np.round(u[s0:]))
    TH = np.fft.rfft(th[:, s0:], axis=1)
    bins = nidx * periods
    G2 = TH[:, bins] / U[bins]
    return combos, fex, G2, r26max, Tmax


def main():
    t0 = time.time()
    fam = H.family(include_stress=False)
    lines = []
    P = lambda s: (print(s), lines.append(s))  # noqa: E731
    # MIN_SPEED check (the lsf denominator)
    from openpilot.selfdrive.controls.lib import latcontrol_torque as LT
    P("MIN_SPEED (drive_helpers) = %r ; LOW_SPEED_X/Y = %r / %r ; friction threshold 0.30 asserted by the harness port"
      % (LT.MIN_SPEED, LT.LOW_SPEED_X, LT.LOW_SPEED_Y))
    for v in SPEEDS:
        P("  v %5.1f  kla %.4f m/s^2/deg   lsf %.3f   (1+lsf/Kp) %.3f   harness kla %.4f" % (
            v, kla(v), lsf(v), 1 + lsf(v) / 0.9,
            (1 - H._vm_consts()["chi"]) / (1 - H._vm_consts()["sf"] * v * v) / H._vm_consts()["l"] / 16.84 * v * v * np.pi / 180))
    # ---- M2 identification vs M1
    P("\n== M1 (harness analytic) vs M2 (time-domain, integer lane + plant stepper, friction off): wire -> theta ==")
    combos, fex, G2, r26max, Tmax = identify(MEMBERS, [3.1, 8.0, 12.0, 17.0, 22.0, 26.9], ["V294", "V295"])
    P("  max |r26| over the run %.0f (clamp 1024), max |T| %.0f (rail 2461)" % (r26max.max(), Tmax.max()))
    worst = []
    sgn0 = np.sign(np.real(G2[0][0] / G1_eps(CELLS[combos[0][0]], fam[combos[0][1]].at(combos[0][2]), fex[:1])[0]))
    for j, (cn, m, v) in enumerate(combos):
        g1 = sgn0 * G1_eps(CELLS[cn], fam[m].at(v), fex)   # the two conventions differ by an overall sign only
        sel = fex <= 8.0
        rel = np.abs(G2[j] - g1) / np.abs(g1)
        worst.append(rel[sel].max())
        if m in ("nominal", "light_b") and v in (3.1, 22.0, 26.9):
            P("  %s %-8s v%5.1f  DC-ish |G| M1 %.4f M2 %.4f  | max rel err 0.05-8 Hz %.3f (at %.2f Hz); phase diff at 2.3 Hz %.1f deg"
              % (cn, m, v, abs(g1[0]), abs(G2[j][0]), rel[sel].max(), fex[sel][np.argmax(rel[sel])],
                 np.degrees(np.angle(G2[j][np.argmin(abs(fex - 2.3))] / g1[np.argmin(abs(fex - 2.3))]))))
    P("  ALL %d rows: worst max rel err (0.05-8 Hz) %.3f ; median %.3f" % (len(combos), max(worst), float(np.median(worst))))
    sign = np.sign(np.real(G2[0][0] / G1_eps(CELLS[combos[0][0]], fam[combos[0][1]].at(combos[0][2]), fex[:1])[0]))
    P("  M2/M1 sign at DC: %+d" % sign)
    # ---- margins
    FG = np.logspace(-3, np.log10(25.0), 6000)
    res = {}
    P("\n== OUTER margins, my fork linearisation x M1 EPS: Ms / GM / PM (deg), relay slope ON ==")
    for (cfg, cn, fn) in CONFIGS:
        for pipe in PIPES:
            for rm in (1.0, 0.0):
                for m in MEMBERS:
                    for v in SPEEDS:
                        p = fam[m].at(v)
                        G = G1_eps(CELLS[cn], p, FG)
                        L = kla(v) * G * np.exp(-2j * np.pi * FG * pipe * 1e-3) * 4096.0 * C_fork(FORKS[fn], v, FG, rm)
                        # sign: negative feedback <=> L -> +inf*(-j) at DC (integrator, phase -90)
                        if np.real(L[0] * 1j) < 0:
                            L = -L
                        res[(cfg, pipe, rm, m, v)] = margins(FG, L)
    # print the pipe-22 relay-on tables in the designer's format
    for (cfg, _, _) in CONFIGS:
        P("\n%s  pipe 22 ms, relay ON" % cfg)
        for m in MEMBERS:
            P("   %-8s " % m + " ".join("%4.1f:%4.2f/%5.1f/%4.0f" % (v, res[(cfg, 22, 1.0, m, v)]["Ms"], res[(cfg, 22, 1.0, m, v)]["GM"],
                                                                 res[(cfg, 22, 1.0, m, v)]["PM"]) for v in SPEEDS))
    # identified-family worst per speed, per pipe, relay on/off
    P("\n== identified family (7 linear-distinct members) worst Ms / min GM / min PM per speed ==")
    idm = [m for m in MEMBERS if m != "light_b"]
    summ = {}
    for (cfg, _, _) in CONFIGS:
        for pipe in PIPES:
            for rm in (1.0, 0.0):
                row = []
                for v in SPEEDS:
                    Ms = max(res[(cfg, pipe, rm, m, v)]["Ms"] for m in idm)
                    GM = min(res[(cfg, pipe, rm, m, v)]["GM"] for m in idm)
                    PM = min(res[(cfg, pipe, rm, m, v)]["PM"] for m in idm)
                    row.append((Ms, GM, PM))
                    summ[(cfg, pipe, rm, v)] = (Ms, GM, PM)
                P("  %-11s pipe %2d relay %s: " % (cfg, pipe, "on " if rm else "off") +
                  " ".join("%4.1f:%4.2f/%4.1f/%3.0f" % (v, a, b, c) for v, (a, b, c) in zip(SPEEDS, row)))
    P("\n== light_b Ms / GM / PM ==")
    for (cfg, _, _) in CONFIGS:
        for pipe in PIPES:
            for rm in (1.0, 0.0):
                P("  %-11s pipe %2d relay %s: " % (cfg, pipe, "on " if rm else "off") +
                  " ".join("%4.1f:%4.2f/%4.2f/%3.0f(%.2fHz)" % (v, res[(cfg, pipe, rm, "light_b", v)]["Ms"],
                                                             res[(cfg, pipe, rm, "light_b", v)]["GM"],
                                                             res[(cfg, pipe, rm, "light_b", v)]["PM"],
                                                             res[(cfg, pipe, rm, "light_b", v)]["f_GM"]) for v in SPEEDS))
    # X2 / X3 checks
    P("\n== X2: r2alt identified family, any pipe / relay: Ms > 1.6 or GM < 3 or PM < 35 ? ==")
    bad = [(k, summ[k]) for k in summ if k[0] == "V295+r2alt" and (summ[k][0] > 1.6 or summ[k][1] < 3.0 or summ[k][2] < 35)]
    P("  hits: %d %s" % (len(bad), bad[:10]))
    P("== X3: r2alt light_b at 17/19/22/26.9 vs V294+r1 (flown) same pipe/relay: GM < 0.97x or Ms > 1.10x ? ==")
    for pipe in PIPES:
        for rm in (1.0, 0.0):
            for v in (17.0, 19.0, 22.0, 26.9):
                a = res[("V295+r2alt", pipe, rm, "light_b", v)]
                b = res[("V294+r1", pipe, rm, "light_b", v)]
                c = res[("V295+r1", pipe, rm, "light_b", v)]
                flag = (a["GM"] < 0.97 * b["GM"]) or (a["Ms"] > 1.10 * b["Ms"])
                P("  pipe %2d relay %s v %4.1f  V294+r1 %.2f/%.2f  V295+r1 %.2f/%.2f  r2alt %.2f/%.2f  (Ms/GM)  %s" % (
                    pipe, "on " if rm else "off", v, b["Ms"], b["GM"], c["Ms"], c["GM"], a["Ms"], a["GM"], "FAIL" if flag else "ok"))
    # ---- DF sweep of the relay (the saturation: N(A) in [0, slope]); find the first destabilising multiple
    P("\n== (b) relay DF: smallest relay multiple k (x flown slope) at which the linear loop loses stability (GM<=1 or PM<=0) ==")
    mults = [0, 0.5, 1, 1.5, 2, 3, 4, 5, 6, 8, 10, 13, 16, 20]
    dfres = {}
    for (cfg, cn, fn) in CONFIGS:
        firsts = []
        for m in MEMBERS:
            for v in SPEEDS:
                p = fam[m].at(v)
                G = G1_eps(CELLS[cn], p, FG) * kla(v) * np.exp(-2j * np.pi * FG * 0.022) * 4096.0
                first = None
                for km in mults:
                    L = G * C_fork(FORKS[fn], v, FG, km)
                    if np.real(L[0] * 1j) < 0:
                        L = -L
                    mg = margins(FG, L)
                    if mg["GM"] <= 1.0 or mg["PM"] <= 0:
                        first = km
                        break
                firsts.append((first if first is not None else 99, m, v))
                dfres[(cfg, m, v)] = first
        firsts.sort()
        P("  %-11s first destabilising multiples: %s" % (cfg, firsts[:6]))
    json.dump({"|".join(map(str, k)): v for k, v in res.items()}, open(os.path.join(OUT, "d1_outer.json"), "w"), indent=0)
    open(os.path.join(OUT, "d1_outer_out.txt"), "w").write("\n".join(lines) + "\n")
    print("runtime %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
