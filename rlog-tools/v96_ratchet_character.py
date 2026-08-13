#!/usr/bin/env python3
r"""What KIND of thing is the oscillation the operator elicits?  Four questions the time-domain
figures raise but do not answer, each with its own control.

Q1  Is it in the WHEEL, or only in the TORSION BAR?  6-9 Hz content of steering ANGLE and ANGLE
    RATE (0x14A) beside the torque sensor (0x18F).  Torque-only => the column is winding between
    the driver's hands and the motor; angle too => the rim is physically moving.
Q2  Is it a SATURATION artefact?  Split engaged elicitation time by whether the LKAS command is
    on its +-4096 rail.
Q3  Does its amplitude track the LKAS COMMAND MAGNITUDE?  (Decides whether a pure gain cut is even
    the right shape of lever.)
Q4  Pooled effect size across both routes, bootstrapped over EPISODES, with the negative control
    band 15-22 Hz carried alongside so a broadband change cannot masquerade as a 6-9 Hz one.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import welch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
from v96_elicitation_finder import load, band_env, mmss, FS  # noqa: E402
from v96_probe_vs_ratchet import signed_lane  # noqa: E402
from v96_transitions_and_stats import boot_ratio  # noqa: E402

CACHE = {r: ROOT / "analysis-2020accord" / f"_cache_r{r}" / f"r{r}.npz" for r in ("7e", "7f")}
BANDS = {"6-9 Hz (ratchet)": (6.0, 9.0), "15-22 Hz (control)": (15.0, 22.0),
         "1-3 Hz (control)": (1.0, 3.0)}


def brms(x, fs, lo, hi):
    if len(x) < int(fs * 1.5):
        return float("nan")
    f, P = welch(x - np.nanmean(x), fs=fs, nperseg=min(len(x), int(fs * 4)))
    m = (f >= lo) & (f <= hi)
    return float(np.sqrt(np.trapezoid(P[m], f[m]))) if m.any() else float("nan")


def episodes(D, blocks_, min_sec=1.5):
    t, lat = D["t"], D["lat"]
    inb = np.zeros(len(t), bool)
    for b in blocks_:
        inb |= (t >= b["t0"]) & (t <= b["t1"])
    out, state, start = [], None, None
    for i in range(len(t)):
        s = (bool(inb[i]), bool(lat[i]))
        if s != state:
            if state is not None and state[0] and t[i] - t[start] >= min_sec:
                out.append((start, i, state[1]))
            state, start = s, i
    return out


if __name__ == "__main__":
    bl_all = json.loads((ROOT / "analysis-2020accord" / "_r7e_r7f_elicitations.json").read_text())
    rows = []
    for r in ("7e", "7f"):
        D = load(r)
        env = band_env(D["tq"])
        z = np.load(CACHE[r], allow_pickle=True)
        for a, b, eng in episodes(D, bl_all[r]):
            rec = dict(route=r, t0=float(D["t"][a]), t1=float(D["t"][b - 1]), eng=bool(eng),
                       dur=float(D["t"][b - 1] - D["t"][a]), v=float(D["v"][a:b].mean()),
                       tq_absmed=float(np.median(np.abs(D["tq"][a:b]))),
                       cmd_absmed=float(np.median(np.abs(D["cmd"][a:b]))),
                       cmd_rail=float(np.mean(np.abs(D["cmd"][a:b]) >= 4090)),
                       env_med=float(np.median(env[a:b])))
            for nm, (lo, hi) in BANDS.items():
                rec[f"tq[{nm}]"] = brms(D["tq"][a:b], FS, lo, hi)
                rec[f"ang[{nm}]"] = brms(D["ang"][a:b], FS, lo, hi)
                rec[f"rate[{nm}]"] = brms(D["rate_c"][a:b], FS, lo, hi)
                rec[f"wang[{nm}]"] = brms(D["wang"][a:b], FS, lo, hi)
            rows.append(rec)
    E = [x for x in rows if x["eng"]]
    M = [x for x in rows if not x["eng"]]
    print(f"pooled episodes: {len(E)} engaged ({sum(x['dur'] for x in E):.0f} s)  "
          f"{len(M)} LKAS-off ({sum(x['dur'] for x in M):.0f} s)")
    print(f"  control  speed        engaged {np.median([x['v'] for x in E]):5.1f} km/h   "
          f"off {np.median([x['v'] for x in M]):5.1f} km/h")
    print(f"  control  |tq| median  engaged {np.median([x['tq_absmed'] for x in E]):5.0f} ct     "
          f"off {np.median([x['tq_absmed'] for x in M]):5.0f} ct")

    print("\nQ1/Q4  band RMS by signal and band, engaged vs LKAS off, episode bootstrap")
    print(f"  {'signal':<16}{'band':<20}{'engaged':>10}{'LKAS off':>10}{'ratio':>9}  95% CI")
    q = {}
    for sig, lab in (("tq", "driver torque ct"), ("ang", "steer angle deg"),
                     ("wang", "wheel angle deg"), ("rate", "angle rate 0x14A")):
        for nm in BANDS:
            k = f"{sig}[{nm}]"
            ra, ci = boot_ratio([x[k] for x in E], [x[k] for x in M])
            me = float(np.nanmedian([x[k] for x in E]))
            mm = float(np.nanmedian([x[k] for x in M]))
            q[k] = dict(engaged=me, off=mm, ratio=ra, ci=ci)
            print(f"  {lab:<18}{nm:<20}{me:10.3f}{mm:10.3f}{ra:9.1f}x  "
                  f"[{ci[0]:.1f}, {ci[1]:.1f}]")

    print("\nQ2  is it the +-4096 rail?  engaged episodes split by command-rail duty")
    hi = [x for x in E if x["cmd_rail"] >= 0.30]
    lo = [x for x in E if x["cmd_rail"] < 0.30]
    for nm, s in (("rail >=30% of episode", hi), ("rail <30%", lo)):
        if s:
            print(f"  {nm:<24} n={len(s):>2}  6-9 Hz torque RMS median "
                  f"{np.nanmedian([x['tq[6-9 Hz (ratchet)]'] for x in s]):8.1f} ct   "
                  f"|cmd| med {np.median([x['cmd_absmed'] for x in s]):6.0f}")

    print("\nQ3  does 6-9 Hz amplitude track |LKAS command|?  (engaged episodes only)")
    x = np.array([e["cmd_absmed"] for e in E], float)
    y = np.array([e["tq[6-9 Hz (ratchet)]"] for e in E], float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() >= 4:
        rho = float(np.corrcoef(np.log(x[m] + 1), np.log(y[m] + 1))[0, 1])
        print(f"  corr(log |cmd|, log 6-9 Hz RMS) = {rho:+.3f} over n={int(m.sum())} episodes "
              f"— n is small; treat as a DIRECTION, not an estimate")
    (ROOT / "analysis-2020accord" / "_r7e_r7f_character.json").write_text(
        json.dumps(dict(episodes=rows, bands=q), indent=1, default=float))
