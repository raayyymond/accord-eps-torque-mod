"""reconcile: the ZERO-CAVE re-key option (Kp and Kd records keyed on gp-0x6a5d = speed>>8, Ki and DB flat) in the
FREQ harness.  Kp(v) = the freq harness's ROBUST edge schedule (reproducible exactly by 5 knots), Kd(v) and a flat Ki
searched.  Reports gates on the credible family and tracking over 0.1-0.5 Hz (the goal's 0.5 Hz-LP regression band)
as well as 0.1-1 Hz.  Analysis only."""
import sys, math, json, itertools
from pathlib import Path
HERE = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\studies\angle_loop")
sys.path.insert(0, str(HERE))
import numpy as np
import harness_freq as HF
import lane_mirror_v295 as LM

SPEEDS = HF.SPEEDS
CRED = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6")
F = HF.FGRID
b05 = (F >= 0.1) & (F <= 0.5)


def key(v):
    return int(round(v * 3.6 * 64)) >> 8


def evalc(kp, ki, kd, v, members=CRED):
    c = HF.Ctl(kp=float(kp), ki=float(ki), kd=float(kd))
    out = {}
    for m in members:
        p = HF.plant_at(m, v)
        r295 = HF.metrics(HF.V295, p, exact=True)
        r = HF.metrics(c, p, exact=True)
        g = HF.gates(r, r295)
        g["GM6"] = r["gm_lti_db"] >= 6.0
        cc = HF.replace(c, d=p.tau)
        P = HF.plant_frf(p, F)
        L = HF.C_fb(F, cc) * P
        Tr = HF.C_ref(F, cc) * P / (1 + L)
        r["trk05"] = (float(np.abs(Tr[b05]).min()), float(np.abs(Tr[b05]).max()))
        out[m] = (all(g.values()), [k for k, ok in g.items() if not ok], r)
    return out


def main():
    ROB = dict(zip(SPEEDS, (637, 682, 730, 1178, 3070, 3520, 3520)))
    res = {}
    print("ZERO-CAVE RE-KEY: Kp(v) = ROBUST edge; flat Ki; Kd per speed.  cell: robust-safe? | nominal fc/PM | "
          "trk 0.1-0.5 / 0.1-1 | hold")
    for Ki in (0, 100, 154, 200, 250, 300, 400, 500, 650, 849):
        line = []
        for v in SPEEDS:
            best = None
            for kd in (8, 12, 16, 20, 24, 28):
                o = evalc(ROB[v], Ki, kd, v)
                safe = all(x[0] for x in o.values())
                rn = o["nominal"][2]
                perf = (v < 8.0) or (0.95 <= rn["trk05"][0] and rn["trk05"][1] <= 1.05 and rn["hold"] >= 0.90)
                score = (safe, perf, rn["pm"])
                if best is None or score > best[0]:
                    best = (score, kd, o)
            (safe, perf, _), kd, o = best
            rn = o["nominal"][2]
            bad = sorted({m for m, x in o.items() if not x[0]})
            line.append(f"{v:g}: Kd{kd} {'SAFE' if safe else 'unsafe(' + ','.join(bad) + ')'} {'PERF' if perf else 'noperf'}"
                        f" fc{rn['fc']:.2f} PM{rn['pm']:.0f} trk05 {rn['trk05'][0]:.2f}-{rn['trk05'][1]:.2f}"
                        f" trk1 {rn['trk_min']:.2f}-{rn['trk_max']:.2f} hold{rn['hold']:.2f}")
            res.setdefault(str(Ki), {})[str(v)] = dict(kd=kd, safe=safe, perf=perf, fc=rn["fc"], pm=rn["pm"],
                                                        trk05=rn["trk05"], trk1=(rn["trk_min"], rn["trk_max"]),
                                                        hold=rn["hold"], unsafe=bad)
        npass = sum(1 for v in SPEEDS if res[str(Ki)][str(v)]["safe"] and res[str(Ki)][str(v)]["perf"])
        print(f"\nKi {Ki}: {npass}/7 safe+perf")
        for l in line:
            print("   " + l)
    # the E-gain ROBUST for reference with the same trk05 metric
    print("\nREFERENCE: E-gain ROBUST (Ki = 0.2413 Kp, Kd 16)")
    for v in SPEEDS:
        o = evalc(ROB[v], HF.ki_for(ROB[v], 0.3), 16, v)
        rn = o["nominal"][2]
        bad = sorted({m for m, x in o.items() if not x[0]})
        print(f"   {v:g}: {'SAFE' if not bad else bad} fc{rn['fc']:.2f} PM{rn['pm']:.0f} trk05 {rn['trk05'][0]:.2f}-"
              f"{rn['trk05'][1]:.2f} trk1 {rn['trk_min']:.2f}-{rn['trk_max']:.2f} hold{rn['hold']:.2f}")
    Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\_scratch\angle_loop\reconcile\rec_freq_rekey.json"
         ).write_text(json.dumps(res))


if __name__ == "__main__":
    main()
