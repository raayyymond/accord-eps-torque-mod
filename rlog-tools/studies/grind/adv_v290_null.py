# -*- coding: utf-8 -*-
"""studies/grind/adv_v290_null.py -- ADVERSARIAL attack on the V290 NULL verdict.  Agent advnull, 2026-09-09.
Analysis only: builds nothing, flashes nothing, sends nothing.

INDEPENDENT of design290b_candidates.py: every electronic block, the notch integers and the Q14 rounding are
re-derived here from the V289 IMAGE bytes with my own struct reads; the closed-loop poles come from root-finding
1 + L(z) = 0 on my own polynomial assembly.  The plant family JSON is imported (the brief allows it) and
SPOT-VERIFIED by re-deriving f282/z282/f289/z289 per fit and comparing to the stored values.

THE TWO ATTACKS
  T1  TOPOLOGY.  design290b places every sum-filter on the loop OUTPUT S (forward path): it appears in BOTH the
      return ratio R and the reference transfer fwd().  The SAME filter on the FEEDBACK OPERAND gives an IDENTICAL
      R (hence identical poles, zeta, Ms, PM, gate73, stability) but drops out of fwd() -- so the capped-step pkR
      is restored.  The 92-row table contains NO feedback-path row.
  T2  METRIC.  pkR = max of the closed-loop step RATE response.  On V282 that maximum IS the 20 Hz overshoot.
"""
import json
import os
import struct
import sys
import glob

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
FW = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares") + "/analysis-2020accord/"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TS, FS, CPD = 1e-3, 1000.0, 8.0
STEP_SP = 33
LS73 = 0.55 * np.exp(1j * np.radians(96.0))
LR73 = 1.19 * np.exp(1j * np.radians(-27.0))   # adv_v290_physics constant; gate73(V282 vs V282) = 1.003
FG = np.arange(1.0, 200.0, 0.02)
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def read_cells():
    p = glob.glob(FW + "_v289_*_plain_image.bin")[0]
    b = open(p, "rb").read()
    u16 = lambda a: struct.unpack_from("<H", b, a)[0]
    s16 = lambda a: struct.unpack_from("<h", b, a)[0]
    u32 = lambda a: struct.unpack_from("<I", b, a)[0]
    c = dict(path=os.path.basename(p))
    c["fb_a"], c["fb_b"] = s16(0xC63E8), u16(0xC63EA)
    c["lag_a"], c["lag_b"] = s16(0xC63EC), u16(0xC63EE)
    c["gain"] = s16(0xBF000 + u16(0x2A1F0))
    kb = u32(0xCB994 + 4 * 7)
    c["kp_n"] = u16(kb)
    c["kp_X"] = [u16(kb + 2 + 2 * i) for i in range(5)]
    c["kp_Y"] = [u16(kb + 12 + 2 * i) for i in range(5)]
    db = u32(0xCB7D4 + 4 * 7)
    c["kd_n"] = u16(db)
    c["kd_X"] = [u16(db + 2 + 2 * i) for i in range(4)]
    c["kd_Y"] = [u16(db + 10 + 2 * i) for i in range(4)]
    c["kp_base"], c["kd_base"] = kb, db
    c["sum_clamp"], c["t_clamp"] = u16(0xC61BE), u16(0xC61B4)
    c["d_clamp"], c["p_clamp"] = u16(0xC61B6), u16(0xC61BC)
    c["fb_clamp"] = u16(0xC62E6)
    c["b0"], c["a2"], c["b1"] = s16(0xC4C10), s16(0xC4C28), s16(0xC4C3E)
    return c, b


def pmul(*ps):
    o = np.array([1.0])
    for p in ps:
        o = np.convolve(o, np.asarray(p, float))
    return o


def padd(a, b):
    n = max(len(a), len(b))
    o = np.zeros(n)
    o[:len(a)] += a
    o[:len(b)] += b
    return o


def pev(p, f):
    w = np.exp(-2j * np.pi * np.asarray(f, float) * TS)
    return sum(cc * w ** k for k, cc in enumerate(p))


def rbj_notch_q14(fc, Q):
    w0 = 2 * np.pi * fc / FS
    al = np.sin(w0) / (2 * Q)
    cw = np.cos(w0)
    a0 = 1 + al
    b = np.array([1.0, -2 * cw, 1.0]) / a0
    a = np.array([a0, -2 * cw, 1 - al]) / a0
    bi = np.round(b * 16384).astype(int)
    ai = np.round(a * 16384).astype(int)
    ai[0] = 16384
    return bi / 16384.0, ai / 16384.0, (bi.tolist(), ai.tolist())


def fb_pole_ints(f_hz, dc=30.891):
    a = int(round(1024 * np.exp(-2 * np.pi * f_hz / FS)))
    return a, int(round(dc * (1024 - a) / 2.0))


class E:
    """place = 'fwd' (filter on S, V289 as built) or 'fb' (same filter on the feedback operand)."""

    def __init__(self, c, filt=None, place="fwd", fb_ab=None, kp=None, kd=None):
        self.c = c
        fb_a, fb_b = fb_ab if fb_ab else (c["fb_a"], c["fb_b"])
        kp = float(c["kp_Y"][0] if kp is None else kp)
        kd = float(c["kd_Y"][0] if kd is None else kd)
        self.F = (np.array([fb_b / 1024.0, fb_b / 1024.0]), np.array([1.0, -fb_a / 1024.0]))
        self.C = (np.array([kp / 256.0 + kd / 8.0, -kd / 8.0]), np.array([1.0]))
        self.fade = 254.0 / 256.0
        self.Hlag = (np.array([c["lag_b"] / 1024.0 / 32.0] * 2), np.array([1.0, -c["lag_a"] / 1024.0]))
        self.K = c["gain"] / 32768.0
        self.N = filt if filt else (np.array([1.0]), np.array([1.0]))
        self.place = place

    def R(self):
        n = pmul([0.0, 1.0], self.F[0], self.C[0], self.Hlag[0], self.N[0]) * self.K * self.fade
        d = pmul(self.F[1], self.C[1], self.Hlag[1], self.N[1])
        return n, d

    def fwd(self):
        if self.place == "fwd":
            return (pmul([0.0, 1.0], self.C[0], self.Hlag[0], self.N[0]) * self.K * self.fade,
                    pmul(self.C[1], self.Hlag[1], self.N[1]))
        return (pmul([0.0, 1.0], self.C[0], self.Hlag[0]) * self.K * self.fade,
                pmul(self.C[1], self.Hlag[1]))

    def Rf(self, f):
        n, d = self.R()
        return pev(n, f) / pev(d, f)


class Plant:
    def __init__(self, d):
        self.g0, self.tau, self.f1 = d["g0"], d["tau"], d["f1"]
        self.fp, self.zp, self.kappa = d["fp"], d["zp"], d.get("kappa")
        nd = int(round(self.tau / TS))
        w1 = 2 * np.pi * self.f1
        num, den = np.array([self.g0 * w1]), np.array([1.0, w1])
        if self.fp:
            wp = 2 * np.pi * self.fp
            mden = np.array([1.0, 2 * self.zp * wp, wp ** 2])
            mnum = np.array([wp ** 2])
            if self.kappa is not None:
                mnum = np.polyadd((1 - self.kappa) * mden, self.kappa * mnum)
            num, den = np.polymul(num, mnum), np.polymul(den, mden)
        bz, az, _ = signal.cont2discrete((num, den), TS, method="zoh")
        bz = np.atleast_1d(np.squeeze(bz))
        az = np.atleast_1d(np.squeeze(az))
        self.num = np.concatenate([np.zeros(nd), bz])
        self.den = az.copy()


def Lpoly(el, pl):
    rn, rd = el.R()
    return pmul(rn, pl.num) * CPD, pmul(rd, pl.den)


def poles(el, pl):
    n, d = Lpoly(el, pl)
    ch = padd(d, n)
    w = np.roots(ch[::-1])
    w = w[np.abs(w) > 1e-12]
    z = 1.0 / w
    s = np.log(z) * FS
    return np.abs(s.imag) / (2 * np.pi), -s.real / np.abs(s), z


def least_damped(f, zeta, lo=8.0, hi=30.0):
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return np.nan, np.nan
    k = int(np.argmin(zeta[m]))
    return float(f[m][k]), float(zeta[m][k])


def step_lin(el, pl, n=1500, sp=STEP_SP):
    """EXACT closed-loop step, time domain.  T(w) = fn*pn*CPD*ld / (fd*pd*(ld+ln)) with everything a
    polynomial in w = z^-1, so lfilter integrates it directly -- no 32k FFT per (candidate, fit)."""
    fn, fd = el.fwd()
    ln, ld = Lpoly(el, pl)
    num = pmul(fn, pl.num, ld) * CPD
    den = pmul(fd, pl.den, padd(ld, ln))
    u = np.zeros(n)
    u[5:] = 32.0 * sp
    y = signal.lfilter(num, den, u) / CPD
    ss = float(y[-200:].mean())
    k = np.where(y >= 0.9 * ss)[0] if ss > 0 else np.array([], int)
    return dict(pk=float(np.max(np.abs(y))), ss=ss, t90=(float(k[0]) - 5.0) if len(k) else np.nan, y=y)


def score(el, pl, base_step):
    f, z, zz = poles(el, pl)
    fm, zm = least_damped(f, z)
    ln, ld = Lpoly(el, pl)
    Lv = pev(ln, FG) / pev(ld, FG)
    S = 1 / np.abs(1 + Lv)
    st = step_lin(el, pl)
    return dict(f=fm, z=zm, Ms=float(S.max()), unst=bool(np.any(np.abs(zz) >= 1.0)),
                pkR=st["pk"] / base_step["pk"], ss=st["ss"] / base_step["ss"], t90=st["t90"],
                over=st["pk"] / st["ss"] if st["ss"] > 0 else np.nan)


def gate73(el, el0):
    return float(abs(LS73 * (el.Rf(7.3) / el0.Rf(7.3)) + LR73))


def main():
    c, img = read_cells()
    pr("adv_v290_null -- image %s" % c["path"])
    pr("  BYTE-READ (my own struct reads): fb %d/%d  lag %d/%d  gain %d  clamps P%d D%d S%d T%d fb%d" % (
        c["fb_a"], c["fb_b"], c["lag_a"], c["lag_b"], c["gain"],
        c["p_clamp"], c["d_clamp"], c["sum_clamp"], c["t_clamp"], c["fb_clamp"]))
    pr("  Kp record @0x%X n=%d  X=%s  Y=%s" % (c["kp_base"], c["kp_n"], c["kp_X"], c["kp_Y"]))
    pr("  Kd record @0x%X n=%d  X=%s  Y=%s" % (c["kd_base"], c["kd_n"], c["kd_X"], c["kd_Y"]))
    pr("  V289 notch ints b0 %d b1 %d a2 %d" % (c["b0"], c["b1"], c["a2"]))
    N289 = (np.array([c["b0"], c["b1"], c["b0"]], float) / 16384.0,
            np.array([16384.0, c["b1"], c["a2"]]) / 16384.0)
    fam = json.load(open(os.path.join(SCR, "design290b_family.json")))
    pr("  family: %d fits" % len(fam))

    pr("")
    pr("SPOT-VERIFY the family JSON (my own root-find vs the stored values)")
    pr("     id | stored f282/z282   mine            | stored f289/z289   mine")
    err = []
    e282 = E(c, None, "fwd", fb_ab=(923, 1560))
    e289 = E(c, N289, "fwd")
    for i in list(range(0, len(fam), max(1, len(fam) // 8)))[:8]:
        ft = fam[i]
        pl = Plant(ft)
        f1, z1 = least_damped(*poles(e282, pl)[:2], 12, 32)
        f2, z2 = least_damped(*poles(e289, pl)[:2], 12, 32)
        pr("  %5d | %6.3f %+7.4f  %6.3f %+7.4f | %6.3f %+7.4f  %6.3f %+7.4f" % (
            ft["id"], ft["f282"], ft["z282"], f1, z1, ft["f289"], ft["z289"], f2, z2))
        err += [abs(f1 - ft["f282"]), abs(f2 - ft["f289"]),
                abs(z1 - ft["z282"]) * 100, abs(z2 - ft["z289"]) * 100]
    pr("  max |err| over the 8 (Hz, and zeta x100): %.4f  => family JSON %s" % (
        max(err), "REPRODUCES" if max(err) < 0.05 else "DOES NOT REPRODUCE"))

    stable = [ft for ft in fam if ft["z289"] >= 0.005]
    pr("  linear-stable-on-V289 sub-family: %d" % len(stable))
    plants = [Plant(ft) for ft in stable]
    base = [step_lin(e282, pl) for pl in plants]
    b282 = [score(e282, pl, base[k]) for k, pl in enumerate(plants)]

    pr("")
    pr("T2. IS pkR AN AUTHORITY METRIC?  V282 baseline capped-step, per fit")
    ov = np.array([b["over"] for b in b282])
    zv = np.array([b["z"] for b in b282])
    pr("  V282 peak/steady OVERSHOOT ratio, stable family: p5 %.2f  p50 %.2f  p95 %.2f  (1.00 = no overshoot)"
       % tuple(np.percentile(ov, [5, 50, 95])))
    pr("  V282 least-damped pole zeta:                     p5 %.3f p50 %.3f p95 %.3f"
       % tuple(np.percentile(zv, [5, 50, 95])))
    pr("  rho(overshoot ratio, -zeta) = %+.3f   [~ +1 means the step PEAK *is* the ring]"
       % float(np.corrcoef(ov, -zv)[0, 1]))

    pr("")
    pr("T1. THE MISSING TOPOLOGY: the SAME filter on the FEEDBACK OPERAND")
    pr("  rows = design290b section-4 joint-solve winners, each scored in BOTH placements over the %d"
       % len(plants))
    pr("  linear-stable fits.  place=fwd is what design290b scored; place=fb is absent from its 92 rows.")
    pr("")
    pr("  candidate                              place |  z_w    @f_w |  z_med | Ms_w  | gate73 | pkR_w pkR_med | ss_med | t90_med | unst")
    rows = []
    combos = [("notch 21.5 Q1.5 + fb 40 Hz", 21.5, 1.5, 40.0),
              ("notch 21.0 Q1.5 + fb 40 Hz", 21.0, 1.5, 40.0),
              ("notch 20.5 Q1.5 + fb 40 Hz", 20.5, 1.5, 40.0),
              ("notch 20.0 Q1.5 + fb 40 Hz", 20.0, 1.5, 40.0),
              ("notch 19.0 Q1.5 + fb 40 Hz", 19.0, 1.5, 40.0),
              ("notch 19.0 Q1.5 + fb 35 Hz", 19.0, 1.5, 35.0),
              ("notch 18.0 Q1.0 + fb 25 Hz", 18.0, 1.0, 25.0),
              ("notch 20.04 Q3 + fb 25 (=V289)", None, None, None)]
    for name, fc, Q, fbf in combos:
        if fc is None:
            filt, fbab = N289, (c["fb_a"], c["fb_b"])
        else:
            bq, aq, _i = rbj_notch_q14(fc, Q)
            filt = (bq, aq)
            fbab = fb_pole_ints(fbf)
        for place in ("fwd", "fb"):
            el = E(c, filt, place, fb_ab=fbab)
            zs, fs_, ms, pk, ssr, t9, un = [], [], [], [], [], [], 0
            for k, pl in enumerate(plants):
                s = score(el, pl, base[k])
                zs.append(s["z"]); fs_.append(s["f"]); ms.append(s["Ms"])
                pk.append(s["pkR"]); ssr.append(s["ss"]); t9.append(s["t90"])
                un += int(s["unst"])
            zs = np.array(zs); pk = np.array(pk)
            g = gate73(el, e282)
            kw = int(np.argmin(zs))
            pr("  %-38s %-5s | %+.3f %5.1f | %+.3f | %5.1f | %6.3f | %5.2f %5.2f   | %6.3f | %5.0f   | %d/%d" % (
                name, place, zs[kw], fs_[kw], float(np.median(zs)), float(np.max(ms)), g,
                float(pk.min()), float(np.median(pk)), float(np.median(ssr)),
                float(np.median(t9)), un, len(plants)))
            rows.append(dict(name=name, place=place, z_w=float(zs[kw]), z_med=float(np.median(zs)),
                             gate=g, pkR_w=float(pk.min()), pkR_med=float(np.median(pk)),
                             t90_med=float(np.median(t9)), unst=un))

    pr("")
    pr("  CHECK: poles identical between placements (they must be -- same return ratio R)")
    bq, aq, _i = rbj_notch_q14(21.5, 1.5)
    fbab = fb_pole_ints(40.0)
    ea = E(c, (bq, aq), "fwd", fb_ab=fbab)
    eb = E(c, (bq, aq), "fb", fb_ab=fbab)
    d = np.max(np.abs(np.sort_complex(poles(ea, plants[0])[2]) - np.sort_complex(poles(eb, plants[0])[2])))
    pr("    max |pole difference| on fit 0: %.3e   gate73 fwd %.6f  fb %.6f"
       % (abs(d), gate73(ea, e282), gate73(eb, e282)))
    pr("    V282 baseline t90 median: %.0f ms" % float(np.median([b["t90"] for b in b282])))

    # ------------------------------------------------------------------ T3: the constrained search, fb placement
    pr("")
    pr("T3. THE CONSTRAINED SEARCH design290b's section 10 never printed, re-run in the FEEDBACK placement.")
    pr("    Gates (the operator's, as stated in the brief): gate73 <= 1.01, pkR_med >= 0.95, 0 unstable fits.")
    pr("    Ranked by WORST-CASE zeta over the 121 linear-stable fits.  V282 baseline: z_w +0.013, z_med +0.031.")
    pr("")
    grid = []
    for fc in np.arange(16.0, 26.01, 0.5):
        for Q in (0.7, 1.0, 1.5, 2.0, 3.0):
            for fbf in (16.5, 20.0, 25.0, 30.0, 35.0, 40.0, 50.0):
                grid.append((fc, Q, fbf))
    res = []
    for fc, Q, fbf in grid:
        bq, aq, ints = rbj_notch_q14(fc, Q)
        fbab = fb_pole_ints(fbf)
        el = E(c, (bq, aq), "fb", fb_ab=fbab)
        g = gate73(el, e282)
        if g > 1.01:
            continue
        zs, pk, un, ms = [], [], 0, []
        for k, pl in enumerate(plants):
            s = score(el, pl, base[k])
            zs.append(s["z"]); pk.append(s["pkR"]); ms.append(s["Ms"])
            un += int(s["unst"])
        zs = np.array(zs); pk = np.array(pk)
        res.append(dict(fc=fc, Q=Q, fb=fbf, z_w=float(zs.min()), z_med=float(np.median(zs)),
                        gate=g, pkR_med=float(np.median(pk)), pkR_w=float(pk.min()),
                        Ms_w=float(np.max(ms)), unst=un, ints=ints, fb_ab=fbab))
    feas = [r for r in res if r["pkR_med"] >= 0.95 and r["unst"] == 0]
    feas.sort(key=lambda r: -r["z_w"])
    pr("    grid %d combos -> %d pass gate73 <= 1.01 -> %d also pass pkR_med >= 0.95 and 0 unstable" % (len(grid), len(res), len(feas)))
    pr("")
    pr("    notch f   Q    fb pole |  z_w   z_med | Ms_w  | gate73 | pkR_med pkR_w | notch Q14 ints (b0,b1,b2 / a1,a2) | fb a/b")
    for r in feas[:20]:
        pr("    %5.1f Hz %4.1f  %5.1f Hz | %+.3f %+.3f | %5.1f | %6.3f |  %5.2f  %5.2f  | %s / %s | %d/%d" % (
            r["fc"], r["Q"], r["fb"], r["z_w"], r["z_med"], r["Ms_w"], r["gate"], r["pkR_med"], r["pkR_w"],
            r["ints"][0], r["ints"][1][1:], r["fb_ab"][0], r["fb_ab"][1]))
    if not feas:
        pr("    NONE -- the null would stand on this surface.")
    json.dump(feas, open(os.path.join(SCR, "adv_v290_null_feasible.json"), "w"), indent=1)

    # ------------------------------------------------------------------ T4: is the worst case set by refuted fits?
    pr("")
    pr("T4. IS THE WORST CASE SET BY FITS THE CAR HAS ALREADY REFUTED?")
    n696 = sum(1 for ft in fam if ft.get("unst696"))
    pr("    Kp 696 datum (r31-r34 flew Kp 696 STABLE, f +0.4 Hz, zeta 0.019):")
    pr("      the family predicts UNSTABLE at Kp 696 on %d of %d fits (%d of the %d linear-stable ones)."
       % (n696, len(fam), sum(1 for ft in stable if ft.get("unst696")), len(stable)))
    pr("      => EVERY fit in the family is falsified by the one direct gain-sweep measurement available.")
    pr("      The 'unstable on N/121' column, and any worst-case-over-the-family score, is therefore biased")
    pr("      PESSIMISTIC by an unknown amount.  My T3 winners use the same criterion, so they are conservative.")
    sub = [k for k, ft in enumerate(stable) if 0.02 <= ft["z289"] <= 0.13]
    pr("    Sub-family also consistent with the MEASURED V289 burst decay (zeta_eff 0.02-0.13): %d of %d fits"
       % (len(sub), len(stable)))
    pr("")
    pr("    top T3 rows re-ranked on that sub-family (worst case over %d fits), with the new-peak checks:" % len(sub))
    pr("    notch f   Q    fb pole |  z_w(sub) z_med(sub) | Ms_w  | S1014 S2230 (worst ratio vs V282) | pkR_med(sub)")
    for r in feas[:6]:
        bq, aq, _i = rbj_notch_q14(r["fc"], r["Q"])
        el = E(c, (bq, aq), "fb", fb_ab=tuple(r["fb_ab"]))
        zs, pk, s14, s23, ms = [], [], [], [], []
        for k in sub:
            pl = plants[k]
            ln, ld = Lpoly(el, pl)
            Lv = pev(ln, FG) / pev(ld, FG)
            S = 1 / np.abs(1 + Lv)
            ln0, ld0 = Lpoly(e282, pl)
            S0 = 1 / np.abs(1 + pev(ln0, FG) / pev(ld0, FG))
            m14 = (FG >= 10) & (FG <= 14)
            m23 = (FG >= 22) & (FG <= 30)
            s14.append(S[m14].max() / S0[m14].max())
            s23.append(S[m23].max() / S0[m23].max())
            ms.append(float(S.max()))
            f_, z_, _z = poles(el, pl)
            zs.append(least_damped(f_, z_)[1])
            pk.append(step_lin(el, pl)["pk"] / base[k]["pk"])
        pr("    %5.1f Hz %4.1f  %5.1f Hz |  %+.3f    %+.3f     | %5.1f | %5.1fx %5.1fx                    | %5.2f" % (
            r["fc"], r["Q"], r["fb"], float(np.min(zs)), float(np.median(zs)), float(np.max(ms)),
            float(np.max(s14)), float(np.max(s23)), float(np.median(pk))))

    json.dump(rows, open(os.path.join(SCR, "adv_v290_null_rows.json"), "w"), indent=1)
    open(os.path.join(SCR, "adv_v290_null.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")


main()
