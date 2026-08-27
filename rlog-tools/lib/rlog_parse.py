"""Minimal rlog.zst parser. No openpilot dependency tree — just cereal schemas + pycapnp + zstandard."""
import io
import sys
from pathlib import Path
import zstandard as zstd
import capnp

CEREAL_DIR = Path(__file__).parents[1] / "cereal"
capnp.remove_import_hook()
log_capnp = capnp.load(str(CEREAL_DIR / "log.capnp"))


def read_messages(rlog_path):
    """Yield cap'n proto Event readers from a single rlog.zst file."""
    raw = Path(rlog_path).read_bytes()
    data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(raw)).read()
    for evt in log_capnp.Event.read_multiple_bytes(data):
        yield evt


if __name__ == "__main__":
    path = sys.argv[1]
    n = 0
    which_counts = {}
    for evt in read_messages(path):
        n += 1
        w = evt.which()
        which_counts[w] = which_counts.get(w, 0) + 1
        if n >= 1000:
            break
    print(f"first 1000 messages in {path}:")
    for k, v in sorted(which_counts.items(), key=lambda x: -x[1])[:25]:
        print(f"  {v:5d}  {k}")
