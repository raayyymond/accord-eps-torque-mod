# -*- coding: utf-8 -*-
r"""rev_cap_size.py -- size the A3 cap: ONE cave immediate sets ONE cap value for EVERY v-word <= capv, so extending the
cap to 12.5 m/s also changes the <= 6 m/s band (V298: 4096).  Compares, per turn amplitude 30/45/60/90 deg:
  V298 | A-rev1 (synthesis: 4096 @ <= 1382) | A-S5120 / A-S5632 / A-S6144 (single value @ <= 2880, the 4-byte edit)
  | A-TL6144 (two-level: 4096 @ <= 1382, 6144 @ 1382 < v <= 2880 -- NOT a 4-byte edit; emulated per column, speed fixed)
Hands-off turn-in at the planner's rate, hold 4 s, unwind; speeds 3, 4, 5, 6, 6.5, 7, 8, 10, 11.75, 12.5 m/s;
members r79F and b_lo*J_hi.  usage: python rev_cap_size.py RSN|S2   (one engine per call, each < 30 s)."""
import collections, json, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rev_common as RC

ENG = sys.argv[1] if len(sys.argv) > 1 else "RSN"
SPEEDS = (3.0, 4.0, 5.0, 6.0, 6.5, 7.0, 8.0, 10.0, 11.75, 12.5)
AMPS = (30.0, 45.0, 60.0, 90.0)
HOLD = 4.0


def cap_of(sysname, v):
    vw = int(round(v * 230.4))
    if sysname == "A-rev1":
        return dict(capv=1382, capval=4096, caplo_v=1382, caplo=4096)
    if sysname.startswith("A-S"):
        return dict(capv=2880, capval=int(sysname[3:]), caplo_v=2880, caplo=int(sysname[3:]))
    if sysname.startswith("A-TL"):
        return dict(capv=2880, capval=4096 if vw <= 1382 else int(sysname[4:]), caplo_v=1382, caplo=4096)
    return {}


SYSN = ("V298", "A-rev1", "A-S5120", "A-S5632", "A-S6144", "A-TL6144")


def metrics(th, T, A, t0, ta, tu, v):
    i0, i25, iu = int(t0 * 1000), int((ta + 2.5) * 1000), int(tu * 1000)
    ovs = float(th[i0:i25].max() - A)
    hit = np.flatnonzero(th[i0:iu] >= 0.9 * A)
    return dict(ovs=ovs, F4=bool(v <= 10.0 and (ovs > 6.0 or ovs > 0.15 * A)), t90=hit[0] / 1000 if len(hit) else None,
                err=float(A - th[iu - 1]), und=float(-th[iu:].min()), tap=float(np.abs(T).max() / 2461.0))


def rsn_job(args):
    v, sd = args
    E = RC.load_rsn()
    cols = [dict(sys=s, rule="V298" if s == "V298" else "V299", fork="V298" if s == "V298" else "A", variant=cap_of(s, v),
                 member=m, v=v, An=A, A=min(A, 0.9 * float(E.vm_amax(v)))) for s in SYSN for A in AMPS for m in ("r79F", "b_lo*J_hi")]
    Av = np.array([c["A"] for c in cols]); Rt = E.plan_rate(v); t0 = 0.5; ta = t0 + Av / Rt; tu = ta + HOLD
    plan = lambda t: np.clip((t - t0) * Rt, 0, Av) - np.clip((t - tu) * Rt, 0, Av)  # noqa
    R = E.run(cols, float(tu.max() + Av.max() / Rt + 1.5), plan, seed=300 + sd, rec=("th", "T"))
    return [dict(metrics(R["th"][:, j].astype(float), R["T"][:, j].astype(float), c["A"], t0, ta[j], tu[j], v),
                 sys=c["sys"], v=v, A=c["A"], An=c["An"], member=c["member"], sd=sd) for j, c in enumerate(cols)]


def s2_job(v):
    S2 = RC.load_s2()
    S2.FK["SYNA"] = dict(inst=1200.0, d600=8, o1lead=0.0, take=0.4)
    S2.CANDS = {"V298": ("V298", "V298", "")}
    for s in SYSN[1:]:
        S2.FW["fw_" + s] = dict(thr=1229, sgn=0, asym=True, **cap_of(s, v))
        S2.CANDS[s] = ("fw_" + s, "SYNA", s)
    amax = float(S2.D2C.vm_amax(np.array([v]))[0])
    cols = [dict(cid=c, member=m, v=v, x="ti", s=s, An=A, A=min(A, 0.9 * amax)) for c in S2.CANDS for A in AMPS
            for m in S2.MEMBERS for s in (1, 2)]
    B = len(cols); Av = np.array([c["A"] for c in cols]); Rt = S2.plan_rate(v); t0 = 0.5; ta = t0 + Av / Rt; tu = ta + HOLD
    plan = lambda t: np.clip((t - t0) * Rt, 0, Av) - np.clip((t - tu) * Rt, 0, Av)  # noqa
    R = S2.run(cols, float(tu.max() + Av.max() / Rt + 1.5), plan, np.zeros(B))
    return [dict(metrics(R["th"][:, j].astype(float), R["T"][:, j].astype(float), c["A"], t0, ta[j], tu[j], v),
                 sys=c["cid"], v=v, A=c["A"], An=c["An"], member=c["member"], sd=c["s"]) for j, c in enumerate(cols)]


if __name__ == "__main__":
    T0 = time.perf_counter()
    if len(sys.argv) > 2 and sys.argv[2] == "report":
        res = json.loads((RC.OUT / f"rev_cap_size_{ENG}.json").read_text())
    else:
      with Pool(16) as p:
        if ENG == "RSN":
            res = sum(p.map(rsn_job, [(v, sd) for v in SPEEDS for sd in (1, 2)]), [])
        else:
            res = sum(p.map(s2_job, SPEEDS), [])
      (RC.OUT / f"rev_cap_size_{ENG}.json").write_text(json.dumps(res), encoding="utf-8")
    L = [f"### {ENG}: overshoot max over members x seeds [F4 cols] / hold error @4 s max |.| -- per amplitude",
         "| system | v | " + " | ".join(f"{int(a)} deg ovs [F4] / err" for a in AMPS) + " | tap pk % |",
         "|---|---|" + "---|" * (len(AMPS) + 1)]
    g = collections.defaultdict(list)
    for d in res:
        g[(d["sys"], d["v"])].append(d)
    for s in SYSN:
        for v in SPEEDS:
            X = g[(s, v)]
            cells = []
            for a in AMPS:
                Y = [x for x in X if x["An"] == a]
                o = max(x["ovs"] for x in Y); f4 = sum(x["F4"] for x in Y); e = max(abs(x["err"]) for x in Y)
                cells.append(f"{o:.1f} [{f4}/{len(Y)}] / {e:.1f}")
            L.append(f"| {s} | {v} | " + " | ".join(cells) + f" | {100*max(x['tap'] for x in X):.0f} |")
    L.append(f"wall {time.perf_counter() - T0:.1f} s")
    txt = "\n".join(L); print(txt); (RC.OUT / f"rev_cap_size_{ENG}.md").write_text(txt, encoding="utf-8")
