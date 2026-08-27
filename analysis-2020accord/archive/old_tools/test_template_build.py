"""Exercise build_rwd_from_template with no patches; assert byte-identical."""
import os, sys, gzip
ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import CALIB_FILES
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from encode_eps import build_rwd_from_template

TESTS = [
    str(CALIB_FILES / "39990-T2F-A210.rwd.gz"),
    str(CALIB_FILES / "39990-T3L-A210.rwd.gz"),
    str(CALIB_FILES / "39990-TV9-A910.rwd.gz"),
    str(CALIB_FILES / "39990-TG7-A030-M1.rwd.gz"),
    str(CALIB_FILES / "39990-T5N-M020-M1.rwd.gz"),
]

passed = failed = 0
for path in TESTS:
    raw = open(path, 'rb').read()
    if path.endswith('.gz'): raw = gzip.decompress(raw)
    rebuilt = build_rwd_from_template(path, patched_blocks={})
    ok = rebuilt == raw
    print(f"{os.path.basename(path)}: template-rebuild byte-equal? {ok}  (raw={len(raw)}, rebuilt={len(rebuilt)})")
    passed += int(ok); failed += int(not ok)

print(f"\n{passed} passed, {failed} failed")
sys.exit(0 if failed == 0 else 1)
