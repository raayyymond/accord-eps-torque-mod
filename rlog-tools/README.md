# rlog-tools — Openpilot rlog parsing for EPS analysis

Standalone toolkit for parsing openpilot rlogs (route logs) and extracting
signals relevant to EPS analysis: CAN bus traffic, steering commands,
torque measurements, driver inputs, model predictions.

This directory is self-contained. The kit ships it as a portable utility
you can drop into other openpilot-adjacent projects.

## What's here

| File | Purpose |
|---|---|
| `lib/rlog_parse.py` | Core rlog reader. Handles `.bz2` / `.zst` / raw rlog files. Yields cereal log events as parsed objects. |
| `decode/extract_signals.py` | Extracts time-series signals (CAN messages, model outputs, controlsd state) from rlogs into pandas DataFrames. Configurable signal list. |
| `studies/misc/dcam_clip.py` | Extracts driving camera (`dcam`) frames from rlog segments for visual context around events. |
| `cereal/` | The openpilot `cereal` schema (capnproto definitions for all log message types). Needed for `lib/rlog_parse.py` to deserialize. Includes `car.capnp`, `log.capnp`, `custom.capnp`, `deprecated.capnp`. |

## Quick install

```bash
pip install pycapnp numpy pandas
```

Optional (for dcam_clip):
```bash
pip install opencv-python
```

The `cereal/` directory ships its `.capnp` schemas; `pycapnp` reads them
at runtime. No build step required for the Python API (the kit doesn't
ship the compiled C++ libs — pure-Python is enough for parsing).

## Common usage

### Parse an rlog and iterate events
```python
from rlog_parse import iter_log_events

for event in iter_log_events("rlog.bz2"):
    if event.which() == "carState":
        print(event.carState.steeringAngleDeg, event.carState.steeringTorque)
    elif event.which() == "can":
        for msg in event.can:
            if msg.address == 0xE4:  # STEER_COMMAND
                print(msg.dat.hex())
```

### Extract a signal set to a DataFrame
```python
from extract_signals import extract_signals

df = extract_signals(
    "rlog.bz2",
    signals=["carState.steeringAngleDeg",
             "carState.steeringTorque",
             "controlsState.lateralControlState.pidState.error",
             "modelV2.position.x",
             "modelV2.position.y"]
)
df.to_parquet("drive_signals.parquet")
```

### Clip driving camera around a timestamp
```python
from dcam_clip import extract_clip

extract_clip(
    rlog="rlog.bz2",
    dcam="dcamera.hevc",
    start_seconds=120,
    duration_seconds=10,
    output="event_clip.mp4"
)
```

## Where rlogs come from

- **Comma device:** `/data/media/0/realdata/<route_id>/<segment>/rlog`
  (full) or `qlog` (compressed subset)
- **Connect cloud:** download via `gh:commaai/openpilot-tools` or the
  Connect web UI
- **Local copies:** if you've extracted rlogs from a comma device or a
  shared route, point the scripts at the file path

## Relationship to other parts of the kit

- **`analysis-2020accord/`** telemetry analysis scripts (e.g. `studies/gates/analyze_gentle_eme.py`,
  `studies/telemetry/analyze_telem_0x660.py`, `studies/gates/analyze_torque_thresholds.py`) use rlog-tools
  (or equivalent code paths) to pull CAN/UDS telemetry signals out of route
  logs for the gentle-EME and telemetry investigations.
- **`docs/research/HONDA-EPS-PID-KNOWLEDGE.md`** — references rlog upload as the
  group's standard for sharing driving data (`wiki.firestar.link/faq`).

## Caveats

- The `cereal/` schema shipped here is a snapshot. If you parse rlogs
  from a newer openpilot version with new message types, you may need to
  update the schemas (copy from `openpilot/cereal/`).
- `pycapnp` install can be finicky on Windows — if you hit build issues,
  WSL is the reliable path.
- Very large rlogs (full drives) can be memory-heavy — `iter_log_events`
  is streaming, but `extract_signals` accumulates into a DataFrame. For
  GB-scale logs, batch by segment.
