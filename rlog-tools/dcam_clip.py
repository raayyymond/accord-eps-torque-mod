"""Extract a short clip from a segment's camera stream around a flagged timestamp.

Usage:
    python dcam_clip.py <route_id> <seg_idx> <t_start_in_seg> <duration> [--cam dcamera|fcamera] [--out PATH]
    python dcam_clip.py 00000007--408bdfcdb9 10 22.5 8

The .hevc files are raw HEVC bitstreams (no container). openpilot writes them at 20 fps.
"""
import argparse
import subprocess
import sys
from pathlib import Path

DRIVE_ROOT = Path("D:/drivedata")
CLIP_DIR = DRIVE_ROOT / "clips"
CLIP_DIR.mkdir(exist_ok=True)


def make_clip(route_id, seg_idx, t_start_in_seg, duration, cam="dcamera", out_path=None):
    seg_dir = DRIVE_ROOT / f"{route_id}--{seg_idx}"
    src = seg_dir / f"{cam}.hevc"
    if not src.exists():
        sys.exit(f"missing source: {src}")

    if out_path is None:
        out_path = CLIP_DIR / f"{route_id}--{seg_idx}-{cam}-t{t_start_in_seg:.1f}-{duration:.1f}s.mp4"
    out_path = Path(out_path)

    # raw HEVC has no PTS — tell ffmpeg the source framerate before -i so seek works in seconds
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-framerate", "20",
        "-i", str(src),
        "-ss", f"{t_start_in_seg:.3f}",
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("route_id")
    ap.add_argument("seg_idx", type=int)
    ap.add_argument("t_start_in_seg", type=float)
    ap.add_argument("duration", type=float)
    ap.add_argument("--cam", default="dcamera", choices=["dcamera", "fcamera"])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    p = make_clip(args.route_id, args.seg_idx, args.t_start_in_seg, args.duration, args.cam, args.out)
    print(f"wrote {p}")
