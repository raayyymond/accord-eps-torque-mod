# -*- coding: utf-8 -*-
"""r1 -- identify each route's PLANT anchor and the quantities the repaired controller needs.

Per (route, speed bin), engaged + hands-off only:
  * H1(f) = S_uy / S_uu  from the logged command cs_out (+left torque, units of the [-1,1] output)
    to the measured steering angle sa_deg.  ANCHOR = |H1| over 0.15-0.30 Hz  (deg per torque).
  * coherence there (the prereg's coh(Z,M) analogue).
  * c(v) = measurement per degree, from the logged actualLateralAccel vs sa_deg (static map).
  * A = sqrt(2) * rms(pid_log.error) -- the amplitude the saturating friction element sees.
  * the fraction of frames whose relay argument |err + 0.22*jerk| exceeds the 0.30 threshold.
  * window list with the contiguous-run id, so the bootstrap can cluster on runs.

Nothing here knows anything about controllers.  One route at a time.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CACHE = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref")
DT = 0.01
NW = 2048          # 20.48 s -> df = 0.0488 Hz
HOP = 1024
ANCHOR = (0.15, 0.30)
BINS = [("15-22", 15.0, 22.0), ("22+", 22.0, 99.0)]
ROUTES = ["00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4",
          "00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac",
          "0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
          "00000070--717f5a7866", "00000071--f2c9d073a3", "00000072--8001fc3048",
          "00000073--79fd149dd8", "00000075--6c8687d5bd", "00000076--d0b7ea7e4d"]


def grid(rt):
    D = np.load(CACHE / f"{rt}.npz", allow_pickle=True)
    t0 = max(D["t_cs"][0], D["t_cst"][0], D["t_cc"][0])
    t1 = min(D["t_cs"][-1], D["t_cst"][-1], D["t_cc"][-1])
    t = np.arange(t0, t1, DT)
    g = {"t": t}
    for src, names in (("t_cs", ["cs_err", "cs_out", "cs_la_act", "cs_la_des", "cs_la_jerk", "cs_sat", "cs_f", "cs_p", "cs_i"]),
                       ("t_cst", ["vego", "sa_deg", "sr_deg", "spress"]),
                       ("t_cc", ["lat_active"])):
        for n in names:
            g[n] = np.interp(t, D[src], D[n])
    D.close()
    return g


def runs_of(mask, minlen):
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i >= minlen:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def spec(*sigs):
    w = np.hanning(NW)
    return [np.fft.rfft((s - s.mean()) * w) for s in sigs]


def main():
    store = {}
    fq = np.fft.rfftfreq(NW, DT)
    ab = (fq >= ANCHOR[0]) & (fq <= ANCHOR[1])
    for rt in ROUTES:
        g = grid(rt)
        eng = (g["lat_active"] > 0.5) & (g["spress"] < 0.5)
        for nm, lo, hi in BINS:
            m = eng & (g["vego"] >= lo) & (g["vego"] < hi)
            rr = runs_of(m, NW)
            Us, Ys, Ws, rid, vmed = [], [], [], [], []
            for k, (i, j) in enumerate(rr):
                for s in range(i, j - NW + 1, HOP):
                    U, Y, W = spec(g["cs_out"][s:s + NW], g["sa_deg"][s:s + NW], g["cs_la_des"][s:s + NW])
                    Us.append(U); Ys.append(Y); Ws.append(W); rid.append(k)
                    vmed.append(float(np.median(g["vego"][s:s + NW])))
            if len(Us) < 4:
                continue
            U = np.array(Us); Y = np.array(Ys); W = np.array(Ws); rid = np.array(rid)
            Suu = np.mean(np.abs(U) ** 2, axis=0)
            Suy = np.mean(np.conj(U) * Y, axis=0)
            Syy = np.mean(np.abs(Y) ** 2, axis=0)
            Sww = np.mean(np.abs(W) ** 2, axis=0)
            Swu = np.mean(np.conj(W) * U, axis=0)
            Swy = np.mean(np.conj(W) * Y, axis=0)
            H1 = Suy / Suu
            Hiv = Swy / Swu
            coh = np.abs(Suy) ** 2 / np.maximum(Suu * Syy, 1e-300)
            coh_wu = np.abs(Swu) ** 2 / np.maximum(Sww * Suu, 1e-300)
            coh_wy = np.abs(Swy) ** 2 / np.maximum(Sww * Syy, 1e-300)
            # static angle -> measurement map, in-bin frames
            c = -float(np.polyfit(g["sa_deg"][m], g["cs_la_act"][m], 1)[0])
            r2 = float(np.corrcoef(g["sa_deg"][m], g["cs_la_act"][m])[0, 1] ** 2)
            err = g["cs_err"][m]
            arg = err + 0.22 * g["cs_la_jerk"][m]
            store[f"{rt}|{nm}"] = dict(
                route=rt, bin=nm, n_win=len(Us), n_run=len(rr), secs=float(m.sum() * DT),
                v=float(np.median(g["vego"][m])),
                anchor=float(np.abs(np.mean(Hiv[ab]))),
                anchor_ph=float(np.degrees(np.angle(np.mean(Hiv[ab])))),
                anchor_dir=float(np.abs(np.mean(H1[ab]))),
                anchor_dir_ph=float(np.degrees(np.angle(np.mean(H1[ab])))),
                coh=float(np.mean(coh_wu[ab])), coh_wy=float(np.mean(coh_wy[ab])),
                coh_uy=float(np.mean(coh[ab])),
                H1_re=H1.real.tolist(), H1_im=H1.imag.tolist(),
                Hiv_re=Hiv.real.tolist(), Hiv_im=Hiv.imag.tolist(),
                coh_f=coh.tolist(), rid=rid.tolist(),
                wSwu_re=(np.conj(W[:, ab]) * U[:, ab]).real.tolist(),
                wSwu_im=(np.conj(W[:, ab]) * U[:, ab]).imag.tolist(),
                wSwy_re=(np.conj(W[:, ab]) * Y[:, ab]).real.tolist(),
                wSwy_im=(np.conj(W[:, ab]) * Y[:, ab]).imag.tolist(),
                Suu=Suu.tolist(), Suy_re=Suy.real.tolist(), Suy_im=Suy.imag.tolist(),
                Swu_re=Swu.real.tolist(), Swu_im=Swu.imag.tolist(),
                Swy_re=Swy.real.tolist(), Swy_im=Swy.imag.tolist(), Sww=Sww.tolist(),
                Syy=Syy.tolist(),
                c=c, c_r2=r2,
                A_rms=float(np.sqrt(np.mean(err ** 2))), A_p90=float(np.percentile(np.abs(err), 90)),
                sat_frac=float(np.mean(np.abs(arg) > 0.30)),
                sat_frac_err=float(np.mean(np.abs(err) > 0.30)),
                clip_frac=float(np.mean(g["cs_sat"][m] > 0.5)),
                sa_rms=float(np.std(g["sa_deg"][m])), u_rms=float(np.std(g["cs_out"][m])))
            S = store[f"{rt}|{nm}"]
            print(f"{rt}|{nm:6s} nw {len(Us):3d} nr {len(rr):2d} {m.sum()*DT:6.0f}s "
                  f"v {S['v']:5.1f} IV {S['anchor']:7.2f}/{S['anchor_ph']:+6.1f} "
                  f"dir {S['anchor_dir']:7.2f}/{S['anchor_dir_ph']:+6.1f} "
                  f"coh_wu {S['coh']:.3f} coh_wy {S['coh_wy']:.3f} "
                  f"c {c:.4f} Arms {S['A_rms']:.3f} sat {S['sat_frac']:.3f}")
            sys.stdout.flush()
        del g
    json.dump(dict(f=fq.tolist(), nw=NW, dt=DT, anchor=list(ANCHOR), cells=store),
              open(HERE / "out" / "r1_ident.json", "w"))
    print("\nwrote", HERE / "out" / "r1_ident.json")


if __name__ == "__main__":
    main()
