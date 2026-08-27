---
name: feedback-rwd-output-dir
description: "Current operator convention: all .rwd build scripts output to ../accord-firmware/flashing-2020accord/rwd/ (not inside the repository or next to the build script). Also: one build script per version family (build_v11_tva.py = V11 ceiling-raise, build_v12_tva.py = V12 gain); a new lever class gets a new build_vN script rather than piling variants into an existing one."
metadata:
  node_type: memory
  type: feedback
---

For the 2020 Accord work, the operator wants generated `.rwd` files written to **`../accord-firmware/flashing-2020accord/rwd/`** — the external directory the flasher (`flashing-2020accord/eps-update-tva.py`) reads from — not dropped inside the repository or next to the build script. Python tools honor `ACCORD_FIRMWARE_ROOT`, which defaults to `../accord-firmware`.

**Why:** keeps proprietary flashable artifacts outside the source repository in one known directory, so there is no hunting across source trees for the exact file to name at flash time (and it satisfies the iron rule of naming the exact file + bus before flashing).

**How to apply:** in any new `build_v*_tva.py`, use the shared firmware path resolver and its `RWD_DIR`, or honor `ACCORD_FIRMWARE_ROOT` with the default `../accord-firmware/flashing-2020accord/rwd/`. Do not introduce a repository-local or machine-specific absolute output path.

Companion convention (same session): **one build script per version family.** `build_v11_tva.py` = V11 ceiling-raise; `build_v12_tva.py` = V12 setpoint-gain (imports V11's verified clamp recipe to avoid drift). A genuinely new lever class gets its own `build_vN_tva.py` rather than being bolted onto an existing script. Aligns with [[feedback-rigorous-validation]] (each script is auditable in isolation). Build state lives in [[project-accord-torque-mod-v0]].
