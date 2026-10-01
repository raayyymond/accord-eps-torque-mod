# -*- coding: utf-8 -*-
"""d2_engine -- ADV-dynamics synthetic closed loop with the REAL fork controller (not the designer's VecPort).

Per 100 Hz frame: plant.wheel_angle() -> 0.1 deg quantiser -> fork_real.RealController (the real LatControlTorque
@20d24ab79, toggles = r71b's recorded runtime toggles + accord_torque_ki_high) -> Honda limiter (+-0.03/frame, trunc
x4096; steer_limited_by_safety when it clips by > 0.01, the harness rule) -> 0xE4 effective at tick 10k + pipe ->
byte-exact H.Lane (V294 / V295 cells) at 1 kHz -> H.PlantBatch (Karnopp stick-slip, members from the harness family,
x sensor noise 1.93 counts) -> back.
Each CONFIG runs as its own batch with the SAME row layout and seed, so rows are PAIRED across configs (identical
sensor-noise draws) -- differences between configs are not noise-realisation differences.
ANALYSIS ONLY.
"""
import os, sys, time
import numpy as np
HARN = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness"
sys.path.insert(0, HARN)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import v295_harness as H
import fork_real as FK

V295_IMG = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR."
            "SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
CELLS = {"V294": H.Cells.v294(),
         "V295": H.Cells.from_image(V295_IMG, "V295", "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed")}
KIH = {"r1": 0.0, "r2alt": 0.8}
CONFIGS = {"V294+r1": ("V294", "r1"), "V295+r1": ("V295", "r1"), "V295+r2alt": ("V295", "r2alt")}


def toggles_for(fork_name):
    tg = dict(H.route()["toggles"])
    assert tg["accord_torque_ki"] == 0.3 and tg["accord_torque_ki_high"] == 0.0 and tg["latAccelFactor"] == 14.0
    assert abs(tg["friction"] - 0.011) < 1e-9 and tg["steerKp"] == [[0], [0.9]]
    tg["accord_torque_ki_high"] = KIH[fork_name]
    return tg


def run(config, rows, secs, pipe_ms=22, x_noise=1.93, seed=3, lat_delay=0.426, laf_off=-0.149, record=True):
    """rows: list of dicts with keys member, v, c0 (T counts, + left, constant plant disturbance), des (callable
    t_seconds -> desired lateral accel m/s^2, or None), drv (callable t -> extra plant torque, or None),
    pressed (callable t -> bool, or None).  Returns dict of (B, NF) arrays."""
    cn, fn = CONFIGS[config]
    fam = H.family()
    B = len(rows)
    mem = [fam[r["member"]] for r in rows]
    V = np.array([r["v"] for r in rows], float)
    lane = H.Lane([CELLS[cn]] * B)
    plant = H.PlantBatch(mem, np.zeros(B), np.zeros(B), x_noise=x_noise, seed=seed)
    plant.set_speed(V)
    plant.c0 = np.array([r.get("c0", 0.0) for r in rows], float)
    tg = toggles_for(fn)
    reals = [FK.RealController(tg) for _ in range(B)]
    NF = int(secs * 100)
    keys = ("ang", "rate", "cmd", "la_act", "la_des", "i", "p", "f", "torque", "stuck", "T", "slew")
    R = {k: np.zeros((B, NF)) for k in keys}
    last_tq = np.zeros(B)
    steer_lim = np.zeros(B, bool)
    qcmd = np.zeros((B, NF + 4))
    wire_eff = np.zeros(B)
    idx, sp, mm = lane.demand(wire_eff)
    t0 = time.time()
    drv = np.zeros(B)
    for n in range(NF * 10):
        k = n // 10
        if n % 10 == 0:
            t = k * 0.01
            aw = plant.wheel_angle()
            aq = np.round(aw / 0.1) * 0.1
            tq = np.zeros(B)
            for j, rc in enumerate(reals):
                r = rows[j]
                a_des = r["des"](t) if r.get("des") else 0.0
                pr = bool(r["pressed"](t)) if r.get("pressed") else False
                o = rc.step(True, float(V[j]), float(aq[j]), float(plant.om[j]), pr, 0.0, 0.0, a_des / V[j] ** 2,
                            lat_delay, laf_off, bool(steer_lim[j]))
                tq[j] = o["torque"]
                if record:
                    R["la_act"][j, k] = o["la_act"]; R["la_des"][j, k] = o["la_des"]
                    R["i"][j, k] = o["i"]; R["p"][j, k] = o["p"]; R["f"][j, k] = o["f"]
                drv[j] = r["drv"](t) if r.get("drv") else 0.0
            lim, can = H.honda_limiter(tq, last_tq)
            R["slew"][:, k] = np.abs(tq - lim) > 1e-9
            steer_lim = np.abs(tq - lim) > 1e-2
            last_tq = lim
            qcmd[:, k] = can
            R["ang"][:, k] = aq
            R["torque"][:, k] = tq
        if (n - pipe_ms) >= 0 and (n - pipe_ms) % 10 == 0:
            wire_eff = qcmd[:, (n - pipe_ms) // 10]
            idx, sp, mm = lane.demand(wire_eff)
        x = plant.sense()
        T, _ = lane.tick(-x, sp, idx, mm)
        plant.step(T.astype(float), drv if np.any(drv) else None)
        if n % 10 == 9:
            R["rate"][:, k] = x / 8.0
            R["cmd"][:, k] = wire_eff
            R["T"][:, k] = T
            R["stuck"][:, k] = plant.om == 0.0
    R["runtime_s"] = time.time() - t0
    R["V"] = V
    return R
