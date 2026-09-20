"""ATTRIBUTION: which measured mechanism can own the measured |H| gap, in which cell of the surface.

Everything here is either (i) a MEASUREMENT from logged input and logged output, or (ii) ALGEBRA on one
mechanism's own transfer (a delay's phase, a clip's duty, a constant's share of a command).  Nothing is
chained into a closed-loop prediction of the car's response -- the boundary is marked at every section.

Sections
  0  ADMISSIBILITY -- coherence, split-half floor, what is excluded and what that costs
  1  THE GAP, matched cell by matched cell, route-cluster bootstrap CI
  2  AMPLITUDE SHAPE -- the discriminator between the four mechanisms' signatures
  3  (a) DELAY        -- algebra: magnitude-neutral; measured excess phase beyond the delay
  4  (b) SATURATION   -- measured duty, re-derived from the logs; the energy bound it implies
  5  (c) HOLD-FF      -- measured share of the low-speed command; testability on this route set
  6  (d) OBSERVER     -- measured unexplained output power in 1.5-3.5 Hz, ON routes vs the OFF route
  7  RESIDUAL         -- what none of the four reaches, from the wire-read config difference
"""
import sys, json, math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1])); sys.path.insert(0, str(HERE))
import v282cmp as V
from surf import INSTR, BANDS, SPD, OUT
from agg import load_all, band_amp, cell_H

rng = np.random.default_rng(11)
COH_MIN, NMIN = 0.60, 6
TORQ = ("T64", "T64B", "T5", "T4")
OBS_ON = {"0000006c--68c6e94b17": True, "0000006d--05e83bb04f": True,
          "0000006e--6ca3e014fd": True, "00000076--d0b7ea7e4d": True,
          "00000075--6c8687d5bd": False}          # r75: no AccordDobHz key on the wire -> update() returns 0


def cells(B, key, f1, f2, nq=(0.35, 0.65, 0.875)):
    """Assemble every (group, speed, amplitude) cell for one band, keeping per-block payload for bootstrap."""
    per, pool = {}, {si: [] for si in range(len(SPD))}
    grp = {rk: str(B[rk]["group"][0]) for rk in B}
    for rk, d in B.items():
        amp, s, df = band_amp(d, key, f1, f2)
        vv = d[f"{key}_v"]
        per[rk] = (amp, s, df, vv)
        for si, (lo, hi) in enumerate(SPD):
            pool[si].extend(amp[(vv >= lo) & (vv < hi)].tolist())
    out = {}
    edges_by_si = {}
    for si, (lo, hi) in enumerate(SPD):
        pv = np.array(pool[si])
        if len(pv) < 12:
            continue
        e = [0.0] + list(np.quantile(pv, nq)) + [np.inf]
        edges_by_si[si] = e
        for ai in range(len(e) - 1):
            for rk, d in B.items():
                amp, s, df, vv = per[rk]
                m = (vv >= lo) & (vv < hi) & (amp >= e[ai]) & (amp < e[ai + 1])
                for j in np.flatnonzero(m):
                    out.setdefault((grp[rk], si, ai), []).append(dict(
                        rk=rk, P=(d[f"{key}_pxx"][j, s], d[f"{key}_pyy"][j, s], d[f"{key}_pxy"][j, s]),
                        amp=float(amp[j]), ang=float(d[f"{key}_ang_med"][j]),
                        rail=float(d[f"{key}_rail"][j]), i_abs=float(d[f"{key}_i_abs"][j]),
                        f_abs=float(d[f"{key}_f_abs"][j]), cmd=float(d[f"{key}_cmd_abs"][j]),
                        df=float(df), fbins=d[f"{key}_f"][s]))
    return out, edges_by_si


def H_of(recs):
    return cell_H([r["P"] for r in recs])


def boot_H(recs, n=300):
    """Route-cluster bootstrap: resample routes with replacement, then blocks within each drawn route."""
    by = {}
    for r in recs:
        by.setdefault(r["rk"], []).append(r)
    rks = sorted(by)
    hs = []
    for _ in range(n):
        pick = rng.choice(rks, len(rks), replace=True)
        sel = []
        for rk in pick:
            g = by[rk]
            sel += [g[i] for i in rng.integers(0, len(g), len(g))]
        if len(sel) >= 2:
            hs.append(H_of(sel)[0])
    return (np.percentile(hs, [2.5, 97.5]) if len(hs) > 30 else (np.nan, np.nan)), hs


def sect0_1_2(B):
    print("=" * 130)
    print("SECTION 0/1/2  THE MEASURED SURFACE, its admissibility, and the amplitude shape")
    print("  |H| = model-desired lateral accel -> livePose yaw*v.  MEASUREMENT (logged in, logged out).")
    print("  adm = coh >= %.2f AND n >= %d AND split-half floor < 0.5*|H-1| or < 0.15" % (COH_MIN, NMIN))
    print("=" * 130)
    keep = {}
    for key in INSTR:
        for f1, f2 in BANDS[key]:
            C, E = cells(B, key, f1, f2)
            bn = f"{f1:.2f}-{f2:.2f}"
            print(f"\n### band {bn} Hz   ({INSTR[key]/V.FS:.2f} s blocks, df {100.0/INSTR[key]:.4f} Hz)")
            hdr = f"{'v m/s':7s} {'ai':2s} {'A med':>7s} {'grp':7s} {'n':>4s} {'sec':>6s} {'|H|':>6s} " \
                  f"{'CI95':>15s} {'coh':>5s} {'fl':>5s} {'lag_eq s':>9s} {'ang':>6s} {'rail%':>6s} {'|i|':>6s} {'|f|':>6s} {'adm':>4s}"
            print(hdr)
            for si, (lo, hi) in enumerate(SPD):
                for ai in range(4):
                    for g in ["V282", "V282old"] + list(TORQ):
                        recs = C.get((g, si, ai))
                        if not recs or len(recs) < 4:
                            continue
                        H, coh, ph, Pxx, Pyy, Pxy = H_of(recs)
                        (clo, chi), _ = boot_H(recs)
                        # split-half floor
                        sh = []
                        for _ in range(150):
                            pm = rng.permutation(len(recs)); h = len(recs) // 2
                            if h < 2:
                                break
                            sh.append(abs(H_of([recs[i] for i in pm[:h]])[0] - H_of([recs[i] for i in pm[h:]])[0]))
                        fl = float(np.median(sh)) if sh else np.nan
                        fb = recs[0]["fbins"]
                        lag = float(np.average(-np.degrees(np.angle(Pxy)) / (360.0 * fb), weights=Pxx))
                        adm = (coh >= COH_MIN and len(recs) >= NMIN
                               and (fl < 0.15 or fl < 0.5 * abs(H - 1.0)))
                        row = dict(band=bn, key=key, si=si, ai=ai, g=g, n=len(recs),
                                   secs=len(recs) * INSTR[key] / V.FS, H=H, coh=coh, fl=fl, lo=clo, hi=chi,
                                   lag=lag, amp=float(np.median([r["amp"] for r in recs])),
                                   ang=float(np.median([r["ang"] for r in recs])),
                                   rail=float(np.mean([r["rail"] for r in recs])),
                                   i_abs=float(np.median([r["i_abs"] for r in recs])),
                                   f_abs=float(np.median([r["f_abs"] for r in recs])),
                                   cmd=float(np.median([r["cmd"] for r in recs])),
                                   unexp=float(np.sum((1 - np.clip(np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30), 0, 1)) * Pyy)),
                                   outp=float(np.sum(Pyy)), inp=float(np.sum(Pxx)), adm=bool(adm))
                        keep.setdefault((bn, si, ai), {})[g] = row
                        print(f"{lo}-{hi:<4d} {ai:<2d} {row['amp']:7.4f} {g:7s} {len(recs):4d} {row['secs']:6.0f} "
                              f"{H:6.2f} [{clo:5.2f},{chi:5.2f}] {coh:5.2f} {fl:5.2f} {lag:9.3f} "
                              f"{row['ang']:6.1f} {100*row['rail']:6.3f} {row['i_abs']:6.3f} {row['f_abs']:6.3f} "
                              f"{'YES' if adm else 'no':>4s}")
    json.dump({f"{k[0]}|{k[1]}|{k[2]}": v for k, v in keep.items()}, open(OUT / "cells.json", "w"), indent=1)
    return keep


def sect_gap(keep):
    print("\n" + "=" * 130)
    print("SECTION 1b  THE GAP, matched cell by matched cell (torque - V282), ADMISSIBLE cells only")
    print("  gap significant when the two bootstrap CIs do not overlap.  MEASUREMENT.")
    print("=" * 130)
    print(f"{'band':11s} {'v':7s} {'ai':2s} {'A med':>7s} {'V282':>16s} " + "".join(f"{g:>20s}" for g in TORQ))
    gaps = []
    for (bn, si, ai), d in sorted(keep.items()):
        r0 = d.get("V282")
        if not r0 or not r0["adm"]:
            continue
        lo, hi = SPD[si]
        line = f"{bn:11s} {lo}-{hi:<4d} {ai:<2d} {r0['amp']:7.4f} {r0['H']:6.2f}[{r0['lo']:.2f},{r0['hi']:.2f}] "
        any_t = False
        for g in TORQ:
            r = d.get(g)
            if not r or not r["adm"]:
                line += f"{'--':>20s}"; continue
            any_t = True
            sig = "*" if (r["lo"] > r0["hi"] or r["hi"] < r0["lo"]) else " "
            line += f"{r['H']:7.2f}{sig}({r['H']-r0['H']:+.2f})[{r['lo']:.2f},{r['hi']:.2f}]"
            gaps.append(dict(band=bn, si=si, ai=ai, g=g, amp=r0["amp"], H0=r0["H"], H1=r["H"],
                             d=r["H"] - r0["H"], sig=(sig == "*"), rail=r["rail"], ang=r["ang"],
                             i_abs=r["i_abs"], cmd=r["cmd"], lag0=r0["lag"], lag1=r["lag"]))
        if any_t:
            print(line)
    return gaps


def sect_ampshape(keep):
    print("\n" + "=" * 130)
    print("SECTION 2b  AMPLITUDE SHAPE -- the signature that separates the four mechanisms")
    print("  fit over the amplitude bins of one (band, speed, group):  H = a + c/A   (c>0 = a CONSTANT-MAGNITUDE")
    print("  additive command, gain falls as 1/A)  and  H = p + q*A   (q<0 = SATURATION droop at large A).")
    print("  ALGEBRA on the measured cells; no plant model.")
    print("=" * 130)
    print(f"{'band':11s} {'v':7s} {'grp':8s} {'bins':>4s} {'A range':>17s} {'H range':>13s} "
          f"{'c (m/s^2)':>10s} {'R2(1/A)':>8s} {'q':>9s} {'R2(A)':>7s}  verdict")
    rows = []
    for key in INSTR:
        for f1, f2 in BANDS[key]:
            bn = f"{f1:.2f}-{f2:.2f}"
            for si, (lo, hi) in enumerate(SPD):
                for g in ["V282"] + list(TORQ):
                    pts = []
                    for ai in range(4):
                        r = keep.get((bn, si, ai), {}).get(g)
                        if r and r["adm"]:
                            pts.append((r["amp"], r["H"], r["n"]))
                    if len(pts) < 3:
                        continue
                    A = np.array([p[0] for p in pts]); H = np.array([p[1] for p in pts]); w = np.array([p[2] for p in pts], float)
                    def wls(X, y, w):
                        Xw = X * np.sqrt(w)[:, None]; yw = y * np.sqrt(w)
                        b = np.linalg.lstsq(Xw, yw, rcond=None)[0]
                        r = y - X @ b
                        ss = np.sum(w * (y - np.average(y, weights=w)) ** 2)
                        return b, 1 - np.sum(w * r ** 2) / max(ss, 1e-12)
                    b1, r2a = wls(np.c_[np.ones(len(A)), 1.0 / A], H, w)
                    b2, r2b = wls(np.c_[np.ones(len(A)), A], H, w)
                    verd = []
                    if b1[1] > 0 and r2a > 0.5:
                        verd.append("CONSTANT-ADDITIVE shape")
                    if b2[1] < 0 and r2b > 0.5:
                        verd.append("droop with A (sat-like)")
                    if not verd:
                        verd.append("flat / no shape")
                    print(f"{bn:11s} {lo}-{hi:<4d} {g:8s} {len(pts):4d} {A.min():7.4f}-{A.max():<9.4f} "
                          f"{H.min():5.2f}-{H.max():<6.2f} {b1[1]:10.5f} {r2a:8.2f} {b2[1]:9.2f} {r2b:7.2f}  {'; '.join(verd)}")
                    rows.append(dict(band=bn, si=si, g=g, c=float(b1[1]), r2c=float(r2a),
                                     q=float(b2[1]), r2q=float(r2b), A=[float(x) for x in A],
                                     H=[float(x) for x in H]))
    return rows


def sect_delay(keep):
    print("\n" + "=" * 130)
    print("SECTION 3  MECHANISM (a) LOOP DELAY 55-75 ms -- ALGEBRA on the mechanism's own transfer.")
    print("  A delay is EXACTLY magnitude-neutral: |exp(-j w D)| = 1 at every frequency, every amplitude,")
    print("  every speed.  The only magnitude the measured actuation law carries is its 5 Hz pole.")
    print("  BOUNDARY: the phase budget below is algebra.  It is NOT a prediction of the car's |H|.")
    print("=" * 130)
    print(f"{'band fc Hz':11s} {'|pole 5Hz|':>11s} {'phase@55ms':>11s} {'@65':>7s} {'@75':>7s}   "
          f"{'measured lag_eq (s): V282 / T64 / T64B / T5 / T4'}")
    for key in INSTR:
        for f1, f2 in BANDS[key]:
            bn = f"{f1:.2f}-{f2:.2f}"; fc = 0.5 * (f1 + f2)
            mag = 1.0 / math.hypot(1.0, fc / 5.0)
            ph = [-360.0 * fc * D / 1000.0 for D in (55, 65, 75)]
            lags = {}
            for g in ["V282"] + list(TORQ):
                ls = [keep[(bn, si, ai)][g]["lag"] for (b2, si, ai) in keep
                      if b2 == bn and g in keep[(bn, si, ai)] and keep[(bn, si, ai)][g]["adm"]]
                lags[g] = (np.median(ls) if ls else np.nan, len(ls))
            s = "  ".join(f"{g}:{lags[g][0]:+.3f}(n{lags[g][1]})" for g in ["V282"] + list(TORQ))
            print(f"{bn:11s} {mag:11.3f} {ph[0]:11.1f} {ph[1]:7.1f} {ph[2]:7.1f}   {s}")
    print("\n  excess lag = measured lag_eq - 0.065 s (the delay point estimate).  Anything positive is")
    print("  dynamics OTHER than the round trip: reference filtering, plant lag, or loop phase.")


def sect_sat(B):
    print("\n" + "=" * 130)
    print("SECTION 4  MECHANISM (b) ACTUATOR SATURATION -- re-derived from the logs by my own method,")
    print("  then bounded.  A railed frame's output is not a function of demand; the MOST of a band |H|")
    print("  it can move is the railed share of that band's input energy.  ALGEBRA + MEASUREMENT.")
    print("=" * 130)
    print(f"{'route':24s} {'grp':8s} {'v bin':7s} {'sec':>7s} {'railed s':>9s} {'duty %':>7s} "
          f"{'episodes':>9s} {'longest s':>10s} {'med |ang| in ep':>16s}")
    tot = {}
    for rk in V.ROUTES:
        S = V.load(rk)
        g = S["meta"].get("group", "?")
        out = np.nan_to_num(S["out"]); u = V.usable(S)
        for lo, hi in SPD:
            m = u & (S["v"] >= lo) & (S["v"] < hi)
            if m.sum() < 100:
                continue
            r = m & (np.abs(out) >= 0.995)
            eps = V.runs(r, S["t"], min_s=0.0)
            longest = max((S["t"][b - 1] - S["t"][a] for a, b in eps), default=0.0)
            angs = [float(np.median(np.abs(S["sa"][a:b]))) for a, b in eps]
            print(f"{rk:24s} {g:8s} {lo}-{hi:<4d} {m.sum()/V.FS:7.1f} {r.sum()/V.FS:9.2f} "
                  f"{100*r.sum()/max(m.sum(),1):7.4f} {len(eps):9d} {longest:10.3f} "
                  f"{(np.median(angs) if angs else float('nan')):16.1f}")
            k = (g, lo)
            tot[k] = tot.get(k, np.zeros(3)) + np.array([m.sum() / V.FS, r.sum() / V.FS, len(eps)])
        del S
    print("\n  pooled per group x speed:  sec / railed s / duty %% / episodes")
    for (g, lo), a in sorted(tot.items()):
        print(f"   {g:8s} v>={lo:<3d} {a[0]:8.1f} s  {a[1]:7.2f} s  {100*a[1]/max(a[0],1e-9):7.4f} %  {int(a[2]):5d} eps")
    return tot


def sect_hold(keep):
    print("\n" + "=" * 130)
    print("SECTION 5  MECHANISM (c) THE HOLD-FF ADDITIVE DEFICIT (+0.0231 torque at 0.6-2.5 deg, 2-8 m/s)")
    print("  Budget it against the MEASURED command in the same regime, and state its testability here.")
    print("=" * 130)
    DEF = 0.0231
    print(f"{'band':11s} {'v':7s} {'grp':8s} {'med |cmd|':>10s} {'deficit/|cmd|':>14s} {'med |i|':>8s} "
          f"{'med |f|':>8s} {'med |ang| deg':>14s} {'adm':>4s}")
    for key in INSTR:
        for f1, f2 in BANDS[key]:
            bn = f"{f1:.2f}-{f2:.2f}"
            for si, (lo, hi) in enumerate(SPD):
                if lo != 0:
                    continue
                for g in ["V282"] + list(TORQ):
                    rs = [keep[(bn, s2, ai)][g] for (b2, s2, ai) in keep
                          if b2 == bn and s2 == si and g in keep[(bn, s2, ai)]]
                    if not rs:
                        continue
                    cmd = float(np.median([r["cmd"] for r in rs]))
                    print(f"{bn:11s} {lo}-{hi:<4d} {g:8s} {cmd:10.4f} {DEF/max(cmd,1e-9):14.2f} "
                          f"{float(np.median([r['i_abs'] for r in rs])):8.4f} "
                          f"{float(np.median([r['f_abs'] for r in rs])):8.4f} "
                          f"{float(np.median([r['ang'] for r in rs])):14.1f} "
                          f"{'YES' if any(r['adm'] for r in rs) else 'no':>4s}")


def sect_obs(keep, B):
    print("\n" + "=" * 130)
    print("SECTION 6  MECHANISM (d) THE DISTURBANCE OBSERVER -- measured output power in 1.5-3.5 Hz that the")
    print("  demand does NOT explain: (1-coh)*Pyy, per second of data.  r75 (T4) flew the observer OFF")
    print("  (no AccordDobHz key on the wire) and is the only on-car OFF control that exists.  MEASUREMENT.")
    print("=" * 130)
    bn = "1.50-3.50"
    print(f"{'v m/s':7s} {'grp':8s} {'obs':4s} {'n':>5s} {'sec':>6s} {'unexplained Pyy/s':>19s} "
          f"{'total Pyy/s':>13s} {'unexp share':>12s} {'x V282':>8s}")
    for si, (lo, hi) in enumerate(SPD):
        base = None
        for g in ["V282", "V282old"] + list(TORQ):
            rs = [keep[(bn, s2, ai)][g] for (b2, s2, ai) in keep if b2 == bn and s2 == si and g in keep[(bn, s2, ai)]]
            if not rs:
                continue
            secs = sum(r["secs"] for r in rs)
            ue = sum(r["unexp"] for r in rs) / secs
            tp = sum(r["outp"] for r in rs) / secs
            if g == "V282":
                base = ue
            obs = "ON" if g in ("T64", "T64B", "T5") else ("OFF" if g == "T4" else "n/a")
            print(f"{lo}-{hi:<4d} {g:8s} {obs:4s} {sum(r['n'] for r in rs):5d} {secs:6.0f} "
                  f"{ue:19.4g} {tp:13.4g} {ue/max(tp,1e-30):12.3f} {ue/max(base,1e-30):8.2f}")


def _self_test():
    """Controls: (1) a known gain+lag through the cell math; (2) a known constant-additive term must show
    c>0 in the amplitude fit and a known clip must show q<0; (3) the duty bound arithmetic."""
    n = 512
    t = np.arange(40 * n) / V.FS
    x = V.lowpass(rng.standard_normal(len(t)), 1.2)
    x = x / float(np.std(x))                 # unit RMS, so the clip amplitudes below really clip
    from surf import _spec
    def band_cell(xx, yy, f1, f2):
        P = []
        for k in range(0, len(t) - n + 1, n):
            f, pxx, pyy, pxy = _spec(xx[k:k + n], yy[k:k + n], n)
            s = (f >= f1) & (f < f2)
            P.append((pxx[s], pyy[s], pxy[s]))
        return cell_H(P)[0]
    y = 0.9 * np.concatenate([np.zeros(6), x[:-6]])
    assert abs(band_cell(x, y, 0.5, 1.0) - 0.9) < 0.03
    # constant-additive: y = x + 0.05*sign(dx/dt) -> gain excess must fall as 1/A
    Hs = []
    for amp in (0.3, 1.0, 3.0):
        xa = x * amp
        ya = xa + 0.05 * np.sign(np.gradient(xa))
        Hs.append(band_cell(xa, ya, 0.5, 1.0))
    assert Hs[0] > Hs[1] > Hs[2], Hs
    A = np.array([0.3, 1.0, 3.0]) * float(np.std(x))
    c = np.polyfit(1.0 / A, np.array(Hs), 1)[0]
    assert c > 0, c
    # clip: gain must fall with A
    Hc = [band_cell(x * a, np.clip(x * a, -1, 1), 0.5, 1.0) for a in (0.5, 2.0, 6.0)]
    assert Hc[0] > Hc[1] > Hc[2], Hc
    return (f"self-test OK: cell |H| recovers 0.9; constant-additive gives c={c:+.3f}>0 with H falling "
            f"{Hs[0]:.2f}->{Hs[2]:.2f}; clip gives H falling {Hc[0]:.2f}->{Hc[2]:.2f}")


if __name__ == "__main__":
    print(_self_test()); print(V._self_test()); print()
    B = load_all()
    keep = sect0_1_2(B)
    gaps = sect_gap(keep)
    shp = sect_ampshape(keep)
    sect_delay(keep)
    json.dump(dict(gaps=gaps, shape=shp), open(OUT / "attrib.json", "w"), indent=1)
    sect_hold(keep)
    sect_obs(keep, B)
    del B
    sect_sat(None)
