# -*- coding: utf-8 -*-
"""SECTION O -- the amplitude thresholds, in the demand's own units AND in deg of wheel angle.

O1  V282's small-amplitude |H| knee (the deadband scale of the REFERENCE), located on a fine sweep,
    and the torque mode's flatness over the same sweep.
O2  where the torque mode's extra lag switches on at 2-8 m/s.
O3  the RAIL threshold in wheel angle: how close to full scale the command gets, by |wheel angle| and
    speed, per group -- the headroom a future design has to spend.
O4  the unit conversions a design needs: band-limited demand amplitude (m/s^2 RMS) <-> deg of desired
    wheel angle <-> peak lateral accel, at each speed.

ANALYSIS ONLY.  Run: python thresh.py
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dflib as D            # noqa: E402
import fastH as FH           # noqa: E402
import v282cmp as C          # noqa: E402

GROUPS = {"V282": ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"],
          "V282old": ["00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4"],
          "TQall": ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
                    "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]}
LOG = []


def pr(s=""):
    print(s, flush=True)
    LOG.append(s)


RUNS = {}
for rk in C.ROUTES:
    RUNS[rk], _ = D.route_runs(rk)

# ================================================================================= O1
pr("=" * 128)
pr("O1   THE SMALL-AMPLITUDE |H| KNEE -- fine sweep, 15-40 m/s, overlapping amplitude windows")
pr("=" * 128)
pr("Sliding amplitude windows (each holds 25 % of the group's windows in that band, stepped by 10 %)")
pr("so the knee is not an artefact of bin edges.  A = RMS of the band-passed model demand, m/s^2.")
pr("'deg RMS' = the same amplitude expressed as desired WHEEL angle through the fork's VehicleModel;")
pr("'deg pk' = x sqrt(2), the sinusoid-equivalent peak.")
pr("")
for f1, f2, W in D.BANDS[:3]:
    pr(f"BAND {f1:.2f}-{f2:.2f} Hz")
    for gname in ("V282", "TQall"):
        ws = []
        for ri, rk in enumerate(GROUPS[gname]):
            for w in D.windows(RUNS[rk], W):
                if 15 <= w["v"] < 40:
                    w2 = dict(w); w2["A"] = D.amp(w, f1, f2); w2["spec"] = FH.win_spec(w, f1, f2, W)
                    w2["cid"] = (ri, w["rid"]); ws.append(w2)
        ws.sort(key=lambda w: w["A"])
        n = len(ws)
        if n < 60:
            pr(f"  {gname:8s} only {n} windows -> skipped")
            continue
        wid = max(int(0.25 * n), 12)
        step = max(int(0.10 * n), 5)
        rows = []
        for k in range(0, n - wid + 1, step):
            sub = ws[k:k + wid]
            r = FH.pool([w["spec"] for w in sub])
            a = float(np.median([w["A"] for w in sub])); vm = float(np.median([w["v"] for w in sub]))
            dg = a / vm ** 2 * float(D.deg_per_curv(vm))
            rows.append((a, dg, r))
        plateau = float(np.median([r["H"] for _, _, r in rows[-3:]]))
        knee95 = next((a for a, _, r in rows if r["H"] >= 0.95 * plateau), None)
        knee90 = next((a for a, _, r in rows if r["H"] >= 0.90 * plateau), None)
        pr(f"  {gname:8s} n={n}  plateau |H| {plateau:.2f}")
        pr(f"    {'A m/s2':>8s} {'degRMS':>7s} {'deg pk':>7s} {'|H|':>5s} {'coh':>5s} {'NE':>5s} "
           f"{'lag ms':>7s} {'nwin':>5s}")
        for a, dg, r in rows:
            pr(f"    {a:8.4f} {dg:7.3f} {dg*1.414:7.3f} {r['H']:5.2f} {r['coh']:5.2f} {r['NE']:5.2f} "
               f"{1000*r['lag']:+7.0f} {r['n']:5d}")
        if knee95:
            i = next(i for i, (a, _, _) in enumerate(rows) if a == knee95)
            pr(f"    -> |H| reaches 90 % of its plateau at A = {knee90:.4f} m/s^2, 95 % at "
               f"A = {knee95:.4f} m/s^2 = {rows[i][1]:.3f} deg RMS ({rows[i][1]*1.414:.3f} deg peak) "
               f"of desired wheel angle")
        else:
            pr("    -> |H| never reaches 95 % of its plateau over the measured amplitude range")
        pr("")

# ================================================================================= O2
pr("=" * 128)
pr("O2   WHERE THE TORQUE MODE'S EXTRA LAG SWITCHES ON AT 2-8 m/s (sliding amplitude windows)")
pr("=" * 128)
pr("Both groups' windows are sorted on a COMMON amplitude axis and matched window-for-window by")
pr("amplitude rank, so the comparison is at equal demand.")
pr("")
for f1, f2, W in D.BANDS[1:4]:
    out = {}
    for gname in ("V282", "TQall"):
        ws = []
        for ri, rk in enumerate(GROUPS[gname]):
            for w in D.windows(RUNS[rk], W, hop=W // 4):
                if 2 <= w["v"] < 8:
                    w2 = dict(w); w2["A"] = D.amp(w, f1, f2); w2["spec"] = FH.win_spec(w, f1, f2, W)
                    w2["cid"] = (ri, w["rid"]); ws.append(w2)
        out[gname] = sorted(ws, key=lambda w: w["A"])
    if min(len(out["V282"]), len(out["TQall"])) < 30:
        continue
    pr(f"BAND {f1:.2f}-{f2:.2f} Hz, 2-8 m/s   (V282 n={len(out['V282'])}, torque n={len(out['TQall'])})")
    pr(f"    {'A range':>17s} {'degRMS':>7s} {'|ang|':>6s} | {'V282 H':>7s}{'NE':>6s}{'lag':>7s}{'n':>5s} | "
       f"{'TQ H':>6s}{'NE':>6s}{'lag':>7s}{'n':>5s} | {'d_lag':>6s} {'NE x':>5s}")
    qs = [0, 25, 50, 75, 100]
    allA = sorted([w["A"] for g in out for w in out[g]])
    ed = [float(np.percentile(allA, q)) for q in qs]
    ed[0], ed[-1] = 0.0, 1e9
    for k in range(len(ed) - 1):
        sv = [w for w in out["V282"] if ed[k] <= w["A"] < ed[k + 1]]
        st = [w for w in out["TQall"] if ed[k] <= w["A"] < ed[k + 1]]
        if len(sv) < 8 or len(st) < 8:
            pr(f"    {f'{ed[k]:.4f}-{min(ed[k+1],9.9):.4f}':>17s}  -- n too thin (V282 {len(sv)}, "
               f"torque {len(st)}) --")
            continue
        rv = FH.pool([w["spec"] for w in sv]); rt = FH.pool([w["spec"] for w in st])
        a = float(np.median([w["A"] for w in sv + st])); vm = float(np.median([w["v"] for w in sv + st]))
        pr(f"    {f'{ed[k]:.4f}-{min(ed[k+1],9.9):.4f}':>17s} {a/vm**2*float(D.deg_per_curv(vm)):7.3f} "
           f"{float(np.median([w['sa_med'] for w in sv+st])):6.1f} | "
           f"{rv['H']:7.2f}{rv['NE']:6.2f}{1000*rv['lag']:+7.0f}{len(sv):5d} | "
           f"{rt['H']:6.2f}{rt['NE']:6.2f}{1000*rt['lag']:+7.0f}{len(st):5d} | "
           f"{1000*(rt['lag']-rv['lag']):+6.0f} {rt['NE']/max(rv['NE'],1e-9):5.2f}")
    pr("")

# ================================================================================= O3
pr("=" * 128)
pr("O3   HOW CLOSE THE COMMAND GETS TO FULL SCALE, by |wheel angle| and speed -- the headroom")
pr("=" * 128)
pr("|out| is the logged, already-clipped command in units of full scale.  p99.9 and max are per cell.")
pr("")
AB = [(0, 2), (2, 5), (5, 15), (15, 30), (30, 60), (60, 120), (120, 400)]
for slo, shi in [(2, 8), (8, 15), (15, 40)]:
    pr(f"  v {slo}-{shi} m/s")
    pr(f"    {'|ang| deg':>11s} |" + "|".join(f"{g:^34s}" for g in GROUPS))
    pr(f"    {'':>11s} |" + "|".join(f"{'sec':>7s}{'p99.9':>7s}{'max':>6s}{'%>=0.9':>7s}{'%>=0.98':>8s} "
                                    for g in GROUPS))
    for a0, a1 in AB:
        line = f"    {f'{a0}-{a1}':>11s} |"
        any_ = False
        for gname in GROUPS:
            o = np.concatenate([r["out"] for rk in GROUPS[gname] for r in RUNS[rk]])
            v = np.concatenate([r["v"] for rk in GROUPS[gname] for r in RUNS[rk]])
            sa = np.abs(np.concatenate([r["sa"] for rk in GROUPS[gname] for r in RUNS[rk]]))
            m = (v >= slo) & (v < shi) & (sa >= a0) & (sa < a1)
            if m.sum() < 50:
                line += f"{'--':^34s}|"
                continue
            any_ = True
            line += (f"{m.sum()/D.FS:7.1f}{np.percentile(o[m],99.9):7.3f}{o[m].max():6.3f}"
                     f"{100*(o[m]>=0.90).mean():7.3f}{100*(o[m]>=0.98).mean():8.4f} |")
        if any_:
            pr(line)
    pr("")

# ================================================================================= O4
pr("=" * 128)
pr("O4   UNIT CONVERSIONS a design can be sized against")
pr("=" * 128)
pr(f"{'v m/s':>6s} {'deg per 1/m':>12s} | {'0.01 m/s2 ->':>13s} {'0.03 ->':>9s} {'0.10 ->':>9s} "
   f"{'0.30 ->':>9s}   (deg of desired wheel angle, same RMS/peak convention as the input)")
for v in (3, 5, 8, 12, 18, 25, 32):
    dpc = float(D.deg_per_curv(v))
    pr(f"{v:6.0f} {dpc:12.1f} | " + " ".join(f"{a/v**2*dpc:>12.3f}" if i == 0 else f"{a/v**2*dpc:>9.3f}"
                                             for i, a in enumerate((0.01, 0.03, 0.10, 0.30))))
pr("")

with open(os.path.join(HERE, "THRESH-OUT.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(LOG) + "\n")
