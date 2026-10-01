"""reconcile: evaluate the TIME harness's candidates and the FREQ harness's schedules on the SAME frequency-domain
metrics (harness_freq.metrics/full), nominal + credible members.  Analysis only."""
import sys, math, json
from pathlib import Path
HERE = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\studies\angle_loop")
sys.path.insert(0, str(HERE))
import numpy as np
import harness_freq as HF

SPEEDS = HF.SPEEDS
def key(v):
    return int(round(v * 3.6 * 64)) >> 8

def lerp(X, Y, u):
    import lane_mirror_v295 as LM
    return LM.lerp(X, Y, u)

# --- candidate schedules: per speed (Kp, Ki, Kd) ---------------------------------------------------------------
def speed1(Ki=1024):
    kx, ky = (2, 4, 11, 17, 23), (1500, 1200, 1800, 1500, 2500)
    dx, dy = (2, 4, 7, 11), (28, 24, 24, 0)
    return {v: (lerp(kx, ky, key(v)), Ki, lerp(dx, dy, key(v))) for v in SPEEDS}

ROB = dict(zip(SPEEDS, (637, 682, 730, 1178, 3070, 3520, 3520)))
DES = dict(zip(SPEEDS, (896, 960, 1028, 2335, 4628, 4628, 4628)))
def egain(S, fi=0.3, kd=16):
    return {v: (S[v], HF.ki_for(S[v], fi), kd) for v in SPEEDS}

CANDS = {
    "SPEED-1 (time)": speed1(),
    "ROBUST (freq)": egain(ROB),
    "DESIGN (freq)": egain(DES),
    "FLAT-L (time)": {v: (1200, 1024, 24) for v in SPEEDS},
    "FLAT-T (time)": {v: (2500, 1024, 16) for v in SPEEDS},
}
if len(sys.argv) > 1 and sys.argv[1] == "--extra":
    extra = json.loads(Path(sys.argv[2]).read_text())
    CANDS = {k: {float(v): tuple(x) for v, x in d.items()} for k, d in extra.items()}

MEMBERS = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6", "light_b")

def run():
    out = {}
    for name, sch in CANDS.items():
        print(f"\n=== {name}")
        out[name] = {}
        for v in SPEEDS:
            kp, ki, kd = sch[v]
            c = HF.Ctl(kp=float(kp), ki=float(ki), kd=float(kd))
            cells = []
            for m in MEMBERS:
                p = HF.plant_at(m, v)
                r295 = HF.metrics(HF.V295, p, exact=True)
                r = HF.full(c, p)
                g = HF.gates(r, r295)
                g["GM6"] = r["gm_exact_db"] >= 6.0
                fails = [k for k, ok in g.items() if not ok]
                w = r["wheel"]
                out[name].setdefault(str(v), {})[m] = dict(fc=r["fc"], pm=r["pm"], gm=r["gm_exact_db"], M20=r["M20"],
                    M20bar=r295["M20"], L20=r["L20"], L20bar=r295["L20"], Tr163=r.get("Tr163"), S530=r["S530_db"],
                    trk=(r.get("trk_min"), r.get("trk_max")), hold=r.get("hold"), wheel=w, stable=r["stable"],
                    fails=fails)
                if m in ("nominal", "b_lo", "J_hi", "light_b"):
                    cells.append(f"{m}: fc {r['fc']:.2f} PM {r['pm']:.0f} GM {r['gm_exact_db']:.1f} M20 {r['M20']:.2f}"
                                 f" Tr1.6-3 {r.get('Tr163', float('nan')):.2f} S5-30 {r['S530_db']:+.1f}"
                                 f" trk {r.get('trk_min', float('nan')):.2f}-{r.get('trk_max', float('nan')):.2f}"
                                 f" wheel {w[0]:.2f}Hz z{w[1]:.2f}" + (" FAIL:" + ",".join(fails) if fails else ""))
            print(f" v {v:4g} Kp {kp:.0f} Ki {ki:.0f} Kd {kd:.0f} fI {7.8125*ki/(2*math.pi*kp):.2f}Hz")
            for cl in cells:
                print("     " + cl)
    return out

if __name__ == "__main__":
    o = run()
    tag = sys.argv[3] if len(sys.argv) > 3 else "base"
    Path(rf"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\_scratch\angle_loop\reconcile\rec_freq_{tag}.json").write_text(
        json.dumps(o, default=lambda x: float(x) if isinstance(x, (np.floating,)) else str(x)))
