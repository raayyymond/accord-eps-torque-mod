---
name: feedback_rwd_output_beside_script
description: .rwd builders should write output under the external artifact root, not next to the script or to a machine-specific absolute path
metadata:
  type: feedback
---

When a `.rwd` builder script writes its output, the output file should land in
the external **`../accord-firmware/flashing-2020accord/rwd/`** directory (or
the equivalent `ACCORD_FIRMWARE_ROOT` override), not beside the script and not
at a hardcoded machine-specific absolute path.

**Why:** proprietary firmware artifacts are intentionally kept outside the
source repository, while a configurable sibling-root path works on every
checkout and keeps the flasher's inputs in one known directory.

**How to apply:** Resolve `OUT_PATH` and template paths through the shared
firmware path resolver and honor `ACCORD_FIRMWARE_ROOT`; the default is
`../accord-firmware`. Relates to [[feedback_rigorous_validation]].
