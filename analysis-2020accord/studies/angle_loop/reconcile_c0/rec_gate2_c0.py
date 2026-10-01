"""reconcile: GATE 2 tables for the chosen design (E-gain ROBUST schedule, Kd 16, fI 0.3) -- the EPS angle loop at every
speed, magnitude AND phase, on nominal / b_lo / J_hi; the 20 Hz comparison to V295 in both conventions; and the fork
outer loop closed around the new inner loop (stand-in: integrating correction on the ~60 ms-old 0x14A angle, the time
harness's 'pi' form; plus the stock LatControlAngle feed-forward which closes no loop).  Analysis only."""
import sys, math, json
from pathlib import Path
HERE = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\studies\angle_loop")
sys.path.insert(0, str(HERE))
import numpy as np
import harness_freq as HF

SPEEDS = HF.SPEEDS
ROB = dict(zip(SPEEDS, (450, 500, 600, 1000, 2500, 3000, 3000)))  # C0
DES = dict(zip(SPEEDS, (896, 960, 1028, 2335, 4628, 4628, 4628)))
FR = np.array([0.1, 0.3, 0.5, 1.0, 1.6, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0, 13.0, 17.0, 20.0, 25.0, 30.0])


def rec20(kp, kd):
    """the record's no-hold |(P+D)/x| at 20 Hz (V295 3.85) -- harness_time.hf20 form."""
    W = 2 * np.pi * 20.0
    z1 = np.exp(-1j * W * 1e-3)
    Pp = (kp / 256.0) * 8.0 * abs(1 + z1) * 10.0 / W / 8.0
    return float(np.hypot(Pp, kd / 8.0))


def table(S, name, fi=0.55, kd=16):
    print(f"\n##### {name}: Kd {kd}, fI {fi} Hz (Ki = {7.8125:.4f}^-1 * 2 pi fI Kp)")
    rows = {}
    for v in SPEEDS:
        kp = S[v]
        c = HF.Ctl(kp=float(kp), ki=HF.ki_for(kp, fi), kd=float(kd))
        for m in ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6", "light_b", "J_hi2", "ms_free"):
            p = HF.plant_at(m, v)
            r = HF.full(c, p)
            r295 = HF.metrics(HF.V295, p, exact=True)
            cc = HF.replace(c, d=p.tau)
            P = HF.plant_frf(p, FR) if False else p.frf(FR)
            L = HF.C_fb(FR, cc) * P
            Tr = HF.C_ref(FR, cc) * P / (1 + L)
            w = r["wheel"]
            rows.setdefault(str(v), {})[m] = dict(
                kp=kp, ki=c.ki, fc=r["fc"], pm=r["pm"], gm=r["gm_exact_db"], f180=r["f180"], M20=r["M20"],
                M20_v295=r295["M20"], L20=r["L20"], L20_v295=r295["L20"], Ms=r["Ms"], S530=r["S530_db"],
                Tr163=r["Tr163"], wheel=w, stable=r["stable"], rec20=rec20(kp, kd),
                bode={f"{f:g}": (float(abs(L[i])), float(np.degrees(np.angle(L[i]))), float(abs(Tr[i])))
                      for i, f in enumerate(FR)})
            if m in ("nominal", "b_lo", "J_hi", "J_lo", "b_hi", "tau6"):
                print(f" v {v:4g} {m:8s} Kp {kp:5.0f} Ki {c.ki:5.0f} | fc {r['fc']:.2f} PM {r['pm']:5.1f} GM {r['gm_exact_db']:5.1f}"
                      f" f180 {r['f180']:5.2f} | M20 {r['M20']:.2f} (V295 {r295['M20']:.2f}) L20 {r['L20']:.4f} (V295"
                      f" {r295['L20']:.4f}) rec20 {rec20(kp, kd):.2f} (3.85) | Ms {r['Ms']:.2f} S5-30 {r['S530_db']:+.1f}"
                      f" Tr1.6-3 {r['Tr163']:.2f} | wheel {w[0]:.2f} Hz z {w[1]:.2f}" + ("" if r["stable"] else " UNSTABLE"))
            else:
                print(f" v {v:4g} {m:8s} stable {r['stable']} wheel {w[0]:.2f} Hz z {w[1]:.2f} PM {r['pm']:.0f}")
    return rows


def bode(S, name, fi=0.55, kd=16):
    print(f"\n##### BODE {name} (nominal): |L|, angle L deg, |T_ref|")
    print("  v    " + " ".join(f"{f:>13g}" for f in FR))
    for v in SPEEDS:
        kp = S[v]
        c = HF.Ctl(kp=float(kp), ki=HF.ki_for(kp, fi), kd=float(kd))
        p = HF.plant_at("nominal", v)
        cc = HF.replace(c, d=p.tau)
        P = p.frf(FR)
        L = HF.C_fb(FR, cc) * P
        Tr = HF.C_ref(FR, cc) * P / (1 + L)
        print(f" {v:4g} |L|  " + " ".join(f"{abs(x):13.3f}" for x in L))
        print(f"      angL " + " ".join(f"{np.degrees(np.angle(x)):13.0f}" for x in L))
        print(f"      |Tr| " + " ".join(f"{abs(x):13.3f}" for x in Tr))


def outer(S, name, fi=0.55, kd=16, tau_o=1.0, lat=0.06):
    """fork outer loop stand-in: c' = (1/tau_o) (theta_ref - theta(t - lat)); theta = T_ref * (theta_ref + c).
    Loop L_o = T_ref(s) e^{-s lat} / (tau_o s).  Also the outer loop if the fork closed a P on the angle at gain kO."""
    print(f"\n##### OUTER LOOP (fork stand-in, integrating correction tau_o {tau_o} s on the {lat*1000:.0f} ms-old 0x14A angle)"
          f" around {name} (nominal / b_lo)")
    f = np.logspace(-3, 1.3, 4000)
    out = {}
    for v in SPEEDS:
        kp = S[v]
        c = HF.Ctl(kp=float(kp), ki=HF.ki_for(kp, fi), kd=float(kd))
        cells = []
        for m in ("nominal", "b_lo"):
            p = HF.plant_at(m, v)
            cc = HF.replace(c, d=p.tau)
            P = p.frf(f)
            L = HF.C_fb(f, cc) * P
            Tr = HF.C_ref(f, cc) * P / (1 + L)
            Lo = Tr * np.exp(-2j * np.pi * f * lat) / (tau_o * 2j * np.pi * f)
            mag = np.abs(Lo)
            i = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0][0]
            fc = f[i]
            pm = 180 + np.degrees(np.angle(Lo[i]))
            ph = np.unwrap(np.angle(Lo))
            j = np.where(ph < -np.pi)[0]
            gm = (20 * np.log10(1 / mag[j[0]])) if len(j) else float("inf")
            cells.append(f"{m}: fc {fc:.3f} Hz PM {pm:.1f} GM {gm:.1f} dB")
            out.setdefault(str(v), {})[m] = dict(fc=float(fc), pm=float(pm), gm=float(gm))
        print(f" v {v:4g}: " + " | ".join(cells))
    return out


if __name__ == "__main__":
    o = dict(c0=table(ROB, "C0"))
    bode(ROB, "C0")
    o["outer_c0"] = outer(ROB, "C0")
    o["outer_c0_fast"] = outer(ROB, "C0", tau_o=0.3)
    Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\_scratch\angle_loop\reconcile\rec_gate2_c0.json").write_text(
        json.dumps(o, default=lambda x: float(x) if isinstance(x, (np.floating, np.bool_)) else str(x)))
