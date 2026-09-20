"""D_ctl from the message chain, by VALUE matching (not by assumed ordering).

For each sendcan 0xE4 (bus 1) find which carControl produced it (exact value match of the torque command at candidate
cycle offsets), which carState that carControl's controlsd tick consumed (controlsState.curvature == carControl
.currentCurvature is computed from that carState; we match carState by nearest-preceding + verify by the angle it
implies through a per-route linear fit), and the CAN-in batch that produced the carState.
Also: the panda TX echo (can src 129, addr 0xE4) of each sent frame -> host-to-bus latency upper bound.

usage: python chain.py <counter--hash> [seg ...]
"""
import sys, json
from pathlib import Path
import numpy as np

KIT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(KIT / "rlog-tools" / "lib"))
from rlog_parse import read_messages  # noqa

RL = KIT / "analysis-2020accord" / "rlogs"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)


def s16(b):
    return int.from_bytes(b[0:2], "big", signed=True)


def grab(route, seg):
    A = {k: [] for k in ["cst_t", "cst_sa", "cst_sr", "cs_t", "cs_out", "cs_curv", "cc_t", "cc_tq", "cc_curvnow", "cc_lat",
                         "sc_t", "sc_e4", "can_t", "can_has14a", "echo_t", "echo_e4", "co_t", "co_tq"]}
    for e in read_messages(RL / f"75604b0a432fdc89_{route}--{seg}--rlog.zst"):
        try:
            w = e.which()
        except Exception:
            continue
        t = e.logMonoTime / 1e9
        if w == "carState":
            A["cst_t"].append(t); A["cst_sa"].append(e.carState.steeringAngleDeg); A["cst_sr"].append(e.carState.steeringRateDeg)
        elif w == "controlsState":
            A["cs_t"].append(t); A["cs_curv"].append(e.controlsState.curvature)
            try:
                A["cs_out"].append(e.controlsState.lateralControlState.torqueState.output)
            except Exception:
                A["cs_out"].append(np.nan)
        elif w == "carControl":
            a = e.carControl.actuators
            A["cc_t"].append(t); A["cc_tq"].append(a.torque); A["cc_curvnow"].append(e.carControl.currentCurvature)
            A["cc_lat"].append(float(e.carControl.latActive))
        elif w == "carOutput":
            A["co_t"].append(t)
            try:
                A["co_tq"].append(e.carOutput.actuatorsOutput.torque)
            except Exception:
                A["co_tq"].append(np.nan)
        elif w == "sendcan":
            for m in e.sendcan:
                if m.address == 0xE4 and m.src == 1:
                    A["sc_t"].append(t); A["sc_e4"].append(s16(bytes(m.dat)))
        elif w == "can":
            has = False
            for m in e.can:
                if m.address == 0x14A and m.src == 1:
                    has = True
                if m.address == 0xE4 and m.src == 129:
                    A["echo_t"].append(t); A["echo_e4"].append(s16(bytes(m.dat)))
            A["can_t"].append(t); A["can_has14a"].append(float(has))
    D = {}
    for k, v in A.items():
        x = np.asarray(v, float)
        D[k] = x
    for pre in ["cst", "cs", "cc", "sc", "can", "echo", "co"]:
        tk = f"{pre}_t"; o = np.argsort(D[tk], kind="stable")
        for k in list(D):
            if k.startswith(pre + "_") and len(D[k]) == len(o):
                D[k] = D[k][o]
    return D


def analyse(D):
    R = {}
    sc_t, sc = D["sc_t"], D["sc_e4"]
    cc_t, cc = D["cc_t"], D["cc_tq"]
    co_t, co = D["co_t"], D["co_tq"]
    # 1) which carControl / carOutput produced each sendcan: previous-k message by time, find k with best value match
    res = {}
    for name, tt, val in [("carControl", cc_t, cc), ("carOutput", co_t, co)]:
        idx = np.searchsorted(tt, sc_t) - 1       # last message strictly before the sendcan
        best = None
        for k in range(0, 4):
            j = idx - k
            ok = (j >= 0) & (np.abs(sc) > 50)
            x = val[j[ok]]; y = sc[ok]
            if len(x) < 100:
                continue
            g = float(np.dot(x, y) / np.dot(x, x))
            r = float(np.sqrt(np.mean((y - g * x) ** 2)))
            exact = float(np.mean(np.abs(y - np.round(g * x)) <= 1))
            res[f"{name}_k{k}"] = dict(scale=g, rms=r, frac_within_1lsb=exact)
            if best is None or r < best[1]:
                best = (k, r, g)
        res[f"{name}_best_k"] = best[0]
        j = idx - best[0]
        ok = j >= 0
        dt = (sc_t[ok] - tt[j[ok]]) * 1e3
        res[f"{name}_to_sendcan_ms"] = [float(np.percentile(dt, p)) for p in (5, 50, 95)]
    # 2) carControl -> the carState its controlsd tick consumed: controlsState and carControl are published together;
    #    controlsd runs on carState arrival, so the consumed carState is the last one before the controlsState.
    #    Verify with the angle: carControl.currentCurvature is a function of that carState's angle, so its correlation
    #    with carState angle at candidate offsets must peak at the chosen one.
    k = res["carControl_best_k"]
    jcc = np.searchsorted(cc_t, sc_t) - 1 - k
    ok = jcc >= 0
    jcst0 = np.searchsorted(D["cst_t"], cc_t) - 1
    offs = {}
    for m in range(0, 3):
        jj = jcst0 - m
        g = jj >= 0
        # differences remove the speed dependence of curvature(angle); correlation of increments
        a = np.diff(D["cst_sa"][jj[g]]); c = np.diff(D["cc_curvnow"][g])
        offs[m] = float(np.corrcoef(a, c)[0, 1]) if np.std(a) > 0 and np.std(c) > 0 else float("nan")
    mbest = max(offs, key=lambda q: abs(offs[q]) if np.isfinite(offs[q]) else -1)
    res["carState_offset_corr_increments"] = offs
    res["carState_best_offset"] = mbest
    jcst = jcst0[jcc[ok]] - mbest
    good = jcst >= 0
    dctl = (sc_t[ok][good] - D["cst_t"][jcst[good]]) * 1e3
    res["D_ctl_carState_to_sendcan_ms"] = [float(np.percentile(dctl, p)) for p in (5, 25, 50, 75, 95)]
    res["D_ctl_mean_ms"] = float(np.mean(dctl))
    # 3) CAN-in batch (containing 0x14A) -> carState
    ct = D["can_t"][D["can_has14a"] > 0]
    jc = np.searchsorted(ct, D["cst_t"]) - 1
    g = jc >= 0
    d = (D["cst_t"][g] - ct[jc[g]]) * 1e3
    res["canIn_to_carState_ms"] = [float(np.percentile(d, p)) for p in (5, 50, 95)]
    # 4) sendcan -> TX echo (src 129) matched by value sequence
    et, ev = D["echo_t"], D["echo_e4"]
    je = np.searchsorted(et, sc_t)
    lat = []
    for i in range(len(sc_t)):
        for q in range(je[i], min(je[i] + 4, len(et))):
            if ev[q] == sc[i] and abs(sc[i]) > 20:
                lat.append((et[q] - sc_t[i]) * 1e3); break
    res["sendcan_to_TXecho_batch_ms"] = [float(np.percentile(lat, p)) for p in (5, 50, 95)] if lat else None
    res["n_sendcan"] = int(len(sc_t))
    return res


if __name__ == "__main__":
    route = sys.argv[1]
    segs = sys.argv[2:] or ["3"]
    allr = {}
    for s in segs:
        D = grab(route, s)
        allr[s] = analyse(D)
        del D
        print(route, s, json.dumps(allr[s], indent=1))
    (OUT / f"chain_{route}.json").write_text(json.dumps(allr, indent=1))
