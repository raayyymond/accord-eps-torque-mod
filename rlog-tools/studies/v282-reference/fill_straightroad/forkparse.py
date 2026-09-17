"""rlog parser with the FORK's cereal schema (kit schema slot @137 = epsTelemetry collides with the fork's
starpilotLateralState @137). Copied schemas in ./forkcereal (car.capnp from opendbc_repo; git symlink on Windows)."""
import io
from pathlib import Path
import zstandard as zstd
import capnp
capnp.remove_import_hook()
_log = capnp.load(str(Path(__file__).parent / "forkcereal" / "log.capnp"))
def read_messages(p):
    data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(Path(p).read_bytes())).read()
    for e in _log.Event.read_multiple_bytes(data):
        yield e
