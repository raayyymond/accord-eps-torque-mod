# -*- coding: utf-8 -*-
r"""syn_s2.py -- the V299 SYNTHESIS composite scored as ONE ROW of the common S2 time/nonlinear scorer
(scores/S2-time-nonlinear/s2_time.py imported unchanged; only the candidate table is extended).  ANALYSIS ONLY.
Rows: V298, D1c (fw only), D2a (fork only), G:D1c+D3fork (S2's graft), and three composite forks on D1c's firmware:
  SYN     D1c fw + D2a-style fork WITHOUT SteerDelay: cap 300 (jerk-limited above ~6 m/s), clip x1.6 at <= 11.75 m/s,
          O1 > 1200 instant | > 600 held 8 frames, O1 lead 0, takeover ramp 0.4 s (rate AND clip)
  SYN-K1  D1c fw + D3's K1 envelope (cap 300/300/200/120 at 0/5/8/10 m/s, clip 30/25 deg at 3.1/8) + the same O1 gate,
          lead 0, takeover 0.4 s; NO K3 post-clip lead, NO K4
  SYN-250 SYN with cap 250 (D5's)
usage: python syn_s2.py   (Pool over TI/LH/OV/C2; RD is identical for every row by S2's own result)
"""
import importlib.util, json, os, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
V299 = HERE.parent
KIT = V299.parents[3]
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
_s = importlib.util.spec_from_file_location("s2_time_syn", V299 / "scores" / "S2-time-nonlinear" / "s2_time.py")
S2 = importlib.util.module_from_spec(_s); sys.modules["s2_time_syn"] = S2; _s.loader.exec_module(S2)
G4 = dict(inst=1200.0, d600=8, o1lead=0.0, take=0.4)
CLIP16 = (27.2, 24.8, 31.2, 27.2, 8.5, 4.5)
S2.FK["SYN"] = dict(cap_v=(3.0, 3.0), clip=CLIP16, **G4)
S2.FK["SYNK1"] = dict(cap_bp=(0.0, 5.0, 8.0, 10.0), cap_v=(3.0, 3.0, 2.0, 1.2), clip=(30.0, 25.0, 19.5, 17.0, 8.5, 4.5), **G4)
S2.FK["SYN250"] = dict(cap_v=(2.5, 2.5), clip=CLIP16, **G4)
S2.CANDS = {k: S2.CANDS[k] for k in ("V298", "D1c", "D2a", "G:D1c+D3fork")}
S2.CANDS.update({"SYN": ("D1c", "SYN", "synthesis: D1c fw + G4/lead0/take + cap300/clip1.6"),
                 "SYN-K1": ("D1c", "SYNK1", "synthesis: D1c fw + G4/lead0/take + D3 K1 envelope"),
                 "SYN-250": ("D1c", "SYN250", "synthesis: SYN with cap 250")})
S2.CIDS = tuple(S2.CANDS)
OUT = KIT / "_scratch" / "v299_SYN"; OUT.mkdir(parents=True, exist_ok=True)

def _job(g):
    t0 = time.perf_counter(); rows = S2.GROUPS[g](); return g, [S2._clean(r) for r in rows], time.perf_counter() - t0

def agg(rows, key, cid, v=None, x=None, member="r79F", seeds=(1, 2, 3), worst=False):
    sel = [r for r in rows if r["cid"] == cid and (v is None or r["v"] == v) and (x is None or r["x"] == x)
           and r.get(key) is not None]
    if worst:
        vals = [r[key] for r in sel if r["s"] in seeds]
        return max(vals) if vals else np.nan
    vals = [r[key] for r in sel if r["member"] == member and r["s"] in seeds]
    return float(np.median(vals)) if vals else np.nan

if __name__ == "__main__":
    T0 = time.perf_counter()
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        R = json.loads((OUT / "syn_s2.json").read_text(encoding="utf-8")); walls = {}
    else:
        with Pool(4) as p:
            res = p.map(_job, ["TI", "LH", "OV", "C2"])
        R = {g: rows for g, rows, _ in res}; walls = {g: w for g, _, w in res}
        (OUT / "syn_s2.json").write_text(json.dumps(R), encoding="utf-8")
    TI, LH, OV, C2 = R["TI"], R["LH"], R["OV"], R["C2"]
    L = ["| cand | TI t90 s 3/8 | w pk 3/8 | ovs deg [worst] | settle s | tap pk %rail [worst] | frz tog/s 3/8 | I kept 3/8 | hand-lost 3 | stall-surge | O1 twist trips | r48 3/8 | r1.6-3 3/8 | unwind under deg 3 | LH worst lurch deg | LH o5 median | OV t_O1 ms 5/15 | OV tap under hand % 5 | OV hand T 5 | C2 slow e_rms 15/25 |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in S2.CIDS:
        a = lambda k, v, **kw: agg(TI, k, c, v, **kw)  # noqa: E731
        ss = sum(int(r["ss"]) for r in TI if r["cid"] == c and r["member"] == "r79F" and r["s"] == 1)
        o1 = sum(int(r["o1_eps"]) for r in TI if r["cid"] == c and r["member"] == "r79F" and r["s"] == 1)
        lh_w = max(r["lurch"] for r in LH if r["cid"] == c)
        lh_o5 = agg(LH, "lurch", c, 5.0, "o")
        L.append(f"| {c} | {a('t90',3.0):.2f}/{a('t90',8.0):.2f} | {a('wpk',3.0):.0f}/{a('wpk',8.0):.0f} | "
                 f"{max(a('ovs',3.0),a('ovs',8.0)):.1f} [{max(agg(TI,'ovs',c,worst=True),0):.1f}] | {max(a('settle',3.0),a('settle',8.0)):.2f} | "
                 f"{100*max(a('tap_pk',3.0),a('tap_pk',8.0)):.0f} [{100*agg(TI,'tap_pk',c,worst=True):.0f}] | "
                 f"{a('hand_tog_s',3.0):.1f}/{a('hand_tog_s',8.0):.1f} | {a('kept',3.0):.2f}/{a('kept',8.0):.2f} | {a('hand_lost',3.0):.2f} | {ss} | {o1} | "
                 f"{a('r48',3.0):.1f}/{a('r48',8.0):.1f} | {a('r163',3.0):.1f}/{a('r163',8.0):.1f} | {a('under',3.0):.1f} | "
                 f"{lh_w:.1f} | {lh_o5:.1f} | {agg(OV,'t_o1_ms',c,5.0):.0f}/{agg(OV,'t_o1_ms',c,15.0):.0f} | "
                 f"{100*agg(OV,'ov_tap',c,5.0):.0f} | {agg(OV,'hf_hold',c,5.0):.0f} | {agg(C2,'erms',c,15.0,'slow'):.2f}/{agg(C2,'erms',c,25.0,'slow'):.2f} |")
    L.append(f"\nwalls: {dict((k, round(v, 1)) for k, v in walls.items())} total {time.perf_counter() - T0:.1f} s")
    txt = "\n".join(L); print(txt); (OUT / "syn_s2.md").write_text(txt, encoding="utf-8")
