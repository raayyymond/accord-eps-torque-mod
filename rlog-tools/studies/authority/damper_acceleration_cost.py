# -*- coding: utf-8 -*-
"""What does the engaged damper actually COST in steering acceleration?

The operator asks for both "low apparent steering mass to LKAS" and "no ratcheting",
and on the engaged friction row those are in measured opposition. The row went x1.5
(V91..V104) -> x3.0 (V107..V121), so the corpus contains a natural experiment on his
exact complaint. Quantify the cost so the trade is a number, not an adjective.

Outcome: peak steering ACCELERATION reached under LKAS. Each route is its own control --
the statistic is the ratio of engaged to manual peak acceleration within the same drive,
so route-to-route exposure differences cancel (the design that survived
feedback-one-route-per-build-cannot-resolve-band-ratios).
"""
import numpy as np, os

FS = 100.0
DOSE = {'77': ('V90', 1.0), '78': ('V91', 1.5), '79': ('V92', 1.5), '7e': ('V96', 1.5),
        '7f': ('V96', 1.5), '85': ('V100', 1.5), '95': ('V101', 1.5), '96': ('V102', 1.5),
        '9e': ('V103', 1.5), 'a4': ('V104', 1.5), 'a5': ('V105', 1.5), 'a6': ('V106', 1.5),
        '1e': ('V107', 3.0), '21': ('V111', 3.0), '22': ('V112', 3.0), '23': ('V112', 3.0),
        '97': ('STOCK', 1.0)}


def stat(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate', 'cc_lat', 'cs_v')):
        return None
    rate, lat, v = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v')]
    acc = np.abs(np.diff(rate, prepend=rate[0])) * FS          # deg/s^2
    moving = v > 5.0
    eng = moving & (lat > 0.5)
    man = moving & (lat <= 0.5)
    if eng.sum() < 3000 or man.sum() < 3000:
        return None
    return (np.percentile(acc[eng], 99), np.percentile(acc[man], 99),
            np.percentile(np.abs(rate[eng]), 99), eng.sum(), man.sum())


rows = []
for r in sorted(DOSE):
    s = stat(r)
    if s:
        rows.append((r, DOSE[r][0], DOSE[r][1], s))
print("  peak steering ACCELERATION (p99 |d rate/dt|), engaged vs manual, same drive\n")
print("  route build   dose   eng acc     man acc    eng/man    eng rate p99   n_eng")
for r, b, d, s in sorted(rows, key=lambda x: (x[2], x[1])):
    print("   r%-4s %-6s %4.1fx  %8.1f   %8.1f   %6.3f      %7.1f     %6d"
          % (r, b, d, s[0], s[1], s[0] / s[1], s[2], s[3]))

rng = np.random.default_rng(0)
print("\n  dose   n_routes   median eng/man acc ratio    median engaged rate p99")
grp = {}
for d in (1.0, 1.5, 3.0):
    sel = [x for x in rows if x[2] == d]
    if not sel:
        continue
    grp[d] = np.array([x[3][0] / x[3][1] for x in sel])
    print("  %4.1fx     %2d              %6.3f                    %7.1f deg/s"
          % (d, len(sel), np.median(grp[d]), np.median([x[3][2] for x in sel])))

if 1.5 in grp and 3.0 in grp:
    a, b = grp[3.0], grp[1.5]
    bs = [np.median(rng.choice(a, len(a))) / np.median(rng.choice(b, len(b))) for _ in range(4000)]
    print("\n  x3.0 / x1.5 on the engaged-vs-manual acceleration ratio = %.3f   CI [%.3f, %.3f]"
          % (np.median(a) / np.median(b), np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
    print("  (below 1.0 = the bigger damper DOES cost engaged acceleration; CI containing 1.0 = not resolved)")
