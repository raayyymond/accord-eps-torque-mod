#!/usr/bin/env python3
r"""Shared library for the MEASURED STEERING RATIO study (`_cache_ratio/`).

GEOMETRY (2020 Accord Sport 1.5T sedan, CV1/CV2 chassis)
    WHEELBASE  L = 2.830 m   (111.4 in)
    REAR TRACK T = 1.613 m   (63.5 in)   -- rear wheels are UNDRIVEN and UNSTEERED on this FWD car

SIGN CONVENTION -- MEASURED, NOT ASSUMED (see `qa()`), operator-confirmed frame:
    carState.steeringAngleDeg  > 0  = LEFT turn        (operator: NEGATIVE angle = RIGHT turn)
    livePose.angularVelocityDevice.z  < 0 on a LEFT turn  (device frame is x-fwd, y-right, z-DOWN)
    ⇒ vehicle yaw rate, positive-left,  yaw_A = -avz                     [corr(ang, avz) = -0.971]
    ⇒ rear differential,  positive-left, yaw_B = (ws_rr - ws_rl)/T       [corr(avz, rr-rl) = -0.898]

STEADY-STATE BICYCLE MODEL
    yaw = v * delta / (L + K v^2)      delta = road-wheel angle [rad], K = understeer gradient [s^2/m]
    => delta = yaw * (L + K v^2) / v
    RATIO(theta) = theta_steeringwheel / delta_roadwheel   (both deg)  -- a SECANT ratio.

🛑 carState.yawRate is IDENTICALLY ZERO on this car (0 nonzero samples / 512,895).  Method A is
   livePose, not carState.
"""
import glob
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CACHE = ROOT / "analysis-2020accord" / "_cache_ratio"

L_WB = 2.830          # m, wheelbase
T_REAR = 1.613        # m, rear track
DT = 0.05             # s, grid step (20 Hz)
RAD = 180.0 / np.pi

FIELDS = ("t", "seg", "v", "ang", "rate", "press", "std", "gear", "brake", "lat", "en", "yaw",
          "avz", "zstd", "lp_valid", "gy_x", "ws_fl", "ws_fr", "ws_rl", "ws_rr",
          "par_off", "par_offavg", "par_sr", "par_roll")


def load(routes=None):
    """Load the corpus.  Returns dict of concatenated float64 arrays + `route` (int) + `blk`.

    `blk` is a CONTIGUOUS-BLOCK id: a new block starts at every route change, segment change, or
    time gap > 0.5 s.  Bootstraps resample BLOCKS (episodes), never rows.
    """
    fs = sorted(CACHE.glob("*.npz")) if routes is None else [CACHE / f"{r}.npz" for r in routes]
    out, rid, parts = {k: [] for k in FIELDS}, [], []
    for i, f in enumerate(fs):
        z = np.load(f)
        n = len(z["t"])
        for k in FIELDS:
            out[k].append(np.asarray(z[k], float))
        rid.append(np.full(n, int(f.stem, 16), float))
        parts.append(f.stem)
    A = {k: np.concatenate(v) for k, v in out.items()}
    A["route"] = np.concatenate(rid)
    # contiguous blocks
    newblk = np.zeros(len(A["t"]), bool)
    newblk[0] = True
    newblk[1:] = ((np.diff(A["route"]) != 0) | (np.diff(A["seg"]) != 0)
                  | (np.diff(A["t"]) > 0.5) | (np.diff(A["t"]) < 0))
    A["blk"] = np.cumsum(newblk).astype(float)
    A["_routes"] = parts
    return A


def smooth(x, win_s=0.5):
    """Centred boxcar, applied IDENTICALLY to every channel so no relative lag is introduced."""
    n = max(1, int(round(win_s / DT)))
    if n % 2 == 0:
        n += 1
    k = np.ones(n) / n
    pad = n // 2
    xp = np.concatenate([np.full(pad, x[0]), x, np.full(pad, x[-1])])
    return np.convolve(xp, k, mode="valid")


def smooth_blocks(A, x, win_s=0.5):
    """`smooth` applied WITHIN each contiguous block (never across a route/segment seam)."""
    y = np.empty_like(x)
    b = A["blk"]
    idx = np.flatnonzero(np.diff(b) != 0) + 1
    for lo, hi in zip(np.r_[0, idx], np.r_[idx, len(b)]):
        y[lo:hi] = smooth(x[lo:hi], win_s) if hi - lo > 3 else x[lo:hi]
    return y


def base_mask(A, vmin=1.0, vmax=40.0):
    """Physical validity only -- NO steadiness, NO angle window.

    🛑 The speed window is applied to `v_ref` (REAR-AXLE speed), not to `vEgo`.  See `derive`.
    `v_ref > 1.0` also keeps us clear of the wheel-speed sensors' dropout floor: below
    vEgo 0.6 m/s, 74.8 % of frames report rear speeds of exactly 0."""
    return ((A["lp_valid"] > 0) & (A["gear"] == 2) & (A["std"] < 0.5)
            & (np.abs(A["ang"]) < 800) & np.isfinite(A["avz"]) & np.isfinite(A["ws_rl"])
            & (A["v_ref"] > max(vmin, 1.0)) & (A["v_ref"] < vmax) & (A["zstd"] < 0.05))


def derive(A, win_s=0.5):
    """Attach the smoothed channels and both raw yaw-rate estimates (rad/s, POSITIVE-LEFT).

    🛑🛑 `v_ref` IS THE REAR-AXLE SPEED (ws_rl + ws_rr)/2 -- NOT `vEgo`.  The steady-state bicycle
    model is written about the REAR AXLE (`yaw = v_rear * tan(delta) / L`), and openpilot's `vEgo`
    is an average over ALL FOUR wheels.  The front wheels are STEERED, so they run at v/cos(delta):
    MEASURED here, v_front/v_rear = 1.0016 / 1.0056 / 1.0372 / 1.1115 at |theta| =
    0-5 / 60-100 / 150-250 / 250-400 deg, against sec(delta) = 1.0000 / 1.0043 / 1.0343 / 1.0930.
    Using `vEgo` therefore UNDER-reads `delta` at the plateau by ~8 % and OVER-reads the plateau
    RATIO by the same amount, which SUPPRESSES the measured notch by ~10 %.  (vEgo/v_rear ran
    0.989 at centre and 1.079 at 250-400 deg -- an angle-dependent bias, exactly the shape that
    would fake, or here mask, a ratio notch.)
    The mean of the two REAR wheel speeds is the rear-axle-centre speed EXACTLY, by rigid-body
    kinematics, and the rear wheels are neither driven nor steered on this car."""
    A["s_ang"] = smooth_blocks(A, A["ang"], win_s)
    A["s_v"] = smooth_blocks(A, A["v"], win_s)
    A["v_ref"] = smooth_blocks(A, 0.5 * (A["ws_rl"] + A["ws_rr"]), win_s)
    A["s_rate"] = smooth_blocks(A, A["rate"], win_s)
    A["yawA"] = smooth_blocks(A, -A["avz"], win_s)
    A["yawB_raw"] = smooth_blocks(A, (A["ws_rr"] - A["ws_rl"]) / T_REAR, win_s)
    A["s_gyx"] = smooth_blocks(A, -A["gy_x"], win_s)          # raw-IMU control on Method A
    # d/dt for the steadiness test
    A["dyaw"] = np.gradient(A["yawA"], DT)
    A["dv"] = np.gradient(A["s_v"], DT)
    return A


def steady_mask(A, rate_max=25.0, dyaw_max=0.35, dv_max=1.5):
    return ((np.abs(A["s_rate"]) < rate_max) & (np.abs(A["dyaw"]) < dyaw_max)
            & (np.abs(A["dv"]) < dv_max))


def block_bootstrap(vals, blocks, stat, n=2000, seed=0):
    """Bootstrap over BLOCKS (episodes), never rows.  Returns (point, lo95, hi95)."""
    rng = np.random.default_rng(seed)
    ub, inv = np.unique(blocks, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    inv_s = inv[order]
    bounds = np.searchsorted(inv_s, np.arange(len(ub) + 1))
    idx_by_blk = [order[bounds[i]:bounds[i + 1]] for i in range(len(ub))]
    pt = stat(vals[np.concatenate(idx_by_blk)]) if len(ub) else np.nan
    outs = []
    for _ in range(n):
        pick = rng.integers(0, len(ub), len(ub))
        sel = np.concatenate([idx_by_blk[p] for p in pick])
        s = stat(vals[sel])
        if np.isfinite(s):
            outs.append(s)
    if len(outs) < 10:
        return pt, np.nan, np.nan
    return pt, float(np.percentile(outs, 2.5)), float(np.percentile(outs, 97.5))
