"""POOLED pass.  attrib.py keeps the study's own per-rev groups; with 4-6 blocks a cell they are too thin
to resolve an AMPLITUDE axis on the torque side.  Here the routes are pooled by THE THING BEING TESTED,
read from each route's own initData (wire_params.py / ffgain_ceiling/flown_params.json):

  V282   64, 65, 6c(2bc8)   V282 rate-servo EPS; fork 0f98d8c7/57410c3b: NO AccordDobHz, NO AccordRefFilter,
                            NO AccordRateLoopGain, NO AccordFrictionHyst, NO AccordHoldLevel key at all.
                            LAF 6.0, SteerKP 0.9, SteerFriction 0.01, Ki 0.3, RatePlantFF 1, SR 16.33/16.84
  TON    6c(68c6), 6d, 6e, 76   V293 torque EPS, observer ON (AccordDobHz 0.6). LAF 14.0
  TOFF   75                     V293 torque EPS, observer OFF (no AccordDobHz key). LAF 14.0
  V282old 39, 3a, 3c            V282 EPS, old fork, LAF 2.11/4.0/3.6, SR 12.5

Route-cluster bootstrap throughout, so a pooled |H| whose routes disagree gets a wide CI and is not read
as evidence.  5 amplitude bins.  MEASUREMENT + algebra only.
"""
import sys, json, math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1])); sys.path.insert(0, str(HERE))
import v282cmp as V
from surf import INSTR, BANDS, SPD, OUT
from agg import load_all, band_amp, cell_H

rng = np.random.default_rng(19)
POOL = {
    "00000064--ce6b0b0ebb": "V282", "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
    "0000006c--68c6e94b17": "TON", "0000006d--05e83bb04f": "TON",
    "0000006e--6ca3e014fd": "TON", "00000076--d0b7ea7e4d": "TON",
    "00000075--6c8687d5bd": "TOFF",
    "00000039--f56039af87": "V282old", "0000003a--283a39a1d6": "V282old", "0000003c--927965c2b4": "V282old",
}
GR = ["V282", "TON", "TOFF", "V282old"]
NQ = (0.2, 0.4, 0.6, 0.8)
COH_MIN, NMIN = 0.55, 8


def cells(B, key, f1, f2):
    per, pool = {}, {si: [] for si in range(len(SPD))}
    for rk, d in B.items():
        amp, s, df = band_amp(d, key, f1, f2)
        vv = d[f"{key}_v"]
        per[rk] = (amp, s, df, vv)
        for si, (lo, hi) in enumerate(SPD):
            pool[si].extend(amp[(vv >= lo) & (vv < hi)].tolist())
    out, edges = {}, {}
    for si, (lo, hi) in enumerate(SPD):
        pv = np.array(pool[si])
        if len(pv) < 20:
            continue
        e = [0.0] + list(np.quantile(pv, NQ)) + [np.inf]
        edges[si] = e
        for ai in range(len(e) - 1):
            for rk, d in B.items():
                amp, s, df, vv = per[rk]
                m = (vv >= lo) & (vv < hi) & (amp >= e[ai]) & (amp < e[ai + 1])
                for j in np.flatnonzero(m):
                    out.setdefault((POOL[rk], si, ai), []).append(dict(
                        rk=rk, P=(d[f"{key}_pxx"][j, s], d[f"{key}_pyy"][j, s], d[f"{key}_pxy"][j, s]),
                        amp=float(amp[j]), ang=float(d[f"{key}_ang_med"][j]),
                        rail=float(d[f"{key}_rail"][j]), i_abs=float(d[f"{key}_i_abs"][j]),
                        f_abs=float(d[f"{key}_f_abs"][j]), p_abs=float(d[f"{key}_p_abs"][j]),
                        cmd=float(d[f"{key}_cmd_abs"][j]), fbins=d[f"{key}_f"][s]))
    return out, edges


def H_of(recs):
    return cell_H([r["P"] for r in recs])


def boot(recs, n=400):
    by = {}
    for r in recs:
        by.setdefault(r["rk"], []).append(r)
    rks = sorted(by); hs = []
    for _ in range(n):
        sel = []
        for rk in rng.choice(rks, len(rks), replace=True):
            g = by[rk]; sel += [g[i] for i in rng.integers(0, len(g), len(g))]
        if len(sel) >= 3:
            hs.append(H_of(sel)[0])
    return np.percentile(hs, [2.5, 97.5]) if len(hs) > 50 else (np.nan, np.nan)


def splithalf(recs, n=150):
    sh = []
    for _ in range(n):
        pm = rng.permutation(len(recs)); h = len(recs) // 2
        if h < 3:
            break
        sh.append(abs(H_of([recs[i] for i in pm[:h]])[0] - H_of([recs[i] for i in pm[h:]])[0]))
    return float(np.median(sh)) if sh else float("nan")


def run():
    B = load_all()
    ALL = {}
    for key in INSTR:
        for f1, f2 in BANDS[key]:
            bn = f"{f1:.2f}-{f2:.2f}"
            C, E = cells(B, key, f1, f2)
            print("\n" + "=" * 146)
            print(f"### band {bn} Hz   ({INSTR[key]/V.FS:.2f} s blocks, df {100.0/INSTR[key]:.4f} Hz)   "
                  f"|H| model-desired lat-accel -> livePose yaw*v   (5 amplitude quintiles, pooled edges)")
            print("=" * 146)
            print(f"{'v m/s':7s} {'ai':2s} {'A med':>7s} | " + " | ".join(
                f"{g:^32s}" for g in GR))
            print(f"{'':7s} {'':2s} {'':7s} | " + " | ".join(
                f"{'n/s  |H| [CI95]  coh fl lag':^32s}" for g in GR))
            for si, (lo, hi) in enumerate(SPD):
                for ai in range(len(NQ) + 1):
                    line0 = None
                    cellrow = {}
                    for g in GR:
                        recs = C.get((g, si, ai))
                        if not recs or len(recs) < 4:
                            continue
                        H, coh, ph, Pxx, Pyy, Pxy = H_of(recs)
                        clo, chi = boot(recs)
                        fl = splithalf(recs)
                        fb = recs[0]["fbins"]
                        lag = float(np.average(-np.degrees(np.angle(Pxy)) / (360.0 * fb), weights=Pxx))
                        ue = float(np.sum((1 - np.clip(np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30), 0, 1)) * Pyy))
                        cellrow[g] = dict(n=len(recs), secs=len(recs) * INSTR[key] / V.FS, H=H, coh=coh,
                                          fl=fl, lo=float(clo), hi=float(chi), lag=lag,
                                          amp=float(np.median([r["amp"] for r in recs])),
                                          ang=float(np.median([r["ang"] for r in recs])),
                                          rail=float(np.mean([r["rail"] for r in recs])),
                                          i_abs=float(np.median([r["i_abs"] for r in recs])),
                                          f_abs=float(np.median([r["f_abs"] for r in recs])),
                                          p_abs=float(np.median([r["p_abs"] for r in recs])),
                                          cmd=float(np.median([r["cmd"] for r in recs])),
                                          unexp=ue, outp=float(np.sum(Pyy)), inp=float(np.sum(Pxx)),
                                          routes=len(set(r["rk"] for r in recs)),
                                          adm=bool(coh >= COH_MIN and len(recs) >= NMIN))
                        if line0 is None:
                            line0 = cellrow[g]["amp"]
                    if not cellrow:
                        continue
                    amps = [cellrow[g]["amp"] for g in cellrow]
                    s = f"{lo}-{hi:<4d} {ai:<2d} {np.median(amps):7.4f} | "
                    parts = []
                    for g in GR:
                        r = cellrow.get(g)
                        if r is None:
                            parts.append(f"{'--':^32s}"); continue
                        mark = "" if r["adm"] else "*"
                        parts.append(f"{r['n']:3d}/{r['secs']:4.0f} {r['H']:5.2f}{mark:1s}[{r['lo']:4.2f},{r['hi']:4.2f}] "
                                     f"{r['coh']:.2f} {r['fl']:.2f} {r['lag']:+.2f}")
                    print(s + " | ".join(parts))
                    ALL[f"{bn}|{si}|{ai}"] = cellrow
    json.dump(ALL, open(OUT / "pooled.json", "w"), indent=1)
    return ALL


def shape(ALL):
    print("\n" + "=" * 146)
    print("AMPLITUDE SHAPE per (band, speed, group).   H = a + c/A  ->  c>0 means a CONSTANT-MAGNITUDE")
    print("  additive EXCESS (gain falls as 1/A);  c<0 means a constant-magnitude DEFICIT (gain rises with A).")
    print("  H = p + q*A  ->  q<0 is the SATURATION signature (droop at large amplitude).")
    print("  Cells with coh >= %.2f and n >= %d only.  ALGEBRA on measured cells." % (COH_MIN, NMIN))
    print("=" * 146)
    print(f"{'band':11s} {'v':7s} {'grp':8s} {'k':>2s} {'A range':>19s} {'H(small)':>9s} {'H(large)':>9s} "
          f"{'c':>9s} {'R2':>5s} {'q':>8s} {'R2':>5s}  reading")
    rows = []
    for key in INSTR:
        for f1, f2 in BANDS[key]:
            bn = f"{f1:.2f}-{f2:.2f}"
            for si, (lo, hi) in enumerate(SPD):
                for g in GR:
                    pts = []
                    for ai in range(len(NQ) + 1):
                        r = ALL.get(f"{bn}|{si}|{ai}", {}).get(g)
                        if r and r["adm"]:
                            pts.append((r["amp"], r["H"], r["n"]))
                    if len(pts) < 3:
                        continue
                    A = np.array([p[0] for p in pts]); H = np.array([p[1] for p in pts])
                    w = np.array([p[2] for p in pts], float)

                    def wls(X, y):
                        Xw = X * np.sqrt(w)[:, None]
                        b = np.linalg.lstsq(Xw, y * np.sqrt(w), rcond=None)[0]
                        res = y - X @ b
                        ss = np.sum(w * (y - np.average(y, weights=w)) ** 2)
                        return b, 1 - np.sum(w * res ** 2) / max(ss, 1e-12)
                    b1, r1 = wls(np.c_[np.ones(len(A)), 1.0 / A], H)
                    b2, r2 = wls(np.c_[np.ones(len(A)), A], H)
                    rd = []
                    if r1 > 0.5 and b1[1] > 0:
                        rd.append(f"const EXCESS {b1[1]:+.4f} m/s^2")
                    if r1 > 0.5 and b1[1] < 0:
                        rd.append(f"const DEFICIT {b1[1]:+.4f} m/s^2")
                    if r2 > 0.5 and b2[1] < 0:
                        rd.append("droop with A")
                    if not rd:
                        rd.append("no monotone shape")
                    print(f"{bn:11s} {lo}-{hi:<4d} {g:8s} {len(pts):2d} {A.min():8.4f}-{A.max():<10.4f} "
                          f"{H[np.argmin(A)]:9.2f} {H[np.argmax(A)]:9.2f} {b1[1]:9.5f} {r1:5.2f} {b2[1]:8.2f} {r2:5.2f}  "
                          + "; ".join(rd))
                    rows.append(dict(band=bn, si=si, g=g, c=float(b1[1]), r2c=float(r1), q=float(b2[1]),
                                     r2q=float(r2), A=[float(a) for a in A], H=[float(h) for h in H]))
    json.dump(rows, open(OUT / "shape.json", "w"), indent=1)
    return rows


def gaps(ALL):
    print("\n" + "=" * 146)
    print("THE GAP vs the V282 REFERENCE, matched (band, speed, amplitude) cell.  * = bootstrap CIs disjoint.")
    print("  Also: d_lag = lag_eq(group) - lag_eq(V282), in SECONDS, same cell -- the whole loop delay is 0.055-0.075 s.")
    print("=" * 146)
    print(f"{'band':11s} {'v':7s} {'ai':2s} {'A med':>7s} {'V282 |H|':>16s} "
          f"{'TON |H|':>24s} {'d_lag':>7s} {'TOFF |H|':>24s} {'d_lag':>7s} {'V282old':>17s}")
    out = []
    for key in INSTR:
        for f1, f2 in BANDS[key]:
            bn = f"{f1:.2f}-{f2:.2f}"
            for si, (lo, hi) in enumerate(SPD):
                for ai in range(len(NQ) + 1):
                    cr = ALL.get(f"{bn}|{si}|{ai}", {})
                    r0 = cr.get("V282")
                    if not r0 or not r0["adm"]:
                        continue
                    line = f"{bn:11s} {lo}-{hi:<4d} {ai:<2d} {r0['amp']:7.4f} {r0['H']:6.2f}[{r0['lo']:.2f},{r0['hi']:.2f}] "
                    hit = False
                    for g in ("TON", "TOFF"):
                        r = cr.get(g)
                        if not r or not r["adm"]:
                            line += f"{'--':>24s} {'--':>7s}"; continue
                        hit = True
                        sig = "*" if (r["lo"] > r0["hi"] or r["hi"] < r0["lo"]) else " "
                        line += f"{r['H']:7.2f}{sig}({r['H']-r0['H']:+.2f})[{r['lo']:.2f},{r['hi']:.2f}] {r['lag']-r0['lag']:+7.2f}"
                        out.append(dict(band=bn, si=si, ai=ai, g=g, amp=r0["amp"], H0=r0["H"], H1=r["H"],
                                        d=r["H"] - r0["H"], sig=(sig == "*"), dlag=r["lag"] - r0["lag"],
                                        rail=r["rail"], ang=r["ang"], i0=r0["i_abs"], i1=r["i_abs"],
                                        f0=r0["f_abs"], f1=r["f_abs"], p0=r0["p_abs"], p1=r["p_abs"],
                                        cmd0=r0["cmd"], cmd1=r["cmd"]))
                    ro = cr.get("V282old")
                    rostr = f"{ro['H']:.2f}" if (ro and ro["adm"]) else "--"
                    line += f"{rostr:>17s}"
                    if hit:
                        print(line)
    json.dump(out, open(OUT / "gaps.json", "w"), indent=1)
    return out


def observer(ALL):
    print("\n" + "=" * 146)
    print("MECHANISM (d) OBSERVER: the ON/OFF contrast that exists on-car.  TON = AccordDobHz 0.6 (4 routes),")
    print("  TOFF = r75, no AccordDobHz key (1 route).  Confounded: r75 also ran Ki 0.6/KiHigh 2.5, SteerKP 0.85,")
    print("  AccordRefFilter 0.12 (TON's 6c/6d/6e ran 0.06), RateLoopGain 0.0006, SteerFriction 0.212.")
    print("=" * 146)
    print(f"{'band':11s} {'v':7s} {'V282 |H|':>10s} {'TON |H|':>22s} {'TOFF |H|':>22s} "
          f"{'TON-V282':>9s} {'TOFF-V282':>10s} {'unexp Pyy/s V282/TON/TOFF':>34s}")
    for key in INSTR:
        for f1, f2 in BANDS[key]:
            bn = f"{f1:.2f}-{f2:.2f}"
            for si, (lo, hi) in enumerate(SPD):
                agg = {}
                for g in GR:
                    rs = [ALL[f"{bn}|{si}|{ai}"][g] for ai in range(len(NQ) + 1)
                          if f"{bn}|{si}|{ai}" in ALL and g in ALL[f"{bn}|{si}|{ai}"]
                          and ALL[f"{bn}|{si}|{ai}"][g]["adm"]]
                    if not rs:
                        continue
                    sec = sum(r["secs"] for r in rs)
                    agg[g] = dict(H=float(np.average([r["H"] for r in rs], weights=[r["inp"] for r in rs])),
                                  ue=sum(r["unexp"] for r in rs) / sec, sec=sec,
                                  lo=min(r["lo"] for r in rs), hi=max(r["hi"] for r in rs))
                if "V282" not in agg or not ({"TON", "TOFF"} & set(agg)):
                    continue
                f = lambda g: (f"{agg[g]['H']:6.2f}[{agg[g]['lo']:.2f},{agg[g]['hi']:.2f}]({agg[g]['sec']:.0f}s)"
                               if g in agg else "--")
                d = lambda g: (f"{agg[g]['H']-agg['V282']['H']:+9.2f}" if g in agg else f"{'--':>9s}")
                ue = "/".join(f"{agg[g]['ue']:.3g}" if g in agg else "--" for g in ("V282", "TON", "TOFF"))
                print(f"{bn:11s} {lo}-{hi:<4d} {agg['V282']['H']:10.2f} {f('TON'):>22s} {f('TOFF'):>22s} "
                      f"{d('TON'):>9s} {d('TOFF'):>10s} {ue:>34s}")


if __name__ == "__main__":
    A = run()
    shape(A)
    gaps(A)
    observer(A)
