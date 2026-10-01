"""reconcile round 2: E-gain designs chosen from the per-speed intersection (rec_joint.py / rec_freq_edges.py).
Same LaneCave (rec_time.py) -- E' = (E*G(v))>>8, Kd flat, Ki/Kp constant.  Analysis only."""
import sys, os, json
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1"); os.environ.setdefault("OMP_NUM_THREADS", "1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rec_time as R          # patches harness_time.LaneVec = LaneCave (rec_time.py sits next to this file)
from rec_time import HT, egain_row, OUT, json as _j

SP = HT.SPEEDS
def S(*k): return tuple(k)
C0 = S(450, 500, 600, 1000, 2500, 3000, 3000)

def cands():
    c = []
    c.append(egain_row(C0, 450, fi=0.55, kd=16, DB=0, ICL=4096, label="C0 Kd16 fI0.55 DB0 ICL4096 Kp_eff 450/500/600/1000/2500/3000/3000 + bleed |tq|>1024 tau64ms",
                       bleed_thr=1024, bleed_sh=6))
    c.append(egain_row(C0, 450, fi=0.52, kd=16, DB=0, ICL=4096, label="C0-fI0.52 (same, Ki base 188)", bleed_thr=1024, bleed_sh=6))
    c.append(egain_row(C0, 450, fi=0.55, kd=16, DB=0, ICL=4096, label="C0nb = C0 without the bleed"))
    return c


R.cands = cands
if __name__ == "__main__":
    which = sys.argv[1]
    rows = cands()
    if which == "nominal":
        jobs = [(nm, v, rows, "nominal", "ff", 0) for v in SP for nm in HT.SCENARIOS]
        res = HT.merge(HT.run_jobs(jobs, procs=6, tag="r6-nominal"))
        (OUT / "rec6_nominal.json").write_text(json.dumps(dict(rows=rows, results=res)))
    elif which == "robust":
        jobs = [(nm, v, rows, m, "ff", 0) for m in R.MEMBERS_ROB for v in SP for nm in HT.SC_TRACK]
        res = HT.merge(HT.run_jobs(jobs, procs=6, tag="r6-robust"))
        (OUT / "rec6_robust.json").write_text(json.dumps(dict(rows=rows, members=R.MEMBERS_ROB, results=res)))
    elif which == "pi":
        jobs = [(nm, v, rows, "nominal", "pi", 0) for v in SP for nm in HT.SC_TRACK]
        res = HT.merge(HT.run_jobs(jobs, procs=6, tag="r6-pi"))
        (OUT / "rec6_pi.json").write_text(json.dumps(dict(rows=rows, results=res)))
