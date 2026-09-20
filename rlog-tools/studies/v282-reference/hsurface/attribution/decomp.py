"""SERIES DECOMPOSITION of the goal metric, per route, from two logged signals at each cut.

  H_total = model desired lat accel      -> achieved (livePose yaw*v)     the operator's own metric
  H_fork  = model desired lat accel      -> the controller's SETPOINT     (torqueState.desiredLateralAccel)
  H_dwn   = the controller's SETPOINT    -> achieved                      everything downstream of the fork's
                                                                         demand shaping: EPS + rack + tyre
Both cuts are MEASURED (logged in, logged out).  H_total ~= H_fork * H_dwn and lag ~= lag_fork + lag_dwn is
then ARITHMETIC on three measurements, and the residual of that identity is printed so the reader can see
where the cascade stops holding (roll compensation and the learned latAccelOffset enter the SETPOINT but
not the model, so they show up as lost coherence in H_fork, never as a silent gain).

This is the cut the operator can act on: H_fork is fork toggles; H_dwn is the EPS image plus the car.
"""
import sys, json, math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1])); sys.path.insert(0, str(HERE))
import v282cmp as V
from surf import _spec, SPD, OUT

BANDS = [(0.10, 0.25, 2048), (0.25, 0.50, 2048), (0.50, 1.00, 512), (1.00, 2.00, 512)]
# flown, read from each route's own initData (wire_params.py + ffgain_ceiling/flown_params.json)
WIRE = {
    "00000064--ce6b0b0ebb": "V282  refFilt ABSENT LAF6.0 Kp0.9 fric0.01 Ki0.3 obs- SR16.33",
    "00000065--b9f78988bd": "V282  refFilt ABSENT LAF6.0 Kp0.9 fric0.01 Ki0.3 obs- SR16.33",
    "0000006c--2bc842dbac": "V282  refFilt ABSENT LAF6.0 Kp0.9 fric0.01 Ki0.3 obs- SR16.84",
    "0000006c--68c6e94b17": "T64   refFilt 0.06   LAF14  Kp1.0 fric0.00 Ki0.3 obs0.6 rlg0.001",
    "0000006d--05e83bb04f": "T64   refFilt 0.06   LAF14  Kp1.0 fric0.212 Ki0.3 obs0.6 rlg0.001",
    "0000006e--6ca3e014fd": "T64B  refFilt 0.06   LAF14  Kp1.0 fric0.00 Ki0.3 obs0.6 hold OFF",
    "00000076--d0b7ea7e4d": "T5    refFilt 0.12   LAF14  Kp1.0 fric0.00 Ki0.3 obs0.6 rlg0.001",
    "00000075--6c8687d5bd": "T4    refFilt 0.12   LAF14  Kp0.85 fric0.212 Ki0.6/2.5 obs OFF rlg0.0006",
    "00000039--f56039af87": "V282old refFilt ABSENT LAF2.11 Kp0.8 fric0.03 SR12.5",
    "0000003a--283a39a1d6": "V282old refFilt ABSENT LAF4.0  Kp0.8 fric0.03 SR12.5",
    "0000003c--927965c2b4": "V282old refFilt ABSENT LAF3.6  Kp0.8 fric0.03 SR12.5",
}
# the fork's own AccordRefFilter arithmetic (two cascaded first-order lags of RC each): group delay 2RC/(1+(wRC)^2)
REFRC = {"0000006c--68c6e94b17": 0.06, "0000006d--05e83bb04f": 0.06, "0000006e--6ca3e014fd": 0.06,
         "00000076--d0b7ea7e4d": 0.12, "00000075--6c8687d5bd": 0.12}


def pair(S, xk, yk, lo, hi, f1, f2, n):
    u = V.usable(S, lo, hi)
    x = np.nan_to_num(S[xk]); y = np.nan_to_num(S[yk])
    Pxx = Pyy = Pxy = None; nb = 0
    for a, b in V.runs(u, S["t"], min_s=n / V.FS):
        for k in range(a, b - n + 1, n):
            f, pxx, pyy, pxy = _spec(x[k:k + n], y[k:k + n], n)
            s = (f >= f1) & (f < f2)
            Pxx = pxx[s] if Pxx is None else Pxx + pxx[s]
            Pyy = pyy[s] if Pyy is None else Pyy + pyy[s]
            Pxy = pxy[s] if Pxy is None else Pxy + pxy[s]
            fb = f[s]; nb += 1
    if nb < 4:
        return None
    H = float(np.average(np.abs(Pxy) / Pxx, weights=Pxx))
    coh = float(np.average(np.abs(Pxy) ** 2 / (Pxx * Pyy), weights=Pxx))
    lag = float(np.average(-np.degrees(np.angle(Pxy)) / (360.0 * fb), weights=Pxx))
    return dict(H=H, coh=coh, lag=lag, n=nb, secs=nb * n / V.FS)


def main():
    print("=" * 152)
    print("SERIES DECOMPOSITION, per route.  H_fork = model -> controller setpoint;  H_dwn = setpoint -> achieved;")
    print("  H_tot = model -> achieved.  lag in s.  'refFF pred' = the fork's own AccordRefFilter PHASE delay")
    print("  2*atan(w*RC)/w at the band centre (two cascaded first-order lags of RC each, latcontrol_torque.py:319-326).")
    print("  PHASE delay, not group delay, because lag_eq below is -phase/(2*pi*f) -- ALGEBRA on the filter alone,")
    print("  printed next to the MEASURED lag_fork.  Nothing here is chained into a closed-loop prediction.")
    print("=" * 152)
    rows = []
    for rk in V.ROUTES:
        S = V.load(rk)
        g = S["meta"].get("group", "?")
        print(f"\n{rk}  {g:8s}  {WIRE.get(rk,'?')}")
        print(f"   {'band':11s} {'v m/s':7s} {'n/sec':>9s} | {'H_fork':>6s} {'coh':>5s} {'lag_f':>6s} "
              f"{'refFF pred':>10s} | {'H_dwn':>6s} {'coh':>5s} {'lag_d':>6s} | {'H_tot':>6s} {'coh':>5s} "
              f"{'lag_t':>6s} | {'H_f*H_d':>7s} {'lag_f+d':>7s}")
        for f1, f2, n in BANDS:
            fc = 0.5 * (f1 + f2); w = 2 * math.pi * fc
            for lo, hi in SPD:
                a = pair(S, "model", "setpoint", lo, hi, f1, f2, n)
                b = pair(S, "setpoint", "la_pose", lo, hi, f1, f2, n)
                c = pair(S, "model", "la_pose", lo, hi, f1, f2, n)
                if not (a and b and c):
                    continue
                rc = REFRC.get(rk)
                pred = (2 * math.atan(w * rc) / w) if rc else 0.0
                print(f"   {f1:.2f}-{f2:<6.2f} {lo}-{hi:<4d} {c['n']:4d}/{c['secs']:4.0f} | "
                      f"{a['H']:6.3f} {a['coh']:5.2f} {a['lag']:+6.3f} {pred:10.3f} | "
                      f"{b['H']:6.3f} {b['coh']:5.2f} {b['lag']:+6.3f} | "
                      f"{c['H']:6.3f} {c['coh']:5.2f} {c['lag']:+6.3f} | "
                      f"{a['H']*b['H']:7.3f} {a['lag']+b['lag']:+7.3f}")
                rows.append(dict(rk=rk, g=g, band=f"{f1:.2f}-{f2:.2f}", v=f"{lo}-{hi}", refrc=rc,
                                 pred_lag=pred, Hf=a["H"], cf=a["coh"], lf=a["lag"],
                                 Hd=b["H"], cd=b["coh"], ld=b["lag"], Ht=c["H"], ct=c["coh"], lt=c["lag"],
                                 n=c["n"], secs=c["secs"]))
        del S
    json.dump(rows, open(OUT / "decomp.json", "w"), indent=1)

    print("\n" + "=" * 152)
    print("SUMMARY: is the extra lag the FORK's demand shaping or the EPS+plant?  medians over speed bins,")
    print("  V282 = the reference (no AccordRefFilter key on the wire at all).")
    print("=" * 152)
    print(f"{'band':11s} {'group':9s} {'routes':6s} {'H_fork':>7s} {'lag_f':>7s} {'pred':>6s} "
          f"{'H_dwn':>7s} {'lag_d':>7s} {'H_tot':>7s} {'lag_t':>7s} {'d lag_f vs V282':>16s} {'d lag_d vs V282':>16s}")
    GR = {"V282": ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"],
          "T64_rc06": ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd"],
          "T5_rc12": ["00000076--d0b7ea7e4d"], "T4_rc12_obsOFF": ["00000075--6c8687d5bd"],
          "V282old": ["00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4"]}
    for f1, f2, n in BANDS:
        bn = f"{f1:.2f}-{f2:.2f}"
        base = None
        for gname, rks in GR.items():
            sel = [r for r in rows if r["band"] == bn and r["rk"] in rks and r["ct"] > 0.5]
            if len(sel) < 2:
                continue
            m = lambda k: float(np.median([r[k] for r in sel]))
            if gname == "V282":
                base = (m("lf"), m("ld"))
            dl = (m("lf") - base[0]) if base else float("nan")
            dd = (m("ld") - base[1]) if base else float("nan")
            print(f"{bn:11s} {gname:9s} {len(set(r['rk'] for r in sel)):6d} {m('Hf'):7.3f} {m('lf'):+7.3f} "
                  f"{m('pred_lag'):6.3f} {m('Hd'):7.3f} {m('ld'):+7.3f} {m('Ht'):7.3f} {m('lt'):+7.3f} "
                  f"{dl:+16.3f} {dd:+16.3f}")


if __name__ == "__main__":
    main()
