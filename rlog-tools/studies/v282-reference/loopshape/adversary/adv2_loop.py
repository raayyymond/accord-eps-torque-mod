"""ADVERSARY 2 -- attack the loop identification itself.

The fork's outer loop closes on the CONTROLLER'S OWN measurement: error = setpoint - measurement, so
    T = Y/Z  (complementary sensitivity),  S = (Z-Y)/Z = 1 - T  (sensitivity),  L = T/(1-T) = T/S.
That makes L recoverable from logged data BY ALGEBRA -- but only up to (a) Z being exogenous and
(b) the amplification 1/|S| that the inversion applies to every error in T.  Both are measured here.

Everything is per frequency bin, complex (phasor-summed cross-spectra), never magnitude-averaged, because
phase is the whole question.  Positive control first.
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V

FS = 100.0
NPS = 4096                     # 40.96 s -> df 0.0244 Hz
BANDS = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20)]
FAM = {"00000064--ce6b0b0ebb": "V282", "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
       "00000039--f56039af87": "V282old", "0000003a--283a39a1d6": "V282old", "0000003c--927965c2b4": "V282old",
       "0000006c--68c6e94b17": "TORQ", "0000006d--05e83bb04f": "TORQ", "0000006e--6ca3e014fd": "TORQ",
       "00000075--6c8687d5bd": "TORQ", "00000076--d0b7ea7e4d": "TORQ"}


def xspec(segs):
    """Phasor-summed cross/auto spectra over segments. segs = [(x, y), ...]. Returns f, Pxx, Pyy, Pxy(complex)."""
    Pxx = Pyy = Pxy = None; fr = None; nseg = 0
    for x, y in segs:
        if len(x) < NPS:
            continue
        xs, ys = x - x.mean(), y - y.mean()
        f, pxx = signal.welch(xs, FS, nperseg=NPS, noverlap=NPS // 2)
        _, pyy = signal.welch(ys, FS, nperseg=NPS, noverlap=NPS // 2)
        _, pxy = signal.csd(xs, ys, FS, nperseg=NPS, noverlap=NPS // 2)
        Pxx = pxx if Pxx is None else Pxx + pxx
        Pyy = pyy if Pyy is None else Pyy + pyy
        Pxy = pxy if Pxy is None else Pxy + pxy
        fr = f; nseg += 1
    return fr, Pxx, Pyy, Pxy, nseg


def _selftest():
    """A known loop: plant G = k/(s(tau s+1)) with delay D, unity feedback, driven by a coloured reference plus
    an output disturbance. Recover |L| and the phase margin from Z and Y alone."""
    rng = np.random.default_rng(7)
    n = int(600 * FS); dt = 1 / FS
    D = 6                                     # 60 ms
    k, tau = 3.0, 0.10
    z = V.lowpass(rng.standard_normal(n), 0.9) * 2.0
    d = V.lowpass(rng.standard_normal(n), 2.0) * 0.30      # output disturbance, independent of z
    y = np.zeros(n); x1 = 0.0; x2 = 0.0; ub = np.zeros(n)
    for i in range(1, n):
        e = z[i] - y[i - 1]
        ub[i] = e
        u = ub[i - D] if i >= D else 0.0
        x1 += dt * (u - x1) / tau                # 1/(tau s + 1)
        x2 += dt * k * x1                        # k/s
        y[i] = x2 + d[i]
    segs = [(z[j:j + NPS], y[j:j + NPS]) for j in range(0, n - NPS, NPS)]
    f, Pzz, Pyy, Pzy, ns = xspec(segs)
    T = Pzy / Pzz
    L = T / (1 - T)
    # true L(jw) = k exp(-j w D dt) / (j w (1 + j w tau))
    w = 2 * np.pi * f[1:]
    Lt = k * np.exp(-1j * w * D * dt) / (1j * w * (1 + 1j * w * tau))
    sel = (f[1:] > 0.1) & (f[1:] < 2.0)
    em = np.abs(np.abs(L[1:][sel]) - np.abs(Lt[sel])) / np.abs(Lt[sel])
    ep = np.abs(np.degrees(np.angle(L[1:][sel] / Lt[sel])))
    # crossover + PM, true vs recovered
    def cross(ff, LL):
        m = np.abs(LL); i = np.where(m < 1)[0]
        if not len(i) or i[0] == 0: return np.nan, np.nan
        i = i[0]
        fc = np.interp(0.0, [np.log(m[i]), np.log(m[i - 1])], [ff[i], ff[i - 1]])
        ph = np.interp(fc, ff, np.unwrap(np.angle(LL)))
        return fc, 180 + np.degrees(ph)
    fc_t, pm_t = cross(f[1:], Lt); fc_r, pm_r = cross(f[1:], L[1:])
    print(f"  SELF-TEST closed-loop L recovery: |L| median rel err {np.median(em)*100:.1f}% , "
          f"phase median err {np.median(ep):.1f} deg over 0.1-2 Hz")
    print(f"  SELF-TEST crossover  true {fc_t:.3f} Hz PM {pm_t:.1f} deg  ->  recovered {fc_r:.3f} Hz PM {pm_r:.1f} deg")
    assert np.median(em) < 0.12 and np.median(ep) < 8.0, "loop recovery control FAILED"
    return True


def run():
    print("=" * 120)
    print("POSITIVE CONTROL (must pass before any real number counts)")
    print("=" * 120)
    _selftest()

    out = {}
    for rk, fam in FAM.items():
        p = V.CACHE / f"{rk}.npz"
        if not p.exists():
            continue
        S = V.load(rk)
        m = V.usable(S, 15.0)
        segs = {k: [] for k in ["ZY", "ZM", "MY", "XZ", "ZE"]}
        amps = []
        for a, b in V.runs(m, S["t"], min_s=NPS / FS):
            X = np.nan_to_num(S["model"][a:b]); Z = np.nan_to_num(S["setpoint"][a:b])
            M = np.nan_to_num(S["sa"][a:b]);     Y = np.nan_to_num(S["la_act"][a:b])
            E = Z - Y
            for k, (u, v_) in dict(ZY=(Z, Y), ZM=(Z, M), MY=(M, Y), XZ=(X, Z), ZE=(Z, E)).items():
                segs[k].append((u, v_))
            amps.append(float(np.std(Z)))
        if not segs["ZY"]:
            continue
        rec = dict(fam=fam, nrun=len(segs["ZY"]), amp=float(np.median(amps)))
        for k, sg in segs.items():
            f, Pxx, Pyy, Pxy, ns = xspec(sg)
            if f is None:
                rec[k] = None; continue
            rec["f"] = f
            rec[k] = dict(H=Pxy / np.maximum(Pxx, 1e-30), coh=np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30),
                          Pxx=Pxx, ns=ns)
        out[rk] = rec
        del S
    return out


def band_agg(rec, key, f1, f2):
    f = rec["f"]; s = (f >= f1) & (f < f2)
    d = rec[key]
    if d is None:
        return None
    H = d["H"][s]; w = d["Pxx"][s]
    return dict(mag=float(np.average(np.abs(H), weights=w)),
                phase=float(np.degrees(np.angle(np.average(H, weights=w)))),
                coh=float(np.average(d["coh"][s], weights=w)))


if __name__ == "__main__":
    R = run()
    print("\n" + "=" * 120)
    print("A.  THE LOOP, MEASURED.  >=15 m/s, runs >= 41 s.  T = Y/Z (complementary sensitivity),")
    print("    S = (Z-Y)/Z = 1-T (sensitivity), L = T/S.  |1/S| is the factor by which the L-inversion")
    print("    MULTIPLIES every relative error in T -- the identification's condition number.")
    print("=" * 120)
    print(f"{'route':24s} {'fam':8s} {'band':10s} | {'|T|':>6s} {'<T':>7s} {'coh':>5s} | {'|S|':>6s} | "
          f"{'|L|':>7s} {'<L':>7s} | {'cond=1/|S|':>10s}")
    fams = {}
    for rk, rec in R.items():
        for (f1, f2) in BANDS:
            f = rec["f"]; s = (f >= f1) & (f < f2)
            T = rec["ZY"]["H"][s]; w = rec["ZY"]["Pxx"][s]
            Sv = 1 - T
            L = T / Sv
            aT = np.average(T, weights=w); aS = np.average(Sv, weights=w); aL = np.average(L, weights=w)
            coh = float(np.average(rec["ZY"]["coh"][s], weights=w))
            cond = float(np.average(1 / np.abs(Sv), weights=w))
            print(f"{rk:24s} {rec['fam']:8s} {f1:.2f}-{f2:.2f} | {abs(aT):6.3f} {np.degrees(np.angle(aT)):7.1f} "
                  f"{coh:5.2f} | {abs(aS):6.3f} | {abs(aL):7.3f} {np.degrees(np.angle(aL)):7.1f} | {cond:10.2f}")
            fams.setdefault((rec["fam"], f1), []).append((abs(aT), np.degrees(np.angle(aT)), abs(aS), abs(aL),
                                                          np.degrees(np.angle(aL)), cond, coh))
    print("\n  FAMILY MEDIANS")
    print(f"  {'fam':8s} {'band':10s} | {'|T|':>6s} {'<T':>7s} | {'|S|':>6s} | {'|L|':>7s} {'<L':>7s} "
          f"{'PM-if-LTI':>10s} | {'cond':>6s}")
    for (fam, f1), v in sorted(fams.items()):
        a = np.median(np.array(v), axis=0)
        print(f"  {fam:8s} {f1:.2f}-{[b for b in BANDS if b[0]==f1][0][1]:.2f} | {a[0]:6.3f} {a[1]:7.1f} | "
              f"{a[2]:6.3f} | {a[3]:7.3f} {a[4]:7.1f} {180+a[4]:10.1f} | {a[5]:6.2f}")

    print("\n" + "=" * 120)
    print("B.  IS THE DEFICIT GAIN OR PHASE?  Leg magnitudes and phases, same runs, same estimator.")
    print("=" * 120)
    print(f"  {'fam':8s} {'band':10s} | {'|X->Z|':>7s} {'<':>6s} | {'|Z->M|':>7s} {'<':>6s} {'coh':>5s} | "
          f"{'|M->Y|':>7s} {'<':>6s} | {'|Z->Y|':>7s} {'<':>6s}")
    for fam in ["V282", "V282old", "TORQ"]:
        for (f1, f2) in BANDS:
            rows = [r for r in R.values() if r["fam"] == fam]
            vals = []
            for r in rows:
                v = [band_agg(r, k, f1, f2) for k in ["XZ", "ZM", "MY", "ZY"]]
                if any(x is None for x in v):
                    continue
                vals.append([v[0]["mag"], v[0]["phase"], v[1]["mag"], v[1]["phase"], v[1]["coh"],
                             v[2]["mag"], v[2]["phase"], v[3]["mag"], v[3]["phase"]])
            if not vals:
                continue
            a = np.median(np.array(vals), axis=0)
            print(f"  {fam:8s} {f1:.2f}-{f2:.2f} | {a[0]:7.3f} {a[1]:6.1f} | {a[2]:7.3f} {a[3]:6.1f} {a[4]:5.2f} | "
                  f"{a[5]:7.4f} {a[6]:6.1f} | {a[7]:7.3f} {a[8]:6.1f}")
    np.save(HERE / "adv2_cache.npy", np.array([1]))
