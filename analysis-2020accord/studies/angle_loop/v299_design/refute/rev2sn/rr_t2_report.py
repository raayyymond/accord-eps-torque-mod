"""rr_t2_report.py -- tabulate rr_t2_hands (< 1 s)."""
import collections, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rsn2 as R
res = json.loads((R.OUT / "rr_t2_hands.json").read_text())
g = collections.defaultdict(list)
for d in res:
    g[(d["model"], d["dirn"], d["v"], d["wd"], d["sys"])].append(d)
L = ["| hand | dir | v | word | V298: F3lit / swing / F5lit / droop / F7b ms / tap opp max-res % / hand T | R2: same |", "|---|---|---|---|---|---|"]
for model in ("pos", "frc"):
    for dn in (("c", "o", "ov") if model == "pos" else ("c", "o")):
        for v in (5.0, 8.0, 10.0, 12.5, 15.0, 25.0):
            for w in (300.0, 550.0, 800.0, 1150.0, 1500.0, 2500.0):
                cells = []
                for s in ("V298", "R2"):
                    X = g[(model, dn, v, w, s)]
                    mx = lambda k: max(x[k] for x in X)  # noqa
                    cells.append(f"{mx('F3lit'):.1f} / {mx('swing'):.1f} / {mx('F5lit'):.1f} / {mx('droop'):.1f} / {mx('f7b_ms')} / "
                                 f"{100*mx('tapopp'):.0f}-{100*mx('tapres'):.0f} / {mx('handT'):.0f}")
                L.append(f"| {model} | {dn} | {v} | {int(w)} | " + " | ".join(cells) + " |")
# criterion firings summary
L.append("\n### criterion firings (R2 vs V298), all rows")
for s in ("V298", "R2"):
    X = [d for d in res if d["sys"] == s]
    f3 = [d for d in X if d["v"] >= 8 and d["F3lit"] > 8]
    f3s = [d for d in X if d["v"] >= 8 and d["swing"] > 8]
    f5 = [d for d in X if d["dirn"] == "c" and 300 < d["wd"] < 1229 and d["F5lit"] > 4]
    f5d = [d for d in X if d["dirn"] == "c" and 300 < d["wd"] < 1229 and d["droop"] > 4]
    f7b = [d for d in X if d["f7b_ms"] > 300]
    L.append(f"{s}: F3 as written (|th-sp|>8 within 1.5 s, v>=8) {len(f3)}/{sum(d['v']>=8 for d in X)} "
             f"[pos ov {sum(d['dirn']=='ov' and d['model']=='pos' for d in f3)}, pos c/o {sum(d['dirn']!='ov' and d['model']=='pos' for d in f3)}, frc {sum(d['model']=='frc' for d in f3)}]; "
             f"swing-past-sp > 8 (page metric) {len(f3s)}; F5 as written {len(f5)} / page droop metric {len(f5d)}; F7b {len(f7b)} "
             f"(words {sorted(set(int(d['wd']) for d in f7b))}, v {sorted(set(d['v'] for d in f7b))})")
    big = sorted(X, key=lambda d: -d["swing"])[:6]
    L.append("  worst swings: " + "; ".join(f"{d['model']} {d['dirn']} v{d['v']} w{int(d['wd'])} {d['member']} age{d['age']}: {d['swing']:.1f}" for d in big))
txt = "\n".join(L); print(txt); (R.OUT / "rr_t2_report.md").write_text(txt, encoding="utf-8")
