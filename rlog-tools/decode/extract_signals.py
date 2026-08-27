"""Extract canonical signal CSV/parquet per route.

Signals (per-event, native rates, time-indexed by logMonoTime in nanoseconds):
- t_ns:                   logMonoTime
- src:                    which message ('cc'|'cs'|'co'|'ss'|'lp')
- v_ego, a_ego, v_cluster, yaw_rate            (cs)
- str_angle_meas, str_rate_meas                (cs)
- str_torque_driver, str_torque_eps            (cs)
- str_pressed, lat_active, sd_enabled          (cs|cc|ss)
- cmd_torque, cmd_angle, cmd_curvature         (cc.actuators)
- cmd_torque_can                               (cc.actuators.torqueOutputCan)  <- THE EPS input
- out_torque, out_torque_can                   (co.actuatorsOutput)             <- post-limiter
- lat_accel, lon_accel, ang_vel_z              (livePose.accelerationDevice etc.)
- alert_text                                   (ss alerts)

Output: D:/drivedata/signals/<route>.parquet  (long-form, one row per event)
"""
import io
import sys
from pathlib import Path
import zstandard as zstd
import capnp
import pandas as pd
from tqdm import tqdm

CEREAL_DIR = Path(__file__).parents[1] / "cereal"
capnp.remove_import_hook()
log_capnp = capnp.load(str(CEREAL_DIR / "log.capnp"))

DRIVE_ROOT = Path("D:/drivedata")
OUT_DIR = DRIVE_ROOT / "signals"
OUT_DIR.mkdir(exist_ok=True)


def extract_segment(rlog_path: Path):
    """Yield dict rows from a single rlog.zst."""
    raw = rlog_path.read_bytes()
    data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(raw)).read()

    # Final segment of a route can be truncated (ignition cycled mid-write);
    # accept whatever we can read before the cap'n proto stream goes ragged.
    it = log_capnp.Event.read_multiple_bytes(data)
    while True:
        try:
            evt = next(it)
        except StopIteration:
            break
        except capnp.KjException:
            break
        t = evt.logMonoTime
        w = evt.which()

        if w == "carState":
            cs = evt.carState
            yield {
                "t_ns": t, "src": "cs",
                "v_ego": cs.vEgo, "v_cluster": cs.vEgoCluster, "a_ego": cs.aEgo, "yaw_rate": cs.yawRate,
                "str_angle_meas": cs.steeringAngleDeg, "str_rate_meas": cs.steeringRateDeg,
                "str_torque_driver": cs.steeringTorque, "str_torque_eps": cs.steeringTorqueEps,
                "str_pressed": cs.steeringPressed,
                "steer_fault_temp": cs.steerFaultTemporary, "steer_fault_perm": cs.steerFaultPermanent,
            }
        elif w == "carControl":
            cc = evt.carControl
            a = cc.actuators
            yield {
                "t_ns": t, "src": "cc",
                "lat_active": cc.latActive, "long_active": cc.longActive,
                "cmd_torque": a.torque, "cmd_angle": a.steeringAngleDeg, "cmd_curvature": a.curvature,
                "cmd_torque_can": a.torqueOutputCan,
                "current_curvature": cc.currentCurvature,
            }
        elif w == "carOutput":
            co = evt.carOutput
            ao = co.actuatorsOutput
            yield {
                "t_ns": t, "src": "co",
                "out_torque": ao.torque, "out_angle": ao.steeringAngleDeg,
                "out_torque_can": ao.torqueOutputCan, "out_curvature": ao.curvature,
            }
        elif w == "selfdriveState":
            ss = evt.selfdriveState
            yield {
                "t_ns": t, "src": "ss",
                "sd_enabled": ss.enabled, "sd_active": ss.active,
                "sd_state": str(ss.state), "alert_text": (ss.alertText1 or "") + ("|" + ss.alertText2 if ss.alertText2 else ""),
            }
        elif w == "livePose":
            lp = evt.livePose
            ad = lp.accelerationDevice
            avd = lp.angularVelocityDevice
            vd = lp.velocityDevice
            yield {
                "t_ns": t, "src": "lp",
                "lat_accel": ad.y, "lon_accel": ad.x, "vert_accel": ad.z,
                "ang_vel_x": avd.x, "ang_vel_y": avd.y, "ang_vel_z": avd.z,
                "vel_body_x": vd.x, "vel_body_y": vd.y,
            }


def process_route(route_id: str):
    seg_dirs = sorted(
        DRIVE_ROOT.glob(f"{route_id}--*"),
        key=lambda p: int(p.name.split("--")[-1]),
    )
    print(f"Route {route_id}: {len(seg_dirs)} segments")
    rows = []
    seg_t0 = None  # logMonoTime of first event, used as route_t0
    for seg in tqdm(seg_dirs):
        rlog = seg / "rlog.zst"
        if not rlog.exists():
            print(f"  WARN: missing {rlog}")
            continue
        seg_idx = int(seg.name.split("--")[-1])
        for row in extract_segment(rlog):
            if seg_t0 is None:
                seg_t0 = row["t_ns"]
            row["seg"] = seg_idx
            row["t_s"] = (row["t_ns"] - seg_t0) / 1e9
            rows.append(row)

    df = pd.DataFrame(rows)
    out_path = OUT_DIR / f"{route_id}.parquet"
    df.to_parquet(out_path, index=False)
    print(f"  wrote {out_path}  ({len(df):,} rows, {df['t_s'].max():.1f}s total)")
    print(f"  msg type counts: {df['src'].value_counts().to_dict()}")
    return df


if __name__ == "__main__":
    routes = ["00000006--2459689731", "00000007--408bdfcdb9"]
    for r in routes:
        process_route(r)
