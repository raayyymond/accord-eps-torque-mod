"""rr_t1_report.py -- tabulate rr_t1_* (< 1 s)."""
import collections, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rsn2 as R
D = {"RSN": json.loads((R.OUT / "rr_t1_RSN.json").read_text()),
     "S2": json.loads((R.OUT / "rr_t1_S2_lin.json").read_text()) + json.loads((R.OUT / "rr_t1_S2_rc.json").read_text())}
SP = sorted({d["v"] for d in D["RSN"]})
AM = (30.0, 45.0, 60.0, 90.0)
L = []
for eng, rows in D.items():
    g = collections.defaultdict(list)
    for d in rows:
        g[(d["sys"], d["v"], d["An"])].append(d)
    L.append(f"\n### {eng}: overshoot max over members x seeds x plans [F4 cols / n] (F4 as rev-2 text; F4old = rev-1 text incl. 15 % at any amp)")
    L.append("| v | " + " | ".join(f"{s} {int(a)}" for s in ("V298", "R2", "R1N") for a in AM) + " |")
    L.append("|---|" + "---|" * 12)
    for v in SP:
        cells = []
        for s in ("V298", "R2", "R1N"):
            for a in AM:
                X = g[(s, v, a)]
                cells.append(f"{max(x['ovs'] for x in X):.1f} [{sum(x['F4'] for x in X)}|{sum(x['F4old'] for x in X)}/{len(X)}]")
        L.append(f"| {v} | " + " | ".join(cells) + " |")
    L.append(f"\n### {eng}: R2 by plan kind -- overshoot max [F4] at 45/60/90, hold err max, unwind max, a3 duty in hold (median)")
    for v in SP:
        cells = []
        for k in ("lin", "rc1", "rc2"):
            X = [d for d in rows if d["sys"] == "R2" and d["v"] == v and d["kind"] == k and d["An"] >= 45]
            cells.append(f"{k}: {max(x['ovs'] for x in X):.1f} [{sum(x['F4'] for x in X)}] err {max(abs(x['err']) for x in X):.1f} und {max(x['und'] for x in X):.1f}")
        a3 = np.median([d["a3hold"] for d in rows if d["sys"] == "R2" and d["v"] == v])
        L.append(f"| {v} | " + " | ".join(cells) + f" | a3 {a3:.2f} |")
    L.append(f"\n### {eng}: note 2 / stutter -- linear plan, 60 & 90 deg; median [max] over members x seeds")
    L.append("| v | sys | t90 60 | t90 90 | r4-8 | r1.6-3 | stall-surges/turn | ovs | err | unwind | tap LSB max |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for v in SP:
        for s in ("V298", "R2", "R1N"):
            X = [d for d in rows if d["sys"] == s and d["v"] == v and d["kind"] == "lin" and d["An"] in (60.0, 90.0)]
            f = lambda k, Y=X: f"{np.median([y[k] for y in Y if y[k] is not None]):.2f} [{max(y[k] for y in Y if y[k] is not None):.2f}]"  # noqa
            t60 = [y["t90"] for y in X if y["An"] == 60 and y["t90"] is not None]; t90_ = [y["t90"] for y in X if y["An"] == 90 and y["t90"] is not None]
            L.append(f"| {v} | {s} | {np.median(t60) if t60 else float('nan'):.2f} | {np.median(t90_) if t90_ else float('nan'):.2f} | {f('r48')} | {f('r163')} | {np.mean([y['ss'] for y in X]):.2f} | {f('ovs')} | {f('err')} | {f('und')} | {max(y['tap'] for y in X):.0f} |")
    # member split of t90 at 3-8
    L.append(f"\n### {eng}: t90 (lin, 60/90) R2 / V298 ratio per member, 3-8 m/s")
    for m in ("r79F", "b_lo*J_hi"):
        cells = []
        for v in (3.0, 4.0, 5.0, 6.1, 7.0, 8.0):
            a = [d["t90"] for d in rows if d["sys"] == "R2" and d["v"] == v and d["member"] == m and d["kind"] == "lin" and d["An"] >= 60 and d["t90"]]
            b = [d["t90"] for d in rows if d["sys"] == "V298" and d["v"] == v and d["member"] == m and d["kind"] == "lin" and d["An"] >= 60 and d["t90"]]
            cells.append(f"{v}: {np.median(a):.2f}/{np.median(b):.2f}={np.median(a)/np.median(b):.2f}")
        L.append(f"| {m} | " + " | ".join(cells) + " |")
    # all-amplitude tap max hands-off (F9 > 250 LSB)
    for s in ("V298", "R2"):
        X = [d for d in rows if d["sys"] == s]
        L.append(f"{eng} {s}: tap LSB max over the grid {max(x['tap'] for x in X):.0f}; >250: {sum(x['tap'] > 250 for x in X)}/{len(X)}")
txt = "\n".join(L); print(txt); (R.OUT / "rr_t1_report.md").write_text(txt, encoding="utf-8")
