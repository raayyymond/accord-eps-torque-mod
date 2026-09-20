"""Final D_ctl / D_act / D_loop table per route and per speed bin, with route-cluster bootstrap CIs.

D_ctl  = carState logMonoTime -> sendcan logMonoTime of the command computed from THAT carState (value identity)
D_act  = lambda' + dd + pole_phase_delay(f) + sample_age   [+ unobserved post-427 stage]  = D_loop - D_ctl
D_loop = A + dd + pole_phase_delay(f)                      [+ the same unobserved term]
A      = 0x14A arrival -> 0xE4 on bus = D_ctl + age + lambda'.  pandad's read offset d cancels in A+dd and in
         lambda'+dd+age, so both composites are d-free.
"""
import json, math
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
V293 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd", "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]
V282 = ["00000064--ce6b0b0ebb", "0000006c--2bc842dbac"]
BINS = ("<8", "8-15", ">=15")
FREQS = (1.0, 2.0, 2.5, 3.0, 3.5)


def pole_ms(f, fc):
    return math.atan(f / fc) / (2 * math.pi * f) * 1e3 if np.isfinite(fc) else 0.0


def ci(vals, rng, n=4000):
    vals = np.asarray([v for v in vals if np.isfinite(v)], float)
    if len(vals) == 0:
        return (float("nan"), [float("nan")] * 2)
    bs = [np.mean(rng.choice(vals, len(vals))) for _ in range(n)]
    return float(vals.mean()), [round(x, 2) for x in np.percentile(bs, [2.5, 97.5])]


def main():
    rng = np.random.default_rng(7)
    rows = {}
    for r in V293 + V282:
        ch = json.load(open(HERE / "out" / f"chain_{r}.json"))
        tm = json.load(open(HERE / "out" / f"timing_{r}.json"))
        age = float(np.mean(tm["sample_age_at_carState_ms_pct(+d)"][1:4]))   # IQR mean, robust
        lam = tm["lambda_prime_mean_ms"]
        tapb = tm["B_tap_fit_diff"]["best"]
        rows[r] = dict(eps="V293" if r in V293 else "V282", n=ch["n_engaged_handsoff_identity"],
                       ident=ch["identity_rate_engaged"], D_ctl=ch["D_ctl_mean"],
                       D_ctl_bin={b: ch["by_speed"][b]["D_ctl_mean"] for b in BINS},
                       lam=lam, age=age, A=tm["A_mean_ms"],
                       A_bin={b: (tm["A_by_speed"][b]["mean"] if tm["A_by_speed"].get(b) else float("nan")) for b in BINS},
                       fc=tapb[0], dd=tapb[1], tap_r2=tapb[2],
                       tap_bin={b: (tm["B_tap_fit_by_speed"][b]["best"] if b in tm.get("B_tap_fit_by_speed", {}) else None) for b in BINS})
    print("route                     eps   n     D_ctl  age   lam'   A     tap(fc,dd,R2d)")
    for r, x in rows.items():
        print(f"{r} {x['eps']} {x['n']:6d} {x['D_ctl']:6.2f} {x['age']:5.2f} {x['lam']:5.2f} {x['A']:6.2f}"
              f"  fc={x['fc']} dd={x['dd']} R2={x['tap_r2']:.3f}")
    out = {"per_route": rows, "pooled_V293": {}}
    P = out["pooled_V293"]
    for k in ("D_ctl", "A", "lam", "age", "dd"):
        m, c = ci([rows[r][k] for r in V293], rng)
        P[k] = dict(per_route=[round(rows[r][k], 3) for r in V293], mean=round(m, 3), ci95=c)
    P["fc_hz_per_route"] = [rows[r]["fc"] for r in V293]
    print("\nPOOLED V293 (route cluster bootstrap)")
    for k in ("D_ctl", "A", "lam", "age", "dd"):
        print(f"  {k:6s} {P[k]['mean']:7.2f}  CI {P[k]['ci95']}   per route {P[k]['per_route']}")
    print(f"  fc     {P['fc_hz_per_route']} Hz")
    print("\nD_ctl per speed bin (pooled)")
    for b in BINS:
        m, c = ci([rows[r]["D_ctl_bin"][b] for r in V293], rng)
        P[f"D_ctl {b}"] = dict(mean=round(m, 2), ci95=c, per_route=[round(rows[r]["D_ctl_bin"][b], 2) for r in V293])
        print(f"  {b:5s} {m:6.2f}  CI {c}")
    print("\nD_act and D_loop floors, per frequency, pooled and per speed bin")
    for f in FREQS:
        da, dl = [], []
        for r in V293:
            x = rows[r]
            p = pole_ms(f, x["fc"])
            da.append(x["lam"] + x["dd"] + p + x["age"]); dl.append(x["A"] + x["dd"] + p)
        ma, ca = ci(da, rng); ml, cl = ci(dl, rng)
        P[f"D_act @{f}Hz"] = dict(mean=round(ma, 2), ci95=ca, per_route=[round(z, 2) for z in da])
        P[f"D_loop @{f}Hz"] = dict(mean=round(ml, 2), ci95=cl, per_route=[round(z, 2) for z in dl])
        line = f"  {f:4.1f} Hz  D_act {ma:6.2f} CI {ca}   D_loop {ml:6.2f} CI {cl}   |"
        for b in BINS:
            dlb = []
            for r in V293:
                x = rows[r]
                tb = x["tap_bin"][b] or [x["fc"], x["dd"]]
                if not np.isfinite(x["A_bin"][b]):
                    continue
                dlb.append(x["A_bin"][b] + tb[1] + pole_ms(f, tb[0]))
            mb, cb = ci(dlb, rng)
            P[f"D_loop {b} @{f}Hz"] = dict(mean=round(mb, 2), ci95=cb, per_route=[round(z, 2) for z in dlb])
            dab = [z - rows[V293[i]]["D_ctl_bin"][b] for i, z in enumerate(dlb)]
            mab, cab = ci(dab, rng)
            P[f"D_act {b} @{f}Hz"] = dict(mean=round(mab, 2), ci95=cab, per_route=[round(z, 2) for z in dab])
            line += f" {b}: loop {mb:5.1f}{cb} act {mab:5.1f}{cab} |"
        print(line)
    # V282 software chain, same links
    print("\nV282 control (same software chain, different EPS):")
    for r in V282:
        x = rows[r]
        print(f"  {r}  D_ctl {x['D_ctl']:.2f}  age {x['age']:.2f}  lam' {x['lam']:.2f}  A {x['A']:.2f}"
              f"  tap fit fc={x['fc']} dd={x['dd']} R2diff={x['tap_r2']:.3f}  (NO pole+delay law fits)")
        out.setdefault("V282", {})[r] = dict(D_ctl=x["D_ctl"], A=x["A"], age=x["age"], lam=x["lam"],
                                             tap_best=[x["fc"], x["dd"], x["tap_r2"]])
    json.dump(out, open(HERE / "out" / "final_table.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
