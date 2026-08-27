# `analysis-2020accord/` — layout

Reorganised 2026-08-26. Everything here was flat (649 scripts in one directory) until then.

| folder | what is in it |
|---|---|
| `model/` | **the golden model** — `eps_lkas_chain_model.py` (facade) over `eps_chain_{core,lanes,control,delivery}.py`. Verification contract in `CLAUDE.md`. |
| `lib/` | shared importable modules: `_*_lib.py`, `_*_common.py`, `firmware_paths.py`, `encode_eps.py`, `verify_bootloader_crc.py` |
| `builds/` | `build_v*_tva.py`, grouped `v18_v49` · `v50_v79` · `v80_v107` · `telemetry` |
| `extract/` | rlog → cache builders (`extract_*_cache.py`) |
| `verify/` | `verify_*`, `audit_*`, `redteam_*`, gate checks |
| `studies/` | per-topic work (`acoustic`, `grind2`, `nearcentre`, `highway`, `models`, …) and `studies/sessions/<route-or-build-tag>/` |
| `sessions/` | mixed notes + data kept together for one build session (`v97`, `v99`, `v100`, `v74base`) |
| `notes/` | long-form firmware notes (`TORQUE_PATH_*`, `EME_*`, `HOW_TO_BUILD_*`) |
| `reference/` | data of record: `svd_for_ghidra/`, `svd_parts/`, `opendbc/`, `fw_inventory/`, `can-scans/`, `e4_excitation/`, the MCU datasheet |
| `figures/` | plot artifacts of record |
| `archive/` | superseded scripts (`old_tools/`, one-off scratch) |
| `ghidra_project/` | the Ghidra database (binary, gitignored) |
| `rlogs/` | drive captures (local only, gitignored) |
| `_scratch/` | **regenerable**, gitignored: `cache/<route>/`, `out/`, `data/`, `logs/` |

## Imports

`.pkgroot` marks this directory as the import root. Scripts that import a sibling by bare name carry a
`PATH BOOTSTRAP` block at the top that walks up to `.pkgroot` and puts this directory and every code
subfolder on `sys.path` — so they run from any working directory. Keep the block if you move a script,
and re-base its `__file__`-relative anchors by the number of levels it moved.

Run everything with the `bin_decompile` conda env:
`C:/Users/dudei/anaconda3/envs/bin_decompile/python` (Python 3.12 — some scripts use f-strings that
older interpreters reject).
