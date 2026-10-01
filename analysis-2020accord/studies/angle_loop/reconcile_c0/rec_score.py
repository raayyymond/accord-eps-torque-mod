"""score rec_time_*.json with harness_time's OWN gates (per_speed_score), strict and line-only, plus the per-speed
detail table and the safety scenarios.  Analysis only."""
import sys, json, os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
from pathlib import Path
HERE = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\studies\angle_loop")
sys.path.insert(0, str(HERE))
import numpy as np
import harness_time as HT
import lane_mirror_v295 as LM

OUT = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\_scratch\angle_loop\reconcile")


def kp_kd_at(r, v):
    spd = int(round(v * 3.6 * 64))
    if "gX" in r:
        G = LM.lerp(r["gX"], r["gY"], spd)
        return r["kpY"][0] * G / 256.0, r["kdY"][0] if r.get("d_rate") else 0
    if r.get("key") == "speed":
        k = spd >> 8
        return LM.lerp(r["kpX"], r["kpY"], k), (LM.lerp(r["kdX"], r["kdY"], k) if r.get("d_rate") else 0)
    return max(r["kpY"]), (r["kdY"][0] if r.get("d_rate") else 0)


def score(fn, members=False):
    d = json.loads((OUT / fn).read_text())
    rows = d["rows"]
    res = d["results"]
    by_mem = {}
    for r in res:
        by_mem.setdefault(r["member"], []).append(r)
    out = {}
    for mem, rr in by_mem.items():
        T = HT.table(rr, rows)
        for strict in (True, False):
            tag = ("STRICT" if strict else "LINE-ONLY")
            line = {}
            for v in HT.SPEEDS:
                kps = [kp_kd_at(r, v)[0] for r in rows]
                kds = [kp_kd_at(r, v)[1] for r in rows]
                gates, allpass, cost = HT.per_speed_score(T, v, kps, kds, strict=strict)
                for i in range(len(rows)):
                    fails = [k for k in HT.GATES if not gates[k][i]]
                    line.setdefault(i, []).append((v, bool(allpass[i]), fails))
            for i, cells in line.items():
                out.setdefault(mem, {}).setdefault(tag, {})[rows[i]["label"]] = cells
    return rows, out, by_mem


def detail(fn):
    d = json.loads((OUT / fn).read_text())
    rows = d["rows"]
    T = HT.table([r for r in d["results"] if r["member"] == "nominal"], rows)
    for i, r in enumerate(rows):
        print(f"\n**{r['label']}**")
        print("| m/s | Kp_eff | ess | hold | tg0.2 | tg0.5 | +-1 fit | dj ev | stick% | T_hf hold | T_hf sin | hunt p2p | step ov% | hard16 / ref |")
        print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for v in HT.SPEEDS:
            rh, st, s02, s05, ssm = (T[(n, v)] for n in ("rh", "st", "s02", "s05", "ssm"))
            dj = s02["dj_events"][i] + s05["dj_events"][i] + ssm["dj_events"][i] + rh["hold_slips"][i] + st["hold_slips"][i]
            stick = max(s02["stick_pct"][i], s05["stick_pct"][i], ssm["stick_pct"][i])
            print(f"| {v:g} | {kp_kd_at(r, v)[0]:.0f} | {rh['ess_turn'][i]:.2f} | {rh['hold_ratio'][i]:.3f} | {s02['track_gain'][i]:.3f} |"
                  f" {s05['track_gain'][i]:.3f} | {ssm['fit_gain'][i]:.2f} | {dj:.0f} | {stick:.0f} | {max(rh['T_hf'][i], st['T_hf'][i]):.1f} |"
                  f" {max(s02['T_hf'][i], s05['T_hf'][i], ssm['T_hf'][i]):.1f} | {max(rh['hunt_p2p'][i], st['hunt_p2p'][i]):.2f} |"
                  f" {st['overshoot_pct'][i]:.0f} | {rh['hard16'][i]:.2f} / {rh['hard16_ref'][i]:.2f} |")
        if ("ov_fade", 3.0) in T:
            print("| m/s | override fade-only overshoot deg / peak T | latch overshoot | sentinel L16 peak T / s>50 / excursion | dis meas / zero excursion |")
            print("|---|---|---|---|---|")
            for v in HT.SPEEDS:
                ov, la, se, dm, dz = (T[(n, v)] for n in ("ov_fade", "ov_latch", "sen_L16", "dis_meas", "dis_zero"))
                print(f"| {v:g} | {ov['lurch_overshoot'][i]:.2f} / {ov['lurch_peakT'][i]:.0f} | {la['lurch_overshoot'][i]:.2f} |"
                      f" {se['sen_peakT'][i]:.0f} / {se['sen_dur_s'][i]:.2f} / {se['sen_excursion'][i]:.1f} |"
                      f" {dm['dis_excursion'][i]:.2f} / {dz['dis_excursion'][i]:.2f} |")


if __name__ == "__main__":
    fn = sys.argv[1]
    rows, out, by_mem = score(fn)
    for mem, o in out.items():
        print(f"\n===== member {mem}")
        for tag, d in o.items():
            print(f"  -- {tag}")
            for lab, cells in d.items():
                n = sum(1 for c in cells if c[1])
                s = " ".join(f"{v:g}:{'PASS' if ok else '/'.join(f)}" for v, ok, f in cells)
                print(f"    {n}/7  {lab[:60]:60s} {s}")
    if len(sys.argv) > 2 and sys.argv[2] == "--detail":
        detail(fn)
