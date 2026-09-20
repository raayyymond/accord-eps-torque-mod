"""Collect the e4_chain outputs into one table (out/summary.json + stdout).

Composite, per route and speed bin (all on the can-batch clock, pandad's read offset d cancels in D_loop):
  D_ctl            carState logMonoTime -> sendcan of the command computed from it     (chain_software, value identity)
  lambda'          sendcan -> 0xE4 on bus (+d)                                         (chain_timing, FIFO order)
  A                0x14A arrival -> 0xE4 on bus                                        (chain_timing, d-free)
  tap law          0xE4 on bus -> firmware lane torque gp-0x6b38 (0x1AB): dd + 1st-order pole fc (chain_timing tap fit)
  age              0x14A arrival -> carState logMonoTime (-d)
  D_act(f)   = lambda' + dd + pole_phase_delay(f) + age            [+ post-tap stage and in-EPS sensing age: NOT observed]
  D_loop(f)  = A + dd + pole_phase_delay(f)                        [+ same unobserved terms]
Route-cluster bootstrap over the V293 routes for the pooled CI.
"""
import json, math
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
V293 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd", "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]
V282 = ["00000064--ce6b0b0ebb", "0000006c--2bc842dbac"]
FREQS = (1.0, 2.0, 2.5, 3.0, 3.5, 4.0)
BINS = ("<8", "8-15", ">=15")


def pole_delay_ms(f, fc):
    if not np.isfinite(fc):
        return 0.0
    return math.atan(f / fc) / (2 * math.pi * f) * 1e3


def load(p):
    p = HERE / "out" / p
    return json.load(open(p)) if p.exists() else None


def main():
    S = {}
    for r in V293 + V282:
        ch = load(f"chain_{r}.json"); tm = load(f"timing_{r}.json"); sl = load(f"sensor_lags_{r}.json")
        ct = load(f"controls_{r}.json")
        if ch is None or tm is None:
            S[r] = None; continue
        row = dict(eps="V293" if r in V293 else "V282")
        row["n_frames"] = ch["n_engaged_handsoff_identity"]
        row["identity_rate"] = ch["identity_rate_engaged"]
        row["controls_consumes_carState_lag0_sign_agree"] = ch["controlsState_consumes_carState_lag"]["0"]["sign_agree"]
        row["carOutput_is_previous_carControl"] = ch["carOutput_torque_eq_Lth_recent_carControl"]["1"]
        row["carState_loops_stale"] = ch["carState_loops_stale_hist"]
        row["D_ctl_mean"] = ch["D_ctl_mean"]; row["D_ctl_pct"] = ch["D_ctl_carState_to_sendcan_ms_pct"]
        row["D_ctl_by_speed"] = {k: v["D_ctl_mean"] for k, v in ch["by_speed"].items()}
        row["carState_minus_batch_ms"] = ch["carState_minus_its_can_batch_ms"]
        row["controlsState_minus_carState_ms"] = ch["controlsState_minus_carState_ms"]
        row["sendcan_to_echo_batch_mean"] = ch["sendcan_to_echo_mean"]
        row["lambda_prime_mean"] = tm["lambda_prime_mean_ms"]; row["lambda_prime_q"] = tm["lambda_prime_quantiles_ms"]
        row["A_mean"] = tm["A_mean_ms"]; row["A_by_speed"] = tm["A_by_speed"]
        row["age_pct"] = tm["sample_age_at_carState_ms_pct(+d)"]
        row["clock14A"] = tm["clock_14A"]; row["clock_ppm"] = tm["clock_14A_ppm"]
        row["e18_minus_e14"] = tm.get("e18_minus_prev_e14_ms"); row["eAB_minus_e14"] = tm.get("eAB_minus_prev_e14_ms")
        bd = tm.get("B_tap_fit_diff", {}).get("best"); bl = tm.get("B_tap_fit_all", {}).get("best")
        row["tap_diff_best"] = bd; row["tap_level_best"] = bl
        row["tap_diff_dd_per_fc"] = tm.get("B_tap_fit_diff", {}).get("best_dd_per_fc")
        row["tap_by_speed"] = {k: v["best"] for k, v in tm.get("B_tap_fit_by_speed", {}).items()}
        if sl:
            row["rate14_lag_vs_grad_angle_ms_1-4Hz"] = -sl["grad(angle14) -> rate14"]["1-4Hz"]["lag_ms"]
            row["rate14_lag_vs_grad_angle_ms_2-8Hz"] = -sl["grad(angle14) -> rate14"]["2-8Hz"]["lag_ms"]
            row["rate18_minus_rate14_ms_1-4Hz"] = -sl["rate14 -> rate18"]["1-4Hz"]["lag_ms"]
            row["rate18_gain_vs_rate14"] = sl["rate14 -> rate18"]["1-4Hz"]["gain"]
        if ct:
            row["tap_control"] = {k: (v["level_best"][:3], v["diff_best"][:3]) for k, v in ct["tap_control"].items()}
            row["orch_xcorr_control"] = ct["orch_xcorr_control"]
        if bd and row["eps"] == "V293":
            fc, dd = bd[0], bd[1]
            age_mean = tm.get("sample_age_mean_ms(+d)", float(np.mean(tm["sample_age_at_carState_ms_pct(+d)"])))
            row["composite"] = {}
            for f in FREQS:
                pdm = pole_delay_ms(f, fc)
                row["composite"][f] = dict(pole_ms=round(pdm, 2),
                                           D_act=round(row["lambda_prime_mean"] + dd + pdm + age_mean, 2),
                                           D_loop=round(row["A_mean"] + dd + pdm, 2))
        S[r] = row
    # pooled route-cluster bootstrap for D_ctl, A, lambda', and D_loop at each f, per speed bin
    rng = np.random.default_rng(0)
    pooled = {}
    rows = [S[r] for r in V293 if S.get(r) and S[r].get("composite")]
    for key in ("D_ctl", "A", "lambda_prime", "tap_dd", "tap_fc"):
        vals = []
        for row in rows:
            vals.append(dict(D_ctl=row["D_ctl_mean"], A=row["A_mean"], lambda_prime=row["lambda_prime_mean"],
                             tap_dd=row["tap_diff_best"][1], tap_fc=row["tap_diff_best"][0])[key])
        vals = np.array(vals, float)
        bs = [np.mean(rng.choice(vals, len(vals))) for _ in range(2000)]
        pooled[key] = dict(per_route=vals.round(3).tolist(), mean=float(vals.mean()), ci95=np.percentile(bs, [2.5, 97.5]).round(3).tolist())
    for b in BINS:
        vals = [(row["A_by_speed"][b]["mean"] if row["A_by_speed"].get(b) else np.nan) for row in rows]
        dctl = [row["D_ctl_by_speed"].get(b) for row in rows]
        vals = np.array(vals, float); dctl = np.array([np.nan if x is None else x for x in dctl], float)
        ok = np.isfinite(vals)
        bs = [np.mean(rng.choice(vals[ok], ok.sum())) for _ in range(2000)] if ok.sum() else [np.nan]
        pooled[f"A {b}"] = dict(per_route=vals.round(3).tolist(), mean=float(np.nanmean(vals)), ci95=np.percentile(bs, [2.5, 97.5]).round(3).tolist())
        okd = np.isfinite(dctl)
        bs = [np.mean(rng.choice(dctl[okd], okd.sum())) for _ in range(2000)] if okd.sum() else [np.nan]
        pooled[f"D_ctl {b}"] = dict(per_route=dctl.round(3).tolist(), mean=float(np.nanmean(dctl)), ci95=np.percentile(bs, [2.5, 97.5]).round(3).tolist())
        # D_loop per bin: A_bin + dd + pole(f) using each route's own tap law (bin-specific tap fit if present)
        for f in (2.0, 2.5, 3.5):
            dl = []
            for row in rows:
                tb = row["tap_by_speed"].get(b) or row["tap_diff_best"]
                if not row["A_by_speed"].get(b):
                    continue
                dl.append(row["A_by_speed"][b]["mean"] + tb[1] + pole_delay_ms(f, tb[0]))
            dl = np.array(dl)
            if len(dl):
                bs = [np.mean(rng.choice(dl, len(dl))) for _ in range(2000)]
                pooled[f"D_loop_floor {b} @{f}Hz"] = dict(per_route=dl.round(2).tolist(), mean=float(dl.mean()),
                                                          ci95=np.percentile(bs, [2.5, 97.5]).round(2).tolist())
    for f in FREQS:
        for k in ("D_act", "D_loop"):
            vals = np.array([row["composite"][f][k] for row in rows])
            bs = [np.mean(rng.choice(vals, len(vals))) for _ in range(2000)]
            pooled[f"{k}_floor @{f}Hz"] = dict(per_route=vals.round(2).tolist(), mean=float(vals.mean()),
                                               ci95=np.percentile(bs, [2.5, 97.5]).round(2).tolist())
    out = dict(routes=S, pooled_V293=pooled)
    json.dump(out, open(HERE / "out" / "summary.json", "w"), indent=1, default=float)
    for r, row in S.items():
        if not row:
            print(r, "MISSING"); continue
        print(f"\n== {r} {row['eps']} n={row['n_frames']} ident={row['identity_rate']:.4f} ppm={row['clock_ppm']} fit={row['clock14A']['fitted_frac']:.2f}")
        print(f"  D_ctl {row['D_ctl_mean']:.2f} {row['D_ctl_pct']} by speed {row['D_ctl_by_speed']}  stale {row['carState_loops_stale']}")
        print(f"  lambda' mean {row['lambda_prime_mean']:.2f} q {row['lambda_prime_q']}")
        print(f"  A {row['A_mean']:.2f} by speed {row['A_by_speed']}")
        print(f"  age(+d) {row['age_pct']}  e18-e14 {row['e18_minus_e14']}  eAB-e14 {row['eAB_minus_e14']}")
        print(f"  tap diff {row['tap_diff_best']} level {row['tap_level_best']} by speed {row['tap_by_speed']}")
        print(f"  rate14 lag vs d(angle)/dt {row.get('rate14_lag_vs_grad_angle_ms_1-4Hz')} / {row.get('rate14_lag_vs_grad_angle_ms_2-8Hz')}  rate18-rate14 {row.get('rate18_minus_rate14_ms_1-4Hz')} gain {row.get('rate18_gain_vs_rate14')}")
        if row.get("composite"):
            print("  composite", row["composite"])
        if row.get("tap_control"):
            print("  tap control", row["tap_control"])
            print("  orch xcorr control", {k: (v["lag_refined_ms"] if v else None) for k, v in row["orch_xcorr_control"].items()})
    print("\nPOOLED V293")
    for k, v in pooled.items():
        print(" ", k, v)


if __name__ == "__main__":
    main()
