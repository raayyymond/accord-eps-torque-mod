"""reconcile: per speed, which (Kp, Ki, ICL, DB, Kd) configurations pass BOTH harnesses?
  TIME: harness_time's own per_speed_score on its existing caches (flat_sweep.json + refined_sweep.json, nominal plant),
        LINE-ONLY and STRICT readings.
  FREQ: harness_freq's gates (PM45, GM6, M20<=V295, L20<=V295, |T|,|T_ref| <= +3 dB in 5-30 Hz, no 5-50 Hz pole
        zeta<0.2, stable) on EVERY credible member (nominal, J_lo, J_hi, b_lo, b_hi, tau0, tau6), plus the 1.6-3 Hz
        |T_ref| peak (the hard-turn band) on nominal and the worst credible member.
At a fixed speed an E-gain/re-key schedule IS a flat configuration, so the intersection per speed is the design space
of any speed schedule.  Analysis only."""
import sys, os, json, math
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
from pathlib import Path
HERE = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\studies\angle_loop")
sys.path.insert(0, str(HERE))
import numpy as np
import harness_time as HT
import harness_freq as HF

CACHE = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\_scratch\angle_loop\harness-time")
OUT = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\_scratch\angle_loop\reconcile")
CRED = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6")

_fc = {}


def freq_eval(kp, ki, kd, v):
    k = (kp, ki, kd, v)
    if k in _fc:
        return _fc[k]
    c = HF.Ctl(kp=float(kp), ki=float(ki), kd=float(kd))
    worst_pm, worst_tr, fails, nom = 999, 0, set(), None
    for m in CRED:
        p = HF.plant_at(m, v)
        r295 = HF.metrics(HF.V295, p, exact=True)
        r = HF.metrics(c, p, exact=True)
        g = HF.gates(r, r295)
        g["GM6"] = r["gm_lti_db"] >= 6.0
        for kk, ok in g.items():
            if not ok:
                fails.add(f"{m}:{kk}")
        worst_pm = min(worst_pm, r["pm"] if np.isfinite(r["pm"]) else -99)
        worst_tr = max(worst_tr, r["Tr163"])
        if m == "nominal":
            nom = dict(fc=r["fc"], pm=r["pm"], Tr163=r["Tr163"], M20=r["M20"], wheel=r["wheel"])
    out = dict(safe=not fails, fails=sorted(fails), worst_pm=worst_pm, worst_Tr163=worst_tr, nom=nom)
    _fc[k] = out
    return out


def main():
    rows, res = [], []
    for fn in ("flat_sweep.json", "refined_sweep.json"):
        d = json.loads((CACHE / fn).read_text())
        off = len(rows)
        rows += d["rows"]
        for r in d["results"]:
            r = dict(r)
            res.append((off, r))
    # build per-file tables then score per file
    report = {}
    for fn in ("flat_sweep.json", "refined_sweep.json"):
        d = json.loads((CACHE / fn).read_text())
        R = d["rows"]
        T = HT.table(d["results"], R)
        kp = [max(r["kpY"]) for r in R]
        kd = [r["kdY"][0] if r["d_rate"] else 0 for r in R]
        for v in HT.SPEEDS:
            for strict in (False, True):
                gates, allpass, cost = HT.per_speed_score(T, v, kp, kd, strict=strict)
                for i, r in enumerate(R):
                    if r.get("oa", 992) != 992:
                        continue
                    key = (r["label"], v)
                    e = report.setdefault(key, dict(row=r, v=v))
                    e["strict" if strict else "line"] = bool(allpass[i])
                    if not strict:
                        e["fails_line"] = [k for k in HT.GATES if not gates[k][i]]
                        rh, st, s02, s05, ssm = (T[(n, v)] for n in ("rh", "st", "s02", "s05", "ssm"))
                        e["m"] = dict(tg=(s02["track_gain"][i], s05["track_gain"][i]), hold=rh["hold_ratio"][i],
                                      fit=ssm["fit_gain"][i],
                                      dj=s02["dj_events"][i] + s05["dj_events"][i] + ssm["dj_events"][i] + rh["hold_slips"][i] + st["hold_slips"][i],
                                      Thf=max(rh["T_hf"][i], st["T_hf"][i]),
                                      tex=max(s02["T_hf"][i], s05["T_hf"][i], ssm["T_hf"][i]),
                                      hard=(rh["hard16"][i], rh["hard16_ref"][i]), ess=rh["ess_turn"][i])
    # freq-evaluate every time-LINE-passing config, per speed
    out = {}
    for (lab, v), e in sorted(report.items(), key=lambda t: (t[0][1], t[0][0])):
        if not e.get("line"):
            continue
        r = e["row"]
        kp = max(r["kpY"])
        kd = r["kdY"][0] if r["d_rate"] else 0
        f = freq_eval(kp, r["Ki"], kd, v)
        out.setdefault(str(v), []).append(dict(label=lab, kp=kp, ki=r["Ki"], icl=r["ICL"], db=r["DB"], kd=kd,
                                               strict=e["strict"], freq=f, m=e["m"]))
    for v in HT.SPEEDS:
        L = out.get(str(v), [])
        both = [x for x in L if x["freq"]["safe"]]
        print(f"\n=== {v:g} m/s: TIME line-only passes {len(L)}, of which FREQ credible-safe {len(both)}"
              f" (TIME strict + FREQ safe: {sum(1 for x in both if x['strict'])})")
        for x in sorted(L, key=lambda x: (not x["freq"]["safe"], -x["freq"]["worst_pm"]))[:14]:
            f, m = x["freq"], x["m"]
            print(f"  {'BOTH' if f['safe'] else 'time'}{'+S' if x['strict'] else '  '} Kp{x['kp']:5d} Ki{x['ki']:5d} ICL{x['icl']:5d}"
                  f" DB{x['db']} Kd{x['kd']:2d} | freq worstPM {f['worst_pm']:5.1f} worstTr1.6-3 {f['worst_Tr163']:.2f}"
                  f" nomPM {f['nom']['pm']:.0f} nomTr {f['nom']['Tr163']:.2f} | tg {m['tg'][0]:.2f}/{m['tg'][1]:.2f} hold"
                  f" {m['hold']:.2f} fit {m['fit']:.2f} dj {m['dj']:.0f} Thf {m['Thf']:.1f} tex {m['tex']:.1f}"
                  f" hard {m['hard'][0]:.2f}/{m['hard'][1]:.2f}" + ("" if f["safe"] else "  freqfail " + ",".join(f["fails"][:4])))
    (OUT / "rec_joint.json").write_text(json.dumps(out, default=lambda x: float(x) if isinstance(x, np.floating) else
                                                   (bool(x) if isinstance(x, np.bool_) else str(x))))


if __name__ == "__main__":
    main()
