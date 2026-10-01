# -*- coding: utf-8 -*-
"""f4: the mode-B drive sweep (r71b's 21 chunks, 608 s, the real fork port per lane) over fork candidates on V295
cells.  Controls in every run: V295+r1 ("r1"), a duplicate of it at a different batch row ("r1dup" = the noise floor
of every difference: the sensor-noise stream is drawn per row), and V294+r1 ("V294_r1", what flew).
Usage: python f4_sweep.py <stage> ; stages defined below.  Output: out/f4_<stage>.json + a printed table."""
import sys, json, time, itertools
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/fork-config")
import numpy as np
import fc_lib as F
H = F.H

c294, c295 = H.Cells.v294(), F.cells_v295()
BANDS = [b for b, _, _ in H.BANDS]
KEYS = ("track_gain", "turn_hold", "straight_delivery", "i_share", "J_err", "hard16", "s03", "s13", "s15", "cmd_rms",
        "slew_share", "sat4096")


def stage_def(stage):
    C = []
    if stage == "s1":
        for laf in (14.0, 12.5, 11.0, 10.0):
            for kpol in ("fix", "iso"):
                if laf == 14.0 and kpol == "iso":
                    continue
                kp = 0.9 if kpol == "fix" else round(0.9 * laf / 14.0, 3)
                for ki, kih in ((0.3, 0.0), (0.5, 0.0), (0.3, 1.0), (0.3, 2.0)):
                    if laf == 14.0 and kp == 0.9 and ki == 0.3 and kih == 0.0:
                        continue
                    C.append(F.Fork("L%.1f_%s_Ki%.1f_%.1f" % (laf, kpol, ki, kih), kp=kp, ki=ki, ki_high=kih, laf=laf))
        members = ("nominal", "b_lo", "light_b")
    elif __import__("os").path.exists("out/%s_spec.json" % stage):
        spec = json.load(open("out/%s_spec.json" % stage))
        C = [F.Fork(**d) for d in spec["forks"]]
        members = tuple(spec["members"])
    else:
        raise SystemExit("unknown stage")
    return C, members


def run(stage, dists=("lp", "full"), max_lanes=320):
    cands, members = stage_def(stage)
    controls = [(c295, F.Fork("r1")), (c294, F.Fork("V294_r1")), (c295, F.Fork("r1dup"))]
    pairs = controls[:1] + [(c295, f) for f in cands] + controls[1:]
    per = len(members) * 21
    nb = max(1, max_lanes // per)
    out = {}
    t0 = time.time()
    for dist in dists:
        for s in range(0, len(pairs), nb):
            grp = pairs[s:s + nb]
            R, idx = F.sim(grp, list(members), dist=dist)
            for (_, fk) in grp:
                for m in members:
                    met = F.metrics(R, idx[(fk.name, m)])
                    out[(dist, fk.name, m)] = met
            print("  %s: %d/%d configs  %.0f s" % (dist, min(s + nb, len(pairs)), len(pairs), time.time() - t0), flush=True)
    meta = {f.name: F.asdict(f) for _, f in pairs}
    json.dump(dict(meta=meta, res={"|".join(k): v for k, v in out.items()}), open("out/f4_%s.json" % stage, "w"))
    return out, [f for _, f in pairs], members


def table(out, forks, members, dists):
    for dist in dists:
        for m in members:
            base = out[(dist, "r1", m)]
            print("\n=== %s / %s : V295+r1 absolute, then candidate - r1 (tracking, turn-hold, straight, i-share | J x, hard16 x, s13 x, s03 x | lc dB)" % (dist, m))
            print("  %-28s" % "r1 (abs)" + " ".join("%s:%.3f/%.3f/%.2f/%.2f" % (b, base[b]["track_gain"], base[b]["turn_hold"],
                                                     base[b]["straight_delivery"], base[b]["i_share"]) for b in BANDS if b in base)
                  + "  lc %.1fHz %.1fdB" % (base["limit_cycle"]["f"], base["limit_cycle"]["dB"]))
            for fk in forks:
                if fk.name == "r1":
                    continue
                r = out[(dist, fk.name, m)]
                s = "  %-28s" % fk.name
                for b in BANDS:
                    if b not in r or b not in base:
                        continue
                    d = lambda k: r[b][k] - base[b][k]  # noqa: E731
                    x = lambda k: r[b][k] / base[b][k] if base[b][k] else float("nan")  # noqa: E731
                    s += " %s:%+.3f/%+.3f/%+.2f/%+.2f|%.2f,%.2f,%.2f,%.2f" % (
                        b, d("track_gain"), d("turn_hold") if np.isfinite(base[b]["turn_hold"]) else float("nan"),
                        d("straight_delivery"), d("i_share"), x("J_err"), x("hard16") if np.isfinite(base[b]["hard16"]) else float("nan"),
                        x("s13"), x("s03"))
                s += "  lc %.1fHz %+.1fdB" % (r["limit_cycle"]["f"], r["limit_cycle"]["dB"] - base["limit_cycle"]["dB"])
                if r.get("diverged"):
                    s += " DIVERGED"
                print(s)


if __name__ == "__main__":
    stage = sys.argv[1]
    dists = tuple(sys.argv[2].split(",")) if len(sys.argv) > 2 else ("lp", "full")
    out, forks, members = run(stage, dists)
    table(out, forks, members, dists)
